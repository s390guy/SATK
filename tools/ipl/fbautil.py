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

# This module provides utility functions for accessing AWS Tapes from Python
#
# It is one of a number of modules that support Hercules emulated device
# media:
#
#    media.py      Instances of media records are converted to emulated
#                  media: card images, AWS tape image file, FBA image file
#                  or CKD image file.  All image files are uncompressed.
#    recsutil.py   Python classes for individual records targeted to a device
#                  type: card, tape, fba or ckd
#    rdrpun.py     Handles writing and reading card decks.
#    awsutil.py    Handles writing and reading AWS tape image files.
#    fbautil.py    This module. Handles writing and reading of FBA image files.
#    ckdutil.py    Handles writing and reading of CKD image files.
#
# See media.py for usage of FBA image files.

#import struct
import os       # Access to the OS functions
import stat     # Access to file stat data

class fba(object):
    # To open a new unitialized FBA image:  fba.new(filename,dtype,size,comp)
    #    New FBA image files are always opened as read/write
    # To open an existings FBA image: fba.attach(filename,ro=True|False)
    #    Existing FBA images tapes are opened read-only by default
    # It is recommended to use either attach or new to open an FBA image file
    #
    # fba Static Methods:
    #   attach   Open an existing FBA image file for access
    #   init     Initialize with binary zeros all sectors of a file and
    #            set its size
    #   new      Open a new FBA image file for access
    #
    # fba instance Methods:
    #   read     Read a single sector, either the next or specified sector
    #   seek     Position making the specified sector the next sector
    #   write    Write a single sector, either the next or specific sector
    #.
    # Dictionary mapping device type to sectors. Used to register devices.
    sectors={}
        #                      Sectors     File Size   File Size  K-bytes
        #"3310":124664,      #   124,664   64,851,968    3DD9000   63,332K
        #"3370":558000,      #   558,000  285,696,000   11076000  279,000K
        #"3370-A1":558000,   #   558,000  285,696,000   11076000  279,000K
        #"3370-B1":558000,   #   558,000  285,696,000   11076000  279,000K
        #"3370-A2":712752,   #   712,752  364,929,024   15C06000  356,376K
        #"3370-B2":712752,   #   712,752  364,929,024   15C06000  356,376K
        #"9313":246240,      #   246,240  126,074,880    783C000  123,120K
        #"9313-1":246240,    #   246,240  126,074,880    783C000  123,120K
        #"9332":360036,      #   360,036  184,338,432    AFCC800  180,016K
        #"9332-200":360036,  #   360,036  184,338,432    AFCC800  180,016K
        #"9332-400":360036,  #   360,036  184,338,432    AFCC800  180.016K
        #"9332-600":554800,  #   554,800  284,057,600   10EE6000  277,400K
        #"9335":804714,      #   804,714  412,013,568   188ED400  402,357K
        #"9335-1":804714,    #   804,714  412,013,568   188ED400  402,357K
        #"9336":920115,      #   920,115  471,098,880   1C146600  460,057K
        #"9336-10":920115,   #   920,115  471,098,880   1C146600  460,057K
        #"9336-20":1672881,  # 1,672,881  856,515,072   330D6200  836,440K
        #"9336-25":1672881,  # 1,672,881  856,515,072   330D6200  836,440K
        #"0671":574560,      #   574,560  294,174,720   1188C000  287,280K
        #"0671-04":624456,   #   624,456  319,721,472   130E9000  312,228K
        #"0671-08":513072}   #   513,072  262,692,864    FA86000  256,536K
    record=["fba"]    # recsutil class name of fba records
    pad=512*"\x00"  # Sector pad
    @staticmethod
    def attach(filename,ro=True):
        # Access an existing FBA emulating media file for reading or writing.
        if ro:
            mode="rb"
        else:
            mode="a+b"
        try:
            fo=open(self.filename,mode)
        except IOError:
            raise IOError(\
                "Could not open existing FBA image: %s" % self.filename)
        return fba(fo,ro)
    @staticmethod
    def init(fo,dtype,size=None,comp=False):
        try:
            dev=fba.sectors[dtype]
            sectors=dev.sectors
        except KeyError:
            raise TypeError("unrecognized FBA device type: %s" % dtype)
        if not size is None:
            if comp:
                blkgrp=120   # A block group is 120 sectors
                (grps,excess)=divmod(size,blkgrp)
                if excess!=0:
                    sectors=(grps+1)*blkgrp
            else:
                sectors=size
        fo.truncate()
        for x in xrange(sectors):
            try:
                fo.write(fba.pad)
            except IOError:
                raise IOError("error initializing FBA image sector %s: %s" \
                    % (x,fo.name))
        fo.seek(0)
    @staticmethod
    def new(filename,dtype,size=None,comp=False):
        # Create a new FBA image file, overwriting an existing file
        try:
            fo=open(filename,"w+b")
        except IOError:
            raise IOError(\
                "Could not open new FBA image: %s" % filename)
        
        fba.init(fo,dtype,size=size,comp=comp)
        return fba(fo,ro=False)
    @staticmethod
    def size(dtype,hwm=None,comp=False):
        # Size a new device.  
        # hwm (high water mark) is the last used sector number
        # This method is required by media.py to size a emulating media file
        if hwm is None:
            return fba.sectors[dtype].sectors
        if comp:
            (grps,excess)=divmod(hwm+1,120)
            if excess>0:
                grps+=1
            return grps*120
        return hwm+1
    def __init__(self,fo,ro=True):
        self.fo=fo              # Open file object from mount or scratch
        self.ro=ro              # Set read-only (True) or read-write (False)
        self.pos=0              # Set at load point
        self.filesize=self.__file_size()  # Determine the physical file size
        (sectors,excess)=divmod(self.filesize,512)
        if excess!=0:
            raise TypeError("FBA image truncated last sector %s: %s" \
                % (sectors,self.fo.name))
        self.last=sectors-1     # Last sector number
        self.seek(0)            # Position at sector zero
        self.sector=0           # Current sector position
    def __file_size(self):
        # Determines the file size using Python modules
        s=os.fstat(self.fo.fileno())  # Get a stat instance from file number
        return s[stat.ST_SIZE]        # Get the file size from the stat data
    def detach(self):
        try:
            self.fo.close()
        except IOError:
            raise IOError("IOError detaching %s FBA image %s" % self.fo.name)
    def read(self,sector=None):
        if not sector is None: 
            self.seek(sector)
        try:
            return self.fo.read(512)  # Read and return the sector
            self.sector+=1
        except IOError:
            raise IOError("error reading FBA sector: %s" % self.sector)
    def seek(self,sector):
        # Sets the pos in the file for reading or writing a sector
        if sector>self.last:
            raise ValueError("FBA sector %s is beyond last sector %s" \
                % (sector,self.last))
        sector_loc=sector*512
        if sector_loc>self.filesize:
            raise IOError("FBA sector %s file position %s is beyond EOF: %s" \
                % (sector,sector_loc,self.filesize))
        self.fo.seek(sector_loc)
        self.sector=sector
    def write(self,bytes,sector=None,pad=False):
        if self.ro:
            raise NotImplementedError(\
                "Can not write to read-only FBA image: %s" % self.fo.name)
        if not sector is None:
            self.seek(sector)
        data=bytes
        if len(data)!=512:
            if pad:
               data=data+fba.pad
               data=data[:512]
            else:
                raise TypeError("FBA image sector must be 512 bytes: %s"\
                    % len(data))
        try:
            self.fo.write(data)
            self.sector+=1
        except IOError:
            raise IOError(\
                "IOError while writing FBA sector: %s" % self.sector)

class fba_info(object):
    #K=1024
    #M=1024*1024
    #G=1024*1024*1024
    units=[1024*1024*1024,1024*1024,1024]
    def KMG(value):
        for x in range(len(fba_info.units)):
            if value>=x:
                unit="GMK"[x]
                unit_metric=fba_info.units[x]
                units,excess=divmod(value,unit_metric)
                tenths=excess*10 / unit_metric
                return "%s.%s%sB" % (units,tenths,unit)
        return "%sB" % (value)
    KMG=staticmethod(KMG)
    # This class gives access to the information managed by the fbadev class. 
    # Once created, a fba_info instance is read only.
    def __init__(self,dtype,blocklen=0):
        try:
            self.__dev=fba.sectors[dtype]  # Access fba's sector dictionary
        except KeyError:
            raise TypeError("unrecognized FBA device type: %s" % dtype)
        self.__block=blocklen    # Size of the block for this instance
    def __str__(self):
        string="Volume:  TYPE=%s SECTORS=%s LFS=%s" \
            % (self.device,self.sectors,self.lfs)
        string="\nHost:    FILE=%s (%s)" \
            % (self.host,fba_info.KMG(self.host))
        string="\nBlock:   LENGTH=%s SECTORS=%s BLOCKS=%s" \
            % (self.block,self.required,self.capacity)
        return string
    @property
    def block(self):
        # Returns the specified block length
        return self.__block
    @property
    def capacity(self):
        # Return the number of blocks that can be stored on the volume
        if self.__block<=0:
            return None
        return self.hostsize//self.__block
    @property
    def device(self):
        # Returns the device type
        return self.__dev.dtype
    @property
    def required(self):
        # Returns the number of sectors required for the specified block length
        return (self.__block+511)//512
    @property
    def sectors(self):
        # Returns the number of 512-bytes sectors in this device type.
        return self.__dev.sectors
    #
    # Provides volume related information
    @property
    def host(self):
        # Returns the host file size of the emulated volume
        return self.sectors*512
    @property
    def lfs(self):
        # Returns whether host large file system support is required
        return False

class fbadev(object):
    def __init__(self,dtype,devtyp,cls,typ,mdl,bpg,bpp,size,blks,cu):
        # All of the elements of the Hercules FBADEV table are provided in
        # the instance definition.  Only those elements required by fbautil
        # are set to attributes of the fbadev instance.
        #                                               Hercules FBADEV field 
        self.dtype=dtype    # Device type                         name
        self.devtyp=devtyp  # Device number                       devt
        self.model=mdl      # Device model                        mdl
        self.sectors=blks   # Number of sectors                   blks
        self.logcyl=bpp     # Sectors per logical cylinder        bpp
        self.logtrk=bpg     # Sectors per logical track           bpg
        fba.sectors[self.dtype]=self

#static FBADEV fbatab[] = {
#/* name          devt class type mdl  bpg bpp size   blks   cu     */
# {"3310",       0x3310,0x21,0x01,0x01, 32,352,512, 125664,0x4331},
# {"3310-1",     0x3310,0x21,0x01,0x01, 32,352,512, 125664,0x4331},
# {"3310-x",     0x3310,0x21,0x01,0x01, 32,352,512,      0,0x4331},
#
# {"3370",       0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880},
# {"3370-1",     0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880},
# {"3370-A1",    0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880},
# {"3370-B1",    0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880},
# {"3370-2",     0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880},
# {"3370-A2",    0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880},
# {"3370-B2",    0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880},
# {"3370-x",     0x3370,0x21,0x05,0x04, 62,744,512,      0,0x3880},
#
# {"9332",       0x9332,0x21,0x07,0x00, 73,292,512, 360036,0x6310},
# {"9332-400",   0x9332,0x21,0x07,0x00, 73,292,512, 360036,0x6310},
# {"9332-600",   0x9332,0x21,0x07,0x01, 73,292,512, 554800,0x6310},
# {"9332-x",     0x9332,0x21,0x07,0x01, 73,292,512,      0,0x6310},
#
# {"9335",       0x9335,0x21,0x06,0x01, 71,426,512, 804714,0x6310},
# {"9335-x",     0x9335,0x21,0x06,0x01, 71,426,512,      0,0x6310},
#
#/*"9313",       0x9313,0x21,0x08,0x00, ??,???,512, 246240,0x????}, */
#/*"9313-1,      0x9313,0x21,0x08,0x00, ??,???,512, 246240,0x????}, */
#/*"9313-14",    0x9313,0x21,0x08,0x14, ??,???,512, 246240,0x????}, */
#/* 246240=32*81*5*19 */
# {"9313",       0x9313,0x21,0x08,0x00, 96,480,512, 246240,0x6310},
# {"9313-x",     0x9313,0x21,0x08,0x00, 96,480,512,      0,0x6310},
#
#/* 9336 Junior models 1,2,3 */
#/*"9336-J1",    0x9336,0x21,0x11,0x00, 63,315,512, 920115,0x6310}, */
#/*"9336-J2",    0x9336,0x21,0x11,0x04, ??,???,512,      ?,0x6310}, */
#/*"9336-J3",    0x9336,0x21,0x11,0x08, ??,???,512,      ?,0x6310}, */
#/* 9336 Senior models 1,2,3 */
#/*"9336-S1",    0x9336,0x21,0x11,0x10,111,777,512,1672881,0x6310}, */
#/*"9336-S2",    0x9336,0x21,0x11,0x14,???,???,512,      ?,0x6310}, */
#/*"9336-S3",    0x9336,0x21,0x11,0x18,???,???,512,      ?,0x6310}, */
# {"9336",       0x9336,0x21,0x11,0x00, 63,315,512, 920115,0x6310},
# {"9336-10",    0x9336,0x21,0x11,0x00, 63,315,512, 920115,0x6310},
# {"9336-20",    0x9336,0x21,0x11,0x10,111,777,512,1672881,0x6310},
# {"9336-25",    0x9336,0x21,0x11,0x10,111,777,512,1672881,0x6310},
# {"9336-x",     0x9336,0x21,0x11,0x10,111,777,512,      0,0x6310},
#
# {"0671-08",    0x0671,0x21,0x12,0x08, 63,504,512, 513072,0x6310},
# {"0671",       0x0671,0x21,0x12,0x00, 63,504,512, 574560,0x6310},
# {"0671-04",    0x0671,0x21,0x12,0x04, 63,504,512, 624456,0x6310},
# {"0671-x",     0x0671,0x21,0x12,0x04, 63,504,512,      0,0x6310}
#} ;
 
# Build the sectors dictionary
fbadev("3310",       0x3310,0x21,0x01,0x01, 32,352,512, 125664,0x4331)
fbadev("3310-1",     0x3310,0x21,0x01,0x01, 32,352,512, 125664,0x4331)
fbadev("3370",       0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880)
fbadev("3370-1",     0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880)
fbadev("3370-A1",    0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880)
fbadev("3370-B1",    0x3370,0x21,0x02,0x00, 62,744,512, 558000,0x3880)
fbadev("3370-2",     0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880)
fbadev("3370-A2",    0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880)
fbadev("3370-B2",    0x3370,0x21,0x05,0x04, 62,744,512, 712752,0x3880)
fbadev("9332",       0x9332,0x21,0x07,0x00, 73,292,512, 360036,0x6310)
fbadev("9332-400",   0x9332,0x21,0x07,0x00, 73,292,512, 360036,0x6310)
fbadev("9332-600",   0x9332,0x21,0x07,0x01, 73,292,512, 554800,0x6310)
fbadev("9335",       0x9335,0x21,0x06,0x01, 71,426,512, 804714,0x6310)
fbadev("9313",       0x9313,0x21,0x08,0x00, 96,480,512, 246240,0x6310)
fbadev("9336",       0x9336,0x21,0x11,0x00, 63,315,512, 920115,0x6310)
fbadev("9336-10",    0x9336,0x21,0x11,0x00, 63,315,512, 920115,0x6310)
fbadev("9336-20",    0x9336,0x21,0x11,0x10,111,777,512,1672881,0x6310)
fbadev("9336-25",    0x9336,0x21,0x11,0x10,111,777,512,1672881,0x6310)
fbadev("0671-08",    0x0671,0x21,0x12,0x08, 63,504,512, 513072,0x6310)
fbadev("0671",       0x0671,0x21,0x12,0x00, 63,504,512, 574560,0x6310)
fbadev("0671-04",    0x0671,0x21,0x12,0x04, 63,504,512, 624456,0x6310)
 
# media.py expects this function to be available
def register_devices(dtypes):
    for x in fba.sectors.values():
        dtypes.dtype(x.dtype,fba)
        dtypes.dndex(dtypes.number(x.devtyp,x.model),x.dtype)

if __name__=="__main__":
    print "awsutil.py is only intended for import"