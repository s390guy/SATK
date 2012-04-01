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

# This module assists in the creation of channel programs

# SATK imports
from   hexdump import *     # Access hex dump utility methods/functions

def align(addr,align):
   return ((addr+align-1)//align)*align
    
# CCW commands:
CKD_RDATA=0x06 # CKD READ DATA command
CKD_SEEK=0x07  # CKD SEEK cylinder and track command
CKD_SIDEQ=0xB1 # CKD SEARCH ID EQUAL command
IPLREAD=0x02   # READ IPL command
TIC=0x08       # TRANSFER IN CHANNEL command
FBA_READ=0x42  # FBA Read Sectors command
FBA_LOC=0x43   # FBA Locate blocks command
READ=0x02      # Unit record read command

# CCW flags:
CD=0x80
CC=0x40
SLI=0x20
SKIP=0x10
    
# FBA Locate Operations
FBAL_WRITE=0x01   # Write data
FBAL_RDREP=0x02   # Read replicated data
FBAL_FORMT=0x04   # Format defective sectors
FBAL_WRTVR=0x05   # Write data and verify
FBAL_READ =0x06   # Read sectors

class chain(object):
    # This is the primary class for the creation of channel program chains
    cur=None
    @staticmethod
    def untarget():
        global this
        this=None
        chain.cur=None
    def __init__(self,loc=0):
        self.items=[]
        self.tags={}
        self.loc=loc
        if chain.cur is None:
            self.target()
    def __getitem__(self,item):
        return self.tags[item]
    def __setitem__(self,item,value):
        self.tags[item]=value
    def add(self,itm):
        self.items.append(itm)
        itm.chanpgm=self
        return self.update(itm.length)
    def binary(self):
        ccws=""
        for x in self.items:
            ccws+=x.binary()
        return ccws
    def next(self):
        # Returns the address of the next CCW
        return self.loc
    def target(self):
        global this
        # makes this chain the target for tag definitions
        #global this
        chain.cur=self
        this=self
    def update(self,length):
        star=self.loc
        self.loc+=length
        return star
    def value(self,tag):
        try:
            sym=self.tags[tag]
            return sym.value
        except KeyError:
            if isinstance(tag,type("")):
                raise KeyError("ccwutil.py: error: tag not defined: '%s'"\
                    % tag)
            return tag

class item(object):
    def __init__(self,length):
        if chain.cur is None:
            raise ValueError("ccwutil.py: error: no chain being targeted")
        self.length=length
        self.loc=this.add(self)
    def __len__(self):
        return self.length
    def __rlshift__(self,other):
        # Used to interpret tag assignment:  "tag" << item
        # tags are referrenced by: this["tag"]
        if chain.cur is None:
            raise ValueError("ccwutil.py: error: no chain being targeted")
        if not isinstance(other,type("")):
            raise TypeError("ccwutil.py: error: tag must be string: %s" % other)
        self.chanpgm[other]=symbol(other,self.loc)
        
class ccw0(item):
    def __init__(self,cmd,address=0,count=1,flags=0):
        self.cmd=cmd
        self.address=address
        self.count=count
        self.flags=flags
        item.__init__(self,8)
    def __str__(self):
        return "ccw0(0x%02X,address=0x%06X,count=%s,flags=0x%02X)" \
            % (self.cmd,self.address,self.count,self.flags)
    def binary(self):
        cmd=self.chanpgm.value(self.cmd)
        addr=self.chanpgm.value(self.address)
        fl=self.chanpgm.value(self.flags)
        cnt=self.chanpgm.value(self.count)
        return byteb(cmd)+addr24b(addr)+byteb(fl)+"\x00"+halfwordb(cnt)
        
        
class ckdid(item):
    def __init__(self,cc=0,hh=0,r=0,seek=False,pad=False):
        if seek:
            if pad:
                item.__init__(self,8)
            else:
                item.__init__(self,7)
        else:
            item.__init__(self,5)
        self.cc=cc
        self.hh=hh
        self.r=r
        self.pad=pad
        self.seek=seek
    def binary(self):
        if self.seek:
            string="\x00\x00"
        string="%s%s" % (string,halfwordb(self.cc))
        string="%s%s" % (string,halfwordb(self.hh))
        string="%s%s" % (string,byteb(self.r))
        if self.pad:
            string="%s%s" % (string,"\x00")
        return string
        
class ckdseek(item):
    def __init__(self,cc=0,hh=0):
        self.cc=cc
        self.hh=hh
        item.__init__(self,6)
    def binary(self):
        return "\x00\x00"+halfwordb(self.cc)+halfwordb(self.cc)

class fbaloc(item):
    def __init__(self,opr,sector=0,sectors=1,repl=0):
        self.opr=opr
        self.sector=sector
        self.sectors=sectors
        self.repl=repl
        item.__init__(self,8)
    def binary(self):
        opr=self.chanpgm.value(self.opr)
        sec=self.chanpgm.value(self.sector)
        secs=self.chanpgm.value(self.sectors)
        repl=self.chanpgm.value(self.repl)
        return byteb(opr)+byteb(repl)+halfwordb(secs)+fullwordb(sec)

class symbol(object):
    def __init__(self,lable,value=None):
        self.lable=lable
        self.value=value

if __name__=="__main__":
    raise NotImplementedError("ccwutil.py: error: must only be imported")