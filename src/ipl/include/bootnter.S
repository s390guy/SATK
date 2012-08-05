.ifndef .Lbootnter_S
.Lbootnter_S=1
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

 # This macro provides standard entry for booted ELF executables
 #   elfenter Generate the logic to enter a 64- or 32-bit ELF executable
 # Arguments:
 #   loadr  = Register pointing to start of loaded boot content (required)
 #   entryr = Register used to enter booted program (required)
 #   parms  = Lable where IPL parms were saved (required)
 #   error  = Lable of where to pass control on an error (defaults to .Lexitpgm)
 #   zerr   = Lable of where to pass control on z/Architecture failure
 #            (Defaults to .Lexitarch)
 #   sym    = Lable prefix of generated symbols (defaults to .Lenter)
 #   er     = Register pointing to point of error (defaults to 15)
 #   br     = Base register (defaults to 12)
 #   b      = Lable of the current base (defaults to 0b)
 # Notes:
 #  The macro assumes the loaderif macro has been used to generate loader I/F
 #  symbols.  Error defaults assume that the exits macro has been used to generate
 #  standard disabled wait states.  Entering z/Architecture requires use of
 #  registers 10,11 and 13.
 
           .macro elfenter loadr:req entryr:req parms:req error=.Lexitpgm zerr=.Lexitarch sym=.Lenter er=15 br=12 b=0b
\sym:
           mvc      0x200(64),\parms-0b(12) # Restore IPL parameters
.ifdef __s390x__      # Only include if z/Architecture is supported
    # Enter architecture mode required by bootstrapped program
           cli      .Lreqarch-0b(12),0x64     # Is z/Architecture required?
           bne      \sym\()32-0b(12)          # ..No, enter ELF in ESA/390 mode        
           zarch     10,13,error=\zerr,br=\b  # ..Yes, enter z/Architecture
    # Now in z/Architetecture mode
           sam64                              # Set address mode to 64
           enterz   \loadr,\entryr,\error,er=\er,br=\br,b=\b
\sym\()32: 
.endif # .ifdef __s390x__ 
.ifndef __s370__
           sam31                              # Set amode to 31
.endif # .ifndef __s370__
           enter    \loadr,\entryr,\error,er=\er,br=\br,b=\b
           .endm
 
 # These macros enter the booted program.
 #   enterz  enters in z/Architecture
 #   enter   enters in ESA/390 or System/370
 # Arguments:
 #   loadr  = Register pointing to start of loaded boot content (required)
 #   entryr = Register used to enter booted program (required)
 #   error  = Lable of where to pass control on an error (required)
 #   er     = Register pointing to point of error (defaults to 15)
 #   br     = Base register (defaults to 12)
 #   b      = Lable of the current base (defaults to 0b)

           .macro enterz loadr:req entryr:req error:req er=15 br=12 b=0b
           clc      0(4,\loadr),4f+12-\b(\br)       # Did we load an ELF header?
           bne      2f-\b(\br)                      # ..No, enter TEXT segment
           clc      18(2,\loadr),4f+10-\b(\br)      # s370 ELF? (9 or 0x0009)
           be       3f-\b(\br)                      # ..Yes, enter it.
           clc      18(2,\loadr),4f+8-\b(\br)       # s390 ELF? (22 or 0x0016)
           be       .+8-\b(\br)                     # ..Yes, see how to enter it
           bas      \er,\error-\b(\br)              # ..No, I don't know what to do
           cli      4(\loadr),0x02                  # 64-bit ELF?
           be       .+8-\b(\br)                     # ..Yes, enter 64-bit ELF
           b        3f-\b(\br)                      # ..No, ender 32-bit ELF
    # Enter 64-bit ELF in z/Architecture mode
           lg       \entryr,24(\loadr)              # Load the 64-bit entry
           br       \entryr                         # Enter bootstrapped 64-bit ELF   
    # Enter TEXT segment in z/Architecture mode
2:         ng       \entryr,4f-\b(12)        # Make sure high-order bits are zero
           bnzr     \entryr                  # Have an entry, so go...
           bas      \er,\error-\b(12)        # ..DIE: No entry for TEXT segment
    # Enter 32-bit ELF in z/Architecture mode
3:         l        \entryr,24(\loadr)       # Get entry point from ELF header
           ng       \entryr,4f-\b(12)        # Make sure high-order bits are zero
           br       \entryr                  # and go...
           .align   8
4:         .quad    0x000000007FFFFFFF       # Clear bits 0-33 of 64-bit register
           .hword   22                       # s390 ELF machine type
           .hword   9                        # s370 ELF machine type
           .ascii   "\x7F"                   # ELF header magic
           .ascii   "ELF"
           .endm

           .macro enter loadr:req entryr:req error:req er=15 br=12 b=0b
           clc      0(4,\loadr),4f-4-\b(\br)          # Did we load an ELF header?
           bne      4f-\b(\br)                        # ..No, enter TEXT segment
           clc      18(2,\loadr),4f-6-\b(\br)         # Is this a s370 ELF?
           be       2f-\b(\br)                        # ..Yes, enter it.
           clc      18(2,\loadr),4f-8-\b(\br)         # Is this a s390 ELF?
           be       2f-\b(\br)                        # ..Yes, enter it.
           bas      \er,\error-\b(\br)                # ..No, don't know what to do
           cli      4(\loadr),0x02                    # Is it a 64-bit ELF?
           be       3f-\b(\br)                        # ..Yes, enter ELF
    # Enter 32-bit ELF in ESA/390 mode
2:         l        \entryr,24(\loadr)      # Get entry point from ELF header
           br       \entryr                 # Enter the ELF
    # Enter 64-bit ELF in ESA/390 mode
3:         l        \entryr,28(\loadr)      # Get entry point from ELF header
           br       \entryr                 # Enter the ELF
           .hword   22                      # s390 ELF machine type
           .hword   9                       # s370 ELF machine type
           .ascii   "\x7F"                  # ELF header magic
           .ascii   "ELF"
    # Enter TEXT segment in ESA/390 mode
4:         ltr      \loadr,\loadr           # Did we actually read any blocks?
           bnzr     \loadr                  # ..Yes, beginning of text is entry
           bas      \er,\error-\b(\br)      # ..DIE: not entry point

           .endm

.endif # .ifndef .Lbootnter_S scope
