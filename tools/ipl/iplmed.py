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

# This module processes an IPL ELF executable and 
# loads it to an IPL storage medium

# SATK imports
from   ccwutil  import *    # Access the ccw utility functions
from   hexdump  import *    # Access hex dump utility methods/functions
from   recsutil import *    # Access record utility classes
import media                # Access the Hercules device emulation support
import PyELF                # ELF utility
import volume               # Access the DASD Standard Volume support classes
# Python imports
import argparse             # command line argument parser
#import functools            # Access compare to key function for sorting
import os.path              # path manipulation tools
import struct               # access binary structures
import sys                  # system values

# Class usage
#   device_class     Generic IPL device medium.  It generates CCW's, if not 
#                    supplied by the IPL ELF.  Writes out the IPL records to the
#                    device targets.
#        CARD, CDROM, CKD, ECKD, FBA, TAPE
#
#   iplelf           The internalized representation of the IPL ELF executable
#                    It maps segments to records providing default content
#                    Identifies the actual output device class being targeted
#
#   IPLMED           The IPL medium processor.  It interacts with the external
#                    environment, processing command line arguments and driving
#                    output generation
#
#   record           The generic IPL record content.  Each subclass generates its
#                    own default content if required.
#        ccw, elf, ipl, loader, lowc, text
#
#   segment          Program segment extracted from an IPL ELF executable

def align(addr,align):
    return ((addr+align-1)//align)*align
    
def dead(code=0):
    # return a S/370 EC-mode or ESA/390 disabled wait PSW
    return psw(sysmsk=0x000A,addr=code)

def deade(code=0):
    # return a z/Architecture disabled wait PSW
    return pswe(sysmsk=0x0002,addr=code)

def psw(sysmsk=0x0008,pgmmsk=0,addr=0,mode=24,debug=False):
    if debug:
        print("psw(sysmsk=0x%04X,pgmmsk=0x%04X,addr=0x%08X,mode=%s)" \
            % (sysmsk,pgmmsk,addr,mode))
    # return a S/370 EC-mode or 24-bit addressing mode ESA/390 64-bit PSW
    if mode==31:
        return halfwordb(sysmsk)+byteb(pgmmsk)+b"\x00"+addr31b(addr,bit0=1)
    return halfwordb(sysmsk)+byteb(pgmmsk)+b"\x00\x00"+addr24b(addr)
    
def pswe(sysmsk=0x0000,pgmmsk=0,addr=0,debug=False):
    if debug:
        print("pswe(sysmsk=0x%04X,pgmmsk=0x%04X,addr=0x%016X)" \
            % (sysmsk,pgmmsk,addr))
    # return a z/Architecture 24-bit addressin mode z/Architecture 128-bit PSW
    return halfwordb(sysmsk)+byteb(pgmmsk)+b"\x00\x00\x00\x00\x00"+dblwordb(addr)
    
def roundup(value,rnd):
    # return the value rounded up to the next rnd increment
    return ((value+rnd-1) // rnd)*rnd

class archs(object):
    # Displayable architecture levels used in self.archs
    archmodes={0:"S/370 BC-mode",1:"S/370 EC-mode",\
               2:"ESA/390",3:"z/Architecture",None:None}
    iomodes={True:"channel",False:"subchannel",None:None}

    # Command line options to internal archs values
    cli2arch={24:1,31:2,64:3,None:None}      # Command line architecture options
    cli2io={"chan":True,"sch":False,None:False}  # Command line I/O options

    # loader and ipl classes these values for arch and I/O:
    archs2mode={0:24,1:24,2:31,3:64}
    io2loader={True:0x04,False:0x02}
    archs2loader={0:0x24,1:0x24,2:0x31,3:0x64}

    # IPL architectures from Program archs
    iplarch={0:0,1:1,2:2,3:2,None:None}
    
    # IPL I/O implied from Program arch
    # True == Channel I/O, False == subsystem I/O
    iplio={0:True,1:True,2:False,3:False,None:None}

    # Displayable sources
    levels={0:"cli    ",1:"LOADER ",2:"IPL ELF",3:"default"}
    
    # Converts source to a level
    sources={"cli":0,"LOADER":1,"IPL ELF":2,"default":3}
                   
    # This class manages the selection of the IPL device's IPL architecture.
    # The IPL architecture is driven by the IPL PSW.  The IPL PSW sets the
    # architecture when entering either the IPL ELF directly or the bootstrap
    # loader.  There are potentially four sources for the architecture 
    # in the following order of priority.
    #
    #   1 the command line arguments --arch and --s370bc
    #   2 the loader interface data of the bootstrap loader
    #   3 the architecture implied by the IPL ELF itself
    #   4 global defaults
    #
    # The individual set_xxx methods internalize the information from each source
    # The get_arch and get_bcmode methods supply the selected architecture.
    def __init__(self,arch=2,bcmode=False,iochan=False,debug=False):
        self.archs=[None,None,None,None]        # Architecture level
        self.iochan=[None,None,None,None]       # S/370 channels: True/False
        # bcmode is only significant when setting self.archs
        self.bcmode=[False,False,False,False]  # S/370 BC-mode: True/False
        #  self.xxxxx [0] - command line arguments
        #  self.xxxxx [1] - loader interface data of the bootstrap loader
        #  self.xxxxx [2] - Implied architecture of the IPL ELF itself
        #  self.xxxxx [3] - Default
        index=len(self.archs)-1
        self.archs[index]=arch
        self.bcmode[index]=bcmode
        self.iochan[index]=iochan
        # Stores loader capabilities
        self.loader_archs=[False,False,False,False]
        if debug:
            print("iplmed.py: debug: archs -- %s" % self.display(index))
    def __str__(self):
        string="sources:"
        for x in range(len(self.archs)):
            if self.archs[x] is not None:
                string="%s %s," % (string, archs.levels[x])
        string=string[:-1]
        return "%s " % string
    def active(self):
        # Select the active architecture based upon the available hierarchy
        # If not found, then force internal defaults and select them
        for x in range(len(self.archs)):
            if self.archs[x] is not None:
                return x
        index=len(self.archs)-1
        self.defaults(index)
        return index
    def compatible(self,a,b,debug=False):
        # This method compares two levels for compatibility and returns 
        # True or False.  If False, warning messages are provided
        if debug:
            print("iplmed.py: debug: archs comparing %s:%s" % (a,b))
        if a=="active":
            a_arch=self.active()
            a_name=self.who_is_active()
        else:
            a_arch=archs.sources[a]
            a_name=a
        if b=="active":
            b_arch=self.active()
            b_name=self.who_is_active()
        else:
            b_arch=archs.sources[b]
            b_name=b
        a_pgm_arch=self.get_arch(a_arch)
        b_pgm_arch=self.get_arch(b_arch)
        a_ipl_arch=self.get_ipl_arch(a_arch)
        b_ipl_arch=self.get_ipl_arch(b_arch)
        a_io=self.iochan[a_arch]
        b_io=self.iochan[b_arch]
        compatible=True
        if debug:
            print("iplmed.py: debug: archs inspecting %s:%s" % (a_name,b_name))
            print("iplmed.py: debug:     program arch: %s:%s" \
                % (archs.archmodes[a_pgm_arch],
                   archs.archmodes[b_pgm_arch]))
            print("iplmed.py: debug:     IPL arch:     %s:%s" \
                % (archs.archmodes[a_ipl_arch],
                   archs.archmodes[b_ipl_arch]))
            print("iplmed.py: debug:     I/O arch:     %s:%s" \
                % (archs.iomodes[a_io],
                   archs.iomodes[b_io]))
        if a_pgm_arch!=b_pgm_arch:
            compatible=False
            print("iplmed.py: warning: %s %s and %s %s program architectures "\
                  "incompatible"\
                % (a_name,archs.archmodes[a_pgm_arch],
                   b_name,archs.archmodes[b_pgm_arch]))
        if a_ipl_arch!=b_ipl_arch:
            compatible=False
            print("iplmed.py: warning: %s %s and %s %s IPL architectures "\
                  "incompatible"\
                % (a_name,archs.archmodes[a_ipl_arch],\
                   b_name,archs.archmodes[b_ipl_arch]))  
        if a_io!=b_io:
            compatible=False
            print("iplmed.py: warning: %s %s and %s %s I/O architectures "\
                  "incompatible"\
                  % (a_name,archs.iomodes[a_io],
                     b_name,archs.iomodes[b_io]))
        return compatible
    def defaults(self,index):
        self.archs[index]=2
        self.archs[index]=False
        self.archs[index]=False
    def display(self,index):
        if self.active()==index:
            act=" **active**"
            ast="*"
        else:
            act=""
            ast=" "
        source=archs.levels[index]
        # Get the program architecture
        arch=self.get_arch(index)
        arch=archs.archmodes[arch]
        # Get the IPL architecture
        iplarch=self.get_ipl_arch(index)
        iplarch=archs.archmodes[iplarch]
        # Get the bcmode
        bcmode=self.get_bcmode(index)
        # Get the I/O mode
        if self.iochan[index]:
            io="channel"
        else:
            io="channel subsystem"
        return "%s: %s Program arch=%s, IPL arch=%s, I/O=%s (BC-mode=%s)%s" \
             % (source,ast,arch,iplarch,io,bcmode,act)
             
    # Retrieve program architecture
    def get_arch(self,level):          # Any level
        return self.archs[level]
    def get_arch_mode(self):           # Active level
        return self.get_arch(self.active())

    # Retrive program architecture BC-mode flag
    def get_bcmode(self,level):        # Any level
        return self.archs[level]==0
        
    # Retrieve an I/O architecture
    def get_io_arch(self,level):       # Any level
        return self.iochan[level]
    def get_io_mode(self):             # Active level
        return self.get_io_arch(self.active())
    
    # Retrive an IPL architecture
    def get_ipl_arch(self,level):      # Any level
        arch=self.get_arch(level)
        return archs.iplarch[arch]
    def get_ipl_mode(self):            # Active level
        # This method returns to interested class the PSW mode required for PSW
        return self.get_ipl_arch(self.active())
        
    # Retrieve the IPL architecture BC-mode flag
    def get_ipl_bcmode(self):
        # This method returns a True/False flag if the active arch is S/370 BC-mode
        return self.get_arch(self.active())==0

    # Display the architecture source hierarchy
    def hierarchy(self,alive=True):
        for x in range(len(self.archs)):
            if alive and self.archs[x] is None:
                continue
            print("iplmed.py: archs: %s" % self.display(x))
    def set_arch(self,level,value):
        bcmode=self.bcmode[level]
        if value==1 and bcmode:
            self.archs[level]=0
        else:
            self.archs[level]=value
    def set_cli_arch(self,arch,bcmode,debug=False):
        if bcmode:
            # BC-mode can only be set by the command line, hence if specified
            # it applies to all sources
            self.bcmode=[True,True,True,True]
        arch=archs.cli2arch[arch]
        self.set_arch(0,arch)
    def set_cli_io(self,io):
        cli_arch=self.get_arch(0)
        if io is None and cli_arch is not None:
            self.iochan[0]=archs.iplio[self.get_ipl_arch(0)]
        else:
            self.iochan[0]=archs.cli2io[io]
    def set_elf_arch(self,pyelf):
        if pyelf.iss370():
            self.set_arch(2,1)
        else:
            if pyelf.is64():
                self.set_arch(2,3)
            else:
                self.set_arch(2,2)
        self.iochan[2]=archs.iplio[self.get_arch(2)]
    def set_loader_arch(self,arch_cap):
        # This method converts a loader arch capability into a list of archs
        loader_archs=[False,False,False,False]
        if (arch_cap & 0x80) != 0:  # System/370 EC supported
            loader_archs[1]=True
            loader_archs[0]=self.get_bcmode(0)  # Command line sets bcmode
        if (arch_cap & 0x40) != 0:  # ESA/390 supported
            loader_archs[2]=True
        if (arch_cap & 0x20) != 0:  # z/Architecture supported
            loader_archs[3]=True
        pgm_arch=self.get_arch(2)   # See what the program wants
        if loader_archs[pgm_arch]:  # If the loader supports it, set it
            self.set_arch(1,pgm_arch)
            return
        ipl_arch=self.get_ipl_arch(2)   # See what arch the program needs for IPL
        if loader_archs[ipl_arch]:
            self.set_arch(1,ipl_arch)   # Use the loader for booting then
            print("iplmed.py: warning: archs - loader can boot IPL ELF but can"
                   "not enter the ELF in the expected architecture mode")
            print("                    IPL ELF expects: %s" \
                % archs.archmodes[pgm_arch])
            print("                    LOADER will enter IPL ELF in: %s" \
                % archs.archmodes[ipl_arch])
            return
        print("iplmed.py: warning: archs - loader supports neither the "\
              "architecture nor IPL architecture implied by the IPL ELF")
        for x in range(len(loader_archs)):
            if loader_archs[x]:
                select_arch=x
        self.set_arch(1,select_arch)
        print("iplmed.py: loader architecture selected: %s" \
            % archs.archmodes[select_arch])
    def set_loader_io(self,io_cap):
        # This method converts a loader I/O capability into a list of I/O archs
        if (io_cap & 0x06) == 0x06:
            # Both I/O archs supported, so pick the one the program wants
            self.iochan[1]=self.iochan[2]
            return
        if (io_cap & 0x06) == 0:    # No I/O specified, use arch implied I/O
            self.iochan[1]=archs.iplio[self.get_arch(1)]
            return
        if (io_cap & 0x04) != 0:    # Channel I/O supported
            self.iochan[1]=True
        else:                       # Channel subsystem I/O supported (or assumed)
            self.iochan[1]=False
    def to_loader_arch(self,arch):
        return archs.archs2loader[arch]
    def to_loader_io(self,io):
        return archs.io2loader[io]
    def to_segment_arch(self,arch):
        return archs.archs2mode[arch]
    def who_is_active(self):
        return archs.levels[self.active()].rstrip()

class device_class(object):
    # This class and its subclasses manage the device specific portions of
    # device content creation.  This includes, IPL data, IPL CCW chains, segment
    # content and stream or directed datasets.
    #  Methods       Description
    #
    #  dataset       Creates a list of stream or directed records. The list is
    #                managed by the device_mgr.  This method needs to replace
    #                the deblock method.  Uses directed, stream and next methods
    #
    #  records       Creates IPL data, IPL CCW chains, program or loader content
    #                and additional (program when requiring a loader).  Returns
    #                a list of device specific records for device_mgr handling.
    #
    #                This method must delegate creation of loader records to
    #                a loader if present.
    classes={}
    @staticmethod
    def init():
        CKD()
        ECKD()
        FBA()
        TAPE()
        CARD()
        CDROM()
    @staticmethod
    def enabled(mask):
        # This method creates a list of device_class instances for which the
        # IPL ELF is enalbed.
        devices=[]
        for x in device_class.classes.values():
            if (x.iplmask & mask)!=0:
                devices.append(x)
        return devices
    @staticmethod
    def chunk(data,size):
        # This method breaks a stream into pieces of 'size' length, the last
        # being truncated as required
        chunks=[]
        for x in range(0,len(data),size):
            if x+size<=len(data):
                chunks.append(data[x:x+size])
            else:
                chunks.append(data[x:])
        return chunks
    @staticmethod
    def directed(sego,size,pad=False,eof=False):
        # From an input segment instance, it creates a list of strings of the
        # directed format.  If the final directed string is not a full record 
        # of the specified size, the pad argument determines if the final record
        # should be padded with 0x00 to the complete size.  The eof argument
        # determines if the last record gets the end of directed records flag.
        dirsize=size-4
        address=sego.seg.p_vaddr
        content=sego.content()
        chunks=device_class.chunk(content,dirsize)
        recs=[]
        numrecs=len(chunks)
        lastrec=numrecs-1
        for x in range(numrecs):
            rec=chunks[x]
            if eof and (x==lastrec):
                recs.append(addr31b(address,bit0=1)+rec)
            else:
                recs.append(addr31b(address,bit0=0)+rec)
            address+=dirsize
        if pad:
            recs[-1]=device_class.pad(recs[-1],size)
        return recs
    @staticmethod
    def pad(data,size):
        if len(data)==size:
            return data
        padded=data + size*b"\x00"
        return padded[:size]
    @staticmethod
    def stream(sego,size,pad=False):
        # From an input segment instance, it creates a list of strings of the 
        # required size.  If the final string is not a full record of the
        # specified size, the pad argument determines if the final record
        # should be padded with 0x00 to the complete size.
        recs=device_class.chunk(sego.content(),size)
        if pad:
            recs[-1]=device_class.pad(recs[-1],size)
        return recs
    @staticmethod
    def stream_content(content,size,pad=False):
        # This method performs the same function as the stream staticmethod, but
        # operates on a string of content, rather than a segment instance
        recs=device_class.chunk(content,size)
        if pad:
            recs[-1]=device_class.pad(recs[-1],size)
        return recs
    def __init__(self,dtype,devices=[],iplmask=0x0):
        # Register new device class
        name=self.__class__.__name__
        self.dtype=dtype               # media.py device type string
        try:
            device_class.classes[name]
            raise ValueError("device_class: duplicate class definition: %s" \
                % name)
        except KeyError:
            self.name=name
            device_class.classes[self.name]=self
        # Specify the IPL segment device class mask bit for this device
        self.iplmask=iplmask
    def ccwbeg(self,ccwbeg):
        # override if CCW start needs to be adjusted
        return ccwbeg
    def ccwseg(self,*args,**kwds):
        raise NotImplementedError(\
            "iplmed.py: class must provide ccwseg method: %s"\
            % self.__class__.__name__)
    def deblock(self,*args,**kwds):
        # This method creates device specific stream records from chunks
        raise NotImplementedError(\
            "iplmed.py: class must provide deblock method: %s"\
            % self.__class__.__name__)
    def dataset(self,*args,**kwds):
        # Thie method creates a list of device specific records that constitute
        # a dataset from a list of stream or directed records.
        raise NotImplementedError(\
            "iplmed.py: class must provide dataset method: %s"\
            % self.__class__.__name__)
    def eof(self,*args,**kwds):
        # return a EOF record or None if the device does not support it
        raise NotImplementedError(\
            "iplmed.py: class must provide eof method: %s"\
            % self.__class__.__name__)
    def iplccw1(self,*args,**kwds):
        raise NotImplementedError(\
            "iplmed.py: class must provide iplccw1 method: %s"\
            % self.__class__.__name__)
    def iplccw2(self,*args,**kwds):
        raise NotImplementedError(\
            "iplmed.py: class must provide iplccw2 method: %s"\
            % self.__class__.__name__)
    def next(self,*args,**kwds):
        # Given a record id, determines the next record id
        raise NotImplementedError(\
            "iplmed.py: class must provide next method: %s"\
            % self.__class__.__name__)
    def records(self,*args,**kwds):
        # Creates from a list of iplmed.record instances a list of media.rec 
        # instances.  This is where the IPL ELF data gets converted to device
        # specific content.
        raise NotImplementedError(\
            "iplmed.py: class must provide records method: %s"\
            % self.__class__.__name__)
    def volsup(self,*args,**kwds):
        # Defines whether a DASD Standard Volume is supported by the device class.
        # Returns True if the standard is supported, False otherwise
        return False

class CARD(device_class):
    # Note: Loaders must be used for program and LOWC segments
    #       If LOWC segments are to be used, both must use directed records
    padding=80*"\x00"
    @staticmethod
    def build_ccws(start,cards=[],lastflag=0):
        addr=start
        ccws=[]
        for x in cards:
            ccws.append(ccw0(READ,addr,len(x),CC))
            addr+=80
        last=ccws[-1]
        last.flags=lastflag
        return ccws
    @staticmethod
    def chunk(data):
        # Returns recsutil card insances
        cards=device_class.chunk(data,80)
        cards[-1]=CARD.pad(cards[-1])
        recs=[]
        for x in cards:
            recs.append(card(data=x))
        return recs
    @staticmethod
    def pad(data):
        if len(data)==80:
            return data
        padded="%s%s" % (data,CARD.padding)
        return padded[:80]
    def __init__(self):
        device_class.__init__(self,"pun",iplmask=0x08)
        # Data for building ccw chain
        self.ipllen=0      # Length of IPL card data read by IPL record 0
    def ccwcards(self,start,ccws=[]):
        data=""
        for x in ccws:
            data+=x.binary()
        return data
    def ccwseg(self,ccwbeg,pgmo,lowc=None,iplpsw=None,debug=False):
        # For cards, lowc must be loaded by the loader.  Only pgmo is loaded
        # by the ccw chain.
        # The following chain is built:
        # IPL card 1      reads CCW records or pgmo content cards ( maximum CCW 
        #                 10 cards )
        # CCW cards 2-9   reads pgmo content ( 10 cards per record ) - optional
        # pgm cards 10-n pgmo content
        #
        # Maximum CCW card is 10, each containing 10 data reading CCw's.  Each
        # CCW card reads a maximum of 10 data cards (or 800 bytes of content)
        # The maximum amount of data readable is 10 (CCW cards) * 800 or 8000
        # bytes of content.  If the program content is small enough (800 or less),
        # only card 1 will be used.
        this=chain(ccwbeg)
        self.this=this
        if len(pgmo.content())>8000:
            print("iplmed.py: error: CARD loading restricted to 8000 bytes " \
                "or less: %s" \
                % len(pgmo.content()))
        if len(pgmo.content())==0:
            print("iplmed.py: error: IPL program content of zero length")  
        
        pgmcards=device_class.chunk(pgmo.content(),80)
        pgmccws=CARD.build_ccws(pgmo.seg.p_vaddr,cards=pgmcards,lastflag=SLI)
        if debug:
            string="iplmed.py: debug: program content CCW's:"
            for x in pgmccws:
                string="%s\n    %s" % (string,x)
            print(string)
        pgmcards[-1]=CARD.pad(pgmcards[-1])
        
        # If CCW cards are not needed just generate the first card to read
        # the program.
        if len(pgmccws)<=10:
            return self.iplcard(ccwbeg,ccws=pgmccws)
            
        # CCW cards are required.
        #
        # Determine how many CCW cards required to read content
        # Memory layout:
        #    ccwbeg              ccwbeg+8*CCW's in iplcard
        #    iplcard data        CCW card data
        #num_cardccws=len(cardccws)
        ccwcards=roundup(len(pgmccws),10)  # 10 pgm CCW's per CCW card
        ccwcards_beg=ccwbeg+8*ccwcards
        # Turn the pgm ccws into a string
        cardccws=""
        for x in pgmccws:
            cardccws+=x.binary()
        cardccw_recs=device_class.chunk(cardccws,80)
        # cardccw_recs is the content for the CCW cards
        # Create the CCW's for the IPL card
        iplccws=CARD.build_ccws(ccwcards_beg,cards=cardccw_recs,lastflag=CC+SLI)
        if debug:
            string="iplmed.py: debug: CCW chain CCW's for CCW cards:"
            for x in iplccws:
                string="%s\n    %s" % (string,x)
            print(string)
        cardccw_recs[-1]=CARD.pad(cardccw_recs[-1])
        iplcard=self.iplcard(ccwbeg,ccws=iplccws)
        for x in cardccw_recs:
            iplcard+=x  
        return iplcard
    def dataset(self,sego,size,pad=False,directed=False,eof=False,start=None,\
            debug=False):
        # Convert a segment's content into a list of directed or stream card
        # images.  The start argument specifies the initial record id for
        # the device records.  Cards do not use a position record id.  The
        # cont argument determines if the last directed record will have the
        # end of stream indicator set in the last record. 
        if directed:
            recs=device_class.directed(sego,size,pad=pad,eof=eof)
        else:
            recs=device_class.stream(sego,eof=eof)
        cards=[]
        for x in recs:
            cards.append(card(x))
        return cards
    def eof(self):
        # Return a physical EOF record
        return None
    def iplcard(self,start,ccws=[]):
        data=""
        for x in ccws:
            data+=x.binary()
        self.ipllen=len(data)
        return CARD.pad(data)
    def iplccw1(self,ccwbeg,ccwlen):
        self.this.target()
        return ccw0(READ,ccwbeg,self.ipllen,CC+SLI).binary()
    def iplccw2(self,ccwbeg):
        return ccw0(TIC,ccwbeg).binary()    
    def records(self,mgr,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
            dmgr=None,debug=False):
        dev_recs=[]
        
        if debug:
            for x in range(len(iplrecs)):
                print("iplmed.py: debug: CARD.records: iplrecs[%s]=%s" \
                    % (x,iplrecs[x]))
        
        # Card IPL Rec 0 - 24-bytes of IPL data
        dev_recs.append(card(CARD.pad(data=iplrecs[0].content())))
    
        # Card IPL Rec 1 - CCW segment 
        if iplrecs[1] is not None:
            dev_recs.extend(CARD.chunk(iplrecs[1].content()))

        # Card IPL Rec 2 - loader or program segment
        lowc=False
        pgm=False
        lodr=None
        if iplrecs[2] is not None:
            if isinstance(iplrecs[2],loader):
                lodr=iplrecs[2]
                if not lodr.pgm.test_arch(arch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "required CPU architecture: %02X" % arch)
                if not lodr.pgm.test_io(ioarch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "require I/O architecture: %02X" % io)
                if not lodr.check_device(self.iplmask):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "device")
                pgm=lodr.pgm.supported
                lowc=lodr.lowc.supported
                lodr.update(14*"\x00"+chr(arch)+chr(self.iplmask|ioarch))
            dev_recs.extend(CARD.chunk(iplrecs[2].content()))
            
        # Card IPL Rec 4 - ELF or TEXT segment
        # Card IPL Rec 3 - LOWC segment
        #  Note: the program ELF is loaded first, then LOWC (if supported)
        #        This is required so that the loader can depend upon the ELF
        #        or text segment being first in the stream of card images.
        #        By being first, the loader can readily determine where to enter
        #        the program.
        if ((iplrecs[4] is not None) or (iplrecs[3] is not None)):
           if lodr is None:
               print("iplmed.py: error: program and/or LOWC segment requires " \
                   "loader")
               sys.exit(1)
           else:
               if noboot:
                   print("iplmed.py: warning: CARD boot program blocks suppressed")
               dev_recs.extend(\
                   lodr.records(self,program=iplrecs[4],lowc=iplrecs[3],debug=debug))

        return dev_recs

class CDROM(device_class):
    # Note: Loaders are treated as any other loaded segment.
    zeros=8*"\x00"
    def __init__(self):
        device_class.__init__(self,None,iplmask=0x01)
    def ccwseg(self,ccwbeg,pgmo,lowc=None,iplpsw=None,debug=False):
        if (lowc!=None) and not lowc.overwrite():
            # Not overwriting IPL PSW, so replicate it in low core
            lowc.iplpsw(iplpsw)
        return ""
    def iplccw1(self,ccwbeg,ccwlen):
        return CDROM.zeros
    def iplccw2(self,ccwbeg):
        return CDROM.zeros
    def records(self,mgr,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
            dmgr=None,debug=False):
        # Convert a list of iplmed records instances into a list of cdrom_record
        # instances
        dev_recs=[]
        
        # CDROM IPL Rec 0 - 24-bytes of IPL data
        dev_recs.append(cdrom_record(iplrecs[0]))
        
        # CDROM IPL Rec 1 - CCW segment 
        if iplrecs[1] is not None:
            rec=iplrecs[1]
            if len(rec.seg.content)!=0:
                print("iplmed.py: warning: CCW segment ignored for CDROM device")
        
        # CDROM IPL Rec 2 - loader or program segment
        pgm=False
        lodr=None
        if iplrecs[2] is not None:
            if isinstance(iplrecs[2],loader):
                lodr=iplrecs[2]
                if not lodr.pgm.test_arch(arch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "required architecture: %02X" % arch)
                if not lodr.check_device(self.iplmask):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "device")
                pgm=lodr.pgm.supported
                if pgm and lodr.pgm.update:
                    if iplrecs[4] is not None:
                        prep_data=addr31b(iplrecs[4].entry,bit0=0)+10*"\x00"\
                            +chr(arch)+chr(self.iplmask)
                    else:
                        prep_data=14*"\x00"+chr(arch)+chr(self.iplmask|ioarch)
                    lodr.update(prep_data)
            dev_recs.append(cdrom_record(iplrecs[2]))
        
        # CDROM IPL Rec 3 - LOWC segment
        if iplrecs[3] is not None:
            if (lodr is not None) and lodr.lowc.supported:
                print("iplmed.py: warning: IPL function supporting LOwC "\
                    "segment not bootstrap loader")
            dev_recs.append(cdrom_record(iplrecs[3]))

        # CDROM IPL Rec 4 - ELF or TEXT segment
        if iplrecs[4] is not None:
            if (lodr is not None) and lodr.pgm.supported:
                print("iplmed.py: warning: IPL function supporting program "\
                    "segment not bootstrap loader")
            dev_recs.append(cdrom_record(iplrecs[4]))

        return dev_recs

class CKD(device_class):
    # Note: Loaders may only be used for an additional program, not LOWC segment
    IPL0="\xC9\xD7\xD3\xF0"
    IPL1="\xC9\xD7\xD3\xF1"
    IPL3="\xC9\xD7\xD3\xF3"
    @staticmethod
    def info(recsize,mgr):
        # This method interogates the media.py device and returns the 
        # ckd_info instance that provides details about the device
        return mgr.med_device.hndcls.info(mgr.mtype,keylen=0,datalen=recsize)
    def __init__(self,iplmask=0x80):
        device_class.__init__(self,"ckd",iplmask=iplmask)
    def ccwseg(self,ccwbeg,pgmo,lowc=None,iplpsw=None,debug=False):
        # +0 BBCCHHR ID of Program record (used for SEEK and SEARCH ID)
        #      (+8) BBCCHHR ID of lowc record - optional
        # +8  (+16) SEEK IPL program track
        # +16 (+24) SEARCH ID EQUAL of IPL program record ID
        # +24 (+32) TIC back to SEARCH ID EQUAL
        # +32 (+40) READ DATA of IPL program record
        #     (+48) SEEK IPL lowc track               - optional
        #     (+52) SEARCH ID EQUAL of IPL lowc track - optional
        #     (+60) TIC back to SEARCH ID EQUAL       - optional
        #     (+68) READ DATA of IPL lowc record      - optional
        if debug:
            print("iplmed.py: debug: %s IPL CCW chain continues at: %06X" \
                % (self.__class__.__name__,ccwbeg))
        this=chain(ccwbeg)
        self.this=this
        "pid" << ckdid(cc=0,hh=1,r=1,seek=True,pad=True)
        if debug:
            print("iplmed.py: debug: %s IPL program seek/search data at: %06X" \
                % (self.__class__.__name__,self.this.value("pid")))
        if lowc!=None:
            "lid" << ckdid(cc=0,hh=0,r=3,seek=True,pad=True)
            if debug:
                print("iplmed.py: debug: %s IPL lowc seek/search data at: %06X" \
                    % (self.__class__.__name__,self.this.value("lid")))
        "tic" << ccw0(CKD_SEEK,"pid",6,CC)
        if debug:
            print("iplmed.py: debug: %s IPL program seek at: %06X" \
                % (self.__class__.__name__,self.this.value("tic")))
        "psrch" << ccw0(CKD_SIDEQ,self.this.value("pid")+2,5,CC)
        if debug:
            print("iplmed.py: debug: %s IPL program search id at: %06X" \
                % (self.__class__.__name__,self.this.value("psrch")))
        ccw0(TIC,"psrch",0,0)
        next=self.this.next()
        if lowc!=None:
            ccw0(CKD_RDATA,pgmo.seg.p_vaddr,len(pgmo.seg.content))
        else:
            ccw0(CKD_RDATA,pgmo.seg.p_vaddr,len(pgmo.seg.content),CC)
        if debug:
            print("iplmed.py: debug: %s IPL program read at: %06X" \
                % (self.__class__.__name__,next))
        if lowc!=None:
            next=self.this.next()
            ccw0(CKD_SEEK,"lid",6,CC)
            if debug:
                print("iplmed.py: debug: %s IPL lowc seek at: %06X" \
                    % (self.__class__.__name__,next))
            "lsrch" <<  ccw0(CKD_SIDEQ,self.this.value("lid")+2,5,CC)
            if debug:
                print("iplmed.py: debug: %s IPL lowc search id at: %06X" \
                    % (self.__class__.__name__,self.this.value("lsrch")))
            ccw0(TIC,"lsrch",0,0)
            #if not lowc.overwrite():
                # Not overwriting IPL PSW, so replicate it in low core
            #    lowc.iplpsw(iplpsw)
            next=self.this.next()
            ccw0(CKD_RDATA,0,len(lowc.seg.content),0)
            if debug:
                print("iplmed.py: debug: %s IPL lowc read at: %06X" \
                    % (self.__class__.__name__,next))
        return this.binary()
    def dataset(self,sego,size,pad=False,directed=False,eof=False,start=None,\
            debug=False):
        # Convert a segment's content into a list of directed or stream records.
        # The start argument specifies the initial record id for the device records.  For CKD devices this is a CKDID instance. 
        # For directed block format, the eof argument determines if the last 
        # directed record will have the last block indicator set in the block's
        # header.  For stream blocks, eof has no meaning.
        if directed:
            if debug:
                print("iplmed.py: debug: CKD.dataset: building CKD directed " \
                    "dataset: size=%s,pad=%s,eof=%s,start=%s" \
                    % (size,pad,eof,start))
            recs=device_class.directed(sego,size,pad=pad,eof=eof)
        else:
            if debug:
                print("iplmed.py: debug: CKD.dataset: building CKD stream " \
                    "dataset: size=%s,pad=%s,start=%s" \
                    % (size,pad,start))
            recs=device_class.stream(sego,size,pad=pad)
        blocks=[]
        rid=start
        if debug:
            print("iplmed.py: debug: CKD.dataset: Starting rid=%s" % rid)
        for x in recs:
            blk=ckd(data=x,cc=rid.cc,hh=rid.hh,r=rid.r)
            rid+=1   # Increment to recid of next block
            if debug:
                print("iplmed.py: debug: CKD.dataset: next rid=%s" % rid)
            blocks.append(blk)
        if debug:
             print("iplmed.py: debug: CKD.dataset: EOF rid=%s" % rid)
        blocks.append(self.eof(rid))
        return blocks
    def eof(self,rid=None):
        if not isinstance(rid,CKDID):
            return None
        return eof(cc=rid.cc,hh=rid.hh,r=rid.r)
    def iplccw1(self,ccwbeg,ccwlen):
        self.this.target()
        return ccw0(CKD_RDATA,ccwbeg,ccwlen,CC).binary()
    def iplccw2(self,ccwbeg):
        return ccw0(TIC,"tic").binary()
    def records(self,mgr,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
            dmgr=None,debug=False):
        fba.strict=False
        dev_recs=[]
        pgm_id=None
        
        if debug:
            for x in range(len(iplrecs)):
                print("iplmed.py: debug: CKD.records: iplrecs[%s]=%s" \
                    % (x,iplrecs[x]))

        # CKD IPL Rec 0 - 24-bytes of IPL data
        dev_recs.append(\
            ckd(data=iplrecs[0].content(),key=CKD.IPL0,cc=0,hh=0,r=1))

        # CKD IPL Rec 1 - CCW segment
        if iplrecs[1] is not None:
            dev_recs.append(\
                ckd(data=iplrecs[1].content(),key=CKD.IPL1,cc=0,hh=0,r=2))

        # CKD IPL Rec 2 - loader or program segment
        pgm=False
        lodr=None
        if iplrecs[2] is not None:
            if isinstance(iplrecs[2],loader):
                lodr=iplrecs[2]
                if not lodr.pgm.test_arch(arch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "required architecture: %02X" % arch)
                if not lodr.check_device(self.iplmask):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "device")
                pgm=lodr.pgm.supported
                if pgm and lodr.pgm.update:
                    # Determine disk geometry info for the IPL program dataset
                    geo=CKD.info(lodr.pgm.recsize,mgr)
                    # Create the initial record id
                    pgm_id=CKDID(0,2,1,\
                        cyls=geo.cylinders-1,
                        heads=geo.heads-1,
                        recs=geo.NUMRECS)
                    if debug:
                        print("iplmed.py: debug: CKD.records: block_size=%s," \
                            "max_cyl=%s,max_head=%s,blocks/track=%s" \
                            % (lodr.pgm.recsize,
                               pgm_id.cyls,
                               pgm_id.heads,
                               pgm_id.recs))
                    # Create the loader interface data
                    prep_data=halfwordb(0)+halfwordb(2)+byteb(1)
                    prep_data+=byteb(pgm_id.recs)+halfwordb(pgm_id.cyls)
                    prep_data+=halfwordb(pgm_id.heads)
                    prep_data+=4*b"\x00"
                    prep_data+=chr(arch)
                    prep_data+=chr(self.iplmask|ioarch)
                    lodr.update(prep_data)
            dev_recs.append(\
                ckd(data=iplrecs[2].content(),cc=0,hh=1,r=1))

        # CKD IPL Rec 3 - lowc segment
        if iplrecs[3] is not None:
            if (lodr is not None) and lodr.lowc.supported:
                print("iplmed.py: warning: IPL function supporting LOwC "\
                    "segment not bootstrap loader")
            dev_recs.append(\
                ckd(data=iplrecs[3].content(),key=CKD.IPL3,cc=0,hh=0,r=3))

        # CKD IPL Rec 4 - ELF or TEXT segment loaded by loader
        if iplrecs[4] is not None:
            if lodr is None:
                print("iplmed.py: error: program requires loader")
                sys.exit(1)
            else:
                dev_recs.extend(lodr.records(self,\
                    program=iplrecs[4],start=pgm_id,debug=debug))
        
        # pgm_id contains the cchhr of the next record that would be written on
        # the volume.  It can be used to determine how much space to reserve on a
        # DASD Standard Volume.  If pgm_id is None then the first two tracks only
        # should be reserved.  DASD Volume Blocks should be added to dev_recs
        # before returning.
        
        return dev_recs

class CKDID(object):
    def __init__(self,cc,hh,r,cyls=0,heads=0,recs=0):
        # CKD Record ID information
        self.cc=cc
        self.hh=hh
        self.r=r
        # Geometry information
        self.cyls=cyls      # Maximum cylinders
        self.heads=heads    # Tracks per cylinder
        self.recs=recs      # Records per track of some consistent size
    def __str__(self):
        return "CKD id=(%s,%s,%s) geometry: max cyl=%s, mac head=%s, " \
            "recs/track=%s" \
            % (self.cc,self.hh,self.r,self.cyls,self.heads,self.recs)
    def __add(self,recs):
        c=self.cc
        h=self.hh
        r=self.r+1
        if r>self.recs:
            (incr,rec)=(r+self.recs-1)%self.recs
            r=rec+1
            h=self.hh+incr
            if h>self.heads:
                incr=(h+self.hh-1)//self.heads
                c=self.cc+incr
                if c>self.cyls:
                    raise ValueError("iplmed.py: error: CKD device overflow")
        return (c,h,r)
    def __add__(self,other):
        (c,h,r)=self.__add(other)
        return CKDID(c,h,r,cyls=self.cyls,heads=self.heads,recs=self.recs)
    def __radd__(self,other):
        raise NotImplementedError("iplmed.py: internal: CKDID may not be added " \
            "to another value")
    def __iadd__(self,other):
        res=self.__add(other)
        #print("CKDID.__iadd__: result=(%s,%s,%s)" % res)
        self.cc=res[0]
        self.hh=res[1]
        self.r=res[2]
        return self
    def reserve(self,next=False):
        # This method returns the number of tracks that should be reserved on a
        # DASD Standard Volume based upon the current cc,hh,r information.  
        #
        # If called with next=True, the current information represents the next
        # record that would be written.  In this case, r==1 indicates the current
        # track does not need to be reserved
        tracks=((self.cc)*self.heads)+self.hh+1
        if next and self.r==1:
            tracks-=1
        return tracks

class ECKD(CKD):
    def __init__(self):
        CKD.__init__(self,iplmask=0x40)

class FBA(device_class):
    # Note: Loaders may only be used for an additional program, not LOWC segment
    def __init__(self):
        device_class.__init__(self,"fba",iplmask=0x20)
        self.dasd=None         # volume.DASDDEFN instance for DASD Standard Volume
        self.last_sector=-1
    def addrecs(self,lst,recs):
        # Adds a list of fba instances (recs) to a list (lst) keeping track of the
        # last sector added to the list.
        newlst=lst
        newlst.extend(recs)
        self.last_sector=newlst[-1].sector
        return newlst
    def ccwbeg(self,begin):
        # Make sure not overwritten by last block of program and
        # CCW's chain continues following the IPLPSW, IPLCCW1 and IPLCCW2
        return begin+512+24  # Make sure not overwritten by last block of program
    def ccwseg(self,ccwbeg,pgmo,lowc=None,iplpsw=None,debug=False):
        # +0  pgm locate parameters
        # +8  lowc locate parameters (or zeros) - optional
        # +16 LOCATE CCW (for program read)
        # +24 READ CCW for program
        # +32 LOCATE CCW (for lowc read)        - optional
        # +40 READ CCW                          - optional
        # length of ccws: 24 or 48 bytes
        if debug:
            print("iplmed.py: debug: %s IPL CCW chain continues at: %06X" \
                % (self.__class__.__name__,ccwbeg))
        this=chain(ccwbeg)
        self.this=this
        pgmsecs=align(len(pgmo.seg.content),512)//512
        if debug:
            print ("iplmed.py: debug: %s IPL program resides in %s sectors" \
                % (self.__class__.__name__,pgmsecs))
        pgmsec=4
        if debug:
            print("iplmed.py: debug: %s IPL program starting sector: %s" \
                % (self.__class__.__name__,pgmsec))
        chain()
        "pl" << fbaloc(FBAL_READ,sector=pgmsec,sectors=pgmsecs)
        if debug:
            print("iplmed.py: debug: %s IPL program locate data: %06X" 
                % (self.__class__.__name__,self.this.value("pl")))
        pgmflag=0
        if lowc!=None:
            lowcsecs=align(len(lowc.seg.content),512)//512
            if debug:
                print("iplmed.py: debug: %s IPL lowc resides in %s sectors" \
                    % (self.__class__.__name__,lowcsecs))
            "ll" << fbaloc(FBAL_READ,sector=2,sectors=lowcsecs)
            if debug:
                print("iplmed.py: debug: %s IPL lowc locate data: %06X" \
                    % (self.__class__.__name__,self.this.value("ll")))
            pgmflag=CC
        "tic" << ccw0(FBA_LOC,"pl",8,CC)
        if debug:
            print("iplmed.py: debug: %s IPL program locate CCW at: %06X" \
                % (self.__class__.__name__,self.this.value("tic")))
            print("iplmed.py: debug: %s IPL program read ccw at: %06X" \
                % (self.__class__.__name__,self.this.next()))
        ccw0(FBA_READ,pgmo.seg.p_vaddr,roundup(len(pgmo.seg.content),512),pgmflag)
        if lowc!=None:
            if debug:
                print("iplmed.py: debug: %s IPL lowc locate ccw at: %06X" \
                % (self.__class__.__name__,self.this.next()))
            ccw0(FBA_LOC,"ll",8,CC)
            if debug:
                print("iplmed.py: debug: %s IPL lowc read ccw at: %06X" \
                    % (self.__class__.__name__,self.this.next()))
            ccw0(FBA_READ,0,roundup(len(lowc.seg.content),512),0)
        return this.binary()
    def dataset(self,sego,size,pad=False,directed=False,eof=False,start=None,\
            debug=False):
        # Convert a segment's content into a list of directed or stream block
        # images.  The start argument specifies the initial record id for
        # the device records.  For FBA devices this is its sector number. 
        # For directed block format, the eof argument determines if the last 
        # directed record will have the last block indicator set in the block's
        # header.  For stream blocks, eof has no meaning.
        if directed:
            if debug:
                print("iplmed.py: debug: building FBA directed dataset: "
                    "size=%s,pad=%s,eof=%s,start=%s" \
                    % (size,pad,eof,start))
            recs=device_class.directed(sego,size,pad=pad,eof=eof)
        else:
            if debug:
                print("iplmed.py: debug: building FBA stream dataset: " \
                    "size=%s,pad=%s,start=%s" \
                    % (size,pad,start))
            recs=device_class.stream(sego,size,pad=pad)
        sectors=[]
        sec=start
        for x in recs:
            secs=self.sectorize(sec,x)
            sec+=len(secs)
            sectors.extend(secs)
        return sectors
    def eof(self):
        return None
    def iplccw1(self,ccwbeg,ccwlen):
        self.this.target()
        return ccw0(IPLREAD,ccwbeg-24,512,CC).binary()
    def iplccw2(self,ccwbeg):
        self.this.target()
        return ccw0(TIC,"tic").binary()
    def records(self,mgr,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
            dmgr=None,debug=False):
        fba.strict=False
        dev_recs=[]
        
        if debug:
            for x in range(len(iplrecs)):
                print("iplmed.py: debug: FBA.records: iplrecs[%s]=%s" \
                    % (x,iplrecs[x]))
        
        # Sectors on the FBA Volume are allocated here.  These allocations are
        # needed here to allow creation of the IPLP repository information before
        # actually creating the LOWC data.
        fbamap=FBAMAP()
        fbamap.allocate("IPL",1)
        fbamap.allocate("VOLLBL",1)
        fbamap.allocate("LOWC",2)
        if iplrecs[2] is not None:
            fbamap.allocate("Program",self.sectors(len(iplrecs[2].content())))
        if isinstance(iplrecs[2],loader):
            # Calculate the number of sectors consumed by the program directed 
            # records
            lodr=iplrecs[2]
            recsize=lodr.pgm.recsize
            if lodr.pgm.directed:
                # If we are using directed blocks format, the actual data per block
                # is less 4 for the directed information.
                recsize-=4
            if iplrecs[4] is not None:
                elf_len=len(iplrecs[4].content())
                directed_blocks=(elf_len+recsize-1)//recsize
                fbasize=directed_blocks*(recsize+4)
                fbasectors=self.sectors(fbasize)
                fbamap.allocate("ELF",fbasectors)

        if debug:
            print("iplmed.py: debug: FBA Volume Content Sector Allocations")
            fbamap.display(prefix="iplmed.py: debug:    ")

        # FBA IPL Rec 0 - 24-bytes of IPL data
        # FBA IPL Rec 1 - CCW segment 
        # Note: IPL record 0 and IPL record 1 merged into a single FBA sector
        dev_recs.append(\
            fba(data=iplrecs[0].content()+iplrecs[1].content(),sector=0))

        # FBA IPL Rec 2 - loader or program segment
        pgm=False
        lodr=None
        if iplrecs[2] is not None:
            if isinstance(iplrecs[2],loader):
                lodr=iplrecs[2]
                if not lodr.pgm.test_arch(arch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "required architecture: %02X" % arch)
                if not lodr.check_device(self.iplmask):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "device")
                pgm=lodr.pgm.supported
                #pgm_sector=3+self.sectors(lodr.length())
                pgm_allocate=fbamap.areas["ELF"]
                pgm_sector=pgm_allocate.sector
                if pgm and lodr.pgm.update:
                    prep_data=fullwordb(pgm_sector)
                    prep_data+=10*b"\x00"
                    prep_data+=chr(arch)
                    prep_data+=chr(self.iplmask|ioarch)
                    lodr.update(prep_data)
            vol_sect=fbamap.areas["Program"]
            vol_sect=vol_sect.sector
            recs=self.dataset(iplrecs[2],512,pad=True,start=vol_sect,debug=debug)
            dev_recs.extend(recs)
            next_sector=3+len(recs)

        # FBA IPL Rec 3 - LOWC segment
        if iplrecs[3] is not None:
            # Update the LOWC segment if building a DASD Volume Standard device
            if vol is not None:
                iplrecs[3].vol(1, 512)
            recs=self.dataset(iplrecs[3],512,pad=True,start=2,debug=debug)
            dev_recs.extend(recs)
            
        # FBA IPL Rec 4 - ELF or TEXT segment loaded by loader
        if (iplrecs[4] is not None):
            if lodr is None:
                print("iplmed.py: error: program requires loader")
                sys.exit(1)
            else:
                vol_sect=fbamap.areas["ELF"]
                vol_sect=vol_sect.sector
                dev_recs.extend(lodr.records(self,program=iplrecs[4],\
                    start=vol_sect, debug=debug))

        # FBA DASD VOlume Standard content added to records
        #
        # fbamap.pos is the number of sectors that must be reserved on an FBA
        # DASD Standard Volume for the IPL medium preparation processor data.
        if vol is not None:
            dasd_recs=[]
            try:
                self.dasd=volume.DASDDEFN(vol,sec=fbamap.pos,\
                    device=dmgr.med_device,\
                    minimize=dmgr.trunc,compress=dmgr.compress,\
                    debug=debug)
                dasd_recs=self.dasd.construct(external=True,debug=debug)
            except ValueError:
                print("iplmed.py: ERROR: could not construct DASD Volume content, "
                    "content not added to volume")
            dev_recs.extend(dasd_recs)
        return dev_recs
    
    def volsup(self):
        # Identify the DASD Volume Standard is supported by this class
        return True

    def sectorize(self,start,data):
        # This method converts a block into individual sectors and returns a list
        sectors=[]
        cur_sector=start
        for x in range(0,len(data),512):
            if x+512<=len(data):
                sectors.append(fba(data=data[x:x+512],sector=cur_sector))
            else:
                sectors.append(fba(data=data[x:],sector=cur_sector))
            cur_sector+=1
        return sectors
        
    def sectors(self,bytes):
        # return the number of sectors required to contain supplied bytes
        return (bytes+511)//512

# Classes that manage the FBA volume IPL Medium Preparation Processor content
class FBAMAP(object):
    def __init__(self):
        self.areas={}      # Allocated area, FBAMAPE instance, accessed by name
        self.arealist=[]   # List of allocated areas
        self.pos=0         # The next available sector or number of sectors used
    def allocate(self, name, size=0):
        # Allocate an area of 'size' sectors with 'name'
        entry=FBAMAPE(name,self.pos,size)
        self.areas[entry.name]=entry
        self.arealist.append(entry)
        self.pos+=entry.sectors
    def display(self, prefix=""):
        for x in self.arealist:
            print("%s%s" % (prefix,x))
    def reserve(self):
        # Returns the number of sectors to reserve on a DASD Standard Volume.
        return self.pos
    def start(self,name):
        # Return the starting sector number of an area by its name
        entry=self.areas[name]
        return entry.sector

class FBAMAPE(object):
    def __init__(self,name,sector=None,sectors=0):
        self.name=name        # Area name
        self.sector=sector    # Starting sector of the FBA area
        self.sectors=sectors  # Number of sectors
    def __str__(self):
        name="%s        " % self.name
        name=name[:8]
        return "%s %s-%s sectors=%s" \
            % (name, self.sector, self.sector+self.sectors-1, self.sectors)

class TAPE(device_class):
    # Note: Loaders may only be used for an additional program, not LOWC segment
    #       If used, the loader should REW and FSF to get to the start of the
    #       additional records.
    def __init__(self):
        device_class.__init__(self,"tape",iplmask=0x10)
    def ccwseg(self,ccwbeg,pgmo,lowc=None,iplpsw=None,debug=False):
        # +0   read program
        # +8   read lowc - optional
        if debug:
            print("iplmed.py: debug: %s IPL CCW chain continues at: %06X" \
                % (self.__class__.__name__,ccwbeg))
        this=chain(ccwbeg)
        self.this=this
        if len(pgmo.seg.content)>65535:
            print("iplmed.py: error: IPL program > 65535 bytes: %s" \
                % len(pgmo.seg.content))
            sys.exit(1)
        "tic" << ccw0(READ,pgmo.seg.p_vaddr,len(pgmo.seg.content),CC)
        if debug:
            print("iplmed.py: debug: %s IPL program read ccw at: %06X" \
                % (self.__class__.__name__,self.this.value("tic")))
        if lowc!=None:
            if debug:
                print("iplmed.py: debug: %s IPL lowc read ccw at: %06X" \
                % (self.__class__.__name__,self.this.next()))
            #if not lowc.overwrite():
                # Not overwriting IPL PSW, so replicate it in low core
            #    lowc.iplpsw(iplpsw)
            if len(lowc.seg.content)>65535:
                print("iplmed.py: error: IPL lowc > 65535 bytes: %s" \
                    % len(lowc.seg.content))
                sys.exit(1)
            ccw0(READ,0,len(lowc.seg.content),0)
        return this.binary()
    def dataset(self,sego,size,pad=False,directed=False,eof=False,start=None,\
            debug=False):
        # Convert a segment's content into a list of directed or stream card
        # images.  The start argument specifies the initial record id for
        # the device records.  Cards do not use a position record id.  The
        # cont argument determines if the last directed record will have the
        # end of stream indicator set in the last record. 
        if directed:
            if debug:
                print("iplmed.py: debug: building TAPE directed dataset: "
                    "size=%s,pad=%s,eof=%s" \
                    % (size,pad,eof))
            recs=device_class.directed(sego,size,pad=pad,eof=eof)
        else:
            if debug:
                print("iplmed.py: debug: building TAPE stream dataset: pad=%s" \
                    % pad)
            recs=device_class.stream(sego,pad=pad)
        blocks=[]
        for x in recs:
            blocks.append(tape(data=x))
        return blocks
    def eof(self):
        return tm()
    def iplccw1(self,ccwbeg,ccwlen):
        self.this.target()
        return ccw0(READ,ccwbeg,ccwlen,CC).binary()
    def iplccw2(self,ccwbeg):
        self.this.target()
        return ccw0(TIC,"tic").binary()
    def records(self,mgr,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
            dmgr=None,debug=False):
        dev_recs=[]

        if debug:
            for x in range(len(iplrecs)):
                print("iplmed.py: debug: TAPE.records: iplrecs[%s]=%s" \
                    % (x,iplrecs[x]))

        # Tape IPL Rec 0 - 24-bytes of IPL data
        dev_recs.append(tape(data=iplrecs[0].content()))
        
        # Tape IPL Rec 1 - CCW segment 
        if iplrecs[1] is not None:
            dev_recs.append(tape(data=iplrecs[1].content()))

        # Tape IPL Rec 2 - loader or program segment
        pgm=False
        lodr=None
        if iplrecs[2] is not None:
            if isinstance(iplrecs[2],loader):
                lodr=iplrecs[2]
                if not lodr.pgm.test_arch(arch):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "required architecture: %02X" % arch)
                if not lodr.check_device(self.iplmask):
                    print("iplmed.py: warning: LOADER segment does not support " \
                        "device")
                pgm=lodr.pgm.supported
                if pgm and lodr.pgm.update:
                    lodr.update(14*"\x00"+chr(arch)+chr(self.iplmask|ioarch))
            dev_recs.append(tape(data=iplrecs[2].content()))
        
        # Tape IPL Rec 3 - LOWC segment
        if iplrecs[3] is not None:
            if (lodr is not None) and lodr.lowc.supported:
                print("iplmed.py: warning: IPL function supporting LOwC "\
                    "segment not bootstrap loader")
            dev_recs.append(tape(data=iplrecs[3].content()))
           
        # Tape IPL Rec 4 - ELF or TEXT segment loaded by loader
        if (iplrecs[4] is not None):
            if lodr is None:
                print("iplmed.py: error: program requires loader")
                sys.exit(1)
            else:
                dev_recs.extend(\
                    lodr.records(self,program=iplrecs[4],debug=debug))
        
        # Terminating physical end-of-file indicators
        if lodr and lodr.pgm.directed_eof:
            # If loader used directed eof, need to add a physical eof
            dev_recs.append(self.eof())
        else:
            dev_recs.append(self.eof())
        dev_recs.append(self.eof())
        
        return dev_recs
        
class device_mgr(object):
    # This class encapsulates the management of the devices and may be driven
    # by the 
    #   1. command line (in which case the IPL ELF must be consistent or device
    #      independent)
    #   2. the IPL ELF (in which case a device dependent IPL ELF is required)
    # This class is where the command line, IPL ELF and media module converge
    # and interact
    handlers={}  # Maps media device class to media handler name
    @staticmethod
    def command_line(option):
        if option is None:
            return None
        if option=="CDROM":
            return cdrom_mgr()
        try:
            mdcls=media.dtypes[option]
            dtype=option
        except (KeyError, ValueError):
            print("iplmed.py: error: unrecognized device: '%s'" % option)
            sys.exit(1) 
        mh=device_mgr.handlers[mdcls.__name__]
        hndlr=media.device.handlers[mh]
        mod=hndlr.model(option)
        device=mod[0]
        model=mod[1] 
        if (hndlr.dclass=="CKD") and (device>=0x3380):
            dcls="ECKD"
        else:  
            dcls=hndlr.dclass
        devclso=device_class.classes[dcls]
        return device_mgr(device,model,dcls,devclso,option)
    @staticmethod
    def init():
        device_mgr.handlers["fba"]="fba"
        device_mgr.handlers["awstape"]="tape"
        device_mgr.handlers["ckd"]="ckd"
        device_mgr.handlers["punch"]="punch"
    @staticmethod
    def iplelf(device,model):
        if (device==0) and (model==0):
            # Must be a CDROM
            return cdrom_mgr()
        try:
            dtype=media.dtypes.number(device,model)
        except ValueError:
            print("iplmed.py: error: IPL ELF device model invalid: %04X-%X" \
                % (device,model))
            sys.exit(1)
        hndlr=media.dtypes(dtype)
        if (hndlr.dclass=="CKD") and (device>=0x3380):
            dcls="ECKD"
        else:  
            dcls=hndlr.dclass
        devclso=device_class.classes[dcls]
        return device_mgr(device,model,dcls,devclso,dtype)
    def __init__(self,device,model,dclass,devclso,dtype):
        self.dev=device       # hex device type (for example: 0x3380)
        self.model=model      # hex device model number (for example: 0x01)
        self.dclass=dclass    # IPLMED device class
        self.devclso=devclso  # IPLMED device class instance
        self.mtype=dtype      # media.py device type string
        self.med_device=None  # media.py device instance created by device method
        self.med_file=None    # media.py device path name
        # Values supplied by the options method
        self.trunc=False      # Should the device size be minimized or not
        self.compress=False   # If minimizing, should the device be compressable
    def __eq__(self,other):
        return self.devclso==other.devclso
    def __str__(self):
        return "%s %04X-%X (%s)" \
             % (self.dclass,self.dev,self.model,self.mtype)
    def create(self,debug=False):
        self.med_device.create(self.med_file,minimize=self.trunc,\
            comp=self.compress,progress=debug,debug=debug)        
    def device(self,filename,debug=False):
        self.med_device=media.device(self.mtype)
        self.med_file=filename
        if debug:
            print("iplmed.py: debug: media device: %s" % self.med_device)
            print("iplmed.py: debug: file name: %s" % self.med_file)
    def options(self,trunc=False,compress=False):
        self.trunc=trunc
        self.compress=compress
    def queue(self,iplrecs=[]):
        # Queues device records for output
        for x in iplrecs:
            self.med_device.record(x)
    def records(self,iplrecs=[],vol=None,arch=None,ioarch=None,noboot=False,\
                debug=False):
        # This method calls the appropriate device_class instance to convert
        # the iplmed.record instances into recsutil.rec instances (or 
        # cdrom_record instances).
        recs=self.devclso.records(\
            self,iplrecs=iplrecs,vol=vol,arch=arch,ioarch=ioarch,noboot=noboot,\
                dmgr=self,debug=debug)
        if debug:
            print("iplmed.py: debug: device_mgr.records: processing %s iplrecs" \
                % len(recs))
        return recs

    def volsup(self):
        # This method is called to determine whether the device supports a
        # repository.
        return self.devclso.volsup()
        
device_mgr.init()

class cdrom_mgr(device_mgr):
    # This class provides CDROM device manager support by overrideing methods
    # as require.
    def __init__(self):
        device_mgr.__init__(self,0,0,"CDROM",device_class.classes["CDROM"],None)
        self.mtype="CDROM"
    def __str__(self):
        return "CDROM"
    def create(self,debug=False):
        # Create the files associated with the CDROM list directed load
        fil=os.path.basename(self.med_file)
        (fil,ext)=os.path.splitext(fil)
        filepfx=fil
        cdrom_content=""
        ok=True
        for x in self.med_recs:
            cdrom_content="%s%s" % (cdrom_content,x.listload(filepfx))
            ok&=x.write(self.med_dir,filepfx,debug=debug)
        fl=self.med_file
        if debug:
            lines=cdrom_content.split("\n")
            string="iplmed.py: debug: CDROM list directed IPL data: %s" \
                % fl
            for x in lines:
                if len(x)!=0:
                    string="%s\n    %s" % (string,x)
            print(string) 
        try:
            if debug:
                print("iplmed.py: debug: writing file: %s" % fl)
            fo=open(fl,mode="wb")
            fo.write(cdrom_content)
            fo.close()
        except IOError:
            print("iplmed.py: error: could not write CDROM file: %s" % fl)
            ok=False
        if not ok:
            sys.exit(1)
    def device(self,filename,debug=False):
        self.med_device=None
        self.med_file=filename
        self.med_dir=os.path.dirname(self.med_file)
        if debug:
            print("iplmed.py: debug: media device: %s" % self.med_device)
            print("iplmed.py: debug: CDROM file name: %s" % self.med_file)
    def queue(self,iplrecs=[]):
        print("iplmed.py: debug: cdrom_mgr.queue: queueing %s IPL records" \
            % len(iplrecs))
        self.med_recs=iplrecs
        
class cdrom_record(object):
    filenames={}
    @staticmethod
    def init():
        cdrom_record.filenames[ipl]="IPLPSW"
        cdrom_record.filenames[lowc]="PREFIX"
        cdrom_record.filenames[loader]="INIT"
        cdrom_record.filenames[text]="PROGRM"
        cdrom_record.filenames[elf]="PROGRM"
        cdrom_record.filenames[ccw]=None
    def __init__(self,iplrec):
        self.filename=None
        self.load=iplrec.seg.p_vaddr
        self.data=iplrec.content()
        self.filename=cdrom_record.filenames[iplrec.__class__]
        # Handle special cases
        if isinstance(iplrec,ipl):
            self.data=self.data[:8]  # Just need the PSW from the IPL segment
        if isinstance(iplrec,lowc):
            self.load=0
    def dump(self):
        return "CDROM record %s\n%s" \
            % (self.filename,\
                hexdump.dump(self.data,start=self.load,indent="   "))
    def listload(self,pfx):
        return "%s 0x%08X\n" % (self.pathname(pfx),self.load)
    def pathname(self,pfx):
        return "%s.%s" % (pfx,self.filename)
    def write(self,directory,pfx,debug=False):
        fl=os.path.join(directory,self.pathname(pfx))
        try:
            if debug:
                print("iplmed.py: debug: writing file: %s" % fl)
            fo=open(fl,mode="wb")
            fo.write(self.data)
            fo.close()
        except IOError:
            print("iplmed.py: error: could not write CDROM file: %s" % fl)
            return False
        return True

class iplelf(object):
    #ioarchs={0x24:0x04,0x31:0x02,0x64:0x02}
    #iostrings={0x04:"channel",0x02:"subchannel"}    
    @staticmethod
    def extract(pyelf):
        # Extract into a list each program segment
        segments=[]
        bits64=pyelf.is64()
        for seg in pyelf.PgmTbl.entries:
            if seg.typ!=1: # Only process PT_LOAD segments
                print("iplmed.py: warning: segment ignored: p_type=%s" % seg.typ)
                continue
            #def __init__(self,pvaddr,paddr,pflags,offset,content,bit64=False):
            sego=segment(\
                seg.virt_addr,\
                seg.phys_addr,\
                seg.flags,\
                seg.offset,\
                seg.fetch(),\
                bit64=bits64,
                entry=pyelf.getEntry())
            if sego.name=="?":
                print("iplmed.py: warning: unrecognized segment ignored: %s" \
                    % sego)
                continue
            segments.append(sego)
        return segments
    # Keyword arguments:
    #   devmgr = iplmed.device_mgr instance
    #   extlodr= PyELF instance of external loader ELF
    #   lodr=    if False, ignore any embedded or external loader present
    #   lowcore= if True, ignore any LOWC segment preset, default or embedded
    #   bootelf= if True, force loader to load the entire ELF
    #   archso=  archs instance for the build
    #   debug=   If True output debug information
    def __init__(self,pyelf,devmgr=None,extlodr=None,lodr=True,lowcore=True,\
                 bootelf=False,vol=False,archso=None,debug=False):
        if debug:
            print("iplmed.py: iplelf(pyelf=%s,"    % pyelf)
            print("                  devmgr=%s,"   % devmgr)
            print("                  extlodr=%s,"  % extlodr)
            print("                  lodr=%s,"     % lodr)
            print("                  lowcore=%s,"  % lowcore)
            print("                  bootelf=%s,"  % bootelf)
            print("                  vol=%s,"      % vol)
            print("                  archso=%s,"   % archso)
            print("                  debug=%s)"    % debug)
        self.elf=pyelf                # PyELF instance
        self.exe=pyelf.fil            # String of the entire ELF file
        self.devmgr=devmgr            # device_mgr instance (command line or ELF)
        self.segments=iplelf.extract(pyelf)  # List of program segment instances
        self.extloader=None           # External loader segment if present
        self.archs=archso             # Save archs for additional info
        self.arch=None                # Determine required program architecture
        self.ioarch=None              # Determine required I/O architecture
        
        # Determine bootstrap program's required architecture
        self.archs.set_elf_arch(self.elf)
        if debug:
            self.archs.hierarchy()
        # Active program arch as LOADER bits
        self.arch=self.archs.to_loader_arch(self.archs.get_arch_mode())
        # Active I/O as LOADER I/F Bits
        self.ioarch=self.archs.to_loader_io(self.archs.get_io_mode())

        # Dictionary of recognized segments initialized to None
        self.segnames={"IPL":None,"CCW":None,"TEXT":None,"LODR":None,\
                       "LOWC":None,"ELF":None}
        for x in self.segments:
            self.segnames[x.name]=x 
            print("iplmed.py: segment: %s" % x)
        if self.segnames["TEXT"] is None:
            print("iplmed.py: error: IPL ELF required TEXT segment missing")
            sys.exit(1)
        self.elfseg()   # Make the entire ELF a "segment"
        print("iplmed.py: exe:     %s" % self.segnames["ELF"])
        
        # Process the external loader ELF
        if extlodr is not None:
            ext_segments=iplelf.extract(extlodr)
            for x in ext_segments:
                if x.name!="LODR":
                    continue
                self.extloader=x
                print("iplelf.py: external:%s" % self.extloader)
                break
            if self.extloader is None:
                print("iplelf.py: error: external loader does not contain " \
                    "LOADER segment")
                sys.exit(1)

        # Create IPL records
        #                       LODR      addi
        #                       ELF       tion
        #             IPL  CCW  TEXT LOWC al
        self.iplrecs=[None,None,None,None,None]
        # These 5 segment instances drive the IPL medium creation.  They are
        # adjusted below to address the model being implemented.
        
        self.IPL=None
        self.CCW=None
        self.PGM=None
        self.LOWC=None
        self.additional=None
        
        # Create the IPL segment
        self.IPL=ipl(self.segnames["IPL"],self.elf,self.devmgr,bootelf=bootelf,\
                     archso=self.archs,debug=debug)
        if self.devmgr is None:
            self.devmgr=self.IPL.dmgr
        else:
            if self.devmgr!=self.IPL.dmgr:
                print("iplmed.py: error: command line device, %s, and IPL ELF "
                    "device are inconsistent: %s" \
                    % (self.devmgr.mtype,self.IPL.devmgr.mtype))
                sys.exit(1)
        
        # Create the LODR segment. May be suppressed or supplied externally
        # Suppression overrides the externally supplied loader.  An externally
        # supplied loader overrides an embedded loader.  Need to add logic for
        # external loader.
        ldr=self.segnames["LODR"]
        if self.extloader is not None:
            if ldr is not None:
                print("iplmed.py: warning: embedded loader replaced by external " \
                    "loader")
            ldr=self.extloader
        
        # Create the LOWC segment. May be suppressed by the command line
        if lowcore:
            # Note: the vol argument is no longer needed 1024 byte LOWC is
            # always created now because of the IPL program address info.
            self.LOWC=lowc(self.segnames["LOWC"],self.elf,True,debug=debug)
        else:
            print("iplmed.py: warning: LOWC segment suppressed")
        
        # Create the TEXT, ELF or LOADER segment being loaded by the IPL function
        if self.IPL.text_load:
            self.PGM=text(self.segnames["TEXT"])
        else:
            self.PGM=elf(self.segnames["ELF"])
        lowc_program=self.PGM
        if ldr is not None:
            # A LODR segment is present
            if lodr:
                # the --nolodr argument was not provided (use the loader, then)
                if bootelf:
                    # --bootelf argument forces the whole elf regardless of the
                    # special section name used for the IPL section.
                    self.additional=elf(self.segnames["ELF"])
                else:
                    self.additional=self.PGM
                lowc_program=self.additional

                self.PGM=loader(ldr,self.elf,archso=self.archs,debug=debug)

                # Overide the IPL PSW with that provided by the loader
                self.IPL.iplpsw=self.PGM.iplpsw(debug=debug)
                print("iplmed.py: booting: %s" % self.additional)
            else:
                # Command line suppressed LODR segment
                print("iplmed.py: warning: LOADER segment suppressed")
        
        self.CCW=ccw(self.segnames["CCW"],self.elf,self.IPL.device_cls,\
            self.IPL,self.PGM,self.LOWC,debug=debug)
        # Set the IPL records
        self.iplrecs[self.IPL.rec]=self.IPL
        self.iplrecs[self.PGM.rec]=self.PGM
        if self.LOWC is not None:
            self.LOWC.pgmload(lowc_program,debug=debug)
            self.iplrecs[self.LOWC.rec]=self.LOWC
            
        self.iplrecs[self.CCW.rec]=self.CCW
        self.iplrecs[4]=self.additional
        
        if debug:
            for x in range(len(self.iplrecs)):
                if (x == 4) and (self.iplrecs[4] is None):
                    print("iplmed.py: debug: Additional : None")
                else:
                    print("iplmed.py: debug: %s" % self.iplrecs[x])
                        
    def elfseg(self):
        # Figure out the IPL ELF load address from the TEXT segment
        text=self.segnames["TEXT"]
        elfaddr=text.p_vaddr-text.p_offset
        # Create a segment instance for the ELF
        seg=segment(elfaddr,elfaddr,None,0,self.exe,\
             bit64=self.elf.is64(),entry=self.elf.getEntry())
        # Add the pseudo segment to the dictionary of segments and segment list
        self.segments.append(seg)
        self.segnames[seg.name]=seg
    def records(self):
        # returns the list of targeted IPL records
        return self.iplrecs
    def target(self):
        # returns the identified target device
        return self.devmgr

class IPLMED(object):
    def __init__(self,opts,debug=False):
        device_class.init()
        self.options=opts
        self.debug=debug or self.options.debug  # Turn on debugging, if requested

        if self.debug:
            print("iplmed.py: debug: command line:")
            for x in range(len(sys.argv)):
                print("     %s" % sys.argv[x])

        self.exefile=self.options.exefile[0]  # IPL ELF exe file name
        
        # IPL architecture management
        self.archs=archs(debug=self.debug)  # Create defaults
        self.archs.set_cli_arch(self.options.arch,self.options.s370bc)
        self.archs.set_cli_io(self.options.ioarch)
        if self.debug:
            self.archs.hierarchy()
        
        # Repository related variables
        self.vol=None               # Volume instance if requested and supported
        self.spec=None              # Path to DASD Volume specification file
        #self.repoload=self.options.repoload  # Repository loading start address
        #self.repostmts=[]          # List of specstmt instances
        
        # I/O and device type management
        self.medium=self.options.medium       # emulated device file name
        # Note: self.options.device contains the device type string
        self.dmgr=device_mgr.command_line(self.options.device)
        self.reqdevdep=False       # Device dependent IPL ELF required or not
        #self.ioarch=None           # Required bootstrap I/O architecture support
        if (self.dmgr is None): 
            self.reqdevdep=True   # Need a device dependent IPL ELF then
            # the iplelf instance must set self.dtype, self.device, self.model
            # and self.devclso
        # Command line device arguments processed.  self.devclso is either None
        # or is an instance of device_class.
        
        try:
            self.elf=PyELF.elf(PyELF.elf_source(filename=self.exefile))
            print("iplmed.py: program ELF: %s" % self.exefile)
        except TypeError:
            print("iplmed.py: error: not an ELF or invalid: %s" % self.exefile)
            sys.exit(1)
        if self.debug:
            self.elf.prt(details=True)
        if not self.elf.isexec():
            print("iplmed.py: error: not an executable: %s" % self.exefile)
            sys.exit(1)
        
        # Process --external option
        self.external=None
        if self.options.external is not None:
            external=self.options.external
            try:
                self.external=PyELF.elf(PyELF.elf_source(filename=external))
                print("iplmed.py: loader ELF: %s" % external)
            except TypeError:
                print("iplmed.py: error: ignoring external loader, invalid or" \
                    "not an ELF: %s" \
                    % self.external)
                sys.exit(1)

        # Process the IPL ELF and provide it with command line device options
        self.iplelf=iplelf(self.elf,\
            devmgr=self.dmgr,\
            lodr=self.options.nolodr,\
            lowcore=self.options.nolowc,\
            extlodr=self.external,\
            bootelf=self.options.bootelf,\
            vol=self.options.volume!=None,
            archso=self.archs,\
            debug=self.debug)
        # The iplelf instance has the real device manager.  It could be mine or
        # built its own.  I need to access the real one.
        self.dmgr=self.iplelf.target()
        # Set the device build options from the command line
        self.dmgr.options(trunc=self.options.trunc,\
            compress=self.options.compressable)

        # Process the --vol option
        if self.options.volume is not None:
            isVolumeSupported=self.iplelf.devmgr.volsup()
            if self.debug:
                print("volume.py: debug: DASD Volume support: %s" \
                    % isVolumeSupported)
            if not isVolumeSupported:
                print("iplmed.py: error: DASD Volume may not be specified for "
                    "device")
                sys.exit(1)
            self.spec=self.options.volume

        if self.debug:
            print("iplmed.py: debug: targeted device: %s" \
                % self.iplelf.target())
    def generate(self,debug=False):
        self.debug=(debug or self.options.debug)
        # Extract the target device class (it knows how to put the IPL records
        # on the device).  Retrieve the records being written to the device.
        if self.debug:
            print("iplmed.py: debug: GENERATING IPL MEDIUM")
            print("iplmed.py: debug: IPLMED.generate: device manager: %s" \
                % self.dmgr)
        self.dmgr.device(self.medium,self.debug)
        self.device_records=self.dmgr.records(\
            iplrecs=self.iplelf.records(),\
            vol=self.spec,\
            arch=self.iplelf.arch,\
            ioarch=self.iplelf.ioarch,\
            noboot=self.options.noboot,\
            debug=self.debug)
        if self.debug:
            for x in self.device_records:
                print("iplmed.py: debug: %s" % x.dump())
        self.dmgr.queue(self.device_records)
        # Create the IPL medium
        self.dmgr.create(debug=self.debug)
        
        print("iplmed.py: %s IPL device created: %s" \
            % (self.dmgr.mtype,self.dmgr.med_file))

class record(object):
    recno={"IPL":0,"CCW":1,"ELF":2,"LODR":2,"TEXT":2,"LOWC":3}
    def __init__(self,seg):
        self.name=seg.name
        self.seg=seg
        self.rec=record.recno[self.name]
        self.devloc=None         # Assigned device location
    def __str__(self):
        return "IPL %s %-05s: %s" % (self.rec,self.__class__.__name__,self.seg)
    def content(self,*args,**kwds):
        # Returns a string that is the records content as raw binary data
        raise NotImplementedError("iplmel.py: internal: subclass must provide "\
            "content method: %s" \
            % (self.__class__.__name__))
        
class ccw(record):
    def __init__(self,sego,elf,devclso,iplsego,pgmsego,lowcsego,debug=False):
        if sego is None:
            # There is no CCW segment in the IPL ELF, 
            # so create the default content
            seg=self.dftccw(elf,devclso,iplsego,pgmsego,lowcsego,debug=debug)
            if debug:
                print("iplmed.py: debug: generated segment: %s" % seg) 
        else:
            seg=sego
        record.__init__(self,seg)
    def content(self):
        return self.seg.content
    def dftccw(self,elf,devcls,iplo,pgmo,lowco,debug=False):
        if debug:
            print("iplmed.py: ccw.dftccw(elf=%s," % elf)
            print("                      devcls=%s," % devcls)
            print("                      iplo=%s," % iplo)
            print("                      pgmo=%s," % pgmo)
            print("                      lowco=%s," % lowco)
            print("                      debug=%s)" % debug)
                
        # ccw segment placed following program segment
        pgmend=pgmo.seg.p_vaddr+len(pgmo.seg.content)
        # ccws must be doubleword aligned
        ccwbeg=align(pgmend,8)
        ccwbeg_before=ccwbeg
        if debug:
            print("iplmed.py: debug: CCW chain continues at: %06X" % ccwbeg)
        ccwbeg=devcls.ccwbeg(ccwbeg)
        if debug and (ccwbeg!=ccwbeg_before):
            print("iplmen.py: debug: CCW chain adjusted by device to continue"\
                " at: %06X" % ccwbeg)
        # Call the device class to build CCW chain
        # FBA requires IPL PSW for lowc because it can not data chain within
        # a physical sector.
        ccws=devcls.ccwseg(ccwbeg,pgmo,lowc=lowco,iplpsw=iplo.iplpsw,debug=debug)
        if iplo.iplccw1 is None:
            iplo.iplccw1=devcls.iplccw1(ccwbeg,len(ccws))
        if iplo.iplccw2 is None:
            iplo.iplccw2=devcls.iplccw2(ccwbeg)
        if lowco!=None:
            lowco.iplccws(iplo.iplpsw,iplo.iplccw1,iplo.iplccw2)
        if debug:
            print("iplmed.py: debug: IPL CCW1  %s" \
                    % dblwordX(dblword(iplo.iplccw1)))
            print("iplmed.py: debug: IPL CCW2  %s" \
                    % dblwordX(dblword(iplo.iplccw2)))
        if debug:
            print("iplmed.py: debug: CCW segment content:")
            print(dump(ccws,start=ccwbeg,indent="   "))
        return segment(ccwbeg,ccwbeg,0x20000000,0,ccws,bit64=elf.is64())

class elf(record):
    # This subclass accepts a PyELF segment instance and creates an logical IPL
    # record for it.
    def __init__(self,seg):
        record.__init__(self,seg)
        self.entry=self.seg.elfentry
    def content(self):
        return self.seg.content
        
class ipl(record):
    strfmt=">8s8s8sHBB"
    iplsize=28
    def __init__(self,sego,elf,devmgr,bootelf=False,archso=None,debug=False):
        if debug:
            print("iplmed.py: ipl(sego=%s,"     % sego)
            print("               elf=%s,"      % elf)
            print("               devmgr=%s,"   % devmgr)
            print("               bootelf=%s,"  % bootelf)
            print("               archso=%s,"   % archso)
            print("               debug=%s)"    % debug)
            archso.hierarchy()

        self.archs=archso

        fmtlen=struct.calcsize(ipl.strfmt)
        if fmtlen!=ipl.iplsize:
            raise ValueError(\
                "iplmed.py: internal: ipl struct format not 28 bytes: %s" %
                fmtlen)
        if sego is None:
            # There is no IPL segment in the IPL ELF, 
            # so create the default content

            seg=self.dftipl(elf,bootelf,debug=debug)
            if debug:
                print("iplmed.py: debug: generated segment: %s" % seg) 
        else:
            seg=sego
        record.__init__(self,seg)
        # Indicates whether the TEXT or ELF is being loaded (default is ELF)
        # The actual load location is determined by the segment p_vaddr value.
        self.text_load=(seg.p_flags&0x08000000)!=0
        self.devtype=None
        self.devmodel=None
        self.devcls=None
        self.classes=[]        # Supported device_class instances
        self.device_cls=None   # This is the class of the actual target device
        self.dmgr=None         # Device manager selected below
        # Used for physical IPL record 0 construction
        # Note: If a loader is used, the IPL PSW specified by the IPL segment or
        #       generated from the IPL program ELF below in the dftipl method
        #       will be overriden.
        self.iplpsw=None
        self.iplccw1=None
        self.iplccw2=None
        # Interpret IPL segment content
        data=self.seg.content
        if len(data)!=8 and (len(data)!=ipl.iplsize):
            print("iplmed.py: error: IPL segment length must be 8 or 28: %s" \
                % len(data))
            sys.exit(1)
        if len(data)==8:
            # This is a device independent IPL ELF
            self.iplpsw=data
            # Device independent IPL EFL encountered.
            # Use command line device information, if provided, error otherwise
            if devmgr is None:
                print("iplmed.py: error: device independent IPL ELF requires "
                    "--device argument, "\
                    "could not identify target device")
                sys.exit(1)
            self.classes=[devmgr.dclass]
            self.device_cls=devmgr.devclso
            self.dmgr=devmgr
            if debug:
                print("iplmed.py: debug: IPL PSW   %s" \
                    % dblwordX(dblword(self.iplpsw)))
                print("iplmed.py: debug: command line device being used")
        else:
            ipldata=struct.unpack(ipl.strfmt,data)
            self.iplpsw=ipldata[0]
            self.iplccw1=ipldata[1]
            self.iplccw2=ipldata[2]
            self.devtype=ipldata[3]
            self.devmodel=ipldata[4]
            self.devcls=ipldata[5]
            self.classes=device_class.enabled(self.devcls)
            if debug:
                print("iplmed.py: debug: IPL PSW   %s" \
                    % dblwordX(dblword(self.iplpsw)))
                print("iplmed.py: debug: IPL CCW1  %s" \
                    % dblwordX(dblword(self.iplccw1)))
                print("iplmed.py: debug: IPL CCW2  %s" \
                    % dblwordX(dblword(self.iplccw2)))
                print("iplmed.py: debug: dev type  %s" % halfwordX(self.devtype))
                print("iplmed.py: debug: dev model %s" % byteX(self.devmodel))
                print("iplmed.py: debug: dev class %s" % byteX(self.devcls))
                for x in self.classes:
                    print("iplmed.py: debug: enabled device class: %s" % x.name)
            # These checks validate that device dependent data is internally 
            # consistent within the IPL segment
            for x in self.classes:
                # If command line selected CDROM and CDROM is enabled use CDROM
                if (x.__class__==CDROM) and (devmgr.devclso.__class__==CDROM):
                    self.dmgr=devmgr
                    break
            if self.dmgr is None:
                # Still None, so not using CDROM.  Use media module for devices
                # We will not come back if the IPL segment contains an invalid
                # device type or model
                self.dmgr=device_mgr.iplelf(self.devtype,self.devmodel)
            for x in self.classes:
                if x==self.dmgr.devclso:
                    self.device_cls=x
                    break
        if self.device_cls is None:
            print("iplmed.py: error: Neither command nor IPL segment "
                "specifies device")
            sys.exit(1)
    def content(self):
        data=self.iplpsw+self.iplccw1+self.iplccw2
        if len(data)!=24:
            raise ValueError(\
                "iplmed.py: internal: ipl record content not 24 bytes: %s" \
                % len(data))
        return data
    def dftipl(self,elf,bootelf,debug=False):
        # Generate a IPL segment as if it was present in the IPL ELF
        self.archs.compatible("active","IPL ELF",debug=debug)
        
        b64=elf.is64()
        
        # This selects between the ELF loading into ELF1 storage area (32-bit ELF)
        # or ELF2 storage area (64-bit ELF)
        if bootelf:
            text=0x00000000
        else:
            text=0x08000000
        if b64:
            p_flag=0x15000000|text
        else:
            p_flag=0x14000000|text
        if self.archs.get_ipl_bcmode():
            sysmask=0x0000
        else:
            sysmask=0x0008
        if debug:
            print("iplmed.py: debug: Generated IPL PSW for IPL ELF:")
        ipl_mode=self.archs.to_segment_arch(self.archs.get_ipl_mode())
        elf_psw=psw(sysmsk=sysmask,addr=elf.getEntry(),\
                    mode=ipl_mode,debug=debug)
        return segment(0,0,p_flag,0,elf_psw,bit64=b64)
        
class loader(record):
    header=32        # Size of the iplmed.py loader interface data
    loader_info=16   # Size of the loader provided interface data
    loader_resv=9    # Loader provided interface data reserved start pos.
    def __init__(self,sego,elf,archso=None,debug=False):
        if debug:
            print("iplmed.py: loader(sego=%s,"   % sego)
            print("                  elf=%s,"    % elf)
            print("                  archso=%s," % archso)
            print("                  debug=%s)"  % debug)
        record.__init__(self,sego)
        
        self.archs=archso
        if debug:
            self.archs.hierarchy()
        # Extract loader capability from the loader header
        self.pgm=None
        self.lowc=None
        self.parse(self.content(),debug=debug)
        # I need to be entered following the loader interface data
        # This value is used for creating my IPL PSW in the iplpsw method
        self.entry=self.seg.p_vaddr+loader.header
    def check_device(self,dev_flag):
        # Returns True is device is supported, False otherwise
        return 0 != (self.pgm.devices & dev_flag)
    def content(self):
        return self.seg.content       # Exclude the first two bytes
    def iplpsw(self,s370=False,debug=False):
        self.archs.compatible("active","LOADER",debug=debug)
        if debug:
            print("iplmed.py: debug: Generated IPL PSW for boot loader:")
        ipl_mode=self.archs.to_segment_arch(self.archs.get_ipl_mode())
        if ipl_mode==24:
            if self.archs.get_ipl_bcmode():
                return psw(sysmsk=0x0000,addr=self.entry,mode=24,debug=debug)
            else:
                return psw(sysmsk=0x0008,addr=self.entry,mode=24,debug=debug)
        return psw(addr=self.entry,mode=31,debug=debug)
    def length(self):
        # Returns the length of the loader in bytes
        return len(self.content())
    def parse(self,content,debug=False):
        # This method interprets the iplmed.py loader interface data supplied
        # by the loader segment.
        if len(content)<loader.header:
            print("iplmed.py: error: loader interface information incomplete " \
                "or missing, size: %s" % len(content))
            sys.exit(1)
        self.cap=content[0:loader.loader_info]
        print("iplmed.py: LOADER segment loader interface data:\n%s" \
            % dump(self.cap,indent="    "))
        prep_data=content[loader.loader_info:loader.header]
        error=False
        if self.cap[loader.loader_resv:]\
           !=(loader.loader_info-loader.loader_resv)*"\x00":
            print("iplmed.py: error: loader's reserved interface data not " \
                "binary zeros:\n%s" % dump(self.cap,indent="    "))
            error=True
        if prep_data!=((loader.header-loader.loader_info)*"\x00"):
            print("iplmed.py: error: medium preparation interface data not " \
                "binary zeros:\n%s" % dump(prep_data,indent="    "))
            error=True

        recsize=halfword(self.cap[0:2])
        pgm_cap=self.cap[2]
        lowc_cap=self.cap[3]
        eof_cap=self.cap[4]
        pad_cap=self.cap[5]
        pgm_loc=self.cap[6]
        boot_dev=ord(self.cap[7])   # All bit combinations valid
        arch_cap=ord(self.cap[8])
        if pgm_cap not in "SDN":
            print("iplmed.py: error: loader program capability invalid: 0x%02X" \
                % ord(pgm_cap))
            error=True
        if lowc_cap not in "SDN":
            print("iplmed.py: error: loader lowc capability invalid: 0x%02X" \
                % ord(lowc_cap))
            error=True
        if eof_cap not in "HP":
            print("iplmed.py: error: loader EOF capability invalid: 0x%02X" \
                % ord(eof_cap))
            error=True
        if pad_cap not in "YN":
            print("iplmed.py: error: loader block pad capability invalid: 0x%02X" \
                % ord(pad_cap))
            error=True
        if pgm_loc not in "YN":
            print("iplmed.py: error: loader program location update invalid: 0x%02X" \
                % ord(pgm_loc))
            error=True
        if (arch_cap & 0x1F) != 0:
             print("iplmed.py: error: loader arch support reserved bits " \
                 "not zero: 0x%02X" \
                % arch_cap)
             error=True   
        if error:
            print("iplmed.py: error: loader interface data in error")
            sys.exit(1)
        self.pgm=loader_cap(pgm_cap,eof_cap,recsize,pad_cap,pgm_loc,boot_dev,\
            arch_cap)
        self.lowc=loader_cap(lowc_cap,eof_cap,recsize,pad_cap,pgm_loc,boot_dev,\
            arch_cap)
        
        # Update archs manager with loader's capabilities and select loader
        # archs.
        self.archs.set_loader_arch(arch_cap)
        self.archs.set_loader_io(boot_dev)
        self.archs.compatible("LOADER","IPL ELF",debug=debug)

        if debug:
            print("iplmed.py: debug: loader capability program: %s" % self.pgm)
            print("iplmed.py: debug: loader capability    lowc: %s" % self.lowc)
            self.archs.hierarchy()
    def records(self,devcls,program=None,lowc=None,start=None,debug=False):
        # This method generates the content loaded by the bootstrap loader
        # based upon its capabilities.  It gets assistance from the device_class
        dev_recs=[]
        pgm_dir_eof=(lowc is None) and (self.pgm.directed_eof)
        if program is not None:
            if self.pgm.supported:
                # Build ELF dataset
                recs=devcls.dataset(\
                    program,
                    self.pgm.size,
                    pad=self.pgm.pad,
                    directed=self.pgm.directed,
                    eof=pgm_dir_eof,
                    start=start,
                    debug=debug)
                dev_recs.extend(recs)
            else:
                print("iplmed.py: error: program not supported by loader")
                sys.exit(1)
        
        # IPL Rec 3 - lowc segment - need to use directed records
        if lowc is not None:
            if self.lowc.supported:
                # Build lowc dataset
                recs=devcls.dataset(\
                    lowc,
                    self.lowc.size,
                    pad=self.lowc.pad,
                    directed=self.lowc.directed,
                    eof=self.lowc.directed_eof,
                    debug=debug)
                dev_recs.extend(recs)
            else:
                print("iplmed.py: warning: lowc not supported by loader")
            
        if self.lowc.physical_eof:
            eof=devcls.eof()
            if eof is not None:
                dev_recs.append(eof)
        return dev_recs
    def update(self,data=""):
        # Prepare supplied data for insertion into the loader segment
        prep_size=loader.header-loader.loader_info
        pad=prep_size*"\x00"
        prep_data=data+pad
        prep_data=prep_data[:prep_size]
        if ord(prep_data[-2])==0:
            raise NotImplementedError("iplmed.py: internal: Loader interface "\
                "data does not contain required architecture support data")
        if ord(prep_data[-1])==0:
            raise NotImplementedError("iplmed.py: internal: Loader interface "\
                "data does not contain required device support data")
        print("iplmed.py: Loader interface data provided to LOADER segment:\n%s" \
            % dump(prep_data,start=loader.loader_info,indent="    "))
        # Perform the update to the loader segment
        ldr_content=self.content()
        content_len=len(ldr_content)
        preamble=ldr_content[:loader.loader_info]
        remainder=ldr_content[loader.header:]
        new_content=preamble+prep_data+remainder
        if len(new_content)!=content_len:
            raise ValueError("iplmed.py: internal: updated loader differs in "\
                "size, expected %s: %s" \
                % (content_len,len(new_content)))
        self.seg.content=new_content

class loader_cap(object):
    arch_masks={0x24:0x80,
                0x31:0x40,
                0x64:0x20}
    # This class assists the loader in managing its capabilities
    def __init__(self,cap,eof,size,pad,loc,dev,arch):
        self.recsize=size
        self.cap=cap
        self.eof=eof
        self.pad_block=pad
        self.pgm_loc=loc
        self.dev=dev
        self.arch=arch
    def __str__(self):
        return "supported=%s, size=%s, pad=%s, format=%s, EOF=%s, pgm=%s " \
             "devices=%02X, arch=%02X, ioarch=%02X" \
             % (self.supported,self.recsize,self.pad_block,self.cap,self.eof,\
                self.update,(self.dev & 0xF9),self.arch,(self.dev & 0x06))
    def test_arch(self,arch):
        # Returns true if supplied architecture is supported
        #print "mask=%02X, self.arch=%02X" % \
        #    (loader_cap.arch_masks[arch],self.arch)
        return (loader_cap.arch_masks[arch] & self.arch) != 0
    def test_io(self,io):
        if io==0:
            # Unspecified I/O architecture, assume correct match
            return True
        return ((self.dev & 0x06) & io)!=0
    @property
    def chanio(self):
        reutrn (self.dev & 0x04)!=0
    @property
    def devices(self):
        return self.dev
    @property
    def directed(self):
        return self.cap=="D"
    @property
    def directed_eof(self):
        return self.directed and (self.eof=="H")
    @property
    def pad(self):
        return self.pad_block=="Y"
    @property
    def physical_eof(self):
        return self.eof=="P" or (not self.directed)
    @property
    def schio(self):
        return (self.dev & 0x02)!=0
    @property
    def size(self):
        return self.recsize
    @property
    def stream(self):
        return self.cap=="S"
    @property
    def supported(self):
        return not self.cap=="N"
    @property
    def update(self):
        return self.pgm_loc=="Y"

class lowc(record):
    def __init__(self,sego,elf,vol,debug=False):
        if sego is None:
            # There is no LOWC segment in the IPL ELF, 
            # so create the default content
            seg=self.dftlowc(elf,vol,debug=debug)
            if debug:
                print("iplmed.py: debug: generated segment: %s" % seg) 
        else:
            seg=sego
        record.__init__(self,seg)
        self.entry=None
    def content(self):
        return self.seg.content
    def dftlowc(self,elf,vol,debug=False):
        zeros=8*b"\x00"
        pfx=zeros              # 0x0   restart new PSW
        pfx+=zeros             # 0x8   restart old PSW
        pfx+=zeros             # 0x10  
        pfx+=zeros             # 0x18  external old PSW
        pfx+=zeros             # 0x20  supervisor-call old PSW
        pfx+=zeros             # 0x28  program old PSW
        pfx+=zeros             # 0x30  machine-check old PSW
        pfx+=zeros             # 0x38  input-output old PSW
        pfx+=zeros             # 0x40 
        pfx+=zeros             # 0x48
        pfx+=zeros             # 0x50
        pfx+=dead(code=0x18)   # 0x58  external new PSW
        pfx+=dead(code=0x20)   # 0x60  supervisor-call new PSW
        pfx+=dead(code=0x28)   # 0x68  program new PSW
        pfx+=dead(code=0x30)   # 0x70  machine-check new PSW
        pfx+=dead(code=0x38)   # 0x78  input-output new PSW
        pfx+=128*b"\x00"       # 0x80-0xFF
        pfx+=32*b"\x00"        # 0x100-0x11F
        pfx+=zeros+zeros       # 0x120 restart old PSW
        pfx+=zeros+zeros       # 0x130 external old PSW
        pfx+=zeros+zeros       # 0x140 supervisor call old PSW
        pfx+=zeros+zeros       # 0x150 program old PSW
        pfx+=zeros+zeros       # 0x160 machine-check old PSW
        pfx+=zeros+zeros       # 0x170 input-output old PSW
        pfx+=zeros+zeros       # 0x180
        pfx+=zeros+zeros       # 0x190
        pfx+=deade(code=0x120) # 0x1A0 restart new PSW
        pfx+=deade(code=0x130) # 0x1B0 external new PSW
        pfx+=deade(code=0x140) # 0x1C0 supervisor-call new PSW
        pfx+=deade(code=0x150) # 0x1D0 program new PSW
        pfx+=deade(code=0x160) # 0x1E0 machine-check new PSW
        pfx+=deade(code=0x170) # 0x1F0 input-output new PSW
        if vol:
            pfx+=b"\x00" * 512
        if debug:
            print("iplmed.py: debug: LOWC segment content:")
            print(dump(pfx,indent="   "))
        return segment(0,0,0x30000000,0,pfx,bit64=elf.is64())
    def iplccws(self,iplpsw,iplccw1,iplccw2):
        if len(iplpsw)!=8:
            print("iplmed.py: internal: IPL PSW for low core not 8 bytes: %s" \
                % len(iplpsw))
        if len(iplccw1)!=8:
            print("iplmed.py: internal: IPL CCW1 for low core not 8 bytes: %s" \
                % len(iplccw1))
        if len(iplccw2)!=8:
            print("iplmed.py: internal: IPL CCW2 for low core not 8 bytes: %s" \
                % len(iplccw2)) 
        #nullquad=8*b"\x00"
        if self.overwrite(24):
            self.seg.content=iplpsw+iplccw1+iplccw2+self.seg.content[24:]
        else:
            if self.overwrite(16):
        
                self.seg.content=iplpsw+iplccw1+self.seg.content[16:]
            else:
                if self.overwrite(8):
                    self.seg.content=iplpsw+self.seg.content[8:]
                else:
                    print("iplmed.py: warning: could not update LOWC with IPL PSW")
    def iplpsw(self,psw):
        if len(psw)!=8:
            print("iplmed.py: internal: IPL PSW for low core not 8 bytes: %s" \
                % len(psw))
        if len(self.seg.content)<=8:
            self.seg.content=psw[:len(self.seg.content)]
        else:
            self.seg.content=psw+self.seg.content[8:]
    def overwrite(self,length=8):
        if len(self.seg.content)>=length:
            return self.seg.content[:length]==length*b"\x00"
        return False
        
    # Add the start and end address information (0x24C-0x253) to the LOWC segment
    # Input is an instance of record
    def pgmload(self,reco,debug=False):
        segment=reco.seg
        start=fullwordb(segment.p_vaddr)
        end=fullwordb(segment.segend)
        content=self.seg.content
        first_half=content[:0x24C]
        second_half=content[0x254:]
        new_content=first_half+start+end+second_half
        self.seg.content=new_content
        if debug:
            print("iplmed.py: debug: "
                "Updated LOWC at address 0x24C with program start: %s" \
                % fullwordf(segment.p_vaddr))
            print("iplmed.py: debug: "
                "Updated LOWC at address 0x250 with program end+1: %s" \
                % fullwordf(segment.segend))
        
    def vol(self, block=0, size=0):
        # This method supports use of LOWC segment for DASD Standard Volume 
        # information used with FBA devices.  The block number of the Volume 
        # Description Block is provided by the 'block' argument.  The DASD volume
        # block size of the Volume Descriptor block is provided by the size
        # argument.
        #
        # The block number is stored in bytes 256-259. 
        # the block size is stored in bytes 260-263.  
        # 
        # This method will extend the LOWC segment content if needed to accommodate 
        # this information or, if already large enough, set the specified values.
        vdbr_block_bin = fullwordb(block)
        vdbr_size_bin = fullwordb(size)
        vdbr_bin = vdbr_block_bin+vdbr_size_bin
        content = self.seg.content
        if len(content)<1024:
            content = content+1024*"\x00"
            content = content[:1024]
        first_half = content[:0x244]
        second_half = content[0x24C:]
        content = first_half + vdbr_bin + second_half
        self.seg.content = content
        
class text(record):
    def __init__(self,seg):
        record.__init__(self,seg)
        self.entry=self.seg.elfentry
    def content(self):
        return self.seg.content

class segment(object):
    names={0x00000000:"TEXT",
           0x10000000:"IPL",
           0x20000000:"CCW",
           0x30000000:"LOWC",
           0xF0000000:"LODR",
           None:"ELF"}
    def __init__(self,pvaddr,paddr,pflags,offset,content,bit64=False,entry=None):
        self.p_vaddr=pvaddr
        self.p_paddr=paddr
        self.p_flags=pflags
        self.p_offset=offset
        self.content=content
        self.bit64=bit64
        self.elfentry=entry
        self.segend=self.p_vaddr+len(content)
        if pflags is not None:
            flag=self.p_flags & 0xF0000000
        else:
            flag=None
        try:
            self.name=segment.names[flag]
        except KeyError:
            self.name="?" 
    def __str__(self):
        name="%-5s" % self.name
        if self.bit64:
            vaddr="0x%016X" % self.p_vaddr
            vend="0X%016X" % self.segend
        else:
            vaddr="0x%08X" % self.p_vaddr
            vend="0X%08X" % self.segend
        if self.p_flags is None:
            flag="None,"
        else:
            flag="0x%08X," % self.p_flags
        return "%s p_vaddr=%s, p_flags=%-11s p_offset=%s (0x%X)," \
            " size=%s (0x%X) end=%s" \
            % (name,vaddr,flag,self.p_offset,self.p_offset,\
            len(self.content),len(self.content),vend)

cdrom_record.init()

def parse_args():
    parser=argparse.ArgumentParser(\
        description="creates IPL media")
    parser.add_argument("exefile",\
        help="source ELF executable file",nargs=1)
    parser.add_argument("--arch",type=int,choices=[24,31,64],
        help="bootstrap program required architecture")
    parser.add_argument("--ioarch",choices=["chan","sch"],
        help="bootstrap required I/O architecture")
    parser.add_argument("--s370bc",action="store_true",default=False,\
        help="default IPL PSW uses S/370 basic control mode format")
    parser.add_argument("--medium",\
        help="targeted storage medium emulating file",required=True)
    parser.add_argument("--device",\
        help="targeted Hercules device type and model")
    parser.add_argument("--bootelf",action="store_true",default=False,\
        help="force loading of IPL ELF by loader")
    parser.add_argument("--debug",action="store_true",default=False,\
        help="enable debugging output")
    parser.add_argument("--external",default=None,\
        help="external loader ELF file")
    parser.add_argument("--noboot",action="store_true",default=False,\
        help="suppress boot program")
    parser.add_argument("--nolowc",action="store_false",default=True,\
        help="suppress explicit or default LOWC segment")
    parser.add_argument("--nolodr",action="store_false",default=True,\
        help="suppress LOADER segment if present")
    parser.add_argument("--trunc",action="store_true",default=False,\
        help="media truncated to minimal size")
    parser.add_argument("--compressable",action="store_true",default=False,\
        help="size media for compression")
    parser.add_argument("--volume",default=None,\
        help="path to DASD Volume Standard specification file")
    return parser.parse_args()   

if __name__=="__main__":
    med=IPLMED(parse_args())
    med.generate()