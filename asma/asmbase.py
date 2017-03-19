#!/usr/bin/python3.3
# Copyright (C) 2015-2017 Harold Grovesteen
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

# This module provides base classes used in multiple places within ASMA

this_module="asmbase.py"

# Python imports: None
# SATK imports:
import fsmparser         # Access Finite-State-Machine-based parsing technology
import lexer             # Access some objects
import pratt3            # Identify pratt literals
# ASMA imports:
import assembler
import asmtokens
import lnkbase


# This class supports expressions as lexical tokens, pratt token creation and
# evaluation.
class ASMExpr(object):
    def __init__(self,tokens):
        assert isinstance(tokens,list),\
            "'tokens' argument must be a list: %s" % tokens

        self.tokens=tokens       # Lexical token list comprising the expression

        # Pratt expression for evaluation (see prepare_arith or prepare_binary)
        self.pratt=None
        # Set to the pratt token when a quick evaluation can be performed.
        self.quick=False

    # Returns the number of lexical token in the list of lexical tokens
    def __len__(self):
        return len(self.tokens)

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__,self.tokens)

    def display(self,indent="",string=False):
        s=""
        lindent="%s    " % indent
        for t in self.tokens:
            if isinstance(t,ASMOperand):
                s="%s%s" % (s,t.display(indent=indent,string=True))
            else:
                s='%s, "%s"' % (s,t.string)
        if s[0:2]==", ":
            s=s[2:]
        if string:
            return s
        print(s)

    def evaluate(self,external,debug=False,trace=False):
        assert self.pratt is not None,"%s pratt attribute is None" \
            % assembler.eloc(self,"evaluate",module=this_module)

        # Quick execution if the expression is a single pratt Token.  No need to
        # invoke the parser with its context generation, etc.
        if self.quick:
            return self.quick.value(external,debug=debug,trace=trace)
        # Use the Pratt parser to evaluate the expression
        return self.pratt.evaluate(external,debug=debug,trace=trace)

    # Finds the first tid in an expression list.  Used mainly for address expressions
    # that need to find the first tid.  The user must know the TID.
    def find_first_ltok(self,tid=[]):
        if not isinstance(tid,list):
            # Scan tokens for the requested TID
            for tok in self.tokens:
                if tok.tid == tid:
                    return tok
        else:
            # Scan tokens for a TID in the requested list
            for tok in self.tokens:
                if tok.tid in tid:
                    return tok
        return None  # Not found

    def find_first_ptok(self,lineno,cls=[],debug=False):
        assert self.pratt is not None,"%s [%s] pratt attribute is None" \
            % (assembler.eloc(self,"find_first_ptok",module=this_module),lineno)
        assert len(self.pratt.toks)>0,"%s [%s] pratt.toks length: zero" \
            % (assembler.eloc(self,"find_first_ptok",module=this_module),lineno)

        if not isinstance(cls,list):
            for ptok in self.pratt.toks:
                if __debug__:
                    if debug:
                        print("%s [%s] ptok: %s" \
                            % (assembler.eloc(self,"find_first_ptok",\
                                module=this_module),lineno,ptok.__class__.__name__))
                        print("%s [%s] class: %s" \
                                % (assembler.eloc(self,"find_first_ptok",\
                                    module=this_module),lineno,cls))
                if isinstance(ptok,cls):
                    return ptok
        else:
            for ptok in self.pratt.toks:
                if __debug__:
                    if debug:
                        print("%s [%s] ptok: %s" \
                            % (assembler.eloc(self,"find_first_ptok",\
                                module=this_module),lineno,ptok.__class__.__name__))
                for c in cls:
                    if __debug__:
                        if debug:
                            print("%s [%s] class: %s" \
                                % (assembler.eloc(self,"find_first_ptok",\
                                    module=this_module),lineno,c))
                    if isinstance(ptok,c):
                        return ptok
        return None  # Not found

    def prepare(self,stmt,desc,debug=False):
        raise NotImplementedError("%s subclass %s must supply prepare() method" \
            % (assembler.eloc(self,"prepare",module=this_module),\
                self.__class__.__name__))


class ASMExprArith(ASMExpr):
    def __init__(self,tokens):
        super().__init__(tokens)

        # Whether the expression references the current location counter.  See
        # the prepare() method.
        self.loc_ctr=False

    def evaluate(self,external,debug=False,trace=False):
        assert self.pratt is not None,"%s pratt attribute is None" \
            % assembler.eloc(self,"evaluate",module=this_module)

        # Quick execution if the expression is a single pratt Token.  No need to
        # invoke the parser with its overhead, context generation, etc.
        if self.quick:
            val=self.quick.value(external,debug=debug,trace=trace)
            if isinstance(val,lnkbase.SectAddr) and val.isRelative():
                # Quick expressions avoid invoking the Pratt expression processing
                # by returning the single Pratt token itself.  When the value
                # of the token is a section relative address the same object
                # may end up being made absolute more than once.  When that happens
                # an uncaught exception is raised during post pass 1 processing.
                # This can occur with an EQU when the first operand is a single
                # label referencing a section relative address.
                # By placing the fix here (rather than elsewhere) it addresses the
                # problem with EQU and any other potential place with the same
                # issue.
                return val.clone()
            return val
            #return self.quick.value(external,debug=debug,trace=trace)
        # Use the Pratt parser to evaluate the expression
        return self.pratt.evaluate(external,debug=debug,trace=trace)

    # Preparse the expression for execution by converting lexical tokens into
    # a list of Pratt tokens within a Pratt arithmetic expression object.
    # Method Arguments:
    #   stmt   The statement in which the expression is used.
    #   desc   A description of the expression for debugging purposes.
    def prepare(self,stmt,desc,debug=False):
        assert self.pratt is None,\
            "%s pratt attribute not None: %s" \
                % (assembler.eloc(self,"prepare",module=this_module),self.pratt)

        # Create an empty Pratt arithmetic expression
        pexpr=asmtokens.ArithExpr(desc,stmt.lineno,tokens=[])
        if __debug__:
            if debug:
                print("%s: %s expr before: %s" % (desc,lineno,expr))

        # Now popultate it with pratt tokens from lexical tokens usign their
        # atoken() method.
        for ltok in self.tokens:
            if isinstance(ltok,CTerm):
                # Note currently CTerm is only used by macro directives so it is
                # not sensitive to location counter usage.
                ltok.prepare(stmt,desc)
            ptok=ltok.atoken()
            pexpr.token(ptok)

        if __debug__:
            if debug:
                print("%s: %s expr after: %s" % (desc,lineno,expr))

        self.pratt=pexpr
        self.quick=pexpr.quick()


class ASMExprBinary(ASMExpr):
    def __init__(self,tokens):
        super().__init__(tokens)

    def evaluate(self,external,debug=False,trace=False):
        assert self.pratt is not None,"%s pratt attribute is None" \
            % assembler.eloc(self,"evaluate",module=this_module)

        # Quick execution if the expression is a single pratt Token.  No need to
        # invoke the parser with its context generation, etc.
        if self.quick:
            return self.quick.value(external,debug=debug,trace=trace)
        # Use the Pratt parser to evaluate the expression
        return self.pratt.evaluate(external,debug=debug,trace=trace)

    def prepare(self,stmt,desc,debug=False):
        assert self.pratt is None,\
            "%s pratt attribute not None: %s" \
                % (assembler.eloc(self,"prepare",module=this_module),
                    self.pratt)

        # Create an empty Pratt binary expression
        pexpr=asmtokens.BinaryExpr(desc,stmt.lineno,tokens=[])
        if __debug__:
            if debug:
                print("%s: %s expr before: %s" % (desc,lineno,expr))

        # Now popultate it with pratt tokens from lexical tokens usign their
        # btoken() method.
        for ltok in self.tokens:
            if isinstance(ltok,CTerm):
                ltok.prepare(stmt,desc)
            pexpr.token(ltok.btoken())

        if __debug__:
            if debug:
                print("%s: %s expr after: %s" % (desc,lineno,expr))

        self.pratt=pexpr
        self.quick=pexpr.quick()


class ASMExprChar(ASMExpr):
    def __init__(self,tokens,string=False):
        super().__init__(tokens)
        self.string=string

    def evaluate(self,external,debug=False,trace=False):
        res=super().evaluate(external,debug=debug,trace=trace)
        if __debug__:
            if trace:
                print('%s returning: "%s"' \
                    % (assembler.eloc(self,"evaluate",module=this_module),res))

        return res

    def prepare(self,stmt,desc,debug=False):
        assert self.pratt is None,\
            "%s pratt attribute not None: %s" \
                % (assembler.eloc(self,"prepare",module=this_module),
                    self.pratt)

        # Create an empty Pratt binary expression.  Only binary expressions
        # will ever evaluate character expression tokens, so we will use it here.
        # Although technically either binary or arithmetic should work because
        # this object will only ever have one pratt token and should use the
        # quick execution path.
        pexpr=asmtokens.CharacterExpr(desc,stmt.lineno,tokens=[],string=self.string)
        if __debug__:
            if debug:
                print("%s: %s expr before: %s" % (desc,lineno,expr))

        # Now popultate it with pratt tokens from lexical tokens usign their
        # atoken() method.
        for ltok in self.tokens:
            if __debug__:
                if debug:
                    print("%s [%s] '%s' ltok: %s" \
                        % (assembler.eloc(self,"prepare",module=this_module),\
                            stmt.lineno,desc,ltok))

            if isinstance(ltok,CTerm):
                ltok.prepare(stmt,desc)
            ptok=ltok.ctoken()
            if __debug__:
                if debug:
                    print("%s [%s] '%s' ptok: %s" \
                        % (assembler.eloc(self,"prepare",module=this_module),\
                            stmt.lineno,desc,ptok))
            assert isinstance(ptok,(pratt3.PLit,asmtokens.PLitCTerm)),\
                "%s unexpected pratt token: %s" \
                    % (assembler.eloc(self,"prepare",module=this_module),ptok)
            pexpr.token(ptok)

        if __debug__:
            if debug:
                print("%s: %s expr after: %s" % (desc,lineno,expr))

        self.pratt=pexpr
        self.quick=pexpr.quick()


# This allows an arithmetic expression to be evaluated multiple times,  Used for
# retry evaluations during assembly.
class ASMExprRetry(ASMExprArith):
    def __init__(self,tokens):
        super().__init__(tokens)

        self.result=None   # Result from previously successful evaluation

    def evaluate(self,external,debug=False,trace=False):
        if self.result:
            return self.result
        self.result=super().evaluate(external,debug=False,trace=trace)
        return self.result


# This class encapsulates the results of a parsed operand
# Its content are tokenized expressions (ASMExpr objects).
# This is also the base class for all parser complex term result objects.
#
# Instance Methods:
#   display    Creates a printable version of the operand
#   primary    Accepts the supplied object as the objects primary expression
#   result     Returns the primary expression as the result or the ASMOperand object
#              itself if secondary expressions are present.
#   secondary  Adds the supplied object to the list of secondary expressions.
class ASMOperand(object):
    def __init__(self):
        self._primary=None        # Primary portion of the operand (ASMExpr object)
        self._secondary=[]        # Optional secondary operands (ASMExpr objects)
        # At some point the self._expr list may eliminate this arbitrary separation.

        # Expressions are added as presented via the primary() and secondary()
        # methods or the expr() method
        self._expr=[]             # Expressions as a single list

        # Whether &SYSLIST is required (for macro statement result objects)
        self.syslist=False

    def __str__(self):
        string="%s Primary: %r\nSecondary:" % (self.__class__.__name__,self._primary)
        for n,sec in enumerate(self._secondary):
            string="%s\n    [%s] %r" % (string,n, sec)
        return string

    def display(self,indent="",string=False):
        s="%s %r" % (indent,self)
        lindent="%s    " % indent
        s="%s\n%sPrimary: %r" % (s,indent,self._primary)
        if isinstance(self._primary,ASMExpr):
            s="%s\n%s%s" % (s,lindent,\
                self._primary.display(indent=lindent,string=True))
        if self._secondary:
            s="%s\n%sSecondary:" % (s,indent)
            sindent="%s    " % lindent
            for n,sec in enumerate(self._secondary):
                if sec is None:
                    s=s="%s\n%s[%s] %s" % (s,lindent,n,sec)
                else:
                    s="%s\n%s[%s] %r" % (s,lindent,n,sec)
                    s="%s\n%s %s" % (s,lindent,sec.display(indent=indent,string=True))
        if string:
            return s
        print(s)

    # Add an arbitrary expression to the expression list ignoring the primary
    # and secondary concepts
    def expr(self,obj):
        if isinstance(obj,list):
            self._expr.extend(obj)
        else:
            self._expr.append(obj)

    # Return the number of primary expressions present
    def hasPrimary(self):
        if len(self._expr)>=1:
            return 1
        else:
            return 0

    # Return the number of secondary expressions present
    def hasSecondary(self):
        if len(self._expr)>=1:
            return len(self._expr)-1
        return 0

    # Return whether primary expression is being added
    def isPrimaryState(self):
        return len(self._expr)==0

    # Return whether secondary expression is being added
    def isSecondaryState(self):
        return len(self._expr)>=1

    # Override this for a different use of the primary expression
    def primary(self,obj):
        self._primary=obj
        assert len(self._expr)==0,\
            "%s can not add primary expression to expression list as first "\
                "expression, exressions in list: %s" \
                    % (assembler.eloc(self,"primary",module=this_module),\
                        len(self.expr))
        self._expr.append(obj)

    def result(self):
        #print(assembler.eloc(self,"result",module=this_module))
        if len(self._secondary)==0:
            return self._primary
        return self

    # Override this for a different use of a secondary expression
    def secondary(self,obj):
        assert len(self._expr)>=1,\
            "%s can not add secondary expressions to expression list because no "\
                "primary expression is present: expressions in list: %s" \
                    % (assembler.eloc(self,"secondary",module=this_module),\
                        len(self._expr))

        if isinstance(obj,list):
            self._secondary.extend(obj)
            self._expr.extend(obj)
        else:
            self._secondary.append(obj)
            self._expr.append(obj)


# This object defines the interface methods required of complex terms generated by
# a MacroScope subclass.  Within expressions they must expose the same methods
# as do lexical tokens.
#
# Instance Methods Mirroring a asmtokens.LexicalToken object:
#   atoken     Returns the arithmetic Pratt token for this object.  Defaults to
#              ptoken() method if not overriden by a subclass.
#   btoken     Returns the binary (logical) Pratt token for this object.  Defaults
#              to ptoken() method if not overriden by a subclass.
#   ctoken     Returns the character Pratt token for this object.  Defaults to
#              ptoken() method if not overriden by a subclass.
#   ptoken     Returns the default Pratt token for this object.
#   syntax     Sets operator syntax attibutes.  Subclasses should never override.
#
# Instance Methods Inherited from asmbase.ASMOperand:
#   display    Creates a printable version of the operand
#   primary    Accepts the supplied object as the objects primary expression
#   result     Returns the primary expression as the result or the ASMOperand object
#              itself if secondary expressions are present.
#   secondary  Adds the supplied object to the list of secondary expressions.
class CTerm(ASMOperand):
    def __init__(self):
        super().__init__()
        self.line=None    # Line number of the token's start in the original string
        self.linepos=0    # Position in line of token string start
        self.source=None  # Input source

        # Subclass must set these values if needed using its supplied syntax() method
        self.binary=False       # Whether token represents a binary operator
        self.unary=False        # Whether token represents a unary operator

    # Generates and returns a pratt3 module PToken object for arithmetic expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def atoken(self):
        return self.ptoken()

    # Generates and returns a pratt3 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def btoken(self):
        return self.ptoken()

    # Analyzes the recognized string and returns it as a native Python object.
    def convert(self):
        raise NotImplementedError("%s subclass %s must provide convert() method"\
            % (assembler.eloc(self,"convert",module=this_module),\
                self.__class__.__name__))

    # Generates and returns a pratt3 module PToken object for binary expressions.
    # By default, it returns the token generated by the ptoken() method.
    # A subclass must override this method to change this behavior.
    def ctoken(self):
        return self.ptoken()

    # This method generates a pratt3 module PToken object, specifically a
    # subclass of asmtokens.PLitCTerm.
    def ptoken(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s must provide ptoken() method" \
            % (assembler.eloc(self,"ptoken",module=this_module),\
                self.__class__.__name__))

    # This method sets the operator syntax attributes.  If actual values are
    # required, the subclass must override this method.  Complex terms are not
    # operators, so this method should never be overridden by a complex term subclass.
    def syntax(self):
        pass

    # This method updates the lexical token with statement specific position
    # information.
    #
    # The lexical analyzer is designed to recognize entire files.  However, ASMA
    # only uses it to recognize portions of a line.  So after accepting the token
    # ASMA must update the token with actual statement location as produced
    # by the assembler listing.

    # This updates the token position based upon a ASMPloc object.  Generally
    # the creator of the CTerm object should update locations in tokens _before_
    # being created.  But, if it makes sense to do it here, then this is a
    # place holder.
    def update_loc(self,line,loc):
        raise NotImplementedError("%s subclass %s must supply update_loc() method" \
            % (assembler.eloc(self,"update_loc",module=this_module),\
                self.__class__.__name__))


class ASMPLoc(object):
    def __init__(self,source=None,pndx=None):
        self.source=source  # Physical line asminput.Source object
        self.pndx=pndx      # Index within the physical line of this input location

    # Support augmented addition of physical index:  self+=n
    def __iadd__(self,other):
        self.pndx+=other
        return self

    # Return a printable version of this location
    def __str__(self):
        if self.source is None:
            return "[%s]" % (self.pndx+1)
        return "[%s-%s:%s]" % (self.source.fileno,self.source.lineno,self.pndx+1)

    # Create a copy of myself
    def clone(self):
        if self.source:
            src=self.source.clone()
        else:
            src=None
        return ASMPLoc(source=src,pndx=self.pndx)


class ASMString(object):
    def __init__(self,string,start=None,amp=False):
        assert isinstance(string,str),\
            "'string' argument must be a string: %s" % string
        assert isinstance(start,ASMPLoc) or start is None,\
            "'start' argument must be an ASMPloc object or None: %s" % start

        self.text=string            # Python string foundation of this object
        self.length=len(string)     # Length of self.string
        self.amp=amp                # Whether string contains an ampersand
        self.chr_exp=None           # Character expression for symbolic replacement

        # This list is used in converting an index within self.string into its
        # physical input location.  Used primarily for error reporting.  The first
        # entry in the list corresponds to the index 0, the starting location of
        # self.string.  Method ndx2loc() provides the location of the supplied index.
        #
        # Each entry in the list is a tuple:
        #  ( index-in-self.start, ASMPLoc-of-this-index)
        self.new_line=[]      # self.string index starting on a new physical line

        if start is not None:
            self.newloc(start,ndx=0)

    # Support augmented concatenation to string: self+=c
    def __iadd__(self,other):
        self.text+=other
        return self

    # Returns the length of the accumulated string
    def __len__(self):
        return len(self.text)

    def display(self,indent="",string=False):
        s='%sstring: "%s" length: %s indexes:' % (indent,self.text,self.length)
        for index,loc in self.new_line:
            s="%s %s:%s," % (s,index,loc)
        s=s[:-1]
        if string:
            return s
        print(s)

    def newloc(self,loc,ndx=None):
        assert isinstance(loc,ASMPLoc),\
            "'loc' argument must be an instance of ASMPLoc: %s" % start
        if ndx is None:
            n=len(self.text)
        else:
            n=ndx
        t=(n,loc.clone())
        self.new_line.append(t)

    # Convert an index of self.string into a physical input location.  The index may
    # be any valid value used in referencing a list entry.
    # Returns: an ASMPLoc object of the location.
    # Exceptions:
    #   ValueError: Supplied value outside of self.string
    def ndx2loc(self,ndx):
        assert len(self.new_line)>0,"no line location information available"

        length=len(self.text)
        if ndx<0:
            n=length+ndx
        else:
            n=ndx
        if n>=length or n<0:
            raise ValueError("invalid index for string of length %s: %s" \
                % (length,ndx))

        for t in range(len(self.new_line)-1,-1,-1):
            index,loc=self.new_line[t]
            if n<index:
                continue

        return ASMPLoc(source=loc.source,pndx=loc.pndx+n-index)

    # Recognizes symbolic replacement and performs it if needed
    # Returns:
    #   Original text string of following symbolic replacement
    def replace(self,amp):
        if not self.amp:
            # If an ampersand is not present, no replacement so return original
            return self.text
        # Ampersand is present so need to parse the string for symbolic variables


    # Returns the starting location of the string
    def start(self):
        first=self.new_line[0]
        return first[1]  # Return just the ASMPLoc part of the tuple

#
#  +----------------------------------+
#  |                                  |
#  |   OPERATION MANAGEMENT CLASSES   |
#  |                                  |
#  +----------------------------------+
#

class ASMOper(object):
    def __init__(self,oper,stmtcls,O="U",info=None):
        #assert stmtcls is not None,\
        #    "%s 'stmtcls' argument must not be None" \
        #        % (assembler.eloc(self,"__init__",module=this_module))
        self.oper=oper        # Operation name
        self.stmtcls=stmtcls  # ASMStmt subclass used to process operation
        # Object with optional operation informattion (for example instruction data,
        # or a macro definition)
        self.info=info
        # O' attribute values:
        #    A - Assembler operation
        #    E - Extended mnemonic
        #    M - Macro definition
        #    O - Machine instruction
        #    S - Macro definition found in library
        #    U - Undefined, unknown, unassigned or deleted
        self.O=O

    def __str__(self):
        return "Operation '%s' O':%s stmtcls:%s info:%s" \
            % (self.oper,self.O,self.stmtcls,self.info)

class ASMOperTable(object):
    def __init__(self):
        self.table={}         # Dictionary of ASMOper object keyed to ASMOper.oper

    def __str__(self):
        return "%s" % self.table

    # Retireve an operation from the table
    # Returns:
    #   The operation's ASMOper object
    # Exceptions:
    #   KeyError raised if operation key not found
    def __getitem__(self,key):
        return self.table[key]

    # Registers an operation with a key other than that of the operation
    def __setitem__(self,key,oper):
        assert isinstance(key,str) and len(key)>0,\
            "'key' argument must be a not empty string: %s" % key
        assert isinstance(oper,ASMOper),\
            "'oper' argument must be an instance of ASMOper: %s" % oper

        self.table[key]=oper

    # Emulate the dictionary get() method.
    def get(self,key,default=None):
        return self.table.get(key,default)

    # Registers a new operation with the table.  The operation must not already
    # be present in the table.
    def register(self,oper):
        assert isinstance(oper,ASMOper),\
            "'oper' argument must be an instance of ASMOper: %s" % oper
        try:
            self.table[oper.oper]
            raise ValueError("duplicate operation being registered: %s" % oper.oper)
        except KeyError:
            self[oper.oper]=oper


#
#  +---------------------------+
#  |                           |
#  |   SHARED PARSER CLASSES   |
#  |                           |
#  +---------------------------+
#

# This class forms the base class for all SINGLE context finite-state machine based
# syntactical analyzers.  It enforces the structure used by each parser and provides
# some standard functions.
class AsmFSMParser(fsmparser.FSMParser):
    def __init__(self,dm,pm,scope=None,init="init",external=None,trace=False):
        self.dm=dm              # Debug manager, passed to lexical analyzer
        self.pm=pm              # Parser manager
        self.lex=self.Lexer("lexer")   # Create my lexical analyzer
        super().__init__(self.lex,scls=scope,external=external,init=init,trace=trace)
        self.initialize()       # Initialize the finite-state machine
        #self._scope_stack=[]    # Scope stack for pushing/popping scope

    # This method uses the super class state() method to register defined states
    def initialize(self):
        raise NotImplementedError("%s subclass %s must provide initialize() method" \
            % (assembler.eloc(self,"initialize",module=this_module),\
                self.__class__.__name__))

    # This method allows a scope to be supplied rather than generating one.
    def parse(self,string,scope=None,fail=False):
        return super().parse(string,scope=scope,fail=fail)

    def ACT_Expected(self,expected,value,found=None):
        self.stop()    # Terminate the lexer because we are bailing.
        msg="expected %s, found " % expected
        if found is None:
            if isinstance(value,asmtokens.EoOperToken):
                msg="%s%s" % (msg,"end of operands")
            elif isinstance(value,lexer.EOS):
                msg="%s%s" % (msg,"end of statement")
            else:
                msg='%s"%s"' % (msg,value.string)
        else:
            msg="%s%s" % (msg,found)
        raise assembler.AsmParserError(value,msg=msg)

    # This method returns the default lexical analyzer used by all macro statements.
    # Override this method to utilize a different lexical analyzer.
    def Lexer(self,lexer):
        return self.pm.lexers[lexer]


class AsmFSMState(fsmparser.PState):
    def __init__(self,state,pfx="",exit=None):
        self.pfx=pfx
        super().__init__(self.next_state(state))
        self.exit=exit
    def next_state(self,state):
        return "%s_%s" % (self.pfx,state)


# Base class for AsmFSMParser scopes supporting expressions and compound strings.
# Other parsers may continue to utilize fsmparser.PScope.  It has special handling
# for elements encountered in assembly parsing, specifically, expressions and
# strings with dual single quotes that must be converted to a single quote.
#
# Instance Methods:
#   ck_parens   Validates balanced parenthesis are present
#   flush       Discard all pending lexical tokens
#   init        Initializes the scope for use.
#   expr        Returns the lexical token list of the expression
#   expr_end    Returns the lexical token list after token update has occurred.
#   lparen      Add a left parenthesis lexical token to the pending list and track it
#   pending     Returns the number of lexical tokens pending for release
#   rparen      Add a right parenthesis lexical token to the pending list and track it
#   str_beg     Start a string represented by the asmtokens.StringToken() objects.
#   str_cont    Add more characters to the pending asmtokens.StringToken() object
#   str_end     Return the asmtokens.StringToken of the entire string.
#   str_pending Return whether a string is pending (True) or not (False).
#   token       Add a token to the pending expression
#   update_loc  Update a lexical token with is physical source (ASMPLoc object)
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

    # This method flushes current pending expression tokens.  Useful if the tokens
    # or token does not participate in expression evaluation here.  The caller has
    # appropriately dispatched the pending tokens.
    def flush(self):
        self._lextoks=[]      # Discard the pending lexical tokens
        self._parens=0        # Reset the number of encountered parenthesis to 0

    # Initializes the scope for use.  Automatically called by super class
    def init(self,stmt=None,case=False):
        self._stmt=stmt       # Statement being parsed
        self._case=case       # Whether symbol/label case sensitivity in use
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
    def expr_end(self,source=None,line=None):
        assert source is None or isinstance(source,ASMString),\
            "%s 'source' argument must be an instance of ASMString: %s" \
                % (assembler.eloc(self,"expr_end",module=this_module),source)
        #print("%s %s" % (assembler.eloc(self,"expr_end",module=this_module),self))
        self._parens=0
        expr=self._lextoks
        if source:
            for tok in expr:
                #print("%s: tok: %s" \
                #    % (assembler.eloc(self,"expr_end",module=this_module),tok))
                loc=source.ndx2loc(tok.linepos)
                tok.update_loc(line,loc)
        self._lextoks=[]
        return expr

    # Process a left parenthesis in an expression.  Adds the parenthesis to the
    # expression lexical token list and increments the parenthesis count
    def lparen(self,value):
        self._parens+=1
        self.token(value)

    # Returns the number of lexical tokens (or equivalent) pending in the
    # accumulated expression.
    def pending(self):
        return len(self._lextoks)

    # Process a right parenthesis in an expression.  Add the parenthesis to the
    # expression lexical token list and decrements the parenthesis count
    def rparen(self,value):
        self._parens-=1
        self.token(value)

    # Start accumulation of a compound string.
    def str_begin(self,value):
        assert isinstance(value,asmtokens.StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_begin",module=this_module),value)
        assert self._string is None,\
            "%s '_string' attribute is not None when starting a compound string: %s" \
                % (assembler.eloc(self,"str_begin",module=this_module),\
                    self._string)

        self._string=value

    # Adds additional string content to the compound string
    def str_cont(self,value):
        assert isinstance(value,asmtokens.StringToken),\
            "%s 'value' argument must be a StringToken object: %s"\
                % (assembler.eloc(self,"str_cont",module=this_module),value)
        assert isinstance(self._string,asmtokens.StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_cont",module=this_module),self.string)

        self._string.extend(value)

    # Returns the StringToken object of the accumulated string.
    def str_end(self):
        if self._string is None:
            return
        assert isinstance(self._string,asmtokens.StringToken),\
            "%s '_string' attribute must be a StringToken object: %s" \
                % (assembler.eloc(self,"str_end",module=this_module),self._string)

        accum=self._string
        self._string=None
        return accum

    # Returns whether a string is pending (True) or not (False)
    def str_pending(self):
        return self._string is not None

    # Adds a lexical token to the expression token list
    def token(self,tok):
        self._lextoks.append(tok)

    # Updates a lexical token to reflect its position in the Stmt object's source
    # statement.
    #def update(self,stmt,token):
    #    lineno=stmt.lineno
    #    source=stmt.source
    #    operpos=stmt.fields.operpos
    #    token.update(lineno,operpos,source)

    # Updates an individual token with its position information
    def update_loc(self,source,line,token):
        loc=source.ndx2loc(token.linepos)
        token.update_loc(line,loc)


# Context specifc scope base class
class AsmCtxScope(AsmFSMScope):
    def __init__(self):
        super().__init__()

        # The statements operation field in upper case.
        self.stmt_inst=None  # See the statement() method
        self.stmt_lineno=None  # The statemetn's assemly line number

    def statement(self,stmt):
        #assert isinstance(stmt,assembler.Stmt),\
        #    "%s 'stmt' argument must be an assembler.Stmt object: %s" \
        #        % (assembler.eloc(self,"statement",module=this_module),stmt)

        self.stmt_inst=stmt.instu   # The statement in upper case
        self.stmt_lineno=stmt.lineno  # The statement's line number


# This is an adaptation of AsmFSMParser for the use of context sensitive parsers.
# Context sensitive parsers can during a parsing activity change both the state,
# scope and lexical analyzer for the following tokens.
#
# Instance Arguments:
#   dm        The debug manager object in use
#   pm        The parser manager (parsers.Parsers object)
#   lex       The name of the lexical analyzer as known by parsers.ParserMgr object.
#   scope     The global scope class used by the parser.  Defaults to
#   init      The initial FSM parser state.  Defaults to 'init'
#   context   The initial context.  Defaults to 'init'
#   external  External helper object supplied to the parser.  Defaults to None
#   trace     Specify True to enable tracing of the finite state machine.
#             Defaults to False (no tracing)
class AsmCtxParser(fsmparser.FSMContext):
    def __init__(self,dm,pm,lex,scope=AsmFSMScope,init="init",context="init",\
                 external=None,trace=False):
        self.pm=pm
        lexer=self.Lexer(lex)

        super().__init__(lexer,scls=scope,external=external,\
                         init=init,context=context,trace=trace)

        self.init_ctx=context # Initial context when starting a parse
        self.init_context()   # Initialize the parser contexts
        self.initialize()     # Initialize the finite-state machine

    # This overrides the semantics of the super class fmsparser.FSMParser
    # _init_scope() method by reversing the priority.  It returns:
    #    1. the provided scope in the scope argument
    # or 2. A new object initialized by the super class
    def _init_scope(self,scope=None):
        if scope is not None:
            return scope
        return super()._init_scope(scope)

    # This override changes the default context scope class to asmtokens.AsmFSMScope
    # rather than the more generic fsmparser.PScope
    def ctx(self,name,lexctx=None,gbl=False,ccls=AsmCtxScope):
        super().ctx(name,lexctx=lexctx,gbl=gbl,ccls=ccls)

    # This method uses the super class ctx() method to register defined contexts.
    def init_context(self):
        cls_str=assembler.eloc(self,"init_context",module=this_module)
        raise NotImplementedError("%s subclass %s must provide init_context() method" \
            % (cls_str,self.__class__.__name__))

    # This method uses the super class state() method to register defined states
    def initialize(self):
        cls_str=assembler.eloc(self,"initialize",module=this_module)
        raise NotImplementedError("%s subclass %s must provide initialize() method" \
            % (cls_str,self.__class__.__name__))

    def ACT_Expected(self,expected,value,found=None):
        msg="expected %s, found " % expected
        if found is None:
            if isinstance(value,asmtokens.EoOperToken):
                msg="%s%s" % (msg,"end of operands")
            elif isinstance(value,lexer.EOS):
                msg="%s%s" % (msg,"end of statement")
            else:
                msg='%s"%s"' % (msg,value.string)
        else:
            msg="%s%s" % (msg,found)
        raise assembler.AsmParserError(value,msg=msg)

    def Lexer(self,name):
        return self.pm.lexers[name]


#
#  +--------------------------------------------+
#  |                                            |
#  |   MACHINE INSTRUCTION OPERAND PROCESSING   |
#  |                                            |
#  +--------------------------------------------+
#

# This class is the base class for managing an instruction's or assembler directive's
# operands.  Each operand in the source input is convered into a subclass of Operand.
class Operand(object):
    def __init__(self,name):
        self.name=name       # An operand name.
        #For MSLDB Format the source sfield (without a number) is the name.

        # These attributes hold the state of the validation results, good or bad
        self.source=0b000    # From validate_source() method
        self.exprs=[]        # From validate_source() method
        self.fields=0x000    # From validate_expr() method (valid and invalid)

        # Evaluated expressions.  Only an Address or int object is returned by
        # expression evalution.  Attribute is set by the evaluate() method
        self.values=[None,None,None]

        # Address for listing set by resolve() method
        self.laddr=None

    def __str__(self):
        return '%s("%s",exprs: %s,repr=%s)' \
            % (self.__class__.__name__,self.name,self.exprs,repr(self))

    def evaluate(self,asm,debug=False,trace=False):
        cls_str="assembler.py - %s.evaluate() -" % self.__class__.__name__
        values=[]
        if trace:
            print("%s %s.exprs: %s" % (cls_str,self,self.exprs))
        for n,exp in enumerate(self.exprs):
            #print("exp: %s" % exp)
            if exp is None:
                values.append(None)
                continue

            if __debug__:
                if debug:
                    print("%s exp: %s" \
                        % (assembler.eloc(self,"evaluate",module=this_module),exp))

            v=exp.evaluate(asm,debug=debug,trace=trace)
            #print("v: %s" % v)
            values.append(v)
        if len(values)==3:
            self.values=values
        else:
            raise ValueError("%s %s expression values not three: %s" \
                % (cls_str, self, values))

    # This method is used by the instruction builder to extract a machine field's
    # value based upon its type.
    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() subclass must supply field() method" \
            % cls_str)

    # This method is used by assembler directives to retrieve the results of
    # evaluating the operand.
    def getValue(self):
        cls_str="assembler.py - %s.getValue() -" % self.__class__.__name__
        raise NotImplementedError("%s getValue() method not supported by this operand" \
            % cls_str)

    def resolve(self):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported by this operand" \
            % cls_str)

    # Returns a string for reporting a failure to pass validate_source() method
    def source_error(self):
        cls_str="asmparsers.py - %s.source_error() -" % self.__class__.__name__
        raise NotImplementedError("%s source_error() method not supported by this "
            "operand" % cls_str)

    # Validates the types resulting from the expression evaluation.
    # Return:
    #   True   if type is valid for each expression
    #   False  if any of the expressions evaluates to an unexpected result
    def validate_expr(self,trace=False):
        if __debug__:
            if trace:
                cls_str="assembler.py - %s.validate_expr() -" \
                    % self.__class__.__name__
                print("%s values: %s" % (cls_str,self.values))
        state=0
        opr=0xF00
        shift=0
        for val in self.values:
            if trace:
                print("%s value: %s" % (cls_str,val))
            if val is None:
                typ=0x000
            elif isinstance(val,int):
                typ=0x100
            elif isinstance(val,lnkbase.Address):
                typ=0x200
            else:
                typ=0x300
            typ_shifted=typ>>shift
            if __debug__:
                if trace:
                    print("%s typ: %s" % (cls_str,hex(typ_shifted)))
            state|=(typ>>shift)
            if __debug__:
                if trace:
                    print("%s state: %s" % (cls_str,hex(state)))
            shift+=4
        self.fields=state
        valid=self.__class__.valid_expr
        if __debug__:
            if trace:
                print("%s valid_expr: %s" % (cls_str,valid))
        return state in valid

    # Returns a string for reporting a failure to pass validate_expr() method
    def value_error(self):
        cls_str="assembler.py - %s.value_error() -" % self.__class__.__name__
        raise NotImplementedError("%s value_error() method not supported by this "
            "operand" % cls_str)

# This class supports a single statement operand that must evaluate to an integer
# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                          self.values list
#   fields     Source statement syntax             [0]    [1]    [2]
#
#   0x100 -  integer-expression                   [int,   None, None]
class Single(Operand):
    valid_expr=[0x100,]
    valid_source=[0b100,]        # int -> register or mask or immediate
    omitted=[0,None,None]

    def __init__(self,name):
        super().__init__(name)
        self.immediate=None

    # Return operand values for 'I', 'M', 'R' or 'V' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ in ["I","M","R","RI","V"]:
            return self.immediate
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Returns this single operand's value.  Used by assembler directives
    def getValue(self):
        return self.values[0]

    # This is used by machine instructions to finalize immediate/masks/regs
    def resolve(self,asm,line,opn,trace=False):
        self.immediate=self.values[0]

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must not be an address (error=%s): %s" \
            % (hex(self.fields),self.values[0])

# This class supports a single statement operand that must evaluate to an address
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]
#   0x200 -  DSECT-Address-expression             [isDummy(),    None, None]
class SingleAddress(Operand):
    valid_expr=[0x200,]
    valid_source=[0b100,]        # Address -> directive address
    omitted=[0,None,None]
    def __init__(self,name):
        super().__init__(name)

    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() method not supported for directive "
            "only operand" % cls_str)

    # Returns this single operand's value.
    def getValue(self):
        return self.values[0]

    def resolve(self,asm,stmt,opn,trace=False):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported for directive "
            "only operand" % cls_str)

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must be an address (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x100 -  integer-expression                   [int,          None, None]
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]
#   0x200 -  DSECT-Address-expression             [isDummy(),    None, None]
class SingleAny(Operand):
    valid_expr=[0x100,0x200,]
    valid_source=[0b100,]    # Address or integer       -> directive operand
    omitted=[0,None,None]
    def __init__(self,name):
        super().__init__(name)

    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() method not supported for directive "
            "only operand" % cls_str)

    # Returns this single operand's value.
    def getValue(self):
        return self.values[0]

    def resolve(self,asm,stmt,opn,trace=False):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported for directive "
            "only operand" % cls_str)

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "unexpected value (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that must evaluate to an address
# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]
class SingleRelImed(Operand):
    valid_expr=[0x200,]
    valid_source=[0b100,]
    omitted=[0,None,None]
    def __init__(self,name):
        super().__init__(name)
        self.relimed=None
        self.isladdr=True

    # Return operand value for 'RI' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ == "RELI":
            return self.relimed
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Returns this single operand's target destination
    def getValue(self):
        cls_str="assembler.py - %s.getValue() -" % self.__class__.__name__
        raise NotImplementedError("%s getValue method not supported for instruction "
            "only operand" % cls_str)

    # Resolve instruction field values in preparation for instruction construction
    def resolve(self,asm,stmt,opn,trace=False):
        dest=self.values[0]
        if not dest.isAbsolute:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s (%s) encountered unexpected %s as relative "
                    "target: %s" % (opn,self.name,dest.description(),dest))
        self.laddr=dest        # Save for listing
        binary=stmt.content
        relative=dest-binary.loc
        relative_abs=max(relative,-relative)
        halfwords,excess=divmod(relative_abs,2)
        if excess:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s (%s) encountered unexpected odd value as relative "
                    "target: %s" % (opn,self.name,relative))

        self.relimed=relative//2

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must be an address (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that takes the form of a simple
# storage reference.  It supports the following constructs:
#
#    self.                                              self.values list     Base
#   fields     Source statement syntax             [0]       [1]   [2]
#
#   0x100 -  disp                                 [int1,       None, None]     0
#   0x110 -  disp(base)                           [int1,       int2, None]    int2
#   0x200 -  region-address                       [isAbsolute, None, None]   implied
#   0x200 -  DSECT-Address                        [isDummy,    None, None]   implied
#   0x210 -  region-address(base)                 [isAbsolue,  int,  None]     int
#   0x210 -  DSECT-Address(base)                  [isDummy,    int,  None]     int
#
# Note: 0x210 is equivalent to 0x200 with expicit USING statement.  Is this useful?
#
# Preparing this operand for presentation to the machinery that builds machine
# instructions requires the following actions:
#
#    Operand.evaluate()    - Builds self.values list from self.operands,
#    Storage.resolve()     - establishes all values explicit or implied
class Storage(Operand):
    valid_expr=[0x100,0x110,0x200,0x210]
    valid_source=[0b100,     # Address/int, None, None  ->  UA/Disp (UA=base implied)
                  0b110]     # Address/int, int, None   ->  UA/Disp,base
    omitted=[0,0,None]

    # Displacement size.  Used for both Storage and StorageExt
    disp_size={"S":12,"SY":20,"SL":12,"SR":12,"SX":12,"SYL":20,"SYX":20}
    def __init__(self,name):
        super().__init__(name)
        self.size=Storage.disp_size[self.name]   # Set the displacement field size
        self.base=None       # This is the base register that resolves for address
        self.disp=None       # This is the displacement that resolves for address

    def ck_base_disp(self,base,disp,stmt,opn):
        if not isinstance(base,int):
            #if isinstance(base,Address):
            if isinstance(base,lnkbase.Address):
                raise assembler.AssemblerError(line=stmt.lineno,\
                   msg="operand %s base register must not be an address: %s" \
                    % (opn+1,base))
            else:
                raise ValueError("%s [%s] operand %s base register did not resolve"
                    "to an integer: %s" % (eloc(self,"ck_base_disp"),\
                        stmt.lineno,opn+1,base))
        if not isinstance(disp,int):
            if isinstance(disp,lnkbase.Address):
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s displacement must not be an address: %s" \
                        % (opn+1,disp))
            else:
                raise ValueError("%s [%s] operand %s displacement did not resolve "
                    "to an integer: %s" % (eloc(self,"resolve"),\
                        stmt.lineno,opn+1,disp))

    # Return operand values for 'B' or 'D' type machine fields
    # Results depend upon the resolve() having completed its work.
    def field(self,typ):
        if typ == "B":                  # Used by source type: S and SY
            return self.base
        if typ == "D":                  # Used by source type: S
            return self.disp
        if typ == "DH":                 # Used by source type: SY
            return self.disp // 4096
        if typ == "DL":                 # Used by source type: SY
            return self.disp %  4096

        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Resolves explicit/implicit values for operand 'opn' in statement number 'line'
    def resolve(self,asm,stmt,opn,trace=False):
        if self.fields==0x100:
            self.base=0
            self.laddr=self.disp=self.values[0]
        elif self.fields==0x110:
            self.base=self.values[1]
            self.laddr=self.disp=self.values[0]
        elif self.fields==0x200:
            # Note, if this fails, an AssemblerError exception is raised.
            dest=self.values[0]
            self.laddr=dest.lval()
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
        elif self.fields==0x210:
            disp=self.values[0]
            if disp.isDummy():
                # Use the DSECT relative address as displacement
                self.disp=disp.lval()
            elif disp.isAbsolute():
                # Use absolute address as displacement
                self.disp=disp.address
            else:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s (%s) encountered unexpected displacement: %s" \
                        % (opn,self.name,disp.description()))

            self.base=self.values[1]
            self.laddr=self.disp=disp
        else:
            raise ValueError("%s unexpected self.fields: 0x%03X" \
                % (eloc(self,"resolve"),self.fields))

        # Make sure we are good to go before leaving
        self.ck_base_disp(self.base,self.disp,stmt,opn)

    def source_error(self):
        return "unexpected index register (error=%s)" % self.source

    def value_error(self):
        return "explicit base register must be an integer (error=%s)" \
            % (hex(self.fields),self.values[2])

# This class supports a single statement operand that takes the form of a full
# storage reference.  It supports the following constructs:
#
#    self.                                self.values list       Instruction Usage
#   fields   Source statement syntax   [0]           [1]   [2]  Index/Length    Base
#
#   0x100 -  disp                      [int,        None, None]   0     1        0
#   0x101 -  disp(,base)               [int1,       None, int2]   0     1       int2
#   0x110 -  disp(ndx/len)             [int1,       int2, None]   0    int2       0
#   0x111 -  disp(ndx/len,base)        [int1,       int2, int3]  int2  int2     int3
#   0x200 -  CSECT-Addr                [isAbsolute, None, None]   0  implied   implied
#   0x200 -  DSECT-Addr                [isDummy,    None, None]   0  implied   implied
#   0x210 -  CSECT-Addr(ndx/len)       [isAbsolute, int,  None]  int   int     implied
#   0x210 -  DSECT-Addr(ndx/len)       [isDummy,    int,  None]  int   int     implied
#   0x211 -  DSECT-Addr(ndx/len,base)  [isDummy,    int1, int2]  int1  int1     int2
#
# Base register for an absolute address is implied from the current absolute USING
# registers assignments.
#
# Base register for DSECT displacements is implied from the current relative USING
# asignments.
#
# Lengths are implied from the expression's root symbol's length.  The expression's
# root symbol is the one to which an integer value is added or subtracted.
class StorageExt(Storage):
    valid_expr=[0x100,0x101,0x110,0x111,0x200,0x210,0x211]
    valid_source=[0b100,     # Address/int, None, None  -> UA/Disp  (UA==base implied)
                  0b110,     # Address/int, int, None   -> UA/Disp,index
                  0b101,     # int, None, int           -> Disp,base
                  0b111]     # int, int, int            -> Disp,index,base
    disp_size={"SL":12,"SX":12,"SYL":20,"SYX":20}
    isIndex=["SX","SYX"]
    omitted=[0,0,0]

    def __init__(self,name):
        super().__init__(name)
        # Indicates whether field is an index register (True) or length (False)
        self.isIndex=(name in StorageExt.isIndex)

        self.index=None
        self.length=None
        # self.base, self.disp and self.size and self.isladdr are inherited from
        # Storage superclass.

    def __setNdxLen(self,value):
        if self.isIndex:
            self.index=value
        else:
            self.length=value

    # Return operand values for 'B', 'D', 'DH', 'DL', 'R','X' or 'L' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ == "B":
            return self.base
        elif typ == "D":
            return self.disp   # caller has to sort out DH vs. DL values
        elif typ == "DH":
            return self.disp // 4096
        elif typ == "DL":
            return self.disp %  4096
        elif typ == "R":
            return self.length
        elif self.isIndex and typ in ["X","V"]:
            return self.index
        else:
            if typ == "L":
                return max(0,self.length-1)

        raise ValueError("%s upsupported machine type requested: %s index=%s" \
            % (assembler.eloc(self,"field"),typ,self.isIndex))

    def resolve(self,asm,stmt,opn,trace=False):
        if __debug__:
            if trace:
                print("%s [%s] operand %s self.fields: %3X" \
                     % (assembler.eloc(self,"resolve",module=this_module),stmt.lineno,\
                         opn,self.fields))
        if self.fields==0x100:
            self.base=0
            self.laddr=self.disp=self.values[0]
            if self.isIndex:
                self.index=0
            else:
                self.length=1
        elif self.fields==0x101:
            self.base=self.values[2]
            self.laddr=self.disp=self.values[0]
            if self.isIndex:
                self.index=0
            else:
                self.length=1
        elif self.fields==0x110:
            self.base=0
            self.laddr=self.disp=self.values[0]
            self.__setNdxLen(self.values[1])
        elif self.fields==0x111:
            self.base=self.values[2]
            self.laddr=self.disp=self.values[0]
            self.__setNdxLen(self.values[1])
        elif self.fields==0x200:
            # Note, if this fails, an AssemblerError exception is raised.
            self.laddr=dest=self.values[0]
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
            if self.isIndex:
                self.index=0
            else:
                self.length=self.values[0].length
        elif self.fields==0x210:
            self.laddr=dest=self.values[0]
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
            self.laddr=dest.address
            self.__setNdxLen(self.values[1])
        elif self.fields==0x211:
            self.base=self.values[2]
            disp=self.values[0]
            if isinstance(disp,lnkbase.Address) and not disp.isDummy():
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s displacement must not be an address: %s" \
                        % (opn+1,disp))
            if disp.isDummy():
                # Use the DSECT relative address as displcement
                self.disp=disp.lval()
            elif isinstance(disp,int):
                self.disp=disp
                self.laddr=disp
            else:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s (%s) encountered unexpected %s as "
                        "displacement: %s" % (opn,self.name,disp.description()))
            self.laddr=self.disp
            self.__setNdxLen(self.values[1])
        else:
            raise ValueError("%s unexpected self.fields: 0x%03X" \
                % (assembler.eloc(self,"resolve"),self.fields))

        # Make sure we are good to go before leaving
        self.ck_base_disp(self.base,self.disp,stmt,opn)

        if self.isIndex:
            if not isinstance(self.index,int):
                if isinstance(self.index,lnkbase.Address):
                    raise assembler.AssemblerError(line=stmt.lineno,\
                        msg="operand %s index must not be an address: %s" \
                            % (opn+1,self.index))
                raise ValueError("%s [%s] operand %s index register not an integer: "
                    "%s" % (cls_str,stmt.lineno,opn,self.index))
        else:
            if not isinstance(self.length,int):
                if isinstance(self.length,lnkbase.Address):
                    raise assembler.AssemblerError(line=stmt.lineno,\
                        msg="operand %s length must not be an address: %s" \
                            % (opn+1,self.length))
                raise ValueError("%s [%s] operand %s length length not an integer: "
                    "%s" % (cls_str,stmt.lineno,opn,self.length))

    def source_error(self):
        if self.fields & 0x0F0 == 0x020:
            return "explicit index register must be an integer (error=%s): %s" \
                % (hex(self.fields),self.values[1])
        if self.fields & 0x00F == 0x002:
            return "explicit base register must be an integer (error=%s): %s" \
                % (hex(self.fields),self.values[2])

        raise ValueError("%s unexpected expression value (error=%s): %s" \
            % (eloc(self,"source_error"),hex(self.fields),self.values))


#
#  +------------------------------+
#  |                              |
#  |   Process Driver Framework   |
#  |                              |
#  +------------------------------+
#

# This object is the basis for statement handling within source code and
# macro library accesses.  Each uses a different approach.  This object ensures
# that an access to phase numbers are adjusted even with changes to the phase
# sequencing as along as other objects use the phase name as an object attribute.
# Conceptually phase names are assigned a number similar to an enumeration in C.
# At the same time a execution method is associated with the phase.
class ASMProcessor(object):
    def __init__(self,asm):
        self.asm=asm       # The global Assembler object
        # Supported phase names as attributes and method list.  List sequence
        # control execution sequence.  Each element of the list is a tuple:
        # ( phase_name, bound_method)
        self.phases=[]        # Bound method for corresponding phase
        self.phase=None       # Current processing phase number
        self.cur_phase=None   # Current processing phase name
        self.init()           # Subclass defines phases

        # Supplied during phase processing returned by the process() method
        self.result=None

    # Utility method for defining a phase.  Each phase is called in sequence.
    # Each phase is assigned a number based upon the sequence in which it is
    # defined.  The name is used as an attribute of this object to access the number.
    # Method Arguments:
    #   name    The name of a phase as a string.  Defines an object attribute of
    #           its name equal to the number assigned to the phase.  Objects
    #           requiring access to phase numbers must use these attributes to
    #           ensure consistent number usage even when phases are added or deleted.
    #
    #           Phase names may not confict with other attributes a the time of
    #           definition.  This includes method names of the subclass.
    #   method  The bound method of the subclass that processes this phase.
    #           Use self.method not Class.method.  Phase methods are defined with
    #           this argyment signature:
    #               method(asm,fail=False)
    #           where:
    #               asm is the global Assembler object and
    #               fail is True if the command-line --error 0 has been supplied.
    def defPhase(self,name,method):
        n=len(self.phases)
        try:
            atr=getattr(self,name)
            raise ValueError("%s phase name %s is already defined: %s" \
                % (assembler.eloc(self,"defPhase"),name,atr))
        except AttributeError:
            setattr(self,name,n)
            t=(name,method)
            self.phases.append(t)

    # Subclass initializer.  Phases should be defined here by the subclass
    def init(self):
        raise NotImplementedError("%s subclass %s must provide init() method" \
            % (assembler.eloc(self,"init",module=this_module),\
                self.__class__.__name__))

    # Drive one or more processes.  Called by the subclass to drive its processing
    def process(self):
        for n,phaset in enumerate(self.phases):
            self.phase=n                       # Set the current phase number
            self.cur_phase,phase=phaset        # Set the name of the current phase
            self.result=phase(self.asm,fail=self.asm.fail)  # Execute it!
        return self.result

    # The subclass must provide this method, called by the user of the processor,
    # for subclass specific run initialization.  This method will call self.process()
    # to drive its processing
    def run(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s must provide run() method" \
            % (assembler.eloc(self,"init",module=this_module),\
                self.__class__.__name__))


#
#  +-------------------------------+
#  |                               |
#  |   SYMBOL TABLE BASE CLASSES   |
#  |                               |
#  +-------------------------------+
#

# This class manages attribute values for a single label or symbolic variable
# Attributes may be applied as follows in open code:
#                                    ASMA Supported         ASMA specific
#   open code label              T, L,        D,  O,  S,  I
#   open code sections/regions   T, L,        D,      S,  I        M
#   literals in macro operands   T, L,        D,      S,  I
#   global system variables      T,    K, N
#
# Attributes may be applied as follows in macro definitions
#   ordinary symbols             T, L,        D,  O,  S,  I
#   literals in macro operands   T, L,        D,      S,  I
#   symbolic parameters          T, L*, K, N  D*, O*, S*, I*,      M*
#   &SYSLIST                     T, L*, K, N  D*, O*, S*, I*,      M*
#   other system variables       T,     K, N
#
# * If SETC symbol or macro parameter is assigned a valid label as its value
#
# Label attributes in open code:   I L M S T
# Label attributes in macros:    D I L M S T
# SET attributes:     K   N
# SETC as label:  D I   L   M S T
#
# Various locations within ASMA modules actually assign the attributes
# These comments document where they are set:
#  T' Attributes
#     A  asmdcds.DC_A  asmdcds.AD
#     B  asmdcds.DC_B
#     C  asmdcds.DC_C  asmdcds.CA  asmdcds.CE
#     D  asmdcds.DC_D  asmdcds.DC_DD
#     E  asmdcds.DC_ED
#     F  asmdcds.DC_F
#     H  asmdcds.DC_H
#     I  asmstmts.MachineStmt.Pass1()
#     J  assembler.Assembler._csect_new()
#     K  asmdcds.DC_DD  asmdcds.DC_ED  asmdcds.DC_LD
#     L  asmdcds.DC_LD
#     N  macsyms.A_Val.__init__()
#        macsyms.B_Val.__init__()
#        macopnd.PSymRefCAttr_T.value()
#     O  macsyms.Parm_Val.__init__()
#     P  asmdcds.DC_P
#     R  asmdcds.DC_A  asmdcds.DC_AD  asmdcds.DC_S  asmdcds.DC_Y
#     S  asmdcds.DC_S
#     W  asmstmts.CCW0.Pass1()  asmstmts.CCW1.Pass1()
#     X  asmdcds.DC_X
#     Y  asmdcds.DC_Y
#     Z  asmdcds.DC_Z
#     1* assembler.Assembler._image_new()
#     2* assembler.Assembler._region_new()
#     3* asmstmts.PSWS.Pass1()   asmstmts.PSW360.Pass1()
#        asmstmts.PSW67.Pass1()  asmstmts.PSWBC.Pass1()
#        asmstmts.PSWEC.Pass1()  asmstmts.PSWBi.Pass1()
#        asmstmts.PSWZ.Pass1()
#     4* assembler.Assembler._dsect_new()
# * ASMA specific attributes
class ASMSymAttr(object):
    # Defaults attributes values (used by __getitem__() method):
    dfts={"D":0,"I":0,"K":0,"L":1,"M":0,"N":0,"O":"U","S":1,"T":"U"}

    # Defined attributes (used by __setitem__() method):
    #      ATTR    value     valid
    #     LETTER   class     values
    attrs={"D":   (int,      [0,1]),       # Label definition status
           "I":   (int,      None),        # Label integer attribute
           "K":   (int,      None),        # Count of SET symbol characters
           "L":   (int,      None),        # Label Length
           "M":   (int,      None),        # ASMA specific
           "N":   (int,      None),        # Number of SET symbol entries
           "O":   (str,      "AEMOSU"),    # Operation type
           "S":   (int,      None),        # Constant Scale
           "T":   (str,      "ABCDEFGHKLPQRSVXYZ@IJMTW$ONU1234")}   # Label Type
    def __init__(self):
        self.attr={}   # Assigned attributes

    # Return an attribute's value
    def __getitem__(self,key):
        try:
            return self.attr.get(key,ASMSymAttr.dfts[key])
        except KeyError:
            raise ValueError("unrecognized attribute: %s" % key)

    # Set a symbol's attribute
    def __setitem__(self,key,value):
        try:
            cls,valid=ASMSymAttr.attrs[key]
        except KeyError:
            raise ValueError("unrecognized attribute: %s" % key)

        # Make sure the value is of the proper type
        assert isinstance(value,cls),\
            "attribute '%s' requires value of class %s found: %s (%s)" \
                % (key,cls.__name__,value,value.__class__.__name__)
        # Make sure the value is valid for the attribute
        if valid and value not in valid:
            raise ValueError("invalid value for attribute %s': %s" % (key,value))

        # Now make the assignment
        self.attr[key]=value

    def __str__(self):
        s=""
        for a in "DIKLMNOST":
            v=self[a]
            s="%s %s:%s" % (s,a,v)
        return s[1:]

# These two class provides generic Symbol Table support
# Attributes are normally accessed using the item fetch self[attr] or
# set self[attr]=v syntax.  Use the update method to set multiple attributes as
# keyword arguments.
# Instance Arguments:
#   name   The name of the symbol as a string
#   value  An object or integer that constitutes the value of the symbol
#   length If supplied, sets the symbol's length attribute to this value.
#          Otherwise, the length attribute must be specified explicitly following
#          object creation.  Default value is if not previously set 1.
#   T      Sets the entry's T' (type) attribute
#   S      Sets the entry's S' (scale) attribute
#   I      Sets the entry's I' (integer) attribute
class ASMSymEntry(object):
    def __init__(self,name,value,length=None,T="U",S=0,I=0):
        assert isinstance(name,str) and len(name)>=1,\
            "'name' argument must be a non-empty string: '%s'" % name
        #print("%s name:%s value:%s length:%s T:%s S:%s I:%s"\
        #    % (assembler.eloc(self,"__init__",module=this_module),\
        #        name,value,length,T,S,I))

        self.name=name                # Symbol name
        self.attrs=ASMSymAttr()       # Symbol attributes
        self._value=value             # Value of defined symbol
        # Set the type, scale and integer attributes
        self["T"]=T
        self["S"]=S
        self["I"]=I
        # Set the legnth attribute if supplied
        if length is not None:
            self["L"]=length

    def __str__(self):
        return "SymEntry: %s %s" % (self.name,self.attrs)

    # Retrieves symbol attribute values
    def __getitem__(self,key):
        assert isinstance(key,str) and len(key)==1,\
           "'key' arguement must be a string of one character: '%s'" % key

        return self.attrs[key]

    # Sets symbol attributes
    def __setitem__(self,key,value):
        assert isinstance(key,str) and len(key)==1,\
           "'key' argument must be a string of one character: '%s'" % key

        self.attrs[key]=value

    # Update attributes.  Each updated attribute is an undefined keyword argument
    # accessed bia the **attrs dictionary, for exmaple update(I=5,T="A")
    def update(self,**attrs):
        for atr,value in attrs.items():
            self.attrs[atr]=value

    # This method returns the entries value attribute
    def value(self):
        return self._value


# Creates symbol table object
# Instance Arguments:
#   cls   Identifies the class required of symbol table entries.  Must be a subclass
#         of ASMSymEntry
#   attrs A string of the supported attributes of entries in the table
#   wo    Whether the symbol table restricts symbols from having a new entry
#         object from being assigned the symbol (wo=True) or not (wo=False)
#         Defaults to False.
#   case  Whether case insensitivity is enabled
class ASMSymTable(object):
    def __init__(self,cls,attrs,wo=False,case=False):
        assert issubclass(cls,ASMSymEntry),\
            "'cls' argument must be a subclass of ASMSymEntry: %s" % cls
        assert isinstance(attrs,str),\
            "'attrs' argument must a string: %s" % attrs

        self.cls=cls        # Required class of symbols defined by this table
        self.attrs=attrs    # Supported symbol entry attributes
        self.tbl={}         # Symbol table dictionary
        self.wo=wo          # Whether symbol table is 'write-once'
        self.case=case      # Whether smbols names are case insensitive

    # Retrieve a symbol entry definition by its name using index syntax: table[name]
    # Exceptions:
    #   KeyError  if symbol is not defined
    # Raises KeyError if item not in table
    def __getitem__(self,symbol):
        return self.tbl[symbol]

    # Set the value of a symbol in the table using index syntax:
    #    table[name]=object
    # 'object' must be an instance of class identified when the table was created.
    # Raises KeyError if write_once=True and the symbol name already exists
    def __setitem__(self,key,item):
        assert isinstance(key,str),\
            "'key' argument must be a string: %s" % key
        assert isinstance(item,self.cls),\
            "'item' argument must an instance of %s: %s" % (self.cls.__name__,item)

        # Detect redefinition of a symbol in a 'write-once' table.
        if self.wo:
            val=None
            try:
                val=self.tbl[key]
                raise KeyError()
            except KeyError:
                pass

        self.tbl[key]=item

    # Add a new lang.STE entry.  The 'line' argument is the defining statement number
    # AssemblerError is raised if symbol already exists in the table
    def add(self,entry,line):
        if not self.case:
            entry.name=entry.name.upper()
        try:
            self[entry.name]
            raise assembler.AssemblerError(line=line,\
                msg="region, section or symbol already defined: '%s'" % entry.name)
        except KeyError:
            self[entry.name]=entry

        # Set where the entry was defined.
        entry._defined=line

    # Returns the attribute of a symbol defined by the table
    def attr(self,symbol,attr):
        if attr not in self.attrs:
            raise ValueError("attribute invalid for symbol %s: %s" % (symbol,attr))

        try:
            sym=self[symbol]
        except KeyError:
            # Symbol is undefined so return the attributes default
            return ASMSymAttr.dfts[attr]

        # Symbol is defined so return its attribute value (or possibly default)
        return sym[attr]

    # Return an iterator of entries, a tuple (label,ASMSymEntry)
    def entries(self):
        return self.tbl.items()

    # Fetch a symbol by name.  Returns an instance of lang.STE.
    # Raises KeyError if symbol is not defined
    def get(self,item):
        if not self.case:
            return self[item.upper()]
        return self[item]

    # Returns a list of all symbol names.  If sort=True is specified the returned
    # list will be sorted.
    def getList(self,sort=False):
        labels=list(self.labels())
        if sort:
            labels.sort()
        return labels

    # Return an interator of symbol labels
    def labels(self):
        return self.tbl.keys()

    # Return an interator of ASMSymEntry objects
    def symbols(self):
        return self.tbl.values()


#
#  +---------------------------------+
#  |                                 |
#  |   Assembler Symbol Table Entry  |
#  |                                 |
#  +---------------------------------+
#

# This object is used by both the assembler symbol table and literal pools.
class LabelSymbol(ASMSymEntry):
    def __init__(self,name,entry,length=None,T="U",S=0,I=0):
        super().__init__(name,entry,length=length,T=T,S=S,I=I)
        # Assembler XREF information
        self._defined=None       # source statement number defining the symbol
        self._refs=[]            # source statements referencing this symbol

        # Define attributes:
        if length is None:
            self["L"]=len(entry)
        else:
            self["L"]=length

    # Returns the underlying value that participates in computations
    def compute(self):
        obj=self._value
        if isinstance(obj,int):
            return obj
        if isinstance(obj,lnkbase.Address):
            # Instruction generation needs this for implied lengths
            obj.length=self["L"]
            return obj
        elif isinstance(obj,(Section,Region,Img)):
            addr=obj.loc
            addr.length=self["L"]  # Do we need this here???
            return addr

        raise ValueError("%s unexpected symbol table object '%s': %s" \
            % (eloc(self,"compute"),self.symbol,obj))

    # Add a reference to the symbol
    def reference(self,line):
        assert isinstance(line,int),\
            "%s 'line' argument must be an integer" % eloc(self,"reference")

        if not line in self._refs:
            self._refs.append(line)


#
#  +-----------------------------+
#  |                             |
#  |   CROSS-REFERENCE MANAGER   |
#  |                             |
#  +-----------------------------+
#

# The assembler manages many cross-reference contexts.  This object is used for
# managing this information.  It has the ability to support an attribute character
# with the line number.  Some cross-reference listings require that.
class XREF(object):

    # Returns the comparison value for sorting cross-reference items.
    @staticmethod
    def sort_key(item):
        return item.line

    # Create cross-reference database
    def __init__(self):
        self.refs=[]      # Cross-reference item objects

    # Enter a definition entry.  Flag defaults to an asterisk, '*'.
    def define(self,line,flag="*"):
        self.refs.append(xref(line,flag=flag))

    # Enter a reference entry.  Flag defaults to a space, ' '.
    def ref(self,line,flag=" "):
        self.refs.append(xref(line,flag=flag))

    # Returns a sorted list of cross-reference entries.  Sort is based upon the
    # line number of the entry.
    def sort(self):
        return sorted(self.refs,key=XREF.sort_key)


# Individual cross-reference entry.  The flag defaults to a space.
class xref(object):
    def __init__(self,line,flag=" "):
        self.line=line
        self.flag=flag


if __name__ == "__main__":
    raise NotImplementedError("%s - this module only supports import usage" \
        % this_module)
