#!/usr/bin/python3
# Copyright (C) 2014-2017 Harold Grovesteen
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

# This module processes files written in the Machine Specification Language (MSL).  The
# following constitutes the description of the MSL.  It is the responsibility of
# users of a file written in MSL to parse and process it as appropriate to its needs.
# It is hoped that the language is simple enough that other scripting languages, for
# example REXX, or Perl, etc.  The module provides both a command line utility
# and a reusable class for processing such files.  The command line utility is intended
# for testing purposes and validation test of a file written in MSL.  A file
# successfully processed by the command line utility should be considered as valid.
#
# Machine Specification Language
# ------- ------------- --------
#
# The Machine Specification Language is a line oriented language.  It does not support
# free flowing text.  A 'line' does not NOT include platform specific line termination
# characters.  A process needs to handle removal of such characters and tolerate
# variations.  If a processor is not able to do that, an external mechanism should
# convert the lines to the platform specific termination before being processed.

# A valid line contains only the ASCII characters 0x20-0x7E, inclusive.  Comments
# are excluded from this requirement.
#
#   1. an empty line (contains only spaces or no characters at all).
#   2. a comment line (starting with either a '*' or '#' in position 1),
#   3. an invalid line (contains characters other than ASCII 0x20-0x7E inclusive),
#   4. a statement line (printable character(s) starting in position 1), or
#   5. a parameter line (printable character(s) starting in position 2 or later),
#
# Only statement and parameter lines are processed.  A processor is also free to ignore
# any statement or parameter line for which it has no interest.  Statement and
# parameter lines may also contain a comment starting with a comment character through
# the remainder of the line.  Character restrictions do not apply to comments.
#
# MSL is _strictly_ case sensitive.  All statement and parameter line information
# is case sensitive.
#
# A 'name' identifies each statement.  Statement names must be unique.  Duplications
# are not allowed.
#
# Python Integration:
#
# Integration of the MSL processor into another Python module is accomplisehed by
# importing this module.  Instatiating
#
# External Processor Integration:
#
# The command line utility provided by this module can output a stripped down version
# of the input file.  This file contains only statement and parameter lines with
# all comments removed.  include statements have been acted upon as well.  This
# reduces some of the processing needs on the part of other processors.

#
# STATEMENT TYPES
# --------- -----
#
# Statements or parameters with a '!' are yet to be implemented.  Parameter
# statements with an '*' may occur multiple times within a statement.

# Include a MSL file into this one.  _Spaces_ within the path are _not_ supported.
#   include path

#   system  <sys-id> [exp]
#      model <model-id>
#      memory <size>[K|M|G]
#      muxdevs <number>

#   model <model-id> [exp]
#      cpu <cpu-id>
# *    channel <chan-id> [standard] [cus <number>] [addr <addr>]
# *    cus <cu-id>...
# *    icu <device-id> [addr]
# *    exclude <device-id>...

#   channel <chan-id> [exp]                      # A channel technology

#   cu <cu-id> [single|dual|shared] [integ] [exp]
# *    channels <channel-id>                     # Channel technologies supported
# *    devices <device-id> ... <device-id>       # Devices attachable to the CU

#   cpu <cpu-id> [exp]
# *    base <iset-id> ... <iset-id>              # Base instruction set features
# *    features <iset-id>                        # Optional instruction set features
# *    exclude <mnemonic> ... <mnemonic>         # Exclude specific instructions
# *    include <mnemonic> ... <mnemonic>         # Include these specific instructions

#   iset <is-id>
# *    mnemonics <mnemonic> ... <mnemonic>       # instruction mnemonic

#   inst <mnemonic> <opcode> <format-id> <priv>  # Instruction definition
# *    fixed <ifield> <hex-value>               # Fixed portion of instruction

#   format <format-id>                           # Instruction format
#      length <bytes>                            # Instruction length in bytes
#      xopcode <start-bit> <end-bit>             # Extended opcode bit positions
# *    mach <mfield> <start-bit> <ending-bit> [signed]   # machine instruction field
# *    source <sfield> <mfield> <mfield>...      # source statement operands

# PYthon imports:
import argparse          # Access the command line parser
import functools         # Allow sorting of objects
import re                # Access regular expression support (see Format.source_proc)
import sys               # Access to exit() method to terminate run

# SATK imports:
import sopl              # Access the Statement Oriented Paramater Language tool

copyright="msldb.py Copyright (C) %s Harold Grovesteen" % "2014, 2015"


#
#  +-------------------------+
#  |                         |
#  |   MSL Error Exception   |
#  |                         |
#  +-------------------------+
#

class MSLError(sopl.SOPLError):
    def __init__(self,loc=None,msg=""):
        super().__init__(loc=loc,msg=msg)

#
#  +--------------------------+
#  |                          |
#  |   MSL Database Objects   |
#  |                          |
#  +--------------------------+
#

# Encodes model statement channel parameter lines
class channel(object):
    def __init__(self,chanid,cus=None,addr=None,standard=False):
        self.chanid=chanid      # Channel technology of this channel
        self.cus=cus            # Number of control units supported by the channel
        self.addr=addr          # Channel address of this channel
        self.standard=False     # If True, the channel is standard with the model

class icu(object):
    def __init__(self,device,addr=None):
        self.device=device      # device ID that attached to CPU integrated CU
        self.addr=addr          # Prefered address of the attached device

class mfield(object):
    rxb={8:0b1000,12:0b0100,16:0b0010,32:0b0001}
    # Used by functools for sorting of mfield objects by starting bit number
    # select_list=sorted(possible,key=functools.cmp_to_key(mfield.compare))
    @staticmethod
    def compare(a,b):
        if a.beg<b.beg:
            return -1
        if a.beg>b.beg:
            return 1
        return 0
    def __init__(self,name,typ,beg,end,signed=False,fixed=False,vector=False):
        self.name=name        # Name of the machine field
        self.typ=typ          # Field type
        self.beg=beg          # starting bit of the field (inclusive of this bit)
        self.end=end          # ending bit of the field (inclusive of this bit)
        self.signed=signed    # If True, field content is signed, otherwise unsigned
        self.fixed=fixed      # If True, a fixed source assigns value
        # Instruction bit where high-order bit of vector register number is placed.
        # Used when a vector register value greater than 15 is supplied.  All
        # vector machine field rxb values are merged together to create the
        # instruction RXB field.
        self.rxb=0
        if vector:
            try:
                self.rxb=mfield.rxb[beg]
            except KeyError:
                cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
                raise ValueError("%s usupported vector register field start: %s" \
                    % (cls_str,beg))
    def __str__(self):
        rxb=self.isvector()
        return "mfield('%s',type='%s',%s,%s,signed=%s,fixed=%s,vector=%s: rxb=0x%X)" \
            % (self.name,self.typ,self.beg,self.end,self.signed,self.fixed,\
                rxb,self.rxb)
    # Returns True or False depending upon whether this is a vector field
    def isvector(self):
        return self.rxb!=0

class soper(object):
    signed=["SY","SYX"]
    def __init__(self,name,typ,mfields=[]):
        self.name=name        # Name of the source operand type
        self.typ=typ          # source operand type
        self.mfields=mfields  # Machine fields populated by this source operand
        self.signed = typ in soper.signed  # Whether the value is signed
    def __str__(self):
        return "soper('%s',type='%s',mfields=%s)" % (self.name,self.typ,self.mfields)

class MSLDB(object):
    def __init__(self):
        self.ids={}       # The underlying database dictionary of all entries

    def __getitem__(self,key):
        return self.ids[key]

    def __setitem__(self,key,item):
        if not isinstance(item,MSLDBE):
            cls_str="msldb.py - %s.__setitem__() -" % self.__class__.__name__
            raise ValueError("%s MSLDB items must be an instance of MSLDBE: %s" \
                % (cls_str,item))
        try:
            #defined=self.ids[item.ID]
            defined=self.ids[key]
            raise MSLError(loc=item.els.source,\
                msg="duplicate %s ID previously defined at %s: %s" \
                    % (item.__class__.__name__,defined.els.source,key))
        except KeyError:
            pass

        #self.ids[item.ID]=item
        self.ids[key]=item

    def dump(self,indent="",string=False,sort=False):
        lcl="%s    " % indent
        s=""
        keys=list(self.ids.keys())
        if sort:
            keys.sort()
        s=""
        for key in keys:
            item=self.ids[key]
            if string:
                s="%s%s%s\n%s%s" \
                    % (s,indent,key,lcl,item.dump(indent=lcl,string=True))
            else:
                print("%s%s" % (indent,key))
                item.dump(indent=lcl,string=False)
        if string:
            return s

    def iter_entries(self):
        return self.ids.values()

    def iter_ids(self):
        return self.ids.keys()

    # This method validates that a ID is present in the database and is of the
    # expected type.  If the object is not present OR is present but not of the
    # expected type a KeyError is raised.
    def validate(self,eid,typ):
        entry=self[eid]
        if typ!=entry.typ:
            raise KeyError()

class MSLDBE(object):
    upper=["format","inst"]
    def __init__(self,els,typ,keep=False):
        cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
        if not isinstance(els,sopl.Statement):
            raise ValueError("%s 'els' argument must be an instance of "
                "ElementStmt: %s" % (cls_str,els))
        if els.typ != typ:
            raise ValueError("%s element type does not match DBE: %s" \
                % (cls_str,els))
        if typ in MSLDBE.upper:
            self.ID=els.ID.upper()
        else:
            self.ID=els.ID
        self.typ=typ
        self.loc=els.source
        self.els=els

    # Validate this statement is consistent with rest of database
    def consistent(self,db):
        cls_str="msldb.py - %s.consistent() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide consistent() method" \
            % cls_str)

    # Return string or print contents of the database entry
    def dump(self,indent="",string=False):
        cls_str="msldb.py - %s.dump() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide dump() method" \
            % cls_str)

    # Returns an expanded version of itself
    def expand(self,db):
        cls_str="msldb.py - %s.expand() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide expand() method" \
            % cls_str)

    # Returns a list of all references to other statement ID's.
    def references(self):
        cls_str="msldb.py - %s.references() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide references() method" \
            % cls_str)

    # Perform internal sanity check in supplied parameters and attributes
    def sanity(self,source):
        cls_str="msldb.py - %s.sanity() -" % self.__class__.__name__
        raise NotImplementedError("%s subclass must provide sanity() method" \
            % cls_str)


#   channel <chan-id> [exp]
class Channel(MSLDBE):
    def __init__(self,els,keep=False):
        super().__init__(els,"channel",keep=keep)

        # channel Statement attrbutes
        self.experimental='exp' in self.attr    # Set experimental attrbute

    def consistent(self): pass

    def dump(self,indent="",string=False):
        if self.experimental:
            exp=" (experimental)"
        else:
            exp=""
        s="%sChannel ID: %s%s" % (indent,self.ID,exp)
        if string:
            return s
        print(s)

    def references(self):
        return []


#   cpu <cpu-id> [exp]
#      addrmax <16|24|31|64>                     # Maximum address size in bits
#      ccw <CCW0|CCW1>                # optional - Expected CCW format for processor
#      psw <PSWS|PSW360|PSW67|PSWBC|PSWEC|PSW380|PSWXA|PSWE370|PSWE390|PSWZ>
#                                                # Expected PSW format for processor
# *    base <iset-id> ... <iset-id>              # Base instruction set features
# *    features <iset-id>                        # Optional instruction set features
# *    exclude <mnemonic> ... <mnemonic>         # Exclude specific instructions
# *    include <mnemonic> ... <mnemonic>         # Include these specific instructions
class CPU(MSLDBE):
    valid_addrsize=[16,24,31,64]
    valid_ccw=["CCW0","CCW1"]
    valid_psw=["PSWS","PSW360","PSW67","PSWBC","PSWEC","PSW380","PSWXA","PSWE370",\
               "PSWE390","PSWZ"]
    def __init__(self,els,keep=False):
        super().__init__(els,"cpu",keep=keep)

        # Statement Attributes
        self.addrmax=None     # Maximum address size in bits
        self.ccw=None         # Expected CCW format to be used by the processor
        self.psw=None         # Expected PSW format to be used by the processor
        self.base=[]          # Base CPU instruction set features
        self.features=[]      # Optional CPU instruction set features
        self.exclude=[]       # instruction mnemonics excluded from features
        self.include=[]       # instruction mnemonics added to features
        self.renames=[]       # List of instruction to be renamed during expansion

        # CPU statement attributes
        self.experimental='exp' in els.attr    # Set experimental attrbute

        cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
        for p in els.parms:
            if p.typ=="addrmax":
                self.addrmax_proc(p)
            elif p.typ=="ccw":
                self.ccw_proc(p)
            elif p.typ=="psw":
                self.psw_proc(p)
            elif p.typ=="base":
                self.base.extend(p.attr)
            elif p.typ=="features":
                self.features.extend(p.attr)
            elif p.typ=="exclude":
                self.exclude.extend(p.attr)
            elif p.typ=="include":
                self.include.extend(p.attr)
            elif p.typ=="rename":
                self.rename_proc(p)
            else:
                raise ValueError("%s invalid parameter type for cpu statement: %s" \
                    % (cls_str,p.typ))

    def addrmax_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="CPU statement addrmax parameter requires one attribute: %s" \
                    % len(elp.attr))

        attr=elp.attr[0]
        try:
            bits=int(attr,10)
        except IndexError:
            raise MSLError(loc=elp.source,\
                msg="CPU statement addrmax parameter must be an integer: %s" % attr)

        if bits not in CPU.valid_addrsize:
            raise MSLError(loc=elp.source,\
                msg="CPU statement addrmax parameter attribut not "
                    "valid (16, 24, 31, 64): %s" % attr)

        self.addrmax=bits

    def ccw_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="CPU statement ccw parameter requires one attribute: %s" \
                    % len(elp.attr))
        attr=elp.attr[0]
        if attr not in CPU.valid_ccw:
            raise MSLError(loc=elp.source,\
                msg="CPU statement ccw parameter attribut not valid: %s" % attr)

        self.ccw=attr

    def consistent(self,db):
        bad_isets=[]
        bad_inst=[]
        error=False
        for alist in [self.base,self.features]:
            for item in alist:
                try:
                    db.validate(item,"iset")
                except KeyError:
                    bad_isets.append(item)
        for alist in [self.exclude,self.include]:
            for x in alist:
                try:
                    db.validate(x,"inst")
                except KeyError:
                    bad_isets.append(x)
        s=""
        if len(bad_isets)>0:
            bad=""
            for aset in bad_isets:
                bad="%s %s," % (bad,aset)
            bad=bad[1:-1]   # Drop ending comma and starting space
            s="%s\n    iset undefined or not an iset statement: %s" % (s,bad)
            error=True

        if len(bad_inst)>0:
            bad=""
            for ainst in bad_inst:
                bad="%s %s," % (bad,ainst)
            bad=bad[1:-1]   # Drop ending comma and starting space
            s="%s\n    inst undefined or not an inst statement: %s" % (s,bad)
            error=True

        if self.addrmax is None:
            s="%s\n    addrmax parameter required, missing" % s
            error=True

        if error:
            raise MSLError(loc=self.loc,\
                msg="cpu %s statement contains errors:%s" % (self.ID,s))

    def dump(self,indent="",string=False):
        if self.experimental:
            exp=" (experimental)"
        else:
            exp=""
        s="%sCPU ID: %s%s" % (indent,self.ID,exp)
        lcl="%s    " % indent
        s="%s\n%saddrmax: %s" % (s,lcl,self.addrmax)
        s="%s\n%spsw:     %s" % (s,lcl,self.psw)
        s="%s\n%sccw:     %s" % (s,lcl,self.ccw)
        s="%s\n%sbase iset's: %s" % (s,lcl,self.base)
        s="%s\n%soptional iset's: %s" % (s,lcl,self.features)
        s="%s\n%sexcluded inst: %s" % (s,lcl,self.exclude)
        s="%s\n%sincluded inst: %s" % (s,lcl,self.include)
        s="%s\n%srenamed inst:  %s" % (s,lcl,self.renames)
        if string:
            return s
        print(s)

    # Expand myself into a CPUX object and return
    def expand(self,db):
        cpux=CPUX(self)
        refs=[]
        refs.extend(self.base)
        refs.extend(self.features)
        for ref in refs:
            iset=db[ref]
            for inst in iset.references():
                i=db[inst]
                cpux.addInst(i)
        for inst in self.exclude:
            i=db[inst]
            cpux.excludeInst(i)
        for inst in self.include:
            i=db[inst]
            cpux.addInst(i)
        for old,new in self.renames:
            cpux.renameInst(old,new)
        cpux.fini(db)
        return cpux

    def psw_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="CPU statement psw parameter requires one attribute: %s" \
                    % len(elp.attr))
        attr=elp.attr[0]
        if attr not in CPU.valid_psw:
            raise MSLError(loc=elp.source,\
                msg="CPU statement psw parameter attribut not valid: %s" % attr)

        self.psw=attr

    def rename_proc(self,elp):
        if len(elp.attr)!=2:
            raise MSLError(loc=elp.source,\
                msg="CPU statement rename parameter requires two attributes: %s" \
                    % (len(elp.attr)))
        rename=(elp.attr[0],elp.attr[1])
        self.renames.append(rename)

    def references(self):
        refs=[]
        refs.extend(self.base)
        refs.extend(self.features)
        refs.extend(self.exclude)
        refs.extend(self.include)
        return refs


# Expanded version of CPU statement
class CPUX(object):
    def __init__(self,cpu):
        self.ID=cpu.ID    # ID of expanded CPU object
        self.loc=cpu.loc  # Location of expanded CPU object
        self.inst={}      # Supported instructions Inst objects
        self.formats={}   # Format objects used by Inst objects

        self.addrmax=cpu.addrmax  # Maximum address size in bits
        self.ccw=cpu.ccw          # Expected CCW Format in use by CPU
        self.psw=cpu.psw          # Expected PSW Format in use by CPU

    def addInst(self,inst):
        try:
            entry=self.inst[inst.ID]
            cls_str="msldb.py - %s.addInst() -" % self.__class__.__name__
            raise ValueError("%s duplicate inst ID: %s" % (cls_str,inst.ID))
        except KeyError:
            self.inst[inst.ID]=inst
            format=inst.format

    def dump(self,indent="",string=False,sort=False):
        lcl="%s    " % indent

        s="CPUX ID: %s" % self.ID
        if not string:
            print(s)
            s=""

        # Dump instructions
        keys=list(self.inst.keys())
        if sort:
            keys.sort()
        for key in keys:
            item=self.inst[key]
            if string:
                s="%s%s%s\n%s%s" \
                    % (s,indent,key,lcl,item.dump(indent=lcl,string=True))
            else:
                print("%s%s" % (indent,key))
                item.dump(indent=lcl,string=False)
                s=""
        # Dump formats
        keys=list(self.formats.keys())
        if sort:
            keys.sort()
        for key in keys:
            item=self.formats[key]
            if string:
                s="%s%s%s\n%s%s" \
                    % (s,indent,key,lcl,item.dump(indent=lcl,string=True))
            else:
                print("%s%s" % (indent,key))
                item.dump(indent=lcl,string=False)
                s=""
        if string:
            return s

    def excludeInst(self,inst):
        try:
            del self.inst[inst.ID]
        except KeyError:
            pass

    def fini(self,db):
        for inst in self.inst.values():
            format=inst.format
            try:
                self.formats[format]
                # already in dictionary, no need to add it
            except KeyError:
                # Not in dictionary
                fmt=db[format]            # Get the Format from the MSLDB
                self.formats[format]=fmt  # Add it to my dictionary

    def renameInst(self,old,new):
        try:
            inst=self.inst[old]
        except KeyError:
            return
        del self.inst[old]
        inst.ID=new
        self.inst[new]=inst

    def summarize(self,indent="",string=False,sort=False):
        lcl="%s    " % indent
        s="CPUX ID: %s" % self.ID
        if not string:
            print(s)
            s=""

        # Dump instructions
        keys=list(self.inst.keys())
        if sort:
            keys.sort()
        for key in keys:
            if string:
                s="%s\nINST %s" % (lcl,key)
            else:
                print("%sINST %s" % (lcl,key))

        # Dump formats
        keys=list(self.formats.keys())
        if sort:
            keys.sort()
        for key in keys:
            if string:
                s="%s\nFORMAT: %s" % (lcl,key)
            else:
                print("%sFORMAT: %s" % (lcl,key))

        if string:
            return s


#   cu <cu-id> [single|dual|shared] [integ] [exp]
# *    channels <channel-id>                     # Channel technologies supported
# *    devices <device-id> ... <device-id>       # Devices attachable to the CU
class CU(MSLDBE):
    def __init__(self,els,keep=False):
        super().__init__(els,"cu",keep=keep)

        # Statement attributes
        self.single=None            # cu supports one channel
        self.dual=None              # cu supports two channels, one active
        self.shared=None            # cu supports two active channels
        self.integrated=False       # cu functionality is integrated
        self.experimental=False     # cu is experimental
        self.channels=[]            # channel technologies supported by CU
        self.devices=[]             # devices attachable to control unit

        attr=self.attr
        for x in range(len(attr)):
            at=attr[x]
            if at == "single":
                self.single=True
                self.dual=False
                self.shared=False
            elif at == "dual":
                self.single=False
                self.dual=True
                self.shared=False
            elif at == "shared":
                self.single=False
                self.dual=False
                self.shared=False
            elif at == "integ":
                self.integrated=True
            elif at == "exp":
                self.experimental=True
            else:
                raise MSLError(loc=els.source,\
                    msg="cu statement attribute not recognized: %s" % at)

        for p in els.parms:
            if p.typ=="channels":
                self.channels.extend(p.attr)
            elif p.typ=="devices":
                self.devices.extend(p.attr)
            else:
                raise ValueError("%s invalid parameter type for format statement: %s" \
                    % (cls_str,p.typ))


#   format <format-id>                           # Instruction format
#      length <bytes>                            # Instruction length in bytes
#      xopcode <start-bit> <end-bit>             # Extended opcode bit positions
# *    mach <mfield> <start-bit> <ending-bit> [signed] [fixed]   # instruction field
# *    source <sfield> <mfield> <mfield>...      # source statement operands
class Format(MSLDBE):
    lengths=[2,4,6]   # Valid instruction length sizes in bytes
    # The sops source operand names are tightly coupled to ASMA.  Changes there or
    # here must be coordinated.  This dictionary maps source operand type to the
    # number of machine fields to which it provides values.
    sops={"I":1,"M":1,"R":1,"RELI":1,"RI":1,"V":1,"S":2,\
          "SY":3,"SL":3,"SR":3,"SX":3,"SYL":4,"SYX":4}
    mflds=["B","D","DH","DL","I","L","M","R","RELI","RI","RXB","V","X"]
    # Machine fields supplied by the assembler.  No match with a source field
    # is required for these machine field types.
    asm=["RXB",]
    styp_re=re.compile(r'([A-Z]+)([0-9]+)?')
    def __init__(self,els,keep=False):
        super().__init__(els,"format",keep=keep)

        # Statement Attributes
        self.length=None        # Instruction length in bytes
        self.mach={}            # Machine field definitions
        self.soper={}           # Source operand definitions
        self.soper_seq=[]       # Source operand sequence by operand names
        self.stype_seq=[]       # Source operand sequence by operand types
        # Instruction opcode placement
        self.opcode={"OP":mfield("OP","OP",0,7)}  # This dict has two keys: OP, OPX

        cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
        for p in els.parms:
            if p.typ=="length":
                self.length_proc(p)
            elif p.typ=="mach":
                self.mach_proc(p)
            elif p.typ=="source":
                self.source_proc(p)
            elif p.typ=="xopcode":
                self.xopcode_proc(p)
            else:
                raise ValueError("%s invalid parameter type for format statement: %s" \
                    % (cls_str,p.typ))

        # Make sure the mach and source fields make sense
        self.sanity(els.source)

    def bit_range(self,beg,end,parm,loc):
        try:
            beg_bit=int(beg,10)
        except IndexError:
            raise MSLError(loc=loc,\
                msg="format %s statement %s parameter starting bit number not "
                    "numeric: %s" % (self.ID,parm,begin))
        try:
            end_bit=int(end,10)
        except IndexError:
            raise MSLError(loc=loc,\
                msg="format %s statement %s parameter ending bit number not "
                    "numeric: %s" % (self.ID,parm,begin))
        return (beg_bit,end_bit)

    def consistent(self,db):
        # This statement does not reference any other statements so there is
        # nothing to validate for consistency with the database.
        pass

    def dump(self,indent="",string=False):
        s="%sFormat ID: %s" % (indent,self.ID)
        lcl="%s    " % indent
        s="%s\n%sinst length: %s" % (s,lcl,self.length)
        for key,item in self.opcode.items():
            s="%s\n%sopcode  %s = %s" % (s,lcl,key,item)
        for key,item in self.mach.items():
            s="%s\n%smachine %s = %s" % (s,lcl,key,item)
        for key,item in self.soper.items():
            s="%s\n%ssource  %s = %s" % (s,lcl,key,item)
        s="%s\n%ssource seq: %s" % (s,lcl,self.soper_seq)
        s="%s\n%stype seq:   %s" % (s,lcl,self.stype_seq)
        if string:
            return s
        print(s)

    def length_proc(self,elp):
        if self.length is not None:
            raise MSLError(loc=elp.source,\
                msg="format statement encounterd more than one length parameter ")

        length=elp.attr[0]
        try:
            l=int(length,10)
        except IndexError:
            raise MSLError(loc=elp.source,\
                 msg="format %s invalid length parameter not numeric: %s" \
                     % (self.ID,length))
            self.length=Format.lengths[length]
        if l not in Format.lengths:
             raise MSLError(loc=elp.source,\
                 msg="format %s invalid length parameter: %s" % (self.ID,length))
        self.length=l

    # <mfield> <start-bit> <ending-bit> [signed] [fixed]
    def mach_proc(self,elp):
        attr=elp.attr
        if len(attr)==0:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'mach' parameter field definition missing"\
                    % elp.ID)
        if len(attr)>5:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'mach' parameter contains too many "
                "attributes: %s" % (self.ID,len(attr)))
        if len(attr)<3:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'mach' parameter requires between 3 and 5 "
                     "attributes incomplete, found: %s" % (self.ID,len(attr)))
        mfld=attr[0].upper()
        typ,num=self.separate(mfld,elp.source,"mach")
        if typ not in Format.mflds:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'mach' parameter 'mfield' type "
                "invalid: %s" % (self.ID,typ))

        # Determine if the machine field is a vector register.  They require
        # special handling for the high-order bit of the register number.
        vector = typ=="V"

        # Determine if the supplied value is signed
        signed=False
        fixed=False
        if len(attr)>3:
            for a in attr[3:]:
                if a == "signed":
                    signed=True
                elif a == "fixed":
                    fixed=True
                else:
                    raise MSLError(loc=elp.source,\
                        msg="format %s statement 'mach' parameter %s contains "
                            "unrecognized attribute: %s" % (self.ID,mfld,a))

        beg_bit,end_bit=self.bit_range(attr[1],attr[2],"machine",elp.source)
        if beg_bit>end_bit:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'mach' parameter %s beginning bit follows "
                     "ending bit: %s>%s" % (self.ID,mfld,beg_bit,end_bit))

        mfieldo=mfield(mfld,typ,beg_bit,end_bit,\
            signed=signed,vector=vector,fixed=fixed)

        # Make sure the machine field was not previously defined
        try:
            self.mach[mfld]
            raise MSLError(loc=elp.source,\
                msg="'mach' field previously defined: %s" % mfld)
        except KeyError:
            self.mach[mfld]=mfieldo

    # This statement does not reference any others
    def references(self):
        return []

    def sanity(self,loc):
        undefined=[]     # List of machine fields in source parameters not defined
        unreferenced=[]  # List of machine fields for which no source is identified
        multiple=[]      # List of machine fields with multiple source operands
        overlap=[]       # List of machine fields that overlap another field
        out_of_range=[]  # List of machine fields outside the valid instruction.

        fldsrc={}        # Working dictionary of machine field references
        for key,mfld in self.mach.items():
            # Don't look for a source if the assembler supplies the field
            # or it is defined in the instruction with a fixed value
            if key in Format.asm or mfld.fixed:
                continue
            fldsrc[key]=[]

        for item in self.soper.values():
            sfld=item.name
            for mfld in item.mfields:

                # Determine if source parameter references any undefined mach fields
                try:
                    self.mach[mfld]
                except KeyError:
                    undefined.append(mfld)
                    continue

                # Determine if machine has more than one source by tracking 'source'
                # parameter references.
                msrc=fldsrc[mfld]
                msrc.append(sfld)

        for key,item in fldsrc.items():
            if len(item)==0:
                unreferenced.append(key)
            if len(item)>1:
                multiple.append(key)

        max_bit=(8*self.length)-1
        for mfld in self.mach.values():
            if mfld.beg>max_bit or mfld.end>max_bit:
                out_of_range.append(mfld.name)

        if len(self.mach)>1:
            fields=list(self.mach.values())
            fields.extend(list(self.opcode.values()))
            sorted_fields=sorted(fields,key=functools.cmp_to_key(mfield.compare))
            for x in range(len(sorted_fields)-1):
                this=sorted_fields[x]
                next=sorted_fields[x+1]
                if next.beg<=this.end:
                    # fields overlap
                    overlap.append(next.name)

        # Build error info:
        error=False
        s=""
        if self.length is None:
            s="\n    required parameter length missing"
        if len(undefined)>0:
            undef=""
            for field in undefined:
                undef="%s %s," % (undef,field)
            undef=undef[1:-1]   # Drop ending comma and starting space
            s="%s\n    source parameters reference undefined mach field(s): %s" \
                % (s,undef)
            error=True
        if len(multiple)>0:
            mult=""
            for field in multiple:
                mult="%s %s," % (mult,field)
            mult=mult[1:-1]
            s="%s\n    machine field(s) have multiple sources: %s" % (s,mult)
            error=True
        if len(unreferenced)>0:
            unref=""
            for field in unreferenced:
                unref="%s %s," % (unref,field)
            unref=unref[1:-1]
            s="%s\n    machine field(s) without a source: %s" % (s,unref)
            error=True
        if len(out_of_range)>0:
            oor=""
            for field in out_of_range:
                oor="%s %s," % (oor,field)
            oor=oor[1:-1]
            s="%s\n    machine field(s) outside of instruction boundary: %s" % (s,oor)
            error=True
        if len(overlap)>0:
            over=""
            for field in overlap:
                over="%s %s," % (over,field)
            over=over[1:-1]
            s="%s\n    machine field(s) overlap another: %s" % (s,over)
            error=True
        if error:
            raise MSLError(loc=loc,\
                msg="format %s statement contains errors:%s" % (self.ID,s))

    # Returns a tuple from a source or machine name: (type,number)
    # Raises an MSLError if the format is not recognized
    def separate(self,name,loc,parm):
        # The use of a regular expression to separate the name's number from its type
        # is strictly one of convenience.  It is quite feasible to perform the
        # separation by simpler methods if needed by some other processor.
        match=Format.styp_re.match(name)
        if match is None:
            raise MSLError(loc=loc,\
                msg="%s parameter name unrecognizable: %s" % (parm,name))
        return match.groups()

    def source_proc(self,elp):
        attr=elp.attr
        if len(attr)==0:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'source' parameter field definition missing"\
                    % elp.ID)
        if len(attr)<2:
            raise MSLError(loc=elp.source,\
                msg="format %s statement 'source' parameter machine fields missing"\
                    % elp.ID)
        name=attr[0].upper()

        typ,num=self.separate(name,elp.source,"source")

        try:
            num_fields=Format.sops[typ]
        except KeyError:
            raise MSLError(loc=elp.source,\
                msg="source operand name invalid: '%s'" % (name))
        if len(attr)!=num_fields+1:
            raise MSLError(loc=elp.source,\
                msg="source operand %s requires %s machine fields: %s" \
                    % (name,num_fields,len(attr)-1))
        oper=soper(name,typ,mfields=attr[1:])
        try:
            self.soper[name]
            raise MSLError(loc=elp.source,\
                msg="'source' operand previously defined: %s" % name)
        except KeyError:
           self.soper[name]=oper
        self.soper_seq.append(name)
        self.stype_seq.append(typ)

    def xopcode_proc(self,elp):
        attr=elp.attr
        if len(attr)==0:
            raise MSLError(loc=elp.source,\
                msg="format %s statement xopcode parameter bit range missing"\
                    % self.ID)
        if len(attr)<2:
            raise MSLError(loc=elp.source,\
                msg="format %s statement xopcode paramater missing ending bit number" \
                    % self.ID)
        if len(attr)>2:
            raise MSLError(loc=elp.source,\
                msg="format %s statement xopcode paramater has too many "
                    "attributes %s" % (self.ID,len(attr)))

        beg_bit,end_bit=self.bit_range(attr[0],attr[1],"xopcode",elp.source)
        try:
            self.opcode["OPX"]
            raise MSLError(loc=elp.source,\
               msg="format %s statement xopcode parameter previously defined" \
                   % self.ID)
        except KeyError:
            self.opcode["OPX"]=mfield("OPX","OPX",beg_bit,end_bit)


#   inst <mnemonic> <opcode> <format-id> [flags]  # Instruction definition
#            ID     <-------attributes--------->
#       fixed <ifield> <hex-value>
class Inst(MSLDBE):
    opcode_factor=[None,None,1,16,256]
    priv={"G":False,"P":True}    # Values for privileged operation mode eligibility
    pstr={False:"G",True:"C"}    # Printable values for privilege eligibility
    bits2={0b00:2,0b01:4,0b10:4,0b11:6}  # converts bits 0,1 of opcode to length
    def __init__(self,els,keep=False):
        super().__init__(els,"inst",keep=keep)

        # Statement Attributes
        self.mnemonic=self.ID.upper() # instruction mnemonic in upper case
        self.opcode=[None,None]       # Opcode split into base and extended parts
        self.opc_len=None             # Length of the opcode in hex digits
        self.format=None              # Instruction Format ID

        # Flag values
        self.priv=False               # 'P' sets True, for a privileged instruction
        self.extended=False           # 'E' sets True, for an extended mnemonic
        self.experimental=False       # 'X' sets True, for an experimental instruction
        self.nolenck=False            # 'L' sets True, do not check bits 0,1 vs format

        # Fixed constant instruction content fields
        self.fixed=[]                 # List of fixed ifield names
        self.fixed_value={}           # Values assigned to the fixed ifield

        attr=els.attr
        if len(attr)==0:
            raise MSLError(loc=els.source,\
                msg="inst %s statement attributes missing" % elp.ID)
        if len(attr)<2 or len(attr)>4:
            raise MSLError(loc=els.source,\
                msg="inst %s statement requires 2 or 3 attributes, found: %s" \
                    % (self.ID,len(attr)))

        # Validate OP Code
        attr=els.attr
        opcode=attr[0]
        if len(opcode)>4 or len(opcode)<2:
            raise MSLErro("inst %s statement opcode must between 2 and 4 hex digits: %s" \
                % (self.ID,opcode))

        opc_len=len(opcode)
        factor=Inst.opcode_factor[opc_len]

        try:
            opc=int(opcode,16)
        except IndexError:
            raise MSLError(loc=els.source,\
                msg="inst %s statement opcode not hex: %s" % (self.ID,opcode))
        self.opcode=list(divmod(opc,factor))
        self.opc_len=opc_len

        # Set format ID
        self.format=attr[1].upper()

        # Set optional flags
        if len(attr)==3:  # Flags are present
            flags=attr[2]
            invalid=""
            for flag in flags:  # Examine each flag separately
                if flag == "P":
                    self.priv=True
                    continue
                if flag == "E":
                    self.extended=True
                    continue
                if flag == "L":
                    self.nolenck=True
                    continue
                if flag == "X":
                    self.experimental=True
                    continue
                invalid="%s%s" % (invalid,flag)

            if len(invalid)!=0:
                raise MSLError(loc=els.source,\
                    msg="inst %s statement contains one or more unrecognized "
                        "flags: '%s' " % (self.ID,invalid))

        for p in els.parms:
            if p.typ=="fixed":
                self.fixed_proc(p)
            else:
                raise ValueError("%s invalid parameter type for inst statement: %s" \
                    % (cls_str,p.typ))

    def consistent(self,db):
        try:
            db.validate(self.format,"format")
        except KeyError:
            raise MSLError(loc=self.loc,\
                msg="inst %s format statement not defined or not a format "
                    "statement: %s" % (self.mnemonic,self.format))
        if self.nolenck:
            return
        format=db[self.format]
        two_bits=self.opcode[0]>>6
        length=Inst.bits2[two_bits]
        if length != format.length:
            raise MSLError(loc=self.loc,\
                msg="inst %s opcode implies a length of %s bytes, but format %s "
                    "requires length: %s" % (self.ID,length,format.ID,format.length))

        # Ensure format and instruction fixed fields are consistent
        mfields=format.mach
        for ff in self.fixed:
            try:
                ffield=mfields[ff]
            except KeyError:
                raise MSLError(loc=self.loc,\
                    msg="inst %s fixed source %s not found in format %s" \
                        % (self.ID,ff,format.ID))
            if not ffield.fixed:
                raise MSLError(loc=self.loc,\
                    msg="inst %s fixed source %s not a fixed field in format %s" \
                        % (self.ID,ff,format.ID))

    def dump(self,indent="",string=False):
        s="%sInst ID: %s" % (indent,self.ID)
        lcl="%s    " % indent
        s="%s\n%smnemonic: %s" % (s,lcl,self.mnemonic)
        s="%s\n%sopcode: %s" % (s,lcl,self.opcode)
        s="%s\n%sopcode digits: %s" % (s,lcl,self.opc_len)
        s="%s\n%sformat: %s" % (s,lcl,self.format)
        s="%s\n%sprivileged: %s" % (s,lcl,self.priv)
        for f in self.fixed:
            s="%s\n%sfixed %s: %s" % (s,lcl,f,self.fixed_value[f])
        if string:
            return s
        print(s)

    def fixed_proc(self,fparm):
        attr=fparm.attr
        if len(attr) != 2:
            raise MSLError(loc=fparm.source,\
                msg="inst statement fixed parameter requires two attributes: %s" \
                    % len(attr))

        # Make sure no duplicate fixed parmaters
        fchar=attr[0]
        if fchar in self.fixed:
            raise MSLError(loc=fparm.source,\
                msg="inst %s statement duplicate fixed field: %s" % (self.ID,fchar))

        # Process value field
        vchar=attr[1]
        try:
            #value=int(vchar,16)
            value=int(vchar,0)
        except IndexError:
            raise MSLError(loc=fparm.source,\
                msg="inst %s statement fixed field %s value not hex: %s" \
                    % (self.ID,field,vchar))

        # Add to objects interpreted value
        self.fixed.append(fchar)
        self.fixed_value[fchar]=value

    def references(self):
        return [self.format,]


#   iset <is-id>
# *    mnemonics <mnemonic> ... <mnemonic>       # instruction mnemonic
class Iset(MSLDBE):
    def __init__(self,els,keep=False):
        super().__init__(els,"iset",keep=keep)

        # Attributes
        self.mnemonics=[]

        cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
        for p in els.parms:
            if p.typ=="mnemonics":
                for m in p.attr:
                    self.mnemonics.append(m.upper())
            else:
                raise ValueError("%s invalid parameter type for iset statement: %s" \
                    % (cls_str,p.typ))

    def consistent(self,db):
        bad=[]
        error=False
        for x in self.mnemonics:
            try:
                db.validate(x,"inst")
            except KeyError:
                bad.append(x)

        if len(bad)>0:
            invalid=""
            for inst in bad:
                invalid="%s %s," % (invalid,inst)
            invalid=invalid[1:-1]   # Drop ending comma and starting space
            s="\n    inst statement(s) undefined or not an inst statement: %s" \
                % invalid
            error=True

        if error:
            raise MSLError(loc=self.loc,\
                msg="iset %s statement contains errors:%s" % (self.ID,s))

    def dump(self,indent="",string=False):
        s="%sIset ID: %s" % (indent,self.ID)
        lcl="%s    " % indent
        s="%s\n%smnemonics: %s" % (s,lcl,self.mnemonics)
        if string:
            return s
        print(s)

    def references(self):
        return self.mnemonics


#   model <model-id> [exp]
#       cpu <cpu-id>
# *     channel <chan-id> <max-cu> [addr] [standard]
# *     cus <cu-id>...
# *     icu <device-id> [addr]
# *     exclude <device-id>...
class Model(MSLDBE):
    def __init__(self,els,keep=False):
        super().__init__(els,"model",keep=keep)

        self.cpu=None          # cpu-id of this model's CPU specification
        self.channels=[]       # List of channel objects for channel parameter lines
        self.cus=[]            # Lisf of supported control unit id's
        self.icus=[]           # List of icu object for icu parameter lines
        self.exclude=[]        # List of excluded devices

        # Model statement attributes
        self.experimental='exp' in self.attr   # Experimental indicator

        for p in els.parms:
            if p.typ=="cpu":
                self.cpu_proc(p)
            elif p.typ=="channel":
                self.channel_proc(p)
            elif p.typ=="cus":
                self.cus.extend(p.attr)
            elif p.typ=="icu":
                self.icu_proc(p)
            elif p.typ=="exclude":
                self.exclude.extend(p.attr)
            else:
                cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
                raise ValueError("%s invalid parameter type for moodel statement: %s" \
                    % (cls_str,p.typ))

    def channel_proc(self,elp):
        standard=False
        maxcu=None
        addr=None
        attr=elp.attr

        if len(attr)>4 or len(attr)<3:
            raise MSLError(loc=elp.source,\
                msg="model statement channel parameter requires 2 to 4 "
                    "attributes: %s" % len(attr))

        chanid=attr[0]

        try:
            maxcu=int(attr[1],10)
        except IndexError:
            raise MSLError(loc=elp.source,\
                msg="model statement channel parameter max-cu attribute 2 not "
                "numeric: %s" % attr[1])

        for x in range(2,len(attr)):
            at=attr[x]
            if at == "standard":
                if standard is True:
                    raise MSLError(loc=elp.source,\
                        msg="model statement channel parameter attribute %s multiple"
                            "standard attributes excounterd" % x+1)
                standard=True
            else:
                if addr is not None:
                    raise MSLError(loc=elp.source,\
                         msg="model statement channel parameter attribute %s multiple"
                             "addr attributes excounterd" % x+1)
                try:
                    addr=int(at,16)
                except IndexError:
                     raise MSLError(loc=elp.source,\
                         msg="model statement channel parameter addr attribute %s not "
                              "hexadecimal: %s" % (x+1,at))

        self.channels.append(channel(chanid,cus=maxcu,addr=addr,standard=standard))

    def cpu_proc(self,elp):
        attr=elp.attr
        if len(attr)==1:
            raise MSLError(loc=elp.source,msg="model statement cpu parameter "
                "requires one attrbiute: %s" % len(attr))
        if self.cpu is not None:
            raise MSLError(loc=elp.source,msg="model statement cpu parameter "
                "previously defined, only one allowed" % len(attr))

        self.cpu=attr[0]

    def icu_proc(self,elp):
        addr=None
        attr=elp.attr
        if len(attr)<1 or len(attr)>2:
            raise MSLError(loc=elp.source,\
                msg="model statement icu parameter requires 1 or 2 attributes: %s" \
                    % len(attr))
        device=attr[0]
        if len(attr)==2:
            try:
                addr=int(attr[1],16)
            except IndexError:
                raise MSLError(loc=elp.source,\
                    msg="model statement icu parameter addr attribute not "
                    "hexadecimal: %s" % attr[1])
        self.icus.append(icu(device,addr=addr))


#   system  <sys-id> [exp]
#      model <model-id>
#      memory <size>[K|M|G]
#      muxdevs <number>
class System(MSLDBE):
    memory_units={"K":1024,"M":1024*1024,"G":1024*1024*1024}
    def __init__(self,els,keep=False):
        super().__init__(els,"system",keep=keep)

        # Statement attributes
        self.experimental=False       # Experimental system
        self.model=None
        self.memory=None
        self.muxdevs=[]

        attr=els.attr
        if len(attr)>1:
            raise MSLError(loc=els.source,\
                msg="system statement supports only one optional attribute: %s" \
                    % len(attr))
        if attr[0]!="exp":
            raise MSLError(loc=els.source,\
                msg="system statement attribute 1 not recognized: %s" % attr[0])
        else:
            self.experimental=True

        for p in els.parms:
            if p.typ=="model":
                self.model_proc(p)
            elif p.typ=="memory":
                self.memory_proc(p)
            elif p.typ=="muxdevs":
                self.muxdevs_proc(p)
            else:
                cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
                raise ValueError("%s invalid parameter type for system statement: %s" \
                    % (cls_str,p.typ))

    def memory_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="system statement memory parameter requires one attribute: %s" \
                    % len(elp.attr))
        if self.memory is not None:
            raise MSLError(loc=elp.source,
                msg="system statement supports only one memory parameter")
        memory=elp.attr[0]
        unit=memory[-1]
        try:
            unit=System.memory_units[unit]
            memory=memory[:-1]
        except KeyError:
            unit=1
        try:
            quantity=int(memory,10)
        except IndexError:
            raise MSLError(loc=elp.source,\
                msg="system statement memory parameter size not numeric: %s" \
                    % memory)
        self.memory=unit*memory

    def model_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="system statement model parameter requires one attribute: %s" \
                    % len(elp.attr))
        if self.model is not None:
            raise MSLError(loc=elp.source,
                msg="system statement supports only one model parameter")
        self.model=elp.attr[0]

    def muxdevs_proc(self,elp):
        if len(elp.attr)!=1:
            raise MSLError(loc=elp.source,\
                msg="system statement muxdevs parameter requires one attribute: %s" \
                    % len(elp.attr))
        if self.muxdevs is not None:
            raise MSLError(loc=elp.source,
                msg="system statement supports only one muxdevs parameter")

        muxdevs=elp.attr[0]
        try:
            mux=int(muxdevs,10)
        except IndexError:
            raise MSLError(loc=elp.source,\
                msg="system statement muxdevs parameter attribute not numeric: %s" \
                    % muxdevs)

#
#  +----------------------------------------------+
#  |                                              |
#  |   Machine Specification Language Processor   |
#  |                                              |
#  +----------------------------------------------+
#

# Instance Argument:
#   default   A string identifying the default directory for includes if MSLPATH
#             is not defined.
class MSL(sopl.SOPL):
    statements={"cpu":CPU,
                "format":Format,
                "inst":Inst,
                "iset":Iset}
    def __init__(self,default=None,pathmgr=None,debug=False):
        self.db=MSLDB()          # The master database being built

        # Attribute supplied by the build() method
        self.fail=False          # Immediate failure flag
        self.xref=None           # MSLxref object if build(xref=True)

        # Instantiate super class.  Use 'MSLPATH' environment variable for includes
        # or supplied default directory.
        super().__init__(variable="MSLPATH",default=default,pathmgr=pathmgr,\
            debug=debug)

    # Processes SOPL Statmeent and Parameter objects, creating the MSL database.
    # Method arguments:
    #   See build() method for argument usage.
    def __process(self,keep=False,xref=False,dead=False,debug=False):
        cls_str="msldb.py - %s.__process() -" % self.__class__.__name__

        # Use SOPL to process text into sopl.Statement and sopl.Parameter objects
        #self.pre_process(debug=debug)
        db=self.db

        # Build the database from the sopl.Statement objects
        for s in self.getStmts():
            typ=s.typ
            try:
                cls=MSL.statements[typ]
            except KeyError:
                raise ValueError("%s unrecognized statement ID: %s" % (cls_str,typ))
            dbe=cls(s,keep=keep)
            db[dbe.ID]=dbe

        # Make sure database is consistent
        for s in db.iter_entries():
            try:
                s.consistent(db)
            except MSLError as me:
                self._do_error(error=me)

        # Build XREF and find any 'dead' (unreferenced statements)
        if dead:
            xrefdb=MSLxref(self.db)
            # Check for dead statements.  Passing myself gives access to _do_error()
            xrefdb.check(self,xref=xref)

    # This method builds a database based upon an MSL source file as input.  It it
    # the primary method used by an MSL consumer in constructing the MSL database.
    # Method arguments:
    #   filename    The path to the primary MSL source file
    #   xref        Specify True to generate a cross-reference listing
    #   keep        Causes SOPL object to be kept in MSLDBE objects
    #   fail        Specify True to fail immediately upon detection of an error
    #   dead        Specify True to analyze database for dead objects.
    #   debug       Specify True to have intermediate results printed
    # Returns:
    #   True if errors detected during the build of the MSL database
    #   False otherwise.
    def build(self,filename,xref=False,keep=False,fail=False,dead=False,debug=False):

        # Use SOPL to read and recognize statements
        self.recognize(filename,fail=fail,debug=debug)
        # SOPL has created sopl.Statement and sopl.Parameter objects

        # Process my statements into subclasses of MSLDBE objects
        self.__process(keep=keep,xref=xref,dead=dead,debug=debug)

        # Return if there were any detected errors.
        return self.isErrors()

    # Returns the MSLDB object
    def DB(self):
        if self.isErrors():
            cls_str="msldb.py - %s.DB() -" %  self.__class__.__name__
            raise ValueError("%s database build in error" % cls_str)
        return self.db

    # Provides a deatiled listing of the database content
    def dump(self,indent="",string=False):
        s=self.db.dump(indent=indent,string=string)
        if string:
            return s

    # expand a single hardware component and all of its dependent statements
    def expand(self,item):
        cls_str="msldb.py - %s.expand() -" % self.__class__.__name__
        try:
            expitem=self.db[item]
        except KeyError:
            raise ValueError("%s '--expand' database ID does not exist: %s" \
                % (cls_str,item)) from None
        if expitem.typ != "cpu":
            raise ValueError("%s MSL database entry %s can not be expanded: %s" \
                % (cls_str,item,expitem.typ)) from None
        expanded=expitem.expand(self.db)
        return expanded

    # Register my statements and parameters with the SOPL super class.
    def register(self):
        self.regStmt("channel")
        self.regStmt("cpu",parms=\
            ["addrmax","base","features","exclude","include","ccw","psw","rename"])
        self.regStmt("cu",parms=["channels","devices"])
        self.regStmt("format",parms=["length","mach","source","xopcode"])
        self.regStmt("iset",parms=["mnemonics",])
        self.regStmt("inst",parms=["fixed",])
        self.regStmt("model",parms=["cpu","channel","cus","icu","exclude"])
        self.regStmt("system",parms=["model","memory","muxdevs"])

# This class creates a cross reference database and if requested listing.
class MSLxref(object):
    def __init__(self,db):
        xrefdb={}
        top=["cpu"]
        keys=list(db.iter_ids())
        # Build the initial statement database of xref objects
        for key in keys:
            stmt=db[key]
            xrefo=xref(key,stmt.loc,stmt.typ in top)
            xrefdb[key]=xrefo

        # Get all of the statement references and update the objects.
        for key in keys:
            stmt=db[key]
            loc=stmt.loc
            refs=stmt.references()
            for r in refs:
                st=xrefdb[r]
                st.ref(loc)

        # Save the final database
        self.xrefdb=xrefdb

    # Check the XREF data for dead statements.
    def check(self,msl,xref=False):
        dead=[]
        xrefd=self.xrefdb
        keys=list(xrefd.keys())

        for key in keys:
            xrefo=xrefd[key]
            if not xrefo.check():
                dead.append(key)

        self.xref=xrefd     # Save the XREF data object

        if len(dead)>0:
            noref=""
            for stmt in dead:
                noref="%s %s," % (noref,stmt)
            noref=noref[1:-1]   # Drop ending comma and starting space
            if xref:
                me=MSLError(\
                    msg="unreferenced statement in database: %s" % (noref))
                msl._do_error(error=me)
            else:
                print("unreferences statement(s) in database: %s" % (noref))

# A statement's cross reference information
class xref(object):
    def __init__(self,ID,loc,top=False):
        self.ID=ID        # Statement ID
        self.loc=loc      # Statement's definition within the source
        self.top=top      # If this statement at the top of the hierarchy
        self.refs=[]      # References to this statement

    # Update the data with a reference
    def ref(self,loc):
        self.refs.append(loc)

    # Returns whether a statement is referenced.  Top entries are implicitly referenced
    def check(self):
        return len(self.refs)>0 or self.top

if __name__ == "__main__":
    raise NotImplementedError("msldb.py - intended for import use only")
