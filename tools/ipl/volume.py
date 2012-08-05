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

# The DASD Volume Standard is implemented by this Python module.
# 
# At its core is the DASDDEFN class.  This class instantiates the processing of
# the standard.  This module may be used as a utility in its own right or as 
# component driven by another utility.
#
# The following device types are supported:
#   CKD - 2305-x, 2311, 2314, 3330-x, 3340-x, 3350, 3375, 3380-x, 3390, 3390-x, 
#         9345-x
#   FBA - 0671, 3310, 3370, 9313, 9332, 9335, 9336

import os
import os.path
import re
import sys
import struct
#import time

# SATK modules
from translate import *       # ASCII-EBCDIC translation tables
from hexdump import *         # Bigendian binary conversion routines
from specfile import *        # Generic specification file handling classes
import media                  # Access the Hercules device emulation support
import ckdutil                # Access CKD emulation support (uncomment to use)
import fbautil                # Access FBA emulation support
import recsutil               # Access to the generic device record classes

def chunk(data,size,pad=False):
    # This method breaks a string 'data' into pieces of 'size' length, the last
    # being truncated or padded as requested by 'pad'.
    chunks=[]
    for x in range(0,len(data),size):
        if x+size<=len(data):
            chunks.append(data[x:x+size])
        else:
            chunks.append(data[x:])
    if pad:
        last=chunks[-1]
        if len(last)!=size:
            last+=size*"\x00"
            chunks[-1]=last[:size]
    return chunks

#def spaces(number,ascii=False):
#    if ascii:
#        return number*"\x20"
#    return number*"\x40"

# This class manages the relationships between physical device type and geometries
# and the DASD Volume Standard block abstraction.  It is used by the DASD class
# to assist in media device record creation.
class BLOCKS(object):
    index={512:0,1024:1,2048:2,4096:3}
    @staticmethod
    def new(dtype,blksize,debug=False):
        # Instantiate a BLOCK subclass for creation of the management of block
        # semantics as appropriate to the device type (dtype).
        if debug:
            print("volume.py - BLOCKS.new(%s,%s,debug=%s)" \
                % (repr(dtype),repr(blksize),debug))
        # Create either a CKD_BLOCKS or FBA_BLOCKS instance.  If the dtype is 
        # not valid for the DASD architecture, a KeyError will be thrown.
        try:
            return CKD_BLOCKS(dtype,blksize,debug=debug)
        except KeyError:
            if debug:
                print("volume.py - BLOCKS.new_dasd - CKD_BLOCKS failed")
        try:
            return FBA_BLOCKS(dtype,blksize,debug=debug)
        except KeyError:
            if debug:
                print("volume.py - BLOCKS.new_dasd - FBA_BLOCKS failed")
        # Neither successful, fail.
        raise ValueError

    def __init__(self,dtype,blksize,debug=False):
        self.dtype=dtype
        self.blksize=blksize
        self.block_factor=self.block_factors[BLOCKS.index[self.blksize]]
        if self.block_factor==0:
            print("volume.py - ERROR - Device type %s does not support a block "
                "size of %s") % (self.dtype,self.blksize)
            raise ValueError
        self.reserve=self.minrsrv()  # Determine the minimum to reserve
        self.nullblk=self.blksize*"\x00"  # An empty block
    def __str__(self):
        return "BLOCKS: %s" % self.device

    def init(self):
        # Initialize variables
        self.block_factors=[0,0,0,0]
        self.cylinders_per_volume=0
        self.tracks_per_cylinder=0
        self.blocks_per_track=0
        self.sectors_per_volume=0
        self.sectors_per_block=0
        self.ckd=False
        self.fba=False
        self.dasdcls=None
        
    def blocks(self,length):
        # This method returns a tuple, the number of blocks required to contain
        # content of 'length' bytes and the number of bytes in the last block.
        blocks,extra = divmod(length,self.blksize)
        if extra==0:
            return (blocks,self.blksize)
        return (blocks+1,extra)

    def dasd(self,vdbr,device,debug=False):
        # This method creates the DASD subclass required for the medium 
        return self.dasdcls(vdbr,device,debug=debug)
        
    def dasd_file(self,start,alloc,blklist=[],debug=False):
        # This method returns a list of physical media records, corresponding
        # to a DASD Volume file starting with block 'start' and allocated for
        # 'alloc' blocks.  The record creation will truncate a file source
        # content is larger than the number of allocated blocks and will pad with
        # blocks of binary zeros if the allocation exceeds the source content 
        # size.  Truncation and padding may occur only if the specification
        # FILE statement for the file contains a size argument.
        if debug:
            print("volume.py - BLOCKS.dasd_file - start=%s,alloc=%s,"
                "len(blklist)=%s" % (start,alloc,len(blklist)))
        recs=[]
        current_content=start
        first_content=start
        last_content=start+len(blklist)-1
        last_file=start+alloc-1
        for x in blklist:
            if len(x)!=self.blksize:
                raise ValueError  # figure out what this should be
            if current_content<=last_file:
                recs=self.record(current_content,x,recs,debug=debug)
                if debug:
                    print("volume.py - BLOCKS.dasd_file - file content len(recs)=%s" \
                        % len(recs))
                current_content+=1
            else:
                break
        for x in range(last_content+1,last_file):
            recs=self.record(x,self.nullblk,recs,debug=False)
            if debug:
                print("volume.py - BLOCKS.dasd_file - file content with pad "
                    "len(recs)=%s" % len(recs))
        if debug:
             print("volume.py - BLOCKS.dasd_file - returning len(recs)=%s"
                 % len(recs))
        return recs

    # These methods must be supplied by the BLOCKS subclass.

    def blk2phys(self,block):
        # Returns in device specific terms the location of a 'block' number
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement blk2phyx method" % (self.__class__.__name__))

    def capacity(self):
        # Returns the total capacity in blocks of the volume
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement capacity method" % (self.__class__.__name__))

    def minrsrv(self):
        # Returns the minimum number of blocks that must be reserved on the volume
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement minrsrv method" % (self.__class__.__name__))
        
    def record(self,block,data,reclist=[],debug=False):
        # Adds a block converted to physical media records to a list of 
        # physical media records.
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement record method" % (self.__class__.__name__))
        
    def vdb_record(self,data,reclist=[],debug=False):
        # Add the physical record corresponding to the VDBR to 'reclist'
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement vdb_record method" % (self.__class__.__name__))
        
    def vdbr_create(self,vdbro,debug=False):
        # Returns a physical media record for the DASD Volume VDBR
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement vdbr_create method" % (self.__class__.__name__))

class CKD_BLOCKS(BLOCKS):
    # Blocks per track:
    #            512  1024  2048  4096
    ckd={"2305":[15,  10,   5,    3],
         "2311":[6,   3,    1,    0],
         "2314":[11,  6,    3,    1],
         "3330":[20,  11,   6,    3],
         "3350":[27,  15,   8,    4],
         "3375":[40,  25,   14,   8],
         "3380":[35,  23,   14,   7],
         "3390":[49,  33,   21,   12],
         "9345":[41,  28,   17,   9]}
    def __init__(self,dtype,blksize,debug=False):
        if debug:
            print("volume.py - CKD_BLOCKS(%s,%s,debug=%s)" \
                % (repr(dtype),repr(blksize),debug))
        self.init()
        dt=dtype[:4]
        if debug:
            print("volume.py - CKD_BLOCKS - trying CKD_BLOCKS.ckd[%s]" \
                    % (repr(dt)))
        self.block_factors=CKD_BLOCKS.ckd[dt]
        if debug:
            print("volume.py - CKD_BLOCKS - self.block_factors=%s" \
                % self.block_factors)
        self.cylinders_per_volume=ckdutil.ckd.size(dtype)
        self.tracks_per_cylinder=ckdutil.ckd.tracks(dtype)
        self.ckd=True
        self.dasdcls=CKD_DASD  # Class used to create DASD instance
        super(CKD_BLOCKS,self).__init__(dtype,blksize,debug=debug)
        self.blocks_per_track=self.block_factor
    def __str__(self):
        return "CKD %s BLOCKS: blksize=%s, cyls=%s, tracks/cyl=%s, blocks/track=%s" \
            % (self.dtype,self.blksize,self.cylinders_per_volume,\
            self.tracks_per_cylinder,self.block_factor)
    def cylinders(self,n):
        # Returns the number of blocks corresponding to the number of cylinders (n)
        return self.tracks(n*self.tracks_per_cylinder)
    def tracks(self,n):
        # Returns the number of blocks corresponding to the number tracks (n)
        return n*self.block_factor
     
    # Methods required of subclasses
    def blk2phys(self,block,debug=False):
        # Returns a tuple (cc,hh,r) corresponding to numbered 'block'
        rel_trk,r = divmod(block,self.blocks_per_track)
        if debug:
            print("volume.py - CKD_BLOCKS.blk2phys - \n" 
                "   rel_trk=%s,r=%s = divmod(block=%s,blocks_per_track=%s)"
                % (rel_trk,r,block,self.blocks_per_track))
        r+=1
        cc,hh = divmod(rel_trk,self.tracks_per_cylinder)
        if debug:
            print("volume.py - CKD_BLOCKS.blk2phys - \n" 
                "   cc=%s,hh=%s = divmod(rel_trk=%s,tracks_per_cylinder=%s)"
                % (cc,hh,rel_trk,self.tracks_per_cylinder))
        return (cc,hh,r)
    def capacity(self):
        return self.cylinders_per_volume\
            *self.tracks_per_cylinder\
            *self.blocks_per_track
    def minrsrv(self):
        return 4  # Ensure each physical record including (0,0,4) is reserved.
    def record(self,block,data,reclist=[],debug=False):
        # Create a single CKD record for a block and concatenate it to 'reclist'
        cc,hh,r = self.blk2phys(block,debug=debug)
        rec=recsutil.ckd(data=data,cc=cc,hh=hh,r=r)
        if debug:
            print("volume.py - CKD_BLOCKS.record - %s" % rec)
        reclist.append(rec)
        return reclist
    def vdb_record(self,vdbro,reclist=[],debug=False):
        # Add the physical record corresponding to the VDBR to 'reclist'
        reclist.append(self.vdbr_create(vdbro,debug=debug))
        return reclist
    def vdbr_create(self,vdbro,debug=False):
        data=vdbro.binary(debug=debug)
        rec=recsutil.ckd(key=data[:4],data=data,cc=0,hh=0,r=4)
        if debug:
            print("volume.py - CKD_BLOCKS.vdbr_create - %s" % rec)
        return rec

class FBA_BLOCKS(BLOCKS):
    def __init__(self,dtype,blksize,debug=False):
        if debug:
            print("volume.py - FBA_BLOCKS(%s,%s,debug=%s)" \
                % (repr(dtype),repr(blksize),debug))
        self.init()
        self.block_factors=[1,2,4,8]
        if debug:
            print("volume.py FBA_BLOCKS - self.block_factors=%s" \
                % self.block_factors)
        self.sectors_per_volume=fbautil.fba.size(dtype)
        self.fba=True
        self.dasdcls=FBA_DASD  # Class used to create DASD instance
        super(FBA_BLOCKS,self).__init__(dtype,blksize,debug=debug)
        self.sectors_per_block=self.block_factor
    def __str__(self):
        return "FBA %s BLOCKS: blksize=%s, sectors/block=%s" \
            % (self.dtype,self.blksize,self.block_factor)
    def sectors(self,n,debug=False):
        # Returns the number of blocks corresponding to a number of sectors (n)
        if debug:
            print("FBA_BLOCKS.sectors - self.block_factor=%s" % self.block_factor)
        return (n+self.block_factor-1)//self.block_factor

    # Methods required of subclasses
    def blk2phys(self,block):
        # Returns the starting sector number of 'block'
        return block*self.sectors_per_block
    def capacity(self):
        # Returns the total capacity in blocks for the volume
        return self.sectors_per_volume/self.sectors_per_block
    def minrsrv(self):
        # Return the number of blocks to reserve sectors 0 and 1.
        return self.sectors(2)
    def record(self,block,data,reclist=[],debug=False):
        # return a list of sectors with sector numbers for block
        sec=self.blk2phys(block)
        secs=chunk(data,512,pad=True)
        sectors=[]
        for x in secs:
            sectors.append(recsutil.fba(data=x,sector=sec))
            sec+=1
        if debug:
            for x in sectors:
                print("volume.py - FBA_BLOCKS.record - %s" % x)
        reclist.extend(sectors)
        return reclist
    def vdb_record(self,vdbro,reclist=[],debug=False):
        # Add the physical record corresponding to the VDBR to 'reclist'
        reclist.append(self.vdbr_create(vdbro,debug=debug))
        return reclist
    def vdbr_create(self,vdbro,debug=False):
        data=vdbro.binary(debug=debug)
        rec=recsutil.fba(data=data,sector=1)
        if debug:
            print("volume.py - FBA_BLOCKS.vdbr_create - %s" % rec)
        return rec

# This class manages the physcial DASD volume and the placing of content on
# volume.
class DASD(object):
    def __init__(self,vdbr,device,debug=False):
        if debug:
            print("volume.py - \n   DASD(vdbr=<%s>,\n   device=<%s>,"
                "\n   debug=%s)" % (vdbr,device,debug))
        self.vdbr=vdbr            # VDBR instance (contains FDS list and VCF FDS)
        self.device=device        # media.py device instance
        self.debug=debug
        
        # Provided by vdbr.records method
        self.recs=[]              # List of medium physical records
        # When constructed, self.recs will contain medium records in this sequence:
        #   1.  The Volume Definition Block Record, self.recs[0]
        #   2.  records for each of the DASD Volume files
        #   3.  records for the Volume Content File (pointed to by the VDBR)
        # The last record of the list represents the volume's high water mark
        # used to determine its minimum size.

        # Determine the number of blocks to allocate for each file.  The size may
        # be explicitly set by the FILE or VOLUME statement.
        
        if debug:
            print("\nvolume.py - DASD.__init__ - DASD file sizing: started")
        self.vdbr.required_sizes(self.debug)
        if debug:
            print("volume.py - DASD.__init__ - DASD file sizing: completed")
        # The required number of blocks for the VCF and each FDS is now known.
        
        if debug:
            print("\nvolume.py - DASD.__init__ - DASD file allocations: started")
        self.vdbr.allocate(self.debug)
        if debug:
            print("volume.py - DASD.__init__ - DASD file allocations: completed")
            
        # Convert the files' content into DASD Volume blocks
        if debug:
            print("\nvolume.py - DASD.__init__ - DASD block content: started")
        self.vdbr.content(debug=self.debug)
        if debug:
            print("volume.py - DASD.__init__ - DASD block content: completed")
    
        # Convert the files' DASD volume blocks into physical medium records:
        # VDBR.records               Creates records for each file and the VCF
        #     FDS.records            Returns the records for its file's content
        #         BLOCKS.dasd_file   Returns each block as medium record(s) list
        #             BLOCKS.record  Adds individual medium record(s) to a list
        if debug:
            print("\nvolume.py - DASD.__init__ - medium content creation: started")
        self.recs=self.vdbr.records(debug=self.debug)
        if self.debug:
            print("volume.py - %s - volume content physical records: %s\n" \
                % (self.__class__.__name__,len(self.recs)))
            self.display()
        if debug:
            print("volume.py - DASD.__init__ - medium content creation: completed")
    # These methods must NOT be overriden by any subclass
    
    def display(self):
        # Output volume content information
        self.vdbr.display()
    
    def minimize(self,comp=False):
        # Based upon existing medium records, minimize the size and reflect it
        # in an updated VDB record
        last_rec=self.recs[-1]
        size=self.device.query_size(last=self.recs[-1],comp=comp)
        rec=self.vdb_update(size,debug=self.debug)
        if self.debug:
            print("volume.py - DASD.minimize - updated VDBR: %s" % rec)
        self.recs[0]=rec
        if self.debug:
            print("volume.py - %s - VDBR updated for minimized volume" \
                % self.__class__.__name__)

    def records2device(self,debug=False):
        # Pass the records to the device instance
        index=0
        for x in self.recs:
            try:
                if debug:
                    print(x.dump())
                self.device.record(x)
            except TypeError:
                raise TypeError("record index %s, not a valid device record: %s"\
                    % (index,x))
            index+=1

    def records2external(self,debug=False):
        if debug:
            print("volume.py - DASD.records2external - returning medium "
                "records: %s" % len(self.recs))
        return self.recs

    # This method must be supplied by subclasses
    
    def vdb_update(self,size,debug=False):
        # Return an updated VDBR instance based upon 'size'
        raise NotImplementedError("volume.py - INTERNAL - subclass %s must "
            "implement vdb_update method" % (self.__class__.__name__))

class CKD_DASD(DASD):
    def __init__(self,vdbr,device,debug=False):
        super(CKD_DASD,self).__init__(vdbr,device,debug=debug)
    # Required subclass method
    def vdb_update(self,size,debug=False):
        # Return arecord instance containing an update CKD VDBR
        return self.vdbr.update_ckd(size)
        
class FBA_DASD(DASD):
    def __init__(self,vdbr,device,debug=False):
        super(FBA_DASD,self).__init__(vdbr,device,debug=debug)
    # Required subclass method
    def vdb_update(self,size,debug=False):
        # Return arecord instance containing an update FBA VDBR
        return self.vdbr.update_fba(size)
        

# This class defines the volume's content.  When used by another utility,
# the class instantiation arguments that override the specification file are
# provided by the utility when creating this class instance.  When used locally
# this class must only be instantiated with the command line supplied specification
# file without overrides.
# 
# Errors in the specification file will result in a ValueError exception
# being thrown during instantiation of the DASDDEFN class instance.
#
# A user of the DASDDEFN class will utilize one of two instance methods:
#   contruct() - Establishes the DASD Standard structures as class instances and
#                returns a set of recsutil record instances that can be used to
#                build the DASD volume content.  The externally supplied handler
#                is used to add records to the device.
#   create()   - Output a DASD image with the specified content.  This method is
#                used by this utility to build a DASD image itself with just the
#                content specified in the specification file.  It will instantiate
#                its own handler and create the DASD image.
class DASDDEFN(object):
    def __init__(self,specfile,filename=None,reserve=None,cyl=None,trk=None,\
       sec=None,minimize=None,compress=None,device=None,debug=False):
        self.specpath=specfile  # Specification file path
        self.filename=filename  # Emulated device file name overrides specfile
        self.reserve=reserve    # External override of volume reserved blocks
        self.minimize=minimize  # External override of the volume creation size
        self.compress=compress  # External override to force compressability
        self.cyl=cyl            # External override of reserved CKD cylinders
        self.trk=trk            # External override of reserved CKD tracks
        self.sec=sec            # External override of reserved FBA sectors
        self.debug=debug        # Generate debug output if True
        
        self.device=device      # Externally supplied media.device instance
        # If None is supplied a media.py device instance will be provided by
        # the device_type method.
        
        # Validate that a valide media.py device instance was provided.
        if self.device is not None:
            if not isinstance(self.device,media.device):
                raise ValueError("volume.py - INTERNAL - media.device instance "
                    "required, encountered %s" % self.device)
        
        # Specification file statement information as Python class instances
        self.content=None       # A CONTENT instance
        self.volume=None        # The VOLUME instance
        self.files=[]           # List of a volume's FILE instances
        # DASD creation instance
        self.blocks=None        # BLOCKS subclass instance
        self.dasd=None          # DASD subclass instance as created by BLOCKS.dasd

        if self.debug:
            print("volume.py - DEBUG - DASDDEFN(%s,filename=%s,reserve=%s,"\
                "minimize=%s,device=%s,debug=%s)" % \
                (specfile,filename,reserve,device,minimize,debug))
        
        try:
            if debug:
                print("\nvolume.py - DASDDEFN.__init__ - specfile.py subclass "
                    "initialization: starting")
            self.content=CONTENT(debug=self.debug)
            if debug:
                print("volume.py - DASDDEFN.__init__ - specfile.py subclass "
                    "initialization: completed")
            
            if debug:
                print("\nvolume.py - DASDDEFN.__init__ - specification file "
                    "processing: started")
            self.content.process(self.specpath,debug=self.debug)
            if debug:
                print("volume.py - DASDDEFN.__init__ - specification file "
                    "processing: completed")
        except IOError:
            print("volume.py - ERROR - could not read specification file: %s" \
                % self.specpath)
            raise ValueError   # DASDDEFN instantiation failed

        self.volume=self.content.volume
        self.files=self.content.files
        self.program=self.content.program
        
        if self.volume is None:
            print("volume.py - ERROR - required specification statement missing: "\
                "VOLUME")
            raise ValueError

        # Update the specifications with external overrides
        if self.debug:
            print("%s" % self.volume)
        
        # Validate device type and block size
        if debug:
            print("\nvolume.py - DASDDEFN.__init__ - device and block size "
                "validation: started")
        self.blocks=self.device_type(debug=self.debug)
        if self.debug:
            print("volume.py - DASDDEFN.__init__ - %s" % self.blocks)
            print("volume.py - DASDDEFN.__init__ - device and block size "
                "validation: completed")
            
        self.override("file",self.filename)
        self.override("reserve",self.reserve)
        self.override("cyl",self.cyl)
        self.override("trk",self.trk)
        self.override("sec",self.sec)
        self.override("minimize",self.minimize)
        self.override("compress",self.compress)
        # Supply the specfile path for use in creating VCF FDS instance
        self.override("source",self.specpath)
        # Calculate blocks specified for reserve based upon the input values.
        # 'reserve' is set to the maximum blocks indicated.
        self.volume.reserve_update(self.blocks)
        
        # Specification file processing is now complete
        if self.debug:
            print("\nvolume.py - VOLUME and FILE instance values:")
            print("%s" % self.volume)
            for x in self.files:
                print("%s" % x)
        # Specification file processing is now complete
            
    def construct(self,external=False,debug=False):
        # Build the DASD Volume Standard structures as Python instances used by the
        # construct method to build the DASD class instance.
        vcf=[]
        blksize=self.volume.values["blksize"]
        for x in self.files:
            fds=FDS(x.values,blksize)
            try:
                fds.host()
            except ValueError:
                print("volume.py - WARNING - problem accessing host file, "
                    "ignoring: %s" % fds.source)
                continue
            vcf.append(fds)
        # Merge PROGRAM statement values with the VOLUME statement
        self.volume.values["data"]=None     # Indicate no program data
        self.volume.values["struct"]=None   # Indicate no struct data
        if not self.program is  None:
            for x in self.program.values.keys():
                self.volume.values[x]=self.program.values[x]
        vdbr=VDBR(self.volume.values,self.blocks,vcf)
        if debug:
            print("\nvolume.py - DASDDEFN.construct - VBDR:\n%s" % vdbr)
            
        # The instantiation of the DASD subclass instance by BLOCKS.dasd does all 
        # of the heavy lifting of the volume creation process.  Within the DASD
        # subclass, the VDBR instance actually does the work.
        
        if debug:
            print("\nvolume.py - DASDDEFN.contruct - DASD volume content "
                "creation: started")
        self.dasd=self.blocks.dasd(vdbr,self.device,debug=debug)

        if self.volume.values["minimize"]:
            self.dasd.minimize(comp=self.volume.values["compress"])
        if debug:
            print("\nvolume.py - DASDDEFN.contruct - DASD volume content "
                "creation: completed")
        
        # At this point, all of the content block allocations have been made.
        # The FDS entries contain all of the information for their content.
        # All of the content of the DASD Volume files has been coverted into block 
        # images.  The VDBR has been updated if necesary
        
        if debug:
            print("\nvolume.py - DASDDEFN.construct - Volume content summary:")
            self.dasd.display()
        
        # Return the final content to external source
        if external:
            return self.dasd.records2external(debug=debug)

    def create(self,debug=False):
        self.construct(debug=debug)
        if debug:
            print("\nvolume.py - DASDDEFN.create - physical volume creation: "
                "started")

        # Pass the final content to media.py device
        if debug:
             print("volume.py - DASDDEFN.create - medium record "
                 "processing: started")
        self.dasd.records2device(debug)
        if debug:
            print("volume.py - DASDDEFN.create - medium record "
                "processing: completed")

        path=self.volume.values["file"]
        minimize=self.volume.values["minimize"]
        compress=self.volume.values["compress"]
        
        if path is None:
            print("volume.py - ERROR - device emulation file path missing")
            return

        if self.debug:
            print("volume.py - DASDDEFN.create - "
                "%s.create(path=%s,mimimize=%s,comp=%s,progress=%s,debug=%s)" \
                % (self.device.__class__.__name__,path,minimize,compress,\
                debug,self.debug))
        self.device.create(path=path,minimize=minimize,comp=compress,\
            progress=debug,debug=self.debug)
        if debug:
            print("volume.py - DASDDEFN.create - physical volume creation: "
                "completed\n")
        print("volume.py - DASD Volume successfully created: %s" % path)
        
    # Process the device type either from a supplied handler or create one from
    # the VOLUME statement's device type.  Validate blocksize.
    def device_type(self,debug=False):
        if not isinstance(self.device,media.device):
            try:
                dtype=self.volume.values["type"]
                if debug:
                    print("volume.py - DASDDEFN.device_type - trying media.device"
                        "(%s,%s)" % (dtype,debug))
                self.device=media.device(dtype,debug=debug)
            except ValueError:
                print("volume.py - ERROR - unrecognized device type: %s" \
                    % dtype)
                raise ValueError
        dtype=self.device.dtype
        blksize=self.volume.values["blksize"]
        try:
            if debug:
                print("volume.py - DASDDEFN.device_type - trying BLOCKS.new"
                    "(%s,%s,debug=%s)" % (dtype,blksize,debug))
            return BLOCKS.new(dtype,blksize,debug=debug)
        except ValueError:
            print("volume.py - ERROR - unsupported device, %s, or block size, %s" \
                % (dtype,blksize))
            raise ValueError
        
    # Overrides or adds an argument and its value in the VOLUME instance
    def override(self,arg,value):
        if value is None:
            return
        self.volume.values[arg]=value

# DASD Standard File Description Structure (FDS).  It also provides the interface
# to the host system containing the DASD Volume file content source.
class FDS(object):
    name_pad=36*"\x00"
    def __init__(self,vdict,blksize):
        # Externally supplied parameters from FILE statement
        #print("volume.py - FDS.__init__ - vdict: %s" % vdict)
        self.name=vdict["name"][0]     # DASD volume name (ASCII or EBCDIC)
        self.isEBCDIC=vdict["name"][1] # EBCDIC flag
        self.load=vdict["load"]        # Default load address or None
        self.relo=vdict["relo"]        # Relocation requested, True/False
        self.enter=vdict["enter"]      # Passing of control requested, True/False
        self.size=vdict["size"]        # Explicit size in blockd from FILE statement
        self.source=vdict["source"]    # Host file name of file's content
        self.recsize=vdict["recsize"]  # Logical record size of source file
        self.card=vdict["card"]        # Treat source text lines as card images

        self.blksize=blksize           # DASD Volume's block size
        self.error=False               # This is set if an error occurs

        # Values set by the allocation method
        self.first_block=None  # First DASD volume block allocated to this file
        self.last_block=None   # Last DASD volume block allocated to this file
        self.last_written=None # Last DASD volume block containing content
        
        # Values set by the content method
        self.volblks=[]        # A list of the volume blocks containing content

        # Values created by the host method
        self.hostfile=None     # hostfile instance for use when reading the file.

        # Values set by the required method
        self.allocate=None     # Number of blocks to allocate to the file
        self.blocks=None       # Number of blocks required for file content
        self.last_used=None    # Number of bytes used in the last block written
        self.truncated=None    # Whether host file content was truncated
        
        
    def __str__(self):
        load=self.load
        if self.load is not None:
            load=hex(self.load)
        return "FDS Entry: name=%s,load=%s,relo=%s,blocks=%s,\nsource=%s" \
            % (repr(self.name),load,self.relo,self.size,self.source)

    # These methods may be overriden by a subclass depending upon the source of the
    # file's content
    def content(self,debug=False):
        # Saves the host file's content as a list of volume blocks. (self.volblks)
        try:
            self.volblks=self.hostfile.create_blocks(self.blksize,debug=debug)
            if debug:
                print("volume.py - FDS.content - len(self.volblks)=%s" \
                    % len(self.volblks))
        except IOError:
            print("volume.py - WARNING - Error reading host file: %s" \
                % self.source)
            self.error=True
        if len(self.volblks)!=self.blocks:
            print("volume.py - WARNING - inconsistency between FDS blocks (%s)" \
                "and number of blocks created for volume (%s)" \
                % (self.blocks,len(self.volblks)))
            self.error=True
        if debug:
            print("volume.py - FDS.content - "
                "File: %s - created volume blocks: %s" \
                % (repr(self.name),len(self.volblks)))
    def content_size(self,debug=False):
        # Returns the size in bytes of the actual file's content
        #return self.hostfile.hostlen
        size=self.hostfile.allocate_length(self.blksize,debug=debug)
        if debug:
            print("volume.py - FDS.content_size - allocate_length(%s)=%s" \
                % (self.blksize,size))
        return size
    def host(self):
        # Create a hostfile instance
        if self.card is not None:
            self.hostfile=cardfile(self.source,self.recsize,\
                ebcdic=self.card=="ebcdic")
        else:
            self.hostfile=hostfile(self.source,self.recsize)
        
    # These methods must not be overridden by a subclass
    
    def allocation(self,start,debug=False):
        # Returns the next available DASD volume block based upon the supplied
        # starting block for this FDS.
        if debug:
            print("volume.py - FDS.allocation - File %s start=%s" \
                % (repr(self.name),start))
        self.first_block=start
        if debug:
            print("volume.py - FDS.allocation - File %s first_block=%s" \
                % (repr(self.name),self.first_block))
            print("volume.py - FDS.allocation - File %s blocks=%s" \
                % (repr(self.name),self.blocks))
        self.last_written=start+self.blocks-1
        if debug:
            print("volume.py - FDS.allocation - File %s last_written=%s" \
                % (repr(self.name),self.last_written))
        # Allocated blocks
        next=self.first_block+self.allocate
        self.last_block=next-1
        if debug:
            print("volume.py - FDS.allocation - File %s last_block=%s" \
                % (repr(self.name),start))
        # Adjust for truncation
        if self.truncated:
            self.last_used=self.blksize
            self.last_written=self.last_block
            if debug:
                print("volume.py - FDS.allocation - File %s truncated "
                    "last_used=%s, last_written=%s" \
                    % (repr(self.name),self.last_used,self.last_written))
        if debug:
            print("volume.py - FDS.allocation - next block=%s" % next)
        return next
        
    def binary(self):
        # This method returns a string corresponding to the binary contents 
        # of a DASD Volume File Descriptor Structure.
        if self.recsize is None:
            recsz=0
            recflag=0x00
        else:
            recsz=self.recsize
            recflag=0x04
        flag=0x80|recflag
        if self.isEBCDIC:
            flag|=0x40
        if self.load is None:
            load=0
        else:
            flag|=0x20
            load=self.load
        if self.relo:
            flag|=0x10
        if self.enter:
            flag|=0x08
        if self.truncated:
            flag|=0x01
        string=self.name+FDS.name_pad
        string=string[:36]                   # [0:36]  DASD Volume file name
        string+="\x00"                       # [36:37] reserved
        string+=chr(flag)                    # [37:38] flag byte
        string+=halfwordb(self.last_used)    # [38:40] Bytes used in last block
        string+=halfwordb(recsz)             # [30:42] Blocked file record size
        string+=halfwordb(0)                 # [42:44] reserved
        string+=fullwordb(self.last_written) # [44:48] Last written block
        string+=fullwordb(self.first_block)  # [48:52] First allocated block
        string+=fullwordb(self.last_block)   # [52:56] Last allocated block
        string+=dblwordb(load)               # [56:64] Default load address
        if len(string)!=64:
            raise ValueError("volume.py - INTERNAL - "
                "FDS structure not 64 bytes: %s" % len(string))
        return string
        
    def display(self,pad=""):
        string="%s: %s" % (self.__class__.__name__,repr(self.name))
        string="%s Allocated blocks: %s-%s" \
            % (string,self.first_block,self.last_block)
        string="%s Content blocks: %s-%s" \
            % (string,self.first_block,self.last_written)
        string="%s Used in last block: %s" % (string,self.last_used)
        if self.recsize is not None:
            string="%s Record size: %s" % (string,self.recsize)
        if self.truncated:
            string="%s TRUNCATED!" % string
        print("%s%s" % (pad,string))
        
        
    def records(self,blko,debug=False):
        # Returns the physical media records corresponding to the file content.
        # This is a fairly complex process that spans many elements of the module.
        if debug:
            print("volume.py - FDS.records - File: %s - "
                "blko.dasd_file(%s,%s,%s,debug=%s)" \
                % (repr(self.name),self.first_block,self.allocate,\
                    len(self.volblks),debug))
        return blko.dasd_file(self.first_block,self.allocate,self.volblks,\
            debug=debug)
        
    def required(self,blocks,used):
        # Specifies the required blocks and last block used value for this file,
        # taking into consideration that an explicit size may have been specified.
        self.blocks=blocks
        self.last_used=used
        if self.size is None:
            self.allocate=blocks
        else:
            self.allocate=self.size
        if self.allocate < self.blocks:
            self.truncated=True
        else:
            self.truncated=False
        
# This class allows the Volume Content File (VCF) to be treated as a volume file.
# It provides the File Description Structure embedded within the Volume
# Description Block record (VDBR)
class VCF(FDS):
    @staticmethod
    def new(vcflist,name=None,load=None,relo=False,enter=False,size=None,\
        source=None,blksize=None):
        # This static method creates a VCF subclass instance.  This is used by the 
        # VDB class to create the FDS embedded in the VDB record.
        vdict={"name":name,
               "load":load,
               "relo":relo,
               "enter":enter,
               "size":size,
               "source":source,
               "recsize":None,
               "card":None}
        return VCF(vdict,vcflist,blksize)
    def __init__(self,vdict,vcflist,blksize):
        self.vcf=vcflist    # This is the same instance as used by DASDDEFN.VCF
        super(VCF,self).__init__(vdict,blksize)
    # These methods override the corresponding super class FDS methods
    def content(self,blksize,debug=False):
        string=""
        for x in self.vcf:
            string+=x.binary()
        self.volblks=chunk(string,blksize,pad=True)
    def content_size(self,debug=False):
        size=64*len(self.vcf)   # Total size of FDS entries in the VCF
        if debug:
            print("volume.py - VCF.content_size - returning %s" % size)
        return size
    def host(self):
        raise NotImplementedError("volume.py - INTERNAL - VCF class does not "
            "support host method")

# DASD Standard Volume Definition Block Record
# This class manages the DASD Volume Standard content of the VDBR and VCF
class VDBR(object):
    def __init__(self,vdict,blocks,vcflist):
        self.blocks=blocks              # BLOCKS subclass instance
        # Externally supplied parameters from VOLUME statement
        self.dtype=vdict["type"]
        self.name=vdict["name"]         # VCF FDS name value
        self.filepath=vdict["file"]     # VCF FDS source value
        self.vcfsize=vdict["vcfsize"]   # VCF FDS size value
        # Externally supplied parameters from PROGRAM statement
        self.vdb_data=vdict["data"]     # The program data
        self.vdb_struct=vdict["struct"] # struct mask to build data (To be done)
        self.vdb_ebcdic=vdict["ebcdic"] # Whether data is to be EBCDIC
        
        # Embedded Volume Content File's File Description Structure
        self.vcf=vcflist
        self.vcffds=VCF.new(self.vcf,\
            name=self.name,source=vdict["source"],size=self.vcfsize,\
            blksize=self.blocks.blksize)
        
        #
        # Values destined for binary VDBR content:
        #
        
        self.vdbr_lit="\xE5\xC4\xC2\xF1"  # 'VDB1' in EBCDIC
        # Bit-level flags:
        self.flags1=0x00
        self.volblks=self.blocks.capacity()  # Total storabelDASD volulme blocks

        # Specify CKD related content
        self.ckd_cyls=self.blocks.cylinders_per_volume   # minimize=True updates
        self.ckd_tracks=self.blocks.tracks_per_cylinder
        self.ckd_blocks=self.blocks.blocks_per_track
        if self.blocks.ckd:
            self.volblks=self.blocks_ckd()               # minimime=True updates
            self.flags1|=0x80
            
        # Specify FBA related content
        self.fba_sectors=self.blocks.sectors_per_volume  # minimize=True updates
        self.fba_secs=self.blocks.sectors_per_block
        if self.blocks.fba:
            self.volblks=self.blocks_fba()               # minimize=True updates
            self.flags1|=0x40

        # Specify Volume related content
        self.blksize=self.blocks.blksize     # DASD Volume block size
        self.reserved=vdict["reserve"]       # Number of initial reserved blocks
        self.flags1|=0x20
            
        self.next_available=self.reserved    # Next available block on the volume

    def __str__(self):
        string="VDB Record: type=%s,blksize=%s" \
            % (self.dtype,self.blksize)
        string="%s\nVCF %s" % (string,self.vcffds)
        return string

    def allocate(self,debug=False):
        # Allocates blocks to DASD volume files.  The Volume Content File is
        # allocated last placing it after all other content.
        for x in self.vcf:
            self.next_available=x.allocation(self.next_available,debug=debug)
        self.next_available=self.vcffds.allocation(self.next_available,debug=debug)
        if debug:
            print("volume.py - VDBR.allocate - next available block=%s" \
                % self.next_available)

    def binary(self,debug=False):
        self.flags1|=0x10
        string=self.vdbr_lit                    # [0:4]     VDB1 in EBCDIC
        string+=chr(self.flags1)                # [4:4]     flags
        string+="\x00\x00\x00"                  # [5:8]     reserved
        string+=fullwordb(self.ckd_cyls)        # [8:12]    Number of cylinders
        string+=halfwordb(self.ckd_tracks)      # [12:14]   Tracks/cylinder
        string+=halfwordb(self.ckd_blocks)      # [14:16]   Blocks/track
        string+=fullwordb(self.fba_sectors)     # [16:20]   FBA sectors
        string+=halfwordb(self.fba_secs)        # [20:22]   sectors/block
        string+=halfwordb(self.blksize)         # [22:24]   DASD volume block size
        string+=fullwordb(self.reserved)        # [24:28]   Reserved blocks
        string+=fullwordb(self.volblks)         # [28:32]   Blocks on the volume
        string+=self.vcffds.binary()            # [32:96]   VCF FDS
        string+=160*"\x00"                      # [96:256]  padding
        string+=self.program_data(debug=debug)  # [256:512] program data
        if len(string)!=512:
            raise ValueError("volume.py - VDBR record not 512 bytes: %s" \
                % len(string))
        return string

    def blocks_ckd(self):
        # Calculate the number of blocks storable on the CKD volume
        return self.ckd_cyls*self.ckd_tracks*self.ckd_blocks
        
    def blocks_fba(self):
        # Calculate the number of blocks storable on the FBA volume
        return self.fba_sectors/self.fba_secs

    def display(self,pad=""):
        # Provide console description of VDBR
        dasd_type="?"
        if self.blocks.ckd:
            dasd_type="CKD"
        if self.blocks.fba:
            dasd_type="FBA"
        
        string="VDBR: %s %s volume" % (self.dtype,dasd_type)
        string="%s Total Blocks=%s" % (string,self.volblks)
        string="%s blocksize=%s" % (string,self.blksize)
        string="%s reserved blocks=%s" % (string,self.reserved)
        string="%s\n      CKD cyl/vol=%s" % (string,self.ckd_cyls)
        string="%s trk/cyl=%s" % (string,self.ckd_tracks)
        string="%s blk/trk=%s" % (string,self.ckd_blocks)
        string="%s\n      FBA sec/vol=%s" % (string,self.fba_sectors)
        string="%s sec/blk=%s" % (string,self.fba_secs)
        string="%s\n      Flags=%s" % (string,hex(self.flags1))
        string='%s\n      Data="%s"' % (string,self.vdb_data)
        
        print("%s%s" % (pad,string))
        for x in self.vcf:
            x.display()
        self.vcffds.display(pad=pad)

    def content(self,debug=False):
        # Read each of the file's content and convert the content to full DASD
        # Volume blocks
        for x in self.vcf:
            x.content(debug)

    def program_data(self,debug=False):
        # This method returns a 256 byte string constituting program data
        # The data is supplied via the PROGRAM statement
        pad=256*"\x00"
        if self.vdb_data is None:
            return pad
        if self.vdb_struct is None:
            if self.vdb_ebcdic:
                data=self.vdb_data.translate(A2E)+pad
            else:
                data=self.vdb_data+pad
        else:
            pack="struct.pack('%s',%s)" % (self.vdb_struct,self.vdb_data)
            try:
                data=eval(pack)+pad
            except Exception,error:
                print("volume.py - WARNING - evaluating: %s" % pack)
                print("volume.py - WARNING - %s" %error)
                print("volume.py - WARNING - ignoring failed program struct data")
                data=pad
        data=data[:256]
        if debug:
            print("volume,py - VDBR.program_data - Program data:\n%s" \
                % dump(data,indent="   "))
        return data

    def records(self,debug=False):
        # Returns a list of physical volume records corresponding to volume 
        # content
        
        # Create the DASD record for myself.  It will always be the first record
        recs=self.blocks.vdb_record(self,debug=debug)
        
        # Create the DASD records for the files
        lst=[]
        for x in self.vcf:
            lst=x.records(self.blocks,debug=debug)
            if debug:
                print("volume.py - VDBR.records - len of lst=%s" % len(lst))
            recs.extend(lst)
            
        # Create the DASD records for the Volume Content File
        self.vcffds.content(self.blksize,debug=debug)
        recs.extend(self.vcffds.records(self.blocks,debug=debug))
        return recs

    def required(self,vcf,debug=False):
        # Determine the number of blocks for a file and its last block used value
        blocks,used=self.blocks.blocks(vcf.content_size(debug=debug))
        vcf.required(blocks,used)
        
    def required_sizes(self,debug=False):
        # Apply file size overrides from the specification file
        for x in self.vcf:
            self.required(x,debug=debug)
        self.required(self.vcffds,debug=debug)
   
    def update_ckd(self,size,debug=False):
        # Update with a new CKD device size
        self.ckd_cyls=size
        self.volblks=self.blocks_ckd()
        return self.blocks.vdbr_create(self)
        
    def update_fba(self,size,debug=False):
        # Update with a new FBA device size
        self.fba_sectors=size
        self.volblks=self.blocks_fba()
        return self.blocks.vdbr_create(self)
        
        
class hostfile(object):
    def __init__(self,name,recsize=None):
        self.hostname=name
        self.recsize=recsize
        try:
            self.hostlen=os.path.getsize(self.hostname)
        except OSError:
            raise ValueError
            
        self.recs_block=None  # For 'blocked' files, records per volume block
        self.fo=None          # File object for readin source file
            
    def allocate_length(self,blksize,debug=False):
        clength=self.content_length()
        if debug:
            print("volume.py - hostfile.allocate_length - clength: %s " % clength)
        if self.recsize is None:
            if debug:
                print("volume.py - hostfile.allocate_length - returning for "
                    "stream file %s bytes" % clength)
            return clength
        # Calculate the number of logical records in a DASD volume block
        if debug:
            print("volume.py - hostfile.allocate_length - processing block file")
        self.recs_block,rem=divmod(blksize,self.recsize)
        if debug:
            print("volume.py - hostfile.allocate_length - self.recs_blocks: %s" \
                % self.recs_block)
        if self.recs_block==0:
            raise ValueError
            
        # Calculate the number of whole DASD Volume blocks needed and number of
        # records in the last DASD Volume block
        block_size=self.recs_block*self.recsize
        if debug:
            print("volume.py - hostfile.allocate_length - source content in each "
                "volume block %s (%s)" % (block_size,hex(block_size)))
        blocks,last=divmod(clength,block_size)
        if debug:
            print("volume.py - hostfile.allocate_length - block file equivalent "
                "stream blocks %s with last bl0ck containing %s (%s) bytes" \
                % (blocks,last,hex(last)))
        # Convert content length into the equivalent stream file content length
        block_clength=(blocks*blksize)+last
        if debug:
            print("volume.py - hostfile.allocate_length - returning equvalent "
                "steam file content for block file: %s bytes" % block_clength)
        return block_clength

    def create_blocks(self,blksize,debug=False):
        # Reads a file from the host file system turning it into a list of DASD
        # Volume blocks.  The last block will be padded.  An IOError is thrown
        # if there is a problem reading the file.
        pad=blksize*"\x00"
        if debug:
            print("volume.py - hostfile.create_blocks - record size: %s" \
                % self.recsize)
            print("volume.py - hostfile.create_blocks - records per block: %s" \
                % self.recs_block)
        if self.recsize is None:
            read_size=blksize
        else:
            read_size=self.recsize*self.recs_block
        if debug:
            print("volume.py - hostfile.create_blocks - content read size: %s" \
                % read_size)
        blocks=[]
        fo=open(self.hostname,"rb")
        self.open_file()
        while True:
            block=self.read_file(read_size)
            if len(block)==0:
                # End-of-file reached without any partial block, we are done
                break
            if len(block)==blksize:
                # we read a whole block from the file
                blocks.append(block)
                continue
            # Partial block read
            block=block+pad
            blocks.append(block[:blksize])
        self.close_file()
        if debug:
            print("volume.py - hostfile.create_blocks - blocks created: %s" \
                % len(blocks))
        return blocks
        
    # These methods may be overridden by a subclass
    
    def close_file(self):
        self.fo.close()
    
    def content_length(self):
        return self.hostlen
        
    def open_file(self):
        self.fo=open(self.hostname,"rb")
        
    def read_file(self,length):
        return self.fo.read(length)
    
        
class cardfile(hostfile):
    spaces=80*" "
    def __init__(self,name,recsize=None,ebcdic=False):
        super(cardfile,self).__init__(name,recsize)
        self.ebcdic=ebcdic   # Whether to translate ASCII to EBCDIC
        images=[]
        try:
            fo=open(self.hostname,"rt")
            for line in fo:
                line=line[:-1]  # Remove end of line 
                line=line+cardfile.spaces
                line=line[:80]
                images.append(line)
            fo.close()
        except IOError:
            raise ValueError
        self.cards="".join(images)
        self.next=None
        
    # Overridden methods
    def close_file(self):
        self.next=None

    def content_length(self):
        return len(self.cards)
        
    def read_file(self,length):
        if self.next>=len(self.cards):
            return ""
        true_length=min(self.content_length()-self.next,length)
        data=self.cards[self.next:self.next+length]
        if self.ebcdic:
            data=data.translate(A2E)
        self.next+=length
        return data
        
    def open_file(self):
        self.next=0

# These classes use specfile.py to define the statements used by the DASD Volume
# specification file.  Processing of the file if performed by the instance method
# SPECFILE.process.

class BLKSIZE(DEC):
    def __init__(self,keyword):
        super(BLKSIZE,self).__init__(keyword)
    def parse(self,string,debug=False):
        bsize=super(BLKSIZE,self).parse(string)
        try:
            return {512:512,1024:1024,2048:2048,4096:4096}[bsize]
        except KeyError:
            raise ValueError

class CONTENT(SPECFILE):
    def __init__(self,debug=False):
        super(CONTENT,self).__init__(module="volume.py",debug=debug)
        self.define_statements(debug=debug)
        self.volume=None      # Initial VOLUME statements encountered
        self.program=None     # The last PROGRAM statement encountered
        self.files=[]         # List of FILE statements encountered
        
    def define_statements(self,debug=False):
       #if debug:
       #     print("\nvolume.py - CONTENT.define_statements - specfile.py "
       #         "subclass initialization: starting")
        self.register("VOLUME",VOLUME,debug=debug)
        self.register("FILE",FILE,debug=debug)
        self.register("PROGRAM",PROGRAM,debug=debug)
        #if debug:
        #    print("volume.py - CONTENT.define_statements - specfile.py "
        #        "subclass initialization: completed")
        
    def post_process(self,stmt):
        if isinstance(stmt,VOLUME):
            if self.volume is None:
                self.volume=stmt
            else:
                print("volume.py - ERROR - additional 'VOLUME' statement "
                    "encountered in line [%s]" % self.lineno)
                return
        if isinstance(stmt,FILE):
            self.files.append(stmt)
        if isinstance(stmt,PROGRAM):
            self.program=stmt
        return stmt

class FILE(STATEMENT):
    @classmethod
    def define(cls,debug=False):
        if debug:
            print("FILE.define - cls=%s" % cls)
        cls.required(AorE("name"),debug=debug)
        cls.required(PATH("source"),debug=debug)
        cls.default(Y_N("relo"),False,debug=debug)
        cls.default(Y_N("enter"),False,debug=debug)
        cls.default(HEX("load"),debug=debug)
        cls.default(DEC("size"),debug=debug)
        cls.default(STRING_LIST("card",["ascii","ebcdic"]),debug=debug)
        cls.default(DEC("recsize"),debug=debug)
        # WARNING: when adding or deleting keyword arguments, ensure the VCF.new
        # method is adjusted appropriately.
        
    def __init__(self,lineno,args,debug=False):
        super(FILE,self).__init__(lineno,args,module="volume.py",debug=debug)

class PROGRAM(STATEMENT):
    @classmethod
    def define(cls,debug=False):
        if debug:
            print("PROGRAM.define - cls=%s" % cls)
        cls.required(QSTRING("data"),debug=debug)
        cls.default(QSTRING("struct"),None,debug=debug)
        cls.default(Y_N("ebcdic"),False,debug=debug)
    def __init__(self,lineno,args,debug=False):
        super(PROGRAM,self).__init__(lineno,args,module="volume.py",debug=debug)

class VOLUME(STATEMENT):
    @classmethod
    def define(cls,debug=False):
        if debug:
            print("VOLUME.define - cls=%s" % cls)
        cls.required(AorE("name"),debug=debug)
        cls.default(STRING("type"),debug=debug)
        cls.default(BLKSIZE("blksize"),512,debug=debug)
        cls.default(PATH("file"),debug=debug)
        cls.default(Y_N("minimize"),True,debug=debug)
        cls.default(Y_N("compress"),False,debug=debug)
        cls.default(DEC("reserve"),debug=debug)
        cls.default(DEC("cyl"),debug=debug)
        cls.default(DEC("trk"),debug=debug)
        cls.default(DEC("sec"),debug=debug)
        cls.default(DEC("vcfsize"),debug=debug)
    def __init__(self,lineno,args,debug=False):
        super(VOLUME,self).__init__(lineno,args,module="volume.py",debug=debug)

    def fetch_value(self,name):
        # This method returns zero for None values
        val=self.values[name]
        if val is None:
            return 0
        return val

    def reserve_update(self,block):
        rsv=self.fetch_value("reserve")
        if block.ckd:
           rsv=max(rsv,block.cylinders(self.fetch_value("cyl")))
           rsv=max(rsv,block.tracks(self.fetch_value("trk")))
        else:
           rsv=max(rsv,block.sectors(self.fetch_value("sec")))
        self.values["reserve"]=max(rsv,block.reserve)

def copyright():
    print("volume.py Copyright, Harold Grovesteen, 2012")

def usage(n):
    print "Usage: ./volume.py spec_file [device_file] [debug]"
    #     sys.argv   [0]        [1]          [2]        [3]
    sys.exit(n)

# Checks command line arguments and instantiates the DASDDEFN instance
def check_args():
    global debugsw
    debugsw=False
    filepath=None
    if len(sys.argv)==4 and sys.argv[3]=="debug":
        filepath=sys.argv[2]
        if sys.argv[3]=="debug":
            debugsw=True
        else:
            print("volume.py - unrecognized argument '%s'" % sys.argv[3])
            usage(1)
    if len(sys.argv)==3:
        if sys.argv[2]=="debug":
            debugsw=True
        else:
            filepath=sys.argv[2]
    if len(sys.argv)==2 and sys.argv[1]=="debug":
        debugsw=True
        
    if len(sys.argv)<2:
        print("volume.py - command-line missing required spec_file argument")
        usage(1)
    if debugsw:
        print("volume.py - DEBUG - sys.argv: %s" % sys.argv)
    try:
        return DASDDEFN(sys.argv[1],filename=filepath,debug=debugsw)
    except ValueError:
        print("volume.py - Volume creation terminated due to specification error")
        sys.exit(1)

if __name__ == "__main__":
    copyright()
    d=check_args()  # returns an instantiated and valid DASD content specification
    d.create(debugsw)   # create and write out the emulation file
    
   
