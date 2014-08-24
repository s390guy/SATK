#!/usr/bin/python3
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

# This module contains the finit-state machine parsing technology shared by the
# assembler and macro languages supported by ASMA.  The shared technology includes
# the lexical tokens, pratt evaluator tokens, evaluators used by ASMA.
#
# The class Parsers, at the end of the module, provides common tools and interface
# used for lexical analysis, syntactical analysis and expression evaluation within
# the assembler.
#
# asmparsers.py includes parsers specific to the assembler language.
# macparsers.py contains parsers specific to the macro language.

# Python imports: none
# SATK imports:
import lexer                # Access the lexical analyzer
import fsmparser            # Access the finite state machine based parser
import pratt2               # Access the generalized operator precedence evaluator
import seqparser            # Access the sequential parser
# ASMA imports:
import assembler            # Access the assembler language module
import asmfsmcs             # Access the context senstive parsers
import asmmacs              # Access the macro language module
import asmtokens            # Access standard lexical and pratt2 tokens

this_module="asmfsmbp.py"

#
#  +--------------------------------------------+
#  |                                            |
#  |  ASMA Shared Regular Expression Patterns   |
#  |                                            | 
#  +--------------------------------------------+
#

# These definitions provide consistency between different modules using regular
# expressions.  Use requires the assembler module to be imported

# Note these should probably move here rather than reside in the assembler module.
multiline=assembler.multiline       # Turns on multiline for start/end match
ws=assembler.ws                     # White space characters
macid=assembler.label               # Macro ID (same as a normal label)
label=assembler.label               # Location label 
symvar="&%s" % assembler.label      # Symbolic variable recognizer
seqsym="\.%s" % assembler.label     # Macro sequence symbol recognizer
spaces="[ ]+"                       # One or more spaces
opend=assembler.opend               # End of the operands
anduc="[Aa][Nn][Dd]"                # Mixed case "AND"
equc="[Ee][Qq]"                     # Mixed case "EQ"
geuc="[Gg][Ee]"                     # Mixed case "GE"
gtuc="[Gg][Tt]"                     # Mixed case "GT"
leuc="[Ll][Ee]"                     # Mixed case "LE"
ltuc="[Ll][Tt]"                     # Mixed case "LT"
neuc="[Nn][Ee]"                     # Mixed case "NE"
notuc="[Nn][Oo][Tt]"                # Mixed case "NOT"
oruc="[Oo][Rr]"                     # Mixed case "OR"
xoruc="[Xx][Oo][Rr]"                # Mixed case "XOR"


#
#  +------------------------------+
#  |                              |
#  |   ASMA Shared Base Classes   |
#  |                              | 
#  +------------------------------+
#

# This class forms the base class for all of the finite-state machine based
# syntactical analyzers.  It enforces the structure used by each parser and provides
# some standard functions.
class AsmFSMParser(fsmparser.FSMParser):
    def __init__(self,dm,scope=None,init="init",external=None,trace=False):
        self.dm=dm            # Debug manager, passed to lexical analyzer
        self.lex=self.Lexer() # Create my lexical analyzer
        super().__init__(self.lex,scls=scope,external=external,init=init,trace=trace)
        self.initialize()     # Initialize the finite-state machine

    # This method uses the super class state() method to register defined states
    def initialize(self):
        cls_str=assembler.eloc(self,"initialize",module=this_module)
        raise NotImplementedError("%s subclass %s must provide initialize() method" \
            % (cls_str,self.__class__.__name__))

    def ACT_Expected(self,expected,value,found=None):
        self.stop()    # Terminate the lexer because we are bailing.
        msg="expected %s, found " % expected
        if found is None:
            if isinstance(value,asmtokens.EoOperToken):
                msg="%s%s" % (msg,"end of operands")
            elif isinstance(value,lexer.EOS):
                msg="%s%s" % (msg,"end of statement")
            else:
                msg='%s"%s"' % (msg,value.string)
        else:
            msg="%s%s" % (msg,found)
        raise assembler.AsmParserError(value,msg=msg)

    # This method returns the default lexical analyzer used by all macro statements.
    # Override this method to utilize a different lexical analyzer.
    def Lexer(self):
        return Parsers.lexer


class AsmFSMState(fsmparser.PState):
    def __init__(self,state,pfx="",exit=None):
        self.pfx=pfx
        super().__init__(self.next_state(state))
        self.exit=exit
    def next_state(self,state):
        return "%s_%s" % (self.pfx,state)   

# Base class for all Pratt Evaluator operand tokens. Subclasses are used in
# conjunction with AsmPrattExpr object.  The object provides context sensitive 
# semantics for operands based upon the same lexical token but with differing
# semantics.
#
# An example of this is the use of symbolic SETC characters in arithmetic expressions.
# SETC symbol strings must be recognized as self-defining terms.  However, in 
# character expressions and model statement 
#
# Instance Argument:
#    ltoken   The lexer.Token object forming the basis for the operand
#             This object becomes the pratt2.PLit object's src attribute
class AsmPrattToken(pratt2.PLit):
    def __init__(self,ltoken):
        super().__init__(src=ltoken)


# This is the base class for all lexical tokens created by the lexical analyzers
# shared within ASMA.
class LexicalToken(lexer.Token):
    def __init__(self):
        super().__init__()
        
    # Generates and returns a pratt2 module PToken object for arithmetic expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def atoken(self):
        return self.ptoken()
        
    # Generates and returns a pratt2 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def btoken(self):
        return self.ptoken()
        
    # Generates and returns a pratt2 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def ctoken(self):
        return self.ptoken()
        
    # This method generates a pratt2 module PToken opject.  For lexical tokens that
    # must be converted into a PToken object that participates in expression
    # evalutations this method returns the object.  Lexical tokens that do not
    # participate in expression evaluations do not require this method.
    def ptoken(self,*args,**kwds):
        cls_str=assembler.eloc(self,"ptoken",module=this_module)
        raise NotImplementedError("%s subclass %s must provide ptoken() method" \
            % (cls_str,self.__class__.__name__))

    # This method updates the lexical token with statement specific position
    # information.
    #
    # The lexical analyzer is designed to recognize entire files.  However, ASMA
    # only uses it to recognize portions of a line.  So after accepting the token
    # ASMA must update the token with actual statement location as produced 
    # by the assembler listing.
    def update(self,line,incr,source=None):
        self.line=line
        self.linepos+=incr
        self.source=source 


#
#  +---------------------------------------------+
#  |                                             |
#  |   Expression Evaluation Token Definitions   |
#  |                                             |
#  +---------------------------------------------+
#

# This division operator implements the assembler specific behavior of returning
# a value of zero when division by zero occurs.  Otherwise the pratt2.PFloorDiv
# object handles the division operation.
#class PAsmDiv(pratt2.PFloorDiv):
#    def __init__(self,src=None):
#        super().__init__(src)
    # Infix arithmetic operation: left divided by right, ignoring remainder
#    def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
#        if right==0:
#            return 0
#        return super().calc_led(parser,left,right,external=external,\
#            debug=debug,trace=trace)

# This pratt2.PLit subclass accesses the current location counter.  It is used
# in expressions where the '*' symbol is being used to reference the current location
# (as opposed to being the multiplication operator).
class PLitCur(AsmPrattToken):
    def __init__(self,token):
        super().__init__(token)
    def value(self,external=None,debug=False,trace=False):
        cur_stmt=self.external.cur_stmt
        stmt_bin=cur_stmt.content
        if stmt_bin is None:
            cur=self.external.cur_loc.retrieve()
        else:
            cur=cur_stmt.current()
        if not isinstance(cur,assembler.Address):
            cls_str="asmparsers.py - %s.convert() -" % self.__class__.__name__
            raise ValueError("%s current location of statement %s not an address: %s" \
                % (cls_str,cur_stmt.lineno,cur))
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,cur))
        return cur

# This pratt2.PLit object references to a symbolic symbol's values' K' attribute
#class PLitKAttr(pratt2.PLit):
class PLitKAttr(AsmPrattToken):
    def __init__(self,token):
        super().__init__(token)
        self.symid=self.src.SymID()
    def value(self,external=None,debug=False,trace=False):
        valo=external.lcls._reference(self.symid)
        if debug:
            cls_str=assembler.eloc(self,"value",module=this_module)
            print("%s valo: %s" % (cls_str,valo))
        val=valo.getAttr("K")
        if debug:
            print("%s val: %s" % (cls_str,val))
        return val


# This pratt2.PLit object references to a symbolic symbol's N' attribute
#class PLitNAttr(pratt2.PLit):
class PLitNAttr(AsmPrattToken):
    def __init__(self,token):
        super().__init__(token)
        self.symid=self.src.symid
    def value(self,external=None,debug=False,trace=False):
        return external.lcls._reference_symbol(self.symid).getAttr("N")


# This pratt2 PLit object is used for all symbolic variable references.  It handles
# accessing the current macro symbol dictionary and accessing the symbol's subscript
# if provided.  ALL ACCESS ERRORS ARE DETECTED HERE.
#
# Instance arguments:
#   token    An instance of SymRefToken
class PLitSym(AsmPrattToken):
    def __init__(self,token):
        super().__init__(token)
        self.symid=self.src.SymID()   # Create a SymbolID to access the dictionary
        
    def __str__(self):
        return "%s(symid=%s)" % (self.__class__.__name__,self.symid)

    # Return the symbol's value from the external macro symbol dictionary.
    # Method Arguments:
    #   external   The current Invoker object used to access the symbol dictionary
    # Returns:
    #   the expression type sensitive interpretation of the referenced
    #   AVal, BVal or CVal object from the symbol dictionary
    # Excpetions:
    #   Various MacroError exceptions may be triggered.  The PParser does not catch
    #   them, but they are caught by the current Invoker object in its run() method.
    def value(self,external=None,debug=False,trace=False):
        return external.lcls._reference(self.symid)

class APLitSym(PLitSym):
    def __init__(self,token):
        super().__init__(token)

    # This method must be part of the pratt2.PLit object to facilitate error 
    # reporting of an invalid self defining-term.  This need complicates the 
    # implementation because the ideal place for this method is the asmmacs.CVal
    # object.
    #
    # Returns an integer (and remembers it, in the CVal object) of the self-
    # defining term saved in the SETC symbolic variable when used in arithmetic
    # expression.
    def sdterm(self,valo,debug=False,trace=False):
        if valo._sdvalue is not None:
            return valo._sdvalue
        aval=ArithEval.sdterm(self,valo.string())
        valo._sdvalue=aval
        return aval

    # This method is called by the pratt2 arithmetic evaluator for the symbol's value
    def value(self,external=None,debug=False,trace=False):
        if debug:
            cls_str=assembler.eloc(self,"value",module=this_module)
            print("%s self=%s)" % (cls_str,self))
        valo=super().value(external=external,debug=debug,trace=debug)
        if debug:
            print("%s valo: %s" % (cls_str,valo))
        # valo is either a AVal, BVal, or CVal object
        if isinstance(valo,asmmacs.CVal):
            return self.sdterm(valo,debug=debug,trace=trace)
        return valo.value()

class BPLitSym(PLitSym):
    def __init__(self,token):
        super().__init__(token)

    # This method is called by the pratt2 arithmetic evaluator for the symbol's value
    def value(self,external=None,debug=False,trace=False):
        # Use the super class to access the macro symbol dictionary
        valo=super().value(external=external,debug=debug,trace=debug)
        # valo is either a AVal, BVal, or CVal object
        return valo.value()

#
#  +----------------------------------------------+
#  |                                              |
#  |   Macro Lexical Analyzer Token Definitions   |
#  |                                              |
#  +----------------------------------------------+
#

# Each of these classes provides the update() method.  This method updates the 
# location information provided by the lexical analyzer to match that of the 
# assembler statement from which the expression is evaluated.  This is needed because
# from the view point of the lexical analyzer each string it evalutates is a single
# line starting with the position 0.  By updating the tokens, error reporting 
# reflects the actual statement and character positions of the assembly.

AOPER=asmtokens.AOperType()
COMMA=asmtokens.CommaType()
EOO=asmtokens.EoOperType()
EOS=lexer.EOSType()
LABEL=asmtokens.LabelType()
LPAREN=asmtokens.LParenType()
RPAREN=asmtokens.RParenType()
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()
STRING=asmtokens.StringType()

class CompToken(LexicalToken):
    ptokens={"EQ":pratt2.PEQ,
             "NE":pratt2.PNE,
             "LT":pratt2.PLT,
             "LE":pratt2.PLE,
             "GT":pratt2.PGT,
             "GE":pratt2.PGE}
    def __init__(self):
        super().__init__()
    # Override lexer.Token's extract() method
    def extract(self):
        groups=self.groups()
        return groups[1]
        
    # Returns a pratt2 PToken object with myself as the source
    def ptoken(self):
        cls=CompToken.ptokens[self.extract().upper()]
        return cls(src=self)

class CompType(lexer.Type):
    # Groups 0     1                  2
    pattern="(%s)(%s|%s|%s|%s|%s|%s)(%s)" \
        % (spaces,equc,neuc,ltuc,leuc,gtuc,geuc,spaces)
    def __init__(self,debug=False):
        super().__init__("COMPARE",CompType.pattern,tcls=CompToken,mo=True,debug=debug)

COMPARE=CompType()

#EOO=asmtokens.EoOperType()
#EOS=lexer.EOSType()

class EqualToken(LexicalToken):
    def __init__(self):
        super().__init__()

class EqualType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("EQUAL","=",tcls=EqualToken,debug=debug)

EQUAL=EqualType()

class KeywordToken(LexicalToken):
    def __init__(self):
        super().__init__()
        # Note: self.string will have the terminating equal sign from the pattern

class KeywordType(lexer.Type):
    pattern="%s=" % label
    def __init__(self,debug=False):
        super().__init__("KEYWORD",KeywordType.pattern,tcls=KeywordToken,debug=debug)

KEYWORD=KeywordType()

#LABEL=asmtokens.LabelType()

class LogGenToken(LexicalToken):
    bitwise_ops={"AND":pratt2.PBWAnd,
                 "OR": pratt2.PBWOr,
                 "XOR":pratt2.PBWXor}
    logical_ops={"AND":pratt2.PAnd,
                 "OR": pratt2.POr,
                 "XOR":pratt2.PXor}
    def __init__(self):
        super().__init__()

    # Override lexer.Token's extract() method.  Returns the logical or bit-wise
    # primary operation from the type regular expression object: AND, OR or XOR.
    def extract(self):
        groups=self.groups()
        return groups[1]

    # Returns a pratt2 PToken object with myself as the source
    def ptoken(self):
        cls=self.ptokens()[self.extract().upper()]
        return cls(src=self)

    # This method returns a dictionary for selecting the pratt token associated with
    # the "AND", "OR" and "XOR" operations.
    def ptokens(self):
        cls_str=assembler.eloc(self,"ptokens",module=this_module)
        raise NotImplementedError("%s subclass %s must implement ptokens() method"\
            % (cls_str,self.__class__.__name__))

class LogGenNotToken(LogGenToken):
    def __init__(self):
        super().__init__()

    def ptoken(self):
        cls=self.ptokens()[self.extract().upper()]
        tok1=cls(src=self)
        tok2=self.ptoken_not()
        return [tok1,tok2]

    # Returns the pratt Ptoken associated with the "NOT" operation
    def ptoken_not(self):
        cls_str=assembler.eloc(self,"ptoken_not",module=this_module)
        raise NotImplementedError("%s subclass %s must implement ptoken_not() method"\
            % (cls_str,self.__class__.__name__))

class LogGenType(lexer.Type):
    # Groups 0   1         2
    pattern="(%s)(%s|%s|%s)(%s)" % (spaces,anduc,oruc,xoruc,spaces)
    def __init__(self,tid,tcls,debug=False):
        super().__init__(tid,LogGenType.pattern,tcls=tcls,mo=True,debug=debug)

class LogGenNotType(lexer.Type):
    # Groups 0   1         2   3   4
    pattern="(%s)(%s|%s|%s)(%s)(%s)(%s)" \
        % (spaces,anduc,oruc,xoruc,spaces,notuc,spaces)
    def __init__(self,tid,tcls,debug=False):
        super().__init__(tid,LogGenNotType.pattern,tcls=tcls,mo=True,debug=debug)

class BWOpToken(LogGenToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.bitwise_ops

class BWOpType(LogGenType):
    def __init__(self,debug=False):
        super().__init__("BWOP",BWOpToken,debug=debug)

BWOP=BWOpType()

class BWNOpToken(LogGenNotToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.bitwise_nops
    def ptoken_not(self):
        return pratt2.PBWNot(src=self)   
        
class BWNOpType(LogGenNotType):
    def __init__(self,debug=False):
        super().__init__("BWNOP",BWNOpToken,debug=debug)

BWNOP=BWNOpType()

class LogicalToken(LogGenToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.logical_ops
        
class LogicalType(LogGenType):
    def __init__(self,debug=False):
        super().__init__("LOGICAL",LogicalToken,debug=debug)

LOGICAL=LogicalType()

class LogNotToken(LogGenNotToken):
    def __init__(self):
        super().__init__(self)
    def ptokens():
        return LogGenToken.logical_ops
    def ptoken_not(self):
        return pratt2.PNot(src=self)

class LogNotType(LogGenNotType):
    def __init__(self,debug=False):
        super().__init__("LOGNOT",LogNotToken,debug=debug)

LOGNOT=LogNotType()

#LPAREN=asmtokens.LParenType()

class NAttrToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def ptoken(self):
        groups=self.mo.groups()
        self.symid=asmmacs.SymbolID(groups[2])
        return PLitNAttr(self)

class NAttrType(lexer.Type):
    # Groups 0  1  2
    pattern="(N)(')(%s)" % symvar
    def __init__(self,debug=False):
        super().__init__("NATTR",NAttrType.pattern,tcls=NAttrToken,mo=True,debug=debug)

NATTR=NAttrType()

class NotToken(LexicalToken):
    def __init__(self):
        super().__init__()

    # Override lexer.Token's extract() method
    def extract(self):
        groups=self.groups()
        return groups[1]

    def atoken(self):
        return pratt2.PBWNot(src=self)

    def btoken(self):
        return pratt2.PNot(src=self)

    # Returns a pratt2 PToken object with myself as the source
    #def ptoken(self):
    #    return pratt2.PNot(src=self)

class NotType(lexer.Type):
    # Groups 0     1   2
    pattern="([ ]*)(%s)(%s)" % (notuc,spaces)
    def __init__(self,debug=False):
        super().__init__("NOT",NotType.pattern,tcls=NotToken,mo=True,debug=debug)

NOT=NotType()

# This token type and token object are used only during macro parameter parsing.
# It accepts anything that is _not_ the following when encountered outside of single
# quoted strings:
#   - a space outside of quotes (indicates the end of the 
#   - a single quote (only allowed within single quoted strings)
#   - a left parenthesis (indicates the start of a subscripted parameter)
#   - a right parenthesis (indicates the end of a subscripted parameter)
class ParameterToken(lexer.Token):
    def __init__(self):
        super().__init__()
        
class ParameterType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("PARM","[^',\(\) ]+",tcls=ParameterToken,debug=debug) 

PARM=ParameterType()

#RPAREN=asmtokens.RParenType()

#SDBIN=asmtokens.SDBinType()

#SDCHR=asmtokens.SDChrType()

#SDDEC=asmtokens.SDDecType()

#SDHEX=asmtokens.SDHexType()

class SeqToken(LexicalToken):
    def __init__(self):
        super().__init__()

class SeqType(lexer.Type):
     def __init__(self,debug=False):
        super().__init__("SEQSYM",seqsym,tcls=SeqToken,debug=debug)

SEQSYM=SeqType()

#STRING=asmtokens.StringType()

# This object processes a regular expression match object created by one of the
# SymRefType regular expression patterns.  This allows the match object to be
# utilized in different contexts.  All of the heavy lifting of symbolic variable
# refernences occur here.
class SymRefMO(object):
    # Groups                4<---->4 5--5
    # Groups               3<----------->3
    # Groups 0---01--12<-----------------------2
    pattern="(K')?(%s)([\(](([0-9]+)|(%s))[\)])?"   % (symvar,symvar)
    def __init__(self,mo):
        self.mo=mo               # Match object from a SymRefType pattern
        self.symid=None          # Symbolic variable name
        self.subscripted=False   # True is the reference contains a subscript
        self.subscript=None      # Subscript as an integer value
        self.subsym=None         # Subscript symbolic variable if not an integer
        self.attr=None           # Attribute associated with reference

        self.groups=groups=mo.groups()
        #print("SymRefMO groups: %s" % list(groups))
        if len(groups)!=6:
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s unexpected match object groups: %s" \
                % (cls_str,list(self.groups)))
        attr=groups[0]
        self.symid=groups[1]
        subscript=groups[2]
        if attr is not None:
            self.attr=attr[0]  # Remember the attribute character

        if self.symid is None:
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s symbolic variable: %s" % (cls_str,self.symid))

        if subscript is not None:
            # Remove the parenthesis from around subscript
            self.subscripted=True
            subscript=subscript[1:-1]
            try:
                # Convert numeric subscript (unsigned numeric self defining term)
                self.subscript=int(subscript,10)
            except ValueError:
                # If not integer, subscript is a SETA symbol
                self.subsym=subscript

    def __str__(self):
        if self.subsym is not None:
            subsym='%s' % self.subsym
        else:
            subsym="None"
        string="%s(symid='%s',subscripted=%s,subscript=%s,subsym=%s" \
            % (self.__class__.__name__,self.symid,self.subscripted,self.subscript,\
                subsym)
        string="%s\n   groups: %s" % (string,self.groups)
        return string
        
    # Returns the position of the symbolic reference.  Allows updating via 'incr'
    # argument
    def subpos(self,incr=0):
        if self.mo.group(2) is None:
            return None
        return self.mo.start(2)+incr+1

    # Returns the position of the subscript or None.  Allows updating via the 'incr'
    # argument.
    def sympos(self,incr=0):
        return self.mo.start(1)+incr

    # Returns the asmmacs.SymbolID object derived from the match object
    def SymID(self):
        if not self.subscripted:
            return asmmacs.SymbolID(self.symid)
        if self.subscript is None:
            # Not an integer subscript, so assume symbolic variable as the subscript
            return asmmacs.SymbolID(self.symid,subscript=self.subsym)
        # Use integer subscript
        return asmmacs.SymbolID(self.symid,subscript=self.subscript)

class SymRefToken(LexicalToken):
    atokens={None:APLitSym,"K":PLitKAttr}
    btokens={None:BPLitSym,"K":PLitKAttr}
    ptokens={None:PLitSym,"K":PLitKAttr}
    def __init__(self):
        super().__init__()
        # These attributes are set by the update() method
        self.subpos=None       # Position in the line of the subscript
        self.sympos=None       # Position in the line of the symbol reference
        self.srmo=None         # SymRefMO object

    def atoken(self):
        cls=SymRefToken.atokens[self.srmo.attr]
        return cls(self)
    def btoken(self):
        cls=SymRefToken.btokens[self.srmo.attr]
        return cls(self)
    def ctoken(self):
        return self.ptoken()
    # Returns a pratt2 PToken object (defined above) with myself as the source
    def ptoken(self):
        cls=SymRefToken.ptokens[self.srmo.attr]
        return cls(self)

    # Returns an asmmacs.SymbolID object used to reference the macro dictionary
    def SymID(self):
        return self.srmo.SymID()

    # Update the token with its actual location in the input line
    def update(self,stmt,incr,source=None):
        # Do the generic update via the super class.
        super().update(stmt,incr,source=source)
        # Perform special handling of the symbolic variable reference via the
        # SymRefMO object.
        self.srmo=srmo=SymRefMO(self.mo)
        # Remember where the symbolic variable is in the line
        self.sympos=srmo.sympos(incr=incr)
        # If a subscript is provided, remember where it starts in the line
        self.subpos=srmo.subpos(incr=incr)

class SymRefType(lexer.Type):
    def __init__(self,debug=False):
        pattern=SymRefMO.pattern
        super().__init__("SYMREF",pattern,mo=True,tcls=SymRefToken,debug=debug)

SYMREF=SymRefType()


#
#  +-------------------------------------------+
#  |                                           |
#  |   Macro Arithmetic Expression Evaluator   |
#  |            (AGO, SETA, SETC)              |
#  |                                           |
#  +-------------------------------------------+
#

class ArithEval(pratt2.PParser):
    # This method tries to convert a string (PListStr) or SETC symbol value (PLitSym)
    # a pratt2.PParserError will be raised if the conversion fails.
    @staticmethod
    def sdterm(ptok,string):
        if len(string)==0:
            raise pratt2.PParserError(ptok=ptok,msg="empty SETC symbol or string")
        try:
            sdscope=Parsers.sdterm.parse(string)
        except assembler.AsmParserError as mpe:
            # Convert to a pratt parser error 
            raise pratt2.PParserError(ptok=ptok,msg=mpe.msg) from None
        # Convert the SDDEC, SDHEX, SDCHR or SDBIN lexical token into an integer
        return sdscope.sdtok.convert()

    def __init__(self):
        super().__init__()
        # Initialize my operator precedence values
        self.operator(pratt2.PBWNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
        #self.operator(pratt2.PFloorDiv,lbp=50,rbp=None,symbol="/",\
        #    isinfix=True,isunary=False)
        self.operator(asmtokens.PAsmDiv,lbp=50,rbp=None,symbol="/",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PMul,lbp=50,rbp=None,symbol="*",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PAdd,lbp=40,rbp=100,symbol="+",\
            isinfix=True,isunary=True)
        self.operator(pratt2.PSub,lbp=40,rbp=100,symbol="-",\
            isinfix=True,isunary=True)
        self.operator(pratt2.PBWAnd,lbp=30,rbp=None,symbol="AND",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PBWOr,lbp=30,rbp=None,symbol="OR",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PBWXor,lbp=30,rbp=None,symbol="XOR",\
            isinfix=True,isunary=False)
        # Need to add bit-wise shifts: SLA, SLL, SRA, SRL

class ArithExpr(pratt2.PExpr):
    evaluator=ArithEval()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return ArithExpr.evaluator.run(self,external=external,debug=debug,trace=trace)
    def token(self,ptok):
        super().token(ptok)


#
#  +----------------------------------------+
#  |                                        |
#  |   Macro Logical Expression Evaluator   |
#  |               (AIF, SETB)              |
#  |                                        |
#  +----------------------------------------+
#

class BinaryEval(pratt2.PParser):
    def __init__(self):
        super().__init__()

        # Operator Precedence (Highest to Lowest)
        #   Comparisons
        #   NOT
        #   AND
        #   OR
        #   XOR
        self.operator(pratt2.PNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
        self.operator(pratt2.PEQ,lbp=50,rbp=None,symbol="EQ",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PNE,lbp=50,rbp=None,symbol="NE",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PLT,lbp=50,rbp=None,symbol="LT",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PLE,lbp=50,rbp=None,symbol="LE",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PGT,lbp=50,rbp=None,symbol="GT",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PGE,lbp=50,rbp=None,symbol="GE",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PAnd,lbp=40,rbp=None,symbol="AND",\
            isinfix=True,isunary=False)
        self.operator(pratt2.POr,lbp=30,rbp=None,symbol="OR",\
            isinfix=True,isunary=False)
        self.operator(pratt2.PXor,lbp=20,rbp=None,symbol="XOR",\
            isinfix=True,isunary=False)

class BinaryExpr(pratt2.PExpr):
    evaluator=BinaryEval()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return BinaryExpr.evaluator.run(self,external=external,debug=debug,trace=trace)
    def token(self,ptok):
        super().token(ptok)

#
#  +--------------------------------------+
#  |                                      |
#  |   Statement Field Lexical Analyzer   |
#  |                                      |
#  +--------------------------------------+
#

class FieldLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm
        
    def init(self):
        tdebug=self.dm.isdebug("tdebug")
    
        lst=[]
        #lst.append(LPAREN)      # "("
        #lst.append(RPAREN)      # ")"
        #lst.append(COMMA)       # ","
        #lst.append(EQUAL)       # "="
        #lst.append(LOGNOT)      # " AND NOT ", " OR NOT ", " XOR NOT "
        #lst.append(LOGICAL)     # " AND ", " OR ", " XOR "
        #lst.append(COMPARE)     # " EQ ", " NE ", " LT ", " LE ", " GT ", " GE "
        #lst.append(AOPER)       # "+", "-", "*", "/"
        #lst.append(NOT)         # "NOT ", " NOT "
        #lst.append(SDBIN)       # "B'01.."
        #lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        #lst.append(SDHEX)       # "X'0..F..'"
        #lst.append(SDDEC)       # "0..9.."
        #lst.append(NATTR)       # N'&label   # Number attribute reference
        lst.append(SYMREF)      #*   "&label",   "&label(0..9..)",    "&label(&sub)"
                                # "K'&label", "K'&label(0..9..)",  "K'&label(&sub)"
        lst.append(SEQSYM)      #* ".label"
        lst.append(LABEL)       #* "label"
        #lst.append(STRING)      # "'x..'"  Includes the empty string
        lst.append(EOO)         #* " "      One or more spaces
        lst.append(EOS)         #* end of input string detected by lexer
        # Because of the options used by the fsmparser.FSMParser class, the lexical
        # analyzer will also generate the lexer.Unrecognized() token when no 
        # match is found.

        for typ in lst:
            typ.setDebug(tdebug)
            self.type(typ)

        # Display token types if --debug ldebug set in the command line
        if self.dm.isdebug("ldebug"):
            self.types()

        return self


#
#  +-----------------------------------------------+
#  |                                               |
#  |   Shared Statement Operand Lexical Analyzer   |
#  |                                               |
#  +-----------------------------------------------+
#

class AsmLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        lst=[]
        lst.append(LPAREN)      # "("
        lst.append(RPAREN)      # ")"
        lst.append(COMMA)       # ","
        lst.append(EQUAL)       # "="
        lst.append(LOGNOT)      # " AND NOT ", " OR NOT ", " XOR NOT "
        lst.append(LOGICAL)     # " AND ", " OR ", " XOR "
        lst.append(COMPARE)     # " EQ ", " NE ", " LT ", " LE ", " GT ", " GE "
        lst.append(AOPER)       # "+", "-", "*", "/"
        lst.append(NOT)         # "NOT ", " NOT "
        lst.append(SDBIN)       # "B'01.."
        lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        lst.append(SDHEX)       # "X'0..F..'"
        lst.append(SDDEC)       # "0..9.."
        lst.append(NATTR)       # N'&label   # Number attribute reference
        lst.append(SYMREF)      #   "&label",   "&label(0..9..)",    "&label(&sub)"
                                # "K'&label", "K'&label(0..9..)",  "K'&label(&sub)"
        lst.append(SEQSYM)      # ".label"
        lst.append(LABEL)       # "label"
        lst.append(STRING)      # "'x..'"  Includes the empty string
        lst.append(EOO)         # " "      One or more spaces
        lst.append(EOS)         # end of input string detected by lexer
        # Because of the options used by the fsmparser.FSMParser class, the lexical
        # analyzer will also generate the lexer.Unrecognized() token when no 
        # match is found.

        for typ in lst:
            typ.setDebug(tdebug)
            self.type(typ)

        # Display token types if --debug ldebug set in the command line
        if self.dm.isdebug("ldebug"):
            self.types()

        return self

#
#  +--------------------------------------+
#  |                                      |
#  |   Macro Parameter Lexical Analyzer   |
#  |                                      |
#  +--------------------------------------+
#

class ParameterLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        lst=[]
        lst.append(LPAREN)      # "("
        lst.append(RPAREN)      # ")"
        lst.append(COMMA)       # ","
        #lst.append(EQUAL)       # "="
        lst.append(KEYWORD)     # "label="
        #lst.append(LOGNOT)      # " AND NOT ", " OR NOT ", " XOR NOT "
        #lst.append(LOGICAL)     # " AND ", " OR ", " XOR "
        #lst.append(COMPARE)     # " EQ ", " NE ", " LT ", " LE ", " GT ", " GE "
        #lst.append(AOPER)       # "+", "-", "*", "/"
        #lst.append(NOT)         # "NOT ", " NOT "
        #lst.append(SDBIN)       # "B'01.."
        #lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        #lst.append(SDHEX)       # "H'0..F..'"
        #lst.append(SDDEC)       # "0..9.."
        #lst.append(NATTR)       # N'&label   # Number attribute reference
        #lst.append(SYMREF)      #   "&label",   "&label(0..9..)",    "&label(&sub)"
                                # "K'&label", "K'&label(0..9..)",  "K'&label(&sub)"
        #lst.append(SEQSYM)      # ".label"
        #lst.append(LABEL)       # "label"
        lst.append(STRING)      # "'x..'"  Includes the empty string
        lst.append(PARM)        # anything that isn't a single quote, parenthesis , 
                                # comma or a space outside of quotes
        lst.append(EOO)         # " "      One or more spaces
        lst.append(EOS)         # end of input string detected by lexer
        # Because of the options used by the fsmparser.FSMParser class, the lexical
        # analyzer will also generate the lexer.Unrecognized() token when no 
        # match is found.

        for typ in lst:
            typ.setDebug(tdebug)
            self.type(typ)

        # Display token types if --debug ldebug set in the command line
        if self.dm.isdebug("ldebug"):
            self.types()

        return self  

#
#  +----------------------------------------+
#  |                                        |
#  |   Generic Statement Field Recognizer   |
#  |                                        |
#  +----------------------------------------+
#

class FieldParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=None,trace=False)

    # Define my states and action methods.
    def initialize(self):
        # Looking for the name feild
        init=fsmparser.PState("init")
        init.action([SEQSYM,],self.ACT_NameSeq)
        init.action([SYMREF,],self.ACT_NameSym)
        init.action([LABEL,],self.ACT_NameLabel)
        init.action([EOO,],self.ACT_NameNone)
        init.error(self.ACT_ExpectedName)
        self.state(init)

        # Looking for spaces before the operation field
        op_spaces=fsmparser.PState("op_spaces")
        op_spaces.action([EOO,],self.ACT_Oper)
        op_spaces.error(self.ACT_ExpectedSpaces1)
        self.state(op_spaces)

        # Found the operation field
        optn=fsmparser.PState("optn")
        optn.action([LABEL,],self.ACT_Operation)
        optn.error(self.ACT_ExpectedOper)
        self.state(optn)

        # Looking for spaces after the operation field
        opnd_spaces=fsmparser.PState("opnd_spaces")
        opnd_spaces.action([EOO,],self.ACT_Opnd)
        opnd_spaces.action([EOS,],self.ACT_Done)
        opnd_spaces.error(self.ACT_ExpectedSpaces2)
        self.state(opnd_spaces)

        # Found spaces following operation field, if anything is there it marks the
        # start of the operands.
        opnd=fsmparser.PState("opnd")
        opnd.action([EOS,],self.ACT_Done)
        opnd.error(self.ACT_Operands)
        self.state(opnd)

    def ACT_Done(self,value,state,trace=False):
        state.atend()

    def ACT_ExpectedName(self,value,state,trace=False):
        self.ACT_Expected("name field",value)

    def ACT_ExpectedOper(self,value,state,trace=False):
        self.ACT_Expected("operation field",value)

    def ACT_ExpectedSpaces1(self,value,state,trace=False):
        self.ACT_Expected("one or more spaces before operation field",value)

    def ACT_ExpectedSpaces2(self,value,state,trace=False):
        self.ACT_Expected("one or more spaces following operation field",value)

    def ACT_NameLabel(self,value,state,trace=False):
        gs=self.scope()
        gs.NameLabel(value)
        return "op_spaces"

    def ACT_NameNone(self,value,state,trace=False):
        return "optn"

    def ACT_NameSeq(self,value,state,trace=False):
        gs=self.scope()
        gs.NameSeq(value)
        return "op_spaces"

    def ACT_NameSym(self,value,state,trace=False):
        gs=self.scope()
        gs.NameSym(value)
        return "op_spaces"

    def ACT_Oper(self,value,state,trace=False):
        return "optn"

    def ACT_Opnd(self,value,state,trace=False):
        return "opnd"

    def ACT_Operands(self,value,state,trace=False):
        gs=self.scope()
        #print("ACT_Operands value: %s" % value)
        gs.Operands(value)
        state.atend()

    def ACT_Operation(self,value,state,trace=False):
        gs=self.scope()
        gs.Operation(value)
        return "opnd_spaces"

    def Lexer(self):
        return Parsers.flexer



#
#  +-----------------------------------------+
#  |                                         |
#  |   Assembler Address Expression Parser   |
#  |                                         |
#  +-----------------------------------------+
#

class AddressParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=AddrScope,trace=False)

    # Define my states and action methods.
    def initialize(self):                                            # Next state
        init=fsmparser.PState("init")
        init.action([LABEL,],self.ACT_Add_Base)                      #   adjust     
        init.error(self.ACT_ExpectedLabel)
        self.state(init)

        # Initial infix +/- expected
        adjust=fsmparser.PState("adjust")
        adjust.action([AOPER,],self.ACT_Add_Adjustment)              #   rh
        adjust.action([EOO,EOS],self.ACT_End)  # No adjustment, done  
        adjust.error(self.ACT_ExpectedAdjustment)
        self.state(adjust)

        # State after an infix operator
        rh=fsmparser.PState("rh")
        rh.action([LPAREN,],self.ACT_LPAREN)                          #  rh
        rh.action([LABEL,SDBIN,SDHEX,SDCHR,SDDEC],self.ACT_Add_RHand) #  infix
        rh.action([AOPER,],self.ACT_Add_Unary)                    #  +/-=rh, *=infix
        rh.error(self.ACT_ExpectedOperand)
        self.state(rh)

        # Expecting an infix operator
        infix=fsmparser.PState("infix")
        infix.action([AOPER],self.ACT_Add_Infix)                      # rh
        infix.action([RPAREN,],self.ACT_RPAREN)                       # infix
        infix.action([EOO,EOS],self.ACT_End)    # no more, done
        infix.error(self.ACT_ExpectedOperator)
        self.state(infix)

    def ACT_Add_Adjustment(self,value,state,trace=False):
        if value.string in "+-":
            gs=self.scope()
            gs.token(value)
            return "rh"
        self.ACT_Expected("plus or minus address adjustment",value)
        
    def ACT_Add_Base(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        # Remember the base address token so its label is remembered for a possible
        # Location object
        gs.anchor=value
        return "adjust"

    def ACT_Add_Infix(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "rh"

    def ACT_Add_RHand(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "infix"

    def ACT_Add_Unary(self,value,state,trace=False):
        if value.string in "+-":
            gs=self.scope()
            gs.token(value)
            return "rh"
        elif value.string=="*":
            value.iscur=True       # Make sure the correct pratt token is generated
            gs.token(value)
            return "infix"
        else:
            self.ACT_Expected("unary operator or current location counter",value)

    def ACT_End(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        lextoks=gs.expr_end()
        gs.lextoks=lextoks
        if len(lextoks)>1:
            self.adjust=lextoks[1:]
        state.atend()

    def ACT_ExpectedAdjustment(self,value,state,trace=False):
        self.ACT_Expected("plus/minus address adjustment",value)

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("arithmetic operation or valid arithemtic operand",value)
        
    def ACT_ExpectedLabel(self,value,state,trace=False):
        self.ACT_Expected("initial address label",value)

    def ACT_ExpectedOperand(self,value,state,trace=False):
        self.ACT_Expected("address, self-defining term, or left parenthesis",value)
     
    def ACT_ExpectedOperator(self,value,state,trace=False):
        self.ACT_Expected("infix operator",value)

    def ACT_LPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "rh"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.rparen(value)
        return "infix"

# Shared between AddressParser, ArithParser, MHELPParser and SPACEParser
#class AddrScope(AsmFSMScope):
class AddrScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
    def __str__(self):
        string="%s():" % self.__class__.__name__
        for tok in self.lextoks:
            string="%s\n    %s" % (string,tok)
        return string
    def init(self):
        super().init()
        self.parens=0          # Used to check for balanced parenthesis

        # These two attributes are relavant for a potential Location object
        # Note: ultimately only Location objects might result from address arithmetic
        self.anchor=None
        self.adjust=[]
        # This attribute is relavant for an address calculation.
        self.lextoks=[]


#
#  +----------------------------------------+
#  |                                        |
#  |   Macro Arithmetic Expression Parser   |
#  |                                        |
#  +----------------------------------------+
#

class ArithParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=AScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,NATTR,SYMREF],self.ACT_Add_Token)
        init.action([LPAREN,],self.ACT_LPAREN)
        init.action([RPAREN,],self.ACT_RPAREN)
        init.action([EOO,EOS],self.ACT_End)
        init.error(self.ACT_ExpectedExpr)
        self.state(init)

    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return state.state

    def ACT_End(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        gs.lextoks=gs.expr_end()
        state.atend()

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("arithmetic operation or valid arithemtic operand",value)

    def ACT_LPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "init"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.rparen(value)
        return "init"

# Shared between ArithParser, MHELPParser and SPACEParser
#class AScope(AsmFSMScope):
class AScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
    def __str__(self):
        string="%s():" % self.__class__.__name__
        for tok in self.lextoks:
            string="%s\n    %s" % (string,tok)
        return string
    def init(self):
        super().init()
        self.lextoks=[]


#
#  +------------------------------------+
#  |                                    |
#  |   Assembler MHELP Operand Parser   |
#  |                                    |
#  +------------------------------------+
#

# The MHELP parser is nothing more than an ArithParser with a subset of the tokens
# accepted by the ArithParser.  It will return an instance of AScope.
class MHELPParser(ArithParser):
    def __init__(self,dm):
        super().__init__(dm)

    def initialize(self):
        init=fsmparser.PState("init")
        init.action([AOPER,SDBIN,SDHEX,SDDEC],self.ACT_Add_Token)
        init.action([LPAREN,],self.ACT_LPAREN)
        init.action([RPAREN,],self.ACT_RPAREN)
        init.action([EOO,EOS],self.ACT_End)
        init.error(self.ACT_ExpectedExpr)
        self.state(init)

#
#  +------------------------------------+
#  |                                    |
#  |   Assembler SPACE Operand Parser   |
#  |                                    |
#  +------------------------------------+
#

# The SPACE parser is nothing more than an ArithParser with a subset of the tokens
# accepted by the ArithParser.  It will return an instance of AScope.
class SPACEParser(ArithParser):
    def __init__(self,dm):
        super().__init__(dm)

    def initialize(self):
        init=fsmparser.PState("init")
        init.action([AOPER,SDBIN,SDHEX,SDDEC],self.ACT_Add_Token)
        init.action([LPAREN,],self.ACT_LPAREN)
        init.action([RPAREN,],self.ACT_RPAREN)
        init.action([EOO,EOS],self.ACT_End)
        init.error(self.ACT_ExpectedExpr)
        self.state(init)

#
#  +------------------------------------+
#  |                                    |
#  |   Assembler MNOTE Operand Parser   |
#  |                                    |
#  +------------------------------------+
#

class MNOTEParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=MNOTEScope,trace=False)

    def initialize(self):
        init=fsmparser.PState("init")
        init.action([SDBIN,SDHEX,SDDEC,SDCHR],self.ACT_Add_Token)
        init.action([AOPER,],self.ACT_Asterisk)
        init.action([LPAREN,],self.ACT_LPAREN)
        init.action([COMMA,],self.ACT_ONLY_COMMA)
        init.action([STRING,],self.ACT_Message_Start)
        init.error(self.ACT_ExpectedSeverity)
        self.state(init)
        
        expr=fsmparser.PState("expr")
        expr.action([SDBIN,SDHEX,SDDEC,SDCHR,AOPER],self.ACT_Add_Token)
        expr.action([LPAREN,],self.ACT_LPAREN)
        expr.action([RPAREN,],self.ACT_RPAREN)
        expr.action([COMMA,],self.ACT_COMMA)
        expr.error(self.ACT_ExpectedExpr)
        self.state(expr)
        
        comma=fsmparser.PState("comma")
        comma.action([COMMA,],self.ACT_COMMA)
        comma.error(self.ACT_ExpectedComma)
        self.state(comma)
        
        msg_beg=fsmparser.PState("msg_beg")
        msg_beg.action([STRING,],self.ACT_Message_Start)
        msg_beg.error(self.ACT_ExpectedMessage)
        self.state(msg_beg)
        
        msg_cont=fsmparser.PState("msg_cont")
        msg_cont.action([STRING,],self.ACT_Message_More)
        msg_cont.action([EOO,EOS],self.ACT_Done)
        msg_cont.error(self.ACT_ExpectedEnd)
        self.state(msg_cont)
        
    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return state.state
        
    def ACT_Asterisk(self,value,state,trace=False):
        gs=self.scope()
        oper=value.string
        if oper=="*":
            gs.comment=True
            return "comma"
        if oper in ["+","-"]:
            # This is a valid unary operator of expression
            gs.token(value)
            return "expr"
        self.ACT_Expected("asterisk or unary arithmetic operator",value)
        
    # Comma found after severity
    def ACT_COMMA(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        gs.lextoks=gs.expr_end()
        return "msg_beg"

    def ACT_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.message=gs.str_end()
        state.atend()

    def ACT_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operands",value)

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("severity arithmetic expression of self-defining terms",\
            value)

    def ACT_ExpectedMessage(self,value,state,trace=False):
        self.ACT_Expected("message string",value)
  
    def ACT_ExpectedSeverity(self,value,state,trace=False):
        self.ACT_Expected("serverity expression, comma, or message",value)
  
    def ACT_LPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "expr"

    def ACT_Message_Comment(self,value,state,trace=False):
        gs=self.scope()
        gs.comment=True
        gs.str_begin(value)
        return "msg_cont"

    def ACT_Message_More(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "msg_cont"

    def ACT_Message_Start(self,value,state,trace=False):
        gs=self.scope()
        gs.str_begin(value)
        return "msg_cont"

    # Comma found without severity
    def ACT_ONLY_COMMA(self,value,state,trace=False):
        gs=self.scope()
        gs.severity=1
        return "msg_beg"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.rparen(value)
        return "init"


#class MNOTEScope(AsmFSMScope):
class MNOTEScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()

    def init(self):
        super().init()
        # Severity expression lexical tokens
        self.lextoks=[]
        # StringToken of message text
        self.message=None
        # Set to True if severity and comma omitted, or serverity is '*'
        self.comment=False
        # Set to 1 if severity is ommitted, but initial comma is present
        self.severity=None


#
#  +-------------------------------------+
#  |                                     |
#  |   Macro Logical Expression Parser   |
#  |             (AIF, SETB)             |
#  |                                     |
#  +-------------------------------------+
#

class BinaryParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=BScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([LPAREN,RPAREN,SDBIN,SDHEX,SDCHR,SDDEC,NATTR,SYMREF,STRING,\
                     LOGNOT,LOGICAL,COMPARE,NOT],method=self.ACT_Add_Token)
        init.action([EOO,EOS],self.ACT_End)
        init.error(self.ACT_ExpectedExpr)
        self.state(init)

    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return state.state

    def ACT_End(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        gs.lextoks=gs.expr_end()
        state.atend()

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("logical operation or valid logical operand",value)

    def ACT_LPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "oper"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.rparen(value)
        return "oper"

#class BScope(AsmFSMScope):
class BScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
    def __str__(self):
        string="%s():" % self.__class__.__name__
        for tok in self.lextoks:
            string="%s\n    %s" % (string,tok)
        return string
    def init(self):
        super().init()
        self.lextoks=[]


#
#  +------------------------------+
#  |                              |
#  |   Macro AGO Operand Parser   |
#  |                              |
#  +------------------------------+
#

class AGOParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=AGOScope,trace=False)

    def initialize(self):
        init=fsmparser.PState("init")
        init.action(SEQSYM,self.ACT_Initial_Sequence)
        init.action(LPAREN,self.ACT_Computed_Start)
        init.action([EOO,EOS],self.ACT_MissingOperand) # see Note below
        init.error(self.ACT_ExpectedSeqLP)
        self.state(init)
        # Note: the EOO or EOS lexical tokens should never be initially presented
        # because all leading spaces are removed before operand parsing and an
        # empty string should not attempt to be parsed.  This really indicates a
        # bug likely in the FieldParser object.

        isend=fsmparser.PState("isend")
        isend.action([EOO,EOS],self.ACT_Done)
        isend.error(self.ACT_ExpectedEnd)
        self.state(isend)

        comp=fsmparser.PState("comp")
        comp.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,SYMREF],self.ACT_Add_Token)
        comp.action([LPAREN,],self.ACT_LPAREN)
        comp.action([RPAREN,],self.ACT_RPAREN)
        comp.action([SEQSYM,],self.ACT_Computed_Done)
        comp.error(self.ACT_ExpectedArith)
        self.state(comp)

        more=fsmparser.PState("more")
        more.action([COMMA,],self.ACT_MoreSeq)
        more.action([EOO,EOS],self.ACT_Done)
        more.error(self.ACT_ExpectedComma)
        self.state(more)

        next=fsmparser.PState("next")
        next.action([SEQSYM,],self.ACT_NextSeq)
        next.error(self.ACT_ExpectedSeq)
        self.state(next)

    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "comp"

    def ACT_Computed_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        gs.lextoks=gs.expr_end()
        gs.sequence(value)
        return "more"

    def ACT_Computed_Start(self,value,state,trace=False):
        return "comp"

    def ACT_Done(self,value,state,trace=False):
        state.atend()

    def ACT_ExpectedArith(self,value,state,trace=False):
        self.ACT_Expected("arithmetic operation or valid arithemtic operand",value)

    def ACT_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operands",value)

    def ACT_ExpectedSeq(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol",value)

    def ACT_ExpectedSeqLP(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol or left parenthesis",value)

    def ACT_Initial_Sequence(self,value,state,trace=False):
        gs=self.scope()
        gs.sequence(value)
        return "isend"

    def ACT_MissingOperand(self,value,state,trace=False):
        raise assembler.AsmParserError(value,msg="AGO required operand field missing")

    def ACT_MoreSeq(self,value,state,trace=False):
        return "next"

    def ACT_NextSeq(self,value,state,trace=False):
        gs=self.scope()
        gs.sequence(value)
        return "more"

    def ACT_LPAREN(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "comp"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        if gs._parens==0:
            return "next"
        gs.rparen(value)
        return "comp"

#class AGOScope(fsmparser.PScope):
#class AGOScope(AsmFSMScope):
class AGOScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
    def init(self):
        super().init()
        self.lextoks=[]       # Computed AGO arithemtic expression lexical toke
        self.seq=[]           # Sequence Symbol lexical tokens
    def sequence(self,tok):
        self.seq.append(tok) 
 

#
#  +---------------------------------------------+
#  |                                             |
#  |   Macro Conditional Branch Operand Parser   |
#  |                   (AIF)                     |
#  |                                             |
#  +---------------------------------------------+
#

class AIFParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=AIFScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([LPAREN,],self.ACT_LPAREN_First)
        init.error(self.ACT_ExpectedLParen)
        self.state(init)

        oper=fsmparser.PState("oper")
        oper.action([LPAREN,],self.ACT_LPAREN_Other)
        oper.action([RPAREN,],self.ACT_RPAREN)
        oper.action([SDBIN,SDHEX,SDCHR,SDDEC,SYMREF,STRING,LOGNOT,COMPARE,NOT],
            method=self.ACT_Add_Token)
        oper.error(self.ACT_ExpectedExpr)
        self.state(oper)

        seq=fsmparser.PState("seq")
        seq.action([SEQSYM,],self.ACT_Sequence)
        seq.error(self.ACT_ExpectedSeqSym)
        self.state(seq)

        end=fsmparser.PState("end")
        end.action([EOO,EOS],self.ACT_End)
        end.error(self.ACT_ExpectedEnd)
        self.state(end)

    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        gs.last=False
        return state.state

    def ACT_End(self,value,state,trace=False):
        state.atend()

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operands",value)

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("logical operations or valid logical operand",value)

    def ACT_ExpectedLParen(self,value,state,trace=False):
        self.ACT_Expected("left parenthesis",value)

    def ACT_ExpectedSeqSym(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol",value)

    def ACT_LPAREN_First(self,value,state,trace=False):
        return "oper"

    def ACT_LPAREN_Other(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return "oper"

    def ACT_RPAREN(self,value,state,trace=False):
        gs=self.scope()
        if gs._parens==0:
            if len(gs._lextoks)==0:
                self.ACT_ExpectedExpr(value,state,trace=False)
            return "seq"
        gs.rparen(value)
        return "oper"

    def ACT_Sequence(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        gs.lextoks=gs.expr_end()
        gs.seq=value
        return "end"

#class AIFScope(AsmFSMScope):
class AIFScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
    def __str__(self):
        string="%s():" % self.__class__.__name__
        for tok in self.lextoks:
            string="%s\n    %s" % (string,tok)
        return string
    def init(self):
        super().init()
        self.lextoks=[]       # AIF logical expression lexical tokens
        self.seq=None         # Sequence Symbol lexical token


#
#  +---------------------------------------+
#  |                                       |
#  |   Macro Character Expression Parser   |
#  |                (SETC)                 |
#  |                                       |
#  +---------------------------------------+
#

class CharParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=CScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([STRING,],self.ACT_String_Token)
        init.error(self.ACT_ExpectedString)
        self.state(init)

        more=fsmparser.PState("more")
        more.action([STRING,],self.ACT_String_Extend)
        more.action([LPAREN,],self.ACT_Sub_String_Start)
        more.action([EOO,EOS],self.ACT_Done)
        more.error(self.ACT_ExpectedSubString)
        self.state(more)

        subst=fsmparser.PState("subst")
        subst.action([LPAREN,],self.ACT_LParen)
        subst.action([RPAREN,],self.ACT_RParen1)
        subst.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,SYMREF],method=self.ACT_Add_Token)
        subst.action([COMMA,],self.ACT_Start_Done)
        subst.error(self.ACT_ExpectedComma)
        self.state(subst)

        strlen=fsmparser.PState("strlen")
        strlen.action([LPAREN,],self.ACT_LParen)
        strlen.action([RPAREN,],self.ACT_RParen2)
        strlen.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,SYMREF],method=self.ACT_Add_Token)
        strlen.error(self.ACT_ExpectedRParen)
        self.state(strlen)

        done=fsmparser.PState("done")
        done.action([EOO,EOS],self.ACT_Done)
        done.error(self.ACT_ExpectedEnd)
        self.state(done)

    def ACT_Add_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return state.state   # Stay in this state

    def ACT_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.st_token=gs.str_end()
        state.atend()

    def ACT_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operands",value)

    def ACT_ExpectedRParen(self,value,state,trace=False):
        self.ACT_Expected("right parenthesis",value)

    def ACT_ExpectedString(self,value,state,trace=False):
        self.ACT_Expected("string",value)

    def ACT_ExpectedSubString(self,value,state,trace=False):
        self.ACT_Expected("sub-string",value)

    def ACT_LParen(self,value,state,trace=False):
        gs=self.scope()
        gs.lparen(value)
        return state.state  # Stay in this state

    def ACT_RParen1(self,value,state,trace=False):
        gs=self.scope()
        gs.rparen()
        return "subst"

    def ACT_RParen2(self,value,state,trace=False):
        gs=self.scope()
        if gs._parens==0:
            self.st_len=gs.expr_end()
            return "done"
        gs.rparen()
        return "strlen"

    # Starting position arithmetic expression recognized
    def ACT_Start_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.ck_parens(value)
        self.st_start=gs.expr_end()
        return "strlen"

    # Extend the initial string token with additional content
    def ACT_String_Extend(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "more"

    # Initial character string recognized, need to determine if there is a substring
    # specification
    def ACT_String_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.str_begin(value)
        return "more"

    # Recognized the start of a substring specification, process the start position
    # arithmetic expression.
    def ACT_Sub_String_Start(self,value,state,trace=False):
        return "subst"

#class CScope(AsmFSMScope):
class CScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()

    def __str__(self):
        string="%s():" % self.__class__.__name__
        string="%s\n  st_token: %s" % (string,self.st_token)
        string="%s\n  st_start:" % string
        if len(self.st_start)==0:
            string="%s []" % string
        else:
            for tok in self.st_start:
                string="%s\n    %s" % (string,tok)
        string="%s\n  st_len:" % string 
        if len(self.st_len)==0:
            string="%s []" % string
        else:
            for tok in self.st_len:
                string="%s\n    %s" % (string,tok)
        string="%s\n  indefn:" % string
        if len(self._lextoks)==0:
            string="%s []" % string
        else:
            for tok in self._lextoks:
                string="%s\n    %s" % (string,tok)
        string="%s\n  parens: %s" % (string,self._parens)
        return string

    def init(self):
        super().init()
        self.st_token=None      # langutil smart token for single quoted string
        self.st_start=[]        # Arithmetic expression defining sub-string start
        self.st_len=[]          # Arithmetic expression defining sub-string length


#
#  +------------------------------------------------------+
#  |                                                      |
#  |   Local/Global Symbolic Variable Definition Parser   |
#  |        (GBLA, GBLB, GBLC, LCLA, LCLB, LCLC)          |
#  |                                                      |
#  +------------------------------------------------------+
#

class SymDefnParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=SymDefnScope,trace=False)

    def initialize(self):
        init=fsmparser.PState("init")
        init.action([SYMREF,],self.ACT_SymDef)
        init.action([EOO,EOS],self.ACT_Error_NoDefs)
        init.error(self.ACT_ExpectedDefn)
        self.state(init)

        more=fsmparser.PState("more")
        more.action([EOO,EOS],self.ACT_Done)
        more.action([COMMA,],self.ACT_Next_Defn)
        more.error(self.ACT_ExpectedComma)
        self.state(more)

        next=fsmparser.PState("next")
        next.action([SYMREF,],self.ACT_SymDef)
        next.error(self.ACT_ExpectedDefn)
        self.state(next)

    def __ACT_Expected(self,expected,value):
        msg="expected %s, found %s" % (expected,value.string)
        raise assembler.AsmParserError(value,msg=msg)

    def ACT_Done(self,value,state,trace=False):
        state.atend()

    def ACT_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedDefn(self,value,state,trace=False):
        self.ACT_Expected("symbolic variable definition",value)

    def ACT_Error_NoDefs(self,value,state,trace=False):
        raise assembler.AsmParserError(value,\
            msg="symbolic variable definition(s) missing")

    def ACT_Next_Defn(self,value,state,trace=False):
        return "next"

    def ACT_SymDef(self,value,state,trace=False):
        gs=self.scope()
        gs.symdefs.append(value)
        return "more"

class SymDefnScope(fsmparser.PScope):
    def __init__(self):
        super().__init__()   # Calls init() method

    def init(self):
        self.symdefs=[]      # List of SymRefToken objects identified during parse


#
#  +--------------------------------------+
#  |                                      |
#  |   Macro Parameter Statement Parser   |
#  |                                      |
#  +--------------------------------------+
#

# This FSM-based parser recognizes macro invocation parameters.  Each parameter
# element may be a one or more successive strings or a series of characters that
# do _not_ contain commas or parenthesis.  Parameter elements requiring either of
# these characters must be enclosed in single quotes as a string.  Two successive
# single quotes result in one in the string.
#
# Positional parameters may contain either a single 
class ParameterParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=ParameterScope,trace=False)

    def __Complete_String(self,gs):
        strtok=gs.str_end()
        if strtok is None:
            return
        string=strtok.convert()
        gs.sub_list.append(string)

    def __Define_Keyword(self,gs):
        if not gs.iskeyword:
            return
        if not isinstance(gs.key_parm,str):
            cls_str=assembler.eloc(self,"__Define_Keyword",module=this_module)
            raise ValueError("%s gs.key_parm must be a string: %s" \
                % (cls_str,gs.key_parm))

        symbol="&%s" % gs.key_parm
        if len(gs.sub_list) == 0:
            gs.key_parms[symbol]=""
        elif gs.islist:
            gs.key_parms[symbol]=gs.sub_list
        else:
            gs.key_parms[symbol]=gs.sub_list[0]
        gs.sub_list=[]
        gs.key_parm=None
        gs.iskeyword=False
        gs.islist=False

    def __Define_Positional(self,gs):
        if not gs.ispos:
            return 
        if len(gs.sub_list) == 0:
            gs.pos_parms.append("")
        elif gs.islist:
            gs.pos_parms.append(gs.sub_list)
        else:
            gs.pos_parms.append(gs.sub_list[0])
        gs.sub_list=[]
        gs.islist=False
        gs.ispos=False

    def __Parm_Done(self,gs):
        if gs.iskeyword:
            self.__Define_Keyword(gs)
        else:
            self.__Define_Positional(gs)

    def __Parms_Done(self,gs):
        if gs.string is not None:
            self.__Complete_String(gs)
            self.__Parm_Done(gs)
            
    def _gen_SubList_States(self,pfx,exit):
        # The left parenthesis has been recognized for the sub-list
        # Need to process the first sub-list element
        first=AsmFSMState("slst_first",pfx=pfx,exit=exit)
        first.action([COMMA,],self._ACT_Sublist_EmptyParm)
        first.action([STRING,],self._ACT_Sublist_Begin_String)
        first.action([PARM,],self._ACT_Sublist_FoundParm)
        first.action([RPAREN,],self._ACT_Sublist_Term)
        first.error(self._ACT_Sublist_ExpectedParm)
        self.state(first)

        # Checks for comma (more parms) or right parenthesis (sub-list done)
        ismore=AsmFSMState("slst_ismore",pfx=pfx,exit=exit)
        ismore.action([COMMA,],self._ACT_Sublist_MoreParms)
        ismore.action([RPAREN,],self._ACT_Sublist_Term)
        ismore.error(self._ACT_Sublist_ExpectedComma)
        self.state(ismore)

        # Have another parameter
        more=AsmFSMState("slst_more",pfx=pfx,exit=exit)
        more.action([COMMA,],self._ACT_Sublist_EmptyParm)
        more.action([STRING,],self._ACT_Sublist_Begin_String)
        more.action([PARM,],self._ACT_Sublist_FoundParm)
        more.action([RPAREN,],self._ACT_Sublist_EmptyParm_Term)
        more.error(self._ACT_Sublist_ExpectedParm)
        self.state(more)

        # Found a string so process for extensions
        st=AsmFSMState("slst_str",pfx=pfx)
        st.action([STRING,],self._ACT_Sublist_String_Continue)
        st.action([COMMA,],self._ACT_Sublist_String_Done)
        st.action([RPAREN,],self._ACT_Sublist_Term)
        st.error(self._ACT_String_Expected)
        self.state(st)
        
    def _ACT_String_Expected(self,value,state,trace=False):
        self.ACT_Expected("more of string expected",value) 

    def _ACT_String_More(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return state.name

    def _ACT_Sublist_Begin_String(self,value,state,trace=False):
        gs=self.scope()
        gs.str_begin(value)
        return state.next_state("slst_str")

    def _ACT_Sublist_EmptyParm(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append("")
        return state.next_state("slst_more")

    def _ACT_Sublist_EmptyParm_Term(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append("")
        self.__Parm_Done(gs)
        return state.exit
            
    def _ACT_Sublist_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma continuing sub-list",value)
            
    def _ACT_Sublist_ExpectedParm(self,value,state,trace=False):
        self.ACT_Expected("sub-list element",value)
        
    def _ACT_Sublist_FoundParm(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append(value.string)
        return state.next_state("slst_ismore")
        
    def _ACT_Sublist_MoreParms(self,value,state,trace=False):
        return state.next_state("slst_more")
        
    def _ACT_Sublist_String_Continue(self,value,state,trace=False):
        gs=self.scope()
        self.__Continue_String(gs,value)
        return state.next_state("slst_str")
        
    # String is done, but there are more sub-list parms
    def _ACT_Sublist_String_Done(self,value,state,trace=False):
        gs.self.scope()
        self.__Complete_String(gs)
        return state.next_state("slst_more")

    def _ACT_Sublist_Term(self,value,state,trace=False):
        gs=self.scope()
        self.__Complete_String(gs)
        self.__Parm_Done(gs)
        return state.exit

    def initialize(self):
        # Expecting a parameter or the end of the list
        init=fsmparser.PState("init")
        init.action([KEYWORD,],self.ACT_Found_Keyword)       # keyword=
        init.action([STRING,],self.ACT_String_Begin_Pos)     # 'string'
        init.action([PARM],self.ACT_Found_Positional)        # parm
        init.action([COMMA,],self.ACT_Found_Empty_Pos)       # first parm is empty
        init.action([LPAREN,],self.ACT_Pos_List_Begin)       # (  --> a sub-list
        init.error(self.ACT_ExpectedParm)
        self.state(init)

        # This state is used when a parameter is expected.  This occurs when
        # the preceding state detects the comma separating parameters.
        new_parm=fsmparser.PState("new_parm")
        new_parm.action([KEYWORD,],self.ACT_Found_Keyword)   # keyword=
        new_parm.action([STRING,],self.ACT_String_Begin_Pos) # 'string'
        new_parm.action([PARM],self.ACT_Found_Positional)    # parm
        new_parm.action([COMMA],self.ACT_Found_Empty_Pos)    #
        new_parm.action([LPAREN,],self.ACT_Pos_List_Begin)   # (  --> a sub-list
        new_parm.action([EOO,EOS],self.ACT_Done)             # end of parms, done
        self.state(new_parm)
        
        # This is state is used when the preceding state has not detected the
        # comma separating parameters, so we look for it here.
        more_parm=fsmparser.PState("more_parm")
        more_parm.action([COMMA,],self.ACT_Parm_Next)       # ...,
        more_parm.action([EOO,EOS],self.ACT_Done)           # end of input
        more_parm.error(self.ACT_ExpectedComma)
        self.state(more_parm)
   
        # Process keyword value like a positional from here on
        key_parm=fsmparser.PState("key_parm")
        key_parm.action([STRING,],self.ACT_String_Keyword_Begin)  # keyword='string'
        key_parm.action([PARM],self.ACT_Found_KeyParm)      # keyword=parm
        key_parm.action([LPAREN,],self.ACT_Key_List_Begin)  # keyword=(  --> a sub-list
        key_parm.action([COMMA,],self.ACT_FoundEmptyKey)    # keyword=,
        key_parm.action([EOO,EOS],self.ACT_FoundEmptyKey_Done)  # keyword= end of ops.
        key_parm.error(self.ACT_ExpectedKeyValue)
        self.state(key_parm)

        # Processes multiple 'strings' replacing two successive single quotes as one
        # in keyword parameters.
        more_str_kp=fsmparser.PState("more_str_kp")
        # keword partm string argument is being continued
        more_str_kp.action([STRING,],self.ACT_String_Keyword_More)
        # keyword string parameter done, more parms
        more_str_kp.action([COMMA,],self.ACT_String_Term_More_Parms)
        more_str_kp.action([EOO,EOS],self.ACT_Done)         # end of input
        more_str_kp.error(self.ACT_ExpectedMoreString)
        self.state(more_str_kp)

        # Processes multiple 'strings' replacing two successive single quotes as one
        # in keyword parameters.
        more_str_pos=fsmparser.PState("more_str_pos")
        # keword partm string argument is being continued
        more_str_pos.action([STRING,],self.ACT_String_Pos_More)
        # keyword string parameter done, more parms
        more_str_pos.action([COMMA,],self.ACT_String_Term_More_Parms)
        more_str_pos.action([EOO,EOS],self.ACT_Done)         # end of input
        more_str_pos.error(self.ACT_ExpectedMoreString)
        self.state(more_str_pos)

        self._gen_SubList_States("pos","more_parm")
        
    def Lexer(self):
        return Parsers.plexer

    def ACT_Done(self,value,state,trace=False):
        gs=self.scope()
        self.__Parms_Done(gs)
        state.atend()

    def ACT_ExpectedComma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedKeyValue(self,value,state,trace=False):
        self.ACT_Expected("keyword parameter value",value)

    def ACT_ExpectedMoreString(self,value,state,trace=False):
        self.ACT_Expected("continuation of string",value)

    def ACT_ExpectedParm(self,value,state,trace=False):
        self.ACT_Expected("keyword or positional parameter",value)

    def ACT_FoundEmptyKey(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append("")
        self.__Define_Keyword(gs)
        return "init"

    def ACT_FoundEmptyKey_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append("")
        self.__Define_Keyword(gs)
        state.atend()

    def ACT_Found_Empty_Pos(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list=[]
        self.__Define_Positional(gs)
        return "new_parm"

    # Keyword at the start of a parameter found:
    #   Remeber it and remember that this is a keyword parameter
    def ACT_Found_Keyword(self,value,state,trace=False):
        gs=self.scope()
        gs.key_parm=value.string[:-1]  # Drop off the equal sign
        gs.iskeyword=True
        return "key_parm"

    # Found the keyword's parameter value that is not a list or a string
    def ACT_Found_KeyParm(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append(value.string)
        self.__Define_Keyword(gs)
        return "more_parm"

    def ACT_Found_Positional(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list.append(value.string)
        gs.ispos=True
        self.__Define_Positional(gs)
        return "more_parm"

    def ACT_Parm_Next(self,value,state,trace=False):
        return "new_parm"

    def ACT_Key_List_Begin(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list=[]
        gs.islist=True
        return "pos_slst_first"

    def ACT_Pos_List_Begin(self,value,state,trace=False):
        gs=self.scope()
        gs.sub_list=[]
        gs.islist=True
        gs.ispos=True
        return "pos_slst_first"

    def ACT_String_Keyword_Begin(self,value,state,trace=False):
        gs=self.scope()
        gs.str_begin(value)
        return "more_str_kp"
        
    def ACT_String_Keyword_More(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "more_str_kp"

    def ACT_String_Pos_More(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "more_str_pos"

    def ACT_String_List_More(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "more_str_list"

    def ACT_String_Begin_Pos(self,value,state,trace=False):
        gs=self.scope()
        gs.ispos=True
        gs.str_begin(value)
        return "more_str_pos"
        
    # Terminates a string and continues with next parameter
    def ACT_String_Term_More_Parms(self,value,state,trace=False):
        gs=self.scope()
        self.__Complete_String(gs)
        self.__Parm_Done(gs)
        return "new_parm"   # Otherwise on to next parm

#class ParameterScope(fsmparser.PScope):
#class ParameterScope(AsmFSMScope):
class ParameterScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()  # Calls init() method

    def __str__(self):
        string="%s():" % self.__class__.__name__
        string="%s\n    positionals: %s" % (string,self.pos_parms)
        string="%s\n    keywords: %s" % (string,self.key_parms)
        return string

    def init(self):
        super().init()
     #
     # These attributes constitute the result of the parse
     #

        # Found positional parameters (a list of individual strings and sub-lists)
        self.pos_parms=[]
        # Found keyword parameters (a string or sub-list)
        self.key_parms={}      

     #
     # These attributes are used while recognizing parameters
     #

        self.islist=False        # Is True when a list is being constructed
        self.sub_list=[]

        self.iskeyword=False     # Is True when a keyword parm is being contructed
        self.key_parm=None       # Pending keyword parameter

        self.ispos=False         # Is True when a positional parm is being constructed

        self.string=None         # StringToken object being built

#
#  +--------------------------------------+
#  |                                      |
#  |   Macro Prototype Statement Parser   |
#  |                                      |
#  +--------------------------------------+
#

class PrototypeParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=PrototypeScope,trace=False)

    def initialize(self):
        # Expecting a prototype parameter or the end of the list
        init=fsmparser.PState("init")
        init.action([SYMREF,],self.ACT_Symbol_Found)
        init.action([EOS,EOO],self.ACT_Done)
        init.error(self.ACT_ExpectedParm)
        self.state(init)

        # Looking for an equal sign indicating this is a keyword parameter or
        # a comma indicating the previous positional parameter is done, or
        # the end of prototype parameters
        kywd=fsmparser.PState("kywd")
        kywd.action([COMMA,],self.ACT_Positional_Found)
        kywd.action([EQUAL,],self.ACT_Keyword_Started)
        kywd.action([EOO,EOS],self.ACT_Done)
        kywd.error(self.ACT_ExpectedKeyword)
        self.state(kywd)

        # Found the keyword's equal sign, looking for the string, a comma for the
        # next parameter or the end of the prototype parameters.
        dflt=fsmparser.PState("dflt")
        dflt.action([STRING,],self.ACT_Default_Found)
        dflt.action([COMMA,],self.ACT_Default_Empty)
        dflt.action([EOO,EOS],self.ACT_Done)
        dflt.error(self.ACT_ExpectedDefault)
        self.state(dflt)

    def ACT_Default_Empty(self,value,state,trace=False):
        gs=self.scope()
        gs.keyword()
        return "init"

    def ACT_Default_Found(self,value,state,trace=False):
        gs=self.scope()
        gs.key_parms[gs.key_parm]=value.string
        gs.key_parm=None
        return "init"

    def ACT_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.positional()  # Add a final positional if pending
        gs.keyword()     # Add a final keyword if pending
        state.atend()

    def ACT_ExpectedDefault(self,value,state,trace=False):
        self.__ACT_Expected("keyword parameter default value",value)

    def ACT_ExpectedKeyword(self,value,state,trace=False):
        self.__ACT_Expected("keyword parameter default or comma",value)

    def ACT_ExpectedParm(self,value,state,trace=False):
        self.__ACT_Expected("prototype parameter",value)

    def ACT_Keyword_Started(self,value,state,trace=False):
        gs=self.scope()
        gs.key_parm=gs.pos_parm
        gs.pos_parm=None
        return "dflt"

    def ACT_Positional_Found(self,value,state,trace=False):
        gs=self.scope()
        gs.positional()
        return "init"

    def ACT_Symbol_Found(self,value,state,trace=False):
        srmo=SymRefMO(value.mo)
        symid=srmo.symid
        if srmo.subscripted:
            raise assembler.AsmParserError(value,\
                msg="protoype statement parameter may not be subscripted: %s" % symid)
        gs=self.scope()
        gs.pos_parm=symid
        return "kywd"

    def ACT_ExpectedParm(self,value,state,trace=False):
        self.__ACT_Expected("prototype parameter",value)


class PrototypeScope(fsmparser.PScope):
    def __init__(self):
        super().__init__()  # Calls init() method

    def init(self):
        # When initially recognized, have to wait to figure out if this is a keyword
        # or positional parameter.  This attribute holds the parameter
        self.pos_parm=None
        # List of positional parameters (with initial ampersand)
        self.pos_parms=[]
        # Pending keyword parameter
        self.key_parm=None
        # Dictionary of keyword parameters (with initial ampersand) and defaults
        self.key_parms={}

    def keyword(self):
        if self.key_parm is None:
            return
        self.key_parms[self.key_parm]=""

    def positional(self):
        if self.pos_parm is None:
            return
        self.pos_parms.append(self.pos_parm)
        self.pos_parm=None


#
#  +---------------------------------------------+
#  |                                             |
#  |         Self Defining Term Recognizer       |
#  |   (SETC symbol in Arithmetic Expressions)   |
#  |                                             |
#  +---------------------------------------------+
#

class SDParser(AsmFSMParser):
    def __init__(self,dm):
        super().__init__(dm,scope=SDScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([SDDEC,SDHEX,SDBIN,SDCHR],self.ACT_SD_Token)
        init.error(self.ACT_ExpectedSD)
        self.state(init)

        end=fsmparser.PState("end")
        end.action([EOS],self.ACT_Done)
        end.error(self.ACT_ExpectedEND)
        self.state(end)

    def ACT_Done(self,value,state,trace=False):
        state.atend()

    def ACT_ExpectedEND(self,value,state,trace=False):
        self.ACT_Expected("end of self-defining term in SETC symbol",value)

    def ACT_ExpectedSD(self,value,state,trace=False):
        self.ACT_Expected("self-defining term in SETC symbol",value)

    def ACT_SD_Token(self,value,state,trace=False):
        gs=self.scope()
        gs.sdtok=value
        return "end"

class SDScope(fsmparser.PScope):
    def __init__(self):
        super().__init__()  # Calls init() method

    def init(self):
        self.sdtok=None     # The recognized self defining term
        

#
#  +------------------------------------+
#  |                                    |
#  |   Model Statement Symbol Scanner   |
#  |                                    | 
#  +------------------------------------+
#

class SymRefRepMO(object):
    # Groups             3<---->3 4-4
    # Groups            2<----------->2    
    # Groups   0--01<-----------------------15<--->5
    pattern=  "(%s)([\(](([0-9]+)|(%s))[\)])?([\.])?" % (symvar,symvar)
    def __init__(self,mo):
        self.mo=mo               # Match object from a SymRefType pattern
        self.symid=None          # Symbolic variable name
        self.subscripted=False   # True is the reference contains a subscript
        self.subscript=None      # Subscript as an integer value
        self.subsym=None         # Subscript symbolic variable if not an integer

        self.groups=groups=mo.groups()
        #print("SymRefRepMO groups: %s" % list(groups))
        if len(groups)!=6:       # This is the result of SymRefType.model pattern
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s unexpected match object groups: %s" \
                % (cls_str,list(self.groups)))
        self.symid=groups[0]
        subscript=groups[1]
            
        if self.symid is None:
            cls_str=assembler.eloc(self,"__init__",module=this_module)
            raise ValueError("%s symbolic variable: %s" % (cls_str,self.symid))

        if subscript is not None:
            # Remove the parenthesis from around subscript
            self.subscripted=True
            subscript=subscript[1:-1]
            try:
                # Convert numeric subscript (unsigned numeric self defining term)
                self.subscript=int(subscript,10)
            except ValueError:
                # If not integer, subscript is a SETA symbol
                self.subsym=subscript

    def __str__(self):
        if self.subsym is not None:
            subsym='%s' % self.subsym
        else:
            subsym="None"
        string="%s(symid='%s',subscripted=%s,subscript=%s,subsym=%s" \
            % (self.__class__.__name__,self.symid,self.subscripted,self.subscript,\
                subsym)
        string="%s\n   groups: %s" % (string,self.groups)
        return string

    # Returns the asmmacs.SymbolID object derived from the match object
    def SymID(self):
        if not self.subscripted:
            return asmmacs.SymbolID(self.symid)
        if self.subscript is None:
            # Not an integer subscript, so assume symbolic variable as the subscript
            return asmmacs.SymbolID(self.symid,subscript=self.subsym)
        # Use integer subscript
        return asmmacs.SymbolID(self.symid,subscript=self.subscript)


class SymRefPart(seqparser.Part):
    def __init__(self,mo,name):
        super().__init__(mo,name)
        self.symmo=SymRefRepMO(mo)
        self.beg=mo.start(0)       # Beginning pos matched in string
        self.end=mo.end(0)         # Ending position matched in string
    
    def __str__(self):
        return "%s" % self.symmo

    # Returns an asmmacs.SymbolID object for the located symbolic reference
    def SymID(self):
        return self.symmo.SymID()

class SymRefSearch(seqparser.SeqSearch):
    def __init__(self):
        # Matches: "&label",  "&label(0..9..)",   "&label(&sub)"
        #   or     "&label.", "&label(0..9..).",  "&label(&sub)."
        pattern=SymRefRepMO.pattern
        super().__init__("SymRefSrch",pattern,cls=SymRefPart) 


#
#  +-----------------------------+
#  |                             |
#  |   Common Parser Interface   |
#  |                             | 
#  +-----------------------------+
#

class Parsers(object):
    # Established by __init_lexers() method
    lexer=None    # Lexical analyzer used by the shared operand recognizer
    flexer=None   # Lexical analyzer used by the generic statement field recognizer
    plexer=None   # Lexical analyzer used by the macro parameter recognizer
    #csla=None     # Context sensitive lexical analyzer (all defined contexts)
    # Established by __init_parsers() method
    sdterm=None   # Self-defining term recognizer used by ArithEval.sdterm()
    def __init__(self,asm):
        self.asm=asm      # The assembler object
        self.parsers={}   # Dictionary of parsers by name (see init() method)
        self.lexers={}    # Dictionary of lexers (see __init_lexers() method)

    def __fetch_parser(self,parser):
        try:
            return self.parsers[parser]
        except KeyError:
            cls_str=assembler.eloc(self,"__parse",module=this_module)
            raise ValueError("%s undefined parser: '%s'" % (cls_str,parser))

    def __init_lexers(self,dm):
        self.lexers["lexer"]=Parsers.lexer=AsmLexer(dm).init()
        self.lexers["flexer"]=Parsers.flexer=FieldLexer(dm).init()
        self.lexers["plexer"]=Parsers.plexer=ParameterLexer(dm).init()

    def __init_parsers(self,dm):
        # Single context FSM parsers
        self.parsers["addr"]=AddressParser(dm)
        self.parsers["fields"]=FieldParser(dm)
        self.parsers["mhelp"]=MHELPParser(dm)
        self.parsers["aif"]=AIFParser(dm)
        self.parsers["ago"]=AGOParser(dm)
        self.parsers["mhelp"]=MHELPParser(dm)
        self.parsers["mnote"]=MNOTEParser(dm)
        self.parsers["parms"]=ParameterParser(dm)
        self.parsers["proto"]=PrototypeParser(dm)
        self.parsers["sdterm"]=Parsers.sdterm=SDParser(dm)
        self.parsers["seta"]=ArithParser(dm)
        self.parsers["setb"]=BinaryParser(dm)
        self.parsers["setc"]=CharParser(dm)
        self.parsers["space"]=SPACEParser(dm)
        self.parsers["symd"]=SymDefnParser(dm)
        
        # Context sensitive FSM parsers
        self.parsers["start"]=asmfsmcs.START_Parser(dm)

    def __parse(self,parser,string,scope=None):
        if isinstance(parser,str):
            try:
                fsmp=self.parsers[parser]
            except KeyError:
                cls_str=assembler.eloc(self,"__parse",module=this_module)
                raise ValueError("%s undefined parser: '%s'" % (cls_str,parser))
        else:
            fsmp=parser

        # This may raise an AsmParserError that should be caught by the caller.
        return fsmp.parse(string,scope=scope)

    def evaluate_expr(self,asm,stmt,expr,debug=False,trace=False):
        try:
            return expr.evaluate(external=asm,debug=debug,trace=False)
        except pratt2.PParserError as pe:
            # Convert PParserError into an AssemblerError
            ltok=pe.ptok.src
            msg="%s: '%s'" % (pe.msg,ltok.string)
            raise assembler.AssemblerError(line=stmt.lineno,linepos=ltok.pos,\
                msg=msg) from None
            #raise MacroError(msg=msg) from None
        except assembler.LabelError as le:
            raise assembler.AssemblerError(line=stmt.lineno,linepos=le.ltok.linepos,\
                msg=le.msg) from None

    def init(self):
        dm=self.asm.dm
        self.__init_lexers(dm)
        self.__init_parsers(dm)
        return self

    # Creates a asmfsmbp.ArithExpr object from a list of lexical token objects
    def L2ArithExpr(self,desc,stmt,ltoks=[],debug=False):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.fields.operpos

        # Note: for some unexplained reason, if left to default, tokens picks up
        # the list from the previous expr.  Force the argument to be empty
        expr=ArithExpr(desc,lineno,tokens=[])
        if __debug__:
            if debug:
                print("%s: %s expr before: %s" % (desc,lineno,expr))

        for ltok in ltoks:
            ltok.update(lineno,operpos,source)
            expr.token(ltok.atoken())

        if __debug__:
            if debug:
                print("%s: %s expr after: %s" % (desc,lineno,expr))
        return expr

    # Creates a asmfsmbp.BinaryExpr object from a list of lexical token objects
    def L2BinaryExpr(self,desc,stmt,ltoks=[],debug=False):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.fields.operpos

        # Note: for some unexplained reason, if left to default, tokens picks up
        # the list from the previous expr.  Force the argument to be empty
        expr=BinaryExpr(desc,lineno,tokens=[])
        if debug:
            print("%s: %s expr before: %s" % (desc,lineno,expr))
        for ltok in ltoks:
            ltok.update(lineno,operpos,source)
            expr.token(ltok.btoken())
        if debug:
            print("%s: %s expr after: %s" % (desc,lineno,expr))
        return expr

    # Update a lexical token with its actual position in the statement.
    # Users of the parser are encouraged to use this method rather than 
    def ltoken_update(self,stmt,ltok):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.fields.operpos
        ltok.update(lineno,operpos,source)

    # Perform a parse using the supplied FSM-based parser on statement operands.
    # Method arguments:
    #   stmt      An assembler.Stmt object
    #   parser    A asmfsmbp.FSMParser object identified by its string name
    #   scope     Specify the scope object or let the parser create its own
    #   required  Specify 'True' if the operands are required for the statement
    # Returns:
    #   1. a fsmparser.PScope object with the results of the successful parse or
    #   2. None if no operands present and operands are not required.  
    #   Caller must be aware of this second condition before attempting to process
    #   a scope object.
    # Exception:
    #   AssemblerError if the parse fails or required operands are not present
    #
    #   The AssemblerError object is generated from the information in the 
    #   assembler.Stmt object augmented by information from the
    #   asmfsmbp.AsmParserError object if available.
    def parse_operands(self,stmt,parser,scope=None,required=False):
        # If the parse is for operands then the source and string positions
        # are different than if this is a statement field parse using an FSM-based
        # parser
        flds=stmt.fields
        if flds is None:
            cls_str=assembler.eloc(self,"parse",module=this_module)
            raise ValueError("%s Stmt.fields is required: %s" \
                % (cls_str,flds))
        string=flds.operands

        # Only parse operands if they are actually present in the statement
        if string is None:
            if required: 
                raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                    msg="required operand field missing")
            else:
                return None

        try:
            # Returns a asmfsmbp.xxxScope object
            return self.__parse(parser,string,scope=scope)
        except assembler.AsmParserError as ape:
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                linepos=ape.token.linepos+flds.operpos+1,msg=ape.msg) from None

    # This is equivalent to parse_operands() but always returns a scope object.
    def parse_scope(self,stmt,parser,scope=None):
        prsr=self.__fetch_parser(parser)
        flds=stmt.fields
        assert flds is not None,\
            "%s Stmt.fields is required: %s" \
                % (assembler.eloc(self,"parse",module=this_module),flds)
        string=flds.operands

        if scope is None:
            scp=scope
        else:
            scp=prsr._init_scope()

        if string is None:
            return scp

        # There are operands to parse...
        try:
            # Returns a likely subclassed asmfsmbp.AsmFSMScope object
            return self.__parse(prsr,string,scope=scp)
        except assembler.AsmParserError as ape:
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                linepos=ape.token.linepos+flds.operpos+1,msg=ape.msg) from None

    # Perform a parse using the supplied FSM-based parser on entire statement
    # Method arguments:
    #   stmt      An assembler.Stmt object
    #   parser    A asmfsmbp.FSMParser object identified by its string name
    #   scope     Specify the scope object or let the parser create its own
    # Returns:
    #   a fsmparser.PScope object or supplied scope with the results of the successful
    #   parse.
    # Exception:
    #   AssemblerError if the parse fails
    #
    #   The AssemblerError object is generated from the information in the 
    #   assembler.Stmt object augmented by information from the
    #   asmfsmbp.AsmParserError object if available.
    def parse_statement(self,stmt,parser,scope=None):
        first=stmt.line.first()       # First (maybe only) raw input line
        #print("[%s] first: %s" % (stmt.lineno,first))
        if first.empty:
            stmt.empty=True
            return
        try:
            self.__parse(parser,first.content,scope=scope)
        except assembler.AsmParserError as ape:
            # Formation of the entire logical statement from continued lines has
            # not happened yet.  Why?  Because we need to parse the first statement
            # into its fields (which we do in this method) so that the operation
            # can be identified.  This identification is performed in 
            # the assembler.__operid() method (called after this method).  Based 
            # upon the identification, it is then known whether a macro is being
            # invoked and the alternative continuation convensions apply.  As of
            # yet the alternative macro continuation conventions are not yet
            # supported.
            # 
            # Because the error found here, without continuation conventions being
            # applied the listing has no logical line and reports "None" for the
            # statement.  To address this siutation we will now apply normal
            # continuation conventions to create the logical statement used in the
            # listing. 
            #
            # Note, if the asmlist module handled raw input lines this could go away.
            # Until then we will do it here.
            stmt.fields.normal(stmt.line)
            raise assembler.AssemblerError(source=first.source,line=stmt.lineno,\
                linepos=ape.token.linepos+1,msg=ape.msg) from None

    # Helper method for scopes that perform their own Pass 0 processing.  Its
    # primary goal is to convert an AsmParserError into an AssemblerError
    def Pass0(self,stmt,scope,debug=False):
        try:
            scope.Pass0(stmt,self,debug=debug)
        except assmebler.AsmParserError as ape:
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                 linepos=ape.token.linepos+1,msg=ape.msg) from None
            # Note: the exception assumes that the lexical token in the exception
            # has been updated to reflect actual positions within the statement.


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
