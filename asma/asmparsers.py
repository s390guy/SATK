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

# This module provides the Python based mainframe assembler all of its statement
# operand parsing support.  Syntactical analysis is performed only on the operand
# field of the assembler statement, not the entire statement and not the entire source
# input.  These processing elements are provided by this module
#
#   - syntax analyzer, lexical analyzer and expression evaluator for machine 
#     instructions and most pseudo instructions (assembler directives)
#
# In all cases the output of the syntactical analyzer is a list of recognized operands
# in the form of a list of Python objects.  In the syntactical analyzer, the grammar 
# production callback methods associated perform these transformations from input 
# lexical tokens to Python object.
#
# In general, no attempt is made by the syntactical analyzer to determine if the
# recognized operands are correct in any way for the statement to which they apply.
# Whether the correct number of operands were recognized or whether a given recognized
# operand is correct for a specific statement in a specific position is also left for
# determination by the  assembler, the language processor in SATK language tools
# terminonlogy.
#
# This table summarizes the relationships of the different pieces of tool kit.  The
# parser name is how the assembler identifies it in its AsmPasses object.
#
#  Parser     Lexical                     Syntactical     Expression      Operand List
#   Name      Analyzer        Grammar       Analyzer    Parser/Evaluator     Objects
# --------   ----------   --------------  ------------  -----------------  ------------
#
# "common"  CommonLexer  common_grammar   CommonParser   ExpressionParser    Parsed
#
#
# The Pratt Operator Precedence Parser/Evaluator
# --- ----- -------- ---------- ----------------
#
# This technology, like most language parsers, operates on the concept of lexical
# tokens.  This technology recognizes only three types of lexical tokens:
#
#   - operators
#   - literals and
#   - parenthesis (left or right).
#
# Operators can support either unary or infix operations.  Unary operations are those
# where the operator takes one right-hand operand ( operator operand ).  Infix
# operations are those that require two operands ( operand operator operand).  The
# sequence of input tokens determines whether a unary or infix operation is implied 
# by the token stream.  Which type of operation is being supported is driven by
# the operator in its subclass of the generic Pratt operator.  
#
# The pratt module supports these these operators.  They are described in terms of
# Python operations because the underlying operand evaluation depends upon Python
# operations between Python operands.  Hence any Python object that can perform
# these operations through binary operator overloading methods can participate as
# operands of the Pratt Parser/Evaluator.
#
#   pratt                                                    Python     expression
#   Class                  Description                      Operator      Class
#
#   PAdd       the class for Python addition operation          +       ExpAdd
#   PDiv       the class for Python division operation          /       ExpDiv
#   PFloorDiv  the class for Python floor division operation    //      ExpFloorDiv
#   PMul       the class for Python multiplication operation    *       ExpMul
#   PSub       the class for Python substraction operation      -       ExpSub
#
# Lierals are anything that can provide as its value an object that can participate
# in the above Python operators.  Native Python int objects do.  The assembler
# Address class can also participate in these operations.  The PLit class is the
# generic pratt module literal.  All literals must be subclasses of PLit.
#
# The SATK language tools have no implicit understanding of the Pratt
# Parser/Evaluator.  The Pratt Parser/Evaluator has no knowledge of the the lexical
# tokens created by the lexer module's lexical analyzer, lexer.Lexer.  Further
# the pratt module knows nothing about grammars or grammatical productions.  The
# expressions module provides the linkage between these two different technologies.
# The expressions module provides a set of grammatical productions that a language
# processor can add to its productions for expression parsing.  The modules ExpParser
# class provides its own set of production callbacks used during LL1Parser recognition
# processing and a method that registers them with the parser.
#
# The primary role of the ExpParser provided callback methods is the transformation
# of SATK lexical tokens, instances of lexer.Token, into objects suitable for 
# use by the pratt module.  It does this by providing a set of subclasses pf the
# prass module classes that wraps the lexical token from the lexer module (via the
# parser module and its grammar).  The corresponding classes for operators is 
# identified in the previous table.  For literals (or as they are identified in the
# ExpParser supplied grammar, factors), the expression module provides two classes:
# the PLitTID and PLitSmart classes.  PLitTID is intended for direct wrapping of 
# a lexer.Token object.  PLitSmart expects one of the "smart tokens" found in the
# langutil class.  All of the subclasses used here are subclasses of PLitSmart.
# PLitSmart expects the token to support a convert() method (as do the predefined
# tokens in langutil) that convert the token into a sutiable value, in this case
# an object that supports the Python operations identified above.
#
# At the completion of the conversion process in the callbacks, the ExpParser
# creates an Expression object.  All of the conveted tokens are in a list as an
# attribute of the object.  This object is used when the expression is actually
# evaluated.  Delivering this object to the assembler is key to the assemblers
# processing of instructions and other statements.  Neither the pratt module nor
# the expression module knows how the expression fits into the overall language 
# process.  It uses its own call back to the ExpParser subclass operating like
# a parser callback to handle the delivery in the parser's global scope object.
# Refer the either of the two expression parsers below to see how this is done
# for the assembler.
#
#
# Why Multiple Lexers and Parsers?
# --- -------- ------ --- --------
#
# The "language" recognized by mainframe assemblers was initially engineered in the
# 1960's.  Formal language theory was an area of research, not an area of usable
# knowledge as it is 50 years later.  To, illustrate, the technical description of 
# what is here implemented as the pratt module resulted from research in 1973.  
# The assembler languge that arose in the 1960's is extremely context sensitive.
#
#.One of the more troubling examples involves the descriptors of DS statement storage 
# areas and assembler symbols.  For example 'PL3' is a valid DS operand and a valid
# symbol.  It becomes even more problematic when a portion of a symbol can be 
# recognize as a DS operand and the rest can not.  In the context where the complete
# symbol is required, putting the pieces back together is a mess.  No matter how the
# problem is approached, you simply _have_ to know the statement you are processing
# and that knowledge must influence how text is converted into recognized lexical
# tokens.  Ultimately, separation of these conflicts into different parsers with
# different lexers and different expression parsers was the way to provide the 
# essential context sensitivity.
#
# The next level of context sensitivity involves instructions.  Even with much more
# advanced language tools than those provided by the SATK, attempting to incorporate 
# each of the over 1000 instructions used today by mainframe systems into a single
# grammar becomes impractical even if theoretically feasible.  For this reason
# the parser used for machine instructions really only performs a well formed test
# of the operands and converts them into something more readily usable than text.
# The operands are recognized to make sense as operands of an instruction.  Whether 
# the specific operands make sense for a specific instruction in specfic positions
# is left to the assembler to decide.
#
# What one discovers about the mainframe assembler language is that it is an essenxe
# an evaluator of expressions with various context sensitive separators between 
# expressions.  For this reason, the grammars used by the individual parsers are
# extremely simple once the expression processing itself has been exported to the 
# expression module.  All modern language tools separate the recognition of a grammar
# composed of a stream of token types from the recognition of a stream of text
# characters as a strem of token types.  In the development of the mainframe
# assembler technology, likely, no such separation exists.  It is for this reason
# that most theoretical driven approaches to language recognition were abandoned.
# Grammars and parsers and lexical analyzers are used where that makes sense.  In
# other places regular expressions are used to accomplish a very specific portion
# of the analysis.  Such regular expressions may be combined with the use of finite-
# state machines designed for parsing.

# Python imports
import re           # Use Python's regular expression module

# SATK imports - PYTHONPATH must include ${SATK_DIR}/tools/lang and ${SATK_DIR}/tools
import expression   # Access the Pratt parser / LL1 parser interface
import fsmparser    # Access the finite state machine based parser
import lang         # Access SATK language tools Interface
import langutil     # Access SATK "Smart Tokens"
import lexer        # Access SATK language tools lexical analyzer
import pratt        # Access directly Pratt PTokens
import translate    # Access the ASCII-to-EBCDIC translation table
from   LL1parser import ParserAbort   # Access exception for try statement

# ASMA imports
import assembler    # Access the assembler's user error exception and Translator


#
#  +--------------------------------------------+
#  |                                            |
#  |  ASMA Shared Regular Expression Patterns   |
#  |                                            | 
#  +--------------------------------------------+
#

# These definitions provide consistency between different modules using regular
# expressions.  Use requires the assembler module to be imported
char=assembler.char                 # Special characters used in names
multiline=assembler.multiline       # Turns on multiline for start/end match
ws=assembler.ws                     # White space characters
label=assembler.label               # Label pattern with special chracters


#
#  +------------------------------+
#  |                              |
#  |  ASMA Syntactical Grammars   |
#  |                              | 
#  +------------------------------+
#
common_grammar=\
"""# ASMA Statement Operand Field Grammar
stmt -> operands* eolcmt*

# Instruction operands
operands -> operand more_operands*
operands -> EMPTY

# Instruction additional arguments
more_operands -> COMMA operand
more_operands -> EMPTY

# An instruction operand
operand -> exp opt_stg*

# Optional end-of-line comment
eolcmt -> EOLCMT
eolcmt -> EMPTY

# Optional storage argument
opt_stg -> LPARAN arg1* arg2* RPARAN
opt_stg -> EMPTY
arg1 -> exp
arg1 -> EMPTY
arg2 -> COMMA exp
arg2 -> EMPTY

# Productions from Pratt ExpressionParser follows... 

"""


#
#  +---------------------------------------+
#  |                                       |
#  |   Lexical Analyzer Tokens and Types   |
#  |                                       | 
#  +---------------------------------------+
#

# Recognized character literal in expressions:  C[E]'x' for EBCDIC or CA'x' for ASCII
class CharLitToken(lexer.Token):
    ebcdic=["C","CE"]
    def __init__(self):
        super().__init__()
    def convert(self):#        string=self.string
        # groups[1] -> descriptor
        # groups[2] -> first single quote
        # groups[3] -> the character
        # groups[4] -> second single quote
        groups=self.groups()
        char=groups[3]
        desc=groups[1]
        if desc.upper() in CharLitToken.ebcdic:
            char=assembler.CPTRANS.a2e(char)
        return ord(char)

class CharLitType(lexer.Type):
    def __init__(self,debug=False):
        res="([Cc][AaEe]?)(')([^'])(')"
        super().__init__("CHAR",res,tcls=CharLitToken,mo=True,debug=debug)


# Recognized character literal in expressions:  C[E]'x' for EBCDIC or CA'x' for ASCII
class LabelAttrToken(lexer.Token):
    def __init__(self):
        super().__init__()

    # Used by PLitLableAttr object to determine the symbol and its attribute 
    # being referened.
    def convert(self):#        string=self.string
        # groups[0] -> symbol attribute character
        # groups[1] -> the single quote
        # groups[2] -> the symbol's name
        groups=self.groups()
        attr=groups[0]
        sym=groups[2]
        return (attr,sym)

class LabelAttrType(lexer.Type):
    def __init__(self,debug=False):
        res="([%s])(')(%s)" % ("IiLl",label)
        super().__init__("LATTR",res,tcls=LabelAttrToken,mo=True,debug=debug)


# The token generated by LABEL token type
# The convert() method returns the name as a string
class LableToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string[:-1]

class EOLCmtType(lexer.Type):
    def __init__(self,debug=False):
        res="%s%s+[^\n]*$" % (multiline,ws)
        super().__init__("EOLCMT",res,tcls=langutil.WsToken,debug=debug)

# Defined token types
BIN=langutil.BinType(format="im")
CHAR=CharLitType()
COMMA=lexer.Type("COMMA",r",")
DEC=langutil.DecType(sign=True)
DIV=lexer.Type("DIV",r"/")
EMPTY=lexer.EmptyType("EMPTY")
EOLCMT=EOLCmtType()
EOS=lexer.EOSType("EOS")
HEX=langutil.HexType(format="im")
LABEL=langutil.NamType("LABEL",tcls=LableToken,first=char,special=char)
LATTR=LabelAttrType()
LPARAN=lexer.Type("LPARAN",r"\(")
MINUS=lexer.Type("MINUS",r"-")
MUL=lexer.Type("MUL",r"\*")
PLUS=lexer.Type("PLUS",r"\+")
RPARAN=lexer.Type("RPARAN",r"\)")
STR=langutil.StrType(quotes="s")


#
#  +-------------------------------------+
#  |                                     |
#  |   Expression Parser and Evaluator   |
#  |                         -           | 
#  +-------------------------------------+
#

# This is a literal whose value is determined by the current location of the 
# currently active control or dummy section.  This is the PLit that corresponds
# to the factor '*' in an expression
class PLitCur(expression.PLitSmart):
    def __init__(self,token,asm):
        super().__init__(token,asm)

    def convert(self,debug=False,trace=False):
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
        return cur

    def value(self,debug=False,trace=False):
        v=self.convert()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v


# This class allows a symbol to be used as a factor within an expression.
# It retrieves from the symbol table the symbol's value and passes it to
# the Pratt expression evaluator
class PLitLabel(expression.PLitSmart):
    def __init__(self,token,asm):
        super().__init__(token,asm)

    def convert(self,debug=False,trace=False):
        token=self.src
        label=token.extract()
        # self.external is the Assembler object
        # Note: this method will raise a KeyError excpetion if the symbol
        # is not found.
        try:
            ste=self.external._getSTE_Ref(label,token.line)
        except KeyError:
            raise assembler.LabelError(label,ltok=self.src,msg="undefined label") \
                from None

        value=ste.value()
        if isinstance(value,(assembler.SectAddr,assembler.DDisp,assembler.AbsAddr)):
            value.length=ste.attrGet("L")
            if trace:
                print("%s.convert() v=%s,length=%s" \
                    % (self.__class__.__name__,value,value.length))
        else:
        #v=self.external._getSymbol(label,token.line)
            if trace:
                print("%s.value() v=%s" % (self.__class__.__name__,value))
        return value

    # Returns the symbol name as a string (used by EQU assembly directive)
    def symbol(self):
        return self.src.extract()

    def value(self,debug=False,trace=False):
        v=self.convert()
        if trace:
            if isinstance(v,Address):
                print("%s.value() v=%s" % (self.__class__.__name__,v,v.length))
            else:
                print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

# This class allows a symbol's attribute to be used as a factor within an expression.
# It retrieves from the symbol table the symbol's attribute's value and passes it to
# the Pratt expression evaluator.
class PLitLabelAttr(expression.PLitSmart):
    def __init__(self,token,asm):
        super().__init__(token,asm)

    def convert(self,debug=False,trace=False):
        tok=self.src
        attr,label=tok.convert()
        # self.external is the Assembler object
        # Note: this method will raise a KeyError excpetion if the symbol
        # is not found. 
        try:
            v=self.external._getAttr(label,attr.upper(),tok.line)
            if trace:
                print("%s.value() v=%s" % (self.__class__.__name__,v))
        except KeyError:
            raise assembler.LabelError(lable,ltok=self.src,msg="undefined label") \
                from None
        return v

    def value(self,debug=False,trace=False):
        v=self.convert()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

#
#  +------------------------------+
#  |                              |
#  |   Common Expression Parser   |
#  |                              | 
#  +------------------------------+
#

class ExpressionParser(expression.ExpParser):
    def __init__(self,asm):
        super().__init__(external=asm)
        self.asm=asm

    # 
    #  expression.ExpParser required methods
    #

    def define_factors(self):
        # Define my supported factors
        self.factors("BIN",expression.PLitSmart)
        self.factors("HEX",expression.PLitSmart)
        self.factors("DEC",expression.PLitSmart)
        self.factors("CHAR",expression.PLitSmart)
        self.factors("LATTR",PLitLabelAttr)
        self.factors("LABEL",PLitLabel)
        self.factors("MUL",PLitCur)

    def define_operators(self):
        # Define my supported operators - precedence is defined by pratt module
        self.operators("PLUS",expression.ExpAdd)
        self.operators("DIV",expression.ExpFloorDiv)
        self.operators("MUL",expression.ExpMul)
        self.operators("MINUS",expression.ExpSub)

    def define_parans(self):
        self.parans("LPARAN","RPARAN")

    def define_unary(self):
        self.unary("MINUS")

    def expression_done(self,gs,exp,trace=False):
        cls_str="asmparsers.py - %s.expression_done() callback" \
            % self.__class__.__name__
        if trace:
            print(cls_str)
        if gs.exp_ndx>2:
            raise ValueError("%s INTERNAL expression index >2: %s" \
                % (cls_str,gs.exp_ndx))
        if trace:
            print("%s gs.expression[%s]=Expression" % (cls_str,gs.exp_ndx))
        gs.expressions[gs.exp_ndx]=exp   # Take responsibility for the 'expression'
        gs.exp_ndx+=1

    # Extract the first symbol from the expression pratt tokens
    # This is an assist for the EQU directive
    def extract_symbol(self,exp):
        if not isinstance(exp,expression.Expression):
            cls_str="asmparsers.py - %s.extract_symbol() -" % self.__class__.__name__
            raise ValueError("%s 'exp' argument must be an instance of "
                "expression.Expression: %s" % (cls_str,exp))
        ptokens=exp.ptokens
        for pt in ptokens:
            if isinstance(pt,PLitLabel):
                return pt
        return None


#
#  +-----------------------------+
#  |                             |
#  |   Common Lexical Analyzer   |
#  |                             | 
#  +-----------------------------+
#

class CommonLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()  # Initialize lang.lexer
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        # Create a list of token types to be registered with the lexical analyzer
        lst=[COMMA,LPARAN,RPARAN,PLUS,MINUS,MUL,DIV,STR]
        # Add expression factors:
        lst.extend([LATTR,BIN,CHAR,DEC,HEX,LABEL,EOLCMT])
        # Add utility token types need by LL1Parser
        lst.extend([EOS,EMPTY])

        for typ in lst:
            typ.setDebug(tdebug)
            self.type(typ)

        # Display token types if --debug ldebug set in the command line
        if self.dm.isdebug("ldebug"):
            self.types()

        return self


#
#  +----------------------------+
#  |                            |
#  |   Common Syntax Analyzer   |
#  |                            | 
#  +----------------------------+
#

class CommonParser(lang.Processor):
    def __init__(self,dm,asm):
        super().__init__()                       # Initialize lang.Processor
        self.d=dm                                # Debug Manager
        self.asm=asm                             # The assembler itself
        self.pratt=ExpressionParser(self.asm)    # Interface to Pratt parser
        self.init()  # Create and initialize the lang.Language instance

#
#  These methods are called during parsing
#
    def filter(self,gs,tok):
        # Because the lexical analyzer processes only one line, its line number will
        # always be 1.  The true input line number is passed in the global scope
        # instance. We update the Token instance with the real line number here.
        tok.line=gs.lineno        # Update with input line no
        tok.linepos+=gs.linepos   # Update with the input line pos
        if gs.dm.isdebug("tokens"):
            print(tok)
        return tok

#
#  These callback methods are used to create the language processor
#  They are triggered by self.init() and called in this order.
#

    # call back to configure the lang.Language instance.  Register call backs here.
    def configure(self,lang):
        # Register callback methods:
        #    cbreg(pid,point,method)
        lang.cbreg("stmt","beg",self.stmt_begin)
        lang.cbreg("operands","beg",self.operands_begin)
        lang.cbreg("operands","end",self.operands_end)
        lang.cbreg("more_operands","beg",self.more_operands_begin)
        lang.cbreg("more_operands","token",self.more_operands_token)
        lang.cbreg("more_operands","end",self.more_operands_end)
        lang.cbreg("operand","beg",self.operand_begin)
        lang.cbreg("operand","end",self.operand_end)
        lang.cbreg("opt_stg","beg",self.opt_stg_begin)
        lang.cbreg("opt_stg","token",self.opt_stg_token)
        lang.cbreg("opt_stg","end",self.opt_stg_end)
        lang.cbreg("arg1","beg",self.arg1_begin)
        lang.cbreg("arg1","end",self.arg1_end)
        lang.cbreg("arg2","beg",self.arg2_begin)
        lang.cbreg("arg2","token",self.arg2_token)
        lang.cbreg("arg2","end",self.arg2_end)

        # Set up expression parser's callbacks
        self.pratt.callbacks(lang)

        return self.d  # Return my debug manager

    # Create my lexer - called by the lang.Language.create() method 
    def create_lexer(self):
        return CommonLexer(self.d).init()

    # Define the parser's grammar
    def define_parser(self):

# Note: the rather imature parser requires a non-terminal that can produce empty to
# be marked with the '*' repition designator.  It does not excpet '?'.  The 
# presentation of empty terminates the production only when the '*' is present.
# This deserves more research but this works for now.

        g=common_grammar+self.pratt.get_grammar()
        return (g,"stmt")

    #
    # Common methods used by callbacks
    #

    def operand_init(self,gs,trace=False):
        if trace:
            cls_str="asmparsers.py - %s.operand_init()" % self.__class__.__name__
            print(cls_str)
        gs.expressions=[None,None,None]
        gs.exp_ndx=0
        gs.expression=None

    def operand_new(self,gs,trace=False):
        if trace:
            cls_str="asmparsers.py - %s.operand_new()" % self.__class__.__name__
            print(cls_str)
        gs.cur_operand=None
        stmt=gs.stmt
        if gs.operands==gs.next_oprndx:
            raise assembler.AssemblerError(line=gs.lineno,msg="too many operands")
        try:
            gs.cur_operand=stmt.get_operand(gs.next_oprndx)
        except IndexError:
            cls_str="asmparsers.py - %s.new_operand() -" % self.__class__.__name__
            raise ValueError("%s INTERNAL operand not supported: %s" \
                % (cls_str,gs.next_oprndx)) from None
        gs.next_oprndx+=1

        self.operand_init(gs,trace=trace)

    def operand_done(self,gs,trace=False):
        cls_str="asmparsers.py - %s.operand_done()" % self.__class__.__name__
        if trace:
            print(cls_str)
        operand=gs.cur_operand
        exprs=gs.expressions

        # Make sure what I am sending back to the assembler is correct.  If
        # any of these tests faile, there is a problem in the callback routines.
        if not isinstance(exprs,list):
            raise ValueError("%s expression list is not a list: %s" % (cls_str,exprs))
        if len(exprs)!=3:
            raise ValueError("%s list of expressions not of length three: %s" \
                % (cls_str, exprs))
        for e in exprs:
            if e is not None and not isinstance(e,expression.Expression):
                raise ValueError("%s failed to deliver Expression instance: %s" \
                    % (cls_str,e))
 
        parsed=Parsed(operand,exprs=exprs)
        if trace:
            print("%s gs.parsed %s objects after appending: %s" \
                % (cls_str,len(gs.parsed)+1,parsed))

        gs.parsed.append(parsed)

    #
    # Parser Callback Methods
    #
    # Method signatures:
    #    "beg"      def _beg(self,gs,pid):
    #    "empty"    def _empty(self,gs,pid,n):
    #    "trying"   def _trying(self,gs,pid,n,last=False):
    #    "token"    def _token(self,gs,pid,n,token):
    #    "error"    def _error(self,gs,pid,n,token):
    #    "found"    def _found(self,gs,pid,n,last=False):
    #    "failing   def _failing(self,gs,pid,n,eo=[],last=False):
    #    "end"      def _end(self,gs,pid,failed=False,eo=[]):

    #
    def stmt_begin(self,gs,pid):
        # global scope object has some initialization in Assembler.__parse() method
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.stmt_begin()" % self.__class__.__name__
            print(cls_str)
        gs.parsed=[]
        gs.next_oprndx=0
        gs.cur_exp=None

    def stmt_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.stmt_end()" % self.__class__.__name__
            print(cls_str)
        return False

    def operands_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.operands_beg()" % self.__class__.__name__
            print(cls_str)

    def operands_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.operands_end() -" % self.__class__.__name__
            print("%s failed=%s" % (cls_str,failed))

        if failed or len(eo)!=0:
            return False  # I am not handling the error and doing nothing
        self.operand_done(gs,trace=trace)

    def more_operands_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.more_operands_begin()" \
                % self.__class__.__name__
            print(cls_str)

    def more_operands_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.more_operands_token() -" \
                % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))

        # We found the comma in the more_operands production.  This means the 
        # previous operand is done and should be completed.
        if token.tid == "COMMA":
            self.operand_done(gs,trace=trace)

    def more_operands_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.more_operands_end()" % self.__class__.__name__
            print(cls_str)
        return False

    def operand_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.operand_begin()" % self.__class__.__name__
            print(cls_str)

        self.operand_new(gs,trace=trace)

    def operand_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.operand_end()" % self.__class__.__name__
            print(cls_str)

    def opt_stg_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.opt_stg_begin()" % self.__class__.__name__
            print(cls_str)

    def opt_stg_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.opt_stg_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))

    def opt_stg_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.opt_stg_end()" % self.__class__.__name__
            print(cls_str)

    def arg1_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.arg1_begin()" % self.__class__.__name__
            print(cls_str)

    def arg1_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.arg1_end()" % self.__class__.__name__
            print(cls_str)
        return False

    def arg2_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.arg2_begin()" % self.__class__.__name__
            print(cls_str)

    def arg2_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.opt_stg_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))

    def arg2_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.arg2_end()" % self.__class__.__name__
            print(cls_str)
        return False


#
#  +--------------------------------------+
#  |                                      |
#  |   Parsed Statement Related Classes   |
#  |                                      | 
#  +--------------------------------------+
#

# The assembler statement operand field consists in all cases of a sequence of 
# comma separated operands.  Each parser produces an object corresponding to the
# recognized text of one of these source statement operands.
#
# As the result of the parsing process, each parser returns its global scope
# object.  Within the object, the parser provides a list of these objects named
# 'parsed'.  Assembler directives (except for the DS and DC directives) and machine 
# instruction will find an instance of the Parsed class corresponding to each source 
# statement operand.  The DC and DS statements will find an instance of the DSDC class. 
#
# Each assembler pass method used to process an instruction or directive must process
# the list in a way meaningful to its definition.  Some directives will do this
# in pass 1.  Some will do it in pass 2.  Some will do it in both passes.  Refer the
# the various '_directive_pass1" or "_directive_pass1" methods for the details.

# This class encapsulates the results of parsing a SINGLE operand.  It is the 
# interface between the statement and the statement's operands within the statement
# pass procesing methods.
class Parsed(object):
    def __init__(self,operand,exprs=[]):
        cls_str="asmparsers.py - %s.__init__() -" % self.__class__.__name__

        # Perform sanity checks on output from the parser
        if not isinstance(operand,\
                         (assembler.Single,\
                          assembler.Storage,\
                          assembler.StorageExt,\
                          assembler.SingleAny,\
                          assembler.SingleAddress,
                          assembler.SingleRelImed)):
            raise ValueError("%s 'operand' argument must be an Operand instance: %s"\
                % (cls_str,operand))
        if not isinstance(exprs,list):
            raise ValueError("%s 'exprs' argument must be a list: %s" \
                % (cls_str,exprs))
        for x in exprs:
            if ( not isinstance(x,expression.Expression) ) and ( x is not None ):
                raise ValueError("%s 'exprs' element not None or "
                    "expression.Expression instance: %s" % (cls_str,x))

        # Arguments OK so set attributes
        self.operand=operand   # An instance of Operand
        self.exprs=exprs       # list of Expression instances created by parser.

    def __str__(self):
        return "%s(operand=%s,exprs=%s)" \
            % (self.__class__.__name__,self.operand,self.exprs)

    # This method determines if the parsed list of Expression instances makes sense
    # for the type of operand.  It returns True if the operand type and expresions
    # makes sence.  Returns False otherwise.
    def validate_operand(self,line,n,trace=False):
        operand=self.operand
        ok=operand.validate_source(self.exprs,trace=trace)
        if not ok:
            raise assembler.AssemblerError(line=line,msg=operand.source_error())
        return


#
#  +-----------------------------------------------+
#  |                                               |
#  |   FSM-based Parsers for Individual Contexts   |
#  |                                               | 
#  +-----------------------------------------------+
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
        msg="expected %s, found " % expected
        if found is None:
            if isinstance(value,EoOperToken):
                msg="%s%s" % (msg,"end of operands")
            elif isinstance(value,lexer.EOS):
                msg="%s%s" % (msg,"end of statement")
            else:
                msg='%s"%s"' % (msg,value.string)
        else:
            msg="%s%s" % (msg,found)
        raise MacroParserError(value,msg=msg)

    # This method returns the default lexical analyzer used by all macro statements.
    # Override this method to utilize a different lexical analyzer.
    def Lexer(self):
        return assembler.Assembler.lexer


if __name__ == "__main__":
    raise NotImplementedError("asmparsers.py - intended for import use only")
