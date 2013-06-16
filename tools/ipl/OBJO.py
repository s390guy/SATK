#!/usr/bin/python

# Utility to handle IBM object decks

import objutil            # Access the generic object module interface
import struct             # Python binary structure module
import sys                # Access to command line arguments
from translate import *   # ASCII/EBCDIC translate tables
from hexdump import   *   # Access to hexdump methods

# Note: this module requires Python 2.6 or greater

# Data relationships
#
#    objutil:  module  ------> codearea ------> adcon
#               ^               ^  |  ^          |  ^
#               |               |  |  +----------+  |
#               |               |  V                |
#               |               | relo              |
#               |               |  ^                |
#               |               |  |                |
#    OBJO:      |               | objrelo           |
#               |               |  ^                |
#               |               |  |                |
#              obj0 ---------> section ----------> rlditem
#

# Reference: IBM manual SA22-7644-09

# OBJO Class Hierarchy:
#
#  sym
#  esd
#  txt
#  rld
#  end
#  esditem -----> ld
#                 er
#                 pr
#                 cm
#                 sd -----> pc 
#  rlditem -----> A
#                 V
#                 Q
#                 CXD
#  section
#  objo

class objo(objutil.module):
    # For objo instances, code area base and load point are always zero.
    def create(path):
        # This staticmethod is required by objutil to create an instance
        recs=pythonize.deck(path)
        obj=objo.pythonize(recs)
        return obj.init()
    create=staticmethod(create)
    def pythonize(recs,strict=True):
        obj=objo(recs)
        text=[]
        rlditems=[]
        esditems=[]
        needs_length=None
        for x in recs:
            if isinstance(x,esd):
                for y in x.items:
                    obj.esditem(y)
                    if isinstance(y,sd):
                        if not y.len_on_end:
                            obj.sections[y.esdid]=section(y)
                            continue
                        if needs_length==None:
                            needs_length=y
                        else:
                            msg="Multiple sections need length on END: ESDID %s"\
                                % y.esdid
                            if strict:
                                raise ValueError(msg)
                            else:
                                print(msg)
                    else:
                        esditems.append(y)
                continue
            if isinstance(x,txt):
                text.append(x)
                continue
            if isinstance(x,rld):
                for y in x.items:
                    rlditems.append(y)
                continue
            if isinstance(x,end):
                if needs_length!=None:
                    sdo=needs_length
                    if x.sd_length==None:
                        sdo.length=0
                    else:
                        sdo.length=x.sd_length
                    sdo.len_on_end=False
                    obj.sections[sdo.esdid]=section(sdo)
                obj.end=x
            if isinstance(x,sym):
                continue
        for x in esditems:          # Process ESD items from deck
            objo.ESD(obj,x,strict)
        for x in text:              # Process TXT records from deck
            objo.TXT(obj,x,strict)
        obj.image()                 # Create storage image from TXT data
        for x in rlditems:
            objo.RLD(obj,x,strict)
        # Resolve local V-constants
        return obj
    pythonize=staticmethod(pythonize)
    
    def ESD(obj,esditem,strict=True):
        if isinstance(esditem,ld):
            sect=obj.sections[esditem.pesdid]
            sect.ld(esditem,strict)
    ESD=staticmethod(ESD)

    def TXT(obj,txtrec,strict=True):
        sect=obj.sections[txtrec.esdid]
        sect.TXT(txtrec.address,txtrec.text,strict)
    TXT=staticmethod(TXT)

    def RLD(obj,rlditem,strict=True):
        # Present to the RLD item to the section in which it resides
        sect=obj.sections[rlditem.pos_esdid]
        rlditem.ressect=sect
        sect.RLD(rlditem,strict)
        if rlditem.pos_esdid!=rlditem.rel_esdid:
            # This RLD item is an external reference
            ext_esdid=obj.esd[rlditem.rel_esdid]
            try:
                esditem=obj.names[ext_esdid.name]
                # Locally resolved name, pass the real value
            except KeyError:
                esditem=ext_esdid
                # A real external reference, pass the ER/WX to section
            sect.external(obj,rlditem,esditem,strict)
    RLD=staticmethod(RLD)

    def __init__(self,deck=[]):
        objutil.module.__init__(self)
        self.deck=deck     # List of card images
        self.esd={}        # ESD items indexed by ESDID
        self.names={}      # Locally resolved ESD names to ESDID mapping
        self.sections={}   # Sections indexed by ESDID
        self.end=None      # End instance
        # Build the relocation type binder mappings
    
    def __str__(self):
        str="External Symbol Dictionary (ESDIDs):"
        esdids=self.esd.keys()
        esdids.sort()
        for x in esdids:
            str="%s\n    %s" % (str,self.esd[x])
        str="%s\nExternal Symbol Dictionary (Symbols):" % str
        names=self.names.keys()
        names.sort()
        for x in names:
            str="%s\n    %s %s" % (str,x.ljust(8),self.names[x].esdid)
        sections=self.sections.keys()
        sections.sort()
        for x in sections:
            str="%s\n%s" % (str,self.sections[x])
        return str

    def deckdump(self):
        # Print the input object deck
        for x in self.deck:
           print(x)

    def esditem(self,item,strict=True):
        if not isinstance(item,ld):
            try:
                self.esd[item.esdid]
                msg="ESDID %s duplicate" % item.esdid
                if strict:
                    raise KeyError(msg)
                else:
                    print(msg)
                    return
            except KeyError:
                self.esd[item.esdid]=item
        if len(item.name)==0:
            return
        if isinstance(item,sd) or isinstance(item,ld) or isinstance (item,pr):
           try:
               self.names[item.name]
               msg="ESDID %s duplicate name" % item.name
               if strict:
                   raise KeyError(msg)
               else:
                   print(msg)
           except KeyError:
               self.names[item.name]=item

    def image(self):
        # For each section, merge TXT data into a storage image
        for x in self.sections.itervalues():
            x.image()
    #
    # These methods are used by objutil to interrogate the object instance
    def getEntry(self):
        # Return the entry point.  Entry points are assumed to be determined
        # at linkage editing of an object module.  None is returned
        return None
    def getLocal(self):
        # Return a dictionary of code area objects keyed to their local ids
        return self.sections
    def getNames(self):
        # Return a dictionary of code area objects keyed to their names
        namedict={}
        for x in self.sections:
            sect=self.sections[x]
            namedict[sect.name]=sect
        return namedict
    def hexdump(self):
        # Return a string of binary contents of the module's sections
        names=self.sections.keys()
        names.sort()
        str=""
        for x in names:
            sect=self.sections[x]
            str="%sTXT of Section %s\n%s\n" \
                % (str,sect.name,sect.hexdump("    "))
        return str[:-1]


class section(objutil.code):
    binders=None    # Set in first call to section.getBinders()
    def __init__(self,sd):
        objutil.code.__init__(self)
        self.sd=sd               # Section's sd instance
        self.name=sd.name        # Section name
        self.address=sd.address  # SD item address
        self.length=sd.length    # SD item length
        self.esdid=sd.esdid      # SD item ESDID
        self.rmode=sd.rmode      # SD item rmode
        self.start=None  # TXT residency start
        self.end=None    # TXT residency end
        self.extids={}   # External ESDID's encountered in external RLD's
        self.entries={}  # Entry points indexed by address
        self.rlds={}     # RLD entries indexed by address
        self.rldexts={}  # External RLD items references indexed by address
        self.vcons=[]    # List of V rlditems encountered
        self.text=bytearray("\x00"*self.length)
        self.txt_chunks=[]  # Accumulate portions of text for later merging
    def __str__(self):
        end=self.address+self.length-1
        str="%s Section ESDID[%s] %06X-%06X length(%s):" \
            % (self.name.ljust(8),self.esdid,self.address,end,self.length)
        length=self.end-self.start+1
        str="%s\n    TXT %06X-%06X length(%s)" \
            % (str,self.start,self.end,len(self.text))
        externs=self.extids.keys()
        if len(externs)==0:
            str="%s\n    External references: None" % str
        else:
            str="%s\n    External references:" % str
            externs.sort()
            for x in externs:
                str="%s\n        %s" % (str,self.extids[x])
        entries=self.entries.keys()
        if len(entries)==0:
            str="%s\n    Global entries: None" % str
        else:
            str="%s\n    Global entries:" % str
            entries.sort()
            for x in entries:
                str="%s\n        %s" % (str,self.entries[x])
        rlds=self.rlds.keys()
        if len(rlds)==0:
            str="%s\n    Relocation dictionary: None" % str
        else:
            str="%s\n    Relocation dictionary:" % str
            rlds.sort()
            for x in rlds:
                str="%s\n        %s" % (str,self.rlds[x])
        return str
    def bytes(self,offset,length):
        # returns a bytearray of the specified length starting at the
        # specified offset from the start of the content
        return self.text[offset:offset+length]
    def external(self,obj,rlditem,esditem,strict=True):
        # Add external information for my external references from objo.RLD
        try:
            self.rldexts[rlditem.address]
            msg="ESDID[%s] %06X - multiple external RLD items" \
                % rlditem.address
            if strict:
                raise ValueError(msg)
            else:
                 print(msg)
                 return
        except KeyError:
            self.rldexts[rlditem.address]=rlditem
        try:
            self.extids[esditem.esdid]
            # Already have this information, don't need to add it again
        except KeyError:
            self.extids[esditem.esdid]=esditem
        if isinstance(esditem,ld):
            rlditem.codeid=esditem.pesdid
            
    def image(self):
        if len(self.txt_chunks)==0:
            return
        self.text=bytearray("\x00"*(self.end-self.start+1))
        for x in range(len(self.txt_chunks)):
            (address,txt)=self.txt_chunks[x]
            offset=address-self.start
            if offset<0:
                raise ValueError(\
                    "Negative offset from txt_chunk[%s]: %s-%s=%s" \
                    % (x,address,self.start,offset))
            self.text[offset:offset+len(txt)]=txt
        self.txt_chunks=[]
    def ld(self,lditem,strict=True):
        self.entries[lditem.address]=lditem
    def TXT(self,address,string,strict=True):
        self.txt_chunks.append((address,string))
        #offset=self.address-address
        #self.text[offset:offset+len(string)]=string
        if self.start==None:
            self.start=address
        else:
            if address<self.start:
                self.start=address
        end=address+len(string)-1
        if end>self.end:
            self.end=end
    def RLD(self,rlditem,strict=True):
        try:
            self.rlds[rlditem.address]
            msg="ESDID[%s] %06X - multiple RLD items" % rlditem.address
            if strict:
                raise ValueError(msg)
            else:
                print(msg)
        except KeyError:
            self.rlds[rlditem.address]=rlditem
        if isinstance(rlditem,V):
            self.vcons.append(rlditem)
    #
    # These methods support the objutil code area interface
    def getAdcons(self):
        # Return a list of adcon instances (rlditems)
        cons=[]
        for x in self.rlds:
            cons.append(self.rlds[x])
        return cons
    def getBinders(self):
        # Return the binder dictionary
        if section.binders is None:
            section.binders={}
            objutil.binder(1,1,8).register(section.binders)
            objutil.binder(2,2,16).register(section.binders)
            objutil.binder(3,3,24).register(section.binders)
            objutil.binder(4,4,31).register(section.binders)
            objutil.binder(8,8,64).register(section.binders)
        return section.binders
    def getContent(self):
        # Return a copy of the section's content
        string=str(self.text)
        return bytearray(string)
    def getID(self):
        # Return the code area's local identifier
        return self.esdid
    def getLoad(self):
        # Return the storage residency start address of the code area's content
        return self.address
    def getRmode(self):
        # Returns the residency mode of this section.  Default is 24
        return self.rmode
    def hexdump(self,indent=""):
        # Returns the contents of this section
        return dump(self.text,self.start,self.getRmode(),indent)

class pythonize(object):
    # This class provides a set of transformational methods that convert
    # IBM 80-byte records into Python object instances or lists.  The
    # conversions ultimately result in a OBJO instance being created.
    # 
    rectypes={}  # Maps OBJO record type to pythonize method
    esdtypes={}  # Maps ESD item type to Python class
    rldtypes={}  # Maps RLD item type to Python class
    objometh={}  # Maps record class to pythonize method
    def init():
        # Initializes values, lists and dictionaries at module end
        # Map OBJO record identifiers to pythonize method
        reclist=[("\x02\xC5\xE2\xC4",pythonize.esdrec),\
                 ("\x02\xE3\xE7\xE3",pythonize.txtrec),\
                 ("\x02\xD9\xD3\xC4",pythonize.rldrec),\
                 ("\x02\xE2\xE8\xD4",pythonize.symrec),\
                 ("\x02\xC5\xD5\xC4",pythonize.endrec)\
                ]
        for x in reclist:
            pythonize.rectypes[x[0]]=x[1]
        # Map ESD item types to Python class
        esdlist=[("\x00",sd),\
                 ("\x01",ld),\
                 ("\x02",er),\
                 ("\x04",pc),\
                 ("\x05",cm),\
                 ("\x06",pr),\
                 ("\x0A",wx),\
                 ("\x0D",pc),\
                 ("\x0F",cm)\
                ]
        for x in esdlist:
            pythonize.esdtypes[x[0]]=x[1]
        rldlist=[("\x00",A),\
                 ("\x10",V),\
                 ("\x20",Q),\
                 ("\x30",CXD)\
                ]
        for x in rldlist:
            pythonize.rldtypes[x[0]]=x[1]
    init=staticmethod(init)

    #
    # These methods operate on an entire OBJO file
    def cards(images,strict=True):
        if not isinstance(images,type("")):
	        raise TypeError("OBJECT argument must be a string")
        cards,overflow=divmod(len(images),80)
        if overflow!=0:
	        raise ValueError("Last card of deck is truncated")
        recs=[]
        for x in range(0,len(images)-1,80):
            card=images[x:x+80]
            try:
                method=pythonize.rectypes[card[0:4]]
                #print method
            except KeyError:
                msg="Unrecognized OBJO record, %s: %02X%02X%02X%02X" %\
                    (len(recs),\
                    ord(card[0]),ord(card[1]),ord(card[2]),ord(card[3]))
                if strict:
                    raise ValueError(msg)
                else:
                    print(msg)
                    continue
            recs.append(method(card,len(recs),strict))
        return recs
    cards=staticmethod(cards)

    def deck(path,strict=True):
        # Converts, a string into a list of record instances
        try:
            fo=open(path,"rb")
        except IOError:
            raise IOError("Could not open for reading: %s" % path)
        try:
            images=fo.read()
        except IOError:
            raise IOError("Error reading: %s" % path)
        try:
            fo.close()
        except IOError:
            raise IOError("Error closing: %s" % path)
        return pythonize.cards(images,strict)
    deck=staticmethod(deck)

    #
    # These methods convert individual record types into their parts
    def endrec(card,recno=None,strict=True):
        if card[28:32]=="\x40\x40\x40\x40":
            csect_len=0
        else:
            csect_len=fullword(card[28:32])
        idr_data=card[32:71]
        if card[4:16]=="\0x40"*12:
            # END Type 2
            if card[16:24]=="\x40\x40\x40\x40\x40\x40\x40\x40":
                entry_sym=None
            else:
                entry_sym=pythonize.name(card[16:24])
            return end(recno,csect_len,None,None,entry_symbol,idr_data)
        else:
            # END Type 1
            if card[5:8]=="\x40\x40\x40":
                entry=None
            else:
                entry=addr24(card[5:8])
            if card[14:16]=="\x40\x40":
                entry_esdid=None
            else:
                entry_esdid=halfword(card[14:16])
            return end(recno,csect_len,entry,entry_esdid,None,idr_data)
    endrec=staticmethod(endrec)

    def esdrec(card,recno=None,strict=True):
        length=halfword(card[10:12])
        (items,overflow)=divmod(length,16)
        # z390 does not create correct ESD length in all cases.
        #if overflow!=0:
        #    raise ValueError("[%s] ESD data length not multiple of 16: %s" \
        #        % (recno,length))
        # Remove these tests after z390 is fixed
        if overflow!=0:
             errlen=length
             length=(items+1)*16
             print("[%s] Warning ESD length invalid, rounding up: %s" % \
                 (recno,errlen))
        data=card[16:16+length]
        esdid=card[14:16]
        if esdid=="\x40\x40":
            esdid=None
        else:
            esdid=halfword(esdid)
        items=[]
        #ld_items=0
        for x in range(0,len(data)-1,16):
            item=data[x:x+16]
            itemtype=item[8]
            try:
                cls=pythonize.esdtypes[itemtype]
                #print cls
                # LD items use ESDID in ESD record
                # if itemtype=="\x01":
                #     ld_items+=1
            except KeyError:
                msg="[%s] Unrecognized ESD item: %02X" % (recno),ord(item[8])
                if strict:
                    raise ValueError(msg)
                else:
                    print(msg)
                    continue
            esditem=cls.pythonize(item[:8],item[9:12],item[12],item[13:16])
            #                         name,      addr,    flag,       data
            items.append(esditem)
        # ESDID of LD items start with ESDID in the ESD record
        thisesd=esdid
        for x in items:
            x.esdid=thisesd
            thisesd+=1
        return esd(recno,items,esdid)
    esdrec=staticmethod(esdrec)

    def rldrec(card,recno=None,strict=True):
        rldlength=halfword(card[10:12])
        data=card[16:16+rldlength]
         # Parse rld items in record
        cont=False
        prevpos=None
        prevesdid=None
        items=[]
        while len(data)!=0:
            if not cont:
                if len(data)<8:
                    msg="[%s] last RLD item not 8 bytes: %s" \
                        %  (recno,len(data))
                    if strict:
                        raise ValueError(msg)
                    else:
                        print(msg)
                resdid=halfword(data[0:2])
                pesdid=halfword(data[2:4])
                flag=ord(data[4])
                addr=addr24(data[5:8])
                data=data[8:]
            else:
                if len(data)<4:
                    msg="[%s] last RLD item not 4 bytes: %s" \
                        % (recno,len(data))
                    if strict:
                        raise ValueError(msg)
                    else:
                        print(msg)
                pesdid=prevpos
                resdid=prevesdid
                flag=ord(data[0])
                addr=addr24(data[1:4])
                data=data[4:]
            if flag&0x01==0x01:
                cont=True
                prevesdid=resdid
                prevpos=pesdid
            else:
                cont=False
                prevesdid=None
                prevpos=None
            if flag&0x02==0x02:
                direction=-1
            else:
                direction=1
            isrel=flag&0x70==0x70
            if isrel:
                if flag&0x0C==0x00:
                    length=2
                else:
                    length=4
                items.append(RI(addr,resdid,pesdid,length,direction))
                continue
            if flag&0x40==0x40:
                lenincr=4
            else:
                lenincr=0
            length=((flag&0x0C)>>2)+lenincr
            itemtype=flag&0x30
            try:
                cls=pythonize.rldtypes[chr(itemtype)]
            except KeyError:
                msg="[%s] Unrecognized RLD item at pos %s: %02X" %\
                    (recno,rldlength-len(data),itemtype)
                if strict:
                    raise ValueError(msg)
                else:
                    print(msg)
                continue
            items.append(cls(addr,resdid,pesdid,length,direction))
        return rld(recno,items)
    rldrec=staticmethod(rldrec)

    def symrec(card,recno=None,strict=True):
        length=halfword(card[10:12])
        return sym(recno,addr,card[16:16+length])
    symrec=staticmethod(symrec)

    def txtrec(card,recno=None,strict=True):
        addr=addr24(card[5:8])
        length=halfword(card[10:12])
        esdid=halfword(card[14:16])
        return txt(recno,esdid,addr,card[16:16+length])
    txtrec=staticmethod(txtrec)

    #
    # This method operates on EBCDIC name fields
    def name(ebcdic):
        if len(ebcdic)!=8:
            raise ValueError("EBCDIC name must be 8-bytes: %s" % len(ebcdic))
        return ebcdic.translate(E2A).rstrip()
    name=staticmethod(name)
#
# Individual OBJO records as Python instance
class end(object):
    def __init__(self,recno,length,entry,esdid,symbol,idr):
        self.recno=recno
        self.sd_length=length
        self.entry=entry
        self.entry_esdid=esdid
        self.entry_symbol=symbol
        self.idr=idr
    def __str__(self):
        str="END %s:" % self.recno
        str="%s\n    Section length=%s" % (str,self.sd_length)
        if self.entry==None:
            str="%s\n    Entry symbol=%s" % (str,self.entry_symbol)
        else:
            str="%s\n    Entry point=%06X in ESDID[%s]" % \
                (str,self.entry,self.entry_esdid)
        return str

class esd(object):
    # Helper methods for pythonizing flags
    amodes=["?","24","31","ANY","64"]
    amode24=1
    amode31=2
    amode64=4
    amodeany=3
    def amode(flag):
        if flag&0x10==0x10:
            return 4
        return flag&0x03
    amode=staticmethod(amode)
    def rmode(flag):
        if flag&0x20==0x20:
            return 64
        rmode=(flag&0x04)>>2
        return [24,31][rmode]
    rmode=staticmethod(rmode)
    def __init__(self,recno,items,esdid=None):
        self.recno=recno
        self.esdid=esdid  # esdid of first item if not all LD items
        self.items=items
        #print self.recno,self.esdid,self.items
    def __str__(self):
       str=""
       if self.esdid!=None:
           str=" First ESDID in rec %s" % self.esdid
       str="ESD %s:%s" % (self.recno,str)
       for x in self.items:
           str="%s\n   %s" % (str,x)
       return str

class rld(object):
    def __init__(self,recno,items):
        self.recno=recno
        self.items=items
    def __str__(self):
       str="RLD %s" % (self.recno)
       for x in self.items:
           str="%s\n   %s" % (str,x)
       return str
        
class sym(object):
    def __init__(self,recno,data):
        self.recno=recno
        self.data=data
    def __str__(self):
       return "SYM %s, data length:" % (self.recno,len(self.data))

class txt(object):
    def __init__(self,recno,esdid,address,text):
        self.esdid=esdid
        self.recno=recno
        self.address=address
        self.text=text
    def __str__(self):
       str="TXT %s:" % self.recno
       return "%s\n    ESDID[%s] Address %06X, bytes %s" %\
           (str,self.esdid,self.address,len(self.text))

#
# Individual ESD items

class esditem(object):
    def __init__(self,name):
       self.esdid=None      # Supplied by pythonize.esdrec method
       self.name=name
    
class cm(esditem):
    # Common control section
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        # address=addr24(addr)             Address determined by linkage editor
        # flags=ord(flag)                  Flags not used
        info=addr24(data)
        return sd(ascii,info)
    pythonize=staticmethod(pythonize)
    def __init__(self,name,length):
        esditem.__init__(self,name)
        self.address=None
        self.length=length
        self.rsect=False
        self.len_on_end=False
    def __str__(self):
        return "[%s] CM: %s @ %06X: size(%s),RM(%s),AM(%s),RO(%s)" % \
            (self.esdid,\
             self.name.ljust(8),\
             self.address,\
             length,\
             self.rmode,\
             self.amode,\
             self.rsect\
            )

class er(esditem):
    # External lable reference
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        # address=addr24(addr)           Address not used
        # flags=ord(flag)                Flags not used
        # info=addr24(data)              Data not used
        return er(ascii)
    pythonize=staticmethod(pythonize)
    def __init__(self,name):
        esditem.__init__(self,name)
        self.weak=False
        self.id="ER"
    def __str__(self):
        return "[%s] %s: %s" % (self.esdid,self.id,self.name)

class ld(esditem):
    # Lable referencable externally, an entry point
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        address=addr24(addr)
        # flags=ord(flag)      Flags not used
        info=addr24(data)
        return ld(ascii,address,info)
    pythonize=staticmethod(pythonize)
    def __init__(self,name,address,pesdid):
        esditem.__init__(self,name)
        self.address=address
        self.pesdid=pesdid
    def __str__(self):
        return "[%s] LD: %s @ %06X in ESDID[%s]" \
            % (self.esdid,self.name.ljust(8),self.address,self.pesdid)

class pr(esditem):
    # Pseudo Register
    alignments=[0,2,4,8]
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        address=addr24(addr)
        flags=ord(flag)
        info=addr24(data)
        return pr(address,flags,info)
    pythonize=staticmethod(pythonize)
    def __init__(self,name,alignment,length):
        esditem.__init__(self,name)
        self.alignment=pr.alignments[alignment]
        self.length=length
    def __str__(self):
        return "[%s] PR: %s, %s bytes, align(%s)" % \
            (self.esdid,self.name.ljust(8),length,self.alignment)

class sd(esditem):
    # Named Control Section
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        address=addr24(addr)
        flags=ord(flag)
        info=addr24(data)
        rsect=flags&0x08==0x08
        return sd(ascii,address,esd.amode(flags),esd.rmode(flags),rsect,info)
    pythonize=staticmethod(pythonize)
    def __init__(self,name,address,amode,rmode,rsect,length):
        esditem.__init__(self,name)
        self.address=address
        self.amode=amode    # See esd.amodes
        self.rmode=rmode
        self.rsect=rsect
        self.length=length
        self.len_on_end=self.length==0   # Might need legnth from END
        self.id="SD"
    def __str__(self):
        amode=esd.amodes[self.amode]
        return "[%s] %s: %s @ %06X: size(%s),RM(%s),AM(%s),RO(%s)" % \
            (self.esdid,\
             self.id,\
             self.name.ljust(8),\
             self.address,\
             self.length,\
             self.rmode,\
             amode,\
             self.rsect\
            )
            
class pc(sd):
    # Private Control Section (unnamed section)
    def pythonize(name,addr,flag,data):
        # ascii=pythonize.name(name)    Name not used for private csect
        address=addr24(addr)
        flags=ord(flag)
        info=addr24(data)
        rsect=flags&0x08==0x08
        return pc(address,esd.amode(flags),esd.rmode(flags),rsect,info)
    pythonize=staticmethod(pythonize)
    def __init__(self,address,amode,rmode,rsect,length):
        sd.__init__(self,"",address,amode,rmode,rsect,length)
        self.id="PC"

class wx(er):
    # Weak External lable reference
    def pythonize(name,addr,flag,data):
        ascii=pythonize.name(name)
        # address=addr24(addr)           Address not used
        # flags=ord(flag)                Flags not used
        # info=addr24(data)              data not used
        return wx(ascii)
    pythonize=staticmethod(pythonize)
    def __init__(self,name):
        er.__init__(self,name)
        self.weak=True
        self.id="WX"

#
# Individual RLD items
class rlditem(objutil.adcon):
    convert={1:byte,
             2:halfword,
             3:addr24,
             4:fullword,
             5:dblword}
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        objutil.adcon.__init__(self)
        self.address=addr
        self.length=length+1
        self.rel_esdid=rel_esdid
        self.pos_esdid=pos_esdid
        self.direction=direction
        self.setRtype(self.getRtype())
        self.ressect=None         # objo.RLD() method will provide
        self.codeid=None          # sect.extern() method will provide
    def __str__(self):
        clsname=self.__class__.__name__
        str="%sL%s" % (clsname,self.length)
        if self.direction>0:
            dir="+"
        else:
            dir='-'
        str="%s in ESDID[%s] @ %06X %spointer is rel to ESDID[%s]" %\
            (str,self.pos_esdid,self.address,dir,self.rel_esdid)
        return str
    # These methods are used by objutil.py to interogate the RLD item
    def getAddend(self):
        # Extracts the address constant addend from the resident 
        # section's content
        bytes=str(self.ressect.bytes(self.address,self.length))
        return rlditem.convert[self.length](bytes)
    def getPtrDir(self):
        # This method returns how the address constants contents relates to
        # the base of section to which the address constant relates
        return self.direction
    def getPtrID(self):
        # Returns the object format specific id of the section to which
        # the address constand actually points.
        if self.codeid!=None:
            return self.codeid
        return self.rel_esdid
    def getResID(self):
        # This method returns the local id of the section in which this
        # relocation item phyiscally resides
        return self.pos_esdid
    def getResOff(self,base=0):
        # Return the offset into the section in which the address constant
        # resides.  objutil will provide the section's base for use by 
        # this method.  The object format may not require it.
        #
        # RLD items generated by z390 contain in the RLD address field an
        # offset into the section where the address constant resides.
        # This may not be consistent with HLASM - requires further research
        return self.address-base
    def getRmode(self):
        # Returns the residency mode of this section.
        return self.rmode
    def getRtype(self):
        # Return the relocation type of this address constant.  The algorithm
        # is determined by the length, so return the length for type
        return self.length
    def getSize(self):
        # Return the physical size of the address constant residing in the
        # section
        return self.length

class RI(rlditem):
    # Relative immediate value
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        rlditem.__init__(self,addr,rel_esdid,pos_esdid,length,direction)

class A(rlditem):
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        rlditem.__init__(self,addr,rel_esdid,pos_esdid,length,direction)

class CXD(rlditem):
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        rlditem.__init__(self,addr,rel_esdid,pos_esdid,length,direction)

class Q(rlditem):
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        rlditem.__init__(self,addr,rel_esdid,pos_esdid,length,direction)

class V(rlditem):
    def __init__(self,addr,rel_esdid,pos_esdid,length,direction):
        rlditem.__init__(self,addr,rel_esdid,pos_esdid,length,direction)

# Initailize pythonize class variables
pythonize.init()

if __name__=="__main__":
   args=sys.argv
   if len(args)<3:
       print("Usage: OBJO.py [deck|dump|print| objofile")
       sys.exit(1)
   recs=pythonize.deck(args[2])
   obj=objo.pythonize(recs)
   if args[1]=="deck":
       for x in recs:
           print(x)
       sys.exit(0)
   if args[1]=="print":
       print(obj)
       sys.exit(0)
   if args[1]=="dump":
       print(obj.hexdump())
       sys.exit(0)
   print("Invalid option: %s" % args[1])
   sys.exit(1)
       