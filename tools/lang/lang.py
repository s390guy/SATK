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
import parser   # Access the language tools' syntactical analyzer

class Language(parser.Parser):
    # Create the language processor as a subclass of the syntactical analyzer
    def __init__(self):
        super().__init__()
        self.gs=None
        
    # Call the parser.Parser parse() method to recognize text in the target 
    # language. The lang.Language subclass has full responsibility for its
    # handling of recognized text.
    #
    # If present, the following call backs to the language processor are used.  
    # In each case 'n' is the index of the right hand alternative being processed.
    #   self.<pid>_beg()
    #         Recognition of <pid> has started.
    #   self.<pid>_trying(n,last=True/False)   
    #         Signals the attempt to recognize a right hand side of a production.
    #   self.<pid>_token(n,token)
    #         This signals the language processor that the token instance was found
    #         in the <pid>.
    #   self.<pid>_failing(n,last=True/False) 
    #         Signals the previously attempted recognition failed.  The 
    #         language processor should "clean up" from the previous attempt. 
    #   self.<pid>_found(n,last=True/False)
    #         The syntactical analyzer succeeded its recognition of the 
    #         production pid with the n'th alternative.  The language analyzer
    #         should do what it needs to for the production's recognition.
    #   self.<pid>_end(failed=True/False)
    #         Recognition of the production has ended for <pid>.
    # For a given production, if the callback is not present, the default version
    # is called, which does nothing.
    #
    # This is a default analyze method that calls the parser.Parser parse() method
    # with its default arguments.  
    def analyze(self,text):
        self.prepare()
        self.parse(text)

    # This method creates the Language processor and must be called from the 
    # lang.Language subclass in its init() method.
    def create(self):
        lxr=self.create_lexer()
        if not isinstance(lxr,lexer.Lexer):
            raise ValueError("%s.create_lexer() method must return an instance of "
                "lexer.Lexer, but encountered: %s" \
                % (self.__class__.__name__,lexer)) 
        tg,prod=self.define_parser()
        if not isinstance(tg,str):
            raise ValueError("%s.define_parser() method must return a string "
                "object for the grammar definition. but encountered: %s" \
                % (self.__class__.__name__,tg))
        if not isinstance(prod,str):
            raise ValueError("%s.define_parser() method must return a string "
                "object for the starting production id, but encountered: %s"\
                % (self.__class__.__name__,prod))
        self.generate(tg,lxr,prod)
    
    # This method prepares the language environment for parsing.  It must be 
    # called by the analyze method calls the parser.Parser.parse() method.
    def prepare(self):
        self.gs=self.create_global()
        self.gs.mgr=self.create_error_mgr()
    
    # This method creates an error manager.  If a subclass needs to instantiate its
    # own, then this method should be overridden.
    def create_error_mgr(self):
        return parser.ErrorMgr()
    
    # Create the lexical analyzer to be used by the language.  This method must
    # instantiate and initialize the lexer.Lexer subclass for this language.
    # This method is called by the self.create() method that initializes the 
    # language system.
    #
    # Subclasses MUST provide this method, returning the lexical analyzer instance.
    def create_lexer(self):
        raise NotImplementedError("Subclass %s of lang.Language must provide the "
            "create_lexer() method")
    
    # Creates a global Scope instance from lang.Scope.  If the language processor
    # needs to subclass Scope, this method should be overridden by the 
    # lang.Language subclass.
    def create_global(self):
        return Scope()

    # Define the syntactic analyzer to be used by the language.  This method must
    # return a tuple of two strings.  The first string is the grammar string that
    # define's the syntactical analyzer's processing. The second string is the
    # pid of the starting production.
    #
    # Subclasses MUST provide this method
    def define_parser(self):
        raise NotImplementedError("Subclass %s of Language must provide the "
            "create_parser() method")
      
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
      
if __name__ == "__main__":
    raise NotImplementedError("lang.py - must only be imported")
