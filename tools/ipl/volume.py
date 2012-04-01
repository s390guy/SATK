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

# This module organizes a FBA or CKD volume into dataset named extents in a Volume
# Table of Contents (VTOC).  The structure of the datasets may not conform to that 
# found on a standard volume and the volume or datasets may not be readable by 
# legacy operating system supporting the volume.  Rather than creating a new 
# structure, this approach uses a known VTOC layout for use with the IPL repository 
# loader. But it is not intended to replicate in detail standard volume structures.
#
# The VTOC uses the standard volume VTOC.  The lable records may have modified 
# content for use with the repository loader.
#
# It is believed that a standard operating system should be able to read the
# datasets stored on the volume with the appropriate application level coding.
#
# Current limitations: only FBA volumes are presently supported, however the 
# design is intended to allow CKD to be supported with some ease.

import os
import os.path
import re
import sys
import struct
import time

# SATK modules
from translate import *       # ASCII-EBCDIC translation tables
from hexdump import *         # Bigendian binary conversion routines
#import ckdutil                # Access CKD emulation support (uncomment to use)
import fbautil                # Access FBA emulation support
import recsutil               # Access to the generic device record classes

def spaces(number,ascii=False):
    if ascii:
        return number*"\x20"
    return number*"\x40"

class CONTENT(object):
    # This class processes an individual statement (line) from the content file
    # The command structure is simple:
    #
    #         Command syntax      Description
    #
    #     # comment                      A comment statement
    #     cards  dataset path [ascii]    Create an 80-byte card stream file,
    #                                    truncating any lines in the file identified 
    #                                    by the path to 80-bytes.  'ascii' leaves
    #                                    content in ASCII character set.
    #     cd path                        Establish the directory for relative paths.
    #                                    The default is the current working dir.
    #     direct dataset path address [blksize]   Create a directed dataset
    #     owner owner_name               Define the volume owner
    #     seq dataset path lrecl blksize Create a sequential dataset with these 
    #                                    attributes
    #     stream dataset path [blksize]  Create a stream dataset
    #     system system_name             Define the system
    #     volume volid [ascii]           Define the volume id. 'ascii' causes VTOC
    #                                    information to be in ASCII rather than 
    #                                    EBCDIC.
    #
    #  Environment variables are expanded for all paths.
    def __init__(self,specfile,process_dict):
        # Values extracted from statements, otherwise these are the defaults:
        self.volid="IPL001"
        self.owner="STAND-ALONE TK"
        self.system="SATK"
        self.vol_ascii=False  # When True VTOC fields contain ASCII not EBCDIC
        
        self.relpath=os.getcwd()

        self.statements=[]    # These statements only contain dataset statements
        fo=open(specfile)
        lineno=0
        for line in fo:
            if line[-1]=="\n":
                line=line[:-1]
            lineno+=1
            try:
                statement=STATEMENT(lineno,line,self.relpath)
                # Successfully instantiating the STATEMENT instance means a 
                # syntactically valid statement has been encountered
                if statement.command=="comment":
                    # Drop comment statements from the list
                    continue
                if statement.command=="cd":
                    self.relpath=statement.path
                    continue
                if statement.command=="volume":
                    self.volid=statement.volid
                    self.vol_ascii=statement.ascii
                    continue
                if statement.command=="owner":
                    self.owner=statement.owner
                    continue
                if statement.command=="system":
                    self.system=statement.system
                    continue
                try:
                    statement.process=process_dict[statement.command]
                except KeyError:
                    print("volume.py - error - '%s' statement not implemented" \
                        % statement.command)
                    raise ValueError
                self.statements.append(statement)
            except ValueError:
                print("volume.py - ignored [%s] %s" % (lineno,line))
        fo.close()

# The STATEMENT class accepts a single line of the specfile as one of its 
# instantiation arguments.  The line is generally parsed.  The statement contained
# on the line is recognized by the parse method and each argument is processed 
# by a process_xxxx() instance method.  The process_xxxx() method will convert
# strings into integer, detect length problems and any other edits appropriate to
# the argument.  If the argument passes all tests it will be set as its value in
# self.argument.  Successful handling of a statement results in an instantiated
# STATEMENT instance.  Errors will trigger a ValueError caught by the CONTENT
# class initializer the results in a general message that the statement is ignored.
class STATEMENT(object):
    address_re=re.compile("[a-fA-F0-9]+")
    def __init__(self,lineno,line,relpath=""):
        self.line=line         #  Command line
        self.lineno=lineno     #  Line no of command in file
        #
        #  Command arguments   Used by commands:
        self.command=None      #  all
        self.process=None      #  all  (The external method for the statement)
        
        self.path=None         #  cards, cd, direct, stream  This is absolute path
        self.dataset=None      #  cards, direct, seq, stream
        self.blksize=None      #  direct, stream, seq
        self.ascii=False       #  cards
        self.owner=None        #  owner
        self.address=None      #  stream
        self.system=None       #  system
        self.volid=None        #  volume
        
        self.display=None      # My display routine
        
        self.parse(lineno,line,relpath)

    def __str__(self):
        return self.display()

    def display_ascii(self):
        if self.ascii:
            return " ascii"
        return ""
    
    def display_cards(self):
        return "[%s] %s %s %s%s" \
            % (self.lineno,self.command,self.dataset,self.path,self.display_ascii)

    def display_cd(self):
        return "[%s] %s %s" % (self.lineno,self.command,self.path)

    def display_direct(self):
        return "[%s] %s %s %s 0x%X" \
            % (self.lineno,self.command,self.dataset,self.path,self.address)

    def display_owner(self):
        return "[%s] %s %s" % (self.lineno,self.command,self.owner)

    def display_seq(self):
        return "[%s] %s %s %s %s %s" % (self.lineno,self.command,\
            self.dataset,self.path,self.lrecl,self.blksize)

    def display_stream(self):
        return "[%s] %s %s %s %s" \
            % (self.lineno,self.command,self.dataset,self.path,self.blksize)

    def display_system(self):
        return "[%s] %s %s" % (self.lineno,self.command,self.system)

    def display_volume(self):
        return "[%s] %s %s" % (self.lineno,self.command,self.volid)

    def parse(self,lineno,line,relpath):
        syntax_msg="statement syntax invalid or incomplete"
        line_work=line.strip()
        if len(line_work)==0 or line_work[0]=="#":
            self.command="comment"
            return
        line_work=line_work.split()  # Separate into argument strings

        # Remove any comment at the end of the line
        arguments=[]
        for arg in line_work:
            if arg[0]=="#":
                break
            arguments.append(arg)
        
        # Process the individual statements
        statement=arguments[0]
        
        #     cards  dataset path [ascii]
        if statement=="cards":
            if len(arguments)<3 or len(arguments)>4:
                print("volume.py - error - cards  %s" % syntax_msg)
                raise ValueError
            self.process_dataset(arguments[1])
            self.process_path(arguments[2],relpath)
            if len(arguments)==4:
                self.process_ascii(arguments[3])
            self.command="cards"
            self.display=self.display_cards
            return

        #     cd path
        if statement=="cd":
            if len(arguments)!=2:
                print("volume.py - error - cd %s" % syntax_msg)
                raise ValueError
            self.process_path(arguments[1],relpath)
            self.command="cd"
            self.display=self.display_cd
            return
            
        #     direct dataset path address [blksize]
        if statement=="direct":
            if len(arguments)>5 or len(arguments)<4:
                print("volume.py - error - direct  %s" % syntax_msg)
                raise ValueError
            self.process_dataset(arguments[1])
            self.process_path(arguments[2],relpath)
            self.process_address(arguments[3])
            if len(arguments)==4:
                self.process_blksize(arguements[4])
            else:
                self.blksize=512
            self.command="direct"
            self.display=self.display_direct
            return

        #     owner owner_name
        if statement=="owner":
            if len(arguments)!=2:
                print("volume.py - error - owner  %s" % syntax_msg)
            self.owner=arguments[1]
            self.command="owner"
            self.display=self.display_owner
            return
            
        #     seq dataset path lrecl blksize
        if statement=="seq":
            if len(arguments)!=5:
                print("volume.py - error - seq  %s" % syntax_msg)
                raise ValueError
            self.process_dataset(arguement[1])
            self.process_path(argument[2])
            self.process_lrecl(argument[3])
            self.process_blksize(argument[4])
            if self.blksize<self.lrecl:
                print("volume.py - error - 'blksize' %s less than 'lrecl'" \
                    % (self.blksize,self.lrecl))
                raise ValueError
            (recs,remainder)=divmod(self.blocksize,self.lrecl)
            if remainder!=0:
                self.blocksize=recs*self.lrecl
                print("volume.py - warning - 'blksize' set to %s for accomodation of"
                    " %s records per block" % (self.blocksize,recs))
            self.display=self.display_seq
            return

        #   stream dataset path [blksize]
        if statement=="stream":
            if len(arguments)>4 or len(arguments)<3:
                print("volume.py - error - stream  %s" % syntax_msg)
                raise ValueError
            self.process_dataset(arguments[1])
            self.process_path(arguments[2],relpath)
            if len(arguments)==4:
                self.process_blksize(arguments[3])
            else:
                self.blksize=512
            self.command="stream"
            self.display=self.display_stream
            return

        #     system system_name
        if statement=="system":
            if len(arguments)!=2:
                print("volume.py - error - system  %s" % syntax_msg)
                raise ValueError
            self.system=arguments[1]
            self.command="system"
            self.display=self.display_system
            return

        #     volume volid [ascii]
        if statement=="volume":
            if len(arguments)>3 or len(arguments)<2:
                print("volume.py - error - 'volume'  %s" % syntax_msg)
                raise ValueError
            if len(arguments[1])>6:
                print("volume.py - error - 'volume' id longer than six " \
                    "characters: %s" % len(arguments[1]))
                raise ValueError
            self.volid=arguments[1]
            if len(arguments)==3:
                self.process_ascii(argument[2])
            self.command="volume"
            self.display=self.display_volume
            return
            
        # unrecognized statement
        print("volume.py - error - unrecognized statement '%s'" % statement)
        raise ValueError

    def process_address(self,addr):
        addr_string=addr
        if len(addr_string)>2:
            if addr_string[:2]=="0x":
                addr_string=addr_string[2:]
            else:
                if addr_string[:2]=="X'" and addr_string[-1]=="'":
                    addr_string=addr_string[2:-1]
                else:
                    pass
        match=STATEMENT.address_re.match(addr_string)
        if match is None:
            print("volume.py - error - 'address' is not a valid hexadecimal string")
            raise ValueError
        self.address=int(addr_string,16)
        
    def process_ascii(self,ascii):
        if ascii=="ascii":
            self.ascii=True
            return
        print("volume.py - error - 'ascii' argument invalid: '%s'" % ascii)
        raise ValueError
        
    def process_blksize(self,blksize):
        try:
            size=int(blksize,10)
        except IndexError:
            print("volume.py - error - 'blksize' invalid: %s" % blksize)
            raise ValueError
        if size>65535 or size<1:
            print("volume.py - error - 'blksize' not in range (1-65535): %s" % size)
            raise ValueError
        self.blksize=size
        
    def process_dataset(self,dataset):
        if len(dataset)>44:
            print("volume.py - error - 'dataset' name longer than 44 characters")
            raise ValueError
        self.dataset=dataset.upper()

    def process_lrecl(self,lrecl):
        try:
            recl=int(lrecl,10)
        except IndexError:
            print("volume.py - error - 'lrecl' invalid: %s" % lrecl)
            raise ValueError
        if recl>65535 or recl<1:
            print("volume.py - error - 'lrecl' not in range (1-65535): %s" % recl)
            raise ValueError
        self.lrecl=recl
        
            
    def process_path(self,string,relpath):
        trial_path=os.path.expandvars(string)
        if not os.path.isabs(trial_path):
            trial_path=os.path.abspath(os.path.join(relpath,trial_path))
        self.path=trial_path

class EXTENT(object):
    # This class defines an extent
    # 
    # Structure:
    #    Name    Disp       Length     Format       Description
    #  xttype     +0          1        binary       Extent type (see below)
    #  xtseqn     +1          1        binary       Extent sequence number
    #  xtbcyl     +2          2        binary       Beginning logical cylinder
    #  xtbtrk     +2          2        binary       Beginning logical track
    #  xtecyl     +2          2        binary       Ending logical cylinder
    #  xtetrk     +2          2        binary       Ending logical track
    #
    # Extent types:
    #  X'00'  -  unused
    #  X'01'  -  data
    #  X'02'  -  overflow
    #  X'04'  -  index
    #  X'40'  -  User label
    #  X'80'  -  shared cylinders
    #  X'81'  -  Extend on cylinder boundary
    def __init__(self,beg,end):
        # beg = a (cylinder, track) tuple
        # end = a (cylinder, track) tuple
        self.xtbcyl=beg[0]
        self.xtbtrk=beg[1]
        self.xtecyl=end[0]
        self.xtetrk=end[1]
        self.xttype=chr(1)       # Extent type is always data
        self.xtseqn=chr(0)       # Extend sequence always 0

    def create(self):
        # Convert the extent into a binary string
        rec=self.xttype+self.xtseqn
        rec+=halfwordb(self.xtbcyl)
        rec+=halfwordb(self.xtbtrk)
        rec+=halfwordb(self.xtecyl)
        rec+=halfwordb(self.xtetrk)
        if len(rec)!=10:
            raise ValueError("Extent not 10 bytes: %s" % len(rec))
        return rec

class DSCB1(object):
    # This class manages the format 1 DSCB, the dataset descripter
    #
    # Structure:
    #    Name    Disp       Length     Format       Description
    #  ds1dsnam   +0          44       EBCDIC       Dataset name (space padded)
    #  ds1fmtid   +44          1       EBCDIC       '1' or X'F1'
    #  ds1dssn    +45          6       EBCDIC       Volume serial number
    #  ds1volsq   +51          2       binary       Volume sequence number
    #  ds1creyr   +53          1       binary       Creation Year minus 1900
    #  ds1credy   +54          2       binary       Creation Julian day of year
    #  ds1expyr   +56          1       binary       Expiration year
    #  ds1expdy   +57          2       binary       Expiration julian day
    #  ds1noepv   +59          1       binary       number of extents
    #  ds1bodbd   +60          1       binary       bytes used in last dir. block
    #  ds1satk    +61          1       binary       SATK options (normally reserved)
    #  ds1syscd   +62         13       ECBDIC       System code
    #  reserved   +75          7       EBCDIC       spaces (X'40')
    #  ds1dsorg1  +82          1       binary       Dataset organization
    #  ds1dsorg2  +83          1       binary       Dataset organization
    #  ds1recfm   +84          1       binary       Record format
    #  ds1optcd   +85          1       binary       option codes
    #  ds1blkl    +86          2       binary       block length
    #  ds1lrecl   +88          2       binary       logical record length
    #  ds1keyl    +90          1       binary       key length
    #  ds1rkp     +91          2       binary       relative key position
    #  ds1dsind   +93          1       binary       dataset indicators
    #  ds1scalu   +94          1       binary       secondary allocation units
    #  ds1scalq   +95          3       binary       quantity of allocation units
    #  ds1lstar   +98          3       ttr          Last used
    #  ds1ltrbal  +101         2       binary       bytes used on last track
    #  reserved   +103         2       EBCDIC       spaces (X'40')
    #  ds1ext1    +105        10       EXTENT       First extent
    #  ds1ext2    +115        10       EXTENT       Second extent
    #  ds1ext3    +125        10       EXTENT       Third extent
    #  ds1ptrds   +135         5       cchhr        CCHHR of F2 or F3 DSCB
    # Total length: 140
    #
    # Values for ds1dsind:
    #   X'80'  -  Last volume of the dataset
    #   X'40'  -  RACF indicated
    #   X'20'  -  Blocksize multiple of 8
    #   X'10'  -  Password protected
    #   X'04'  -  Write protected
    #   X'02'  -  Updated since last backup
    #   X'01'  -  Secure checkpoint dataset
    #
    # Value for ds1optcd:
    #   X'80'  -  Dataset in ICF catalog
    #   X'40'  -  ICF catalog
    #
    # Values for ds1scalo byte 0:
    #   X'00'  -  Absolute track allocation units
    #   X'40'  -  block allocation units
    #   X'80'  -  track allocation units
    #   X'C0'  -  cylinder allocation units
    #   X'08'  -  Contiguous space
    #   X'04'  -  Maximum contiguour extents
    #   X'02'  -  Upto 5 largest extents
    #   X'01'  -  Round to cylinders
    #
    # Values for ds1dsorg byte 0:
    #   X'80'  -  IS Indexed sequential
    #   X'40'  -  PS Physically sequential
    #   X'20'  -  DA Direct Access
    #   X'02'  -  PO Partitioned organization
    #   X'01'  -  U  Unmovable
    #
    # Values for ds1dsorg byte 1:
    #   X'08'  -  VSAM dataset
    #
    # Values for ds1recfm:
    #   X'40'  -  V  Variable length 
    #   X'80'  -  F  Fixed length
    #   X'C0'  -  U  Undefined length
    #   X'20'  -  Track overflow
    #   X'10'  -  Blocked
    #   X'08'  -  Spanned or standard
    #   X'04'  -  A  ANSI carriage control
    #   X'02'  -  M  Machine carriage control
    #
    # Values for ds1satk:
    #   X'01'  -  Stream dataset
    #   X'02'  -  Directed dataset
    dsorgs={"IS":0x80,"PS":0x40,"DA":0x20,"PO":0x02,"DAU":0x21}
    recfms={"F":0x80,"FB":0x90,"V":0x40,"VB":0x50,"U":0xC0}
    satk={None:0x40,"stream":0x01,"direct":0x02}
    def __init__(self,name,volser,blklen=0,lrecl=0,dsorg="DA",recfm="U",satk=None,\
                 system="SATK"):
        try:
            self.ds1satk=DSCB1.satk[satk]
        except KeyError:
            self.ds1satk=DSCB1.satk[None]
        try:
            self.ds1dsorg1=DSCB1.dsorgs[dsorg]
        except KeyError:
            self.ds1dsorg1=DSCB1.dsorgs["DA"]
        try:
            self.ds1recfm=DSCB1.recfms[recfm]
        except KeyError:
            self.ds1recfm=DSCB1.recfms["U"]
        self.ds1dsnam=name
        self.ds1dssn=volser
        self.ds1syscd=system
        self.ds1blkl=blklen
        self.ds1lrecl=lrecl
        self.ds1ltrbal=None        # set by dtf method
        self.ds1ext1=None          # set by dtf method
        
    def create(self,ascii=False):
        # Returns a string corresponding to the Format 1 DSCB
        dataset=self.ds1dsnam+44*" "
        dataset=dataset[:44]
        if ascii:                             #  Bytes 0-43  ds1dsnam 
            rec=dataset
        else:
            rec=dataset.translate(A2E)
        if ascii:                             #  Bytes 0-44  ds1fmtid
            rec=+"\x21"
        else:
            rec+="\xF1"
        volser=ds1dssn+6*" "
        volser=volser[:6]
        if ascii:                             #  Bytes 0-50  ds1dssn
            rec+=volser
        else:
            rec+=volser.translate(A2E)
        rec+="\x00\x00"                       #  Bytes 0-52  ds1volsq
        time_tuple=time.localtime()
        year=time_tuple[0]
        day=time_tuple[7]
        rec+=chr(year-2000)                   # Bytes 0-53   ds1creyr
        rec+=halfwordb(day)                   # Bytes 0-55   ds1credy
        rec+=chr(255)                         # Bytes 0-56   ds1expyr
        rec+=halfwordb(367)                   # Bytes 0-58   ds1expyr
        rec+="\x01"                           # Bytes 0-59   ds1noepv
        rec+="\x00"                           # Bytes 0-60   ds1bodbd
        rec+=chr(self.ds1satk)                # Bytes 0-61   ds1satk
        syscode=system+13*" "
        syscode=syscode[:13]
        if ascii:                             # Bytes 0-74   ds1syscd
            rec+=syscode
        else:
            rec+=syscode.translate(A2E)
        rec+=spaces(7,ascii)                  # Bytes 0-81   reserved
        rec+=chr(self.ds1dsorg1)              # Bytes 0-82   ds1dsorg1
        rec+="\x00"                           # Bytes 0-83   ds1dsorg2
        rec+=chr(self.ds1recfm)               # Bytes 0-84   ds1recfm
        rec+="\x00"                           # Bytes 0-85   ds1optcd
        rec+=halfwordb(self.ds1blkl)          # Bytes 0-87   ds1blkl
        rec+=halfwordb(self.ds1lrecl)         # Bytes 0-89   ds1lrecl
        rec+="\x00"                           # Bytes 0-90   ds1keyl
        rec+="\x00\x00"                       # Bytes 0-92   ds1rkp
        rec+="\x80"                           # Bytes 0-93   ds1dsind
        rec+="\x00"                           # Bytes 0-94   ds1scalu
        rec+=3*"\x00"                         # Bytes 0-97   ds1scalq
        rec+=3*"\x00"                         # Bytes 0-100  ds1lstar
        rec+=halfwordb(self.ds1ltrbal)        # Bytes 0-102  ds1ltrbal
        rec+=spaces(2,ascii)                  # Bytes 0-104  reserved
        rec+=self.ds1ext1.create()            # Bytes 0-114  ds1ext1
        rec+=10*"\x00"                        # Bytes 0-124  ds1ext2
        rec+=10*"\x00"                        # Bytes 0-134  ds1ext3
        rec+=5*"\x00"                         # Bytes 0-139  ds1ptrds
        if len(rec)!=140:
            raise ValueError("Format 1 DSCB not 140 bytes: %s" % len(rec))
        return rec

class DSCB4(object):
    # This class manages the format 4 DSCB, the VTOC descripter
    #
    # Structure:
    #    Name    Disp       Length     Format       Description
    # ds4keyid   +0         44         binary       44 bytes of X'04'
    # ds4fmtid   +44        1          EBDCIC       '4' or X'F4'
    # ds4hpchr   +45        5          cchhr        Location of highest F1 DSCB
    # ds4dsrec   +50        2          binary       Number of Format 0 DSCB's
    # ds4hcchh   +52        4          cchh         Next available alternate track
    # ds4noatk   +56        2          binary       Number of alternate tracks
    # ds4vtoci   +58        1          bits         See below
    # ds4noext   +59        1          binary       Number of extents in VTOC
    # reserved   +60        2          EBCDIC       spaces (X'40')
    # ds4dscyl   +62        2          binary       Number of logical cylinders.
    # ds4dstrk   +64        2          binary       Logical tracks in a logical cyl.
    # ds4devtk   +66        2          binary       Device logical track length
    # ds4devi    +68        1          binary       Non-last keyed blk overhead
    # ds4devl    +69        1          binary       Last keyed blk overhead
    # ds4devk    +70        1          binary       Non-keyed block overhead
    # ds4devfg   +71        1          binary       Device flags
    # ds4devtl   +72        2          binary       Device tolerance
    # ds4devdt   +74        1          binary       Number of DSCB's per track
    # ds4devdb   +75        1          binary       Number of dirblks/track
    # ds4amtim   +76        8          binary       VSAM timestamp
    # ds4vsind   +84        1          binary       VSAM indicators
    # ds4vscra   +85        2          binary       CRA track location
    # ds4r2tim   +87        8          binary       VSAM vol/cat timestamp
    # reserved   +95        5          EBCDIC       spaces (X'40')
    # ds4f6ptr   +100       5          cchhr        First Format 6 DSCB
    # ds4vtoce   +105       10         Extent fmt   VTOC Extent (see EXTENT class)
    # reserved   +115       25         EBCDIC       spaces
    # Total length: 140
    #
    # ds4vtoci indicators:
    #  0x80  -  Format 5 DSB's are not valid (DOS)
    #  0x10  -  DOS stacked pack
    #  0x08  -  DOS converted pack
    #  0x40  -  VTOC contains errors
    #  0x20  -  DIRF reclaimed
    def __init__(self,cyls,trkpercyl,trksize):
        #  sectors is the number of sectors supported by the device
        #  bpg is the fbautil.py value for blocks per cyclical group (log. trk.)
        #  bpp is the fbaulti.py value for blocks per access position (log. cyl.)
        self.ds4dscyl=cyls              # Number of logical cylinders
        self.ds4dstrk=trkpercyl         # Logical tracks per logical cylinder
        self.ds4devtk=trksize           # Size of a logical track
        self.extent=None                # VTOC Extent
        
    def create(self,ascii=False):
        # Return a string corresponding to the Format 4 DSCB
        rec=44*"\x04"                   # Bytes 0-43   ds4keyid
        if ascii:                       # Bytes 0-44   ds4fmtid
            rec+="\x41"
        else:
            rec+="\xF4"
        rec+=5*"\x00"                   # Bytes 0-49   ds4hpchr
        rec+=2*"\x00"                   # Bytes 0-51   ds4dsrec
        rec+=4*"\x00"                   # Bytes 0-55   ds4hcchh
        rec+=2*"\x00"                   # Bytes 0-57   ds4noatk
        rec+="\x80"                     # Bytes 0-58   ds4vtoci DOS
        rec+="\x01"                     # Bytes 0-59   ds4noext 1
        rec+=spaces(2,ascii)            # Bytes 0-61   reserved
        rec+=halfwordb(self.ds4dscyl)   # Bytes 0-63   ds4dscyl
        rec+=halfwordb(self.ds4dstrk)   # Bytes 0-65   ds4dstrk
        rec+=halfwordb(self.ds4devtk)   # Bytes 0-67   ds4devtk
        rec+="\x00"                     # Bytes 0-68   ds4devi
        rec+="\x00"                     # Bytes 0-69   ds4devl
        rec+="\x00"                     # Bytes 0-70   ds4devk
        rec+="\x00"                     # Bytes 0-71   ds4devfg
        rec+="\x00\x00"                 # Bytes 0-73   ds4devtl
        rec+="\x00"                     # Bytes 0-74   ds4devdt
        rec+="\x00"                     # Bytes 0-75   ds4devdb
        rec+=8*"\x00"                   # Bytes 0-83   ds4amtim
        rec+="\x00"                     # Bytes 0-84   ds4vsind
        rec+="\x00\x00"                 # Bytes 0-86   ds4vscra
        rec+=8*"\x00"                   # Bytes 0-94   ds4r2tim
        rec+=spaces(5,ascii)            # Bytes 0-99   reserved
        rec+=self.extent.create()       # Bytes 0-114  ds4vtoce
        rec+=spaces(25,ascii)           # Bytes 0-139  reserved
        if len(rec)!=140:
            raise ValueError("Format 4 DSCB not 140 bytes: %s" % len(rec))
        return rec

class VOL1(object):
    # This class manages the volume label in sector 1
    #
    # Structure:
    #    Name    Disp       Length     Format       Description
    #  volkey     +0           4       EBCDIC       'VOL1'
    #  vollbl     +4           4       EBDCIC       'VOL1'
    #  volid      +8           6       EBCDIC       Volume label
    #  security   +14          1       binary       Security byte
    #  vtoccyl    +15          2       binary       Logical cylinder of Format 4
    #  vtoctrk    +17          2       binary       Logical track of Format 4
    #  vtocrec    +19          1       binary       sector of track of first CI
    #  reserved   +20          5       EBCDIC       spaces (X'40')
    #  cisize     +25          4       binary       VTOC CI size in bytes
    #  blkperci   +29          4       binary       Sectors per CI
    #  labperci   +33          4       binary       Number of labels per CI
    #  reserved   +37          4       EBCDIC       spaces (X'40')
    #  owner      +41         14       EBCDIC       Volume owner
    #  reserved   +55         29       EBCDIC       spaces (X'40')
    #  Total length: 84
    def __init__(self,volid="IPL001",owner="STAND-ALONE TK"):
        self.volid=volid
        self.owner=owner
        self.vtoccyl=None    # Set by the vtoc method
        self.vtoctrk=None    # Set by the vtoc method
        self.vtocrec=None    # Set by the vtoc method
        self.cisize=None     # Set by the defvtoc method
        self.blkperci=None   # Set by the defvtoc method
        self.labperci=None   # Set by the defvtoc method
     
    def create(self,ascii=False):
        # Returns a string corresponding the specified VOL1 record
        if ascii:
            vol1="VOL1"                # ASCII 'VOL1'
        else:
            vol1="\xE5\xD6\xD3\xF1"    # EBCDIC 'VOL1'
        rec=vol1+vol1                  # Bytes 0-7       Volume key and label
        volid=self.volid+6*" "
        volid=volid[:6]
        if ascii:                      # Bytes 0-13      Volume label
            rec+=volid
        else:
            rec+=volid.translate(A2E)
        rec+=chr(0)                    # Bytes 0-14      Security byte
        rec+=halfwordb(self.vtoccyl)   # Bytes 0-16      vtoccyl
        rec+=halfwordb(self.vtoctrl)   # Bytes 0-18      vtoctrk
        rec+=chr(self.vtocrec)         # Bytes 0-19      vtocrec
        rec+=spaces(5,ascii)           # Bytes 0-24      reserved
        rec+=fullwordb(self.cisize)    # Bytes 0-28      cisize
        rec+=fullwordb(self.blkperci)  # Bytes 0-32      blkperci
        rec+=fullwordb(self.labperci)  # Bytes 0-36      labperci
        rec+=spaces(4,ascii)           # Bytes 0-40      reserved
        owner=self.owner+14*" "
        owner=owner[:14]
        if ascii:                      # Bytes 0-54      owner
            rec+=owner
        else:
            rec+=owner.translate(A2E)
        rec+=spaces(29,ascii)          # Bytes 0-83      reserved
        if len(rec)!=84:
            raise ValueError(\
                "volume.py - INTERNAL - VOL1 not 84-bytes: %s" % len(rec))
        return rec
        
class DATASET(object):
    def __init__(self,statement):
        self.ddname=statement.dataset
        self.filepath=statement.path
        if not os.path.isfile(statement.path):
            print("volume.py - error %s source file %s does not exist" \
                % (self.ddname,statement.path))
            raise ValueError
        self.filepath=statement.path
        self.size=os.path.getsize(self.filepath)
        if self.size==0:
            print("volume.py - error %s source file %s has zero length" \
                % (self.ddname,statement.path))
            raise ValueError
            
        self.stream=False      # Subclass must set to True for a stream file
        self.directed=False    # Subclass must set to True for a directed stream
        self.lrecs=None        # The subclass must initialize
        self.lrecl=None        # The subclass must initialize
        self.extent=None       # The extent is established during allocation
        
        # variables established by method block
        self.blocks=None       # The number of blocks required by the dataset
        self.lastused=None     # The number of bytes used in the last block
        self.blksize=None      # The subclass must initialize
        
        # variables established by allocate method
        self.extent=None       # EXTENT instance for allocated space
        self.tracks=None       # Tracks required for the dataset
        self.last_used=None    # Bytes used on last track
        
        # variable established by the dtf method
        self.dscb1=None        # The DSCB1 instance associated with this dataset

    def allocate(self,spacemgr):
        # This method defines the space requirements for the dataset using
        # the supplied space manager instance.
        self.tracks,self.last_used=spacemgr.space(\
            self.blocks,self.blksize,self.lastused)
        self.extent=spacemgr.allocate(self.tracks)

    def blocks(self):
        # This method calculates the number of blocks required by the dataset and
        # the number of bytes used in the last block
        raise NotImplementedError("volume.py - internal error - " \
            "blocks method must be implemented by subclass: %s" \
            % self.__class__.__name__)

    def dtf(self,volser):
        # This method creates a DSCB1 instance for this dataset
        raise NotImplementedError("volume.py - internal error - " \
            "dtf method must be implemented by subclass: %s" \
            % self.__class__.__name__)

class CARDS(DATASET):
    # A CARDS dataset it a contiguous stream of cards stored on the FBA device.
    # Blocks are actually 512 bytes in length.  The intent is the entire dataset
    # will be read into contiguous storage locations.  This allows the stand-alone
    # program to process the cards in a simple loop.
    def __init__(self,statement):
        super(CARDS,self).__init__(statement)
        self.ascii=statement.ascii     # Whether to leave cards as ASCII data
        try:
            fo=open(self.filepath,"rt")
        except IOError:
            print("volume.py - error opening %s source file %s" \
                % (self.ddname,self.filepath))
            raise ValueError
        lineno=0
        self.cards=[]
        try:
            for line in fo:
                lineno+=1
                if line[-1]=="\n":
                    line=line[:-1]
                if len(line)>80:
                    print("volume.py - warning truncating line %s in %s source file"\
                        % (self.lineno,self.ddname,self.filepath))
                else:
                    line=line+80*" "
                line=line[:80]
                if not self.ascii:
                    line.translate(A2E)
                self.cards.append(line)
        except IOError:
            print("volume.py - error reading %s source file %s" \
                % (self.ddname,self.filepath))
            raise ValueError
        try:
            fo.close()
        except IOError:
            print("volume.py - error closing %s source file %s" \
                % (self.ddname,self.filepath))
            raise ValueError

        self.lrecs=len(self.cards)
        self.lrecl=80
        #self.blklen=6*self.lrecl     # This fits in one sector
        #self.stream=True
        
    def blocks(self):
        total_bytes=self.lrecs*self.lrecl
        self.blocks,self.lastused=divmod(total_bytes,512)
        if self.lastused=0:
            self.lastused=512
        else:
            self.blocks+=1
        self.blocksize=512
        
    def dtf(self,volser,system):
        dscb1=DSCB1(self.ddname,volser,blklen=512,lrecl=512,dsorg="DA",recfm="U",\
            satk="stream",system=system)
        dscb1.ds1ext1=self.extent
        dscb1.ds1ltrbal=self.last_used
        self.dscb1=dscb1
        
class STREAM(DATASET):
    def __init__(self,statement):
        super(STREAM,self).__init__(statement)
        self.stream=True    # This dataset is allocated contiguously
        self.lrecs=self.
        
class SPACEMGR(object):
    # Space is managed based upon relative track.  For CKD, this corresponds to
    # a physical track.  For FBA this corresponsd to a set of sectors within an
    # access position.  Cylinders are derived from relative track for both FBA and
    # CKD devices.  For CKD devices, the number of tracks per cylinder is 
    # determined by the disk geometry.  For an FBA device the number of access
    # positions within a cyclical group determines this relationship.
    #
    # How data blocks are allocated on the volume is device specific.  Each 
    # subclass has the responsibility to manage these allocations.
    def __init__(self,devinfo):
        self.devinfo=devinfo
        
        self.next_rel_trk=None      # This is the next relative track available
        # It will be set by the reserve method

    def allocate(self,tracks):
        # Returns an extent instance of the allocated tracks
        raise NotImplementedError("volume.py - internal error - " \
            "defautl_reserve method must be implemented by subclass: %s" \
            % self.__class__.__name__)

    def default_reserve(self):
        # Returns the number of volume units to reserve by default.  The unit
        # is device type specific
        raise NotImplementedError("volume.py - internal error - " \
            "defautl_reserve method must be implemented by subclass: %s" \
            % self.__class__.__name__)

    def reserve(self,units):
        # Reserves the specified units and establishes the starting relative track
        # for allocations.
        raise NotImplementedError("volume.py - internal error - " \
            "reserve method must be implemented by subclass: %s" \
            % self.__class__.__name__)
        
    def space(self,blocks,blocksize,last_used_block):
        # Calculates the number of tracks required for the blocks and the number
        # bytes used on the last track.  Returns a tuple (tracks,last_track_used).
        raise NotImplementedError("volume.py - internal error - " \
            "space method must be implemented by subclass: %s" \
            % self.__class__.__name__)
        
class CKDSPACE(SPACEMGR):
    def __init__(self,devinfo):
        super(CKDSPACE,self).__init__(devinfo)
    # Implement the remaining interface classes to complete CKD device support
    def default_reserve(self):
        # By default reserve the first track for volume information
        return 1  # Track (0,0) reserved for IPL records and VOL1 label
    def reserve(self,tracks):
        # The next relative track that can be assigned is the number of tracks
        # being reserved
        self.next_rel_trk=tracks

class FBASPACE(SPACEMGR):
    # This class manages the allocation of data blocks to sectors and sectors to
    # tracks that can be managed by the super class.
    #
    # For standard blocked files:
    #
    # FBA devices can only read and write complete sectors (512-bytes of data).
    # For example, a block that contain 10 80-byte logical records (or 800 bytes
    # of data in the block) will require two sectors to allow full blocks to be
    # read or written.  10 blocks will therefore consume 20 sectors.
    #
    # Let's also assume in this example that a logical track contains 6 sectors.
    # These 10 blocks of logical data will therefore consume 4 logical tracks.  The
    # first two sectors of the last track will contain the last block of the file
    # and the remaining four sectors of the last track are unused.  Also the
    # number of bytes used in the last track will be 800 corresponding to the actual
    # end of the last block of the actual data in the file.  This value is required
    # to understand where the end of the file actually resides.
    #
    # Currently, it is unclear whether "last_track_used" relates to dataset bytes,
    # a logical measure, or physical track capacity consumed by dataset on
    # the last track.  The definition used below assumes physical consumption.  It
    # is really dependent upon the algorithm used to calculate the end of the 
    # logical file.
    # 
    # "last_track_used" is assumed to mean physical track capacity consumed by the 
    # dataset on the last logical track.  This translates to number of bytes in the 
    # sectors consumed by the complete blocks on the track plus the number of bytes 
    # consumed by the logical records in the last block.  
    #
    # Another interpretation of this definition is "last_track_used" is the 
    # relative byte following the last incomplete block otherwise it is the 
    # relative byte following the last sector of the last complete block.
    #
    # For stream files:
    #
    # While stream files conform to the logical track boundaries, they are written 
    # to use each sector completely by storing the stream in contiguous whole
    # sectors until the last sector is encountered.  The last sector may contain
    # unused areas.  And the last sector may not completely utilize the last track.
    # So portions of the last track may also be unused.  Stream files eliminate the
    # unused space resulting from incomplete track usage required by the blocking
    # process.  Stream files use the track length as the block size and logical
    # record length.  Stream files are read in units of entire tracks.  The total
    # length of the stream is determined by the combined length of all of the 
    # tracks read and the last track used value.
    def __init__(self,devinfo):
        super(FBASPACE,self).__init__(devinfo)
        self.sectors=self.devinfo.sectors      # sectors on the volume
        self.logtrk=self.devinfo.logtrk        # sectors per logical track
        self.logcyl=self.devinfo.logcyl        # sectors per logical cylinder
        self.logcyls=self.sectors/self.logcyl  # number of logical cylinders
        self.track_size=self.logtrk*512        # Size of a logical track
        self.tracks_per_cyl=self.logcyl/self.logtrk  # Tracks per cylinder

    def __str__(self):
        return "%s track size: %s, tracks/cyl: %s, cyl/vol: %s" \
            % (self.dtype,self.track_size,self.tracks_per_cyl,self.logcyls)

    def allocate(self,tracks):
        begin_rel_track=self.next_rel_trk
        end_rel_track=begin_rel_track+tracks-1
        begin=divmod(begin_rel_track,self.tracks_per_cyl)
        end=divmod(end_rel_track,self.tracks_per_cyl)
        self.next_rel_trk=end_rel_track+1
        return EXTENT(begin,end)

    def default_reserve(self):
        # By default reserve the first two sectors for volume information
        return 2  # sector 0 = IPL PSW and CCW chain, sector 2 = VOL1 label
    
    def reserve(self,sectors):
        # Round reserved sectors to the start of the next logical track
        self.next_rel_trk=(sectors+self.logtrk-1)/self.logtrk
        
    def space(self,blocks,blocksize,last_used):
        sectors_per_block=(blocksize+511)/512
        last_used_sectors=(last_used+511)/512
        unused_last_sector=(last_used_sectors*512)-last_used
        sectors_needed=(blocks*sectors_per_block)+last_used_sectors
        tracks,last_track_sectors_used=divmod(sectors_needed,self.logtrk)
        if last_track_sectors_used>0:
            tracks+=1
        if last_track_sectors_used<last_used_sectors:
            last_used_data_in_sectors=\
                ((last_used_sectors-last_track_sectors_used)*512)-unused_last_sector
        else:
            last_used_data_in_sectors=\
                (last_track_sectors_used*512)-unused_last_sector
        space_bytes=tracks*self.track_size
        last_track_not_used=space_bytes-bytes_needed
        last_track_used=self.track_size-track_not_used
        return (tracks,last_used_data_in_sectors)
        
class VOLUME(object):
    # This class manages the creation of the volume content.  It is designed to
    # operate as a class used by another utility or on its own.  The staticmethod
    # process() will process and create the volume.  The staticmethod records() 
    # returns a list of recsutil.fba or recsutil.ckd instances that the caller 
    # accepts responsibility for delivery to the medium.
    @staticmethod
    def process(dtype,content):
        v=VOLUME(dtype,content)
        if v.rc()!=0:
            print("volume.py - device creation aborted")
            sys.exit(2)
        v.allocate(dtype)
    @staticmethod
    def records(dtype,content,reserve=None):
        v=VOLUME(dtype,content,reserve)
        if v.rc()!=0:
            return []
        v.allocate()
    def __init__(self,dtype,content,reserve=None):
        self.status=0           # returned via rc method to indicate success
        self.dds=[]             # Datasets being created on volume
        self.filename=content   # Content specification file
        self.process_dict={"cards":self.process_cards,
                           "direct":self.process_direct,
                           "stream":self.process_stream}
         
        try:
            self.spacemgr=self.manager(dtype)
        except ValueError:
            self.status=1
            return
            
        # Reserve any necessary space
        if reserve is None:
            self.reserve=self.spacemgr.default_reserve()
        else:
            self.reserve=reserve
        self.spacemgr.reserve(self.reserve)
                           
        # Process the specification file                  
        self.content=CONTENT(content,self.process_dict)
        self.volid=self.content.volid
        self.owner=self.content.owner
        self.system=self.content.system
        
        for dataset in self.content.statements:
            try:
                dd=dataset.process(dataset)
            except ValueError:
                print("volume.py - ignored %s" % dataset)
                continue
            self.dds.append(dd)
            
        self.vtoc=None          # The VTOC instance is create during allocation
        
    def allocate(self,spacemgr):
        # This method allocates volume space to the individual datasets, creates
        # extent information
        self.vtoc=VTOC(spacemgr,self.dds,self.volid,self.system,self.owner)
        
    def manager(self,dtype):
        # Identify the device type and return a volume space manager
        try:
            devinfo=fbautil.fba.sectors[self.dtype]
            return FBASPACE(devinfo)
        except KeyError:
            pass
        try:
            devinfo=ckdutil.ckd.geometry[self.dtype]
            return CKDSPACE(devinfo)
        except KeyError:
            pass
        print("volume.py - error - unrecognized device type: %s" % self.dtype)
        raise ValueError
        
    def process_cards(self,statement):
        dd=CARDS(statement)
    def process_direct(self,statement):
        dd=DATASET(statement)
    def process_stream(self,statement):
        dd=DATASET(statement)
        
    def rc(self):
        # return the return code
        return self.status
        
class VTOC(object):
    def __init__(self,spacemgr,dds,volser,system,owner):
        self.spacemgr=spacemgr
        self.dds=dds         # List of dataset instances destined for VTOC
        self.volser=volser   # Volume serial number
        self.system=system   # Owning system
        self.owner=owner     # Ownner
        
        # Allocate the space on the volume
        for dd in self.dds:
            dd.allocate(self.spacemgr)
            dd.dtf(self.volser,self.system)

def copyright()
    print("volume.py Copyright, Harold Grovesteen, 2011, 2012")

def usage(n):
    print "Usage: ./volume.py dtype spec_file device_file"
    sys.exit(n)

if __name__ == "__main__":
    copyright()
    if len(sys.argv)!=4:
        print("volume.py - error in command-line syntax")
        usage(1)
    VOLUME.local(sys.argv[1],sys.argv[2],sys.argv[3])
   
