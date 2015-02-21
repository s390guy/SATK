Copyright (C) 2013,2015 Harold Grovesteen

    This file is part of SATK.

    SATK is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SATK is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SATK.  If not, see <http://www.gnu.org/licenses/>.

                              SATK Samples

The 'samples' directory contains examples and tests of various SATK components.
Active development is occurring with samples that utilize the SATK supplied assembler,
ASMA.  The ASMA assembler supports all architectures from System/360 to the most
current although all samples may not.

Sample programs using the ASMA assembler reside in the samples/asma directory.  Some
samples may require use of SATK supplied software residing in the srcasm directory.
These are identified below with the 'yes' in the SATK column.  Architectures supported
by the sample are identified in the description by the ASMA --target command-line
argument and its testing status.  Willing testers of various ASMA output formats are
sought.

The following samples are supplied in the samples/asma directory:

File          SATK    Description
----          ----    -----------

dsects.asm     yes    Assembles DSECTs used by SATK for reference purposes.
                      Architecture: all, but sensitive to current architecture
                      Tested: not applicable

hello.asm      yes    Simple Hello World program
                      Architecture:
                           s360  - tested under s370-BC mode
                           s370  - tested
                           s380  - not tested
                           e390  - tested
                           s390x - tested

hellof.asm     yes    Hello World program extended to use functions
                      Architecture:
                           s360  - tested under s370-BC mode
                           s370  - tested
                           s380  - not tested
                           e390  - tested
                           s390x - tested

sos.asm        no     Sample Operating System described in Madnick/Donovan book
                      "Operating Systems".
                      Architecture: 
                           s360   - not tested
                           s370BC - not tested
