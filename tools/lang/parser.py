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
# of creating a simple recursive descent parser utilized in a language processor.
# Refer to the document "SATK for s390 - Language Processing Tools" in the SATK
# doc directory for a description of this module's usage.

# Python imports:
import functools  # Access to compare function to key function

# SATK imports:
import lexer

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
            return ""
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
        print("P%s'%s' error %s%s%s" % (self.loc(depth=True),self.pid,n,string,src)) 
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

# GLexer - the lexer used by the Grammar class
class GLexer(lexer.Lexer):
    def __init__(self,debug=False,tdebug=False):
        self.gdebug=debug
        self.tdebug=tdebug
        super().__init__()

    # Initialize the lexer
    def init(self):
        tdebug=self.tdebug
        self.type(lexer.Type("name",r"[a-zA-Z][a-zA-Z0-9_]*",debug=tdebug))
        self.type(lexer.Type("decorator",r"<[^ \t\r\f\v\n>]+>",debug=tdebug))
        self.type(lexer.Type("rep",r"[\*\+\?]|:[1-9][0-9]*",debug=tdebug))
        self.type(lexer.Type("rhand","->",debug=tdebug))
        self.type(lexer.Type("ws",r"[ \t\r\f\v]+",ignore=True,debug=tdebug))
        self.type(lexer.Type("comment",r"#[^\n]*",ignore=True,debug=tdebug))
        self.type(lexer.Type("nl",r"(?m)\n+",eol=True,debug=tdebug))
        if self.gdebug:
            self.types()
        return self

# Grammar - provides to a parser its defined productions used for recognizing
#           its language.
#
# This method is used internally by the Parser class while it is being created.
# There is limited sophistication in this grammar recoginizer.
#
# Grammar instance methods:
#   lexer    Provides the lexer used by the parser being created
#   spec     This method converts a grammar specification into a dictionary of
#            PRD instances.  This dictionary is the foundation of the parser
#
# Grammar instance arguments:
#   debug    Specify True to debug the Grammar class.  Default is False.
#   ldebug   Specify True to debug the GLexer.  Default is False.
#   tdebug   Specify True to debug the GLexer token types.  Default is False.
class Grammar(object):
    def __init__(self,debug=False,ldebug=False,tdebug=False):
        self.debug=debug

        # Attributes used by to process the production definitions. See spec()
        self.glexer=GLexer(debug=ldebug,tdebug=tdebug).init()
        self.glines=None   # List of tokenized lines
        self.specification=None
        self.parser=None   # Parser for which productions are being built

        # Attributes used to build the generated parser.  See lexer() method
        self.ptokens=[]    # The list of token types recognized by the parser
        self.plexer=None   # The lexer used by the generated parser

        # Productions defined for the parser. See _pass1() method
        self.prods=[]

        # Production dictionary.  See _pass2() method
        self.pdict={}

        # Global error counter.  It is expected that the Parser will detect these
        # errors.  This class only records the occurrence of the errors.
        self.errors=0

    # Tests a ID name for it being a terminal id
    def _isTID(self,name):
        status=name in self.ptokens
        if self.debug:
            print("%s == %s._isTID('%s')" % (status,self.__class__.__name__,name))
        return status

    # The internal method parses a set of tokens from a tokenized line for valid
    # grammar syntax.
    #
    #          name rhand ( name rep? )+ decorator*
    # states 0     1       2    3       4          4
    #
    # It returns a PRD instance corresponding to the defined production
    def _parse(self,line):
        if len(line)==0:
            raise ValueError("Grammar._parse() - empty line encountered")

        lh=None       # Left hand production 'name' Token
        rh=[]         # List of ID instances
        trace=False   # Trace this production
        sync=[]       # Synchronize production with next token id in this list
        syncflag=[]   # The corresponding accept ('+') indicator for token id

        tpid=None     # GLexer 'name' token for production or token ids
        rep=None      # Glexer 'rep' token for a id repetition
        decorators=[] # List of decorator tokens
        error=False
        state=0

        thisclass=self.__class__.__name__

        # This scan of the tokens in the input list
        for x in line:
            if self.debug:
                print("%s._parse(): state=%s token=%s" \
                    % (thisclass,state,x))
            if state==0:   # Looking for production left hand 'name' token
                if x.istype("name"):
                    lh=x
                    state=1
                    continue
                else:
                    self._unexpected(x)
                    error=True
                    break
            elif state==1: # Looking for right hand separator 'rhand' token
                if x.istype("rhand"):
                    state=2                                    
                    continue
                else:
                    self._unexpected(x)               
                    error=True
                    break
            elif state==2: # Looking for terminal or non-terminal 'name' or
                           # 'decorator' token
                if x.istype("name"):
                    tpid=x
                    state=3
                    continue
                elif x.istype("decorator"):
                    decorators.append(x)
                    state=4
                    continue
                else:
                    self._unexpected(x)
                    error=True
                    break
            elif state==3: # Target token id found
                if x.istype("name"):
                    # Flush the pending ID creation
                    rh.append( ID(tpid) )
                    tpid=x
                    state=3
                    continue
                elif x.istype("rep"):
                    rh.append( ID(tpid,rep=x) )
                    tpid=None
                    state=2
                    continue
                elif x.istype("decorator"):
                    decorators.append(x)
                    state=4
                    continue
                else:
                    self._unexpected(x)
                    error=True
            elif state==4: # decorator found, continue looking for more
                if x.istype("decorator"):
                    decorators.append(x)
                    continue
                else:
                    self._unexpected(x)
                    error=True
            else:
                raise ValueError("Grammar._parse() - Invalid state: %s" % state)
        if tpid is not None:
            rh.append( ID(tpid,rep=rep) )
        if error:
            raise ParserError()
        rh=RH(lst=rh)  # Create the RH instance

        # Process decorators:
        for x in decorators:
            if self.debug:
                print("%s._parse(): decorator=%s" % (thisclass,x))
            dec=x.string
            if len(dec)<3:
                print("[%s:%s] invalid decorator identified by GLexer: '%s'"\
                    % (x.line,x.linepos,dec))
                raise ParserError()
            if dec[1]=="!":
                r=dec[2:-1]
                a=False
                if r[-1]=="+":
                    a=True
                    r=r[:-1]
                if len(r)==0:
                    print("[%s:%s] resynchronization token missing from decorator" \
                        % (x.line,x.linepos))
                    self.errors+=1
                else:
                    if not self._isTID(r):
                        print("[%s:%s] unrecognized resynchronization token type: "
                            "'%s'" % (x.line,x.linepos,r))
                        self.errors+=1
                    else:
                        sync.append(r)
                        syncflag.append(a)
                continue
            if dec == "<trace>":
                trace=True
                continue
            print("[%s:%s] unrecognized decorator: '%s'" \
                % (x.line,x.linepos,dec))

        # Make sure production does not conflict with a token id
        if self._isTID(lh.string):
            self.errors+=1
            print(\
                "[%s:%s] left hand production id conflicts with token id: %s"\
                % (lh.line,lh.linepos,ls.string))
            raise ParserError()

        # Initialize the ID instance for use by the parser
        for x in rh.ids:
            if self._isTID(x.tpid):
                x.istid=True
                x.typ="TID"
                x.trace=trace
            else:
                x.isprd=True
                x.typ="PRD"
            # Set recognizer and language processor methods
            self.parser.idinit(lh.string,x)
        rh.trace=trace

        prd=PRD(lh.string,sync=sync,flags=syncflag)
        prd.rhand(rh)
        if self.debug:
            print("%s" % prd)
        return prd

    # Pass 1 of the grammar processor - creates a list of PRD instances
    def _pass1(self):
        for x in self.glines:
            try:
                self.prods.append(self._parse(x))
            except ParserError:
                continue

    # Pass 2 of the grammar processor - creates the PRD dictionary for the parser
    def _pass2(self):
        for x in self.prods:
            try:
                pid=self.pdict[x.pid]
                pid.alts.extend(x.alts)
            except KeyError:
                self.pdict[x.pid]=x

    # Pass 3 validates that each production identified in a right hand option is
    # defined.
    def _pass3(self):
        tids=0
        pdict=self.pdict
        for pidkey in pdict:
            pid=pdict[pidkey]
            for rh in pid.alts:
                for tpid in rh.ids:
                    if tpid.isprd:
                        try:
                            name=tpid.tpid
                            pdict[tpid.tpid]
                        except KeyError:
                            tok=tpid.id_tok
                            line=tok.line
                            pos=tok.linepos
                            self.errors+=1
                            print("[%s:%s] encountered undefined production: %s" \
                                % (line,pos,name))
                    elif tpid.istid:
                        tids+=1
                    else:
                        tok=tpid.id_tok
                        print("[%s:%s] token type '%s' not classified as "
                            "PRD or TID, recognized string: '%s'" \
                            % (tok.line,tok.linepos,tok.tid,tok.string))
        if not tids:
            print("error: no TID's found in productions")
            self.errors+=1

    # Generic internal method for printing unexpected token messages
    def _unexpected(self,tok):
        self.errors+=1
        print("[%s:%s] unexpected '%s' token in production: '%s'" \
            % (tok.line,tok.linepos,tok.tid,tok.string))

    # This method identifies the lexer.Lexer instance used by the parser.  The lexer
    # must be identified before any productions are associated with the Parser.
    def lexer(self,l=None):
        self.plexer=l
        if self.plexer is not None:
            self.ptokens=self.plexer.tids

    # This method processes a grammar specification creating a dictionary of PRD
    # instances.  The PRD instances contain ID instances linked to the parser
    # for processing.
    def spec(self,string,parser):
        self.specification=string
        self.parser=parser
        self.glines=[]
        aline=[]

        if self.plexer is None:
            self.errors+=1
            print("[1:1] lexer has not been registered")

        # Tokenize the grammar specification
        for x in self.glexer.tokenize(self.specification,lines=True,fail=False):
            if self.debug:
                print("%s" % x)
            if x.istype("unrecognized"):
                self.errors+=1
                print("[%s:%s] unrecognized text ignored: '%s'" \
                    % (x.line,x.linepos,x.string))
                continue
            if x.ignore:
                continue
            if not x.istype("nl"):
                aline.append(x)  # tokens: name, rhand, rep, decorator
                continue
            # "nl" signals the end of a production
            if len(aline)>0:
                self.glines.append(aline)
                aline=[]

        if len(aline)>0:
            self.glines.append(aline)

        if self.debug:
            print("\n%s Recognized production line" % self.__class__.__name__)
            for x in self.glines:
                for y in x:
                    print("%s" % y)
                print("")

        self._pass1()  # Create PRD istances, one PRD per production
        self._pass2()  # Create the final PRD dictionary
        self._pass3()  # Validate all referenced pid's are defined

        return self.pdict  # Return this to the Parser

# ID - The generic production right hand terminal or non-terminal
#
# Instance arguments:
#   tpid   The 'name' Token of the terminal or non-terminal or its id
#   rep    The 'rep' Token of terminal or non-terminal (or None if absent)
#   string Indicates whether the tpid argument is a string (True) or a Token
#          from the Grammar processing (False).
class ID(object):
    def __init__(self,tpid,rep=None,string=False):
        if string:
            self.id_tok=None
            self.rep_tok=None
            self.tok_tok=None
            self.tpid=tpid
            self.repstr=rep
        else:
            if not isinstance(tpid,lexer.Token):
                raise TypeError("ID.__init__() - tpid must be instance of Token: "
                    "%s" % tpid)

            if rep is not None:
                if not isinstance(rep,lexer.Token):
                    raise TypeError("ID.__init__() - rep must be instance of "
                        "Token: %s" % rep)

            self.id_tok=tpid   # Preserve id token for error message reporting
            self.tpid=tpid.string # Set the token or production id

            self.rep_tok=rep   # Preserve the rep token, just in case
            if self.rep_tok is not None:
                self.repstr=rep.string
            else:
                self.repstr=None

        # These attribute will be set by the Grammar._parse() method or a subclass.
        self.typ="?"
        self.istid=False
        self.isprd=False

        # Repetitions of ID established by cvt_rep() method
        self.reptyp=None    # Rep type identifies the rep parser method
        self.min=None       # The minimum allowed repetitions
        self.max=None       # The maximum alloowd repetitions (may be None)

        # These attributes are also set by the Grammar._parse() method using the
        # Parser.idinit() method.  These methods link the ID to syntax analysis
        # performed by the Parser and its subclass
        #
        # The Parser recognizer method for this ID type
        self.rec=None       # This is a function object
        # The Parser language processor method for repetition recognizer
        self.rep=None       # This is the function object

        # Language processor call back method for a token and whether it is traced
        # the ID is traced.  Only TID type ID's use these attributes
        self.trace=False
        # PRD ID tracing is controlled by the trace attribute in the PRD and RH
        # triggered by the <trace> decorator in a production grammar statement.

        if self.repstr is not None:
            self.cvt_rep(self.repstr)
        else:
            self.cvt_rep(":1")

    def __str__(self):
        rec=CBM.mname(self.rec)
        rep=CBM.mname(self.rep)
        return "ID('%s',%s,min=%s,max=%s,rec=%s,rep=%s,trace=%s)" \
            % (self.tpid,self.typ,self.min,self.max,rec,rep,self.trace)

    def cvt_rep(self,string):
        if string=="*":
            self.min=0
            self.reptyp="*"
            self.repstr=string
        elif string=="+":
            self.min=1
            self.reptyp="+"
            self.repstr=string
        elif string=="?":
            self.min=0
            self.max=1
            self.reptyp="?"
            self.repstr=string
        elif string[0]==":":
            self.min=self.max=int(string[1:])
            self.reptyp=":"
            self.repstr=string
        else:
            raise ValueError("ID.cvt_rep() - invalid rep string: '%s'" % string)

# PRD - Defines a grammar production
class PRD(object):
    dummys=["_beg","_trying","_found","_failing","_end"]
    def __init__(self,pid,sync=[],flags=[]):
        self.pid=pid
        self.alts=[]      # One or more lists of ID instances
        self.sync=sync    # List of token types for resynchronization
        self.flags=flags  # Correspondin '+' flags of sync token
        self.ptrace=False # If any of the right hands are traced, so will the PRD
        
        # List of token types for resynchronization.  This is a list of tuples of
        # the form (True/False,tid).  The first element of the tuple indicates
        # whether the resynchronization token is to be consumed (True) or not
        # (False) when recognized during synchronization.  If the list is empty
        # the production does not perform resynchronization when recognition fails.
        # If resynchronization itself failes, a SyntaxError exception is raised.
        self.sync=sync

    def __str__(self):
        sync=string=''
        if len(self.sync)>0:
            for x in self.sync:
                sync="%s,'%s'" % (sync,x)
            sync=sync[1:]
            sync=",sync=[%s]" % sync
        string="PRD('%s'%s,trace=%s)" % (self.pid,sync,self.ptrace)
        for x in self.alts:
            string="%s\n    %s" % (string,x)
        return string

    # This method processes a right hand production
    def rhand(self,rh):
        if not isinstance(rh,RH):
            raise TypeError("parser.PRD.rhand() - rh must be an RH instance: %s" \
                % rh)
        if rh.trace:
            self.ptrace=True
        self.alts.append(rh)

# RH - A right hand side alternative of a production
class RH(object):
    def __init__(self,lst=[],trace=False):
        self.ids=lst   # List of ID instances defining this right hand alternative
        self.trace=trace  # Trace this alternative or not
    def __str__(self):
        string="RH(trace=%s [" % self.trace
        rh=""
        for x in self.ids:
            rh="%s, %s" % (rh,x)
        string="%s%s ] )" %(string,rh[1:])
        return string
    def define(self,lst=[]):
        self.ids=lst

# START - A subclass of ID representing the start production
class START(ID):
    def __init__(self,pid):
        super().__init__(pid,rep=None,string=True)
        self.ispid=True
        self.typ="PRD"

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
    def __init__(self):
        # Set of debug 'flags'.  See debug() and _isdebug() methods
        self.pdebug={}  # Set of debug 'flags', used to set debug options
        self.flag("pdebug")    # Parser debug flag
        self.flag("prdebug")   # Parser PRD debug flag
        self.flag("ldebug")    # Parser lexer's debug flag
        self.flag("tdebug")    # Parser lexer's token debug flag
        self.flag("edebug")    # Parser error generation debug flag
        self.flag("gdebug")    # Grammar processing debug flag
        self.flag("gldebug")   # Grammar processing lexer debug flag
        self.flag("gtdebug")   # Grammar processing token debug flag

        # These attributes are used to establish ID instance recognizers
        self.idrec={"TID":getattr(self,"_TID"),
                    "PRD":getattr(self,"_PRD") \
                   }
        self.idrep={"*":getattr(self,"_rep_0_or_more"),
                    "+":getattr(self,"_rep_1_or_more"),
                    "?":getattr(self,"_rep_0_or_1"),
                    ":":getattr(self,"_rep_n") \
                   }

        # This establishes callback manager and callback processing points
        self.cbm=CBM()
        # Add each processing point CB instance with default methods
        self.cbm.point( CB("beg",    default=self._beg)     )
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
        self.prds={}    # The production dictionary created by the grammar object
        self.sprd=None  # The ID instance corresponding to the start productions

        # Parse specific attributes
        self.stream=None # The Stream managing the token input stream.
        
        # Detect Left Recursion in productions to specified depth.
        self.depth=[]      # List of recursive pid's
        self.max_depth=0   # Maximum recursive pid's

    # Dummy language processor call back methods.  These are the expected method
    # signatures to be supported by an overridden subclass method.
    def _beg(self,gs,pid): pass
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
    def _PRD(self,ido,ppid,n,resync=False):
        pid=ido.tpid
        prod_err=[]      # Captured error objects for SyntaxError exceptions
        # Note this KeyError should not occur!  But we catch it just in case.
        try:
            prdo=self.prds[pid]  # Fetch the PRD instance
        except KeyError:
            raise ValueError("parser.Parser._PRD() - PRD object not found for "
                "ID instance: %s" % ido) from None

        # Detect left recursion in productions
        self.depth.append(pid)
        if len(self.depth)>=self.max_depth:
            print("Left recursion detected at depth: %s\nPID's:" % len(self.depth))
            for x in self.depth:
                print("   %s" % x)
            raise ValueError("Left recursion detected")

        ptrace=prdo.ptrace
        
        # Call back for start of production
        beg=self.cbm.method("beg",pid)
        if ptrace:
            begm=CMB.mname(beg)
            if len(begm)>0:
                print("%s(gs,%s)" % (begm,pid))
        beg(self.gs,pid)                 # Call back for start of production
        
        # Try the productions alternatives
        last=len(prdo.alts)-1
        error=True
        for x in range(len(prdo.alts)):
            alt_err=[]
            end=(x==last)
            alt=prdo.alts[x]   # alt is an RH instance
            tracing=alt.trace  # trace this alternative or not

            # Call back for altenative being tried
            trying=self.cbm.method("trying",pid)
            if tracing:
                tryingn=CBM.mname(trying)
                if len(tryingn)>0:
                    print("%s(gs,%s,%s,last=%s)" % (tryingn,pid,trying,x,end))
            trying(self.gs,pid,x,last=end)

            try:
                for i in alt.ids:
                    i.rep(i,pid,x)            # Recognize the number of id's

                # Call back for recognizing an alternative
                found=self.cbm.method("found",pid)
                if tracing:
                    foundn=CBM.mname(found)
                    if len(foundn)>0:
                        print("%s(gs,%s,last=%s)" % (foundn,x,end))
                found(self.gs,pid,x,last=end)    # Do callback for production alternative found

                error=False
                break
            # One of the ID's failed so the alternative failed
            except SyntaxError as se:
                eo=se.eo
                if self.isdebug("edebug"):
                    print("parser.Parser._PRD() - excepted SyntaxError.eo=%s" % eo)
                
                tok=self.stream.inspect(self.stream.current())
                d=len(self.depth)
                eo=ErrorProd(pid,n,depth=d,token=tok)
                alt_err.append(eo)
                
                # Do production alternative failure
                failing=self.cbm.method("failing",pid)
                if tracing:
                    failingn=CBM.mname(failing)
                    if len(failingn)>0:
                        print("%s(gs,%s,%s,eo=%s,last=%s)" \
                            % (failingn,pid,x,alt_err,end))
                res=failing(self.gs,pid,x,eo=alt_err,last=end)
                
                # If the callback method did not handle error objects, add them
                # to the list of production error failures
                if not res:
                    prod_err.extend(alt_err)
                    
                # Try the next production alternative
                continue
        
        # Call back for end of production
        if error:
            eolist=prod_err
        else:
            eolist=[]

        endm=self.cbm.method("end",pid)
        if ptrace:
            endn=CBM.mname(endm)
            if len(endn)>0:
                print("%s(%s,failed=%s,eo=%s)" % (endn,pid,error,eolist))
        res=endm(self.gs,pid,failed=error,eo=eolist)
        
        if error:
            # If error objects not handled by callback method, generate a 
            # ErrorProd instance and report it to the Error Manager.
            if not res:
                eo=self._production_error(pid,lst=eolist)
                if self.isdebug("edebug"):
                    print("parser.Parser._PRD() - reporting eo=%s" % eo)
                self.gs.mgr.report(eo)

            self.depth.pop()
            # do any optional resynching of the recognition process
            if resync and self._resynch(prdo.pid,lst=prdo.sync,flags=prdo.flags):
                return True

            raise SyntaxError(eo=eo)
            
        # Production recognized
        self.depth.pop()
        return False
        
    # Generate a ErrorProd instance for a production where all alternatives failed
    def _production_error(self,pid,lst=[]):
        if len(lst)==0:
            eo=ErrorProd(pid,None,depth=len(self.depth),token=None,
                source="_production_error")
            return eo
        first=lst[0]
        for x in range(1,len(lst)):
            item=lst[x]
            if Error.compare(first,item)==1:
                first=item
        eo=ErrorProd(pid,None,depth=len(self.depth),token=first.token,\
            source="_production_error")
        return eo

    # This is the recognizer for ID instances of type TID
    # This method is called from one of the repetition recognizers
    # Note, resync is ignored for TID's
    def _TID(self,ido,pid,n,resync=False):
        trace=ido.trace
        tid=ido.tpid
        if trace:
            print("seeking: %s" % tid)
        eos=self.stream.eos()
        if trace and eos:
            print("@ end of stream")
        if eos:
            raise SyntaxError()
        tok=self.stream.fetch()
        if trace:
            print("fetched: %s" % tok)
        if tid!=tok.tid:
            d=len(self.depth)
            eo=ErrorToken(pid,n,d,tid,tok,source="_TID")
            #self.gs.mgr.report(eo)
            if self.isdebug("edebug"):
                print("parser.Parser._TID - eo=%s" % eo)
            terror=self.cbm.method("error",pid)
            if trace:
                print("rejected token")
                terrorn=CBM.mname(terror)
                if len(terrorn)>0:
                    print("%s(gs,%s,%s,%s)" % (terrorn,pid,n,eo))
            terror(self.gs,pid,n,eo)
            self.stream.reset(tok)  # Cancel accept pending
            raise SyntaxError(eo=eo)
        self.stream.accept()
        
        token=self.cbm.method("token",pid)
        if trace:
            print("accepted token")
            tokenn=CBM.mname(token)
            if len(tokenn)>0:
                print("%s(gs,%s,%s,%s)" % (tokenn,pid,n,tok))
        token(self.gs,pid,n,tok)        # Do token callback for pid
        return False  # We never resync on TID's

    # "?" Repetition Recognizer - zero or 1 instances of PRD or ID
    # Returns a list of zero or more Syntax.Node instances
    def _rep_0_or_1(self,ido,pid,n):
        try:
            ido.rec(ido,pid,n,resync=False)  # Call TID or PRD recognizer
        except SyntaxError:
            pass

    # "*" Repetition Recognizer - zero or more instances of PRD or ID
    def _rep_0_or_more(self,ido,pid,n):
        current=self.stream.current()      # Remember the stream restart position
        while True:
            try:
                # Call TID or PRD recognizer.  Never resync in this case
                resync=ido.rec(ido,pid,n,resync=False) 
                current=self.stream.current()  # Advance the stream restart position
                if resync:
                    break
            except SyntaxError:
                # Resync stream following last recognized position
                self.stream.pos(current)
                break

    # "+" Repetition Recognizer - one or more instances of PRD or ID
    def _rep_1_or_more(self,ido,pid,n):
        number=0
        eo=None
        current=self.stream.current()      # Remember the stream restart position
        while True:
            try:
                # Call TID or PRD recognizer.  Resync only for first attempt
                resync=ido.rec(ido,pid,n,resync=number==0)
                # ID recognized or resync'ed.  Either way update the position
                current=self.stream.current()  
                if resync:
                    return
                number+=1
            except SyntaxError as se:
                eo=se.eo
                if self.isdebug("edebug"):
                    print("parser.Parser._rep_1_or_more() - SytaxError.eo=%s" % eo)
                # Resync stream following last recognized instance
                self.stream.pos(current)
                break
        if number==0:
            tok=self.stream.inspect(current)
            d=len(self.depth)
            eo=ErrorProd(pid,n,depth=d,token=tok,source="_rep_1_or_more")
            raise SyntaxError(eo=eo)

    # ":" Repetition Recognizer - x number of instances of PRD or ID
    # Consumes each occurrence of the ID encountered, but if the occurrence number
    # is not as expected, generate a syntax error.
    def _rep_n(self,ido,pid,x):
        n=ido.min  # The number of required occurrences
        number=0
        eo=None
        resync=False
        current=self.stream.current()      # Remember the stream restart position
        while number<n:
            try:
                # Call TID or PRD recognizer.  Always allow resynching in this case
                resync=ido.rec(ido,pid,x,resync=True)
                # Consume the recognized occurrence of the ID or resync
                current=self.stream.current()
                if resync:
                    return
                # If resync'ing did not occure, ID succeeded
                number+=1
            except SyntaxError as se:
                eo=se.eo
                if self.isdebug("edebug"):
                    print("parser.Parser._rep_n() - SytaxError.eo=%s" % eo)
                break
        if number!=n:
            # Resync stream following to position of last recognized occurrence
            # The recognized occurrences get "consumed"
            self.stream.pos(current)
            # BUT, because we did not find the number we expected, it is a
            # syntax error.
            tok=self.stream.inspect(current)
            d=len(self.depth)
            eo=ErrorProd(pid,x,depth=d,token=tok,source="_rep_n")
            raise SyntaxError(eo=eo)

    # This internal method performs resynchronization.
    def _resynch(self,pid,lst=[],flags=[]):
        # The list is a tuple of True/False and TID's
        if len(lst)==0:
            return False
        # Resynching is defined (and allowed or we would not be here)
        if self.stream.eos():
            print("Input stream resynchronized failed for production id '%s'.  "
                "Already at end of input." % pid)
            return False
        # Some input stream left, so lets try the resynchronization
        self.stream.resync()    # Prepare for resynching
        current=self.stream.current()   # Remember where resynching started
        first=None
        while True:
            if self.steam.eos():
                self.stream.pos(current)
                if first is not None:
                    print("[%s:%s] Input stream resynchronized failed for "
                        "production id '%s'.  Parsing contines here." \
                        % (first.line,first.linepos,pid,tok.tid))
                else:
                    print("Input stream resynchronized failed for "
                        "production id '%s'.  Already at end of input." % pid)
                return False
            tok=self.stream.fetch()
            if first==None:
                first=tok
            try:
                ndx=lst.index(tok.tid)
                # we have successfully found the resync token.
                # If flag set, accept the token
                if flags[ndx]:
                    self.stream.accept()
                    print("[%s:%s] Input stream resynchronized by production id "
                        "'%s' following token '%s' at this location" \
                        % (tok.line,tok.linepos,pid,tok.tid))
                # Otherwise, make it the next to be fetched
                else:
                    self.stream.resync()
                    print("[%s:%s] Input stream resynchronized by production id "
                        "'%s' at this token '%s'" \
                        % (tok.line,tok.linepos,pid,tok.tid))
            except IndexError:
                self.stream.accept()
                continue
        return False

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
            try:
                self.pdebug[x]
                self.pdebug[x]=True
            except KeyError:
                raise ValueError("%s.debug() - invalid debug flag: '%s'" \
                    % (self.__class__.__name__,x)) \
                    from None
        for x in kwds:
            new=kwds[x]
            print("parser.debug() - %s=%s" % (x,new))
            try:
                self.pdebug[x]
                if new:
                    self.pdebug[x]=True
                else:
                    self.pdebug[x]=False
            except KeyError:
                raise ValueError("%s.debug() - invalid debug flag: '%s'" \
                    % (self.__class__.__name__,x)) \
                    from None

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
        try:
            self.pdebug[dflag]
            raise ValueError("%s.flag() - debug flag already exists: '%s'" \
                % (self.__class__.__name__,dflag))
        except KeyError:
            self.pdebug[dflag]=False

    # This method is used to create the parser from a supplied lexer and grammar.
    # It is intended to called from a subclass init() method
    def generate(self,grammar,lexer,start):
        gdebug=self.isdebug("gdebug")
        gldebug=self.isdebug("gldebug")
        gtdebug=self.isdebug("gtdebug")
        self.go=Grammar(debug=gdebug,ldebug=gldebug,tdebug=gtdebug)
        self.go.lexer(lexer)
        pids=self.go.spec(grammar,self)
        self.setup(pids,lexer,start)

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
    def idinit(self,pid,ido):
        typ=ido.typ
        # Set up recognizer methods
        ido.rec=self.idrec[typ]  # The recognizer method for the ID
        ido.rep=self.idrep[ido.reptyp] # Rep recognizer method for ID

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
        try:
            switch=self.pdebug[flag]
            if switch:
                return True
            return False
        except KeyError:
            raise ValueError("%s.isdebug() - undefined flag encountered: %s" \
                % (self.__class__.__name__,flag)) \
                from None

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
        self.max_depth=depth
        self.depth=[]
        self.stream=Stream(self)
        self.stream.tokens(string,lines=lines,fail=fail)
        self.sprd.rep(self.sprd,None,0)  # Do the START ID

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
        for x in self.prds.keys():
            pids.append(x)
        pids.sort()
        for x in pids:
            prd=self.prds[x]
            print("%s" % prd)

    # Establish and valiate all of the components are present.
    # Method arguments:
    #    prds    A dictinary of PRD instances.  It may be manually created or
    #            established with a grammar using the generate() method
    #    lexer   A lexer.Lexer instace used to recognize token types by the parser
    #    start   The production id of the initial starting production
    def setup(self,prds,lexer,start):
        self.prds=prds
        self.lex=lexer
        try:
            sprd=self.prds[start]
            self.sprd=START(start)
            self.idinit(None,self.sprd)
        except KeyError:
            pass
        if self.sprd is None:
            raise ValueError(\
                "%s.setup() - start production not defined by grammar: %s"\
                % (self.__class__.__name__,start))
        if (self.go is not None) and self.go.errors:
            raise ValueError(\
                "%s.setup() - errors encountered in parser grammar: %s"\
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
    raise NotImplementedError("parser.py - must only be imported")
