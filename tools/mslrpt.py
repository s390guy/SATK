#!/usr/bin/python3
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

# This module provides a reporting tool of information contained in Machine
# Specification Language (MSL) database files. For a description of the MSL, see
# module msldb.py.

this_module="mslrpt.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2014")

# Python imports:
import sys               # Access the exit method
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse          # Access the command line parser
import functools         # Access complex sorting sequences

# Setup PYTHONPATH
import satkutil          # Access utility functions
satkutil.pythonpath("asma")        # Provides path to msldb
satkutil.pythonpath("tools/lang")  # Provides path to sopl

# ASMA imports
import msldb             # Access the database

# SATK imports
from listing import *    # Access the formatted report tools


# This wraps a msldb.CPUX object with report information
class CPU(object):
    def __init__(self,col,filename,cpux):
        self.col=col
        self.filename=filename
        self.cpux=cpux
        self.count=0
    def __str__(self):
        return "[%s] %s %s" % (self.col, self.filename, self.cpux.ID)   

class ITBL(Listing):
    @staticmethod
    def sort_by_format(this,that):
        # This method requies the use of functools.cmp_to_key() function
        if this.format<that.format:
            return -1
        elif this.format>that.format:
            return 1
        else:
            if ITBL.sort_by_op(this)<ITBL.sort_by_op(that):
                return -1
            elif ITBL.sort_by_op(this)>ITBL.sort_by_op(that):
                return 1
            else:
                return 0

    @staticmethod
    def sort_by_name(item):
        return item.mnem

    @staticmethod
    def sort_by_op(item):
        if item.opc_len==2:
            return item.opcode[0]*256
        elif item.opc_len==3:
            return item.opcode[0]*256+item.opcode[1]*16
        else:
            return item.opcode[0]*256+item.opcode[1]

    def __init__(self, columns, seq, extend=False, linesize=132):
        super().__init__(linesize=linesize)
        self.columns=columns
        self.extend=extend
        self.seq=seq

        # Use Multiline detail generation
        self.buf=Multiline(self)

        # Built by method cpu()
        self.counts=[0,]*columns
        self.cpus=[None,]*columns
        self._inst={}
        self._formats={}

        # Calculated in validate() method
        self.mnem_size=0
        self.format_size=0
        self.opcode_size=0

        # Basis of 'inst' and 'PoO' reports
        self.entries=None   # List of ITLBE objects.  See validate() method.

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
        self.lists=None
        
        self.buf.part(self.detail_line,header=self.heading,\
            last=True)

    def by_format(self):
        return sorted(self.entries,key=functools.cmp_to_key(ITBL.sort_by_format))

    def by_name(self):
        return sorted(self.entries,key=ITBL.sort_by_name)

    def by_op(self):
        return sorted(self.entries,key=ITBL.sort_by_op)

    def check_inst(self, this, that):
        if this.ID in ["IPTE",]:   # Known exceptions
            return True
        if this.ID != that.ID:
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

    def cpu(self, cpu):
        col=cpu.col
        self.cpus[col]=cpu
        cpux=cpu.cpux
        for inst in cpux.inst.values():
            if inst.extended and not self.extend:
                continue
            self.inst(inst, col)
            self.format(inst, col)

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

    def format(self, inst, col):
        try:
            fmtlist=self._formats[inst.format]
        except KeyError:
            fmtlist=[0,]*self.columns
        n=fmtlist[col]
        n+=1
        fmtlist[col]=n
        self._formats[inst.format]=fmtlist

    def format_det(self, entry):
        if isinstance(entry,ITBLE):
            fmt=entry.format
        else:
            fmt=entry

        pad=" " * self.format_size
        string="%s%s" % (fmt,pad)
        return string[:self.format_size]

    def heading(self):
        return self.hedgrp

    def inst(self, inst, col):
        try:
            instlist=self._inst[inst.ID]
        except KeyError:
            instlist=[None,]*self.columns
        instlist[col]=inst
        self._inst[inst.ID]=instlist
        self.counts[col]=self.counts[col]+1

    def mismatch(self,i1,n1,i2,n2):
        print("Instruction mismatch")
        print("mnemonic: [%s] %s <> [%s] %s" % (n1,i1.ID,n2,i2.ID))
        print("opcode:   [%s] %s <> [%s] %s" % (n1,i1.opcode,n2,i2.opcode))
        print("opc_len:  [%s] %s <> [%s] %s" % (n1,i1.opc_len,n2,i2.opc_len))
        print("format:   [%s] %s <> [%s] %s" % (n1,i1.format,n2,i2.format))

    def mnemonic(self,entry):
        # entry is an ITLBE object
        pad=" " * self.mnem_size
        string="%s%s" % (entry.mnem,pad)
        return string[:self.mnem_size]

    def opcode(self,entry):
        # entry is an ITBLE object
        string="%s    " % entry.op()
        return string[:4]

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

    def seq_init(self):
        if self.seq_ndx>=len(self.lists):
            return True   # AT EOF
        self.cur_title,self.insts = self.lists[self.seq_ndx]
        self.cur_title="MSL DATABASE REPORT - %s" % self.cur_title
        self.seq_ndx+=1
        self.seq=0
        return False

    def stats(self,mlbuf):
        self.cur_title="MSL DATABASE REPORT - Statistics"
        self.eject()
        lines=[]
        for format,stats in sorted(self._formats.items()):
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

    def title(self):
        return self.cur_title

    def validate(self):
        entries=[]
        for mnem,instlist in self._inst.items():
            inst=None
            col=None
            elist=[]
            for n,x in enumerate(instlist):
                if x is None:
                    # This CPU does not support the instruction
                    elist.append("-   ")
                    continue
                if inst is None:
                    # This CPU is the first in the list to support the instruction
                    col=n
                    inst=x
                    elist.append(self.flags(inst))
                    continue
                # Additional CPUs support the instruction
                # This checks the basic definition for consistency between the CPU's
                if not self.check_inst(inst,x):
                    self.mismatch(inst,col,x,n)
                    elist.append("?")
                else:
                    elist.append(self.flags(inst))
            entry=ITBLE(inst,elist)
            self.mnem_size=max(self.mnem_size,len(entry.mnem))
            self.format_size=max(self.format_size,len(entry.format))
            self.opcode_size=max(self.opcode_size,entry.opc_len)
            entries.append(entry)
        self.entries=entries


class ITBLE(object):
    def __init__(self,inst,instlist):
        self.mnem=inst.ID
        self.opcode=inst.opcode
        self.opc_len=inst.opc_len
        self.format=inst.format
        self.columns=instlist

    def __str__(self):
        mnem="%s     " % self.mnem
        mnem=mnem[:5]
        format="%s     " % self.format
        format=format[:5]
        op="%s    " % self.op()
        op=op[:4]
        cols=""
        for c in self.columns:
            if c is None:
                cols="%s -" % cols
            else:
                cols="%s %s" % (cols,c)
        return "%s %s %s  %s" % (mnem,format,op,cols)

    def op(self):
        length=self.opc_len
        if length==2:
            return "%02X" % self.opcode[0]
        elif length==3:
            return "%02X%X" % (self.opcode[0],self.opcode[1])
        else:
            return "%02X%02X" % (self.opcode[0],self.opcode[1])


#
#  +----------------------------+
#  |                            |
#  |   Command Line Execution   |
#  |                            |
#  +----------------------------+
#

class MSLRPT(object):
    PATHVAR="MSLPATH"
    DEFAULT=satkutil.satkdir("asma/msl",debug=False)
    def __init__(self,args):
        self.report=args.report        # Report requested.  See run() method
        self.cpus=[]

        # Process the --cpu argument(s)
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

    def __find_files(self):
        msl=msldb.MSL(default=MSLRPT.DEFAULT)
        path=msl.opath # Reach in and get the path manager
        return path.files(MSLRPT.PATHVAR,ext=".msl")

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

    def files_report(self):
        files=self.__find_files()
        print("MSL Files in MSLPATH:")
        for f in files:
            print("    %s" % f)

    def inst_report(self):
        if len(self.cpus)==0:
            print("inst report requires one or more --cpu arguments")
            return
        files={}
        # Create a dictionary by file of a list the its requested cpu(s)
        for filename,cpu in self.cpus:
            fn=files.setdefault(filename,[])
            if cpu not in fn:
                fn.append(cpu)
            files[filename]=fn
        dbs={}
        for filename in files.keys():
            msl=msldb.MSL(default=MSLRPT.DEFAULT)
            errors=msl.build(filename)
            if errors:
                print("MSL errors encountered in file: %s" % filename)
                continue
            # No errors to extract the database for the file and create dictionary
            dbs[filename]=msl.DB()

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
        itbl=ITBL(len(cpux),self.seq,\
            extend=self.extend,linesize=self.line)
        for c in cpux:
            itbl.cpu(c)
        itbl.validate()    # Valid the instructions

        # Print the instruction report
        itbl.prepare()     # Prepare to do the report
        if self.listing is None:
            print(itbl.generate())
        else:
            itbl.generate(filename=self.listing)

    def run(self):
        if self.report=="files":
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
    # 'cpu' reports on all cpus defined in the MSL files in the MSLPATH.
    # 'files' reports on the MSL files found in the MSLPATH
    # 'inst'  reports on instructions for CPUs identified by the --cpu argument
    # 'PoO'   Principles of Operation 'inst' report
    parser.add_argument("-r","--report",choices=["cpu","files","inst","PoO"],\
        required=True,\
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
