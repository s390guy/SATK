#!/usr/bin/python3
# Copyright (C) 2014-2017 Harold Grovesteen
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

# This module provides support for the ASMA Macro Language.  Three types of macros
# are defined:
#   - built-in macros,
#   - ASMA Macro Language macros, and
#   - legacy compatible macros.
#
# Built-in macros are macros defined by statements supplied internally.  ASMA Macro
# Language macros are macros defined from statements supplied by external user sources.
# The underlying mechanisms are the same.
#
# ASMA Macro Language macros have some limitations driven the separateness of the
# two designs and certain internal structuring of assembler processes within ASMA
# itself.  Until these more fundamental changes are addressed full legacy compatible
# macros will not be possible.  _But_, some macro ability is better than none at all!
#
# ASMA Lessons Learned (so far)
# ---- ------- ------- --- ----
#
# The decision to abandon full use of compiler based technology within ASMA has been
# the key to the implementation.  With the real understanding that legacy mainframe
# assemblers apply selective use of expression evaluation, the ASMA Macro Language
# will continue this direction by optimizing expression recognizers and replacing
# full scale grammar based parsing with more granular approaches, for example using
# finite state machines, in conjunction with the lexical analyzer as opposed to
# LL1 grammars.
#
# The use of the technology discovered by Vaughn Pratt for operator precedence
# expression evaluation has also proven to be a success.  This technology has been
# further leveraged by generalizing the implementation to support any operators
# and any set of precedence relationships between them.
#
# The ASMA assembler.py module uses a special integration facility based upon the
# LL1 parsing technology in SATK to recognize expressions.  The use of LL1 parsing
# requires separation of operator precedence levels into separate grammatical
# productions.  While this worked well with the original pratt.py module that only
# supports arithmetic expressions, the approach is less feasible in the generalized
# approach in the new pratt3.py module.  The real requirements for expression
# recognition is to convert lexical tokens into objects that can be used by the
# precedence evalutor.  This does push certain syntactical errors into the precedence
# evaluator.
#
# The seqparser.py module is representative of this approach based solely on
# regular expressions.  As such, it is almost the extreme end such simplifications
# eliminating the use of traditional parsing techniques.  It is also only useful for
# truly simple parsing needs.
#
# At present no plans exist to replace the assembler usage of LL1 grammars with the
# new techniques being used by the macro facilities.  That may be a future objective.

this_module="%s.py" % __name__

# Python imports:
import datetime               # Access UTC time
import os.path                # For file path manipulation
import re                     # Access regular expressions

# SATK imports:
from satkutil import method_name       # Access the method names in method objects
import pratt3                 # Access a number of expression evalutor objects

# ASMA imports:
#import asmcards               # Access the continuation support
import asmbase
import asminput               # Access the input manager for macro expansions
#import asmfsmbp               # Access the finite-state machine parsers
import assembler              # Access the assembler for AsmPasses generation
import asmstmts               # Access statement classes
import macsyms                # Access symbolic variable and parameter implementation
import macopnd                # Access complex terms
import asmtokens              # Access Pratt expression evaluators


#
#  +--------------------------------+
#  |                                |
#  |   Macro Implementation Notes   |
#  |                                |
#  +--------------------------------+
#

#  Case [In]Sensitivity
#  ---- ---------------

# Assember case sensitivity is globally controlled by the assembler.Assembler object's
# case attribute provided when the object is instantiated.  It is set to True
# when the asma.py command-line argument '--case' is present.  It defaults to False
# othewise.
#
# Macro symbol and sequence symbol case sensitivity is controlled by the global
# case attribute.  Macro symbol access is provided through the SynbolID object.
# Controlling the case of a macro symbol occurs whenever a SymbolID object is
# created.  Outside of this module SymbolID objects are created by the objects:
#
# asmfsmbp.PLitKAttr   - Pratt expression token accessing a symbol's K' attribute
# asmfsmbp.PLitNattr   - Pratt expression token accessing a symbol's N' attribute
# asmfsmbp.PLitSym     - Pratt expression token that accesses a symbol's value
# asmfsmbp.PrototypeScope - Prototype statement parser for parameters
# asmfsmbp.SymRefRepMO - Manages the re match object created by SymRefType
# asmfsmbp.SymRefToken - The lexical token resulting from a match of SymRefType
# asmfsmbp.SymRefPart  - A searched matched by the SymRefType pattern.
#
# SymRefRepMO is a object dedicated to managing the regular expression match
# object created by the lexical type classe asmfsmbp.SymRefType and made available
# in the asmfsmbp.SymRefToken object.  Both asmfsmbp.SymRefToken and
# asmfsmbp.SymRefRepMO classes provide the SymID method for the purpose of creating.
# A SymbolID object from the recognized string. The state of case sensitivity must
# be available to the SymID method when called to ensure the correct case sensitive
# or insensitive symbol name is used internally.  It is a required positional
# parameter.
#
# The Pratt expression tokens use their internally created SymbolID object for
# access to the macro symbol table when accessing a symbol's value or one of its
# supported attributes.  In each case, the Pratt token uses the SymRefRepMO.SymID
# method.  For Pratt expression tokens, the state of case sensitivity is supplied
# by the external helper object, in these cases the macro Invoker object.
#
# When parsing a prototype statement, the PrototypeScope object itself handles
# case sensitivity for prototype positional and keyword parameters.  It is created
# externally by the MacroLanguage object setting the current case sensitivity state,
# rather than having the parser create it automatically.
#
# Because case sensitivity state effects macro definition and execution including
# the creation of statements from model statements, the state of case sensitivity
# must be known during all of these macro related processes.  It is supplied to
# each of these objects when instantiated:
#
# MacroLanguage - by directly accessing the Assembler object's case attribute
# Invoker       - also by directly accessing the Assembler object's case attribute.
# EngineState   - by directly accessing the macro's Invoker object's case attribute.
# Macro         - as a required instance argument when created.
#
# Sequence symbol case sensitivity is handled completely by the __seq() method
# of the MacroLanguage object when a sequence symbol appears in a macro directive's
# name field.  When a sequence symbol is part of the directives operands (AGO and
# AIF) the respective MacroLanguage method handles the case sensitivity.


# This excpetion is used when a user error occurs during the invocation of a
# macro.  assembler.AssemblerError is raised for user errors during macro
# definition.
#
# Instance Arguments:  All are optional and default to None if not supplied
#   line    The assembler statement generating the error report
#   source  The Source object identifying the macro statement detecting the error
#   linepos The location within the detecting statement of the error
#   invoke  Whethet the error was raised during an invoked macro (True) or during a
#           macro definition (False)
#   msg     The nature of the error.
# Note: This object expects to be created by Invoker.error() method.
class MacroError(Exception):
    def __init__(self,line=None,source=None,linepos=None,invoke=False,msg=""):
        # These attributes identify the location of macro directive detecting the error
        self.linepos=linepos     # Position in the defining statement of the error
        self.source=source       # Source of error detecting statement
        self.invoke=invoke       # Whether error occurred during an invoked macro
        # If available this is intended to enhance the reporting of the error

        # These attributes relate to location and nature of the macro statement whose
        # invocation of the macro generated the error in the macro processing
        self.line=line   # Assembler statement for which the error is reported
        self.msg=msg     # Nature of the error.

        # Generate the error reported if this error is not caught.
        string=""
        if line is not None:
             string="%s" % line
        if len(msg)>0:
             string="%s %s" % (string,msg)
        super().__init__(string)


#
#  +----------------------------+
#  |                            |
#  |   Macro Defining Classes   |
#  |                            |
#  +----------------------------+
#

# Class representing a macro's prototype statement
# Instance Arguments:
#   macid      The name of the macro being defined by this prototype as a string
#   lblsym     The variable symbol used for the macro's label field content as a
#              string.  Default is None.
#   pos        A list of positional parameters.  Each parameter is a string with
#              starting with an '&'.  Default is an empty list.
#   keywords   A dictionary of keyword positional paramaters with their assigned
#              default values.  Each parameter is a string starting with an '&'.
#              Each default value is a string.  Default is an empty dictionary.
class Prototype(object):
    def __init__(self,macid,lblsym=None,positionals=[],keywords={}):
        self.macid=macid.upper()   # Macro ID of this macro
        self.lblsym=lblsym         # The label field variable symbol
        self.pos=positionals       # List of position parameters
        self.keywords=keywords     # Dictionary of keyword parameters with defaults

        self.noparms = (len(self.pos)==0) and (len(self.keywords)==0)

    def __str__(self):
        string="Prototype(macid='%s')" % self.macid
        string="%s\n    label: %s" % (string,self.lblsym)
        if not self.noparms:
            string="%s\n    pos: %s" % (string,self.pos)
            string="%s\n    keywords: %s" % (string,self.keywords)
        return string


# Base class for all macros
class Macro(object):
    Arith=asmtokens.ArithEval()   # Arithmetic Evaluator
    Binary=asmtokens.BinaryEval() # Binary Evaluator
    def __init__(self,prototype,case,defn=None):
        assert isinstance(prototype,Prototype),\
            "%s 'prototype' argument must be a prototype :%s" \
                % (assembler.eloc(self,"__init__",module=this_module),prototype)
        assert case in [True,False],\
            "%s 'case' argument must be either True or False: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),case)

        self.name=prototype.macid  # Macro Name
        self.prototype=prototype   # Prototype object
        self.case=case             # Specifies if case sensitivity is enabled
        self.engine=MacroEngine(self.name) # My definition in terms of MacroOp objects
        self._defined=defn         # source statement number where definition occurs
        self._refs=[]              # source statements referencing this macro
        # XREF object for my references
        self._xref=None            # see asmoper.MacroTable.define() method.

        # Controls whether &SYSLIST is created when invoked
        self.syslist=False

        # Debug switch
        self.idebug=False          # If True trace macro invocation

    # This method initializes the prototype parameter values when the macro is
    # invoked.  Only unique SETC local symbols are created.  The local symbolic
    # variable may be unsubscripted or subscripted depending upon whether the
    # parameter defined a single value or multiple in a list.
    def __initparm(self,parm,pvalue,lcls):
        assert isinstance(parm,str),\
            "%s 'parm' argument must be a string: %s" \
                % (assembler.eloc(self,"__initparm",module=this_module),parm)
        assert isinstance(pvalue,macsyms.Parm_Val),\
            "%s 'pvalue' argument must be a macsyms.Parm_Val object: %s" \
                % (assembler.eloc(self,"__initparm",module=this_module),pvalue)

        # Enforce symbol case sensitivity rule.
        if not self.case:
            symname=parm.upper()
        else:
            symname=parm

        # Create an unsubscripted symbolic variable to hold the parameter string
        symid=macsyms.SymbolID(symname)
        symo=lcls.defp(symid,parm=True,unique=True,ro=True)
        # At this point the unsubscripted symbol has been added to the macro
        # dictionary.
        # Update it with the string assigned to the parameter.
        symo.setValue(symid,pvalue,user=False)

  #
  # These methods build macro operations from macro directives
  #
    # Add a ACTR operation
    def _actr(self,lineno,expr,seq=None,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(ACTR(lineno,expr),seq=seq)

    # Add a simple AGO operation
    def _ago(self,lineno,dest,seq=None):
        self.engine.define(AGO(lineno,dest),seq=seq)

    # Add a computed AGO operation
    def _agoc(self,lineno,dest,expr,seq=None,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(AGOC(lineno,dest,expr),seq=seq)

    # Add an AIF operation
    def _aif(self,lineno,dest,expr,seq=None,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(AIF(lineno,dest,expr),seq=seq)

    # Add an ANOP operation
    def _anop(self,lineno,seq=None):
        self.engine.define(ANOP(lineno),seq=seq)

    # Add a GBLA operation
    def _gbla(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(GBLA(lineno,symid),seq=seq,syslist=syslist)

    # Add a GBLB operation
    def _gblb(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(GBLB(lineno,symid),seq=seq,syslist=syslist)

    # Add a GBLC operation
    def _gblc(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(GBLC(lineno,symid),seq=seq,syslist=syslist)

    # Add a LCLA operation
    def _lcla(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(LCLA(lineno,symid),seq=seq,syslist=syslist)

    # Add a LCLB operation
    def _lclb(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(LCLB(lineno,symid),seq=seq,syslist=syslist)

    # Add a LCLC operation
    def _lclc(self,lineno,symid,seq=None,syslist=False):
        self.engine.define(LCLC(lineno,symid),seq=seq,syslist=syslist)

    # Add a MEND operation
    def _mend(self,lineno,seq=None):
        self.engine.define(MEND(lineno),seq=seq)

    # Add a MEXIT operation
    def _mexit(self,lineno,seq=None):
        self.engine.define(MEXIT(lineno),seq=seq)

    # Add a model statement to the macro
    def _model(self,lineno,mdlstmt,seq=None,debug=False,syslist=False):
        if debug:
            cls_str=assembler.eloc(self,"_model",module=this_module)
            print("%s [%s] '%s'" % (cls_str,lineno,mdlstmt))
        self.syslist=self.syslist or syslist
        self.engine.define(Model(lineno,mdlstmt),seq=seq)

    # Add a SETA operation
    def _seta(self,lineno,symid,expr_list,debug=False,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(SETA(lineno,symid,expr_list),seq=None)

    # Add a SETB operaion
    def _setb(self,lineno,symid,expr,debug=False,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(SETB(lineno,symid,expr),seq=None)

    # Add a SETC operation
    # dmethod(self.lineno,setname,exp_list)
    def _setc(self,lineno,symid,expr_list,debug=False,syslist=False):
        self.syslist=self.syslist or syslist
        self.engine.define(SETC(lineno,symid,expr_list),seq=None)

    # Invokes the macro engine
    # Returns
    #   a model statement as a string
    #   None if the macro has ended.
    # Exceptions:
    #   MacroError if a user created error occurred
    def invoke(self):
        model=self.engine.run()
        return model

    # Parses the macro statements parameters if the prototype has parameters defined
    # Updates the supplied local variable symbol table as follows:
    #   If a keyword parameter is provided for a defined keyword, it is assigned the
    #   value found in the macro statement.  If a keyword is encountered but not
    #   defined in the prototype, it is silently ignored.
    #
    #   Sequentially assign positional parameters to each defined positional in
    #   the prototype.  Additional positional parameters are ignored.  Unspecified
    #   positional prototype parameters are assigned the empty string.
    # Method Arguments:
    #   stmt     Input assembler.Stmt object
    #   lcls     The local MacSymbols in which parameters are defined
    # Return: None
    # Exceptions:
    #   AssemblerError if parameters not parsable or duplicae keyword parameter found
    #   SymbolError if sublist parsing encounters an error
    def parms(self,stmt,lcls,debug=False):
        pdebug=debug
        proto=self.prototype
        Parm_Val=macsyms.Parm_Val

        if __debug__:
            if debug:
                print("%s proto: %s" \
                    % (assembler.eloc(self,"parms",module=this_module),proto))

        # Define the prototype name field parameter if defined and specified
        lblsym=proto.lblsym
        if lblsym is not None:
            if stmt.label:
                lbl=stmt.label
            else:
                lbl=None
            lbl_parm=Parm_Val(value=lbl,onum=0)
            self.__initparm(lblsym,lbl_parm,lcls)

        # Treat anything in the macro statement after operation field as comments
        # because the prototype does not define any parameters
        if proto.noparms:
            return

        stmt_kparms=stmt.keywords       # Keyword parameters in statement, a dict
        proto_kparms=proto.keywords     # Prototype keyword parameters, a dict

        # Validate that all of the keywords parameters in the statement are in
        # fact defined in the macro prototype.
        undefined=[]
        for stmt_key,stmt_kparm in stmt_kparms.items():
            try:
                proto_kparm=proto_kparms[stmt_key]
            except KeyError:
                undefined.append(stmt_key)
        if len(undefined)>0:
            string=""
            for undef in undefined:
                string="%s,%s" % (string,undef)
            string=string[1:]
            if len(undefined)<2:
                s=""
            else:
                s="s"
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                msg="undefined keyword parameter%s found: %s" % (s,string))

        # Define all of the keyword symbols as specified or with prototype defaults
        for key,proto_kparm in proto.keywords.items():
            # key is the keyword parameter
            # value is a keyword prototype macsyms.MacroParm object
            try:
                key_parm=stmt_kparms[key]
                # key_parm is the keyword statement macsyms.MacroParm object
                value=key_parm.value
            except KeyError:
                # parameter not specified so set its default now
                value=proto_kparm.value
            # Define the keyword in the macro dictionary
            self.__initparm(key,Parm_Val(value=value),lcls)

        # Define the positional parameters with specified or implied empty string
        stmt_pos=stmt.pos       # Positinal parameter (macsyms.MacroParm)
        proto_pos=proto.pos     # Prototype positional parameter (macsyms.MacroParm)
        poss=len(stmt_pos)      # Number of positional parameters in statement
        posn=len(proto_pos)     # Number of positional parameters in prototype

        # Set parameter values
        nparms=max(posn,poss)
        sysl=[]    # We accumulate syslist Parm_Val objects here
        if poss>posn and self.syslist:
            # When doing &SYSLIST we need to process all statement parms even
            # if not defined in prototype.  This happens when the statement has
            # more positionals than are defined by the prototype
            for ndx in range(poss):
                pval=Parm_Val(value=stmt_pos[ndx].value)
                sysl.append(pval)
                if ndx<posn:
                    self.__initparm(proto_pos[ndx].positional,pval,lcls)
        else:
            # Otherwise we only need to process the statement positionals we have
            # and create omitted entries for remaining prototype positionals.
            for ndx in range(posn):
                if ndx<poss:
                    val=stmt_pos[ndx]
                    if val is None:
                        pval=Parm_Val()   # Ommitted positional parameter
                    else:
                        pval=Parm_Val(value=stmt_pos[ndx].value)
                    if self.syslist:
                        sysl.append(pval)
                else:
                    # Positional parameters not present at all in statement
                    pval=Parm_Val()
                self.__initparm(proto_pos[ndx].positional,pval,lcls)

        if self.syslist:
            syslist=macsyms.SYSLIST(label=lbl,posparms=sysl)
            self.__initparm("&SYSLIST",syslist,lcls)

    # Update this macro cross reference with this reference
    def reference(self,lineno):
        self._xref.ref(lineno)


class Built_In(Macro):
    def __init__(self,proto,case):
        super().__init__(proto,case)

        self.define()

    # This method calls the MacroEngine object defining its operations
    # Each Built_In subclass must provide this method
    def define(self):
        cls_str=assembler.eloc(self,"define",module=this_module)
        raise NotImplementedError("%s subclass %s must implement define() method" \
            % (cls_str,self.__class__.__name__))


#
#  +----------------------+
#  |                      |
#  |   Macro Operations   |
#  |                      |
#  +----------------------+
#

# This set of classes define the internal representation of macro operations.
# These objects define the underlying interpretation engine of a macro definition.
# The MacroEngine object encapsulates these internal functions and exposes an
# interface used by both user defined macros and built-in macros for defining
# the engines functionality.
class MacroEngine(object):
    def __init__(self,name):
        # These attributes are built during macro definition by calls to the
        # define() method.
        self.name=name   # Name of the macro using this engine
        self.ops=[]      # List of macro operations defining the macro's functions
        self.seq={}      # Dictionary of sequence symbols used to control flow
        self.syslist=False  # Whether to build &SYSLIST when invoked.
        self.done=False  # Set to True when Mend object added

    # This method drives the resolution of operation's sequence symbol usage.
    def __resolve(self):
        for n in range(len(self.ops)):
            op=self.ops[n]
            dest=[]
            for seq in op.dest_seq:
                try:
                    ndx=self.seq[seq]
                except KeyError:
                    raise assembler.AssemblerError(line=op.lineno,\
                        msg="%s macro definition failed, sequence symbol "
                            "undefined: %s" % (self.name,seq)) from None
                dest.append(ndx)
            op.dest=dest
            op.post_resolve()

    # Add a macro operation to the engine.
    # Method arguments:
    #   op        An instance of MacroOp, normally subclassed
    #   seq       Name field sequence symbol associated with the operation
    # Note: this is where sequence symbols get defined.  They get referenced
    # in self.__set_next() when a branching statement references it.
    # Exceptions:
    #   assembler.AssemblerError may be raised
    def define(self,op,seq=None,syslist=False):
        assert isinstance(op,MacroOp),\
            "%s 'op' argument must be a MacroOp object: %s" \
                % (assembler.eloc(self,"define",module=this_module),op)
        assert not self.done,\
            "%s can not add MacroOp, Mend encountered: %s" \
                % (assembler.eloc(self,"define",module=this_module),\
                    op.__class__.__name__)

        self.syslist=self.syslist or syslist

        # Define the macro directives sequence symbol if provided
        next_loc=len(self.ops)  # Index of operation being added
        if seq is not None:
            assert isinstance(seq,str),\
            "%s 'seq' argument must be a string or None: %s" \
                % (assembler.eloc(self,"define",module=this_module),seq)
            self.seq[seq]=next_loc

        if isinstance(op,MEND):
            # raises assembler.AssemblerError exception for undefined sequence symbol
            self.__resolve()
            self.done=True

        op.location(next_loc)
        self.ops.append(op)

    # Converts an macro operation index into its relavant statement
    # Method Argument:
    #   n   macro operation index value
    # Returns:
    #   the source statement number in which the operation is defined.
    def op2stmt(self,n):
        return self.ops[n].lineno

    # This method exeutes macros.  Because recursive macros are possible, the
    # caller must maintain the engine state externally.
    def run(self,state,debug=False):
        next=state.next       # Determine the next operation, if any
        state.result=None     # Eliminate the result from the previous call
        idebug=state.idebug or debug   # Set invocation debug switch

        if next is None:
            loc=0             # Starting the macro invocation
        else:
            loc=next          # Already started it, pick up where we left off

        while True:
            # Fetch the operation
            op=self.ops[loc]

            # Execute it
            try:
                loc,result=op.operation(state,debug=idebug)
            except MacroError as me:
                newme=state.exp.error(op,me.msg)
                #print("macro engine: newme: %s" % newme)
                raise newme from None
            except Exception as exp:
                print("INTERNAL ERROR in macro %s, %s operation line: %s" \
                    % (self.name,op.__class__.__name__,op.lineno))
                #raise exp
                raise

            # next being None indicates the macro has ended.
            if loc is None:
                state.next=None
                # None ends the input source and the macro invocation.
                return state
            # If a model statement has been generated, return it as an input
            if isinstance(result,list):
                state.next=loc
                state.result=result
                return state        # Return the engine state
            assert result is None,\
                "%s unexpected result from macro op: %s" \
                    % (assembler.eloc(self,"run",module=this_module),result)

    # Start the engine by returning its initial state
    def start(self,exp):
        return EngineState(exp)

class EngineState(object):
    def __init__(self,exp):
        assert isinstance(exp,Invoker),\
            "%s 'exp' argument must be an Invoker: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),self.exp)

        # These attributes maintain the dynamic state of the MacroEngine and
        # preserve the state between each cycle of the MacroEngine.
        #
        # Next index of the next operation to be performed.
        self.next=None
        # If not None, the resulting model statement fron this cycle of the MacroEngine
        self.result=None

        # Global state of the MacroEngine for this invocation.
        self.exp=exp             # This state's Invoker object
        self.case=exp.case       # Need case to properly locate symbols
        self.lcls=exp.lcls       # The local macro symbol dictionary
        self.idebug=exp.idebug   # Pick up invoke debug switch from Invoker
        self.lineno=exp.lineno   # Assembler statement invoking the macro
        self._actr=4096          # Macro ACTR value

    # Access the assembler symbol table (but don't create a listing cross-reference
    # entry).
    # WARNING: Any changes to method arguments must be matched with the arguments of
    # the assembler.Assembler._getSTE_Ref() and Invoker._getSTE_Ref()
    def _getSTE_Ref(self,name,line):
        return self.exp._getSTE_Ref(name,line)

    def actr(self):
        if self._actr:
            self._actr-=1
            return
        else:
            raise MacroError(invoke=True,msg="aborted - ACTR exhausted")

    # This method evaluates macro expressions during macro invocation.  It is
    # the interface to asmbase.ASMExpr expression evalutaion.
    # Method Arguments:
    #   expr    The asmbase.ASMExpr subclass being evalutated
    # Returns:
    #   a A_Val, B_Val, C_Val object or integer
    # Exception:
    #   MacroError generated from a pratt3.PParserError encountered or directly
    #   during evaluation.
    def expr(self,expr,debug=False,trace=False):
        try:
            return expr.evaluate(external=self.exp,debug=debug,trace=False)
        except pratt3.PParserError as pe:
            # Convert PParserError into a MacroError
            msg="%s: '%s'" % (pe.msg,pe.ptok.src.string)
            raise MacroError(invoke=True,msg=msg) from None

    # Returns the A_Val object associated with the SymbolID object
    def geta(self,symid):
        return self.lcls.geta(symid)

    # Returns the B_Val object associated with the SymbolID object
    def getb(self,symid):
        return self.lcls.getb(symid)

    # Returns the C_Val object associated with the SymbolID object
    def getc(self,symid):
        return self.lcls.getc(symid)

    # Return True if the MacroEngine is done
    def isDone(self):
        return self.next is None

    # Actually set a GBLA/LCLA variable by updating its A_Val object
    def seta(self,symid,value):
        self.lcls.seta(symid,value)

    # Actually set a GBLB/LCLB variable by updating its B_Val object
    def setb(self,symid,value):
        self.lcls.setb(symid,value)

    # Actually set a GBLB/LCLB variable by updating its C_Val object
    def setc(self,symid,value):
        self.lcls.setc(symid,value)


# The base class for all macro operations.  Helper methods for operations are also
# provided.
# Method Arguments:
#   lineno    The source statement number that defined this operation
#   next      The sequence symbol as a string defining the next operation to be
#             executed.  Defaults to None.  If None, the next sequential macro op
#             is assumed.
class MacroOp(object):
    def __init__(self,lineno,dest=[]):
        self.lineno=lineno    # Statement from which this operation derived

        # List of sequence symbols to which this Operation may branch.
        # An empty list implies the next sequential instruction
        if not isinstance(dest,list):
            self.dest_seq=[dest,]
        else:
            self.dest_seq=dest

        # These attributes are provided by the MacroEngine.define() method
        self.loc=None     # My index in the MacroEngine.ops list
        self.next=None    # Next sequential operation index to execute
        # This list is created from self.dest_seq by MacroEngine.__resolve() method
        self.dest=[]      # List of operation indices to which this op may branch

  #
  # Macro Operation Definition Helper Methods
  #

    # Defines my location and the default next operation.
    # Unless overridden, the next operation index is this op's index plus one.
    def location(self,loc):
        self.loc=loc
        self.next=loc+1

    # Post-processes sequence symbol resolution, if needed
    # For most operations, this method does nothing.
    def post_resolve(self):
        pass

  #
  # Macro Operation Execution Helper Methods
  #

    # DEPRECATED IN FAVOR OF ASMBASE.ASMExpr USAGE RATHER THAN pratt3.PExpr USAGE
    # This method evaluates macro expressions during macro invocation.  It is the
    # interface to the pratt3 module's usage by macros.
    #
    # Method arguments:
    #   state   The active EngineState object
    #   expr    The pratt3.PExpr object containing the PToken objects being evluated
    #   peval   The pratt3.PParser object performing the evaluation
    # Returns:
    #   a A_Val, B_Val, C_Val object or integer
    # Exception:
    #   MacroError generated from a pratt3.PParserError encountered
    def evaluate(self,state,expr,peval,debug=False,trace=False):
        try:
            return peval.run(expr,external=state,debug=debug,trace=False)
        except pratt3.PParserError as pe:
            # Convert PParserError into a MacroError
            msg="%s: '%s'" % (pe.msg,pe.ptok.src.string)
            raise MacroError(invoke=True,msg=msg) from None

    # This method evaluates macro expressions during macro invocation.  It is
    # the interface to asmbase.ASMExpr expression evalutaion.
    # Method Arguments:
    #   state   The active EngineState object
    #   expr    The asmbase.ASMExpr subclass being evalutated
    # Returns:
    #   a A_Val, B_Val, C_Val object or integer
    # Exception:
    #   MacroError generated from a pratt3.PParserError encountered
    def evaluate_expr(self,state,expr,debug=False,trace=False):
        try:
            return expr.evaluate(external=state.exp,debug=debug,trace=False)
        except pratt3.PParserError as pe:
            # Convert PParserError into a MacroError
            msg="%s: '%s'" % (pe.msg,pe.ptok.src.string)
            raise MacroError(invoke=True,msg=msg) from None
        except assembler.LabelError as le:
            # Convert a LabelError into a MacroError
            raise MacroError(invoke=True,msg=le.msg) from None

    # All subclasses must provide an operation method that returns next.
    # Returns:
    #   a tuple: (next,result)
    #   The first element of the tuple is the next operation to be performed
    #   The second element of the tuple is the result of the operation.
    def operation(self,state,debug=False):
        raise NotImplementedError("%s subclass %s must provide operation() method" \
            % (assembler.eloc(self,"operation",module=this_module),\
                self.__class__.__name__))

    # Used to convert result of arithmetic expressions into Python integers.
    def to_integer(self,value):
        if isinstance(value,macsyms.A_Val):
            return value.value()
        return value

    # Used to convert the result of a logical expression into a Python True or False
    def to_logical(self,value):
        if isinstance(value,int):
            return value!=0
        return value.value()!=0


class ACTR(MacroOp):
    def __init__(self,lineno,expr):
        super().__init__(lineno)
        self.expr=expr        # Computed ACTR arithmetic expression
    def operation(self,state,debug=False):
        value=self.evaluate_expr(state,self.expr,debug=debug,trace=False)

        if isinstance(value,(macsyms.A_Val,macsyms.B_Val,int)):
            new_value=self.to_integer(value)
        else:
            if isinstance(value,C_Val):
                found="character value"
            else:
                raise ValueError("ACTR %s encountered unexpected result: %s"
                    % (self.lineno,value))
            raise MacroError(invoke=True,\
                msg="ACTR computation requires arithmetic result: %s" % found)

        # Explicitly set the ACTR value
        if new_value<0:
            # Treat negative values as zero - next branch will fail
            state._actr=0
        else:
            state._actr=new_value

        return (self.next,None)


class AGO(MacroOp):
    def __init__(self,lineno,dest):
        super().__init__(lineno,dest=dest)

    def operation(self,state,debug=False):
        state.actr()    # decrement ACTR and abort if already zero
        state.exp.mhelp_02(self.lineno,self.next)
        return (self.next,None)

    def post_resolve(self):
        self.next=self.dest[0]


class AGOC(MacroOp):
    def __init__(self,lineno,dest,expr):
        super().__init__(lineno,dest=dest)
        self.expr=expr        # Computed AGO arithmetic expression

    def operation(self,state,debug=False):
        #value=self.evaluate(state,self.expr,Macro.Arith,debug=debug,trace=False)
        value=self.evaluate_expr(state,self.expr,debug=debug,trace=False)

        if isinstance(value,(macsyms.A_Val,int)):
            ndx=self.to_integer(value)
        else:
            if isinstance(value,macsyms.B_Val):
                found="binary value"
            elif isinstance(value,C_Val):
                found="character value"
            else:
                raise ValueError("AGO %s encountered unexpected result: %s"
                    % (lineno,value))
            raise MacroError(invoke=True,\
                msg="AGO computation requires arithmentic result: %s" % found)

        state.actr()    # Decrement ACTR and abort if exhausted

        # Determmine next statement to be invoked
        if ndx<1 or ndx > len(self.dest):
            next=self.next
        else:
            next=self.dest[ndx-1]

        # Do the branch...
        state.exp.mhelp_02(self.lineno,next)
        return (next,None)


class AIF(MacroOp):
    def __init__(self,lineno,dest,expr):
        super().__init__(lineno,dest=dest)
        self.expr=expr        # AIF logical expression

    def operation(self,state,debug=False):
        state.exp.mhelp_04()   # Dump variable symbols if requested

        value=self.evaluate_expr(state,self.expr,debug=False,trace=False)

        if isinstance(value,(macsyms.A_Val,macsyms.B_Val,int)):
            logical=self.to_logical(value)
        else:
            if isinstance(value,C_Val):
                found="character value"
            else:
                raise ValueError("AIF %s encountered unexpected result: %s"
                    % (self.lineno,value))
            raise MacroError(invoke=True,\
                msg="AIF computation at source line %s requires logical result: %s" \
                    % (self.lineno,found))

        state.actr()    # Decrement ACTR and abort if exhausted

        if logical:
            next=self.dest[0]
        else:
            next=self.next

        # Do the branch...
        state.exp.mhelp_02(self.lineno,next)
        return (next,None)


class ANOP(MacroOp):
    def __init__(self,lineno):
        super().__init__(lineno)

    def operation(self,state,debug=False):
        return (self.next,None)


class GBLA(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        sym=state.exp.gbls.defa(symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class GBLB(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        sym=state.exp.gbls.defb(symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class GBLC(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        sym=state.exp.gbls.defc(symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class LCLA(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        state.exp.lcls.defa(symid)
        return (self.next,None)


class LCLB(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        state.exp.lcls.defb(symid)
        return (self.next,None)


class LCLC(MacroOp):
    def __init__(self,lineno,symref):
        assert isinstance(symref,macopnd.PSymRef),\
            "%s 'symref' argument must be a macopnd.PSymRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symref)

        super().__init__(lineno)
        self.symid=symref

    def operation(self,state,debug=False):
        symid=self.symid.SymID(state,debug=debug)
        state.exp.lcls.defc(symid)
        return (self.next,None)


class MEND(MacroOp):
    def __init__(self,lineno):
        super().__init__(lineno)

    def location(self,loc):
        self.loc=loc

    # Do not set next sequential instruction
    def operation(self,state,debug=False):
        state.exp.mhelp_08()
        return (None,None)


class MEXIT(MacroOp):
    def __init__(self,lineno):
        super().__init__(lineno)

    def location(self,loc):
        self.loc=loc

    # Do not set next sequential instruction
    def operation(self,state,debug=False):
        state.exp.mhelp_08()
        return (None,None)


class Model(MacroOp):
    def __init__(self,lineno,model,debug=False):
        self.model=model
        super().__init__(lineno)

    def operation(self,state,debug=False):
        self.model.replace(state.exp)  # Perform any symbolic replacements
        plines=self.model.create()     # Create physical lines for macro source
        return (self.next,plines)


# Shared portion of SETA, SETB, and SETC operations
class SETx(MacroOp):
    def __init__(self,lineno):
        super().__init__(lineno)

    # Shared process identifies symbol being set, and, for subscripted set symbols
    # drives the updating of successive symbols from each operand in the statement
    def process(self,state,debug=False):
        setsym=self.setsym
        setname=setsym.symname    # Retrieve the set symbol name being SET
        exp=state.exp         # asmmac.Invoker object
        if not setsym.hasSubscript():
            # Perform unsubscripted SET
            # The single value is the first and only operand
            expr=self.expr[0]
            try:
                set_val=expr.evaluate(external=exp,debug=False)
            except assembler.LabelError as le:
                raise MacroError(invoke=True,msg=le.msg) from None
            if __debug__:
                if debug:
                    print("%s set_val: %s" \
                        % (assembler.eloc(self,"process",module=this_module),\
                            set_val))
            symid=macsyms.SymbolID(setname)
            self.setx(state,symid,set_val,0,debug=debug)
            return

        # Perform subscripted set
        exp=state.exp         # asmmac.Invoker object
        ndx_expr=setsym[0]    # Fetch the subscript expression
        ndx=ndx_expr.evaluate(external=exp,debug=debug)
        if not isinstance(ndx,int):
            raise MacroError(invoke=True,\
                msg="symbol %s subscript 1 not an integer: %s" % (setname,ndx))

        for n,expr in enumerate(self.expr):
            try:
                set_val=expr.evaluate(external=exp,debug=debug)
            except assembler.LabelError as le:
                raise MacroError(invoke=True,msg=le.msg) from None
            symid=macsyms.SymbolID(setname,indices=[ndx,])
            # Let the subclass set the value
            self.setx(state,symid,set_val,n,debug=debug)
            ndx+=1   # Bump the subscript to the next index

    # Lets the subclass actually store away a value from an evalutated expression
    # with its type sensitive handling
    # Method Arguments:
    #   state    asmmacs.Invoker object of this macro
    #   symid    macsyms.SymbolID object of the set symbol being set
    #   result   Result of the operand expression's evaluation defining the value
    #   n        Operand number, starting at zero, of the value (for error reporting)
    # Exceptions:
    #   MacroError excpetion if subclass can not set the calculated value
    def setx(self,state,symid,result,n,debug=False):
        raise NotImplementedError("%s subclass %s must supply setx() method" \
            % (assembler.eloc(self,"setx",module=this_module),\
                self.__class__.__name__))


class SETA(SETx):
    def __init__(self,lineno,setsym,expr,debug=False):
        super().__init__(lineno)
        assert isinstance(setsym,macopnd.SymbolRef),\
            "%s 'setsym' argument must be a macopnd.SymbolRef object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),setsym)

        self.setsym=setsym     # Prepared SymbolRef object
        self.expr=expr         # List of prepared arithmetic expressions
        super().__init__(lineno)

    # Perform the statements operation
    def operation(self,state,debug=False):
        self.process(state,debug=debug)   # Do the set(s)
        return (self.next,None)   # Execute next macro operation

    # Validate arithmetic expression result and set an arithemtic symbol's or array
    # element's value.
    def setx(self,state,symid,value,n,debug=False):
        if isinstance(value,int):
            v=macsyms.A_Val(value)
        elif isinstance(value,macsyms.A_Val):
            v=value
        elif isinstance(value,macsyms.B_Val):
            if value._value!=0:
                v=macsyms.A_Val(1)
            else:
                v=macsyms.A_Val(0)
        elif isinstance(value,macsyms.C_Val):
            v=value.sdterm(excp=False,debug=debug)
            if v is None:
                raise MacroError(invoke=True,\
                    msg="SETA operand %s requires arithmentic result, character "
                        "value: %s" % (n+1,value))
            v=macsyms.A_Val(value=v)
        else:
            raise ValueError("[%s] SETA operand %s encountered unexpected "
                "result: %s" % (self.lineno,n+1,value))
            raise MacroError(invoke=True,\
                msg="SETA operand %s requires arithmentic result: %s" \
                    % (n+1,found))

        state.seta(symid,v)


class SETB(SETx):
    def __init__(self,lineno,setsym,expr,debug=False):
        self.setsym=setsym
        self.expr=expr
        super().__init__(lineno)

    def operation(self,state,debug=False):
        self.process(state,debug=debug)   # Do the set(s)
        return (self.next,None)

    # Validate binary expression result and set a binary symbol's or array
    # element's value
    def setx(self,state,symid,value,n,debug=False):
        if isinstance(value,(int,macsyms.A_Val)):
            if value!=0:
                v=macsyms.B_Val(1)
            else:
                v=macsyms.B_Val(0)
        elif isinstance(value,macsyms.B_Val):
            v=value
        elif isinstance(value,(str,macsyms.C_Val)):
            raise MacroError(invoke=True,\
                msg='SETB operand %s requires logical or arithmentic result: "%s"'\
                    % (n+1,value))
        else:
           raise ValueError(\
               "%s [%s] SETB operand %s encountered unexpected result: %s" \
               % (assembler.eloc(self,"setx",module=this_module),\
                   self.lineno,n+1,value))

        state.setb(symid,v)


class SETC(SETx):
    def __init__(self,lineno,setsym,expr,debug=False):
        assert isinstance(expr,list),\
            "%s 'expr' argument must be a list: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),expr)
        if __debug__:
            if debug:
                for n,item in enumerate(expr):
                    assert isinstance(item,asmbase.ASMExprChar),\
                        "%s [%s] expr item[%s] must be an asmbase.ASMExprChar "\
                            "object: %s" \
                                % (assembler.eloc(self,"__init__",\
                                    module=this_module),lineno,n,item)

        self.setsym=setsym
        self.expr=expr
        if __debug__:
            if debug:
                print("%s [%s] expr: %s" \
                    % (assembler.eloc(self,"__init__",module=this_module),lineno,\
                        self.expr))
                for n,item in enumerate(self.expr):
                    print("%s [%s] expr[%s]:%s" \
                        % (assembler.eloc(self,"__init__",module=this_module),
                            lineno,n,item.display(string=True)))

        super().__init__(lineno)

    def operation(self,state,debug=False):
        self.process(state,debug=debug)   # Do the set(s)
        return (self.next,None)

    # Validate character expression result and set a character symbol's or array
    # element's value
    def setx(self,state,symid,value,n,debug=False):
        #print("%s value: %s" \
        #    % (assembler.eloc(self,"setx",module=this_module),value))
        if isinstance(value,str):
            val=macsyms.C_Val(value)
        elif isinstance(value,int):
            # Convert integer into a self-defining term string
            string="%s" % value
            val=macsyms.C_Val(string)
        elif isinstance(value,macsyms.A_Val):
            string="%s" % value._value
            val=macsyms.C_Val(string)
        else:
            assert isinstance(value,macsyms.C_Val),\
                "%s 'value' argument must be a C_Val object: %s" \
                    % (assembler.eloc(self,"setx",module=this_module),value)
            val=value
        if __debug__:
            if debug:
                print("%s symid, %s, being set to: %s " \
                    % (assembler.eloc(self,"setx",module=this_module),symid,val))
        state.setc(symid,val)

#
#  +--------------------------------+
#  |                                |
#  |   Macro Processing Interface   |
#  |                                |
#  +--------------------------------+
#

# This class performs macro language processing.  It is supplied to an
# asminput.MacroSource object to extract generated model statements from a macro,
# inject them into the source and then replace symbolic variables in the input.
#
# On the macro side of the interface, it enteracts with a MacroEngine object to
# interpret a defined macro.  On the assembler input side, it passes raw input
# statements, strings, to the MacroSource object for injection into the universal
# input source, the asminput.LineBuffer object.
#
# Methods used for invoking a macro definition:
#   invoke()     Used by the MacroLanguage object to prepare the macro for invocation
#                of the macro statement occurring in assembler source.  See the
#                MacroLanguage.macstmt() method for its context.
# Methods used by the asminput.MacroSource object during invocation:
#   enter()      Causes the macro to be entered, initializing the macro engine.
#                See the asminput.MacroSource.init() method.
#   generate()   Returns a new model statement for assembler processing.  See the
#                asminput.MacroSource.getLine() method
# Methods used by the macro itself during invocation
#   mhelp_init() Updates current MHELP values from the assembler
#   mhelp_XX()   Performs MHELP processing for the macro engine.
#   replace()    Returns a model statement with replaced symbol values. Used by Model
#                macro operation.
# Macro's have access to the assembler symbol table.  These methods provide access
# to the assembler symbol via Pratt literal token objects that inherently do so
# when the external object is the assembler.Assembler object.  By duplicating the
# methods here, the same Pratt token objects function in either the assembler context
# or the macro invocation context.
#   _getSTE_REf  Returns the assembler entry object for a given label definition
class Invoker(object):

    # Built as system variable symbols are defined.  See MacroLanguage._initsys()
    gblc=[]  # This list controls which global variables are passed to a macro

    def __init__(self,mgr,debug=False):
        self.mgr=mgr            # Manager helps me to expand macro.
        self.asm=mgr.asm        # The assembler
        self.case=self.asm.case # Specifies case sensitivity is enabled when True
        self.pm=self.asm.PM     # The Parser manager object
        self.debug=debug        # If True, enables expander debug message.

        # Macro expansion state:
        self.gbls=self.mgr.gbls # Locate the global variable symbols

        # These attributes are set by invoke() method when preparing the macro for
        # entry.
        self.macro=None         # Macro object being expanded, if any.
        self.engine=None        # The macro engine being expanded
        self.state=None         # The macro engine state
        self.stmt=None          # assembler.Stmt object associated with expansion
        self.step=0             # Next step to perform in expansion.
        self.lcls=None          # Local variable symbols
        self.lineno=None        # Statement number of invoking statement
        self.name=None          # The macro name being invoked
        self.sysndx=""          # &SYSNDX string (from __init_lcls() method)

        # MHELP related attributes.  See mhelp_init() method
        self._mhelp_sup=128
        self._mhelp_01=0        # Trace macro entry
        self._mhelp_02=0        # Trace macro branches (AIF, AGO)
        self._mhelp_04=0        # Dump SET symbols before AIF
        self._mhelp_08=0        # Dump SET symbols on exit (MEND, MEXIT)
        self._mhelp_10=0        # Dump parameters in entry
        self._mhelp_20=0        # Ignore global symbols with _mhelp_10 & _mhelp_08
        self._mhelp_40=0        # Dump SETC hex with
        self._mhelp_prefix=""   # Prefix used for all MHELP output of this invocation

        # Swich to enable tracing of the macro invokation
        self.idebug=False       # This switch is driven by the invoked Macro object

    # Intialize the macro's local variable symbols
    def __init_lcls(self):
        l=Mac_Symbols(self.case,unique=True)

        # Make system global variables available to local macro.  Each of these are
        # read only.
        gbl=self.gbls
        for sys in Invoker.gblc:
            s=gbl._fetch(sys)
            l._put(sys,s)

        # Macro expansion UTC time: YYYY-MM-DD HH:MM:SS.mmmmmm
        time=datetime.datetime.now(datetime.timezone.utc)
        tim="%04d-%02d-%02d %02d:%02d:%02d.%06d" % (time.year,time.month,time.day,\
            time.hour,time.minute,time.second,time.microsecond)
        l._initc("&SYSCLOCK",tim)    # UTC date and time to microseconds
        l._initc("&SYSECT",self.asm._sysect(),ro=True)

        # Note: update &SYSLOC when full location counter support is available
        # For now the location counter and the section name are the same.
        l._initc("&SYSLOC",self.asm._sysect(),ro=True)

        l._initc("&SYSMAC",self.macro.name,ro=True)

        self.sysndx=self.mgr.getSysNdx()
        l._initc("&SYSNDX",self.sysndx,ro=True)
        l._inita("&SYSNEST",self.mgr.nesting()+1,ro=True)

        # Establish ASMA specific system variable symbols
        # These allow a macro to interrogate the current XMODE settings for
        # code generation.
        try:
            ccw=self.asm.OMF.getXMODE("CCW")
        except KeyError:
            ccw=""
        l._initc("&SYSCCW",ccw,ro=True)

        try:
            psw=self.asm.OMF.getXMODE("PSW")
        except KeyError:
            psw=""
        l._initc("&SYSPSW",psw,ro=True)

        return l

    # Performs MHELP variable symbol dump.
    # Method Arguments:
    #   plist    A list of the parameters being dumped
    #   n        The MHELP option performing the dump:
    def __mhelp_dump(self,plist,n):
        plist.sort()
        for sym in plist:
            symo=self.lcls._fetch(sym)
            if symo.gbl:
                gl="GBL"
            else:
                gl="LCL"

            value=symo.value

            typ=symo.__class__.__name__[0]
            h=""

            if typ=="C":
                val="'%s'" % value.string()
                if self._mhelp_40:
                    ebcdic=value.value()
                    if len(ebcdic)>0:
                        for ndx in range(len(ebcdic)):
                            c=ebcdic[ndx]
                            h="%s%02X" % (h,ord(c))
                        h=" X'%s'" % h
            elif typ=="P":
                val=value.display(string=True)
            else:
                val=value.string()
            print("%s %s%s %s %s%s" % (self.__mhelp_prefix(n),gl,typ,sym,val,h))

    # Helper method returning the standard MHELP prefix
    # Method Arguments:
    #   n    The two digit MHELP action number being generated
    def __mhelp_prefix(self,n):
        name=self.name
        if len(name)<8:
            name="%s        " % name
            name=name[:8]
        return "MHELP %2d - %s %s" % (n,name,self.sysndx)

    # Helper method to dump unscripted SET symbols with optional globals suppressed
    # Method Argument:
    #   n   The two digit MHELP action number being generated
    def __mhelp_set_dump(self,n):
        syms=[]
        for sym,xsym in self.lcls._items():
            if isinstance(xsym,macsyms.Mac_Sym_Array):
                continue
            if xsym.parm or (xsym.gbl and self._mhelp_20):
                continue
            syms.append(sym)
        self.__mhelp_dump(syms,n)

    # Access the assembler Operation Manager for operation attribute
    # WARNING: Any changes to method arguments must be matched with the arguments of
    # the assembler.Assembler._getAttr_O() method.
    def _getAttr_O(self,oper):
        return self.asm._getAttr_O(oper)

    # Access the assembler symbol table (but don't create a listing cross-reference
    # entry).
    # WARNING: Any changes to method arguments must be matched with the arguments of
    # the assembler.Assembler._getSTE_Ref() method.
    def _getSTE_Ref(self,name,line):
        return self.asm._getSTE(name)

    # Enters the macro.
    def enter(self):
        # Remember where the macro was invoked
        self.macro.reference(self.lineno)   # Update the macro XREF entries
        self.mhelp_init()                   # Initialize MHELP values
        self.mhelp_01()                     # Trace macro entry if requested
        self.mhelp_10()                     # Dump parameters if requested
        self.state=self.engine.start(self)  # Start the macro engine

    # Creates a MacroError object from one supplied, adding macro specific
    # information to the error and reflecting the invoking statement as the error's
    # location.
    def error(self,op,msg,linepos=None):
        msg="MACRO ERROR in %s @%s: %s" % (self.macro.name,op.lineno,msg)
        # Create an AssemblerError for printing with the invoking statement in the
        # listing.
        stmt=self.stmt
        ae=assembler.AssemblerError(line=stmt.lineno,linepos=linepos,msg=msg)
        stmt.ae_error(ae)   # Make sure the error gets printed with the statement
        # This gets raised to terminate the macro processing.  It is ultimately
        # caught by the assembler input loop in Assembler.statement() method
        return MacroError(line=self.lineno,linepos=linepos,invoke=True,msg=msg)

    # Generate a new source statement line of text to be added to the assembly
    # Returns:
    #     a string (the generated model statement) or
    #     None to indicate the macro expansion has terminated.
    def generate(self):
        state=self.state
        while True:
            state=self.engine.run(state)
            if state.isDone():
                break
            # Macro is not done, so just return the model statement
            self.state=state       # Save the macro engine state for the next call

            if __debug__:
                if self.debug:
                    print("%s macro %s returning: %s" \
                        % (assembler.eloc(self,"generate",module=this_module),\
                            self.name,state.result))
            return state.result

        # Done, returning none
        self.engine=None
        self.state=None
        return None

    # Prepare to enter macro processing
    # This method is called by MacroLanguage.macstmt() method after the Invoker object
    # has been created.  Actual entry is via the entry() method called by the
    # asminput.MacroSource object during its init() method.
    def invoke(self,stmt):
        assert isinstance(stmt,asmstmts.MacroStmt),\
            "%s 'stmt' argument must be a asmstmts.MacroStmt object: %s" \
                % (assembler.eloc(self,"invoke",module=this_module),stmt)

        self.stmt=stmt
        macro=stmt.macro
        assert isinstance(macro,Macro),\
            "%s Stmt.macro attribute must be a Macro object: %s" \
                % (assembler.eloc(self,"macstmt",module=this_module),macro)

        self.macro=macro
        self.engine=macro.engine       # MacroEngine object of macro definition
        self.idebug=macro.idebug       # Pick up debug switch from macro definition

        # Parse statement macro parameters and create and update local symbols
        # based upon the macro prototype.
        self.lcls=self.__init_lcls()

        # This method may raise assembler.AssemblerError exceptions.  They will
        # be handled by the assembler during pre-processing.
        macro.parms(stmt,self.lcls,debug=stmt.trace)

        # Ready to do macro expansion now with the MacroEngine with my state
        self.lineno=stmt.lineno        # Statement number of invoking statement
        self.name=self.macro.name      # Macro being invoked
        # This Invoker object is now ready to enter the macro.
        # Entry occurs in the asminput.MacroSource object when its init() method
        # is called by the asminput.LineBuffer managing all source statement input.

    # Updates the current MHELP local values from the current global settings
    def mhelp_init(self):
        # Initialize local mhelp flags from the global macro language manager
        mhelp=self.mgr.mhelp_mask
        self._mhelp_sup=self.mgr.mhelp_sup
        self._mhelp_01=mhelp & 0x01   # Trace macro entry
        self._mhelp_02=mhelp & 0x02   # Trace macro branches (AIF, AGO)
        self._mhelp_04=mhelp & 0x04   # Dump SET symbols before AIF
        self._mhelp_08=mhelp & 0x08   # Dump SET symbols on exit (MEND, MEXIT)
        self._mhelp_10=mhelp & 0x10   # Dump parameters in entry
        self._mhelp_20=mhelp & 0x20   # Ignore global symbols with mhelp_04 & mhelp_08
        self._mhelp_40=mhelp & 0x40   # Dump SETC hex data with mhelp_10, mhelp_08 and
                                      # mhelp_04
        #print("%s _mhelp_sup: %s" \
        #    % (assembler.eloc(self,"mhelp_init",module=this_module),self._mhelp_sup))

    # Perform MHELP option 1 - Trace macro entry
    def mhelp_01(self):
        if self._mhelp_sup or not self._mhelp_01:
            return
        help="%s nest:%s" % (self.__mhelp_prefix(1),self.mgr.nesting())
        print(help)

    # Perform MHELP option 2 - Branch trace
    def mhelp_02(self,this,new):
        if self._mhelp_sup or not self._mhelp_02:
            return
        next=self.engine.op2stmt(new)
        trace="%s branch: %s -> %s" % (self.__mhelp_prefix(0x02),this,next)
        print(trace)

    # Perform MHELP option 4 - Dump SET symbols before AIF
    def mhelp_04(self):
        if self._mhelp_sup or not self._mhelp_04:
            return
        self.__mhelp_set_dump(0x04)

    # Perform MHELP option 8 - Dumpt SET symbols on exit (MEND, MEXIT)
    def mhelp_08(self):
        if self._mhelp_sup or not self._mhelp_08:
            return
        self.__mhelp_set_dump(0x08)

    # Perform MHELP option 16 - Macro entry parameter dump
    def mhelp_10(self):
        if self._mhelp_sup or not self.mhelp_10:
            return
        parms=[]
        for key,value in self.lcls._items():
            if value.parm:
                if isinstance(value,macsyms.Mac_Sym_Array):
                    # Only print parms that do not have sublists
                    # Fix later when sublists supported.
                    continue
                parms.append(key)
        self.__mhelp_dump(parms,0x10)


# This object interacts with the processor (statement or maclib) to facilitate
# macro definition.
#
# Instance Arguments:
#   asm        The global assembler.Assembler object
#   O_source   The O' attribute to be used for macros defined by this instance
#              of the object.  Two values are possible: 'S' for a macro from a
#              library or 'M' for an in-line macro definition
class MacroBuilder(object):
    def __init__(self,asm,O_source):
        self.asm=asm           # The assembler
        self.O_source=O_source # O' attribute for macros built by this instance

        # Macro processing state:
        #  0 ==> not processing a macro definition
        #  1 ==> macro started expecting prototype statement
        #  2 ==> prototype found, processing macro body statements
        #  3 ==> macro definition abandoned, flush till mend
        # This state is used to define actions in method defining()
        self.state=0        # Macro processing state.

        # This is the Macro object presently being defined.  Macro directives and
        # model directives are added to this object.
        self.indefn=None
        # Switch to debug a macro definition.
        self.ddebug=False   # Set by define() method from MACRO assembler directive.

    # Add a defined macro the the operation management framework
    # Change state if triggered by an MEND directive
    def addMacro(self,mac,mend=False):
        assert isinstance(mac,Macro),\
            "%s 'mac' argument must be a Macro object: %s" \
                % (assembler.eloc(self,"addMacro",module=this_module),mac)

        self.asm.OMF.def_macro(mac,O=self.O_source)    # Add the macro the OMF
        if mend:
            self.flush()

    # Initiate a new macro definition
    def define(self,debug=False):
        self.ddebug=debug    # Set the define debug switch from MACRO directive
        self.state=1         # We now expect a prototype statement

    # Hook used by the Assembler Language to process macro definition statements
    # Method Arguments:
    #   stmt   A ASMStmt object of the statement that may or may not be part of
    #          a macro definition.
    #   debug  Enable debugging messages (True).  Disable debugging messages (False).
    #          Defaults to False.
    # Returns:
    #   True if the ASMStmt object is part of a macro definition and nothing further
    #        needs to be done by the Assembler object for it.
    #   False if the ASMStmt object is not part of a macro definition and the
    #        Assembler object must process it in full.
    def defining(self,stmt,debug=False):
        ddebug=self.ddebug or debug #or True
        if __debug__:
            if ddebug:
                cls_str=assembler.eloc(self,"defining",module=this_module)
                print("%s macro state: %s" \
                    % (cls_str,self.state))
                print("%s stmt: %s" % (cls_str,stmt))

        state=self.state
        #print("[%s] defining: %s  stmt: %s %r" % (stmt.lineno,state,stmt.instu,stmt))
        # If not defining a macro, simply return with a value of False.
        if state==0:
            return False

        # Looking for prototype statmenet
        if state==1:
            #if flds.comment or flds.empty or isinstance(stmt,asmstmts.StmtComment):
            if isinstance(stmt,asmstmts.StmtComment):
                self.state=3
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="comment or empty line not allowed for prototype statement")

            op=stmt.optn.oper

            if __debug__:
                if ddebug:
                    print("%s state -> %s operation: '%s'" % (cls_str,state,op))

            # prototype statement may not contain a macro directive
            if op=="MEND":
                self.state=0         # Leave macro definition mode
                raise assembler.AssemblerError(line=stmt.lineno,linepos=flds.oppos,\
                    msg="empty macro definition ignored")
            if stmt.asmdir or stmt.macdir:
                self.state=3
                raise assembler.AssemblerError(line=stmt.lineno,linepos=flds.oppos,\
                    msg="macro definition suppressed - expected macro prototype "
                        "statement but found: %s" % op)

            # Prototype statement found
            try:
                # Debugging of prototype statements requires use of the MACRO
                # DEBUG operand.  Neither --oper nor ATRACEON works for the
                # prototype statement
                stmt.Pass0(self.asm,macro=self,debug=ddebug)
            except assembler.AssemblerError as ae:
                self.state=3         # Ignore rest of macro definition
                raise ae from None
            self.state=2

        # Processing body statements (macro diretives and model statements)
        elif state==2:
            op=stmt.optn.oper
            try:
                # Debuggging of macro directives may be controlled either by
                # --oper or ATRACEON.  Model statements may only be debugged
                # using MACRO with the DEBUG operand
                stmt.Pass0(self.asm,macro=self,debug=ddebug)
            except assembler.AssemblerError as ae:
                if op=="MEND":
                    self.state=0  # Macro definition ended due to an error
                else:
                    self.state=3  # Flush until we find the MEND
                raise ae from None
            # Remain in state 2 as long as no errors found in body

        # Bad macro is being suppressed
        elif state==3:
            if isinstance(stmt,asmstmts.StmtComment):
                if __debug__:
                    if ddebug:
                        print("%s state -> %s comment" % (cls_str,state))

            else:
                op=stmt.optn.oper
                if __debug__:
                    if ddebug:
                        print("%s state -> %s operation: '%s'" % (cls_str,state,op))

                if op=="MEND":
                    # Got to the end of bad macro, leaving macro definition mode
                    self.state=0
                    if self.indefn is not None:
                        ae_msg="%s macro definition failed" % self.indefn.name
                    else:
                        ae_msg="macro definition failed"
                    self.indefn=None  # Obliterate failed macro
                    self.ddebug=False # Turn off definition debug switch
                    raise assembler.AssemblerError(line=stmt.lineno,msg=ae_msg)

        # Do not recognize state, so something is messed up, bailing....
        else:
            raise ValueError("%s MacroBuilder.state invalid: %s" \
                % (assembler.eloc(self,"defining",module=this_module),state))

        # Tell caller we processed the statement here.
        return True

    # Flush the current definition being built
    def flush(self):
        self.indefn=None             # Leaving macro definition mode
        self.ddebug=False            # Turn off definition debug switch
        self.state=0                 # Change state to relfect this


class MacroLanguage(object):
    def __init__(self,asm):
        self.asm=asm           # The assembler
        self.case=asm.case     # Inherits the case sensitivity option
        self.parsers=asm.PM    # parsers.ParserMgr object
        # Make the parser manager available to macro symbol value objects,
        # subclasses of macsyms.Mac_Val.
        macsyms.pm=self.parsers

        # Macro processing state:
        #  0 ==> not processing macro definitions
        #  1 ==> macro started expecting prototype statement
        #  2 ==> prototype found, processing macro body statements
        #  3 ==> macro definition abandoned, flush till mend
        # This state is used to define actions in method defining()
        self.state=0        # Macro processing state.

        # This is the Macro object presently being defined.  Macro directives and
        # model directives are added to this object.
        self.indefn=None
        # Switch to debug a macro definition.
        self.ddebug=False   # Set by define() method from MACRO assembler directive.

        # Managed by getSysNdx() method
        self.sysndx=0       # The global sysndx upon which each local is derived

        # MHELP action mask. See the mhelp() method
        # Mask or Value       Action taken
        # 0x80     128     Suppress MHELP actions
        # 0x40      64     SETC dumps EBCDIC hex
        # 0x20      32     Ignores global variables in option 16 and 8
        # 0x10      16     Dumps parameter values immediately on macro entry
        # 0x08       8     Dumps undimensioned SET symbols with MEND and MEXIT
        # 0x04       4     Dumps undimensioned SET symbols before AIF executed
        # 0x02       2     Trace AGO and AIF statements
        # 0s01       1     Provides MACRO name, nesting depth and &SYSNDX on entry
        self.mhelp_mask=0     # MHELP trace/dump mask
        self.mhelp_sup=0x80   # MHELP actions suppressed
        # Note: mhelp output is created by the Invoker object.

        # MHELP maximum &SYSNDX value.  See the mhelp() method
        self.max_sysmon=0   # If not zero, &SYSNDX value is being monitored
        self.max_sysndx=0   # Maximum &SYSNDX value allowed
        self.max_hit=False  # Set to True if the maximum hit

        # Managed by nest() and unnest() methods
        self._nest=0        # Current macro nesting level
        self.expanders=[]   # List of active expanders

        # Global variable symbol dictionaries: '&symbol' -> [A|B|C]Sym object
        self.gbls=self.__init_globals()       # Initalize Global variable symbols

    # Returns the GlobalSymbols object with system variables initialized
    def __init_globals(self):
        g=Mac_Symbols(self.case,unique=False,gbl=True)
        now=self.asm.now         # This is an instance of time.struct_time

        self._initsys("&SYSASM","A SMALL MAINFRAME ASSEMBLER",gbls=g)

        # now is a struct_time object
        year="%04d" % now.tm_year
        month="%02d" % now.tm_mon
        day="%02d" % now.tm_mday
        datc="%s%s%s" % (year,month,day)

        # Assembly date: YYYYMMDD
        self._initsys("&SYSDATC",datc,gbls=g)


        # Assembly date: MM/DD/YY
        date="%s/%s/%s" % (month,day,year[2:4])
        self._initsys("&SYSDATE",date,gbls=g)

        # A single quote
        self._initsys("&SYSQ","'",gbls=g)

        # Assembly time: HH.MM
        hour="%02d" % now.tm_hour
        minute="%02d" % now.tm_min
        time="%s.%s" % (hour,minute)
        self._initsys("&SYSTIME",time,gbls=g)

        # Assembler version: version.release.modification
        ver="%s.%s.%s" % self.asm.version
        self._initsys("&SYSVER",ver,gbls=g)

        return g

    def __set_name(self,stmt,setx,debug=False):
        fields=stmt.fields
        if not fields.symbol:
            raise assembler.AssemblerError(line=stmt.lineno,linepos=1,\
                msg="%s macro directive symbolic variable name unrecognized: %s" \
                    % (setx,fields.name))

        return fields.symid

    # Extract the sequence from the name field, if any, from the macro fields
    def __seq(self,fields,debug=False):
        if fields.sequence:
            if not self.case:
                return fields.name.upper()
            else:
                return fields.name
        return None

  #
  # EXTERNAL GBLC INITIALIZATION
  #

    # Establish a global SETC symbol from sources external to the assembly, for
    # example, the command line.
    # Method Arguments:
    #   symbol   The name of the GBLC symbolic variable being created
    #   value    The value to which the SETC symbol is to be set or None
    # Exceptions:
    #   MacroError if the symbol being defined is already defined as read-only.
    #            &SYSxxxx symbolic variables can be read-only.
    def _init_gblc(self,symbol,value):
        # Establish global SETC symbol from the assembler's external drive
        assert isinstance(symbol,str) and len(symbol)>1,\
            "%s 'symbol' argument must be a non-empty string: %s" \
                % (assembler.eloc(self,"_init_gblc",module=this_module),symbol)
        assert isinstance(value,str) or value is None,\
            "%s 'value' argument must be a string: %s" \
                % (assembler.eloc(self,"_init_gblc",module=this_module),value)

        if symbol[0]!="&":
            name="&%s" % symbol
        else:
            name=symbol
        if not self.case:
            sid=macsyms.SymbolID(name.upper())
        else:
            sid=macsyms.SymbolID(name)
        s=self.gbls.defc(sid)
        if value is not None:
            s.setValue(sid,macsyms.C_Val(value),user=True)

    # Initialize initial file related system variable symbols
    def _init_gblc_file(self,filepath):
        directory, filename=os.path.split(filepath)
      # "/dir/dir","filename.ext"

        name,      ext     =os.path.splitext(filename)
      # "filename",".ext" or
      # "filename",""
        if len(ext)!=0:
            ext=ext[1:]  # Drop the separating period

        # Define the respective system variables
        self._initsys("&SYSPATH", filepath)
        self._initsys("&SYSDIR",  directory)
        self._initsys("&SYSFNAME",filename)
        self._initsys("&SYSFNAM", name)
        self._initsys("&SYSFEXT", ext)

    # This initializes system variable symbols and interfaces with the Invoker
    # class to ensure they are presented to each macro when invoked.
    def _initsys(self,symbol,value,gbls=None):
        if gbls:
            g=gbls
        else:
            g=self.gbls
        g._initc(symbol,value,ro=True)
        if symbol not in Invoker.gblc:
            Invoker.gblc.append(symbol)

  #
  # MACRO INVOCATION PROCESSING
  #

    # Returnt the current expander
    def currentInvoker(self):
        return self.expanders[-1]

    # Returns the incremented value of &SYSNDX as a character string
    def getSysNdx(self):
        self.sysndx+=1
        sysndx=self.sysndx
        if self.sysndx<10000:
            sysndx="%04d" % sysndx
        else:
            sysndx="%s" % sysndx
        return sysndx

    # Start the invocation of a macro. Process a Stmt object that is a macro statement.  This method kicks off
    # a macro expansion.
    # Returns:
    #   the Invoker object for the statement
    #   None if MHELP &SYSNDX value has been reached
    # Excpetions:
    #   assembler.AssemblerError when MHELP &SYSNDX is reached.  Following this
    #   exception, only None will be returned.
    def macstmt(self,stmt,debug=False):
        assert isinstance(stmt,asmstmts.MacroStmt),\
            "%s 'stmt' argument must be a asmstmts.MacroStmt object: %s" \
                % (assembler.eloc(self,"macstmt",module=this_module),stmt)

        macro=stmt.macro
        assert isinstance(macro,Macro),\
            "%s 'stmt.macro' must be a Macro object: %s" \
                % (assembler.eloc(self,"macstmt",module=this_module),macro)

        # Before launching the macro's invocation determine if MHELP maximum &SYSNDX
        # value exceeded if it is set.  Once the maximum &SYSNDX is triggered,
        # following macros are ignored.
        if self.max_hit:
            return None
        if self.max_sysmon and (self.sysndx>=self.max_sysndx):
            if not self.max_hit:
                self.max_hit=True
                raise assembler.AssemblerError(line=stmt.lineno,
                    msg="MHELP maximum &SYSNDX value (%s) may not be exceeded" \
                        % self.max_sysndx)
            return None
        # Note: &SYSNDX is incremented when the new Invoker object is created in the
        # following statement.

        exp=Invoker(self,debug=debug)
        # Pass the invoking Stmt object and the operands to the expander
        try:
            exp.invoke(stmt)        # Initialize the macro expander
        except macsyms.SymbolError as se:
            raise assembler.AsemblerError(source=stmt.source,line=stmt.lineno,\
                msg=se.msg) from None
        return exp

    # Updates the MHELP values.  Called by assembler.Assembler._spp_mhelp() method
    def mhelp(self,value,debug=False):
        val=value & 0xFFFFFFFF
        self.max_sysndx=val & 0xFFFFFF00   # maximum &SYSNDX value being detected
        self.max_sysmon=val & 0x0000FF00   # &SYSNDX value being monitored
        self.mhelp_mask=val & 0x000000FF   # MHELP action mask
        self.mhelp_sup =val & 0x00000080   # If bit set, suppressing actions
        if self.mhelp_sup == 0 and self.mhelp_mask == 0:
            self.mhelp_sup =  0x00000080
        if debug:
            cls_str=assembler.eloc(self,"mhelp",module=this_module)
            print("%s max_sysndx=%s" % (cls_str,self.max_sysndx))
            print("%s max_sysmon=%s" % (cls_str,self.max_sysmon))
            print("%s mhelp_mask=%s" % (cls_str,bin(self.mhelp_mask)))
            print("%s mhelp_sup =%s" % (cls_str,self.mhelp_sup))

    # Incrments and returns the new nesting level
    # The open code macro statements have a depth of 1.  Inner macro statements have
    # a nesting depth of 2 or more.
    def nest(self,exp):
        if not isinstance(exp,Invoker):
            raise ValueError("%s 'exp' argument must be an Invoker object: %s" \
                % (assembler.eloc(self,"nest",module=this_module),exp))
        self.expanders.append(exp)
        self._nest=len(self.expanders)
        self.cur_exp=self.expanders[-1]
        return self._nest

    # Current nesting level
    def nesting(self):
        return self._nest

    # Decrements the nesting level
    def unnest(self):
        if len(self.expanders)==0:
            raise ValueError("%s can not unnest expander, nesting level empty" \
                % assembler.eloc(self,"unnest",module=this_module))
        del self.expanders[-1]
        self._nest=len(self.expanders)
        if self._nest==0:
            self.cur_exp=None


#
#  +------------------------+
#  |                        |
#  |   Macro Symbol Table   |
#  |                        |
#  +------------------------+
#

# Class for managing symbols.
# Instance arguments:
#   unique    Specify True if all variables must be unique when defined.
#             Specify False if previously defined variables are allowed.
#             Default is False.
#             Note: Global variables are not required to be unique when defined.
#                   Local variables and macro context variables must be unique
#                   Unique=True may be forced by the defa(), defb() or defc() methods.
#   gbl       Specifies a symbol's global attribute of True or False
#   case      Enables case sensitivity for macro symbols if True.  Defaults to False
# Note: This class is heavily dependent upon module macsyms.
class Mac_Symbols(object):
    def __init__(self,case,unique=False,gbl=False):
        self.syms={}        # Dictionary of variable symbols
        self.unique=unique  # Only new unique symbols may be defined
        self.gbl=gbl        # Sets a symbol's gbl attribute
        self.case=case      # Enables case sensitivity for macro symbols

    # Defines a symbol variable
    # Method Arguments:
    #   symbol    A SymbolID object defining the variable and its subscripts
    #   cls       The class object of the variable type: A_Sym, B_Sym or C_Sym
    #   unique    Specify True if the symbol may not already be defined
    # Returns:
    #   the created, or previously created if unique=False, A_Sym, B_Sym or C_Sym object
    # Exceptions:
    #   MacroError  variable symbol already created if unqiue is being enforced.
    def __define(self,symbol,cls,parm=False,unique=False,ro=False):
        assert isinstance(symbol,macsyms.SymbolID),\
            "%s 'symbol' argument must be a macsyms.SymbolID object: %s" \
                % (assembler.eloc(self,"__define",module=this_module),symbol)
        assert self.case or symbol.var == symbol.var.upper(),\
             "SymbolID not case insensitive: %s" % symbol

        name=symbol.var
        try:
            s=self.syms[name]
            if self.unique or unique:
                raise MacroError(msg="symbol already defined: '%s'" % name)
        except KeyError:
            s=cls.Create(symbol)
            s.gbl=self.gbl     # Set symbol's gbl attribute
            s.parm=parm        # Identify if symbol is a macro parameter
            s.ro=ro            # Set the symbol's read-only status
            self.syms[name]=s
        return s

    def _add(self,sym,n=None,pos=None,unique=False):
        assert isinstance(sym,macsyms.Mac_Sym),\
            "%s 'sym' argument must be a Mac_Sym object: %s" \
                % (assembler.eloc(self,"_add",module=this_module),sym)
        assert self.case or sym.symbol == sym.symbol.upper(),\
            "SymbolID not case insensitive: %s" % sym

        name=sym.symbol
        try:
            self._fetch(name)
            if self.unqiue or unique:
                raise MacroError(msg="symbol already defined: '%s'" % name)
        except KeyError:
            pass
        self._put(name,sym)

    # This is a low-level function for direct access to the xSym object
    # Method Arguments:
    #   sym      Symbolic variable name (with '&')
    # Exceptions:
    #   KeyError if symbol variable not defined
    def _fetch(self,sym):
        return self.syms[sym]

    # These three methods create and initialize a variable symbol.
    #   _inita    establishes an arithmetic variable
    #   _initb    establishes a binary variable
    #   _initc    establishes a character variable
    # Method Arguments:
    #   symbol   System variable symbol name as a string with initial '&'
    #   value    Arithmetic value being assigned the system variable symbol
    #   parm     If True, the symbol is a macro parameter.  Default is False.
    #   ro       If True, the symbol will be flagged as read-only.  Default is False
    #   unique   If True, forces the symbol to be unique even if the table does not.
    def _inita(self,symbol,value,parm=False,ro=False,unique=False):
        if not self.case:
            i=macsyms.SymbolID(symbol.upper())
        else:
            i=macsyms.SymbolID(symbol)
        s=self.defa(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,macsyms.A_Val(value),user=False)

    def _initb(self,symbol,value,parm=False,ro=False,unique=False):
        if not self.case:
            i=macsyms.SymbolID(symbol.upper())
        else:
            i=macsyms.SymbolID(symbol)
        s=self.defb(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,macsyms.B_Val(value),user=False)

    def _initc(self,symbol,value,parm=False,ro=False,unique=False):
        if not self.case:
            i=macsyms.SymbolID(symbol.upper())
        else:
            i=macsyms.SymbolID(symbol)
        s=self.defc(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,macsyms.C_Val(value),user=False)

    # Returns the items() iterator for the symbol dictionary
    def _items(self):
        return self.syms.items()

    # This is a low-level function for direct setting of a symbol's xSym object
    def _put(self,name,sym):
        self.syms[name]=sym

    # References a symbolic variable value defined by a SymbolID object
    # Method Arguments:
    #   symbol    the SymbolID object identifying the referenced variable and subscript
    #   updating  If True, the symbol is being referenced for an update (SETx)
    # Returns:
    #   the referenced SymbolValue object: A_Val, B_Val or C_Val object
    # Exceptions:
    #   MacroError when variable symbol is undefined,
    #              when a subscript is provided for an unsubscripted symbol,
    #              when the subscript is out of range, or
    #              when macro parameter sublists nesting depth is exceeded.
    # Note: The macsyms module may generate a macsyms.SymbolError, but it is
    # converted to a MacroError by this method.
    def _reference(self,symbol,updating=False):
        # This raises an uncaught MacroError if the symbol is not defined
        sym=self._reference_symbol(symbol,updating=updating)
        #print("%s sym found: %s" \
        #    % (assembler.eloc(self,"_reference",module=this_module),sym))

        try:
            return sym.getValue(symbol)
        except macsyms.SymbolError as se:
            # Add symbol name to message and re-raise it as a macro error
            raise MacroError(invoke=True,msg="symbol '%s' - %s" \
                % (sym.symbol,se.msg)) from None

    # References a symbolic variable MacroSymbol whose reference is defined by a
    # SymbolID object's symbolic variable name.
    # Method Arguments:
    #   symbol    the SymbolID object identifying the referenced variable and subscript
    #   updating  If True, the symbol is being referenced for an update (SETx)
    #   implicit  Specify the bound method that defines the undefined symbol when
    #             the reference if for implicit definition.   Otherwise specify None
    #             to inhibit implicit definition.  Default is None
    # Returns:
    #   the referenced MacroSymbol object, Mac_Sym, Parm_Sym, or Array_Sym
    # Exceptions:
    #   MacroError if variable symbol is undefined, if subscript provided for
    #   unsubscripted symbol, if subscript is out of range or if subscript symbol
    #   itself is undefined.
    def _reference_symbol(self,symbol,updating=False,implicit=None):
        assert isinstance(symbol,macsyms.SymbolID),\
            "%s 'symbol' argument must be a macsyms.SymbolID object: %s" \
                % (assembler.eloc(self,"_reference_symbol",module=this_module),\
                    symbol)
        assert self.case or symbol.var == symbol.var.upper(),\
            "symbol not case insensitive: %s" % symbol

        try:
            mac_sym=self.syms[symbol.var]   # Locate its MacroSymbol object
        except KeyError:
            if implicit is None:
                raise MacroError(invoke=True,msg="undefined symbol: '%s'" \
                    % symbol.var) from None
            # Implicit definition requested
            mac_sym=implicit(symbol)   # Create the required Mac_Sym subclass

        # Check for read-only symbol if it is being referenced for an update by SETx
        if updating and mac_sym.ro:
            raise MacroError(invoke=True,\
                msg="symbol '%s' read-only, can not SET" % sym.symbol)

        return mac_sym


    # References a symbolic variable MacroSymbol whose reference is defined by a
    # SymbolID object's symbolic variable name for the purposes of providing
    # the symbol's T' attribute.
    # Method Arguments:
    #   symbol    the SymbolID object identifying the referenced variable and
    #             subscript
    # Returns:
    #   the referenced SymbolValue object, A_Val, B_Val or C_Val object if defined
    #   None if the symbol is not defined.
    # Exceptions:
    #   MacroError if subscript provided for unsubscripted symbol, if subscript is
    #   out of range.
    def _reference_T(self,symbol):
        assert isinstance(symbol,macsyms.SymbolID),\
            "%s 'symbol' argument must be a macsyms.SymbolID object: %s" \
                % (assembler.eloc(self,"_reference_symbol",module=this_module),\
                    symbol)
        assert self.case or symbol.var == symbol.var.upper(),\
            "symbol not case insensitive: %s" % symbol

        try:
            mac_sym=self.syms[symbol.var]   # Locate its MacroSymbol object
        except KeyError:
             # We return None so that the T' attribute 'U' can be returned rather
             # than generating an error via an exception.
            return None

        try:
            return mac_sym.getValue(symbol)
        except macsyms.SymbolError as se:
            # Add symbol name to message and re-raise it as a macro error
            raise MacroError(invoke=True,msg="symbol '%s' - %s" \
                % (sym.symbol,se.msg)) from None

    # These three methods define a variable symbol from a Symbol ID object
    #   defa   Defines an arithmetic symbol
    #   defb   Defines a binary symbol
    #   defc   Defines a character symbol
    # Method Arguments:
    #   symbol   SymbolID object identifying the symbol's name and subscripting
    #   parm     If True, indicates the symbol is a macro parameter.  Default is False.
    #   unique   If True, forces the symbol to be unique within the table even if
    #            the table does not require it.  Default is False.
    #   ro       If True, the symbol is read-only.  Default is False.  If read-only'
    #            the setx argument user=False must be specified to set its value.
    # Returns:
    #   the A_Sym, B_Sym or C_Sym object of the defined symbol.
    # Exceptions:
    #   MacroError if unique=True and symbol is already defined
    def defa(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,macsyms.A_Sym,parm=parm,unique=unique,ro=ro)

    def defb(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,macsyms.B_Sym,parm=parm,unique=unique,ro=ro)

    def defc(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,macsyms.C_Sym,parm=parm,unique=unique,ro=ro)

    def defp(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,macsyms.Parm_Sym,parm=True,unique=True,ro=True)

    # Return the value of a symbol from a symbol ID's value
    #   geta   Returns an arithmetic symbol's A_Val object
    #   getb   Returns a binary symbol's B_Val object
    #   getc   Returns a character symbol's C_Val object
    #   getx   Returns the symbol's A_Sym, B_Sym or C_Sym object
    # Method Argument:
    #   symbol A SymbolID object identifying the symbol's name and subscripting
    # Returns:
    #   an A_Val, B_Val or C_Val object
    # Excpetions: the caller needs to catch and handle appropriately
    #   MacroError if the variable is not defined, subscript our of range or
    #              the symbol is not of the requested type.
    def geta(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,macsyms.A_Val):
            raise MacroError(invokde=True,\
                msg="variable symbol '%s' not LCLA or GBLA" % symbol.var)
        return v

    def getb(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,macsyms.B_Val):
            raise MacroError(invoke=True,\
                msg="variable symbol '%s' not LCLB or GBLB" % symbol.var)
        return v

    def getc(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,macsyms.C_Val):
            raise MacroError(invoke=True,\
                msg="variable symbol '%s' not LCLC or GBLC" % symbol.var)
        return v

    def getx(self,symbol):
        return self._reference(symbol)   # May raise a MacroError exception

    # These three methods set a sybmol's value based upon a symbol ID object.  The
    # methods are used solely for implementation of the SETA, SETB and SETC macro
    # directives.
    #   seta       Sets an arithmetic symbol's value to a Python integer.
    #   setb       Sets a binary symbol's value to a Python integer of value 0 or 1.
    #   setc       Sets a character symbol's value to a Python string.
    # Method Arguments:
    #   symbol     A SymbolID whose value is being set
    #   value      A Python integer, or string
    #   user       If True, recognize read-only status.  Default is True.  Specify
    #              False to set the value regardless of the read-only status.
    # Returns: None
    # Excpetions: the caller needs to catch and handle appropriately
    #   KeyError   if the variable symbol is not defined
    #   IndexError if the variable subscript is out of range
    #   MacroError if the variable is not defined as GBLA or LCLA
    #   ValueError if the value is not valid for the type.
    def seta(self,symbol,value,user=True):
        assert isinstance(value,macsyms.A_Val),\
            "%s 'value' argument must be a macsyms.A_Val object: %s" \
                % (assembler.eloc(self,"setb",module=this_module),value)

        s=self._reference_symbol(symbol,updating=True,implicit=self.defa)
        if not isinstance(s,macsyms.A_Sym):
            raise MacroError(invoke=True,msg="SETA can not set a SET%s symbol: %s" \
                % (s.__class__.__name__[0],s.symbol))
        s.setValue(symbol,value,user=True)

    # Set a LCLB or GBLB variable.  Value must be a macsyms.B_Val object
    def setb(self,symbol,value,user=True):
        assert isinstance(value,macsyms.B_Val),\
            "%s 'value' argument must be a macsyms.B_Val or macsyms.A_Val "\
                "object: %s" % (assembler.eloc(self,"setb",module=this_module),value)

        s=self._reference_symbol(symbol,updating=True,implicit=self.defb)
        if not isinstance(s,macsyms.B_Sym):
            raise MacroError(invoke=True,msg="SETB can not set SET%s symbol: %s" \
                % (s.__class__.__name__[0],s.symbol))
        s.setValue(symbol,value,user=True)

    # Set a LCLC or GBLC variable.  Value must be a macsyms.C_Val object
    def setc(self,symbol,value,user=True):
        assert isinstance(value,macsyms.C_Val),\
            "%s 'value' argument must be a macsyms.C_Val object or string: %s" \
                % (assembler.eloc(self,"setc",module=this_module),value)

        s=self._reference_symbol(symbol,updating=True,implicit=self.defc)
        if not isinstance(s,macsyms.C_Sym):
            raise MacroError(invoke=True,msg="SETC can not set a SET%s symbol: %s" \
                % (s.__class__.__name__[0],s.symbol))
        s.setValue(symbol,value,user=True)


if __name__ == "__main__":
    raise NotImplementedError("asmmacs.py - intended for import use only")
