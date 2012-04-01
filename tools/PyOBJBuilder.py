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

# This module provides the ability to create an object module file by calling the 
# methods of the OBJBuiler class.  It is intended to be imported into another module 
# that drives the actual construction of the object deck.

from fdump import Chunker      # Iterable returning same size pieces of a stirng
from PyOBJ import TRANS        # Object Module EBCDIC-ASCII and Hex Translations
from hexdump import *          # Import binary/hex functions
import time                    # Access to date information

# Refer to IBM publication SA22-7644-06, 
# MVS Program Management: Advanced Facilities, Appendix A, 
# for details of the record formats.

# Record formats:
#             1 11 11 11 11.....777 77777778
# 1234 5 678 90 12 34 56 78.....012 34567890
# TYPE b ADR bb LN bb ID   Variable    SEQ
#
# 2SYM b bbb bb LN bb bb   SYM Data    SEQ
# 2ESD b bbb bb LN bb ID   ESD Data    SEQ
# 2TXT b ADR bb LN bb ID   TXT Data    SEQ
# 2RLD b bbb bb LN bb bb   RLD Data    SEQ
# 2END b ADR bb bb bb ID   END Data    SEQ
#
# ADR = A 24-bit address associated with the record
# LN  = a 2-byte length of the variable data
# ID  = ESDID related to variable content
# SEQ = 8-byte unused field, by convention record sequence information

def ebcdic(string):
    # Translate an ASCII string to EBCDIC
    return OBJBuilder.TRANS.ASCII(string)

class OBJBuilder(object):
    TRANS=TRANS(TRANS.ALL)
    BLANK="\x40"

    def __init__(self):
        self.recs=[]                     # Object deck built
        self.SYMs=[]                     # SYM instances
        self.ESDs=[]                     # ESD instances
        self.TXTs=[]                     # TXT instances
        self.RLDs=[]                     # RLD instances
        self.IDRs=[]                     # IDR instances
        self.ENDrec=None                 # END instance
        
        self.esdmgr=ESDMgr()             # Manages the External Symbol Dictionary
        self.rldmgr=RLDMgr(self.esdmgr)  # Manages the Relocation Dictionary

    def deck(self,seq="",number=1):
        # Returns the deck as a list of 80-byte strings
        self.ENDrec=[self.ENDrec]
        seqno=number
        for y in [self.SYMs,self.ESDs,self.TXTs,self.RLDs,self.ENDrec]:
            for x in y:
                sequence=self.sequence(seq,seqno)
                self.recs.append(x.record(sequence))
                seqno+=1
        return self.recs

    def display_end(self,indent=""):
        print("END Record:")
        if self.ENDrec is None:
            print("END record does not exist")
        print(self.ENDrec.display(indent=indent))

    def display_esd(self,indent=""):
        print("ESD Records:")
        for x in range(len(self.ESDs)):
            rec=self.ESDs[x]
            print(rec.display(indent=indent))

    def display_esds(self,indent=""):
        print("ESD Items:")
        for x in range(len(self.esdmgr.sdid)):
            item=self.esdmgr.get_sdid(x+1)
            print(item.display(indent=indent))

    def display_idrs(self,indent=""):
        print("IDR Items:")
        for item in self.IDRs:
            print(item.display(indent))

    def display_txt(self,indent=""):
        print("TXT Records:")
        for x in self.TXTs:
            print(x.display(indent=indent))

    def esdid(self,sdid):
        # Returns the ESDItem instance corresponding to the presented sdid
        return self.esdmgr.get_sdid(sdid)
        
    def sequence(self,cont,n):
        number="%08d" % n
        return cont+number[len(cont):]
        
    def translate_table(self):
        # Prints the ASCII to EBCDIC translate table.  Useful for debugging.
        OBJBuilder.TRANS.ASCII_TABLE()

    # These methods create and adds specific RLD items
    # optional arguments:
    #   action='+' or action="-"
    #   sdid=number
    #   csect="symbol"
    def A(self,symbol,length,address,**kwds):
        self.rldmgr.add(A,symbol,length,address,kwds)
    def Q(self,symbol,length,address,**kwds):
        self.rldmgr.add(Q,symbol,length,address,kwds)
    def V(self,symbol,length,address,**kwds):
        self.rldmgr.add(Q,symbol,length,address,kwds)
    def CXD(self,symbol,length,address,**kwds):
        self.rldmgr.add(CXD,symbol,length,address,kwds)
    def IMM(self,symbol,length,address,**kwds):
        self.rldmgr.add(IMM,symbol,length,address,kwds)

    # These methods create and add specific ESD items
    def CM(self,name=" ",length=0): 
        self.esdmgr.add(CM(name=name,length=length))
    def ER(self,name):
        self.esdmgr.add(ER(name))
    def LD(self,name,address,**kwds):
        self.esdmgr.add(LD(name,address,kwds))
    def PC(self,address=None,length=None,rmode=0,amode=0,ro=False):
        self.esdmgr.add(PC(address,length,rmode,amode,ro))
    def PR(self,name,length=0,aligned=0):
        self.esdmgr.add(PR(name,length,aligned))
    def SD(self,name,address=None,length=None,rmode=0,amode=0,ro=False):
        self.esdmgr.add(SD(name,address,length,rmode,amode,ro))
    def WX(self,name):
        self.esdmgr.add(WX(name))
        
    def IDR(self,proc="",ver="",rel=""):
        self.IDRs.append(IDR(proc,ver,rel))
        
    def ESD(self):
        # Builds the ESD records from the individual items.  Also finalizes
        # the sections that are built dynamically.  Should be called after all
        # TXT records have been established
        self.esdmgr.finalize()           # Finalize section information
        self.ESDs=self.esdmgr.records()  # Create the records
        
    def TXT(self,text="",address=None,**kwds):
        sdid=self.esdmgr.ckparm(kwds,"TXT")
        section=self.esdid(sdid)
        addr=section.current
        section.add_txt(text,address)

        for txt in Chunker(text,56):
            txtrec=TXT(txt,addr,sdid)
            self.TXTs.append(txtrec)
            addr+=56

    def RLD(self):
        self.RLDs=self.rldmgr.records() # Create the records

    def END(self,entry=None,**kwds):
        if self.ENDrec is not None:
            raise ValueError("PyOBJBuilder.py: error: END already exists")
        sdid=self.esdmgr.ckparm(kwds,"END")
        section=self.esdid(sdid)
        if entry is None:
            entry_addr=section.addr
        else:
            entry_addr=entry
        if entry_addr < section.lowaddr or entry_addr > section.hiaddr:
            raise ValueError("PyOBJBuilder.py: error: entry %s not within section "\
                "'%s' from %s to %s" % (addr24X(entry_addr),section.name,\
                addr24X(section.lowaddr),addr24X(section.hiaddr)))
        self.ENDrec=END(entry=entry,sdid=sdid,idr=self.IDRs)
        
# +-----------------------------------------+
# |                                         |
# |         Object Module Records           |
# |                                         |
# +-----------------------------------------+
        
class IDR(object):
    def __init__(self,proc="",ver="",rel=""):
        self.proc=proc
        self.ver=("00"+ver)[-2:]
        self.rel=("00"+rel)[-2:]
        time_tuple=time.localtime()
        year=time_tuple[0]
        self.year="%02d" % (year % 100)
        self.day="%03d" % time_tuple[7]
    def data(self):
        proc=(self.proc+10*" ")[:10]
        ver=(self.ver+"  ")[:2]
        rel=(self.rel+"  ")[:2]
        year=(self.year+"  ")[:2]
        day=(self.day+"   ")[:3]
        string="%s%s%s%s%s" % (proc,ver,rel,year,day)
        if len(string)!=19:
            raise ValueError("PyOBJBuilder.py: internal: IDR data not 18 bytes: %s" \
                % string)
        return ebcdic(string)
    def display(self,indent=""):
        return "%sIDR(proc='%s',ver='%s',rel='%s',year='%s',day='%s')" \
            % (indent,self.proc,self.ver,self.rel,self.year,self.day)
    
        
class OBJRecord(object):
    types={"SYM":"\x02\xE2\xE8\xD4",
           "ESD":"\x02\xC5\xE2\xC4",
           "TXT":"\x02\xE3\xE7\xE3",
           "RLD":"\x02\xD9\xD3\xC4",
           "END":"\x02\xC5\xD5\xC4"}

    def __init__(self):
        try:
            self.rectype=OBJRecord.types[self.__class__.__name__]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: invalid OBJRecord subclass % s"\
                % self.__class__.__name__)

    def record(self,seq="        "):
        # Returns 72-bytes of used record content.  The 8-byte sequence field in
        # positions 73-80 (relative to 1) is provided elsewhere.
        # Data returned by the subclass data method must be 72 bytes long.
        content=self.data()
        if len(content)!=72:
            raise ValueError("PyOBJBuilder.py: error: subclass %s did not provide "
                "72 bytes of data: returned %s" \
                % (self.__class__.__name__,len(content)))
        if len(seq)!=8:
            raise ValueError("PyOBJBuilde.py: error: sequence field not 8 bytes: %s"\
                % (len(seq)))
        eb=ebcdic(seq)
        #print "%s" % eb
        return content+ebcdic(seq)
                
    def data(self,*args,**kwds):
        # This method must return a string of 68 bytes of data for inclusion into
        # the record corresponding to positions 0-72 (relative to 1) of the 80-byte 
        # record.  Character data that must be EBCDIC must be translated to EBCDIC 
        # by the subclass before providing the data.
        raise NotImplementedError("PyOBJBuilder.py: error: subclass %s "\
            "must provide the data method" % (self.__class__.__name__))
        
    def display(self):
        # This method displays a readable display of an OBJRecord subclass.  It
        # must be provided by the subclass
        raise NotImplementedError("PyOBJBuilder.py: error: subclass %s "\
            "must provide the display method" % (self.__class__.__name__))

class SYM(OBJRecord):
    def __init__(self):
        OBJRecord.__init__(self)

class ESD(OBJRecord):
    def __init__(self,items,firstid=None):
        OBJRecord.__init__(self)
        self.items=items
        self.firstid=firstid
    def data(self):
        esd_data=""
        for item in self.items:
            esd_data+=item.item()
        bin=OBJRecord.types["ESD"]
        bin+=6*OBJBuilder.BLANK
        bin+=halfwordb(len(esd_data))
        bin+=2*OBJBuilder.BLANK
        if self.firstid is None:
            bin+=2*OBJBuilder.BLANK
        else:
            bin+=halfwordb(self.firstid)
        data=esd_data+56*OBJBuilder.BLANK
        bin+=data[:56]
        return bin
    def display(self,indent=""):
        string="%sESD(firstid=%s):" % (indent,self.firstid)
        for x in self.items:
            string="%s %s" % (string,x)
        binary=self.record()
        string="%s\n%s%s" % (string,indent,dump(binary,indent="%s    " % indent))
        return string

class TXT(OBJRecord):
    def __init__(self,text,address,sdid):
        OBJRecord.__init__(self)
        self.text=text
        self.addr=address
        self.sdid=sdid
    def data(self):
        bin=OBJRecord.types["TXT"]
        bin+=OBJBuilder.BLANK
        bin+=addr24b(self.addr)
        bin+=2*OBJBuilder.BLANK
        bin+=halfwordb(len(self.text))
        bin+=2*OBJBuilder.BLANK
        bin+=halfwordb(self.sdid)
        var=self.text+56*OBJBuilder.BLANK
        bin+=var[:56]
        return bin
    def display(self,indent=""):
        string="%sTXT(sdid=%s,address=%s)" % (indent,self.sdid,addr24X(self.addr))
        string="%s: length=%s" % (string,len(self.text))
        binary=self.record()
        string="%s\n%s%s" % (string,indent,dump(binary,indent="%s    " % indent))
        return string

class RLD(OBJRecord):
    def __init__(self):
        OBJRecord.__init__(self)
        self.length=0
        self.items=[]
    def add(self,item):
        # This method adds an item to the record.  It must be called after the
        # can_add method even for the first RLD item.
        self.items.append(item)
        self.length+=item.length
        if self.length>56:
            raise ValueError("OBJBuilder.py: internal: RLD record data exceeds "\
                "56: %s" % self.length)
    def can_add(self,item):
        # This method tests to determine if an RLD item can be added to this
        # RLD record.  It sets the length of the item being added and sets the
        # short flag of the preceding item when the r_esdid and p_esdid values
        # match.  This method must be called even when the first item is being 
        # added, to ensure the first item's length and short flag are set
        # correctly.
        if len(items)==0:
            item.short=False
            item.length=8
            return True
        last_item=self.items[len(items)-1]
        if last_item.issame(item):
            self.last_item.short=True
            item.length=4
        else:
            self.last_item.short=False
            item.length=8
        if self.length+item.length>56:
            return False
        return True
    def data(self):
        bin=OBJRecord.types["RLD"]
        bin+=6*OBJBuilder.BLANK
        bin+=halfwordb(self.length)
        bin+=4*OBJBuilder.BLANK
        rld_data=""
        for x in self.items:
            rld_data+=x.data()
        if len(rld_data)>56:
            raise ValueError("OBJGuilder: internal: RLD data > 56 bytes: %s" \
                % len(rld_data))
        if len(rld_data)!=self.length:
            raise ValueError("OBJBuilder: internal: RLD item lengths and RLD "\
                "record length do not match - %s:%s" % (len(rld_data),self.length))
        rld_data+=56*OBJBuilder.BLANK
        bin+=rld_data[:56]
        return bin
    def display(self,indent=""):
        string="%sRLD(data=%s) items:" % (indent,self.length)
        for x in self.items:
            string+="%s\n%s" % (string,x.display(indent+"   "))
        return string

class END(OBJRecord):
    def __init__(self,sdid,entry=None,idr=[]):
        OBJRecord.__init__(self)
        self.entry=entry
        self.sdid=sdid
        self.idr=idr
    def data(self):
        bin=OBJRecord.types["END"]
        bin+=OBJBuilder.BLANK
        bin+=addr24b(self.entry)
        bin+=6*OBJBuilder.BLANK
        bin+=halfwordb(self.sdid)
        bin+=16*OBJBuilder.BLANK
        if len(self.idr)==0:
            bin+=39*"\x40"
        elif len(self.idr)==1:
            bin+="\xF1"
            bin+=self.idr[0].data()
            bin+=19*OBJBuilder.BLANK
        else: 
           bin+="\xF2"
           bin+=self.idr[0].data()
           bin+=self.idr[1].data()
        bin+=OBJBuilder.BLANK
        return bin
    def display(self,indent=""):
        string="%sEND(entry=%s,sdid=%s)\n" % (indent,addr24X(self.entry),self.sdid)
        binary=self.record()
        string="%s%s" %  (string,dump(binary,indent="%s    " % indent))
        return string
        
# +-----------------------------------------+
# |                                         |
# |  External Symbol Dictionary Management  |
# |                                         |
# +-----------------------------------------+
        
# ESD Item formats
#                111 1 111
#    12345678 9  012 3 456
#    NAME     T  ADR A VAR
#
# SD NAME     00 ADR A LEN   Section definition
# PC bbbbbbbb 04 ADR A LEN   Private code section
# LD NAME     01 ADR b ID    A Global symbol defined in section ID
# PR NAME     06 bbb A LEN   Pseuderegister
# CM NAME/b   05 bbb b LEN   Common section
# ER NAME     02 bbb b bbb   External reference (NAME not defined in this module)
# WX NAME     0A bbb b bbb   Weak External reference (NAME not defined in this module)
        
        
class ESDMgr(object):
    self=None   # Established when instantiated as an instance
    def __init__(self):
        self.sections={}               # CSECT instances
        self.commons=[]                # List of CM instances
        self.esdnames={}               # ESD names
        self.PCsdid=None               # Flag to indicate PC presence
        self.sdid=[]                   # List of items with ID's
        self.LDs=[]                    # Lable definitions (do not get sdid)
        self.esd=[]                    # List of ESD records (records method)
        self.addrtn={"CM":self.add_CM,
                     "ER":self.add_ER,
                     "LD":self.add_LD,
                     "PC":self.add_PC,
                     "PR":self.add_PR,
                     "SD":self.add_SD,
                     "WX":self.add_WX}
        ESDMgr.self=self  # Set up for callbacks by ESDItem instances
    def add(self,item):
        self.addrtn[item.__class__.__name__](item)
        
    def add_id(self,item):
        self.sdid.append(item)
        return len(self.sdid)
        
    def add_name(self,item):
        self.esdnames[item.name]=self.ckname(item)
        
    def add_txt(self,*args,**kwds):
        raise NotImplementedError("ESD item %s does not support adding TXT" \
            % self.__class__.__name__)
        
    def add_CM(self,item):
        self.add_name(item)
        item.sdid=self.add_id(item)
        self.commons.append(item)
        
    def add_ER(self,item):
        self.add_name(item)
        item.sdid=self.add_id(item)
    
    def add_LD(self,item):
        self.add_name(item)
        self.LDs.append(item)
        
    def add_PC(self,item):
        if self.PCsdid is not None:
            raise ValueError("PyOBJBuilder.py: error: only one PC may be present")
        item.sdid=self.add_id(item)
        self.PCsdid=item.sdid
        
    def add_PR(self,item):
        self.add_name(item)
        item.sdid=self.add_id(item)

    def add_SD(self,item):
        self.add_name(item)
        item.sdid=self.add_id(item)
        self.sections[item.name]=item
        
    def add_WX(self,item):
        self.externs.append(item)

    def ckname(self,item):
        # Ensures names are unique
        try:
            self.esdnames[item.name]
            raise ValueError("PyOBJBuilder.py: error: duplicate ESD name: %s" \
                % item.name)
        except KeyError:
            return item
            
    def ckparm(self,dct,item):
        try:
            section=dct["csect"]
            try:
                section=self.sections[section]
            except KeyError:
                raise ValueError("PyOBJBuilder.py: error: section '%s' undefined" \
                    % section)
            sdid=section.sdid
        except KeyError:
            try:
                sdid=dct["id"]
                sdid=int(sdid,10)
                section=self.sdid[sdid-1]
            except KeyError:
                raise ValueError("PyOBJBuilder.py: error: %s required parameter "\
                    "'csect' or 'id' missing" % item)
            sdid=int(sdid,10)
            section=self.sdid[sdid-1]

        if not section.hastext():
            raise ValueError("PyOBJBuilder.py: error: ESD item %s may not contain "\
                "%s" % (section,item))
        return sdid
            
    def finalize(self):
        for x in range(len(self.sdid)):
            item=self.sdid[x]
            item.finalize()
            
    def get_esdid(self,symbol):
        # returns the sdid of the symbol.  May generate a KeyError
        item=self.esdnames[symbol]
        return item.sdid
            
    def get_sdid(self,id):
        # Returns the item instance associated with the id
        return self.sdid[id-1]

    def name(self,name):
        try:
            return self.esdnames[name]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: ESD name undefined: %s" \
                % name)

    def records(self):
        # Creates the ESD records.
        recs=[]    # Accumulates the ESD records
        for x in range(0,len(self.sdid),3):
            items=self.sdid[x:min(x+3,len(self.sdid))]
            recs.append(ESD(items=items,firstid=x+1))
        for x in range(0,len(self.LDs),3):
            items=self.LDs[x:min(x+3,len(self.LDs))]
            recs.append(ESD(items=items,firstid=None))
        return recs
            
    def sdids(self,sdid,lst):
        # Returns the ESD record with the ESD items in the list
        if len(lst)>3:
            raise ValueError("PyOBJBuilder.py: internal: more than three ESD items "\
                "presented for ESD rec: %s" % len(lst))
        return ESD(items=lst,firstid=sdid)
        return esdrec
        
class ESDItem(object):
    types={"CM":"\x05",
           "ER":"\x02",
           "LD":"\x01",
           "PC":"\x04",
           "PR":"\x06",
           "SD":"\x00",
           "WX":"\x0A"}
    alignments={0:"\x00",1:"\x00",None:"\x00",2:"\x01",4:"\x03",8:"\x07"}
    rmodes={64:0x20,31:0x04,24:0,0:0}
    amodes={64:0x10,31:0x02,24:0x01,0:0,"ANY":0x03,"any":0x03}
    names="ABCDEFGHIJKLMNOPQRSTUVWXYZ"\
          "abcdefghijklmnopqrstuvwzyx"\
          "$_#@"

    @staticmethod
    def PR_attr(alignment):
        try:
            return ESDItem.alignments[alignment]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: invalid alignment: %s" \
                % alignment)

    @staticmethod
    def SD_attr(rmode,amode,ro):
        attr=0
        try:
            attr|=ESDItem.rmodes[rmode]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: invalid rmode: %s" % rmode)
        try:
            attr|=ESDItem.amodes[amode]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: invalid amode: %s" % amode)
        if ro:
            attr|=0x80
        return chr(attr)

    def __init__(self,name=None,addr=None,attr=None,length=None,inid=None):
        self.sdid=None      # Provided by OBJBuilder method
        self.typ=ESDItem.types[self.__class__.__name__]
        self.name=self.ckname(name)   # Name of ESDItem (may be None)
        self.addr=addr                # Address (may be None)
        if attr is None:
            self.attr=OBJBuilder.BLANK
        else:
            self.attr=attr[0]
        self.length=length  # Length of ESDItem (may be None)
        self.inid=inid      # ESD ID in which item resides (may be None)

    def __str__(self):
        return "%s(%s,sdid=%s)" % (self.__class__.__name__,self.name,self.sdid)
        
    def ckname(self,name):
        # Validates that the name is valid and the item requires a name
        if name is None and not self.isnamed():
            return
        if len(name)>8:
            raise ValueError("PyOBJBuilder.py: error: ESD item name too long: %s"\
                % name)
        for x in name:
            try:
                ESDItem.names.index(x)
            except ValueError:
                raise ValueError("PyOBJBuilder.py: error: invalid character '%s' " \
                    "found in ESD name: %s" % (x,name))
        return name
        
    def item(self):
        # Returns a 16 byte character string representing the ESD item
        item=""
        if self.name is None:
            name=8*OBJBuilder.BLANK
        else:
            name=self.name+8*" "
            name=name[:8]
            name=ebcdic(name)
        if self.addr is None:
            addr=3*OBJBuilder.BLANK
        else:
            addr=addr24b(self.addr)
        if self.length is None:
            if self.inid is None:
                length=3*OBJBuilder.BLANK
            else:
                length=addr24b(self.inid)
        else:
            length=addr24b(self.addr)
        item=name+self.typ+addr+self.attr+length
        if len(item)!=16:
            raise ValueError("PyOBJBuilder.py: internal: ESD Item length not 16: %s"\
                % len(item))
        return item
                
    def named(self):
        # Returns True/False if item has a name
        return self.name is not None

    def display(self):
        raise NotImplementedError("PyOBJBuilder.py: error: ESDItem subclass %s"\
            "must provide the display method" % (self.__class__.__name__))

    def finalize(self):
        # Complete any final operations before generating ESD item binary data
        # A subclass requiring final actions must override this method
        return

    def hastext(self):
        # Returns True/False if item may contain TXT or LD
        raise NotImplementedError("PyOBJBuilder.py: error: ESDItem subclass %s"\
            "must provide the hastext method" % (self.__class__.__name__))
       
    def isnamed(self):
        # Returns True of False if a name is required
        raise NotImplementedError("PyOBJBuilder.py: error: ESDItem subclass %s"\
            "must provide the isnamed method" % (self.__class__.__name__))
        
class CM(ESDItem):
    def __init__(self,name=" ",length=0):
        super(CM,self).__init__(name,addr=None,length=length)
    def hastext(self):
        return False   
    def isnamed(self):
        return True  # Name can not be None

class ER(ESDItem):
    def __init__(self,name):
        super(ER,self).__init__(self,name)
    def hastext(self):
        return False   
    def isnamed(self):
        return True  # Name can not be None

class LD(ESDItem):
    def __init__(self,name,address,kwds):
        myid=ESDMgr.self.name(kwds["csect"])
        super(LD,self).__init__(self,name,addr=address,inid=myid)
    def hastext(self):
        return False
    def isnamed(self):
        return True

class PR(ESDItem):
    def __init__(self,name,length=0,aligned=0):
        super(PR,self).__init__(name,attr=ESDItem.PR_attr(aligned),length=length)
    def hastext(self):
        return False
    def isnamed(self):
        return True

class SD(ESDItem):
    def __init__(self,name,address=None,length=None,rmode=0,amode=0,ro=False):
        self.rmode=rmode
        self.amode=amode
        self.ro=ro
        if address is None:
            self.current=0         # Current location counter
            self.lowaddr=0         # low water mark of added text addresses
            if length is not None:
                self.hiaddr=length
            else:
                self.hiaddr=0      # high water mark of added text addresses
        else:
            self.current=address   # Current location counter
            self.lowaddr=address   # low water mark of added text addresses
            if length is not None:
                self.hiaddr=self.lowaddr+length
            else:
                self.hiaddr=address
        super(SD,self).__init__(name,
            addr=address,
            attr=self.SD_attr(rmode,amode,ro),
            length=length)
        
    def add_txt(self,text,address=None):
        # If the SD or PC item is created with address=None, the address of the
        # text as it is added to the section will establish the starting address.
        # If the SD or PC item is created with length=None, the total length of 
        # spanned by the added text will extablish the section's length
        #print("address=%s" % address)
        #print("self.addr=%s" % self.addr)
        #print("self.length=%s" % self.length)
        if address is None:
            textaddr=self.current
        else:
            textaddr=address
        textend=textaddr+len(text)
        if self.addr is None:
            # Update starting address if needed
            self.lowaddr=min(textaddr,self.lowaddr)
            # Update the current location
            self.current+=len(text)
        else:
            # Starting address is fixed at section's creation
            if textaddr<self.addr:   # Address lower than section start?
                raise ValueError("PyOBJBuilder.py: error: text starts before "\
                    "section: section start=%s, text start=%s"\
                    % (addr24X(self.addr),addr24X(textaddr)))
        if self.length is None:
            # Section length is dynamic
            self.hiaddr=max(self.hiaddr,textend)
        else:
            # Section size is fixed
            sectend=self.addr+self.length
            if textend>sectend:
                raise ValueError("PyOBJBuilder.py: error: text ends beyond "\
                    "section: section end=%s, text end=%s"\
                    % (addr24X(sectend),addr24X(textend)))

    def display(self,indent=""):
        string='%s[%s] SD(name="%s"' % (indent,self.sdid,self.name)
        if self.addr is None:
            addr="None"
        else:
            addr=addr24X(self.addr)
        string="%s,address=%s" % (string,addr)
        string="%s,length=%s"  % (string,self.length)
        string="%s,rmode=%s"   % (string,self.rmode)
        string="%s,amode=%s"   % (string,self.amode)
        string="%s,ro=%s)\n"   % (string,self.ro)
        string="%s%s    %s-%s" % (indent,string,addr24X(self.lowaddr),\
                                  addr24X(self.hiaddr))
        string="%s, *=%s"      % (string,addr24X(self.current))
        binary=self.item()
        string="%s\n%s"        % (string,dump(binary,indent="%s    " % indent))
        return string

    def finalize(self):
        # If either the starting address or sections length is being determined
        # dynamically, complete the values
        if self.addr is None:
            self.addr=self.lowaddr
        if self.length is None:
            self.length=self.hiaddr-self.lowaddr
    def hastext(self):
        return True
    def isnamed(self):
        return True   # Name can not be None

class PC(SD):
    def __init__(self,address=None,length=None,rmode=0,amode=0,ro=False):
        super(PC,self).__init__(None,address,length,rmode,amode,ro)
    def __str__(self):
        return "PC(sdid=%s)" % self.sdid
    def display(self,indent=""):
        string="%s[%s] PC("   % (indent,self.sdid)
        if self.addr is None:
            addr="None"
        else:
            addr=addr24X(self.addr)
        string="%saddress=%s" % (string,addr)
        string="%s,length=%s" % (string,self.length)
        string="%s,rmode=%s"  % (string,self.rmode)
        string="%s,amode=%s"  % (string,self.amode)
        string="%s,ro=%s)\n"  % (string,self.ro)
        string="%s%s    %s-%s"% (indent,string,addr24X(self.lowaddr),\
                                 addr24X(self.hiaddr))
        string="%s, *=%s"     % (string,addr24X(self.current))
        binary=self.item()
        string="%s\n%s"       % (string,dump(binary,indent="%s    " % indent))
        return string
    def hastext(self):
        return True
    def isnamed(self):
        return False

class WX(ESDItem):
    def __init__(self,name):
        super(WX,self).__init__(self,name)
    def hastext(self):
        return False   
    def isnamed(self):
        return True  # Name can not be None

# +-----------------------------------------+
# |                                         |
# |          Relocation Dictionary          |
# |                                         |
# +-----------------------------------------+

# RLD Item format:
#
# 12 34 5 678  (long format)
# R  P  F ADR
#
# 1 234        (short format)
# F ADR

class RLDMgr(object):
    def __init__(self,esdmgr):
        self.items=[]
        self.esdmgr=esdmgr

    def add(self,item_cls,symbol,length,address,kwds):
        # Primary method for adding an RLD item
        r_esdid=self.symbol(symbol)
        p_esdid=self.pos_esdid(kwds)
        act=self.set_action(kwds)
        item=item_cls(r_esdid,p_esdid,length,act,address)
        self.items.append(item)

    def pos_esdid(self,kwds):
        try:
            p_esdid=kwds["sdid"]
        except KeyError:
            try:
                p_sym=kwds["csect"]
            except KeyError:
                raise ValueError("OBJBuilder.py: error: required argument 'csect' "\
                    "or 'sdid' missing")
            p_esdid=self.symbol(p_sym)
        return p_esdid
     
    def records(self):
        # This method generates a series of RLD instances from the list of RLDItems.
        self.items.sort()
        recs=[]
        rec=RLD()
        for x in self.items:
            if rec.can_add(x):
                rec.add(x)
                continue
            recs.append(rec)
            rec=RLD()
        if rec.length>0:
            recs.append(rec)
        return recs  

    def set_action(self,kwds):
        try:
            return kwds["action"]
        except KeyError:
            return "+"
     
    def symbol(self,sym):
        # Return symbols ESD ID
        try:
            return self.esdmgr.get_esdid(sym)
        except KeyError:
            raise ValueError("OBJBuilder.py: error: undefined ESD symbol: %s" \
                % sym)

class RLDItem(object):
    actions={"+":0x00,"-":0x02}
    def __init__(self,r_esdid,p_esdid,address):
        self.r_esdid=r_esdid
        self.p_esdid=p_esdid
        self.address=address
        self.short=False     # This may be changed when added to an RLD record
        self.length=8        # This may be changed when added to an RLD record
        # self.flags must be set by the subclass

    def __cmp__(self,other):
        # This method is used to sort the RLD items before creating the RLD records
        if self.r_esdid<other.r_esdid:
            return -1
        if self.r_esdid>other.r_esdid:
            return 1
        if self.p_esdid < other.p_esdid:
            return -1
        if self.p_esdid > other.p_edsid:
            return 1
        if self.address < other.address:
            return -1
        if self.address > other.address:
            return 1
        return 0

    def data(self):
        if self.length==8:
            bin=halfwordb(self.r_esdid)
            bin+=halfwordb(self.p_esdid)
            bin+=chr(self.flags|0x01)
        elif self.length==4:
            bin=chr(self.flags)
        else:
            raise ValueError("OBJBuilder: internal: RLD item length not 4 or 8: "\
                "%s" % self.length)
        bin+=addr24b(self.address)
        return bin

    def display(self,indent=""):
        string="%s%s" % (indent,self.__class__.__name__)
        string="%s(R-esdid=%s" % (string,self.r_esdid)
        string="%s,P-esdid=%s" % (string,self.p_esdid)
        string="%s,P-addr=0x%06X)" % (string,self.address)
        string="%s\n%s   flags=0x%02X: " % (string,indent,self.flags)
        string="%s%s" % (string,self.display_flags())
        return string

    def display_short(self):
        return {0x00:"False",0x01:"True"}[self.flags & 0x01]

    def display_sign(self):
        return {0x00:"+",0x02:"-"}[self.flags & 0x02]

    def issame(self,next):
        # compares this RLD item to the next item to determine if next can omit
        # its r_esdid and p_esdid fields from its entry in the RLD record
        return (self.p_esdid==next.p_esdid) and (self.r_esdid==next.esdid)

    def set_action(self,action):
        try:
            self.flags|=RLDItem.actions[action]
        except KeyError:
            raise ValueError("PyOBJBuilder.py: error: invalid RLD item action: %s" \
                % action)

class adcon(RLDItem):
    lengths={1:0x00,2:0x04,3:0x08,4:0x0C,5:0x40,6:0x44,7:0x48,8:0x4C}
    def __init__(self,r_esdid,p_esdid,length,action,address,typ):
        self.flags=typ
        self.set_action(action)
        self.set_length(length)
        super(adcon,self).__init__(r_esdid,p_esdid,address)

    def display_flags(self):
        typ={0x00:"A",0x10:"V",0x20:"Q",0x30:"CXD"}[self.flags & 0x30]
        length={0x40:5,0x44:6,0x48:7,0x4C:8,0x00:1,0x04:2,0x08:3,0x0C:4}\
            [self.flags & 0x4C]
        return "type=%s, sign=%s, length=%s, next_short=%s" \
            % (typ, self.display_sign(), length, self.display_short())

    def set_length(self,length):
        try:
            self.flags|=adcon.lengths[length]
        except KeyError:
            raise ValueError("PyOBJBuilder,py: error: invalid RLD adcon length: %s" \
                % length)

class A(adcon):
    def __init__(self,r_esdid,p_esdid,length,action,address):
        super(A,self).__init__(r_esdid,p_esdid,length,action,address,0x00)
        
class V(adcon):
    def __init__(self,r_esdid,p_esdid,length,action,address):
        super(V,self).__init__(r_esdid,p_esdid,length,action,address,0x10)
        
class Q(adcon):
    def __init__(self,r_esdid,p_esdid,length,action,address):
        super(Q,self).__init__(r_esdid,p_esdid,length,action,address,0x20)
        
class CXD(adcon):
    def __init__(self,r_esdid,p_esdid,length,action,address):
        super(CXD,self).__init__(r_esdid,p_esdid,length,action,address,0x30)
        
class IMM(adcon):
    lengths={2:0x70,4:0x78}
    def ___init__(self,r_esdid,p_esdid,length,action,address):
        super(IMM,self).__init__(r_esdid,p_esdid,length,action,address,0x00)

    def display_flags(self):
        # Override adcon display_flags method
        try:
            typ,length={0x70:("IMM",2),0x78:("IMM",4)}[self.flags & 0x7C]
        except KeyError:
            typ="?"
            length="?"
        return "type=%s, sign=%s, length=%s, short_next=%s" \
            % (typ, self.display_sign(), length, self.display_short())

    def set_length(self,length):
        # Overrides RLDItem set_length method
        try:
            self.flags|=IMM.length[length]
        except KeyError:
            raise ValueError("OBJBuilder.py: error: invalid RLD IMM length: %s" \
                % length)

if __name__=="__main__":
    print("PyOBJBuilder.py, Copyright, Harold Grovesteen, 2011")
    print("PyOBJBuilder.py: error: module is intended to be imported only")