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

# This module provides support for SATK core program management functions.  These
# include address management and object module creation.  Both ASMA and SALINK
# utuilize these objects.

this_module="%s.py" % __name__

# SATK imports:
import assembler     # Access the global assember module
import objlib        # Access object moodule read/write library


# This function returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
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
#  +---------------------+
#  |                     |
#  |   Address Objects   |
#  |                     | 
#  +---------------------+
#

# Two forms of address are supported by the objects in this module:
#   - relative, and
#   - absolute.
#
# Relative addresses are always relative to a specific origin.  Internally this
# origin is always zero.  Each type of origin has its own subclass.
#
# Absolute addresses are based upon an assignment of an address to the origin and
# utilizes the sum of the relative location and the origin's address when converting
# a relative address into an absolute address.
#
# Use of these classes within an expressions is directly supported.
#
# Concepts such as a symbol, length or relocation are outside the scope of these
# objects.  These additional concepts are represented by other classes in other
# modules.

# The Address class represents all addresses created during the assembly, both
# relative and absolute.  During the assembly pass 1, Binary content has an address
# assigned to it using an Address object.  If the content has an accompanying label
# in the symbol table, the actual Address object is used to provide the symbol's
# value.  During the address binding process, the address is converted from a
# relative address into an absolute addres.  Because the very same object is used in
# the symbol table, the change in the content address is automatically seen in the 
# symbol table.
# 
# The Address class and its subclasses are designed to pariticipate in Python
# arithmetic operations using overloading methods.  This allows them to paricipate
# directly in expression evaluation as would a standard Python integer.

# This exception is raised when problems arise during address arithemtic.  It
# should be caught and an AssemblerError with relevant context information should 
# then be raised.
class AddrArithError(Exception):
    def __init__(self,msg=None):
        self.msg=msg
        super().__init__(msg)

# This exception is raised when two positions participate in an arithemetic
# operation but are allocated under different Allocation objects.
class PosArithError(Exception):
    def __init__(self,msg=None):
        self.msg=msg
        super().__init__(msg)


# This is the base class for all Address Types
class Address(object):
    @staticmethod
    def extract(addr):
        if addr is None:
            return None
        if isinstance(addr,int):
            return addr
        return addr.lval()

    def __init__(self,typ,rel,section,address,length=1):
        if __debug__:
            cls_str=eloc(self,"__init__")
            assert isinstance(typ,int),\
                "%s 'typ' argument must be an integer: %s" % (cls_str,typ)
            assert typ>=1 and typ<=4,\
                "%s 'typ' argument invalid (1-4): %s" % (cls_str,typ)
            assert isinstance(length,int),\
                "%s 'length' argument must be an integer: %s" \
                     % (cls_str,length)

            if typ==1:
                # Dummy section displacement
                assert isinstance(section,assembler.Section) \
                   and section.isdummy(),\
                    "%s 'section' argument must be DSECT for typ %s: %s" \
                        % (cls_str,typ,section)
                assert address is None,\
                    "%s 'address' argument must be None for typ %s: %s" \
                        % (cls_str,type,address)

            elif typ==2:
                # Section relative address
                assert isinstance(section,assembler.Section) \
                   and not section.isdummy(),\
                    "%s 'section' argument must be CSECT for typ %s: %s" \
                        % (cls_str,typ,section)
                assert address is None,\
                    "%s 'address' argument must be None for typ %s: %s" \
                        % (cls_str,typ,address)

            elif typ==3:
                # Absolute Address
                assert isinstance(address,int), \
                    "%s 'address' argument must be integer for typ %s: %s" \
                        % (cls_str,typ,address)
                assert rel is None, \
                     "%s 'rel' argument must be None for typ %s: %s" \
                         % (cls_str,typ,rel)
                assert section is None, \
                     "%s 'section' argument must be None for typ %s: %s" \
                         % (cls_str,typ,section)

            elif typ==4:
                # External address
                assert isinstance(section,str),\
                    "%s 'section' argument must be a string for typ %s: %s" \
                        % (cls_str,typ,section)
                assert rel == 0,\
                    "%s 'rel' argument must be 0 for typ %s: %s" \
                        % (cls_str,typ,rel)
                assert address is None,\
                    "%s 'address' argument must be None for typ %s: %s" \
                        % (cls_str,typ,address)

            else:
                # This should never happen because of initial assertions, but...
                raise ValueError("%s 'unexpected address type: %s" % (cls_str,typ))

        self.typ=typ            # Set my type (1, 2, 4, or 3 - relative or absolute)
        # Position information of the address (constant after creation)
        self.section=section    # Section/external of this position
        # Address relative to the section/external
        self.value=rel          # May be either positive, negative or zero

        # Absolute address corresponding corresponding to relative address
        self.address=address    # May not be a negative value
        self.length=length      # This attibute is used for implied length values

    def __len__(self):
        return self.length

    def __repr__(self):
        string="%s(typ=%s,value=%s,address=%s,length=%s" \
            % (self.__class__.__name__,self.typ,self.value,self.address,self.length)
        string="%s\n    section=%s)" % (string,self.section)
        return string

    def __str__(self):
        if self.isRelative():
            return self._rel_str()
        elif self.isExternal():
            return self._ext_str()
        return self._abs_str()

    def _abs_str(self):
        return "ABS:0x%X" % self.address

    def _ck(self,v,a,op,b,rsup=False):
        if v>=0:
            return v
        if rsup:
            raise AddrArithError(msg="negative address not supported %s %s %s: %s" \
                % (b,op,a,v))
        raise AddrArithError(msg="negative address not supported %s %s %s: %s" \
            % (a,op,b,v))

    def _cmp(self,other,op):
        typo=self._type(other)
        if typo==0 or typo!=self.typ:    # Can only compare same address types
            self._no_sup(op,other)
        if typo==3:       # Both are absolute addresses
            return (self.address,other.address)
        # Both are either DSECT displacements or relative addresses, same rules
        if self.section!=other.section:
            self._no_sup(op,other)
        return (self.value,other.value)

    def _ext_str(self):
        return "EXT:%s+0x%X" % (self.section,self.value)

    def _no_sup(self,op,b):
        raise AddrArithError(msg="can't perform: %s %s %s" % (self,op,b))

    def _no_rsup(self,op,b):
        raise AddrArithError(msg="can't perform: %s %s %s" % (b,op,self)) 

    def _no_usup(self,op):
        raise AddrArithError(msg="can't perform: %s %s" % (op,self))

    def _rel_str(self):
        return "%s+0x%X" % (self.section.name,self.value)

    # Categorizes Address argument in calculations by type:
    #   0 == integer
    #   1 == dummy section displacement (treat like integer with other addresses)
    #   2 == relative address
    #   3 == absoulute address
    #   4 == external address
    #   5 == anything else
    def _type(self,other):
        if isinstance(other,int):
            return 0
        if isinstance(other,Address):
            return other.typ
        return 5

    # Unsupported infix operations
    def __div__(self,other):
        self._no_sup("/",other)
    def __floordiv__(self,other):
        self._no_sup("/",other)
    def __mul__(self,other):
        self._no_sup("*",other)
    def __radd__(self,other):
        return self.__add__(other,rsup=True)
    def __rdiv__(self,other):
        self._no_rsup("/",other)
    def __rfloordiv__(self,other):
        self._no_rsup("/",other)
    def __rmul__(self,other):
        self._no_rsup("*",other)
    def __rsub__(self,other):
        self._no_rsup("-",other)
        
    # Unsupported unary operations
    def __neg__(self):
        self._no_usup("-")

    # Comparison overloads for addresses
    def __lt__(self,other): 
        me,other=self._cmp(other,"<")
        return me<other
    def __le__(self,other):
        me,other=self._cmp(other,"<=")
        return me<=other
    def __eq__(self,other):
        me,other=self._cmp(other,"==")
        return me==other
    def __ne__(self,other):
        me,other=self._cmp(other,"!=")
        return me!=other
    def __gt__(self,other):
        me,other=self._cmp(other,">")
        return me>other
    def __ge__(self,other):
        me,other=self._cmp(other,">=")
        return me>=other
        
    # Unary + overload for addresses
    def __pos__(self):
        return self

    # Returns the intgeger value to be used in Base/Displacement calculation.
    def base(self):
        raise NotImplementedError("%s subclass must implement base() method" \
            % eloc(self,"base"))

    def clone(self):
        raise NotImplementedError("%s subclass must implement clone() method" \
            % eloc(self,"clone"))

    def description(self):
        raise NotImplementedError("%s subclass must implement description() method" \
            % eloc(self,"description"))

    def isAbsolute(self):
        raise NotImplementedError("%s subclass must implement isAbsolute() method" \
            % eloc(self,"isAbsolute"))

    def isDummy(self):
        raise NotImplementedError("%s subclass must implement isDummy() method" \
            % eloc(self,"iisDummy"))

    def isExternal(self):
        raise NotImplementedError("%s subclass must implement isExternal() method" \
            % eloc(self,"isExternal"))

    def isRelative(self):
        raise NotImplementedError("%s subclass must implement isRelative() method" \
            % eloc(self,"isRelative"))

    def lval(self):
        raise NotImplementedError("%s subclass must implement lval() method" \
            % eloc(self,"lval"))

    # Position I/F methods
    def addr_a(self,samode=True):
        raise NotImplementedError("%s subclass must implement addr_a() method" \
            % eloc(self,"addr_a"))

    def addr_i(self):
        raise NotImplementedError("%s subclass must implement addr_i() method" \
            % eloc(self,"addr_i"))

    def addr_o(self):
        raise NotImplementedError("%s subclass must implement addr_o() method" \
            % eloc(self,"addr_o"))

    def addr_sa(self):
        raise NotImplementedError("%s subclass must implement addr_sa() method" \
            % eloc(self,"addr_sa"))


class DDisp(Address):
    def __init__(self,rel,section,length=1):
        super().__init__(1,rel,section,None,length=length)

    def __add__(self,other,rsup=False):
        typo=self._type(other)    # The other objects type number
                       # I'm a Dummy displacement
        if typo==0:    #    Other is an integer
            new_rel=self._ck(\
               self.value+other,other,"+",self,rsup=rsup)
            return DDisp(new_rel,self.section,length=self.length)
        elif typo==1:  #    Other is a dummy displacement
            new_rel=self._ck(\
                self.value+other.value,self,"+",other,rsup=rsup)
            return DDisp(new_rel,self.section,length=self.length)
        elif typo==2:  #    Other is a relative address (treat me like int)
            #new_rel=self._ck(\
            #    self.value+other.value,self,"+",other,rsup=rsup)
            new_rel=self.value+other.value
            return SectAddr(new_rel,other.section,length=other.length)
        elif typo==3:  #    Other is an absolute address (treat me like int)
            new_addr=self._ck(\
                self.value+other.address,self,"+",other,rsup=rsup)
            return AbsAddr(address=new_addr,length=other.length)
        if rsup:
            self._no_rsup("+",other)
        self._no_sup("+",other)  

    def __sub__(self,other):
        typo=self._type(other)    # The other objects type number
                       # I'm a Dummy displacement
        if typo==0:    #    Other is an integer
            new_rel=self._ck(self.value-other,self,"-",other)
            return DDisp(new_rel,self.section)
        elif typo==1:  #    Other is a DSECT displacement
            if self.section!=other.section:
                self._no_sup("-",other)
            return self.value-other.value
        self._no_sup("-",other)

    def __str__(self):
        return self._rel_str()

    def base(self):
        return self.value

    def clone(self):
        return DDisp(self.value,self.section)

    def description(self):
        return "DSECT-relative address"

    def isAbsolute(self):
        return False

    def isDummy(self):
        return True

    def isExternal(self):
        return False

    def isRelative(self):
        return True

    def lval(self):
        return self.value
        
    # Position I/F methods only supported for addresses that have a presence
    # within object modules.  Should never be used with DDisp objects
    def addr_a(self,samode=True):
        raise NotImplementedError("%s subclass does not support addr_a() method" \
            % eloc(self,"addr_a"))

    def addr_i(self):
        raise NotImplementedError("%s subclass does not support addr_i() method" \
            % eloc(self,"addr_i"))

    def addr_o(self):
        raise NotImplementedError("%s subclass does not support addr_o() method" \
            % eloc(self,"addr_o"))

    def addr_sa(self):
        raise NotImplementedError("%s subclass does not support addr_sa() method" \
            % eloc(self,"addr_sa"))


class ExternalAddr(Address):
    def __init__(self,rel,section,length=1):
        super().__init__(rel=rel,section=section,typ=4,length=length)

    def __add__(self,other,rsup=False):
        typo=self._type(other)    # The other objects type number
                       # I'm an external address
        if typo==0:    #    other is an integer
            #new_addr=self._ck(\
            #    self.value+other,self,"+",other,rsup=rsup)
            new_addr=self.value+other
            return ExternalAddr(new_addr,self.section,length=self.length)
        if rsup:
            self.__no_rsup("+",other)
        self.__no_sup("+",other)

    def __sub__(self,other):
        typo=self._type(other)    # The other objects type number
                       # I'm an external address
        if typo==0:    #    other is an integer
            #new_addr=self._ck(\
            #    self.value+other,self,"-",other,rsup=rsup)
            new_addr=self.value+other
            return ExternalAddr(new_addr,self.section,length=self.length)
        self.__no_sup("-",other)

    def clone(self):
        return ExternalAddr(self.value,self.section,length=self.length)

    def description(self):
        return "external address"

    def isAbsolute(self):
        return False

    def isDummy(self):
        return False

    def isExternal(self):
        return True

    def isRelative(self):
        return False

    def isAbsolute(self):
        return True

    def lval(self):
        return self.value
        

class AbsAddr(Address):
    def __init__(self,address=None,rel=None,section=None,typ=3,length=1):
        super().__init__(typ,rel,section,address,length=length)

    def __add__(self,other,rsup=False):
        typo=self._type(other)    # The other objects type number
                       # I'm an absolute address
        if typo==0:    #    other is an integer
            new_addr=self._ck(\
                self.address+other,self,"+",other)
            return AbsAddr(new_addr,length=self.length)
        elif typo==1:  #    other is a DSECT displacement
            new_addr=self._ck(\
                self.address+other.value,self,"+",other)
            return AbsAddr(new_addr,length=self.length)
        if rsup:
            self.__no_rsup("+",other)
        self.__no_sup("+",other)

    def __sub__(self,other):
        typo=self._type(other)    # The other objects type number
                       # I'm an absolute address
        if typo==0:    #    Other is an integer
            new_addr=self._ck(self.address-other,self,"-",other)
            return AbsAddr(new_addr)
        elif typo==1:  #    Other is a DSECT displacement
            new_addr=self._ok(self.address-other.value,self,"-",other)
            return AbsAddr(new_addr)
        elif typo==3:  #    Other is an absolute address
            return self.address-other.address
        self.__no_sup("-",other)

    def base(self):
        return self.address

    def clone(self):
        return AbsAddr(self.address)

    def description(self):
        return "absolute address"

    def isAbsolute(self):
        return True

    def isDummy(self):
        return False

    def isExternal(self):
        return False

    def isRelative(self):
        return False

    def lval(self):
        return self.address
        
    # Position I/F methods only supported for addresses that have a presence
    # within object modules.  Should never be used with DDisp objects
    def addr_a(self,samode=True):
        if samode:
            return self.addr_sa()
        raise NotImplementedError(\
            "%s subclass does not support addr_a(samode=False) method" \
                 % eloc(self,"addr_a"))

    def addr_i(self):
        raise NotImplementedError("%s subclass does not support addr_i() method" \
            % eloc(self,"addr_i"))

    def addr_o(self):
        raise NotImplementedError("%s subclass does not support addr_o() method" \
            % eloc(self,"addr_o"))

    def addr_sa(self):
        return self.address


class SectAddr(AbsAddr):
    def __init__(self,rel,section,length=1):
        super().__init__(rel=rel,section=section,typ=2,length=length)

    def __add__(self,other,rsup=False):
        if self.typ==3:  # Use super class if I am an absolute address now
            return super().__add__(other)

        typo=self._type(other)    # The other objects type number
                         # I'm a CSECT Relative address
        if typo==0:      #   other is an integer
           new_rel=self.value+other
           return SectAddr(new_rel,self.section)
        if typo==1:      #   other is a DSECT displacement
           return SectAddr(self.value+other.value,self.section)

        if rsup:
            self._no_rsup("+",other)
        self._no_sup("+",other) 

    def __sub__(self,other,rsup=False):
        if self.typ==3:  # Use super class if I am an absolute address now
            return super().__sub__(other)

        typo=self._type(other)    # The other objects type number
                       # I'm a CSECT Relative address
        if typo==0:    #    Other is integer
            new_rel=self.value-other
            return SectAddr(new_rel,self.section)
        elif typo==2 or typo==1:   #    Other is a relative address (CSECT or DSECT)
            if self.section!=other.section:
                self._no_sup("-",other)
            return self.value-other.value
        self._no_sup("-",other) 

    def base(self):
        if self.isRelative():
            return self.value
        return self.address

    def clone(self):
        if self.isRelative():
            return SectAddr(self.value,self.section)
        return super().clone()

    def makeAbs(self):
        if self.typ!=2:
            raise ValueError("%s relative (%s) already absolute: %s" \
                % (eloc(self,"makeAbs"),self._rel_str(),self._abs_str()))

        section=self.section
        if section.isdummy():
            sec_addr=self.section.value()
            self.address=sec_addr+self.value
        else:
            sec_addr=self.section.value()
            if not sec_addr.isAbsolute():
                raise ValueError("%s section address is not absolute: %s" \
                    % (eloc(self,"makeAbs"),repr(sec_addr)))
            self.address=sec_addr.address+self.value
            self.typ=3

    def description(self):
        if self.typ==2:
            return "CSECT-relative address"
        return "absolute address"

    def isDummy(self):
        return False

    def isExternal(self):
        return False

    def isRelative(self):
        return self.typ==2

    def isAbsolute(self):
        return self.typ==3

    def lval(self):
        if self.isRelative():
            return self.value
        return self.address

    # Position I/F methods.
    def addr_a(self,samode=True):
        return self.section.addr_a(samode=samode)+self.value

    def addr_i(self):
        return self.section.addr_i()+self.value

    def addr_o(self):
        return self.section.addr_o()+self.value

    def addr_sa(self):
        return self.section.addr_sa()+self.value


#
#  +--------------------+
#  |                    |
#  |   Link Exception   |
#  |                    |
#  +--------------------+
#

class LNKError(Exception):
    def __init__(self,msg=""):
        self.msg=msg          # Text associated with the error
        super().__init__(msg)

#
#  +------------------------+
#  |                        |
#  |   Unnamed Link Items   |
#  |                        |
#  +------------------------+
#

# This object represents relocatable address within a section
class Relo(object):
    types=None
    
    # Need to work on this for linker (not used by assembler)
    @staticmethod
    def accept(pname,rname,rld):
        if __debug__:
            cls_str="%s - Relo.accept() -" % this_module
        assert isinstance(rld,objlib.RLDITEM),\
            "%s 'rlditem' argument must be an objlib.RLDITEM object: %s" \
                % (cls_str,rld)
        assert isinstance(pname,str),\
            "%s 'pname' argument must be a string: %s" % (cls_str,pname)
        assert isinstance(rname,str),\
            "%s 'rname' arguement must be a string: %s" % (cls_str,rname)

        try:
            cls=Relo.types[rlditem.typ]
        except KeyError:
            raise LNKError(msg="unrecognized objlib relocation item: %s" % rlditem)
            
        rld=cls.accept(pname,rname,rld)
        return rld
    
    def __init__(self,typ,size,pndx,rndx,radj,rname=None):
        assert isinstnace(typ,int) and typ>=0 and typ<=4,\
            "%s 'typ' argument must be an integer between 0 and 4: %s" \
                % (eloc(self,"__init__"),typ)
        assert isinstance(size,int) and size>0 and size<=8,\
            "%s 'size' argument must be an integer greater between 1 and 8: %s" \
                % (eloc(self,"__init__"),size)
        assert isisntance(pndx,int) and ndx>=0,\
            "%s 'pndx' argument must be a non-negative integer: %s" \
                % (eloc(self,"__init__"),pndx)
        assert rndx is None or (isisntance(rndx,int) and rndx>=0),\
            "%s 'rndx' argument must be a non-negative integer: %s" \
                % (eloc(self,"__init__"),rndx)
        assert isinstance(radj,int),\
            "%s 'radj' argument must be an integer: %s" \
                % (eloc(self,"__init__"),radj)
        assert rname is None or isinstance(rname,str),\
            "%s 'rname' argument must be a string or None: %s" \
                % (eloc(self,"__init__"),rname) 

        self.typ=typ          # Type of relocation being defined.
        self.length=size      # Length of the address constant being relocated
        # Position information
        self.pndx=ndx         # Index of address constant in its section
        self.pname=None       # Section of position assigned when added to section
        # Address constant content
        self.rndx=rndx        # Index in target, rname.  May be zero for externals
        self.rname=rname      # Symbol associated with address constant nominal value
        self.adjust=adjust    # Adjustment to address in the constant from address


# Locally defined address
# rname is the CSECT in which the address resides
# Assemles the address of the rname+rndx+radj into the address constant
class ARelo(Relo):
    typ=0

    def __init__(self,size,pndx,rndx,radj,rname=None):
        super().__init__(ARelo.typ,size,pndx,rndx,radj,rname=None)


# External address
# rname is the external named: CSECT or EXTRN
# Assembles the absolute value of the radj field into the address constant
class VRelo(Relo):
    typ=1
    def __init__(self,size,pndx,radj,rname):
        super().__init__(VRelo.typ,size,pndx,0,0,radj,rname=rname)


# External Dummy Section or DSECT
# rname is the name of the DXD or DSECT
# Assembles zero into the address constant
class QRelo(Relo):
    typ=2
    def __init__(self,size,pndx,rname):
        super().__init__(QRelo.typ,size,pndx,0,0,rname=rname)


# Cumulative Dummy Section length
# rname is the name of the dummy section
# Assembles zero into the address constant
class CXDRelo(Relo):
    typ=3
    def __init__(self,size,pndx,rname):
        super().__init__(CXDRelo.typ,size,pndx,None,0,rname=rname)


# Relative immediate item
# rname is the section name of the target relocation item
# Assembly is within the instruction using this relocation. No additional adjustment
# required.  The value is always based upon the separation of the instruction
# and the target.
class RIRelo(Relo):
    typ=4
    def __init__(self,size,pndx,rndx,rname=None):
        super().__init__(RIRelo.typ,size,pndx,rndx,0,rname=rname)

Relo.types={ARelo.typ:ARelo,VRelo.typ:VRelo,QRelo.typ:QRelo,\
            CXDRelo.typ:CXDRelo,RIRelo.typ:RIRelo}


#
#  +---------------------------+
#  |                           |
#  |    MODULE CORE CLASSES    |
#  |                           |
#  *---------------------------+
#

# These core objects are abstractions of the proceses involved in object module
# creation.  Object content must be placed within some contiguous area.  The
# positioning of data within the contiguous area is managed by the Allocation
# object.  It creates Postion objects that provide where content will be placed.
#
# The actual content is separate from the Allocation in which it will placed and
# its positioning.  The content is represented by a Text object.  The text object
# is anchored to the allocation via its assigned Position.  The Position is 
# anchored to the Allocation.
#
# These objects are completely free from the concepts of sections or addresses.
# They become linked when the foundation Allocation object becomes "bound" to
# a residence location.  Once the Allocation is bound all Position and Text objects
# can be associated with sections and addresses.

# This object manages allocation of binary content in a hierarchy of allocations.
class Allocation(object):
    def __init__(self,name,typ=None,start=None):
        assert isinstance(name,str),\
            "%s 'name' argument must be a string: %s" \
                % (eloc(self,"__init__"),name)
        assert start is None or (isinstance(start,int) and start>=0),\
            "%s 'start' argument must be an non-negative integer: %s" \
                % (eloc(self,"__init__"),start)

        # Starting position of this Allocation
        self.start=start     # Bound starting position of allocation

        # This allocations parameters
        self.name=name   # Identifying name of this allocation
        #self.typ=typ     # Type of allocation
        self._align=0    # Maximum required alignment of content in this allocation
        self._len=0      # Length of the expandable allocation
        self._cur=0      # Current position for next allocation (without alignment)

        # Allocation Hierarchy support:
        self.sub_allocs=[]    # Allocations within this allocation
        # In a hierarchy of allocations, the Allocation containing this Allocation
        self._cont=None
        # Position of this allocation in its container, when bound to its containing
        # allocation
        self._contpos=None

        # Different addresses are required based upon the context
        self.a_addr=None      # Assembler assigned Section relative address
        self.i_addr=None      # Starting image location of this object
        self.sa_addr=None     # Stand-alone absolute address

    def __len__(self):
        return self._len

    def __str__(self):
        return "%s Allocation %s pos:%s length:%s: max alignment:%s current:%s" \
            % (self.name,self._contpos,self._len,self._align,self._cur)

    # Align the current position to the requested alignment
    # Returns:
    #   Integer position following alignment
    def __align(self,align):
        if align<2:
            return self._cur
        cur=self._cur
        aligned=(cur+(align-1)//align)*align
        self._align=max(align,self._align)    # Track maximum alignment required
        needed=aligned-cur
        if needed>0:
            self.__alloc(needed)
        return aligned

    # Allocate a number of bytes from the current position.
    def __alloc(self,size):
        self._cur+=size
        self._len=max(self._cur,self._len)

    # Returns my assembler address based upon my position within my container
    def addr_a(self):
        if not self.a_addr:
            self.a_addr=self._contpos.addr_a()
        return self.a_addr

    # Returns my assembler address based upon my position within my container
    def addr_i(self):
        if not self.i_addr:
            self.i_addr=self._contpos.addr_i()
        return self.i_addr

    # Align the current position and return the aligned Position object
    # Returns:
    #   Position object of the aligned position within the allocation
    def align(self,align=1):
        assert isinstance(align,int),\
            "%s 'align' argument must be a non-negative integer: %s" \
                % (eloc(self,"alloc"),align)

        pos=self.__align(align)
        return Position(self,disp=pos)

    # Allocate with optional alignment an area of a given size.
    # Note: 
    #   alloc(0) is equivalent to start()
    #   alloc(0,align) is equivalent to align(align)
    # Method Arguments:
    #   size   Size of the requested area in bytes.
    #   align  Requested alignment.  Defaults to 1.  Zero is treated as 1
    # Returns:
    #   Position object of the aligned allocated area's starting position within the
    #   allowing
    def alloc(self,size,align=1):
        assert isinstance(size,int) and size>=0,\
            "%s 'size' argument must be a non-negative integer: %s" \
                % (eloc(self,"alloc"),size)

        pos=self.align(align=align)
        self.__alloc(size)
        return pos

    # March down the hierarchy and allocate each sub-allocation within its containing
    # allocation.  Leaf allocations have nothing to assign
    def assign(self):
        for cont in self.sub_allocs:
            cont.bind()
            cont.contpos=self.alloc(len(cont),align=cont._align)
       
    # From the top of the hierarchy assign fixed positions based upon their relative
    # positions.
    def bind(self):
        assert isinstance(self.start,int) and self.start>=0,\
            "%s %s can not bind sub allocations without a valid start location" \
                % (eloc(self,"bind"),self.start)
        for cont in self.sub_allocs:
            cont.start=cont._contpos+self.start
            cont.bind()    # Bind its allocations

    # Allocates, with optional alignment, an area of a given size.  Similar to
    # alloc() method but returns the position of the first and byte following the
    # allocated space.
    # Method Arguments:
    #   size   Size of the requested area in bytes.
    #   align  Requested alignment.  Defaults to 1.  Zero is treated as 1
    # Returns:
    #   a tuple ( Position start , Position end+1)
    def bounds(self,size,align=1):
        beg=self.alloc(size,align=align)
        return (beg,self.star())

    # Reset the allocation position based upon a supplied Position
    def org(self,pos):
        assert isinstance(pos,Position),\
            "%s 'pos' argument must be a Position object: %s" \
                % (eloc(self,"org"),pos)
        assert pos.cntr==self.cont,\
            "%s Position not within this allocation (%s: %s" \
                % (eloc(self,"org"),self.name,pos)
                
        self._cur=pos.disp

    # Return the current location within the allocation as a Position object
    def star(self):
        return Position(self,disp=self.cur)

    # Add an allocation to this containing allocation.  The links between the
    # allocations are made by this method.  Sub-allocations follow any allocations
    # made directly from this containing allocation.  Allocations that only contain
    # other allocations will have nothing allocated from them
    def sub_alloc(self,alloc):
        assert alloc is None or isinstance(alloc,Allocation),\
             "%s 'cont' argument must be an Allocation object: %s" \
                % (eloc(self,"__init__"),alloc)
        alloc._cont=self
        self.sub_allocs.append(alloc)


# This object is the base for all content positioned within an object module
class Position(object):
    def __init__(self,cntr,disp=0):
        assert isinstance(cntr,Allocation),\
            "%s 'cntr' argument must be an Allocation object: %s" \
                % (eloc(self,"__init__"),cntr)
        assert isinstance(disp,int) and disp>=0,\
            "%s 'disp' argument must be a non-negative integer: %s" \
                % (eloc(self,"__init__"),disp)
                
        # Container object information
        self.cntr=cntr        # Container object in which this is a member
        self.disp=disp        # This object's displacement index into its container

        # Different numeric addresses are required based upon the context
        self.i_addr=None      # Starting image location of this object
        self.a_addr=None      # Assembler assigned address (influenced by mode)
        self.sa_addr=None     # Stand-alone absolute address

    # These methods allow Positions within the same allocation to be used
    # arithmetically.  Integer right hand arguments are supported
    
    # Perform:  Position + int
    # Returns:
    #   a new Position object
    # Exceptions:
    #   AssertionError if the displacement is negative
    def __add__(self,other):
        if isinstance(other,int):
            "%s 'other' argument must be an integer: %s" \
                % (eloc(self,"__add__"),other)

        return Position(self.cntr,disp=self.disp+other)
        
    # Perform  int + Position
    # Returns:
    #   a new Position object
    def __radd__(self,other):
        return self.__add__(other)

    # Perform  Position - int
    # Returns:
    #   a new Position object
    # Exception:
    #   AssertionError if a negative displacement within an allocation resultes
    #
    # Perform  Position - Position
    # Returns:
    #   an integer
    # Exceptions:
    #   AssertionError if the Positions are from the same allocation
    def __sub__(self,other):
        if isinstance(other,Position):
            if self.cntr!=other.cntr:
                raise PosArithError(msg="can not substract positions in different "
                    "containers: %s-%s" % (self,other))

            return self.disp-other.disp

        assert isinstance(other,int),\
            "%s 'other' argument must be an integer: %s" \
                % (eloc(self,"__sub__"),other)

        return Position(self.cntr,disp=self.disp-other)

    # Return a descriptive string
    def __str__(self):
        return "%s@%s" % (self.cntr.name,self.disp)

    # Assembler address
    def addr_a(self,samode=True):
        # Assembler stand-alone mode returns an absolute address value
        if samode:
            return self.addr_sa()
        # Assembler link mode returns an address based upon the location counter
        if not self.a_addr:
            if self.cntr is None:
                raise ValueError("%s not assigned a container: %s" \
                    % (eloc(self,"addr_a"),self))  
            self.a_addr=self.cntr.addr_a()+self.disp
        return self.a_addr

    # Image location
    def addr_i(self):
        if not self.i_addr:
            if self.cntr is None:
                raise ValueError("%s not assigned a container: %s" \
                    % (eloc(self,"addr_i"),self))
            self.i_addr=self.cntr.addr_i()+self.disp
        return self.i_addr

    # Object module address
    def addr_o(self):
        if self.cntr is None:
            raise ValueError("%s not assigned a container: %s" \
                % (eloc(self,"addr_o"),self))
        return self.cntr.addr_i()
        
    # Region absolute address
    def addr_sa(self):
        if not self.sa_addr:
            if self.cntr is None:
                raise ValueError("%s not assigned a container: %s" \
                    % (eloc(self,"addr_a"),self))
                self.sa_addr=self.cntr.addr_sa()+self.disp
        return self.sa_addr
        
    # Tests whether another position is from the same container (Allocation) as
    # this Position object.
    # Returns:
    #    True  if they are from the same container
    #    False if they are not from the same container
    def together(self,other):
        assert isinstance(other,Position),\
            "%s 'other' argument must be a Position object: %s" \
                % (eloc(self,"together"),other)
        return self.cntr==other.cntr


# This object represents text positioned within an allcoation.  It is the foundation
# for creation of binary content.
#
# The object depends upon three pieces of information that may be separately
# established or supplied when the object is created, or any combination.
#    - the position of the text within an allocation - set_pos() method
#    - the length of the binary text - set_len() method
#    - the binary content itself - set_text() method
#
# When all three have been supplied, the self.valid attribute will be set to True
# indicating it may be used.  The object's length and text must not conflict.
# Once either the text is set or the length, setting the other must not have a
# different text length or length.  In some contexts it may make sense to
# establish the length before the text is set.  In others, it may make sense to
# let the supplied text establish the length.
#
# The Text object is mutable.  Binary data within the supplied text may be
# set using self[n]=int or self[i:j]=bytearray.

class Text(Position):
    def __init__(self,text=None,pos=None,length=None):
        super().__init__()    # Set up position related attributes
        self._pos=self._len=self._text=None

        if pos is not None:
            self.set_pos(pos)    # Section position (address) of the binary content
        if text is not None:
            self.set_text(text)  # Binary text of this object
        if length is not None:
            self.set_len(length) # Length of text (must match text if text present)
        self.valid=not self._invalid()
            
        self.binary=None         # sa mode binary output

    # Return the length of the object.  If text is present the length is that of
    # the text itself.  If not it is the set length.  This can return None if
    # neither the text nor the length have been set.
    def __len__(self):
        if self._text is None:
            return self._len
        return len(self._text)

    # Accesses a portion of the binary bytearray object.
    # Returns:
    #   self[n] the individual byte in the array as an integer
    #   self[i:j] returns a bytearray object of the requested indices.
    # Exceptions:
    #   IndexError if the indices are out of bounds.
    #   ValueError if the int is not in the range 0-255, inclusive
    def __getitem__(self,key):
        if isinstance(key,int):
            return self._text[key]

        # Assume we are dealing with a slice object.  If not very likely an
        # AttributeError will occur somewhere in the processing.  This is a bug
        # that needs fixing.  slice objects are very difficult to programmatically
        # identify, so a "look before you leap" approach is heavy. 

        # The slice object must not contain a third value,
        # self[i:J:k] is not supported.  This assertion tests for this case.
        assert key.step is None,\
            "%s slice object must not contain a step value: %s" \
                % (eloc(self,"__getitem__"),key)
        # An IndexError may result if the indices are out of bounds.  Again, a 
        # bug so just let it happen.
        return self._text[key.start:key.end]

    # Inserts an integer byte or bytearray into the existing binary text
    #   self[n]=int
    #   self[i:j]=bytearray
    # Exceptions:
    #   IndexError if the indices are out of bounds.
    #   ValueError if the int is not in the range 0-255, inclusive
    def __setitem__(self,key,item):
        if isinstance(key,int):
            assert isinstance(item,int),\
                "%s 'item' argument must be an integer: %s" \
                    % (eloc(self,"__setitem__"),item)
            self._text[key]=item

        # Otherwise assume a slice object.  See the comments in the __getitem__
        # method concerning slice objects.
        assert isinstance(item,bytearray),\
             "%s 'item' argument must be a bytearray object: %s" \
                 % (eloc(self,"__setitem__"),item)
        assert key.step is None,\
            "%s slice object must not contain a step value: %s" \
                % (eloc(self,"__setitem__"),key)
        self._text[key.start:key.stop]=item

    def __str__(self):
        if self._text is None:
            txt="None"
        else:
            txt="len(%s)==%s" % (self._text.__class__.__name__,len(self._text))
        return "Text: pos:%s length:%s text:len(%s)==%s" \
            % (self._pos,self._len,txt)

    # Tests whether the object has all of its attributes.  Each key attribute
    # may be set separately
    def _invalid(self):
        return self._text is None or self._pos is None or self._len is None

    # Add binary text, bytearray, to the objects text
    # Use the extend() method to add another Text object
    def append(self,bytes):
        assert isinstance(bytes,bytearray),\
            "%s 'bytes' argument must be a bytearray object: %s" \
                % (eloc(self,"append"),bytes)
                
        self._text+=bytes
        self._len=len(self._text)

    def build(self):
        assert self.binary is None,\
            "%s Text object already built" % eloc(self,"build")
        self.binary=self._text

    # This method allows text to be added to object from another Text object.
    # The extended Text object must follow this object.
    # Use the append() method to directly add a bytearray to the object.
    # Method Arguments:
    #   text   A Text object being included in this object
    #   pad    Specify True to cause binary zero to be inserted between the new
    #          text and the existing text if a gap exists between the two positions.
    #          Specify False if the extending Text object must immediately follow
    #          this object.  Defaults to False.
    def extend(self,text,pad=False):
        assert isinstance(text,Text),\
            "%s 'text' argument must be a Text object: %s" \
                % (eloc(self,"extend"),text)
              
        gap=self.follows(text)
        assert gap>=0,"%s can not extend object, follows() method returned: %s" \
            % (eloc(self,"extend"),gap)
        
        if gap == 0:
            self._text+=text._text
            self._len=len(self._text)
            return
        # gap exists
        assert pad,"%s can not extend text because pad is %s and gap exists: %s" \
            % (eloc(self,"extend"),pad,gap)
        insert=bytearray(gap)
        self._text+=insert
        self._text+=text._text
        self._len=len(self._text)

    # Creates a bytes list matching the length of the object
    def fill(self):
        assert isinstance(self._len,int) and self._len>0,\
            "%s self._len not an integer >0: %s" % (eloc(self,"fill"),self._len)
        self._text=bytesarray(self._len)

    # Determines whether another Text follows this Text object and by how many
    # positions.  Negative values indicate conditions why the other does not
    # follow this object.
    # Returns:
    #  An integer indicating how the other object does or does not follow this
    #  Text object:
    #  0 or more  The other Text follows this Text with this number of positions
    #             separating the two.  O means the other immediately follows this
    #             object
    #   -1     If the two Text objects belong to different Allocation objects.
    #   -2     If the two Text objects overlap
    #   -3     If the other completely precedes this Text object
    def follows(self,text):
        mypos=self._pos
        other=text._pos
        if not mypos.together(other):
            return -1
        rel=self.relative(text)
        if rel==1:
            # The other object does follow me, return the gap, if any
            return other.disp - (mypos.disp+self._len)
        if rel==0:
            # Text object are from different allocations
            return -1
        if rel<0:
            # Text objects overlap
            return -2
        if rel==2:
            # Other text object precedes this object
            return -3    
        raise ValueError(\
            "%s received unexpected result from relative() method: %s" \
                % (eloc(self,"follows"),rel))

    # Determines the relative relationship between this and another Text object
    # Returns:
    #   -2  If the other object begins before this object AND overlaps
    #        self      [----------]
    #       other  [--------]
    #
    #   -1  If the other object does not begin before this object and overlaps
    #        self  [-------]
    #       other  [----]
    #       other      [------]
    #
    #    0  If the two objects are from different allocations
    #
    #    1  If the other object starts after this object and does not overlap
    #        self  [------]
    #       other          [-------]
    #       other               [-------]
    #
    #    2  If the other object precedes this object without overlap
    #        self               [-------]
    #       other     [--------]
    #       other [-------]
    def relative(self,other):
        assert isinstance(other,Text),\
            "%s 'other' argument must be a Text object: %s" \
                % (eloc(self,"overlap"),other)
        
        mypos=self._pos
        pos=text._pos
        if not mypos.together(pos):
            # Postions in different allocations do not overlap
            return 0
        mystart=mypos.disp
        start=pos.disp
        if (mypos.disp+self._len)<=start or (pos.disp+other._len)<=mystart:
            overlap=1
        else:
            overlap=-1
        if start<mystart:
            return overlap*2
        else:
            return overlap*1
        
    # Set the length of this Text object.  If the object already contains text
    # data, then the length being set must match.  This method is expected to be
    # used prior to use of set_text() method.
    # Method Argument:
    #   length   The length of the object.
    def set_len(self,length):
        assert isinstance(length,int) and lenght>=1,\
            "%s 'length' argument must be an integer greater than 0: %s" \
                % (eloc(self,"set_len"),length)
        assert self._text is not None and len(self._text)==length,\
            "%s text length (%s) does not match set length: %s" \
                % (eloc(self,"set_len"),len(self._text),length)

        self._len=length
        self.valid=not self._invalid()

    # Sets the position within a allocation of the Text object.
    def set_pos(self,addr):
        assert addr is isinstance(addr,Position),\
            "%s 'addr' argument must be a Position object: %s" \
                % (eloc(self,"set_pos"),addr)
        self._pos=addr          # Address object of my position
        self.valid=not self._invalid()

    # Sets the initial binary text of the object.  If the set_len() method has
    # already been used, the text length must match.  If the set_len() method has
    # not been used, the length is established based upon the length of the supplied
    # text.
    # Method Arguments:
    #   text    This argument must be a bytearray object.
    def set_text(self,text):
        assert isinstance(text,(bytes,bytearray)),\
            "%s 'text' argument must be a bytes or bytesarray object: %s" \
                % (eloc(self,"set_text"),text)
        assert len(text)==self._len,\
            "%s length (%s) does not match 'text' argument length: %s" \
                % (eloc(self,"set_text"),self._len,len(text))

        self._text=text
        self._len=len(text)
        self.valid=not self._invalid()

    def validate(self):
        if self._invalid():
            raise ValueError("%s %s imcomplete: %s" \
                % (eloc(self,"validate"),self.__class__.__name__,self))

        
# This object represents an address constant positioned within a section
# During assembly Pass1 type, length, and position are established and in Pass2 the
# relocated address is specified
# During linking the entire object is created from the object module
class Adcon(Text):
    def __init__(self,length,addr=None,pos=None):
        assert isinstance(typ,str),\
            "%s 'typ' argument must be a string: %s" % (eloc(self,"__init__"),typ)
        assert addr is None or (isinstance(addr,int) and addr>=1 and addr<=8),\
            "%s 'length' argument must be an integer between 1 and 8 or None: %s" \
                % (eloc(self,"__init__"),addr)

        super().__init__(pos=pos,length=length)
        # Both of these attributes are set by the set_relo() method
        self.typ=None          # Address constant type
        self._relo=None        # Relocated address
        self._dir=None         # Direction of relocation
        self._adj=None         # Adjustment applied to relocated address
        # Note the adjustment value becomes the text content for the adcon
        if addr is not None:
            self.set_relo(addr)  # This is the source of the text content for the 

    def __str__(self):
        return "%s  %s:%s" % (super().__str__(),self.typ,self._relo)

    def _invalid(self):
        return self.typ is None or self._relo is None or super()._invalid()

    def build(self):
        value=self._relo.addr_sa()
        self.binary=value.to_bytes(len(self),byteorder="big",signed=False)

    def set_relo(self,addr):
        assert isinsance(addr,Address),\
            "%s 'addr' argument must an Address object: %s" \
                % (eloc(self,"set_relo"),addr)
                
        # Establish the adcon type
        if isinstance(addr,SectAddr):
            typ="A"
        elif isinstance(addr,ExternalAddr):
            typ="V"
        else:
            raise ValueError("%s unexpected type: %s" \
                % (eloc(self,"set_relo"),addr))
        self.typ=typ
        
        # Establishe relocation information from the relocation address
        self._relo=addr
        lval=addr.lval()
        if lval < 0:
            self._dir=-1
        else:
            self._dir=1
        self._adj=abs(lval)

        # Establish the text content
        if typ=="A":
            value=addr.section.base+self._adj
        elif typ=="V":
            value=self._adj
        self.set_text(value.to_bytes(len(self),byteorder="big",signed=False))

#
#  +----------------------+
#  |                      |
#  |   Named Link Items   |
#  |                      |
#  +----------------------+
#

# This class is the foudation for all elements that have a symbol associated with it
# The element's content is defined by the subclass of this class
class LNKBase(object):
    def __init__(self,name,unnamed=True):
        super().__init__()      # Initialize Position attributes
        if unnamed and name is None:
            self.symbol=None    # Unnamed object
            return
        assert isinstance(name,str),\
           "%s 'name' argument must be a string: %s" % (eloc(self,"__init__"),name)
        self.symbol=name        # Name of the symbol referenced link element


# This class is the foudation for hierarchical elements, for example, regions and
# sections.  Element's are required to have a unique name.
#
# Instance Arguments
#   name     A name by which the element this is identified.  None indicates this
#            element is unnamed.  It will be added to the name diction
#   ecls     The LNKELE subclass supported as elements of this element.  If this is
#            a leaf element, None must be specified.  Leaf elements may not have any
#            elements added to it.
#   track    Specify True to cause elements to be tracked sequentially when added
#            Specify False to only maintain added elements by name
#   unnamed  Whether this element can be unnamed. 
class LNKELE(LNKBase):
    def __init__(self,name,ecls,track=False,unnamed=False):
        super().__init__(name,unnamed=unnamed)
        self.ecls=ecls        # Elements of this class may be added to this element
        if name is None and not unnamed:
            raise ValueError("%s this element may not be unnamed: %s" \
                % (eloc(self,"__init__"),self.__class__.__name__))
        self.name=name        # Name of this element (None == unnamed)

        self.parent=None      # Element object in which I am a member (root is None)

        # Name-based tracking of added elements
        self.unnamed=unnamed  # Whether an instance of this element can be unnamed
        self.named={}         # Elements accessed by name
        # Sequence tracking of added elements
        self.track=track      # Whether to track sequence of added elements
        self.seq=[]           # Elements accessed by sequence

    # Retrieve an added element by index or name
    def __getitem__(self,key):
        if isinstance(key,int):
            return self.seq[key]   # Use the integer as an index into the sequence
        if isinstance(key,str) or key is None:
            return self.named[key] # Use the symbol as the symbol dictionary key
        raise ValueError("%s requested item must be an integer or string: %s" \
            % (eloc(self,"__getitem__"),key))
        
    def __str__(self):
        return "%s:%s" % (self.__class__.__name__,self.name)

    # Add an element to this element.
    # Method Argument:
    #   ele    The element being added to the element.
    def add_ele(self,ele):
        if self.ecls is None:
            raise ValueError("%s leaf element (%s) may not have added elements: %s"\
                % (eloc(self,"add_ele:"),self,ele))
        assert isinstance(ele,self.ele),\
            "%s 'ele' argument must be a %s object: %s" \
                % (eloc(self,"add_ele"),ecls.__name__,ele.__class__.__name)

        try:
            self.named[ele.name]
            raise LNKError(msg="%s element already registered with %s: %s" \
                % (eloc(self,"add_ele"),self.name,ele.name))
        except KeyError:
            pass
        item.parent=self
        self.named[ele.name]=ele
        if self.track:
            self.seq.append(ele)

#
#  +---------------------------------+
#  |                                 |
#  |   Individual Named Link Items   |
#  |                                 |
#  +---------------------------------+
#

class Entry(LNKBase):
    def __init__(self,symbol,pos):
        assert isinstance(pos,Position),\
            "%s 'pos' argument must be a Position object: %s" \
                % (eloc(self,"__init__"),pos)
        super().__init__(self,symbol)
        self.pos=pos          # Position within control section of entry


class LNKContent(LNKELE):
    def __init__(self,name,ecls,align=0,track=False,unnamed=False):
        super().__init__(name,ecls,track=track,unnamed=unnamed)

        # Allocation of content in this element
        self._alloc=Allocation(self.name)

        # Output binary content
        self.binary=None      # A Text object when created.

    def __len__(self):
        return self.length

    # Returns a content address appropriate to the subclass
    def _addr(self,value):
        raise NotImplementedError("%s subclass %s must supply _addr() method" \
            % (eloc(self,"_addr"),self.__class__.__name__))

    # Expand the section without actually adding any text content
    # Returns:
    #   starting position of the expanded section following any alignment
    def _expand(self,size,align=None):
        if align is not None:
            cur=self._align(align)
        else:
            cur=self.ndx
        self.ndx=new=cur+size
        self.length=max(self.length,new)

    # Assigns positions to elements within this object
    def _position(self):
        for ele in self.seq:
            # Position element's own elements within itself so we know its length
            ele._position()  # Recursion ends with the section object
            pos=self._allocate(len(ele),align=ele.alignment)
            ele.disp=pos

    # Establishes a new section displacement for assignments
    # Returns:
    #   the newly assigned displacement as a SectAddr
    def _reset(self,new):
        assert isinstance(new,int) and new>=0,\
            "'new' argument must be a non-negative integer: %s" % new
        self.ndx=new
        self.length=max(self.length,new)
        return self._addr(new)

    # Add a content element to this content element
    def add_ele(self,content):
        super().add_ele(content)   # Use super class to add the element
        # Now add the element's Allocation object to mine as a sub-allocation.
        self.alloc.sub_alloc(content.alloc)

    # Alignment returning new Position
    def align(self,align):
        return self._alloc.align(align=align)

    # Allocate a portion of the content based upon alignment and size
    # Returns:
    #   Address object of the items allocated position
    def alloc(self,length,align=1):
        return self._alloc.alloc(length,align=align)

    # Accumulates all of the element content into a single object
    # Used for sa mode output
    def build(self):
        # Create the binary content for regions and image
        self.binary=bytesarray(self.length)
        for ele in self.seq:
            ele.build()           # Consolidate the elements content 
            start=ele.disp
            end=ele.disp+ele.length
            try:
                self.binary[start:end]=ele.binary
            except IndexError:
                raise ValueError(\
                    "%s binary destinted for [%s:%s] can not be inserted "
                        "into [0:%s]" % (start,end,len(self.binary)))
        self.binary=bytes(self.binary)

    # Returns the current location Position
    def star(self):
        return self._alloc.star()

    # Assigns positions to elements within this 
    def position(self):
        for ele in self.seq:
            # Position element's own elements within itself so we know its length
            ele.position()  # Recursion ends with the section object
            pos=self._allocate(len(ele),align=ele.alignment)
            ele.disp=pos


# Constructed program module
# A module's elements are regions in samode and sections in link mode
class LNKModule(LNKContent):
    def __init__(self,name,samode=True):
        self.samode=samode    # Whether regions are being supported or not
        super().__init__(name,LNKRegion,track=True)

        self.needed=[]        # Region names needed by this module
        self.symbols={}       # Dictionary of external symbols.

    def add_needed(self,symbol):
        assert isinstance(symbol,str),\
            "%s 'symbol' argument must be a string: %s" \
                % (eloc(self,"add_needed"),symbol)

        self.needed.append(symbol)

    def add_region(self,rgn):
        if not self.samode:
            raise NotImplementedError("%s does not support regions in link mode" \
                % eloc(self,"add_region"))
        assert isinstance(rgn,LNKRegion),\
            "%s 'item' argument must be a LNKRegion object: %s" \
                % (eloc(self,"add_region",rgn))

        self[rgn.symbol]=rgn
        self.add_symbol(rgn)

    def add_section(self,sect):
        if self.samode:
            raise NotImplementedError("%s does not support regions in sa mode" \
                % eloc(self,"add_section"))
        assert isinstance(sect,LNKSection),\
            "%s 'item' argument must be a LNKSection object: %s" \
                % (eloc(self,"add_section",sect))
        
        self[sect.symbol]=sect
        self.add_symbol(sect)

    def add_symbol(self,obj):
        assert isinstance(obj,LNKBase),\
            "%s 'obj' argument must be a LNKBase object: %s" \
                % (eloc(self,"add_symbol",obj))

        try:
            defn=self.symbols[obj.symbol]
            raise KNKError(msg="symbol already defined: %s = %s" \
                % (obj.symbol,defn)) from None
        except KeyError:
            self.symbols[obj.symbol]=obj

    def build(self):
        if not self.samode:
            raise NotImplementedError(\
                "%s build() method not implemented in link mode" \
                    % eloc(self,"build"))
        # Do the build for sa mode
        super().build()

    # Position I/F methods
    def addr_a(self,samode=True):
        raise NotImplementedError("%s subclass does not support addr_a() method" \
            % eloc(self,"addr_a"))

    def addr_i(self):
        return 0

    def addr_sa(self):
        raise NotImplementedError("%s subclass does not support addr_sa() method" \
            % eloc(self,"addr_sa"))


# Constructed Region
# A region's elements are sections
#
# Instance Arguments
#   name      The regions name or None if unnamed
#   address   The absolute address at which the region starts
class LNKRegion(LNKContent):
    def __init__(self,name,address):
        assert isinstance(addres,AbsAddr),\
            "%s 'address' argument must be an AbsAddr object: %s" \
                % (eloc(self,"__init__"),address)
        super().__init__(name,LNKSection,track=True,unnamed=True)

        self.start=address      # Starting address of this region
        self.needed=[]          # Section names needed by this region

    def _addr(self,disp):
        return AbsAddr(self.sa_addr+disp)

    def add_needed(self,symbol):
        assert isinstance(symbol,str),\
            "%s 'symbol' argument must be a string: %s" \
                % (eloc(self,"add_needed"),symbol)

        self.needed.append(symbol)

    def add_section(self,sect):
        assert isinstance(item,LNKSection),\
            "%s 'item' argument must be a LNKSection object: %s" \
                % (eloc(self,"add_section"),sect)

        self[sect.symbol]=sect

    # Position I/F methods - Position.addr_i() and addr_sa() are inherited
    def addr_a(self,samode=True):
        if samode:
            return super().addr_a(samode=True)
        raise NotImplementedError(\
            "%s subclass does not support addr_a(samode=False) method" \
                % eloc(self,"addr_a"))

    def addr_o(self):
        raise NotImplementedError("%s subclass does not support addr_o() method" \
            % eloc(self,"addr_o"))

    def itPrivate(self):
        return self.name is None


# This class is used when assembling a control section.
# Elements: ASMLocCtr
class ASMSection(LNKContent):
    def __init__(self,name,align=4):
        super().__init__(name,LNKLocCtr,align=align,track=True,unnamed=True)

        # Text object making up the section
        self.relos=[]       # List of Relo objects assigned to the section
        self.entrys=[]      # List of externally accessible entries
        self.text=[]        # List of Text entries

        # Dummy sections use the section Allocation, not a location counter
        if not dummmy:
            # This is the implied section location counter
            self.add_ele(LNKLocCtr(name))

    def __setitem__(self,key,item):
        assert isinstance(item,Entry),\
            "%s 'item' argument must be an Entry object: %s" \
                % (eloc(self,"__setitem__"),item)

        super().__setitem__(key,item)

    def _addr(self,value):
        return SectAddr(value,self)


    # Add an address constant - contribute to both text and relo list
    def add_adcon(self,adcon):
        assert isinstnace(adcon,Adcon),\
            "%s 'adcon' argument must be an Adcon object: %s" \
                % (eloc(self,"add_adcon"),adcon)

        self.text.append(self.adcon)

    # Add a positioned entry to the section
    def add_entry(self,entry):
        assert isinstance(entry,Entry),\
            "%s 'entry' must be an Entry object: %s" % (eloc(self,"add_entry"),entry)

        self._pname(entry)
        self[entry.symbol]=entry

    # Add a positioned relocation item to the section
    def add_relo(self,relo):
        assert isinstance(relo,Relo),\
            "%s'relo' argument must be a Relo object: %s" \
                %(eloc(self,"add_relo"),relo)

        self._pname(relo)
        self.relos.append(relo)

    # Add positioned binary content to the section
    def add_text(self,text,align=1):
        raise NotImplementedError("%s Text objects may not be added directly to "
            "a section, the location counter must be used" % eloc(self,"add_text"))

    # Whether the section is a dummy (True) or control section (False)
    def isDummy(self):
        return False

    # Whether this is private code (unnamed constrol section)
    def isPrivate(self):
        return self.name is None

    # Adds a new location counter to the section and returns it
    def new(self,name):
        cont=LNKLocCtr(name,self)

    # Establishes a new section displacement for assignments
    # Returns:
    #   the newly assigned displacement as a SectAddr
    def org(self,new):
        assert isinstance(new,int) and new>=0,\
            "'new' argument must be a non-negative integer: %s" % new
        self.ndx=new
        self.length=max(self.length,new)
        return self._addr(new)


# This class is used during assembly of a dummy section
# Elements: None
#
# Space may be allocated and assigned by no actual content may be added to it.
class ASMDummy(LNKContent):
    def __init__(self,name):
        super().__init__(name,None)

    def add_text(self,ele):
        raise NotImplementedError(\
            "%s Text elements may not be added to a dummy section (%s)" \
                % (eloc(self,"add_text"),self.name))

    def isDummy(self):
        return True

    def isPrivate(self):
        return False


# This Section object is used when linking sections
class LNKSection(LNKContent):
    def __init__(self,name):
        super().__init__(name,None,unnamed=True)

        self.relos=[]       # List of Relo objects assigned to the section
        self.entrys=[]      # List of externally accessible entries
        self.text=[]        # List of Text entries

class ASMLocCtr(LNKContent):
    def __init__(self,name):
        super().__init__(name,None,unnamed=False,track=False)

        self.text=[]    # Text objects are added here

    def add_text(self,text):
        assert isinstance(text,Text),\
            "%s 'text' argument must be a Text object: %s" \
                % (eloc(self,"add_text"),text)

        self.text.append(text)


#
#  +-------------------+
#  |                   |
#  |   Linked Module   |
#  |                   |
#  +-------------------+
#

# This class represents a module ready for stand-alone output creation.  It is created
# from some external source to which module elements are added.  Unlike an object
# module that is ESD-ID based, this module is symbol name based.  It is composed of
# linkage items that represent, memory resident regions, control sections and other
# symbol related items.  At instantiation, the object is empty.  Elements are added
# using the various "add_xxx" methods.

# Stand-Alone Mode:
#   root is 

class LNKMOD(object):
    def __init__(self,sa=True):
        self.sa=se          # Whether this is running in stand-alone mode or not
        self.pc_reg=None    # 
        self.pc_sect=None
        self.regions={}
        self.reg_seq=[]
        self.sections={}
        #self.seq_seq=
        pass
        
if __name__=="__main__":
   raise NotImplementedError("%s - is intended only for import" % this_module)
        