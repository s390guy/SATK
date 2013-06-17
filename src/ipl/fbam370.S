.ifndef .Lfbam370_S
.Lfbam370_S=1
 # Copyright (C) 2012,2013 Harold Grovesteen
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

           .eject
           .sbttl "FBA DASD Embedded Loader"

 # Fixed-Block-Architecture (FBA) Direct-Access-Storage Device (DASD) Embedded Loader
 # for S/370 channel-based I/O operations

 # LOADER Segment
 #         .section .loader,"a",@progbits

 # Beginning of S/370 FBA DASD bootstrap loader program
 # Entry is in: 
 #     24-bit addressing mode
 #     BC-mode if iplmpp.py argument --bcmode is specified when creating the FBA disk
 #     EC-mode if iplmpp.py argumnet --bcmode is not specified when creating the FBA 
 #             disk

 # Register Usage:
 #  R0     Size of program content to move from program block
 #  R1     Subchannel ID number (R1 required by I/O instructions)
 #  R2     ELF header address
 #  R3     available
 #  R4     ELF entry point address
 #  R5     Work register
 #  R6     Sectors read for each block
 #  R7     Sector number of next sector to read
 #  R8     Move block - source address, the program block
 #  R9     Move block - source size, program block data length
 #  R10    Move block - receiving address, location in the directed block header
 #         or SIGNAL PROCESSOR status register
 #  R11    Move block - receiving size, program block data length
 #         or SIGNAL PROCESSOR parameter register
 #  R12    Base register
 #  R13    Read subroutine address
 #         or SIGNAL PROCESSOR address of CPU being signaled
 #  R14    Subroutine return address
 #  R15    On a disabled wait, it contains the address where the error occurred
 
           .sbttl "FBA DASD Embedded Loader - Macros"
           .eject

           .include "loaderif.S"    # src/ipl/ - IPL ELF ABI LOADER segment support

           .include "bootnter.S"    # src/ipl/ - ELF entry support macros

           .include "iortn370.S"    # src/ - Macros for S/370 I/O operations

           .sbttl "FBA DASD Embedded Loader - Boot Program"
           .eject
 # LOADER Segment

           loaderif 512,'D,'N,'H,'Y,'Y,0x24,0x80,.Lbaseadj
    # D = IPL program supported with directed block format
    # N = LOWC segment not supported (medium preparation process handles)
    # H = Directed block format header indicates end-of-program
    # Y = Blocks must be padded to full size of the block
    # Y = Medium preparation process provides its data
    # 0x24 = FBA, Channel I/O
    # 0x80 = System/370

           mvc      .Liplparms-0b(64,12),0x200  # Save the IPL parms for restore

           # Set up I/O registers
    .ifeq .L__psw_arch           # S/370 BC-mode
           lh       1,0x2(0)                 # Load the IPL device into R1
    .else  # .ifeq .L__psw__arch # S/370 EC-mode or ESA/390
           lh       1,.LIO_dev(0)            # Load the IPL device into R1
    .endif # .ifeq .L__psw__arch 
           lctl     2,2,.Lctlr2-0b(12)       # Set channel interrupt masks

           # Set up FBA CCW's for reading a block
           # The loaded block is treated as an extent.  Each read adjusts
           # the start of the extent to the next sector
           sr       6,6                      # Make SURE R6 is zero
           icm      6,3,.Lreadsiz-0b(12)     # Load the blksize
           lr       0,6                      # This is the size of the block
           sh       0,.Ldirhdr-0b(12)        # Set the size of the data to move
           srl      6,9                      # Sectors read per block
           sth      6,.Lsectors-0b(12)       # Set in LOCATE for block
           lr       5,6                      # Move # of sectors to work reg.
           bctr     5,0                      # Calculate last sector rel. to block
           st       5,.Ldsend-0b(12)         # Set up DEFINE EXTENT for block

           # Set up program register
           l        7,.Lpgmsec-0b(12)        # Determine initial program sector
           la       13,.Lread-0b(12)         # Set the read block subroutine

           basr     14,13                    # Read First FBA program block
           l        2,.Lblock-0b(12)         # Fetch start of program
           b        .Lmove-0b(12)            # Move it into storage
.Lloop:
           tm       .Lblock-0b(12),0x80      # If this the last block?
           bo       .Lenter-0b(12)           # ..yes, enter the program
           la       3,10                     # Max 10 tries to test subchannel
           basr     14,13                    # Read FBA sector
.Lmove:    
           la      8,.Lblock+4-0b(12)        # Program block source address
           lr      9,0                       # size of data being moved
           l       10,.Lblock-0b(12)         # Destination for program data
           lr      11,9                      # Receiving same as sending
           mvcl    10,8                      # Move the program block
           ah      7,.Lsectors-0b(12)        # Increment to next sector number
           b       .Lloop-0b(12)             # Process next program block

 # Enter program - Read subroutine passes control here when EOF encountered
.Lenter:
           mvc      0x200(64),.Liplparms-0b(12) # Restore IPL parameters

    # Pass control to bootstrapped program in ESA/390 mode  

           enter    2,4,.Lexitpgm

 # Read FBA sector subroutine (return via R14)
.Lread:    
           # Define the extent to start with the first sector to read
           st       7,.Lfirstsec-0b(12) 

           iochan   1,.Lccws,.Liostatus,.Lexitio,cerr=0x03,derr=0x02,br=12
           br       14                      # Return after good I/O

           .align  4
.Lbaseadj: .long   .Llodrtemp-.Llodr        # Adjustment to base
.Lctlr2:   .long   0xFFFFFFFF               # CR 2 - I/O Channel interrupt Mask
.Lccws:    .long   .Lccwpgm0                # Address of CCW's
.Lone:     .long   1                        # Constant of one
.Ldirhdr:  .hword  4                        # Size of directed block header
.Liostatus:.hword  0                        # I/O status area for iochan macro

 #
 # CCW0 Channel Program
 #
 #     program define extent parameters
 #     program block locate parameters
 # +0  DEFINE EXTENT CCW for the program block
 # +8  LOCATE CCW for program block
 # +16 READ CCW for program block
            .align  8
.Lextent:   .byte   0x40,0,0,0              # File mask: inhibit all writes
.Lfirstsec: .long   0                       # First sector to be read
.Ldsstart:  .long   0                       # Extent starts with 0 and
.Ldsend:    .long   0                       # ...ends with number of sectors-1
.Lextlen    =       .-.Lextent              # Size of extent data

.Llocate:   .byte   0x06                    # Read sector operation
            .byte   0                       # Replication count ignored for read
.Lsectors:  .hword  0                       # Number of sectors to read
            .long   0                       # First sector always 0 (rel to extent)
.Lloclen    =       .-.Llocate              # Size of the locate data

.Lccwpgm0:  .byte   0x63,0                  # DEFINE EXTENT command
            .hword  .Lextent                # Location of the EXTENT data
            .byte   0x40,0                  # Flags - CC
            .hword  .Lextlen                # Size of the EXTENT data

.Lccwpgm1:  .byte   0x43,0                  # LOCATE command
            .hword  .Llocate                # Location of the LOCATE data
            .byte   0x40,0                  # Flags - CC
            .hword  .Lloclen                # Size of the LOCATE data

.Lccwpgm2:  .byte   0x42,0                  # READ command
            .hword  .Lblock                 # Address where the block is being read
            .byte   0x00,0                  # Flags - none
.Lblklen:   .hword  .Lrecsize               # Size of the program block

 #
 #  Standard Loader Disabled Wait States
 #
            exits

 #
 # From this point forward, uninitialized storage is used
 #
.Liplparms  =      .                        # IPL parameter save area
.Lblock     =      .Liplparms+64            # FBA physical sector/block read here

.endif # .ifndef .Lfbam370_S scope
