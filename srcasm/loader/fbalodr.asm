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
         TITLE 'FBA BOOT LOADER'
* Program Description:
*
* LOADER is a generic boot loader program.  It requires input/output commands to
* the IPL device to load the booted program.  This boot loader is executed by
* means of an IPL from a FBA DASD volume.  Control is passed to the booted
* program by means of a branch instruction.
*
* Various boot loader services are provided for use by the loader itself and
* the booted program.
*
* Target Architecture: S/360, S/370, ESA/390, or z/Arch
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
*    X'000018' - Unexpected External interruption occurred.  Old External PSW at
*                address X'18'
*    X'000020' - Unexpected Supervisor interruption occurred.  Old Supervisor
*                PSW at address X'20'
*    X'000028' - Unexpected Program interruption occurred. Old Program PSW at
*                address X'28'
*    X'000030' - Unexpected Machine Check interruption occurred.  Old Machine
*                Check PSW at address X'30'
*    X'000038' - Unexpected Input/Output interruption occurred.  Old
*                Input/Output PSW at address X'38'
*    X'050004' - IPL Device or channel not operational
*    X'050008' - IPL Device or channel busy
*    X'05000C' - IPL Device or channel had a problem. See SCSW in IOT entry
*    X'050010' - Unexpected interruption from some other device. See ASA X'BA'
*    X'050014' - NOT USED
*    X'050018' - IPL device not supported by this boot loader
*    X'05001C' - Directed record overwriting boot loader
*    X'050020' - Destructive overlap detected by MVCL while loading record
*    X'050024' - Cumulative booted program sizes do not match in LOD1
*    X'050028' - Can not change addressing mode for booted program
*    X'05002C' - Incompatbile run-time and assembly-time architectures
         TITLE 'FBA BOOT LOADER - ARCHITECTURE LEVEL SET AND LOAD ASA CONTENT'
* See all object data and macro generated model statements in the listing
         PRINT DATA,GEN
         SPACE 1
* Inform the SATK macros of the architecture being targeted.  Inferred from
* the ASMA -t command-line argument.
         ARCHLVL
         SPACE 2
* Ensure interrupt traps are loaded by iplasma.py before program execution
* begins.  This macro will create the memory region that will also contain
* the IPL PSW.  The region name defaults to ASAREGN.  iplasma.py knows how
* to deal with ASA creation.
         SPACE 1
ASASECT  BLASALD
         ASAIPL IA=LODSTART    Define the bare-metal program's IPL PSW
         SPACE 3
*
*  Commonly used FBA Values
*
         SPACE 1
* CCW Commands
NOP      EQU   X'03'     No operation CCW Command
DEFN_EXT EQU   X'63'     Define Extent CCW Command
LOC_DATA EQU   X'43'     Locate CCW Command (within a defined extent)
READ     EQU   X'42'     Read located data CCW Command
         SPACE 1
* CCW Flags
CC       EQU   X'40'     CCW Command chaining
         TITLE 'FBA BOOT LOADER - INITIALIZATION'
*
* FBA Boot Loader Program
*
         SPACE 1
LODSECT  START X'400',LOADER   Start a second region for the loader itself
* This results in LOADER.bin being created in the list directed IPL directory
         BLINIT DTYPE=LOD1LENF+LOD1FBA
         TITLE 'FBA BOOT LOADER - PROCESSING'
* Test the service call framework
         LA    13,EOBL+(SAVEAREA-DMEMORY)   Point to my save area
         BLSCALL SPB=TEST00
         $LTR  15,15
         $BZ   *+6            CC==0, success
         DC    HL2'0'         Otherwise, die here
         SPACE 3
* Initialize the I/O system and the I/O Table with the IPL device
         BLSCALL SPB=INIT01
         $LTR  15,15
         $BZ   *+6            RC==0, success
         DC    HL2'0'         Otherwise, die here
         SPACE 1
* Remember where the IPL Device is in the I/O Table.  Need it during use of
* EXCP service.  So set it in the ORB.
         L     6,INIT01+(SPBIOTA-SPB)
         ST    6,EXCPORB
         USING BLSIOT,6
         SPACE 3
* Test the QIOT service
* Look for the IPL device whatever its device number is
         MVC     QUERY02+2(2),BLSDEV
         DROP    6
         BLSCALL SPB=QUERY02
         B        *+4(15)     Use branch table to process return code
         $B       IPLFND      RC==0, found IPL device in I/O Table
         DC       FL4'4'      RC==4, did not find the IPL device. Die here
         SPACE 3
* Test the ENADEV service
* This is commented out because the only device used by the boot loader is
* the IPL device and it is enabled by the hardware during the IPL function.
* For this reason, the I/O Table address is supplied by the INITIO service.
* The boot loader does not need this service, but the booted program may.
*         BLSCALL SPB=ENADEV03
*         B     *+4(15)        Use branch table to process return code
*         DC    F'0'           RC==0, entry added                    TESTED
*         $B    IPLFND         RC==4, duplicate entry                TESTED
*         DC    F'8'           RC==8, error state                    TESTED
*         DC    F'12'          RC==12, device not operational        TESTED
*         DC    F'16'          RC==16, I/O Table full                TESTED
*         DC    F'20'          RC==20, device entry class mismatch   TESTED
          SPACE 1
* Prepare for use of the IPL device by the boot loader
IPLFND   MVC   IPLDEV,IOICODE    Save the address of the IPL device
* The IPL device must be available for use because we successfully got here.
* Prepare the channel program for use of the IPL device by the boot loader
         SPACE 1
* Initialize the static portions of the I/O related data
         SR    2,2          Clear cumulative size of loaded program to zero
         LR    9,2          Clear size of data being moved from record
         SR    6,2          Clear work register
         LOADHL 6,LOD1MDLN  Fetch from LOD1 the maximum directed record length
         STCCWCNT 6,FBACCW3 CCW - Update count field in CCW
         SRL   6,9(0)             Convert bytes into sectors.
         STH   6,LOCSECS    LOC - Will always read the same number of sectors
         LR    5,6                Save the number of sectors (updates extent)
         BCTR  6,0                And the logical end of the extent is constant
         ST    6,ENDLSEC    EXT - Set it in the FBA extent data
* R6 is now available for other uses
         L     4,LOD1IOA          Fetch where directed records are read
         STCCWADR 4,FBACCW3          CCW - Update the CCW for reading
         MVC   FRSTPSEC,LOD1FSEC     EXT - Set starting sector of first record
* Initialize the static portions of record loading
         LA    8,6(4)       Locate start of directed record's content
         LA    3,EOBL+(HWM-DMEMORY)   Directed records may not overwrite me!
         SPACE 1
READLOOP BLSCALL SPB=EXCP04
         B     *+4(15)           Use the branch table to analyze return code
         $B    MOVEREC           ..Success, move the directed record
         DC    FL4'4'            ..Physical EOF should not occur for FBA device
         $B    DEVCSW            ..Error state
         $B    DEVNOAVL          ..Device busy, not avalable or invalid
         DC    FL4'16'           ..Die here if ORB is invalid
         DC    HL2'0'            Die here if unexpected return code
         SPACE 3
MOVEREC  DS    0H    Move the directed record to its residence address
         L     10,0(4)           Destination address of record's content
         CLR   3,10              Will data from record overwrite boot loader?
         BH    OVRWRITE          ..Yes, HWM higher than load address, quit now!
         LOADHL 9,4(4)           Size of record being loaded
         LR    6,9               Increment for cumulative program loaded
         VMOVE 10,8,DSTRCT=DESTRT
         SPACE 1
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
CKSIZE   CLC   LOD1BPLN,LOD1BPLD  Do the cumulative sizes match in LOD1?
         BNE   CUMERROR           ..No, something went wrong, quit
         SPACE 3
* Enter the boot loaded program...
         SPACE 1
         BOOTNTR
         SPACE 3
* Service NOOP SPB
         DS    0F
TEST00   DC    Y(NOOP),H'0'         Tests service functionality
         SPACE 1
* Service IOINIT SPB
         DS    0F
INIT01   DC    Y(IOINIT),H'0',F'0'  Perform I/O initialization
         SPACE 1
* Service QIOT SPB
         DS    0F
QUERY02  DC    Y(QIOT),H'0',F'0'    Locate the IPL device in the device table
         SPACE 1
* Service ENADEV SPB
*         DS    0F      This SPB is used for testing ENADEV service
*ENADEV03 DC    Y(ENADEV),X'0110',X'00000000'  Add a device
         SPACE 1
         DS    0F
* Service EXCP SPB
EXCP04   DC    Y(EXCP),AL1(SPBEWDC),XL1'0'
EXCPORB  BLSORB CCW=FBACCW1
         SPACE 3
* End the bare-metal program with an error indicated in PSW
DEVNOAVL MVI   DIE+7,X'04'   Code 004 device is not available
         LPSW  DIE
DEVBUSY  MVI   DIE+7,X'08'   Code 008 device is busy (no wait)
         LPSW  DIE
DEVCSW   MVI   DIE+7,X'0C'   Code 00C CSW stored in ASA
         LPSW  DIE
DEVUNKN  MVI   DIE+7,X'10'   Code 010 unexpected device caused I/O interruption
         LPSW  DIE
*SERVERR  MVI   DIE+7,X'14'   Code 014 booted program may not call this service
*         LPSW  DIE
BADDEVT  MVI   DIE+7,X'18'   Code 018 IPL device type unsupported
         LPSW  DIE
OVRWRITE MVI   DIE+7,X'1C'   Code 01C Overwriting boot loader
         LPSW  DIE
DESTRT   MVI   DIE+7,X'20'   Code 020 Destructive overlap detected by MVCL
         LPSW  DIE
CUMERROR MVI   DIE+7,X'24'   Code 024 Cumulative booted program sizes do no match
         LPSW  DIE
AMERROR  MVI   DIE+7,X'28'   Code 028 Can not change booted pgm addressing mode
         LPSW  DIE
ARCHBAD  MVI   DIE+7,X'2C'   Code 028 Incompatible assembled vs run-time archs
         LPSW  DIE
         SPACE 1
* General Constants:
ONE      DC    F'1'      The constant 'one'.
         SPACE 1
* I/O related information
IPLDEV   DC    XL2'0000'   IPL device address from I/O interrupt information
         SPACE 2
*
* FBA CCW chain used by the boot loader to read a directed record
*
FBACCW1  CCW   DEFN_EXT,EXTENT,CC,EXTENTL   Define extent for the read
FBACCW2  CCW   LOC_DATA,LOCATE,CC,LOCATEL   Establish location for read
FBACCW3  CCW   READ,0,0,0                   Read the directed record
*         CCW   NOP,0,0,1                    ..then a NOP.
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
* PSW used by the boot loader
PGMRS    DWAIT CODE=008     Restart New PSW trap.  Points to Restart Old PSW
         SPACE 2
* PSW's terminating program execution
DONE     DWAITEND              Successful execution of the program
DIE      DWAIT PGM=05,CMP=0,CODE=000  Code set at run-time
         TITLE 'BOOT LOADER - SERVICES'
         COPY  'bls.asm'
         TITLE 'BOOT LOADER - MEMORY USAGE OUTSIDE OF REGION'
EOBL     DS    0D   The end of the boot loader that participates in IPL.
* DSECT DMEMORY is placed after this location
         SPACE 1
         BLMEM
         TITLE 'BOOT LOADER - DSECTS'
         BLSPB
         SPACE 3
BLSIOT   BLSIOT
         SPACE 3
*
* Subroutine Register Save Area DSECT
*
         SPACE 1
         SAVEAREA DSECT=YES
         SPACE 3
*
* Input/Output Structure DSECT's
*
         SPACE 1
         BLSIODS
         SPACE 3
*
* Hardware and Software Assigned Storage Locations
*
         SPACE 1
* This DSECT allows symbolic access to these locations.  The DSECT created is
* named ASA.  Addressing is established by: USING  ASA,0
* In this context, general register 0 is an assembler artifact.  Instructions
* that have R0 as a base register never actually use it for address generation.
         SPACE 1
ASA      BLSASA
         TITLE 'BOOT LOADER'
         END
