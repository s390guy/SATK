* Copyright (C) 2015 Harold Grovesteen
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

* NOTICES:
* z/Architecture is a registered trademark of International Business Machines
* Corporation.   

         TITLE 'hello.asm - Generic Mainframe Bare-Metal Hello World Program'
* This program displays a "Hello World" message on the console device found
* at device address X'00F'.  It can be assembled for use on a system compatible with
* architectures: System/360, System/370, ESA/390 or z/Architecture(R).
*
* The program illustrates various SATK facilities for:
*   - defining assigned storage locations,
*   - changing architecture mode,
*   - performing input/output operations, and
*   - defining macros for SATK conditional assembly programming
*
* Two regions are used: the first for assigned storage locations and the second
* for the Hello World program itself.
*
* Suggested Hercules Config:
*    # Depending upon your choice of ASMA target use:
*    ARCHMODE S/370   # For ASMA target command-line argument -t s360 or -t s370
* or ARCHMODE ESA/390 # For ASMA target command-line argument -t e390
* or ARCHMODE z/Arch  # For ASMA target command-line argument -t s390x
*    MAINSIZE  1M     # Minimum required for ESA/390 or z/Architecture
*    NUMCPU   1
*    # Console Device
*    000F 3215-C /    # Hello world message displayed here
*
* Recommend List-Directed IPL using ASMA command-line argument -g
         SPACE 1
         PRINT ON
         COPY  'satk.mac'
         PRINT ON
*
* Macro for conditionally including an architecture change or not
*
         MACRO
&LABEL   SETARCH &BASE
         GBLA  &ARCHLVL   Current architecture level
         AIF   ('&LABEL' EQ '').NOLBL
&LABEL   DS    0H
.NOLBL   ANOP
         AIF   (&ARCHLVL LT 8).DONE
         AIF   ('&BASE' EQ '').NOCLR
         ZEROLH &BASE,1    Make sure bit 32 in 64-bit register is zero after change
.NOCLR   ANOP
         ZARCH 6,5,SUCCESS=INZMODE,FAIL=FAIL  Change to 64-bit mode if capable
INZMODE  DS    0H
.DONE    MEND
         SPACE 1
         ARCHLVL ZARCH=NO
         EJECT
         DSECTS NAME=(ASA,IO,IOCB)
         EJECT
* Initiate the LOWCORE CSECT in the LOAD region with location counter at 0
         PRINT DATA
LOWCORE  ASALOAD REGION=LOAD
* Create IPL PSW
         ASAIPL IA=HELLO
         EJECT
* The Hello World program itself...
* Address Mode: 24
* Register Usage:
*   R1     I/O device used by ENADEV and RAWIO macros
*   R2     Program base register
*   R3     IOCB pointer for ENADEV and RAWIO macros
*   R4     IO work register used by ENADEV and RAWIO
* z/Architecture systems only:
*   R5     Used for CPU register when signaling architecture change
*   R6,R7  Signaling registers when changing architecture
         SPACE 1
* Initiate the HELLO CSECT in the PROGRAM region with location counter at X'2000'
HELLO    START X'2000',PROGRAM   Initiates the HELLO CSECT in the PROGRAM region
         USING ASA,0         Allow the program to address assigned storage directly
         $BASR  2,0          Establish the program's base register
         USING *,2           ..and inform the assembler
         SETARCH 2           Cleanly enter 64-bit mode if that makes sense
         LA    3,HELLOIO     Provide access to the IOCB
         USING IOCB,3        ..and inform the assembler
         SPACE 1
* Display the hello world message on the console.
* Step 1 - Initialize the CPU for I/O operations
         IOINIT
         SPACE 1
* Step 2 - Enable the device, making it ready for use
         ENADEV DISPLAY,FAIL,REG=4
         SPACE 1
* Step 3 - Output the hello world message on the console
DISPLAY  RAWIO 4,FAIL=FAIL,CERR=FAIL,UERR=FAIL
         SPACE 1
* Step 4 - Terminate the bare-metal program
         LPSW  GOODPSW       Terminate with indication of success
         SPACE 1
* Any error arrives here
FAIL     LPSW  FAILPSW       Terminate with indication of failure
         SPACE 3
* Data and structures used by the program
*
* Structure used by RAWIO identifying the device and operation being performed
HELLOIO  IOCB  X'00F',CCW=HELLOCCW
         SPACE 1
* Channel program that displays a message on a console with carriage return
WRITECR  EQU   X'09'
HELLOCCW CCW   WRITECR,HELLOMSG,0,HELLOLEN
         SPACE 1
* The actual Hello World message
HELLOMSG DC    C'Hello World from a bare-metal mainframe program'
HELLOLEN EQU   *-HELLOMSG
         SPACE 3
* Termination PSWs
FAILPSW  DWAIT                     I/O failed
GOODPSW  DWAITEND                  Hello World succeeded
         END   HELLO
