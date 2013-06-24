#!/usr/bin/python3.3
# Copyright (C) 2012,2013 Harold Grovesteen
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

# This module is intended to be imported for use by other modules
import os
import os.path
import PyELF
import sys

copyright_years="2012,2013"

class elfbin(object):
    s390=22
    s370=9
    def __init__(self,flnm):
        self.flnm=flnm
        if not os.path.exists(self.flnm):
            print("File does not exist: %s" % self.flnm)
            sys.exit(1)
        if not os.access(self.flnm,os.R_OK):
            print("Permissions do not allow reading: %s" % self.flnm)
            sys.exit(2)
        if not os.access(self.flnm,os.W_OK):
            print("Permissions do not allow writing: %s" % self.flnm)
            sys.exit(2)
        self.e=open(self.flnm,"r+b")
        fd=self.e.fileno()
        size=os.fstat(fd)[7]
        if size<16:
            print("Incomplete ELF header: %s" % self.flnm)
            self.close()
            sys.exit(2)
        self.header=self.e.read(16)
        self.elftyp=self.e.read(2)
        self.elfmach=self.e.read(2)
        magic=self.header[0:4]
        if magic!=b"\x7FELF":
            print("Invalid ELF magic: %02X%02X%02X%02X" % \
	            (ord(magic[0]),ord(magic[1]),ord(magic[2]),ord(magic[3])))
            self.close()
            sys.exit(2)
        #if self.header[4]!=b"\x01":
        if self.header[4]!=1:
            print("Not a 32-bit ELF: %s" % self.flnm)
            self.close()
            sys.exit(2)
        #if self.header[5]!=b"\x02":   
        if self.header[5]!=2:
            print("Not MSB (Big-endian) encoding: %s" % self.flnm)
            self.close()
            sys.exit(2)
        if self.elftyp!=b"\x00\x02":
            print("Not an ELF executable: %s" % self.flnm)
            self.close()
            sys.exit(2)
        if self.elfmach!=b"\x00\x16":
            print("Not a s390 ELF (0016): found %02X%02X in %s" % \
	            (ord(self.elfmach[0]),ord(self.elfmach[1]),self.flnm))
            self.close()
            sys.exit(2)
    def close(self):
        self.e.close()
    def setmach(self,mach):
        self.e.seek(18)
        self.e.write(mach)

class elfs370(object):
    def __init__(self,args):
        self.p=args.print
        self.filename=args.exefile
    def convert(self):
        e=elfbin(self.filename)
        e.setmach(b"\x00\x09")
        print("elfs370.py: Changed ELF executable from s390 to s370: %s" \
            % self.filename)
        e.close()
        if self.p:
            elf=PyELF.elf(self.filename)
            elf.prt()
        sys.exit(0)
    
def parser_args():
    parser=argparse.ArgumentParser(prog="inventory.py",
        epilog="inventory.py Copyright (C) %s Harold Grovesteen" % copyright_years, 
        description="converts a s390 ELF executable into a s370 ELF executable")
    parser.add_argument("exefile",\
        help="input ELF executable file path",nargs=1)
    parser.add_argument("-p","--print",action="store_true",default=False,\
        help="enables printing of the input filename")

    return parser.parse_args()  
      
if __name__ == "__main__":
    e=elfs370(parser_args())
    e.convert()
    
    #if len(sys.argv)<2 or len(sys.argv)>3:
    #    usage()
    #    sys.exit(1)
    #filename=sys.argv[1]
    #e=elfbin(filename)
    #e.setmach(b"\x00\x09")
    #print("elfs370.py: Changed ELF executable from s390 to s370: %s" % sys.argv[1])
    #e.close()
    #if len(sys.argv)==3 and sys.argv[2]=="print":
    #    elf=PyELF.elf(filename)
    #    elf.prt()
    #sys.exit(0)
