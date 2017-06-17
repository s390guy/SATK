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

# This module supports use of the externally installed gmpy2 package for creation
# binary floating point interchange format data.  For a description of the
# interchange formats see bfp.py.

this_module="bfp_gmpy2.py"

# Python imporrts:
import sys       # Access the system's byte order
# SATK imports:
import fp        # Access the generic floating point objects
import bfp       # Access the shared binary floating point objects

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


# This class uses the external package gmpy2 (MPFR wrapper).
class BFP(fp.FP):
    Special=bfp.BFP_Special()     # Special object for BFP special values
    rounding={}                   # Maps numeric rounding mode to gmpy2 mode
    
    format={4:bfp.BFP_Formatter(4),
            8:bfp.BFP_Formatter(8),
            16:bfp.BFP_Formatter(16)}

    def __init__(self,string,length=8,rmode=None,debug=False):
        self.formatter=BFP.format[length]
        self.attr=self.formatter.attr
        super().__init__(string,length=length,rmode=rmode,debug=debug)

  #
  # These methods are required by super class.
  #

    # Create the Python object for the floating point literal string.  What is
    # returned from this method is set to the self.fpo attribute, that is, a
    # MPFR_Data object.
    def create(self):
        data=bfp.MPFR_Data(self.fpstr,format=self.length*8,round=self.rmodeo)
        if __debug__:
            if self.debug:
                print("%s %s" % (fp.eloc(self,"create",module=this_module),\
                    data.display(string=True)))

        return data

    # Return the default numeric and gmpy2 rounding modes as a tuple
    #   tuple[0]   the default numeric rounding mode number
    #   tuple[1]   the gmpy2 default rounding mode
    def default(self):
        #return (fp.BFP_HALF_EVEN,gmpy2.RoundToNearest)
        return (fp.BFP_HALF_EVEN,bfp.MPFR_Data.default)

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
        try:
            return MPFR_Data.rounding[num]
        except KeyError:
            pass

        # invalid or unsupported rounding mode.  
        # So return the default mode, round to nearest or BFP_HALF_EVEN
        return MPFR_Data.default
        #fpnum,gmpy2_num=self.default()
        #return  gmpy2_num

    def to_number(self,fpo):
        return bfp.BFP_Number(fpo.isign,integer=fpo.integer,fraction=fpo.ibits,\
            exp=fpo.iexp,rounding=self.rmodeo,format=self.formatter,debug=self.debug)


#if bfp.gmpy2_available:
    # Don't do this if the gmpy2 module is not available
#    MPFR_Data.init()


if __name__ == "__main__":
    #raise NotImplementedError("%s - intended for import use only" % this_module)

    if not bfp.gmpy2_available:
        raise NotImplementedError("%s - module gmpy2 not available" % this_module)

    #MPFR_Data("25",ic="41C80000",format=32,round=gmpy2.RoundDown).display(modes=True)
    #MPFR_Data("25",ic="4039000000000000",format=64).display()
    #MPFR_Data("25",ic="40039000000000000000000000000000",format=128).display() 
    #MPFR_Data("-25").display()
    #MPFR_Data("2222222222222222222222222222222225",format=32).display()
    #MPFR_Data("2222222222222222222222222222222225",format=64).display()
    #MPFR_Data("2222222222222222222222222222222225",\
    #    ic="406DB6418D0C06E3BF9A45AE38E38E44",format=128).display()

    #MPFR_Data("inf",format=32).display(modes=True)
    #MPFR_Data("2",format=32).display()
    #MPFR_Data("4",format=64).display()
    #MPFR_Data("8",format=128).display()
    #b=BFP("2r5",length=4,debug=True).to_bytes()
    #print(b)
    c=BFP("2r5",length=8,debug=True).to_bytes()
    print(c)
    #d=BFP("2r5",length=16,debug=True).to_bytes()
    #print(c)
    
