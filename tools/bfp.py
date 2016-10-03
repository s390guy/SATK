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

# Python imports: None
# SATK imports:
import fp        # Access the generic floating point support

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
# with the BFPRound class.
# Instance Arguments:
#   length   required bytes sequence length
#   sign     a tuple of a sign mask and a sign right shift for extraction
#   exp      a tuple of a exponent mask and a exponent right shift for extraction
#   frac     a mask for fraction isolation
#   bias     the exponent bias
#   spec     unsigned bias exponent indicating a special value
class BFPDecode(object):
    #    len           len base  prec    min    max  bias sci fp.Special
    attr={4: fp.FPAttr(4,    2,    24,   -127,  127,  127,True,BFP_Special),\
          8: fp.FPAttr(8,    2,    53,  -1623, 1623, 1023,True,BFP_Special),\
          16:fp.FPAttr(16,   2,   113, -16383,16383,16383,True,BFP_Special)}

    def __init__(self,length,sign,exp,frac,bias,spec):
        self.attr=BFPDecode.attr[length]     # fp.FPAttr object of the format
        self.length=length                   # Legnth of the format
        self.sign_msk,self.sign_shift=sign   # Sign mask and shift values
        self.exp_msk,self.exp_shift=exp      # Exponent mask and shift values
        self.frac_mask=frac                  # fraction mask
        self.bias=bias                       # Unsigned exponent bias
        self.spec=spec    # The unsigned exponent of a special value
        
    def __str__(self):
        return "BFPDecode: bias: %s" % self.bias
        
    # Decodes a bytes sequence as a number
    # Method Arguments:
    #   byts       the bytes sequence being decoded
    #   prec       The precision of the fraction.  Defaults to the precision of the
    #              interchange format implied by the length of byts
    #   byteorder  The byte order of the bytes sequence.  Specify 'big' for most-
    #              significant byte to least significant byte.  Specify 'little' for
    #              least-significant byte to most significant byte.  Defaults to 
    #              'big'.
    # Returns a tuple:
    #   tuple[0]  the sign
    #   tuple[1]  the fraction digit list
    #   tuple[2]  the signed exponent
    #   tuple[3]  the FPAttr object associated with this value
    # Exception:
    #   FPError if the supplied bytes sequence is a special value
    def decode(self,byts,prec=None,byteorder="big"):
        # Convert bytes to an integer
        fmt=int.from_bytes(byts,byteorder=byteorder,signed=False)

        # Extract the sign
        sign_bit = ( fmt & self.sign_msk ) >> self.sign_shift
        sign=sign_bit >> self.sign_shift

        # Extract the biased exponent and convert it to a signed exponent
        exp_bits = fmt & self.exp_msk
        exp=exp_bits >> self.exp_shift
        if exp == self.spec:
            raise fp.FPError(msg="%s BFP special can not be decoded as a number: %s" \
                % (fp.eloc(self,"decode",module=this_module),fp.FP.bytes2str(byts)))
        exp = exp - self.bias

        # Extract the fraction
        frac_bits = fmt & self.frac_mask
        if prec is None:
            precision=self.attr.prec
        else:
            precision=prec
        base=self.attr.base
        
        if __debug__:
            # Perform sanity check to validate extraction was correct
            restored=sign_bit | exp_bits | frac_bits
            restored_byts=restored.to_bytes(len(byts),byteorder="big",signed=False)
            assert restored == fmt,\
               "%s extracted fields do not match original fields:\n"\
                   "    original: %s\m    extracted: %s" \
                       % (fp.eloc(self,"decode",module=this_module),\
                           fp.bytes2str(byts),fp.bytes2str(restored_byts))

        digits=[]
        fracwk=frac_bits
        for n in range(precision):
            fracwk,digit=divmod(fracwk,base)
            digits.append(digit)
        assert len(digits)==precision,\
            "%s precision (%s) does not match number of digits produced: %s" \
                % (fp.eloc(self,"decode",module=this_module),precision,len(digits))

        digits.reverse()

        return (sign,digits,exp,self.attr)
        
    # Encode into bytes
    # Method Arguments:
    #   sign   the sign: 0 -> positive, 1-> negative
    #   exp    the signed exponent as an integer
    def encode(self,sign,exp,frac,byteorder="big"):
        sign_bit= sign << self.sign_shift


class BFPRound(object):
    decode={4:BFPDecode(4,(1<<31,31),(0b011111111<<23,23),0x007FFFFF,127,255),\
            8:BFPDecode(8,(1<<63,63),(0x7FF<<52,52),0xFFFFFFFFFFFFF,1023,2047),\
           16:BFPDecode(16,(1<<127,127),(0x7FFF<<112,112),\
                        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,16383,32767)}

    def __init__(self,byts):
        assert isinstance(byts,bytes),\
            "%s 'byts' argument must be bytes: %s" \
                % (fp.eloc(self,"__init__",module=this_module),byts)
        
        self.length=len(byts)
        try:
            dcdr=BFPRound.decode[self.length]
        except KeyError:
            raise ValueError("%s 'byts' argument must be of length 4, 8, or 16: %s"\
                % (fp.eloc(self,"__init__",module=this_module),self.length))
        sign,frac,exp,attr=dcdr.decode(attr,byts)
        super(),__init__(sign,frac,exp,attrs=attr)


class BFP_Special_old(fp.FP_Special):
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


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)