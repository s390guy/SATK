.ifndef .LDRVUTIL_S
.LDRVUTIL_S = 1
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

 # This module provides some useful macros for device drivers.  See also drvutil.S
 # for some useful run time tools.

 # Driver Framework related source modules:
 #      DRIVER.S   - Macros and symbols used by programs that call drivers
 #   *  DRVUTIL.S  - Macros and symbols used by drivers participating in the Driver
 #                   Framework
 #      XXX_driver.S Various drivers
 #      driver.S   - Implements the Driver Framework.  Included by a program that
 #                   provides the framework with which drivers are registered or
 #                   called by users of the drivers themselves.
 #
 #   * This source module

 # Macro         Description

 #   drvabort   Issue a device driver abort
 #   sdclear    Sets an area on the stack to zeros 

 #  The following Driver Framework macros are provided
 #
 #    32-bit    64-bit       Description
 #
 #    att       attg       Start an Action Token Table
 #    atte      attge      Create an Action Token Table entry
 #    attend    attend     Terminate an Action Token Table
 #    cbs       cbs        Channel Builder Structure
 #    cpt       cptg       Start a Channel Program Table
 #    cptend    cptend     Terminate a Channel Program Table
 #    dsb       dsbg       Driver Specification Block

 # Device Driver standard aborts
.LDRV_nop = 0x0000   # Device is not operational
.LDRV_lost= 0x0001   # Device status lost
.LDRV_cerr= 0x0002   # Channel error detected
.LDRV_calt= 0x0003   # Channel alert detected
.LDRV_derr= 0x0004   # Device error detected
.LDRV_dalt= 0x0005   # Device alert detected
.LDRV_nodr= 0x0006   # Action Token driver is not registered
.LDRV_noat= 0x0007   # Action not defined by Action Token driver
.LDRV_dder= 0x0008   # Device Definition Entry address invalid (64-bit only)
.LDRV_dbdr= 0x0009   # Driver ID is out of DMT valid range
.LDRV_ddup= 0x000A   # Driver ID is already registered, a duplicate
.LDRV_nodr= 0x000B   # Driver ID is unregistered
.LDRV_drne= 0x000C   # Driver ID in ATTH and Driver Action Token do not match
.LDRV_tkne= 0x000D   # Driver Action Token in ATTE and caller's do not match
.LDRV_toob= 0x000E   # Driver Action Token outside of driver's ATT valid range
.LDRV_noaf= 0x000F   # Driver Action Table Entry missing the action function
.LDRV_nodf= 0x0010   # Driver Framework not initialized
.LDRV_bdtk= 0x0011   # Token Symbol and Driver ID/Action ID of ATTE do not match
.LDRV_tbd = 0x0012   # Requested action is not yet implemented
.LDRV_nosc= 0x0013   # Subchannel could not be identified for the device number
.LDRV_noen= 0x0014   # Device enable failed
.LDRV_nocp= 0x0015   # Required driver CCW Program Table missing
.LDRV_bdpr= 0x0016   # Process model in ATT entry out of bounds
.LDRV_ddtr= 0x0017   # Re-initializing the drivers - usually a bad DRB token

 # See DRIVER.S for Driver ID assigments


  # +---------------------------------+
  # |  Device Definition Entry (DDE)  |
  # +---------------------------------+
  # Access: private - the Driver Framework owns the DDE
  # Macro: none - dynamically created at run-time

    # Size
            struct .LDDE
    # 208 - IOLO Area 
            sbytes .LDDE_IOLO,.LIOLO_len  # 208 bytes
    #  20 - User Program Data                                          DAF Reg
            slong  .LDDE_pgm_data_hi # 64-bit program I/O data address  # R4
            slong  .LDDE_pgm_data_lo # 32-bit program I/O data address  # R5
            slong  .LDDE_pgm_token   # Program's action token           # R2
            shword .LDDE_pgm_length  # Length of program I/O data       # R6
            salign 8                 # CCW's must be on doubleword boundary
   #  200 - Channel Program CCW and IDAW build area 
            sbytes .LDDE_ccws,64     # CCW Build area (8 CCW's)
            sbytes .LDDE_idaws,136   # IDAW2 Build area (17 IDAW's) for 64K data
   #   18 - Driver Framework Area
            slong  .LDDGE_daf        # 64-bit DAF address (for driver use)
            slong  .LDDE_daf         # 32-bit DAF address (for driver use)
            slong  .LDDGE_att        # 64-bit Driver Action Token Table address
            slong  .LDDE_att         # 32-bit Driver Action Token Table address
            shword .LDDE_drvid       # Driver ID (used in bits 0-15 of AT)
   #   40 - Device Information Area
            shword .LDDE_senseid_len
            shword .LDDE_rdc_len
            sbytes .LDDE_sense_id,28 # SENSE ID data
            sbytes .LDDE_rdc,64      # READ DEVICE CHARACTERISTICS data
   #  242 - Driver Work Area
            sbytes .LDDE_wa,182
            shere  .LDDE_len         # 768 bytes (0x300)

.if .LDDE_len-0x300
            .warning ".LDDE_len != 0x300"
            .long   .LDDE_len
.endif # .if .LDDE_len-0x300

  # +--------------------------+
  # | Driver Framework Macros  |
  # +--------------------------+

 # att/attg - Start an Action Token Table
 # attend   - Terminate an Action Token Table
 #
 #  Macro Parameters:
 #     name     Symbol associated with the Action Token Table (required)
 #     id       The Driver ID with which this Action Token Table is associated
 #              (required)
 #     embed    Specify any value to inhibit embedding (default embeds driver)

.Latt_debug = 0  # Set this value to 1 to generate messages during assembly

            .macro att name:req id:req embed
    .ifb \embed
    .ifndef .Ldriver_S
    .if .Latt_debug
           .warning "generating 32-bit embedded driver: \name, ID=\id"
    .endif # .if .Latt_debug
           .text 7
           .long  \name
           .text 0
    .else  # .ifndef .Ldriver_S
           .error "the 32-bit embedded driver list (subsection 7) had been terminated"
           .print "reposition driver.S following this driver"
    .endif # .ifndef .Ldriver_S
    .endif # .ifb \embed
            .align 8
            table  name=\name len=16 hdr=8
            .hword \id,0,0,0
            .endm

            .macro attg name:req id:req embed
    .ifb \embed
    .ifndef .Ldriver_S
    .if .Latt_debug
           .warning "generating 64-bit embedded driver: \name, ID=\id"
    .endif # .if .Latt_debug
           .text 8
           .quad  \name
           .text 0
    .else  # .ifndef .Ldriver_S
           .error "the 64-bit embedded driver list (subsection 7) had been terminated"
           .print "reposition driver.S following this driver"
    .endif # .ifndef .Ldriver_S
    .endif # .ifb \embed
            .align 8
            tableg name=\name len=24 hdr=8
            .hword \id,0,0,0
            .endm

            .macro attend name:req
            tablend name=\name
            .endm


 # atte/attge - Create an Action Token Table entry
 #
 #  Macro Parameters:
 #     token    Token Value associated with this ATTE (required)
 #     func     Symbol identifying the driver function handling this request or
 #              request results (default 0)
 #     cpt      Symbol associated with the Channel Program Table driver framework
 #              uses to process the I/O operation directly (default 0)
 #     proc     DAF process model used for this entry (default 0) - see driver.S
 #
 # Note: Both func and cpt defaulting or set to zero will cause an run-time abort

            .macro atte token:req func=0 cpt=0 proc=0

            .long  \func,\cpt,\token
            .hword \proc,0
            .endm

            .macro attge token:req func=0 cpt=0 proc=0
            .quad  \func,\cpt
            .long  \token
            .hword \proc,0
            .endm


 # cbs - CCW Builder Structure
 #
 #  Macro Parameters:
 #     code     CCW command code
 #     data     Specify the sdwa disp to data, or -1 for user data in sdwa
 #              For TRANSFER IN CHANNEL, data represents the CCW chain index of the
 #              CCW to which the channel program control is passed.
 #     len      Specify the sdwa data length, or -1 for user data length in sdwa
 #     flags    CCW flags (default 0)

            .macro cbs type:req code:req data:req len:req flags=0x00
            .hword \type,\data,\len
            .byte  \code,\flags
            .endm

            # Data within the DDE
            .macro cbs_dde code=req data:req len:req flags=0x00
            cbs    type=0x08,code=\code,data=\data,len=\len,flags=\flags
            .endm

            # Build an immediate CCW
            .macro cbs_imd code:req flags=0x00
            cbs    type=0x0C,code=\code,data=0,len=1,flags=\flags
            .endm

            # CCW Data and length supplied by DRB
            .macro cbs_pgm code:req flags=0x00
            cbs    type=0x00,code=\code,data=0,len=0,flags=\flags
            .endm

            # TRANSFER-IN-CHANNEL CCW
            .macro cbs_tic toccw:req
            cbs    type=0x04,code=0x08,data=\toccw,len=1
            .endm

 # cpt/cptg - Start a Channel Program Table
 # cptend   - Complete a Channel Program Table
 #
 #  Macro Parameters:
 #       name   Symbol associated with this Channel Program Table
 #       ce     Channel errors to be detected (required)
 #       ca     Channel alerts to be detected (required)
 #       de     Device errors to be detected (required)
 #       da     Device alerts to be detected (required)

            .macro cpt name:req ce:req ca:req de:req da:req
            table  name=\name len=8 hdr=4
            .byte  \ce,\ca,\de,\da
            .endm

            .macro cptg name:req ce:req ca:req de:req da:req
            tableg name=\name len=8 hdr=4
            .byte  \ce,\ca,\de,\da
            .endm

            .macro cptend name:req
            tablend name=\name
            .endm

 # drvabort - Generate a device driver abort
 #    error    Specify the error code of the abort (required)
 #    dtype    Specify the device type (required)

            .macro drvabort error:req dtype:req
            .hword 0x00dd,(\dtype<<8)+\error
            .endm

 # sdinit - Initialize IDAWs for use (sets the end of the list indicator)
 #    name    Specify the symbol prefix associated with the work area
 #    r       A register pointing to the sdwork area to be initialized

            .macro sdinit name:req r:req
            mvi    \name\()_idaw+((\name\()_idaws-1)*8)(\r),0x80
            .endm

.if .Lhal_32bit

  # +-------------------------------+
  # |  32-bit Embedded Driver List  |
  # +-------------------------------+
  # Access: private

            .text  7
.LDF_drivers:    # Start the 32-bit Embedded Driver List
            .text  0

.endif # .if .Lhal_32bit

.if .Lhal_s390x

  # +-------------------------------+
  # |  64-bit Embedded Driver List  |
  # +-------------------------------+
  # Access: private

            .text  8
.LDF_drivers64:    # Start the 64-bit Embedded Driver List
            .text  0

.endif # .if .Lhal_s390x

.endif # .ifndef .LDRVUTIL_S
