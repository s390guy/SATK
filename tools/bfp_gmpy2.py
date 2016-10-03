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


#
# +---------------------------------+
# |                                 |
# |    gmpy2 mpfr Object Support    |
# |                                 |
# +---------------------------------+
#

# This class provides detailed information about the content of a gmpy2.mpfr object
# Its attributes are made availalbe and the objects to_binary() content is
# exposed.  This object participates in creation of the actual interchange format.
#
# The sequence of bytes supplied by the to_binary() method is internal to the gmpy2
# package and can change from one release to the next.
class MPFR_Data(object):
    def __init__(self,src,ic=None,format=32,round=0):
        self.ic=ic         # Interchange format hex data string
        self.fpo=None      # gnoy2.mpfr object
        self.format=format # interchange format being created

        # These values are supplied by the gmpy2.mpfr.digits() method
        self.digits=None   # the binary digits of the signigicand
        self.dexp=None     # the signed exponent
        self.dprec=None    # the precision of the object

        # These attributes are produced below and are destined for the interchange
        # format
        self.isign=None    # The value's sign
        self.ibits=None    # The actual bits destined for the significand
        self.iexp=None     # The signed exponent destined for the int

        if isinstance(src,gmpy2.mpfr):
            self.fpo=src
        elif isinstance(src,str):
            ctx=gmpy2.ieee(format)
            ctx.round=gmpy2.round=round
            gmpy2.set_context(ctx)
            self.fpo=gmpy2.mpfr(src)
        else:
            raise ValueError("%s 'byts' argument unrecognized: %s" \
                % (fp.eloc(self,"__init__",module=this_module),byts))

        self.digits,self.dexp,self.dprec=self.fpo.digits(2)

        if self.digits[0] == "-":
            self.isign=1
            self.ibits=self.digits[2:]   # Remove the sign and implied first 1
        else:
            self.isign=0
            self.ibits=self.digits[1:]   # Remove the implied first 1
           
        # The exponent assumes the leading one is part of the significand, so the
        # exponent is one larger than is required for the interchange format.
        self.iexp=self.dexp-1


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
        #man,exp,mpfr_prec=self.fpo.digits(2)
        s="%s\n%smpfr prec:%s 0x%X" % (s,lcl,self.dprec,self.dprec)
        s="%s\n%smpfr sign: %s" % (s,lcl,self.isign)

        if not self.ic:
            s="%s\n%smpfr man: %s (%s digits)" % (s,lcl,self.digits,len(self.digits))
            #    % (s,lcl,digits[0],len(digits[0]))
            s="%s\n%smpfr exp:  %s 0x%X" % (s,lcl,self.dexp,self.dexp)
        else:
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

        ctx=gmpy2.get_context()
        s="%s\n%s%s" % (s,lcl,ctx)
        s="%s\n" % s
        if string:
            return s
        print(s)


# This class uses the external package gmpy2 (MPFR wrapper).
class BFP(fp.FP):
    Special=bfp.BFP_Special()     # Special object for BFP special values
    rounding={}                   # Maps numeric rounding mode to gmpy2 mode

    # This has to be in a method because otherwise when gmpy2 is not available
    # the class will not be defined.
    @staticmethod                                           # Num   GMPY2
    def init():                                             # Mode  Mode
        BFP.rounding={fp.BFP_HALF_UP:gmpy2.RoundAwayZero,     # 1     4
                      fp.BFP_HALF_EVEN:gmpy2.RoundToNearest,  # 4     0
                      fp.BFP_DOWN:gmpy2.RoundToZero,          # 5     1
                      fp.BFP_CEILING:gmpy2.RoundUp,           # 6     2
                      fp.BFP_FLOOR:gmpy2.RoundDown}           # 7     3

    def __init__(self,string,length=8,rmode=None,debug=False):
        super().__init__(string,length=length,rmode=rmode,debug=debug)

  # These methods are required by super class.

    # Create the Python object for the floating point literal string
    def create(self):
        ctx=gmpy2.ieee(self.length*8)  # Emulate IEEE for requested format size
        ctx.round=self.rmodeo          # Set the requested gmpy2 rounding mode
        gmpy2.set_context(ctx)         # Make this the active context.

        # Convert the floating point string to an mpfr object
        return gmpy2.mpfr(self.fpstr)

    # Return the default numeric and gmpy2 rounding modes as a tuple
    #   tuple[0]   the default numeric rounding mode number
    #   tuple[1]   the gmpy2 default rounding mode
    def default(self):
        return (fp.BFP_HALF_EVEN,gmpy2.RoundToNearest)

    # Return the gmpy2 rounding mode corresponding to the numeric rounding mode
    def rounding(self,num):
        try:
            return BFP.rounding[num]
        except KeyError:
            pass

        # invalid or unsupported rounding mode.  
        # So return the default mode, round to nearest or BFP_HALF_EVEN
        fpnum,gmpy2_num=self.default()
        return  gmpy2_num

    def to_bytes(self,byteorder="big"):
        
        self.digits()
        
        print(format(self.fpo,"A"))
        ctx=gmpy2.ieee(self.length*8)
        gmpy2.set_context(ctx)
        b=gmpy2.to_binary(self.fpo)
        return b
        
    def to_number(self,fpo):
        data=MPFR_Data(fpo)
        raise NotImplementedError("%s method implementation is incomplete"\
            % fp.eloc(self,"to_number",module=this_module))


if gmpy2_available:
    # Don't do this if the gmpy2 module is not available
    BFP.init()


if __name__ == "__main__":
    #raise NotImplementedError("%s - intended for import use only" % this_module)

    if not gmpy2_available:
        raise NotImplementedError("%s - module gmpy2 not available" % this_module)

    #MPFR_Data("25",ic="41C80000",format=32,round=gmpy2.RoundDown).display(modes=True)
    #MPFR_Data("25",ic="4039000000000000",format=64).display()
    #MPFR_Data("25",ic="40039000000000000000000000000000",format=128).display() 
    #MPFR_Data("-25").display()
    #MPFR_Data("2222222222222222222222222222222225",format=32).display()
    #MPFR_Data("2222222222222222222222222222222225",format=64).display()
    #MPFR_Data("2222222222222222222222222222222225",\
    #    ic="406DB6418D0C06E3BF9A45AE38E38E44",format=128).display()

    MPFR_Data("inf",format=32).display(modes=True)
    MPFR_Data("0",format=32).display()
