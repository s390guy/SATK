         TITLE 'SAMPLE OPERATING SYSTEM     VERSION 2.00'
***********************************************************************
*                                                                     *
*  *****************************************************************  *
*  *                                                               *  *
*  *                       SAMPLE OPERATING SYSTEM                 *  *
*  *                             VERSION 2.00                      *  *
*  *                        DEVELOPED AT MIT 1973                  *  *
*  *                                                               *  *
*  *****************************************************************  *
*                                                                     *
***********************************************************************
         SPACE 3
         PRINT ON,NODATA,GEN
PROGRAM  START 0,SOSLOAD           ASMA: Needed to create region
         SPACE 1
CORESIZE EQU   32768 BYTES OF CORE IN OBJECT MACHINE
         SPACE 1
         USING *,0 COMMUNICATIONS AREA
         SPACE 1
IPLPSW   DC    B'00000000',B'00000000',X'0000',X'00',AL3(IPLRTN)
IPLCCW1  DS    D .                 IPL CCW #1
IPLCCW2  DS    D .                 IPL CCW #2
EXTOLD   DS    D .                 EXTERNAL OLD PSW
SVCOLD   DS    D .                 SVC OLD PSW
PGMOLD   DS    D .                 PROGRAM INTERRUPT OLD PSW
MCHKOLD  DS    D .                 MACHINE CHECK OLD PSW
IOOLD    DS    D .                 I/O INTERRUPT OLD PSW
CSW      DS    D .                 CHANNEL STATUS WORD
CAW      DS    F .                 CHANNEL ADDRESS WORD
UNUSED0  DS    F .
TIMER    DC    F'-1' .             TIMER
UNUSED1  DC    F'0' .
EXTNEW   DC    B'00000000',B'00000000',X'0000',X'00',AL3(EXTHANDL)
SVCNEW   DC    B'00000000',B'00000000',X'0000',X'00',AL3(SVCHANDL)
PGMNEW   DC    B'00000000',B'00000000',X'0000',X'00',AL3(PGMHANDL)
MCHKNEW  DC    B'00000000',B'00000010',X'0000',X'00',AL3(0)
IONEW    DC    B'00000000',B'00000000',X'0000',X'00',AL3(IOHANDL)
         ORG   *+X'100' SPACE OVER STAND ALONE DUMP AREA
FSBPTR   DC    A(VERYEND) .        FSB POINTER
FSBSEM   DC    F'1,0' .            FSB SEMAPHORE
MEMORY   DC    F'0,0' .            MEMORY SEMAPHORE
CAWSEM   DC    F'1,0' .            CAW SEMAPHORE
         SPACE 1
TRAPSAVE DS    16F .               STORAGE FOR EXTERNAL INTERRUPTS
IOHSAVE  DS    16F .               STORAGE FOR I/O INTERRUPTS
         SPACE 1
SYSSEMSA DS    CL84 .              SYSTEM SEMAPHORE SAVE AREA
         SPACE 1
RUNNING  DS    A .                 RUNNING
NEXTTRY  DS    A .                 NEXTTRY
NEXTTRYM DS    C,0H .              NEXTTRY MODIFIED
         EJECT
***********************************************************************
*                                                                     *
*              EXTERNAL, PROGRAM, AND SVC INTERRUPT HANDLERS          *
*                                                                     *
***********************************************************************
         SPACE 1
EXTHANDL EQU   * .                 EXTERNAL INTERRUPT HANDLER
         STM   0,15,TRAPSAVE .     SAVE REGISTERS
         BALR  1,0 .               ESTABLISH ADDRESSING
         USING *,1
         CLI   EXTOLD+3,X'80' .    SEE IF TIMER TRAP
         BNE   EXTHRET .           IF NOT, IGNORE
         L     15,RUNNING .        SET UP REGISTERS FOR TRAFFIC
         USING PCB,15 .             CONTROLLER (XPER)
         CLI   PCBBLOKT,X'FF' .    IF BLOCKED, NO PROCESS IS
         BE    EXTHRET .            RUNNABLE, SO RETURN
         LA    14,PCBISA .         GET SAVE AREA
         USING SA,14
         MVC   SAPSW,EXTOLD .      AND STORE OLD STUFF INTO IT
         MVC   SAREGS,TRAPSAVE
         B     XPER .              THEN GO TO TRAFFIC SCHEDULER
         DROP  14,15
EXTHRET  LM    0,15,TRAPSAVE .     TO IGNORE AN INTERRUPT, RELOAD
         LPSW  EXTOLD .            AND TRANSFER BACK
         SPACE 1
PGMHANDL EQU   * .                 PROGRAM INTERRUPT HANDLER
         SVC   C'?' .              IN ANY CASE, AN ERROR
         EJECT
***********************************************************************
*                                                                     *
*                          SVC INTERRUPT HANDLER                      *
*                                                                     *
*        FOR ALL ROUTINES ENTERED BY SVC INTERRUPT, THE               *
*        FOLLOWING REGISTERS CONTAIN THIS INFORMATION:                *
*                                                                     *
*        REGISTER  1 - BASE REGISTER FOR ROUTINE                      *
*        REGISTER  2 - POINTER TO ARGUMENT LIST (IF ANY)              *
*        REGISTER 14 - POINTER TO SAVEAREA USED FOR THIS SVC          *
*        REGISTER 15 - POINTER TO PCB PRESENTLY RUNNING               *
*                                                                     *
***********************************************************************
         SPACE 1
SVCHANDL EQU   * .                 SVC HANDLER
         STM   0,15,TRAPSAVE .     SAVE REGISTERS
         BALR  9,0 .               ESTABLISH ADDRESSING
         USING *,9
         LM    10,14,SVCCONST .    INITIALIZE REGISTERS
         IC    10,SVCOLD+3 .       GET SVC CODE
         IC    10,SVCHTABL(10) .   TRANSLATE INTO TABLE OFFSET
         LA    10,SVCRTN(10) .     REG 10 -> THE CORRECT PSW
         CLI   2(10),X'00' .       IS THIS CALL PROTECTED?
         BE    SVCHPROT .          THEN SEE IF WE CAN CALL IT
SVCOK    L     15,RUNNING .        GET PCB POINTER
         USING PCB,15
         CLI   3(10),X'00' .       IS IT A SYSTEM SAVEAREA?
         BE    SYSSEM .            DON'T USE REG 14 AS PCB POINTER
         LR    14,15 .             ELSE, SET UP PCB POINTER
SYSSEM   IC    11,3(10) .          GET POINTER TO SAVE AREA OFFSET
         A     14,SVCSAVE(11) .    REG 14 -> SAVE AREA
         CLI   SVCOLD+3,C'.' .     ARE WE CALLING XPER?
         BE    SVCXPER .           IF SO, DON'T SAVE RETURN STATUS
         USING SA,14
         MVC   SAPSW,SVCOLD .      SAVE PSW
         MVC   SAREGS,TRAPSAVE .   SAVE REGISTERS
SVCXPER  L     1,4(10) .           MAKE ADDRESSING EASY WITHIN
         LPSW  0(10) .              ROUTINE, AND GO THERE
SVCHPROT L     12,SVCOLD .         GET PROTECTION KEY
         NR    12,13 .             IS IT A USER?
         BZ    SVCOK .             IF NO, THAT'S FINE
         LA    10,SVCRTN+136 .     ELSE SET UP CALL TO XQUE
         B     SVCOK .
         DROP  9
SVCCONST DC    3F'0',X'00F00000',F'0'
         SPACE 1
SVCHTABL DC    256X'84' .          TABLE OF PSW OFFSETS
         ORG   SVCHTABL+C'P'
         DC    AL1(0)
         ORG   SVCHTABL+C'V'
         DC    AL1(8)
         ORG   SVCHTABL+C'!'
         DC    AL1(16)
         ORG   SVCHTABL+C','
         DC    AL1(24)
         ORG   SVCHTABL+C'B'
         DC    AL1(32)
         ORG   SVCHTABL+C'A'
         DC    AL1(40)
         ORG   SVCHTABL+C'F'
         DC    AL1(48)
         ORG   SVCHTABL+C'I'
         DC    AL1(56)
         ORG   SVCHTABL+C'J'
         DC    AL1(64)
         ORG   SVCHTABL+C'.'
         DC    AL1(72)
         ORG   SVCHTABL+C'R'
         DC    AL1(80)
         ORG   SVCHTABL+C'S'
         DC    AL1(88)
         ORG   SVCHTABL+C'C'
         DC    AL1(96)
         ORG   SVCHTABL+C'N'
         DC    AL1(104)
         ORG   SVCHTABL+C'Y'
         DC    AL1(112)
         ORG   SVCHTABL+C'Z'
         DC    AL1(120)
         ORG   SVCHTABL+C'D'
         DC    AL1(128)
         ORG   SVCHTABL+C'?'
         DC    AL1(136)
         ORG   SVCHTABL+C'H'
         DC    AL1(144)
         ORG   SVCHTABL+C'E'
         DC    AL1(152)
         ORG   SVCHTABL+256
         SPACE 1
SVCRTN   DS    0D .                THE PSWS
*                  IN THE FOLLOWING PSWS, THE THIRD BYTE INDICATES    *
*                  WHETHER THE SVC IS RESTRICTED:                     *
*                             X'00' -> OPERATING SYSTEM ONLY          *
*                             X'FF' -> AVAILABLE TO USER ALSO         *
*                                                                     *
*                   THE FOURTH BYTE INDICATES WHICH SAVE AREA TO USE; *
*                   SVCSAVE BELOW SHOWS THE CODE VALUES.              *
         DC    B'00000000',B'00000000',X'0000',X'00',AL3(XP)
         DC    B'00000000',B'00000000',X'0000',X'00',AL3(XV)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XEXC)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XCOM)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XB)
         DC    B'11111111',B'00000000',X'000C',X'00',AL3(XA)
         DC    B'11111111',B'00000000',X'000C',X'00',AL3(XF)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XI)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XJ)
         DC    B'00000000',B'00000000',X'0004',X'00',AL3(XPER)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XR)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XS)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XC)
         DC    B'00000000',B'00000000',X'FF04',X'00',AL3(XN)
         DC    B'00000000',B'00000000',X'FF08',X'00',AL3(XY)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XZ)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XD)
         DC    B'00000000',B'00000000',X'FF04',X'00',AL3(XQUE)
         DC    B'11111111',B'00000000',X'FF08',X'00',AL3(XH)
         DC    B'11111111',B'00000000',X'000C',X'00',AL3(XAUTO)
         SPACE 1
SVCSAVE  DS    0F .                THE SAVE AREA OFFSETS
         DC    A(SYSSEMSA) .       CODE 00 -> SYSSEMSA
         DC    A(PCBISA-PCB) .     CODE 04 -> INTERRUPT SAVE AREA
         DC    A(PCBFSA-PCB) .     CODE 08 -> FAULT SAVE AREA
         DC    A(PCBMSA-PCB) .     CODE 0C -> MEMORY SAVE AREA
         SPACE 3
***********************************************************************
*                                                                     *
* RETURN SEQUENCE FOR REQUEST DRIVEN ROUTINES AND TRAFFIC CONTROLLER  *
*                                                                     *
***********************************************************************
         SPACE 1
         DS    0D
RETURN   DC    B'00000000',B'00000000',X'0000',X'00',AL3(RETURNR)
         SPACE 1
RETURNR  EQU   * .                 RETURN ROUTINE FOR SVC'S AND XPER
         MVC   SVCOLD,SAPSW .      SAVE PSW IN A SAFE PLACE
         LM    0,15,SAREGS .       RELOAD REGISTERS
         LPSW  SVCOLD .            AND RETURN
         EJECT
***********************************************************************
*                                                                     *
*                          REQUEST DRIVEN ROUTINES                    *
*                                                                     *
***********************************************************************
         SPACE 3
***********************************************************************
*                                                                     *
*                                  XP ROUTINE                         *
*                                                                     *
*        FUNCTION: TO IMPLEMENT "P" PRIMITIVE FOR SEMAPHORES          *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS SM         *
*                    SM        DS 0D   SEMAPHORE DEFINITION           *
*                    SMVAL     DS F    VALUE                          *
*                    SMPTR     DS A    POINTER TO FIRST WAITER        *
*   ROUTINES USED: XPER                                               *
*       PROCEDURE: SUBTRACT ONE FROM SMVAL; IF NON-NEGATIVE, RETURN.  *
*                  IF NEGATIVE, PLACE RUNNING PROCESS AT END OF LIST  *
*                  OF PRECESSES WAITING ON SM. BLOCK CALLING PROCESS; *
*                  ENTER TRAFFIC CONTROLLER.                          *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XP       EQU   * .                 THE XP ROUTINE
         USING *,1
         USING SM,2 .              ARGUMENT IS A SEMAPHORE
         L     3,SMVAL  .          GET THE VALUE
         BCTR  3,0 .               SUBTRACT ONE
         ST    3,SMVAL .           AND STORE IT BACK
         LTR   3,3 .               SET CONDITION CODE
         BM    XPWAIT .            IF IT'S NEGATIVE, MUST WAIT
         LPSW  RETURN .            ELSE RETURN NOW
XPWAIT   LA    4,SMPTR .           START GOING DOWN
         L     5,SMPTR .            CHAIN OF POINTERS
         DROP  15
         USING PCB,5
XPLOOP   LTR   5,5 .               IF REACHED END
         BZ    XPTHEN .            ADD OUR PCB ON. ELSE,
         LA    4,PCBNSW .          INCREMENT POINTERS
         L     5,PCBNSW
         B     XPLOOP .            AND TRY AGAIN
         DROP  5
         USING PCB,15
XPTHEN   MVC   0(4,4),RUNNING .    WE'RE AT THE END
         ST    5,PCBNSW .          STORE NULL POINTER
         MVI   PCBBLOKT,X'FF' .    AND WE'RE BLOCKED
         MVC   PCBISA,SYSSEMSA .   SWITCH SAVE AREAS
         B     XPER .              SO RUN SOMEONE ELSE
         DROP  2
         EJECT
***********************************************************************
*                                                                     *
*                                  XV ROUTINE                         *
*                                                                     *
*        FUNCTION: TO IMPLEMENT "V" PRIMITIVE FOR SEMAPHORES          *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS SM         *
*                    SM        DS 0D   SEMAPHORE DEFINITION           *
*                    SMVAL     DS F    VALUE                          *
*                    SMPTR     DS A    POINTER TO FIRST WAITER        *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: ADD ONE TO SMVAL; IF > ZERO, RETURN. IF ZERO OR    *
*                  LESS, REMOVE FIRST PROCESS FROM WAITER CHAIN;      *
*                  UNBLOCK IT; IF NEXTTRYM NOT SET, SET IT AND SET    *
*                  NEXTTRY TO THAT PROCESS; RETURN; IF NEXTTRYM SET,  *
*                  RETURN.                                            *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XV       EQU   * .                 THE XV ROUTINE
         USING *,1
         USING SM,2 .              ARGUMENT IS A SEMAPHORE
         L     3,SMVAL .           GET THE VALUE
*        A     3,=F'1' .           ADD ONE
         A     3,LTGF1 .     ASMA: ADD ONE (LITERAL POOL NOT SUPPORTED)
         ST    3,SMVAL .           AND STORE IT BACK
         BNP   XVWAKEUP .          IF <=0, SOMEONE'S WAITING
         LPSW  RETURN .            ELSE RETURN
XVWAKEUP L     4,SMPTR .           GET THE FIRST OF THE GUYS
         DROP  15
         USING PCB,4
         MVC   SMPTR,PCBNSW .      REMEMBER THE REST
         MVI   PCBBLOKT,X'00' .    WE'RE NO LONGER BLOCKING HIM
         CLI   NEXTTRYM,X'FF' .    IS NEXT TRY MODIFIED?
         BE    XVRET .             IF SO, WELL OK
         ST    4,NEXTTRY           ELSE MODIFY NEXTTRY
         MVI   NEXTTRYM,X'FF' .    AND SAY SO
XVRET    LPSW  RETURN .            GET BACK
         DROP  2,4
         EJECT
***********************************************************************
*                                                                     *
*                          XPER ROUTINE (TRAFFIC CONTROLLER)          *
*                                                                     *
*        FUNCTION: TO IMPLEMENT MULTIPROGRAMMING                      *
*       DATABASES: NONE                                               *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: STARTING WITH NEXTTRY, SEARCH FOR PROCESS ON ALL   *
*                  PCB CHAIN NOT BLOCKED OR STOPPED; IF FOUND, USE AS *
*                  NEW RUNNING, FOR 50 MS OF TIME AND RETURN. ELSE,   *
*                  ENTER WAIT STATE WITH INTERRUPTS ON, AND TRY TO    *
*                  SCHEDULE AGAIN AFTER INTERRUPT; RETURN.            *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XPER     EQU   * .                 ROUTINE XPER: TRAFFIC SCHEDULER
         SSM   IONEW .             MASK OFF INTERRUPTS
         BALR  1,0
         USING *,1
         L     10,NEXTTRY .        START LOOKING AT NEXTTRY
         LR    11,10 .             REMEMBER WHICH THAT WAS
         USING PCB,10
GWLOOP   CLI   PCBBLOKT,X'FF' .    IF IT'S BLOCKED
         BE    GWINC .             IGNORE
         CLI   PCBSTOPT,X'FF' .    ELSE, IF IT'S NOT STOPPED
         BNE   GWRUN .             WE CAN RUN IT
GWINC    L     10,PCBNPALL .       ELSE, GO TO THE NEXT
         CR    10,11 .             IF WE'VE SEEN ALL, QUIT
         BNE   GWLOOP .            ELSE TRY AGAIN
         LPSW  IDLE .              SIT AND WAIT
         DS    0D
IDLE     DC    B'11111110',B'00000010',X'0000',X'00',AL3(XPER)
         SPACE 1
GWRUN    MVC   NEXTTRY,PCBNPALL .  GET A NEW NEXTTRY
         MVI   NEXTTRYM,X'00' .    NOT MODIFIED
         ST    10,RUNNING .        GET A NEW RUNNING
         LA    14,PCBISA
         MVC   TIMER,QUANTUM .     INTERRUPT AFTER 50 MS
         LPSW  RETURN .            AND GO TO RETURNR
QUANTUM  DC    X'00000F00' .       QUANTUM OF TIME
         DROP  10
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                          XEXC ROUTINE                               *
*                                                                     *
*        FUNCTION: TO ENTER SMC SECTION                               *
*       DATABASES: NONE                                               *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: INCREMENT SMC BYTE IN PCB BY ONE; RETURN.          *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XEXC     EQU   * .                 ROUTINE XEXC: ENTER SMC SECTION
         USING *,1
         SR    8,8
         IC    8,PCBINSMC
         LA    8,1(8) .            ADD ONE TO SMC BYTE
         STC   8,PCBINSMC
         LPSW  RETURN .            AND LEAVE
         SPACE 1
***********************************************************************
*                                                                     *
*                          XCOM ROUTINE                               *
*                                                                     *
*        FUNCTION: TO LEAVE SMC SECTION                               *
*       DATABASES: NONE                                               *
*   ROUTINES USED: XP, XV                                             *
*       PROCEDURE: DECREMENT SMC BYTE IN PCB BY ONE; IF NOT ZERO,     *
*                  RETURN. ELSE, CHECK FOR STOP WAITING; IF STOP      *
*                  WAITING, ALLOW STOP AND BLOCK SELF; RETURN. IF NO  *
*                  STOP WAITING, RETURN.                              *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XCOM     EQU   * .                 ROUTINE XCOM: LEAVE SMC
         USING *,1
         SR    8,8
         IC    8,PCBINSMC
         BCTR  8,0 .               SUBTRACT ONE FROM IN SMC BYTE
         STC   8,PCBINSMC
         LTR   8,8 .               IS IT ZERO?
         BNZ   XCOMRET .           NO, THEN GET BACK, OTHERWISE
         CLI   PCBSW,X'00' .       IS STOP WAITING?
         BE    XCOMRET .           IF NOT, RETURN
         MVI   PCBSW,X'00' .       STOPS NOT WAITING AFTER THIS
         LA    2,PCBSRS .          WE'LL "V" THE STOPPER,
         SVC   C'V'
         LA    2,PCBSES .          AND "P" THE STOPPEE.
         SVC   C'P'
XCOMRET  LPSW  RETURN .            AND HERE (IF EVER) WE RETURN
         EJECT
***********************************************************************
*                                                                     *
*                            XA ROUTINE                               *
*                         XAUTO ROUTINE                               *
*                                                                     *
*        FUNCTION: TO ALLOCATE MEMORY                                 *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XAX:       *
*                    XAX       DS 0D                                  *
*                    XAXSIZE   DS F     SIZE OF BLOCK TO BE ALLOCATED *
*                    XAXADDR   DS A     ADDRESS OF FIRST BYTE OF BLOCK*
*                    XAXALGN   DS F     ALIGNMENT OF BLOCK            *
*   ROUTINES USED: XEXC, XCOM, XP, XV, XB                             *
*       PROCEDURE: LOCK FSB SEMAPHORE; SEARCH FREE STORAGE FOR LARGE  *
*                  ENOUGH MEMORY BLOCK; ALIGN BOUNDARY; USE XB TO     *
*                  CHAIN ANY LEFTOVER BLOCKS TO FREE STORAGE LIST;    *
*                  PLACE ADDRESS OF ALLOCATED BLOCK IN XAXADDR; UNLOCK*
*                  FSB SEMAPHORE; RETURN. IF CAN'T SATISFY REQUEST,   *
*                  UNLOCK FSB SEMAPHORE, APPLY XP ROUTINE TO MEMORY   *
*                  SEMAPHORE, BLOCKING PROCESS RUNNING UNTIL MEMORY   *
*                  FREED; THEN UNBLOCK; TRY TO SATISFY REQUEST AGAIN. *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XA       EQU   * .                 THE XA ROUTINE, TO ALLOCATE
         USING *,1
         LA    0,1 .               SET REGISTER ZERO TO ONE TO
         B     XACOM .              INDICATE C'A' CALL
XAUTO    EQU   * .                 AUTO STORAGE ENTRY POINT
         USING *,1
         SR    0,0 .               REG0=0 INDICATES C'E' CALL
*        L     1,=A(XA) .          RESET BASE REGISTER PROPERLY
         L     1,LTGXA .     ASMA: RESET BASE REGISTER PROPERLY 
         USING XA,1
XACOM    SVC   C'!' .              ENTER SMC
         LR    7,2
         USING XAX,7 .             ARGUMENT LIST
         L     6,XAXSIZE .         GET THE SIZE REQUESTED
XATOP    LA    2,FSBSEM .          LOCK THE FSB SEMAPHORE
         SVC   C'P' .
         LA    5,FSBPTR .          START LOOKING DOWN
         L     4,FSBPTR .           THE FREE STORAGE LIST
         L     8,XAXALGN .         WE WOULD HAVE TO START AT WITH
         BCTR  8,0 .                THIS CONSTANT TO FIND ALIGNMENT
         USING FSB,4
XALOOP   LTR   4,4 .               IF AT THE END
         BZ    XAWAIT .             WAIT UNTIL A "FREE" OP
         LR    13,4 .              FIND THE LOCATION
         BCTR  13,0 .               IN THIS BLOCK WITH THIS
         OR    13,8 .              ALIGNMENT
         LA    13,1(13) .          THAT'S IT
         LR    9,13 .              AND NOW GET IN REG 9
         SR    9,4 .                WHAT IS WASTED AT THE FRONT
         L     3,FSBSIZE .         GET SIZE MINUS WASTE AT
         SR    3,9 .                FRONT, LEAVING EFFECTIVE SIZE
         CR    6,3 .               IS IT ENOUGH?
         BNP   XAFOUND .           EUREKA!
         LA    5,FSBNEXT .         OH WELL, GET THE NEXT FREE
         L     4,FSBNEXT .          STORAGE BLOCK ON THE CHAIN
         B     XALOOP .            BETTER LUCK NEXT TIME
XAWAIT   SVC   C'V' .              NEED TO WAIT
         LA    2,MEMORY .          SO WE LET OTHER PEOPLE GET IN
         SVC   C'P' .              SO THEY'LL WAKE US UP
         B     XATOP .             AND THEN WE'LL TRY AGAIN
XAFOUND  ST    13,XAXADDR .        WE'VE NOW GOT THE ADDRESS
         MVC   0(4,5),FSBNEXT .    UNLINK THE BLOCK OUT
         L     12,FSBSIZE .        GET THE WHOLE BLOCK SIZE
         LA    2,SATEMP .          START MAKING UP ARG LISTS
         USING XBX,2 .             FOR THE XB ROUTINE
         LR    10,13 .             THE STARTING LOCATION
         SR    10,4 .              MINUS THE START OF THE BLOCK
         BZ    XANF .              IF NONE WASTED AT THE FRONT, SKIP
         ST    4,XBXADDR .         ELSE FREE, STARTING THERE
         ST    10,XBXSIZE .         UP TO THE BEGINNING OF THE
         SVC   C'B' .               ALLOCATION; INSERT IT IN THE CHAIN
XANF     LR    11,13 .             THE STARTING ADDR PLUS THE SIZE
         AR    11,6 .               GIVES THE FIRST UNUSED ADDR
         SR    12,10 .             MINUS THE WASTE AT FRONT,
         SR    12,6 .              MINUS THE PART ALLOCATED. IF
         BZ    XARETURN .          NONE LEFT OVER, GOOD
         ST    11,XBXADDR .        ELSE STORE ADDRESS AND
         ST    12,XBXSIZE .        SIZE, AND LINK ONTO
         SVC   C'B' .              FREE STORAGE LIST
         DROP  2
XARETURN LA    2,FSBSEM .          WE ARE DONE, SO NOW SOMEONE
         SVC   C'V' .               ELSE CAN COME IN
         LTR   0,0 .               IS THIS FOR AUTOMATIC STORAGE?
         BNZ   XABACK .            IF NOT, RETURN NOW
         ST    6,PCBASIZE .        OTHERWISE STORE SIZE AND
         ST    13,PCBAADDR .        ADDRESS OF AUTOMATIC STORAGE
XABACK   SVC   C',' .              LEAVE SMC SECTION
         LPSW  RETURN .            GET BACK JOJO
         DROP  4,7
         EJECT
***********************************************************************
*                                                                     *
*                            XF ROUTINE                               *
*                                                                     *
*        FUNCTION: TO FREE MEMORY                                     *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XFX:       *
*                    XFX       DS 0D                                  *
*                    XFXSIZE   DS F     SIZE OF BLOCK TO BE FREED     *
*                    XFXADDR   DS A     ADDRESS OF FIRST BYTE OF BLOCK*
*   ROUTINES USED: XEXC, XP, XV, XB, XCOM                             *
*       PROCEDURE: LOCK FSB SEMAPHORE; SEARCH FREE STORAGE LIST TO    *
*                  FIND IF ANY FREE BLOCK CONTIGUOUSLY FOLLOWS OR     *
*                  PRECEDES BLOCK TO BE FREED; IF THERE IS ANY,       *
*                  COMPACT THEM INTO A SINGLE BLOCK OF COMBINED SIZE; *
*                  USE XB TO CHAIN COMPACTED BLOCK ONTO FREE STORAGE  *
*                  LIST; WAKEUP ALL PROCESSES WAITING ON MEMORY       *
*                  SEMAPHORE; UNLOCK FSB SEMAPHORE; RETURN            *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XF       EQU   * .                 THE XF ROUTINE, TO FREE STORAGE
         USING *,1
         SVC   C'!' .              ENTER SMC SECTION
         LR    7,2
         USING XFX,7 .             THE ARGUMENT LIST
         L     3,XFXSIZE .         GET THE SIZE
         L     4,XFXADDR .         AND THE ADDRESS
         LR    5,3 .               GET THE ADDRESS OF THE END OF THE
         AR    5,4 .                BLOCK TO BE FREED
         LA    2,FSBSEM .          LOCK FSBSEM
         SVC   C'P'
         LA    8,FSBPTR .          START LOOKING DOWN THE FREE
         L     6,FSBPTR .           STORAGE LIST, FOR COMPACTION
         USING FSB,6
XFLOOP   LTR   6,6 .               ARE WE THROUGH?
         BZ    XFLINK .            IF SO, JUST ADD IT ON
         L     9,FSBNEXT .         IF NOT. GET THE NEXT PTR
         CR    6,5 .               IS THIS BLOCK RIGHT AFTER OURS?
         BNE   XFTHEN .            IF NOT, OK. BUT IF IT IS,
         ST    9,0(8) .            WE CAN COMPACT, SO UNCHAIN IT
         A     3,FSBSIZE .         AND REMEMBER THE NEW SIZE
         B     XFBACKUP .          AND ON TO THE NEXT
XFTHEN   LR    10,6 .              MAYBE IT'S RIGHT BEFORE OURS
         A     10,FSBSIZE .        GET ENDING ADDRESS OF FREE BLOCK
         CR    10,4 .              IS IT RIGHT BEFORE OURS?
         BNE   XFINC .             OH FUDGE! NO!
         ST    9,0(8) .            IF SO, UNLINK IT
         LR    4,6 .               GET THE NEW BEGINNING LOCATION
         A     3,FSBSIZE .         AND NEW SIZE OF FREE BLOCK
XFBACKUP LR    6,8 .               BACK UP ONE FSB
XFINC    LA    8,FSBNEXT .         ON TO THE NEXT FSB
         L     6,FSBNEXT
         B     XFLOOP .            TRY, TRY AGAIN
XFLINK   LA    2,SATEMP .          START TO CALL XB
         USING XBX,2
         ST    3,XBXSIZE .         STORE SIZE
         ST    4,XBXADDR .         AND ADDRESS
         SVC   C'B' .              LINK IT ONTO THE FSB CHAIN
         USING SM,2
         LA    2,MEMORY .          GET VALUE OF MEMORY SEMAPHORE
         LA    11,1(0,0) .         SUBTRACT FROM ONE, IT'S A HANDLE
         S     11,SMVAL .          ON THE # OF PEOPLE WAITING
         DROP  2
XFVLOOP  BCT   11,XFVDO .          LOOP IF ANYONE ELSE IS WAITING
         LA    2,FSBSEM .          WE'RE THROUGH, SO
         SVC   C'V' .              UNBLOCK FSBSEM
         SVC   C',' .              LEAVE SMC
         LPSW  RETURN .            RETURN
XFVDO    SVC   C'V' .              WAKE SOMEONE UP
         B     XFVLOOP .           TRY AGAIN FOR ANOTHER
         DROP  6,7
         EJECT
***********************************************************************
*                                                                     *
*                            XB ROUTINE                               *
*                                                                     *
*        FUNCTION: TO CHAIN A STORAGE BLOCK ONTO FREE STORAGE LIST    *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XBX:       *
*                    XBX       DS 0D                                  *
*                    XBXSIZE   DS F     SIZE OF BLOCK                 *
*                    XBXADDR   DS A     ADDRESS OF FIRST BYTE OF BLOCK*
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: SEARCH FREE STORAGE LIST TO FIND WHERE TO INSERT   *
*                  FREE BLOCK IN ORDER OF INCREASING SIZE; FORMAT     *
*                  BLOCK LIKE AN FSB; INSERT; RETURN.                 *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*        COMMENTS: SINCE XB ROUTINE ONLY CALLED BY XA AND XF, FSB     *
*                  SEMAPHORE IS ALREADY LOCKED.                       *
*                                                                     *
***********************************************************************
         SPACE 1
XB       EQU   *
         USING *,1
         USING XBX,2 .             ARGUMENT LIST
         L     3,XBXSIZE .         GET THE SIZE
         L     4,XBXADDR .         AND THE ADDRESS
         LA    8,FSBPTR .          START LOOKING DOWN THE CHAIN
         L     6,FSBPTR
         LTR   6,6 .               IF ZERO POINTER, WE ARE AT
         BZ    XBINSERT .          END OF CHAIN ALREADY
         USING FSB,6
XBLOOP   C     3,FSBSIZE .         IF THE SIZE OF OURS IS LESS,
         BNP   XBINSERT .           TIME TO INSERT
         LA    8,FSBNEXT .         ELSE GO ON TO THE NEXT
         L     6,FSBNEXT
         LTR   6,6 .               IF NOT ALREADY THROUGH
         BNZ   XBLOOP .            BRANCH BACK
XBINSERT ST    4,0(8) .            NOW, LINK OURS ON
         DROP  6
         USING FSB,4
         ST    6,FSBNEXT .         MAKE OURS POINT TO THE NEXT
         ST    3,FSBSIZE .         WITH THE RIGHT SIZE
         LPSW  RETURN .            AND RETURN
         DROP  2,4
         EJECT
***********************************************************************
*                                                                     *
*                            XC ROUTINE                               *
*                                                                     *
*        FUNCTION: TO CREATE A PROCESS                                *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XCX:       *
*                    XCX       DS 0D                                  *
*                    XCXNAME   DS CL8   NAME OF PROCESS TO BE CREATED *
*   ROUTINES USED: XEXC, XCOM, XN, XA, XI, XQUE                       *
*       PROCEDURE: USE XA TO ALLOCATE NEW PCB; PLACE XCXNAME IN PCB;  *
*                  INITIALIZE SEMAPHORES; STOP; BLOCK; OUT OF SMC;    *
*                  CALL XI TO LINK PCB ONTO PCB CHAINS; RETURN.       *
*    ERROR CHECKS: IF NAME ALREADY USED IN THIS GROUP, XQUE ENTERED.  *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XC       EQU   * .                 THE XC ROUTINE: CREATE A PROCESS
         USING *,1
         LR    7,2
         USING XCX,7 .             ARGUMENT LIST
         LA    2,SATEMP .          READY TO MAKE CALLS OUT
         USING XNX,2 .             A XN-LIKE ARGUMENT LIST
         MVC   XNXNAME,XCXNAME .   GET THE NAME
         SVC   C'N' .              AND CALL TO FIND THE PCB
*        CLC   XNXADDR,=A(0) .     SEE IF THERE
         CLC   XNXADDR,LTG0 .      SEE IF THERE
         BNE   XCERR .             IF ALREADY EXISTS, BAD
         SVC   C'!' .              ENTER SMC SECTION
         DROP  2
         USING XAX,2 .             READY TO CALL XA
*        MVC   XAXSIZE,=A(LENPCB) . WE KNOW THE SIZE
         MVC   XAXSIZE,LTGPCBL . ASMA: WE KNOW THE SIZE (for literal pool)
*        MVC   XAXALGN,=F'8' .     AND THE ALIGNMENT
         MVC   XAXALGN,LTGF8 .   ASMA: AND THE ALIGNMENT (for literal pool)
         SVC   C'A' .              SO CALL
         L     2,XAXADDR .         FIND THE ADDRESS
         DROP  2,15
         USING PCB,2 .             FILL IN THE PCB
         MVC   PCBNAME,XCXNAME .   GIVE IT A NAME
         MVI   PCBSTOPT,X'FF' .    IT'S STOPPED
         MVC   PCBBLOKT(PCBISA-PCBBLOKT),TEMPLATE+1 INITIALIZE PCB
         SVC   C'I' .              THREAD IT ON
         SVC   C',' .              LEAVE SMC SECTION
         LPSW  RETURN .            AND RETURN
XCERR    SVC   C'?' .              IF ALREADY EXISTS,KERROR
         DROP  2,7
         EJECT
***********************************************************************
*                                                                     *
*                            XD ROUTINE                               *
*                                                                     *
*        FUNCTION: TO DESTROY A PROCESS                               *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XDX:       *
*                    XDX       DS 0D                                  *
*                    XDXNAME   DS CL8  NAME OF PROCESS TO BE DESTROYED*
*   ROUTINES USED: XEXC, XJ, XS, XN, XF, XCOM, XQUE                   *
*       PROCEDURE: USE XN TO FIND PCB FOR PROCESS TO BE DESTROYED;    *
*                  USE XJ TO UNLOCK PCB FROM PROCESS CHAINS; IF ANY   *
*                  MESSAGES FOR THIS PROCESS, FREE STORAGE FOR THEM;  *
*                  IF THERE IS ANY AUTOMATIC STORAGE, FREE IT;        *
*                  FREE STORAGE FOR PCB; RETURN.                      *
*    ERROR CHECKS: IF NAME DOESN'T EXIST OR PROCESS NOT STOPPED,      *
*                  XQUE ENTERED.                                      *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XD       EQU   * .                 XD ROUTINE: DESTROY A PROCESS
         USING *,1
         LR    7,2
         USING XDX,7 .             ARG LIST
         LA    2,SATEMP .          READY TO CALL OUT
         USING XNX,2 .             WILL CALL XN
         MVC   XNXNAME,XDXNAME .   GET NAME
         SVC   C'N' .              AND CALL
         L     2,XNXADDR .         GET ADDRESS
         DROP  2
         LTR   2,2 .               IF ADDRESS IS NULL,
         BZ    XDERR .             IT'S AN ERROR
         USING PCB,2
         CLI   PCBSTOPT,X'FF' .    IF NOT STOPPED
         BNE   XDERR .             IT'S AN ERROR
         SVC   C'!' .              ENTER SMC SECTION
         DROP  2
         USING PCB,15
         SVC   C'J' .              ELSE UNTHREAD THE ENTRY
         LR    8,2 .               REMEMBER THE PCB POINTER
         LA    2,SATEMP .          READY TO CALL OUT AGAIN
         USING PCB,8
         DROP  15
         L     9,PCBFM .           GET FIRST MESSAGE
XDLOOP   LTR   9,9 .               ANY MORE MESSAGES?
         BZ    XDCHECK .           IF NOT, FINISH UP
         USING MSG,9
         L     10,MSGNEXT .        ELSE REMEMBER NEXT
         L     11,MSGSIZE .        GET THE SIZE
         LA    11,15(11) .          AND MAKE IT SOME NUMBER
*        N     11,=F'-8' .          OF DOUBLEWORDS
         N     11,LTGFM8 .   ASMA:  OF DOUBLEWORDS (for literal pool)
         USING XFX,2
         ST    9,XFXADDR .         FREE THE LOCATION
         ST    11,XFXSIZE .         THE NUMBER OF WORDS
         SVC   C'F' .              DO IT
         LR    9,10 .              ON TO THE NEXT
         B     XDLOOP .            GET THE NEXT MESSAGE
*XDCHECK  CLC   PCBAADDR(4),=A(0) . HAS AUTOMATIC STORAGE BEEN
XDCHECK  CLC   PCBAADDR(4),LTG0 .  ASMA: HAS AUTOMATIC STORAGE BEEN (for literal pool)
         BE    XDTHEN .             ALLOCATED? IF NOT, GO FINISH UP
         LA    2,PCBASIZE .        SET UP THE ARGUMENT LIST
         SVC   C'F' .              FREE IT
         LA    2,SATEMP .          RESET REGISTER 2
XDTHEN   ST    8,XFXADDR .         READY TO FREE THE PCB
*        MVC   XFXSIZE,=A(LENPCB) . THE SIZE
         MVC   XFXSIZE,LTGPCBL . ASMA: THE SIZE (for literal pool)
         SVC   C'F' .              FREE IT
         SVC   C',' .              LEAVE SMC
         LPSW  RETURN .            AND RETURN
XDERR    SVC   C'?' .              IF PROCESS DOES NOT EXIST
         DROP  2,7,8,9
         USING PCB,15
         SPACE 3
***********************************************************************
*                                                                     *
*                            XH ROUTINE                               *
*                                                                     *
*        FUNCTION: TO HALT A JOB                                      *
*       DATABASES: NONE                                               *
*   ROUTINES USED: XS, XR                                             *
*       PROCEDURE: SEND MESSAGE TO SUPERVISOR PROCESS FOR THIS JOB    *
*                  INDICATING NORMAL TERMINATION; TRIES TO READ       *
*                  MESSAGES FOREVER LOOPING; BLOCKS ITSELF, THEREBY   *
*                  NEVER RETURNING.                                   *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*        COMMENTS: USER NORMALLY USES THIS ROUTINE TO END A JOB.      *
*                                                                     *
***********************************************************************
         SPACE 1
XH       EQU   * .                 THE XH ROUTINE: HALT A JOB
         USING *,1
         LA    2,XHMSG1 .          SEND A MESSAGE TO *IBSUP
         SVC   C'S' .              SEND IT
XHLOOP   LA    2,XHMSG2 .          READY TO READ A REPLY
         SVC   C'R' .               WHICH NEVER COMES
         B     XHLOOP .            BUT IF IT DOES WERE READY
         DS    0F
XHMSG1   DC    CL8'*IBSUP' .       SAY TO *IBSUP
         DC    F'12' .             TWELVE CHARACTERS
         DC    C'PROGRAM HALT' .   SAYING WERE OK
XHMSG2   DS    CL8 .               WHO SENDS US A MESSAGE
         DC    F'1' .              ONE CHARACTER
         DS    CL1,0H .            WHICH GOES HERE
         EJECT
***********************************************************************
*                                                                     *
*                            XI ROUTINE                               *
*                                                                     *
*        FUNCTION: TO CHAIN A PCB ONTO PROCESS CHAINS                 *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS OF A PCB   *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: POINTER USED TO CHAIN PCB INTO ALL PCB CHAIN AND   *
*                  THIS GROUP CHAIN RIGHT AFTER RUNNING PCB; RETURN.  *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XI       EQU   * .                 THE XI ROUTINE: THREAD IN A PCB
         USING *,1
         L     10,PCBNPALL .       GET THE NEXT 'ALL' PCB
         ST    2,PCBNPALL .        STORE THIS PCB RIGNT AFTER MINE
         DROP  15
         USING PCB,10
         ST    2,PCBLPALL .        THE NEXT ONE DOWN POINTS BACK
         DROP  10
         USING PCB,2
         ST    15,PCBLPALL .       THIS PCB POINTS BACK
         ST    10,PCBNPALL .        AND FORWARD
         DROP  2
         USING PCB,15
         L     10,PCBNPTG .        GET NEXT "THIS GROUP" PCB
         ST    2,PCBNPTG .         RUNNING PCB POINTS TO NEW MEMBER
         DROP  15 .                 OF PROCESS GROUP
         USING PCB,10
         ST    2,PCBLPTG .         NEXT PCB DOWN POINTS BACK
         DROP  10
         USING PCB,2
         ST    15,PCBLPTG .        AND WE POINT BACKWARD
         ST    10,PCBNPTG .        AND FORWARD
         DROP  2
         LPSW  RETURN .            RETURN
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XJ ROUTINE                               *
*                                                                     *
*        FUNCTION: TO UNCHAIN A PCB FROM PROCESS CHAINS               *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS OF A PCB   *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: POINTERS TO PCB IN ALL PCB CHAIN AND THIS GROUP    *
*                  CHAIN MODIFIED WITHOUT FREEING STORAGE; RETURN.    *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: NO                                                 *
*                                                                     *
***********************************************************************
         SPACE 1
XJ       EQU   * .                 THE XJ ROUTINE: UNTHREAD A PCB
         USING *,1
         DROP  15
         USING PCB,2
         L     11,PCBLPALL .       GET PRECEDING PCB
         L     10,PCBNPALL .        AND FOLLOWING ONE IN "ALL"
         DROP  2 .                  CHAIN
         USING PCB,11
         ST    10,PCBNPALL .       LAST POINTS TO NEXT
         DROP  11
         USING PCB,10
         ST    11,PCBLPALL .       NEXT POINTS TO LAST
         DROP  10
         USING PCB,2
         L     11,PCBLPTG .        REDO FOR THIS GROUP PCB CHAIN
         L     10,PCBNPTG
         DROP  2
         USING PCB,11
         ST    10,PCBNPTG .        LAST POINTS TO NEXT
         DROP  11
         USING PCB,10
         ST    11,PCBLPTG .        NEXT POINTS TO LAST
         DROP  10
         LPSW  RETURN .            AND RETURN
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XN ROUTINE                               *
*                                                                     *
*        FUNCTION: TO FIND THE PCB FOR A PROCESS GIVEN ITS NAME ONLY  *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XNX        *
*                    XNX       DS 0D                                  *
*                    XNXNAME   DS CL8   NAME OF PROCESS               *
*                    XNXADDR   DS A     ADDRESS OF PCB                *
*   ROUTINES USED: NONE                                               *
*       PROCEDURE: SEARCH THIS GROUP PCB CHAIN FOR NAME; IF FOUND,    *
*                  STORE POINTER IN XNXADDR. IF NOT FOUND, STORE      *
*                  ZERO IN XNXADDR; RETURN.                           *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XN       EQU   * .                 THE XN ROUTINE: FIND A NAMED PCB
         USING *,1
         USING XNX,2 .             THE ARG LIST
         LR    10,15 .             FIRST PCB TO LOOK AT IS OURS
         DROP  15
         USING PCB,10
XNXLOOP  L     10,PCBNPTG .        LOOK AT NEXT PCB
         CLC   PCBNAME,XNXNAME .   HAS IT THE RIGHT NAME?
         BE    XNXFOUND .          IF YES, OH JOY.
         CR    10,15 .             IF NOT, ARE WE THROUGH?
         BNE   XNXLOOP .           IF NOT, TRY THE NEXT PCB
         LA    10,0 .              ELSE, IT'S NOT HERE
XNXFOUND ST    10,XNXADDR .        FOUND IT. SAY WHERE.
         LPSW  RETURN .            AND RETURN
         DROP  2,10
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XR ROUTINE                               *
*                                                                     *
*        FUNCTION: TO READ A MESSAGE                                  *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XRX        *
*                    XRX       DS 0D                                  *
*                    XRXNAME   DS CL8   NAME OF SENDER PROCESS        *
*                    XRXSIZE   DS F     SIZE OF MESSAGE TEXT          *
*                    XRXTEXT   DS C     TEXT OF MESSAGE               *
*   ROUTINES USED: XP, XEXC, XN, XCOM, XF                             *
*       PROCEDURE: USE XP ON MESSAGE SEMAPHORE RECEIVER TO SEE IF ANY *
*                  MESSAGES WAITING; IF NONE, PROCESS BLOCKED UNTIL   *
*                  THERE IS ONE; LOCK MESSAGE CHAIN; REMOVE A MESSAGE *
*                  FROM CHAIN AND UNLOCK IT; MOVE TEXT OF MESSAGE,    *
*                  PADDING WITH BLANKS OR TRUNCATING AS NECESSARY;    *
*                  INDICATE CORRECT MESSAGE LENGTH AND NAME OF        *
*                  MESSAGE SENDER; FREE STORAGE USED TO HOLD MESSAGE, *
*                  AND RETURN.                                        *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XR       EQU   * .                 THE XR ROUTINE: READ A MESSAGE
         USING *,1
         LR    7,2
         USING XRX,7 .             ARG LIST
         LA    2,PCBMSR .          SEE IF MESSAGES WAITING
         SVC   C'P'
         SVC   C'!' .              ENTER SMC SECTION
         LA    2,PCBMSC .          THEN LOCK THE MESSAGE CHAIN
         SVC   C'P'
         L     5,PCBFM .           GET THE FIRST MESSAGE
         USING MSG,5
         MVC   PCBFM,MSGNEXT .     REMEMBER THE NEXT
         SVC   C'V' .              UNLOCK THE MESSAGE CHAIN
         L     6,XRXSIZE .         GET THE BUFFER CAPACITY
*        S     6,=F'2' .           MINUS 1, MINUS 1
         S     6,LTGF2 .     ASMA: MINUS 1, MINUS 1 (for literal pool)
         MVI   XRXTEXT,C' ' .      MOVE IN A BLANK
         BM    XRNOB
         EX    6,XRFILL .          THEN FILL THE REST WITH BLANKS
XRNOB    LA    6,1(6) .            THEN GET PROPER BUFFER COUNT
         C     6,MSGSIZE .         COMPARE WITH MESSAGE LENGTH
         BL    XRTHEN .            IF LESS, HANDLE ACCORDINGLY
         L     6,MSGSIZE .         ELSE COUNT FOR MVC IS MESSAGE
         BCTR  6,0 .                SIZE MINUS ONE
XRTHEN   LTR   6,6 .               ANY CHARACTERS TO MOVE?
         BM    XRAFT .             IF NOT, DON'T
         EX    6,XRMOVE .          ELSE MOVE THEM
XRAFT    LA    6,1(6) .            THEN GET LENGTH
         ST    6,XRXSIZE .         STORE IT
         L     10,MSGSENDR .       GET SENDER'S PCB
         DROP  15
         USING PCB,10
         MVC   XRXNAME,PCBNAME .   AND STORE SENDER'S NAME
         L     6,MSGSIZE .         GET SIZE OF MESSAGE TEXT
         LA    6,LENMSG(6) .        ADD SIZE OF MESSAGE BLOCK
         LA    6,7(6) .            AND TRUNCATE
*        N     6,=F'-8' .          UP
         N     6,LTGFM8 .    ASMA: UP (for literal pool)
         LR    2,5 .               SET UP POINTER TO XFX
         USING XFX,2
         ST    5,XFXADDR .         STORE ADDRESS
         ST    6,XFXSIZE .         STORE SIZE
         SVC   C'F' .              AND FREE THE MESSAGE BLOCK
         SVC   C',' .              LEAVE SMC
         LPSW  RETURN .            AND RETURN
XRFILL   MVC   XRXTEXT+1,XRXTEXT . FILL WITH BLANKS
XRMOVE   MVC   XRXTEXT,MSGTEXT .   MOVE TEXT
         DROP  2,5,7,10
         USING PCB,15
         SPACE 3
***********************************************************************
*                                                                     *
*                            XS ROUTINE                               *
*                                                                     *
*        FUNCTION: TO SEND A MESSAGE                                  *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XSX        *
*                    XSX       DS 0D                                  *
*                    XSXNAME   DS CL8   NAME OF TARGET PROCESS        *
*                    XSXSIZE   DS F     SIZE OF TEXT                  *
*                    XSXTEXT   DS C     TEXT OF MESSAGE               *
*   ROUTINES USED: XP, XV, XEXC, XCOM, XA, XQUE                       *
*       PROCEDURE: USE XN TO GET POINTER TO PCB OF TARGET PROCESS;    *
*                  USE LENGTH OF MESSAGE AND XA TO ALLOCATE BLOCK FOR *
*                  MESSAGE; LOCK MESSAGE CHAIN OF TARGET PROCESS;     *
*                  PUT MESSAGE BLOCK AT END OF CHAIN; STORE SENDER    *
*                  NAME, SIZE, AND TEXT OF MESSAGE; UNLOCK CHAIN;     *
*                  INDICATE MESSAGE CHAIN IS ONE LONGER; RETURN.      *
*    ERROR CHECKS: IF NO PROCESS BY GIVEN NAME, ENTER XQUE.           *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XS       EQU   * .                 THE XS ROUTINE: SEND MESSAGES
         USING *,1
         LR    7,2
         USING XSX,7 .             ARG LIST
         LA    2,SATEMP .          READY TO CALL OUT
         USING XNX,2 .             ABOUT TO CALL XN
         MVC   XNXNAME,XSXNAME .   GIVE NAME OF TARGET PROCESS
         SVC   C'N' .              SEE WHERE IT IS
         L     4,XNXADDR .         GET THE POINTER
         LTR   4,4 .               IS THERE INDEED ONE?
         BZ    XSERR .             IF NOT, ERROR
         USING PCB,4
         DROP  2,15
         USING XAX,2 .             READY TO CALL XA
         SVC   C'!' .              ENTERING SMC SECTION
         L     3,XSXSIZE .         GET THE STATED SIZE
         LA    3,LENMSG(3) .       PLUS THE AMOUNT OF OVERHEAD
         LA    3,7(3) .            AND TRUNCATE
*        N     3,=F'-8' .          UP
         N     3,LTGFM8 .    ASMA: UP (for literal pool)
         ST    3,XAXSIZE .         THAT'S THE SIZE OF THE REGION TO
*        MVC   XAXALGN,=F'8' .     ALLOCATE, ON A DOUBLEWORD BOUND
         MVC   XAXALGN,LTGF8 .ASMA: ALLOCATE, ON A DOUBLEWORD BOUND (for literal pool)
         SVC   C'A' .              SO ALLOCATE ALREADY
         L     5,XAXADDR .         GET THE ADDRESS
         DROP  2
         LA    2,PCBMSC .          GET THE MESSAGE CHAIN SEMAPHORE
         SVC   C'P' .               AND LOCK IT
         LA    8,PCBFM .           THEN START DOWN THE MESSAGE
         L     9,PCBFM .            CHAIN
         USING MSG,9
XSLOOP   LTR   9,9 .               ARE WE THROUGH?
         BZ    XSADD .             IF SO ADD IT ON
         LA    8,MSGNEXT .         IF NOT, ON TO THE NEXT
         L     9,MSGNEXT
         B     XSLOOP .            AND TRY AGAIN
XSADD    ST    5,0(8) .            CHAIN OURS ON THE END
         DROP  9
         USING MSG,5
*        MVC   MSGNEXT,=A(0) .     SET NEXT POINTER NULL
         MVC   MSGNEXT,LTG0 .ASMA: SET NEXT POINTER NULL (for literal pool)
         ST    15,MSGSENDR .       STORE THE SENDER
         L     6,XSXSIZE .         GET THE TEXT LENGTH
         ST    6,MSGSIZE .         AND STORE IT
         BCTR  6,0 .               ONE LESS
         LTR   6,6 .               TEST LENGTH
         BM    XSAFT .             IF ZERO, NOTHING TO MOVE
         EX    6,XSMOVE .          ELSE, MOVE IT
XSAFT    SVC   C'V' .              UNLOCK THE MESSAGE CHAIN
         LA    2,PCBMSR .          THEN SAY THERE'S
         SVC   C'V' .               ONE MORE MESSAGE
         SVC   C',' .              LEAVE SMC SECTION
         LPSW  RETURN .            AND RETURN
XSERR    SVC   C'?'
XSMOVE   MVC   MSGTEXT,XSXTEXT .   THE MOVE FOR THE TEXT
         DROP  4,5,7
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XY ROUTINE                               *
*                                                                     *
*        FUNCTION: TO START A PROCESS                                 *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XYX        *
*                    XYX       DS 0D                                  *
*                    XYXNAME   DS CL8   NAME OF PROCESS TO BE STARTED *
*                    XYXADDR   DS A     STARTING ADDRESS OF PROCESS   *
*   ROUTINES USED: XN, XEXC, XCOM, XQUE                               *
*       PROCEDURE: USE XN TO GET POINTER TO THE PCB OF PROCESS TO BE  *
*                  STARTED; STORE IN PCB INTERRUPT SAVE AREA REGISTERS*
*                  AND PSW WITH STARTING ADDRESS AS SENT FROM STARTING*
*                  PROCESS; STOPPED BIT TURNED OFF; RETURN.           *
*    ERROR CHECKS: IF NO PROCESS BY GIVEN NAME, XQUE ENTERED.         *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XY       EQU   * .                 THE XY ROUTINE: START A PROCESS
         USING *,1
         LR    7,2
         USING XYX,7 .             THE ARG LIST
         LA    2,SATEMP .          READY TO CALL OUT
         USING XNX,2
         MVC   XNXNAME,XYXNAME .   GIVE XN A NAME
         SVC   C'N' .              CALL XN
         L     10,XNXADDR .        WHERE IS THE PCB?
         LTR   10,10 .              OR IS THERE ONE?
         BZ    XYERR .             IF NOT, OH HISS BOO
         DROP  2,14,15
         USING PCB,10
         LA    13,PCBISA .         GET INTO THAT PCB'S ISA
         USING SA,13
         MVC   SAPSW,(SAPSW-SA)(14) . GIVE IT THE CALLER'S PSW
         MVC   SAPSW+5(3),XYXADDR+1 . BUT AT THE REQUESTED ADDRESS
         MVC   SAREGS,(SAREGS-SA)(14) .GIVE IT HIS REGISTERS
         MVI   PCBSTOPT,X'00' .    IT'S NO LONGER STOPPED
         LPSW  RETURN .            AND RETURN
XYERR    SVC   C'?' .              WE DONE BAD
         DROP  7,10,13
         USING SA,14
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XZ ROUTINE                               *
*                                                                     *
*        FUNCTION: TO STOP A PROCESS                                  *
*       DATABASES: UPON ENTRY, REGISTER 2 CONTAINS ADDRESS XZX        *
*                    XZX       DS 0D                                  *
*                    XZXNAME   DS CL8   NAME OF PROCESS TO BE STOPPED *
*   ROUTINES USED: XN, XEXC, XCOM, XQUE, XP                           *
*       PROCEDURE: CHECK THAT USER PROCESS CAN'T STOP SYSTEM          *
*                  PROCESS; USE XN TO GET PCB POINTER; IF IN SMC, SET *
*                  STOP WAITING BIT AND BLOCK SELF UNTIL STOP         *
*                  PERFORMED; ELSE SET STOPPED BIT, AND RETURN.       *
*    ERROR CHECKS: IF NO PROCESS BY GIVEN NAME OR USER TRIES TO       *
*                  STOP A SYSTEM PROCESS, XQUE ENTERED.               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XZ       EQU   * .                 THE XZ ROUTINE: STOP A PROCESS
         USING *,1
         LR    7,2
         USING XZX,7 .             ARG LIST
         CLI   PCBNAME,C'*' .      IS STOPPER A * PROCESS
         BE    XZFINE .            THAT'S OK
         CLI   XZXNAME,C'*' .       IF NOT, IS STOPPEE A * ?
         BE    XZERR .             CAN'T DO THAT
XZFINE   LA    2,SATEMP .          READY TO CALL OUT
         USING XNX,2 .             WILL CALL XN
         MVC   XNXNAME,XZXNAME .   GIVE IT THE NAME
         SVC   C'N' .              AND DO THE CALL
         L     10,XNXADDR .        GET THE PCB'S ADDRESS
         LTR   10,10 .             SEE IF NULL
         BZ    XZERR .             IF SO, ERROR
         SVC   C'!' .              ENTER SMC
         DROP  2,15
         USING PCB,10
XZSTOP   CLI   PCBINSMC,X'00' .    SEE IF IN SMC
         BNE   XZINSMC .           IF SO, BAD
         MVI   PCBSTOPT,X'FF' .    ELSE JUST STOP IT
         SVC   C',' .              LEAVE SMC
         LPSW  RETURN .            AND RETURN
XZINSMC  MVI   PCBSW,X'FF' .       IF IN SMC, SAY STOP WAITING
         LA    2,PCBSRS .          AND STOP OURSELVES AGAINST
         SVC   C'P' .               A SEMAPHORE
         B     XZSTOP .            THEN WE CAN REALLY STOP IT
XZERR    SVC   C'?' .              AN ERROR
         DROP  10,7
         USING PCB,15
         EJECT
***********************************************************************
*                                                                     *
*                            XQUE ROUTINE                             *
*                                                                     *
*        FUNCTION: TO SIGNAL ERROR CONDITION                          *
*       DATABASES: NONE                                               *
*   ROUTINES USED: XR, XS                                             *
*       PROCEDURE: SEND MESSAGE TO SUPERVISOR PROCESS FOR THIS JOB    *
*                  INDICATING ABNORMAL TERMINATION; TRY TO READ       *
*                  MESSAGES, FOREVER LOOPING; BLOCK ITSELF, THEREBY   *
*                  NEVER RETURNING.                                   *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: OFF                                                *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
XQUE     EQU   * .                 THE XQUE ROUTINE: ERROR!
         USING *,1
         LA    2,XQUEM1 .          SEND AN ERROR MESSAGE TO *IBSUP
         SVC   C'S'
XQUELOOP LA    2,XQUEM2 .          WAIT FOR REPLY
         SVC   C'R'
         B     XQUELOOP .          BUT IGNORE IT
         DS    0F
XQUEM1   DC    CL8'*IBSUP'
         DC    F'12'
         DC    CL12'PROGRAM FLOP'
XQUEM2   DS    CL8
         DC    F'1'
         DS    CL1,0H
         DROP  14,15
         EJECT
***********************************************************************
*                                                                     *
*                           INPUT/OUTPUT ROUTINES                     *
*                                                                     *
***********************************************************************
         SPACE 1
***********************************************************************
*                                                                     *
*             SYSTEM SUPPLIED DEVICE HANDLER FOR READERS              *
*                                                                     *
***********************************************************************
         SPACE 1
RDRHANDL EQU   * .                 THE READER HANDLER
         USING UCB,3 .             STARTED WITH REG3 -> UCB
         BALR  1,0
         USING *,1 .               ESTABLISH ADDRESSING
         LA    2,RDRHSEM .         LOCK OURSELVES UNTIL WE SET UP
         SVC   C'P' .               AN AUTOMATIC STORAGE AREA
         LA    2,RDRHAAS .         READY TO ALLOCATE
         USING XAX,2
         SVC   C'E' .              ALLOCATE
         L     12,XAXADDR .        GET A PTR
         DROP  2
         LA    2,RDRHSEM .         AND UNBLOCK OURSELVES
         SVC   C'V'
         SRL   4,16 .              SHIFT KEY
         SR    10,10 .             CLEAR REG 10
         USING RDRHAS,12 .         AUTOMATIC AREA
         MVI   JOBBIT,X'00' .      INITIALIZE
         LA    6,RDRHCCB .         GET PTR TO CCB
RDRHLOOP LA    2,RDRHMSG .         TRY TO READ A MESSAGE
         USING XRX,2
*        MVC   XRXSIZE,=F'8' .     WE CAN TAKE 8 CHARS
         MVC   XRXSIZE,LTGF8 .ASMA: WE CAN TAKE 8 CHARS (for literal pool)
         SVC   C'R' .              READ IT
*        CLC   =C'READ',XRXTEXT .  IF FIRST WORD IS READ, OK
         CLC   LTGREAD,XRXTEXT .ASMA: IF FIRST WORD IS READ, OK (for literal pool)
         BNE   RDRHLOOP .          ELSE IGNORE
         L     5,XRXTEXT+4 .       GET 2ND WORD OF TEXT
         DROP  2
         LA    2,UCBUS .           LOCK THE UCB AND IT'S UNIT
         SVC   C'P'
         LA    2,RDRHMSG .         RESET ADDRESSING POINTER
         USING XRX,2
         CLI   JOBBIT,X'FF' .      HAVE WE JUST READ $JOB CARD?
         BNE   RDRHMORE .          IF NO, GO CHECK PROTECTION, ELSE
         CLI   XRXNAME,C'*' .      IS JSP CALLING US?
         BNE   RDRHNO .            IF NOT, TELL HIM NO.
         MVC   0(80,5),RDRHTEMP .  IF IT IS, GIVE JSP THE $JOB CARD
         MVI   JOBBIT,X'00' .      SAY WE DON'T HAVE $JOB WAITING
         B     RDRHSOK .            AND SEND MESSAGE BACK
         DROP  2
RDRHMORE CLI   RDRHMSG,C'*' .      IS SYSTEM CALLING?
         BE    RDRHPOK .           THEN PROTECTION OK, ELSE
         LR    11,5 .              GET ADDRESS THAT'S TO HOLD CARD,
         N     11,PROTCON1 .       GET THE 2K BOUNDARY
         ISK   10,11 .             FIND STORAGE KEY
         CR    10,4 .              DOES IT MATCH OURS?
         BNE   RDRHNO .            IF NOT, TELL HIM NO
         LA    11,79(5) .          CHECK LAST BYTE ADDR OF CARD
         N     11,PROTCON1 .       GET THE 2K BOUNDARY
         ISK   10,11 .             FIND STORAGE KEY
         CR    10,4 .              DOES IT MATCH OURS?
         BNE   RDRHNO .            IF NOT, TELL HIM NO
RDRHPOK  N     5,CCBCON1 .         MAKE ADDRESS INTO
         ST    5,RDRHCCB .         A CCW (OR CCB)
         OI    RDRHCCB,X'02'
*        MVC   RDRHCCB+4,=F'80' .  WE'LL READ EIGHTY CHARACTERS
         MVC   RDRHCCB+4,LTGF80 .ASMA: WE'LL READ EIGHTY CHARACTERS (for literal pool)
*        MVC   UCBCSW(4),=A(0) .   CLEAR THE LAST CSW THERE
         MVC   UCBCSW(4),LTG0 .  ASMA: CLEAR THE LAST CSW THERE (for literal pool)
*        MVC   UCBCSW+4(4),=A(0) 
         MVC   UCBCSW+4(4),LTG0  ASMA: for literal pool
         LA    2,CAWSEM .          LOCK THE CAW
         SVC   C'P'
         ST    6,CAW .             THAT'S THE CAW
         L     7,UCBADDR .         GET THE UNIT ADDRESS
         SIO   0(7) .              START THE I/O
         BNZ   RDSTATUS .          BRANCH IF SIO UNSUCCESSFUL
         SVC   C'V' .              THEN UNLOCK THE CAW
RDRHWAIT LA    2,UCBWS .           NOW WAIT FOR AN INTERRUPT
         SVC   C'P'
         TM    UCBCSW+4,X'05' .    CHECK THE STATUS
         BZ    RDRHWAIT .          IF NOT FINISHED, WAIT
         TM    UCBCSW+4,X'01' .    CHECK FOR EXCEPTION
         BZ    RDRHOK .            IF NOT, ALL IS GROOVY
*RDRHNO  MVC   RDRHM+12(2),=C'NO' .ELSE MESSAGE BACK IS NO
RDRHNO   MVC   RDRHM+12(2),LTGNO .ASMA: ELSE MESSAGE BACK IS NO (for literal pool)
         B     RDRHSEND .          GET READY TO SEND
RDRHOK   CLI   RDRHMSG,C'*' .      IS THE SYSTEM CALLING?
         BE    RDRHSOK .           THAT'S FINE. OTHERWISE,
*        CLC   =C'$JOB,',0(5) .    WAS IT A $JOB CARD?
         CLC   LTGJOB,0(5) . ASMA: WAS IT A $JOB CARD? (for literal pool)
         BE    ENDADATA .          OOPS! WE HIT END OF DATA STREAM
*RDRHSOK  MVC   RDRHM+12(2),=C'OK' .GROOVINESS MESSAGE
RDRHSOK  MVC   RDRHM+12(2),LTGOK . ASMA: GROOVINESS MESSAGE
*RDRHSEND MVC   RDRHM+8(4),=F'2' .  SAY THERE ARE 2 CHARACTERS
RDRHSEND MVC   RDRHM+8(4),LTGF2 .ASMA: SAY THERE ARE 2 CHARACTERS (for literal pool)
         MVC   RDRHM+0(8),RDRHMSG+0 . SEND BACK TO SAME GUY
         LA    2,UCBUS .           NOW UNLOCK UCB AND UNIT
         SVC   C'V'
         LA    2,RDRHM .           SET UP MESSAGE
         SVC   C'S' .               AND SEND IT
         B     RDRHLOOP
*ENDADATA MVC   RDRHM+12(2),=C'NO' . TELL USER NO MORE CARDS
ENDADATA MVC   RDRHM+12(2),LTGNO .ASMA: TELL USER NO MORE CARDS (for literal pool)
         MVC   RDRHTEMP(80),0(5) . SAVE THE $JOB CARD
         MVI   0(5),C' ' .         BLANK OUT THE USER'S COPY
         MVC   1(79,5),0(5)
         MVI   JOBBIT,X'FF' .      INDICATE WE HAVE A NEW $JOB CARD
         B     RDRHSEND .          AND SEND THE MESSAGE BACK
RDSTATUS SVC   C'V' .              UNLOCK THE CAW
         LA    2,UCBWS .           AND WAIT FOR AN INTERRUPT
         SVC   C'P'
         B     RDRHPOK .           AND TRY TO RESTART THE I/O
         DROP  3,12
         SPACE 1
RDRHSEM  DC    F'1,0'
CCBCON1  DC    X'00FFFFFF' MASK
PROTCON1 DC    X'00FFF800'
RDRHAAS  DC    A(LENRDRHA) ALLOCATE ARGLIST FOR STORAGE
         DC    F'0'
         DC    F'8'
         SPACE 3
***********************************************************************
*                                                                     *
*             SYSTEM SUPPLIED DEVICE HANDLER FOR PRINTERS             *
*                                                                     *
***********************************************************************
         SPACE 1
PRTHANDL EQU   * .                 THE PRINTER HANDLER
         USING UCB,3 .             ENTERED WITH REG3 -> THE UCB
         BALR  1,0
         USING *,1 .               ESTABLISH ADDRESSING
         LA    2,PRTHSEM .         LOCK UNTIL ALLOCATE STORAGE
         SVC   C'P' .
         LA    2,PRTHAAS .         READY TO ALLOCATE
         USING XAX,2
         SVC   C'E' .              ALLOCATE
         L     12,XAXADDR .        GET THE ADDRESS
         DROP  2
         LA    2,PRTHSEM .
         SVC   C'V'                UNLOCK TO ROUTINE
         SRL   4,16 .              SHIFT KEY
         SR    10,10 .             CLEAR REG 10
         USING PRTHAS,12 .         ADDRESSING IN THE AUTO AREA
         LA    6,PRTHCCB .         MAKE A CAW
PRTHLOOP LA    2,PRTHMSG .         READY TO READ A MESSAGE
         USING XRX,2
*        MVC   XRXSIZE,=F'8' .     WE CAN TAKE 8 CHARACTERS
         MVC   XRXSIZE,LTGF8 .ASMA: WE CAN TAKE 8 CHARACTERS (for literal pool)
         SVC   C'R' .              READ IT
         L     5,XRXTEXT+4 .       LOAD THE ADDRESS
*        CLC   =C'PRIN',XRXTEXT .  IS IT A PRIN REQUEST?
         CLC   LTGPRIN,XRXTEXT .ASMA: IS IT A PRIN REQUEST? (for literal pool)
         BE    PRTHPRIN
*        CLC   =C'STC1',XRXTEXT .  OR A SKIP REQUEST?
         CLC   LTGSKIP,XRXTEXT .ASMA: OR A SKIP REQUEST? (for literal pool)
         BE    PRTHSTC1
         B     PRTHLOOP .          IF NEITHER, IGNORE
         DROP  2
PRTHPRIN LA    2,UCBUS
         SVC   C'P' .              LOCK THE UCB AND UNIT
         CLI   PRTHMSG,C'*' .      IS SYSTEM CALLING?
         BE    PRTHPOK .           THEN PROTECTION OK. ELSE
         LR    11,5 .              GET ADDRESS THAT'S TO HOLD MSG,
         N     11,PROTCON1 .       GET THE 2K BOUNDARY
         ISK   10,11 .             FIND STORAGE KEY
         CR    10,4 .              DOES IT MATCH OURS?
         BNE   PRTHNO .            IF NOT, TELL HIM NO
         LA    11,131(5) .         CHECK LAST BYTE ADDRESS OF LINE
         N     11,PROTCON1 .       GET THE 2K BOUNDARY
         ISK   10,11 .             FIND STORAGE KEY
         CR    10,4 .              DOES IT MATCH OURS?
         BNE   PRTHNO .            IF NOT, TELL HIM NO
PRTHPOK  N     5,CCBCON1 .         MAKE A WRITE REQUEST
         ST    5,PRTHCCB .         FOR THE CCB
         OI    PRTHCCB,X'09' .     PRINT COMMAND CODE
*        MVC   PRTHCCB+4,=F'132' . WE'LL PRINT 132 CHARACTERS
         MVC   PRTHCCB+4,LTGF132 .ASMA: WE'LL PRINT 132 CHARACTERS (for literal pool)
         B     PRTHCOMM .          BRANCH TO COMMON SECTION
*PRTHSTC1 MVC   PRTHCCB(8),=X'8900000020000001' SKIP TO TOP OF PAGE
PRTHSTC1 MVC   PRTHCCB(8),LTGSCMD  ASMA: SKIP TO TOP OF PAGE (for literal pool)
         LA    2,UCBUS
         SVC   C'P' .              LOCK THE UCB AND UNIT
PRTHCOMM LA    2,CAWSEM .          LOCK THE CAW
         SVC   C'P'
         ST    6,CAW .             STORE OUR CAW
*        MVC   UCBCSW(4),=A(0) .   CLEAR THE LAST CSW THERE
         MVC   UCBCSW(4),LTG0 .ASMA: CLEAR THE LAST CSW THERE (literal pool)
*        MVC   UCBCSW+4(4),=A(0)
         MVC   UCBCSW+4(4),LTG0
         L     7,UCBADDR .         GET THE ADDRESS
         SIO   0(7) .              START THE I/O
         BNZ   PTSTATUS .          BRANCH IF SIO UNSUCCESSFUL
         SVC   C'V' .              AND UNLOCK THE CAW
PRTHWAIT LA    2,UCBWS .           START TO WAIT
         SVC   C'P'
         TM    UCBCSW+4,X'05' .    IS THE UNIT READY?
         BZ    PRTHWAIT .          IF NOT, ITS STILL ON. WAIT
         TM    UCBCSW+4,X'01' .    WAS THERE AN EXCEPTION?
         BZ    PRTHOK .            IF NOT, GOOD
*PRTHNO   MVC   PRTHM+12(2),=C'NO' .THERE WAS, SO SAY SO
PRTHNO   MVC   PRTHM+12(2),LTGNO .ASMA: THERE WAS, SO SAY SO (literal pool)
         B     PRTHSEND
*PRTHOK   MVC   PRTHM+12(2),=C'OK' .NO ERRORS
PRTHOK   MVC   PRTHM+12(2),LTGOK .ASMA: NO ERRORS (literal pool)
*PRTHSEND MVC   PRTHM+8(4),=F'2' .  SENDING 2 CHARACTERS
PRTHSEND MVC   PRTHM+8(4),LTGF2 . ASMA: SENDING 2 CHARACTERS (literal pool)
         MVC   PRTHM+0(8),PRTHMSG+0 . SEND TO OUR SENDER
         LA    2,UCBUS
         SVC   C'V' .              UNLOCK THE UCB
         LA    2,PRTHM
         SVC   C'S' .              SEND IT
         B     PRTHLOOP .          AND READ ANOTHER MESSAGE
PTSTATUS SVC   C'V' .              UNLOCK THE CAW
         LA    2,UCBWS .           AND WAIT FOR THE INTERRUPT
         SVC   C'P'
         B     PRTHCOMM .          AND TRY TO RESTART THE I/O
         DROP  3,12
         SPACE 2
PRTHSEM  DC    F'1,0' LOCK
PRTHAAS  DC    A(LENPRTHA) XA ARG LIST FOR AUTO STORAGE
         DC    F'0'
         DC    F'8'
         EJECT
***********************************************************************
*                                                                     *
*             SYSTEM ROUTINE FOR USER SUPPLIED DEVICE HANDLER         *
*                                                                     *
***********************************************************************
         SPACE 1
EXCPHNDL EQU   * .                 EXCP DEVICE HANDLER
         USING UCB,3 .             WILL HAVE REG3 -> UCB
         BALR  1,0
         USING *,1 .               ESTABLISH ADDRESSING
         LA    2,EXCPHSEM .        LOCK OURSELVES UNTIL WE HAVE
         SVC   C'P' .              SET UP AUTOMATIC STORAGE
         LA    2,EXCPHAAS .        READY TO ALLOCATE
         USING XAX,2
         SVC   C'E' .              ALLOCATE
         L     12,XAXADDR .        GET POINTER TO AUTO STORAGE
         DROP  2
         LA    2,EXCPHSEM .        AND UNLOCK OURSELVES
         SVC   C'V'                UNLOCK TO ROUTINE
         LR    4,11
         SLL   4,8 .               SHIFT KEY FOR CAW
         USING EXCPHAS,12 .        FOR ADDRESSING AUTO AREA
EXCPLOOP LA    2,EXCPHMSG .        TRY TO READ A MESSAGE
         USING XRX,2
*        MVC   XRXSIZE,=F'12' .    WE'LL TAKE 12 CHARACTERS
         MVC   XRXSIZE,LTGF12 .ASMA: WE'LL TAKE 12 CHARACTERS (literal pool)
         SVC   C'R'
*        CLC   =C'EXCP',XRXTEXT .  IS IT AN EXCP MESSAGE?
         CLC   LTGEXCP,XRXTEXT .ASMA: IS IT AN EXCP MESSAGE? (literal pool)
         BNE   EXCPLOOP .          IF NOT, IGNORE IT
         L     5,XRXTEXT+4 .       REG 5 CONTAINS CHAN AND DEV
         L     6,XRXTEXT+8 .       REG 6 CONTAINS ADDR OF CCWS
         DROP  2
         LA    7,UCBTABLE .        GET PTR TO UCB TABLE
EXCPCOMP C     5,0(7) .            COMPARE UNIT ADDRESS
         BE    EXCPFIND .          THAT'S THE UCB WE WANT
         LA    7,UCBLENG(7) .      GET PTR TO NEXT UCB
*        C     7,=A(UCBTBEND) .    ARE WE THROUGH WITH TABLE?
         C     7,LTGUCBND .  ASMA: ARE WE THROUGH WITH TABLE? (literal pool)
         BNE   EXCPCOMP .          IF NOT, LOOK SOME MORE
         SVC   C'?' .              ELSE ERROR
EXCPFIND LR    3,7 .               SET REG 3 TO UCB PTR
         LA    2,UCBUS
         SVC   C'P' .              LOCK THE UCB
         OR    6,4 .               OR IN THE USER'S KEY
*        MVC   UCBCSW(4),=A(0) .   CLEAR THE LAST CSW THERE
         MVC   UCBCSW(4),LTG0 .ASMA: CLEAR THE LAST CSW THERE (literal pool)
*        MVC   UCBCSW+4(4),=A(0)
         MVC   UCBCSW+4(4),LTG0  ASMA: literal pool
         LA    2,CAWSEM
         SVC   C'P' .              LOCK CAW
         ST    6,CAW .             STORE OUR CAW
         SIO   0(5) .              START THE I/O
         SVC   C'V' .              UNLOCK THE CAW
EXCPWAIT LA    2,UCBWS .           NOW WAIT FOR AN INTERRUPT
         SVC   C'P'
         MVC   EXCPHM+12(8),UCBCSW . GIVE USER HIS CSW
*        MVC   EXCPHM+8(4),=F'12'
         MVC   EXCPHM+8(4),LTGF12 .ASMA: literal pool
         MVC   EXCPHM(8),EXCPHMSG
         LA    2,EXCPHM
         SVC   C'S' .              AND SENT THE MESSAGE
         LA    2,EXCPHMSG .        AND WAIT FOR A REPLY
         USING XRX,2
*        MVC   XRXSIZE(4),=F'8' .  FROM THE USER
         MVC   XRXSIZE(4),LTGF8 .ASMA: FROM THE USER (literal pool)
         SVC   C'R'
*        CLC   =C'OK',XRXTEXT .    AM I DONE?
         CLC   LTGOK,XRXTEXT .ASMA: AM I DONE? (literal pool)
         BE    EXCPDONE
*        CLC   =C'AGAIN',XRXTEXT . DOES HE WANT ANOTHER CSW?
         CLC   LTGAGAIN,XRXTEXT .ASMA: DOES HE WANT ANOTHER CSW? (literal pool)
         BE    EXCPWAIT
         SVC   C'?' .              WRONG MESSAGE
         DROP  2
EXCPDONE LA    2,UCBUS .           UNLOCK UNIT
         SVC   C'V'
         B     EXCPLOOP .          AND GET ANOTHER MESSAGE
         DROP  3,12
EXCPHSEM DC    F'1,0'
EXCPHAAS DC    A(LENEXCPA) .       ALLOCATION OF AUTO STORAGE
         DC    F'0'
         DC    F'8'
         SPACE 3
*        LTORG               ASMA: Literal pools are not supported by ASMA
LTGF1    DC    F'1'
LTGF2    DC    F'2'
LTGF8    DC    F'8'
LTGF12   DC    F'12'
LTGF80   DC    F'80'
LTGF132  DC    F'132'
LTGFM8   DC    F'-8'
LTGXA    DC    A(XA)
LTG0     DC    A(0)
LTGPCBL  DC    A(LENPCB)
LTGUCBND DC    A(UCBTBEND)
LTGAGAIN DC    C'AGAIN'
LTGEXCP  DC    C'EXCP'
LTGJOB   DC    C'$JOB,'
LTGNO    DC    C'NO'
LTGOK    DC    C'OK'
LTGPRIN  DC    C'PRIN'
LTGREAD  DC    C'READ'
LTGSKIP  DC    C'STC1'
LTGSCMD  DC    X'8900000020000001'
         EJECT
***********************************************************************
*                                                                     *
*             UNIT CONTROL BLOCKS                                     *
*                                                                     *
***********************************************************************
         SPACE 1
UCBTABLE DS    0F .                TABLE OF UNIT CONTROL BLOCKS
*                          UCB FOR READER 1
UCBRDR1  DC    X'00000012' .       DEVICE ADDRESS,
         DC    F'1,0' .            USER SEMAPHORE,
         DC    F'0,0' .            WAIT SEMAPHORE,
         DC    F'0,0' .            CHANNEL STATUS WORD
         DC    X'00'
         DS    0F
*                          UCB FOR PRINTER 1
UCBPRT1  DC    X'00000010' .       DEVICE ADDRESS,
         DC    F'1,0' .            USER SEMAPHORE,
         DC    F'0,0' .            WAIT SEMAPHORE,
         DC    F'0,0' .            CHANNEL STATUS WORD
         DC    X'00'
         DS    0F
*                          UCB FOR READER 2
UCBRDR2  DC    X'0000000C' .       DEVICE ADDRESS,
         DC    F'1,0' .            USER SEMAPHORE,
         DC    F'0,0' .            WAIT SEMAPHORE,
         DC    F'0,0' .            CHANNEL STATUS WORD
         DC    X'00'
         DS    0F
*                          UCB FOR PRINTER 2
UCBPRT2  DC    X'0000000E' .       DEVICE ADDRESS,
         DC    F'1,0' .            USER SEMAPHORE,
         DC    F'0,0' .            WAIT SEMAPHORE,
         DC    F'0,0' .            CHANNEL STATUS WORD
         DC    X'00'
         DS    0F
UCBTBEND EQU   *
         EJECT
***********************************************************************
*                                                                     *
*             I/O INTERRUPT HANDLER                                   *
*                                                                     *
***********************************************************************
         SPACE 1
IOHANDL  EQU   * .                 THE I/O INTERRUPT HANDLER
         STM   0,15,IOHSAVE .      SAVE REGISTERS
         BALR  1,0
         USING *,1 .               ESTABLISH ADRESSING
         NI    IOOLD+1,X'FD' .     TURN OFF WAIT BIT
*        L     6,=A(UCBTABLE) .    GET POINTER TO UCB TABLE
         L     6,LTGUCBA .   ASMA: GET POINTER TO UCB TABLE (literal pool)
IOCOMP   CLC   2(2,6),IOOLD+2 .    COMPARE DEVICE AND CHANNEL
         BE    IODEVFND .          IF EQUAL, REG 6 INDICATES PTR
         LA    6,UCBLENG(6) .      INCREMENT TO NEXT ENTRY
*        C     6,=A(UCBTBEND) .    ARE WE AT END OF TABLE?
         C     6,LTGUCBN .   ASMA: ARE WE AT END OF TABLE? (literal pool)
         BNE   IOCOMP .            IF NOT DONE, TRY NEXT UCB
         B     IOBACK .            ELSE, IGNORE IT
         USING UCB,6 .             IT'S A UCB PTR
IODEVFND MVC   UCBCSW(4),CSW .     MOVE IN THE NEW CSW
         L     7,CSW+4 .           GET STATUS BYTE
         O     7,UCBCSW+4 .        OR IN NEW STATUS INFORMATION
         ST    7,UCBCSW+4 .         AND STORE IT BACK
         MVC   UCBCSW+6(2),CSW+6 . MOVE IN BYTE COUNT
         LA    2,UCBWS
         CLI   UCBFPR,X'00' .      IS FAST PROCESSING
         BE    IONOFPR .            REQUIRED? IF NOT, RETURN
         L     15,RUNNING .        IF SO, STOP GUY NOW RUNNING
         USING PCB,15
         CLI   PCBBLOKT,X'FF' .    IS ANYONE REALLY RUNNING?
         BE    IOWAIT .            IF NOT, START UP SLEEPER
         LA    13,PCBISA .         IF SO, STOP RUNNING PROCESS
         USING SA,13
         MVC   SAPSW,IOOLD .       SAVE PROCESS WHICH WAS
         MVC   SAREGS,IOHSAVE .     INTERRUPTED
         DROP  13,15
IOWAIT   MVI   NEXTTRYM,X'00' .    MAKE NEXTTRY NOT MODIFIED
         SVC   C'V' .              SO CAN FAST PROCESS SLEEPER
         SVC   C'.' .              GO PROCESS IT RIGHT AWAY
IONOFPR  SVC   C'V' .              AND WAKE UP THE SLEEPER
IOBACK   LM    0,15,IOHSAVE .      RELOAD OUR REGISTERS
         LPSW  IOOLD .             AND STEALTHILY RETURN
         DROP  1,6
         EJECT
***********************************************************************
*                                                                     *
*             IPL ENTERED ROUTINE                                     *
*                                                                     *
*        FUNCTION: TO INITIALIZE SYSTEM PARAMETERS, SET STORAGE KEYS, *
*                  AND CREATE MULTIPLE JOB STREAMS.                   *
*                                                                     *
***********************************************************************
         SPACE 1
IPLRTN   EQU   * .                 THE IPL-ENTERED ROUTINE
         BALR  1,0
         USING *,1 .               ESTABLISH ADDRESSING
         LA    15,IPLPCB .         I'M RUNNING
         ST    15,RUNNING .        INITIALIZE 'RUNNING'
         ST    15,NEXTTRY .        INITIALIZE 'NEXTTRY'
*        MVC   VERYEND,=A(0,CORESIZE-(VERYEND-PROGRAM)) FREE CORE
         MVC   VERYEND,LTGCORN .ASMA: FREE CORE (literal pool)
         LA    3,8 .               SET ZERO KEY AND FETCH PROTECT
         L     2,CORESIZ .         START PAST THE LAST BLOCK
*IPLCL    S     2,=F'2048' .        GO TO THE PREVIOUS BLOCK
IPLCL    S     2,LTGF2048 .  ASMA:  GO TO THE PREVIOUS BLOCK (literal pool)
         BM    IPLTH .             IF NEGATIVE, WE'RE THROUGH HERE
         SSK   3,2 .               ELSE SET THE STORAGE KEY TO
         B     IPLCL .              ZERO, AND WORK BACKWARDS
IPLTH    SR    4,4 .               INDEX IN TABLES FOR INPUT STREAM
         L     5,STREAMS .         HOW MANY STREAMS?
IPLLOOP  LA    2,IPLAPCBS .        READY TO ALLOCATE A PCB
         USING XAX,2
         SVC   C'A' .              ALLOCATE
         L     2,XAXADDR .         GET THE ADDRESS
         MVC   0(TYPLEN,2),TYPPCB .MAKE IT LOOK LIKE A PCB
         SVC   C'I' .              CHAIN IT ON
         USING PCB,2
         ST    2,PCBNPTG .         BUT PUT IT IN A GROUP BY ITSELF
         ST    2,PCBLPTG
         DROP  2
         USING PCB,15
         ST    15,PCBLPTG .        LIKEWISE FOR THE IPL PCB
         ST    15,PCBNPTG
         DROP  15
         USING PCB,2
         LA    8,PCBISA .          GET THE NEW PCB'S ISA
         USING SA,8
         LA    9,SAREGS .          ABOUT TO FIX INIT REGS
         USING REGS,9
         LA    10,UCBTAB
         AR    10,4
         MVC   REG3,0(10) .        REG3 -> (RDRUCB,PRTUCB)
         MVC   REG4,KEYTAB-UCBTAB(10) . REG4 = KEY
         DROP  9
         LA    4,4(4) .            GO TO NEXT JOB STREAM
         BCT   5,IPLLOOP .         DO FOR EACH STREAM
         SVC   C'.' .              THEN ENTER TRAFFIC CONTROLLER
         SPACE 1
STREAMS  DC    F'1' .              NUMBER OF STREAMS
         SPACE 1
UCBTAB   EQU   * .                 TABLE OF PTRS TO UCB BLOCKS
         DC    A(UCBLP1)
         DC    A(UCBLP2)
         SPACE 1
KEYTAB   EQU   * .                 TABLE OF PROTECTION KEYS
         DC    X'00100000'
         DC    X'00200000'
         SPACE 1
UCBLP1   DC    A(UCBRDR1,UCBPRT1)
UCBLP2   DC    A(UCBRDR2,UCBPRT2)
         SPACE 1
         DS    0D
IPLPCB   DC    CL8' ' .            IPL ROUTINE PCB
         DC    4A(IPLPCB)
         DC    X'FF000000' .       INITIALIZED FLAGS
         DC    F'1,0'
         DC    5F'0,0' .
         DC    X'0002000000000000'
         DS    CL76
         DS    CL84
         DS    CL84
         SPACE 1
IPLAPCBS DC    A(LENPCB) .         ALLOC LIST FOR PCB'S
         DC    A(0)
         DC    F'8'
CORESIZ  DC    A(CORESIZE) .       BYTES OF CORE IN OBJECT MACHINE
         SPACE 1
         DS    0D
TYPPCB   DC    CL8'*IBSUP' .       A TEMPLATE *IBSUP PCB
         DC    4A(0)
TEMPLATE DC    X'00000000' .       INITIALIZED FLAGS
         DC    F'1,0'
         DC    5F'0,0'
         DC    X'FF00000000',AL3(JSP)
TYPLEN   EQU   *-TYPPCB
         EJECT
***********************************************************************
*                                                                     *
*             JOB STREAM PROCESSOR                                    *
*                                                                     *
***********************************************************************
         SPACE 1
JSP      EQU   * .                 THE JOB STREAM PROCESSOR
         BALR  1,0 .                (PROCESS *IBSUP)
         USING *,1 .               ESTABLISH ADDRESSING
         LA    2,JSPSUSEM .        LOCK OURSELVES UNTIL
         SVC   C'P' .               WE CAN ALLOCATE STORAGE
         LA    2,JSPAAS .          READY TO ALLOCATE
         USING XAX,2
         SVC   C'E' .              ALLOCATE
         L     12,XAXADDR .        PTR TO AUTO AREA
         DROP  2
         USING JSPAS,12 .          USE FOR ADDRESSING
         LA    2,JSPSUSEM .        UNLOCK OURSELVES
         SVC   C'V'
*        MVC   TREAD+0(8),=CL8'*IN' . INITIALIZE VALUES IN AUTOMATIC
         MVC   TREAD+0(8),LTGIN .ASMA: INITIALIZE VALUES IN AUTOMATIC (literal pool)
*        MVC   TREAD+8(4),=F'8' .   STORAGE
         MVC   TREAD+8(4),LTG2F8 .ASMA: STORAGE (literal pool)
*        MVC   TREAD+12(4),=C'READ'
         MVC   TREAD+12(4),LTGREAD2 .ASMA: literal pool
         LA    2,CARD
         ST    2,ACARD
*        MVC   USERL+0(8),=CL8'USERPROG'
         MVC   USERL+0(8),LTGUPGM .ASMA: literal pool
         MVC   WRITE(12),SKIP
*        MVC   WRITE+12(4),=C'PRIN'
         MVC   WRITE+12(4),LTGPRIN2 .ASMA: literal pool
         LA    5,LINE
         ST    5,WRITE+16
*        MVC   CORE+8(4),=F'2048'
         MVC   CORE+8(4),LTGF2048 . ASMA: literal pool
*        MVC   TALK+0(8),=CL8'USERPROG'
         MVC   TALK+0(8),LTGUPGM .  ASMA: literal pool
*        MVC   TALK+8(4),=F'12'
         MVC   TALK+8(4),LTG2F12 .  ASMA: literal pool        
*        MVC   ANYBACK+8(4),=F'1'
         MVC   ANYBACK+8(4),LTG2F1 .ASMA: literal pool
*        MVC   RLDTEMP,=A(0)
         MVC   RLDTEMP,LTG2A0 .     ASMA: literal pool
         ST    4,KEY .             STORE KEY
         LR    5,3 .               GET PTR TO UCB PTR BLOCK
         L     3,0(5) .            GET READER POINTER
         LA    2,INSEQ .           READY TO CREATE & START *IN
         SVC   C'C' .              CREATE
         SVC   C'Y' .              START
         L     3,4(5) .            GET PTR TO PRINTER UCB
         LA    2,OUTSEQ .          READY TO CREATE & START *OUT
         SVC   C'C' .              CREATE
         SVC   C'Y' .              START
         SPACE 1
LOOP     LA    2,TREAD .           READT TO READ A CARD
         SVC   C'S' .              START TO READ
*        MVC   RREPLY1,=F'132' .   132 CHARS FOR REPLY
         MVC   RREPLY1,LTG2F132 .ASMA: 132 CHARS FOR REPLY (literal pool)
         LA    2,RREPLY
         SVC   C'R' .              LISTEN FOR REPLY
*        CLC   REPLY(2),=C'OK' .   IS REPLY 'OK'?
         CLC   REPLY(2),LTG2OK .   IS REPLY 'OK'?
         BNE   STOP .              IF NOT, STOP
*        CLC   =C'$JOB,',CARD .    HAVE WE A JOB CARD?
         CLC   LTG2JOB,CARD .ASMA: HAVE WE A JOB CARD? (literal pool)
         BE    JOB .               GOOD!
         B     LOOP .              ELSE LOOP
STOP     LA    2,JSPNEVER .        WAIT FOR A "V" OPERATION
         SVC   C'P' .               THAT NEVER COMES
         SPACE 1
JOB      MVI   LOADED,X'00' .      REMEMBER NOT LOADED
*        MVC   LINE,=CL8' ' .      CLEAR A LINE, PUT IN
         MVC   LINE,LTGSPCS .ASMA: CLEAR A LINE, PUT IN (literal pool)
         MVC   LINE+8(124),LINE+7 .ALL BLANKS
         MVC   LINE(80),CARD .     GET READY TO SEND $JOB CARD
         LA    2,WRITE .           TO PRINTER
         SVC   C'S' .              SEND IT
         LA    2,RREPLY
         SVC   C'R' .              AND WAIT FOR REPLY
         LA    2,USERL .           CREATE USERPROG
         SVC   C'C'
         LA    4,CARD+4 .          START TO SCAN CARD
         BAL   3,SCAN .            GET NEXT TOKEN
         LA    8,2048 .            FIRST GUESS AT CORE SIZE
         L     7,CORETABS .        GET CORE TABLE SIZE
         LA    6,CORETAB .         INDEX INTO CORE TABLE
CORELOOP EX    5,CORECOMP .        IS THIS THE CORE SPEC?
         BE    COREOK .            IF SO, BINGO!
         LA    8,2048(8) .         ELSE UP OUR GUESS
         LA    6,4(6) .             AND OUR INDEX
         BCT   7,CORELOOP .         AND TRY AGAIN
         B     EXPUNGE .           ELSE THROW HIM AWAY
CORECOMP CLC   0(0,9),0(6) .       EX'D TO TEST AGAINST CORE TABLE
COREOK   ST    8,CORE .            REMEMBER CORE REQUIREMENT
ASGNUNIT BAL   3,SCAN .            GET NEXT TOKEN
         CLI   0(4),C'=' .         IS IT AN '='?
         BNE   LOAD .              IF NOT, LOAD IN THE OBJECT DECK
         CLI   0(9),C'*' .         HAS USER NAMED IT STARTING
         BE    EXPUNGE .            WITH '*'? IF SO, THROW HIM OUT
         LA    2,SEQ .             ELSE CREATE A PROCESS
*        MVC   SEQ,=CL8' ' .       BLANK OUT THE NAME
         MVC   SEQ,LTGSPCS . ASMA: BLANK OUT THE NAME (literal pool)
         EX    5,UNAMMOV .         THEN MOVE THE RELEVANT
         SVC   C'C' .               CHARACTERS AND CREATE
         LA    2,SEQ .             WE'LL START IT IN A MOMENT
         BAL   3,SCAN .            SCAN AGAIN
         EX    5,CMPIN .           IS IT 'IN'?
         BE    ASIN .              IF SO, ASSIGN IT AS IN
         EX    5,CMPOUT .          IF IT'S 'OUT'
         BE    ASOUT .              ASSIGN IT AS OUT
         EX    5,CMPEXCP .         IS IT 'EXCP'?
         BE    ASEXCP .             IF SO, ASSIGN IT AS EXCP
         B     EXPUNGE .            ERROR: GO ON TO NEXT JOB
UNAMMOV  MVC   SEQ(0),0(9) .       MOVE THE UNIT'S PROCESS NAME
*CMPIN   CLC   0(0,9),=C'IN ' .    DOES IT SAY 'IN'?
CMPIN    CLC   0(0,9),LTG2IN .  ASMA: DOES IT SAY 'IN'? (literal pool)
*CMPOUT   CLC   0(0,9),=C'OUT ' .   DOES IT SAY 'OUT'?
CMPOUT   CLC   0(0,9),LTG2OUT . ASMA: DOES IT SAY 'OUT'? (literal pool)
*CMPEXCP  CLC   0(0,9),=C'EXCP ' .  DOES IT SAY 'EXCP'?
CMPEXCP  CLC   0(0,9),LTG2EXCP .ASMA:  DOES IT SAY 'EXCP'?
         SPACE 1
*ASIN    LA    11,=CL8'*IN' .      POINT TO NAME OF READER HANDLER
ASIN     LA    11,LTGIN .    ASMA: POINT TO NAME OF READER HANDLER (literal pool)
*SETDIM  MVC   UNITRTN,=A(DIM) .   USE DIM AS THE INTERFACE
SETDIM   MVC   UNITRTN,LTGADIM .ASMA: USE DIM AS THE INTERFACE (literal pool)
         SVC   C'Y'
         B     ASGNUNIT
*ASOUT   LA    11,=CL8'*OUT' .     POINT TO NAME OF PRINTER HANDLER
ASOUT    LA    11,LTGOUT .   ASMA: POINT TO NAME OF PRINTER HANDLER (literal pool)
         B     SETDIM
*ASEXCP   MVC   UNITRTN,=A(EXCPHNDL) . USE FOR USER SUPPLIED
ASEXCP   MVC   UNITRTN,LTGAEXCP .ASMA: USE FOR USER SUPPLIED (literal pool)
         L     11,KEY
         SVC   C'Y' .              I/O ROUTINE
         B     ASGNUNIT
         SPACE 1
LOAD     LA    2,CORE .            READY TO ALLOCATE THE REGION
         SVC   C'A' .              AND ALLOCATE IT
         MVI   LOADED,X'FF' .      REMEMBER THAT WE'RE LOADED
         L     9,CORE+4 .          GET THE FIRST ADDRESS
         L     4,KEY .             GET THE KEY
         SRL   4,16
         LR    3,9 .               GET THE BLOCK FOLLOWING OURS
         AR    3,8
*LOADSK  S     3,=F'2048' .        GET THE PREVIOUS BLOCK
LOADSK   S     3,LTGF2048 .  ASMA: GET THE PREVIOUS BLOCK (literal pool)
         CR    3,9 .               HAVE WE PASSED THE START?
         BL    LOADLOOP .          IF SO, START LOADING
         SSK   4,3 .               ELSE SET THIS BLOCK TO THE KEY
         B     LOADSK .            AND BRANCH BACK
LOADLOOP LA    2,TREAD .           READ IN OBJECT DECK
         SVC   C'S' .              GET A CARD A'READING
*        MVC   RREPLY1,=F'132'
         MVC   RREPLY1,LTG2F132 .ASMA: literal pool
         LA    2,RREPLY
         SVC   C'R' .              WAIT FOR ANSWER
*        CLC   CARD+1(3),=C'TXT' . IS IT A TXT CARD?
         CLC   CARD+1(3),LTGTXT .ASMA: IS IT A TXT CARD? (literal pool)
         BE    TXTCARD
*        CLC   CARD+1(3),=C'RLD' . IS IT A RLD CARD?
         CLC   CARD+1(3),LTGRLD .ASMA: IS IT A RLD CARD? (literal pool)
         BE    RLDCARD
*        CLC   CARD+1(3),=C'END' . IS IT AN END CARD?
         CLC   CARD+1(3),LTGEND .ASMA: IS IT AN END CARD? (literal pool)
         BE    ENDCARD
         B     LOADLOOP .          IF NONE, IGNORE.
         SPACE 1
TXTCARD  L     10,CARD+4 .         GET THE RELATIVE ADDRESS
         AR    10,9 .              PLUS THE ABSOLUTE ADDRESS
         LH    11,CARD+10 .        GET THE COUNT,
         BCTR  11,0 .               DECREMENTED
         EX    11,TXTMOV .         AND MOVE THE TEXT
         B     LOADLOOP .          AND READ ANOTHER CARD! OH WOW!
TXTMOV   MVC   0(0,10),CARD+16
         SPACE 1
RLDCARD  LH    11,CARD+10 .        GET THE BYTE COUNT
         LA    13,CARD+20 .        AND AN INDEX INTO THE CARD
RLDLOOP  L     10,0(13) .          GET THE LOCATION TO BE RLD'D
         AR    10,9 .              GET THE ABSOLUTE ADDRESS
         TM    3(13),X'03' .       IS IT A FULLWORD?
         BNZ   NOTALGND .          IF NO, HANDLE AS THREE BYTES
         L     7,0(10) .           GET THAT WORD (HAD BETTER BE
         AR    7,9 .                ONE); ADD THE RELOCATION
         ST    7,0(10) .            ADDRESS, AND STORE IT BACK
RLDCONT  TM    0(13),X'01' .       CHECK IF LONG OR SHORT FIELD
         BNZ   SHORT .             AND BRANCH ACCORDINGLY
         LA    4,8 .               SKIP EIGHT BYTES
         B     RLDFINI
SHORT    LA    4,4 .               SKIP FOUR BYTES
RLDFINI  AR    13,4 .              INCREMENT THE CARD INDEX
         SR    11,4 .              DECREMENT THE BYTE COUNT
         BP    RLDLOOP .           AND TRY AGAIN
         B     LOADLOOP .          OR READ ANOTHER CARD
NOTALGND MVC   RLDTEMP+1(3),0(10) . PUT ADDRESS HERE
         L     7,RLDTEMP .         RELOCATE IT
         AR    7,9
         ST    7,RLDTEMP .         AND PUT IT BACK TO
         MVC   0(3,10),RLDTEMP+1 .  WHERE IT BELONGS
         NI    RLDTEMP,X'00' .     CLEAR OUT TEMPORARY
         B     RLDCONT .           AND LOOP BACK
         SPACE 1
ENDCARD  LA    2,USERL .           FIND THE PCB FOR USERPROG
         SVC   C'N'
         L     4,USERL+8 .         GET THE ADDRESS
         USING PCB,4
         MVI   PCBBLOKT,X'FF' .    TEMPORARILY BLOCK IT
         ST    9,USERL+8 .         STORE THE BEGINNING ADDRESS
         SVC   C'Y' .              THEN START IT
         L     5,KEY .             GET THE KEY
         O     5,PCBISA+0 .        THEN OR THIS INTO THE
         ST    5,PCBISA+0 .         FIRST WORD OF THE PCB
         OI    PCBISA+1,X'01' .    OR IN A 'PROGRAM STATE' BIT
         MVI   PCBBLOKT,X'00' .    AND THEN UNBLOCK IT
         DROP  4
         LA    2,TALK .            LISTEN TO WHAT IT SAYS
         SVC   C'R'
         SPACE 1
*        MVC   LINE(8),=CL8' ' .   IF JOB FINISHED, CLEAR A LINE
         MVC   LINE(8),LTGSPCS .ASMA: IF JOB FINISHED, CLEAR A LINE (literal pool)
         MVC   LINE+8(124),LINE+7
         MVC   LINE(12),TALK+12 .  MOVE THE MESSAGE ONTO THE LINE
         LA    2,WRITE .           AND SAY TO WRITE IT
         SVC   C'S'
         LA    2,ANYBACK
         SVC   C'R'
         LA    2,SKIP .            SKIP TO THE TOP OF THE NEXT PAGE
         SVC   C'S'
         LA    2,ANYBACK
         SVC   C'R'
         SPACE 1
EXPUNGE  L     5,RUNNING .         EXPUNGE A JOB: LOOK AT ALL PCBS
         LA    2,SEQ
         USING PCB,5
EXPLOOP  MVC   SEQ(8),PCBNAME .    GET THE PROCESS NAME
         L     4,PCBNPTG .         GET THE NEXT PTR
         CLI   SEQ+0,C'*' .        IS IT A '*' PROCESS?
         BE    EXPNXT .            IF SO, SKIP OVER
         SVC   C'Z' .              ELSE STOP IT
         SVC   C'D' .              AND DESTROY IT
EXPNXT   LR    5,4 .               GO TO THE NEXT PCB
         C     5,RUNNING .         ARE WE THROUGH?
         BNE   EXPLOOP .           IF NOT, LOOP AGAIN
         CLI   LOADED,X'00' .      WAS CORE ALLOCATED?
         BE    LOOP .              IF NOT, GO READ THE NEXT $JOB CARD
         SR    4,4 .               ELSE GET A ZERO KEY
         LR    3,9 .               AND A POINTER TO THE NEXT
         AR    3,8 .                BLOCK AFTER OURS
*LOADCL  S     3,=F'2048' .        GO TO THE PREVIOUS BLOCK
LOADCL   S     3,LTGF2048 .  ASMA: GO TO THE PREVIOUS BLOCK (literal pool)
         CR    3,9 .               ARE WE THROUGH?
         BL    LOADD .             IF SO, GO FREE CORE
         SSK   4,3 .               ELSE CLEAR STORAGE KEY
         B     LOADCL .            AND LOOP BACK
LOADD    LA    2,CORE
         SVC   C'F' .              FREE THE STORAGE
         B     LOOP .              READ ANOTHER $JOB CARD
         SPACE 1
SCAN     SR    5,5 .               START THE TOKEN COUNT AT ZERO
SCANLOOP LA    4,1(4) .            GO TO NEXT CHARACTER
         CLI   0(4),C',' .         DO WE HAVE A DELIMITER? IF SO,
         BE    TOKSTART
         CLI   0(4),C'=' .         DITTO
         BE    TOKSTART
         CLI   0(4),C' ' .         DITTO
         BE    TOKSTART
         LA    5,1(5) .            AND UP COUNT
         B     SCANLOOP .          AND LOOP
TOKSTART LR    9,4 .               SET REG9 TO START
         SR    9,5 .               OF THIS TOKEN
         BCTR  5,0 .               LESS ONE FOR EXECUTE INSTRUCTION
         BR    3
         SPACE 2
JSPNEVER DC    F'0,0' .            A GOOD WAY TO DIE: P(JSPNEVER)
SKIP     DC    CL8'*OUT' .         MESSAGE BLOCK FOR A NEW PAGE
         DC    F'8'
         DC    CL4'STC1'
INSEQ    DC    CL8'*IN' .          SEQ TO CREATE & START *IN
         DC    A(RDRHANDL)
OUTSEQ   DC    CL8'*OUT' .         SEQ TO CREATE & START *OUT
         DC    A(PRTHANDL)
CORETAB  EQU   * .                 TABLE OF CORE SIZES
         DC    CL4'2K'
         DC    CL4'4K'
         DC    CL4'6K'
         DC    CL4'8K'
         DC    CL4'10K'
         DC    CL4'12K'
         DC    CL4'14K'
         DC    CL4'16K'
         DC    CL4'18K'
         DC    CL4'20K'
         DC    CL4'22K'
CORETABS DC    A((*-CORETAB)/4) .  CORE TABLE SIZE
JSPSUSEM DC    F'1,0' .            SEMAPHORE TO LOCK ROUTINE
JSPAAS   DC    A(LENJSPAS) .       ALLOCATE LIST FOR AUTO STORAGE
         DS    A
         DC    F'8'
         EJECT
***********************************************************************
*                                                                     *
*                            DEVICE INTERFACE MODULE                  *
*                                                                     *
*        FUNCTION: TO INTERFACE BETWEEN USERPROG AND DEVICE HANDLER   *
*       DATABASES: NONE                                               *
*   ROUTINES USED: XA, XP, XV, XR, XS                                 *
*       PROCEDURE: ALLOCATE AUTOMATIC STORAGE; START TO READ MESSAGE  *
*                  FROM USER; SEND MESSAGE TO DEVICE HANDLER;         *
*                  CONTINUE LOOPING, SENDING MESSAGES FROM USER TO    *
*                  DEVICE HANDLER AND BACK.                           *
*    ERROR CHECKS: NONE                                               *
*      INTERRUPTS: ON                                                 *
*     USER ACCESS: YES                                                *
*                                                                     *
***********************************************************************
         SPACE 1
DIM      EQU   * .                 THE DEVICE INTERFACE MODULE
         BALR  1,0
         USING *,1 .               ESTABLISH ADDRESSING
         LA    2,DIMSEM .          LOCK UNTIL GET STORAGE
         SVC   C'P'
         LA    2,DIMAAS .          READY TO ALLOCATE STORAGE
         USING XAX,2
         SVC   C'E' .              DO IT
         L     12,XAXADDR .        GET THE ADDRESS
         DROP  2
         LA    2,DIMSEM .          UNLOCK OURSELVES
         SVC   C'V'
         USING DIMAS,12 .          USE 12 FOR AUTO STORAGE
         MVC   DIMLMS,0(11) .      MOVE NAME OF RECIEVER
         LA    8,132 .             REG 8 = SIZE OF MESSAGE
DIMLOOP  ST    8,DIMMSG+8 .        GET READY TO READ A MESSAGE
         LA    2,DIMMSG
         SVC   C'R' .              READ
         MVC   DIMTEMP,DIMMSG .    SAVE SENDER NAME
         MVC   DIMMSG,DIMLMS .     SEND IT BACK TO THE LAST GUY
         SVC   C'S' .              SEND IT
         MVC   DIMLMS,DIMTEMP .    AND REMEMBER WHO TO SEND TO NEXT
         B     DIMLOOP .           RELOOP
DIMSEM   DC    F'1,0' .            SEMAPHORE FOR ENTRY
DIMAAS   DC    A(DIMLEN) .         ALLOCATE SEQ FOR AUTO STORAGE
         DC    A(0)
         DC    F'8'
         DROP  12
         EJECT
*        LTORG               ASMA: does not support literal pools
LTG2F1   DC    F'1'
LTG2F8   DC    F'8'
LTG2F12  DC    F'12'
LTG2F132 DC    F'132'
LTGF2048 DC    F'2048'
LTG2A0   DC    A(0)
LTGUCBA  DC    A(UCBTABLE)
LTGUCBN  DC    A(UCBTBEND)
LTGADIM  DC    A(DIM)
LTGAEXCP DC    A(EXCPHNDL)
LTGCORN  DC    A(0,CORESIZE-(VERYEND-PROGRAM))
LTGIN    DC    CL8'*IN'
LTGOUT   DC    CL8'*OUT'
LTGUPGM  DC    CL8'USERPROG'
LTGSPCS  DC    CL8' '
LTG2JOB  DC    C'$JOB,'
LTGPRIN2 DC    C'PRIN'
LTGREAD2 DC    C'READ'
LTG2OK   DC    C'OK'
LTG2IN   DC    C'IN '
LTGEND   DC    C'END'
LTGRLD   DC    C'RLD'
LTGTXT   DC    C'TXT'
LTG2OUT  DC    C'OUT '
LTG2EXCP DC    C'EXCP '
VERYEND  DS    D .                 BEGINNING OF FREE STORAGE
         EJECT
***********************************************************************
*                                                                     *
*                          DATABASE DEFINITIONS                       *
*                                                                     *
***********************************************************************
         SPACE 1
PCB      DSECT .                   PROCESS CONTROL BLOCK DEFINITION
PCBNAME  DS    CL8 .               NAME
PCBNPTG  DS    F .                 NEXT POINTER THIS GROUP
PCBLPTG  DS    F .                 LAST POINTER THIS GROUP
PCBNPALL DS    F .                 NEXT POINTER ALL
PCBLPALL DS    F .                 LAST POINTER ALL
PCBSTOPT DS    C .                 STOPPED
PCBBLOKT DS    C .                 BLOCKED
PCBINSMC DS    C .                  IN SMC
PCBSW    DS    C .                 STOP WAITING
PCBMSC   DS    CL8 .               MESSAGE SEMAPHORE COMMON
PCBMSR   DS    CL8 .               MESSAGE SEMAPHORE RECEIVER
PCBFM    DS    F .                 FIRST MESSAGE
PCBNSW   DS    F .                 NEXT SEMAPHORE WAITER
PCBSRS   DS    CL8 .               STOPPER SEMAPHORE
PCBSES   DS    CL8 .               STOPPEE SEMAPHORE
PCBASIZE DS    F .                 AUTOMATIC STORAGE SIZE
PCBAADDR DS    A .                 AUTOMATIC STORAGE ADDRESS
PCBISA   DS    CL84 .              INTERRUPT SAVE AREA
PCBFSA   DS    CL84 .              FAULT SAVE AREA
PCBMSA   DS    CL84 .              MEMORY SAVE AREA
         DS    0D .                (ALIGN)
LENPCB   EQU   *-PCB .             (LENGTH)
         SPACE 1
SA       DSECT .                   SAVE AREA DEFINITION
SAPSW    DS    D .                 PROGRAM STATUS WORD
SAREGS   DS    CL64 .              REGISTERS
SATEMP   DS    CL12 .              TEMPORARIES
         SPACE 1
REGS     DSECT .                   REGISTER DEFINITION
REG0     DS    F .                 REGISTER 0
REG1     DS    F .                 REGISTER 1
REG2     DS    F .                 REGISTER 2
REG3     DS    F .                 REGISTER 3
REG4     DS    F .                 REGISTER 4
REG5     DS    F .                 REGISTER 5
REG6     DS    F .                 REGISTER 6
REG7     DS    F .                 REGISTER 7
REG8     DS    F .                 REGISTER 8
REG9     DS    F .                 REGISTER 9
REG10    DS    F .                 REGISTER 10
REG11    DS    F .                 REGISTER 11
REG12    DS    F .                 REGISTER 12
REG13    DS    F .                 REGISTER 13
REG14    DS    F .                 REGISTER 14
REG15    DS    F .                 REGISTER 15
         SPACE 1
FSB      DSECT .                   FREE STORAGE BLOCK DEFINITIONS
FSBNEXT  DS    A .                 NEXT
FSBSIZE  DS    F .                 SIZE
         SPACE 1
SM       DSECT .                   SEMAPHORE DEFINITION
SMVAL    DS    F .                 VALUE
SMPTR    DS    F .                 PTR
         SPACE 1
MSG      DSECT .                   MESSAGE DEFINITION
MSGSENDR DS    A .                 POINTER TO SENDER'S PCB
MSGNEXT  DS    A .                 NEXT
MSGSIZE  DS    F .                 SIZE
MSGTEXT  DS    0C .                TEXT
LENMSG   EQU   *-MSG .             (LENGTH)
         SPACE 1
XAX      DSECT .                   XA ARGUMENT LIST
XAXSIZE  DS    F .                 SIZE
XAXADDR  DS    F .                 ADDRESS
XAXALGN  DS    F .                 ALIGNMENT
         SPACE 1
XFX      DSECT .                   XF ARGUMENT LIST
XFXSIZE  DS    F .                 SIZE
XFXADDR  DS    F .                 ADDRESS
         SPACE 1
XBX      DSECT .                   XB ARGUMENT LIST
XBXSIZE  DS    F .                 SIZE
XBXADDR  DS    F .                 ADDRESS
         SPACE 1
XCX      DSECT .                   XC ARGUMENT LIST
XCXNAME  DS    CL8 .               NAME
         SPACE 1
XDX      DSECT .                   AD ARGUMENT LIST
XDXNAME  DS    CL8 .               NAME
         SPACE 1
XNX      DSECT .                   XN ARGUMENT LIST
XNXNAME  DS    CL8 .               NAME
XNXADDR  DS    A .                 ADDRESS
         SPACE 1
XRX      DSECT .                   XR ARGUMENT LIST
XRXNAME  DS    CL8 .               NAME
XRXSIZE  DS    F .                 SIZE
XRXTEXT  DS    0C .                TEXT
         SPACE 1
XSX      DSECT .                   XS ARGUMENT LIST
XSXNAME  DS    CL8 .               NAME
XSXSIZE  DS    F .                 SIZE
XSXTEXT  DS    0C .                TEXT
         SPACE 1
XYX      DSECT .                   XY ARGUMENT LIST
XYXNAME  DS    CL8 .               NAME
XYXADDR  DS    A .                 ADDR
         SPACE 1
XZX      DSECT .                   XZ ARGUMENT LIST
XZXNAME  DS    CL8 .               NAME
         SPACE 1
RDRHAS   DSECT .                   READER HANDLER AUTOMATIC STORAGE
RDRHCCB  DS    2F .                CCB
RDRHMSG  DS    CL8 .               MESSAGE BLOCK FOR REQUESTS
         DS    F'8'
         DS    CL8
RDRHTEMP DS    CL80 .              AREA FOR $JOB IN DATA STREAM
RDRHM    DS    CL8 .               MESSAGE BLOCK FOR REPLY
         DS    F'2'
         DS    CL2
JOBBIT   DS    1C
         DS    0D
LENRDRHA EQU   *-RDRHAS .          (LENGTH)
         SPACE 1
PRTHAS   DSECT .                   PRINTER HANDLER AUTOMATIC STORAGE
PRTHCCB  DS    2F .                CCB
PRTHMSG  DS    CL8 .               MESSAGE BLOCK FOR REQUESTS
         DS    F'2'
         DS    CL8
PRTHM    DS    CL8 .               MESSAGE BLOCK FOR REPLY
         DS    F'2' 
         DS    CL2
         DS    0D
LENPRTHA EQU   *-PRTHAS .          (LENGTH)
         SPACE 1
EXCPHAS  DSECT .                   EXCP HANDLER AUTOMATIC STORAGE
EXCPHMSG DS    CL8 .               MESSAGE BLOCK FOR REQUESTS
         DS    F'12'
         DS    CL12
EXCPHM   DS    CL8 .               MESSAGE BLOCK FOR REPLY
         DS    F'12'
         DS    CL12
         DS    0D
LENEXCPA EQU   *-EXCPHAS .          (LENGTH)
         SPACE 1
UCB      DSECT .                   UNIT CONTROL BLOCK DEFINITION
UCBADDR  DS    F .                 ADDRESS
UCBUS    DS    FL8 .               USER SEMAPHORE
UCBWS    DS    FL8 .               WAITER SEMAPHORE
UCBCSW   DS    FL8 .               CHANNEL STATUS WORD
UCBFPR   DS    CL1 .               FAST PROCESSING REQUIRED
         DS    0F
UCBLENG  EQU   *-UCB
         SPACE 1
JSPAS    DSECT .                   JSP AUTOMATIC STORAGE
LINE     DS    CL132 .             PRINTED LINE
         DS    0F
CARD     DS    CL80 .              CARD READ
         DS    0F
RREPLY   DS    CL8 .               MESSAGE BLOCK FOR REPLIES
RREPLY1  DS    F
REPLY    DS    CL132
TREAD    DS    0F .                MESSAGE BLOCK FOR READING
         DS    CL8'*IN'
         DS    F'8'
         DS    CL4'READ'
ACARD    DS    A(0)
WRITE    DS    CL8'*OUT' .         MESSAGE BLOCK TO PRINT A LINE
         DS    F'8'
         DS    CL4'PRIN'
         DS    A(LINE)
KEY      DS    F
USERL    DS    CL8'USERPROG' .     LIST FOR MANIPULATING USERPROG
         DS    F
SEQ      DS    CL8' ' .            COMMON ARG LIST FOR I/O PROCESS
UNITRTN  DS    A
CORE     DS    F .                 MEMORY ALLOCATED AND FREE
         DS    F .                 SEQUENCE
         DS    F'2048'
RLDTEMP  DS    F
TALK     DS    CL8'USERPROG' .     MESSAGE BLOCK FOR MESSAGE FROM
         DS    F'12' .              USERPROG
         DS    CL12
ANYBACK  DS    CL8 .               MESSAGE BLOCK FOR IGNORING MESS
         DS    F'1'
         DS    CL1
LOADED   DS    C .                 IS CORE ALLOCATED
         DS    0D
LENJSPAS EQU   *-JSPAS .           (LENGTH)
         SPACE 1
DIMAS    DSECT .                   DEVICE INTERFACE MODULE STORAGE
DIMMSG   DS    CL8 .               MESSAGE BLOCK
         DS    F'132'
         DS    CL132
DIMLMS   DS    CL8 .               LAST MESSAGE SENDER
DIMTEMP  DS    CL8 .               TEMPORARY
         DS    0D
DIMLEN   EQU   *-DIMAS .           (LENGTH)
         END   IPLRTN
