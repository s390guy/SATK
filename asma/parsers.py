#!/usr/bin/python3
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

# This module manages all ASMA parsers.

this_module="%s.py" % __name__

# Python imports: None
# SATK imports: None
import fsmparser   # Access Finite-State Machine based parsers
import lexer       # Access lexical analyzers
import pratt3      # Access pratt exceptions

# ASMA imports:
import assembler   # Access assembler objects
import asmbase
import asmdcds     # Access DC/DS parser and related objects
import asmopnd     # Access the instruction operand FSM-based parser
import macopnd     # Access the macro operand FSM-based parser
import macsyms     # Access protype and statement parameter parser
import asmtokens   # Access lexical analyzer token types


# Defined lexical analyzer token types
AOPER=asmtokens.AOperType()
COMMA=asmtokens.CommaType()
DCBIN=asmtokens.DCDS_Bin_Type()
DCDPT=asmtokens.DCDS_Dec_Type()
DCHEX=asmtokens.DCDS_Hex_Type()
DCLEN=asmtokens.DCDS_Length_Type()
DCNUM=asmtokens.DCDS_Number_Type()
DCQUOTE=asmtokens.DCDS_Quote_Type()
DCSTRING=asmtokens.DCDS_String_Type()
DCTYPE=asmtokens.DCDS_Types_Type()
EOO=asmtokens.EoOperType()
EOS=asmtokens.EOSType()
LABEL=asmtokens.LabelType()
LATTR=asmtokens.LabelAttrType()
LPAREN=asmtokens.LParenType()
RPAREN=asmtokens.RParenType()
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()
STRING=asmtokens.StringType()


#
#  +----------------------------------------+
#  |                                        |
#  |   Context Sensitive Lexical Analyzer   |
#  |                                        |
#  +----------------------------------------+
#

# A single CSLA can support all context sensitive parsers by defining all of the 
# _lexical_ contexts required by the context sensitive parsers.
class CSLA(lexer.CSLA):
    def __init__(self,dm):
        self.dm=dm
        super().__init__()

    # Initialize base contexts
    # Debug manager is not used for CSLA debug settings.  They are manually
    # controlled by the call to individual context definitions.
    # Context token type match debugging is enabled by setting the tdebug argument
    # to True in the individial calls to the context types
    def init(self):
        # Debug manager is not used for CSLA debug settings.  They are manually
        # controlled by the call to individual context definitions.
        # Set ldebug=True to cause a context's token list to be displayed when the
        # debug manager has ldebug set to True.
        # Set tdebug=True to cause the token type matching debug to be enabled
        
        self.init_abs_expr()
        self.init_addr_expr()
        self.init_bin_value()
        self.init_dc_chr1()
        self.init_dc_chr2()
        self.init_dc_dcpt()
        self.init_dc_opers()
        self.init_dc_types()
        self.init_dup_beg()
        self.init_hex_value()
        self.init_len_beg()
        self.init_lenp_beg()
        self.init_lenq_beg()
        self.init_lparen()
        self.init_number_value()
        self.init_quote()
        self.init_start_region()

        # Print the tokens when the debug manager is set for ldebug
        # Token debugging is determined by 
        if self.dm.isdebug("ldebug"):
            self.types(debug=True)

        return self

    # Define the absolute expression context
    def init_abs_expr(self,ldebug=False,tdebug=False):
        c="absexpr"
        self.ctx(c,debug=ldebug)
        types=[AOPER,SDDEC,SDHEX,SDBIN,SDCHR,LABEL,LPAREN,RPAREN,COMMA,EOO]
        self.type(c,types,debug=tdebug)

    # Define an address expression context
    # The difference between this context and the 'absexpr' context is that 
    # symbol attributes are allowed.
    #
    # Should this be the default?  For now only using this with address constant
    # nominal value expressions.
    def init_addr_expr(self,ldebug=False,tdebug=False):
        c="addrexpr"
        self.ctx(c,debug=ldebug)
        types=[AOPER,SDDEC,SDHEX,SDBIN,SDCHR,LATTR,LPAREN,RPAREN,COMMA,EOO]
        self.type(c,types,debug=tdebug)

    def init_bin_value(self,ldebug=False,tdebug=False):
        c="dcbin"
        self.ctx(c,debug=ldebug)
        types=[DCBIN,COMMA,DCQUOTE]
        self.type(c,types,debug=tdebug)

    # DC/DS Operands continued
    def init_dc_opers(self,ldebug=False,tdebug=False):
        c="dccont"
        self.ctx(c,debug=ldebug)
        types=[COMMA,EOO]
        self.type(c,types,debug=tdebug)

    # DC/DS Character value initial context
    def init_dc_chr1(self,ldebug=False,tdebug=False):
        c="dcchr1"
        self.ctx(c,debug=ldebug)
        types=[DCSTRING,]
        self.type(c,types,debug=tdebug)

    # DC/DS Character value continued context
    def init_dc_chr2(self,ldebug=False,tdebug=False):
        c="dcchr2"
        self.ctx(c,debug=ldebug)
        types=[STRING,COMMA,DCQUOTE,EOO]
        self.type(c,types,debug=tdebug)

    # DC/DS Decimal Values with Optional Decimal Point
    def init_dc_dcpt(self,ldebug=False,tdebug=False):
        c="dcdpt"
        self.ctx(c,debug=ldebug)
        types=[DCDPT,COMMA,DCQUOTE]
        self.type(c,types,debug=tdebug)

    # DC/DS Type 
    def init_dc_types(self,ldebug=False,tdebug=False):
        c="dctypes"
        self.ctx(c,debug=ldebug)
        self.type(c,[DCTYPE,],debug=tdebug)

    # DC/DS Duplication expression start
    def init_dup_beg(self,ldebug=False,tdebug=False):
        c="dupbeg"
        self.ctx(c,debug=ldebug)
        types=[SDDEC,LPAREN,DCTYPE]
        self.type(c,types,debug=tdebug)

    # DC/DS Hexadecimal Value
    def init_hex_value(self,ldebug=False,tdebug=False):
        c="dchex"
        self.ctx(c,debug=ldebug)
        types=[DCHEX,COMMA,DCQUOTE]
        self.type(c,types,debug=tdebug)

    # DC/DS Start of Address nominal values
    def init_lparen(self,ldebug=False,tdebug=False):
        c="lpren"
        self.ctx(c,debug=ldebug)
        types=[LPAREN,COMMA]
        self.type(c,types,debug=tdebug)

    # DC/DS Explict Length Modifier started
    def init_len_beg(self,ldebug=False,tdebug=False):
        c="lenbeg"
        self.ctx(c,debug=ldebug)
        types=[SDDEC,LPAREN]
        self.type(c,types,debug=tdebug)

    # DC/DS Explicit Length with parenthesized values
    def init_lenp_beg(self,ldebug=False,tdebug=False):
        c="lenpbeg"
        self.ctx(c,debug=ldebug)
        types=[DCLEN,LPAREN,COMMA,EOO]
        self.type(c,types,debug=tdebug)

    # DC/DS Explicit Length with quoted values
    def init_lenq_beg(self,ldebug=False,tdebug=False):
        c="lenqbeg"
        self.ctx(c,debug=ldebug)
        types=[DCLEN,DCQUOTE,COMMA,EOO]
        self.type(c,types,debug=tdebug)

    # DC Fixed Point Numeric Values
    def init_number_value(self,ldebug=False,tdebug=False):
        c="dcnum"
        self.ctx(c,debug=ldebug)
        types=[DCNUM,COMMA,DCQUOTE]
        self.type(c,types,debug=tdebug)

    # DC start of quoted nominal values
    def init_quote(self,ldebug=False,tdebug=False):
        c="quote"
        self.ctx(c,debug=ldebug)
        types=[DCQUOTE,COMMA,EOO]
        self.type(c,types,debug=tdebug)

    # START directive region operand
    def init_start_region(self,ldebug=False,tdebug=False):
        c="region"
        self.ctx(c,debug=ldebug)
        self.type(c,[LABEL,EOO],debug=tdebug)


#
#  +-----------------------------------------------+
#  |                                               |
#  |   Shared Statement Operand Lexical Analyzer   |
#  |                                               |
#  +-----------------------------------------------+
#

# Used by END, MNOTE, TITLE and SETC SD-term Parser
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
        lst.append(AOPER)       # "+", "-", "*", "/"
        lst.append(SDBIN)       # "B'01.."
        lst.append(SDCHR)       # "C'x'", "CE'x'", "CA'x'"
        lst.append(SDHEX)       # "X'0..F..'"
        lst.append(SDDEC)       # "0..9.."
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
#  +----------------------------------+
#  |                                  |
#  |   Assembler END Operand Parser   |
#  |                                  |
#  +----------------------------------+
#

# This is specific to the END directive address calculation.
class AddressParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,scope=AddrScope,trace=False)

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

# Shared Scope for address expressions
class AddrScope(asmbase.AsmFSMScope):
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
#  +---------------------------------------------+
#  |                                             |
#  |         Self Defining Term Recognizer       |
#  |   (SETC symbol in Arithmetic Expressions)   |
#  |                                             |
#  +---------------------------------------------+
#

class SDParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,scope=SDScope,trace=False)

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
#  |   Assembler MNOTE Operand Parser   |
#  |                                    |
#  +------------------------------------+
#

class MNOTEParser(asmbase.AsmFSMParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,scope=MNOTEScope,trace=False)

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


class MNOTEScope(asmbase.AsmFSMScope):
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
#  +----------------------------+
#  |                            |
#  |   START Directive Parser   |
#  |                            |
#  +----------------------------+
#


# Syntax: [csect] START [start-expression][,[region-name]]

class START_Parser(asmbase.AsmCtxParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,"cslex",scope=START_Scope,context="loc",trace=False)
        # Note: "cslex" is used by both the START_Parser and the DCDS_Parser

    def __loc_end(self):
        gs=self.scope()
        cs=self.cscope()
        gs.start_list(cs.expr(value))

    def init_context(self):
        self.ctx("loc",lexctx="absexpr",ccls=asmbase.AsmFSMScope)
        self.ctx("region",lexctx="region")

    def initialize(self):
        init=fsmparser.PState("init")
        init.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,LABEL],self.ACT_Add_Token)
        init.action([LPAREN,],self.ACT_LPAREN)
        init.action([RPAREN,],self.ACT_RPAREN)
        init.action([EOO,EOS],self.ACT_End_Loc)
        init.action([COMMA],self.ACT_End_Loc)
        init.error(self.ACT_ExpectedExpr)
        self.state(init)

        region=fsmparser.PState("region")
        region.action([LABEL],self.ACT_Region)
        region.action([EOO,EOS],self.ACT_End)
        region.error(self.ACT_ExpectedRegion)
        self.state(region)

        end=fsmparser.PState("end")
        end.action([EOO,EOS],self.ACT_End)
        end.error(self.ACT_ExpectedEnd)
        self.state(end)

    def ACT_Add_Token(self,value,state,trace=False):
        cs=self.cscope()
        cs.token(value)
        return state.state

    def ACT_End(self,value,state,trace=False):
        state.atend()

    def ACT_End_Loc(self,value,state,trace=False):
        # Process the context scope into the global scope
        gs,cs=self.scopes()
        assert gs is not None,"global scope is None"
        #cs=self.cscope()
        assert cs is not None,"context scope is None"
        gs.start_list(cs,value)
        
        # Determine next context or whether we are in fact done
        if value.tid!="COMMA":
            state.atend()
            return

        # Otherwise we found a comma and need to parse the region name if present
        self.context("region")
        return "region"

    def ACT_ExpectedEnd(self,value,state,trace=False):
        self.ACT_Expected("end of operands or end of statement",value)

    def ACT_ExpectedExpr(self,value,state,trace=False):
        self.ACT_Expected("arithmetic operation or valid arithemtic operand",value)

    def ACT_ExpectedRegion(self,value,state,trace=False):
        self.ACT_Expected("region name",value)

    def ACT_LPAREN(self,value,state,trace=False):
        cs=self.cscope()
        cs.lparen(value)
        return "init"

    def ACT_RPAREN(self,value,state,trace=False):
        cs=self.cscope()
        cs.rparen(value)
        return "init"

    def ACT_Region(self,value,state,trace=False):
        gs=self.scope()
        gs.region(value)  # Provide the region name to the global scope
        return "end"


class START_Scope(asmbase.AsmCtxScope):
    def __init__(self):
        super().__init__()
        # Parser results
        self.region_tok=None    # region argument lexical token.  See region()
        self.expr_list=[]       # Lexical token list of expression. See start_list()
        # Pass 0 results
        self.new_region=False   # Set if a new region is requested
        self.addr_expr=None     # ArithExpr object of start address
        self.reg_name=None      # Region name.  None implies unnamed region
        self.start=0            # Default starting address for the region

    def Pass0(self,stmt,parser,debug=False):
        # Update and extract region name if specified
        self.new_region = (self.region_tok is not None) or (len(self.expr_list)>0)
        if self.new_region and self.region_tok:
            tok=self.region_tok
            # Update location from LOperands object for error reporting
            parser.ltoken_update(stmt,tok,asmstr=stmt.opnd_fld)
            self.region=tok.extract()
        else:
            self.region=None
        # Create an expression object if starting address expression specified
        if self.new_region and len(self.expr_list)>0:
            self.expr=parser.L2ArithExpr("[%s] address" % stmt.lineno,\
                stmt,ltoks=self.expr_list,debug=debug)
        else:
            self.start=0

    def start_list(self,cs,value):
        assert cs is not None,"context scope is None"
        assert cs.expr is not None,"cs.expr is None"
        self.expr_list=cs.expr(value)

    def region(self,value):
        self.region_tok=value
        self.reg_name=value.extract()


#
#  +-----------------------------+
#  |                             |
#  |   Common Parser Interface   |
#  |                             | 
#  +-----------------------------+
#

class ParserMgr(object):
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
        self.lexers["lexer"]=AsmLexer(dm).init()
        self.lexers["cslex"]=CSLA(dm).init()
        self.lexers["opnd"]=asmopnd.OperandLexer(dm).init()
        self.lexers["macs"]=macopnd.MacroCSLexer(dm).init()

    def __init_parsers(self,dm):
        # Single context FSM parsers                                   Lexer
        self.parsers["addr"]=AddressParser(dm,self)         # END     "lexer"
        self.parsers["mnote"]=MNOTEParser(dm,self)          # MNOTE   "lexer"
        self.parsers["opnd"]=asmopnd.OperandParser(dm,self) #         "opnd"
        self.parsers["mparms"]=macsyms.MacroOperands()      # asmstmts.MacroStmt
        self.parsers["mproto"]=macsyms.ProtoParser()        # asmstmts.MacroProto
        self.parsers["sdterm"]=SDParser(dm,self)            #         "lexer"

        # Context sensitive FSM parsers
        self.parsers["dcds"]=asmdcds.DCDS_Parser(dm,self)   # DC/DS   "cslex"
        self.parsers["mopnd"]=macopnd.MacroParser(dm,self)  #         "macs"
        self.parsers["start"]=START_Parser(dm,self)         # START   "cslex"

    def __parse(self,parser,string,scope=None):
        if isinstance(parser,str):
            try:
                fsmp=self.parsers[parser]
            except KeyError:
                raise ValueError("%s undefined parser: '%s'"\
                    % (assembler.eloc(self,"__parse",module=this_module),parser))
        else:
            fsmp=parser
        #print("%s parser: %s" \
        #    % (assembler.eloc(self,"__parse",module=this_module),fsmp))

        # This may raise an AsmParserError that should be caught by the caller.
        return fsmp.parse(string,scope=scope)

    def evaluate_expr(self,asm,stmt,expr,debug=False,trace=False):
        try:
            return expr.evaluate(external=asm,debug=debug,trace=False)
        except pratt3.PParserError as pe:
            # Convert PParserError into an AssemblerError.  The PParserError object
            # may contain an object generated by the PParser object without a
            # source.  Before using the src for the AssemblerError we need to 
            # make sure it is valid.  If all else fails, simply convert the
            # ptok to a printable string and use whatever results.
            raise assembler.AssemblerError(line=stmt.lineno,linepos=pe.pos,msg=pe.msg) \
                from None
        except assembler.LabelError as le:
            # Convert LabelError into an AssemblerError
            raise assembler.AssemblerError(line=stmt.lineno,linepos=le.ltok.linepos,\
                msg=le.msg) from None

    def init(self):
        dm=self.asm.dm
        self.__init_lexers(dm)
        self.__init_parsers(dm)
        return self

    # Creates an asmtokens.ArithExpr object from a list of lexical token objects
    def L2ArithExpr(self,desc,stmt,ltoks=[],debug=False):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.logline.operpos()

        # Note: for some unexplained reason, if left to default, tokens picks up
        # the list from the previous expr.  Force the argument to be empty
        expr=asmtokens.ArithExpr(desc,lineno,tokens=[])
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

    # Update a lexical token with its actual position in the statement.
    # Users of the parser are encouraged to use this method rather than 
    def ltoken_update(self,stmt,ltok,asmstr=None):
        assert isinstance(asmstr,asmbase.ASMString),\
            "%s 'asmstr' argument must be an instance of asmbase.ASMString: %s" \
                 % (assembler.eloc(self,"ltoken_update",module=this_module),asmstr)

        loc=asmstr.ndx2loc(ltok.linepos)
        ltok.update_loc(stmt.lineno,loc)

    # This provides direct access to the macro parser for conditional branch
    # operand recognition.  It is used to recognize the computed vs. unconditional
    # AGO first operand.  This is simply an wrapper providing access to the
    # MacroParser object's parse_ago() method.
    # Exception:
    #   AsmParserError from MacroParser if parse fails
    def parse_ago(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_cbranch",module=this_module),\
                        debug))

        parser=self.__fetch_parser("mopnd")
        return parser.parse_ago(stmt,field,debug=debug)

    # This provides direct access to the macro parser to validate symbolic variable
    # references in the label field for various instructions.
    # Exception:
    #   AsmParserError from MacroParser if parse fails
    def parse_label(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_label",module=this_module),debug))

        parser=self.__fetch_parser("mopnd")
        return parser.parse_symbol(stmt,field,debug=debug)

    # This provides direct access to the macro parser to validate symbolic variable
    # references in the label field for various instructions.
    # Exception:
    #   AsmParserError from MacroParser if parse fails
    def parse_model(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_model",module=this_module),debug))

        parser=self.__fetch_parser("mopnd")
        return parser.parse_model(stmt,field,debug=debug)

    # This provides direct access to the macro parser to validate an operand
    # using a specific control state name.  This allows statement control over
    # individual operand parsing.
    # Exception:
    #   AsmParserError from MacroParser if parse fails
    def parse_operand(self,stmt,field,mpname,debug=False):
        parser=self.__fetch_parser("mopnd")
        return parser.parse_operand(stmt,field,mpname,debug=debug)

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
    #   assembler.AsmParserError object if available.
    def parse_operands(self,stmt,parser,scope=None,required=False):
        # If the parse is for operands then the source and string positions
        # are different than if this is a statement field parse using an FSM-based
        # parser

        opnd=stmt.opnd_fld
        if opnd is not None:
            loc=opnd.start()
            source=loc.source
            string=opnd.text
            operpos=loc.pndx
        else:
            source=stmt.logline.source
            string=None

        # Only parse operands if they are actually present in the statement
        if string is None:
            if required: 
                raise assembler.AssemblerError(source=source,line=stmt.lineno,\
                    msg="%s operation required operand field missing" % stmt.instu)
            else:
                return None

        try:
            # Returns a asmfsmbp.xxxScope object
            return self.__parse(parser,string,scope=scope)
        except assembler.AsmParserError as ape:
            #raise assembler.AssemblerError(source=source,line=stmt.lineno,\
            #    linepos=ape.token.linepos+flds.operpos+1,msg=ape.msg) from None
            raise assembler.AssemblerError(source=source,line=stmt.lineno,\
                msg=ape.msg) from None

    # This is equivalent to parse_operands() but always returns a scope object.
    # unless an assembler.AssemblerError is raised.
    def parse_scope(self,stmt,parser,scope=None,required=False):
        prsr=self.__fetch_parser(parser)

        if stmt.opnd_fld:
            string=stmt.opnd_fld.text
        else:
            string=None

        if scope is not None:
            scp=scope
        else:
            scp=prsr._init_scope(scope=None)

        scp.statement(stmt)  # Tell the scope what statement is being parsed

        if string is None:
            if required:
                raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                    msg="required operand field missing")
            else:
                return scp

        # There are operands to parse...
        try:
            # Returns a likely subclassed asmfsmbp.AsmFSMScope object
            return self.__parse(prsr,string,scope=scp)
        except assembler.AsmParserError as ape:
            lpos=stmt.opnd_fld.ndx2loc(ape.token.linepos)
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                linepos=lpos.pndx,msg=ape.msg) from None


    # Parses a string for a self-defining term.  Used when treating a macro
    # character symbol as a term in arithmetic expressions or type attribute
    # resolution.
    def parse_sdterm(self,string):
        return self.__parse("sdterm",string)

    # Parser a list of operands separated when the operation type has sep=True.
    # Method Arguments:
    #   stmt    ASMStmt object whose operand is being parsed
    #   parser  Parser id from ASMOper object of the statement's operation
    # Returns:
    #   A list of objects corresponding to the parsed separated operand
    #     Parser 'opnd' returns ASMOperand objects
    # Exception:
    #   AsmParserError   when an error is detected by the parser
    def parse_sep(self,stmt,debug=False):
        parser=self.__fetch_parser(stmt.get_Operand_Parser())
        if __debug__:
            if debug:
                print("%s parser: %s" \
                    % (assembler.eloc(self,"parse_sep",module=this_module),parser))

        result=parser.parse_operands(stmt,debug=debug)
        if __debug__:
            if debug:
                print("%s result: %s" \
                    % (assembler.eloc(self,"parse_sep",module=this_module),result))

        return result

    # This provides direct access to the macro parser to validate symbolic variable
    # references in the label field for various instructions.
    # Exception:
    #   AsmParserError from MacroParser if parse fails
    def parse_seqsym(self,stmt,field,debug=False):
        if __debug__:
            if debug:
                print("%s debug: %s" \
                    % (assembler.eloc(self,"parse_model",module=this_module),debug))

        parser=self.__fetch_parser("mopnd")
        return parser.parse_seqsym(stmt,field,debug=debug)

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
    raise NotImplementedError("%s - this module only supports import usage" \
        % this_module)