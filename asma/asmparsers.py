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

# This module provides the Python based mainframe assembler all of its statement
# operand parsing support.  Syntactical analysis is performed only on the operand
# field of the assembler statement, not the entire statement and not the entire source
# input.  These processing elements are provided by this module
#
#   - syntax analyzer, lexical analyzer and expression evaluator for machine 
#     instructions and most pseudo instructions (assembler directives)
#   - syntax analyzer, lexical analyzer and expression evaluator for the DC assembler 
#     directive
#   - syntax analyzer and lexical analyzer for the DS assembler directive
#
# In all cases the output of the syntactical analyzer is a list of recognized operands
# in the form of a list of Python objects.  In each syntactical analyzer, the grammar 
# production callback methods associated perform these transformations from input 
# lexical tokens to Python object.
#
# In general, no attempt is made by the syntactical analyzer to determine if the
# recognized operands are correct in any way for the statement to which they apply.
# Whether the correct number of operands were recognized or whether a given recognized
# operand is correct for a specific statement in a specific position is also left for
# determination by the  aseembler, the language processor in SATK language tools
# terminonlogy.  
#
# For the DC and DS statements, being more narrowly focused, the Python object 
# resulting from the parse is always correct for the statement.  As in the general
# case, whether the number of operands is correct (at least one) for these statements
# is left for the assembler to determine outside of the syntactical analyzer
# processing.
#
# This table summarizes the relationships of the different pieces of tool kit.  The
# parser name is how the assembler identifies it in its AsmPasses object.
#
#  Parser     Lexical                     Syntactical     Expression      Operand List
#   Name      Analyzer        Grammar       Analyzer    Parser/Evaluator     Objects
# --------   ----------   --------------  ------------  -----------------  ------------
#
# "common"  CommonLexer  common_grammar   CommonParser   ExpressionParser    Parsed
#   "dc"      DCLexer      dc_grammar       DCParser    DCExpressionParser    DCDS
#   "ds"      DSLexer      ds_grammar       DSParser        (not used)        DCDS
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
# symbol is required, putting the pieces back to gether is a mess.  No matter how the
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
# of the analysis.

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
opend=assembler.opend               # End of a statements operands

# Template user must provide DS type(s)
ds_template="([0-9]+)?(%s)([Ll][0-9]+)?"
# User must provide DC type(s) and the characters that may appear between quotes 
dc_template="([0-9]+)?(%s)([Ll][0-9]+)?('%s+')"


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

dc_grammar=\
"""# ASMA DC Statement Operand Field Grammar
dc_stmt -> dc_oper_items* eolcmt*

# Optional end-of-line comment
eolcmt -> EOLCMT
eolcmt -> EMPTY

# DC/DS operands
dc_oper_items -> dc_operand dc_operands*
dc_oper_items -> EMPTY

# DC operands
dc_operands -> COMMA dc_operand
dc_operands -> EMPTY

# A DC operand
dc_operand -> DCA exp_list RPARAN
dc_operand -> DCB
dc_operand -> DCC
dc_operand -> DCF
dc_operand -> DCH
dc_operand -> DCP
dc_operand -> DCX
dc_operand -> DCZ

# DC ADCON Expression List
exp_list -> exp exprs*
exprs    -> COMMA exp
exprs    -> EMPTY

# Productions from Pratt ExpressionParser follows... 

"""

ds_grammar=\
"""# ASMA DS Statement Operand Field Grammar
ds_stmt -> ds_desc ds_operands* eolcmt*

# Optional end-of-line comment
eolcmt -> EOLCMT
eolcmt -> EMPTY

# DS operands
ds_operands -> COMMA ds_desc
ds_operands -> EMPTY

ds_desc -> DSDESC

"""

#
#  +-----------------+
#  |                 |
#  |   Label Error   |
#  |                 | 
#  +-----------------+
#

class LableError(Exception):
    def __init__(self,label,ltok=None,msg=""):
        self.msg=msg         # Text associated with the error
        self.ltok=ltok       # Lexical token where label occurs
        self.label=label     # Label for which error is detected
        string="%s: %s" % (self.msg,self.label)
        super().__init__(string)

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

# DS/DC base description token used directlye for all DS operands and DC ADCON 
# descriptor.  Subclassed for all other DC constants by DCOperandToken.
class DescToken(lexer.Token):

    # Returns a tuple: (dup,styp,length):
    #   dup     The duplicatin factor as an integer or None if absent
    #   styp    The storage type as a string
    #   length  Length as either None or an integer
    @staticmethod
    def getDescriptor(groups):
        # re match object groups:
        #   groups[0] -> duplication factor: None or string
        #   groups[1] -> storage type as a string, never None
        #   groups[2] -> storage length as None or a string starting with L
        dup=groups[0]
        if dup is not None:
            dup=int(dup)
        length=groups[2]
        if length is not None:
            length=int(length[1:])  # Convert to an integer after dropping the L
        return (dup,groups[1],length)

    def __init__(self):
        super().__init__()

    def descriptor(self):
        return DescToken.getDescriptor(self.groups())

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

# This class is used as a constant instead of a string for DC constants that
# have signed values, types: F, FD, H, P, and Z.
# This class primarily saves all of the work on constant analysis for later use.
class Signed(object):
    sign_char={"+":1,"-":-1,None:1}
    def __init__(self,sign,digits):
        self.sign=sign           # Sign of the constant '+' or '-' or None 
        self.digits=digits       # String of decimal digits
    def sign_factor(self):
        return Signed.sign_char[self.sign]  

# DC Operand used for all DC operands other than ADCON (which uses DescToken)
# Because of the need to fold into the lexical analyzer the recognition of most
# all DC operands, additional validation checks must be performed in any LL1 parser
# callback method that processes these tokens.
#
# Validation involves separating the constant string (coded between two single
# quotation marks) into separate constants and ensure no empty constants exist.
# An empty constant exists if there are two successive commas without any intervening
# text.  Some operands require additional processing because the lexical analyzer is
# only able to ensure that the correct characters are coded between the single quotes
# but not that they are properly structured for the type of constant.  The token
# id is used to diffentiate these requirements.

DCFHValidateRe=re.compile(r'([+-])?([0-9]+)')
DCPZValidateRe=re.compile(r'([+-])?([0-9]+)(\.[0-9]*)?')
class DCOperandToken(DescToken):
    # This dictionary provides a tuple based upon TID: (split,re)
    #   split  If True the constants must be separated where there are commas
    #   re     If provided (not None), the compiled re will validate a separated 
    #          constant.
    val={"DCB":(True,None),
         "DCC":(False,None),
         "DCF":(True,DCFHValidateRe),
         "DCH":(True,DCFHValidateRe),
         "DCX":(True,None),
         "DCP":(True,DCPZValidateRe),
         "DCZ":(True,DCPZValidateRe)}
    packed=["DCP","DCZ"]
    def __init__(self):
        super().__init__()

    # This method returns a tuple (desc_tuple,clist)
    #   desc   This is itself a tuple, the descriptor tuple
    #   clist  This is a list of constant strings or Signed instances.
    def constants(self,debug=False):
        # re match object groups:
        #              description    string of...      May be None?    Method
        # groups[0] -> duplication    '99.."                 yes      descriptor
        # groups[1] -> type           type                   no       descriptor
        # groups[2] -> length         'L9.."                 yes      descriptor
        # groups[3] -> constant       char with quotes       no       constants
        if debug:
            cls_str="asmparsers.py - %s.constants() -" % self.__class__.__name__
            print("%s %s" % (cls_str,self))
        mo=self.match()                   # Get the whole match object
        groups=mo.groups()                # Here are the match groups
        desc=self.getDescriptor(groups)   # Get descriptor tuple
        con_str=groups[3]                    # Constant string
        con_str=con_str[1:-1]                # Drop single quotes from ends
        con_start=mo.start(4)+self.linepos   # Constant pos in statement line

        # Determine how to process the constant(s)
        split,res=DCOperandToken.val[self.tid]

        # Split constants as needed and detect any empty constants
        strings=[]
        if split:
            s=con_str.split(",")
            for string in s:
                if len(string)==0:
                    raise assembler.AssemblerError(line=self.line,linepos=con_start,\
                        msg="empty constant between two commas in DC operand")
                strings.append(string)
        else:
            strings.append(con_str)   # The whole constant string is one constant

        # Perform constant validation
        if res is None:
            # B, C and X types
            return (desc,strings)     # Return descriptor and constant strings

        scons=[]
        for con in strings:
            cmo=res.match(con)         # Use the match object to match constant
            if cmo is None:
                raise assembler.AssemblerError(line=self.line,linepos=con_start,\
                    msg="invalid %s-type constant: '%s'" % (desc[1],con))
            sgrps=cmo.groups()
            if debug:
                print("%s constant match groups: %s" % (cls_str,sgrps))
            if self.tid in DCOperandToken.packed:
                # P or Z types
                #
                # Note this process does not preserve decimal point precision.
                # The decimal point is cosmetic.  This is consistent with legacy 
                # mainframe handling of packed or zones decimal constants.
                fraction=sgrps[2]
                if fraction is not None:
                    fraction=fraction[1:]     # drop off decimal
                else:
                    fraction=""
                digits="%s%s" % (sgrps[1],fraction)
                so=Signed(sgrps[0],digits)
                scons.append(so)
            else:
                # F, FD or H types
                sign=sgrps[0]
                digits=sgrps[1]
                so=Signed(sign,digits)
                scons.append(so)

        return (desc,scons)          # Return descriptor and Signed objects


# DS Descriptor token type
class DSDescType(lexer.Type):
    def __init__(self,debug=False):
        #ds_desc=ds_template \
        #% "[Bb]|[Hh]|[Pp]|[Xx]|[Zz]|[Aa][Dd]?|[Cc][AaEe]?|[Ff][Dd]?"
        ds_desc=ds_template \
            % "[Bb]|[Dd]|[Hh]|[Pp]|[Xx]|[Zz]|[Aa][Dd]?|[Cc][AaEe]?|[Ff][Dd]?"
        super().__init__("DSDESC",ds_desc,tcls=DescToken,mo=True,debug=debug)

# DC ADCON Descriptor token type
class DCAdconType(lexer.Type):
    def __init__(self,debug=False):
        dc_adcon="%s%s" % (ds_template % "[Aa][Dd]?","(\()")
        super().__init__("DCA",dc_adcon,tcls=DescToken,mo=True,debug=debug)

# DC BINARY OPERAND token type
class DCBinaryType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Bb]","[,01]")
        super().__init__("DCB",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC CHARACTER OPERAND token type
class DCCharType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Cc][AaEe]?","[^']")
        super().__init__("DCC",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC FIXED POINT BINARY OPERAND token type - fullword or doubleword
class DCFullType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Ff][Dd]?","[,0-9+-]")
        super().__init__("DCF",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC FIXED POINT BINARY OPERAND token type - halfword
class DCHalfType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Hh]","[,0-9+-]")
        super().__init__("DCH",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC HEX OPERAND token type
class DCHexType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Xx]","[,0-9A-Fa-f]")
        super().__init__("DCX",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC PACKED OPERAND token type
class DCPackedType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Pp]","[,0-9+-\.]")
        super().__init__("DCP",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

# DC PACKED OPERAND token type
class DCZonedType(lexer.Type):
    def __init__(self,debug=False):
        dc_opr=dc_template % ("[Zz]","[,0-9+-\.]")
        super().__init__("DCZ",dc_opr,tcls=DCOperandToken,mo=True,debug=debug)

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

# DS Descriptor token type
DSDESC=DSDescType()

# DC OPERAND token type (entire operand, not just the descriptor)
DCA=DCAdconType()
DCB=DCBinaryType()
DCC=DCCharType()
DCF=DCFullType()
DCH=DCHalfType()
DCP=DCPackedType()
DCX=DCHexType()
DCZ=DCZonedType()

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

# Due to lexical recognition overlap, the strings recognized by HEX literal token gets
# matched by the DCX token used within DC operands.  This class allows such tokens
# to be accepted by the Pratt factor productions when in use by the DC syntactical
# analyzer, DCParser.
class PLitDC(expression.PLitSmart):
    base={"X":16,"B":2}
    chars=["C","CE","CA"]
    def __init__(self,token,asm):
        super().__init__(token,asm)
        groups=self.src.groups()
        # A valid literal does not have a duplication or length in ASMA
        if groups[0] is not None or groups[2] is not None:
            raise assembler.AssemblerError(line=token.lineno,linepos=token.linepos,\
                msg="constant may not be used in an expression")
        literal=groups[3]
        self.literal=literal[1:-1]   # Drop off starting and ending quotes
        self.dctype=groups[1]        # Extract the DC type
        if self.dctype in PLitDC.chars and len(self.literal) !=1:
            raise assembler.AssemblerError(line=token.lineno,linepos=token.linepos,\
                msg="character literal restricted to one character: '%s'" %
                     self.literal)

    def convert(self,debug=False,trace=False):
        dctype=self.dctype

        if dctype == "CA":
            v=ord(self.literal)
        elif dctype == "C" or dctype == "CE":
            v=ord(assembler.CPTRANS.a2e(self.literal))
        else:
            b=PLitDC.base[dctype]
            v=int(self.literal,b)

        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

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
            raise LableError(label,ltok=self.src,msg="undefined label") from None

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
            raise LableError(lable,ltok=self.src,msg="undefined label")
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
#  +--------------------------+
#  |                          |
#  |   DC Expression Parser   |
#  |                          | 
#  +--------------------------+
#

class DCExpressionParser(ExpressionParser):
    def __init__(self,asm):
        super().__init__(asm)
        # Inherits from ExpressionParser its define_operators and define_parans methods

    # 
    #  expression.ExpParser required method
    #

    def define_factors(self):
        # Define my supported factors
        self.factors("DEC",expression.PLitSmart)
        self.factors("DCB",PLitDC)
        self.factors("DCX",PLitDC)
        self.factors("DCC",PLitDC)
        self.factors("LATTR",PLitLabelAttr)
        self.factors("LABEL",PLitLabel)
        self.factors("MUL",PLitCur)

    def define_unary(self): pass

    def expression_done(self,gs,exp,trace=False):
        cls_str="asmparsers.py - %s.expression_done()" % self.__class__.__name__
        if trace:
            print(cls_str)
        gs.dc_constants.append(exp)


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
#  +-------------------------+
#  |                         |
#  |   DC Lexical Analyzer   |
#  |                         | 
#  +-------------------------+
#

class DCLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()  # Initialize lang.lexer
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        # Create a list of token types to be registered with the lexical analyzer
        tlst=[]

        # Add DC operand types
        tlst.extend([DCA,DCB,DCC,DCF,DCH,DCP,DCX,DCZ])
        # Add DC operand separator
        tlst.append(COMMA)
        # Add expression operators:
        tlst.extend([LPARAN,RPARAN,PLUS,MINUS,MUL,DIV,])
        # Add expression factors:
        tlst.extend([BIN,DEC,HEX,LATTR,LABEL])
        # Add end of line
        tlst.append(EOLCMT)
        # Add utility token types need by LL1Parser
        tlst.extend([EOS,EMPTY])

        for typ in tlst:
            typ.setDebug(tdebug or typ.debug)
            self.type(typ)

        # Display token types if --debug ldebug set in the command line
        if self.dm.isdebug("ldebug"):
            self.types()

        return self


#
#  +-------------------------+
#  |                         |
#  |   DS Lexical Analyzer   |
#  |                         | 
#  +-------------------------+
#

class DSLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()  # Initialize lang.lexer
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        # Create a list of token types to be registered with the lexical analyzer
        tlst=[]

        # Add DS operand type
        tlst.append(DSDESC)
        # Add DS operand separator
        tlst.append(COMMA)
        # Add end of line
        tlst.append(EOLCMT)
        # Add utility token types need by LL1Parser
        tlst.extend([EOS,EMPTY])

        for typ in tlst:
            typ.setDebug(tdebug or typ.debug)
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
#  +------------------------+
#  |                        |
#  |   DC Syntax Analyzer   |
#  |                        | 
#  +------------------------+
#

class DCParser(lang.Processor):
    def __init__(self,dm,asm):
        super().__init__()                       # Initialize lang.Processor
        self.d=dm                                # Debug Manager
        self.asm=asm                             # The assembler itself
        self.pratt=DCExpressionParser(self.asm)  # Interface to Pratt parser
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
        #Register callback methods:
        #    cbreg(pid,point,method)
        lang.cbreg("dc_stmt","beg",self.dc_stmt_begin)
        lang.cbreg("dc_operand","beg",self.dc_operand_begin)
        lang.cbreg("dc_operand","token",self.dc_operand_token)
        lang.cbreg("dc_operand","end",self.dc_operand_end)
        lang.cbreg("expr_list","beg",self.expr_list_begin)
        lang.cbreg("expr_list","end",self.expr_list_end)

        # Set up expression parser's callbacks
        self.pratt.callbacks(lang)

        return self.d  # Return my debug manager

    # Create my lexer - called by the lang.Language.create() method 
    def create_lexer(self):
        return DCLexer(self.d).init()

    # Define the parser's grammar
    def define_parser(self):

# Note: the rather imature parser requires a non-terminal that can produce empty to
# be marked with the '*' repition designator.  It does not excpet '?'.  The 
# presentation of empty terminates the production only when the '*' is present.
# This deserves more research but this works for now.

        g=dc_grammar+self.pratt.get_grammar()
        return (g,"dc_stmt")

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

    def dc_stmt_begin(self,gs,pid):
        # global scope object has some initialization in Assembler.__parse() method
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.dcds_stmt_begin()" % self.__class__.__name__
            print(cls_str)
        gs.parsed=[]
        gs.next_oprndx=0

    def dc_operand_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.dc_operand_begin()" % self.__class__.__name__
            print(cls_str)
        gs.desc=None       # DCDescToken instance
        gs.dca_desc=None   # DC Adcon descriptor DSDESC instance
        gs.dca_exp=None    # DC Adcon Expression instance
        gs.dc_desc_tuple=None  # DC descriptor tuple
        gs.dc_constants=[]     # DC constants list

    def dc_operand_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.dc_operand_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))
        if token.istype("DCA"):
            gs.desc=token  # Save DC adcon descriptor
            return
        if token.istype("RPARAN"):  # Right parenthesis happens in ADCON operands
            gs.dc_desc_tuple=gs.desc.descriptor()
            return

        # All other DC operands are DCOperandToken's
        # Complete the validation by processing its constants
        gs.dc_desc_tuple,gs.dc_constants=token.constants(debug=trace)

    def dc_operand_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.dc_operand_end() -" % self.__class__.__name__
            print("%s failed=%s" % (cls_str,failed))
        if failed or len(eo)!=0:
            return False  # I am not handling the error and doing nothing

        tdup,ttyp,tlength=gs.dc_desc_tuple
        if trace:
            print("%s descriptor: dup=%s typ=%s length=%s" \
                % (cls_str,tdup,ttyp,tlength))
        opr=DCDS(ttyp,dup=tdup,length=tlength,constants=gs.dc_constants)
        if trace:
            print("%s created: %s" % (cls_str,opr))
        opr.unroll(debug=trace)   # Unroll the constants
        if trace:
            print("%s adding to parsed: %s" % (cls_str,opr))
        gs.parsed.append(opr)       # Add the operand to the parser operands

    def expr_list_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.expr_list_begin()" % self.__class__.__name__
            print(cls_str)

        # DC ADCON constants (expressions) added to this list by 
        # DCExpressionParser.expression_done() method
        gs.dc_constants=[]

    def expr_list_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.expr_list_end() -" % self.__class__.__name__
            print("%s failed=%s" % (cls_str,failed))
        if failed or len(eo)!=0:
            return False  # I am not handling the error and doing nothing

        desc=gs.desc       # Descriptor token
        dup,typ,length=desc.descriptor()

        if trace:
            print("%s descriptor: D=%s, T=%s, L=%s" % (cls_str,dup,typ,length))
        opr=DCDS(typ,dup=dup,length=length,constants=gs.dc_constants)
        if trace:
            print("%s created: %s" % (cls_str,opr))
        opr.unroll(debug=trace)     # Unroll the storage definitions
        gs.parsed.append(opr)       # Add the operand to the parser operands


#
#  +------------------------+
#  |                        |
#  |   DS Syntax Analyzer   |
#  |                        | 
#  +------------------------+
#

class DSParser(lang.Processor):
    def __init__(self,dm,asm):
        super().__init__()                       # Initialize lang.Processor
        self.d=dm                                # Debug Manager
        self.asm=asm                             # The assembler itself
        self.pratt=DCExpressionParser(self.asm)  # Interface to Pratt parser
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
        #Register callback methods:
        #    cbreg(pid,point,method)
        lang.cbreg("ds_stmt","beg",self.ds_stmt_begin)
        lang.cbreg("ds_desc","beg",self.ds_desc_begin)
        lang.cbreg("ds_desc","token",self.ds_desc_token)
        lang.cbreg("ds_desc","end",self.ds_desc_end)

        # Set up expression parser's callbacks
        self.pratt.callbacks(lang)

        return self.d  # Return my debug manager

    # Create my lexer - called by the lang.Language.create() method 
    def create_lexer(self):
        return DSLexer(self.d).init()

    # Define the parser's grammar
    def define_parser(self):

# Note: the rather imature parser requires a non-terminal that can produce empty to
# be marked with the '*' repition designator.  It does not excpet '?'.  The 
# presentation of empty terminates the production only when the '*' is present.
# This deserves more research but this works for now.

        g=ds_grammar
        return (g,"ds_stmt")

    #
    # Common methods used by callbacks
    #


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
    def ds_stmt_begin(self,gs,pid):
        # global scope object has some initialization in Assembler.__parse() method
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.dcds_stmt_begin()" % self.__class__.__name__
            print(cls_str)
        gs.parsed=[]
        gs.next_oprndx=0

    def ds_desc_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.ds_desc_begin()" % self.__class__.__name__
            print(cls_str)
        gs.desc=None

    def ds_desc_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.ds_desc_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))

        gs.desc=token  # Save DS descriptor

    def ds_desc_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="asmparsers.py - %s.ds_desc_end() -" % self.__class__.__name__
            print("%s failed=%s" % (cls_str,failed))
        if failed or len(eo)!=0:
            return False  # I am not handling the error and doing nothing

        desc=gs.desc       # Descriptor token
        dup,typ,length=desc.descriptor()

        if trace:
            print("%s descriptor: D=%s, T=%s, L=%s" % (cls_str,dup,typ,length))
        opr=DCDS(typ,dup=dup,length=length)
        if trace:
            print("%s created: %s" % (cls_str,opr))
        opr.unroll(debug=trace)  # Unroll the storage definitions
        gs.parsed.append(opr)       # Add the operand to the parser operands


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

# Operand subclass used for each DS or DC operand of a DS or DC statement.  The
# input is what came in from the source text.  Its role for DS and DC statements
# is the same role as provided by the Parsed object for other assembler directives and
# machine instructions.  The implications of duplication are addressed before this
# object is released by the parser.  
class DCDS(object):
    def __init__(self,typ,dup=None,length=None,constants=[]):
        if not isinstance(constants,list):
            cls_str="asmparsers.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s 'constants' argument must be a list: %s" \
                % (cls_str,constants))

        self.name=typ.upper()
        self.dup=dup         # Duplication factor of this DC or DS operand
        self.length=length   # Length of each individual constant or duplication
        # DC statement only - List of strings or Expression instances of constants 
        self.constants=constants   # For DS this is an empty list
        self.unrolled=[]     # List of Constant instances from unrolling

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "%s(dup=%s,type=%s,length=%s,constants=%s)" \
            % (self.__class__.__name__,self.dup,self.name,self.length, \
                self.constants)

    # This process unrolls the duplications, applies lengths and makes explicit
    # the individual attributes of each physcal constant
    def unroll(self,debug=False):
        cons=len(self.constants)

        if debug:
             cls_str="asmparsers.py - %s.unroll() -" % self.__class__.__name__
             print("%s ..." % cls_str)
             print("%s self.dup=%s cons=%s" % (cls_str,self.dup,cons))

        # Case 0 - DS Statement
        if cons==0:
            if self.dup is None:
                # DS no duplication but a descriptor, just one Constant is needed
                con=Constant(self.name,constant=None,length=self.length)
                if debug:
                    print("%s case 0a adding to unrolled:\n    %s" % (cls_str,con))
                self.unrolled.append(con)
                return
            if self.dup==0 and self.length is None:
                con=Constant(self.name,constant=None,length=0,force=True)
                if debug:
                    print("%s case 0b adding to unrolled:\n    %s" % (cls_str,con))
                self.unrolled.append(con)
                return
            for n in range(self.dup):
                con=Constant(self.name,constant=None,length=self.length)
                if debug:
                    print("%s case 0c adding to unrolled:\n    %s" % (cls_str,con))
                self.unrolled.append(con)
            return

        # Case 1
        if self.dup==0 and self.length is None:
            # Explicit zero dup, no physical constant data 
            # to be allocated, but still need to align with zero length
            con=Constant(self.name,constant=None,length=0,force=True)
            if debug:
                print("%s case 1 adding to unrolled:\n    %s" % (cls_str,con))
            self.unrolled.append(con)
            return

        # Case 2
        if self.dup is None:
            # No duplication, so each coded constant becomes its own physical 
            # constant
            for c in self.constants:
                con=Constant(self.name,constant=c,length=self.length)
                if debug:
                    print("%s case 2 adding to unrolled:\n    %s" % (cls_str,con))
                self.unrolled.append(con)
            return

        # Case 3 - this logic is not consistent with legacy mainframe handling.
        #          although appeared to be the manner in which duplication is
        #          hangled by modern mainframe assemblers.  This could be the
        #          result of incorrect reading of the modern mainframe assembler
        #          manuals.  It is left here as comments in the case it proves 
        #          useful in the future.

        # self.dup is >0 and so is the number of constants.  The duplications
        # factor will drive how many of the constants and which get repeated as
        # physical constants.  There will be exactly the number of physical constants
        # specified by the duplication factor.  As many constants will be repeated
        # or truncated to provided by this number.
        #
        # Example:   5F'1,0' will become F'1',F'0',F'1',F'0',F'1'

        #cndx=0
        #for n in range(self.dup):
        #    con=Constant(self.name,self.constants[cndx],length=self.length)
        #    if debug:
        #        print("%s case 3 adding to unrolled:\n    %s" % (cls_str,con))
        #    self.unrolled.append(con)
        #    cndx+=1
        #    if cndx>=cons:
        #        cndx=0
                
        # Case 3 - this logic is consistent with legacy mainframe duplication
        #          factor handling.

        # self.dup is >0 and so is the number of constants.  The duplication
        # factor will drive how the constants are repeated as physical constands.
        # The duplication is straight forward.  For entire set of constants coded
        # will be duplicated by the duplication factor.  All constants will be
        # duplicated by the duplication factor resulting in defined constants
        # multiplied by the duplication factor being created.
        #
        # Example:   5F'1,0' will become: F'1,0',F'1,0',F'1,0',F'1,0',F'1,0'
        for n in range(self.dup):
            for c in self.constants:
                con=Constant(self.name,constant=c,length=self.length)
                if debug:
                    print("%s case 3 adding to unrolled:\n    %s" % (cls_str,con))
                self.unrolled.append(con)
        return
      

# This class is used as a constant instead of a string for DC constants that
# have signed values.
class Signed(object):
    sign_char={"+":1,"-":-1,None:1}
    def __init__(self,sign,digits):
        self.sign=Signed.sign_char[sign]
        self.digits=digits
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "%s(sign=%s,digits='%s')" \
            % (self.__class__.__name__,self.sign,self.digits)

# This class contains information needed to convert constants into binary data.
# An instance of this class is created for each type.  It is used as the tool
# to convert the input text data into binary data and provide the constant class
# These classes must be defined before the Constant class so that instances
# can be built when the Constant class is defined.
class ConsType(object):

    # Accepts a string of digits and converts them to bytes using the supplied
    # base and number of characters per byte.
    @staticmethod
    def base2bytes(digits,base,cpb):
        b=bytearray(0)
        chars=len(digits)
        for x in range(0,chars,cpb):
            txt=digits[x:x+cpb]
            if len(txt)==0:
                cls_str="asmparsers.py ConsType.base2bytes() -"
                raise ValueError("%s base conversion loop should not end "
                    "prematurely: x:%s, len(s):%s cpb:%s" % (cls_str,x,len(s),cpb))
            i=int(txt,base)
            b.append(i)
        return bytes(b)

    # Given a number of input text characters return the number of bytes consumed
    # where 'cpb' is the number of characters per byte.
    @staticmethod
    def round_up(chars,cpb):
        bytes,extra=divmod(chars,cpb)
        if extra > 0:
            bytes+=1
        return bytes

    def __init__(self,typ,align=1,cpb=None):
        self.typ=typ               # Constant type from DC operand
        self.align=align           # Implied alignment/size in binary bytes
        self.cpb=cpb               # Input characters per binary byte

    def __str__(self):
        return "%s('%s',align=%s,cpb=%s)" % (self.typ,self.align,self.cpb)

    # The method builds the binary data from source input. It returns an immutable
    # byte list.  Ultimately the bytes list will be inserted into the bytearray of
    # an instance of Binary.  An AssemblerError may be raised if
    #   stmt     The Stmt object associated with this
    #   ondx     Operand index of this constant being built
    #   con      This is the instance of Signed, Expression or string that is the
    #            source for the binary data being built.  The subclass should
    #            validate its input argument is as expected.
    #   length   This is the length reguired by the constant descriptor
    #   debug    The current setting of the 'expr' debug option
    #   trace    The current combined setting of the pass and stmt trace settings.
    def build(self,stmt,ondx,con,length,debug=True,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide build() method" % cls_str)

    # Truncate/pad string on left with zero as the pad character
    def tp_left(self,string,chars):
        if len(string)<chars:
            s=string.rjust(chars,'0')    # Pad on the left with ASCII zeros
        else:
            s=string[len(string)-chars:] # Truncate on the left if needed
        return s

# Types: A, AD    
class AdCon(ConsType):
    def __init__(self,typ,align):
        super().__init__(typ,align=align)

    def build(self,stmt,ondx,expr,length,debug=False,trace=False):    
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(expr,expression.Expression):
            raise ValueError("%s 'expr' argument must be a Expression object: %s" \
                % (cls_str,signed))

        try:
            expr.evaluate(debug=debug,trace=trace)
        except LableError as le:
            raise assembler.AssemblerError(line=stmt.lineno,source=stmt.source,\
                msg="%s: %s" % (le.msg,le.label)) from None 
        # I can trust the result to be either an integer or Address
        value=expr.value
        if isinstance(value,assembler.Address):
            if value.isAbsolute():
                value=value.address
            else:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="address constant in operand %s did not evaluate to an "
                        "absolute address: %s" % (ondx+1,value))

        # Convert computed address constant to bytes
        b=value.to_bytes((value.bit_length()//8)+1,byteorder="big",signed=False)

        # Perform left truncation/padding
        pad=b'\x00' * length
        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(b),b))
        return b

    def infer_length(self,constant):
        return self.align

class A_Con(AdCon):
    def __init__(self):
        super().__init__("A",4)

class AD_Con(AdCon):
    def __init__(self):
        super().__init__("AD",8)

# Types: D, F, FD, H
# Note: Type D constants are actually hexadecimal floating point constants.  But
#       legacy code uses D in lieu of AD for 8-byte aligned fields.  ASMA treats
#       type D as fixed point, not hexadecimal floating point.
class FixPt(ConsType):
    def __init__(self,typ,align):
        super().__init__(typ,align=align)

    def build(self,stmt,ondx,signed,length,debug=False,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(signed,Signed):
            raise ValueError("%s 'signed' argument must be a Signed object: %s" \
                % (cls_str,signed))

        # Compute input source text into an integer with the correct sign
        i=int(signed.digits)*signed.sign

        # Convert the converted data into bytes
        b=i.to_bytes((i.bit_length()//8)+1,byteorder="big",signed=True)

        # Perform left truncation/padding
        if i<0:
            pad=b'\xFF' * length
        else:
            pad=b'\x00' * length
        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(b),b))
        return b

    def infer_length(self,constant):
        return self.align

class D_Con(FixPt):
    def __init__(self):
        super().__init__("D",8)

class F_Con(FixPt):
    def __init__(self):
        super().__init__("F",4)

class FD_Con(FixPt):
    def __init__(self):
        super().__init__("FD",8)

class H_Con(FixPt):
    def __init__(self):
        super().__init__("H",2)

# Types: P, Z
class DecCon(ConsType):
    sign={-1:"D",1:"C"}
    def __init__(self,typ,cpb=1):
        super().__init__(typ,cpb=cpb)

class P_Con(DecCon):
    def __init__(self):
        super().__init__("P",cpb=2)

    def build(self,stmt,ondx,signed,length,debug=False,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(signed,Signed):
            raise ValueError("%s 'signed' argument must be a Signed object: %s" \
                % (cls_str,signed))

        # Convert to packed digits plus sign
        hexdigits="%s%s" % (signed.digits,DecCon.sign[signed.sign])

        # Do left truncation/padding
        chars=length*self.cpb
        hexdigits=self.tp_left(hexdigits,chars)

        # Convert the hex data into bytes
        b=ConsType.base2bytes(hexdigits,16,2)
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(b),b))
        return b

    def infer_length(self,constant):
        # The assumption is that the constant is a string
        chars=len(constant.digits)+1 
        return ConsType.round_up(chars,self.cpb)

class Z_Con(DecCon):
    def __init__(self):
        super().__init__("Z",cpb=1)

    def build(self,stmt,ondx,signed,length,debug=False,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(signed,Signed):
            raise ValueError("%s 'signed' argument must be a Signed object: %s" \
                % (cls_str,signed))

        digits=self.tp_left(signed.digits,length)

        hi=digits[:-1]
        lo=digits[-1]
        lohex="%s%s" % (DecCon.sign[signed.sign],lo)

        zoned=""
        for digit in hi:
            # unpack each non-signed digit
            zoned="%sF%s" % (zoned,digit)
        zonehex="%s%s" % (zoned,lohex)

        # Convert the hex data into bytes
        b=ConsType.base2bytes(zonehex,16,2)
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(b),b))
        return b

    def infer_length(self,constant):
        # constant is assumed to be an instance of Signed
        return len(constant.digits)

# Types: C, CA, CE
class CharCon(ConsType):
    def __init__(self,typ):
        super().__init__(typ,cpb=1)

    def build(self,stmt,ondx,string,length,debug=False,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(string,str):
            raise ValueError("%s 'string' argument must be a string: %s" \
                % (cls_str,string))

        # Note input string is ASCII data natively
        if len(string)<length:
            s=string.ljust(length)   # Pad on the right with ASCII blanks
        else:
            s=string[:length]  # Truncate on the right if needed
        s=self.translate(s)    # Let the subclass handle the character set
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(s),s))
        return s               # Return the string from the regular string

    def infer_length(self,constant):
        # constant is assumed to be a string
        return len(constant)

class CA_Con(CharCon):
    def __init__(self):
        super().__init__("CA")
    def translate(self,string):
        return string

class ECharCon(CharCon):
    def __init__(self,typ):
        super().__init__(typ)
    def translate(self,string):
        return assembler.CPTRANS.a2e(string)

class C_Con(ECharCon):
    def __init__(self):
        super().__init__("C")

class CE_Con(ECharCon):
    def __init__(self):
        super().__init__("CE")

# Types: B, X
class BaseCon(ConsType):
    def __init__(self,typ,base,cpb):
        super().__init__(typ,cpb=cpb)
        self.base=base

    def build(self,stmt,ondx,string,length,debug=False,trace=False):
        cls_str="asmparsers.py - %s.build() -" % self.__class__.__name__
        if not isinstance(string,str):
            raise ValueError("%s 'string' argument must be a string: %s" \
                % (cls_str,string))

        cpb=self.cpb      # Get the number of characters per byte
        chars=cpb*length
        s=self.tp_left(string,chars)

        b=bytearray(0)
        for x in range(0,chars,cpb):
            txt=s[x:x+cpb]
            if len(txt)==0:
                raise ValueError("%s base conversion loop should not end "
                    "prematurely: x:%s, len(s):%s cpb:%s" % (cls_str,x,len(s),cpb))
            i=int(txt,self.base)
            b.append(i)
        b=bytes(b)
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(b),b))
        return b

    def infer_length(self,constant):
        # The assumption is that constant is a string
        return ConsType.round_up(len(constant),self.cpb)

class B_Con(BaseCon):
    def __init__(self):
        super().__init__("B",2,8)

class X_Con(BaseCon):
    def __init__(self):
        super().__init__("X",16,2)


# The unroll process creates instances of Constant.  This class is an intermediary
# between the constant as coded in the source and the binary object that contains
# its object code.  Instances of this class form the basis for binary objects.
# Each instance corresponds to a physical constant placed in the binary imate.
# It is used by both DC and DS statements.  DS statements will not have a 
class Constant(object):
    Types={"A": A_Con(),
           "AD":AD_Con(),
           "B": B_Con(),
           "C": C_Con(),
           "CA":CA_Con(),
           "CE":CE_Con(),
           "D": D_Con(),
           "F": F_Con(),
           "FD":FD_Con(),
           "H": H_Con(),
           "P": P_Con(),
           "X": X_Con(),
           "Z": Z_Con()}
    def __init__(self,typ,constant=None,length=None,force=False):
        self.typ=typ             # Constant type from DC operand
        self.constant=constant   # May be Signed, Expression or string instance
        self.contyp=None         # Set from Types dictionary above

        # Binary object associated with this constant.  Established by 
        # Assembler Pass 1 method __dcds_pass1().  The assingment of this object
        # to a Section object means that any changes to it here, for example, when
        # its bytearray attribute is updated, will automatically be seen by the 
        # Section object.
        self.content=None

        try:
            self.contyp=Constant.Types[typ]
        except KeyError:
            cls_str="asmparsers.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s unrecognized constant type: '%s'" % (cls_str,typ))

        # These attributes are set below after much analysis
        self.align=None
        self.length=None

        # This attribute is set by Assembler._dcds_pass1() method
        self.content=None               # This will the constant's Binary instance

        if length is None or force:
            self.align=self.contyp.align
        else:
            self.align=1

        if length is not None:          # Explicit length in descriptor
            self.length=length          # ..so use it for the length
            return                      # and we are now done

        # Without a real constant, the length is driven by the alignment
        if constant is None:            # Constant being None means a DS statememt
            self.length=self.align      # For DS use alignment for length
            return                      # and we are done

        # Need to infer the length from the constant
        self.length=self.contyp.infer_length(constant)

    def __str__(self):
        content="None"
        if self.content is not None:
            content="%s" % self.content.loc
        return "Constant('%s',align=%s,length=%s,constant=%s,content=%s)" \
            % (self.typ,self.align,self.length,self.constant,content)

    # Updates the Binary object associated with me with its binary image content
    # and finalize it.
    def build(self,stmt,ondx,debug=False,trace=False):
        data=self.contyp.build(stmt,ondx,self.constant,self.length,\
            debug=debug,trace=trace)
        self.content.update(data,full=True,finalize=True,trace=trace)

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
        gs.Operands(value)
        state.atend()

    def ACT_Operation(self,value,state,trace=False):
        gs=self.scope()
        gs.Operation(value)
        return "opnd_spaces"


if __name__ == "__main__":
    raise NotImplementedError("asmparsers.py - intended for import use only")
