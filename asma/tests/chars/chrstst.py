#!/usr/bin/python3
# Copyright (C) 2021 Harold Grovesteen
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

# This module produces the ASMA input source file for testing ASMA character
# handling.

# Note: when changing the copyright notice also change it in gpl3_license and
# recreate the assembler source so it reflects the new notice.

this_module="chrstst.py"

import argparse       # Access command-line parser module
import sys            # Access exit() function.

# ASMA source file licensing information:
gpl3_license=[\
"* Copyright (C) 2021 Harold Grovesteen\n",
"*\n",
"* This file is part of SATK.\n",
"*\n",
"*     SATK is free software: you can redistribute it and/or modify\n",
"*     it under the terms of the GNU General Public License as published by\n",
"*     the Free Software Foundation, either version 3 of the License, or\n",
"*     (at your option) any later version.\n",
"*\n",
"*     SATK is distributed in the hope that it will be useful,\n",
"*     but WITHOUT ANY WARRANTY; without even the implied warranty of\n",
"*     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n",
"*     GNU General Public License for more details.\n",
"*\n",
"*     You should have received a copy of the GNU General Public License\n",
"*     along with SATK.  If not, see <http://www.gnu.org/licenses/>.\n"]


class TSTCHR:
    def __init__(self,args):
        self.args=args
        self.debug=args.debug     # Whether to produce debug messages

        self.srcfile=args.src     # ASMA source created from self.txtfile
        self.txtfile=args.work    # Work file forcing UTF-8 conversion on reads
        self.txtdata=None   # Initialized by read_text() method

        self.utflen=128
        # binary codes 0x80-0xFF cause Pythonn UnicodeDecodeError exceptions
        # Python does not read these codes as text.

        self.chrs=[None,]*self.utflen
        for n in range(len(self.chrs)):
            self.chrs[n]=[]   # initialize each character with empty list
        # Data placed in self.chrs by create_text() method.

        if self.txtfile:
            self.create_text(self.txtfile) # Create binary output
            self.read_text(self.txtfile)  # Read as text (uses UTF-8 conversion)

        if self.srcfile:
            self.create_source(self.srcfile)

    def create_source(self,ofil):
        print("creating ASMA source: %s" % ofil)

        lines=gpl3_license    # Source starts with GPL3 license"
        label=" "*8
        csect_name="ACSECT".ljust(8)
        dc="DC".ljust(5)
        lines.append("%s SPACE 1\n" % label)
        lines.append("%s START 0,TEST\n" % csect_name)

        for n,achr in enumerate(self.chrs):
            the_chr=achr[0]
            if the_chr == "'":
                # Special handling for ASMA single quote requirement
                lines.append("%s %s C''''  %02X\n" % (label,dc,n))
            else:
                # All other characters
                lines.append("%s %s C'%s'   %02X\n" % (label,dc,the_chr,n))
            if n == 0x0a:
                # Add hexadecimal handling for ASMA assembly of line feed
                # character
                lines.append("%s %s X'0A'  %02X\n" % (label,dc,n))
            elif n == 0x0d:
                # Add hexdecimal handling for ASMA assembly of carriage return
                # character
                lines.append("%s %s X'0D'  %02X\n" % (label,dc,n))
                
        # Add tests of tabs outside of character nominal values
        lines.append("%s BALR  2,0\t<--- tab is here\n" % label)
        lines.append("%s BALR  2,0 \t<--- tab is here\n" % label)

        lines.append("%s END\n" % label)

        if self.debug:
            for n,line in enumerate(lines,start=1):
                print("%03d%s" % (n,line),end="")

        fo=open(ofil,"wt")
        for line in lines:
            fo.write(line)
        fo.close()

    def create_text(self,tfil):
        print("creating input Python text: %s" % tfil)
        bindata=bytearray(self.utflen)
        for n in range(self.utflen):
            bindata[n]=n
        bytedata=bytes(bindata)
        fo=open(tfil,mode="wb")
        fo.write(bytedata)
        fo.close()

    def read_text(self,tfil):
        fo=open(tfil,mode="rt")
        self.utfdata=fo.readlines()
        fo.close()

        # self.utfdata contains a list of text lines.  Each line ends with
        # the Python detected end-of-line sequence.
        chrs="".join(self.utfdata)
        # Individual text lines are now a single sequence of bytes, essentially
        # the same data as read but having passed through UTF8 character
        # handling.

        print("read %s bytes of text data: %s" % (self.utflen,len(chrs)))
        for c in chrs:
            n=ord(c)
            lst=self.chrs[ord(c)]
            lst.append(c)
            self.chrs[n]=lst

        # Fix up table due to UTF8 character handling by Python
        self.chrs[0x0d]=[self.chrs[0x0a][1],]  # Carriage Return - CR
        self.chrs[0x0a]=[self.chrs[0x0a][0],]  # Line Feed - LF
        # Both LF and CR are converted into the Python End-of-Line character:\n

        if self.debug:
            for n in range(len(self.chrs)):
                print("%02X - %s" % (n,self.chrs[n]))


def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,\
        description="test ASMA character handling")

    parser.add_argument("-d","--debug",default=False,action="store_true",\
        help="Generate debug messages")
    
    parser.add_argument("-s","--src",metavar="FILEPATH",default=None,\
        required=True,\
        help="File path of the created ASMA test source")

    parser.add_argument("-w","--work",metavar="FILEPATH",default=None,\
        required=True,\
        help="File path of the 128 byte Python work 'txt' file")

    return parser.parse_args()


# Main line processing for ASMLINK
if __name__ == "__main__":
    args=parse_args()
    TSTCHR(args)