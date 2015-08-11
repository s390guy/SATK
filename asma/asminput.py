#!/usr/bin/python3
# Copyright (C) 2014, 2015 Harold Grovesteen
#
# This file is part of SATK.
#
#     SATK is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     SATK is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with SATK.  If not, see <http://www.gnu.org/licenses/>.

# This module handles all input operations for the assembler.py module.  Input can 
# be provided directly for the embedded assembler use case or for others via a source
# file, included file, or macro generated statements.
#
# Environment variable ASMPATH used to search for input files.

# Python imports
import os.path       # Access path tools by FileBuffer class

# SATK imports:
import satkutil      # Access the path manager

# ASMA imports:
import asmmacs       # Access macro facilities
import assembler     # Access assembler exceptions

this_module="asminput.py"

#
#  +--------------------------------+
#  |                                |
#  |   Input Statement Management   |
#  |                                | 
#  +--------------------------------+
#

# The LineBuffer class raises this exception when the buffer is empty.  The caller
# must know what to do in this event.
class BufferEmpty(Exception):
    def __init__(self):
        super().__init__()

# This excpetion is raised by a source when it has been exhausted.
class SourceEmpty(Exception):
    def __init__(self):
        super().__init__()

# An InputSource object raises this exception if it encounters a source related 
# problem.
class SourceError(Exception):
    def __init__(self,msg):
        self.msg=msg
        super().__init__(msg)

#
#  +-------------------+
#  |                   |
#  |   Input Sources   |
#  |                   | 
#  +-------------------+
#

# This is the base class for all input sources.  It defines the interface each
# subclass must support and the common methods exposed for external use.
#
# The purpose of the InputSource class (and its subclasses) is to provide and 
# INDIVIDUAL assembler statement as a Line object.  It is completely a slave to the
# requirements of the LineBuffer class.
class InputSource(object):
    def __init__(self,typ,sid,stmtno=None):
        self._depth=None      # This is the input source depth (used by the LineBuffer)
        self._sid=None        # The id of the source. (could a file name, etc.)
        self._typ=typ         # The type of input source
        self._stmtno=stmtno   # Statement number initiating source

   #
   #  Commonly shared methods
   #

    def __str__(self):
        return "InputSource(type='%s',sid=%s,stmtno=%s)" \
            % (self._typ,self._sid,self._stmtno)

    def setDepth(self,n):
        self._depth=n

   #
   #  Required subclass methods
   #

    # Terminate the source.  If not needed simply return.
    # If a problem occurs in terminating the input source, a SourceError exception
    # must be raised.
    def fini(self):
        raise NotImplementedError("%s subclass must provide fini() method" \
            % assembler.eloc(self,"fini",module=this_module))

    # This method returns an Line object when requested by the LineBuffer.
    # When the source is exhausted it must raise a SourceEmpty exception.
    # If the source encounters a problem in producing the input line, is must raise
    # a SourceError exception.
    def getLine(self):
        raise NotImplementedError("%s subclass must provide getLine() method" \
            % assembler.eloc(self,"getLine",module=this_module))

    # Initialize the source if needed.  If not needed simply return
    # If the source is unsuccessful in initializing itself, it must raise a SourceError
    # exception.
    def init(self):
        raise NotImplementedError("%s subclass must provide init() method" \
            % assembler.eloc(self,"init",module=this_module))

# Manage a text file as an input source.
# Instance Arguments:
#    typ        Type of input source. Always 'F' supplied by LineBuffer
#    filename   A file name is the source id for a FileSource
#    fixed      Specify True to use legacy line continuation conventions.
#               Specify False to use stream line continuation conventions.
class FileSource(InputSource):
    def __init__(self,typ,filename,stmtno=None,srcno=None,fixed=False):
        super().__init__(typ,filename,stmtno=stmtno)
        assert isinstance(filename,str),\
            "%s 'filename' argument must be a string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),filename)

        self.rname=filename       # Text input file relative path or absolute path
        self.fixed=fixed          # True if fixed line contuation in use.
        self.fileno=srcno         # File number of this source
        self.fname=None           # Text absolute path from search path.
        self.eof=False            # Flag set at physical end-of-file
        self.leof=False           # Flas set when at logical end-of-file
        self.fo=None              # Python file object
        self.lineno=None          # File line number
        #self.handler=asmcards.InputHandler()  # line continuation handler
        
        # Physical line class returned by this source
        if fixed:
            self.pcls=FixedLine
        else:
            self.pcls=StreamLine
        
        self.queued=[]  # Allows physical lines to be pushed back and read again

    # Finish use of this file input source
    def fini(self):
        if self.fo is None:
            raise ValueError("%s file object not created for file: %s" \
                % (assembler.eloc(self,"fini",module=this_module),self.fname))
        try:
            self.fo.close()
        except OSError:
            raise SourceError("could not close input text file: %s" % self.fname) \
                from None

    # Returns a physical line conforming to the files continuation convention
    def getLine(self,debug=False):
        # Validate source state for getLine() method
        if self.fo is None:
            cls_str=assembler.eloc(self,"getLine",module=this_module)
            raise ValueError("%s file object not created for file: %s" \
                % (cls_str,self.fname))
        if self.eof:
            if self.leof:
                cls_str=assembler.eloc(self,"getLine",module=this_module)
                raise ValueError("%s text file already at end-of-file: %s" \
                    % (cls_str,self.fname))
            else:
                raise SourceEmpty()

        # Read from queued physical lines before reading from file
        if len(self.queued)!=0:
            pline=self.queued[0]
            del self.queued[0]
            return pline

        # No queued lines, so read from the file
        line=self.fo.readline()
        if len(line)==0:
            self.fini()
            raise SourceEmpty()
        self.lineno+=1
        if line[-1]=="\n":
            line=line[:-1]

        return self.pcls(Source(lineno=self.lineno,fileno=self.fileno),line)

    # Perform file input source initialization
    # Locate the file based upon ASMPATH environment variable and open it
    def init(self,pathmgr=None,variable="ASMPATH"):
        if self.fo is not None:
            raise ValueError("%s file object already exists for file: %s" \
                % (assembler.eloc(self,"init",module=this_module),self.fname))
        try:
            self.fname,self.fo=pathmgr.ropen(self.rname,variable=variable)
        except ValueError as ve:
            raise SourceError("%s" % ve) from None

        self.lineno=0
        
    # Queue a  physical line for reading instead of the platform file
    def queue(self,pline):
        assert isinstance(pline,PhysLine),\
            "%s 'pline' argument must be an instance of asmline.PhyLine: %s" \
                % (assembler.eloc(self,"queue",module=this_module),pline)

        self.queued.append(pline)

# This is the base class for a source that injects lines into the input stream during
# execution of the assembler.
class InjectableSource(InputSource):
    def __init__(self,typ,sid):
        super().__init__(typ,sid)
        self.lines=[]

   #
   #  Methods required by superclass
   #

    def fini(self): pass

    def getLine(self,debug=False):
        try:
            line=self.lines[0]
            del self.lines[0]
        except IndexError:
            raise SourceEmpty() from None
        return line

    def init(self,pathmgr=None,variable=None): pass

   #
   #  Methods unique to injectable sources
   #

    def inject(self,lines,release=True):
        ln=[]
        if isinstance(lines,str):
            ln.append(lines)
        elif isinstance(lines,list):
            for ndx in range(len(lines)):
                line=lines[ndx]
                if not isinstance(line,str):
                    cls_str=assembler.eloc(self,"inject")
                    raise ValueError("%s 'line' argument item %s not a string: %s" \
                        (cls_str,ndx,line))
                if len(line)!=0 and line[-1]=="\n":
                    line=line[:-1]
                ln.append(line)
        else:
            cls_str=assembler.eloc(self,"inject")
            raise ValueError("%s 'lines' argument must be a string or list of "
                "strings: %s" % lines)
        self.lines.extend(ln)


class MacroSource(InputSource):
    def __init__(self,typ,exp,stmtno=None,srcno=None,fixed=False):
        if not isinstance(exp,asmmacs.Invoker):
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s 'exp' argument must be an asmmacs.Expander object: "
                "%s" % (cls_str,exp))

        self.exp=exp          # asmmacs.Invoker object
        self.depth=None       # Macro level nesting depth - See init() method.
        super().__init__(typ,exp.macro.name,stmtno=stmtno)
        self.queued=[]

    def init(self,pathmgr=None,variable=None):
        self.depth=self.exp.mgr.nest(self.exp)
        self.exp.enter()

    def fini(self):
        # Clean up Invoker that is no longer needed.
        mm=self.exp.mgr
        mm.unnest()
        self.exp=None

    # Returns a generated macro generated logical line from a macro model statement
    # Returns:
    #   A StreamLine object containing a physical line generated by a macro model 
    #   statement. The physical line may be continued or not.  The physical
    #   lines will always use the normal statement format.
    # Exception:
    #   MacroError if the macro detected a user error
    def getLine(self,debug=False):
        # Throws a MacroError if a user error is detected
        # Note: Need to accept a list of physical lines and a line continuation
        # convention

        if len(self.queued)>0:
            line=self.queued.pop(0)
            pline=StreamLine(None,line,genlvl=self.depth)
            if __debug__:
                if debug:
                    print("%s returning queued: %s" \
                        % (assembler.eloc(self,"getLine",module=this_module),pline))
            return pline

        # No previously queed physical lines so not get one (or more) from the
        # macro.
        plines=self.exp.generate()
        if __debug__:
            if debug:
                print("%s received from macro %s Invoker: %s" \
                    % (assembler.eloc(self,"getLine",module=this_module),\
                        self.exp.name,plines))

        # Determine if the macro is done generating input
        if plines is None:
            if __debug__:
                if debug:
                    print("%s end of input from macro %s Invoker: " \
                        "raising SourceEmpty()" \
                            % (assembler.eloc(self,"getLine",module=this_module),\
                                self.exp.name))
            # Tell LineBuffer object that this source is exhausted
            raise SourceEmpty()

        # Create a new physical line - eventually multiple physical lines will be
        # required of different continuation styles.
        assert isinstance(plines,list) and len(plines)>0,\
            "%s macro invocation must return a non-empty list of strings: %s" \
                % (assembler.eloc(self,"getLine",module=this_module),plines)

        if len(plines)>1:
            self.queued=plines[1:]  # Queue the extra lines for the next call

        # Return the first or only line
        pline=StreamLine(None,plines[0],genlvl=self.depth)
        if __debug__:
            if debug:
                print("%s returning: %s" \
                    % (assembler.eloc(self,"getLine",module=this_module),pline))

        return pline


#
#  +-------------------------------------+
#  |                                     |
#  |   Pysical Input Text Line Objects   |
#  |                                     | 
#  +-------------------------------------+
#

class PhysLine(object):
    conspaces=" "*15
    def __init__(self,source,content,genlvl=None):
        assert source is None or isinstance(source,Source),\
            "%s 'source' argumenet must be an instance of Source: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),source)
        assert isinstance(content,str),\
            "%s 'content' argumenet must be a string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),content)

        self.source=source      # Location of source content
        # This attribute is the basis for the Statement column in the assembly
        # listing.
        self.content=content    # a string, may be of length of 0
        # This tracks the source of generated physical lines by macros or open code
        # If None, the input comes from a file.  If 0 it comes from open code.
        # If 1 or more, it comes from a macro.  Used to determine if a macro statement
        # is an inner macro call or not for listing purposes.
        self.genlvl=genlvl      # If generated by assembler, level of generator

        # Established by subclass init() method
        self.cont=False         # Whether physical line is continued
        self.empty=False        # Phyiscal line is empty
        self.text=None          # Actual parsable content of the line

        # Physical line flags - set below in this __init__() method
        self.comment=False      # Physical line is a comment
        self.quiet=False        # Physical line is also a quiet comment

        # Field information - starting index of fields
        self.oper_start=None        # Set by LogLine.fields() method
        self.operand_start=None     # Set by Logline.fields() method
        self.comment_start=None     # Set by asmline.cfsm.ACT_Found_Comment() method

        # Make sure we do not process an empty physical line
        if len(self.content)==0:
            self.empty=True
            self.cont=False
            self.text=""
            return

        # Perform subclass initialization
        self.init()
        
        # Also do not process a line with an empty logical content (like some spaces)
        if len(self.text)==0:
            self.empty=True
            self.cont=False
            return

        # Complete base class initialization
        # Continuation of comment lines is never recognized so no continuation forced
        if self.text[0]=="*":
            self.comment=True
            self.cont=False
        elif len(self.text)>=2 and self.text[:2]==".*":
            self.comment=self.quiet=True
            self.cont=False

    def __str__(self):
        c=e=" "
        if self.cont:
            c='+'
        if self.empty:
            e=" "
        return '%s %s%s %s %s %s "%s"' % (self.source,c,e,\
            self.oper_start,self.operand_start,self.comment_start,self.text)

    # Performs generic initialization, called by subclass
    def init(self):
        raise NotImplementedError("subclass %s must provide init() method"\
            % self.__class__.__name__)

    # Test for physical line being a valid continuation line (for a previous
    # physical line)
    # Valid continuation lines must be at least 16 bytes of text and the first
    # 16 bytes must be spaces.
    # Return: True if valid continuation line
    #         False if not a valid continuation line and set.error to True
    def isContinuation(self):
        if len(self.text)<15 or self.text[:15]!=PhysLine.conspaces:
            return False
        self.operand_start=15   # Operand starts at index 15 (column 16)
        return True

class FixedLine(PhysLine):
    def __init__(self,source,content,genlvl=None):
        super().__init__(source,content,genlvl=genlvl)

    # Fixed physical line initialization
    # 1. Mark the line as empty if physical line content is zero.
    # 1. Determine if there is a continuation in column 72.  If there is no colume
    #    72 then blank is implied and no continuation
    # 2. Extract parsable text from columns 1-71, or less if line is shorter than
    #    71 columns
    # 3. Remove trailing trailing blanks from parsable text
    def init(self):
        self.cont=len(self.content)>=72 and self.content[71]!=" "
        text=self.content[:min(len(self.content),72)]
        self.text=text.rstrip()

class StreamLine(PhysLine):
    def __init__(self,source,content,genlvl=None):
        super().__init__(source,content,genlvl=genlvl)

    # Steam physical line initialization for non-empty lines
    # 1. Identify continuation as a backslash, \, in the last byte of string content
    # 2. Set parsable text, right hand spaces removed, not including an optional
    #    line continuation.
    def init(self):
        #print("content: '%s'" % self.content)
        if self.content[-1]=="\\":
            self.cont=True
            text=self.content[:-1]
            #print("text: '%s'" % text)
        else:
            self.cont=False
            text=self.content
        self.text=text.rstrip()


# This class buffers input lines in a LIFO stack of input sources.
#
#
# An individual line submitted by the Assembler.statement() method is pushed onto the
# stack, and then the stack buffer is processed until empty.  In most cases it will be
# just the one statement submitted with the statement() method.  If however, that one 
# statement is an include statement, the empty buffer will be filled with the included 
# statements and processing will continue.  Nested includes are not possible.
#
# Instance Arguments:
#    depth     The number of nested input sources supported
#    env       Environment variable defining file source directory search order
#    error     Report if a file source in included more than once.
#              (not yet implemented)
#
# Instance Methods:
#    end       Terminate additional input.  Called when END directive encountered
#    getline   Return a Line object from the current source.
#    newFile   Initiate a new file input source.  Used by INCLUDE directive or implied
#              inclusion for initial input source file.
class LineBuffer(object):
    source_type={"F":FileSource,"M":MacroSource}
    def __init__(self,depth=20,env="ASMPATH"):
        # Directory search order path manager
        self._opath=satkutil.PathMgr(variable=env,debug=False)
        self._env=env              # Environment variable used by this LineBufer
        self._depth=depth          # Supported depth of input sources.
        self._sources=[]           # List of input sources
        self._files=[]             # List of input files
        self._cur_src=None         # Current active source
        self._fileno=0             # Current file number
        self._lineno=0             # The previous global line number
        self._inject=None          # Injectable source queueing input lines
        # Master end of input switch.  It is set to True by an END statement
        self._end=False

    # Adds a source to nest of input sources and make it the current input source
    # This has the effect of interrupting the previous input, thereby inserting in
    # place the source lines from the new source.  When the newly added source
    # is exhausted, the interrupted source continues to provide its input.
    def __appendSource(self,src):
        self._sources.append(src)
        self._cur_src=src
        if src._typ=="F":
            src.fileno=len(self._files)+1
            self._files.append(src)

    # Source terminated, resume previous source
    # Method Argument:
    #   excp  If True a BufferEmpty exception is raised when all sources are empty.
    #         If False and all sources are empty, simply returns.  Defaults to True
    #         This argument is set to False when an explicit source is closed by
    #         closeSource() method.
    # Exceptions:
    #   BufferEmpty   Tells the assembler ALL input sources are exhausted. Only
    #         raised if excp argument is True.
    def __exhausted(self,excp=True):
        # Current source is done
        try:
            self._cur_src.fini()
        except SourceError as se:
            # This is a fatal uncaught exception
            raise assembler.AssemblerError(msg=se.msg) from None

        # Unnest one input source
        self._sources.pop()
        if len(self._sources)==0:
            if excp:
                raise BufferEmpty from None  # All sources done, tell the assembler
            else:
                return
        self._cur_src=self._sources[-1]
        # Unnested source becomes the current providing input

    # Initiate a new input source
    def __source(self,typ,sid,stmtno=None,srcno=0,fixed=False):
        if len(self._sources)>=self._depth:
            raise assembler.AssemblerError(line=stmtno,\
                msg="nested input source depth reached: %s" % self.depth)
        src_cls=LineBuffer.source_type[typ]
        srco=src_cls(typ,sid,srcno=srcno,fixed=fixed)
        try:
            srco.init(pathmgr=self._opath,variable=self._env)
        except SourceError as se:
            raise assembler.AssemblerError(line=stmtno,msg=se.msg) from None

        # Input source now ready to be used
        self.__appendSource(srco)

    # Closes the current input source and returns to previous source if any.
    # BufferEmpty is not raised even if all sources are empty.
    def closeSource(self):
        self.__exhausted(excp=False)

    # Terminate input acceptance.  No new lines or files accepted and requests for
    # lines by the assembler will fail if the buffer isn't empty.
    def end(self):
        self._end=True

    # Retrieve the next input Physical line object from the current source
    # Exceptions:
    #   BufferEmpty when all input is exhaused
    def getLine(self):
        if self._end:
            raise ValueError("%s input statements present after END statement" \
                % assembler.eloc(self,"getline"))

        # This while statement ends with:
        #   - a BufferEmtpy exception being raised (to tell assembler input is done)
        #   - an AssemblerError exception if current source can not be terminated
        #   - has received a Line object from the source.
        # This while statement recycles only when a source ends and a previous
        # source has been made the current source.  The recycle simply tries to
        # read from the unnested source, now the current source.
        while True:
            try:
                ln=self._cur_src.getLine(debug=False)
                # WARNING: this break is required!  DO NOT DELETE
                break
            except SourceEmpty:
                # Current source is done
                # A BufferEmpty exception is raised when all input is exhausted
                self.__exhausted()
                continue   # try reading from the unnested source now
            except asmmacs.MacroError as me:
                # A macro invocation will throw this error when a problem is detected
                # We catch it here so we can terminate the macro source.
                self.__exhausted()
                # Then we raise it again to allow the assembler to handle it
                raise me from None

        return ln

    # Returns the absolute path of the initial input file
    # A helper method for building system variable symbols involving the assembled
    # file
    # Returns:
    #   A Python string of the initial file's absolute path
    #   None  if no initial file (should not occur)
    def InputPath(self):
        if len(self._files) == 0:
            return None
        return self._files[0].fname

    # Initiate a new file input source
    def newFile(self,filename,stmtno=None,fixed=False):
        fname=filename
        # Detection of recursion requires work
        for src in self._sources:
            if src._typ!="F":
                continue
            if src.fname==fname:
                raise assembler.AssemblerError(line=stmtno,\
                    msg="nested file recursion encountered for file: %s" \
                        % (fname))
        # No recursion, safe to add as source
        self._fileno+=1
        self.__source("F",filename,srcno=self._fileno,fixed=fixed)

    # Initiate a new source of injected input statements
    def newInject(self,typ,sid,stmtno=None):
        assert self._inject is None,\
            "%s already queueing injectable source: %s" \
                % (assembler.eloc(self,"newInject",module=this_module),self._inject)

        self._inject=InjectableSource(typ,sid)

    # Initialize a new macro source for statements
    def newMacro(self,macro,stmtno=None,fixed=False):
        self.__source("M",macro,stmtno=stmtno,fixed=fixed)

    # Inject a line or list of lines
    def putline(self,line):
        if self._inject is None:
            cls_str=assembler.eloc(this_module,"putline")
            raise ValueError("%s InjectableSource not established" % cls_str)
        self._inject.inject(line)

    # Return a physical line to the current input source to be read again
    # Currently only support for file input sources.
    def queue(self,pline):
        self._cur_src.queue(pline)

    # Release injected source as input to the assembler.
    def release(self):
        if self._inject is None:
            cls_str=assembler.eloc(this_module,"release")
            raise ValueError("%s InjectableSource not established" % cls_str)
        self.__appendSource(self._inject)
        self._inject=None

# This encapsulates statement location information for consistent printing
class Source(object):
    def __init__(self,fileno=None,lineno=None,linepos=None):
        self.fileno=fileno
        self.lineno=lineno
        self.linepos=linepos
    def __str__(self):
        # This results in the following location strings
        # [lineno:position]-fileno
        # [lineno:position]          fileno is None
        # [lineno]-fileno            linepos is None
        # [lineno]                   fileno and linepos are None
        # or no position             fileno, line and linepos are all None
        string=""
        if self.linepos is not None:
            string="%s[%s:%s]" % (string,self.lineno,self.linepos)
            if self.fileno is not None:
                string="%s-%s" % (string,self.fileno)
        elif self.lineno is not None:
            string="%s[%s]" % (string,self.lineno)
            if self.fileno is not None:
                string="%s-%s" % (string,self.fileno)
        return string
    def clone(self):
        return Source(fileno=self.fileno,lineno=self.lineno,linepos=self.linepos)

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
