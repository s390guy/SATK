#!/usr/bin/python3
# Copyright (C) 2017 Harold Grovesteen
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

# This module creates Data Set Control Block records for use in an FBA DASD Volume 
# Table of Contents (VTOC).

this_module="fbadscb.py"

# Python imports:
import time                # Access to time structure

# SATK imports:
import ci                  # Access control interval manager
from structure import *    # Access big-endian structure manager


#
#  +---------------------------------------------------+
#  |                                                   |
#  |   Data Set Control Block Recognizer and Decoder   |
#  |                                                   | 
#  +---------------------------------------------------+
#

# Function Argument:
#   bin   a bytes/bytearray sequence of the unknown structure
# Exception:
#   ValueError if sequence not a recognized data set control block record
def from_bytes(bin,debug=False):
    return decode(bin,[DSCB1,DSCB0,DSCB4,VOL1])


#
#  +----------------------------------------------+
#  |                                              |
#  |   Data Set Control Block Common Structures   |
#  |                                              | 
#  +----------------------------------------------+
#

class Date(structure):
    length=3

    # Date Fields
    #       beg end len  typ
    yr=    (  0,  1,  1, "U")  # The year less 1900
    julian=(  1,  3,  2, "U")  # Julian date (1-366)

    @classmethod
    def from_bytes(cls,byts):
        return Date(bin=byts)

    def __init__(self,bin=None,year=None,julian=None):
        super().__init__(bin=bin,debug=False)

        if bin is not None:
            return

        if year is None and julian is None:
            yr,jul=self.getDate()
        else:
            cls_str=eloc(self,"__init__",module=this_module)
            assert year is not None,"%s 'yr' argument must not be None" % cls_str
            assert julian is not None,\
                "%s 'julian' argument must not be None" % cls_str
            yr=year
            jul=julian

        assert yr>=1900 and yr<=2155,"%s year out of range (1900-2155): %s"\
            % (cls_str,yr)
        assert jul>=1 and jul<=366,"%s Julian date out of range (1-366): %s"\
            % (cls_str,jul)

        self.insert("yr",yr-1900)
        self.yr=yr
        self.insert("julian",jul)
        self.julian=jul

    def __str__(self):
        tm=time.strptime("%s %s" % (self.yr,self.julian),"%Y %j")
        return "%s.%s (%s/%s/%s)"\
            % (self.yr,self.julian,tm.tm_mon,tm.tm_mday,tm.tm_year)

    def _extract(self):
        self.yr=self.extract("yr")+1900
        self.julian=self.extract("julian")

    # Returns a tuple of the current calendar date:
    #   tuple[0]  the current calendar year
    #   tuple[1]  the current day of year relative to 1 (1 Jan)
    def getDate(self):
        tm=time.localtime()
        return (tm.tm_year,tm.tm_yday)


# Creates a data set extent for an FBA resident data set
# Instance Arguments:
#   lower   The first physical sector of the data set
#   upper   The last physical sector of the data set
#   seq     Extent sequence number of the data set extents.  Default is 1 (the first)
class Extent(structure):
    length=10

    # FBA Extent Fields
    #       beg end len  typ
    typ=   (  0,  1,  1, "U")   # Extent entry type (0=unused,1=used)
    seq=   (  1,  2,  1, "U")   # Extent sequence number
    lower= (  2,  6,  4, "U")   # First physical sector of the extent
    upper= (  6, 10,  4, "U")   # Last physical sector of the extent

    @classmethod
    def from_bytes(cls,byts):
        return Extent(bin=byts)

    def __init__(self,bin=None,lower=0,upper=0,seq=1):
        super().__init__(bin=bin,debug=True)

        if bin is not None:
            return

        self.notused = (lower == 0) and (upper == 0)
        if self.notused:
            return

        assert lower>=0,\
            "%s 'lower' argument must be greater than or equal to 0: %s" \
                % (eloc(self,"__init__"),lower)
        assert lower>=0,\
            "%s 'upper' argument must be greater than or equal to 0: %s" \
                % (eloc(self,"__init__"),upper)
        assert lower<=upper,\
            "%s 'lower' arguement (%s) must not be greater than 'upper' "\
                "argument (%s)" % (eloc(self,"__init__"),lower,upper)

        self.insert("typ",1)

        self.insert("seq",seq)
        self.seq=seq

        self.insert("lower",lower)
        self.lower=lower

        self.insert("upper",upper)
        self.upper=upper

    def __str__(self):
        if self.notused:
            return("Extent() unused")
        return "Extent[%s:%s]-%s sectors:%s" \
            % (self.lower,self.upper,self.seq,self.sectors())

    def _extract(self):
        typ=self.extract("typ")
        if typ == 0:
            self.lower=self.upper=self.seq=0
            self.notused=True
            return

        self.seq=self.extract("seq")
        self.lower=self.extract("lower")
        self.upper=self.extract("upper")
        self.notused=False

    # Returns the number of sectors in the extent
    def sectors(self):
        return self.upper-self.lower+1


# Creates a slot address used as a DSCB pointer within the VTOC.
# Instance Arguments:
#   sector   Logical sector number within the VTOC containing the addressed slot
#   slot     CI slot number of the DSCB record being referenced within the sector.
class SlotAddr(structure):
    length=5

    # FBA Extent Fields
    #       beg end len  typ
    sector=(  0,  4,  4, "U")   # Starting sector of the CI containing the slot
    slot=  (  4,  5,  1, "U")   # Slot number

    @classmethod
    def from_bytes(cls,byts):
        return SlotAddr(bin=byts)

    def __init__(self,bin=None,sector=0,slot=0):
        self.sector=self.slot=0
        super().__init__(bin=bin,debug=True)

        if bin is not None:
            return

        self.insert("sector",sector)
        self.sector=sector

        self.insert("slot",slot)
        self.slot=slot

    def __str__(self):
        return "Slot[%s:%s]" % (self.sector,self.slot)

    def _extract(self):
        self.sector=self.extract("sector")
        self.slot=self.extract("slot")

    # Return an integer representing the slot address
    def to_int(self):
        return self.sector << 8 & self.slot & 0xFF


#
#  +---------------------------+
#  |                           |
#  |   FBA DASD Volume Label   |
#  |                           | 
#  +---------------------------+
#

class VOL1(structure):
    length=512
    ID="VOL1"
    IDFLD="id"

    # Volume Label Fields
    #       beg end len  typ
    id=     ( 0,  4,  4, "C")  # Volume Label Identification
    volser= ( 4, 10,  6, "C")  # Volume serial number
    sec=    (10, 11,  1, "B")  # Security Byte - 0xC0
    zero1=  (11, 12,  1, "B")  # Binary zero - 0x00
    vtocsec=(12, 16,  4, "U")  # Physical sector number of the Volume Table of Contents
    sp1=    (16, 21,  5, "C")  # EBCDIC spaces - 0x40
    cisize= (21, 25,  4, "U")  # VTOC control interval size
    cisecs= (25, 29,  4, "U")  # Number of sectors per control interval
    cislots=(29, 33,  4, "U")  # Number of DSCB record slots per control interval
    sp2=    (33, 37,  4, "C")  # EBCDIC spaces - 0x40
    owner=  (37, 51, 14, "C")  # Owner and address in EBCDIC, otherwise spaces 0x40
    sp3=    (51, 80, 29, "C")  # EBCDIC spaces - 0x40

    @classmethod
    def from_bytes(cls,byts):
        return VOL1(bin=byts)

    def __init__(self,bin=None,volser="SATK",sector=2,cisize=512,owner=None,\
                 debug=False):
        super().__init__(bin=bin,debug=debug)

        if bin is not None:
            return

        self.insert_id()

        if volser is None:
            raise ValueError("%s 'volser' argument required" \
                % eloc(self,"__init__",module=this_module))
        volser=self.pad("volser",volser)
        self.insert("volser",volser)
        self.serial=volser.rstrip()

        self.insert("sec",b"\xC0")
        
        self.insert("zero1",b"\x00")

        if sector is not None:
            self.insert("vtocsec",sector)
            self.sector=sector

        self.insert("sp1"," ",fill=True)

        if cisize is None:
            raise ValueError("%s 'cisize' argument must not be None" \
                % eloc(self,"__init__",module=this_module))

        if ci.CI.cisize_invalid(cisize):
            raise ValueError("%s 'cisize' argument must be a multiple of 512: %s" \
                % (eloc(self,"__init__",module=this_module),cisize))

        self.insert("cisize",cisize)
        self.cisize=cisize

        self.cisecs=cisize // 512
        self.insert("cisecs",self.cisecs)

        self.cislots=ci.CI.ci_slots(cisize,140)
        self.insert("cislots",self.cislots)

        self.insert("sp2"," ",fill=True)

        the_owner=self.pad("owner",owner)
        self.insert("owner",the_owner)
        self.owner=the_owner.rstrip()

        self.insert("sp3"," ",fill=True)

    def __str__(self):
        return "VOL1 - volser:%s  sector:%s  CI size:%s  sectors/CI:%s  slots/CI:"\
            "%s  owner:'%s'" % (self.serial,self.sector,self.cisize,self.cisecs,\
                self.cislots,self.owner)

    def _extract(self):
        self.ck_id()
        self.serial=self.extract("volser")
        self.sector=self.extract("vtocsec")
        self.cisize=self.extract("cisize")
        self.cisecs=self.extract("cisecs")
        self.cislots=self.extract("cislots")
        self.owner=self.extract("owner").rstrip()


#
#  +-----------------------------------------+
#  |                                         |
#  |   FBA DASD DSCB-0 - VTOC Unused Entry   |
#  |                                         | 
#  +-----------------------------------------+
#

class DSCB0(structure):
    length=140
    ID=0
    IDFLD="id"

    # DSCB-0 Fields
    #         beg end len  typ
    id=      ( 44, 45,  1, "U")  # Record ID

    @classmethod
    def from_bytes(cls,byts):
        return DSCB0(bin=byts)

    def __init__(self,bin=None,debug=False):
        super().__init__(bin=bin,debug=debug)

        if bin is not None:
            return

        self.insert_id()

    def __str__(self):
        return "DSCB-0"

    def _extract(self):
        self.ck_id()


#
#  +-------------------------------------------------+
#  |                                                 |
#  |   FBA DASD DSCB-1 - VTOC Data Set Description   |
#  |                                                 | 
#  +-------------------------------------------------+
#

class DSCB1(structure):
    length=140
    ID="1"
    IDFLD="id"

    # DSCB-1 Fields
    #         beg end len  typ
    dsnam=   (  0, 44, 44, "C")  # Data set name
    id=      ( 44, 45,  1, "C")  # Record ID
    volser=  ( 45, 51,  6, "C")  # VOLSER of first extent of the data set
    volseq=  ( 51, 53,  2, "U")  # Volume sequence relative to the first
    crdat=   ( 53, 56,  3, "B")  # Data set creation date
    vtoci=   ( 58, 59,  1, "U")  # VTOC indicator
    noepv=   ( 59, 60,  1, "U")  # Number of extents on this volume
    nobdb=   ( 60, 61,  1, "U")  # Number of bytes in last PDS directory block
    syscd=   ( 62, 75, 13, "C")  # System code of creating program
    cisize=  ( 80, 82,  2, "U")  # Data set control interval size in bytes
    dsorg1=  ( 82, 83,  1, "U")  # Data set organization
    recfm=   ( 84, 85,  1, "U")  # Record format
    optcd=   ( 85, 86,  1, "U")  # Data set organization option code
    blksz=   ( 86, 88,  2, "U")  # Block size
    recsz=   ( 88, 90,  2, "U")  # Record size
    dsi=     ( 93, 94,  1, "U")  # Data set indicator 
    lastsec= ( 98,102,  4, "U")  # Last used data set logical sector
    pdsdb=   (103,105,  2, "U")  # Number of PDS sectors
    ext1=    (105,115, 10, "B")  # First and only extent

    # Dictionary of data set organizations and default movability flag
    dsorg1f={"PS":(0x40,0x00),"DA":(0x20,0x01),"PO":(0x02,0x00),"UN":(0x00,0x01)}

    # Dictionary for encoding record format type
    recfm1d={0x80:"F",0x90:"FB",0x40:"V",0x58:"VB",0xC0:"U",0x08:"S"}
    recfm1e={"F":0x80,"FB":0x90,"V":0x40,"VB":0x50,"U":0xC0,"S":0x08}
    recfm2d={0x00:None,0x04:"A",0x02:"M"}
    recfm2e={None:0x00,"A":0x04,"M":0x02}

    @classmethod
    def from_bytes(cls,byts):
        return DSCB1(bin=byts)

    def __init__(self,bin=None,ds=None,extent=None,org="PS",recfm="FB",ctl=None,\
                 blksz=None,recsz=None,volser=None,cisize=512,vtoci=0,noepv=1,\
                 nobdb=0,syscd="",move=None,rdf=False,physical=False,lastsec=0,\
                 pdsdb=0,debug=True):
        super().__init__(bin=bin,debug=debug)

        if bin is not None:
            return

        if __debug__:
            cls_str=eloc(self,"__init__",module=this_module)
            assert ds is not None,"%s 'ds' argument must not be None" % cls_str
            assert isinstance(extent,Extent),\
                "%s 'extent' argument must be an Extent object: %s" % (cls_str,extent)
            assert volser is not None,"%s 'volser' argument must not be None" \
                % cls_str
            assert recsz is not None,"%s 'recsz' argument must not be None" % cls_str

        self.insert_id()

        self.insert("dsnam",self.pad("dsnam",ds))
        self.ds=ds

        self.insert("volser",self.pad("volser",volser))
        self.volser=volser

        self.volseq=1
        self.insert("volseq",1)

        date=Date()
        self.insert("crdat",date.to_bytes())
        self.crdat=date

        self.insert("vtoci",vtoci)
        self.vtoci=vtoci

        self.insert("noepv",noepv)
        self.noepv=noepv

        self.insert("nobdb",nobdb)
        self.nobdb=nobdb

        self.insert("syscd",self.pad("syscd",syscd))
        self.syscd=syscd

        self.insert("cisize",cisize)
        self.cisize=cisize

        self.dsorg1_encode(org,move)
        self.recfm_encode(recfm,ctl,recsz,blksz)
        self.optcd_encode(rdf,physical)
        self.dsi_encode()

        self.insert("lastsec",lastsec)
        self.lastsec=lastsec

        self.insert("pdsdb",pdsdb)
        self.pdsdb=pdsdb

        self.insert("ext1",extent.to_bytes())
        self.ext1=extent

    def __str__(self):
        # Data set information
        s="DSCB1 - %s  org:%s  cisize:%s  recfm:%s  ctl:%s  recsz:%s  blksz:%s"\
            % (self.ds,self.org,self.cisize,self.recfm,self.ctl,self.recsz,\
                self.blksz)
        # Allocation information
        s="%s\n    volser:%s  volseq:%s  noepv:%s  lastvol:%s %s" \
            % (s,self.volser,self.volseq,self.noepv,self.lastvol,self.ext1)
        s="%s\n    vtoci:%02X  syscd:%s  movable:%s  creation date:%s" \
            % (s,self.vtoci,self.syscd,self.move,self.crdat)
        s="%s\n    rdf eof:%s  physical addressing:%s  last used sector:%s" \
            % (s,self.rdf,self.physical,self.lastsec)
        # PDS information
        s="%s\n    PDS directory sectors: %s  nobdb:%s" \
            % (s,self.pdsdb,self.nobdb)
        return s

    def _extract(self):
        self.ck_id()
        self.ds=self.extract("dsnam").rstrip()
        self.volser=self.extract("volser").rstrip()
        self.volseq=self.extract("volseq")
        crdat=self.extract("crdat")
        self.crdat=Date(bin=crdat)
        self.vtoci=self.extract("vtoci")
        self.noepv=self.extract("noepv")
        self.nobdb=self.extract("nobdb")
        self.syscd=self.extract("syscd").rstrip()
        self.cisize=self.extract("cisize")
        self.dsorg1_decode()
        self.recfm_decode()
        self.optcd_decode()
        self.dsi_decode()
        self.lastsec=self.extract("lastsec")
        self.pdsdb=self.extract("pdsdb")
        ext=self.extract("ext1")
        self.ext1=Extent(bin=ext)

    def dsi_decode(self):
        i=self.extract("dsi")
        self.lastvol = (i & 0x80) == 0x80

    def dsi_encode(self):
        self.insert("dsi",0x80)
        self.lastvol=True

    def dsorg1_decode(self):
        dsorg1=self.extract("dsorg1")
        org= dsorg1 & 0x62
        if org & 0x40:
            self.org="PS"
        elif org & 0x20:
            self.org="DA"
        elif org & 0x02:
            self.org="PO"
        elif org == 0:
            self.org="UN"
        else:
            print("DSCB1 - DECODE WARNING - forcing UN organization, unrecognized "
                "dsorg: %02X" % dsorg1)
            self.org="UN"
        self.move = (dsorg1 & 0x01) == 0

    def dsorg1_encode(self,org,move):
        orgu=org.upper()
        try:
            dsorg,mv=DSCB1.dsorg1f[orgu]
        except KeyError:
            raise ValueError("%s 'org' argument unrecognized: %s" \
                % (eloc(self,"__init__",module=this_module),org)) from None
        if move is not None:
            if move:
                mv=0
            else:
                mv=1
        self.insert("dsorg1",dsorg | mv)
        self.org=orgu
        self.move=mv

    def optcd_decode(self):
        code=self.extract("optcd")
        self.rdf = (code & 0x80) == 0x80
        addr= code & (0x09)
        if addr == 0x08:
            self.physical = True
        elif addr == 0x01:
            self.physical = False
        else:
            print("DSCB1 - DECODE WARNING - forcing physical sector addressing, \
                unrecognized optcd addressing: %02X" % addr)
            self.physical = True

    def optcd_encode(self,rdf,physical):
        optcd=0
        if rdf:
            optcd=optcd | 0x80
            self.rdf=True
        else:
            self.rdf=False
        if physical:
            optcd=optcd | 0x08
            self.physical=True
        else:
            optcd=optcd | 0x01
            self.physical=False
        self.insert("optcd",optcd)

    def recfm_decode(self):
        recfm=self.extract("recfm")
        rfm= recfm & 0xF8
        ctrl= recfm & 0x06
        try:
            rfm=DSCB1.recfm1d[rfm]
        except KeyError:
            print("DSCB1 - DECODE WARNING - forcing U record format, unrecognized "
                "recfm: %02X" % rfm)
            rfm="U"
        try:
            c=DSCB1.recfm2d[ctrl]
        except KeyError:
            print("DSCB1 - DECODE WARNING - forcing cotrol character None, "\
                "unrecognized control character: %02X" % ctrl)
            c=None
        self.recfm=rfm
        self.ctl=c

        self.recsz=self.extract("recsz")
        self.blksz=self.extract("blksz")

    def recfm_encode(self,fm,ctrl,recsz,blksz):
        try:
            fmt=DSCB1.recfm1e[fm]
        except KeyError:
            raise ValueError("%s 'recfm' argument unrecognized: %s" \
                % (eloc(self,"__init__",module=this_module),fm)) from None
        try:
            ctl=DSCB1.recfm2e[ctrl]
        except KeyError:
            raise ValueError("%s 'ctl' argument unrecognized: %s" \
                % (eloc(self,"__init__",module=this_module),ctrl)) from None
        recfm=fmt | ctl
        self.insert("recfm",recfm)
        self.recfm=fm
        self.ctl=ctrl

        if fm == "F" or fm == "V":
            self.insert("recsz",recsz)
            self.recsz=recsz
            if blksz is None:
                self.insert("blksz",recsz)
                self.blksz=recsz
            elif recsz != blksz:
                raise ValueError("%s for recfm %s 'recsz' argument (%s) must equal "
                    "'blksz' argument: %s" \
                        % (eloc(self,"__init__",module=this_module),fm,recsz,\
                            blksz))
            else:
                self.insert("blksz",blksz)
                self.blksz=blksz
        elif fm == "FB":
            if blksz is None:
                raise ValueError("%s for recfm FB 'blksz' argument must not be None"\
                    % eloc(self,"__init__",module=this_module))
            recs,excess=divmod(blksz,recsz)
            if excess:
                raise ValueError("%s for recfm FB 'blksz' argument must be a "\
                    "multiple of 'recsz' argument (%s): %s" \
                        % (eloc(self,"__init__",module=this_module),recsz,blksz))
            self.insert("recsz",recsz)
            self.insert("blksz",blksz)
            self.recsz=recsz
            self.blksz=blksz
        elif fm == "VB":
            if blksze is None:
                raise ValueError("%s for recfm VB 'blksz' argument must not be None"\
                    % eloc(self,"__init__",module=this_module))
            assert blksz>recsz,\
                "%s for recfm VB 'blksz' must be greater than 'recsz' (%s): %s"  \
                    % (eloc(self,"__init__",module=this_module),recsz,blksz)
            self.insert("recsz",recsz)
            self.insert("blksz",blksz)
            self.recsz=recsz
            self.blksz=blksz
        elif fm == "S" or fm == "U":
            self.insert("recsz",recsz)
            self.recsz=recsz
            self.blksz=0
        else:
            raise ValueError("%s unexpected 'fm' argument: %s" \
                % (elic(self,"recfm_encode",module=this_module),fmt))


#
#  +----------------------------------------+
#  |                                        |
#  |   FBA DASD DSCB-4 - VTOC Description   |
#  |                                        | 
#  +----------------------------------------+
#

class DSCB4(structure):
    length=140
    ID="4"
    IDFLD="id"

    # DSCB-4 Fields
    #         beg end len  typ
    key=     (  0, 44, 44, "B")  # Key for CKD compatibility, all X'04'
    id=      ( 44, 45,  1, "C")  # DSCB Format ID, X'F4'
    last=    ( 45, 50,  5, "B")  # Slot address of last DSCB-1
    totrecs= ( 50, 52,  2, "U")  # Number of DSCB records after initialization
    vtoci=   ( 58, 59,  1, "U")  # VTOC indicators
    vtocexts=( 59, 60,  1, "U")  # Number of VTOC extents, always 1
    sp1=     ( 60, 62,  2, "C")  # spaces
    sectors= ( 62, 66,  4, "U")  # Number of sectors aailable on the volume
    devi=    ( 71, 72,  1, "U")  # Device VTOC indicators
    slots=   ( 74, 75,  1, "U")  # Number of slots/CI
    vtocext= (105,115, 10, "B")  # VTOC extent

    @classmethod
    def from_bytes(cls,byts):
        return DSCB4(bin=byts)

    def __init__(self,bin=None,extent=None,last=None,recs=0,cislots=0,vtoci=0,devi=0,\
                 debug=True):
        super().__init__(bin=bin,debug=True)

        if bin is not None:
            return

        if __debug__:
            if extent:
                assert isinstance(extent,Extent),\
                    "%s 'extent' argument must be an Extent object: %s" \
                        % (eloc(self,"__init__",module=this_module),extent)
            if last:
                assert isinstance(last,SlotAddr),\
                    "%s 'extent' argument must be an Extent object: %s" \
                        % (eloc(self,"__init__",module=this_module),last)

        self.insert("key",0x04,fill=True)
        self.insert_id()

        self.insert("last",last.to_bytes())
        self.last=last

        self.insert("totrecs",recs)
        self.totrecs=recs

        self.insert("vtoci",vtoci)
        self.vtoci=vtoci

        self.insert("vtocexts",1)
        self.vtocexts=1

        self.sectors=extent.sectors()
        self.insert("sectors",self.sectors)

        self.insert("devi",devi)
        self.devi=devi

        self.insert("slots",cislots)
        self.slots=cislots

        self.insert("vtocext",extent.to_bytes())
        self.extent=extent

    def __str__(self):
        ext="%s-%s" % (self.extent.lower,self.extent.upper)
        return "DSCB4 - extents:%s  extent:%s  sectors:%s  last:%s  recs:%s  " \
            "cislots:%s  vtoci:%02X  devi:%02X" % (self.vtocexts,ext,self.sectors,\
                self.last,self.totrecs,self.slots,self.vtoci,self.devi)

    def _extract(self):
        self.ck_id()
        self.last=SlotAddr(bin=self.extract("last"))
        self.totrecs=self.extract("totrecs")
        self.vtoci=self.extract("vtoci")
        self.vtocexts=self.extract("vtocexts")
        self.sectors=self.extract("sectors")
        self.devi=self.extract("devi")
        self.slots=self.extract("slots")
        ext=self.extract("vtocext")
        self.extent=Extent(bin=ext)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
    # Comment out the preceding statement to execute the tests.

    test(Date(year=2017,julian=23))
    test(Date())
    test(SlotAddr(sector=2,slot=1))
    test(Extent(lower=2,upper=10))
    test(Extent())
    test_rec(VOL1(owner="ME",debug=False))
    test_rec(DSCB4(extent=Extent(lower=2,upper=10),last=SlotAddr(sector=2,slot=1),\
        recs=80,cislots=5,debug=False))
    test_rec(DSCB1(ds="SYSTEM.LOAD.MODULE",extent=Extent(lower=11,upper=21),\
        volser="ME",syscd="Python",recsz=80,blksz=160,\
        rdf=True,debug=False))
    test_rec(DSCB0(debug=False))
