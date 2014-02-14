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
import argparse
import sys

# ASMA imports
import assembler

# SATK imports
#import satkutil

class ASMA(object):
    def __init__(self,args,dm):
        self.dm=dm       # Global Debug Manager instance
        self.args=args   # Command line arguments

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
            otrace=args.oper)

        self.source=args.source[0]     # Source input file

    def run(self):
        self.assembler.statement(filename=self.source)

        # All of the parsed and sane statements are now queued for assembly
        self.assembler.assemble()

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

# Parse the command line arguments
def parse_args(dm):
    parser=argparse.ArgumentParser(prog="asma.py",
        epilog=copyright, 
        description="from assembler source create an image file")

    # Source input file (Note: attribute source in the parser namespace will be a list)
    parser.add_argument("source",\
        help="input assembler source file path",nargs=1)

    # Override MSL maximum address size
    parser.add_argument("-a","--addr",type=int,choices=[16,24,31,64],\
        help="override target CPU maximum address size in listing")

    # Machine Target
    parser.add_argument("-c","--cpu",required=True,
        help="MSL database target cpu, for example, '2025'")

    # Dump the completed CSECT's, region's and image
    parser.add_argument("-d","--dump",action="store_true",default=False,\
        help="listing provides the image content in storage dump format")

    # Specify error handling level
    parser.add_argument("-e","--error",type=int,choices=[0,1,2],default=2,\
        help="specify error handling level")

    # Generic list directed IPL option
    parser.add_argument("-g","--gldipl",
        help="directory containing list directed IPL files")

    # Machine Specification Language database source file
    parser.add_argument("-i","--image",
        help="binary image file containing content")

    # Machine Specification Language database source file
    parser.add_argument("-l","--listing",
        help="assembly listing file")

    # Machine Specification Language database source file
    parser.add_argument("-m","--msldb",default="msl.txt",
        help="path to MSL database source file")

    # Maximum depth of nested input sources.
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

    # Build list of instructions or assembler directives to trace
    parser.add_argument("--oper",action="append",default=[],\
        help="indicate the operation by name to trace (may be used multiple times)")

    # Build list of passes to trace
    parser.add_argument("--pas",action="append",type=int,default=[],\
        help="indicate by number a pass to be traced (may be used multiple times)")

    # Add debug options from Debug Manager
    dm.add_argument(parser,help="enable debug option")

    return parser.parse_args()

if __name__ == "__main__":
    dm=assembler.Assembler.DM()
    args=parse_args(dm)
    print(copyright)
    ASMA(args,dm).run()
