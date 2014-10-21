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
# approach in the new pratt2.py module.  The real requirements for expression
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

# Python imports:
import datetime               # Access UTC time
import re                     # Access regular expressions

# SATK imports:
from satkutil import method_name       # Access the method names in method objects
import pratt2                 # Access a number of expression evalutor objects

# ASMA imports:
import asmcards               # Access the continuation support
import asminput               # Access the input manager for macro expansions
import asmfsmbp               # Access the finite-state machine parsers
import assembler              # Access the assembler for AsmPasses generation

this_module="asmmacs.py"

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
# macro.  assembler.AssemblerError is raised during user errors during macro
# definition.
#
# Instance Arguments:  All are optional and default to None if not supplied
#   line    The assembler statement generating the error report
#   source  The Source object identifying the macro statement detecting the error
#   linepos The location within the detecting statement of the error
#   msg     The nature of the error.
# Note: This object expects to be created by Invoker.error() method.
class MacroError(Exception):
    def __init__(self,line=None,source=None,linepos=None,msg=""):
        # These attributes identify the location of macro directive detecting the error
        self.linepos=linepos     # Position in the defining statement of the error
        self.source=source       # Source of error detecting statement
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
    Arith=asmfsmbp.ArithEval()   # Arithmetic Evaluator
    Binary=asmfsmbp.BinaryEval() # Binary Evaluator
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
        
        # Debug switch
        self.idebug=False          # If True trace macro invocation

    # This method initializes the prototype parameter values when the macro is
    # invoked.  Only unique SETC local symbols are created.  The local symbolic
    # variable may be unsubscripted or subscripted depending upon whether the 
    # parameter defined a single value or multiple in a list.
    def __initparm(self,symbol,value,lcls):
        # Enforce symbol case sensitivity rule.
        if not self.case:
            symname=symbol.upper()
        else:
            symname=symbol

        if isinstance(value,str):
            # Create an unsubscripted symbolic variable to hold the parameter string
            symid=SymbolID(symname)
            symo=lcls.defc(symid,parm=True,unique=True,ro=True)
            # At this point the unsubscripted symbol has been added to the macro
            # dictionary.
            # Update it with the string assigned to the parameter.
            symo.setValue(symid,CVal(value),user=False)
            return

        assert isinstance(value,list),\
            "%s 'value' argument must be a list or a string: %s" \
                % (assembler.eloc(self,"__initc",module=this_module),value)

        # Create a subscripted symbolic variable to hold the parameter list
        number=len(value)   
        symid=SymbolID(symname,number)
        symo=lcls.defc(symid,parm=True,unique=True,ro=True)
        # At this point the symbol has been added to the symbol table with default
        # values assigned to each subscript.
        for n in range(number):
            sub=n+1     # subscripts use 1 as the index origin, not 0 like Python
            val=value[n]
            symid=SymbolID(symname,sub)
            symo.setValue(symid,CVal(val),user=False)

   #
   # These methods build macro operations from macro directives
   #
   
    # Add a simple AGO operation
    def _ago(self,lineno,dest,seq=None):
        self.engine.define(AGO(lineno,dest),seq=seq)
   
    # Add a computed AGO operation
    def _agoc(self,lineno,dest,expr,seq=None):
        self.engine.define(AGOC(lineno,dest,expr),seq=seq)
   
    # Add an AIF operation
    def _aif(self,lineno,dest,expr,seq=None):
        self.engine.define(AIF(lineno,dest,expr),seq=seq)
   
    # Add an ANOP operation
    def _anop(self,lineno,seq=None):
        self.engine.define(ANOP(lineno),seq=seq)
   
    # Add a GBLA operation
    def _gbla(self,lineno,symid,seq=None):
        self.engine.define(GBLA(lineno,symid),seq=seq)
   
    # Add a GBLB operation
    def _gblb(self,lineno,symid,seq=None):
        self.engine.define(GBLB(lineno,symid),seq=seq)
        
    # Add a GBLC operation
    def _gblc(self,lineno,symid,seq=None):
        self.engine.define(GBLC(lineno,symid),seq=seq)
   
    # Add a LCLA operation
    def _lcla(self,lineno,symid,seq=None):
        self.engine.define(LCLA(lineno,symid),seq=seq)
        
    # Add a LCLA operation
    def _lclb(self,lineno,symid,seq=None):
        self.engine.define(LCLB(lineno,symid),seq=seq)
   
    # Add a LCLA operation
    def _lclc(self,lineno,symid,seq=None):
        self.engine.define(LCLC(lineno,symid),seq=seq)
   
    # Add a MEND operation
    def _mend(self,lineno,seq=None):
        self.engine.define(MEND(lineno),seq=seq)
   
    # Add a MEXIT operation
    def _mexit(self,lineno,seq=None,source=None):
        self.engine.define(MEXIT(lineno),seq=seq)
   
    # Add a model statement to the macro
    def _model(self,lineno,mdlstmt,seq=None,debug=False):
        if debug:
            cls_str=assembler.eloc(self,"_model",module=this_module)
            print("%s [%s] '%s'" % (cls_str,lineno,mdlstmt))
        self.engine.define(Model(lineno,mdlstmt),seq=seq)
   
    # Add a SETA operation
    def _seta(self,lineno,symid,expr,debug=False):
        self.engine.define(SETA(lineno,symid,expr),seq=None)

    # Add a SETB operaion
    def _setb(self,lineno,symid,expr,debug=False):
        self.engine.define(SETB(lineno,symid,expr),seq=None)

    # Add a SETC operation
    def _setc(self,lineno,symid,charstr,start_expr,len_expr):
        self.engine.define(SETC(lineno,symid,charstr,start_expr,len_expr),seq=None)

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
    #   parsers  The asmfsmbp.Parsers object
    # Return: None
    # Exceptions:
    #   AssemblerError if parameters not parsable or duplicae keyword parameter found
    def parms(self,stmt,lcls,parsers,debug=False):
        pdebug=debug
        proto=self.prototype

        if __debug__:
            if debug:
                print("%s proto: %s" \
                    % (assembler.eloc(self,"parms",module=this_module),proto))

        # Define the prototype name field parameter if defined and specified
        lblsym=proto.lblsym
        if lblsym is not None:
            if stmt.label:
                lcls._initc(lblsym,stmt.label,parm=True,ro=True)
            else:
                lcls._initc(lblsym,"",parm=True,ro=True)

        # Treat anything in the macro statement after operation field as comments
        # because the prototype does not define any parameters
        if proto.noparms:
            return

        # Parse the parameters in the macro invocation statement if provided
        operands=stmt.fields.operands
        if operands is not None:
            # Parse the operand field of the statement
            # An assembler.AssemblerError exception may be raised here
            if pdebug:
                print('parsing macro parameters: "%s"' % operands)
            scope=parsers.parse_operands(stmt,"parms")
            key_parms=scope.key_parms
            pos=scope.pos_parms
        else:
            # Otherwise, we present an empty list and dictionary for no parms.
            key_parms={}
            pos=[]

        # Define all of the keyword symbols as specified or with prototype defaults
        for key,value in proto.keywords.items():
            try:
                key_parm=key_parms[key]
            except KeyError:
                # parameter not specified so set its default now
                key_parm=value
            # Define the keyword in the macro dictionary
            self.__initparm(key,key_parm,lcls)

        # Define the positional parameters with specified or implied empty string
        proto_pos=proto.pos
        posn=len(pos)       # Number of positional parameters
        for ndx in range(len(proto_pos)):
            possym=proto_pos[ndx]
            if ndx<posn:
                val=pos[ndx]
            else:
                val=""
            self.__initparm(possym,val,lcls)

    # This method returns the assembler.asmpasses object for this macro
    # when encountered in a source statement.  All subclasses must provide this method.
    def passes(self,asm):
        po=assembler.AsmPasses(self.name,spp=asm._spp_invoke,parser=None,\
            optional=True,directive=True)
        return po

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
    def define(self,op,seq=None):
        assert isinstance(op,MacroOp),\
            "%s 'op' argument must be a MacroOp object: %s" \
                % (assembler.eloc(self,"define",module=this_module),op)
        assert not self.done,\
            "%s can not add MacroOp, Mend encountered: %s" \
                % (assembler.eloc(self,"define",module=this_module),\
                    op.__class__.__name__)

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
            # Fetch the 
            op=self.ops[loc]
            try:
                loc,result=op.operation(state,debug=idebug)
            except MacroError as me:
                newme=state.exp.error(op,me.msg)
                raise newme from None
            
            # next being None indicates the macro has ended.
            if loc is None:
                state.next=None
                # None ends the input source and the macro invocation.
                return state
            # If a model statement has been generated, return it as an input 
            if isinstance(result,str):
                state.next=loc
                state.result=result
                return state        # Return the engine state

    # Start the engine by returning its initial state
    def start(self,exp):
        return EngineState(exp)
    
class EngineState(object):
    def __init__(self,exp):
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

    # Returns the AVal object associated with the SymbolID object
    def geta(self,symid):
        return self.lcls.geta(symid)
    # Returns the BVal object associated with the SymbolID object
    def getb(self,symid):
        return self.lcls.getb(symid)
    # Returns the CVal object associated with the SymbolID object
    def getc(self,symid):
        return self.lcls.getc(symid)
    def isDone(self):
        return self.next is None
    def model(self):
        return self.result
    # Actually set a GBLA/LCLA variable by updating its AVal object
    def seta(self,symid,value):
        old=self.geta(symid)
        old.update(value)
    # Actually set a GBLB/LCLB variable by updating its BVal object
    def setb(self,symid,value):
        old=self.getb(symid)
        old.update(value)
    # Actually set a GBLB/LCLB variable by updating its CVal object
    def setc(self,symid,value):
        old=self.getc(symid)
        old.update(value)
        
    
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

    # This method evaluates macro expressions during macro invocation.  It is the
    # interface to the pratt2 module's usage by macros.
    #
    # Method arguments:
    #   state   The active EngineState object
    #   expr    The pratt2.PExpr object containing the PToken objects being evluated
    #   peval   The pratt2.PParser object performing the evaluation
    # Returns:
    #   a AVal, BVal, CVal object or integer
    # Exception:
    #   MacroError generated from a pratt2.PParserError encountered
    def evaluate(self,state,expr,peval,debug=False,trace=False):
        try:
            return peval.run(expr,external=state,debug=debug,trace=False)
        except pratt2.PParserError as pe:
            # Convert PParserError into a MacroError
            msg="%s: '%s'" % (pe.msg,pe.ptok.src.string)
            raise MacroError(msg=msg) from None

    def evaluate_expr(self,state,expr,debug=False,trace=False):
        try:
            return expr.evaluate(external=state,debug=debug,trace=False)
        except pratt2.PParserError as pe:
            # Convert PParserError into a MacroError
            msg="%s: '%s'" % (pe.msg,pe.ptok.src.string)
            raise MacroError(msg=msg) from None

    # All subclasses must provide an operation method that returns next.
    # Returns:
    #   a tuple: (next,result)
    #   The first element of the tuple is the next operation to be performed
    #   The second element of the tuple is the result of the operation.
    def operation(self,state,debug=False):
        cls_str=assembler.eloc(self,"operation",module=this_module)
        raise NotImplementedError("%s subclass %s must provide operation() method" \
            % (cls_str,self.__class__.__name__))

    # Used to convert result of arithmetic expressions into Python integers.
    def to_integer(self,value):
        if isinstance(value,AVal):
            return value.value()
        return value

    # Used to convert the result of a logical expression into a Python True or False
    def to_logical(self,value):
        if isinstance(value,int):
            return value!=0
        return value.value()!=0


class AGO(MacroOp):
    def __init__(self,lineno,dest):
        super().__init__(lineno,dest=dest)
    def operation(self,state,debug=False):
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

        if isinstance(value,(AVal,int)):
            ndx=self.to_integer(value)
        else:
            if isinstance(value,BVal):
                found="binary value"
            elif isinstance(value,CVal):
                found="character value"
            else:
                raise ValueError("AGO %s encountered unexpected result: %s" 
                    % (lineno,value))
            raise MacroError(msg="AGO computation requires arithmentic result: %s" \
                % found)

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
        value=self.evaluate(state,self.expr,Macro.Binary,debug=debug,trace=False)

        if isinstance(value,(AVal,BVal,int)):
            logical=self.to_logical(value)
        else:
            if isinstance(value,CVal):
                found="character value"
            else:
                raise ValueError("AIF %s encountered unexpected result: %s" 
                    % (lineno,value))
            raise MacroError(msg="AIF computation requires logical result: %s" \
                % found)

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
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        gbls=state.exp.gbls
        sym=gbls.defa(self.symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class GBLB(MacroOp):
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        gbls=state.exp.gbls
        sym=gbls.defb(self.symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class GBLC(MacroOp):
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        gbls=state.exp.gbls
        sym=gbls.defc(self.symid)
        state.exp.lcls._add(sym)
        return (self.next,None)


class LCLA(MacroOp):
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        state.exp.lcls.defa(self.symid)
        return (self.next,None)


class LCLB(MacroOp):
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        state.exp.lcls.defb(self.symid)
        return (self.next,None)


class LCLC(MacroOp):
    def __init__(self,lineno,symid):
        super().__init__(lineno)
        self.symid=symid
    def operation(self,state,debug=False):
        state.exp.lcls.defc(self.symid)
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
        line=state.exp.symbol_replace(self.model,debug=debug)
        return (self.next,line)


class SETA(MacroOp):
    def __init__(self,lineno,setsym,expr,debug=False):
        self.setsym=setsym
        self.expr=expr
        super().__init__(lineno)
    def operation(self,state,debug=False):
        new_value=self.evaluate_expr(state,self.expr,debug=debug,trace=False)

        if isinstance(new_value,int):
            new_value=AVal(new_value)
        if isinstance(new_value,AVal):
            # This ensures a new object is created when setting the symbol's value
            new=AVal()
            new.update(new_value)
            new_value=new
        else:
            if isinstance(new_value,BVal):
                found="binary value"
            elif isinstance(new_value,CVal):
                found="character value"
            else:
                raise ValueError("SETA %s encountered unexpected result: %s" \
                    % (lineno,new_value))
            raise MacroError(msg="SETA requires arithmentic result: %s" % found) 
        state.seta(self.setsym,new_value)

        return (self.next,None)


class SETB(MacroOp):
    def __init__(self,lineno,setsym,expr,debug=False):
        self.setsym=setsym
        self.expr=expr
        super().__init__(lineno)
    def operation(self,state,debug=False):
        new_value=self.evaluate(state,self.expr,Macro.Binary,debug=debug,trace=False)

        if not isinstance(new_value,(int,AVal,BVal)):
            if isinstance(new_value,CVal):
                raise MacroError(\
                    msg="SETB requires arithmentic result: character value")
            else:
                raise ValueError("SETB %s encountered unexpected result: %s" \
                    % (lineno,new_value))

        state.setb(self.setsym,new_value)
        return (self.next,None)


class SETC(MacroOp):
    def __init__(self,lineno,setsym,chars,start_expr=None,len_expr=None,debug=False):
        self.setsym=setsym      # Character symbol being set (SymbolID object)
        self.chars=chars        # The character string being assigned
        self.start=start_expr   # The start of the sub-string (PExpr object) or None
        self.length=len_expr    # The length of the sub-string (PExpr object) or None
        super().__init__(lineno)

    def operation(self,state,debug=False):
        exp=state.exp
        # Need to do symbolic replacement with new searcher
        string=exp.symbol_replace(self.chars,debug=debug)

        # Extract sub-string if specified
        if self.start is not None:
            string=self.sub_string(string,state,debug=debug)
        # 'string' is now the string we want to set
        state.setc(self.setsym,string)

        return (self.next,None)

    # Extract a sub-string from the character string
    def sub_string(self,string,state,debug=False):
        # Evaluate the starting sub-string position
        start_value=self.evaluate(state,self.start,Macro.Arith,\
            debug=debug,trace=False)

        # Evalueate the length of the sub-string
        length_value=self.evaluate(state,self.length,Macro.Arith,\
            debug=debug,trace=False)

        start=self.to_integer(start_value)  # Make sure its an integer
        length=self.to_integer(length_value) # Make sure its an integer

        # Validate the starting sub-string position 
        strlen=len(string)
        if start<1 or start>strlen:
            raise MacroError("substring starting position out of range (1-%s): %s" \
                % (strlen,start))

        # Validate the sub-string position length
        if length>0:
            end=start+length-1
            if end<1 or end>strlen:
                raise MacroError("substring ending position out of range (1-%s): %s" \
                    % (strlen,end))
        elif length==0:
            return ""
        else:
            raise MacroError("substring length may not be negative: %s" % length)

        # Extract the substring from the Python string
        start-=1     # Convert starting position to Python string index relative to 0     
        return string[start:end]


#
#  +--------------------------+
#  |                          |
#  |   Macro Symbol Classes   |
#  |                          | 
#  +--------------------------+
#

# Base class for all Macro Variable Symbols
class MacroSymbol(object):
    def __init__(self,symbol,entrycls):
        assert isinstance(symbol,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),symbol)

        # Note: other rules concerning variable symbols are not enforced here.  They
        # must be enforced during statement processing in a special pre-processor method
        # or through use of a parser designed to recognize valid symbols.
        self.symbol=symbol.var  # Symbol including the starting &
        self.entrycls=entrycls  # Entry class
        self.ro=False           # Indicates whether symbol is read-only
        self.values=[]          # The symbol's character, binary or arithmetic values
        # Set for symbols when defined. Used to filter symbols when MHELP 0x20 is set
        self.gbl=False          # Set for symbols when defined. Used to filter MHELP
        # Macro symbolic parameter. 
        self.parm=False         # Used to indentify symbols when MHELP 0x10 is set
        
        # Attributes are currently only supported for the symbol name itself.
        self.attr={}            # Attribute dictionary

        # Determine the number of elements in value list
        entries=symbol.length()
        for n in range(entries):
            v=entrycls()
            self.values.append(v)
        self.attr["N"]=entries-1

    # Returns the attribute value.
    def getAttr(self,attr):
        return self.attr[attr]

    # Return a subscript value
    # Exceptions:
    #   IndexError   if subscript is out of range
    def getValue(self,symbol):
        # Note: after debugging, these checks should be eliminated.  All access
        # should be through the MacroSymbols object and the checks should occur there
        assert isinstance(symbol,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"getValue",module=this_module),symbol)
        assert symbol.var==self.symbol,\
            "%s symbol's variable name ('%s') does not match symbol " \
                % (assembler.eloc(self,"getValue",module=this_module),\
                    self.symbol,symbol.var)

        return self.values[symbol.sub]

    # Sets a value in one of the symbols subscript
    # Sets a subscript value
    # Exceptions:
    #   IndexError   if subscript is out of range
    def setValue(self,symbol,value,user=True):
        # Note: after debugging, these checks should be eliminated.  All access
        # should be through the MacroSymbols object and the checks should occur there
        assert isinstance(symbol,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"setValue",module=this_module),symbol)
        assert symbol.var==self.symbol,\
            "%s symbol's variable name ('%s') does not match symbol name being " \
                "referenced: '%s'" \
                % (assembler.eloc(self,"setValue",module=this_module),\
                    self.symbol,symbol.var)
        assert isinstance(value,self.entrycls),\
            "%s 'value' argument must be an instance of %s: %s" \
                % (assembler.eloc(self,"setValue",module=this_module),\
                    self.entrycls.__name__,value)
        assert (not user) or (not self.ro),\
            "%s symbol '%s' read-only, can not set value" \
                % (assembler.eloc(self,"setValue",module=this_module),self.symbol)        

        self.values[symbol.sub]=value

# This object encapsulates a symbolic variable's reference.  The reference is used
# to define a local or global variable.  It is used to access a variable's value,
# represented by a subclass of SymbolValue.  No subscripting, numeric subscripting
# and variable subscripting are all supported.
#
# Case sensitivity is managed via the 'variable' argument.  Case must be established
# when the object is created.
class SymbolID(object):
    def __init__(self,variable,subscript=0):
        assert isinstance(variable,str) and len(variable)>0,\
            "%s 'variable' argument must be a non-empty string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),variable)
        assert variable[0]=='&',\
            "%s 'variable' argument must start with an '&': '%s'" \
                % (assembler.eloc(self,"__init__",module=this_module),variable)

        self.var=variable        # The symbolic symbols's name (with '&')
        self.sub=None            # Integer or SymbolID of subscript

        # The referenced subscript
        #    &var     references "subscript" 0
        #    &var(n)  references subscript 1 to n
        #    &var(&x) references subscript defined by variable symbol &x
        # When used in a definition it represents the number of subscripted values
        #    &var    0 defines an unsubscipted value
        #    &var(n) n defines a subscripted variable of n elements (in Python, n+1
        #              elements in the variable list of xVal objects.
        if isinstance(subscript,int):
            self.sub=subscript
        elif isinstance(subscript,str) and len(subscript)>1 and subscript[0]=="&":
            self.sub=SymbolID(subscript)
        elif subscript is None:
            self.sub=0
        else:
            raise ValueError("%s 'subscript' argument invalid: '%s'" \
                % (assembler.eloc(self,"__init__",module=this_module),subscript)) 

    def __str__(self):
        return "%s(variable=%s,subscipt=%s)" \
            % (self.__class__.__name__,self.var,self.sub)

    # Returns the number of list elements required for a definition
    # For an unsubscripted variable one element is created in the value list, 0+1
    # For a subscripted variable, n+1 elements are created. This also creates an
    # unsubscripted value allowing dual usage.
    def length(self):
        return self.sub+1

# Base class for all macro symbol values
class SymbolValue(object):
    def __init__(self,value):
        self._value=value         # The macro symbol's value
        self.attr={"K":0}         # Attribute Dictionary
    
    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    # Returns the attribute value.
    def getAttr(self,attr):
        return self.attr[attr]

    # This method returns a string used to replace the symbol in a model statement
    # Each subclass must provide this method
    def string(self):
        raise NotImplementedError("%s subclass %s must provide string() method" \
            % (assembler.eloc(self,"string",module=this_module),\
                self.__class__.__name__))
        
    # Updates this SymbolValue object with a vew value
    def update(self,value):
        raise NotImplementedError("%s subclass %s must provide update() method" \
            % (assembler.eloc(self,"update",module=this_module),\
                self.__class__.__name__))
        
    # This method returns the symbol's value when encoutered in a macro statement
    # Each subclass must provide this method
    def value(self):
        raise NotImplementedError("%s subclass %s must provide value() method" \
            % (assembler.eloc(self,"value",module=this_module),\
                self.__class__.__name__))

# GBLA or LCLA Arithmetic Macro Variable Symbol
class ASym(MacroSymbol):
    def __init__(self,symbol):
        super().__init__(symbol,AVal)

class AVal(SymbolValue):
    def __init__(self,value=0):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer: '%s'" \
                % (assembler.eloc(self,"__init__",module=this_module),value)

        super().__init__(value)

    #
    # Infix Arithmetic Operations
    #

    # Addition
    def __add__(self,other):
        return AVal(self.value() + self.__other(other))
    def __radd__(self,other):
        return AVal(self.__other(other) + self.value())

    # Division (true division handled the same a floor division)
    def __floordiv__(self,other):
        return AVal(self.value() // self.__other(other))
    def __rfloordiv__(self,other):
        return AVal(self.__other(other) // self.value())
    def __truediv__(self,other):
        return self.__floordiv__(other)
    def __rtruediv__(self,other):
        return self.__rfloordiv(other)

    # Multiplication
    def __mul__(self,other):
        return AVal(self.value() * self.__other(other))
    def __rmul__(self,other):
        return AVal(self.__other(other) * self.value())

    # Subtraction
    def __sub__(self,other):
        return AVal(self.value() - self.__other(other))
    def __rsub__(self,other):
        return AVal(self.__other(other) - self.value())

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    #
    # Unary Arithmetic Operations
    #

    # Unary minus
    def __neg__(self):
        return AVal(-self.value())

    # Unary plus
    def __pos__(self):
        return AVal(self.value())

    #
    # Infix Comparison Operations
    #
    def __lt__(self,other):
        return BVal(self.value() < self.__other(other))
    def __le__(self,other):
        return BVal(self.value() <= self.__other(other))
    def __eq__(self,other):
        return BVal(self.value() == self.__other(other))
    def __ne__(self,other):
        return BVal(self.value() != self.__other(other))
    def __ge__(self,other):
        return BVal(self.value() >= self.__other(other))
    def __gt__(self,other):
        return BVal(self.value() > self.__other(other))    

    # Returns the integer value of the operand
    # Exception:
    #   ValueError if operand is neither an integer nor an AVal object
    def __other(self,other):
        if isinstance(other,(AVal,BVal)):
            return other.value()
        elif isinstance(other,int):
            return other
        else:
            raise pratt2.PEvaluationError(msg="operation not supported between an "
                "arithmetic value and %s" % other)

    # Returns the object's value as a string
    def string(self):
        return "%s" % self._value

    # Updates the object's value from either an integer or another AVal object
    def update(self,value):
        if isinstance(value,AVal):
            self._value=value.value()
        elif isinstance(value,int):
            self._value=value
        else:
            cls_str=assembler.eloc(self,"update",module=this_module)
            raise ValueError("%s 'value' argument must be an integer: '%s'" \
                % (cls_str,value))

    # Returns the AVal object's integer value
    def value(self):
        return self._value

# GBLB or LCLB Binary Macro Variable Symbol
class BSym(MacroSymbol):
    def __init__(self,symbol):
        super().__init__(symbol,BVal)

class BVal(SymbolValue):
    values={True:1,False:0,1:1,0:0}
    def __init__(self,value=0):
        val=self.__check(value)
        super().__init__(val)

    # Addition
    def __add__(self,other):
        return AVal(self.value() + self.__other(other))
    def __radd__(self,other):
        return AVal(self.__other(other) + self.value())

    # Division (true division handled the same a floor division)
    def __floordiv__(self,other):
        return AVal(self.value() // self.__other(other))
    def __rfloordiv__(self,other):
        return AVal(self.__other(other) // self.value())
    def __truediv__(self,other):
        return self.__floordiv__(other)
    def __rtruediv__(self,other):
        return self.__rfloordiv(other)

    # Multiplication
    def __mul__(self,other):
        return AVal(self.value() * self.__other(other))
    def __rmul__(self,other):
        return AVal(self.__other(other) * self.value())

    # Subtraction
    def __sub__(self,other):
        return AVal(self.value() - self.__other(other))
    def __rsub__(self,other):
        return AVal(self.__other(other) - self.value())

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,self._value)

    #
    # Unary Arithmetic Operations (not supported with character values)
    #

    # Unary minus
    def __neg__(self):
        return AVal(-self.value())

    # Unary plus
    def __pos__(self):
        return AVal(self.value())
        
    #
    # Infix Comparison Operations
    #
    def __lt__(self,other):
        return BVal(self.value() < self.__other(other))
    def __le__(self,other):
        return BVal(self.value() <= self.__other(other))
    def __eq__(self,other):
        return BVal(self.value() == self.__other(other))
    def __ne__(self,other):
        return BVal(self.value() != self.__other(other))
    def __ge__(self,other):
        return BVal(self.value() >= self.__other(other))
    def __gt__(self,other):
        return BVal(self.value() > self.__other(other))    

    def __check(self,value):
        try:
            val=BVal.values[value]
        except KeyError:
            if isinstance(value,int):
                if value:
                    val=1
                else:
                    val=0
            else:
                cls_str=assembler.eloc(self,"__check",module=this_module)
                raise ValueError("%s 'value' argument for binary symbol '%s' "
                    "invalid: %s" % (cls_str,symbol,value))
        return val

    # Returns the integer value of the operand
    # Exception:
    #   ValueError if operand is neither an integer nor an AVal object
    def __other(self,other):
        if isinstance(other,(AVal,BVal)):
            return other.value()
        elif isinstance(other,int):
            return other
        else:
            raise pratt2.PEvaluationError(\
                msg="operation not supported between a binary value and %s" % other)
        
    def string(self):
        return "%s" % self._value 
        
    def update(self,value):
        if isinstance(value,BVal):
            self._value=value.value()
        else:
            val=self.__check(value)
            self._value=val

    def value(self):
        return self._value

# GBLC or LCLC Binary Macro Variable Symbol
class CSym(MacroSymbol):
    def __init__(self,symbol):
        super().__init__(symbol,CVal)

# The CVal object does not support direct use in arithmetic expressions.
# In arithmetic expressions the asmfsmbp.SymRefToken (a subclass of pratt2.PLit)
# will attempt to convert the SETC recognize the content of the SETC character
# value as a self-defining term.  If it is recognized, an integer is returned and
# the arithmetic operation is performed directly on the integer, not this object.
# As a consequence, methods such as __add__ or __sub__, etc., are not included in
# this class.
class CVal(SymbolValue):
    def __init__(self,value=""):
        assert isinstance(value,str),\
            "%s 'value' argument must be a string: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),value)

        super().__init__(value)
        self.__setK()
        self.__translate()
        # This is set when a self-defining term is recognized during arithmetic
        # expression processing of this SETC symbol value.
        # See asmfsmbp.PLitSym.avalue() method.
        self._sdvalue=None

    def __str__(self):
        return '%s("%s")' % (self.__class__.__name__,self._value)

    #
    # Infix Comparison Operations (only supports character to character comparisons)
    #
    def __lt__(self,other):
        return BVal(self.value() < self.__other(other))
    def __le__(self,other):
        return BVal(self.value() <= self.__other(other))
    def __eq__(self,other):
        return BVal(self.value() == self.__other(other))
    def __ne__(self,other):
        return BVal(self.value() != self.__other(other))
    def __ge__(self,other):
        return BVal(self.value() >= self.__other(other))
    def __gt__(self,other):
        return BVal(self.value() > self.__other(other)) 

    # Returns the othr value as an EBCDIC string for use in comparison operations
    # Exception:
    #   ValueError if operand is neither an integer nor an AVal object
    def __other(self,other):
        if isinstance(other,CVal):
            return other.value()
        elif isinstance(other,str):
            return assembler.CPTRANS.a2e(other)
        else:
            raise pratt2.PEvaluationError(msg="operation not supported between a "
                "character value and %s" % other)

    def __setK(self):
        self.attr["K"]=len(self._value)

    def __translate(self):
        self._ebcdic=assembler.CPTRANS.a2e(self._value)

    def string(self):
        return self._value

    # Updates the object's value from either an integer or another AVal object
    def update(self,value):
        if isinstance(value,CVal):
            self._value=value.value()
        elif isinstance(value,str):
            self._value=value
        else:
            cls_str=assembler.eloc(self,"update",module=this_module)
            raise ValueError("%s 'value' argument must be an integer: '%s'" \
                % (cls_str,value))
        self.__setK()
        self.__translate()
        self._sdvalue=None

    # This is only when performing comparison operations on EBCDIC strings
    def value(self):
        return self._ebcdic


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
class MacSymbols(object):
    def __init__(self,case,unique=False,gbl=False):
        self.syms={}        # Dictionary of variable symbols
        self.unique=unique  # Only new unique symbols may be defined
        self.gbl=gbl        # Sets a symbol's gbl attribute
        self.case=case      # Enables case sensitivity for macro symbols

    # Defines a symbol variable
    # Method Arguments:
    #   symbol    A SymbolID object defining the variable and its subscripts
    #   cls       The class object of the variable type: ASym, BSym or CSym
    #   unique    Specify True if the symbol may not already be defined
    # Returns:
    #   the created, or previously created if unique=False, ASym, BSym or CSym object
    # Exceptions:
    #   MacroError  variable symbol already created if unqiue is being enforced.
    def __define(self,symbol,cls,parm=False,unique=False,ro=False):
        assert isinstance(symbol,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"__define",module=this_module),symbol)
        assert self.case or symbol.var == symbol.var.upper(),\
             "SymbolID not case insensitive: %s" % symbol

        name=symbol.var
        try:
            s=self.syms[name]
            if self.unique or unique:
                raise MacroError(msg="symbol already defined: '%s'" % name)
        except KeyError:
            s=cls(symbol)
            s.gbl=self.gbl     # Set symbol's gbl attribute
            s.parm=parm        # Identify if symbol is a macro parameter
            s.ro=ro            # Set the symbol's read-only status
            self.syms[name]=s
        return s

    def _add(self,sym,n=None,pos=None,unique=False):
        assert isinstance(sym,MacroSymbol),\
            "%s 'sym' argument must be a MacroSymbol object: %s" \
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
    #   KeyError if symbol variable name not defined
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
            i=SymbolID(symbol.upper())
        else:
            i=SymbolID(symbol)
        s=self.defa(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,AVal(value),user=False)

    def _initb(self,symbol,value,parm=False,ro=False,unique=False):
        if not self.case:
            i=SymbolID(symbol.upper())
        else:
            i=SymbolID(symbol)
        s=self.defb(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,BVal(value),user=False)

    def _initc(self,symbol,value,parm=False,ro=False,unique=False):
        if not self.case:
            i=SymbolID(symbol.upper())
        else:
            i=SymbolID(symbol)
        s=self.defc(i,parm=parm,unique=unique,ro=ro)
        s.setValue(i,CVal(value),user=False)

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
    #   the referenced SymbolValue object: AVal, BVal or CVal object
    # Exceptions:
    #   MacroError when variable symbol is undefined, 
    #              when a subscript is provided for an unsubscripted symbol, 
    #              when the subscript is out of range, or 
    #              when the subscript symbol itself is undefined
    def _reference(self,symbol,updating=False):
        # This raises an uncaught MacroError if the symbol is not defined
        sym=self._reference_symbol(symbol)
        # sym is a MacroSymbol object
        var=symbol.var           # Variable symbol name from SymbolID object

        # Check for read-only symbol if it is being referenced for an update by SETx
        if updating and sym.ro:
            raise MacroError(msg="symbol '%s' read-only, can not SET" % sym.name)

        values=len(sym.values)
        # Access a symbol's value that is not subscripted
        if values==1:
            sub=symbol.sub
            if isinstance(sub,int) and sub==0:
                return sym.values[0]
            else:
                raise MacroError(msg="symbol '%s' not subscripted" % var)
        
        # Symbol is subscripted, determine the subscript value
        if isinstance(symbol.sub,SymbolID):
            # Might raise a MacroError
            # Note: This ends up being a recursive call back to this method to
            # locate the subscript's value
            sub=self.geta(symbol.sub).value()
        else:
            sub=symbol.sub
            
        # Validate the subscript value is within range.
        if sub<1 or sub>values:
            raise MacroError(msg="symbol '%s' subscript out of defined range "
                "(1-%s): %s" % (var,values,sub))
        
        return sym.values[sub]

    # References a symbolic variable MacroSymbol whose reference is defined by a 
    # SymbolID object's symbolic variable name.
    # Method Arguments:
    #   symbol    the SymbolID object identifying the referenced variable and subscript
    #   updating  If True, the symbol is being referenced for an update (SETx)
    # Returns:
    #   the referenced SymbolValue object, AVal, BVal or CVal object
    # Exceptions:
    #   MacroError if variable symbol is undefined, if subscript provided for
    #   unsubscripted symbol, if subscript is out of range or if subscript symbol
    #   itself is undefined.
    def _reference_symbol(self,symbol):
        assert isinstance(symbol,SymbolID),\
            "%s 'symbol' argument must be a SymbolID object: %s" \
                % (assembler.eloc(self,"_reference_symbol",module=this_module),\
                    symbol)
        assert self.case or symbol.var == symbol.var.upper(),\
            "symbol not case insensitive: %s" % symbol

        try:
            return self.syms[symbol.var]   # Locate its MacroSymbol object
        except KeyError:
            raise MacroError(msg="undefined symbol: '%s'" % symbol.var) from None

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
    #   the ASym, BSym or CSym object of the defined symbol.
    # Exceptions:
    #   MacroError if unique=True and symbol is already defined
    def defa(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,ASym,parm=parm,unique=unique,ro=ro)
    
    def defb(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,BSym,parm=parm,unique=unique,ro=ro)

    def defc(self,symbol,parm=False,unique=False,ro=False):
        return self.__define(symbol,CSym,parm=parm,unique=unique,ro=ro)

    # Return the value of a symbol from a symbol ID's value
    #   geta   Returns an arithmetic symbol's AVal object
    #   getb   Returns a binary symbol's BVal object
    #   getc   Returns a character symbol's CVal object
    #   getx   Returns the symbol's ASym, BSym or CSym object
    # Method Argument:
    #   symbol A SymbolID object identifying the symbol's name and subscripting 
    # Returns:
    #   an AVal, BVal or CVal object
    # Excpetions: the caller needs to catch and handle appropriately
    #   MacroError if the variable is not defined, subscript our of range or
    #              the symbol is not of the requested type.
    def geta(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,AVal):
            raise MacroError(msg="variable symbol '%s' not LCLA or GBLA" % symbol.var)
        return v

    def getb(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,BVal):
            raise MacroError(msg="variable symbol '%s' not LCLB or GBLB" % symbol.var)
        return v

    def getc(self,symbol):
        v=self._reference(symbol)   # May raise a MacroError exception
        if not isinstance(v,CVal):
            raise MacroError(msg="variable symbol '%s' not LCLC or GBLC" % symbol.var)
        return v

    def getx(self,symbol):
        return self._reference(symbol)   # May raise a MacroError exception

    # These three methods set a sybmol's value based upon a symbol ID object
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
        v=AVal(value)
        s=self._reference(symbol,updating=True)
        s.setValue(symbol,v,user=user)

    def setb(self,symbol,value,user=True):
        v=BVal(value)
        s=self._reference(symbol,updating=True)
        s.setValue(symbol,v,user=user)

    def setc(self,symbol,value,user=True):
        v=CVal(value)
        s=self._reference(symbol,updating=True)
        s.setValue(symbol,v,user=user)


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
class Invoker(object):
    gblc=["&SYSASM","&SYSDATC","&SYSDATE","&SYSQ","&SYSTIME","&SYSVER"]
    mhelp="MHELP %2d %s &SYSNDX:%s nest:%s"   # MHELP data prefix
    searcher=asmfsmbp.SymRefSearch()
    def __init__(self,mgr,debug=False):
        self.mgr=mgr            # Manager helps me to expand macro.
        self.asm=mgr.asm        # The assembler
        self.case=self.asm.case # Specifies case sensitivity is enabled when True
        #print("Invoker.case=%s" % self.case)
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
        
        # MHELP related attributes.  See mhelp() method
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
        l=MacSymbols(self.case,unique=True)
        
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

        # NOTE: The active CSECT name is not defined until Pass 1.  All macro 
        # processing occurs during the pre-process Pass 0.  Until Pass 0 and Pass 1
        # are merged, these symbols must be handled with special logic in Pass 0.
        # See Assembler.__oper_id() method
        #
        # Tracking sections in Pass 0 assumes that the Pass 1 processing will be
        # successful.  It is possible to incorrectly report the section name in
        # the SYSCECT symbolic variable if the statement that would set the name
        # fails in Pass 1.
        l._initc("&SYSECT",self.asm.sysect,ro=True)
        #l._initc("&SYSLOC",cursect,ro=True)

        l._initc("&SYSMAC",self.macro.name,ro=True)
        
        self.sysndx=self.mgr.getSysNdx()
        l._initc("&SYSNDX",self.sysndx,ro=True)
        l._inita("&SYSNEST",self.mgr.nesting()+1,ro=True)
        
        # Establish ASMA specific system variable symbols
        # These allow a macro to interrogate the current XMODE settings for
        # code generation.
        try:
            ccw=self.asm._xmode_fetch("CCW")
        except KeyError:
            ccw=""
        l._initc("&SYSCCW",ccw,ro=True)
        
        try:
            psw=self.asm._xmode_fetch("PSW")
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
            
            value=symo.values[0]
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
            if xsym.parm or (xsym.gbl and self._mhelp_20) or len(xsym.values)>1:
                continue
            syms.append(sym)
        self.__mhelp_dump(syms,n)

    # Enters the macro.
    def enter(self):
        # Remember where the macro was invoked
        self.macro._refs.append(self.lineno)
        self.mhelp_init()              # Initialize MHELP values
        self.mhelp_01()                # Trace macro entry if requested
        self.mhelp_10()                # Dump parameters if requested
        self.state=self.engine.start(self)     # Start the macro engine 
    
    # Creates a MacroError object from one supplied, adding macro specific
    # information to the error and reflecting the invoking statement as the error's
    # location.
    def error(self,op,msg,linepos=None):
        msg="MACRO ERROR in %s @%s: %s" % (self.macro.name,op.lineno,msg)
        return MacroError(line=self.lineno,linepos=linepos,msg=msg)
    
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
        assert isinstance(stmt,assembler.Stmt),\
            "%s 'stmt' argument must be a Stmt object: %s" \
                % (assembler.eloc(self,"macstmt",module=this_module),stmt)
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
        macro.parms(stmt,self.lcls,self.asm.fsmp,debug=stmt.trace)

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
                parms.append(key)
        self.__mhelp_dump(parms,0x10)

    # Perform variable symbol replacement in a text string
    # Method Arguments:
    #   line  a model statement text string
    # Returns:
    #   the original string or string with variable symbols replaced.
    def symbol_replace(self,line,debug=False):
        assert isinstance(line,str),\
            "%s 'line' argument must be a string: %s" \
                % (assembler.eloc(self,"symbol_replace",module=this_module),line)

        # Note: lines not requiring expansion do not reach this method
        if __debug__:
            if debug:
                cls_str=assembler.eloc(self,"symbol_replace",module=this_module)

        text=line
        syms=Invoker.searcher.search(text)
        if len(syms)==0:
            if __debug__:
                if debug:
                    print("%s no syms found" % cls_str)

            return line
        # Now need to process each found symbolic variable reference.

        # Found symbolic variables, so replace them if found
        pos=0   # position in original text
        new=""
        lcls=self.lcls
        case=self.case
        for sym in syms:
            # sym is a asmfsmbp.SymRefPart object containing a asmfsmbp.SymRefMO
            if __debug__:
                if debug:
                    print("%s: %s" % (cls_str,sym))

            if sym.beg>pos:
                new="%s%s" % (new,text[pos:sym.beg])

                if __debug__:
                    if debug:
                        print("%s added input to text: '%s'" % (cls_str,new))

            try:
                value=lcls.getx(sym.SymID(case))
                new="%s%s" % (new,value.string())
            except KeyError:
                # symbolic variable not found add it to the replacement
                new="%s%s" % (new,sym.string)
            pos=sym.end

            if __debug__:
                if debug:
                    print("%s added symbol value to text: '%s'" % (cls_str,new))

            pos=sym.end
        # Pick remainder of original statement if any
        if sym.end<len(text):
            new="%s%s" % (new,text[sym.end:])

            if __debug__:
                if debug:
                    print("%s added last of input to text: '%s'" % (cls_str,new))

        if __debug__:
            if debug:
                print("%s: original:   '%s'" % (cls_str,text))
                print("%s: repacement: '%s'" % (cls_str,new))

        return new

class MacroLanguage(object):
    def __init__(self,asm):
        self.asm=asm           # The assembler
        self.bltin=asm.bltin   # Enable/disable builtin macros
        self.case=asm.case     # Inherits the case sensitivity option
        #print("MacroLanguage.case=%s" % self.case)
        self.parsers=asm.fsmp  # asmfsmbp.Parsers object

        # Macro processing state:
        #  0 ==> not processing macro definitions
        #  1 ==> macro started expecting prototype statement
        #  2 ==> prototype found, processing macro body statements
        #  3 ==> macro definition abandoned, flush till mend
        # This state is used to define actions in method defining()
        self.state=0        # Macro processing state.

        # This is the Macro object presently being defined.  Macor directives and
        # model directives are added to this object.
        self.indefn=None
        # Switch to debug a macro definition.
        self.ddebug=False   # Set by define() method from MACRO assembler directive.

        # Identifies method for processing a directive
        self.directives=self.__init_directives()

        self.macros={}      # Defined macros
        if self.bltin:
            self.__built_ins()  # Set up all built-in macros.

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

    # Define built in macros
    def __built_ins(self):
        macs=[Test,]
        for m in macs:
            b=m(self.case)
            self.addMacro(b)

    # Initialize dictionary mapping macro directive to processing method
    def __init_directives(self):
       # Define each macro directive's processing method within this class
       d={}
       d["AGO"]=self._AGO
       d["AIF"]=self._AIF
       d["ANOP"]=self._ANOP
       d["GBLA"]=self._GBLA
       d["GBLB"]=self._GBLB
       d["GBLC"]=self._GBLC
       d["LCLA"]=self._LCLA
       d["LCLB"]=self._LCLB
       d["LCLC"]=self._LCLC
       d["MACRO"]=self._MACRO
       d["MEND"]=self._MEND
       d["MEXIT"]=self._MEXIT
       d["SETA"]=self._SETA
       d["SETB"]=self._SETB
       d["SETC"]=self._SETC
       
       # Return the directive dictionary
       return d

    # Returns the GlobalSymbols object with system variables initialized
    def __init_globals(self):
        g=MacSymbols(self.case,unique=False,gbl=True)
        now=self.asm.now         # This is an instance of time.struct_time

        g._initc("&SYSASM","A SMALL MAINFRAME ASSEMBLER")

        # now is a struct_time object
        year="%04d" % now.tm_year
        month="%02d" % now.tm_mon
        day="%02d" % now.tm_mday
        datc="%s%s%s" % (year,month,day)

        # Assembly date: YYYYMMDD
        g._initc("&SYSDATC",datc,ro=True)

        # Assembly date: MM/DD/YY
        date="%s/%s/%s" % (month,day,year[2:4])
        g._initc("&SYSDATE",date,ro=True)

        # A single quote
        g._initc("&SYSQ","'",ro=True)

        # Assembly time: HH.MM
        hour="%02d" % now.tm_hour
        minute="%02d" % now.tm_min
        time="%s.%s" % (hour,minute)
        g._initc("&SYSTIME",time,ro=True)

        # Assembler version: version.release.modification
        ver="%s.%s.%s" % self.asm.version
        g._initc("&SYSVER",ver,ro=True)

        return g

    # Perform a parse using the supplied FSM-based parser on statement operands.
    # Method arguments:
    #   stmt      An assembler.Stmt object
    #   parser    A asmfsmbp.FSMParser object
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
    #   asmfsmbp.AsmParserError object if available.
    def __parse(self,stmt,parser,required=False):
        flds=stmt.fields
        operands=flds.operands
        
        # Only parse operands if they are actually present in the statement
        if operands is None:
            if required: 
                raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                    msg="required operand field missing")
            else:
                return None

        try:
            # Returns a asmfsmbp.xxxScope object
            return parser.parse(operands)
        except asmfsmbp.AsmParserError as me:
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                linepos=me.token.linepos+flds.operpos+1,msg=me.msg) from None

    # Extracts the symbol name from the name field as a SymbolID object.
    # May raise AssemblerError is SETx statement does not have a symbol in the name
    # field.
    def __set_name(self,stmt,setx,debug=False):
        fields=stmt.fields
        if not fields.symbol:
            raise assembler.AssemblerError(line=stmt.lineno,linepos=1,\
                msg="%s macro directive symbolic variable name unrecognized: %s" \
                    % (setx,flds.name))

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

    # Establish global SETC symbol from the assembler's external drive
    # Method Arguments:
    #   symbol   The name of the GBLA symbolic variable being created
    #   value    The value to which the SETC symbol is to be set or None
    # Exceptions:
    #   MacroError if the symbol being defined is already defined as read-only.
    #            &SYSxxxx symbolic variables can be read-only.
    def _init_gblc(self,symbol,value):
        # Establish global SETC symbol from the assembler's external drive
        assert isinstance(symbol,str),\
            "%s 'symbol' argument must be a string: %s" \
                % (assembler.eloc(self,"_init_gblc",module=this_module),symbol)
        assert len(symbol)>0,\
            "%s 'symbol' argument must be a non-empty string: '%s'" \
                % (assembler.eloc(self,"_init_gblc",module=this_module),symbol)
        assert isinstance(value,str) or value is None,\
            "%s 'value' argument must be a string: %s" \
                % (assembler.eloc(self,"_init_gblc",module=this_module),value)
        
        if symbol[0]!="&":
            name="&%s" % symbol
        else:
            name=symbol
        if not self.case:
            sid=SymbolID(name.upper())
        else:
            sid=SymbolID(name)
        s=self.gbls.defc(sid) 
        if value is not None:
            s.setValue(sid,CVal(value),user=True)


   #
   # MACRO DEFINITION PROCESSING
   #

    # Process a macro body statement
    def _body(self,stmt,debug=False):
        flds=stmt.fields
        if flds.silent:
            # Silent comments are dropped at this point
            # Regular comments become model statements
            return
        stmt.fields=flds
        try:
            method=self.directives[flds.opuc]
        except KeyError:
            method=self._model
           
        # May raise assembler.AssemblerError for encountered error
        if debug:
            cls_str=assembler.eloc(self,"_body",module=this_module)
            mcls,mname=method_name(method)
            print("%s macro directive processing method: %s()" % (cls_str,mname))
        method(stmt,debug=debug)


    # Process a model statement in a macro definition
    def _model(self,stmt,debug=False):
        flds=stmt.fields
        if flds.sequence:
            if not self.case:
                seq=flds.name.upper()
            else:
                seq=flds.name
            model=" %s" % flds.text[flds.oppos:]
        else:
            seq=None
            model=flds.text

        if debug:
            cls_str=assembler.eloc(self,"_model",module=this_module)
            print("%s model: '%s'" % (cls_str,model))
        
        self.indefn._model(stmt.lineno,model,seq=seq,debug=debug)
        

    # Process a prototype statement in a macro definition
    def _prototype(self,stmt,debug=False):
        flds=stmt.fields

        if flds.name is not None:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="invalid prototype name symbol variable: '%s'" % flds.name)

        assert not flds.symbol or isinstance(flds.symid,SymbolID),\
             "%s StmtFields.symid must be a SymbolID: %s" \
                % (assembler.eloc(self,"_prototype",module=this_module),flds.symid)

        scp=asmfsmbp.PrototypeScope(self.case)
        # This method may raise an assembler.AssemblerError
        scope=self.parsers.parse_operands(stmt,"proto",scope=scp,required=False)
        if scope is None:
            pos=[]
            keys={}
        else:
            pos=scope.pos_parms
            keys=scope.key_parms

        lblsym=flds.symid
        if lblsym is not None:
            if lblsym.sub is not None and lblsym.sub!=0:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="prototype name symbol variable %s may not be subscripted" \
                         % lblsym.var)
            var=lblsym.var
        else:
            var=None

        proto=Prototype(flds.opuc,lblsym=var,positionals=pos,keywords=keys)

        if __debug__:
            if debug:
                print("%s starting macro:\n%s" \
                    % (assembler.eloc(self,"_prototype",module=this_module),proto))

        # Prototype statement successfully processed, can proceed with definition
        self.indefn=Macro(proto,self.case,defn=stmt.lineno)


   # 
   # MACRO DIRECTIVE PROCESSING
   #

    # AGO macro directive found in macro definition
    def _AGO(self,stmt,debug=False):
        flds=stmt.fields
        lineno=stmt.lineno

        scope=self.parsers.parse_operands(stmt,"ago",required=True)

        computed=scope.lextoks  # Computed AGO expression lexical tokens
        #print("[%s] computed: %s" % (lineno,computed))
        sequence=scope.seq      # SEQSYM lexical tokens

        # Test if this is a simple AGO with a seqence symbol.
        if len(computed)==0:
            # Extract sequence symbol from the lexical token
            if not self.case:
                seqsym=sequence[0].string.upper()
            else:
                seqsym=sequence[0].string
            self.indefn._ago(lineno,seqsym,seq=self.__seq(flds))
            return

        # For the computed AGO, need to create PExpr object and list of 
        # sequence symbols.

        # Convert arithmetic expression lexical tokens into pratt2.PExpr object
        expr=self.parsers.L2ArithExpr("_AGO",stmt,ltoks=computed,debug=debug)
        
        # Convert list of SEQSYM lexical tokens into a list of strings
        dest=[]
        for ltok in sequence:
            if not self.case:
                seqsym=ltok.string.upper()
            else:
                seqsym=ltok.string
            dest.append(seqsym)

        # Add the operation to the macro definition
        self.indefn._agoc(lineno,dest,expr,seq=self.__seq(flds))

    def _AIF(self,stmt,debug=False):
        flds=stmt.fields
        lineno=stmt.lineno

        scope=self.parsers.parse_operands(stmt,"aif",required=True)

        # Convert arithmetic expression lexical tokens into pratt2.PExpr object
        expr=self.parsers.L2BinaryExpr("_AIF",stmt,ltoks=scope.lextoks,debug=debug)

        # Add the operation to the macro definition
        if not self.case:
            seqsym=scope.seq.string.upper()
        else:
            seqsym=scope.seq.string
        self.indefn._aif(lineno,seqsym,expr,seq=self.__seq(flds))

    def _ANOP(self,stmt,debug=False):
        self.indefn._anop(stmt.lineno,seq=self.__seq(stmt.fields))
        return
       
    # GBLA macro directive found
    def _GBLA(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"GBLA",self.indefn._gbla,debug=debug)

    # GBLB macro directive found
    def _GBLB(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"GBLB",self.indefn._gblb,debug=debug)

    # GBLC macro directive found
    def _GBLC(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"GBLC",self.indefn._gblc,debug=debug)

    # LCLA macro directive found
    def _LCLA(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"LCLA",self.indefn._lcla,debug=debug)

    # LCLB macro directive found
    def _LCLB(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"LCLB",self.indefn._lclb,debug=debug)

    # LCLC macro directive found
    def _LCLC(self,stmt,debug=False):
        self._define_LCLx_GBLx(stmt,"LCLC",self.indefn._lclc,debug=debug)

    # MACRO assembler directive found in macro definition
    def _MACRO(self,stmt,debug=False):
        raise assembler.AssemblerError(line=stmt.lineno,\
            msg="MACRO directive not allowed within a macro definition")

    # MEND macro directive - normal macro definition end
    def _MEND(self,stmt,debug=False):
        # Finish the macro engine definition by adding the Mend op
        self.indefn._mend(stmt.lineno,seq=self.__seq(stmt.fields))
        # Add the new macro to the definitions
        self.addMacro(self.indefn)

        self.indefn=None             # Leaving macro definition mode
        self.ddebug=False            # Turn off definition debug switch
        self.state=0                 # Change state to relfect this

    # MEXIT macro directive
    def _MEXIT(self,stmt,debug=False):
        self.indefn._mexit(stmt.lineno,seq=self.__seq(stmt.fields))

    # SETA macro directive
    def _SETA(self,stmt,debug=False):
        flds=stmt.fields
        lineno=stmt.lineno
        source=stmt.source
        
        # May raise an AssemblerError if name field is not a symbol reference
        setname=self.__set_name(stmt,"SETA")  # SymbolID object for variable being set
        #print("_SETA setname: %s" % setname)

        # Parse the operands.
        scope=self.parsers.parse_operands(stmt,"seta",required=True)
        if debug:
            print("_SETA: %s scope: %s" % (lineno,scope))

        expr=self.parsers.L2ArithExpr("_SETA",stmt,ltoks=scope.lextoks,debug=debug)
        if debug:
            print(expr)

        self.indefn._seta(lineno,setname,expr)

    def _SETB(self,stmt,debug=False):
        flds=stmt.fields
        lineno=stmt.lineno
        source=stmt.source
        
        # May raise an AssemblerError if name field is not a symbol reference
        setname=self.__set_name(stmt,"SETB")  # SymbolID object for variable being set

        # Parse the operands.
        scope=self.parsers.parse_operands(stmt,"setb",required=True)

        if debug:
            print("_SETB: %s scope: %s" % (lineno,scope))
        
        expr=self.parsers.L2BinaryExpr("_SETB",stmt,ltoks=scope.lextoks,debug=debug)

        self.indefn._setb(lineno,setname,expr)

    def _SETC(self,stmt,debug=False):
        lineno=stmt.lineno
        
        # May raise an AssemblerError if name field is not a symbol reference
        setname=self.__set_name(stmt,"SETC")  # SymbolID object for variable being set

        # Parse the operands.
        scope=self.parsers.parse_operands(stmt,"setc",required=True)
        
        if debug:
            print("_SETC: %s scope: %s" % (lineno,scope))

        charstr=scope.st_token.convert()  # String without quotes
        if debug:
            print("_SETC: %s charstr: %s" % (lineno,charstr))

        st_start=scope.st_start           # Lexical tokens of sub-string start
        if len(st_start)>0:
            start_expr=self.parsers.L2ArithExpr("SETC",stmt,ltoks=st_start,\
                debug=debug)
            end_expr=self.parsers.L2ArithExpr("SETC",stmt,ltoks=scope.st_len,\
                debug=debug)
        else:
            start_expr=end_expr=None

        self.indefn._setc(lineno,setname,charstr,start_expr,end_expr)

    # Defines symbol definitions in LCLx and GBLx macro directives
    # Exception:
    #   assembler.AssemblerError if parsing fails
    def _define_LCLx_GBLx(self,stmt,typ,dmethod,debug=False):
        flds=stmt.fields
        lineno=stmt.lineno
        source=stmt.source
        operands=flds.operands
        operpos=flds.operpos

        dscope=self.parsers.parse_operands(stmt,"symd",required=True)

        syms=dscope.symdefs
        case=self.case
        for n in range(len(syms)):
            sym=syms[n]
            #print(sym)
            sym.update(stmt,operpos,source=stmt.source)
            symid=sym.SymID(case)
            sub=symid.sub
            if sub is not None and isinstance(sub,SymbolID):
                raise assembler.AssemblerError(\
                    source=source,line=lineno,linepos=sym.subpos+1,\
                    msg="%s symbol definition subscript must be a decimal "
                    "self defining term: '%s'" % (typ,sub.var))
            # Only define the sequence name with the first definition
            if n==0:
                seq=self.__seq(stmt.fields)
            else:
                seq=None
            dmethod(lineno,symid,seq=seq)
        return

    def addMacro(self,mac):
        assert isinstance(mac,Macro),\
            "%s 'mac' argument must be a Macro object: %s" \
                % (assembler.eloc(self,"addMacro",module=this_module),mac)

        self.macros[mac.name]=mac

    # Returnt the current expander
    def currentInvoker(self):
        return self.expanders[-1]

    # Initiate a new macro definition
    def define(self,debug=False):
        self.ddebug=debug    # Set the define debug switch from MACRO directive
        self.state=1         # We now expect a prototype statement

    # Hook used by the Assembler Language to process macro definition statements
    def defining(self,stmt,debug=False):
        ddebug=self.ddebug or debug
        # If not defining a macro, simply return with a value of False.
        if __debug__:
            if ddebug:
                cls_str=assembler.eloc(self,"defining",module=this_module)
                print("%s macro state: %s" \
                    % (cls_str,self.state))
        state=self.state
        if state==0:
            return False

        # Within a macro definition so we now process statement fields for a macro
        # This is essentially the same as assembler.__classifier()
        #flds=assembler.StmtFields()
        #flds.parse(self.asm,stmt,debug=ddebug)
        #stmt.classified()
        flds=stmt.fields

        # This is the same as assembler.__continuation()
        # Needs to be updated for alternate continuation conventions.
        try:
            flds.normal(stmt.line)
        except asmcards.LineError as le:
            raise AssmeblerError(source=le.source,line=stmt.lineno,msg=le.msg) \
                from None
        stmt.continuation()

        if __debug__:
            if ddebug:
                print("%s %s" % (cls_str,flds))

        stmt.fields=flds
        
        # Looking for prototype statmenet
        if state==1:
            if flds.comment:
                self.state=3
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="comment not allowed for prototype statement")
            op=flds.opuc

            if __debug__:
                if ddebug:
                    print("%s state -> %s operation: '%s'" % (cls_str,state,op))

            # prototype statement may not contain a macro directive
            if op=="MEND":
                self.state=0         # Leave macro definition mode
                raise assembler.AssemblerError(line=stmt.lineno,linepos=flds.oppos,\
                    msg="empty macro definition ignored")
            try:
                mdir=self.directives[op]
                self.state=3
                raise assembler.AssemblerError(line=stmt.lineno,linepos=flds.oppos,\
                    msg="macro definition suppressed - expected macro prototype "
                        "statement but found: %s" % flds.operation)
            except KeyError:
                pass

            # Prototype statement found
            try:
                self._prototype(stmt,debug=debug)
            except assembler.AssemblerError as ae:
                self.state=3         # Ignore rest of macro definition
                raise ae from None
            self.state=2
            
        # Processing body statements (macro diretives and model statements)
        elif state==2:
            op=flds.opuc
            try:
                self._body(stmt,debug=ddebug)
            except assembler.AssemblerError as ae:
                if op=="MEND":
                    self.state=0  # Macro definition ended due to error
                else:
                    self.state=3  # Flush until we find the MEND
                raise ae from None
            # Remain in state 2 as long as no errors found in body

        # Bad macro is being suppressed
        elif state==3:
            if flds.comment:
                if __debug__:
                    if ddebug:
                        print("%s state -> %s comment" % (cls_str,state))

            else:
                op=flds.opuc
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
                    raise assembler.AssemblerError(line=stmt.lineno,\
                        linepos=flds.oppos,msg=ae_msg)

        # Do not recognize state, so something is messed up, bailing....
        else:
            raise ValueError("%s MacroLanguage.state invalid: %s" \
                % (assembler.eloc(self,"defining",module=this_module),state))
            
        # Tell caller we processed the statement here.
        return True

    # Find the Macro object associated with a macro
    # Exceptions:
    #    KeyError if macro name not registered
    def find(self,macname):
        return self.macros[macname]

    # Causes the remaining statements of a macro to be ignored through the
    # next MEND statement.
    def flush(self):
        self.state=3

    # Return a list of the built-in macro names
    def getBuiltIns(self):
        lst=[]
        for x in self.macros.values():
            if isinstance(x,Built_In):
                lst.append(x.name)
        return lst

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
        if not isinstance(stmt,assembler.Stmt):
            cls_str=assembler.eloc(self,"macstmt")
            raise ValueError("%s 'stmt' argument must be a Stmt object: %s" \
                % (cls_str,stmt))
        macro=stmt.macro
        if not isinstance(macro,Macro):
            cls_str=assembler.eloc(self,"macstmt")
            raise ValueError("%s 'stmt.macro' must be a Macro object: %s" \
                % (cls_str,macro))
            
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
        exp.invoke(stmt)        # Initialize the macro expander
        return exp

    # Updates the MHELP values.  Called by assembler.Assembler._spp_mhelp() method
    def mhelp(self,value,debug=False):
        val=value & 0xFFFFFFFF
        self.max_sysndx=val & 0xFFFFFF00   # maximum &SYSNDX value being detected
        self.max_sysmon=val & 0x0000FF00   # &SYSNDX value being monitored
        self.mhelp_mask=val & 0x000000FF   # MHELP action mask
        self.mhelp_sup =val & 0x00000080   # If bit set, suppressing actions
        if debug:
            cls_str=assembler.eloc(self,"mhelp",module=this_module)
            print("%s max_sysndx=%s" % (cls_str,self.max_sysndx))
            print("%s max_sysmon=%s" % (cls_str,self.max_sysmon))
            print("%s mhelp_mask=%s" % (cls_str,bin(self.mhelp_mask)))
            print("%s mhelp_sup =%s" % (cls_str,self.mhelp_sup))

    # Incrments and returns the new nesting level
    def nest(self,exp):
        if not isinstance(exp,Invoker):
            cls_str=assembler.eloc(self,"nest")
            raise ValueError("%s 'exp' argument must be an Invoker object: %s" \
                % (cls_str,exp))
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
            cls_str=assembler.eloc(self,"unnest",module=this_module)
            raise ValueError("%s can not unnest expander, nesting level empty" \
                % cls_str)
        del self.expanders[-1]
        self._nest=len(self.expanders)
        if self._nest==0:
            self.cur_exp=None


#
#  +---------------------+
#  |                     |
#  |   Built-in Macros   |
#  |                     | 
#  +---------------------+
#

class Test(Built_In):
    def __init__(self,case):
        pos=["&pparm",]
        keywords={"&kparm":"dflt"}
        proto=Prototype("test",lblsym="&LBL",positionals=pos,keywords=keywords)
        super().__init__(proto,case)

    def define(self):
        eng=self.engine
        eng.define(Model(None,"&LBL     DC F'0'"))
        eng.define(MEND(None))


if __name__ == "__main__":
    raise NotImplementedError("asmmacs.py - intended for import use only")
        