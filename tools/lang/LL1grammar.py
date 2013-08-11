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
from parser import CBM   # Access Callback Manager static methods

# +--------------------------------+
# |  Exceptions Raised by Grammar  |
# +--------------------------------+

# This exception is raised any time the Parser encounters an error.
# Instance arguments:
#   tok      The token triggering the error.  Default is None.
#   msg      A message associated with the error.  Default is "".
class GrammarError(Exception):
    def __init__(self,tok=None,msg=""):
        self.tok=tok         # The token in error
        self.msg=msg         # Error message
        super().__init__(self.msg)

# +---------------------------+
# |  LL(1) Grammar Processor  |
# +---------------------------+

# GLexer - the lexer used by the Grammar class
class GLexer(lexer.Lexer):
    def __init__(self,debug=False,tdebug=False):
        self.gdebug=debug
        self.tdebug=tdebug
        super().__init__()

    # Initialize the lexer
    def init(self):
        tdebug=self.tdebug
        self.type(lexer.Type("name",r"([a-zA-Z][a-zA-Z0-9_]*)([\*]?)([!]?)",\
            mo=True,debug=tdebug))
        self.type(lexer.Type("decorator",r"<[^ \t\r\f\v\n>]+>",debug=tdebug))
        #self.type(lexer.Type("rep",r"[\*]?()?",debug=tdebug))
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
    def __init__(self,debug=False,ldebug=False,tdebug=False,LL1debug=False):
        self.debug=debug
        self.LL1debug=LL1debug  # Debug LL(1) analysis

        self.lex=None      # Instance of lexer.Lexer supplied by lexer() method
        self.prods=None    # Instance of LL1Prods created by lexer() method
        self.gp=None       # Instance of GrammarPY created by spec() method

        # Attributes used by to process the production definitions. See spec()
        self.glexer=GLexer(debug=ldebug,tdebug=tdebug).init()
        self.glines=None   # List of tokenized lines
        self.startid=None         # Grammar start ID based upon start PID
        self.specification=None   # Parser provided grammar
        self.parser=None          # Parser providing the grammar

        # See self.lexer() method
        self.prods=None     # Instance of LL1Prods created

        # Global error counter.  It is expected that the Parser will detect these
        # errors.  This class only records the occurrence of the errors.
        self.errors=0

    # The internal method parses a set of tokens from a tokenized line for valid
    # grammar syntax.
    #
    #          name rhand ( name rep? )+ decorator*
    # states 0     1       2    3       4          4
    #
    # It returns a PRD instance corresponding to the defined production
    def __parse(self,line):
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
            # Now that we are not using the "rep" token this state can be
            # callapsed into state 2. And state 4 becomes 3.
            elif state==3: # Target token id found
                if x.istype("name"):
                    # Flush the pending ID creation
                    rh.append( ID(tpid) )
                    tpid=x
                    state=3
                    continue
                #elif x.istype("rep"):
                #    rh.append( ID(tpid,rep=x) )
                #    tpid=None
                #    state=2
                #    continue
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
            raise GrammarError()
        rh=RH(lh,lst=rh)  # Create the RH instance

        # Process decorators:
        for x in decorators:
            if self.debug:
                print("%s._parse(): decorator=%s" % (thisclass,x))
            dec=x.string
            if len(dec)<3:
                print("[%s:%s] invalid decorator identified by GLexer: '%s'"\
                    % (x.line,x.linepos,dec))
                raise GrammarError()
            #if dec[1]=="!":
            #    r=dec[2:-1]
            #    a=False
            #    if r[-1]=="+":
            #        a=True
            #        r=r[:-1]
            #    if len(r)==0:
            #        print("[%s:%s] resynchronization token missing from decorator" \
            #            % (x.line,x.linepos))
            #        self.errors+=1
            #    else:
            #        #if not self.prods.isTID(r):
            #        if not self.gp.isTID(r):
            #            print("[%s:%s] unrecognized resynchronization token type: "
            #                "'%s'" % (x.line,x.linepos,r))
            #            self.errors+=1
            #        else:
            #            sync.append(r)
            #            syncflag.append(a)
            #    continue
            if dec == "<trace>":
                trace=True
                continue
            print("[%s:%s] unrecognized decorator: '%s'" \
                % (x.line,x.linepos,dec))

        # Make sure production does not conflict with a token id
        if self.gp.isTID(lh.string):
            self.errors+=1
            print(\
                "[%s:%s] left hand production id conflicts with token id: %s"\
                % (lh.line,lh.linepos,ls.string))
            raise GrammarError()

        # Initialize the ID instance for use by the parser
        for x in rh.ids:
            if self.gp.isTID(x.tpid):
                x.istid=True
                x.typ="TID"
                x.trace=trace
                x.empty=self.gp.isEmpty(x.tpid)
            else:
                x.isprd=True
                x.typ="PRD"
        rh.trace=trace

        prd=PRD(lh.string,sync=sync,flags=syncflag)
        prd.rhand(rh)
        if self.debug:
            print("%s" % prd)
        return prd

    # Generic internal method for printing unexpected token messages
    def _unexpected(self,tok):
        self.errors+=1
        print("[%s:%s] unexpected '%s' token in production: '%s'" \
            % (tok.line,tok.linepos,tok.tid,tok.string))

    # This method identifies the lexer.Lexer instance used by the parser.  The lexer
    # must be identified before any productions are associated with the Parser.
    def lexer(self,lex):
        if not isinstance(lex,lexer.Lexer):
            raise ValueError("LL1grammar.py - lexer() - 'lex' argument must be "
                "an instance of lexer.Lexer: %s" % lexer)
        self.lex=lex
        #self.prods=LL1Prods(lex,debug=self.LL1debug)

    # This method processes a grammar specification creating a dictionary of PRD
    # instances.  The PRD instances contain ID instances linked to the parser
    # for processing.
    def spec(self,start,string,parser):
        if not isinstance(start,str):
            raise ValueError("LL1grammar.py - Grammar.spec() - 'start' argument "
                "must be a string" % start)
        self.startid=START(start)       # The START ID instance
        self.parser=parser              # The parser for which the grammar is used
        self.gp=GrammarPy(self.lex,parser,self.startid)
        self.specification=string       # Grammar as a string
        self.glines=[]                  # Individual lines of the spec.
        aline=[]

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

        for x in self.glines:
            try:
                prd=self.__parse(x)
                self.gp.append(prd)
            except GrammarError:
                continue

        #self.prods=LL1Prods1(self.gp,debug=self.LL1debug)
        self.prods=LL1Prods2(self.gp,debug=self.LL1debug)
        self.prods.validate()  # Check out and process the productions

        return self.prods  # Return this to the Parser

# This class manages access to the grammatical elements recognized by the 
# Grammar class.  It includes various access methods on the grammar.  This 
# object is acted upon by the LL1Prods object in creating its various relation
# ships.  The productions are added to the object as they are recognized by 
# the Grammar object.
#
# These three classes have the following roles and are accessed from this object
#
#  PRD   An instance of the PRD class is associated with each unique production
#        identifier occurring in the input grammar.
#  RH    An instance of the RH class is associated with each alternative right-
#        hand side of a production.  Each instance is associated with its left-
#        hand PID by being part of a list or RH instances maintained by the 
#        PRD class.
#  ID    An instance of the ID class is associated with each grammatical terminal
#        and non-terminal occurring in the right-hand portion of a production.
#        The RH instance representing the right-hand side of a production maintains
#        a list of its ID instances.  Each ID instance knows if it is associated
#        with a terminal by having it typ attribute set to "TID" or a not-terminal
#        by having its typ attribute set to "PRD".
#
# To illustrate with an example production:
#
#       +-------------- 
#       |           <---RH------>
#       |   pid0  ->  T1 nt1 T2    # pid0 first alternative
#  PRD -+
#       |   pid0  ->  T3           # pid0 second alternative
#       |           <-RH->
#       +--------------
#
#  This is transformed by the Grammar class into:
#
#                                         [0]    [1]
#     PRD("pid0") with right-hand list: [ RH(), RH() ]
#        RH list entry [0] has this ID list [ ID("T1"), ID("nt1"), ID("T2") ]
#        RH list entry [1] has this ID list [ ID("T3"), ] 
#
# Instance arguments:
#   lex      The lexer.Lexer object that will perform lexical analysis
#   start    The START ID instance of the starting non-terminal
#  
class GrammarPy(object):
    def __init__(self,lex,parser,start):
        if not isinstance(lex,lexer.Lexer):
            raise ValueError("LL1grammar.py - GrammarPy() - 'lex' argument must "
                "be an instance of lexer.Lexer: %s" % lex)
        if not isinstance(start,START):
            raise ValueError("LL1grammar.py - GrammarPy() - 'start' argument must "
                "be an instance of START: %s" % start)
        self.lex=lex         # lexer.Lexer defining terminal symbols.
        self.parser=parser   # parser.Parser using the grammar
        
        # Values extracted from the input objects
        self.start_id=start              # ID instance of start
        self._tids=lex.tids               # A list of terminal id's (TID's).
        self.tidempty=lex.empty_tid()    # TID of empty token type
        self.tideos=lex.eos_tid()        # Get the TID of the EOS token
        # Values supplied while grammar is being recognized by Grammar object
        self._pids=[]       # List of PID's as encountered by Grammar object
        self._prds=[]       # List of PRD instances corresponding to PID's
        self.prods={}       # PRD's with merged alternatives, key is PID

    # Add a production to this object.
    def append(self,prd):
        if not isinstance(prd,PRD):
            raise ValueError("LL1grammar.py - GrammarPy.append() - 'prd' argument "
                "must be an instance of PRD: %s" % prd)
        pid=prd.pid
        try:
            p=self.prods[pid]
            for alt in prd.alts:
                p.rhand(alt)
        except KeyError:
            self.prods[pid]=prd
            self._pids.append(pid)
            self._prds.append(prd)
            
    # Return a production RH instance based upon PID and alternative number
    def alt(self,pid,n):
        return self.pid(pid).alts[n]
        
    def alts(self,pid):
        p=self.pid(pid)
        return p.alts
            
    # Returns the Empty symbol token type.
    def Empty(self):
        return self.tidempty
            
    # Returns the ID of the EOS token type.
    def EOS(self):
        return self.tideos
            
    # Tests whether the supplied list of ID instances or right-hand alternative
    # has the empty string.  Returns True if it does, False otherwise.
    # Note: This should be detected on the first element of the list of ID's for RH
    # instances.
    def hasEmpty(self,lst):
        if isinstance(lst,RH):
            l=lst.ids
        elif isinstance(lst,List):
            l=lst.tids
        elif isinstnace(lst,list):
            l=lst
        else:
            raise ValueError("LL1grammar.py - GrammarPy.hasNT() - 'lst' "
                "argument must be either a list, instance of RH or List: "
                "%s" % lst) 
        for x in l:
            if self.isEmpty(x):
                return True
        return False
        
    # Tests whether a list of ID instances or a right-hand alternative has any
    # PID's.  Returns True if it does, False otherwise
    def hasNT(self,lst):
        if isinstance(lst,RH):
            l=lst.ids
        elif isinstnace(lst,list):
            l=lst
        else:
            raise ValueError("LL1grammar.py - GrammarPy.hasNT() - 'lst' "
                "argument must be either a list or instance of RH: %s" % lst) 
        for x in l:
            if self.isNT(x):
                return True
        return False
            
    # Tests whether a list of ID instances or a right-hand alternative has any
    # terminals.  Returns True if it does, False otherwise
    def hasT(self,lst):
        if isinstance(lst,RH):
            l=lst.ids
        elif isinstnace(lst,list):
            l=lst
        else:
            raise ValueError("LL1grammar.py - GrammarPy.hasNT() - 'lst' "
                "argument must be either a list or instance of RH: %s" % lst) 
        for x in l:
            if self.isT(x):
                return True
        return False
            
    def id(self,pid,n,x):
        return self.alt(pid,n).ids[x]
        
    # Let the parser initialize the ID object as it needs.
    def idinit(self,ido):
        self.parser.idinit(ido,empty=self.isEmpty(ido))

    def ids(self,pid,n):
        p=self.alt(pid,n)
        return p.ids
            
    # Tests whether the name or ID instance is the empty string
    def isEmpty(self,name):
        if isinstance(name,ID):
            n=name.tpid
        elif isinstance(name,str):
            n=name
        else:
            raise ValueError("LL1grammar.py - GrammarPy.isEmpty() - 'name' "
                "argument must be either a string of instance of ID: %s" % name)
        return n==self.tidempty

    # Tests whether the name or ID instance is the EOS token type.
    def isEOS(self,name):
        if isinstance(name,ID):
            n=name.tpid
        elif isinstance(name,str):
            n=name
        else:
            raise ValueError("LL1grammar.py - GrammarPy.isEmpty() - 'name' "
                "argument must be either a string of instance of ID: %s" % name)
        return n==self.tideos

    # Tests whether a name or ID instance is a non-terminal
    def isNT(self,name):
        if isinstance(name,ID):
            n=name.tpid
        elif isinstance(name,str):
            n=name
        else:
            raise ValueError("LL1grammar.py - GrammarPy.isNT() - 'name' "
                "argument must be either a string of instance of ID: %s" % name)
        return n in self._pids

    # Tests whether the supplied name or ID instance is a terminal
    def isT(self,name):
        # Note: the Lexer includes the Empty token types' TID in its list.
        # For grammatical analysis, the Empty TID is _not_ a terminal
        if self.isEmpty(name):
            return False
        if isinstance(name,ID):
            n=name.tpid
        else:
            n=name
        return n in self._tids
        
    # Tests whether the supplied name or ID instance is a TID
    def isTID(self,name):
        # Note: the Lexer includes the Empty token types' TID in its list.
        # For grammatical analysis, the Empty TID is _not_ a terminal
        if isinstance(name,ID):
            n=name.tpid
        elif isinstance(name,str):
            n=name 
        else:
            raise ValueError("LL1grammar.py - GrammarPy.isTID() - 'name' "
                "argument must be a string or instance of ID: %s" % name)
        return n in self._tids
        
    # Iterate on alternatives: yields (index,RH instance)
    # Used in:   for ndx,rh in GrammarPY.iter_alts(pid):
    def iter_alts(self,pid):
        if isinstance(pid,PRD):
            p=pid
        else:
            p=self.pid(pid)
        return p.alts
        
    # Return iterable of ID instances from PID and alternative number or an 
    # RH instance
    def iter_ids(self,item,n=None):
        if isinstance(item,RH):
            rh=item
        else:
            if n is None:
                raise ValueError("LL1grammar.py - GrammarPY.iter_ids() - 'n' "
                    "argument required when 'item' is not a RH instance: %s" \
                    % item)
            rh=self.alt(pid,n)
        return rh.ids
        
    # Return iterable of PID strings
    def iter_pids(self):
        return self._pids
        
    # Return iterable of TID strings 
    # The iterables imcludes the empty TID if the 'empty' argument is True.
    def iter_tids(self,empty=False):
        lst=[]
        for x in self._tids:
            if (not empty) and self.isEmpty(x):
                continue
            lst.append(x)
        return lst
        
    # Return iterable of PRD instances
    def iter_prods(self):
        return self._prds
        
    # Return a PRD instance based upon its PID
    def pid(self,pid):
        return self.prods[pid]
        
    # Return the start PID
    def start(self):
        return self.start_id.tpid
            
# A class that manages lists of TID strings.  This class ensures the list
# does not contain duplicates.
#
# A subset of sequence operations are supported: indexing by offset (but not 
# slicing), iteration and len() built-in.  The mutable list operations append(),
# extend() and index are suppored.  When a list extends or an item appends to the
# list, duplicate TID's are ignored.
class List(object):
    def __init__(self,items=[]):
        # This list is used to detect duplicate TID's.  Duplicates are ignored.
        # A tid in this list more than once does not matter
        self.tids=[]     # List of TID's of the LL1Term instances
        
        # Instances supplied when the 'list' is created are added here.
        if isinstance(items,list):
            if len(items)>0:
                self.extend(items)
        else:
            self.append(items)

    def __contains__(self,item):
        if not isinstance(item,str):
            raise ValueError("LL1grammar.py - List.__contains__() - "
                "'item' argument must be a string: %s" % item)
        return item in self.tids

    # Deletes an element from the list.  It assumes the value has been returned
    # by the index() method.
    def __delitem__(self,index):
        del self.tids[index]

    def __getitem__(self,index):
        return self.tids[index]

    def __len__(self):
        return len(self.tids)

    def __setitem__(self,key,value):
        self.tids[key]=value
        
    def __str__(self):
        return self.print()
        
    # Adds a new LL1Term instance to the list.  Duplicate TID's are ignored.
    def append(self,item):
        if not isinstance(item,str):
            raise ValueError("LL1grammar.py - List.append() - 'item' "
                "argument must be a string: %s" % item)
        if item in self.tids:
            return
        self.tids.append(item)
        
    # Same as append but returns True if the list was changed, False otherwise.
    def cappend(self,item):
        if not isinstance(item,str):
            raise ValueError("LL1grammar.py - List.cappend() - 'item' "
                "argument must be a string: %s" % item)
        if item in self.tids:
            return False
        self.tids.append(item)
        return True
        
    # Same as extend but returns True if the list was changed, False otherwise.
    def cextend(self,lst):
        if isinstance(lst,List):
            l=lst.tids
        elif isinstance(lst,list):
            l=lst
        else:
            raise ValueError("LL1grammar.py - List.cextend() - 'lst' "
                "argument must be a list or instance of List: %s" % lst)
        changed=False
        for x in l:
            changed|=self.cappend(x)
        return changed
        
    # Extends the list of LL1Term instances with the supplied list or another
    # instance of List.
    def extend(self,lst):
        if isinstance(lst,List):
            l=lst.tids
        elif isinstance(lst,list):
            l=lst
        else:
            raise ValueError("LL1grammar.py - List.extend() - 'lst' "
                "argument must be a list or instance of List: %s" % lst)
        for x in l:
            self.append(x)
           
    # Returns the index of the item supplied or raises ValueError
    def index(self,item):
        if not isinstance(item,str):
            raise ValueError("LL1grammar.py - List.index() - 'item' "
                "must be a string : %s" % item)
        return self.tids.index(item)
        
    # Returns an iterable list of the List contents
    def iter(self):
        return self.tids
        
    # Return a string suitable for printing of the list
    def print(self,indent=""):
        slist=sorted(self.tids)
        return "%s%s" % (indent,slist)
        
    # Remove an entry from the list
    def remove(self,item,change=False):
        if not isinstance(item,str):
            raise ValueError("LL1grammar.py - List.remove() - 'item' "
                "must be a string: %s" % item)
        try:
            ndx=self.index(item)
        except ValueError:
            if change:
                return False
            return None
        self.__delitem__(ndx)
        if change:
            return True
        return None

# This class is used to manage productions and perform the various analysis for
# a valid grammar and production alternative selections needed by a parser.  After
# the Grammar class has processed a grammar specification, this class takes 
# responsibility for all validation and required processing  allowing parsing by 
# a parser.
#
# Experience has demonstrated the need to allow grammar processing for a parser
# to use different algorithms for analysis.  This class is the base class
# for such handling.
#
# This class in essence performs the semantic analysis of the supplied grammer, on 
# which the Grammar class performs syntactical analysis.  The PRD, RH and ID
# instances encapsulated by the GrammarPy class take on the role of an abstract 
# syntax tree for recognizing a domain specific language recognized by the Grammar
# class itself.  Turning this internal representation into one usable by a is the 
# responsibility of a subclass of this grammar.
#
# Instance arguments:
#   gp        The GrammarPy instance that is the internal representation of the
#             grammar recognized by the Grammar class.
#   debug     Enable debugging.  (Note: set the same as Grammar debug flag)
#
# Instance methods:
#   validate  Method supplied by a subclass to perform analysis of the recognized
#             grammar.
class Prods(object):
    def __init__(self,gp,debug=False):
        self.debug=debug    # Debug flag

        if not isinstance(gp,GrammarPy):
            raise ValueError("LL1grammar.py - Prods.__init__() - 'gp' argument "
                "must be an instance of GrammarPy: %s" % gp)
        if gp.tideos is None:
            raise ValueError("LL1grammar.py - Prods1 - lexical analyzer must "
                "provide EOS token")
        self.gp=gp  # This object manages access to the grammar
        
        # Lexical analyzer information required for production analysis.
        self.start_id=self.gp.start_id     # Start ID instance
        self.pid_start=self.start_id.tpid  # Start PID
        
        # sanity check results:
        self.sck1=0          # Errors encountered by sanity check 1.
        self.sck2=0          # Errors encountered by sanity check 2.
        
        self.alive=[]        # Alive non-terminals, found by alive()
        self.ambigous=[]     # Ambiguous non-terminals.  found by director()
        self.dead=[]         # Dead non-terminals, found by __alive()
        self.reachable=[]    # Reachable non-terminals, found by __reachable()
        self.unreachable=[]  # Unreachable non-terminals, found by __reachable()

    # Determine the productions that are alive or dead
    def __alive(self):
        alive=[]   # List of alive non-terminals (PID's)
        # Identify all of the non-terminals (PID) with at lease one alternative
        # that has no non-terminals.  These are already known to be alive.
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for rh in prd.alts:
                if (not self.gp.hasNT(rh)) and (pid not in alive):
                    alive.append(pid)
            if pid in alive:
                prd.alive=True
        
        # Analyze all of the right-hand alternatives, repeatedly, looking for
        # an alternative in a not-alive production that has all of its non-
        # terminals alive.  This non-terminal is also alive.
        while True:
            added=0
            for prd in self.gp.iter_prods():
                if prd.alive:
                    continue
                pid=prd.pid
                for rh in prd.alts:
                    nts=0
                    alive_nt=0
                    for ido in rh.ids:
                        if ido.typ=="TID":
                            continue
                        nts+=1
                        if ido.tpid in alive:
                            alive_nt+=1
                    # All of the non-terminals are alive
                    if (alive_nt==nts) and (pid not in alive):
                       prd.alive=True
                       alive.append(pid)
                       added+=1
                       break
            if not added:
                break
                
        dead=[]
        for prd in self.gp.iter_prods():
            if not prd.alive:
                dead.append(prd.pid)
                print("LL1grammar.py - LL1Prods1.__alive() - WARNING: PID '%s' is "
                    "dead")
        for pid in dead:
            if pid in alive:
                # This should not happen
                print("LL1grammar.py - LL1Prods1.__alive() - INTERNAL: pid '%s' "
                    "marked dead but in alive list!" % pid)
        for pid in alive:
            prd=self.gp.pid(pid)
            if not prd.alive:
                # This should also not happen
                print("LL1grammar.py - LL1Prods.__alive() - INTERNAL: pid '%s' "
                    "in the alive list not marked as alive!" % pid)
        self.alive=alive
        self.dead=dead

    def __reachable(self):
        reachable=[self.pid_start,]   # Start symbol is always reachable

        # Analyze all of the right-hand alternatives, repeatedly, looking for
        # an alternative in a not-alive production that has all of its non-
        # terminals alive.  This non-terminal is also alive.
        while True:
            added=0
            for prd in self.gp.iter_prods():
                pid=prd.pid
                isreachable=pid in reachable
                for rh in prd.alts:
                    for ido in rh.ids:
                        if ido.typ=="TID":
                            continue
                        # Because my left hand non-terminal is reachable, 
                        # so are all of my non-terminals.
                        nt=ido.tpid
                        if nt not in reachable:
                            reachable.append(nt)
                            added+=1
            if not added:
                break
                
        unreachable=[]
        for prd in self.gp.iter_prods():
            pid=prd.pid
            if pid in reachable:
                prd.reachable=True
                continue
            unreachable.append(pid)
        
        self.reachable=reachable
        self.unreachable=unreachable

    # Checks that all of the non-terminal PID's have a defined production.
    # A missing production can occur when a TID is incorrectly coded causing the
    # id string to be interpreted as a PID, creating a PID without any production 
    # alternatives.
    def __sanity_check1(self):
        eos_found=False
        tids=0
        for prd in self.gp.iter_prods():
            #print("prd=%s" % prd)
            pid=prd.pid
            for rh in prd.alts:
                # rh is a single right-hand alternative
                for tpid in rh.ids:
                    # tpid is an ID instance
                    if tpid.isprd:
                        try:
                            name=tpid.tpid
                            self.gp.pid(tpid.tpid)
                        except KeyError:
                            tok=tpid.id_tok
                            line=tok.line
                            pos=tok.linepos
                            self.sck1+=1
                            print("[%s:%s] encountered undefined production: %s" \
                                % (line,pos,name))
                    elif tpid.istid:
                        tids+=1
                        if self.gp.isEOS(tpid):
                            tok=tpid.id_tok
                            line=tok.line
                            pos=tok.linepos
                            self.sck1+=1
                            print("[%s:%s] end-of-string encounered in "
                                "production: %s" % (line,pos,pid))
                    else:
                        self.sck1+=1
                        tok=tpid.id_tok
                        print("[%s:%s] token type '%s' not classified as "
                            "PRD or TID, recognized string: '%s'" \
                            % (tok.line,tok.linepos,tok.tid,tok.string))
        try:
            sid=self.gp.start_id.tpid
            s=self.gp.pid(sid)
        except KeyError:
            self.sck1+=1
            print("start production is not defined: '%s'" % sid)
        if not tids:
            self.sck1+=1
            print("error: no TID's found in productions")

        if self.sck1:
            raise ValueError("LL1grammar.py - LL1Prods.sanity_check1() - "
                "productions did not pass sanity check 1")
        
    # Make sure alternatives that have the 'empty' tid only contain that one id
    # and set flag for PID non-terminal has an empty alternative.
    def __sanity_check2(self):
        for prd in self.gp.iter_prods():
            #for ndx in LL1Prods.RL(prd.alts):
            for ndx in range(len(prd.alts)):
                alt=prd.alts[ndx]
                # alt is an instance of RH (right hand)
                ids=alt.ids  # This is the alternative ID list
                if len(ids)==0:
                    lhtok=alt.lhtok
                    print("[%s:%s] INTERNAL ERROR: production alternative of PID "
                        " has no terminals or non-terminals" \
                            % (lhtok.line,lhtok.linepos,prd.pid))
                    self.sck2+=1
                elif len(ids)==1:
                    i=ids[0]
                    if self.gp.isEmpty(i.tpid):
                        prd.isempty=True
                        alt.isempty=True
                        i.isempty=True
                else:
                    for i in ids:
                        # i is an indivdual ID instance
                        if self.gp.isEmpty(i.tpid):
                            emtok=i.id_tok
                            self.sck2+=1
                            print("[%s:%s] production alternative of PID '%s' "
                                "contains an empty token with other terminals " 
                                "and/or non terminals" \
                                % (emtok.line,emtok.linepos,alt.lhpid))
                            
        if self.sck2:
            raise ValueError("LL1grammar.py - LL1Prods.sanity_check2() - "
                "productions did not pass sanity check 2")

    # The algorithms used by this class when detecting whether the grammar is 
    # LL(1) assumes that only non-terminals are nullable and terminals never are.
    # The Grammar class allows for terminals to be tagged with the '*' or '?' 
    # attribute.  Both of these constructs produce nullable results.  Hence, they
    # are prohibited within an LL(1) grammar, although allowed by the simple
    # grammar language processed by the Grammar class.  This method ensures that
    # no nullable TERMINALS exist in the grammar.
    def __sanity_check3(self):
        self.sck3=0
        for prd in self.gp.iter_prods():
            for ndx in range(len(prd.alts)):
                alt=prd.alts[ndx]
                # alt is an instance of RH (right hand)
                ids=alt.ids  # This is the alternative ID list
                for idn in range(len(ids)):
                    ido=ids[idn]
                    if not self.gp.isTID(ido):
                        continue
                    if ido.reptyp in "*":
                        print("[%s:%s] replication type '%s' is invalid for TID, "
                            "'%s', replace with nullable non-terminal PID" \
                            % (ido.rep_tok.line,ido.rep_tok.linepos,ido.reptyp,\
                               ido.tpid))
                        self.sck3+=1
        if self.sck3:
            raise ValueError("LL1grammar.py - LL1Prods.sanity_check3() - "
                "TID's did not pass sanity check 3")

    def director(self):
        ambiguous=[]
        for prd in self.gp.iter_prods():
            # Build the DIRECTOR set
            ambig={}
            ds=prd.ds
            pid=prd.pid
            for rhn in range(len(prd.alts)):
                rh=prd.alts[rhn]
                select=rh.select
                for tid in select:
                    try:
                        ds_lst=ds[tid]
                    except KeyError:
                        ds_lst=[]
                    ds_lst.append(rhn)
                    ds[tid]=ds_lst

            # Examine DIRECTOR set for ambiguous alternatives and complete 
            # non-terminal's DIRECTOR set dictionary.
            for tid in ds.keys():
                ds_lst=ds[tid]
                if len(ds_lst)==0:
                    raise ValueError("LL1grammar.py - LL1Prods1.__director() - "
                        "INTERNAL: PID %s director set for TID %s has no "
                        "alternatives" % (pid,tid))
                elif len(ds_lst)==1:
                    ds[tid]=ds_lst[0]
                else:
                    ambig[tid]=ds_lst

            # Save ambiguous data for reporting
            if len(ambig)!=0:
                prd.ambig=ambig
                prd.ambigous=True
                ambiguous.append(pid)

        self.ambiguous=ambiguous

    def print_alive(self):
        print("\nALIVE NON-TERMINALS: %s" % self.alive)

    def print_ambigous(self):
        print("\nAMBIGUOUS NON-TERMINALS: %s" % self.ambiguous)

    def print_dead(self):
        print("\nDEAD NON-TERMINALS: %s" % self.dead)

    def print_director(self):
        string="\nDIRECTOR Sets:\n"
        for prd in self.gp.iter_prods():
            string="%s%s\n" % (string,prd.print_director())
        print(string[:-1])

    def print_first(self,details=False):
        string="\nFIRST Sets:\n"
        for prd in self.gp.iter_prods():
            string="%s%s\n" % (string,prd.print_first(details=details))
        print(string[:-1])

    def print_follow(self,details=False):
        string="\nFOLLOW Sets:\n"
        for prd in self.gp.iter_prods():
            string="%s%s\n" % (string,prd.print_follow(details=details))
        print(string[:-1])

    def print_reachable(self):
        print("\nREACHABLE NON-TERMINALS: %s" % self.reachable)

    def print_unreachable(self,details=False):
        print("\nUNREACHABLE NON-TERMINALS: %s" % self.unreachable)

    def sanity_checks(self):
        self.__sanity_check1()
        self.__sanity_check2()
        self.__sanity_check3()

    def sensible(self):
        self.__alive()
        if self.debug:
            self.print_alive()
        if self.debug or len(self.dead)>0:
            self.print_dead()
        self.__reachable()
        if self.debug:
            self.print_reachable()
        if self.debug or len(self.unreachable)>0:
            self.print_unreachable()
        if len(self.dead)>0 or len(self.unreachable)>0:
            raise ValueError("LL1grammar.py - Prods.semsible() - grammar "
                "processing terminated due to presence of dead or unreachable "
                "non-terminals")

    def validate(self):
        raise NotImplementedError("LL1Prods subclass %s must provide the "
            "validate() method" % self.__class__.__name__)

# The director set for the grammar drives the selection of alternatives by an
# LL(1) parser, but identifying the next input symbol that will select a
# production alternative (and conversely, identify incorrect input).
#
# Determining the Director set for each non-terminal is a multiple step process.
# The algorithms used here are those described in "Compiler Design Theory" by 
# Philip M. Lewis II, Daniel J. Rosenkrantz, and Richard E. Stearns, published 
# by Addison-Wesley Publishing Company of Reading, Massachusetts in 1978.
#
# Instance arguments: see class Prods.
class LL1Prods1(Prods):
    def __init__(self,gp,debug=False):
        super().__init__(gp,debug=debug)

        # Keys used to access a LL1Relationship matrix. Includes the EOS symbol
        # even though the LL(1) analysis does not consider EOS to be a terminal
        # or non-terminal.  It is needed for IS-END-OF relationship
        self.rkeys=[]
        for pid in self.gp.iter_pids():
            self.rkeys.append(pid)
        for tid in self.gp.iter_tids():
            self.rkeys.append(tid)

        # sanity check results:
        self.sck1=0          # Errors encountered by sanity check 1.
        self.sck3=0          # Errors encountered by sanity check 3.
        
        # Results of analysis:
        #self.alive=[]        # Alive non-terminals, found by __alive()
        #self.ambigous=[]     # Ambiguous non-terminals.  found by __director()
        #self.dead=[]         # Dead non-terminals, found by __alive()
        self.nullable=[]     # Nullable non-terminals, found by __nullable()
        #self.reachable=[]    # Reachable non-terminals, found by __reachable()
        #self.unreachable=[]  # Unreachable non-terminals, found by __reachable()
        self.bdw=None        # Begins-directly with relationship.
        self.bw=None         # Begins-with relationship
        self.deo=None        # Direct-end-of relationship
        self.fb=None         # Followed-by relationship
        self.fb_eos=None     # Followed-by relationship with EOS information
        self.fdb=None        # Follows-directly-by relationship
        self.ieo=None        # Is-end-of relationship

    def __begins_directly_with(self):
        br=LL1Relationship(keys=self.rkeys)
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for rh in prd.alts:
                # Examine each alternative's terminals and non-terminals
                for ido in rh.ids:
                    if self.gp.isEmpty(ido):
                        continue
                    br.set(pid,ido.tpid,True)
                    if not ido.nullable:
                        break
        self.bdw=br

    def __begins_with(self):
        self.bw=self.bdw.clone()
        self.bw.closure(reflexive=True)

    def __direct_end_of(self):
        deo=LL1Relationship(keys=self.rkeys)
        
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for rhn in range(len(prd.alts)):
                rh=prd.alts[rhn]
                # Starting at the end, each symbol is directe end of pid until
                # the first non-nullable symbol is found
                ids=rh.ids
                nids=len(ids)
                if nids<1:
                    continue
                #print("%s[%s] number ids: %s" % (pid,rhn,nids))
                for idn in range(nids-1,-1,-1):
                    ido=ids[idn]
                    if self.gp.isEmpty(ido):
                        break
                    deo.set(pid,ido.tpid,True)
                    if ido.nullable:
                        continue
        self.deo=deo

    def __director(self):
        ambiguous=[]
        for prd in self.gp.iter_prods():
            # Build the DIRECTOR set
            ambig={}
            ds=prd.ds
            pid=prd.pid
            for rhn in range(len(prd.alts)):
                rh=prd.alts[rhn]
                select=rh.select
                for tid in select:
                    try:
                        ds_lst=ds[tid]
                    except KeyError:
                        ds_lst=[]
                    ds_lst.append(rhn)
                    ds[tid]=ds_lst

            # Examine DIRECTOR set for ambiguous alternatives and complete 
            # non-terminal's DIRECTOR set dictionary.
            for tid in ds.keys():
                ds_lst=ds[tid]
                if len(ds_lst)==0:
                    raise ValueError("LL1grammar.py - LL1Prods1.__director() - "
                        "INTERNAL: PID %s director set for TID %s has no "
                        "alternatives" % (pid,tid))
                elif len(ds_lst)==1:
                    ds[tid]=ds_lst[0]
                else:
                    ambig[tid]=ds_lst

            # Save ambiguous data for reporting
            if len(ambig)!=0:
                prd.ambig=ambig
                prd.ambigous=True
                ambiguous.append(pid)

        self.ambiguous=ambiguous

    def __first_NT(self):
        # Record for use below of the PID's terminal BEGIN-WITH relationships
        for prd in self.gp.iter_prods():
            pid=prd.pid
            first=prd.bw     
            f=self.bw.rowHas(pid)
            for i in f:
                if self.gp.isTID(i):
                    first.append(i)
            prd.first=first
            
    def __first_prod(self):
        # Calculate the FIRST set for each production alternative
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for rh in prd.alts:
                first=rh.first
                for ido in rh.ids:
                    if ido.typ=="TID":
                        first.append(ido.tpid)
                    elif ido.typ=="PRD":
                        p=self.gp.pid(ido.tpid)
                        first.extend(p.first)
                    if not ido.nullable:
                        break
                rh.first=first
        
    def __follow(self):
        fb=self.fb_eos
        for prd in self.gp.iter_prods():
            if not prd.nullable:
                continue
            pid=prd.pid
            for tid in self.gp.iter_tids():
                if fb.get(pid,tid):
                    prd.follow.append(tid)

    def __followed_by(self):
        x=self.ieo.product(self.fdb)
        self.fb=x.product(self.bw)
        
    def __followed_by_extended(self):
        x=self.fb.clone()
        start=self.pid_start
        ieo=self.ieo
        eos=self.gp.EOS()
        end_of_start=[]
        # Find all of the symbols which have IS-END-OF start relationship with the
        # starting symbol.
        for i in self.rkeys:
            if self.ieo.get(start,i):
                end_of_start.append(i)
        # These are the symbols which have IS-FOLLOWED-BY EOS
        for i in end_of_start:
            x.set(i,eos,True)
        self.fb_eos=x

    def __followed_directly_by(self):
        fdb=LL1Relationship(keys=self.rkeys)
        
        for prd in self.gp.iter_prods():
            pid=prd.pid
            #print("prd=%s" % prd)
            for rhn in range(len(prd.alts)):
                rh=prd.alts[rhn]
                ids=rh.ids
                nids=len(ids)
                #print("rh=%s[%s],num ids=%s" % (pid,rhn,nids))
                if nids<=1:
                    continue
                for bn in range(nids-1):
                    #print("bn=%s" % bn)
                    if bn>=nids-1:
                        break
                    lid=ids[bn]
                    lidnm=lid.tpid
                    for cn in range(bn+1,nids):
                        #print("cn=%s" % cn)
                        rid=ids[cn]
                        fdb.set(lidnm,rid.tpid,True)
                        if not rid.nullable:
                            break
        self.fdb=fdb

    def __is_end_of(self):
        self.ieo=self.deo.clone()
        self.ieo.closure(reflexive=True)

    # This is essentially the same algorithm as used for calculating the alive
    # non-terminals, except it is looking for non-terminals that may result in
    # the empty string.
    def __nullable(self):
        nullable=[]   # List of nullable non-terminals (PID's)
       
        # Create the initial list of productions (RH instances) that do not have
        # any terminals and identify those that have the empty string as nullable.
        # Those non-terminals that derive the empty string are by definition 
        # nullable.
        maybe=[]
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for ndx in range(len(prd.alts)):
                rh=prd.alts[ndx]
                if self.gp.hasEmpty(rh):
                    rh.nullable=True
                    nullable.append(pid)
                    if self.debug and rh.nullable:
                        print("PID %s[%s] is nullable" % (pid,ndx))
                if not self.gp.hasT(rh):
                    maybe.append(rh)
        
        # Analyze all of the right-hand alternatives, repeatedly, looking for
        # an alternative in a not-alive production that has all of its non-
        # terminals alive.  This non-terminal is also alive.
        while True:
            added=0
            # This list identifies the RH instances determined
            for rhn in range(len(maybe)):
                rh=maybe[rhn]
                pid=rh.lhpid
                if pid in nullable:
                    continue

                nts=nullable_nt=0
                for ido in rh.ids:
                    if ido.typ=="TID":
                        continue
                    nts+=1
                    if ido.tpid in nullable:
                         nullable_nt+=1
                    # All of the non-terminals are nullable
                is_nullable = nullable==nts
                rh.nullable = is_nullable
                if self.debug and rh.nullable:
                    print("PID %s[%s] is nullable" % (pid,rhn))
                if is_nullable and (pid not in nullable):
                    nullable.append(pid)
                    added+=1
            if not added:
                break
                
        for pid in nullable:
            prd=self.gp.pid(pid)
            prd.nullable=True
        
        self.nullable=nullable      # List of nullable non-terminals
        
        # Update all of the ID's in the grammer.  This will be useful when
        # calculating the 'begins-directly-with' relationship.
        for prd in self.gp.iter_prods():
            for rh in prd.alts:
                for ido in rh.ids:
                    if self.gp.isEmpty(ido):
                        ido.nullable=True
                    elif ido.typ=="TID":
                        ido.nullable=False
                        ido.bw=List(ido.tpid)
                    elif ido.typ=="PRD":
                        ido.nullable=self.gp.pid(ido.tpid).nullable
                    else:
                        raise ValueError("Unrecognized ID type for '%s': '%s'" \
                            % (ido.tpid,ido.typ))
     
    # Propogate FIRST/FOLLOW information to right hand ID's
    def __propogate(self):
        for prd in self.gp.iter_prods():
            pid=prd.pid
            for rhn in range(len(prd.alts)):
                rh=prd.alts[rhn]
                ids=len(rh.ids)
                # Propogate all of the first information to the ID's and initialize
                for idn in range(ids):
                    ido=rh.ids[idn]
                    self.gp.idinit(ido)
                    if ido.typ=="TID":
                        if self.gp.isEmpty(ido):
                            ido.first.extend(rh.select)
                            continue
                        ido.first.append(ido.tpid)
                    elif ido.typ=="PRD":
                        id_prd=self.gp.pid(ido.tpid)
                        ido.first.extend(id_prd.first)
                        ido.nullable=id_prd.nullable
                    else:
                        raise ValueError("LL1grammar.py - LL1Prods1.__propagate() "
                            "- Unrecongined ID type in PID '%s', alternative, %s "
                            "ID '%s' at position %s in alternative: %s" \
                            % (pid,rhn,ido.tpid,idn,ido.typ))
                # Calculate the FOLLOW set for each ID
                prod_last=ids-1      # Index of the last ID in the alternative
                id_last=prod_last-1  # Index of the last ID in FIRST calculation
                for idn in range(ids):
                    ido=rh.ids[idn]
                    if idn==prod_last:
                        ido.follow.extend(prd.follow)
                        continue
                    id_follow=ido.follow
                    for idx in range(idn,prod_last,1):
                        next_id=rh.ids[idx+1]
                        id_follow.extend(next_id.first)
                        if not next_id.nullable:
                            break

    def __selection(self):
        for prd in self.gp.iter_prods():
            for rh in prd.alts:
                lst=rh.select
                if rh.nullable:
                    for term in prd.follow:
                        lst.append(term)
                else:      
                    for term in rh.first:
                        lst.append(term)

    #def print_ambigous(self):
    #    print("\nAMBIGUOUS NON-TERMINALS: %s" % self.ambiguous)

    def print_begins_directly_with(self):
        print("\nBEGINS-DIRECTLY-WITH Relationsip:\n%s" % self.bdw.string())

    def print_begins_with(self):
        print("\nBEGINS-WITH Relationship:\n%s" % self.bw.string())

    #def print_dead(self):
    #    print("\nDEAD NON-TERMINALS: %s" % self.dead)

    def print_direct_end_of(self):
        print("\nDIRECT-END-OF Relationship:\n%s" % self.deo.string())

    #def print_director(self):
    #    string="\nDIRECTOR Sets:\n"
    #    for prd in self.gp.iter_prods():
    #        string="%s%s\n" % (string,prd.print_director())
    #    print(string[:-1])

    #def print_first(self,details=False):
    #    string="\nFIRST Sets:\n"
    #    for prd in self.gp.iter_prods():
    #        string="%s%s\n" % (string,prd.print_first(details=details))
    #    print(string[:-1])

    def print_followed_by(self):
        print("\nFOLLOWED-BY Relationship:\n%s" % self.fb.string())
       
    def print_followed_by_extended(self):
        print("\nFOLLOWED-BY Relationship with EOS:\n%s" % self.fb_eos.string())

    def print_followed_directly_by(self):
        print("\nFOLLOWED-DIRECTLY-BY Relationship:\n%s" % self.fdb.string())

    def print_follow(self,details=False):
        string="\nFOLLOW Sets:\n"
        for prd in self.gp.iter_prods():
            string="%s%s\n" % (string,prd.print_follow(details=details))
        print(string[:-1])

    def print_is_end_of(self):
        print("\nIS-END-OF Relationship:\n%s" % self.ieo.string())

    def print_nullable(self):
        print("\nNULLABLES: %s" % self.nullable)

    def print_select(self,details=False):
        string="\nSELECTION Sets:\n"
        for prd in self.gp.iter_prods():
            string="%s%s\n" % (string,prd.print_select(details=details))
        print(string[:-1])

    def print_unreachable(self,details=False):
        print("\nUNREACHABLE NON-TERMINALS: %s" % self.unreachable)

    def removeEmpty(self,lst):
        lst.remove(self.gp.tidempty)

    # Validate and process productions.  Underlying errors will raise a
    # ValueError exception.  It is NOT recommended that these exceptions be caught.
    def validate(self):
      # Check output of Grammar object for sanity
        self.sanity_checks()

      # Check that the grammar makes sense
        self.sensible()

      # Perform LL(1) analysis
        # Step 1. Find nullable non-terminals and production alternatives
        self.__nullable()
        if self.debug:
            self.print_nullable()
        # Step 2. Compute the BEGINS-DIRECTLY-WITH relationship
        self.__begins_directly_with()
        if self.debug:
            self.print_begins_directly_with()
        # Step 3. Compute the BEGINS-WITH relationship
        self.__begins_with()
        if self.debug:
            self.print_begins_with()
        # Step 4. Compute the FIRST set for each non-terminal
        self.__first_NT()
        if self.debug:
            self.print_first()
        # Step 5: Compute the FIRST ser for each production alternative
        self.__first_prod()
        if self.debug:
            self.print_first(details=True)
        # Step 6: Compute the FOLLOWED-DIRECTLY-BY relationship
        self.__followed_directly_by()
        if self.debug:
            self.print_followed_directly_by()
        # Step 7: Compute the DIRECT-END-OF relationship
        self.__direct_end_of()
        if self.debug:
            self.print_direct_end_of()
        # Step 8: Compute IS-END-OF relationship
        self.__is_end_of()
        if self.debug:
            self.print_is_end_of()
        # Step 9: Compute FOLLOWED-BY relationship
        self.__followed_by()
        if self.debug:
            self.print_followed_by()
        # Step 10: Extend FOLLOWED-BY relationship with EOS information
        self.__followed_by_extended()
        if self.debug:
            self.print_followed_by_extended()
        # Step 11: Compute the FOLLOW set for each nullable non-terminal
        self.__follow()
        if self.debug:
            self.print_follow()
        # Step 12: Compute the Selection Set for each production
        self.__selection()
        if self.debug:
            self.print_select()
        
      # Prepare grammar for parser
        # Calculate FIRST/FOLLOW set information for grammar vocabulary (ID's)
        self.__propogate()
        if self.debug:
            print("\nPropogated FIRST/FOLLOW information to production alternatives")
            self.print_first(details=True)
            self.print_follow(details=True)
            
        # Build the director set for each non-terminal (PID)
        self.__director()
        if self.debug:
            self.print_director()
        if self.debug or len(self.ambigous)>0:
            self.print_ambigous()
            
        if len(self.ambiguous)>0:
            raise ValueError("LL1grammar.py - LL1Prods.validate() - supplied "
                "grammar is not LL(1)")

# The director set for the grammar drives the selection of alternatives by an
# LL(1) parser, but identifying the next input symbol that will select a
# production alternative (and conversely, identify incorrect input).
#
# Determining the Director set for each non-terminal is a multiple step process.
# The algorithm used here for recognizing nullable and calculating the FIRST and 
# FOLLOW sets are those described in "Modern Compiler Implementation in Java", by 
# Andrew W. Appel and published by the Cambridge University Press in Cambridge, 
# United Kingdom, in 1998.  The algorithm can be found in section  3.2, Predictive 
# Parsing, on pages 47-52.  The algorithm described on these pages is independent 
# of the implementation language, in this case being Python rather than Java.
# The validate method implements Algorithm 3.13 on page 51.
#
# Instance arguments: see class Prods.
class LL1Prods2(Prods):
    def __init__(self,gp,debug):
        super().__init__(gp,debug=debug)
        
        # This is a list of all of the productions (RH instances) in the grammar.
        # It is used to validate the grammar and the RH instance index is used
        # by the cross-reference dictionary.
        self.prods=[]
        for prdo in self.gp.iter_prods():
            for rh in prdo.alts:
                self.prods.append(rh)
        
        # This dictionary is a cross reference of each grammar symbol.  It is 
        # used to speed up the analysis process.  The key is a grammar symbol
        # (PID or TID) and its value is a List of indexes into self.prods where
        # the symbol is used.
        self.xref={}
        self.__build_xref()

        # The keys to this dictionary are TID's and PID's
        # The value for each key is True/False depending upon its "nullability"
        self.nullable=List()
        
        # The keys for each of these dictionaries are TID's and PID's. 
        # The value for each key is a List entry. 
        self.first={}
        self.follow={}
    
        self.start_pid=self.gp.start()
        self.empty_tid=self.gp.Empty()
        self.eos_tid=self.gp.EOS()
    
        for tid in self.gp.iter_tids():
            self.follow[tid]=List()
            if self.gp.isEmpty(tid):
                # EMPTY TID
                self.first[tid]=List()
                self.nullable.append(tid)
            else:
                # All other TID's
                self.first[tid]=List(tid)
            
        for pid in self.gp.iter_pids():
            self.first[pid]=List()
            self.follow[pid]=List()
        start_follow=List(self.gp.EOS())
        self.follow[self.start_pid]=start_follow
        
    def __build_xref(self):
        for n in range(len(self.prods)):
            rh=self.prods[n]
            for ido in rh.ids:
                tpid=ido.tpid
                try:
                    xref=self.xref[tpid]
                except KeyError:
                    xref=[]
                if not n in xref:
                    xref.append(n)
                    self.xref[tpid]=xref
        for pid in self.gp.iter_pids():
            try:
                self.xref[pid]
            except KeyError:
                self.xref[pid]=[]
        for tid in self.gp.iter_tids():
            try:
                self.xref[tid]
            except KeyError:
                self.xref[tid]=[]
        
    def __first(self):
        # Determine the FIRST set for each production alternative
        # This will be used to create the director set for the PID.
 
        work=list(range(len(self.prods)))
        passes=1
        while True:
            new=[]
            if self.debug:
                print("\nFIRST pass: %s work: %s" % (passes,work))
            for ndx in work:
                rh=self.prods[ndx]
                pid=rh.lhpid
                ids=rh.ids
                rh_changed=False
                for ido in rh.ids:
                    if ido.isempty:
                        break
                    tpid=ido.tpid
                    id_first=self.first[tpid]
                    if self.debug:
                        print(" [%s] tpid %s first: %s" % (ndx,tpid,id_first))
                    rh_first=rh.first
                    rh_changed|=rh_first.cextend(id_first)
                    if self.debug:
                        if rh_changed:
                            rhc="*"
                        else:
                            rhc=" "
                            print("%s[%s] lh: %s first: %s" % (rhc,ndx,pid,rh.first))
                    if not tpid in self.nullable:
                        break
                if rh_changed:
                    # Now update the FIRST set for the PID
                    pid_first=self.first[pid]
                    pid_changed=pid_first.cextend(rh_first)
                    if self.debug:
                        if pid_changed:
                            pidc="*"
                        else:
                            pidc=" "
                        print("%sPID: %s first: %s" % (pidc,pid,pid_first))
                    if pid_changed:
                        new=self.__new_work(new,rh)
            if len(new)==0:
                break
            passes+=1
            work=new
            
        # Update PRD instances with first information
        for prdo in self.gp.iter_prods():
            prdo.first=self.first[prdo.pid]
        
    def __follow1(self):
        work=list(range(len(self.prods)))
        passes=1
        while True:
            new=[]
            if self.debug:
                print("\nFOLLOW1 pass: %s work: %s" % (passes,work))
            for ndx in work:
                rh=self.prods[ndx]
                pid=rh.lhpid
                ids=rh.ids
                follow_lh=self.follow[pid]
                if self.debug:
                    print(" [%s] PID %s ..." % (ndx,pid))
                for indx in range(len(ids)-1):
                    i_ido=rh.ids[indx]
                    if i_ido.isempty:
                        break
                    i_tpid=i_ido.tpid
                    i_follow=self.follow[i_tpid]
                    if self.debug:
                        print(" [%s] PID: %s i_tpid [%s] %s follow: %s" \
                            % (ndx,pid,indx,i_tpid,i_follow))
                    for jndx in range(indx+1,len(ids)):
                        j_ido=rh.ids[jndx]
                        j_tpid=j_ido.tpid
                        if indx+1==jndx or j_tpid in self.nullable:
                            j_first=self.first[j_tpid]
                            if self.debug:
                                print(" [%s] PID: %s j_tpid [%s] %s first: %s" \
                                    % (ndx,pid,jndx,j_tpid,j_first))
                            i_changed=i_follow.cextend(j_first)
                            if self.debug:
                                if i_changed:
                                    idc="*"
                                else:
                                    idc=" "
                                print("%s[%s] PID: %s i_tpid [%s] %s follow: %s" \
                                    % (idc,ndx,pid,indx,i_tpid,i_follow)) 
                            if i_changed:
                                # Don't think I need to do this
                                self.follow[i_tpid]=i_follow
                                new=self.__new_work(new,i_tpid)
                # Now, examine next ID instance in the production
            if len(new)==0:
                break
            passes+=1
            work=new
        
    def __follow2(self):
        work=list(range(len(self.prods)))
        passes=1
        while True:
            new=[]
            if self.debug:
                print("\nFOLLOW2 pass: %s work: %s" % (passes,work))
            for ndx in work:
                rh=self.prods[ndx]
                pid=rh.lhpid
                ids=rh.ids
                numids=len(ids)
                last=numids-1
                follow_lh=self.follow[pid]
                for indx in range(numids):
                    i_ido=rh.ids[indx]
                    if i_ido.isempty:
                        break
                    i_tpid=i_ido.tpid
                    i_follow=self.follow[i_tpid]
                    if self.debug:
                        print(" [%s] PID: %s i_tpid [%s] %s follow: %s" \
                            % (ndx,pid,indx,i_tpid,i_follow))
                    all_nullable=True
                    for jndx in range(indx+1,numids):
                        j_ido=rh.ids[jndx]
                        if j_ido.tpid not in self.nullable:
                            all_nullable=False
                            break
                    if indx==last or all_nullable:
                        i_changed=i_follow.cextend(follow_lh)
                        self.follow[i_tpid]=i_follow
                        if self.debug:
                            if i_changed:
                                idc="*"
                            else:
                                idc=" "
                            print("%s[%s] PID: %s i_tpid [%s] %s follow: %s" \
                                % (idc,ndx,pid,indx,i_tpid,i_follow))
                        if i_changed:
                            new=self.__new_work(new,i_tpid)
            if len(new)==0:
                break
            passes+=1
            work=new

    def __nullable(self):
        # Start by looking at all productions
        work=list(range(len(self.prods)))
        passes=0
        while True:
            new=[]
            for ndx in work:
                prod=self.prods[ndx]
                ids=prod.ids
                n=0
                for ido in prod.ids:
                    if ido.isempty or ido.tpid in self.nullable:
                        n+=1
                if n==len(ids):
                    prod.nullable=True
                    pid=prod.lhpid
                    self.nullable.append(pid)
                    new=self.__new_work(new,prod)
            passes+=1
            if self.debug:
                print("\nnullable pass: %s" % passes)
                self.print_nullable()
                print("new work: %s" % len(new))
            if len(new)==0:
                break
            work=new
                    
    def __new_work(self,work,prod):
        if isinstance(prod,str):
            tpid=prod
        elif isinstance(prod,RH):
            tpid=prod.lhpid
        else:
            raise ValueError("LL1grammar.py - LL1Prods2 - __new_work() - 'prod' "
                "argument must be a string or RH instance: %s" % prod)
        xref=self.xref[tpid]
        for n in xref:
            if not n in work:
                work.append(n)
        return work

    def __propogate(self):
        # Update PRD instances with follow information
        if self.debug:
            print("\nUpdating Grammar with Follow information")
            print("\nUpdating PID follow information")
        for prdo in self.gp.iter_prods():
            pid=prdo.pid
            pid_follow=self.follow[pid]
            if self.debug:
                print("PID %s follow data: %s" % (pid,pid_follow))
            prdo.follow.extend(pid_follow)
            if self.debug:
                print("PID %s follow:      %s" % (pid,prdo.follow))
            
        if self.debug:
            print("\nUpdating nullable alternatives:")
            
        for prdo in self.gp.iter_prods():
            pid=prdo.pid
            pid_follow=self.follow[pid]
            for rndx in range(len(prdo.alts)):
                rh=prdo.alts[rndx]
                ids=rh.ids
                if rh.nullable:
                    if self.debug:
                        print("PID %s [%s] nullable follow data: %s" \
                            % (pid,rndx,pid_follow))
                    rh.first.extend(pid_follow)
                    if self.debug:
                        print("PID %s [%s] nullable first:       %s" \
                            % (pid,rndx,rh.first))
                        print("PID %s [%s] nullable follow data: %s" \
                            % (pid,rndx,pid_follow))
                    rh.follow.extend(pid_follow)
                    if self.debug:
                        print("PID %s [%s] nullable follw:       %s" \
                            % (pid,rndx,rh.follow))
                    continue
                    
        if self.debug:
            print("\nUpdating alternative selection set:")

        for prdo in self.gp.iter_prods():
            pid=prdo.pid
            for rndx in range(len(prdo.alts)):
                rh=prdo.alts[rndx]
                lst=List()
                lst.extend(rh.first)
                rh.select=lst
                if self.debug:
                    print("PID %s[%s] selections set: %s" % (pid,rndx,rh.select))
            
        if self.debug:
             print("\nUpdating id follow information:")
            
        for prdo in self.gp.iter_prods():
            pid=prdo.pid
            pid_follow=self.follow[pid]
            for rndx in range(len(prdo.alts)):
                rh=prdo.alts[rndx]
                ids=rh.ids
                for idx in range(len(ids)):
                    ido=ids[idx]
                    self.gp.idinit(ido)
                    tpid=ido.tpid
                    if self.gp.isEmpty(tpid):
                        if self.debug:
                            print("PID %s [%s] tpid [%s] %s follow data: %s" \
                                % (pid,rndx,idx,tpid,pid_follow))
                        ido.follow.extend(pid_follow)
                    else:
                        id_follow=self.follow[tpid]
                        if self.debug:
                            print("PID %s [%s] tpid [%s] %s follow:      %s" \
                                % (pid,rndx,idx,tpid,id_follow))
                        ido.follow.extend(self.follow[tpid])

    def print_first_data(self):
        # Sort the symbols
        syms=[]
        symlen=0
        for x in self.xref.keys():
            symlen=max(symlen,len(x))
            syms.append(x)
        syms=sorted(syms)
        print("\nSymbol First Data\n")
        for sym in syms:
            if self.gp.isTID(sym):
                typ="TID"
            else:
                typ="PID"
            symtxt=sym.ljust(symlen)
            refs=""
            try:
                follow=self.first[sym]
            except KeyError:
                follow=[]
            print("%s %s  %s" % (typ,symtxt,follow))

    def print_follow_data(self):
        # Sort the symbols
        syms=[]
        symlen=0
        for x in self.xref.keys():
            symlen=max(symlen,len(x))
            syms.append(x)
        syms=sorted(syms)
        print("\nSymbol Follow Data\n")
        for sym in syms:
            if self.gp.isTID(sym):
                typ="TID"
            else:
                typ="PID"
            symtxt=sym.ljust(symlen)
            refs=""
            try:
                follow=self.follow[sym]
            except KeyError:
                follow=[]
            print("%s %s  %s" % (typ,symtxt,follow))

    def print_nullable(self):
        print("NULLABLES: %s" % self.nullable)
        
    # Print the cross-reference information
    def print_xref(self):
        # Sort the symbols
        syms=[]
        symlen=0
        for x in self.xref.keys():
            symlen=max(symlen,len(x))
            syms.append(x)
        syms=sorted(syms)
        print("\nGrammar Symbol Cross-reference\n")
        for sym in syms:
            symtxt=sym.ljust(symlen)
            refs=""
            xref=self.xref[sym]
            for n in xref:
                alt=self.prods[n]
                line=alt.lhtok.line
                refs="%s%s, " % (refs,line)
            refs=refs[:-2]
            print("%s  %s" % (symtxt,refs))

    def validate(self):
        self.sanity_checks()    # Check the output Grammar object for sanity
        self.sensible()         # Check that the grammar makes sense

        if self.debug:
            self.print_xref()
            
        self.__nullable()       # Determine nullable non-terminals
        self.__first()          # Determine production and PID first sets.
        if self.debug:
            self.print_first_data()
        self.__follow1()
        if self.debug:
            self.print_follow_data()
        self.__follow2()
        if self.debug:
            self.print_follow_data()
        self.__propogate()
        if self.debug:
            self.print_first(details=True)
            self.print_follow(details=True)
        self.director()
        if self.debug:
            self.print_director()
        if self.debug or len(self.ambigous)>0:
            self.print_ambigous()

class LL1Relationship(object):
    def __init__(self,keys,init=False):
        if not isinstance(keys,list):
            raise ValueError("LL1grammar.py - LL1Relationship() - 'keys' "
                "argument must be a list: %s" % keys)
        if len(keys)==0:
            raise ValueError("LL1grammar.py - LL1Relationship() - 'keys' "
                "argument must not be an empty list")
            
        self.init=init  # Value used to initialize the empty matrix
            
        # Validate row/column keys are unique
        k=[]
        for x in keys:
            if x not in k:
                k.append(x)
            else:
                raise ValueError("LL1grammar.py - LL1Relationship() - 'keys' "
                    "element not unique: %s" % x)
        self.keys=k  # Maps a key to a row or column index
       
        # Build the empty n x n matrix, initializing with the 'init' argument.
        n=len(self.keys)
        rows=[]
        for x in range(n):
            row=[]
            for y in range(n):
                row.append(init)
            rows.append(row)
        self.rows=rows

    def __index(self,row,col):
        try:
            r=self.keys.index(row)
        except IndexError:
            raise ValueError("LL1grammar.py - LL1Relationship().__index - 'row' "
                    "not a valid key: %s" % r) from None
        try:
            c=self.keys.index(col)
        except IndexError:
            raise ValueError("LL1grammar.py - LL1Relationship().__index - 'row' "
                    "not a valid key: %s" % r) from None
        return (r,c)
        
    # Returns a new instance of LL1Relationship with values equal to this one
    def clone(self):
        new=LL1Relationship(keys=self.keys,init=self.init)
        for row in self.keys:
            for col in self.keys:
                new.set(row,col,self.get(row,col))
        return new
        
    # Computes the transitive closure or, if 'reflexive' is specified as True
    # the reflexive transitive closure of this matrix.  The calculation modifies
    # this instance.
    #
    # This method uses Warshall's algorithm for performing the transitive
    # closure calculation.  The code is based upon Slide 20 in Lecture #26 of 
    # Adam J. Lee with the University of Pittsburgh.  The lecture is datad 
    # 12 April, 2011.  Google for the link.
    def closure(self,reflexive=False):
        a=self
        
        for K in self.keys:
            for I in self.keys:
                for J in self.keys:
                    if not a.get(I,K):
                        continue
                    if not a.get(J,K):
                        continue
                    a.set(I,J,True)
            if reflexive:
                self.set(K,K,True)

    def get(self,row,col):
        r,c=self.__index(row,col)
        row=self.rows[r]
        return row[c]

    def set(self,row,col,value):
        r,c=self.__index(row,col)
        row=self.rows[r]
        row[c]=value
        
    # This method calculates the product of two matrices of the same dimensions.  
    # Reference the Wikipedia article on "Matrix multiplication" at
    # http://en.wikipedia.org/wiki/Matrix_multiplication on the method uses for 
    # calculation.  Because the relationship matrix uses logical values (True or
    # False) multiplication is treated as the result of an AND operation and
    # addition is treated as an OR operation on the two logic values.
    def product(self,other):
        if not isinstance(other,LL1Relationship):
            raise ValueError("LL1grammar.py - LL1Relationship.product() - "
                "'other' argument must be an instance of LL1Relationship: %s" \
                % other)
        
        # This calculates c=a*b
        a=self
        b=other
        c=LL1Relationship(keys=self.keys,init=self.init)

        for i in self.keys:
            for j in self.keys:
                for k in self.keys:
                    Aij=a.get(i,k)
                    if not Aij:
                        continue
                    Bky=b.get(k,j)
                    if not Bky:
                        continue
                    c.set(i,j,True)
                    break
        return c

    def rowHas(self,row):
        has=[]
        for col in self.keys:
            if self.get(row,col):
                has.append(col)
        return has
        
    def string(self):
        string=""
        n=len(self.keys)
        init=self.init
        for rn in range(n):
            row=self.rows[rn]
            rowkey=self.keys[rn]
            values=[]
            for cn in range(n):
                if row[cn]!=init:
                    values.append(cn)
            if len(values)==0:
                continue
            keys=[]
            for x in values:
                keys.append(self.keys[x])
            string="%s%s <> %s\n" % (string,rowkey,keys)
        if len(string)==0:
            return "relationship not present"
        else:
            return string[:-1]

# This is the base class for all LL(1) grammar components represented by various
# subclases.  The LL1Prods class populates the attributes in this base class
# during its analysis of the grammar.
class LL1Sem(object):
    def __init__(self):
        self.alive=False       # If True, is alive. Set by __alive()
        self.ambiguous=False   # If True, alternatives have ambiguous selections.
        self.ambig={}          # Ambiguous alternatives
        self.bw=List()         # The PID BEGINS-WITH rel.  Set by __first()
        self.ds={}             # The DIRECTOR set.  Set by __director()
        self.first=List()      # The FIRST set. Set by __first()
        self.follow=List()     # The FOLLOW set.  Set by __follow()
        self.select=List()     # The selection set.  Set by __selection()
        self.nullable=False    # If True, is nullable. Set by __nullable()
        self.reachable=False   # If True, is reachable. Set by __reachable()
        
    def print_director(self,*args,**kwds):
        raise NotImplementedError("subclass %s must provide print_director() "
            "method" % self.__class__.__name__)
    def print_first(self,*args,**kwds):
        raise NotImplementedError("subclass %s must provide print_first() method"\
            % self.__class__.__name__)
    def print_follow(self,*args,**kwds):
        raise NotImplementedError("subclass %s must provide print_follow() method"\
            % self.__class__.__name__)
    def print_select(self,*args,**kwds):
        raise NotImplementedError("subclass %s must provide print_select() method"\
            % self.__class__.__name__)

# ID - The generic production right hand terminal or non-terminal
#
# Instance arguments:
#   tpid   The 'name' Token of the terminal or non-terminal or its id
#   rep    The 'rep' Token of terminal or non-terminal (or None if absent)
#   rsync  Whether eligible for resynchronization following this ID.
#   string Indicates whether the tpid argument is a string (True) or a Token
#          from the Grammar processing (False).
class ID(LL1Sem):
    def __init__(self,tpid,rep=None,rsync=False,string=False):
        super().__init__()
        if string:
            self.id_tok=None
            self.tok_tok=None
            self.tpid=tpid
            self.repstr=rep
            self.resync=rsync
        else:
            if not isinstance(tpid,lexer.Token):
                raise TypeError("ID.__init__() - tpid must be instance of Token: "
                    "%s" % tpid)
                
            self.id_tok=tpid
            
            # Extract ID elements from the match object groups
            mg=tpid.groups()
            
            # Set the TID or PID
            self.tpid=mg[0]
            
            # Set the repetition string (only '*') supported
            repstr=mg[1]
            if len(repstr)==0:    # This means a match was not found for the group
                self.repstr=None
            else:
                self.repstr=repstr
                
            # Set the resync value
            self.resync = mg[2]=="!"

        # These attribute will be set by the Grammar._parse() method or a subclass.
        self.typ="?"
        self.istid=False
        self.isprd=False
        self.isempty=False

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
        return "ID('%s',%s,min=%s,max=%s,rec=%s,rep=%s,resync=%s,trace=%s)" \
            % (self.tpid,self.typ,self.min,self.max,rec,rep,self.resync,self.trace)

    def cvt_rep(self,string):
        if string=="*":
            self.min=0
            self.reptyp="*"
            self.repstr=string
        elif string[0]==":":
            self.min=self.max=int(string[1:])
            self.reptyp=":"
            self.repstr=string
        else:
            raise ValueError("ID.cvt_rep() - invalid rep string: '%s'" % string)

    def print_first(self,indent=""):
        return "%s%s %s %s" % (indent,self.typ,self.tpid,self.first)
    def print_follow(self,indent=""):
        return "%s%s %s %s" % (indent,self.typ,self.tpid,self.follow)
    def print_select(self,indent=""):
        return "%s%s %s %s" % (indent,self.typ,self.tpid,self.select)

# PRD - Defines a grammar production
class PRD(LL1Sem):
    def __init__(self,pid,sync=[],flags=[]):
        super().__init__()
        self.pid=pid
        self.alts=[]      # One or more lists of ID instances
        self.sync=sync    # List of token types for resynchronization
        self.flags=flags  # Correspondin '+' flags of sync token
        self.ptrace=False # If any of the right hands are traced, so will the PRD
        # If an integer, attribute identifies the production alternative that
        # contains: PID -> EMPTY.  Set by LL1Prods.__sanity_check2()
        self.empty=None

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

    def print_director(self,indent="",details=False):
        string="%sPID %s\n" % (indent,self.pid)
        ind="%s    " % indent
        ds=self.ds
        tids=[]
        for tid in self.ds.keys():
            tids.append(tid)
        tids=sorted(tids)
        for tid in tids:
            string="%s%sTID %s -> %s\n" % (string,ind,tid,ds[tid])
        return string[:-1]

    def print_first(self,indent="",details=False):
        string="%sPID %s %s\n" % (indent,self.pid,self.first)
        ind="%s    " % indent
        for x in range(len(self.alts)):
            alt=self.alts[x]
            string="%s%s%s\n" \
                % (string,indent,alt.print_first(ind,index=x,details=details))
        return string[:-1]
        
    def print_follow(self,indent="",details=False):
        string="%sPID %s %s\n" % (indent,self.pid,self.follow)
        ind="%s    " % indent
        for x in range(len(self.alts)):
            alt=self.alts[x]
            string="%s%s%s\n" \
                % (string,indent,alt.print_follow(ind,index=x,details=details))
        return string[:-1]
        
    def print_select(self,indent="",details=False):
        string="%sPID %s %s\n" % (indent,self.pid,self.select)
        ind="%s    " % indent
        for x in range(len(self.alts)):
            alt=self.alts[x]
            string="%s%s%s\n" \
                % (string,indent,alt.print_select(ind,index=x,details=details))
        return string[:-1]

    # This method processes a right hand production
    def rhand(self,rh):
        if not isinstance(rh,RH):
            raise TypeError("parser.PRD.rhand() - rh must be an RH instance: %s" \
                % rh)
        if rh.trace:
            self.ptrace=True
        rh.lhpid=self.pid    # Remember which non-terminal the rh is analternative
        self.alts.append(rh)

# RH - A right hand side alternative of a production
class RH(LL1Sem):
    def __init__(self,lhtok,lst=[],trace=False):
        super().__init__()
        self.lhtok=lhtok  # Left hand side of alternative token
        self.ids=lst   # List of ID instances defining this right hand alternative
        self.trace=trace  # Trace this alternative or not
        self.lhpid=None   # This is set when the RH instance is appended to a PRD
        self.empty=False  # this alternative contains the empty token.

    def __str__(self):
        string="RH(trace=%s [" % self.trace
        rh=""
        for x in self.ids:
            rh="%s, %s" % (rh,x)
        string="%s%s ] )" %(string,rh[1:])
        return string
    def define(self,lst=[]):
        self.ids=lst
    def print_first(self,indent,index=None,details=False):
        string=n=""
        if index is not None:
            n="[%s] " % index
        string="%s%s%s%s\n" % (string,indent,n,self.first)
        ind="%s    " % indent
        if details:
            for x in self.ids:
                string="%s%s%s\n" % (string,indent,x.print_first(ind))
        return string[:-1]
    def print_follow(self,indent,index=None,details=False):
        string=n=""
        if index is not None:
            n="[%s] " % index
        string="%s%s%s%s\n" % (string,indent,n,self.follow)
        ind="%s    " % indent
        if details:
            for x in self.ids:
                string="%s%s%s\n" % (string,indent,x.print_follow(ind))
        return string[:-1]
    def print_select(self,indent,index=None,details=False):
        string=n=""
        if index is not None:
            n="[%s] " % index
        string="%s%s%s%s\n" % (string,indent,n,self.select)
        ind="%s    " % indent
        if details:
            for x in self.ids:
                string="%s%s%s\n" % (string,indent,x.print_select(ind))
        return string[:-1]

# START - A subclass of ID representing the start production
class START(ID):
    def __init__(self,pid):
        super().__init__(pid,rep=None,string=True)
        self.ispid=True
        self.typ="PRD"

if __name__ == "__main__":
    raise NotImplementedError("LL1grammar.py - must only be imported")
