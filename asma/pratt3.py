#!/usr/bin/python3.3
# Copyright (C) 2015 Harold Grovesteen
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

# This module provides an Python based top-down operator precedence parser.  It 
# extends and generalizes the capabilities offered by the pratt.py module.

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
# can then be collected and presented at any time appropriate for evaluation by the
# Pratt parser.
#
# pratt2.py vs. pratt.py
# --------- --- --------
#
# The pratt.py module is restricted to arithmetic expressions consisting of only 
# addition, subtraction, multiplication and division infix operators and the plus or
# minus unary operators.  Operator precedence for these arithmetic operators is
# fixed to those used by arithmetic calculations: multiplication and division take
# precedence over addition or subtraction with parathesized expressions overriding
# normal precedence rules.
#
# pratt2.py provides handling of any number of infix or unary operators and any
# arbitrary set of precedence rules.  As with the normal case, parenthesized
# expresions override the normal rules.
#
# pratt3.py vs. pratt2.py
# --------- --- ---------
#
# The pratt2.py module is restricted to serial reuse of the PParser object.  This
# means only a single PExpr object can be evaluated at a single time.  This
# limitation results from the controls that fetch the next token residing in the
# PParser object itself.  The pratt3.py module removes these from PParser by placing
# them in a single use evalutation specific object, the PCtx.  This change
# allows recursive operands.  Such operands themselves have embedded expressions
# that may be evalutated using the same or different PParser object while the
# operand itself is used as in a different expression.  This change modifies the
# PParser method signatures, passing the PCtx object around while the expression
# is being evalutated. Further it allows all expression evalutation to use a 
# single function as the executor of expression evaluation.

# Python imports: None
# SATK imports:
import lexer         # Access lexical analyzer tokens as an interface to pratt

this_module="%s.py" % __name__

#
#  +----------------------------------+
#  |                                  |
#  |   PParser User Error Exception   |
#  |                                  | 
#  +----------------------------------+
#

# This exception is triggered when an expression evaluation encounters a user
# created error (as opposed to internal errors which trigger NotImplementedError
# or ValueError exceptions).
#
# Users of a Pratt evaluator should catch and respond to this exception.
class PParserError(Exception):
    def __init__(self,ptok=None,msg=""):
        self.msg=msg         # Text associated with the error
        self.ptok=ptok       # PToken or subclass associated with the error
        self.pos=None        # Position from possible source token
        if ptok is not None:
            string=PParser.token_id(ptok)
            src=ptok.src
            if isinstance(src,lexer.Token):
                self.pos=src.linepos
        else:
            string=""
        string="%s%s" % (string,msg)
        super().__init__(string)

# This exception is intended for use by PToken subclasses to recognize context
# related errors and communicate the nature of the error to the evalutor.  The
# response by the evaluator is to trigger a PParserError that passes on the cause
# of the error in conjuction with the PToken object that detected the error.
#
# This mechanism allows objects that participate in the evaluation but are logically
# separated from the PToken object to trigger an exception locally.  Unlike the
# PParserError exception, the PEvaluationError is caught by the Pratt parser.
# It should be viewed as an internal communication vehicle between Pratt parser
# objects.
class PEvaluationError(Exception):
    def __init__(self,msg=""):
        self.msg=msg

#
#  +-------------------------------------------+
#  |                                           |
#  |   Standardized Error Location Reporting   |
#  |                                           | 
#  +-------------------------------------------+
#

# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     raise Exception("%s %s" % (eloc(self,"method"),"error information"))
#
# It results in a Exceptin string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)

#
#  +-------------------------+
#  |                         |
#  |   Pratt Parser Tokens   |
#  |                         | 
#  +-------------------------+
#

# External Helper Objects
# -------- ------ -------
#
# When utilizing the operator precedence parser/evaluator, external assistance may be
# required.  It takes two forms:
#  1.  objects that participate in Python operations via overloading methods and
#  2.  an external object that assists in conversion of a "value" into one of these
#      objects.
# The first mechanism is inherent in the definition of the Python object representing
# the "value".  
#
# The second mechanism is typically used to resolve a value's symbolic reference into
# an object that can participate in the expression evaluation.  This module offers two
# approaches for the second type.  If the helper object is static it can be supplied
# when the PToken object is instantiated or via the PParser object itself.  However, if
# the helper object may change, for example, when a single expression may be evaluated
# with different contexts, the helper object may be supplied to the PParser.run()
# method and passed down to each token that may need it.
#
# In either situation, the method argument 'external' is used to provide the helper
# object.  If not used, it will default to None.  It is the responsibility of the
# PToken object subclass using the external helper to reference it and use it 
# as needed.  This module and its classes provide the static and dynamic external
# helper mechanisms but do not themselves utilize them for any purpose.

# Base class for all PTokens.
class PToken(object):
    def __init__(self,src):
        self.src=src    # Preserve the original input source object for literals

    # Infix processor
    # Its actual signature is: led(self,parser,left,debug=False)
    def led(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s must implement led() method" \
            % (eloc(self,"__init__"),self.__class__.__name__))

    # Unary processor
    # Its actual signature is: nud(self,parser,debug=False)
    def nud(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s must implement led() method" \
            % (eloc(self,"__init__"),self.__class__.__name__))


# Base class for all infix only operators.
# This class does the generic operator precedence management of operators.  Parsing
# of a list of PToken's is driven by the PParser.expression() method.
#
# Individual operator evaluation is performed in the respective subclass' calc_nud 
# (unary operator) or calc_led (infix operator) methods.
class Operator(PToken):
    def __init__(self,src):
        # These attributes are established by the bind() method when called by
        # the PParser.bind() method which is in turn driven by the PExpr.init()
        # method
        self.binding=None
        self.lbp=None
        self.rbp=None
        self.isinfix=None
        self.isunary=None
        self.symbol=None

        super().__init__(src)

    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__,self.symbol)

    def bind(self,binding):
        self.binding=binding
        self.lbp=binding.lbp
        self.rbp=binding.rbp
        self.isinfix=binding.isinfix
        self.isunary=binding.isunary
        self.symbol=binding.symbol

    # Returns the result of evaluating infix operator: left operator right
    # The subclass MUST provide this method to support the infix role.
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        raise PParserError(ptok=self,msg="syntax error: not an infix operator")

    # Returns the result of evaluating unary operator: operator right
    # Any Operator that supports a unary option MUST provide this method to support
    # the unary role.
    def calc_nud(self,ctx,right,debug=False,trace=False):
        raise PParserError(ptok=self,msg="syntax error: not a unary operator")

    # Generic infix operator processing
    def led(self,ctx,left,debug=False,trace=False):
        if not self.isinfix:
            raise PParserError(ptok=self,msg="is not an infix operator")

        if __debug__:
            if debug:
                cls=self.__class__.__name__
                print("%s.led() left input: %s" % (cls,left))
                print("%s.led() calling expression(%s,debug=%s)"\
                    % (cls,self.lbp,debug))

        # Calculate the right-hand side of the operator
        right=ctx.parser._expression(ctx,bp=self.lbp,debug=debug,trace=trace)
        
        if __debug__:
            if debug:
                print("%s.led() right -> %s" % (cls,right))

        # Calculate the operator's result from its left-hand and right-hand operands.
        res=self.calc_led(ctx,left,right)

        if __debug__:
            if debug:
                print("%s.led() result: %s" % (cls,res))

        if trace:
            self.trace_led(left,right,res)

        return res

    # Generic unary operator processing
    #def nud(self,parser,external=None,debug=False,trace=False):
    def nud(self,ctx,debug=False,trace=False):
        if not self.isunary:
            raise PParserError(ptok=self,msg=" is not a unary operator")

        if __debug__:
            if debug:
                cls=self.__class__.__name__
                print("%s.nud() calling expression(%s)" % (cls,self.rbp))

        # Calculate the right-hand side of the unary operator
        right=ctx.parser._expression(ctx,bp=self.rbp,debug=debug,trace=trace)

        if __debug__:
            if debug:
                print("%s.nud() right -> %s" % (cls,right))

        # Calculate the result of this unary operator on its right-hand operand
        res = self.calc_nud(ctx,right,debug=debug,trace=trace)

        if __debug__:
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

    def nud(self,ctx,debug=False,trace=False):
        res=self.value(external=ctx.external)

        if __debug__:
            if debug:
                print("PLit.nud() result: %s" % res)

        if trace:
            print("%s %s -> %s" % (self.__class__.__name__,self.src,res))

        return res

    # Override this method to do anything other than return self.src.
    def value(self,*args,**kwds):
        return self.src

# This subclass of PLit assumes the source is a lexer.Token instance.
class PLitTID(PLit):
    def __init__(self,token,external=None):
        assert isinstance(token,lexer.Token),\
            "%s 'token' argument must be an instance of lexer.Token: %s" \
                % (eloc(self,"__init__"),token)

        self.external=external   # An object providing external assistance
        super().__init__(token)

    def value(self,external=None,debug=False,trace=False):
        v=self.src.extract()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

# This subclass of PLit assumes the source is a langutil smart token instance.
# langutil module smart tokens support directly the convert() method.  They
# are subclasses of the lexer.token class.
class PLitSmart(PLitTID):
    def __init__(self,token,external=None):
        super().__init__(token,external)

    def value(self,external=None,debug=False,trace=False):
        v=self.src.convert()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__,self.src.string) 

# The following classes are examples of PToken classes typically expected to be 
# found in arithmetic expressions.  These classes support addition, subtraction,
# multiplication, division, parenthesized expressions and unary plus and minus.
# Additional classes may be defined and any of these may be subclassed as appropriate.
class PAdd(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left + right

    # Unary aritithmetic operation: positive of right
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        return right

class PDiv(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left divided by right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left / right

class PFloorDiv(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left divided by right, ignoring remainder
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left // right

class PMul(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left multiplyied by right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left * right

class PSub(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: right subtracted from left
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left - right

    # Unary arithmetic operation: negate right
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        return - right

# The following classes are examples of PToken classes typically expected to be 
# found in arithmetic expressions that perform bit-wise operations.  These classes 
# support bitwise infix operations: and, nand, nor, nxor, or, xor operations.
# Bitwise invertion, not, is a unary operation.
class PBWAnd(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left & right

class PBWNand(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return ~(left & right)

class PBWNor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return ~(left | right)

class PBWNot(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Unary arithmetic operation: inversion right
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        return ~ right

class PBWNxor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return ~(left ^ right)

class PBWOr(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left | right

class PBWXor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix arithmetic operation: left plus right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left ^ right


# Special end of expression "operator"
class PEnd(Operator):
    def __init__(self,src=None):
        super().__init__(src)


# This class manages parenthesis processing.  It is tightly coupled with the
# generic handling of unary operators in the Operator.nud() and the generic
# operator precedence evaluation in PParser._expression() methods.  Operator.nud()
# first calculates the sub-expression following the left parenthesis.  This sub-
# expression evaluation, in PParser._expression(), continues until the next token 
# has a left binding power less than the right binding power of the current unary
# operator, in this case the left binding power of this class, the PLParan object.
# The sub-expression needs to end when it finds its matching right parenthesis.
# That means the left and right parentheses must have defined the the same left and
# right binding power and it must be less than all other operators.  By defining rbp
# and lbp to zero for both the PLParan and PRParan classes satisfies this
# requirement.  The PParser object binds left and right parenthesis classes correctly
# for this handling.
#
# As a consequence of this processing, the calc_nud() method is not called until
# the subexpression has been evaluated.  The next token (because the subexpression
# has been consumed) must the a right parenthesis.  The calc_nud() method performs
# a look-ahead into the token list expecting a right parenthesis.  Assuming it is
# found, the right parenthesis is consumed.  For this reason the PRParen object
# always raises an exception if either of its calculation methods are actually
# called.  The value of the subexpression is simply returned.
class PLParen(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Unary operation: ( right
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        #cur_depth=parser.pexp
        cur_depth=ctx.pexp
        #parser.pexp+=1       # Increment parenthesized expression depth
        ctx.pexp+=1           # Increment parenthesized expression depth
        #parser._match(PRParen,debug=debug,trace=trace)
        ctx.match(PRParen,debug=debug,trace=trace)
        #parser.pexp-=1
        ctx.pexp-=1
        return right


class PRParen(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix operation: left ) right - this should not occur. see PLParan.calc_nud()
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        raise NotImplementedError("%s does not support unary role" \
            % eloc(self,"calc_led"))

    # Unary operation: ) right - this should not occur.  see PLParan.calc_nud()
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        raise NotImplementedError("%s does not support infix role" \
            % eloc(self,"calc_nud"))


# Comparison opeators:
#   ==, !=, <, <=, >, >=
#
# All of these are infix operators.
#
# The following classes are examples of PToken classes typically expected to be
# found in logical expressions.  These classes support comparisons  operations.
# Additional classes may be defined, and, any of these may be subclassed
# as appropriate, and combined with the previous arithmetic related classes, in
# particular, those supporting parenthesis.
class PEQ(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical comparison operation: left equals right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left == right


class PGE(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical comparison operation: left greater than or eqaul to right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left >= right 


class PGT(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical comparison operation: left greater than right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left > right


class PLE(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical comparison operation: left less than or eqaul to right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left <= right


class PLT(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical comparison operation: left < right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left < right


class PNE(Operator):
    def __init__(self,src=None):
        super().__init__(src)
    # Infix logical comparison: left not equal right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left != right


# Logical expression (not bitwise) operators:
#   not, and, nand, or, nor, xor, nxor 
#
# All of these are infix operators, except for 'not'.
#
# Python does not support override methods for logical operations involving 'or', 'and',
# 'not', etc.  The classes below depend upon comparison to 0 to detect the logical
# value of an operand.  In these methods a non-zero integer is considered True.  So -1
# and +1 both are treated as True.  This is consistent with how Python internally
# treats these values in logical expressions.  For objects that use overloading to
# perform calculations the override methods for __ne__ and __eq__ are required.  If a
# specific situation does not conform to these logical results, a subclass of Operator
# designed along the lines of these methods must be supplied.

#  not |
# -----+----
#   0  |  1
#   1  |  0
#
class PNot(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Unary logical operation: not right (not a bitwise operation)
    #def calc_nud(self,parser,right,external=None,debug=False,trace=False):
    def calc_nud(self,ctx,right,debug=False,trace=False):
        return right==0

#  and |  0   1
# -----+--------
#   0  |  0   0
#   1  |  0   1
#
class PAnd(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: left and right (not bitwise AND) 
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left!=0 and right!=0

# nand |  0   1
# -----+--------
#   0  |  1   1
#   1  |  1   0
#
class PNand(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: not left and right (not a bitwise operation) 
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return not (left!=0 and right!=0)

#  or  |  0   1
# -----+--------
#   0  |  0   1
#   1  |  1   1
#
class POr(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: left or right (not a bitwise or)
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return left!=0 or right!=0

#  nor |  0   1
# -----+--------
#   0  |  1   0
#   1  |  0   0
#
class PNor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: not left or right (not a bitwise operation)
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        return not (left!=0 or right!=0)

#  xor |  0   1
# -----+--------
#   0  |  0   1
#   1  |  1   0
#
class PXor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: left exclusive or with right (not a bitwise XOR)
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        if left!=0:               # 1 XOR ?
            if right!=0:          # 1 XOR 1 -> False
                return False
            else:                 # 1 XOR 0 -> True
                return True
        else:                     # 0 XOR ?
            if right!=0:          # 0 XOR 1 -> True
                return True
            else:                 # 0 XOR 0 -> False
                return False

# nxor |  0   1
# -----+--------
#   0  |  1   0
#   1  |  0   1
#
class PNxor(Operator):
    def __init__(self,src=None):
        super().__init__(src)

    # Infix logical operation: left not exclusive or with right
    #def calc_led(self,parser,left,right,external=None,debug=False,trace=False):
    def calc_led(self,ctx,left,right,debug=False,trace=False):
        if left !=0:              # 1 NXOR ?
            if right!=0:          # 1 NXOR 1 -> True
                return True
            else:                 # 1 NXOR 0 -> False
                return False
        else:                     # 0 NXOR ?
            if right!=0:          # 0 NXOR 1 -> False
                return False
            else:                 # 0 NXOR 0 -> True
                return True
        raise ValueError()

#
#  +------------------+
#  |                  |
#  |   Pratt Parser   |
#  |                  | 
#  +------------------+
#

# This object manages registered binding properties of each supported operator.
class Binding(object):
    def __init__(self,cls,lbp=None,rbp=None,symbol="?",isinfix=False,isunary=False):
        assert issubclass(cls,Operator),\
            "%s 'cls' argument not a subclass of Operator: %s" \
                % (eloc(self,"__init__"),cls)

        self.cls=cls
        self.lbp=None
        self.rbp=None
        self.symbol=symbol    # The operator's symbol used in trace messages

        # Establish Operator's role
        self.isinfix=isinfix  # Supports an infix role (True) or not (False)
        self.isunary=isunary  # Supports a unary role (True) or not (False)

        # Process lbp for infix operator role
        assert not (isinfix and not isinstance(lbp,int)),\
            "%s - 'lbp' argument must be an integer for infix operator %s: %s" \
                % (eloc(self,"__init__"),self.symbol,lbp)

        self.lbp=lbp

        # Process rbp for unary operator role
        assert not (isunary and not isinstance(rbp,int)),\
            "%s 'rbp' argument must be an integer for unary %s: %s" \
                % (eloc(self,"__init__"),self.symbol,rbp)
       
        self.rbp=rbp

# This class manages the access to tokens within an expression as a process
# separate from the PParser performing the evaluation.  Concurrent use of the 
# same PParser object (and hence its bindings) is supported.  Operands that
# themselves have expressions that require evaluation by the same PParser object
# are supported by this separation.  This object is intended for single use and
# should not be reused.  See the PParer.run() method.  Users of this module
# should never instantiate this class, nor subclass it.  Additional expression
# state, should be managed by the supplied external object if needed.
class PCtx(object):
    def __init__(self,parser,expr,external=None,emu=False,debug=False):
        assert isinstance(parser,PParser) or emu,\
            "%s 'parser' argument must be a PParser object: %s" \
                % (eloc(self,"__init__"),parser)
        assert isinstance(expr,PExpr),\
            "%s 'expr' argument must be a PExpr object: %s" \
                % (eloc(self,"__init__"),expr)

        self.parser=parser        # Parser being used by this evaluation
        
        # Initialize the expression
        expr._init(parser)
        self.expr=expr            # Initialized expression being evaluated
        self.ptokens=expr.toks    # List of initialized ptokens in expression
        self.expr_len=len(self.ptokens)   # Number of ptokens in expression

        # Evaluation state.
        self.external=external    # External helper object
        self.ndx=0     # Start at the beginning of the expression's tokens
        self.pexp=0    # Make sure parenthesis tracker is zero for new expression
        self.ptoken=self.next(debug=debug)   # Prime the evaluation (current token)
        
        if __debug__:
            if debug:
                print("%s pratt3 tokens:\n    %s" % (eloc(self,"run"),self.ptokens))

    # Validates parenthesis tracking values at the end of the evaluation
    def ck_parens(self):
        if self.pexp > 0:
            self.error(self.gen(PRParen))
        if self.pexp < 0:
            raise ValueError("%s - parenthesize expression tracker negative: %s" \
                % (eloc(self,"ck_parens"),self.pexp))

    # Generate a PParserError based upon the supplied token
    def error(self,ptok):
        raise PParserError(ptok,msg="Expected %s, encountered: %s" \
            %  (PParser.token_id(ptok),PParser.token_id(self.ptoken)))

    # Generate a token object for error reporting
    def gen(self,tokcls):
        obj=tokcls()
        self.parser.bind(obj)
        return obj

    # Match the current Ptoken instance as being a subclass of the supplied class.
    # If a match, consume the current token and advance to the next token
    # If not a match, raise an error
    def match(self,ptok=None,debug=False,trace=False):
        if __debug__:
            if debug:
                print("%s matching self.token=%s against %s" \
                    % (eloc(self,"match"),self.ptoken,ptok.__name__))

        current=self.ptoken
        if not isinstance(current,ptok):
            # Note ptok is a class object.  ParserError expects a class instance
            self.error(self.gen(ptok))
        self.ptoken=self.next(debug=debug)

        if trace:
            print("%s : %s -> next: %s" % (current,ptok.__name__,self.ptoken))

        if __debug__:
            if debug:
                print("match: current token after match of %s: %s" \
                    % (ptok,self.ptoken))

    # Returns the next PToken object to be processed.  It detects the end of the
    # list by presenting a instance of PEnd().
    # Note: DO NOT UPDATE self.ptoken IN THIS METHOD.  Control of the current
    # ptoken is performed by the parser.
    def next(self,debug=False):
        curndx=self.ndx
        if curndx>=self.expr_len:
            r=self.parser.pend
        else:
            r=self.ptokens[curndx]
            self.ndx+=1
        
        if __debug__:
            if debug:
                print("PCtx.next() returning [%s]: %s" % (curndx,r))
        return r

# This class defines an expression that will be evalutated.  It is the primary
# interface for the presentation of an expression that will be evualted one or 
# more times by the PParser object.  It only understand PToken objects.  If some
# other source exists for the expression, it must be converted to PToken objects
# before being presented to the PExpr class.
#
# Instance Arguments:
#   desc    A description of the expression.  Defaults to 'nodesc'.
#   tokens  A list of PTokens to be evaluated.  Defaults to [].
# Instance Methods:
#   init    Makes the expression ready for evaluation.
class PExpr(object):
    def __init__(self,desc="nodesc",tokens=[]):
        self.name=desc     # A description of this expression
        self.toks=[]       # List of PToken ojbects defining the expression

        # If True, binding attributes have been applied to the Operator objects.
        self._isinit=False
        if not isinstance(tokens,list):
            self.toks=[tokens,]
        else:
            self.toks=tokens

    def __str__(self):
        string="%s(desc='%s')" % (self.__class__.__name__,self.name)
        for tok in self.toks:
            string="%s\n    %s" % (string,tok.__class__.__name__)
        return string

    # This method performs error checks on the supplied tokens.  Initialization occurs
    # once for the object.  Because operator binding values are performed here,
    # once the object is initialized it is expected to be evalutated using the same
    # PParser object.
    #
    # The object must be initialized before use.
    # Method Arguments:
    #   pparser   A PParser object that contains the binding values of each operator.
    # Exceptions:
    #    ValueError     If the expression token list is empty or ends in an operator
    #                   or the token list ends in an operator.
    #    AssertionError If a token is not a PToken object.
    def _init(self,pparser):
        if self._isinit:
            return

        if len(self.toks)==0:
            raise ValueError("%s PExpr '%s' - can not initialize empty token list" \
                % (eloc(self,"_init"),self.name))

        for ndx,tok in enumerate(self.toks):
            assert isinstance(tok,PToken),\
                "%s PExpr %s - 'tokens[%s]' not a PToken object: %s" \
                    % (eloc(self,"_init"),self.name,ndx,t)

            if not isinstance(tok,Operator):
                continue
            try:
                pparser.bind(tok)
            except KeyError:
                raise ValueError(\
                    "%s PExpr %s - 'tokens[%s] not a registered operator: %s" \
                        % (eloc(self,"_init"),self.name,ndx,tok.__class__.__name__)) \
                    from None

        self._isinit=True  # Expression is initialized and ready for use.
        
    # Used to identify an return the only token when the expression is just one
    # token.  The user must know how to invoke the token's value() method.
    def quick(self):
        if len(self.toks)==1:
            return self.toks[0]
        
    # Add a token to the list of tokens in this expression.
    def token(self,tok):
        if isinstance(tok,list):
            self.toks.extend(tok)
        else:
            self.toks.append(tok)
        self._isinit=False


# This class is the base class of the operator precedence evaluator.
#
# Instance Arguments:
#   external   An external helper object used during expression evaluation. Looking
#              up a symbol's value in an external table is an example of how this
#              could be used.
#   leftp      PToken subclass representing a left parenthesis.  Defaults to PLParen
#              See the coments preceding the PLParen class above for more details.
#   rightp     PToken subclass representing a right parenthesis.  Defaults to PRParen
#              See the coments preceding the PLParen class above for more details.
#
# Instance Methods:
#   operator   Defines a the operator binding attributes of Operator subclasses.
#   run        The primary external method used to evaluate an expression based upon
#              a list of supplied PToken objects or subclasses.
class PParser(object):
    
    # This method provides an identification string associated with the token
    # If the token's src is a lexer.Token object, the string that was used to
    # recognized the lexical token is returned.  If not and the token is an 
    # expression operator, its printable symbol is returned.  Otherwise the objects
    # string representation is returned.
    @staticmethod
    def token_id(tok,debug=False):
        assert isinstance(tok,PToken),\
            "%s - PParser.token_id() - 'tok' argument must be a PToken object: %s" \
                % (this_module,tok)

        src=tok.src
        if isinstance(src,lexer.Token):
            string=src.string
        elif isinstance(tok,Operator):
            string=tok.symbol
        else:
            string="%s" % tok

        if __debug__:
            if debug:
                print("%s - PParser.token_id(%s) returning: '%s'" \
                    % (this_module,tok,string))

        return string

    def __init__(self,external=None,leftp=PLParen,rightp=PRParen):
        assert leftp==PLParen or issubclass(leftp,PLParen),\
            "%s 'leftp' argument must be a subclass of PLParen: %s" \
                % (eloc(self,"__init__"),leftp)
        assert rightp == PRParen or ssubclass(leftp,PRParen),\
            "%s 'rightp' argument must be a subclass of PRParen: %s" \
                % (eloc(self,"__init__"),rightp)

        #self.external=external   # External class made available to parser
        #self.ptokens=[]          # List of PTokens being parsed
        #self.ptoken=None         # Current PToken instance
        #self.ndx=None            # Next ptoken in self.ptokens to be provided

        # Parenthesizes expression depth handling
        #self.pexp=0

        # Defined Bindings for specific Operator subclasses
        self.bindings={}

        # Internally bind the generic PEnd operator and parenthesis operators.
        self.operator(PEnd,lbp=0,rbp=0,symbol="end",isinfix=False,isunary=True)
        self.operator(leftp,lbp=0,rbp=0,symbol="(",isinfix=False,isunary=True)
        self.operator(rightp,lbp=0,rbp=0,symbol=")",isinfix=False,isunary=False)
        self.pend=PEnd()
        self.bind(self.pend)

    # Evaluates a sub expression bounded by PToken binding properties.
    # Method Arguments:
    #   ctx     PCtx object containing the evaluation state
    #   bp      PTokens whose left binding property exceed this binding property 
    #           value are evaluted until a PToken is encountered with a lower
    #           left binding property or the end of the list is detected.
    #           Note: For infix operators, bp is its left binding property.
    #                 For unariy operators, bp is it right binding property.
    #   debug   If True details of the sub-expression evaluation are displayed
    #   trace   If True, operator and literals results are traced.
    def _expression(self,ctx,bp=0,external=None,debug=False,trace=False):
        if __debug__:
            if debug:
                print("_expression bp=%s" % bp)

        #t=self.ptoken
        t=ctx.ptoken

        if __debug__:
            if debug:
                print("_expression initial token: %s" % t)

        #next_tok=self.ptoken=self._next()
        next_tok=ctx.ptoken=ctx.next(debug=debug)
        # next_tok gives us look ahead to detect premature end of expression for
        # unary operators

        if __debug__:
            if debug:
                #print("_expression next token: %s" % self.ptoken)
                print("_expression next token: %s" % next_tok)
                print("_expression calling %s.nud()" % t.__class__.__name__)

        # The start of a subexpression must be a literal or unary operator.
        # Two distinctly different actions are taken depending upon whether the
        # current token is a literal (PLit or subclass) or an operator (Operator
        # or subclass).  For literals, the nud() method returns the literals
        # value.  For operators, the operator must be a unary operator and the 
        # expression to the right of the operator is evaluated.  Various tokens
        # will be consumed in this second case.

        # Evaluate the unary operator or operand
        if isinstance(t,Operator) and t.isunary and isinstance(next_tok,PEnd):
            raise PParserError(ptok=t,msg="operand required for operator")
        try:
            #left=t.nud(self,external=external,debug=debug,trace=trace)
            left=t.nud(ctx,debug=debug,trace=trace)
        except PEvaluationError as ee:
            raise PParserError(ptok=t,msg=ee.msg) from None

        if left is None:
            raise ValueError("%s %s.nud expression -> %s" \
                % (eloc(self,"_expression"),t.__class__.__name__,left))

        if __debug__:
            if debug:
                print("_expression %s.nud left -> %s" % (t.__class__.__name__,left))

        # Various tokens may be consumed by the call to t.nud() above.  ctx.ptoken
        # may not be the same at this point.  
        while True:
            #if isinstance(self.ptoken,PLit):
            #    raise PParserError(ptok=self.ptoken,msg="not an operator")
            if isinstance(ctx.ptoken,PLit):
                raise PParserError(ptok=ctx.ptoken,msg="not an operator")

            # This tests whether the evalutation loop in this call should continue
            #test=bp < self.ptoken.lbp
            test=bp < ctx.ptoken.lbp
            if __debug__:
                if debug:
                    #print("_expression: bp < self.ptoken.lbp -> %s < %s -> %s" \
                    #    % (bp,self.ptoken.lbp,test))
                    print("_expression: bp < ctx.ptoken.lbp -> %s < %s -> %s" \
                        % (bp,ctx.ptoken.lbp,test))
            # test failed, so bail from the while loop
            if not test:
                break

            #t=self.ptoken
            t=ctx.ptoken

            if __debug__:
                if debug:
                    print("_expression while current token: %s" % t)

            if isinstance(t,PEnd):
                if __debug__:
                    if debug:
                        print("_expression terminating due to PEnd recognzized")
                break

            #next_token=self._next()
            next_token=ctx.next(debug=debug)
            # Detect end of epression when infix operator needs an right-hand operand
            if isinstance(next_token,PEnd):
                #raise PParserError(ptok=self.ptoken,\
                raise PParserError(ptok=ctx.ptoken,\
                    msg="operand required for operator")
            #self.ptoken=next_token
            ctx.ptoken=next_token

            if __debug__:
                if debug:
                    #print("_expression while next token: %s" % self.ptoken)
                    print("_expression while next token: %s" % ctx.ptoken)
                    print("_expression calling %s.led(left=%s,debug=%s)" \
                        % (t.__class__.__name__,left,debug))

            # Evaluate infix operator
            try:
                #left=t.led(self,left,external=external,debug=debug,trace=trace)
                left=t.led(ctx,left,debug=debug,trace=trace)
            except PEvaluationError as ee:
                raise PParserError(ptok=t,msg=ee.msg) from None

            if left is None:
                raise ValueError("%s %s.led expression -> %s" \
                    % (eloc(self,"_expression"),t.__class__.__name__,left))

            if __debug__:
                if debug:
                    print("_expression while left -> %s" % left)

        if trace or (__debug__ and debug):
            print("_expression returning left: %s" % left)

        return left

    # Occasionally this class needs to create a PToken object.  This method
    # applies the same processes to it as does the Expr._init() method.
    #def _gen(self,tokcls):
    #    obj=tokcls()
    #    self.bind(obj)
    #    return obj

    # Match the current Ptoken instance as being a subclass of the supplied class.
    # If a match, consume the current token and advance to the next token
    # If not a match, raise an error
    #def _match(self,ptok=None,debug=False,trace=False):
    #    if __debug__:
    #        if debug:
    #            print("%s matching self.token=%s against %s" \
    #                % (eloc(self,"_match"),self.ptoken,ptok.__name__))

    #    current=self.ptoken
    #    if not isinstance(current,ptok):
    #        # Note ptok is a class object.  ParserError expects a class instance
    #        self.error(self._gen(ptok))
    #    self.ptoken=self._next()

    #    if trace:
    #        print("%s : %s -> next: %s" % (current,ptok.__name__,self.ptoken))

    #    if __debug__:
    #        if debug:
    #            print("match: current token after match of %s: %s" \
    #                % (ptok,self.ptoken))

    # Returns the next PToken object to be processed.  It detects the end of the
    # list by presenting a instance of PEnd().
    #def _next(self):
    #    if self.ndx>=len(self.ptokens):
    #        return self.pend
    #    n=self.ptokens[self.ndx]
    #    self.ndx+=1
    #    return n

    # This method evalutates a previously supplied list of PToken objects.
    #def _parse(self,external=None,debug=False,trace=False):
    def _parse(self,ctx,debug=False,trace=False):
        if __debug__:
            if debug:
                print("_parse...")

        # New expression...
        #self.ndx=0     # Start at the beginning of the expression's tokens
        #self.pexp=0    # Make sure parenthesis tracker is zero for new expression
        #self.ptoken=self._next()  # Prime the evaluation

        if __debug__:
            if debug:
                #print("_parse: initial token: %s" % self.ptoken)
                print("_parse: initial token: %s" % ctx.ptoken)
                print("_parse: callng expression(rbp=0,debug=%s)" % debug)

        #exp=self._expression(bp=0,external=external,debug=debug,trace=trace)
        result=self._expression(ctx,bp=0,debug=debug,trace=trace)

        if __debug__:
            if debug:
                print("_parse -> %s" % result)

        #if self.pexp > 0:
        #    self.error(self._gen(PRParen))
        #if self.pexp < 0:
        #    raise ValueError("%s - parenthesize expression tracker negative: %s" \
        #        % (eloc(self,"_parse"),self.pexp))
        ctx.ck_parens()

        # Return the evaluated expression's result
        return result

    # Initialize a new series of PTokens for parsing.
    # Returns:
    #   The PCtx object representing the expression's 
    #def _start(self,expr):
    #    assert isinstance(expr,PExpr),\
    #        "%s 'expr' argument must be a PExpr object: %s" \
    #            % (eloc(self,"_start"),expr)

        # Initialize the expression object.
        # Exceptions raised:
        #    ValueError   if the expression token list is empty or ends in an operator
        #                 or the token list ends in an operator.
        #    AssertionError if a token is not a PToken object.
    #    expr._init(self)

        # The initialized tokens are referenced from this object once initialized.
    #    self.ptokens=expr.toks

    # Bind an instance of an Operator to its precedence bindings
    # Exception:
    #   KeyError if Operator class has not been registered with the parser.
    def bind(self,opr):
        binding=self.bindings[opr.__class__]
        opr.bind(binding)

    # Override this method to provide different handling of a syntax error.
    #def error(self,ptok):
    #    raise PParserError(ptok,msg="Expected %s, encountered: %s" \
    #        %  (PParser.token_id(ptok),PParser.token_id(self.ptoken)))

    # Establishes the binding definition of an opertor based upon is class.
    # See the class Binding for details of the argument usage.
    #
    # Note: the PParser object automatically handles the internal PEnd object and
    # the correct binding values for subclasses of PLParen and PRParen classes.
    # A user can not bind such classes with this method.  They will already be
    # registered.
    def operator(self,cls,lbp=None,rbp=None,symbol="?",isinfix=False,isunary=False):
        bnd=Binding(cls,lbp=lbp,rbp=rbp,symbol=symbol,isinfix=isinfix,isunary=isunary)
        try:
            self.bindings[bnd.cls]
            raise ValueError("%s class already registered as an operator: %s" \
                % (eloc(self,"operator"),cls.__name__))
        except KeyError:
            self.bindings[bnd.cls]=bnd  

    # Evalutes an expression based upon defined operator precedence rules
    # Method Arguments:
    #   expr      A PExpr object defining an expression for evaluation
    #   external  An external helper object shared with all PTokens during
    #             expression evaluation.  Alternatively an external helper object
    #             may be defined when a PToken object is instantiated.  
    #             Default is None
    #   debug     If True provides a set of debug messages during processing
    #   trace     If True traces the expression evaluation results.  This is less
    #             verbose, displaying just the results of each operator
    #   _test     If True, prints the result of the embedded test.  Not recommended 
    #             for use outside of this module.
    # Returns:
    #   the result of the expression evaluation.  Results may be other than integers
    #   depending upon the processing of operand subclasses.
    # Exception:
    #   PParserError if the object detects an error during evaluation.
    #   Other exceptions are possible if subclasses implement them.
    def run(self,expr,external=None,debug=False,trace=False,_test=False):
        ctx=PCtx(self,expr,external=external,debug=debug)
        #self._start(expr)

        #if __debug__:
        #    if debug:
        #        print("%s pratt3 tokens:\n    %s" % (eloc(self,"run"),self.ptokens))

        #res=self._parse(external=external,debug=debug,trace=trace)
        res=self._parse(ctx,debug=debug,trace=trace)
        #if self.pexp!=0:
        if ctx.pexp!=0:
            #if self.pexp<0:
            #raise PParserError(msg="too many right parenthesis parenthesis, "
            #       "found %s more" % -1*self.pexp)
            #else:
            #    raise PParserError(msg="too few right parenthesis parenthesis, "
            #       "expected %s more" % self.pexp)
            if ctx.pexp<0:
               raise PParserError(msg="too many right parenthesis, "
                   "found %s more" % -1*ctx.pexp)
            else:
                raise PParserError(msg="too few right parenthesis, "
                   "expected %s more" % ctx.pexp)

        if __debug__:
            if trace:
                print("exp '%s' -> %s" % (expr.name,res))
            elif _test:
                print("exp '%s' test result: %s" % (expr.name,res))
                return

        return res


if __name__ == "__main__":
    # Comment out the following statement to run tests
    raise NotImplementedError("%s - intended for import use only" % this_module)

    #       5      +      1       /      (         2        )
    lst1=[PLit(5),PAdd(),PLit(1),PDiv(),PLParen(),PLit(2),PRParen()]
    pexpr1=PExpr(desc="lst1",tokens=lst1)
    #       5      +      -      1
    lst2=[PLit(5),PAdd(),PSub(),PLit(1)]
    pexpr2=PExpr(desc="lst2",tokens=lst2)
    #       5       +      (          (       2        )         )
    lst3=[PLit(5),PAdd(),PLParen(),PLParen(),PLit(2),PRParen(),PRParen()]
    #       5       +      (       7         *      (       2        )
    lst3=[PLit(5),PAdd(),PLParen(),PLit(7),PMul(),PLParen(),PLit(2),PRParen()]
    #             -       1         )
    lst3.extend([PSub(),PLit(1),PRParen()])
    pexpr3=PExpr(desc="lst3",tokens=lst3)

    p=PParser()
    p.operator(PAdd,lbp=10,rbp=100,symbol="+",isinfix=True,isunary=True)
    p.operator(PDiv,lbp=20,rbp=None,symbol="/",isinfix=True,isunary=False)
    p.operator(PFloorDiv,lbp=20,rbp=None,symbol="//",isinfix=True,isunary=False)
    p.operator(PMul,lbp=20,rbp=None,symbol="*",isinfix=True,isunary=False)
    p.operator(PSub,lbp=10,rbp=100,symbol="-",isinfix=True,isunary=True)

    p.run(pexpr1,debug=False,trace=True,_test=True)
    p.run(pexpr2,debug=False,trace=True,_test=True)
    p.run(pexpr3,debug=False,trace=True,_test=True)
