.ifndef .LIPLELF_S
.LIPLELF_S = 1
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

 # This module defines for program use the IPL ELF standard real storage usage and
 # macros that define the various special sections used by the IPL ELF standard

 #  The following macros establish IPL ELF special sections
 #     Macro           Description
 #     iplelf_ccw    Defines the section used to create the executable CCW program
 #                   segment
 #     iplelf_ipl    Defines the section used to create the executable IPL program 
 #                   segment

 # Standard usage of real storage by the IPL ELF standard
.LIPL_parms   = 0x200   # 64-bytes of IPL parameters from R0-R15
.LIPL_bs      = 0x240   # .long  Address of the bootstrap services function list
.LIPL_fbarepo = 0x244   # .long  Starting sector of FBA repository
.LIPL_fbasize = 0x248   # .long  Size of the FBA repository in bytes
.LIPL_unused  = 0x24C   # .long  Not currently specified

 # iplelf_ipl - Start a iplelf_ipl section.
 #  Macro Parameters:
 #       area   Storage area into which the TEXT segment of ELF is to be loaded 
 #              (optional)
 #       text   Specify 'yes' to place in storage only IPL ELF TEXT segment during
 #              the IPL function, otherwise the entire IPL ELF will be loaded
 #              (default 'no')
 #
 # The iplelf_ipl macro must be followed with a psw macro defining the IPL PSW used
 # during the IPL function.

         .macro iplelf_ipl area text=no
   .ifc \text,yes
      .ifb \area
            .section .iplt,"a",@progbits
      .else  # .ifb \area
            .section .iplt.\area,"a",@progbits
      .endif # .ifb \area
   .else  # .ifc \text,yes
       .ifb \area
            .section .ipl,"a",@progbits
      .else  # .ifb \area
            .section .ipl.\area,"a",@progbits
      .endif # .ifb \area
   .endif # .ifc \text,yes
         .endm

.endif # .ifndef .LIPLELF_S
