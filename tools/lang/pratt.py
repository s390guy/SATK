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

# This module provides an Python based top-down operator precedence parser.

#
#  +-------------------------------------------------+
#  |                                                 |
#  |   Pratt Top-down Expression Precedence Parser   |
#  |                                                 | 
#  +-------------------------------------------------+
#

# This expression parser is based upon the research of Vaughn Pratt published in an
# article entitled "Top-down Operator Precedence".  The original article can be
# found by Googling for the article's title.  Insight for this parser was provided
# by Eli Bendersky in an article posted on his website, "Top-Down operator precedence
# parsing" available here
#     http://eli.thegreenplace.net/2010/01/02/top-down-operator-precedence-parsing/
#
# Pratt parsers use the concept of binding power applied to a set of tokens.  As
# implemented they typically parse an input stream into a series of tokens on which
# evaluation occurs as the tokens are recognized.  For integration into the SATK system,
# the actual parsing of the input should remain with the lexical and possibly
# the semantic processors.  As the Eli Bendersky article shows, text is parsed and
# as tokens are recognized they are converted into instances of some simple token
# classes.  This is the identical process used by the SATK lexical analyzer.  Instances 
# of these classes are actually presented to the Pratt parser for evaluation.
#
# This implementation replaces the built in parsing used by Mr. Bendershy's parser with
# the tools already available in the language toolkit of SATK.  An implementation
# using SATK would convert SATK lexer.Token instances into Pratt parser tokens.  These
# can they be collected and presented at any time appropriate for evaluation by the
# Pratt parser.

# Python imports: None
# SATK imports: None

#
#  +-----------------------------------+
#  |                                   |
#  |   PParser User Error Exceptions   |
#  |                                   | 
#  +-----------------------------------+
#

class PParserError(Exception):
    def __init__(self,ptok=None,msg=""):
        self.msg=msg         # Text associated with the error
        self.ptok=ptok       # PToken or subclass associated with the error
        
        string="%s %s" % (ptok.__class__.__name__,msg)
        super().__init__(string)


#
#  +-------------------------+
#  |                         |
#  |   Pratt Parser Tokens   |
#  |                         | 
#  +-------------------------+
#

# Base class for all PTokens.
class PToken(object):
    def __init__(self,src):
        self.src=src    # Preserve the original input source object for literals

    # Infix processor
    # Its actual signature is: led(self,parser,left,debug=False)
    def led(self,*args,**kwds):
        raise NotImplementedError("pratt.py - %s.led() - subclass must implement led() "
            "method" % self.__class__.__name__)

    # Unary processor
    # Its actual signature is: nud(self,parser,debug=False)
    def nud(self,*args,**kwds):
        raise NotImplementedError("pratt.py - %s.nud() - subclass must implement nud() "
            "method" % self.__class__.__name__)

# Base class for all infix only operators.
# This class does the generic operator precedence management of operators.  Parsing
# of a list of PToken's is driven by the PParser.expression() method.
#
# Individual operator evaluation is performed in the respective subclass' calc_nud 
# (unary operator) or calc_led (infix operator) methods.
class Operator(PToken):
    def __init__(self,src,lbp=None,rbp=None,symbol="?",isinfix=False,isunary=False):
        self.lbp=None
        self.rbp=None

        # Establish Operator's role
        self.isinfix=isinfix  # Supports an infix role (True) or not (False)
        self.isunary=isunary  # Supports a unary role (True) or not (False)

        # Process lbp for infix operator role
        if isinfix and (not isinstance(lbp,int)):
            raise ValueError("pratt.py - %s.__init__() - 'lbp' argument must be "
                "an integer for infix operator: %s" % (self.__class__.__name__,lbp))
        else:
            self.lbp=lbp

        # Process rbp for unary operator role
        if isunary and (not isinstance(rbp,int)):
            raise ValueError("pratt.py - %s.__init__() - 'rbp' argument must be "
                "an integer for unary: %s" % (self.__class__.__name__,rbp))
        else:
            self.rbp=rbp

        self.symbol=symbol    # The operator's symbol used in trace messages
        super().__init__(src)

    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__,self.symbol)

    # Returns the result of evaluating infix operator: left operator right
    # The subclass MUST provide this method
    def calc_led(self,parser,left,right,debug=False,trace=False):
        raise PParserError(ptok=self,msg="syntax error: not an infix operator")

    # Returns the result of evaluating unary operator: operator right
    # Any Operator that supports a unary option MUST provide this method
    def calc_nud(self,parser,right,debug=False,trace=False):
        raise PParserError(ptok=self,msg="syntax error: not an unary operator")

    # Generic infix operator processing
    def led(self,parser,left,debug=False,trace=False):
        if not self.isinfix:
            raise PParserError(ptok=self,msg="is not an infix operator")
        if debug:
            cls=self.__class__.__name__
            print("%s.led() left input: %s" % (cls,left))
            print("%s.led() calling expression(%s,debug=%s)"\
                % (cls,self.lbp,debug))

        right=parser.expression(self.lbp,debug=debug,trace=trace)
        if debug:
            print("%s.led() right -> %s" % (cls,right))
        res=self.calc_led(parser,left,right)
        if debug:
            print("%s.led() result: %s" % (cls,res))
        if trace:
            self.trace_led(left,right,res)
        return res

    # Generic unary operator processing
    def nud(self,parser,debug=False,trace=False):
        if not self.isunary:
            raise PParserError(ptok=self,msg="is not an unary operator")
        if debug:
            cls=self.__class__.__name__
            print("%s.nud() calling expression(%s)" % (cls,self.rbp))
        right=parser.expression(self.rbp,debug=debug,trace=trace)
        if debug:
            print("%s.nud() right -> %s" % (cls,right))
        res = self.calc_nud(parser,right,debug=debug,trace=trace)
        if debug:
            print("%s.nud() result: %s" % (cls,res))
        if trace:
            self.trace_nud(right,res)
        return res

    # Override either of these methods to modify the results of a trace
    def trace_led(self,left,right,res):
        print("%s %s %s -> %s" % (left,self.symbol,right,res))

    def trace_nud(self,right,res):
        print("%s %s -> %s" % (self.symbol,right,res))

# The PLit class is the operator argument class.  ALL operator evaluations utilize an
# instance of PLit (or subclass) as its argument for evalution.
#
# Instance arguments:
#    src     This is any object that can participate in the operations coded in a
#            respective calc_led() or calc_nud() method. Any argument is accepted.  
#            See the following considerations for src objects for details.
#
# Considerations for src objects.
#   Plit instances (or a subclass) are the arguments for ALL expression evaluation
#   calculations.  The requirements of the PLit instance (or subclass) are dictated
#   by what has been coded in the operator's calc_nud() or calc_led() methods.  The
#   supplied arithmetic operator classes use Python arithmetic operators directly.
#   This leads to two cases.
#
#    Case 1: the src object CAN perform the required operations itself.
#            Such an object will have overloading methods for arithmetic (__add__,
#            __mul__, etc.) or inherently support them, for example a Python int
#            object.  In this PLit may be used directly.  See the test examples at
#            the end of the module.  This is the case when the various operator
#            classes supplied by this module are used for arithmetic expressions
#            without any overriding subclass methods for calc_nud() or calc_led()
#
#    Case 2: The src object CAN NOT perfrom required operations directly.
#            In this case an object that can perform the required operations must be
#            derivable from the src object.  A subclass of PLit will be required to
#            derive this object in its overriding value() method, returning the 
#            derived object.
class PLit(PToken):
    def __init__(self,src=None):
        super().__init__(src)
    def nud(self,parser,debug=False,trace=False):
        res=self.value()
        if debug:
            print("PLit.nud() result: %s" % res)
        if trace:
            print("%s %s -> %s" % (self.__class__.__name__,self.src,res))
        return res

    # Override this method to do anything other than return self.tok.
    def value(self,*args,**kwds):
        return self.src


# The following classes are examples of PToken classes typically expected to be 
# found.  These classes support addition, subtraction, multiplication, division,
# parenthesized expressions and unary plus and minus.  Additional classes may be
# defined and any of these may be subclassed as appropriate.
class PAdd(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=10,rbp=100,symbol="+",isinfix=True,isunary=True)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        return left + right

    def calc_nud(self,parser,right,debug=False,trace=False):
        return right

class PDiv(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=20,rbp=None,symbol="/",isinfix=True,isunary=False)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        return left / right

class PFloorDiv(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=20,rbp=None,symbol="//",isinfix=True,isunary=False)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        return left // right

class PEnd(Operator):
    def __init__(self):
        super().__init__(None,lbp=0,rbp=0,symbol="None",isinfix=False,isunary=True)

class PLParan(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=0,rbp=0,symbol="(",isinfix=False,isunary=True)

    def calc_nud(self,parser,right,debug=False,trace=False):
        cur_depth=parser.pexp
        parser.pexp+=1       # Increment parenthesized expression depth
        parser.match(PRParan,debug=debug,trace=trace)
        parser.pexp-=1
        return right

class PMul(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=20,rbp=None,symbol="*",isinfix=True,isunary=False)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        return left * right

class PRParan(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=0,rbp=0,symbol=")",isinfix=True,isunary=True)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        cls_str="pratt.py - %s.calc_nud() -" % self.__class__.__name__
        raise NotImplementedError("%s does not support unary role" % cls_str)

    def calc_nud(self,parser,right,debug=False,trace=False):
        cls_str="pratt.py - %s.calc_nud() -" % self.__class__.__name__
        raise NotImplementedError("%s does not support infix role" % cls_str)

class PSub(Operator):
    def __init__(self,src=None):
        super().__init__(src,lbp=10,rbp=100,symbol="-",isinfix=True,isunary=True)

    def calc_led(self,parser,left,right,debug=False,trace=False):
        return left - right

    def calc_nud(self,parser,right,debug=False,trace=False):
        return - right

#
#  +------------------+
#  |                  |
#  |   Pratt Parser   |
#  |                  | 
#  +------------------+
#

class PParser(object):
    def __init__(self,external=None):
        self.external=external   # External class made available to parser
        self.ptokens=[]          # List of PTokens being parsed
        self.ptoken=None         # Current PToken instance
        self.ndx=None            # Next ptoken in self.ptokens to be provided

        # Parenthesizes expression depth handling
        self.pexp=0

    # Override this method to provide different handling of a syntax error.
    def error(self,ptok):
        raise SyntaxError("Expected %s, encountered:%s"
            % (ptok,self.ptoken))

    def expression(self,rbp=0,debug=False,trace=False):
        if debug:
            print("expression rbp=%s" % rbp)
        t=self.ptoken
        if debug:
            print("expression initial token: %s" % t)
        self.ptoken=self.next()
        if debug:
            print("expression next token: %s" % self.ptoken)
            print("expression calling %s.nud()" % t.__class__.__name__)
        left=t.nud(self,debug=debug,trace=trace)
        if left is None:
            raise ValueError("expression -> %s" % left)
        if debug:
            print("expression left -> %s" % left)
        while rbp < self.ptoken.lbp:
            t=self.ptoken
            if debug:
                print("expression while current token: %s" % t)
            if isinstance(t,PEnd):
                if debug:
                    print("expression terminating due to PEnd recognzized")
                break
            self.ptoken=self.next()
            if debug:
                print("expression while next token: %s" % self.ptoken)
                print("expression calling %s.led(left=%s,debug=%s)" \
                    % (t.__class__.__name__,left,debug))
            left=t.led(self,left,debug=debug,trace=trace)
            if left is None:
                raise ValueError("expression -> %s" % left)
            if debug:
                print("expression while left -> %s" % left)
        if trace or debug:
            print("expression returning left: %s" % left)
        return left

    # Match the current Ptoken instance as being a subclass of the supplied class.
    # If a match, consume the current token and advance to the next token
    # If not a match, raise an error
    def match(self,ptok=None,debug=False,trace=False):
        cls_str="pratt.py %s.match() -" % self.__class__.__name__
        if debug:
            print("%s matching self.token=%s against %s" \
                % (cls_str,self.ptoken,ptok.__name__))
        current=self.ptoken
        if not isinstance(current,ptok):
            self.error(ptok)
        self.ptoken=self.next()
        if trace:
            print("%s : %s -> next: %s" % (current,ptok.__name__,self.ptoken))
        if debug:
            print("match: current token after match of %s: %s" % (ptok,self.ptoken))

    def next(self):
        if self.ndx>=len(self.ptokens):
            return PEnd()
        n=self.ptokens[self.ndx]
        self.ndx+=1
        return n

    # This method performs a parse of the PToken instances provided by the start
    # method and evalutates them during parse.
    def parse(self,debug=False,trace=False):
        if debug:
            print("parse...")
        self.ndx=0
        self.ptoken=self.next()
        if debug:
            print("parse: initial token: %s" % self.ptoken)
            print("parse: callng expression(rbp=0,debug=%s)" % debug) 
        exp=self.expression(rbp=0,debug=debug,trace=trace)
        if debug:
            print("parse -> %s" % exp)
        return exp

    # Run the parser using a list of PTokens.
    def run(self,lst,debug=False,trace=False,test=False):
        if debug:
            cls_str="pratt.py - %s.run() -" % self.__class__.__name__
            print("%s pratt tokens:\n    %s" % (cls_str,lst))
        self.start(lst)
        res=self.parse(debug=debug,trace=trace)
        if trace:
            print("exp -> %s" % res)
        elif test:
            print("test result: %s" % res)
            return
        else:
            pass
        return res

    # Initialize a new series of PTokens for parsing.
    def start(self,lst=[]):
        if not isinstance(lst,list):
            raise ValueError("pratt.py - PParser.tokenize() - 'lst' argument must be "
                "a list: %s" % lst)
        self.ptokens=lst

if __name__ == "__main__":
    # Comment out the following statement to run tests
    raise NotImplementedError("pratt.py - intended for import use only")

    #       5      +      1       /      (         2        )
    lst1=[PLit(5),PAdd(),PLit(1),PDiv(),PLParan(),PLit(2),PRParan()]
    #       5      +      -      1
    lst2=[PLit(5),PAdd(),PSub(),PLit(1)]
    #       5       +      (          (       2        )         )
    lst3=[PLit(5),PAdd(),PLParan(),PLParan(),PLit(2),PRParan(),PRParan()]
    #       5       +      (       7         *      (       2        )
    lst3=[PLit(5),PAdd(),PLParan(),PLit(7),PMul(),PLParan(),PLit(2),PRParan()]
    #             -       1         )
    lst3.extend([PSub(),PLit(1),PRParan()])

    p=PParser()
    p.run(lst1,debug=True)
    p.run(lst2,debug=True)
    p.run(lst3,debug=True,trace=True)
