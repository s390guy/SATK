#!/usr/bin/python3.3
# Copyright (C) 2015, 2016 Harold Grovesteen
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

# This module implements macro symbolic variables, local and global, and 
# macro statement parameters. 

this_module="%s.py" % __name__

# Python imports:
import re
# SATK imports
import fsm
import pratt3
# ASMA imports
import assembler
import asmbase
import asmtokens


# This excpetion is used when a user when symbolic variable related errors occur.
#
# Instance Arguments:  All are optional and default to None if not supplied
#   msg     The nature of the error.
# Note: This object expects to be created by Invoker.error() method.
class SymbolError(Exception):
    def __init__(self,msg=""):
        self.msg=msg     # Nature of the error.
        super().__init__(self.msg)


# Base class for all Macro Variable Symbols and Macro Parameters
# Instance Arguments:
#   symbol   Name of the symbolic variable or macro statement parameter
#   value    An unsubscripted value (A_Val, B_Val or C_Val)
#            A subscripted symbolic variable (A_Array, B_Array or C_Array)
#            A macro statement parameter value (Parm_Val - underlying C_Val)
# Symbol attributes are defined within the value object, not the symbol itself
class Mac_Sym(object):
    def __init__(self,symbol,value,ro=False,unique=False):
        self.symbol=symbol
        self.value=value        # Value of this macro symbol and its attributes
        self.ro=ro              # Whether the value is read-only
        self.unique=unique
        # Set for symbols when defined. Used to filter symbols when MHELP 0x20 is set
        self.gbl=False          # Set for symbols when defined. Used to filter MHELP
        # Macro symbolic parameter. 
        self.parm=False         # Used to identify symbols when MHELP 0x10 is set

    def _ck_nosub(self,symid):
        if len(symid.indices)>0:
            raise SymbolError(msg="symbol is not subscripted: %s" % self.symbol)

    def _ck_sub(self,symid):
        if len(symid.indices)!=1:
            raise SymbolError(msg="symbol requires a subscript: %s" % self.symbol)

    def _ck_symid(self,symid):
        assert isinstance(symid,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"_ck_symid",module=this_module),symid)
        assert symid.var==self.symbol,\
            "%s symbol's variable name ('%s') does not match symbol name being " \
                "referenced: '%s'" \
                % (assembler.eloc(self,"_ck_symid",module=this_module),\
                    self.symbol,symid.var)
        return

    def _ck_value(self,value):
        assert isinstance(value,self.entrycls),\
            "%s 'value' argument must be an instance of %s: %s" \
                % (assembler.eloc(self,"_ck_value",module=this_module),\
                    self.entrycls.__name__,value)
        return
                
    def _ck_writable(self,user):
        assert (not user) or (not self.ro),\
            "%s symbol '%s' read-only, can not set value" \
                % (assembler.eloc(self,"_ck_writable",module=this_module),\
                    self.symbol)
        return

    # Return attributes of my value object
    def getAttr(self,attr):
        return self.value[attr]

    # Returns the symbol's value based upon SymbolID
    def getValue(self,symbol):
        if __debug__:
            self._ck_symid(symbol)
        self._ck_nosub(symbol)
        return self.value

    # Sets a value in the unsubscripted symbol based upon SymbolID object
    # Exceptions:
    # Note: Subclasses may need to override this method
    def setValue(self,symbol,value,user=True):
        # Note: after debugging, these checks should be eliminated.  All access
        # should be through the MacroSymbols object and the checks should occur there
        if __debug__:
            self._ck_symid(symbol)
            self._ck_value(value)
            self._ck_writable(user)
        self._ck_nosub(symbol)
        self.value=value


# Base class for all symbol values.
class Mac_Val(object):
    def __init__(self,value,ro=False):
        self.ro=ro
        self.attr=asmbase.ASMSymAttr()
        self._value=value

    # Returns the requested attribute
    def __getitem__(self,key):
        return self.attr[key]

    # Sets the specified attribute
    def __setitem__(self,key,item):
        self.attr[key]=item

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    # Parse the supplied string as a valid self-defining term.  This method is
    # used in two situations.
    #   1. A SETC symbol occurs in an arithmetic expression.  This is valid if
    #      the value of the symbol is a self-defining term.  This case uses 
    #      excp=True.
    #   2. Returning the type (T') attribute of a parameter or SETC symbol.
    # Method Arguments:
    #   pm       The parser manager from the Assembler object
    #   string   A string to be parsed
    #   excp     Whether an exception should be raised if the string is not a
    #            self-defining term.  Specify True to raise an exception.  Specify
    #            False to return None.  Defaults to False.
    # Returns:
    #   an integer corresponding to the string's self-defining term value
    #   None if the string is not a self-defining term and excp is True.
    # Exception:
    #   pratt3.PEvaluationError raised if string is not a self-defining term when
    #   excp is specified as True.
    def _parse_sdterm(self,pm,string,excp=False):
        assert isinstance(string,str),\
            "%s 'string' argument must be a string: %s" \
                % (assembler.eloc(self,"_parse_sdterm",module=this_module),string)
        if len(string)==0:
            if excp:
                raise pratt3.PEvaluationError(\
                    msg="empty string not a self-defining term")
            return None
        try:
            #sdscope=parsers.Parsers.sdterm.parse(string)
            sdscope=pm.parse_sdterm(string)
        except assembler.AsmParserError as mpe:
            if excp:
            # Convert to a pratt parser error 
                raise pratt3.PEvaluationError(msg=mpe.msg) from None
            else:
                return None
        # Convert the SDDEC, SDHEX, SDCHR or SDBIN lexical token into an integer
        return sdscope.sdtok.convert()

    # Retrieve a subsidiary value
    def fetch(self,item):
        raise NotImplementedError("%s subclass %s must provide fetch() method" \
            % (assembler.eloc(self,"fetch",module=this_module),\
                self.__class__.__name__))

    # This method returns a string used to replace the symbol in a model statement
    # Each subclass must provide this method
    def string(self):
        raise NotImplementedError("%s subclass %s must provide string() method" \
            % (assembler.eloc(self,"string",module=this_module),\
                self.__class__.__name__))

    # Update an underlying value.
    def update(self,item,value):
        raise NotImplementedError("%s subclass %s must provide update() method" \
            % (assembler.eloc(self,"update",module=this_module),\
                self.__class__.__name__))

    # This method returns the symbol's value when encoutered in a macro statement
    # Each subclass must provide this method
    def value(self):
        raise NotImplementedError("%s subclass %s must provide value() method" \
            % (assembler.eloc(self,"value",module=this_module),\
                self.__class__.__name__))


class MacroParm(object):
    def __init__(self,onum,value=None,keyword=None,positional=None,syslist=None):
        super().__init__()
        self.onum=onum      # Operand field operand number
        # Keyword parameter (not used for positional parameter)
        #  Prototype positional:    None
        #  Prototype keyword:       Keyword parameter name
        #  Positional parameter:    None
        #  Keyword parameter:       Keyword parameter name
        self.keyword=keyword

        # Positional parameter name symbol (not used for keyword parameter)
        #  Prototype positional:    Positional parameter name
        #  Prototype keyword:       None
        #  Positional parameter     None ( pos parm chosen by operand position)
        #  Keyword parameter        None
        self.positional=positional

        # Value varies based upon context:
        #  Prototype positional:  value is None
        #  Prototype keyword:     keyword's default value (str)
        #  Positional parameter:  value or empty string if omitted
        #  Keyword parameter:     Actual value or default (str)
        #  SYSLIST:               List of LString, LString subclass or None
        if syslist is not None:
            raise NotImplementedError("SYSLIST support to be developed")
            # Creating SYSLIST
            self.value=Parm_Val(ndx=0,sylist=syslist)
        else:
            self.value=value

    def __str__(self):
        return "MacroParm keyword:%s positional:%s value:%s" \
            % (self.keyword,self.positional,self.value)

    def display(self,indent="",string=False):
        s="%skeyword: %s positional: %s" % (indent,self.keyword,self.positional)
        lindent="%s    " % indent
        if self.value:
            s="%s\n%s%s" % (s,lindent,self.value.display(string=True))
        else:
            s="%s\n%s%s" % (s,lindent,self.value)
        if string:
            return s
        print(s)


class Parm_Sym(Mac_Sym):
    @staticmethod
    def Create(symid,ro=False,unique=False):
        return Parm_Sym(symid.var,ro=ro,unique=unique)

    def __init__(self,name,value=None,ro=False,unique=False):
        super().__init__(name,value,ro=True,unique=unique)
        self.entrycls=Parm_Val

    def getValue(self,symbol):
        if __debug__:
            self._ck_symid(symbol)
        try:
            return self.value.fetch(indices=symbol.indices)
        except SymbolError as se:
            # Add symbol name to error message and re-raise it
            raise SymbolError(msg="parameter %s - %s" % (self.symbol,se.msg)) \
                from None

    def setValue(self,symbol,value,user=True):
        super().setValue(symbol,value,user=False)


# This object represents recognized macro prototype or statement parameters.
# Instance Arguments:
#   value   A string that is the parameter's value or default
class Parm_Val(Mac_Val):
    attrs="KkNnTt"
    def __init__(self,value=None,onum=None,ndx=1,minimum=1,syslist=None):
        super().__init__(None,ro=True)
        self.syslist=syslist is not None
        self.onum=onum          # Operand number
        if value is None:
            self.cval=C_Val()
            self["T"]="O"
        else:
            self.cval=C_Val(value)
        self._value=self.cval
        #super().__init__(self.cval,ro=True)

        #print("MacroParmValue: %s" % self.value)
        self.ndx=ndx            # Index adjustment
        self.minimum=minimum    # Minimum index

        if self.syslist:
            self.sublists=syslist
        else:
            self.sublists=[]
            self.sublist(trace=False)       # This provides recursion for sublists

        # Set the N attribute
        self["N"]=len(self.sublists)
        self["K"]=self.cval["K"]

    def display(self,indent="",string=False):
        s='%sK:%s N:%s T:%s "%s"' \
            % (indent,self["K"],self["N"],self["T"],self.cval.string())
        if self.syslist:
            incr=0
        else:
            incr=1
        lindent="%s    " % indent
        for n,sub in enumerate(self.sublists):
            s='%s\n%s[%s] %s' \
                % (s,lindent,n+incr,sub.display(indent=lindent,string=True))
        if string:
            return s
        print(s)

    def fetch(self,indices=[],depth=0,debug=False):
        assert isinstance(indices,list),\
            "%s 'indices' argument must be a list: %s" \
                % (assembler.eloc(self,"fetch",module=this_module),indices)
        if __debug__:
            if debug:
                print("%s indices:%s depth:%s" \
                    % (assembler.eloc(self,"fetch",module=this_module),\
                        indices,depth))

        if len(indices)==0:      # Unsubscripted parameter or SYSLIST reference
            return self.cval
        ndxs=indices             # Subscripted parameter or SYSLIST reference

        if depth>=len(ndxs):
            raise SymbolError(msg="too many sublist subscripts: %s" % depth)

        this=ndxs[depth]
        if len(self.sublists)==0:
            # The requested sublist does not exist, so return an empty C_Val
            return C_Val()
        val=self.sublists[this-self.minimum]
        if depth==len(ndxs)-1:
            # Last requested index so return the retrieved sublist's C_Val object
            return val.value()
        # Not the last index so reach into the next level of sublist for its entry.
        return val.fetch(indices=ndxs,depth=depth+1)

    # Returns, recursively, the first sublist entry or only element of parameter
    # Returns:
    #   The C_Val object corresponding to the parameter's 'first' element
    def first(self):
        if len(self.sublists)==0:
            return self.cval
        return self.sublists[0].first()

    # This method recognizes a sublist within a parameter value.
    # Returns:
    #   None  if a sublist is not present
    #   A list containing a Parm_Val object if the sublist entry is present
    #         or None for an omitted sublist entry.
    # This method will be called by each instance of this class, until no sublist 
    # entries are found.
    def sublist(self,trace=False):
        string=self.cval._value
        #if len(self.value)<2 or self.value[0]!="(" or self.value[-1]!=")":
        if len(string)<2 or string[0]!="(" or string[-1]!=")":
            # no sublist in this parm, so exit
            return
        sublist=string[1:-1]  # Remove the beginning and ending parenthesis
        sublen=len(sublist)
        if __debug__:
            if trace:
                print('recognizing sublist len:%s : "%s"' % (sublen,sublist))

        if sublen==0:
            # Empty sublist
            self.sublists.append(Parm_Val(value="",onum=self.onum))
            return

        # Recognizer loop initialization
        attrs=Parm_Val.attrs  # Recognized symbol attributes
        state=1         # Current processing state
        ndx=0           # Index of the next character to be examined

        # Sublist specific values
        sub=""          # Current sublist being accumulated
        squote=0        # Number of unmatched single quotes
        lparens=0       # Number of left parentheses in sublist outside of quotes
        rparens=0       # Number of right parentheses in sublist outside of quotes
        issub=False     # Whether an embedded sublist is being recognized

        # Recognize sublist(s) in a string
        while ndx < sublen:
            c=sublist[ndx]
            ndx+=1     # Set the index for the NEXT character
            # Checking if starting an embedded sublist
            if __debug__:
               if trace:
                   print("state: %s [%s]: %s" % (state,ndx,c))

            # Examine beginning of the string.  Special handling for initial
            # sublist and empty sublist
            if state == 1:
                if c in attrs:       # Possible attribute character
                    sub+=c
                    state=3
                elif c == "(":       # This is an embedded sublist
                    issub=True
                    lparens+=1
                    sub+=c
                    state=2
                elif c == "'":        # Start of a quoted string
                    sub+=c
                    squote+=1
                    state=4
                elif c==",":          # Sublist entry separator
                    self.sublists.append(Parm_Val(value=sub,onum=self.onum))
                    sub=""
                    lparens=0
                    rparens=0
                    issub=False
                    #print("state 2 ,: issub %s" % issub)
                    state=1
                elif c == ")":        # Right parenthesis outside of quoted string
                    raise SymbolError("operand %s - sublist may not start with a "
                        "left parenthesis" % self.onum+1)
                else:
                    sub+=c
                    state=2

            # Recognizing remainder of the string for sublists
            elif state == 2:
                if c in attrs:   # Possible attribute character
                    sub+=c
                    state=3
                elif c == "'":        # Start of a quoted string
                    sub+=c
                    squote+=1
                    state=4
                elif c == "(":        # Left parenthesis outside of quoted string
                    sub+=c
                    lparens+=1
                    if ndx==0:
                        issub=True
                elif c == ")":        # Right parenthesis outside of quoted string
                    sub+=c
                    rparens+=1
                    #print("state 2 ): issub:   %s" % issub)
                    #print("state 2 ): lparens: %s" % lparens)
                    #print("state 2 ): rparens: %s" % rparens)
                    #print("state 2 ): ndx      %s" % ndx)
                    #print("state 2 ): sublen   %s" % sublen)
                    #if ndx<sublen-1:
                    #    print("state 2 ): next:    %s" % sublist[ndx])
                    #else:
                    #    print("state 2 ): next     EOS")
                    # Note: ndx already points to the next character
                    if issub and (lparens==rparens) and ndx< sublen and \
                       sublist[ndx]==",":
                         issub=False   # Found end of embedded sublist
                    #print("state 2 ): issub %s" % issub)
                elif c==",":          # Sublist entry separator
                    #print("state 2 ,: issub %s" % issub)
                    if issub:
                        sub+=c
                    else:
                        if squote!=0:
                            raise SymbolError(msg="operand %s sublist entry quoted "
                                "string missing terminating single quote"\
                                    % self.onum+1)
                        if lparens!=rparens:
                            raise SymbolError(msg="operand %s - sublist contains "
                                "umbalanced parenthesis: %s" % self.onum+1)
                        self.sublists.append(Parm_Val(value=sub,onum=self.onum))
                        
                        # Reset sublist related values
                        sub=""
                        lparens=0
                        rparens=0
                        issub=False
                        state=1
                else:
                    sub+=c

            # checking for attribute single quote 
            elif state == 3:
                sub+=c
                state=2
                if c == "'":      # Preceding character was an attribute (not string)
                    squote+=1
                elif c == "(":    # Left parenthesis outside of quoted string
                    lparens+=1
                elif c == ")":    # Right parenthesis outside of quoted string
                    rparens+=1

            # Checking for end of quoted string in sublist entry
            elif state == 4:
                # Checking for end of quoted string
                sub+=c
                if c == "'":     # End of quoted string
                    squote-=1
                    state=2

            # Unrecognized state
            else:
                raise ValueError("%s unexpected sublist state: %s" \
                    % (assembler.elod(self,"sublist",module=this_module),state))

        if squote!=0:
            raise SymbolError(\
                msg="operand %s - quoted string missing terminating single quote" \
                    % self.onum+1)
        if lparens!=rparens:
            raise SymbolError(msg="operand %s - umbalanced parenthesis: %s" \
                % self.onum+1)
        self.sublists.append(Parm_Val(value=sub,onum=self.onum))

    #def value(self):
        #return self._value
    #    return self.cval


# &SYSLIST subclass of generic Parm_Val object
# &SYSLIST is essentially a Parm_Val object that only has sublists.
#
# This subclass 
#  - uses Parm_Val.display() and Parm_Val.fetch() methods.
#  - does not use the Parm_val.sublist() method
class SYSLIST(Parm_Val):
    def __init__(self,label=None,posparms=[]):
        assert label is None or isinstance(label,str),\
            "%s 'label' argument must be a string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),label)
        # Build syslist
        if label is None:
            lbl=Parm_Val()
        else:
            lbl=Parm_Val(value=label)
        syslist=[lbl,]
        syslist.extend(posparms)

        super().__init__(ndx=0,minimum=0,syslist=syslist)


class lexfsm(fsm.FSM):
    def __init__(self,trace=False):
        super().__init__(trace=trace)

        # Current text being processed
        self.text=None          # Current text string being processed
        self.cndx=None          # Index of next character in self.text

    # The subclass manages the lexical analysis state of a new parse with attributes
    # supplied by this method
    def _init(self):
        raise NotImplementedError("%s subclass must provide _init() method" \
            % self.__class__.__name__)

    def add_part(self):
        raise NotImplementedError("%s subclass must provide add_part() method" \
            % self.__class__.__name__)

    # Moves to the next character in the text
    # Returns:
    #   the next character
    #   None if the processed text is exhausted
    def char(self):
        try:
            c=self.text[self.cndx]
            self.cndx+=1
        except IndexError:
            return None
        return c

    # Assesses whether part is valid for inclusion in result
    def ck_part(self):
        raise NotImplementedError("%s subclass must provide ck_part() method" \
            % self.__class__.__name__)

    # Tests whether the next character is one of these contained in a supplied string.
    #
    # Method Argument:
    #   chars   A string containing the set of characters against which the current
    #           character is tested
    # Returns:
    #   True    If the next character is in the string of tested characters
    #   False   If the next character is not in the string of tested characters or
    #           the current character is the last of the string
    def look_ahead(self,chars):
        if self.cndx<len(self.text):
            c=self.text[self.cndx]
            return c in chars
        return False
        
    # Establishes state for new part
    def new_part(self):
        raise NotImplementedError("%s subclass must provide new_part() method" \
            % self.__class__.__name__)

    # Run the finite state machine
    def runfsm(self):
        # Use FSM to parse operands
        while True:
            c=self.char()
            if c is None:
                break
            done=self.machine(c)
            if done:
                break

    # Preparse the lexical analysis by the finite state machine
    # Method Arguments:
    #   text    The string being parsed
    #   ndx     The position within the string at which the parsing begins.
    #           Defaults to 0, the first character.
    def start(self,text,ndx=0):
        self.text=text
        self.cndx=ndx
        # Actually starts the finite state machine
        super().start() 

# This object parses macro operands in either macro statements or macro prototypes
class MacroOperands(object):
    keyword=re.compile("%s=" % assembler.label)
    parm=re.compile("(&%s)(=)?" % assembler.label)
    def __init__(self,trace=False):
        # Parse parameters from parse() method
        #self.spaces=False       # Whether spaces may be in operands

        # Parse specific attributes. Reset by parse() method
        self.keyword=None       # Keyword of keyword macro parameter
        self.value=None         # Keyword or positional parameter value

    def parse(self,operand,proto=False):
        #assert isinstance(operand,(asmline.LOperand)),\
        #    "parse() method 'operand' argument must be an instance of LOperand: %r" \
        #        % operand
                
        self.keyword=None
        self.value=None
        
        # Test for keyword parameter
        text=operand.text
        if proto:
            mo=MacroOperands.parm.match(text)
            if mo is None:
                raise SymbolError(msg="operand %s invalid prototype "
                    "parameter: '%s'" % (operand.onum+1,text))
            # Have a valid prototype parameter
            groups=mo.groups()
            # Index 0 -> prototype parameter name
            # Index 1 -> equal sign of keyword prototype parameter 
            if groups[1] is None:
                # Have a positional parameter
                if mo.end() != len(text):
                    # Something did not match at the end
                    raise ValueError("operand %s positional parameter invalid: %s" \
                        % (operand.onum,text))
                # Good positional prototype parameter
                return MacroParm(operand.onum,positional=groups[0])
            # Have a keyword prototype parameter
            keyword=groups[0]
            value=text[mo.end():]   # Could be a zero length string
            return MacroParm(operand.onum,value=value,keyword=keyword)

        # Macro statement operand processing
        mo=MacroOperands.keyword.match(text)
        start_pos=0
        if mo is not None:
            # This is a keyword macro parameter
            start_pos=mo.end()
            self.keyword=text[:start_pos-1]  # Do not include equal sign of keyword
            self.value=text[start_pos:]      # The value is the remainder
            # Convert statement keyword parameter into a symbolic variable reference
            keyword="&%s" % self.keyword
            return MacroParm(operand.onum,value=self.value,keyword=keyword)
        else:
            # No keyword present so its a positional parmaeter.  The entire
            # operand string is the value
            self.keyword=None
            self.value=text
            return MacroParm(operand.onum,value=self.value)

    # Parse each operand and return the resulting list
    def parse_operands(self,stmt,proto=False,debug=False):
        # argument 'operands' is a list of asmline.LOperand objects derived from
        # parsers.parse_sep() method

        #print("%s operands: %s" \
        #    % (assembler.eloc(self,"parse_operands",module=this_module),operands))
        opnds=[]
        for n,opnd in enumerate(stmt.operands):
            if opnd is None:
                opnds.append(None)
                continue
            #print('parsing: "%s"' % opnd.text)
            parm=self.parse(opnd,proto=proto)
            #print(parm)
            if isinstance(parm,MacroParm):
                opnds.append(parm)
            else:
                raise ValueError("MacroParm not returned from parse: %s" % opnd)
        return opnds    # List of POperand objects or None if omitted


class ProtoParser(MacroOperands):
    def __init__(self,trace=False):
        super().__init__(trace=False)
        
    def parse_operands(self,stmt,debug=False):
        return super().parse_operands(stmt,proto=True,debug=debug)


#
#  +--------------------------+
#  |                          |
#  |   Macro Symbol Classes   |
#  |                          | 
#  +--------------------------+
#

class Mac_Sym_Array(Mac_Sym):
    def __init__(self,name,value,ro=False,unique=False):
        super().__init__(name,value,ro=ro,unique=unique)

    def _ck_sub(self,sub):
        if len(sub.indices)==1:
            return
        elif len(sub.indices)==0:
            raise SymbolError(msg="subscript required")
        raise SymbolError(msg="one subsript required, found: %s" % len(sub.indices))

    def _ck_value(self,value):
        assert isinstance(value,self.value.entrycls),\
            "%s 'value' argument must be an instance of %s: %s" \
                % (assembler.eloc(self,"_ck_value",module=this_module),\
                    self.value.entrycls.__name__,value)

    # Returns my value attibutes
    def getAttr(self,attr):
        return self.value.getAttr(attr)
        
    # Returns the symbol's value based upon an integer subscript.
    def getValue(self,symbol):
        if __debug__:
            self._ck_symid(symbol)       # AssertionError
            #self._ck_sub(symbol.sub)     # SymbolError
            self._ck_sub(symbol)         # SymbolError
        return self.value[symbol.sub]

    # Sets a value in the unsubscripted symbol based upon SymbolID object
    # Exceptions:
    #   IndexError if subscript is out of range
    def setValue(self,symbol,value,user=True):
        #print("%s symbol:%s value:%s user:%s" \
        #    % (assembler.eloc(self,"setValue",module=this_module),\
        #        symbol,value,user))

        # Note: after debugging, these checks should be eliminated.  All access
        # should be through the MacroSymbols object and the checks should occur there
        if __debug__:
            self._ck_symid(symbol)       # AssertionError
            self._ck_value(value)        # AssertionError
            self._ck_writable(user)      # AssertionError
            #self._ck_sub(symbol.sub)     # SymbolError
            self._ck_sub(symbol)         # SymbolError

        self.value[symbol.sub]=value


# Base class for all subscripted variable symbols value object
class Macro_Array(object):
    def __init__(self,size,entrycls):
        self.entrycls=entrycls   # Array entries must be of the class
        self.entries={}          # Sparse array using a dictionary
        self.size=size           # Defined size of the Array
        self.attr=asmbase.ASMSymAttr()
        self.attr["N"]=self.size

    # Retrieve a subscript's value
    # Exceptions:
    #   SymbolError  If index is out of range
    def __getitem__(self,key):
        assert isinstance(key,int),\
            "%s 'key' argument must be an integer: %s" \
                % (assembler.eloc(self,"__getitem__",module=this_module),key)
        # Detect out of range subscript
        if (self.size and key>self.size) or key<1:
            raise SymbolError(msg="subscript out of range(1-%s): %s" \
                % (self.size,key))

        # Return the subscripted value.  If the value is not present, return the
        # a value as initialized.
        try:
            return self.entries[key] 
        except KeyError:
            print("%s key not found: %s" \
                % (assembler.eloc(self,"__getitem__",module=this_module),key))
            return self.entrycls()

    # Set a subscript's value
    # Exceptions:
    #   SymbolError  If the subscript is out of range
    def __setitem__(self,key,item):
        assert isinstance(key,int),\
            "%s 'key' argument must be an integer >= 1: %s" \
                % (assembler.eloc(self,"__setitem__",module=this_module),key)
        assert isinstance(item,self.entrycls),\
            "%s 'item' argument must be of class %s: %s" \
                % (assembler.eloc(self,"__setitem__",module=this_module),\
                    self.entrycls.__name__,item)

        # Detect out of range subscript   
        if key>self.size or key<1:
            raise SymbolError(msg="subscript out of range (1-%s): %s" \
                % (self.size,key))

        # Set the new value
        self.entries[key]=item
        # Adjust N' to current maximum subscript
        self.attr["N"]=max(self.attr["N"],key)
        
    def getAttr(self,attr):
        return self.attr[attr]

class A_Sym_Array(Mac_Sym_Array):
    def __init__(self,name,size,ro=False,unique=False):
        super().__init__(name,A_Array(size),ro=ro,unique=unique)

class A_Array(Macro_Array):
    def __init__(self,size):
        super().__init__(size,A_Val)
        
class B_Sym_Array(Mac_Sym_Array):
    def __init__(self,name,size,ro=False,unique=False):
        super().__init__(name,B_Array(size),ro=ro,unique=unique)

class B_Array(Macro_Array):
    def __init__(self,size):
        super().__init__(size,B_Val)

class C_Sym_Array(Mac_Sym_Array):
    def __init__(self,name,size,ro=False,unique=False):
        super().__init__(name,C_Array(size),ro=ro,unique=unique)

class C_Array(Macro_Array):
    def __init__(self,size):
        super().__init__(size,C_Val)


# This object encapsulates a symbolic variable's reference.  The reference is used
# to define a local or global variable.  It is used to access a variable's value,
# represented by a subclass of SymbolValue.  No subscripting, numeric subscripting
# and variable subscripting are all supported.
#
# Case sensitivity is managed via the 'variable' argument.  Case must be established
# when the object is created.  While migrating to index access, indices take
# precedence over use of subscript.
class SymbolID(object):
    def __init__(self,variable,indices=[],subscript=0):
        assert isinstance(variable,str) and len(variable)>0,\
            "%s 'variable' argument must be a non-empty string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),variable)
        assert variable[0]=='&',\
            "%s 'variable' argument must start with an '&': '%s'" \
                % (assembler.eloc(self,"__init__",module=this_module),variable)

        self.var=variable        # The symbolic symbols's name (with '&')
        self.indices=indices     # Variable number of integer indices.
        self.sub=None            # Integer of array subscript

        if len(indices)==1:
            self.sub=indices[0]

    def __str__(self):
        return "%s(variable=%s,subscipt=%s,indices=%s)" \
            % (self.__class__.__name__,self.var,self.sub,self.indices)
            
    # This method is used to provide a user friendly string of the symbol reference
    # object.  Primarily used for error reporting.
    def display(self):
        if len(self.indices)==0:
            return self.var
        indices=""
        for n in self.indices:
            indices="%s,%s" % (indices,n)
        indices=indices[1:]  # Drop off initial comma
        return "%s(%s)" % (self.var,indices)

    def indexing(self):
        return len(self.indices)!=0

    # Returns the number of list elements required for a definition
    # For an unsubscripted variable one element is created in the value list, 0+1
    # For a subscripted variable, n+1 elements are created. This also creates an
    # unsubscripted value allowing dual usage.
    def length(self):
        return self.sub+1


# GBLA or LCLA Arithmetic Macro Variable Symbol
class A_Sym(Mac_Sym):
    @staticmethod
    def Create(symid,ro=False,unique=False):
        sub=symid.sub
        if sub is None or sub == 0:
            return A_Sym(symid.var,ro=ro,unique=unique)
        return A_Sym_Array(symid.var,sub,ro=ro,unique=unique)

    def __init__(self,symbol,ro=False,unique=False):
        super().__init__(symbol,A_Val(),ro=ro,unique=unique)
        self.entrycls=A_Val

class A_Val(Mac_Val):
    def __init__(self,value=0):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer: '%s'" \
                % (assembler.eloc(self,"__init__",module=this_module),value)

        super().__init__(value)
        self["T"]="N"

    #
    # Infix Arithmetic Operations
    #

    # Addition
    def __add__(self,other):
        return A_Val(self.value() + self.__other(other))
    def __radd__(self,other):
        return A_Val(self.__other(other) + self.value())

    # Division (true division handled the same a floor division)
    def __floordiv__(self,other):
        return A_Val(self.value() // self.__other(other))
    def __rfloordiv__(self,other):
        return A_Val(self.__other(other) // self.value())
    def __truediv__(self,other):
        return self.__floordiv__(other)
    def __rtruediv__(self,other):
        return self.__rfloordiv(other)

    # Multiplication
    def __mul__(self,other):
        return A_Val(self.value() * self.__other(other))
    def __rmul__(self,other):
        return A_Val(self.__other(other) * self.value())

    # Subtraction
    def __sub__(self,other):
        return A_Val(self.value() - self.__other(other))
    def __rsub__(self,other):
        return A_Val(self.__other(other) - self.value())

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    #
    # Unary Arithmetic Operations
    #

    # Unary minus
    def __neg__(self):
        return A_Val(-self.value())

    # Unary plus
    def __pos__(self):
        return A_Val(self.value())

    #
    # Infix Comparison Operations
    #
    def __lt__(self,other):
        return self.value() < self.__other(other)
    def __le__(self,other):
        return self.value() <= self.__other(other)
    def __eq__(self,other):
        return self.value() == self.__other(other)
    def __ne__(self,other):
        return self.value() != self.__other(other)
    def __ge__(self,other):
        return self.value() >= self.__other(other)
    def __gt__(self,other):
        return self.value() > self.__other(other)  

    # Returns the integer value of the operand
    # Exception:
    #   ValueError if operand is neither an integer nor an A_Val object
    def __other(self,other):
        if isinstance(other,(A_Val,B_Val)):
            return other.value()
        if isinstance(other,int):
            return other
        if isinstance(other,C_Val):
            return other.sdterm()
        raise pratt3.PEvaluationError(\
            msg="operation not supported between an arithmetic value and %s" % other)

    # Returns the object's value as a string
    def string(self):
        return "%s" % self._value

    # Updates the object's value from either an integer or another A_Val object
    def update(self,value):
        if isinstance(value,A_Val):
            self._value=value.value()
        elif isinstance(value,int):
            self._value=value
        else:
            cls_str=assembler.eloc(self,"update",module=this_module)
            raise ValueError("%s 'value' argument must be an integer: '%s'" \
                % (cls_str,value))

    # Returns the A_Val object's integer value
    def value(self):
        return self._value

# GBLB or LCLB Binary Macro Variable Symbol
class B_Sym(Mac_Sym):
    @staticmethod
    def Create(symid,ro=False,unique=False):
        sub=symid.sub
        if sub is None or sub == 0:
            return B_Sym(symid.var,ro=ro,unique=unique)
        return B_Sym_Array(symid.var,sub,ro=ro,unique=unique)

    def __init__(self,symbol,ro=False,unique=False):
        super().__init__(symbol,B_Val(),ro=ro,unique=unique)
        self.entrycls=B_Val


class B_Val(Mac_Val):
    values={True:1,False:0,1:1,0:0}
    def __init__(self,value=0):
        val=self.__check(value)
        super().__init__(val)
        self["T"]="N"

    # Addition
    def __add__(self,other):
        return A_Val(self.value() + self.__other(other))
    def __radd__(self,other):
        return A_Val(self.__other(other) + self.value())

    # Division (true division handled the same a floor division)
    def __floordiv__(self,other):
        return A_Val(self.value() // self.__other(other))
    def __rfloordiv__(self,other):
        return A_Val(self.__other(other) // self.value())
    def __truediv__(self,other):
        return self.__floordiv__(other)
    def __rtruediv__(self,other):
        return self.__rfloordiv(other)

    # Multiplication
    def __mul__(self,other):
        return A_Val(self.value() * self.__other(other))
    def __rmul__(self,other):
        return A_Val(self.__other(other) * self.value())

    # Subtraction
    def __sub__(self,other):
        return A_Val(self.value() - self.__other(other))
    def __rsub__(self,other):
        return A_Val(self.__other(other) - self.value())

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    #
    # Unary Arithmetic Operations (not supported with character values)
    #

    # Unary minus
    def __neg__(self):
        return A_Val(-self.value())

    # Unary plus
    def __pos__(self):
        return A_Val(self.value())
        
    #
    # Infix Comparison Operations
    #
    def __lt__(self,other):
        return self.value() < self.__other(other)
    def __le__(self,other):
        return self.value() <= self.__other(other)
    def __eq__(self,other):
        return self.value() == self.__other(other)
    def __ne__(self,other):
        return self.value() != self.__other(other)
    def __ge__(self,other):
        return self.value() >= self.__other(other)
    def __gt__(self,other):
        return self.value() > self.__other(other)    

    def __check(self,value):
        try:
            val=B_Val.values[value]
        except KeyError:
            if isinstance(value,int):
                if value:
                    val=1
                else:
                    val=0
            else:
                cls_str=assembler.eloc(self,"__check",module=this_module)
                raise ValueError("%s 'value' argument for binary symbol '%s' "
                    "invalid: %s" % (cls_str,symbol,value))
        return val

    # Returns the integer value of the operand
    # Exception:
    #   ValueError if operand is neither an integer nor an A_Val object
    def __other(self,other):
        if isinstance(other,(A_Val,B_Val)):
            return other.value()
        if isinstance(other,int):
            return other
        if isinstance(other,C_Val):
            return other.sdterm()
        raise pratt3.PEvaluationError(\
            msg="operation not supported between a binary value and %s" % other)
        
    def string(self):
        return "%s" % self._value 
        
    def update(self,value):
        if isinstance(value,B_Val):
            self._value=value.value()
        else:
            val=self.__check(value)
            self._value=val

    def value(self):
        return self._value

# GBLC or LCLC Binary Macro Variable Symbol
class C_Sym(Mac_Sym):
    @staticmethod
    def Create(symid,ro=False,unique=False):
        sub=symid.sub
        if sub is None or sub == 0:
            return C_Sym(symid.var,ro=ro,unique=unique)
        return C_Sym_Array(symid.var,sub,ro=False,unique=unique)

    def __init__(self,symbol,ro=False,unique=False):
        super().__init__(symbol,C_Val(),ro=ro,unique=unique)
        self.entrycls=C_Val


class C_Val(Mac_Val):
    # Regular expression for validating the value is a valid assembler label string
    label=re.compile(assembler.label)

    @staticmethod
    def Create(value=""):
        return C_Val(value)

    def __init__(self,value=""):
        assert isinstance(value,str),\
            "%s 'value' argument must be a string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),value)

        super().__init__(value)
        self.__setK()
        self.__translate()
        # This is set when a self-defining term is recognized during arithmetic
        # expression processing of this SETC symbol value.
        # See asmfsmbp.PLitSym.avalue() method.
        
        # Whether the current value has been parsed as a self-defining term
        self._sdparse=False
        # Value as an integer of the self-defining term
        self._sdvalue=None    # If previously parsed and still None, not valid

    def __str__(self):
        return '%s("%s")' % (self.__class__.__name__,self._value)
        
    #
    # Infix Arithmetic Operations
    #

    # Addition
    def __add__(self,other):
        return A_Val(self.sdterm() + self.__other_arith(other))
    def __radd__(self,other):
        return A_Val(self.__other_arith(other) + self.sdterm())

    # Division (true division handled the same a floor division)
    def __floordiv__(self,other):
        return A_Val(self.sdterm() // self.__other_arith(other))
    def __rfloordiv__(self,other):
        return A_Val(self.__other_arith(other) // self.sdterm())
    def __truediv__(self,other):
        return self.__floordiv__(other)
    def __rtruediv__(self,other):
        return self.__rfloordiv(other)

    # Multiplication
    def __mul__(self,other):
        return A_Val(self.sdterm() * self.__other_arith(other))
    def __rmul__(self,other):
        return A_Val(self.__other_arith(other) * self.sdterm())

    # Subtraction
    def __sub__(self,other):
        return A_Val(self.sdterm() - self.__other_arith(other))
    def __rsub__(self,other):
        return A_Val(self.__other_arith(other) - self.sdtern())

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    #
    # Unary Arithmetic Operations
    #

    # Unary minus
    def __neg__(self):
        return A_Val(-self.sdtern())

    # Unary plus
    def __pos__(self):
        return A_Val(self.sdterm())

    #
    # Infix Comparison Operations
    #
    
    # If the comparison with another SETC symbol or string

    def __lt__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm < othr
        return self.value() < othr
    def __le__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm() <= othr
        return self.value() <= othr
    def __eq__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm() == othr
        return self.value() == othr
    def __ne__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm() != othr
        return self.value() != othr
    def __ge__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm() >= othr
        return self.value() >= othr
    def __gt__(self,other):
        othr=self.__other_char(other)
        if isinstance(other,int):
            return self.sdterm() > othr 
        return self.value() > othr

    # Returns an integer of the other operand
    # Exception:
    #   PEvaluationError if operand can not be used in an arithmetic operation
    def __other_arith(self,other):
        if isinstance(other,(A_Val,B_Val)):
            return other.value()
        if isinstance(other,int):
            return other
        raise pratt3.PEvaluationError(\
            msg="arithmetic operation not supported between a character value and %s" \
                % other)

    # Returns the othr value as an EBCDIC string for use in comparison operations
    # between character objects or the self-defining term is comparison is with
    # a numeric operand (binary or arithemetci SET symbol).
    # Exception:
    #   PEvaluationError if operand can not be compared
    def __other_char(self,other):
        if isinstance(other,C_Val):
            return other.value()
        if isinstance(other,str):
            return assembler.CPTRANS.a2e(other)
        if isinstance(other,(A_Val,B_Val)):
            return other.value()
        raise pratt3.PEvaluationError(\
            msg="comparisonoperation not supported between a character value and %s" \
                % other)

    def __setK(self):
        self.attr["K"]=len(self._value)

    def __translate(self):
        self._ebcdic=assembler.CPTRANS.a2e(self._value)

    # Returns True or False depending upon whether the character value is a label
    def islabel(self,debug=False,trace=False):
        mo=C_Val.label.match(self._value)
        if mo is None:
            return False
        # If matching substring is the same as the value, it is a label
        return mo.group()==self._value

    # Returns an integer (and remembers it) if this C_Val object is a self
    # defining term.
    # Method Arguments:
    #   excp    Specify whether an exception is raised if the value is not a 
    #           self.defining term.  Specify True to generate an exception.
    #           Specify False to return None.  Defaults to False.
    # Returns:
    #   an integer corresponding to the value of the self-defining term
    # Exception:
    #   PEvaluationError if symbol is not set to a valid self-defining term.
    def sdterm(self,pm,excp=False,debug=False,trace=False):
        if not self._sdparse:
            self._sdvalue=None
            self._sdparse=True
            self._sdvalue=self._parse_sdterm(pm,self._value,excp=excp)
        if excp and self._sdvalue is None:
            raise pratt3.PEvaluationError(\
                msg="SETC symbol not a self-defining term: '%s'" % self._value)
        return self._sdvalue

    def string(self):
        return self._value

    # Updates the object's value from either an integer or another C_Val object
    def update(self,value):
        if isinstance(value,C_Val):
            self._value=value.string()
        elif isinstance(value,str):
            self._value=value
        else:
            raise ValueError(\
                "%s 'value' argument must be a string or C_Val object: '%s'" \
                    % (assembler.eloc(self,"update",module=this_module),value))

        self.__setK()
        self.__translate()
        self._sdparse=False
        self._sdvalue=None

    # This is only when performing comparison operations on EBCDIC strings
    def value(self):
        return self._ebcdic

    
if __name__ == "__main__":
    raise NotImplementedError("%s module intended for import only" % this_module)