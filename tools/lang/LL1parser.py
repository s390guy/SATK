#!/usr/bin/python3.3
# Copyright (C) 2013 Harold Grovesteen
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

# This module is intended to be imported for use by other modules for the purpose
# of creating a LL(1) recursive descent parser utilized in a language processor.
# Refer to the document "SATK for s390 - Language Processing Tools" in the SATK
# doc directory for a description of this module's usage.

# Python imports:
import functools  # Access to compare function to key function

# SATK imports:
import lexer
import LL1grammar         # Access the LL(1) grammar processor
from satkutil import DM   # Access the generic debug manager

# +-----------------------+
# |  Callback Management  |
# +-----------------------+

# The Callback Manager class assists in registering callback methods by a 
# language processor and in the identification of a callback for a specific 
# point in the processing.  The CBM class mangages the processing points.  The
# CB class manages individual callbacks for specific id's.
#
# Class instance arguments: None
#
# Instance methods:
#   method     Returns the callback method for a specific processing point and id
#   point      Register a CB instance for managing callbacks of a processing point.
#              callback id's must be unique.
#   register   Register a method with a specific processing point and id.
class CBM(object):
    @staticmethod
    def mname(mo):         # Returns the method name string: 'class.method'
        if mo is None:
            return "None"
        io=mo.__self__     # Get the instance object from the method object 
        cls=io.__class__   # Get the class object from the instance object
        fo=mo.__func__     # Get the function object from the method object
        return "%s.%s" % (cls.__name__,fo.__name__)

    def __init__(self):
        # Dictionary of callback processing points.  Contains CB instances.
        self.cbp={}

    # Returns the callback method for a specific processing point and callback id.
    # If the processing point or callback method is not recognized (or a default
    # callback method was not specified), a ValueError is raised.
    def method(self,point,cbid):
        try:
            p=self.cbp[point]
        except KeyError:
            raise ValueError("parser.py - CBM.method() - unrecognized callback "
                "processing point: %s' % point")
        return p.method(cbid)  # Fetch the callback method for the id.

    # Register a CB instance for a callback processing point
    def point(self,cbo):
        if not isinstance(cbo,CB):
            raise ValueError("parser.py - CBM.point() - process point must be "
                "a instance of class CB: %s" % point)
        ppoint=cbo.point   # Fetch the processing point of the CB instance
        try:
            
            p=self.cbp[ppoint]
            raise ValueError("parser.py - CBM.point() - duplicate processing "
                "point encountered: %s" % ppoint)
        except KeyError:
            self.cbp[ppoint]=cbo   # Register the CB instance for the point
            
    # Register a specific method for a processing point and callback id.
    def register(self,point,cbid,method):
        try:
            p=self.cbp[point]
        except KeyError:
            raise ValueError("parser.py - CBM.register() - Unrecognized "
                "processing point: %s" % point)
        #print("p=%s" % p)
        p.register(cbid,method)
    
# This class handles the all of the callbacks for an individual processing point.
# A default can be established when the class is created or later registered.
class CB(object):
    def __init__(self,point,default=None):
        if not isinstance(point,str):
            raise ValueError("parser.py - CB.__init__() - processing point id "
                "must be a string: %s" % point)
        self.point=point   # Save the processing point
        self.dft=default   # set the default method
        self.cbs={}        # The empty dictionary of cbid's to method mapping

    # Specify a default or new default method for the processing point
    def default(self,method):
        self.dft=method

    # Return a method for a specific callback id or the default if no method has
    # been registered.  If no default method exists, a ValueError exception is
    # raised
    def method(self,cbid):
        try:
            m=self.cbs[cbid]
            return m
        except KeyError:
            pass
        if self.dft is None:
            raise ValueError("parser.py - CB.method() - unrecognized callback "
                "id and no default specified: '%s'" % cbid)
        return self.dft

    # Register a method for a specific callback id.
    def register(self,cbid,method):
        if not isinstance(cbid,str):
            raise ValueError("parser.py - CB.register() - callback id must be a "
                "string: %s" % cbid)
        self.cbs[cbid]=method

# +-------------------------------+
# |  Exceptions Raised by Parser  |
# +-------------------------------+

# This exception is raised any time the Parser encounters an error.
# Instance arguments:
#   tok      The token triggering the error.  Default is None.
#   msg      A message associated with the error.  Default is "".
class ParserError(Exception):
    def __init__(self,tok=None,msg=""):
        self.tok=tok         # The token in error
        self.msg=msg         # Error message
        super().__init__(self.msg)

# This exception is raised when syntactical analysis detects an error
class SyntaxError(Exception):
    def __init__(self,eo=None):
        super().__init__()
        self.eo=eo  # Associated error object
        
# This exception is raised when the empty string is accepted
class Empty(Exception):
    def __init__(self):
        super().__init__()

# +------------------------+
# |  Parser Error Objects  |
# +------------------------+

# These classes categorize encountered errors and passed in SyntaxErrors and
# ultimately communicated to the language processor for eventual processing.
class Error(object):
    @staticmethod
    def compare(a,b):
        if a.line is None and b.line is None:
            return 0
        if a.line is None:
            return -1
        if b.line is None:
            return 1
        if a.line<b.line:
            return -1
        if a.line>b.line:
            return 1
        # lines are equal so check out position within the line
        if a.pos<b.pos:
            return -1
        if a.pos>b.pos:
            return 1
        # lines and position are equal, check the the parse depth (in reverse)
        if a.depth>b.depth:
            return 1
        if a.depth>b.depth:
            return -1
        return 0
    def __init__(self,line=None,pos=None,depth=0,source="UNKNOWN"):
        self.line=line
        self.pos=pos
        self.depth=depth
        self.source=source
        self.reported=False    # Set to True by ErrorMgr when reported
    def loc(self,depth=False):
        if self.line is None:
            ln=""
        if self.line is None and self.pos is None:
            return ""
        if depth:
            return "[%s:%s]-%s " % (self.line,self.pos,self.depth)
        else:
            return "[%s:%s] " % (self.line,self.pos)
    def print(self,*args,**kwds):
        raise NotImplementedError("lang.Error.print() - subclass %s must implement "
            "method print()" % self.__class__.__name__)
class ErrorProd(Error):
    def __init__(self,pid,n,depth=0,token=None,source="UNKNOWN"):
        self.pid=pid
        self.n=n
        self.token=token
        if token is None:
            super().__init__(line=None,pos=None,depth=depth,source=source)
        else:
            super().__init__(line=token.line,pos=token.linepos,\
                depth=depth,source=source)
    def __str__(self):
        return "ErrorProd(pid=%s,n=%s,depth=%s,token=%s,source=%s" \
            % (self.pid,self.n,self.depth,self.token,self.source)
    def print(self,debug=False):
        if self.n is None or self.n==0:
            n=""
        else:
            n="for alternative %s" % self.n
        if self.token is None:
            string=""
        else:
            string=" encountered: '%s'" % self.token.string
        if debug:
            src=" %s()" % self.source
        else:
            src=""
        print("P%s'%s' error %s%s%s" \
            % (self.loc(depth=True),self.pid,n,string,src))
        
class ErrorResync(Error):
    def __init__(self,pid,n,depth,rtoken,source="UNKNOWN"):
        self.pid=pid
        self.n=n
        self.rtoken=rtoken
        super().__init__(line=rtoken.line,pos=rtoken.linepos,depth=depth,\
            source=source)
    def print(self,debug=False):
        print("S%s following %s[%s] error, input stream continues with token "
            "type '%s'" \
            % (self.loc(depth=True),self.pid,self.n,self.rtoken.tid))
        
class ErrorStream(Error):
    def __init__(self,pid,depth,token,source="UNKNOWN"):
        self.pid=pid
        self.token=token
        super().__init__(line=token.line,pos=token.linepos,depth=depth,\
            source=source)
    def print(self,debug=False):
        print("S%s'%s' input stream processing incomplete: '%s'" \
            % (self.loc(depth=True),self.pid,self.token.string))
   
class ErrorToken(Error):
    def __init__(self,pid,n,depth,expect,found,source="UNKNOWN"):
        self.pid=pid
        self.n=n
        self.expect=expect
        self.token=found
        super().__init__(line=found.line,pos=found.linepos,\
            depth=depth,source=source)
    def __str__(self):
        return "ErrorToken(pid=%s,n=%s,expect=%s,found=%s,source=%s)" \
            % (self.pid,self.n,self.expect,self.token,self.source)
    def clone(self):
        return ErrorToken(self.pid,self.n,self.expect,self.token)
    def print(self,debug=False):
        if self.n is None or self.n==0:
            n=""
        else:
            n=" for alternative %s" % self.n
        if debug:
            src=" %s()" % self.source
        else:
            src=""
        print("T%s'%s'%s expected %s, found: '%s'%s" \
            % (self.loc(depth=True),self.pid,n,self.expect,self.token.string,src))

class ErrorUnrecognized(Error):
    def __init__(self,token,depth=0):
        self.token=token
        super().__init__(line=token.line,pos=token.linepos,\
            depth=depth,source="LEXER")
    def print(self,debug=False):
        if debug:
            src=" %s" % self.source
        else:
            src=""
        print("U%sunrecognized text ignored: '%s'%s" \
            % (self.loc(),self.token.string,src))

# This class is intended to help a language processor to manage error reporting
# Instances of class Error are presented to it.  The ErrorManager will sort errors
# into text sequence for reporting.
class ErrorMgr(object):
    @staticmethod
    def comp_errors(a,b):
        return Error.compare(a,b)
    def __init__(self):
        self.errors=[]   # List of encountered errors with text locations
        self.noloc=[]    # List of encountered errors without text locations

    # This method returns the number of reported errors.
    def quantity(self):
        return len(self.errors)+len(self.noloc)

    # This method is called when an error object is to be reported as an error.
    def report(self,error):
        if not isinstance(error,Error):
            raise TypeError("lang.ErrorMgr.report() - error must be an instance of "
                "Error, encountered: %s" % error)
            
        # Only report the same error once.  It may be presented multiple times by
        # the parser.
        if error.reported:
                return
        error.reported=True
        
        # Add the error to one of the lists of reported errors.
        if error.line is None or error.pos is None:
            self.noloc.append(error)
        else:
            self.errors.append(error)

    # This method presents a list of errors for processing.
    def present(self):
        self.errors.sort(key=functools.cmp_to_key(ErrorMgr.comp_errors))
        lst=self.errors
        lst.extend(self.noloc)
        return lst

# The Parser class creates a recursive descent parser with retries and parser
# sychronization for failed productions.  The Parser class may be subclassed.
#
# Instance methods:
#   cbreg     Allows a language processor to register a callback method for a 
#             specific production id and its processing point.
#   debug     Sets a registered debug flag as True or False.  Unrecognized flags
#             raise ValueError exceptions.
#   flag      Registers a unique debug flag testable by the isdebug() method and
#             able to be set by the debug() method.  Although these flags are
#             used by the parser for enabling and disabling debug switches, they
#             may in fact be used by for any purpose by a subclass.
#   generate  Initialize the parser from a grammar, lexer and start production
#             It uses the setup() method to complete the parser.
#   isdebug   Returns a registered debug flags state, True or False.
#   lexer     This method identifies for the parser the specific lexer it will use
#             to create the input token stream.
#   parse     This method parses and processes a string in the target language.
#   setup     Initialize the parser from a dictionary of PRD instances, lexer and
#             start symbol.
#
# Instance methods providing information about the parser.
#   grammar   Prints with line numbers the input grammar.  The grammar text is not
#             available until the generate() method has been called.
#   productions  Prints the production dictionary.
#   source    Prints with line numbers the input text.  Source is not available
#             until the parse() method has been called
#   tokens    Prints a list of the tokens parsed by parser, post filtering.  Stream
#             index is provided for each token.  Tokens are not available until
#             the parse() method is called.
#
# Instance methods supplied by subclasses:
#   filter    Filters lexical recognized Tokens before presented to parser for
#             processing.  Returns either the Token or None.
#   init      This method must be supplied by a subclass if used.  It is intended to
#             to initialize a specific Parser with its lexer and productions.
class Parser(object):
    def __init__(self,dm=None):
        if dm is None:
            self.dm=DM(parser=True)
        else:
            self.dm=dm

        # These attributes are used to establish ID instance recognizers
        self.idrec={"TID":getattr(self,"_TID"),
                    "PRD":getattr(self,"_PRD"),
                    "empty":getattr(self,"_TID_Empty") \
                   }
        self.pidrep={"*":getattr(self,"_pid_0_or_more"),
                     ":":getattr(self,"_pid_n") \
                    }
                   
        self.tidrep={":":getattr(self,"_tid_n") }

        # This establishes callback manager and callback processing points
        self.cbm=CBM()
        # Add each processing point CB instance with default methods
        self.cbm.point( CB("beg",    default=self._beg)     )
        self.cbm.point( CB("empty",  default=self._empty)   )
        self.cbm.point( CB("trying", default=self._trying)  )
        self.cbm.point( CB("token",  default=self._token)   )
        self.cbm.point( CB("error",  default=self._error)   )
        self.cbm.point( CB("found",  default=self._found)   )
        self.cbm.point( CB("failing",default=self._failing) )
        self.cbm.point( CB("end",    default=self._end)     )

        # This attribute is established by the lexer() method
        self.lex=None         # The lexer to be used by this parser

        # These attributes are established by the generate() method
        self.go=None    # The grammar object that build the production dictionary
        self.gp=None    # GrammarPy instance
        self.prds=None  # LL1Prods instance
        self.sprd=None  # The ID instance corresponding to the start productions
        
        # These attributes are established by the 

        # Parse specific attributes
        self.stream=None # The Stream managing the token input stream.
        
        # Detect Left Recursion in productions to specified depth.
        self.smgr=None      # Manages the parser's global state. see init()

    # Used by Parser class to report an error
    def __report(self,eo):
        self.gs.mgr.report(eo)

    # Dummy language processor call back methods.  These are the expected method
    # signatures to be supported by an overridden subclass method.
    def _beg(self,gs,pid): pass
    def _empty(self,gs,pid,n):pass
    def _trying(self,gs,pid,n,last=False): pass
    def _token(self,gs,pid,n,token): pass
    def _error(self,gs,pid,n,token): pass
    def _found(self,gs,pid,n,last=False): pass
    def _failing(self,gs,pid,n,eo=[],last=False): pass
    def _end(self,gs,pid,failed=False,eo=[]): pass

    # This is the recognizer for ID instances of type PRD
    # This method is called from one of the repetition recognizers.
    # Method Arguments:
    #    ido     The instance of ID trying to be recognized
    #    n       The alternative right side index in which this ID occurs in the
    #            production.  This information is passed to the language processor
    #            call back methods.
    #    resync  Whether the repetition recognizer allows stream resynchronization
    #            or not.  If allowed, the production must have had one or more 
    #            token resynchronization decorators defined in its grammar for
    #            resynchronization to have been attempted.
    #
    # The actions taken by this method are determined by whether the production
    # was recognized or not and whether or not resynchronization is allowed and
    # defined for the production:
    #   Production:                 Recognized         Not recognized
    #
    #   Synching Not Defined        False returned     SyntaxError raised
    #   Synching Defined:
    #     Not Allowed               False returned     SyntaxError raised
    #     Allowed and failed        False returned     SyntaxError raised
    #     Allowed and succeeded     False returned     True returned
    #   Synching Not Defined        False returned     SyntaxError raised
    #
    # Returning False indicates that resychronization of the input token stream
    # did not occur.  Resyncrhonization may occur only if the production was not
    # recognized.  If allowed and it succeeded, True is returned.  All other 
    # failure situations result in a SyntaxError being raised.  By returning True
    # the repetition recognizer is allerted that it does not need to adjust the
    # input stream processing following the failure.
    
    # A production alternative is represented by a series of ID's each call to
    # this method represents a PID to be recognized within a right-hand
    # alternative.  It is called by...
    #   _pid_n
    #   _pid_0_or_more.
    #
    #  prod1 ->  id id id prod2 id
    #                      |
    #                      +------> i.rep() calls:
    #                               _pid_n(ido=ID("prod2"),pid="prod1",x=0)
    #                or if prod2*   _pid_0_or_more(ido=ID("prod2"),pid="prod1",x=0)
    #
    # _pid_n calls ido.rec() which calls once
    #              _PRD(ido=ID("prod2"),ppid="prod1",n=3)
    # _pid_0_or_more calls ido.rec() multiple times until Empty is raised
    # 
    # _PRD will find the "prod2" PRD instance and will then select an alternative
    # based upon looking ahead into the input stream to next input symbol. 
    #
    #  prod2 -> TID1 TID2
    #             |
    #             +---------------> i.rep() calls:
    #                               _tid_n(ido=ID("TID1"),pid="prod2",x=0)
    # or if prodd2*:
    #  prod2 -> EMPTY
    #
    # _tid_n ido.rec() calls:
    #        _TID(ido=ID("TID1"),pid="prod2",x=0)
    #
    # The resyncing process is about figuring out where the parse should continue
    # and ensuring the language processor is aware of what productions that were
    # in the works failed.  The parser has two choices:
    #     - continue with the next TID/PID in the sequence of ID's or
    #     - abort recognition of the alternative entirely
    # 
    #
    def _PRD(self,ido,ppid,n):
        pid=ido.tpid
        prod_err=[]      # Captured error objects for SyntaxError exceptions
        # Note this KeyError should not occur!  But we catch it just in case.
        try:
            prdo=self.prds.gp.pid(pid)  # Fetch the PRD instance
        except KeyError:
            raise ValueError("parser.Parser._PRD() - PRD object not found for "
                "ID instance: %s" % ido) from None

        ptrace=prdo.ptrace

        # Call back for start of production
        beg=self.cbm.method("beg",pid)
        if ptrace:
            begm=CBM.mname(beg)
            if len(begm)>0:
                print("%s       CB %s(gs,%s)" % (pid,begm,pid))
        beg(self.gs,pid)                 # Call back for start of production
        
        # Use director set to determine the alternative being tried
        la_tok=self.stream.inspect(self.stream.current())
        la_id=la_tok.tid
        la_alt=None
        eo=None
        alt_err=[]
        try:
            la_alt=prdo.ds[la_id]
            action=0
        except KeyError:
            action=1
            if ido.resync:
                self.smgr.push(PState(pid,None,prdo,ido))
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - pushed state - %s" \
                        % (pid,"?",self.smgr.print()))
                state=self.smgr.resync(self.stream,debug=self.isdebug("edebug"))
                if self.isdebug("edebug"):
                    print("%s[%s] - _PRD - popped state by resync - %s" \
                        % (pid,"?",self.smgr.print()))
                action=state.action
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - resync action: %s" % (pid,"?",action))
        
        # Successful selection of RH instance from director set
        if action==0:
            pass

        # Syntax error because this ID provides no resynching or resycn
        elif action==1:   # Abort this production
            if self.isdebug("edebug"):
                print("%s[?] _PRD - ***** raising SyntaxError, director set "
                    "failure, no match for token: '%s'" % (pid,la_tok))
            eo=ErrorProd(pid,None,depth=self.smgr.depth(),token=la_tok,\
                source="_PRD")
            raise SyntaxError(eo=eo)

        
        elif action==2:  # Resync here.
                    # Input stream is positioned, so produce an error and continue
            d=self.smgr.depth()
            rtok=self.stream.inspect(self.stream.current())
            eo=ErrorResync(pid,"?",d,rtok,source="_PRD")
            if self.isdebug("edebug"):
                print("%s[?] _PRD - ***** reporting eo=\n    %s\n)" % (pid,eo))
            self.gs.mgr.report(eo)
            
            eo=ErrorProd(pid,None,depth=self.smgr.depth(),token=la_tok,\
                source="_PRD")
            eolist=[eo,]
            
            endm=self.cbm.method("end",pid)
            if ptrace:
                endn=CBM.mname(endm)
                if len(endn)>0:
                    print("%s    CB %s(%s,failed=%s,eo=\n    %s\n)"\
                        % (pid,endn,pid,True,eolist))
            res=endm(self.gs,pid,failed=True,eo=eolist)
            
            if not res:
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - ***** reporting eo=\n    %s" \
                            % (pid,"?",eo))
                self.gs.mgr.report(eo)
            return False

        else:
            raise ValueError("LL1parer.py - _PRD() - INTERNAL: invalid "
                "resync action: %s" % action)

        if ptrace:
            print("%s[%s] - selected by token: %s" % (pid,la_alt,la_tok))
            
        altn=la_alt
        alt=prdo.alts[altn]
        
        # Try the production alternative selected by the director set
        last=len(prdo.alts)-1
        end=(altn==last)
        error=True
        tracing=alt.trace  # trace this alternative or not

        # Call back for altenative being tried
        trying=self.cbm.method("trying",pid)
        if tracing:
            tryingn=CBM.mname(trying)
            if len(tryingn)>0:
                print("%s[%s]    CB %s(gs,%s,%s,last=%s)" \
                    % (pid,altn,tryingn,pid,altn,end))
        trying(self.gs,pid,altn,last=end)
        
        empty=False
        eo=None
        for i in alt.ids:
            self.smgr.push(PState(pid,altn,prdo,i))
            if self.isdebug("edebug"):
                print("%s[%s] _PRD - pushed state - %s" \
                    % (pid,altn,self.smgr.print()))
            try:
                if tracing:
                    repn=CBM.mname(i.rep)
                    print("%s[%s] _PRD tpid %s calling: %s" \
                        % (pid,altn,i.tpid,repn))
                # Recognize the number of id's and detect nullable production
                empty=i.rep(i,pid,altn,ptrace=tracing)
                if tracing:
                    print("%s[%s] _PRD returned empty=%s from: %s" \
                        % (pid,altn,empty,repn))

                state=self.smgr.pop()
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - popped state - %s" \
                        % (pid,altn,self.smgr.print()))
                action=state.action
            except SyntaxError as se:
                eo=se.eo
                if self.isdebug("edebug"):
                    print_id="ID('%s',%s)" % (i.tpid,i.typ)
                    print("%s[%s] _PRD %s - excepted SyntaxError.eo=\n    %s" \
                        % (pid,altn,print_id,eo))
                state=self.smgr.resync(self.stream,debug=self.isdebug("edebug"))
                if self.isdebug("edebug"):
                    print("%s[%s] - _PRD - popped state by resync - %s" \
                        % (pid,altn,self.smgr.print()))
                action=state.action
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - resync action: %s" % (pid,altn,action))
               
            if empty:
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - raising Empty" % (pid,altn))
                # Need to do this to break _pid_0_or_more recognition loop
                raise Empty()
 
            # Analyze action to be performed
            if action==0:  # Successful recognition
                continue
            if action==1:  # Abort this production
                break
            elif action==2:  # Resync here.
                # Input stream is positioned, so produce an error and continue
                d=self.smgr.depth()
                rtok=self.stream.inspect(self.stream.current())
                eo=ErrorResync(pid,altn,d,rtok,source="_PRD")
                if self.isdebug("edebug"):
                    print("%s[%s] _PRD - ***** reporting eo=\n    %s" \
                        % (pid,"?",eo))
                self.gs.mgr.report(eo)
                continue
            else:
                raise ValueError("LL1parer.py - _PRD() - INTERNAL: invalid "
                    "resync action: %s" % action)

        if eo is None:
            # Call back for recognizing an alternative
            found=self.cbm.method("found",pid)
            if tracing:
                foundn=CBM.mname(found)
                if len(foundn)>0:
                    print("%s[%s]    CB %s(gs,%s,last=%s)" \
                        % (pid,altn,foundn,altn,end))
            found(self.gs,pid,altn,last=end)    # Do callback for production alternative found

            error=False
        else:
            alt_err.append(eo)

            # Do production alternative failure
            failing=self.cbm.method("failing",pid)
            if tracing:
                failingn=CBM.mname(failing)
                if len(failingn)>0:
                    print("%s[%s]    CB %s(gs,%s,%s,eo=%s,last=%s)" \
                        % (pid,altn,failingn,pid,altn,alt_err,end))
            res=failing(self.gs,pid,altn,eo=alt_err,last=end)

            # If the callback method did not handle error objects, add them
            # to the list of production error failures
            if not res:
                prod_err.extend(alt_err)
            error=len(prod_err)>0
                

        # Call back for end of production
        if error:
            eolist=prod_err
        else:
            eolist=[]

        endm=self.cbm.method("end",pid)
        if ptrace:
            endn=CBM.mname(endm)
            if len(endn)>0:
                print("%s    CB %s(%s,failed=%s,eo=\n    %s\n)"\
                    % (pid,endn,pid,error,eolist))
        res=endm(self.gs,pid,failed=error,eo=eolist)

        if error:
            # If error objects not handled by callback method,
            # report them to the Error Manager.
            if not res:
                for eo in eolist:
                    if self.isdebug("edebug"):
                        print("%s[%s] _PRD - ***** reporting eo=\n    %s" \
                            % (pid,altn,eo))
                    self.gs.mgr.report(eo)

            if self.isdebug("edebug"):
                print("%s[%s] _PRD - ***** raising error eo=\n    %s"\
                    % (pid,altn,eo))
            raise SyntaxError(eo=eo)

        # Production recognized
        return False  # Not ever nullable here

    # This is the recognizer for an ID instance of type TID
    # This method is called from one of the repetition recognizers
    # Note, resync is ignored for TID's
    # Stream matched actions:
    #   1. The matching token is accepted and the stream moves forward
    #   2. 'token' callback method is called.
    #   3. returns False (do we still need this)?
    # Steam unmatched actions:
    #   1. Stream is reset to allow fetching of the error token
    #   2. 'error' callback method is called.
    #   3. raise a SyntaxError with an ErrorToken error object
    def _TID(self,ido,pid,n,resync=False):
        trace=ido.trace
        tid=ido.tpid
        if trace:
            print("%s[%s] _TID -     seeking: %s" % (pid,n,tid))
        eos=self.stream.eos()
        if trace and eos:
            print("%s[%s] _TID -     @ end of stream" % (pid,n))
        if eos:
            raise SyntaxError()

        # Whether the token matches or not, we need to get it from the steam
        tok=self.stream.fetch()
        if trace:
            print("%s[%s] _TID -     fetched token: %s" % (pid,n,tok))

        # Determine if token matches
        if tid!=tok.tid:

            # Token DID NOT MATCH!
            self.stream.reset(tok)  # Cancel accept pending

            # Build the error object so it can be passed in the callback
            #d=len(self.depth)
            d=self.smgr.depth()
            eo=ErrorToken(pid,n,d,tid,tok,source="_TID")

            # Perform the 'error' callback
            terror=self.cbm.method("error",pid)
            if trace:
                print("%s[%s] _TID - ***** rejected token" % (pid,n))
                terrorn=CBM.mname(terror)
                if len(terrorn)>0:
                    print("%s[%s]    CB %s(gs,%s,%s,%s)" \
                        % (pid,n,terrorn,pid,n,eo))
            terror(self.gs,pid,n,eo)

            if self.isdebug("edebug"):
                print("%s[%s] _TID - ***** raising SyntaxError.eo=\n    %s" \
                    % (pid,n,eo))
            raise SyntaxError(eo=eo)
            
        # Token MATCHED!
        self.stream.accept()
        token=self.cbm.method("token",pid)
        if trace:
            print("%s[%s] _TID -     accepted token" % (pid,n))
            tokenn=CBM.mname(token)
            if len(tokenn)>0:
                print("%s[%s]    CB %s(gs,%s,%s,%s)" \
                    % (pid,n,tokenn,pid,n,tok))
        token(self.gs,pid,n,tok)        # Do token callback for pid
        return False  # We never detect Empty here, so always return False
        
    # This is the recognizer for ID instances of type TID
    # This method is called from one of the repetition recognizers
    # Note, resync is ignored for TID's
    def _TID_Empty(self,ido,pid,n,resync=False):
        trace=ido.trace
        empty=self.cbm.method("empty",pid)
        if trace:
            print("%s[%s] _TID_Empty -      empty string accepted" % (pid,n))
            emptyn=CBM.mname(empty)
            if len(emptyn)>0:
                print("%s[%s]    CB %s(gs,%s,%s)" \
                    % (pid,n,emptyn,pid,n))
        empty(self.gs,pid,n)            # Do token callback for pid
        if self.isdebug("edebug"):
            print("%s[%s] _TID_Empty - ***** raising Empty" % (pid,n))
        raise Empty()                   # Break out of recognizer loops

    # "*" Repetition Recognizer - zero or more instances of PRD or ID
    def _pid_0_or_more(self,ido,pid,n,ptrace=False):
        current=self.stream.current()      # Remember the stream restart position
        while True:
            try:
                # Call PRD recognizer.  Never resync in this case
                if ptrace:
                    recn=CBM.mname(ido.rec)
                    print("%s[%s] _pid_0_or_more calling: %s" % (pid,n,recn)) 
                empty=ido.rec(ido,pid,n) 
                if ptrace:
                    print("%s[%s] _pid_0_or_more empty=%s returned from: %s" \
                        % (pid,n,empty,recn))
                if empty:
                    if ptrace:
                        print("%s[%s] _pid_0_or_more returning, empty=%s" \
                            % (pid,n,empty))
                    break
            except Empty:
                if self.isdebug("edebug"):
                    print("%s[%s] _pid_0_or_more - excepted Empty" % (pid,n))
                break

    # ":" Repetition Recognizer - x number of instances of PRD or ID
    # Consumes each occurrence of the ID encountered, but if the occurrence number
    # is not as expected, generate a syntax error.
    def _pid_n(self,ido,pid,x,ptrace=False):
        n=ido.min  # The number of required occurrences
        number=0
        eo=None
        current=self.stream.current()      # Remember the stream restart position
        while number<n:
            try:
                # Call PID recognizer.  Always allow resynching in this case
                resync=ido.rec(ido,pid,x)
                # Consume the recognized occurrence of the ID or resync
                current=self.stream.current()
                # current is the positions within the stream of the NEXT token
                if resync:
                    return
                # If resync'ing did not occure, ID succeeded
                number+=1
            except Empty as em:
                if self.isdebug("edebug"):
                    print("%s[%s]    pid_n() - excepted Empty for ID: %s" \
                        % (pid,x,ido)) 
                break
            except SyntaxError as se:
                # current points to the error toekn
                eo=se.eo
                if self.isdebug("edebug"):
                    print("%s[%s] _pid_n() - ***** excepted SyntaxError.eo="
                        "\n    %s" % (pid,n,eo))
                break
        if number!=n:
            if eo is None:
                # BUT, because we did not find the number we expected, it is a
                # syntax error.
                tok=self.stream.inspect(current)
                d=self.smgr.depth()
                eo=ErrorProd(pid,x,depth=d,token=tok,source="_pid_n")
            if self.isdebug("edebug"):
                print("%s[%s] _pid_n() - ***** raising SyntaxError.eo=\n    %s" \
                    % (pid,x,eo))
            raise SyntaxError(eo=eo)
            
        return False  # Captured nullable production here, continue as normal
            
    # ":" Repetition Recognizer - x number of instances of TID
    #
    # Consumes each valid occurrence of the ID encountered.
    # If the number of expected occurences matchs, returns to the caller, _PRD()
    # If the number of expected matches does not occur:
    #   1.  The ErrorToken object is reported to the error manager
    #   2.  A SyntaxError with the same ErrorToken object is raised to _PRD()
    #
    # Exceptions raised:
    #   SyntaxError(eo=ErrorToken())
    def _tid_n(self,ido,pid,x,ptrace=False):
        n=ido.min  # The number of required occurrences
        number=0
        eo=None
        current=self.stream.current()      # Remember the stream restart position
        empty=False
        while number<n:
            try:
                # Call TID recognizer.  Always allow resynching in this case
                if ptrace:
                    recn=CBM.mname(ido.rec)
                    print("%s[%s] _tid_n calling: %s" % (pid,x,recn))
                ido.rec(ido,pid,x)
                if ptrace:
                    print("%s[%s] _tid_n returned from: %s" % (pid,x,recn))
                # Consume the recognized occurrence of the ID or resync
                current=self.stream.current()
                number+=1
            except Empty as em:
                if self.isdebug("edebug"):
                    print("%s[%s] _tid_n excepted Empty" % (pid,x))
                number+=1
                empty=True
                break
            except SyntaxError as se:
                # This means the stream is set to return the token unaccepted
                # token.
                eo=se.eo
                if self.isdebug("edebug"):
                    print("%s[%s] _tid_n() - ***** excepted SyntaxError.eo="
                        "\n    %s" % (pid,x,eo))
                break
        if number!=n:
            self.gs.mgr.report(eo)
            if self.isdebug("edebug"):
                print("%s[%s] _tid_n() - ***** raising SyntaxError.eo="
                    "\n    %s" % (pid,x,eo))
            raise SyntaxError(eo=eo)
        return empty

    # This internal method prints text with line numbers
    def _text(self,string):
        lines=string.splitlines()
        for x in range(len(lines)):
            line=lines[x]
            num=x+1
            number="[%s]" % num
            print("%s %s" % (number,line))
            
    # Establish a callback method for the language processor.
    # Method arguments:
    #    point   The processing point id.  
    #            One of: "beg","trying", "token", "found", "failing", or "end"
    #    pid     The production id for which the method should be called
    #    method  The method name called for the production's processing point.
    def cbreg(self,pid,point,method):
        self.cbm.register(point,pid,method)

    # Set a debug flag or flags.
    #    debug("flag1","flag2") will enable both flags for debugging
    #    debug(flag1=True,flag2=False)  will set the flag as specified
    # The following debugging flags are supported by the Parser claas:
    #    pdebug   Parser debug flag
    #    ldebug   Parser lexer's debug flag
    #    tdebug   Parser lexer's token debug flag
    #    gdebug   Grammar processing debug flag
    #    gldebug  Grammar processing lexer debug flag
    #    gtdebug  Grammar processing token debug flag
    # Subclasses may add their own debug flags by calling the flag() method,
    # although they must be unique from those supported inherently by the Parser
    # class.
    def debug(self,*args,**kwds):
        for x in args:
            self.dm.enable(x)
        for x in kwds:
            new=kwds[x]
            if new:
                self.dm.enable(x)
            else:
                self.dm.disable(x)

    # This method filters Tokens before presentation to the parser.  By default
    # this method returns all recognized tokens.  A subclass must override this
    # method to change this behavior.  When a subclass overrides this method it
    # must either return the token for further processing or None to cause the
    # token to be removed from the token stream.
    def filter(self,tok):
        return tok

    # Define a debug flag and initialize it to False
    # A subclass may add additional debug flags
    def flag(self,dflag):
        self.dm.flag(dflag)
        #try:
        #    self.pdebug[dflag]
        #    raise ValueError("%s.flag() - debug flag already exists: '%s'" \
        #        % (self.__class__.__name__,dflag))
        #except KeyError:
        #    self.pdebug[dflag]=False

    # This method is used to create the parser from a supplied lexer and grammar.
    # It is intended to called from a subclass init() method
    def generate(self,grammar,lexer,start):
        gdebug=self.isdebug("gdebug")
        gldebug=self.isdebug("gldebug")
        gtdebug=self.isdebug("gtdebug")
        gLL1debug=self.isdebug("gLL1debug")
        self.go=LL1grammar.Grammar(debug=gdebug,ldebug=gldebug,tdebug=gtdebug,\
            LL1debug=gLL1debug)
        self.go.lexer(lexer)
        prods=self.go.spec(start,grammar,self)
        self.setup(prods,lexer)

    # Print the grammar used to create the parser.
    #
    # WARNING:
    # If you get a "TypeError: 'str' object is not callable" when attempting
    # to call this method, you have inadvertently replaced this method with 
    # a string that has the attribute name 'grammer'.  This will happen if you 
    # define a string as either a class attribute  
    # <someLanguageClass>.grammar="string" or within a lang.Language processor 
    # subclass you have defined self.grammar='string".  
    #
    # For that reason it is recommended the grammar be defined as a local variable 
    # in the <someLanaguageClass>.define_parser() method, as it is in the sample
    # module in this directory.  This technique avoids this possibility.
    #
    # This TypeError is not restricted to string objects but can be encountered
    # for other none callable objects that have replaced this method.  Because it 
    # is painful to track down and requires a good understanding of how 
    # dictionaries are used in Python, this warning has been provided.
    def grammar(self):
        if not self.prereq("grammar",grammar=True,msg=False):
            print("%s not constructed from a grammar" % self.__class__.__name__)
        if not self.prereq("grammar",spec=True):
            return
        print("\n%s Grammar Specification\n" % self.__class__.__name__)
        self._text(self.go.specification)

    # This method links the ID instance to the parser recognizer functions and
    # the language processor for Node creation.
    def idinit(self,ido,empty=False):
        typ=ido.typ
        # Set up recognizer methods
        if empty:
            typ="empty"
        ido.rec=self.idrec[typ]
        if ido.typ=="TID":
            ido.rep=self.tidrep[ido.reptyp] # Rep recognizer method for a TID
        else:
            ido.rep=self.pidrep[ido.reptyp] # Rep recognizer method for a PID
        if ido.rec is None:
            raise ValueError("LL1parser.py - Parser.idinit() - ID tpid %s "
                "recognizer is None" % ido.tpid)
        if ido.rep is None:
            raise ValueError("LL1parser.py - Parser.idinit() - ID tpid %s "
                "repetition recognizer is None" % ido.tpid)

    # This method must be supplied by a subclass.  It is intended to be used for
    # initialization of the Parser with productions instances specific to the
    # subclass parser.
    #
    # WARNING: This method should return the current instance (return self) if
    # this coding contruct is expected to be used:
    #     lex=MyParser().init()
    def init(self,*args,**kwds):
        thiscls=self.__class__
        if issubclass(thiscls,Parser):
            raise NotImplementedError(\
                "The class %s must supply the init() method" % thiscls.__name__)
        raise NotImplementedError(\
            "a subclass of Parser must supply the method init()")

    # This method returns True of False for a tested debug flag.  Unregistered
    # flags raise a Value Error
    def isdebug(self,flag):
        return self.dm.isdebug(flag)
        #try:
            
        #    switch=self.pdebug[flag]
        #    if switch:
        #        return True
        #    return False
        #except KeyError:
        #    raise ValueError("%s.isdebug() - undefined flag encountered: %s" \
        #        % (self.__class__.__name__,flag)) \
        #        from None

    # Parse a string in the target language
    #
    # Method arguments:
    #    string     The input source being parsed
    #    depth      Specify the maximum production call depth.  Defaults to 20.
    #    lines      Argument passed to lexer tokenize() method.  Defaults to True.
    #               True causes the lexer to track input line numbers.
    #    fail       Argument passed to the lexer tokenize() method.
    #               Defaults to False.  False causes the token of type
    #               'unrecognized' to be created
    # A SyntaxError is raised if the START production is not recognized
    def parse(self,string,depth=20,lines=True,fail=False):
        self.smgr=PStateMgr(self.gp.EOS(),depth=depth)
        self.stream=Stream(self)
        self.stream.tokens(string,lines=lines,fail=fail)
        start_pid=self.sprd.tpid
        
        # Recognize the starting non-terminal repetitions
        try:
            self.sprd.rep(self.sprd,None,0)  # Do the START ID
        except SyntaxError as se:
            eo=se.eo  # Extract the error object
            if self.isdebug("edebug"):
                print("%s parse - reporting error eo=\n    %s" 
                    % (self.sprd.tpid,eo))
            self.__report(eo)
            
        # Validate parser end state
        current=self.stream.current()
        token=self.stream.inspect(current)
        eos=self.gp.EOS()
        depth=self.smgr.depth()
        if token.tid!=eos:
            eo=ErrorStream(start_pid,depth,token,source="parse")
            self.__report(eo)
        if depth != 0:
            print("ERROR: state stack not exhaused - %s" % self.smgr.print())

    # Check the state of the parser for a prerequisite component. Returns
    # True if prereqs are present, False otherwise.
    def prereq(self,method,lexer=False,grammar=False,source=False,stream=False,\
               spec=False,msg=True):
        if lexer and self.lex is None:
            if msg:
                print("%s.%s() can not perform operation, lexer is missing" \
                    % (self.__class__.__name__,method))
            return False
        if grammar and self.go is None:
            if msg:
                print("%s.%s() can not perform operation, grammar is missing" \
                    % (self.__class__.__name__,method))
            return False
        if source:
            if ((not self.prereq(nethod,lexer=True,msg=False)) \
               or (self.lex.string is None) \
               or (len(self.lex.string)==0)):
                if msg:
                    print("%s.%s() can not perform operation, source is missing" \
                        % (self.__class__.__name__,method))
                return False
        if spec:
            if (not self.prereq(method,grammar=True,msg=False)):
                spec=self.go.specification
                if (spec is None) or (len(spec)==0):
                    if msg:
                        print("%s.%s() can not perform operation, grammar "
                            "specification is missing" \
                            % (self.__class__.__name__,method))
                    return False
        if stream and self.stream is None:
            print("%s.%s() can not perform operation, token stream is missing" \
                % (self.__class__.__name__,method))
            return False
        return True

    # Display PRD instances supported by the parser
    def productions(self):
        print("\n%s Productions\n" % self.__class__.__name__)
        if self.sprd is None:
            print("Start production undefinded")
        else:
            print("Start Production: %s" % self.sprd)
        pids=[]
        for x in self.prds.gp.iter_pids():
            pids.append(x)
        pids.sort()
        for x in pids:
            prd=self.prds.gp.pid(x)
            print("%s" % prd)

    # Establish and valiate all of the components are present.
    # Method arguments:
    #    prds    A LL1Prods instance.  It may be manually created or
    #            established with a grammar using the generate() method
    #    lexer   A lexer.Lexer instace used to recognize token types by the parser
    def setup(self,prds,lexer):
        if not isinstance(prds,LL1grammar.Prods):
            raise ValueError("LL1Parser.py - parser.setup() - 'prds' argument "
                "must be an instance of LL1grammar.LL1Prods: %s" % prds)
        self.prds=prds                  # LL1Prods instance
        self.lex=lexer                  # lexer.Lexer instance
        self.gp=self.prds.gp            # GrammarPy instance
        self.sprd=self.prds.gp.start_id
        self.idinit(self.sprd,empty=False)

        if (self.go is not None) and self.go.errors:
            raise ValueError("LL1parser.py - %s.setup() - errors encountered "
                "in parser grammar: %s"\
                % (self.__class__.__name__,self.go.errors))

    # Print the input text with line numbers
    def source(self):
        if not self.prereq("source",lexer=True):
            return
        print("\n%s Source Text\n" % self.__class__.__name__)
        self._text(self.lex.string)

    # Print a the token stream being parsed after filtering
    def tokens(self):
        if not self.prereq("tokens",stream=True):
            return
        self.stream.print()

# This object manages the global state of the recursive descent parser and
# facilitates various forms of token stream error recovery.
class PStateMgr(object):
    def __init__(self,eos,depth=20):
        # Left recursion detector.  
        # With LL(1) validation this should not be a problem
        self.eos=eos      # End of stream token
        self._depth=depth # Maximum allowed call stack size
        self.stack=[]     # Individual state entries are added to this list
        
        # When in the resynch process this is set True. 
        # Reset to False when a state returns an action other than 1.
        self.resyncing=False
        
    def __no_resync(self):
        for state in self.stack:
            state.action=1    # Force a syntax error at every level
        
    # The input stream will be positioned at the token that is in error
    # Resynchronization of the input stream with the parsr state occurs
    # When the first match of a follow set occurs for the currently tested
    # input token, starting with the failed token and checking ID's from top of
    # the stack to the bottom (the starting production id)
    def __resync(self,stream,debug=False):
        if debug:
            print("PStateMgr - __resync() - failure in stack - %s" \
                % self.print())
            
            #for x in self.stack:
            #   print("    %s" % x.print())
        # find eligible resynchronization points in the current state
        eligible=[]   # List of ID's in bottom to top of stack order
        for state in self.stack:
            if not state.ido.resync:
                continue
            eligible.append(state)
            
        if debug:
            print("PStateMgr - __resync() - search started with eligible IDs:")
            for x in eligible:
                print("    %s" % x.print())

        # If no eligible ID's for resynchronization, we have no choice but to
        # force a SyntaxError at every level
        if len(eligible)==0:
            if debug:
                print("PStateMgr - __resync() - resync failed, no eligible ID's")
            self.__no_resync()
            return

        eligible.reverse() # Process the eligible ID's the top of the stack down

        stream.resync()  # prepare the input stream for resynchronization
        testpos=current=stream.current()
        eos=self.eos

        while True:
            token=stream.inspect(testpos)
            tid=token.tid
            # If we have exhausted the input streamm, 
            # resynchronization is not possible
            if tid==eos:
                if debug:
                    print("PStateMgr - __resync() - resync failed, "
                        "encountered end-of-stream")
                self.__no_resync()
                return

            # Try this token
            for state in eligible:
                if state.n is None:  
                    # We are resynching because the diretor set selection of an
                    # eligible PID 
                    this_follow=state.prdo.follow
                else:
                    this_follow=state.ido.follow
                if tid in this_follow:
                    # !! YES - we can resynch here
                    state.action=2
                    if debug:
                        print("PStateMgr - __resync() - resync state found:"
                            "\n    %s" % state.print())
                    # Everything else above this point must be a SyntaxError
                    for d in range(state.depth+1,len(self.stack)):
                        pstate=self.stack[d]
                        pstate.action=1
                    # Reset the next token to the one we can synchronize on
                    if debug:
                        print("PStateMgr - __resync() - successful %s" \
                            % self.print())
                       
                        #for x in self.stack:
                        #    print("    %s" % x)
                        print("PStateMgr - __resync() - repositioning input "
                            "at [%s,%s]" % (token.line,token.linepos))
                    stream.pos(testpos)
                    # Return and resynchronize
                    return

            testpos+=1   # Try the next token input

    # Returns the current call stack size
    def depth(self):
        return len(self.stack)

    # Remove a PState entry from the call stack
    def pop(self):
        if len(self.stack)==0:
            raise ParserError(msg="LL1parser.py - PStateMgr.pop() - "
                "production call depth exhausted, no entries to remove")
        return self.stack.pop()

    # Print the current state of the stack
    def print(self):
        string="PStateMgr stack:\n"
        for x in self.stack:
            string="%s    %s\n" % (string,x.print())
        return string[:-1]

    # Add a PState entry to the call stack
    def push(self,pstate):
        if not isinstance(pstate,PState):
            raise ValueError("LL1parser.py - PstateMgr.push() - 'pstate' "
                "argument must be an instance of PState: %s" % pstate)
        if len(self.stack)>=self._depth:
            self.print()
            raise ParserError(msg="LL1parser.py - PStateMgr.push() - "
                "exceeded production call depth")
        pstate.depth=len(self.stack)
        self.stack.append(pstate)
        
    # Resynchronize input stream with parsing process
    def resync(self,stream,debug=False):
        if not self.resyncing:
            self.__resync(stream,debug=debug)
            self.resyncing=True
        state=self.pop()
        if state.action == 2:
            self.resyncing=False
        #state.action=1
        return state
        
class PState(object):
    def __init__(self,pid,n,prdo,ido):
        self.pid=pid
        self.n=n
        self.prdo=prdo
        self.ido=ido
        self.depth=None   # Set when the state object is pushed on the stack
        # re-sync ations:
        #  0 == no-resync, continue processing ID's
        #  1 == can not re-sync following this ID, create a SyntaxError
        #  2 == stream synchronized following this ID, issue error report and
        #       continue processing ID's in this right-hand ID list.
        self.action=0
    def __str__(self):
        return "PState(PRD=%s[%s] IDO='%s' depth=%s action=%s"\
            % (self.pid,self.n,self.ido.tpid,self.depth,self.action)
    def print(self):
        if self.n is None:
            return "PState[%s]: %s[?] action=%s" \
                % (self.depth,self.pid,self.action) 
        return "PState[%s]: %s[%s]:'%s' action=%s" \
            % (self.depth,self.pid,self.n,self.ido.tpid,self.action)     

# Stream - the token stream manager
#
# Instance creation arguments:
#    parser   The Parser instance using this stream.
#
# Instance methods:
#    tokens   Creates the token stream using the parser's lexer.Lexer instance.
#
class Stream(object):
    def __init__(self,parser):
        self._parser=parser  # The parser instance using this stream
        self._stream=[]      # The entire stream of Token instances being parsed
        self._next=0         # The index in self.stream of the next token
        self._pending=False  # Whether an accept is pending
        self._tokens=0       # Number of tokens in the stream

    # Accept the previously fetched token.  Note if the previously fetched token
    # has already been accepted a ValueError is raised
    def accept(self):
        if self._pending:
            self._next+=1
            self._pending=False
            return
        raise ValueError("Stream.accept() - accept not pending")

    # Return the next position in the input stream to be fetched
    def current(self):
        return self._next
        
    # Return whether positioned at end-of-stream
    def eos(self):
        return self._next>=self._tokens

    # Get the next token in the stream.  An IndexError will be raised if the
    # parser attempts to read beyond the last token.
    #
    # Note: the next index is not advanced to the next token until the accept()
    # method is called.  Succeeding calls to the fetch() method without an
    # intervening call to accept() will return the same Token instance
    def fetch(self):
        tok=self._stream[self._next]
        self._pending=True
        return tok
        # The pointer to the next token is not advanced until the accept() method
        # is called.

    # Return a token independent of stream processing.  Used by the parser for
    # error reporting.
    def inspect(self,ndx):
        if ndx<0 or ndx>=self._tokens:
            return None
        return self._stream[ndx]

    # Reset the stream position to supplied ndx
    def pos(self,ndx):
        # Do a sanity check on the new index.
        self._pending=False
        if self.eos():
            return
        if ndx<0 or ndx >= self._tokens:
            raise ValueError("Stream.pos() - stream new position is invalid: %s" \
                % ndx)
        self._next=ndx

    # Print the input stream of tokens
    def print(self):
        cls=self._parser.__class__.__name__
        if len(self._stream)==0:
            print("%s token stream is not available" % cls )
            return
        print("\n%s Input Token Stream\n" % cls)
        for x in range(len(self._stream)):
            tok=self._stream[x]
            print("[%s] %s" % (x,tok))

    # Reset to the stream so that the provided token becomes the next token
    # for fetching.  A pending accept is cleared
    def reset(self,tok):
        if not isinstance(tok,lexer.Token):
            raise ValueError("LL1parser.py - Stream.reset() - 'tok' argument "
                "must be an instance of lexer.Token: %s" % tok)
        info=tok.info   # Get the location of the token
        # Do a sanity check on the info.
        if info<0 or info >= self._tokens:
            raise ValueError("Stream.reset() - token info corrupted\n   %s" % tok)
        self._next=info
        self._pending=False
        
    # Set up the stream for the resychronization process.  Resynching will occur
    # with the previously unaccepted token or at the current position.  The 
    # accept pending flag is turned off.
    def resync(self):
        if self._pending:
            self._next=-1
        self._pending=False

    # Build the token stream that will be recognized by the parser.  It will
    # use the parser's filter() method to filter tokens.
    #
    # Method Arguments:
    #   string  The input string being analyzed for token content.
    #   lines   Whether lines will be recognized by the lexer.Lexer instance.
    #           Default it True.
    #   fail    Whether the lexer will fail (fail=True) or generate Unrecognized
    #           tokens (fail=False).  Default is False.
    def tokens(self,string,lines=True,fail=False):
        # It is faster to reduce the number of lookups on each usage
        parser=self._parser
        lexer=parser.lex

        for tok in lexer.tokenize(string,lines=lines,fail=fail):
            ftok=parser.filter(tok)
            if ftok is None:
                continue
            ftok.info=len(self._stream)  # Preserve the tokens position
            self._stream.append(ftok)    # Add it to the stream.
        self._next=0                     # Start with the first token
        self._tokens=len(self._stream)   # Number of tokens in the stream

if __name__ == "__main__":
    raise NotImplementedError("LL1parser.py - must only be imported")
