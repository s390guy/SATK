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

# Utility useful for manipulating s390 binary data.
#
# Python handling of binary data has changed between version 2 and 3.  Version
# 2 handled binary data as strings with the struct module.  Version 3, starting 
# with 3.2, handled binary data as bytes, but the struct module was not available 
# until 3.3.  The SATK tools depend heavily upon the struct module, having been
# originally developed under Python version 2.  To support Python 2 code
# compatibly with both Python run time version 2.6+ (under version 2) and 3.3+ 
# (under version 3), the binary conversion functions have been turned into wrapper
# functions that now access an instance of bstruct.  The instance of bstruct is 
# built sensitive to the Python run-time in use and the two different versions of
# the struct module.
#
# Python-based tools using hexdump should see no change between Python 2.x and 3.3+.
#
# Modules that utilize binary string data in version 2 will have to use byte data.
# Both v2 strings and v3 bytes are immutable so operate similarly.  The difference
# between the two Python versions appear where ord() is used to convert a string of
# length one into its numeric value.  The ord() will not work with a byte, the byte
# already being a Python integer.  Tools using ord() for this purpose will require 
# modification to work with a byte list.  PyELF is an example where such changes
# were made.

# Python imports
import struct      # Access to Python binary manipulation module
import sys         # Access to the hexversion attribute

class bstruct(object):
    @staticmethod
    def init():
        ver=sys.hexversion
        if ver >= 0x03030000:
            return bstruct3()
        if ver <  0x03000000:
            return bstruct2()
        error="binary data handling not supported by this version of Python: %08X"
        raise NotImplementedError(error % ver)
    def __init__(self):
        name=self.__class__.__name__
        self.ver=name[7:]
    def __str__(self):
        return "%s()" % self.__class__.__name__
    def _check1(self,byte):
        if len(byte)!=1:
            raise ValueError("byte must be 1-byte: %s" % len(byte))
    def _checkaddr(self,address,bits,n):
        if len(address)!=n:
            raise ValueError("%s-bit address must be %s-bytes: %s" \
                % (bits,n,len(address)))
    def _checkn(self,lst,n,name):
        if len(lst)!=n:
            raise ValueError("%s must be %s-bytes: %s" % (name,n,len(lst)))
    # Generic struct methods
    def calcsize(self,fmt):
        raise NotImplementedError("subclass %s must provide method calcsize()" \
            % (self.__class__.___name__))
    def pack(self,*args):
        raise NotImplementedError("subclass %s must provide method pack()" \
            % (self.__class__.___name__))
    def unpack(self,fmt,buf):
        raise NotImplementedError("subclass %s must provide method unpack()" \
            % (self.__class__.___name__))
    # s390 Binary Data Methods
    def addr24(self,address):
        raise NotImplementedError("subclass %s must provide method add24()" \
            % (self.__class__.___name__))
    def addr24b(self,address):
        raise NotImplementedError("subclass %s must provide method add24b()" \
            % (self.__class__.___name__))
    def addr31(self,address):
        raise NotImplementedError("subclass %s must provide method addr31()" \
            % (self.__class__.___name__))
    def addr31b(self,address,bit0=0):
        raise NotImplementedError("subclass %s must provide method addr31b()" \
            % (self.__class__.___name__))
    def byte(self,byte):
        raise NotImplementedError("subclass %s must provide method byte()" \
            % (self.__class__.___name__))
    def byteb(self,byte):
        raise NotImplementedError("subclass %s must provide method byteb()" \
            % (self.__class__.___name__))
    def dblword(self,dword):
        raise NotImplementedError("subclass %s must provide method dblword()" \
            % (self.__class__.___name__))
    def dblwordb(self,dword):
        raise NotImplementedError("subclass %s must provide method dblwordb()" \
            % (self.__class__.___name__))
    def halfword(self,hword):
        raise NotImplementedError("subclass %s must provide method halfword()" \
            % (self.__class__.___name__))
    def halfwordb(self,hword):
        raise NotImplementedError("subclass %s must provide method halfwordb()" \
            % (self.__class__.___name__))
    def fullword(self,fword):
        raise NotImplementedError("subclass %s must provide method fullword()" \
            % (self.__class__.___name__))
    def fullwordb(fword):
        raise NotImplementedError("subclass %s must provide method fullwordb()" \
            % (self.__class__.___name__))
    def sbyte(self,byte):
        raise NotImplementedError("subclass %s must provide method sbyte()" \
            % (self.__class__.___name__))
    def sbyteb(self,byte):
        raise NotImplementedError("subclass %s must provide method sbyteb()" \
            % (self.__class__.___name__))
    def sdblword(self,dword):
        raise NotImplementedError("subclass %s must provide method sdblword()" \
            % (self.__class__.___name__))
    def sdblwordb(self,dword):
        raise NotImplementedError("subclass %s must provide method sdblwordb()" \
            % (self.__class__.___name__))
    def sfullword(self,fword):
        raise NotImplementedError("subclass %s must provide method sfullword()" \
            % (self.__class__.___name__))
    def sfullwordb(self,fword):
        raise NotImplementedError("subclass %s must provide method sfullwordb()" \
            % (self.__class__.___name__))
    def shalfword(self,hword):
        raise NotImplementedError("subclass %s must provide method shalfword()" \
            % (self.__class__.___name__))
    def shalfwordb(self,hword):
        raise NotImplementedError("subclass %s must provide method shalfwordb()" \
            % (self.__class__.___name__))
        
class bstruct2(bstruct):
    def __init__(self):
        bstruct.__init__(self)
        self.ver=2
    def calcsize(self,fmt):
        return struct.calcsize(fmt)
    def pack(self,*args):
        struct.pack(args)
    def unpack(self,fmt,buf):
        return struct.unpack(fmt,buf)
    def addr24(self,address):
        self._checkaddr(address,24,3)
        #if len(address)!=3:
        #    raise ValueError("24-bit address must be 3-bytes: %s" % len(address))
        addr="\x00%s" % address
        return struct.unpack(">L",addr)[0]
    def addr24b(self,address):
        addr=struct.pack(">L",address)
        return addr[1:]
    def addr31(self,address):
        self._checkaddr(address,31,4)
        #if len(address)!=4:
        #    raise ValueError("31-bit address must be 4-bytes: %s" % len(address))
        return (struct.unpack(">L",address)[0])
    def addr31b(self,address,bit0=0):
        mask=bit0<<31
        return struct.pack(">L",mask|(address&0x7FFFFFFF))
    def byte(self,byte):
        self._check1(byte)
        #if len(byte)!=1:
        #    raise ValueError("byte must be 1-byte: %s" % len(byte))
        return struct.unpack(">B",byte)[0]
    def byteb(self,byte):
        return struct.pack(">B",byte)
    def dblword(self,dword):
        self._checkn(dword,8,"dblword")
        #if len(dword)!=8:
        #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
        return struct.unpack(">Q",dword)[0]
    def dblwordb(self,dword):
        return struct.pack(">Q",dword)
    def halfword(self,hword):
        self._checkn(hword,2,"halfword")
        #if len(hword)!=2:
        #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
        return struct.unpack(">H",hword)[0]
    def halfwordb(self,hword):
        return struct.pack(">H",hword)
    def fullword(self,fword):
        self._checkn(fword,4,"fullword")
        #if len(fword)!=4:
        #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
        return struct.unpack(">L",fword)[0]
    def fullwordb(self,fword):
        return struct.pack(">L",fword)
    def sbyte(self,byte):
        self._check1(byte)
        #if len(byte)!=1:
        #    raise ValueError("byte must be 1-byte: %s" % len(byte))
        return struct.unpack(">b",byte)[0]
    def sbyteb(self,byte):
        return struct.pack(">b",byte)
    def sdblword(self,dword):
        self._checkn(dword,8,"dblword")
        #if len(dword)!=8:
        #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
        return struct.unpack(">q",dword)[0]
    def sdblwordb(self,dword):
        return struct.pack(">q",dword)
    def sfullword(self,fword):
        self._checkn(fword,4,"fullword")
        #if len(fword)!=4:
        #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
        return struct.unpack(">l",fword)[0]
    def sfullwordb(self,fword):
        return struct.pack(">l",fword)
    def shalfword(self,hword):
        self._checkn(hword,2,"halfword")
        #if len(hword)!=2:
        #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
        return struct.unpack(">h",hword)[0]
    def shalfwordb(self,hword):
        return struct.pack(">h",hword)

class bstruct3(bstruct):
    def __init__(self):
        super().__init__()
        self.ver=3
        self.SByte=struct.Struct(">b")
        self.SHalfWord=struct.Struct(">h")
        self.SFullWord=struct.Struct(">l")
        self.SDoubleWord=struct.Struct(">q")
        self.UByte=struct.Struct(">B")
        self.UHalfWord=struct.Struct(">H")
        self.UFullWord=struct.Struct(">L")
        self.UDoubleWord=struct.Struct(">Q")
    def _ckint(self,i):
        if isinstance(i,int):
            return
        icls=i.__class__.__name__
        raise ValueError("argument must be an int: found of class %s: %s" \
            % (icls,i))
    def calcsize(self,fmt):
        return struct.calcsize(fmt)
    def pack(self,*a):
        #a=args
        if  len(a) == 0:
            raise ValueError("format and values missing")
        elif len(a) == 1:
            raise ValueError("values missing")
        elif len(a) == 2:
            return struct.pack(a[0],a[1])
        elif len(a) == 3:
            return struct.pack(a[0],a[1],a[2])
        elif len(a) == 4:
            return struct.pack(a[0],a[1],a[2],a[3])
        elif len(a) == 5:
            return struct.pack(a[0],a[1],a[2],a[3],a[4])
        elif len(a) == 6:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5])
        elif len(a) == 7:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6])
        elif len(a) == 8:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7])
        elif len(a) == 9:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8])
        elif len(a) == 10:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9])
        elif len(a) == 11:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],\
                a[10])
        elif len(a) == 12:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],\
                a[10],a[11])
        elif len(a) == 13:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],\
                a[10],a[11],a[12])
        elif len(a) == 14:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],\
                a[10],a[11],a[12],a[13])
        elif len(a) == 15:
            return struct.pack(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],\
                a[10],a[11],a[12],a[13],a[14])
        else:
            raise ValueError("too many integers, max is 14: %s" % len(a)-1)
        #return struct.pack(fmt,args)
    def unpack(self,fmt,buf):
        return struct.unpack(fmt,buf)
    def addr24(self,address):
        self._checkaddr(address,24,3)
        #if len(address)!=3:
        #    raise ValueError("24-bit address must be 3-bytes: %s" % len(address))
        addr=b'\x00' + address
        return self.UFullWord.unpack(addr)[0]
        #return struct.unpack(">L",addr)[0]
    def addr24b(self,address):
        addr=self.UFullWord.pack(address)
        #addr=struct.pack(">L",address)
        return addr[1:]
    def addr31(self,address):
        self._checkaddr(address,31,4)
        #if len(address)!=4:
        #    raise ValueError("31-bit address must be 4-bytes: %s" % len(address))
        return self.UFullWord.unpack(address)[0]
        #return (struct.unpack(">L",address)[0])
    def addr31b(self,address,bit0=0):
        mask=bit0<<31
        return self.UFullWord.pack(mask|(address&0x7FFFFFFF))
        #return struct.pack(">L",mask|(address&0x7FFFFFFF))
    def byte(self,byte):
        self._check1(byte)
        #if len(byte)!=1:
        #    raise ValueError("byte must be 1-byte: %s" % len(byte))
        return self.UByte.unpack(byte)[0]
        #return struct.unpack(">B",byte)[0]
    def byteb(self,byte):
        return self.UByte.pack(byte)
        #return struct.pack(">B",byte)
    def dblword(self,dword):
        self._checkn(dword,8,"dblword")
        #if len(dword)!=8:
        #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
        return self.UDoubleWord.unpack(dword)[0]
        #return struct.unpack(">Q",dword)[0]
    def dblwordb(self,dword):
        return self.UDoubleWord.pack(dword)
        #return struct.pack(">Q",dword)
    def halfword(self,hword):
        self._checkn(hword,2,"halfword")
        #if len(hword)!=2:
        #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
        return self.UHalfWord.unpack(hword)[0]
    def halfwordb(self,hword):
        self._ckint(hword)
        return self.UHalfWord.pack(hword)
        #return struct.pack(">H",hword)
    def fullword(self,fword):
        self._checkn(fword,4,"fullword")
        #if len(fword)!=4:
        #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
        return self.UFullWord.unpack(fword)[0]
        #return struct.unpack(">L",fword)[0]
    def fullwordb(self,fword):
        return self.UFullWord.pack(fword)
        #return struct.pack(">L",fword)
    def sbyte(self,byte):
        self._check1(byte)
        #if len(byte)!=1:
        #    raise ValueError("byte must be 1-byte: %s" % len(byte))
        return self.SByte.unpack(byte)[0]
        #return struct.unpack(">b",byte)[0]
    def sbyteb(self,byte):
        return self.SByte.pack(byte)
        #return struct.pack(">b",byte)
    def sdblword(self,dword):
        self._checkn(dword,8,"dblword")
        #if len(dword)!=8:
        #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
        return self.SDoubleWord.unpack(dword)[0]
        #return struct.unpack(">q",hword)[0]
    def sdblwordb(self,dword):
        return self.SDoubleWord.pack(dword)
        #return struct.pack(">q",dword)
    def sfullword(self,fword):
        self._checkn(fword,4,"fullword")
        #if len(fword)!=4:
        #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
        return self.SFullWord.unpack(fword)[0]
        #return struct.unpack(">l",fword)[0]
    def sfullwordb(self,fword):
        return self.SFullWord.pack(fword)
        #return self.pack(">l",fword)
    def shalfword(self,hword):
        self._checkn(hword,2,"halfword")
        #if len(hword)!=2:
        #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
        return self.SHalfWord.unpack(hword)[0]
        #out=self.unpack(">h",hword)
        #return out[0]
    def shalfwordb(self,hword):
        return self.SHalfWord.pack(hword)
        #bin=self.pack(">h",hword)
        #return bin
        
bstructx=bstruct.init()

def dump(barray,start=0,mode=24,indent=""):
    isstring=isinstance(barray,type(""))
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
                if isstring: 
                    wordstr="%s%02X" % (wordstr,ord(barray[z]))
                else:
                    wordstr="%s%02X" % (wordstr,barray[z])
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
# method  xxxxxxf formats for printing a numeric hex value (C-format: '0xHHHH')
# method  xxxxxxX formats for printing a binary hex string ('HHHH')
def addr24(address):
    return bstructx.addr24(address)
    #if len(address)!=3:
    #    raise ValueError("24-bit address must be 3-bytes: %s" % len(address))
    #addr="\x00%s" % address
    #return struct.unpack(">L",addr)[0]
    
def addr24b(address):
    return bstructx.addr24b(address)
    #addr=struct.pack(">L",address)
    #return addr[1:]
    
def addr24f(address):
    return "0x%06X" % (address&0xFFFFFF)
    
def addr24X(address):
    return "%06X" % (address&0xFFFFFF)
    
def addr31(address):
    return bstructx.addr31(address)
    #if len(address)!=4:
    #    raise ValueError("31-bit address must be 4-bytes: %s" % len(address))
    #return (struct.unpack(">L",address)[0])
    
def addr31b(address,bit0=0):
    return bstructx.addr31b(address,bit0=bit0)
    #mask=bit0<<31
    #return struct.pack(">L",mask|(address&0x7FFFFFFF))
    
def addr31f(address,bit0=0):
    if bit0:
        mask=0xFFFFFFFF
    else:
        mask=0x7FFFFFFF
    return "0x%08X" % (address & mask)
    
def addr31X(address,bit0=0):
    if bit0:
        mask=0xFFFFFFFF
    else:
        mask=0x7FFFFFFF
    return "%08X" % (address & mask)
    
def byte(byte):
    return bstructx.byte(byte)
    #if len(byte)!=1:
    #    raise ValueError("byte must be 1-byte: %s" % len(byte))
    #return struct.unpack(">B",byte)[0]
    
def byteb(byte):
    return bstructx.byteb(byte)
    #return struct.pack(">B",byte)
    
def bytef(byte):
    return "0x" + byteX(byte)
   
def byteX(byte):
    return "%02X" % (byte&0xFF)
    
def dblword(dword):
    return bstructx.dblword(dword)
    #if len(dword)!=8:
    #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
    #return struct.unpack(">Q",dword)[0]
    
def dblwordb(dword):
    return bstructx.dblwordb(dword)
    #return struct.pack(">Q",dword)
    
def dblwordf(dword):
    return "0x" + dblwordX(dword)
    
def dblwordX(dword):
    return "%016X" % (dword&0xFFFFFFFFFFFFFFFF)
    
def halfword(hword):
    return bstructx.halfword(hword)
    #if len(hword)!=2:
    #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
    #return struct.unpack(">H",hword)[0]
    
def halfwordb(hword):
    return bstructx.halfwordb(hword)
    #return struct.pack(">H",hword)
    
def halfwordf(hword):
    return "0x" +  halfwordX(hword)
    #return "0x%04X" % hword
    
def halfwordX(hword):
    return "%04X" % (hword&0xFFFF)

def fullword(fword):
    return bstructx.fullword(fword)
    #if len(fword)!=4:
    #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
    #return struct.unpack(">L",fword)[0]
    
def fullwordb(fword):
    return bstructx.fullwordb(fword)
    #return struct.pack(">L",fword)
    
def fullwordf(fword):
    return "0x" + fullwordX(fword)
    #return "0x%08X" % fword
    
def fullwordX(fword):
    return "%08X" % (fword&0xFFFFFFFF)
    
def sbyte(byte):
    return bstructx.sbyte(byte)
    #if len(byte)!=1:
    #    raise ValueError("byte must be 1-byte: %s" % len(byte))
    #return struct.unpack(">b",byte)[0]
    
def sbyteb(byte):
    return bstructx. sbyteb(byte)
    #return struct.pack(">b",byte)
    
def sdblword(dword):
    return bstructx.sdblword(dword)
    #if len(dword)!=8:
    #    raise ValueError("dblword must be 8-bytes: %s" % len(dword))
    #return struct.unpack(">q",hword)[0]
    
def sdblwordb(dword):
    return bstructx.sdblwordb(dword)
    #return struct.pack(">q",dword)
    
def sfullword(fword):
    return bstructx.sfullword(fword)
    #if len(fword)!=4:
    #    raise ValueError("fullword must be 4-bytes: %s" % len(fword))
    #return struct.unpack(">l",fword)[0]
    
def sfullwordb(fword):
    return bstructx.sfullwordb(fword)
    #return struct.pack(">l",fword)
    
def shalfword(hword):
    return bstructx.shalfword(hword)
    #if len(hword)!=2:
    #    raise ValueError("halfword must be 2-bytes: %s" % len(hword))
    #return struct.unpack(">h",hword)[0]
    
def shalfwordb(hword):
    #return struct.pack(">h",hword)
    return bstructx.shalfwordb(hword)

if __name__ == "__main__":
    raise NotImplementedError("hexdump.py - must only be imported")
    # Comment the preceding statement to run the test below.
    
    class testhex(object):
        def __init__(self):
            print("bstructx=%s" % bstructx)
            self.ver=bstructx.ver
            if self.ver == 2:
                self.ltest=10*"\x00"
            else:
                self.ltest=10*b"\x00"
            #           [s]xxxxxb   [s]xxxxx  xxxxxf    xxxxxF
            self.test1=[(sbyteb,    sbyte,    bytef,    byteX,    -10,"sbyte"),
                        (shalfwordb,shalfword,halfwordf,halfwordX,-10,"shalf"),
                        (sfullwordb,sfullword,fullwordf,fullwordX,-10,"sfull"),
                        (sdblwordb, sdblword, dblwordf, dblwordX, -10,"sdbl"),
                        (byteb,     byte,     bytef,    byteX,     10,"ubyte"),
                        (halfwordb, halfword, halfwordf,halfwordX, 10,"uhalf"),
                        (fullwordb, fullword, fullwordf,fullwordX, 10,"ufull"),
                        (dblwordb,  dblword,  dblwordf, dblwordX,  10,"udbl"),
                        (addr24b,   addr24,   addr24f,  addr24X,   10,"addr24")]
            self.tst31=[(addr31b,   addr31,   addr31f,  addr31X,   10,0,"addr31-0"),
                        (addr31b,   addr31,   addr31f,  addr31X,   10,1,"addr31-1")]
            self.length=[(sbyte,    "sbyte"),
                         (shalfword,"shalf"),
                         (sfullword,"sfull"),
                         (sdblword, "sdbl"),
                         (byte,     "ubyte"),
                         (halfword, "uhalf"),
                         (fullword, "ufull"),
                         (dblword,  "udbl"),
                         (addr24,   "addr24"),
                         (addr31,   "addr31-0"),
                         (addr31,   "addr31-1")]
        def run(self):
            for x in self.test1:
                self.test(x[0],x[1],x[2],x[3],x[4],x[5])
            for x in self.tst31:
                self.test31(x[0],x[1],x[2],x[3],x[4],x[5],x[6])
            for x in self.length:
                self.testl(x[0],x[1])
        def test(self,mb,mi,mpc,mp,value,desc):
            print("\nTest: %s" % desc)
            print("input: %s" % value)
            bin=mb(value)
            print("binary:\n%s" % dump(bin))
            num=mi(bin)
            print("output: %s" % num)
            print("C-hex: %s" % mpc(num))
            print("HEX: %s" % mp(num))
            if num!=value:
                print("ERROR: input and output do not match: %s!=%s" % (value,num))
                
        def test31(self,mb,mi,mpc,mp,value,bit31,desc):
            print("\nTest: %s" % desc)
            print("input: %s" % value)
            bin=mb(value,bit31)
            print("binary:\n%s" % dump(bin))
            num=mi(bin)
            print("output: %s" % num)
            print("C-hex: %s" % mpc(num,bit31))
            print("HEX: %s" % mp(num,bit31))
            if num!=value:
                print("ERROR: input and output do not match: %s!=%s" % (value,num))
        def testl(self,mi,desc):
            print("\nTest: %s" % desc)
            for x in range(1,len(self.ltest)):
                t=self.ltest[:x]
                try:
                    i=mi(t)
                    print("succeeded length: %s" % len(t))
                except ValueError:
                    typ,exp,tb=sys.exc_info()
                    print("FAILED    length: %s - %s" % (len(t),exp))
    
    test=testhex()
    test.run()
