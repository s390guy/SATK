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

# The module provides prepackaged use of the foundation language tools.  The 
# classes provided by this module fall into three categories:
#
#   1. Key-Word Language Definition - classes that aid in defining an instance of
#                     the Key-Word Language.
#   2. Smart Tokens - subclasses of lexer.Type and lexer.Token providing prepackaged
#                     support for commonly occurring types of data.
#   3. Key-Word Language - Classes that consume definition classes creating a
#                     run-time processor of the language, generating its own 
#                     lexical analyzer and LL(1) syntactical analyzer from the
#                     foundtation tools.
#
# Descriptions of the facilities provided herein accompany the object definitions.
#
# This module is intended to be imported for use by other modules for the purpose
# of reusing developed language components.  Refer to the document "SATK for s390 -
# Language Processing Tools" in the SATK doc directory for a description of how 
# the base components are used in this module.

# Python imports:
import sys                # Need access to the exit() method.

# SATK imports:
import lang               # Access the language application interface to the tools
import lexer              # Access the lexical analyzer
import LL1parser          # Access the LL1parser module
import satkutil           # Access the SATK utility module
from satkutil import DM,Text_Print   # Access the debug manager if needed

# +---------------------------------+
# |  Key-Word Language Definitions  |
# *---------------------------------+

# These classes are used to define statements.  They manage the creation of 
# lexical analyzer types and the internal statement representation of them
# utilized by the KWLang class.  The KWDef and KWKeyWord classes may be used
# directly to define the language or this wrapper classes for building the
# language.  The wrapper class is intended to provide coordination between
# lexical analyzer definitions and the statement definition found to be painful
# in practice when using the KWDef, KWKeyWord classes themselves.

class Definition(object):
    start_cbs=["beg","end"]
    statements_cbs=["end"]
    def __init__(self,la,kwlang,ptrace=False):
        if not isinstance(la,LA):
            raise ValueError("languitil.py - Definition.__init__() - 'la' "
                "argument requires an instance of LA: %s" % la)
        if not isinstance(kwlang,KWLang):
            raise ValueError("languitil.py - Definition.__init__() - 'kwlang' "
                "argument requires an instance of KWLang: %s" % kwlang)
        self.la=la          # LA instance
        self.kwlang=kwlang  # KWLang instance of this language
        self._stmts={}      # Dictionary of statement name to Stmt instances
        self._stmts_pids={} # Dictionary of PID's to Stmt instances
        self._stmts_lst=[]  # List of Stmt instances
        
        # Attribute related to production generation
        # Specify True to cause 'start' and 'statements' production tracing
        self.ptrace=ptrace
        
        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None           # Debug manager
        self.lang=None         # LL1parser instance
        
    # Add a new statement (with a Stmt instance) to the language
    def add(self,st):
        if not isinstance(st,Stmt):
            raise ValueError("langutil.py - Definition.add() - 'st' argument "
                "must be and instance of Stmt: %s" % st)
        name=st.name
        if name in self._stmts:
            raise ValueError("langutil.py - Definition.add() - duplicate "
                "statement: %s" % name)
        self._stmts[name]=st
        self._stmts_pids[name]=st
        self._stmts_lst.append(st)
        
    # Define my syntactical analyzer call back methods.
    def callbacks(self,lang,dm):
        self.dm=dm         # Set the Debug manager
        self.lang=lang     # Set the LL1parser instance
        lang.cbreg("start","beg",self.cb_start_beg)
        lang.cbreg("start","end",self.cb_start_end)
        lang.cbreg("statements","end",self.cb_statements_end)
        for x in self._stmts_lst:
            x.callbacks(lang,dm)
        
    # Called when a recognition begins with the start production.
    # Note: this method initializes the global Scope object
    def cb_start_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Definition.cb_start_beg(gs,pid='%s')" % pid)

        # Initialize the global scope for Key-word language parsing.  All
        # callback activity occurs within this single object
        gs.defn=self           # Provide access to this Definition instance
        gs.kwlang=self.kwlang  # Provide access to the KWLang instance
        gs.build=Build(self)   # Provide access to the Build instance
        
    # Called at completion of the recognition process
    def cb_start_end(self,gs,pid,failed=False,eo=[]):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Definition.cb_start_end"
                "(gs,pid='%s',failed=%s,eo=%s)" % (pid,failed,eo))
            
        # Check for any missing required statements 
        gs.build.required(self)
        return True
        
    # Called when the end of all statement options has completed.
    # Note: there is no corrsponding '_beg' method when starting to recognize
    # statements.  This allow exposure of any error objects during tracing.
    def cb_statements_end(self,gs,pid,failed=False,eo=[]):
        if self.lang.isdebug("cbtrace"):
            print("langutil.py - Definition.cb_statements_end(gs,pid='%s')" % pid)

        return True
    
    # Add optional lexer.Type instances to the lexical analyzer
    def opt(self,typ):
        self.la.opt(typ)
        
    # This method returns the Stmt instance corresponding to the supplied PID
    def pid2stmt(self,pid):
        try:
            return self._stmts_pids[pid]
        except KeyError:
            raise ValueError("langutil.py - Definition.pid2stmt() - INTERNAL: "
                "PID not found: '%s'" % pid)

    # Return the productions required to recognize the defined language
    def prods(self):
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p="start -> statements*!%s\n" % pt
        for x in self._stmts_lst:
            p="%sstatements -> %s%s\n" % (p,x.symbol(),pt)
        p="%sstatements -> %s%s\n" % (p,self.la.overrides["empty"],pt)
        for x in self._stmts_lst:
            p="%s%s" % (p,x.prods(self.la))
        return p
        
    # Adds, if not already present, a new reserved word to the lexical analyzer.
    def res(self,match,tid=None):
        if tid is None:
            rw=RWord(match.upper(),match)
        else:
            rw=RWord(tid.upper(),match)
        self.la.res(rw)
        
    # Returns the starting grammar symbol
    def symbol(self):
        return "start"

    # Report token errors from an xxxxx_eos list
    def token_errors(self,who,eo_list):
        if not isinstance(eo_list,list):
            lst=[eo_list,]
        else:
            lst=eo_list
        for x in lst:
            tok=x.token
            expected=x.expect
            message="%s expected TID %s but found TID %s: '%s'" \
                % (who,expected,tok.tid,tok.string)
            error=KWSemanticError("token_errors",\
                type="T",token=tok,message=message)
            self.kwlang.error(error)
        
class Keyword(object):
    cbs=["beg","end","error","failing","token"]
    def __init__(self,name,st,tids=[],required=False,multiple=False,default=None,\
                 ptrace=False):
        if not isinstance(tids,list):
            raise ValueError("langutil.py - Keyword.__init__() - 'tids' argument "
                "must be a list: %s" % tids)
        if len(tids)==0:
            raise ValueError("langutil.py - Keyword.__init__() - 'tids' argument "
                "list must not be empty")

        self.st=st               # Statement name
        self.name=name.lower()   # Keyword name in a production symbol
        self.tid=name.upper()    # Keyword reserved word TID
        self.tids=tids           # TID(s) that match the argument
        self.required=required   # If True, this keyword is required
        self.multiple=multiple   # If True, multiple occurrences allowed
        self.default=default     # Default value if any
        self.value=Value(self.st,self.name,self.tids,ptrace=ptrace)
        
        # Attribute associated with production generation
        self.ptrace=ptrace

        # Attributes used by callback methods and set by the callbacks() method
        self.lang=None           # LL1parser instance

    def __str__(self):
        return "Keyword(name='%s',st='%s',required=%s,multiple=%s,default=%s)" \
            % (self.name,self.st,self.required,self.multiple,self.default)

    def callbacks(self,lang,dm):
        self.dm=dm               # Set the Debug manager
        self.lang=lang           # Set the LL1parser instance
        sym=self.symbol()
        for cb in Keyword.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_keyword_%s" % cb))
        self.value.callbacks(lang,dm)

    # Called when attempts to recognize a statement's keyword argument occurs.
    def cb_keyword_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Keyword.cb_keyword_beg(gs,pid='%s')" % pid)
            
        # Find the Keyword instance being recognized
        gs.keyword=gs.build.new_keyword(pid)   # Keyword instance
        
        # attributes used to recognize a keyword and its value
        gs.keyword_state=0
        gs.keyword_token=None     # Keyword name token set by cb_keyword_token()
        gs.keyword_argument=None  # Token set by Value.cb_argument_end()
        gs.keyword_eos=[]         # Keyword name token error list
        gs.keyword_equal_eos=[]   # Keyword equal error list

    # Called at the completion of the recogniztion of the keyword sequence
    def cb_keyword_end(self,gs,pid,failed=False,eo=[]):
        fun="langutil.py - Keyword.cb_keyword_end"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',failed=%s,eo=%s)" % (fun,pid,failed,eo))

        if failed:
            edebug=dm.isdebug("edebug")
            defn=gs.defn
            if edebug:
                print("langutil.py - Keyword.cb_keyword_end() - "
                    "gs.keyword_equal_eos: %s" % gs.keyword_equal_eos)
                print("langutil.py - Keyword.cb_keyword_end() - "
                    "gs.keyword_eos: %s" % gs.keyword_eos)
            for x in gs.keyword_equal_eos:
                who="'%s' statement argument '%s'" \
                    % (gs.stmt.name,gs.keyword)
                defn.token_errors(who,gs.keyword_equal_eos,debug=edebug)
            who="'%s' statement" % gs.stmt.name 
            defn.token_errors(who,gs.keyword_eos)
            gs.keyword_eos=[]
            return True

        # At this point tokens for both the keyword and its argument have been
        # recognized.  We can add it to the build
        build=gs.build
        name=gs.keyword.name            # Get the name from Keyword instance
        arg_tok=gs.keyword_argument     # Get the recognized argument token
        value=build.convert(arg_tok)    # Convert the argument token to a value
        arg=Key_Arg(name,value,ktoken=gs.keyword_token,atoken=arg_tok)
        build.keyword_add(arg)

    # This method is called when a token fails recognition with an ErrorToken
    # instance
    def cb_keyword_error(self,gs,pid,n,eo):
        fun="langutil.py - Keyword.cb_keyword_error"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,eo=%s)" % (fun,pid,n,eo))

        state=gs.keyword_state
        edebug=dm.isdebug("edebug")
        if state == 0:  # First time, this is the keyword's token
            KWlang.recognize_new_token_errors(gs.keyword_eos,[eo,],debug=edebug)
        elif state == 1:   # Second time, this is the EQUAL token (ignored)
            errors=KWLang.find_token_errors([eo,],debug=edebug)
            gs.keyword_equal_eos.extend(errors)
        else:
            raise ValueError("%s - 'gs.keyword_state' invalid value, not 0, 1, "
                "or 2: %s" % (fun,state))
        if edebug:
            print("%s - state=%s, gs.keyword_equal_eos: %s"\
                % (fun,state,gs.keyword_equal_eos))
            print("%s - state=%s, gs.keyword_eos: %s" \
                % (fun,state,gs.keyword_eos))
        return True

    # This method is called each time a keyword argument alternative fails.
    def cb_keyword_failing(self,gs,pid,n,eo=[],last=False):
        fun="langutil.py - Keyword.cb_keyword_failing"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
           print("%s(gs,pid='%s',n=%s,eo=%s,last=%s)" % (fun,pid,n,eo,last))
        if len(eo)>0:
            if dm.isdebug("edebug"):
                peo=KWLang.print_eo(eo,indent="    ")
                print("%s() - eo:\n%s" % (fun,peo))
            #KWLang.recognize_new_token_errors(gs.keyword_eos,eo,\
        return False

    # Called first when the keyword argument name has been recognized
    # Called second when the EQUAL separator has been recognized
    # Note: the argument itself calls cb_argument_xxxx() method
    def cb_keyword_token(self,gs,pid,n,tok):
        fun="langutil.py - Keyword.cb_keyword_token"
        if gs.dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,tok=%s)" % (fun,pid,n,tok))

        state=gs.keyword_state
        if state == 0:  # First time, this is the keyword's token
            gs.keyword_token=tok
        elif state == 1:   # Second time, this is the EQUAL token (ignored)
            pass
        else:
            raise ValueError("%s() - 'gs.keyword_state' invalid value, not 0, "
                "1: %s" % state)
        gs.keyword_state+=1

    def prods(self,la):
        eq=la.overrides["equal"]
        sym=self.symbol()
        vsym=self.value.symbol()
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p=""
        p="%s%s -> %s %s %s%s\n" % (p,sym,self.tid,eq,vsym,pt)
        p="%s%s" % (p,self.value.prods(la))
        return p
        
    # Generate my grammar symbol for the keywords grammatical definition.
    # It will be the <statement_name>_key_<keyword_name>
    def symbol(self):
        return "%s_key_%s" % (self.st,self.name.lower())
        
class Keywords(object):
    cbs=["beg","end"]
    def __init__(self,st,ptrace=False):
        self.st=st              # Statement name
        self.keys={}            # Keyword instances keyed to keyword name
        self.key_lst=[]         # Keyword instances in order
        self.pids_keys={}       # Dictionary of PIDs and Keyword instances

        # Attribute related to production generation
        # Causes 'statement_keys' and its alternatives traced. Set by Stmt
        # instance and based upon the Stmt ptrace argument.
        self.ptrace=ptrace

        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None             # Debug manager
        self.lang=None           # LL1parser instance

    def add(self,kwd):
        if not isinstance(kwd,Keyword):
            raise ValueError("langutil.py - Keywords.add() - 'kwd' argument must "
                "be an instance of Keyword: %s" % kwd)
        name=kwd.name
        if name in self.keys:
            raise ValueError("langutil.py - Keywords.add() - duplicate keyword "
                "for statement %s: %s" % (self.st,name))
        self.keys[name]=kwd
        self.pids_keys[kwd.symbol()]=kwd
        self.key_lst.append(kwd)
        
    def callbacks(self,lang,dm):
        self.lang=lang
        if len(self.key_lst)==0:
            return
        self.dm=dm               # Set the Debug manager
        self.lang=lang           # Set the LL1parser instance
        sym=self.symbol()
        for cb in Keywords.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_statement_keys_%s" % cb))
        for keyword in self.key_lst:
            keyword.callbacks(lang,dm)
        
    # Called when a statement's keyword arguments are starting to be recognized
    # This method also indicates the end of any positional argyments in the
    # statement
    def cb_statement_keys_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Keywords.cb_statement_keys_beg(gs,pid='%s')" \
                % pid)
        gs.build.new_keys()

    # Called when all keyword arguments have been recognized.
    def cb_statement_keys_end(self,gs,pid,failed=False,eo=[]):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Keywords.cb_statement_keys_end"
                "(gs,pid='%s',failed=%s,eo=%s)" % (pid,failed,eo))
        gs.build.keys_done()

    # Return the number of defined keywords
    def number(self):
        return len(self.key_lst)
        
    def pid2key(self,pid):
        try:
            return self.pids_keys[pid]   # Find the right Keyword instance
        except KeyError:
            raise ValueError("langutil.py - Keyword.pid2key() - INTERNAL: "
                "PID not recognized as Keyword for statement '%s': %s" \
                % (self.st,pid)) from None
        
    def prods(self,la):
        if len(self.key_lst)==0:
            return ""
        p=""
        sym_keys=self.symbol()
        sym_key=self.symbol_key()
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p="%s%s -> %s*%s\n" % (p,sym_keys,sym_key,pt)
        sym=self.symbol_key()
        for x in self.key_lst:
            p="%s%s -> %s%s\n" % (p,sym,x.symbol(),pt)
        p="%s%s -> %s%s\n" % (p,sym,la.overrides["empty"],pt)
        for x in self.key_lst:
            p="%s%s" % (p,x.prods(la))
        return p
        
    def symbol(self):
        if len(self.key_lst)==0:
            return ""
        return "%s_keys" % self.st
        
    def symbol_key(self):
        if len(self.key_lst)==0:
            return ""
        return "%s_key" % self.st

class Pos(object):
    cbs=["error","token",]
    def __init__(self,st,n,tids=[],ptrace=False):
        self.st=st               # Statement name
        self.n=n                 # Positional arguments position in the statement
        self.tids=tids           # TID's that match this positional argument
        
        # Attribute associate with production generation
        # Indicates whether tracing is enabled for the 'statement_pos_x'
        # production.
        self.ptrace=ptrace
        
        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None             # Debug manager
        self.lang=None           # LL1parser instance

    def callbacks(self,lang,dm):
        self.dm=dm               # Set the Debug manager
        self.lang=lang           # Set the LL1parser instance
        sym=self.symbol()
        for cb in Pos.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_positional_%s" % cb))

    # This method is called when a token fails recognition with an ErrorToken
    # instance
    def cb_positional_error(self,gs,pid,n,eo):
        fun="langutil.py - Pos.cb_positional_error"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,eo=%s)" % (fun,pid,n,eo))
        edebug=dm.isdebug("edebug")
        if edebug:
            print("%s eo:\n%s" % KWLang,print_eo(eo,indent="    "))
        gs.positional_eos.append(eo)

    # Called when a statment's positional argument has been recognized.
    def cb_positional_token(self,gs,pid,n,tok):
        fun="langutil.py - Pos.cb_positional_token"
        if gs.dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,tok=%s)" % (fun,pid,n,tok))

        gs.build.pos_add(pid,tok)

    # Generate the set of grammar productions that define the values of this
    # positional argument.  If a single token type matches this positional
    # argument this method returns an empty string.  Otherwise it will return
    # a string consisting of two or more productions each terminated with a 
    # new line.
    def prods(self,la):
        p=""
        sym=self.symbol()
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        for x in self.tids:
            p="%s%s -> %s%s\n" % (p,sym,x,pt)
        return p

    # Generate my grammar symbol within the position of the statement.
    # If there is a single TID, it will be the TID itself.
    # If it is a set of values, the symbol will be '<statement_name>_n'
    def symbol(self):
        return "%s_pos_%s" % (self.st,self.n)
        
class Positionals(object):
    cbs=["beg","end"]
    def __init__(self,st,ptrace=False):
        self.st=st         # Statement symbol
        self.pos=[]        # Pos instances
        self.pos_pids={}   # Dictionary of PIDs to Pos instances
        
        # Attribute associated with production generation
        # Specify 'True' to trace 'statement_pos' production.  Set by Stmt
        # instance and based upon the Stmt ptrace argument
        self.ptrace=ptrace
        
        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None       # Debug manager
        self.lang=None     # LL1parser instance

    # Reset the state of keyword processing
    def __reset_positional(self,gs):
        gs.positionals=None        # Tokens added to it by cb_positional_token()
        # Token errors added by cb_positional_error()
        gs.positional_eos=[]      # Error objects while recognizing positional
        return True

    # Add a positional argument to the statement.  Stmt.pos() method is the source
    # the ptrace argument.
    def add(self,tids,ptrace=False):
        n=len(self.pos)
        pos=Pos(self.st,n,tids=tids,ptrace=ptrace)
        self.pos_pids[pos.symbol()]=pos
        self.pos.append(pos)

    def callbacks(self,lang,dm):
        if len(self.pos)==0:
            return
        self.dm=dm            # Set the Debug manager
        self.lang=lang        # Set the LL1parser instance
        sym=self.symbol()
        for cb in Positionals.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_positionals_%s" % cb))
        for pos in self.pos:
            pos.callbacks(lang,dm)

    # Called when a statment's positional arguments are starting to recognized
    def cb_positionals_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Positionals.cb_positionals_beg(gs,pid='%s')" % pid)

        self.__reset_positional(gs)
        gs.positionals=gs.build.new_pos()

    # Called when recognition of a statement's positional arguments has completed.  
    # Failure implies a problem with the positional arguments.
    def cb_positionals_end(self,gs,pid,failed=False,eo=[]):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Positionals.cb_positionals_end"
                "(gs,pid='%s',failed=%s,eo=%s)" % (pid,failed,eo))
        build=gs.build
        defn=build.stmt
        num_req=defn.num_pos
        pos_num=len(gs.positionals)
        if failed:
            for x in gs.positional_eos:
                gs.mgr.report(x)
            self.semerror("cb_positionals_end",token=gs.statement_token,\
                message="'%s' statement %s of %s required positional arguments "
                "missing" \
                % (gs.statement.name,num_req-pos_num,num_req))
            self.__reset_positional(gs)
            return False
        if num_req!=pos_num:
            raise ValueError("langutil.py - Positionals.cb_positionals_end() - "
                "internal error: expected %s positional aguments encountered: %s" \
                % (num_req,pos_num))
            
        build.pos_done()

        #defn._set_positionals(gs.statement,gs.positionals)
        return False  # production errors should be reported

    # Returns the number of defined positionals
    def number(self):
        return len(self.pos)

    # Convert a PID to an index
    def pid2pos(self,pid):
        try:
            return self.pos_pids[pid]
        except KeyError:
            raise ValueError("langutil.py - Positionals.pid2ndx() - INTERNAL: "
                "PID unrecognized as statement '%s' positional argument: %s" \
                % (self.st,pid))

    def prods(self,la):
        if len(self.pos)==0:
            return ""
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p="%s ->" % self.symbol()
        pos=""
        for x in self.pos:
            p="%s %s" % (p,x.symbol())
            pos="%s%s" % (pos,x.prods(la))
        p="%s%s\n%s" % (p,pt,pos)
        return p

    def symbol(self):
        if len(self.pos)==0:
            return ""
        return "%s_pos" % self.st

class RWord(object):
    def __init__(self,tid,match):
        if not isinstance(tid,str):
            raise ValueError("langutil.py - RWord.__init__() - 'tid' argument "
                "must be a string: %s" % tid)
        if not isinstance(match,str):
            raise ValueError("langutil.py - RWord.__init__() - 'match' argument "
                "must be a string: %s" % match)
        self.match=match
        self.tid=tid

# These classes operates on reserved words or TID's.  Required positional and
# keyword arguments are defined when the Stmt instance is created.  Optional
# keyword argument of the statement are defined by the optional() method.
#
# Instance methods:
#   optional   Defines each optional keyword with its list of optional values and
#              its default.
class Stmt(object):
    cbs=["beg","end","error","failing","token"]
    def __init__(self,name,la,required=False,multiple=False,ptrace=False):
        # Define positional arguments from *args for statement 'name'.
        if not isinstance(name,str):
            raise ValueError("langutil.py - Stmt.__init__() - 'name' argument "
                "must be a string: %s" % name)
        if not isinstance(la,LA):
            raise ValueError("langutil.py - Stmt.__init__() - 'la' argument "
                "must be an instance of LA: %s" % la)
        self.name=name         # statement name
        self.required=required # statement in required
        self.multiple=multiple # statement may have multiple occurrences
        self.la=la             # Used to build lexical analyzer
        
        # Add the statement name as a reserved word
        self.tid=self.name.upper()
        self.la.res(RWord(self.tid,self.name))
        self.st=self.name.lower()        # The statement PID in lower case
        
        # Attribute related to production generation
        # Specify 'True' to cause tracing of 'statement', 'statement_pos' and
        # 'statement_keys' productions
        self.ptrace=ptrace
        
        # Attributes related to positional arguments
        self._pos=Positionals(self.name,ptrace=self.ptrace)
        self.num_pos=0
        
        # Attributes related to keyword arguments
        self._keys=Keywords(self.name,ptrace=self.ptrace)
        
        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None           # Debug manager
        self.lang=None         # LL1parser instance

    def __values(self,value=[]):
        if isinstance(value,str):
            v=[value,]
        elif isinstance(value,list):
            v=value
        else:
            raise ValueError("langutil.py - Stmt.__values() - 'value' argument "
                "definition not a string or list: %s" % value)
        tids=[]
        num_args=len(v)
        for n in range(num_args):
            arg=v[n]
            la=self.la
            if not isinstance(arg,str):
                raise ValueError("langutil.py - Stmt.__values() - 'value' list "
                    "member %s not a string: %s" % (n,arg))
            tid=arg.upper()
            la.res(RWord(tid,arg))  # Add the reserved word if needed
            tids.append(tid)
        return tids

    # Define my syntactical analyzer call back methods.
    def callbacks(self,lang,dm):
        self.dm=dm          # Set the Debug manager
        self.lang=lang      # Set the LL1parser instance
        sym=self.symbol()
        for cb in Stmt.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_statement_%s" % cb))
        self._pos.callbacks(lang,dm)
        self._keys.callbacks(lang,dm)

    # Called when a trying to recognize a specifc statement
    def cb_statement_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Stmt.cb_statement_beg(gs,pid='%s')" % pid)

        gs.statement_token=None  # Token recognizing start of the statement
        gs.statement_eos=[]      # List of accummultated token errors
        gs.stmt=gs.build.new_stmt(pid)

    # Called when the statement recognition process has completed.
    # Failure implies the statement was not recognized.
    def cb_statement_end(self,gs,pid,failed=False,eo=[]):
        dm=gs.dm
        fun="langutil.py - Stmt.cb_statement_end"
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',failed=%s,eo=%s)" % (fun,pid,failed,eo))
        if dm.isdebug("edebug") and len(eo)>0:
            peo=KWLang.print_eo(eo,indent="    ")
            print("%s - eo:\n%s" % (fun,peo))
        source="cb_statement_end"
        if failed:
            if dm.isdebug("edebug"):
                print("langutil.py - Stmt.cb_statement_end() - "
                    "gs.statement_eos: %s" % gs.statement_eos)
            gs.defn.token_errors("statement",gs.statement_eos)
            return

        # Set any default keyword value for those that have them
        # Receive a list of required keyword arguments that are missing.
        missing=gs.build.defaults()

        # If any, report missing required keyword arguments
        if len(missing)!=0:
            stmt_tok=gs.statement_token  # Use the statement token for errors
            name=gs.stmt.name
            kwlang=gs.kwlang
            for keyword in missing:
                kwlang.semerror("Stmt.cb_statement_end",token=stmt_tok,\
                    message="'%s' statement missing required keyword "
                    "argument '%s'" % (name,keyword))
            #return self.__reset_statement(gs)
            return

        gs.build.statement_done()
        # Statement instance will be now part of the result
        return True

    # This method is called when a token fails recognition with an ErrorToken
    # instance
    def cb_statement_error(self,gs,pid,n,eo):
        fun="Stmt.cb_statement_error"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("langutil.py - %s(gs,pid='%s',n=%s,eo=%s)" % (fun,pid,n,eo))
            
        edebug=dm.isdebug("edebug")
        if edebug :
            peo=KWLang.print_eo(eo,indent="    ")
            print("langutil.py - %s - eo:\n%s" % (fun,peo))
        KWLang.recognize_new_token_errors(gs.statement_eos,[eo,],debug=edebug)
        return True

    # This method is called each time a statement alternative fails.
    def cb_statement_failing(self,gs,pid,n,eo=[],last=False):
        fun="languitl.py - Stmt.cb_statement_failing"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,eo=%s,last=%s)" % (fun,pid,n,eo,last))
        if len(eo)>0:
            edebug=dm.isdebug("edebug")
            if edebug:
                peo=KWLang.print_eo(eo,indent="    ")
                print("%s - eo:\n%s" % (fun,peo))
            KWLang.recognize_new_token_errors(gs.statement_eos,eo,debug=edebug)
        return True

    # Called when the statement's starting token has been recognized
    def cb_statement_token(self,gs,pid,n,tok):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Stmt.cb_statement_token"
                "(gs,pid='%s',n=%s,tok=%s)" % (pid,n,tok))

        gs.statement_token=tok   # Saved for error reporting in global state
        gs.build.statement.set_stmt_tok(tok)

    # Define keyword arguments to the language for this statement
    #
    # Method arguments:
    #   keyword     Reserved word recognizing the keyword argument.  Required.
    #   val         One or more TID's recognizing the keyword argument's value.
    #               A sinlge TID is treated as a list of one item.
    #   required    Specifies whether the keyword argument is required.  Specify
    #               'True' if the keyword must be present in the statement.
    #               Specify 'False' if the keyword may be omitted.   Defaults
    #               to 'False'.
    #   multiple    Specifies whether the statement may have multiple occurrences
    #               of this keyword.  Specify 'True' if multiple occurences are
    #               allowed.  Specify 'False' if the only one occurrence is 
    #               allowed.
    #   default     Specify the default value for the keyword argument if it is
    #               not required and is ommitted from the statement.
    #   ptrace      Specify whether productions related to this keyword should
    #               be traced.  Specify 'True' to enable parser tracing of the
    #               productions.  Specify 'False' to disable parser tracing.
    #               Defaults to 'False'
    def keyword(self,keyword,val=[],required=False,multiple=False,default=None,\
                ptrace=False):
        if not isinstance(keyword,str):
            raise ValueError("langutil.py - Stmt.keyword() - 'keyword' "
                "argument not a string: %s" % keyword)
        tids=self.__values(val)
        self.la.res(keyword.upper())
        self._keys.add(\
            Keyword(keyword,self.st,tids=tids,required=required,multiple=multiple,\
                default=default,ptrace=ptrace))
       
    # Add a postional argument to the statement.
    # 
    # Method arguments:
    #   values    One or more TID's as a list.  A single TID is processed as a 
    #             list of one item.
    #   ptrace    Indicates whether the production for this positional argument
    #             should be traced.  Specify 'True' to enable production tracing
    #             Specify 'False' to disable production tracing. 
    #             Defaults to 'False'.
    def pos(self,values,ptrace=False):
        tids=self.__values(values)
        self._pos.add(tids,ptrace=ptrace)
        self.num_pos+=1

    # Return the grammar productions required to recognized this statement
    def prods(self,la):
        num_pos=self._pos.number()
        num_keys=self._keys.number()
        pos_sym=key_sym=""
        if num_pos:
            pos_sym=" %s" % self._pos.symbol()
        if num_keys:
            num_sym=" %s" % self._keys.symbol()
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p="\n# '%s' Statement Definition\n" % self.name
        p="%s%s -> %s%s%s%s\n" % (p,self.st,self.tid,pos_sym,num_sym,pt)
        if num_pos:
            p="%s%s" % (p,self._pos.prods(la))
        if num_keys:
            p="%s%s" % (p,self._keys.prods(la))
        return p

    # Return the grammar symbol associated with this statement definition
    def symbol(self):
        return self.st

class Value(object):
    cbs=["beg","end","error","failing","token",]
    def __init__(self,st,keyname,tids,ptrace=False):
        self.st=st
        self.key=keyname
        self.tids=tids
        
        # Attribute associated with production generation
        # Specified whether 'statement_key_word_args' is traced.
        self.ptrace=ptrace
        
        # Attributes used by callback methods and set by the callbacks() method
        self.dm=None           # Debug manager
        self.lang=None         # LL1parser instance

    def callbacks(self,lang,dm):
        self.dm=dm                # Set the Debug manager
        self.lang=lang            # Set the LL1parser instance
        sym=self.symbol()
        for cb in Value.cbs:
            lang.cbreg(sym,cb,getattr(self,"cb_argument_%s" % cb))

    # Called when a statement's keyword argument's value is about to be recognized.
    def cb_argument_beg(self,gs,pid):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Value.cb_argument_beg(gs,pid='%s')" % pid)
        gs.keyword_argument=None     # Set by cb_argument_end
        gs.argument_token=None       # Set by cb_argument_token
        gs.argument_eos=[]           # keyword argument error list

    # Called when recognition of a statement's keyword argument's value has
    # completed.  Failure implies the arguments value was not recognized.
    def cb_argument_end(self,gs,pid,failed=False,eo=[]):
        fun="langutil.py - Value.cb_argument_end"
        if gs.dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',failed=%s,eo=%s)" % (fun,pid,failed,eo))

        if failed:
            who="'%s' statement argument '%s' value" \
                    % (gs.stmt_def.name,gs.keyword)
            dm.defn.token_errors(who,gs.argument_eos)
            gs.argument_eos=[]
            return True 

        gs.keyword_argument=gs.argument_token
        return True

    # This method is called when a token fails recognition with an ErrorToken
    # instance
    def cb_argument_error(self,gs,pid,n,eo):
        fun="langutil.py - Value.cb_argument_error"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
            print("%s(gs,pid='%s',n=%s,eo=%s)" % (fun,pid,n,eo))
        edebug=dm.isdebug("edebug")
        if edebug and len(eo)>0:
            peo=KWLang.print_eo(eo,indent="    ")
            print("%s() - eo:\n%s" % (fun,peo))

        KWLang.recognize_new_token_errors(gs.argument_eos,[eo,],debug=edebug)
        return True

    # This method is called each time a keyword argument alternative fails.
    def cb_argument_failing(self,gs,pid,n,eo=[],last=False):
        fun="langutil.py - Value.cb_argument_failing"
        dm=gs.dm
        if dm.isdebug("cbtrace"):
           print("%s(gs,pid='%s',n=%s,eo=%s,last=%s)" % (fun,pid,n,eo,last))

        edebug=dm.isdebug("edebug")
        if edebug and len(eo)>0:
            peo=KWLang.print_eo(eo,indent="    ")
            print("%s() - eo:\n%s" % (fun,peo))
        LWLang.recognize_new_token_errors(gs.argument_eos,eo,debug=edebug)
        return True

    # Called when a statment's keyword argument's value has been recognized.
    def cb_argument_token(self,gs,pid,n,tok):
        if gs.dm.isdebug("cbtrace"):
            print("langutil.py - Value.cb_argument_token"
                "(gs,pid='%s',n=%s,tok=%s)" % (pid,n,tok))

        arg_tok=gs.argument_token
        if arg_tok is not None:
            raise ValueError("langutil.py - Value.cb_argument_token() - "
                "'gs.argument_token' already set: %s" % arg_tok)
        gs.argument_token=tok
        
    def prods(self,la):
        if self.ptrace:
            pt=" <trace>"
        else:
            pt=""
        p=""
        for tid in self.tids:
            p="%s%s -> %s%s\n" % (p,self.symbol(),tid,pt)
        return p

    def symbol(self):
        return "%s_key_%s_args" % (self.st,self.key)

# +-------------------------------------+
# |  Key-word Language Parsing Objects  |
# *-------------------------------------+

# All of these objects reside within the global Scope object during parsing.

class Build(object):
    def __init__(self,defn):
        if not isinstance(defn,Definition):
            raise ValueError("langutil.py - Build.__init__() - 'defn' argumnent "
                "must be an instance of Definition: %s" % defn)
        self.defn=defn         # Definition instance of this language
        self.dm=defn.dm        # Access the debug manager

        self.stmt_counts={}     # Maintains statement counts
        self.statements=[]      # Recognized statements (Statement objects)
        
        # These attributes maintain the definition of the current component
        # being recognized
        self.stmt=None         # Current Stmt instance being recognized
        self.pos=None          # Current Positionals instance being recognized
        self.key=None          # Current Keywords instance being recognized
        self.keyword=None      # Current Keyword instance being recognized
        
        self.statement=None    # Current Statement instance being built
        self.pos_args=None     # Current Pos_Args being built
        self.key_args=None     # Current Key_Args being built
        self.req_keys=[]       # Current missing required keywords
    
    # Returns the result of a smart token's convert() method or the recognized
    # string.
    def convert(self,token):
        try:
            return token.convert()
        except AttributeError:
            return token.string

    # Sets the default keyword values for those that have them and need them
    # Returns a list of missing required keyword names.
    def defaults(self):
        bdebug=self.dm.isdebug("bdebug")
        if bdebug:
            print("Build.defaults(): setting defaults for statement '%s' "
                "keywords, found %s:%s" \
                % (self.statement.name,len(self.key_args),self.key_args.print()))
        missing=self.key_args.defaults(self.key,debug=bdebug)
        return missing

    # Complete the keyword arguments setting any defaults.
    def keys_done(self):
        bdebug=self.dm.isdebug("bdebug")
        if bdebug:
            print("Build.keys_done(): all keywords for statement '%s' found" \
                % self.statement.name)
        #self.key_args.defaults(self.key,debug=bdebug)
        self.statement.add_key(self.key_args)

    # Add a recognized keyword argument to the statement
    def keyword_add(self,keyword):
        if not isinstance(keyword,Key_Arg):
            raise ValueError("langutil.py - Build.keyword_add() - 'keyword' "
                "argument must be an instance of Key_Arg: %s" % keyword)

        bdebug=self.dm.isdebug("bdebug")
        if bdebug:
            print("Build.keyword_add() - adding Keyword to statement '%s'"
                "\n    %s" % (self.statement.name,keyword))
        self.key_args.add(keyword,multiple=self.keyword.multiple,debug=bdebug)
        
    def new_keys(self):
        self.key=self.stmt._keys   # Current Keywords instance being recognized
        self.key_args=Key_Args()   # Current Key_Args being built
    
    def new_keyword(self,pid):
        self.keyword=self.key.pid2key(pid)
        return self.keyword
    
    # Resets everything to recognize a new set of positional arguments
    def new_pos(self):
        self.pos=self.stmt._pos    # Current Positionals being recognized
        self.pos_args=Pos_Args(self.stmt.num_pos)
        return self.pos_args       # SEE IF WE CAN ELIMINATE THIS!
    
    # Resets everything for a new statement
    def new_stmt(self,pid):
        # Set the definitional read-only objects for this statement
        self.stmt=self.defn.pid2stmt(pid)
        self.pos=None              # Set by new_pos()     Positionals instance
        self.key=None              # Set by new_key()     Keywords instance
        self.keyword=None          # Set by new_keyword() Keyword instance
        
        # Set the recogniztion time read-write objects
        self.statement=Statement(self.stmt)
        self.pos_args=None         # Set by new_pos(), reset by pos_done()
        self.key_args=None         # Set by new_key(), reset by key_done()

        return self.stmt

    # Add a recognized positional argument to the positionals.
    def pos_add(self,pid,token):
        if not isinstance(token,lexer.Token):
            raise ValueError("langutil.py - Build.pos() - 'token' argument must "
                "be an instance of lexer.Token: %s" % token)
        try:
            pos=self.pos.pid2pos(pid)
        except KeyError:
            raise ValueError("langutil.py - Build.pos() - PID not recognized as "
                "a '%s' statement positional argument: %s" \
                % (self.stmt.name,pid))
        cur_args=len(self.pos_args)
        if len(self.pos_args)!=pos.n:
            raise ValueError("langutil.py - Build.pos() - when adding '%s' "
                "statement positional argument %s encountered PID for argument "
                "%s" % (self.stmt.name,cur_args,pos.n))
            
        # Add the new argument to the list being built
        value=self.convert(token)
        self.pos_args.add(Pos_Arg(value,token))
        
    # Passes the recognized positional arguments to the Statement object and
    # resets the pos_args.
    def pos_done(self):
        self.statement.add_pos(self.pos_args)
        self.pos_args=None
        
    # Determine if any required statements are missing.  Issue an error if so.
    def required(self,defn):
        if not isinstance(defn,Definition):
            raise ValueError("langutil.py - Build.required() - 'defn' argumnent "
                "must be an instance of Definition: %s" % defn)
        
        stmts=self.defn._stmts     # Dictionary of defined statements
        kwlang=self.defn.kwlang
        for stmt in stmts.keys():
            s=stmts[stmt]             # Stmt instance
            if not s.required:
                continue
            # Stmt is required
            try:
                cnt=self.stmt_counts[stmt]
            except KeyError:
                # Not found in counts so required statement is missing
                message="required statement missing: '%s'" % s.name
                kwlang.semerror("__required_statements",\
                    type="",token=None,message=message)
    
    # Add the built statement and enforce multiple=False 
    def statement_done(self):
        if self.dm.isdebug("bdebug"):
            print("Build.statememt_done(): completing statement:%s" \
                % self.statement)
        name=self.statement.name
        try:
            cnt=self.stmt_counts[name]
            # this means we have seen at least one of these statements before
            if not self.stmt.multiple:
                # OOPS, can't have more than one, so generate an error
                message="'%s' statement may only occur once" % stmt.name
                self.kwlang.semerror("__statement_result",token=stmt._stmt_token,\
                    message=message)
                return  # without adding the statement to the results
        except KeyError:
            cnt=0

        self.stmt_counts[name]=cnt+1
        if self.dm.isdebug("bdebug"):
            print("Build.statement_done:\n%s" % self.statement)
        self.statements.append(self.statement)
        self.statement=None

class Key_Arg(object):
    def __init__(self,name,value,ktoken=None,atoken=None):
        if not atoken is None:
            if not isinstance(ktoken,lexer.Token):
                raise ValueError("langutil.py - Key_Arg.__init__() - 'ktoken' "
                    "argument must be an instance of lexer.Token: %s" % ktoken)
            if not isinstance(atoken,lexer.Token):
                raise ValueError("langutil.py - Key_Arg.__init__() - 'atoken' "
                    "argument must be an instance of lexer.Token: %s" % atoken)
        self.name=name
        self.value=value
        self.ktoken=ktoken
        self.atoken=atoken   # None indicates the default value was used
    def __str__(self):
        if self.atoken is None:
            return "Key_Arg(name='%s',default=%s)" % (self.name,self.value)
        return "Key_Arg(name='%s',value=%s,\n    ktoken=%s,\n    atoken=%s" \
            % (self.name,self.value,self.ktoken,self.atoken)

class Key_Args(object):
    def __init__(self):
        self.keywords={}         # Dictionary of keyword name to Key_Arg instances

    # Returns the item's value or list of values.  May raise a KeyError.
    def __getitem__(self,item):
        i=self.keywords[item]
        if isinstance(i,list):
            values=[]
            for x in i:
                values.append(x.value)
            return values
        return i.value

    def __len__(self):
        return len(self.keywords)

    def add(self,keyword,multiple=False,debug=False):
        if not isinstance(keyword,Key_Arg):
            raise ValueError("langutil.py - Key_Args.add() - 'keyword' argument "
                "must be an instance of Key_Arg: %s" % keyword)
        name=keyword.name
        if multiple:
            try:
                kwds=self.keywords[name]
            except KeyError:
                kwds=[]
            kwds.append(keyword)
            self.keywords[name]=kwds
        else:
            try:
                kwd=self.keywords[name]
                raise ValueError("langutil.py - Key_Args.add() - INTERNAL "
                    "multiple values not supported for keyword: '%s'" % keyword)
            except KeyError:
                self.keywords[name]=keyword
        if debug:
            kwd=self.keywords[name]
            print("Key_Args.add(): keywords=%s" % len(self.keywords))
            print("Key_Args.add(): keyword '%s':\n%s" % (name,kwd))

    # This method sets the defaults
    def defaults(self,keywords,debug=False):
        if not isinstance(keywords,Keywords):
            raise ValueError("langutil.py - Key_Args.defaults() - 'keyword' "
                "argument must be an instance of Keywords: %s" % keywords)
        missing=[]
        for keyword in keywords.keys.values():
            if debug:
                print("Key_Args.defaults(): ckecking %s" % keyword)
            name=keyword.name
            try:
                keyarg=self.keywords[name]  # Get Key_Arg instance
                if debug:
                    print("Key_Args.defaults(): found %s" % keyarg)
            except KeyError:
                if debug:
                    print("Key_Args.defaults(): not found keyword '%s'" % name)
                if keyword.required:
                    if debug:
                        print("Key_Args.defaults(): required missing '%s'" % name)
                    missing.append(name)
                    continue
                default=keyword.default
                if default is not None:
                    defarg=Key_Arg(name,default)
                    if debug:
                        print("Key_Args.defaults(): adding default %s" % defarg)
                    self.add(defarg,multiple=keyword.multiple,debug=debug)
        return missing
    
    def keys(self,sort=False):
        lst=list(self.keywords.keys())
        if sort:
            lst=sorted(lst)
        return lst
    
    def print(self,indent=""):
        keys=list(self.keywords.keys())
        srt=sorted(keys)
        string=""
        for k in srt:
            arg=self.keywords[k]
            string="%s\n%s%s='%s'" % (string,indent,arg.name,arg.value)
        return string

class Pos_Arg(object):
    def __init__(self,value,token):
        if not isinstance(token,lexer.Token):
            raise ValueError("langutil.py - Pos_Arg.__init__() - 'token' "
                "argument must be an instance of lexer.Token: %s" % token)
        self.token=token
        self.value=value
    def __str__(self):
        return "Pos_Arg(value=%s,token=%s)" % (self.value,self.token)

class Pos_Args(object):
    def __init__(self,n):
        self.num=n          # Number of positional arguments
        self.args=[]        # List of Pos_Arg instances

    def __str__(self):
        string=""
        for arg in self.args:
            string="%s\n%s" % (string,arg)
        return string

    # Returns the positional argument's value
    def __getitem__(self,item):
        return self.args[item].value

    def __len__(self):
        return len(self.args)

    def add(self,arg):
        if not isinstance(arg,Pos_Arg):
            raise ValueError("langutil.py - Pos_Args.add() - 'arg' argument must "
                "be an instance of Pos_Arg: %s" % arg)
        self.args.append(arg)
        
    def print(self,indent=""):
        string=""
        for arg in self.args:
            string="%s\n%s%s" % (string,indent,arg.value)
        return string

# +----------------+
# |  Smart Tokens  |
# *----------------+

# Smart tokens understand a specific character encoding of certain frequently 
# encountered data types.  They also provide a mechanism for conversion of the
# recognized string data into a Python data type.  Each smart token is defined
# by a subclass of lexer.Type that recognizes the data and a subclass of 
# lexer.Token that provides the conversion mechanism for use by semantic analysis.
# A token id must be supplied with each smart token type recognizer.
#
# The following smart tokens are supported:
#
#   Type      Token   Default
# subclass   subclass   TID     Description
#
#  BinType   BinToken   BIN   Recognizes binary data: 0b0101 or B'0101'
#  CmtType   CmtToken   CMT   Recognizes comments.
#  DecType   DecToken   DEC   Recognizes decimal data: 500, or +500 or -500
#  HexType   HexToken   HEX   Recognizes hexadecimal data: 0x535  or X'535'
#                             Various combinations of encoding and alpha case are 
#                             supported.
#  NamType   NamToken   NAME  Recognizes names of alphabetic, numeric and special
#                             characters.
#  NLType    NLToken    NL    Platform independently recognizes new lines.
#  StgType   StgToken   STG   Recognizes storage sizes with units: 
#                             B, K, M, G, T, P or E.
#  StrType   StrToken   STR   Recognizes single, double quoted strings or both
#  WordType  WordToken  none  Recognizes a one or more strings as part of the type
#  WsType    WsToken    WS    Recognizes white space

# The token generated by DecType.  
# The convert() method returns an integer from recognized string
class BinToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        # Ignore starting B' and ending quote
        return int(self.string[2:-1],2)

# This token type recognizes a binary strings.  The binary string may be 
# coded using either the:
#   - GNU as convention.  A '0b' precedes the binary digits.  For example: 0b1011
#   - ASM conventions.  A "B'" precedes the binary digits which are followed by
#     a closing singe quote.  For example: B'1011'.
#
# Which format(s) are recognized is specified by setting the format argument:
#   - 'b' - GNU as and ASM conventions.  (This is the default)
#   - 'g' - GNU as convention only
#   - 'i' - ASM convention only uppercase only
#   - 'im' - ASM convention upper or lower case
class BinType(lexer.Type):
    exp={"g":r"0b[01]+",
         "i":r"B'[01]+'",
         "im":r"[Bb]'[01]+'",
         "b":r"0x[01]+|X'[01]+'"}
    def __init__(self,tid="BIN",format="b",debug=False):
        try:
            exp=BinType.exp[format]
        except KeyError:
            raise ValueError("langutil.py - BinType - invalid format: '%s'" % format)
        super().__init__(tid,exp,tcls=BinToken,debug=debug)

# The token generated by CmtType.  
# The convert() method returns the recognized comment (if needed).
class CmtToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string

# This method defines a token type that recognizes comments starting with a special
# character.  The character is specified by the char argument.  It defaults to
# a '#' character.
class CmtType(lexer.Type):
    def __init__(self,tid="CMT",char="#",ignore=True,debug=False):
        exp="%s%s" % (char[0],r"[^\n]*")
        super().__init__(tid,exp,tcls=CmtToken,ignore=ignore,debug=debug)

# The token generated by DecType.  
# The convert() method returns an integer from recognized string
class DecToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return int(self.string,10)

# This method defines a token Type that recognizes signed/unsigned decimal input.
# Specify sign=True to recognize an optional '+' or '-' sign preceding the digits.
# Specify sign=False to only recognize decimal digits.
class DecType(lexer.Type):
    def __init__(self,tid="DEC",sign=True,debug=False):
        if sign:
            exp_sign=r"[\+-]?"
        else:
            exp_sign=""
        exp="%s%s" % (exp_sign,r"[0-9]+")
        super().__init__(tid,exp,tcls=DecToken,debug=debug)

# The token generated by HexType.
# The convert() method returns an integer from recognized string
class HexToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        if self.string[:2]=="X'" or self.string[:2]=="x'":
            hexdigits=self.string[2:-1]  # Drop the beginning "X'" and ending "'"
        else:
            hexdigits=self.string[2:]    # Drop the beginning "0x"
        return int(hexdigits,16)

# This token type recognizes a hexadecimal strings.  The hexadecimal string may be 
# coded using either the:
#   - GNU as convention.  A '0x' precedes the hexadicimal digits.  For example: 0x5F
#   - ASM conventions.  A "X'" precedes the hexadecimal digits which are followed by
#     a closing singe quote.  For example: X'5F'.
# The alpha hexadecimal characters may be coded using upper or lower case.
#
# Which formats are recognized is specified by setting the format argument: 
#   - 'gl' - GNU as lower case alpha (This is the typical GNU as encoding, like C)
#   - 'il' - ASM lower case alpha
#   - 'gm' - GNU as with either lower or upper case alpha
#   - 'im' - ASM with either lower or upper case
#   - 'gu' - GNU as upper case alpha
#   - 'iu' - ASM upper case (This is the typical ASM encoding)
#   - 'bl' - GNU as and ASM with lower case alpha
#   - 'bm' - GNU as and ASM with lower or upper case alpha (This is the default)
#   - 'bu' - GNU as and ASM with upper case alpha
#   - 'bt' - Recognizes GNU as with lower case and ASM with upper case alpha
class HexType(lexer.Type):
    exp={"gl":r"0x[0-9a-f]+",
         "il":r"X'[0-9a-f]+'",
         "gm":r"0x[0-9a-fA-F]+",
         "im":r"[Xx]'[0-9a-fA-F]+'",
         "gu":r"0x[0-9A-F]+",
         "iu":r"X'[0-9A-F]+'",
         "bl":r"0x[0-9a-f]+|X'[0-9a-f]+'",
         "bm":r"0x[0-9a-fA-F]+|X'[0-9a-fA-F]+'",
         "bu":r"0x[0-9A-F]+|X'[0-9A-F]+'",
         "bt":r"0x[0-9a-f]+|X'[0-9A-F]+'"}
    def __init__(self,tid="HEX",format="bm",debug=False):
        try:
            exp=HexType.exp[format]
        except KeyError:
            raise ValueError("langutil.py - HexType - invalid format: '%s'" % format)
        super().__init__(tid,exp,tcls=HexToken,debug=debug)

# The token generated by NamType.
# The convert() method returns an the name as a string
class NamToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string

# This class recognizes names starting with an alphabetic character followed by 
# any number of alphabetic characters, number, 0 through 9.  Various environments
# allow additional characters to be used within a name, for example an underscore,
# '_', or dollar sign, '$'.  These additional characters are specified as a string
# argument to the instance argument 'special'.  The 'first' argument provides the
# specification of special characters that may start a name.  The 'end' argument
# allows specification of a specific ending sequence.
class NamType(lexer.Type):
    def __init__(self,tid="NAME",tcls=NamToken,first="",special="",end="",debug=False):
        if not isinstance(special,str):
            raise ValueError("langutil.py - NamType - requires 'special' to be a"
                "string: %s" % special)
        exp="[a-zA-Z%s][a-zA-Z0-9%s]*%s" % (first,special,end)
        super().__init__(tid,exp,tcls=tcls,debug=debug)

# The token generated by NLType.
# The convert() method returns a string containing the number of recognized new
# lines.
class NLToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string

# This class recognizes new lines.  Because is uses Python's '\n' designation,
# new line recognition is platform independent.
class NLType(lexer.Type):
    def __init__(self,tid="NL",ignore=True,debug=False):
        super().__init__(\
            tid,r"(?m)\n+",eol=True,tcls=NLToken,ignore=ignore,debug=debug)

# The token generated by StgType.
# The convert() method returns an integer for the recognized storage quantity and
# units in bytes.
class StgToken(lexer.Token):
    units={"B":1,
           "K":1024,
           "M":1048576,
           "G":1073741824,
           "T":1099511627776,
           "P":1125899906842624,
           "E":1152921504606846976}
    def __init__(self):
        super().__init__()
    def convert(self):
        unit=self.string[-1]
        try:
            unit=StgToken[unit]
        except KeyError:
            raise ValueError("langutil.py - StgToken - internal error: StgType "
                "accepted a unit not recognized by StgToken: %s" % unit)
        quantity=int(self.string[:-1],10)
        return unit*quantity

# This class recognizes storage size designations with these size units:
#   B  =  1 byte
#   K  =  1,024 bytes
#   M  =  1,048,576 bytes or 1024K
#   G  =  1,073,741,824 bytes or 1024M
#   T  =  1,099,511,627,776 bytes or 1024G
#   P  =  1,125,899,906,842,624 bytes or 1024T
#   E  =  1,152,921,504,606,846,976 bytes or 1024P
#
# Class instance arguments:
#   tid     The token id used by this token type
#   units   A string containing the valid units recognized by the token.
#           By default all units defined above are accepted.  If explictly specified
#           they may be in any order.
# Note: An instance of this type should be defined by to a lexer before an instance 
# of DecType class.  Otherwise DecType will recognize the numeric portion of the
# storage size string and leave the unit as unrecognized or recognized as another
# token type.
class StgType(lexer.Type):
    def __init__(self,tid="STG",units="BKMGTPE",debug=False):
        if not isinstance(units,str):
            raise ValueError("langutil.py - StgType - requires 'units' to be a"
                "string: %s" % units)
        for x in range(len(units)):
            u=units[x]
            if u not in ["B","K","M","G","T","P","E"]:
                raise ValueError("langutil.py - StgType - invalid unit at position "
                    "%s: %s" % (x+1,u))
        exp="[0-9]+[%s]" % units
        super().__init__(tid,exp,tcls=StgToken,debug=debug)

# The token generated by StrType.
# The convert() method returns the string without enclosing quotes
class StrToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string[1:-1]

# This class recognizes single and/or double quoted strings.
# The type of enclosing quotes is specified by the quotes argument.
#   'd' - Recognizes strings enclosed by double quotes: "a string"
#   's' - Recognizes strings enclosed by single quotes: 'a string'
#   'sd' or 'ds' - Recognizes strings enclosed by either single or double quotes.
# Default quotes values is 'd'.
class StrType(lexer.Type):
    double='"[^"]*"'
    single="'[^']*'"
    def __init__(self,tid="STR",quotes="d",debug=False):
        if not isinstance(quotes,str):
            raise ValueError("langutil.py - StrType - requires 'quotes' to be a"
                "string: %s" % quotes)
        single=False
        double=False
        for x in range(len(quotes)):
            q=quotes[x]
            if q == "d":
                double=True
            elif q == "s":
                single=True
            else:
                raise ValueError("langutil.py - StrType - invalid quote at position "
                    "%s: %s" % (x+1,q))
        exp=[]
        if single:
            exp.append(StrType.single)
        if double:
            exp.append(StrType.double)
        exp="|".join(exp)
        super().__init__(tid,exp,tcls=StrToken,debug=debug)

# The token generated by WordType when case=None or defaults
# The convert() method returns the recognized word.
class WordToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string

# The token generated by WordType when case="lower".
# The convert() method returns the recognized word in lower case.
class WordTokenLower(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string.lower()

# The token generated by WordType when case="upper".
# The convert() method returns the recognized word in upper case.
class WordTokenUpper(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string.upper()

# This class recognizes a series of words as part of a specific type.  This type
# allows multiple words to grouped together as a single type.  Words are specified
# in a list of strings. The first two characters of the string define the 
# recognition case sensitivity and the remainder of the string identifies the
# characters recognized by the string.
#
# The following case sensitivities are allowed:
#   L:  - only lower case recognized
#   U:  - only upper case recognized
#   E:  - either all upper case or all lower case, but not mixed, is recognized
#   M:  - mixed case is recognized
#  If case sentivity is not provided the word is recognized as supplied.  These
#  values effect recognition of words in input text.
#
# Instance arguments:
#   tid    Token type id (required).
#   words  The list of word specifiers
#   case   Specifies the case of the word presented to the language processor
#          internally via the convert method of the Token instance
#          Specify 'upper' for smart token to return word in upper case
#          Specify 'lower' for smart token to return word in lower case
#          Specify None for smart token to return string as recognized.
#          Defaults to None.
class WordType(lexer.Type):
    def __init__(self,tid,words=[],case=None,debug=False):
        if case == "upper":
            cls=WordTokenUpper
        elif case == "lower":
            cls=WordTokenLower
        elif case is None:
            cls=WordToken
        else:
            raise ValueError("langutil.py - WordType - 'case' argument invalid: "
                "%s" % case)
        if not isinstance(words,list):
            wds=[words,]
        else:
            wds=words

        # Dictionary of methods corresponding to case sensitivity
        redict={"E:":self._either,
                "L:":self._lower,
                "M:":self._mixed,
                "U:":self._upper}

        # dictionary of input words to regular expressions       
        expr={}
        for x in range(len(wds)):
            w=wds[x]
            if not isinstance(w,str):
                raise ValueError("langutil.py - WordType - words[%s] not a string:"
                    " %s" % (x,w))
            case=w[:min(len(w),2)]
            try:
                m=redict[case]
                expr[w]=m(w[2:])
            except KeyError:   
                expr[w]=w

        # Sort the words so that the greediest word is recognized first.
        strings=[]
        for w in expr:
            strings.append(w)
        order=sorted(strings,reverse=True)
        # Build a list of regular expressions in recognition order.
        exp=[]
        for x in order:
            exp.append(expr[x])
        # Join the individual expressions into one big one
        exp="|".join(exp)
        super().__init__(tid,exp,tcls=cls,debug=debug)

    # Return a regular expression recognizing all upper or all lower case
    def _either(self,word):
        return "%s|%s" % (word.upper(),word.lower())

    # Return a regular expression recognizing the letters in lower case
    def _lower(self,word):
        return word.lower()

    # Return a regular expression recognizing the letters in mixed case
    def _mixed(self,word):
        exp=""
        for x in range(len(word)):
            letter=word[x]
            if letter.islower():
                exp="%s[%s%s]" % (exp,letter.upper(),letter)
                continue
            if letter.isupper():
                exp="%s[%s%s]" % (exp,letter,letter.lower())
                continue
            exp="%s%s" % (exp,letter)
        return exp

    # Return a regular expression recognizing the word in upper case
    def _upper(self,word):
        return word.upper()

# The token generated by WsType.
# The convert() method returns the recognized white space 
class WsToken(lexer.Token):
    def __init__(self):
        super().__init__()
    def convert(self):
        return self.string

# This class recognizes white space: spaces, vertical or horizontal tabs, form feed,
# or carriage return.
# Note: because the regular expression does not include the MULTILINE option, the
# linefeed sequence is not recognized by the WsType.  Only the NLType class 
# recognizes the linefeed.
class WsType(lexer.Type):
    def __init__(self,tid="WS",ignore=True,debug=False):
        super().__init__(tid,r"[ \t\r\f\v]+",tcls=WsToken,ignore=ignore,\
            debug=debug)

# +-------------------------------+
# |  Key-Word Language Processor  |
# *-------------------------------+

#    KWLang       The base class used to implement a Key-Word language by a 
#                 subclass.  It is a subclass of lang.Lanuage and parser.Parser.
#    Statement    An instance of this object is returned for each successfully
#                 recognized statement.

# This is the lexer built internally by KWLang.  It is not referenced externally.
class _KWLexer(lexer.Lexer):
    def __init__(self):
        super().__init__()
    def init(self,types):
        # Register all of the supplied types
        for x in types:
            self.type(x)
        return self

# This class allows a subclass to create and process a key-word oriented language.
# The subclass registers the token types it has of interest.  These TID's are
# used to build the recognizing grammar and basic semantic processing.  All tokens
# should be registered before being referenced by a statement or keyword 
# definition.
#
# When KWLang is created it is possible to override the default required token
# type TID's.  This allows resolution of conflicts between reserved words which
# might need to use the same string as a TID as the default token types.
#
# Instance arguments:
#   cmt            TID of comment token type.  Defaults to "CMT".
#   empty          TID of empty Tokne type.  Defaults to "EMPTY".
#   eos            TID of end-of-stream token type.  Defaults to "EOS".
#   equal          TID of equal '=' token type.  Defaults to "EQUAL".
#   nl             TID of new-line token type.  Defaults to "NL".
#   ws             TID of white space token type.  Defaults to "WS".
#
# KWLang instance methods used by a KWLang subclass:
#   begin          Returns a Definition instance throuhg which the specific 
#                  language is defined.  All statement, reserved word and optional
#                  token types are defined by means of the Definition object.
#   token          Defines registered token types by TID.  TID's must be upper
#                  case.
#   init_lang      Method used by a subclass to initialize language processing
#                  after all token types have been registerd and statements 
#                  have been defined.  The keyword language processor is now ready
#                  for use of the methods described next.
#
# lang.Processor instance methods used by a KWLang subclass
#
#   errors         Returns the number of currently encountered errors.
#
# KWLang instance methods used by a KWLang subclass or user of the subclass itself.
# This allows language processing to be controlled by
#   - either the specific instance of a keyword language or
#   - instantiator of the keyword language.
#
#   analyze        Parses and processes text statements.  Results in a list of
#                  Statement instances returned to the method caller for
#                  additional semantic processing.
#   report         Produce the consolidated error report.
#   semerror       Report semantic errors to the error manager for consolidated 
#                  reporting.
#
# KWLang is a subclass of lang.Processor.
#
#  Methods supplied by KWLang for lang.Processor:
#       Method        Description
#    create_lexer   returns an instance of lexer.Lexer with registered token types.
#                   Token types are registered by the KWLang subclass by using the
#                   KWLang.token() method before calling KWLang.init_lang()
#    define_parser  Returns a tuple of the language grammar and starting PID.
#                   KWLang builds the grammar based upon statements registered with
#                   KWLang by the subclass using the KWLang.statements() method
#                   before calling KWLang.init_lang().
#
#  Methods supplied by KWLang for parser.Parser:
#     init          Enables debugging options for parser.  And establishes 
#                   KWLang call back methods.
#
class KWLang(lang.Processor):
    # Extract token errors from error list
    def find_token_errors(eo,debug=False):
        fun="langutil.py - KWLang.find_token_errors"
        if debug:
            print("%s eo: %s" % (fun,eo))
        lst=[]
        for x in eo:
            if isinstance(x,LL1parser.ErrorToken):
                lst.append(x)
        if debug:
            print("%s returning: %s" % (fun,lst))
        return lst
    
    # Returns a string of printed eo list entries with optional indenting
    @staticmethod
    def print_eo(eo,indent=""):
        if isinstance(eo,list):
            lst=eo
        else:
            lst=[eo,]
        string=""
        for x in lst:
            string="%s%s%s\n" % (string,indent,x.print(string=True))
        if len(string)>0:
            string=string[:-1]  # remove last '\n'
        return string

    # Finds token errors in the error object list (eo) and adds them to the list
    # of token error objects (te).
    @staticmethod
    def recognize_new_token_errors(te,eo,debug=False):
        fun="langutil.py - KWLang.recognize_new_token_errors"
        lst=KWLang.find_token_errors(eo,debug=debug)
        if debug:
            print("%s, y lst=%s" % (fun,lst))
            print("%s, x te=%s" % (fun,te))
        if len(te)==0:
            add=lst
        else:
            add=[]
            for x in te:
                for y in lst:
                    compare=parser.Error.compare(y,x)
                    print("__recognize_new_token_error:\n"
                          "   y=%s\n"
                          "   x=%s\n"
                          "   y:x == %s" % (y,x,compare))
                    if compare==0:
                        continue
                    add.append(y)
        if debug:
            print("%s - extending error list with: %s" % (fun,add))
        te.extend(add)

    def __init__(self,cmt="CMT",empty="EMPTY",eos="EOS",equal="EQUAL",nl="NL",\
                 ws="WS"):
        super().__init__()
        self.dm=None      # Debug manager supplied by init_lang() method

        # Classes related to the definition of a language
        # The LA (lexical analyzer) class
        la=LA()
        la.req(WordType(equal,words="="),"equal")
        la.req(WsType(tid=ws),"ws")
        la.req(CmtType(tid=cmt),"cmt")
        la.req(NLType(tid=nl),"nl")
        la.req(lexer.EOSType(tid=eos),"eos")
        la.req(lexer.EmptyType(tid=empty),"empty")
        self._la=la
        
        # The Definition instance provided by the begin() method
        self._defn=Definition(self._la,self)

        # Language processing performed by basic tools
        self._grammar=None
        self._lexer=None
        self._parser=None
        self.gs=None         # Returned by lang.Language.analyze() method
        self.recovery=False  # Parser recovery flag.  Set by init_lang() method

        # Statements (Statement instances) recognized by language processing
        self._statements=[]   # See cb_statement_end() method
        self._stmt_counts={}  # Number of occurrences of the statement

    # Initialize the grammar kew-word language syntactic processing.
    def __init_grammar(self,kdebug=False):
        g="# %s Key-Word Language Grammar\n\n" % self.__class__.__name__
        g="%s%s" % (g,self._defn.prods())
        if kdebug:
            print("Generated Grammar:\n")
            pt=satkutil.Text_Print(g)
            pt.print()
        self._grammar=g
        return

    # Initializes the lexer
    def __init_lexer(self,incase="L",outcase="lower",kdebug=False,tdebug=False):
        self._lexer=self._la.create(self.dm,incase=incase,outcase=outcase)
        if kdebug:
            self._lexer.types()

    # Overrides lang.Language default analyze method
    # May raise the ParserAbort exception if recovery=False and an error is 
    # detected by the parser.
    #
    # Method arguments:
    #   text      The input text string being parsed into Statement instances.
    #   sdebug    Specifies whether the input token stream from the lexical
    #             analyzer should be printed.  Specify 'True' to cause the 
    #             token stream to be printed.  Specify 'False' to inhibit printing.
    #             Defaults to 'False'.
    #   abort     Indicates how the Keyword Lanuage should handle a ParserAbort
    #             exception.  Specify 'None' to disable catching of the raised
    #             exception.  Specify an integer value to indicate the value
    #             returned by sys.exit() when the exception is caught.  Defaults
    #             to 2 (also implying the ParserAbort exception is caught here.
    def analyze(self,text,sdebug=False,abort=2):
        if abort is None:
            handle=False
        elif isinstance(abort,int):
            rc=abort
            handle=True
        else:
            raise ValueError("langutil.py - KWLang.analyze() - 'abort' argument "
                "not 'None' or an integer: %s" % abort) 

        # Set these local attributes so that they are consistent in each call
        # to analyze
        rec=self.recovery
        d=20
        l=True
        f=False

        # Call the lang.analyze() method either wrapped with a try/except or 
        # without.  This does the actual parsing and conversion to Statement
        # instances via the various callback methods.
        edebug=self.dm.isdebug("edebug")
        pa=None
        if handle:
            if edebug:
                print("langutil.py - KWLang.analyze() - will catch ParserAbort "
                    "exception")
            try:
                gs=self.lang.analyze(text,recovery=rec,depth=d,lines=l,fail=f)
            except LL1parser.ParserAbort as pao:
                if edebug:
                    print("langutil.py - KWLang.analyze() - ParserAbort "
                        "exception caught")
                pa=pao
        else:
            if edebug:
                print("langutil.py - KWLang.analyze() - not catching "
                    "ParserAbort exception")
            gs=self.lang.analyze(text,recovery=rec,depth=d,lines=l,fail=f)
            
        # Display input tokens if requested.
        if sdebug:
            self.lang.tokens()
            
        # Respond to the ParserAbort exception if caught
        if not pa is None:
            pa.print()
            sys.exit(rc)
            
        # Normal return from the analyze() method
        self.gs=gs
        return self.gs.build.statements   # Return the results from Build object

    # This method begins a language definition using the Stmt class by creating
    # an instance of the Definition class and an underlying LA class instance.
    # Stmt class instances are added to the returned definition class by the 
    # KWLang sub class being constructed.
    #
    # Method arguments
    #   ptrace      Specifies whether tracing of the 'start' and 'statements'
    #               productions are to be enabled.  Specify 'True' to enable
    #               parser tracing.  Specify 'False' to disable tracing.
    #               Defaults to 'False'.
    def begin(self,ptrace=False):
        if ptrace:
            self._defn.ptrace=ptrace
        else:
            self._defn.ptrace=False
        return self._defn         # Return the Definition instance.

    # Method supplied by subclass defining the keyword language and initilizing
    # the embedded parser.  It also returns the debug manager to be used
    # Required by lang.Processor
    def configure(self,lang,dm=None):

        self._defn.callbacks(lang,self.dm)
        # Establish generic call backs
        return self.dm   # Pass along the Debug Manager provided by init_lang()

    # Required by lang.Processor - provide the lexical analyzer
    def create_lexer(self):
        return self._lexer

    # Required by lang.Processor - provides the grammar and starting production
    def define_parser(self):
        return (self._grammar,"start")

    # Filter the input tokens for just the ones I need
    # Overrides parser.Parser.filter() default handling
    def filter(self,gs,tok):
        if tok.istype("unrecognized"):
            eo=LL1parser.ErrorUnrecognized(tok)
            if self.recovery:
                if self.dm.isdebug("edebug"):
                    print("langutil.py - KWLang.filter() - reporting eo=\n    %s"\
                        % eo)
                gs.mgr.report(eo)
                return None

            if self.dm.isdebug("edebug"):
                print("langutil.py - KWLang.filter() - raising ParserAbort "
                        "exception due to unrecognized input token")
            raise LL1parser.ParserAbort(eo=eo)
      
        if tok.ignore:
            return None
        return tok

    # Initializes the language processing components
    def init_lang(self,dm=None,recovery=False,incase="L",outcase="upper"):
        if recovery:
            self.recovery=recovery
        else:
            self.recovery=False
        if dm is None:
            self.dm=satkutil.DM(parser=True,langutil=True,lexer=True)
        else:
            self.dm=dm

        kdebug=self.dm.isdebug("kdebug")
        tdebug=self.dm.isdebug("tdebug")
        gdebug=self.dm.isdebug("gdebug")
        self.__init_lexer(incase=incase,outcase=outcase,\
            kdebug=kdebug,tdebug=tdebug)
        self.__init_grammar(kdebug=kdebug)
        # Now initialize the parser, process the grammer and make it ready to use
        self.init()  # Instantiate the language.
        if gdebug:
            self.lang.productions()

    # Print accumulated errors with help of the error manager
    def report(self):
        self.lang.gs.mgr.print(debug=self.lang.isdebug("edebug"))

    # Report a semantic error to the error manager
    # Method arguments:
    #    source    A string identifying where the error was generated.
    #    token     The lexer.Token associated with the error.  Used to identify
    #              where in the source text the error occurred and influences
    #              where the error is reported to the user.
    def semerror(self,source,type="S",token=None,message=""):
        eo=KWSemanticError(source,type=type,token=token,message=message)
        self.error(eo)

class KWSemanticError(LL1parser.Error):
    def __init__(self,source,type="S",token=None,message=""):
        self.type=type
        self.message=message
        if token is None:
            super().__init__(line=None,pos=None,source=source)
        else:
            super().__init__(line=token.line,pos=token.linepos,source=source)

    def print(self,string=False,debug=False):
        sr=self.src(debug=debug)
        msg="%s%s%s%s" % (self.type,self.loc(),self.message,sr)
        if string:
            return msg
        print(msg)

# This is a class that manages the creation of the lexical analyzer.
class LA(object):
    def __init__(self):
        # Dictionary and list of token types required by the KWLang instance.
        self.required={}      # Keyed by TID
        self.required_lst=[]  # Order of required TID's
        
        # Dictionary and list of token types required by the KWLang instance
        self.optional={}      # Dictionary of lexer.Types needed by the language
        self.optional_lst=[]  # Order of optional TID's
        
        # Dictionary and list of reserved word token types.  Statement ID's,
        # key-word arguments and explicit positional or key-word values become
        # reserved words, recognized before optional or required types.
        self.reserved={}          # Dictionary of reserved word WordType instances
        self.reserved_lst=[]      # Reserved word TID's
        self.reserved_rwords={}   # RWord TID's mapped to RWord instances
        self.reserved_matches={}
        
        self.overrides={}      # Ditionary of overrides.
        
        self.types=[]          # lexer.Type subclasses of this lexical analyzer

    def __dup_check(self,typ,method):
        if isinstance(typ,str):
            tid=typ
        elif isinstance(typ,lexer.Type):
            tid=typ.tid
        else:
            raise ValueError("langutil.py - LA.%s() - 'typ' argument must be "
                "either a string or instance of lexer.Type: %s" % (method,typ))
        self.__dup_list(self.required_lst,tid,method,"required")
        self.__dup_list(self.optional_lst,tid,method,"optional")
        self.__dup_list(self.reserved_lst,tid,method,"reserved")
        return tid
    
    # Internal method that detects a duplicate TID in a TID list
    def __dup_list(self,lst,tid,method,name):
        if tid in lst:
            raise ValueError("langutil.py - LA.%s() - duplicate %s token type id: "
                "%s" % (method,name,tid))
    
    # Create the lexical analyzer
    def create(self,dm,incase='',outcase=None):
        if not (outcase in ["upper","lower",None]):
            raise ValueError("langutil.py - LA.create() - 'outcase' argument "
                "must be either 'upper', 'lower' or None: %s" % outcase)
        if not isinstance(incase,str):
            raise ValueError("langutil.py - LA.create() - 'incase' argument "
                "must be a string: %s" % incase)
        if len(incase)!=1:
            raise ValueError("langutil.py - LA.create() - 'incase' argument "
                "must be a one character string: '%s'" % incase)
        if not incase in "LUME":
            raise ValueError("langutil.py - LA.create() - 'incase' argument "
                "must be 'E', 'L', 'M' or 'U': '%s'" % incase)
        incas="%s:" % incase
        reserved_types=[]
        tdebug=dm.isdebug("tdebug")
        
        # Create reserved word WordType instances
        match_len={}
        for rw in self.reserved_rwords.values():
            match=rw.match
            length=len(match)
            try:
                len_lst=match_len[length]
            except KeyError:
                len_lst=[]
            len_lst.append(rw)
            match_len[length]=len_lst
        lengths=[]
        for x in match_len.keys():
            lengths.append(x)
        l2s=sorted(lengths,reverse=True)
        for length in l2s:
            lst=match_len[length]
            for rw in lst:
                typ=WordType(rw.tid,"%s%s" % (incas,rw.match),case=outcase,\
                    debug=tdebug)
                self.types.append(typ)
        
        for tid in self.optional_lst:
            typ=self.optional[tid]
            self.types.append(typ)
            
        for tid in self.required_lst:
            typ=self.required[tid]
            self.types.append(typ)
            
        lexer=_KWLexer().init(self.types)
        return lexer
    
    # Add an optional lexer.Type subclass to the list.
    def opt(self,typ):
        if not isinstance(typ,lexer.Type):
            raise ValueError("langutil.py - LA.opt() - 'typ' argument requires "
                "an instance of lexer.Type: %s" % typ)
        tid=typ.tid
        if not tid.isupper():
            raise ValueError("langutil.py - LA.opt() - token type TID must be "
                "upper case: %s" % tid)
        tid=self.__dup_check(typ,"opt")
        self.optional[tid]=typ
        self.optional_lst.append(tid)
    
    # Add a required lexer.Type subclass to the list.
    def req(self,typ,override):
        if not isinstance(typ,lexer.Type):
            raise ValueError("langutil.py - LA.req() - 'typ' argument requires "
                "an instance of lexer.Type: %s" % typ)
        tid=typ.tid
        if not tid.isupper():
            raise ValueError("langutil.py - LA.req() - token type TID must be "
                "upper case: %s" % tid)
        tid=self.__dup_check(typ,"req")
        self.required[tid]=typ
        self.required_lst.append(tid)
        self.overrides[override]=tid
        
    # Add a reserved word TID to the list.  The actual WordType instance will be
    # created and the sequence defined when the lexical analyzer is created
    # by the create_lexer() method.  Note any typ string provided that is already
    # defined is assumed to be referencing the defined TID.  If the TID does not
    # exist, it is assumed to be a new reserved word and added to the list of
    # reserved words.  When created, all required TID's will be defined by KWLang.
    # Hence, the language processor defining a language instance should define
    # its optional lexical analyzer token types _before_ defining any statements.
    def res(self,word):
        if isinstance(word,RWord):
            rw=word
            tid=word.tid
        elif isinstance(word,str):
            rw=RWord(word.upper(),word)
            tid=rw.tid
        else:
            raise ValueError("langutil.py - LA.res() - 'word' argument must be an "
                "instance of RWord or a string: %s" % word)
        if not tid.isupper():
            raise ValueError("langutil.py - LA.res() - token type TID must be "
                "upper case: %s" % tid)
        try:
            tid=self.__dup_check(tid,"res")
        # Exception means the TID is not used somewhere and is not a new RWord
        except ValueError:
            return
        match=rw.match
        try:
            r=self.reserved_matches[match]
            raise ValueError("langutil.py - LA.res() - duplicate reserved"
                "word match '%s' with TID: %s" % (match,r.tid)) from None
        except KeyError:
            pass
        self.reserved_lst.append(tid)
        self.reserved_rwords[tid]=rw
        self.reserved_matches[match]=rw

# Insances of this class represent the result of successful statement recognizion
# A list of instances of this class is returned by the KWLang.analyze() method.
class Statement(object):
    def __init__(self,defn):
        if not isinstance(defn,Stmt):
            raise ValueError("langutil.py - Statement - 'defn' argument must "
                "be a instance of Stmt: %s" % defn)
        self.name=defn.name  # Name of this statement
        self.pos=None        # Pos_Args instance set by add_pos() method 
        self.key=None        # Key_Args instance set by add_key() method

        # These are used to position semantic error reporting within the input
        # stream.
        self._stmt_token=None   # The token that start statement recognition


    # Extract argument value.  If key is a string, a key-word argument value
    # is returned.  Otherwise the key is assumed to be an integer and a positional
    # argument is returned.  This method allows use of indexing and key-based
    # extraction of statement arguments.  If s is an object instance of 
    # Statement, then
    #    s["string"]   Returns the key-word statement argument's value.  If the
    #                  argument "string" is not present in the statement, a
    #                  KeyError exception is raised.
    #    s[integer]    Returns the corresponding positional argument's value.  If
    #                  no positional parameter exists at the specified position,
    #                  an IndexError exceptions is raised.
    def __getitem__(self,key):
        if isinstance(key,str):
            return self._key_values[key]
        if isinstance(key,int):
            return self.pos.values[key]
        raise ValueError("langutil.py - Statement.__getitem__() - item key "
            "is not a string or integer: %s" % key)

    def __setitem__(self,key):
        if isinstance(key,str):
            arg="keyword"
            key="'%s'" % key
        elif isinstance(key,int):
            arg="positional"
            key="%s" % key
        else:
            raise ValueError("langutil.py - Statement.__setitem__() - item key "
                "is not a string or integer: %s" % key)
        raise NotImplementedError("langutil.py - Statement.__setitem__() - "
            "statement arguments are read-only, can not set %s argument: %s" \
            % (arg,key))

    # Provide a printable view of the statement
    def __str__(self):
        string="\n'%s' Statement" % self.name
        if self.pos is not None and len(self.pos)>0:
            string="%s\nPOSITIONAL: %s" % (string,self.pos.print())
        if self.key is not None and len(self.key)>0:
            string="%s\nKEYWORDS: %s" % (string,self.key.print())
        return string

    # Add a set of keyword arguments to the statement results
    def add_key(self,key):
        if not isinstance(key,Key_Args):
            raise ValueError("langutil.py - Statement.add_pos() - 'key' argument "
                "must be an instance of Key_Args: %s" % pos)
        self.key=key

    # Add a set of positional arguments to the statement results
    def add_pos(self,pos):
        if not isinstance(pos,Pos_Args):
            raise ValueError("langutil.py - Statement.add_pos() - 'pos' argument "
                "must be an instance of Pos_Args: %s" % pos)
        self.pos=pos

    # Returns an iterable dictionay view object of the keyword values
    def keywords(self):
        return self._key_values.keys()

    # Returns an interagble list of positional arguments
    def positionals(self):
        return self._pos_values
        
    # Returns a string of the formatted content
    def print(self,indent=""):
        string="%s'%s' statement:" % (indent,self.name)
        ind1="%s    " % indent
        ind2="%s    " % ind1
        pargs=self.pos
        string="%s\n%sPOSITIONAL:" % (string,ind1)
        for x in range(len(pargs)):
            value=pargs[x]
            if isinstance(value,str):
                v="'%s'" % value
            else:
                v="%s" % value
            string="%s\n%s[%s] %s" % (string,ind2,x,v)
        kargs=self.key
        string="%s\n%sKEYWORDS:" % (string,ind1)
        keys=[]
        for key in kargs.keys(sort=True):
            value=kargs[key]
            if isinstance(value,str):
                v="'%s'" % value
            else:
                v="%s" % value
            string="%s\n%s%s=%s" % (string,ind2,key,v)
        return string
        
    # Sets the recognizing token of the statement 
    def set_stmt_tok(self,tok):
        if not isinstance(tok,lexer.Token):
            raise ValueError("langutil.py - Statement._set_stmt_tok() - "
                "'tok' argument must be an instance of lexer.Token: %s " % tok)
        self._stmt_token=tok

if __name__ == "__main__":
    raise NotImplementedError("langutil.py - must only be imported")
