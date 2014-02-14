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

# This module provides a pluggable expression engine for reuse in any language 
# processor requiring expression support.  It provides an interface between a parser 
# and the Pratt top-down operator precedence parser.  It supplies a portion of a 
# grammar, a set of callbacks for use by the parser in processing the expression 
# grammar it has supplied and a result class usable for evaluation.  

# This module allows different parsers in the same application to utilize the same 
# expression handling machinery with the same lexical tokens but different supporting
# parser grammars if needed.  While the motivation for this module was such separation
# it should serve equally well for a single parser.

# Three classes are provided:
#   ExpParser    This provides the interface with an SATK LL1Parser
#   ExpScope     This class is used to maintain parser scope data during grammar
#                parsing
#   Expression   The result of the grammar interface.  It is ready for evaluation
#                when completed.

# Python imports: none

# SATK imports: none
import lexer     # Access lexical analyzer tokens

# ASMA imports:
import pratt     # Access the Pratt top-down operator precedence parser

#
#  +-----------------------------------+
#  |                                   |
#  |   LL1 Parser Aware Pratt Tokens   |
#  |                                   | 
#  +-----------------------------------+
#

# This subclass of PLit assumes the source is a lexer.Token instance.
class PLitTID(pratt.PLit):
    def __init__(self,token,external):
        if not isinstance(token,lexer.Token):
            cls_str="assembler.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s 'token' argument must be an instance of "
                "lexer.Token: %s" % (cls_str,token))
        self.external=external   # An object providing external assistance
        super().__init__(token)
    def value(self,debug=False,trace=False):
        v=self.src.extract()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v

# This subclass of PLit assumes the source is a langutil smart token instance.
class PLitSmart(PLitTID):
    def __init__(self,token,external):
        super().__init__(token,external)
    def value(self,debug=False,trace=False):
        v=self.src.convert()
        if trace:
            print("%s.value() v=%s" % (self.__class__.__name__,v))
        return v
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "%s('%s')" % (self.__class__.__name__,self.src.string)    

# Interface classes for operators
class ExpAdd(pratt.PAdd):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpDiv(pratt.PDiv):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpFloorDiv(pratt.PFloorDiv):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpLParan(pratt.PLParan):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpMul(pratt.PMul):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpRParan(pratt.PRParan):
    def __init__(self,tok):
        super().__init__(src=tok)

class ExpSub(pratt.PSub):
    def __init__(self,tok):
        super().__init__(src=tok)

# This class manages expression handling
class Expression(object):
    def __init__(self,tokens,pparser):
        # List of Pratt Parser PToken instances
        self.ptokens=tokens   # These are accumulated by syntactical analyzer
        self.pparser=pparser  # Used to evaluate the expression
        
        # This value is provided by the evaluate method which is called by
        # Assembler.evaluate
        self.value=None

    def append(self,ptoken):
        if not isinstance(ptoken,pratt.PToken):
            cls_str="expression.py - %s.append() -" % self.__class__.__name__
            raise ValueError("%s 'ptoken' argument must be an instance of "
                "pratt.PToken: %s" % (cls_str,ptoken))
        self.ptokens.append(ptoken)

    def evaluate(self,debug=False,trace=False):
        # Evaluate the expression of PTokens
        res=self.pparser.run(self.ptokens,debug=debug,trace=trace)
        self.value=res

#Object maintains expression module state during callback processing of LL1 grammar
class ExpScope(object):
    def __init__(self):
        self.inexp=0     # Used by callbacks to know in LL1 expression parsing
        self.subexp=0    # Parenthensized expression depth
        self.ptokens=[]  # Accumulated list of ptoken during LL1 parsing

# This class manages the interface between the Pratt parser and the LL1Parser for
# parsing and evaluating expressions.  It is recommended that it be subclassed
# allowing the subclass to perform the pre-requisite mapping of lexical tokens
# to pratt aware tokens.

# Instance arguments:
#   pid    The grammar production ID for an expression.  Defaults to 'exp'
#   tids   A list of grammar tids that constiture individual expression factors.

class ExpParser(object):
    # Note this grammar is specific to the needs of the assembler module.
    # In the future, precedence levels and LL1 grammar generation need to be
    # generalized.  Right now the goal is to make the same processes reusable.
    grammar="""# Expression Productions for ExpParser
exp       -> term exp_more*
exp_more  -> PLUS exp
exp_more  -> MINUS exp
exp_more  -> EMPTY
term      -> factor term_more*
term_more -> MUL term
term_more -> DIV term
term_more -> EMPTY

# Expression Factors
"""

    def __init__(self,pid="exp",external=None):
        self.pid=pid            # Grammar pid for expressions
        self.external=external  # external helper during evaluation.

        self.pparser=pratt.PParser(external=external)

        # These dictionaries allows a lexical analyzer tid to be mapped to an 
        # instance of a pratt.PToken depending upon how they are found
        self.factor_map={}      # Populate by calls to factors() method
        self.operator_map={}    # Populate by calls to operators() method
        self.unaries=[]         # List of unary operators.
        # These attributes are populatd by a call to parans() method
        self.parans_map={}
        self.left_tid=None      # Lexical analyzer TID of left parenthesis
        self.right_tid=None     # Lexical analyzer TID of right parenthesis

        # Let subclass tailor the factors and operators
        self.define_operators()
        self.define_factors()
        self.define_parans()
        self.define_unary()

    def callbacks(self,lang):
        lang.cbreg("exp","beg",self.exp_begin)
        lang.cbreg("exp","end",self.exp_end)
        lang.cbreg("exp_more","token",self.exp_more_token)
        lang.cbreg("factor","token",self.factor_token)
        lang.cbreg("term_more","token",self.term_more_token)

    def get_grammar(self):
        gram=ExpParser.grammar
        for x in self.factor_map.keys():
            factor="factor -> %s\n" % x
            gram="%s%s" % (gram,factor)
        for x in self.unaries:
            factor="factor -> %s factor\n" % x
            gram="%s%s" % (gram,factor)
        gram="%sfactor -> %s %s %s" % (gram,self.left_tid,self.pid,self.right_tid)
        return gram

    def factors(self,tid,ptoken):
        cls_str="expression.py - %s.factors() -" % self.__class__.__name__
        if not isinstance(tid,str):
            raise ValueError("%s 'tid' argument must a string: %s" % (cls_str,tid))
        if not issubclass(ptoken,PLitTID):
            raise ValueError("%s 'ptoken' argument must be a subclass of "
                "pratt.PLitTID: %s" % (cls_str,ptoken))

        try:
            f=self.factor_map[tid]
            raise ValueError("%s factor tid already defined: '%s'" % (cls_str,tid))
        except KeyError:
            self.factor_map[tid]=ptoken

    def operators(self,tid,ptoken):
        cls_str="expression.py - %s.operators() -" % self.__class__.__name__
        if not isinstance(tid,str):
            raise ValueError("%s 'tid' argument must a string: %s" % (cls_str,tid))
        if not issubclass(ptoken,pratt.Operator):
            raise ValueError("%s 'ptoken' argument must be a subclass of "
                "pratt.Operator: %s" % (cls_str,ptoken))

        try:
            f=self.operator_map[tid]
            raise ValueError("%s operator tid already defined: '%s'" % (cls_str,tid))
        except KeyError:
            self.operator_map[tid]=ptoken

    def parans(self,left,right):
        cls_str="expression.py - %s.parans() -" % self.__class__.__name__
        if not isinstance(left,str):
            raise ValueError("%s 'left' argument must a string: %s" % (cls_str,tid))
        if not isinstance(right,str):
            raise ValueError("%s 'right' argument must a string: %s" % (cls_str,tid))
        self.parans_map[left]=ExpLParan
        self.left_tid=left
        self.parans_map[right]=ExpRParan
        self.right_tid=right

    def unary(self,tid,ptoken=None):
        cls_str="expression.py - %s.unary() -" % self.__class__.__name__
        if not isinstance(tid,str):
            raise ValueError("%s 'tid' argument must a string: %s" % (cls_str,tid))
        if ptoken is not None and not issubclass(ptoken,pratt.Operator):
            raise ValueError("%s 'ptoken' argument must be a subclass of "
                "pratt.Operator: %s" % (cls_str,ptoken))

        if tid in self.unaries:
            raise ValueError("%s 'tid' argument already defined as unary "
                    "operator: %s" % (cls_str,tid))

        # Defining an already defined infix operator as a unary operator
        if ptoken is None:
            try:
                f=self.operator_map[tid]
            except KeyError:
                raise ValueError("%s 'tid' argument not defined as an operator: %s" \
                    % (cls_str,tid)) from None
            self.unaries.append(tid)
            return

        # Defining a new operator as unary operator and mapping it to a token.
        try:
            f=self.operator_map[tid]
            raise ValueError("%s operator tid already defined: '%s'" % (cls_str,tid))
        except KeyError:
            pass
        self.operator_map[tid]=ptoken
        self.unaries.append(tid)

    #
    #  Subclass provided methods
    #

    #  Role: when the object is instantiated, it needs to know its factors.  In this
    #        method, the subclass must call the factors() method to define its
    #        factors.
    #
    def define_factors(self):
        cls_str="expression.py - %s.define_factors() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide define_factors() method")

    #  Role: when the object is instantiated, it needs to know its operators.  In this
    #        method, the subclass must call the operators() method to define its
    #        factors.
    #
    #  Note: TODAY THIS IS RESTRICTED TO THE OPERATORS EXPECTED BY THE GRAMMAR:
    #        PLUS, MINUS, MUL, DIV.  EACH MUST BE DEFINED TODAY.
    #
    def define_operators(self):
        cls_str="expression.py - %s.define_operators() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide define_operators() method")    

    #  Role: when the object is instantiated, it needs to know its parenthesis
    #        lexical analyzer token IDs..  In this method, the subclass must call the
    #        parans() method to define them.
    #
    def define_parans(self):
        cls_str="expression.py - %s.define_operators() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide define_operators() method")   

    #  Role: when the object is instantiated, it needs to know its unary operator
    #        lexical analyzer token IDs..  In this method, the subclass must call the
    #        unary() method to define them.
    #
    def define_unary(self):
        cls_str="expression.py - %s.define_unary() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide define_unary() method") 

    #  Role: language processor handling of completed expression LL1 parsing
    #        driven in PID exp 'end' callback
    #
    def expression_done(self,gs,exp,trace=False):
        cls_str="expression.py - %s.expression_done() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide expression_done() method")

    #
    #  method used by LL1 parser callback methods
    #

    def create_PToken(self,tok,mapdict,trace=False):
        cls_str="expression.py - %s.create_PToken()" % self.__class__.__name__
        tid=tok.tid
        try:
            cls=mapdict[tid]
        except KeyError:
            raise ValueError("%s unable to determine Pratt PToken class for "
                "lexical analyzer Token identifier (tid): '%s'" \
                % (cls_str,tid))
        if issubclass(cls,PLitTID):
            po=cls(tok,self.external)   
            # provide the lexer.Token and Assembler instance
        else:
            po=cls(tok)            
            # Use pratt module supplied PToken
        if trace:
            print("%s created %s('%s')" % (cls_str,po.__class__.__name__,tid))
        return po

    #
    # LL1parser.parser callback functions
    #

    def exp_begin(self,gs,pid):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="expression.py - %s.exp_begin() -" % self.__class__.__name__
            print(cls_str[:-2])
        try:
            exp=getattr(gs,"exp")
            if trace:
                print("%s found gs.exp" % cls_str)
        except AttributeError:
            exp=gs.exp=ExpScope()
            if trace:
                print("%s assigned gs.exp" % cls_str)

        exp.inexp+=1

    def exp_end(self,gs,pid,failed=False,eo=[]):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="expression.py - %s.exp_end()" % self.__class__.__name__
            print(cls_str)
        exp=gs.exp

        exp.inexp-=1
        if not exp.inexp:
            expr=Expression(exp.ptokens,self.pparser)
            self.expression_done(gs,expr,trace=trace)
            del gs.exp
            if trace:
                print("%s deleted gs.exp" % cls_str)

    def exp_more_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="expression.py - %s.exp_more_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))
        po=self.create_PToken(token,self.operator_map,trace=trace)
        gs.exp.ptokens.append(po)

    def factor_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="expression.py - %s.factor_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token))

        # Is this a left paran '('?
        if token.istype(self.left_tid):
            po=self.create_PToken(token,self.parans_map,trace=trace)
            gs.exp.subexp+=1
        # Is this a right paran ')'?
        elif token.istype(self.right_tid):
            po=self.create_PToken(token,self.parans_map,trace=trace)
            gs.exp.subexp-=1
        # Is this a unary operator?
        elif token.tid in self.unaries:
            po=self.create_PToken(token,self.operator_map,trace=trace)
        else:
        # None of the above - treat a normal factor
            po=self.create_PToken(token,self.factor_map,trace=trace)

        gs.exp.ptokens.append(po)

    def term_more_token(self,gs,pid,n,token):
        trace=gs.dm.isdebug("cbtrace")
        if trace:
            cls_str="expression.py - %s.term_more_token() -" % self.__class__.__name__
            print("%s token.tid='%s'" % (cls_str,token.tid))
        po=self.create_PToken(token,self.operator_map,trace=trace)
        gs.exp.ptokens.append(po)

if __name__ == "__main__":
    raise NotImplementedError("expression.py - intended for import use only")
