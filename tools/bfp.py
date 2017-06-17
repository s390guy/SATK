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

# This module provides generic binary floating point support providing objects
# shared between the two underlying supporting technologies:
#
#   - Python supplied float objects (See bfp_float.py), and
#   - Externally supplied gmpy2 package extension (See bfp_gmpy2.py).
#
# Binary floating point (BFP) interchange formats for 32-, 64-. and 128-bit values
# using the decimal encoding of the significand as described in IEEE-754-2008.
#
# BFP interchange formats consist of three fields:
#   - a sign,
#   - a biased exponent (most significant to least significant bits), and
#   - a fraction (most significant to least significant bits).
#
# The 32-bit format is:
#
#      1     8               23
#     +-+--------+-----------------------+
#     |S|   EXP  |       FRACTION        |
#     +-+--------+-----------------------+
#       0b11111111
#
#        Biased Exponents:  0 to 254  (Bias 127)
#        Signed Exponents:  -127 to 127
#        Infinities / NaNs: 255
#
#
# The 64-bit format is:
#
#      1      11                             52
#     +-+-----------+----------------------------------------------------+
#     |S|    EXP    |                     FRACTION                       |
#     +-+-----------+----------------------------------------------------+
#           7FF
#
#        Biased Exponents:   0 to 2046 (Bias 1023)
#        Signed Exponents:   -1023 to 1023
#        Infinitites / NaNs: 2047
#
#
#
# The 128-bit format is:
#
#      1        15                                  112
#     +-+---------------+-------------------------- ~ ~ ~ -------------------------+
#     |S|      EXP      |                         FRACTION                         |
#     +-+---------------+---------------------------~ ~ ~ -------------------------+
#            7FFF
#
#        Biased Exponents:  0 to 32766 (Bias 16383)
#        Signed Exponents:  -16383 to 16383
#        Infinities / NaNs: 32767
#
#
# The combination and trailing significand fields and their size depends upon the 
# size of the exchange format.  Exchange formats of 32, 64, and 128 bits are
# described in the standard, as well as how attributes for formats in excess of 128 
# bits are determined.  This module supports only 32-, 64- and 128-bit exchange
# formats.
#

this_module="bfp.py"

# Python imports:
import re        # Access regular expression support
# SATK imports:
import fp        # Access the generic floating point framework support
import retest    # Access the regular expression test harness


# Try to import the gmpy2 package extension
gmpy2_available=False
try:
    import gmpy2    # Load the gmpy2 package extension if available
    gmpy2_available=True
except ImportError:
    pass


# This function establishes the optional use of gmpy2 when available
use_gmpy2=False
def gmpy2_usage(use=False):
    global use_gmpy2
    use_gmpy2 = gmpy2_available and use


# This object wraps a Python floating point object.  Each subclass understands
# how to process the object presented to it.  The methods of this object 
# expose the common interface to such objects used by the framework.
#
# Instance Arguments:
#   src     Either a floating point string (without embedded rounding) or an Python
#           floating point object.
#   ic      Interchange format hexadecimal string.  Intended for creation of a
#           floating point object from an externally sourced interchange format value.
#           Presently not used.
#   format  Interchange format in bits.  Must be 32, 64 or 128.  Defaults to 32. 
#   round   The floating point object's rounding mode if applicable.  This is not a 
#           rounding mode number, but the object's native rounding mode. 
class BFP_Data(object):
    cls=None     # Class of the object produced by the subclass
    rounding={}  # Mapping of floating point framework BFP rounding mode to object
    default=None # The object's default rounding mode.

    # This class method initializes the 'cls' class attribute
    @classmethod
    def init(cls):
        raise NotImplementedError("subclass %s must provide init() class method" \
            % (cls.__name__))
    
    def __init__(self,src,ic=None,format=32,round=0,debug=False):
        self.ic=ic         # Hexadecimal byte string of an external interchange format
        self.format=format # interchange format being created
        self.debug=debug   # Remember debug status

        # Attributes related to the Python floating point object
        self.fpo=None      # Python floating point object
        self.ctx=None      # context associated with Python floating point object

        # These attributes are produced by the wrap() method that interprets the
        # Python floating point object
        self.isign=None    # The value's sign
        self.integer=None  # The implied integer value
        self.ibits=None    # The actual bits destined for the significand
        self.iexp=None     # The signed exponent destined for the biased exponent
        self.special=None  # Special value to be set

        if isinstance(src,str):
            self.fpo=self.create(src,round=round)
        elif isinstance(src,self.__class__.cls):
            self.fpo=src
        else:
            raise ValueError("%s 'src' argument unrecognized: %s" \
                % (fp.eloc(self,"__init__",module=this_module),src))

        self.wrap()    # Interpret the object for use by the framework

  #
  #  These methods must be supplied by the subclass
  #

    # This method creates the Python floating point object from a floating point
    # constant string.
    # Returns:
    #   the created Python floating point object
    def create(self,string,round=0):
        raise NotImplementedError("%s subclass %s must provide create() method" \
            % (fp.eloc(self,"create",module=this_module),self.__class__.__name__))

    # Print or return a string describing the floating point object's data
    def display(self,modes=False,indent="",string=False):
        raise NotImplementedError("%s subclass %s must provide display() method" \
            % (fp.eloc(self,"display",module=this_module),self.__class__.__name__))

    # Returns True if overflow has been detected, otherwise False.
    def has_overflow(self):
        raise NotImplementedError("%s subclass %s must provide has_overflow() method"\
            % (fp.eloc(self,"has_overflow",module=this_module),\
                self.__class__.__name__))

    # Returns True if underflow has been detected, otherwise False.
    def has_underflow(self):
        raise NotImplementedError("%s subclass %s must provide has_underflow() method"\
            % (fp.eloc(self,"has_underflow",module=this_module),\
                self.__class__.__name__))

    # This method interprets an underlying floating point object into data
    # usable by the floating point framework
    def wrap(self):
        raise NotImplementedError("%s subclass %s must provide wrap() method" \
            % (fp.eloc(self,"wrap",module=this_module),self.__class__.__name__))


#
# +-----------------------------------+
# |                                   |
# |    Python float Object Support    |
# |                                   |
# +-----------------------------------+
#

class FLOAT_Data(BFP_Data):
    cls=float     # Class of the object produced by the create() method

    #                                                # Num   float
    #                                                # Mode  Mode
    rounding={fp.BFP_HALF_UP:None,                    # 1    None
              fp.BFP_HALF_EVEN:None,                  # 4    None
              fp.BFP_DOWN:None,                       # 5    None
              fp.BFP_CEILING:None,                    # 6    None
              fp.BFP_FLOOR:None}                      # 7    None
    default=None   # float only uses internally the fp.BFP_HALF_EVEN mode

    # Regular expression used to recognize a float object hex() method output
    parser=re.compile("(?P<sign>[+-])?(0x)(?P<integer>[0-9a-f]+)"\
        "(?P<fraction>\.[0-9a-f]*)?(?P<exp>p[+-]?[0-9]+)")

    # Convert the match object sign into the framework standard integer
    signs={"+":0,"-":1,None:0}

    hex_chars={"0":[0,0,0,0],
               "1":[0,0,0,1],
               "2":[0,0,1,0],
               "3":[0,0,1,1],
               "4":[0,1,0,0],
               "5":[0,1,0,1],
               "6":[0,1,1,0],
               "7":[0,1,1,1],
               "8":[1,0,0,0],
               "9":[1,0,0,1],
               "A":[1,0,1,0],
               "a":[1,0,1,0],
               "B":[1,0,1,1],
               "b":[1,0,1,1],
               "c":[1,1,0,0],
               "D":[1,1,0,1],
               "d":[1,1,0,1],
               "E":[1,1,1,0],
               "e":[1,1,1,0],
               "F":[1,1,1,1],
               "f":[1,1,1,1]}

    # Converts a string of hexadcimal digits to a binary digits list
    @staticmethod
    def hex2bin(string):
        chars=FLOAT_Data.hex_chars
        lst=[]
        for c in string:
            lst.extend(chars[c])
        return lst

    def __init__(self,src,ic=None,format=32,round=0,debug=False):
        # These attributes are created by wrap() method
        self.hx=None        # Hex literal from float conversion
        self.mo=None        # Regular expression match object from hex literal
        self.integer=None   # Integer from parsed Hex literal
        # conditions detected
        self.overflow_detected=False
        self.underflow_detected=False
        
        super().__init__(src,ic=ic,format=format,round=round,debug=debug)

  #
  #  These methods are required by the super class
  #

    # Create the Python float object from the floating point constant string
    def create(self,string,round=0):
        return float(string)
        
    def display(self,modes=False,indent="",string=False):
        s="%s FLOAT Data:" % indent
        lcl="%s    " % indent
        s="%s\n%sfpo:      %s" % (s,lcl,self.fpo)
        s="%s\n%sformat:   %s" % (s,lcl,self.format)
        s="%s\n%sfloat hex:%s" % (s,lcl,self.hx)

        if self.special:
            s="%s\n%sfloat spec:%s" % (s,lcl,self.hx)
        else:
            prec=len(self.ibits)
            s="%s\n%sfloat prec:%s 0x%X" % (s,lcl,prec,prec)
            s="%s\n%sfloat sign: %s" % (s,lcl,self.isign)

            if not self.ic:
                # Input is a floating point string
                s="%s\n%sfloat man: %s (%s digits)" % (s,lcl,self.ibits,\
                    len(self.ibits))
                s="%s\n%smfloat exp:  %s 0x%X" % (s,lcl,self.iexp,self.iexp)
            else:
                # Format interchange format - TO BE DONE
                pass

        if string:
            return s
        print(s)

    def has_overflow(self):
        return self.overflow_detected
        
    def has_underflow(self):
        return self.underflow_detected
        
    def is_subnormal(self):
        pass

    def wrap(self):
        self.hx=hx=self.fpo.hex()
        if __debug__:
            if self.debug:
                cls_str=fp.eloc(self,"wrap",module=this_module)
                print("%s hex: %s" % (cls_str,hx))
        if hx == 'inf':
            if __debug__:
                if self.debug:
                    print("%s positive infinity found" % cls_str)
            self.overflow_detected=True
            self.isign=0
            self.special="(inf)"
            return
        elif hx == "-inf":
            if __debug__:
                if self.debug:
                    print("%s negative infinity found" % cls_str)
            self.overflow_detected=True
            self.isign=1
            self.special="-(inf)"
            return
        self.mo=mo=FLOAT_Data.parser.match(hx)
        if mo is None:
            raise ValueError("unrecognized hex literal: '%s'" % hx)
        mod=mo.groupdict()

        self.isign=FLOAT_Data.signs[mod["sign"]]
        integer=mod["integer"]
        if integer not in ["1","0"]:
            raise ValueError("unexpected integer in hex literal: '%s'" \
                % self.integer)
        self.integer=int(integer)

        frac=mod["fraction"]
        frac=frac[1:]      # Drop off the leading period of the fraction
        self.ibits=FLOAT_Data.hex2bin(frac)

        exp=mod["exp"]
        if exp is None:
            self.iexp=0
        else:
            self.iexp=int(exp[1:],10)


#
# +---------------------------------+
# |                                 |
# |    gmpy2 mpfr Object Support    |
# |                                 |
# +---------------------------------+
#

# This class provides detailed information about the content of a gmpy2.mpfr object
# Its attributes are made available and the objects to_binary() content is
# exposed.  This object participates in creation of the actual interchange format.
#
# The sequence of bytes supplied by the to_binary() method is internal to the gmpy2
# package and can change from one release to the next.  This wrapper to the gmpy2
# mfpr object allows access to the internal data in a release independent manner.
#
# Instance Arguments:
#   src     Either a floating point string (without embedded rounding) or an object
#           created by the gmpy2.mpfr() function.
#   ic      Interchange format hexadecimal string.  Intended for creation of an mpfr
#           object from an externally sourced interchange format.  Presently not used
#   format  Interchange format in bits. Must be 32, 64 or 128.  Defaults to 32. 
#   round   floating point framework rounding mode number.
class MPFR_Data(BFP_Data):
    # Both of these attributes are initialized by the init() class method
    cls=None      # Class of the object produced by the create() method
    rounding={}   # Maps numeric rounding mode to gmpy2 mode
    default=None  # Default gmpy2 rounding mode

    # This has to be in a method because otherwise when gmpy2 is not available
    # the class will not be initialized
    @classmethod                                             # Num   GMPY2
    def init(cls):                                           # Mode  Mode
        cls.rounding={fp.BFP_HALF_UP:gmpy2.RoundAwayZero,     # 1     4
                      fp.BFP_HALF_EVEN:gmpy2.RoundToNearest,  # 4     0
                      fp.BFP_DOWN:gmpy2.RoundToZero,          # 5     1
                      fp.BFP_CEILING:gmpy2.RoundUp,           # 6     2
                      fp.BFP_FLOOR:gmpy2.RoundDown}           # 7     3
        # Define the default gmpy2 rounding mode
        cls.default=gmpy2.RoundToNearest

        # This is needed to access the actual mpfr object's class.  gmpy2.mpfr is
        # actually a builtin-function not a class.  This gets us to the actual class
        # of the underlying mpfr object.
        cls.cls=gmpy2.mpfr("0").__class__

    def __init__(self,src,ic=None,format=32,round=0,debug=False):
        assert gmpy2_available,\
            "%s MPFR_Data must not be instantiated if the gmpy2 module is not "\
                "available" % fp.eloc(self,"__init__",module=this_module)

        # These values are supplied by the gmpy2.mpfr.digits() method used by
        # the wrap() method
        self.digits=None   # the binary digits of the signigicand as a string
        self.dexp=None     # the signed exponent
        self.dprec=None    # the precision of the object

        super().__init__(src,ic=ic,format=format,round=round,debug=debug)

  #
  #  These methods are required by super class
  #

    # Create the gmpy2.mpfr object from the floating point constant string
    # Method Arguments:
    #   string   A floating point constant string
    #   round    The rounding number used for the created object
    def create(self,string,round=0):
        ctx=gmpy2.ieee(self.format)
        ctx.round=MPFR_Data.rounding[round]
        gmpy2.set_context(ctx)
        fpo=gmpy2.mpfr(string)
        ctx=gmpy2.get_context()     # Get the results
        self.ctx=ctx.copy()         # Copy the context for later status
        return fpo

    def display(self,modes=False,indent="",string=False):
        s="%s MPFR Data:" % indent
        lcl="%s    " % indent
        if modes:
            s="%s\n%sRoundAwayZero:  %s" % (s,lcl,gmpy2.RoundAwayZero)
            s="%s\n%sRoundDown:      %s" % (s,lcl,gmpy2.RoundDown)
            s="%s\n%sRoundToNearest: %s" % (s,lcl,gmpy2.RoundToNearest)
            s="%s\n%sRoundToZero:    %s" % (s,lcl,gmpy2.RoundToZero)
            s="%s\n%sRoundUp:        %s" % (s,lcl,gmpy2.RoundUp)
        s="%s\n%sfpo:      %s" % (s,lcl,self.fpo)
        s="%s\n%sformat:   %s" % (s,lcl,self.format)

        # Get Base 2 mantissa and base 10 exponent
        # man,exp,mpfr_prec=self.fpo.digits(2)
        s="%s\n%smpfr prec:%s 0x%X" % (s,lcl,self.dprec,self.dprec)
        s="%s\n%smpfr sign: %s" % (s,lcl,self.isign)
        s="%s\n%smpfr int:  %s" % (s,lcl,self.integer)

        if not self.ic:
            # Input is a floating point string
            s="%s\n%smpfr man: %s (%s digits)" % (s,lcl,self.digits,len(self.digits))
            #    % (s,lcl,digits[0],len(digits[0]))
            s="%s\n%smpfr exp:  %s 0x%X" % (s,lcl,self.dexp,self.dexp)
        else:
            # Input is from an external interchange format hex string
            l=self.format//8
            dcd=bfp.BFPRound.decode[l]
            s="%s\n%sdecode:   %s" % (s,lcl,dcd)
            byts=fp.FP.str2bytes(self.ic)
            ic_sign,ic_frac,ic_exp,ic_attr=dcd.decode(byts)
            ic_frac=fp.rounding_mode.list2str(ic_frac,2)
            s="%s\n%sifmt big: %s" % (s,lcl,fp.FP.bytes2str(byts))
            b=int.from_bytes(byts,byteorder="big",signed=False)
            s="%s\n%sifmt sign:%s" % (s,lcl,ic_sign)
            s="%s\n%sifmt exp: %s" % (s,lcl,ic_exp)
            bexp=exp+dcd.bias
            s="%s\n%sifmt bias:%s 0x%X" % (s,lcl,bexp,bexp)
            s="%s\n%smpfr exp: %s 0x%X" % (s,lcl,exp,exp)
            s="%s\n%smpfr man: %s (%s digits)" % (s,lcl,man,len(man))
                #% (s,lcl,digits[0],len(digits[0]))
            s="%s\n%sifmt frac: %s (%s digits)" % (s,lcl,ic_frac,len(ic_frac))
            s="%s\n%sattr:     %s" % (s,lcl,ic_attr)

        #ctx=gmpy2.get_context()
        s="%s\n%s%s" % (s,lcl,self.ctx)
        s="%s\n" % s
        if string:
            return s
        print(s)
        
    def has_overflow(self):
        return self.ctx.overflow
        
    def has_underflow(self):
        return self.ctx.underflow
        
    def is_subnormal(self):
        pass
    
    # Interpret the gmpy2.mpfr object
    def wrap(self):
        self.digits,self.dexp,self.dprec=self.fpo.digits(2)  # 2 is the base
        if __debug__:
            if self.debug:
                cls_str=fp.eloc(self,"wrap",module=this_module)
                print("%s digits: '%s'" % (cls_str,self.digits))
                print("%s exp:     %s"  % (cls_str,self.dexp))

        # Detect special values
        if self.digits == "-inf":
            self.isign=1
            self.special="(inf)"
            self.overflow_detected
            return

        # Determine the sign of the value
        if self.digits[0] == "-":
            actual_digits=self.digits[1]
            self.isign=1
        else:
            actual_digits=self.digits
            self.isign=0

        if actual_digits=="0":
            # Handle the case of a true zero
            self.ibits=actual_digits
            self.integer="0"
            self.iexp=self.dexp
        else:
            # Handle the normal case
            self.ibits=actual_digits[1:]   # Remove the implied first 1
            self.integer=actual_digits[0]    # The implied integer digit
            # The exponent assumes the leading one is part of the significand, so the
            # exponent is one larger than is required for the interchange format.
            self.iexp=self.dexp-1


if gmpy2_available:
    # Don't do this if the gmpy2 module is not available
    MPFR_Data.init()

class BFP_Special(fp.FP_Special):
    def __init__(self):
        super().__init__()  # Create the empty dictionaries

    # Supplied method for defining the special values
    def build(self):
        
        qnan= "7FE00000"
        qnanm="FFE00000"
        snan= "7FA00000"
        snanm="FFA00000"
        nan=  "7FC00000"
        nanm= "FFC00000"
        inf=  "7F800000"
        infm= "FF800000"
        max=  "7F7FFFFF"
        maxm= "FF7FFFFF"
        min=  "00800000"
        minm= "80800000"
        dmin= "00000001"
        dminm="80000001"
        
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
        self.define("-(dmin)",dmin)
        
        qnan= "7FFC000000000000"
        qnanm="FFFC000000000000"
        snan= "7FF4000000000000"
        snanm="FFF4000000000000"
        nan=  "7FF8000000000000"
        nanm= "FFF8000000000000"
        inf=  "7FF0000000000000"
        infm= "FFF0000000000000"
        max=  "7FEFFFFFFFFFFFFF"
        maxm= "FFEFFFFFFFFFFFFF"
        min=  "0010000000000000"
        minm= "8010000000000000"
        dmin= "0000000000000001"
        dminm="8000000000000001"
        
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
        self.define("-(dmin)", dmin)

        qnan= "7FFFC000000000000000000000000000"
        qnanm="FFFFC000000000000000000000000000"
        snan= "7FFF4000000000000000000000000000"
        snanm="FFFF4000000000000000000000000000"
        nan=  "7FFF8000000000000000000000000000"
        nanm= "FFFF8000000000000000000000000000"
        inf=  "7FFF0000000000000000000000000000"
        infm= "FFFF0000000000000000000000000000"
        max=  "7FFEFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        maxm= "FFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        min=  "00010000000000000000000000000000"
        minm= "80010000000000000000000000000000"
        dmin= "00000000000000000000000000000001"
        dminm="80000000000000000000000000000001"

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
        self.define("-(dmin)", dmin)


# This class decodes a bytes sequence into its consituent parts suitable for use
# with the BFP_Number class or encodes the BFP_Number object into a sequence of bytes.
#
# Instance Arguments:
#   length   required bytes sequence length
class BFP_Formatter(fp.FPAttr):
    #    len           len base  prec    min    max  bias sci fp.Special
    attr={4: fp.FPAttr(4,    2,    24,   -127,  127,  127,True,BFP_Special),\
          8: fp.FPAttr(8,    2,    53,  -1623, 1623, 1023,True,BFP_Special),\
          16:fp.FPAttr(16,   2,   113, -16383,16383,16383,True,BFP_Special)}

    #     len    sign      biased exponent       significand
    masks={4:((1<<31,31),  (0b011111111<<23,23), 0x007FFFFF),
           8:((1<<63,63),  (0x7FF<<52,52),       0xFFFFFFFFFFFFF),
          16:((1<<127,127),(0x7FFF<<112,112),    0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF)}
    
    #       len special      quiet   payload
    spmasks={4:(0b011111111, 1<<22,  0x003FFFFF),
             8:(0x7FF,       1<<51,  0x7FFFFFFFFFFFF),
            16:(0x7FFF,      1<<111, 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFF)}

    # biased exponent field of special values for each format length
    spec_exp={4:255,8:2047,16:32767}


    # Convert a digit list into an integer
    @staticmethod
    def bits2int(bits):
        s=[]
        for b in bits:
            s.append("01"[b])
        string = "".join(s)
        return int(string,2)

    def __init__(self,length):
        self.attr=BFP_Formatter.attr[length]         # fp.FPAttr object of the format
        self.masks=BFP_Formatter.masks[length]       # decode/encode masks and shifts
        self.spmasks=BFP_Formatter.spmasks[length]   # special value masks
        self.length=length                           # Legnth of the format
        self.sign_msk,self.sign_shift=self.masks[0]  # Sign mask and shift values
        self.exp_msk,self.exp_shift=self.masks[1]    # Exponent mask and shift values
        self.frac_mask=self.masks[2]                 # fraction mask
        self.bias=self.attr.bias                     # Unsigned exponent bias

        # Special value masks
        self.spec=self.spmasks[0]                    # Special value exponent field
        self.quiet_msk=self.spmasks[1]               # Special value quite mask
        self.payload_msk=self.spmasks[2]             # Special value payload mask

    def __str__(self):
        return "BFP_Formatter: length:%s bias: %s" % (self.length,self.bias)

    def _decode_special(self,sign,digits,infinity,debug=False):
        if __debug__:
            if debug:
                cls_str=fp.eloc(self,"_decode_special",module=this_module)
        if infinity:
            bfp=BFP_Infinity(sign)
        else:
            # Must be a NaN then
            if digits[0]==0:
                signaling=True
            else:
                signaling=False
            payload_int = BFP_Formatter.bits2int(digits[1:])
            if __debug__:
                if debug:
                    print("%s found payload: %s" % (cls_str,payload_int))

            if signaling:
                bfp=BFP_sNaN(sign,payload=payload_int)
            else: 
                bfp=BFP_qNaN(sign,payload=payload_int)

        if __debug__:
            if debug:
                print("%s returning: %s" % (cls_str,bfp))
        return bfp

    # Encode a number into bytes
    # Method Arguments:
    #   sign   the sign: 0 -> positive, 1-> negative
    #   exp    the signed exponent as an integer
    #   frac   the significand WITHOUT the implied first digit as digits list
    #   debug  Specify True to enable debugging messages.
    def _encode_number(self,sign,exp,integer,frac,byteorder="big",debug=False):
        assert isinstance(frac,list),\
            "%s 'frac' argument must be a list: %s" \
                % (fp.eloc(self,"_encode_number",module=this_module),frac)

        # Set the sign
        val = sign << self.sign_shift
        if __debug__:
            if debug:
                cls_str=fp.eloc(self,"_encode_number",module=this_module)
                print("%s sign: 0x%X" % (cls_str,val))

        # Convert the significand into a list of digits
        if isinstance(frac,int):
            frac_lst=[frac,]
        else:
            frac_lst=frac
        prec=self.attr.prec-1
        if len(frac_lst)<prec:
            zeros=prec-len(frac_lst)
            zeros=[0,]*zeros
            frac_lst.extend(zeros)
        elif len(frac_lst)>prec:
            frac_lst=frac_lst[:prec]
        frac_int=BFP_Formatter.bits2int(frac_lst)
        ifrac_int = frac_int & self.frac_mask

        if ifrac_int == 0 and exp == 0 and integer == 0:
            # This is a true zero value not a subnormal
            bexp = 0
            if __debug__:
                if debug:
                    print("%s signed exponent: %s" % (cls_str,exp))
                    print("%s biased exponent: %s" % (cls_str,bexp))
        else:
            # Set the biased exponent
            bias  = self.attr.bias
            bexp  = exp + bias
            if __debug__:
                if debug:
                    print("%s signed exponent: %s" % (cls_str,exp))
                    print("%s bias:            %s" % (cls_str,bias))
                    print("%s biased exponent: %s" % (cls_str,bexp))
                    #print("%s exponent mask:   0x%X" % (cls_str,self.exp_msk))

        val = val | bexp << self.exp_shift
        if __debug__:
            if debug:
                print("%s w/exp: 0x%X" % (cls_str,val))

        # Set the significand
        val = val | ifrac_int
        if __debug__:
            if debug:
                print("%s coef:  0x%X" % (cls_str,frac_int))
                print("%s w/coef:0x%X" % (cls_str,val))

        # Convert to bytes
        return val.to_bytes(self.length,byteorder=byteorder,signed=False)

    # Encode a BFP Special Value
    # Method Arguments:
    #   sign        Sign of the special value.  Specify 0 for positive.  Specify
    #               1 for negative.
    #   signaling   Specify True if a signaling value.  Specify False if quiet.
    #               Infinity signaling must be True.
    #   payload     The payload encoded.  Infinity payload must be zero  
    # Returns:
    #   a sequence of bytes representing the special value
    def _encode_special(self,sign,signaling,payload,byteorder="big",debug=False):
        if __debug__:
            if debug:
                cls_str=fp.eloc(self,"_encode_special",module=this_module)
                print("%s sign:%s signaling:%s payload:%s byteorder:%s debug:%s"\
                    % (cls_str,sign,signaling,payload,byteorder,debug))

        # Set the sign
        val = sign << self.sign_shift
        if __debug__:
            if debug:
                print("%s sign: 0x%X" % (cls_str,val))

        # Set the reserved exponent value used by special values
        val = val | self.spec << self.exp_shift

        # Set the signaling value
        if not signaling:
            val = val | self.quiet_msk

        # Set the payload
        val = val | payload & self.payload_msk

        # Convert to bytes
        return val.to_bytes(self.length,byteorder=byteorder,signed=False)

    # Decodes a bytes sequence as a number
    # Method Arguments:
    #   byts       the bytes sequence being decoded
    #   prec       The precision of the fraction.  Defaults to the precision of the
    #              interchange format implied by the length of byts
    #   byteorder  The byte order of the bytes sequence.  Specify 'big' for most-
    #              significant byte to least significant byte.  Specify 'little' for
    #              least-significant byte to most significant byte.  Defaults to 
    #              'big'.
    # Returns for a special value
    #   a BFP_Finite, BFP_Infinity, BFP_qNaN, or BFP_sNan object
    def decode(self,byts,prec=None,byteorder="big",debug=False):
        # Convert bytes to an integer
        fmt=int.from_bytes(byts,byteorder=byteorder,signed=False)
        if __debug__:
            if debug:
                cls_str=fp.eloc(self,"decode",module=this_module)
                print("%s sign fld: 0x%X" % (cls_str,fmt))

        # Extract the sign
        sign_fld = fmt & self.sign_msk
        if __debug__:
            if debug:
                print("%s sign field: 0x%X" % (cls_str,sign_fld))
        sign=sign_fld >> self.sign_shift
        if __debug__:
            if debug:
                print("%s found sign: %s" % (cls_str,sign))

        # Extract the biased exponent and convert it to a signed exponent
        exp_fld = fmt & self.exp_msk
        if __debug__:
            if debug:
                print("%s exp field:  0x%X" % (cls_str,exp_fld))
        bexp=exp_fld >> self.exp_shift
        if __debug__:
            if debug:
                print("%s found bexp: %s" % (cls_str,bexp))
        if bexp == self.spec:
            special=True
            if __debug__:
                if debug:
                    print("%s found special value" % cls_str)
        else:
            exp = bexp - self.bias
            if __debug__:
                if debug:
                    print("%s found finite number" % cls_str)
                    print("%s found exp: %s" % (cls_str,exp))
            special=False

        # Extract the fraction
        frac_fld = fmt & self.frac_mask
        if __debug__:
            if debug:
                print("%s frac mask:   0x%X" % (cls_str,self.frac_mask))
                print("%s frac field:  0x%X" % (cls_str,frac_fld))

        # Check for infinity
        if special and frac_fld==0:
            infinity=True
        else:
            infinity=False
        if prec is None:
            precision=self.attr.prec
        else:
            precision=prec
        frac_prec=precision-1
        base=self.attr.base

        if __debug__:
            # Perform sanity check to validate extraction was correct
            restored=sign_fld | exp_fld | frac_fld
            restored_byts=restored.to_bytes(len(byts),byteorder="big",signed=False)
            assert restored == fmt,\
               "%s extracted fields do not match original fields:\n"\
                   "    original: %s\m    extracted: %s" \
                       % (fp.eloc(self,"decode",module=this_module),\
                           fp.FP.bytes2str(byts),fp.FP.bytes2str(restored_byts))

        digits=[]
        fracwk=frac_fld
        for n in range(frac_prec):
            fracwk,digit=divmod(fracwk,base)
            digits.append(digit)
        assert len(digits)==frac_prec,\
            "%s precision (%s) does not match number of digits produced: %s" \
                % (fp.eloc(self,"decode",module=this_module),precision,len(digits))

        digits.reverse()
        if __debug__:
            if debug:
                print("%s found digits: %s" % (cls_str,digits))

        if special:
            return self._decode_special(sign,digits,infinity,debug=debug)

        if bexp == 0:
            implied=0
        else:
            implied=1

        significand=[implied,]
        significand.extend(digits)
        if __debug__:
            if debug:
                print("%s found significand: %s" %(cls_str,significand))

        return BFP_Finite(sign,exp,significand)

    # Encode into bytes a BFP value
    # Method Arguments:
    #   val    the BFP value as an instance of BFP_Value
    #   debug  Specify True to enable debugging messages.
    def encode(self,val,byteorder="big",debug=False):
        if isinstance(val,BFP_Finite):
            return self._encode_number(val.sign,val.exp,1,val.frac,\
                byteorder=byteorder,debug=debug)
        elif isinstance(val,BFP_Special_Value):
            return self._encode_special(val.sign,val.signaling,val.payload,\
                byteorder=byteorder,debug=debug)
        else:
            raise ValueError("%s 'val' argument must be a BFP_Value object: %s" \
                % (fp.eloc(self,"encode",module=this_module),val))


#
# +-----------------------------------+
# |                                   |
# |    Binary Floating Point Datum    |
# |                                   |
# +-----------------------------------+
#

# These classes provide a representation of the binary floating point datum
# types independent of the underlying Python objects used for there creation.

class BFP_Value(object):
    formatter={4:BFP_Formatter(4),\
               8:BFP_Formatter(8),\
               16:BFP_Formatter(16)}

    # Convert a sequence of bytes into a BFP_Value object
    @staticmethod
    def from_bytes(byts,byteorder="big",debug=False):
        assert isinstance(byts,bytes),\
            "%s BPF_Value.from_bytes() - 'byts' argument must be a sequence of "\
                "bytes: %s" % (this_module,byts)

        try:
            format=BFP_Value.formatter[len(byts)]
        except KeyError:
            raise ValueError("%s - BFP_Value.from_bytes() - 'byts' argument must "\
                "be of length 4, 8, or 16: %s" % (this_module,len(byts)))

        return format.decode(byts,byteorder=byteorder,debug=debug)

    def __init__(self,sign,typ,exp=None,frac=None,signaling=None,payload=None,\
                 debug=False):
        self.debug=debug           # Whether debug messages are produced
        self.sign=sign             # Sign of the value
        self.typ=typ               # Type of value
        self.exp=exp               # Exponent field
        self.frac=frac             # fraction as a list of digits
        self.signaling=signaling   # Whether signaling is in effect
        self.payload=payload       # Special value payload

    def __str__(self):
        return "BFP %s sign:%s exp:%s frac:%s signaling:%s payload:%s" \
            % (self.typ,self.sign,self.exp,self.frac,self.signaling,self.payload)

    def to_bytes(self,length,byteorder="big",debug=False):
        ddebug=self.debug or debug
        try:
            format=BFP_Value.formatter[length]
        except KeyError:
            raise FPError(msg="%s 'length' argument must be 4, 8, or 16: %s" \
                % (fp.eloc(self,"to_bytes",module=this_module),length))

        return format.encode(self,byteorder=byteorder,debug=ddebug)


class BFP_Finite(BFP_Value):
    def __init__(self,sign,exp,frac,debug=False):
        super().__init__(sign,"num",exp=exp,frac=frac,debug=debug)
        
    def __str__(self):
        return "BFP %s sign:%s exp:%s frac:%s" \
            % (self.typ,self.sign,self.exp,self.frac)


class BFP_Special_Value(BFP_Value):
    def __init__(self,sign,typ,signaling=False,payload=None,debug=False):
        assert payload >= 0,\
            "%s 'payload' argument must not be negative: %s" \
                % (fp.eloc(self,"__init__",module=this_module),payload)

        super().__init__(sign,typ,signaling=signaling,payload=payload,debug=debug)


class BFP_Infinity(BFP_Special_Value):
    def __init__(self,sign,debug=False):
        super().__init__(sign,"inf",signaling=True,payload=0,debug=debug)
        
    def __str__(self):
        return "BFP %s sign:%s" % (self.typ,self.sign)


class BFP_NaN(BFP_Special_Value):
    def __init__(self,sign,typ,signaling=True,payload=0,debug=False):
        super().__init__(sign,typ,signaling=signaling,payload=payload,debug=debug)

    def __str__(self):
        if self.signaling:
            q=0
        else:
            q=1
        return "BFP %s%s sign:%s signaling:%s payload:%s" \
            % (self.typ,self.sign,q,self.payload)


class BFP_qNaN(BFP_Special_Value):
    def __init__(self,sign,payload=0,debug=False):
        super().__init__(sign,"qNaN",signaling=False,payload=payload,debug=debug)


class BFP_sNaN(BFP_Special_Value):
    def __init__(self,sign,payload=1,debug=False):
        assert payload != 0,\
            "%s 'payload' argument must not be 0" \
                % (fp.eloc(self,"__init__",module=this_module))

        super().__init__(sign,"sNaN",signaling=True,payload=payload,debug=debug)


# A BFP Number
class BFP_Number(fp.FP_Number):

    @classmethod
    def from_bytes(cls,byts,byteorder="little",debug=False):
        raise NotImplementedError("class %s must provide from_bytes() class method"\
            % cls.__name__)

    def __init__(self,sign,integer=None,fraction=None,exp=0,rounding=12,\
                 format=None,debug=False):
        #assert isinstance(integer,str),\
        #    "%s 'integer' argument must be a string: %s" \
        #        % (fp.eloc(self,"__init__",module=this_module),integer)
        assert isinstance(format,BFP_Formatter),\
            "%s 'attr' argument must be a BFP_Formatter object: %s" \
                % (fp.eloc(self,"__init__",module=this_module),attr)

        self.formatter=format
        self.base=2
        self.integer=integer

        if isinstance(fraction,str):
            frac=self._str2list(fraction)
        else:
            frac=fraction

        super().__init__(sign,exp,frac,self.base,self.formatter.attr,\
            rounding=rounding,debug=debug)

    def to_bytes(self,byteorder="big",debug=False):
        if self.is_special:
            return fp.FP_Special.to_bytes(self.is_special,byteorder=byteorder)

        return self.formatter._encode_number(\
            self.sign,self.exp,self.integer,self.coef,byteorder=byteorder,\
                debug=self.debug)

  #
  # These methods must be supplied by the base (binary, decimal, or hexadecimal)
  # specific subclass.
  #

    # Take the required action to generate the number or special value when
    # overflow_occurs.
    def overflow_set(self):
        raise NotImplementedError("subclass %s must provide overflow_set() method" \
            % self.__class__.__name__)

    # Set the number to a subnormalized value
    def subnormal_set(self):
        raise NotImplementedError("subclass %s must provide subnormal_set() method" \
            % self.__class__.__name__)

    # Take the required action to generate the number or special value when
    # underflow_occurs.
    def underflow_set(self):
        raise NotImplementedError("subclass %s must provide overflow_set() method" \
            % self.__class__.__name__)


# This class uses the Python float object to create a BFP value in its interchange
# format.
class BFP(fp.FP):
    Special=BFP_Special()      # Special object for BFP special values
    
    format={4:BFP_Formatter(4),
            8:BFP_Formatter(8),
            16:BFP_Formatter(16)}

    def __init__(self,string,length=8,rmode=None,debug=False):
        self.formatter=BFP.format[length]
        self.attr=self.formatter.attr
        super().__init__(string,length=length,rmode=rmode,debug=debug)

  #
  # These methods are required by super class.
  #

    # Create the BFP_Data object for the presented floating point string.
    # Returns:
    #   a BFP_Data object (either FLOAT_Data or MPFR_Data)
    def create(self):
        if use_gmpy2:
            data=MPFR_Data(self.fpstr,format=self.length*8,round=self.rmodeo,\
                debug=self.debug)
        else:
            data=FLOAT_Data(self.fpstr,format=self.length*8,debug=self.debug)
        if __debug__:
            if self.debug:
                print("%s %s" % (fp.eloc(self,"create",module=this_module),\
                    data.display(string=True)))

        return data

    # Return the default numeric and underlying objects default rounding modes 
    # as a tuple.
    #   tuple[0]   the default numeric rounding mode number
    #   tuple[1]   the gmpy2 default rounding mode
    def default(self):
        if use_gmpy2:
            return (fp.BFP_HALF_EVEN,MPFR_Data.default)
        # Otherwise the float object is being used.
        return (fp.BFP_HALF_EVEN,FLOAT_Data.default)

    # Returns True if overflow has been detected, otherwise False.
    def has_overflow(self):
        return self.fpo.has_overflow()

    # Returns True if underflow has been detected, otherwise False.
    def has_underflow(self):
        return self.fpo.has_underflow()
        
    # Creates the interchange format for the FP_Number object.  Shortening and
    # rounding ocurs here.  This method is called by the FP class own to_bytes()
    # method for creation of the radix specific interchange format for floating
    # point datum.  Special values are handled directly by the FP.to_bytes() method.
    def i_fmt(self,byteorder="big"):
        return self.number.to_bytes(byteorder=byteorder)

    # Returns True if value is subnormal, otherwise False.
    def is_subnormal(self):
        return self.fpo.iexp == self.attr.emin \
            and not FP_Number.all_zeros(self.fpo.ibits)

    # Return the gmpy2 rounding mode corresponding to the numeric rounding mode
    def rounding(self,num):
        if use_gmpy2:
            data=MPFR_Data
        else:
            data=FLOAT_Data
        try:
            return data.rounding[num]
        except KeyError:
            pass

        # invalid or unsupported rounding mode.  
        # So return the default mode, round to nearest or BFP_HALF_EVEN
        return data.default

    def to_number(self,fpo):
        if fpo.special:
            self.is_special=BFP.Special.hexadecimal(fpo.special,length=self.length)
            return
        return BFP_Number(fpo.isign,integer=fpo.integer,fraction=fpo.ibits,\
            exp=fpo.iexp,rounding=self.rmodeo,format=self.formatter,debug=self.debug)


if __name__ == "__main__":
    #raise NotImplementedError("%s - intended for import use only" % this_module)
    
    class atest(object):
        def __init__(self,value,length):
            print(value)
            b=value.to_bytes(length)
            print(fp.FP.bytes2str(b))
            c=BFP_Value.from_bytes(b,debug=value.debug)
            print(c)
            print()
    
    def btest(string,debug=True):
        print("Testing: %s" % string)
        a=BFP(string,length=8,debug=debug)
        a.to_bytes()
        print()
    
    def test(length):
        atest(BFP_sNaN(0,payload=1,debug=False),length)
        atest(BFP_qNaN(1,payload=0,debug=False),length)
        atest(BFP_Infinity(1,debug=False),length)
        atest(BFP_Finite(0,4,[1,0,1],debug=False),length)

    #test(4)
    #test(8)
    #test(16)

    #btest("2")
    #btest("-1e1200")
    #btest("1e-1200")
    #btest("0")
    btest("-1")

    # Test gmpy2
    gmpy2_usage(use=True)
    if use_gmpy2:
        #btest("2")
        #btest("-1e1200")
        #btest("1e-1200")
        #btest("0")
        btest("-1")
        pass
