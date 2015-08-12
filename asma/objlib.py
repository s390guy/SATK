#!/usr/bin/python3.3
# Copyright (C) 2015 Harold Grovesteen
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

# This module provides a set of classes for the manipulation of a mainframe object
# deck or load module content in a stand-alone environment.
#
# The stand-alone environment extends the traditional records with information
# specific to creating stand-alone loadable content.  These records would appear
# to legacy linkage editors as comments, but are recognized by the library when
# found.

this_module="%s.py" % __name__

#
#  +-----------------------+
#  |                       |
#  |   Utility Functions   |
#  |                       |
#  +-----------------------+
#

# Python EBCDIC code page used for conversion to/from ASCII
# Change this value to use a different Python codepage.
EBCDIC="cp037"

# Converts a list of three bytes into an unsigned integer
def addr(binary):
    assert isinstance(binary,bytes) and len(binary)==3,\
        "'binary' argument must be a bytes object of lenght two: %s" % binary
    return int.from_bytes(binary,byteorder="big")

# Converts a lit of two bytes into an signed or unsigned integer
def hword(binary,signed=False):
    assert isinstance(binary,bytes) and len(binary)==2,\
        "'binary' argument must be a bytes object of lenght two: %s" % binary
    return int.from_bytes(binary,byteorder="big",signed=signed)


#
#  +-----------------------------+
#  |                             |
#  |   Object Record Exception   |
#  |                             |
#  +-----------------------------+
#

class OBJRecordError(Exception):
    def __init__(self,msg=""):
        self.msg=msg          # Text associated with the error
        super().__init__(msg)


#
#  +-------------------------------------+
#  |                                     |
#  |   External Symbol Dictionary Item   |
#  |                                     |
#  +-------------------------------------+
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
    types=None
    amodes={64:0x20,31:0x02,24:0x01,True:0x03,None:0x00}
    amode_flags=[24,24,31,True]  # True implies any

    @staticmethod
    def decode(esdid,binary):
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__

        items=[]             # List of returned items

        # ESD item loop controls
        length=len(binary)   # Length of the ESD record data
        ndx=0                # Index of next ESD item in the record data
        # ESD-ID of the first item if the first item is not an LD 
        esdid=hword(binary[14:16]) 

        # Process the individual items in the ESD record data
        while ndx<length:
            if ndx+16>length:
                raise OBJRecordError(msg="Incomplete ESD item at column %s" % ndx+17)

            styp=binary[ndx+8]
            try:
                cls=ESDITEM.types[styp]
            except KeyError:
                raise OBJRecordError(msg="unrecognized ESD item type: 0x%02X" % etyp)

            item=cls.decode(esdid,binary[ndx:ndx+16])
            items.append(item)
            ndx+=16
            esdid+=1

        return items

    @staticmethod
    def decode_section_alignment(styp):
        if styp in [0x0D,0x0E,0x0F]:
            return 8
        return 4

    @staticmethod
    def decode_symbol(binary):
        return binary.decode(EBCDIC).rstrip()

    @staticmethod
    def decode_SDPC_flag(flag):
        if flag & 0x20:
            rmode=64
        else:
            if flag & 0x04:
                rmode=31
            else:
                rmode=24
        if flag & 0x01:
            amode=64
        else:
            amode=ESDITEM.amode_flags[amode & 0x03]
        rsect=flag & 0x08 == 0x08
        return (rmode,amode,rsect)

    def __init__(self,styp,esdid,ignore=False):
        self.styp=styp
        self.esdid=esdid
        self.ignore=ignore


# COMMON SECTION
class CM(ESDITEM):
    typ=0x05     # Fullword aligned common section
    qtyp=0x0F    # Quadword aligned common section

    # Returns the decoded CM item
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        length=addr(binary[13:16])
        align=ESDITEM.decode_section_alignment(binary[8])
        return CM(name,length=length,align=align)

    def __init__(self,esdid,symbol,length=0,align=4):
        if align==8:
            typ=CM.qtyp
        else:
            typ=CM.typ
        super().__init__(typ,esdid)
        self.symbol=symbol
        self.length=length
        self.align=align


# EXTERNAL REFERENCE
# Created by an EXTRN assember directive 
class ER(ESDITEM):
    typ=0x02

    # Returns the decoded LD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        return ER(name,esdid)

    def __init__(self,esdid,symbol):
        super().__init__(ER.typ,esdid)
        self.symbol=symbol


# LABEL DEFINITION
# Defined by an ENTRY assembler directive
class LD(ESDITEM):
    typ=0x01

    # Returns the decoded LD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        address=addr(binary[9:12])
        sd=addr(binary[13:16])
        return LD(esdid,name,address,sd)

    def __init__(self,esdid,symbol,addr,sd):
        self.symbol=symbol
        self.sd=sd
        self.address=addr
        super().__init__(LD.typ,esdid)


# PRIVATE CODE (UNNAMED CONTROL SECTION)
class PC(ESDITEM):
    typ=0x04     # Fullword aligned private code
    qtyp=0x0E    # Quadword aligned private code

    # Returns the decoded PC item
    @staticmethod
    def decode(esdid,binary):
        address=addr(binary[9:12])
        rmode,amode,rsect=ESDITEM.decode_SDPC_flag(binary[8])
        length=addr(binary[13:16])
        align=ESDITEM.decode_section_alignment(binary[8])
        return PC(esdid,addr,rmode=rmode,amode=amode,\
            rsect=rsect,length=length,align=align)

    def __init__(self,esdid,addr,rmode=24,amode=24,rsect=False,length=0,align=4):
        if align==8:
            typ=PC.qtyp
        else:
            typ=PC.typ
        super().__init__(typ,esdid)
        self.symbol=None
        self.address=addr
        self.rmode=rmode
        self.amode=amode
        self.rsect=rsect
        self.length=length
        self.align=align


# CONTROL SECTION DEFINITION
# Created by CSECT or RSECT assembler directive
class SD(ESDITEM):
    typ=0x00      # Fullword aligned control section
    qtyp=0x0D     # Quadword aligned control section

    # Returns the decoded SD item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        address=addr(binary[9:12])
        length=addr(binary[13:16])
        align=ESDITEM.decode_section_alignment(binary[8])
        rmode,amode,rsect=ESDITEM.decode_SDPC_flag(binary[12])
        return SD(esdid,name,address,amode=amode,\
            rmode=rmode,rsect=rsect,length=length)

    def __init__(self,esdid,symbol,address,amode=24,rmode=24,rsect=0,length=0,align=4):
        if align==8:
            typ=SD.qtyp
        else:
            typ=SD.typ
        super().__init__(typ,esdid)
        self.symbol=symbol
        self.amode=amode
        self.rmode=rmode
        self.rsect=rsect
        self.symbol=symbol
        self.align=align
        self.length=lengh


# WEAK EXTERNAL REFERENCE
class WX(ESDITEM):
    typ=0x0A

    # Returns the decoded WX item
    @staticmethod
    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        return WX(esdid,name)

    def __init__(self,esdid,symbol):
        super().__init__(WX.typ,esdid)
        self.symbol=symbol


# EXTERNAL DUMMY SECTION
class XD(ESDITEM):
    typ=0x06

    def decode(esdid,binary):
        name=ESDITEM.decode_symbol(binary[0:8])
        align=binary[12]
        length=addr(binary[13:16])
        return XD(esdid,name,align,length)

    def __init__(self,esdid,symbol,align,length):
        super().__init__(PR.typ,esdid)
        self.symbol=symbol
        self.align=align
        self.length=length


# Initialize ESDITEM class attribute of item types
# This can not be done until each subclass has been created during import
ESDITEM.types={CM.typ:CM,ER.typ:ER,LD.typ:LD,SD.typ:SD,XD.typ:XD,\
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
#  [1:4]     3,4      Position Pointer ESD-ID of field being relocated
#   [4]       5     * Flag byte
#  [5:8]     6-8    * Position address or offset assigned to the field being relocated
#
# * These fields are always present in each RLD item.  Others are controlled by
# * the flag byte

# This class reads or creates an object deck as a list of bytes.  The bytes are

class RLDITEM(object):

    # Decodes an RLD record's data into a list of RLDITEM objects
    @staticmethod
    def decode(binary):
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__

        items=[]             # List of returned items

        # RLD item loop controls
        length=len(binary)   # Length of the RLD record data
        ndx=0                # Index of next RLD item in the record data

        # Truncated RLD item controls for RLD items using previous item pointers
        same=0               # Whether this item uses this previous item's pointers
        prevr=None           # Previous R-pointer ESDID
        prevp=None           # Previous P-pointer ESDID

        # Process the individual items in the RLD record data
        while ndx<length:

            # Determine if this RLD item is full (8 bytes) or truncated (4 bytes)
            if same:
                if ndx+4>length:
                    raise OBJRecordError(msg="Incomplete RLD item at column %s" \
                        % ndx+17)
                common=binary[ndx:ndx+4]
                pptr=prevp
                rptr=prevr
                ndx+=4
            else:
                if ndx+8>length:
                    raise OBJRecordError(msg="Incomplete RLD item at column %s" \
                        % ndx+17)
                common=binar[ndx+4:ndx+8]
                prevr=rptr=hword(binary[0:2])
                prevp=rptr=hword(binary[2:4])
                ndx+=8

            # Common field processing for all RLD items
            address=addr(common[1:4])
            flag=common[0]
            if flag & 0x02:
                sign=-1
            else:
                sign=+1
            same=flag & 0x01
            relfld=flag & 0b01111100
            if relfd==0b011100:
                l=2
                atyp=4
            elif relfd==0b011110:
                l=4
                atyp=4
            else:
                if flag & 0x40 == 0x40:
                    linc=4
                else:
                    linc=0
                atyp=(flag & 0x30) >> 4
                l=linc + ((flag & 0xC0) >> 2) 

            rld=RLDITEM(rptr,pptr,address,atyp,length,sign)
            items.append(rld)

        # Return completed list of RLDITEM objects
        return items

    def __init__(self,r,p,a,atyp,length,sign):
        self.rptr=r        # ESDID of target address being relocated
        # Target address being relocated is located at the following position
        self.pptr=r        # Position ESDID of constant being relocated
        self.address=a     # Position Address of the constant being relocated
        # Type of address constant:
        #  0 -> A type
        #  1 -> V type
        #  2 -> Q type
        #  3 -> CXD type
        #  4 -> Relative immediate
        self.adcon=atyp    # Type of address constant
        self.length=length # Length of the position constant being relocated
        self.sign=sign     # Sign factor: +1 or -1


class OBJREC(object):
    types=None   # Dictionary of recognized object record types.  Initialized below.

    # Decode a bytes object of length 80 into a OBJREC subclass
    @staticmethod
    def decode(self,binary):
        assert isinstance(binary,bytes),\
            "'binary' argument must be a bytes object: %s" \
                % binary.__class__.__name__
        assert len(binary)==80,"bytes object must of length 80: %s" % len(binary)

        rtyp=binary[:4]
        try:
            cls=OBJREC.types[rtyp]
        except KeyError:
            raise OBJRecordError("unrecognized record type: %s" % rtyp)  
        obj=cls.decode(binary)
        return obj

    def __init__(self,typ,ignore=False):
        self.typ=typ
        self.ignore=ignore


# Format used by the END record:
#  Python
#  Index   Columns Type  Description
#   [0]       1         * X'02' constant data
#  [1:4]     2-4        * Record type: EBCDIC 'END' characters
#   [4]       5         * EBCDIC space character (X'40')
#  [5:8]     6-8      1   Optional entry address or EBCDIC spaces
#  [8:14]    9-14         EBCDIC space characters (X'40)
# [14:16]   15,16     1   ESD-ID of entry address if present, EBCDIC spaces otherwise
# [16:24]   17-24     2   Symbol name of entry point, otherwise EBCDIC spaces
# [24:28]   25-28         EBCDIC space characters (X'40')
# [28:32]   29-32     1   Length of SD ESD item without a length, byte 29 is X'00'
#   [32]     33           EBCDIC 1 (X'F1') or 2 (X'F2') of number of IDR entries
# [33:52]   34-52         IDR Record 1
# [52:71]   53-71         IDR Record 2
# [72:80]   73-80       * Not used, reserved for optional deck ID or EBCDIC spaces
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
# [49:52]    50-52    Day of processing year: 3 EBCDIC number

class IDR(object):

    @staticmethod
    def decode(binary):
        trans=binary[0:10]
        trans=trans.decode("cp027").rstrip()

        v=[]
        for beg,end in [(10,12),(12,14),(14,16),(16,19)]:
            ebcdic=binary[beg:end]
            ascii=ebcdic.decode("cp027")
            try:
                value=ind(ascii)
            except ValueError:
                value=None
            v.append(value)

        return IDR(trans=trans,ver=V[0],rel=V[1],yr=V[2],day=V[4])

    def __init__(self,trans=None,ver=None,rel=None,yr=None,day=None):
        self.trans=trans
        self.ver=ver
        self.rel=rel
        self.yr=yr
        self.day=day


class END(OBJREC):
    ID=b'\x02\xC5\xD4\xC4'
    IDR={0x40:0,0xF1:1,0xF2:2}

    @staticmethod
    def decode(binary):
        length=entsym=entsd=entaddr=None
        if binary[23]!=0x40:
            # Extract type 2 data
            entsym=ESDITEM.decode_symbol(binary[16:24])
        else:
            sd=hword(binary[14:16])
            addr=addr(binary[5:8])
            if addr!=0x404040:
                entaddr=addr
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

        if num:
            for n in range(num-1):
                ndx=n*19+33
                idrdata=binary[ndx:ndx+20]
                idr=IDR.decode(idrdata)
                idrs.append(idr)

        return END(sdlen=sdlen,entsd=entsd,entaddr=entaddr,entsym=entsym,idrs=idrs)

def __init__(self,sdlen=None,entsd=None,entaddr=None,entsym=None,idrs=[]):
        super().__init__("END")
        if entsd is not None:
            self.typ=2
        else:
            self.typ=1
        self.sdlen=sdlen     # Length of SD or PC ESD entry with a zero length 
        self.entsd=entsd     # Type 1 ESD-ID of entry address
        self.entaddr=entaddr # Type 1 Entry address
        self.entsym=entsym   # Type 2 symbolic entry point
        self.idrs=idrs       # Index 0 = source translator, 1 = source creator


# General record format used by ESD, TXT, RLD and SYM records of 80 bytes:
#  Python
#  Index   Columns    Description
#   [0]       1     * X'02' constant data
#  [1:4]     2-4    * Record type: EBCDIC 'ESD', 'TXT', 'RLD' or 'SYM' characters
#   [4]       5     * EBCDIC space character (X'40')
#  [5:8]     6-8      TXT only: 24-bit address.  ESD, RLD and SYM: EBCDIC spaces
#  [8:10]    9,10   C EBCDIC space characters (X'40')
# [10:12]   11,12   C Number of bytes of record data, unsigned big-endian binary
# [12:14]   13,14   C EBCDIC space characters (X'40')
# [14:16]   15,16     ESD, TXT: ESD-ID of first item or text.  RLD, SYM: EBCDIC spaces
# [16:72]   17-72   C Record data (56 bytes)
# [72:80]   73-80   * Not used, reserved for optional deck ID or EBCDIC spaces
#
# C indicates the field is common to all record types using the general format.
# * indicates the field is present in all records.
#

class ESD(OBJREC):
    ID=b'\x02\xC5\xE2\xC4'

    # Returns an RLD object containing the record's RLD items
    @classmethod
    def decode(binary):
        length=hword(binary[10:12])
        esdid=hword(binary[14:16]) 
        rlditems=binary[16:length+16]
        items=RLDITEM.decode(esdid,rlditems)
        return ESD(items=items)

    def __init__(self,items=[]):
        super().__init__("ESD")
        self.items=items      # List of ESDITEM objects from ESD.decode() method


class RLD(OBJREC):
    ID=b'\x02\xD9\xD3\xC4'

    # Returns an RLD object containing the record's RLD items
    @classmethod
    def decode(binary):
        length=hword(binary[10:12])
        rlditems=binary[16:length+16]
        items=RLDITEM.decode(rlditems)
        return RLD(items)

    def __init__(self,items):
        super().__init__("RLD")
        self.items=items      # List of RLDITEM objects


class SYM(OBJREC):
    ID=b'\x02\xE2\xE8\xD4'

    @classmethod
    def decode(binary):
        return SYM()

    def __init__(self):
        super().__init__("SYM",ignore=True)


class TXT(OBJREC):
    ID=b'\x02\xE3\xE7\xE3'

    # Returns an TXT object containing the record's content
    @classmethod
    def decode(binary):
        address=addr(binary[5:8])
        esdid=hword(binary[14:16])
        length=hword(binary[10:12])
        text=binary[16:length+16]
        return TXT(address,esdid,text)

    def __init__(self,addr,esdid,text):
        assert isinstance(text,bytes),\
           "'text' argument must be a bytes object: %s" % text
        assert len(text)>0 and len(text)<=56,\
           "'text' argument must be of length between 1 to 56: %s" % len(text)
        super().__init__("TXT")

        self.address=addr    # Address of TXT data
        self.esdid=esdid     # ESDID to which TXT data belongs
        self.text=text       # TXT record data


# PSW record -- defines the IPL PSW used for stant alone program
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
            raise OBJRecordError(msg="invalid PSW format at column 5: %s" % format) \
                from None

        # Process address mode field
        amode=ascii[9:11]
        try:
            am=PSW.amodes[amode] 
        except KeyError:
            raise OBJRecordError(msg="invalid PSW address mode at column 10: %s" \
                % amode)

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
                    raise OBJRecordError(msg="invalid PSW attribute at column %s" \
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
# [15:23]   16-23     load address (EBCDIC hexadecimal load digits, left zero filled)
#   [23]      24      EBCDIC space
# [24:69]   25-69     Record data (45 bytes) - max 7 EBCDIC hex ESD-ID's and space
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
            raise OBJRecordError(msg="invalid region load address at column 16: %s" 
                % addr) from None

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


# This class reads or creates an object deck as a list of bytes.  The bytes are
# either read from or written to a binary file by the user of the object.
#
# Static methods:
#   decode   Creates an OBJ object from a list of bytes lists of 80 elements.
#            Typically the list is derived from reading a binary file.
#
# Instance argument:
#   records  A list of OBJREC objects defining the object file.
class OBJ(object):

    @staticmethod
    def decode(blist):
        assert isinstance(blist,list),\
            "'blist' argument must be a list: %s" % blist.__class__.__name__

        recs=[]
        errors=0

        for n,rec in enumerate(blist):
            assert isinstance(rec,bytes),\
                "'blist' entry %s not a bytes list: %s" % rec.__class__.__name__

            try:
                record=OBJREC.decode(rec)
            except OBJRecordError as oe:
                print("OBJ error [%s] %s" % (n,oe.msg))
                errors+=1
            self.recs.append(record)

        if errors:
            raise OBJRecordError(msg="OBJ.decode() failed, errors: %s" % errors)

        return OBJ(records=recs)

    def __init__(self,records=[]):
        self.records=records   # List of OBJREC objects of the module


if __name__=="__main__":
   raise NotImplementedError("%s - is intended only for import" % this_module)
