#!/usr/bin/python3
# Copyright (C) 2016 Harold Grovesteen
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

# This module provides the command-line interface for invoking the Hercules
# operation code audit module: tools/herc/hopaudit.py.

this_module="hopcodes.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2016")

# Python Imports:
import sys
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse       # Access command-line processor

# SATK Imports:
import satkutil       # Access dynmamic Python path modifications
satkutil.pythonpath("asma")         # Access msldb for MSL database access
satkutil.pythonpath("tools/herc")   # Access the Hercules audit module
satkutil.pythonpath("tools/lang")   # Access sopl.py for asma msldb module
import herc_audit     # Access the Hercules operation code audit processing


# Parse the command line arguments.
# Returns:
#   argparse Namespace object.
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,
        epilog=copyright, 
        description="audits Hercules operation code tables against ASMA MSL "\
            "specifications")

    parser.add_argument("-H","--Hercules",metavar="DIR",\
        help="Hercules root source directory. If omitted the current working "
            "directory is assumed to be the Hercules root directory")

    parser.add_argument("-l","--listing",metavar="FILEPATH",\
        help="optional audit report output listing file path")

    parser.add_argument("-v","--verbose",action="store_true",default=False,\
        help="specifies that the audit report is to be displayed.  Assumed if "
        "--listing is omitted")

    return parser.parse_args()


if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    herc_audit.Hercules_Opcodes(args,satkutil.satkdir("asma/msl")).run(debug=True)
