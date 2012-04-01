.ifndef .LELF32_S
.LELF32_S = 1
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
 
 # ELF 32-bit related Macros
 #
 # Dependencies:
 #   ELF.S - for ELF structures and values

 # s370 ELF executable header
          .macro e32s370
          .long  0x7F454C46    # ELF identification
          .byte  .Lei32        # 32-bit ELF
          .byte  .Leibig       # big-endian
          .byte  .Leicur       # Current ABI version
          .byte  .Leiosno      # No OS ABI extensions
          .byte  .Leiabino     # No ABI version specified
          .byte  0,0,0,0,0,0,0 # Ident padding
          .hword .Letexec      # Executable ELF
          .hword .Lems370      # Machine type
          .long  .Levcurrent   # File version
          .endm

 # s390 ELF executable header

          .macro e32s390
          .long  0x7F454C46    # ELF identification
          .byte  .Lei32        # 32-bit ELF
          .byte  .Leibig       # big-endian
          .byte  .Leicur       # Current ABI version
          .byte  .Leiosno      # No OS ABI extensions
          .byte  .Leiabino     # No ABI version specified
          .byte  0,0,0,0,0,0,0 # Ident padding
          .hword .Letexec      # Executable ELF
          .hword .Lems390      # Machine type
          .long  .Levcurrent   # File version
          .endm

 # Generic 32-bit entry calculation
 #
 #   Registers: entry number is converted into an address
 #     ntryr = entry number on entry, address on exit
 #     tblr  = register that points to the start of the table
 #
 #   Program Labels
 #     size  = label of a half word containing 

          .macro elfent32 ntryr tblr elfr size
          mh     \ntryr,\size(\elfr)
          alr    \ntryr,\tblr
          .endm

 # Locate the program segment table in a 32-bit ELF
          .macro e32ptbl ptblr elfr
          lr     \ptblr,\elfr   # Get the start of the ELF
          al     \ptblr,.Lephoff32(\elfr)  # Add the segment table offset
          .endm

 # Locate the program table entry in a 32-bit ELF
          .macro e32ptn ptbnx ptblr elfr
          elfent32 \ptbnx,\ptblr,\elfr,.Lephent32
          .endm

 # Locate the section header table in a 32-bit ELF
          .macro e32stbl stblr elfr
          lr     \stblr,\elfr   # Get the start of the ELF
          al     \stblr,.Leshoff32(\elfr)  # Add the section table offset
          .endm

 # Locate a section table entry in a 32-bit ELF
          .macro e32stn stbnx stblr elfr
          elfent32 \stbnx,\stblr,\elfr,.Leshent32
          .endm

 # Scan a 32-bit ABI table
 #
 #  e32scan? - start the scan of the section table
 #  e32next? - increment to the next table entry and process it
 #
 #  Registers:
 #    cntr  = a register used to count the number of table entries
 #    ?tblr = a register used to point to the current table entry
 #    elfr  = a register pointing to the start of the ELF
 #
 #  Program Labels:
 #     iter = location that processes the next entry
 #
 #  Example:
 #            e32scanp 1,2,3  # Start scan of program table
 #    .Liter: # process current entry
 #
 #            e32nextp .Liter,1,2,3 # Process the next entry
 #    [ Fall through when all processed ]

          .macro e32next size iter cntr tblr elfr br=13 b=0b
          ah     \tblr,\size(\elfr)
          bct    \cntr,\iter-\b(\br)
          .endm

          .macro e32scanp cntr ptblr elfr
          e32ptbl \ptblr,\elfr
          lh     \cntr,.Lephnum32(\elfr)
          .endm

          .macro e32nextp iter cntr ptblr elfr br=13 b=0b
          e32next .Lephent32,\iter,\cntr,\ptblr,\elfr,\br,\b
          .endm

          .macro e32scans cntr stblr elfr
          e32stbl \stblr,\elfr
          lh     \cntr,.Leshnum32(\elfr)
          .endm

          .macro e32nexts iter cntr stblr elfr br=13 b=0b
          e32next .Leshent32,\iter,\cntr,\stblr,\elfr,\br,\b
          .endm

 # Locate a program segment header of a specific type
 #
 #  Registers:
 #    typr  = contains a segment type being processed
 #    cntr  = a register used to count the program segment table entries
 #    stblt = a register used to point to the found segment table entry
 #    elfr  = a register pointing to the start of the ELF
 #    br    = the current program base register, defaults to %r15
 #
 #  Program Labels:
 #    found = where to process the found section
 #    done  = where to pass control after all sections have been processed
 #    iter  = where to continue the scan after processing a section header
 #    b     = the program base label, defaults to 0b
 #
 #  Example:
 #            la    1,typex
 #            e32styp .Lfound,.Ldone,.Liter,1,2,3,4
 #   .Lfound: # process the found entry
 #
 #            b    .Liter-0b(15) # scan for the next entry of type typex
 #   .Ldone:  # All entries processed, continue

          .macro e32ptyp found done iter typr cntr stblr elfr br=13 b=0b
          e32scanp \cntr,\stblr,\elfr
1:        cl     \typr,.Lptype32(\stblr)
          be     \found-\b(\br)
\iter:    e32nextp 1b,\cntr,\stblr,\elfr,\br,\b
          b      \done-\b(\br)
          .endm

 # Locate a section header of a specific type
 #
 #  Registers:
 #    typr  = contains a section type being processed
 #    cntr  = a register used to count the section table entries
 #    stblr = a register used to point to the found section table entry
 #    elfr  = a register pointing to the start of the ELF
 #    br    = the current program base register, defaults to %r15
 #
 #  Program Labels:
 #    found = where to process the found section
 #    done  = where to pass control after all sections have been processed
 #    iter  = where to continue the scan after processing a section header
 #    b     = the program base label, defaults to 0b
 #
 #  Example:
 #            la    1,typex
 #            e32styp .Lfound,.Ldone,.Liter,1,2,3,4
 #   .Lfound: # process the found entry
 #
 #            b    .Liter-0b(15) # scan for the next entry of type typex
 #   .Ldone:  # All entries processed, continue

          .macro e32styp found done iter typr cntr stblr elfr br=13 b=0b
          e32scans \cntr,\stblr,\elfr
1:        cl     \typr,.Lshtype32(\stblr)
          be     \found-\b(\br)
\iter:    e32nexts 1b,\cntr,\stblr,\elfr,\br,\b
          b      \done-\b(\br)
          .endm

.endif # .ifndef .LELF32_S scope
