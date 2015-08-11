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

this_module="asmfsmbp.py"
raise NotImplementedError("module is deprecated: %s" % this_module)

# Python imports: none
# SATK imports:
import lexer                # Access the lexical analyzer
import fsmparser            # Access the finite state machine based parser
import pratt3               # Access the generalized operator precedence evaluator
import seqparser            # Access the sequential parser
# ASMA imports:
import assembler            # Access the assembler language module
import asmbase              # Access parser base classes
import asmtokens            # Access standard lexical and pratt3 tokens
import macsyms              # Access SymbolID object

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
symvar="&%s" % assembler.label      # Symbolic variable recognizer


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
BWNOP=asmtokens.BWNOpType()
BWOP=asmtokens.BWOpType()
COMMA=asmtokens.CommaType()
COMPARE=asmtokens.CompType()
EOO=asmtokens.EoOperType()
EOS=asmtokens.EOSType()
EQUAL=asmtokens.EqualType()
LABEL=asmtokens.LabelType()
LOGICAL=asmtokens.LogicalType()
LOGNOT=asmtokens.LogNotType()
LPAREN=asmtokens.LParenType()
MACLABEL=asmtokens.MacLabelType()
#NATTR=asmtokens.NAttrType()
NOT=asmtokens.NotType()
RPAREN=asmtokens.RParenType()
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()
SEQSYM=asmtokens.SeqType()
STRING=asmtokens.StringType()
SYMREF=asmtokens.SymRefType()



#
#  +-------------------------------------------+
#  |                                           |
#  |   Macro Arithmetic Expression Evaluator   |
#  |            (AGO, SETA, SETC)              |
#  |                                           |
#  +-------------------------------------------+
#

class ArithEval_old(pratt3.PParser):
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
        # Initialize my operator precedence values
        self.operator(pratt3.PBWNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
        #self.operator(pratt3.PFloorDiv,lbp=50,rbp=None,symbol="/",\
        #    isinfix=True,isunary=False)
        self.operator(asmtokens.PAsmDiv,lbp=50,rbp=None,symbol="/",\
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

class ArithExpr_old(pratt3.PExpr):
    evaluator=ArithEval_old()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return ArithExpr.evaluator.run(\
            self,external=external,debug=debug,trace=trace)
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

class BinaryEval_old(pratt3.PParser):
    def __init__(self):
        super().__init__()

        # Operator Precedence (Highest to Lowest)
        #   Comparisons
        #   NOT
        #   AND
        #   OR
        #   XOR
        self.operator(pratt3.PNot,lbp=None,rbp=100,symbol="NOT",\
            isinfix=False,isunary=True)
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

class BinaryExpr_old(pratt3.PExpr):
    evaluator=BinaryEval_old()
    def __init__(self,desc,lineno,tokens=[]):
        name="%s %s" % (desc,lineno)
        super().__init__(desc=name,tokens=tokens)
    def evaluate(self,external,debug=False,trace=False):
        return BinaryExpr.evaluator.run(\
            self,external=external,debug=debug,trace=trace)
    def token(self,ptok):
        super().token(ptok)


#
#  +-------------------------------------+
#  |                                     |
#  |   Macro Logical Expression Parser   |
#  |             (AIF, SETB)             |
#  |                                     |
#  +-------------------------------------+
#

#class BinaryParser(asmbase.AsmFSMParser):
#    def __init__(self,dm,pm):
#        super().__init__(dm,pm,scope=BScope,trace=False)

    # Define my states and action methods.
#    def initialize(self):
#        init=fsmparser.PState("init")
#        init.action([LPAREN,RPAREN,SDBIN,SDHEX,SDCHR,SDDEC,NATTR,SYMREF,STRING,\
#                     LOGNOT,LOGICAL,COMPARE,NOT],method=self.ACT_Add_Token)
#        init.action([EOO,EOS],self.ACT_End)
##        init.error(self.ACT_ExpectedExpr)
#        self.state(init)

#    def ACT_Add_Token(self,value,state,trace=False):
#        gs=self.scope()
#        gs.token(value)
#        return state.state

#    def ACT_End(self,value,state,trace=False):
##        gs=self.scope()
#        gs.ck_parens(value)
#        gs.lextoks=gs.expr_end()
#        state.atend()

#    def ACT_ExpectedExpr(self,value,state,trace=False):
#        self.ACT_Expected("logical operation or valid logical operand",value)

#    def ACT_LPAREN(self,value,state,trace=False):
#        gs=self.scope()
#        gs.lparen(value)
#        return "oper"

#    def ACT_RPAREN(self,value,state,trace=False):
#        gs=self.scope()
#        gs.rparen(value)
#        return "oper"


#class BScope(asmbase.AsmFSMScope):
#    def __init__(self):
#        super().__init__()
#    def __str__(self):
#        string="%s():" % self.__class__.__name__
#        for tok in self.lextoks:
#            string="%s\n    %s" % (string,tok)
##        return string
#    def init(self):
#        super().init()
#        self.lextoks=[]


#
#  +------------------------------+
#  |                              |
#  |   Macro AGO Operand Parser   |
#  |                              |
#  +------------------------------+
#

class AGOParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,scope=AGOScope,trace=False)

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


class AGOScope(asmbase.AsmFSMScope):
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

class AIFParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,scope=AIFScope,trace=False)

    # Define my states and action methods.
    def initialize(self):
        init=fsmparser.PState("init")
        init.action([LPAREN,],self.ACT_LPAREN_First)
        init.error(self.ACT_ExpectedLParen)
        self.state(init)

        oper=fsmparser.PState("oper")
        oper.action([LPAREN,],self.ACT_LPAREN_Other)
        oper.action([RPAREN,],self.ACT_RPAREN)
        oper.action([SDBIN,SDHEX,SDCHR,SDDEC,SYMREF,STRING,LOGNOT,LOGICAL,COMPARE,NOT],
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


class AIFScope(asmbase.AsmFSMScope):
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

#class CharParser(asmbase.AsmFSMParser):
#    def __init__(self,dm,pm):
#        super().__init__(dm,pm,scope=CScope,trace=False)

    # Define my states and action methods.
#    def initialize(self):
#        init=fsmparser.PState("init")
#        init.action([STRING,],self.ACT_String_Token)
#        init.error(self.ACT_ExpectedString)
#        self.state(init)

#        more=fsmparser.PState("more")
#        more.action([STRING,],self.ACT_String_Extend)
#        more.action([LPAREN,],self.ACT_Sub_String_Start)
#        more.action([EOO,EOS],self.ACT_Done)
#        more.error(self.ACT_ExpectedSubString)
#        self.state(more)

#        subst=fsmparser.PState("subst")
##        subst.action([LPAREN,],self.ACT_LParen)
#        subst.action([RPAREN,],self.ACT_RParen1)
#        subst.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,SYMREF],method=self.ACT_Add_Token)
#        subst.action([COMMA,],self.ACT_Start_Done)
#        subst.error(self.ACT_ExpectedComma)
#        self.state(subst)

#        strlen=fsmparser.PState("strlen")
#        strlen.action([LPAREN,],self.ACT_LParen)
#        strlen.action([RPAREN,],self.ACT_RParen2)
#        strlen.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,SYMREF],method=self.ACT_Add_Token)
#        strlen.error(self.ACT_ExpectedRParen)
#        self.state(strlen)

#        done=fsmparser.PState("done")
#        done.action([EOO,EOS],self.ACT_Done)
#        done.error(self.ACT_ExpectedEnd)
#        self.state(done)

#    def ACT_Add_Token(self,value,state,trace=False):
#        gs=self.scope()
#        gs.token(value)
#        return state.state   # Stay in this state

#    def ACT_Done(self,value,state,trace=False):
#        gs=self.scope()
#        gs.st_token=gs.str_end()
#        state.atend()

#    def ACT_ExpectedComma(self,value,state,trace=False):
#        self.ACT_Expected("comma",value)

#    def ACT_ExpectedEnd(self,value,state,trace=False):
#        self.ACT_Expected("end of operands",value)

#    def ACT_ExpectedRParen(self,value,state,trace=False):
#        self.ACT_Expected("right parenthesis",value)

#    def ACT_ExpectedString(self,value,state,trace=False):
#        self.ACT_Expected("string",value)

#    def ACT_ExpectedSubString(self,value,state,trace=False):
#        self.ACT_Expected("sub-string",value)

#    def ACT_LParen(self,value,state,trace=False):
#        gs=self.scope()
##        gs.lparen(value)
#        return state.state  # Stay in this state

#    def ACT_RParen1(self,value,state,trace=False):
#        gs=self.scope()
##        gs.rparen()
#        return "subst"

#    def ACT_RParen2(self,value,state,trace=False):
#        gs=self.scope()
#        if gs._parens==0:
#            gs.st_len=gs.expr_end()
#            return "done"
#        gs.rparen()
#        return "strlen"

#    # Starting position arithmetic expression recognized
#    def ACT_Start_Done(self,value,state,trace=False):
#        gs=self.scope()
#        gs.ck_parens(value)
#        gs.st_start=gs.expr_end()
#        return "strlen"

    # Extend the initial string token with additional content
#    def ACT_String_Extend(self,value,state,trace=False):
#        gs=self.scope()
#        gs.str_cont(value)
#        return "more"

    # Initial character string recognized, need to determine if there is a substring
    # specification
#    def ACT_String_Token(self,value,state,trace=False):
#        gs=self.scope()
#        gs.str_begin(value)
#        return "more"

    # Recognized the start of a substring specification, process the start position
    # arithmetic expression.
#    def ACT_Sub_String_Start(self,value,state,trace=False):
#        return "subst"


#class CScope(asmbase.AsmFSMScope):
#    def __init__(self):
#        super().__init__()

#    def __str__(self):
#        string="%s():" % self.__class__.__name__
#        string="%s\n  st_token: %s" % (string,self.st_token)
#        string="%s\n  st_start:" % string
#        if len(self.st_start)==0:
#            string="%s []" % string
#        else:
#            for tok in self.st_start:
#                string="%s\n    %s" % (string,tok)
#        string="%s\n  st_len:" % string 
#        if len(self.st_len)==0:
#            string="%s []" % string
#        else:
#            for tok in self.st_len:
#                string="%s\n    %s" % (string,tok)
#        string="%s\n  indefn:" % string
#        if len(self._lextoks)==0:
#            string="%s []" % string
#        else:
#            for tok in self._lextoks:
#                string="%s\n    %s" % (string,tok)
#        string="%s\n  parens: %s" % (string,self._parens)
#        return string

#    def init(self):
#        super().init()
#        self.st_token=None      # langutil smart token for single quoted string
#        self.st_start=[]        # Arithmetic expression defining sub-string start
#        self.st_len=[]          # Arithmetic expression defining sub-string length        


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
        assert len(groups)==6,"%s unexpected match object groups: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),\
                    list(self.groups))
                
        self.symid=groups[0]
        subscript=groups[1]
        assert self.symid is not None,"%s symbolic variable: %s" \
             % (assembler.eloc(self,"__init__",module=this_module),self.symid)

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

    # Returns the macsyms.SymbolID object derived from the match object
    def SymID(self,case):
        if not case:
            symid=self.symid.upper()
        else:
            symid=self.symid
        if not self.subscripted:
            return macsyms.SymbolID(symid)
        if self.subscript is None:
            # Not an integer subscript, so assume symbolic variable as the subscript
            if not case:
                return macsyms.SymbolID(symid,subscript=self.subsym.upper())
            else:
                return macsyms.SymbolID(symid,subscript=self.subsym)
        # Use integer subscript
        return macsyms.SymbolID(symid,subscript=self.subscript)


class SymRefPart(seqparser.Part):
    def __init__(self,mo,name):
        super().__init__(mo,name)
        self.symmo=SymRefRepMO(mo)
        self.beg=mo.start(0)       # Beginning pos matched in string
        self.end=mo.end(0)         # Ending position matched in string

    def __str__(self):
        return "%s" % self.symmo

    # Returns an macsyms.SymbolID object for the located symbolic reference
    def SymID(self,case):
        return self.symmo.SymID(case)


class SymRefSearch(seqparser.SeqSearch):
    def __init__(self):
        # Matches: "&label",  "&label(0..9..)",   "&label(&sub)"
        #   or     "&label.", "&label(0..9..).",  "&label(&sub)."
        pattern=SymRefRepMO.pattern
        super().__init__("SymRefSrch",pattern,cls=SymRefPart) 


# Additional ASMA imports
# Because of circular dependency can not import parsers until this module is
# completely imported
import parsers              # Access parser interface

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
