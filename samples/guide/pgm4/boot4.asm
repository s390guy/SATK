* Copyright (C) 2020 Harold Grovesteen
*
* This file is part of SATK.
*
*     SATK is free software: you can redistribute it and/or modify
*     it under the terms of the GNU General Public License as published by
*     the Free Software Foundation, either version 3 of the License, or
*     (at your option) any later version.
*
*     SATK is distributed in the hope that it will be useful,
*     but WITHOUT ANY WARRANTY; without even the implied warranty of
*     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*     GNU General Public License for more details.
*
*     You should have received a copy of the GNU General Public License
*     along with SATK.  If not, see <http://www.gnu.org/licenses/>.
*
         TITLE 'BOOT4 - S/370 FBA Boot Loader'
* Program Description:
*
* BOOT4 is a FBA boot loader program.  It requires input/output commands to
* the IPL device to load the booted program.  This boot loader is executed by
* means of an IPL from a FBA DASD volume.  Control is passed to the booted
* program by means of a branch instruction.
*
* Target Architecture: S/370
* 
* Devices Used:
*   110 - FBA IPL volume containing the booted program
*
* Program Register Usage:
*
*   R0   Base register for access to the ASA.  Required by DSECT usage
*        This is purely an assembler artifact.  R0 available for other uses
*   R1   Device Channel and Unit Addresses for I/O instructions
*   R2   Cumulative size of loaded program
*   R3   Boot loader high water mark (can not write below it)
*   R4   FBA I/O Area address (where a directed record is read)
*   R5   Number of FBA sectors read for each directed record
*   R6   Work register
*   R8   Source address of directed record's content    ---+
*   R9   Length of a directed record's program content     |-- MVCL
*   R10  Destination address of directed record's content  |
*   R11  Length of a directed record's program content  ---+
*   R12  The program base register
*   R13  available
*   R14  available
*   R15  Booted program's entry address
*
* Disabled Wait State PSW's address field values used by the program:
*    X'000000' - Successful execution of the program
*    X'000008' - Unexpected Restart interruption occurred. Old Restart PSW at
*                address X'8'
*    X'000018' - rUnexpected External interruption occurred.  Old External PSW at
*                address X'18'
*    X'000020' - Unexpected Supervisor interruption occurred.  Old Supervisor
*                PSW at address X'20'
*    X'000028' - Unexpected Program interruption occurred. Old Program PSW at
*                address X'28'
*    X'000030' - Unexpected Machine Check interruption occurred.  Old Machine
*                Check PSW at address X'30'
*    X'000038' - Unexpected Input/Output interruption occurred.  Old
*                Input/Output PSW at address X'38'
*    X'040004' - IPL Device X'110' or channel not operational
*    X'040008' - IPL Device X'110' or channel busy
*    X'04000C' - IPL Device X'110' or channel had a problem. See CSW.
*    X'040010' - Unexpected interruption from some other device. See ASA X'BA'
*    X'040014' - IPL device channel error occurred
*    X'040018' - IPL device did not complete the I/O without a problem
*    X'04001C' - Directed record overwriting boot loader
*    X'040020' - Destructive overlap detected by MVCL while loading record
*    X'040024' - Cumulative booted program sizes do not match in LOD1
*    X'040028' - Can not change addressing mode for booted program
         EJECT
* See all object data and macro generated model statements in the listing
         PRINT DATA,GEN
* Uncomment the next statement if you do not want the ASA DSECT in the listing         
*        PRINT OFF
         SPACE 1
*
* Hardware and Software Assigned Storage Locations
*
         SPACE 1
* This DSECT allows symbolic access to these locations.  The DSECT created is 
* named ASA.
ASA      ASAREA DSECT=YES
         LOD1  ASA=ASA
         EJECT
* Uncomment this statement if you have disabled printing of the ASA
*        PRINT ON,GEN
* Inform the SATK macros of the architecture being targeted.  Inferred from
* the ASMA -t command-line argument.
         ARCHLVL
* Ensure interrupt traps are loaded by iplasma.py before program execution
* begins.  This macro will create the memory region that will also contain
* the IPL PSW.  The region name defaults to ASAREGN.  iplasma.py knows how
* to deal with this situation.
ASASECT  ASALOAD
         ASAIPL IA=PGMSTART    Define the bare-metal program's IPL PSW
         SPACE 2
*
*  Commonly used FBA Values
* 
         SPACE 1
* CCW Commands
NOP      EQU   X'03'     No operation CCW Command
DEFN_EXT EQU   X'63'     Define Extent CCW Command
LOC_DATA EQU   X'43'     Locate CCW Command (within a defined extent)
READ     EQU   X'42'     Read located data CCW Command

* CCW Flags
CC       EQU   X'40'     CCW Command chaining
         
*
* FBA Boot Loader Program
*
         SPACE 1
PGMSECT  START X'400',BOOT4    Start a second region for the loader itself
* This results in BOOT4.bin being created in the list directed IPL directory
         USING ASA,0           Give me instruction access to the ASA and LOD1
PGMSTART STM   0,15,LODPARMS   Preserve Hercules IPL parameters, if any.
* This must happen before any register is altered!
         BALR  12,0            Establish my base register
         USING *,12            Tell the assembler
         SPACE 1
* Ensure program is not re-entered by a Hercules console initiated restart.
* Address 0 changed from its absolute storage role (IPL PSW) to its real
* storage role (Restart New PSW) after the IPL.
* Change from the IPL PSW at address 0 to a Restart New PSW trap
         MVC   RSTNPSW,PGMRS
         SPACE 1
* Prepare for use of the IPL device by the boot loader
         MVC   IPLDEV,IOICODE    Save the address of the IPL device
         LCTL  2,2,CR2     Enable only channel 1 for I/O interruptions
* The IPL device must be available for use because we successfully got here.
         SPACE 1
* Initialize the static portions of the I/O related data
         SR    2,2          Clear cumulative size of loaded program to zero
         LR    9,2          Clear size of data being moved from record
         SR    6,2          Clear work register
         ICM   6,B'0011',LOD1MDLN   Fetch from LOD1 the maximum directed length
         STH   6,FBACCW3+6  CCW - Will always read the same number of bytes
         SRL   6,9(0)             Convert bytes into sectors.
         STH   6,LOCSECS    LOC - Will always read the same number of sectors
         LR    5,6                Save the number of sectors (updates extent)
         BCTR  6,0                And the logical end of the extent is constant
         ST    6,ENDLSEC    EXT - Set it in the FBA extent data
* R6 is now available for other uses
         L     4,LOD1IOA          Remeber where to find a directed record
         STCM  4,B'0111',FBACCW3+1   CCW - Where the loader read's its data
         MVC   FRSTPSEC,LOD1FSEC     EXT - Set starting sector of first record
* Initialize the static portions of record loading
         LA    8,6(4)       Locate start of directed record's content
         LA    3,HWM        Directed records may not overwrite me!
         SPACE 1
* Prepare for I/O with the IPL device
         MVC   CAW(8),CCWADDR    Identify in ASA where first CCW resides
         LH    1,IPLDEV          R1 contains the IPL device CUU address
         SPACE 1
* Read a directed record from the IPL device
READLOOP DS    0H
         MVC   STATUS,STATCLR    Clear accumulated status
         SIO   0(1)     Request IPL device channel program to start, did it?
         BC    B'0100',DEVNOAVL  ..No, CC=1 don't know why, but tell someone.
         BC    B'0010',DEVBUSY   ..No, CC=2 console device or channel is busy
         BC    B'0001',DEVCSW    ..No, CC=3 CSW stored in ASA at X'40' 
* IPL device is now sending to the CPU a directed record (CC=0)
         SPACE 1
* Wait for an I/O interruption
DOWAIT   MVC   IONPSW(8),CONT  Set up continuation PSW for after I/O interrupt
         LPSW  WAIT       Wait for I/O interruption and CSW from channel
IODONE   EQU   *          The bare-metal program continues here after I/O
         MVC   IONPSW(8),IOTRAP     Restore I/O trap PSW
         SPACE 1
* I/O results can now be checked.
*   Did the interruption come from the console device?
         CH    1,IPLDEV            Is the interrupt from the IPL device?
         BNE   DEVUNKN             ..No, end program with an error
*   Yes, check the CSW conditions to determine if the I/O worked
         OC    STATUS,CSW+4        Accummulate Device and Channel status
         CLI   STATUS+1,X'00'      Did the channel have, a problem?
         BNE   CHNLERR             ..Yes, end with a channel error
         TM    STATUS,X'F3'        Did the unit encounnter a problem?
         BNZ   UNITERR             ..No, end with a unit error
         TM    STATUS,X'0C'        Did both channel and unit end?
         BNO   DOWAIT              Wait again for both to be done
* Both channel and unit have ended
         SPACE 1
* Move the directed record to its residence address
         L     10,0(4)           Destination address of record's content
         CLR   3,10              Will data from record overwrite boot loader?
         BH    OVRWRITE          ..Yes, HWM higher than load address, quit now!
         ICM   9,B'0011',4(4)    Size of record being loaded
         LR    11,9              Same size to the receiving location
         LR    6,9               Increment for cumulative program loaded
         MVCL  10,8              Move directed record
         BC    B'0001',DESTRT    Destructive overlap detected (CC=3), quit
         AL    6,LOD1BPLD        Increment loaded program size
         ST    6,LOD1BPLD        Update the cumulative program size in LOD1
         SPACE 1
* Determine if last record has been loaded
         TM    0(4),X'80'        Bit 0 of destination address one?
         BO    CKSIZE            ..Yes, check if correct amount loaded
         LR    6,5               Fetch the number of sectors read
         AL    6,FRSTPSEC        Update starting sector for the next extent
         ST    6,FRSTPSEC  EXT - Update the FBA extent with new starting sector
         B     READLOOP          Read the next record.
         SPACE 1
* Total bytes loaded should match what LOD1 says is the booted program size
CKSIZE   CLC   LOD1BPLN,LOD1BPLD  Do the cumulative sizes match in LOD1
         BNE   CUMERROR           ..No, something went wrong, quit
         SPACE 2
* Enter the boot loaded program...
         TM    LOD1ENTR,X'80'     Is 31-bit addressing set in address?
         BO    AMERROR            ..Yes, can not do that, so quit
         TM    LOD1ENTR,X'01'     Is 64-bit addressing set in address?
         BO    AMERROR            ..Yes, can not do that either, quit
         L     15,LOD1ENTR        Fetch entry point for booted program from LOD1
         BR    15                 Enter the booted program
         SPACE 2
* End the bare-metal program with an error indicated in PSW
DEVNOAVL LPSW  NODEV     Code 004 End console device is not available
DEVBUSY  LPSW  BUSYDEV   Code 008 End because device is busy (no wait)
DEVCSW   LPSW  CSWSTR    Code 00C End because CSW stored in ASA
DEVUNKN  LPSW  NOTCON    Code 010 End unexpected device caused I/O interruption
CHNLERR  LPSW  CHERROR   Code 014 End because console channel error occurred
UNITERR  LPSW  DVERROR   Code 018 End because console device error occurred
OVRWRITE LPSW  OVERWRIT  Code 01C Overwriting boot loader
DESTRT   LPSW  DESTOVLP  Code 020 Destructive overlap detected by MVCL
CUMERROR LPSW  BADSIZE   Code 024 Cumulative booted program sizes do no match
AMERROR  LPSW  NOAMCHNG  Code 028 Can not change addressing mode for booted pgm
         SPACE 1
* General Constants:
ONE      DC    F'1'      The constant 'one'.
         SPACE 1
* Control Register 2 - Enables channels for interruptions
CR2      DC    XL4'40000000'  Enable channel 1 where IPL device is connected
         SPACE 1
* I/O related information
CCWADDR  DC    A(FBACCW1)  Address of first CCW to be executed by IPL device.
IPLDEV   DC    XL2'0000'   IPL device address from I/O interrupt information
STATUS   DC    XL2'0000'   Used to accumulate unit and channel status
STATCLR  DC    XL2'0000'   Clears the STATUS field for each new read
         SPACE 2
*
* FBA CCW chain used by the boot loader to read a directed record
*
FBACCW1  CCW0  DEFN_EXT,EXTENT,CC,EXTENTL   Define extent for the read
FBACCW2  CCW0  LOC_DATA,LOCATE,CC,LOCATEL   Establish location for read
FBACCW3  CCW0  READ,0,0,0                   Read the directed record
*         CCW0  NOP,0,0,1                    ..then a NOP.
* If the preceding NOP CCW command is enabled, then the FBACCW3 must set 
* command chaining in the flag byte, setting the third operand to X'40'
         SPACE 1
* FBA extent used for reading a directed record.  Unlike typical operations
* where the extent is constant and the locate data changes, when reading
* directed boot loader records, the extent changes and the locate information
* remains unchanged.
EXTENT   DC    XL4'40000000'   Extent file mask: Inhibit all writes
FRSTPSEC DC    FL4'0'       ** Physical first sector of the extent
FRSTLSEC DC    FL4'0'          First logical sector of the extent, always 0
* Last logical sector of the extent, always the same based upon record length
ENDLSEC  DC    FL4'0'
EXTENTL  EQU   *-EXTENT        Length of an FBA extent (16 bytes)
* ** This field is adjusted for each read of a directed record.
         SPACE 1
* FBA locate used for reading a directed record
LOCATE   DC    XL1'06'         Read sector operation being performed
         DC    XL1'00'         Replication count ignored for read sector
LOCSECS  DC    HL2'0'          Number of sectors being read
         DC    FL4'0'          First sector (relative to the extent), always 0
LOCATEL  EQU   *-LOCATE        Length of the FBA locate information (8 bytes)
         SPACE 2
* PSW's used by the boot loader
PGMRS    DWAIT CODE=008     Restart New PSW trap.  Points to Restart Old PSW
WAIT     PSWEC 2,0,2,0,0    Causes CPU to wait for I/O interruption
CONT     PSWEC 0,0,0,0,IODONE   Causes the CPU to continue after waiting
IOTRAP   PSWEC 0,0,2,0,X'38'    I/O trap New PSW (restored after I/O)
         SPACE 1
* PSW's terminating program execution
DONE     DWAITEND              Successful execution of the program
NODEV    DWAIT PGM=04,CMP=0,CODE=004  IPL device not available
BUSYDEV  DWAIT PGM=04,CMP=0,CODE=008  IPL device busy
CSWSTR   DWAIT PGM=04,CMP=0,CODE=00C  CSW stored in ASA
NOTCON   DWAIT PGM=04,CMP=0,CODE=010  Unexpected interruption from other device
CHERROR  DWAIT PGM=04,CMP=0,CODE=014  IPL channel error occurred
DVERROR  DWAIT PGM=04,CMP=0,CODE=018  IPL device error occurred
OVERWRIT DWAIT PGM=04,CMP=0,CODE=01C  Trying to overwrite boot loader
DESTOVLP DWAIT PGM=04,CMP=0,CODE=020  Destructive overlap detected by MVCL
BADSIZE  DWAIT PGM=04,CMP=0,CODE=024  Cumulative booted program sizes mismatch
NOAMCHNG DWAIT PGM=04,CMP=0,CODE=028  Can not change booted program's AMODE
HWM      EQU   *    Can not load any directed record lower than here
         END