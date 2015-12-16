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

# This module parses macro statement operands.

this_module="%s.py" % __name__

# SATK imports
import fsmparser
import lexer
# ASMA imports:
import assembler
import asmbase
import asmtokens
import asmline
import macsyms


# This module parses macro statements with recursion for symbolic variable references
# and function calls.  Function calls and symbolic references are extensions of the
# process that recognizes symbolic variables and labels respectively.  Both are
# examples of the type of parsing used by the asmopnd.OperandParser, but are now
# contexts that require recursion.
#
# Corresponding recursion will be required for evaluation of the expressions parsed
# by this module.
#
# ASMA utilizes a common approach to statement processing.  Multiple steps are taken
# to get from input characters to a processed statement.  The assembler is at its
# heart an expression evaluator.  The meaning and processing details are statement
# specific.
#
# The asmline module performs initial processing of the label and operation fields
# of the statement.  The recognized statement's implementation drives the processing
# of the operand field:
#
#   asmopnd - machine instruction and most assembler directives
#   asmdcds - DC/DS operands
#   macopnd - macro statement operands - this module
#
# Some assembler directive operands are parsed directly by the statement
# implementation.  Those are typically simple in nature and do not involve actual
# use of expressions.  These cases lend themselves well to use of standard Python
# string processing techniques.
#
# In the above mentioned three modules, the processing results in creation of
# the recognized operand as an object instance:
#
#  asmopnd - asmbase.ASMOperand
#  asmdcds - asmdcds.DCDS_Operand and subclasses of asmdcds.Nominal
#  macopnd - macopnd subclasses derived from asmbase.ASMOperand.
#
# Parsing results utilize a concept of a "comples term".
# A complex term takes the form:
#
#   primary-expression(secondary_expression1,secondary_expression2,....)
#
# Secondary expressions are optional and may vary from one to many.  When multiple
# secondary expressions are present they are each separated by a comma.  Empty
# secondary expressions are allowed.  When present a secondary expression is always
# an arithmetic expression.
#
# Parsing and processing of complex terms utilizes three steps:
#   1 - Perform lexical recognition using a context sensitive lexer and parser.
#       Results from this process is a parser scope object usually specific to
#       the complex term. The output of step 1 is a "result object", a subclass 
#       of asmbase.CTerm.
#   2 - The CTerm object emulates a lexical token but with an understanding of
#       the underlying complex term's expressions.  The "expressions" are instances
#       of asmbase.ASMExpr, really a subclass: 
#          - ASMExprArith for an arithmetic expression
#          - ASMExprBinary for a logical expresion or
#          - ASMExprChar for a character expression.
#       These objects utilize Pratt tokens created during the expression preparation
#       process from the source lexical tokens.  For a CTerm object emulating a
#       lexical token it will create an instance of asmtokens.PLitCTerm during the
#       preparation process.  
#   3 - Expressions within complex terms are evaluated.  When an instance of
#       PLitCTerm is encountered, the evaluation of its internal expressions occurs
#       to provide its evaluated result.  Because expressions within a PLitCTerm
#       object may include PLitCTerm objects, the evaluation is recursive.
#
# Steps one and two occur together.  Step 1 is performed by this module.  Step 2
# is typically handled by the asmstmts.Stmt subclass associated with type of
# statement being assembled during Pass0 processing.  Step 3 occurs either during
# Pass1 processing or Pass2 for assembler directives and machine instructions
# depending upon the type of instruction.  For macro statements, step 3 occurs
# during Pass0 processing of the invoked macro.
#
# Complex terms start with either a symbol or label with or without an attribute
# character.  Symbols may include one or more arithmetic expressions, identifying
# one or more subscripts.  A label (or what is really lexically equivalent to a
# label) initiates a function with a set of parameters.  The difference between
# the primary/secondary expression construct used in asmopnd.py for instruction
# operands, is that the primary may only be a single symbol or label in each case.
# For complex terms the initial primary utomatically is completed with the single
# lexical token.  The following symbol determines whether secondary expressions are
# present, namely a left parenthesis.  If it is not present, the complex term scope
# is complete and it can be "popped".  The following lexical symbol then needs to
# be stacked to allow the returned to state to process it.  Complex terms always
# set the next state as 'term'.  This module only supports symbolic references.
# Functions are a future goal.  The framework used to support symbolc variable, in
# particular multiple levels of parameter sublists and &SYSLIST, will be the
# basis for macro function support.
#
# A complex term takes the form:
#
#   primary-expression(secondary_expression1,secondary_expression2,....)
#
# The parenthesis enclosed secondary expressions are optional.
#
# Parsing context determines which scope object, result object and Pratt literal
# object is utilized.  The following table summarizes these relationships
#
#    Parser                Scope Object        Result Object       Pratt Literal
#    Context               (MacroScope)           (CTerm)           (PLitCTerm)
#
# AGO Statement              AGOScope           CondBranch            not used
# AIF Statement              AIFScope           CondBranch            not used
# Character Expression     CharacterExpr          ChrExpr             PChrExpr
# SETC Statement             SETCScope            ChrExpr             PChrExpr
# Symbol Declaration     SymbolicReference       SymbolRef            PSymRef
# Symbol Reference       SymbolicReference       SymbolRef            PSymRef
# Symbolic Replacement     CharacterExpr          ChrExpr             PChrExpr
#
#                        Recursive Parsing
#                        --------- -------
#
# The macro language demands recursive parsing.   The parser, MacroParser, utilizes
# the basic capabilities of the context sensitive lexer, lexer.CSLA, and context
# sensitive parser, fsmparser.FSMContext, with additional support to perform
# recursive parsing in a manner similar to a recursize decent parser.  The handling
# of parentheses and operator precedence by the Pratt evaluators simplifies the
# parsing process.
#
# Within a given context, recognition of the need to perform recursion is necessary.
# However, it is the recursed context that knows what lexical context and finite-
# state machine state is required.  It knows the scope object is needs as well.
# The recognition of the need to recurse is of course triggered by a lexical token.
# The recursed context is best positioned to handle this token, being the first
# lexical token of the context's primary expression.  Each recursed context supplies
# a XXXX_Call() method to which is passed the initial token and which modifies the
# parser state to continue processing.  The "calling" context simply needs to return
# to the finite-state machine the state returned by this call.  Correspondingly
# it is the "calling" context that knows the state it needs upon return, so it needs
# to supply that to the "called" context to effect return.  The MPControl object
# incorporates the return state for the finite-state machine.
#
# This call is used within the "calling" context's action method to initiate the
# recursion:
#
#     return Called_Context_Call(token,ret=MPControl())
#
# Returning to the "calling" context has similar considerations.  The "called"
# context must recognize when it is at its end.  In some cases it simply needs to
# return, after consuming its ending lexical token.  In other cases, the ending
# lexical token may belong to the "calling" context.  In this case it needs to be
# returned for processing by the previous "calling" context.
#
# A return by a "called" context is effected by this method call in its ending
# finite-state machine action method, with an optional token argument.
#
#     return Call_Return([token=tok])
#
# This method has the effect of extracting the "returning" context's result object
# and adding it to the previously "calling" context's current expression (primary
# or secondary.  The returned token is actually rejected, causing recognition
# to occur under the lexical context of context to which control is returned.
# 
# These "calling" and "returning" processes utilize the enter_scope() and
# return_scope() methods of the MacroProcessor object to emulate the recursive call/
# return processing of contexts.
#
# Because arithmetic and logical expression parsing depends upon the current scope, 
# the underlying mechanisms are slightly different.  They do not require a new scope.
# But they do result in a change in context.  The two forms of expressions,
# arithmetic and logical, are entered by use of the Arith_Call() and Binary_Call()
# methods, respectively.  These methods handle the difference between processing
# an expression and processing a new complex term with its own scope.  But from a
# coding perspective they are logically the same.  The actions within expression
# recognition use the commond Expr_Return() method to complete the expression.


AMP=asmtokens.AmpType()
AOPER=asmtokens.AOperType()
CHRS=asmtokens.ChrsType()
CHRSREP=asmtokens.ChrsRepType()
COMMA=asmtokens.CommaType()
COMPARE=asmtokens.CompType()
DBLQUOTE=asmtokens.DblQuoteType()
EOS=lexer.EOSType()
LAREF=asmtokens.LabelAttrRefType()
LATTR=asmtokens.LabelAttrType()
LOGICAL=asmtokens.LogicalType()
LOGNOT=asmtokens.LogNotType()
LPAREN=asmtokens.LParenType()
NOT=asmtokens.NotType()
QUOTE=asmtokens.QuoteType()
PCTerm=asmtokens.PLitCTerm       # Base class for Pratt complex terms
PERIOD=asmtokens.PeriodType()
RPAREN=asmtokens.RParenType()
SAREF=asmtokens.SymAttrRefType() # Used in SETC statements for attribute references
SATTR=asmtokens.SymAttrType()    # Used in macro statements expressions
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()
SEQSYM=asmtokens.SeqType()
STRING=asmtokens.StringType()    # Used during open code quoted string recognition
SYM=asmtokens.SymType()          # Used during symbolic replacement in strings
SYMBOL=asmtokens.SymbolType()    # Used during symbolic replacement in strings


#
#  +-----------------------------------------------------+
#  |                                                     |
#  |   Shared Macro Statement Operand Lexical Analyzer   |
#  |                                                     |
#  +-----------------------------------------------------+
#

class MacroLexer(lexer.Lexer):
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
        lst.append(LOGNOT)      # " AND NOT ", " OR NOT ", " XOR NOT "
        lst.append(LOGICAL)     # " AND ", " OR ", " XOR "
        lst.append(COMPARE)     # " EQ ", " NE ", " LT ", " LE ", " GT ", " GE "
        lst.append(AOPER)       # "+", "-", "*", "/"
        lst.append(NOT)         # "NOT ", " NOT "
        lst.append(SDBIN)       # "B'01.."
        lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        lst.append(SDHEX)       # "X'0..F..'"
        lst.append(SDDEC)       # "0..9.."
        lst.append(AMP)         # "&&"
        #lst.append(NATTR)       # N'&label   # Number attribute reference
        #lst.append(SYMREF)      #   "&label",   "&label(0..9..)",    "&label(&sub)"
        #                        # "K'&label", "K'&label(0..9..)",  "K'&label(&sub)"
        lst.append(SEQSYM)      # ".label"
        lst.append(SATTR)       # "&symbol" or "X'&symbol"
        lst.append(LATTR)       # "label" or "X'label"
        # Need a new STRING token type for this style of parsing
        #lst.append(STRING)      # "'x..'"  Includes the empty string
        lst.append(DBLQUOTE)    # "''"
        lst.append(QUOTE)       # "'"
        #lst.append(EOO)         # " "      One or more spaces
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


class MacroCSLexer(lexer.CSLA):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")
        ldebug=self.dm.isdebug("ldebug")
        
        # Initialize lexical contexts                      Name
        self.init_cexpr(ldebug=ldebug,tdebug=tdebug)     # 'cexpr'
        self.init_default(ldebug=ldebug,tdebug=tdebug)   # 'init'
        self.init_quote(ldebug=ldebug,tdebug=tdebug)     # 'quote'
        self.init_rep(ldebug=ldebug,tdebug=tdebug)       # 'rep'
        self.init_seq(ldebug=ldebug,tdebug=tdebug)       # 'seq'
        self.init_setc(ldebug=ldebug,tdebug=tdebug)      # 'setc'
        self.init_string(ldebug=ldebug,tdebug=tdebug)    # 'string'
        self.init_sym(ldebug=ldebug,tdebug=tdebug)       # 'sym'

        # Print the tokens when the debug manager is set for ldebug
        # Token debugging is determined by 
        #if self.dm.isdebug("ldebug"):
        #    self.types(debug=True)

        return self

    def init_cexpr(self,ldebug=False,tdebug=False):
        c="cexpr"
        self.ctx(c,debug=ldebug)
        types=[DBLQUOTE,QUOTE,AMP,SYMBOL,SYM,CHRS,LPAREN]
        self.type(c,types,debug=tdebug)

    def init_default(self,ldebug=False,tdebug=False):
        c="init"
        self.ctx(c,debug=ldebug)
        types=[LPAREN,RPAREN,COMMA,LOGNOT,LOGICAL,COMPARE,AOPER,NOT,SDBIN,SDCHR,\
               SDHEX,SDDEC,SEQSYM,SATTR,LATTR,QUOTE]
        self.type(c,types,debug=tdebug)

    def init_quote(self,ldebug=False,tdebug=False):
        c="quote"
        self.ctx(c,debug=ldebug)
        types=[STRING,]
        self.type(c,types,debug=tdebug)

    def init_rep(self,ldebug=False,tdebug=False):
        c="rep"
        self.ctx(c,debug=ldebug)
        types=[AMP,SYMBOL,SYM,CHRSREP,LPAREN]
        self.type(c,types,debug=tdebug)

    def init_seq(self,ldebug=False,tdebug=False):
        c="seq"
        self.ctx(c,debug=ldebug)
        types=[SEQSYM,]
        self.type(c,types,debug=tdebug)

    def init_setc(self,ldebug=False,tdebug=False):
        c="setc"
        self.ctx(c,debug=ldebug)
        types=[SAREF,LAREF,QUOTE]
        self.type(c,types,debug=tdebug)

    def init_string(self,ldebug=False,tdebug=False):
        c="string"
        self.ctx(c,debug=ldebug)
        types=[AMP,DBLQUOTE,QUOTE,SATTR,CHRS]
        self.type(c,types,debug=tdebug)

    def init_sym(self,ldebug=False,tdebug=False):
        c="sym"
        self.ctx(c,debug=ldebug)
        types=[SYM,LPAREN]
        self.type(c,types,debug=tdebug)


#
#  +--------------------------+
#  |                          |
#  |    BASE MACRO CLASSES    |
#  |                          |
#  +--------------------------+
#


# This object is the basic interface object between the statement processor and
# the parser.  Different statements and complex terms may use their own subclass
# of this object.  The result method determines what is produced by the parser
# for the operand parsed.  
#
# This foundation class itself processes macro arithmetic expressions.  This role
# is moving to class MacroScopeExprA.

# Instance Methods:
#   balanced_parens  Checks for balanced parenthesis.
#   expression_end   Completes the pending primary or secondary expression.
#   init             Initializes the MacroScope subclass by creating its result 
#                    object
#   result           Returns the scope's completed result object
#   init_result    * Creates the subclass' result object.
#   primary       ** Updates the result object with the primary expression
#   secondary     ** Updates the result object with its secondary expressions
# * init_result() method used internally by init() method
# ** primary() and secondary() methods are used internally by expression_end()

# Instance Methods Inherited from asmbase.AsmFSMScope:
#   ck_parens   Validates balanced parenthesis are present
#   flush       Discard all pending lexical tokens
#   init        Initializes the scope for use.
#   expr        Returns the lexical token list of the expression
#   expr_end    Returns the lexical token list after token update has occurred.
#   lparen      Add a left parenthesis lexical token to the pending list and track it
#   pending     Returns the number of lexical tokens pending for release
#   rparen      Add a right parenthesis lexical token to the pending list and track it
#   str_beg     Start a string represented by the asmtokens.StringToken() objects.
#   str_cont    Add more characters to the pending asmtokens.StringToken() object
#   str_end     Return the asmtokens.StringToken of the entire string.
#   str_pending Return whether a string is pending (True) or not (False).
#   token       Add a token to the pending expression
#   update_loc  Update a lexical token with is physical source (ASMPLoc object)
#
# Instance Arguments:
#   lopnd       The asmline.LOperand or asmline.LField object assocated with the
#               portion of the statement being parsed.
#   suffix      Operator precedence expressions share actions.  For a given type
#               of expression, the supplied suffix is appended by the action when
#               returning the finite-state machine state.  Defaults to ''.
#               Presently the following suffixes are used:
#                  d - macro arithmentic expression
#                  e - macro binary (logical) expression
class MacroScope(asmbase.AsmFSMScope):
    def __init__(self,lopnd,suffix=""):
        super().__init__()
        assert isinstance(lopnd,(asmline.LOperand,asmline.LField)),\
            "%s 'lopnd' argument must be an asmline.LOperand object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),lopnd)

        self.lopnd=lopnd       # LOperand source object
        self.opnd=None         # ASMOperand result object. See init_result() method

        # This attribute allows a context under a scope to determine what should
        # be the next FSM state when control is returned to this scope during a
        # leave_scope operation.  The state that initiates the enter_scope() is the
        # one best able to know what FSM should be entered upon return.
        #
        # The leave_scope() method will reset these attributes to None each time 
        # a return occurs.  See the MacroParser.enter_scope() and
        # MacroParser.leave_scope() methods.
        self.next_state=None   # Next FSM state upon pop'ing this scope.
        self.next_pctx=None    # The parser context to be established
        self.follow=[]         # Valid tokens that follow the expression

        # Whether the primary expression is being parsed (True) or a secondary
        # expression is being parsed (False).
        self._primary=True  # Initially the primary expression is being parsed

        # Subclass can modify these after it calls this initializer
        self.cterm=False    # Assume this is not a complex term scope
        self.suffix=suffix  # Expression state suffix used by expression actions

    # Checks the surrent state of parenthesis balancing
    # Returns:
    #   True   if the expression parenthesis are balanced
    #   False  if the expression parenthesis are not balanced
    def balanced_parens(self):
        return self._parens==0

    # This method completes the current expression being accumulated by the scope
    # or returned by a called scope.  It automatically moves from the primary
    # expression to the secondary expressions when the primary expression is
    # completed.
    #
    # Method Argument:
    #   result    Result opbject supplied by a called scope.  Default is None.
    #             When result is None, the subclass primary() and secondary()
    #             methods must locate or create the result object.
    #
    # Returns:
    #   True  If scope is done after primary expression (cterm=False)
    #   False If scope is not done after primary expression (cterm=True)
    def expression_end(self,result=None):
        if self._primary:
            #print("scope %r expression_end completed primary" % self)
            self.primary(result=result)
            self._primary=False
        else:
            #print("scope %r expression_end completed, secondary" % self)
            self.secondary(result=result)

    # Initializes the scope for use and instantiates the result object
    # Override this method to create a different result object
    def init(self,stmt=None,case=False):
        self.opnd=self.init_result()
        super().init(stmt=stmt,case=case)
        return self


  #
  # Methods that may be overridden by a subclass
  # 


    # Returns the result object creaed by init_result() method
    def result(self):
        return self.opnd

    # Processes returned result object from a called scope.  By default the 
    # result object is treated as a new token.  Scopes that support expression
    # results must override this method to support primary/secondary expression
    # handling.
    def result_returned(self,res):
        self.token(res)


  #
  # Methods that must be supplied by the subclass
  # 

    # Returns the result object used by this scope.
    # Override this method to create a result object other than asmbase.Operand
    def init_result(self):
        raise NotImplementedError("%s subclass %s must provide init_result() method" \
            % (assembler.eloc(self,"init_result",module=this_module),\
                self.__class__.__name__))
        
        # Legacy default behavior.  Preserved for reference
        # return asmbase.ASMOperand()


    # This method processes a recognized operand's primary expression.  Subclass
    # must provide this method.  Subclass detected errors should raise
    # assembler.AsmParserError that contains the offending lexical token.
    #
    # Method Argument:
    #   result   Result opbject supplied by a called scope.  Default is None.
    def primary(self,result=None):
        raise NotImplementedError("%s subclass %s must provide primary() method" \
            % (assembler.eloc(self,"primary",module=this_module),\
                self.__class__.__name__))

        # Legacy default behavior.  Preserved for reference
        # expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        # self.opnd.primary(asmbase.ASMExprArith(expr))

    # This method processes a recognized operand's secondary expression.  Subclass
    # must provide this method.  Subclass detected errors should raise
    # assembler.AsmParserError that contains the offending lexical token.
    #
    # Method Argument:
    #   result   Result opbject supplied by a called scope.  Default is None.
    def secondary(self,result=None):
        raise NotImplementedError("%s subclass %s must provide secondary() method" \
            % (assembler.eloc(self,"secondary",module=this_module),\
                self.__class__.__name__))

        # Legacy default secondary behavior.  Preserved for reference.
        # expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        # self.opnd.secondary(asmbase.ASMExprArith(expr))


# This scope is used for a macro statement operand that is an arithmetic expression.
# Used by ACTR and SETA macro directives.
class ArithScope(MacroScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)

    def init_result(self):
        return asmbase.ASMOperand()

    def primary(self,result=None):
        assert isinstance(result,asmbase.ASMExprArith),\
            "%s result not a ASMExprArith object: %s" \
                % (assembler.eloc(self,"primary",module=this_module),result)
        self.opnd.primary(result)

    def result_returned(self,result):
        assert isinstance(result,asmbase.ASMExprArith),\
            "%s result not a ASMExprArith object: %s" \
                % (assembler.eloc(self,"result_returned",module=this_module),result)
        self.expression_end(result=result)


class BinaryScope(MacroScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)

    def init_result(self):
        return asmbase.ASMOperand()

    def primary(self,result=None):
        assert isinstance(result,asmbase.ASMExprBinary),\
            "%s result not a ASMExprArith object: %s" \
                % (assembler.eloc(self,"primary",module=this_module),result)
        #print("%s result: %s" \
        #    % (assembler.eloc(self,"primary",module=this_module),result))
        self.opnd.primary(result)

    def result_returned(self,result):
        assert isinstance(result,asmbase.ASMExprBinary),\
            "%s result not a ASMExprArith object: %s" \
                % (assembler.eloc(self,"result_returned",module=this_module),result)
        self.expression_end(result=result)
    

class CTermScope(MacroScope):
    def __init__(self,lopnd,suffix="",seqsym=False):
        super().__init__(lopnd,suffix=suffix)
        self.cterm=True        # Identify this as a complex term
        self.first_tok=None    # Remember first lexical token for PCTerm object

    def token(self,tok):
        if len(self._lextoks)==0:
            self.first_tok=tok
        super().token(tok)


#
#  +------------------------------------+
#  |                                    |
#  |    EVALUATED EXPRESSION CLASSES    |
#  |                                    |
#  +------------------------------------+
#


# Scope for recognition and creation of operator precedence based expressions.
# Result Object, a subclass of ASMExpr that is not a complex term
#
# Method Arguments:
#   lopnd    Logical operand (LOperand object) being parsed.
#   suffix   For shared action methods, the character suffix of FSM states
#            This is used for all operator precedent expressions evaluated by 
#            a Pratt expression evaluator.
#   exprcls  The subclass of ASMExpr being created by the scope
class MacroScopeExpr(MacroScope):
    def __init__(self,lopnd,suffix,exprcls):
        super().__init__(lopnd,suffix=suffix)
        self.exprcls=exprcls

    # Create the result object accumulated with the help of MacroScope superclass.
    def build_expression(self):
        assert self.opnd is None,"%s self.opnd is not None: %s" \
            % (assembler.eloc(self,"expression_end",module=this_module),self.opnd)
        expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        self.opnd=self.exprcls(expr)

    # The handling of primary or secondary expressions performed by the
    # MacroScope object is not supported for operator precedence expressions.
    def expression_end(self,result=None):
        raise NotImplementedError("%s does support primary or secondry expressions" \
            % assembler.eloc(self,"expression_end",module=this_module))

    # Has the effect of setting self.opnd to None
    # The result object is not created until the expression_end() method is called
    def init_result(self):
        return None

    # Tests if a lexical token is in the follow list
    def isFollow(self,token,trace=False):
        if __debug__:
            cls_str=assembler.eloc(self,"isFollow",module=this_module)
            if trace:
                print("%s follow: %s" % (cls_str,self.follow))

        for follow in self.follow:
            if follow.tid == token.tid:
                if __debug__:
                    if trace:
                        print("%s folow tid %s -> True" % (cls_str,token.tid))
                return True

        if __debug__:
            if trace:
                print("%s folow tid %s -> False" % (cls_str,token.tid))
        return False

    # Expression scopes do not have the concept of primary or secondary expressions.
    # This class builds the expression itself used by other scopes
    def primary(self,result=None):
        raise NotImplementedError("%s primary expressions not supported" \
            % assembler.eloc(self,"secondary",module=this_module))

    # Return the scope's result object: an ASMExpr
    def result(self):
        assert self.opnd is not None,\
            "%s build_expression method not called, self.opnd is still None" \
                % assembler.eloc(self,"results")
        return self.opnd

    # Expression scopes do not have the concept of primary or secondary expressions.
    # This class builds the expression itself used by other scopes
    def secondary(self,result=None):
        raise NotImplementedError("%s secondary expressions not supported" \
            % assembler.eloc(self,"secondary",module=this_module))


# Macro Arithmetic Expression Scope
# Result Object: asmbase.ASMExprArith
# Used by AGO and SETA macro directives and various secondary expressions in macro
# related complex terms.
class MacroScopeExprA(MacroScopeExpr):
    def __init__(self,lopnd):
        super().__init__(lopnd,"d",asmbase.ASMExprArith)


# Macro Binary Expression Scope
# Result Object: asmbase.ASMExprBinary
# Used by AIF and SETB macro directives.
class MacroScopeExprB(MacroScopeExpr):
    def __init__(self,lopnd):
        super().__init__(lopnd,"e",asmbase.ASMExprBinary)


# Macro Character String Expression Scope
# Result Object: asmbase.ASMExprChar
class MacroScopeExprC(MacroScopeExpr):
    def __init__(self,lopnd):
        super().__init__(lopnd,None,asmbase.ASMExprChar)


#
#  +------------------------------------+
#  |                                    |
#  |    CHARACTER EXPRESSION CLASSES    |
#  |                                    |
#  +------------------------------------+
#


# The Pratt token of a character expression.
# Instance Arguments:
#   chr_lst   List of strings and replacement symbolic references
#   start     An optional arithmetic expression specifying the substring start.
#             Default is None.
#   length    An optional arithemtic expression of the substring length.  Default
#             is None.
#   string    Whehter a Python string should be returned (True) or a macsyms.C_Val
#             object (False).  A C_Val object is the default.
class PChrExpr(PCTerm):
    def __init__(self,expr,start=None,length=None,string=False):
        assert isinstance(expr,asmbase.ASMExprChar),\
            "%s 'expr' argument must be an asmbase.ASMExprChar object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),expr)
        assert (start is None and length is None) \
          or (start is not None and length is not None),\
            "%s 'start' and 'length' aguments must both be present or absent: "\
                " start %s, length %s" \
                    % (assembler.eloc(self,"__init__",module=this_module),\
                        start,length)
        super().__init__(None)

        # All of these are subclasses of ASMExpr
        self.expr=expr           # ASMExprChar object
        self.start=start         # Starting substring position relative to 1
        self.length=length       # Substring length

        # How to return the result.
        self.string=string       # Whether to return C_Val or Python string

    # Used to convert result of arithmetic expressions into Python integers.
    def to_integer(self,value):
        if isinstance(value,macsyms.A_Val):
            return value.value()
        return value

    # Performs symbolic replacement and substring extraction
    # Returns:
    #   C_Val object of the final string or Python string depending upon self.string
    def value(self,external=None,debug=False,trace=False):
        result=""
        if __debug__:
            if debug:
                print("%s chr exp list: %s" \
                    % (assembler.eloc(self,"value",module=this_module),self.chr_lst))
        
        result=self.expr.evaluate(external,debug=debug,trace=trace)
        if __debug__:
            if debug:
                print("%s chars: '%s'" \
                    % (assembler.eloc(self,"value",module=this_module),result))
                print("%s string: %s" \
                    % (assembler.eloc(self,"value",module=this_module),self.string))

        # Extract substring if present
        if self.start:
            start=self.start.evaluate(external,debug=debug,trace=trace)
            length=self.length.evaluate(external,debug=debug,trace=trace)

            # Expression evaluated, so turn them into Python integers
            start=to_integer(start)
            length=to_integer(length)

            # Validate the starting sub-string position 
            strlen=len(result)
            if start<1 or start>strlen:
                raise MacroError(invoke=True,\
                    msg="substring starting position out of range (1-%s): %s" \
                        % (strlen,start))

            # Validate the sub-string length
            if length>0:
                end=start+length-1
                if end<1 or end>strlen:
                    raise MacroError(invoke=True,\
                        msg="substring ending position out of range (1-%s): %s" \
                            % (strlen,end))
                start-=1
                result=result[start:end]
            elif length==0:
                result=""
            else:
                raise MacroError(invoke=True,\
                    msg="substring length may not be negative: %s" % length)

        # Return the replacement string in the form requested
        # (Python string vs. macsyms.C_Val object)
        if self.string:
            return result
        return macsyms.C_Val(result)


# Character Expression result object
class ChrExpr(asmbase.CTerm):
    def __init__(self,string=False):
        super().__init__()
        # self._primary is a ASMExprChar object
        # self._secondary will be a list of 0 or 2 arithmetic expressions
        
        # Whether to return a string (True) or C_Val object (False)
        self.string=string
        
        self.chr_exp=None   # A list of pratt tokens destined for the PChrExpr object

        # If present, both will be available.  Derived from self._secondary in
        # prepare() method
        self.start_expr=None       # Character substring starting position
        self.len_expr=None         # Substring length from starting position

        self.prepared=False

    # Prepare the ASMExpr objects in self._secondary for execution - this converts
    # each lexical token or complex term object into 
    def prepare(self,stmt,desc):
        assert len(self._secondary) in [0,2],\
            "%s [%s] seconary expression may be 0 or 2, found: %s" \
                % (assembler.eloc(self,"prepare",module=this_module),stmt.lineno,\
                    len(self._secondary))

        self._primary.prepare(stmt,desc)
        self.prepared=True

        if len(self._secondary)==0:
            return

        d="%s expr 0" % desc
        self.start_expr=self._secondary[0]
        self.start_expr.prepare(stmt,d)

        d="%s expr 1" % desc
        self.len_expr=self._secondary[1]
        self.len_expr.prepare(stmt,d)

    def primary(self,expr,result=None):
        assert isinstance(expr,asmbase.ASMExprChar),\
            "%s 'expr' argument must be an ASMExprChar object: %s" \
                % (assembler.eloc(self,"primary",module=this_module),expr)
        self._primary=expr

    def ptoken(self):
        assert self.prepared,"%s not prepared" \
            % assembler.eloc(self,"ptoken",module=this_module)

        ptok=PChrExpr(self._primary,start=self.start_expr,length=self.len_expr,\
            string=self.string)

        return ptok

    def update_loc(self,line,loc):
        self.line=line          # This is the assembly statement line number
        self.linepos=loc.pndx   # Position within source input line
        self.source=loc.source  # Input source


# Character expressions take the general form:
#
#   'characters,'',&&... [symbol-ref] '[(start-expr,len-expr)]
#    <------------primary------------>   <---secondaries--->
#
# The primary expression is a list of unmodified portions of the string and any
# embedded symbolic variable reference identifying replacement content.  Double
# ampersands and double single quotes are all replaced here with a single ampersand
# and quote respectively.

# Instance Methods:
#   balanced_parens  Checks for balanced parenthesis.
#   expression_end   Completes the pending primary or secondary expression.
#   init             Initializes the MacroScope subclass by creating its result 
#                    object
#   result           Returns the scope's completed result object
#   init_result    * Creates the subclass' result object.
#   primary       ** Updates the result object with the primary expression
#   secondary     ** Updates the result object with its secondary expressions
# * init_result() method used internally by init() method
# ** primary() and secondary() methods are used internally by expression_end()
#
# Instance Methods Inherited from asmbase.AsmFSMScope:
#   ck_parens   Validates balanced parenthesis are present
#   flush       Discard all pending lexical tokens
#   init        Initializes the scope for use.
#   expr        Returns the lexical token list of the expression
#   expr_end    Returns the lexical token list after token update has occurred.
#   lparen      Add a left parenthesis lexical token to the pending list and track it
#   pending     Returns the number of lexical tokens pending for release
#   rparen      Add a right parenthesis lexical token to the pending list and track it
#   str_beg     Start a string represented by the asmtokens.StringToken() objects.
#   str_cont    Add more characters to the pending asmtokens.StringToken() object
#   str_end     Return the asmtokens.StringToken of the entire string.
#   str_pending Return whether a string is pending (True) or not (False).
#   token       Add a token to the pending expression
#   update_loc  Update a lexical token with is physical source (ASMPLoc object)
class CharacterExpr(CTermScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)
        self.cterm=True          # This is a scope for complex term

    def init_result(self):
        return ChrExpr(string=True)

    def primary(self,result=None):
        expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        #for n,item in enumerate(expr):
        #    print("%s token[%s]: %s" \
        #        % (assembler.eloc(self,"primary",module=this_module),\
        #            n,item))
        #self.opnd.primary(expr)
        self.opnd.primary(asmbase.ASMExprChar(expr,string=True))

    def secondary(self,result=None):
        expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        #for n,item in enumerate(expr):
        #    print("%s token[%s]: %s" \
        #        % (assembler.eloc(self,"secondary",module=this_module),\
        #            n,item))

        self.opnd.secondary(asmbase.ASMExprArith(expr))


#
#  +-------------------------------------+
#  |                                     |
#  |    CONDITIONAL BRANCHING CLASSES    |
#  |                                     |
#  +-------------------------------------+
#

# This is the result object of conditional branching scopes.
# The primary expression computes the conditional branch or for unconditional
# branches (unconditional AGO) it is the target sequence symbol
#
# For unconditional AGO:
#   self._primary is not used (set to None)
#   self._secondary list is not used (an empty list)
#   self._target is the target sequence symbol as a Python string
#
# For computed AGO:
#   self._primary is the computed arithmetic expression
#   self._secondary list is not used (an empty list
#   self._target is the first computed sequence symbol target as a Python string
# Other operands have additional sequence symbol targets and are parsed as Seq_Sym
# objects.  The statement subclass combines the computed targets before providing
# them to the AGOC macro operation.
#
# For each AIF operand:
#   self._primary is the conditional branch logical expression
#   self._secondary list is not used.
#   self._target is the target sequence symbol as a Python string

class CondBranch(asmbase.CTerm):
    def __init__(self,exprcls):
        super().__init__()
        self.exprcls=exprcls   # ASMExpr class of branch conditional expression
        # Targeted sequence symbol of the branch as a Python string
        self._target=None

    def prepare(self,stmt,desc):
        assert self._target is not None,"%s self._target is None" \
            % assembler.eloc(self,"prepare",module=this_module)
        if self._primary is None:
            return
        self._primary.prepare(stmt,desc)

    def target(self,token):
        # Target case sensitivity handled by the asmstmts.AIF.Pass0() method
        self._target=token.string     # Extract the sequence symbol from the token


class AGOScope(MacroScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)
        # Whether this is a computed AGO (True) or unconditional branch (False)
        self.conditional=True

    def _target(self,token):
        token.update_loc(self._stmt.lineno,self.lopnd)
        self.opnd.target(token)

    def init_result(self):
        return CondBranch(asmbase.ASMExprArith)

    def primary(self,result=None):
        if isinstance(result,asmtokens.LexicalToken):
            if result.tid=="SEQSYM":
                self._target(result)
                self.conditional=False
        elif isinstance(result,asmbase.ASMExpr):
            self.opnd.primary(result)
        else:
            raise ValueError("%s unexpeced result object: %s" \
                % (assembler.eloc(self,"primary",module=this_module),result))

    def result_returned(self,result):
        self.expression_end(result=result)

    def secondary(self,result=None):
        if isinstance(result,asmtokens.LexicalToken):
            self._target(result)
        else:
            raise ValueError("%s unexpected result object: %s" \
                % (assembler.eloc(self,"secondary",module=this_module),result))


class AIFScope(MacroScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)

    def _target(self,token):
        token.update_loc(self._stmt.lineno,self.lopnd)
        self.opnd.target(token)

    def init_result(self):
        return CondBranch(asmbase.ASMExprBinary)

    def primary(self,result=None):
        self.opnd.primary(result)

    def result_returned(self,result):
        self.expression_end(result=result)

    def secondary(self,result=None):
        if isinstance(result,asmtokens.LexicalToken):
            self._target(result)
        else:
            raise ValueError("%s unexpected result object: %s" \
                % (assembler.eloc(self,"secondary",module=this_module),result))


#
#  +-----------------------------------+
#  |                                   |
#  |    QUOTED STRING OPERAND SCOPE    |
#  |                                   |
#  +-----------------------------------+
#

class QuoteScope(asmbase.AsmFSMScope):
    def __init__(self,lopnd):
        super().__init__()
        self.lopnd=lopnd       # LOperand source object
        
    def init_result(self):
        pass

    # Return result object, a Python string
    def result(self):
        return self.str_end()
        
    def token(self,value):
        raise NotImplementedError("%s only calls to str_xxx methods supported" \
            % assembler.eloc(self,"token",module=this_module))

#
#  +--------------------------+
#  |                          |
#  |    SETC OPERAND SCOPE    |
#  |                          |
#  +--------------------------+
#

# This scope handles SETC operands, although they are essentially a single character
# expression, they need an ASMExprChar object as it primary.  This allows driving
# of the ultimate creation of the PChrExpr object for execution in the SETC
# statement.  The key difference is in the override of the primary() method
class SETCScope(MacroScope):
    def __init__(self,lopdn):
        super().__init__(lopdn)
        
    def init_result(self):
        return asmbase.ASMOperand()

    def primary(self,result=None):
        expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        #for n,item in enumerate(expr):
        #    print("%s token[%s]: %s" \
        #        % (assembler.eloc(self,"primary",module=this_module),\
        #            n,item))
        self.opnd.primary(asmbase.ASMExprChar(expr))  # Returns a C_Val object

    def secondary(self,result=None):
        expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        #for n,item in enumerate(expr):
        #    print("%s token[%s]: %s" \
        #        % (assembler.eloc(self,"secondary",module=this_module),\
        #            n,item))
        self.opnd.secondary(asmbase.ASMExprArith(expr))
    
    
#
#  +----------------------------+
#  |                            |
#  |   SEQUENCE SYMBOL CLASSES  |
#  |                            |
#  +----------------------------+
#

class SeqSymScope(MacroScope):
    def __init__(self,lopnd):
        super().__init__(lopnd)
        
        # self._primary is a list of one SEQSYM lexical token
        # self._secondary is not used

    def init_result(self):
        self.opnd=[]   # Result object will be the primary expression list

    def primary(self,result=None):
        self.opnd=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
        # List of tokens (should be only one)
        assert len(self.opnd)==1,"%s unexpected token in primary expresion: %s" \
            % assembler.eloc(self,"primary",module=this_module)

    def secondary(self,result=None):
        raise NotImplementedError("%s does not support secondary expressions" \
            % assembler.eloc(self,"secondary",module=this_module))

#
#  +-----------------------------+
#  |                             |
#  |   SYMBOL REFERENCE CLASSES  |
#  |                             |
#  +-----------------------------+
#

# The PSymRef class and its subclasses is modeled after the asmtokens.PLitLabel
# class and its subclasses.  The SymbolRef class is modeled after the
# asmtokens.LabelAttrToken class.

# Pratt Symbol Reference Term
# Instance Arguments:
#   token     The actual SATTR lexical token of this reference for error reporting
#   symbol    Sequence symbol being referenced (from token)
#   attr      Optional symbol attribute being referenced
#   indices   A list of ASMArithExpr objects of each index being requested.
#             May be an empty list if symbol or parmeter is not subscripted.
#             The number of indices can not be validated until the actual symbol
#             is referenced and it is known whether the symbol is a symbolic
#             variable (one index) or a macro parameter (multiple are valid)
class PSymRef(PCTerm):
    def __init__(self,token,symbol,attr=None,indices=[]):
        assert isinstance(symbol,str) and len(symbol)>0,\
            "%s 'symbol' argument must be a non-empty string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symbol)

        super().__init__(token)
        # Note: self.src is a SATTR lexical token object
        self.attr=attr             # Symbol attribute
        self.symname=symbol        # Symbolic Variable/Parameter beign referenced
        self.indices=indices       # List of prepared arithmetic expressions

    # Returns a symbol's macro symbol object (Mac_Sym or subclass)
    # Returns:
    #   a Mac_Sym or subclass
    # Exception:
    #   MacroError when variable symbol is undefined, 
    #              when a subscript is provided for an unsubscripted symbol, 
    #              when the subscript is out of range, or 
    #              when macro parameter sublists nesting depth is exceeded.
    def getSymbol(self,external,symid,debug=False):
        if __debug__:
            if debug:
                print("%s symid: %s" \
                    % (assembler.eloc(self,"vgetValue",module=this_module),\
                        symid.display()))

        value=external.lcls._reference_symbol(symid)  # Mac_Sym or subclass
        if __debug__:
            if debug:
                print("%s value: %s" \
                    % (assembler.eloc(self,"value",module=this_module),value))

        return value

    # Return a label's assembler symbol table entry (assembler.LabelSymbol object)
    # Method Arguments:
    #   label     The string representing the assembler label being queried
    #   extermal  The current Pratt external helper object
    #   excp      Whether an exception should be raised or not.  Specify True to
    #             raise an exception.  Specify False to return None.  Defaults to
    #             False.
    # Exception:
    #   PParserError if the label is not defined and excp=True
    def getSTE(self,label,external=None,excp=False,debug=False,trace=False):
        try:
            return external._getSTE_Ref(label,self.src.line)
            # Cross-reference label entry creation depends upon the external object:
            #  asmmacs.Invoker     - XREF entry is not generated
            #  assembler.Assembler - XREF entry is generated
        except KeyError:
            # Label not defined
            if excp:
                raise pratt3.PParserError(ptok=self.src,\
                    msg="undefined label: %s" % label) from None

        return None

    # Returns a symbol's value object for its referenced element
    # Returns:
    #   a A_Val, B_Val or C_Val object depending upon the symbol or parameter.
    # Exception:
    #   MacroError when variable symbol is undefined, 
    #              when a subscript is provided for an unsubscripted symbol, 
    #              when the subscript is out of range, or 
    #              when macro parameter sublists nesting depth is exceeded.
    def getValue(self,external,symid,debug=False):
        if __debug__:
            if debug:
                print("%s symid: %s" \
                    % (assembler.eloc(self,"vgetValue",module=this_module),\
                        symid.display()))

        value=external.lcls._reference(symid)  # Mac_Val or subclass
        if __debug__:
            if debug:
                print("%s value: %s" \
                    % (assembler.eloc(self,"value",module=this_module),value))

        return value

    # Returns the value object based upon the supplied macsyms.SymbolID and
    # macsyms.Mac_Sym subclass.
    def getValObj(self,sym,symid):
        if not symid.indexing():
            return sym.value
        if isinstance(sym,(macsyms.A_Sym,macsyms.B_Sym,macsyms.C_Sym)):
            raise MacroError("symbol %s does not support subscripts" % sym.name)
        return sym.value.fetch(symid.indices)

    # Creates a macsyms.SymbolID object suitable for access to the symbolic
    # variable or macro parameter.
    # Returns:
    #   A macsyms.SymbolID object
    # Exceptions:
    def SymID(self,external=None,debug=False,trace=False):
        indexes=[]
        for n,ndx_expr in enumerate(self.indices):
            index=ndx_expr.evaluate(external=external,debug=debug,trace=trace)
            indexes.append(index)
        return macsyms.SymbolID(self.symname,indices=indexes)

    # Provides the symbolic variable or parameter value or its attribute during
    # expression evaluation.
    # Method Arguments:
    #   external   The current asmmacs.EngineState object of the invoked macro
    #              Access to the symbol table is via this object
    # Returns:
    #   A_Val, B_Val or C_Val
    # Exceptions:
    #   MacroError when variable symbol is undefined, 
    #              when a subscript is provided for an unsubscripted symbol, 
    #              when the subscript is out of range, or 
    #              when too many subscripts supplied for a parameter
    def value(self,external=None,debug=False,trace=False):
        symid=self.SymID(external=external,debug=debug,trace=trace)
        return self.getValue(external,symid,debug=debug)


# This class supports references to symbolic variables shared by all symbols
class PSymRefAttr(PSymRef):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    def value(self,external=None,debug=False,trace=False):
        # Create the SymbolID used to access the symbol table
        symid=self.SymID(external=external,debug=debug,trace=trace)
        # Retrieve the symbol object associated with the symbol name, if defined
        symo=self.getSymbol(external,symid,debug=debug)
        # Retrieve the value object associated with the referenced symbol/indices
        valo=self.getValObj(symo,symid)
        # Return its attribute value
        if isinstance(valo,macsyms.Macro_Array):
            #print("%s %s'array: %s" \
            #    % (assembler.eloc(self,"value",module=this_module),self.attr,valo))
            return valo.getAttr(self.attr)
        return valo[self.attr]


# This class is used to reference label attributes for the label name that is
# the value of a SETC or macro parameter, including &SYSLIST.  The value must be
# a valid assembler label.
class PSymRefCAttr(PSymRef):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    # Treat a character attribute as a character self-defining term
    # This method is used by subclasses.
    def character(self,attr):
        return(ord(assembler.CPTRANS.a2e(attr)))

    def getLabel(self,external,debug=False):
        # Creaty the SymbolID used to access the symbol table
        symid=self.SymID(external=external,debug=debug)
        # Retrieve the symbol object associated with the symbol name, if defined
        symo=self.getSymbol(external,symid,debug=debug)
        # Retrieve the value object associated with the referenced symbol/indices
        v=self.getValObj(symo,symid)
        if isinstance(v,(macsyms.A_Val,macsyms.B_Val)):
            raise pratt3.PParserError(ptok=self.src,\
                msg="symbol %s'%s requires SETC symbol or parameter, "
                    "encountered: SET%s" \
                        % (self.attr,symid,v.__class__.__name__[0]))

        # Validate that the value is a valid assembler label
        if not v.islabel():
            raise pratt3.PParserError(ptok=self.src,\
                msg="symbolic variable %s value not a valid label: %s" \
                    % (symid,v._value))

        return v._value

    def value(self,external=None,debug=False,trace=False):
        label=self.getLabel(external,debug=debug)
        ste=self.getSTE(label,external=external,debug=debug,trace=trace)
        attr_val=ste[self.attr]
        if __debug__:
            if trace or debug:
                print("%s.value() %s'%s=%s" \
                    % (assembler.eloc(self,"value",module=this_module),\
                        attr,symid,attr_val))
        return attr_val


# Used to supply a label's definition status to the macro language, via a SETC
# symbol's value treated as an assembler label.
class PSymRefCAttr_D(PSymRefCAttr):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    def value(self,external=None,debug=False,trace=False):
        label=self.getLabel(external,debug=debug)
        lval=self.getSTE(label,external=external,excp=False,debug=debug,trace=trace)
        if lval is None:
            return 0
        return 1


# Used to supply a label's operation type to the macro language via a SETC
# symbol's value treated as an assembler operation.
class PSymRefCAttr_O(PSymRefCAttr):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    def value(self,external=None,debug=False,trace=False):
        label=self.getLabel(external,debug=debug)
        return external._getAttr_O(label.upper())


# Used to supply a label's
class PSymRefCAttr_OInt(PSymRefCAttr_O):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    def value(self,external=None,debug=False,trace=False):
        attr=super().value(external=external,debug=debug,trace=trace)
        return self.character(attr)


# Used for T' attribute of symbolic variables.  Results are dependent upon
# the symbolic variable.
# The following values may be returned
class PSymRefCAttr_T(PSymRefCAttr):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)

    def value(self,external=None,debug=False,trace=False):
        symid=self.SymID(external=external,debug=debug,trace=trace)
        v=external.lcls._reference_T(symid)
        # Undefined symbol will not trigger and exception, but subscript mismatch
        # will
        if v is None:
            # Symbol is undefined
            return "U"
        # Symbol is defined.
        if isinstance(v,(macsyms.A_Val,macsyms.B_Val)):
            return v["T"]     # Numeric type of symbol for SETA and SETB
        elif isinstance(v,macsyms.Parm_Val):
            cval=v.first() 
        elif isinstance(v,macsyms.C_Val):
            cval=v
        else:
            raise ValueError("%s unexpected value for symbol %s: %s" \
                % (assembler.eloc(self,"value",module=this_module),\
                    symid,v))
        # SETC symbol - determine if its value is a self-defining term
        sdval=cval.sdterm(external.pm,excp=False)
        if sdval is not None:
            return "N"
        # Value is not a self-defining term, so maybe it is an assembler label.
        if not cval.islabel():
            # Nope, not an assembler label
            return "U"

        # Retrive the assembler's value for the label
        ste=self.getSTE(cval._value,external=external,excp=False,\
            debug=debug,trace=trace)
        if ste is None:
            # label is undefined
            return "U"
        # Label is defined, now return _its_ T' attribute
        #print("%s ste:%s" \
        #    % (assembler.eloc(self,"value",module=this_module),ste))
        return ste["T"]


class PSymRefCAttr_TInt(PSymRefCAttr_T):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)
        
    def value(self,external=None,debug=False,trace=False):
        attr=super().value(external=external,debug=debug,trace=trace)
        return self.character(attr)


# This class accesses label attributes that need to be treated as character
# self-defining terms in arithmetic expressions.
class PSymRefCAttrInt(PSymRefCAttr):
    def __init__(self,token,symbol,attr=None,indices=[]):
        super().__init__(token,symbol,attr=attr,indices=indices)
        
    def value(self,external=None,debug=False,trace=False):
        v=super().value(external=external,debug=debug,trace=trace)
        if isinstance(v,int):
            return v
        if isinstance(v,str):
            # Convert to character self-defining term value
            return self.character(v[0])
        raise ValueError("%s unexpected attribute value: %s" \
            % (assembler.eloc(self,"value",module=this_module),v))


# This object must support three roles:
#  1. As the parsed symbolic reference following the parse
#  2. Because it is added to expressions, it must support preparation of embedded
#     expressions.
#  3. It must itself generate a Pratt PLit subclass allowing evaluation of the
#     complex term.
#
# object[index] retrieves a subscript expression
class SymbolRef(asmbase.CTerm):
    # These class attributes are initialized by MacroParser.Sym() method
    attr_tids=None    # These TIDs support recognition of a symbol attribute
    noattr_tids=None  # These TIDs do not support recognition of symbol attribute
    # Classes used for macro arithmetic expressions
    #                                     Attribute
    a_attr={"D":PSymRefCAttr_D,       #      int
            "I":PSymRefCAttr,         #      int
            "K":PSymRefAttr,          #      int
            "L":PSymRefCAttr,         #      int
            "M":PSymRefCAttr,         #      int
            "N":PSymRefAttr,          #      int
            "O":PSymRefCAttr_OInt,    #      char as self-defining term
            "S":PSymRefCAttr,         #      int
            "T":PSymRefCAttr_TInt}    #      char as self-defining term
    # Classes used for macro logical expressions
    #                                     Attribute
    b_attr={"D":PSymRefCAttr_D,       #      int
            "I":PSymRefCAttr,         #      int
            "K":PSymRefAttr,          #      int
            "L":PSymRefCAttr,         #      int
            "M":PSymRefCAttr,         #      int
            "N":PSymRefAttr,          #      int
            "O":PSymRefCAttr_O,       #      char
            "S":PSymRefCAttr,         #      int
            "T":PSymRefCAttr_T}       #      char
    # Classes use for character expressions (SETC directives)
    # Note: Presently the same classes are used as with a logical expression
    #                                     Attribute
    c_attr={"D":PSymRefCAttr_D,       #      int
            "I":PSymRefCAttr,         #      int
            "K":PSymRefAttr,          #      int
            "L":PSymRefCAttr,         #      int
            "M":PSymRefCAttr,         #      int
            "N":PSymRefAttr,          #      int
            "O":PSymRefCAttr_O,       #      char
            "S":PSymRefCAttr,         #      int
            "T":PSymRefCAttr_T}       #      char

    def __init__(self):
        super().__init__()
        # self._primary will be a SATTR lexical token for the referenced symbol
        # self._secondary will be a list of expressions, one per symbol index

        # These values are extracted from the SATTR lexical token by primary() method
        self.symname=None    # The symbol name as coded in the source
        self.attr=None       # Attribute of symbol reference being requested

    # Returns a suscript's prepared expression based upon its index in the list
    # Returns:
    #   asmbase.ASMExprArith object of the expression computing the subscript.
    def __getitem__(self,key):
        return self._secondary[key]

    def __str__(self):
        cls=self.__class__.__name__
        if self.attr is not None:
            attr="%s'" % self.attr
        else:
            attr=""
        if len(self._secondary)==0:
            return "%s(%s%s)" % (cls,attr,self.symname)
        return "%s(%s%s(%s))" % (cls,attr,self.symname,self._secondary)

    def atoken(self):
        if self.attr is None:
            return PSymRef(\
                self._primary,self.symname,attr=self.attr,indices=self._secondary)
        try:
            cls=SymbolRef.a_attr[self.attr]
        except KeyError:
            raise assembler.LabelError(self.label,ltok=self,\
                msg="attribute %s unsupported in macro arithmetic expressios" \
                    % self.attr) from None
        return cls(self._primary,self.symname,attr=self.attr,indices=self._secondary)

    def btoken(self):
        if self.attr is None:
            return PSymRef(\
                self._primary,self.symname,attr=self.attr,indices=self._secondary)
        try:
            cls=SymbolRef.b_attr[self.attr]
        except KeyError:
            raise assembler.LabelError(self.label,ltok=self,\
                msg="attribute %s unsupported in macro logical expressios" \
                    % self.attr) from None
        return cls(self._primary,self.symname,attr=self.attr,indices=self._secondary)

    def ctoken(self):
        if self.attr is None:
            return PSymRef(\
                self._primary,self.symname,attr=self.attr,indices=self._secondary)
        try:
            cls=SymbolRef.c_attr[self.attr]
        except KeyError:
            raise assembler.LabelError(self.label,ltok=self,\
                msg="attribute %s unsupported in macro logical expressios" \
                    % self.attr) from None
        return cls(self._primary,self.symname,attr=self.attr,indices=self._secondary)

    def hasSubscript(self):
        return len(self._secondary)!=0

    def ptoken(self):
        raise NotImplementedError(\
            "%s assembler statements do not support symbolic references" \
                % assembler.eloc(self,"ctoken",module=this_module))
        # This is because symbolic references in assembler statements should have
        # been replaced in model statements.


    # Prepare the ASMExpr objects in self._secondary for execution - this converts
    # each lexical token or complex term object into 
    def prepare(self,stmt,desc):
        for n,exp in enumerate(self._secondary):
            d="%s expr %s" % (desc,n)
            exp.prepare(stmt,d)

    # Accepts three different lexical tokens as the primary expression
    #  - SAREF  - in SETC where symbol attribute is the character expression - X'&SYM
    #  - SATTR  - in macro statements with or without an attribute - x'&SYM or &SYM 
    #  - SYMBOL - in character replacement using a concatenated symbold - &SYM.
    #  - SYM    - in character replacement without an attribute - &SYM... or &SYM(
    def primary(self,tok):
        assert isinstance(tok,asmtokens.LexicalToken),\
            "%s 'tok' argument must be a LexicalToken object: %s" \
                % (assembler.eloc(self,"primary",module=this_module),tok)

        super().primary(tok)      # sets self._primary to the token object
        #if tok.tid=="SATTR":
        if tok.tid in SymbolRef.attr_tids:
            self.attr=tok.attr    # Retrieve the optional attribute if recognized
        else:
            assert tok.tid in ["SYMBOL","SYM"],\
                "%s 'tok' argument must have a token id of SATTR, SYMBOL or SYM: %s"\
                    % (assembler.eloc(self,"primary",module=this_module),tok)
            pass
        self.symname=tok.symname  # Retrieve the referenced symbol from the token

    def update_loc(self,line,loc):
        self.line=line            # This is the assembly statement line number
        self.linepos=loc.pndx     # Position within source input line
        self.source=loc.source    # Input source


class SymbolicReference(CTermScope):
    tids=None    # This class attributes in initialized by MacroParser.Sym() method
    def __init__(self,lopdn):
        super().__init__(lopdn)

    def init_result(self):
        return SymbolRef()
        
    def primary(self,result=None):
        pending=self.pending()   # How many tokens in the pending list
        # For a symbolic reference this should onle ever be 1
        assert pending==1,\
            "%s pending tokens must only be one: %s" \
                % (assembler.eloc(self,"primary",module=this_module),pending)
                
        pend_tok=self._lextoks[0]
        self.flush()     # Now discard the tokens, I have responsibility
        self.update_loc(self.lopnd,self._stmt.lineno,pend_tok)
        self.opnd.primary(pend_tok)

    def result_returned(self,res):
        self.expression_end(result=res)

    def secondary(self,result=None):
        assert result is not None,"%s result is None" \
            % assembler.eloc(self,"secondary",module=this_module)
        self.opnd.secondary(result)

    def token(self,tok):
        # Bubble up to the statement whether syslist is needed in macro.
        # The statement communicates this to the macro under construction.
        #if tok.tid in ["SYM","SYMBOL","SYM",]:
        if tok.tid in SymbolicReference.tids:
            if self._case:
                self._stmt.syslist=tok.symname=="&SYSLIST"
            else:
                self._stmt.syslist=tok.symname.upper()=="&SYSLIST"
        super().token(tok)


#
#  +------------------------------+
#  |                              |
#  |    MACRO STATEMENT PARSER    |
#  |                              |
#  +------------------------------+
#

# This class helps to direct macro statement parsing.  The enter_scope() and
# leave_scope() methods use this object to determine actions taken during a
# change of scope or where a context change occurs.
#
# These objects are long lived and should be considered immutable.  If there is
# a need for a new object or one based upon dynamic considerations, it should
# be instantiated at that time for the duration of its use.
# 
# Instance Arguments:
#   start      Identifies the first FSM state upon entering or the next
#              FSM state upon leaving.
#   pctx       Identifies the first parser context or next parser context
#   scope      Identifies the scope for a new statement
class MPControl(object):
    def __init__(self,start,pctx=None,scope=None):
        # Attributes related to entering a scope
        self.start=start        # FSM state upon entering this control state
        self.context=pctx       # Parser context in which the entered scope operates
        
        self.scope=scope        # Scope class (only used for parser entry)
        
    def __str__(self):
        return "%s(start=%s,pctx=%s,scope=%s)" \
            % (self.__class__.__name__,self.start,self.context,self.scope)


class MacroParser(asmbase.AsmCtxParser):
    init_states={"ACTR": MPControl("aop",  pctx="init", scope=ArithScope),
                 "AGO":  MPControl("ago",  pctx="init", scope=AGOScope),
                 "AIF":  MPControl("aif",  pctx="init", scope=AIFScope),
                 "GBLA": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "GBLB": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "GBLC": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "LCLA": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "LCLB": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "LCLC": MPControl("inits",pctx="sym",  scope=SymbolicReference),
                 "SETA": MPControl("aop",  pctx="init", scope=ArithScope),
                 "SETB": MPControl("bop",  pctx="init", scope=BinaryScope),
                 "SETC": MPControl("setc", pctx="setc", scope=SETCScope),
                 "TITLE":MPControl("initq",pctx="quote",scope=QuoteScope),
                 "rep" : MPControl("initr",pctx="rep",  scope=CharacterExpr),
                 "seq":  MPControl("seqb", pctx="seq",  scope=SeqSymScope),
                 "sym":  MPControl("inits",pctx="sym",  scope=SymbolicReference)}
    def __init__(self,dm,pm):
        # Lexical token lists used during initialze() method processing
        self.term= [SDBIN,SDHEX,SDCHR,SDDEC,LATTR]
        #self.cterm=[SATTR,]
        #self.char =[QUOTE,]
        #self.aoper=[AOPER,]
        self.boper=[LOGNOT,LOGICAL,NOT,COMPARE]
        super().__init__(dm,pm,"macs",trace=False)
        self.case=pm.asm.case    # Whether case sensitive symbols in use

    def Lexer(self,lexer):
        return super().Lexer("macs")

    def init_context(self):
        self.ctx("cexpr", lexctx="cexpr", gbl=True,ccls=None)
        self.ctx("init",  lexctx="init",  gbl=True,ccls=None)
        self.ctx("quote", lexctx="quote", gbl=True,ccls=None)
        self.ctx("rep",   lexctx="rep",   gbl=True,ccls=None)
        self.ctx("seq",   lexctx="seq",   gbl=True,ccls=None)
        self.ctx("setc",  lexctx="setc",  gbl=True,ccls=None)
        self.ctx("string",lexctx="string",gbl=True,ccls=None)
        self.ctx("sym",   lexctx="sym",   gbl=True,ccls=None)

    def initialize(self):

        # Expression parsing involves primarily six states:
        #   init    Initial state at the start of the expression parsing.  This is 
        #           the state at the start of processing the primary and each
        #           secondary expression.
        #   term    The state following a term: label, self-defining term or the
        #           current location (*)
        #   chterm  The state following initial character expression token
        #   cterm   The state following initial complex term token
        #   binary  The state following a binary operator: +, -, * (multiply), /
        #   unary   The state following a unary operator: +, -
        #   lparen  The state following a left parenthesis: (
        #   rparen  The state following a right parenthesis: )
        #   end     The state at which the operand should be completely parsed
        term_tokens=[SDBIN,SDHEX,SDCHR,SDDEC,LATTR]
        cterm_tokens=[SATTR,]
        chr_tokens=[QUOTE,]
        aoper_tokens=[AOPER,]
        boper_tokens=[LOGNOT,LOGICAL,NOT]

        self.Ago()       # Initialize AGO statement states
        self.Aif()       # Initialize AIF statement states
        self.Aopnd()     # Initialize arithmetic operand states
        self.Arith()     # Initialize arithmetic expression call scope states
        #self.Binary_Old() # Initialize binary (logical) expression states
        self.Binary()    # Initialize binary expression call scope states
        self.Bopnd()     # Initialize binary operand states
        self.Chr()       # Initialize character expression complex term states
        self.Decl()      # Initialize symbolic declaration states
        self.Quote()     # Initialize open code quoted string states
        self.Rep()       # Initialize symbolic replacement states
        self.Seq()       # Initialize sequence symbol recognition states
        self.Sym()       # Initialize symbolic reference states
        self.SETC()      # Initialize SETC statement states

    # This method is used to parse an individual ASMString object.
    def _parse_operand(self,stmt,asmstr,mp,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"_parse_operand",module=this_module),\
                        debug))
                self.trace(on=debug)   # Set FSM trace stateACT_Term_R
        self.init(mp.start)            # Set FSM initial state
        sc=mp.scope(asmstr)            # Create the scope object
        sc.cterm=False                 # Never a complex term if created here
        sc.init(stmt=stmt)             # Pass it the statement

        # Parse the operand
        scope=self.parse(asmstr.text,context=mp.context,scope=sc,fail=False)
        if __debug__:
            if debug:
                print("%s [%s] scope: %s" \
                    % (assembler.eloc(self,"_parse_operand",module=this_module),\
                        stmt.lineno,scope))
                self.trace(on=False)

        return scope.result()

    # Return from a scope/context "call"
    def Call_Return(self,token=None,trace=False):
        gs=self.scope()
        if token:
            self.lex_retry(token,trace=trace)
        result=gs.result()
        return self.leave_scope(result=result,stack=None,trace=trace)  

    # Enter a new scope, stacking the current scope.
    # This method uses an MPControl object to enter a new scope
    # Method Arguments:
    #   old   Current active context
    #   retmp MPControl object defining how called scope returns to the current 
    #         scope
    #   new   Scope of new context
    #   newmp MPControl object defining how to start the new scope
    #   stack a Token object that is optionally passed to the new context/scope as
    #         its first input item presented to its initial FSM state.
    #   trace Specify True to cause information about the enter_scope method to 
    #         be displayed.
    # Note: This method is normally used by a method that invokes the new context
    # and scope that understand how to enter it.
    # 
    # A current context/scope calls a new context and scope by calling a method
    # dedicated to entering the new context/scope.  This occurs within an action
    # of the current context/scope.  The current/scope knows to where the called
    # context/scope whould return and constructs that information in a MPControl
    # object, passed to the called context/scope's entry helper method.
    #
    #      return self.Sub_Call(returnMP)
    #
    # Sub_Call will determine the current active scope and pass it with
    # the returnMP to the enter_scope() method.  It will further create the the
    # MPControl object for entering the new context/scope and a new context object.
    # Sub_Call will marshall the values to call the enter_scope() method.  Its
    # final act is to return the initial FSM state to enter the called context/scope.
    # It is the responsibility of the caller of Sub_Call to pass the new FSM state
    # of the called context/scopt to the finite state machine processor, hence the
    # return in the above statement.
    def enter_scope(self,old,retmp,new,newmp,stack=None,trace=False):
        if __debug__:
            if trace:
                print("%s new mp:%s return mp:%s stack:%s" \
                    % (assembler.eloc(self,"enter_scope",module=this_module),\
                        newmp,retmp,stack))
        # Stack this input value if requested.  It will be the first value
        # returned in the new scope.
        if stack:
            # This sequence results in passing this lexical token to the 
            # next state's input, letting it be processed as the first token of
            # the new scope.
            self.stack(stack,trace=trace)
            self.unstack(trace=trace)
        # Save state upon return to the old scope
        old.next_state=retmp.start
        if retmp.context:
            old.next_pctx=retmp.context
        else:
            old.next_pctx=self.ctx_name
        assert old.next_pctx is not None,"%s old.next_pctx is None" \
            % assembler.eloc(self,"enter_scope",module=this_module)

        # Prepare the new scope with assembler information from the old scope
        # object.
        new.init(stmt=old._stmt,case=self.case)

        self.push_scope(new,trace=trace)
        # Old scope is now on the LIFO stack and the new scope is active
        if newmp.context:
            # Switch to the new lexical context of the new scope
            self.context(newmp.context)
        # Enter the new context/scope by returning its initial FSM state
        return newmp.start

    # Returning to a previously stacked scope.  Most of the relavent information
    # was placed in the returning scope by the enter_scope() method.  This method
    # uses this information to restablish parsing under the control of the previously
    # pushed scope.
    #
    # Method Arguments:
    #   result    Specify a result object being returned to the previous scope.
    #             It will automatically be added to the previous scopes lexical
    #             tokens.  Specify None to return no object.  Defaults to None.
    #   stack     Specify the input value to be stacked for processing by the
    #             next state of the scope to which control returns.  Specify None
    #             to not perform input stacking.  Defaults to None.
    def leave_scope(self,result=None,stack=None,trace=False):
        if __debug__:
            if trace:
                print("%s leaving scope: %s" \
                    % (assembler.eloc(self,"leave_scope",module=this_module),\
                        self.scope()))
        # Fetch the scope to which we are returning from the scope stack
        ret=self.pop_scope(trace=trace)
        # Pass to it as a new token the result of the returning scope
        if result:
            ret.result_returned(result)
            #ret.token(result)
        # If returning scope has a stack item, make it the next FSM input value
        if stack:
            self.stack(stack,trace=trace)
            self.unstack(trace=trace)
        # Restore the parser (and by implication lexical context) for the scope to 
        # which control is returning
        assert ret.next_pctx is not None,"%s %s.next_pctx is None" \
            % (assembler.eloc(self,"leave_scope",module=this_module),ret)
        self.context(ret.next_pctx)
        ret.pctx=None
        # Return the next state to receive the next input value
        next=ret.next_state
        ret.next_state=None
        return next

    # Cause the context sensitive lexical analyzer to reset its next position
    # so that this sequence can be recognized in its new lexical context.
    # The new lexical context may recognize an entirely different token and present
    # it to the new FSM state as input.
    #
    # The exception is the End-of-String (EOS) token that will simply be made
    # available to the next FSM state as input.  Once at the EOS there is nothing
    # to retry by the lexer.
    def lex_retry(self,token,trace=False):
        if __debug__:
            if trace:
                print("%s lexical recognition retry for: %s" \
                    % (assembler.eloc(self,"reject",module=this_module),token))

        if token.tid=="EOS":
            self.stack(token,trace=trace)
            self.unstack(trace=trace)
        else:
            self.lex.reject(token)

    # Parses the first operand of an AGO statement, differentiating between a 
    # computed AGO and unconditional AGO transfer of control.
    def parse_ago(self,stmt,opnd,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_ago",module=this_module),debug))

        mp=MacroParser.init_states["AGO"]
        result=self._parse_operand(stmt,opnd,mp,debug=debug)
        if __debug__:
            if debug:
                print("%s resulto: %s" \
                    % (assembler.eloc(self,"parse_ago",module=this_module),result))
        return result

    # Parses a macro language statement's operands
    # The initial state of the parser is determined by the statement's operation
    def parse_operands(self,stmt,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_operands",module=this_module),\
                        debug))
                print("%s [%s]" \
                    % (assembler.eloc(self,"parse_operands",module=this_module),\
                        stmt.lineno))

        try:
            mp=MacroParser.init_states[stmt.instu]
        except KeyError:
            raise ValueError("%s MPControl object not defined for operation: %s"\
                % (assembler.eloc(self,"parse_operands",module=this_module),\
                    stmt.instu))

        self.operands=[]
        for n,opnd in enumerate(stmt.operands):
            if opnd is None:
                self.operands.append(None)
                continue
            if __debug__:
                if debug:
                    print('%s [%s] parsing operand %s: "%s"' \
                        % (assembler.eloc(self,"parse_operands",module=this_module),\
                            stmt.lineno,n,opnd.text))

            opnd=self._parse_operand(stmt,opnd,mp,debug=debug)

            if isinstance(opnd,asmbase.ASMOperand) \
               or isinstance(opnd,asmtokens.StringToken):
                self.operands.append(opnd)
            else:
                raise ValueError("operand not returned from parse: %s" % opnd)
        return self.operands   # List of POperand objects or None if omitted
        
    # This method is used to parse an individual field or operand for symbolic
    # replacement in model statements.
    # Exception:
    #   AsmParserError if parse fails
    # Note: Normally accessed via the parser.ParserMgr.parse_model() method
    def parse_model(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_model",module=this_module),debug))

        mp=MacroParser.init_states["rep"]
        result=self._parse_operand(stmt,field,mp,debug=debug)
        if __debug__:
            if debug:
                print("%s resulto: %s" \
                    % (assembler.eloc(self,"parse_model",module=this_module),result))
        return result

    # This method is used to parse an individual ASMString object.  Some statements
    # need to control how each operand in recognized.
    def parse_operand(self,stmt,asmstr,mpname,debug=False):
        try:
            mp=MacroParser.init_states[mpname]
        except KeyError:
            raise ValueError("%s 'mpname argument unrecognized: %s" \
                % (assembler.eloc(self,"parse_operand",module=this_module),mpname))
        result=self._parse_operand(stmt,asmstr,mp,debug=debug)
        if __debug__:
            if debug:
                print("%s resulto: %s" \
                    % (assembler.eloc(self,"parse_operand",module=this_module),result))
        return result

    # This method is used to parse an individual field or operand containing a 
    # single sequence symbol
    # Exception:
    #   AsmParserError if parse fails
    # Note: Normally accessed via the parser.ParserMgr.parse_seqsym() method
    def parse_seqsym(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_seqsym",module=this_module),debug))

        mp=MacroParser.init_states["seq"]
        result=self._parse_operand(stmt,field,mp,debug=debug)
        if __debug__:
            if debug:
                print("%s resulto: %s" \
                    % (assembler.eloc(self,"parse_seqsym",module=this_module),result))
        return result

    # This method is used to parse an individual statement label field.
    # This is used specifically for SETx directives via the LField object
    # Exception:
    #   AsmParserError if parse fails
    # Note: Normally accessed via the parser.ParserMgr.parse_label() method
    def parse_symbol(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_symbol",module=this_module),debug))

        mp=MacroParser.init_states["sym"]
        return self._parse_operand(stmt,field,mp,debug=debug)


  #                 +-----------+
  #                 |           |
  #                 |    AGO    |
  #                 |           |
  #                 +-----------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: AGOScope
    # Result Object: CondBranch
    # See MacroCSLexer.init_default() method
    
    # Parses:
    #
    #    Case 1 - An unconditional transfer of control.
    #
    #        .SEQSYM
    #            ^      
    #            |
    #            +--- target
    #
    #    Case 2 - An arithmetic expression enclosed within paired parethensis
    #             and immediately followed by the target sequence symbol.  The 
    #             'target' is specific to this scope's result object.  The target
    #             if the first of possibly more operands defining the collection
    #             of computed AGO targets.  The additional targets are statement
    #             operands parsed separately.
    #
    #
    #        (&SYM1 EQ &SYM2 OR &SYM3...).SEQSYM
    #         \____________ ___________/     ^      
    #                      v                 |
    #              Primary Expression        +--- target
    #
    # Note: additional target sequence symbols in the computed AGO case are
    # processed as additional operands, not part of the first operand.  See
    # the asmstmts.AGO class for details.

    def Ago(self):
        
        ago=fsmparser.PState("ago")
        ago.action([SEQSYM,],self.Ago_Target)               #   None .seq  agoe
        ago.action([LPAREN,],self.Ago_Computed)             #   None (     >a-expr
        ago.error(self.ACT_Expected_LP_Seq)                 # E None ???
        self.state(ago)
        
        agor=fsmparser.PState("agor")
        agor.action([RPAREN,],self.Ago_ExprEnd)             #   expr )     agos
        agor.error(self.ACT_Expected_RP)                    # E expr ???
        self.state(agor)
        
        agos=fsmparser.PState("agos")
        agos.action([SEQSYM,],self.Ago_Target)              #   )    .seq  agoe
        agos.error(self.ACT_Expected_Seq_Only)              # E )    ???
        self.state(agos)
        
        agoe=fsmparser.PState("agoe")
        agoe.action([EOS,],self.Ago_Done)                   #   .seq  EOS  done
        agoe.error(self.ACT_ExpectedEnd)                    # E .seq  ???
        self.state(agoe)

    def Ago_Computed(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("agor",pctx="init")
        return self.Arith_Call(ret,follow=[RPAREN,],trace=trace)

    def Ago_Done(self,value,state,trace=False):
        state.atend()

    def Ago_ExprEnd(self,value,state,trace=False):
        # Just consume the ending right parenthesis and then look for first target
        return "agos"

    def Ago_Target(self,value,state,trace=False):
        gs=self.scope()
        gs.opnd.target(value)
        return "agoe"


  #                 +-----------+
  #                 |           |
  #                 |    AIF    |
  #                 |           |
  #                 +-----------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: AIFScope
    # Result Object: CondBranch
    # See MacroCSLexer.init_default() method

    # Parses:
    #
    #    A logical (binary) expression enclosed within paired parethensis and
    #    immediately followed by the target sequence symbol.  The 'target' is
    #    specific to this scope's result object. 
    #
    #
    #        (&SYM1 EQ &SYM2 OR &SYM3...).SEQSYM
    #         \____________ ___________/     ^      
    #                      v                 |
    #               Primary Expression       +--- target

    def Aif(self):

        aif=fsmparser.PState("aif")
        aif.action([LPAREN,],self.Aif_Expr)                 #   None (     >b-expr
        aif.error(self.ACT_Expected_LP)                     # E None ???
        self.state(aif)

        aifr=fsmparser.PState("aifr")
        aifr.action([RPAREN,],self.Aif_Rparen)              #   <binary )  aift
        aifr.error(self.Aif_Binary_Call_Failure)            # E <binary ???
        self.state(aifr)

        aift=fsmparser.PState("aift")
        aift.action([SEQSYM,],self.Aif_Target)              #   )  .seq  aife 
        aift.error(self.ACT_Expected_Seq)                   # E )  ???
        self.state(aift)

        aife=fsmparser.PState("aife")
        aife.action([EOS,],self.Aif_Done)                   #   .seq  EOS   done
        aife.error(self.ACT_ExpectedEnd)                    # E .seq  ???
        self.state(aife)

    def Aif_Binary_Call_Failure(self,value,state,trace=False):
        raise ValueError("%s Binary_Call returned unexpected token: %s" \
            % (assembler.eloc(self,"Aif_Binary_Call_Failure",module=this_module),\
                value))

    def Aif_Expr(self,value,state,trace=False):
        ret=MPControl("aifr",pctx="init")
        return self.Binary_Call(ret,token=None,follow=[RPAREN,],trace=trace)

    def Aif_Rparen(self,value,state,trace=False):
        return "aift"

    def Aif_Target(self,value,state,trace=False):
        gs=self.scope()
        gs.opnd.target(value)
        return "aife"

    def Aif_Done(self,value,state,trace=False):
        gs=self.scope()
        #gs.expression_end()     # Complete capture conditional branch target
        state.atend()           # Terminate the finite state machine


  #                 +-----------------------------------+
  #                 |                                   |
  #                 |   ARITHMETIC EXPRESSION OPERAND   |
  #                 |                                   |
  #                 +-----------------------------------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: ArithScope
    # Result Object: asmbase.ASMExprArith
    # See MacroCSLexer.init_default() method

    # Parses:
    #
    #    arithmetic-expression$
    #    \__________ _________/
    #               v
    #      Primary Expression

    def Aopnd(self):

        aop=fsmparser.PState("aop")
        aop.error(self.Aopnd_Start)                          #   None  ???  >arith
        self.state(aop)
        
        aope=fsmparser.PState("aope")
        aope.action([EOS,],self.Aopnd_End)                   #   <arith EOS  Done
        aope.error(self.ACT_ExpectedEnd)                     # E ????
        self.state(aope)

    def Aopnd_Start(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("aope",pctx="init")
        return self.Arith_Call(ret,token=value,follow=[EOS,],trace=trace)
        
    def Aopnd_End(self,value,state,trace=False):
        gs=self.scope()
        state.atend()


  #                 +-------------------------------+
  #                 |                               |
  #                 |   BINARY EXPRESSION OPERAND   |
  #                 |                               |
  #                 +-------------------------------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: BinaryScope
    # Result Object: asmbase.ASMExprBinary
    # See MacroCSLexer.init_default() method

    # Parses:
    #
    #    binary-expression$
    #    \_______ _______/
    #            v
    #      Primary Expression

    def Bopnd(self):

        bop=fsmparser.PState("bop")
        bop.error(self.Bopnd_Start)                          #   None  ???  >arith
        self.state(bop)
        
        bope=fsmparser.PState("bope")
        bope.action([EOS,],self.Aopnd_End)                   #   <arith EOS  Done
        bope.error(self.ACT_ExpectedEnd)                     # E ????
        self.state(bope)

    def Bopnd_Start(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("aope",pctx="init")
        return self.Binary_Call(ret,token=value,follow=[EOS,],trace=trace)
        
    def Bopnd_End(self,value,state,trace=False):
        gs=self.scope()
        state.atend()



  #                 +-----------------------------+
  #                 |                             |
  #                 |    ARITHMETIC EXPRESSION    |
  #                 |                             |
  #                 +-----------------------------+
  
    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: current scope
    # See MacroCSLexer.init_default() method

    #def Arith_Old(self):

    #    inita=fsmparser.PState("inita")
    #    inita.action(self.term,self.Expr_Term)               #   None  term   terma
    #    inita.action([SATTR,],self.Expr_Start_S)             #   None  sym    >
    #    inita.action([AOPER,],self.Expr_Start_O)             #   None  oper   unarya/E
    #    inita.action([LPAREN,],self.Expr_Start_L)            #   None  (      lparena
    #    inita.action(self.boper,self.ACT_Expected_Aoper)     # E None  boper
    #    inita.action([QUOTE,],self.ACT_Expected_LP_Term)     # E None  '
    #    inita.action([RPAREN,],self.ACT_Expected_LP_Term)    # E None  )
    #    inita.action([COMMA,],self.ACT_Expected_LP_Term)     # E None  ,
    #    inita.action([EOS,],self.ACT_Expected_LP_Term)       # E None  EOS
    #    inita.error(self.ACT_Expected_LP_Term)               # E None  ??
    #    self.state(inita)

    #    unarya=fsmparser.PState("unarya")
    #    unarya.action(self.term,self.Expr_Term)              #   unary term   terma
    #    unarya.action([SATTR,],self.Expr_Unary_S)            #   unary sym    >sym
    #    unarya.action([LPAREN,],self.Expr_Unary_L)           #   unary (      lparena
    #    unarya.action([AOPER,],self.ACT_Expected_LP_Term)    # E unary aoper
    #    unarya.action(self.boper,self.ACT_Expected_Aoper)    # E None  boper
    #    unarya.action([RPAREN,],self.ACT_Expected_LP_Term)   # E unary )
    #    unarya.action([COMMA,],self.ACT_Expected_LP_Term)    # E unary ,
    #    unarya.action([EOS,],self.ACT_Expected_LP_Term)      # E unary EOS
    #    self.state(unarya)

    #    binarya=fsmparser.PState("binarya")
    #    binarya.action(self.term,self.Expr_Term)             #   binary term  terma
    #    binarya.action([SATTR,],self.Expr_Binary_S)          #   binary sym   >
    #    binarya.action([AOPER,],self.Expr_Binary_O)          #   binary oper unarya/terma
    #    binarya.action([LPAREN,],self.Expr_Binary_L)         #   binary (
    #    binarya.action(self.boper,self.ACT_Expected_Aoper)   # E binary boper
    #    binarya.action([RPAREN,],self.ACT_Expected_LP_Term)  # E binary )
    #    binarya.action([COMMA,],self.ACT_Expected_RP_Oper)   # E binary ,
    #    binarya.action([EOS,],self.ACT_Expected_LP_Term)     # E binary EOS
    #    self.state(binarya)

    #    lparena=fsmparser.PState("lparena")
    #    lparena.action(self.term,self.Expr_Term)             #   ( term     terma
    #    lparena.action([SATTR,],self.Expr_LParen_S)          #   ( sym      >
    #    lparena.action([AOPER,],self.Expr_LParen_O)          #   ( oper unarya/terma/E
    #    lparena.action([LPAREN,],self.Expr_LParen_L)         #   ( (        lparena
    #    lparena.action(self.boper,self.ACT_Expected_Aoper)   # E ( boper
    #    lparena.action([RPAREN,],self.ACT_Expected_LP_Term)  # E ( )
    #    lparena.action([COMMA,],self.ACT_Expected_LP_Term)   # E ( ,
    #    lparena.action([EOS,],self.ACT_Expected_LP_Term)     # E ( EOS
    #    self.state(lparena)

    #    rparena=fsmparser.PState("rparena")
    #    rparena.action([AOPER,],self.Expr_RParen_O)          #   ) aoper  binarya/E
    #    rparena.action([LPAREN,],self.Expr_RParen_L)         #   ) (       inita/E
    #    rparena.action([RPAREN,],self.Expr_RParen_R)         #   ) )     rparena/enda
     #   rparena.action([COMMA,],self.Expr_RParen_C)          #   ) ,       inita/E
    #    rparena.action([EOS,],self.Expr_RParen_E)            #   ) EOS     done/E
    #    rparena.action(self.boper,self.ACT_Expected_Aoper)   # E ) boper
    #    rparena.action(self.term,self.ACT_Expected_RP_Oper)  # E ) term
    #    rparena.action([SATTR,],self.ACT_Expected_RP_Oper)   # E ) sym
    #    rparena.error(self.Expr_Follow)                      #   ) follow  done/E
    #    self.state(rparena)

    #    terma=fsmparser.PState("terma")
    #    terma.action([AOPER,],self.Expr_Term_O)              #   term aoper binarya/E
    #    terma.action([LPAREN,],self.Expr_Term_L)             #   term (    inita/E
    #    terma.action([RPAREN,],self.Expr_Term_R)             #   term )   rparena/end
    #    terma.action([COMMA,],self.Expr_Term_C)              #   term ,    inita/E
    #    terma.action([EOS,],self.Expr_Term_E)                #   term EOS   done/E
    #    terma.action(self.boper,self.ACT_Expected_Aoper)     # E term boper
    #    terma.action(self.term,self.ACT_Expected_RP_Oper)    # E term term
    #    terma.action([SATTR,],self.ACT_Expected_RP_Oper)     # E term sym
    #    terma.error(self.Expr_Follow)                        #   term follow  done/E
    #    self.state(terma)

        # This state ensures nothing follows the final secondary expression's
        # terminating right parenthesis
    #    enda=fsmparser.PState("enda")
    #    enda.action([EOS,],self.Expr_End)                    #   EOS (Hurray!) done
    #    enda.error(self.ACT_ExpectedEnd)                     # E ??? ($#@$!)
    #    self.state(enda)


    # Lexcial Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: MacroScopeExprA
    # Result: asmbase.ASMExprArith
    # See MacroCSLexer.init_default() method
    #
    # The macro arithmentic expression does not include any enclosing parenthesis
    # required by the macro statement.  See AGO as an example.

    def Arith(self):

        initd=fsmparser.PState("initd")
        initd.action(self.term,self.Expr_Term)               #   None  term   termd
        initd.action([SATTR,],self.Expr_Start_S)             #   None  sym    >
        initd.action([AOPER,],self.Expr_Start_O)             #   None  oper   unaryd/E
        initd.action([LPAREN,],self.Expr_Start_L)            #   None  (      lparend
        initd.action(self.boper,self.ACT_Expected_Aoper)     # E None  boper
        initd.action([QUOTE,],self.ACT_Expected_LP_Term)     # E None  '
        initd.action([RPAREN,],self.ACT_Expected_LP_Term)    # E None  )
        initd.action([COMMA,],self.ACT_Expected_LP_Term)     # E None  ,
        initd.action([EOS,],self.ACT_Expected_LP_Term)       # E None  EOS
        initd.error(self.ACT_Expected_LP_Term)               # E None  ??
        self.state(initd)

        unaryd=fsmparser.PState("unaryd")
        unaryd.action(self.term,self.Expr_Term)              #   unary term   termd
        unaryd.action([SATTR,],self.Expr_Unary_S)            #   unary sym    >sym
        unaryd.action([LPAREN,],self.Expr_Unary_L)           #   unary (      lparend
        unaryd.action([AOPER,],self.ACT_Expected_LP_Term)    # E unary aoper
        unaryd.action(self.boper,self.ACT_Expected_Aoper)    # E None  boper
        unaryd.action([RPAREN,],self.ACT_Expected_LP_Term)   # E unary )
        unaryd.action([COMMA,],self.ACT_Expected_LP_Term)    # E unary ,
        unaryd.action([EOS,],self.ACT_Expected_LP_Term)      # E unary EOS
        self.state(unaryd)

        binaryd=fsmparser.PState("binaryd")
        binaryd.action(self.term,self.Expr_Term)             #   binary term  termd
        binaryd.action([SATTR,],self.Expr_Binary_S)          #   binary sym   >
        binaryd.action([AOPER,],self.Expr_Binary_O)          #   binary oper unaryd/termd
        binaryd.action([LPAREN,],self.Expr_Binary_L)         #   binary (
        binaryd.action(self.boper,self.ACT_Expected_Aoper)   # E binary boper
        binaryd.action([RPAREN,],self.ACT_Expected_LP_Term)  # E binary )
        binaryd.action([COMMA,],self.ACT_Expected_RP_Oper)   # E binary ,
        binaryd.action([EOS,],self.ACT_Expected_LP_Term)     # E binary EOS
        self.state(binaryd)

        lparend=fsmparser.PState("lparend")
        lparend.action(self.term,self.Expr_Term)             #   ( term     termd
        lparend.action([SATTR,],self.Expr_LParen_S)          #   ( sym      >
        lparend.action([AOPER,],self.Expr_LParen_O)          #   ( oper unarya/termd/E
        lparend.action([LPAREN,],self.Expr_LParen_L)         #   ( (        lparend
        lparend.action(self.boper,self.ACT_Expected_Aoper)   # E ( boper
        lparend.action([RPAREN,],self.ACT_Expected_LP_Term)  # E ( )
        lparend.action([COMMA,],self.ACT_Expected_LP_Term)   # E ( ,
        lparend.action([EOS,],self.ACT_Expected_LP_Term)     # E ( EOS
        self.state(lparend)

        rparend=fsmparser.PState("rparend")
        rparend.action([AOPER,],self.Expr_RParen_O)          #   ) aoper  binaryd/E
        rparend.action([RPAREN,],self.Exor_RParen_R)         #   ) )      rparend/E
        rparend.action([LPAREN,],self.ACT_Expected_RP_Oper)  # E ) (
        rparend.action(self.boper,self.ACT_Expected_Aoper)   # E ) boper
        rparend.action(self.term,self.ACT_Expected_RP_Oper)  # E ) term
        rparend.action([SATTR,],self.ACT_Expected_RP_Oper)   # E ) sym
        rparend.error(self.Expr_Follow)                      #   ) follow  done/E
        self.state(rparend)

        termd=fsmparser.PState("termd")
        termd.action([AOPER,],self.Expr_Term_O)              #   term aoper binaryd/E
        termd.action([RPAREN,],self.Expr_Term_R)             #   term )   rparend/end
        termd.action([EOS,],self.Expr_Term_E)                #   term EOS   done/E    
        termd.action(self.boper,self.ACT_Expected_Aoper)     # E term boper
        termd.action(self.term,self.ACT_Expected_RP_Oper)    # E term term
        termd.action([SATTR,],self.ACT_Expected_RP_Oper)     # E term sym
        termd.action([LPAREN,],self.ACT_Expected_RP_Oper)    # E term (
        termd.error(self.Expr_Follow)                        #   term follow  done/E
        self.state(termd)

        # This state ensures nothing follows the final secondary expression's
        # terminating right parenthesis
        endd=fsmparser.PState("endd")
        endd.action([EOS,],self.Expr_End)                    #   EOS (Hurray!) done
        endd.error(self.ACT_ExpectedEnd)                     # E ??? ($#@$!)
        self.state(endd)

    def Arith_Call(self,ret,token=None,follow=[],trace=False):
        assert isinstance(ret,MPControl),\
             "%s 'ret' argument must be a MPControl object: %s" \
                 % (assembler.eloc(self,"Arith_Call",module=this_module),ret)
        gs=self.scope()
        new=MacroScopeExprA(gs.lopnd)
        new.follow=follow
        newmp=MPControl("initd",pctx="init")
        return self.enter_scope(gs,ret,new,newmp,stack=token,trace=trace)


  #                 +-------------------------+
  #                 |                         |
  #                 |    BINARY EXPRESSION    |
  #                 |                         |
  #                 +-------------------------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: current scope
    # See MacroCSLexer.init_default() method

    #def Binary_Old(self):

    #    initb=fsmparser.PState("initb")
    #    initb.action(self.term,self.Expr_Term)               #   None  term   termb
    #    initb.action([QUOTE,],self.Expr_Start_Ch)            #   None  chr    >
    #    initb.action([SATTR,],self.Expr_Start_S)             #   None  sym    >
    #    initb.action(self.boper,self.Expr_Start_O)           #   None  boper  unaryb/E
    #    initb.action([AOPER,],self.Expr_Start_O)             #   None  aoper  unaryb/E
    #    initb.action([LPAREN,],self.Expr_Start_L)            #   None  (      lparenb
    #    initb.action([RPAREN,],self.ACT_Expected_LP_Term)    # E None  )
    #    initb.action([COMMA,],self.ACT_Expected_LP_Term)     # E None  ,
    #    initb.action([EOS,],self.ACT_Expected_LP_Term)       # E None  EOS
    #    initb.error(self.ACT_Expected_LP_Term)               # E None  ??
    #    self.state(initb)

    #    unaryb=fsmparser.PState("unaryb")
    #    unaryb.action(self.term,self.Expr_Term)              #   unary term   term
    #    unaryb.action([SATTR,],self.Expr_Unary_S)            #   unary sym    >
    #    unaryb.action([LPAREN,],self.Expr_Unary_L)           #   unary (      lparen
    #    unaryb.action([AOPER,],self.ACT_Expected_LP_Term)    # E None  aoper
    #    unaryb.action(self.boper,self.ACT_Expected_LP_Term)  # E unary boper
    #    unaryb.action([RPAREN,],self.ACT_Expected_LP_Term)   # E unary )
    #    unaryb.action([COMMA,],self.ACT_Expected_LP_Term)    # E unary ,
    #    unaryb.action([EOS,],self.ACT_Expected_LP_Term)      # E unary EOS
    #    unaryb.error(self.ACT_Expected_LP_Term)              # E unary  ??
    #    self.state(unaryb)

    #    binaryb=fsmparser.PState("binaryb")
    #    binaryb.action(self.term,self.Expr_Term)             #   binary term  term
    #    binaryb.action([QUOTE,],self.Expr_Start_Ch)          #   binary chr   >
    #    binaryb.action([SATTR,],self.Expr_Binary_S)          #   binary sym   >
    #    binaryb.action(self.boper,self.Expr_Binary_O)        #   binary boper unary/term
    #    binaryb.action([AOPER,],self.Expr_Binary_O)          #   binary aoper unary/term
    #    binaryb.action([LPAREN,],self.Expr_Binary_L)         #   binary (
    #    binaryb.action([RPAREN,],self.ACT_Expected_LP_Term)  # E binary )
    #    binaryb.action([COMMA,],self.ACT_Expected_RP_Oper)   # E binary ,
    #    binaryb.action([EOS,],self.ACT_Expected_LP_Term)     # E binary EOS
    #    self.state(binaryb)

    #    lparenb=fsmparser.PState("lparenb")
    #    lparenb.action(self.term,self.Expr_Term)             #   ( term     term
    #    lparenb.action([QUOTE,],self.Expr_Start_Ch)          #   ( chr      >
    #    lparenb.action([SATTR,],self.Expr_LParen_S)          #   ( sym      >
    #    lparenb.action(self.boper,self.Expr_LParen_O)        #   ( boper  unary/term/E
    #    lparenb.action([AOPER,],self.Expr_LParen_O)          #   ( aoper  unary/term/E
    #    lparenb.action([LPAREN,],self.Expr_LParen_L)         #   ( (        lparen
    #    lparenb.action([RPAREN,],self.ACT_Expected_LP_Term)  # E ( )
    #    lparenb.action([COMMA,],self.ACT_Expected_LP_Term)   # E ( ,
    #    lparenb.action([EOS,],self.ACT_Expected_LP_Term)     # E ( EOS
    #    self.state(lparenb)

    #    rparenb=fsmparser.PState("rparenb")
    #    rparenb.action(self.boper,self.Expr_RParen_O)        #   ) boper  binaryb/E
    #    rparenb.action([AOPER,],self.Expr_RParen_O)          #   ) aoper  binaryb/E
    #    rparenb.action([LPAREN,],self.Expr_RParen_L)         #   ) (       initb/E
    #    rparenb.action([RPAREN,],self.Expr_RParen_R)         #   ) )      rparenb/end
    #    rparenb.action([COMMA,],self.Expr_RParen_C)          #   ) ,       initb/E
    #    rparenb.action([EOS,],self.Expr_RParen_E)            #   ) EOS     done/E
    #    rparenb.action(self.term,self.ACT_Expected_RP_Oper)  # E ) term
    #    rparenb.action([SATTR,],self.ACT_Expected_RP_Oper)   # E ) sym
    #    rparenb.error(self.Expr_Follow)                      #   ) follow  done/E
    #    self.state(rparenb)

    #    termb=fsmparser.PState("termb")
    #    termb.action(self.boper,self.Expr_Term_O)            #   term boper binaryb/E
    #    termb.action([AOPER,],self.Expr_Term_O)              #   term aoper binaryb/E
    #    termb.action([LPAREN,],self.Expr_Term_L)             #   term (    initb/E
    #    termb.action([RPAREN,],self.Expr_Term_R)             #   term )   rparenb/end
    #    termb.action([COMMA,],self.Expr_Term_C)              #   term ,    initb/E
    #    termb.action([EOS,],self.Expr_Term_E)                #   term EOS   done/E
    #    termb.action(self.term,self.ACT_Expected_RP_Oper)    # E term term
    #    termb.action([SATTR,],self.ACT_Expected_RP_Oper)     # E term sym
    #    termb.error(self.Expr_Follow)                        #   term follow  done/E
    #    self.state(termb)

        # This state ensures nothing follows the final secondary expression's
        # terminating right parenthesis
    #    endb=fsmparser.PState("endb")
    #    endb.action([EOS,],self.Expr_End)                    #   EOS (Hurray!) done
    #    endb.error(self.ACT_ExpectedEnd)                     # E ??? ($#@$!)
    #    self.state(endb)
        
    def Binary(self):

        inite=fsmparser.PState("inite")
        inite.action(self.term,self.Expr_Term)               #   None  term   terme
        inite.action([QUOTE,],self.Expr_Start_Ch)            #   None  chr    >
        inite.action([SATTR,],self.Expr_Start_S)             #   None  sym    >
        inite.action(self.boper,self.Expr_Start_O)           #   None  boper  unarye/E
        inite.action([AOPER,],self.Expr_Start_O)             #   None  aoper  unarye/E
        inite.action([LPAREN,],self.Expr_Start_L)            #   None  (      lparene
        inite.action([RPAREN,],self.ACT_Expected_LP_Term)    # E None  )
        inite.action([COMMA,],self.ACT_Expected_LP_Term)     # E None  ,
        inite.action([EOS,],self.ACT_Expected_LP_Term)       # E None  EOS
        inite.error(self.ACT_Expected_LP_Term)               # E None  ??
        self.state(inite)

        unarye=fsmparser.PState("unarye")
        unarye.action(self.term,self.Expr_Term)              #   unary term   term
        unarye.action([SATTR,],self.Expr_Unary_S)            #   unary sym    >
        unarye.action([LPAREN,],self.Expr_Unary_L)           #   unary (      lparen
        unarye.action([AOPER,],self.ACT_Expected_LP_Term)    # E None  aoper
        unarye.action(self.boper,self.ACT_Expected_LP_Term)  # E unary boper
        unarye.action([RPAREN,],self.ACT_Expected_LP_Term)   # E unary )
        unarye.action([COMMA,],self.ACT_Expected_LP_Term)    # E unary ,
        unarye.action([EOS,],self.ACT_Expected_LP_Term)      # E unary EOS
        unarye.error(self.ACT_Expected_LP_Term)              # E unary  ??
        self.state(unarye)

        binarye=fsmparser.PState("binarye")
        binarye.action(self.term,self.Expr_Term)             #   binary term  term
        binarye.action([QUOTE,],self.Expr_Start_Ch)          #   binary chr   >
        binarye.action([SATTR,],self.Expr_Binary_S)          #   binary sym   >
        binarye.action(self.boper,self.Expr_Binary_O)        #   binary boper unary/term
        binarye.action([AOPER,],self.Expr_Binary_O)          #   binary aoper unary/term
        binarye.action([LPAREN,],self.Expr_Binary_L)         #   binary (
        binarye.action([RPAREN,],self.ACT_Expected_LP_Term)  # E binary )
        binarye.action([COMMA,],self.ACT_Expected_RP_Oper)   # E binary ,
        binarye.action([EOS,],self.ACT_Expected_LP_Term)     # E binary EOS
        self.state(binarye)

        lparene=fsmparser.PState("lparene")
        lparene.action(self.term,self.Expr_Term)             #   ( term     term
        lparene.action([QUOTE,],self.Expr_Start_Ch)          #   ( chr      >
        lparene.action([SATTR,],self.Expr_LParen_S)          #   ( sym      >
        lparene.action(self.boper,self.Expr_LParen_O)        #   ( boper  unary/term/E
        lparene.action([AOPER,],self.Expr_LParen_O)          #   ( aoper  unary/term/E
        lparene.action([LPAREN,],self.Expr_LParen_L)         #   ( (        lparen
        lparene.action([RPAREN,],self.ACT_Expected_LP_Term)  # E ( )
        lparene.action([COMMA,],self.ACT_Expected_LP_Term)   # E ( ,
        lparene.action([EOS,],self.ACT_Expected_LP_Term)     # E ( EOS
        self.state(lparene)

        rparene=fsmparser.PState("rparene")
        rparene.action(self.boper,self.Expr_RParen_O)        #   ) boper  binarye/E
        rparene.action([AOPER,],self.Expr_RParen_O)          #   ) aoper  binarye/E
        rparene.action([RPAREN,],self.Exor_RParen_R)         #   ) )      rparene/E
        rparene.action(self.term,self.ACT_Expected_RP_Oper)  # E ) term
        rparene.action([SATTR,],self.ACT_Expected_RP_Oper)   # E ) sym
        rparene.action([LPAREN,],self.ACT_Expected_RP_Oper)  # E ) (
        rparene.error(self.Expr_Follow)                      #   ) follow  done/E
        self.state(rparene)

        terme=fsmparser.PState("terme")
        terme.action(self.boper,self.Expr_Term_O)            #   term boper binarye/E
        terme.action([AOPER,],self.Expr_Term_O)              #   term aoper binarye/E
        terme.action([RPAREN,],self.Expr_Term_R)             #   term )   rparene/end
        terme.action([EOS,],self.Expr_Term_E)                #   term EOS   done/E
        terme.action(self.term,self.ACT_Expected_RP_Oper)    # E term term
        terme.action([SATTR,],self.ACT_Expected_RP_Oper)     # E term sym
        terme.action([LPAREN,],self.ACT_Expected_RP_Oper)    # E term (
        terme.error(self.Expr_Follow)                        #   term follow  done/E
        self.state(terme)

        # This state ensures nothing follows the final secondary expression's
        # terminating right parenthesis
        ende=fsmparser.PState("ende")
        ende.action([EOS,],self.Expr_End)                    #   EOS (Hurray!) done
        ende.error(self.ACT_ExpectedEnd)                     # E ??? ($#@$!)
        self.state(ende)

    def Binary_Call(self,ret,token=None,follow=[],trace=False):
        assert isinstance(ret,MPControl),\
             "%s 'ret' argument must be a MPControl object: %s" \
                 % (assembler.eloc(self,"Binary_Call",module=this_module),ret)
        gs=self.scope()
        new=MacroScopeExprB(gs.lopnd)
        new.follow=follow
        newmp=MPControl("inite",pctx="init")
        return self.enter_scope(gs,ret,new,newmp,stack=token,trace=trace)


  #                 +-----------------------------------+
  #                 |                                   |
  #                 |    OPERATOR PRECEDENCE ACTIONS    |
  #                 |                                   |
  #                 +-----------------------------------+
  
    # These actions are shared with both the arithmetic and binary (logical) 
    # expression contexts.  The recognition of which actions should be taken
    # is the responsibility of the finite-state machine state definitions.
    # However, the actions taken are the same regardless of the nature of the
    # underlying type of operator precedence expression is being recognized.
    # The differentiation between which state is returned is based upon the
    # setting of the current scope's suffix attribute.  Where a particular operator
    # needs to distinguish between an infix or unary operator, or in one case
    # a term, the lexical token and processing figures that out.
    #
    # The method names incorporate the previously identified token and the 
    # currently encountered token.  The actions are sensitive to whether a primary
    # or secondary expression is being recognized, whether parentheses are balanced.

    #
    # Actions following an infix operator
    #

    def Expr_Binary_S(self,value,state,trace=False):
        # binary cterm
        gs=self.scope()
        ret=MPControl("term%s" % gs.suffix,pctx="init")
        return self.Sym_Call(ret,token=value,trace=trace)

    def Expr_Binary_L(self,value,state,trace=False):
        # binary (
        gs=self.scope()
        gs.lparen(value)
        return "lparen%s" % gs.suffix

    def Expr_Binary_O(self,value,state,trace=False):
        gs=self.scope()

        # binary unary
        if value.unary:
            # If operator is a unary
            gs.token(value)
            return "unary%s" % gs.suffix

        # binary loc
        elif value.string == "*":
            # Check for token string of "*" to detect current location counter
            value.current()     # Update token to reflect location counter symbol
            gs.token(value)
            return "term%s" % gs.suffix   # Treat the location counter as a term

        # binary binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    def Expr_Common_Term(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "term%s" % gs.suffix
        
    #
    # Action when valid end of operand encountered
    #
    
    def Expr_End(self,value,state,trace=False):
        state.atend()
        
    #
    # Action to detect valid follow tokens indicating valid end of expression
    #

    def Expr_Follow(self,value,state,trace=False):
        gs=self.scope()
        if not gs.balanced_parens():
            self.ACT_Expected_RP_Oper(value,state,trace=trace)

        if gs.isFollow(value,trace=trace):
            #return self.Expr_Return(token=value,trace=trace)
            return self.Expr_Return(token=value,trace=trace)

        # Input token not legitimate end of expression
        self.ACT_Expected_EndExpr(value,state,trace=trace)

    #
    # Actions following a left parenthesis
    #

    def Expr_LParen_S(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("term%s" % gs.suffix,pctx="init")
        return self.Sym_Call(ret,token=value,trace=trace)

    def Expr_LParen_L(self,value,state,trace=False):
        # ( (
        gs=self.scope()
        gs.lparen(value)
        return "lparen%s" % gs.suffix

    def Expr_LParen_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags
        if value.unary:
            # ( unary
            gs=self.scope()
            gs.token(value)
            return "unary%s" % gs.suffix

        elif value.string=="*":
            # ( current-location-counter
            value.current()
            gs.token(value)
            return "term%s" % gs.suffix

        # ( binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    #def Expr_Return(self,token=None,trace=False):
    #    gs=self.scope()         # Get the current scope (the complex term's scope)
    #    if __debug__:
    #        if trace:
    #            cls_str=assembler.eloc(self,"Expr_Return",module=this_module)
    #            print("%s scope: %s" % (cls_str,gs.__class__.__name__))
    #            print("%s gs.arith_new:  %s" % (cls_str,gs.arith_new))
    #            print("%s gs.binary_new: %s" % (cls_str,gs.binary_new))
            
    #    if gs.arith_new or gs.binary_new:
    #        return self.Expr_Return_New(token=token,trace=trace)
    #    if __debug__:
    #        if trace:
    #            print("%s %r.expression_end(): primary:%s" \
    #                % (assembler.eloc(self,"Expr_Return",module=this_module),\
    #                    gs,gs._primary))
    #    gs.expression_end()     # Finish the pending expression (primary/secondary)

    #    if __debug__:
    #        if trace:
                #print("%s result: %s" \
                #    % (assembler.eloc(self,"Expr_Return",module=this_module),\
                #       result.display(string=True)))
    #            print("%s gs %s next_state %s next_pctx %s" \
    #                % (assembler.eloc(self,"Expr_Return",module=this_module),\
    #                    gs.__class__.__name__,gs.next_state,gs.next_pctx))

    #    gs.suffix=None
    #    gs.follow=[]
    #    self.context(gs.next_pctx,trace=trace)
    #    gs.next_pctx=None
    #    if token:
    #        self.lex_retry(token,trace=trace)
    #    next=gs.next_state
    #    assert next is not None,"%s %s return FSM state is None" \
    #        % (assembler.eloc(self,"Expr_Return",module=this_module),\
    #            gs.__class__.__name__)
    #    gs.next_state=None
    #    return next

    def Expr_Return(self,token=None,trace=False):
        gs=self.scope()
        if __debug__:
            if trace:
                print("%s leaving scope: %s" \
                    % (assembler.eloc(self,"Expr_Return",module=this_module),\
                        gs))

        gs.build_expression()
        return self.leave_scope(result=gs.result(),stack=token,trace=trace)


    #
    # Actions following a right parenthesis
    #

    # This action goes away when all expressions use the expression call interface.
    # This is because the calling scope parses the comma by supplying it as a 
    # follow TID class.
    #def Expr_RParen_C_Old(self,value,state,trace=False):
        # ) ,
    #    gs=self.scope()
    #    if gs._primary:
    #        self.ACT_Expected_RP_Oper(value,state,trace=trace)

        # The comma marks the end of a secondary expression
    #    if gs.balanced_parens():
    #        print("%s %r.expression_end(): primary:%s" \
    #            % (assembler.eloc(self,"Expr_RParen_C",module=this_module),\
    #                gs,gs._primary))
    #        gs.expression_end()
    #        return "init%s" % gs.suffix

        # Secondary expression has unbalanced parenthesis
    #    self.ACT_Unbalaced(value,state,trace=trace)

    #def Expr_RParen_E_Old(self,value,state,trace=False):
        # ) EOS
    #    gs=self.scope()

    #    if gs._primary:
    #        if gs.balanced_parens:
    #            if __debug__:
    #                if trace:
    #                    print("%s %r.expression_end(): primary:%s" \
    #                        % (assembler.eloc(self,"Expr_RParen_E",\
    #                            module=this_module),gs,gs._primary))
    #            gs.expression_end()
    #            if gs.cterm:
    #                return self.Expr_Return(token=value,trace=trace)
    #            state.atend()
    #            return
    #        else:
    #            self.ACT_Unbalaced_Primary(value,state,trace=trace)

    #    if gs.balanced_parens:
    #        if __debug__:
    #            if trace:
    #                print("%s %r.expression_end(): primary:%s" \
    #                    % (assembler.eloc(self,"Expr_RParen_E",\
    #                            module=this_module),gs,gs._primary))
    #        return self.Expr_Return(token=value,trace=trace)

        # Not balanced parenthesis, so an error.
    #    self.ACT_Expected_RP_Oper(value,state,trace=trace)

    # This is always an error!!
    #def Expr_RParen_L(self,value,state,trace=False):
        # ) (
    #    gs=self.scope()

    #    if gs._primary:
            # See if primary expression done and now starting secondaries
    #        if gs.balanced_parens():
    #            print("%s %r.expression_end(): primary:%s" \
    #                % (assembler.eloc(self,"Expr_RParen_L",module=this_module),\
    #                    gs,gs._primary))
    #            gs.expression_end()
    #            return "init%s" % gs.suffix

    #    self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def Expr_RParen_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags

        # ) binary
        if value.binary:
            gs=self.scope()
            gs.token(value)
            return "binary%s" % gs.suffix

        # ) unary
        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    #def Expr_RParen_R(self,value,state,trace=False):
        # ) )
    #    gs=self.scope()

    #    if gs._primary:
    #        gs.rparen(value)
    #        return "rparen%s" % gs.suffix

        # For secondary expression, this might be the ending right parenthesis
        # This goes away for the expression call interface.  The expression call
        # interface does not differentiate between primary or secondary expressions.
        # That is the responsibility of the calling scope
    #    if gs.balanced_parens():
    #        if __debug__:
    #            if trace:
    #                print("%s %r.expression_end(): primary:%s" \
    #                    % (assembler.eloc(self,"Expr_RParen_R",module=this_module),\
    #                        gs,gs._primary))
    #        gs.expression_end()
    #        if gs.cterm:
    #            return self.Expr_Return(token=value)
                #return self.ACT_Cterm_End(state,value,trace=trace)
    #        return "end%s" % gs.suffix
    #    else:
    #        gs.rparen(value)
    #        return "rparen%s" % gs.suffix
    #    self.ACT_Unbalaced(value,state,trace=trace)

    def Exor_RParen_R(self,value,state,trace=False):
        gs=self.scope()
        
        if not gs.balanced_parens():
            gs.rparen(value)
            return "rparen%s" % gs.suffix
            
        self.ACT_Unbalaced(value,state,trace=trace)
        

    #
    # Actions at start of expression
    #

    def Expr_Start_Ch(self,value,state,trace=False):
        # ' initicating start of a character expression
        gs=self.scope()
        # Treat a character expression as a 'term' so enter the state 
        # following a term when we come back
        ret_state="term%s" % gs.suffix
        ret=MPControl(ret_state,pctx="init")
        return self.Chr_Call(ret)

    def Expr_Start_S(self,value,state,trace=False):
        # &SYM or X'&SYM
        gs=self.scope()
        ret=MPControl("term%s" % gs.suffix,pctx="init")
        return self.Sym_Call(ret,token=value,trace=trace)

    def Expr_Start_L(self,value,state,trace=False):
        # (
        gs=self.scope()
        gs.lparen(value)
        return "lparen%s" % gs.suffix

    def Expr_Start_O(self,value,state,trace=False):
        gs=self.scope()
        value.syntax()     # Set operator syntax flags

        # unary
        if value.unary:
            gs.token(value)
            return "unary%s" % gs.suffix

        # Check for current location counter at start of expression
        elif self.string=="*":
            # Check for token string of "*" to detect current location counter
            value.current()     # Update token to reflect location counter symbol
            gs.token(value)
            return "term%s" % gs.suffix   # Treat the location counter as a term

        # binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    #
    # Action upon encountering a term
    #
    
    def Expr_Term(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "term%s" % gs.suffix

    #
    # Actions following a term
    #

    # This action goes away when all expressions use the calling scope interface.
    # The comma signaling the next secondary expression is handled by the calling
    # scope not the expression call interface.
    #def Expr_Term_C(self,value,state,trace=False):
        # term ,
    #    gs=self.scope()

    #    if gs._primary:
    #        self.ACT_Expected_LP_Term(value,state,trace=trace)

        # For secondary is end of the expresion
    #    if gs.balanced_parens():
    #        if __debug__:
    #            if trace:
    #                print("%s %r.expression_end(): primary:%s" \
    #                    % (assembler.eloc(self,"Expr_Term_C",module=this_module),\
    #                        gs,gs._primary))
    #        gs.expression_end()
    #        return "init%s" % gs.suffix
    #    self.ACT_Unbalaced(value,state,trace=trace)

    # This action is replace by Expr_Term_E_New when all expressions use the
    # expression call interface.
    #def Expr_Term_E(self,value,state,trace=False):
        # term EOS
    #    gs=self.scope()
        
    #    if gs.arith_new or gs.binary_new:
    #        return self.Expr_Term_E_New(value,state,trace=trace)

    #    if gs._primary:
    #        if gs.balanced_parens():
    #            if __debug__:
    #                if trace:
    #                    print("%s %r.expression_end(): primary:%s" \
    #                        % (assembler.eloc(self,"Expr_Term_E",module=this_module),\
    #                            gs,gs._primary))
    #            gs.expression_end()
    #            state.atend()
    #            return
    #        else:
    #            self.ACT_Unbalaced_Primary(value,state,trace=trace)

        # For secondary missing final right parenthesis
    #    self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def Expr_Term_E(self,value,state,trace=False):
        # term EOS
        gs=self.scope()
        
        if gs.balanced_parens():
            return self.Expr_Return(token=value,trace=trace)
        else:
            self.ACT_Unbalaced_Primary(value,state,trace=trace)

    #def Expr_Term_L(self,value,state,trace=False):
        # term (
    #    gs=self.scope()


        # This goes away when all expressions use the expression call interface.
        # This is because primary vs. secondary expressions are handled by the 
        # calling scope.  So the 'term (' sequence is always an error and never
        # _here_ signals the end of the primary expression.
    #    if gs._primary:
    #        if gs.balanced_parens():
                # End of primary expression
    #            if __debug__:
    #                if trace:
    #                    print("%s %r.expression_end(): primary:%s" \
    #                        % (assembler.eloc(self,"Expr_Term_L",module=this_module),\
    #                            gs,gs._primary))
    #            gs.expression_end()
    #            # Start of secondary expression
    #            return "init%s" % gs.suffix

    #    self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def Expr_Term_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags

        # term binary
        if value.binary:
            gs=self.scope()
            gs.token(value)
            return "binary%s" % gs.suffix

        # term unary
        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    # This action is replaced by Expr_Term_R_New when all expressions use the 
    # expression call interface.
    #def Expr_Term_R(self,value,state,trace=False):
        # term )
    #    gs=self.scope()
        
    #    if __debug__:
    #        if trace:
    #            cls_str=assembler.eloc(self,"Expr_Term_R",module=this_module)
    #            print("%s scope: %s" % (cls_str,gs.__class__.__name__))
    #            print("%s gs.arith_new:  %s" % (cls_str,gs.arith_new))
    #            print("%s gs.binary_new: %s" % (cls_str,gs.binary_new))
            
    #    if gs.arith_new or gs.binary_new:
    #        return self.Expr_Term_R_New(value,state,trace=trace)

    #    if gs._primary:
    #        gs.rparen(value)
    #        return "rparen%s" % gs.suffix

        # For secondary need to see if end of secondary expressions
    #    if gs.balanced_parens():
    #        if gs.cterm:
                #return self.ACT_Cterm_End(value,state,trace=trace)
    #            return self.Expr_Return(value,trace=trace)
    #        else:
    #            if __debug__:
    #                if trace:
    #                    print("%s %r.expression_end(): primary:%s" \
    #                        % (assembler.eloc(self,"Expr_Term_R",module=this_module),\
    #                            gs,gs._primary))
    #            gs.expression_end()
    #            if gs.cterm:
    #                self.Expr_Return(token=value)
    #        return "end%s" % gs.suffix

    #    gs.rparen(value)
    #    return "rparen%s" % gs.suffix

    def Expr_Term_R(self,value,state,trace=False):
        # term )
        gs=self.scope()
        if gs.balanced_parens() and gs.isFollow(value,trace=trace):
            return self.Expr_Return(token=value,trace=trace)

        gs.rparen(value)
        return "rparen%s" % gs.suffix


    #
    # Actions following a unary operator
    #

    def Expr_Unary_S(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("term%s" % gs.suffix,pctx="init")
        return self.Sym_Call(ret,token=value,trace=trace)

    def Expr_Unary_L(self,value,state,trace=False):
        # unary (
        gs=self.scope()
        gs.lparen(value)
        return "lparen%s" % gs.suffix


  #                 +----------------------------+
  #                 |                            |
  #                 |    CHARACTER EXPRESSION    |
  #                 |                            |
  #                 +----------------------------+

    # Context: cexpr - tokens: DBLQUOTE, QUOTE, AMP, SYMBOL, SYM, CHRS, LPAREN
    # Scope: CharacterExpr(cterm=True)
    # See MacroCSLexer.init_cexpr() method
    
    # Parses:
    #   
    #   Case 1: Primary Expression only.  The initiating single quote is consumed
    #           by the previous context.  Following the terminating single quote
    #           the next token determines whether this is really Case 2.  If it is
    #           not a left parenthesis, it must be stacked to allow the previous
    #           context to process it within its set of recognized tokens.
    #
    #        ' &SYM. &SYM &SYM( ''  &&  '?
    #         \____________ ____________/^             
    #                      v             +-- stacked for previous context
    #               Primary Expression
    #
    #   Case 2: Primary and Secondary Expressions.  As with Case 1, the initiating
    #           single quote is consumed by the previous context.
    #
    #
    #        ' &SYM. &SYM &SYM( ''  &&  '(starting-expr,length_expr)
    #         \____________ ____________/ \____________ __________/
    #                      v                           v
    #               Primary Expression        Secondary Expresions
    #

    def Chr(self):

        initc=fsmparser.PState("initc")
        initc.action([SYMBOL],self.Chr_Sym_dot)              #   ...  &SYM.  initc
        initc.action([SYM],self.Chr_Sym)                     #   ...  &SYM   >sym
        initc.action([LPAREN,],self.Chr_Chrs)                #   ...  (      initc
        initc.action([CHRS],self.Chr_Chrs)                   #   ...  xxxx   initc
        initc.action([DBLQUOTE],self.Chr_Chrs)               #   ...  ''     initc
        initc.action([AMP,],self.Chr_Chrs)                   #   ...  &&     initc
        initc.action([QUOTE],self.Chr_End)                   #   ...  '      done
        initc.error(self.Chr_Expected_Chrs)                  # E      other
        self.state(initc)

        # Look for End-of-String after final right parenthesis
        csube=fsmparser.PState("csube")
        csube.action([EOS,],self.Chr_End)                    #   )    EOS     done!
        csube.error(self.ACT_ExpectedEnd)                    # E ???
        self.state(csube)

        # Return state after parsing sublist length expression
        csubl=fsmparser.PState("csubl")
        csubl.action([RPAREN,],self.Chr_Subs_End)            #  arith> )     csube
        self.state(csubl)

        # Return state after parsing starting position expression
        csubs=fsmparser.PState("csubs")
        csubs.action([COMMA,],self.Chr_Subs_Length)          #   arith ,    >arith
        csubs.error(self.ACT_Expected_Comma)                 # E ???
        self.state(csubs)

        # Symbol within possible subscripts found within string
        # Determining whether subscripts are present
        csym=fsmparser.PState("csym")
        csym.action([LPAREN,],self.Chr_Subs_Start)           #   &SYM  (     >
        csym.error(self.Chr_Sym_End)                         #   &SYM  other initr
        self.state(csym)

    def Chr_Call(self,ret,token=None,trace=False):
        if __debug__:
            if trace:
                print("%s ret: %s token:%s trace:%s" \
                    % (assembler.eloc(self,"Chr_Call",module=this_module),\
                        ret,token,trace))
        assert isinstance(ret,MPControl),\
            "%s 'ret' argument must be a MPControl object: %s" \
                % (assembler.eloc(self,"Chr_Call",module=this_module),ret)
        assert token is None,\
            "%s 'token' argument must be None: %s" \
                % (assembler.eloc(self,"Chr_Call",module=this_module),token)

        gs=self.scope()
        new=CharacterExpr(gs.lopnd)
        newmp=MPControl("initc",pctx="cexpr")
        return self.enter_scope(gs,ret,new,newmp,stack=None,trace=trace)

    def Chr_Chrs(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "initc"

    def Chr_End(self,value,state,trace=False):
        gs=self.scope()
        if __debug__:
            if trace:
                print("%s %r.expression_end(): primary:%s" \
                    % (assembler.eloc(self,"Rep_End",module=this_module),\
                        gs,gs._primary))
        gs.expression_end()
        return "csym"    # See if we have a substring

    # Sublist detected with character string
    #def Chr_Subs(self,value,state,trace=False):
    #    gs=self.scope()
        # Because the replacement scope has already been pushed, don't need to use
        # enter_scope(), but do need to set how to get back to the rep context
        # we are about to leave

        # Enter context for sublist arithmetic expressions
    #    return self.Arith_Call(MPControl("csym",pctx="cexpr"))
        
        # When the RPAREN is detected at the end of the sublist, we return to 
        # these states and context via a leave_scope()

    def Chr_Subs_End(value,state,trace=False):
        return "csube"

    def Chr_Subs_Length(value,state,trace=False):
        ret=MPControl("csubl",pctx="cexpr")
        return self.Arith_Call(ret,token=None,follow=[RPAREN,],trace=trace)

    def Chr_Subs_Start(value,state,trace=False):
        ret=MPControl("csubs",pctx="cexpr")
        return self.Arith_Call(ret,token=None,follow=[COMMA,],trace=trace)

    # A replacement symbolic reference started (without concatenation)
    #   Scope:   CharacterExpr
    #   Context: rep
    def Chr_Sym(self,value,state,trace=False):
        gs=self.scope()
        
        ret=MPControl("initc",pctx="cexpr")
        return self.Sym_Call(ret,token=value,trace=trace)
        
        # All of this needs to be changed to using the scope call interface.  The
        # Symbolic Reference states need to handle all of this
        #
        # When we return to the CharcterExpr scope, this is its state.
        #gs.return_state("initc","cexpr")  # When we 
        #new=SymbolicReference(gs.lopnd)
        #new.init(stmt=gs._stmt)
        #new.token(value)
        #if __debug__:
        #    if trace:
        #        print("%s %r.expression_end(): primary:%s" \
        #            % (assembler.eloc(self,"Rep_Sym",module=this_module),\
        #                gs,gs._primary))
        #new.expression_end()   # Complete the primary expression (the symbol name)
        #self.push_scope(new)
        #return "csym"

    def Chr_Sym_dot(self,value,state,trace=False):
        gs=self.scope()
        symref=SymbolRef()
        symref.primary(value)
        self.token(symref)
        return "initc"

    # Complete a symbolic variable reference without subscripts:
    #   Scope: SymbolicReference
    #   Context: rep
    def Chr_Sym_End(self,value,state,trace=False):
        #gs=self.scope()
        #result=gs.result()      # Get the result object (SymbolRef)
        #assert isinstance(result,SymbolRef),\
        #    "%s expected SymbolRef object from current scope (%s): %s" \
        #        % (assembler.eloc(self,"Rep_Sym_End",module=this_module),\
        #            result.__class__.__name__,result)

        
        #old=self.pop_scope()    # Return to CharacterExpr scope
        #old.token(result)       # Add the result object to the CharacterExpr scope
        # Make the input token available to the next FSM state
        #self.stack(value)
        #self.unstack()
        #return "initc"
        return self.Call_Return(token=value,trace=trace)

    def Chr_Expected_Chrs(self,value,state,trace=False):
        # This action should not occur.  Should it be a value exception?
        self.ACT_Expected("characters",value)


  #                 +--------------------------+
  #                 |                          |
  #                 |    SYMBOL DECLARATION    |
  #                 |                          |
  #                 +--------------------------+

    # Context: sym - tokens: SYM, LPAREN
    # Scope: SymbolicReference(cterm=False)
    # See MacroCSLexer.init_rep() method

    # Parses: Symbolic variable symbol declaration statement (LCLx and GBLx) operands.
    #
    #   Case 1: An unsubscripted variable symbol declaration
    #
    #         &SYMBOL$
    #         \__ ___/            
    #            v             
    #         Primary
    #        Expression
    #
    #   Case 2: A subscripted variable symbol declaration
    #
    #         &SYMBOL(size-expression)$
    #         \__ __/ \_______ _____/          
    #            v            v
    #         Primary      Secondary
    #        Expression    Expression

    def Decl(self):
        
        inits=fsmparser.PState("inits")
        inits.action([SYM,],self.Decl_Sym)                   #   None term  >
        inits.error(self.ACT_Expected_Symbol)                # # None other
        self.state(inits)

        cterms=fsmparser.PState("cterms")
        cterms.action([LPAREN,],self.Decl_Subs)              #   cterm (     arith >
        cterms.action([EOS,],self.Decl_End)                  #   cterm EOS   finished
        cterms.error(self.ACT_Expected_LP)                   # E cterm other term
        self.state(cterms)

        ctermr=fsmparser.PState("ctermr")
        # Note: The final right parenthesis is stacked by the Arith call
        ctermr.action([RPAREN,],self.Decl_Rparen)            #   cterm )     terms
        ctermr.error(self.ACT_Expected_RP)                   # E cterm ???
        self.state(ctermr)

        terms=fsmparser.PState("terms")
        terms.action([EOS,],self.Decl_End)                    #   EOS (Hurray!) done
        terms.error(self.ACT_ExpectedEnd)                     # E ??? ($#@$!)
        self.state(terms)

    def Decl_Rparen(self,value,state,trace=False):
        # Now check for End-of-String...
        return "terms"

    def Decl_Sym(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        # This is always the primary expression so complete it now.
        gs.expression_end()
        # Determine if the declaration is for an array
        return "cterms"

    def Decl_Subs(self,value,state,trace=False):
        gs=self.scope()
        if __debug__:
            if trace:
                print("%s %r.expression_end(): primary:%s" \
                    % (assembler.eloc(self,"Decl_Subs",module=this_module),\
                        gs,gs._primary))
        # Stay with the SymbolicReference scope but change to arithmetic expr context
        ret=MPControl("ctermr",pctx="init")
        return self.Arith_Call(ret,token=None,follow=[RPAREN,],trace=trace)
        
    def Decl_End(self,value,state,trace=False):
        state.atend()


  #                 +-------------------------------+
  #                 |                               |
  #                 |    OPEN CODE QUOTED STRING    |
  #                 |                               |
  #                 +-------------------------------+

    # Context: quote - tokens: STRING
    # Scope: QuotedScope()
    # See MacroCSLexer.init_quote() method
    
    # Parses: An ppen code quoted string operand.  Double single quotes are 
    #         replaced with a single quote.  Double ampersands are not replaced
    #         by a single ampersand.  The user of the result object must do
    #         that.
    #
    #        'xxx ''stuff '' more stuff'
    #         \____________ __________/            
    #                      v
    #            asmtokens.STRING object

    def Quote(self):
    
        initq=fsmparser.PState("initq")
        initq.action([STRING,],self.Quote_Begin)             #   ...  'stuff  contq
        initq.error(self.ACT_Expected_Quote)
        self.state(initq)

        contq=fsmparser.PState("contq")
        contq.action([STRING,],self.Quote_Cont)              # 'stuff 'more   contq
        contq.action([EOS,],self.Quote_End)                  # EOS     done
        contq.error(self.ACT_Expected_Quote)
        self.state(contq)
        
    def Quote_Begin(self,value,state,trace=False):
        gs=self.scope()
        gs.str_begin(value)
        return "contq"
        
    def Quote_Cont(self,value,state,trace=False):
        gs=self.scope()
        gs.str_cont(value)
        return "contq"
        
    def Quote_End(self,value,state,trace=False):
        state.atend()


  #                 +----------------------------+
  #                 |                            |
  #                 |    SYMBOLIC REPLACEMENT    |
  #                 |                            |
  #                 +----------------------------+

    # Context: rep - tokens: AMP, SYMBOL, SYM, CHRSREP, LPAREN
    # Scope: CharacterExpr(cterm=False)
    # See MacroCSLexer.init_rep() method

    # Parses: Model statement fields and operands.  The entire string upto and
    #         including the end-of-string token, designated by the $ below is
    #         consumed.  The processing is similar to a character expression except
    #         that there are no enclosing single quotes used here and there are never
    #         any secondary expressions.
    #
    #        xxx &SYM. &SYM &SYM( ''  &&xx$
    #        \____________ _______________/            
    #                     v             
    #              Primary Expression

    def Rep(self):

        initr=fsmparser.PState("initr")
        initr.action([SYMBOL,],self.Rep_Sym_dot)             #   ...  &SYM.  initr
        initr.action([SYM],self.Rep_Sym)                     #   ...  &SYM   > 
        initr.action([LPAREN,],self.Rep_Chrs)                #   ...  (      initr
        initr.action([CHRSREP],self.Rep_Chrs)                #   ...  xxxx   initr
        initr.action([AMP,],self.Rep_Chrs)                   #   ...  &&     initr
        initr.action([EOS],self.Rep_End)                     #   ...  EOS    done
        initr.error(self.Rep_Expected_Chrs)                  # E      other
        self.state(initr)

        # Symbol with possible subscripts found.
        # Determining whether subscripts are present
        rsym=fsmparser.PState("rsym")
        rsym.action([LPAREN,],self.Rep_Subs)                 #   &SYM  (     >
        rsym.error(self.Rep_Sym_End)                         #   &SYM  other initr
        self.state(rsym)

    def Rep_Chrs(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "initr"

    def Rep_End(self,value,state,trace=False):
        gs=self.scope()
        if __debug__:
            if trace:
                print("%s %r.expression_end(): primary:%s" \
                    % (assembler.eloc(self,"Rep_End",module=this_module),\
                        gs,gs._primary))
        gs.expression_end()
        state.atend()

    # Subscript(s) detected with symbolic variable
    #   Scope:   SymbolicReference
    #   Context: rep
    def Rep_Subs(self,value,state,trace=False):
        gs=self.scope()
        # Because the replacement scope has already been pushed, don't need to use
        # enter_scope(), but do need to set how to get back to the rep context
        # we are about to leave

        # Enter scope for subscript recognition
        self.context("init",trace=trace)
        return "init%s" % gs.suffix
        # When the RPAREN is detected at the end of the subscript, we return to 
        # these states and context via a leave_scope()
        
    # A replacement symbolic reference started (without concatenation)
    #   Scope:   CharacterExpr
    #   Context: rep
    def Rep_Sym(self,value,state,trace=False):
        gs=self.scope()
        ret=MPControl("initr",pctx="rep")
        return self.Sym_Call(ret,token=value,trace=trace)

    def Rep_Sym_dot(self,value,state,trace=False):
        gs=self.scope()
        symref=SymbolRef()
        symref.primary(value)
        self.token(symref)
        return "initr"

    # Complete a symbolic variable reference without sugscripts:
    #   Scope: SymbolicReference
    #   Context: rep
    def Rep_Sym_End(self,value,state,trace=False):
        gs=self.scope()
        result=gs.result()      # Get the result object (SymbolRef)
        assert isinstance(result,SymbolRef),\
            "%s expected SymbolRef object from current scope (%s): %s" \
                % (assembler.eloc(self,"Rep_Sym_End",module=this_module),\
                    gs.__class__.__name__,result)

        old=self.pop_scope()    # Return to CharacterExpr scope
        old.token(result)       # Add the result object to the CharacterExpr scope
        # Make the input token available to the next FSM state
        self.stack(value)
        self.unstack()
        return "initr"
        
    def Rep_Expected_Chrs(self,value,state,trace=False):
        # This action should not occur.  Should it be a value exception?
        self.ACT_Expected("characters",value)


  #                 +---------------------------------+
  #                 |                                 |
  #                 |    SEQUENCE SYMBOL REFERENCE    |
  #                 |                                 |
  #                 +---------------------------------+

    # Context: seq - tokens: SEQSYM 
    # Scope: MacroScope
    # See MacroCSLexer.init_seq() method

    def Seq(self):
        
        seqb=fsmparser.PState("seqb")
        seqb.action([SEQSYM,],self.Seq_Sym)                #   none  .seq  seq_end
        seqb.error(self.Seq_Not_Seq)                       # E none   ???? 
        self.state(seqb)
        
        seq_end=fsmparser.PState("seq_end")
        seq_end.action([EOS,],self.Seq_End)                #   .seq  EOS   done
        seq_end.error(self.Seq_Not_End)                    # E .seq  ???
        self.state(seq_end)

    def Seq_End(self,value,state,trace=False):
        gs=self.scope()
        gs.expression_end()   # The primary expression is the single SEQSYM token
        state.atend()

    def Seq_Not_End(self,value,state,trace=False):
        self.ACT_Expected("end of operand",value)

    def Seq_Not_Seq(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol",value)

    def Seq_Sym(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "seq_end"
        

  #                 +------------------------+
  #                 |                        |
  #                 |    SYMBOL REFERENCE    |
  #                 |                        |
  #                 +------------------------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: SymbolicReference
    # See MacroCSLexer.init_sym() method
    
    # Parses: A macro symbolic symbol reference with optional secondary arithmetic
    #         expression as the only secondary expression.  Whatever token occurs
    #         following either the symbol or the ending right parenthesis is
    #         stacked for the calling scope to process.
    #
    #         +--primary expresion
    #         |
    #         v
    #       &SYM(arithemetic-expression)
    #            \__________ _________/
    #                       v
    #              secondary expression
    
    def Sym(self):
        # These two lists control the sharing of information with other classes
        # required to correctly process lexical tokens that support symbol names.
        # If new lexical tokens are created for symbol name support, modify these
        # two lists for proper information sharing.
        attr_tids=[SATTR,SAREF]   # Symbol name types that support attributes
        noattr_tids=[SYM,SYMBOL]  # Symbol name types that do not support attributes

        # Coordinate initial token processing with SymbolicReference scope
        # by sharing the recognizing token ids.  SymbolicReference scope needs these
        # to recognize when it needs to inspect a token for possible references
        # to &SYSLIST.
        sym_ids=[]
        for tok in attr_tids:
            sym_ids.append(tok.tid)
        for tok in noattr_tids:
            sym_ids.append(tok.tid)
        #print("%s sym_ids: %s" \
        #    % (assembler.eloc(self,"Sym",module=this_module),sym_ids))
        SymbolicReference.tids=sym_ids

        # Coordinate token ids with SymbolRef result object for tokens that support
        # a symbol attribute.  This informs SymbolRef.primary() method to extract
        # the attribute from the asmtokens.LexicalToken object.
        attr_ids=[]
        for tok in attr_tids:
            attr_ids.append(tok.tid)
        #print("%s attr_ids: %s" \
        #    % (assembler.eloc(self,"Sym",module=this_module),attr_ids))
        SymbolRef.attr_tids=attr_ids

        initsr=fsmparser.PState("initsr")
        initsr.action(attr_tids,self.Sym_Start)            # none sym   srsub
        initsr.action(noattr_tids,self.Sym_Start)          # none sym   srsub
        initsr.error(self.Sym_Call_Fail)
        self.state(initsr)

        srsub=fsmparser.PState("srsub")
        srsub.action([LPAREN,],self.Sym_Subs)              # sym  (    >Arith
        srsub.error(self.Sym_End)                          # sym  ?    <return
        self.state(srsub)

        srend=fsmparser.PState("srend")
        srend.action([RPAREN,],self.Sym_Subs_End)          # Arith<  )
        srend.error(self.Sym_Arith_Fail)                   # internal failure
        self.state(srend)

    def Sym_Arith_Fail(self,value,state,trace=False):
        raise ValueError("%s Arith_Call returned unexpected token: %s" \
            % (assembler.eloc(self,"Sym_Arith_Fail",module=this_module),value))
        
    def Sym_Call(self,ret,token=None,trace=False):
        assert isinstance(ret,MPControl),\
            "%s 'ret' argument must be a MPControl object: %s" \
                % (assembler.eloc(self,"Sym_Call",module=this_module),ret)
        assert token is not None,\
            "%s 'token' argument must not be None" \
                % assembler.eloc(self,"Sym_Call",module=this_module)

        gs=self.scope()
        new=SymbolicReference(gs.lopnd)
        newmp=MPControl("initsr",pctx="init")
        return self.enter_scope(gs,ret,new,newmp,stack=token,trace=trace)

    def Sym_Call_Fail(self,value,state,trace=False):
        raise ValueError("%s expected symbol type token at start of symbol "\
            "reference, received: %s" \
                % (assembler.eloc(self,"Sym_Call_Fail",module=this_module),value))
        
    # Complete symbol reference without secondary arithmetic expression
    # The symbol is returned for the calling scope to process as one of its own
    def Sym_End(self,value,state,trace=False):
        return self.Call_Return(token=value,trace=trace)

    def Sym_Start(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        if __debug__:
            if trace:
                print("%s %r.expression_end(): primary:%s" \
                    % (assembler.eloc(self,"Sym_Start",module=this_module),\
                        gs,gs._primary))
        gs.expression_end()   # Complete the primary expression (the symbol name)
        return "srsub"

    def Sym_Subs(self,value,state,trace=False):
        ret=MPControl("srend",pctx="init")
        return self.Arith_Call(ret,token=None,follow=[RPAREN,],trace=trace)

    def Sym_Subs_End(self,value,state,trace=False):
        return self.Call_Return(trace=trace)
    


  #                 +------------+
  #                 |            |
  #                 |    SETC    |
  #                 |            |
  #                 +------------+

    # Context: init - tokens: LPAREN, RPAREN,  COMMA, 
    #                         LOGNOT, LOGICAL, COMPARE, AOPER, NOT,
    #                         SDBIN,  SDCHR,   SDHEX,   SDDEC,
    #                         SEQSYM, SATTR,   LATTR,   QUOTE
    # Scope: SETCScope
    # See MacroCSLexer.init_rep() method
    #
    # Parses operands of:
    #
    #   Case 1: A Character expression - see Chr()
    #
    #   Case 2: Primary Expression of a single assembler label or symbol attribute
    #
    #        [X']LABEL
    #        [X']&SYMBOL
    #        [X']&SYMBOL(subscript,...)   Depends upon symbol's sublist or subscript
    
    def SETC(self):
        
        setc=fsmparser.PState("setc")
        setc.action([QUOTE,],self.SETC_Beg)              #   None   '       >cexpr
        setc.action([SAREF,],self.SETC_Attr)             #   None   T'&SYM  >sym
        setc.action([LAREF,],self.SETC_LAttr)            #   None   T'LABEL setc_end
        setc.error(self.ACT_Expected_String)             # E None   other
        self.state(setc)

        setc_end=fsmparser.PState("setc_end")
        setc_end.action([EOS,],self.SETC_End)            #   EOS (Hurray!) done
        setc_end.error(self.ACT_ExpectedEnd)             # E ??? ($#@$!)
        self.state(setc_end)

    def SETC_Attr(self,value,state,trace=False):
        gs=self.scope()
        retmp=MPControl("setc_end",pctx="setc")
        return self.Sym_Call(retmp,token=value,trace=trace)

    def SETC_Beg(self,value,state,trace=False):
        # Start new complex term scope for Character expression
        gs=self.scope()                # Fetch the current scope (MacroScope)
        retmp=MPControl("setc_end",pctx="init")
        return self.Chr_Call(retmp,token=None,trace=trace)

    def SETC_LAttr(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "setc_end"

    def SETC_End(self,value,state,trace=False):
        gs=self.scope()                # Fetch the current scope (MacroScope)
        if __debug__:
            if trace:
                print("%s %r.expression_end(): primary:%s" \
                % (assembler.eloc(self,"SETC_End",module=this_module),\
                    gs,gs._primary))
        gs.expression_end()
        state.atend()


  #
  # Error condition actions
  #
    def ACT_Expected(self,expected,value,found=None):
        self.stop()    # Terminate the lexer because we are bailing.
        msg="expected %s, found " % expected
        if found is None:
            if isinstance(value,lexer.EOS):
                msg="%s%s" % (msg,"end of statement")
            else:
                msg='%s"%s"' % (msg,value.string)
        else:
            msg="%s%s" % (msg,found)
        raise assembler.AsmParserError(value,msg=msg)

    def ACT_Expected_Aoper(self,value,state,trace=False):
        self.ACT_Expected("aritmetic operator",value)
 
    def ACT_Expected_Comma(self,value,state,trace=False):
        self.ACT_Expected("comma",value)

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operand",value)
        
    def ACT_Expected_EndExpr(self,value,state,trace=False):
        self.ACT_Expected("end of expression",value)
    
    def ACT_Expected_LP(self,value,state,trace=False):
        self.ACT_Expected("left parenthesis",value)
        
    def ACT_Expected_LP_Seq(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol or left parenthesis",value)

    def ACT_Expected_LP_Term(self,value,state,trace=False):
        self.ACT_Expected("label, self-defining term, currrent location or left "
            "parenthesis",value)

    def ACT_Expected_Quote(self,value,state,trace=False):
        self.ACT_Expected("quote",value)

    def ACT_Expected_RP(self,value,state,trace=False):
        self.ACT_Expected("right parenthesis",value)

    def ACT_Expected_RP_Oper(self,value,state,trace=False):
        self.ACT_Expected("right parenthesis or operator",value)

    def ACT_Expected_Seq(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol or left parenthesis",value)
        
    def ACT_Expected_Seq_Only(self,value,state,trace=False):
        self.ACT_Expected("sequence symbol",value)

    def ACT_Expected_String(self,value,state,trace=False):
        self.ACT_Expected("start of character string",value)

    def ACT_Expected_Symbol(self,value,state,trace=False):
        self.ACT_Expected("symbolic variable name",value)
        
    def ACT_Unbalaced_Primary(self,value,state,trace=False):
        self.ACT_Expected("balanced parenthesis",value)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)