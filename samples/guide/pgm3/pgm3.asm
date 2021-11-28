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
         TITLE 'PGM3 - HELLO WORLD WITH CONSOLE I/O'
* Program Description:
*
* PGM3 is a bare-metal 'Hello World' program.  It requires input/output
* commands to the console device to issue the message.  The program is
* executed by means of an IPL from a FBA DASD volume.
*
* Target Architecture: S/370
* 
* Devices Used:
*   00F - Console device
*   110 - FBA IPL volume
*
* Program Register Usage:
*
*   R0   Base register for access to the ASA.  Required by DSECT usage
*   R1   Device Channel and Unit Address for I/O instructions 
*   R12  The program base register
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
*    X'030004' - Console Device X'00F' or channel not operational
*    X'030008' - Console Device X'00F' or channel busy
*    X'03000C' - Console Device X'00F' or channel had a problem. See CSW.
*    X'030010' - Unexpected interruption from some other device. See ASA X'BA'
*    X'030014' - Console channel error occurred
*    X'030018' - Console device did not complete the I/O without a problem
         EJECT
* See all object data and macro generated model statements in the listing
         PRINT DATA,GEN
* Uncomment the next statement if you do not want the ASA DSECT in the listing         
*        PRINT OFF
* Inform the SATK macros of the architecture being targeted.  Inferred from
* the ASMA -t command-line argument.
         ARCHLVL
         SPACE 1
*
* Hardware Assigned Storage Locations
*
         SPACE 1
* This DSECT allows symbolic access to these locations.  The DSECT created is 
* named ASA.
ASA      ASAREA DSECT=YES
         EJECT
* Uncomment this statement if you have disabled printing of the ASA
*        PRINT ON,GEN
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
PGMSECT  START X'300',IPLPGM3  Start a second region for the program itself
* This results in IPLPGM3.bin being created in the list directed IPL directory
         USING ASA,0           Give me instruction access to the ASA CSECT
PGMSTART BALR  12,0            Establish my base register
         USING *,12            Tell the assembler
         SPACE 1
* Ensure program is not re-entered by a Hercules console initiated restart.
* Address 0 changed from its absolute storage role (IPL PSW) to its real
* storage role (Restart New PSW) after the IPL.
* Change from the IPL PSW at address 0 to Restart New PSW trap
         MVC   RSTNPSW,PGMRS
         SPACE 1
* Prepare channels for use by the bare-metal program
         LCTL  2,2,CR2     Enable only channel 0 for I/O interruptions
         SPACE 1
* Determine if the device, subchannel and channel are ready for use.
         LH    1,CONDEV    Set up I/O device address in I/O instruction register
         TIO   0(1)        Determine if the console is there
         BC    B'0100',DEVNOAVL  ..No, CC=1 might have a different config address
         BC    B'0010',DEVBUSY   ..No, CC=2 console device or channel is busy
         BC    B'0001',DEVCSW    ..No, CC=3 CSW stored in ASA at X'40'
* Console device is available (CC=0)!
         SPACE 1
* Prepare for I/O to console
         MVC   CAW(8),CCWADDR    Identify in ASA where first CCW resides
         SPACE 1
* Send the Hello World message to the console
         SIO   0(1)        Request console channel program to start, did it?
         BC    B'0100',DEVNOAVL  ..No, CC=1 don't know why, but tell someone.
         BC    B'0010',DEVBUSY   ..No, CC=2 console device or channel is busy
         BC    B'0001',DEVCSW    ..No, CC=3 CSW stored in ASA at X'40' 
* Console device is now receiving the message (CC=0)
         SPACE 1
* Wait for an I/O interruption
DOWAIT   MVC   IONPSW(8),CONT  Set up continuation PSW for after I/O interrupt
         LPSW  WAIT       Wait for I/O interruption and CSW from channel
IODONE   EQU   *          The bare-metal program continues here after I/O
         MVC   IONPSW(8),IOTRAP     Restore I/O trap PSW
         SPACE 1
* I/O results can now be checked.
*   Did the interruption come from the console device?
         CH    1,IOICODE           Is the interrupt from the console?
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
* HURRAY!  Program 3 delivered its Hello World message!
         LPSW  DONE      Normal program termination
         SPACE 1
* End the bare-metal program with an error indicated in PSW
DEVNOAVL LPSW  NODEV     Code 004 End console device is not available
DEVBUSY  LPSW  BUSYDEV   Code 008 End because device is busy (no wait)
DEVCSW   LPSW  CSWSTR    Code 00C End because CSW stored in ASA
DEVUNKN  LPSW  NOTCON    Code 010 End unexpected device caused I/O interruption
CHNLERR  LPSW  CHERROR   Code 014 End because console channel error occurred
UNITERR  LPSW  DVERROR   Code 018 End because console device error occurred
         SPACE 1
* Control Register 2 - Enables channels for interruptions
CR2      DC    XL4'80000000'  Enable only channel 0 where console is connected
         SPACE 1
* I/O related information
CCWADDR  DC    A(CONCCW) Address of first CCW to be executed by console device.
CONDEV   DC    XL2'000F'   Console device address
STATUS   DC    XL2'0000'   Used to accumulate unit and channel status
         SPACE 1
* CCW used by the program to write the Hello World message
CONCCW   CCW0  X'09',MESSAGE,0,MSSGLEN      Write Hello World message with CR
*         CCW0  X'03',0,0,1                   ..then a NOP.
* If the preceding NOP CCW command is enabled, then the CONCCW must set 
* command chaining in the flag byte, setting the third operand to X'40'
MESSAGE  DC    C'Hello Bare-Metal World!'   Data sent to console device
MSSGLEN  EQU   *-MESSAGE                    Length of Hello World text data
         SPACE 1
* PSW's used by the bare-metal program
PGMRS    DWAIT CODE=008     Restart New PSW trap.  Points to Restart Old PSW
WAIT     PSWEC 2,0,2,0,0    Causes CPU to wait for I/O interruption
CONT     PSWEC 0,0,0,0,IODONE   Causes the CPU to continue after waiting
IOTRAP   PSWEC 0,0,2,0,X'38'    I/O trap New PSW (restored after I/O)
         SPACE 1
* PSW's terminating program execution
DONE     DWAITEND              Successful execution of the program
NODEV    DWAIT PGM=03,CMP=0,CODE=004  Console device not available
BUSYDEV  DWAIT PGM=03,CMP=0,CODE=008  Console device busy
CSWSTR   DWAIT PGM=03,CMP=0,CODE=00C  CSW stored in ASA
NOTCON   DWAIT PGM=03,CMP=0,CODE=010  Unexpected interruption from other device
CHERROR  DWAIT PGM=03,CMP=0,CODE=014  Console channel error occurred
DVERROR  DWAIT PGM=03,CMP=0,CODE=018  Console device error occurred
         END