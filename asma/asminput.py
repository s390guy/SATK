#!/usr/bin/python3.3
# Copyright (C) 2014 Harold Grovesteen
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
import asmcards      # Logical line continuation handler
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

# An InputSource object raises this exception if it encounters a source related problem.
class SourceError(Exception):
    def __init__(self,msg):
        self.msg=msg
        super.__init__(msg)

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
        cls_str=assembler.eloc(self,"fini")
        raise NotImplementedError("%s subclass must provide fini() method" \
            % cls_str)

    # This method returns an Line object when requested by the LineBuffer.
    # When the source is exhausted it must raise a SourceEmpty exception.
    # If the source encounters a problem in producing the input line, is must raise
    # a SourceError exception.
    def getLine(self):
        cls_str=assembler.eloc(self,"getLine")
        raise NotImplementedError("%s subclass must provide getLine() method" \
            % cls_str)

    # Initialize the source if needed.  If not needed simply return
    # If the source is unsuccessful in initializing itself, it must raise a SourceError
    # exception.
    def init(self):
        cls_str=assembler.eloc(self,"init")
        raise NotImplementedError("%s subclass must provide init() method" \
            % cls_str)

# Manage a text file as an input source.
# Instance Arguments:
#    typ        Type of input source. Always 'F' supplied by LineBuffer
#    filename   A file name is the source id for a FileSource
#    legacy     Specify True to use legacy line continuation conventions.
#               Specify False to use stream line continuation conventions.
class FileSource(InputSource):
    def __init__(self,typ,filename,stmtno=None,srcno=None,legacy=False):
        super().__init__(typ,filename,stmtno=stmtno)
        self.rname=filename       # Text input file relative path or absolute path
        self.legacy=legacy        # True if legacy line contuation in use.
        self.fileno=srcno         # File number of this source
        self.fname=None           # Text absolute path from search path.
        self.eof=False            # Flag set at physical end-of-file
        self.leof=False           # Flas set when at logical end-of-file
        self.fo=None              # Python file object
        self.lineno=None          # File line number
        self.legacy=legacy        
        self.handler=asmcards.InputHandler()  # line continuation handler

    def fini(self):
        if self.fo is None:
            cls_str=assembler.eloc(self,"fini")
            raise ValueError("%s file object not created for file: %s" \
                % (cls_str,self.fname))
        try:
            self.fo.close()
        except OSError:
            raise SourceError("could not close input text file: %s" % self.fname) \
                from None

    def getLine(self):
        # Validate source state for getLine() method
        if self.fo is None:
            cls_str=assembler.eloc(self,"getLine")
            raise ValueError("%s file object not created for file: %s" \
                % (cls_str,self.fname))
        if self.eof:
            if self.leof:
                cls_str=assembler.eloc(self,"getLine")
                raise ValueError("%s text file already at end-of-file: %s" \
                    % (cls_str,self.fname))
            else:
                raise SourceEmpty()

        # Read a single line with universal newlines
        line=None
        while line is None:
            try:
                inline=self.fo.readline()
            except OSError:
                raise SourceError("could not read from text file: %s" % self.fname) \
                    from None
                    
            if len(inline)==0:
                self.eof=True
                line=self.handler.end()
                
                if line is None:
                    self.leof=True
                    raise SourceEmpty()
            else:
                self.lineno+=1
                line=self.handler.text(inline,\
                    source=Source(lineno=self.lineno,fileno=self.fileno))
                #print("line: %s" % line)

        # The line variable now contains an unvalidated logical line from which
        # actual active content has not been consolided by either the normal()
        # or stream() continuation conventions.
        ln=Line(line)
        return ln

    def init(self,pathmgr=None):
        if self.fo is not None:
            cls_str=assembler.eloc(self,"init")
            raise ValueError("%s file object already exists for file: %s" \
                % (cls_str,self.fname))
        try:
            self.fname,self.fo=pathmgr.ropen(self.rname)
        except ValueError:
            raise SourceError("could not open for reading text file: %s" % self.fname) \
                from None

        self.lineno=0
        self.handler.begin(legacy=self.legacy)

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

    def getLine(self):
        try:
            line=self.lines[0]
            del self.lines[0]
        except IndexError:
            raise SourceEmpty() from None
        return line

    def init(self,pathmgr=None): pass

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
    def __init__(self,typ,exp,stmtno=None):
        if not isinstance(exp,asmmacs.Invoker):
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s 'exp' argument must be an asmmacs.Expander object: "
                "%s" % (cls_str,exp))

        self.exp=exp          # asmmacs.Invoker object
        super().__init__(typ,exp.macro.name,stmtno=stmtno)
       
    def init(self,pathmgr=None):
        self.exp.mgr.nest(self.exp)
        self.exp.enter()

    def fini(self):
        # Clean up Invoker that is no longer needed.
        mm=self.exp.mgr
        mm.unnest()
        self.exp=None

    # Returns a generated macro line
    # Exception:
    #   MacroError if the macro detected a user error
    def getLine(self):
        # Throws a MacroError if a user error is detected
        line=self.exp.generate()

        if line is None:
            raise SourceEmpty() # Tell LineBuffer object that this source is exhausted.
        # Create logincal input line
        # Create a raw stream input "card".
        raw=asmcards.StreamRaw(line,None,stream="")
        logline=asmcards.LogLineString(raw)
        return Line(logline,macro=True)


# This class associates source information of a line with the text itself.
class Line(object):
    def __init__(self,line,lineno=None,source=None,typ="X",macro=False):
        if not isinstance(line,asmcards.LogLine):
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s 'line' argument must be an instance of "
                "asmcards.LogLine: %s" % (cls_str,line))
        if source is not None and not isinstance(source,Source):
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s 'source' argument must be an instance of Source: %s" \
                % (cls_str,source))

        # typ attribute controls how the line is processed by the assembler
        #   'B' --> This is a macro body statement
        #   'E' --> Expanded line (typ after expansion)
        #   'F' --> Text expansion failed, see self.merror for reason
        #   'P' --> This is a macro prototype statement
        #   'X' --> This is a normal input line and must be expanded by the current
        #           asmmacs.Expander object
        self.typ=typ         # Line type
        self.logline=line    # asmcards.LogLine object

        # THIS ATTRIBUTE IS USED FOR LISTING SOURCE CONTENT
        self.text=None       # Text of logical line of text
        
        self.lineno=lineno   # Global line number (The statement number in the listing)
        self.source=source   # Input source information
        self.psource=None    # This is used for printing source lines

        # Macro related information
        self.macro=macro     # If True, this line is a macro generated line
        self.merror=None     # MacroError exception if expansion failed

        self.comment=line.comment   # If True this is a comment statement
        self.silent=line.silent     # If comment and True, it is a silent comment
        self.empty=line.empty       # True if line is empty or all spaces
        
        # Validate the logical line.  LineError exceptions caught and reraised as
        # assembler errors which must be handled by Stmt instantiator
        self.validate()
        
        # Early comment and empty line detection
        if self.empty:
            self.text=""

    def __str__(self):
        string="%s" % self.source
        if len(string)>0:
            string="%s " % string
        return "%s %s %s" % (string,self.typ,self.text)

    # Return the first raw line of the logical line for statement classification
    def first(self):
        return self.logline.first()

    # Perform normal continuation conventions on logical lines raw input.
    def normal(self):
        logline=self.logline
        logline.normal()
        self.text=logline.line
        self.empty=logline.empty
        if self.text is None:
            print("Line.normal(): logline: %s" % (logline))

    # Returns the size of the prefix location information before printing
    def prefix(self):
        psource="%s" % self.source   # Make it printable
        self.psource=psource
        return len(psource)

    def print(self,locsize=None,string=False):
        loc="%s" % self.source
        if locsize is None:
            size=self.prefix()
        else:
            size=locsize
        st="%*s  %s" % (size,self.psource,self.text)
        if string:
            return st
        print(st)

    # Sets the external globally unique line number used in listings.
    def setLineNo(self,n):
        self.lineno=n

    # Validate the Logical Line object.
    def validate(self):
        logline=self.logline
        try:
            logline.validate()
        except asmcards.LineError as le:
            raise assembler.AssemblerError(source=le.source,line=self.lineno,\
                msg=le.msg) from None
        if self.comment:
            self.text=logline.line

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
#    error     Report if a file source in included more than once. (not yet implemented)
#
# Instance Methods:
#    end       Terminate additional input.  Called when END directive encountered
#    getline   Return a Line object from the current source.
#    newFile   Initiate a new file input source.  Used by INCLUDE directive or implied
#              inclusion for initial input source file.
class LineBuffer(object):
    source_type={"F":FileSource,"M":MacroSource}
    def __init__(self,depth=20):
        # ASMPATH search path manager
        self._opath=satkutil.PathMgr("ASMPATH",debug=False)
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
    # Exceptions:
    #   BufferEmpty   Tells the assembler ALL input sources are exhausted
    def __exhausted(self):
        # Current source is done
        try:
            self._cur_src.fini()
        except SourceError as se:
            # This is a fatal uncaught exception
            raise assembler.AssemblerError(msg=se.msg) from None

        # Unnest one input source
        self._sources.pop()
        if len(self._sources)==0:
            raise BufferEmpty from None  # All sources done, tell the assembler
        self._cur_src=self._sources[-1]
        # Unnested source becomes the current providing input

    # Initiate a new input source
    def __source(self,typ,sid,stmtno=None,srcno=0):
        if len(self._sources)>=self._depth:
            raise assembler.AssemblerError(line=stmtno,\
                msg="nested input source depth reached: %s" % self.depth)
        src_cls=LineBuffer.source_type[typ]
        srco=src_cls(typ,sid,srcno)
        try:
            srco.init(pathmgr=self._opath)
        except SourceError as se:
            raise assembler.AssemblerError(line=stmtno,msg=se.msg) from None

        # Input source now ready to be used
        self.__appendSource(srco)

    # Terminate input acceptance.  No new lines or files accepted and requests for
    # lines by the assembler will fail if the buffer isn't empty.
    def end(self):
        self._end=True

    # Retrieve the next input Line object from the current source
    def getline(self):
        if self._end:
            cls_str=assembler.eloc(self,"getline")
            raise ValueError("%s input statements present after END statement" \
                % cls_str)

        # This while statement ends with:
        #   - a BufferEmtpy exception being raised (to tell assembler input is done)
        #   - an AssemblerError exception if current source can not be terminated
        #   - has received a Line object from the source.
        # This while statement recycles only when a source ends and a previous
        # source has been made the current source.  The recycle simply tries to
        # read from the unnested source, now the current source.
        while True:
            try:
                ln=self._cur_src.getLine()
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

        self._lineno+=1
        ln.setLineNo(self._lineno)
        return ln

    # Initiate a new file input source
    def newFile(self,filename,stmtno=None):
        fname=os.path.abspath(filename)
        for src in self._sources:
            if src.typ!="F":
                continue
            if src.fname==fname:
                raise assembler.AssemblerError(line=stmtno,\
                    msg="nested file recursion encountered for file: %s" \
                        % (fname))
        # No recursion, safe to add as source
        self._fileno+=1
        self.__source("F",fname,stmtno=stmtno,srcno=self._fileno)

    # Initiate a new source of injected input statements
    def newInject(self,typ,sid,stmtno=None):
        if self._inject is not None:
            cls_str=assemlber.eloc(self,"newInject")
            raise ValueError("%s already queueing injectable source: %s" \
                % (cls_str,self._inject))
        self._inject=InjectableSource(typ,sid)

    # Initialize a new macro source for statements
    def newMacro(self,macro,stmtno=None):
        self.__source("M",macro,stmtno=stmtno)

    # Inject a line or list of lines
    def putline(self,line):
        if self._inject is None:
            cls_str=assembler.eloc(this_module,"putline")
            raise ValueError("%s InjectableSource not established" % cls_str)
        self._inject.inject(line)

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

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
