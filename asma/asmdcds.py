#!/usr/bin/python3
# Copyright (C) 2014-2021 Harold Grovesteen
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

# This module supports the creation of DC and DS content.

this_module="%s.py" % __name__

# Python imports: None
# SATK imports:
import pratt3     # Access for some object type checks
import fsmparser  # Access Finite-State machine parser technology

# ASMA imports:
import assembler  # Access assembler classes
import asmbase    # Access assembler base classes
import asmtokens  # Access lexical token types
import fp         # Access the floating point tools
import lnkbase    # Access address objects

# Defined lexical analyzer token types
AOPER=asmtokens.AOperType()
COMMA=asmtokens.CommaType()
DCBIN=asmtokens.DCDS_Bin_Type()
DCDPT=asmtokens.DCDS_Dec_Type()
DCFLOAT=asmtokens.DCDS_Float_Type()
DCFLSPL=asmtokens.DCDS_Float_Special_Type()
DCHEX=asmtokens.DCDS_Hex_Type()
DCLEN=asmtokens.DCDS_Length_Type()
DCNUM=asmtokens.DCDS_Number_Type()
DCQUOTE=asmtokens.DCDS_Quote_Type()
DCSTRING=asmtokens.DCDS_String_Type()
DCTYPE=asmtokens.DCDS_Types_Type()
EOO=asmtokens.EoOperType()
EOS=asmtokens.EOSType()
LATTR=asmtokens.LabelAttrType()
LPAREN=asmtokens.LParenType()
RPAREN=asmtokens.RParenType()
SDBIN=asmtokens.SDBinType()
SDCHR=asmtokens.SDChrType()
SDDEC=asmtokens.SDDecType()
SDHEX=asmtokens.SDHexType()
STRING=asmtokens.StringType()


#
#  +----------------------------+
#  |                            |
#  |   DC/DS Directive Parser   |
#  |                            |
#  +----------------------------+
#


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
        #assert issubclass(valcls,asmdcds.Nominal),\
        assert issubclass(valcls,Nominal),\
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

class DCDS_Parser(asmbase.AsmCtxParser):
    def __init__(self,dm,pm):
        super().__init__(dm,pm,"cslex",scope=None,\
            context="dup",init="dup",trace=False)
        # Note: "cslex" is used by both the START_Parser and the DCDS_Parser
        # See the parsers.py module for its definition.  Set trace=True to cause
        # parser to trace the finite machine actions.

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

        #        nominal   len      len     nom     nom       val       val
        #   TYPE  class    state    CTX    state    ctx      state      ctx
        A= c("A", DC_A, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        AD=c("AD",DC_AD,("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        B= c("B", DC_B, ("lengthq","lqb"),("nomq","quote"),("binvals","dcbin"))
        C= c("C", DC_C, ("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        CA=c("CA",DC_CA,("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        CE=c("CE",DC_CE,("lengthq","lqb"),("nomq","quote"),("chrvals","dcchr1"))
        D= c("D", DC_D, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        DD=c("DD",DC_DD,("lengthq","lqb"),("nomq","quote"),("fltvals","dcflt"))
        ED=c("ED",DC_ED,("lengthq","lqb"),("nomq","quote"),("fltvals","dcflt"))
        F= c("F", DC_F, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        FD=c("FD",DC_FD,("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        H= c("H", DC_H, ("lengthq","lqb"),("nomq","quote"),("numvals","dcnum"))
        LD=c("LD",DC_LD,("lengthq","lqb"),("nomq","quote"),("fltvals","dcflt"))
        P= c("P", DC_P, ("lengthq","lqb"),("nomq","quote"),("dpvals", "dcdpt"))
        S= c("S", DC_S, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        SY=c("SY",DC_SY,("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        X= c("X", DC_X, ("lengthq","lqb"),("nomq","quote"),("hexvals","dchex"))
        Y= c("Y", DC_Y, ("lengthp","lpb"),("nomp","lpren"),("adrvals","addr"))
        Z= c("Z", DC_Z, ("lengthq","lqb"),("nomq","quote"),("dpvals", "dcdpt"))
        self.__constant(A)
        self.__constant(AD)
        self.__constant(B)
        self.__constant(C)
        self.__constant(CA)
        self.__constant(CE)
        self.__constant(D)
        self.__constant(DD)
        self.__constant(ED)
        self.__constant(F)
        self.__constant(FD)
        self.__constant(H)
        self.__constant(LD)
        self.__constant(P)
        self.__constant(S)
        self.__constant(SY)
        self.__constant(X)
        self.__constant(Y)
        self.__constant(Z)

    # Check a DCFLOAT lexical token for recognition of a valid finite floating
    # point number.
    # Method Arguments:
    #   gs    the current parser global state
    #   ltok  The lexical token (tid='DCFLOAT') being examined.
    # Returns:
    #   None if the lexical token contains a valid finite floating point number
    # Exception:
    #   assembler.AsmParserError  terminates the operand parsing process for the
    #   statement by raisnng the exception.
    # Note: This check is required because the regular expression used by the
    # DCFLOAT lexical token generates a match object with all unmatched groups set
    # to None.  DCFLOAT will match invalid strings as well as valid strings.
    def ck_DCFLOAT(self,gs,ltok):
        assert isinstance(ltok,asmtokens.DCDS_Float_Token),\
            "%s 'ltok' argument must be an instance of DCFLOAT: %s" \
                % (assembler.eloc(self,"ck_DCFLOAT",module=this_module),ltok)

        mo=ltok.mo
        grps=mo.groupdict()
        if grps["int"]==None and grps["frac"]==None:
            nom=len(gs.operand.values)+1
            opnd=len(gs.operands)+1
            raise assembler.AsmParserError(ltok,msg="operand %s invalid floating "\
                "point number in nominal value %s: %s"\
                % (opnd,nom,mo.string[mo.pos:min(mo.endpos,mo.pos+10)]))
        return

    # Initialize the lexical contexts used by the parser.
    def init_context(self):
        self.ctx("addr",   lexctx="addrexpr",ccls=asmbase.AsmFSMScope)
        self.ctx("dcnum",  lexctx="dcnum",   ccls=asmbase.AsmFSMScope)
        self.ctx("dup",    lexctx="dupbeg",  ccls=asmbase.AsmFSMScope)
        self.ctx("dupexpr",lexctx="addrexpr", ccls=asmbase.AsmFSMScope)
        self.ctx("dcbin",  lexctx="dcbin",   ccls=asmbase.AsmFSMScope)
        self.ctx("dcchr1", lexctx="dcchr1",  ccls=asmbase.AsmFSMScope)
        self.ctx("dcchr2", lexctx="dcchr2",  ccls=asmbase.AsmFSMScope)
        self.ctx("dcdpt",  lexctx="dcdpt",   ccls=asmbase.AsmFSMScope)
        self.ctx("dchex",  lexctx="dchex",   ccls=asmbase.AsmFSMScope)
        self.ctx("dcflt",  lexctx="dcflt",   ccls=asmbase.AsmFSMScope)
        self.ctx("type",   lexctx="dctypes", ccls=asmbase.AsmFSMScope)
        self.ctx("lpb",    lexctx="lenpbeg", ccls=asmbase.AsmFSMScope)
        self.ctx("lqb",    lexctx="lenqbeg", ccls=asmbase.AsmFSMScope)
        self.ctx("length", lexctx="lenbeg",  ccls=asmbase.AsmFSMScope)
        self.ctx("lenexpr",lexctx="addrexpr", ccls=asmbase.AsmFSMScope)
        self.ctx("lpren",  lexctx="lpren",   ccls=asmbase.AsmFSMScope)
        self.ctx("opernxt",lexctx="dccont",  ccls=asmbase.AsmFSMScope)
        self.ctx("quote",  lexctx="quote",   ccls=asmbase.AsmFSMScope)

    def initialize(self):
        # Looks for duplication factor as a self-defining term or parenthesized
        # expression
        dup=fsmparser.PState("dup")
        dup.action([SDDEC,],self.ACT_Dup_SD_found)
        dup.action([LPAREN,],self.ACT_Dup_Expr_Start)
        dup.action([DCTYPE,],self.ACT_DC_Type)    # No duplication.
        dup.action([COMMA,],self.ACT_Expected_Constant)
        dup.error(self.ACT_Expected_Dup)
        self.state(dup)

        # Completes the duplication factor parenthesized expression
        dup_expr=fsmparser.PState("dupexpr")
        dup_expr.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,LATTR],self.ACT_Add_Token)
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
        len_expr.action([AOPER,SDBIN,SDHEX,SDCHR,SDDEC,LATTR],self.ACT_Add_Token)
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

        # Type A, AD, S, SY, Y - Recognizes address expressions as nominal value
        # Expression left-hand side values
        #                                                          Next State
        adrvals=fsmparser.PState("adrvals")
        adrvals.action([LPAREN,],self.ACT_Addr_LPAREN)            #  vals
        adrvals.action([LATTR,SDBIN,SDHEX,SDCHR,SDDEC],self.ACT_Addr_RHand) #  infix
        adrvals.action([AOPER,],self.ACT_Addr_Unary)              #  +/-=vals, *=infix
        adrvals.error(self.ACT_Expected_Addr_Operand)
        self.state(adrvals)

        # Type A, AD, S, SY, Y - Recognizes address expressions as nominal value
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
        binvals.error(self.ACT_Expected_Binary_Value)
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

        # Types DD, ED, LD - Floating point values
        fltvals=fsmparser.PState("fltvals")
        fltvals.action([DCFLOAT,],self.ACT_Floating_Point_Value)
        fltvals.action([DCFLSPL,],self.ACT_Floating_Point_Special)
        fltvals.error(self.ACT_Expected_FloatingPt_Value)
        self.state(fltvals)

        # Types DD, ED, LD -
        # Recognizes whether another floating point nominal or operand is done
        fltnext=fsmparser.PState("fltnext")
        fltnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes context
        fltnext.action([COMMA,],self.ACT_FloatingPt_Another)
        fltnext.error(self.ACT_Expected_More_Values)
        self.state(fltnext)

        # Types P,Z - Recognizes decimal pointed nominal values
        dpvals=fsmparser.PState("dpvals")
        dpvals.action([DCDPT,],self.ACT_DecimalPt_Value)
        dpvals.error(self.ACT_Expected_DecimalPt_Value)
        self.state(dpvals)

        # Types P,Z - Recognizes whether another nominal value or the operand is done
        dpnext=fsmparser.PState("dpnext")
        dpnext.action([DCQUOTE,],self.ACT_Operand_Done)      # changes context
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
        #cs=self.cscope()
        gs,cs=self.scopes()
        if value.string in "+-":
            cs.token(value)
            return "adrvals"      # Found the unary operator now seek its right hand
        elif value.string=="*":
            #value.iscur=True       # Make sure the correct pratt token is generated
            value.current(gs._stmt) # Make sure the correct pratt token is generated
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
            # Note: This condition should not occur.  If it does, there is a
            # problem with pattern used by class asmtokens.DCDS_Types_Type or
            # the constants defined in __init_constants() method.
            # By raising the AsmParserError the assembly continues.
            raise assembler.AsmParserError(value,\
                msg="invalid constant type: '%s'" % value.string) from None
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

    def ACT_Expected_Constant(self,value,state,trace=False):
        self.ACT_Expected("start of constant",value)

    def ACT_Expected_DCDS_Done(self,value,state,trace=False):
        self.ACT_Expected("end of DC or DS directive",value)

    def ACT_Expected_DecimalPt_Value(self,value,state,trace=False):
        self.ACT_Expected("decimal nominal value",value)

    def ACT_Expected_Dup(self,value,state,trace=False):
        self.ACT_Expected("duplication factor",value)

    def ACT_Expected_Dup_Expr(self,value,state,trace=False):
        self.ACT_Expected(\
            "duplication modifier arithmetic operation or operand",value)

    def ACT_Expected_Fixed_Point_Value(self,value,state,trace=False):
        self.ACT_Expected("fixed point nominal value",value)

    def ACT_Expected_FloatingPt_Value(self,value,state,trace=False):
        self.ACT_Expected("floating point nominal value",value)

    def ACT_Expected_Hexadecimal_Value(self,value,state,trace=False):
        self.ACT_Expected("hexadecimal nominal value",value)

    def ACT_Expected_Len(self,value,state,trace=False):
        self.ACT_Expected("constant length",value)

    def ACT_Expected_Len_Expr(self,value,state,trace=False):
        self.ACT_Expected(\
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

    def ACT_FloatingPt_Another(self,value,state,trace=False):
        return "fltvals"

    def ACT_Floating_Point_Special(self,value,state,trace=False):
        gs=self.scope()
        #self.ck_DCFLOAT(gs,value)
        gs.operand.nominal(value)
        return "fltnext"

    def ACT_Floating_Point_Value(self,value,state,trace=False):
        gs=self.scope()
        self.ck_DCFLOAT(gs,value)
        gs.operand.nominal(value)
        return "fltnext"

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
class DCDS_Scope(asmbase.AsmCtxScope):
    def __init__(self):
        super().__init__()
        self.operands=[]     # List of parsed operands of DCDS_Context_Scope objects
        self.operand=None    # The current operand being recognized
        #self.stmt_inst=None  # The statements operation filed in upper case.

        # Pass 0 results:
        #self.dc=False        # True if parsing DC operands

        # Pass 1 results:
        #self.values=None     # List of DSDC_Operand and/or asmdcds.Nominal objects.

    def init(self,stmt=None):
        super().init(stmt=stmt)
        self.operand_new()

    def operand_new(self):
        self.operand=DCDS_Operand()
        self.operand.init(stmt=self._stmt)

    def operand_done(self):
        self.operands.append(self.operand)
        self.operand=None


# The context of a single operand.  Used for Pass 0, 1.
# Pass 2 uses build() method to create binary content.
class DCDS_Operand(asmbase.AsmFSMScope):
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
        self.unique=False   # Whether this constand operand is unique

        # Pass1 results
        self.dup=1          # The duplication factor
        self.act_len=1      # Actual length
        self.act_algn=0     # Actual alignement
        self.ds_stg=None    # asmdcds.Storage object if this is a DS operand
        self.T="U"          # Type attribute of operand
        self.S=0            # Scale attribute of operand
        self.I=0            # Integer attribute of operand
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
        self._dup_expr=cs.expr_end(line=self._stmt.lineno)

    def len_expr(self,cs):
        self._len_expr=cs.expr_end(line=self._stmt.lineno)

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
    # Exception:
    #   assembler.AssemblerError if a problem arises during nominal value class
    #   instantiation.
    def Pass0(self,stmt,parsers,n,dc,update=None):
        parsers.ltoken_update(stmt,self._typ_tok,asmstr=update)

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
                self.unique=self.unique or val.unique
            else:
                parsers.ltoken_update(stmt,val,asmstr=update)
                if isinstance(val,asmtokens.PLitCur):
                    self.unique=True
            try:
                nom=self.nomcls(val)
            except assembler.AsmParserError as ape:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s nominal %s %s" % (n,vn+1,ape.msg)) from None
            self.values.append(nom)

        # For a DS operand without a nominal value, create the pseudo nomimal value
        if not dc and len(self.values)==0:
            self.values.append(Storage(self.nomcls))

    # During Pass1 duplication and length values are calculated
    # And nominal values unrolled so addresses and length can be applied.
    #   3. Calculate duplication factor, if provided.  Must not be negative
    #   4. Calculate explict length modifier.  Must not be negative and must be
    #      valid for the constant type.
    def Pass1(self,stmt,asm,debug=False,trace=False):
        parsers=asm.PM
        # Calculate explicit duplication factors if provided.
        # All symbols must already be defined.
        if self._dup:
            self.dup=\
                parsers.evaluate_expr(asm,stmt,self._dup,debug=debug,trace=trace)
            if self.dup<0:
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
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s length modifier must be at least one byte: %s" \
                        % (self.opnum,self.act_len))

            # Access maximum length from Nominal subclass attribute max_len
            max_len=self.typ.valcls.max_len
            if self.act_len>max_len:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s length modifier exceeds allowed maximum of "
                    "%s: %s" % (self.opnum,max_len,self.act_len))

            # Perform nominal value explicit length check.  Because the length
            # applies to all nominal values, the first value is used to perform
            # the check.  An AssemblerError is raised if the check fails
            self.values[0].ck_length(exp_len,self.opnum)

            # Explicit length is value.
            self.act_algn=0
            self.T=self.nomcls.utyp
        else:
            self.act_len=self.imp_len
            self.act_algn=self.imp_algn
            self.T=self.nomcls.atyp

        assert exp_len is None or isinstance(exp_len,int),\
            "%s 'exp_len' variable must be an integer or None: %s" \
                % (assembler.eloc(self,"Pass1",module=this_module),exp_len)

        # Push downward from the operand to the nominal values the operand's
        # explicit length and Type attribute.  If the explicit length is None
        # the implicit length prevails.
        for val in self.values:
            val.Pass1(exp_len,T=self.T)

        # If there is at least one nominal value for a DC, its
        #   - length (implicit or explicit)
        #   - alignment (implied or suppressed)
        #   - Scale attribute and
        #   - Integer attribute
        # become the corresponding values of the operand as a whole.
        # These values of the first operand become the attributes of a label
        # assigned to the statement.  See asmstmts.DC
        if self.dc and self.values:
            first=self.values[0]
            self.act_len=first.length()
            self.act_algn=first.align()
            self.I=first.I
            self.S=first.S
            if __debug__:
                if debug:
                    print("%s first nomonal value %s T:%s S:%s I:%s" \
                        % (assembler.eloc(self,"Pass1",module=this_module),\
                            first.__class__.__name__,self.T,self.S,self.I))

        # If duplication factor is zero, return myself for unroll list.
        if self.dup==0:
            return [self,]

        # DC operands with a non-zero duplication factor must have at least one
        # nominal value
        if self.dc and len(self._values)==0:
            raise assembler.AssemblerError(line=stmt.lineno,\
                linepos=self._typ_tok.linepos,\
                    msg="constant operand requires a nominal value")

        # Unroll the nominal values per duplication factor
        nominal_values=[]
        for n in range(self.dup):
            for m in self.values:
                assert m.content is None or \
                  isinstance(m.content.barray,bytesarray), \
                    "%s [%s] cloned nominal does not have bytearray: %s" \
                        % (assembler.eloc(self,"Pass1",module=this_module),\
                            self.lineno,nom.content.barray)
                nom=m.clone()
                nom.T=self.T
                nominal_values.append(nom)
                assert nom.content is None or \
                  isinstance(nom.content.barray,bytearray), \
                    "%s [%s] clone nominal does not have bytearray: %s" \
                        % (assembler.eloc(self,"Pass1",module=this_module),\
                            self.lineno,nom.content.barray)
        return nominal_values


#
#  +---------------------------------+
#  |                                 |
#  |   DC/DS NOMINAL VALUE OBJECTS   |
#  |                                 |
#  +---------------------------------+
#


# This is the base class describing a nominal values.  This class ultimately creates
# assembled binary data for constant nominal values.  It also contains the
# information related to constant length and alingment for address assignment but
# does not itself perform the assignments.  These objects only exist for DC directive
# operands.  DS directives do not utilize this object.
#
# Instance Arguments:
#   ltok        The asmtokens.LexicalToken object defining the nominal value or
#               an pratt expression object defines the nominal value's generated
#               value.
#               This class and subclasses assume that all lexical tokens have been
#               updated to reflect actual statement position, that is, the tokens
#               update method has been called.
#   length      The implied length.  Specify None if the implied length is defined by
#               the value.  Defaults to None.
#   alignment   The implied alignment.  Specify 0 if no implied alignment applied.
#               Defaults to 0.
#   signed      Specify True if by default the nominal value is signed.  Defaults
#               to None.  None is not equivalent to False.
class Nominal(object):

    # Accepts a string of digits and converts them to bytes using the supplied
    # base and number of characters per byte.
    @staticmethod
    def base2bytes(digits,base,cpb):
        b=bytearray(0)
        chars=len(digits)
        for x in range(0,chars,cpb):
            txt=digits[x:x+cpb]
            assert len(txt)>0,\
                "%s - Nominal.base2bytes() - base conversion loop should not end "\
                "prematurely: x:%s, len(s):%s cpb:%s" % (this_module,x,len(s),cpb)
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

    # Truncate/pad string on left with zero as the pad character
    @staticmethod
    def tp_left(string,chars):
        if len(string)<chars:
            s=string.rjust(chars,'0')    # Pad on the left with ASCII zeros
        else:
            s=string[len(string)-chars:] # Truncate on the left if needed
        return s

    def __init__(self,ltok,length=None,alignment=0,signed=None):
        # This check is performed to ensure alignment meets the needs of
        assert isinstance(alignment,int),\
            "%s 'alignment' argument must be an integer: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),alignment)
        self.ltok=ltok             # May be a single token or a list of tokens

        self._length=length        # Implied or explicit length
        self._alignment=alignment  # Implied alignment or None if no alignment
        self._signed=signed        # Whether nominal value is signed or not
        # The signed method updates this if the value by default is signed but this
        # instance is unsigned.  The attribute influences the assembled value.
        self.unsigned=False

        # In Pass1 an empty Binary object is create with binary zeros.  If Pass2
        # does nothing, we are left with zeros.  But that should never happen here
        # We will build the actual values and replace it here during Pass2 with the
        # build method()
        self.T="U"
        self.S=0
        self.I=0
        self.content=None

    # Returns any alignment required
    # This matches the asmfmscs.DCDS_Operand method of the same name.
    def align(self):
        if self._alignment is None:
            return 0
        return self._alignment

    # This method updates the content attribute with a Binary object containing
    # the nominal values's assembled data.  This method is called by the assembler
    # during Pass 2 processing
    def build(stmt,asm,n,debug=False,trace=False):
        raise NotImplementedError("%s subclass %s must provide build() method" \
            % (assembler.eloc(self,"build",module=this_module),\
                self.__class__.__name__))

    # This methd allows nominal specific checks for explicit lengths.  Most cases
    # the maximum length check using the class attribute max_len is sufficient.
    # Nominal values requiring additional checks must override this method.
    #
    # Method Arguments:
    #   act_len  The calculated explicit length
    #   n        The operand number of the nominal value.
    # Returns:
    #   None when nominal value length check succeeds
    # Exception:
    #   AssemblerError if nominal value length check fails.
    def ck_length(self,act_len,n):
        pass

    # This method returns an instance of the Nominal subclass suitable for generating
    # binary data.  All subclasses share this method.
    def clone(self):
        new=self.__class__(self.ltok)
        new.unsigned=self.unsigned
        new.ivalue=self.ivalue
        new.T=self.T
        new.S=self.S
        new.I=self.I
        # These attributes get updated after initial object creation.
        # Cloned objects must reflect the current value not the original.
        new._alignment=self._alignment
        new._length=self._length

        return new

    # Updates the location counter after building the final binary data
    def cur_loc(self,asm):
        asm.cur_loc.increment(self.content,debug=False)

    # Returns the length being assembled
    # This matches the asmfmscs.DCDS_Operand method of the same name.
    def length(self):
        return self._length

    # Update the nominal value with the constant operand's explicit length.
    # This method is only called when a valid explict length has been provided for
    # the constant's nominal values.  All subclasses use this method.
    def Pass1(self,explen,T="U"):
        #print('%s T="%s"' % (assembler.eloc(self,"Pass1",module=this_module),T))
        # Set explicit length, overriding implied length
        if explen:
            self._length=explen
            # Disable implied alignment because of explicit length
            self._alignment=0   # assembler.Content.align() wants a number
        # Remember by type attribute
        self.T=T

    # Update whether this is an unsigned nominal value or not.
    def signed(self):
        if self._signed is True:
            self.unsigned=self.ltok.unsigned


class Address(Nominal):
    def __init__(self,addrexpr):
        assert isinstance(addrexpr,pratt3.PExpr),\
            "%s 'addrexpr' argument must be a pratt3.PExpr: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),addrexpr)

        cls=self.__class__
        length,align=cls.attr
        super().__init__(addrexpr,length=length,alignment=align,signed=False)
        self.ivalue=ADCON(addrexpr,cls.typ)

    def build(self,stmt,asm,n,debug=False,trace=False):
        if __debug__:
            if trace:
                print("%s cur_loc before: %s" \
                    % (assembler.eloc(self,"build",module=this_module),asm.cur_loc))
                print("%s content: %s" \
                    % (assembler.eloc(self,"build",module=this_module),self.content))

        asm.cur_loc.establish(self.content.loc,debug=trace)
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(asm,asm.PM,stmt,n,self._length,trace=trace)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)
        if __debug__:
            if trace:
                print("%s cur_loc after: %s" \
                    % (assembler.eloc(self,"build",module=this_module),asm.cur_loc))


class BinaryBits(Nominal):
    def __init__(self,ltok):
        length,align,cpb,base=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=False)

        # Create the underlying data abstraction from the lexical token
        self.ivalue=Bits(ltok.extract(),(cpb,base),ltok.linepos)
        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class Characters(Nominal):
    def __init__(self,ltok,ccls):
        super().__init__(ltok,length=1,alignment=0,signed=False)

        # This attribute represents an intermediate form between a lexical token
        # and the assembled value.
        self.ivalue=ccls(ltok.convert(),ltok.linepos)
        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class DecimalPointed(Nominal):
    def __init__(self,ltok,dcls):
        length,align=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=True)
        # The lexical token figures out the digits right of decimal point
        self.S=ltok.S
        self.I=0     # The integer value is set during Pass1() processing

        # This attribute represents an intermediate form between a lexical token
        # and the assembled value.
        self.ivalue=dcls(ltok.sign(),ltok.digits(),ltok.linepos,S=self.S)

        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=True):
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)

    def Pass1(self,explen,T="U"):
        super().Pass1(explen,T=T)
        self.I=self.ivalue.calc_I(self._length,self.S,debug=False)
        #print("%s T:%s S:%s I:%s" \
        #    % (assembler.eloc(self,"Pass1",module=this_module),self.T,self.S,self.I))


class Float(Nominal):
    def __init__(self,ltok,dcls):
        assert ltok.tid in ["DCFLOAT","DCFLSPL"],\
            "%s unexpected lexical token: %s"\
                 % (assembler.eloc(self,"__init__",module=this_module),ltok)

        length,align=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=False)
        self.ivalue=None    # See build() method
        self.dcls=dcls      # The nominal value builder class

    def build(self,stmt,asm,n,debug=False,trace=False):
        # This method may raise an fp.FPError that must be caught by the caller

        if self.ltok.tid=="DCFLOAT":
            self.ivalue=self.dcls(self.ltok.dct(),self._length,debug=trace)
        else:  # Assume it is a special value token
            self.ivalue=self.dcls(None,self._length,special=self.ltok.extract(),\
                debug=trace)
        #except assembler.AsmParserError as ape:
        #    raise assembler.AssemblerError(line=stmt.lineno,\
        #        msg="operand %s %s" % (n,ape.msg)) from None

        self.content.barray=bytearray(self._length)
        data=self.ivalue.build()

        # Report any overflow or underflow
        if self.ivalue.has_overflow():
            msg="WARNING: nominal value %s - overflow to infinity" % int(n+1)
            ae=assembler.AssemblerError(line=stmt.lineno,msg=msg,info=True)
            asm._ae_excp(ae,stmt,string="asmdcds.Float.build()",debug=debug)
        elif self.ivalue.has_underflow():
            msg="WARNING: nominal value %s - underflow to zero" % int(n+1)
            ae=assembler.AssemblerError(line=stmt.lineno,msg=msg,info=True)
            asm._ae_excp(ae,stmt,string="acmdcds.Float.build()",debug=debug)

        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class SConstant(Nominal):
    def __init__(self,addrexpr,size):
        assert isinstance(addrexpr,pratt3.PExpr),\
            "%s 'addrexpr' argument must be a pratt3.PExpr: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),addrexpr)

        length,align=self.__class__.attr
        super().__init__(addrexpr,length=length,alignment=align,signed=False)
        self.ivalue=SCON(addrexpr,size=size)

    def build(self,stmt,asm,n,debug=False,trace=False):
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(asm,asm.PM,stmt,n,self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


# This object stands in for DS "nominal" values, generating 0x00 for each byte.
# This class allows DS processing to parallel DC.  In the case of DS, one of these
# objects if used when no nominal values are supplied for the operand.  Regular
# nominal values are used if the DS statement actually has nominal values.
class Storage(Nominal):
    def __init__(self,typcls):
        attr=typcls.attr
        super().__init__(None,length=attr[0],alignment=attr[1],signed=False)
        self.typcls=typcls
        # Assume alignment here.  But it might change if there is a length
        self.T=typcls.atyp
        self.S=0     # When no nomimal value is supplied
        self.I=0     # When no nominal value is supplied

    def __str__(self):
        return "%s(length=%s,alignment=%s)" \
            % (self.__class__.__name__,self._length,self._alignment)

    # DS operand has no Pass 2 processing.  Its content is completed in Pass 1
    def build(self,stmt,asm,n,debug=False,trace=False):
        pass

    # Override Nominal class clone() method for my needs.
    def clone(self):
        new=Storage(self.typcls)
        new.unsigned=self.unsigned
        # These attributes get updated after initial object creation.
        # Cloned objects must reflect the current value not the original.
        new._alignment=self._alignment
        new._length=self._length
        new.T=self.T
        new.S=self.S
        new.I=self.I
        return new


class TwosCompBin(Nominal):
    def __init__(self,ltok):
        length,align=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=True)

        # This attribute represents an intermeidate form between a lexical token
        # and the assembled value
        self.ivalue=FixedPoint(ltok.sign(),ltok.digits(),ltok.linepos)

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        self.content.barray=bytearray(self._length)
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


# Each of these classes defines the basic attributes of a constant type related
# to alignment and length.  The first two attributes must be the implied length
# and implied alignment.  For some types, additional attributes are supplied.
# Each Nominal subclass is tied to the values specified by the class 'attr' attribute.

class DC_A(Address):
    attr=(4,4)       # implied length, alignment
    max_len=4        # maximum explicit length
    typ="A"
    atyp="A"
    utyp="R"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_AD(Address):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    typ="AD"
    atyp="A"
    utyp="R"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_B(BinaryBits):
    attr=(1,0,8,2)   # Attributes used by Bits object (chars/byte, base)
    max_len=256      # maximum explicit length
    atyp="B"
    utyp="B"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_C(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=65536    # maximum explicit length
    atyp="C"
    utyp="C"
    def __init__(self,ltok):
        super().__init__(ltok,StringE)


class DC_CA(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=65536    # maximum explicit length
    atyp="C"
    utyp="C"
    def __init__(self,ltok):
        super().__init__(ltok,StringA)


class DC_CE(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=65536    # maximum explicit length
    atyp="C"
    utyp="C"
    def __init__(self,ltok):
        super().__init__(ltok,StringE)


class DC_D(TwosCompBin):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="D"
    utyp="U"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_DD(Float):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="D"
    utyp="K"
    def __init__(self,ltok):
        super().__init__(ltok,DFP)

    def ck_length(self,exp_len,n):
        if exp_len not in [4,8]:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s explicit length invalid, must be 4, or 8: %s" \
                    % (n+1,exp_len))


class DC_ED(Float):
    attr=(4,4)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="E"
    utyp="K"
    def __init__(self,ltok):
        super().__init__(ltok,DFP)

    def ck_length(self,exp_len,n):
        if exp_len not in [4,8]:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s explicit length invalid, must be 4, or 8: %s" \
                    % (n+1,exp_len))


class DC_F(TwosCompBin):
    attr=(4,4)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="F"
    utyp="U"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_FD(TwosCompBin):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="F"
    utyp="U"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_H(TwosCompBin):
    attr=(2,2)       # implied length, alignment
    max_len=8        # maximum explicit length
    atyp="H"
    utyp="U"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_LD(Float):
    attr=(16,8)      # implied length, alignment
    max_len=16       # maximum explicit length
    atyp="L"
    utyp="K"
    def __init__(self,ltok):
        super().__init__(ltok,DFP)

    def ck_length(self,exp_len,n):
        if exp_len not in [4,8,16]:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s explicit length invalid, must be 4, 8, or 16: %s" \
                    % (n+1,exp_len))


class DC_P(DecimalPointed):
    attr=(1,0)       # implied length, alignment
    max_len=16       # maximum explicit length
    atyp="P"
    utyp="P"
    def __init__(self,ltok):
        super().__init__(ltok,Packed)


class DC_S(SConstant):
    attr=(2,2)       # implied length, alignment
    max_len=2        # maximum explicit length
    atyp="S"
    utyp="R"
    def __init__(self,addrexpr):
        super().__init__(addrexpr,12)


class DC_SY(SConstant):
    attr=(3,0)       # implied length, alignment
    max_len=3        # maximum explicit length
    atyp="S"
    utyp="R"
    def __init__(self,addrexpr):
        super().__init__(addrexpr,20)


class DC_X(BinaryBits):
    attr=(1,0,2,16)  # implied length, alignment, char/byte, base
    max_len=65536    # maximum explicit length
    atyp="X"
    utyp="X"
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_Y(Address):
    attr=(2,2)       # implied length, alignment
    max_len=2        # maximum explicit length
    typ="Y"
    atyp="Y"
    utyp="R"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_Z(DecimalPointed):
    attr=(1,0)       # implied length, alignment
    max_len=16       # maximum explicit length
    atyp="Z"
    utyp="Z"
    def __init__(self,ltok):
        super().__init__(ltok,Zoned)


class ADCON(object):
    # Valid lengths for different address constants when value is not an integer
    lengths={"A":[2,3,4],"AD":[1,2,3,4,5,6,7,8],"Y":[2,]}
    def __init__(self,expr,typ):
        self.expr=expr
        self.typ=typ
        self.lengths=ADCON.lengths[typ]

    def __str__(self):
        return "%s(expr=%s)" % (self.__class__.__name__,self.expr)

    def build(self,asm,parsers,stmt,n,length,trace=False):
        #print("%s trace: %s"
        #    % (assembler.eloc(self,"build",module=this_module),trace))
        sign=False   # Assume this is an unsigned value
        try:
            value=parsers.evaluate_expr(asm,stmt,self.expr,debug=False,trace=trace)
        except lnkbase.AddrArithError as ae:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s address arithmetic error, %s" \
                    % (n+1,ae))

        assert isinstance(value,(int,lnkbase.Address)),\
            "%s internal calculation of operand %s address expression resulted in an"\
            "unsupported value: %s" \
            % (assembler.eloc(self,"build",module=this_module),n+1,value)

        if isinstance(value,lnkbase.Address):
            if length not in self.lengths:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s %s-type explicit length invalid for an address "\
                    "nominal value: %s" % (n+1,self.typ,length))
            if value.isAbsolute():
                value=value.address
            else:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s address constant did not evaluate to an "\
                        "absolute address: %s" % (n+1,value))
        else:  # Must be an integer then.  Determine if a sign is required
            if value < 0:
                sign=True

        # Convert computed address constant to bytes
        b=value.to_bytes((value.bit_length()//8)+1,byteorder="big",signed=sign)

        # Perform left truncation/padding
        pad=b'\x00' * length
        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'"
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))

        return b


# This object abstracts binary values.  It is derived from a lexitcal token but
# ceases to be conntected to it.  It assumes that the lexical token's type regular
# expression has done its job and only valid characters are present
class Bits(object):
    def __init__(self,digits,attr,linepos):
        self.digits=digits
        self.cpb,self.base=attr
        self.linepos=linepos

    def __str__(self):
        return "%s(digits='%s',base=%s,cpb=%s,bpos=%s)" \
            % (self.__class__.__name__,self.digits,self.base,self.cpb,self.linepos)

    # Build binary data composed of bits based upon the supplied length
    def build(self,length,trace=False):
        cpb=self.cpb      # Get the number of characters per byte
        chars=cpb*length
        s=Nominal.tp_left(self.digits,chars)
        b=Nominal.base2bytes(s,self.base,self.cpb)

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))

        return b

    # Returns the length implied by the nominal value itself
    def infer_length(self):
        return Nominal.round_up(len(self.digits),self.cpb)


# This object abstracts input signed decimal values.  It is derived from a lexical
# token but ceases to be connected to it.  It assumes that the lexical token's type
# regular expression has done its job and only valid characters are present.
# The handling of the original lexical token and its input is similar to the
# FixedPoint class.  However, assembled data diverges dramatically from the
# FixedPoint class.
class Decimal(object):
    sign={"-":"D","+":"C","U":"F",None:"C"}
    def __init__(self,sign,digits,cpb,linepos,S=None):
        self.linepos=linepos
        self.sign=sign           # Sign of the constant '+', '-', 'U' or None
        self.digits=digits       # String of decimal digits
        self.cpb=cpb
        self.S=S                 # Number of digits right of decimal point
        # Set by build() method using make_hex()
        self.I=None              # Set by make_hex() when the actual length is known

    def __str__(self):
        return "%s(sign='%s',digits='%s',pos=%s)" \
            % (self.__class__.__name__,self.sign,self.digits,self.linepos)

    def build(self,length,trace=False):
        hexdigits=self.make_hex(length)
        # Convert the hex data into bytes
        b=Nominal.base2bytes(hexdigits,16,2)

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" % (cls_str,len(b),b))

        return b

    def calc_I(self,length,S):
        raise NotImplementedError("%s subclass %s must proivde infer_length() method" \
            % (assembler.eloc(self,"calc_I",module=this_module),\
                self.__class__.__name__))

    def infer_length(self):
        raise NotImplementedError("%s subclass %s must proivde infer_length() method" \
            % (assembler.eloc(self,"infer_length",module=this_module),\
                self.__class__.__name__))


class Packed(Decimal):
    def __init__(self,sign,digits,linepos,S=0):
        super().__init__(sign,digits,2,linepos,S=S)

    def calc_I(self,length,S,debug=False):
        I=max(0,(length*2)-S-1)
        if __debug__:
            if debug:
                print("%s length:%s S:%s returning I:%s" \
                    % (assembler.eloc(self,"calc_I",module=this_module),length,S,I))
        return I

    def infer_length(self):
        return Nominal.round_up(len(self.digits)+1,2)

    def make_hex(self,length):
        # Convert to packed digits plus sign
        hexdigits="%s%s" % (self.digits,Decimal.sign[self.sign])
        # Do left truncation/padding
        chars=length*2
        return Nominal.tp_left(hexdigits,chars)


class Zoned(Decimal):
    def __init__(self,sign,digits,linepos,S=0):
        super().__init__(sign,digits,1,linepos,S=S)

    def calc_I(self,length,S,debug=False):
        I=max(0,length-S)
        if __debug__:
            if debug:
                print("%s length:%s S:%s returning I:%s" \
                    % (assembler.eloc(self,"calc_I",module=this_module),length,S,I))
        return I

    def infer_length(self):
        return len(self.digits)

    def make_hex(self,length):
        digits=Nominal.tp_left(self.digits,length)
        hi=digits[:-1]
        lo=digits[-1]
        lohex="%s%s" % (Decimal.sign[self.sign],lo)

        zoned=""
        for digit in hi:
            # unpack each non-signed digit
            zoned="%sF%s" % (zoned,digit)
        return "%s%s" % (zoned,lohex)


# This object abstracts input signed numeric values.  It is derived from a lexical
# token but ceases to be connected to it.  It assumes that the lexical token's type
# regular expression has done its job and only valid characters are present.
# The handling of the original lexical token and its input is similar to the
# Decimal class.  However, assembled data diverges dramatically from the Decimal class.
class FixedPoint(object):
    sign_char={"+":1,"-":-1,None:1,"U":1}
    def __init__(self,sign,digits,linepos):
        self.linepos=linepos
        self.sign=sign           # Sign of the constant '+', '-', 'U' or None
        self.digits=digits       # String of decimal digits with possible spaces

    def __str__(self):
        return "%s(sign='%s',digits='%s',pos=%s)" \
            % (self.__class__.__name__,self.sign,self.digits,self.linepos)

    # Private method that assembles fixed point values
    def __build(self,length,signed=False,trace=False):
        # Compute input source text into an integer with the correct sign
        i=int(self.digits)*FixedPoint.sign_char[self.sign]

        # Convert the integer into bytes
        b=i.to_bytes((i.bit_length()//8)+1,byteorder="big",signed=signed)

        # Determine padding
        if signed and i<0:
            pad=b'\xFF' * length
        else:
            pad=b'\x00' * length

        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"__build",module=this_module),len(b),b))

        return b

    # Returns assembled bytes conforming the external interface
    def build(self,length,trace=False):
        return self.__build(length,signed=self.sign!="U",trace=trace)


# This object provides generic support for floating point constants.  Each
# subclass tailors the actions for each type of floating point constant.
class FloatingPoint(object):
    def __init__(self,mo,length,debug=False):
        self.mo=mo           # Lexical token match object
        self.length=length   # Length of the floating point constant in bytes
        self.debug=debug     # Remember whether we are debugging or not
        self.fp=None         # The fp.FP subclass associated with the FP datum

    def build(self,trace=False):
        return self.fp.to_bytes()

    def has_overflow(self):
        return self.fp.has_overflow()

    def has_underflow(self):
        return self.fp.has_underflow()


class DFP(FloatingPoint):
    def __init__(self,mo,length,special=None,debug=False):
        super().__init__(mo,length)
        if special:
            self.fp=fp.DFP(None,length=self.length,special=special,debug=debug)
        else:
            self.fp=fp.DFP(self.mo,length=self.length,debug=debug)


# This object builds S-type constants.  It is very similar to ADCON.
class SCON(object):
    mask={12:(0xFFF,2),20:(0xFFFFF,3)}
    def __init__(self,expr,size=12):
        self.expr=expr      # Address expression from which constant is derived
        self.size=size      # Size of the constand in bits
        self.mask=None      # Displacement mask as an integer
        self.length=None    # Required constant length
        try:
            self.mask,self.length=SCON.mask[size]
        except KeyError:
            raise ValueError("%s invalid displacement size: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),size)) \
                    from None

    def __str__(self):
        return "%s(expr=%s)" % (self.__class__.__name__,self.expr)

    def build(self,asm,parsers,stmt,n,length,trace=False):
        if length != self.length:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type explicit length invalid: %s" % (n+1,length))

        value=parsers.evaluate_expr(asm,stmt,self.expr,debug=False,trace=trace)

        if isinstance(value,int):
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type value not an address: %s" % (n+1,value))

        try:
            base,disp=asm.bases.find(value,self.size,asm,trace=trace)
        except KeyError:
            # Could not resolve base register and displacement
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type constant could not resolve implied base "
                "register for location: %s" % (n+1,value)) from None

        if self.length==2:
            value=(base<<self.size)+(self.mask & disp)
        elif self.length==3:
            hi,lo=divmod(self.mask & disp,4096)
            value=(base<<self.size)+(lo<<8)+hi
        else:
            raise ValueError("%s unexpected S-Type constant length: %s" \
                % (assembler.eloc(self,"build",module=this_module),self.length))
        b=value.to_bytes(self.length,byteorder="big",signed=False)

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))

        return b


class String(object):
    def __init__(self,chrs,linepos):
        self.chrs=chrs
        self.linepos=linepos
        # This is the assembler value.  Double quotes have been handled by parser.
        # Double ampersands are handled here.
        self.achrs=self.chrs.replace("&&","&")

    def __str__(self):
        return "%s(chrs='%s',pos=%s)" \
            % (self.__class__.__name__,self.chrs,self.linepos)

    def build(self,length,trace=False):
        # Note input string is ASCII data natively
        string=self.achrs
        if len(string)<length:
            s=string.ljust(length)   # Pad on the right with ASCII blanks
        else:
            s=string[:length]  # Truncate on the right if needed

        s=self.translate(s)    # Let the subclass handle the character set
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(s),s))
        return s               # Return the character string as its to be assembled

    def infer_length(self):
        return len(self.achrs)


# String assembled using ASCII code points
class StringA(String):
    def __init__(self,chrs,linepos):
        super().__init__(chrs,linepos)

    def translate(self,string):
        return string


# String assembled using EBCDIC code points
class StringE(String):
    def __init__(self,chrs,linepos):
        super().__init__(chrs,linepos)

    def translate(self,string):
        return assembler.CPTRANS.a2e(string)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
