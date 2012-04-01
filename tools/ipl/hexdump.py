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

# Utility useful for manipulating s390 binary data

import struct      # Access to Python binary manipulation module

# Note: this module requires Python 2.6 or greater

def dump(barray,start=0,mode=24,indent=""):
    if mode==31:
        format="%s%s%08X %s\n"
    else:
        if mode==64:
           format="%s%s%016X %s\n"
        else:
           format="%s%s%06X %s\n"
    str=""
    addr=start
    strlen=len(barray)
    strend=strlen-1
    for x in range(0,strlen,16):
    #print "x=%s" % x
        linestr=""
        for y in range(x,x+15,4):
            #print "y=%s" % y
            wordstr=""
            if y>strend:
                continue
            last=min(y+4,strlen)
            for z in range(y,last,1):
                #print "z=%s" % z
                wordstr="%s%02X" % (wordstr,ord(barray[z]))
            linestr="%s %s" % (linestr,wordstr)
        str=format % (str,indent,addr,linestr)
        addr+=16
    return str[:-1]

#
# These methods operate on individual big-endian fields.
# method  xxxxxx  converts a string to an unsigned numeric value
# method sxxxxxx  converts a string to a signed numeric value
# method  xxxxxxb converts an unsigned numeric value to a binary string
# method sxxxxxxb converts a signed numeric value to a binary string
# method  xxxxxxf formats for printing a numeric hex value (C-format)
# method  xxxxxxX foramts for printing a binary hex string
def addr24(address):
    if len(address)!=3:
        raise ValueError("24-bit address must be 3-bytes: %s" % len(address))
    addr="\x00%s" % address
    return struct.unpack(">L",addr)[0]
    
def addr24b(address):
    addr=struct.pack(">L",address)
    return addr[1:]
    
def addr24f(address):
    return "0x%06X" % (address&0xFFFFFF)
    
def addr24X(address):
    return "%06X" % (address&0xFFFFFF)
    
def addr31(address):
    if len(address)!=4:
        raise ValueError("31-bit address must be 4-bytes: %s" % len(address))
    return (struct.unpack(">L",address)[0])
    
def addr31b(address,bit0=0):
    mask=bit0<<31
    return struct.pack(">L",mask|(address&0x7FFFFFFF))
    
def addr31f(address,bit0=0):
    mask=bit0<<31
    return "0x%08X" % ((address|mask)&0xFFFFFFFF)
    
def addr31X(address,bit0=0):
    mask=bit0<<31
    return "%08X" % ((address|mask)&0xFFFFFFFF)
    
def byte(byte):
    if len(byte)!=1:
        raise ValueError("byte must be 1-byte: %s" % len(byte))
    return struct.unpack(">B",byte)[0]
    
def byteb(byte):
    return struct.pack(">B",byte)
    
def bytef(byte):
    return "0x%2X" % (byte&0xFF)
   
def byteX(byte):
    return "%02X" % (byte&0xFF)
    
def dblword(dword):
    if len(dword)!=8:
        raise ValueError("dblword must be 8-bytes: %s" % len(dword))
    return struct.unpack(">Q",dword)[0]
    
def dblwordb(dword):
    return struct.pack(">Q",dword)
    
def dblwordf(dword):
    return "0x%16X" % (dword&0xFFFFFFFFFFFFFFFF)
    
def dblwordX(dword):
    return "%016X" % (dword&0xFFFFFFFFFFFFFFFF)
    
def halfword(hword):
    if len(hword)!=2:
        raise ValueError("halfword must be 2-bytes: %s" % len(hword))
    return struct.unpack(">H",hword)[0]
    
def halfwordb(hword):
    return struct.pack(">H",hword)
    
def halfwordf(hword):
    return "0x%04X" % hword
    
def halfwordX(hword):
    return "%04X" % (hword&0xFFFF)

def fullword(fword):
    if len(fword)!=4:
        raise ValueError("fullword must be 4-bytes: %s" % len(fword))
    return struct.unpack(">L",fword)[0]
    
def fullwordb(fword):
    return struct.pack(">L",fword)
    
def fullwordf(fword):
    return "0x%08X" % fword
    
def fullwordX(fword):
    return "%08X" % (fword&0xFFFFFFFF)
    
def sbyte(byte):
    if len(byte)!=1:
        raise ValueError("byte must be 1-byte: %s" % len(byte))
    return struct.unpack(">b",byte)[0]
    
def sbyteb(byte):
    return struct.pack(">b",byte)
    
def sdblword(dword):
    if len(dword)!=8:
        raise ValueError("dblword must be 8-bytes: %s" % len(dword))
    return struct.unpack(">q",hword)[0]
    
def sdblwordb(dword):
    return struct.pack(">q",dword)
    
def sfullword(fword):
    if len(fword)!=4:
        raise ValueError("fullword must be 4-bytes: %s" % len(fword))
    return struct.unpack(">l",fword)[0]
    
def sfullwordb(fword):
    return struct.pack(">l",fword)
    
def shalfword(hword):
    if len(hword)!=2:
        raise ValueError("halfword must be 2-bytes: %s" % len(hword))
    return struct.unpack(">h",hword)[0]
    
def shalfwordb(hword):
    return struct.pack(">h",hword)
    
