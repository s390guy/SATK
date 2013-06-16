#!/usr/bin/python3.3
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

# This module is a wrapper for PyELF tailored to the IPL ELF ABI Supplement.

import PyELF                # access the Python ELF handler
import hexdump              # access to the binary manipulation functions

class PyIPLELF(object):
    def __init__(self,elf,debug=False):
        if not isinstance(elf,PyELF.elf):
            raise TypeError("PyIPLELF.py: error: not a PyELF.elf instance: %s" % elf)
        self.filename=elf.name            # IPL ELF file name
        self.elfo=elf                     # IPL ELF as a PyELF.elf instance
        self.elf=self.elfo.fil            # IPL ELF as a single string
        if debug:
            print("PyIPLELF.py: debug: length of elf file: %s" % len(self.elf))
        self.elf_entry=self.elfo.getEntry()   # Entry address of IPL ELF

        self.segments={}       # Contains the IPL ELF recognized segments by name
        self.elf_itself=None   # Set by elfseg method, if called below
        
        self.ipl_entry=None    # Set by loadelf method if IPL segment is present
        
        # The rmode is used to define the architecture in which the IPL ELF
        # expects to run.  This is determined from the IPL ELF Header data
        self.rmode=self.arch() # Set residency mode (or arch) the same as amode
        
        # amode may be set from the IPL PSW if the IPL ELF contains an IPL segment.
        # Otherwise it will default to the hightest addressing mode available to
        # the architecture implied by the IPL ELF Header data.
        self.amode=None        # Set amode based upon IPL ELF
        self.rmode=self.arch() # Set residency mode (or arch) the same as amode
        # Note, if an IPL PSW is present, the IPL PSW address overrides the ELF
        # entry address.
        
        # Construct the self.segments dictionary from the IPL ELF
        for seg in self.elfo.PgmTbl.entries:
            try:
                segname=IPLSegment.name(seg)
            except KeyError:
                continue
            sego=IPLSegment(segname,seg)
            self.segments[sego.name]=sego
        try:
            text=self.segments["TEXT"]
        except KeyError:
            pass

        if self.loadelf():
            # Try to create a segment wrapper for the ELF itself
            self.elfseg()
            
        # If no IPL Segment, set the addressing mode to match the residency arch.
        if self.amode is None:
            self.amode=self.rmode

    def __str__(self):
        keys=self.segments.keys()
        keys.sort()
        segs=""
        for x in keys:
            segs="%s, %s" % (segs,self.segments[x].name)
        return "Segments: %s" % segs[2:]

    def arch(self):
        if self.elfo.iss370():
            return 24
        if self.elfo.is64():
            return 64
        return 31

    def elfseg(self):
        # This method returns the ELF as a segment in its own right
        # This treatment allows the ELF to be handled the same as in individual
        # segment
        if len(self.segments)==0:
            raise ValueError("PyIPLELF.py: error: could not locate information for "\
                "IPL ELF segment creation")
        # A segment is needed to calculate where the ELF itself should be loaded
        keys=self.segments.keys()
        seg=self.segments[keys[0]]
        self.elf_itself=ELFSegment(self.elf,address=seg.address-seg.elf_offset)

    def entry(self):
        # Return the entry address.  It defaults to the ELF executable entry
        # address.  If an IPL segment is present the address provided by the PSW
        # is used.
        if self.ipl_entry is None:
            return self.elf_entry
        return self.ipl_entry

    def get_elf(self):
        # Returns the ELF Segment
        if self.elf_itself is not None:
            return self.elf_itself
        raise ValueError("PyIPLELF.py: error: ELFSegment not available")

    def loadelf(self):
        # True is returned if entire ELF is required by the program or
        # False is returned if program uses just the TEXT segment
        # How to load the ELF is defined by the IPL segment flags.  If there is
        # no IPL segment, then it is assumed the entire ELF is required.
        try:
            iplseg=self.segments["IPL"]
        except KeyError:
            # No IPL segment, so assume the whole ELF is required
            return True
        self.ipl_entry=iplseg.iplentry
        self.amode=iplseg.amode
        return False

    def sego(self,name):
        # Returns by name a segment's PyELF.Program instance. A segment name that is
        # not present raises a KeyError.
        return self.segments[name]
            
class IPLSegment(object):
    areas={0x01000000:"TXT0",
           0x02000000:"TXT1",
           0x03000000:"TXT2",
           0x04000000:"ELF1",
           0x05000000:"ELF2"}
    names={0x00000005:".data",
           0x00000006:".text",
           0x00000007:"TEXT",
           0x10000004:"IPL",
           0x20000004:"CCW",
           0x30000006:"LOWC",
           0xF0000007:"LOADER"}
           
    @staticmethod
    def area(sego):
        if not isinstance(sego,PyELF.Program):
            raise TypeError("PyIPLELF.py: internal: not a PyELF.Program: %s" % sego)
        try:
            return IPLSegment.areas[sego.flags & 0x07000000]
        except KeyError:
            return "any"

    @staticmethod
    def name(sego):
        if not isinstance(sego,PyELF.Program):
            raise TypeError("PyIPLELF.py: internal: not a PyELF.Program: %s" % sego)
        return IPLSegment.names[sego.flags & 0xF0000007]
    
    def __init__(self,name,sego=None):
        if sego is not None and not isinstance(sego,PyELF.Program):
            raise TypeError("PyIPLELF.py: internal: not a PyELF.Program: %s" % sego)
        self.name=name
        self.sego=sego    # Program segment as a PyELF.Program instance

        if self.name=="IPL":
            self.iplseg_decode()
            self.isIPL=True
        else:
            self.isIPL=False
        # Must use self.isIPL flag before attempting to access instance variables
        # created by iplseg_decode: self.iplpsw, self.amode, self.iplentry

    def iplseg_decode(self):
        # Decode the information in the IPL ELF "IPL" segment
        self.iplpsw=self.segment[:8]
        self.loadelf=(self.sego.flags & 0x08000000) == 0x00000000
        if (ord(self.iplpsw[1])&0x08)==0x08:
            # If EC-mode PSW use last 4 bytes for address (valid for S/370 & ESA/390)
            addr=addr31(self.iplpsw[4:8])
            self.iplentry=addr&0x7FFFFFFF
            if (addr&0x80000000)==0x80000000:
                self.amode=31
            else:
                self.amode=24
        else:
            # If BC-mode PSW use last 3 bytes for address
            self.iplentry=addr24(self.iplpsw[5:8])
            self.amode=24

    @property
    def address(self):
        # Retrns the segment's load address
        return self.sego.virt_addr

    @property
    def elf_offset(self):
        return self.sego.offset

    @property
    def segment(self):
        # Returns the segment data as a string
        return self.sego.fetch()
        
    @property
    def size(self):
        # Returns the segment's memory size
        return self.sego.mem_size
    
class ELFSegment(IPLSegment):
    # Representation of the entire IPL ELF as an IPL ELF Segment
    def __init__(self,elftext,address):
        self.addr=address
        self.elftext=elftext
        super(ELFSegment,self).__init__("ELF",sego=None)
        
    @property
    def address(self):
        # Retrns the segment's load address
        return self.addr

    @property
    def elf_offset(self):
        return 0

    @property
    def segment(self):
        # Returns the segment data as a string
        return self.elftext
        
    @property
    def size(self):
        # Returns the segment's memory size
        return len(self.segment)