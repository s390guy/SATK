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

# This Python script provides a generic Finite State Machine class: FSM.  
#
# The FSM is built from:
#   FSM      - the actual Finite State Machine
#   FSMState - Defines the actions to be performed when the state is current. 
#              Actions are callable functions or methods.  The action is defined
#              by using the FSMState.action() method.  Each state is registered 
#              with the FSM by use of the FSM.state() method.
#
# Finally, the FSM.init(state) method identifies the initial state of the FSM.
#
# Once the FSM has been built the following steps are required:
#
# FSM.start()        - Set the FSM to the initial state
#
# Repeatedly call until it returns a value of False:
# FSM.machine(value) - Run a cycle of the FSM.  This performs the action identified
#                      for input 'value' of the current state of the machine.
# 
# The design allows for the following construct to be used:
#
#      running=True
#      input=<specify the first input value>
#      while running:
#          running=FSM.machine(input)
#          input=<next input value>
#
# The FSM may be reused after it terminates by re-issuing the FSM.start() method.

#
# Additional lexical assists are provided by the FSMLex subclass.  These assists
# are intended for use with the FSMToken and FSMTType classes.  See the FSMLex
# class below.
#
# An example of the use of the classes provided by fsm.py in conjunction with a 
# line_parser.py parser can be found in orders.py.

# Python imports: None

# SATK imports: lexer
import lexer   # Need to access the lexer

this_module="fsm.py"

# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exceptin string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)

# Defines a Finite State Machine
# Instance arguments:
#   name      Specify a name for the FSM.  By default the name will be the FSM's
#             class name.  The name is used in various run-time messages.
#   trace     Specify True to enable state action tracing.  Defaults to False. 
# Instance methods:
#   current   Returns the current state of the FSM
#   init      Specify the starting state of the FSM. Use start() to set the state.
#   machine   Run a single cycle of the finite state machine.
#   scope     Returns the current global scope object or None
#   start     Ready the finite state machine for use by setting the start state.
#   trace     Enable (True) or disable (False) state action tracing.
# Note: This FSM understands lexer.Token objects as inputs and lexer.Type objects
# as defining input to a state.  The FSMParser object wraps this object with an
# interface to the lexical analyzer.
class FSM(object):
    def __init__(self,name=None,trace=False):
        if name is None:
            self.name=self.__class__.__name__
        else:
            self.name=name
        self._start=None       # Start state name
        self._current=None     # Current state name
        self._states={}        # Dictionary of supported states
        self.trace(trace)      # Initialize tracing
        #
        # FSM processing state initialized by the start() method
        self._started=False    # When started, True
        self._terminated=True  # When started, False
        self._scope=None       # Global scope shared with processing states
        # In single context fsmparser.FSMParser objects, this is the global scope
        # In multi-context fsmparser.FSMContext objects, this is the active scope

    # Return the current state of the FSM
    def current(self):
        return self._current
    
    # Generate a trace from a subclass
    def do_trace(self,state,method,text,trace):
        print("FSM:%s [%s] %s() %s" % (trace,state.state,method,text))

    # Define the initial state of the FSM by its defined string
    # The state must already have been defined by a call to FSM.state()
    def init(self,state):
        self._start=state

    # Run a _single_ cycle of the FSM.
    # Arguments:
    #   value  A value presented to the current state for action.  Any value
    #          registered with the state may be used, including an FSMToken
    #          instance.
    # Returns: 
    #   False when the machine terminates, True otherwise.  The caller should test
    #   the return to determine if the machine has ended.
    def machine(self,value):
        assert self._started,"%s FSM not started" % eloc(self,"machine")
        assert not self._terminated,"%s FSM terminated" % eloc(self,"machine")

        if __debug__:
            if self._trace:
                print("FSM:%s machine input: %s" % (self.__class__.__name__,value))

        # Fetch the next state and set it as current
        try:
            current=self._states[self._current]
        except KeyError:
            raise ValueError("%s current state undefined: '%s'" \
                % (eloc(self,"machine"),self._current))

        # Run the current state:
        self._current=current.input(value,trace=self._trace)

        self._terminated=current.isend()
        if self._terminated:
            if __debug__:
                if self._trace is not None:
                    print("FSM:%s terminated" % self.name)
            self._started=False
            self._current=None
        else:
            assert self._current is not None,\
                "%s action method for input %s for state '%s'returned None as the "\
                    "next state" % (eloc(self,"machine"),value,current.state)
        return self._terminated 

    # Method returns the global scope object for processing actions.
    # A state should be defined with fsm=True if this method is intended to be used.
    def scope(self):
        return self._scope

    # Initialize the FSM by setting the current state to the start state
    # Method Arguments:
    #   scope   A global scope object shared among the processing states.  Defaults
    #           to None.
    def start(self,scope=None):
        self._current=self._start
        self._started=True
        self._terminated=False
        self._scope=scope
        if __debug__:
            if self._trace is not None:
                print("FSM:%s [%s] initial state set" % (self.name,self._current))

    # Define a state (as represented by an FSMState instance) to the FSM
    def state(self,state):
        assert isinstance(state,FSMState),\
            "%s requires FSMState instance, encountered: %s" \
                % (eloc(self,"state"),state)

        s=state.state
        if state.fsm not in [True,False]:
            if isinstance(state.fsm,FSM):
                other=state.fsm.name
            else:
                other="unknown"
            raise ValueError("%s state '%s' already registered with another FSM: %s" \
                % (eloc(self,"state"),s,other))

        # If requested, link the FSM (myself) to the state object
        if state.fsm:
            state.fsm=self

        try:
            self._states[s]
            raise ValueError("%s duplicate state encountered: '%s'" \
                % (eloc(self,"state"),s))
        except KeyError:
            self._states[s]=state

    # Enable or disable FSM state tracing
    def trace(self,on=False):
        if on:
            self._trace=self.name
        else:
            self._trace=None

# The class defines a state within the FSM and its actions upon receiving
# specific inputs.
# Instance arguments:
#   state   a required name for the state.
#   end     Specify 'True' if the FSM is to terminated upon finishing this states
#           action.  Specify 'False' if the FSM it to continue to the next state
#           returned by the action callable.  Defaults to 'False'
#           Note: this behavior may be overriden in a subclass by overriding the
#           FSMState.atend() method.  The overriding method must return 'True' or 
#           'False'.
#   fsm     If True, the FSM object will set itself to the state's 'fsm' attribute.
#           If False, the FSM object leaves the 'fsm' attribute set to False.
#           Defaults to False.
# Instance methods:
#   ActID   The method converts an input to an internal ID associated with the
#           input.  This method is intended primarily for subclass override.
#   action  Defines an action for a specific input or input token type.  Action
#           methods or functions must be defined at least with the following
#           signature:   
#               callable_name(value,state)
#           and return the next state of the finite state machine.
#   atend   Dynamically indicate the FSM should end after this state
#   error   Define an action for any unrecognized input.  If no actions are 
#           defined by the FSMState.action() method, the method specified by
#           FSMState.error() becomes the default action for the state.  If this
#           method is not used, unrecognized input will raise a TypeError
#           exception.
#   input   Perform the defined action for a specific input
#   isend   Inform the FSM if it is terminated at the completion of this action.
class FSMState(object):
    def __init__(self,state,end=False,fsm=False):
        self.state=state     # Name of the state as a string
        self._actions={}     # Actions to be performed depending upon input token
        self._error=None     # Method used to process unrecognized tokens
        self._end=end        # If True, ending this state will terminate the FSM
        self._force=False    # When True, the state will end after this action
        
        # Subclass related attributes.  Not used by the base FSM
        # Indicates to the FSM that this state wants access to the FSM object
        # If True, the FSM object sets this attribute to itself upon registering
        # with the state with the FSM with its FSM.state() method.
        self.fsm=fsm

    def __str__(self):
        return "%s('%s',end=%s)" % (self.__class__.__name__,self.state,self._end)

    # The State object must identify its required action via the input to the state.
    # By default the input value is used.  To extract or identify a different value 
    # from the input, override this method.
    # Method Arguments:
    #   value   Value being defined or an input value to this state.
    #   reg     If True, the value is being registered with an action method
    #           If False, the value is being used as input to this state.
    # The 'reg' argument allows the method to recognize whether a value is being
    # register or is input and to use different behaviors, if needed.
    # Returns:
    #   the action ID used to determine the method associated with the action.  By
    #   default the input value is simply returned in both cases.
    def ActID(self,value,reg=False):
        return value

    # Defines an action in the form of a methoc for a given input or list of inputs.
    # Method Arguments:
    #   ids     A single input or list of inputs.
    #   method  Specifies the method to be called with the input.
    # Note: method ActionID() is used to translate each submitted input into its
    # internal ID.  The internal ID is used to identify the action associated with
    # the input.
    def action(self,ids,method):
        if not isinstance(ids,list):
            t=[ids,]
        else:
            t=ids
        for inid in t:
            intyp=self.ActID(inid,reg=True)
            try:
                self._actions[intyp]
                raise ValueError("%s duplicate type encountered: %s" \
                    % (eloc(self,"action"),intyp))
            except KeyError:
                self._actions[intyp]=method

    def atend(self):
        self._force=True

    # Define the method for handling an unrecognized input.  It must return the 
    # next state name.
    def error(self,method):
        self._error=method

    # Process an input when in this state.
    def input(self,value,trace=None):
        tk=self.ActID(value)
        try:
            method=self._actions[tk]
        except KeyError:
            if self._error is None:
                raise TypeError("%s: No action method defined by state '%s' for input "
                    "value: %s" % (eloc(self,"input"),self.state,tk)) from None
            method=self._error

        if __debug__:
            if trace is not None:
                print("FSM:%s [%s] action called for input: %s" \
                    % (trace,self.state,tk))
                print("FSM:%s [%s] calling self.%s(%s,self,trace=%s)" \
                    % (trace,self.state,method.__name__,value,trace))

        next=method(value,self,trace=trace)

        if __debug__:
            if trace is not None:
                print("FSM:%s [%s] action for input '%s' returned next state: %s" \
                    % (trace,self.state,tk,next))

        return next

    # This method may be overridden if a subclass wants to modify the end state
    # detection from the default.  By default if either the state was initialized
    # as an ending state, FSMState(end=True), or an action triggers ending by
    # calling FSMState.atend(), the FSM will terminate.
    #
    # In the case when FSMState.atend(), the state will reset to returning False
    # on successive uses of the FSM.
    #
    # Returns:
    #  True    - signals the FSM that it has reached the end state
    #  False   - signals the FSM that it has _not_ reached the end state
    def isend(self):
        value=False
        if self._force or self._end:
            value=True
        self._force=False
        return value

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
