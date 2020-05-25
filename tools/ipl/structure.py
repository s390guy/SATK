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

# This module manages big-endian data in field-based structures.  It provides
# conversions to/from big-endian data and EBCDIC/ASCII translations.  It accepts
# and returns structured data as bytes or bytearray sequences.
#
# The class structure is a super class for other classes that provide the conversion
# of structured data into a Python object or a Python class, the subclass, that
# constructs the structured data.
#
# Each subclass provides information to the structure through class attributes of
# the subclass.  This information includes:
#
#  - the length of the structured data in bytes, 'length' attribute
#  - the fields defined by the structured data, set to an attribute name
#  - If ID verification and setting is to be performed, the attributes ID and IDFLD
#    are set to the value of the ID and the name of the field definition where the
#    ID is stored as a string.

#The length class attribute must be set to the length in bytes of
# the supported structured data. 

# See file fbadscb.py for an example of how this module is used

this_module="sructure.py"

# Python imports: None
# SATK imports:
from hexdump import dump    # Get the dump function for hex display

# ASMA imports: None


#
#  +----------------------+
#  |                      |
#  |   Module Functions   |
#  |                      | 
#  +----------------------+
#


# This function will attempt to convert a bytes/bytearray sequence into a
# subclass of structure using identification checking to determine a match.
# Each potential structure must provide the class attributes required for
# identification validation and use the keyword argument 'bin'
#
# Function Arguments:
#   bin   a bytes/bytearray sequence of an unknown structure
#   cls   is a single class or list of classes that are subclasses of structure
#         that are potential candidates for conversion.
# Returns:
#   a structure object that has decoded the bytes sequence into its attributes
# Exception:
#   ValueError if sequence not a recognized data set control block record
def decode(bin,cls,debug=False):
    assert isinstance(bin,(bytes,bytearray)),\
        "%s.from_bytes() - 'bin' argument must be bytes/bytearray object: %s" \
            % (this_module,bin)
            
    # Ensure we are dealing with a list
    if not isinstance(cls,list):
        cl=[cls,]
    else:
        cl=cls

    # Check each class in the list and see if it recognizes the sequence
    string="%s - decode() -" % this_module
    length=len(bin)
    for n,obj in enumerate(cl):
        assert issubclass(obj,structure),\
           "%s 'cls' argument element %s not a structure object: %s" % (string,n,obj)
        if __debug__:
            if debug:
                print("%s checking if seq is a %s record" % (string,obj.__name__))

        length=len(bin)
        if obj.length != length:
            if __debug__:
                if debug:
                    print("%s seq length (%s) does not match %s length: %s" \
                        % (string,length,obj.__name__,obj.length))
            continue

        try:
            o=obj.from_bytes(bin)
            if __debug__:
                if debug:
                    print("%s recognized record: %s" % (string,o.__class__.__name__))
            return o
        except ValueError:
            if __debug__:
                if debug:
                    print("%s seq not a %s object" % (string,obj.__name__))

    raise ValueError("%s - 'bin' argument not a recognized structure" % string)



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


# Test a structure
# Function Argument:
#   obj    An instance of a super class of the structure class
def test(obj):
    assert isinstance(obj,structure),\
        "%s - test() - 'obj' argument not a structure object: %s" % (this_module,obj)

    obj.dump()
    print(obj)
    print()
    byts=obj.to_bytes()
    o=obj.__class__.from_bytes(byts)
    o.dump()
    print(o)
    print()


# Test a structure using identification verification
# Function Argument:
#   obj    An instance of a super class of the structure class
def test_rec(obj):
    assert isinstance(obj,structure),\
        "%s - test_rec() - 'obj' argument not a structure object: %s" \
            % (this_module,obj)

    obj.dump()
    print(obj)
    print()
    byts=obj.to_bytes()
    o=decode(byts,[obj.__class__,],debug=obj.debug)
    o.dump()
    print(o)
    print()


#
#  +---------------------------------------------+
#  |                                             |
#  |   Mainframe Field-Based Structure Manager   |
#  |                                             | 
#  +---------------------------------------------+
#

# This class manages field structured data at the bytes level and provides
# conversions between Python native objects and access to binary fields
#
# This class is the base class for a class managing a pre-defined structure.
# 
# Fields are identified by a tuple of three values:
#  tuple[0] - The first byte of the field
#  tuple[1] - The index of the byte following the field
#  tuple[2] - The length of the field (must equal tuple[1] - tuple [0])
#  tuple[3] - The type: 'C' characters, 'S' signed number, 'U' unsigned number
#
# Method arguments named 'fld' expect the tuple as described to be the argument's
# value.  The tuple is defined by the super class using this base class.
#
# The structure either accesses a supplied bytes/bytearray sequence or creates a
# new sequence of the specified length.  Each element of the sequence is initialized
# to binary zero, 0x00.
#
# Instance Arguments:
#   length    The length in bytes of the structure whose content is being managed.
#   bin       A byte/bytearry sequence being managed.  If provided, it must be of
#             the same length as specified by the 'length' argument.  If not specified
#             a new sequence is created with the number of bytes specified by the
#             'length' argument.
#   encoding  Specify the Python encoding/decoding codec for EBCDIC.  Defaults to
#             "cp037", for IBM English
#   debug     Specify True to enable field debugging checks
#
# Exceptions:
#   AssertionError if a check fails.
class structure(object):
    
    @classmethod
    def from_bytes(cls,bin):
        raise NotImplementedError(\
            "%s.from_bytes() - class %s must provide from_bytes() class method" \
                % (cls.__name__,cls.__name__))
    
    def __init__(self,bin=None,encoding="cp037",debug=False):
        self.debug=debug                 # Enable debugging checks
        self.encoding=encoding

        # Super class supplied information
        self.length=self.__class__.length  # Length of the binary structure
        self.flds=self.__class__.__dict__  # Field tuple definitions

        # Check for required class attribute
        if __debug__:
            if debug:
                try:
                    l=getattr(self.__class__,"length")
                except AttributeError:
                    raise ValueError(\
                        "%s subclass %s must provide class attribute: length" \
                            % (eloc(self,"__init__").self.__class__.__name__)) \
                                from None
                assert isinstance(l,int),\
                    "%s subclass %s must provide class attribute as an integer: %s" \
                        % (eloc(self,"__init__"),self.__class__.__name__,l)

        # Fetch conversion methods for each field type extracted
        self.extract_methods={\
            "B":self.to_python,
            "C":self.to_ascii,
            "S":self.to_signed,
            "U":self.to_unsigned}

        # Insert conversion methods for each field type inserted
        self.insert_methods={\
            "B":self.from_python,
            "C":self.from_ascii,
            "S":self.from_signed,
            "U":self.from_unsigned}

        if bin is None:
            self.bin=bytearray([0,]*self.length)
            return

        # An existing bytes/bytearray sequence has been provided
        b=bin
        if isinstance(bin,bytes):
            b=bytearray(bin)
        assert isinstance(b,bytearray),\
            "%s 'bin' argument must be bytes/bytearray sequence: %s" \
                % (eloc(self,"__init__",module=this_module),b)
        assert len(b) == self.length,\
            "%s 'bin' argument must be of length %s: %s" \
                % (eloc(self,"__init__",module=this_module),self.length,b)

        self.bin=b
        self._extract()  # Extract fields into instance attributes

    def __len__(self):
        return self.length

    # Performs checks on a field definition tuple.
    # Exception:
    #   AssertionError if the tuple has any detected errors.
    def _ck_field(self,fld,name=""):
        if name:
            fn=" field: %s" % name
        else:
            fn=""
        loc=eloc(self,"_ck_field")
        assert isinstance(fld,tuple),\
            "%s 'fld' argument must a tuple: %s%s" % (loc,fld,fn)
        assert len(fld) == 4,\
            "%s 'fld' argument must be of length three: %s%s" % (loc,len(fld),fn)
        beg,end,length,typ=fld
        assert isinstance(beg,int),\
            "%s fld[0] must be an integer: %s%s" % (loc,beg,fn)
        assert isinstance(end,int),\
            "%s fld[1] must be an integer: %s%s" % (loc,end,fn)
        assert isinstance(length,int),\
            "%s fld[2] must be an integer: %s%s" % (loc,length,fn)
        assert beg >= 0 and beg <= self.length,\
            "%s fld[0] out of range (0-%s): %s%s" % (loc,self.length,beg,fn)
        assert end >= 0 and end <= self.length,\
            "%s fld[0] out of range (0-%s): %s%s" % (loc,self.length,beg,fn)
        assert beg < end,\
            "%s fld[0] >= fld[1]: %s <> %s%s" % (loc,beg,end,fn)
        assert beg + length == end,\
            "%s fld[0] (%s) and fld[1] (%s) inconsitent with fld[3]: %s%s" \
                % (loc,beg,end,length,fn)
        assert typ in ["B","C","S","U"],\
            "%s fld[3] must be 'B', 'C', 'S', or 'U': '%s%s'" % (loc,typ,fn)

    # Check subclass has provided the class attributes for identification verification.
    def _ck_id_ver(self):
        try:
            getattr(self.__class__,"ID")
        except AttributeError:
            raise ValueError("%s subclass %s must provide class attribute ID "\
                "for ID verification"\
                    % (eloc(self,"_ck_id_ver"),self.__class__.__name__)) from None
        try:
            getattr(self.__class__,"IDFLD")
        except KeyError:
            raise ValueError("%s subclass %s must provide class attribute ID "\
                "for ID verification"\
                    % (eloc(self,"_ck_id_ver"),self.__class__.__name__)) from None

    def _extract(self):
        raise NotImplementedError("%s subclass %s must provide _extract() method" \
            % (eloc(self,"_extract"),self.__class__.__name__))

    # Validates that the extracted ID from a binary image matches the ID defined
    # by the class.
    # Exception:
    #   ValueError if the ID's do not match
    # Programming Note: the subclass that uses this methoc must provide the
    # class attributes ID and IDFLD.
    def ck_id(self):
        if __debug__:
            if self.debug:
                self._ck_id_ver()

        id=self.extract(self.__class__.IDFLD)
        if self.__class__.ID != id:
            raise ValueError("%s binary ID not '%s': '%s'" \
                % (eloc(self,"_extract",module=this_module),self.__class__.id,id))

    # Dump the structure in hex format with offset
    # Method Arguments:
    #   indent a string, usually spaces of the line indent of the dump
    #   string Specify True to return a string.  Specify False to cause the
    #          dump to be printed here.  Default False.
    def dump(self,indent="",string=False):
        s=dump(self.bin,indent=indent)
        if string:
            return s
        print(s)

    # Extract a field from the structure
    # Method Argument:
    #   fld   A name of a pre-defined field class attribute as a string or
    #         A four-element field definition tuple
    def extract(self,fld):
        beg,end,length,typ=self.field(fld)
        method=self.extract_methods[typ]
        byts=self.bin[beg:end]
        return method(byts)

    # Retrieves a number of bytes constituting a field from the instantitated
    # bytes/bytearray sequence.
    def fetch(self,beg,end):
        return self._fetch(beg,end)

    # Returns a field tuple definition
    def field(self,fld):
        fn=""
        if isinstance(fld,str):
            fn=fld
            #try:
            #    f=self.flds[fld]
            #except KeyError:
            #    pass
            #try:
            f=getattr(self.__class__,fld,None)
            #except AttributeError:
            #    pass
            if f is None or not isinstance(f,tuple):
                raise ValueError("%s undefined field tuple: %s"\
                    % (eloc(self,"field"),fld))
        elif isinstance(fld,tuple):
            assert len(fld) == 4,"%s 'fld' tuple must of be length 4: %s" \
                % (eloc(self,"field"),len(fld))
            f=fld
        else:
            raise ValueError("%s 'fld' argument must be a string or tuple: %s" \
                % (eloc(self,"field"),fld))

        if __debug__:
            if self.debug:
                self._ck_field(f,name=fn)
        return f

    # Create a bytes sequence filled with the specified value
    def fill(self,length,value):
        if isinstance(value,str):
            c=value[0]
            v=c.encode(encoding=self.encoding)
            v=v[0]
        elif isinstance(value,int):
            v=value
        else:
            raise ValueError("%s 'value' argument must be a string or integer: %s" \
                % (eloc(self,"fill"),value))

        byts=bytearray([v,]*length)
        assert len(byts) == length,"%s fill data length not requested (%s): %s" \
            % (eloc(self,"fill"),length,len(byts))
        return byts


    # Convert a Python ASCII string into an EBCDIC byte sequence
    # Method Arguments:
    #   length  Length of the EBCDIC character field being inserted into the structure
    #   value   A Python string being inserted into a structure's field
    def from_ascii(self,length,value):
        assert isinstance(value,str),\
            "%s 'value' argument must be a string: %s" \
                % (eloc(self,"insert_chars"),value)
        assert len(value) == length,\
        "%s field length (%s) does not match length of 'string' argument: %s" \
                % (eloc(self,"insert_chars"),length,len(value))
        return value.encode(self.encoding)

    # Leaves unconverted raw bytes
    def from_python(self,length,value):
        assert isinstance(value,(bytes,bytearray)),\
            "%s 'value' argument must be a bytes/bytearray sequence: %s" \
                % (eloc(self,"from_python"),value)
        assert len(value) == length,\
        "%s field length (%s) does not match length of 'value' argument: %s" \
                % (eloc(self,"from_python"),length,len(value))
        return value

    # Convert a Python integer into a big-endian signed binary value
    # Method Arguments:
    #   length  Length of the signed numeric field
    #   value   The Python numeric integer being inserted into the field
    def from_signed(self,length,value):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer: %s" \
                % (eloc(self,"insert_number"),value)
        assert value>=0,"%s unsigned 'value' argument must not be negative: %s" \
            % (eloc(self,"insert_number"),value)

        return value.to_bytes(length,byteorder="big",signed=True)

    # Convert a Python integer into a big-endian unsigned binary value
    # Method Arguments:
    #   length  Length of the signed numeric field
    #   value   The Python numeric integer being inserted into the field
    def from_unsigned(self,length,value):
        assert isinstance(value,int),\
            "%s 'value' argument must be an integer: %s" \
                % (eloc(self,"insert_number"),value)

        return value.to_bytes(length,byteorder="big",signed=False)

    # Retrieves a number of bytes constituting a field from the instantitated
    # bytes/bytearray sequence.
    #def fetch(self,beg,end):
    #    return self._fetch(beg,end)

    # Returns a field tuple definition
    #def field(self,fld):
    #    fn=""
    #    if isinstance(fld,str):
    #        f=None
    #        fn=fld
    #        try:
    #            f=self.flds[fld]
    #        except KeyError:
    #            pass
    #        if f is None or not isinstance(f,tuple):
    #            raise ValueError("%s undefined field tuple: %s"\
    #                % (eloc(self,"field"),fld))
    #    elif isinstance(fld,tuple):
    #        assert len(fld) == 4,"%s 'fld' tuple must of be length 4: %s" \
    #            % (eloc(self,"field"),len(fld))
    #        f=fld
    #    else:
    #        raise ValueError("%s 'fld' argument must be a string or tuple: %s" \
    #            % (eloc(self,"field"),fld))

    #    if __debug__:
    #        if self.debug:
    #            self._ck_field(f,name=fn)
    #    return f

    # Create a bytes sequence filled with the specified value
    #def fill(self,length,value):
    #    if isinstance(value,str):
    #        c=value[0]
    #        v=c.encode(encoding=self.encoding)
    #        v=v[0]
    #    elif isinstance(value,int):
    #        v=value
    #    else:
    #        raise ValueError("%s 'value' argument must be a string or integer: %s" \
    #            % (eloc(self,"fill"),value))

    #    byts=bytearray([v,]*length)
    #    assert len(byts) == length,"%s fill data length not requested (%s): %s" \
    #        % (eloc(self,"fill"),length,len(byts))
    #    return byts

    # Insert into a structure field its byte content
    # Method Arguments:
    #   fld    A field definition tuple
    #   byts   The bytes being inserted into the field
    #   fill   Specify whether value is to fill each byte (True) or the field (False).
    #          fill=True overrides the field's normal data type.
    def insert(self,fld,value,fill=False):
        beg,end,length,typ=self.field(fld)
        if fill:
            byts=self.fill(length,value)
        else:
            method=self.insert_methods[typ]
            byts=method(length,value)
        assert len(byts) == length,\
            "%s field length (%s) does not match length of 'byts' argument" \
                % (eloc(self,"insert"),length,len(byts))

        self.bin[beg:end]=byts
        if __debug__:
            if self.debug:
                assert len(self.bin) == self.length,\
                    "%s structure length (%s) does not match bytearray sequence "\
                        "length (%s) after field insertion: %s"\
                            % (eloc(self,"to_bytes"),self.length,len(self.bin),fld)

    # Inserts the required ID into its fld
    # Method Argument:
    #   fld    A field definition tuple
    # Programming Note: the subclass that uses this method must provide the
    # class attributes ID and IDFLD.
    def insert_id(self):
        if __debug__:
            if self.debug:
                self._ck_id_ver()

        self.insert(self.__class__.IDFLD,self.__class__.ID)

    # This method left justifies and pads a string for a field.  If None is supplied
    # a string of all spaces is supplied.
    # Method Argumemnts:
    #   fld    A field definition tuple 
    #   string A string to be made to fit within the field
    def pad(self,fld,string):
        beg,end,length,typ=self.field(fld)
        if string is None:
            return " ".ljust(length)
        return string.ljust(length)

    # Converts an EBCDIC character sequence field into a Python ASCII string
    # Method Argument:
    #   byts    The EBCDIC field's byte sequence
    # Returns
    #   an ASCII string sequence of the same length
    def to_ascii(self,byts):
        return byts.decode(encoding=self.encoding)

    # Return the structures bytearray sequence
    def to_bytes(self):
        # Note: insertions can change the length so make sure that has not 
        # happened.
        assert len(self.bin) == self.length,\
            "%s structure length (%s) does not match bytearray sequence length: %s"\
                % (eloc(self,"to_bytes")) 
        return self.bin

    # Leaves unconverted raw binary bytes from a structure
    def to_python(self,byts):
        return byts

    # Converts a signed big endian numeric field to a Python integer
    # Method Arguments:
    #   byts    The big endian field's byte sequence
    # Returns:
    #   a Python integer
    def to_signed(self,byts):
        return int.from_bytes(byts,byteorder="big",signed=True)

    # Converts an unsigned big endian numeric field into a Python integer
    # Method Arguments:
    #   byts    The big endian field's byte sequence
    # Returns:
    #   a Python integer
    def to_unsigned(self,byts):
       return int.from_bytes(byts,byteorder="big",signed=False)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
