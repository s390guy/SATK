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

# This model consolidates 
#   - all lexical and 
#   - all pratt3 tokens
#   - all finite-state-machine base classes

this_module="asmtokens.py"

# Python imports: none
# SATK imports:
import fsmparser            # Access Finite-Machine-based Parsing tools
import lexer                # Access the lexical analyzer
import pratt3               # Access the generalized operator precedence evaluator

# ASMA imports:
import assembler            # Access the assembler module
import macsyms              # Access SymbolID object
import lnkbase              # Access address objects

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
label=assembler.label               # Location label
seqsym="\.%s" % label               # Macro sequence symbol recognizer
spaces="[ ]+"                       # One or more spaces
symvar="&%s" % label                # Symbolic variable recognizer
anduc="[Aa][Nn][Dd]"                # Mixed case "AND"
equc="[Ee][Qq]"                     # Mixed case "EQ"
geuc="[Gg][Ee]"                     # Mixed case "GE"
gtuc="[Gg][Tt]"                     # Mixed case "GT"
neuc="[Nn][Ee]"                     # Mixed case "NE"
ltuc="[Ll][Tt]"                     # Mixed case "LT"
leuc="[Ll][Ee]"                     # Mixed case "LE"
notuc="[Nn][Oo][Tt]"                # Mixed case "NOT"
oruc="[Oo][Rr]"                     # Mixed case "OR"
xoruc="[Xx][Oo][Rr]"                # Mixed case "XOR"
ATTR="DdIiKkLlMmNnOoSsT"            # Mixed case label and symbol attributes


#
#  +----------------------------------------+
#  |                                        |
#  |   PRATT EXPRESSION EVALUATION TOKENS   |
#  |                                        |
#  +----------------------------------------+
#


# This division operator implements the assembler specific behavior of returning
# a value of zero when division by zero occurs.  Otherwise the pratt3.PFloorDiv
# object handles the division operation.
class PAsmDiv(pratt3.PFloorDiv):
    def __init__(self,src=None):
        super().__init__(src)
    # Infix arithmetic operation: left divided by right, ignoring remainder
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        if right==0:
            return 0
        return super().calc_led(ctx,left,right,debug=debug,trace=trace)


# Pratt Literal for AmpToken
class PLitAmp(pratt3.PLit):
    def __init__(self,src):
        super().__init__(src=src)

    def value(self,external=None,debug=False,trace=False):
        return "&"


# Pratt Literal for ChrsToken
class PLitChrs(pratt3.PLit):
    def __init__(self,src):
        super().__init__(src=src)

    def value(self,external=None,debug=False,trace=False):
        return self.src.string


# This pratt literal encapsulates a complex term.  It ulitmately evaluates through
# perhaps recursive evaluations into an expression operand.  The source of this
# pratt literal is always a CTermToken object (that appears to be a lexical token).
#
# Currently these complex terms are supported:
#  - instruction operand
#  - character expression
#  - symbolic variable reference
#  - SYSLIST reference
class PLitCTerm(pratt3.PLit):
    def __init__(self,src):
        super().__init__(src=src)

    def value(self,external=None,debug=False,trace=False):
        raise NotImplementedError("%s subclass %s must supply value() method" \
            % (assembler.eloc(self,"value",module=this_module),\
                self.__class__.__name__))


# This pratt3.PLit subclass accesses the current location counter.  It is used
# in expressions where the '*' symbol is being used to reference the currne location
# (as opposed to being the multiplication operator).
class PLitCur(pratt3.PLit):
    def __init__(self,token):
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        cur=external.cur_loc.retrieve()

        assert isinstance(cur,lnkbase.Address),\
            "%s current location of statement %s not an address: %s" \
                % (assembler.eloc(self,"value",module=this_module),cur)

        if __debug__:
            if trace:
                print("%s.value() v=%s" % (self.__class__.__name__,cur))

        return cur


# Pratt Literal for single quotation mark
class PLitDblQ(pratt3.PLit):
    def __init__(self,src):
        super().__init__(src=src)

    def value(self,external=None,debug=False,trace=False):
        return "'"


# This class allows a symbol to be used as a factor within an expression.
# It retrieves from the symbol table the symbol's value and passes it to
# the Pratt expression evaluator
class PLitLabel(pratt3.PLit):
    def __init__(self,token):
        super().__init__(token)
        
        self.label=token.label  # Label being referenced
        # This class does not refernence attributes, but subclasses do
        self.attr=None          # Label attribute being referenced.

    # Return a label's assembler symbol table entry (assembler.LabelSymbol object)
    # Exception:
    #   LabelError if the symbol is not defined
    def getSTE(self,external=None,debug=False,trace=False):
        try:
            return external._getSTE_Ref(self.label,self.src.line)
            # Cross-reference label entry creation depends upon the external object:
            #  asmmacs.Invoker     - XREF entry is not generated
            #  assembler.Assembler - XREF entry is generated
        except KeyError:
            # Label not defined
            raise assembler.LabelError(self.label,ltok=self.src,msg="undefined label") \
                from None

    def value(self,external=None,debug=False,trace=False):
        ste=self.getSTE(external=external,debug=debug,trace=trace)

        # Retrieve the underlying defining object (Section, Address, int, etc.)
        value=ste.compute()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,value))
        return value


# This class allows a symbol or one of its attributes to be used as a factor within an 
# expression.  It retrieves from the symbol table the symbol's value and passes it to
# directly to the Pratt expression evaluator if no attribute was supplied.  If
# supplied, it will return the requested attribute's value.
class PLitLabelAttr(PLitLabel):
    def __init__(self,token):
        super().__init__(token)

        #self.label              # Label being referenced supplied by superclass
        self.attr=token.attr     # Upper case attribute being referenced or None

    # Treat a character attribute as a character self-defining term
    # This method is used by subclasses.
    def character(self,attr):
        return(ord(assembler.CPTRANS.a2e(attr)))

    def value(self,external=None,debug=False,trace=False):
        assert isinstance(self.attr,str),\
            "%s self.attr must be a string: %s" \
                % (assembler.eloc(self,"value",module=this_module),self.attr)

        ste=self.getSTE(external=external,debug=debug,trace=trace)

        # Retrieve the requested attribute's value
        attr_val=ste[self.attr]
        if trace:
            print("%s.value() %s'%s=%s" \
                % (assembler.eloc(self,"value",module=this_module),attr,label,value))
        return attr_val


# This class supports the label D attribute that tests for label definition.
class PLitLabelAttr_D(PLitLabelAttr):
    def __init__(self,token):
        super().__init__(token)
        
    def getSTE(self,external=None,debug=False,trace=False):
        try:
            return external._getSTE_Ref(self.label,self.src.line)
            # Cross-reference label entry creation depends upon the external object:
            #  asmmacs.Invoker     - XREF entry is not generated
            #  assembler.Assembler - XREF entry is generated
        except KeyError:
            pass
        return None

    def value(self,external=None,debug=False,trace=False):
        ste=self.getSTE(external=external,debug=debug,trace=trace)
        if ste is None:
            return 0     # Return 'False' or 0 for undefined label
        return 1         # Return 'True' or 1 for defined label


# This class supports lable O attribute which tests for operation type
class PLitLabelAttr_O(PLitLabelAttr):
    def __init__(self,token):
        super().__init__(token)
        
    def value(self,external=None,debug=False,trace=False):
        return external._getAttr_O(self.label.upper())


# This class supports lable O attribute which tests for operation type but treats
# character result as a character self-defining term.
class PLitLabelAttr_OChr(PLitLabelAttr):
    def __init__(self,token):
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        char=external._getAttr_O(self.label.upper())
        return self.character(char)


# Same as superclass, but treats a character attribute as a self defining term.
class PLitLabelAttrChr(PLitLabelAttr):
    def __init__(self,token):
        super().__init__(token)
        
    def value(self,external=None,debug=False,trace=False):
        char=super().value(external=external,debug=debug,trace=trace)
        # Attribute returns a character.  This treats is as a self-defining term
        return self.character(char)


# This pratt3 PLit object is used for all self defining terms.  It will evaluate
# the term's value when instantiated as opposed to when referenced during evaluation.
# This latter behavior is used by PLitTID and PLitSmart.  This eliminates the need
# to do the convertion evertime the expression is evaluated in a macro invocation.
class PLitSD(pratt3.PLit):
    def __init__(self,token):
        super().__init__(token)
        self.sdval=self.src.convert()   # Self-defining term's integer value
    def value(self,external=None,debug=False,trace=False):
        v=self.sdval
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v


# This pratt3 PLit object is used for all symbolic variable references.  It handles
# accessing the current macro symbol dictionary and accessing the symbol's subscript
# if provided.  ALL ACCESS ERRORS ARE DETECTED HERE.
#
# Instance arguments:
#   token    An instance of SymRefToken
class PLitSym(pratt3.PLit):
    def __init__(self,token):
        super().__init__(token)
        self.symid=None    # SymbolID to access the dictionary (see value() method)

    def __str__(self):
        return "%s(symid=%s)" % (self.__class__.__name__,self.symid)

    # Return the symbol's value from the external macro symbol dictionary.
    # Method Arguments:
    #   external   The current Invoker object used to access the symbol dictionary
    # Returns:
    #   the expression type sensitive interpretation of the referenced
    #   A_Val, B_Val or C_Val object from the symbol dictionary
    # Excpetions:
    #   Various MacroError exceptions may be triggered.  The PParser does not catch
    #   them, but they are caught by the current Invoker object in its run() method.
    def value(self,external=None,debug=False,trace=False):
        if not self.symid:
            self.symid=self.src.SymID(case=external.case)
        return external.lcls._reference(self.symid)


# This class accesses a variable symbol in the context of an arithmetic expression,
# being sensitive to xxxA, xxxB, and xxxC symbols in this contest.
class APLitSym(PLitSym):
    def __init__(self,token):
        super().__init__(token)

    # This method must be part of the pratt3.PLit object to facilitate error 
    # reporting of an invalid self defining-term.  This need complicates the 
    # implementation because the ideal place for this method is the asmmacs.C_Val
    # object.
    #
    # Returns an integer (and remembers it, in the C_Val object) of the self-
    # defining term saved in the SETC symbolic variable when used in arithmetic
    # expression.
    def sdterm(self,valo,debug=False,trace=False):
        if valo._sdvalue is not None:
            return valo._sdvalue
        aval=ArithEval.sdterm(self,valo.string())
        valo._sdvalue=aval
        return aval

    # This method is called by the pratt3 arithmetic evaluator for the symbol's value
    def value(self,external=None,debug=False,trace=False):
        if __debug__:
            if debug:
                print("%s self=%s)" \
                    % (assembler.eloc(self,"value",module=this_module),self))

        valo=super().value(external=external,debug=debug,trace=debug)
        
        if __debug__:
            if debug:
                print("%s valo: %s" \
                    % (assembler.eloc(self,"value",module=this_module),valo))

        # valo is either a A_Val, B_Val, or C_Val object
        if isinstance(valo,macsyms.C_Val):
            return self.sdterm(valo,debug=debug,trace=trace)

        return valo.value()


# This class accesses a variable symbol's attribute in the context of an arithmetic 
# expression, being sensitive to xxxA, xxxB, and xxxC symbols in this contest.
class APLitSymAttr(PLitSym):
    def __init__(self,token):
        super().__init__(token)

    # This method must be part of the pratt3.PLit object to facilitate error 
    # reporting of an invalid self defining-term.  This need complicates the 
    # implementation because the ideal place for this method is the asmmacs.C_Val
    # object.
    #
    # Returns an integer (and remembers it, in the C_Val object) of the self-
    # defining term saved in the SETC symbolic variable when used in arithmetic
    # expression.
    def sdterm(self,valo,debug=False,trace=False):
        if valo._sdvalue is not None:
            return valo._sdvalue
        aval=ArithEval.sdterm(self,valo.string())
        valo._sdvalue=aval
        return aval

    # This method is called by the pratt3 arithmetic evaluator for the symbol's value
    def value(self,external=None,debug=False,trace=False):
        if __debug__:
            if debug:
                print("%s self=%s)" \
                    % (assembler.eloc(self,"value",module=this_module),self))

        valo=super().value(external=external,debug=debug,trace=debug)
        
        if __debug__:
            if debug:
                print("%s valo: %s" \
                    % (assembler.eloc(self,"value",module=this_module),valo))

        # valo is either a A_Val, B_Val, or C_Val object
        if isinstance(valo,macsyms.C_Val):
            return self.sdterm(valo,debug=debug,trace=trace)

        return valo.value()



# This class accesses a variable symbol in the context of a binary  expression,
# being sensitive to xxxA, xxxB, and xxxC symbols in this context.
class BPLitSym(PLitSym):
    def __init__(self,token):
        super().__init__(token)

    # This method is called by the pratt3 arithmetic evaluator for the symbol's value
    def value(self,external=None,debug=False,trace=False):
        # Use the super class to access the macro symbol dictionary
        valo=super().value(external=external,debug=debug,trace=debug)
        # valo is either a A_Val, B_Val, or C_Val object
        return valo.value()


#
#  +---------------------------------------------+
#  |                                             |
#  |   PRATT EXPRESSION CLASSES AND EVALUATORS   |
#  |                                             |
#  +---------------------------------------------+
#

class ArithEval(pratt3.PParser):
    # This method tries to convert a string (PListStr) or SETC symbol value (PLitSym)
    # a pratt3.PParserError will be raised if the conversion fails.
    @staticmethod
    def sdterm(ptok,string):
        if len(string)==0:
            raise pratt3.PParserError(ptok=ptok,msg="empty SETC symbol or string")
        try:
            sdscope=Parsers.sdterm.parse(string)
        except assembler.AsmParserError as mpe:
            # Convert to a pratt parser error 
            raise pratt3.PParserError(ptok=ptok,msg=mpe.msg) from None
        # Convert the SDDEC, SDHEX, SDCHR or SDBIN lexical token into an integer
        return sdscope.sdtok.convert()

    def __init__(self):
        super().__init__()
        
        # Operator Precedence (higher takes precedence to lower)
        #   /, *
        #   +, -
        #   NOT (bit-wise)
        #   AND (bit-wise)
        #   OR  (bit-wise)
        #   XOR (bit-wise)

        # Initialize my operator precedence values
        self.operator(pratt3.PBWNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
        self.operator(PAsmDiv,lbp=50,rbp=None,symbol="/",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PMul,lbp=50,rbp=None,symbol="*",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PAdd,lbp=40,rbp=100,symbol="+",\
            isinfix=True,isunary=True)
        self.operator(pratt3.PSub,lbp=40,rbp=100,symbol="-",\
            isinfix=True,isunary=True)
        self.operator(pratt3.PBWAnd,lbp=30,rbp=None,symbol="AND",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PBWOr,lbp=30,rbp=None,symbol="OR",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PBWXor,lbp=30,rbp=None,symbol="XOR",\
            isinfix=True,isunary=False)
        # Need to add bit-wise shifts: SLA, SLL, SRA, SRL

class ArithExpr(pratt3.PExpr):
    evaluator=ArithEval()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return ArithExpr.evaluator.run(\
            self,external=external,debug=debug,trace=trace)
    def token(self,ptok):
        super().token(ptok)


class BinaryEval(pratt3.PParser):
    def __init__(self):
        super().__init__()

        # Operator Precedence (higher takes precedence to lower)
        #   /, *
        #   +, -
        #   Comparisons (logical)
        #   NOT  (logical)
        #   AND  (logical)
        #   OR   (logical)
        #   XOR  (logical)
        self.operator(pratt3.PNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
        self.operator(PAsmDiv,lbp=70,rbp=None,symbol="/",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PMul,lbp=70,rbp=None,symbol="*",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PAdd,lbp=60,rbp=100,symbol="+",\
            isinfix=True,isunary=True)
        self.operator(pratt3.PSub,lbp=60,rbp=100,symbol="-",\
            isinfix=True,isunary=True)
        self.operator(pratt3.PEQ,lbp=50,rbp=None,symbol="EQ",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PNE,lbp=50,rbp=None,symbol="NE",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PLT,lbp=50,rbp=None,symbol="LT",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PLE,lbp=50,rbp=None,symbol="LE",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PGT,lbp=50,rbp=None,symbol="GT",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PGE,lbp=50,rbp=None,symbol="GE",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PAnd,lbp=40,rbp=None,symbol="AND",\
            isinfix=True,isunary=False)
        self.operator(pratt3.POr,lbp=30,rbp=None,symbol="OR",\
            isinfix=True,isunary=False)
        self.operator(pratt3.PXor,lbp=20,rbp=None,symbol="XOR",\
            isinfix=True,isunary=False)


class BinaryExpr(pratt3.PExpr):
    evaluator=BinaryEval()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return BinaryExpr.evaluator.run(\
            self,external=external,debug=debug,trace=trace)
    def token(self,ptok):
        super().token(ptok)


# The Character Expression Evaluator duplicates the interface to the pratt3.PParser
# object utilizing the underlying Pratt evaluation tooling.  Character expressions
# do not utilize operators.  Rather a sequence of Pratt operand objects, some
# complex terms, are evaluated in the sequence they appear in the expression.  The
# results are concatenated together to create the resulting Python string.
class CharacterEval(object):
    def __init__(self):
        self.pend=pratt3.PEnd()

    # Evaluate a character expression:
    # Returns:
    #   a Python string of the resulting character expression
    # Exceptions:
    #   PParserError if a token evaluation fails.
    def run(self,expr,external=None,debug=False,trace=False,_test=False):
        ctx=pratt3.PCtx(self,expr,external=external,emu=True,debug=debug)
        # Note: The PCtx object "primes" the token input stream with the first token

        token=ctx.ptoken
        res=""      # Result string
        try:
            while not isinstance(token,pratt3.PEnd):
                #print("%s token: %s" \
                #    % (assembler.eloc(self,"run",module=this_module),token))
                value=token.nud(ctx,debug=debug,trace=trace)
                if __debug__:
                    if trace:
                        print("%s token: %s value: %s" \
                            % (assembler.eloc(self,"run",module=this_module),\
                                token,value))
                # Add the pratt token value to the result stream
                if isinstance(value,str):
                    res+=value
                elif isinstance(value,macsyms.Mac_Val):
                    res+=value.string()
                elif isinstance(value,int):
                    res="%s%s" % (res,value)
                else:
                    raise ValueError("%s unexpected result from pratt token %s: %s"\
                        % (assembler.eloc(self,"run",module=this_module),\
                            token,value))
                # Proceed to the next token.
                token=ctx.next()
        except pratt3.PEvaluationError as ee:
            raise pratt3.PParserError(ptok=token,msg=ee.msg) from None

        if __debug__:
            if trace:
                print('%s returning: "%s"' \
                    % (assembler.eloc(self,"run",module=this_module),res))

        return res   # Return the Python string result


class CharacterExpr(pratt3.PExpr):
    evaluator=CharacterEval()
    def __init__(self,desc,lineno,tokens=[],string=False):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
        self.name=desc     # A description of this expression
        self.toks=[]       # List of PToken ojbects defining the expression
        # Whether result should be a string or a macro C_Val object
        self.string=string

    # Character expressions do not utilize bindings so the expression does not
    # need initialization.  Initialization is bypassed.
    def _init(self,pparser):
        self._isinit=True

    # Evaluate the character expression
    def evaluate(self,external,debug=False,trace=False):
        result=CharacterExpr.evaluator.run(self,external=external,\
            debug=debug,trace=trace)
        if __debug__:
            if trace:
                print('%s evaluator result: "%s"' \
                    % (assembler.eloc(self,"evaluate",module=this_module),result))

        if self.string:
            res=result
        else:
            res=macsyms.C_Val(result)
        if __debug__:
            if trace:
                print('%s returning: "%s"' \
                    % (assembler.eloc(self,"evaluate",module=this_module),res))

        return res

    # Add a token or list of tokens to the expression
    def token(self,ptok):
        super().token(ptok)


#
#  +-----------------------------+
#  |                             |
#  |   LEXICAL ANALYZER TOKENS   |
#  |                             |
#  +-----------------------------+
#

EOSType=lexer.EOSType

# This is the base class for all lexical tokens created by the lexical analyzers
# within ASMA.
class LexicalToken(lexer.Token):
    def __init__(self):
        super().__init__()
        self.source=None        # Assembler input source

        # Subclass must set these values if needed using its supplied syntax() method
        self.binary=False       # Whether token represents a binary operator
        self.unary=False        # Whether token represents a unary operator

    # Generates and returns a pratt3 module PToken object for macro arithmetic 
    # expressions.  By default, it returns the token generated by the ptoken()
    # method.  A subclass must override this method to change this behavior.
    def atoken(self):
        return self.ptoken()

    # Generates and returns a pratt3 module PToken object for macro binary 
    # expressions.  By default, it returns the token generated by the ptoken()
    # method.  A subclass must override this method to change this behavior.
    def btoken(self):
        return self.ptoken()

    # Analyzes the recognized string and returns it as a native Python object.
    def convert(self):
        raise NotImplementedError("%s subclass %s must provide convert() method"\
            % (assembler.eloc(self,"convert",module=this_module),\
                self.__class__.__name__))

    # Generates and returns a pratt3 module PToken object for macro character 
    # expressions.  By default, it returns the token generated by the ptoken()
    # method.  A subclass must override this method to change this behavior.
    def ctoken(self):
        return self.ptoken()

    # This method generates a pratt3 module PToken opject for assembler arithmetic
    # expressions.  For lexical tokens that must be converted into a PToken object
    # that participates in expression  evalutations this method returns the object.
    # Lexical tokens that do not  participate in expression evaluations do not
    # require this method.
    def ptoken(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s must provide ptoken() method" \
            % (assembler.eloc(self,"ptoken",module=this_module),\
                self.__class__.__name__))

    # This method sets the operator syntax attributes.  If actual values are
    # required, the subclass must override this method.
    def syntax(self):
        pass

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

    # This updates the token position based upon a ASMPloc object
    def update_loc(self,line,loc):
        self.line=line          # This is the assembly statement line number
        self.linepos=loc.pndx
        self.source=loc.source

#
# Pseudo-Lexical Token for complex terms consisting of a primary expression and
# optionally one or more secondary expressions.  This token results when a parser
# recognizes a complex term.  Because the parser, rather than a lexical analyzer
# performs the recognition, no token type is used to create it.
# 
# A corresponding PLit token is created from this object for evaluation of the
# complex term into an expression operand during expression evaluation.

class CTermToken(LexicalToken):
    def __init__(self,primary,secondary=[]):
        self.primary=primary       # Primary TExpr object
        self.secondary=secondary   # List of secondary TExpr objects



#
# Context Dependent Semantic Operators
#

# The AND, OR, and XOR operators have two different semantics depending upon the
# context in which they are used.  In arithmetic expressions they perform bit-wise
# operations on their integer operands.  In binary expressions they perform logical
# operations on their logical operands of "True" or "False".

class LogGenToken(LexicalToken):
    bitwise_ops={"AND":pratt3.PBWAnd,
                 "OR": pratt3.PBWOr,
                 "XOR":pratt3.PBWXor}
    logical_ops={"AND":pratt3.PAnd,
                 "OR": pratt3.POr,
                 "XOR":pratt3.PXor}
    def __init__(self):
        super().__init__()

    def atoken(self):
        cls=LogGenToken.bitwise_ops[self.extract().upper()]
        return cls(src=self)

    def btoken(self):
        cls=LogGenToken.logical_ops[self.extract().upper()]
        return cls(src=self)

    # Override lexer.Token's extract() method.  Returns the logical or bit-wise
    # primary operation from the type regular expression object: AND, OR or XOR.
    def extract(self):
        groups=self.groups()
        return groups[1]


    # Returns a pratt3 PToken object with myself as the source
    def ptoken(self):
        cls=self.ptokens()[self.extract().upper()]
        return cls(src=self)

    # This method returns a dictionary for selecting the pratt token associated with
    # the "AND", "OR" and "XOR" operations.
    def ptokens(self):
        raise NotImplementedError("%s subclass %s must implement ptokens() method"\
            % (assembler.eloc(self,"ptokens",module=this_module),\
                self.__class__.__name__))
        
    def syntax(self):
        self.binary=True


class BWOpToken(LogGenToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.bitwise_ops
        
class LogicalToken(LogGenToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.logical_ops

class LogGenNotToken(LogGenToken):
    def __init__(self):
        super().__init__()

    def atoken(self):
        cls=LogicalGenToken.logical_ops[self.extract().upper()]
        tok1=cls(src=self)
        tok2=pratt3.PBWNot(src=self)
        return [tok1,tok2]

    def btoken(self):
        cls=LogicalGenToken.bitwise_ops
        tok1=cls(src=self)
        tok2=pratt3.PNot(src=self)
        return [tok1,tok2]

    def ptoken(self):
        cls=self.ptokens()[self.extract().upper()]
        tok1=cls(src=self)
        tok2=self.ptoken_not()
        return [tok1,tok2]

    # Returns the pratt Ptoken associated with the "NOT" operation
    def ptoken_not(self):
        raise NotImplementedError("%s subclass %s must implement ptoken_not() method"\
            % (assembler.eloc(self,"ptoken_not",module=this_module),\
                self.__class__.__name__))

class BWNOpToken(LogGenNotToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.bitwise_nops
    def ptoken_not(self):
        return pratt3.PBWNot(src=self)

class LogNotToken(LogGenNotToken):
    def __init__(self):
        super().__init__()
    def ptokens(self):
        return LogGenToken.logical_ops
    def ptoken_not(self):
        return pratt3.PNot(src=self)

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
        
# These classes are used to instantiate the actual types:

# Bit-wise arithmetic operators
class BWOpType(LogGenType):
    def __init__(self,debug=False):
        super().__init__("BWOP",BWOpToken,debug=debug)

# Bit-wise arithmetic not operators
class BWNOpType(LogGenNotType):
    def __init__(self,debug=False):
        super().__init__("BWNOP",BWNOpToken,debug=debug)

# Logical operators
class LogicalType(LogGenType):
    def __init__(self,debug=False):
        super().__init__("LOGICAL",LogicalToken,debug=debug)

# Logical not operators
class LogNotType(LogGenNotType):
    def __init__(self,debug=False):
        super().__init__("LOGNOT",LogNotToken,debug=debug)

#
# Lexical tokens with identical semantics within either arithmetic or binary
# expressions.
#


# &&     - Recognizes two sequential ampersands used in character expressions
class AmpToken(LexicalToken):
    def __init__(self):
        super().__init__()
        
    def ptoken(self):
        return PLitAmp(self)

class AmpType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("AMP","&&",tcls=AmpToken,debug=debug)


# +-*/   - Recognizes arithmetic expression operators
class AOperToken(LexicalToken):
    # converts an arithmetic operator as a string into a pratt3 module Operator classs
    ptokens={"+":pratt3.PAdd,
             "-":pratt3.PSub,
             "*":pratt3.PMul,
             "/":PAsmDiv}
    def __init__(self):
        super().__init__()

        # This flag used to trigger current location counter for * instead of multiply
        # The parser must recognize this condition and set theis using the
        # current() method.
        self.iscur=False

    # Indicate this token represents the current location counter ('*')
    def current(self):
        self.iscur=True
        self.binary=self.unary=False

    # Sets operator syntax settings
    def syntax(self):
        self.binary=True
        self.unary=self.string in "+-"

    # Returns a pratt3 PToken object with myself as the sourc
    def ptoken(self):
        if self.iscur:
            return PLitCur(self)
        # Add logic for Current location PToken
        cls=AOperToken.ptokens[self.extract()]
        return cls(src=self)

class AOperType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("AOPER","[\+\-\*\/]",tcls=AOperToken,debug=debug)


# Not & or ( - characters requiring separate recognition during symbolic replacement
class ChrsRepToken(LexicalToken):
    def __init__(self):
        super().__init__()

    def ptoken(self):
        return PLitChrs(self)

class ChrsRepType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("CHRSREP","[^&(]+",tcls=ChrsRepToken,debug=debug)


# Not ' or & - Fixed characters in character expression
class ChrsToken(LexicalToken):
    def __init__(self):
        super().__init__()
        
    def ptoken(self):
        return PLitChrs(self)

class ChrsType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("CHRS","[^'&]+",tcls=ChrsToken,debug=debug)


# EQ, NE, LT, LE, GT, GE - Recognizes comparison infix operators
class CompToken(LexicalToken):
    ptokens={"EQ":pratt3.PEQ,
             "NE":pratt3.PNE,
             "LT":pratt3.PLT,
             "LE":pratt3.PLE,
             "GT":pratt3.PGT,
             "GE":pratt3.PGE}
    def __init__(self):
        super().__init__()
    # Override lexer.Token's extract() method
    def extract(self):
        groups=self.groups()
        return groups[1]
        
    # Returns a pratt3 PToken object with myself as the source
    def ptoken(self):
        cls=CompToken.ptokens[self.extract().upper()]
        return cls(src=self)
        
    def syntax(self):
        self.binary=True

class CompType(lexer.Type):
    # Groups 0     1                  2
    pattern="(%s)(%s|%s|%s|%s|%s|%s)(%s)" \
        % (spaces,equc,neuc,ltuc,leuc,gtuc,geuc,spaces)
    def __init__(self,debug=False):
        super().__init__("COMPARE",CompType.pattern,tcls=CompToken,\
            mo=True,debug=debug)


# ''     - Recognizes double quotes in character expressions
class DblQuoteToken(LexicalToken):
    def __init__(self):
        super().__init__()
        
    def ctoken(self):
        return PLitDblQ(src=self)

class DblQuoteType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("DBLQUOTE","''",tcls=DblQuoteToken,debug=debug)


# DC,DS - Binary nominal value recognizer
class DCDS_Bin_Token(LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Bin_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[01]+"
        super().__init__("DCBIN",pattern,tcls=DCDS_Bin_Token,debug=debug)


# DC,DS - P, Z - Decimal signed or unsigned decimal pointed nominal value recognizer
class DCDS_Dec_Token(LexicalToken):
    signs={"U":1,"+":1,"-":-1,None:1}
    def __init__(self):
        super().__init__()
        # Set by init() method
        self.S=None         # S' attribute (digits to the right of the decimal point)
        self.fraction=None  # Fractional part of the number as a string
        self.integer=None   # Integer part of the number as a string
        self.sign=None      # Sign as a string or None
        #self.unsigned=None  # Whether the value is explicitly unsigned
        self._sign=None     # Sign factor if implicitly or explicitly signed
        self.digits=None    # Integer and fraction digits as a single string
        
        # Set by convert() method
        self.value=None

    def convert(self):
        #groups=self.groups()

        # Recognize the sign of the value
        #sign=self.sign()
        #if sign=="U":
        #    self.unsigned=True
        #try:
        #    self._sign=sign=DCDS_Dec_Token.signs[sign]
        #except KeyError:
        #    raise ValueError("%s unrecognized sign matched in re pattern: %s" \
        #        % (assembler.eloc(self,"convert",module=this_module),sign))

        # Determine the digits in the value
        #self.digits=self.dec_digits()

        # Concatenate the integer and fractions for creation of the nominal value
        # (which ignores the decimal point).
        self.digits="%s%s" % (self.integer,self.fraction)

        # Convert to a Python value
        self.value=int(self.digits,10)*self._sign
        return self.value

    #def dec_digits(self):
        #groups=self.groups()
        #fraction=groups[2]   # Fractional part of value with decimal point
        #if fraction is not None:
        #    fraction=fraction[1:]     # drop off decimal point
        #else:
        #    fraction=""    # No fractional part supplied
        # Set the number of digits to the right of the decimal point    
        #self.S=len(fraction)
        #return "%s%s" % (groups[1],fraction)

    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        # Let super classs initalize the lexical token
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        groups=self.groups()

        # Recognize the sign of the value
        sign=groups[0]
        if sign:
            self.sign=sign=sign.upper()
        try:
            self._sign=sign=DCDS_Dec_Token.signs[sign]
        except KeyError:
            raise ValueError(\
                "%s unrecognized sign matched in re pattern: %s" \
                    % (assembler.eloc(self,"convert",module=this_module),sign))

        # Extract the integer part of the number
        self.integer=groups[1]
        
        # Extract the fractional part of the number
        fraction=groups[2]   # Fractional part of value with decimal point
        if fraction is not None:
            self.fraction=fraction[1:]     # drop off decimal point
        else:
            self.fraction=""       # No fractional part supplied
        self.S=len(self.fraction)  # Set the number's Scale attribute
        
        # Decimal digits ignoring decimal point.
        self.digits="%s%s" % (self.integer,self.fraction)

    #def sign(self):
    #    sign=self.groups()[0]
    #    if sign:
    #        return sign.upper()
    #    return None

class DCDS_Dec_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern=r'([Uu+-])?([0-9]+)(\.[0-9]*)?'
        super().__init__("DCDPT",pattern,tcls=DCDS_Dec_Token,mo=True,debug=debug)


# DC,DS - X - Hex nominal value recognizer
class DCDS_Hex_Token(LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Hex_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[0-9A-Fa-f]+"
        super().__init__("DCHEX",pattern,tcls=DCDS_Hex_Token,debug=debug)


# DC,DS - Length modifier recgonizer
class DCDS_Length_Token(LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Length_Type(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("DCLEN","[Ll]",tcls=DCDS_Length_Token,debug=debug)


# DC,DS - D, F, FD, H - Fixed point signed or unsigned nominal value recognizer
class DCDS_Number_Token(LexicalToken):
    signs={"U":1,"+":1,"-":-1,None:1}
    def __init__(self):
        super().__init__()
        # Set by convert() method
        #self.unsigned=None
        self._sign=None
        self.value=None

    def digits(self):
        grps=self.mo.groups()
        return grps[1]

    def sign(self):
        grps=self.mo.groups()
        return grps[0]

    def convert(self):
        mo=self.mo
        groups=self.mo.groups()
        sign=groups[0].upper()
        if sign=="U":
            self.unsigned=True
        try:
            self.sign=sign=DCDS_Number_Token.signs[sign]
        except KeyError:
            raise ValueError("%s unrecognized sign matched in re pattern: %s" \
                % (assembler.eloc(self,"convert",module=this_module),sign))
        value=groups[1]
        self.value=int(value,10)*sign
        return self.value

class DCDS_Number_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="([Uu+-])?([0-9]+)"
        super().__init__("DCNUM",pattern,tcls=DCDS_Number_Token,mo=True,debug=debug)


# DC,DS - Single quote ' recognizer.  For many types, nominal values start and end
#         with a single quote.
class DCDS_Quote_Token(LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Quote_Type(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("DCQUOTE","'",tcls=DCDS_Quote_Token,debug=debug)


# DC,DS - Constant type recognizer
class DCDS_Type_Token(LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Types_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[Aa][Dd]?|[Bb]|[Cc][AaEe]?|[Dd]|[Ff][Dd]?|[Hh]|[Pp]"
        pattern="%s|%s" % (pattern,"[Ss][Yy]?|[Xx]|[Yy]|[Zz]")
        super().__init__("DCTYPE",pattern,tcls=DCDS_Type_Token,debug=debug)


# Recognizes the end of operands, namely, one or more spaces
class EoOperToken(LexicalToken):
    def __init__(self):
        super().__init__()

class EoOperType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("EOO",spaces,tcls=EoOperToken,mo=True,debug=debug)


# =      - Recognizes the equal sign 
class EqualToken(LexicalToken):
    def __init__(self):
        super().__init__()

class EqualType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("EQUAL","=",tcls=EqualToken,debug=debug)


# ,      - Recognizes a single comma
class CommaType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("COMMA",",",tcls=LexicalToken,debug=debug)

# LABEL  - Recgonizes an assembler label without an attribute
class LabelToken(LexicalToken):
    def __init__(self):
        super().__init__()
        
        # Supplied by init() method
        self.label=None   # Label being referenced

    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        # Let super classs initalize the lexical token
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        self.label=self.string

    def ptoken(self):
        return PLitLabel(self)

class LabelType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("LABEL",label,tcls=LabelToken,mo=True,debug=debug)


# LABEL   - Recgonizes an assembler label alone or
# X'LABEL - Recognizes an assembler label preceded by an attribute.  Attributes are
#           defined in the LabelAttrType.ATTR attribute.
class LabelAttrToken(LexicalToken):
    # Classes used for macro arithmetic expressions
    #                                     Attribute
    a_attr={"D":PLitLabelAttr_D,      #      int
            "I":PLitLabelAttr,        #      int
            "L":PLitLabelAttr,        #      int
            "M":PLitLabelAttr,        #      int
            "O":PLitLabelAttr_OChr,   #      char
            "S":PLitLabelAttr,        #      int
            "T":PLitLabelAttrChr}     #      char
    # Classes used for macro logical expressions
    #                                     Attribute
    b_attr={"D":PLitLabelAttr_D,      #      int
            "I":PLitLabelAttr,        #      int
            "L":PLitLabelAttr,        #      int
            "M":PLitLabelAttr,        #      int
            "O":PLitLabelAttr_O,      #      char
            "S":PLitLabelAttr,        #      int
            "T":PLitLabelAttr}        #      char
    # Classes used for macro logical expressions
    #                                     Attribute
    c_attr={"D":PLitLabelAttr_D,      #      int
            "I":PLitLabelAttr,        #      int
            "L":PLitLabelAttr,        #      int
            "M":PLitLabelAttr,        #      int
            "O":PLitLabelAttr_O,      #      char
            "S":PLitLabelAttr,        #      int
            "T":PLitLabelAttr}        #      char
    
    # Classes used for machine instructions and assembler directives
    #                                   Attribute
    p_attr={"D":PLitLabelAttr_D,      #      int
            "I":PLitLabelAttr,        #      int
            "L":PLitLabelAttr,        #      int
            "M":PLitLabelAttr,        #      int
            "O":PLitLabelAttr_OChr,   #      char
            "S":PLitLabelAttr,        #      int
            "T":PLitLabelAttrChr}     #      char
    def __init__(self):
        super().__init__()

        # Initialized by init() method
        self.label=None      # Case (in)sensitive label being referenced
        self.attr=None       # Attribute of the label being referenced
        
    # Access the class attribute dictionary to determine the Pratt operand 
    # class to be returned.
    def __getPLit(self,dct):
        try:
            cls=dct[self.attr]
        except KeyError:
            raise assembler.LabelError(self.label,ltok=self,\
                msg="unsupported attribute %s for assembler label: %s" \
                    % (self.attr,self.label)) from None
        return cls(self)

    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        # Let super classs initalize the lexical token
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        mogrps=self.groups()
        attr=mogrps[0]        # None or "X'" where X is the requested attribute
        if attr:
            self.attr=attr[0].upper()
        self.label=mogrps[1]  # The referenced label
        
    def atoken(self):
        if self.attr is None:
            return PLitLabel(self)
        return self.__getPLit(LabelAttrToken.a_attr)
        #try:
        #    cls=LabelAttrToken.a_attr[self.attr]
        #except KeyError:
        #    raise assembler.LabelError(self.label,ltok=self,\
        #        msg="attribute %s unsupported in macro arithmetic expressios" \
        #            % self.attr) from None
        #return cls(self)
        
    def btoken(self):
        if self.attr is None:
            return PLitLabel(self)
        return self.__getPLit(LabelAttrToken.b_attr)
        #try:
        #    cls=LabelAttrToken.b_attr[self.attr]
        #except KeyError:
        #    raise assembler.LabelError(self.label,ltok=self,\
        #        msg="attribute %s unsupported in macro logical expressios" \
        #            % self.attr) from None
        #return cls(self)

    def ctoken(self):
        # Because of how the symbolic replacement parsers work we should never
        # be here.  This is why a ValueError is raised rather than a LabelError.
        # LabelErrors are used for user generated errors.  Being here implies
        # a bug, so a ValueError is raised.
        if self.attr is None:
            # We should never be here
            raise NotImplementedError(\
                "%s label references unsupported in character expressions: %s" \
                    % (assembler.eloc(self,"ctoken",module=this_module),self.label))
        return self.__getPLit(LabelAttrToken.c_attr)
        #try:
        #    cls=LabelAttrToken.c_attr[self.attr]
        #except KeyError:
        #    raise assembler.LabelError(self.label,ltok=self,\
        #        msg="unsupported attribute %s for assembler label: %s" \
        #            % (self.attr,self.label)) from None
        #return cls(self)

    def ptoken(self):
        if self.attr is None:
            return PLitLabel(self)
        return self.__getPLit(LabelAttrToken.p_attr)
        #try:
        #    cls=LabelAttrToken.b_attr[self.attr]
        #except KeyError:
        #    raise assembler.LabelError(self.label,ltok=self,\
        #         msg="unsupported attribute %s for assembler label: %s" \
        #            % (self.attr,self.label)) from None
        #return cls(self)

# This type recognizes only labels with attributes.
class LabelAttrRefType(lexer.Type):
    def __init__(self,debug=False):
        pattern="([%s]')(%s)" % (ATTR,label)
        super().__init__("LAREF",pattern,tcls=LabelAttrToken,mo=True,debug=debug)

# This type recognizes labels with optional attributes.
class LabelAttrType(lexer.Type):
    def __init__(self,debug=False):
        pattern="([%s]')?(%s)" % (ATTR,label)
        super().__init__("LATTR",pattern,tcls=LabelAttrToken,mo=True,debug=debug)


# (      - Recognizes a single left parenthesis
class LParenToken(LexicalToken):
    def __init__(self):
        super().__init__()
    # Returns a pratt3 PLit for character replacement contexts
    def ctoken(self):
        return PLitChrs(src=self)
    # Returns a pratt3 operator object for actual expression evaluation
    def ptoken(self):
        return pratt3.PLParen(src=self)

class LParenType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("LPAREN","[\(]",tcls=LParenToken,debug=debug)
   

# LABEL&SYM  - Recgonizes an assembler label with a final symbollic variable.
# This is used exclusively by the Fields Parser to allow this construct to be
# recognized in macro body statements.
class MacLabelToken(LexicalToken):
    def __init__(self):
        super().__init__()

class MacLabelType(lexer.Type):
    def __init__(self,debug=False):
        pattern="(%s)(%s)" % (label,symvar)
        super().__init__("MACLABEL",pattern,tcls=MacLabelToken,mo=True,debug=debug)


# NOT    - Unary NOT operator
class NotToken(LexicalToken):
    def __init__(self):
        super().__init__()

    # Override lexer.Token's extract() method
    def extract(self):
        groups=self.groups()
        return groups[1]

    def atoken(self):
        return pratt3.PBWNot(src=self)

    def btoken(self):
        return pratt3.PNot(src=self)

    def syntax(self):
        self.unary=True

class NotType(lexer.Type):
    # Groups 0     1   2
    pattern="([ ]*)(%s)(%s)" % (notuc,spaces)
    def __init__(self,debug=False):
        super().__init__("NOT",NotType.pattern,tcls=NotToken,mo=True,debug=debug)


# .      - Recoginzes a single period ending a complex term
class PeriodToken(LexicalToken):
    def __init__(self):
        super().__init__()
        
class PeriodType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("PERIOD","\,",tcls=PeriodToken,debug=debug)


# '      - Recognizes a single quote starting a character expression
class QuoteToken(LexicalToken):
    def __init__(self):
        super().__init__()

class QuoteType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("QUOTE","'",tcls=QuoteToken,debug=debug)
   

# )      - Recognizes a single right parenthesis 
class RParenToken(LexicalToken):
    def __init__(self):
        super().__init__()
    # Returns a pratt3 PLit for character replacement contexts
    def ctoken(self):
        return PLitChrs(src=self)
    # Returns a pratt3 operator for actual expressions
    def ptoken(self):
        return pratt3.PRParen(src=self)

class RParenType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("RPAREN","[\)]",tcls=RParenToken,debug=debug)


# B'xxx' - Recognized binary self defining terms
class SDBinToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        # Convert BINARY self defining term to integer (ignoring leading B and quotes)
        return int(self.string[2:-1],2)
    # Returns a pratt3 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDBinType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDBIN","[Bb]'[01]+'",tcls=SDBinToken,debug=debug)


# C'x', CA'x', CE'x' - Recognizes character self-defining terms
class SDChrToken(LexicalToken):
    ebcdic=["C","CE"]
    def __init__(self):
        super().__init__()

    def convert(self):
        groups=self.groups()

        # groups 2 through 5 are the characters, one group per logical character
        chars=""
        for n in range(2,6):
            c=groups[n]
            if c is None:      # Group is absent, so no more characters
                break
            elif len(c)==1:    # Add the character to the list
                chars+=c
            elif c=="''":      # Convert double single quotes into 1 single quote
                chars+="'"
            else:
                raise ValueError('%s unexpected re match object for group %s: "%s"'\
                    % (assembler.eloc(self,"convert",module=this_module)))

        # Convert to EBCDIC if required
        desc=groups[0]
        if desc.upper() in SDChrToken.ebcdic:
            chars=assembler.CPTRANS.a2e(chars)

        # Convert the character code points into a single unsigned value
        number=0
        for c in chars:
            number=number<<8
            number+=ord(c)

        return number

    # Returns a pratt3 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDChrType(lexer.Type):
    def __init__(self,debug=False):
        pattern="([Cc][EeAa]?)(')(''|[^'])(''|[^'])?(''|[^'])?(''|[^'])?(')"
        #  Groups 0            1  2        3         4         5         6
        super().__init__("SDCHR",pattern,mo=True,tcls=SDChrToken,debug=debug)


# 9..9   - Recognizes an unsigned decimal self-defining term
class SDDecToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        return int(self.string,10)
    # Returns a pratt3 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDDecType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDDEC","[0-9]+",tcls=SDDecToken,debug=debug)


# X'xx'  - Recognizes hexadecimal self-defining terms
class SDHexToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        # Convert HEX self defining term to integer (ignoring leading H and quotes)
        return int(self.string[2:-1],16)
    # Returns a pratt3 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDHexType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDHEX","[Xx]'[0-9a-fA-F]+'",tcls=SDHexToken,debug=debug)


# .SEQSYM  - Recognizes a sequence symbol
class SeqToken(LexicalToken):
    def __init__(self):
        super().__init__()

class SeqType(lexer.Type):
     def __init__(self,debug=False):
        super().__init__("SEQSYM",seqsym,tcls=SeqToken,debug=debug)

# This token is extended to allow recognition of two adjacent singe quotes to be
# recognized as a single quote in the internal representation of a string.  This
# token requires assistance by the parser to successfully handle this case.  The way
# this works is not intuitive which is why this lengthy explanation is provided.
# It is based upon the rule that valid strings will always contain an even number
# of single quotes.
# 
# The regular expression of the StringType object recognizes this basic pattern: '.*'
# This includes two single quotes with nothing between them or any set of characters
# which are not single quotes.
#
# Applying this regular expression to a string that includes successive single quotes
# results in multiple string tokens in succession being recognized.  In this example,
# each recognized character sequence is identified by the beginning and ending
# characters in the diagram, '<' and '>'.
#
#      'X''abc'''
#      <-><---><>
#       1   2   3  <---StringToken object number
# 
# The characters actually provided in each of the StingToken object's string attribute
# is as follows, the content being surrounded here by double quotes:
#
#   1.  self.string contains  "X'"
#   2.  self.string contains  "abc'"
#   3.  self.string contains  "'"
#
# The overridden init() method performs the removal of the initial single quote,
# allowing the final quote to end up becoming the single quote as expected when
# additional characters are added to the string.
#
# The extend method() allows the next StringToken object to contribute to the 
# content of the first StringToken object.  Here is the content of the first
# StringToken object after extending it by the second and third objects:
#
#   after extending with object 2, object 1 contains  "X'abc'"
#   after extending with object 3, object 1 contains  "X'abc''"
#
# It is the application of the original StringToken object's extend() method that
# drives the need for parser assistance.
#
# The convert method() is used to access the internal representation of the
# StringToken object and this results in this final result: "X'abc'".
# This final result is the intent of the original coding.  Assigning such a string
# to a SETC symbolic variable, allows it to be used in a macro SETA statement as
# a self-defining term.
class StringToken(LexicalToken):
    def __init__(self):
        # Normally will drop the initial single quote.  Reset in a subclass if needed.
        self.drop=True   
        super().__init__()

    def atoken(self):
        cls_str=assembler.eloc(self,"atoken",module=this_module)
        raise NotImplementedError("%s TID:%s must not be recognized in "
            "arithemetic expressions" % (cls_str,self.tid))
        
    def btoken(self):
        raise NotImplementedError("%s Use of StringToken as a character expression "\
            "is deprecated in favor of macopnd.py processing" \
                % assembler.eloc(self,"btoken",module=this_module))
        return BPLitStr(self)

    def convert(self):
        # Because self.string does not contain a leading single quote having it
        # removed in the overridden init() method, it is only necessary to remove
        # the trailing single quote.
        return self.string[:-1]

    # This method allows for the logical extension of a string token, allowing two
    # successive quotes to be converted into one in the final result.
    def extend(self,ltok):
        assert isinstance(ltok,StringToken),\
            "%s 'ltok' argument must be another StringToken object: %s" \
                % (assembler.eloc(self,"extend",module=this_module),ltok)  

        self.string="%s%s" % (self.string,ltok.string)
        #print('following extend: self.string="%s"' % self.string)
        self.end=ltok.end

    # Override the lexer.token init() method to insert additional logic at that
    # point.
    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        super().init(tid,string,beg,end,\
            line=line,linepos=linepos,eols=eols,ignore=ignore,mo=mo)
        # remove the leading single quote of the string.  This forms the basis
        # of the extend method()
        if self.drop:
            self.string=self.string[1:]   # String now contains xxxxxx'

    def ptoken(self):
        cls_str=assembler.eloc(self,"ptoken",module=this_module)
        raise NotImplementedError("%s TID:%s must only be recognized in binary "
            "expressions" % (cls_str,self.tid))

class StringType(lexer.Type):
    def __init__(self,debug=False):
        pattern="'[^']*'"
        super().__init__("STRING",pattern,tcls=StringToken,debug=debug)


# DC, DS - character type nomimal value recognizer.
class DCDS_String_Token(StringToken):
    def __init__(self):
        super().__init__()
        # Because this token type uses a different pattern we do not need to drop
        # the initial quote.  The pattern used here already excludes the initial
        # quote.
        self.drop=False  # Affects asmtokens.StringToken.init() method

class DCDS_String_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[^']*'"  # everything upto and including the next single quote
        super().__init__("DCSTR",pattern,tcls=DCDS_String_Token,debug=debug)


# &SYMBOL  - Recgonizes a macro symbolic variable in the replacement context
#            or symbolic variable declaration
#
# Note: This differs from SymAttrType in that attributes are not recognized.
# This also differs from SymbolType in that the concatenation character, a period,
# is not recognized.  However SymToken and SymbolToken occur in the same contexts,
# namely model statement and quoted string symbolic replacements.
class SymToken(LexicalToken):
    def __init__(self):
        super().__init__()
        # Symbolic variable name being referenced.  See init() method.
        self.symname=None
        
    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        # Let super classs initalize the lexical token
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        # Extract results from matched string
        self.symname=self.string

class SymType(lexer.Type):
    def __init__(self,debug=False):
        pattern="&%s" % (label)
        super().__init__("SYM",pattern,tcls=SymToken,mo=False,debug=debug)


# &SYMBOL   - Recognizes a macro symbolic variable alone or
# X'&SYMBOL - Recognizes a macro symbolic variable preceded by an attribute.
#             Attributes are defined in the SymAttrType.ATTR class attribute.
class SymAttrToken(LexicalToken):
    def __init__(self):
        super().__init__()
        # See init() method
        self.symname=None     # Symbolic variable name being referenced
        self.attr=None        # Attribute character in upper case
        
    def ptoken(self):
        # REPLACE THIS OBJECT
        raise NotImplementedError(\
            "%s SymAttrToken should be part of a SymbolRef object" \
                % assembler.eloc(self,"ptoken",module=this_module))
        #return PLitLabelAttr(self)

    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        # Let super classs initalize the lexical token
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        # Extract results from match object
        mogrps=self.mo.groups()
        attr=mogrps[0]         # None or "X'" where X is the requested attribute
        # Match string includes the following ', drop it
        if attr is not None:
            self.attr=attr[0].upper()
        self.symname=mogrps[1]      # The symbol being referenced
        #print("%s symname:%s attr:%s" \
        #    % (assembler.eloc(self,"init",module=this_module),\
        #        self.symname,self.attr))

class SymAttrType(lexer.Type):
    # Add new attributes HERE!  Upper and lower case are automatically recognized
    # New attributes must be coordinated throughout the assembler but in particular
    # the assembler.Symbol class and subclasses.
    def __init__(self,debug=False):
        pattern="([%s]')?(&%s)" % (ATTR,label)
        super().__init__("SATTR",pattern,tcls=SymAttrToken,mo=True,debug=debug)

class SymAttrRefType(lexer.Type):
    # Add new attributes HERE!  Upper and lower case are automatically recognized
    # New attributes must be coordinated throughout the assembler but in particular
    # the assembler.Symbol class and subclasses.
    def __init__(self,debug=False):
        pattern="([%s]')(&%s)" % (ATTR,label)
        super().__init__("SAREF",pattern,tcls=SymAttrToken,mo=True,debug=debug)


# &SYMBOL.  - Recgonizes a macro symbolic variable in the replacement context
#
# Note a symbolic variable without the concatenation period (.) will be recognized
# by the SymAttrType class.
class SymbolToken(LexicalToken):
    def __init__(self):
        super().__init__()
        # Symbolic variable name being referenced.  See init() method
        self.symname=None
        
    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        super().init(tid,string,beg,end,line=line,linepos=linepos,eols=eols,\
                     ignore=ignore,mo=mo)
        # Extract results from match object
        mogrps=self.mo.groups()
        self.symname=mogrps[0]

class SymbolType(lexer.Type):
    def __init__(self,debug=False):
        pattern="(&%s)(\.)" % (label)
        super().__init__("SYMBOL",pattern,tcls=SymbolToken,mo=True,debug=debug)


#
#  +-----------------------------------------+
#  |                                         |
#  |   Finite-Machine Parsing Base Classes   |
#  |                                         |
#  +-----------------------------------------+
#


# Base class for AsmFSMParser scopes supporting expressions and compound strings.
# Other parsers may continue to utilize fsmparser.PScope.  It has special handling
# for elements encountered in assembly parsing, specifically, expressions and 
# strings with dual single quotes that must be converted to a single quote.
class AsmFSMScope_old(fsmparser.PScope):
    def __init__(self):
        super().__init__()

    # Raise an AsmParserError if expression parenthesis are not balanced.
    # Must be explicitly called by the scope user or the expr() method should be
    # used to ensure parenthesis are balanced.
    # Method Argument:
    #   ltok    The lexical token following the expression used by the exception
    #           for error reporting.
    # Exceptions
    #   assembler.AsmParserError raised if the expression's parenthesis are not
    #           balanced.
    def ck_parens(self,ltok):
        if self._parens!=0:
            raise assembler.AsmParserError(ltok,msg="unbalanced parenthesis")

    # Initializes the scope for use.  Automatically called by super class
    def init(self):
        self._string=None     # Accumulates a complex string with double single quotes
        self._lextoks=[]      # List of accumulated token on an expression
        self._parens=0        # Used to check for balanced parenthesis

    # Check the expression for balanced parenthesis and return the lexical token
    # list if balanced.
    # Method Argument:
    #   ltok    The lexical token following the expression used by the exception
    #           for error reporting.
    # Exceptions
    #   assembler.AsmParserError raised if the expression's parenthesis are not
    #           balanced.
    def expr(self,ltok):
        self.ck_parens(ltok)
        return self.expr_end()

    # Returns the list of accumulated tokens, presumably for an expression
    def expr_end(self):
        self._parens=0
        expr=self._lextoks
        self._lextoks=[]
        return expr

    # Process a left parenthesis in an expression.  Adds the parenthesis to the
    # expression lexical token list and increments the parenthesis count
    def lparen(self,value):
        self._parens+=1
        self.token(value)
        
    # Process a right parenthesis in an expression.  Add the parenthesis to the
    # expression lexical token list and decrements the parenthesis count
    def rparen(self,value):
        self._parens-=1
        self.token(value)

    # Start accumulation of a compound string.
    def str_begin(self,value):
        assert isinstance(value,StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_begin",module=this_module),value)
        assert self._string is None,\
            "%s '_string' attribute is not None when starting a compound string: %s" \
                % (assembler.eloc(self,"str_begin",module=this_module),\
                    self._string)

        self._string=value

    # Adds additional string content to the compound string
    def str_cont(self,value):
        assert isinstance(value,StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_cont",module=this_module),value)
        assert isinstance(self._string,StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_cont",module=this_module),self.string)

        self._string.extend(value)

    # Returns the StringToken object of the accumulated string.
    def str_end(self):
        if self._string is None:
            return
        assert isinstance(self._string,StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_end",module=this_module),self._string)

        accum=self._string
        self._string=None
        return accum

    # Returns whether a string is pending (True) or not (False)
    def str_pending(self):
        return self._string is not None

    # Adds lexical tokens to the expression token list
    def token(self,tok):
        self._lextoks.append(tok)
        
    # Updates a lexical token to reflect its position in the Stmt object's source
    # statement.
    def update(self,stmt,token):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.fields.operpos
        token.update(lineno,operpos,source)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
