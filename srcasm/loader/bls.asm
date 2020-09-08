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
*
* The Boot Loader Services Framework
*
         SPACE 1
BLS      SERVS  SERVTBL
         SPACE 3
*
* Boot Loader Service Table
*
         SPACE 1
         BLSTABLE
         SPACE 3
* Register Contents at service entry
*  R0  - unpredictable but usable (also ASA base register)
*  R1  - Pointer to Service Parameter Block (passed by framework)
*  R2  - unpredictable but usable (used by service framework as work register)
*  R3  - unpredictable but usable
*  R4  - unpredictable but usable
*  R5  - unpredictable but usable
*  R6  - unpredictable but usable
*  R7  - unpredictable but usable
*  R8  - unpredictable but usable
*  R9  - unpredictable but usable
*  R9  - unpredictable but usable
*  R10 - unpredictable but usable
*  R11 - unpredictable but usable
*  R12 - The service's entry point (set by service framework, use as base)
*  R13 - Pointer to service CALLER'S save area (passed by framework)
*  R14 - unpredictable but usable
*  R15 - unpredictable but usable
*
         SPACE 1
* Use LOD1RTN address to return to caller from the service.
* Register usage on entry to SERVRTN
*  R0 - Return code from service.  Framework will move it to R15
*  R13 - Service caller's save area
*  R15 - Address from LOD1RTN to return to framework
         TITLE 'BOOT LOADER - SERVICE 0 - NOOP'
*
* Boot Loader Service - 0 - NOOP
*
         SPACE 1
         SERVNOOP
         TITLE 'BOOT LOADER - SERVICE 1 - IOINIT'
*
* Boot Loader Service - 1 - IOINIT
*
* Register Usage:
*   R0 - Return Code
*   R1 - Address of the INTHND SPB when used
*   R3 - Used to point to caller's save area when booted program being checked
*   R4 - Address of the IOINIT input SPB (from R1 entry contents)
*   R5 - Start of I/O table address and table entry start
*   R6 - I/O table entry length
*   R7 - Address of the last byte of the I/O table itself
*   R12 - Base register
*   R15 - Return address to serivce framework
         SPACE 1
         SERVIOIN
         TITLE 'BOOT LOADER - SERVICE 2 - QIOT'
*
* Boot Loader Service - 2 - QIOT
*
* Register Usage:
*   R0 - Return Code
*   R1 - Address of the SPB and its extention
*   R5 - Start of I/O table address and table entry start
*   R6 - I/O table entry length
*   R7 - Address of the last byte of the I/O table itself
*   R12 - Base register
*   R15 - Return address to serivce framework
         SPACE 1
         SERVQIOT
         TITLE 'BOOT LOADER - SERVICE 3 - ENADEV'
*
* Boot Loader Service - 3 - ENADEV
*
* Register Usage:
*   R0 - Return Code
*   R1 - Hardware device address for I/O commands
*   R2 - Address of the new table entry
*   R3 - New end of the I/O Table after entry is added
*   R4 - Address of the SPB and its extention
*   R5 - Address of the existing I/O Table entry of the device
*   R6 - Location where channel subsystem SCHIB's are stored
*   R12 - Base register
*   R15 - Return address to serivce framework
         SPACE 1
         SERVENAD
         TITLE 'BOOT LOADER - SERVICE 4 - EXCP'
*
* Boot Loader Service - 4 - EXCP
*
* SPB:
*      SPB Bytes 0,1   - EXCP Service ID (4)
*      SPB Byte 2      - SI EXCP input function control mask (See SPB DSECT)
*      SPB Byte 3      - not used
*      SPB Bytes 4-7   - ORB - I/O Table device entry address
*      SPB Bytes 8-11  - ORB - Key and flags
*      SPB Bytes 12-15 - ORB - CCW program starting address 
*
* Register Usage:
*   R0 - Return Code
*   R1 - Hardware device address for I/O commands (from I/O Table)
*   R2 - 
*   R3 - I/O Error execution register
*   R4 - Address of the SPB and its extention (the ORB)
*   R5 - Address of the primary device IOT entry
*   R6 - Interrupting device I/O Table entry (may not be the R5 entry)
*   R7 - Start of I/O table address and table entry start --------+
*        When found this becomes the secondary device IOT address |
*   R8 - I/O table entry length                                   |-- BXLE
*   R9 - Address of the last byte of the I/O table itself --------+
*   R12 - Base register
*   R15 - Return address to serivce framework
*
         SPACE 1
SERVEXCP SERVEXCP
         TITLE 'BOOT LOADER - SERVICE 5 - PNDING'
*
* Boot Loader Service - 5 - PNDING
*
* Register Usage:
*   R0 - Return Code
*   R1 - AVAILABLE
*   R2 - AVAILABLE
*   R3 - AVAILABLE
*   R4 - Address of the SPB and its extention
*   R5 - AVAILABLE
*   R6 - AVAILABLE
*   R7 - Start of I/O table address and table entry start --------+
*        When found this becomes the secondary device IOT address |
*   R8 - I/O table entry length                                   |-- BXLE
*   R9 - Address of the last byte of the I/O table itself --------+
*   R10 - AVAILABLE
*   R11 - AVAILABLE
*   R12 - Base register
*   R15 - Return address to serivce framework
*
         SPACE 1
         SERVPEND
         TITLE 'BOOT LOADER - COMMON SERVICES DATA'
*
* Common information used by Boot Loader Services
*
         SPACE 1
         BLCOMMON
         SPACE 3
* END OF bls.asm