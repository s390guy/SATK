.ifndef .Ldwait_S
.Ldwait_S = 1
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

 # This module defines SATK disabled wait state codes

 # CP.S and other hypervisor wait state codes:
.Ldw_cmdfail =  0x0500   # Command to console failed
.Ldw_biosub  =  0x0501   # Block I/O sub-interruption code invalid
.Ldw_biostat =  0x0502   # Block I/O I/O status invalid

 # devio.S wait state codes:
.Ldw_invccwa =  0x0600   # Invalid CCW address encountered
.Ldw_invccwf =  0x0602   # Invalid CCW format encountered
.Ldw_statlost=  0x0604   # Status lost
.Ldw_nostatus=  0x0606   # No status available on I/O interrupt
.Ldw_iohalfdn=  0x0608   # Channel and Device did not end together on Hercules
.Ldw_unexpect=  0x060A   # Unexpected results
 # 07xx = Channel/Subchannel Program Errors
.Ldw_chainck =  0x0701   # CCW chaining check status
.Ldw_ifctlck =  0x0702   # CCW channel interface control check status
.Ldw_chctlck =  0x0704   # CCW channel control check status
.Ldw_chdatck =  0x0708   # CCW channel data check status
.Ldw_protck  =  0x0710   # CCW protection check status
.Ldw_pgmck   =  0x0720   # CCW program check status
.Ldw_badlen  =  0x0740   # CCW incorrect length status
 # deviosys.S wait state codes
.Ldw_badioprm=  0x0750   # Bad interrupt parameter
.Ldw_baddsdag=  0x0752   # Display Subchannel DIAGNOSE X'8' failed

 # display.S wait state codes:
.Ldw_dmgd    =  0x0204   # Diagnose command to display a message failed
.Ldw_dmgc    =  0x0208   # Display command failed

 # elfldld32.S, elfldld64.S, elfrelo32.S and elfrelo64.S wait state codes:
.Ldw_not64   =  0x0304   # ELF not in 64-bit format
.Ldw_noentry =  0x0308   # Entry point not found in ELF
.Ldw_not32   =  0x030C   # ELF not in 32-bit format

 # flih.S wait state codes:
.Ldw_badft   =  0x0800   # Invalid Interrupt Function Table specified.
.Ldw_nopfxft =  0x0802   # Function Table not registered in prefix area
.Ldw_badsub  =  0x0804   # Invalid Interrupt Function Table index specified

 # flihio.S wait state codes:
.Ldw_iobadft =  0x0900   # Function table not registered
.Ldw_iobadfun=  0x0902   # Subroutine not registered or unsupported
.Ldw_ionochan=  0x0904   # Channel I/O interrupt handling not supported

 # init.S wait state codes
.Ldw_archx   =  0x0404   # Unrecognized ELF architecture
.Ldw_gblfail =  0x0408   # Global relocation failed
.Ldw_lclfail =  0x040C   # Local relocation failed
.Ldw_badloc  =  0x0410   # Non-relocating program loaded in wrong location
.Ldw_archfail=  0x0414   # Setting of required architecture failed

 # intpgm.S wait state code
.Ldw_intpgm  =  0x0000   # Normal termination from a program interrupt

 # setarch.S wait state codes:
.Ldw_CPUdead =  0x0004   # cc=3, CPU not running
.Ldw_CPUbusy =  0x0008   # cc=2, CPU is busy
.Ldw_CPUstat =  0x000C   # cc=1, Order not accepted
.Ldw_badcur  =  0x0010   # Bad current architecture
.Ldw_baddesr =  0x0014   # Bad desired architecture
.Ldw_unsup   =  0x0018   # Unsupported architecture change
.Ldw_inccur  =  0x001C   # Current architecture incorrect
.Ldw_intrnl  =  0x0020   # Internal error
.Ldw_inarch  =  0x0024   # Already in desired architecture
.Ldw_notmain =  0x0028   # 64-to-32 bit change must be mainline.

 # trace.S wait state codes
.Ldw_tonfail =  0x0104   # Could not turn on instruction tracing
.Ldw_toffail =  0x0108   # Could not turn off instruction tracing

          .endif
