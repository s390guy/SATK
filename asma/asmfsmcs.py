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

# This module provides all ASMA finite-state machine context-sesitive parsers for
# ASMA assembler directives and machine instructions.  

# Long-term this module will replace asmparsers.py eliminating LL1 parser technology
# and the more limited pratt.py module use.

this_module="asmfsmcs.py"

# Python imports: None
# SATK imports:
import fsmparser      # Access Finite-State Machine based parsers
import lexer          # Access lexical analyzers

# ASMA imports:
import assembler      # Access assembler shared objects and exceptions
import asmdcds        # Access DC/DS directive processing support
import asmtokens      # Access the common lexical tokens and parsing related objects


class DCDS_Bin_Token(asmtokens.LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Bin_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[01]+"
        super().__init__("DCBIN",pattern,tcls=DCDS_Bin_Token,debug=debug)

class DCDS_Dec_Token(asmtokens.LexicalToken):
    signs={"U":1,"+":1,"-":-1,None:1}
    def __init__(self):
        super().__init__()
        # Set by convert() method
        self.unsigned=None
        self._sign=None
        self.value=None

    def convert(self):
        groups=self.groups()

        # Recognize the sign of the value
        sign=self.sign()
        if sign=="U":
            self.unsigned=True
        try:
            self._sign=sign=DCDS_Dec_Token.signs[sign]
        except KeyError:
            raise ValueError("%s unrecognized sign matched in re pattern: %s" \
                % (assembler.eloc(self,"convert",module=this_module),sign))

        # Determine the digits in the value
        self.digits=self.dec_digits()

        # Convert to a Python value
        self.value=int(self.digits,10)*sign
        return self.value

    def dec_digits(self):
        groups=self.groups()
        fraction=groups[2]   # Fractional part of value with decimal point
        if fraction is not None:
            fraction=fraction[1:]     # drop off decimal point
        else:
            fraction=""    # No fractional part supplied
        return "%s%s" % (groups[1],fraction)

    def sign(self):
        sign=self.groups()[0]
        if sign:
            return sign.upper()
        return None

class DCDS_Dec_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern=r'([Uu+-])?([0-9]+)(\.[0-9]*)?'
        super().__init__("DCDPT",pattern,tcls=DCDS_Dec_Token,mo=True,debug=debug)

class DCDS_Hex_Token(asmtokens.LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Hex_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[0-9A-Fa-f]+"
        super().__init__("DCHEX",pattern,tcls=DCDS_Hex_Token,debug=debug)

class DCDS_Length_Token(asmtokens.LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Length_Type(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("DCLEN","[Ll]",tcls=DCDS_Length_Token,debug=debug)

class DCDS_Number_Token(asmtokens.LexicalToken):
    signs={"U":1,"+":1,"-":-1,None:1}
    def __init__(self):
        super().__init__()
        # Set by convert() method
        self.unsigned=None
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

class DCDS_Quote_Token(asmtokens.LexicalToken):
    def __init__(self):
        super().__init__()

class DCDS_Quote_Type(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("DCQUOTE","'",tcls=DCDS_Quote_Token,debug=debug)

class DCDS_String_Token(asmtokens.StringToken):
    def __init__(self):
        super().__init__()
        # Because this token type uses a different pattern we do not need to drop
        # the initial quote.  The pattern used here already excludes the initial quote.
        self.drop=False  # Affects asmtokens.StringToken.init() method

class DCDS_String_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[^']*'"  # everything upto and including the next single quote
        super().__init__("DCSTR",pattern,tcls=DCDS_String_Token,debug=debug)

class DCDS_Type_Token(asmtokens.LexicalToken):
    def __init__(self):
        super().__init__()
    
class DCDS_Types_Type(lexer.Type):
    def __init__(self,debug=False):
        pattern="[Aa][Dd]?|[Bb]|[Cc][AaEe]?|[Dd]|[Ff][Dd]?|[Hh]|[Pp]"
        pattern="%s|%s" % (pattern,"[Ss]|[Xx]|[Yy]|[Zz]")
        super().__init__("DCTYPE",pattern,tcls=DCDS_Type_Token,debug=debug)

# Defined lexical analyzer token types
AOPER=asmtokens.AOperType()
COMMA=asmtokens.CommaType()
DCBIN=DCDS_Bin_Type()
DCDPT=DCDS_Dec_Type()
DCHEX=DCDS_Hex_Type()
DCLEN=DCDS_Length_Type()
DCNUM=DCDS_Number_Type()
DCQUOTE=DCDS_Quote_Type()
DCSTRING=DCDS_String_Type()
DCTYPE=DCDS_Types_Type()
EOO=asmtokens.EoOperType()
EOS=lexer.EOSType()
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
#  +---------------------------------------------------+
#  |                                                   |
#  |   Base Assembler Context Sensitive Global Scope   |
#  |                                                   |
#  +---------------------------------------------------+
#

class AsmCtxScope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
        
        # The statements operation field in upper case.
        self.stmt_inst=None  # See the statement() method
        
    def statement(self,stmt):
        assert isinstance(stmt,assembler.Stmt),\
            "%s 'stmt' argument must be an assembler.Stmt object: %s" \
                % (assembler.eloc(self,"statement",module=this_module),stmt)

        self.stmt_inst=stmt.instu   # The statement in upper case
    

#
#  +-----------------------------------------------------------+
#  |                                                           |
#  |   Base Assembler Context Sensitive Syntactical Analyzer   |
#  |                                                           |
#  +-----------------------------------------------------------+
#

# This is an adaptation of asmfsmbp.py AsmFSMParser for the use of context sensitive
# parsers.
#
# Instance Arguments:
#   dm        The debug manager object in use
#   scope     The global scope class used by the parser.  Defaults to 
#   init      The initial FSM parser state.  Defaults to 'init'
#   context   The initial context.  Defaults to 'init'
#   external  External helper object supplied to the parser.  Defaults to None
#   trace     Specify True to enable tracing of the finite state machine.  
#             Defaults to False (no tracing)
class AsmCtxParser(fsmparser.FSMContext):
    csla=None     # Built during first instantiation
    def __init__(self,dm,scope=asmtokens.AsmFSMScope,init="init",context="init",\
                 external=None,trace=False):
        if AsmCtxParser.csla:
            lex=AsmCtxParser.csla
        else:
            AsmCtxParser.csla=lex=CSLA(dm)

        super().__init__(lex,scls=scope,external=external,init=init,context=context,\
                         trace=trace)

        self.init_ctx=context # Initial context when starting a parse
        self.init_context()   # Initialize the parser contexts
        self.initialize()     # Initialize the finite-state machine

    # This overrides the semantics of the super class fmsparser.FSMParser
    # _init_scope() method by reversing the priority.  It returns:
    #    1. the provided scope in the scope argument
    # or 2. A new object initialized by the super class 
    def _init_scope(self,scope=None):
        if scope is not None:
            return scope
        return super()._init_scope(scope)

    # This override changes the default context scope class to asmtokens.AsmFSMScope
    # rather than the more generic fsmparser.PScope
    def ctx(self,name,lexctx=None,ccls=AsmCtxScope):
        super().ctx(name,lexctx=lexctx,ccls=ccls)

    # This method uses the super class ctx() method to register defined contexts.
    def init_context(self):
        cls_str=assembler.eloc(self,"initialize",module=this_module)
        raise NotImplementedError("%s subclass %s must provide initialize() method" \
            % (cls_str,self.__class__.__name__))

    # This method uses the super class state() method to register defined states
    def initialize(self):
        cls_str=assembler.eloc(self,"initialize",module=this_module)
        raise NotImplementedError("%s subclass %s must provide initialize() method" \
            % (cls_str,self.__class__.__name__))

    def ACT_Expected(self,expected,value,found=None):
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

#
#  +----------------------------+
#  |                            |
#  |   DC/DS Directive Parser   |
#  |                            |
#  +----------------------------+
#

# Syntax: [label] DC [dup]<atype>[L<length>](<avalue[,avalue...]>)[,another type...]
#     or  [label] DC [dup]<ctype>[L<length>]'characters'
#     or  [label] DC [dup]<ntype>[L<length>]'<value[,value...]>'[,another type...]
#     or  [label] DS [dup]<atype>[L<length>][(<avalue[,avalue...]>][,another type...]
#     or  [label] DS [dup]<ctype>[L<length>]['characters']
#     or  [label] DS [dup]<ntype>[L<length>]['<value[,value...]>'][,another type...]
#
# valid values are determined by the nature of the type:
#   <atype> is an address value consisting of an address expression
#   <ctype> is a character value of characters using single or double quotes/ampersands
#   <ntype> is a numeric value consisting of an arithmetic expression
# values are optional for DS directives, but if present must be validly recognized.
# In all cases at least one operand is required.

class DCDS_Parser(AsmCtxParser):
    def __init__(self,dm):
        super().__init__(dm,scope=DCDS_Scope,context="dup",init="dup",trace=False)

        # Dictionary of supported constant types
        self.types={}
        self.__init_constants()

    # common routine for completing an address nominal value expression.
    def __address_nominal_done(self,gs,cs,value,trace=False):
        expr=cs.expr(value)
        # Returned so the expression is good - this means we are at the end
        # of the last address expression of nominal values

        if __debug__:
            if trace:
                cls="%s.__address_nominal_done()" % self.__class__.__name__
                print("%s: expr: %s" % (cls,expr))

        if not len(expr):
             # Expression token list empty
             self.ACT_Expected_Address_Expression(value,state,trace=trace)
             # We do not return from this method

        if __debug__:
            if trace:
                print("%s updating gs.operand with expr" % cls)

        gs.operand.nominal(expr)

    # Define an individual constant type
    def __constant(self,cnst):
        assert isinstance(cnst,DCDS_Constant),\
            "%s 'cnst' argument must be a DCDS_Constant object: %s" \
                % (assembler.eloc(self,"__constant",module=this_module),cnst)

        # Define the type if it has not already been defined
        try:
            self.types[cnst.typ]
            raise ValueError("%s constant type already defined: %s" \
                % (assembler.eloc(self,"__constant",module=this_module),cnst.typ))
        except KeyError:
            pass
        self.types[cnst.typ]=cnst

    # Initialize all of the constant types
    # Note: these must be consistant with the pattern defined by the 
    # class DCDS_Types_Type.
    def __init_constants(self):
        c=DCDS_Constant   # This is just a typing convenience.

        #             nominal      len      len    nom     nom       val       val
        #    TYPE      class       state    CTX   state    ctx      state      ctx
        A= c("A", asmdcds.DC_A, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        AD=c("AD",asmdcds.DC_AD,("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        B= c("B", asmdcds.DC_B, ("lengthq","lqb"),("nomq","quote"),("binvals","dcbin"))
        C= c("C", asmdcds.DC_C, ("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        CA=c("CA",asmdcds.DC_CA,("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        CE=c("CE",asmdcds.DC_CE,("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        D= c("D", asmdcds.DC_D, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        F= c("F", asmdcds.DC_F, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        FD=c("FD",asmdcds.DC_FD,("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        H= c("H", asmdcds.DC_H, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        P= c("P", asmdcds.DC_P, ("lengthq","lqb"),("nomq","quote"),("dpvals", "dcdpt"))
        S= c("S", asmdcds.DC_S, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        X= c("X", asmdcds.DC_X, ("lengthq","lqb"),("nomq","quote"),("hexvals","dchex"))
        Y= c("Y", asmdcds.DC_Y, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        Z= c("Z", asmdcds.DC_Z, ("lengthq","lqb"),("nomq","quote"),("dpvals", "dcdpt"))
        self.__constant(A)
        self.__constant(AD)
        self.__constant(B)
        self.__constant(C)
        self.__constant(CA)
        self.__constant(CE)
        self.__constant(D)
        self.__constant(F)
        self.__constant(FD)
        self.__constant(H)
        self.__constant(P)
        self.__constant(S)
        self.__constant(X)
        self.__constant(Y)
        self.__constant(Z)

    # Initialize the lexical contexts used by the parser.
    def init_context(self):
        self.ctx("addr",   lexctx="addrexpr",ccls=asmtokens.AsmFSMScope)
        #self.ctx("addradj",lexctx="addradj", ccls=asmtokens.AsmFSMScope)
        self.ctx("dcnum",  lexctx="dcnum",   ccls=asmtokens.AsmFSMScope)
        self.ctx("dup",    lexctx="dupbeg",  ccls=asmtokens.AsmFSMScope)
        self.ctx("dupexpr",lexctx="absexpr", ccls=asmtokens.AsmFSMScope)
        self.ctx("dcbin",  lexctx="dcbin",   ccls=asmtokens.AsmFSMScope)
        self.ctx("dcchr1", lexctx="dcchr1",  ccls=asmtokens.AsmFSMScope)
        self.ctx("dcchr2", lexctx="dcchr2",  ccls=asmtokens.AsmFSMScope)
        self.ctx("dcdpt",  lexctx="dcdpt",   ccls=asmtokens.AsmFSMScope)
        self.ctx("dchex",  lexctx="dchex",   ccls=asmtokens.AsmFSMScope)
        self.ctx("type",   lexctx="dctypes", ccls=asmtokens.AsmFSMScope)
        self.ctx("lpb",    lexctx="lenpbeg", ccls=asmtokens.AsmFSMScope)
        self.ctx("lqb",    lexctx="lenqbeg", ccls=asmtokens.AsmFSMScope)
        self.ctx("length", lexctx="lenbeg",  ccls=asmtokens.AsmFSMScope)
        self.ctx("lenexpr",lexctx="absexpr", ccls=asmtokens.AsmFSMScope)
        self.ctx("lpren",  lexctx="lpren",   ccls=asmtokens.AsmFSMScope)
        self.ctx("opernxt",lexctx="dccont",  ccls=asmtokens.AsmFSMScope)
        self.ctx("quote",  lexctx="quote",   ccls=asmtokens.AsmFSMScope)

    def initialize(self):
        # Looks for duplication factor as a self-defining term or parenthesized 
        # expression
        dup=fsmparser.PState("dup")
        dup.action([SDDEC,],self.ACT_Dup_SD_found)
        dup.action([LPAREN,],self.ACT_Dup_Expr_Start)
        dup.action([DCTYPE,],self.ACT_DC_Type)    # No duplication.
        dup.error(self.ACT_Expected_Dup)
        self.state(dup)

        # Completes the duplication factor parenthesized expression
        dup_expr=fsmparser.PState("dupexpr")
        dup_expr.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,LABEL],self.ACT_Add_Token)
        dup_expr.action([LPAREN,],self.ACT_LPAREN)
        dup_expr.action([RPAREN,],self.ACT_Dup_RPAREN)
        dup_expr.error(self.ACT_Expected_Dup_Expr)
        self.state(dup_expr)

        # Recognizes a constant type.
        typ=fsmparser.PState("type")
        typ.action([DCTYPE,],self.ACT_DC_Type)
        typ.error(self.ACT_Expected_Type)
        self.state(typ)

        # Recognize explicit length with parenthesized values
        lengthp=fsmparser.PState("lengthp")
        lengthp.action([DCLEN,],self.ACT_Len_Found)        # Explicit length
        lengthp.action([LPAREN,],self.ACT_Addr_Begin)      # Start of nominal values
        lengthp.action([COMMA,],self.ACT_Addr_NotStarted)  # No length and no values
        lengthp.action([EOO,EOS,],self.ACT_Operand_Done)   # No length or values (DS?)
        lengthp.error(self.ACT_Expected_Len)
        self.state(lengthp)

        # Recognize explicit length with quoted values
        lengthq=fsmparser.PState("lengthq")
        lengthq.action([DCLEN,],self.ACT_Len_Found)        # Explicit length
        lengthq.action([DCQUOTE,],self.ACT_Value_Started)  # Start of nominal values
        lengthq.action([COMMA,],self.ACT_Value_NotStarted) # No length and no values
        lengthq.action([EOO,EOS,],self.ACT_Operand_Done)   # No length or values (DS?)
        lengthq.error(self.ACT_Expected_Len)
        self.state(lengthq)

        # Recognize the length modifers value (decimal SD term or expression)
        length=fsmparser.PState("length")
        length.action([SDDEC,],self.ACT_Len_SD_Found)     # Length SD found
        length.action([LPAREN,],self.ACT_Len_Expr_Start)  # Length expression found
        length.error(self.ACT_Expected_Length)
        self.state(length)

        # Recognize a length modifier's expression.
        len_expr=fsmparser.PState("lenexpr")
        len_expr.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,LABEL],self.ACT_Add_Token)
        len_expr.action([LPAREN,],self.ACT_LPAREN)
        len_expr.action([RPAREN,],self.ACT_Len_RPAREN)
        len_expr.error(self.ACT_Expected_Len_Expr)
        self.state(len_expr)
        
        # Recognizes start of nominal values by a single left parenthesis following 
        # modifiers
        nomp=fsmparser.PState("nomp")
        nomp.action([LPAREN,],self.ACT_Addr_Begin)
        nomp.action([COMMA,EOO,EOS],self.ACT_Addr_NotStarted)
        nomp.error(self.ACT_Expected_Address_Values)
        self.state(nomp)
        
        # Recognizes start of nominal values by a single quote following modifiers
        nomq=fsmparser.PState("nomq")
        nomq.action([DCQUOTE,],self.ACT_Value_Started)
        nomq.action([COMMA,EOO,EOS],self.ACT_Value_NotStarted)
        nomq.error(self.ACT_Expected_Quoted_Values)
        self.state(nomq)

        # Determine whether another operand is present or the DC/DS diretive is done
        opers=fsmparser.PState("opers")
        opers.action([COMMA,],self.ACT_Operand_Next)
        opers.action([EOO,EOS],self.ACT_DCDS_Done)
        opers.error(self.ACT_Expected_DCDS_Done)
        self.state(opers)

        #
        # Nominal Value States
        #

        # Type A, AD, S, Y - Recognizes address expressions as nominal value
        # Expression left-hand side values
        #                                                          Next State
        adrvals=fsmparser.PState("adrvals")
        adrvals.action([LPAREN,],self.ACT_Addr_LPAREN)            #  vals
        adrvals.action([LATTR,SDBIN,SDHEX,SDCHR,SDDEC],self.ACT_Addr_RHand) #  infix
        adrvals.action([AOPER,],self.ACT_Addr_Unary)              #  +/-=vals, *=infix
        adrvals.error(self.ACT_Expected_Addr_Operand)
        self.state(adrvals)

        # Type A, AD, S, Y - Recognizes address expressions as nominal value
        # Expecting an infix operator in the expression
        adrinfix=fsmparser.PState("adrinfix")
        adrinfix.action([AOPER],self.ACT_Addr_Infix)              # vals
        adrinfix.action([RPAREN,],self.ACT_Addr_RPAREN)           # infix
        adrinfix.action([COMMA,],self.ACT_Addr_Value_Done)        # vals
        adrinfix.error(self.ACT_Expected_Addr_Operator)
        self.state(adrinfix)

        # Type B - Recognizes binary nominal values
        binvals=fsmparser.PState("binvals")
        binvals.action([DCBIN,],self.ACT_Binary_Value)
        binvals.error(self.ACT_Expected_Hexadecimal_Value)
        self.state(binvals)

        # Type B - Recognizes whether another nominal value or the operand is done
        binnext=fsmparser.PState("binnext")
        binnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes conext
        binnext.action([COMMA,],self.ACT_Binary_Another)
        binnext.error(self.ACT_Expected_More_Values)
        self.state(binnext)

        # Type C, CA, CE - Recognizes start of a character string
        chrvals=fsmparser.PState("chrvals")
        chrvals.action([DCSTRING,],self.ACT_String_Value_Start)
        chrvals.error(self.ACT_Expected_String_Value)
        self.state(chrvals)

        # Type C, CA, CE - Recognizes more of string after second quote
        chrvals2=fsmparser.PState("chrvals2")
        chrvals2.action([STRING,],self.ACT_String_Value_Cont)
        chrvals2.action([COMMA,EOO,EOS],self.ACT_String_Value_Done)
        chrvals2.error(self.ACT_Expected_More_String)
        self.state(chrvals2)

        # Types P,Z - Recognizes decimal pointed nominal values
        dpvals=fsmparser.PState("dpvals")
        dpvals.action([DCDPT,],self.ACT_DecimalPt_Value)
        dpvals.error(self.ACT_Expected_DecimalPt_Value)
        self.state(dpvals)

        # Types P,Z - Recognizes whether another nominal value or the operand is done
        dpnext=fsmparser.PState("dpnext")
        dpnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes conext
        dpnext.action([COMMA,],self.ACT_DecimalPt_Another)
        dpnext.error(self.ACT_Expected_More_Values)
        self.state(dpnext)

        # Type X - Recognizes hexadecimal nominal values
        hexvals=fsmparser.PState("hexvals")
        hexvals.action([DCHEX,],self.ACT_Hexadecimal_Value)
        hexvals.error(self.ACT_Expected_Hexadecimal_Value)
        self.state(hexvals)

        # Type X - Recognizes whether another nominal value or the operand is done
        hexnext=fsmparser.PState("hexnext")
        hexnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes conext
        hexnext.action([COMMA,],self.ACT_Hexadecimal_Another)
        hexnext.error(self.ACT_Expected_More_Values)
        self.state(hexnext)

        # Types D, F, FD, H - Recognizes a fixed point numeric nominal value
        numvals=fsmparser.PState("numvals")
        numvals.action([DCNUM],self.ACT_Fixed_Point_Value)
        numvals.error(self.ACT_Expected_Fixed_Point_Value)
        self.state(numvals)

        # Types D, F, FD, H - Recognizes whether another nominal value or done.
        numnext=fsmparser.PState("numnext")
        numnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes conext
        numnext.action([COMMA,],self.ACT_Fixed_Point_Another)
        numnext.error(self.ACT_Expected_More_Values)
        self.state(numnext)

    # Add an expression operation or operand to the current context scope
    def ACT_Add_Token(self,value,state,trace=False):
        cs=self.cscope()
        cs.token(value)
        return self.current()    # Stay in this state


    #
    # Address Type Nominal Value Processing
    #

    # This state entered when the presence of parenthesis surrounded values are being
    # recognized.  The initial ( has already been consumed.  It sets the context
    # for nominal value recognition.
    def ACT_Addr_Begin(self,value,state,trace=False):
        gs=self.scope()
        constant=gs.operand.typ         # Get the type's DCDS_Constant object
        self.context(constant.val_ctx)  # Set the lexical context for these values
        return constant.val_state       # Set the FSM state for their recognition.

    # An infix operator recognized.  Simply add it to list of expression tokens and
    # continue looking for the operator's right-hand operand.
    def ACT_Addr_Infix(self,value,state,trace=False):
        cs=self.cscope()
        cs.token(value)   # Add it to the expression
        return "adrvals"  # Look for the infix operator's right hand value

    # A left-parenthesis found while expecting an expression operand.  Still looking
    # for the operand after the left-parenthesis is recognized.
    def ACT_Addr_LPAREN(self,value,state,trace=False):
        cs=self.cscope()
        cs.lparen(value)   # Add it to the expression
        return "adrvals"

    def ACT_Addr_NotStarted(self,value,state,trace=False):
        gs=self.scope()
        if gs.stmt_inst=="DS":
            return self.ACT_Operand_Done(value,state,trace=trace)
        self.ACT_Expected_Address_Values(value,state,trace=trace)


    # Right-Hand expression operand found
    def ACT_Addr_RHand(self,value,state,trace=False):
        cs=self.cscope()
        cs.token(value)
        return "adrinfix"  # Look for infix operator now

    # Right parenthesis found.  It will either match a previous left-parenthesis
    # or signal the end of the address type DC operand.
    def ACT_Addr_RPAREN(self,value,state,trace=False):
        gs,cs=self.scopes()
        if cs._parens:
            # Need to match a previous left parenthesis
            cs.rparen(value)
            return "adrinfix"
        # No left parenthesis to match, so this signals the end of the address
        # type nominal value and the end of the DC directive itself
        self.__address_nominal_done(gs,cs,value,trace=trace)
        return self.ACT_Operand_Done(value,state,trace=trace)
        # The parser returns to the state needed to recognize another operand

    # Found either a unary operator or the current location counter.  The lexical
    # token (AOPER) recognizes '+', '-', '*' and '/'.  This action figures out
    # which it is.  If it is the current location counter.  The lexical token will
    # have a flag set causing the pratt token for the current location counter to be
    # generated rather than the normal pratt token that performs multiplication.
    def ACT_Addr_Unary(self,value,state,trace=False):
        cs=self.cscope()
        if value.string in "+-":
            cs.token(value)
            return "adrvals"      # Found the unary operator now seek its right hand
        elif value.string=="*":
            value.iscur=True       # Make sure the correct pratt token is generated
            cs.token(value)
            # Found the right hand (current address) seek an infix operator now
            return "adrinfix"
        # This only happens if the division operator is recognized by AOPER.
        self.ACT_Expected("unary operator or current location counter",value)

    # The address type nominal value is done (signaled by a comma) and we need
    # to process the next value.
    def ACT_Addr_Value_Done(self,value,state,trace=False):
        gs,cs=self.scopes()
        self.__address_nominal_done(gs,cs,value,trace=trace)
        return "adrvals"

    def ACT_Binary_Another(self,value,state,trace=False):
        return "binvals"

    def ACT_Binary_Value(self,value,state,trace=False):
        gs=self.scope()
        gs.operand.nominal(value)
        return "binnext"

    def ACT_DC_Type(self,value,state,trace=False):
        gs=self.scope()
        operand=gs.operand
        assert operand is not None,\
            "%s global scope operand is None" \
                % assembler.eloc(self,"ACT_DC_Type",module=this_module)

        try:
            t=self.types[value.string.upper()]
        except KeyError:
            raise ValueError("%s undefined constant type recognized by lexer: %s" \
                % (assembler.eloc(self,"ACT_DC_Type",module=this_module),value))
        if __debug__:
            if trace:
                print("ACT_DC_Type constant: %s" % t)
        operand.dc_type(value,t)
        
        self.context(t.len_ctx)  # Lexical context changes for length modifier
        return t.len_state       # Start looking for length modifier

    def ACT_DCDS_Done(self,value,state,trace=False):
        state.atend()

    def ACT_DecimalPt_Another(self,value,state,trace=False):
        return "dpvals"

    def ACT_DecimalPt_Value(self,value,state,trace=False):
        gs=self.scope()
        gs.operand.nominal(value)
        return "dpnext"

    def ACT_Dup_Expr_Start(self,value,state,trace=False):
        self.context("dupexpr")  # Change to lexical absolute expression context
        return "dupexpr"

    def ACT_Dup_RPAREN(self,value,state,trace=False):
        gs,cs=self.scopes()
        if cs._parens==0:
            # Must be the terminating RPAREN matching the beginning LPAREN
            gs.operand.dup_expr(cs)
            self.context("type")
            return "type"        # Looking for the type no
        # Just a matching right parenthesis of the expression
        cs.rparen(value)
        return self.current()    # Stay in the current state

    def ACT_Dup_SD_found(self,value,state,trace=False):
        gs,cs=self.scopes()
        cs.token(value)
        gs.operand.dup_expr(cs)
        self.context("type")
        return "type"

    def ACT_Expected_Address_Base(self,value,state,trace=False):
        self.ACT_Expected("initial address expression symbol",value)

    def ACT_Expected_Address_Expression(self,value,state,trace=False):
        self.ACT_Expected(\
            "address expression arithmetic operation or operand",value)

    def ACT_Expected_Addr_Operand(self,value,state,trace=False):
        self.ACT_Expected("address, self-defining term, or left parenthesis",value)

    def ACT_Expected_Addr_Operator(self,value,state,trace=False):
        self.ACT_Expected("address, self-defining term, or left parenthesis",value)

    def ACT_Expected_Address_Values(self,value,state,trace=False):
        self.ACT_Expected("start of address values",value)

    def ACT_Expected_Binary_Value(self,value,state,trace=False):
        self.ACT_Expected("binary nominal value",value)

    def ACT_Expected_DCDS_Done(self,value,state,trace=False):
        self.ACT_Expected("end of DC or DS directive",value)

    def ACT_Expected_DecimalPt_Value(self,value,state,trace=False):
        self.ACT_Expected("decimal nominal value",value)

    def ACT_Expected_Dup(self,value,state,trace=False):
        self.ACT_Expected("duplication factor",value)

    def ACT_Expected_Dup_Expr(self,value,state,trace=False):
        self.ACT_Exprected(\
            "duplication modifier arithmetic operation or operand",value)

    def ACT_Expected_Fixed_Point_Value(self,value,state,trace=False):
        self.ACT_Expected("fixed point nominal value",value)

    def ACT_Expected_Hexadecimal_Value(self,value,state,trace=False):
        self.ACT_Expected("hexadecimal nominal value",value)

    def ACT_Expected_Len(self,value,state,trace=False):
        self.ACT_Expected("constant length",value)

    def ACT_Expected_Len_Expr(self,value,state,trace=False):
        self.ACT_Exprected(\
            "length modifier arithmetic operation or valid operand",value)

    def ACT_Expected_Length(self,value,state,trace=False):
        self.ACT_Expected(\
            "decimal self-defining term or parenthesized expression",value)
        
    def ACT_Expected_More_String(self,value,state,trace=False):
        self.ACT_Expected("continuation of character constant",value)
        
    def ACT_Expected_More_Values(self,value,state,trace=False):
        self.ACT_Expected("another value signaled by a comma",value)
        
    def ACT_Expected_Quoted_Values(self,value,state,trace=False):
        self.ACT_Expected("nominal values signaled by a single quote",value)
        
    def ACT_Expected_String_Value(self,value,state,trace=False):
        self.ACT_Expected("character string nominal value",value)
        
    def ACT_Expected_Type(self,value,state,trace=False):
        self.ACT_Expected("constant type",value)

    def ACT_Expected_Values(self,value,state,trace=False):
        self.ACT_Expected("start of nominal values",value)

    def ACT_Fixed_Point_Another(self,value,state,trace=False):
        return "numvals"

    def ACT_Fixed_Point_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.operand_done()
        self.context("opernxt")
        return "opers"

    def ACT_Fixed_Point_Value(self,value,state,trace=False):
        gs=self.scope()
        gs.operand.nominal(value)
        return "numnext"

    def ACT_Hexadecimal_Another(self,value,state,trace=False):
        return "hexvals"

    def ACT_Hexadecimal_Value(self,value,state,trace=False):
        gs=self.scope()
        gs.operand.nominal(value)
        return "hexnext"

    def ACT_Len_Expr_Start(self,value,state,trace=False):
        self.context("lenexpr")
        return "lenexpr"
    
    def ACT_Len_Found(self,value,state,trace=False):
        self.context("length")
        return "length"

    def ACT_Len_RPAREN(self,value,state,trace=False):
        gs,cs=self.scopes()
        if cs._parens==0:
            # Must be the terminating RPAREN matching the beginning LPAREN
            operand=gs.operand
            operand.len_expr(cs)
            constant=operand.typ
            self.context(constant.nom_ctx)
            return constant.nom_state

        # Just a matching right parenthesis of the expression
        cs.rparen(value)
        return self.current()    # Stay in the current state

    def ACT_Len_SD_Found(self,value,state,trace=False):
        gs,cs=self.scopes()
        cs.token(value)
        operand=gs.operand
        operand.len_expr(cs)
        constant=operand.typ
        self.context(constant.nom_ctx)
        return constant.nom_state

    # Add a left parenthesis to the current context scope's expression
    def ACT_LPAREN(self,value,state,trace=False):
        cs=self.cscope()
        cs.lparen(value)
        return self.current()  # Stay in this state

    def ACT_Operand_Done(self,value,state,trace=False):
        gs=self.scope()
        gs.operand_done()

        # Figure out how we ended the operand and what to do next.
        # This only occurs when a C, CA or CE constant ends because the ending
        # single quote is consumed by the string token.  In most cases the final
        # single quote is consumed outside of the nominal value in the 'opers' state.
        if value.tid == "COMMA":
            # Natural continuation with another operand
            # Handle the same as when a COMMA is consumed in a separate state.
            return self.ACT_Operand_Next(value,state,trace=trace)
        elif value.tid in ["EOO","EOS"]:
            # Done if at end of operand data
            state.atend()

        # Otherwise operand is done because we hit end of nominal values
        # Look for a comma
        self.context("opernxt")
        return "opers"

    # Starting a new constant
    def ACT_Operand_Next(self,value,state,trace=False):
        gs=self.scope()
        gs.operand_new()  # Set up a new DCDS_Operand object
        # Start with a new operand looking for its duplication factor
        self.context("dup")
        return "dup"

    # Continuing a string
    def ACT_String_Value_Cont(self,value,state,trace=False):
        cs=self.cscope()
        cs.str_cont(value)
        return self.current()

    # Complete a string
    def ACT_String_Value_Done(self,value,state,trace=False):
        gs,cs=self.scopes()
        string_tok=cs.str_end()
        gs.operand.nominal(string_tok)
        # Character constants only have one nominal value, so the operand is also done
        # Let ACT_Operand_Done determine the next state and context, too.
        return self.ACT_Operand_Done(value,state,trace=trace)

    # Starting a string.
    def ACT_String_Value_Start(self,value,state,trace=False):
        cs=self.cscope()
        cs.str_begin(value)
        self.context("dcchr2",scope=cs)  # Reuse existing scope
        return "chrvals2"

    # Valid end of a DS storage allocation.  The FSM is either done or an error
    def ACT_Value_NotStarted(self,value,state,trace=False):
        gs=self.scope()
        if gs.stmt_inst=="DS":
            return self.ACT_Operand_Done(value,state,trace=trace)
        self.ACT_Expected_Quoted_Values(value,state,trace=trace)

    # This state entered when the presence of quoted numeric values are being
    # recognized.  The initial ' has already been consumed.  It sets the context
    # for nominal value recognition.
    def ACT_Value_Started(self,value,state,trace=False):
        gs=self.scope()
        constant=gs.operand.typ         # Get the type's DCDS_Constant object
        self.context(constant.val_ctx)  # Set the lexical context for these values
        return constant.val_state       # Set the FSM state for their recognition.


# The global context for a DC or DS statement.  It keeps track of the operands
# being recognized.  The current operand holds the DCDS_Constant object being
# recognized once the type has been identified.
class DCDS_Scope(AsmCtxScope):
    def __init__(self):
        super().__init__()
        self.operands=[]     # List of parsed operands of DCDS_Context_Scope objects
        self.operand=None    # The current operand being recognized
        #self.stmt_inst=None  # The statements operation filed in upper case.

        # Pass 0 results:
        self.dc=False        # True if parsing DC operands
        
        # Pass 1 results:
        self.values=None     # List of DSDC_Operand and/or asmdcds.Nominal objects.

    def init(self):
        self.operand_new()

    def operand_new(self):
        self.operand=DCDS_Operand()

    def operand_done(self):
        self.operands.append(self.operand)
        self.operand=None

    def Pass0(self,stmt,parsers,debug=False):
        self.dc=dc=stmt.instu=="DC"
        for n,oprnd in enumerate(self.operands):
            oprnd.Pass0(stmt,parsers,n+1,dc)

    def Pass1(self,stmt,asm,debug=False,trace=False):
        values=[]
        for oprnd in self.operands:
            values.extend(oprnd.Pass1(stmt,asm,debug=debug,trace=trace))
        self.values=values
        
    #def statement(self,stmt):
    #    assert isinstance(stmt,assembler.Stmt),\
    #        "%s 'stmt' argument must be an assembler.Stmt object: %s" \
    #            % (assembler.eloc(self,"statement",module=this_module),stmt)
    #
    #   self.stmt_inst=stmt.instu   # The statement in upper case

# This object describes operand processing by the context parser.  Handling of the
# duplication factor and constant type are common for each constant.  This object
# describes for the context parser which states to enter and context for each
# type of constant to successfully parse an explicit length and nominal values.
#
# Instance Arguments
#   typ      An uppercase string of the constants type
#   valcls   The class that processes an operand's value
#   length   The length state and lexical context as a tuple.
#   nominal  The state and context of nominal value start
#   value    The value state and lexical context
class DCDS_Constant(object):
    def __init__(self,typ,valcls,length,nominal,value):
        assert issubclass(valcls,asmdcds.Nominal),\
            "%s 'valcls' argument must be a subclass of asmdcds.Nominal: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),valcls)

        self.typ=typ

        self.len_state,self.len_ctx=length
        assert isinstance(self.len_state,str),\
            "%s length[0] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.len_state)
        assert isinstance(self.len_ctx,str),\
            "%s length[1] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.len_ctx)

        self.nom_state,self.nom_ctx=nominal
        assert isinstance(self.nom_state,str),\
            "%s length[0] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.nom_state)
        assert isinstance(self.nom_ctx,str),\
            "%s length[1] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.nom_ctx)

        self.val_state,self.val_ctx=value
        assert isinstance(self.val_state,str),\
            "%s value[0] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.val_state)
        assert isinstance(self.val_ctx,str),\
            "%s value[1] must be a string: %s" \
            % (assembler.eloc(self,"__init__",module=this_module),self.val_ctx)

        self.valcls=valcls

    def __str__(self):
        return "%s(%s,%s(%s,%s),(%s,%s),(%s,%s)" % (self.__class__.__name__,self.typ,
            self.valcls,self.len_state,self.len_ctx,self.nom_state,self.nom_ctx\
            ,self.val_state,self.val_ctx)


# The context of a single operand.  Used for Pass 0, 1. 
# Pass 2 uses build() method to create binary content.
class DCDS_Operand(asmtokens.AsmFSMScope):
    def __init__(self):
        self.typ=None       # DCDS_Constant object associated with the operand
        self.value=[]       # Parsed current value
        self.nomcls=None    # The class used to process this type's nominal values
        # These attributes are derived from the asmdcds.Nominal object for the type.
        self.imp_len=1      # Length implied by the type (could be None)
        self.imp_algn=0     # Alignment implied by the type (could be None)

        # Parsing results
        self._dup_expr=[]   # Duplication expression lexical tokens
        self._len_expr=[]   # Length expression lexical tokens
        self._values=[]     # Lexical token or expression token list of nominal values 
        self._typ_tok=None  # Lexical token of operand type

        # Pass0 results
        self.dc=None        # Gets set to True/False depending upon the directive
        self._dup=None      # Duplication expression object
        self._len=None      # Explicit length expression object
        self.values=[]      # asmdcds.Nominal objects, one per each value
        self.opnum=None     # Operand number of this operand in the statement

        # Pass1 results
        self.dup=1          # The duplication factor
        self.act_len=1      # Actual length
        self.act_algn=0     # Actual alignement
        self.ds_stg=None    # asmdcds.Storage object if this is a DS operand
        # also updates asndcds.Nominal objects in self.values with explicit lengths 
        # if required.

    def __str__(self):
        if self.dc is True:
            d="DC"
        elif self.dc is False:
            d="DS"
        else:
            d="DC/DS?"
        typ=self.typ.typ
        return "%s(%s: '%s',imp-len=%s,imp-align=%s,act_len=%s,act_align=%s,dup=%s,"\
            "pvals=%s,nvals=%s)" \
            % (self.__class__.__name__,\
               d,typ,self.imp_len,self.imp_algn,self.act_len,self.act_algn,self.dup,\
               len(self._values),len(self.values))

    # Returns any required alignment
    # Matches the method of the same name in asmdcds.Nominal class
    def align(self):
        return self.act_algn

    # A DC operand with zero duplication ends up being represented by this object.
    # This lets Pass 2 build nothing.
    def build(self,stmt,asm,n,debug=False,trace=False):
        pass
    
    def dc_type(self,ltok,cobj):
        self._typ_tok=ltok              # Save the type lexical token
        self.typ=cobj                   # Remember the DCDS_Constant object
        self.nomcls=nomcls=cobj.valcls  # Remember the DCDS_Nominal class
        attr=nomcls.attr                # Fetch its attributes
        self.imp_len=attr[0]            # Remember any implied length
        self.imp_algn=attr[1]           # Remember implied alignment

    def dup_expr(self,cs):
        self._dup_expr=cs.expr_end()

    def len_expr(self,cs):
        self._len_expr=cs.expr_end()

    # Returns the length being assembled
    # Matches the method of the same name in asmdcds.Nominal class
    def length(self):
        return self.act_len

    # Add a lexical token or expresion list to the values.  Address constants will
    # have an expression.  All other types will have a lexical token
    def nominal(self,ltok):
        self._values.append(ltok)

    # Perform DC/DS Pass 0 operand processing:
    #   1. Update lexical tokens with actual position within the line.
    #   2. For DC, make sure the operand has at least one nominal value.
    #   3. Convert, as needed, the duplication factor, length modifier and address
    #      constant nominal values into expression objects ready for calculation
    #   4. Convert constant nominal values into a subclass of the Nominal class or
    #      storage allocation into Storage objects.
    # Method arguments:
    #   stmt   The Stmt object of the corresponding DC or DS directive
    #   parser The single asmfsmbp.Parsers object used to assist with expression
    #          object creation.
    #   n      The operand number of this operand in the statement, starting at 1.
    #   dc     True for a DC directive or False for a DS directive.
    # Returns:
    #   A list of a mixture of  DCDS_Operand objects (an operand with zero duplication
    #   factor) and subclasses of asmdcds.Nominal for constant nominal values or
    #   storage allocations.
    def Pass0(self,stmt,parsers,n,dc):
        parsers.ltoken_update(stmt,self._typ_tok)

        self.dc=dc                 # Remember whether DC (True) or DS (False)
        self.opnum=n               # Remember the operand number within the directive.

        if len(self._dup_expr)>0:
            self._dup=parsers.L2ArithExpr("oprnd %s dup expr" % n,\
                stmt,ltoks=self._dup_expr)
        if len(self._len_expr)>0:
            self._len=parsers.L2ArithExpr("oprnd %s len expr" % n,\
                stmt,ltoks=self._len_expr)
        
        # Create Nominal objects for each nominal value
        for vn,val in enumerate(self._values):
            if not isinstance(val,asmtokens.LexicalToken):
                # address constants have an entire list of tokens for each nominal
                # value.  Create an expression object and use it as the basis for
                # each nominal value rather than a lexical token.
                val=parsers.L2ArithExpr("oprnd %s val %s expr" % (n,vn+1),\
                    stmt,ltoks=val)
            else:
                parsers.ltoken_update(stmt,val)
            nom=self.nomcls(val)
            self.values.append(nom)

        # For a DS operand without a nominal value, create the pseudo nomimal value
        if not dc and len(self.values)==0:
            self.values.append(asmdcds.Storage(self.nomcls))

    # During Pass1 duplication and length values are calculated
    # And nominal values unrolled so addresses and length can be applied.
    #   3. Calculate duplication factor, if provided.  Must not be negative
    #   4. Calculate explict length modifier.  Must not be negative and must be
    #      valid for the constant type.
    def Pass1(self,stmt,asm,debug=False,trace=False):
        parsers=asm.fsmp
        # Calculate explicit duplication factors if provided.
        # All symbols must already be defined.
        if self._dup:
            self.dup=\
                parsers.evaluate_expr(asm,stmt,self._dup,debug=debug,trace=trace)
            if self.dup<0:
                #ltok=self._dup[0].src
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s negative duplication modifier encountered: %s" \
                        % (self.opnum,self.act_len))

        # Calculate explicit length if provided and establish actual length and
        # actual alignment.
        exp_len=None
        if self._len:
            self.act_len=exp_len=\
                parsers.evaluate_expr(asm,stmt,self._len,debug=debug,trace=trace)
            if self.act_len<1:
                #ltok=self._len[0].src
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s length modifier must be at least one byte: %s" \
                        % (self.opnum,self.act_len))

            # Access maximum length from Nominal subclass attribute max_len
            max_len=self.typ.valcls.max_len
            if self.act_len>max_len:
                #ltok=self._len[0].src
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s length modifier exceeds allowed maximum of "
                    "%s: %s" % (self.opnum,max_len,self.act_len))
            self.act_algn=0
        else:
            self.act_len=self.imp_len 
            self.act_algn=self.imp_algn

        assert exp_len is None or isinstance(exp_len,int),\
            "%s 'exp_len' variable must be an integer or None: %s" \
                % (assembler.eloc(self,"Pass1",module=this_module),exp_len)
          
        if exp_len is not None:
            for val in self.values:
                val.Pass1(exp_len)
            
        # If there is at least one nominal value for a DC, its length becomes
        # the length of an assigned lable even if the duplication factor is zero.
        if self.dc and self.values:
            first=self.values[0]
            self.act_len=first.length()
            self.act_algn=first.align()

        # If duplication factor is zero, return myself for unroll list.
        if self.dup==0:
            return [self,]

        # DC operands with a non-zero duplication factor must have at least one
        # nominal value
        if self.dc and len(self._values)==0:
            raise assembler.AssemblerError(line=stmt.lineno,\
                linepos=self._typ_tok.linepos,\
                msg="constant operand %s requires a nominal value" % n)

        # Unroll the nominal values per duplication factor dictates
        nominal_values=[]
        for n in range(self.dup):
            for m in self.values:
                nominal_values.append(m.clone())
        return nominal_values


#
#  +----------------------------+
#  |                            |
#  |   START Directive Parser   |
#  |                            |
#  +----------------------------+
#


# Syntax: [csect] START [start-expression][,[region-name]]

class START_Parser(AsmCtxParser):
    def __init__(self,dm):
        super().__init__(dm,scope=START_Scope,context="loc",trace=False)

    def __loc_end(self):
        gs=self.scope()
        cs=self.cscope()
        gs.start_list(cs.expr(value))

    def init_context(self):
        self.ctx("loc",lexctx="absexpr",ccls=asmtokens.AsmFSMScope)
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


class START_Scope(AsmCtxScope):
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
            parser.ltoken_update(stmt,tok)
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
    

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
