.ifndef .LDRIVER_S
.LDRIVER_S = 1
 # Copyright (C) 2012 Harold Grovesteen
 #
 # This file is part of SATK.
 #
 #     SATK is free software: you can redistribute it and/or modify
 #     it under the terms of the GNU General Public License as published by
 #     the Free Software Foundation, either version 3 of the License, or
 #     (at your option) any later version.
 #
 #     SATK is distributed in the hope that it will be useful,
 #     but WITHOUT ANY WARRANTY; without even the implied warranty of
 #     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 #     GNU General Public License for more details.
 #
 #     You should have received a copy of the GNU General Public License
 #     along with SATK.  If not, see <http://www.gnu.org/licenses/>.

 # Driver Framework related source modules:
 #   *  DRIVER.S   - Macros and symbols used by programs that call drivers
 #      DRVUTIL.S  - Macros and symbols used by drivers participating in the Driver
 #                   Framework
 #      drivers.S  - Implements the Driver Framework.  Included by a program that
 #                   provides the framework with which drivers are registered or
 #                   called by users of the drivers themselves.
 #
 #   * This source module

 # Dependencies:
    .ifndef .Ltable_S
            .include "table.S"   # Used to calculate a table size
    .endif

  # +------------------------+
  # |  Driver Request Block  |
  # +------------------------+
  # Access: public

  # This structure is required because the number of arguments exceeds what is
  # supported by the ABI standard.

.LDRB_at     = 0   # .long      Driver token of request (see below)
.LDRB_dde    = 4   # .long      31-bit Device Definition Entry address (see note 1)
.LDRB_addr   = 8   # .quad      64-bit program area address (see note 2)
.LDRB_addr32 = 12  # .long      32-bit program area address (see note 2)
.LDRB_length = 16  # .hword     16-bit unsigned area length
.LDRB_misc   = 18  # .hword     Various uses (see driver action descriptions below)
.LDRB_info   = 20  # .quad      Driver dependent request information (see below)
.LDRB_len    = 28  #            Driver Request Block length

 # Note 1: I/O operations are performed out of the DDE.  I/O operations are
 # restricted to the first 2G of real storage addresses.  For this reason only a 
 # fullword is supported in the structure for this address.
 #
 # Note 2: For consisency on all CPU and I/O architectures, a 64-bit address is used.
 # Only on S/370 is it safe to ignore the high-order 40-bits of the address.  On
 # ESA/390, any of bits 0-33 set to one will cause IDAW2's to be used and storage
 # addresed at those locations.  I/O failures may occur if bits 0-33 are not set to
 # zero on ESA/390.


  # +------------------------------+
  # |  Driver Request Block Macro  |
  # +------------------------------+
  # Access: public

 # drb - Generate a DRB inline within the assembly
 #
 #  Macro Parameters:
 #     token    Token Value associated with this request (required)
 #     dde      Device definition entry address (default 0)
 #     addr     Program address associated with the request (default 0)
 #     len      Program length/number associated with the request (default 0)
 #     misc     Program miscelaneous data associated with the request (default 0)
 #     info     Specify 'no' to cause the 8-byte information area to be suppressed.
 #              This allows the program to provide its information area as needed
 #              Otherwise, this area is generated with zeros.

            .macro drb token:req dde=0,addr=0,len=0 misc=0 info=0
            .long  \token,\dde
            .quad  \addr
            .hword \len,\misc
    .ifnc \info,no
            .quad  \info
    .endif # .ifnc \info,no
            .endm

 # drbf - Create a DRB on the local stack
 #
 #  Macro Parameters:
 #     name     Symbol associated with the stack-base DRB (required)
 #     r        If specified, will load a pointer to the DRB into the register

            .macro drbf name:req r
    .ifnb \r
            la     \r,\name(15)
    .endif
            mvi    \name(15),0x00
            mvc    \name+1(.LDRB_len-1,15),\name(15)
            .endm

  # +----------------------------+
  # |  Driver Management Macros  |
  # +----------------------------+
  # Access: public

 # drvid - Assign a driver ID number to a name
 #
 # Macro Parameters
 #     name      Symbol associated with the driver id

            .macro drvid name:req start
    .ifndef .L_drvid
.L_drvid    =  0
    .endif # .ifndef .L_drvid
\name       =  .L_drvid
.L_drvid    =  .L_drvid+1
            .endm

 # drvids - Assign the number of driver ID's assigned to a symbol
 #
 # Macro Parameters
 #     name      Symbol associated with the number of assigned driver ID's

            .macro drvids name:req
\name       = .L_drvid
            .endm

       drvid name=.LDRV_CMN   # drivers.S - Common Driver
       drvid name=.LDRV_CON   # dev3215.S - Line Console Driver
       drvid name=.LDRV_UI    # console.S - Generic Console Driver
       drvids name=.LDRV_IDS  # number of assigned driver ID's (defines DMT size)

 # drvtok - Define a driver action token
 #
 #  Macro Parameters:
 #     name     Symbol associated with Driver Action (required)
 #     id       Driver ID of the driver whose action is being defined (required)
 #     action   Value associated with the Driver's action (required)

            .macro drvtok name:req,id:req,action:req
\name       = (\id<<16)+\action
            .endm


 # Driver Management Table Calculators
 # 
 # Macro Parameters
 #     name      Symbol to which the calculated size is assigned (required)
 #     entries   Number of entries (default 4, one 4K page)


.LDRV_MAX_DRIVERS = 15

            .macro ddtsize name:req entries=4
            tblsize name=\name,entry=.LDDE_len,entries=\entries,header=0
            .endm

            tblsize .LDRV_DMT_len,4,.LDRV_IDS,0
            tblsize .LDRVG_DMT_len,8,.LDRV_IDS,0

  # +--------------------------------------+
  # |  Driver Action Tokens and DRB Usage  |
  # +--------------------------------------+
  # Access: public


 # CKD driver information
.LDRB_cc   = 20  # .hword     Cylinder targeted by the operation
.LDRB_hh   = 22  # .hword     Track targeted by the operation
.LDRB_r    = 23  # .byte      Record targeted by the operation
                 # .byte      unused by CKD devices
                 # .hword     unused by CKD devices

 # FBA driver information
.LDRB_sec  = 20  # .long      32-bit unsigned starting sector number of operation
                 # .long      unused by FBA devices


 # **  CMN - Common Driver  **


            drvtok .LCMN_Ena_Drv,id=.LDRV_CMN,action=0  # Enable Drivers
 #.LCMN_Ena_Drv = 0x00000000       # Enable Drivers
 # DRB Usage:
 #    .LDRB_dde      Location where DDE table should be built (if not zero)
 #    .LDRB_length   Number of entries to be provided in the DDE

            drvtok .LCMN_Reg_Drv,id=.LDRV_CMN,action=1  # Register Driver
 #.LCMN_Reg_Drv = 0x00000001       # Register Driver
 # DRB Usage:
 #    .LDRB_addr     Location of the driver's Action Token Table

            drvtok .LCMN_Opn_Dev,id=.LDRV_CMN,action=2  # Register Driver
 #.LCMN_Opn_Dev = 0x00000002       # Open Device
 # DRB Usage:
 #    .LDRB_addr     Device ID of device being opened (device number or SSID)
 #    .LDRB_dde      Device Definition being opened
 #    .LDRB_misc     Specify the driver id


 # **  UI - Generic Console Driver  **


            drvtok .LUI_Opn_Con,id=.LDRV_UI,action=0    # Configure/Open Console
 # DRB Usage:
 #    .LDRB_dde      Device Definition Entry address to be used for console

            drvtok .LUI_Wrt_Asc,id=.LDRV_UI,action=1    # Write ASCII message
            drvtok .LUI_Wrt_Ebc,id=.LDRV_UI,action=2    # Write EBCDIC message
 # DRB Usage:
 #    .LDRB_dde      Device Definition Entry address for console
 #    .LDRB_addr[32] Address of the ASCII/EBCDIC text message
 #    .LDRB_length   Length of the ASCII/EBCDIC text message
 #    .LDRB_misc     Physical driver output message options (see driver)
 #                      0x0000 - 3215 Write with Carrier and no alarm
 #                      0x0001 - 3215 Write with Carrier and with alarm
 #                      0x0002 - 3215 Write without Carrier and no alarm
 #                      0x0003 - 3215 Write without Carrier and with alarm

 
 # **  3215 - Console Driver  **
 

            drvtok .LCON_Wrt_Cr, id=.LDRV_CON,action=0  # Write Carrier, No alarm
            drvtok .LCON_Wrt_CrA,id=.LDRV_CON,action=1  # Alarm, Write Carrier
            drvtok .LCON_Wrt_NoC,id=.LDRV_CON,action=2  # Write No Carrier, No alarm
            drvtok .LCON_Wrt_Alm,id=.LDRV_CON,action=3  # Alarm, Write No Carrier
            drvtok .LCON_Alarm  ,id=.LDRV_CON,action=4  # Alarm
 # DRB Usage:
 #    .LDRB_dde      Device Definition Entry address for console
 #    .LDRB_addr[32] Address of the EBCDIC text message
 #    .LDRB_length   Length of the EBCDIC text message

.endif # .ifndef .LDRIVER_S
