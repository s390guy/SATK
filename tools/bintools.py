#!/usr/bin/python3
# Copyright (C) 2023 Harold Grovesteen
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

# Note: see SATK/tools/objlib.py for embedded version of these functions.

this_module="bintools.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2023")

# This module contains a collection of binary helper functions and or classes
# for manipulation of binary data and EBCDIC encoded characters.  These tasks
# repeatedly occur in SATK tools and this module reduces duplicated effort.
#
# Some tools may use this module, others may not.  Tools predating this
# module will not use it.  Later tools probably so.

# Python EBCDIC code page used for conversion to/from ASCII
# Change this value to use a different Python codepage to include more
# characters.
#
# Refer to this link for additional encoding options...
#    https://docs.python.org/3/library/codecs.html#standard-encodings
EBCDIC="cp037"


# ASCII to EBCDIC character encoding conversion
# Function Argument:
#   string   an ASCII character string.
# Returns:
#   a inmutable byte sequence of EBCDIC encoded characters
def A2E(string):
    assert isinstance(string,str),\
        "'string' argument must be a string: %s" % string

    return string.encode(EBCDIC)


# A sequence of big-endian bytes converted to an integer
# Function Arguments:
#   byts   a bytes or bytearray sequence
#   signed whether the bytes are to be considered signed (True) or unsigned
#          (False).  Defaults to unsigned or False.
# Returns:
#   an integer from the big-endian bytes
def B2I(byts,signed=False):
    assert isinstance(byts,(bytes,bytearray)),"'byts' must be a bytes "\
        "sequence: %s" % byts

    return int.from_bytes(byts,byteorder="big",signed=signed)


# Converts a bytes type sequence into printable hexadecimal digits
# Function arguments:
#   byts    A bytes or bytearray object to be made printable as hexadecimal
#           values.
#   sep     If True, each byte will be separated by period.  If False, bytes
#           are not separated
def B2X(byts,sep=False):
    assert isinstance(byts,(bytes,bytearray)),\
        "'byts' must be a bytes sequence %s" % byts

    if sep:
        sep_char="."
    else:
        sep_char=""
    string=""
    for b in byts:
        string="%s%s%02X" % (string,sep_char,b)
    if sep:
        return string[1:]
    else:
        return string


# EBCDIC to ASCII character encoding conversion
# Function Argument
#   byts   A bytes like list (bytes or bytearray objects) containing EBCDIC
#          encoded characters.
# Returns
#   an ASCII character string from the EBCDIC character encoded sequence
def E2A(byts):
    assert isinstance(byts,(bytes,bytearray)),\
        "'byts' argument must be a byte sequence: %s" % byts

    return byts.decode(EBCDIC)

# Converts an integer to a big endian byte sequence
# Function Arguments:
#   integer   The integer being converted.
#   length    The size of the byte sequence returned.  Defaults to 4
#   signed    Specify True if integer is treated as signed, False otherwise.
#             Defaults to False or unsigned.
def I2B(integer,length=4,signed=False):
    assert isinstance(integer,int),"'integer' must be an integer: %s" % integer
    assert isinstance(length,int),"'length' must be an integer: %s" % length

    return integer.to_bytes(length,byteorder="big",signed=signed)


# Converts hexadecimal characters into a binary bytes sequence.
# Function Arguments:
#   hex_chars    a string of hexadecimal characters.  The string must be
#                of even number of characters.
# Returns:
#   a bytes sequence of converted hexadecimal characters.
# Exceptions:
#   ValueError if hex_chars function argument contains any non-hexadecimal
#              digits.
def X2B(hex_chars):
    assert isinstance(hex_chars,str),"'hex_chars' must be a string: %s" %\
        hex_chars
    assert len(hex_chars) % 2 == 0,"'hex_chars' must be even number of "\
        "characters: %s" % hex_chars
    byt=[]
    for ndx in range(0,len(hex_chars)-1,2):
        b=hex_chars[ndx:ndx+2]
        try:
            byt.append(int(b,16))
        except ValueError:
            raise ValueError("'hex_chars' argument not hexadecimal: %s" %
                hex_chars)
    return bytes(byt)


# Function Arguments:
#   addr   an integer that is being formatted as a hexadecimal address
#   digits the number of digits being printed with zero fill on the left.
#          If addr exceeds the number of digits, the formatted address will
#          simply exceed the digits.
# Returns:
#   a displayable string.  It will be zero filled on the left to return the
#   number of requested digits.  If the value exceeds the number of digits
#   requested, the full value will be returned.
def print_address(addr,digits=6):
    assert isinstance(addr,int) and addr>=0,\
        "'addr' must be a non-negative integer: %s" % addr
    assert isinstance(digits,int) and digits >0 or digits <= 8,\
        "'int' must be an integer between 1 and 8: %s" % digits

    fmt_spec="0>%sX" % digits
    fmt_str="{0:%s}" % fmt_spec
    return fmt_str.format(addr)


# Rounds a value upward to the next rounding value if not already rounded
# Function Arguments:
#   value    the integer value being rounded upward
#   rounding the integer amount to which value is rounded
# Returns:
#   the rounded upward value
def round_up(value,rounding):
    assert isinstance(value,int),"'value' must be an integer: %s" % addr
    assert isinstance(rounding,int),"'rounding' must be an integer: %s" \
        % rounding

    return ( (value + (rounding-1)) // rounding ) * rounding


if __name__ == "__main__":
    raise NotImplementedError("%s is intended for import only" % this_module)
