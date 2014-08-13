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

# This module provides a command line interface to the Machine Specification Language
# (MSL) database generted by the msldb module.  For a description of the MSL, see
# module msldb.py.

this_module="msl.py"
copyright="msl.py Copyright (C) %s Harold Grovesteen" % "2014"

# Python imports:
import sys               # Access the exit method and Python version information
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse          # Access the command line parser

# Setup PYTHONPATH
import satkutil
satkutil.pythonpath("asma")        # Provides path to msldb
satkutil.pythonpath("tools/lang")  # Provides path to sopl

# ASMA imports
import msldb             # Access the database


#
#  +----------------------------+
#  |                            |
#  |   Command Line Execution   |
#  |                            |
#  +----------------------------+
#

class MSLIF(object):
    def __init__(self,args):
        self.mslfile=args.mslfile[0]   # Input MSL text file

        # Normal processing options
        self.expand=args.expand        # Expand a cpu statment with dependencies
        self.fail=args.fail            # If True fail immediately on an error
        self.xref=args.xref            # Print the cross-reference listing

        # Diagnostic options
        self.dump=args.dump            # Dump the final output DB

        # The Machine Language Specification Processor
        self.dbp=msldb.MSL(default=satkutil.satkdir("asma/msl",debug=False))

    def run(self):
        keep=self.expand is not None
        errors=self.dbp.build(self.mslfile,xref=self.xref,fail=self.fail,keep=keep)
        self.dbp.printWarnings()
        if errors:
            self.dbp.printErrors()
            if self.expand is not None:
                cls_str="msl.py - %s.run() -" % self.__class__.__name__ 
                print("%s output suppressed due to database build errors" % cls_str)
            sys.exit(2)
        if self.xref:
            self.dbp.xref()
        final=self.dbp.DB()
        if self.expand is not None:
            final=self.dbp.expand(self.expand)
            # Final may be a MSLDB object or a CPUX object
        if self.dump is not None:
            if self.dump=="full":
                final.dump(sort=True)
            else:
                final.summarize(sort=True)

#
#  +-----------------------------+
#  |                             |
#  |   Command Line Processing   |
#  |                             |
#  +-----------------------------+
#

# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog="msl.py",
        epilog=copyright, 
        description="validates for correctness a Machine Specification Language "
                    "text file")

    # Input text file (attribute mslfile in the parse_arg namespace will be a list)
    parser.add_argument("mslfile",\
        help="input MSL source file path",nargs=1)

    # Extract the machine specification for a specific machine, or 'all', the default.
    parser.add_argument("-e","--expand",\
        help="expand this cpu statemnt with database subset")

    # Force failure upon detecting an error
    parser.add_argument("-f","--fail",action="store_true",default=False,\
        help="fail upon detection of an error, otherwise report at process end")

    # Produce a statement cross reference listing
    parser.add_argument("-x","--xref",action="store_true",default=False,\
        help="produce a statement cross reference listing")

    # Dump the database Python content of the internal Python database objects.
    parser.add_argument("--dump",choices=["full","summary"],\
        help="dumps the the database entries' Python content")

    return parser.parse_args()

if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    MSLIF(args).run()
