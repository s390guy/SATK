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
#    fbautil.py    Handles writing and reading of FBA image files.
#    ckdutil.py    This module. Handles writing and reading of CKD image files.
#
# See media.py for usage of CKD image filed

import hexdump     # Access dump utility
import os          # Access OS functions
import stat        # Access to file stat data
import struct      # Make binary structure module available
import sys         # Access Python system funtions

class ckd(object):
    # This class provides the external interface seen by users of the ckdutil
    # module.  It uses the ckdev class instance to interface with the image
    # file.
    #
    # To open a new unitialized CKD image:  ckd.new(filename,dtype,size,comp)
    #    New CKD image files are always opened as read/write
    # To open an existings CKD image: ckd.attach(filename,ro=True|False)
    #    Existing CKD images are opened read-only by default
    # Either attach or new are required to open a CKD image file
    #
    # ckd Static Methods:
    #   attach   Open an existing CKD image file for access
    #   new      Open a new CKD image file for access
    #
    # ckd Instance Methods:
    #
    #   detach   Flushes to the image updated cache and closes image file
    #   read     Reads a (key,data) tuple from a cached track image
    #   seek     Flushes an updated cache image to the file and reads into
    #            the cache a new track image
    #   update   Updates a record's data in a cached track image.  Data is
    #            padded or truncated as required to maintain the data's
    #            length.
    #   write    Write a new record to a cached track image, ala format 
    #            write.  All existing records starting with the new record
    #            will be removed from the track before the new record is
    #            added.  This semantics is similar to a formatting write
    #            operation on a CKD DASD device.
    #  
    # Dictionary mapping device type to CKD geometry.
    geometry={}     # Built when ckdev instances are created
    record="ckd"    # recsutil class name of ckd records
    autodump=False  # Master switch to enable dumps
    #
    # Private Static Methods
    @staticmethod
    def __devtyp(typ):
        try:
            return ckd.geometry[typ]
        except KeyError:
            raise TypeError("unrecognized CKD device type: %s" % typ)
    @staticmethod
    def __init(fo,dtype,size=None,comp=False,progress=False,debug=False):
        dev=ckd.__devtyp(dtype)
        if not size is None:
            cyls=size
        else:
            cyls=dev.ecyl
        fo.truncate(0)
        try:
            fo.write(dev.devhdr())
        except IOError:
            raise IOError("writing CKD device header")
        init_cyls=0
        for x in xrange(cyls):
            for y in range(dev.eheads):
                #print "track (%s,%s)" % (x,y)
                t=track(dev,x,y,r0=True)
                trkimg=t.pack(debug=debug)
                if len(trkimg)!=dev.etrksize:
                    raise IndexError("init track image not %s bytes: %s" \
                        % (dev.etrksize,len(trkimg)))
                try:
                    fo.write(trkimg)
                except IOError:
                    raise IOError("writing track image: (%s,%s)" % (x,y))
            init_cyls+=1
            if progress and ((x%100)==0):
                print "Cylider initialized: %s" % x
        fo.flush()
        if progress:
            print "%s CKD image initialized with %s cylinders: %s" \
                % (dev.edtype,init_cyls,fo.name)
        return cyls
    #
    # ckd Static Methods
    @staticmethod
    def attach(filename,ro=True,debug=False):
        # Access an existing CKD emulating media file for reading or writing.
        if ro:
            mode="rb"
        else:
            mode="a+b"
        try:
            fo=open(filename,mode)
        except IOError:
            raise IOError(\
                "Could not open existing FBA image: %s" % filename)
        hdr=fo.read(ckdev.hdrsize)
        heads,devtyp,trksize=ckdev.parse(hdr,debug)
        stat=os.fstat(fo.fileno())  # stat instance from file number
        filesize=stat.st_size           # Get the file size from the stat data
        tracks,excess=divmod(filesize-512,trksize)
        if excess!=0:
            print "WARNING: malformed CKD image file, incomplete track: %s" \
                % self.fo.name
        cyls,excess=divmod(tracks,heads)
        if excess!=0:
            raise ValueError(\
                "CKD image file contains truncated cylinder: %s" \
                % cyls)
        try:
            dev=ckdev.extract(devtyp,cyls)
            if debug:
                print dev
        except KeyError:
            raise TypeError("CKD header device type unrecognized: 0x%02X" \
                % ord(devtyp))
        if trksize!=dev.etrksize:
            raise ValueError(\
                "CKD header track size incompatible with device "
                "type %s size %s: %s" \
                % (dev.edtype,dev.etrksize,etrksize))
        return ckd(fo,dev,cyls,ro)
    @staticmethod
    def dump(enable=False):
        ckd.autodump=enable
    @staticmethod
    def new(filename,dtype,size=None,comp=False,progress=False):
        # Create a new CKD image file, overwriting an existing file
        try:
            fo=open(filename,"w+b")
        except IOError:
            raise IOError(\
                "Could not open new CKD image: %s" % filename)
        cyls=ckd.__init(fo,dtype,size=size,comp=comp,progress=progress)
        return ckd(fo,ckd.__devtyp(dtype),cyls,ro=False)
    @staticmethod
    def size(dtype,hwm=None,comp=False):
        # Size a new device by providing the number of required cylinders 
        # hwm (high water mark) is the recsutil recid of the last record
        # This method is required by media.py to size a emulating media file
        if hwm is None:
            dev=ckd.geometry[dtype]
            return dev.ecyl
        return hwm[0]+1  # Return the number of cylinders
    #
    # ckd instance methods
    def __init__(self,fo,dev,cyls,ro=True):
        self.fo=fo          # Open file object from new or attach
        self.dev=dev        # ckdev instance for this volume
        self.cyls=cyls      # Number of cylinders in the emulated CKD device
        self.ro=ro          # Set read-only (True) or read-write (False)
        # Cached track instance
        self.cache=None
    def __str__(self):
        return "CKD %s cyl=%s" % (self.dev.edtype,self.cyls)
    def __check_cache(self):
        if not isinstance(self.cache,track):
            raise NotImplementedError("operation must be preceded by seek")
    def __check_cyl(self,cyl):
        if cyl>self.cyls-1:
            raise IndexError("invalid cylinder (max=%s): %s" \
                % (self.cyls-1,cyl))
    def __check_head(self,head):
        if (head>self.dev.eheads-1) or (head<0):
            raise IndexError("invalid head (max=%s): %s" \
                % (self.dev.eheads-1,head))
    def __check_rec(self,rec):
        if (rec>255) or (rec<0):
            raise IndexError("invalid record (max=255): %s" % rec)
    def __check_ro(self):
        if self.ro:
            raise NotImplementedError(\
                "operation not allowed for read-only volume")
    def __check_track(self,cyl,head):
        if self.cache.cyl!=cyl or self.cache.head!=head:
            raise NotImplementedError(\
                "track (%s,%s) requires record for same track: (%s,%s)" \
                % (self.cache.cyl,self.cache.head,record.cyl,record.head))
    def detach(self,debug=False):
        if debug:
            print("ckdutil.py: debug: ckd.detach: self.cache=%s" \
                % self.cache)
            #if self.cache != None:
            #    print("ckdutil.py: debug: ckd.detach: self.cache.updated=%s" \
            #        % self.cache.updated)
        if (self.cache!= None) and self.cache.updated:
            self.dev.write(self.fo,self.cache,debug=debug)
        try:
            self.fo.close()
        except IOError:
            raise IOError("IOError detaching %s CKD image %s" % self.fo.name)
    def read(self,recno):
        # Trys to find a record from a cached track image.
        # On success, returns a tuple (key,data)
        # If it fails, it raises an exception
        self.__check_cache()
        self.__check_rec(recno)
        rec=self.cache.read(recno)
        if rec is None:
            raise IndexError("Could not find on track (%s,%s) record: %s" \
                % (self.cache.cyl,self.cache.head,recno))
        return (rec.key,rec.data)
    def seek(self,cc,hh,debug=False,dump=False):
        dodump=dump or ckd.autodump
        self.__check_cyl(cc)
        self.__check_head(hh)
        if self.cache is None:
            if debug:
                print("ckdutil.py: debug: ckd.seek(%s,%s) - " \
                    "initial seek" \
                    % (cc,hh))
            self.cache=self.dev.read(self.fo,cc,hh,debug=debug,dump=dodump)
        else:
            if debug:
                print("ckdutil.py: debug: ckd.seek(%s,%s) - " \
                    "current track (%s,%s)" \
                    % (cc,hh,self.cache.cyl,self.cache.head))
            if (cc!=self.cache.cyl or hh!=self.cache.head):
                if self.cache.updated:
                    if debug:
                        print("ckdutil.py: debug: ckd.seek(%s,%s) - " \
                            "updating current track" \
                            % (cc,hh))
                    self.dev.write(self.fo,self.cache,debug=debug,dump=dodump)
                if debug:
                    print "ckdutil.py: debug: ckd.seek(%s,%s) - " \
                        "reading track" \
                        % (cc,hh)
                self.cache=self.dev.read(self.fo,cc,hh,debug=debug,dump=dodump)
    def update(self,recno,data=""):
        # Trys to update a cached track image record's data.  
        # Raises an exception if it fails
        self.__check_ro()
        self.__check_rec(recno)
        self.__check_cached()
        if not self.cache.update(recno,data):
             raise IndexError(\
                 "Failed to update track (%s,%s) record: %s" \
                 % (self.cache.cyl,self.cache.head,recno))
    def write(self,cc,hh,r,key="",data="",debug=False):
        # Trys to write a new record to a cached track image
        # Raises an exception if it fails
        self.__check_ro()
        self.__check_cyl(cc)
        self.__check_head(hh)
        self.__check_rec(r)
        self.__check_cache()
        self.__check_track(cc,hh)
        r=record(cc,hh,r,key=key,data=data)
        succeeded=self.cache.write(r,debug=debug)
        if not succeeded:
            raise IndexError("Failed to write to track (%s,%s) record: %s" \
                % (cc,hh,r))

class ckd_info(object):
    K=1024
    M=1024*1024
    G=1024*1024*1024
    def KMG(value):
        if value>=ckd_info.G:
            unit="G"
            unit_metric=ckd_info.G
        else:
            if value>=ckd_info.M:
                unit="M"
                unit_metric=ckd_info.M
            else:
                unit="K"
                unit_metric=ckd_info.K
        units,excess=divmod(value,unit_metric)
        tenths=excess*10 / unit_metric
        return "%s.%s%s" % (units,tenths,unit)
    KMG=staticmethod(KMG)
    # This class gives access to the information managed by the ckdev class 
    # and devcap subclasses.  Once created, a ckd_info instance is read only.
    def __init__(self,dtype,keylen=0,datalen=0):
        self.__dev=ckd._ckd__devtyp(dtype)  # Use ckd's private static method
        self.__info=self.__dev.formula      # Access the devcap instance
        self.__info.calc(klen=keylen,dlen=datalen)
    def __str__(self):
        string="Volume:  TYPE=%s CYLINDERS=%s PRIMARY=%s ALTERNATE=%s LFS=%s" \
            % (self.device,self.cylinders,self.primary,self.alternate,self.lfs)
        string="%s\nTrack:   HEADS=%s CAPACITY=%s IMAGE=%s" \
            % (string,self.heads,self.capacity,self.image)
        string="%s\nRecord:  KEY=%s DATA=%s block=%s last block=%s" \
            % (string,self.key,self.data,self.block,self.last)
        string="%s\n         R0=%s R1=%s HA+RO=%s" \
            % (string,self.R0,self.R1,self.HA_R0)
        string="%s\nDataset: Records/Track=%s" % (string,self.NUMRECS)
        string="%s\n         DEVFG=%s DEVI=%s DEVK=%s DEVL=%s DEVTL=%s" \
            % (string,self.DEVFG,self.DEVI,self.DEVK,self.DEVL,self.DEVTL)
        if self.data>self.R1:
            string="%s\nStorage: "\
                "block data length %s exceeds track capacity %s"\
                % (string,self.data,self.R1)
            return string
        cyl=self.Cylinder
        trk=self.Track
        vol=self.Volume
        string="%s\nStorage: Track=%s (%s) Cylinder=%s (%s) Volume=%s (%s)" \
            % (string,trk,ckd_info.KMG(trk),\
                      cyl,ckd_info.KMG(cyl),\
                      vol,ckd_info.KMG(vol))
        return string
    #
    # Volume related properties
    @property
    def alternate(self):
        # Return the number of alternate cylinders
        return self.__dev.ealt
    @property
    def cylinders(self):
        # Return total number of cylinders of the device
        return self.__dev.ecyl
    @property
    def device(self):
        # Return the device type
        return self.__dev.edtype
    @property
    def lfs(self):
        # Return if large file system required for emulation
        return self.__dev.elfs
    @property
    def primary(self):
        # Return the number of primary cylinders
        return self.__dev.eprime
    # Track related properties
    @property
    def capacity(self):
        # Return the capacity of a real device tracks
        return self.__dev.rlen
    @property
    def heads(self):
        # Return number of heads per track
        return self.__dev.eheads
    @property
    def image(self):
        # Returns the size of a track in the emulated disk volume
        return self.__dev.etrksize
    @property
    def tracks(self):
        # Return the total number of tracks of the device
        return self.heads*self.cylinders
    #
    # Record related properties
    @property
    def block(self):
        # Track capacity consumed by an individual block (with specified
        # key length and data length)
        return self.__info.block_used
    @property
    def data(self):
        # Return the record's data length property
        return self.__info.dlen
    @property
    def key(self):
        # Return the record's data length property
        return self.__info.dlen
    @property
    def last(self):
        # Track capacity consumed by the last block on a track (with
        # specified key length and data length)
        return self.__info.last_used
    @property
    def HA_R0(self):
        # Bytes consumed by Home Address and Record 0
        return self.__dev.rhar0
    @property
    def R0(self):
        # Maximum Record 0 data size
        return self.__dev.er0
    @property
    def R1(self):
        # Maximum Record 1 data size
        return self.__dev.er1
    #
    # Dataset related properties
    @property
    def DEVFG(self):
        return self.__info.DEVFG
    @property
    def DEVI(self):
        return self.__info.DEVI
    @property
    def DEVK(self):
        return self.__info.DEVK
    @property
    def DEVL(self):
        return self.__info.DEVL
    @property
    def DEVTL(self):
        return self.__info.DEVTL
    @property
    def NUMRECS(self):
        # Return number of records per track (with the specified key length
        # and data length
        return self.__info.NUMRECS
    #
    # Data storage potential for specified key length and data length
    # Note: key length is not included in the calculations.
    @property
    def Cylinder(self):
        return self.Track*self.heads
    @property
    def Record(self):
        return self.__info.dlen
    @property
    def Track(self):
        return self.NUMRECS*self.Record
    @property
    def Volume(self):
        return self.Cylinder*self.primary

class ckdev(object):
    # This class provides the interface between Python ckdutil class
    # instances and the CKD emulation file.  It operates at the level
    # of track images and Python file objects and assists class ckd with
    # building the internal dictionary caches.
    #
    # ckdev Static methods
    #   ckfmt    Checks that the struct format builds the correct sizes
    #
    # ckdev Instance methods
    #   capacity  After adding a record to a track, returns
    #   records   Returns the number of records of a given size that will
    #             fit on a single track
    #
    # header struct formats
    devfmt="<8sLLccH"  # Device header format
    recfmt=">HHccH"    # Record header format
    trkfmt=">cHH"      # Track header format
    # header related information
    hdrdev={}          # This maps the device header type field to instances
    hdrID="CKD_P370"   # Constant in a Hercules CKD device header
    hdrsize=20         # Size of device image header
    def ckfmt(fmt,field,length):
        size=struct.calcsize(fmt)
        if size!=length:
            raise ValueError("ckdev.%s structure not %s bytes: %s" \
                % (field,length,size))
    ckfmt=staticmethod(ckfmt)
    def extract(devtyp,cyls):
        type_list=ckdev.hdrdev[devtyp]
        for x in type_list:
            if cyls<=x.ecyl:
                return x
        return type_list[0]
    extract=staticmethod(extract)
    def parse(header,debug=False):
        if len(header)!=ckdev.hdrsize:
            raise IndexError("CKD header size not %s: %s" \
                % (ckdev.hdrsize,len(header)))
        ID,heads,etrksize,devtyp,seq,highcyl\
            =struct.unpack(ckdev.devfmt,header)
        if debug:
            string="CKD.ID: %s" % ID
            string="%s\nCKD.heads: %s" % (string,heads)
            string="%s\nCKD.tracksize: %s" % (string,etrksize)
            string="%s\nCKD.devtyp: 0x%02X" % (string,ord(devtyp))
            string="%s\nCKD.seq: %s" % (string,ord(seq))
            string="%s\nCKD.highcyl: %s" % (string,highcyl)
            print string
        if ID!=ckdev.hdrID:
            raise TypeError("invalid CKD device header")
        if highcyl!=0:
            raise TypeError("multi-image file CKD volumes not supported")
        return (heads,devtyp,etrksize)
    parse=staticmethod(parse)
    def register(inst):
        # Register myself with the ckd class
        ckd.geometry[inst.edtype]=inst
        # Register myself with the ckd header device type dictionary
        try:
            type_list=ckdev.hdrdev[inst.devtyp]
        except KeyError:
            type_list=[]
        type_list.append(inst)
        type_list.sort()
        ckdev.hdrdev[inst.devtyp]=type_list
    register=staticmethod(register)
    #
    # ckdev Instance Methods
    def __init__(self,dtype,devtyp,model,clas,code,prime,alt,heads,\
                 r0,r1,har0,length,sectors,rps,formula,f1,f2,f3,f4,f5,f6,cu):
        # All of the elements of the Hercules CKDDEV table are provided in
        # the instance definition.  Only those elements required by ckdutil
        # are set to attributes of the ckdev instance.
        #                                               Hercules CKDDEV field 
        self.edtype=dtype    # Device type                       name
        self.edevice=devtyp  # Device number                     type
        self.emodel=model    # Device model number               model
        self.eprime=prime    # Number of primary cylinders       prime
        self.ealt=alt        # Number of alternate cylinders     a
        self.eheads=heads    # Number of tracks per cylinder     hd
        self.er0=r0          # Maximum r0 data length            r0
        self.er1=r1          # Maximum r1 data length            r1
        self.rhar0=har0      # Size on real disk of HA and R0    har0
        self.rlen=length     # Maximum content on a real disk    len
        self.formula=formula # Formula number of device          f
        self.f1=f1           # Formula factors                   f1
        self.f2=f2           #                                   f2
        self.f3=f3           #                                   f3
        self.f4=f4           #                                   f4
        self.f5=f5           #                                   f5
        self.f6=f6           #                                   f3
        # Derived values
        #
        # Total number of cylinders in the volume (primary plus alternates)
        self.ecyl=self.eprime+self.ealt
        # The formula class used for determining real device track capacity
        self.formula=formula(f1,f2,f3,f4,f5,f6,self.rlen)
        #self.method=formulas[self.formula+2]
        #
        # The emulation file tracksize
        # tracksize=sizeof(trkhdr)      HA              (5 bytes)
        #          +sizeof(rechdr)+8    R0 (8 data)     (5+16=21 bytes)
        #          +sizeof(rechdr)+r1   R1 max. size    (21+8=29+r1 bytes)
        #          +8                   eight 0xFF's    (8+29=37+r1 bytes
        # tracksize is rounded up to the next full 512 bytes
        self.etrksize=(((37+self.er1)+511)//512)*512
        # Is LFS required to support this volume as a single image file
        # (This module supports only one image file for a volume)
        self.elfs=self.lfs()
        # Header device type
        self.devtyp=chr(devtyp&0xFF)
        #
        # Register myself with the ckd class
        ckdev.register(self)
        #ckd.geometry[self.edtype]=self
        # Register myself with the ckd header device type dictionary
        #ckdev.hdrdev[self.etrksize]=self
    def __cmp__(self,other):
        # Allows ckdev instances to be sorted in a list
        # Used by ckdev.register() static method.
        if self.ecyl<other.ecyl:
            return -1
        if self.ecyl>other.ecyl:
            return 1
        return 0
    def __str__(self):
        string="CKD Device: %s" % self.edtype
        string="%s\nPrimary Cylinders: %s" % (string,self.eprime)
        string="%s\nAlternate Cylinders: %s" % (string,self.ealt)
        string="%s\nTracks per Cylinder: %s" % (string,self.eheads)
        string="%s\nMaximum R0 Data Length: %s" % (string,self.er0)
        string="%s\nMaximum R1 Data Length: %s (0x%X)" \
            % (string,self.er1,self.er1)
        cylsize=self.eheads*self.er1
        string="%s\nMaximum cylinder data: %s (0x%X)" \
            % (string,cylsize,cylsize)
        volsize=cylsize*self.eprime
        string="%s\nMaximum volume data: %s (0x%X)" \
            % (string,volsize,volsize)
        string="%s\nReal Disk HA and R0 size: %s" % (string,self.rhar0)
        string="%s\nReal Disk Maximum Track size: %s" % (string,self.rlen)
        string="%s\nImage File Track size: %s (0x%X)" \
            % (string,self.etrksize,self.etrksize)
        isize=self.etrksize*self.eheads*self.ecyl
        string="%s\nImage File size: %s (0x%X)" % (string,isize,isize)
        string="%s\nHeader Device Type: 0x%02X" % (string,ord(self.devtyp))
        string="%s\nLarge File System required: %s" % (string,self.elfs)
        string="%s\nFormula %s " % (string,self.formula.__class__.__name__)
        string="%sFactors: f1(%s),f2(%s),f3(%s),f4(%s),f5(%s),f6(%s)" \
            % (string,self.f1,self.f2,self.f3,self.f4,self.f5,self.f6)
        return string
    #
    # Private methods
    def __file_pos(self,reltrk):
        # returns the file position of this track
        return (reltrk*self.etrksize)+512
    def __rel_track(self,cyl,head):
        # Returns the relative track
        if cyl>=self.ecyl:
            raise ValueError("cylinder beyond image capacity %s: %s" \
                % (self.ecyl,cyl))
        if head>=self.eheads:
            raise ValueError("head beyond tracks in a cylinder %s: %s" \
                % (self.eheads,head))
        return (cyl*self.eheads)+head
    def capacity(self,used,keylen,datalen):
        # returns (newused,fit,track_balance)
        #b1,b2,nrecs=self.method(keylen,datalen)
        self.formula.calc(keylen,datalen)
        newused=used+self.formula.block_used
        if newused>self.rlen:
            trkbaln=0
        else:
            trkbaln=self.rlen-newused
        fit=(used+self.formula.last_used)<=self.rlen
        return (newused,fit,trkbaln)
    def devhdr(self):
        # returns a device header (512 bytes)
        # Bytes    Content
        #  0-7  =  Device ID (ASCII 'CKD_P370')
        #  8-11 =  heads (little-endian)
        # 12-15 =  track size (little-endian)
        #  16   =  last two digits of device type
        #  17   =  sequence number (0 for only one image file)
        # 18-19 =  high cylinder (little-endian, 0 for last image file)
        # 20-512=  492 reserved bytes
        #
        # tracksize=sizeof(trkhdr)      HA              (5 bytes)
        #          +sizeof(rechdr)+8    R0              (5+16=21 bytes)
        #          +sizeof(rechdr)+r1   R1 max. size    (21+8=29+r1 bytes)
        #          +8                   eight 0xFF's    (8+29=37+r1 bytes
        # tracksize is rounded up to the next full 512 bytes
        #
        hdr=struct.pack(ckdev.devfmt,\
                        ckdev.hdrID,\
                        self.eheads,\
                        self.etrksize,\
                        self.devtyp,\
                        "\x00",
                        0)
        return "%s%s" % (hdr,492*"\x00")
    def lfs(self):
        # This method determines if Large File System is required for this
        # device.  It uses the same rules as Hercules dasdutil.c create_ckd().
        cylsize=self.ecyl*self.etrksize
        maxcyls=(0x7FFFFFFF-512+1)//cylsize
        return maxcyls<self.ecyl
    def read(self,fo,cyl,head,debug=False,dump=False):
        # reads a track from the image file
        pos=self.__file_pos(self.__rel_track(cyl,head))
        fo.seek(pos)
        trk=fo.read(self.etrksize)
        if debug:
            string="ckdutil.py: debug: ckdev.read: " \
                "CYL %s HEAD %s at file pos 0x%x:" \
                % (cyl,head,pos)
            if dump:
                string="%s\n%s" % (string,\
                    hexdump.dump(trk,start=0,indent="    "))
            print string
        return track.parse(trk,self,debug=debug)
    def records(self,keylen,datalen):
        # Returns the number of records of this size that will fit on a track
        b1,b2,nrecs=self.method(keylen,datalen)
        return nrecs
    def write(self,fo,trk,debug=False,dump=False):
        # This method writes a track to an image file.
        if not isinstance(trk,track):
            raise TypeError("trk not a track instance: %s" %trk)
        data=trk.pack(debug=debug)
        if len(data)!=self.etrksize:
            raise IndexError(\
                "track size incompatible with device track size %s : %s" \
                % (self.etrksize,len(data)))
        pos=self.__file_pos(self.__rel_track(trk.cyl,trk.head))
        if debug:
            string="ckdutil.py: debug: ckdev.write: " \
                "CYL %s HEAD %s updated at file pos 0x%x:" \
                % (trk.cyl,trk.head,pos)
            if dump:
                string="%s\n%s" % (string,\
                    hexdump.dump(data,start=0,indent="    "))
            print string
        try:
            fo.seek(pos)
        except IOError:
            raise IOError("could not seek to trk (%s,%s) file pos: %s" \
                % (trk.cyl,trk.head,pos))
        fo.write(data)

class devcap(object):
    # This class and its subclasses abstract the capacity calculation 
    # for real CKD DASD devices.  Without these calculations, a Python program
    # can create an emulated CKD DASD with data stored in ways incompatible
    # with operating systems current during the period when the device was
    # in common usage.  In addition, vintage operating system Logical 
    # Input/Output Control System utilizes data dependent upon these 
    # formulats for the construction of Volume Table of Contents records.
    # These classes support these various capacity calculations.
    def __init__(self,f1,f2,f3,f4,f5,f6,tracklen):
        # Factors used in the formulas that determine track capacity on
        # a specific CKD DASD architecture.  Actual manuals for the real
        # devices must be consulted, if available, to determine the actual
        # meaning of the various factors for that device architecture and the
        # mathematical formulas for that architecture.  This class and 
        # related subclasses are derived from the Hercules devtab.c module
        # capacity_calc function.
        self.f1=f1
        self.f2=f2
        self.f3=f3
        self.f4=f4
        self.f5=f5
        self.f6=f6
        self.tracklen=tracklen
        # All of the following attributes are set by the calc() method
        # Physical Record related values
        self.klen=0             # key length used to calculate these values
        self.dlen=0             # data length used to calculate these values
        self.last_used=0        # b1 in C formulas
        self.block_used=0       # b2 in C formulas
        # Dataset related values
        self.NUMRECS=0
        self.DEVI=0
        self.DEVL=0
        self.DEVK=0
        self.DEVTL=0
        self.DEVFG=0
    # Over the decades of CKD device manufacture, numerous technologies have
    # been used.  Each type of technology has its own factors and formulas
    # used to determine track capacity.  The four subclasses of this base
    # class provide access to these calculations.  Each of the subclasses
    # is based upon the formulas in Hercules dasdutil.c module.
    def calc(self,klen,dlen):
        # This method performs the appropriate calculations for a CKD DASD
        # device.  Each subclass must provide this method setting the various
        # properties.
        raise NotImplementedError("class %s must provide calc() method" \
            % self.__class__.__name__)

class neg_1(devcap):
    # Capacity calculations for 2305, 3330, 3340 and 3350 CKD DASD devices
    def __init__(self,f1,f2,f3,f4,f5,f6,tracklen):
        devcap.__init__(self,f1,f2,f3,f4,f5,f6,tracklen)
    def calc(self,klen=0,dlen=0):
        self.klen=klen
        self.dlen=dlen
        # Returns (b1,b2,numrecs)
        # Formulas for 3330,3340,3350 from Hercules dasdutil.c capacity_calc()
        #
        # c = ckd->f1; x = ckd->f2;
        # b1 = b2 = keylen + datalen + (keylen == 0 ? 0 : c) + x;
        if klen==0:
            self.last_used=dlen+self.f2
        else:
            self.last_used=klen+dlen+self.f1+self.f2
        # b2=b1
        self.block_used=self.last_used
        # nrecs = trklen / b2;
        self.NUMRECS=self.tracklen // self.block_used
        # devi = c + x; devl = c + x; devk = c; devtl = 512;
        # devfg = 0x01;
        self.DEVI=self.f1+self.f2
        self.DEVL=self.DEVI
        self.DEVK=self.f1
        self.DEVTL=512
        self.DEVFG=0x01

class neg_2(devcap):
    # Capacity calculations for 2311 and 2314 CKD DASD devices
    def __init__(self,f1,f2,f3,f4,f5,f6,tracklen):
        devcap.__init__(self,f1,f2,f3,f4,f5,f6,tracklen)
    def calc(self,klen=0,dlen=0):
        self.klen=klen
        self.dlen=dlen
        #
        # c = ckd->f1; x = ckd->f2; d1 = ckd->f3; d2 = ckd->f4;
        # b1 = keylen + datalen + (keylen == 0 ? 0 : c);
        # b2 = ((keylen + datalen) * d1 / d2)
        #         + (keylen == 0 ? 0 : c) + x;
        if klen==0:
            self.last_used=dlen
            self.block_used=(dlen*self.f3 // self.f4)+self.f2
        else:
            self.last_used=klen+dlen+self.f1
            self.block_used=((keylen+datalen)*self.f3 // self.f4)\
                 +self.f1+self.f2
        # nrecs = (trklen - b1)/b2 + 1;
        self.NUMRECS=((self.tracklen-self.last_used) // self.block_used)+1
        # devi = c + x; devl = c; devk = c; devtl = d1 / (d2/512);
        # devfg = 0x01;
        #
        self.DEVI=self.f1+self.f2
        self.DEVL=self.f1
        self.DEVK=self.f1
        self.DEVTL=self.f3 // (self.f4//512)
        self.DEVFG=0x01

class pos_1(devcap):
    # Capacity calculations for 3375 and 3380 CKD DASD devices
    def __init__(self,f1,f2,f3,f4,f5,f6,tracklen):
        devcap.__init__(self,f1,f2,f3,f4,f5,f6,tracklen)
    def calc(self,klen=0,dlen=0):
        self.klen=klen
        self.dlen=dlen
        #
        # f1 = ckd->f1; f2 = ckd->f2; f3 = ckd->f3;
        # fl1 = datalen + f2;
        fl1=dlen+self.f2
        # fl2 = (keylen == 0 ? 0 : keylen + f3);
        if klen==0:
            fl2=0
        else:
            fl2=klen+self.f3
        # fl1 = ((fl1 + f1 - 1) / f1) * f1;
        fl3=((fl1+self.f1-1)//self.f1)*self.f1
        # fl2 = ((fl2 + f1 - 1) / f1) * f1;
        fl4=((fl2+self.f1-1)//self.f1)*self.f1
        # b1 = b2 = fl1 + fl2;
        self.last_used=fl3+fl4
        self.block_used=self.last_used
        # nrecs = trklen / b2;
        self.NUMRECS=self.tracklen // self.block_used
        # devi = 0; devl = 0; devk = 0; devtl = 0; devfg = 0x30;
        self.DEVI=0
        self.DEVL=0
        self.DEVK=0
        self.DEVTL=0
        self.DEVFG=0x30

class pos_2(devcap):
    # Capacity calculations for 3375 and 3380 CKD DASD devices
    def __init__(self,f1,f2,f3,f4,f5,f6,tracklen):
        devcap.__init__(self,f1,f2,f3,f4,f5,f6,tracklen)
    def calc(self,klen=0,dlen=0):
        self.klen=klen
        self.dlen=dlen
        # Formulas for 3390, 9345 from Hercules dasdutil.c capacity_calc()
        #
        # f1 = ckd->f1; f2 = ckd->f2; f3 = ckd->f3;
        # f4 = ckd->f4; f5 = ckd->f5; f6 = ckd->f6;
        # int1 = ((datalen + f6) + (f5*2-1)) / (f5*2);
        i1=((dlen+self.f6)+((self.f5*2)-1)) // (self.f5*2)
        # int2 = ((keylen + f6) + (f5*2-1)) / (f5*2);
        i2=((klen+self.f6)+((self.f5*2)-1)) // (self.f5*2)
        # fl1 = (f1 * f2) + datalen + f6 + f4*int1;
        fl1=(self.f1*self.f2)+dlen+self.f6+(self.f4*i1)
        # fl2 = (keylen == 0 ? 0 : (f1 * f3) + keylen + f6 + f4*int2);
        if klen==0:
            fl2=0
        else:
            fl2=(self.f1*self.f3)+klen+self.f6+(self.f4*i2)
        # fl1 = ((fl1 + f1 - 1) / f1) * f1;
        fl3=((fl1+self.f1-1) // self.f1) * self.f1
        # fl2 = ((fl2 + f1 - 1) / f1) * f1;
        fl4=((fl2+self.f1-1) // self.f1) * self.f1
        # b1 = b2 = fl1 + fl2;
        self.last_used=fl3+fl4
        self.block_used=self.last_used
        # nrecs = trklen / b2;
        self.NUMRECS=self.tracklen // self.block_used
        # devi = 0; devl = 0; devk = 0; devtl = 0; devfg = 0x30;
        self.DEVI=0
        self.DEVL=0
        self.DEVK=0
        self.DEVTL=0
        self.DEVFG=0x30

class home(object):
    # This class abstracts the track home address
    hdrsize=5
    def parse(trkimg,debug=False):
        header=trkimg[:home.hdrsize]
        bin,cyl,head=struct.unpack(ckdev.trkfmt,header)
        if debug:
            print "ckdutil.py: debug: home.parse: " \
                "HOME BIN=0x%02X CYL=%s HEAD=%s" \
                % (ord(bin),cyl,head)
        if bin!="\x00":
            raise ValueError("invalid home address for track: (%s,%s)" \
                % (cyl,head))
        ha=home(cyl,head)
        return (ha,trkimg[home.hdrsize:])
    parse=staticmethod(parse)
    def __init__(self,cyl,head):
        self.cyl=cyl
        self.head=head
    def __str__(self):
        return "ckdutil.home(cyl=%s,head=%s)" % (self.cyl,self.head)
    def pack(self):
        # returns a track header (5 bytes)
        # Bytes    Content
        #   0   =  0x00
        #  1,2  =  cyl (big-endian)
        #  3,4  =  head (big-endian)
        # 
        return struct.pack(ckdev.trkfmt,"\x00",self.cyl,self.head)
    def vsize(self):
        return home.hdrsize

class record(object):
    # This class abstracts a CKD record
    hdrsize=8
    def parse(trkimg,debug=True):
        header,trk=track.sever(trkimg,record.hdrsize)
        cyl,head,rec,klen,dlen=struct.unpack(ckdev.recfmt,header)
        rec=ord(rec)
        klen=ord(klen)
        if debug:
            print "ckdutil.py: debug: record.parse: " \
                "Record CYL=%s HEAD=%s REC=%s key=%s data=%s" \
                % (cyl,head,rec,klen,dlen)
        key=""
        data=""
        if klen!=0:
            key,trk=track.sever(trk,klen)
        if dlen!=0:
            data,trk=track.sever(trk,dlen)
        r=record(cyl,head,rec,key=key,data=data)
        return (r,trk)
    parse=staticmethod(parse)
    def __init__(self,cyl,head,rec,key="",data=""):
        self.cyl=cyl
        self.head=head
        self.rec=rec
        self.key=key
        self.data=data
    def __str__(self):
        return "ckdutil.record(cyl=%s,head=%s,rec=%s,key_len=%s,data_len=%s)"\
            % (self.cyl,self.head,self.rec,len(self.key),len(self.data))
    def pack(self):
        return self.rechdr()+self.key+self.data
    def rechdr(self):
        # returns a record header (8 bytes)
        # Bytes    Content
        #  0,1  =  cyl (big-endian)
        #  1,2  =  head (big-endian)
        #   4   =  rec
        #   5   =  key length
        #  6,7  =  data length
        #
        return struct.pack(ckdev.recfmt,self.cyl,self.head,chr(self.rec),\
             chr(len(self.key)),len(self.data))
    def update(self,data=""):
        newdata=data
        pad=len(self.data)-len(data)
        if pad>0:
            pad=pad*"\x00"
            newdata="%s%s" % (newdata,pad)
        self.data=newdata[:len(self.data)]
    def vsize(self):
        return record.hdrsize+len(self.key)+len(self.data)
        
class track(object):
    # This class abstracts a CKD track image
    eightFF=8*"\xFF"
    r0data=8*"\x00"
    def end_of_track(trkimg):
        if len(trkimg)<8:
            raise IndexError("track image truncated: %s" % len(trkimg))
        return trkimg[:8]==track.eightFF
    end_of_track=staticmethod(end_of_track)
    def parse(trkimg,dev,debug=False):
        ha,trk=home.parse(trkimg,debug=debug)
        trko=track(dev,ha.cyl,ha.head,debug=debug)
        while not track.end_of_track(trk):
           r,trk=record.parse(trk,debug=debug)
           trko.add(r,debug=debug)
        return trko
    parse=staticmethod(parse)
    def sever(trkimg,length):
        if length>len(trkimg):
            raise IndexError(\
                "sever length exceeds image length of %s bytes: %s" \
                % (length,len(trkimg)))
        return (trkimg[:length],trkimg[length:])
    sever=staticmethod(sever)
    def __init__(self,dev,cyl,head,r0=False,debug=False):
        self.dev=dev   # ckdev instance for this volume
        #self.reltrk=self.dev.rel_track(cyl,head)
        # Note: ckd manages tracks by relative track number
        self.cyl=cyl
        self.head=head
        self.__start(r0=r0,debug=debug)   # Initialize the track
        self.updated=False   # Flag to indicate if the track has changed
    def __str__(self):
        return "track cyl=%s,head=%s: updated=%s records=%s" \
            % (self.cyl,self.head,self.updated,len(self.recs))
    def __start(self,r0=False,debug=False):
        # starts a new track image.  These are updated by self.add() method
        if debug:
            print("ckdutil.py: debug: track.__start: initializing track (%s,%s)"\
                % (self.cyl,self.head))
        self.recs=[]
        self.eused=0
        self.rused=0
        self.rbal=self.dev.rlen
        ha=home(self.cyl,self.head) # track home address
        if not self.add(ha,debug=debug):
            raise ValueError("Could not add home on track: (%s,%s)" \
                % (self.cyl,self.head))
        if not r0:
            return
        r0=record(self.cyl,self.head,0,data=track.r0data)  # Standard R0
        if not self.add(r0,debug=debug):
            raise ValueError("Could not add r0 on track: (%s,%s)" \
                % (self.cyl,self.head))
    def add(self,rec,warn=False,force=False,debug=False):
        # Trys to add a record to the track. Returns True/False
        if debug:
            print("ckdutil.py: debug: track.add: adding to track (%s,%s) "
                "records=%s: %s" \
                % (self.cyl,self.head,len(self.recs),rec))
        rused=self.rused
        rbal=self.rbal
        if isinstance(rec,record) and rec.rec!=0:
            # capacity calculations implicitly include HA and R0.
            # Only call capacity calcuations for user records.
            rused,fit,rbal=self.dev.capacity(rused,len(rec.key),len(rec.data))
            if not fit:
                if warn:
                    print "WARNING: Could not add record %s on track " \
                         "(%s,%s): real used=%s, real balance=%s" \
                         % (rec.rec,self.cyl,self.head,rused,rbal)
                if not force:
                    return False
        size=rec.vsize()
        if self.eused+size>self.dev.etrksize:
            if warn:
                print "WARNING: Could not add record %s on track (%s,%s), " \
                    "maximum track size %s exceeded: %s" \
                    % (rec.rec,self.cyl,self.head,self.dev.etrksize,\
                    self.eused+size)
            return False
        self.recs.append(rec)
        self.eused+=size
        self.rused=rused
        self.rbal=rbal
        if debug:
            print("ckdutil.py: debug: track.add: added to track (%s,%s) " \
                "records=%s: %s" \
                % (self.cyl,self.head,len(self.recs),rec))
        return True
    def pack(self,debug=False):
        if debug:
            print("ckdutil.py: debug: track.pack: "\
                "creating track image for (%s,%s): records=%s" \
                % (self.cyl,self.head,len(self.recs)))
        size=self.dev.etrksize
        image=""
        for x in self.recs:
            if debug:
                print("ckdutil.py: debug: track.pack: %s" % x)
            image="%s%s" % (image,x.pack())
        image="%s%s" % (image,track.eightFF)
        if len(image)>size:
            raise ValueError("packed track larger than track image %s: %s" \
                % (size,len(image)))
        pad=size-len(image)
        image+=pad*"\x00"
        return image
    def read(self,recno):
        for x in self.recs:
            if isinstance(x,record) and x.rec==recno:
                return x
        return None  # Not found
    def update(self,recno,data=""):
        # updates the data of a record.  Returns True/False
        for x in range(len(self.recs)):
            r=self.recs[x]
            if isinstance(r,record) and r.rec==recno:
                r.update(data)
                self.updated=True
                return True
        return False
    def write(self,rec,debug=False):
        # Writes a new record on the track.  Returns True/False
        if not isinstance(rec,record):
            raise TypeError("track.update requires record instance: %s" % rec)
        for x in range(len(self.recs)):
            r=self.recs[x]
            if isinstance(r,home):
                continue
            if isinstance(r,record) and r.rec<rec.rec:
                continue
            break
        if x==len(self.recs)-1:
            succeeded=self.add(rec,warn=debug,debug=debug)
        else:
            newtrk=self.recs[2:x+1]  # Ignore home and r0 instances
            self.__start(debug=debug)
            for x in newtrk:
                if not self.add(x,warn=debug,debug=False):
                    raise IndexError(
                        "Could not add to track (%s,%s) image record: %s" \
                        % (x.cyl,x.head,x.rec))
            succeeded=self.add(rec,warn=debug,debug=debug)
        if succeeded:
            self.updated=True
        return succeeded

# Now that helper classes are built, check the struct module formats
ckdev.ckfmt(ckdev.devfmt,"devfmt",ckdev.hdrsize)
ckdev.ckfmt(ckdev.recfmt,"recfmt",record.hdrsize)
ckdev.ckfmt(ckdev.trkfmt,"trkfmt",home.hdrsize)
        
#static CKDDEV ckdtab[] = {
#/* name         type model clas code prime a hd    r0    r1 har0   len sec    rps  f f1  f2   f3   f4 f5 f6  cu */
# {"2305",      0x2305,0x00,0x20,0x00,   48,0, 8,14568,14136, 432,14568, 90,0x0000,-1,202,432,  0,   0,  0,0,"2835"},
# {"2305-1",    0x2305,0x00,0x20,0x00,   48,0, 8,14568,14136, 432,14568, 90,0x0000,-1,202,432,  0,   0,  0,0,"2835"},
# {"2305-2",    0x2305,0x02,0x20,0x00,   96,0, 8,14858,14660, 198,14858, 90,0x0000,-1, 91,198,  0,   0,  0,0,"2835"},
#
# {"2311",      0x2311,0x00,0x20,0x00,  200,3,10,    0, 3625,   0, 3625,  0,0x0000,-2,20, 61, 537, 512,  0,0,"2841"},
# {"2311-1",    0x2311,0x00,0x20,0x00,  200,3,10,    0, 3625,   0, 3625,  0,0x0000,-2,20, 61, 537, 512,  0,0,"2841"},
#
# {"2314",      0x2314,0x00,0x20,0x00,  200,3,20,    0, 7294,   0, 7294,  0,0x0000,-2,45,101,2137,2048,  0,0,"2314"},
# {"2314-1",    0x2314,0x00,0x20,0x00,  200,3,20,    0, 7294,   0, 7294,  0,0x0000,-2,45,101,2137,2048,  0,0,"2314"},
#
# {"3330",      0x3330,0x01,0x20,0x00,  404,7,19,13165,13030, 135,13165,128,0x0000,-1,56,135,   0,   0,  0,0,"3830"},
# {"3330-1",    0x3330,0x01,0x20,0x00,  404,7,19,13165,13030, 135,13165,128,0x0000,-1,56,135,   0,   0,  0,0,"3830"},
# {"3330-2",    0x3330,0x11,0x20,0x00,  808,7,19,13165,13030, 135,13165,128,0x0000,-1,56,135,   0,   0,  0,0,"3830"},
# {"3330-11",   0x3330,0x11,0x20,0x00,  808,7,19,13165,13030, 135,13165,128,0x0000,-1,56,135,   0,   0,  0,0,"3830"},
#
# {"3340",      0x3340,0x01,0x20,0x00,  348,1,12, 8535, 8368, 167, 8535, 64,0x0000,-1,75,167,   0,   0,  0,0,"3830"},
# {"3340-1",    0x3340,0x01,0x20,0x00,  348,1,12, 8535, 8368, 167, 8535, 64,0x0000,-1,75,167,   0,   0,  0,0,"3830"},
# {"3340-35",   0x3340,0x01,0x20,0x00,  348,1,12, 8535, 8368, 167, 8535, 64,0x0000,-1,75,167,   0,   0,  0,0,"3830"},
# {"3340-2",    0x3340,0x02,0x20,0x00,  696,2,12, 8535, 8368, 167, 8535, 64,0x0000,-1,75,167,   0,   0,  0,0,"3830"},
# {"3340-70",   0x3340,0x02,0x20,0x00,  696,2,12, 8535, 8368, 167, 8535, 64,0x0000,-1,75,167,   0,   0,  0,0,"3830"},
#
# {"3350",      0x3350,0x00,0x20,0x00,  555,5,30,19254,19069, 185,19254,128,0x0000,-1,82,185,   0,   0,  0,0,"3830"},
# {"3350-1",    0x3350,0x00,0x20,0x00,  555,5,30,19254,19069, 185,19254,128,0x0000,-1,82,185,   0,   0,  0,0,"3830"},
#/* name         type model clas code prime a hd    r0    r1 har0   len sec    rps  f f1  f2   f3   f4 f5 f6  cu */
#
# {"3375",      0x3375,0x02,0x20,0x0e,  959,3,12,36000,35616, 832,36000,196,0x5007, 1, 32,384,160,   0,  0,0,"3880"},
# {"3375-1",    0x3375,0x02,0x20,0x0e,  959,3,12,36000,35616, 832,36000,196,0x5007, 1, 32,384,160,   0,  0,0,"3880"},
# 
# {"3380",      0x3380,0x02,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-1",    0x3380,0x02,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-A",    0x3380,0x02,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-B",    0x3380,0x02,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"}, 
# {"3380-D",    0x3380,0x06,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-J",    0x3380,0x16,0x20,0x0e,  885,1,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-2",    0x3380,0x0a,0x20,0x0e, 1770,2,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-E",    0x3380,0x0a,0x20,0x0e, 1770,2,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-3",    0x3380,0x1e,0x20,0x0e, 2655,3,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"3380-K",    0x3380,0x1e,0x20,0x0e, 2655,3,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"EMC3380K+", 0x3380,0x1e,0x20,0x0e, 3339,3,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
# {"EMC3380K++",0x3380,0x1e,0x20,0x0e, 3993,3,15,47988,47476,1088,47968,222,0x5007, 1, 32,492,236,   0,  0,0,"3880"},
#/* name         type model clas code prime a hd    r0    r1 har0   len sec    rps  f f1  f2   f3   f4 f5 f6  cu */
#
# {"3390",      0x3390,0x02,0x20,0x26, 1113,1,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-1",    0x3390,0x02,0x20,0x26, 1113,1,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-2",    0x3390,0x06,0x20,0x27, 2226,1,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-3",    0x3390,0x0a,0x20,0x24, 3339,1,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-9",    0x3390,0x0c,0x20,0x32,10017,3,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-27",   0x3390,0x0c,0x20,0x32,32760,3,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-J",    0x3390,0x0c,0x20,0x32,32760,3,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-54",   0x3390,0x0c,0x20,0x32,65520,3,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
# {"3390-JJ",   0x3390,0x0c,0x20,0x32,65520,3,15,57326,56664,1428,58786,224,0x7708, 2, 34,19,   9,   6,116,6,"3990"},
#
# {"9345",      0x9345,0x04,0x20,0x04, 1440,0,15,48174,46456,1184,48280,213,0x8b07, 2, 34,18,   7,   6,116,6,"9343"},
# {"9345-1",    0x9345,0x04,0x20,0x04, 1440,0,15,48174,46456,1184,48280,213,0x8b07, 2, 34,18,   7,   6,116,6,"9343"},
# {"9345-2",    0x9345,0x04,0x20,0x04, 2156,0,15,48174,46456,1184,48280,213,0x8b07, 2, 34,18,   7,   6,116,6,"9343"}
#/* name         type model clas code prime a hd    r0    r1 har0   len sec    rps  f f1  f2   f3   f4 f5 f6  cu */

# Build the ckd.geometry dictionary:
ckdev("2305",   0x2305,0x00,0x20,0x00,48,0,8,14568,14136,432,14568,90,0x0000,neg_1,202,432,0,0,0,0,"2835")
ckdev("2305-1", 0x2305,0x00,0x20,0x00,48,0,8,14568,14136,432,14568,90,0x0000,neg_1,202,432,0,0,0,0,"2835")
ckdev("2305-2", 0x2305,0x02,0x20,0x00,96,0,8,14858,14660,198,14858,90,0x0000,neg_1, 91,198,0,0,0,0,"2835")
ckdev("2311",   0x2311,0x00,0x20,0x00,200,3,10,0,3625,0,3625,0,0x0000,neg_2,20,61,537,512,0,0,"2841")
ckdev("2311-1", 0x2311,0x00,0x20,0x00,200,3,10,0,3625,0,3625,0,0x0000,neg_2,20,61,537,512,0,0,"2841")
ckdev("2314",   0x2314,0x00,0x20,0x00,200,3,20,0,7294,0,7294,0,0x0000,neg_2,45,101,2137,2048,0,0,"2314")
ckdev("2314-1", 0x2314,0x00,0x20,0x00,200,3,20,0,7294,0,7294,0,0x0000,neg_2,45,101,2137,2048,0,0,"2314")
ckdev("3330",   0x3330,0x01,0x20,0x00,404,7,19,13165,13030,135,13165,128,0x0000,neg_1,56,135,0,0,0,0,"3830")
ckdev("3330-1", 0x3330,0x01,0x20,0x00,404,7,19,13165,13030,135,13165,128,0x0000,neg_1,56,135,0,0,0,0,"3830")
ckdev("3330-2", 0x3330,0x11,0x20,0x00,808,7,19,13165,13030,135,13165,128,0x0000,neg_1,56,135,0,0,0,0,"3830")
ckdev("3330-11",0x3330,0x11,0x20,0x00,808,7,19,13165,13030,135,13165,128,0x0000,neg_1,56,135,0,0,0,0,"3830")
ckdev("3340",   0x3340,0x01,0x20,0x00,348,1,12,8535,8368,167,8535,64,0x0000,neg_1,75,167,0,0,0,0,"3830")
ckdev("3340-1", 0x3340,0x01,0x20,0x00,348,1,12,8535,8368,167,8535,64,0x0000,neg_1,75,167,0,0,0,0,"3830")
ckdev("3340-35",0x3340,0x01,0x20,0x00,348,1,12,8535,8368,167,8535,64,0x0000,neg_1,75,167,0,0,0,0,"3830")
ckdev("3340-2", 0x3340,0x02,0x20,0x00,696,2,12,8535,8368,167,8535,64,0x0000,neg_1,75,167,0,0,0,0,"3830")
ckdev("3340-70",0x3340,0x02,0x20,0x00,696,2,12,8535,8368,167,8535,64,0x0000,neg_1,75,167,0,0,0,0,"3830")
ckdev("3350",   0x3350,0x00,0x20,0x00,555,5,30,19254,19069,185,19254,128,0x0000,neg_1,82,185,0,0,0,0,"3830")
ckdev("3350-1", 0x3350,0x00,0x20,0x00,555,5,30,19254,19069,185,19254,128,0x0000,neg_1,82,185,0,0,0,0,"3830")
ckdev("3375",   0x3375,0x02,0x20,0x0e,959,3,12,36000,35616,832,36000,196,0x5007,pos_1,32,384,160,0,0,0,"3880")
ckdev("3375-1", 0x3375,0x02,0x20,0x0e,959,3,12,36000,35616,832,36000,196,0x5007,pos_1,32,384,160,0,0,0,"3880")
ckdev("3380",   0x3380,0x02,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-1", 0x3380,0x02,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-A", 0x3380,0x02,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-B", 0x3380,0x02,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-D", 0x3380,0x06,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-J", 0x3380,0x16,0x20,0x0e,885,1,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-2", 0x3380,0x0a,0x20,0x0e,1770,2,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-E", 0x3380,0x0a,0x20,0x0e,1770,2,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-3", 0x3380,0x1e,0x20,0x0e,2655,3,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3380-K", 0x3380,0x1e,0x20,0x0e,2655,3,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("EMC3380K+",0x3380,0x1e,0x20,0x0e,3339,3,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("EMC3380K++",0x3380,0x1e,0x20,0x0e,3993,3,15,47988,47476,1088,47968,222,0x5007,pos_1,32,492,236,0,0,0,"3880")
ckdev("3390",   0x3390,0x02,0x20,0x26,1113,1,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-1", 0x3390,0x02,0x20,0x26,1113,1,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-2", 0x3390,0x06,0x20,0x27,2226,1,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-3", 0x3390,0x0a,0x20,0x24,3339,1,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-9", 0x3390,0x0c,0x20,0x32,10017,3,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-27",0x3390,0x0c,0x20,0x32,32760,3,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-J", 0x3390,0x0c,0x20,0x32,32760,3,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-54",0x3390,0x0c,0x20,0x32,65520,3,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("3390-JJ",0x3390,0x0c,0x20,0x32,65520,3,15,57326,56664,1428,58786,224,0x7708,pos_2,34,19,9,6,116,6,"3990")
ckdev("9345",   0x9345,0x04,0x20,0x04,1440,0,15,48174,46456,1184,48280,213,0x8b07,pos_2,34,18,7,6,116,6,"9343")
ckdev("9345-1", 0x9345,0x04,0x20,0x04,1440,0,15,48174,46456,1184,48280,213,0x8b07,pos_2,34,18,7,6,116,6,"9343")
ckdev("9345-2", 0x9345,0x04,0x20,0x04,2156,0,15,48174,46456,1184,48280,213,0x8b07,pos_2,34,18,7,6,116,6,"9343")

# media.py expects this function to be available
def register_devices(dtypes):
    for x in ckd.geometry.values():
        dtypes.dtype(x.edtype,ckd)
        dtypes.dndex(dtypes.number(x.edevice,x.emodel),x.edtype)

def usage():
    print "/ckdutil.py image_file"

if __name__=="__main__":
    print "ckdutil.py is only intended for import"
    if len(sys.argv)!=2:
        usage()
        sys.exit(1)
    dev=ckd.attach(sys.argv[1],debug=True)
    print dev
    print "seeking to cyl=1,head=1"
    dev.seek(1,1,debug=True,dump=True)
    print "seeking to cyl=46,head=7"
    dev.seek(46,7,debug=True)
    info=ckd_info(dev.dev.edtype,datalen=4096)
    print info