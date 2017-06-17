#!/usr/bin/python3
# Copyright (C) 2012, 2013, 2016, 2017 Harold Grovesteen
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

this_module="fbautil.py"

# Python imports:
import os                    # Access to the OS functions
import stat                  # Access to file stat data

# SATK imports:
import hexdump               # Get the dump function for hex display
from structure import eloc   # Access the error reporting function
from fbadscb   import Extent # Access FBA data set control block Extent class
# ASMA imports: None


#
#  +---------------------+
#  |                     |
#  |   Module Functions  |
#  |                     | 
#  +---------------------+
#

# Converts a number of bytes into number of sectors
# Returns:
#   the number of whole sectors exactly matched by the number of bytes
# Exception:
#   ValueError if the number of bytes implies a length exceeding whole sectors
def bytes2sectors(byts):
    if isinstance(byts,(bytes,bytearray)):
        l=len(byts)
    else:
        l=byts
    sectors,excess=divmod(l,512)
    if excess != 0:
        raise ValueError(\
            "%s.bytes2sectors() - %s byts if %s sectors with excess: %s" \
                % (this_module,byts,sectors,excess))
    return sectors


# Dump bytes/bytearray object content as hexadecimal digits with byte positions
# Function Arguments:
#   byts    the bytes/bytearray sequence being dumped
#   hdr     An optional header preceding the information
#   indent  How much each line should be indented.  Defaults to "".
#   string  Whether a string is to be returned (True) or the output
#           printed (False)
def dump(byts,hdr="",indent="",string=False):
    if hdr:
        s="%s%s\n" % (indent,hdr)
    else:
        s=""
    s="%s%s\n" % (s,hexdump.dump(byts,indent=indent))
    if string:
        return s
    print(s)


# Returns the size of the file object file in bytes
# Function Argument:
#   fo   An open file object of the file whose size is returned
# Returns:
#   the size of the file object's file in bytes
def filesize(fo):
    # Determines the file size using Python modules
    s=os.fstat(fo.fileno())       # Get a stat instance from file number
    return s[stat.ST_SIZE]        # Get the file size from the stat data


# This function dumps an FBA image file by physical sector or an extent within the
# image file by both logical and physical sector numbers.
# Function Arbuments:
#   path    the path to the image file being dumped
#   extent  An fbadscb.Extent object
def image_dump(path,extent=None):
    fo=open(path,"rb")
    image=fo.read()
    image_size=filesize(fo)
    fo.close()

    if extent is None:
        # Print physical volume sectors
        print("\nImage File %s\n" % path)
        for n,rba in enumerate(range(0,image_size,512)):
            hdr="%s PSEC" % n
            chunk=image[rba:min(rba+512,image_size)]
            dump(chunk,hdr=hdr)
    else:
        # Prnt extent from the volume
        assert isinstance(extent,Extent),\
            "%s - image_dump() - 'extent' argument must be an Extent object: %s" \
                % (this_module,extent)

        print("\n%s in Image File %s\n" % (extent,path))
        pbeg=extent.lower
        beg=pbeg*512
        end=(extent.upper+1)*512
        for n,rba in enumerate(range(beg,end,512)):
            hdr="%s LSEC  %s PSEC" % (n,pbeg+n)
            chunk=image[rba:min(rba+512,image_size)]
            dump(chunk,hdr=hdr)


#
#  +----------------------------------------+
#  |                                        |
#  |   Fixed-Block Architecture Emulation   |
#  |                                        | 
#  +----------------------------------------+
#


# This class provides emulation of a FBA DASD device using a file.
#
# To open a new itialized FBA image for reading and writing:
#     fbao=fba.new(filename,dtype,comp=True|False)
# To open an existings FBA image for reading and writing (or just reading if ro=True):
#     fbao=fba.attach(filename,ro=True|False)
# To re-initialze an existing image already opened for reading and writing use the
# init class method with the fba object returned by the attach() method
#     fba.init(fbao)
#
# The fba class must be instantiated by means of either the attach() or new()
# methods.  After accesses are complete, the instance method detach() terminates
# access to the image, completes pending writes to the image file and closes it.
#   
# Following creation of the fba object, the following methods are available for
# single physical sector accesses:
#
#   read()      Read the next or specified physical sector from the image file.
#   seek()      Position to a specific sector of the image file, making it next
#   tell()      Retreive the next physical sector to be accessed
#   write()     Write to the next or specified physical sector in the image file
#
# The following methods are available for logical sector accesses of multiple
# sectors within an opened data set extent.  Positioning always occurs.
#
#   ds_open()   Provide extent information for data set accesses
#   ds_erase()  Overwrite the content of the logical sectors with a constant
#   ds_extent() Create an Extent object for use with ds_open() method.
#   ds_read()   Read one or more sectors from within a data set extent
#   ds_tell()   Retrieve the next logical sector to be accessed in the data set extent
#   ds_write()  Write one or more sectors from within a data set extent
#   ds_erase()  Overwrite the content of the logical sectors with a constant
#   ds_close()  Close a data set extent
#
# Only one data set extent may be open at any given time.
#
# Refer to the respective method descriptions for details of method usage.

class fba(object):

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
    pad=512*b"\x00"   # Sector pad

    # Dump bytes/bytearray object content as hexadecimal digits with byte positions
    # Method Arguments:
    #   byts    the bytes/bytearray sequence being dumped
    #   hdr     An optional header preceding the information
    #   indent  How much each line should be indented.  Defaults to "".
    #   string  Whether a string is to be returned (True) or the output
    #           printed (False)
    @staticmethod
    def dump(byts,hdr="",indent="",string=False):
        if hdr:
            s="%s%s\n" % (indent,hdr)
        else:
            s=""
        s="%s%s\n" % (s,dump(byts,indent=indent))
        if string:
            return s
        print(s)

    # Returns the size of the file object file in bytes
    # Method Argument:
    #   fo   An open file object of the file whose size is returned
    # Returns:
    #   the size of the file object's file in bytes
    @staticmethod
    def filesize(fo):
        # Determines the file size using Python modules
        s=os.fstat(fo.fileno())       # Get a stat instance from file number
        return s[stat.ST_SIZE]        # Get the file size from the stat data

    @staticmethod
    def size(dtype,hwm=None,comp=False):
        # Size a new device.  
        # hwm (high water mark) is the last used sector number
        # This method is required by media.py to size an emulating media file
        if hwm is None:
            return fba.sectors[dtype].sectors
        if comp:
            (grps,excess)=divmod(hwm+1,120)
            if excess>0:
                grps+=1
            return grps*120
        return hwm+1

    # Validates whether the size is valid for an FBA image file
    # Method Argument:
    #   size       The size being validated
    #   filename   The name of the file if an actual image file is being tested for
    #              reporting purposes.  Defaults to None
    # Returns:
    #   the number of emulated sectors for the given size
    # Exception:
    #   ValueError if the size is not valid.  If filename supplied an informational
    #   message is included with the exception.
    @staticmethod
    def volume_size(size,filename=None):
        sectors,excess=divmod(size,512)
        if excess!=0:
            if filename is None:
                raise ValueError()
            else:
                raise ValueError("%s FBA image truncated last physical sector %s: %s"\
                % (sectors,filename))
        return sectors

    # Attach an existing emulated FBA volume image file for access
    # Method Arguments:
    #   filename  The path to the existing FBA volume image file
    #   ro        Whether access is read-only (True) or read-write (False).  Defaults
    #             to True.
    @classmethod
    def attach(cls,filename,ro=False):
        # Access an existing FBA emulating media file for reading or writing.
        if ro:
            mode="rb"
        else:
            mode="r+b"
        try:
            fo=open(filename,mode)
        except IOError:
            raise IOError(\
                "Could not open existing FBA image: %s" % filename) from None
        return fba(fo,ro)

    # Initialize all sectors in an FBA image file to binary zeros.
    # Method Arguments:
    #   fo     A fba object created by methods new() or attach().  Or a Python
    #          file object opened for writing.
    #   dtype  The FBA device type being emulated as a string or the non-standard
    #          FBA image size as an integer.
    #   comp   Whether the image file is intended for compression by a Hercules
    #          utility.  Defaults to False.
    @classmethod
    def init(cls,fo,dtype,size=None,comp=False):
        if isinstance(fo,fba):
            if fba.ro:
                raise ValueError(\
                    "%s - %s.init() - can not initialize a read-only FBA image" \
                        % (this_module,cls.__name__))
            f=fba.fo
        else:
            f=fo

        if isinstance(dtype,str):
            # String device type supplied
            try:
                dev=fba.sectors[dtype]
                sectors=dev.sectors
            except KeyError:
                raise ValueError(\
                    "%s - %s.init() - unrecognized FBA device type: %s" \
                        % (this_module,cls.__name__,dtype))
            if size is not None:
                sectors=size
        elif isinstance(dtype,int):
            # Integer number of sectors supplied
            sectors=dtype
        else:
            # Don't know what to do with this
            raise ValueError(\
                "%s - %s.init() - 'dtype' argument must be a string or an integer: %s" \
                    % (this_module,cls.__name__,dtype))

        # Adjust sectors for Hercules compression if the FBA image will be compressed
        if comp:
            blkgrp=120   # A block group is 120 sectors
            (grps,excess)=divmod(sectors,blkgrp)
            if excess!=0:
                sectors=(grps+1)*blkgrp

        f.truncate()
        for x in range(sectors):
            try:
                f.write(fba.pad)
            except IOError:
                raise IOError(\
                    "%s - %s.init() - error initializing FBA image sector %s: %s" \
                        % (this_module,cls.__name__,x,f.name))
        f.flush()

    # Create a new FBA image file and initialize all sector to binary zeros.
    # Method Arguments:
    #   filename  The file path of the FBA image file being created.  An existing
    #             file will be overwriten.
    #   dtype     The FBA device type being emulated as a string or the non-standard
    #             FBA image size as an integer.
    #   comp      Whether the image file is intended for compression by a Hercules
    #             utility.  Defaults to False.
    # Returns:
    #   the fba object providing access to the emulated FBA image
    # Note: size is retained for media.py compatibility.
    @classmethod
    def new(cls,filename,dtype,size=None,comp=False):
        try:
            fo=open(filename,"w+b")
        except IOError:
            raise IOError(\
                "%s - %s.new() - could not open new FBA image: %s" \
                    % (this_module,cls.__name__,filename)) from None

        fba.init(fo,dtype,size=size,comp=comp)
        return fba(fo,ro=False,pending=True)

    # See the description above for 
    def __init__(self,fo,ro=True,pending=False):
        # Image file controls and status
        self.filename=fo.name        # Remember the filename of the image file
        # Image file size in bytes
        self.filesize=fba.filesize(fo)

        # Validate the image files size and determine the number of sectors it
        # emulcates.
        sectors=fba.volume_size(self.filesize,filename=self.filename)
        self.fo=fo               # Open file object from new() or attach()
        self.pending=pending     # Whether file object writes may be pending

        # Emulation controls and status
        self.ro=ro              # Set read-only (True) or read-write (False)
        self.last=sectors-1     # Last physical sector number
        self.sector=0           # Current physical sector position

        # Logical data set extent controls
        self.extent=None        # Currently open data set extent
        self.lower=None         # The first physical sector of the extent
        self.upper=None         # The last physical sector of the extent
        self.ds_sector=None     # Current logical sector position
        self.ds_sectors=0       # The number of sectors in the extent
        self.ds_last=None       # The last logical sector in the extent

        # I/O tracing control
        self._trace=False       # Trace I/O operations
        self._tdump=False       # Dump sector content while tracing
        
        # Have to wait until self._trace is defined.
        self.seek(0)            # Position file to sector 0

    def __str__(self):
        if self.fo.closed:
            return "FBA: detached image file: %s" % self.filename
        return "FBA: extent:%s  sector:%s  self.fo:%s"\
            "  ro=%s  last:%s  file:%s" \
                % (self.extent,self.sector,\
                    self.fo.tell(),self.ro,self.last,self.filename)

    # This method validates that a physical extent is within the actual FBA image
    # Exception:
    #   ValueError is raised if either the lower or upper extent boundary is
    #   greater than the last physical sector or the Extent is in the 'not used'
    #   state.
    def _ck_extent(self,extent):
        if extent.notused:
            raise ValueError("%s Extent object must be used: %s" \
                % (eloc(self,"_ck_extent",module=this_module),extent))

        lower=extent.lower
        if lower>self.last:
            raise ValueError(\
                "%s extent lower boundary is not within the FBA image (0-%s): %s"\
                    % (eloc(self,"_ck_extent",module=this_module),self.last,lower))
        upper=extent.upper
        if upper>self.last:
            raise ValueError(\
                "%s extent upper boundary is not within the FBA image (0-%s): %s"\
                    % (eloc(self,"_ck_extent",module=this_module),self.last,upper))

    # Perform the actual forcing of possible pending writes to occur
    def _flush(self):
        self.fo.flush()
        self.pending=False

    # Performs a low level read.
    # Method Argument:
    #   size   the number of bytes to read from the image file current position
    # Returns:
    #   the bytes read
    def _read(self,size):
        # Force writing any pending writes before attempting to read the file
        # otherwise, the image file may have stale sector data.
        if self.pending:
            # By using this method we get to trace the flush operation
            self.flush()

        # Read the requested bytes
        try:
             byts=self.fo.read(size)
        except IOError:
            raise IOError("%s IOError while reading FBA physical sector: %s" \
                % (eloc(self,"_read",module=this_module),self.sector))

        # Ensure we actually read the number of expected bytes.
        if len(byts)!=size:
            raise ValueError(\
                "%s did not read requested bytes (%s) from image file: %s"
                    % (eloc(self,"_read",module=this_module),size,len(byts)))
        return byts

    # Convert logical sector number to physical and validate logical sectors are
    # within the open extent
    # Method Arguments:
    #   sector    The starting logical sector of the operation
    #   sectors   The number of sectors in the logical operation
    # Returns:
    #   A tuple where:
    #      tuple[0] is the starting physical sector being read
    #      tuple[1] is the last physical sector being read
    #      tuple[2] is the last logical sector being read
    # Exception:
    #   ValueError if the number of sectors in the operation exceeds the open
    #   extent.
    def _to_physical(self,sector,sectors=1):
        assert sector >=0,"%s 'sector' argument must be >= 0: %s" \
            % (eloc(self,"_to_physical",module=this_module),sector)
        assert sectors >=1,"%s 'sectors' argument must be >= 1: %s" \
            % (eloc(self,"_to_physical",module=this_module),sectors)

        l_last=sector+sectors-1
        if l_last > self.upper:
            raise ValueError(\
                "%s end of operation beyond end of extent (%s): %s" \
                    % (eloc(self,"_to_physical",module=this_module),\
                        self.upper,l_last))

        return (self.lower+sector,self.lower+l_last,l_last)

    # Performs the low level write.
    # Method Argument:
    #   data   a bytes sequence being written.  Must be bytes not bytearray
    def _write(self,data):
        # Ensure bytes sequence is being written not bytearray.  Python requires
        # a bytes sequence.  Sequence can not be bytearray.  This give the using
        # software the freedom to use either sequence.
        if isinstance(data,bytearray):
            byts=bytes(data)
        else:
            byts=data
        assert isinstance(byts,bytes),\
            "%s 'data' argument must be a bytes/bytearray sequence for sector %s: %s" \
                % (eloc(self,"_write",module=this_module),byts,self.sector)

        # Write the bytes
        try:
            self.fo.write(byts)
        except IOError:
            raise IOError(\
                "%s IOError while writing FBA physical sector: %s" \
                    % (eloc(self,"write",module=this_module),self.sector))

        self.pending=True        # Indicate the write might be pending

    # Detach and close the image file
    def detach(self):
        if __debug__:
            if self._trace:
                print("%s detaching image file: %s" \
                    % (eloc(self,"detach",module=this_module),self.filename))

        if self.extent:
            self.ds_close()
        try:
            self.fo.flush()
            self.fo.close()
        except IOError:
            raise IOError(\
                "%s IOError detaching %s FBA image: %s" \
                    % (eloc(self,"detach",module=this_module),self.filename))

        self.pending=False

    # Force pending writes
    def flush(self):
        if __debug__:
            if self._trace:
                print("%s forcing pending image file writes" \
                    % eloc(self,"flush",module=this_module))
        self._flush()   # Use the low-level method to actually force pending writes

    # Enable/Disable I/O operation tracing.
    # Method Argument:
    #   state   Specify True to enable tracing.  Specify False to disable tracing.
    #   tdump   Specify True to dump sector content while tracing, False otherwise.
    def trace(self,state,dump=False):
        if state:
            self._trace=True
            self._tdump=dump
            if __debug__:
                print("%s set tracing:%s, dump:%s" \
                    % (eloc(self,"trace",module=this_module),self._trace,self._tdump))
        else:
            if __debug__:
                was_tracing=self._trace
            self._trace=False
            self._tdump=False
            if __debug__:
                if was_tracing:
                    print("%s set tracing:%s, dump:%s" \
                        % (eloc(self,"trace",module=this_module),\
                            self._trace,self.dump))

  #
  #  Physical sector accessing methods
  #

    # Read the next sector or a specified sector.  Following the read the image is
    # positioned at the next physical sector.
    # Method Argument:
    #   sector   Specify a physical sector number to be read.  Specify None to read
    #            from the next sector to which the image is positioned based upon
    #            the previously accessed sector.  Defaults to None.
    #   array    Whether a bytearray (True) or bytes (False) sequence is returned
    # Exception:
    #   IOError  if there is a file related problem
    #
    # Programming Note:
    # Use array=True if the user software expects to update the content of the
    # sector.
    def read(self,sector=None,array=False):
        # Position the image file if requested to do so.
        if sector is not None: 
            self.seek(sector)

        # Trace the read if physical tracing is enabled
        if __debug__:
            if self._trace:
                sec=self.sector
                fpos=self.fo.tell()

        # Read the physical sector using the low-level routine
        data=self._read(512)
        self.sector+=1

        # Trace the read if physical tracing is enabled
        if __debug__:
            if self._trace:
                print("%s READ: sector: %s  file pos: %s" \
                    % (eloc(self,"read",module=this_module),sec,fpos))
                if self._tdump:
                    dump(data,indent="    ")

        # Return the information is the requested sequence type
        if array:
            return bytearray(data)
        return data

    # Position the image file to a specific physical sector.
    # Method Argument:
    #   sector   the physical sector to which the image file is to be positioned.
    # Exception:
    #   ValueError if the physical sector does not exist in the image file.
    #   IOError if there is a file related problem
    def seek(self,sector):
        # Determine the position in the file for a physical sector access
        if sector>self.last:
            raise ValueError("%s FBA sector %s is beyond last sector %s" \
                % (eloc(self,"seek",module=this_module),sector,self.last))
        sector_loc=sector*512
        if sector_loc>self.filesize:
            raise IOError("%s FBA sector %s file position %s is beyond EOF: %s" \
                % (eloc(self,"seek",module=this_module),sector,sector_loc,\
                    self.filesize))

        # Perform the positioning by physical sector number in this object and
        # position the file object accordingly
        try:
            self.fo.seek(sector_loc)
        except IOError:
            raise IOError("%s IOError while positioning to FBA sector: %s" \
                % (eloc(self,"seek",module=this_module),self.sector))

        self.sector=sector

        # Trace the seek if physical tracing is enabled
        if __debug__:
            if self._trace:
                print("%s SEEK: sector: %s  file pos: %s" \
                    % (eloc(self,"seek",module=this_module),sector,self.fo.tell()))

    # Return the current physical sector position
    def tell(self):
        if __debug__:
            if self._trace:
                print("%s returning: %s" % (eloc(self,"tell",module=this_module),\
                    self.sector))
        return self.sector

    # Write content to the next sector or a specified sector.  Following the write
    # operation the image is positioned at the next physical sector.
    # Method Arguments:
    #   byts     A bytes/bytearray sequence of the content to be written
    #   sector   Specify a physical sector number to which the content is written.
    #            Specify None to write to the next sector to which the image is
    #            positioned based upon the previously accessed sector.  Defaults to
    #            None.
    #   pad      Whether content is to be padded to a full sector (True) or the
    #            content must be a full sector (False).  Defaults to False.
    # Exception
    #   NotImplementedError if the image file is read-only.
    def write(self,byts,sector=None,pad=False):
        if self.ro:
            raise NotImplementedError(\
                "%s can not write to read-only FBA image: %s" \
                    % (eloc(self,"write",module=this_module),self.filename))

        # Position the image file if requested to do so.
        if sector is not None:
            self.seek(sector)

        # Pad or detect truncated sector content
        data=byts
        if len(data)!=512:
            if pad:
               data=data+fba.pad
               data=data[:512]
            else:
                raise ValueError("%s FBA image sector must be 512 bytes: %s"\
                    % (eloc(self,"write",module=this_module),len(data)))

        # Trace the write operation if physical sector tracing is enabled
        if __debug__:
            if self._trace:
                if len(data)>len(byts):
                    padded="  pad: %s" % len(data) - len(byts)
                else:
                    padded=""
                print("%s WRITE: sector: %s  file pos: %s%s" \
                    % (eloc(self,"write",module=this_module),\
                        sector,self.fo.tell(),padded))
                if self._tdump:
                    dump(data,indent="    ")

        # Write to the sector using the low-level routine
        self._write(data)
        self.sector+=1

  #
  #  Logical data set extent accessing methods
  #

    # Closes the open extent.  It no extent is open, resets the extent controls
    def ds_close(self):
        # Trace the data set close if logical sector tracing is enabled
        if __debug__:
            if self._trace:
                print("%s DS_CLOSE: closing extent: %s" \
                    % (eloc(self,"ds_close",module=this_module),self.extent))

        if self.extent:
            self.flush()     # Write any pending sectors to the image file

        self.ds_sector=self.ds_last=self.extent=self.lower=self.upper=None
        self.ds_sectors=0

    # Erase one or more sectors of the extent or the entire extent with a defined
    # value.
    # Method Arguments:
    #   sector   starting logical sector of the erased area.  Defaults to 0.
    #   sectors  Specify the number of sectors whose content is erased.  Specify
    #            True to erase all logical sectors following the first.
    #            Defaults to 1.
    #   fill     The value to filling the erased bytes of each sector.  May be a
    #            character or numeric value between 0-255.  Defaults to 0
    # Exception:
    #   NotImplementedError if the image file is read-only or has no open extent.
    #
    # Programming Notes: 
    # To erase an entire extent to zeros use an opened extent:
    #    fbao.ds_erase(sector=0,sectors=True)
    # If an EBCDIC character is desired for the fill character, fill must be a hex
    # integer, for example:
    #    fill=0x40
    def ds_erase(self,sector=0,sectors=1,fill=0):
        assert isinstance(sector,int) and sector>=0,\
            "%s 'sector' argument must be an integer >= 0: %s"\
                % (eloc(self,"ds_erase",module=this_module),sector)
        if self.ro:
            raise NotImplementedError("%s can not erase a read-only image file: %s"\
                % (eloc(self,"ds_erase",module=this_module),self.filename))
        if not self.extent:
            raise NotImplementedError("%s no open extent for erasing" \
                % (eloc(self,"ds_erase",module=this_module)))

        # Create the content for an erased sector
        if isinstance(fill,str):
            if len(fill)>0:
                f=ord(fill[0])
            else:
                raise ValueError("%s 'fill' argument must not be an empty string"\
                    % eloc(self,"ds_erase",module=this_module))
        elif isinstance(fill,int):
            if fill<0 or fill >255:
                raise ValueError("%s 'fill' argument out of range (0-255): %s" \
                    % eloc(self,"ds_erase",module=this_module),fill)
            f=fill
        byts=bytes([f,]*512)

        # Determine the physical sectors of erased area
        if sectors == True:
            secs=self.ds_sectors
        else:
            assert isinstance(sectors,int) and sectors>=1,\
               "%s 'sectors' argument must be True or an integer >= 1: %s" \
                   % (eloc(self,"ds_erase",module=this_module),sectors)
            secs=sectors

        p_first,p_last,l_last = self._to_physical(sector,sectors=secs)

        # Erase the requested sectors' content
        self.seek(p_first)
        sec=sector
        if __debug__:
            if self._trace:
                if secs == 1:
                    s="%s DS_ERASING: logical sector:%s  physical sector: %s"\
                        "file pos:%s  with:%02X" \
                            % (eloc(self,"ds_read",module=this_module),\
                                sector,p_first,self.fo.tell(),f)
                else:
                    s="%s DS_ERASING: logical sectors:%s-%s  physical sectors: %s-%s" \
                        "  sectors:%s  file pos:%s  with:0x%02X" \
                            % (eloc(self,"ds_read",module=this_module),\
                                sector,l_last,p_first,p_last,secs,self.fo.tell(),\
                                    f)
                print(s)

        # Erase the requested sectors' content
        for n in range(secs):
            self._write(byts)
            self.sector+=1
            self.ds_sector+=1

    # This method returns an Extent object for a specific range of physical sectors
    # Method Arguments:
    #   lower   the first physical sector of the extent
    #   upper   the last physical sector of the extent.  If True is specified the
    #           upper limit of the extent is the last physical sector of the image
    #           file.
    # Programming Note: To access all sectors of the image fila as a data set use:
    #   fbao.ds_open(fbao.ds_extent(0,True))
    # Using the entire volume as an extent allows multi-sector operations on the 
    # image file at the physical level.
    def ds_extent(self,lower,upper):
        if upper is True:
            up=self.last
        else:
            up=upper

        ext=Extent(lower=lower,upper=up)
        if __debug__:
            if self._trace:
                print("%s returned: %s" % (eloc(self,"ds_extent"),ext))

        return ext

    # Open an extent for logical sector accesses
    # Exception
    #   NotImplementedError if the image file already has an open extent.
    def ds_open(self,extent):
        assert isinstance(extent,Extent),\
            "%s 'extent' argument must be a fbadscb.Extent object: %s" \
                % (eloc(self,"ds_open",module=this_module),extent)
        if self.extent:
            raise NotImplementedError("%s extent already open: %s" \
                % (eloc(self,"ds_open",module=this_module),self.extent))

        self._ck_extent(extent)

        self.extent=extent      # Remember the physical extent
        self.lower=extent.lower # The first physical sector of the extent
        self.upper=extent.upper # The last physical sector of the extent
        self.ds_sector=0        # The next logical sector to be accessed
        self.ds_sectors=extent.sectors()  # Calculate the number of sectors
        self.ds_last=self.ds_sectors-1    # The last logical sector in the extent

        # Trace the data set open if tracing is enabled
        if __debug__:
            if self._trace:
                print("%s DS_OPEN: extent:%s  sectors:%s  logical sectors:0-%s" \
                    % (eloc(self,"ds_open",module=this_module),\
                        extent,self.ds_sectors,self.ds_last))

        self.seek(self.lower)   # Position at start of the extent   

    # Read one or more sectors from the extent.  
    # Method Arguments:
    #   sector    the starting logical sector number within the extent
    #   sectors   the number of sectors to be read including the first sector.
    #             Defaults to 1.
    #   array     Whether a bytearray is to be returned (True) or a bytes sequence
    #             (False).  Defaults to False.
    # Programming Note: use array=True if the user plans to update the content
    # Returns:
    #   a bytes/bytearray sequence (as requested) of the sector or sectors content
    #   form the image file
    # Exception:
    #   ValueError for various detected errors.  See _to_physical() method 
    #              for detected errors.
    #   IOError if an error occurs during reading
    #   NotImplementedError if the image file has no open extent.
    def ds_read(self,sector=None,sectors=1,array=False):
        if not self.extent:
            raise NotImplementedError("%s no open extent for reading" \
                % eloc(self,"ds_read",module=this_module))

        if sector is None:
            sec=self.ds_sector
        else:
            sec=sector

        p_first,p_last,l_last=self._to_physical(sec,sectors=sectors)

        # Position to the starting sector
        self.seek(p_first)
        self.ds_sector=sec

        # Perform tracing if requested
        if __debug__:
            if self._trace:
                if sectors == 1:
                    s="%s DS_READ: logical sector:%s  physical sector: %s"\
                    "  file pos:%s" % (eloc(self,"ds_read",module=this_module),\
                            sec,p_first,self.fo.tell())
                else:
                    s="%s DS_READ: logical sectors:%s-%s  physical sectors: %s-%s" \
                        "  sectors:%s  file pos: %s"\
                            % (eloc(self,"ds_read",module=this_module),\
                                sec,l_last,p_first,p_last,sectors,self.fo.tell())
                print(s)

        # Read the sector' or sectors' content
        byts=self._read(sectors*512)
        self.sector+=sectors
        self.ds_sector+=sectors
        
        # Dump the content read from the file image if content tracing enabled
        if __debug__:
            if self._tdump:
                dump(byts,indent="    ")

        # Return the content read from the sector or sectors as bytes or bytearray
        # as requested.
        if array:
            return bytearray(byts)
        return byts

    # Returns the next logical sector for access in the extent
    # Exception:
    #   NotImplementedError if the image file has no open extent.
    def ds_tell(self):
        if not self.extent:
            raise NotImplementedError("%s no open extent for logical sector position" \
                % (eloc(self,"ds_tell",module=this_module)))

        if __debug__:
            if self._trace:
                print("%s returning: %s" \
                    % (eloc(self,"ds_tell",module=this_module),self.ds_sector))

        return self.ds_sector

    # Write the content of the byte/bytearray sequence to the sector or sectors
    # implied by the length of the sequence starting with a given logical sector
    # Method Arguments:
    #   byts    the bytes/bytearray sequence being written to the file image
    #   sector  Specify the starting logical sector of the write operation.  Omit
    #           to write at the next positioned sector.
    # Exceptions:
    #   ValueError for various detected errors.  See bytes2sectors() function and
    #              _to_physical() method for detected errors.
    #   IOError if an error occurs during writing
    #   NotImplementedError if the image file is read-only or no open extent.
    def ds_write(self,byts,sector=None):
        if self.ro:
            raise NotImplementedError("%s can not write to a read-only image file: %s"\
                % (eloc(self,"ds_write",module=this_module),self.filename))
        if not self.extent:
            raise NotImplementedError("%s no open extent for writing" \
                % (eloc(self,"ds_write",module=this_module)))
          
        # Validate there is enough data to write entire sectors
        try:
            sectors=bytes2sectors(byts)
        except ValueError:
            raise ValueError("%s 'byts' argument not full sectors, length: %s" \
                % (eloc(self,"ds_write",module=this_module),len(byts))) from None
            
        # Locate where the write operation begins
        if sector is None:
            sec=self.ds_sector
        else:
            sec=sector

        p_first,p_last,l_last=self._to_physical(sec,sectors=sectors)

        # Position to the starting sector
        self.seek(p_first)
        self.ds_sector=sec

        # Perform tracing if requested.
        if __debug__:
            if self._trace:
                if sectors == 1:
                    s="%s DS_WRITE: logical sector:%s  physical sector: %s"\
                        "file pos: %s" % (eloc(self,"ds_write",module=this_module),\
                            sector,p_first,self.fo.tell())
                else:
                    s="%s DS_WRITE: logical sectors:%s-%s  physical sectors: %s-%s" \
                        "sectors:%s  file pos:%s" \
                            % (eloc(self,"ds_write",module=this_module),sector,\
                                l_last,p_first,p_last,sectors,self.fo.tell())
                print(s)
                if self._tdump:
                    dump(byts,indent="    ")

        # Write the sector' or sectors' content
        self._write(byts)
        self.sector+=sectors
        self.ds_sector+=sectors


class fba_info(object):
    # K=1024
    # M=1024*1024
    # G=1024*1024*1024
    units=[1024*1024*1024,1024*1024,1024]
    
    @staticmethod
    def KMG(value):
        for n,x in enumerate(fba_info.units):
            if value>=x:
                unit="GMK"[n]
                unit_metric=fba_info.units[n]
                units,excess=divmod(value,unit_metric)
                tenths=excess*10 // unit_metric
                return "%s.%s%sB" % (units,tenths,unit)
        return "%sB" % (value)

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
        string="%s\nHost:    FILE=%s (%s)" \
            % (string,self.host,fba_info.KMG(self.host))
        string="%s\nBlock:   LENGTH=%s SECTORS=%s BLOCKS=%s" \
            % (string,self.block,self.required,self.capacity)
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
        return self.host//self.__block

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
    raise NotImplementedError("%s is only intended for import use" % this_module)
