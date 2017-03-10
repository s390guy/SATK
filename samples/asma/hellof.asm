* Copyright (C) 2017 Harold Grovesteen
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

         TITLE 'hellof.asm - Hello World Program Using Functions'
* This program displays a "Hello World" message on the console device found
* at device address X'00F'.  It can be assembled for use on a system compatible with
* architectures: System/360, System/370, ESA/390 or z/Architecture(R).
*
* The program illustrates various SATK facilities for:
*   - defining assigned storage locations,
*   - changing architecture mode,
*   - performing input/output operations,
*   - defining macros for SATK conditional assembly programming,
*   - use of functions,
*   - use of functions calling functions, and
*   - use of function-local stack frame values.
*
* Two regions are used: the first for assigned storage locations and the second
* for the Hello World program itself.
*
* Requires ASMA environment variable MACLIB set to SATK/maclib
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
         PRINT OFF
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
         DSECTS NAME=(ASA,FRAME,IO,IOCB)
         EJECT
* Initiate the LOWCORE CSECT in the LOAD region with location counter at 0
         PRINT DATA
LOWCORE  ASALOAD REGION=LOAD
* Create IPL PSW
         ASAIPL IA=HELLO
         EJECT
* The Hello World program itself...
* Address Mode: 24
* Main Program Register Usage:
*   R2     Function argument and return value
*   R8     IOCB pointer for ENADEV and RAWIO macros
*   R13    Program and function base register
* z/Architecture systems only:
*   R5     Used for CPU register when signaling architecture change
*   R6,R7  Signaling registers when changing architecture
         SPACE 1
* Initiate the HELLO CSECT in the PROGRAM region with location counter at X'2000'
HELLO    START X'2000',PROGRAM   Initiates the HELLO CSECT in the PROGRAM region
         USING ASA,0         Allow the program to address assigned storage directly
         $BASR 13,0          Establish the program's base register
         USING *,13          ..and inform the assembler
         SETARCH 13          Cleanly enter 64-bit mode if that makes sense
         SPACE 1
* Initialize the function stack
         STKINIT BOS         Now intialize the function stack frame
* Functions can now be called.  The main program must be sensitive to function
* register usage and volatile registers.  Local "variables" are not available to
* the main program.
         SPACE 1
         LA    8,HELLOIO     Locate the console IOCB in a non-volatile register
         SPACE 1
* Initialize I/O
         $LR   2,8           Tell the IOINIT function where the IOCB is located
         CALL  IOINIT        Enable the CPU and console device for I/O
         $LTR  2,2           Did we succeed?
         $BNZ  FAILED        ..No, error disabled wait then
         SPACE 1
* Issue Hello World Message
         $LR   2,8           Tell the DOIO function where the IOCB is located
         LA    3,HELLODEV    Locate the console device number in the message
         CALL  DOIO
         $LTR  2,2           Did we succeed?
         $BNZ  FAILED        ..No, error disabled wait then
         SPACE 1
* Terminate the bare-metal program
         LPSW  GOODPSW       Terminate with indication of success
         SPACE 1
* Any error arrives here
FAILED   LPSW  FAILPSW       Terminate with indication of failure
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
HELLOMSG DC    C'Hello World from a bare-metal mainframe program using functions'
         DC    C' on console device '
HELLODEV DC    C'XXXX'
HELLOLEN EQU   *-HELLOMSG
         SPACE 3
* Termination PSWs
FAILPSW  DWAIT                     I/O failed
GOODPSW  DWAITEND                  Hello World succeeded
         TITLE 'hellof.asm - IOINIT Function'
* IOINIT Entry Register Usage:
*   R1   I/O device used by ENADEV macro
*   R2   Address of the IOCB being enabled
* IOINIT Function Register Usage:
*   R8   Used to address SCHIB if used
*   R13  Local base register (established by FUNCTION macro)
* IOINIT Exit Register Usage:
*   R2   Return code: 0 == success, 1 == failure
*   R14  Return address (established by caller's CALL or CALLR macro)
         SPACE 1
IOINIT   FUNCTION
* Step 1a - Initialize the CPU for I/O operations
         IOINIT
         USING IOCB,2              Establish my addressability to the IOCB
* Step 1b - Enable the device, making it ready for use
         ENADEV DISPLAY,FAIL,REG=8
         SPACE 1
* Could not enable the device
FAIL     DS    0H
         LA    2,1                 Enable failed, return 1
         $B    IOINITR             Return to caller
         SPACE 1
* Device enable successful
DISPLAY  DS    0H
         SPACE 1
         $SR   2,2                Enable succeeded, return 0
IOINITR  RETURN
         TITLE 'hellof.asm - DOIO Function'
* DOIO Entry Register Usage:
*   R2   Address of the IOCB to with which the I/O is performed
*   R3   Location in message where device number/address is placed.
* DOIO Function Register Usage:
*   R1   I/O device used by RAWIO macro
*   R8   Channel subsystem structure addressing, if required
*   R9   IOCB base address
*   R13  Local base register (established by FUNCTION macro)
* DOIO Exit Register Usage:
*   R2   Return code: 0 == success, 1 == failure
*   R14  Return address (established by caller's CALL or CALLR macro)
         SPACE 1
DOIO     FUNCTION
         $LR   9,2                 Move IOCB address to a non-volatile register
         USING IOCB,9
         LH    2,IOCBDEV           Fetch the device number from the IOCB
         CALL  HHEX                Format it in the message
         RAWIO 8,FAIL=IOFAIL,CERR=IOFAIL,UERR=IOFAIL
         $SR   2,2                 I/O succeeded, return 0
         $B    DOIOR
         SPACE 1
IOFAIL   DS    0H
         LA    2,1                 I/O failed, return 1
         SPACE 1
DOIOR    RETURN
         TITLE 'hellof.asm - HHEX Function'
* HHEX Function:
*   Converts a two-byte halfword in R2 to a 4-byte EBCDIC character sequence moved
*   to the address contained in R3.
* HHEX Entry Register Usage:
*   R2   Low-order 16-bits contains halfword to be converted to hex
*   R3   Address of the 4-bytes for the converted half word to hex
* HHEX Function Register Usage:
*   R8   Hex translation table address
*   R13  Local base register (established by FUNCTION macro)
*   R15  Stack frame base register (established by FUNCTION macro)
* DOIO Exit Register Usage:
*   R14  Return address (established by caller's CALL or CALLR macro)
         SPACE 1
* Local stack frame usage
         LOCAL
HHEXHWD  DS    CL3
HHEXHWX  DS    CL5
         SPACE 1
HHEX     FUNCTION
         STH   2,HHEXHWD
         UNPK  HHEXHWX,HHEXHWD
         $L    8,HHEXTRTA
         TR    HHEXHWX(4),0(8)
         MVC   0(4,3),HHEXHWX
         RETURN
         SPACE 1
HHEXTRT  DC    CL16'0123456789ABCDEF'
*         SPACE 1
*         MACRO
*&LABEL   POINTER &LOC
*         GBLC  &ARCHATP   Address constant type from ARCHIND macro
*&LABEL   DC    &ARCHATP.(&LOC)
*         MEND
         SPACE 1
HHEXTRTA POINTER  HHEXTRT-240
         SPACE 3
* Locate the bottom of the function call stack beyond the end of this section
BOS      STACK 2048          Establish the bottom of the stack with label BOS
         END   HELLO
