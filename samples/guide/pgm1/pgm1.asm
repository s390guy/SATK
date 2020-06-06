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
         TITLE 'PGM1 - HELLO WORLD'
* Program Description:
*
* PGM1 is a bare-metal 'Hello World' program.  It does not require any I/O
* to issue the message.  DIAGNOSE X'008' as emulated by Hercules is used for
* the output.  The program is executed by means of Hercules list-directed
* IPL.
*
* Target Architecture: S/370
*
* Program Register Usage:
*   R8   The DIAGNOSE start of command address
*   R9   The DIAGNOSE start of command response address
*   R10  The DIAGNOSE command length (bytes 1-3) and flags (byte 0) on input
*        and return code on output
*   R11  The DIAGNOSE command response length
*   R12  The program base register
*
* DIAGNOSE RX,RY,X'008'
*   Issues a console command to Hercules.  The command being executed is the
*   Hercules MSG command.  It displays a message on the Hercules console.  The
*   instruction sets the condition code:
*      0 - Successful execution by Hercules
*      1 - Unsuccessful execution by Hercules
*   If successful a return code is set in register RY
*      0 - Successful execution
*   Otherwise a non-zero return code is an error.  Note Hercules only returns
*   zero.  However, VM may not.
*
*   Flags are specified in the high-order byte, byte 0, of the RY register:
*     X'80' - Reject password in command (ignored by Hercules)
*     X'40' - Provide command response in the area defined by RX+1 and RY+1
*     X'20' - Prompt for password (ignored by Hercules).
*
*   A program specification exception can be triggered if an invalid register
*   is used, if the command string is too long (256 max on Hercules), if
*   the response area is too short (256 max on Hercules), flags are invalid,
*   or DIAGNOSE X'008' not enabled by Hercules configuration statement:
*       DIAG8CMD enable
*
* Hercules MSG Command
*    The Hercules MSG command emulates the VM MSG command.  The VM MSG command
*    sends a message to the specified user ID.  An asterisk for user ID
*    indicates the message is directed to the issuing user id.  For Hercules
*    this is the executing program.  For this reason, the command is separated
*    into its command portion and the text portion.
*
* Disables Wait State PSW's address field values used by the program:
*    X'0000' - Successful execution of the program
*    X'0028' - Unexpected program interruption occurred. Old program PSW at
*              address X'28'
*    X'DEAD' - Unsuccessful execution of the DIAGNOSE command
*
         SPACE 2
         PRINT DATA            See all object data in listing
         SPACE 1
PSWSECT  START 0,IPLPSW        Start the first region for the IPL PSW
* This results in IPLPSW.bin being created in the list directed IPL directory
         PSWEC 0,0,0,0,PGMSECT The IPL PSW for this program
         SPACE 1
PGMSECT  START X'300',IPLPGM1  Start a second region for the program itself
* This results in IPLPGM1.bin being created in the list directed IPL directory
         BALR  12,0            Establish my base register
         USING *,12            Tell the assembler
         SPACE 1
* Set a trap PSW in case some program interruption occurs
         MVC   X'68'(8,0),PGMEX  Set a NEW PSW to trap program interruptions
* Issue the DIAGNOSE instruction that executes a Hercules command
         LM    8,10,DIAGPRMS   Load the DIAGNOSE instruction's registers
         DIAG  8,10,X'008'     Issue the Hello World message to the console
         SPACE 1
* Analyze results...
         BNZ   BADCMD    If a non-zero condition code set, the DIAGNOSE failed
         LTR   10,10     Was a non-zero return code set by the DIAGNOSE?
         BNZ   BADCMD    ..Yes, abnormal program termination
         LPSW  GOOD      ..No, normal program termination
         SPACE 1
BADCMD   LPSW  BAD       End with a bad address in PSW field
         SPACE 1
* PSW's used by this program...
* Disabled wait trap PSW for program interruptions
PGMEX    PSWEC 0,0,2,0,X'28'   Points to the program OLD PSW
* Program termination PSW's
GOOD     PSWEC 0,0,2,0,0       Successful execution of the program
BAD      PSWEC 0,0,2,0,X'DEAD' Unsuccessful execution of the program
         SPACE 1
* The DIAGNOSE parameters are placed in these registers.  Note, because no
* response is returned to the program, the RX+1 and RY+1 registers are 0.
*              8          9    10                11
*              RX         RX+1 RY                RY+1
DIAGPRMS DC    A(COMMAND),A(0),X'00',AL3(CMDLEN),A(0)
         SPACE 1
* Hercules console command being issued.  This command, MSG, simply displays
* a message on the Hercules console.  Just what the Hello World program needs.
COMMAND  DC    C'MSG * '                    VM emulated command
MESSAGE  DC    C'Hello Bare-Metal World!'   Message text sent to self
CMDLEN   EQU   *-COMMAND
         END