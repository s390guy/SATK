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

# This script reads a text file and seeks to determine if the GNU as listing has
# any undefined symbols.  GNU as treats undefined symbols as normal and does not
# report them on the console.  The assumption is that the undefined symbols will be
# defined during linkage editing.  For native assembler programs (as opposed to 
# compiler generated listings), undefined symbols usually indicate errors.  This
# script will displayed the undefined symbols on the output.

import sys       # System module

noerror="NO UNDEFINED SYMBOLS"
noerror_len=len(noerror)
error="UNDEFINED SYMBOLS"
error_len=len(error)

def ckas(filename):
    try:
        listing=open(filename,"rt")
    except IOError:
        print("ckaslst.py: error - could not open GNU as listing: %s" % filename)
        sys.exit(1)
    errorline=False
    for line in listing:
        if errorline:
            # Encountered undefined symbols, so print them
            print(line[:-1])
            continue
        if len(line)>=noerror_len and line[:noerror_len]==noerror:
            # For GNU as listing without undefined symbols, silently end
            return
        if len(line)>=error_len and line[:error_len]==error:
            # There are undefined symbols, print the line and all undefined symbols
            print(line[:-1])
            errorline=True
    # If we get here and errorline is not set, then something went wrong
    if not errorline:
        print("ckaslst.py: error - did not recognize end of GNU as listing: %s" \
            % filename)
    listing.close()

if __name__ == "__main__":
    # sys.argv[0] == the script name
    # sys.argv[1] == the listing file name
    if len(sys.argv)!=2:
        print("ckaslst.py: error - expected one command line argument, found %s" \
            % len(sys.argv)-1)
        sys.exit(1)
    ckas(sys.argv[1])
    sys.exit(0)
    