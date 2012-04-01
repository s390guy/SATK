.ifndef .Lcdrommbed_S
.Lcdrommbed_S=1
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

 # CDROM embedded loader

          .eject
          .sbttl "Embedded Loader"
 # LOADER Segment
 #         .section .loader,"a",@progbits

 # Beginning of card ESA/390 or z/Architecture bootstrap loader program
 # Entry is in 24-bit addressing mode

 # Register Usage:
 #  R0     not used
 #  R1     not used
 #  R2     not used
 #  R3     not used
 #  R4     boot program entry point address
 #  R5     not used
 #  R6     not used
 #  R7     not used
 #  R8     not used
 #  R9     not used
 #  R10    not used
 #  R11    not used
 #  R12    Base register
 #  R13    not used
 #  R14    not used
 #  R15    On a disabled wait, it reflects where the error occurred. But this
 #         can not happen with this program because the disabled wait PSW is 
 #         never loaded.

           .sbttl "Embedded Loader - Macros"
           .eject
           .include "archmode.S"

           .include "loaderif.S"

 #         .include "bootnter.S" - CDROM does not use boot content for entry

 #         .include "iortn.S" - CDROM does not use I/O routine for bootstrapping

           .sbttl "Embedded Loader - Boot Program"
           .eject
 # LOADER Segment

           loaderif  0,'S,'S,'P,'N,'Y,0x01,0x60,.Lbaseadj
    # S = IPL program supported with stream format (but IPL function loads it)
    # S = LOWC segment supported with stream format (but IPL function loads it)
    # P = Physical end-of-file indicator used (but it is the host end-of-file)
    # N = Blocks must be padded to full size of the block
    # Y = Medium preparation process does provide data


 # This is the minimum a CDROM embedded loader would do, a stub really.  Because
 # the CDROM IPL function will load everything, including the booted program,
 # there is very little required of the CDROM loader.  However, if there was
 # more extensive initialization required in a specific case, the CDROM loader
 # would do it here before entering the program.

 # Enter program
.Lenter:
    # Enter architecture mode required by bootstrapped program
           cli      .Lreqarch-0b(12),0x64    # Is z/Architecture required?
           bne      .Lenter32-0b(12)         # ..No, enter ELF in ESA/390 mode        
           zarch     10,13,error=.Lexitarch  # ..Yes, enter z/Architecture
    # Now in z/Architetecture mode
           sam64                             # Set address mode to 64
           sgr      4,4                      # Make sure entry zero
           b         .Lpgmbr-0b(12)          # Go ahead and use interface entr

.Lenter32: 
    # Pass control to bootstrapped program in ESA/390 mode
           sam31                             # Set amode to 31
.Lpgmbr:
           l        4,.Lpgmntry-0b(12)       # Get entry from loader interface
           br       4                        # Just pass control

           .align   4

.Lbaseadj: .long    1b-0b                    # Adjustment to base

.Lexitarch:lpsw     .Lpswffd-0b(12)          # Enter wait state
.Lpswffd:  .long    0x000A0000,0x00000ffd    

.endif # .ifndef .Lcdrommbed_S scope
