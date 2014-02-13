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
# of creating a small language processor.  Refer to the document 
# "SATK for s390 - Language Processing Tools" in the SATK doc directory for a 
# description of this module's usage.

# Python imports: None

# SATK imports:
import lexer    # Access the language tools' lexical analyzer
import LL1parser   # Access the language tools' syntactical analyzer
import satkutil    # Access the DM class

class Language(LL1parser.Parser):
    # Create the language processor as a subclass of the syntactical analyzer
    def __init__(self,processor):
        if not isinstance(processor,Processor):
            raise ValueError("lang.py - Language.__init__() - 'processor' argument "
                "must be an instance of lang.Processor: %s" % processor)
        super().__init__()
        self.gs=None                   # The Global Scope object
        self.processor=processor       # The language processor
        
        # Turn on debugging and enable call backs
        dm=self.processor.configure(self)
        if isinstance(dm,satkutil.DM):
            self.dm=dm  # Override default DM with one supplied.
        
        # Now initialize my parser super class parser.Parser
        proccls=self.processor.__class__.__name__
        lxr=self.processor.create_lexer()
        if not isinstance(lxr,lexer.Lexer):
            raise ValueError("%s.create_lexer() method must return an instance of "
                "lexer.Lexer, but encountered: %s" % (proccls,lexer)) 
        tg,prod=self.processor.define_parser()
        if not isinstance(tg,str):
            raise ValueError("%s.define_parser() method must return a string "
                "object for the grammar definition. but encountered: %s" \
                % (proccls,tg))
        if not isinstance(prod,str):
            raise ValueError("%s.define_parser() method must return a string "
                "object for the starting production id, but encountered: %s"\
                % (proccls,prod))
        self.generate(tg,lxr,prod)
        
    # Calls the parser.Parser parse() method to recognize text in the target 
    # language. The lang.Language subclass has full responsibility for its
    # handling of recognized text.
    #
    # This is a default analyze method that calls the parser.Parser parse() method
    # with its default arguments.  Upon completion, it returns the global scope
    # object to the processor.
    # 
    # ParserAbort exception may be raised if recovery=False and a parser detected
    # and error.
    def analyze(self,text,scope=None,error_mgr=None,recovery=False,\
                depth=20,lines=True,fail=False):
        self.prepare(scope,error_mgr)
        self.parse(text,recovery=recovery,depth=depth,lines=lines,fail=fail)
        return self.gs

    def filter(self,tok):
        return self.processor.filter(self.gs,tok)

    # This method prepares the language environment for parsing.  It must be 
    # called by the analyze method calls the parser.Parser.parse() method.
    #
    # Its role is to initialize the global scope object  with global parser 
    # management objects:
    #   gs.dm      The Debug manager being used by the parser
    #   gs.mgr     The Error manager being used by the parser
    # SHOULD THIS BE MOVED TO THE LL1Parser object?
    def prepare(self,scope,error_mgr):
        if scope is None:
            self.gs=Scope()
        else:
            if not isinstance(scope,Scope):
                raise ValueError("lang.py - Lanuage.prepare() - 'scope' argument "
                    "must be an instance of Scope: %s" % scope)
            self.gs=scope
        if error_mgr is None:
            self.gs.mgr=LL1parser.ErrorMgr()
        else:
            if not isinstance(error_mgr,parser.ErrorMgr):
                raise ValueError("lang.py - Lanuage.prepare() - 'error_mgr' "
                    "argument must be an instance of parser.ErrorMgr: %s" \
                    % error_mgr)
            self.gs.mgr=error_mgr
        self.gs.dm=self.dm

# This is the base class for all language processors as separate entities.  The
# Language class expects to interface with this class when being instantiated.
# All language processors must be subclasses of this class.  It defines the
# interactions with the Language object that constitute the interface between the
# two environments.  Text recognition processes interact between the two objects
# by means of a global instance of the Scope object and callback methods registered
# with the Lanugage object.
#
# Processor object arguments: None
#
# Methods required by lang.Language to be provided by Processor subclasses:
#
#   configure      Enables lang.Language (and its superclass parser.Parser) debug
#                  options and Processor subclass callback methods.
#   create_lexer   Instantiates and returns to the Language object the lexical
#                  analyzer used by the processor.
#   define_parser  Returns two strings as a tuple: the grammar used by the language
#                  and the starting PID used by the parser embedded in the language
#                  object.
#
# Methods available for use by a Processor subclass:
#
#  error           Deliver an error object to the error manager.
#  errors          Returns the number of currently encountered errors.
class Processor(object):
    def __init__(self):
        # This attribute is provided when the Processor object is associated
        # with the Language object during the init method() call by the language object.
        self.lang=None 
    
    # This method is called by the Language interface object for initialization
    # of processor operations.  This method must enable call back methods and return
    # a Debug Manager instance.
    def configure(self,lang):
        raise NotImplementedError("Subclass %s of lang.Processor must provide the "
            "configure() method" % self.__class__.__name__)
    
    # Create the lexical analyzer to be used by the language.  This method must
    # instantiate and initialize the lexer.Lexer subclass for this language.
    # This method is called by the lang.create() method that initializes the 
    # language system.
    #
    # Subclasses MUST provide this method, returning the lexical analyzer instance.
    def create_lexer(self):
        raise NotImplementedError("Subclass %s of lang.Processor must provide the "
            "create_lexer() method" % self.__class__.__name__)
    
    # Defines the syntactic analyzer to be used by the language.  This method must
    # return a tuple of two strings.  The first string is the grammar string that
    # define's the syntactical analyzer's processing. The second string is the
    # pid of the starting production.
    #
    # Subclasses MUST provide this method
    def define_parser(self):
        raise NotImplementedError("Subclass %s of lang.Processor must provide the "
            "define_parser() method" % self.__class__.__name__)
        
    # Report an error object (instance of parser.Error) to the parser
    def error(self,eo):
        self.lang.gs.mgr.report(eo)
        
    # Return the number of currently encountered errors.
    def errors(self):
        return self.lang.gs.mgr.quantity()
        
    # This method provides the default filter for processing.  A subclass should
    # override this method for actual filtering
    def filter(self,gs,tok):
        return tok

    # This method prints the grammar used by the Language object, a subclass of 
    # LL1parser.Parser.
    def grammar(self):
        self.lang.grammar()

    # This method is part of the Lanugage object interface and must not be
    # overridden by a subclass
    def init(self):
        self.lang=Language(self)

    # Expose the error manager for use by language processor
    def manager(self):
        return self.lang.gs.mgr

    # Returns the global Scope() object
    def scope(self):
        return self.lang.gs
        
    # Returns the processed input text
    def text(self):
        return self.lang.source()
        
    # Returns the lexical tokens resulting from the lexical analysis
    def tokens(self):
        return self.lang.tokens()

# This class facilitates the management of scope within the language processor.  It
# is recommended that this class or a subclass be used at least to manage global
# language processing scope.  This ensures the separation of language processor
# global name space from the lang.Lanugage class and its super class parser.Parser.
#
# The base class simply provides an alternative attribute name space.  A subclass
# may add language specific methods and an init() method for initialization.
class Scope(object):
    def init(self):
        raise NotImplementedError("Subclass %s of lang.Scope must provide the "
            "init() method" % self.__class__.__name__)

# These two class provides generic Symbol Table support
# It is expected that a language processor will subclass these classes tailored to
# its needs.
class STE(object):
    def __init__(self,name):
        if not isinstance(name,str):
            cls_str="lang.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s 'name' argument must be a string: %s" \
                % (cls_str,name))
        self.name=name

class SymbolTable(object):
    def __init__(self,write_once=False):
        self.tbl={}
        self.write_once=write_once

    # Retrieve a symbol by its name using index syntax: table[name]
    # Raises KeyError if item not in table
    def __getitem__(self,key):
        return self.tbl[key]
        
    # Set the value of a symbol in the table using index syntax: table[name]=STE object
    # Raises KeyError if write_once=True and the symbol name already exists
    def __setitem__(self,key,item):
        cls_str="lang.py - %s.__setitem__() -" % self.__class__.__name__
        if not isinstance(key,str):
            raise ValueError("%s 'key' argument must be a string: %s" % (cls_str,key))
        if not isinstance(item,STE):
            raise ValueError("%s 'item' argument must an instance of STE: %s"
                % (cls_str,item))
        if self.write_once:
            try:
                self.tbl[key]
                found=True
            except KeyError:
                found=False
            if found:
                raise KeyError("%s symbol already defined in write_once=True table: "
                    "%s" % (cls_str,key))
        self.tbl[key]=item
    
    # Return an iterator of entries, a tuple (label,STE)
    def entries(self):
        return self.tbl.items()
    
    # Return an interator of symbol labels
    def labels(self):
        return self.tbl.keys()
    
    # Return an interator of STE objects
    def symbols(self):
        return self.tbl.values()
     
    

if __name__ == "__main__":
    raise NotImplementedError("lang.py - must only be imported")
