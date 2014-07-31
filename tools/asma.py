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

# This module provides a command line interface to the ASMA assembler.py module.

this_module="asma.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2014")

# Python imports
import time
# Remember start times for updating
import_start=process_start=time.process_time()
import_start_w=wall_start=time.time()

import argparse
import sys

# ASMA imports
import assembler

class ASMA(object):
    def __init__(self,args,dm):
        self.dm=dm                # Global Debug Manager instance
        self.args=args            # Command line arguments
        self.clstats=args.stats   # Command-line statistics flag

        # Enable any command line debug flags
        for flag in self.args.debug:
            self.dm.enable(flag)

        self.aout=assembler.AsmOut(\
            deck=args.object,\
            image=args.image,\
            ldipl=args.gldipl,\
            listing=args.listing,\
            mc=args.store,\
            rc=args.rc,\
            vmc=args.vmc)

        self.assembler=assembler.Assembler(args.cpu,args.msldb,self.aout,\
            addr=args.addr,\
            debug=dm,\
            dump=args.dump,\
            error=args.error,\
            nest=self.args.nest,\
            ptrace=args.pas,\
            otrace=args.oper,\
            cpfile=args.cpfile,\
            cptrans=args.cptrans)

        self.source=args.source[0]     # Source input file
        
        # Gather together time related data saved outside this object.
        self.process_start=process_start
        self.wall_start=wall_start
        self.import_start=import_start
        self.import_start_w=import_start_w
        self.objects_start=objects_start
        self.objects_start_w=objects_start_w
        
        # Timer information gathered during run() method
        self.assemble_end=None
        self.assemble_end_w=None
        self.out_end=None
        self.out_end_w=None
        
        # Save some of my own time information
        self.objects_end=time.process_time()
        self.objects_end_w=time.time()

    def run(self):
       
        # Perform Pass 0
        if self.clstats:
            stats=assembler.Stats
            stats.start("assemble_p")
            stats.start("assemble_w")
            stats.start("pass0_p")
            stats.start("pass0_w")
        self.assembler.statement(filename=self.source)
        if self.clstats:
            stats.stop("pass0_p")
            stats.stop("pass0_w")

        # All of the parsed and sane statements are now queued for assembly
        
        self.assembler.assemble()
        self.assemble_end_w=time.time()
        self.assemble_end=time.process_time()

        self.out_start=time.process_time()
        self.out_start_w=time.time()
        img=self.assembler.image()

        self.aout.write_listing(this_module,img.listing)
        self.aout.write_image(this_module,img.image)
        self.aout.write_deck(this_module,img.deck)
        self.aout.write_rc(this_module,img.rc)
        self.aout.write_vmc(this_module,img.vmc)
        self.aout.write_mc(this_module,img.mc)
        self.aout.write_ldipl(this_module,img.ldipl)

        if self.args.error==2:
            img.errors()
            
        self.out_end_w=time.time()
        self.out_end=time.process_time()
        
        if self.clstats:
            # Specify False to output stats from the assembler
            self.stats(update=True)
        
    # Report assembler stats
    def stats(self,update=True):
        stats=assembler.Stats
        if update:
            stats.update_start("process",self.process_start)
            stats.update_start("wall",self.wall_start)
        
            stats.update_start("import_p",self.import_start)
            stats.update_start("import_w",self.import_start_w)
        
            stats.update_start("objects_p",self.objects_start)
            stats.update_start("objects_w",self.objects_start_w)
            stats.update_stop( "objects_p",self.objects_end)
            stats.update_stop( "objects_w",self.objects_end_w)
        
            stats.update_stop( "assemble_p",self.assemble_end)
            stats.update_stop( "assemble_w",self.assemble_end_w)
        
            stats.update_start("output_p",self.out_start)
            stats.update_start("output_w",self.out_start_w)
            stats.update_stop( "output_p",self.out_end)
            stats.update_stop( "output_w",self.out_end_w)
        
        print(stats.report())

# Parse the command line arguments
def parse_args(dm):
    parser=argparse.ArgumentParser(prog="asma.py",
        epilog=copyright, 
        description="from assembler source create a bare-metal usable file")

    # Source input file (Note: attribute source in the parser namespace will be a list)
    parser.add_argument("source",\
        help="input assembler source file path",nargs=1)

    # Override MSL maximum address size
    # May be specified in a local configuration
    parser.add_argument("-a","--addr",type=int,choices=[16,24,31,64],\
        help="override target CPU maximum address size in listing")

    # Machine Target
    parser.add_argument("-c","--cpu",required=True,
        help="MSL database target cpu, for example, '2025'")

    # Dump the completed CSECT's, region's and image
    # May be specified in a local configuration
    parser.add_argument("-d","--dump",action="store_true",default=False,\
        help="listing provides the image content in storage dump format")

    # Specify error handling level
    # May be specified in a local configuration
    parser.add_argument("-e","--error",type=int,choices=[0,1,2],default=2,\
        help="specify error handling level")

    # Generic list directed IPL option
    parser.add_argument("-g","--gldipl",
        help="directory containing list directed IPL files")

    # Path and filename of the written binary image file
    parser.add_argument("-i","--image",
        help="binary image file containing content")

    # Machine Specification Language database source file
    parser.add_argument("-l","--listing",
        help="assembly listing file")

    # Machine Specification Language database source file
    parser.add_argument("-m","--msldb",default="msl.txt",
        help="path to MSL database source file")

    # Maximum depth of nested input sources.
    # May be specified in a local configuration
    nest_default=20
    parser.add_argument("-n","--nest",type=int,default=nest_default,
        help="maximum depth of nested input sources (default %s)" % nest_default)

    # Object Deck file name
    parser.add_argument("-o","--object",
        help="loadable object deck file with assembled content")

    # Specify the initial XMODE PSW format
    psw_formats=["S","360","67","BC","EC","380","XA","E370","E390","Z","none"]
    parser.add_argument("-p","--psw",choices=psw_formats,
        help="set the initial XMODE PSW format (none disables the PSW directive)")

    # Hercules RC script file
    parser.add_argument("-r","--rc",
        help="Hercules RC script file with assembled content")

    # STORE command file
    parser.add_argument("-s","--store",
        help="STORE command file with assembled content")

    # virtual machine STORE ommand file 
    parser.add_argument("-v","--vmc",
        help="virtual machine STORE command file with assembled content")

    # Specify the initial XMODE CCW format
    parser.add_argument("-w","--ccw",choices=["0","1","none"],
        help="set the initial XMODE CCW format (none disables the CCW directive)")

    # Define the local default specification
    parser.add_argument("--config",default="default",\
        help="identify the local configuration, if not specified standard defaults "
            "apply")

    # Specify the code page file
    parser.add_argument("--cpfile",
        help="specify the code page source file to be used")

    # Specify the code page translation definition to be used
    # May be specified in a local configuration
    parser.add_argument("--cptrans",default="94C",
        help="specify the code page translation (defaults to '94C')")

    # Build list of instructions or assembler directives to trace
    parser.add_argument("--oper",action="append",default=[],\
        help="indicate the operation by name to trace (may be used multiple times)")

    # Build list of passes to trace
    parser.add_argument("--pas",action="append",type=int,default=[],\
        help="indicate by number a pass to be traced (may be used multiple times)")

    # Enable statistics reporting
    # May be specified in a local configuration
    parser.add_argument("--stats",action="store_true",default=False,\
        help="enables statististics reporting")

    # Add debug options from Debug Manager
    dm.add_argument(parser,help="enable debug option")

    return parser.parse_args()

if __name__ == "__main__":
    objects_start=time.process_time()
    objects_start_w=time.time()

    dm=assembler.Assembler.DM()
    args=parse_args(dm)
    print(copyright)
    ASMA(args,dm).run()
