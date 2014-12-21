#!/usr/bin/python3.3
# Copyright (C) 2014 Harold Grovesteen
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

# NOTICES:
# IBM and z/OS are registered trademarks of International Business Machines
# Corporation.

this_module="xmi.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2014")

# This module extracts a file from an XMI format file.  Presently only a single
# PDS and its members are supported.
#
# XMI is a format used by by IBM(R).  The basis for the structure used in this file
# is documented in the manual "IBM z/OS(R) TSO/E Customization Version 2 Release 1",
# SA32-0976-00, chapter 39, sections "Test units and text unit pointer sets", pages
# 500-507, and "Format of transmitted data", pages 508-512.  The format is heavily
# tied to the TSO transmit and receive processes.  See the comments at the end of the
# file describing the file formats and data relationships.  Refer to specific objects
# for details concerning actual structures.
#
# The XMI format is used by www.cbttape.org files containing a "transmitted" PDS.

# Python imports
import os
import os.path
#import sys
import argparse

# SATK imports
import satkutil

# Setup PYTHONPATH
satkutil.pythonpath("tools/ipl")
from hexdump import dump


#
# +-----------------------------------+
# |                                   |
# |   Generic End-of-File Exception   |
# |                                   |
# +-----------------------------------+
#

# This exception is raised when an end-of-file condition is reached.  Context
# dictates the condition(s) that cause it to be raised
class EOF(Exception):
    def __init__(self):
        super().__init__()



#
# +----------------------------------+
# |                                  |
# |   Binary Data Access Functions   |
# |                                  |
# +----------------------------------+
#

def bigend(bdata,loc,length):
    return int.from_bytes(bdata[loc:loc+length],byteorder="big",signed=False)

def bstr(bdata):
    return satkutil.byte2str(bdata)

def b3(bdata,loc):
    return bigend(bdata,loc,3)

def hw(bdata,loc):
    return bigend(bdata,loc,2)

def fw(bdata,loc):
    return bigend(bdata,loc,4)
    
#
# +----------------------------+
# |                            |
# |   Command-line Processor   |
# |                            |
# +----------------------------+
#

class EXTRACT(object):
    def __init__(self,args):
        self.args=args

        # Produced by run() method
        self.xmifile=None  # --xmi: XMI PDS being processed
        self.wrdir=None    # --dir: Directory into which members are written 
        self.pds=None      # PDS object produced from the XMI data
        self.lrecl=None    # Logical record size in PDS
        self.ds=None       # DATASET object used to access members
        
        # Established by write() method
        # --ext: file name extension for text files. 
        # bin used for all --format image files.
        self.ext=None

    def display(self):
        members=self.args.member
        if len(members)==0:
            self.pds.ds.dir_info(pr=True)
            return
        # member name(s) supplied on command line
        for member in members:
            try:
                data=self.format(member)
            except KeyError:
                print("%s member not found")
                continue
            print(data)

    # Retrieves and formats for listing a member
    # Exception: KeyError if member not found
    def format(self,member):
        mem=self.ds.member(member,"ascii")
        data="\n%s" % member
        for n,line in enumerate(mem):
                lineno=n+1
                num="[%s]" % lineno
                num=num.ljust(6)
                data="%s\n    %s %s" % (data,num,line)
        return data

    # List the directory and all members to a file
    def listing(self,filename):
        members=self.args.member

        # If no member names supplied on command line, write out all of them
        if len(members)==0:
            members=self.ds.dir_all()

        try:
            fo=open(filename,"wt")
        except IOError:
            print("could not open for writing listing file: %s" % filename)
            return

        # Write out the directory
        fo.write(self.ds.dir_info())
        fo.write("\n\n")
        
        # Write out all of the members
        for mem in members:
            member=self.format(mem)
            try:
                fo.write(member)
            except IOError:
                print("aborting: could not write member %s to listing file: %s" \
                    % (mem,filename))
            fo.write("\n")

        try:
            fo.close()
        except IOError:
            print("failed to close listing file: %s" % filename)

    # Run the XMI tool
    def run(self):
        # Validate -d/--dir argument
        wrdir=self.args.dir
        if wrdir:
            if not os.path.isdir(wrdir):
                print("ERROR: -d/--dir argument not a directory: %s" % wrdir)
                return
            self.wrdir=wrdir     # Directory into which members are written

        print("XMI File: %s" % self.args.xmi)
        self.xmifile=XMIFILE(self.args.xmi)

        # Process XMI segments into logical records
        self.xmifile.segments(inventory=False)

        # Create the "PDS" from the logical data records
        self.pds=self.xmifile.isPDS()  # PDS object from XMIFILE
        self.pds.build(rdtl=False)     # Create the DATASET object
        self.lrecl=self.pds.r1.lrecl   # PDS logical record length
        self.ds=self.pds.ds            # DATASET object from PDS

        # --list command-line argument processing
        if self.args.list:
            self.listing(self.args.list)
            return

        # --pds command-line argument processing
        if self.args.pds:
            print("PDS Description")
            self.pds.r1.dev_info(indent="    ",pr=True)
            self.pds.r1.ds_info(indent="    ",pr=True)
            self.pds.exts.info(indent="    ",pr=True)

        if self.wrdir is None:
            # member processing without --dir command line argument
            self.display()
        else:
            # member processing with --dir command line argument
            self.write()

    def write(self):
        members=self.args.member

        # If no member names supplied on command line, write out all of them
        if len(members)==0:
            members=self.ds.dir_all()

        fmt=self.args.format
        if fmt!="image":
            if self.lrecl!=80:
                print("ERROR: --format %s not valid for PDS LRECL %s, use --format " 
                    "image" % (fmt,self.lrecl))
                return
            ext=self.args.ext
            fmode="wt"
        else:
            ext="bin"
            fmode="wb"
            
        for member in members:
            # Constuct the file path
            fname=os.extsep.join([member,ext])
            fpath=os.path.join(self.wrdir,fname)
            
            try:
                recs=self.ds.member(member,fmt)
            except KeyError:
                print("%s member not found")
                continue
                
            try:
                fo=open(fpath,fmode)
            except IOError:
                print("ERROR: could not open member %s  file for writing in "
                    "format '%s' file: %s" % (member,fmt,fpath))
                return

            try:
                if fmt=="image":
                    for rec in recs:
                        fo.write(rec)
                else:
                    fdata="\n".join(recs)
                    fo.write(fdata)
            except IOError:
                print("ERROR: occurred writing member %s file: %s" \
                    % (member,fpath))
            
            try:
                fo.close()
            except IOError:
                print("ERROR: could not close member %s file: %s" \
                    % (member,fpath))
            
            
                
                

#
# +----------------------+
# |                      |
# |   XMI File Objects   |
# |                      |
# +----------------------+
#

# Base class for control record objects
class CtlRec(object):
    # Formats used:
    #  C - 1 EBCDIC characters
    #  D - Dataset organization
    #  F - Dataset Name
    #  N - 1 numeric
    #  R - Record format
    #  T - Dataset Type
    keys={0x0030:("INMBLKSZ","N"),
          0x1022:("INMCREAT","C"),
          0x0001:("INMDDNAM","C"),
          0x000C:("INMDIR","N"),
          0x0002:("INMDSNAM","F"),
          0x003C:("INMDSORG","D"),
          0x8028:("INMEATTR","N"),
          0x1027:("INMERRCD","C"),
          0x0022:("INMEXPDT","C"),
          0x1026:("INMFACK",None),
          0x102D:("INMFFM","C"),
          0x1011:("INMFNODE","C"),
          0X1024:("INMFTIME","C"),
          0x1012:("INMFUID","C"),
          0x1023:("INMFVERS","N"),
          0x1021:("INMLCHG","C"),
          0x0042:("INMLRECL","N"),
          0x1020:("INMLREF","C"),
          0x8018:("INMLSIZE","N"),
          0x0003:("INMMEMBR",None),
          0x102F:("INMNUMF","N"),
          0x102A:("INMRECCT","N"),
          0x0049:("INMRECFM","R"),
          0x000B:("INMSECND","N"),
          0x102C:("INMSIZE","N"),
          0x0028:("INMTERM",None),
          0x1001:("INMTNODE","C"),
          0X1025:("INMTTIME","C"),
          0x1002:("INMTUID","C"),
          0x8012:("INMTYPE","T"),
          0x1029:("INMUSERP","C"),
          0x1028:("INMUTILN","C")}
          
    def __init__(self,ctlid,recdata,debug=False):
        self.ctlid=ctlid
        self.recdata=recdata   # Bytes list of recdata
        if __debug__:
            if debug:
                print("%s:\n%s" % (self.ctlid,dump(self.recdata,indent="    ")))

        self.tus=[]
        self.pos=6   # Start analyzing control record after the ID
        self.error=False
        self.attr={}  # Dictionary of attributes derived from text units
        self.tucls={"C":TextUnitChr,
                    "D":TextUnitDSORG,
                    "F":TextUnitFile,
                    "N":TextUnitDec,
                    "R":TextUnitRECFM,
                    "T":TextUnitFileType}
        self.TextUnits(debug=debug)  # Populate the attribute dictionary

    def fetch_data(self,bytes):
        beg=self.pos
        end=beg+bytes
        if end>len(self.recdata):
            raise ValueError
        data=self.recdata[beg:end]
        self.pos+=bytes
        return data

    def fetch_hw(self):
        hw=self.fetch_data(2)
        return int.from_bytes(hw,byteorder="big",signed=False)

    def fetch_fw(self):
        fw=self.fetch_data(4)
        return int.from_bytes(fw,byteorder="big",signed=False)

    def info(self,tu=False,pr=False):
         if self.error:
              er=" ERROR"
         else:
              er=""
         info="%s%s" % (self.ctlid,er)
         if tu:
             for n,tu in enumerate(self.tus):
                 tu="    %s %s" % (n+1,tu.info())
                 info="%s\n%s" % (info,tu)
         for name in sorted(self.attr.keys()):
             value=self.attr[name]
             value=value.display()
             info="%s\n    %s :%s" % (info,name.ljust(8),value)
         if pr:
             print(info)
             return
         return info

    def TextUnits(self,debug=False):
        try:
            while True:
                # List of bytes corresponding to the data in each length/data pair
                state=0   # Reading key --- this is the only valid point for ending
                pairs=[]
                key=self.fetch_hw()
                if __debug__:
                    if debug:
                        print("Key: %04X" % key)
                state=1   # Reading number of length/data pairs
                num_pairs=self.fetch_hw()
                if __debug__:
                    if debug:
                        print("Length/Data pairs: %s" % num_pairs)
                state=2   # Reading pairs
                for n in range(num_pairs):
                    length=self.fetch_hw()
                    if __debug__:
                        if debug:
                            print("Length %s: %s" % (len(pairs)+1,length))
                    data=self.fetch_data(length)
                    if __debug__:
                        if debug:
                            print("Data %s: %s" % (len(pairs)+1,data))
                    pairs.append(data)

                keyname,format=CtlRec.keys[key]
                try:
                    tucls=self.tucls[format]
                    tu=tucls(key,pairs)
                except KeyError:
                    raise ValueError("unrecognized text unit type: %s" % format)
                    tu=TextUnit(key,pairs)
                self.tus.append(tu)
        except ValueError:
            if state != 0:
                self.error=True
                if state==1:
                    print("%s @%04X failed to read text unit %s key"\
                        % (self.ctlid,self.pos,len(self.tus)+1))
                elif state==2:
                    print("%s @%04X failed to read text unit %s number of length/data "
                        "pairs" % (self.ctlid,self.pos,len(self.tus)+1))
                elif state==3:
                    print("%s @%04X failed to read text unit %s length/data pair %s" \
                        % (self.ctld,self.pos,len(self.tus)+1,len(pairs)+1))
                else:
                    print("@%04X unrecgonized state %s")

        for tu in self.tus:
            #self.attr[tu.keyname]=tu.value()
            self.attr[tu.keyname]=tu

        if __debug__:
            if debug:
                self.info(pr=True)


class INMR01(CtlRec):
    def __init__(self,recdata,debug=False):
        super().__init__("INMR01",recdata,debug=debug)


class INMR02(CtlRec):
    def __init__(self,recdata,debug=False):
        self.fileno=None
        super().__init__("INMR02",recdata,debug=debug)
    def info(self,tu=False,pr=False):
        info=super().info(tu=tu)
        info="%s\n    File #: %s" % (info,self.fileno)
        if pr:
            print(info)
            return
        return info
    def TextUnits(self,debug=False):
        try:
            self.fileno=self.fetch_fw()
        except ValueError:
            print("could read file number from record data")
            return
        super().TextUnits(debug=debug)


class INMR03(CtlRec):
    def __init__(self,recdata,debug=False):
        super().__init__("INMR03",recdata,debug=debug)


class INMR04(CtlRec):
    def __init__(self,recdata,debug=False):
        super().__init__("INMR04",recdata,debug=debug)


class INMR06(CtlRec):
    def __init__(self,recdata,debug=False):
        super().__init__("INMR06",recdata,debug=debug)
    def TextUnits(self,debug=False):
        # This control record has no text units
        pass


class INMR07(CtlRec):
    def __init__(self,recdata,debug=False):
        super().__init__("INMR07",recdata,debug=debug)


class TextUnit(object):
    # Key is the TextUnit Key
    # Pairs is a list of data items (bytes) from length/data pairs of text unit
    # The meaning of the data is dependent upon the Key
    def __init__(self,key,pairs):
        self.key=key
        self.pairs=pairs
        self.keyname,self.format=CtlRec.keys[self.key]

    # Validates that their are the required number of pairs.  The individual byte
    # or bytes are returned.
    # If the number of pairs do not match, then a ValueError is raised
    def check_pairs(self,typ,number):
        if len(self.pairs)!=number:
            raise ValueError("Type %s requires %s length/data pair, found: %s" \
                % (typ,number,len(self.pairs)))
        if number==1:
            return self.pairs[0]
        return self.pairs[0:number]

    # Validates that a pair's length is as required.  The individual byte
    # or bytes are returned.
    # If the length of the pair is invalid, then a ValueError is raised
    def check_pair_length(self,data,typ,length):
        if len(data)!=length:
            raise ValueError("Type %s requires %s bytes of data, found: %s" \
                % (typ,length,len(data)))

    def display(self):
        raise NotImplementedError("subclass %s must provide display() method" \
            % self.__class__.__name__)

    def info(self,pr=False):
        info="Key:%04X %s Data items:%s " \
            % (self.key,self.keyname.ljust(8),len(self.pairs))
        if pr:
            print(info)
            return
        return info

    def value(self):
        raise NotImplementedError("subclass %s must provide value() method" \
            % self.__class__.__name__)


class TextUnitChr(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        return self.val

    def value(self):
        data=self.check_pairs("C",1)
        return data.decode("cp037")


class TextUnitDec(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        return "%s (0x%X)" % (self.val,self.val)

    def value(self):
        data=self.check_pairs("N",1)
        if len(data)>8:
            data=data[-8:]
        return int.from_bytes(data,byteorder="big",signed=False)


class TextUnitDSORG(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        if self.val== 0x0008:
            org="VSAM"
        elif self.val == 0x0200:
            org="PDS"
        elif self.val == 0x4000:
            org="SEQ"
        else:
            org="?"
        return "0x%04X (%s)" % (self.val,org)

    def value(self):
        data=self.check_pairs("D",1)
        self.check_pair_length(data,"D",2)
        return int.from_bytes(data,byteorder="big",signed=False)


class TextUnitFile(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        return "%s" % self.val

    def value(self):
        data=[]
        for item in self.pairs:
            data.append(item.decode("cp037"))
        data=".".join(data)
        return data


class TextUnitFileType(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        data=self.val
        if data == 0x80:
            desc="DLIB"
        elif data == 0x40:
            desc="PLIB"
        elif data == 0x04:
            desc="XSEQ"
        elif data == 0x01:
            desc="LSEQ"
        else:
            desc="?"
        return "0x%02X (%s)" % (self.val,desc)

    def value(self):
        data=self.check_pairs("T",1)
        self.check_pair_length(data,"T",1)
        return data[0]


class TextUnitRECFM(TextUnit):
    def __init__(self,key,pairs):
        super().__init__(key,pairs)
        self.val=self.value()

    def display(self):
        fmt=self.val
        if fmt==0x0001:
            desc="Short VBS"
        else:
            fv=fmt&0xC000
            if fv == 0xC000:
                fvd="U"
            elif fv == 0x8000:
                fvd="F"
            elif fv == 0x4000:
                fvd="V"
            else:
                fvd="?"
            # Blocked
            if fmt & 0x1000 == 0x1000:
                b="B"
            else:
                b=""
            # Spanned
            if fmt & 0x0800 == 0x0800:
                span="S"
            else:
                span=""
            # RDW
            if fmt & 0x0002 == 0x0002:
                rdw=" w/o RDW"
            else:
                rdw=""
            desc="%s%s%s%s" % (fvd,b,span,rdw)
        return "0x%04X (%s)" % (self.val,desc)

    def value(self):
        data=self.check_pairs("R",1)
        self.check_pair_length(data,"R",2)
        return int.from_bytes(data,byteorder="big",signed=False)


# Object representing an XMI formatted file
class XMIFILE(object):
    def __init__(self,filename,save=False):
        self.filename=filename
        self.eof=False   # Indicates pysical end of file

        # XMISEG objects from which logical records are constructed, is saved
        self.save=save   # If set to True XMISEG objects are preserved, otherwise lost
        self.segs=[]     # XMISEG objects if saved
        self.segcnt=0    # Segements read

        # Logical Records
        self.recs=[]
        self.first=None  # First data record index in self.recs
        self.last=None   # Last data record index in self.recs
        self.currec=None # Current logical record being built from XMISEG objects
        # Logical record read index emulating sequential reading
        # Used by open(), read() and close() methods.  None means "not open"
        self.readndx=None

        # XMI file statistics
        self.flags={}    # Inventory of unique flags found in the file
        self.lengths={}  # Inventory of segment lengths found in the file
        self.orgrec={}   # Inventory of original record lengths
        self.eot=False   # End of transmission
        self.eof=False   # Indicates pysical end of file
        self.filesize=0  # Size of file (based upon original records)

        # XMI Control records
        self.R01=None    # Header Record
        self.R02=[]      # Utility Records
        self.R03=None    # Data Control Record (data records follow)
        self.R04=[]      # User Control Records (ignored by xmi.py)
        self.R06=None    # Trailer Record (ends the transmission - last record)
        self.R07=[]      # Notification Record (not valid for xmi.py)

    # Returns a bytes list from XMIREC object representing a logical _data_ record
    # key starts at 0
    def __getitem__(self,key):
        ndx=self.first+key
        if ndx>self.last:
            raise ValueError("attempting to access beyond last data record (%s): %s" \
                % (self.last,ndx))
        rec=self.recs[ndx]
        if __debug__:
            if rec.n!=ndx:
                raise ValueError("XMIREC index (%s) does not match list: %s" \
                    % (rec.n,ndx))
        return rec.bdata

    def close(self):
        self.readndx=None

    # Handles XMI control records when recognized by XMIREC object
    def control(self,rec):
        ctl=rec.ctlid
        if ctl=="INMR01":
            if self.R01 is None:
                self.R01=rec
            else:
                print("Multiple INMR01 header records encountered")
        elif ctl=="INMR02":
            self.R02.append(rec)
        elif ctl=="INMR03":
            if self.R03 is None:
                self.R03=rec
            else:
                print("Multiple INMR03 data control records encountered")
        elif ctl=="INMR04":
            self.R04.append(rec)
        elif ctl=="INMR06":
            if self.R06 is None:
                self.R06=rec
                self.last=len(self.recs)-1
            else:
                print("Multiple INMR06 trailer records encountered")
        elif ctl=="INMR07":
            self.R07.append(rec)
        else:
            print("Unrecognized control record: %s" % ctl)

    # Display XMI Control Record information
    def controls(self,dump=False):
        if self.R01:
            self.R01.display(binary=dump)
        for rec in self.R02:
            rec.display(binary=dump)
        if self.R03:
            self.R03.display(binary=dump)
        for rec in self.R04:
            rec.display(binary=dump)
        if self.R06:
            self.R06.display(binary=dump)
        if self.R07:
            self.R07.display(binary=dump)

    def dump_rec(self,n):
        if n<1 or n>len(self.recs):
            print("record # out of range (1-%s): %s" % (len(self.recs),n))
            return
        rec=self.recs[n-1]
        print("R#-%s %s" % (n,rec.info()))
        rec.display(binary=True)

    # Examines XMI file for transmission of a single PDS based upon XMI control records
    # Produces a PDS object if XMI file contains the PDS.
    def isPDS(self):
        error=False
        num_files=self.R01["INMNUMF"]
        if num_files != 1:
            print("ERROR: XMI file must contain only 1 file: %s" % num_files)
            error=True
        if (not error) and len(self.R02)!=2:
            print("ERROR: Original file must have been processed by only "
                "two processors: %s" % len(self.R02))
            error=True
        if not error:
            proc1=self.R02[0]
            proc2=self.R02[1]
            process=proc2["INMUTILN"]
            if process != "INMCOPY":
                print("ERROR: second processor not INMCOPY: %s" % process)
                error=True
            process=proc1["INMUTILN"]
            if process != "IEBCOPY":
                print("ERROR: first processor not IEBCOPY: %s" % process)
                error=True
        dsorg=proc1["INMDSORG"]
        if (not error) and dsorg!=0x0200:
            print("ERROR: dataset not PDS")
            error=True
        if error:
            return
        blksiz=proc1["INMBLKSZ"]
        dir_blks=proc1["INMDIR"]
        return PDS(blksiz,dir_blks,self)

    # Emulates file access.  Readys the object for the read() method
    def open(self):
        if self.readndx is None:
            self.readndx=self.first
            return
        raise ValueError("XMIFILE logical record 'file' already open")

    # Reads successive logical data records (XMIREC object).  
    # Exception: Raises EOF exception after last data record has been read
    def read(self):
        ndx=self.readndx
        if ndx>self.last:
            raise EOF()
        rec=self.recs[ndx]
        self.readndx+=1
        return rec

    def record(self,seg,save=False,debug=False):
        if self.currec is None:
            if __debug__:
                if debug:
                    print("R#: %s started" % len(self.recs)+1)
            self.currec=XMIREC()

        # Add the segment to the current logical record being constructed
        self.currec.segment(seg)
        self.eot=self.currec.eot

        # Handle the completed logical record
        if self.currec.complete:
            if __debug__:
                if debug:
                    print("R#: %s completed, %s" \
                        % (len(self.recs)+1,self.currec.info()))
            recsize=len(self.currec.bdata)
            self.filesize+=recsize

            # Inventory the original record sizes
            try:
                size_num=self.orgrec[recsize]
                size_num+=1
            except KeyError:
                size_num=1
            self.orgrec[recsize]=size_num

            if self.currec.isctl:
                # Gather control records when encountered
                self.control(self.currec)
            else:
                # Remember where first data record is in list
                if self.first is None:
                    self.first=len(self.recs)

            # Add the record to the list
            self.currec.n=len(self.recs)
            self.recs.append(self.currec)
            self.currec=None

    def records(self,all=False,summary=True,limit=None):
        for n,rec in enumerate(self.recs):
            if all:
                print("R#-%s %s" % (n+1,rec.info(flags=True)))
            if summary:
                continue
            if rec.isctl:
                print(rec.ctlobj.info())
            else:
                if limit and n>limit:
                    continue
                rec.dump()

    def segments(self,limit=None,inventory=False,debug=False):
        fo=self.fo=open(self.filename,"rb")

        save=self.save
        while True:
            seg=fo.read(1)
            # seg is a byte list of 1 byte
            if len(seg)==0:
                # Expected end of file
                self.eof=True
                break
            seg=seg[0]
            
            # Inventory the segment lengths found
            try:
                segn=self.lengths[seg]
                segn+=1
            except KeyError:
                segn=1
            self.lengths[seg]=segn
            
            flags=fo.read(1)
            if len(flags)==0:
                self.eof=True
                print("WARNING: EOF unexpected when reading segment flag")
                break
            flags=flags[0]
            
            # Inventory the flags found
            try:
                nflag=self.flags[flags]
                nflag+=1
            except KeyError:
                nflag=1
            self.flags[flags]=nflag
                
            datalen=seg-2
            if not datalen:
                data=None
            else:
                data=fo.read(datalen)
                if len(data)!=datalen:
                    print("WARNING: EOF unexpected when reading segment data")
                    self.eof=True
                    break

            # Build the XMISEG object
            segment=XMISEG(len(self.segs),seg,flags,data)
            self.segcnt+=1
            if __debug__:
                if debug:
                    segment.info(flags=True,pr=True)

            if self.save:
                self.segs.append(segment)
            self.record(segment,save=save)
            
            if __debug__:
                if limit:
                    if len(self.segs)>limit:
                        break

            # Stop reading any data once the EOT control record (INMR06) encountered
            if self.eot:
                break

        self.fo.close()
        if not self.eot:
            print("INFO: No end-of-transmission (INMR06) control record")
        #if not self.eof:
            # Extra data in the last card image is normal, do not issue warning
            #print("WARNING: data following end-of-transmission (INMR06) control "
            #    "record ignored")

        # Print data about file
        print("XMI file size: %s (0x%X)" % (self.filesize,self.filesize))
        print("XMI segments read: %s" % self.segcnt)
        print("XMI logical records created: %s" % len(self.recs))
        print("XMI logical data records: %s-%s" % (self.first+1,self.last+1))

        if inventory:
            print("Segment lengths found in the file:")
            tot=0
            for key in sorted(self.lengths.keys()):
                l=self.lengths[key]
                tot+=l
                print("    0x%02X %s %s" % (key,key,l))
            print("    Total: %s" % tot)

            print("Flags found in the file:")
            tot=0
            for key in sorted(self.flags.keys()):
                v=self.flags[key]
                tot+=v
                print("    0x%02X %s" % (key,v))
            print("    Total: %s" % tot)

            print("Original record sizes:")
            tot=0
            for key in sorted( self.orgrec.keys()):
                v=self.orgrec[key]
                tot+=v
                print("    0x%X %s %s" % (key,key,v))
            print("    Total: %s" % tot)

# Logical XMI Record
class XMIREC(object):
    ctlcls={"INMR01":INMR01,
            "INMR02":INMR02,
            "INMR03":INMR03,
            "INMR04":INMR04,
            "INMR06":INMR06,
            "INMR07":INMR07}
    def __init__(self):
        self.segs=[]          # Saved by XMIREC.__add() method if save=True
        self.complete=False   # Set by XMIREC.segment() method
        self.bdata=None       # Built by XMIREC.__add() method
        self.n=None           # Set by XMIFILE.record() method

        # Control record related information (established by XMIREC.__ctlid() method)
        self.isctl=False
        self.ctlid=None    # Recognized control record data
        self.eot=False     # This is an EOT (INMR06) control record
        self.ctlobj=None   # Control record object built from control record data

        # Controls handling of different types of segments
        # STATE:
        #   0   Initial state, no segments submitted
        #   1   Expecting middle or last segment, first segment added to record
        #   2   Last segment added (final state)
        self.state=0      # Managed by XMIREC.segment() method

    # Retrieve an attribute value based upon its name
    # May raise a KeyError exception
    def __getitem__(self,key):
        attr=self.ctlobj.attr[key]
        return attr.val

    def __add(self,seg,save=False):
        barray=bytearray(seg.bdata)
        if self.bdata is None:
            self.bdata=barray
        else:
            self.bdata.extend(barray)
        self.isctl = self.ctlid or seg.isctl
        if save:
            self.segs.append(seg)

    def __ctlid(self):
        # Idenfity control record type
        if len(self.bdata)<6:
            return
        # Extract control record ID
        ctlid=self.bdata[:6] 
        # Convert it to ASCII
        ctlid=ctlid.decode("cp037")
        try:
            ctlcls=XMIREC.ctlcls[ctlid]
        except KeyError:
            # Not a recognized control record but segments identified control record
            self.isctl=False
            segn=self.segs[0].n
            print("WARING: Unrecognized control record (segment %s), being "
                "ignored: %s" % (segn,ctlid))
            return
        self.eot = ctlid=="INMR06"
        self.ctlid=ctlid
        self.ctlobj=ctlcls(self.bdata,debug=False)

    def __warning(self,seg,action):
        print("WARNING: STATE %s Segment flags %02X, %s: %s" \
             % (self.state,seg.flags,action,seg.n+1))

    def display(self,binary=False):
        if self.isctl:
            print(self.ctlobj.info())
        else:
            length=len(self.bdata)
            print("data record: recl %s (0x%X)" % (length,length))
        if binary:
            print(dump(self.bdata,indent="    "))

    def dump(self):
        print(dump(self.bdata))
        print("")

    def info(self,flags=False,pr=False):
        info="recl: %s (0x%X)" % (len(self.bdata),len(self.bdata))
        if flags:
            flgdtl="complete:%s eot:%s control:%s" \
                % (self.complete,self.eot,self.isctl)
            if self.isctl:
                flgdtl="%s %s" % (flgdtl,self.ctlid)
            info="%s %s" % (info,flgdtl)
        if pr:
            print(info)
            return
        return info

    def segment(self,seg,save=False):
        if self.state==0:
            # Expecting first segment
            if seg.isonly:
                self.__add(seg,save=save)
                self.state=2
            elif seg.isfirst:
                self.__add(seg,save=save)
                self.state=1
            elif seg.islast:
                self.__warning(seg,"expected first segment, last segment ignored")
            elif seg.ismiddle:
                self.__warning(seg,"expected first segment, middle segment ignored")
            else:
                self.__warning(seg,"expected first segement, unrecognized segment "
                    "ignored")
        elif self.state==1:
            # Expecting middle or last segment
            if seg.isonly:
                self.__warning(seg,"expected middle or last segment, only segment "
                    "ignored")
            elif seg.isfirst:
                self.__warning(seg,"expected middle or last segment, first segment "
                    "ignored")
            elif seg.ismiddle:
                self.__add(seg,save=save)
            elif seg.islast:
                self.__add(seg,save=save)
                self.state=2
        elif self.state==2:
            # Record complete
            if seg.isonly:
                self.__warning(seg,"record complete, only segment ignored")
            elif seg.isfirst:
                self.__warning(seg,"record complete, first segment ignored")
            elif seg.islast:
                self.__warning(seg,"record complete, last segment ignored")
            elif seg.ismiddle:
                self.__warning(seg,"record complete, middle segment ignored")
            else:
                self.__warning(seg,"record complete, unrecognized segment ignored")
        else:
            raise ValueError("unexpected state: %s" % self.state)

        # Determine Control Record ID and whether at end of XMI transmission
        self.complete=self.state == 2
        if self.complete:
            # Convert mutable bytearray into inmutable bytes list.
            self.bdata=bytes(self.bdata)
            # Determine if at EOT
            if self.isctl:
                self.__ctlid()


# Individual XMI Segment
class XMISEG(object):
    def __init__(self,n,length,flags,data):
        self.n=n             # Segment index from zero
        self.length=length   # Segment length as read from the binary file
        self.flags=flags     # Flags as integer read from binary file
        self.bdata=data      # Bytes read from binary file
        self.isonly=(self.flags & 0xC0) == 0xC0    # Is only segment of record
        self.isfirst=(self.flags & 0xC0) == 0x80   # Is first part of original rec.
        self.islast=(self.flags &0xC0) == 0x40     # Is last part of original rec.
        self.ismiddle=(self.flags & 0xC0) == 0x00  # Is middle part of original rec.
        self.isctl=(self.flags & 0x20) == 0x20     # Has control record in segment

    def info(self,flags=False,pr=False):
        if self.length!=len(self.bdata)+2:
            error="*"
        else:
            error=" "
        if self.isctl and len(self.bdata)>=6:
            ctltyp=self.bdata[0:6].decode("cp037")
            ctlrec=": %s" % ctltyp
        else:
            ctlrec=""

        info="[%s] %s%s %2X %s%s" \
            % (self.n,error,self.length,self.flags,len(self.bdata),ctlrec)
        if flags:
            flgdtl="only:%s first:%s middle:%s last:%s ctrl:%s" \
                % (self.isonly,self.isfirst,self.ismiddle,self.islast,self.isctl)
            info="%s %s" % (info,flgdtl)
        if pr:
            print(info)
            return
        return info


# +---------------------------------------+
# |                                       |
# |   Partitioned Dataset (PDS) Objects   |
# |                                       |
# +---------------------------------------+

# Base class for PDS related structures
class structure(object):
    def __init__(self,bdata,ndx=0):
        self.bdata=bdata
        self.ndx=ndx
        
    def dump(self,indent="",pr=False):
        info="%s%s:" % (indent,self.__class__.__name__)
        lcl="%s    " % indent
        info="%s\n%s" % (info,dump(self.bdata,indent=lcl))
        if not pr:
            return info
        print(info)
        
class record(structure):
    def __init__(self,lrec,ndx=0):
        super().__init__(lrec.bdata,ndx=ndx)
        # Convert so recprd number matches XMIFILE.dump_rec() method numbering
        self.xmi_n=lrec.n+1

class CKDREC(record):
    def __init__(self,lrec,ndx,n):
        super().__init__(lrec,ndx)
        if len(self.bdata)<ndx+12:
            raise ValueError("[%s] Incomplete CKD record header" % self.xmi_n)
            
        self.n=n   # Index into list of CKDREC objects of this record

        # Extract header information from logical record
        bdata=self.bdata

        # Header in logical record (12 bytes)
        # Reserved                        +0  4 Reserved
        self.cyl=hw(bdata,ndx+4)        # +4  2 Record Cylinder location
        self.trk=hw(bdata,ndx+6)        # +6  2 Record Track location
        self.rec=bdata[ndx+8]           # +8  1 Record Number on track
        self.klen=bdata[ndx+9]          # +9  1 Record Key length
        self.dlen=hw(bdata,ndx+10)      # +10 2 Record Data length

        self.r0=self.rec==0                # True if track R0 record
        # True if this is an End-of-File Record
        self.eof=(self.dlen+self.klen)==0

        # Indexes into the XMI logical record (self.bdata) used to access differnt
        # pieces of the CKD record.
        #  [self.ndx:self.endndx]     references the entire CKD recor
        #  [self.ndx:self.keyndx]     references just the 12-byte CKD record header
        #  [self.keyndx:self.datandx] references just the key, if any
        #  [self.datandx:self.endndx] references just the data, if any
        self.keyndx=self.ndx+12
        self.datandx=self.keyndx+self.klen
        self.endndx=self.datandx+self.dlen
        
        if self.endndx>len(self.bdata):
            print("WARNING: CKD record extends beyond end of logical record: %s" \
                % self)

    def __str__(self):
        # Accumulate XMI logical record information
        lrloc="[%s:%s]" % (self.ndx,self.endndx)
        info="LR[%s]: len:%5d loc %s" \
            % (self.xmi_n,len(self.bdata),lrloc.ljust(13))
            
        # Accumulate physical CKD record information
        if self.eof:
            eof="*"
        else:
            eof=" "
        info="%s  %sCKD[%s]: P%s" % (info,eof,self.n,self.__ckdaddr().ljust(14))
        klen="%s" % self.klen
        dlen="%s" % self.dlen
        info="%s KEYL %s DATAL %s" % (info,klen.ljust(3),dlen.ljust(5))
        
        # Accumulate record element locations within the logical record
        keyn="%s" % self.keyndx
        datan="%s" % self.datandx
        info="%s  KEY@%s DATA@%s" % (info,keyn.ljust(5),datan.ljust(5))
        return info

    def __ckdaddr(self):
        return "[%s:%s:%s]" % (self.cyl,self.trk,self.rec)
        
    # Returns the CKD record data from the XMI logical record
    def data(self):
        return self.bdata[self.datandx:self.endndx]
        
    # Returns the CKD record key from the XMI logical record
    def key(self):
        return self.bdata[self.keyndx:self.datandx]


class COPY1(record):
    ucbtyps={0x01:"2311",
             0x02:"2301",
             0x03:"2303",
             0x05:"2321",
             0x06:"2305-1",
             0x07:"2305-2",
             0x08:"2314",
             0x09:"3330",
             0x0A:"3340",
             0x0B:"3350",
             0x0C:"3375",
             0x0D:"3330-11",
             0x0E:"3380",
             0x0F:"3390"}
    def __init__(self,lrec):
        super().__init__(lrec)
        if len(self.bdata)<56:
            raise ValueError("[%s] expected at least 56 bytes: %s" \
                % (self.xmi_n,len(bdata)))

        self.error=False   # If True PDS can not be restored by module
        
        # Extract information from logical record
        bdata=self.bdata
        self.uload=bdata[0]               # +0  1 Unload format
        self.copy1id=bstr(bdata[1:4])     # +1  3 Header id
        self.dsraw=bdata[4:6]             # +4  2 Raw dataset org. for __dsorg()
        self.dsorg=hw(bdata,4)            # +4  2 Datset organization
        self.blksiz=hw(bdata,6)           # +6  2 Block size
        self.lrecl=hw(bdata,8)            # +8  2 Logical record length
        self.recfm=bdata[10]              # +10 1 Record format
        self.keylen=bdata[11]             # +11 1 Key length
        self.optcd=bdata[12]              # +12 1 Option codes
        self.sms=bdata[13]                # +13 1 SMS indicators
        self.bkupsz=hw(bdata,14)          # +14 2 Backup block size

        # Original device information
        self.ucbraw=bdata[16:20]          # +16 4 Raw device type for __ucbtyp()
        self.devtype=fw(bdata,16)         # +16 4 Original device type for dev_info()
        self.maxblk=fw(bdata,20)          # +20 4 Maximum block size
        self.cyls=hw(bdata,24)            # +24 2 Cylinders
        self.heads=hw(bdata,26)           # +26 2 Tracks per cylinder
        self.trklen=hw(bdata,28)          # +28 2 Track length
        self.ovrhead=hw(bdata,30)         # +30 2 Block overhead
        self.keyovrhd=bdata[32]           # +32 1 Keyed block overhead
        self.devflgs=bdata[33]            # +33 1 Device flags
        self.tol=hw(bdata,34)             # +34 2 Tolerance factor

        # Backup file information
        self.headers=hw(bdata,36)         # +36 2 Header records (zero means two)
        # reserved                          +38 1

        # Original dataset information
        self.date=b3(bdata,39)            # +39 3 Last reference date
        self.secext=bdata[42:45]          # +42 3 Secondary space extension
        self.secalloc=bdata[45:49]        # +45 4 Secondary allocation
        self.last_ttr=TTR(bdata[49:52])   # +49 3 Last TTR used
        self.last_bal=hw(bdata,52)        # +52 2 Last track balance
        # reserved                        # +54 2

        # Validate this is a IEBCOPY header
        if self.copy1id!="\xCA\x6D\x0F":
            print("logical record 1 not a IEBCOPY header: %s" % self.copy1id)
            self.error=True
        if not (self.headers==2 or self.headers==0):
            print("expected 2 header records: %s" % self.headers)
            self.error=True
        if self.uload != 0:
            print("PDS unload format not valid for restoration")
            self.error=True
        if self.dsorg!=0x0200:
            print("can not process file of dataset org %s" % self.__dsorg())
            self.error=True
        if self.error:
            self.ds_info(indent="    ",pr=True)
            self.dump(pr=True)

    def __dsorg(self):
        org=self.dsraw[0]
        if org & 0x80 == 0x80:
            o="IS"
        elif org & 0x40 == 0x40:
            o="PS"
        elif org & 0x20 == 0x20:
            o="DA"
        elif org & 0x02 == 0x02:
            o="PO"
        else:
            o="?"
        if org & 0x01 == 0x01:
            o="%sU" % o
        return o

    def __recfm(self):
        fm=self.recfm
        f=fm & 0xC0
        if f == 0x40:
            rf="V"
        elif f == 0x80:
            rf="F"
        elif f == 0xC0:
            rf="U"
        else:
            rf="?"
        if fm & 0x20 == 0x20:
            rf="%sT" % rf
        if fm & 0x10 == 0x10:
            rf="%sB" % rf
        if fm & 0x08 == 0x08:
            rf="%sS" % rf
        cc=fm & 0x06
        if cc:
            if cc & 0x04 == 0x04:
                rf="%sA" % rf
            elif cc & 0x02 == 0x02:
                rf="%sM" % rf
            else:
                pass
        return rf

    def __ucbtype(self):
        typ=self.ucbraw
        if typ[2]!=0x20:
            return "?"
        d=typ[3]
        if d == 0x04:
            if typ[1]==0x00:
                return "2302"
            else:
                return "9345"
        try:
            return COPY1.ucbtyps[d]
        except KeyError:
            return "?"

    def dev_info(self,indent="",pr=False):
        info=    "%sDevice Type    %08X (%s)" \
            % (indent,self.devtype,self.__ucbtype())
        info="%s\n%sMaximum Block  %s"     % (info,indent,self.maxblk)
        info="%s\n%sCylinders      %s"     % (info,indent,self.cyls)
        info="%s\n%sTracks/Cyl     %s"     % (info,indent,self.heads)
        info="%s\n%sTrack Length   %s"     % (info,indent,self.trklen)
        info="%s\n%sBlock Overhead %s"     % (info,indent,self.ovrhead)
        info="%s\n%sKeyed Blk Ovr  %s"     % (info,indent,self.keyovrhd)
        info="%s\n%sDevice Flags   0x%02X" % (info,indent,self.devflgs)
        info="%s\n%sTolerance      %s"     % (info,indent,self.tol)
        if not pr:
            return info
        print(info)

    def ds_info(self,indent="",pr=False):
        ufmt=self.uload
        if ufmt & 0x40 == 0x40:
            fmt="PDSE"
        else:
            fmt="PDS"
        if ufmt & 0x80 == 0x80:
            fmt="%s in error" % fmt
        if ufmt & 0x10 == 0x10:
            fmt="%s w/programs" % fmt
        if ufmt & 0x01 == 0x01:
            fmt="%s w/PDSE" % fmt
        info=    "%sUnload Format  0x%02X (%s)" % (indent,self.uload,fmt)
        info="%s\n%sDS Org.        0x%04X (%s)" \
            % (info,indent,self.dsorg,self.__dsorg())
        info="%s\n%sBlock Size     %s (0x%04X)" \
            % (info,indent,self.blksiz,self.blksiz)
        info="%s\n%sRecord Length  %s (0x%04X)" \
            % (info,indent,self.lrecl,self.lrecl)
        info="%s\n%sRecord Format  0x%02X (%s)" \
            % (info,indent,self.recfm,self.__recfm())
        info="%s\n%sKey Length     %s (%0x02X)"  \
            % (info,indent,self.keylen,self.keylen)
        info="%s\n%sOption Codes   0x%02X" % (info,indent,self.optcd)
        info="%s\n%sSMS Indicators 0x%02X" % (info,indent,self.sms)
        info="%s\n%sBackup blksz   %s (0x%04X)" \
            % (info,indent,self.bkupsz,self.bkupsz)
        info="%s\n%sReference Date 0x%06X" % (info,indent,self.date)
        info="%s\n%sLast TTR used  %s"     % (info,indent,self.last_ttr)
        info="%s\n%sLast Trk Bal.  %s"     % (info,indent,self.last_bal)
        if not pr:
            return info
        print(info)
        
# Second PDS logical record contained original DEB data
#  +0  1   Number of extents
#  +16 16  One or more 16 byte fields of extent information
class COPY2(record):
    def __init__(self,lrec,tracks):
        super().__init__(lrec)
        self.tracks=tracks
        if len(self.bdata)<32:
            raise ValueError("[%s] expected at least 32 bytes: %s" \
                % (self.xmi_n,len(bdata)))
        
        # Extract extents from logical record
        bdata=self.bdata
        self.numext=bdata[0]   # Number of extents in record
        self.exts=[]        # EXTENT objects derived by logical record
        
        if self.numext==0:
            raise ValueError("[%s] No extents: can not process PDS records" \
                % self.xmi_n)
            
        # Make sure all of the extents we expect are present in the data
        length=(self.numext+1)*16
        if len(bdata)<length:
            raise ValueError("[%s] expected %s bytes of data: %s" \
                % (self.xmi_n,length,len(bdata)))

        # Extract extents from the COPY2 record
        for n in range(16,length-1,16):
            self.exts.append(EXTENT(bdata[n:n+16],tracks))
            
    def extents(self):
        return EXTENTS(self.exts,self.tracks)
            
    def info(self,indent="",pr=False):
        info="%s%s:" % (indent,self.__class__.__name__)
        lcl="%s    " % indent
        for n,ext in enumerate(self.exts):
            info="%s\n%s%s" % (info,lcl,ext.info())
        if not pr:
            return info
        print(info)

# This object represents the "restored" PDS Dataset
class DATASET(object):
    def __init__(self,extents,ckdrecs,lrecl,tracks):
        self.ckd=ckdrecs    # List of CKDREC objects (from PDS object)
        self.lrecl=lrecl    # Logical record size (from COPY1 object created by PDS)
        self.tracks=tracks  # Tracks per cylinder (from COPY1 object created by PDS)
        self.exts=extents   # EXTENTS objects (from PDS object)
        self.directory=None
        self.dirblks=[]
        self.members=[]     # List of MEMBER objects with member records
        self.recs=[]
        self.ttr2ckd={}     # Converts a TTR key to CKDREC list index
        
        # Used to read "sub-files" within the PDS dataset
        self.nextfile=None   # Index of start of next subfile
        self.nextrec=None
        self.eov=False
        
        # Process directory blocks
        directory=DIRECTORY()
        self.open()
        finished=False
        blocks=0
        used=0
        try:
            while True:
                rec=self.read()
                if rec.dlen!=256:
                    raise ValueError("directory block data length not 256: %s" % rec)
                blocks+=1
                if finished:
                    # flush the "sub-file" until EOF (so positioned for next file) 
                    continue
                data=rec.data()
                self.dirblks.append(data)
                directory.dirblk(data)
                used+=1
                
                # If last directory entry encountered, flush the rest of the blocks 
                if directory.done:
                    finished=True
        except EOF:
            pass
        self.close()

        self.directory=directory
        print("PDS directory blocks read: %s" % blocks)
        print("PDS directory blocks processed: %s" % used)
        print("PDS directory entries found: %s" % len(self.directory.entries))

        # Process member blocks
        lrecl=self.lrecl
        while not self.eov:
            member=MEMBER()
            self.open()
            try:
                while True:
                    rec=self.read()
                    member.block(rec,lrecl)
            except EOF:
                self.close()  # Detects "end-of-subfiles"
                key=member.relative(self.exts)
                # Remember members starting position in the dataset
                self.ttr2ckd[key]=member
                #self.ttr2ckd[key]=member.ckdrec
                self.members.append(member)
        print("PDS members found: %s" % len(self.members))

    # Retrieves all member names from the directory
    def dir_all(self):
        return self.directory.members()

    # Provides directory data in formatted display
    def dir_info(self,indent="",pr=False):
        data=self.directory.info(indent=indent)
        if not pr:
            return data
        print(data)

    # Extract a member from the PDS in a specific format.  A list of records are
    # returned.  The caller can process each record as required.
    # Exception: KeyError if member name is not in the directory
    def member(self,name,format="ascii"):
        ttr=self.directory.member(name)   # This may raise a KeyError
        key=ttr.key
        try:
            member=self.ttr2ckd[key]  # Returns a MEMBER object
        except KeyError:
            # This is an internal error (assuming the PDS was in fact correct) 
            trk,rec=TTR.ttr_tuple(key)
            raise ValueError("PDS member '%s' not found at TTR [%s:%s]" \
                % (name,trk,rec))
        if format=="ascii":
            return member.ascii()
        elif format=="image":
            return member.image()
        elif format=="noseq":
            return member.noseq()
        elif format=="text":
            return member.text()
        else:
            raise ValueError("unrecognized format for member '%s': %s" \
                % (name,format))

    # These methods emulate file reading for physical blocks in a "sub-file"
    def close(self):
        self.nextfile=self.nextrec
        self.nextrec=None
        if self.nextfile>=len(self.ckd):
            self.eov=True

    def open(self,n=None):
        if n is None:
            if self.nextfile is None:
                self.nextfile=0
            self.nextrec=self.nextfile
        else:
            # Use explicit record index
            if n>=len(self.ckd):
                raise ValueError("can not open sub-file, beyond last CKD rec "
                    "(%s): %s" % (len(ckd)-1),n)
            self.nextfile=n
        self.nextrec=self.nextfile
        self.eov=False
           
    def read(self):
        rec=self.ckd[self.nextrec]
        self.nextrec+=1
        if rec.eof:
            if self.nextrec>=len(self.ckd):
                self.eov=True
            raise EOF()
        return rec


class DIRBLK(structure):
    def __init__(self,bdata,ndx=0,debug=False):
        super().__init__(bdata,ndx=ndx)
        self.used=hw(self.bdata,ndx)
        self.entries=[]    # List of directory entries (DIRBLK objects)
        self.dirend=False  # True if this is the last directory block with data

        # Accumulate directory entries
        entndx=ndx+2
        endndx=ndx+self.used

        if __debug__:
            if debug:
                print("dirblk: %02X-%02X" % (entndx,endndx))
                print(dump(bdata,indent="    "))

        while entndx<endndx:
            # Test for last directry entry in the directory
            name=bdata[entndx:entndx+8]
            foxes=0
            for b in name:
                if b==255:
                    foxes+=1
            if foxes==8:
                self.dirend=True
                break

            # Not end, so process it
            entry=DIRNTRY(bdata,ndx=entndx)

            if __debug__:
                if debug:
                    print('[%02X] "%s" %s' % (entndx,entry.member,entry.ttr))

            self.entries.append(entry)
            entndx=entry.endndx


class DIRECTORY(object):
    def __init__(self):
        # Dictionary mapping member name to directory entry (DIRNTRY object) 
        self.entries={}
        self.done=False
        
    # This method processes a directory block creating member entries
    def dirblk(self,data):
        if self.done:
            return
        blk=DIRBLK(data)
        for entry in blk.entries:
            self.entries[entry.member]=entry
        self.done=blk.dirend

    def info(self,indent="",pr=False):
        info="PDS Directory:"
        lcl="%s    " % indent
        for member in self.members():
            entry=self.entries[member]
            info="%s\n%s%s" % (info,lcl,entry.info())
        if not pr:
             return info
        print(info)
        
    # Return the TTR object of a members location from its directory entry
    # Exception: KeyError raise if the member name is not found
    def member(self,name):
        entry=self.entries[name]
        return entry.ttr

    # Return a sorted list of all member names
    def members(self):
        return sorted(self.entries.keys())

class DIRNTRY(structure):
    def __init__(self,bdata,ndx=0):
        super().__init__(bdata,ndx=ndx)
        #                             +0  8  Member name in EBCDIC
        ebcdic=self.bdata[ndx:ndx+8]
        ascii=ebcdic.decode("cp037")
        name=ascii.rstrip()
        self.member=name
        self.ttr=TTR(self.bdata[ndx+8:ndx+11])  #  +8  3  TTR of members first block
        self.cfield=self.bdata[ndx+11]          #  +11 1  "C" field
        self.alias=self.cfield & 0x80 == 0x80   # Whether this is an alias entry

        # Number of user TTR's.  User TTR's take up two half words of user data
        self.numuttr=self.cfield & 0x60 >> 5    # Number of user TTR's

        # Number of user data halfwords (includes the number of user TTR's)
        self.numuser=self.cfield & 0x1F
        self.endndx=ndx+12+(2*self.numuser)

    def info(self,indent="",pr=False):
        info="%s  C:0x%02X TTR:%s" % (self.member.ljust(8),self.cfield,self.ttr)
        if not pr:
            return info
        print(pr)
        
# Extent descriptor for COPY2
class EXTENT(structure):
    def __init__(self,bdata,tracks):
        super().__init__(bdata)
        self.heads=tracks   # Tracks per cylinder

        # Physical extent information
        # Ignored                         +0  6
        # Starting cylinder and track
        self.cylbeg=hw(bdata,6)         # +6  2 Beginning cylinder
        self.trkbeg=hw(bdata,8)         # +8  2 Beginning track
        # Ending cylinder and track
        self.cylend=hw(bdata,10)        # +10 2 Ending cylinder
        self.trkend=hw(bdata,12)        # +12 2 Ending track
        # Number of tracks in the extent
        self.tracks=hw(bdata,14)        # +14 2 Number of tracks

        # Relative track information (supplied by EXTENTS object).  Number of
        # tracks (self.tracks) is used to create these values
        self.vbeg=(self.cylbeg*self.heads)+self.trkbeg
        self.vend=(self.cylend*self.heads)+self.trkend
        self.rbeg=None       # First relative track of extent
        self.rend=None       # Last relative track of extent
        
        if self.tracks==0:
            raise ValueError("number of tracks in extent must not be zero:\n%s" \
                % (self.info(indent="    ")))
        vtks=self.vend-self.vbeg+1
        if vtks != self.tracks:
            raise ValueError("relative end (%s) - relative beg +1 (%s) %s != "
                "tracks (%s)" % (self.vend,self.vbeg,vtks,self.tracks))

    def info(self,indent="",pr=False):
        info="%sExtent: %s:%s - %s:%s (%s tracks)" \
            % (indent,self.cylbeg,self.trkbeg,self.cylend,self.trkend,self.tracks)
        info="%s  Relative Tracks: %s - %s" % (info,self.rbeg,self.rend)
        if not pr:
            return info
        print(info)
        
    # Converts a cyl/trk address to a relative track.
    # Exception: IndexError if the cyl/trk address is outside of the extent
    def relative(self,cyl,trk):
        vrel=(cyl*self.heads)+trk
        if vrel<self.vbeg or vrel>self.vend:
            raise IndexError
        # Relative track is within the extent
        return (vrel-self.vbeg)+self.rbeg

# This class manages the translation between physical CKD addresses and relative
# track addresses.  It is based upon the extent information from the COPY2 object
class EXTENTS(object):
    def __init__(self,extents,cyl_per_trk):
        self.exts=extents       # List of EXTENT objects from COPY2 object
        self.tracks=cyl_per_trk # Number of tracks per cylinder
        
        # Calculate relative track
        reltrk=0
        for ext in self.exts:
            ext.rbeg=reltrk
            tracks=ext.tracks
            reltrk+=tracks      # Next extent's starting relative track
            ext.rend=reltrk-1   # Last relative track of this extent
        self.rlast=reltrk-1     # This is the last relative track of the dataset
        # A relative track greater than this value is not valid.
            
    def info(self,indent="",pr=False):
        info="%sDataset Extent Information:" % indent
        lcl="%s    " % indent
        for n,ext in enumerate(self.exts):
            info="%s\n%s[%s] %s" % (info,lcl,n,ext.info())
        if not pr:
            return info
        print(info)

    # Converts a cyl/track address to a relative track
    # Exception: IndexError raised if address not within available extents
    def relative(self,cyl,track):
        for ext in self.exts:
            try:
                return ext.relative(cyl,track)
            except IndexError:
                continue
        raise IndexError


class MEMBER(object):
    def __init__(self):
        self.ckd=[]
        self.blocks=[]
        
        # Established by the block() method
        self.lrecl=None
        
        # Established by relative() method
        self.reltrk=None
        self.relrec=None
        self.ckdrec=None

    def ascii(self):
        return self.records()

    def block(self,ckd,lrecl):
        datalen=ckd.dlen
        lrecs,extra=divmod(datalen,lrecl)
        if extra !=0:
            raise ValueError("incomplete logical records (lrecl=%s) in block of size "
                "%s\n    %s" % (lrecl,datalen,ckd))
        if self.lrecl is None:
            self.lrecl=lrecl
        self.ckd.append(ckd)

    # Returns a list of EBCDIC blocks suitable for writing to a binary file
    def blocks(self):
        blks=[]
        for blk in self.ckd:
            blks.append(blk.data())
        return blks

    # Returns binary blocks (unblocking not required because they all end up as
    # contiguous binary data).  This works for EBCDIC card images or other forms
    # of PDS, for example, those with programs contained within them
    def image(self):
        return self.blocks()

    # Returns a list of logical records converted to ASCII strings
    def records(self):
        recs=[]
        lrecl=self.lrecl
        for blk in self.ckd:
            data=blk.data()
            for ndx in range(0,blk.dlen-1,lrecl):
                rec=data[ndx:ndx+lrecl]
                rec=rec.decode("cp037")
                recs.append(rec)
        return recs

    # Returns a list of ASCII strings without sequence numbers
    def noseq(self):
        trunc=[]
        for rec in self.records():
            trunc.append(rec[0:71])
        return trunc

    # Returns the "TTR key"
    def relative(self,extents):
        first=self.ckd[0]
        try:
            self.reltrk=extents.relative(first.cyl,first.trk)
        except IndexError:
            raise ValueError("member starting [%s:%s:%s] not within extents" \
                % (first.cyl,first.trk,first.rec)) from None
        self.relrec=first.rec
        self.ckdrec=first.n
        return TTR.ttr_key(self.reltrk,self.relrec)

    # Returns a list of ASCII strings without sequence numbers and ending spaces
    def text(self):
        lines=[]
        for rec in self.records():
            noseq=rec[0:71]
            line=noseq.rstrip()
            lines.append(line)
        return lines


# Object representing original PDS file
class PDS(object):
    def __init__(self,blksize,dirblks,xmifile):
        self.blksize=blksize
        self.dirblks=dirblks
        self.xmi=xmifile
        
        # Created by build() method
        self.r1=None        # COPY1 object of first XMI logical record
        self.r2=None        # COPY2 object of first XMI logical record
        self.ckdrecs=[]     # List of CKDREC objects of physical dataset records
        self.exts=None      # EXTENTS object managing relative track information
        self.ds=None        # DATASET object of this PDS
        self.ckdrecs=[]     # List of CKDREC objects of physical dataset records

    # This method builds the PDS from the XMI logical data records
    # Method Arguments:
    #   rdtl   Specify True to cause detailed information about CKD recs printed
    def build(self,rdtl=False):
        xmi=self.xmi
        lrecs=0
        xmi.open()
        try:
            copy1=xmi.read()
            lrecs+=1
            self.r1=COPY1(copy1)
            copy2=xmi.read()
            lrecs+=1
            self.r2=COPY2(copy2,self.r1.heads)
            self.exts=self.r2.extents()

            # Create the DATASET representation
            while True:
                # Read the logical record
                lrec=xmi.read()
                lrecs+=1
                
                # Deblock the VS data
                bdata=lrec.bdata
                datalen=len(bdata)

                # Index within the logical record where CKDREC data starts
                ndx=0
                # The index of the next CKDREC to be 
                n=len(self.ckdrecs)
                recs=[]

                while ndx<datalen:
                    ckd=CKDREC(lrec,ndx,n+len(recs))
                    if rdtl:
                        print(ckd)  # Uses CKDREC.__str__() method
                    ndx=ckd.endndx
                    recs.append(ckd)
                self.ckdrecs.extend(recs)
            # At this point all physical CKD records are preset in the self.ckdrecs
            # list.
        except EOF:
            print("PDS disk records read: %s" % len(self.ckdrecs))

        # The physical CKDREC objects can now be logically processed recognizing
        # "sub-file" separations
        self.ds=DATASET(self.exts,self.ckdrecs,self.r1.lrecl,self.r1.heads)


# Relative Track and Record Descriptor
class TTR(object):

    # Converts a reltrk and record number into a "TTR key"
    def ttr_key(track,rec):
        return track*256+rec
        
    # Returns a tuple of (reltrk,rec) from a "TTR key"
    def ttr_tuple(key):
        return divmod(key,256)

    def __init__(self,bdata):
        self.track=hw(bdata,0)    # +0  2  Relative track
        self.rec=bdata[2]         # +2  1  Record number in relative track

        # This attribute is used to create a dictionary based upon TTR.
        self.key=TTR.ttr_key(self.track,self.rec)
    def __str__(self):
        return "%s:%s" % (self.track,self.rec)


# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,
        epilog=copyright, 
        description="writes or displays PDS members from an XMI format file")

    # Source input file (Note: attribute source in the parser namespace will be a list)
    parser.add_argument("member",nargs="*",default=[],\
        help="selected members for processing.  If omitted and -d argument supplied "\
            "all members are written to the directory.  If ommitted without the "
            "-d argument, the PDS directory is displayed")

    # XMI infput file name (for production)
    parser.add_argument("-x","--xmi",metavar="FILEPATH",required=True,\
        help="required XMI file from which PDS members are accessed")

    # Directory to which files are written
    parser.add_argument("-d","--dir",metavar="DIRECTORY",\
        help="directory to which PDS members are written. If omitted, "\
            "individually selected PDS members are displayed to the user")

    # File name extention used for writtem members
    parser.add_argument("-e","--ext",default="txt",\
        help="File name extention for written text files.  Defaults to 'txt'. "
           "--format image always uses extention 'bin'")

    # Format in which members are written
    parser.add_argument("-f","--format",default="text",
        choices=["image","text","noseq","ascii"],\
        help="format in which members are written as a file.  'image' creates "
            "contiguous PDS logical records unchanged. 'ascii' creates 80-byte ASCII "
            "text lines. 'noseq' creates 72-bytes ASCII text lines. 'text' creates "
            "variable length text lines with trailing blanks and sequence "
            "columns removed. Displayed mamebers always use format 'ascii'. "
            "'ascii', 'noseq' and 'text' formts require PDS logical record legnth "
            "of 80.")

    # Produce a complete listing of the PDS contained in a XMI file
    parser.add_argument("--list",metavar="FILEPATH",\
        help="the directory and selected members in 'ascii' format are written to "
            "the list file.  If no members are selected, all members are listed. "
            "All other options are ignored.")

    # Displays details from the IEBCOPY description records
    parser.add_argument("--pds",default=False,action="store_true",\
        help="causes PDS description to be displayed")

    return parser.parse_args()

# +---------------------------------+
# |                                 |
# |   XMI File Format Information   |
# |                                 |
# +---------------------------------+

# The XMI file is constructed from a single structure, the XMI segment (represented
# here by the XMISEG object).  Segments contain either the first, middle or last
# segement of a logical record.  In some cases the segemnt is the only segment of a
# logical record.  Segments use a small header indicating the length of the portion
# of the logical record it contains.  Segments do not exceed 255 bytes. The record
# format of segments is called "short VBS" and is the output/input of the INMCOPY
# program.  INMCOPY is the last data processor when a file is transmitted and the
# first data processor when a file is received.  The INMCOPY processor is represented
# here by the XMIFILE object.
#
# Logical records (represented here by an XMIREC object) are of two form: control
# records or data records.  Some number of control records start the file and a
# final control record indicates the end of all data records.  A specific control
# record (INMR03) immediately precedes all data records and is followed by the end-
# of-transmission control record (INMR06).  It is theoretically possible for multiple
# files to be transmitted in a single XMI format.  This module supports only one
# transmitted file.  Documentation is unclear on how this would look.
#
# Note that an XMI file may contain just control records when a notification is
# transmitted.  Notification files are not supported by this module.
#
# Physically, segments are transmitted as if they were 80-byte "card" images.  Due to
# the variable length nature of segments there can be additional data in the file
# after the last transmitted segment for the unused portion of the last "card" image.
# In a stream-based environment, all card images flow together without separation in
# the file.
#
# Logical data records are created by the data processor used before INMCOPY when
# transmitting and the data processor used after INMCOPY when receiving the data.
# For PDS files, this processor is IEBCOPY.
#


#
# +-----------------------------------------+
# |                                         |
# |   IEBCOPY PDS File Format Information   |
# |                                         |
# +-----------------------------------------+
#

# IEBCOPY places two logical records (represented by the COPY1 and COPY2 objects)
# at the beginning of its output required for the file's restoration.  This module
# essentially "restores" the PDS within the script and then extracts PDS members for
# output to the resident file system as as stream text files.  The IEBCOPY processor
# is represented here by the PDS object.
# 
# A Partitioned Dataset (PDS) is accessed using basic direct access methods.  The
# dataset is itself a series of fixed block sequential sub-files terminated by disk
# end-of-file records (a disk record with no key and no data).  The first sub-file
# is a number of directory blocks.  Each directory block contains some number of
# directory entries.  A directory entry contains a member name (in EBCDIC) with 
# its sub-file's starting record as a relative track and record number.  The actual
# physical records of the member continue until the next end-of-file record.
#
# Information about the original PDS is required to successfully restore it.  This
# information is contained in the first two logical records (represented by the COPY1
# and COPY2 objects) produced by IEBCOPY.  The remaining logical records are copies
# of the physical disk blocks in the PDS dataset: directory blocks, end-of-file
# records, track R0 records and member data blocks.
#
# Each logical record contains one or more physical disk records.  Their respective
# lengths controlled by the CKD record header (described by the CKDREC object).
# Each physical CKD record must be extracted from the logical record.
#
# Because the directory entries use relative track rather than physical cylinder
# and head information, the restoration process must convert between relative track
# information and physical information to locate a member's actual records.
# The physical disk extents of the original file are preserved in the second logical
# record created by IEBCOPY (the COPY2 object).  The DATASET object s used to
# represent the original PDS and its extents.  Various objects are used to
# represent the structure and data relationships of the PDS.  Each understands
# its corresponding data structure and mirrors the encapsulation described below.
#
#   1. PDS - understands the IEBCOPY logical records
#   2.    EXTENTS - performs relative/physical track transformations
#   3.       EXTENT - understands a single extent from the COPY2 object
#   4. DATASET - understands the PDS structure
#   5.    DIRECTORY - encapsulates the directory information from the dataset
#   6.       DIRBLK - interprets the information in a single PDS directory block
#   7.          DIRNTRY - interprets a single directory blocks content
#   8.    MEMBER - encapsulates a member's logical records
#
# PDS member extraction is performed by the EXTRACT object, created from the
# supplied command-line script arguments.
#


#
# +-----------------------------+
# |                             |
# |   XMI File Encapsulations   |
# |                             |
# +-----------------------------+
#

#
#    +---------------------------------------------------------------
#    ! XMI Formatted File
#    |   +-----------------------------------------------------------
#    |   | 80-byte card images
#    |   |   +-------------------------------------------------------
#    |   |   | XMI segments
#    |   |   |
#    |   |   | Single segment logical record
#    |   |   |    - XMI first and last segment
#    |   |   | or
#    |   |   |  Multi-segment logical record
#    |   |   |    - XMI first segment
#    |   |   |    - XMI not first and not 
#    |   |   |      last segments (optional)
#    |   |   |    - XMI last segment
#    |   |   |   +---------------------------------------------------
#    |   |   |   | XMI Logical records:
#    |   |   |   |   +-----------------------------------------------
#    |   |   |   |   | Control Logical records:
#    |   |   |   |   |  1. INMR01 (describes source file
#    |   |   |   |   |             always first)
#    |   |   |   |   |  2. INMR02 (processor record for IEBCOPY)
#    |   |   |   |   |  3. INMR02 (processor record for INMCOPY)
#    |   |   |   |   |  4. INMR03 (logical data records follow)
#    |   |   |   |   +----------------------------------------------
#    |   |   |   |   +-----------------------------------------------  
#    |   |   |   |   | Logical Data records:
#    |   |   |   |   |   - IEBCOPY Processor Output Records
#    |   |   |   |   |   +-------------------------------------------
#    |   |   |   |   |   | IEBCOPY Dataset descriptors
#    |   |   |   |   |   |   1. Record 1 (COPY1) describing dataset
#    |   |   |   |   |   |   2. Record 2 (COPY2) describing dataset 
#    |   |   |   |   |   |      extents
#    |   |   |   |   |   +-------------------------------------------
#    |   |   |   |   |   +-------------------------------------------
#    |   |   |   |   |   | PDS Physical Disk Records
#    |   |   |   |   |   |   w/disk address, Count, Key, Data fields
#    |   |   |   |   |   |   (without HA and R0 records)
#    |   |   |   |   |   | + - - - - - - - - - - - - - - - - - - - - 
#    |   |   |   |   |   | . PDS Directory
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .  | Directory Block
#    |   |   |   |   |   | .  |   - Bytes used field
#    |   |   |   |   |   | .  |   - One or more directory entries
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .    etc.
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .  | Disk End-of-File record
#    |   |   |   |   |   | .  |   (key and data counts both zero)
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | + - - - - - - - - - - - - - - - - - - - -
#    |   |   |   |   |   | + - - - - - - - - - - - - - - - - - - - -
#    |   |   |   |   |   | . PDS Member
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .  |  Member data block of one or more
#    |   |   |   |   |   | .  |    logicalrecords of size indicated 
#    |   |   |   |   |   | .  |    by IEBCOPY Record 1.
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .    etc.
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | .  | Disk End-of-File record
#    |   |   |   |   |   | .  |   (key and data counts both zero)
#    |   |   |   |   |   | .  +--------------------------------------
#    |   |   |   |   |   | + - - - - - - - - - - - - - - - - - - - -
#    |   |   |   |   |   | etc. (more PDS Members)
#    |   |   |   |   |   +-------------------------------------------
#    |   |   |   |   +-----------------------------------------------
#    |   |   |   |   +-----------------------------------------------
#    |   |   |   |   | Control Logical record:
#    |   |   |   |   |  1. INMR06 (end-of-transmission - always last)
#    |   |   |   |   +-----------------------------------------------
#    |   |   |   | (end of XMI Logical records)
#    |   |   | +-----------------------------------------------------
#    |   |   | (end of XMI segments)
#    |   |   +-------------------------------------------------------
#    |   | last 80-byte card image may have unused "columns"
#    |   +-----------------------------------------------------------
#    ! (end of XMI File)
#    +---------------------------------------------------------------


if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    extract=EXTRACT(args).run()
    
    
    #xmifile=XMIFILE("/home/harold/CBT/FILE861.XMI")
    #xmifile.segments(inventory=False)
    #xmifile.controls(dump=False)         debug
    #xmifile.records(all=True,limit=8)  # Print details of each original record
    #xmifile.records(limit=8,summary=False)
    #xmifile.dump_rec(4)
    #xmifile.dump_rec(5)
    #xmifile.dump_rec(6)
    #xmifile.dump_rec(7)
    #xmifile.dump_rec(8)
    #xmifile.dump_rec(48)
    #xmifile.dump_rec(63)
    #xmifile.dump_rec(64)
    #xmifile.dump_rec(65)
    #xmifile.dump_rec(66)
    #xmifile.dump_rec(796)
    #xmifile.dump_rec(797)
    #pds=xmifile.isPDS()
    #pds.build(rdtl=False,info=True)
    #pds.r1.dump(pr=True)
    #pds.r1.dev_info(pr=True)
    #pds.r1.ds_info(pr=True)
    #pds.r2.dump(pr=True)
    #pds.r2.info(pr=True)
    #xmifile.dump_rec(794)
