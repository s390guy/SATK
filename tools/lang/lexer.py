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
# of creating a simple lexical analyzer based upon regular expressions.  Refer to
# the document "SATK for s390 - Language Processing Tools" in the SATK doc 
# directory for a description of this module's usage.

# Python imports:
import re

this_module="lexer.py"

# The following public classes are provided by the lexer module:
#   Token    Represents a portion of a string recognized by a Type instance.
#            Instances of Token or a subclass of Token are returned by a Lexer 
#            intance processing a string.
#   Type     This class defines a type of token that is recognized by a regular
#            expression.  A Type instance operates as a template for creating the
#            instance of Token (or a subclass) when recognized during Lexer instance
#            processing.  A given Type instance may be associated with more than
#            one Lexer instance.
#   Unrecognized  A sublcass of Token created by a Lexer instance for unrecognized
#            character sequence
#   Lexer    A simple lexer that turns a string into a series of Token instances.
#            The instantiated lexer may operate as an iterable that supplies a
#            Token instance on each iteration or returns a list of Token instances.
# Multiple instances of Lexer may be created and associated with the same or 
# different instances of Type.

# This exception is raised any time the Lexer encounters an error.
# Instance arguments:
#   pos      The position in the string where the error occurred.  Default is None.
#   line     The line in the string where the error occurred.  Default is None.
#   linepos  The poistion withint the current line where the error occurred.
#            Default is None
class LexerError(Exception):
    def __init__(self,pos=None,line=None,linepos=None,msg=""):
        self.msg=msg         # Text associated with the error
        self.pos=pos         # Position in the string where the error occurred 
        self.line=line       # Line in the string where the error occurred
        self.linepos=linepos # Position relative to start of the line
        
        string=""
        if self.pos is not None:
            string="%s[%s:%s]@%s" % (string,self.line,self.linepos,self.pos)
        if len(self.msg)>0:
            string="%s - %s" % (string,self.msg)
        super().__init__(string)


# +-------------------------------------------+
# |  Tokens Returned by the Lexical Analyzer  |
# +-------------------------------------------+

# This class represents a recognized token and all of its information gathered
# by the lexer for it.  
# Contents of the Token instance are influenced by:
#   - the lexer.analyze() method's 'lines' argument setting (defaults to True)
#   - the lexer.analyze() method's 'line' argument setting (defaults to 1)
#   - the lexer.tokenize() method's 'lines' argument setting (defaults to True)
#   - the lexer.tokenize() method's 'line' argument setting (defaults to 1)
#   - the lexer.Type instance 'ignore' argument setting (defaults to False)
#   - the lexer.Type instance 'mo' argument setting (defaults to False)
#
# To allow easy subclassing of the Token class, Token instances require no
# arguments.  Rather the init() method is used to initialize the instance's 
# attributes.  In this way, subclasses have direct access to the instance attributes
# while allowing the subclass to wrap the base class with aditional functionality.
#
# Instance init() method arguments:
#   tid     The type id of the Type instance that recognized the token
#   string  The character string of the recognized token
#   beg     The starting position of the recognized token in the scanned string
#   end     The ending position of the recognized token in the scanned string
#   line    The line number within the scanned string of the recognized token.
#           If the lexer.anaylyze() or lexer.tokenize() methods are called with
#           lines=False, the line will be set to 1.  Default is 0.
#   eols    The number of end of line symbols in the recognized token.  Generally 
#           speaking this value will only be greater than 0 for token type regular
#           expressions that recognize end of line and are compiled with the 
#           re.MULTILINE flag set.  Otherwise eol greater than zero should be
#           expected in the Unrecognized subclass of the Token base class.
#           Defaults to 0.
#   ignore  This token may be ignored when processed.  This is set based upon
#           the Type instance's setting of its ignore attribute for strings it
#           recognizes.  Default is False.
#   mo      Specifies the actual Regular Expression match object that recognized
#           the token.  The match object is preserved if the recognizing Type
#           instance was created with its mo argument specified as True.
#
# Other Instance methods:
#   istype  Tests whether the token is of a particular type identified by its tid.
#
# All of the other Token class instance methods provide access in some way to the
# match object if present in the Token.  If the match object is not present, a 
# LexerError exception is raised.
#
# These methods are provided to facilitate access to more
# complex regular expressions.
#   dict()    Returns the match object's group dictionary.
#   groups()  Returns the match object's group list.
#   match()   Returns the match object itself.
class Token(object):
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
        if a.linepos<b.linepos:
            return -1
        if a.linepos>b.linepos:
            return 1
        return 0

    def __init__(self):
        self.tid=None     # Token type to which recognized token belongs
        self.string=None  # String of the identified token
        self.beg=None     # Beginning position of the token in the original string
        self.end=None     # Ending poistion of the token in the original string
        self.line=None    # Line number of the token's start in the original string
        self.linepos=None # Position in line of token string start
        self.eols=None    # Number of end of lines encountered in the token
        self.ignore=None  # Indicates whether tokens of this type are ignored
        self.mo=None      # Match object that identified the token
        # All of the above attributes are established via the init() method.
        
        # This attribute is established by the _newline method()
        self.eolpos=None  # Position in the original string of the last eol
        
        # This attribute is provided for use of a program that processes tokens
        # and wants to preserve some information about the token and the its
        # processing.  An example might be its position within a list of Token
        # instances.  It is NOT used by the Token class.
        self.info=None

    # Display the Token instance
    def __str__(self):
        string="%s(" % self.__class__.__name__
        string='%s"%s"' % (string,self.tid)
        string="%s,'%s'" % (string,self.string)
        string="%s,%s,%s" % (string,self.beg,self.end)
        if self.eols:
            string="%s,eols=%s,eolpos=%s" % (string,self.eols,self.eolpos)
        if self.line:
            string="%s,line=%s,linepos=%s" % (string,self.line,self.linepos)
        if self.ignore:
            string="%s,IGNORE" % string
        if self.info is not None:
            string="%s,info=%s" % (string,self.info)
        string="%s)" % string
        if self.mo is not None:
            string="%s\n    mo groups=%s" % (string,self.groups())
            string="%s\n    mo dict=%s" % (string,self.dict())
        return string

    # This internal method determines how many new lines are in the recognized
    # string and the starting position of the last new line in the original
    # tokenized string.  The self.eolpos allows positioning of the succeeding
    # tokens relative to the current line.
    def _newline(self):
         eols=self.string.count("\n")
         if not eols:
             return
         self.eols=eols
         lasteol=self.string.rfind("\n")
         self.eolpos=self.beg+lasteol

    # This method which may be overridden by a subclass, extracts from the instance
    # the recognized token for handling by the language processor.  By default it
    # returns the recognized string of characters.
    def extract(self):
        return self.string
    
    # Initialize the instance attributes even when subclassed.
    # WARNING: This method does not return self as does __init__.  It returns None.
    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        self.tid=tid        # Token type to which recognized token belongs
        self.string=string  # String of the identified token
        self.beg=beg        # Beginning position of the token in the original string
        self.end=end        # Ending poistion of the token in the original string
        self.line=line      # Line number of the token's start in the original string
        self.linepos=linepos # Location of string relative to current line
        self.eols=eols      # Number of end of lines encountered in the token
        self.ignore=ignore  # Indicates whether tokens of this type are ignored
        self.mo=mo          # Match object that identified the token

    # Return the saved Regular Expression match object's group dictionary or
    # if not present raise a LexerError exception.
    #
    # Lack of the match object may occur if it is referenced in the token object's
    # __init__() method.  The match object is not available until the Token.init()
    # method is called.
    def dict(self,default=None):
        if self.mo is None:
            raise LexerError(msg="%s.dict() - match object not available (yet?)" \
                % self.__class__.__name__)
        return self.mo.groupdict(default)   

    # Test whether this Token instance is of a particular type.
    def istype(self,tid):
        return tid == self.tid

    # Return the saved Regular Expression match object's groups or
    # if not present, raise a LexerError exception.
    #
    # Lack of the match object may occur if it is referenced in the token object's
    # __init__() method.  The match object is not available until the Token.init()
    # method is called.
    def groups(self,default=None):
        if self.mo is None:
            raise LexerError(msg="%s.groups() - match object not available (yet?)" \
                % self.__class__.__name__)
        return self.mo.groups(default)
        
    # Returns the complete Regular Expression match object or
    # if not present, raise a LexerError exception
    def match(self):
        if self.mo is None:
            raise LexerError()
        return self.mo

class Empty(Token):
    def __init__(self):
        super().__init__()
    def init(self,tid,beg,line,linepos):
        #tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None
        super().init(tid,"",beg,beg,line=line,linepos=linepos)

class EOS(Token):
    def __init__(self):
        super().__init__()
    def init(self,tid,beg,line,linepos):
        #tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None
        super().init(tid,"",beg,beg,line=line,linepos=linepos)
        
# This class is a subclass of Token use by the Lexer class when it encounters 
# character sequences it is unable to recognize.  It is technically an internal
# subclass of Token used by the lexer when fail=False is used during the token
# recognition process.  However, a user of the Lexer may want to subclass it as
# well.  It uses the same strategy as the Token class by not requiring any 
# instance creation arguments.
#
# Instance init() method arguments:
#   beg      The position within the string being converted into tokens where the
#            first unrecognized sequence starts.
#   line     The line number of the first unrecognized character
#   linepos  The position of the first unrecognized character relative to the start
#            of the line.
class Unrecognized(Token):
    def __init__(self):
        super().__init__()

    # This internal method returns True if unrecognized characters are present
    # and False otherwise.
    def _any(self):
        return len(self.string)!=0

    # This internal method adds unrecognized characters to the string as they are
    # encountered during lexical scanning.
    def _extend(self,char,lines):
        self.string="%s%s" % (self.string,char)
        #length=len(char)
        self.end+=len(char)
            
    # Initialize the Unrecognized instance
    def init(self,beg,line,linepos):
        super().init("unrecognized","",beg,beg,line=line,linepos=linepos,\
            eols=0,ignore=True)
        self.linepos=beg-linepos

# This class defines a regular expression used for the purposes of matching a
# specific type of token.  Instances of class Type, create the cirumstances under
# which a set of tokens are identified and how the recognized instance of Token
# or a subclass of Token are created for a recognized token.  
# Arguments:
#    tid     A string identifying the type of token
#    re      The regular expression used to identify the type of token
#    flags   Special re flags used for compiling the regular expression
#    eol     When type is recognized, test for number of end of lines encountered
#    ignore  Specify True if the token is to be ignored.  Defaults to False
#    mo      Tokens contain the regular expression match object
#    tcls    Class instantiated for a recognized token of this type.  Defaults to
#            Token
class Type(object):
    def __init__(self,tid,pattern,flags=0,eol=False,ignore=False,mo=False,\
        tcls=Token,debug=False):
        # Lexer attributes
        self.tid=tid          # Lexical token type
        self.eol=eol          # Wether to test for end of line in match
        self.ignore=ignore    # Identified string should be ignored
        self.mo=mo            # regular expression match object preserved in Token
        self.tcls=tcls        # The class instantiated when this type is recognized
        self.debug=debug      # Debug this class
        # Regular expression related attributes
        self.pattern=pattern  # Regular expression detecting type
        self.flags=flags      # Regular expression compilation flags
        if pattern is None:
            self.cre=None
        else:
            self.cre=re.compile(pattern,flags)   # Compiled regular expression
        
    def __str__(self):
        flags=eol=ign=mo=""
        cls=self.tcls.__name__
        if self.flags:
            flags=",flags=%s" % flags
        if self.eol:
            eol=",eol=True"
        if self.ignore:
            ign=",IGNORE"
        if self.mo:
            mo=",mo=True"
        return 'Type("%s",' "'%s'%s%s%s,tcls=%s,debug=%s%s)" \
            % (self.tid,self.pattern,flags,eol,mo,cls,self.debug,ign)
        
    # This method does a match from the starting position within the string against
    # the compiled regular expression of the this instance
    # If found, an instance of Token is returned representing the identified token.
    # If not found a LexerError exception is raised.
    def match(self,string,pos=0,line=0,eolpos=0,eos=False):
        if self.debug:
            print("Type '%s' match(string,pos=%s,line=%s,eolpos=%s)" \
                % (self.tid,pos,line,eolpos))
        eols=0
        res=None

        # Try to recognize a token with my Regular Expression match pattern
        if self.debug:
            print("string: '%s'" % string[pos:])
        mo=self.cre.match(string,pos)
        if self.debug:
            print("mo: %s" % mo)
        if mo is None:
            if self.debug:
                print("Type '%s' match(): failed (None)" % self.tid)
            raise LexerError(pos,line,pos-eolpos)

        # Build the Token instance for the recognized token
        string=mo.group()
        if self.mo:
            res=mo
        if self.debug:
            print("matched string '%s' creating tcls: %s" % (string,self.tcls))
            
        # Note excpetions occurring within an iterator behave differently.  This
        # try block attemps to provide some indication of the failure.
        # Is this a bug in the Lexer interator code??  Don't know.
        try:
            tok=self.tcls()
        except Exception as e:
            ecls=e.__class__.__name__
            print("lexer.py - %s.match() - Failed to create token object: %s\n"
                "%s%s" % (self.__class__.__name__,self.tcls,ecls,e.args))
            raise e

        if self.debug:
            print("created token: %s.()" % tok.__class__.__name__)

        relpos=pos-eolpos
        tok.init(self.tid,string,mo.start(),mo.end(),\
            line=line,linepos=relpos,eols=eols,ignore=self.ignore,mo=res)

        if self.eol:
            tok._newline()

        if self.debug:
            print("Type '%s' match(): recognized Token:\n   %s" % (self.tid,tok))
        return tok
        
    # Accessor method to dynamically set debug status
    def setDebug(self,value):
        self.debug=value

class EmptyType(Type):
    def __init__(self,tid="EMPTY",tcls=Empty,debug=False):
        super().__init__(tid,None,tcls=tcls,debug=debug)
    def match(self,string,pos=0,line=0,eolpos=0):
        tok=self.tcls()
        tok.init(self.tid,pos,line,eolpos)

class EOSType(Type):
    def __init__(self,tid="EOS",tcls=EOS,debug=False):
        super().__init__(tid,None,tcls=tcls,debug=debug)
    def match(self,pos=0,line=0,eolpos=0):
        tok=self.tcls()
        #tid,beg,line,linepos
        tok.init(self.tid,pos,line,0)
        return tok

# +------------------------+
# |  THE LEXICAL ANALYZER  |
# +------------------------+

# This class performs a lexical tokenization process on a string based upon a set
# of Type instances associated with the Lexer instance by its type() method.
# 
# Instance Methods - See method description for argument details
#   
#   analyze    Returns a list of recognized Token instances for a supplied string.
#              It uses the tokenize() method for creation of the returned list.
#   init       This method must be provided by a subclass if used.  The intent
#              of this method is to provide a way for a specific Lexer to be 
#              created for within an application.  This method should create
#              all of the Types and associate them with the Lexer by calling the
#              type() method.
#   recognize  Returns a single instance of a Type associated with the Lexer
#              instance.  Types are recognized in the order in which they are 
#              associated with the Lexer.
#   tokenize   Returns an interator that will repetitively attempt recognition
#              of the associated Types on a given string.  It repeatedly calls
#              the recognize() method to recognize the types
#   type       Associate the supplied token Type instance with the lexer for use
#              by the recognize() method.  It takes one argument, a Type instance
#              Duplicate token id's are not allowed.
#   types      Prints the registered tokens in the sequence in which they are used
#              for recognizing a token type.
#
# Instance creation arguments
#    dup       Specify dup=True to allow the same type id to be associated with the
#              Lexer instance.  Specify dup=False to raise a ValueError if a Type
#              instance is attempted to be associated with the Lexer more than 
#              once.  Default is False.
#    grammar   Specify True to ensure Type tid's are compatible with many grammar
#              specifications where terminal tokens are associated with upper case 
#              names and non-terminal productions with lower case names.  Note,
#              the parser Grammar class does not have this requirement for its
#              productions.  This is a convenience for grammar development where 
#              the user prefers this visual separation in the a grammar
#              specification
#    ucls      The class that is instantiated for unrecognized character strings.
#              Defaults to Unrecognized.
class Lexer(object):
    def __init__(self,dup=False,grammar=False,ucls=Unrecognized):
        self.dup=dup   # Indicate whether duplicate token type id's are allowed
        self.ucls=ucls # Class instantiated for unrecognized character sequences
        self.grammar=grammar # Ensure Type instance tis is an uppercase name
        
        # Parser compatible token type tid's must start with a letter and may be
        # by any number of letters, 'a'-'z' or 'A'-'Z', numbers, '0'-'9' or 
        # underscores, '_'.
        if self.grammar:
            self.tidre=re.compile("[a-zA-Z][a-zA-Z0-9_]*")
        
        # List elements provided by the self.type() method
        self.typs=[]        # List of Type instances for recognized tokens
        self.tids=[]        # List of Type tids for detection of duplicates
        self.eos=False      # Set to true if EOSType is registered for recognition
        self.eostype=None   # The Type instance being used for EOS.
        self.emptytype=None # The Type instance beign usef for the Empty string
        
        # Values maintained while acting as an iterator
        self._reset()   # Initialize the attributes
        
        #self.end_debug=0
        
    # Return to the for statement the class that provides the iterator __next__()
    # method.  In this case this Lexer instance itself provides the method.
    def __iter__(self):
        self.stopped=False
        return self.__next__()
        
    # This method is used by the iterator (this instance) to return individually
    # recognized tokens.  It is a generator function.  Generators should only
    def __next__(self):
        if self.stopped:
            raise StopIteration
        while True:
            # Determine if iteration is done
            # provide a token if one is in the list of recognized tokens
            if len(self.recog) > 0:
                tok=self.recog[0]
                self.recog=self.recog[1:]
                yield tok
                continue
            # Stop the iteration if the recognizer has reached the string's end
            if self.pos == self.length:
                if self.eos:
                    tok=self.eostype.match(self.pos,self.line+1,0)
                    self.stopped=True
                    #self._reset()
                    yield tok
                self.stopped=True
                #self._reset()
                raise StopIteration
            else:    
               self.recognizer()

    def _accept(self,lst,tok):
        if self.lines and not isinstance(tok,Unrecognized):
            if tok.eols:
                self.line+=tok.eols      # Increment global line number
                self.eolpos=tok.eolpos   # And set start of this line
        lst.append(tok)
            
    # This internal method is used to recognize tokens with possible termination
    # by a LexerError.  This method is used if fail=True was specified with the
    # self.recognize() method.
    def _error(self):
        tok=self._recog()
        self.recog.append(tok)
        return

    # This internal method is used to recognize tokens including Unrecognize 
    # instances.
    def _noerror(self):
        unrecog=self.ucls()
        unrecog.init(self.pos,self.line,self.eolpos)
        while True:
            if self.pos == self.length:
                break
            try:
                tok=self._recog()
                if unrecog._any():
                    self._accept(self.recog,unrecog)
                    unrecog=self.ucls()
                    unrecog.init(self.pos,self.line,self.eolpos)
                self._accept(self.recog,tok)
                return
            except LexerError:
                badchar=self.string[self.pos]
                self.pos+=1
                n=0
                if self.lines:
                    n=badchar.count("\n")
                    if n:
                        self.line+=n
                        self.eolpos=self.pos
                unrecog._extend(badchar,lines=n)
                continue
        if unrecog._any():
            self._accept(self.recog,unrecog)

    # This internal method recognizes a token, handles line recognition and
    # if recognition fails raises a LexerError
    def _recog(self):
        tok=self.recognize(self.string,self.pos,self.line,self.eolpos)
        self.pos=tok.end
        return tok

    # This internal method resets the iterator attributes
    def _reset(self):
        self.fail=None
        self.pos=None
        self.eolpos=None
        self.line=None
        self.string=None
        self.length=None
        self.recognizer=None
        self.stopped=True
        self.recog=[]

    # This internal method validates Type tid's for compatibility with the parser
    # module.  For a compatible tid, the method returns the compatible tid.  It 
    # raises a ValueError if not.
    def _wgrammar(self,t):
        tid=t.tid
        mo=self.tidre.match(tid)

        if (mo is None) or (mo.endpos!=len(tid)):
            raise ValueError("Type tid not compatible with parser module: '%s'" \
                % tid)

        return tid.upper()

    # Returns a list of recognized tokens using self.tokenize() to create the
    # list.
    # Method arguments - see the tokenize method argument description.
    def analyze(self,string,pos=0,fail=True,lines=True,line=1):
        tokens=[]
        for t in self.tokenize(string,pos,fail=fail,lines=lines,line=line):
            tokens.append(t)
        return tokens

    # Returns the empty token tid 
    def empty_tid(self):
        if self.emptytype is None:
            return None
        return self.emptytype.tid

    # Returns the token tid of the 'end-of-stream' token or None if not supported.
    def eos_tid(self):
        if not self.eos:
            return None
        return self.eostype.tid

    # This method must be supplied by a subclass.  It is intended to be used for
    # initialization of the Lexer with Type instances specific to the subclass
    # lexer.
    #
    # WARNING: This method should return the current instance (return self) if 
    # this coding contruct is expected to be used:
    #   lex=MyLexerSubclass().init()
    def init(self,*args,**kwds):
        lcls=Lexer.__name__
        thiscls=self.__class__.__name__
        if lcls==thiscls:
            raise NotImplementedError(\
                "a subclass of %s must supply the method init()" % lcls)
        raise NotImplementedError(\
            "The Lexer subclass %s must supply the init() method" % thiscls)

    # Returns an instance of Token when one of the associated types is recognized
    # in the supplied string.  Othewise, a LexerError exception is raised.
    # Method arguments:
    #    string  The string being converted into lexical tokens.  Required
    #    pos     The position within the string at which recognition begins.
    #            Defaults to 0.
    #    line    The line number associated with the pos argument.  Defaults to 0.
    #    linepos The position within the current being recognized. Defaults to 0.
    def recognize(self,string,pos=0,line=0,linepos=0):
        for typ in self.typs:
            if self.eos and isinstance(typ,EOSType):  # put pseudo token type test here
                continue
            try:
                return typ.match(string,pos,line,linepos)
            except LexerError:
                continue
        # None of the associated types matches the string
        raise LexerError(pos=pos,line=line,linepos=linepos)

    # Prematurely stops tokenizing iterator without an exception
    def stop(self):
        self.stopped=True

    # Returns an iterator recognizing tokens in a string.  On each successive
    # iteration the next token is recognized and returned.  This method must be 
    # used within a for statement:
    #
    #   for token in Lexer.tokenize():
    #
    # Method arguments:
    #   string  The string from which tokens are recognized.  Required.
    #   pos     Indicates the starting position within the string where token
    #           recognition begins.  Default is 0.
    #   fail    Specify fail=False to create an Unrecognized instance for portions
    #           of the string that do not match any associated type.  
    #           Specify fail=True if a LexerError exception is raised when none of 
    #           the associated types is recognized.  Default is True.
    #   lines   Specify lines=False to inhibit line recognition.
    #           Specify lines=True if line recognition is performed for recognized
    #           token types that support it.  Default is True.
    #           Type instances supporting line recognition are created with the
    #           argument eol=True.
    #   line    Specify the first line number being recognized.  Defaults to 1.
    #           Ignored if lines=False is specified.
    def tokenize(self,string,pos=0,fail=True,lines=True,line=1):
        self.string=string   # String being tokenized
        self.pos=pos         # Starting position
        self.length=len(self.string)  # Ending position
        self.fail=fail       # Indicate whether a LexerError occurs
        self.lines=lines     # Indicate whether line recognition is performed
        self.line=line       # Indicate the starting line
        self.linepos=pos     # Position of the start of this line in string
        self.eolpos=pos      # Indicate the start of the current line
        if fail:
            self.recognizer=self._error
        else:
            self.recognizer=self._noerror
        # The for statement will call the self.__iter__() method on the returned 
        # object, namely this Lexer instance
        return self   

    # Associates the supplied Type instance with the Lexer for token recognition.
    # Method arguments:
    #   t  a Type instance to be recognized by the Lexer.  Whether type ids of the
    #      same name are allowed is dictated by the Lexer 'dup' argument.
    # If the grammar flag was used when the lexer was created, 
    def type(self,t):
        if not isinstance(t,Type):
            raise TypeError("lexer.Lexer.type(%s) - "
                "Type instance required" % t)
        if self.grammar:
            t.tid=self._wgrammar(t)

        if self.dup and (t.tid in self.tids):
            raise ValueError("lexer.Lexer.type() - duplicate type id: '%s'" 
                % t.tid)

        if isinstance(t,EOSType):
            self.eostype=t
            self.eos=True
        if isinstance(t,EmptyType):
            if self.emptytype is None:
                self.emptytype=t
            else:
                raise ValueError("lexer.py - Lexer.type() - empty type, TID '%s', "
                    "already registered" % self.emptytype.tid)
        else:
            self.typs.append(t)
        self.tids.append(t.tid)

    # Print the list of registered tokens
    def types(self):
        print("\n%s Defined Types\n" % self.__class__.__name__)
        for x in self.typs:
            print("%s" % x)

# +------------------------------------------+
# |                                          |
# |  THE CONTEXT SENSITIVE LEXICAL ANALYZER  |
# |                                          |
# +------------------------------------------+

# This stateless recognizer operates on a specific position within a string and
# determines if any of its registered token types matches.  It provides a single
# 'context' in which recognition occurs.
class Recognizer(object):
    def __init__(self, name):
        self.name=name
        self.typs=[]        # List of Type instances for recognized tokens
        self.tids=[]        # List of Type tids for detection of duplicates

    # Returns an instance of Token when one of the associated types is recognized
    # in the supplied string.  Othewise, a LexerError exception is raised.
    # Method arguments:
    #    string  The string being converted into lexical tokens.  Required
    #    pos     The position within the string at which recognition begins.
    #            Defaults to 0.
    #    line    The line number associated with the pos argument.  Defaults to 0.
    #    linepos The position within the current line being recognized.  Defaults to 0.
    # Exception:
    #    LexerError if not match is found
    def recognize(self,string,pos=0,line=0,linepos=0):
        for typ in self.typs:
            if self.eos and isinstance(typ,EOSType):  # put pseudo token type test here
                continue
            try:
                return typ.match(string,pos,line,linepos)
            except LexerError:
                continue
        # None token types associated with this context matches the string
        raise LexerError(pos=pos,line=line,linepos=linepos)
        
    # Associates the supplied Type instance with the Lexer for token recognition.
    # Method arguments:
    #   t  a Type instance to be recognized.  Whether type ids of the
    #      same name are allowed is dictated by the Lexer 'dup' argument.
    # If the grammar flag was used when the lexer was created, 
    def type(self,t):
        if not isinstance(t,Type) or isinstance(t,(EmptyType,EOSType)):
            cls_str="%s - %s.type() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 't' argument not a Type object or type unsupported:"
                ": %s" % (cls_str,t))

        if t.tid in self.tids:
            cls_str="%s - %s.type() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s - context %s duplicate type id: '%s'" \
                % (cls_str,self.name,t.tid))

        self.typs.append(t)
        self.tids.append(t.tid)
        
    # Print the list of registered tokens
    def types(self):
        print("\n%s Recognizer Defined Types\n" % self.name)
        for x in self.typs:
            print("%s" % x)


# Context Sensitive Lexical Analyzer.  Expects to be subclassed.
# It is the responsibility of the user of the subclass to determine when recognition
# contexts change.
class CSLA(object):
    def __init__(self):
        self.ctxs={}      # Defined stateless recognizers
        
        # Current string being recognized under different contexts
        # See start() method
        self.string=None  # Current string being recognized
        self.curctx=None  # Current context in use for recognition
        self.pos=None     # Current position being recognized
        self.eosfnd=False # True when EOS found in the current string
        
        # Initialize the subclass
        self.init()
        
    # Set the current context for the string being recognized
    def context(self,name):
        try:
           self.curctx=self.ctxs[ctx]
        except KeyError:
           cls_str="%s - %s.context() -" % (this_module,self.__class__.__name__)
           raise ValueError("%s context not defined: %s" % (cls_str,ctx))

    # Create a new context to which types are added.
    def ctx(self,name):
        try:
            self.ctxs[name]
            cls_str="%s - %s.ctx() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s context already created: %s" % (cls_str,name))
        except KeyError:
            self.ctxs[name]=Recognizer(name)

    # Allows the subclass to initalize the various contexts
    def init(self):
        clsname=self.__class__.__name__
        cls_str="%s - %s.init() -" % (this_module,clsname)
        raise NotImplementedError("%s subclass %s must provide init() method" \
            % (cls_str,clsname))

    # Returns the next token recognized by the current context
    # Method Argument:
    #   line   Provides a line number for returned tokens.  Defaults to zero
    # Returns:
    #   Token object for recognized token type or 
    #   EOS token when End-of-String condition detected
    # Exception:
    #   LexerError when no token type is recognized.
    #   ValueError if attempts to recognize a token after End-of-String condition
    def recognize(self,line=0):
        # Detect EOS condition
        if self.pos>=self.eospos:
            if self.eosfnd:
                cls_str="%s - %s.recognize() -" \
                    % (this_module,self.__class__.__name__)
                raise ValueError("%s context %s already found EOS:\n[%s] %s" \
                    % (cls_str,self.curctx.name,line,self.string))
            self.eosfnd=True
            return EOSType.match(self.pos,line,self.pos)  

        # Otherwise see if a token can be identified
        tok=self.curtxt.recognize(self.string,pos=self.pos,line=line)
        self.pos=tok.end  # Look next time from where we left off in the string
        return tok

    # Start context sensitive recognition of a new string from a given position
    # Method Arguments:
    #   string   The string being recognized
    #   name     The name of the initial context to be recognized
    #   pos      The starting position of the recognition within the string.
    #            Defaults to zero, the first character of the string.
    # Following the start() method, the recognize() method will return the next
    # token recognized and the context() method will set a new context.
    def start(self,string,name,pos=0):
        self.context(name)   # Establish the initial context
        self.string=string
        self.pos=pos
        self.eosfnd=False

    # Add a token type to an existing context for recognition
    # Method Arguments:
    #   name   The name of the registered context to which a token type is being added
    #   t      The Type object being added to the context.
    def type(self,name,t):
        try:
            ctx=self.ctxs[name]
        except KeyError:
            cls_str="%s - %s.type() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'name' argument is an undefined context: %s" \
                % (cls_str,name))
        ctx.type(t)


if __name__ == "__main__":
    raise NotImplementedError("lexer.py - must only be imported")

    y=Type("atype","(?P<letters>[a-z]+)",mo=True,eol=True)
    print("Created Type instance:\n   %s" % y)
    l=Lexer(grammar=True)
    l.type(y)
    print("Type instance added to lexer:\n   %s" % y)
    
    #string="asd%%"
    #string="asd%%bcd"
    string="\nxyz\nabc"
    #string="1345"
    
    #fail=True
    fail=False
    
    # Use the iterator to tokenize
    print("\nRun the tokenize iterator")
    for t in l.tokenize(string,fail=fail,lines=True):
        print("%s" % t)

    print("\nCreate the analyze list")
    lst=l.analyze(string,fail=fail)
    print("len(lst)==%s" % len(lst))
    for x in lst:
        print("%s" % x)
 