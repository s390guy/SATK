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

# Python imports
import os.path       # Access path tools by FileBuffer class

# SATK imports: None

# ASMA imports:
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
class FileSource(InputSource):
    def __init__(self,typ,filename,stmtno=None):
        super().__init__(typ,filename,stmtno=stmtno)
        self.fname=filename       # Text input file absolute path name
        self.eof=False            # Flag set at end-of-file
        self.fo=None              # Python file object
        self.lineno=None          # File line number
        self.fileno=None          # File number of this source

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
            cls_str=assembler.eloc(self,"getLine")
            raise ValueError("%s text file already at end-of-file: %s" \
                % (cls_str,self.fname))

        # Read a single line with universal newlines
        try:
            line=self.fo.readline()
        except OSError:
            raise SourceError("could not read from text file: %s" % self.fname) \
                from None

        # Test for normal end-of-file
        if len(line)==0:
            self.eof=True       # Remember the file is at end-of-file
            raise SourceEmpty() # Tell LineBuffer object that this source is exhausted.

        # Remove universal line end.  Assembler only wants the character text
        if line[-1]=="\n":
            line=line[:-1]
        self.lineno+=1
        ln=Line(line,lineno=self.lineno,fileno=1)
        return ln

    def init(self):
        if self.fo is not None:
            cls_str=assembler.eloc(self,"init")
            raise ValueError("%s file object already exists for file: %s" \
                % (cls_str,self.fname))
        try:
            self.fo=open(self.fname,"rt")
        except OSError:
            raise SourceError("could not open for reading text file: %s" % self.fname) \
                from None

        self.lineno=0

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

    def init(self): pass

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

# This class associates source information of a line with the text itself.
class Line(object):
    def __init__(self,line,lineno=None,fileno=None):
        self.text=line       # Source line of text
        self.lineno=lineno   # Global line number
        self.source=Source(fileno=fileno,lineno=lineno)
        self.psource=None    # This is used for printing source lines
    def __str__(self):
        string="%s" % self.source
        if len(string)>0:
            string="%s " % string
        return "%s%s" % (string,self.text)

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
    source_type={"F":FileSource}
    def __init__(self,depth=20):
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

    # Initiate a new input source
    def __source(self,typ,sid,stmtno=None,srcno=0):
        if len(self._sources)>=self._depth:
            raise assembler.AssemblerError(line=stmtno,\
                msg="nested input source depth reached: %s" % self.depth)
        src_cls=LineBuffer.source_type[typ]
        srco=src_cls(typ,sid,srcno)
        try:
            srco.init()
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
        #   - an BufferEmtpy exception being raised (to tell assembler input it done)
        #   - an AssemblerError exception if current source can not be terminated
        #   - has received a Line object from the source.
        # This while statement recycles only when a source ends and a previous
        # source has been made the current source.  The recycle simply tries to
        # read from the unnested source, now the current source.
        while True:
            try:
                ln=self._cur_src.getLine()
                break
            except SourceEmpty:
                # Current source is done
                try:
                    self._cur_src.fini()
                except SourceError as se:
                    raise assembler.AssemblerError(msg=se.msg) from None

                # Unnest one input source
                self._sources.pop()
                if len(self._sources)==0:
                    raise BufferEmpty from None  # All sources done, tell the assembler
                self._cur_src=self._sources[-1]
                continue   # try reading from the unnested source

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
        self._inject=InjectableSource(typ,sid,stmtno=stmtno)

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
