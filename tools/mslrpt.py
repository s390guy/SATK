#!/usr/bin/python3
# Copyright (C) 2014-2022 Harold Grovesteen
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

# This module provides a reporting tool of information contained in Machine
# Specification Language (MSL) database files. For a description of the MSL, see
# module msldb.py.

this_module="mslrpt.py"
copyright="%s Copyright (C) %s Harold Grovesteen" \
    % (this_module,"2014-2022")

# Python imports:
import sys               # Access the exit method
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse          # Access the command line parser
import functools         # Access complex sorting sequences

# Setup PYTHONPATH
import satkutil          # Access utility functions
satkutil.pythonpath("asma")        # Provides path to msldb.py
satkutil.pythonpath("tools/lang")  # Provides path to sopl.py needed by msldb

# ASMA imports
import msldb             # Access the database

# SATK imports
from listing import *    # Access the formatted report tools

# This wraps a msldb.CPUX object with report information
class CPU(object):
    def __init__(self,col,filename,cpux):
        # The column ndx into which this CPU instruction's flags are placed
        self.col=col
        self.filename=filename   # The MSL filename upon which this cpu is based
        self.cpux=cpux           # msldb.CPUX object constructed from the MSL file
        #self.count=0
    def __str__(self):
        # Note cpux.ID is the CPU name from the MSL file.
        return "[%s] %s %s" % (self.col, self.filename, self.cpux.ID)


# This object is an intermediate representation of the information for an instruction
# with a specific format.  Some instructions have more than one format dependuing
# upon the supporting CPU.  This object captures the information needed for the
# ultimate creation of the instruction report line object: ITLBE
class inst_format(object):
    def __init__(self,inst,columns):
        self.format=inst.format      # The instruction format
        self.inst=inst               # The msldb.Inst object of the instruction

        # Create a list of unused slots.
        slots=[]
        not_used="-   "
        for n in range(columns):
            slots.append(not_used)
        self.slots=slots

    def __setitem__(self,ndx,value):
        self.slots[ndx]=value


# This class encapsulates the extended mnemonics as defined by a version of
# the Reference Summary.  This provides something to compare the instructions
# against.  Hopefully this improves the accurracy of the extended mnemonics
# defined in the MSL file.  Obviously, errors can occur in the definitions
# supplied here or the MSL file.  Hopefully this will help find missing or
# extended mnemonics in error.
#
# Each new version will subclass this method or a subcalss and add its new 
# extended mnemonics to the master dictionary.
#
# This base method supports all systems preceding ESA/370 and earlier.
class EM(object):
    # Branch, branch register and branch indirect base mnemonics
    branch_ext=["B","BH","BL","BE","BNH","BNL","BNE","BP","BM","BZ","BO",\
                "BNP","BNM","BNZ","BNO","NOP"]
    
    def __init__(self):
        self.extmnem={}           # Master dictionary of extended mnemonics
        # These are generated for report purposes.  Not part of MSL files.
        
        for i in EM.branch_ext:
            self._addExt(i)           # Add branch mnemonics
            self._addExt("%sR" % i)   # Add branch register mnemonics

    # Method Argument:
    #   mnemonic  an extended instruction mnemonic added for the CPU
    def _addExt(self,mnemonic):
        if mnemonic == "CRBH":
            print("EM._addExt() - adding extended mnemonic: %s" % mnemonic)
        try:
            self.extmnem[mnemonic]
        except KeyError:
            #self.extmnem[mnemonic]=None
            self.extmnem[mnemonic]=mnemonic
            return
        raise ValueError("Mnemonic already defined: %s" % mnemonic)
        #print("Mnemonic already defined: %s" % mnemonic)

# Extended mnemonics for s390x-insn.msl CPU: s390
class EM_ESA390(EM):
    branch_rel_immed_ext=["BRU","BRH","BRL","BRE","BRNH","BRNL","BRNE",\
                          "BRP","BRM","BRZ","BRO","BRNP","BRNM","BRNZ",\
                          "BRNO"]
    jump_rel_immed_ext=["JNOP","JH","JL","JE","JNH","JNL","JNE","JP",\
                        "JM","JZ","JO","JNP","JNM","JNZ","JNO"]
    jump_rel_unique=["J",]
    def __init__(self):
        super().__init__()
        
        for i in EM_ESA390.branch_rel_immed_ext:
            self._addExt(i)      # Add BRC extended mnemonic
        for i in EM_ESA390.jump_rel_unique:
            self._addExt(i)      # Add unique "jump" extended mnemonic
        for i in EM_ESA390.jump_rel_immed_ext:
            self._addExt(i)      # Add BRC "jump" extended mnemonic
        
# Extended mnemonics for s390x-insn.msl CPU: s390x
class EM_ALL(EM_ESA390):
    new_long_jump_ext=["JLU","JAS","JASL","JCT","JCTG","JXH",\
                       "JXHG","JXLE","JXLEG"]
                       
    new_06_compares=["H",]
    
    def __init__(self):
        super().__init__()

    # Add branch indirect extended mnemonics
        for i in EM.branch_ext:
            self._addExt("BI%s" % i[1:])  # Add branch indirect mnemonic

    # Relative branch extended mnemonics
        for i in EM_ESA390.branch_rel_immed_ext:
            self._addExt("%sL" % i)       # Add BRCL extended mnemonic
        for i in EM_ESA390.jump_rel_immed_ext:
            #print("adding %s" % i)
            self._addExt("JL%s" % i[1:])  # Add BRCL "jump" extended mnemonic
        for i in EM_ALL.new_long_jump_ext:
            self._addExt(i)               # Add new jump extended mnemonics

    # Compare and branch and compare and trap extended mnemonics
        for i in EM_ALL.new_06_compares:
            self._addExt("CRB%s" % i)
        # To be added

    # Load/Store on Condition extended mnemonics
        # To be added

    # Rotate then insert and / or / exclusive or selected bits extended mnemonic
        # To be added
        
# This object encapsulates the results of an extended mnemonics comparison in
# the --report ext processing.
class EMFOUND(object):
    
    @staticmethod
    def sort_by_mnem(item):
        return item.mnem
    
    def __init__(self,mnem,format=None,report=False,msl=False):
        self.mnem=mnem        # Encountered extended mnemonic
        self.format=format    # Instruction format name
        self.report=report    # Whether found in the report database
        self.msl=msl          # Whether found in the MSL file CPU definition
        
    def __str__(self):
        return "EMFOUND(%s,format=%s,report=%s,msl=%s)" \
            % (self.mnem,self.format,self.report,self.msl)


# This object creates the instruction table report.  The object is GLOBAL,
# containing all CPU's in the report
#
# Instance Arguments:
#   columns   the number of CPU's in the report.
#   seq       The list of requested instruction reports from --seq command line.
#   extend    whether extended mnemonics included (True) or not (False).  Defaults to
#             False.
#   seq       The list of requested instruction reports from --seq command line.
#   msl       An MSL database from which all format types are extracted for format
#             statistics.
#   linesize  Maximum length of the report line.  Defaults to 132
class ITBL(Listing):

    # Used to sort ITLBE objects into format order:
    #   Sorted by format then by instruction opcode
    @staticmethod
    def sort_by_format(this,that):
        # This method requies the use of functools.cmp_to_key() function
        if this.format<that.format:
            return -1
        if this.format>that.format:
            return 1

        if this.mnem<that.mnem:
            return -1
        if this.mnem>that.mnem:
            return 1

        return 0

    # Used to sort ITLBE objects into mnemoic order:
    #   Sorted by mnemonic then by format
    @staticmethod
    def sort_by_name(this,that):
        # This method requies the use of functools.cmp_to_key() function
        if this.mnem<that.mnem:
            return -1
        if this.mnem>that.mnem:
            return 1

        if this.format<that.format:
            return -1
        if this.format>that.format:
            return 1

        return 0

    # Used to sort ITLBE objects into mnemoic order:
    #   Sorted by operation code then by format
    @staticmethod
    def sort_by_op(this,that):
        # This method requies the use of functools.cmp_to_key() function
        if this.op_sort < that.op_sort:
            return -1
        if this.op_sort > that.op_sort:
            return 1

        if this.format < that.format:
            return -1
        if this.format > that.format:
            return 1

        return 0

    def __init__(self, columns, seq, msl=None, extend=False, linesize=132):
        super().__init__(linesize=linesize)
        assert isinstance(msl,msldb.MSLDB),"'seq' argument must be a "\
            "msldb.MSLDB object: %s" % msl

        #print("ITBL.__init__() - msl: %s" % msl)
        self.columns=columns     # Number of CPU columns in the report
        self.extend=extend
        #print("ITBL.__init__() - self.extend: %s" % self.extend)
        self.seq=seq

        # Use Multiline detail generation
        self.buf=Multiline(self)

    # Built by method cpu() - MSL CPU instruction data extracted for presentation
    # in the listing.

        # The cpu object which is the source of information for each column.
        self.cpus=[None,]*columns    # Populated by method cpu()

        # This list is the total mumber instructions by CPU, each element
        # corresponding to a CPU's column
        self.counts=[0,]*columns     # Populated by method inst()

        # Dictionary by instruction mnemonic of all instructions in the report.
        # The value of the entry is a list of all of the msldb.Inst objects placed
        # in their respective columns for which the instruction mnemonic is defined,
        # each column associated with a cpu in the report.  The entry is None if the
        # instruction is not defined by the cpu associated with the column.
        self._inst={}                # Populated by method cpu()

        # Disctionary by instruction formats used by all instructions.  Similar to
        # the previous dictionary it is a list, each element corresponding to a
        # column of the report, each column being associated with a cpu of the
        # instruction report.  The values in the list are counts, by format of the
        # number of instructions defined for the CPU using the format.  For formats
        # not used by a cpu the value is 0.
        self._formats={}             # Populated by method cpu() with stats
        #self.build_format_stats(msl) # Builds the dictionary for stats

        # Calculated in validate() method
        self.mnem_size=0
        self.format_size=0
        self.opcode_size=0

        # Basis of 'inst' and 'PoO' reports
        self.entries=[]    # List of ITLBE objects.  See validate() method.

        # Listing formats. See prepare() method
        self.hedgrp=None
        self.detgrp=None
        self.statgrp=None
        self.lists=None

        # See detail() method
        self.seq_ndx=None   # Index of next list in self.lists
        self.ndx=0          # Index of next instruction in self.insts
        self.seq_ndx=0      # Index of next list in self.lists
        self.insts=None
        self.lists=None     # The title of the lists being generated

        self.buf.part(self.detail_line,header=self.heading,\
            last=True)

    def by_format(self):
        return sorted(self.entries,key=functools.cmp_to_key(ITBL.sort_by_format))

    def by_name(self):
        return sorted(self.entries,key=functools.cmp_to_key(ITBL.sort_by_name))

    def by_op(self):
        return sorted(self.entries,key=functools.cmp_to_key(ITBL.sort_by_op))

  #
  # These methods extract information from the MSL database files for structuring
  # the report.
  #

    #def build_format_stats(self,msl):
        #print("ITBL.build_format_stats() - Entered")
        #print("ITBL.build_format_stats() - msldb cpu: %s" % msl["cpu"])
    #    if not msl:
    #        return
    #    for entry in msl.iter_entries():
            #print("ITBL.build_format_stats() - entry: %s %r" % (entry.ID,entry))
           
            #if entry.ID in ["CBRH","ERRS"]:
            #    print("ITBL.build_format_stats() - entry: %s %r" % (entr)
    #        if not isinstance(entry,msldb.Format):
    #            continue
            # entry is a format
    #        try:
    #            self._formats[entry.ID]
    #            print("Duplicate insruction format found: %s" % entry.ID)
    #        except KeyError:
    #            self._formats[entry.ID]=[0,]*self.columns
                
        #print("ITBL.build_format_stats() - Returning")

    # Compare the instruction formats of two different msldb.Inst objects for
    # equality.
    # Returns:
    #   True   if the two formats are equal
    #   False  if the two formats are not equal
    def check_format(self,this,that):
        if this.format != that.format:
            return False
        return True

    # Compare the attributes of two different msldb.Inst objects for equality
    # Returns:
    #   True   if the two objects are equal
    #   False  if the two objects are not equal
    def check_inst(self, this, that):
        if this.ID in ["SSKE",]:   # Known exceptions
            return True
        if this.mnemonic != that.mnemonic:
            return False
        if this.format != that.format:
            return False
        if this.opc_len != that.opc_len:
            return False
        if this.opcode[0] != that.opcode[0]:
            return False
        if this.opcode[1] != that.opcode [1]:
            return False
        return True

    # Extracts instruction information from a cpu's MSL database definition.  If
    # extended mnemonics are not being included, they are ignored.
    # Method Argument:
    #   cpu    A cpu object wrapping the msldb.CPUX object with report information.
    def cpu(self, cpu):
        col=cpu.col
        self.cpus[col]=cpu
        cpux=cpu.cpux
        assert isinstance(cpux,msldb.CPUX),"cpux must be a msldb.CPUX object: "\
            "%s" % cpux
            
        for inst in cpux.inst.values():
            # inst is a msldb.Inst object
            
            #is_target = inst.ID in ["CRBH","ERRS"]
            #if is_target:
            #    print("ITBL.cpu() - inst: %s" % inst.ID)
            if inst.extended and not self.extend:
                #if is_target:
                #    print("ITBL.cpu() - ignoring: %s" % inst.ID)
                continue
            #if is_target:
            #    print("ITBL.cpu() - adding inst: %s" % inst.ID)
            #    print("ITBL.CPU() - adding format: %r" % inst.format)
            self.inst(inst, col)
            self.format(inst, col)

    # Convert flags into their text format for printing
    def flags(self, inst):
        # inst is an msldb.Inst object
        string=""
        if inst.priv:
            string="P"
        else:
            string="G"
        if inst.extended:
            string="%sE" % string
        else:
            string="%s " % string
        if inst.experimental:
            string="%sX" % string
        else:
            string="%s " % string
        if inst.nolenck:
            string="%sL" % string
        else:
            string="%s " % string
        return string

    # Accumulates the number of instructions using a specific MSL database instruction
    # format by column, the column associated with a cpu of the report.
    # Method Arguments:
    #   inst   A msldb.Inst object defining an instruction for a CPU.
    #   col    The column index into which this instruction format's counts are
    #          placed for the CPU associated with the column.
    def format(self, inst, col):
        try:
            fmtlist=self._formats[inst.format]
        except KeyError:
            fmtlist=[0,]*self.columns
            #raise ValueError("%s unrecognized instruction %s format encountered: %s" \
            #    % (self.cpus[col].cpux.ID,inst.ID,inst.format))

        n=fmtlist[col]
        n+=1
        fmtlist[col]=n
        self._formats[inst.format]=fmtlist

    # Build by instruction mnemonic, the msldb.Inst object associated with the
    # CPU's column
    # Method Arbuments:
    #   inst   A msldb.Inst object defining an instruction for a CPU.
    #   col    The column index into which this instruction's flags are placed for
    #          the CPU associated with the column.
    def inst(self, inst, col):
        try:
            instlist=self._inst[inst.ID]
        except KeyError:
            instlist=[None,]*self.columns
        instlist[col]=inst
        self._inst[inst.ID]=instlist
        self.counts[col]=self.counts[col]+1

    # Print the mismatch of an instruction compare
    def mismatch(self,i1,n1,i2,n2):
        c1=self.cpus[n1].cpux.ID
        c2=self.cpus[n2].cpux.ID

        print("Instruction mismatch")
        v1=i1.mnemonic
        v2=i2.mnemonic
        if v1 == v2:
            s="=="
        else:
            s="!="
        print("mnemonic: [%s] %s %s [%s] %s" % (c1, v1, s, c2, v2))

        v1=i1.opcode
        v2=i2.opcode
        if v1 == v2:
            s="=="
        else:
            s="!="
        print("opcode:   [%s] %s %s [%s] %s" % (c1, v1, s, c2, v2))

        v1=i1.opc_len
        v2=i2.opc_len
        if v1 == v2:
            s="=="
        else:
            s="!="
        print("opc_len:  [%s] %s %s [%s] %s" % (c1, v1 ,s, c2, v2))

        v1=i1.format
        v2=i2.format
        if v1 == v2:
            s="=="
        else:
            s="!="
        print("format:   [%s] %s %s [%s] %s" % (c1, v1 ,s, c2, v2))

    # Create a new entry in the instruction list and update column lengths
    def new_entry(self,inst,elist):
        entry=ITBLE(inst,elist)
        self.mnem_size=max(self.mnem_size,len(entry.mnem))
        self.format_size=max(self.format_size,len(entry.format))
        self.opcode_size=max(self.opcode_size,entry.opc_len)
        self.entries.append(entry)

    # From a list of msldb.Inst objects for a single instruction mnemonic
    # create one or more ITLBE objects for the report.  Multiple ITLBE objects
    # result if there are differences in the instruction definition of the mnemonic
    def validate(self):
        not_used="-   "
        entries=[]
        for mnem,instlist in self._inst.items():
            inst=None
            col=None
            elist=[]

            formats=self.validate_formats(instlist)

            for n,x in enumerate(instlist):
                if x is None:
                    continue
                fmt=formats[x.format]
                fmt[n]=self.flags(x)

            for format,ifmt in formats.items():
                self.new_entry(ifmt.inst,ifmt.slots)

        return

    # Compare all of the formats of a list of supported instructions for
    # Returns:
    #   a dictionary of identified formats with not used flags set for each format
    def validate_formats(self,instlist):
        # This is a list of all instructions known to use different formats
        known = ["ALC","CLCLU","DL","IPTE","MVCLU","ML","RLL","SLB"]
        #known = []

        inst=None    # Current msldb.Inst object against which others are compared
        col=None     # The column of the current msldb.Inst object

        formats={}
        for n,x in enumerate(instlist):
            # n is the index of the current column
            # x is the msldb.Inst object (when supported) or None (when not supported)

            if x is None:
                # This CPU does not support the instruction
                continue

            if inst is None:
                # This is the first cpu that supports the instruction
                inst=x
                col=n

            if not self.check_inst(inst,x):
                if inst.mnemonic not in known:
                    self.mismatch(inst,col,x,n)   # Report the failure
                inst=x
                col=n

            # This CPU does support the instruction
            slots=len(instlist)
            try:
                formats[x.format]
            except KeyError:
                fmt=inst_format(x,slots)
                formats[fmt.format]=fmt

        return formats

  #
  # Listing generator callback methods
  #

    # Return a detail line to the list manager (or None ends the report)
    def detail(self):
        return self.buf.detail(trace=False)

    # Multiline 'more()' method
    # Method Arbument:
    #   mlbuf   The Multiline object providing the buffer to the Listing Manager
    def detail_line(self,mlbuf):
        if self.seq>=len(self.insts):
            if self.seq_init():
                # Done with instruction part of listing (seq_init() returned True)
                # Change the 'more()' method to generate stats and try again
                mlbuf.details(self.stats,cont=True)
                return
            self.eject()
        inst=self.insts[self.seq]
        self.seq+=1
        values=[self.mnemonic(inst),self.format_det(inst), self.opcode(inst)]
        values.extend(inst.columns)
        detail=self.detgrp.string(values=values)
        mlbuf.more(detail)

    # Format the detail line from an ITLBE object
    def format_det(self, entry):
        if isinstance(entry,ITBLE):
            fmt=entry.format
        else:
            fmt=entry

        pad=" " * self.format_size
        string="%s%s" % (fmt,pad)
        return string[:self.format_size]

    # Return the report heading when requested by the listing generator
    def heading(self):
        return self.hedgrp

    # Format for the report the instruction mnemonic from the ITBLE object
    def mnemonic(self,entry):
        # entry is an ITLBE object
        pad=" " * self.mnem_size
        string="%s%s" % (entry.mnem,pad)
        return string[:self.mnem_size]

    # Format for the report the instruction from the ITBLE object
    def opcode(self,entry):
        # entry is an ITBLE object
        string="%s    " % entry.op_hex
        return string[:4]

    # Prepare the formating of the report using listing Group objects
    def prepare(self):
        hed=[]
        det=[]
        stat=[]
        # MNEMONIC Column
        mcol="MNEMONIC"
        msize=max(self.mnem_size,len(mcol))
        det.append(CharCol(msize,just="center",sep=2,colnum=0))
        hed.append(CharCol(msize,just="center",sep=2,colnum=0,default=mcol))
        stat.append(CharCol(msize,just="center",sep=2,colnum=0))

        # FORMAT Column
        fcol="FORMAT"
        fsize=max(self.format_size,len(fcol))
        det.append(CharCol(fsize,just="center",sep=2,colnum=1))
        hed.append(CharCol(fsize,just="center",sep=2,colnum=1,default=fcol))
        stat.append(CharCol(fsize,just="center",sep=2,colnum=1))

        # OPCODE Column
        ocol="OPCODE"
        osize=max(self.opcode_size,len(ocol))
        det.append(CharCol(fsize,just="center",sep=2,colnum=2))
        hed.append(CharCol(fsize,just="center",sep=2,colnum=2,default=ocol))
        stat.append(CharCol(fsize,just="center",sep=2,colnum=2))

        hedvals=[None,]*3
        for n,cpu in enumerate(self.cpus):
            col=n+3
            name=cpu.cpux.ID
            colsize=max(4,len(name))
            decsize=10**colsize-1
            det.append(CharCol(colsize,just="center",sep=2,colnum=col))
            hed.append(CharCol(colsize,just="center",sep=2,colnum=col,default=name))
            stat.append(DecCol(maximum=decsize,trunc=True,sep=2,colnum=col))
            hedvals.append(None)

        hedgrp=Group(columns=hed)
        self.hedgrp=hedgrp.string(values=hedvals)
        self.detgrp=Group(columns=det)
        self.statgrp=Group(columns=stat)

        seq=[]
        for x in self.seq:
            if x=="mnemonic":
                seq.append( ("Instruction List by Mnemonics",self.by_name() ) )
            elif x=="opcode":
                seq.append( ("Instruction List by Opcode",self.by_op() ) )
            elif x=="format":
                seq.append( ("Instruction List by Format",self.by_format() ) )
            else:
                pass
        self.lists=seq

        self.seq_ndx=0
        if self.seq_init():
            return

    # Initialize the instruction report sequence controls
    # Returns:
    #   False if not at the end of the requested instruction sequence lists
    #   True if at the end of the sequence.
    def seq_init(self):
        if self.seq_ndx>=len(self.lists):
            return True   # AT EOF
        self.cur_title,self.insts = self.lists[self.seq_ndx]
        self.cur_title="MSL DATABASE REPORT - %s" % self.cur_title
        self.seq_ndx+=1
        self.seq=0
        return False

    # Create format related statistics
    def stats(self,mlbuf):
        self.cur_title="MSL DATABASE REPORT - Statistics"
        self.eject()
        lines=[]
        is_poo= self.columns>1
        unused=[]
        for format,stats in sorted(self._formats.items()):
            if is_poo:
                usage = 0
                for x in stats:
                    usage+=x
                if usage == 0:
                    unused.append(format)
            values=[None,self.format_det(format),None]
            values.extend(stats)
            line=self.statgrp.string(values=values)
            lines.append(line)
        lines.append("")
        values=[None,"Tot.",None]
        values.extend(self.counts)
        line=self.statgrp.string(values=values)
        lines.append(line)
        mlbuf.more(lines,done=True)
        if not is_poo or len(unused)==0:
            return

        # Report unused formats
        s="Unused instruction formats:"
        for f in unused:
            s="%s %s," % (s,f)
        print(s[:-1])

    # Return the current title when requested by the listing generator
    def title(self):
        return self.cur_title


# Instruction table detail line information
# Instance Arguments:
#   inst     The msldb.Inst instance defining this an instruction
class ITBLE(object):
    def __init__(self,inst,instlist):
        self.mnem=inst.ID           # The instruction mnemonic
        self.format=inst.format     # MSL format name of the instruction

        opc=self.opcode=inst.opcode # The operation code as a list of two elements
        length=self.opc_len=inst.opc_len   # The operation code length in hex digits

        # Calculate the value used to sort by operation code and its hex digits
        if length==2:
            self.op_hex="%02X" % opc[0]
            self.op_sort=opc[0]*256
        elif length==3:
            self.op_hex="%02X%X" % (opc[0],opc[1])
            self.op_sort=opc[0]*256+opc[1]*16
        else:
            self.op_hex="%02X%02X" % (opc[0],opc[1])
            self.op_sort=opc[0]*256+opc[1]

        # Formated flags as a list of strings, one for each column in the
        # instruction report.
        self.columns=instlist

    def __str__(self):
        mnem="%s     " % self.mnem
        mnem=mnem[:5]
        format="%s     " % self.format
        format=format[:5]
        op="%s    " % self.op_hex
        op=op[:4]
        cols=""
        for c in self.columns:
            if c is None:
                cols="%s -" % cols
            else:
                cols="%s %s" % (cols,c)
        return "%s %s %s  %s" % (mnem,format,op,cols)


#
#  +----------------------------+
#  |                            |
#  |   Command Line Execution   |
#  |                            |
#  +----------------------------+
#

# Perform requested reports from the command line.
# Instance Arbument:
#   args    The namespace object from the command-line parser
class MSLRPT(object):
    PATHVAR="MSLPATH"
    DEFAULT=satkutil.satkdir("asma/msl",debug=False)
    
    def __init__(self,args):

        # Process the --report argument
        self.report=args.report        # Report requested.  See run() method

        # Process the --cpu argument(s)
        self.cpus=[]
        for c in args.cpu:
            seps=c.count("=")
            if seps!=1:
                print("invalid --cpu argument ignored: %s" % c)
                continue
            file_cpu=c.split("=")
            t=(file_cpu[0],file_cpu[1])
            self.cpus.append(t)

        # Remeber the --listing argument (may be None)
        self.listing=args.listing

        # Remember --extended argument
        self.extend=args.extended

        # Process --seq argument(s)
        if args.seq is None:
            self.seq=["mnemonic",]
        else:
            self.seq=args.seq

        # Remeber line length
        self.line=args.line

        # A MSL DB is captured so the INTBL object can create format statistics
        # for all defined formats, not just the ones in the selected cpu(s).
        self.msldb=None   # A MSL DB is captured so the INTBL object can create
        
        # --report ext attributes
        self.emfound={}       # See method __add_emfound()


    # Add an EMFOUND object for --report ext processing
    #
    # Method Arguments:
    #   emf  The EMFOUND object being added to the extended mnemonic dictionary
    #   dup  Whether duplicate EMFOUND objects are ignored, True, or generate
    #        an error, False
    # Returns:
    #   True if the EMFOUND object has been successfully added or ignored when
    #        dup=True.
    #   False if the EMFOUND object has not been successfully added because
    #   an EMFOUND object already exists for the instruction
    def __add_emfound(self,emf,dup=False):
        try:
            emo=self.emfound[emf.mnem]
            # Found!
            if dup:
                return True
            return False
        except KeyError:
            # Not found! (so not a duplicate either)
            self.emfound[emf.mnem]=emf

        return True

    # Return a a path object for the MSL data
    def __find_files(self):
        msl=msldb.MSL(default=MSLRPT.DEFAULT)
        path=msl.opath # Reach in and get the path manager
        return path.files(MSLRPT.PATHVAR,ext=".msl")

    # Method Arguments:
    #    filename  The MSL file's name being read by this method
    # Returns:
    #    The MSL database if successful.  An msldb.MSL object
    #    None if unsuccessful.  Messages from the msldb module will identify
    #         any problems encountered
    #      
    # WARNING: This method must be called from this object!
    def __read_MSL_FILE_DB(self,filename):
        msl=msldb.MSL(default=MSLRPT.DEFAULT)
        errors=msl.build(filename,fail=True)
        if errors:
            print("MSL errors encountered in file: %s" % filename)
            return None
           
        # No errors, so return the MSL file as an object
        return msl

    # Process command line --report cpu
    def cpu_report(self):
        files=self.__find_files()
        mslf={}
        for filename in sorted(files):
            msl=msldb.MSL(default=MSLRPT.DEFAULT)
            errors=msl.build(filename)
            if errors:
                print("MSL errors encountered in file: %s" % f)
                continue
            db=msl.DB()
            cpus=[]
            for entry in db.iter_entries():
                if isinstance(entry,msldb.CPU):
                    cpus.append(entry.ID)
            if len(cpus)>0:
                mslf[filename]=cpus
        print("Available CPUs:")
        for f,cpus in mslf.items():
            strcpus=""
            for c in sorted(cpus):
                strcpus="%s, %s" % (strcpus,c)
            strcpus=strcpus[2:]
            print("    %s: %s" % (f,strcpus))

    # Process command line --report ext
    def ext_report(self):
        if self.cpus:
            if len(self.cpus)>1:
                print("only first --cpu argument used by --report ext")
        else:
            print("--cpu argument required by --report ext")
            return
        
        # Instantiate the correct EM class for the requested file/cpu
        filename,cpu=self.cpus[0]
        if filename == "all-insn.msl":
            cls=EM_ALL
        elif filename == "s390x-insn.msl":
            if cpu == "s390":
                cls=EM_ESA390
            elif cpu == "s390x":
                cls=EM_ALL
        else:
            # All other files use the default EM extended mnemonics class
            cls=EM
        ems=cls()
        
        print("\nExtended Mnemonic Report for file %s, CPU: %s" \
            % (filename,cpu))
        print("Extended mnemonics defined by class: %s\n" \
            % ems.__class__.__name__)
        
        # Convert the identified MSL file into a msl.MSLDB object.  Object may
        # contain multiple CPU's.
        filemsl=self.__read_MSL_FILE_DB(filename)
        # filemsl is an msldb.MSL object or None
        if not filemsl:
            print("report --ext terminated")
            return
 
        # Extract the defined CPU and expand it into a msldb.CPUX object for
        # instruction processing.
        cpux=filemsl.expand(cpu)
        # cpux is an msldb.CPUX object
        
        # The extended mnemonics in an EM object can now be compared to those in
        # the MSL file for the requested CPU.  Each comparison results in
        # an EMFOUND object.
        #
        # At the end, all instructions are examined for flag extended being
        # specified and added to the list if not already present.  These are
        # extended mnemonics that are defined in the MSL file for the CPU, but
        # are NOT in the EM object definition.  These need researching and
        # either the EM object is updated or the MSL file removes the
        # intstruction.
        #
        # Where only an EM object defines the extended mnemonic, the MSL file
        # must be fixed to include the mnemonic.  In this comparison, the
        cpui=cpux.inst        # Dictionary of CPU's instructions from MSL
        
        # Pass 1
        ikeys=ems.extmnem.keys()  # Defined extended mnemonics from EM object
        for i in ikeys:
            try:
                msli=cpui[i]        # Fetch the instruction (msldb.Inst object)
                mslfmt=msli.format  # Instruction's format
                emf=EMFOUND(i,format=mslfmt,report=True,msl=True)
            except KeyError:
                # Extended mnemonic defined in EM object, but not in MSL file
                # for the CPU
                emf=EMFOUND(i,format=None,report=True,msl=False)

            result=self.__add_emfound(emf,dup=False)
            if not result:
                print("Duplicate extended mnemonic in EM object: %s" % i)
            
        # Pass 2
        mkeys=cpui.keys()         # MSL CPU instruction mnemonics
        for m in mkeys:
            msli=cpui[m]          # Fetch the instruction (msldb.Inst object)
            if not msli.extended: # Ignore regular instructions
                continue
            # This is an extended mnemonic from the MSL CPU
            emf=EMFOUND(m,format=msli.format,report=False,msl=True)
            
            # Only add if not found in Pass 1
            result=self.__add_emfound(emf,dup=True)
            if not result:
                print("Duplicate extended mnemonic in MSL file for CPU: %s" % m)
                
        # Comparison results
        #ekeys=self.emfound.keys()
        
        # Separate each group of mnemonic sources into separate lists
        both=[]
        em_only=[]
        msl_only=[]
        no_source=[]
        max_length=0
        
        for i in self.emfound.keys():
            emf=self.emfound[i]
            # Calculate the maximum nmemonic length
            max_length=max(len(emf.mnem),max_length)
            if emf.report and emf.msl:
                both.append(emf)
            elif emf.report and not emf.msl:
                em_only.append(emf)
            elif not emf.report and emf.msl:
                msl_only.append(emf)
            else:
                no_source.append(emf)
                
        # Print each group separately in mnemonic colating sequence
        # Note: the sorting of the list that occurs below is in place.
        
        print("Extended Mnemonics defined in both EM object and MSL file: %s" \
            % len(both))
        both.sort(key=EMFOUND.sort_by_mnem)
        for emf in both:
            inst=emf.mnem.ljust(max_length)
            print("    %s fmt: %s" % (inst,emf.format))
                
        print("\nExtended Mnemonics defined only by EM object: %s" \
            % len(em_only))
        if len(em_only) != 0:
            print("These extended mnemonics are missing from the MSL file %s"
                " CPU %s" % (filename,cpu))
        em_only.sort(key=EMFOUND.sort_by_mnem)
        for emf in em_only:
            print("    %s" % emf.mnem)
                
        print("\nExtended Mnemonics only defined in MSL for CPU: %s" \
            % len(msl_only))
        if len(msl_only) != 0:
            print("These extended mnemonics are missing from EM object %s" \
                % ems.__class__.__name__)
        msl_only.sort(key=EMFOUND.sort_by_mnem)
        for emf in msl_only:
            inst=emf.mnem.ljust(max_length)
            print("    %s fmt: %s" % (inst,emf.format))
            
        if len(no_source) == 0:
            return
            
        print("\nExtended Mnemonics with no source: %s" \
            % len(no_source))
        print("THIS SITUATION SHOULD NOT OCCUR!")
        no_source.sort(key=EMFOUND.sort_by_mnem)
        for emf in no_source:
            print("    %s" % emf.mnem)
                
    # Process command line --report files
    def files_report(self):
        files=self.__find_files()
        print("MSL Files in MSLPATH:")
        for f in files:
            print("    %s" % f)

    # Process command line --report PoO and --report inst
    def inst_report(self):
        # A MSL DB is captured so the INTBL object can create format statistics
        # for all defined formats, not just the ones in the selected cpu(s).
        mslfmt=None

        if len(self.cpus)==0:
            print("inst report requires one or more --cpu arguments")
            return
        files={}
        # Create a dictionary by filename of a list the the requested cpu(s)
        for filename,cpu in self.cpus:
            fn=files.setdefault(filename,[])
            if cpu not in fn:
                fn.append(cpu)
            files[filename]=fn

        # Attach the database to its filename in the dictionary
        dbs={}
        for filename in files.keys():
            msl=msldb.MSL(default=MSLRPT.DEFAULT)
            errors=msl.build(filename,fail=True)
            if errors:
                print("MSL errors encountered in file: %s" % filename)
                continue
            # No errors so extract the database for the file and create dictionary
            db=msl.DB()
            if not mslfmt:
                mslfmt=db
            dbs[filename]=db

        # Create a list of the expanded CPU definitions requested
        cpux=[]   # This is a list of tupples: (filename,msldb.CPUX)
        col=0
        for filename,cpu in self.cpus:
            db=dbs[filename]
            try:
                cpu=db[cpu]
            except KeyError:
                print("MSL file %s does not define cpu: %s" % (filename,cpu))
            cpu_ex=cpu.expand(db)
            cpux.append( CPU(col,filename,cpu_ex) )
            col+=1

        # Build the Instruction Table
        itbl=ITBL(len(cpux),self.seq,msl=mslfmt,\
            extend=self.extend,linesize=self.line)
        for c in cpux:
            #print("MSLRPT.inst.report() - c: %r" % c)
            itbl.cpu(c)
        itbl.validate()    # Valid the instructions

        # Print the instruction report
        itbl.prepare()     # Prepare to do the report
        if self.listing is None:
            print(itbl.generate())
        else:
            itbl.generate(filename=self.listing)

    def run(self):
        if self.report=="ext":
            self.ext_report()
        elif self.report=="files":
            self.files_report()
        elif self.report=="inst":
            self.inst_report()
        elif self.report=="cpu":
            self.cpu_report()
        elif self.report=="PoO":
            self.cpus=[]
            self.cpus.append( ("s360-insn.msl","s360") )
            self.cpus.append( ("s370-insn.msl","s370") )
            self.cpus.append( ("s380-insn.msl","s380") )
            self.cpus.append( ("s370XA-insn.msl","s370XA") )
            self.cpus.append( ("e370-insn.msl","e370") )
            self.cpus.append( ("e390-insn.msl","e390") )
            self.cpus.append( ("s390x-insn.msl","s390") )
            self.cpus.append( ("s390x-insn.msl","s390x") )
            self.cpus.append( ("all-insn.msl","24") )
            self.cpus.append( ("all-insn.msl","31") )
            self.cpus.append( ("all-insn.msl","64") )
            self.inst_report()
        else:
            raise ValueError("unexpected --report argument: %s" % self.report)


#
#  +-----------------------------+
#  |                             |
#  |   Command Line Processing   |
#  |                             |
#  +-----------------------------+
#

# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,
        epilog=copyright,
        description="reporting tool for MSL database files in MSLPATH")

    # Specify the report being created:
    # 'cpu'   reports on all cpus defined in the MSL files in the MSLPATH.
    # 'ext'   reports on extended mnemonics
    # 'files' reports on the MSL files found in the MSLPATH
    # 'inst'  reports on instructions for CPUs identified by the --cpu argument
    # 'PoO'   Principles of Operation 'inst' report
    parser.add_argument("-r","--report",\
        choices=["cpu","ext","files","inst","PoO"],required=True,\
        help="report action.")

    # Identify MSL files and cpus on which to base the 'inst' report
    parser.add_argument("-c","--cpu",action="append",default=[],\
        metavar="MSLFILE=CPU",
        help="identifies the MSL file in the MSLPATH and cpu included in the report. "
             "Multiple may be specified")

    # Flag to include extended mnemonics in 'inst' or 'PoO' reports
    parser.add_argument("-e","--extended",action="store_true",default=False,
        help="include extended mnemonics in 'inst' or 'PoO' reports")


    # File to which 'inst' or 'PoO' listing will be written.
    parser.add_argument("-l","--listing",
        metavar="FILEPATH",
        help="file path to which listing is written.")

    # 'inst' or 'PoO' report content:
    #   'mnemonic' by instruction mnemonic
    #   'opcode' by instruction operation code
    #   'format' by instruction format
    # More than one content type may be specified.
    parser.add_argument("-s","--seq",default=None,\
        choices=["mnemonic","opcode","format"],action="append",\
        help="'inst' report sequence.  Multiple allowed.  Defaults to 'mnemonic'")

    # Adjust the output listing line length if necessary
    parser.add_argument("--line",default=132,\
        help="specify the output listing line length.  Defaults to 132")

    return parser.parse_args()

if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    MSLRPT(args).run()
