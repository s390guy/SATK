#!/usr/bin/python3.3
# Copyright (C) 2012-2020 Harold Grovesteen
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
#    awsutil.py    This module. Handles writing and reading AWS tape image
#                  files.
#    fbautil.py    Handles writing and reading of FBA image files.
#    ckdutil.py    Handles writing and reading of CKD image files.
#
# See media.py for usage of AWS tape file images

#import struct

this_module="awsutil.py"

# Convert an UNsigned integer into a little endian half word of two bytes
# Function Argument:
#   value   the integer being converted to a two byte half word
#
# Returns:
#   a bytes sequence of two bytes
def hword_bytes(value):
    assert isinstance(value,int),"%s.hword_bytes() - 'value' argument must be "\
        "an integer: %s" % (this_module,value)
    return value.to_bytes(2,byteorder="little")

# Convert two bytes in little endian format into an integer.
# Function Argument:
#   byt   the sequence of two bytes
# Returns:
#   an integer from the little endian sequence of two bytes.
def hword_int(byt):
    assert isinstance(byt,bytes),"%s.hword_le() - 'byt' argument must be a "\
        "bytes sequence: %s" % (this_module,byt)
    assert len(byt)==2,"%s.hword_le() - 'byt' argutmen must be two bytes: %s"\
        % (this_module,len(byt))
    return int.from_bytes(byt,byteorder="little")

# Master AWS tape management object for media emulation system
class awstape(object):
    # To open a new unitialized AWS scratch tape:  awstape.scratch(filename)
    #    New scratch tapes are always opened as read/write
    # To open an existings AWS tape: awstape.mount(filename,ro=True|False)
    #    Existing AWS tapes are opened read-only by default
    # It is recommended to use either the mount or scratch methods to open
    # an AWS tape file rather than instantiating 
    record=["tape","tm"]  # recsutil class names of tape records
    devices={}  # Dictionary mapping dtype strings to hex device type and model

    @staticmethod
    def _check_filename(name):
        if len(name)<=4 or name[-4:]!=".aws":
            raise ValueError("AWS tape file name must have .aws extention")

    @staticmethod
    def mount(filename,ro=True):
        awstape._check_filename(filename)
        try:
            fo=open(self.filename,"rb")
        except IOError:
            raise IOError(\
                "Could not open existing AWS tape: %s" % self.filename)
        return awstape(fo,ro)

    @staticmethod
    def scratch(filename):
        awstape._check_filename(filename)
        try:
            fo=open(filename,"wb")
        except IOError:
            raise IOError(\
                "Could not open scratch AWS tape: %s" % filename)
        return awstape(fo,False)

    @staticmethod
    def size(hwm=None):
        # This method is required by media.py to size a emulating media file
        return None     # AWS tape files do not have predetermined sizes

    # Functions return:
    #   True = Tapemark read or spaced over
    #   False = successful, data block read (in buffer) or written.
    # At completion of functions the "read/write head" will be positioned
    # before the next inter-record gap (the header) to be read or written
    def __init__(self,fo,ro=False):
        #if struct.calcsize(header.structure)!=header.length:
        #    raise ValueError(\
        #        "Internal errror: AWS structure definition not 6 bytes")
        self.fo=fo              # Open file object from mount or scratch
        self.ro=ro              # Set read-only (True) or read-write (False)
        self.loaded=True        # Loaded (True) or unloaded/closed (False)
        self.pos=0              # Set at load point
        self.data=""            # Current data buffer
        self.prvhdr=self._pseudo_header()   # Previously read header
        self.curhdr=None        # Current header (at current block's data)
        self.buffer=""          # Data buffer

    def _check_at_header(self):
        if self.curhdr!=None:
            self.pos=self.fo.tell()
            raise IOError(\
                "Tape not at header, current pos: %s" % self.pos)

    def _check_at_load_point(self):
        self.pos=self.fo.tell()
        if self.pos==0:
            raise NotImplementedError(\
                "Attempting to backspace past tape load point: %s" %\
                self.fo.name)

    def _check_loaded(self,oper):
        if not self.loaded:
            raise NotImplementedError(\
                "Can not perform %s, tape unloaded/closed: %s" % \
                oper,self.fo.name)

    def _check_ro(self):
        if self.ro:
            raise NotImplementedError(\
                "Can not write to read-only tape: %s" % self.fo.name)

    def _pseudo_header(self):
        return header(0,0,False)

    # Internal: read a vairable number of bytes from the ASW tape file
    def _read_file(self,bytes,reading):
        self.pos=self.fo.tell()
        try:
            data=self.fo.read(bytes)
        except IOError:
            raise IOError("IOError reading %s at %s" % (reading,self.pos))
        if len(data)!=bytes:
            raise IOError(\
                "Unexpected EOF reading %s at %s" % (reading,self.pos))
        self.pos=self.fo.tell()
        return data

    # Internal: read a AWS Header
    def _read_hdr(self):
        filedata=self._read_file(header.length,"block header")
        position=self.pos-header.length  # Header file position
        curhdr=header.aws(filedata,pos=position)
        curhdr.filepos=position
        return curhdr
        
    # Tape Operation: backspace block
    def bsb(self):
        self._check_loaded("bsb")
        self._check_at_load_point()
        # If the previous operation was a forward moving operation (like read
        # or write) we will have in hand the previous block header.  The
        # first bsb in a series of bsb operations will take the False (else)
        # path.  Succeeding bsb's (for example when we are doing bsf) will 
        # take the True path.
        if self.prvhdr==None:
            # The * indicates where we are positioned in the file
            #
            # On entry positioned at end of block we want to backspace over
            #  | prevhdr | prv block | curhdr | cur block
            #                         *
            # Read the current block's header to get previous block length
            self.curhdr=self._read_hdr()
            # Read the current block's header to get previous block length
            #  | prevhdr | prv block | curhdr | cur block
            #                                  *
            self.fo.seek(-(self.curhdr.prvlen+(2*header.length)),1)
            # Now at start of previous block's header where we want to be
            #  | prevhdr | prv block | curhdr | cur block
            #   *
            # Read this block's header to determine if we just backspaced
            # over a tapemark.
            self.curhdr=self._read_hdr()
            #  | prevhdr | prv block | curhdr | cur block
            #             *
            tapemark=self.curhdr.tapemark
            # Reposition back to header of the current block
            self.fo.seek(self.curhdr.filepos,0)
            #  | prevhdr | prv block | curhdr | cur block
            #   *
            self.curhdr=None
        else:
            self.fo.seek(self.prvhdr.filepos,0)
            # Now at start of previous block's header where we want to be
            tapemark=self.prvhdr.tapemark
            self.prvhdr=None
        return tapemark
        
    # Tape Operation: backspace file
    def bsf(self):
        self._check_loaded("bsf")
        while not self.bsb():
            pass
        return True
        
    # Tape Operation: forward space block
    def fsb(self):
        self._check_loaded("fsb")
        self._check_at_header()
        self.curhdr=self._read_hdr()
        self.fo.seek(self.curhdr.curlen,1)
        self.buffer=None
        self.prvhdr=self.curhdr
        self.curhdr=None
        return self.prvhdr.tapemark
        
    # Tape Operation: forward space file
    def fsf(self):
        self._check_loaded("fsf")
        while not self.fsb():
            return True
            
    # Retrieve a saved block buffer
    def get_buffer(self):
        if self.buffer==None:
            raise TypeError("data buffer empty")
        buffer=self.buffer
        self.buffer=None
        return buffer
        
    # Save a block buffer
    def put_buffer(self,data):
        if len(data)==0:
            raise TypeError("can not put_buffer of zero length")
        self.buffer=data
        
    # Tape Operation: read a data block
    def read(self):
        self._check_loaded("read")
        self._check_at_header()
        curhdr=self._read_hdr()
        if curhdr.tapemark:
            self.buffer=None
            self.prvhdr=curhdr
            return True
        self.buffer=self._read_file(curhdr.curlen,"data block")
        self.prvhdr=curhdr
        return False
        
    # Tape Operation: Rewind
    def rew(self):
        self._check_loaded("rew")
        self.fo.seek(0,0)
        self.pos=self.fo.tell()
        self.curhdr=None
        self.prvhdr=self._pseudo_header()
        return False
        
    # Tape Operation: Rewind Unload
    def run(self):
        self._check_loaded("run")
        self.fo.close()
        self.loaded=False
        return
        
    # Tape Operation: Write a data block
    def write(self,bytes=None):
        self._check_loaded("write")
        self._check_ro()
        self._check_at_header()
        if bytes==None:
            if self.buffer==None:
                raise TypeError("Buffer empty and no data provided on write")
            else:
                pass
        else:
            self.put_buffer(bytes)
        curpos=self.fo.tell()
        curhdr=header(len(bytes),self.prvhdr.curlen,False)
        curhdr.filepos=curpos  # Header file position
        hdr=curhdr.newhdr()    # Convert the header to bytes

        data=hdr+self.buffer   # Combine header with its data block
        self.buffer=None
        try:
            self.fo.write(data)
        except IOError:
            raise IOError(\
                "IOError while writing data at: %s" % curhdr.filepos)

        # Now that the block has been written..
        self.prvhdr=curhdr     # current block length becomes previous
        self.curhdr=None       # current header object is gone
        self.fo.truncate()     # truncate the emulation file to end of block
        return False
        
    # Tape Operation: Write Tape Mark
    def wtm(self):
        self._check_loaded("wtm")
        self._check_ro()
        self._check_at_header()
        curhdr=header(0,self.prvhdr.curlen,tapemark=True)
        self.pos=self.fo.tell()
        curhdr.filepos=self.pos
        hdr=curhdr.newhdr()
        try:
            self.fo.write(hdr)
        except IOError:
            raise IOError("could not write tape mark at: %s" % curhdr.filepos)
        self.curhdr=None
        self.prvhdr=curhdr
        return

# Defines the format of an AWS header.  The AWS header separates blocks
# of data and tape marks.
#
# An AWS Header consists of 4 fields.  The Indexes column identifies the
# indexes used to retrieve or set a field
#   Indexes Format
#   [0:2]   unsigned little endian  Current block's length in bytes
#   [2:4]   unsigned little endian  Previous block's length in bytes
#   [4]     Binary bits             Flag byte1
#                                      0x40 - This header is a TM 
#                                      0xA0 - This header has a following block
#   [5]     Unused                  Flag byte 2 - always binary zeros
class header(object):
    length=6        # AWS Header length in bytes
    tapemark=0x40   # Flag 1 value for a TM
    block=0xA0      # Flag 1 value for a data block
    
    # Formats a descriptive string of an AWS Header.
    @staticmethod
    def _aws(hdr,pos):
        string="prev=%s,cur=%s,flag1=%02X,flag2=%02X" % hdr
        if pos!=None:
            return "%s @ %s" % (string,pos)
        return "%s @ pos unspecified" % (string)
      
    # Instantiates an instance of a header object from a bytes sequence
    # Returns:
    #   a header object
    @staticmethod
    def aws(hdrbytes,pos=None):
        assert isinstance(hdrbytes,bytes),"%s.header.aws() - 'hdrbytes' "\
            "argument must be a bytes sequence: %s" % (this_module,hdrbytes)
        assert len(hdrbytes)==header.length,"%s.header.aws() - 'hdrbytes' "\
            "argument must be 6 bytes in length: %s" % (this_module,\
                hdrbytes)
         
        # Convert a 6-byte header from the AWS file into a header instance
        curlen=hword_int(hdrbytes[0:2])   # Current block length
        prvlen=hword_int(hdrbytes[2:4])   # Previous block length
        flag1=hdrbytes[4]  # Flag 1
        flag2=hdrbytes[5]  # Flag 2
        
        # Perform some sanity checks
        if (flag1!=header.block) or (flag1!=header.tapemark):
            raise ValueError("Invalid flag 1: %s" % header._aws(hdr))
        if flag2!=0:
            raise ValueError("Invalid flag 2: %s" % header._aws(hdr))
        if flag1==header.tapemark and curlen!=0:
            raise ValueError(\
               "Invalid current TM block length: %s" % header._aws(hdr))

        return header(cur=curlen,prv=prvlen,tapemark=flag1==header.tapemark)

    def __init__(self,cur=0,prv=0,tapemark=False):
        self.curlen=cur          # Length of the following data block
        self.prvlen=prv          # Length of previous data block
        self.tapemark=tapemark   # This is a tapemark (True) or a block (False)
        
        # Set elsewhere.
        self.filepos=None        # Position in the file of this header
        
    # Return a 6-byte AWS header from this header object
    def newhdr(self):
        if self.tapemark:
            if self.curlen!=0:
                raise ValueError("cur length of tapemark must be zero: %s" %\
                    self.curlen)
            # Return a TM header
            flag=header.tapemark
        else:
            # Return a block header
            flag=header.block
            
        hdr=bytearray(header.length)
        hdr[0:2]=hword_bytes(self.curlen)
        hdr[2:4]=hword_bytes(self.prvlen)
        hdr[4]=flag

        return bytes(hdr)

    def __str__(self):
        return "prev=%s,cur=%s,TM=%s @%s" % \
            (self.prvlen,self.curlen,self.tapemark,self.filepos)
        
# media.py expects this function to be available
def register_devices(dtypes):
    lst=[0x3410,0x3420,0x3422,0x3430,0x3480,0x3490,0x3590,0x8809,0x9347]
    for x in lst:
        string="%04X" % x
        dtypes.dtype(string,awstape)
        dtypes.dndex(dtypes.number(x),string)
        awstape.devices[string]=(x,1)
    dtypes.dtype("tape",awstape)

if __name__=="__main__":
    raise NotImplementedError("awsutil.py - only intended for import")