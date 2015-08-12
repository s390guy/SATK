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

# This module tests a new ASMA instruction operand input parsing stategy.

this_module="%s.py" % __name__

# This module performs general operand parsing for:
#   - machine instructions
#   - some assembler directives and
#   - some macro directives
#
# The operands parsed using this module all have a common structure:
#   1. a "primary operand" and optionally modified by
#   2  one or more "secondary operands".
# Secondary operands are enclosed in a left/right parenthesis pair.  If more than
# one secondary operand is present, the secondary operands are separated by commas.
# The primary operands in some cases may be an expression other times it is restricted,
# for example, to a symbolic variable.  The secondary operands are always expressions.
# Whether symbols, symbolic variables or other basic operand types are allowed is
# context sensitive.
#
# Examples of potential usage:            Operand             Primary   Secondary
#
#   machine instruction storage operand   FIELDA+1            FIELDA+1   none
#                                         FIELDA+1(R5)        FIELDA+1   R5
#                                         FIELDA+1(R6,R7)     FIELDA+1   R6 and R7
#   machine instruction register operand  R7+1                R7+1       none
#   macro SETC operand                    'STUFF'(&S,&E)      STUFF      &S and &E
#   macro statement positional parameter  (A,B,C)             none       A, B and C
#   macro statement keyword parameter     PARM=A              PARM       A
#                                         PARM=(A,B,C)        PARM       A, B and C
#   macro symbolic variable definition    &SYMA               &SYMA      none
#                                         &SYMA(6)            &SYMA      A
#                                         &SYSLIST(&N,&D)     &SYSLIST   &N and &D
#
# In all cases, the operand has been isolated from the statements operand field
# before being presented to this module for further parsing.
#
# Specialized parsers are available for most of these cases.  Eventually this module
# will supplant the specialized operand parser where it makes sense.  Currently
# this module is used to parse:
#   - machine instructions.

# Python imports: none
# SATK imports:
import lexer                # Access the lexical analyzer
import fsmparser            # Access the finite state machine based parser
import pratt3               # Access the generalized operator precedence evaluator

# ASMA imports:
import assembler            # Access the assembler language module
import asmbase              # Access the assembler base classes
import asmtokens            # Need a variety of lexical analyzer tokens


AOPER=asmtokens.AOperType()
COMMA=asmtokens.CommaType()
EOS=lexer.EOSType()
LABEL=asmtokens.LabelType()
LATTR=asmtokens.LabelAttrType()
LPAREN=asmtokens.LParenType()
RPAREN=asmtokens.RParenType()
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()


# Operand expression lexical analyzer used by the OperandParser object.
class OperandLexer(lexer.Lexer):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm

    def init(self):
        tdebug=self.dm.isdebug("tdebug")

        lst=[]
        lst.append(LPAREN)      # "("
        lst.append(RPAREN)      # ")"
        lst.append(COMMA)       # ","
        lst.append(AOPER)       # "+", "-", "*", "/"
        lst.append(SDBIN)       # "B'01.."
        lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        lst.append(SDHEX)       # "X'0..F..'"
        lst.append(SDDEC)       # "0..9.."
        lst.append(LATTR)       # "label" or "X'label"
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


# This class recongizes expressions that make up a machine instruction operand.
# The operand takes the form:
#   primary_expression[(secondary_expression[,secondary_expression]...)]
#
# Register and immediate instructin operands are composed of:
#   primary_expression only
# Storage operands are composed of:
#   primary_expression,
#   primary_expression(secondary_expression)
#   primary_expression(,secondary_expression)
#   primary_expression(secondaryd_expression,secondary_expression)
#
# The parser is not limited to two secondary expressions.  The user of the parsed
# results must validate the number of secondary expressions.
#
# An empty string is not a valid operand.  An empty list of secondary expressions
# is also not a valid operand.
#
# The parsed operand results in a POperand object.  Its primary attribute is a
# ASMExpr object containing the parsed primary expression.  Its secondary attribute 
# is a list of ASMExpr objects, each corresponsing to a secondary expression.  The
# ASMExpr object contains a list of lexical tokens, mostly defined by the asmtokens
# module.
#
# This class supports only expression operator and operand syntax. Ultimately the
# expression is transformed into a sequence or Pratt evaluator tokens.  The Pratt
# expression evaluator handles operator precedence and parenthesized portions of
# the expression.
class OperandParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm,trace=False):
        #super().__init__(dm,pm,scope=OperandScope,trace=False)
        super().__init__(dm,pm,trace=False)

    # Define operand parser states and action methods.
    #
    # Parsing of operands into primary and secondary expressions is driven by
    # the preceding lexical token and operator syntax rules.  The preceding token
    # defines how the following token will be handled, hence its state.  The boundary
    # between the primary expression and each secondary expression is handled by
    # the global scope object.
    def initialize(self):

        # Expression parsing involves primarily six states:
        #   init    Initial state at the start of the expression parsing.  This is 
        #           the state at the start of processing the primary and each
        #           secondary expression.
        #   term    The state following a term: label, self-defining term or the
        #           current location (*)
        #   binary  The state following a binary operator: +, -, * (multiply), /
        #   unary   The state following a unary operator: +, -
        #   lparen  The state following a left parenthesis: (
        #   rparen  The state following a right parenthesis: )
        #   end     The state at which the operand should be completely parsed
        term_tokens=[SDBIN,SDHEX,SDCHR,SDDEC,LATTR]
        oper_tokens=[AOPER,]
                                                            #   prev current
                                                            #   token token  next
        init=fsmparser.PState("init")
        init.action(term_tokens,self.ACT_Start_T)           #   None  term   term
        init.action(oper_tokens,self.ACT_Start_O)           #   None  oper   unary/E
        init.action([LPAREN,],self.ACT_Start_L)             #   None  (      lparen
        init.action([RPAREN,],self.ACT_Expected_LP_Term)    # E None  )
        init.action([COMMA,],self.ACT_Expected_LP_Term)     # E None  ,
        init.action([EOS,],self.ACT_Expected_LP_Term)       # E None  EOS
        init.error(self.ACT_Expected_LP_Term)               # E None  ?
        self.state(init)

        unary=fsmparser.PState("unary")
        unary.action(term_tokens,self.ACT_Unary_T)          #   unary term   term
        unary.action(oper_tokens,self.ACT_Expected_LP_Term) # E unary oper
        unary.action([LPAREN,],self.ACT_Unary_L)            #   unary (      lparen
        unary.action([RPAREN,],self.ACT_Expected_LP_Term)   # E unary )
        unary.action([COMMA,],self.ACT_Expected_LP_Term)    # E unary ,
        unary.action([EOS,],self.ACT_Expected_LP_Term)      # E unary EOS
        unary.error(self.ACT_Expected_LP_Term)              # E unary ?
        self.state(unary)

        binary=fsmparser.PState("binary")
        binary.action(term_tokens,self.ACT_Binary_T)        #   binary term  term
        binary.action(oper_tokens,self.ACT_Binary_O)        #   binary oper unary/term
        binary.action([LPAREN,],self.ACT_Binary_L)          #   binary (
        binary.action([RPAREN,],self.ACT_Expected_LP_Term)  # E binary )
        binary.action([COMMA,],self.ACT_Expected_RP_Oper)   # E binary ,
        binary.action([EOS,],self.ACT_Expected_LP_Term)     # E binary EOS
        binary.error(self.ACT_Expected_LP_Term)             # E binary ?
        self.state(binary)

        lparen=fsmparser.PState("lparen")
        lparen.action(term_tokens,self.ACT_LParen_T)        #   ( term     term
        lparen.action(oper_tokens,self.ACT_LParen_O)        #   ( oper  unary/term/E
        lparen.action([LPAREN,],self.ACT_LParen_L)          #   ( (        lparen
        lparen.action([RPAREN,],self.ACT_Expected_LP_Term)  # E ( )
        lparen.action([COMMA,],self.ACT_Expected_LP_Term)   # E ( ,
        lparen.action([EOS,],self.ACT_Expected_LP_Term)     # E ( EOS
        lparen.error(self.ACT_Expected_LP_Term)             # E ( ?
        self.state(lparen)

        rparen=fsmparser.PState("rparen")
        rparen.action(term_tokens,self.ACT_Expected_RP_Oper)# E ) term
        rparen.action(oper_tokens,self.ACT_RParen_O)        #   ) oper   binary/E
        rparen.action([LPAREN,],self.ACT_RParen_L)          #   ) (       init/E
        rparen.action([RPAREN,],self.ACT_RParen_R)          #   ) )      rparen/end
        rparen.action([COMMA,],self.ACT_RParen_C)           #   ) ,       init/E
        rparen.action([EOS,],self.ACT_RParen_E)             #   ) EOS     done/E
        rparen.error(self.ACT_Expected_RP_Oper)             #   ) ?       E
        self.state(rparen)

        term=fsmparser.PState("term")
        term.action(term_tokens,self.ACT_Expected_RP_Oper)  # E term term
        term.action(oper_tokens,self.ACT_Term_O)            #   term oper binary/E
        term.action([LPAREN,],self.ACT_Term_L)              #   term (    init/E
        term.action([RPAREN,],self.ACT_Term_R)              #   term )   rparen/end
        term.action([COMMA,],self.ACT_Term_C)               #   term ,    init/E
        term.action([EOS,],self.ACT_Term_E)                 #   term EOS   done/E
        term.error(self.ACT_Expected_RP_Oper)               # E term ?
        self.state(term)

        # This state ensures nothing follows the final secondary expression's
        # terminating right parenthesis
        end=fsmparser.PState("end")
        end.action([EOS,],self.ACT_Operand_End)               #   EOS (Hurray!) done
        end.error(self.ACT_ExpectedEnd)                       # E ??? ($#@$!)
        self.state(end)

    def Lexer(self,lexer):
        return super().Lexer("opnd")

    # Parses a list of operands, each operance either None when omitted or an
    # instance of asmline.LOperand
    # Returns:
    #   A list of asmbase.ASMOperand objects, or a None for imitted operands
    # Exceptions:
    #   AsmParserError  when an error is recognized.
    def parse_operands(self,stmt,debug=False):
        self.operands=[]
        for n,opnd in enumerate(stmt.operands):
            # opnd is a LOperand object
            if opnd is None:
                self.operands.append(None)
                continue

            if __debug__:
                if debug:
                    print('%s parsing opnd %s: "%s"' \
                        % (assembler.eloc(self,"parse_operands",module=this_module),\
                            n,opnd.text))
            scope=OperandScope(opnd).init(stmt=stmt)
            scope=self.parse(opnd.text,scope=scope,fail=False)
            if __debug__:
                if debug:
                    print("%s opnd %s: scope: %s" \
                        % (assembler.eloc(self,"parse_operands",module=this_module),\
                            n,scope))

            opnd=scope.result()
            if isinstance(opnd,asmbase.ASMOperand):
                #self.operands.append(opnd.result())
                self.operands.append(opnd)
            else:
                raise ValueError("%s operand %s not returned from parse: %s" \
                    % (assembler.eloc(self,"parse_operands",module=this_module),\
                        n,opnd.text))

        return self.operands   # List of POperand objects or None if omitted

  #
  #  Common actions used in various states
  #
    def ACT_Common_Term(self,value,state,trace=False):
        gs=self.scope()
        gs.token(value)
        return "term"


  #
  #  Actions following binary operator
  #
    def ACT_Binary_L(self,value,state,trace=False):
        # binary (
        gs=self.scope()
        gs.lparen(value)
        return "lparen"

    def ACT_Binary_O(self,value,state,trace=False):
        gs=self.scope()

        # binary unary
        if value.unary:
            # If operator is a unary
            gs.token(value)
            return "unary"

        # binary loc
        elif value.string == "*":
            # Check for token string of "*" to detect current location counter
            value.current()     # Update token to reflect location counter symbol
            gs.token(value)
            return "term"       # Treat the location counter as a term

        # binary binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    def ACT_Binary_T(self,value,state,trace=False):
        # binary term
        return self.ACT_Common_Term(value,state,trace=trace)

  #
  #  Actions following left parenthesis
  #
    def ACT_LParen_L(self,value,state,trace=False):
        # ( (
        gs=self.scope()
        gs.lparen(value)
        return "lparen"

    def ACT_LParen_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags
        if value.unary:
            # ( unary
            gs=self.scope()
            gs.token(value)
            return "unary"
        
        elif value.string=="*":
            # ( current-location-counter
            value.current()
            gs.token(value)
            return "term"

        # ( binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    def ACT_LParen_T(self,value,state,trace=False):
        # ( term
        return self.ACT_Common_Term(value,state,trace=trace)

  #
  #  Actions following right parenthesis
  #
    def ACT_RParen_C(self,value,state,trace=False):
        # ) ,
        gs=self.scope()
        if gs.primary:
            self.ACT_Expected_RP_Oper(value,state,trace=trace)

        # The comma marks the end of a secondary expression
        if gs.balanced_parens():
            gs.expression_end()
            return "init"

        # Secondary expression has unbalanced parenthesis
        self.ACT_Unbalaced(value,state,trace=trace)

    def ACT_RParen_E(self,value,state,trace=False):
        # ) EOS
        gs=self.scope()

        if gs.primary:
            if gs.balanced_parens:
                gs.expression_end()
                state.atend()
                return
            else:
                self.ACT_Unbalaced_Primary(alue,state,trace=trace)

        # What to do if in secondaryies???
        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def ACT_RParen_L(self,value,state,trace=False):
        # ) (
        gs=self.scope()

        if gs.primary:
            # See if primary expression done and now starting secondaries
            if gs.balanced_parens():
                gs.expression_end()
                return "init"

        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def ACT_RParen_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags

        # ) binary
        if value.binary:
            gs=self.scope()
            gs.token(value)
            return "binary"

        # ) unary
        self.ACT_Expected_RP_Oper(value,state,trace=trace)    

    def ACT_RParen_R(self,value,state,trace=False):
        # ) )
        gs=self.scope()

        if gs.primary:
            gs.rparen(value)
            return "rparen"

        # For secondary expression, this might be the ending right parenthesis
        if gs.balanced_parens():
            gs.expression_end()
            return "end"
        else:
            gs.rparen(value)
            return "rparen"
        self.ACT_Unbalaced(value,state,trace=trace)

  #
  #  Initial expression actions
  #
    def ACT_Start_L(self,value,state,trace=False):
        # (
        gs=self.scope()
        gs.lparen(value)
        return "lparen"

    def ACT_Start_O(self,value,state,trace=False):
        gs=self.scope()
        value.syntax()     # Set operator syntax flags

        # unary
        if value.unary:
            gs.token(value)
            return "unary"
            
        # Check for current location counter at start of expression
        elif value.string=="*":
            # Check for token string of "*" to detect current location counter
            value.current()     # Update token to reflect location counter symbol
            gs.token(value)
            return "term"       # Treat the location counter as a term

        # binary
        self.ACT_Expected_LP_Term(value,state,trace=trace)

    def ACT_Start_T(self,value,state,trace=False):
        # term
        return self.ACT_Common_Term(value,state,trace=trace)

  #
  # Actions following term
  #
    def ACT_Term_C(self,value,state,trace=False):
        # term ,
        gs=self.scope()

        if gs.primary:
            self.ACT_Expected_LP_Term(value,state,trace=trace)

        # For secondary is end of the expresion
        if gs.balanced_parens():
            gs.expression_end()
            return "init"
        self.ACT_Unbalaced(value,state,trace=trace)

    def ACT_Term_E(self,value,state,trace=False):
        # term EOS
        gs=self.scope()

        if gs.primary:
            if gs.balanced_parens:
                gs.expression_end()
                state.atend()
                return
            else:
                self.ACT_Unbalaced_Primary(alue,state,trace=trace)

        # For secondary missing final right parenthesis
        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def ACT_Term_L(self,value,state,trace=False):
        # term (
        gs=self.scope()

        if gs.primary:
            if gs.balanced_parens():
                # End of primary expression
                gs.expression_end()
                # Start of secondary expression
                return "init"

        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def ACT_Term_O(self,value,state,trace=False):
        value.syntax()     # Set operator syntax flags

        # term binary
        if value.binary:
            gs=self.scope()
            gs.token(value)
            return "binary"

        # term unary
        self.ACT_Expected_RP_Oper(value,state,trace=trace)

    def ACT_Term_R(self,value,state,trace=False):
        # term )
        gs=self.scope()

        if gs.primary:
            gs.rparen(value)
            return "rparen"

        # For secondary need to see if end of secondary expressions
        if gs.balanced_parens():
            gs.expression_end()
            return "end"
        gs.rparen(value)
        return "rparen"

  #
  # Actions following unary operator
  #
    def ACT_Unary_L(self,value,state,trace=False):
        # unary (
        gs=self.scope()
        gs.lparen(value)
        return "lparen"

    def ACT_Unary_T(self,value,state,trace=False):
        # unary term
        return self.ACT_Common_Term(value,state,trace=trace)

  #
  # Actions following secondary expressions
  #
    def ACT_Operand_End(self,value,state,trace=False):
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

    def ACT_Expected_LP_Term(self,value,state,trace=False):
        self.ACT_Expected("label, self-defining term, currrent location or left "
            "parenthesis",value)

    def ACT_Expected_RP_Oper(self,value,state,trace=False):
        self.ACT_Expected("right parenthesis or operator",value)

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operand",value)

    def ACT_Unbalanced(self,value,state,trace=False):
        self.ACT_Expected("balanced parenthesis",value)


class OperandScope(asmbase.AsmFSMScope):
    def __init__(self,lopnd):
        super().__init__()
        self.lopnd=lopnd       # LOperand source object
        self.opnd=None         # ASMOperand result object

        # Whether the primary expression is being parsed (True) or a secondary
        # expression is being parsed (False).
        self.primary=True  # Initially the primary expression is being parsed

    # Checks the surrent state of parenthesis balancing
    # Returns:
    #   True   if the expression parenthesis are balanced
    #   False  if the expression parenthesis are not balanced
    def balanced_parens(self):
        return self._parens==0

    # This method completes the current expression being accumulated by the scope
    # and automatically moves from the primary expression to the secondary
    # expressions when the primary expression is completed.
    # The result ASMOperand object in self.opnd is updated with the completed
    # operand.
    def expression_end(self):
        #print(assembler.eloc(self,"expression_end",module=this_module))
        if self.primary:
            expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
            self.opnd.primary(asmbase.ASMExprArith(expr))
            self.primary=False
        else:
            expr=self.expr_end(source=self.lopnd,line=self._stmt.lineno)
            self.opnd.secondary(asmbase.ASMExprArith(expr))
        self.previous=None

    # Initializes the scope for use and instantiates the result object
    def init(self,stmt=None):
        self.opnd=asmbase.ASMOperand()
        super().init(stmt=stmt)
        return self

    # Returns the resulting ASMOperand object of the parse.
    def result(self):
        #print("Operand Scope.opnd: %s" % self.opnd)
        return self.opnd

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)