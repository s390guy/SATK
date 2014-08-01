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

# This module provides the foundation for handling raw stream file and generated 
# input by the ASMA assembler and the cards.py utility.  Multiple roles are required
# of these classes:
#  - process assembler continued raw lines into a logical line
#  - process macro invoked raw lines into a logical line using either assembler or
#    alternate conventions.
#  - Assist in printing input raw lines.
#  - How to handle alternate macro formats in the Macro Language is TBD????!!!
#
# Two concepts are employed by this module:
#  -  Raw lines are direct input from a single _text_ file of _ASCII_ data of varying
#     length, and
#  -  Logical lines which collapse one or more raw lines into one single Python string
#     for parsing.
#
# Both the assembler and the cards.py module extend the functionality provided here
# by performing additional processing of the input file (the cards.py utility) or 
# subclassing classes provided here for additional handling of input data (the
# assembler).
#
# Raw lines are concerned with indentification of active content destined for a 
# logical line:
#  - variable length content of the text after any line termination characters have
#    have been removed and spaces at the end of the line are removed
#  - the presence or absence of text content (content of length zero)
#  - the detection of comment lines (comments apply to just the raw input line)
#  - the detection of continuation of the raw line by another raw line.
#
# For the purposes of continuation detection, two strategies are employed:
#  - the 'legacy' use of a non-blank character in column 72 if present, and,
#  - the 'stream' approach that looks for the presence of a final character signaling
#    contination.
#
# Logical line creation is concerned with the extraction of the active input content
# from one or more raw lines.  How raw input becomes a logical line is dependent upon
# context.  Assembler directives and machine instructions simply use columns 16-71 in
# a continuation raw line to extend the previous logical line.  That's it.  Logical
# lines for a macro prototype statement or macro instruction invocation uses an
# optional alternate line format.
#
# The cards.py utility extends the handling of raw lines to support EBCDIC binary 
# input as well as ASCII.  It also performs validation of fixed format assembler fields
# and other aspects of the input.
#
# This module does not read any files.  It is the responsibility of the module user
# to actually provide to the input handler individual lines of ASCII text.  Line
# termination characters if present will be removed.

this_module="asmcards.py"

# Python imports: None
# SATK imports: None
# ASMA imports: None

#
#  +------------------------+
#  |                        |
#  |   Logical Line Error   |
#  |                        | 
#  +------------------------+
#

class LineError(Exception):
    def __init__(self,lineno,source=None,msg=""):
        self.msg=msg         # Text associated with the error
        self.lineno=lineno   # Lexical token where label occurs
        self.source=source   # Input source
        string="[%s]: %s" % (self.lineno,self.msg)
        super().__init__(string)


#
#  +-----------------------------+
#  |                             |
#  |   Raw Input from a Source   |
#  |                             | 
#  +-----------------------------+
#

class Raw(object):
    def __init__(self,card,lineno,source=None,stream="\\",maxsize=None):
        self.card=card                  # Raw ASCII input text without line term.
        self.lineno=lineno              # Input text line number (starting at 1)
        self.source=source

        # These attributes are determined by the Content() method
        # Actual ASCII content of the raw line with continuation
        self.content=None
        self.length=None                # Length of the content

        # Set to True if content is continued.  The continuation character
        self.continued=False
        self.first=False       # If continued, this is the first raw line
        self.middle=False      # If continued, this is a middle raw line
        self.last=False        # If continued, this is the last raw line
                               # If not continued, this is the only raw line

        # Just perform an inspection of the image detecting these conditions.  
        # Whether any of these conditions represents an error, only an analysis 
        # within the context of expected input can determine.
        
        # Set to True if the raw input is too long (only with LegacyRaw class)
        self.oversize=False
        # Set to True if the raw image has zero length or all spaces
        self.empty=False
        # Set to True for any type of comment
        self.comment=False
        # Set to True for only silent comments
        self.silent=False

        # Remove any line termination characters
        if len(card)>0 and card[-1]=="\n":
            self.card=content=card[:-1]
        else:
            self.card=content=card

        # Determine the lines content
        self.Content(content,stream=stream,maxsize=maxsize)
        size=self.length

        # Detect an empty image
        if size==0:
            self.empty=True
            return

        # Detect comment content
        if size>=2 and content[0:2]==".*":
            self.silent=True
            self.comment=True
            return
        if size>=1 and content[0]=="*":
            self.comment=True

    def __str__(self):
        silent=empty=content=cont="?"
        if isinstance(self,LegacyRaw):
            typ="L"
        elif isinstance(self,StreamRaw):
            typ="F"
        elif isinstance(self.StringRaw):
            typ="S"
        else:
            typ="?"
        if typ!="?":
            if self.continued:
                cont="X"
            else:
                cont="."
            if self.empty:
                empty="E"
            else:
                empty="."
            if self.comment:
                comment="*"
            else:
                comment="."
            if self.silent:
                silent="S"
            else:
                silent="." 
            if self.oversize:
                size="!"
            else:
                size="."
        string="%s: %s%s%s%s%s%s" % (self.lineno,typ,size,cont,empty,comment,silent)
        string="%s\n    [card]   ='%s'"   % (string,self.card)
        string="%s\n    [content]='%s'"   % (string,self.content)
        return string

    # Identifies content within the input.  It returns a tuple of the content as 
    # a string and the length as an integer: (string,length)
    def Content(self):
        cls=self.__class__.__name__
        cls_str="%s %s.isContinued() -" % (this_module,cls)
        raise NotImplementedError("%s subclass %s must provide Content() method" \
            % (cls_str,cls))

# Raw input from a legacy style input file with fixed boundaries
class LegacyRaw(Raw):
    def __init__(self,card,lineno,source=None,stream=None,size=80):
        super().__init__(card,lineno,source=source,stream=stream,maxsize=size)
        #print(self)

    # Detect continued statement by inspecting line position 72 for a non-blank
    # character.  Active content is anything preceding the continuation column
    # without any trailing spaces.
    #
    # A legacy non-continued raw line or the last raw line of a continued logical line.
    #
    #  col:  1                           71 72 73------------->
    # card: |   stuff is here              |  |    more stuff\n|
    #       |<-------------content-------->|<-----ignored*---->|  self.content
    #       |<---------------------card----------------------->|  self.card
    #
    # A legacy continued raw line. 'C' may be any non-blank character.
    #
    #  col:  1                           71 72 73------------->
    # card: |   stuff is here              | C|    more stuff\n|
    #       |<-------------content-------->|<-----ignored*---->|  self.content
    #       |<---------------------card----------------------->|  self.card
    #
    # The another continued line or final raw lne of a continued logical line.
    # The required 15 spaces at the beginning of the continued raw line is validated
    # during the construction of the logical line and then subsequently removed from
    # the active content.
    #
    #  col:  1         15 16             71 72 73------------->
    # card: |            |stuff is here    |C?|    more stuff\n|
    #       |<--------------content------->|<---ignored*------>|  self.content
    #       |<---------------------card----------------------->|  self.card
    #
    # * line termination characters, sequence columns or anything beyond sequence
    #   columns is ignored in content.
    # ** active content does not include the comment character if present.
    def Content(self,card,stream=None,maxsize=80):
        self.oversize=len(card)>maxsize
        if len(card)>=72:
            self.content=content=card[:71]       # content is columns 1-71
            self.continued=card[71]!=" "
        else:
            content=self.content=card
        self.empty=len(content.rstrip())==0
        self.length=len(card)

# Raw input from a stream type file without fixed bounadaries
class StreamRaw(Raw):
    def __init__(self,card,lineno,source=None,stream=None,size=80):
        super().__init__(card,lineno,source=source,stream=stream,maxsize=size)
        #print(self)

    # Detect continued if last character of the "card" is in the set of recognized
    # stream continuation characters.  Active content does not include the
    # continuation character or any spaces preceding it or at the end of the
    # non-continued input.
    #
    # A stream non-continued raw line or the last raw line of a continued logical line.
    #
    #  col:  1--------------------------------->
    # card: |   stuff is here                 \n|
    #       |<-------------content---------->| *|  self.content
    #       |<---------------card-------------->|  self.card
    #
    # A stream raw line.  'C' maybe any of the supplied stream continuation characters
    #
    #  col:  1--------------------------------->
    # card: |   stuff is here              |C|\n|
    #       |<-------------content-------->|   *|  self.content
    #       |<---------------card-------------->|  self.card
    #
    # A continued or last raw line of a continued stream logical line.
    # The required 15 spaces at the beginning of the continued raw line is validated
    # during the construction of the logical line and then subsequently removed from
    # the active content.
    #
    #  col:  1---------1516-------------------->
    # card: |            stuff is here    |C?|\n|
    #       |<-------------content---------->| *|  self.content
    #       |<---------------card-------------->|  self.card
    #
    # * line termination characters and continuation character are ignored in content.
    def Content(self,card,source=None,stream=None,maxsize=80):
        if len(card)>0 and card[-1] in stream:
            self.continued=True
            self.content=content=card[0:-1]
        else:
            self.content=content=card
        self.empty=len(content.rstrip())==0
        self.length=len(card)


#
#  +-------------------+
#  |                   |
#  |   Input Control   |
#  |                   | 
#  +-------------------+
#

# Processing of physical input lines into a logical line is context sensitive,
# controlled by the actual statement operation fields content.  This implies that the
# operation field must be identified and interpreted before the assembler can
# correctly construct the logical line or more correctly the parsable operation field.
# Assembler directives and machine instructions only support normal continuation
# lines, that is, characters starting in position 16 of the following physical line
# are concatenated at the location of the continuation character if the predecessor.
#
# Alternate line continuation allows for early recognition of the end of the operand
# field when an operand is followed by a comma and a space, ", ".  The following
# physical line is logically concatenated following the operand's comma.
#
# The fundamental parsing strategy of the assembler is to parse an entire logical
# line as a single entity.  Error reporting is standardized around the source of
# the line and the position within the line of the parsed lexical token.  The use
# of multiple physical lines for the creation of a single physical line requires the
# ability to map these locations appropriately to the raw line source and character
# positions.  This object captures this information for each raw line.

class InputCtrl(object):
    def __init__(self,alt=False):
        # Identifies if alternate continuation an option or not
        self.alt=alt
        self.parts=[]         # List of InputPart objects for this logical line
        
        # attributes used while building raw line location information
        self.end=0
        
    # Enable use of alternate line continuation conventions
    def alternate(self):
        self.alt=True 
        
    # Finds the source, lineno and position information of a specific position
    # within the logical line.
    # Returns a tuple:
    #   tuple[0]   The raw line position corresponding to the logical line pos
    #   tuple[1]   The raw lineno associated with the raw line
    #   tuple[2]   The raw line's source object
    def locate(self,lpos):
        found=None
        for p in self.parts:
            if lpos>p.end:
                continue
            else:
                found=p
                break
        if found is None:
            return (None,None,None)   
        # p is now the found
        rpos=lpos-p.end+p.rpos
        rlineno=p.rlineno
        rsource=p.source
        return (rpos,rlineno,rsource)

    # Builds the logical line
    # Method arguments:
    #   logical    The current logical line content as a string
    #   raw        The raw content being added to the logical line as a string
    #   rbegin     Position within the raw line where the raw content begins relative
    #              to zero, usually 0 or 15.
    def raw(self,logical,raw,rbegin,rlineno=None,rsource=None):
        # extract the actual content being added
        new="%s%s" % (logical,raw)
        end=len(new)-1
        ip=InputPart(end,rbegin,rlineno=rlineno,rsource=rsource)
        self.parts.append(ip)
        return new

# This class encapsulates location information mapping the end of a raw line's
# contribution to the logical line.
class InputPart(object):
    def __init__(self,lpos,rpos,rlineno=None,rsource=None):
        self.lend=lpos        # Position within the logical line where raw line ends 
        # Starting position within the raw line contributing to this part of the
        # logical line
        self.rpos=rpos     
        self.rlineno=rlineno  # The raw lineno of the contributing line
        self.rsource=rsource  # The source object pertaining to the contributing item
    def __str__(self):
        return "%s(lpos=%s,rpos=%s,rlineno=%s,rsource=%s)" \
            % (self.__class__.__name__,self.lend,self.rpos,self.rlineno,self.rsource)

# This class from the perspective of this module is simply the vehicle by which
# logical input lines are delivered to the module's user.  The module user must
# drive logical line validation and handle any LineError exceptions that may occur
# in the validation process.
class LogLine(object):
    def __init__(self):
        self.line=None         # Complete logical line as a Python string
        self.have_raw=False    # If True raw input lines are available.
        self.rawlines=[]
        self.error=False       # Set to True if error detected during validation
        self.ictl=InputCtrl()
        self.comment=None
        self.silent=None
        self.empty=None

    def __str__(self):
        if self.have_raw:
            hr="R"
            lineno=self.rawlines[0].lineno
        else:
            hr="."
            lineno="?"
        if self.error:
            er="!"
        else:
            er="."
        if self.comment is None:
            c="?"
        elif self.comment:
            c="*"
        else:
            c="."
        if self.silent is None:
            s="?"
        elif self.silent:
            s="S"
        else:
            s="."
        if self.empty is None:
            e="?"
        elif self.empty:
            e="E"
        else:
            e="."
        if self.line is None:
            return "%s%s%s%s%s [%s] None" % (hr,er,e,c,s,lineno)
        return "%s%s%s%s%s [%s] '%s'" % (hr,er,e,c,s,lineno,self.line)

    # Enable alternate continuation conventions
    def alternate(self):
        self.ictl.alternate()

    # Return the first raw line
    def first(self):
        return self.rawlines[0]

    def info(self):
        string="%s" % self
        for n in range(len(self.rawlines)):
            raw=self.rawlines[n]
            part=self.ictl.parts[n]
            string="%s\n%s" % (string,raw)
            string="%s\n    %s" % (string,part)
        return "%s\n" % string

    def validate(self):
        cls=self.__class__.__name__
        cls_str="%s %s.validate() -" % (this_module,cls)
        raise NotImplementedError("%s subclass %s must implement validate() method" \
            % (cls_str,cls))

class LogLineRaw(LogLine):
    spaces=" " * 15
    def __init__(self,lines):
        if not isinstance(lines,list):
            cls_str="%s %s.__init__() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'lines' argument must be a list: %s" \
                % (cls_str,lines))
        if len(lines)==0:
            cls_str="%s %s.__init__() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'lines' argument must not be an empty list" % cls_str)

        super().__init__()
        self.rawlines=lines
        self.have_raw=True
        first=self.first()
        self.comment=first.comment
        self.silent=first.silent
        self.empty=first.empty
        if self.comment:
            self.line=first.content.rstrip()
        if self.empty:
            self.line=""

    # Validates that the continued line has spaces in positions 1-15
    #                1111111
    # col   1234567890123456
    #                 111111
    # ndx   0123456789012345
    #       namefild opera operands
    def __ck_cont_spaces(self,raw):
        if raw.empty:
            raise LineError(raw.lineno,source=raw.source,msg=\
                "empty line invalid in continued line")
        # This assumes this is not an empty line
        if len(raw.content)<15:
            raise LineError(raw.lineno,source=raw.source,msg=\
                "positions 1 through 15 must be present in continued line, last "
                "position %s" % len(raw.content))
        if LogLineRaw.spaces!=raw.content[0:15]:
            raise LineError(raw.lineno,source=raw.source,msg=\
                "positions 1 through 15 must be blank in continued line, found '%s'" \
                     % raw.content[0:15])

    # This performs normal statement continuation lines
    def normal(self):
        #print("LogLineRaw.normal called")
        logical=""
        for n in range(len(self.rawlines)):
            r=self.rawlines[n]
            if n==0:
                # First or only line
                logical=self.ictl.raw(\
                    logical,r.content,0,rlineno=r.lineno,rsource=r.source)
            else:
                # Middle or last continued line
                end=len(r.content)
                if end>15:
                    content=r.content[15:]
                    logical=self.ictl.raw(\
                        logical,content,15,rlineno=r.lineno,rsource=r.source)

        # Save the logical line
        line=logical.rstrip()
        if len(line)==0:
            self.empty=True
        self.line=line

    def use_alt(self):
        return self.ictl.alt

    # Validate each of the lines within the logical line
    # Called by asminput.Line.__init__() method via asminput.Line.validate()
    def validate(self):
        for r in self.rawlines:
            if r.oversize:
                self.error=True
                card=r.card
                excess=card[72:]
                card=card[:72]
                raise LineError(r.lineno,source=r.source,msg=\
                    "oversize line: '%s|%s'" % (card,excess))

        first=self.rawlines[0]
        # Empty and comment lines must not be continued
        if first.empty and len(self.rawlines)>1:
            self.error=True
            raise LineError(first.lineno,source=first.source,msg=\
                "INTERNAL: empty line can not be continued")

        if first.comment and len(self.rawlines)>1:
            self.error=True
            raise LineError(first.lineno,source=first.source,msg=\
                "INTERNAL: comment may not be continued")

        if not first.continued:
            self.last=True
            return

        # Dealing with continued logical line
        active=""
        if len(self.rawlines)==1:
            self.error=True
            raise LineError(first.lineno,source=first.source,msg=\
                "INTERNAL: additional line(s) missing from continued line")
        last=len(self.rawlines)-1
        for n in range(len(self.rawlines)):
            raw=self.rawlines[n]
            if n==0:  
                # This is the first of the continued lines
                if not raw.continued:
                    self.error=True
                    raise LineError(raw.lineno,source=raw.source,msg=\
                         "INTERNAL: first or intermediate line not continued")
                raw.first=True
            elif n==last:
                # This is the last of the contineud lines
                if raw.continued:
                    self.error=True
                    raise LineError(raw.lineno,source=raw.source,msg=\
                        "final or additional continuation lines missing")
                self.__ck_cont_spaces(raw)
                raw.last=True
            else:
                # This is in the middle of the continued line
                if not raw.continued:
                    self.error=True
                    raise LineError(raw.lineno,source=raw.source,msg=\
                        "INTERNAL: intermediate line not continued")
                self.__ck_cont_spaces(raw)
                raw.middle=True

# The intent is to use this for generated statements.
class LogLineString(LogLine):
    def __init__(self,line):
        if not isinstance(line,StreamRaw):
            cls_str="%s %s.__init__() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'line' argument must be an instance of "
                "StreamRaw: %s" % (cls_str,line))

        super().__init__()
        self.rawlines=[line,]
        self.have_raw=True
        first=line
        self.comment=first.comment
        self.silent=first.silent
        self.empty=first.empty

    def normal(self):
        self.line=self.first().content
        #print("LogLineString line: '%s'" % self.line)

    def validate(self):
        pass

# This object manages the input for a single source of lines.  An instance of this
# object is required for each _concurrent_ input source.  See asminput.py for input
# source management.
class InputHandler(object):
    def __init__(self,legacy=LegacyRaw,stream=StreamRaw):
        self.legcls=legacy         # Legacy raw subclass
        self.strcls=stream         # Stream raw subclass
        
        # These attributes are set by the begin() method
        self.usecls=None           # Raw subclass to used for this use of the handler  
        self.stream=None           # Stream continuation character(s)
        self.size=None             # Maximum raw string size.
        self.cont=None             # List of raw input lines when being continued
        self.lineno=None           # Line number of current input source

    # Initiate the object for processing of an input source.
    def begin(self,legacy=False,stream="\\",size=80):
        if legacy:
            self.usecls=self.legcls  # Legacy raw line handling is in use
        else:
            self.usecls=self.strcls  # Stream raw line handling is in use.
        self.stream=stream           # Set the stream continuation character
        self.size=size               # Maximum legacy input record size
        self.cont=[]                 # Make sure there are no pending raw lines       
        self.lineno=0                # Reset the line no to zero.

    # This method clears the object for reuse with another source.  It will return 
    # the incomplete logical line as a Line object if any conitnued logical line is
    # not complete.  The Line object handles this condition.  If no pending raw
    # lines exist, it returns None
    def end(self):
        self.lineno=0
        if len(self.cont):
            line=LogLineRaw(self.cont)
            self.cont=[]
            return line

    # Returns a logical line object composed of one or more raw lines.  If a logical
    # line is being continued it returns None, until the logical line is complete.
    # The caller should continue to call this method with a new input string until
    # it returns a Line object.
    def text(self,string,lineno=None,source=None):
        if lineno is None:
            this_line=self.lineno=+1
        else:
            this_line=lineno
        raw=self.usecls(string,this_line,source=source,stream=self.stream,size=self.size)
        self.cont.append(raw)
        if not raw.oversize and raw.continued:
            return
        line=LogLineRaw(self.cont)
        self.cont=[]
        return line


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)