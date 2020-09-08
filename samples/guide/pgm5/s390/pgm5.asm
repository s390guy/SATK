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
         TITLE 'PGM5390 - HELLO WORLD WITH BOOT LOADER SERVICES'
* Program Description:
*
* PGM5390 is a bare-metal 'Hello World' program.  It uses boot loader
* services to issue the message.  The program is executed by means of FBA DASD
* boot loader configured for ESA/390 operation.
*
* Target Architecture: ESA/390
*
* Devices Used:
*   00F - Console device (by this program)
*   110 - FBA IPL volume (by the boot loader)
*
* Program Register Usage:
*
*   R0   Base register for access to the ASA.  Required by DSECT usage
*   R12  The program base register
*   R13  Save area used by calls to Boot Loader Services
*   R15  Used by the boot loader to enter the booted program
*        Boot Loader Services return code
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
*    X'000038' - Unexpected Input/Output interruption occurred.  Old Input/Output
*                PSW at address X'38'
*    X'051004' - Console Device X'00F' or channel not operational
*    X'051008' - Console Device X'00F' or channel busy
*    X'05100C' - Console Device X'00F' or channel had a problem. See CSW.
         EJECT
* See all object data and macro generated model statements in the listing
         PRINT DATA,GEN
         SPACE 1
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
* The Bare-Metal Hello World Program
*
         SPACE 1
PGMSECT  START X'2000',BOOTED5 Start a second region for the program itself
* This results in BOOTED5.bin being created in the list directed IPL directory
         USING ASA,0           Give me instruction access to the ASA CSECT
PGMSTART $LR   12,15           Establish my base register
         USING PGMSTART,12     Tell the assembler
         SPACE 1
* Ensure program is not re-entered by a Hercules console initiated restart.
* Address 0 changed from its absolute storage role (IPL PSW) to its real
* storage role (Restart New PSW) after the IPL.
* Change from the IPL PSW at address 0 to Restart New PSW trap
*         MVC   RSTNPSW,PGMRS    Done by boot loader
         SPACE 1
* Enable the console device for operation
         LA    13,SAVEAREA     Locate my save area (used by both calls)
         BLSCALL SPB=ENASPB
         B     *+4(15)   Use branch table to analyzed return code...
         $B    ENABLED     0 - Console device is successfully enabled
         DC    FL4'4'      4 - Console device is already enabled. Bad! Die.
         $B    DEVSCSW     8 - Console device is in an error state
         $B    DEVNOAVL   12 - Console device is not available or invalid
         DC    FL4'16'    16 - I/O Table is full.  Die here.
         DC    FL4'20'    20 - Device class does not match existing entry. Die.
* We are ignoring any interrupt from a secondary device.  Should not happen.
         SPACE 1
ENABLED  DS    0H    Pass console device IOT entry address to the EXCP service
         MVC   EXCPORB(4),ENAIOTA
         SPACE 1
* Issue the 'Hello World' message...
         BLSCALL SPB=EXCPSPB
         B     *+4(15)   Use branch table to analyzed return code...
         $B    HURRAY    'Hello World' message successful
         DC    FL4'4'      4 - Physical end-of-file??  Nope!  Die here.
         $B    DEVSCSW     8 - Console device is in an error state
         $B    DEVNOAVL   12 - Console device is in an error state
         DC    FL4'16'    16 - ORB is invalid.  Die here.
         space 1
HURRAY   LPSW  DONE      Normal program termination
         SPACE 1
* End the bare-metal program with an error indicated in PSW
DEVNOAVL MVI   ENDBAD+7,X'04'
         LPSW  ENDBAD    Code 004 End console device is not available
DEVBUSY  MVI   ENDBAD+7,X'08'
         LPSW  ENDBAD    Code 008 End because device is busy or not available
DEVSCSW  MVI   ENDBAD+7,X'0C'
         LPSW  ENDBAD    Code 00C End because SCSW stored in IOT entry
         SPACE 1
* PSW's terminating program execution
DONE     DWAITEND              Successful execution of the program
ENDBAD   DWAIT PGM=05,CMP=1,CODE=000  Updated with abend code
         TITLE 'PGM5390 - BOOT LOADER SERVICES PARAMETER BLOCKS'
*
* I/O related Boot Loader Service Parameter Blocks and Save Area
*
         SPACE 1
SAVEAREA SAVEAREA
         SPACE 1
* ENADEV Service Paramater Block (See BLS.odt or BLS.pdf for details)
         DS    0F
ENASPB   DC    Y(ENADEV)    Service ID for ENADEV service (from BLSTABLE)
         DC    XL2'000F'    Input/Output - Console device number
         SPACE 1
* Service Parameter Block Extenion
ENAIOTA  DS    0F           Output - Console device I/O Table entry address
ENASPBC  DC    AL1(BLSCON)  Input - Enabling a console device (from BLIOT)
         DC    XL3'00'
         SPACE 3
* EXCP Service Parametger Block (See BLS.odt or BLS.pdf for details)
         SPACE 1
         DS    0F
EXCPSPB  DC    Y(EXCP)      Service ID for EXCP service (from BLSTABLE)
         DC    AL1(SPBEWDC) EXCP controls (from BLSPB)
         DC    XL1'00'      not used
EXCPORB  BLSORB CCW=CONCCW
         SPACE 3
*
* CCW and data used by the program to write the Hello World message
*
         SPACE 1
CONCCW   CCW   X'09',MESSAGE,0,MSSGLEN      Write Hello World message with CR
*         CCW   X'03',0,0,1                   ..then a NOP.
* If the preceding NOP CCW command is enabled, then the CONCCW must set
* command chaining in the flag byte, setting the third operand to X'40'
         SPACE 1
MESSAGE  DC    C'Hello Bare-Metal World!'   Data sent to console device
MSSGLEN  EQU   *-MESSAGE                    Length of Hello World text data
         SPACE 3
         TITLE 'PGM5390 - DSECTS AND EQUATES'
*
* Boot loader service ID's:
*
         SPACE 1
         BLSTABLE
         SPACE 3
*
* Service Parameter Block and Extension Usage
*
         SPACE 1
         BLSPB
         SPACE 3
*
* Boot Loader I/O Table Entry
*
         SPACE 1
BLSIOT   BLSIOT
         SPACE 3
*
* Hardware and software assigned storage areas
*
         SPACE 1
* This DSECT allows symbolic access to these locations.  The DSECT created is
* named ASA and contains the assigned storage locations and boot loader LOD1
* record definition.
ASA      BLSASA
         END