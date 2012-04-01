#!/usr/bin/python
# Copyright (C) 2012 Harold Grovesteen
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

class elfbin(object):
    s390=22
    s370=9
    def __init__(self,flnm):
        self.flnm=flnm
        if not os.path.exists(self.flnm):
            print "File does not exist: %s" % self.flnm
            sys.exit(1)
        if not os.access(self.flnm,os.R_OK):
            print "Permissions do not allow reading: %s" % self.flnm
            sys.exit(2)
        if not os.access(self.flnm,os.W_OK):
            print "Permissions do not allow writing: %s" % self.flnm
            sys.exit(2)
        self.e=open(self.flnm,"r+b")
        fd=self.e.fileno()
        size=os.fstat(fd)[7]
        if size<16:
            print "Incomplete ELF header: %s" % self.flnm
            self.close()
            sys.exit(2)
        self.header=self.e.read(16)
        self.elftyp=self.e.read(2)
        self.elfmach=self.e.read(2)
        magic=self.header[0:4]
        if magic!="\x7FELF":
            print "Invalid ELF magic: %02X%02X%02X%02X" % \
	            (ord(magic[0]),ord(magic[1]),ord(magic[2]),ord(magic[3]))
            self.close()
            sys.exit(2)
        if self.header[4]!="\x01":
            print "Not a 32-bit ELF: %s" % self.flnm
            self.close()
            sys.exit(2)
        if self.header[5]!="\x02":
            print "Not MSB (Big-endian) encoding: %s" % self.flnm
            self.close()
            sys.exit(2)
        if self.elftyp!="\x00\x02":
            print "Not an ELF executable: %s" % self.flnm
            self.close()
            sys.exit(2)
        if self.elfmach!="\x00\x16":
            print "Not a s390 ELF (0016): found %02X%02X in %s" % \
	            (ord(self.elfmach[0]),ord(self.elfmach[1]),self.flnm)
            self.close()
            sys.exit(2)
    def close(self):
        self.e.close()
    def setmach(self,mach):
        self.e.seek(18)
        self.e.write(mach)

def usage():
    print "Usage: elfs370.py executable [print]"
      
if __name__ == "__main__":
    if len(sys.argv)<2 or len(sys.argv)>3:
        usage()
        sys.exit(1)
    filename=sys.argv[1]
    e=elfbin(filename)
    e.setmach("\x00\x09")
    print "elfs370.py: Changed ELF executable from s390 to s370: %s" % sys.argv[1]
    e.close()
    if len(sys.argv)==3 and sys.argv[2]=="print":
        elf=PyELF.elf(filename)
        elf.prt()
    sys.exit(0)
