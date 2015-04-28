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

# This model consolidates 
#   - all lexical and 
#   - all pratt2 tokens
#   - all finite-state-machine base classes

this_module="asmtokens.py"

# Python imports: none
# SATK imports:
import fsmparser            # Access Finite-Machine-based Parsing tools
import lexer                # Access the lexical analyzer
import pratt2               # Access the generalized operator precedence evaluator

# ASMA imports:
import assembler            # Access the assembler module

#
#  +--------------------------------------------+
#  |                                            |
#  |  ASMA Shared Regular Expression Patterns   |
#  |                                            | 
#  +--------------------------------------------+
#

# These definitions provide consistency between different modules using regular
# expressions.  Use requires the assembler module to be imported

# Note these should probably move here rather than reside in the assembler module.
label=assembler.label               # Location label
spaces="[ ]+"                       # One or more spaces


#
#  +---------------------------------------------+
#  |                                             |
#  |   Expression Evaluation Token Definitions   |
#  |                                             |
#  +---------------------------------------------+
#

# This pratt2 PLit object is used to process strings encountered in logical
# expressions.  The only context in which this occurs is in string comparisons of
# the EBCDIC value of the string.
class BPLitStr(pratt2.PLit):
    def __init__(self,token):
        super().__init__(token)
        #self._ebcdic=assembler.CPTRANS.a2e(self.src.string)
    def value(self,external=None,debug=False,trace=False):
        # Need to do symbolic replacement with new searcher
        string=external.exp.symbol_replace(self.src.string,debug=debug)
        
        if __debug__:
            if trace:
                print('%s string: "%s"' \
                    % (assembler.eloc(self,"value",module=this_module)))

        return assembler.CPTRANS.a2e(string)
        #return self._ebcdic

# This division operator implements the assembler specific behavior of returning
# a value of zero when division by zero occurs.  Otherwise the pratt2.PFloorDiv
# object handles the division operation.
class PAsmDiv(pratt2.PFloorDiv):
    def __init__(self,src=None):
        super().__init__(src)
    # Infix arithmetic operation: left divided by right, ignoring remainder
    def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
        if right==0:
            return 0
        return super().calc_led(parser,left,right,external=external,\
            debug=debug,trace=trace)

# This pratt2.PLit subclass accesses the current location counter.  It is used
# in expressions where the '*' symbol is being used to reference the currne location
# (as opposed to being the multiplication operator).
class PLitCur(pratt2.PLit):
    def __init__(self,token):
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        #cur_stmt=external.cur_stmt
        #stmt_bin=cur_stmt.content
        #if stmt_bin is None:
        #    cur=self.external.cur_loc.retrieve()
        #else:
        #    cur=cur_stmt.current()
        cur=external.cur_loc.retrieve()

        assert isinstance(cur,assembler.Address),\
            "%s current location of statement %s not an address: %s" \
                % (assembler.eloc(self,"value",module=this_module),cur)
        #if not isinstance(cur,assembler.Address):
        #    cls_str="asmparsers.py - %s.convert() -" % self.__class__.__name__
        #    raise ValueError("%s current location of statement %s not an address: %s" \
        #        % (cls_str,cur_stmt.lineno,cur))

        if __debug__:
            if trace:
                print("%s.value() v=%s" % (self.__class__.__name__,cur))

        return cur


# This class allows a symbol to be used as a factor within an expression.
# It retrieves from the symbol table the symbol's value and passes it to
# the Pratt expression evaluator
class PLitLabel(pratt2.PLit):
    def __init__(self,token):
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        # external is the Assembler object
        token=self.src
        label=token.extract()

        # Note: this external method will raise a KeyError excpetion if the symbol
        # is not found.
        try:
            ste=external._getSTE_Ref(label,token.line)
        except KeyError:
            raise assembler.LabelError(label,ltok=self.src,msg="undefined label") \
                from None

        value=ste.value()
        if isinstance(value,(assembler.SectAddr,assembler.DDisp,assembler.AbsAddr)):
            value.length=ste.attrGet("L")
            if trace:
                print("%s.convert() v=%s,length=%s" \
                    % (self.__class__.__name__,value,value.length))
        else:
            if trace:
                print("%s.value() v=%s" % (self.__class__.__name__,value))
        return value

# This class allows a symbol or one of its attributes to be used as a factor within an 
# expression.  It retrieves from the symbol table the symbol's value and passes it to
# directly to the Pratt expression evaluator if no attribute was supplied.  If
# supplied, it will return the requested attributes value.
class PLitLabelAttr(pratt2.PLit):
    def __init__(self,token):
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        # external is the Assembler object
        mogrps=self.src.groups()
        attr=mogrps[0]    # None or "X'" where X is the requested attribute
        label=mogrps[1]

        # Regarless of whether an attribute is present or not, retrieve the symbol
        # from the symbol dictionary.
        # Note: this external method will raise a KeyError excpetion if the symbol
        # is not found.
        try:
            ste=external._getSTE_Ref(label,self.src.line)
        except KeyError:
            raise assembler.LabelError(label,ltok=self.src,msg="undefined label") \
                from None
         
        if attr is not None:
            attr=attr[0].upper()  # Match string includes the following ', drop it
        else:
            # No attribute so just return the symbol's value
            value=ste.value()
            if trace:
                 print("%s.value() %s=%s" % (self.__class__.__name__,label,value))
            return value
            
        # If the attribute recognized by the original token is not valid the getAttr()
        # method will raise a ValueError.
        attr_val=ste.attrGet(attr)
        if trace:
            print("%s.value() %s'%s=%s" % (self.__class__.__name__,attr,label,value))
        return attr_val


# This pratt2 PLit object is used for all self defining terms.  It will evaluate
# the term's value when instantiated as opposed to when referenced during evaluation.
# This latter behavior is used by PLitTID and PLitSmart.  This eliminates the need
# to do the convertion evertime the expression is evaluated in a macro invocation.
class PLitSD(pratt2.PLit):
    def __init__(self,token):
        super().__init__(token)
        self.sdval=self.src.convert()   # Self-defining term's integer value
    def value(self,external=None,debug=False,trace=False):
        v=self.sdval
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

#
#  +----------------------------------------+
#  |                                        |
#  |   Lexical Analyzer Token Definitions   |
#  |                                        |
#  +----------------------------------------+
#

# This is the base class for all lexical tokens created by the lexical analyzers
# shared within ASMA.
class LexicalToken(lexer.Token):
    def __init__(self):
        super().__init__()

        # Subclass must set these values if needed using its supplied syntax() method
        self.binary=False       # Whether token represents a binary operator
        self.unary=False        # Whether token represents a unary operator

    # Generates and returns a pratt2 module PToken object for arithmetic expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def atoken(self):
        return self.ptoken()

    # Generates and returns a pratt2 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def btoken(self):
        return self.ptoken()

    # Analyzes the recognized string and returns it as a native Python object.
    def convert(self):
        raise NotImplementedError("%s subclass %s must provide convert() method"\
            % (assembler.eloc(self,"convert",module=this_module),\
                self.__class__.__name__))

    # Generates and returns a pratt2 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def ctoken(self):
        return self.ptoken()

    # This method generates a pratt2 module PToken opject.  For lexical tokens that
    # must be converted into a PToken object that participates in expression
    # evalutations this method returns the object.  Lexical tokens that do not
    # participate in expression evaluations do not require this method.
    def ptoken(self,*args,**kwds):
        cls_str=assembler.eloc(self,"ptoken",module=this_module)
        raise NotImplementedError("%s subclass %s must provide ptoken() method" \
            % (cls_str,self.__class__.__name__))

    # This method sets the operator syntax attributes.  If actual values are
    # required, the subclass must override this method.
    def syntax(self):
        pass

    # This method updates the lexical token with statement specific position
    # information.
    #
    # The lexical analyzer is designed to recognize entire files.  However, ASMA
    # only uses it to recognize portions of a line.  So after accepting the token
    # ASMA must update the token with actual statement location as produced 
    # by the assembler listing.
    def update(self,line,incr,source=None):
        self.line=line
        self.linepos+=incr
        self.source=source 


# +-*/   - Recognizes arithmetic expression operators
class AOperToken(LexicalToken):
    # converts an arithmetic operator as a string into a pratt2 module Operator classs
    ptokens={"+":pratt2.PAdd,
             "-":pratt2.PSub,
             "*":pratt2.PMul,
             "/":PAsmDiv}
    def __init__(self):
        super().__init__()

        # This flag used to trigger current location counter for * instead of multiply
        # The parser must recognize this condition and set theis using the
        # current() method.
        self.iscur=False

    # Indicate this token represents the current location counter ('*')
    def current(self):
        self.iscur=True
        self.binary=self.unary=False

    # Sets operator syntax settings
    def syntax(self):
        self.binary=True
        self.unary=self.string in "+-"

    # Returns a pratt2 PToken object with myself as the sourc
    def ptoken(self):
        if self.iscur:
            return PLitCur(self)
        # Add logic for Current location PToken
        cls=AOperToken.ptokens[self.extract()]
        return cls(src=self)

class AOperType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("AOPER","[\+\-\*\/]",tcls=AOperToken,debug=debug)


# Recognizes the end of operands, namely, one or more spaces
class EoOperToken(LexicalToken):
    def __init__(self):
        super().__init__()

class EoOperType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("EOO",spaces,tcls=EoOperToken,mo=True,debug=debug)


# ,      - Recognizes a single comma
class CommaType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("COMMA",",",tcls=LexicalToken,debug=debug)

# LABEL  - Recgonizes an assembler label without an attribute
class LabelToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def ptoken(self):
        return PLitLabel(self)

class LabelType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("LABEL",label,tcls=LabelToken,mo=True,debug=debug)


# LABEL   - Recgonizes an assembler label alone or
# X'LABEL - Recognizes an assembler label preceded by an attribute.  Attributes are
#           defined in the LabelAttrType.ATTR attribute.
class LabelAttrToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def ptoken(self):
        return PLitLabelAttr(self)

class LabelAttrType(lexer.Type):
    # Add new attributes HERE!  Upper and lower case are automatically recognized
    # New attributes must be coordinated throughout the assembler but in particular
    # the assembler.Symbol class and subclasses.
    ATTR="KLN"
    def __init__(self,debug=False):
        attr=LabelAttrType.ATTR.upper()    # Recognize upper case..
        attr="%s%s" % (attr,attr.lower())  # and add lower case here
        pattern="([%s]')?(%s)" % (attr,label)
        super().__init__("LATTR",pattern,tcls=LabelAttrToken,mo=True,debug=debug)


# (      - Recognizes a single left parenthesis
class LParenToken(LexicalToken):
    def __init__(self):
        super().__init__()
    # Returns a pratt2 PToken object with myself as the source
    def ptoken(self):
        return pratt2.PLParen(src=self)

class LParenType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("LPAREN","[\(]",tcls=LParenToken,debug=debug)
   

# )      - Recognizes a single right parenthesis 
class RParenToken(LexicalToken):
    def __init__(self):
        super().__init__()
    # Returns a pratt2 PToken object with myself as the source
    def ptoken(self):
        return pratt2.PRParen(src=self)

class RParenType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("RPAREN","[\)]",tcls=RParenToken,debug=debug)

# B'xxx' - Recognized binary self defining terms
class SDBinToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        # Convert BINARY self defining term to integer (ignoring leading B and quotes)
        return int(self.string[2:-1],2)
    # Returns a pratt2 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDBinType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDBIN","[Bb]'[01]+'",tcls=SDBinToken,debug=debug)
        

# C'x', CA'x', CE'x' - Recognizes character self-defining terms
class SDChrToken(LexicalToken):
    ebcdic=["C","CE"]
    def __init__(self):
        super().__init__()
    def convert(self):
        groups=self.groups()
        char=groups[1]
        # Ignore the surrounding single quotes and pick the first char.  The second
        # group, index 1, in the regular expression pattern used by SDChrType will be
        # either: 'x' or ''''.  In either case the character following the first
        # single quote is the one we are interested in using.
        char=char[1]
        desc=groups[0]
        if desc.upper() in SDChrToken.ebcdic:
            char=assembler.CPTRANS.a2e(char)
        return ord(char)
    # Returns a pratt2 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDChrType(lexer.Type):
    def __init__(self,debug=False):
        #  Groups                 0            1
        super().__init__("SDCHR","([Cc][EeAa]?)(''''|'[^']')",mo=True,\
            tcls=SDChrToken,debug=debug)


# 9..9   - Recognizes an unsigned decimal self-defining term
class SDDecToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        return int(self.string,10)
    # Returns a pratt2 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDDecType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDDEC","[0-9]+",tcls=SDDecToken,debug=debug)


# X'xx'  - Recognizes hexadecimal self-defining terms
class SDHexToken(LexicalToken):
    def __init__(self):
        super().__init__()
    def convert(self):
        # Convert HEX self defining term to integer (ignoring leading H and quotes)
        return int(self.string[2:-1],16)
    # Returns a pratt2 PToken object (defined above) with myself as the source
    def ptoken(self):
        return PLitSD(self)

class SDHexType(lexer.Type):
    def __init__(self,debug=False):
        super().__init__("SDHEX","[Xx]'[0-9a-fA-F]+'",tcls=SDHexToken,debug=debug)


# This token is extended to allow recognition of two adjacent singe quotes to be
# recognized as a single quote in the internal representation of a string.  This
# token requires assistance by the parser to successfully handle this case.  The way
# this works is not intuitive which is why this lengthy explanation is provided.
# It is based upon the rule that valid strings will always contain an even number
# of single quotes.
# 
# The regular expression of the StringType object recognizes this basic pattern: '.*'
# This includes two single quotes with nothing between them or any set of characters
# which are not single quotes.
#
# Applying this regular expression to a string that includes successive single quotes
# results in multiple string tokens in succession being recognized.  In this example,
# each recognized character sequence is identified by the beginning and ending
# characters in the diagram, '<' and '>'.
#
#      'X''abc'''
#      <-><---><>
#       1   2   3  <---StringToken object number
# 
# The characters actually provided in each of the StingToken object's string attribute
# is as follows, the content being surrounded here by double quotes:
#
#   1.  self.string contains  "X'"
#   2.  self.string contains  "abc'"
#   3.  self.string contains  "'"
#
# The overridden init() method performs the removal of the initial single quote,
# allowing the final quote to end up becoming the single quote as expected when
# additional characters are added to the string.
#
# The extend method() allows the next StringToken object to contribute to the 
# content of the first StringToken object.  Here is the content of the first
# StringToken object after extending it by the second and third objects:
#
#   after extending with object 2, object 1 contains  "X'abc'"
#   after extending with object 3, object 1 contains  "X'abc''"
#
# It is the application of the original StringToken object's extend() method that
# drives the need for parser assistance.
#
# The convert method() is used to access the internal representation of the
# StringToken object and this results in this final result: "X'abc'".
# This final result is the intent of the original coding.  Assigning such a string
# to a SETC symbolic variable, allows it to be used in a macro SETA statement as
# a self-defining term.
#
# Implementation Limitation: Until the asmparsers module is enhanced to utilize this 
# StringToken object, single quotes will continue to prohibited in DC assembler
# directive character constants.
class StringToken(LexicalToken):
    def __init__(self):
        # Normally will drop the initial single quote.  Reset in a subclass if needed.
        self.drop=True   
        super().__init__()

    def atoken(self):
        cls_str=assembler.eloc(self,"atoken",module=this_module)
        raise NotImplementedError("%s TID:%s must not be recognized in "
            "arithemetic expressions" % (cls_str,self.tid))
        
    def btoken(self):
        return BPLitStr(self)

    def convert(self):
        # Because self.string does not contain a leading single quote having it
        # removed in the overridden init() method, it is only necessary to remove
        # the trailing single quote.
        return self.string[:-1]

    # This method allows for the logical extension of a string token, allowing two
    # successive quotes to be converted into one in the final result.
    def extend(self,ltok):
        assert isinstance(ltok,StringToken),\
            "%s 'ltok' argument must be another StringToken object: %s" \
                % (assembler.eloc(self,"extend",module=this_module),ltok)  

        self.string="%s%s" % (self.string,ltok.string)
        #print('following extend: self.string="%s"' % self.string)
        self.end=ltok.end

    # Override the lexer.token init() method to insert additional logic at that
    # point.
    def init(self,tid,string,beg,end,line=0,linepos=0,eols=0,ignore=False,mo=None):
        super().init(tid,string,beg,end,\
            line=line,linepos=linepos,eols=eols,ignore=ignore,mo=mo)
        # remove the leading single quote of the string.  This forms the basis
        # of the extend method()
        if self.drop:
            self.string=self.string[1:]   # String now contains xxxxxx'

    def ptoken(self):
        cls_str=assembler.eloc(self,"ptoken",module=this_module)
        raise NotImplementedError("%s TID:%s must only be recognized in binary "
            "expressions" % (cls_str,self.tid))

class StringType(lexer.Type):
    def __init__(self,debug=False):
        pattern="'[^']*'"
        super().__init__("STRING",pattern,tcls=StringToken,debug=debug)



#
#  +-----------------------------------------+
#  |                                         |
#  |   Finite-Machine Parsing Base Classes   |
#  |                                         |
#  +-----------------------------------------+
#


# Base class for AsmFSMParser scopes supporting expressions and compound strings.
# Other parsers may continue to utilize fsmparser.PScope.  It has special handling
# for elements encountered in assembly parsing, specifically, expressions and 
# strings with dual single quotes that must be converted to a single quote.
class AsmFSMScope(fsmparser.PScope):
    def __init__(self):
        super().__init__()

    # Raise an AsmParserError if expression parenthesis are not balanced.
    # Must be explicitly called by the scope user or the expr() method should be
    # used to ensure parenthesis are balanced.
    # Method Argument:
    #   ltok    The lexical token following the expression used by the exception
    #           for error reporting.
    # Exceptions
    #   assembler.AsmParserError raised if the expression's parenthesis are not
    #           balanced.
    def ck_parens(self,ltok):
        if self._parens!=0:
            raise assembler.AsmParserError(ltok,msg="unbalanced parenthesis")

    # Initializes the scope for use.  Automatically called by super class
    def init(self):
        self._string=None     # Accumulates a complex string with double single quotes
        self._lextoks=[]      # List of accumulated token on an expression
        self._parens=0        # Used to check for balanced parenthesis

    # Check the expression for balanced parenthesis and return the lexical token
    # list if balanced.
    # Method Argument:
    #   ltok    The lexical token following the expression used by the exception
    #           for error reporting.
    # Exceptions
    #   assembler.AsmParserError raised if the expression's parenthesis are not
    #           balanced.
    def expr(self,ltok):
        self.ck_parens(ltok)
        return self.expr_end()

    # Returns the list of accumulated tokens, presumably for an expression
    def expr_end(self):
        self._parens=0
        expr=self._lextoks
        self._lextoks=[]
        return expr

    # Process a left parenthesis in an expression.  Adds the parenthesis to the
    # expression lexical token list and increments the parenthesis count
    def lparen(self,value):
        self._parens+=1
        self.token(value)
        
    # Process a right parenthesis in an expression.  Add the parenthesis to the
    # expression lexical token list and decrements the parenthesis count
    def rparen(self,value):
        self._parens-=1
        self.token(value)

    # Start accumulation of a compound string.
    def str_begin(self,value):
        assert isinstance(value,StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_begin",module=this_module),value)
        assert self._string is None,\
            "%s '_string' attribute is not None when starting a compound string: %s" \
                % (assembler.eloc(self,"str_begin",module=this_module),\
                    self._string)

        self._string=value

    # Adds additional string content to the compound string
    def str_cont(self,value):
        assert isinstance(value,StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_cont",module=this_module),value)
        assert isinstance(self._string,StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_cont",module=this_module),self.string)

        self._string.extend(value)

    # Returns the StringToken object of the accumulated string.
    def str_end(self):
        if self._string is None:
            return
        assert isinstance(self._string,StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_end",module=this_module),self._string)

        accum=self._string
        self._string=None
        return accum

    # Returns whether a string is pending (True) or not (False)
    def str_pending(self):
        return self._string is not None

    # Adds lexical tokens to the expression token list
    def token(self,tok):
        self._lextoks.append(tok)
        
    # Updates a lexical token to reflect its position in the Stmt object's source
    # statement.
    def update(self,stmt,token):
        lineno=stmt.lineno
        source=stmt.source
        operpos=stmt.fields.operpos
        token.update(lineno,operpos,source)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
