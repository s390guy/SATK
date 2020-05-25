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

# This module manages a FBA control interval.  A control interval is a fixed length
# bytesarray usually of a length in multiples of 512 bytes.  A control interval
# contains logical data records of fixed or varying lengths, and control information
# related to the control interval itself and the logical data records.  Logical data
# records are added from the beginning of the control interval and added at increasing
# offsets within the control interval.  Control information starts at the end of the 
# control itnerval and added at decreasing offsets within the control interval.
# Situated between the logical data records and the control information is usually
# an area unused positions or free space.  It is possible to have no free space
# available.  This is the basic structure of a control interval:
#
#   +--------------------------------------------------------------------+
#   | record | record | record ->|        free space       |<-  controls |
#   +--------------------------------------------------------------------+
#
# The goals of this module are two-fold.  First provide a Python mechanism for the
# creation and access of control intervals.  Second, provide a high-model for
# control interval use by a non-Python program.  Because of the second goal the
# implementation will emphasize mechanisms that might not be typical within Python.
#
# A control interval stores logical data records within the control interval (CI).
# Logical data records are generally organized for sequential access.  However,
# multiple logical data records of the same length, with the appropriate control 
# information, can be accessed for either reading or updating in a random basic.  A
# CI organized for random access may also be read sequentially.
#
# Control intervals are, therefore, accessed and created in three modes:
#
#   - READ mode provides sequential access to logical data records within a CI,
#   - WRITE mode provides sequential addition of logical data records to a CI, and
#   - SLOT mode provides random access to a slot.
#
# This module provides functions for creation of a CI accessed in one of the three
# modes by an object.  See the descriptions associated with "Control Interval Object
# Creation Functions" for details on the overall usage of the objects and individual
# class methods for argument usage.

this_module="ci.py"

# Python imports: None
# SATK imports:
from hexdump import dump    # Get the dump function for hex display

# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exception string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)



#
#  +---------------------------------+
#  |                                 |
#  |   Control Interval Exceptions   |
#  |                                 | 
#  +---------------------------------+
#

# Base class for Control Interval Exceptions is CIError.  The CIError excaption
# should never be caught.  It represents a programming error.  Subclasses of CIError
# represent exceptional conditions that should be caught andprocessed by a method's 
# caller when thrown.  Subclasses of CIError can be thought of as "return codes".

class CIError(Exception):
    def __init__(self,msg=""):
        self.msg=msg
        super().__init__(self.msg)
        
# This excpetion is raised if no more logical control records are present in the
# control interval or a referenced slot does not exist.
class CIEnd(CIError):
    def __init__(self,slot=None):
        self.slot=slot
        if slot is None:
            msg="CI has no more records"
        else:
            msg="slot %s does not exist"
        super().__init__(msg=msg)


# This excpetion is raised when end-of-file is detected as either a RDF flag or
# software end-of-file control interval.
# Instance Argument:
#   src  A string identifying the source of the end-of-file condition
#
# Use either:
#  CIEof("RDF") for an RDF flag triggered end-of-file condition
#  CIEof("SEOF") for a software end-of-file control interval
class CIEof(CIError):
    def __init__(self,src):
        self.src=src    # Source of end-of-file condition
        super().__init__(msg="CI %s end-of-file detected" % typ)


# This excpetion is raised if the control interval does not have enough room to
# add the record.
# Instance Argument:
#   available  The number of bytes available in the control interval
class CIFull(CIError):
    def __init__(self,requested,available):
        self.requested=requested   # Requested bytes in the control interval
        self.available=available   # Available bytes in the control interval
        super().__init__(msg="CI bytes available, %s, can not contain requested" \
            % (available,requested))
        

# This exception is raised if the supplied slot number is invalid
# Instance Argument:
#   slot  The invalid slot number
class CISlot(CIError):
    def __init__(self,slot):
        self.slot=slot   # Invalid slot number
        super().__init__(msg="CI invalid slot: %s" %slot)


# This exception is raised if the requested slot is unused (its content meaningless)
# Instance Argument:
#   slot  The invalid slot number
class CIUnused(CIError):
    def __init__(self,slot):
        self.slot=slot   # Invalid slot number
        super().__init__(msg="CI slot not in use: %s" %slot)

#
#  +------------------------------------------------+
#  |                                                |
#  |   Control Interval Object Creation Functions   |
#  |                                                | 
#  +------------------------------------------------+
#

# These functions instantiate a control interval object, subclass of CI, based
# upon what you want to do with the the CI.  The use cases break down into
# four, the word in upper case used to identify the use case:
#
#   1 - WRITE sequential logical data records to a new CI (WRITE mode)
#   2 - READ sequentail logical data records from an existing CI (READ mode)
#   3 - UPDATE data in a slot or change the slots status in the CI (SLOT mode)
#   4 - SEOF creation.
#
# For each use case various object methods (M) or module functions (F) are available.
# The new() or open() module functions create an object reusable for another instance
# of the same use case.  The seof() module function creates a bytearray sequence, 
# not a CI object.
#
#      Use Case   READ        WRITE       UPDATE       SEOF
# Type  Method
#
#   F   open()      X            -           X
#   F   new()       -            X           X
#   F   seof()      -            -           -          X
#   M   read()      X            -           X
#   M   write()     -            X           X
#   M   avail()     -            -           X
#   M   seof()      -            X           X
#   M   changed()   X            X           X
#   M   isEMPTY()   X            X           X
#   M   isSEOF()    X            X           X
#   M   eof()       -            X           X
#   M   close()     X            X           X
#   M   open()      X            -           X
#   M   new()       -            X           X

# F new()     creates an empty slots CI object or empty CI object for sequential
#             writing of logical data records.  The returned objects close() method
#             returns the updated control interval as a bytearray sequence.
# F open()    creates a CI object that updates an existing CI's slots object or 
#             sequentially reads logical data records.  The returned object's close()
#             method returns the updated CI's slots as a bytesarray sequence or ends
#             reading of logical data records
# F seof()    creates a software end-of-file bytearray control interval.
# M read()    read sequentially logical data records or a slot's content from the CI
# M write()   write sequentially logical data records or upsate a slot's content to
#             the CI.
# M avail()   Make a slot available for new content, making its current content
#             unavailable.
# N changed() Whether the CI has been updated
# M isEMPTY() Whether any logical data records are present.
# M isSEOF()  Whether the current CI is a software end-of-file CI.
# M status()  Determine the CI's status, updated or not.
# M eof()     Indicate in last
# M close()   Retrieve the CI and make the object ready for reuse.
# M seof()    Use the same object to create a SEOF CI after closed.
# M open()    reuse the same object for another CI of the same use case.
# M new()     reuse the seme object for another CI of the same use case
#
# See each function's or method's description for argument details.
#
# The initial object creation should use the new() or open() module function as
# appropriate.  The same object becomes available for re-use after the current CI
# is closed, following which the ojbects new() or open() method may be used.


# This function creates an empty control interval for sequential writing or 
# updating of empty slots.
# Function Arguments:
#   cisize  The size of the control interval to be created (multiple of 512 bytes).
#           Required.
#   size    Specify the size of each slot.  If not specified an empty CI object
#           for sequential writing is created.
#   slots   Specify the number of slots to be created within the CI object.  If
#           ommitted, as many slots of the requested size are created.
#   debug   Whether debug messages are to be generated.  Defaults to False.
def new(cisize,size=0,slots=None,debug=False):
    if size:
        return CISlots(CISlots.new(cisize,size,slots=slots,debug=debug),new=True,\
            debug=debug)
    return CIWrite(CIWrite.new(cisize),new=True,debug=debug)


# This function creates a CI object that allows sequential reading or updating
# of an existing CI bytearray sequence.
# Function Argument:
#   ci      An existing control interval as a bytes/bytearray sequence
#   update  Specify True to perform slot updates.
#           Specify False to perform sequential reads of logical data records.
#           Defaults to False.
#   debug   Whether debug messages are to be generated.  Defaults to False.
def open(ci,update=False,debug=False):
    if update:
        return CISlots(ci,debug=debug)
    return CIRead(ci,debug=debug)


# This function creates a new software end-of-file control interval bytearray 
# sequence.
def seof(cisize,debug=False):
    return CIWrite.new(cisize,seof=True,debug=debug)



#
#  +---------------------------------------+
#  |                                       |
#  |   Control Interval Definition Field   |
#  |                                       | 
#  +---------------------------------------+
#

# Instance Arguments:
#   c    Specify an integer to create a new CIDF for a control interval.
#        Specify the content as a bytes or bytearray sequence.  Required
class CIDF(object):
    def __init__(self,c):
        if isinstance(c,int):
            # Initialize a new CIDF for a control interval
            self.offset=0            # Initialize the free space starting offset
            self.length=c-4          # Initialize the length of the free space

        elif isinstance(c,(bytes,bytearray)):
            assert len(c) == 4,"%s 'c' sequence must be four bytes: %s" \
                % (eloc(self,"__init__"),len(c))

            # Update CIDF data from actual bytes from the control interval
            self.offset=int.from_bytes(c[0:2],byteorder="big",signed=False)
            self.length=int.from_bytes(c[2:4],byteorder="big",signed=False)

        else:
            raise ValueError(\
                "%s 'c' argument must be either an integer or a bytes/bytearray: %s"\
                    % (eloc(self,"__init__"),c))

    # Returns the length of a CIDF
    def __len__(self):
        return 4   #  A CIDF is always four bytes in length

    def __str__(self):
        return "%s - free space offset: %s  free space length: %s" \
            % (self.__class__.__name__,self.offset,self.length)

    # Returns True if this is a software end-of-file CI. False otherwise.
    def isSEOF(self):
        return self.offset == 0 and self.length == 0

    # Convert the CIDF to a bytes sequence
    def to_bytes(self):
        assert self.offset>=0,"%s self.offset must not be negative: %s" \
            % (eloc(self,"to_bytes"),self.offset)
        assert self.length>=0,"%s self.length must not be negative: %s" \
            % (eloc(self,"to_bytes"),self.length)

        b=bytearray(4)
        b[0:2]=self.offset.to_bytes(2,byteorder="big",signed=False)
        b[2:4]=self.length.to_bytes(2,byteorder="big",signed=False)
        assert len(b)==4,"%s length not 4: %s" % (self.__class__.__name__,len(b))
        return b


#
#  +----------------------------+
#  |                            |
#  |   Recod Definition Field   |
#  |                            | 
#  +----------------------------+
#

# Creates a new RDF or establishes the content of an existing RDF.
# Instance Arguments:
#   value    For a new RDF the numeric value of the RDF
#            For an existing RDF, the bytes/bytearray of three elements of the 
#            existing RDF.  Required.
# These arguments are used only by a new RDF:
#   eof      Specify True that this is the last control interval of the data set
#            or group of control intervals.  Specify False otherwise.  Default False.
#   paired   Specity True if this RDF has a paired RDF to its left.  Specify False
#            otherwise.  Default False.
#   spanned  Specify 'first', 'middle' or 'last' for a spanned record.  Otherwise
#            specify None.  Default None.
#   number   Specify True if this RDF's value argument is the number of equal length
#            records with the length of the RDF to its right.  Specify False if the
#            value argument is the length of the record.  Default False.
#   avail    Specify True if this slot is not in use.  Specify False if this slot
#            contains a logical data record.  Default False.
# 
# Exceptions:
#   CIError if flag byte reserved bits are not zero
class RDF(object):
    # Spanned record flags:
    spanned_flags={"first":0x10,"middle":0x30,"last":0x20,None:0}

    def __init__(self,value,eof=False,paired=False,spanned=None,number=False,\
                 avail=False,offset=None):
        self.records=1         # Number of records of this size

        # RDF Field Attributes
        self.offset=offset     # CI offset
        self.flags=0           # Flag byte as an integer
        self.value=0           # Numeric valud of the RDF

        # Initialize flag attributes to zero
        self.at_eof=self.paired=self.number=self.avail=self.spanned=0

        if isinstance(value,int):
            # New RDF
            
            # Set flag related attributes from instance arguments
            if eof:
                self.at_eof=0x80     # end-of-file flag 
            if paired:
                self.paired=0x40     # RDF is paired
            if number:
                self.number=0x08     # value argument is number of records
                self.records=value
            if avail:
                self.avail=0x04      # whether slot is available

            # Set the spanned record flags
            try:
                self.spanned=RDF.spanned_flags[spanned]
            except KeyError:
                raise ValueError(\
                    "%s 'spanned' argument must be 'first', 'middle', 'last' or " 
                        "None: %s" % (eloc(self,"__init__"),spanned)) from None
            
            # Set RDF field attribute
            self.value=value                # Set the RDF binary value field
            self.flags=self._make_flags()   # Set the flag field
            self.offset=offset              # RDF CI offset if provided

        elif isinstance(value,(bytes,bytearray)):
            # Existing RDF
            assert len(value)==3,"%s 'value' must be 3 bytes: %s" \
                % (eloc(self,"__init__"),len(value))
            flags=value[0]
            self._ck_flags(flags,eloc(self,"__init__"))

            # Set specific flag attributes from RDF flag field
            self.at_eof = flags & 0x80
            self.paired = flags & 0x40
            self.number = flags & 0x08
            self.avail  = flags & 0x04
            self.spanned= flags & 0x30
            
            # Set RDF field values
            self.flags  = flags
            self.value=int.from_bytes(value[1:3],byteorder="big",signed=False)
            self.offset=offset
            if self.number:
                self.records=self.value

        else:
            raise ValueError(\
                "%s 'value' arguemnt must be an integer or bytes/bytearray: %s" \
                    % (eloc(self,"__init__"),value))

    # Returns the length of an RDF
    def __len__(self):
        return 3

    def __str__(self):
        flags="{0:0>8b}".format(self.flags)

        # Interpret flags
        of=s=p=e=""
        if self.at_eof:
            e="E"
        if self.paired:
            p="P"
        if self.number:
            n="C"
        else:
            n="L"
        if self.avail:
            f="A"
        else:
            f="U"
        if self.spanned:
            ndx= ( self.spanned & 0x30 ) >> 4
            s=" FLM"[ndx]

        # Add offset if available
        if self.offset is not None:
            of="  offset: %s (Ox%X)" % (self.offset,self.offset)
        return "%s value: %s  flags: %s %s%s%s%s%s  records: %s%s  slot: %s" \
            % (self.__class__.__name__,self.value,flags,n,f,s,p,e,\
                self.records,of,self.isSLOT())

    # Checks that flag byte to ensure reserved bits are zero.
    def _ck_flags(self,flags,eloc):
        if (flags & 0b00000011) != 0:
            if self.offset is None:
                o=""
            else:
                o="offset %s (0x%X)" % (self.offset,self.offset)
            raise CIError(msg="%s RDF %s flag reserved bits not zero: 0x%2X" \
                % (eloc,o,flags))
            
    def _ck_seq(self,flags,eloc):
        if (flags & 0b00001100) != 0:
            if self.offset is None:
                o=""
            else:
                o="offset %s (0x%X)" % (self.offset,self.offset)
            raise CIError(msg="%s seq. RDF %s flags inconsistent: 0x%2X" \
                % (eloc,o,flags))
            
    def _ck_number(self,flags,eloc):
        if (flags & 0b01111100 ) != 0b00001000:
            if self.offset is None:
                o=""
            else:
                o="offset %s (0x%X)" % (self.offset,self.offset)
            raise CIError(msg="%s number RDF %s flags inconsistent: 0x%2X" \
                % (eloc,o,flags))
            
    # Combine the flag attributes into the RDF flag field value
    # Exception:
    #   CIError if the reserved flag field bits are not zero.
    def _make_flags(self):
        flags = self.at_eof | self.paired | self.number | self.avail | self.spanned
        self._ck_flags(flags,eloc(self,"_make_flags"))
        return flags

    # Indicate this RDF is the last of the data of the file or group of records
    def eof(self,flag=True):
        if flag:
            self.at_eof = 0x80
            self.flags=self.flags | 0x80
        else:
            self.at_eof = 0
            self.flags = self.flags & 0x7F

    # Return whether this slot is available
    def isAVAIL(self):
        if self.avail:
            return True
        return False

    # Returns whether this slot contains the count of consecutive equal size records
    def isCOUNT(self):
        if self.number:
            return True
        return False

    # Return whehter this RDF signals end-of-file condition
    def isEOF(self):
        if self.at_eof:
            return True
        return False

    # Returns whether this is the first segment of a spanned record
    def isFIRST(self):
        return self.spanned == 0x10

    # Returns whether this is the last segment of a spanned record
    def isLAST(self):
        return self.spanned == 0x20

    # Returns whether this is a length
    def isLENGTH(self):
        return self.number == 0

    # Returns wether this is a middle segment of a spanned record
    def isMIDDLE(self):
        return self.spanned == 0x30

    # Returns wheter the is a spanned record or not
    def isSPANNED(self):
        return not self.spanned

    # Returns whether this is a valid slot RDF
    def isSLOT(self):
        # An RDF for a slot is must be x000 0x00 (mask 0b0111 1011)
        return ((self.flags & 0b01111011 ) == 0b00000000) and self.records==1

    # Indicate this RDF is now paired with one to its left
    def pair(self,flag=True):
        if flag:
            self.paired=0x40
        else:
            self.pared=0

    # Set the slot's availability status.
    # Method Argument:
    #   flag   Specify False to indicate the slot is not available, its in use
    #          Specify True to indicate teh slot is now available, ignore its content.
    #          Required
    def slot(self,flag):
        if flag:
            self.avail = 0x04
        else:
            self.avail = 0

    # Return an RDF as a sequence of bytes
    # Exception:
    #   CIError if the flag field reserved bits are not zero.
    def to_bytes(self):
        b=bytearray(3)
        b[0]=self._make_flags()
        b[1:3]=self.value.to_bytes(2,byteorder="big",signed=False)
        assert len(b)==3,"%s length not 3: %s" % (self.__class__.__name__,len(b))
        return b


#
#  +------------------------------+
#  |                              |
#  |   Control Interval Classes   |
#  |                              | 
#  +------------------------------+
#

class CI(object):
    
    # Flag mask and valid value for various RDF types:
    num_ck = (0b01111111, 0b00001000)  # Check for a number RDF
    res_ck = (0b00000011, 0)    # Check just the reserved bits
    seq_ck = (0b00111111, 0)    # Check for single unspanned RDF (w/(o) pairing)
    slt_ck = (0b01111011, 0b00000000)  # Check for a slot RDF
    spn_ck = (0b00001111, 0)    # Check for single (un)spanned RDF (w/(o) pairing

    # This method determines if a ci length is invalid
    # Method Argument
    #   cisize  the CI size in bytes as an integer
    # Returns:
    #   True if the ci size is not valid
    #   False if the ci size is valid
    @staticmethod
    def cisize_invalid(cisize):
        sectors,excess = divmod(cisize,512)
        return excess != 0

    # Calculates the number of slots that will fit into a given CI size.
    # Method Arguments:
    #   cisize   The CI size in bytes
    #   recsize  The slot size of each slot in bytes
    @staticmethod
    def ci_slots(cisize,recsize):
        return (cisize - 4) // (recsize + 3)

    # Dump the CI in hex format with offset
    # Method Arguments:
    #   ci     a bytes/bytearray sequence of the CI's content
    #   indent a string, usually spaces of the line indent of the dump
    #   string Specify True to return a string.  Specify False to cause the
    #          dump to be printed here.  Default False.
    @staticmethod
    def dump(ci,indent="",string=False):
        assert isinstance(ci,(bytes,bytearray)),\
           "CI dump() - 'ci' argument must be bytes/bytearray: %s" % ci

        s=dump(ci,indent=indent)
        if string:
            return s
        print(s)

    # Returns a bytearray of all binary zeros with cisize length
    # Exception:
    #   CIError if cisize is not a multiple of 512
    @staticmethod
    def new_raw(cisize):
        if CI.cisize_invalid(cisize):
            raise CIError(msg="'cisize' argument not a multiple of 512: %s" % cisize)

        b=bytearray(cisize)
        assert len(b)==cisize,"CIDF new_raw() - bytesarray length not %s: %s" \
            % (cisize,len(b))

        return b

    @classmethod
    def new(cls,*args,**kwds):
        raise NotImplementedError("%s - does not implement new() class method" \
            % cls.__name__)

    def __init__(self,ci,new=False,debug=False):
        self.debug=debug    # Whether debug messages are generated
        self.closed=True    # Whether this object is open (False) or closed (True)

      # The following fields are initialized by the _init() method.  Allows object
      # reuse.
      #
        # The control intreval
        self.ci=None         # The bytes/bytearray of the control interval
        self.cisize=None     # The length of the control interval
        self.mutable=None    # Whether the CI content (self.ci) is mutable.

        # Free space controls
        self.cidf_off=None   # The offset of the CIDF
        self.cidf=None       # The CIDF object for the control interval
        self._seof=None      # Set whether this is a SEOF CI

        # CI Status
        self.updated=False   # Whether the control interval has been updated.

        # Complete intialization for data containing control interval.
        self.free_off=None   # The offset to the start of the free space
        self.free_len=None   # The length of the free space
        self.free_end=None   # Offset of end of free area

        # RDF controls
        self.rdf_end=None    # last (leftmost) RDF offset.
        self.rdf_offset=None # the offset to the right of the first RDF
        self.rdf_area=None   # Size of the RDF area in the CI
        self.rdf_num=None    # The number of RDF's in the RDF area
        self.rdf_excess=None # Any excess bytes after the free area and the RDF area

        # Sequential RDF controls
        #
        # This offset changes during sequential record processing
        # Current offset the the right of the active RDF
        self.rdf_off=None    # Decrement by 3 before reading or writing the RDF
        self.rdf_len=None    # Records of this size are being processed
        self.rdf_recs=None   # Number of records of this read (decr) written (incr)
        self.rdf=None        # The current active RDF

        # Logical data record controls
        self.rdf_list=[]     # The list of RDF's
        self.ldr_off=0       # The offset of the active logical data record
        self.ldr_len=None    # The length of the active logical data record
      #
      # Initialize the previous fields for a new CI

        self._init(ci,new=new)

    def __len__(self):
        return self.cisize

    def __str__(self):
        if self._seof:
            return "SEOF - CI size: %s" % self.cisize
        return self.stats(string=True)

 #
 #  These methods are private and shared by subclasses
 #

    def _closed_error(self,eloc):
        return CIError(msg="%s method may not be called when object has been closed"\
            % eloc)

    # Extracts the CIDF from the control interval
    # Returns:
    #   CIDF object representing the CI CIDF
    def _cidf_read(self):
        return CIDF(self.ci[self.cidf_off:self.cisize])

    # Inserts into the CI the CIDF from a CIDF object
    # Method Argument:
    #   cidf   The CIDF object that is the source for the CI's CIDF.
    def _cidf_write(self,cidf):
        self.ci[self.cidf_off:self.cisize]=cidf.to_bytes()

    # Initializes the object.
    # Method Argument:
    #   ci   A bytes/bytearray sequence of the CI's content
    #   new  Whether this is a new CI (in which case it is by definition changed)
    # Exception:
    #   ValueError  if the presented CI is not a byte/bytearray with a length a 
    #               multiple of 512.
    #   CIError     if an internal inconsistency detected in controls.
    def _init(self,ci,new=False):
        if isinstance(ci,bytes):
            self.mutable=False
        elif isinstance(ci,bytearray):
            self.mutable=True
        else:
            raise ValueError(\
                "%s 'ci' argument must be a bytes/bytesarray sequence: %s" \
                    % (eloc(self,"_init"),ci))
        if CI.cisize_invalid(len(ci)):
            raise ValueError(\
                "%s 'ci' argument not a valid CI size (multiple of 512): %s"
                    % (eloc(self,"_init"),len(ci)))

        # The control interval
        self.ci=ci          # The bytes/bytearray of the control interval
        self.cisize=len(ci) # The length of the control interval
        self.updated=new    # Whether this CI has been changed
        self.closed=False   # Not closed (open)
        
        # Initialize regardles of CI content
        self.rdf=self.ldr_len=None
        self.rdf_list=[]
        self.ldr_off=0

        # Free space controls
        self.cidf_off=self.cisize-4     # The offset of the CIDF
        self.cidf=self._cidf_read()     # The CIDF object for the control interval
        self._seof=self.cidf.isSEOF()   # Set whether this is a SEOF CI
        if self._seof:
            self.free_off=self.free_len=self.free_end=None
            self.rdf_end=self.rdf_area=self.rdf_num=self.rdf_excess=None
            self.rdf_offset=self.rdf_off=None
            return

        # Complete intialization for data containing control interval.
        self.free_off=self.cidf.offset  # The offset to the start of the free space
        self.free_len=self.cidf.length  # The length of the free space
        self.free_end=self.free_off+self.free_len  # Offset of end of free area

        # RDF controls
        self.rdf_end=self.free_off+self.free_len   # last (leftmost) RDF offset.
        self.rdf_offset=self.cidf.offset           # offset right of first RDF
        # Set the number of RDF's
        self.rdf_area=self.cidf_off-self.rdf_end
        self.rdf_num,self.rdf_excess=divmod(self.rdf_area,3)
        self.rdf_off=self.rdf_offset   # offset to the right of the current RDF

        # Perform sanity checks
        self._sanity_checks()
        
        # Initialize CI access mode
        self._init_mode()

    # This method is required by each subclass for mode specific initialization
    # functions.
    def _init_mode(self):
        raise NotImplementedError("%s subclass %s must provide _init_mode() method"\
            % (eloc(self,"_init_mode"),self.__class__.__name__))

    # Perform a low level read of the RDF from a CI
    # Method Arguments:
    #   offset   offset into the CI of the RDF to be read
    #   mask     a mask applied to the flags to determine validity. Defaults to
    #            reserved bits.
    #   valid    value expected after mask applied to the RDF flags
    # Exception:
    #   CIError if masked flags do not resolve to expected value
    def _rdf_read(self,offset,mask=0b0000000,valid=0):
        assert offset <= self.cidf_off,\
            "%s RDF offset must be <= CIDF offset (%s): %s" \
                % (eloc(self,"_rdf_read"),self.cidf_off,offset)

        rdf=RDF(self.ci[offset:offset+3],offset=offset)
        bits= rdf.flags & mask
        if mask and bits != valid:
            raise CIError(msg="%s flags (0x%x) & mask (0x%X) => 0x%X != (0x%X)"\
                "for RDF: %s" \
                    % (eloc(self,"_rdf_read"),rdf.flags,mask,bits,valid,rdf))

        return rdf

    # This method sequentially accesses RDF's handling paired RDF's when found
    # Method Argument:
    #   spanned   Specify True to accept spanned RDF.  Specify False to detect
    #             spanned RDF as an error.  Default False.
    #   eof       Specify True if the last RDF is to be checked for eof.
    # Side Effects:
    #   self.rdf_off   set to the offset of the last RDF read next RDF read
    #   self.rdf_len   set the length of logical data record(s) to be read
    #   self.rdf_recs  set to the number of records to read of this length
    #   self.rdf       set to the left most RDF read by this method
    # Exception:
    #   CIEnd if no more RDF's available
    #   CIEof if the last RDF has the eof flag set and eof checking is enabled
    #   CIError if an RDF does not contain its expected value or a pair is missing.
    def _rdf_read_seq(self,spanned=False,eof=False):
        if self.rdf is None:
            # First RDF being read
            self.rdf_off = self.rdf_offset
            self.ldr_off = 0
        elif eof and self.rdr_off == self.rdf_end:
            # Check if current active (from last call) has EOF flag set
            if self.rdf.isEOF():
                raise CIEof()

        self.rdf_off -= 3
        if self.rdf_off < self.rdf_end:
            raise CIEnd()

        if spanned:
            msk,valid = CI.spn_ck
        else:
            msk,valid = CI.seq_ck
        if not eof:
            msk = msk | 0b10000000
        rdf=self.rdf=self._rdf_read(self.rdf_off,mask=msk,valid=valid)
        self.ldr_len=rdf.value
        self.rdf_recs=1

        if not rdf.isPAIRED():
            return
            
     # The RDF _is_ paired

        if spanned and rdf.isSPANNED():
            # RDF is also spanned and pairing is inconsistent.
            raise CIError(msg="%s spanned RDF must not be paired: %s" \
                % (eloc(self,"_rdf_read_seq"),rdf))

        # Read and process paired RDF
        self.rdf_off -= 3
        if self.rdf_off < self.rdf_end:
            raise CIError(msg="%s CI missing pair for last RDF: %s" \
                % (eloc(self,"_rdf_read_seq"),rdf))

        msk,valid=CI.num_ck
        rdf=self.rdf=self._rdf_read(self.rdf_off,mask=msk,valid=valid)

        # Update number of records for multiple of the same size
        self.rdf_recs=rdf.value

    # Perform sanity checks.
    # Exceptions:
    #   CIError raised if a sanity check fails.
    def _sanity_checks(self):
        if self.free_end > self.cidf_off:
            raise CIError(\
                msg="%s free space intrudes into CIDF (+%s), offset %s + length %s:"\
                    "%s" % (eloc(self,"_sanity_checks"),self.cidf_off,self.free_off,\
                        self.free_len,self.free_end))
        if self.rdf_excess != 0:
            raise CIError(msg="%s RDF area not divisble by three: %s"\
                % (eloc(self,"__init__"),rdf_area))

    
 #
 #  These methods are shared by the subclasses and are public
 #

    # Returns whether this CI has been updated
    def changed(self):
        return self.updated

    #def close(self): 
    #    self.closed=True
        #ci=self.ci
        #self.ci=
    #    return self.ci

    def display(self,indent="",string=False):
        s="%s\n\n%s" % (self.stats(indent=indent,string=True),\
            CI.dump(self.ci,indent=indent,string=True))
        if string:
            return s
        print(s)

    # Return whether this CI is empty (no RDF's present)
    def isEMPTY(self):
        return not self.rdf_num

    # Return whether this CI is a software end-of-file
    def isSEOF(self):
        return self._seof

    def stats(self,indent="",string=False):
        if self.closed:
            s="%sStatus - CI closed" % indent
            if string:
                return s
            print(s)
            return

        if self._seof:
            s="%sSEOF - CI size: %s" % (indent,self.cisize)
        else:
            # Normal CI information
            hdr="{n: <5s} {b: >5s} {x: >4s} {e: >5s} {x: >4s} {l: >5s}"
            fmt="{n: <5s} {b: >5d} {b:0>4X} {e: >5d} {e:0>4X} {l: >5d} {l:0>4X}"

            # Create header
            s=hdr.format(n="Area",b="beg",e="end",l="len",x=" ")

            # Add CI info
            s="%s%s\n%s" % (s,indent,\
                fmt.format(n="CI",b=0,e=self.cisize-1,l=self.cisize))

            # Add logical data area info
            ldr_end=(max(0,self.free_off-1))
            s="%s%s\n%s" % (s,indent,\
                fmt.format(n="LDRs",b=0,e=ldr_end,l=self.free_off))

            # Add free area info
            if self.free_len:
                free_end=self.free_end-1
            else:
                free_end=self.free_end
            s="%s%s\n%s" % (s,indent,\
                fmt.format(n="Free",b=self.free_off,e=free_end,l=self.free_len))

            # Add RDF info
            if self.rdf_area:
                rdf_end=self.cidf_off-1
            else:
                rdf_end=self.cidf_off
            s="%s%s\n%s" % (s,indent,\
                fmt.format(n="RDFs",b=self.rdf_end,e=rdf_end,l=self.rdf_area))

            # Add CIDF info
            s="%s%s\n%s" % (s,indent,\
                fmt.format(n="CIDF",b=self.cidf_off,e=self.cisize-1,l=4))

        s="%s\n\n%sStatus - CI open  changed:%s  empty:%s  seof:%s" \
            % (s,indent,self.changed(),self.isEMPTY(),self.isSEOF())

        if string:
            return s
        print(s)

 #
 #  These methods myst be supplied by the subclass if supported
 #

    # Subclass must supply this method if supported
    def avail(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support avail() method" \
            % (eloc(self,"avail"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def close(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support close() method" \
            % (eloc(self,"close"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def new(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support new() method" \
            % (eloc(self,"new"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def open(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support open() method" \
            % (eloc(self,"open"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def read(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support read() method" \
            % (eloc(self,"read"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def seof(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support seof() method" \
            % (eloc(self,"seof"),self.__class__.__name__))

    # Subclass must supply this method if supported
    def write(self,*args,**kwds):
        raise NotImplementedError("%s subclass %s does not support write() method" \
            % (eloc(self,"write"),self.__class__.__name__))


# This object allows sequential reading of logical data records from an existing CI
class CIRead(CI):

    def __init__(self,ci,debug=False):
        b=ci
        if isinstance(ci,bytearray):
            b=bytes(ci)
        assert isinstance(b,(bytes)),\
            "%s 'ci' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"__init__"),ci)

        super().__init__(b,debug=debug)

    # Initialize READ mode
    def _init_mode(self):
        raise NotImplementedError("CIRead object not implemented")


# This object allows the use of slots in an existing CI or creation of a new CI
# containing slots.
class CISlots(CI):

    @classmethod
    def new(cls,cisize,size,slots=None,debug=False):
        byts=CI.new_raw(cisize)
        assert len(byts) == cisize,\
            "%s new() - CI length (%s) does not match cisize: %s" \
                % (cls.__name__,len(byts),cisize)
        cidf=CIDF(cisize)
        cidf_off=cidf.length
        recs,excess=divmod(cisize,size+3)
        if slots:
            if recs<slots:
                raise CIError(msg="%s new() - cisize (%s) too small for slots (%s),"\
                    " bytes needed: %s" % (cls.__name__,cisize,slots,slots*size))
            else:
                recs=slots
        if __debug__:
            if debug:
                print("%s new() - slots: %s" % (cls.__name__,recs))
        offset=cidf.length
        rdf=RDF(size,avail=True)
        if __debug__:
            if debug:
                print("%s new() - slot %s" % (cls.__name__,rdf))
        rdf=rdf.to_bytes()
        for n,s in enumerate(range(1,recs+1)):
            #print("s:%s n:%s" % (s,n))
            o=offset-(s*3)
            #print("o:%s" % o)
            if __debug__:
                if debug:
                    print("%s new() - RDF %s placed at offset: %s (0x%X)" \
                        % (cls.__name__,n+1,o,o))
            byts[o:o+3]=rdf
        cidf.offset=size*recs
        cidf.length=o-cidf.offset
        if __debug__:
            if debug:
                print("%s new() - %s" % (cls.__name__,cidf))
        byts[cidf_off:cidf_off+4]=cidf.to_bytes()
        assert len(byts) == cisize,\
            "%s new() - CI length (%s) does not match cisize: %s" \
                % (cls.__name__,len(byts),cisize)
        return byts

    def __init__(self,ci,new=False,debug=False):
        if isinstance(ci,bytes):
            b=bytearray(ci)
        else:
            b=ci
        assert isinstance(b,bytearray),\
            "%s 'ci' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"__init__"),b)

        super().__init__(b,new=new,debug=debug)  # Note: calls _init_mode() method

        # Slot controls (See _init_mode() method)
        self.slot_sz=None      # Size of a slot in this CI.  0 means no slots.
        self.slot_num=None     # Number of slots within the CI
        self.rm_rdf=None       # The offset to the right-most RDF.

    # This method validates a slot number is valid.
    # Exception:
    #   CIError raised if the slot is invalid for this CI
    def _ck_slot(self,slot):
        if slot<1 or slot>self.slot_num:
            raise CIError(msg="%s slot number out of range (1=%s): %s" \
                % (eloc(self,"_ck_slot"),self.slot_num,slot))

    # Initialize SLOT mode
    # Exceptions:
    #   CIError - if CI is an SEOF CI
    #             if CI ia empty (no RDF fields)
    #             if an RDF is not valid as a slot RDF
    #             if an RDF has a length different than the first RDF
    def _init_mode(self):
        if self.isSEOF():
            raise CIError(msg="%s SEOF CI can not be accessed in SLOT mode" \
                % eloc(self,"_init_mode"))
        if self.isEMPTY():
            raise CIError(msg="%s empty CI can not be accessed in SLOT mode" \
                % eloc(self,"_init_mode"))

        slot_len=None
        slot_num=0

        # Initialize current RDF offset to the rightmost RDF
        rdf_off=self.rm_rdf=self.cidf_off-3 
        rdf_end=self.rdf_end
        msk,valid=CI.slt_ck
        while rdf_off >= rdf_end:
            rdf=self._rdf_read(rdf_off,mask=msk,valid=valid)
            if not rdf.isSLOT():
                raise CIError(msg="%s RDF %s not valid for a slot: %s" \
                    % (eloc(self,"_init_mode"),self.slot_num+1,rdf))
            if not slot_num:
                slot_len=rdf.value
            else:
                if slot_len != rdf.value:
                    raise CIError(\
                        msg="%s RDF %s has inconsistent slot length (%s): %s" \
                            % (eloc(self,"_init_mode"),slot_num+1,slot_len,rdf))
            slot_num+=1
            rdf_off-=3

        # Initialize slot controls
        self.slot_sz=slot_len
        self.slot_num=slot_num

    # This method returns an RDF object corresponding to a specific slot's RDF.
    def _fetch_rdf(self,slot):
        offset=self._find_rdf(slot)
        rdf=self.ci[offset:offset+3]
        return RDF(rdf,offset=offset)
        
    # This method returns the offset of a specific slot's RDF.
    # Exceptions:
    #   CIError if the slot number is out of range.
    def _find_rdf(self,slot):
        self._ck_slot(slot)                # Validate slot is valid
        return self.cidf_off - (slot * 3)  # Return the slot's RDF CI offset

    # This method returns the offset of a specific slot's content in the CI
    def _find_slot(self,slot):
        return (slot - 1) * self.slot_sz   # Return the slot's content CI offset

    # Convert an RDF object to bytes and insert the rdf into the CI's slot
    def _insert_rdf(self,rdf):
        byts=rdf.to_bytes()
        offset=rdf.offset
        self.ci[offset:offset+3]=byts
        self.updated=True

    # Mark a slot as being available, making its existing content unavailable
    def avail(self,slot):
        rdf=self._fetch_rdf(slot)
        rdf.slot(True)   # Mark the slot as available
        self._insert_rdf(rdf)

    # Reads the content of a slot that in not available (containing known content)
    # Exceptions:
    #   CIError if the slot number is invalid
    #   CIUnused if the slot is available for content (its content is meaningless)
    def read(self,slot):
        rdf=self._fetch_rdf(slot)
        if rdf.isAVAIL():
            raise CIUnused(slot=slot)
        offset=self._find_slot(slot)
        return self.ci[offset:offset+self.slot_sz]

    # Updates a specific slot with new content and marks the slot as in use.
    # Exceptions:
    #   CIError if 
    #     - the new content length does not match the slot size
    #     - the slot number is out of range
    def write(self,byts,slot):
        assert instance(byts,(bytes,bytearray)),\
            "%s 'byts' argument must be bytes/bytearray: %s" \
                % (eloc(self,"write"),byts)
        if len(byts)!=self.slot_sz:
            raise CIError(\
                msg="%s 'byts' argument length must match CI slot size (%s): %s" \
                    % (eloc(self,"write"),len(byts)))

        rdf=self._fetch_rdf(slot)
        rdf.slot(False)
        offset=self._find_slot(slot)
        self.ci[offset:offset+self.slot_sz]=byts
        self.updated=True


# This object allows the sequential writing of logical data records to an empty CI
# Instance Creation:
#   Use module function new(cisize)
#
# Instance Arguments:
class CIWrite(CI):

    @classmethod
    def new(cls,cisize,seof=False,debug=False):
        byts=CI.new_raw(cisize)
        cidf=CIDF(cisize)
        if seof:
            cidf.length=0
        if __debug__:
            if debug:
                print("%s new() - %s" % (cls.__name__,cidf))

        byts[cisize-4:cisize]=cidf.to_bytes()
        assert len(byts) == cisize,\
            "%s new() - CI length (%s) does not match cisize: %s" \
                % (cls.__name__,len(byts),cisize)
        return byts

    def __init__(self,ci,new=False,debug=False):
        b=ci
        if isinstance(ci,bytes):
            b=bytearray(ci)
        assert isinstance(b,bytearray),\
            "%s 'ci' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"__init__"),b)

        super().__init__(b,new=new,debug=debug)

    # Initialize WRITE mode
    def _init_mode(self):
        raise NotImplementedError("CIWrite object not implemented")


# Creates a new control interval or provides access to an existing control interval.
# The ci argument controls which is the case.  New control intervals may only be
# sequentially written to, unless slots are in use.  Existing control intervals may 
# only be read from, unless slots are in use.
#
# Instance Arguemnts for a new control interval:
#   ci     The size of the new control interval in bytes.  Required.
#   seof   Specify True to create a software end-of-file control interval.  Specify
#          False otherwise.  Defaults to False.
#   sanity Specify True to perform a sanity check on the control information during
#          close() method
# Instance Arguments for an existing control interval:
#   ci     The bytes/bytearray sequence constituting the existing control interval.
#          Required.
#   seof   Ignored for an existing control interval.  The control information will
#          determine if this is a sofware end-of-file control interval.
#   sanity Specify True if sanity checks are performed on the control information
#          during object creation.
class CIOld(object):
    ci_states=["CI object being initialized",    # 0
               "Initializing new CI",            # 1
               "Initializing existing CI",       # 2
               "New CI initialized",             # 3
               "Existing CI initialized",        # 4
               "Slot mode",                      # 5
               "Sequential read mode",           # 6
               "Sequential write mode",          # 7
               "Software End-of-file",           # 8
               "New CI needs closing",           # 9
               "Existing CI needs closing",      # 10
               "Closed CI"]                      # 11
               
    def __init__(ci,seof=False,sanity=False):
        self.sanity=sanity # Whether sanity checks are performed on control info.

        # Control interval controls
        self._seof=None     # Whether this CI is a software EOF
        self.ci_len=None    # The length of the control interval
        # CI Status
        self.updated=False  # Whether the control interval has been updated.

        # Actual control interval
        self.ci=None        # The bytes/bytearray of the control interval

        # Free space controls
        self.cidf=None      # The CIDF object for the control interval
        self.cidf_off=None  # The offset of the CIDF withn the control interval
        self.free_off=None  # The offset to the start of the free space
        self.free_len=None  # The length of the free space

        # Slot controls
        self.slot_sz=0      # Size of a slot in this CI.  0 means no slots.
        self.slot_num=0     # Number of slots within the CI

        # RDF controls
        self.rdf_num=None   # The number of RDF's in the control information
        self.rdf_end=None   # The offset of the last RDF in the control interval
        self.rdf_off=None   # The offset right of the active RDF
        self.rdf=None       # The current active RDF
        self.rdf_list=[]    # The list of RDF's

        # Logical data record controls
        self.ldr_off=None   # The offset of the active logical data record
        self.ldr_len=None   # The length of the active logical data record
        
        # CI FSM states:
        #  0   Initial state when CI object created
        #  1   Initializing new CI
        #  2   Initializing existing CI
        #  3   New CI initialized
        #  4   Existing CI initialized
        #  5   Slot mode
        #  6   Sequential read mode (existing CI) - uses read_state
        #  7   Sequential write mode (new CI) - uses write_state
        #  8   Software End-of-File CI active
        #  9   New CI needs closing
        #  10  Existing CI needs closing
        #  11  Closed CI
        self.ci_state=0     # The CI state

        # Sequential read FSM state
        self.read_state=0   # The read() method state

        # Sequential write FSM state
        self.write_state=0  # The write() method state

        if not seof:
            # Recognize slot value if seof is False
            self.slot=slot

        # Determine type of processing
        if isinstace(ci,(bytes,bytearray)):
            # Existing control interval
            self.ci_state=2
            self._init_existing(ci)

        elif isinstance(ci,int):
            assert isinstance(ci,int),"%s 'ci' argument must be an integer" \
                % (eloc(self,"__init__"),ci)

            # Initialize a new control interval
            self.ci_state=1
            self._init_new(ci,seof)

        else:
            # Unrecognized ci argument
            raise ValueError(\
                "%s 'ci' argument must be either an integer or byte/bytearray: %s" \
                    % (eloc(self,"__init__"),ci))

    # Calculate the slot offset
    # Returns:
    #   the slot's offset as an integer
    # Exceptions
    #   CIError if slot data extends into free space
    def _calc_slot_offset(self,slot):
        offset = self.slot_len * (slot-1)
        eof_slot=offset+self.slot_len
        if eof_slot > self.free_off:
            raise CIError(\
                msg="%s data for slot %s at %s extends into free space (offset %s): %s" \
                    % (eloc(self,"_calc_slot_offset"),slot,offset,self.free_off,\
                        eof_slot))
        return offset

    # Calculates the offset of the slot RDF
    # Returns:
    #   the RDF's offset as an integer
    # Exceptions:
    #   CIEnd if RDF for the requested slot does not exist
    def _calc_slot_RDF_offset(self,slot):
        rdf_off = self.cidf_off - (slot * 3)
        if rdf_off < self.rdf_end:
            raise CIEnd(slot=slot)
        return rdr_off

    # Return a state error message
    def _ci_state_error(self,expected):
        return "expected ci_state %s='%s' found: %s='%s'" \
            % (expected,CI.ci_states[expected],\
                self.ci_state,CI.ci_states[self.ci_state])

    # Initialize the object for an existing control interval
    # Expected CI State:
    #   2 - Initializing existing CI
    # Next CI State:
    #   4 - Existing CI initialized (ready for reads)
    #   8 - SEOF CI active
    def _init_existing(self,ci):
        if self.ci_state != 2:    # 2=Initializing existing CI
            raise CIError(msg="%s %s" \
                % (eloc(self,"_init_existing"),self._ci_state_error(0)))

        sectors,excess = divmod(len(ci),512)
        if excess != 0:
            raise CIError(msg="%s 'ci' argument length must be a multiple of 512, "\
                "%s * 512 + %s: %s" \
                   % (eloc(self,"_init_existing"),sectors,excess,len(ci)))

        self.ci=ci           # Initialize the active control interval
        self.ci_state=4      # Existing CI initialized

    # Initialize the object for a new control interval
    # Method Arguments:
    #   ci    The length of the control interal in bytes
    #   seof  Whether the new control interval is a software end-of-file CI
    # Exceptions:
    #   CIError if length is not a multiple of 512.
    # Expected CI State:
    #   1 - Initializing new CI
    # Next CI State:
    #   3 - New CI initialized (empty ready for writes)
    #   9 - New CI needs closing (because it is a SEOF CI)
    def _init_new(self,ci,seof):
        assert ci>0,"%s 'ci' argument must be greater than 0: %s" \
            % (eloc(self,"_init_new"),ci)
        assert slot>0,"%s 'slot' argument must be greater than 0: %s" \
            % (eloc(self,"_init_new"),ci)

        if self.ci_state != 1:   # 1=Initializing new CI
            raise CIError(msg="%s %s" \
                % (eloc(self,"_init_new"),self._ci_state_error(1)))

        # Create the new control interval's content (all binary zeros)
        sectors,excess = divmod(ci,512)
        if excess != 0:
            raise CIError(msg="%s 'ci' argument must be a multiple of 512, "\
                "%s * 512 + %s: %s" % (eloc(self,"_init_new"),sectors,excess,ci))
        self.ci_len = ci      # Establish the control interval length
        self.ci = bytearray(self.ci_len)  # Create the empty control interval
        
        # Set up CIDF and RDF controls
        self.free_off=0                  # Establish the free space offset
        if seof:
            self.free_len=0              # Establish the free space length
            self.ci_state=9              # This new SEOF CI needs closing
        else:
            # Establish the free space length, and offset of the CIDF
            self.cidf_off = self.free_len = self.ci_len-4
            self.rdf_num=0               # Number of RDF so far.
            # RDF Offset and end of RDF's point to CIDF at the beginning
            self.rdf_off =self.rdf_end=self.free_len
            self._seof=False             # This is not a software EOF CI
            self.ci_state=3              # New CI initialized

    # Read the RDF associated with a specific slot
    # Method Argument:
    #   slot   The slot number being read
    # Returns:
    #   the slot's RDF object
    # Exception:
    #   CIEnd if requested slot does not exist (raised by _calc_slot_RDF_offset)
    #   CIError if slot RDF is paired (slot RDF's are never paired)
    def _read_slot_RDF(self,slot):
        # Locate the slot's RDF offset
        self.rdf_off = rdr_off = self._calc_slot_RDF_offset(slot)
        # Read the RDF from the control interval and make it the active RDF
        rdf=RDF(self.ci[rdf_off:rdf_off+3],offset=rdf_off)
        if rdf.isPAIRED():
            raise CIError(msg="%s slot %s RDF is paired" \
                % (eloc(self,"_read_slot_RDF"),slot))
        return rdf

    # Completes the control interval construction if needed and inhibits any further
    # actions.  If sanity=True and the control interval has been updated, sanity 
    # checks are performed.
    # Returns:
    #   a bytes sequence of the control interval.
    # Method Argument:
    #   eof   Specify True to set the RDF flag in the last RDF as indicating an
    #         end-of-file condition before returning the completed new control
    #         interval.
    # Expected CI States:
    #   9  - New CI needs closing
    #   10 - Existing CI needs closing
    # Next CI State:
    #   11 - Closed CI
    def close(self,eof=False):
        if self.ci_state == 9:
            pass
            # Close new CI
        elif self.ci_state == 10:
            # Close existing CI
            if eof:
                raise CIError(msg="%s 'eof' argument invalid for existing CI" \
                    % eloc(self,"close"))

        s=CI.ci_states
        raise CIError(msg="%s expected ci_states 9='%s' or 10='%s', found: %s='%s'" \
            % (eloc(self,"close"),s[9],s[10],self.ci_state,s[self.ci_state]))

    # Use the logical data records of an existing CI as slots.
    # Expected CI State:
    #   4 - Existing CI initialized
    # Next CI State:
    #   5 - Slot mode
    def enable_slots(self):
        if self.ci_state != 4:  # 4=Existing CI initialized
            raise CIError(msg="%s %s" \
                % (eloc(self,"enable_slots"),self._ci_state_error(4)))
        # TBD
        
        self.ci_state=5

    # Make a slot available
    # Method Argument:
    #   slot   the number of the slot being freed between 1 and the number of slots
    # Exception:
    #   CISlot if the slot number is invalid
    # Expected CI State:
    #   5 - Slot mode
    # Next CI State:
    #   5 - Slot mode
    def free(self,slot):
        assert isinstance(slot,int),\
            "%s 'slot' argument must be an integer: %s" \
                % (eloc(self,"free"),slot)
        if slot>self.slot_num or slot<1:
            raise CISlot(slot)

        if self.ci_state != 5:   # 5=Slot mode
            raise CIError(msg="%s %s" \
                % ((eloc(self),"in_use"),self._ci_state_error(5)))

    # Make a slot unavailable (meaning it is in-use)
    # Method Argument:
    #   slot   the number of the slot now in use between 1 and the number of slots
    # Exception:
    #   CISlot if the slot number is invalid
    # Expected CI State:
    #   5 - Slot mode
    # Next CI State:
    #   5 - Slot mode
    def in_use(self,slot):
        assert isinstance(slot,int),\
            "%s 'slot' argument must be an integer: %s" \
                % (eloc(self,"in_use"),slot)
        if slot>self.slot_num or slot<1:
            raise CISlot(slot)

        if self.ci_state != 5:   # 5=Slot mode
            raise CIError(msg="%s %s" \
                % ((eloc(self),"in_use"),self._ci_state_error(5)))

    # Sequentially read the next logical data record.
    # Returns:
    #   a bytearray of the accessed logical data record
    # Exceptions:
    #   CIEnd    raised when no more logical data records are present but not EOF.
    #   CIEof    raised when attempting to read beyond the last RDF that is marked
    #            as being an end-of-file condition.
    # Expected CI States:
    #   4 - Existing CI initialized
    #   8 - Software End-of-File CI active
    # Next CI States:
    #   6  - Sequential read mode
    #   10 - Existing CI needs closing (after SEOF or all records read)
    def read(self):
        if self.ci_state == 4:   # 4=Existing CI initialized
            self.ci_state = 6    # 6=Sequential read mode
        elif self.ci_state == 8: # 8=Software End-of-File CI active
            self.ci_state = 10   # 10=CI Needs closing
            raise CIEof()
        if self.ci_state != 6:
            raise CIError(msg="%s %s" \
                % (eloc(self,"read"),self._ci_state_error(6)))

        if self.rdf_off == self.rdf_end:
            self.ci_state = 10   # 10=Existing CI needs closing
            if self.rdf and self.rdf.isEOF():
                # Signal EOF because last RDF has the EOF flag set
                raise CIEof()
            # Signal this CI has no more records
            raise CIEnd()

    # Read the contents of an existing slot
    # Method Argument:
    #   slot   The slot number being read
    # Returns:
    #   the slot's content as a bytearray
    # Exception:
    #   CIUnused if the slot is available (it's content is meaningless)
    # Expected CI State:
    #   5 - Slot mode
    # Next CI State:
    #   5 - Slot mode
    def read_slot(self,slot):
        if self.ci_state != 5:  # 5=Slot mode
            raise CIError(msg="%s %s" \
                % (eloc(self,"read_slot"),self._ci_state_error(5)))

        # Read the RDF from the control interval and make it the active RDF
        self.rdf=self._read_slot_RDF(slot)
        if self.rdf.isAVAIL():
            raise CIUnused(slot)

        # Read and return the slots content
        offset = (ndx - 1) * self.slot_sz
        return self.ci[offset:offset+self.slot_sz]  

    # Detects whether the exisitng control interval is a software end-of-file
    # condition.
    # Returns:
    #   None if the control interval is _not_ a software end-of-file
    # Excpetions:
    #   CIEof raised when the control interval _is_ a sofware end-of-file condiion.
    def seof(self):
        if self.ci_state == 8:
            raise CIEof()

    # Initialize slot mode.  The number and length must fit within the control
    # interval.   For a new CI, the slots are created and slot mode is entered
    # For an existing CI, slot mode is entered and the length is validated and
    # the number of actual slots is returned.
    # Method Arguments:
    #   length  The length of each slot.  Required
    #   number  The number of slots to be created (new CI) or expected (existing CI).
    # Returns:
    #   the number of slots created or found
    # Excpetions:
    #   CIFull if the control interval can not contain the requested slots
    def slots(self,length,number):
        assert isinstance(length,int) and length>9,\
            "%s 'length' argument must be an integer greater than 0: %s" \
                % (eloc(self,"slots"),length)
        assert isinstance(number,int) and number>0,\
            "%s 'number' argument must be an integer greater than 0: %s" \
                % (eloc(self,"slots"),number)

        if self.ci_state!=3:     # 3=New CI initialized
           raise CIError(msg="%s %s" % (eloc(self,"slots"),self._ci_state_error(3)))

        # Check the CI's status:
        #if self.free_off != 0:
        #    if self.slot_num == 0:
        #        msg="%s method invalid for new CI with records" % eloc(self,"slots")
        #    else:
        #        msg="%s method invalid for new CI with allocated slots" \
        #            % eloc(self,"slots")
        #    raise CIError(msg=msg)

        # Calculate bytes for the slots (slot length + RDF length)
        slots_len = number * length         # Free space consumed by slots
        rdfs_len  = number * 3              # Free space consumed by RDFs
        consumed= slots_len + rdfs_len      # Total free space conusmed
        # Determine if they fit in free space
        if consumed>self.free_len:
            raise CIFull(consumed,self.free_len)

        self.slot_sz=length            # Establish slot length
        self.slot_num=number           # Establish number of slots built
        # TBD - create slots

        self.updated=True


    # Sequentially write to a new logical data record or if the slot is provided,
    # update the requested slot.  The slot agument controls which is the case.  The
    # default is sequential access.
    # Method Arguments:
    #   data   a byte or bytearray sequence to be written.
    #   slot   the number of the slot being updated, or if None, the write adds
    #          the data to the control interval.  The instance argument slots is
    #          required for use of this argument.  Specifying None causes sequential
    #          addition of the log
    # Excpetions:
    #   CIFull raised when the data can not be contained in the control interval
    def write(self,data):
        assert isinstance(data,(bytes,bytearray)),\
            "%s 'data' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"write"),data)
                
        if self.ci_state == 3:  # 3=New CI initialized
            self.ci_state = 7   # 7=Sequential write mode
        if self.ci_state != 7:
            raise CIError(msg="%s %s" \
                % (eloc(self,"write"),self._ci_state_error(7)))

    # Write data to a slot
    # Method Arguments:
    #   data   a bytes/bytearray sequence of data to be written
    #   slot   slot number to which data is being written
    # Exceptions:
    #   CIError if written data would extend into free space.
    def write_slot(self,data,slot):
        assert isinstance(data,(bytes,bytearray)),\
            "%s 'data' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"write_slot"),data)
        assert isinstance(slot,int),"%s 'slot' argument must be an integer: %s" \
                % (eloc(self,"write_slot"),slot)
        
        if self.ci_state != 5:  # 5=Slot mode
            raise CIError(msg="%s %s" \
                % (eloc(self,"write_slot"),self._ci_state_error(5)))

        # Validate data destined for slot
        if len(data) != self.slot_len:
            raise CIError(msg="%s 'data' argument len must equal slot (%s): %s" \
                % (eloc(self,"write_slot"),self.slot_len,len(data)))

        # Read the RDF from the control interval and make it the active RDF
        self.rdf=self._read_slot_RDF(slot)
        self.rdf.slot(False)    # Because we are writing data the slot is in use.
        offset=self._calc_slot_offset(slot)
        self.ci[offset:offset+self.slot_len]=data
        self.updated=True


if __name__ == "__main__":
    #raise NotImplementedError("%s - intended for import use only" % this_module)
    # Comment out the preceding statement to execute the tests.

    ci=seof(512,debug=True)
    ci=open(ci)
    ci.display()
    print()

    print()
    ci=new(512,debug=True)
    ci.display()
    print()
    
    ci=new(512,size=80,debug=True)
    print()
    ci.display()
    print()

