.ifndef .Ltapembed_S
.Ltapembed_S=1
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

 # This is a test source module to develop support for the 
 # IPL ELF ABI Supplement.  It uses an embedded loader to load the program and 
 # default LOWC content.

 # Tape Device Embedded Loader

          .eject
          .sbttl "Embedded Loader"
 # Beginning of card ESA/390 or z/Architecture bootstrap loader program
 # Entry is in 24-bit addressing mode

 # Register Usage:
 #  R0     not used
 #  R1     Subchannel ID number (R1 required by I/O instructions)
 #  R2     ELF header address
 #  R3     Retry count
 #  R4     ELF entry point address
 #  R5     Work register
 #  R6     not used
 #  R7     not used
 #  R8     Main loop address
 #  R9     Read card subroutine address
 #  R10    SIGNAL PROCESSOR status register
 #  R11    SIGNAL PROCESSOR parameter register
 #  R12    Base register
 #  R13    SIGNAL PROCESSOR address of CPU being signaled
 #  R14    Subroutine return address
 #  R15    On a disabled wait, it reflects where the error occurred

           .sbttl "Embedded Loader - Macros"
           .eject
           .include "archmode.S"

           .include "loaderif.S"

           .include "bootnter.S"

           .include "iortn.S"

           .sbttl "Embedded Loader - Boot Program"
           .eject
 # LOADER Segment

           loaderif 516,'D,'N,'P,'N,'Y,0x10,0x60,.Lbaseadj

   # D = IPL program supported with directed block format
   # N = LOWC segment not supported (medium preparation process handles)
   # P = Physical end-of-program indicator used
   # N = Blocks do not require padding to full size of the block
   # Y = Medium preparation process provides its data

           mvc      .Liplparms-0b(64,12),0x200  # Save the IPL parms for restore

           # Set up I/O registers
           l        1,0xB8                   # Load SID word R1 from 0xB8
           lctl     6,6,.Lctlr6-0b(12)       # Load Control Register 6

           # Set up program register
           la       9,.Lread-0b(12)          # Read subroutine
           sr       2,2                      # Make sure ELF header is 0

           la       3,10                     # Max 10 tries to test subchannel
           basr     14,9                     # Read First Card
           l        2,.Lccwpgm1+4            # Fetch start of data location
.Lloop:
           la       3,10                     # Max 10 tries to test subchannel
           basr     14,9                     # Read Card
           b        .Lloop-0b(12)            # Process next record

 # Enter program - Read subroutine passes control here when EOF encountered
.Lenter:
           mvc      0x200(64),.Liplparms-0b(12) # Restore IPL parameters

    # Enter architecture mode required by bootstrapped program
           cli      .Lreqarch-0b(12),0x64    # Is z/Architecture required?
           bne      .Lenter32-0b(12)         # ..No, enter ELF in ESA/390 mode        
           zarch     10,13,error=.Lexitarch  # ..Yes, enter z/Architecture
    # Now in z/Architetecture mode
           sam64                             # Set address mode to 64

           enterz   .Lelfmagic,.Ls390elf,.Ls370elf,2,4,.Lexitpgm

.Lenter32: 
    # Pass control to bootstrapped program in ESA/390 mode
           sam31                             # Set amode to 31

           enter    .Lelfmagic,.Ls390elf,.Ls370elf,2,4,.Lexitpgm

.Lread: # Perform subchannel I/O to tape device
           iosch    .Lorb,.Lirb,0xBF,0x01,.Lexitio,14,3
    # Ignore IL channel indication
    # Detect end-of-program by unit exception (a tape mark)
    # Fall through when end-of-program detected

           b        .Lenter-0b(12)          # Now enter program

           .align  4

.Lbaseadj: .long   1b-0b                    # Adjustment to base
.Lctlr6:   .long   0xFF000000               # CR 6 - I/O Int Sub Class Mask
.Lelfmagic:.byte   0x7F                     # ELF...
           .ascii  "ELF"                    # ...magic
.Ls370elf: .hword  9                        # s370 ELF machine type
.Ls390elf: .hword  22                       # s390 ELF machine type

 #
 # Self Modifying CCW1 Channel Program
 #
            .align  8
.Lccwpgm0:  .byte   0x02                    # Read command
            .byte   0xA0                    # Flags - CC+SLI
            .hword  4                       # Size of direct address field
            .long   .Lccwpgm1+4             # Overlay in next CCW
.Lccwpgm1:  .byte   0x02                    # Read command
            .byte   0x20                    # Flags - SLI
            .hword  .Lrecsize-4             # Size of direct record content
            .long   0                       # Address overwritten by previous CCW

 #
 #  Standard Loader Disabled Wait States
 #
            exits

 #
 #  Command Mode Operation Request Block
 #
           .align   4   # ORB must be on a word boundary
.Lorb:
.Lorbintp: .long   0xAAAAAAAA               # Word 0: Interrupt parameter
.Lorbflg0: .byte   0                        # Flags
.Lorbflg1: .byte   0x80                     # Using Format-1 CCW's
.Lorbflg2: .byte   0xFF                     # ... Logical path mask X'FF'
.Lorbflg3: .byte   0
.Lorbcpa:  .long   .Lccwpgm0                # Word 2: Address of channel program
           .long   0                        # Word 3
           .quad   0                        # Words 4, 5
           .quad   0                        # Words 6, 7
 #
 # From this point forward, uninitialized storage is used
 #
.Liplparms  =      .                        # IPL parameter save area 

.Lirb       =      .+64
.Lirbword1  =      .Lirb                    # SCSW Word 0
.Lirbddwad  =      .Lirb+4                  # SCSW Word 1 - CCW Address
.Lirbdstat  =      .Lirb+8                  # SCSW Word 2 - Device Status
.Lirbsstat  =      .Lirb+9                  # SCSW Word 2 - Subchannel Status
.Lirbcount  =      .Lirb+10                 # SCSW Word 2 - Residual count
.Lirbesw    =      .Lirb+12                 # ESW
.Lirbecs    =      .Lirb+32                 # ECW 

.endif # .ifndef .Ltapembed_S scope
