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
import asmtokens      # Access the common lexical tokens and parsing related objects

# Defined lexical analyzer token types
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
    # The lde
    # Context token type match debugging is enabled by setting the tdebug argument
    # to True in the individial calls to the context types
    def init(self):
        # Debug manager is not used for CSLA debug settings.  They are manually
        # controlled by the call to individual context definitions.
        # Set ldebug=True to cause a context's token list to be displayed when the
        # debug manager has ldebug set to True.
        # Set tdebug=True to cause the token type matching debug to be enabled
        
        self.init_abs_expr(ldebug=False,tdebug=False)
        self.init_start_region(tdebug=False)
        
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

    # START directive region operand
    def init_start_region(self,tdebug=False):
        c="region"
        self.ctx(c)
        self.type(c,[LABEL,EOO],debug=tdebug)


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

    # This override changes the default context scope class to asmtokens.AsmFSMScope
    # rather than the more generic fsmparser.PScope
    def ctx(self,name,lexctx=None,ccls=asmtokens.AsmFSMScope):
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
        self.ctx("loc",lexctx="absexpr")
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
        gs=self.scope()
        cs=self.cscope()
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


class START_Scope(asmtokens.AsmFSMScope):
    def __init__(self):
        super().__init__()
        # Parser results
        self.region_tok=None    # region argument lexical token.  See region()
        self.expr_list=[]       # Lexical token list of expression. See start_list()
        # Pass 0 results
        self.new_region=False   # Set if a new region is requested
        self.expr=None          # ArithExpr object of start address
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
        self.expr_list=cs.expr(value)

    def region(self,value):
        self.region_tok=value
        self.reg_name=value.extract()
    

if __name__ == "__main__":
    raise NotImplementedError(" - intended for import use only" % this_module)