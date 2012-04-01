.ifndef .LSYSIB_S
.LSYSIB_S = 1
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

 # This module contains definitions of the System Information Block

.LSYSIB_1_1_1 = 0x1000000100000001   # STSI R0,R1 values to select SYSIB 1.1.1
.LSYSIB_1_2_1 = 0x1000000200000001   # STSI R0,R1 values to select SYSIB 1.2.1
.LSYSIB_1_2_2 = 0x1000000200000002   # STSI R0,R1 values to select SYSIB 1.2.2
.LSYSIB_2_2_1 = 0x2000000200000001   # STSI R0,R1 values to select SYSIB 2.2.1
.LSYSIB_2_2_2 = 0x2000000200000002   # STSI R0,R1 values to select SYSIB 2.2.2
.LSYSIB_3_2_2 = 0x3000000200000002   # STSI R0,R1 values to select SYSIB 3.2.2


 # +---------------------------------------------+
 # |  SYSIB 1.1.1 - Basic Machine Configuration  |
 # +---------------------------------------------+

 # Bytes 0-31 are reserved
.LSYSIB111_man = 32   # .octa   Manufacturer left justified EBCDIC space filled
.LSYSIB111_type= 48   # .long   Machine type
 # Bytes 52-63 are reserved
.LSYSIB111_model=64   # .octa   Model id left justified EBCDIC space filled
.LSYSIB111_seq = 80   # .octa   Squence code right justified EBCDIC zero filled
.LSYSIB111_plant=96   # .long   Plant left justified EBCDIC space filled
 # Bytes 84-4095 are reserved

.endif # .ifndef .LSYSIB_S scope
