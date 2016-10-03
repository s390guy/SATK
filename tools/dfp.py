#!/usr/bin/python3
# Copyright (C) 2016 Harold Grovesteen
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

# This module supports decimal floating point (DFP) interchange formats for 32-, 64-.
# and 128-bit values using the decimal encoding of the significand as described in
# IEEE-754-2008.
#
# DFP interchange formats consist of three fields:
#   - a sign,
#   - a combination field, and
#   - a trailing significand.
#
# The combination and trailing significand fields and their size depends upon the 
# size of the exchange format.  Exchange formats of 32, 64, and 128 bits are
# described in the standard, as well as how attributes for formats in excess of 128 
# bits are determined.  This module supports only 32-, 64- and 128-bit exchange
# formats.
#


this_module="dfp.py"

# Python imports:
import decimal      # Access Python native decimal floating point support
# SATK imports:
import fp           # Access generic floating point classes


# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=eloc(self,"method")
# or
#     cls_str=eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exception string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)


#
# +---------------------------------------------------------------+
# |                                                               |
# |   Decimal Floating Point Combination and Sign Field Objects   |
# |                                                               |
# +---------------------------------------------------------------+
#

# These classes support sign and combination field encoding and decoding.  They are
# specific to each of the three supported exchange formats: 32-bit, 64-bit, and
# 128-bit.
#
# The entire combination and sign field are, in bits:
#   bits 0-11 of a 32-bit encoded value, or 12 bits in length
#   bits 0-13 of a 64-bit encoded value, or 14 bits in length
#   bits 0-17 of a 128-bit encoded value, or 18 bits in length
#
# The combination field consists of the binary encoding of the value's biased
# exponent and the "+5" portion of the w+5 content of the combination field.  The
# "+5" portion of the field includes a portion of the exponent, the first digit
# of the signicand and a set of bits that define the format of the "+5" portion
# of the combination field.  The remainder of the combination field is the remaining
# portion of the biased exponent.
#
# The sign field is considered by the standard as a field separate from the 
# combination field (aka w+5).  The interchange format places the sign field
# as the first bit of the interchange value, followed immediately by the w+5 field.
# For the purposes of the implementation it is natural to include the sign field
# with the "+5" portion of the combination field.  Thus the "plus6" format used
# below.
#
# The combination field itself varies in length depending upon the length of the
# interchange format being used.  The variability applies to the length of the
# biased exponent or reserved field.
#
# The following table describes the 9 possible formats used by bits 0-6.
#  LMD == Left most digit of the significand
#  LME == left most bits of the biased exponent
#  RBE == remainng bits of the biased exponent
#
# The complete biased exponent is the concatenation of the LME bits and the RBE bits.
# The LMD is concatenated with the densely packed decimal digits of the significand.
#
# FMT  b0  b1  b2  b3  b4  b5  B6 +           LMD          LME     b6     b7+
#  0   S   1   0   x   x   x   x        4(b3)+2(b4)+b5    b1,b2    <---RBE--->
#  1   S   1   1   0   0   x   x              8+b5        b3,b4    <---RBE--->
#  2   S   1   1   1   1   0   x            Infinity               <-resered->
#  3   S   1   1   1   1   1   x              NAN                  Q/S   payload

#
# The plus6_format encodes bits 0-5: the sign and the +5 bits of the w+5 combination
# field.  The content of the "+6" object is independent of the length of the
# combination field.  The scomb object must handle storage format lengths for
# the two fields.

# Base class for each format
class plus6_format(object):
    format=None       # +6 format number
    is_mask=None      # Mask for recognizing this format
    set_mask=None     # Mask for setting format bits
    digits=None       # List of 'digits' supported by this format

    # Return the class required to interpret first 6 bits of the interchange format.
    # The returned class is independent of the interchange length.
    # Method Arguments:
    #   p6      An integer representing the Sign and "+5" bits of the encoded 
    #           interchange format.
    @staticmethod
    def decode_format(p6):
        # Note: this sequence is required to ensure the format checks start with 
        # the most restrictive bits settings to the least.  The default is format 0.
        c = plus6_fmt0
        for fmt in [plus6_fmt3,plus6_fmt2,plus6_fmt1]:
            if fmt.isFormat(p6):
                c=fmt
                break
        return c

    @staticmethod
    def init():
        plus6_format.digits={\
            0:plus6_fmt0,
            1:plus6_fmt0,
            2:plus6_fmt0,
            3:plus6_fmt0,
            4:plus6_fmt0,
            5:plus6_fmt0,
            6:plus6_fmt0,
            7:plus6_fmt0,
            8:plus6_fmt1,
            9:plus6_fmt1,
            "infinity":plus6_fmt2,
            "nan":     plus6_fmt3}
        for cls in [plus6_fmt0,plus6_fmt1,plus6_fmt2,plus6_fmt3]:
            cls.cls_init()

    # Convert a declet into a string of binary digits.
    @staticmethod
    def p6_binary(value):
        b=bin(value & 0b111111)        # Convert value to a binary literal string
        b=b[2:]                        # Drop off the initial 0b
        b="00000%s" % b                # Add high-order zeros
        b=b[-6:]                       # Right justify the 10 binary digits
        return b                       # Return the string

    # Returns True if the supplied plus6 bits is in the format supported by this
    # class for decoding, False otherwise.
    @classmethod
    def isFormat(cls,value):
        return (value & cls.is_mask) == cls.set_mask

    # Returns True if the supplied digit requires this format for encoding, False
    # otherwise.  
    @classmethod
    def needsFormat(cls,digit):
        try:
            return plus6_format.digits[digit]
        except KeyError:
            raise ValueError("%s.needsFormat - unrecognized digit: %s" \
                % (cls.__name__,digit)) from None

    def __init__(self,number=False,nan=False,infinity=False,debug=False):
        assert number or nan or infinity,\
            "%s neither 'number', 'nan' nor 'infinity' are True" \
                % (eloc(self,"__init__"))

        self.debug=debug

        # These attributes are specific to the subclass and are specified when the
        # subclass is instantiated.
        self.number=number         # This is a number
        self.nan=nan               # This is Not a Number
        self.infinity=infinity     # This is an infinity

        # These attributes are also specific to the subclass but must be visible
        # before the subclass is instantiated.
        cls=self.__class__
        self.format=cls.format
        self.is_mask=cls.is_mask
        self.set_mask=cls.set_mask

        # This attribute is supplied by the decode() method or calculated by
        # the encode() method.  It is always set by the _ck_value() method
        self.bits=None             # This value is established

        # These attributes are supplied by the encode() method or calculated by
        # the decode() method
        self.sign=None             # The sign of the value: 0==+, 1==-
        self.lmd=None              # Left most significand digit
        self.lme=None              # Left most two bits of the biased exponent

    def __str__(self):
        typ="?"
        if self.number:
            typ="Number"
        elif self.nan:
            typ="NaN"
        elif self.infinity:
            typ="Infinity"
        if self.bits is None:
            bits="None"
        else:
            bits=plus6_format.p6_binary(self.bits)
        return "P6: fmt %s: %s - %s sign: %s LMD: %s LME: %s" \
            % (self.format,typ,bits,self.sign,self.lmd,self.lme)

    def _ck_ldigit(self,digit):
        assert isinstance(digit,int),\
            "%s 'digit' argument must be an integer: %s" \
                % (eloc(self,"_ck_ldigit"),digit)
        assert digit==8 or digit==9,\
            "%s 'digit' argument must be either 8 or 9: %s" \
                % (eloc(self,"_ck_ldigit"),digit)
        self.lmd=digit

    def _ck_sdigit(self,digit):
        assert isinstance(digit,int),\
            "%s 'digit' argument must be an integer: %s" \
                % (eloc(self,"_ck_digit"),digit)
        assert digit>=0 and digit<=7,\
            "%s 'digit' argument must be an integer between 0 and 7: %s" \
                % (eloc(self,"_ck_exp"),digit)
        self.lmd=digit

    def _ck_exp(self,exp):
        assert isinstance(exp,int),\
            "%s 'exp' argument must be an integer: %s" \
                % (eloc(self,"_ck_exp"),exp)
        assert exp>=0 and exp<=2,\
            "%s 'exp' argument must be an integer between 0 and 2: %s" \
                % (eloc(self,"_ck_exp"),exp)
        self.lme=exp

    def _ck_sign(self,sign):
        assert sign == 0 or sign == 1,\
            "%s 'sign' argument must be either 0 or 1: %s" \
                % (eloc(self,"_ck_sign"),sign)
        self.sign=sign

    def _ck_value(self,value):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer between 0 and 255: %s" \
                % (eloc(self,"_ck_byte"),value)
        assert value>=0 and value<64,\
            "%s 'value' argument must be between 0 and 255: %s" \
                % (eloc(self,"_ck_byte"),value)
        self.bits=value

    # Decode the +6 information of an interchange format.  The first byte of the
    # interchange format is supplied, namely bits 0-7 of the encoded value as an
    # integer.
    def decode(self,value):
        raise NotImplementedError("%s subclass %s must provide the decode() method"\
            % (eloc(self,"decode"),self.__class__.__name__))

    def encode(self,sign,digit,exp=None):
        raise NotImplementedError("%s subclass %s must provide the encode() method"\
            % (eloc(self,"encode"),self.__class__.__name__)) 


# Number with a small decimal digit format
# FMT  b0  b1  b2  b3  b4  b5  B6 +           LMD          LME     b6     b7+
#  0   S   x   x   x   x   x   .        4(b3)+2(b4)+b5    b1,b2    <---RBE--->
class plus6_fmt0(plus6_format):
    format=0
    is_mask =0b000000
    set_mask=0b000000
    sc_scl=None

    @classmethod
    def cls_init(cls):
        cls.sc_cls={4:scomb32,8:scomb64,16:scomb128}

    def __init__(self,debug=False):
        super().__init__(number=True,debug=debug)

    def decode(self,value):
        self._ck_value(value)

        self.lmd = value & 0b111 # Isolate the left most digit of the significand
        v = value >> 3
        self.lme = v & 0b11      # Isolate the left two digits of the biased exponent
        v = v >> 2
        self.sign=v & 0b1        # Isolate the sign

        self.number=True

    def encode(self,sign,digit,exp=None):
        self._ck_sign(sign)
        self._ck_exp(exp)
        self._ck_sdigit(digit)

        v = digit

        # Add the biased exponent's high-order bits
        e = (self.lme & 0b11) << 3
        v = v | e
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"encode",module=this_module)
                print("%s %s two left most exp bits added at bits 1,2: %s" \
                    % (cls_str,plus6_format.p6_binary(v),self.lme))

        # Add the sign
        v = v | self.sign << 5
        if __debug__:
            if self.debug:
                print("%s %s sign added at bit 0: %s" \
                    % (cls_str,plus6_format.p6_binary(v),self.sign))

        # Add the left most significand digits
        v = v | self.lmd
        if __debug__:
            if self.debug:
                print("%s %s LMD added at bits 3-5: %s" \
                    % (cls_str,plus6_format.p6_binary(v),self.lmd))

        # Add id mask (includes the exponent bits)
        v = v | self.set_mask
        if __debug__:
            if self.debug:
                print("%s %s add id bits: %s" \
                    % (cls_str,plus6_format.p6_binary(v),self.set_mask))

        self._ck_value(v)    # Check the result and set self.bits


# Number with a large decimal digit
# FMT  b0  b1  b2  b3  b4  b5  B6 +           LMD          LME     b6     b7+
#  1   S   1   1   x   x   x   .              8+b5        b3,b4    <---RBE--->
class plus6_fmt1(plus6_format):
    format=1
    is_mask =0b011000
    set_mask=0b011000
    sc_cls=None

    @classmethod
    def cls_init(cls):
        cls.sc_cls={4:scomb32,8:scomb64,16:scomb128}

    def __init__(self,debug=False):
        super().__init__(number=True,debug=debug)

    def decode(self,value):
        self._ck_value(value)

        self.lmd = 8 + (value & 0b1)
        v = value >> 1
        self.lme = v & 0b11
        v = v >> 4
        self.sign= v & 0b1

        self.number=True

    def encode(self,sign,digit,exp=None):
        self._ck_sign(sign)
        self._ck_exp(exp)
        self._ck_ldigit(digit)

        # Add the left-most large significand digit
        v = digit - 8

        # Add the biased exponent's high-order bits
        e = (exp & 0b11) << 1
        v = v | e

        # Add the sign
        v = v | sign << 5

        # Add the id mask (includes the exponent)
        v = v | self.set_mask

        self._ck_value(v)


# Inifinity format
# FMT  b0  b1  b2  b3  b4  b5  B6 +           LMD          LME     b6     b7+
#  2   S   1   1   1   1   0   x            Infinity               <-resered->
class plus6_fmt2(plus6_format):
    format=2
    is_mask =0b011111
    set_mask=0b011110
    sc_cls=None

    @classmethod
    def cls_init(cls):
        cls.sc_cls={4:scomb32_infinity,8:scomb64_infinity,16:scomb128_infinity}

    def __init__(self,debug=False):
        super().__init__(infinity=True,debug=debug)

    def decode(self,value):
        self._ck_value(value)

        self.sign = ( value >> 5 ) & 0b1

    def encode(self,sign,digit,exp=None,debug=False):
        self._ck_sign(sign)

        v = sign << 5
        v = v | self.set_mask

        self._ck_value(v)


# Not a Number (NaN) format
# FMT  b0  b1  b2  b3  b4  b5  B6 +           LMD          LME     b6     b7+
#  3   S   1   1   1   1   1   x              NAN                  Q/S   payload
class plus6_fmt3(plus6_format):
    format=3
    is_mask =0b011111
    set_mask=0b011111
    sc_cls=None

    @classmethod
    def cls_init(cls):
        cls.sc_cls={4:scomb32_nan,8:scomb64_nan,16:scomb128_nan}

    def __init__(self,debug=False):
        super().__init__(nan=True,debug=debug)

    def decode(self,value):
        self._ck_value(value)

        self.sign = ( value >> 5 ) & 0b1

    def encode(self,sign,digit=None,debug=False):
        self._ck_sign(sign)

        v = sign << 5
        v = v | self.set_mask

        self._ck_value(v)


# This is the base class for the combination field.  Arguments are supplied by the
# subclass
# Instance Arguments:
#   max_comb The maximum value of the entire combination field
#   shift    an integer representing the number of bits by which the combination
#            filed must be shifted right to isolate the first six bits.
#   rbebits  The number of 
class scomb(object):

    # These class attributes are compupted by the classmethod cls_init()
    size=None      # Size of the sign plus combination fields in bits
    be_max=None    # Maximum biased exponent
    dpd_cls=None   # dpd sublclass for decoding this object
    max_comb=None  # Maximum value of the combination field
    nan_mask=None  # NaN reserved mask in bit 7 and beyond (and its maximum)
    rbe_bits=None  # Size of the remaining biased exponent in bits
    rbe_mask=None  # Mask that isolates the rbe field (and is the max rbe)
    snan_mask=None # Mask that isolates the signaling NaN flag in bit 6

    # Display class information for each dpd interchange format
    @staticmethod
    def info():
        for cls in [scomb32_number,scomb32_infinity,scomb32_nan,
                    scomb64_number,scomb64_infinity,scomb64_nan,
                    scomb128_number,scomb128_infinity,scomb128_nan]:
            cls.cls_str()

    # Initialize the conbination subclasses
    @staticmethod
    def init():
        for cls in [scomb32_number, scomb32_infinity, scomb32_nan,
                    scomb64_number, scomb64_infinity, scomb64_nan,
                    scomb128_number,scomb128_infinity,scomb128_nan]:
            cls.cls_init()

    # Initialize the subclass class attributes.
    # Method Argument:
    #   size    Size of the combination field, without the sign field, in bits
    @classmethod
    def cls_init(cls,size):
        sz=size+1            # Add 1 to combination field for the sign
        shift=sz-6
        cls.rbe_bits=shift
        rbe_mask=(2**shift)-1
        cls.nan_mask=(2**(shift-1)-1)
        cls.snan_mask=1 << (shift-1)
        cls.rbe_mask=rbe_mask
        cls.size=sz
        cls.max_comb=(2**sz)-1
        cls.be_max=(0b10<<shift) | rbe_mask

    # Display class related information
    @classmethod
    def cls_str(cls,string=False):
        s="%s-bit Format Sign + Combination Fields: %s\n" % (cls.size,cls.__name__)
        s="%s    max sign + combination: %05X (%s)\n" % (s,cls.max_comb,cls.max_comb)
        s="%s    remaining biased exponent size: %s\n" % (s,cls.rbe_bits)
        s="%s    remaining biased exponent mask: %05X (%s)\n" \
            % (s,cls.rbe_mask,cls.rbe_mask)
        s="%s    biased exp max: %05X (%s)\n" % (s,cls.be_max,cls.be_max)
        s="%s    NaN reserved mask: %05X\n" % (s,cls.nan_mask)
        s="%s    SNaN mask: %05X" % (s,cls.snan_mask)
        if string:
            return s
        print(s)

    # Creates a scomb object for decoding the S+C fields
    # Method Arguments:
    #   value   An integer representing the S+C bits of the encoded representation
    #   length  The storage size of the value being decoded.
    @staticmethod
    def decode_format(value,length):
        p6=value >> cls.rbe_bits
        p6_cls = plus6_format.decode_format(p6)
        fo=p6_cls()
        fo.decode(p6)
        try:
            sc = f.sc_cls[length]
        except KeyError:
            raise ValueError("scomb.decode_format() - "
                "decode length must be 4, 8 or 16: %s" % (length)) from None
        return sc(p6=p6)

    def __init__(self,length,number=False,nan=False,infinity=False,p6=None,\
                 debug=False):
        self.debug=debug

        # Access the class attributes
        cls=self.__class__
        self.size=cls.size
        self.be_max=cls.be_max
        self.dpd_cls=cls.dpd_cls
        self.max_comb=cls.max_comb
        self.nan_mask=cls.nan_mask
        self.rbe_bits=cls.rbe_bits
        self.rbe_mask=cls.rbe_mask
        self.snan_mask=cls.snan_mask

        # Set the instance attributes
        self.length=length      # Length of storage format in bytes
        self.number=number      # Whether this is a number
        self.nan=nan            # Whather this ia not a number
        self.infinity=infinity  # Whether this is an infinity
        self.p6=p6              # plus6_format object.

        # This attribute is provided by the decode() method or calculated by the
        # encode() method
        self.bits=None

        # These attributes are 
        self.sign=None         # Sign of the number
        self.exponent=None     # Biased exponent
        self.signed_exp=None   # Signed (Unbiased exponent) or biased exponent
        self.lmd=None          # Left-most digit of the significand
        self.reserved=None     # NaN or Infinity reserved field
        self.snan=None         # Signaling NaN flag

        # Decoded signed (Unbiased exponent) or biased exponent depending upon 
        # whether decode called with a bias or 0, respectively
        self.exp=None

    def __str__(self):
        typ="?"
        if self.number:
            typ="Number"
        elif self.nan:
            if self.snan is None:
                snan="?"
            elif self.snan is False:
                snan="Q"
            elif self.snan is True:
                snan="S"
            typ="%sNaN" % snan
        elif self.infinity:
            typ="Infinity"
        if self.bits is None:
            bits="None"
        else:
            bits="%05X" % self.bits
        s="%s-bit S+C %s - %s: sign: %s  LMD: %s BEXP: %s  Reserved: %s" \
            % (self.length*8,typ,bits,self.sign,self.lmd,self.exponent,self.reserved)
        return "%s\n    %s" % (s,self.p6) 

    def _ck_digit(self,digit):
        assert isinstance(digit,int),\
            "%s 'digit' argument must be an integer: %s" \
                % (eloc(self,"_ck_digit"),digit)
        assert digit>=0 and digit<=9,\
            "%s 'digit' argument must be an integer between 0 and 9: %s" \
                % (eloc(self,"_ck_digit"),digit)
        self.lmd=digit

    def _ck_exp(self,exp):
        assert isinstance(exp,int),\
            "%s 'exp' argument must be an integer: %s" \
                % (eloc(self,"_ck_exp"),exp)
        assert exp>=0 and exp<=self.be_max,\
            "%s 'exp' argument must be an integer between 0 and %s: %s" \
                % (eloc(self,"_ck_exp"),self.be_max,exp)
        self.exponent=exp

    def _ck_inf_resv(self,reserved):
        assert isinstance(reserved,int),\
            "%s 'reserved' argument must be an integer: %s" \
                % (eloc(self,"_ck_exp"),reserved)
        assert reserved>=0 and reserved<=self.rbe_mask,\
            "%s 'reserved' argument must be an integer between 0 and %s: %s" \
                % (eloc(self,"_ck_exp"),self.rbe_mask,exp)
        self.reserved=reserved

    def _ck_nan_resv(self,reserved):
        assert isinstance(reserved,int),\
            "%s 'reserved' argument must be an integer: %s" \
                % (eloc(self,"_ck_exp"),reserved)
        assert reserved>=0 and reserved<=self.nan_mask,\
            "%s 'reserved' argument must be an integer between 0 and %s: %s" \
                % (eloc(self,"_ck_exp"),self.nan_mask,exp)
        self.reserved=reserved

    def _ck_sign(self,sign):
        assert sign == 0 or sign == 1,\
            "%s 'sign' argument must be either 0 or 1: %s" \
                % (eloc(self,"_ck_sign"),sign)
        self.sign=sign

    def _ck_value(self,value):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer: %s" \
                % (eloc(self,"_ck_value"),self.value)
        assert value>=0 and value<=self.max_comb,\
            "%s 'value' argument must be in the range 0-%s: %s" \
                % (eloc(self,"_ck_value"),self.max_comb,value)
        self.bits=value

    # Method returns the plus6 format class for a given value.
    def _decode_format(self,value):
        # Note: this sequence is required to ensure the format checks start with 
        # the most restrictive bits settings to the least
        for fmt in [plus6_fmt3,plus6_fmt2,plus6_fmt1]:
            if fmt.isFormat(value):
                return fmt
        # If one of the preceeding formats is not recognized, then it must be
        # format 0.
        return plus6_fmt0

    def _decode_infinity(self,value):
        self.bits=value
        if self.p6:
            self.sign=self.p6.sign
        else:
            p6_bits=value >> self.rbe_bits
            self.p6=plus6_fmt2()
            self.p6.decode(p6_bits)
            self.sign=self.p6.sign
        self.reserved=value & self.rbe_mask

    def _decode_nan(self,value):
        self.bits=value
        if self.p6:
            self.sign=self.p6.sign
        else:
            p6_bits=value >> self.rbe_bits
            self.p6=plus6_fmt3()
            self.p6.decode(p6_bits)
            self.sign=self.p6.sign
        self.snan = (value & self.snan_mask) == self.snan_mask
        self.reserved = value & self.nan_mask

    def _decode_number(self,value,bias=0):
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_decode_number",module=this_module)
                print("%s bias:%s value:%s" % (cls_str,bias,\
                    dpd.bit_str(value,self.size)))
        self.bits=value
        if self.p6:
            p6=self.p6
        else:
            p6_bits = value >> self.rbe_bits
            p6_cls  = plus6_format.decode_format(p6_bits)
            if __debug__:
                if self.debug:
                    print("%s p6 class: %s" % (cls_str,p6_cls.__name__))
            p6=p6_cls(debug=self.debug)
            p6.decode(p6_bits)
            self.p6=p6
        self.sign=p6.sign
        self.lmd=p6.lmd
        lme=self.p6.lme

        exp = lme << self.rbe_bits
        if __debug__:
            if self.debug:
                print("%s LME %s: shifted left %s bits: %s" \
                    % (cls_str,lme,self.rbe_bits,dpd.bit_str(exp,self.rbe_bits+2)))
        rbe = value & self.rbe_mask
        if __debug__:
            if self.debug:
                print("%s RBE %s: as bits: %s" \
                    % (cls_str,rbe,dpd.bit_str(rbe,self.rbe_bits+2)))
        self.exponent= exp | rbe
        if __debug__:
            if self.debug:
                print("%s Biased exponent: %s as bits: %s" \
                    % (cls_str,self.exponent,\
                        dpd.bit_str(self.exponent,self.rbe_bits+2)))
        self.exp=self.exponent-bias
        if __debug__:
            if self.debug and (bias != 0):
                print("%s Signed exponent: %s" % (cls_str,self.exp))

    # Returns the plus6 format class for a given digit
    def _encode_format(self,digit):
        return plus6_format.needsFormat(digit)

    def _encode_infinity(self):
        p6_cls=self._encode_format("infinity")
        p6=p6_cls()
        p6.encode(self.sign,None)
        self.p6=p6              # First 6 bits are in self.p6.bits

        bits = self.p6.bits << self.rbe_bits
        self.bits = bits | self.reserved

    def _encode_nan(self):
        p6_cls=self._encode_format("nan")
        p6=p6_cls()
        p6.encode(self.sign,None)
        self.p6=p6              # First 6 bits are in self.p6.bits

        bits = self.p6.bits << self.rbe_bits
        if self.snan:
            bits = bits | self.snan_mask
        self.bits = bits | self.reserved

    def _encode_number(self):
        p6_cls=self._encode_format(self.lmd)
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_encode_number",module=this_module)
                print("%s p6 format for left most significand digit %s: %s" \
                    % (cls_str,self.lmd,p6_cls.__name__))
                print("%s Biased exponent: %s as bits %s" % (cls_str,self.exponent,\
                    dpd.bit_str(self.exponent,self.rbe_bits+2)))
        p6=p6_cls(debug=self.debug)
        exph_bits = self.exponent >> self.rbe_bits
        exp_rbe = self.exponent & self.rbe_mask
        if __debug__:
            if self.debug:
                print("%s high order two biased exponent bits: %s" \
                    % (cls_str,dpd.bit_str(exph_bits,2)))
                print("%s RBE exponent as %s bits: %s" % (cls_str,self.rbe_bits,\
                    dpd.bit_str(exp_rbe,self.rbe_bits)))

        p6.encode(self.sign,self.lmd,exp=exph_bits)
        self.p6=p6

        bits = self.p6.bits << self.rbe_bits
        if __debug__:
            if self.debug:
                print("%s %s P6" % (cls_str,dpd.bit_str(bits,self.size)))
                print("%s %s RBE" % (cls_str,dpd.bit_str(exp_rbe,self.size)))
        self.bits = bits | exp_rbe
        if __debug__:
            if self.debug:
                print("%s %s Final S+C" % (cls_str,dpd.bit_str(self.bits,self.size)))

    def decode(self,value,bias=0):
        raise NotImplementedError("%s subclass %s must provide decode() method" \
            % (eloc(self,"decode"),self.__class__.__name__))

    def encode(self,sign,*pos,**kwds):
        raise NotImplementedError("%s subclass %s must provide encode() method" \
            % (eloc(self,"decode"),self.__class__.__name__))


class scomb32(scomb):

    # Initialize the 32-bit format combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init(11)

    def __init__(self,number=False,nan=False,infinity=False,p6=None,debug=False):
        super().__init__(4,number=number,nan=nan,infinity=infinity,p6=p6,debug=debug)


class scomb64(scomb):

    # Initialize the 64-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init(13)

    def __init__(self,number=False,nan=False,infinity=False,p6=None,debug=False):
        super().__init__(8,number=number,nan=nan,infinity=infinity,p6=p6,debug=debug)


class scomb128(scomb):

    # Initialize the 128-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init(17)

    def __init__(self,number=False,nan=False,infinity=False,p6=None,debug=False):
        super().__init__(16,number=number,nan=nan,infinity=infinity,p6=p6,\
            debug=debug)


class scomb32_number(scomb32):

    # Initialize the 32-bit format combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=num32

    def __init__(self,p6=None,debug=False):
        super().__init__(number=True,p6=p6,debug=debug)

    def decode(self,value,bias=0):
        self._decode_number(value,bias=bias)

    def encode(self,sign,digit,exp):
        self._ck_sign(sign)           # Sets self.sign if valid
        self._ck_digit(digit)         # Sets self.lmd if valid
        self._ck_exp(exp)             # Sets self.exponent if valid
        self._encode_number()


class scomb32_infinity(scomb32):

    # Initialize the 32-bit format combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=inf32

    def __init__(self,p6=None,debug=False):
        super().__init__(infinity=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_infinity(value)

    def encode(self,sign,reserved=0):
        self._ck_sign(sign)           # Sets self.sign if valid
        self._ck_inf_resv(reserved)   # Sets self.reserved if valid
        self._encode_infinity()


class scomb32_nan(scomb32):

    # Initialize the 32-bit format combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=nan32

    def __init__(self,p6=None,debug=False):
        super().__init__(nan=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_nan(value)

    def encode(self,sign,signaling=False,reserved=0):
        self._ck_sign(sign)            # Sets self.sign if valid
        self.snan = signaling == True  # Sets the NaN signaling flag
        self._ck_nan_resv(reserved)    # Sets self.reserved if valid
        self._encode_nan()


class scomb64_number(scomb64):

    # Initialize the 64-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=num64

    def __init__(self,p6=None,debug=False):
        super().__init__(number=True,p6=p6,debug=debug)

    def decode(self,value,bias=0):
        self._decode_number(value,bias=bias)

    def encode(self,sign,digit,exp):
        self._ck_sign(sign)           # Sets self.sign if valid
        self._ck_digit(digit)         # Sets self.lmd if valid
        self._ck_exp(exp)             # Sets self.exponent if valid
        self._encode_number()


class scomb64_infinity(scomb64):

    # Initialize the 64-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=inf64

    def __init__(self,p6=None,debug=False):
        super().__init__(infinity=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_infinity(value)

    def encode(self,sign,reserved=0):
        self._ck_sign(sign)          # Sets self.sign if valid
        self._ck_inf_resv(reserved) # Sets self.reserved if valid
        self._encode_infinity()


class scomb64_nan(scomb64):

    # Initialize the 64-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=nan64

    def __init__(self,p6=None,debug=False):
        super().__init__(nan=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_nan(value)

    def encode(self,sign,signaling=False,reserved=0):
        self._ck_sign(sign)            # Sets self.sign if valid
        self.snan = signaling == True  # Sets the NaN signaling flag
        self._ck_nan_resv(reserved)    # Sets self.reserved if valid
        self._encode_nan()


class scomb128_number(scomb128):

    # Initialize the 128-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=num128

    def __init__(self,p6=None,debug=False):
        super().__init__(number=True,p6=p6,debug=debug)

    def decode(self,value,bias=0):
        self._decode_number(value,bias=bias)

    def encode(self,sign,digit,exp):
        self._ck_sign(sign)           # Sets self.sign if valid
        self._ck_digit(digit)         # Sets self.lmd if valid
        self._ck_exp(exp)             # Sets self.exponent if valid
        self._encode_number()


class scomb128_infinity(scomb128):

    # Initialize the 128-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=inf128

    def __init__(self,p6=None,debug=False):
        super().__init__(infinity=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_infinity(value)

    def encode(self,sign,reserved=0):
        self._ck_sign(sign)     # Sets self.sign if valid
        self._ck_inf_resv(reserved) # Sets self.reserved if valid
        self._encode_infinity()


class scomb128_nan(scomb128):

    # Initialize the 128-bit format sign and combination field attributes
    @classmethod
    def cls_init(cls):
        super().cls_init()
        cls.dpd_cls=nan128

    def __init__(self,p6=None,debug=False):
        super().__init__(nan=True,p6=p6,debug=debug)

    def decode(self,value):
        self._decode_nan(value)

    def encode(self,sign,signaling=False,reserved=0):
        self._ck_sign(sign)            # Sets self.sign if valid
        self.snan = signaling == True  # Sets the NaN signaling flag
        self._ck_nan_resv(reserved)    # Sets self.reserved if valid
        self._encode_nan()


#
# +-------------------------------------------+
# |                                           |
# |   Decimal Floating Point Declet Objects   |
# |                                           |
# +-------------------------------------------+
#

# These classes support declet encoding and decoding.  They are reusable and store
# no data related to the actual declet.  Such declet specific information is
# contained in the separate declet class and subclasses.  Each class is instantiated
# once and used by the declet class itself.

class declet_format(object):
    # Mask for setting a bit in the declet indexed by bit number
    bits=[0b1000000000,
          0b0100000000,
          0b0010000000,
          0b0001000000,
          0b0000100000,
          0b0000010000,
          0b0000001000,
          0b0000000100,
          0b0000000010,
          0b0000000001,]

    # Convert a declet into a string of binary digits.
    @staticmethod
    def declet_binary(declet):
        b=bin(declet & 0b1111111111)   # Convert declet to a binary literal string
        b=b[2:]                        # Drop off the initial 0b
        b="0000000000%s" % b           # Add high-order zeros
        b=b[-10:]                      # Right justify the 10 binary digits
        return b                       # Return the string

    # These values are extablished for each subclass object by means of the
    # cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    ismask=None      # Mask to detect a declet format

    # Returns the set_mask for a specific format
    @classmethod
    def cls_init(cls,number,ldm,f6,f7=None,f8=None,f3=None,f4=None):
        bit=declet_format.bits
        l1=mask=0
        ismask=bit[6]

        if f6:
            mask = mask | bit[6]
            l1 = 0b100
            ismask = ismask | bit[7]|bit[8]
            if f7:
                mask= mask | bit[7]
                l1 = l1 | 0b010
            if f8:
                mask = mask |bit[8]
                l1 = l1 | 0b001
            if l1==0b111:
                ismask = ismask | (bit[3]|bit[4])
                if f3:
                    mask = mask | bit[3]
                if f4:
                    mask = mask | bit[4]
        cls.set_mask=mask
        cls.number=number
        cls.ismask=ismask
        cls.ldmask=ldm

    @classmethod
    def cls_str(cls,string=True):
        s="%s: Format: %s LDM:%s  set_mask: %s  ismask: %s" \
            % (cls.__name__,cls.number,cls.ldmask,\
                declet_format.declet_binary(cls.set_mask),\
                    declet_format.declet_binary(cls.ismask))
        if string:
            return s
        print(s)

    @classmethod
    def isCanonical(cls,declet):
        return True

    # Returns True if the supplied declet is in the format supported by this class, 
    # False otherwise.
    @classmethod
    def isFormat(cls,declet):
        return (declet & cls.ismask) == cls.set_mask

    def __init__(self):
        pass

    # Check whether the values are three integers between 0 and 9 inclusive.
    # Returns: None if valid
    # Exceptions:
    #   ValueError if any of the three values are invalid
    def _ck_decimals(self,values):
        if not isinstance(values,list):
            raise ValueError("%s 'values' argument must be a list: %s" \
                % (eloc(self,"_ck_decimals"),values))
        if len(values)!=3:
            raise ValueError(\
                "%s 'values' argument must be a list of three elements: %s" \
                    % (eloc(self,"_ck_decimals",),values))

        # Check each element in the list
        for n,d in enumerate(values):
            if not isinstance(d,int):
                raise ValueError(\
                    "%s 'values' argument element %s not an integer: %s" \
                        % (eloc(self,"_ck_decimals"),n+1,values))
            if d<0 or d>9:
                raise ValueError(\
                    "%s 'values' argument element %s out of range (0-9): %s" \
                        % (eloc(self,"_ck_decimals"),n+1,values))

    # Check that the supplied declet if valid.
    # Returns: None if valid
    # Exceptions:
    #   ValueError if the declet is not valid.
    def _ck_declet(self,declet):
        if not isinstance(declet,int):
            raise ValueError("%s 'argument' must be an integer: %s" \
                % (eloc(self,"_ck_declet",),declet))
        if declet < 0 or declet > 1023:
            raise ValueError("%s 'declet' argument out of range (0-1023): %s" \
                % (eloc(self,"_ck_declet"),declet))

    # Ensure the complete declet has been processed by the decode() method
    # Returns: None if complete declet was processed
    # Excpetions:
    #   AssertionError if the declet has only been partially processed.
    def _ck_wip(self,wip,declet):
        assert wip == 0,\
            "%s DFP declet %s not completely decoded, wip: %s" \
                % (eloc(self,"_ck_wip"),bin(declet),bin(wip))

    # Convert a declet (integer) into a list of decimal values.
    #
    # This is from IEEE 754-2008, Section 3.5.2
    #
    # B0 B1 B2 B3 B4 B5 B6 B7 B8 B9
    #                                     D(1)             D(2)             D(3)
    # x  x  x  ?  ?  x  ?  ?  ?  x
    # .  .  .  x  x  .  0  x  x  .   4(b0)+2(b1)+b2   4(b3)+2(b4)+b5   4(b7)+2(b8)+b9
    # .  .  .  x  x  .  1  0  0  .   4(b0)+2(b1)+b2   4(b3)+2(b4)+b5        8+b9
    # .  .  .  x  x  .  1  0  1  .   4(b0)+2(b1)+b2        8+b5        4(b3)+2(b4)+b9
    # .  .  .  x  x  .  1  1  0  .        8+b2        4(b3)+2(b4)+b5   4(b0)+2(b1)+b9
    # .  .  .  0  0  .  1  1  1  .        8+b2             8+b5        4(b0)+2(b1)+b9
    # .  .  .  0  1  .  1  1  1  .        8+b2        4(b0)+2(b1)+b5        8+b9
    # .  .  .  1  0  .  1  1  1  .   4(b0)+2(b1)+b2        8+b5             8+b9
    # .  .  .  1  1  .  1  1  1  .        8+b2             8+b5             8+b9
    #
    # By mapping the bits used to decode each decimal value into the bit matrix
    # this table is derived.
    #
    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 0  D1 D1 D1 D2 D2 D2 0  D3 D3 D3  4(b0)+2(b1)+b2  4(b3)+2(b4)+b5  4(b7)+2(b8)+b9
    # 1  D1 D1 D1 D2 D2 D2 1  0  0  D3  4(b0)+2(b1)+b2  4(b3)+2(b4)+b5      8+b9
    # 2  D1 D1 D1 D3 D3 D2 1  0  1  D3  4(b0)+2(b1)+b2        8+b5      4(b3)+2(b4)+b9
    # 3  D3 D3 D1 D2 D2 D2 1  1  0  D3       8+b2       4(b3)+2(b4)+b5  4(b0)+2(b1)+b9
    # 4  D3 D3 D1 0  0  D2 1  1  1  D3       8+b2             8+b5      4(b0)+2(b1)+b9
    # 5  D2 D2 D1 0  1  D2 1  1  1  D3       8+b2       4(b0)+2(b1)+b5      8+b9
    # 6  D1 D1 D1 1  0  D2 1  1  1  D3  4(b0)+2(b1)+b2        8+b5          8+b9
    # 7  0  0  D1 1  1  D2 1  1  1  D3       8+b2             8+b5          8+b9
    #
    # Based upon the second matrix it becomes clear how the packing is performed.
    # For a value of 8 or 9, only one bit is required to differentiate the values.
    # The high-order bit (a 1 in both cases), can be inferred.  The least significant
    # bit (LSB) is always in the same positions.  For D1, the LSB is always encoded
    # into bit 2.  For D2, the LSB is always encoded into bit 5.  For D3, the LSB is
    # always encoded into bit 9.
    #
    # Decimal digits requiring three of less bits for an encoding are considered
    # small decimal degits.  Decimal digits requiring four encoding bits are
    # considered large decimal digits.  The flags identify which of the three
    # decimal digits is small and which are large.  When encoding is being performed,
    # the type of digit dictates into which bits of the declet each decimal digit
    # is encoded and which flags are to be set.  During decoding, the flags are
    # interogated to determine how each digit was encoded and whihc bits of the 
    # declet the encoded digit may be found.
    #
    # Format 7, used when all three decimal digits are large, does not use bits
    # 0 and 1 of the 10-bit declet.  If these two bits are both zero, the declet
    # is considered canonical (as are all of the other 7 formats).  However, if
    # either of these two bits are 1, the declet is considered non-canonical.
    # During decoding the two bits are ignored.
    #
    # Where the intermediate bits (bits 1 and 2 of a single digit) are placed
    # is controlled by the flag fields.  Encoded bit 6 controls the encoding of the
    # flags within the value.  It is the master flag.  When bit 6 is encoded as 0,
    # no implied high-order bit exists for any of the decimal values, so the actual
    # decimal value is encoded in bits 0-2 for D1, bits 3-5 for D2, and bits 7-9
    # for D3.  In this case, all of the decimals fall into the range 0-7.
    #
    # When bit 6 is encoded as a 1, there is some mixture of decimal values greater
    # than 7 and less-than or equal to 7.  The flags dictate where the two
    # higher order bits of values 7 or less are placed in the encoded value for a 
    # specific decimal digit, and varies depending upon the combination.
    #
    # By examining each decimal value and identifying which are greater than 7,
    # the ultimate format can be determined.

    # This method must be supplied by the subclass
    def decode(self,declet):
        raise NotImplementedError("%s subclass %s must supply build() method"\
            % (eloc(self,"build"),self.__class__.__name__))

    # Encode three decimal digist into a 10-bit declet.
    #
    # This is the reverse process of decoding.  Decimal digits between 0 and 7,
    # inclusive are considered small decimal digits.  Small decimal digits can be
    # encoded in three binary bits.  Decimal digits 8 and 0 are considered large
    # decimal digits.  Large decimal digits can be encoded with one bit and the 
    # high order bit of a four bit binary coded decimal is implied to be one.
    #
    # This scheme allows three decimal digits which would normally require 4 bits
    # each in a traditional binary coded decimal, 12 bits total, allows three decimal
    # digits to be encoded in 10 bits total.  A mechanism identifying which decimal
    # digit is small and which is large is required.  This is provided by the 
    # variable number of flag bits.
    #
    # This table identifies which of the three decimal digits is large (indicated
    # by a Y) and which is small (indicated by a N) and the associated flag bit
    # settings apply.  The flag bit settings then dictate into which bits of the 
    # 10-bit declet the small or large decimal digit is encoded.  For consistency
    # each combination of flag bits is assigned a format number.  The format
    # number inplies which subclass is used to encode or decode the specific
    # combination of small and large decimal digits.
    #                                                          Large
    #  FMT   D1   D2   D3    F6  F7  F8  F3  F4  Subclass   digit mask
    #   0    N    N    N     0   .   .   .   .    Format0    000 == 0
    #   1    N    N    Y     1   0   0   .   .    Format1    001 == 1
    #   2    N    Y    N     1   0   1   .   .    Format2    010 == 2
    #   3    Y    N    N     1   1   0   .   .    Format3    100 == 4
    #   4    Y    Y    N     1   1   1   0   0    Format4    110 == 6
    #   5    Y    N    Y     1   1   1   0   1    Format5    101 == 5
    #   6    N    Y    Y     1   1   1   1   0    Format6    011 == 3
    #   7    Y    Y    Y     1   1   1   1   1    Format7    111 == 7
    #
    # There is no apperent pattern to the selection of the number and the values
    # greater than 7.

    # This method must be supplied by the subclass
    def encode(self,values):
        raise NotImplementedError("%s subclass %s must supply build() method"\
            % (eloc(self,"build"),self.__class__.__name__))


class Format0(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(0,0,0)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 0  D1 D1 D1 D2 D2 D2 0  D3 D3 D3  4(b0)+2(b1)+b2  4(b3)+2(b4)+b5  4(b7)+2(b8)+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3  = wip & 0b111
        wip = wip >> 4
        d2  = wip & 0b111
        wip = wip >> 3
        d1  = wip & 0b111
        wip = wip >> 3

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d1 = values[0] & 0b111
        d2 = values[1] & 0b111
        d3 = values[2] & 0b111
        wip =  d1 << 7
        wip = wip | d2 << 4
        wip = wip | d3
        wip = wip| self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format1(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(1,1,1,f7=0,f8=0)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 1  D1 D1 D1 D2 D2 D2 1  0  0  D3  4(b0)+2(b1)+b2  4(b3)+2(b4)+b5      8+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3  = 8 + (wip & 0b1)
        wip = wip >> 4
        d2  = wip & 0b111
        wip = wip >> 3
        d1  = wip & 0b111
        wip = wip >> 3

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d1  = values[0] & 0b111
        wip = d1 << 7
        d2  = values[1] & 0b111
        wip = wip | d2 << 4
        wip = wip | values[2] & 0b1
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format2(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(2,2,1,f7=0,f8=1)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 2  D1 D1 D1 D3 D3 D2 1  0  1  D3  4(b0)+2(b1)+b2        8+b5      4(b3)+2(b4)+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3a = wip & 0b1
        wip = wip >> 4
        d2  = 8 + (wip & 0b1)
        wip = wip >> 1
        d3b = wip & 0b11
        d3  = (d3b << 1) + d3a
        wip = wip >> 2
        d1  = wip & 0b111
        wip = wip >> 3

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        wip = values[0] & 0b111
        wip = wip << 7
        d3  = values[2] & 0b111
        d3a = d3 >> 1
        wip = wip | d3a << 5
        d2  = values[1] & 0b1
        wip = wip | d2 << 4
        wip = wip | d3 & 0b1
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format3(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(3,4,1,f7=1,f8=0)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 3  D3 D3 D1 D2 D2 D2 1  1  0  D3       8+b2       4(b3)+2(b4)+b5  4(b0)+2(b1)+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3a = wip & 0b1
        wip = wip >> 4
        d2  = wip & 0b111
        wip = wip >> 3
        d1  = 8 + (wip & 0b1)
        wip = wip >> 1
        d3b = wip & 0b11
        d3 = (d3b << 1) + d3a
        wip = wip >> 2

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d3 = values[2] & 0b111
        d3a = d3 >> 1
        wip = d3a << 8
        d1  = values[0] & 0b1
        wip = wip | d1 << 7
        d2  = values[1] & 0b111
        wip = wip | d2 << 4
        d3b = d3 & 0b1
        wip = wip | d3b
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format4(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(4,6,1,f7=1,f8=1,f3=0,f4=0)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 4  D3 D3 D1 0  0  D2 1  1  1  D3       8+b2             8+b5      4(b0)+2(b1)+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3a = wip & 0b1
        wip = wip >> 4
        d2  = 8 + (wip & 0b1)
        wip = wip >> 3
        d1  = 8 + (wip & 0b1)
        wip = wip >> 1
        d3b = wip & 0b11
        d3  = (d3b << 1) + d3a
        wip = wip >> 2

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d3 = values[2] & 0b111
        d3a = d3 >> 1
        wip = d3a << 8
        d1  = values[0] & 0b1
        wip = wip | d1 << 7
        d2  = values[1] & 0b1
        wip = wip | d2 << 4
        wip = wip | d3 & 0b1
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format5(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(5,5,1,f7=1,f8=1,f3=0,f4=1)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 5  D2 D2 D1 0  1  D2 1  1  1  D3       8+b2       4(b0)+2(b1)+b5      8+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3  = 8 + (wip & 0b1)
        wip = wip >> 4
        d2a = wip & 0b1
        wip = wip >> 3
        d1  = 8 + (wip & 0b1)
        wip = wip >> 1
        d2b = wip & 0b11
        d2  = (d2b << 1) + d2a
        wip = wip >> 2

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d2  = values[1] & 0b111
        d2a = d2 >> 1
        wip = d2a << 8
        d1  = values[0] & 0b1
        wip = wip | d1 << 7
        d2b = d2 & 0b1
        wip = wip | d2b << 4
        d3  = values[2] & 0b1
        wip = wip | d3
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format6(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(6,3,1,f7=1,f8=1,f3=1,f4=0)

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 6  D1 D1 D1 1  0  D2 1  1  1  D3  4(b0)+2(b1)+b2       8+b5            8+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3  = 8 + (wip & 0b1)
        wip = wip >> 4
        d2  = 8 + (wip & 0b1)
        wip = wip >> 3
        d1  = wip & 0b111
        wip = wip >> 3

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d1  = values[0]
        wip = d1 << 7
        d2  = values[1] & 0b111
        wip = wip | d2 << 4
        d3  = values[2] & 0b1
        wip = wip | d3
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


class Format7(declet_format):

    # These values are extablished for this subclass by the cls_init() class method.
    ldmask=None      # The large digit mask associated with this class
    number=None      # Format number
    set_mask=None    # Flag bit set mask
    is_mask=None     # Mask to detect a declet format

    @classmethod
    def cls_init(cls):
        super().cls_init(7,7,1,f7=1,f8=1,f3=1,f4=1)

    @classmethod
    def isCanonical(cls,declet):
        return declet & 0b1100000000 == 0

    def __init__(self):
        super().__init__()

    #FMT B0 B1 B2 B3 B4 B5 B6 B7 B8 B9       D(1)            D(2)            D(3)
    #    x  x  x  F3 F4 x  F6 F7 F8  x
    # 7  0  0  D1 1  1  D2 1  1  1  D3       8+b2             8+b5          8+b9
    def decode(self,declet):
        if __debug__:
            self._ck_declet(declet)

        wip = declet
        d3  = 8 + (wip & 0b1)
        wip = wip >> 4
        d2  = 8 + (wip & 0b1)
        wip = wip >> 3
        d1  = 8 + (wip & 0b1)
        wip = wip >> 3

        result=[d1, d2, d3]

        if __debug__:
            self._ck_wip(wip,declet)
            self._ck_decimals(result)

        return result

    def encode(self,values):
        if __debug__:
            self._ck_decimals(values)

        d1  = values[0] & 0b1
        wip = d1 << 7
        d2  = values[1] & 0b1
        wip = wip | d2 << 4
        d3  = values[2] & 0b1
        wip = wip | d3
        wip = wip | self.set_mask

        if __debug__:
            self._ck_declet(wip)

        return wip


# The declet object, decodes or encodes a declet.
# Instance Argument:
#   value   If value is an integer, it is taken to be an encoded declet to be decoded.
#           The value is treated as an unsigned integer in range 0 <= value <= 1024
#           and is converted to a list of three decimal values, each an integer.
#           If value is a string or list, it is taken as decimal values to be encoded.
#           The argument must contain one, two, or three elements.  Each element 
#           must be either a character between '0' and '9', or an integer between 0 
#           and 9.  The decimal values are encoded into densely-packed encoding
#           resulting in an unsigned integer.
#           If None, the value is supplied by the encode or decode methods.  
#           Defaults to None.
# Exception:
#    ValueError     is raised if the value is of an invalid type or out of range.  It
#                   may also be raised during declet encoding or decoding, but
#                   should not occur.
#    AssertionError occurs when an internal error is detected.
class declet(object):
    # Declet format classes indexed by format number.  
    formats=[]    # The list is created by declet.cls_init() class method

    @classmethod
    def cls_init(cls):
        lst=[]
        # By LDM     0       1       2       3       4       5       6       7
        for f in [Format0,Format1,Format2,Format6,Format3,Format5,Format4,Format7]:
            f.cls_init()
            cls.formats.append(f())

    @classmethod
    def cls_str(cls,string=False):
        fmts=cls.formats
        s=""
        for f in cls.formats:
            s="%s\n%s" % (s,f.cls_str(string=True))
        if string:
            return s
        print(s)

    # Returns the declet_format object that decodes the presented declet
    @staticmethod
    def decode_format(dec):
        for format in declet.formats:
            if format.isFormat(dec):
                return format

    # Returns the declet_format object that supports the large digit mask value 
    # for the presented set of three digits. 
    @staticmethod
    def encode_format(digits):
        assert isinstance(digits,list) and len(digits)==3,\
           "%s 'digits' argument must be a list of length three: %s" \
               % (eloc(self,"encode_format"),values)

        format=0
        if digits[0]>7:
            format = format | 0b100
        if digits[1]>7:
            format = format | 0b010
        if digits[2]>7:
            format = format | 0b001

        return declet.formats[format]

    def __init__(self,value=None):
        self._declet=None       # Encoded declet
        self.decimals=None      # Decoded decimals
        self.canonical=False    # Canonical
        self.format=None        # Declet format

        if value is None:
            return
        elif isinstance(value,int):
            self.decode(value)
        elif isinstance(value,str):
            self.encode(value)
        elif isinstance(value,list):
            self.encode(value)
        else:
            raise ValueError(\
                "%s 'value' argument must be an integer, string or list: %s" \
                    % (eloc(self,"__init__"),value))

    def __str__(self):
        if self._declet is None:
            bin="??????????"
        else:
            bin=declet_format.declet_binary(self._declet)
        if self.decimals is None:
            dec="[?,?,?]"
        else:
            dec=self.decimals
        if self.format is None:
            can="?"
        else:
            can=self.canonical
        return "DFP: declet fmt %s: can:%s  %s decimals: %s" \
            % (self.format,can,bin,self.decimals)


    # Treat the encoded declet as a read-only property.  Only use the declet property
    # when retreiving the declet.  This ensures only canonical declets are returned.
    #
    # Note: To access the instantiated declet directly (regardless of whether it is
    # canononical or not) use the raw() method.
    @property
    def declet(self):
        if self.canonical:
            return self._declet
        elif self._declet is None:
            return None  
        return self._declet & 0b0011111111

    # The declet property may only be set when the the object is instantiated or
    # by use of the decode() or encode() methods post instantiation.
    @declet.setter
    def declet(self,value):
        raise NotImplementedError("%s declet property may not be set directly"\
            % eloc(self,"declet.setter"))

    # Decode a declet into a list of three decimal digits
    # Exceptions:
    #   ValueError       if the declet is invalid
    #   AssertionError   if an internal error is detected
    def decode(self,dec):
        format=declet.decode_format(dec)
        decimals=format.decode(dec)
        self.canonical=format.isCanonical(dec)
        self.format=format.number
        self.decimals=decimals
        self._declet=dec

    # Encode a list of one, two, or three decimal digits into a declet.
    # Exceptions:
    #   ValueError      if an invalid encoding string or list of digits or a problem
    #                   occurs during declet encoding.
    #   AssertionError  if an internal error is detected
    def encode(self,values):
        decimals=[]
        if isinstance(values,str):
            if len(values)<1 or len(values)>3:
                raise ValueError(\
                    "%s 'values' string argument must contain 1, 2, 3 "
                        "characters: '%s'" \
                            % (eloc(self,"encode"),values))
            for n,c in enumerate(values):
                try:
                    decimals.append(int(c))
                except ValueError:
                    raise ValueError("%s 'values' string argument character %s "
                        "out of range ('0'-'9'): '%s'" \
                             % (eloc(self,"encode"),n+1,values)) from None

        elif isinstance(values,list):
            if len(values)<1 or len(values)>3:
               raise ValueError(\
                   "%s 'values' list argument must contain 1, 2, 3 elements: %s" \
                        % (eloc(self,"encode"),values))
            for n,d in enumerate(values):
                if not isinstance(d,int):
                    raise ValueError(\
                        "%s 'values' list argument element %s not an integer: %s" \
                             % (eloc(self,"encode"),n+1,values))
                if d<0 or d>9:
                    raise ValueError(\
                        "%s 'values' list element %s out of range (0-9): %s" \
                             % (eloc(self,"encode"),n+1,values))
                decimals.append(d)
                 
        else:
            raise ValueError("%s 'values' argument must be a string or list: %s" \
                % (eloc(self,"encode"),values))

        while len(decimals)<3:
            decimals.append(0)

        format=declet.encode_format(decimals)
        dec=format.encode(decimals)
        self.canonical=True
        self.format=format.number
        self._declet=dec
        self.decimals=decimals

    # Returns the original canonical or non-canonical declet
    def raw(self):   
        return self._declet

    # Returns the decimal values of the declet with BCD encoding
    # For example:
    #   [5, 6, 7] returns the integer: 0x567 (or decimal 1,383)
    def to_bcd(self):
        if self.decimals is None:
            raise ValueError("decimal digits unavailable")
        return int("%s%s%s" % tuple(self.decimals),16)

    # Returns the declet as a three character string of hex digits 
    def to_hex(self):
        return "%03X" % self._declet

    # Returns the decimal values as an unsigned binary value.
    # For example
    #   [5, 6, 7] returns the integer 567 (hexadecimal 0x237)
    def to_int(self):
        if self.decimals is None:
            raise ValueError("decimal digits unavailable")
        return int("%s%s%s" % tuple(self.decimals),10)

# Establish class specific related values
declet.cls_init()


# These classes support encoding and decoding of the trailing significand field.
# Digit encoding requires exactly the number of digits supported by the interhange
# format.
#
# Note: Adjustments to the digits and exponent for scientific (Right-Units View) or
# integer (Left-Units View) must be applied before the encoding is performed.
class tsig(object):
    def __init__(self,declets):
        self.declets=declets   # The number of declets in the significand
        self.digits=declets*3  # The number of digits in the significand
        
        self.do=[]             # List of declet object used for encoding/decoding
        self.bits=None         # The trailing significand as an integer
        self.decimals=None     # The trailing significand as a list of digits

    def __str__(self):
        cls=self.__class__.__name__
        spaces=" " * len(cls)
        s=    "%s bits:   %s" % (cls,self._format())
        s="%s\n%s digits: %s" % (s,spaces,self.decimals)
        return s

    # Checks the list or tuple of digits for validity
    # Method Argument
    #   digits   A list or tuple of digits matching the interchage format's 
    #            trailing significand.
    # Exception:
    #   ValueError raised if the 'digits' argument is invalid
    def _ck_digits(self,digits):
        if not isinstance(digits,(list,tuple)):
            raise ValueError("%s 'digits' argument must be a list or tuple: %s" \
                % (eloc(self,"_ck_digits"),digits))
        if len(digits)!=self.digits:
            raise ValueError("%s 'digits' argument must contain %s elements: %s" \
                % (eloc(self,"_ck_digits"),self.digits,len(digits)))
        for n,d in enumerate(digits):
            if not isinstance(d,int):
                raise ValueError(\
                    "%s element %s of 'digits' argument %s must be an integer: %s" \
                        % (eloc(self,"_ck_digits"),n,digits,d))
            if d<0 or d>9:
                raise ValueError(\
                     "%s element %s of 'digits' argument %s must be a in "
                         "range 0-9: %s" % (eloc(self,"_ck_digits"),n,digits,d))

    # Decode the Densely-Packed Decimal encoded as specified by the supplied integer.
    # Returns:
    #   a list of integer digits.  The length will exactly match the number of
    #   digits encoded by the interchange format.
    def decode(self,bits):
        assert isinstance(bits,int),\
            "%s 'bits' argument must be an integer: %s" % (eloc(self,"decode"),bits)
        self.bits=declets=bits

        # This loop extracts declets from the right to the left within the
        # trailing significand.  This is the reverse order in which the declets
        # were originally encoded.  See Note below.
        do=[]
        for n in range(self.declets):
            dlet=declet()
            dlet.decode( declets & 0b1111111111 )
            do.append(dlet)
            declets = declets >> 10

        # Note: the preceding loop decodes from low order declets to high order
        # declets.  While the order within a declet is correct, this has the effect
        # of placing the low-order declet digits in the high-order position of the
        # list.  This flips the declet order allowing the next loop to put the digits
        # in the proper sequence, namely the same order in which they were encoded.
        do.reverse()
        self.do=do

        # Now we can put the digits themselves in the proper sequence by restoring
        # the declet sequence.
        digits=[]
        for d in do:
            digits.extend(d.decimals)
        self.decimals=digits

        return digits

    # Encode the list or tuple of integer digits in the range of 0-9 into the 
    # Densely-Packed Decimal encoding.  The number of digits supplied must match the
    # capacity of the interchange format into which the trailing significand is
    # encoded.
    # Returns:
    #   an integer representing the encoding.
    def encode(self,digits,debug=False):
        if __debug__ or debug:
            self._ck_digits(digits)

        self.decimals=digits  
        bits=0
        do=[]

        # Encode declets from right to left.
        for n in range(0,self.digits,3):
            declet_digits=digits[n:n+3]
            dlet=declet()
            do.append(dlet)
            dlet.encode(declet_digits)
            d=dlet.declet
            bits = bits << 10
            bits = bits | d

        self.bits=bits
        self.do=do
        return bits

    def info(self,string=False):
        s=""
        for n,d in enumerate(self.do):
            s="%s[%02d] %s\n" % (s,n,d)
        s=s[:-1]
        if string:
            return s
        print(s)

    # Returns the trailing significand bits as a hex string
    def _format(self):
        raise NotImplementedError("%s subclass %s must provide _format() method" \
            % (eloc(self,"_format"),self.__class__.__name__))


class tsig32(tsig):
    def __init__(self):
        super().__init__(2)

    def _format(self):
        # The significand is 20 bits long: 5 hex digits is 20 bits
        if self.bits is None:
            return "None"
        return "%05X" % self.bits


class tsig64(tsig):
    def __init__(self):
        super().__init__(5)

    def _format(self):
        # The significand is 50 bits long: 13 hex digit is 52 bits
        if self.bits is None:
            return "None"
        return "%013X" % self.bits


class tsig128(tsig):
    def __init__(self):
        super().__init__(11)

    def _format(self):
        # The significand is 110 bits long: 28 hex digit is 112 bits
        if self.bits is None:
            return "None"
        return "%028X" % self.bits


#
# +-------------------------------------------------------------+
# |                                                             |
# |   DFP Densely Packed Decimal Interchange Encoding Objects   |
# |                                                             |
# +-------------------------------------------------------------+
#

class dpd_values(object):
    # List of possible flags used by ctx_info() method
    flags=[decimal.InvalidOperation,  # ?
           decimal.FloatOperation,    # F
           decimal.DivisionByZero,    # 0
           decimal.Overflow,          # >
           decimal.Underflow,         # <
           decimal.Subnormal,         # S
           decimal.Inexact,           # I
           decimal.Rounded,           # R
           decimal.Clamped]           # C

    def __init__(self,prec=0,bias=0,emax=0,emin=0,\
                 luv=False,rounding=None,clamp=1,traps=None):
        self.clamp=clamp    # Whether decimal context should clamp or not
        self.traps=traps    # Traps use for context
        self.prec=prec      # Precision of this format (unsigned integer)

        # Amount by which Emax should be adjusted depending upoon clamping
        if clamp:
            adj=prec-1
        else:
            adj=0             
        self.emax=emax      # Maximum LUV scientific view exponent (signed integer)
        self.ctx_emax=emax+adj           # LUV decimal.Context Emax value
        self.emin=emin      # Minimum LUV scientific view exponent (signed integer)
        self.ebias=bias                  # LUV Bias (unsigned integer)
        self.ebmax=emax+bias             # Maximum LUV Biased exponent (unsigned)
        self.etiny=emin-prec+1           # LUV Etiny (signed integer)
        self.etop=self.ctx_emax-prec+1   # LUV Etop (signed integer)

        # Maximum RUV integer view exponent (signed integer)
        self.qmax=emax-prec+1
        self.ctx_qmax=self.qmax+adj      # RUV decimal.Context Emax value
        # Minimum RUV integer view exponent (signed integer)
        self.qmin=emin-prec+1            # RUV Emin value
        self.qbias=bias+prec-1           # RUV Bias (unsigned integer)
        self.qtiny=self.qmin-prec+1      # RUV Etiny (signed integer)
        self.qtop=self.ctx_qmax-prec+1   # RUV Etop (signed integer)
        self.qbmax=self.qmax+self.qbias  # Maximum RUV biased exponent

        # Context built by subclass.  Remember the bias for the context
        self.sci=None   # Whether scientific (True) or integer (False)
        if luv:
            self.sci=True
            self.ctx=self.ectx(rounding=rounding,clamp=clamp)
            self.bias=self.ebias
            self.maxbias=self.ebmax
            self.minbias=self.emin
            self.tiny=self.etiny
        else:
            self.sci=False
            self.ctx=self.qctx(rounding=rounding,clamp=clamp)
            self.bias=self.qbias
            self.maxbias=self.qbmax
            self.minbias=self.qmin
            self.tiny=self.etiny

    def __str__(self):
        pfx="%s prec: %s - " % (self.__class__.__name__,self.prec)
        sp=" " * len(pfx)
        s=    "%sLUV bias:%s maxbias:%s emax:%s emin:%s ctx_emax:%s etop:%s etiny:%s" \
            % (pfx,self.ebias,self.ebmax,self.emax,self.emin,\
                self.ctx_emax,self.etop,self.etiny)
        s="%s\n%sRUV bias:%s maxbias:%s qmax:%s qmin:%s ctx_qmax:%s etop:%s etiny:%s" \
            % (s,sp,self.qbias,self.qbmax,self.qmax,self.qmin,\
                self.ctx_qmax,self.qtop,self.qtiny)
        return s

    # Convert the context flags settings into a string
    def ctx_flags(self):
        sflags=self.ctx.flags
        chars="?F0><SIRC"
        fs=""
        for n,flag in enumerate(dpd_values.flags):
            flag=sflags[flag]
            if flag:
                f=chars[n]
            else:
                f="."
            fs="%s%s" % (fs,f)
        return fs

    # Provide information about the current context setting
    def ctx_info(self,string=False):
        ctx=self.ctx
        s="%s" % ctx
        etiny=ctx.Etiny()
        etop=ctx.Etop()
        fs=self.ctx_flags()
        s="%s\n    Etiny: %s  Etop: %s  flags: %s" % (s,etiny,etop,fs)
        if string:
            return s
        print(s)

    # Return the scientific view (LUV) decimal.Context object
    # Method Argument:
    #   rounding  The rounding mode used by this context.  If None or omitted, the
    #             rounding mode will be decimal.ROUND_HALF_EVEN
    def ectx(self,rounding=None,clamp=1):
        return decimal.Context(prec=self.prec,rounding=rounding,\
            Emin=self.emin,Emax=self.ctx_emax,capitals=1,clamp=clamp,traps=self.traps)

    # Provide information about the context
    def info(self,string=False):
        s=self.__str__()
        if string:
            return s
        print(s)

    # Reurn the integer view (RUV) decimal.Context object
    # Method Argument:
    #   rounding  The rounding mode used by this context.  If None or omitted, the
    #             rounding mode will be decimal.ROUND_HALF_EVEN
    def qctx(self,rounding=None,clamp=1):
        return decimal.Context(prec=self.prec,rounding=rounding,\
            Emin=self.qmin,Emax=self.ctx_qmax,capitals=1,clamp=clamp,traps=self.traps)


# Each of the following threee subclasses has the same instance arguments:
#   luv       Specify True to create a scientific view (LUV) context.  Specify False
#             to create an integer view (RUV) context.  Defaults to False.
#   rounding  Specify the rounding mode used by the context.  Defaults to None
#             which implies decimal.ROUND_HALF_EVEN is used.

# Establish the context for the 32-bit interchange format
class dpd32(dpd_values):
    def __init__(self,luv=False,rounding=None,clamp=1,traps=None):
        super().__init__(prec=7,bias=95,emax=96,emin=-95,\
            luv=luv,rounding=rounding,clamp=clamp,traps=traps)


# Establish the context for the 64-bit interchange format
class dpd64(dpd_values):
    def __init__(self,luv=False,rounding=None,clamp=1,traps=None):
        super().__init__(prec=16,bias=383,emax=384,emin=-383,\
            luv=luv,rounding=rounding,clamp=clamp,traps=traps)


# Establish the context for the 128-bit interchange foramt
class dpd128(dpd_values):
    def __init__(self,luv=False,rounding=None,clamp=1,traps=None):
        super().__init__(prec=34,bias=6143,emax=6144,emin=-6143,\
            luv=luv,rounding=rounding,clamp=clamp,traps=traps)


class dpd(object):

    # These attributes are set by the dpd subclass cls_init() method
    length=None       # Length of the encoded value in bits
    sc_cls=None       # scomb subclass associated with this class
    sc_len=None       # Length of the sign and combination fields in bits
    sig_digits=None   # Number of trailing significand digits
    sig_len=None      # Trailing significand length in bits
    sig_mask=None     # Mask for isolating trailing significand
    sig_cls=None      # The trailing significand class for this format
    values_i=None     # dpd integer view subclass for the interchange format size
    values_s=None     # dpd scientifc view subclass for the interchange format size

    # These attributes are set by the dpd.init() method
    inf_lengths=None  # Dictionary mapping infinity lengths to dpd subclass
    nan_lengths=None  # Dictionary mapping NaN lengths to dpd subclass
    num_lengths=None  # Dictionary mapping number lengths to dpd subclass

    @staticmethod
    def bit_str(bits,length):
        assert bits.bit_length() <= length,\
            "%s - dpd.bit_str() - value (%s) requires %s bits, too large for %s" \
                % (this_module,bits.bit_length(),length)

        b=bin(bits)                    # Convert value to a binary literal string
        b=b[2:]                        # Drop off the initial 0b
        pad="0" * length               # Create left padding of zeros
        b="%s%s" % (pad,b)             # Pad with bits on the left
        end=-length
        b=b[end:]                      # Right justify the 10 binary digits
        return b                       # Return the string

    @staticmethod
    def context(prec):
        return decimal.Context(prec=prec,capitals=1,clamp=1)

    # This method returns the dpd class required to decode an interchange formatted
    # bytes sequence into a Decimal object.  The length of the sequence implies
    # the interchange format length used.
    @staticmethod
    def decode_cls(byte0,length):
        assert isinstance(byte0,int),\
            "%s - dpd.decode_cls() - 'byte0' argument must be an integer: %s"\
                % (this_module,byte0)

        p6 = byte0 >> 2
        p6_cls=plus6_format.decode_format(p6)
        p6o=p6_cls()
        p6o.decode(p6)
        try:
            if p6o.number:
                cls=dpd.num_lengths[length]
            elif p6o.infinity:
                cls=dpd.inf_lengths[length]
            elif p6o.nan:
                cls=dpd.nan_lengths[length]
            else:
                raise ValueError("%s - dpd.decode_cls() - invalid DFP type: %s" \
                    % (this_module,p6o))
        except KeyError:
            raise ValueError(\
                "%s - dpd.decode_cls() - invalid interchange format length: %s" \
                    % (this_module,length)) from None

        return (cls,p6o)   # Return the dpd subclass and the plus6_format object

    # This method returns the class required to encode a Decimal object with a 
    # specific interchange format length.
    @staticmethod
    def encode_cls(value,length):
        assert isinstance(value,(DFP_Number,decimal.Decimal)),\
            "dpd.new - 'value' argument must be a decimal.Decimal or DFP_Number "\
                "object: %s" % value
        assert isinstance(length,int),\
            "dpd.new - 'length' argument must be an integer: %s" % length

        try:
            if isinstance(value,DFP_Number) or value.is_finite():
                cls=dpd.num_lengths[length]
            elif value.is_nan():
                cls=dpd.nan_lengths[length]
            elif value.is_infinite():
                cls=dpd.inf_lengths[length]
            else:
                raise ValueError("%s - dpd.new_cls() - 'value' argument "
                    "unrecognized: %s" % (this_modue,value))
        except KeyError:
            raise ValueError("%s dpd.new_cls() - 'value' argument length must be "
                "4, 8, or 16: %s" %(this_module,length)) from None

        return cls

    # Return a decimal.Decimal object from a series of bytes
    # Method Arguments:
    #   value      A list of bytes, length implied by the length of the bytes
    #   luv        Whether scientific view (True) or integer view (False)
    #   byteorder  Specify 'big' or 'little' depending upon the byteorder of the
    #              bytes.    Defaults to 'little'.
    @staticmethod
    def from_bytes(value,luv=False,byteorder="little",debug=False):
        assert isinstance(value,(bytes,bytearray)),\
            "%s - dpd.from_bytes() - 'value' argument must be a bytes or bytearray "\
                "sequence: %s" % (this_module,value)

        if byteorder=="little":
            byte0=value[-1]
        elif byteorder=="big":
            byte0=value[0]
        else:
            raise ValueError("%s - dpd.from_bytes() - 'byteorder' argument must "\
                "be 'big' or 'little': %s" % (this_module,byteorder))

        cls,p6o=dpd.decode_cls(byte0,len(value))
        if __debug__:
            if debug:
                print("%s - dpd.from_bytes - decode class: %s" % (this_module,cls)) 
        dpdo=cls(luv=luv,value=value,p6=p6o,byteorder=byteorder,debug=debug)
        # We can now fully decode the DFP value.  Its type, length and subclass have
        # been determined
        dpdo.decode()
        return dpdo

    # Display class information for each dpd interchange format
    @staticmethod
    def info():
        for cls in [num32,inf32,nan32,num64,inf64,nan64,num128,inf128,nan128]:
            cls.cls_str()

    # Initialize the dpd subclasses
    @staticmethod
    def init():
        for cls in [num32,inf32,nan32,num64,inf64,nan64,num128,inf128,nan128]:
            cls.cls_init()

        dpd.inf_lengths={4:inf32,8:inf64,16:inf128}
        dpd.nan_lengths={4:nan32,8:nan64,16:nan128}
        dpd.num_lengths={4:num32,8:num64,16:num128}

    # Return a series of bytes from a decimal.Decimal object
    # Method Arguments:
    #    value     A decimal.Decimal object
    #    length    Number of bytes to create from the value
    #    byteorder Specify 'big' or 'little' depending upon the byteorder of the
    #              bytes being created.  Defaults to 'little'.
    @staticmethod
    def to_bytes(value,length,byteorder="little"):
        print("dpd.to_bytes() - value= %r %s" % (value,value))
        cls=dpd.encode_cls(value,length)    # Figure out the dpd subclass for Decimal
        v=cls(value)
        v.encode()
        return v.binary(byteorder=byteorder)

    @classmethod
    def cls_init(cls,length,sc_cls):
        cls.length     = length
        cls.sc_cls     = sc_cls
        cls.sc_len     = cls.sc_cls.size
        cls.sig_len    = cls.length - cls.sc_len
        cls.sig_digits = ( cls.sig_len // 10 ) * 3
        cls.sig_mask   = 2**(length-cls.sc_len)-1

    @classmethod
    def cls_str(cls,string=False):
        s="%s size: %s  sc_len: %s  sig_len: %s  sig digits: %s  scomb: %s" \
            % (cls.__name__,cls.length,cls.sc_len,cls.sig_len,cls.sig_digits,\
                cls.sc_cls.__name__)
        if string:
            return s
        print(s)

    def __init__(self,length,luv=False,value=None,p6=None,byteorder="little",\
                 debug=False):
        self.debug=debug
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"__init__",module=this_module)
                print("%s value= %r %s" \
                    % (cls_str,value,value))
        self.length=length     # Length of encoded value in bytes (from subclass)

        # Pull down the class attributes
        cls=self.__class__
        self.length=cls.length         # Length of the interchange format in bits
        self.size=self.length // 8     # Lenfth of the interchage format in bytes
        self.sc_cls=cls.sc_cls         # The scomb subclass associated with this cls
        self.sc_len=cls.sc_len         # The size of the scomb field in bits
        self.sig_digits=cls.sig_digits # Number of traling signincand digits 
        self.sig_len=cls.sig_len       # Length of the trailing significand in bits
        self.sig_mask=cls.sig_mask     # Mask for isolating trailing significand
        self.sig_cls=cls.sig_cls       # Trailing significand class
        if luv:
            self.values=cls.values_s   # dpd_values integer view subclass object
        else:
            self.values=cls.values_i   # dpd_values scientific view subclass object
        if __debug__:
            if self.debug:
                print("%s format attributes: %s" % (cls_str,self.values))
        self.bias=self.values.bias     # Scientific (left-units-view) bias

        self.bits=None         # The value as bits in an integer
        self.blist=None        # The value as a bytes or bytearray sequence
        self.deco=None         # The value as a decimal.Decimal object
        self.p6=None           # Already decoded first six bits of the sequence
        # Note: decoding the first 6 bits of the byte sequence is required to 
        # determine the type of DFP value being decoded.  The type determines the 
        # subclass.  As long as we have already gone through the process of decoding
        # it, we might as well remember it for later use.

        self.sign=None         # Sign of the number  (0 == +, 1 == -)
        self.digits=None       # list of digits, each digit being an integer
        self.exponent=None     # Signed exponent of a number
        self.reserved=None     # Reserved area of Infinity or NaN

        if isinstance(value,DFP_Number):
            # DFP_Number object to be encoded
            self._extract_number(value)
        elif isinstance(value,decimal.Decimal):
            # decimal.Decimal object to be encoded
            self.deco=value
            self._extract(value.as_tuple())
        elif isinstance(value,(bytes,bytearray)):
            self.blist=value       # bytes sequence to be decoded
            self.p6=p6             # Decoded first six bits of the value
            self.bits=int.from_bytes(value,byteorder=byteorder,signed=False)

    # This method separates the signficand from the S+C fields
    # Returns:
    #   A tuple: tuple[0] the S+C decoded as an scomb object.
    #            tuple[1] the trailing significand as an integer
    def _comps(self,bits,bias=0):
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_comps",module=this_module)
                print("%s bits: %s" % (cls_str,hex(bits)))
                print("%s sc class: %s" % (cls_str,self.sc_cls.__name__))
        sc=bits >> self.sig_len       # The S+C fields as an integer
        tsig=bits & self.sig_mask     # The trailing significand as an integer
        if __debug__:
            if self.debug:
                print("%s TSIG mask: %s" % (cls_str,hex(self.sig_mask)))
                print("%s TSIG:      %s" % (cls_str,hex(tsig)))

        # Create scomb object for the S+C fields
        sco=self.sc_cls(p6=self.p6,debug=self.debug)
        sco.decode(sc,bias=bias)      # Decode the S+C fiels
        return (sco,tsig)    # Return the separated and partially decoded fields

    # This method separates the payload from the S+C fields
    # Returns:
    #   A tuple: tuple[0] the S+C decoded as an scomb object.
    #            tuple[1] the payload as an integer
    def _compsp(self,bits):
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_comps",module=this_module)
                print("%s bits: %s" % (cls_str,hex(bits)))
                print("%s sc class: %s" % (cls_str,self.sc_cls.__name__))
        sc=bits >> self.sig_len       # The S+C fields as an integer
        payload=bits & self.sig_mask  # The payload as an integer
        if __debug__:
            if self.debug:
                print("%s PALD mask: %s" % (cls_str,hex(self.sig_mask)))
                print("%s PALD:      %s" % (cls_str,hex(payload)))

        # Create scomb object for the S+C fields
        sco=self.sc_cls(p6=self.p6,debug=self.debug)
        sco.decode(sc)          # Decode the S+C fiels
        return (sco,payload)    # Return the separated and partially decoded fields

    # Create a decimal.Decimal object based upon sourced values
    def _create(self):
        raise NotImplementedError("%s subclass %s must provide _create() method"\
            % (eloc(self,"_create"),self.__class__.__name__))

    # Extracts information from a decimal.Decimal object
    def _extract(self,value):
        raise NotImplementedError("%s subclass %s must provide _extract() method"\
            % (eloc(self,"_extract"),self.__class__.__name__))

    # Extracts information from a DFP_Number object.  Only supported for finite
    # numbers.
    def _extract_number(self,value):
        raise NotImplementedError("%s subclass %s must provide _extract() method"\
            % (eloc(self,"_extract_number"),self.__class__.__name__))

    def binary(self,byteorder="little"):
        self.blist=self.bits.to_bytes(self.length,byteorder=byteorder)
        return self.blist

    def decode(self,bias=0):
        raise NotImplementedError("%s subclass %s must provide decode() method"\
            % (eloc(self,"decode"),self.__class__.__name__))

    def encode(self,sign,**kwds):
        raise NotImplementedError("%s subclass %s must provide encode() method"\
            % (eloc(self,"encode"),self.__class__.__name__))


class num(dpd):
    def __init__(self,length,luv=False,value=None,p6=None,\
                 byteorder="little",debug=False):
        if debug:
            print("%s length=%s,luv=%s,value=%s,p6=%s,byteorder='%s',debug=%s" \
                % (eloc(self,"__init__",module=this_module),\
                    length,luv,value,p6,byteorder,debug))

        self.exponent=None     # Signed exponent of a number
        self.luv=luv           # Whether scientific (True) or inteber (False) view
        super().__init__(length,luv=luv,value=value,p6=p6,byteorder=byteorder,\
            debug=debug)
        assert self.values.sci is False,\
            "%s DFP number requires integer view - values.sci: %s" \
                % (eloc(self,"__init__",module=this_module),self.values.sci)
        assert self.deco is None or self.deco.is_finite(),\
            "%s 'value' Decimal object must be finite: %s" \
                % (eloc(self,"__init__",module=this_module),self.deco)

    def __str__(self):
        if self.luv:
            view="sci"
        else:
            view="int"
        d=""
        for digit in self.digits:
            d="%s%s" % (d,digit)
        return "DFP number %s view - sign:%s exponent:%s digits:%s" \
            % (view,self.sign,self.exponent,d)

    # Create a Decimal number value
    def _create(self):
        t=(self.sign,tuple(self.digits),self.exponent)
        return decimal.Decimal(t)

    # Extract number data from Decimal named tuple
    def _extract(self,dec):
        self.sign=dec.sign
        self.digits=list(dec.digits)
        self.exponent=dec.exponent
        self.decimal=dec

    # Extract floating point content from a DFP_Number object
    def _extract_number(self,dnum):
        if __debug__:
            if self.debug:
                print("%s %r %s" \
                    % (eloc(self,"_extract_number",module=this_module),dnum,dnum))

        self.sign=dnum.sign
        assert isinstance(dnum.significand,list),\
            "%s dnum.significand must be a list: %s" \
                 % (eloc(self,"_extract_number",module=this_module),\
                     dnum.significand)
        digits=dnum.significand
        self.digits=digits
        if __debug__:
            if self.debug:
                print("%s digits: %s" \
                    % (eloc(self,"_extract_number",module=this_module),\
                        self.digits))

        self.exponent=dnum.exp_int

    # Decode the instantiated sequence of bytes into its sign, exponent and 
    # significand.
    def decode(self):
        sco,tsig=self._comps(self.bits,bias=self.bias)
        tsigo=self.sig_cls()
        tsigo.decode(tsig)

        if __debug__:
            if self.debug:
                cls_str=eloc(self,"decode",module=this_module)
                print("%s %s" % (cls_str,sco))
                print("%s %s" % (cls_str,tsigo))

        # Populate attributes
        self.sign=sco.sign
        self.exponent=sco.exponent-self.bias
        digits=[sco.lmd,]
        digits.extend(tsigo.decimals)
        self.digits=digits

    # Encode the number into its decimal floating point interchange format
    def encode(self,byteorder="little"):
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"encode",module=this_module)
                print("%s digits: %s" % (cls_str,self.digits))

        lmd=self.digits[0]
        significand=self.digits[1:]

        # Encode the S+C field
        sc=self.sc_cls(debug=self.debug)
        bexp=self.exponent+self.bias
        if __debug__:
            if self.debug:
                print("%s exponent:%s bias: %s = biased exponent: %s" \
                    % (cls_str,self.exponent,self.bias,bexp))
                print("%s S+C %s sign:%s LMD:%s bias exp:%s" \
                    % (cls_str,self.sc_cls.__name__,self.sign,lmd,bexp))
        sc.encode(self.sign,lmd,bexp)

        if __debug__:
            if self.debug:
                print("%s scomb: %s length:%s scomb len: %s" % (cls_str,\
                    bin(sc.bits),sc.bits.bit_length(),self.sc_len))

        # Encode the trailing significand
        ts=self.sig_cls()
        ts.encode(significand)

        # Combine the S+C fields and the trailing significand as one large integer
        bits = sc.bits
        bits = bits << self.sig_len
        bits = bits |  ts.bits

        # Convert the one large integer into a sequence of bytes
        self.blist = bits.to_bytes(self.length//8,byteorder=byteorder,signed=False)
        return self.blist


class inf(dpd):
    def __init__(self,length,value=None,p6=None,byteorder="little",debug=False):
        self.reserved=None     # reserved value for an infinity
        super().__init__(length,value=value,p6=p6,\
            byteorder=byteorder,debug=debug)
        assert self.deco is None or self.deco.is_infinite(),\
            "%s 'value' Decimal object must be an infinity: %s" \
                % (eloc(self,"__init__"),self.deco)

    def __str__(self):
        payload=""
        if self.reserved!=0 or self.payload!=0:
            payload=" - sign:%s reserved:0x%X payload:0x%X" \
                % (self.sign,self.reserved,self.payload)
        if self.sign:
            sign="-"
        else:
            sign="+"
        return "DFP %sinf%s" % (sign,payload)

    # Create a Decimal infinity value
    def _create(self):
        if self.sign:
            return decimal.Decimal("-Inf")
        return decimal.Decimal("+Inf")

    # Extract infinity data from Decimal named tuple
    def _extract(self,dec):
        self.sign=dec.sign
        self.digits=list(dec.digits)
        self.decimal=dec

    def decode(self):
        sco,self.payload=self._compsp(self.bits)

        # Populate attributes
        self.reserved=sco.reserved
        self.sign=sco.sign


class nan(dpd):
    def __init__(self,length,value=None,p6=None,byteorder="little",debug=False):
        self.payload=None      # NaN payload value
        self.signaling=False   # Set True if SNaN, False if QNaN
        super().__init__(length,value=value,p6=p6,byteorder=byteorder,debug=debug)

        assert self.deco is None or self.deco.is_nan(),\
            "%s 'value' Decimal object must be NaN: %s" \
                % (eloc(self,"__init__"),value)

    def __str__(self):
        if self.signaling:
            sgnl="s"
        else:
            sgnl="q"
        payload=""
        if self.reserved!=0 or self.payload!=0:
            payload=" - sign:%s reserved:0x%X payload:0x%X" \
                % (self.sign,self.reserved,self.payload)
        if self.sign:
            sign="-"
        else:
            sign="+"
        return "DFP %s%snan%s" % (sign,sgnl,payload)

    # Create A Decimal Nan value
    def _create(self):
        if self.signaling:
            n="n"
        else:
            n="N"
        if self.digits is None:
            dig=(0,)
        else:
            dig=tuple(self.digits)
        t=(self.sign,dig,n)
        return decimal.Decimal(t)

    # Extract NaN data from Decimal named tuple
    def _extract(self):
        self.sign=dec.sign
        self.digits=list(dec.digits)
        exp=dec.exponent
        self.signaling = exp == "N"
        self.decimal=dec

    def decode(self):
        sco,self.payload=self._compsp(self.bits)
        self.sign=sco.sign
        self.signaling=sco.snan
        self.reserved=sco.reserved


class num32(num):

    @classmethod
    def cls_init(cls):
        super().cls_init(32,scomb32_number)
        cls.values_i=dpd32(luv=False)
        cls.values_s=dpd32(luv=True)
        cls.sig_cls=tsig32

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(4,luv=luv,value=value,p6=p6,byteorder=byteorder,\
            debug=debug)


class inf32(inf):

    @classmethod
    def cls_init(cls):
        super().cls_init(32,scomb32_infinity)
        cls.values_i=dpd32(luv=False)
        cls.values_s=dpd32(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",\
                 debug=False):
        super().__init__(4,value=value,p6=p6,byteorder=byteorder,debug=debug)


class nan32(nan):

    @classmethod
    def cls_init(cls):
        super().cls_init(32,scomb32_nan)
        cls.values_i=dpd32(luv=False)
        cls.values_s=dpd32(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(4,value=value,p6=p6,byteorder=byteorder,debug=debug)


class num64(num):

    @classmethod
    def cls_init(cls):
        super().cls_init(64,scomb64_number)
        cls.values_i=dpd64(luv=False)
        cls.values_s=dpd64(luv=True)
        cls.sig_cls=tsig64

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,luv=luv,value=value,p6=p6,byteorder=byteorder,\
            debug=debug)


class inf64(inf):

    @classmethod
    def cls_init(cls):
        super().cls_init(64,scomb64_infinity)
        cls.values_i=dpd64(luv=False)
        cls.values_s=dpd64(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,value=value,p6=p6,byteorder=byteorder,debug=debug)


class nan64(nan):

    @classmethod
    def cls_init(cls):
        super().cls_init(64,scomb64_nan)
        cls.values_i=dpd64(luv=False)
        cls.values_s=dpd64(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,value=value,p6=p6,byteorder=byteorder,debug=debug)


class num128(num):

    @classmethod
    def cls_init(cls):
        super().cls_init(128,scomb128_number)
        cls.values_i=dpd128(luv=False)
        cls.values_s=dpd128(luv=True)
        cls.sig_cls=tsig128

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,luv=luv,value=value,p6=p6,byteorder=byteorder,\
            debug=debug)


class inf128(inf):

    @classmethod
    def cls_init(cls):
        super().cls_init(128,scomb128_infinity)
        cls.values_i=dpd128(luv=False)
        cls.values_s=dpd128(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,value=value,p6=p6,byteorder=byteorder,debug=debug)


class nan128(nan):

    @classmethod
    def cls_init(cls):
        super().cls_init(128,scomb128_nan)
        cls.values_i=dpd128(luv=False)
        cls.values_s=dpd128(luv=True)
        cls.sig_cls=None

    def __init__(self,luv=False,value=None,p6=None,byteorder="little",debug=False):
        super().__init__(8,value=value,p6=p6,byteorder=byteorder,debug=debug)


# Intialize the dpd, scomb and plus6 classes
plus6_format.init()
scomb.init()
dpd.init()


# A DFP Number
class DFP_Number(fp.FP_Number):

    # Create a DFP_Number object from a decimal.Decimal object
    # Method Argument:
    #   format  The interchange format being constructed.  May be an integer
    #           specifying the number of bits in the interchange format (32, 64, or
    #           128) or a subclass of dpd_values (dpd32, dpd64, dpd128).
    #   dec     a decimal.Decimal object
    # Returns:
    #   a subclass of mdfp from which the interchange format may be constructed
    # Excpetion:
    #   ValueError if the deciaml.Decimal object is subnormal or the format is
    #              invalid
    @staticmethod
    def from_decimal(format,dec,rounding=12):
        assert isinstance(dec,decimal.Decimal),\
            "%s - mdfp.from_decimal() - 'dec' argument must be a decimal.Decimal "\
                "object: %s" % (this_module,dec)

        # Extract components from the decimal.Decimal object
        tup=dec.as_tuple()
        sign=tup.sign
        digits=list(tup.digits)
        exp=tup.exponent

        if dec.is_finite():
            dfp=number(format)
            dfp.value(sign,integer=digits,exp=exp,rounding=rounding)
        elif dec.is_zero():
            dpf=number(format)
            dfp.value(sign,integer="0",exp=0,rounding=rounding)
        elif dec.is_infinite():
            dfp=infinity(format,rounding=rounding)
            dfp.value(sign)
        elif dec.is_qnan():
            dfp=qnan(format)
            dfp.value(sign,payload=digits)
        elif dec.is_snan():
            dfp=snan(format)
            dfp.value(sign,payload=digits)
        elif dec.is_subnormal():
            raise ValueError("%s - mdfp.decimal() - 'dec' argument is subnormal: %s"\
                % (this_module,dec))
        else:
            raise ValueError("%s - mdfp.decimal() - 'dec' argument object is not "
                "supported: %s" % (this_module,dec))

        return dfp

    def __init__(self,sign,integer=None,fraction=None,exp=0,rounding=12,\
                 attr=None,debug=False):
        assert isinstance(attr,fp.FPAttr),\
            "%s 'attr' argument must be a fp.FPAttr object: %s" \
                % (eloc(self,"__init__",module=this_module),attr)

        self.debug=debug                # Remember debug flag
        self.attr=attr                  # The attributes of this DFP format
        self.length=attr.length         # Length in bytes
        self.prec=attr.prec             # Significand precision of the format
        self.size=self.length * 8       # Size in bits
        self.sci=attr.sci     # whether scientific (True) or integer (False) view

        # Supplied by arugment validation methods.  
        self.sign=sign             # Sign of the value
        self.r_exp=exp             # Signed exponent or unsigned reserve value
        self.signal=None           # Signaling state of the value
        self.rounding=None         # Finite number rounding mode

        self.left=[]               # Digits left of the decimal point
        self.left_zeros=0          # Number of zeros left of the decimal point
        self.left_not_zero=0       # First digit left of the decimal point not zero

        self.right=[]              # Digits right of the decimal point
        self.right_zeros=0         # Number of zeros right of the decimal point
        self.right_not_zero=0      # First digit right of the decimal point not 0

        self.payload=[]            # Special value digit payload
        self.payload_zeros=0       # Number of zero digits in payload
        self.payload_not_zero=0    # First digit not zero

        # Validate arguments...
        self._ck_left(integer)          # Digits left of the decimal point
        self._ck_right(fraction)        # Digits right of the decimal point
        self._ck_sign(sign)             # Number sign
        self._ck_exponent(exp)          # Signed exponent
        self._ck_rounding(rounding)     # Rounding ID

        # Scientific view of the coefficient and signed exponent.
        # See _coefficient() method
        self.digits=None           # Coefficient digits
        self.exp_int=None          # Integer view exponent
        self._coefficient(debug=debug)  # Create integer view of coefficient

        # See _interchage() method
        self.significand=None      # Significand being encoded

        super().__init__(self.sign,self.exp_int,self.digits,10,self.attr,\
            rounding=self.rounding,debug=debug)

        # Detect overflow, underflow or subnomralization of input floating point
        # datum.
        self._detect_conditions()

    def __str__(self):
        return "%s sign:%s exp:%s prec:%s digits:%s coef:%s significand: %s "\
            "rmode: %s" % (self.__class__.__name__,\
                self.sign,self.exp_int,len(self.digits),self.digits,self.coef,\
                    self.significand,self.rmode)

    # Check a string or list of decimal digits.
    # Method Argument:
    #   digits     A list to be validated or string for conversion to a list
    # Returns:
    #   a tuple - tuple[0] a list of decimal digits
    #             tuple[1] number of leading zero digits encountered
    #             tuple[2] first non-zero digit (may be None)
    # Exception:
    #   ValueError  if the string or list does not contain decimal digits or the
    #               argument is not a list or string.
    def _ck_digits(self,digits):
        if isinstance(digits,str):
            return self._str_to_list(digits)
        elif isinstance(digits,list):
            return self._ck_list(digits)
        else:
            raise ValueError()

    # Check the string or integer exponent and if valid set self.r_exp as a signed
    # integer.
    # Method Argument:
    #    exp   The exponent as an integer or string
    # Exeption:
    #    ValueError  if the string is not a valid decimal value with an optional
    #                sign.
    def _ck_exponent(self,exp):
        if isinstance(exp,str):
            try:
                self.r_exp=int(exp,10)
            except ValueError:
                raise ValueError(\
                    "%s 'exp' argument must be a valid integer string: %s" \
                        % (eloc(self,"_ck_exponent"),exp)) from None
        elif isinstance(exp,int):
            self.r_exp=exp
        else:
            raise ValueError("%s 'exp' argument must be an integer: %s" \
                % (eloc(self,"_ck_exponent"),exp))

    # Check the decimal digits left of the decimal point
    def _ck_left(self,left):
        if left is None:
            self.left=[]
        else:
            try:
                self.left,self.left_zeros,self.left_not_zero=self._ck_digits(left)
            except ValueError:
                raise ValueError(\
                    "%s 'left' argument does not contain decimal digits: %s" \
                        % (eloc(self,"_ck_left"),left)) from None

    # Check that each element of a list is an integer between 0 and 9
    def _ck_list(self,lst):
        if __debug__:
            if self.debug:
                print("%s checking list: %s" \
                    % (eloc(self,"_ck_list",module=this_module),lst))

        zeros=0
        not_zero=None
        for n,digit in enumerate(lst):
            if isinstance(digit,int) and digit >=0 and digit <=9:
                if digit == 0 and not_zero is None:
                    zeros+=1
                else:
                    if not_zero is None:
                        not_zero=n
                continue
            else:
                raise ValueError()

        if __debug__:
            if self.debug:
                print("%s leading zeros: %s" \
                    % (eloc(self,"_ck_list",module=this_module),zeros))
                print("%s first digit not zero: %s" \
                    % (eloc(self,"_ck_list",module=this_module),not_zero))

        return (lst,zeros,not_zero)

    # Check the digit payload
    def _ck_payload(self,payload):
        if payload is None:
            self.payload=[]
        else:
            try:
                self.payload,self.payload_zeros,self.payload_not_zero\
                    =self._ck_digits(payload)
            except ValueError:
                raise ValueError(\
                    "%s 'payload' argument does not contain decimal digits: %s" \
                        % (eloc(self,"_ck_payload"),payload)) from None

    # Check that reserve is an integer >= 9
    def _ck_reserve(self,reserve):
        if isinstance(reserve,int) and reserve >= 0:
            self.r_exp=reserve
            return
        raise ValueError(\
            "%s 'reserve' argument must be an integer >= 0: %s" \
                % (eloc(self,"_ck_reserve"),reserve))

    # Check the decimal digits right of the decimal point
    def _ck_right(self,right):
        if right is None:
            self.right=[]
        else:
            try:
                self.right,self.right_zeros,self.right_not_zero\
                    =self._ck_digits(right)
            except ValueError:
                raise ValueError(\
                    "%s 'right' argument does not contain decimal digits: %s" \
                        % (eloc(self,"_ck_right"),right)) from None

    # Check the rounding mode
    def _ck_rounding(self,rounding):
        if isinstance(rounding,int) and rounding >= 8 and rounding <= 15:
            self.rounding=rounding
            return
        raise ValueError(\
            "%s 'roudning' argument must be an integer between 8 and 15: %s" \
                % (eloc(self,"_ck_rounding"),rounding))

    # Check the sign
    def _ck_sign(self,sign):
        if sign in [0,1]:
            self.sign=sign
        else:
            raise ValueError("%s 'sign' argument must be 0 or 1: %s" \
                % (eloc(self,"_ck_sign"),sign))

    # Check the signaling state
    def _ck_signal(self,signal):
        if signal in [0,1]:
            self.signal=signal
        else:
            raise ValueError("%s 'signal' argument must be 0 or 1: %s" \
                % (eloc(self,"_ck_signal"),signal))

    # Create the scientific view coefficient and exponent from value() method
    # arguments.
    def _coefficient(self,debug=False):
        left=self.left
        right=self.right
        right_places=len(right)
        if __debug__:
            if self.debug:
                e=eloc(self,"_coefficient")
                print("%s left: %s" % (e,left))
                print("%s right: %s" % (e,right))
                print("%s right_places: %s" % (e,right_places))

        # Construct integer view coefficient
        digits=[]
        if left:
            digits.extend(left)
        if right:
            digits.extend(right)
        assert len(digits)>0,\
            "%s left and right combined digits not >0" % eloc(self,"_coefficient")
        if __debug__:
            if self.debug:
                print("%s digits: %s" % (e,digits))
                print("%s self.left_zeros: %s" % (e,self.left_zeros))
                print("%s self.right_not_zero: %s" % (e,self.right_not_zero))
                print("%s len(left): %s" % (e,len(left)))
        self.digits=digits

        # Determine leading zeros of the integer view coefficient
        if self.left_zeros==len(left):
            zeros=len(left)+self.right_zeros
        else:
            zeros=self.left_zeros
        if __debug__:
            if debug:
                print("%s zeros: %s" % (e,zeros))

        # Adjust exponent to account for positions left of the decimal point.
        # The integer view exponent is created
        self.exp_int=self.r_exp-right_places
        if __debug__:
            if self.debug:
                print("%s exp_int: %s" % (e,self.exp_int))

    # This method creates the interchange format fields
    def _interchange(self,debug=False):
        if self.is_special:
            # Special values have their own handling
            return
        self.round(self.prec)
        assert isinstance(self.coef,list),\
            "%s coef must be a list: %s" \
                % (eloc(self,"_interchange",module=this_module),self.digits)
        self.significand=self.coef
        self.exp_int=self.exp
        if __debug__:
            if self.debug:
                print("%s sign:%s exp:%s significand:%s" \
                    % (eloc(self,"_interchange",module=this_module),\
                        self.sign,self.exp_int,self.significand))

        assert isinstance(self.significand,list),\
            "%s significand attribute must be a list: %s" \
                % (eloc(self,"_interchange",module=this_module),self.significand)

    # Convert a string of decimal digits to a list
    # Returns:
    #   a list of integers corresponding to the decimal digits in the string
    # Exception:
    #   ValueError raised if a character in the string is not a decimal digit
    def _str_to_list(self,string):
        if __debug__:
            if self.debug:
                print("%s input string: '%s'" \
                    % (eloc(self,"_str_to_list",module=this_module),string))
        zeros=0
        not_zero=None
        lst=[]
        for n,char in enumerate(string):
            digit=int(char,10)
            if digit==0 and not_zero is None:
                zeros+=1
            else:
                if not_zero is None:
                    not_zero=n
            lst.append(digit)

        if __debug__:
            if self.debug:
                print("%s output list: '%s'" \
                    % (eloc(self,"_str_to_list",module=this_module),lst))
                print("%s leading zeros: %s" \
                    % (eloc(self,"_str_to_list",module=this_module),zeros))
                print("%s first digit not zero: %s" \
                    % (eloc(self,"_str_to_list",module=this_module),not_zero))

        return (lst,zeros,not_zero)
        
    def to_bytes(self,byteorder="big"):
        if self.is_special:
            return fp.FP_Special.to_bytes(self.is_special,byteorder=byteorder)

        cls=dpd.encode_cls(self,self.length)
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"to_bytes",module=this_module)
                print("%s encoding class: %s" % (cls_str,cls.__name__))
        clso=cls(luv=self.sci,value=self,debug=self.debug)
        if __debug__:
            if self.debug:
                print("%s encoding class debug: %s" % (cls_str,clso.debug))
                print("%s %s" % (eloc(self,"to_bytes",module=this_module),clso))

        byts=clso.encode(byteorder=byteorder)
        return byts

    # This method sets the DFP value for the subclass
    def value(self,*pos,**kwds):
        raise NotImplementedError("%s subclass %s must provide value() method" \
            % (eloc(self,"value"),self.__class__.__name__))
        
  # Methods overriding the super class or required by the super class
  
    # This method sets the result when exponent overflow is detected
    # The result is the special value of a signed inifinity
    def _overflow_set(self):
        self._overflow_set_infinity()

    # This method denomalizes a coefficient to allow the signed exponent to become
    # the minimum.
    def _subnormal_set(self):
        self._subnormal_set_default()

    # This method sets the result when the signed exponent is less than tiny
    # The coefficient is set to all zeros and the signed exponent is set to tiny.
    def _underflow_set(self):
        self.coef=[0,] * self.prec
        self.exp=self.attr.min


# The Infinite special value
class infinity(DFP_Number):
    def __init__(format):
        super().__init__(format,1)

    def value(self,sign,payload=None,reserve=0):
        self._ck_sign(sign)
        self._ck_payload(payload)
        self._ck_reserve(reserve)


# The generic Not-a-Number special value
class nan(DFP_Number):
    def __init__(self,format):
        super().__init__(format,-1)

    def value(self,sign,payload=None,reserve=0,signal=0):
        self._ck_sign(sign)
        self._ck_payload(payload)
        self._ck_reserve(reserve)
        self._ck_signal(signal)


# The Quiet Not-a-Number special value
class qnan(DFP_Number):
    def __init__(self,format):
        super().__init__(format)

    def value(self,sign,payload=None,reserve=0):
        super().value(sign,payload=payload,reserve=reserve,signal=0)


# The Signaling Not-a-Number special value
class snan(nan):
    def __init__(self,format):
        super().__init__(format)

    def value(self,sign,payload=None,reserve=0):
        super().value(sign,payload=payload,reserve=reserve,signal=1)


class DFP_Special(fp.FP_Special):
    def __init__(self):
        super().__init__()  # Create the empty dictionaries

    # Supplied method for defining the special values
    def build(self):

        qnan=  "7C000000"
        qnanm= "FC000000"
        snan=  "7E000000"
        snanm= "FE000000"
        nan=   "7C000000"
        nanm=  "FC000000"
        inf=   "78000000"
        infm=  "F8000000"
        max=   "77F3FCFF"
        maxm=  "F7F3FCFF"
        min=   "04000000"
        minm=  "84000000"
        dmin=  "00000001"
        dminm= "80000001"

        self.define("(qnan)", qnan)
        self.define("(snan)", snan)
        self.define("(nan)",  nan)
        self.define("(inf)",  inf)
        self.define("(max)",  max)
        self.define("(min)",  min)
        self.define("+(qnan)",qnan)
        self.define("+(snan)",snan)
        self.define("+(nan)", nan)
        self.define("+(inf)", inf)
        self.define("+(max)", max)
        self.define("+(min)", min)
        self.define("(dmin)", dmin)
        self.define("+(dmin)",dmin)
        self.define("-(qnan)",qnanm)
        self.define("-(snan)",snanm)
        self.define("-(nan)", nanm)
        self.define("-(inf)", infm)
        self.define("-(max)", maxm)
        self.define("-(min)", minm)
        self.define("-(dmin)",dminm)       

        qnan=  "7C00000000000000"
        qnanm= "FC00000000000000"
        snan=  "7E00000000000000"
        snanm= "FE00000000000000"
        nan=   "7C00000000000000"
        nanm=  "FC00000000000000"
        inf=   "7800000000000000"
        infm=  "F800000000000000"
        max=   "77FCFF3FCFF3FCFF"
        maxm=  "F7FCFF3FCFF3FCFF"
        min=   "0400000000000000"
        minm=  "8400000000000000"
        dmin=  "0000000000000001"
        dminm= "8000000000000001"

        self.define("(qnan)", qnan)
        self.define("(snan)", snan)
        self.define("(nan)",  nan)
        self.define("(inf)",  inf)
        self.define("(max)",  max)
        self.define("(min)",  min)
        self.define("+(qnan)",qnan)
        self.define("+(snan)",snan)
        self.define( "+(nan)",nan)
        self.define("+(inf)", inf)
        self.define("+(max)", max)
        self.define("+(min)", min)
        self.define("(dmin)", dmin)
        self.define("+(dmin)",dmin)
        self.define("-(qnan)",qnanm)
        self.define("-(snan)",snanm)
        self.define("-(nan)", nanm)
        self.define("-(inf)", infm)
        self.define("-(max)", maxm)
        self.define("-(min)", minm)
        self.define("-(dmin)",dminm)

        qnan=  "7C000000000000000000000000000000"
        qnanm= "FC000000000000000000000000000000"
        snan=  "7E000000000000000000000000000000"
        snanm= "FE000000000000000000000000000000"
        nan=   "7C000000000000000000000000000000"
        nanm=  "FC000000000000000000000000000000"
        inf=   "78000000000000000000000000000000"
        infm=  "F8000000000000000000000000000000"
        max=   "77FFCFF3FCFF3FCFF3FCFF3FCFF3FCFF"
        maxm=  "F7FFCFF3FCFF3FCFF3FCFF3FCFF3FCFF"
        min=   "04000000000000000000000000000000"
        minm=  "84000000000000000000000000000000"
        dmin=  "00000000000000000000000000000001"
        dminm= "80000000000000000000000000000001"

        self.define("(qnan)", qnan)
        self.define("(snan)", snan)
        self.define("(nan)",  qnan)
        self.define("(inf)",  inf)
        self.define("(max)",  max)
        self.define("(min)",  min)
        self.define("+(qnan)",qnan)
        self.define("+(snan)",snan)
        self.define("+(nan)", qnan)
        self.define("+(inf)", inf)
        self.define("+(max)", max)
        self.define("+(min)", min)
        self.define("(dmin)", dmin)
        self.define("+(dmin)",dmin)
        self.define("-(qnan)",qnanm)
        self.define("-(snan)",snanm)
        self.define("-(nan)", qnanm)
        self.define("-(inf)", infm)
        self.define("-(max)", maxm)
        self.define("-(min)", minm)
        self.define("-(dmin)",dminm)


#
# +-------------------------------------+
# |                                     |
# |    Decimal Floating Point Object    |
# |                                     |
# +-------------------------------------+
#

class DFP(fp.FP):
    Special=DFP_Special()      # Special object for BFP special values

    # Integer/Right-Units View Attributes (LUV=False)
    #     len           len  base  prec    qmin    qmax  bias  sci  fp.Special
    attri={4: fp.FPAttr( 4,   10,     7,   -101,     90,  101,False,DFP_Special),\
           8: fp.FPAttr( 8,   10,    16,   -398,    369,  398,False,DFP_Special),\
           16:fp.FPAttr(16,   10,    34,  -6176,   6111, 6176,False,DFP_Special)}

    # Scientific/Left-Units View Attributes (LUV=True)
    #     len           len  base  prec    emin    emax  bias  sci fp.Special
    attrs={4: fp.FPAttr( 4,   10,     7,    -95,     96,   95,True,DFP_Special),\
           8: fp.FPAttr( 8,   10,    16,   -383,    384,  383,True,DFP_Special),\
           16:fp.FPAttr(16,   10,    34,  -6143,   6144, 6143,True,DFP_Special)}

    # Convert a sequence of bytes into a Python object.  The object returned
    # depends upon the subclass supplying this method.
    # Method Arguments:
    #   byts       A sequence of 4, 8, or 16 bytes being decoded.
    #   byteorder  Specifies the byte order of the bytes being decoded.  Specify
    #              'big' for big-endian, 'little' for little endian.  Defaults to
    #              'little'.  Use sys.byteorder for platform byte order.
    # Exception:
    #   FPError if an error occurs during conversion
    @classmethod
    def from_bytes(cls,byts,byteorder="little",debug=False):
        return dpd.from_bytes(byts,byteorder=byteorder,debug=debug)

    def __init__(self,string,length=8,rmode=None,luv=False,debug=False):
        # Whether integer view (False) or scientific view (True) in use
        self.luv=luv          # Whether integer view or integer view in use
        if luv:
            self.attr=DFP.attrs[length]     # Get the scientific view attributes
        else:
            self.attr=DFP.attri[length]     # Get the integer view attributes

        super().__init__(string,length=length,rmode=rmode,debug=debug)

    def create(self):
        if self.exponent is None:
            exp=0
        else:
            exp=self.exponent

        fpo=DFP_Number(self.sign,integer=self.int_str,fraction=self.frac_str,exp=exp,\
            rounding=self.rmodeo,attr=self.attr,debug=self.debug)
        if __debug__:
            if self.debug:
                print("%s fpo: %r %s" \
                    % (eloc(self,"create",module=this_module),fpo,fpo))
        return fpo

    def default(self):
        return (fp.DFP_DEFAULT,fp.DFP_DEFAULT)

    def has_overflow(self):
        return self.fpo.overflow
        
    def has_underflow(self):
        return self.fpo.underflow

    def i_fmt(self,byteorder="big"):
        if self.is_special:
            return fp.FP_Special.to_bytes(self.is_special,byteorder=byteorder)

        if __debug__:
            if self.debug:
                cls_str=eloc(self,"i_fmt",module=this_module)
                print("%s %r %s" % (cls_str,self.number,self.number))
                print("%s calling DFP_Number._interchange()" % cls_str)

        self.number._interchange()
        return self.number.to_bytes(byteorder=byteorder)

    def is_subnormal(self):
        return self.fpo.subnormalize

    def rounding(self,rnum):
        if not isinstance(rnum,int) or rnum<8 or rnum>15:
            rtn=fp.DFP_DEFAULT
        else:
            rtn=fp.FP_Number.get_rounding_method(10,rnum)
        if __debug__:
            if self.debug:
                print("%s returning rounding method: %s" \
                    % (eloc(self,"rounding",module=this_module),rtn))
        return rtn

    def to_number(self,fpo):
        assert isinstance(fpo,DFP_Number),\
            "%s 'fpo' argument must be a DFP_Number object: %s" \
                % (eloc(self,"to_number",module=this_module),fpo)

        return fpo


#
# +----------------------------------------------+
# |                                              |
# |    Decimal Floating Point Conversion Test    |
# |                                              |
# +----------------------------------------------+
#

class DFP_Test(fp.Test):
    def __init__(self,value,length=8,ar=True,debug=False):
        super().__init__(value,length=length,ar=ar,debug=debug)
        self.special_converter=DFP.Special  # Set special converter

  #
  # Methods required by super class
  #

    def convert_bytes_to_object(self,byts):
        return DFP.from_bytes(byts,byteorder="big",debug=self.debug)


# This function outputs various information about decimal floating point values
# and class related information about this module.
#
# Function Argument:
#   test   Specify True to run rounding mode tests not found in test cases
#          Specify False to display DFP information.  Defaults to False.
def info(test=False):
    if test:
        rmodes=[8,9,10,11,12,13,14,15]
        #values=["99999999","-99999999"]
        #values=["99999999e200","-99999999e-200"]
        values=["99999999e-103",]
        debug=[]
        print()
        for v in values:
            for r in rmodes:
                val="%sr%s" % (v,r)
                print("testing: %s" % val)
                tst=DFP_Test(val,length=4,debug=r in debug)
                tst.run()
                tst.display()
                print()
    else:
        print("\nDeclet Formats:")
        declet.cls_str()

        print(\
            "\nInterchange Format Attributes: (DFP only uses RUV or integer view)\n")
        for c in [dpd32,dpd64,dpd128]:
            ctx=c()
            print(ctx)
        print()

        # Print out the dpd subclass information
        print("\nDFP Interchange Values:\n")
        dpd.info()
        print()


if __name__ == "__main__":
    #raise NotImplementedError("module %s intended for inport use only" % this_module)

    # Comment out the preceding raise statement to display various information 
    # about this module and decimal floating point values in general.
    info(test=True)