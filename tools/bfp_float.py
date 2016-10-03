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

# This module supports binary floating point objects based upon Python supplied
# float objects.  For a description of the BFP interchange formats see bfp.py.
#
# Instances of float do not have a direct path to binary representation.  All float
# objects use the 64-bit format.  The 32-bit format is derivable from the 64-bit
# provided rounding is supported.
#
# They do not support a mechanism for creation of bytes.  But, the do have a hex()
# method that creates a string that represents the float value exactly.  These can
# be turned into binary bytes from the 'hex' string.  The string corresponds to 
# a C or Java literal with the following format:
#
# [sign] ['0x'] integer ['.' fraction] ['p' exponent]
#
# To illustrate, a 64-bit floating point value in interchange format of decimal 25 is,
# in hex:
#
#    4039000000000000
#
# The first 12 bits, the sign and exponent are: 0100 0000 0011, making the sign 0
# and the biased exponent 1027, or signed exponent of 4 (base 2).  The fraction is
# in base 2: 1001.  The first base 2 digit is always an implied 1.  So the binary 
# value is: 1.1001 * 2**4 (or base 2 11001 and base 10 25).
#
# The hex literal string for this value is: '0x1.9000000000000p+4'
# The fraction corresponds directly with the interchange format and the exponent
# is identical to the signed exponent of the interchange format.   The sign is 
# 0 for the implied +.  The hex literalt string can then be used directly to
# create the sequence of bytes corresponding to this value.


this_module="bfp.py"

# Python imports:
import re       # Access regular expressions
import sys      # Access to the system's native byteorder
# SATK imports:
# WARNING: Do not change the sequence
import fp       # Access the generic Floating Point objects
import bfp      # Access the shared binary floating point objects
import retest   # Access the regular expression test harness


#
# +-----------------------------------+
# |                                   |
# |    Python float Object Support    |
# |                                   |
# +-----------------------------------+
#

# This class processes the hexadecimal literal string produced by a float
# object's hex() method.
class BFP_Number(fp.FP_Number):
    parser=re.compile("(?P<sign>[+-])?(0x)(?P<integer>[0-9a-f]+)"\
        "(?P<fraction>\.[0-9a-f]*)?(?P<exp>p[+-]?[0-9]+)")
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

    bias=1023   # Bias applied to exponent

    # Converts a string of hexadcimal digits to a binary digits list
    @staticmethod
    def hex2bin(string):
        chars=BFP_Number.hex_chars
        lst=[]
        for c in string:
            lst.extend(chars[c])
        return lst

    def __init__(self,src):
        self.hx=None      # Hex literal from float conversion
        self.mo=None      # Regular expression match object from hex literal
        self.integer=None # Integer from parsed Hex literal

        if isinstance(src,float):
            s,e,f=self.float2number(src)
        elif isinstance(src,tuple) and len(src)==3:
            s,e,f=src
        else:
            raise ValueError(\
                "%s 'src' must be either a float or tuple of length 3: %s" \
                    % (fp.eloc(self,"__init__",module=this_module),src))

        super().__init__(s,e,f,2)

    def __str__(self):
        return "sign:%s integer:%s frac:%s exp:%s" \
            % (self.sign,self.integer,self.frac,self.exp)

    def float2number(self,fpo):
        self.hx=hx=fpo.hex()
        self.mo=mo=BFP_Number.parser.match(hx)
        if mo is None:
            raise ValueError("unrecognized hex literal: '%s'" % string)
        mod=mo.groupdict()

        fp_sign=BFP_Number.signs[mod["sign"]]
        self.integer=mod["integer"]

        frac=mod["fraction"]
        frac=frac[1:]      # Drop off the leading period of the fraction
        fp_frac=BFP_Number.hex2bin(frac)

        exp=mod["exp"]
        if exp is None:
            fp_exp=0
        else:
            fp_exp=int(exp[1:],10)

        if self.integer not in ["1","0"]:
            raise ValueError("unexpected integer in hex literal: '%s'" \
                % self.integer)

        return (fp_sign,fp_exp,fp_frac)

    def to_bytes(self,length=None,byteorder="big"):
        fmt = self.sign << 63
        fmt = fmt | ( ( self.exp+BFP_Number.bias ) & 0x7FF ) << 52
        fmt = fmt | self.frac2int(drop=False) & 0xFFFFFFFFFFFFFF
        return fmt.to_bytes(8,byteorder=byteorder,signed=False)


# This class uses the Python float object to create a BFP value in its interchange
# format.  Presently only the 64-bit format is supported.
class BFP(fp.FP):
    Special=bfp.BFP_Special()      # Special object for BFP special values

    def __init__(self,string,length=8,rmode=None,debug=False):
        super().__init__(string,length=length,rmode=rmode,debug=debug)

  # These methods required by super class.

    def default(self):
        return (fp.BFP_DEFAULT,None)

    def create(self):
        return float(self.fpstr)

    def i_fmt(self,byteorder="big"):
        return self.number.to_bytes(self.length,byteorder=byteorder)

    def to_number(self,fpo):
        num=BFP_Number(fpo)
        if __debug__:
            if self.debug:
                print("%s BFP_Number - %s" \
                    % (fp.eloc(self,"number",module=this_module),lit))
        return num

    def rounding(self,num):
        return None


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
