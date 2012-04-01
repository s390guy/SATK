.ifndef .Ldev3215_S
.Ldev3215_S = 1
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

 # This driver provides I/O support for 3215/1052 type console based upon the
 # Low-Level I/O abstractions (halfeat io=low).
 #
 # A program using this driver must provide a driver work area.  Driver work areas
 # must be addressable by the I/O architecture in use.  Use symbol .LCON_len to 
 # determine the DWA length.
 #
 # Dependencies:
          .include "DRVUTIL.S"   # Macros used by drivers

.if .Lhal_32bit

  # +---------------------------------------------+
  # |  1052/3215 32-bit Device Driver Structures  |
  # +---------------------------------------------+
  # Access: Driver Framework

  # Define the Driver's Action Token Table:

    att name=.LCON_att,id=.LDRV_CON
      # WRITE CR
        atte token=.LCON_Wrt_Cr, func=.LCON_Wrt_Rslt,cpt=.LCON_wc, proc=0x000C
      # ALARM, WRITE CR
        atte token=.LCON_Wrt_CrA,func=.LCON_Wrt_Rslt,cpt=.LCON_awc,proc=0x000C
      # WRITE NO CR  
        atte token=.LCON_Wrt_NoC,func=.LCON_Wrt_Rslt,cpt=.LCON_w,  proc=0x000C
      # ALARM, WRITE NO CR  
        atte token=.LCON_Wrt_Alm,func=.LCON_Wrt_Rslt,cpt=.LCON_aw, proc=0x000C
      # ALARM only  
        atte token=.LCON_Alarm  ,func=.LCON_Wrt_Rslt,cpt=.LCON_alm,proc=0x000C
    attend name=.LCON_att

  # +--------------------------------------------------------+
  # |  32-bit Console Device Message Output Result Analysis  |
  # +--------------------------------------------------------+
  # Access: private

  # On entry:
  #    R2     DDE address
  #    R3     Return code from Driver Framework I/O Assist Function
  #
  # Used:
  #    R6     Return code for message caller
  #
  # On Exit:
  #    R2     Console I/O result:
  #              0 -->  Success, message displayed
  #              4 -->  Input pending
  #              8 -->  Console device not available

            func370 .LCON_Wrt_Rslt

  # Local literal pool usage:
.LCON_Wrt_Rslt_rc4:
            .hword 4
.LCON_Wrt_Rslt_rc8:
            .hword 8

            push370

            b      .+4-0b(3,13)           # Handle I/O conditions
            b      .LCON_Wrt_Rslt_success-0b(13)         #  0, successful
            b      .LCON_Wrt_Rslt_failure-0b(13)         #  4, not-operational
            drvabort error=.LDRV_lost,dtype=.LDRV_CON    #  8, status lost
            drvabort error=.LDRV_cerr,dtype=.LDRV_CON    # 12, channel error
            drvabort error=.LDRV_calt,dtype=.LDRV_CON    # 16, channel alert
            b      .LCON_Wrt_Rslt_failure-0b(13)         # 20, device error
            # Fall through on device alert                 24, device alert (ATTN)

            lh     2,.LCON_Wrt_Rslt_rc4-0b(13)    # Set rc==4 (input pending)
            b      .LCON_Wrt_Rslt_return-0b(13)   # Return to caller

.LCON_Wrt_Rslt_failure:
            lh     2,.LCON_Wrt_Rslt_rc8-0b(13)    # Set rc==8 (failed)
            b      .LCON_Wrt_Rslt_return-0b(13)   # Return to caller

.LCON_Wrt_Rslt_success:
            sr     2,2                            # Set rc==0 (success)

.LCON_Wrt_Rslt_return:
            return

.endif # .if .Lhal_32bit

.if .Lhal_s390x

  # +---------------------------------------------+
  # |  1052/3215 64-bit Device Driver Structures  |
  # +---------------------------------------------+
  # Access: Driver Framework

  # Define the Driver's Action Token Table:

     attg name=.LCON_att64,id=.LDRV_CON
        # WRITE CR
          attge token=.LCON_Wrt_Cr, func=.LCON_Wrt_Rslt64,cpt=.LCON_wcg, proc=0x000C
        # ALARM, WRITE CR
          attge token=.LCON_Wrt_CrA,func=.LCON_Wrt_Rslt64,cpt=.LCON_awcg,proc=0x000C
        # WRITE NO CR
          attge token=.LCON_Wrt_NoC,func=.LCON_Wrt_Rslt64,cpt=.LCON_wg,  proc=0x000C
        # ALARM, WRITE NO CR
          attge token=.LCON_Wrt_Alm,func=.LCON_Wrt_Rslt64,cpt=.LCON_awg, proc=0x000C
        # ALARM only
          attge token=.LCON_Alarm  ,func=.LCON_Wrt_Rslt64,cpt=.LCON_almg,proc=0x000C
    attend name=.LCON_att64

  # +--------------------------------------------------------+
  # |  64-bit Console Device Message Output Result Analysis  |
  # +--------------------------------------------------------+
  # Access: private

  # On entry:
  #    R2     DDE address
  #    R3     Return code from Driver Framework I/O Assist Function
  #
  # Used:
  #    R6     Return code for message caller
  #
  # On Exit:
  #    R2     Console I/O result:
  #              0 -->  Success, message displayed
  #              4 -->  Input pending
  #              8 -->  Console device not available

            functionx .LCON_Wrt_Rslt64
            pushx

            b      .+4-0b(3,13)           # Handle I/O conditions
            j      .LCON_Wrt_Rslt64_success              #  0, successful
            j      .LCON_Wrt_Rslt_failure                #  4, not-operational
            drvabort error=.LDRV_lost,dtype=.LDRV_CON    #  8, status lost
            drvabort error=.LDRV_cerr,dtype=.LDRV_CON    # 12, channel error
            drvabort error=.LDRV_calt,dtype=.LDRV_CON    # 16, channel alert
            j      .LCON_Wrt_Rslt64_failure              # 20, device error
            # Fall through on device alert                 24, device alert (ATTN)

            lghi   2,4                            # Set rc==4 (input pending)
            j      .LCON_Wrt_Rslt64_return        # Return to caller

.LCON_Wrt_Rslt64_failure:
            lghi   2,8                            # Set rc==8 (failed)
            j      .LCON_Wrt_Rslt64_return        # Return to caller

.LCON_Wrt_Rslt64_success:
            sr     2,2                            # Set rc==0 (success)

.LCON_Wrt_Rslt64_return:
            returnx


.endif # .if .Lhal_s390x

  # +--------------------------------------------------+
  # |  1052/3215 Device Driver Channel Program Tables  |
  # +--------------------------------------------------+
  # Access: Driver Framework

 # 1052/3215 Console Channel Commands:

.LCON_alarm    = 0x0B   # AUDIBLE ALARM
.LCON_nop      = 0x03   # CONTROL NO-OPERATION
.LCON_read     = 0x0A   # READ INQUIRY
.LCON_sense    = 0x04   # SENSE
.LCON_sense_id = 0xE4   # SENSE ID
.LCON_write    = 0x01   # WRITE NO CARRIER RETURN
.LCON_write_cr = 0x09   # WRITE AUTO CARRIER RETURN

 # Define I/O Conditions Detected
.LCON_ce    =    0xFF   # Channel errors: all channel related status
.LCON_ca    =    0x00   # Channel alerts: none
.LCON_de    =    0x43   # Device errors: SM (0x40), UC (0x02), UE (0x01)
.LCON_da    =    0x80   # Device alerts: AT (0x80)

    # Define some macros to allow reuse of cbs 

            .macro con_alarm 
            cbs_imd  code=.LCON_alarm,flags=.LCCW_CC+.LCCW_SLI
            .endm

            .macro con_write_cr
            cbs_pgm code=.LCON_write_cr
            .endm

            .macro con_write_nocr
            cbs_pgm code=.LCON_write
            .endm

.if .Lhal_32bit
    # 32-bit Channel Program Tables

        # AUDIBLE ALARM, WRITE NO CARRIER

            cpt name=.LCON_aw,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
                con_write_nocr
            cptend name=.LCON_aw

        # AUDIBLE ALARM, WRITE CARRIER

            cpt name=.LCON_awc,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
                con_write_cr
            cptend name=.LCON_awc

        # WRITE NO CARRIER (no alarm)

            cpt name=.LCON_w,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_write_nocr
            cptend name=.LCON_w

        # WRITE CARRIER (no alarm)

            cpt name=.LCON_wc,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_write_cr
            cptend name=.LCON_wc

        # AUDIBLE ALARM

            cpt name=.LCON_alm,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
            cptend name=.LCON_alm

.endif # .if .Lhal_32bit

.if .Lhal_64bit
    # 64-bit Channel Program Tables

        # AUDIBLE ALARM, WRITE NO CARRIER

            cptg name=.LCON_awg,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
                con_write_nocr
            cptend name=.LCON_awg

        # AUDIBLE ALARM, WRITE CARRIER

            cptg name=.LCON_awcg,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
                con_write_cr
            cptend name=.LCON_awcg

        # WRITE NO CARRIER (no alarm)

            cptg name=.LCON_wg,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_write_nocr
            cptend name=.LCON_wg

        # WRITE CARRIER (no alarm)

            cptg name=.LCON_wcg,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_write_cr
            cptend name=.LCON_wcg

        # AUDIBLE ALARM

            cptg name=.LCON_almg,ce=.LCON_ce,ca=.LCON_ca,de=.LCON_de,da=.LCON_da
                con_alarm
            cptend name=.LCON_almg
.endif # .if .Lhal_64bit


.endif # .ifndef .Ldev3215_S
