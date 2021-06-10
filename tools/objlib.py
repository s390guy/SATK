#!/usr/bin/python3
# Copyright (C) 2015, 2018 Harold Grovesteen
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

# This module provides a set of classes for the manipulation of a mainframe
# object deck containing one or more object modules.  The library is intended
# to be used by a language translator that creates an object module
# or by a linkage editor processing object modules in an object deck file.
# Depending on the language translator, multiple modules may be placed in a
# single object deck file.
#
# The stand-alone environment extends the traditional records with information
# specific to creating stand-alone loadable content.  These records would appear
# to legacy linkage editors as comments, but are recognized by the library when
# found.
#
# An object deck file or one or more modules resides on the host as a binary
# file containing EBCDIC data records of 80 bytes without intervening line
# terminating characters between each record.
#
# This module exposes two module functions and one class to the user of this
# module.  The three module functions are:
#
#   objlib.read()      - reads a file as a binary byte sequence returning each
#                        record as either a RAWREC or OBJREC object without
#                        separation of records into individual modules
#   objlib.read_deck() - reads a file returning a DECK object containing one
#                        or more MODULE objects
#   objlib.write()     - writes a byte sequence to a host file from a list
#                        of OBJREC objects, a MODULE object or a DECK
#                        object containing multiple modules.
#
# Language translators or linkage editor processes are expected to use
# objlib.read_deck() and objlib.write().  The objutil.py module uses all
# of these module functions.
#
# These two functions may raise OBJFileError or OBJRecordError exceptions.
#
# The library is intended to be used by a language translator that creates
# an object module or by a linkage editor process that manipulates object
# modules.


this_module="objlib.py"

# Python EBCDIC code page used for conversion to/from ASCII
# Change this value to use a different Python codepage.
EBCDIC="cp037"

#
#  +-----------------------------+
#  |                             |
#  |   Public Module Functions   |
#  |                             |
#  +-----------------------------+
#

# Return an ASCII printable string from a binary EBCDIC byte sequence
# Method Argument:
#   byts  a bytes or bytearray object containing arbitrary binary content.
# Returns:
#   an ASCII printable string of each EBCDIC code point converted to ASCII or
#   where the code point is not EBCDIC, is replaced by a period '.'
def print_ebcdic(byts):
    assert isinstance(byts,(bytes,bytearray)),\
        "'byts' argument must be a byte sequence: %s" % byts

    cp=EBCDIC    # Python EBCDIC encoding name
    chars=[]     # list of ASCII single character strings
    for n in range(len(byts)):
        # Extract each byte as a sequence of one byte.
        byt=byts[n:n+1]
        # Convert the single byte from EBCDIC to ASCII
        ch=byt.decode(cp)
        # The decode method returns an ASCII character that is the
        # equivalent of the source binary EBCDIC code point when one exists.
        # If the source byte is not recognized the character is returned
        # unchanged.

        # In some cases the returned single character string is not a printable
        # ASCII character.  When the print built-in function is called, such
        # unprintable characters are removed from the printed result. In these
        # cases the unprintable ASCII character is also replaced by a printable
        # period, '.'
        if not ch.isprintable():
            ch="."
        chars.append(ch)

    # Convert the list of characters into a string of characters and
    # return the result
    return "".join(chars)

# Read a single object module host file
# Function Arguments:
#   filepath   A string of the path to the object module file being read.
#   raw        Whether the raw byte seq records are returned as a list or
#              a list of OBJREC object are returned.  Specify False for a
#              list of OBJREC objects.  Specify True for a list of byte
#              sequences.  Defaults to False
#   items      Specify True to decode record items into Python objects.
#              Specify False to inhibit record item decodes leaving items as
#              a byte sequence within the OBJREC object. Default is True.
#              Ignored when raw=True.
#
# Note: objutil uses the 'raw' or 'items' arguments to control what objlib.py
# does when reading an object deck file:
#
#     objutil.py -a raw     uses read(filepath,raw=True)
#     objutil.py -a format  uses read(filepath,items=False)
#     ojbutil.py -a decode  uses read(filepath,items=True)
#
# Returns:
#   a list of RAWREC objects (raw=True),
#   a list of OBJREC objects without item decodes, or
#   a list of OBJREC objects with item decodes
# Exceptions:
#   OBJFileError   if I/O errors occur, a truncated record is encountered, or
#                  errors occur during OBJREC object creation.
#   OBJRecordError if an error is encountered while decoding an individual
#                  object deck file record.
def read(filepath,raw=False,items=True):
    assert isinstance(filepath,str),\
        "'filepath' argument must be a string: %s" % filepath

    fo=None     # The file object created when the file is opened
    recs=[]     # Accumulates each 80-byte EBCDIC object record as byte seq.
    recnum=0    # Record number
    errors=0    # Number of errors during decode

    # Open and read the object module file
    try:
        fo=open(filepath,"rb")
    except IOError as ie:
        raise OBJFileError(\
            msg="object module file %s could not be opened for reading: %s"\
                % (filepath,ie)) from None

    # Read the object module file's records.
    while True:
        recnum+=1
        try:
            byts=fo.read(80)
        except IOError as ie:
            raise OBJFileError(\
                msg="object module file %s could not be read record %s: %s" \
                % (filepath,recnum,ie)) from None
        if len(byts)==0:
            break

        if len(byts)!=80:
            raise OBJFileError(\
                msg="object module file %s last record %s truncated: %s" \
                    % (filepath,recnum,len(byts)))

        # Accumulate output records
        if raw:
            # Return the raw bytes from the file as a RAWREC object
            recs.append(RAWREC(byts,recnum=recnum))
        else:
            # Return a list of OBJREC objects
            try:
                recs.append(OBJREC.decode(byts,recnum=recnum,items=items))
            except OBJRecordError as oe:
                print("OBJ error [%s] %s" % (recnum,oe.msg))
                errors+=1
                continue

    # Close the object module file
    try:
        fo.close()
    except IOError as ie:
        raise OBJFileError(msg="object module file %s could not be closed: %s"\
            % (filepath,ie)) from None

    if errors:
        raise OBJFileError(\
            msg="object module file %s contains record errors: %s" \
                % (filepath,errors))

    # Return the object module file as a list
    return recs


# Read an object deck file
# Function Argument:
#   filepath    The path to the object deck file being accessed
# Returns:
#   a DECK object
# Exceptions:
#   OBJFileError   if I/O errors occur, a truncated record is encountered, or
#                  errors occur during OBJREC object creation.
#   OBJRecordError if an error is encountered while decoding an individual
#                  object deck file record.
def read_deck(filepath):
    # Read the object deck file in its entirety
    return DECK(recs=read(filepath),filepath=filepath)


# Write a singe object module host file. If the file already exists it will
# be truncated to an empty file before writing begins.
# Function arguments:
#   filepath   The path of the file being written
#   lst        a list of either OBJREC objects or 80 byte sequences
#   raw        Whether the list contains OBJREC objects or byte sequences.
#              Specify False if 'lst' contains OBJREC objects.  Specify True
#              if 'lst' contains byte sequences of length 80.  Defaults to
#              False.
# Returns: None
# Exceptions:
#   OBJFileError if I/O errors occur while writing the file

def write(filepath,lst,raw=False):
    assert isinstance(filepath,str),\
        "'filepath' argument must be a string: %s" % filepath
    assert isinstance(lst,list),"'lst' argument must be a list: %s" % lst

    bytes=None   # A binary object file record being written

    try:
        fo=open(filepath,"wb")
    except IOError as ie:
        raise OBJFileError(\
            msg="object module file %s could not be opened for writing: %s"\
                % (filepath,ie)) from None

    for n,entry in enumerate(lst):
        if raw:
            assert isinstance(entry,bytes),\
                "'lst' entry %s must be a byte sequence: %s" \
                    % (n,entry)
            bytes=entry
        else:
            assert isinstance(entry,OBJREC),\
                "'lst' entry %s must be an OBJREC object: %s" \
                    % (n,entry)
            try:
                bytes=entry.encode()
            except OBJRecordError as oe:
                raise OBJRecordError(\
                    msg="record %s could not be encoded: %s: %s"\
                        % (n+1,oe.msg,entry))

        if len(bytes)!=80:
            raise OBJRecordError(msg="record %s not 80 bytes in length: %s" \
                % (n+1,len(bytes)))

        try:
            fo.write(bytes)
        except IOError as ie:
            raise OBJFileError(\
                msg="object module file %s record %s could be written: %s" \
                    % (filepath,n+1,ie))

    try:
        fo.close()
    except IOError as ie:
        raise OBJFileError(\
            msg="object module file %s could not be closed: %s"\
                % (filepath,ie))


#
#  +-----------------------+
#  |                       |
#  |   Utility Functions   |
#  |                       |
#  +-----------------------+
#

# Converts a list of three bytes into an unsigned integer
def addr(binary):
    assert isinstance(binary,bytes) and len(binary)==3,\
        "'binary' argument must be a bytes object of length two: %s" % binary
    return int.from_bytes(binary,byteorder="big")

# Convert an
def addr2bin(addr):
    assert isinstance(addr,int) and addr>=0,\
        "'addr' argument must be a non-negative integer: %s" % addr
    return addr.to_bytes(3,byteorder="big")

# Convert an ascii string into EBCDIC
# Return:
#   a byte sequence of EBCDIC characters
def a2e(string):
    assert isinstance(string,str),\
        "'string' argument must be a string: %s" % string
    return string.encode(EBCDIC)

def e2a(byt):
    assert isinstance(byt,(bytes,bytearray)),\
        "'byt' argument must be a byte sequence: %s" % byt
    return byt.decode(EBCDIC)

# Converts a lit of two bytes into an signed or unsigned integer
def hword(binary,signed=False):
    assert isinstance(binary,bytes) and len(binary)==2,\
        "'binary' argument must be a bytes object of length two: %s" % binary
    return int.from_bytes(binary,byteorder="big",signed=signed)

# Converts an integer into a two byte signed or unsigned integer
def hword2bin(value,signed=False):
    assert isinstance(value,int),\
        "'value' argument must be an integer: %s" % value
    return value.to_bytes(2,byteorder="big",signed=signed)


#
#  +---------------------------+
#  |                           |
#  |   Object File Exception   |
#  |                           |
#  +---------------------------+
#

# Reports issues related to an object deck file.
class OBJFileError(Exception):
    def __init__(self,msg=""):
        self.msg=msg          # Text associated with the error
        super().__init__(msg)

#
#  +-----------------------------+
#  |                             |
#  |   Object Record Exception   |
#  |                             |
#  +-----------------------------+
#

# Reports issues related to object module records
class OBJRecordError(Exception):
    def __init__(self,msg=""):
        self.msg=msg          # Text associated with the error
        super().__init__(msg)


#
#  +----------------------+
#  |                      |
#  |   Object Exception   |
#  |                      |
#  +----------------------+
#

# Reports issues related to language translator related errors
class OBJError(Exception):
    def __init__(self,msg=""):
        self.msg=msg          # Text associated with the error
        super().__init__(msg)


#
#  +---------------------------+
#  |                           |
#  |   Object Module Classes   |
#  |                           |
#  +---------------------------+
#

# One class is used to represent the contents of an object module file:
#
#   - DECK manages the physical object file's content of one or more modules
#
# Two classes are used for object module representations:
#
#   - PMOD which manages physical object records and
#   - MODULE which manages object module information content.
#
# The object records and object module information are closely related.
# For that reason MODULE is a subclass of PMOD.  By using two classes it makes
# it easy to separate the different though related processing.


# This object encapsulates the contents of single object deck file composed
# of one or more object modules.  Each module is represented as a MODULE object.
# The function read_deck() returns a DECK object.  If a new object deck is
# being created, a DECK object may be instantiated without any arguments.
#
# An object deck file containing multiple object modules is created by an
# assembler that supports the assembly of more than one assembler input deck,
# also known as batch assembly.  While ASMA is designed to perform assembly
# of a single source input file and one object module in an output file, other
# assemblers may produce multiple modules in one file.  This library handles
# both scenarios.

class DECK(object):

    def __init__(self,recs=[],filepath=None):
        assert isinstance(recs,list),\
            "%s.%s.__init__() - 'recs' argument must be a list: %s" \
                % (this_module,self.__class__.__name__,recs)

        # The file read to create this DECK object.  None if a file is not the
        # source of the object (meaning it is being built by an external
        # process).
        self.filepath=filepath
        self.recs=recs

        self.modules=[]     # A list of MODULE objects created from the records

        # Construct modules from the object deck
        module=[]
        for rec in self.recs:
            if isinstance(rec,END):
                module.append(rec)
                mod=MODULE(recs=module)
                mod.number(len(self.modules)+1)
                mod.fpath=self.filepath
                self.modules.append(mod)
                module=[]
            else:
                module.append(rec)

        if len(module):
            first=module[0]
            if len(self.modules) == 0:
                raise OBJRecordError(\
                    "first or only module missing END record: %s" \
                       % self.filepath)
            else:
                recnum=module[0].recnum
                modnum=len(self.modules)+1
                raise OBJRecordError(\
                    "module %s starting at record %s missing END record: %s" \
                         % (modnum,recnum,self.filepath))

    def __str__(self):
        if self.filepath:
            return "DECK: file %s - Modules: %s" \
                % (self.filepath,len(self.modules))
        return "DECK - Modules %s" % len(self.modules)


# This class accepts module records as OBJREC objects or creates an
# object module as a list OBJREC objects.  It is oriented towards the physical
# structure of an object module's records as opposed to the logical
# relationships that must be maintained for correct generation of the module.
#
# Instance argument:
#   recs     A list of OBJREC objects defining the object file.  Defaults to
#            an empty list.  When empty, the MODULE instance is used to build
#            a new object module by calling various methods.
class PMOD(object):

    def __init__(self,recs=[]):
        self.recs=recs           # List of OBJREC objects of the module
        self.modnum=None         # Module number. See number() method
        self.fpath=None          # Object file path. See filepath() method

        self.esds=[]             # ESD records in the order encountered
        self.esditems=[]         # ESD items from ESD records
        self.zero_length=None    # SD or PC item with zero length

        self.txts=[]             # TXT records in the order encountered

        self.rlds=[]             # RLD records in the other encountered
        self.rlditems=[]         # RLD items from RLD records

        self.end=[]              # END record
        self.enditems=[]         # List if END IDR data objects

        if not self.recs:
            # This module is being constructed, nothing to do here.
            return

        # Process provided object module records
        end_found=False
        for rec in self.recs:
            if end_found:
                raise OBJRecordError(\
                        "Module %s records encountered following END "\
                            "record: %s" % (self.modnum,\
                                rec.__class__.__name__,rec.recnum))
            if isinstance(rec,ESD):
                self._process_ESD_rec(rec)
            elif isinstance(rec,TXT):
                self.txts.append(rec)
            elif isinstance(rec,RLD):
                self._process_RLD_rec(rec)
            elif isinstance(rec,END):
                self._process_END_rec(rec)
                end_found=True

        if not end_found:
            raise OBJRecordError("Module %s missing END record" % self.modnum)

    def __str__(self):
        if self.fpath:
            return "MODULE:%s from file %s - %s records: "\
                "ESD-%s ESDITEMS-%s TXT-%s RLD-%s RLDITEMS-%s END-%s IDR-%s" \
                    % (self.modnum,self.fpath,len(self.recs),\
                        len(self.esds),len(self.esditems),\
                        len(self.txts),len(self.rlds),len(self.rlditems),\
                        len(self.end),len(self.enditems))

        return "MODULE - %s records" % len(self.recs)

    # Adds an ESD record to the list of ESD records and its ESD items to a list
    def _process_ESD_rec(self,esdrec):
        self.esds.append(esdrec)
        for item in esdrec.items:
            # Handle zero length SD or PC case.
            if isinstance(item,(SD,PC)) and item.length == 0:
                if self.zero_length is None:
                    # Remember the item so it can be updated by END record
                    self.zero_length=item
                else:
                    raise ObjectRecord(msg="%s.%s._process_ESD_rec() - "\
                        "More than one zero length section, already found "
                            "'%s': '%s'" \
                                % (this_module,self.__class__.__name__,\
                                    self.zero_length.symbol,item.symbol))
            self.esditems.append(item)

    # Adds an RLD record to the list of RLD records and its RLD items to a list
    def _process_RLD_rec(self,rldrec):
        self.rlds.append(rldrec)
        self.rlditems.extend(rldrec.items)

    # Adds an END record to the list of END records and its IDR items to a list
    # Updates a zero length SD or PC item with the length from the END
    def _process_END_rec(self,endrec):
        if endrec.sdlen is not None:
            if self.zero_length is not None:
                self.zero_length.length=endrec.sdlen
            else:
                raise ObjectRecordError(msg="%s.%s._process_END_rec() - "\
                    "No zero length section, but END record contains length"\
                        % (this_module,self.__class__.__name__))

        self.end.append(endrec)
        self.enditems.append(endrec.items)

    # Set the physical modules file path.
    def filepath(self,fpath):
        assert isinstance(fpath,str) and len(fpath)>0,\
           "%s.%s.filepath() - 'fpath' argument must be a non-empty string: %s"\
                % (this_module,self.__class__.__name__,fpath)

        self.fpath=fpath

    # This method tests whether the PMOD is empty.
    def isempty(self):
        return len(self.recs) == 0

    # This method sets a module's number within a physical file.
    def number(self,n):
        assert isinstance(n,int) and n>0,\
            "%s.%s.number() - 'n' argument must be a positive integer: %s" \
                % (this_module,self.__class__.__name__,n)

        self.modnum=n


#
#  +-----------------------------------+
#  |                                   |
#  |   Logical Object Module Classes   |
#  |                                   |
#  +-----------------------------------+
#

# This class is used by a language translator creating an object module.  It
# maintains the information centered around SD and PC items, keeping related
# information togehter that ultimately result in object module records.
#
# The other purpose of this class is to collect out of the MODULE class all
# of the information related to each SD and PC item in the same way as is done
# for a language translator.
#
# This class is the vehicle by which a linkage editing process can link
# object modules together or a translator creates an object module.  It should
# be viewed as the representation of an object module external to this library
# module.
#
# While the superclass PMOD is focused on interpreting and creating physical
# object modules, this subclass is focused on managing the information content
# of an object module.  This information is the precursor for object module
# creation or the result of interpreting a previously created module.  The
# records and content are tightly coupled.  For this reason the MODULE
# object is subclassed.

class MODULE(PMOD):
    alignment_values=[8,16]
    amode_values={None:None,24:24,31:31,64:64,"ANY":True}
    rmode_values=[None,24,31,64]
    rsect_values={True:1,False:0}

    def __init__(self,recs=[]):
        super().__init__(recs=recs)
        self.esdict=ExternalSymbolDict()   # Create the External Symbol Dict.

        # These two attributes are set when items are added to an Area (PC/SD)
        # See self._current_area() method
        self.curarea=None                  # Current area's Area instance

        self.txtitems=[]                   # TXTITEMS in the order presented

    # Add items to External Symbol Dictionary
    # This internal method is used when the MODULE object is being populated
    # from a series of OBJREC objects supplied to the instantiated PMOD
    # superclass as well as when a language translator adds individual items
    # via the MODULE.ESD_xx() methods.
    def _add_item(self,item):
        self.esdict.add_ESD(item)

    # Adds text from a TXT record to the area as a TXTITEM object.
    # This internal method is used when the MODULE object is being populated
    # from a series of OBJREC objects supplied to the instantiated PMOD
    # superclass.  The TXT() method used by a language translator also uses
    # this method for addition of TXTITEM objects.
    # Exception:
    #   OBJError if section is not defined
    def _add_text(self,txt):
        assert isinstance(txt,TXT),\
            "%s.%s._add_text() - 'txt' argument must be a TXT record: %s" \
                % (this_module,self.__class__.__name__,txt)

        try:
            area=self._current_area(txt.esdid)
        except KeyError:
            raise OBJError(msg="Record %s - "\
                "ESDID to which text is being added does not exist: %s"\
                    % (txt.recnum,txt.esdid)) from None

        txt=TXTITEM(txt.esdid,txt.address,txt.text)
        area.TXT(txt)
        self.txtitems.append(txt)
        
    def _add_rld(self,rld):
        assert isinstance(rld,RLDITEM),\
            "%s.%s._add_rld() - 'rld' argument must be a RLDITEM object: %s" \
                % (this_module,self.__class__.__name__,rld)
        
        try:
            area=self._current_area(rld.pptr)
        except KeyError:
            raise OBJError(msg=\
                "ESDID to which RLD item is being added does not exist: %s"\
                    % (txt.recnum,rld.pptr)) from None
            
        area.RLD(rld)

    # Checks the validity of an amode value.  Valid values are: None, the
    # integers 24, 31, or 64, and the string "ANY".
    # Returns:
    #   The internal representation of the AMODE used by the library when valid
    #   False if not valid.  Caller must
    # Note: the caller must explicitly test for False.  Using an if will cause
    # incorrect results when None is returned.
    def _check_amode(self,amode):
        try:
            return MODULE.amode_values[amode]
        except KeyError:
            return False

    # Checks the validity of an address.  An address is valid if it is an
    # integer and is between X'000000'-X'FFFFFF', inclusive
    # Returns:
    #   True if the addess is valid
    #   False if the address is invalid
    def _check_address(self,address):
        return isinstance(address,int) and address >=0 and address <= 0xFFFFFF

    # Checks the validity of an area's alignment.  Valid values are an integer
    # of 8 or 16.
    # Returns:
    #   True if the alignment is valid
    #   False if the address is invalid
    def _check_align(self,align):
        return align in [8, 16]

    # Checks the common language translator arguments supplied for ESD areas.
    # Method Arguments:
    #   symbol   the name of the symbol being defined as a string.  None is
    #            ignored, allowing case where symbol is not provided.
    #            None is used by PC items that do not have a name.
    #   address  address of the start of the area
    #   amode    amode argument: None, "24", "31", "64", "ANY"
    #   rmode    residency mode: None, "24", "31", "64"
    #   length   area length in bytes
    #   align    area alignment requirement: 8, 16
    #   minimum  minimim length of a valid symbol. Defaults to 1. 0 allows
    #            an empty string to be valid (used by CM items)
    # Returns:
    #   Python amode numeric value:
    #      None for None
    #       24  for "24"
    #       31  for "31"
    #       64  for "64"
    #      True for "ANY"
    # Exceptions:
    #   AssertionError if invalid argument encountered
    def _check_area(self,symbol,address,amode,rmode,length,align,minimum=1):
        assert symbol is not None or self._check_symbol(\
            symbol,minimum=minimum),"%s.%s.check_area() - "\
                "'symbol' argument not a valid symbol: %s" \
                    % (this_module,self.__class__.__name__,symbol)
        assert self._check_address(address),\
            "%s.%s.check_area() - 'address' argument not a valid address: %s" \
                % (this_module,self.__class__.__name__,address)
        assert self._check_rmode(rmode),\
            "%s.%s.check_area() - 'rmode' argument not a valid mode: %s" \
                % (this_module,self.__class__.__name__,rmode)
        assert self._check_length(length),\
            "%s.%s.ESD_CM() - 'length' argument not a valid length: %s" \
                % (this_module,self.__class__.__name__,length)
        assert self._check_align(align),\
            "%s.%s.ESD_CM() - 'align' argument not a valid alignment: %s" \
                % (this_module,self.__class__.__name__,align)
        am=self._check_amode(amode)
        assert am != False,\
            "%s.%s.check_area() - 'amode' argument not a valid mode: %s" \
                % (this_module,self.__class__.__name__,amode)
        return am

    # Checks the validity of a byte sequence.
    # Returns:
    #   True if the binary is a bytes or bytearray object
    #   False if not a valid binary object
    def _check_binary(self,bin):
        return isinstance(bin,(bytes,bytearray))

    # Checks the validity of a length.  A length is valid if it is an
    # integer and is between X'000000'-X'FFFFFF', inclusive
    # Returns:
    #   True if the length is valid
    #   False if the length is invalid
    def _check_length(self,length):
        return isinstance(length,int) and length >= 0 and length <= 0xFFFFFF

    # Checks the validity of the length in relocation dictionary items.
    # A valid length is an integer between 1 and 8, inclusive
    # Returns:
    #   True if the length is valid
    #   False if the length is not valid
    def _check_length_rld(self,length):
        return isinstance(length,int) and length >=1 and length <=8

    def _check_rld(self,rname,pname,address,length,sign,r=True):
        if r:
            assert self._check_symbol(rname) or rname is None,\
                "%s.%s._check_rld() - 'rname' argument not a valid symbol: %s" \
                    % (this_module,self.__class__.__name__,rname)
        else:
            assert self._check_symbol(rname),\
                "%s.%s._check_rld() - 'rname' argument not a valid symbol: %s" \
                    % (this_module,self.__class__.__name__,rname)

        assert self._check_symbol(pname) or pname is None,\
            "%s.%s._check_rld() - 'pname' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,pname)
        assert self._check_address(address),\
             "%s.%s._check_rld() - 'address' argument not a valid address: %s" \
                % (this_module,self.__class__.__name__,address)
        assert self._check_length_rld(length),\
            "%s.%s._check_rld() - 'length' argument not a valid length: %s" \
                % (this_module,self.__class__.__name__,length)
        assert sign in [1, -1],\
            "%s.%s._check_rld() - 'sign' argument not 1 or -1: %s" \
                % (this_module,self.__class__.__name__,sign)

    # Checks the validity of an rmode value. Valid values are: None, 24, 31, 64.
    # Returns:
    #   True if the residency mode is valid
    #   False if the residency mode is invalid
    def _check_rmode(self,rmode):
        return rmode in MODULE.rmode_values

    # Checks the validity of an rsect value. Valid values are: True, False
    # Returns:
    #   0 if the rsect value is False
    #   1 if the rsect value if True
    #   False if the rsect value is invalid.  Caller must check for False.
    # Note: this language translator uses True and False as valid values for
    # rsect.  The ESD items that use rsect use 0 and 1.  This method converts
    # the external value for rsect into the internal value used by this module.
    def _check_rsect(self,rsect):
        try:
            return rsect in MODULE.rsect_values[rsect]
        except KeyError:
            return False

    # Checks the validity of a symbol.  A symbol is valid if it is a string
    # of length 0-8, or 1-8 inclusive.
    # Method Arguments:
    #   symbol   the symbol being validated
    #   minimim  the shortest valid symbol. Defaults to 1. May be 0.
    # Returns:
    #   True if symbol is valid
    #   False if symbol in not valid
    def _check_symbol(self,symbol,minimum=1):
        return isinstance(symbol,str) \
            and len(symbol)>=minimum and len(symbol)<=8

    # This method maintains the current area information
    # Returns the current area.
    # Method Argument:
    #   areaid   either a string of the area's symbol, or an integer of the
    #            area's ESDID, or None for the PC area.
    # Returns:
    #   the current active area as identified by the id.
    # Exception:
    #   KeyError if requested areaid does not exist.
    def _current_area(self,areaid):
        if isinstance(areaid,str):
            if self.curarea and self.curarea.symbol == section:
                # Still working with the current area
                return self.curarea
        elif areaid is None and self.pc:
            if self.curarea and self.curarea.esdid == self.pc.esdid:
               return self.curarea
        else:
            if self.curarea and self.curarea.esdid == areaid:
                return self.curarea

        # Current area being initialized or changing areas
        area=self.esdict[areaid]
        assert isinstance(area,Area),\
             "%s.%s._current_area() - symbol '%s' must be an Area instance: %s" \
                % (this_module,self.__class__.__name__,section,area)
        self.curarea=area
        return area

    # Populate this MODULE object from the superclass PMOD object records
    # Returns:
    #   Number of records populating the module
    def populate(self):
        if self.isempty():
            # No records, so no items to add to MODULE
            return 0

        # Populate the MODULE with ESD items
        for item in self.esditems:
            self._add_item(item)
        for txt in self.txts:
            self._add_text(txt)
        return len(self.recs)

  # 
  # Language Translator Interface
  #
  
    # The collection of ESD_xx, RLD_xx, and TXT methods constitute the library's
    # interface exposed to a language translator.  These methods add various
    # pieces of information to the MODULE object.

    # Adds a CM item to the External Symbol Dictionary
    # Method Arguments:
    #    symbol   The name of the CM item being added
    #    address  The starting address of the CM item
    #    amode    The CM item's amode: None, 24, 31, 64, "ANY"
    #    rmode    The CM item's rmode: None, 24, 31, 64
    #    length   The CM item's length in bytes
    #    align    The CM item's alignment: 8, 16
    # Returns:
    #   The ESDID of the item added to the dictionary for use by the language
    #   translator.
    # Exceptions:
    #   AssertionError if any argument is invalid
    def ESD_CM(self,symbol,address,amode,rmode,length,align):
        am=self._check_area(symbol,address,amode,rmode,length,align,minimum=0)
        return self.esdict.ESD_CM(symbol,address,am,rmode,length,align)

    # This method adds an ER item to the External Sybmol Dictionary.
    # Method Arguments:
    #   symbol   The name of the ER item being added.
    # Returns:
    #   the ESDID value of the added ER item
    def ESD_ER(self,symbol):
        assert self._check_symbol(symbol),\
            "%s.%s.ESD_ER() - 'symbol' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,symbol)

        return self.esdict.ESD_ER(symbol)

    # Adds a LD item to the External Symbol Dictionary
    # Method Arguments:
    #   label   the name of LD item being added
    #   section the name of the SD or PC, an empty string, with which the
    #           label is associated
    #   address the address of the LD item assigned by the language translator
    #           within the section
    # Exceptions:
    #   AssertionError if an arguments is invalid
    #   KeyError       if the section is not found or the label is a duplicate
    def ESD_LD(self,label,section,address):
        assert self._check_symbol(lable),\
            "%s.%s.ESD_LD() - 'label' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,label)
        assert self._check_symbol(section),\
            "%s.%s.ESD_LD() - 'section' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,section)
        assert self._check_address(address),\
            "%s.%s.ESD_LD() - 'address' argument not a valid address: %s" \
                % (this_module,self.__class__.__name__,address)

        self.esdict.ESD_LD(label,section,address)

    # Adds a PC item to the External Symbol Dictionary
    # Method Arguments:
    #    address  The starting address of the SD item
    #    amode    The PC item's amode: None, 24, 31, 64, "ANY"
    #    rmode    The PC item's rmode: None, 24, 31, 64
    #    rsect    The PC item's read-only value (rsect): True, False
    #    length   The PC item's length in bytes
    #    align    The PC item's alignment: 8, 16
    # Returns:
    #   The ESDID of the item added to the dictionary for use by the language
    #   translator.
    # Exceptions:
    #   AssertionError if any argument is invalid
    #   OBJError if a PC item is already defined
    def ESD_PC(self,address,amode,rmode,rsect,length,align):
        am=self._check_area(None,address,amode,rmode,length,align,minimum=0)
        rs=self._check_rsect(rsect)
        assert rs is not False,\
            "%s.%s.ESD_PC() - 'rsect' argument not a valid rsect value: %s" \
                % (this_module,self.__class__.__name__,rsect)
        return self.esdict.ESD_PC(address,am,rmode,rs,length,align)

    # Adds a SD item to the External Symbol Dictionary
    # Method Arguments:
    #    symbol   The name of the SD item being added
    #    address  The starting address of the SD item
    #    amode    The SD item's amode: None, 24, 31, 64, "ANY"
    #    rmode    The SD item's rmode: None, 24, 31, 64
    #    rsect    The SD item's read-only value (rsect): True, False
    #    length   The SD item's length in bytes
    #    align    The SD item's alignment: 8, 16
    # Returns:
    #   The ESDID of the item added to the dictionary for use by the language
    #   translator.
    # Exceptions:
    #   AssertionError if any argument is invalid
    def ESD_SD(self,symbol,address,amode,rmode,rsect,length,align):
        am=self._check_area(symbol,address,amode,rmode,length,align)
        rs=self._check_rsect(rsect)
        assert rs is not False,\
            "%s.%s.ESD_SD() - 'rsect' argument not a valid rsect value: %s" \
                % (this_module,self.__class__.__name__,rsect)
        return self.esdict.ESD_SD(symbol,address,am,rmode,rs,length,align)

    # This method adds an WX item to the External Sybmol Dictionary.
    # Method Arguments:
    #   symbol   The name of the WX item being added.
    # Returns:
    #   the ESDID value of the added WX item
    def ESD_WX(self,symbol):
        assert self._check_symbol(symbol),\
            "%s.%s.ESD_WX() - 'symbol' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,symbol)

        return self.esdict.ESD_WX(symbol)

    # This method adds a XD (aka PR) item to the External Symbol Dictionary.
    # An XD item is created by an assembler DXD (Define External Dummy)
    # directive or when a dummy section defined by a DSECT directive appears
    # in a Q-type address constant.  Access to the DXD defined dummy section
    # also requires it to appear in a Q-type address constant.  The Q-type
    # address constant generates a RLD Q item that supplies to the program the
    # address of the first byte of the external dummy section as allocated by
    # the linkage editor.
    # Method Arguments:
    #   symbol   the name of the external dummy section being defined
    #   align    the alignment required by the external dummy section:
    #            1, 2, 4, or 8.
    #   length   the length of the external dummy section.  Must be a non-
    #            negative integer.
    def ESD_XD(self,symbol,align,length):
        assert self._check_symbol(symbol),\
            "%s.%s.ESD_XD() - 'symbol' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,symbol)
        assert isinstance(align,int) and align in [1,2,4,8],\
            "%s.%s.ESD_XD() - 'align' argument must be 1, 2, 4, or 8: %s" \
                % (this_module,self.__class__.__name__,align)
        assert isinstance(length,int) and length>=0,\
            "%s.%s.ESD_XD() - 'length' argument must a non-negative integer: "\
                "%s" % (this_module,self.__class__.__name__,length)

        return self.esdict.ESD_XD(symbol,align,length)

    # This method adds a A-type address constant to the module
    # Method Arguments:
    #   rname    the name of the SD or None (PC) being referenced.
    #   pname    the name of the SD or None (PC) containing the address constant
    #   address  the address of the A-type constant within the section
    #   length   the length of the A-type address constant
    #   sign     the sign factor applied to the offset contained in the address
    #            constant text data.
    def RLD_A(self,rname,pname,address,length,sign):
        self._check_rld(rname,pname,address,length,sign)
        self.esdict.RLD_A(rname,pname,address,length,sign)

    # Add a CXD RLD item to an object deck. The CXD item is a fullword into
    # which the linkage editor stores the combined lengths of all external
    # dummy sections.
    # Method Arguments:
    #   pname    the name of the SD in which the CXD resides, or None (PC)
    #   address  the address within the SD/PC at which the CXD starts
    #   length   the length of the CXD item in the SD/PC.  Must be four.
    def RLD_CXD(self,pname,address,length):
        assert self._check_symbol(pname) or pname is None,\
            "%s.%s.RLD_CXD() - 'pname' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,pname)
        assert self._check_address(address),\
            "%s.%s.RLD_CXD() - 'address' argument not a valid address: %s" \
                % (this_module,self.__class__.__name__,address)
        assert length == 4,\
            "%s.%s.RLD_CXD() - 'length' argument muse be 4: %s" \
                % (this_module,self.__class__.__name__,length)
        
        self.esdict.RLD_CXD(pname,address,length,sign)

    # This method adds a Q-type address constant to the module
    # Method Arguments:
    #   qname  the name of the external dummy section being referenced
    #   pname  the name of the SD or None (PC) containing the address constant
    #   length the length of the Q-type address constant
    #   sign   the sign factor applied to the offset contained in the address
    #          constant text data.
    def RLD_Q(self,qname,pname,address,length,sign):
        self._check_rld(qname,pname,address,length,sign,r=False)
        self.esdict.RLD_Q(qname,pname,address,length,sign)

    # This method adds a V-type address constant to the module
    # Method Arguments:
    #   rname    the external name being referenced.
    #   pname    the name of the SD or None (PC) containing the address constant
    #   address  the address of the V-type constant within the section
    #   length   the length of the V-type address constant
    #   sign     the sign factor applied to the offset contained in the address
    #            constant text data.
    def RLD_V(self,vname,pname,address,length,sign):
        self._check_rld(vname,pname,address,length,sign,r=False)
        self.esdict.RLD_V(qname,pname,address,length,sign)

    # Adds text data to the module
    # Method Arguments:
    #   section   The name of the SD or None (PC) to which the text data belongs
    #   address   The address within the SD/PC of the first byte of text data
    #   binary    The data being added to the section as a byte sequence
    # Returns: None
    # Exceptions:
    #   AssertionError if any argument is invalid
    def TXT(self,section,address,binary):
        assert self._check_symbol(section) or section is None,\
            "%s.%s.TXT() - 'symbol' argument not a valid symbol: %s" \
                % (this_module,self.__class__.__name__,section)
        assert self._check_address(address),\
            "%s.%s.TXT() - 'address' argument not a valid address: %s" \
                % (this_module,self.__class__.__name__,address)
        assert self._check_binary(binary),\
            "%s.%s.TXT() - 'binary' argument not a valid byte seq: %s" \
                % (this_module,self.__class__.__name__,binary)

        try:
            area=self._current_area(section)
        except KeyError:
            if section is None:
                sc="PC"
            else:
                sc=section
            raise OBJError(msg=\
                "section to which text is being added is not defined: %s" \
                    % sc) from None

        txt=TXTITEM(area.esdid,address,binary)
        area.TXT(txt)
        self.txtitems.append(txt)


# This class manages the external symbol dictionary. It operates exclusively
# upon ESDITEM subclasses.
class ExternalSymbolDict(object):
    def __init__(self):
        # These three attributes manage Global symbols.
        # Access to these attributes are arbitrated through __getitem__() and
        # __setitem__() methods.  They should not be access directly
        self.dct={}             # Symbols accessed by name
        self.esdids={}          # Symbols accessed by ESDID
        # Note: LD items are not assigned an ESDID.  They will appear in
        # self.dct (accessed by name) but not in self.esdids.  LD items
        # are added to the Area in which they reside.
        # PC items have no name but do have an ESDID.  They will appear in
        # self.esdids but not in self.dct.
        # All other items will have a presence in both self.dct and self.esdids,
        # including a blank COM.  The blank COM symbol is the empty string "".

        # The PC item when defined. Only one may exist
        self.pc=None  # See __getitem__() and __setitem__() methods for access

        # Symbols in creation sequence. This is the sequence in ESD records
        self.items=[]

    # Overload:  self[symbol]
    #            self[ESDID]
    #            self[None]    - for PC item access
    # Returns:
    #   the ESDITEM object referenced by the symbol or ESDID or PC (None)
    # Exception:
    #   KeyError if the symbol or ESDID value does not exist
    def __getitem__(self,key):
        if key is None:
            if self.pc:
                return self.pc
            else:
                raise KeyError(\
                    "%s.%s.__getitem__() - PC item not defined" \
                        % (this_module,self.__class__.__name__,key))
        assert isinstance(key,(str,int)),\
            "%s.%s.__getitem__() - "\
                "'key' argument must be a string or integer: %s" \
                    % (this_module,self.__class__.__name__,key)

        if isinstance(key,str):
            # Key is a symbol name
            try:
                return self.dct[key]
            except KeyError:
                raise KeyError(\
                    "%s.%s.__getitem__() - ESD symbol not defined: %s" \
                        % (this_module,self.__class__.__name__,key)) from None

        # Assume key is for an ESDID
        try:
            return self.esdids[key]
        except KeyError:
            raise KeyError(\
                "%s.%s.__getitem__() - ESDID not defined: %s" \
                    % (this_module,self.__class__.__name__,key)) from None

    # Overload self[symbol]=ESDITEM
    #          self[ESDID]=ESDITEM
    #          self[None]=PC
    # Sets the symbol name, ESDID value or PC to the ESDITEM
    # Exception:
    #   KeyError if the symbol or ESDID value has already been associated with
    #   an ESDITEM object.
    def __setitem__(self,key,value):
        if key is None:
            if self.pc:
                raise KeyError("%s.%s.__setitem__() - "\
                    "PC item already defined, can not add" \
                        % (this_module,self.__class__.__name__))
            else:
                assert isinstance(value,PC),\
                    "%s.%s.__setitem__() - "\
                        "'value' argument must be a PC item for key None: %s" \
                            % (this_module,self.__class__.__name__,value)
                self.pc=value
        assert isinstance(key,(str,int)),\
            "%s.%s.__setitem__() - "\
                "'key' argument must be a string or integer: %s" \
                    % (this_module,self.__class__.__name__,key)
        assert isinstance(value,ESDITEM),\
            "%s.%s.__setitem__() - "\
                "'value' argument must be an ESDITEM object: %s" \
                    % (this_module,self.__class__.__name__,value)

        if isinstance(key,str):
            # Adding an item by its symbol name
            try:
                item=self.dct[key]
            except KeyError:
                self.dct[key]=value
                return
            raise KeyError("%s.%s.__setitem__() - "\
                "symbol '%s' already defined by %s item, can not add: %s" \
                    % (this_module,self.__class__.__name__,\
                        key,item.__class__.__name__,value.__class__.__name__))

        # Adding an item by its ESDID
        try:
            item=self.esdids[key]
        except KeyError:
            self.esdids[key]=value
            return
        raise KeyError("%s.%s.__setitem__() - "\
            "ESDID %s already defined by %s item, can not add: %s" \
                % (this_module,self.__class__.__name__,\
                    key,item.__class__.__name__,value.__class__.__name__))

    # Locate related ESD items used by an RLD item.  Checks for validity
    # of item types
    # Returns:
    #   a tuple:
    #     [0] - the ESDITEM object related to the rname
    #     [1] - the ESDITEM object related to the pname
    #     [2] - numeric coding of the address constant type
    # Method Arguments:
    #   rname   the name of the RLD referenced item or None for PC. O indicates
    #           no rname.  CXD items have no rname reference.
    #   pname   the name of the RLD position SD item or None for PC
    #   rcls    a class or tuple of classes for which the rname is valid
    #   pcls    a class or tuple of classes for which the pname is valid
    #   atyp    the address constant type being created as a string
    # Raises:
    #   OBJError if any inconsistency of item types or undefined items
    #   encountered
    def _locate_rld_ESD_items(self,rname,pname,rcls,pcls,atyp,ckr=True):
        atyp=RLDITEM.adcons[atyp]
        if ckr:
            try:
                rarea=self[rname]
            except KeyError:
                if rname is None:
                    raise OBJError(\
                        msg="%s-type PC ESD item reference undefined" % atyp)
                raise OBJError(\
                    msg="%s-type %s ESD item reference undefined: %s" \
                        % (atyp,rcls.__name__,rname))
            if not isinstance(rarea,rcls):
                raise OBJError(\
                    msg="%s-type %s reference ESD '%s' not a valid item: %s" \
                        % (atyp,rcls.__name__,rname,rarea.__class__.__name__))
        else:
            rarea=None

        try:
            parea=self[pname]
        except KeyError:
            if pname is None:
                raise OBJError(msg="%s-type position ESD PC is undefined")
            raise OBJError(msg="%s-type position ESD undefined: %s" \
                % (atyp,pname))
        if not isinstance(parea,pcls):
            raise OBJError(msg="%s-type position ESD '%s' not a SD/PC: %s" \
                % (atyp,pname,parea.__class__.__name__))
            
        return (rarea,parea,atyp)

    # This internal method returns the next available ESD ID
    def _next_esdid():
        return len(self.esdids)+1

    # This method is used to add ESDITEM objects to the External Symbol
    # Dictionary.  The caller must supply an ESDITEM object.  Language
    # translators must call one of the MODULE.ESD_xx methods with the
    # appropriate arguments.  The MODULE.ESD_xx method will call one of the
    # ESD_xx methods of this class for ESDITEM creation and addition to the
    # dictionary.
    #
    # The ESD_xx methods that call this method will assign the item's ESDID.
    #
    # Note: the module object may directly call this method becase the decoding
    # process of object records creates ESDITEM's from the object file.
    #
    # Method Argument:
    #   item   the ESDITEM object being added to the External Symbol Dictionary
    # Returns:
    #   None
    # Exceptions:
    #   KeyError for duplicate ESDID or symbols encountered
    #   AssertionError for various argument errors.
    def add_ESD(self,item):
        assert isinstance(item,ESDITEM),\
            "%s %s.add_ESD() - 'item' must be an ESDITEM object: %s" \
                % (this_module,self.__class__.__name__,item)

        if isinstance(item,PC):
            self[item.esdid]=item       # Add the PC item to the ESDID
            self[None]=item             # Add the PC item as an attribute
        elif isinstance(item,LD):
            self[item.sd].ESD_LD(item)  # Add the LD item to the SD/PC
            self[item.symbol]=item      # Add the LD item to the dictionay
        else:
            self[item.symbol]=item      # Add the item to the dictionary
            self[item.esdid]=item       # Add the item to the ESDID

        self.items.append(item)         # Add the item to the list of items

    # This method, similar to the add_ESD() method, is used to add RLD items
    # when the module is being populated from a decoded object deck, or when
    # a language translator is supplying an RLD item.
    def add_RLD(self,rld):
        assert isinstance(rld,RLDITEM),\
            "%s.%s.add_RLD() - 'rld' argument must be an RLDITEM object: %s" \
                % (this_module,self.__class__.__name__,rld)
        parea=self[rld.p]
        parea.RLD(rld)

  #
  #  MODULE to External Symbol Dictionary Interface
  #

    # These methods are used by the MODULE object when a language translator
    # provides object module information destined for objects within the
    # External Symbol Dictionary.  The method names correspond to the same
    # method name used by the MODULE object.

    # Create a CM item and add it to the external symbol dictionary
    # Method Arguments:
    #   symbol    Name of the CM item being added
    #   amode     Address Mode: integers 24, 31, or 64 or True for ANY
    #   rmode     Residnce Mode: integers 24, 31, or 64.
    #   rsect     Read-Only: integer 0 for not read only, 1 for read-only
    #   length    Length of the CM item in bytes
    #   align     CM item alignment: 8 or 16
    # Returns:
    #   the ESDID assigned to the CM item for use by the language translator
    def ESD_CM(self,symbol,amode,rmode,length,align):
        esdid=self._next_esdid()

        cm=CM(symbol,length=length,align=align,amode=amode,rmode=rmode,\
            esdid=esdid)
        self.add_ESD(cm)
        return esdid

    # Add an ER item to the External Symbol Dictionary
    # Method Argument:
    #   symbol  the name of the ER item being added
    # Returns:
    #   ESDID value of the added ER item
    def ESD_ER(self,symbol):
        esdid=self._next_esdid()
        
        er=ER(symbol,esdid=esdid)
        self.add_ESD(er)
        return esdid

    # Create an LD item and add it to the external symbol dictionary
    # Method Argments:
    #   label     The symbol to be assigned to the LD item
    #   section   The section name to which the LD item belongs
    #   address   Address of the LD item within the section
    # Returns:
    #   None
    def ESD_LD(self,label,section,address):
        sect=self[section]    # Validate the section already exists
        ld=LD(label,address,sect.esdid)
        self.add_ESD(ld)

    # Create a PC item and add it to the external symbol dictionary
    # Method Arguments:
    #   address   Starting address of the PC item
    #   amode     Address Mode: integers 24, 31, or 64 or True for ANY
    #   rmode     Residnce Mode: integers 24, 31, or 64.
    #   rsect     Read-Only: integer 0 for not read only, 1 for read-only
    #   length    Length of the PC item in bytes
    #   align     PC item alignment: 8 or 16
    # Returns:
    #   the ESDID assigned to the PC item for use by the language translator
    # Exception:
    #   OBJError if a PC item already exists
    def ESD_PC(self,address,amode,rmode,rsect,length,align):
        if self.pc:
            raise OBJError(msg="%s.%s.add_PC - "\
                "PC item already defined - ESDID: %s" \
                    % (this_module,self.__class__.__name__,self.pc.esdid))

        esdid=self._next_esdid()
        pc=PC(address,rmode=rmode,amode=amode,rsect=rsect,length=length,\
            align=align,esdid=esdid)
        self.add_ESD(PC)
        return esdid

    # Create an SD item and add it to the external symbol dictionary
    # Method Arguments:
    #   symbol    Name of the SD item being added
    #   address   Starting address of the SD item
    #   amode     Address Mode: integers 24, 31, or 64 or True for ANY
    #   rmode     Residnce Mode: integers 24, 31, or 64.
    #   rsect     Read-Only: integer 0 for not read only, 1 for read-only
    #   length    Length of the SD item in bytes
    #   align     SD item alignment: 8 or 16
    # Returns:
    #   the ESDID assigned to the SD item for use by the language translator
    def ESD_SD(self,symbol,address,amode,rmode,rsect,length,align):
        esdid=self._next_esdid()
        
        sd=SD(symbol,address,amode=amode,rmode=rmode,resect=rsect,\
            length=length,align=align,esdid=esdid)
        self.add_ESD(sd)
        return esdid

    # Add an WX item to the External Symbol Dictionary
    # Method Argument:
    #   symbol  the name of the WX item being added
    # Returns:
    #   ESDID value of the added WX item
    def ESD_WX(self,symbol):
        esdid=self._next_esdid()
        
        wx=WX(symbol,esdid=esdid)
        self.add_ESD(wx)
        return esdid

    # Add a XD item to the External Symbol Dictionary
    # Method Arguments:
    #   symbol   the name of the XD item as defined by a DXD or Q-type DSECT
    #            reference
    #   align    the alignment required by the dummy section: 1, 2, 4, 8
    #   length   the length of the dummy section.  A 0 lengh is allowed.
    # Returns:
    #    ESDID of the added XD item
    def ESD_XD(self,symbol,align,length):
        esdid=self._next_esdid()
        
        xd=XD(symbol,align,length,esdid=esdid)
        self.add_ESD(xd)
        return esdid

    # This method creates a A-type RLD item and adds it to its position area
    # Method Arguments:
    #   rname   The name of the section being referenced
    #   pname   The name of the Area object in which the A-type RLD resides
    #   address The address of the A-type constant in the position area
    #   length  The length of the A-type address constant
    #   sign    The sign factor applied to the A-type constant's offset
    # Exceptions:
    #   OBJError if ESD items incorrect or undefined for addres constant type
    def RLD_A(self,rname,pname,address,length,sign):
        rarea,parea,atyp=\
            self._locate_rld_ESD_items(rname,pname,(SD,PC),(SD,PC),"A")
        
        a=RLDITEM(qarea.esdid,parea.esdid,address,atyp,length,sign)
        self.add_RLD(a)

    # Create a CXD-type RLD item and add it to the SD/PC item in which it
    # resides
    def RLD_CXD(self,pname,address,length,sign):
        rarea,parea,atyp=\
            self._locate_rld_ESD_items(None,pname,None,(SD,PC),"CXD",ckr=False)

        cxd=RLDITEM(0,parea.esdid,address,atyp,length,sign)
        self.add_RLD(cxd)

    # This method creates a Q-type RLD item and adds it to its position area
    # Method Arguments:
    #   qname   The name of the external dummy section being referenced
    #   pname   The name of the Area object in which the Q-type RLD resides
    #   address The address of the Q-type constant in the position area
    #   length  The length of the Q-type address constant
    #   sign    The sign factor applied to the Q-type constant's offset
    def RLD_Q(self,qname,pname,address,length,sign):
        qxd,parea,atyp=self._locate_rld_ESD_items(qname,pname,XD,(SD,PC),"Q")

        q=RLDITEM(qxd.esdid,parea.esdid,address,atyp,length,sign)
        self.add_RLD(q)

    # This method creates a V-type RLD item and adds it to its position area
    # Method Arguments:
    #   rname   The name of the section being referenced
    #   pname   The name of the Area object in which the A-type RLD resides
    #   address The address of the A-type constant in the position area
    #   length  The length of the A-type address constant
    #   sign    The sign factor applied to the A-type constant's offset
    # Exceptions:
    #   OBJError if ESD items incorrect or undefined for addres constant type
    def RLD_V(self,rname,pname,address,length,sign):
        rex,parea,atyp=self._locate_rld_ESD_items(rname,pname,EX,(SD,PC),"V")
        
        v=RLDITEM(rex.esdid,parea.esdid,address,atyp,length,sign)
        self.add_RLD(v)


#
#  +-----------------------------------+
#  |                                   |
#  |   Object Module Record Builders   |
#  |                                   |
#  +-----------------------------------+
#

# This group of classes create one or more records of a specific record type.
# The builder classes may be use by record specific encode() methods to
# recreate the record, or by the MODULE object when creating a new object
# module from data supplied by a language translator.

# Superclass of all builder objects
#
# Instance Argument:
#   items   a list of objects of a specific class associated with the builder
#           subclass.
#   cls     The class of each element in the list against which validation
#           occurs.
class OBJBLDR(object):
    def __init__(self,items,cls):
        assert isinstance(items,list),\
            "%s.%s.__init__() - 'items' argument must be a list: %s" \
                % (this_module,self.__class__.__name__,items)

        # Validate list content
        if __debug__:
            for n,item in enumerate(items):
                assert isinstance(item,cls),"%s.%s.__init__() - 'item[%s]' "\
                   "argument must be a %s object: %s" \
                       % (this_module,self.__class__.__name__,n,cls.__name__,\
                           item)

        self.items=items


class RLDBLDR(OBJBLDR):
    def __init__(self,items):
        super().__init__(items,RLDITEM)



#
#  +--------------------------------------+
#  |                                      |
#  |   External Symbol Dictionary Items   |
#  |                                      |
#  +--------------------------------------+
#

# External Symbol Item Format
#  Python
#  Index   Columns    Description
#  [0:8]     1,8      EBCDIC external symbol name
#   [8]       9       External symbol type
#  [9:12]   10,12     External symbol address
#   [12]     13       Flag byte
# [13:16]   14-16     External symbol attribute, varies with type
class ESDITEM(object):
    types=None    # Defined below after all ESDITEM subclasses defined

    # Template for a new bytearray of an ESD item containing 16 EBCDIC spaces.
    new=[0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40]

    zero_addr=bytes(3)  # Three bytes of zeros.

    # Decode the EDS items from an ESD record
    # Method Arguments:
    #   esdid   The first ESDID from the ESD record being decoded
    #   binary  The entire binary data filed of ESD items from the record
    # Returns:
    #   a list of ESDITEM subclasses of the decoded ESD items
    @staticmethod
    def decode(esdid,binary):
        #print("%s.ESDITEM.decode() - esdid: %s" \
        #    % (this_module,esdid))
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__

        items=[]             # List of returned items

        # ESD item loop controls
        length=len(binary)   # Length of the ESD record data
        ndx=0                # Index of next ESD item in the record data

        # Process the individual items in the ESD record data
        while ndx<length:
            if ndx+16>length:
                raise OBJRecordError(\
                    msg="Incomplete ESD item starting at column %s" % ndx+17)

            styp=binary[ndx+8]
            #print("ESDITEM.decode() - type: %02X" % styp)
            try:
                cls=ESDITEM.types[styp]
            except KeyError:
                raise OBJRecordError(\
                    msg="unrecognized ESD item type: 0x%02X" % styp)

            item=cls.decode(esdid,binary[ndx:ndx+16])
            items.append(item)
            ndx+=16
            # Language translators do not assign an ESDID to LD items.  So
            # the incrementing of the initial ESDID is suppressed when an
            # LD item is found.
            if item.__class__.__name__ != "LD":
                esdid+=1

        return items

    @staticmethod
    def decode_symbol(binary):
        return binary.decode(EBCDIC).rstrip()

    def __init__(self,styp,esdid,ignore=False):
        assert isinstance(esdid,int) and esdid>0 or esdid is None,\
            "%s %s ESDID must be a positive integer: %s" \
                % (self.__class__.__name__,self.symbol,esdid)

        self.styp=styp         # Numeric item type from ESD item
        self.esdid=esdid       # ESDID of the item, may be None for LD types
        self.ignore=ignore     # Ignore flag
        self.bin=None          # Decoded binary content.  See decode() method
        self.ebin=None         # Encoded binary content.  See encode() method

    # This method checks an address argument
    # Method Argument:
    #   address  The address being validated
    # Returns:
    #   None
    # Exceptions:
    #   AssertionError if the address is invalid
    def _check_address(self,address):
        assert isinstance(address,int) and address>=0 and address<=0xFFFFFF,\
            "%s %s address must be an integer between 0x0-0xFFFFFF: %s" \
                % (self.__class__.__name,self.symbol,hex(address))

    # This method checks the bin argument.
    # Method Argument:
    #   bin   the ESD item's binary content being checked
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'bin' argument is invalid
    def _check_bin(self,bin):
        assert isinstance(bin,(bytes,bytearray)) or bin is None,\
            "%s %s 'bin' argument must be a bytes sequence: %s" \
                % (self.__class__.__name__,self.symbol,bin)

    # This method checks the esdid argument.
    # Method Argument:
    #   esdid   the ESD item's ESDID being checked
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'esdid' argument is invalid
    def _check_esdid(self,esdid):
        assert isinstance(esdid,int) and esdid>0 and esdid <=32767,\
           "%s %s ESDID must be an integer between 1-32767: %s" \
                % (self.__class__.__name,self.symbol,esdid)

    # This method checks the length argument.
    # Method Argument:
    #   length   the ESD item's ESDID being checked
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'length' argument is invalid
    def _check_length(self,length):
        assert isinstance(length,int) and length>=0 and length<=0xFFFFFF, \
            "%s %s length must an integer between 0x0 and 0xFFFFFF: %s" \
                % (self.__class__.__name,self.symbol,length)

    # This method checks the validity of an ASCII ESD item's name
    # Method Arguments:
    #   name   The name being validated
    #   empty  Specify True if the name may be of zero length.  Specify False
    #          if the name must contain at least one character.  Defaults to
    #          False.
    # Returns:
    #   the valid name as a string
    # Exceptions:
    #   AssertionError if the name is not valid
    def _check_name(self,name,empty=False):
        if name is None:
            # PC item name is None
            return
        assert isinstance(name,str),\
            "%s ESD item name must be a string: %s"\
                % (self.__class__.__name__,name)
        if empty:
            assert len(name)<=8,\
                "%s ESD item name '%s' length must be between 0-8: %s"\
                    % (self.__class__.__name__,name,len(name))
        else:
            assert len(name)>=1 and len(name)<=8,\
                "%s ESD item name '%s' length must be between 1-8: %s"\
                    % (self.__class__.__name__,name,len(name))

        return name

    # Encoded ESD items start as a mutable bytearray of 16 EBCDIC spaces.
    # Returns:
    #   a bytearray of an 'empty' ESD item.
    # Note: subclass encode() methods will add binary data to the bytearray
    # replacing spaces as required.
    def _create_ebin(self):
        return bytearray(ESDITEM.new)

    # Encode the symbol name.
    # Return:
    #   a bytes sequence containing the name field, left justified, as EBCDIC
    #   characters.
    def _encode_symbol(self):
        return a2e(self.symbol.ljust(8))

    # Convert the ESD item into a binary sequence appropriate for adding to
    # an ESD record.  Each subclass must implement this method.  The method
    # must set the 'ebin' attribute with the encoded sequence.  ESD record
    # generation will use the 'ebin' attribute to populate the record with this
    # ESD item's encoding
    #
    # Returns:
    #   None
    def encode(self):
        raise NotImplementedError(\
            "%s.%s.encode() - subclass %s must implement the encode() method"\
                % (this_module,self.__class__.__name__,self.__class__.__name__))


# Superclass for ESD items defining areas: CM, PC, SD, XD.
# This superclass is used to manage contiguous areas in a module.
class Area(ESDITEM):

    # AMODE Values
    amode_mask=0x13
    amode_flags={64:0x10,31:0x02,24:0x01,None:0x00,True:0x03}
    amode_settings={0x00:None,0x01:24,0x02:31,0x03:True,0x10:64}

    # RMODE Values
    rmode_mask=0x24
    rmode_flags={64:0x20,31:0x04,24:0x00,None:0x00,True:0x04}
    rmode_settings={0x00:24,0x20:64,0x04:31,0x01:24}

    # RSECT Values
    rsect_flags={True:0x08,False:0x00}

    @staticmethod
    def decode_amode(flag):
        #print("Area.decode_amode() - flag: %02X" % flag)
        amode_flags = flag & Area.amode_mask
        #print("Area.decode_amode() - amode flags: %02X" % amode_flags)
        try:
            return Area.amode_settings[flag & Area.amode_mask]
        except KeyError:
            raise ValueError("%s.Area.decode_SDPC_flag() - "\
                "unrecognized AMODE value: %02X" \
                    % (this_module, flag & Area.amode_mask)) from None

    @staticmethod
    def decode_rmode(flag):
        try:
            return Area.rmode_settings[flag & Area.rmode_mask]
        except KeyError:
            raise ValueError("%s.Area.decode_SDPC_flag() - "\
                "unrecognized RMODE value: %02X" \
                    % (this_module,flag & Area.rmode_mask)) from None

    @staticmethod
    def decode_section_alignment(styp):
        if styp in [0x0D,0x0E,0x0F]:
            return 16
        return 8

    # Bits   Mask  Meaning:
    #   0,1  0xC0  00 - not used
    #    2   0x20   0 - Use RMODE bit 5
    #               1 - RMODE 64
    #    3   0x10   0 - Use AMODE bits 6, 7
    #               1 - AMODE 64
    #    4   0x08   0 - not an RSECT
    #               1 - RSECT
    #    5   0x04   0 - RMODE 24
    #               1 - RMODE 31, RMODE ANY
    #   6,7  0x03  00 - AMODE 24
    #              01 - AMODE 24
    #              10 - AMODE 31
    #              11 - AMODE ANY
    @staticmethod
    def decode_SDPC_flag(flag):
        rmode=Area.decode_rmode(flag)
        amode=Area.decode_amode(flag)
        rsect = flag & 0x08 == 0x08
        return (rmode,amode,rsect)

    def __init__(self,typ,esdid,name,address,length,align):
        super().__init__(typ,esdid)
        self.symbol=name      # ESD item's name, may be an empty string
        self.address=address  # Area's starting address, may be None
        self.length=length    # ESD item's length, may be 0
        self.align=align      # ESD item's alignment

      #
      # The following attributes are populated by the MODULE object as
      # driven by a language translator, or the MODULE.populate() method
      # from a decoded object deck.
      #

        # List of LD items associated with this area in the order provided
        self.lds=[]           # See ESD_LD() method
        # Dictionary of LD items associated with the area by name
        self.ldict={}         # See ESD_LD() method

        # List of TXTITEM objects associated with this area in the order
        # provided
        self.txts=[]

        # List of RLDITEM objects associated with this area in the order
        # provided.  The position ESDID of the RLD item determines its
        # presence here.
        self.rlds=[]

    # This method checks the alignment argument.
    # Method Argument:
    #   align   the ESD item's alignement being validated as an integer
    # Returns
    #   the ESD item's type field as an integer for the alignment
    # Exception:
    #   AssertionError if the 'align' argument is invalid
    def _check_alignment(self,align):
        assert align in [8,16],\
            "%s %s alignment must be the integers 8 or 16: %s" \
                % (self.__class__.__name__,self.symbol,align)

        if align==16:
            return self.__class__.qtyp
        return self.__class__.typ

    # This method checks the amode argument.
    # Method Argument:
    #   amode   the ESD item's amode being validated
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'amode' argument is invalid
    def _check_amode(self,amode):
        assert amode in Area.amode_flags,\
            "%s %s amode must be either 24, 31, 64, or True (ANY): %s" \
               % (self.__class__.__name__,self.symbol,amode)

    # This method checks the rmode argument.
    # Method Argument:
    #   rmode   the ESD item's rmode being checked
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'rmode' argument is invalid
    def _check_rmode(self,rmode):
        assert rmode in Area.rmode_flags,\
           "%s %s rmode must be either 24, 31, or 64: %s" \
               % (self.__class__.__name__,self.symbol,rmode)

    # This method checks the rsect argument.
    # Method Argument:
    #   rsect   the ESD item's rsect being checked
    # Returns:
    #   None
    # Exception:
    #   AssertionError if the 'rsect' argument is invalid
    def _check_rsect(self,rsect):
        assert rsect in [False,True],\
            "%s %s rsect must be either True or False: %s" \
                % (self.__class__.__name__,self.symbol,rsect)

    # This method checks all of the common section arguments used by SD and PC
    # subclasses
    # Method Arguments:
    #   address   the section's address being validated
    #   rmode     the section's rmode being validated
    #   amode     the section's amode being validated
    #   rsect     the section's rsect being validated
    #   length    the section's length being validated
    #   align     the section's alignment being validated
    #   esdid     the section's ESDID being validated
    #   bin       the section's binary content being validated
    # Returns:
    #   the objects ESDITEM type field value indicating the sections alignment
    # Exception:
    #   AssertionError if any argument fails validation
    def _check_section(self,address,rmode,amode,rsect,length,align,esdid,bin):
        self._check_address(address)
        self._check_rmode(rmode)
        self._check_amode(amode)
        self._check_rsect(rsect)
        self._check_length(length)
        self._check_esdid(esdid)
        self._check_bin(bin)
        return self._check_alignment(align)

    # Encode the item's amode flag setting
    # Returns:
    #   an integer containing the flag setting for the item's amode
    # Exception:
    #   ValueError if the amode value is invalid
    def _encode_amode(self):
        try:
             amode_flag = Area.amode_flags[self.amode]
             #print("_encode_amode() - amode: %02X" % amode_flag)
        except KeyError:
            cls=self.__class__.__name__
            raise ValueError("%s.%s._encode_amode() - "\
                "invalid amode value for ESD item %s %s: %s" \
                    % (this_module,cls,cls,self.symbol,self.amode)) from None

        return amode_flag

    # Encode the item's rmode flag setting
    # Returns:
    #   an integer containing the flag setting for the item's rmode
    # Exception:
    #   ValueError if the rmode value is invalid
    def _encode_rmode(self):
        try:
            return Area.rmode_flags[self.rmode]
            #print("_encode_SDPC_flag rmode: %02X" % rmode_flag)
        except KeyError:
            cls=self.__class__.__name__
            raise ValueError("%s.%s._encode_rmode() - "\
                "invalid rmode value for ESD item %s %s: %s" \
                    % (this_module,cls,cls,self.symbol,self.rmode)) from None

    # This method encodes the area's rmode, amode and rsect attributes.
    # Returns:
    #   an integer encoding the attributes
    def _encode_SDPC_flag(self):
        flag=0
        rmode_flag=self._encode_rmode()
        amode_flag=self._encode_amode()

        try:
            rsect_flag = Area.rsect_flags[self.rsect]
            #print("_encode_SDPC_flag rsect: %02X" % rsect_flag)
        except KeyError:
            cls=self.__class__.__name__
            raise ValueError("%s.%s._encode_SDPC_flag() - "\
                "invalid rsect value for ESD item %s %s: %s" \
                    % (this_module,cls,cls,self.symbol,self.rsect)) from None

        flag=rmode_flag | amode_flag | rsect_flag
        #print("_encode_SDPC_flag flag: %02X" % flag)

        return flag

    # This method returns the value of the ESD item's typ field that encodes
    # section alignment.
    # Return:
    #   an integer value for the ESD item's type field
    def _encode_section_alignment(self):
        if self.align == 8:
            return self.__class__.typ
        elif self.align == 16:
            return self.__class__.qtyp
        else:
            raise ValueError("%s.%s._encode_section_alignment() - "\
                "%s.%s._encode_section_alignment() - section alignment "\
                    "must be 4 or 8: %s" % (this_module,\
                        self.__class__.__name__,self.align))

    # This method adds a LD item to this area's list of LD items.
    # Method Argument:
    #   ld    Must be an LD object
    # Exceptions:
    #   AssertionError if not an LD object,
    #                  if LD section ESDID does not match this area's ESDID, or
    #                  if LD symbol already present in the area
    #
    # Warning: Area objects that do not support LD items must override this
    # method with one that calls _LD_not_supported() method
    def ESD_LD(self,ld):
        assert isinstance(ld,LD),\
            "%s %s.ESD_LD() - 'ld' argument must be an LD object: %s" \
                % (this_module,self.__class__.__name__,ld)
        assert ld.sd == self.esdid,\
            "%s %s.ESD_LD() - LD '%s' section must match %s '%s' ESDID, %s: %s"\
                % (this_module,self.__class__.__name__,ld.symbol,\
                    self.__class.__name,self.symbol,self.esdid,ld.sd)
        assert self.__class__.lds,\
            "%s %s.ESD_LD() - %s '%s' does not support LD items: LD '%s'"\
                % (this_module,self.__class__.__name__,self.__class__.__name__,\
                    self.symbol,ld.symbol)
        assert not ld.symbol in self.ldict,\
            "%s %s.ESC_LD() - duplicate LD '%s' encountered for %s '%s'" \
                % (this_module,self.__class__.__name__,ld.symbol,\
                    self.__class__.__name__,self.symbol)

        self.ldict[ld.symbol]=ld
        self.lds.append(ld)

    # Add a RLD item to this Area's list of position relocation items
    def RLD(self,rld):
        assert isinstance(rld,RLDITEM),\
            "%s %s.RLD() - 'rld' argument must be a RLDITEM object: %s" \
                % (this_module,self.__class__.__name__,rld)
        assert self.__class__.rlds,\
            "%s %s.RLD() - Area '%s' does not support RLD item data" \
                % (this_module,self.__class__.__name__,self.symol)
        assert rld.pptr == self.esdid,\
            "%s %s.RLD() - Area '%s' ESDID %s does not match RLD item pos "\
                "ESDID: %s"  % (this_module,self.__class__.__name__,self.symol,
                    self.esdid,rld.p)

        self.rlds.append(rld)

    # This method adds a TXTITEM instance to the list of TXTITEMs belonging to
    # this area.
    def TXT(self,txt):
        assert isinstance(txt,TXTITEM),\
            "%s %s.TXT() - 'txt' argument must be a TXTITEM object: %s" \
                % (this_module,self.__class__.__name__,txt)
        assert self.__class__.text,\
            "%s %s.TXT() - Area '%s' does not support TXT item data" \
                % (this_module,self.__class__.__name__,self.symol)

        #print("%s.%s.TXT() - adding %s" \
        #    % (this_module,self.__class__.__name__,txt))

        # Validate the text resides completely within the area
        assert self.iswithin(txt.address),\
            "%s %s.TXT() - TXTITEM starting address must be within Area '%s'"\
                " %06X-%06X: %06X" % (this_module,self.__class__.__name__,\
                    self.symbol,self.address,self.address+self.length-1,\
                        txt.address)
        end=txt.address+len(txt)-1
        assert self.iswithin(end),\
            "%s %s.TXT() - TXTITEM ending address must be within Area '%s' "\
                "%06X-%06X: %06X" % (this_module,self.__class__.__name__,\
                    self.symbol,self.address,self.address+self.length-1,end)

        # Add this TXTITEM to the area. This preserves the order of text data
        # presented to the MODULE maintaining any overlay sequence
        self.txts.append(txt)
        # Note: this is done to allow easy stand-alone images to be built by
        # the linkage editor.

    # This method validates than an address is within the range of the Area
    def iswithin(self,address):
        assert isinstance(address,int) and address>=0,\
            "%s.%s.iswithin() - 'address' argument must be a non-negative "\
                "integer: %s" % (this_module,self.__class__.__name__,address)
        return address >= self.address and address < (self.address+self.length)


# Superclass for ESD items defining locations: ER, LD, WX
class Label(ESDITEM):
    def __init__(self,typ,esdid,name,address):
        super().__init__(typ,esdid)
        self.symbol=name
        self.address=address

    # Returns True if label is external.  Otherwise False.
    # Subclass may overrided this method.
    def isExternal(self):
        return True

    # Returns True if the label is weak.  Otherwise False
    # Subclass may override this method.
    def isWeak(self):
        return False


# COMMON SECTION
class CM(Area):
    typ=0x05     # Fullword aligned common section
    qtyp=0x0F    # Quadword aligned common section

    # Other modules content allowed or not to be associated with a CM ESD item
    text=False   # TXT records not allowed in CM
    rlds=False   # RLD items not allowed in CM
    lds=False    # LD ESD items not allowed in CM
    extrns=False # ER ESD items not allowed in CM
    wxtrns=False # WX ESD items not allowed in CM

    # Returns the decoded CM item
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        flag=binary[12]
        amode=Area.decode_amode(flag)
        rmode=Area.decode_rmode(flag)
        length=addr(binary[13:16])
        align=Area.decode_section_alignment(binary[8])
        return CM(name,length=length,align=align,amode=amode,rmode=rmode,\
            esdid=esdid,bin=binary)

    def __init__(self,symbol,length=0,align=8,amode=24,rmode=24,esdid=None,\
                 bin=None):
        # Validate arguments before instantiating superclass
        # These methods may raise an AssertionError
        sym=self._check_name(symbol,empty=True)
        self._check_amode(amode)
        self._check_rmode(rmode)
        assert isinstance(length,int) and length>=0,\
            "%s %s length must be an integer >=0: %s" \
                % (self.__class__.__name__,symbol,length)
        typ=self._check_alignment(align)
        self._check_bin(bin)

        super().__init__(typ,esdid,sym,None,length,align)
        self.bin=bin      # Decoded binary content

        self.amode=amode  # Default
        self.rmode=rmode

    # Convert the CM object into a byte sequence
    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]  =self._encode_symbol()
        ebin[8]    =self._encode_section_alignment()
        # Mainframe assemblers set the ESD item address field to 0 in CM items.
        # While there is no documented reason for this, for compatibility
        # the address is also set to 0 here.
        ebin[9:12] =ESDITEM.zero_addr
        # Contrary to documention stating the flag byte is not used by CM,
        # the CM flag is used to encode the CM item's amode and rmode.
        ebin[12]   =self._encode_amode() | self._encode_rmode()
        ebin[13:16]=addr2bin(self.length)
        self.ebin=bytes(ebin)


# EXTERNAL REFERENCE
# Created by an EXTRN assembler directive
class ER(Label):
    typ=0x02

    # Returns the decoded LD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        return ER(name,esdid=esdid,bin=binary)

    def __init__(self,symbol,esdid=None,bin=None):
        sym=self._check_name(symbol)
        self._check_bin(bin)

        super().__init__(ER.typ,esdid,sym,None)

        self.bin=bin    # Decoded binary content

    # Convert the ER object into a byte sequence
    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]  =self._encode_symbol()
        ebin[8]    =self.__class__.typ
        # Mainframe assemblers set the ESD item address field to 0 in ER items.
        # While there is no documented reason for this, for compatibility
        # the address is also set to 0 here.
        ebin[9:12] =ESDITEM.zero_addr
        self.ebin=bytes(ebin)


# LABEL DEFINITION
# Defined by an ENTRY assembler directive
class LD(Label):
    typ=0x01

    # Returns the decoded LD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        address=addr(binary[9:12])
        sd=addr(binary[13:16])
        return LD(name,address,sd,bin=binary)

    def __init__(self,symbol,address,sd,bin=None):
        sym=self._check_name(symbol)
        self._check_address(address)
        self._check_esdid(sd)

        super().__init__(LD.typ,None,sym,address)

        self.sd=sd                # Section ESDID containing the label
        self.bin=bin              # Decoded binary content. May be None

    # Encode the LD item as a byte sequence
    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]  =self._encode_symbol()
        ebin[8]    =self.__class__.typ
        ebin[9:12] =addr2bin(self.address)
        ebin[13:16]=addr2bin(self.sd)
        self.ebin=bytes(ebin)

    # LD items are not external
    def isExternal(self):
        return False


# PRIVATE CODE (UNNAMED CONTROL SECTION)
class PC(Area):
    typ=0x04     # Fullword aligned private code
    qtyp=0x0E    # Quadword aligned private code

    # Other module content allowed or not to be associated with a PC ESD item
    text=True    # TXT records allowed in PC
    rlds=True    # Positional RLD items allowed in PC
    lds=True     # LD ESD items allowed in PC
    extrns=True  # ER ESD items allowed in PC
    wxtrns=True  # WX ESD items allowed in PC

    # Returns the decoded PC item
    @staticmethod
    def decode(esdid,binary):
        address=addr(binary[9:12])
        rmode,amode,rsect=Area.decode_SDPC_flag(binary[12])
        length=addr(binary[13:16])
        align=Area.decode_section_alignment(binary[8])
        return PC(address,rmode=rmode,amode=amode,\
            rsect=rsect,length=length,align=align,esdid=esdid,bin=binary)

    def __init__(self,address,rmode=24,amode=24,rsect=False,length=0,\
                 align=8,esdid=None,bin=None):

        typ=self._check_section(\
            address,rmode,amode,rsect,length,align,esdid,bin)

        super().__init__(typ,esdid,"''",address,length,align)

        self.address=address
        self.rmode=rmode
        self.amode=amode
        self.rsect=rsect
        self.bin=bin    # Decoded binary content

    # Encode the PC item as a byte sequence
    def encode(self):
        ebin=self._create_ebin()
        ebin[8]    =self._encode_section_alignment()
        ebin[9:12] =addr2bin(self.address)
        ebin[12]   =self._encode_SDPC_flag()
        ebin[13:16]=addr2bin(self.length)
        self.ebin=bytes(ebin)


# CONTROL SECTION DEFINITION
# Created by CSECT or RSECT assembler directive
class SD(Area):
    typ=0x00     # Fullword aligned control section
    qtyp=0x0D    # Quadword aligned control section

    # Other module content allowed or not to be associated with a SM ESD item
    text=True    # TXT records allowed in SD
    rlds=True    # Positional RLD items allowed in SD
    lds=True     # LD ESD items allowed in SD
    extrns=True  # ER ESD items allowed in SD
    wxtrns=True  # WX ESD items allowed in CM

    # Returns the decoded SD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        address=addr(binary[9:12])
        length=addr(binary[13:16])
        align=Area.decode_section_alignment(binary[8])
        rmode,amode,rsect=Area.decode_SDPC_flag(binary[12])
        return SD(name,address,amode=amode,rmode=rmode,rsect=rsect,\
            length=length,align=align,esdid=esdid,bin=binary)

    def __init__(self,symbol,address,amode=24,rmode=24,rsect=0,length=0,\
                 align=8,esdid=None,bin=None):
        self.symbol=self._check_name(symbol)
        typ=self._check_section(\
            address,rmode,amode,rsect,length,align,esdid,bin)

        super().__init__(typ,esdid,symbol,address,length,align)

        self.amode=amode            # Address mode
        self.rmode=rmode            # Residency mode
        self.rsect=rsect            # Whether a read only section
        self.bin=bin                # Decoded binary content.  May be None

    # Encode the SD item as a byte sequence
    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]  =self._encode_symbol()
        ebin[8]    =self._encode_section_alignment()
        ebin[9:12] =addr2bin(self.address)
        ebin[12]   =self._encode_SDPC_flag()
        ebin[13:16]=addr2bin(self.length)
        self.ebin=bytes(ebin)


# WEAK EXTERNAL REFERENCE
class WX(Label):
    typ=0x0A
    prev=False   # Whether to use the previous ESDID for this item

    # Returns the decoded WX item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        return WX(name,esdid=esdid,bin=binary)

    def __init__(self,symbol,esdid=None,bin=None):
        sym=self._check_name(symbol)
        self._check_esdid(esdid)
        self._check_bin(bin)

        super().__init__(WX.typ,esdid,sym,None)

        self.bin=bin    # Decoded binary content

    # Encode the WX ESD item
    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]=self._encode_symbol()
        ebin[8]  =self.__class__.typ
        # Mainframe assemblers set the ESD item address field to 0 in WX items.
        # While there is no documented reason for this, for compatibility
        # the address is also set to 0 here.
        ebin[9:12]=ESDITEM.zero_addr
        self.ebin=bytes(ebin)

    # WX items are weak
    def isWeak(self):
        return True


# EXTERNAL DUMMY SECTION
class XD(Area):
    typ=0x06
    prev=False   # Whether to use the previous ESDID for this item

    # Other module content allowed or not to be associated with a XD ESD item
    text=False   # TXT records not allowed in CM
    rlds=False   # RLD items not allowed in CM
    lds=False    # LD ESD items not allowed in CM
    extrns=False # ER ESD items not allowed in CM
    wxtrns=False # WX ESD items not allowed in CM

    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        align=binary[12]+1
        length=addr(binary[13:16])
        return XD(name,align,length,esdid=esdid,bin=binary)

    def __init__(self,symbol,align,length,esdid=None,bin=None):
        sym=self._check_name(symbol)

        super().__init__(XD.typ,esdid,sym,None,length,align)

        self.bin=bin    # Decoded binary content
        self.ebin=None  # Encoded binary content

    # Overrides Area superclass method
    # Excpetions:
    #   NotImplementedError if an LD item is being added to a CM area
    #   AssertionError      if an item other than LD is being added.
    def ESD_LD(self,ld):
        assert isinstance(ld,LD),\
           "%s %s.ESD_LD() - 'ld' argument must be an LD object: %s" \
                % (this_module,self.__class__.__name__,ld)
        self._LD_not_supported(ld)

    def encode(self):
        ebin=self._create_ebin()
        ebin[0:8]  =self._encode_symbol()
        ebin[8]    =self.__class__.typ
        # Mainframe assemblers set the ESD item address field to 0 in XD items.
        # While there is no documented reason for this, for compatibility
        # the address is also set to 0 here.
        ebin[9:12] =ESDITEM.zero_addr
        ebin[12]   =self.align-1
        ebin[13:16]=addr2bin(self.length)
        self.ebin=bytes(ebin)



# Initialize ESDITEM class attribute of item types
# This can not be done until each subclass has been created during import
ESDITEM.types={CM.typ:CM,ER.typ:ER,LD.typ:LD,SD.typ:SD,PC.typ:PC,XD.typ:XD,\
               WX.typ:WX,\
               SD.qtyp:SD,PC.qtyp:PC,CM.qtyp:CM}  # These are quad-aligned


#
#  +--------------------------------+
#  |                                |
#  |   Relocation Dictionary Item   |
#  |                                |
#  +--------------------------------+
#

# Relocation Item Format
#  Python
#  Index   Columns    Description
#  [0:2]     1,2      Relocation Pointer ESD-ID of address being relocated
#  [2:4]     3,4      Position Pointer ESD-ID of field being relocated
#   [4]       5     * Flag byte
#  [5:8]     6-8    * Position offset from the Position Pointer to the field
#                     being relocated
#
# * These fields are always present in each RLD item.  Others are controlled by
# * the flag byte

# Instance Arguments:
#   r     ESDID integer of the reference pointer SD, PC, ER, WX
#   p     ESDID integer of the position pointer constant's SD or PC
#   a     Position address of the constant being relocated within the p ESDID
#         SD or PC.
#   atyp  Address Constant Type:
#           0 -> A type
#           1 -> V type
#           2 -> Q type
#           3 -> CXD type
#           4 -> Relative immediate
#   length Length of the postion constant being relocated
#   sign   +1 or -1 depending upon how the position constant's text adjusts
#          the reference pointer ESDID address
#   same   Whether the next RLD item refers to the same position and reference
#          ESDID's.  Defaults to False.  The last RLD item in an RLD record
#          must be False
#   short  Whether this RLD item is encoded using the short format (True) or
#          the long format (False).  Defaults to False (long format).  The
#          first RLD item in an RLD record must always be False, using the
#          long format.
#   valid  Whether the same and short attributes are valid (True), or invalid
#          (False).   The RLDITEM decode() method can set this attribute to
#          True.  The RLDBLDR object will determine the same and short
#          attributes at which time the valid attribute will be set True.
class RLDITEM(object):
    types=["A","V","Q","CXD","RI"]
    adcons={"A":0,"V":1,"Q":2,"CXD":3,"RI":5}

    # Target adjustment direction
    incdir={-1:0b00000010,1:0}

    # Relative immediate flags:
    relim={2:0b01110000,4:0b01111000}

    # Decodes a single RLD record's data into a list of RLDITEM objects
    @staticmethod
    def decode(binary):
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__

        items=[]           # List of returned items

        # RLD item loop controls
        length=len(binary) # Length of the RLD record data
        ndx=0              # Index of next RLD item in the record data

        # Truncated RLD item controls for RLD items using previous item pointers
        same=0             # Whether this item uses the previous item's pointers
        # The first RLD item in a record is always a full entry.
        prevr=None         # Previous R-pointer ESDID
        prevp=None         # Previous P-pointer ESDID

        last=False         # Whether this is the last RLD item in the data

        # Process the individual items in the RLD record data
        while ndx<length:

            # Determine if this RLD item is full (8 bytes) or
            # truncated (4 bytes)
            if same:
                # Determine if the binary data contains a complete truncated
                # RLD entry
                if ndx+4>length:
                    raise OBJRecordError(\
                        msg="Incomplete RLD item at column %s" % ndx+17)
                itembin=common=binary[ndx:ndx+4]
                pptr=prevp
                rptr=prevr
                ndx+=4     # Index of next RLD item in the binary data
                short=True # This is a short item
            else:
                #print("objlib.RLDITEM.decode - full entry index: %s" %ndx)
                # Determine if the binary data contains a complete full RLD
                # entry
                if ndx+8>length:
                    raise OBJRecordError(\
                        msg="Incomplete RLD item at column %s" % ndx+17)
                itembin=binary[ndx:ndx+8]
                common=itembin[4:8]
                prevr=rptr=hword(itembin[0:2])
                #print("objlib.RLDITEM.decode - rptr: %s" % rptr)
                prevp=pptr=hword(itembin[2:4])
                #print("objlib.RLDITEM.decode - pptr: %s" % pptr)
                ndx+=8      # Index of the next RLD item in the binary data
                short=False

            if ndx == length:
                last = True
            elif ndx > length:
                raise OBJRecordError(\
                    msg="RLD item index, %s, exceeds RLD binary length: %s" \
                        % (ndx,length))

            # Common field processing for all RLD items
            address=addr(common[1:4])
            flag=common[0]

            # Indicate whether the next RLD item is truncated
            same=flag & 0b00000001
            # Note this flag must not be set in the last RLD item of the
            # record.
            if same and last:
                raise OBJRecordError(\
                    msg="Last RLD item, %s has 'next item truncated flag set'"\
                        % len(items)+1)

            # Determine how RLD item's position TXT data is used to relocate
            # relocation pointer (it's ESDID).
            if flag & 0b00000010:
                # Subtract RLD item's TXT data from the reference ESDID start
                sign=-1
            else:
                # Add RLD item's TXT data to the reference ESDID start
                sign=+1

            # Recognize special flag combinations for relative immediate
            # field lengths
            relfld=flag &  0b01111100
            if relfld   == 0b01110000:
                atyp=4       # Relative immediate field
                l=2          # of 2 bytes
            elif relfld == 0b01111000:
                atyp=4       # Relative immediate field
                l=4          # of 4 bytes
            else:
                # Otherwise use the flag to determine address type and length
                atyp=(flag & 0b00110000) >> 4

                # Determine whether field length is 1-4 or 5-8 bytes in length
                if flag & 0b01000000 == 0b01000000:
                    linc=4   # Add 4 to the address constant length
                else:
                    linc=0   # Do not add 4 to the address constant length

                # Determine generic relocation field length
                l = ((flag & 0b00001100) >> 2) +1
                l += linc  # Add the address length increment

            rld=RLDITEM(rptr,pptr,address,atyp,l,sign,same=same,short=short,\
                valid=True,bin=itembin)
            items.append(rld)

        # Return completed list of RLDITEM objects
        return items

    def __init__(self,r,p,a,atyp,length,sign,same=False,short=False,\
                 valid=False,bin=None):
        self.bin=bin       # Decoded binary data.  May be None
        self.ebin=None     # Encoded binary data.  May be None

        self.rptr=r        # ESDID of target address being relocated
        # Note: rptr is 0 for CXD RLD items
        # Target address being relocated is located at the following position
        self.pptr=p        # Position ESDID of constant being relocated
        self.address=a     # Assigned address of the constant being relocated
        # Type of address constant:
        #  0 -> A type
        #  1 -> V type
        #  2 -> Q type
        #  3 -> CXD type
        #  4 -> Relative immediate
        self.adcon=atyp    # Type of address constant
        self.length=length # Length of the position constant being relocated
        self.sign=sign     # Sign factor: +1 or -1

        # This attribute is set by the RLDBLDR object when creating RLD records
        # It will encode the flag in this, the preceding item, that the next
        # will be short.
        self.same=same    # When True the next RLD will be a short RLD
        # When this attribute is True this RLD item will be encoded as short
        self.short=short
        # When this attribute is True, self.same and self.short are valid
        self.flag_valid=valid

        if __debug__:
            if self.bin and self.flag_valid:
                if self.short:
                    assert len(bin) == 4,\
                        "%s.%s.__init__() - short RLD item must be 4 bytes: %s"\
                            % (this_module,self.__class__.__name__,len(bin))
                else:
                    assert len(bin) == 8,\
                        "%s.%s.__init__() - full RLD item must be 8 bytes: %s"\
                            % (this_module,self.__class__.__name__,len(bin))

    # Encodes the flag byte
    def _encode_flag(self):
        flag=0
        if self.same:
            flag |= 0b00000001
        try:
            flag |= RLDITEM.incdir[self.sign]
        except KeyError:
            raise ValueError("%s.%s._create_flag() - "
                "self.sign not +1 or -1: %s" \
                    % (this_module,self.__class__.__name__,self.sign))
        if self.adcon == 4:
            try:
                flag |= RLDITEM.relim[self.length]
            except KeyError:
                raise ValueError("%s.%s._create_flag() - "
                    "relative immediate length not 2 or 4: %s" \
                        % (this_module,self.__class__.__name__,self.length))
        else:
            if self.length > 4:
                flag |= 0b01000000
                l=self.length - 4
            else:
                l=self.length
            flag |= ((l-1) & 0x03) << 2   # Encode the length
        flag |= (self.adcon & 0x03) << 4  # Encdoe the adcon type
        return flag

    def encode(self):
        assert self.flag_valid,\
            "%s.%s.encode() - can not encode RLD item, flag is not valid" \
                % (this_module,self.__class__.__name__)

        if self.short:
            ebin=bytearray(4)
            ebin[0]=self._encode_flag()
            ebin[1:4]=addr2bin(self.address)
            assert len(ebin) == 4,\
                "%s.%s.encode() - short RLD item must be 4 bytes: %s" \
                    % (this_module,self.__class__.__name__,len(ebin))
        else:
            ebin=bytearray(8)
            ebin[0:2]=hword2bin(self.rptr)
            ebin[2:4]=hword2bin(self.pptr)
            ebin[4]=self._encode_flag()
            ebin[5:8]=addr2bin(self.address)
            assert len(ebin) == 8,\
                "%s.%s.encode() - full RLD item must be 8 bytes: %s" \
                    % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)

#
#  +---------------------------+
#  |                           |
#  |   Object Module Records   |
#  |                           |
#  +---------------------------+
#

class OBJREC(object):
    types=None   # Dictionary of recognized object record types.
    #Initialized below after all OBJREC subclasses are defined.

    # Encoded object record template
    new=[0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40,0x40]

    # Decode a bytes object of length 80 into a OBJREC subclass
    # Method Arguments:
    #   binary  a Python bytes object of length 80
    #   items   Specify False to suppress decoding of record items.
    #           Specify True to decode record items.  Defaults to True.
    @staticmethod
    def decode(binary,recnum=None,items=True):
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__
        assert len(binary)==80,"bytes object must of length 80: %s" \
            % len(binary)

        rtyp=binary[:4]
        try:
            cls=OBJREC.types[rtyp]
        except KeyError:
            cls=PUNCH      # Assume this is a PUNCH'd object record
        #print("OBJREC.decode - %s" % cls)
        obj=cls.decode(binary,recnum=recnum,items=items)
        return obj

    def __init__(self,typ,recnum=None,ignore=False):
        self.recnum=recnum
        self.typ=typ
        self.ignore=ignore

        self.bin=None     # Decoded binary content
        self.ebin=None    # Encoded binary content


# Format used by the END record:
#  Python
#  Index   Columns Type  Description
#   [0]       1         * X'02' constant data
#  [1:4]     2-4        * Record type: EBCDIC 'END' characters
#   [4]       5         * EBCDIC space character (X'40')
#  [5:8]     6-8      1   Optional entry address or EBCDIC spaces
#  [8:14]    9-14         EBCDIC space characters (X'40)
# [14:16]   15,16     1   ESD-ID of entry address if present, EBCDIC spaces
#                         otherwise
# [16:24]   17-24     2   Symbol name of entry point, otherwise EBCDIC spaces
# [24:28]   25-28         EBCDIC space characters (X'40')
# [28:32]   29-32     1   Length of SD ESD item without a length, byte 29 is
#                         X'00'
#   [32]     33           EBCDIC 1 (X'F1') or 2 (X'F2') of number of IDR
#                         entries. EBCDIC space if no IDR entries.
# [33:52]   34-52         IDR Record 1
# [52:71]   53-71         IDR Record 2
# [72:80]   73-80       * Not used, reserved for optional deck ID or EBCDIC
#                         spaces
#
# * These fields are present in all records.
#
# ID Record Data Format
#  Python
#  Index   Columns    Description
# [33:43]    34-43    Translator Identification: 10 EBCDIC characters
# [43:45]    44,45    Version Level: 2 EBCDIC numbers
# [45:47]    46,47    Releave Level: 2 EBCDIC numbers
# [47:49]    48,49    Last two digits of processing year: 2 EBCDIC numbers
# [49:52]    50-52    Day of processing year: 3 EBCDIC numbers

class IDR(object):
    new=[0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40,0x40,\
         0x40,0x40,0x40]

    @staticmethod
    def decode(binary):
        assert len(binary)==19,\
            "%s.IDR.decode() - IDR binary data must be 19 bytes: %s" \
                % (this_module,len(binary))

        trans=binary[0:10]
        trans=trans.decode(EBCDIC).rstrip()

        V=[]
        for beg,end in [(10,12),(12,14),(14,16),(16,19)]:
            ebcdic=binary[beg:end]
            ascii=ebcdic.decode(EBCDIC)
            try:
                value=int(ascii)
            except ValueError:
                value=None
            V.append(value)

        return IDR(trans=trans,ver=V[0],rel=V[1],yr=V[2],day=V[3],bin=binary)

    def __init__(self,trans=None,ver=None,rel=None,yr=None,day=None,bin=None):
        self.bin=bin         # Decoded binary content.  May be None.
        self.ebin=None       # Encoded binary content.  May be None.
        self.trans=trans     # Translator name as a string
        self.ver=ver         # Translator version as an integer
        self.rel=rel         # Translator release as an integer
        self.yr=yr           # Object two digit creation year as an integer
        self.day=day         # Object three digit creation day as an integer

    def encode(self):
        ebin=bytearray(IDR.new)
        if self.trans is not None:
            ebin[0:10]=a2e(self.trans.ljust(10))
        if self.ver is not None:
            ebin[10:12]=a2e("%02d" % self.ver)
        if self.rel is not None:
            ebin[12:14]=a2e("%02d" % self.rel)
        if self.yr is not None:
            ebin[14:16]=a2e("%02d" % self.yr)
        if self.day is not None:
            ebin[16:19]=a2e("%03d" % self.day)
        assert len(ebin) == 19,\
            "%s.%s.encode() - length of IDR must be 19: %s" \
                % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)


class END(OBJREC):
    ID=b'\x02\xC5\xD5\xC4'
    IDR={0x40:0,0xF1:1,0xF2:2}
    IDRFLAG={0:0x40,1:0xF1,2:0xF2}

    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        length=entsym=entsd=entaddr=None
        if binary[23]!=0x40:
            # Extract type 2 data
            entsym=ESDITEM.decode_symbol(binary[16:24])
        else:
            # Extract type 1 data
            sd=hword(binary[14:16])
            address=addr(binary[5:8])
            if address!=0x40404040:
                entaddr=address
                entsd=sd
        # Length for SD/PC without a length
        if binary[28]==0x00:
            length=addr(binary[29:32])

        # Process IDR information
        idrs=[]
        num=0
        idrflag=binary[32]
        try:
            num=END.IDR[idrflag]
        except KeyError:
            raise OBJRecordError(msg=\
                "END column 33 invalide IDR flag: 0x%02X" % idrflag)

        if num and items:
            for n in range(num):
                ndx=n*19+33
                idrdata=binary[ndx:ndx+19]
                idr=IDR.decode(idrdata)
                idrs.append(idr)

        return END(recnum=recnum,sdlen=length,entsd=entsd,entaddr=entaddr,\
            sym=entsym,numidrs=num,items=idrs,bin=binary)

    def __init__(self,recnum=None,sdlen=None,entsd=None,entaddr=None,sym=None,\
                 numidrs=0,items=[],bin=None):
        super().__init__("END",recnum=recnum)

        self.bin=bin        # Decoded binary content. May be None.
        self.ebin=None      # Encoded binary content. May be None.
        if entsd is not None:
            self.endtyp=2
        else:
            self.endtyp=1

        self.sdlen=sdlen     # Length of SD or PC ESD entry with a zero length
        self.numidrs=numidrs # Number of IDRs in record
        self.items=items     # Index 0 = source translator, 1 = source creator

        # Type 1 Data
        self.entsd=entsd     # Type 1 ESD-ID of entry address
        self.entaddr=entaddr # Type 1 Entry address

        # Type 2 Data
        self.entsym=sym      # Type 2 symbolic entry point

    def encode(self):
        assert len(self.items) <= 2,\
            "%s.%s.encode() - more than 2 IDR items present: %s" \
                % (this_module,self.__class__.__name__,len(self.items))

        ebin=bytearray(OBJREC.new)
        ebin[0:4]=END.ID

        if self.endtyp == 1:
            if self.entsd:
                ebin[14:16]=hword2bin(self.entsd)
            if self.entaddr:
                ebin[5:8]=hword2bin(self.entaddr)
        elif self.endtyp == 2:
            if self.entsym:
                ebin[16:24]=a2e(self.entsym.ljust(8))
        else:
            raise ValueError("%s.%s.encode() - self.endtyp not 1 or 2: %s" \
                % (this_module,self.__class__.__name__,self.endtyp))

        if self.sdlen:
            ebin[28]=0
            ebin[29:32]=addr(self.sdlen)

        if self.items:
            for n,item in enumerate(self.items):
                item.encode()
                ndx=n*19+33
                ebin[ndx:ndx+19]=item.ebin

        ebin[32]=END.IDRFLAG[len(self.items)]

        assert len(ebin)==80,\
            "%s.%s.encode() - ebin not 80 bytes: %s" \
                % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)


# General record format used by ESD, TXT, RLD and SYM records of 80 bytes:
#  Python
#  Index   Columns    Description
#   [0]       1     * X'02' constant data
#  [1:4]     2-4    * Record type: EBCDIC 'ESD', 'TXT', 'RLD' or 'SYM'
#                     characters
#   [4]       5     * EBCDIC space character (X'40')
#  [5:8]     6-8      TXT only: 24-bit address.  ESD, RLD and SYM: EBCDIC
#                     spaces
#  [8:10]    9,10   C EBCDIC space characters (X'40')
# [10:12]   11,12   C Number of bytes of record data, unsigned big-endian binary
# [12:14]   13,14   C EBCDIC space characters (X'40')
# [14:16]   15,16     ESD, TXT: ESD-ID of first item or text.  RLD, SYM: EBCDIC
#                     spaces
# [16:72]   17-72   C Record data (56 bytes)
# [72:80]   73-80   * Not used, reserved for optional deck ID or EBCDIC spaces
#
# C indicates the field is common to all record types using the general format.
# * indicates the field is present in all records.
#

class ESD(OBJREC):
    ID=b'\x02\xC5\xE2\xC4'

    # Returns an RLD object containing the record's RLD items
    # Method Arguments:
    #   binary  a bytes object of length 80
    #   recnum  Optional record number
    #   items   Specify False to suppress decoding of record items.
    #           Specify True to decode record items.  Defaults to True.
    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        length=hword(binary[10:12])
        esditems=binary[16:length+16]

        # Note: LD items are not assigned an ESDID by the language translator.
        # In an ESD record containing only LD items the ESDID field of the ESD
        # record contains blanks.  In this case the ESDID would have a value
        # of 16,448.  For such a record, this value will be ignored by the
        # ESDITEM.decode() method.
        esdid=hword(binary[14:16])

        if items:
            esd_items=ESDITEM.decode(esdid,esditems)
        else:
            esd_items=[]

        return ESD(recnum=recnum,length=length,esdid=esdid,items=esd_items,\
            bin=binary)

    def __init__(self,recnum=None,length=None,esdid=None,items=[],bin=None):
        super().__init__("ESD",recnum=recnum)
        self.bin=bin         # Decoded binary content. May be None
        self.length=length   # Length of binary data in ESD record. May be None
        self.esdid=esdid     # ESD ID of first ESD item in record. May be None
        self.items=items     # List of ESDITEM objects from ESD.decode() method

    def encode(self):
        ebin=bytearray(OBJREC.new)
        ebin[0:4]=ESD.ID

        first_esdid=None
        length=0
        ndx=16
        for item in self.items:
            item.encode()
            assert len(item.ebin) == 16,\
                "%s.%s.encode() - ESD item %s %s length must be 16: %s"\
                    % (this_module,self.__class__.__name__,\
                        self.__class__.__name__,item.symbol,len(item.ebin))
            if item.esdid and not first_esdid:
                first_esdid=item.esdid
            length+=len(item.ebin)
            ebin[ndx:ndx+16]=item.ebin
            ndx+=16
        if first_esdid:
            ebin[14:16]=hword2bin(first_esdid)
        ebin[10:12]=hword2bin(length)

        assert len(ebin)==80,\
            "%s.%s.encode() - ebin not 80 bytes: %s" \
                % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)


class PUNCH(OBJREC):
    ID=None

    # Returns a PUNCH'd object record containing EBCDIC text
    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        return cls(recnum=recnum,bin=binary)

    def __init__(self,recnum=None,bin=None):
        super().__init__(None,recnum=recnum,ignore=True)
        self.bin=bin

    def encode(self):
        self.ebin=self.bin


class RLD(OBJREC):
    ID=b'\x02\xD9\xD3\xC4'

    # Returns an RLD object containing the record's RLD items
    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        length=hword(binary[10:12])
        rlditems=binary[16:length+16]
        if items:
            esd_items=RLDITEM.decode(rlditems)
        else:
            esd_items=[]
        return RLD(recnum=recnum,length=length,items=esd_items,bin=binary)

    def __init__(self,recnum=None,length=None,items=[],bin=None):
        super().__init__("RLD",recnum=recnum)
        self.bin=bin          # Decoded binary content. May be None.
        self.length=length    # Length of RLD items in record
        self.items=items      # List of RLDITEM objects

    def encode(self):
        ebin=bytearray(OBJREC.new)
        ebin[0:4]=RLD.ID

        data=bytearray(0)
        for item in self.items:
            item.encode()
            data.extend(item.ebin)
        assert len(data)<=56,\
            "%s.%s.encode() - record data may not exceed 56 bytes: %s" \
                % (this_module,self.__class__.__name__,len(data))
        ebin[10:12]=hword2bin(len(data))
        ebin[16:len(data)+16]=data

        assert len(ebin)==80,\
            "%s.%s.encode() - ebin not 80 bytes: %s" \
                % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)


# If encountered, SYM records are ignored
class SYM(OBJREC):
    ID=b'\x02\xE2\xE8\xD4'

    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        return SYM(recnum=recnum)

    def __init__(self,recnum=None):
        super().__init__("SYM",recnum=recnum,ignore=True)

    def encode(self):
        raise NotImplementedError(\
            "%s.%s.encode() - SYM record encoding not supported" \
                % (this_module,self.__class__.__name__))


class TXT(OBJREC):
    ID=b'\x02\xE3\xE7\xE3'

    # Returns a TXT object containing the record's content
    # Method Arguments:
    #   binary  a bytes object length 80.
    #   items   Ignored.  This argument is simply for compatibility with other
    #           decode methods that utilize the argument
    @classmethod
    def decode(cls,binary,recnum=None,items=True):
        address=addr(binary[5:8])
        esdid=hword(binary[14:16])
        length=hword(binary[10:12])
        text=binary[16:length+16]
        return TXT(length,address,esdid,text,recnum=recnum,bin=binary)

    def __init__(self,length,addr,esdid,text,recnum=None,bin=None):
        assert isinstance(text,bytes),\
           "'text' argument must be a bytes object: %s" % text
        assert len(text)>0 and len(text)<=56,\
           "'text' argument must be of length between 1 to 56: %s" % len(text)
        assert len(text) == length,\
           "'length' argument, %s must match length of text data, %s" \
               % (length,len(text))
        super().__init__("TXT",recnum=recnum)

        self.bin=bin         # Decoded binary content. May be None
        self.length=length   # Length of text data
        self.address=addr    # Address of TXT data. May be None
        self.esdid=esdid     # ESDID to which TXT data belongs
        self.text=text       # TXT record data

    def encode(self):
        ebin=bytearray(OBJREC.new)
        ebin[0:4]=TXT.ID
        ebin[5:8]=addr2bin(self.address)
        ebin[10:12]=hword2bin(self.length)
        ebin[14:16]=hword2bin(self.esdid)
        ebin[16:self.length+16]=self.text

        assert len(ebin)==80,\
            "%s.%s.encode() - ebin not 80 bytes: %s" \
                % (this_module,self.__class__.__name__,len(ebin))
        self.ebin=bytes(ebin)


# While TXT records do not contain any items, this class is used when a
# language translator provides a byte sequence to be added to TXT records.
# The MODULE object uses instances of this class to create full TXT records.
class TXTITEM(object):
    def __init__(self,esdid,address,binary):
        self.esdid=esdid
        self.address=address
        self.bin=binary
    def __len__(self):
        return len(self.bin)
    def __str__(self):
        return "TXTITEM - ESDID:%s, address:%0X, length:%s" \
            % (self.esdid,self.address,len(self.bin))


# PSW record -- defines the IPL PSW used for stand alone program
#  Python
#  Index   Columns    Description
#   [0]       1       An EBCDIC asterisk (X'5C')
#  [1:4]     2-4    * Record type: EBCDIC 'PSW' characters
#   [4]       5     * EBCDIC space character (X'40')
#   [5]       6       PSW Format: EBCDIC 'B', 'E'
#   [6]       7       EBCDIC space
#  [7:15]    8-15     EBCDIC external entry symbol
#   [15]      16      EBCDIC space
# [16:72]   17-72   C Record data (56 bytes) - PSW attributes
# [72:80]   73-80   * Not used, reserved for optional deck ID or EBCDIC spaces
#
# PSW Attributes:
#   [0:2]    1,2      Interrupt Mask in EBCDIC hex.  Spaces implies '00'
#    [2]      3       EBCDIC space
#    [3]      4       Key in EBCDIC hex.  Space implies '0'
#    [4]      5       System Mask in EBCDIC hex.  Space implies '0'
#    [5]      6       EBCDIC space
#   [6:8]    7,8      Program mask in EBCDIC hex.  Spaces implies '00'
#    [8]      9       EBCDIC space
#   [9:11]  10,11     Address mode: '24' or '31'.  Spaces implies 24.
class PSW(OBJREC):
    ID=b'\x5C\xD7\xE2\xE7'
    amodes={"  ":24,"24":24,"31":31}
    formats={" ":True,"B":True,"E":False}

    # Returns a PSW object containing the record's content
    @classmethod
    def decode(binary):
        ascii=binary.decode(EBCDIC)
        entry=ascii[7:15].rstrip()

        # Process format field
        format=ascii[5]
        try:
            mode=PSW.formats[format]
        except KeyError:
            raise OBJRecordError(msg="invalid PSW format at column 5: %s" \
                % format) from None

        # Process address mode field
        amode=ascii[9:11]
        try:
            am=PSW.amodes[amode]
        except KeyError:
            raise OBJRecordError(\
                msg="invalid PSW address mode at column 10: %s" % amode)

        # Process PSW hexadeciaml attributes
        attr=ascii[16:72]
        v=[]
        for beg,end in [(0,2),(3,4),(4,5),(6,8)]:
            value=attr[beg:end]
            if value in [" ","  "]:
                value=0
            else:
                try:
                    value=ind(value,16)
                except ValueError:
                    raise OBJRecordError(\
                        msg="invalid PSW attribute at column %s" \
                            % beg+17) from None
            v.append(value)

        return PSW(entry,bcmode=mode,am=am,im=v[0],key=v[1],mwp=v[2],pm=v[3])

    def __init__(self,entry,bcmode=False,am=24,im=0,key=0,mwp=0,pm=0):
        super().__init__("PSW")
        self.symbol=entry    # Entry symbol
        self.bdmode=bcmode   # Whether System/360 or System/370 BC-mode in use
        self.am=am           # Address mode
        self.im=im           # Interruption masks
        self.key=key         # Storage key
        self.mwp=mwp         # System mask
        self.pm=pm           # Program mask


# RGN record -- defines a region and its attributes
#  Python
#  Index   Columns    Description
#   [0]       1       An EBCDIC asterisk (X'5C')
#  [1:4]     2-4    * Record type: EBCDIC 'RGN' characters
#   [4]       5     * EBCDIC space character (X'40')
#  [5:14]    6-14     EBCDIC region name
#   [14]      15      EBCDIC space
# [15:23]   16-23     load address (EBCDIC hexadecimal load digits, left zero
#                     filled)
#   [23]      24      EBCDIC space
# [24:69]   25-69     Record data (45 bytes) - max 7 EBCDIC hex ESD-ID's and
#                     space
# [69:72]   70-72     EBCDIC spaces
# [72:80]   73-80   * Not used, reserved for optional deck ID or EBCDIC spaces
class RGN(OBJREC):
    ID=b'\x5C\xD9\xC7\xD5'

    # Returns an RGN object containing the record's content
    @classmethod
    def decode(binary):
        ascii=binary.decode(EBCDIC)
        region=ascii[5:14].strip()

        # Process load address
        addr=ascii[15:23]
        try:
            address=int(addr,16)
        except ValueError:
            raise OBJRecordError(\
                msg="invalid region load address at column 16: %s" % addr) \
                     from None

        esdids=ascii[24:69]
        ids=[]
        for ndx in range(0,len(esdids),5):
            esdid=esdids[ndx:ndx+5]
            if esdid == "     ":
                continue
            if esdid[4]!=" ":
                raise OBJRecordError(msg="invalid ESD-ID separator at %s: %s" \
                    % (ndx+4,esdid[4]))
            try:
                esdid=int(esdid[:4],16)
            except ValueError:
                raise OBJRecordError(msg="invalid ESD-ID separator at %s: %s" \
                    % (ndx+29,esdid[4]))
            esdids.append(esdid)

        return RGN(region,address,esdids=esdids)

    def __init__(self,name,load,esdids=[]):
        super().__init__("RGN")
        self.name=name
        self.load=load
        self.sections=esdids


# Initialize OBJREC class attribute of record types
# This can not be done until each subclass has been created during import
OBJREC.types={END.ID:END,ESD.ID:ESD,PSW.ID:PSW,RGN.ID:RGN,RLD.ID:RLD,TXT.ID:TXT}


#
#  +------------------------------+
#  |                              |
#  |   Raw Object Module Record   |
#  |                              |
#  +------------------------------+
#

class RAWREC(object):
    def __init__(self,byts,recnum=None):
        assert isinstance(byts,bytes),\
            "'byts' argument must be a sequence of bytes: %s" \
                % byts
        assert len(byts)==80,\
            "'byts' argument must be 80 bytes in length: %s" \
                % len(byts)

        # Raw object module record as a byte sequence
        self.byts=byts
        self.recnum=recnum    # The record number of this record in the file

        # This function converts the raw bytes into a string of ASCII
        # characters.  Recognized EBCDIC characters are converted to ASCII.
        # Unrecognized EBCDIC characters are converted to ASCII '.'.
        self.ascii=print_ebcdic(self.byts)

    # Return the ASCII printable version of the object module record.
    def __str__(self):
        return self.ascii


if __name__=="__main__":
   raise NotImplementedError("%s - is intended only for import" % this_module)
