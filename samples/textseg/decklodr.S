            .title "Object Deck Boot Loader Sample"
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
 
 # This source module is the basis for an IPL ELF based boot loader for object 
 # modules in which an ELF has been embedded within the 80-byte object module 
 # format.  It allows multiple modules to be loaded and upon completion of the
 # load process enters the first object module encountered with a START control
 # section to be entered.  The addressing mode of this object module and architecture
 # for which the boot loader is targeted will determine how this ELF is entered.
 #
 # The use of the object module format restricts the ELF's embedded within the 
 # object module to be loaded within the first 16-megabytes of real storage.  The
 # addressing field of the object module are restricted to 24-bits.  This boot
 # loader assumes the object module was built using the exeinobj.py tool in the
 # tools/ipl directory.
 #
 # Unlike most of the samples, this sample is loaded at absolute storage address
 # 0x300, the location used by embedded or external boot loaders.

            .eject
            .sbttl "Macros and Structures"

            .include "psw.S"         # src/     PSW macros, .L__psw_arch, zarch macro
            
            .include "IPLELF.S"      # src/ipl/ IPL ELF macros and assigned storage
            
            .include "loaderif.S"    # src/ipl/ Standard loader exit wait states
            
            .include "OBJ.S"         # src      Object Deck record structures

    .ifle .L__psw_arch-1             # If Channel I/O architecture
            .include "iortn370.S"
    .else  # .ifle .L__psw_arch-1    # If Channel subsystem I/O architecture
            .include "iortn.S"
    .endif # .ifle .L__psw_arch-1

            .eject
            .sbttl "IPL Program"
            
 # IPL Segment for TXT0 storage area placement of TEXT segment
    .ifeq .L__psw_arch-3
            iplelf_ipl text=yes,area=txt1  # Used txt1 for z/Architecture
            psw_arch 390                   # IPL PSW is an ESA/390 PSW
            psw    s=0,p=0,a=_start        # Generate the IPL PSW
    .else
            iplelf_ipl text=yes,area=txt0  # Used txt0 in not z/Architecture
            psw    s=0,p=0,a=_start        # Generate the IPL PSW for architecture
    .endif # .ifeq .L__psw_arch-3

 # TEXT Segment (.text section)
            
            .text

 # Beginning of object deck card loader program
 # Entry is in 24-bit addressing mode

 # Register Usage:
 #  R0     On a disabled wait, it reflects 4 bytes beyond where the error occurred
 #  R1     Subchannel ID number (R1 required by I/O instructions)
 #  R2     not used
 #  R3     not used
 #  R4     ELF entry point address
 #  R5     Work register
 #  R6     not used
 #  R7     not used
 #  R8     not used
 #  R9     not used
 #  R10    SIGNAL PROCESSOR status register
 #  R11    SIGNAL PROCESSOR parameter register
 #  R12    SIGNAL PROCESSOR address of CPU being signaled
 #  R13    Base register
 #  R14    Subroutine return address
 #  R15    not used
 
 # On entry to ELF:
 #  R0     Address of the loadpoint of the START module (either ELF or TEXT segment)
 #  R1     Address of the entry point.
 
 # On disabled wait state:
 #  R0     Address of the detected failure + 4
 
_start:    .global _start                    # Tell linker where to enter me
           stm      0,15,0x200               # Save IPL parms
           basr     13,0                     # Setup the base register
0:                                           # Tell the assembler
    .ifeq .L__psw_arch       # If S/370 BC-mode
           lh       1,0x2(0)                 # Load the IPL device into R1
    .endif # ifeq .L__psw_arch

           trap64   .Ltrap64                 # Set-up 64-bit interrupt trap PSW's

    .ifdef __s390x__
           trap128  .Ltrap128                # Set-up 128-bit interrupt trap PSW's
    .endif # .ifeq .ifdef __s390x__
  
           # Set up I/O registers
    .ifeq .L__psw_arch-1    # If S/370 EC-Mode
           lh       1,.LIO_dev(0)            # Load the IPL device into R1
    .endif # .ifeq .L__psw__arch
    .ifle .L__psw_arch-1    # If S/370 either mode
           lctl     2,2,.Lctlr2-0b(13)       # Set channel interrupt masks
    .endif # .L__psw_arch-1
    .ifge .L__psw_arch-2    # If ESA/390 or z/Architecture
           l        1,.LIO_ssid              # Load SID word R1 from 0xB8
           lctl     6,6,.Lctlr6-0b(13)       # Load Control Register 6
    .endif
           
           # Set up program register
         
           sr       2,2                      # Make sure data location is zero
.Lloop:
           bas      14,.Lread-0b(13)         # Read Card
   # Process individual cards from the object modules in the deck
       # Test for ESD record
           cli      .Lioarea+.LOBJ_id-0b(13),.LOBJ_esd_id
           bne      .Ltxt-0b(13)             # Not ESD, maybe TXT
       # Process ESD record
           tm       .Ldckstatus-0b(13),.Lstartfnd  # Did we find the START module?
           bo       .Lloop-0b(13)            # Yes, can ignore additional ESD recs
       # Look for START SD in an ESD item
           # If ESD record has blanks in first ESD id field, there are no SD's
           clc      .Lioarea+.LOBJ_esdid-0b(2,13),.Lblnkesd-0b(13)
           be       .Lloop-0b(13)            # Yes, blanks, so ignore this record
           #Any data in the ESD? (just in case)
           cli      .Lioarea+.LOBJ_dlen+1-0b(13),0 
           bnh      .Lloop-0b(13)            # ..No, so ignore this record
           # Setup for loop to look at ESD item's in the record
           la       4,.LESD_len(0)           # Set ESD item length
           la       5,.Lioarea+.LOBJ_data-0b(13)   # Point to first ESD item

.LisSD:    # Check for an SD ESD item
           cli      .LESD_type(5),.LESD_SD   # Is this a fullword aligned SD?
           be       .LfoundSD-0b(13)         # ..Yes, found an SD
           cli      .LESD_type(5),.LESD_SD8  # Is this a quad word aligned SD?
           bne      .LnextESD-0b(13)         # ..No, check next ESD item
           
.LfoundSD: # Found an SD item
           clc      .LESD_symbol(8,5),.Lstartnam-0b(13)  # Is it 'START'???
           bne      .LnextESD-0b(13)         # ..No, next to check next ESD item
           # Eureka! Found it!  This is the module we are going to enter.
           mvc      .Lstartatr-0b(1,13),.LESD_attr(5)  # Save the SD attribute byte
           # Indicate we have r and a modes and START was found
           oi       .Ldckstatus-0b(13),.Lstartmod+.Lstartfnd
           b        .Lloop-0b(13)            # Continue processing deck records

.LnextESD: # Try next ESD in the record
           ch       4,.Lioarea+.LOBJ_len-0b(13)   # More data in ESD record?
           bnh      .Lloop-0b(13)            # ..No, try next ESD record
           la       4,.LESD_len(4)           # Calculate data length 
           la       5,.LESD_len(5)           # Point to next ESD item in record
           b        .LisSD-0b(13)            # Check out the next ESD item
           
.Ltxt:
       # Test for TXT record
           cli      .Lioarea+.LOBJ_id-0b(13),.LOBJ_txt_id
           bne      .Lend-0b(13)             # Not TXT, maybe END

       # Process TXT record
           sr       5,5                      # Clear pointer
           lr       6,5                      # Clear end of TXT data address
           icm      5,0b0111,.Lioarea+.LOBJ_addr-0b(13)  # Point to TXT destination
           lh       4,.Lioarea+.LOBJ_len-0b(13)          # Get TXT length
           # First TXT record of START module?
           tm       .Ldckstatus-0b(13),.Lstartfnd+.Lstarttxt
           bnm      .Lmovetxt-0b(13)                     # ..No, just move TXT data
           st       5,.Lelfstart-0b(13)                  # Save START load point
           oi       .Ldckstatus-0b(13),.Lstarttxt         # Remember we have it

.Lmovetxt: # Try to move TXT into real storage
           cl       5,.Lmyend-0b(13)        # Is TXT start below my end?
           bnl      .Lmove-0b(13)           # ..No, safe to load
           la       6,0(4,5)                # R6 points to end of loaded TXT+1
           cl       6,.Lmystart-0b(13)      # Is end before my start?
           bl       .Lmove-0b(13)           # ..Yes, also safe to load
           bas      0,.Loverlay-0b(13)      # ..No, overlaying myself, DIE on this

.Lmove:    # Actually move the TXT!
           bctr     4,0                     # R4 decremented for MVC execute
           ex       4,.Lmvc-0b(13)          # Move the TXT data
           b        .Lloop-0b(13)           # Work on next deck record

.Lend:     
       # Test for END record
           cli      .Lioarea+.LOBJ_id-0b(13),.LOBJ_end_id
           bne      .Lloop-0b(13)            # Not END, ignore this record

       # Process END record
           tm       .Ldckstatus-0b(13),.Lstartfnd+.Lstartend
           bnm      .Lloop-0b(13)            # Only interested if START END not found
           # Save START entry address 
           mvc      .Lstrtnter+1-0b(3,13),.Lioarea+.LOBJ_addr-0b(13)
           # Indicate START module done
           oi       .Ldckstatus-0b(13),.Lstartntr+.Lstartend
           b        .Lloop-0b(13)            # Process next record

 # Enter program - Read subroutine passes control here when EOF encountered
.Lenter:
           tm       .Ldckstatus-0b(13),.Lstartntr  # Did we find a START module?
           bo       .+8-0b(13)               # ..Yes, enter modules SD START section
           bas      0,.Lexitpgm-0b(13)       # ..No, die, could not enter program
           
           lm       0,1,.Lelfstart-0b(13)    # Set ELF start and entry address
           
      .ifge .L__psw_arch-2            # If supporting ESA/390 and z/Architecture
           tm       .Ldckstatus-0b(13),.Lstartmod   # Is mode info valid?
           bno      .Lgotoelf-0b(13)  # ..No, enter in current address mode
      .endif # .ifge .L__psw_arch-2 

      .ifdef __s390x__            # Supporting z/Architecture
    # Enter architecture mode required by bootstrapped program
           tm       .Lstartatr-0b(13),.LESD_SD_rmode64    # Is residency mode 64-bit?
           bno      .Lenter32-0b(13)         # ..No, do not need to enter z      
           zarch    10,12,error=.Lexitarch   # ..Yes, enter z/Architecture
    # Now in z/Architetecture mode
           tm       .Lstartatr-0b(13),.LESD_SD_amode64    # Is amode 64-bit?
           bno      .Lenter32-0b(13)         # ..No, 
           sam64                             # Set address mode to 64
    # Warning: R13 will have the high-order bit set because ESA/390 mode 
    # will use 31-bit addressing.  Do not reference R13 past this point
    # without clearing bit 32 of the 64-bit register.
    # Because we are entering the loaded ELF with R1 we have not bothered
    # to clear bit 32.
           br       1                        # Enter loaded ELF with 64-bit addr.
.Lenter32:
      .endif # .ifdef __s390x__   
      .ifge .L__psw_arch-2
           tm       .Lstartatr-0b(13),.LESD_SD_amode31
           bno      .Lenter24-0b(13)         # Not amode=31 so set amode=24
           sam31                             # Set address mode to 31
           br       1                        # Enter loaded ELF with 31-bit addr.
.Lenter24:
           sam24                             # Set address mode to 24
    .endif # .ifge .L__psw_arch-2
.Lgotoelf:
           br       1                        # Enter loaded ELF with 24 bit addr.

 # Read card subroutine
.Lread:
    .ifle .L__psw_arch-1
 # iochan devr:req ccws:req iostatus:req error:req cerr derr sense er=0 br=13 b=0b
           iochan   1,.Lccws,.Liostatus,.Lexitio,cerr=0xBF,derr=0x02,er=0
           peof370  .Lenter,.Liostatus
    .else
 # iosch orb:req irb:req iostatus:req error:req cerr derr sense er=0 br=13 b=0b
           iosch    .Lorb,.Lirb,.Liostatus,.Lexitio,cerr=0xBF,derr=0x02,er=0
           peof     .Lenter,.Liostatus
    .endif
           br       14                      # Continue processing object deck

           .align  4
    .ifle .L__psw_arch-1     # If S/370
.Lctlr2:   .long   0xFFFFFFFF               # CR 2 - I/O Channel Interrupt Mask
    .else                    # If ESA/390 or z/Architecture
.Lctlr6:   .long   0xFF000000               # CR 6 - I/O Int Sub Class Mask
.Liostatus:.long   0                        # Accumulates I/O status
    .endif # .ifle .L__psw_arch-1
.Lccws:    .long   .Lccwpgm0                # Address of CCW channel program
.Lmystart: .long   _start                   # My starting address
.Lmyend:   .long   .Llodr_end               # My ending address+1

     .ifle .L__psw_arch-1   # If S/370 I/O
.Liostatus:.hword 0                         # Accumulates I/O status
     .endif # .ifle .L__psw_arch-1
     
     # Accumulates status of the deck
     
.Lelfstart: .long 0                         # Address Where START ELF loaded
.Lstrtnter: .long 0                         # Locations where START is entered
.Lmvc:      mvc   0(1,5),.Lioarea+.LOBJ_data-0b(13)  # Move TXT data to storage
.Ldckstatus:.byte 0                         # status of the deck 
.Lstartfnd  =     0x80                      # Object deck START module found
.Lstartend  =     0x40                      # START module completed
.Lstarttxt  =     0x20                      # START load point found
.Lstartntr  =     0x10                      # .Lstrtnter value is valid
.Lstartmod  =     0x08                      # .Lstrtamd  value is valid
.Lstartatr: .byte 0                         # Desired address mode of START module
.Lblnkesd:  .ascii "\x40\x40"               # Used to determine if ESD can have SD's
.Lstartnam: .ascii "\xE2\xE3\xC1\xD9\xE3\x40\x40\x40"  # 'STARTbbb" in EBCDIC
       
 #
 # Channel Program to read a single card from the deck into .Lioarea
 #
            .align  8
    .ifle .L__psw_arch-1    # If S/370 I/O use CCW0 format
.Lccwpgm0:  ccw0    cmd=0x02,addr=.Lioarea,flags=0x00,cnt=80            
    .else                   # Subchannel I/O use CCW1 format
.Lccwpgm0:  ccw1    cmd=0x02,addr=.Lioarea,flags=0x00,cnt=80
    .endif

 #
 #  Standard Loader Disabled Wait States
 #
.Loverlay:  lpsw    .Lpswffb-0b(13)
            exits   br=13
.Lpswffb:   psw     s=0002,a=0xFFB
 #
 #  Interrupt Trap PSW's
 #
.Ltrap64:
           traps64
    .ifdef __s390x__         # If supporting z/Architecture
.Ltrap128:
           traps128
    .endif # ifdef __s390x__
 
    .ifge .L__psw_arch-2
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
    .endif
 #
 # From this point forward, uninitialized storage is used
 #
.Lioarea    =      .                        # Card input I/O area

    .ifge .L__psw_arch-2
.Lirb       =      .Lioarea+80
.Lirbword1  =      .Lirb+0                  # SCSW Word 0
.Lirbddwad  =      .Lirb+4                  # SCSW Word 1 - CCW Address
.Lirbdstat  =      .Lirb+8                  # SCSW Word 2 - Device Status
.Lirbsstat  =      .Lirb+9                  # SCSW Word 2 - Subchannel Status
.Lirbcount  =      .Lirb+10                 # SCSW Word 2 - Residual count
.Lirbesw    =      .Lirb+12                 # ESW
.Lirbecw    =      .Lirb+32                 # ECW
.Llodr_end  =      .Lirb+.LIRB_len
    .else
.Llodr_end  =      .Lioarea+80              # End of S/370 lodr program
    .endif   
            .end
