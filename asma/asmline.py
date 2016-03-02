#!/usr/bin/python3.3
# Copyright (C) 2015 Harold Grovesteen
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

# This module provides the interface between the assembler and all input processing
# of logical lines.  Logical lines require lable and operation field recognition
# early during input processing to determine how further to process the logical
# line. Processing these fields result in the creation of an LField object.
#
# Operands have further processing requirements depending upon statement format
# and the nature of the operands themselves.  Three different approaches to 
# operand field processing are possible.  The asmstmts.Stmt subclass associaed with
# the operation determines how processing is to be done for each physical line
# in the logical line.  Three class attributes influence the processing:
#
#    class.alt    - Indicating normal (False) or alternate (True) statement formats
#    class.sep    - Whether the entire field is processed (False) as an LOperands 
#                   object or operands should be separated (True) into LOperand 
#                   objects
#    class.spaces - Wheher spaces are allowed within an operand (True) or not 
#                   (False).  This causes LTerm objects to be created.
#
# Normal statements may or may not have operands separated.  Alternate statements
# always separate operands but with 
#
# Cases:
#   alt=False sep=False spaces=False  --   Some assembler directives
#   alt=False sep=True  spaces=False cfsm  Instructions, asm and mac directives.
#   alt=True  sep=True  spaces=False cfsm  Macro prototype and macro statements
#   alt=True  sep=True  spaces=True  mfsm  Macro directives
#
# In most cases, further parsing of the constituent objects (LField, LOperands,
# LOperand or LTerm) will be performed by Finite-State Machine based parser using
# lexical tokens.  Processing here simplifies parsing.

this_module="%s.py" % __name__

# Python imports:
import re          # Use regular expressions
# SATK imports
import fsm
#import fsmlexer
import lexer
# ASMA imports
import assembler
import asmbase
import asmtokens   # Need some lexical token types
import asminput    # Access the physical text input handler

#
#  +------------------------+
#  |                        |
#  |   Logical Line Error   |
#  |                        | 
#  +------------------------+
#

class LineError(Exception):
    def __init__(self,source=None,msg="",maclib=False):
        self.msg=msg         # Text associated with the error
        self.maclib=maclib   # Whether error created by MACLIBProcessor 
        self.source=source   # Input source
        if source is not None:
            string="%s: %s" % (self.source,self.msg)
        else:
            string=self.msg
        super().__init__(string)


#
#  +-------------------------------------------+
#  |                                           |
#  |   Logical Line Label or Operation Field   |
#  |                                           | 
#  +-------------------------------------------+
#

LABEL=asmtokens.LabelType()               # Normal label     - LABEL
MACLABEL=asmtokens.MacLabelType()         # Macro label      - LABEL&SYM
SEQSYM=asmtokens.SeqType()                # Sequence symbol  - .LABEL

class LField(asmbase.ASMString):
    #types={"L":LABEL, "M":MACLABEL,"Q":SEQSYM,"S":SYMREF}
    types={"L":LABEL, "M":MACLABEL,"Q":SEQSYM}
    def __init__(self,string,source,ndx,amp):
        assert string is not None,\
            "LField 'string' argument must be a string: %s" % string
        assert len(string)>=1,"LField 'string' argument must not be empty"

        super().__init__(string,start=asmbase.ASMPLoc(source=source,pndx=ndx),amp=amp)

        self.token=None      # Resulting match lexical token
        self.symid=None      # macopnd.SymbolRef object for the field

        # Field content type
        #  'L' -> A normal label
        #  'M' -> A macro model statement label
        #  'S' -> A symbolic variable
        #  'Q' -> A sequence symbol
        #  'U' -> unrecognized
        self.typ="U"         # Unrecognized type
        # Note that with typ "M", self.amp may still be True if there is a symbol
        # somewhere in the field.  The string has not at this point been validated
        # as a valid symbol until the validate() method is called

    def __str__(self):
        if self.amp:
            a="&"
        else:
            a=" "
        return '%s%s%s "%s"' % (self.start(),self.typ,a,self.text)

    def validate(self,asm,stmt,types,debug=False):
        typ="U"
        char=self.text[0]   # Get the first character for a quick sanity check
        for typ in types:
            
            if typ=="S":
                if char=="&":
                    # call back to the statement to do a full symbolic reference parse
                    result=stmt.validate_symbol(asm,self)
                    if result:
                        self.symid=result
                        self.amp=True
                        break
                    continue
                else:
                    continue
            elif typ=="Q" and char!=".":
                continue 

            ltyp=LField.types[typ]

            # Use a lexical token to validate types: L, M and Q
            try:
                if __debug__:
                    if debug:
                        print("%s matching '%s' to typ: %s" \
                            % (assembler.eloc(self,"validate",module=this_module),\
                                self.text,typ))
                self.token=ltyp.match(self.text)
                if __debug__:
                    if debug:
                        print("%s %s match succeeded" \
                            % (assembler.eloc(self,"validate",module=this_module),\
                                typ))
                break

            except lexer.LexerError:
                if __debug__:
                    if debug:
                        print("%s %s match failed" \
                            % (assembler.eloc(self,"validate",module=this_module),\
                                typ))
                continue

        if __debug__:
            if debug:
                print("%s %s match succeeded" \
                    % (assembler.eloc(self,"validate",module=this_module),typ))

        self.typ=typ

        if typ=="M":
            self.amp = self.token.groups()[1] is not None

        return
        
#
#  +------------------------------------------------------+
#  |                                                      |
#  |   Logical Line Complete Operand and Comment Fields   |
#  |                                                      | 
#  +------------------------------------------------------+
#

# This object contains the entire operand field across multiple physical lines.
# Some operations require all operands to be processed together, others can
# process operands separately.  The parser used against this object must recognize
# when the operands logically end.  This object is created when a asmstmts.Stmt
# subclass has the class attribute sep=False.
class LOperands(asmbase.ASMString):
    def __init__(self,pline):
        assert isinstance(pline,asminput.PhysLine),\
            "%s 'pline' argument must be an asminput.PhysLine object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),pline)
        assert pline.operand_start is not None,\
            "%s 'pline.operand_start' must not be None" \
                % assembler.eloc(self,"__init__",module=this_module)

        text=pline.text[pline.operand_start:]
        amp="&" in text
        loc=asmbase.ASMPLoc(source=pline.source,pndx=pline.operand_start)

        super().__init__(text,start=loc,amp=amp)

    def __str__(self):
        if self.amp:
            amp="&"
        else:
            amp=" "
        return "LOperands:%s %s" % (amp,self.display(string=True))

    # Add an additional physical line to logical operands
    def append(self,pline):
        assert isinstance(pline,asminput.PhysLine),\
            "%s 'pline' argument must be an asminput.PhysLine object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),pline)
        assert pline.operand_start is not None,\
            "%s 'pline.operand_start' must not be None" \
                % assembler.eloc(self,"__init__",module=this_module)
                
        loc=asmbase.ASMPLoc(source=pline.source,pndx=pline.operand_start)
        text=pline.text[pline.operand_start:]
        self.newloc(loc)
        self.text+=text
        self.amp = self.amp or "&" in text


#
#  +-------------------------------------------+
#  |                                           |
#  |   Logical Line Individual Operand Entry   |
#  |                                           | 
#  +-------------------------------------------+
#

# This object represents a single operand present in an operand field consisting of
# multiple operands.  A list of these objects is constructed when a asmstmts.Stmt
# subclass has the class attribute sep=True.
class LOperand(asmbase.ASMString):
    def __init__(self,string,source,ndx,onum):
        assert string is not None,\
            "LOperand 'string' argument must be a string: %s" % string
        assert len(string)>=1,"LOperand 'string' argument must not be empty"
        super().__init__(string,asmbase.ASMPLoc(source,ndx))

        self.onum=onum       # Operand number in the logical line
        #self.amp=False       # Ampersand seen in operand, symbols may be present

    def __str__(self):
        if self.amp:
            a="&"
        else:
            a=" "
        return '%s%s "%s"' % (self.start(),a,self.text)


#
#  +----------------------------------------+
#  |                                        |
#  |   Logical Line Individual Term Entry   |
#  |                                        | 
#  +----------------------------------------+
#

# This object represents a single term in an operand present in an operand field 
# consisting of multiple operands and complex terms.  A list of these objects is 
# constructed when a statement class has the class attribute sep=True and
# spaces=True.
class LTerm(asmbase.ASMString):
    def __init__(self,string,source,ndx,onum):
        assert string is not None,\
            "LOperand 'string' argument must be a string: %s" % string
        assert len(string)>=1,"LOperand 'string' argument must not be empty"
        super().__init__(string,asmbase.ASMPLoc(source,ndx))

        self.onum=onum       # Operand number in the logical line
        #self.amp=False       # Ampersand seen in operand, symbols may be present

    def __str__(self):
        if self.amp:
            a="&"
        else:
            a=" "
        return '%s%s "%s"' % (self.start(),a,self.text)


#
#  +----------------------------------------+
#  |                                        |
#  |   Logical Line Operand Field Parsers   |
#  |                                        | 
#  +----------------------------------------+
#


# This FSM parses the operands from a logical line using default operand recognition
# Default recognition applies to instructions, macro statements, and assembler
# directives.  Certain macro directives may require a directive specific parser.
#
# This character based parser processes the operand field of each physical line
# separating the operands from each other.  Each operand is represented by an
# LOperand object.  Omitted operands are represented by a None object.

class cstate(fsm.FSMState):
    def __init__(self,name):
        super().__init__(name,fsm=True)

class cfsm(fsm.FSM):
    def __init__(self,trace=False):
        super().__init__(trace=trace)
        self.initialize()       # Create states and actions

        # Parse parameters from parse() method
        self.spaces=False       # Whether spaces may be in operands

        # Parse specific attributes. Reset by start() method
        self.logline=None       # Current LogLine object being processed
        self.plines=[]          # Physical lines from the logical line
        self.lines=0            # Number of phyiscal lines in logical line
        self.pndx=None          # Next pline index to be processed
        self.operands=[]        # Recognized operands in logical line
        self.alfmt=False        # Whether alternate statement format in use
        self.attrs=""           # String of recognized attributes

        # Current operand attributes.  Set by state action methods.  Reset by start()
        self.opno=None          # Current LOperand being constructed
        self.squote=0           # Number of active single quotes ( 0 or 1 )
        self.lparens=0          # Number of lparens in operand
        self.rparens=0          # Number of rparens in operand
        self.operand=None       # Accumulated characters (None or string)
        self.amp=False          # Ampersand in operand, symbols may be present
        self.source=None        # Start of operand physical line source
        self.new_line=False     # Triggers a new line being added to the operand

        # Current phyiscal line attributes.  Set by line() method
        self.pline=None         # Current Physical line being processed
        self.text=None          # Current PhysLine.text string being processed
        self.cndx=None          # Index of next character in self.text

    # Add a new operand to the list of operands
    def add_operand(self):
        if self.opno is None:
            opnd=None
        else:
            opnd=self.opno
            opnd.amp=self.amp
        self.operands.append(opnd)
        self.operand=self.opno=None

    # Returns the next character of the logical line operands
    def char(self):
        c=None
        try:
            c=self.text[self.cndx]
            self.cndx+=1
        except IndexError:
            # End of physical text
            if self.pline.cont:
                self.line()   # Set up for next physical line processing
                #print("cndx: %s" % self.cndx)
                c=self.text[self.cndx]
                self.cndx+=1
        return c

    def check_operand(self):
        if self.squote:
            opnd=len(self.operands)+1
            raise LineError(source=self.pline.source,
                msg="logical operand %s: string missing terminating single quote" \
                    % opnd)

        if self.lparens==self.rparens:
            return
        #raise ValueError("operand %s: left parens, %s, does match right parens, %s" \
        #    % (len(self.operands)+1,self.lparens,self.rparens))
        opnd=len(self.operands)+1
        raise LineError(source=self.pline.source,\
            msg="logical operand %s: left parens, %s, does match right parens, %s" \
                % (opnd,self.lparens,self.rparens))

    def initialize(self):
        init=cstate("init")
        # Recognize possible symbol attributes that use a single quote and escape
        # to the attr state to process this case.  If we do not do this the single
        # quote will look like the start of a string.  Enter the attr state for this
        # Which attribute characters are recognized is actually controlled by the
        # parse() method's attrs argument.
        
        # Use the global attribute characters from asmtokens
        for c in asmtokens.ATTR:
            init.action(c,self.ACT_Attr)

        # a stand alone (not part of an attribute) single quote will indicate 
        # the start of a string.  Enter the instr state for this case
        init.action("'",self.ACT_String_Begin)

        # Recognize the end of an operand or sub-operand
        init.action(",",self.ACT_Comma)

        # Count parentheses so that we know if they are balanced or not
        init.action("(",self.ACT_LParen)
        init.action(")",self.ACT_RParen)
        
        # If an ampersand is seen, symbolic replacement may be needed
        init.action("&",self.ACT_Ampersand)

        # This means we are at the end of the operands and need to look for
        # where the comments start
        init.action(" ",self.ACT_Comment)
        init.error(self.ACT_Add_Char)
        self.state(init)

        # Process the single quote of an attribute or recognize that the preceding
        # possible attribute character was really just part of the operand.
        attr=cstate("attr")
        attr.action("'",self.ACT_Is_Attr)
        # The possible attribute character isn't an attribute because it was
        # followed by a parenthesis.  In this case we return to normal operand
        # parsing by count the parenthesis to make sure they are balanced
        attr.action("(",self.ACT_LParen)
        attr.action(")",self.ACT_RParen)
        attr.action(" ",self.ACT_Comment)
        attr.action(",",self.ACT_Comma)
        # Otherwise, whatever followed the possible attribute character wasn't
        # so we process it like a normal character and return from this post-attribute
        # character processing to the init state.
        attr.error(self.ACT_Not_Attr)
        self.state(attr)

        # Single quote detected so we will continue accumulating characters
        # until a single quote terminates the string
        instr=cstate("instr")
        instr.action("'",self.ACT_String_End)
        # If an ampersand is seen, symbolic replacement may be needed
        instr.action("&",self.ACT_Ampersand)
        instr.error(self.ACT_Add_Char)
        self.state(instr)

        # This looks for the start of a comment in the current physical line
        comment=cstate("comment")
        comment.action(" ",self.ACT_Find_Comment)
        comment.error(self.ACT_Found_Comment)
        self.state(comment)

        self.init("init")

    # Setup for first or following physical line of a logical line
    # Returns:
    #   True if physical line has an operand field
    #   False if physical line does not have an operand field
    def line(self,trace=False):
        assert self.pndx<self.lines,"pline index exceeds plines (%s): %s" \
            % (self.lines,self.pndx)
        self.pline=pline=self.plines[self.pndx]
        if __debug__:
            if trace:
                print("%s physical line: %r %s" \
                    % (assembler.eloc(self,"line",module=this_module),pline,pline))
        self.pndx+=1
        self.text=pline.text
        self.source=pline.source
        cndx=pline.operand_start
        if cndx is None:
            return False
        self.cndx=cndx
        self.new_line=True
        return True

    def look_ahead(self,chars):
        if self.cndx<len(self.text):
            c=self.text[self.cndx]
            return c in chars
        return False

    def new_operand(self):
        self.opno=None        # Flush LOperand opbject
        self.amp=False
        self.lparens=0
        self.rparens=0
        self.squote=0
        self.source=self.pline.source

    # Parse all physical line operand fields into LOperand objects.
    # Method Arguments:
    #   logline    The logical line (LogLine) object whose operands are being
    #              separated
    #   attrs      The symbol attributes allowed for the operation.  A string
    #              containing the allowed attributes.  The emty string implies
    #              all attributes (see asmtokens.ATTRS).  None implies no
    #              symbol or label attributes allowed.
    # Returns:
    #   list of LOperand objects corresponding to each logical operand
    # Exceptions:
    #   LineError  if unexpected number of single quotes or parenthesis mismatch
    def parse(self,logline,attrs="",spaces=False,alt=False):
        self.start(logline,attrs=attrs,spaces=spaces,alt=alt)

        # If initial line has no operands then just exit
        isline=self.line(trace=False)
        self.new_operand()

        if not isline:
            return []
        else:
            # Test for the case of a comma followed by a space indicating
            # comments are present on a statement without operands.
            opnd=self.cndx
            if len(self.text)>=opnd+2 and self.text[opnd:opnd+2]==", ":
                return []

        # Use FSM to parse operands
        while True:
            c=self.char()
            if c is None:
                break
            done=self.machine(c)
            if done:
                break

        # Make sure we add to the list the last operand
        if self.opno:
            self.check_operand()
            self.add_operand()
        return self.operands

    def start(self,logline,attrs="",spaces=False,alt=False):
        if attrs=="":
            self.attrs=asmtokens.ATTR
        elif attrs is None:
            self.attrs=""
        else:
            self.attrs=attrs
        self.spaces=spaces
        self.altfmt=alt
        self.logline=logline
        self.plines=logline.plines
        self.lines=len(self.plines)
        self.operands=[]
        self.pndx=0
        super().start()    # Start the FSM

    def ACT_Add_Char(self,value,state,trace=False):
        if self.opno:
            # Adding character to current operand
            self.opno+=value
            if self.new_line:
                loc=asmbase.ASMPLoc(self.source,self.cndx-1)
                self.opno.newloc(loc)
                self.new_line=False
        else:
            # Starting a new operand
            self.new_line=False
            self.opno=LOperand(value,self.source,self.cndx-1,\
                len(self.operands)+1)

        return state.state

    def ACT_Ampersand(self,value,state,trace=False):
        self.amp=True
        self.ACT_Add_Char(value,state,trace=trace)
        return state.state

    def ACT_Attr(self,value,state,trace=False):
        if value in self.attrs:
            self.ACT_Add_Char(value,state,trace=trace)
            return "attr"
        return self.ACT_Add_Char(value,state,trace=trace)

    def ACT_Comma(self,value,state,trace=False):
        if self.lparens!=self.rparens:
            # This is a suboperand separator, so include it in the operand
            self.ACT_Add_Char(value,state,trace=trace)
            return state.state
        # This is not a suboperand, but end of the operand
        self.add_operand()
        self.new_operand()
        if self.altfmt and self.pline.cont and self.look_ahead(" "):
            return "comment"
        return "init"

    def ACT_Comment(self,value,state,trace=False):
        # spaces allowed between parenthesis
        if trace:
            print("ACT_Comment: spaces:%s lparens:%s > rparens: %s" \
                 % (self.spaces,self.lparens,self.rparens))

        if self.spaces and self.lparens>self.rparens:
            self.ACT_Add_Char(value,state,trace=trace)
            return "init"
        self.check_operand()
        self.add_operand()
        return "comment"   # Find where comment starts if any

    def ACT_Find_Comment(self,value,state,trace=False):
        # found another space after operands, ignore it
        return "comment"

    def ACT_Found_Comment(self,value,state,trace=False):
        # Found start of comment, remember for other uses
        self.pline.comment_start=self.cndx-1
        # If alternate statement format continue operand recognition on next line
        if self.altfmt and self.pline.cont:
            self.line(trace=trace)
            return "init"
        # Parsing is done for standard statement format
        state.atend()

    def ACT_Is_Attr(self,value,state,trace=False):
        self.ACT_Add_Char(value,state,trace=trace)
        return "init"

    def ACT_LParen(self,value,state,trace=False):
        self.lparens+=1
        self.ACT_Add_Char(value,state,trace=trace)
        return "init"

    def ACT_Not_Attr(self,value,state,trace=False):
        self.ACT_Add_Char(value,state,trace=trace)
        return "init"

    def ACT_RParen(self,value,state,trace=False):
        self.rparens+=1
        self.ACT_Add_Char(value,state,trace=trace)
        return "init"

    def ACT_String_Begin(self,value,state,trace=False):
        self.squote+=1
        self.ACT_Add_Char(value,state,trace=trace)
        return "instr"

    def ACT_String_End(self,value,state,trace=False):
        self.squote-=1
        self.ACT_Add_Char(value,state,trace=trace)
        return "init"


#
#  +-------------------------+
#  |                         |
#  |   Single Logical Line   |
#  |                         | 
#  +-------------------------+
#

class LogLine(object):
    #                       label       sp       oper             sp
    fieldre=re.compile("(?P<label>[^ ]+)?([ ]+)(?P<oper>[^ ]+)(?P<sp>[ ]*)")
    def __init__(self,pline):
        assert isinstance(pline,asminput.PhysLine),\
            "LogLine object pline argument not a asminput.PhysLine object: %s" % pline

        self.plines=[pline,]     # Phyiscal lines on which the logical line is based
        # Make the input source of this logical line that of its first physical line
        self.source=pline.source
        # Generation level for the physical line
        self.genlvl=pline.genlvl
        # Logical line error status.  None or LineError exception
        self.error=None          # If exception, should be propagated upwards

        # Logical line field information - see fields() method.
        # No validation of the label or operation field validity has been made
        #.Any non-blank content is accepted at this point.
        self.label_fld=None      # Label field (LField object)
        self.oper_fld=None       # Operation field (LField object)
        self.opnd_fld=None       # Operand and comment fields (LOperands object)
        self.operu=None          # Operation field in upper case

        # Logical line operation information - see category() method.
        self.T="U"               # Type of statement based upon self.oper_fld
        self.spaces=False        # Whether spaces may be in operands
        self.sep=False           # Whether operands parsed into LOperand list
        self.alt=False           # Whether alternate statement format available
        self.optn=None           # Operation (ASMOper object)
        self.info=None           # operation information object (varies)

        # List of operands from the operand field
        self.operands=[]

        # Logical line status indicators from _initial_ physical line
        self.comment=pline.comment     # True is a comment
        self.quiet=pline.quiet         # True if also a quiet comment
        self.empty=pline.empty         # line has no content
        self.cont=pline.cont           # is continued
        # When True, logical line processing is complete
        self.ignore=self.comment or self.empty or self.error
        if self.ignore:
            return

        # Determine label and operation field contents
        # Operation field will drive further context sensitive processing:
        #   - line continuation convention
        #   - operand parsing
        #   - operand interpretation
        self.fields(pline)
   
    def __str__(self):
        m=c=r=" "
        if self.comment:
            if self.quiet:
                m="."
            else:
                m="*"
        elif self.empty:
            m="0"
        if self.error:
            r="E"
        if self.cont:
            c="+"
        first=self.plines[0]
        string="%s%s%s%s%s\n  label:%s\n  oper:%s\n  operands@%s:" \
            % (first.source,r,m,c,self.T,self.label_fld,self.oper_fld,\
                first.operand_start)
        if len(self.operands)==0:
            return "%s %s" % (string,self.opnd_fld) 
        for opnd in self.operands:
            if opnd is None:
                string="%s\n    %s" % (string,opnd)
            else:
                string="%s\n    %s" % (string,opnd.display(string=True))
        return string

    # Adds a physical line that continues the logical line
    # Returns:
    #   True if line successfully added
    #   False if line was not successfully added (a continuation issue)
    def addCont(self,pline,debug=False):
        cont=pline.isContinuation()

        if not cont:
            if __debug__:
                if debug:
                    print("%s cont: %s" \
                        % (assembler.eloc(self,"addCont",module=this_module),cont))
            return False

        self.plines.append(pline)
        if __debug__:
            if debug:
                print("%s plines: %s" \
                    % (assembler.eloc(self,"addCont",module=this_module),\
                        len(self.plines)))

        return True

    # Add operation specific information to the logical line.
    def category(self,oper,info=None):
        assert isinstance(oper,asmbase.ASMOper),\
            "'type' argument must be an instance of asmbase.ASMOper: %s" % oper

        self.optn=oper             # ASMOper object
        self.T=oper.stmtcls.typ    # Operation type from statement class

    # Determine label and operation field contents
    # Operation field will drive further context sensitive processing for:
    #   - statement format
    #   - operand parsing
    #   - operand interpretation
    def fields(self,pline,debug=False):
        text=pline.text
        mo=re.match(LogLine.fieldre,text)
        if mo is None:
            # If we are here there should be an non-blank operation field.  If
            # not something unexpected happened
            raise ValueError("%s pline: %s\n    field match failed, returned None" \
                % (assembler.eloc(self,"fields",module=this_module),pline))

        # match object returned
        groups=mo.groupdict()
        if __debug__:
            if debug:
                print("%s match groups: %s" \
                    % (assembler.eloc(self,"fields",module=this_module),groups))
        end=mo.end()
        
        label=groups["label"]
        if label:
            amp= "&" in label
            self.label_fld=LField(label,pline.source,0,amp)

        oper=groups["oper"]
        assert oper is not None,\
            "%s re failure: oper field not found by re: %s" \
                % (assembler.eloc(self,"fields",module=this_module),oper)

        oper_start=mo.start("oper")
        amp= "&" in oper
        pline.oper_start=oper_start
        self.oper_fld=LField(oper,pline.source,oper_start,amp)
        self.operu=oper.upper()

        if __debug__:
            if debug:
                print("%s pline: %s" \
                    % (assembler.eloc(self,"fields",module=this_module),pline))

        # Figure out if there are any operands and where they start in the first
        # (and required) physical line
        if end>=len(text):
            # Nothing beyond oper field except some spaces
            # No operands are present
            return
        pline.operand_start=end
        # Note where comments begin can not be determined until operands are parsed
        # and are sensitive to continuation convention used on the physical lines.
        if __debug__:
            if debug:
                print("%s pline: %s" \
                    % (assembler.eloc(self,"fields",module=this_module),pline))

    # Helper method for access to the starting position of the operand field
    # This method only works for a single line.  This needs fixing for continuation
    # lines.
    def operpos(self):
        return self.plines[0].operand_start


# This object manages all input processing, delivering logical lines to the
# assembler.  The line buffer supplied by the asminput module is used for physical
# interfacing with the platform's file system.
#
# Instance Arguments:
#   asm     The assembler.Assembler object
#   mb      The active asmmacs.MacroBuilder object
#   depth   The depth of included source files.  Defaults to 20.
#   env     The environment variable defining included file directory search order
#   pathmgr PathMgr object for LineMgr (used by LineBuffer object)
class LineMgr(object):
    def __init__(self,asm,mb,depth=20,env="ASMPATH",pathmgr=None):
        self.asm=asm           # Assembler object
        self.mb=mb             # MacroBuilder object
        self._end=False        # Set True when assembler encounters END

        # Physical line source manager
        self.LB=asminput.LineBuffer(depth=depth,env=env,pathmgr=pathmgr)

        # Universal Operand Field Parser
        self.fsm=cfsm(trace=False)

    # Reads individual physical lines from input sources and combines continued lines
    # into a single logical line.
    def __getLogical(self,debug=False):
        try:
            pline=self.LB.getLine()
            if __debug__:
                if debug:
                    print("%s pline: %s" \
                        % assembler.eloc(self,"__getLogical",module=this_module),\
                            pline)

        except asminput.SourceEmpty:
            return

        # Start a new logical line with this physical input.  Regardless of whether
        # it is continued or not, the first physical line's operation field
        # dictates all of the remaining processing of the statement.  Processing
        # of the label and operation field occurs during the instantiation of the
        # logical line (see the LogLine.fields() method).
        logical=LogLine(pline)

        while pline.cont:
            # Line is continued, so now add the next physical line
            try:
                pline=self.LB.getLine()
                if __debug__:
                    if debug:
                        print("%s pline: %s" \
                            % assembler.eloc(self,"__getLogical",module=this_module),\
                                pline)
            except asminput.SourceEmpty:
                logical.error=LineError(source=pline.source,\
                    msg="continuation line missing at end of file")
                break
                 # If the source is empty then previously continued physical
                 # line is missing a continuation
                 #raise ValueError("continuation line missing at end of file")
            contok=logical.addCont(pline)
            if __debug__:
                if debug:
                    print("%s contok from addCont: %s" \
                        % (assembler.eloc(self,"__getLogical",module=this_module),\
                            contok))

            if not contok:
                logical.error=LineError(source=pline.source,\
                    msg="invalid continuation line, previously continued line "
                        "rejected")
                self.LB.queue(pline)
            # Bad continue line so give up and assume it was meant to be a
            # new logical line and that is what follows.

        # Logical line is done, so process its operands
        self.categorize(logical)   # Determine the logical line's operation type
        return logical

    # Recognize the logical line's operation and update it with pertinent
    # operation processing information.  This information drives the assembler's
    # processing of statement format and operand recognition.
    def categorize(self,logical):
        assert isinstance(logical,LogLine),\
            "%s 'logical' argument must be a LogLine object: %s" \
                % (eloc(self,"categorize",module=this_module),logical)

        OMF=self.asm.OMF
        if logical.error:
            oper=OMF.getError()
        elif logical.comment or logical.empty:
            oper=OMF.getComment(quiet=logical.quiet)
        else:
            oper=logical.operu
            try:
                # Get the operation infomation, defining a macro from the macro
                # library if necessary.
                oper=OMF.getOper(oper,mbstate=self.mb.state,macread=True,\
                    lineno=logical.source,debug=False)
            except KeyError:
                # If the operation is unrecognized, categorize it as unknown
                logical.T="U"
                logical.ignore=True  # Unknown operations must be ignored.
                source=logical.plines[0].source
                logical.error=LineError(source=source,\
                    msg="Unrecognized operation field: %s" % oper)
                oper=OMF.getError()
            except LineError as le:
                # Failed library macro definitions must also be ignored
                logical.T="U"
                logical.ignore=True  # Unknown operations must be ignored.
                logical.error=le
                oper=OMF.getError()

        #if __debug__:
        #    if True:
        #        print("%s oper: %s" \
        #            % (assembler.eloc(self,"categorize",module=this_module),\
        #                oper))    

        # Update the logical line with this operation related information
        logical.category(oper)

    # The END directive has been encountered.  Only statements allowed after the
    # end directive are allowed now.
    def end(self):
        self._end=True

    # Parse into individual LOperand objects all of the operands across all
    # physical lines.
    def findOperands(self,logline,alt=False,attrs="",sep=False,spaces=False,\
                     debug=True):
        if __debug__:
            if debug:
                cls_str=assembler.eloc(self,"findOperands",module=this_module)
                print("%s sep:   %s" % (cls_str,sep))
                print("%s spaces:%s" % (cls_str,spaces))
                print("%s alt:   %s" % (cls_str,alt))

        #if logline.sep:
        if sep:
            # Separate the individual operands from the operand field in all
            # physical input lines
            self.fsm.trace(on=debug)
            logline.operands=self.fsm.parse(logline,\
                attrs=attrs,spaces=spaces,alt=alt)
            self.fsm.trace(on=False)
            if __debug__:
                if debug:
                    print("%s logline.operands: %s" % (cls_str,logline.operands))
        else:
            # Combine the operand fields and comment fields into a contiguous
            # string form one or more physical lines.
            # Note: this can not be used with alternate statement format
            opnds=None
            for n,pline in enumerate(logline.plines):
                if pline.operand_start is None:
                    break
                if n==0:
                    opnds=LOperands(pline)
                else:
                    opnds.append(pline)
            logline.opnd_fld=opnds
            if __debug__:
                if debug:
                    print("%s logline.opnd_fld: %s" % (cls_str,logline.opnd_fld))

    # Returns a logical line to the assembler.  
    def getLogical(self):
        logical=self.__getLogical()
        if logical is None:
            # signal end of input (should this be an exception?)
            return
        return logical
        
    # Return input file's absolute path
    def InputPath(self):
        return self.LB.InputPath()

    # Initiate a new file source
    def newFile(self,fname,stmtno=None,fixed=False):
        self.LB.newFile(fname,stmtno=stmtno,fixed=fixed)

    # Invoke a macro as a new statement source
    def newMacro(self,exp,stmtno=None):
        self.LB.newMacro(exp,stmtno=stmtno)

    
if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)