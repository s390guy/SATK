.ifndef .Lconsole_S
.Lconsole_S = 1
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

 # This driver provides generic I/O support for multiple console device types, in
 # this order of preference:
 #
 #         Facility            Driver    Status             Functionality
 #
 #   1  1052/3215 device      dev3215.S  implementing       input/output
 #   2  HMC                   conhmc.S   to be developed    input/output
 #   3  3270 device           dev3270.S  to be developed    input/output
 #   4  DIAGNOSE X'08'        conD8.S    to be developed    output only
 #
 # This driver supports ASCII/EBCDIC translation and user input/output functions
 #

.Lconsole_3215 = 1
.Lconsole_hmc  = 0
.Lconsole_d8   = 0
.Lconsole_3270 = 0

.if .Lconsole_3215
.ifndef .Ldev3215_S
            .include "dev3215.S"
.endif # .ifndef .Ldev3215_S
.endif # .if .Lconsolse_3215

  # +------------------------------+
  # |  DDE Driver Work Area Usage  |
  # +------------------------------+
  # Access: Driver

            struct .LUIWA,at=.LDDE_wa
            squad  .LUIWA_console_att  # Address of the console driver's ATT
            squad  .LUIWA_phys_att     # Address of the physical driver's ATT
            sbyte  .LUIWA_cdo          # Console device options available
            sbyte  .LUIWA_cdu          # Console device options used

  # Console Options (.LUIWA_cdo)
.LUIWA_cdeva = 0x80  # Console device available
.LUIWA_chmca = 0x40  # Hardware Management Console available
.LUIWA_cdd8a = 0x20  # DIAGNOSE X'08' available
.LUIWA_cga   = 0x10  # 3270 Console device available

 # Console in Use (.LUIWA_cdu)
.LUIWA_cdev  = 0x04  # Using 1052/3215 console device
.LUIWA_chmc  = 0x08  # Using Hardware Management Console
.LUIWA_cd8   = 0x0C  # Using DIAGNOSE X'08' for output
.LUIWA_c3270 = 0x10  # Using a 3270 console device

            .eject
.if .Lhal_32bit
  # +------------------------------------+
  # |  32-bit Console Driver Structures  |
  # +------------------------------------+
  # Access: Driver Framework

  # Define the Common Driver's 32-bit Action Token Table:

            att name=.LUI_att,id=.LDRV_UI
               atte   token=.LUI_Opn_Con,func=.LUI_0    # Configure/Open Console
               atte   token=.LUI_Wrt_Asc,func=.LUI_1    # Write ASCII message
               atte   token=.LUI_Wrt_Ebc,func=.LUI_2    # Write EBCDIC message
            attend name=.LUI_att         

            .eject
  # +------------------------------------------------------+
  # |  32-bit ACTION TOKEN 0 - Configure and Open Console  |
  # +------------------------------------------------------+
  # Access: public
  # Token: .LUI_Opn_Con

  # This function configures the IEIB console fields and picks the console to
  # be used.

  # On entry:
  #    R2     Device Definition Entry for console device
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Caller's DRB
  #    R8     Device number
  #    R9     Return code
  #    R10    Local DRB
  #    R12    Caller's DDE
  #
  # On exit:
  #    R2     Console device type being used (see .LUIWA_cdu) 
  #           0 == Console configuration failed

            func370 .LUI_0     # May be called in either S/370 or ESA/390

    # Local literal pool usage:
.Lconsole_config_att:
            .long  .LUI_att    # Address of my ATT for use in DDE

    # Local stack frame usage:
            fbytes .Lconsole_config_drb,.LDRB_len  # Create a DRB on the frame

            push370

            lr     6,2                        # Preserve caller's DRB
            l      12,.LDRB_dde(6)            # Preserve caller's DDE address
            la     10,.Lconsole_cfg-0b(13)    # Locate routine
            basr   11,10                      # Configure console to use
            
            sr     9,9                           # Clear the result
            ic     9,.LUIWA_cdu(12)              # Fetch the console type
            b      .+4-0b(9,13)                  # Continue depending upon result
            b      .Lconsole_config_ret-0b(13)   # Failure: done
            b      .Lconsole_config_ssid-0b(13)  # 3215: Find subchannel if needed
            b      .Lconsole_config_ret-0b(13)   # HMC: done
            b      .Lconsole_config_ret-0b(13)   # DIAGNOSE X'08': done
            #      Fall through                  # 3270: Find subchannel if needed

.Lconsole_config_ssid:

    # Open the 3215 console device

            drbf   .Lconsole_config_drb,10       # R2 points to my init'd DRB
            st     12,.LDRB_dde(10)              # Point to the caller's DDE
            lh     8,.LIEIB_cdn(0)               # Fetch the device number
            st     8,.LDRB_addr32(10)            # Set the device we are opening
            # Set the 3215 driver id
            mvc    .LDRB_misc(2,10),.Lconsole_config_3215_drvid-0b(13)
            
            # Move the Open Device token to my DRB
            mvc    .LDRB_at(4,10),.Lconsole_config_open_device_token-0b(13)
            lr     2,10                          # Pass the local DRB
            callptr .LDF_daf                     # Call the Driver Access Function

             # Note: we do not come back if the open device fails

            mvc    .LUIWA_phys_att(4,12),.LDDE_att(12)  # Preserve phys drvr ATT
            # Move my ATT to the DDE for future driver actions
            mvc    .LDDE_att(4,12),.Lconsole_config_att-0b(13)
            mvc    .LUIWA_console_att(4,12),.Lconsole_config_att-0b(13)

.Lconsole_config_ret:
            lr     2,9                           # Set the return code
            return                               # Return to caller

            .eject
  # +--------------------------------------------------------+
  # |  32-bit ACTION TOKEN 1 - Console ASCII Write Function  |
  # +--------------------------------------------------------+
  # Access: public
  # Token: .LUI_Wrt_Asc

  # This function translates an ASCII message into EBCDIC and writes it to the
  # console.

  # On entry:
  #    R2     DRB address
  #    R3     
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     Message text length
  #    R3     Message text address
  #    R6     Caller's DRB
  #    R7     ASCII translate table (from .LIEIB)
  #    R8     DDE address
  #    R9     Return code
  #    R10    EBCDIC message location
  #    R11    Shared subroutine return
  #
  # On exit:
  #    R2     Return Code
  #              0 == Console write succeeded
  #              4 == Console write failed due to pending input
  #              8 == Console write failed due to an error condition

            func370 .LUI_1       # May be called in either S/370 or ESA/390

    # Local literal pool
.Lconsole_write_ascii_mvc: # Used by EXECUTE instruction
            mvc   .Lconsole_write_ascii_text(1,15),0(3)  # Preserve input message
.Lconsole_write_ascii_tr:  # Used by EXECUTE instruction
            tr    .Lconsole_write_ascii_text(1,15),0(7)  # Translate ASCII-->EBCDIC
 #.Lconsole_write_ebcdic_tok:
 #          .long .LUI_Wrt_Ebc

    # Local stack frame usage
            fbytes .Lconsole_write_ascii_drb,.LDRB_len
            fbytes .Lconsole_write_ascii_text,256

            push370

            lr     6,2                            # Preserve caller's DRB address

            drbf   .Lconsole_write_ascii_drb,2    # Initialize my DRB
            l      8,.LDRB_dde(6)                 # Locate the DDE
            l      3,.LDRB_addr32(6)              # Locate the ASCII text message
            lh     1,.LDRB_length(6)              # Get message text length
            sth    1,.LDRB_length(2)              # Move it to EBCDIC write DRB
            bctr   1,0               # Decrement for use by execute
            l      7,.LIEIB_a2e(0)   # Locate the ASCII-->EBCDIC translate table
            ex     1,.Lconsole_write_ascii_mvc-0b(13)  # Move message
            ex     1,.Lconsole_write_ascii_tr-0b(13)   # Translate the message
            la     10,.Lconsole_write_ascii_text(15)   # Pass EBCDIC message..
            st     10,.LDRB_addr32(2)                  # ..address for writing
            mvc    .LDRB_dde(4,2),.LDRB_dde(6)    # Pass the DDE for writing
            # Pass the Write EBCDIC token
            mvc    .LDRB_at(4,2),.Lconsole_write_ebcdic_tok-0b(13)

            callptr .LUI_2           # Write the EBCDIC message

            return

            .eject
  # +---------------------------------------------------------+
  # |  32-bit ACTION TOKEN 2 - Console EBCDIC Write Function  |
  # +---------------------------------------------------------+
  # Access: public
  # Token: .LUI_Wrt_Ebc

  # This function configures the IEIB console fields and picks the console to
  # be used.

  # On entry:
  #    R2     DRB Address
  #    R3     Length of EBCDIC message text
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R5     .LDRB_misc to token id conversion
  #    R6     Caller's DRB
  #    R7     EBCDIC message text address
  #    R8     EBCDIC message text length
  #    R9     Return code
  #    R10    Caller's DDE address
  #    R11    Shared subroutine return
  #
  # On exit:
  #    R2     Return Code
  #              0 == Console write succeeded
  #              4 == Console write failed due to pending input
  #              8 == Console write failed due to an error condition
  #             12 == Console write to an unsupported console type or operation
  #                   for console in use

            func370 .LUI_2       # Caller may be either S/370 or ESA/390

.if .Lconsole_3215
            fbytes .Lconsole_write_3215_drb,.LDRB_len
.endif # .if .Lconsole_3215

            push370

            lr     6,2               # Preserve the caller's DRB
            l      7,.LDRB_addr32(6) # Preserve the message text address
            lh     8,.LDRB_length(6) # Preserve the message text length
            l      10,.LDRB_dde(6)   # Fetch caller's DDE
            sr     2,2               # Clear branch table
            ic     2,.LUIWA_cdu(10)  # Fetch the device type being supported
            b      .+4-0b(2,13)      # Branch to supported console device
            b      .Lconsole_write_unsupported-0b(13)  # 0 == unconfigured
.if .Lconsole_3215
            b      .Lconsole_write_3215-0b(13)         # 3215: supported
.else  # .if .Lconsole_3215
            b      .Lconsole_write_unsupported-0b(13)  # 3215: unsupported
.endif # .if .Lconsole_3215
.if .Lconsole_hmc
            b      .Lconsole_write_hmc-0b(13)          # HMC: supported
.else  # .if .Lconsole_hmc
            b      .Lconsole_write_unsupported-0b(13)  # HMC: unsupported
.endif # .if .Lconsole_hmc
.if .Lconsole_d8
            b      .Lconsole_write_d8-0b(13)           # DIAGNOSE X'08': supported
.else  # .if .Lconsole_d8
            b      .Lconsole_write_unsupported-0b(13)  # DIAGNOSE X'08': unsupported
.endif # .if .Lconsole_d8
.if .Lconsole_3270
            b      .Lconsole_write_d8-0b(13)           # 3270: supported
.else  # .Lconsole_3270
            b      .Lconsole_write_unsupported-0b(13)  # 3270: unsupported
.endif # .Lconsole_3270

.if .Lconsole_3215
.Lconsole_write_3215:
            drbf   .Lconsole_write_3215_drb,2        # Locate and clear my DRB
            mvc    .LDDE_att(4,10),.LUIWA_phys_att(10) # Override my ATT with phys.drv
            st     10,.LDRB_dde(2)                   # Pass the DDE
            st     7,.LDRB_addr32(2)                 # Pass message text address
            sth    8,.LDRB_length(2)                 # Pass message text length
            lh     5,.LDRB_misc(6)                   # Locate the message options
            sll    5,2                               # Convert to a displacement
            la     5,.Lconsole_3215_tokens-0b(5,13)  # Convert to an address
            mvc    .LDRB_at(4,2),0(5)                # Move token to DRB
            l      1,.LDDE_daf(10)                   # Locate the DAF 
            callr  1                                 # Write to the console
            mvc    .LDDE_att(4,10),.LUIWA_console_att(10)  # Restore my AT table
            b      .Lconsole_write_return-0b(13)     # Return the return code

.Lconsole_write_unsupported:
            sr     2,2
            la     2,12              # Unconfigured or unsupported console
.endif # .if .Lconsole_3215

.Lconsole_write_return:
            return

.endif # .if .Lhal_32bit

            .eject
.if .Lhal_s390x

  # +------------------------------------+
  # |  64-bit Console Driver Structures  |
  # +------------------------------------+
  # Access: Driver Framework

  # Define the Driver's Action Token Table:

            attg name=.LUI_att64,id=.LDRV_UI
               attge  token=.LUI_Opn_Con,func=.LUIG_0   # Configure/Open Console
               attge  token=.LUI_Wrt_Asc,func=.LUIG_1   # Write ASCII message
               attge  token=.LUI_Wrt_Ebc,func=.LUIG_2   # Write EBCDIC message
            attend name=.LUI_att64

            .eject
  # +------------------------------------------------------+
  # |  64-bit ACTION TOKEN 0 - Configure and Open Console  |
  # +------------------------------------------------------+
  # Access: public

  # This function configures the IEIB console fields and picks the console to
  # be used.

  # On entry:
  #    R2     Device Definition Entry for console device
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Caller's DRB
  #    R8     Device number
  #    R9     Return code
  #    R10    Shared subroutine address
  #    R11    Shared subroutine return
  #    R12    Caller's DDE
  #
  # On exit:
  #    R2     Console device type being used (see .LUIWA_cdu) 
  #           0 == Console configuration failed

            functionx .LUIG_0

    # Local literal pool usage:
.Lconsole_config64_att:
            .quad  .LUI_att64       # Address of my ATT for use in DDE


    # Local stack frame usage
            fbytes .Lconsole_config64_drb,.LDRB_len  # Create a DRB on the frame

            pushx

            lgr    6,2                        # Preserve caller's DRB
            llgt   12,.LDRB_dde(6)            # Preserve caller's DDE address
            la     10,.Lconsole_cfg-0b(13)    # Locate routine
            basr   11,10                      # Configure console to use

            llgc   9,.LUIWA_cdu(12)              # Fetch the console type
            b      .+4-0b(9,13)                  # Continue depending upon result
            b      .Lconsole_config64_ret-0b(13) # Failure: done
            b      .Lconsole_config64_ssid-0b(13)# 3215: Find subchannel if needed
            b      .Lconsole_config64_ret-0b(13) # HMC: done
            b      .Lconsole_config64_ret-0b(13) # DIAGNOSE X'08': done
            #      Fall through                  # 3270: Find subchannel if needed

.Lconsole_config64_ssid:

    # Open the 3215 console device

            drbf   .Lconsole_config64_drb,2      # R2 points to my init'd DRB
            st     12,.LDRB_dde(2)               # Point to the caller's DDE
            lgh    8,.LIEIB_cdn(0)               # Fetch the device number
            st     8,.LDRB_addr32(2)             # Set the device we are opening
            # Set the 3215 driver id
            mvc    .LDRB_misc(2,2),.Lconsole_config_3215_drvid-0b(13)

            # Move the Open Device token to my DRB
            mvc    .LDRB_at(4,2),.Lconsole_config_open_device_token-0b(13)
            callptrx .LDF_daf64                  # Call the Driver Access Function
            # Note: we do not come back if the open device fails

            mvc    .LUIWA_phys_att(8,12),.LDDGE_att(12)  # Preserve phys drvr ATT
            # Move my ATT to the DDE for future driver actions
            mvc    .LDDGE_att(8,12),.Lconsole_config64_att-0b(13)
            mvc    .LUIWA_console_att(8,12),.Lconsole_config64_att-0b(13)

.Lconsole_config64_ret:
            lgr     2,9                          # Set the return code
            returnx                              # Return to caller

            .eject
  # +--------------------------------------------------------+
  # |  64-bit ACTION TOKEN 1 - Console ASCII Write Function  |
  # +--------------------------------------------------------+
  # Access: public
  # Token: .LUI_Wrt_Asc

  # This function translates an ASCII message into EBCDIC and writes it to the
  # console.

  # On entry:
  #    R2     DRB address
  #    R3     
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     Message text length
  #    R3     Message text address
  #    R6     Caller's DRB
  #    R7     ASCII translate table (from .LIEIB)
  #    R8     DDE address
  #    R9     Return code
  #    R10    EBCDIC message location
  #    R11    Shared subroutine return
  #
  # On exit:
  #    R2     Return Code
  #              0 == Console write succeeded
  #              4 == Console write failed due to pending input
  #              8 == Console write failed due to an error condition

            functionx .LUIG_1

    # Local literal pool
.Lconsole_write_ascii_mvc64: # Used by EXECUTE instruction
            mvc   .Lconsole_write_ascii_text64(1,15),0(3)  # Preserve input message
.Lconsole_write_ascii_tr64:  # Used by EXECUTE instruction
            tr    .Lconsole_write_ascii_text64(1,15),0(7)  # Translate ASCII-->EBCDIC
.Lconsole_write_ebcdic_tok64:
            .long .LUI_Wrt_Ebc

    # Local stack frame usage
            fbytes .Lconsole_write_ascii_drb64,.LDRB_len
            fbytes .Lconsole_write_ascii_text64,256

            pushx

            lgr    6,2                            # Preserve caller's DRB address
            
            drbf   .Lconsole_write_ascii_drb64,2  # Initialize my DRB
            llgt   8,.LDRB_dde(6)                 # Locate the DDE
            lg     3,.LDRB_addr(6)                # Locate the ASCII text message
            lgh    1,.LDRB_length(6)              # Get message text length
            sth    1,.LDRB_length(2)              # Move it to EBCDIC write DRB
            bctgr  1,0               # Decrement for use by execute
            lg     7,.LIEIB_a2eg(0)  # Locate the ASCII-->EBCDIC translate table
            ex     1,.Lconsole_write_ascii_mvc64-0b(13)  # Move message
            ex     1,.Lconsole_write_ascii_tr64-0b(13)   # Translate the message
            la     10,.Lconsole_write_ascii_text64(15)   # Pass EBCDIC message..
            stg    10,.LDRB_addr(2)                      # ..address for writing
            mvc    .LDRB_dde(4,2),.LDRB_dde(6)    # Pass the DDE for writing
            # Pass the Write EBCDIC token
            mvc    .LDRB_at(4,2),.Lconsole_write_ebcdic_tok-0b(13)

            callptrx .LUIG_2          # Write the EBCDIC message

            returnx
            .eject
  # +---------------------------------------------------------+
  # |  64-bit ACTION TOKEN 2 - Console EBCDIC Write Function  |
  # +---------------------------------------------------------+
  # Access: public
  # Token: .LUI_Wrt_Ebc

  # This function configures the IEIB console fields and picks the console to
  # be used.

  # On entry:
  #    R2     DRB Address
  #    R3     Length of EBCDIC message text
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R5     .LDRB_misc to token id conversion
  #    R6     Caller's DRB
  #    R7     EBCDIC message text address
  #    R8     EBCDIC message text length
  #    R9     Return code
  #    R10    Caller's DDE address
  #    R11    Shared subroutine return
  #
  # On exit:
  #    R2     Return Code
  #              0 == Console write succeeded
  #              4 == Console write failed due to pending input
  #              8 == Console write failed due to an error condition
  #             12 == Console write to an unsupported console type or operation
  #                   for console in use

            functionx .LUIG_2       # Caller may be either S/370 or ESA/390

.if .Lconsole_3215
            fbytes .Lconsole_write_3215_drb64,.LDRB_len
.endif # .if .Lconsole_3215

            pushx

            lgr    6,2               # Preserve the caller's DRB
            lg     7,.LDRB_addr(6)   # Preserve the message text address
            lgh    8,.LDRB_length(6) # Preserve the message text length
            llgt   10,.LDRB_dde(6)   # Fetch caller's DDE
            llgc   2,.LUIWA_cdu(10)  # Fetch the device type being supported
            b      .+4-0b(2,13)      # Branch to supported console device
            j      .Lconsole_write_unsupported64         # 0 == unconfigured
.if .Lconsole_3215
            j      .Lconsole_write_3215_64               # 3215: supported
.else  # .if .Lconsole_3215
            j      .Lconsole_write_unsupported64         # 3215: unsupported
.endif # .if .Lconsole_3215
.if .Lconsole_hmc
            j      .Lconsole_write_hmc64                 # HMC: supported
.else  # .if .Lconsole_hmc
           j      .Lconsole_write_unsupported64          # HMC: unsupported
.endif # .if .Lconsole_hmc
.if .Lconsole_d8
            j      .Lconsole_write_d8_64                 # DIAGNOSE X'08': supported
.else  # .if .Lconsole_d8
            j      .Lconsole_write_unsupported64         # DIAGNOSE X'08': unsupported
.endif # .if .Lconsole_d8
.if .Lconsole_3270
            j      .Lconsole_write_3270_64               # 3270: supported
.else  # .Lconsole_3270
            j      .Lconsole_write_unsupported64         # 3270: unsupported
.endif # .Lconsole_3270

.if .Lconsole_3215
.Lconsole_write_3215_64:
            drbf   .Lconsole_write_3215_drb64,2      # Locate and clear my DRB
            mvc    .LDDGE_att(8,10),.LUIWA_phys_att(10) # Override my ATT with phys.drv
            st     10,.LDRB_dde(2)                   # Pass the DDE
            stg    7,.LDRB_addr(2)                   # Pass message text address
            sth    8,.LDRB_length(2)                 # Pass message text length
            lgh    5,.LDRB_misc(6)                   # Locate the message options
            sllg   5,5,2                             # Convert to a displacement
            la     5,.Lconsole_3215_tokens-0b(5,13)  # Convert to an address
            mvc    .LDRB_at(4,2),0(5)                # Move token to DRB
            lg     1,.LDDGE_daf(10)                  # Locate the DAF 
            callrx 1                                 # Write to the console
            mvc    .LDDGE_att(8,10),.LUIWA_console_att(10) # Retore my AT table
            j      .Lconsole_write_return64          # Return the return code

.Lconsole_write_unsupported64:
            lghi    2,12              # Unconfigured or unsupported console
.endif # .if .Lconsole_3215

.Lconsole_write_return64:
            returnx
.endif # .if .Lhal_s390x

           .eject

  # +---------------------------------------+
  # |  Message Option to driver token list  |
  # +---------------------------------------+
  # Access: private

.Lconsole_3215_tokens:
           .long   .LCON_Wrt_Cr
           .long   .LCON_Wrt_CrA
           .long   .LCON_Wrt_NoC
           .long   .LCON_Wrt_Alm
           .long   .LCON_Alarm

.Lconsole_config_open_device_token:
            .long  .LCMN_Opn_Dev
.Lconsole_write_ebcdic_tok:
            .long  .LUI_Wrt_Ebc
.Lconsole_config_3215_drvid:
            .hword .LDRV_CON    #3215 Console Driver ID

  # +-------------------------------------------+
  # |  Console configuration shared subroutine  |
  # +-------------------------------------------+
  # Access: private

  # On entry:
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return
  #    R12    DDE address
  #
  # Used: none
  # On exit: none

.Lconsole_cfg:
0:
           tm      .LIEIB_plt(0),.LIEIB_D8        # DIAGNOSE X'08' available?
           bno     .+8-0b(10)                     # ..No, do not set indicator
           oi      .LUIWA_cdo(12),.LUIWA_cdd8a    # ..yes, set indicator
           tm      .LIEIB_plt(0),.LIEIB_cons      # Console device available?
           bno     .+8-0b(10)                     # ..no, do not set indicator
           oi      .LUIWA_cdo(12),.LUIWA_cdeva    # ..yes, set indicator
           tm      .LIEIB_run(0),.LIEIB_s390x|.LIEIB_s390 # HMC available?
           bz      .+8-0b(10)                     # ..no, do not set indicator
           oi      .LUIWA_cdo(12),.LUIWA_chmca    # ..yes, set indicator
     # Note: additional code is needed to identify 3270 consoles

           mvi     .LUIWA_cdu(12),0x00            # Using console type unconfigured
.if .Lconsole_3215
           tm      .LUIWA_cdo(12),.LUIWA_cdeva    # Is line-mode console available?
           bno     .Lconsole_cfg_no_3215-0b(10)   # ..no, check next possible option
           mvi     .LUIWA_cdu(12),.LUIWA_cdev     # Indicate 3215 console
           br      11                             # Return to caller
.Lconsole_cfg_no_3215:
.endif # .if .Lconsole_3215

.if .Lconsole_hmc
           tm      .LUIWA_cdo(12),.LUIWA_chmca    # Is HMC available?
           bno     .Lconsole_cfg_no_hmc-0b(10)    # ..no, check next possible option
           mvi     .LUIWA_cdu(12),.LUIWA_chmc     # Indicate HMC
           br      11                             # Return to caller
.Lconsole_cfg_no_hmc:
.endif

.if .Lconsole_3270
           tm      .LUIWA_cdo(12),.LUIWA_cga      # Is 3270 available?
           bno     .Lconsole_cfg_no_3270-0b(10)   # ..no, return
           mvi     .LUIWA_cdu(12),.LUIWA_c3270    # Indicate 3270 console
           br      11                             # Return to caller
.Lconsole_cfg_no_3270:
.endif # .if .Lconsole_3270

.if .Lconsole_d8
           tm      .LUIWA_cdo(12),.LUIWA_cdd8a    # Is DIAGNOSE X'08' available?
           bnor     11                            # ..no, check next possible option
           mvi     .LUIWA_cdu(12),..LUIWA_cd8     # Indicate DIAGNOSE X'08' console
.Lconsole_cfg_no_d8:
.endif # .if .Lconsole_d8
           br      11                             # Return to caller

.endif # .ifndef .Lconsole_S
