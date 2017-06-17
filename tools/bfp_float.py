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
import sys      # Access to the system's native byteorder
# SATK imports:
# WARNING: Do not change the sequence
import fp       # Access the generic Floating Point objects
import bfp      # Access the shared binary floating point objects


# This class processes the hexadecimal literal string produced by a float
# object's hex() method.
class BFP_Number(fp.FP_Number):

    bias=1023   # Bias applied to exponent

    def __init__(self,src):
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


# This class uses the Python float object to create a BFP value in its interchange
# format.  Presently only the 64-bit format is supported.
class BFP(fp.FP):
    Special=bfp.BFP_Special()      # Special object for BFP special values
    
    format={4:bfp.BFP_Formatter(4),
            8:bfp.BFP_Formatter(8),
            16:bfp.BFP_Formatter(16)}

    def __init__(self,string,length=8,rmode=None,debug=False):
        self.formatter=BFP.format[length]
        self.attr=self.formatter.attr
        super().__init__(string,length=length,rmode=rmode,debug=debug)

  # These methods required by super class.

    def default(self):
        return (fp.BFP_DEFAULT,None)

    #def create(self):
    #    data=bfp.FLOAT_Data(self.fpstr,format=self.length*8)
    #    if __debug__:
    #        if self.debug:
    #            print("%s %s" % (fp.eloc(self,"create",module=this_module),\
    #                data.display(string=True)))

    #    return data

    def i_fmt(self,byteorder="big"):
        return self.number.to_bytes(byteorder=byteorder)

    def to_number(self,fpo):
        return bfp.BFP_Number(fpo.isign,integer=fpo.integer,fraction=fpo.ibits,\
            exp=fpo.iexp,rounding=self.rmodeo,format=self.formatter,debug=self.debug)

    def rounding(self,num):
        return None


if __name__ == "__main__":
    #raise NotImplementedError("%s - intended for import use only" % this_module)

    #b=BFP("2r5",length=4,debug=True).to_bytes()
    #print(b)
    c=BFP("2r5",length=8,debug=True).to_bytes()
    print(c)
    #d=BFP("2r5",length=16,debug=True).to_bytes()
    #print(c)
