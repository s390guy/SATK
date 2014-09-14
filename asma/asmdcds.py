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

# This module supports the creation of DC and DS content.

this_module="asmdcds.py"

# Python imports: None
# SATK imports:
import pratt2     # Access for some object type checks
# ASMA imports:
import assembler

# This is the base class describing a nominal values.  This class ultimately creates
# assembled binary data for constant nominal values.  It also contains the
# information related to constant length and alingment for address assignment but
# does not itself perform the assignments.  These objects only exist for DC directive
# operands.  DS directives do not utilize this object.
#
# Instance Arguments:
#   ltok        The asmtokens.LexicalToken object defining the nominal value or
#               an pratt expression object defines the nominal value's generated
#               value.
#               This class and subclasses assume that all lexical tokens have been
#               updated to reflect actual statement position, that is, the tokens
#               update method has been called.
#   length      The implied length.  Specify None if the implied length is defined by
#               the value.  Defaults to None.
#   alignment   The implied alignment.  Specify 0 if no implied alignment applied.
#               Defaults to 0.
#   signed      Specify True if by default the nominal value is signed.  Defaults
#               to None.  None is not equivalent to False.
class Nominal(object):

    # Accepts a string of digits and converts them to bytes using the supplied
    # base and number of characters per byte.
    @staticmethod
    def base2bytes(digits,base,cpb):
        b=bytearray(0)
        chars=len(digits)
        for x in range(0,chars,cpb):
            txt=digits[x:x+cpb]
            assert len(txt)>0,\
                "%s - Nominal.base2bytes() - base conversion loop should not end "\
                "prematurely: x:%s, len(s):%s cpb:%s" % (this_module,x,len(s),cpb)
            i=int(txt,base)
            b.append(i)
        return bytes(b)

    # Given a number of input text characters return the number of bytes consumed
    # where 'cpb' is the number of characters per byte.
    @staticmethod
    def round_up(chars,cpb):
        bytes,extra=divmod(chars,cpb)
        if extra > 0:
            bytes+=1
        return bytes

    # Truncate/pad string on left with zero as the pad character
    @staticmethod
    def tp_left(string,chars):
        if len(string)<chars:
            s=string.rjust(chars,'0')    # Pad on the left with ASCII zeros
        else:
            s=string[len(string)-chars:] # Truncate on the left if needed
        return s

    def __init__(self,ltok,length=None,alignment=0,signed=None):
        # This check is performed to ensure alignment meets the needs of 
        assert isinstance(alignment,int),\
            "%s 'alignment' argument must be an integer: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),alignment)
        self.ltok=ltok             # May be a single token or a list of tokens

        self._length=length        # Implied or explicit length
        self._alignment=alignment  # Implied alignment or None if no alignment
        self._signed=signed        # Whether nominal value is signed or not
        # The signed method updates this if the value by default is signed but this
        # instance is unsigned.  The attribute influences the assembled value.
        self.unsigned=False

        # In Pass1 an empty binary object is create with binary zeros.  If Pass2
        # does nothing, we are left with zeros.  But that should never happen here
        # We will build the actual values and replace it here during Pass2 with the
        # build method()
        self.content=None

    # Returns any alignment required
    # This matches the asmfmscs.DCDS_Operand method of the same name.
    def align(self):
        if self._alignment is None:
            return 0
        return self._alignment

    # This method updates the content attribute with a Binary object containing
    # the nominal values's assembled data.  This method is called by the assembler
    # during Pass 2 processing
    def build(stmt,asm,n,debug=False,trace=False):
        raise NotImplementedError("%s subclass %s must provide build() method" \
            % (assembler.eloc(self,"build",module=this_module),\
                self.__class__.__name__))

    # This method returns an instance of the Nominal subclass suitable for generating 
    # binary data.  All subclasses share this method.
    def clone(self):
        new=self.__class__(self.ltok)
        new.unsigned=self.unsigned
        new.ivalue=self.ivalue
        # These attributes get updated after initial object creation.
        # Cloned objects must reflect the current value not the original.
        new._alignment=self._alignment
        new._length=self._length
        return new

    # Updates the location counter after building the final binary data
    def cur_loc(self,asm):
        asm.cur_loc.increment(self.content)

    # Returns the length being assembled
    # This matches the asmfmscs.DCDS_Operand method of the same name.
    def length(self):
        return self._length

    # Update the nominal value with the constant operand's explicit length.
    # This method is only called when a valid explict length has been provided for
    # the constant's nominal values.  All subclasses use this method.
    def Pass1(self,explen):
        # Set explicit length, overriding implied length
        self._length=explen
        # Disable implied alignment because of explicit length
        self._alignment=0   # assembler.Content.align() wants a number

    # Update whether this is an unsigned nominal value or not.
    def signed(self):
        if self._signed is True:
            self.unsigned=self.ltok.unsigned


class Address(Nominal):
    def __init__(self,addrexpr):
        assert isinstance(addrexpr,pratt2.PExpr),\
            "%s 'addrexpr' argument must be a pratt2.PExpr: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),addrexpr)

        cls=self.__class__
        length,align=cls.attr
        super().__init__(addrexpr,length=length,alignment=align,signed=False)
        self.ivalue=ADCON(addrexpr,cls.typ)

    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(asm,asm.fsmp,stmt,n,self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class BinaryBits(Nominal):
    def __init__(self,ltok):
        length,align,cpb,base=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=False)
        # Create the underlying data abstraction from the lexical token
        self.ivalue=Bits(ltok.extract(),(cpb,base),ltok.linepos)
        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)

class Characters(Nominal):
    def __init__(self,ltok,ccls):
        super().__init__(ltok,length=1,alignment=0,signed=False)
        
        # This attribute represents an intermediate form between a lexical token
        # and the assembled value.
        self.ivalue=ccls(ltok.convert(),ltok.linepos)
        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class DecimalPointed(Nominal):
    def __init__(self,ltok,dcls):
        length,align=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=True)

        # This attribute represents an intermediate form between a lexical token
        # and the assembled value.
        self.ivalue=dcls(ltok.sign(),ltok.dec_digits(),ltok.linepos)
        # Set the length implied by the nominal value itself
        self._length=self.ivalue.infer_length()

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


class SConstant(Nominal):
    def __init__(self,addrexpr):
        assert isinstance(addrexpr,pratt2.PExpr),\
            "%s 'addrexpr' argument must be a pratt2.PExpr: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),addrexpr)
        
        length,align=self.__class__.attr
        super().__init__(addrexpr,length=length,alignment=align,signed=False)
        self.ivalue=SCON(addrexpr)
        
    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(asm,asm.fsmp,stmt,n,self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)

# This object stands in for DS "nominal" values, generating 0x00 for each byte.
# This class allows DS processing to parallel DC.  In the case of DS, one of these
# objects if used when no nominal values are supplied for the operand.  Regular
# nominal values are used if the DS statement actually has nominal values.
class Storage(Nominal):
    def __init__(self,typcls):
        attr=typcls.attr
        super().__init__(None,length=attr[0],alignment=attr[1],signed=False)
        self.typcls=typcls
        
    def __str__(self):
        return "%s(length=%s,alignment=%s)" \
            % (self.__class__.__name__,self._length,self._alignment)
    
    # DS operand has no Pass 2 processing.  Its content is completed in Pass 1
    def build(self,stmt,asm,n,debug=False,trace=False):
        pass
    
    # Override Nominal class clone() method for my needs.
    def clone(self):
        new=Storage(self.typcls)
        new.unsigned=self.unsigned
        # These attributes get updated after initial object creation.
        # Cloned objects must reflect the current value not the original.
        new._alignment=self._alignment
        new._length=self._length
        return new


class TwosCompBin(Nominal):
    def __init__(self,ltok):
        length,align=self.__class__.attr
        super().__init__(ltok,length=length,alignment=align,signed=True)

        # This attribute represents an intermeidate form between a lexical token
        # and the assembled value
        self.ivalue=FixedPoint(ltok.sign(),ltok.digits(),ltok.linepos)

    def __str__(self):
        return "%s(length=%s,alignment=%s,value=%s,content=%s" \
            % (self.__class__.__name__,self._length,self._alignment,self.ivalue,\
                self.content)

    def build(self,stmt,asm,n,debug=False,trace=False):
        data=self.ivalue.build(self._length)
        self.content.update(data,full=True,finalize=True,trace=trace)
        self.cur_loc(asm)


# Each of these classes defines the basic attributes of a constant type related
# to alignment and length.  The first two attributes must be the implied length
# and implied alignment.  For some types, additional attributes are supplied.
# Each Nominal subclass is tied to the values specified by the class 'attr' attribute.

class DC_A(Address):
    attr=(4,4)       # implied length, alignment
    max_len=4        # maximum explicit length
    typ="A"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_AD(Address):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    typ="AD"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_B(BinaryBits):
    attr=(1,0,8,2)   # Attributes used by Bits object (chars/byte, base)
    max_len=256      # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_C(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=256      # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok,StringE)


class DC_CA(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=256      # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok,StringA)


class DC_CE(Characters):
    attr=(1,0)       # implied length, alignment
    max_len=256      # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok,StringE)


class DC_D(TwosCompBin):
    attr=(8,8)       # implied length, alignment
    max_len=8        # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_F(TwosCompBin):
    attr=(4,4)       # implied length, alignment
    max_len=8        # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_FD(TwosCompBin):
    attr=(8,8)       # implied length, alignment
    max_len=8        # meximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_H(TwosCompBin):
    attr=(2,2)       # implied length, alignment
    max_len=8        # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_P(DecimalPointed):
    attr=(1,0)       # implied length, alignment
    max_len=16       # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok,Packed)


class DC_S(SConstant):
    attr=(2,2)       # implied length, alignment
    max_len=2        # maximum explicit length
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_X(BinaryBits):
    attr=(1,0,2,16)  # implied length, alignment, char/byte, base
    max_len=256      # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok)


class DC_Y(Address):
    attr=(2,2)       # implied length, alignment
    max_len=2        # maximum explicit length
    typ="Y"
    def __init__(self,addrexpr):
        super().__init__(addrexpr)


class DC_Z(DecimalPointed):
    attr=(1,0)       # implied length, alignment
    max_len=16       # maximum explicit length
    def __init__(self,ltok):
        super().__init__(ltok,Zoned)


class ADCON(object):
    # Valid lengths for different address constants when value is not an integer
    lengths={"A":[2,3,4],"AD":[1,2,3,4,5,6,7,8],"Y":[2,]}
    def __init__(self,expr,typ):
        self.expr=expr
        self.typ=typ
        self.lengths=ADCON.lengths[typ]

    def __str__(self):
        return "%s(expr=%s)" % (self.__class__.__name__,self.expr)
        
    def build(self,asm,parsers,stmt,n,length,trace=False):
        value=parsers.evaluate_expr(asm,stmt,self.expr,debug=False,trace=trace)

        assert isinstance(value,(int,assembler.Address)),\
            "%s internal calculation of operand %s address expression resulted in an"\
            "unsupported value: %s" \
            % (assembler.eloc(self,"build",module=this_module),n+1,value)

        if isinstance(value,assembler.Address):
            if length not in self.lengths:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s %s-type explicit length invalid for an address "\
                    "nominal value: %s" % (n+1,self.typ,length))
            if value.isAbsolute():
                value=value.address
            else:
                raise assembler.AssemblerError(line=stmt.lineno,\
                    msg="operand %s address constant did not evaluate to an "\
                        "absolute address: %s" % (n+1,value))

        # Convert computed address constant to bytes
        b=value.to_bytes((value.bit_length()//8)+1,byteorder="big",signed=False)

        # Perform left truncation/padding
        pad=b'\x00' * length
        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" 
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))

        return b
        

# This object abstracts binary values.  It is derived from a lexitcal token but
# ceases to be conntected to it.  It assumes that the lexical token's type regular
# expression has done its job and only valid characters are present
class Bits(object):
    def __init__(self,digits,attr,linepos):
        self.digits=digits
        self.cpb,self.base=attr
        self.linepos=linepos

    def __str__(self):
        return "%s(digits='%s',base=%s,cpb=%s,bpos=%s)" \
            % (self.__class__.__name__,self.digits,self.base,self.cpb,self.linepos)

    # Build binary data composed of bits based upon the supplied length
    def build(self,length,trace=False):
        cpb=self.cpb      # Get the number of characters per byte
        chars=cpb*length
        s=Nominal.tp_left(self.digits,chars)
        b=Nominal.base2bytes(s,self.base,self.cpb)

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))

        return b

    # Returns the length implied by the nominal value itself
    def infer_length(self):
        return Nominal.round_up(len(self.digits),self.cpb)


# This object abstracts input signed decimal values.  It is derived from a lexical
# token but ceases to be connected to it.  It assumes that the lexical token's type
# regular expression has done its job and only valid characters are present.
# The handling of the original lexical token and its input is similar to the 
# FixedPoint class.  However, assembled data diverges dramatically from the
# FixedPoint class.
class Decimal(object):
    sign={"-":"D","+":"C","U":"F",None:"C"}
    def __init__(self,sign,digits,cpb,linepos):
        self.linepos=linepos
        self.sign=sign           # Sign of the constant '+', '-', 'U' or None
        self.digits=digits       # String of decimal digits
        self.cpb=cpb

    def __str__(self):
        return "%s(sign='%s',digits='%s',pos=%s)" \
            % (self.__class__.__name__,self.sign,self.digits,self.linepos)

    def build(self,length,trace=False):
        hexdigits=self.make_hex(length)
        # Convert the hex data into bytes
        b=Nominal.base2bytes(hexdigits,16,2)

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" % (cls_str,len(b),b))

        return b

    def infer_length(self):
        raise NotImplementedError("%s subclass %s must proivde infer_length() method" \
            % (assembler.eloc(self,"infer_length",module=this_module),\
                self.__class__.__name__))


class Packed(Decimal):
    def __init__(self,sign,digits,linepos):
        super().__init__(sign,digits,2,linepos)

    def infer_length(self):
        return Nominal.round_up(len(self.digits)+1,2)

    def make_hex(self,length):
        # Convert to packed digits plus sign
        hexdigits="%s%s" % (self.digits,Decimal.sign[self.sign])
        # Do left truncation/padding
        chars=length*2
        return Nominal.tp_left(hexdigits,chars)


class Zoned(Decimal):
    def __init__(self,sign,digits,linepos):
        super().__init__(sign,digits,1,linepos)

    def infer_length(self):
        return len(self.digits)

    def make_hex(self,length):
        digits=Nominal.tp_left(self.digits,length)
        hi=digits[:-1]
        lo=digits[-1]
        lohex="%s%s" % (Decimal.sign[self.sign],lo)

        zoned=""
        for digit in hi:
            # unpack each non-signed digit
            zoned="%sF%s" % (zoned,digit)
        return "%s%s" % (zoned,lohex)


# This object abstracts input signed numeric values.  It is derived from a lexical
# token but ceases to be connected to it.  It assumes that the lexical token's type
# regular expression has done its job and only valid characters are present.
# The handling of the original lexical token and its input is similar to the 
# Decimal class.  However, assembled data diverges dramatically from the Decimal class.
class FixedPoint(object):
    sign_char={"+":1,"-":-1,None:1,"U":1}
    def __init__(self,sign,digits,linepos):
        self.linepos=linepos
        self.sign=sign           # Sign of the constant '+', '-', 'U' or None
        self.digits=digits       # String of decimal digits

    def __str__(self):
        return "%s(sign='%s',digits='%s',pos=%s)" \
            % (self.__class__.__name__,self.sign,self.digits,self.linepos)

    # Private method that assembles fixed point values
    def __build(self,length,signed=False,trace=False):
        # Compute input source text into an integer with the correct sign
        i=int(self.digits)*FixedPoint.sign_char[self.sign]

        # Convert the integer into bytes
        b=i.to_bytes((i.bit_length()//8)+1,byteorder="big",signed=signed)

        # Determine padding 
        if signed and i<0:
            pad=b'\xFF' * length
        else:
            pad=b'\x00' * length

        bindata=pad+b
        b=bindata[len(bindata)-length:]

        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"__build",module=this_module),len(b),b))

        return b

    # Returns assembled bytes conforming the external interface
    def build(self,length,trace=False):
        return self.__build(length,signed=self.sign!="U",trace=trace)


# This object builds S-type constants.  It is very similar to ADCON.
class SCON(object):
    def __init__(self,expr):
        self.expr=expr
        
    def __str__(self):
        return "%s(expr=%s)" % (self.__class__.__name__,self.expr)
        
    def build(self,asm,parsers,stmt,n,length,trace=False):
        if length != 2:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type explicit length invalid: %s" % (n+1,length))
        
        value=parsers.evaluate_expr(asm,stmt,self.expr,debug=False,trace=trace)
        
        if isinstance(value,int):
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type value not an address: %s" % (n+1,value))

        try:
            base,disp=asm.bases.find(value,12,asm,trace=trace)
        except KeyError:
            # Could not resolve base register and displacement
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="operand %s S-type constant could not resolve implied base "
                "register for location: %s" % (n+1,value)) from None
            
        value=(base<<12)+(0xFFF & disp)
        b=value.to_bytes(2,byteorder="big",signed=False)
        
        if __debug__:
            if trace:
                print("%s return bytes: %s '%s'" \
                    % (assembler.eloc(self,"build",module=this_module),len(b),b))
        
        return b
        

class String(object):
    def __init__(self,chrs,linepos):
        self.chrs=chrs
        self.linepos=linepos
        # This is the assembler value.  Double quotes have been handled by parser.
        # Double ampersands are handled here.
        self.achrs=self.chrs.replace("&&","&") 

    def __str__(self):
        return "%s(chrs='%s',pos=%s)" \
            % (self.__class__.__name__,self.chrs,self.linepos)

    def build(self,length,trace=False):
        # Note input string is ASCII data natively
        string=self.achrs
        if len(string)<length:
            s=string.ljust(length)   # Pad on the right with ASCII blanks
        else:
            s=string[:length]  # Truncate on the right if needed

        s=self.translate(s)    # Let the subclass handle the character set
        if trace:
            print("%s return bytes: %s '%s'" % (cls_str,len(s),s))
        return s               # Return the character string as its to be assembled

    def infer_length(self):
        return len(self.achrs)


# String assembled using ASCII code points
class StringA(String):
    def __init__(self,chrs,linepos):
        super().__init__(chrs,linepos)

    def translate(self,string):
        return string


# String assembled using EBCDIC code points
class StringE(String):
    def __init__(self,chrs,linepos):
        super().__init__(chrs,linepos)

    def translate(self,string):
        return assembler.CPTRANS.a2e(string)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
