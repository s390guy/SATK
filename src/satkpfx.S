.ifndef .Lsatkpfx_S
.Lsatkpfx_S = 1
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

 # This module summarizes the various SATK defined uses of the prefix storage usage 
 #
 # This area of storage is restricted to real storage addresses 0x000-0xFFF

 # 0x000-0x1FF - Hardware assigned storage locations      - see src/psw.S, src/io.S
 # 0x200-0x24F - IPL ELF ABI Reserved storage area usage  - see ipl/include/IPLELF.S
 #               and "SATK for s390 - IPL Medium Preparation Processor"
 # 0x250-0x2AF - IPL Environment Information Block (IEIB) - see src/hal/IEIB.S
 # 0x2C0-0x5FF - Interrupt Handler Control Blocks (IHCBs) - see src/hal/IHCB.S
 # 0x638-0xCFF - unassigned
 # 0xD00-0xFFF - Interrupt handler general register save areas
.Lpfx_rsa_ext = 0xD00  # 128-bytes External interrupt register save area
.Lpfx_rsa_mck = 0xD80  # 128-bytes Machine Check register save area
.Lpfx_rsa_io  = 0xE00  # 128-bytes I/O interrupt register save area
.Lpfx_rsa_svc = 0xE80  # 128-bytes Supervisor Call register save area
.Lpfx_rsa_pgm = 0xF00  # 128-bytes Program Interrupt register save area
.Lpfx_rsa_rst = 0xF80  # 128-bytes Restart Interrupt register save area

.endif # .ifndef .Lsatkpfx_S
