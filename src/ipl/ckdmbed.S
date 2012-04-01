.ifndef .Lckdmbed_S
.Lckdmbed_S=1
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

 # Count-Key-Data DASD Device Embedded Loader

          .eject
          .sbttl "Embedded Loader"
 # Count-Key-Data (CKD) Direct-Access-Storage Device (DASD) Embedded Loader

 # LOADER Segment
 #         .section .loader,"a",@progbits

 # Beginning of CKD ESA/390 or z/Architecture bootstrap loader program
 # Entry is in 31-bit addressing mode

 # Register Usage:
 #  R0     Size of program content to move from program block
 #  R1     Subchannel ID number (R1 required by I/O instructions)
 #  R2     ELF header address
 #  R3     Available
 #  R4     ELF entry point address
 #  R5     Work register
 #  R6     Sectors read for each block
 #  R7     Sector number of next sector to read
 #  R8     Cylinder number of the next block to read
 #  R9     Head number of the next block to read
 #  R10    Record number of the next block to read
 #         or SIGNAL PROCESSOR status register
 #  R11    SIGNAL PROCESSOR parameter register
 #  R12    Base register
 #  R13    Read card subroutine address
 #         or SIGNAL PROCESSOR address of CPU being signaled
 #  R14    Subroutine return address
 #  R15    On a disabled wait, it reflects where the error occurred

           .sbttl "Embedded Loader - Macros"
           .eject
           .include "loaderif.S"

           .include "bootnter.S"

           .include "iortn.S"

           .sbttl "Embedded Loader - Boot Program"
           .eject
  # LOADER Segment

           loaderif  512,'D,'N,'P,'Y,'Y,0xC0,0x60,.Lbaseadj
    # D = IPL program supported with directed block format
    # N = LOWC segment not supported (medium preparation process handles)
    # P = Physical end-of-file indicator used
    # N = Blocks do not require padding to full block size
    # Y = Medium preparation process provides its data

           mvc      .Liplparms-0b(64,12),0x200  # Save the IPL parms for restore

           # Set up I/O registers
           l        1,.Lio_ssid              # Load LCSS ID of IPL device
           lctl     6,6,.Lctlr6-0b(12)       # Load Control Register 6

           # Set up CKD CCW's for reading a block
           # Move the SEEK and SEARCH ID EQUAL for the first IPL program block
           mvc      .Lblkcyl-0b(5,12),.Lpgmcyl-0b(12)

           # Set up Record ID data
           sr       8,8                      # Make SURE register
           lr       9,8                      # 8-10 are
           lr       10,8                     # zero
           lh       8,.Lpgmcyl-0b(12)        # Set cylinder number
           lh       9,.Lpgmtrk-0b(12)        # Set the track number
           ic       10,.Lpgmrec-0b(12)       # Set the record id

           # Set up program register
           la       13,.Lread-0b(12)         # Set the read block subroutine

           # Read the first directed block of IPL program
           basr     14,13                    # Read First CKD program block
           l        2,.Lccwpgma-0b(12)       # Fetch start of program
.Lloop:
           # Increment record ID
           la       10,1(,10)                # Increment the record count
           clm      10,1,.Lckdblks-0b(12)    # Did record exceed max/track?
           bnh      .Ldoread-0b(12)          # ..No, do the read
           la       10,1                     # ..Yes, reset record number to 1
           la       9,1(,9)                  # Add one to the track number
           clm      9,3,.Lckdmtrk-0b(12)     # Did we exceed max track number?
           ble      .Ldoread-0b(12)          # ..No, do the read
           sr       9,9                      # ..Yes, reset track number to zero
           la       8,1(,8)                  # Add one to the cylinder number
           clm      8,3,.Lckdmcyl-0b(12)     # Did we exceed the max cyl number?
           ble      .Ldoread-0b(12)          # ..No, do the read
           bas      15,.Lexit-0b(12)         # ..Yes, DIE
.Ldoread:
           basr     14,13                    # Read CKD block
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

    # Read CKD block subroutine - uses R8-R10 for cylinder, head, and record id
.Lread:    
           # Define the record ID of the first IPL program block to the channel
           sth      8,.Lblkcyl-0b(12)       # Set SEEK cylinder
           sth      9,.Lblktrk-0b(12)       # Set SEEK head
           stc      10,.Lblkrid-0b(12)      # Set the SEARCH ID EQUAL record id

           iosch    .Lorb,.Lirb,.Liostatus,.Lexitio,cerr=0xBF,er=15,br=12
           peof     Lenter,.Liostatus,br=12
           br       14                      # Not EOF, continue reading

           .align  4
.Lbaseadj: .long   1b-0b                    # Adjustment to base
.Lctlr6:   .long   0xFF000000               # CR 6 - I/O Int Sub Class Mask
.Lelfmagic:.byte   0x7F                     # ELF...
           .ascii  "ELF"                    # ...magic
.Liostatus .long   0                        # Accumulates I/O status
.Ls370elf: .hword  9                        # s370 ELF machine type
.Ls390elf: .hword  22                       # s390 ELF machine type
.Ldirhdr:  .hword  4                        # Size of directed block header

 #
 # Self Modifying CCW1 Channel Program
 #
 #     program SEEK and SEARCH ID EQUAL data
 #     program file mask data
 # +0  SET FILE MASK for the program block access
 # +8  SEEK to cylinder and head of program block
 # +16 SEARCH ID EQUAL of the program blocks record number
 # +24 TIC back to SEARCH ID EQUAL
 # +32 READ DATA from directed block, the address, into next CCW
 # +40 READ DATA of directed block into storage location

.Lblkbin:   .hword  0                       # SEEK bin, must be zeros

 # These fields starting here are adjusted during reading for each physical block
.Lblkcyl:   .hword  0                       # SEEK and SEARCH ID EQUAL cylinder
.Lblktrk:   .hword  0                       # SEEK and SEARCH ID EQUAL head
.Lseeklen   =       .-.Lblkbin              # Length of SEEK command data
.Lblkrid:   .byte   0                       # SEARCH ID EQUAL record id
.Lsrchlen   =       .-.Lblkcyl              # Length of SEARCH ID EQUAL data
 # These fields ending here are adjusted during reading for each physical block

 # File Mask
.Lblkfmsk:  .byte   0x40                    # allow all seeks and no writes

            .align  8  # CCW's must be on doubleword boundary

.Lccwpgm0:  .byte   0x1F                    # SET FILE MASK command
            .byte   0x40                    # Flags - CC
            .hword  1                       # Size of the file mask
            .long   .Lblkfmsk               # Location of the file mask

.Lccwpgm1:  .byte   0x07                    # SEEK command
            .byte   0x40                    # Flags - CC
            .hword  .Lseeklen               # Size of the SEEK data
            .long   .Lblkbin                # Location of the SEEK data

.Lccwpgm2:  .byte   0x31                    # SEARCH ID EQUAL command
            .byte   0x40                    # Flags - CC
            .hword  .Lsrchlen               # Size of the record ID data
            .long   .Lblkcyl                # Location of the record ID data

.Lccwpgm3:  .byte   0x08                    # TRANSFER IN CHANNEL command
            .byte   0x00                    # Flags - none
            .hword  0                       # No data associated with command
            .long   .Lccwpgm2               # Location of SEARCH ID EQUAL command

.Lccwpgm4:  .byte   0x06                    # READ DATA command
            .byte   0xA0                    # Flags - CC+SLI
            .hword  4                       # Size of direct address field
            .long   .Lccwpgm5+4             # Overlay in next CCW

.Lccwpgm5:  .byte   0x06                    # READ DATA command continued
            .byte   0x20                    # Flags - SLI
            .hword  .Lrecsize-4             # Size of directed block content
.Lccwpgma:  .long   0                       # Address overwritten by previous CCW

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

.endif # .ifndef .Lckdmbed_S
