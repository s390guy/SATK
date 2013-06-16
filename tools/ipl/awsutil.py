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
#    awsutil.py    This module. Handles writing and reading AWS tape image
#                  files.
#    fbautil.py    Handles writing and reading of FBA image files.
#    ckdutil.py    Handles writing and reading of CKD image files.
#
# See media.py for usage of AWS tape file images

import struct

class awstape(object):
    # To open a new unitialized AWS scratch tape:  awstape.scratch(filename)
    #    New scratch tapes are always opened as read/write
    # To open an existings AWS tape: awstape.mount(filename,ro=True|False)
    #    Existing AWS tapes are opened read-only by default
    # It is recommended to use either the mount or scratch methods to open
    # an AWS tape file rather than instantiating 
    record=["tape","tm"]  # recsutil class names of tape records
    devices={}     # Dictionary mapping dtype strings to hex device type and model
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
        if struct.calcsize(header.structure)!=header.length:
            raise ValueError(\
                "Internal errror: AWS structure definition not 6 bytes")
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
    def _read_hdr(self):
        filedata=self._read_file(header.length,"block header")
        position=self.pos-header.length  # Header file position
        curhdr=header.aws(filedata,pos=position)
        curhdr.filepos=position
        return curhdr
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
    def bsf(self):
        self._check_loaded("bsf")
        while not self.bsb():
            pass
        return True
    def fsb(self):
        self._check_loaded("fsb")
        self._check_at_header()
        self.curhdr=self._read_hdr()
        self.fo.seek(self.curhdr.curlen,1)
        self.buffer=None
        self.prvhdr=self.curhdr
        self.curhdr=None
        return self.prvhdr.tapemark
    def fsf(self):
        self._check_loaded("fsf")
        while not self.fsb():
            return True
    def get_buffer(self):
        if self.buffer==None:
            raise TypeError("data buffer empty")
        buffer=self.buffer
        self.buffer=None
        return buffer
    def put_buffer(self,data):
        if len(data)==0:
            raise TypeError("can not put_buffer of zero length")
        self.buffer=data
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
    def rew(self):
        self._check_loaded("rew")
        self.fo.seek(0,0)
        self.pos=self.fo.tell()
        self.curhdr=None
        self.prvhdr=self._pseudo_header()
        return False
    def run(self):
        self._check_loaded("run")
        self.fo.close()
        self.loaded=False
        return
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
        curhdr.filepos=curpos
        hdr=curhdr.newhdr()
        data="%s%s" % (curhdr.newhdr(),self.buffer)
        self.buffer=None
        try:
            self.fo.write(data)
        except IOError:
            raise IOError(\
                "IOError while writing data at: %s" % curhdr.filepos)
        self.prvhdr=curhdr
        self.curhdr=None
        self.fo.truncate()
        return False
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

class header(object):
    structure="<HHBB"
    length=6
    tapemark=0x40
    block=0xA0
    def _aws(hdr,pos):
        str="prev=%s,cur=%s,flag1=%02X,flag2=%02X" % hdr
        if pos!=None:
            return "%s @ %s" % (str,pos)
        return "%s @ pos unspecified" % (str)
    _aws=staticmethod(_aws)
    def aws(hdrstring,pos=None):
        # Convert a 6-byte header from the AWS file into a instance of header
        if len(hdrstring)!=header.length:
            raise ValueError(\
                "block header length not 6 bytes: %s" % len(hdrstring))
        hdr=unpack(header.structure,hdrstring)
        curlen=hdr[0]   # Current block length
        prvlen=hdr[1]   # Previous block length
        flag1=hdr[2]    # Flag 1
        flag2=hdr[3]    # Flag 2
        if (flag1!=header.block) or (flag1!=header.tapemark):
            raise ValueError("Invalid flag 1: %s" % header._aws(hdr))
        if flag2!=0:
            raise ValueError("Invalid flag 2: %s" % header._aws(hdr))
        if flag1==header.tapemark and curlen!=0:
            raise ValueError(\
               "Invalid current block length: %s" % header._aws(hdr))
        return header(hdr[0],hdr[1],flag==header.tapemark)
    aws=staticmethod(aws)
    def __init__(self,cur=0,prv=0,tapemark=False):
        self.curlen=cur          # Length of the following data block
        self.prvlen=prv          # Length of previous data block
        self.tapemark=tapemark   # This is a tapemark (True) or a block (False)
        self.filepos=None        # Position in the file of this header
    def newhdr(self):
        # Return a 6-byte AWS header from this instance of header
        if self.tapemark:
            if self.curlen!=0:
                raise ValueError("cur length of tapemark must be zero: %s" %\
                    self.curlen)
            return struct.pack(header.structure,\
                self.curlen,self.prvlen,header.tapemark,0)
        return struct.pack(header.structure,\
            self.curlen,self.prvlen,header.block,0)
    def __str__(self):
        return ("prev=%s,cur=%s,TM=%s @%s" % \
            self.prvlen,self.curlen,self.tapemark,self.filepos)
        
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
    print("awsutil.py is only intended for import")