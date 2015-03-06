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

         TITLE 'hellofm.asm - Hello World Program in Multipl Architectures'
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
*   - use of functions calling functions,
*   - use of function-local stack frame values, and
*   - detecting and executing in multiple architectures.
*
* Two regions are used: the first for assigned storage locations and the second
* for the Hello World program itself.
*
* Assembling this Multi-Architecture Program
*    Command line target may default to -t 24 or be explicitly used
*    --psw not required.  All architectures use 64-bit EC format PSW in amode 24
*
*    The same assembly may be used in all of its supported architectures:
*       - System/370 EC
*       - ESA/390 native
*       - z/Architecture (automatically enters z/Architecture when ESA/390 on z)
*
* Suggested Hercules Config:
*    ARCHMODE S/370
* or ARCHMODE ESA/390
* or ARCHMODE z/Arch
*    MAINSIZE  1M     # Minimum required for ESA/390 or z/Architecture
*    NUMCPU   1
*    # Console Device
*    000F 3215-C /    # Hello world message displayed here
*
* Recommend List-Directed IPL using ASMA command-line argument -g
         SPACE 1
         PRINT OFF
         COPY  'satk.mac'
         COPY  'function.mac'
         PRINT ON
         TITLE 'hellofm.asm - Main Program'
         MACRO
&LABEL   MAIN
         GBLC &A             Architecture specific suffix
         GBLC &I             I/O Architecture specific suffix
HELLO    CSECT
&LABEL   $BASR 13,0          Establish the program's base register
         USING *,13          ..and inform the assembler
* Initialize the function stack
         STKINIT BOS         Now intialize the function stack frame
* Functions can now be called.  The main program must be sensitive to function
* register usage and volatile registers.  Local "variables" are not available to
* the main program.
         SPACE 1
         $L    8,CONIO&A     Locate the console IOCB in a non-volatile register
         SPACE 1
* Initialize I/O
         $LR   2,8           Tell the IOINIT function where the IOCB is located
         ICALL  IOINIT       Enable the CPU and console device for I/O
         $LTR  2,2           Did we succeed?
         $BNZ  FAILED&A      ..No, error disabled wait then
         SPACE 1
* Issue Hello World Message
         $LR   2,8           Tell the DOIO function where the IOCB is located
         LA    3,HELLODEV    Locate the console device number in the message
         LA    4,HELLOARC    Location for the architecture level
         ICALL DOIO
         $LTR  2,2           Did we succeed?
         $BNZ  FAILED&A      ..No, error disabled wait then
         SPACE 1
* Terminate the bare-metal program
         LPSW  GOODPSW&A     Terminate with indication of success
         SPACE 1
* Any error arrives here
FAILED&A LPSW  FAILPSW&A     Terminate with indication of failure
         SPACE 3
* Termination PSWs
FAILPSW&A DWAIT              I/O failed
GOODPSW&A DWAITEND           Hello World succeeded
         SPACE 1
CONIO&A  POINTER HELLOIO&I
         MEND
         TITLE 'hellofm.asm - DOIO Function'
* DOIO Entry Register Usage:
*   R2   Address of the IOCB with which the I/O is performed
*   R3   Location in message where device number/address is placed.
*   R4   Location in message where architecture level placed
* DOIO Function Register Usage:
*   R1   I/O device used by RAWIO macro
*   R8   Channel subsystem structure addressing, if required
*   R9   IOCB base address
*   R13  Local base register (established by FUNCTION macro)
* DOIO Exit Register Usage:
*   R2   Return code: 0 == success, 1 == failure
*   R14  Return address (established by caller's ICALL or CALLR macro)
         SPACE 1
         MACRO
         DOIOI
         GBLC  &I         For localizing function symbols
DOIO     IFUN
         $LR   9,2                 Move IOCB address to a non-volatile register
         USING IOCB,9
         LH    2,IOCBDEV           Fetch the device number from the IOCB
         SCALL HHEX                Format it in the message
         L     2,ARCHLVL           Fetch the architecture level
         LA    3,ARCHNUM           This is where its EBCDIC numbers are placed
         SCALL UFDEC               Convert the arch level to printable value
         MVC   0(1,4),ARCHNUM+L'ARCHNUM-1   Move it to the actual message
         RAWIO 8,FAIL=IOFAIL&I,CERR=IOFAIL&I,UERR=IOFAIL&I
         $SR   2,2                 I/O succeeded, return 0
         $B    DOIOR&I
         SPACE 1
IOFAIL&I DS    0H
         LA    2,1                 I/O failed, return 1
         SPACE 1
DOIOR&I  RETURN
         DROP  9                   Do not polute other functions with my using
         MEND
         TITLE 'hellofm.asm - HHEX Function'
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
* HHEX Exit Register Usage:
*   R14  Return address (established by caller's SCALL or CALLR macro)
         SPACE 1
         MACRO
         HHEXS
         GBLC  &S         For localizing function symbols
* Local stack frame usage
         LOCAL
HHEXHWD&S  DS    CL3
HHEXHWX&S  DS    CL5
         SPACE 1
HHEX     SFUN
         STH   2,HHEXHWD&S
         UNPK  HHEXHWX&S,HHEXHWD&S
         $L    8,HHEXTA&S
         TR    HHEXHWX&S.(4),0(8)
         MVC   0(4,3),HHEXHWX&S
         RETURN
         SPACE 1
HHEXTRT&S  DC    CL16'0123456789ABCDEF'
         SPACE 1
HHEXTA&S POINTER  HHEXTRT&S-240
         MEND
         TITLE 'hellofm.asm - IOINIT Function'
* IOINIT Entry Register Usage:
*   R1   I/O device used by ENADEV macro
*   R2   Address of the IOCB being enabled
* IOINIT Function Register Usage:
*   R8   Used to address SCHIB if used
*   R13  Local base register (established by FUNCTION macro)
* IOINIT Exit Register Usage:
*   R2   Return code: 0 == success, 1 == failure
*   R14  Return address (established by caller's ICALL or CALLR macro)
         SPACE 1
         MACRO
         IOINITI
         GBLC  &I         For localizing function symbols
IOINIT   IFUN
* Step 1a - Initialize the CPU for I/O operations
         IOINIT
         USING IOCB,2              Establish my addressability to the IOCB
* Step 1b - Enable the device, making it ready for use
         ENADEV DISPLAY&I,FAIL&I,REG=8
         SPACE 1
         DROP  2                   Input parm becomes returned value
* Could not enable the device
FAIL&I   DS    0H
         LA    2,1                 Enable failed, return 1
         $B    IOINITR&I           Return to caller
         SPACE 1
* Device enable successful
DISPLAY&I  DS    0H
         SPACE 1
         $SR   2,2                 Enable succeeded, return 0
IOINITR&I RETURN
         MEND
         TITLE 'hellofm.asm - UFDEC Function'
* UFDEC Function:
*   Converts a 4-byte unsigend value into 10 EBCDIC numbers
* UFDEC Entry Register Usage:
*   R2   Low order 32 (or all 32 bits) contains an unsigned binary value
*   R3   Address where the 10 decimal digits are placed
* HHEX Exit Register Usage:
*   R14  Return address (established by caller's SCALL or CALLR macro)
         MACRO
         UFDECS
         GBLC  &S         For localizing function symbols
* Local stack frame usage
         LOCAL
UFDECP&S  DS    CL8                xx.xx.x1.23.45.67.89.0S     Packed (from CVD)
UFDECE&S  DS    CL10      F0.F1.F2.F3.F4 F5.F6.F7.F8 F9.S0     Unpacked (from UNPK)
         SPACE 1
UFDEC    SFUN
         CVD    2,UFDECP&S                 Convert binary to packed decimal format
         OI     UFDECP&S+7,X'0F'           Convert sign to a X'F'
         UNPK   UFDECE&S,UFDECP&S+2(L'UFDECP&S-2)    Convert to zoned numeric
         MVC    0(L'UFDECE&S,3),UFDECE&S   Move result to location requested
         RETURN
         MEND
         TITLE 'hellofm.asm - Architecture Independent Structures'
         DSECTS NAME=(ASA,IOCB)
         TITLE 'hellofm.asm - 32-bit Architecture Specific Structures'
         PRINT NOGEN
         ARCHLVL ZARCH=NO
         PRINT GEN
         DSECTS NAME=FRAME
         TITLE 'hellofm.asm - Channel I/O Specific Structures'
         DSECTS NAME=IO
         TITLE 'hellofm.asm - IPL Entry'
* Initiate the LOWCORE CSECT in the LOAD region with location counter at 0
         PRINT DATA
LOWCORE  ASALOAD REGION=LOAD,ZARCH=YES
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
         SPACE 1
* Determine the running architecture
         APROB
         ST    1,ARCHLVL     Remember the level for printing
         ANTR  S370=S370,E390=E390,S390=S390
         TITLE 'hellofm.asm - 32-bit Shared Functions'
         HHEXS
         SPACE 3
         UFDECS
         TITLE 'hellofm.asm - Channel I/O Structures and Data'
         DSECTS NAME=IO
         SPACE 3
HELLO    CSECT
HELLOIOC IOCB  X'00F',CCW=HELLOCCW
         TITLE 'hellofm.asm - System/370 Hello World'
S370     MAIN
         SPACE 3
         IOINITI
         SPACE 3
         DOIOI
         SPACE 3
         TITLE 'hellofm.asm - Channel Subsystem Specific Structures and Data'
         XMODE PSW,E390
         XMODE CCW,0
         PRINT NOGEN
         ARCHLVL ZARCH=NO
         PRINT GEN
         SPACE 3
         DSECTS NAME=IO
HELLO    CSECT
* Structure used by RAWIO identifying the device and operation being performed
HELLOIOD IOCB  X'00F',CCW=HELLOCCW
         TITLE 'hellofm.asm - Native ESA/390 Hello World'
E390     MAIN
         SPACE 3
         IOINITI
         SPACE 3
         DOIOI
         TITLE 'hellofm.asm - Enter z/Architecture Mode'
         XMODE PSW,E390
         XMODE CCW,0
         PRINT OFF
         ARCHLVL
         PRINT ON
         SPACE 3
HELLO    CSECT
S390     $BASR 13,0
         USING *,13
         ZEROLH 13,1    Make sure bit 32 in 64-bit register is zero after change
         ZARCH 6,5,SUCCESS=INZMODE,FAIL=FAILEDZ  Change to 64-bit mode if capable
         SPACE 1
FAILEDZ  LPSW  FAILPSW9
         TITLE 'hellofm.asm - z/Architecture Specific Structures'
         XMODE PSW,Z
         XMODE CCW,0
         PRINT OFF
         ARCHLVL
         PRINT ON
         DSECTS NAME=FRAME
         TITLE 'hellofm.asm - z/Architecture Shared Functions and I/O Data'
HELLO    CSECT
         HHEXS
         SPACE 3
         UFDECS
         SPACE 3
HELLOIOM IOCB  X'00F',CCW=HELLOCCW
         TITLE 'hellofm.asm - z/Archtecture Hello World'
INZMODE  MAIN
         SPACE 3
         IOINITI
         SPACE 3
         DOIOI
         TITLE 'hellofm.asm - Globally Shared Data'
* Data and structures used by the program
HELLO    CSECT
* Channel program that displays a message on a console with carriage return
WRITECR  EQU   X'09'
HELLOCCW CCW   WRITECR,HELLOMSG,0,HELLOLEN
         SPACE 1
* The actual Hello World message
HELLOMSG DC    C'Hello World using architecture: '
HELLOARC DC    C'9'
         DC    C' from a bare-metal mainframe program'
         DC    C' on console device '
HELLODEV DC    C'XXXX'
HELLOLEN EQU   *-HELLOMSG
         SPACE 1
ARCHLVL  DC    F'-1'            Remember the architecture level here
ARCHNUM  DC    C'1234567890'    This is where it is converted into EBCDIC
         SPACE 3
* Locate the bottom of the function call stack beyond the end of this section
BOS      STACK 2048          Establish the bottom of the stack with label BOS
         END   HELLO
