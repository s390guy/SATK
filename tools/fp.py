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

# When imported, this module supports interchange format creation for various
# Python supplied floating point modules.  When executed from the command=line
# the module is a test driver and conversion utility.  See the comments below the
# 'if __name__ == "__main__":' section near the end of the module for a description
# of the conversion utility command-line interface.
#
# This module supports interchange format creation for Python supplied float, 
# gmpy2.mpfr and dfp.dpd objects as well as conversions for legacy hexadecimal 
# floating point formats.  Formats of 32-, 64-, and 128-bits are supported as
# follows:
#
# Size:     32           64          128    Supplying Module
# BFP   float/mpfr   float/mpfr      mpfr   Python supplied (float) or external
# DFP      dpd           dpd         dpd    SATK/tools/dfp.py
# HFP   float/mpfr   float/mpfr      mpfr   Python supplied (float) or external
#
# A common approach for all floating point formats is provided by this module.
# It is expected to work with corresponding bfp.py, dfp.py, and hfp.py.  Because
# the modules also depend upon of this module, they are imported at the end rather
# than the beginning.
#
# Conversion of interchange formats into the various Python objects is not yet
# suppored.

#
# +--------------------------------------------+
# |                                            |
# |    Floating Point Modules Relationships    |
# |                                            |
# +--------------------------------------------+
#

# Multiple modules provide support for the three supported floating point formats:
# BFP, DFP, and HFP.  This module, fp.py, is intended to be the external interface
# to the various floating point formats as well as the framework used by all of
# the other modules.  The additional modules subclass the classes defined in
# fp.py to tailor their operation for each radix and its format.
#
# The foundation for a floating point datum regardless of radix and format is fp.FP.
# The fp.FP class converts a string definition of the floating point constant
# into an internal representation.  The internal representation performs any rounding
# required and supports the creation of a sequence of bytes conforming to the
# floating point radix' interchange format.
# 
# The fp.FP_Number class supports the internal representation of the floating point
# datum itself.  Rounding of the datum occurs via this object.  A built-in Python 
# type (float), an object from an external package (gmpy2.mpfr), or an object
# supplied by the floating point modules (dfp.dpd) assists the process.
#
# The fp.FP_Special object supports the creation of any speical values supported by
# the radix or format.  In each case they are hard-coded hex constants (converted
# into a sequence of bytes) interpretable by the 
#
# The Test class drives testing of the floating point string to interchange format
# conversions.  It accepts a string for conversion.  The string may be a standard
# floating point string constant (with embedded rounding mode) or a C-type
# hexadecimal constant starting with '0x'.
#
# Each associated module sublcasses these four base classes.
#
# The module using the floating point framework is expected to import only this
# module.  Creation of a floating point datum or special value occurs through use
# of one of threee module level functions:
#
#  - fp.BFP - for a binary floating point value,
#  - fp.DFP - for a decimal floating point value, or
#  - fp.HFP - for a hexadecimal floating point value.
#
# Each function returns an object subclassing fp.FP.  This object has one public
# method: to_bytes().  This method converts the floating point value into a
# sequence of bytes.  
#
# Conversion from a sequence of bytes to an object may use the from_byte() class
# method of each of the FP subclasses or this module's function of the same naame.
#
# This framework implements only three floating point flags or conditions:
#   - underflow
#   - overflow
#   - subnormal
#
# The subnormal condition is not indicated when underflow occurs.  The three
# conditions are mutually exclusive.
#
# Implementation status:
#   binary floating point -      partially implemented by bfp.py, bfp_float.py and
#                                bfp_gmpy2.py
#   decimal floating point -     implemented by dfp.py
#   hexadecimal floating point - not implemented


this_module="fp.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2016")

# Python imports:
import re       # Access regular expressions
import sys      # Access system information

# SATK imports:
import satkutil # Access the utility functions
# Add the tools/lang directory to PYTHONPATH if it is not already there
satkutil.pythonpath("tools/lang",nodup=True)  # Remove when retest no longer needed
import retest   # Access the regular expression test harness for debugging


#
# +------------------------------------+
# |                                    |
# |    Standardized Error Reporting    |
# |                                    |
# +------------------------------------+
#

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
# +----------------------------+
# |                            |
# |    Floating Point Error    |
# |                            |
# +----------------------------+
#

# This class is used to raise an exception during floating point handling
# Instance Argument:
#    msg    a string descibing the error.  Defaults to an empty string.
class FPError(Exception):
    def __init__(self,msg=""):
        self.msg=msg
        super().__init__(msg)


#
# +---------------------------------+
# |                                 |
# |    DFP Conversion Test Error    |
# |                                 |
# +---------------------------------+
#

# This class is used to raise an exception during floating point testing.
# Instance Argument:
#    msg    a string descibing the error.  Defaults to an empty string.
class TestError(Exception):
    def __init__(self,msg=""):
        self.msg=msg
        super().__init__(msg)


#
# +-------------------------------------+
# |                                     |
# |    Floating Point Datum Creation    |
# |                                     |
# +-------------------------------------+
#

# Floating Point String recognition regular expression pattern:
String_Pattern=\
        "(?P<sign>[+-])?(?P<int>[0-9]+)?(?P<frac>\.[0-9]*)?"\
        "(?P<exp>[eE][+-]?[0-9]+)?(?P<rmode>[rR][0-9]+)?\Z"

# Use the BFP function to create a binary floating point datum
# Use the DFP function to create a decimal floating point datum
# Use the HFP function to create a hexadecimal floating point datum
#
# Each function accepts a string defining the floating point datum being encoded.
#
# It has this format: 
#      [+-] [digits] [.[digits]] [e [+-]digits] [r digits]
#
# where:
#       +-           - is an optional sign
#       digits       - is one or more optional decimal integer digits
#       .[digits]    - is optional fractional decimal digits
#       e [+-]digits - is the optional base 10 exponent
#       r digits     - is an optional embedded numeric rounding mode
#
# Either the decimal integer or fraction digits is required.
# While the above description format has spaces, the string itself may not.
#
# Call the returned object's to_bytes() method to encode the datum in its
# interchange format as a sequence of bytes.

# Returns the binary floating point subclass instantiated with the supplied
# arguments:
#   string    A parsable string defining the binary floating point datum.  The 
#             string may contain an embedded rounding mode following the floating
#             point constant value.  The match object alternative is supported.
#   length    The length of the binary floating point constant in bytes.  Defaults
#             to 8.
#   rmode     The rounding mode to be used when creating the binary floating
#             point value if not embedded in the constant string.  Specify None
#             to use the radix format default rounding mode.  Defaults to None.
#   debug     Specify True to enable debugging messages.  Defaults to False.

def BFP(string,length=8,rmode=None,mo=None,debug=False):
    if bfp_gmpy2.use_gmpy2:
        # Using gmpy2 instead of float
        return bfp_gmpy2.BFP(string,length=length,rmode=rmode,mo=mo,debug=debug)

    # Using default Python float object
    return bfp_float.BFP(string,length=length,rmode=rmode,mo=mo,debug=debug)


# Returns the decimal floating point subclass instantiated with the supplied
# arguments:
#   string    A parsable string defining the decimal floating point datum.  The 
#             string may contain an embedded rounding mode following the floating
#             point constant value.    The match object alternative is supported.
#   length    The length of the decimal floating point constant in bytes.  Defaults
#             to 8.
#   rmode     The rounding mode to be used when creating the decimal floating
#             point value if not embedded in the constant string.  Defaults to None.
#   mo        A regular expression match object that recognized a floating point
#             string using the pattern fp.String_Pattern.  The string argument
#             must be specified as True for the match object to be used.  This
#             argument is used by the ASMA assembler for floating point constant
#             creation.
#   debug     Specify True to enable debugging messages.  Defaults to False.

def DFP(string,length=8,rmode=None,mo=None,debug=False):
    return dfp.DFP(string,length=length,rmode=rmode,debug=debug)


# Returns the hexadecimal floating point subclass instantiated with the supplied
# arguments:
#   string    A parsable string defining the hexadecimal floating point datum.  
#             The string may contain an embedded rounding mode following the
#             floating point constant value.  The match object alternative is 
#             supported.
#   length    The length of the hexadecimal floating point constant in bytes.
#             Defaults to 8.
#   rmode     The rounding mode to be used when creating the hexadecimal floating
#             point value when not embedded in the constant string.  Specify 0 for
#             legacy guard digit rounding.  Defaults to None.
#   debug     Specify True to enable debugging messages.  Defaults to False.

def HFP(string,length=8,rmode=None,mo=None,debug=False):
    raise NotImplementedError("hexadecimal floating point not yes supported")


# Convert a sequence of bytes into a Python object.  The object returned
# depends upon the subclass supplying this method.
# Method Arguments:
#   typ        Requried conversion type.  Specify 'b' for binary floating point.
#              Specify 'd' for decimal floating point.  Specify 'h' for hexadecimal
#              floating point.
#   byts       A sequence of 4, 8, or 16 bytes being decoded.
#   byteorder  Specifies the byte order of the bytes being decoded.  Specify
#              'big' for big-endian, 'little' for little endian.  Defaults to
#              'little'.  Use sys.byteorder for platform byte order.
#   debug      Whether debugging messages are enabled.
# Exception:
#   FPError if an error occurs during conversion

def from_bytes(typ,byts,byteorder="little",debug=False):
    if typ == "d":
        return dfp.DFP.from_bytes(byts,byteorder=byteorder,debug=debug)
    elif typ == "b":
        # Remove this raise statement when BFP supported
        raise NotImplementedError(\
            "%s - from_bytes() - binary conversion not yet supported" \
                % this_module)
        if bfp_gmpy2.use_gmpy2:
            return bfp_gmpy2.BFP.from_bytes(byts,byteorder=byteorder,debug=debug)
        else:
            return bfp_float.BFP.from_bytes(byts,byteorder=byteorder,debug=debug)
    elif typ == "h":
        # Remove this raise statement when HFP supported
        raise NotImplementedError(\
            "%s - from_bytes() - hexadecimal conversion not yet supported" \
                % this_module)
        return hfp.HFP.from_bytes(byts,byteorder=byteorder,debug=debug)
    else:
        raise ValueError("%s - from_bytes() - argument 'typ' must be 'b', 'd' or "\
            "'h': %s" % (this_module,typ))
      


#
# +---------------------------------------------+
# |                                             |
# |    Generic Floating Point Rounding Modes    |
# |                                             |
# +---------------------------------------------+
#

# The rounding_mode class is the base class for all rounding operations.  Each
# rounding mode is a subclass that implements the _round_mode() method.  The algorithm
# used by the subclass is embedded within this method.  Various instance and 
# class static methods are available for implementation of the algorithm.
#
# Rounding requires three inputs:
#   - the base of the floating point value
#   - the coefficient (significant, or fraction) of the floating point value
#   - the signed exponent of the floating point value
#
# The base and exponent are integers.  The coefficient is a list of digits within
# the base of the value.  All rounding operations are performed from the scientific
# notation view.


# Defines the attributes required by the generic rounder
# Instance Arguments:
#   length  the interchange format length in bytes
#   base    the base of the floating point object
#   prec    the precision of the object
#   min     the minimum signed exponent for this format
#   max     the maximum signed exponent for this format
#   bias    the bias applied to the signed exponent to create the unsigned exponent.
#   luv     Whether this is a scientific view (True) or integer view (False)
#   special the fp.Special subclass for this base
class FPAttr(object):
    def __init__(self,length,base,prec,min,max,bias,luv,special):
        self.length=length     # Floating point interchange format length in bytes
        self.base=base         # Numeric base of the floating point format
        self.prec=prec         # Precision of the floating point format in base digits
        self.min=min           # Minimum signed exponent
        self.max=max           # Maximum signed exponent
        self.bias=bias         # view bias
        self.sci=luv           # Whether scitentific (True) or integer (False) view
        self.special=special() # fp.Special subclass

        # Minimum signed exponent that can be subnormalized
        self.tiny=self.min-self.prec-1

    def __str__(self):
        return "FPAttr - length:%s base:%s prec:%s min:%s max:%s bias:%s" \
            % (self.length,self.base,self.prec,self.min,self.max,self.bias)

    # Returns the special value hexadecimal string corresponing to the supplied name
    # Exceptions:
    #   KeyError if string is not a valid special value name
    def special_value(self,string):
        return self.special.hexadecimal(string,self.length)


#
# +-----------------------------+
# |                             |
# |    Floating Point Number    |
# |                             |
# +-----------------------------+
#

# The following rounding modes are supported for each radix.  Either the module
# attribute or the number may be used.

# BFP Rounding Modes:
BFP_DEFAULT = 4
BFP_HALF_UP = 1
BFP_HALF_EVEN = 4   # Round ties to even
BFP_DOWN = 5        # Rount to zero, truncate
BFP_CEILING = 6     # Rount towards +infinity
BFP_FLOOR = 7       # Round towards -infinity

# DFP Rounding Modes:
DFP_DEFAULT = 12
DFP_HALF_EVEN = 8
DFP_DOWN = 9
DFP_CEILING = 10
DFP_FLOOR = 11
DFP_HALF_UP = 12    # Default rounding mode for DFP
DFP_HALF_DOWN = 13
DFP_UP = 14
DFP_05UP = 15

# HFP Rounding Modes:
HFP_GUARD = 0       # Legacy guard digit based rounding (May not be embedded)
HFP_DEFAULT = 1
HFP_HALF_UP = 1     # Default rounding mode for HFP
HFP_HALF_EVEN = 4
HFP_DOWN = 5
HFP_CEILING = 6
HFP_FLOOR = 7

# This object represents any floating point number (but not a special value).
# It is the internal representation of a number on which all of the other
# floating point modules operate.  Each type of floating point is expected to
# subclass this object and add any type specific functionality.  It forms the
# basis of all rounding and denormalization actions.
#
# Instance Arguments:
#   sign   The sign of the floating point number.  0 for positive.  1 for negative
#   exp    A signed exponent.  The type of floating point number dictates bounds
#   coef   A list of integers constituting the significand of the number.
#   base   The base of the floating point number
#   rounding  The requested rounding mode for the number.  Specify None for the 
#             defautl rounding mode.  Defaults to None.  See the above set of
#             modules attributes and numbers for valid values of this argument.
# Exception:
#   FPError if the requested rounding mode is invalid or not supported for the base.
class FP_Number(object):
    chars="0123456789ABCDEF"

    # Dictionary of digits by base:
    base_dig={2:"01",10:"0123456789",16:"0123456789ABCDEF"}

    # Dictionary of radix rounding mode dictionaries.  See init() static method
    rounding_modes=None

    @staticmethod
    def all_zeros(digits):
        for d in digits:
            if d != 0:
                return False
        return True

    @staticmethod
    def init():
        cls=FP_Number
        bfp={6:cls._round_ceiling,
             5:cls._round_down,
             7:cls._round_floor,
             4:cls._round_half_even,
             1:cls._round_half_up,
             None:cls._round_half_even}

        dfp={10:cls._round_ceiling,
             9:cls._round_down,
             11:cls._round_floor,
             13:cls._round_half_down,
             8:cls._round_half_even,
             12:cls._round_half_up,
             14:cls._round_up,
             15:cls._round_05up,
             None:cls._round_half_even}

        hfp={6:cls._round_ceiling,
             5:cls._round_down,
             7:cls._round_floor,
             4:cls._round_half_even,
             1:cls._round_half_up,
             0:cls._round_guard_digit,
             None:cls._round_half_even}

        cls.rounding_modes={2:bfp,10:dfp,16:hfp}

    # Returns the method that performs the rounding mode
    # Method Arguments:
    #   base  the floating point radix base as an integer
    #   rnum  the rounding mode as an integer or None for the default
    @staticmethod
    def get_rounding_method(base,rnum):
        try:
            modes=FP_Number.rounding_modes[base]
        except KeyError:
            raise ValueError("%s invalid floating point base: %s" \
                % (eloc(self,"mode"),base)) from None

        if rnum is None:
            self.rounding=modes[None]
        else:
            try:
                return modes[rnum]
            except KeyError:
                raise FPError(msg="base %s rounding mode invalid: %s" \
                    % (base,number)) from None

    def __init__(self,sign,exp,coef,base,attr,rounding=None,debug=False):
        assert base in [2,10,16],\
            "%s 'base' argument must be 2, 10, or 16: %s" \
                 % (eloc(self,"__init__"),base)
        assert sign in [0,1],\
            "%s 'sign' argument must be 0, or 1: %s" \
                 % (eloc(self,"__init__"),sign)
        assert isinstance(exp,int),\
            "%s 'exp' argument must an integer: %s" \
                 % (eloc(self,"__init__"),exp)
        assert isinstance(coef,list),\
            "%s 'coef' argument must a list: %s" \
                 % (eloc(self,"__init__"),coef)
        assert isinstance(attr,FPAttr),\
            "%s 'attr' argument must a FPAttr object: %s" \
                 % (eloc(self,"__init__"),attr)

        self.debug=debug         # Remember debug flag
        self.sign=sign           # The FP number's sign
        self.exp=exp             # The FP number's signed exponent
        self.coef=coef           # The FP number's significand
        self.base=base           # The FP number's base
        self.attr=attr           # Radix and number length attributes
        self.rmode=rounding      # Supplied rounding mode
        self.rounding=None       # Rounding method of the specified mode

        # Floating Point number conditions.  All are mutually exclusive
        self.overflow=False      # See subclass provided overflow_detect() method
        self.subnormalize=False  # See subclass provided subnormal_detect() method
        self.underflow=False     # See subclass provided underflow_detect() method

        # When special values result from overflow or underflow conditions
        self.is_special=None     # The hexadecimal string of the special value

        if __debug__:
            self._ck_digits(self.coef)

        # The FP number's rounding mode method
        self.rounding=FP_Number.get_rounding_method(self.base,rounding)
        assert self.rounding is not None,\
            "%s self.rounding must not be None" % eloc(self,"__init__")

        if __debug__:
            if self.debug:
                print("%s %s" % (eloc(self,"__init__"),self))

    def __str__(self):
        s=""
        for d in self.coef:
            s="%s%s" % (s,d)
        return "%s sign:%s exp:%s frac:%s rmode:%s rmode_method:%s"\
            % (self.__class__.__name__,self.sign,self.exp,s,self.rmode,self.rounding)

    # Check that all digits in a digits list is valid for the number's base
    # Method Arguments:
    #   digits    a list of integers, each digit an integer
    # Excpetion:
    #   ValueError is raised if the degits are not integers or not valid for the base
    def _ck_digits(self,digits):
        base=self.base
        for n,d in enumerate(digits):
            if isinstance(d,int) and d>=0 and d<base:
                continue
            else:
                raise ValueError("%s digit %s, %s, not valid for base %s in: %s" \
                        % (eloc(self,"_ck_digits"),n+1,d,base,digits))

    # Convert the significand digits list into an integer
    # Method Argument:
    #   drop   Specify True to ignore the leading digit in the fraction.  
    #          Defaults to False.
    def _coef2int(self,drop=False):
        return int(self._coef2str(drop=drop),self.base)

    # Convert the significand digits list into a digit string
    # Method Argument:
    #   drop   Specify True to ignore the leading digit in the fraction.
    #          Defaults to False.
    # Returns:
    #   a string of the converted digits list
    def _coef2str(self,drop=False):
        if drop:
            digits=self.frac[1:]
        else:
            digits=self.frac

        s=[]
        for d in digits:
            s.append(FP_Number.chars[d])
        return "".join(s)

    # Compare a set of supplied digits to half of the digits.  Half if defined
    # relative to the base of the number.
    # Returns:
    #   1   if the digits are greater than half
    #   0   if the digits are exactly equal half
    #  -1   if the digits are less than half.
    def _compare_to_half(self,digits):
        # Create 'half' as the middle digit followed by as many zero's are required
        # by he supplied list of digits
        half=self.base//2
        half=[half,]
        zero_digits=len(digits)-1
        zeros=[0,]*zero_digits
        half.extend(zeros)

        # Perform a digit by digit comparison of 'half' and the supplied digits.
        for n in range(len(digits)):
            d=digits[n]
            h=half[n]
            if d>h:
                return 1      # Supplied digits greater than 'half'
            elif d<h:
                return -1     # Supplied digits less than 'half'.
            # Otherwise the digits are equal, compare next digits

        # 'half' and supplied digits compare exactly equal
        return 0

    # Detects conditions and handles them
    # Returns:
    #   True if a condition was detected and handled
    #   False if no condition detected
    #   None if previous condition detected
    def _detect_conditions(self):
        if self.overflow or self.underflow or self.subnormalize:
            return None
        if self._overflow_detect():
            self._overflow_set()
            return True
        if self._underflow_detect():
            self._underflow_set()
            return True
        if self._subnormal_detect():
            self._subnormal_set()
            return True
        return False

    # Perform an increment of the kept coefficient digits by 1.  
    #
    # Note: If there is a carry out of the first digit, the result may be longer
    # than the input coefficients.  The caller of this method must detect this
    # situation and re-apply the rounding algorithm.
    # 
    # Method Arguments:
    #   digits   the list of coefficient digits being incremented by 1
    #   exp      the exponent of the coefficient
    # Returns:
    #   a tuple  tuple[0] is the incremented coefficient digits
    #            tuple[1] is the adjusted exponent.
    def _increment(self,digits,exp):
        addend=[0,]*len(digits)
        addend[-1]=1
        result=[None,]*len(digits)
        carry=0
        exp=self.exp
        for n in range(len(digits)-1,-1,-1):
            d=digits[n]
            a=addend[n]
            r=d+a+carry
            incarry=carry
            if r<10:
                result[n]=r
                carry=0
            else:
                r=r-10
                carry=1
                result[n]=r
            if __debug__:
                if self.debug:
                    print("%s digit:%s  %s + %s + %s = %s carry:%s result: %s" \
                        % (eloc(self,"_increment"),n,d,a,incarry,r,carry,result))

        if carry:
            # This only happens if all input digits are the highest of the base:
            # 1 for base 2, 9 for base 10, or 15 for base 16
            exp+=1
            new_res=[1,]
            new_res.extend(result[:-1])
            result=new_res

        if __debug__:
            if self.debug:
                print("%s result: %s" % (eloc(self,"_increment"),result))
        return (result,exp)

    def _is_greater_than_half(self,digits):
         return 1 == self._compare_to_half(digits)

    def _is_half(self,digits):
         return 0 == self._compare_to_half(digits)

    def _is_half_or_greater(self,digits):
        if digits[0] < ( self.base//2 ):
             return False
        return True

    def _list2str(self,digits):
        dig=FP_Number.base_dig[self.base]
        s=""
        for n in digits:
            s="%s%s" % (s,dig[n])
        return s

    def _is_less_than_half(digits):
        return -1 == self._compare_to_half(digits)

    # Return the rounding mode method for a specific floating point base and 
    # mode number
    #
    # Method Arguments:
    #   number The floating point mode number being requested.  Specify None to 
    #          return the default rounding mode subclass for the base.
    # Returns:
    #   the rounding_mode method defined for the FP radix and number
    # Exception:
    #   FPError if rounding mode is invalid for a given floating point base
    def _mode(self,number=None):
        try:
            modes=FP_Number.rounding_modes[base]
        except KeyError:
            raise ValueError("%s invalid floating point base: %s" \
                % (eloc(self,"mode"),base)) from None

        if number is None:
            return modes[None]

        try:
            return modes[number]
        except KeyError:
                pass

        raise FPError(msg="rouning mode invalid for floating point base %s: %s" \
            % (base,number)) from None

    # Examine the signed exponent for overflow and set attribute self.overflow to
    # True if it is detected.
    # Returns:
    #   True   if overflow detected
    #   False  if overflow not detected
    # Note: A subclass may override this method as appropriate
    def _overflow_detect(self): 
        self.overflow=self.exp > self.attr.max
        if __debug__:
            if self.debug:
                print("%s exponent: %s <> max exponent: %s exponent overflow: %s" \
                    % (eloc(self,"_overflow_detect"),self.exp,self.attr.max,\
                        self.overflow))
        return self.overflow

    # Set the special value negative or positive infinity if overflow detected
    def _overflow_set_infinity(self):
        assert self.overflow,\
            "%s overflow condition not set: %s" \
                % (eloc(self,"_overflow_set"),self.overflow)

        if self.sign:
            # Negative
            self.is_special=self._special_value("-(inf)")
        else:
            # Positive
            self.is_special=self._special_value("(inf)")

    # Pad the significand with zeros:
    #   - on the right (luv=True) for scientific view, or
    #   - on the left (luv=False) for integer view.
    # Method Arguments:
    #   prec  resulting precision with padding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _pad(self,prec,luv=False):
        assert len(self.coef) < prec,\
            "%s coef (%s digits) too long for padding to precision %s" \
                % (eloc(self,"_pad"),len(self.coef),prec)
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_pad")
                if luv:
                    print("%s padding scientific (LUV) view to precision: %s" \
                        % (cls_str,prec))
                else:
                    print("%s padding integer (RUV) view to precision: %s" \
                        % (cls_str,prec))

        zeros=prec - len(self.coef)
        pad=[0,] * zeros
        if not luv:
            # Integer view
            pad.extend(self.coef)
            self.coef=pad
        else:
            self.coef.extend(pad)
        if __debug__:
            if self.debug:
                print("%s padded coefficient to precision %s: %s" \
                    % (cls_str,prec,self.coef))

    # Round toward +infinity
    #   BFP mode: 6
    #   DFP mode: 10
    #   HFP mode: 6
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_ceiling(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_ceiling"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        if ( self.sign == 1 ) or ( FP_Number.all_zeros(ignore) ):
            self.coef=keep
        else:
            self.coef,self.exp=self._increment(keep,self.exp)
        if not luv:
            self.exp+=len(ignore)

    # Round towards 0, truncate
    #  BFP Mode: 5
    #  DFP Mode: 9
    #  HFP Mode: 5
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_down(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_down"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        self.coef=keep
        if not luv:
            self.exp+=len(ignore)

    # Round toward -infinity
    #  BFP Mode: 7
    #  DFP Mode: 11
    #  HFP Mode: 7
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_floor(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_floor"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        if ( self.sign == 0 ) or ( FP_Number.all_zeros(ignore) ):
            self.coef=keep
        else:
            self.coef,self.exp=self._increment(keep,self.exp)
        if not luv:
            self.exp+=len(ignore)

    # Round With Guard Digit
    #  BFP Mode: not supported
    #  DFP Mode: not supported
    #  HFP Mode: 0
    def _round_guard_digit(self,prec):
        raise NotImplementedError(\
            "%s hexadecimal floating point guard digit rounding to be devemeloped" \
                % eloc(self,"_round_guard_digit"))

    # Round Half Down
    #   BFP Mode: not supported
    #   DFP Mode: 13
    #   HFP Mode: not supported
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_half_down(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_half_down"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        res=self._compare_to_half(ignore)
        if res>0:
            # discarded digits are more than half, so increment the coefficient
            self.coef,self.exp=self._increment(keep,self.exp)
        else:
            self.coef=keep
        if not luv:
            self.exp+=len(ignore)

    # Round Half Even
    #  BFP Mode: 4 - default
    #  DFP Mode: 8
    #  HFP Mode: 4
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_half_even(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_half_even"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        res=self._compare_to_half(ignore)
        if res>0:
            # discarded digits are more than half, so increment the coefficient
            self.coef,self.exp=self._increment(keep,self.exp)
            if len(self.coef)>prec:
                    # If we had overflow from the left most digit, round again
                    self._round_half_even(prec)
        elif res<0:
            # discarded digits are less than half, so just ignore the discarded digits
            self.coef=keep
        else:
            # Discarded digits are exactly half so need to look at the last kept
            # digit.  If it is not even, increment the kept digits (making them
            # even).  Otherwise keep the even digits.
            not_even = keep[-1] % 2
            if not_even:
                self.coef,self.exp=self._increment(keep,self.exp)
            else:
                self.coef=keep
        if not luv:
            self.exp+=len(ignore)

    # Round Half Up
    #  BFP Mode: 1
    #  DFP Mode: 12 - default
    #  HFP Mode: 1
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_half_up(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_half_up"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        if not self._is_half_or_greater(ignore):
            # ignored digits are less than half, so throw them away
            self.coef=keep
        else:
            # Ignored digits are half or greater, so increment the kept digits by 1
            self.coef,self.exp=self._increment(keep,self.exp)
        if not luv:
            self.exp+=len(ignore)

    # Round Away from Zero
    #  BFP Mode: not supported
    #  DFP Mode: 14
    #  HFP Mode: not supported
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _round_up(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_up"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        if not FP_Number.all_zeros(ignore):
            self.coef,self.exp=self._increment(keep,self.exp)
        if not luv:
            self.exp+=len(ignore)

    # Round Zero of Five Away From Zero
    #  BFP Mode: not supported
    #  DFP Mode: 15
    #  HFP Mode: not supported
    def _round_05up(self,prec,luv=False):
        assert len(self.coef) > prec,\
            "%s coef (%s digits) too short for rounding to precision %s" \
                % (eloc(self,"_round_05up"),len(self.coef),prec)

        keep,ignore=self._split(prec)
        digit=keep[-1]
        if ( digit == 0 or digit == 5 ) and not FP_Number.all_zeros(ignore):
            self.coef,self.exp=self._increment(keep,self.exp)
        else:
            self.coef=keep
        if not luv:
            self.exp+=len(ignore)

    # Apply a rounding mode algorithm to the coefficient and signed exponent.
    # Method Arguments:
    #   prec  resulting precision with rounding
    #   luv   Whether integer view (False) or scientific view (True) in use
    def _rounding(self,prec,luv=False):
        while len(self.coef)>prec:
            # This loop usually is only performed onece, but if there is carry out
            # from the left-most significand digit, a second use of the algorithm
            # is required.
            if __debug__:
                if self.debug:
                    print("%s calling: %s" % (eloc(self,"_rounding"),self.rounding))
            self.rounding(self,prec,luv=luv)

    # Returns the hexadecimal string of a special value
    def _special_value(self,string):
        return self.attr.special_value(string)

    # This method splits the coefficient into two pieces: the portion of the
    # coefficient being retained and the portion of the coefficient that is being
    # discarded.  Either piece may participate in the round process depending upon
    # the algorithm.
    # 
    # Method Argument:
    #   prec   The precision to which the coefficient is being rounded as an integer.
    # Returns:
    #   a tuple: tuple[0] is the list of coefficient digits being rounded
    #            tuple[1] is the list of coefficient digits being discared.
    def _split(self,prec):
        discards=len(self.coef)-prec
        assert discards>0,\
            "%s can not discard digits (for precision %s) from coeficient "\
                "(%s digits)" % (eloc(self,"discards"),prec,len(self.coef))
        ignore=self.coef[prec:]
        keep=self.coef[:prec]
        return (keep,ignore)

    def _str2list(self,string):
        base=self.base
        lst=[]
        for c in string:
            lst.append(int(c,base))
        return lst

    # Examine the signed exponent for subnormalization required and sets the 
    # attribute self.subnormalize to True
    # Returns:
    #   True   if the number needs to be subnormalized
    #   False  if the number does not need subnormalization.
    # Note: A subclass may override this method as appropriate
    def _subnormal_detect(self):
        self.subnormalize = self.exp>=self.attr.tiny and self.exp<self.attr.min
        if __debug__:
            if self.debug:
                print("%s exponent: %s >= tiny exponent: %s and < minimum: %s "
                    "subnormal: %s" \
                    % (eloc(self,"_subnormal_detect"),self.exp,self.attr.tiny,\
                        self.attr.min,self.subnormalize))
        return self.subnormalize

    # This method peforms denomalization to accommodate signed exponents less than
    # the minimum but greater than or equal to tiny
    def _subnormal_set_default(self):
        # Calculate the number of zero digis to append on the left
        cur_exp=self.exp
        zero_digits=self.attr.min - self.exp
        if __debug__:
            if self.debug:
                cls_str=eloc(self,"_subnormal_set_default")
                print("%s zero left digits: %s = minimum %s - exponent: %s" \
                    % (cls_str,zero_digits,self.attr.min,cur_exp))

        zeros = [0,] * zero_digits
        zeros.extend(self.coef)
        self.coef=zeros
        self.exp=cur_exp + zero_digits
        if __debug__:
            if self.debug:
                print("%s adjusted exponent: %s = exponent: %s + zero digits: %s"\
                    % (cls_str,self.exp,cur_exp,zero_digits))
                print("%s adjusted coeficient: %s" % (cls_str,self.coef))

    # Examine the signed exponent for underflow and set attribute self.underflow to
    # True if it occurred.
    # Returns:
    #   True   if underflow detected
    #   False  if underflow not detected
    # Note: A subclass may override this method as appropriate
    def _underflow_detect(self):
        self.underflow = self.exp<self.attr.tiny
        if __debug__:
            if self.debug:
                print("%s exponent: %s <> tiny exponent: %s exponent underflow: %s" \
                    % (eloc(self,"_underflow_detect"),self.exp,self.attr.tiny,\
                        self.underflow))
        return self.underflow

    # Perform the rounding to a specified precision.  Larger precision pads the
    # instantiated coefficient.  Smaller precision performs the rounding algorithm of
    # the rounding mode.  If the precision is the same as the instantiated
    # coefficient, the coefficient and exponent are unchanged.
    #
    # Method Argument:
    #   prec   the precision to which the coefficient is being rounded
    #   luv   Whether integer view (False) or scientific view (True) in use
    # Exception:
    #   FPError may result if a problem occurs during rounding
    def round(self,prec,luv=False):
        assert not self.is_special,\
            "%s special values may not be rounded" % eloc(self,"round")

        if len(self.coef)<prec:
            if __debug__:
                if self.debug:
                    print("%s padding coef: len(coef) %s < precision %s" \
                        % (eloc(self,"round"),len(self.coef),prec))
            self._pad(prec,luv=luv)

        elif len(self.coef)>prec:
            if __debug__:
                if self.debug:
                    print("%s rounding coef: len(coef) %s > precision %s" \
                        % (eloc(self,"round"),len(self.coef),prec))
            self._rounding(prec,luv=luv)
            return

        else:
            if __debug__:
                if self.debug:
                    print("% taking no action on coef: len(coef) %s == precision %s" \
                        % (eloc(self,"round"),len(self.coef),prec))
            pass

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


# Initialize the rounding mode dictionaries
FP_Number.init()

#
# +-------------------------------------+
# |                                     |
# |    Floating Point Special Values    |
# |                                     |
# +-------------------------------------+
#

# This class manages the special values for a floating point type.  Each type
# supplies its own definition
class FP_Special(object):

    @staticmethod
    def to_bytes(special,byteorder="little"):
        length=len(special) // 2
        bin=int(special,16)
        return bin.to_bytes(length,byteorder=byteorder,signed=False)

    def __init__(self):
        # These dictionaries return a integer suitable for bytes conversion
        self.L4={}     # Dictionary of 4-byte special values
        self.L8={}     # Dictionary of 8-byte special values
        self.L16={}    # Dictionary of 16-byt special values

        # Top level access to special values is by length
        self.ByL={4:self.L4,8:self.L8,16:self.L16}
        self.build()

    # Builds all of the defined special values for the subclass.  Each subclass
    # must provide this method.
    def build(self):
        raise NotImplementedError("%s subclass %s must provide build() method"\
            % (eloc(self,"build"),self.__class__.__name__))

    def define(self,name,hexdata):
        assert isinstance(name,str) and len(name)>0,\
            "%s 'name' arguement must be a not-empty string: '%s'" \
                % (eloc(self,"define"),name)
        assert isinstance(hexdata,str) and len(hexdata) in [8,16,32],\
            "%s 'hexdata' argument,'%s', length must be 8, 16, or 32 digits: %s" \
                % (eloc(self,"define"),hexdata,len(hexdata))

        length=len(hexdata) // 2
        dct=self.ByL[length]

        try:
            dct[name]
            raise ValueError("%s special value already defined: %s" \
                % (eloc(self,"define"),name))
        except KeyError:
            pass
        try:
            dct[name]=hexdata
        except ValueError:
            raise ValueError("%s 'hexdata' argument for special value %s "\
                "contains invalid hex data: '%s'" \
                    % (eloc(self,"define"),name,hexdata)) from None


    # Retrieve the defined special value
    # Method Argument:
    #   name       the defined name of the special value
    #   length     the length of the special value in bytes
    # Returns:
    #   a string of hexadicmal digits of the defined special value 
    #   or None if the special value name is not defined.
    # Exception:
    #   KeyError if the special value is not defined
    def hexadecimal(self,name,length):
        # Fetch the dictionary that has the special values defined for the required
        # length.
        try:
            dct=self.ByL[length]
        except KeyError:
            raise ValueError("%s special value length invalid: %s" \
                % (eloc(self,"to_bytes"),length)) from None

        # Retrieve the defined encoded special value from the supplied name
        return dct[name.lower()]


#
# +----------------------------------------+
# |                                        |
# |    Floating Point Object Base Class    |
# |                                        |
# +----------------------------------------+
#

# This class is the base class for all generic floating point objects.
# Instance Arguments:
#   string   a string representing the decimal value being encoded.
#            It has this format: [+-] digits [.digits] [e [+-]digits] [r digits]
#               e [+-] digits - is the optional base 10 exponent
#               r digits      - is a numeric rounding mode
#            While the above description has spaces, the string may not
#
#            Alternatively, a match object produced by matching against the
#            fp.String_Pattern module attribute may be supplied.  This is
#            used when integrating the floating point tools with the ASMA assembler.
#   length   The length of the floating point object to be created.
#   rmode    The rounding mode to be used.  When rmode is specified the string
#            argument may not contain the rounding mode.  Use the Python value
#            for the appropriate underlying values.
class FP(object):
    parse=re.compile(String_Pattern)   # Parse a floating point string
    sign_str={"+":0,"-":1,"":0}        # Convert string sign to value

    Special=None   # FP_Special object for the subclass generating special values
    # Each subclass will provide this object used by this super class to_bytes() 
    # method

    # This method turns a sequence of bytes into a string of hex digits with each
    # byte separated by a space
    # Method Argument:
    #   byts   The bytes sequence being converted
    # Returns:
    #   a string of hexadecimal bytes.
    @staticmethod
    def bytes2str(byts,space=True):
        if space:
            sp=" "
        else:
            sp=""
        s=""
        for byt in byts:
            hexbyte="%02X" % byt
            s="%s%s%s" % (s,sp,hexbyte)
        if space:
            return s[1:]
        return s

    # This method turns a sequence of bytes into a string of hex digits with each
    # byte separated by a space
    # Method Argument:
    #   string   A string of hexadecimal digits
    # Returns:
    #   a sequence of bytes from the string
    @staticmethod
    def str2bytes(string):
        b=bytearray(0)
        s=""
        for n in range(0,len(string),2):
            h=string[n:n+2]
            h="0%s" % h
            byt=int(h,16)
            b.append(byt)
        return bytes(b)

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
        raise NotImplementedError("class %s must provide from_bytes() class method"\
            % cls.__name__)

    def __init__(self,string,length=8,rmode=None,debug=False):
        if __debug__:
            if debug:
                cls_str=eloc(self,"__init__")
                print("%s string:%s length=%s rmode=%s debug=%s" \
                    % (cls_str,string,length,rmode,debug))
        assert string is not None,\
            "%s 'string' argument must not be None" % eloc(self,"__init__")

        # Instantiating arguments:
        self.con_str=None       # The input constant string is set below
        self.length=length      # Length of the floating point object
        self.rmode=rmode        # Rounding mode supplied outside of the string
        self.debug=debug        # Remember debug status

        # This object is created for floating point numbers (not special values).
        self.mo=None            # Regular expression match object
        self.mod=None           # The regular expression matcho object dictionary

        # These attributes are used by the subclass to create the underlying Python
        # object supporting the floating point base (binary, decimal, or 
        # hexadecimal).  They are established by parsing the constant 'string'
        # argument.
        self.fpstr=None    # floating point string without embedded rounding rmode
        self.sign=None     # Sign of the floating point value integers 0 or 1.
        self.int_str=None  # Integer digits from the constant string (as a string)
        self.frac_str=None # Fraction digits from the constant string (as a string)
        self.exponent=None # Exponent from the constant string as a signed integer
        self.rm_num=None   # Constant string embedded rounding mode (as an integer)
        self.rmodeo=None   # Object rounding mode

        # If the constant string does not parse, an attempt is made to determine
        # if this is a special value.  If so, this attribute is a string of 
        # hexadecimal digits that can be used to create the special value's sequence
        # of bytes:
        self.is_special=None

      # Subclass created objects

        # Python floating point object.  See subclass create() method
        self.fpo=None

        # FP_Number object.  See subclass to_number() method
        self.number=None

      # Analyze the floating point constant 'string' argument.

        # Use the regular expression module to parse the constant string or use
        # the externally supplied match object
        if isinstance(string,str):
            self.con_str=string
            self.mo=FP.parse.match(string)
        else:
            # No mechanism exists for detecting a regular expression match object.
            # We must assume the 'string' argument when not a string is a match
            # object.  The assumption is also made that the match object matched
            # the pattern defined above in the String_Pattern module
            self.mo=string
            self.con_str=string.string

        if self.mo is not None:
            if __debug__:
                if debug:
                    print("%s match object:" % cls_str) 
                    retest.print_mo(self.mo,indent="    ")
            self.mod=mod=self.mo.groupdict()

        if self.mo is None or ( self.mod["int"] is None and self.mod["frac"] is None ):
            # match did not occur or match does not contain a required component
            try:
                self.is_special=self.__class__.Special.hexadecimal(\
                    self.con_str,self.length)
            except KeyError:
                raise FPError(\
                    msg="unrecognized floating point constant: %s" % self.con_str)\
                        from None
            return

        # Analyze the constant sign
        str_sign=self._mo_str(mod,"sign")
        self.sign=FP.sign_str[str_sign]

        # Analyze the integer part of the constant
        self.int_str=str_int=self._mo_str(mod,"int")

        # Analyze the fraction part of the constant if present
        frac=str_frac=self._mo_str(mod,"frac")
        if len(frac)>0:
            if frac == ".":
                frac = ""
            else:
                frac = frac[1:]   # Drop the initiating period
        self.frac_str=frac

        # Analyze the exponant of the constant if present
        str_exp=self._mo_str(mod,"exp")
        if len(str_exp)>0:
            self.exponent=int(str_exp[1:],10)

        # Create the floating point string without the rounding mode.  Python
        # does not understand the rounding mode as part of the floating point
        # value, but some other contexts do.
        self.fpstr="%s%s%s%s" % (str_sign,str_int,str_frac,str_exp)

        # Analyze the rounding mode embedded in the constant if present
        #   a 'R' followed by one or more decimal digits
        str_rmode=mod["rmode"]
        if __debug__:
            if self.debug:
                print("%s embeddded rmode: '%s'" % (cls_str,str_rmode))
        if str_rmode is not None:
            self.rm_num=int(str_rmode[1:],10)
            if __debug__:
                if self.debug:
                    print("%s embedded rmode integer: %s" % (cls_str,self.rm_num))

        if rmode is not None and str_rmode is not None:
            raise FPError(msg=\
                "argument 'rmode', %s, may not be supplied with rounding mode "
                    "embedded in the 'string' argument: %s" % (rmode,str_rmode))

        if rmode is None and str_rmode is None:
            # Neither rounding mode is supplied so set the default for both
            self.rmodeo,self.rm_num = self.default()
            if __debug__:
                if self.debug:
                    print("%s rmode being set to default: %s" \
                        % (cls_str,self.rmodeo))

        elif str_rmode is not None and rmode is None:
            # Rounding mode embedded in 'string' argument without 'rmode' argument
            assert isinstance(self.rm_num,int),\
                "%s rm_num attribute must be an integer: %s" % (cls_str,self.rm_num)
            self.rmodeo = self.rm_num
            if __debug__:
                if self.debug:
                    print("%s rmode being set from embedded string value: %s" \
                        % (cls_str,self.rmodeo))

        elif str_rmode is None and rmode is not None:
            # Rounding mode only supplied by 'rmode' argument.
            if __debug__:
                if self.debug:
                    print("%s rmode being set from instance argument rmode: %s" \
                        % (cls_str,rmode))
            self.rmodeo = rmode
        assert isinstance(self.rmodeo,int),\
            "%s rmodeo attribut must be an integer: %s" % (cls_str,self.rmodeo)

        # Create the Python floating point object
        self.fpo=self.create()

        # Convert the Python floating point object to a FP_Number object
        self.number=self.to_number(self.fpo)

    def __str__(self):
        return "%s: sign:%s %s.%s exp:%s length:%s rmode:%s" \
            % (self.__class__.__name__,self.sign,self.int_str,self.frac_str,\
                self.exponent,self.length,self.rmode)

    # Replaces the group dictionary None (for a missing group in the regular 
    # expression) with an empty string.
    def _mo_str(self,grp,key):
        string=grp[key]
        if string is None:
            return ""
        return string

    # Return the bytes from converting the floating point object.
    def to_bytes(self,byteorder="big"):
        if self.is_special:
            bin=int(self.is_special,16)
            return bin.to_bytes(self.length,byteorder=byteorder,signed=False)

        # Must be a regular number.  Use subclass to help
        return self.i_fmt(byteorder=byteorder)

  #
  # These methods must be supplied by the base (binary, decimal, or hexadecimal)
  # specific subclass.
  #

    # Return both the default embedded rounding mode the the default Python 
    # rounding mode values as a tuple:
    #   tuple[0]  The default embedded rounding mode
    #   tuple[1]  The Python object default rounding mode
    # It is assumed that these are the same rounding algorithm, just identified
    # differently within the respecive contexts.
    def default(self):
        raise NotImplementedError("subclass %s must provide default() method" \
            % self.__class__.__name__)

    # Returns the Python object supporting the floating point type.  There are two
    # ways for the subclass to create the Python object:
    #   1  Use the floating point string constant with the embedded rounding mode
    #      removed, that is, use the 'string' argument.
    #   2. Use the various pieces of the parsed string constant, arguments 'sign'
    #      'integer', 'fraction', and 'exp' to build the object.
    # The 'rmode' is that required by the underlying object.  The subclass provides
    # this mode based upon what is found in the string constant or the instantiating
    # values.
    def create(self,*pos,**kwds):
        raise NotImplementedError("subclass %s must provide create() method" \
            % self.__class__.__name__)

    # Returns True if overflow has been detected, otherwise False.
    def has_overflow(self):
        raise NotImplementedError("subclass %s must provide has_overflow() method" \
            % self.__class__.__name__)
        
    # Returns True if underflow has been detected, otherwise False.
    def has_underflow(self):
        raise NotImplementedError("subclass %s must provide has_underflow() method" \
            % self.__class__.__name__)

    # Creates the interchange format for the FP_Number object.  Shortening and
    # rounding ocurs here.  This method is called by the FP class own to_bytes()
    # method for creation of the radix specific interchange format for floating
    # point datum.  Special values are handled directly by the FP.to_bytes() method.
    def i_fmt(self,num,rmode):
        raise NotImplementedError("subclass %s must provide i_fmt() method" \
            % self.__class__.__name__)

    # Returns True if value is subnormal, otherwise False.
    def is_subnormal(self):
        raise NotImplementedError("subclass %s must provide is_subnormal() method" \
            % self.__class__.__name__)

    # Analyze the embedded rounding number and set according to underlying Python's 
    # object's expectation.  If no embedded rounding mode is available or the
    # rounding mode is invalid or usupported, the default rounding mode is supplied.
    #
    # Note: if the underlying object uses the embedded rounding mode number directly
    # the subclass should simply return the rnum value.
    #
    # Method Argument:
    #   rnum   the embedded rounding mode if available or None.
    def rounding(self,rnum):
        raise NotImplementedError("subclass %s must provide rounding() method" \
            % self.__class__.__name__)

    # Returns a FP_Number object from an instatiated Python floating point object.
    #
    # Note: if the subclass instantiates a FP_Number object during the create()
    # method, it should simply return it when this method is called.
    def to_number(self,fpo):
        raise NotImplementedError("subclass %s must provide number() method" \
            % self.__class__.__name__)


#
# +--------------------------------------+
# |                                      |
# |    Floating Point Conversion Test    |
# |                                      |
# +--------------------------------------+
#

# Perform a conversion test on a value.
# Instance Arguments:
#   value   A hexadecimal string, a finite number string, a sequence of bytes, or
#           an integer.  A hexadecimal string, sequence of bytes, or an integer are
#           converted to its abstract representation.  A floating point string is
#           coverted into its interchange format and, if not disabled by --noar, 
#           its abstract representation.
#   length  The interchange format length into which the floating point string is
#           converted.
#   ar      Whether the abstract representation is to be included for floating point
#           string conversions.  Defaults to True.
#
# Note: a Test object subclass may be imported for use in other contexts independent
# of the TestRun object used by the command-line conversion testing interface.
class Test(object):
    has_digits=re.compile("[0-9]+")
    is_special=re.compile("(?P<sign>[+-])?(?P<lp>[\(])?(?P<val>([SsQq]?[Nn][Aa][Nn]|"\
        "[Ii][Nn][Ff]|[Mm][Aa][Xx]|[Dd]?[Mm][Ii][Nn]))(?P<rp>[\)])?\Z")
    is_hexadecimal=re.compile("[0-9A-Fa-f]+\Z")
    def __init__(self,value,length=8,ar=True,debug=False):
        assert length in [4,8,16],\
            "%s 'length' argument must be 4, 8, or 16: %s" \
                % (eloc(self,"__init__",module=this_module),length)

        # Output length for conversions to DFP interchange format
        self.length=length     # Interchange format length
        self.value=value       # Input value
        self.bits=None         # Input integer (may be from string)
        self.blist=None        # Input sequence of bytes (may be from integer)
        self.ar=ar             # Whether abstract representation is to be displayed.
        self.debug=debug       # Whether to enable debugging

        # Supplied by subclass after this class is initialized
        self.special_cnverter=None

        # Special value to be converted to interchange format
        self.special=None      # See convert_special_value() method

        # Result of convert_bits(), convert_bytes_to_dfp(), convert_hex_to_dpd()
        # methods, a dfp.dpd object
        self.dpd=None

        # Result of convert_finit_number() method, a dfp.DFP object
        self.dfp=None

    def __str__(self):
        return "%s(%s,length=%s,ar=%s,debug=%s)" \
            % (self.__class__.__name__,self.value,self.length,self.ar,self.debug)

    def convert_bits(self,val):
        self.blist=val.to_bytes(length=self.length,byteorder="big",signed=False)
        self.dpd=self.convert_bytes_to_object(self.blist)

    def convert_finite_number(self):
        self.dfp=DFP(self.value,length=self.length,debug=self.debug)
        self.blist=self.dfp.to_bytes()
        self.dpd=self.convert_bytes_to_object(self.blist)

    def convert_hex_to_object(self,string):
        mo=Test.is_hexadecimal.match(string)
        if mo is None:
            raise TestError(msg="invalide hexadecimal string: '%s'" % string)
        if not len(string) in [8,16,32]:
            raise TestError(\
                msg="hexadecimal string '0x%s' must contain 8, 16, or 32 digits: %s" \
                        % (hexstr,len(string)))
        byts=FP.str2bytes(string)
        self.blist=byts
        self.dpd=self.convert_bytes_to_object(self.blist)

    def convert_special_value(self):
        mo=Test.is_special.match(self.value)
        if mo is None or mo.end() != len(self.value):
            raise TestError(msg="unrecognized special value: '%s'" % self.value)
        #retest.print_mo(mo)
        dct=mo.groupdict()

        # Process sign
        sign=dct["sign"]
        if sign is None:
            sign=""

        # Process parenthesis
        lp=dct["lp"]
        rp=dct["rp"]
        if lp is None and rp is None:
            lp="("
            rp=")"
        elif lp == "(" and rp == ")":
            pass
        else:
            raise TestError(msg="mismatched parenthesis in special value: %s" \
                % self.value)

        # Process the value
        val=dct["val"]
        val=val.lower()

        self.special="%s%s%s%s" % (sign,lp,val,rp)
        #print("special value: '%s'" % self.special)
        hex_digits=self.special_converter.hexadecimal(self.special,self.length)
        self.blist=(FP.str2bytes(hex_digits))

    # Perform string conversions of non-empty strings
    def convert_string(self):
        value=self.value
        if len(value)>=3 and value[:2] == "0x":
            self.convert_hex_to_object(value[2:])
            # Result in self.dpd
        else:
            mo=Test.has_digits.search(value)
            if mo is None:
                self.convert_special_value()
            else:
                self.convert_finite_number()

    def display(self,indent="",string=False):
        cond=""
        if self.dfp:
            if self.dfp.has_underflow():
                cond="  UNFL"
            elif self.dfp.has_overflow():
                cond="  OVFL"
            elif self.dfp.is_subnormal():
                cond="  SUBN"
            s="%s%s" % (indent,FP.bytes2str(self.blist,space=False))
            if self.ar:
                s="%s  %s" % (s,self.dpd)
            if cond:
                s="%s%s" % (s,cond)
        elif self.special:
            s="%s%s" % (indent,FP.bytes2str(self.blist,space=False))
        else:
            s="%s%s  %s" % (indent,FP.bytes2str(self.blist,space=False),self.dpd)
        if string:
            return s
        print(s)

    # Perform the conversion test
    def run(self):
        value=self.value
        if isinstance(value,str):
            # The TestRun object only drives tests with strings.  Other sources
            # may also use a string.
            assert len(value)>0,\
                "%s 'value' argument must not be an empty string" \
                    % eloc(self,"run",module=this_module)
            self.convert_string()
        elif isinstance(value,bytes):
            # a sequence of bytes can not occur for a test by the TestRun object
            assert len(value) in [4,8,16],\
                "%s 'value' argument must not be a sequence of 4, 8, or 16 bytes: %s"\
                    % (eloc(self,"run",module=this_module),len(value))
            self.blist=value
            self.convert_bytes_to_dpd(self.blist)
            # Result in self.dpd
        elif isinstance(value,int):
            # an integer can not occur for a test by the TestRun object
            assert int>=0,\
                "%s 'value' argument must not be a negative integer" \
                    % eloc(self,"run",module=this_module)
            self.convert_bits()
            # Result is self.dpd
        else:
            raise TestError(msg="unrecognized input value: %s" % value)

  #
  # Methods that must be supplied by the subclass
  #

    # Method Arguments:
    #   byts  A sequence of bytes.
    # Returns:
    #   the object to which the sequence has been converted
    def convert_bytes_to_object(self,byts):
        raise NotImplementedError("%s subclass %s must provide "\
            "convert_bytes_to_object() method" \
                % (eloc(self,"convert_bytes_to_object"),self.__class__.__name__))


# Now that all objects used by the various floating point modules are defined
# they can be imported
#
# WARNING - DO NOT CHANGE THIS SEQUENCE
# SATK imports
import bfp_float  # Access binary floating point conversions using float objects
import bfp_gmpy2  # Access binary floating point conversions using gmpy2.mpfr objects
#import bfp       # bfp.py is not directly accessed by this module 
import dfp        # Access decimal floating point conversions
#import hfp       # hfp.py is not yet implemented


# The remainder of the module provides a command-line tool for testing floating point
# constants.  Command-line arguments may be supplied for conversion.  
#
# If the --prompt option is used, user input is queried with a prompt.  User input
# ends when either 'end' or 'quit' is entered by the user.
#
# Execute this module with the command-line option -h to see the format of the 
# command line arguments.
#
# User queried arguments are a value followed by an optional length.  The length may
# only be 4, 8, or 16.  If the length is not supplied the command-line supplied
# length applies, which defaults to 8.
#
# Regardless of the source of the input the argument or arguments supplied may be a:
#
#   - decimal floating point string followed by an optional length, or 
#   - hexadecimal string starting with the characters '0x', or
#   - a special value.
#
# Floating point string:
#
#   When a decimal floating point string is provided, the string is converted to
#   an abstract representation including a sign, an exponent, and set of digits.
#   A second optional argument may be supplied identifying the length of the
#   interchange format to which the string is converted.  If omitted, the length is
#   assumed to be 8.  The interchange format is displayed as a sequence of hexadecimal
#   digits preceded by the characters '0x'.

#   The floating point string includes an optional sign, integer and/or fraction
#   followed by an optional exponent (with or without a sign) and an optional rounding
#   mode:
#
#   [+-][integer][.[fraction]][e[+-]N...][rN...]
#
#   At least an integer or fraction must be provided.
#
# Hexadecimal string:
#
#   The hexadecimal string must start with the characters '0x' which must be followed
#   with 8, 16 or 32 hexadecimal digits.  The number of digits implies the constant
#   length.  The string is converted to an abstract representation containing a 
#   sign, an expoent, and a set of decimal digits.
#
# Special values:
#
#    A special value may be supplied followed by an optional length.  If the length
#    is not supplied it is assumed to be 8.  The special value is converted to its
#    hexadecimal string preceded by the characters '0x'.
#
#   The following special case insensitive values are supported:
#     qnan - quiet Not-a-Number
#     snan - signaling Not-a-Number
#     nan  - Not-a-Number
#     inf  - Infinity
#     max  - maximum number
#     min  - minimum number
#     dmin - minimum denormalized or subnormal number
#
#   All special values may be preceded with an optional sign.  However, negative
#   special values may only be entered when queried due to conflicts with argument
#   parsing.
#
# Note: the Test object may be imported for use in other contexts.

if __name__ == "__main__":
    # Additional Python imports when run from the command-line
    import argparse
    import sys

    # Perform the requested tests
    class TestRun(object):
        prompt_intro="\n"\
            "Welcome to the floating point test tool: %s\n"\
            "At the %sprompt enter a floating point string followed by an\n"\
            "optional interchange format length.  The length must be 4, 8, or\n"\
            "16.  If a length is not entered, the default, %s, set by the command\n"\
             "line -l or --length argument, is used."\
            "\n\nTo terminate, enter either 'end' or 'quit' (without quotation "\
            "marks) or Cntrl-C."
        def __init__(self,args):
            typ=args.t
            self.test_cls=None # Test class used by the requested -t option.
            self.prompt=None   # Prompt string
            if typ == "d":
                self.test_cls=dfp.DFP_Test
                self.prompt="DFP> "
            else:
                raise TestError(msg="command line option -t invalid: %s" % typ)
            self.args=args   # Argument parser command line arguments
            self.ar=args.noar    # Whether abstract representation printing
            self.values=args.value   # command-line values
            self.length=args.length  # Get the command-line length or default
            self.minus=args.minus    # Whehter to create a negative value
            self.debug=args.debug    # Whether conversions being debugged

        def _force_minus(self,value):
            if value[0]=="+":
                return "-%s" % value[1:]
            if value[0]=="-":
                return value
            return "-%s" % value

        def query(self):
            if not self.args.quiet:
                print(TestRun % (self.prompt,self.prompt,self.length))
            #print("\n"
            #    "Welcome to the floating point test tool: %s\n"
            #    "At the %sprompt enter a floating point string followed by an\n"
            #    "optional interchange format length.  The length must be 4, 8, or\n"
            #    "16.  If a length is not entered, the default, %s, set by the command\n"\
            #    "line -l or --length argument, is used."\
            #    "\n\nTo terminate, enter either 'end' or 'quit' (without quotation "
            #    "marks) or Cntrl-C." % (self.prompt,self.prompt,self.length))
            while True:
                string=input(self.prompt)
                if not string.isprintable():
                    print("ERROR: nonpritable characters")
                    continue
                if string.lower() in ["end","quit"]:
                    return
                args=string.split()
                if len(args) == 0:
                    continue
                if len(args) > 2:
                    print("ERROR: maximimum two arguments allowed: %s" % len(args))
                elif len(args) == 2:
                    value=args[0]
                    length=args[1]
                    try:
                        length=int(length,10)
                    except ValueError:
                        print("ERROR: unrecognized length: %s" % length)
                        continue
                    if not (length in [4,8,16]):
                        print("ERROR: invalid length argument: %s" % length)
                        continue
                elif len(args) == 1:
                    value=args[0]
                    length=self.length
                else:
                    raise ValueError("unexpected number of arguments: %s" % len(args))

                # Perform test
                tst=self.test_cls(value,length=length,ar=self.ar,debug=self.debug)
                if __debug__:
                    if self.debug:
                        print("%s %s" % (eloc(self,"query"),tst))

                try:
                    tst.run()
                except TestError as te:
                    print("ERROR: %s" % te)
                    continue
                print(tst.display(string=True))

        def run(self):
            if self.args.prompt:
                try:
                    self.query()
                except KeyboardInterrupt:
                    print()
            else:
                self.test()

        def test(self):
            for v in self.values:
                if self.minus:
                    v=self._force_minus(v)
                tst=self.test_cls(v,length=self.length,ar=self.ar,debug=self.debug)
                if __debug__:
                    if self.debug:
                        print("%s %s" % (eloc(self,"test"),tst))

                try:
                    tst.run()
                except TestError as te:
                    print(te)
                    continue
                print(tst.display(string=True))


    # Parse the command-line arguments
    def parse_args():
        parser=argparse.ArgumentParser(prog=this_module,
            epilog=copyright, 
            description="Test decimal floating point constants")
        parser.add_argument("value",nargs="*",\
            help="one or more optional strings to be converted to its interchange "\
                "format. If omitted prompt mode is entered.")
        parser.add_argument("-t",default="d",choices=["d",],\
            help="type of floating point: 'd' for decimal floating point. "\
                "Defaults to d.")
        parser.add_argument("-l","--length",default=8,type=int,choices=[4,8,16],\
            help="interchange format default output length. Defaults to 8.")
        parser.add_argument("-m","--minus",default=False,action="store_true",\
            help="convert command-line value(s) to negative")
        parser.add_argument("-q","--quiet",default=False,action="store_true",\
            help="disable copyright notice")
        parser.add_argument("--noar",default=True,action="store_false",\
            help="disable abstract representation with string conversions")
        parser.add_argument("--prompt",default=False,action="store_true",\
            help="enable input prompt mode")
        parser.add_argument("--debug",default=False,action="store_true",\
            help="enable debugging of value conversions")
        return parser.parse_args()

    # Perform conversion tests
    args=parse_args()
    if not args.quiet:
        print(copyright)

    # Perform the test
    TestRun(args).run()
