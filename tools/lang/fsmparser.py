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

# This module utilizes a finite state machine in conjunction with the lexer.py module
# to implement a parser.  It is built from the basic finite state machine support
# provide by the fsm.py module.

# Python imports: None
# SATK imports:
import fsm        # Access the generic finite state machine.
import lexer      # Access the lexical analyzer.

this_module="fsmparser.py"

# This FSM provides parsing services based upon the SATK single context lexical
# analyzer.
#
# Instance Arguments:
#   lex        Lexical analyzer used for parsing.
#   scls       Scope class used for accumulating parse information.  Defaults to None.
#   external   External object providing assistance.  Defaults to None.
#   init       Specify the initial FSMState instance name of the FSM.  
#              Defaults to 'init'.
#   trace      Enable (True) or disable (False) tracing of state actions.  Defaults to 
#              False.
# Instance methods:
#   parse      Parse a string using the lexical analyzer
#   stack      Allows a previously processed token to be placed on a LIFO stack
#   unstack    Removes a previously processed token from the LIFO stack
class FSMParser(fsm.FSM):
    def __init__(self,lex,scls=None,external=None,init="init",trace=False):
        super().__init__(trace=trace)
        assert isinstance(lex,(lexer.Lexer,lexer.CSLA)),\
            "%s - %s.__init__() - 'lex' argument must be an instance of lexer.Lexer "\
            "or lexer.CSLA: %s" % (this_module,self.__class__.__name__,lex)

        self.lex=lex              # Lexical analyzer used for parsing
        self.scopecls=scls        # Class to create for my scope
        self.external=external    # External assistance object
        self._stack=[]            # A holding place for potential look aheads
        self._unstacked=None      # Queued token from stack for input to FSM

        self.init(init)  # Establish FSM start state

    def _init_scope(self,scope=None):
        if self.scopecls is not None:
            scop=self.scopecls()
            scop.init()
        else:
            scop=scope   # If not defined with the parser, use the one supplied here.
        return scop

    # Uses the FSM to recognize a string converting it into lexical tokens.
    # Returns the global scope object constructed during the parse.
    def parse(self,string,context=None,scope=None,fail=False,lines=False,line=1):
        # Note: argument context is not used by the FSMParser
        self.start(scope=self._init_scope(scope=scope))
        done=False
        for token in self.lex.analyze(string,pos=0,fail=fail,lines=lines,line=line):
            while self._unstacked is not None:
                inp=self._unstacked
                self._unstacked=None
                done=self.machine(inp)
                if done:
                    break
            if not done:
                done=self.machine(token)
        return self.scope()

    # Saves a previously presented token on a pushdown stack
    def stack(self,token,trace=None):
        if trace is not None:
            print("FSM:%s input token stacked: %s" % (trace,token))  
        self._stack.append(token)

    # Overrides to super class
    def start(self,scope=None):
        super().start(scope=scope)
        self._stack=[]

    # Terminates the lexer so that next use of lexical analyzer has nothing
    # sticking around from this use of it.
    def stop(self):
        self.lex.stop()

    # Queues a token from the pushdown stack for input to the FSM
    def unstack(self,trace=None):
        if len(self._stack)==0:
            cls_str="%s - %s.unstack():" % (this_module,self.__class__.__name__)
            raise ValueError("%s stack is empty" % cls_str)
        if self._unstacked is not None:
            cls_str="%s - %s.unstack():" % (this_module,self.__class__.__name__)
            raise ValueError("%s ustacked token already queued for machine" % cls_str)
        self._unstacked=self._stack.pop(-1)
        if trace is not None:
            print("FSM:%s token unstacked: %s" % (trace,token))
        return

# Define an individual context for the parser
# Instance Arguments:
#   name   Supplies a name for use by the Parser of the context.
#   lexctx Identifies the context sensitive lexical analyzer context used for
#          recognition.  Defaults to the same name as the parser context if not
#          supplied.
#   ccls   A context scope object created for the new scope
class Context(object):
    def __init__(self,name,lexctx=None,ccls=None):
        self.name=name
        if lexctx:
            self.lexctx=lexctx
        else:
            self.lexctx=name
        if ccls:
            self.ccls=ccls
        else:
            self.ccls=PScope


# This FSM provides parsing services based upon the SATK multiple context lexical
# analyzer.
#
# Instance Arguments:
#   lex        Context Sensitive Lexical analyzer used for parsing.
#   scls       Global scope class used for accumulating parse information.
#              Defaults to None.  If None, a scope object is required when
#              calling the parse() method.
#   external   External object providing assistance.  Defaults to None.
#   init       Specify the initial FSMState instance name of the FSM.  
#              Defaults to 'init'.
#   trace      Enable (True) or disable (False) tracing of state actions.  Defaults to 
#              False.
#
# Instance Methods:
#   context    Set a new context for continued parsing
#   csparse    Perform a context sensitive parse on a string
class FSMContext(FSMParser):
    def __init__(self,lex,scls=None,external=None,init="init",context="init",\
                 trace=False):
        self.ctxs={}           # Dictionary of Context objects.
        self.ctx_scope=None    # Current ctx_scope active
        self.ctx_name=None     # The name of the current ctx_scope 
        self.init_ctx=context  # The initial context
        super().__init__(lex,scls=scls,external=external,init=init,trace=trace)

    def __init_cscope(self,ctx,scope=None):
        if scope:
            return scope
        cscope=ctx.ccls()
        cscope.init()
        return cscope

    # Define a parser context from a Context object.
    # See the description of the Context objects arguments for details.
    def ctx(self,name,lexctx=None,ccls=None):
        ctxo=Context(name,lexctx=lexctx,ccls=ccls)
        try:
            self.ctxs[ctxo.name]
            cls_str="%s - %s.ctx() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s Context object already defined: %s" \
                % (cls_str,ctxo.name))
        except KeyError:
            pass
        self.ctxs[ctxo.name]=ctxo   

    # Set a new context in the lexer
    # Method Arguments:
    #   name   The name of the new parser context being established
    #   gscope The global scope object that will contain the context scope
    #   scope  The scope object to be used by the context.  If None is supplied
    #          the scope class identified by the scope object will be created
    def context(self,name,gscope=None,scope=None):
        try:
            ctx=self.ctxs[name]
        except KeyError:
            cls_str="%s - %s.context() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s can not switch to an undefined parser context: %s" \
                % (cls_str,name)) from None
        if gscope:
            gs=gscope
        else:
            gs=self.scope()
        gs.cscope=self.__init_cscope(ctx,scope)
        self.lex.context(ctx.lexctx)   # Set the lexer context here too
        self.ctx_name=name             # Remember the parser context too

    # Returns the active context scope object
    def cscope(self):
        return self.scope().cscope

    # Perform a context sensitive parse
    # Method Arguments:
    #   string   The string being recognized
    #   context  The name of the initial context.  Defaults to __init__ context
    #   scope    The global scope object to be used.  Defaults to None.
    #   line     The line number of the line being parsed
    # Exceptions
    #   LexerError if current context does not match any token types
    def parse(self,string,context=None,scope=None,fail=False,lines=False,line=1):
        # Note: arguments fail and lines are not used by the FSMContext parser
        gscope=self._init_scope(scope=scope)
        if context:
            ctx=context
        else:
            ctx=self.init_ctx
        # Set initial parser context and initial CSLA context
        self.context(ctx,gscope=gscope,scope=scope)
        # Pass the string to be parsed to the lexical analyzer
        self.lex.start(string)     # Tell the lexer what to recognize
        # Initialize the FSM initial state and the global scope object
        self.start(scope=gscope)   # Start the FSM with global scope

        # Perform the parse by pulling tokens from the lexical analyzer until
        # the FSM is done.
        while True:
            token=self.lex.recognize(line=line)  # May raise LexerError
            done=self.machine(token)
            if done:
                break

        # Return the global scope object when done
        return self.scope()

    def stack(self,token,trace=None):
        cls_str="%s - %s.stack():" % (this_module,self.__class__.__name__)
        raise NotImplementedError("%s stack() method not supported" % cls_str)
        
    def unstack(self,trace=None):
        cls_str="%s - %s.unstack():" % (this_module,self.__class__.__name__)
        raise NotImplementedError("%s unstack() method not supported" % cls_str)


# This class facilitates the management of scope within the FSM.  It  is recommended
# that this class or a subclass be used at least to manage global  FSM processing scope.
# This ensures the separation of FSM processor global name space from the FSM
# class and its states.
#
# The base class simply provides an alternative attribute name space.  A subclass
# may add language specific methods and an init() method for initialization.
class PScope(object):
    def __init__(self):
        self.cscope=None
        self.init()        # Initialize myself

    # Optional initialization method.  If used, the subclass must provide it.
    def init(self): pass

class PState(fsm.FSMState):
    def __init__(self,name,end=False):
        super().__init__(name,end=end,fsm=True)

    # Must match the method signature of FSMState.ActID() method.
    def ActID(self,value,reg=False):
        if reg:
            if not isinstance(value,(lexer.Type,lexer.Unrecognized)):
                cls_str="%s - %s.ActID() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s 'value' argument must be an instance of "
                    "lexer.Type: %s" % (cls_str,value))
        else:
            if not isinstance(value,lexer.Token):
                cls_str="%s - %s.ActID() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s 'value' argument must be an instance of "
                    "lexer.Token: %s" % (cls_str,value))
        return value.tid

    # Returns the the current context scope
    def cscope(self):
        return self.fsm.scope().cscope

    # Returns the global PScope object of the parser.
    def scope(self):
        return self.fsm.scope()

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)