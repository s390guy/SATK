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

# Utility to handle the emulation of "records" and "sequential files" 
# in Python.  The utility includes a class that encapsulates and provides the
# utility functions provided.
#
# A set of records is a list consisting of a series of string or bytearray 
# instances.
#
# This module is one of a number of modules that support Hercules emulated
# device media:
#    recsutil.py   This module. Python classes for individual records targeted
#                  to a device type: card, tape, fba or ckd
#    media.py      instances of media records are converted to emulated 
#                  media: card images, AWS tape image file, FBA image file 
#                  or CKD image file.  All image files are uncompressed.
#    rdrpun.py     Handles writing and reading card decks.
#    awsutil.py    Handles writing and reading AWS tape image files.
#    fbautil.py    Handles writing and reading of FBA image files.
#    ckdutil.py    Handles writing and reading of CKD image files.
#
# See media.py for creation of device-specific records in Python
#
# When executed from a scipt or command line, a set of card records will
# be converted to a Python module.

import hexdump       # Access the dump utility
import os.path       # Access to OS file system methods and attributes
import sys           # Access to system atributes

class rec(object):
    # This class is the superclass of all media record types
    #
    # rec Static Methods
    #   check       Raises a TypeError if a data argument is not a string
    #   hex_string  Formats an arbitrary binary string into hex characters
    #   init        Initializes the rectypes dictionary
    #   pad_trunc   Pads or truncates a string to required length
    #
    # rec Factory Static Methods
    #   instance    Creates a subclass instance of rec from a record-tuple. 
    #               The inverse of rec.tuplize()
    #
    # rec Instance Methods
    #   tuplize     Converts a rec instance into a record-tuple.  The inverse
    #               of rec.instance()
    #
    # rec Required Subclass Interface methods
    #   pythonize   Create a string from which the record can be instantiated
    rectypes={}   # Maps record id types to a rec subclass. Set by rec.init()
    devtypes={}   # Maps record class names to class objects
    def check(rec):
        # Check that a record content is a string
        # Bytearrays must be converted to strings before being used with
        # recsutil.py
        if type(rec)!=type(""):
            raise TypeError("not a string: %s" % type(rec))
    check=staticmethod(check)
    def hex_string(hdr="",string="",append="",end="",header=True):
        linindent=" "*(len(append))
        endpad=" "*(len(end)-1)
        rec=bytearray(string)
        if header:
            if len(hdr)==0:
                rechdr="#"
                hdrindent=linindent[:-2]
            else:
                rechdr=hdr
                hdrindent=linindent
            if len(rechdr)>0 and rechdr[-1]=="\n":
                rechdr=rechdr[:-1]
            rechdr=rechdr+hdrindent+" "
            rechdr="%s   .0  .1  .2  .3  .4  .5  .6  .7  .8" \
                % rechdr[:len(linindent)+1]
            rechdr="%s  .9  .A  .B  .C  .D  .E  .F\n" % rechdr
        str='%s%s' % (rechdr,append)
        reclen=len(rec)
        for y in range(0,reclen-1,16):
            if y==0:
                indent=""
            else:
                indent=linindent
            lineend="# 0x%X" % y
            if y+16<reclen:
                part=rec[y:y+16]
                linend=",%s %s\n" % (endpad,lineend)
            else:
                # Last part of record
                part=rec[y:]
                linend="%s %s\n" % (end,lineend)
            dblquad=""
            for z in range(len(part)):
                dblquad="%s\\x%02X" % (dblquad,part[z])
            str='%s%s"%s"%s' % (str,indent,dblquad,linend)
        return str
    hex_string=staticmethod(hex_string)
    def init():
        # The first element of a record tuple defines the type of record
        # the tuple specifies.  This element's Python type is mapped to 
        # a recsutil class object here.
        rec.rectypes[type(None)]=card
        rec.rectypes[type("")]=tape
        rec.rectypes[type(0)]=fba
        rec.rectypes[type((None))]=ckd
        # Each device handler module in its device specific class will
        # define a string attribute: record.  The record attribute string is
        # mapped to a recsutil class object here.
        rec.devtypes["card"]=card
        rec.devtypes["tape"]=tape
        rec.devtypes["tm"]=tape
        rec.devtypes["fba"]=fba
        rec.devtypes["ckd"]=ckd
    init=staticmethod(init)
    def instance(rectuple):
        if type(rectuple)!=type((None)):
            raise TypeError("record-tuple not a tuple: %s" % type(rectuple))
        if len(rectuple)!=2:
            raise TypeError("record-tuple may contain only two values: %s" \
                % len(rectuple))
        try:
            cls=rec.rectypes[rectuple[0]]
        except KeyError:
            raise TypeError("tuple[0] type unrecognized: %s" \
                % type(rectuple[0]))
        return cls.detuple(rectuple)
    instance=staticmethod(instance)
    def pad_trunc(data,length,pad="\x00"):
        # Pad or truncate a string
        if len(data)<length:
            return data+(length-len(data))*pad
        return data[:length]
    pad_trunc=staticmethod(pad_trunc)
    def __init__(self,recid=None,data=""):
        self.recid=recid
        self.content=data
    def dump(self,*args,**kwds):
        raise NotImplementedError(\
            "class %s must implement dump() method" \
            % self.__class__.__name__)
    def pythonize(self,*args,**kwds):
        raise NotImplementedError(\
            "class %s must implement pythonize() method" \
            % self.__class__.__name__)
    def tuplize(self):
        return (self.recid,self.data)

class card(rec):
    strict=True    # Global switch for padding or truncating card records
    def detuple(rectuple):
        # Convert a card record-tuple into a card instance
        return card(rectuple[1])
    detuple=staticmethod(detuple)
    def __init__(self,data=""):
        rec.check(data)
        if card.strict and len(data)!=80:
            raise ValueError("card record must be 80 bytes: %s" % len(data))
        rec.__init__(self,None,rec.pad_trunc(data,80,"\x40"))
    def __str__(self):
        return "80-byte card image"
    def dump(self):
        return "Card\n%s" \
            % (hexdump.dump(self.content,start=0,indent="   ")) 
    def pythonize(self,hdr="",append="",indent=""):
        myappend='%scard(data="".join([' % append
        myend="]))"
        python=rec.hex_string(\
            hdr=hdr,
            append=myappend,\
            string=self.content,\
            end=myend)
        return python[:-1]

class tape(rec):
    def detuple(rectuple):
        # Convert a tape record-tuple into a tape instance
        if rectuple[0]=="BLOCK":
            return tape(data=rectuple[1])
        if rectuple[0]=="TM":
            return tm()
        raise ValueErrro("unrecognized tape record-tuple: %s" % rectuple[0])
    detuple=staticmethod(detuple)
    def __init__(self,data="",recid="BLOCK"):
        rec.check(data)
        rec.__init__(self,recid=recid,data=data)
    def __str__(self):
        return "tape id=%s: length=%s" % (self.recid,len(self.content))
    def dump(self):
        if self.tm:
            return "Tape Mark"
        return "Tape block\n%s" \
            % (hexdump.dump(self.content,start=0,indent="   ")) 
    @property
    def tm(self):
        return len(self.content)==0
    def pythonize(self,hdr="",append="",indent=""):
        myappend='%stape(data="".join([' % append
        myend="]))"
        python=rec.hex_string(\
            hdr=hdr,
            append=myappend,\
            string=self.content,\
            end=myend)
        return python[:-1]

class tm(tape):
    def __init__(self):
        tape.__init__(self,recid="TM",data="")
    def pythonize(self,hdr="",append="",indent=""):
        return "%s%stm()" % (hdr,append)

class fba(rec):
    strict=True    # Global switch for padding or truncating fba sectors
    def detuple(rectuple):
        # Convert a fba record-tuple into a fba instance
        return fba(block=rectuple[0],data=rectuple[1])
    detuple=staticmethod(detuple)
    def __init__(self,data="",sector=0):
        rec.check(data)
        if fba.strict and len(data)!=512:
            raise ValueError("fba sector must be 512 bytes: %s" % len(data))
        rec.__init__(self,recid=sector,data=rec.pad_trunc(data,512,"\x00"))
        self.sector=sector
    def __cmp__(self,other):
        # Compare two fba instances
        if self.sector<other.sector:
            return -1
        if self.sector>other.sector:
            return 1
        return 0
    def __str__(self):
        return "recsutil.py fba sector=%s len(data)=%s" \
            % (self.sector,len(self.content))
    def dump(self):
        return "FBA sector %s\n%s" \
            % (self.sector,hexdump.dump(self.content,start=0,indent="   ")) 
    def pythonize(self,hdr="",append="",indent=""):
        myappend='%sfba(data="".join([' % append
        myend="]),sector=%s)" % self.sector
        python=rec.hex_string(\
            hdr=hdr,
            append=myappend,\
            string=self.content,\
            end=myend)
        return python[:-1]

class ckd(rec):
    #
    # Count-Key-Data DASD device record class
    #
    # ckd Factory Static methods
    #   detuple    Converts a ckd record-tuple into a ckd instance
    #
    # ckd Instance Properties
    #   RO  eof    Returns True is the record is an end-of-file record
    strict=True   # Global switch for enabling padding and truncating
    def detuple(rectuple):
        # Convert a ckd record-tuple into a ckd instance
        ID=rectuple[0]
        if len(ID)!=5:
            raise TypeError("ckd record tuple ID invalid: %s" % ID)
        if len(rectuple[1])==0:
            return eof(cc=ID[0],hh=ID[1],r=ID[2])
        data=rectuple[1]
        key=data[:ID[3]]
        data=data[ID[3]:ID[3]+ID[4]]
        return ckd(data=data,key=key,cc=ID[0],hh=ID[1],r=ID[2])
    detuple=staticmethod(detuple)
    def __init__(self,data="",key="",cc=0,hh=0,r=1):
        rec.check(data)
        rec.check(key)
        if len(key)>255:
            raise ValueError("ckd key length greater than 255: %s" % len(key))
        rec.__init__(self,recid=(cc,hh,r,len(key),len(data)),data=key+data)
        self.cc=cc
        self.hh=hh
        self.r=r
        self.key=key
        self.data=data
    def __str__(self):
        return "ckd record: data_len(%s),key_len(%s) @ CC=%s,HH=%s,R=%s" \
            % (len(self.data),len(self.key),self.cc,self.hh,self.r)
    def __cmp__(self,other):
        # Perform ckd record comparison
        if self.cc<other.cc:
            return -1
        if self.cc>other.cc:
            return 1
        if self.hh<other.hh:
            return -1
        if self.hh>other.hh:
            return 1
        if self.r<other.r:
            return -1
        if self.r>other.r:
            return 1
        return 0
    def dump(self):
        return "CKD record CC=%s, HH=%s, R=%s: "\
            "key_length(%s), data_length(%s)\n%s" \
            % (self.cc,self.hh,self.r,len(self.key),len(self.data),\
                hexdump.dump(self.content,start=0,indent="   ")) 
    @property
    def eof(self):
        return len(recdata)==0
    def pythonize(self,hdr="",append="",indent=""):
        python=hdr
        if len(self.key)>0:
            keydata=rec.hex_string(\
                append='k="".join([',\
                string=self.key,\
                end="])")
            python="%s%s" % (python,keydata)
            key="k"
        else:
            key='""'
        data=rec.hex_string(\
            append='d="".join([',\
            string=self.data,\
            end="])")
        python="%s%s" % (python,data)
        python="%s%sckd(data=d,key=%s,cc=%s,hh=%s,r=%s)" \
            % (python,append,key,self.cc,self.hh,self.r)
        return python

class eof(ckd):
    def __init__(self,cc=0,hh=0,r=1):
        ckd.__init__(self,data="",key="",cc=cc,hh=hh,r=r)
    def pythonize(self,hdr="",append="",indent=""):
        return "%s%seof(cc=%s,hh=%s,r=%s)" \
            % (hdr,append,self.cc,self.hh,self.r)

rec.init()

class recs(object):
    # class abstracting a record sequence.
    #
    # rec Factory Static methods:
    #    Cards      Converts a string or bytearray into a sequence of card 
    #               80-byte records
    #    Card2Tape  Converts a string or bytearray into a sequence of card
    #               images as tape records.
    #    Recs       Converts a list of record-tuples into a list of rec 
    #               instances
    def Cards(string):
        lst=[]
        for x in range(0,len(string)-1,80):
            lst.append(card(data=string[x:x+80]))
        return recs(lst)
    Cards=staticmethod(Cards)
    def Cards2Tape(string):
        lst=[]
        for x in range(0,len(string)-1,80):
            lst.append(tape(data=string[x:x+80]))
        lst.append(tm())
        lst.append(tm())
        return recs(lst)
    def isRec(record):
        if not isinstance(record,rec):
            raise TypeError()
        return record
    isRec=staticmethod(isRec)
    def isRecs(construct):
        # Validates that an argument constitutes a valid list class rec
        # instances.  Raises a ValueError if not.
        if type(construct)!=type([]):
            raise TypeError("not a list: %s" % construct)
        for x in range(len(construct)):
            rec=construct[x]
            try:
                recs.isRec(rec)
            except TypeError:
                raise ValueError(\
                    "record instance %s not a rec instance: %s" \
                    % (x,type(rec)))
        return construct
    isRecs=staticmethod(isRecs)
    def Recs(lst):
        rec_lst=[]
        for x in lst:
            rec_lst.append(rec.instance(x))
        return recs(rec_lst)
    Recs=staticmethod(Recs)
    def Strings(lst):
        # Create a recs instance of strings from a list
        return recs(lst).strings()
    Strings=staticmethod(Strings)
    def __init__(self,lst=[]):
        self.records=recs.isRecs(lst)
    def append(self,rec):
        # Add a record to the list
        self.records.append(recs.isRec(rec))
    def pythonize(self,module,listname="records"):
        # This method returns a string that constitutes a module 
        # that may be imported.  The module creates a list of rec instances
        # as specified in the file and each rec instance is appended to list
        # named records by default.
        #
        # The module would be used as follows
        #
        #    import recsutil         # Import this module for use
        #    import module           # Import the module of rec instances
        #    l=module.records        # the list of rec instances from module
        #    recs=recsutil.recs(l)   # the entire module encapsulated here
        #
        # Generate the module's header lines
        str="#!/usr/bin/python\n"
        str="%s# %s was generated by recsutil.py\n\n" % (str,module)
        str="%simport recsutil       # Make record classes available\n\n" \
            % str
        str="%s%s=[]\n" % (str,listname)
        #
        # Generate the individual rec instances in the module
        assign="r="
        numrec=len(self.records)
        for x in range(numrec):
            rechdr="\n# Record %s\n" % (x+1)
            instance=self.records[x].pythonize(hdr=rechdr,append=assign)
            str="%s%s\n%s.append(r)\n" % (str,instance,listname)
        return str

def convert(filename,modfile,listname,display=False):
    fo=open(filename,"rb")
    ldr=fo.read()
    fo.close()
    rec=recs.Cards(ldr)
    sep=os.path.split(modfile)
    modname=sep[1]
    rec=rec.pythonize(modname,listname)
    if display:
        print rec
    fo=open(modname,"wb")
    fo.write(rec)
    fo.close()

def test_formats():
    fba.strict=False
    fba_recs=recs([fba(data="some fba data",sector=10)])
    fba_mod=fba_recs.pythonize("fbamod","fbarecs")
    print fba_mod
    r=[]
    r.append(ckd(data="some ckd data",cc=0,hh=0,r=1))
    r.append(ckd(data="a vol1 lable",key="VOL1",cc=0,hh=0,r=2))
    r.append(eof(cc=0,hh=1,r=1))
    ckd_recs=recs(r)
    ckd_mod=ckd_recs.pythonize("ckdmod","ckdrecs")
    print ckd_mod

def usage():
    return "./recsutil.py infile outmodule outlist"

if __name__=="__main__":
    if len(sys.argv)==1:
        test_formats()
        convert("/home/harold/SATK/loaders/bin/3cards370.ldr",\
            "/home/harold/SATK/loaders/python/cards370.py",\
            "cardldr",True)
        sys.exit(0)
    if len(sys.argv)!=4:
        convert(sys.argv[1],sys.argv[2],sys.argv[3])
        sys.exit(0)
    print usage()
    sys.exit(1)
