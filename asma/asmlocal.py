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

# This module provides support for local assembler command-line parameters

this_module="asmlocal.py"

# ASMA imports:
from assembler import local

# Use the local.config() method to supply command-line parameters.  This sample is
# equivalent to the standard defaults.
local.config(\
    name="sample",
    addr=None,
    ccw=None,
    cptrans="94C",
    dump=False,
    error=2,
    msldb="msl.txt",
    nest=20,
    stats=False)

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)