.ifndef .LELF64
.LELF64 = 1
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

 # ELF 64-bit related Macros
 #
 # Dependencies:
 #   ELF.S - for ELF structures and values

 # s390x ELF executable header
          .macro e64s390x
          .long  0x7F454C46    # ELF identification
          .byte  .Lei64        # 64-bit ELF
          .byte  .Leibig       # big-endian
          .byte  .Leicur       # Current ABI version
          .byte  .Leiosno      # No OS ABI extensions
          .byte  .Leiabino     # No ABI version specified
          .byte  0,0,0,0,0,0,0 # Ident padding
          .hword .Letexec      # Executable ELF
          .hword .Lems390      # Machine type
          .long  .Levcurrent   # File version
          .endm

 # Generic 64-bit entry calculation
 #
 #   Registers: entry number is converted into an address
 #     ntryr = entry number on entry, address on exit
 #     tblr  = register that points to the start of the table
 #
 #   Program Labels
 #     size  = label of a half word containing 

          .macro elfent64 ntryr tblr size
          mghi   \ntryr,\size
          algr   \ntryr,\tblr
          .endm

 # Locate the program segment table in a 64-bit ELF

          .macro e64ptbl ptblr elfr
          lgr    \ptblr,\elfr              # Get the start of the ELF
          alg    \ptblr,.Lephoff64(\elfr)  # Add the segment table offset
          .endm

 # Locate the program table entry in a 32-bit ELF

          .macro e64ptn ptbnx ptblr
          elfent64 \ptbnx,\ptblr,.Lephdr64_len
          .endm

 # Locate the section table in a 64-bit ELF

          .macro e64stbl stblr elfr
          lgr    \stblr,\elfr              # Get the start of the ELF
          alg    \stblr,.Leshoff64(\elfr)  # Add the section table offset
          .endm

 # Locate the section table entry in a 64-bit ELF

          .macro e64stn stbnx stblr
          elfent64 \stbnx,\stblr,.Leshdr64_len
          .endm

 # Locate the symbol table entry in a 64-bit ELF

          .macro e64sym symxr stblr
          elfent64 \symxr,\stblr,.Lesym64_len
          .endm

 # Scan a 64-bit ABI table
 #
 #  e64scan? - start the scan of the section table
 #  e64next? - increment to the next table entry and process it
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
 #            e64scanp 1,2,3  # Start scan of program table
 #    .Liter: # process current entry
 #
 #            e64nextp .Liter,1,2 # Process the next entry
 #    [ Fall through when all processed ]

          .macro e64next size iter cntr tblr
          aghi   \tblr,\size
          brctg  \cntr,\iter
          .endm

          .macro e64scanp cntr ptblr elfr
          e64ptbl \ptblr,\elfr            # Locate the first program segment
          lgh    \cntr,.Lephnum64(\elfr)  # Load the number of segment entries
          .endm

          .macro e64nextp iter cntr ptblr
          e64next .Lephdr64_len,\iter,\cntr,\ptblr
          .endm

          .macro e64scans cntr stblr elfr
          e64stbl \stblr,\elfr
          lgh    \cntr,.Leshnum64(\elfr)
          .endm

          .macro e64nexts iter cntr stblr
          e64next .Leshdr64_len,\iter,\cntr,\stblr
          .endm

 # Locate a program header of a specific type
 #
 #  Registers:
 #    typr  = contains a section type being processed
 #    cntr  = a register used to count the section table entries
 #    stblt = a register used to point to the found section table entry
 #    elfr  = a register pointing to the start of the ELF
 #
 #  Program Labels:
 #    found = where to process the found section
 #    done  = where to pass control after all sections have been processed
 #    iter  = where to continue the scan after processing a section header
 #
 #  Example:
 #            la    1,typex
 #            e64ptyp .Lfound,.Ldone,.Liter,1,2,3,4
 #   .Lfound: # process the found entry
 #
 #            j   .Liter   # scan for the next entry of type typex
 #   .Ldone:  # All entries processed, continue

          .macro e64ptyp found done iter typr cntr stblr elfr
          e64scanp \cntr,\stblr,\elfr
1:        cl     \typr,.Lptype64(\stblr)
          je     \found
\iter:    e64nextp 1b,\cntr,\stblr
          brc     15,\done
          .endm

 # Locate a section header of a specific type
 #
 #  Registers:
 #    typr  = contains a program segment type being processed
 #    cntr  = a register used to count the segment table entries
 #    stblt = a register used to point to the found segment table entry
 #    elfr  = a register pointing to the start of the ELF
 #
 #  Program Labels:
 #    found = where to process the found section
 #    done  = where to pass control after all sections have been processed
 #    iter  = where to continue the scan after processing a section header
 #
 #  Example:
 #            la    1,typex
 #            e64styp .Lfound,.Ldone,.Liter,1,2,3,4
 #   .Lfound: # process the found entry
 #
 #            j   .Liter   # scan for the next entry of type typex
 #   .Ldone:  # All entries processed, continue

          .macro e64styp found done iter typr cntr stblr elfr
          e64scans \cntr,\stblr,\elfr
1:        cl     \typr,.Lshtype64(\stblr)
          je     \found
\iter:    e64nexts 1b,\cntr,\stblr
          brc     15,\done
          .endm

 # The macros assist in relocation.  They are all based upon a pointer to
 # a 64-bit relocation entry in a register.  The result is placed in a register
 # which is the first macro argument.  The second argument is a pointer to
 # the relavent table entry. Additional arguments may be required depending upon
 # the value being retrieved.

 # Fetch A from a relocation entry

          .macro l_A64 reg relor
          lg     \reg,.Lrelaadd64(\relor)
          .endm

 # Fetch S from a symbol table

          .macro l_S64 reg symr
          lg     \reg,.Lstval64(\symr)
          .endm

 # Bounds checking for 64-bit relocations

          .macro ck_zeros reg mask error br=13 b=0b
          ng     \reg,\mask-\b(\br)
          jnz    \error
          .endm

          .macro ck_zeros_ones reg mask error br=13 b=0b
          ng     \reg,\mask-\b(\br)
          jz     1f
          cl     \reg,\mask-\b(\br)
          jne    \error
1:
          .endm

.Le64_half16 = 0xFFFFFFFFFFFF0000
.Le64_pc16   = 0xFFFFFFFFFFFE0000
.Le64_pc32   = 0xFFFFFFFE00000000
.Le64_low12  = 0xFFFFFFFFFFFFF000
.Le64_byte8  = 0xFFFFFFFFFFFFFF00

.endif
