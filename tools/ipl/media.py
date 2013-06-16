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

# Utility module for the handling of Hercules device emulation media.  All
# access in Python to Hercules media types is through this module.
#
# This module is one of a number of modules that support Hercules emulated
# device media:
#
#    media.py      This module.  Root module for handling of all Hercules
#                  emulated media: card images, AWS tape image file, FBA
#                  image file or CKD image file.  All image files are
#                  uncompressed.
#    recsutil.py   Python classes for individual records targeted to a device
#                  type: card, tape, fba or ckd
#    rdrpun.py     Handles writing and reading card decks.
#    awsutil.py    Handles writing and reading AWS tape image files.
#    fbautil.py    Handles writing and reading FBA uncompressed image files.
#    ckdutil.py    Handles writing and reading CKD uncompressed image files.
#
# A module wanting to access Hercules emulated device media will import this
# module:
#   
#   import media                  # Make Python device emulation available
#   dev=media.device(type)        # Create an emulated device.
#   dev.record(parms)             # Create a set of device specific records
#   dev.create(path)              # Creates the device image file
#
# The record() method will have different parameters depending upon the device
#

import functools          # Access compare to key function for sorting
import objutil            # Access the generic object module classes
import sys                # Access to command line arguments
# Media related modules
import recsutil    # Access device-specific record classes
import rdrpun      # Access the card deck handler
import awsutil     # Access AWS tape image handler
import fbautil     # Access FBA DASD image handler
import ckdutil     # Access CKD DASD image handler

# Note: this module requires Python 2.6 or greater

class registry(object):
    # This container class provides the vehicle by which the various handler
    # modules register their devices.  An instance is passed to the handler 
    # for registering when the handlers register_devices function is called.
    #
    # registry Overloading Methods
    #   __getitem__   Used to retrieve the class or dtype as determined
    #                 by the Python type of the item.  Strings return the
    #                 dtype.  Integers return
    #
    # registry Instance Methods
    #   dtype  Register a device type and the class that supports it.
    #   dndex  Returns an integer suitable for registering or retrieving
    #          a device number and model.  The dndex is an internal value
    #          used by the registry class.
    #   number Register a device number and model number and its
    #          corresponding dtype.
    #   
    def __init__(self):
        self.dtypes={}     # String device types mapped to utility class
        self.dindexes={}   # Device and model number indexes mapped to device
                           # type strings
    def __getitem__(self,value):
        # Returns the registered value
        if type(value)==type(0):
            # Integer, so must be going after device index's device type
            if value<0:
                raise ValueError("device index must not be negative: %s" \
                    % value)
            try:
                return self.dindexes[value]
            except KeyError:
                device,model=divmod(value,256)
                raise ValueError(\
                    "unrecognized device %04X model %02X index: %s" \
                    % (device,model,value))
        if type(value)==type(""):
           # String, so must be going after device type's class
           try:
               return self.dtypes[value]
           except KeyError:
               raise ValueError("unrecognized device type: '%s'" % value)
        raise TypeError("Invalid registry type: %s" % type(value))
    def dndex(self,di,dt):
        # Only the first device index is added to the dictionary
        # Where the same device index is used for multiple device types, device
        # type must be used to differentiate.
        try:
            self.dindexes[di]
        except KeyError:
            self.dindexes[di]=dt
    def dtype(self,dt,cls):
        self.dtypes[dt]=cls
    def number(self,device,model=0):
        # Convert a device number and model number into a device index
        if device<0 or device>65535:
            raise ValueError("device must be between 0 and 65535: %s" \
                % device)
        if model<0 or model>255:
            raise ValueError("model must be between 0 and 255: %s" % model)
        return device*256+model

dtypes=registry()  # Registry instance holding registered device types
for x in [rdrpun,awsutil,fbautil,ckdutil]:
    x.register_devices(dtypes)

class device(object):
    # Create the generic media device.  This class stages records destined
    # for a Hercules emulating device.  The emulating device media is created
    # as the final step of the process my means of the create() instance
    # method.  The create() instance method uses the appropriate media handler
    # in conjunction with the appropriate media utility module to create
    # the emulating device media.
    handlers={}   # Maps record type to media_handler class name
    def init():
        device.handlers["awstape"]=tape_handler
        device.handlers["punch"]=card_handler
        device.handlers["tape"]=tape_handler
        device.handlers["fba"]=fba_handler
        device.handlers["ckd"]=ckd_handler
    init=staticmethod(init)
    def __init__(self,dtype,debug=False):
        self.dtype=dtype    # Device type
        self.hndcls=None    # The device handler class for this device
        self.devcls=None    # Device utility class
        self.reccls=None    # The recsutil record class list for this device
        self.handler=None   # media handler class for this device
        self.records=[]     # List of records to create media
        self.sequence=[]    # List of sequenced records
        self.media=None     # Device utility instance of media
        try:
            self.devcls=dtypes[dtype]
            if debug:
                print("media.py: debug: self.devcls=%s" % self.devcls)
        except KeyError:
            raise ValueError("invalid device type: %s" % dtype)
        try:
            self.hndcls=device.handlers[self.devcls.__name__]
            self.reccls=self.hndcls.record
            if debug:
                print("media.py: debug: self.hndcls=%s" % self.hndcls)
                print("media.py: debug: self.reccls=%s" % self.reccls)
        except KeyError:
            raise ValueError(\
                "device media handler class unrecognized: %s" \
                % self.devcls.__name__)
    def __str__(self):
        return "device(%s) device class=%s, record class=%s" \
            % (self.dtype,self.devcls.__name__,self.reccls.__name__)
    def create(self,path=None,minimize=False,comp=False,progress=False,debug=False):
        # Create the media handler used to build the media
        #self.handler=self.hndcls(path)
        # To create the medium, a host path is required for the emulating file.
        # The handler class does the actual medium creation and requires the path.
        # Setting the path may occur:
        #   - When the handler class is instantiated or
        #   - Later by using the handler.set_path method or
        #   - At the latest when this method is called.
        #
        # Likewise the actual creation of the handler class instance may occur:
        #   - When the device.create_handler method is called (with or without
        #     a path), or
        #   - At the latest when this method is called.
        if self.handler is None:
            self.create_handler()
        if self.handler.path is None:
            if path is None:
                raise ValueError("media.py - ERROR - device.create - path is "
                        "required")
            else:
                self.handler.set_path(path)
        else:
            if path is not None:
                print("media.py - WARNING - path already specified in handler, "
                    "ignoring: %s" % path)
        
        self.sequence=self.handler.sequence(self.records)
        if debug:
            for x in self.sequence:
                print("media.py: debug: in device.create: %s" % x)
        if minimize:
            last=self.sequence[-1]
            if debug:
                print("media.py: debug: in device.create: last=%s" % last) 
            dev_size=self.handler.size(\
                self.devcls,self.dtype,last=last.recid,comp=comp)
        else:
            dev_size=self.handler.size(self.devcls,self.dtype)
        self.media=self.handler.media(self.devcls,size=dev_size,\
            progress=progress)
        self.handler.initialize(self.sequence,debug=debug)
        self.handler.close(debug=debug)
    def create_handler(self,path=None):
        self.handler=self.hndcls(path)
    def query_size(self,last=None,comp=False):
        return self.devcls.size(self.dtype,hwm=last.recid,comp=comp)
    def record(self,rec):
        if not isinstance(rec,self.reccls):
            raise TypeError("device requires record class %s: %s" \
                % (self.devcls.__name__,rec.__class__.__name__))
        self.records.append(rec)

class handler(object):
    # This is the superclass for all media handlers.  Media handlers are 
    # device type specific, but support a generic interface used by a device
    # instance.  This class defines the handler interface
    #
    # To create a media emulating device file for device type xxx:
    #      d=xxx_handler(path_to_file)
    #      seq_list=d.sequence(record_list)
    #      med_size=d.size(dtype,minimize=None|seq_list)
    #      d.media(devcls,size=med_size)
    #      d.initialize(seq_list)
    #      d.close()
    @classmethod
    def model(cls,string):
        # Given a device type string, provide the hex device type and model
        # Raises KeyError exception if an invalid string is presented
        raise NotImplementedError(\
            "%s class must provide model() class method" \
            % cls.__name__)
    def __init__(self,path=None):
        # Attributes from arguments
        self.path=path  # The path for the emulating media file
        # Attributes form size() instance method
        self.comp=None  # Whether compression is to be accommodated
        self.dtype=None # device type
        self.dsize=None # device size in device specific units
        # Attributes from media() instance method
        self.dev=None   # device instace from utility module
    #
    # handler instance methods
    def ckvalid(self,rec,strict=True):
        # Raise a TypeError or print a message if record instance is not
        # valid for the handler
        if self.valid(rec):
            return
        msg="record class %s is not valid for %s device" \
             % (rec.__class__.__name__,self.dtype)
        if strict:
           raise TypeError(msg)
        print("Warning: %s" % msg)
    def set_path(self,path):
        self.path=path
    def valid(self,rec):
        # Return True/False if record instance is valid for the handler
        return isinstance(rec,self.__class__.record)
    #
    # handler subclass required methods
    def close(self):
        # complete the creation of the device file
        raise NotImplementedError(\
            "%s class must provide close() method" \
            % self.__class__.__name__)
    def initialize(self,reclst):
        # place the record list, reclst, on the device media.
        raise NotImplementedError(\
            "%s class must provide initialize() method" \
            % self.__class__.__name__)
    def media(self,dtype,size=None):
        # creates the emulating media file.  For
        raise NotImplementedError(\
            "%s class must provide media() method" \
            % self.__class__.__name__)
    def sequence(self,reclst):
        # This method sequences the records for emulating media.  It returns
        # a sequenced list.  For sequential media, reclst should be returned
        # unaltered.
        raise NotImplementedError(\
            "%s class must provide sequence() method" \
            % self.__class__.__name__)
    def size(self,dtype,minimize=None,comp=False):
        # This method provides the size of the emulating media in media 
        # specific terms.  The returned value is media type specific.
        # For card or tape:
        #     The value None may be returned. Minimize and compressable
        #     arguments are ignored
        # For fba or ckd:
        #     The size of the requested media must be returned in terms of
        #     sectors for fba or cylinders for ckd.
        #     If a record list is provided for the minimize argument, the
        #     size returned is optimized for the records targeted to the 
        #     device.  If compressable=True is specified the size will
        #     ensure the device is a candidate for compression.
        raise NotImplementedError(\
            "%s class must provide size() method" \
            % self.__class__.__name__)

class card_handler(handler):
    # Card deck media handler
    dclass="CARD"
    record=recsutil.card
    @classmethod
    def model(cls,string):
        # Return the hex device type and model as a tuple
        # Raises KeyError if an invalid dtype string is supplied
        return rdrpun.rdrpun_devices[string]
    def __init__(self,path):
        handler.__init__(self,path)
    def close(self,debug=False):
        # complete the creation of the device file
        self.dev.unload()
    def initialize(self,reclst,strict=True,debug=False):
        # place the card instances on the emulated media
        for r in reclst:
            self.ckvalid(r,strict)
            self.dev.punch(r.content)
    def media(self,devcls,size=None,progress=False):
        # create the device object
        self.dev=devcls.load(self.path)
    def sequence(self,reclst):
        # sequence the card instances for placement on the media
        return reclst    # card instance are placed in the sequence provided
    def size(self,devcls,dtype,last=None,comp=False):
        # Return the device size in media specific units
        return None      # card decks have variable sizes

class ckd_handler(handler):
    # CKD DASD media handler
    dclass="CKD"
    record=recsutil.ckd
    @classmethod
    def model(cls,string):
        # Return the hex device type and model as a tuple
        # Raises KeyError if an invalid dtype string is supplied
        dev=ckdutil.ckd.geometry[string]
        return (dev.edevice,dev.emodel)
    @staticmethod
    def info(string,keylen=0,datalen=0):
        # Returns the ckd_info instance for a CKD device type string and the block
        # provided key and data length
        return ckdutil.ckd_info(string,keylen=keylen,datalen=datalen)
    def __init__(self,path):
        handler.__init__(self,path)
    def close(self,debug=False):
        # complete the creation of the device file
        self.dev.detach(debug=debug)
    def initialize(self,reclst,strict=True,debug=False):
        # place the ckd instances on the emulated media
        if debug:
            self.dev.dump(enable=False)
        for r in reclst:
            self.ckvalid(r,strict)
            self.dev.seek(cc=r.cc,hh=r.hh,debug=debug)
            self.dev.write(r.cc,r.hh,r.r,key=r.key,data=r.data,debug=debug)
    def media(self,devcls,size=None,progress=False):
        # create the device object
        self.dev=devcls.new(self.path,self.dtype,size=size,progress=progress)
    def sequence(self,reclst):
        # sequence the ckd record instances for placement on the media.
        newlist=[]
        for x in reclst:
            newlist.append(x)
        newlist.sort()
        return newlist
    def size(self,devcls,dtype,last=None,comp=False):
        # Return the device size in media specific units
        # Use the device class passed
        # last is the recsutil record id of the last record on the device
        size=devcls.size(dtype,hwm=last)
        # size is the last used cylinder of the device
        self.comp=True
        self.dtype=dtype
        self.dsize=size
        return self.dsize

class fba_handler(handler):
    # FBA DASD media handler
    dclass="FBA"
    record=recsutil.fba
    @classmethod
    def model(cls,string):
        # Return the hex device type and model as a tuple
        # Raises KeyError if an invalid dtype string is supplied
        dev=fbautil.fba.sectors[string]
        return (dev.devtyp,dev.model)
    def __init__(self,path):
        handler.__init__(self,path)
    def close(self,debug=False):
        # complete the creation of the device file
        self.dev.detach()
    def initialize(self,reclst,strict=True,debug=False):
        # place the fba instances on the emulated media
        for r in reclst:
            self.ckvalid(r,strict)
            self.dev.write(r.content,sector=r.recid)
    def media(self,devcls,size=None,progress=False):
        # create the device object
        self.dev=fbautil.fba.new(self.path,self.dtype,size=size,comp=False)
    def sequence(self,reclst):
        # sequence the fba record instances for placement on the media
        sorted_list=[]
        for x in reclst:
            sorted_list.append(x)
        sorted_list=sorted(sorted_list,\
            key=functools.cmp_to_key(recsutil.fba.compare))
        return sorted_list
    def size(self,devcls,dtype,last=None,comp=False):
        # Return the device size in media specific units
        # Use the device class passed
        size=devcls.size(dtype,hwm=last,comp=comp)
        self.comp=comp
        self.dtype=dtype
        self.dsize=size
        return self.dsize

class tape_handler(handler):
    # AWS tape media handler
    dclass="TAPE"
    record=recsutil.tape
    @classmethod
    def model(cls,string):
        # Return the hex device type and model as a tuple
        # Raises KeyError if an invalid dtype string is supplied
        return awsutil.awstape.devices[string]
    def __init__(self,path):
        handler.__init__(self,path)
    def close(self,debug=False):
        # complete the creation of the device file
        self.dev.run()
    def initialize(self,reclst,strict=True,debug=False):
        # place the tape instances on the emulated media
        for r in reclst:
            self.ckvalid(r,strict)
            if r.tm:
                self.dev.wtm()
                continue
            self.dev.write(r.content)
    def media(self,devcls,size=None,progress=False):
        # create the device object
        self.dev=devcls.scratch(self.path)
    def sequence(self,reclst):
        # sequence the tape record instances for placement on the media
        return reclst    # tape records are placed in the sequence provided
    def size(self,devcls,dtype,last=None,comp=True):
        # Return the device size in media specific units
        self.comp=True
        self.dtype=dtype
        return None

device.init()  # Setup record to handler mapping

def usage():
    print("./media.py dtype image_file")

if __name__=="__main__":
    raise NotImplementedError("media.py - intended for import only")
    # Comment out the preceding statement to run the following tests.
    
    if len(sys.argv)!=3:
        usage()
        sys.exit(1)
    print(ckdutil.ckd.geometry[sys.argv[1]])
    dev=device(sys.argv[1])
    dev.create(sys.argv[2],progress=True)
    sys.exit(0)