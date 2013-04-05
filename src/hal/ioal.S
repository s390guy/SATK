.ifndef .Lioal_S
.Lioal_S = 1
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

 # This module contains the I/O Hardware Abstraction Layer ABI-compliant functions
 #
 # ioal.S is automatically included by hals.S if io=yes or io=0x000x was
 # specified on the halfeat macro.
 #
 # Functions:
 #
 #  Abstraction   32-bit channel    32-bit I/O subsystem     64-bit I/O subsystem
 #  Included ifdef .Lioal_s370           .Lioal_s390             .Lioal_s390x
 #
 #  DATA          .Lioal_data_chan  .Lioal_data_s390         .Lioal_data_s390x
 #  DATA IDA      .Lioal_datp_chan  .Lioal_datp_s390         .Lioal_unsup
 #  EXECUTE IO    .Lioal_io_chan    .Lioal_io_s390           .Lioal_io_s390x
 #  INIT IO       .Lioal_init_s370  .Lioal_init_s390         .Lioal_init_s390x
 #  QUERY DEVICE  .Lioal_qdev_chan  .Lioal_qdev_s390         .Lioal_qdev_s390x
 #  SET DEVICE    .Lioal_sdev_chan  .Lioal_sdev_s390         .Lioal_sdev_s390x
 #
 # HAL Error Codes
 #  See HAL.S for a complete listing of error codes
 #
 # Dependencies:
 #
            .include "ASB.S"   # Include HAL Support if not already included
            .include "io.S"    # I/O Structures if not already included
            .include "s370.S"  # S/370 I/O instruction macros

.if .Lhal_s370
            .sbttl "I/O Hardware Abstraction Layer - s370"
            .eject
  # Macros used by the IO Hardware Abstraction Layer

            .macro savecsw scswr:req
            mvc    .LSCSW_status(1,\scswr),.LIO_csw_key  # Save status from CSW
            mvi    .LSCSW_ccw(\scswr),0x00               # Set bits 0-7 of addr to 0
            mvc    .LSCSW_ccw+1(7,\scswr),.LIO_csw_ccw   # Save CCW addr and status
            ni     .LSCSW_status(\scswr),0xF0            # Clear SCSW bits
            .endm

            .macro srchdt devidr:req dtr:req found:req br=13 b=0b
            l      \dtr,.Lioal_DT_start-\b(\br)  # Locate the first entry
2:          cl     \dtr,.Lioal_DT_end-\b(\br)    # Is the table empty or at end?
            bc     0b1010,3f-\b(\br)         # ..Yes, then not found
            ch     \devidr,.LPMCW_dev(\dtr)  # Is this the device?
            be     \found-\b(\br)            # ..Yes, found it (\dtr points to it)
            la     \dtr,.Lioal_DT_size(\dtr) # Point to the next SCHIB
            b      2b-\b(\br)                # ..No, maybe this is the one
3:
            .endm

  # +----------------------------------+
  # |  System/370 INIT IO abstraction  |
  # +----------------------------------+

  # On entry:
  #    R2     Starting address reserved for the Device Table 
  #    R3     Last address reserved for the Device Table
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Pointer to the ASB
  #    R7     Used to test if interrupt abstractions are enabled
  #
  # On exit: none

            func370 .Lioal_init_s370
            push370

            icm     7,0b1111,.Lihstk(0)    # Interrupt abstractions enabled?
            bnz     .+8-0b(13)             # ..yes, continue with INIT IO
            halabort error=0x000C          # ..no, need interrupt abstractions
            st      2,.Lioal_DT_start-0b(13)  # Save the start of the DT
            st      2,.Lioal_DT_end-0b(13) # Save the end (at init start == end)
            st      3,.Lioal_DT_max-0b(13) # Save the maximum size of the DT

            l       6,.LIEIB_asb(0)        # Locate the active ASB
            mvc     .LPSW_newio(8,0),.LASB_ionpsw(6)  # Set I/O new 64-bit PSW
            lctl    2,2,.LASB_cr2(6)       # Initialize CR2
            lctl    6,6,.LASB_cr6(6)       # Initialize CR6
            oc      .LASB_amode(2,6),.LASB_amode(6)  # Need to set address mode?
            bz      .Lioal_init_s370_return-0b(13)   # ..No, just return then
            ex      0,.LASB_amode(6)       # ..Yes, then set it

.Lioal_init_s370_return:
            return

  # +---------------------------------+
  # |  System/370 IO DATA abstraction |
  # +---------------------------------+ 

  # On entry:
  #    R2     ORB address (the ORB CCW address identifies the CCW1 being modified)
  #    R3     Program data address
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Address of the ORB whose CCW1 is being modified (CCW0 subroutine)
  #    R7     Data address (CCW0 subroutine)
  #    R8     ORB address
  #
  # On exit:
  #    CCW0 contains valid program data addressing

            func370 .Lioal_data_chan
            push370

            # Bits 0-7 of the 32-bit address are ignored
            lr      6,2                      # Pass the ORB to the CCW0 routine
            lr      7,3                      # Pass address to the CCW0 routine
            bas     11,.Lioal_ccw0-0b(13)    # Use the common CCW0 setup routine
            return

.if .Lhal_s390x

  # +-------------------------------------+
  # |  System/370 IO DATA IDA abstraction |
  # +-------------------------------------+ 

  # On entry:
  #    R2     IDAW address
  #    R3     ORB address  (the ORB CCW address identified the CCW being modified)
  #    R4     Program data address (bits 0-31)
  #    R5     Program data address (bits 32-64)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     ORB address for the CCW0 subroutine
  #    R7     Data address for CCW0 subroutine
  #
  # On exit:
  #    R2     next IDAW (IDAW's are not used with S/370 so R2 is not changed)
  #    CCW0 contains valid program data addressing

            func370 .Lioal_datp_chan
            push370

            # Bits 0-39 of the 64-bit address are ignored
            lr      6,3                      # Pass the ORB to the CCW0 routine
            lr      7,5                      # Pass address to the CCW0 routine
            bas     11,.Lioal_ccw0-0b(13)    # Use the common CCW0 setup routine
            return

.endif # .if ioal_s390x scope

  # +-------------------------------------+
  # |  System/370 INITIATE IO abstraction |
  # +-------------------------------------+ 

  # On entry:
  #    R2     ORB address
  #    R3     Device id (device CCUU address, bits 16-31)
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R6     Condition code from START I/O instruction
  #    R7     SCHIB of located DEVICE TABLE entry
  #    R8     SCSW in SCHIB
  #
  # On exit:
  #    R2     Condition code as it would be for a real STORE SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            func370 .Lioal_doio_chan
            push370

            srchdt devidr=3,dtr=7,found=.Lioal_doio_chan_found
            # Not found, so consider device not operational

.Lioal_doio_chan_not_found:
            lh     2,.Lioal_cc3-0b(13)     # Indicate device not operational
            b      .Lioal_doio_chan_return-0b(13)  # Return to caller

.Lioal_doio_chan_found:   
            tm     .LPMCW_f2(5),.LPMCW_enable      # Enabled?
            bno    .Lioal_doio_chan_not_found-0b(13) # ..No, then not oper
            tm     .LSCHIB_SCSW+.LSCSW_sc(5),.LSCSW_statpend  # Status pending?
            bno    .Lioal_doio_chan_start-0b(13)   # ..No, do the I/O
            lh     2,.Lioal_cc1-0b(13)             # ..Yes, Set cc to 1
            b      .Lioal_doio_chan_return         # Return to caller

.Lioal_doio_chan_start:
            tm     .LSCHIB_SCSW+.LSCSW_ctl(7),.LSCSW_busy # busy?
            bnz    .Lioal_doio_chan_busy-0b(13)    # ..Yes, function in progress

            # Initiate the I/O at the device
            l      6,.Lioal_asb-0b(13)             # Locate current ASB
            # Doing initial I/O, not a concurrent SENSE operation
            ni     .LSCHIB_SCSW+.LSCSW_ctl(7),0xFF-.LSCSW_docs
            mvc    .LIO_caw+1(3,0),.LORB_pgm+1(3)  # Put CCW chain address in CAW
            mvc    .LIO_caw(1,0),.LORB_key(3)      # Put storage key in CAW
            ni     .LIO_caw(0),0xF0                # Set CAW reserved bits to zero
            # Indicate concurrent sense data is not present
            ni     .LIRB_ESW_erw(4),0xFF-.LIRB_ESW_csense

            sio    0,2                     # Start the I/O
            savecc24 6                      # Place the cc in R1
            bc     0b1000,.Lioal_doio_chan_started-0b(13)   # -> started
            bc     0b0100,.Lioal_doio_chan_csw-0b(13)       # -> CSW stored
            bc     0b0010,.Lioal_doio_chan_return_cc-0b(13) # -> busy
            # Not operational, update the SCSW in the SCHIB

            oi     .LSCHIB_SCSW+.LSCSW_f1(7),.LSCSW_f1_nop  # Indicate not oper
            b      .Lioal_doio_chan_return_cc-0b(13)    # Return to caller

.Lioal_doio_chan_started:
            oi     .LSCHIB_SCSW+.LSCSW_ctl(7),.LSCSW_start  # Start in progress
            b      .Lioal_doio_chan_return_cc-0b(13)  # and return

.Lioal_doio_chan_busy:
            lh     2,.Lioal_cc2-0b(13)             # Set cc to 2
            b      .Lioal_doio_chan_return-0b(13)  # Return

.Lioal_doio_chan_csw:
            la     8,.LSCHIB_SCSW(7)                # Locate the SCSW
            savecsw scswr=8                         # Save CSW info in SCSW
            oi     .LSCSW_sc(5),.LSCSW_statpend     # Status pending?

.Lioal_doio_chan_return_cc:
            lr      2,6
.Lioal_doio_chan_return:
            return

  # +--------------------------------------+
  # |  System/370 QUERY DEVICE abstraction |
  # +--------------------------------------+ 

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (device CCUU address, bits 16-31)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R6     Condition code from TEST I/O instruction
  #    R7     DT entry pointer for scanning the DT
  #
  # On exit:
  #    R2     Condition code as it would be for a real STORE SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            func370 .Lioal_qdev_chan
            push370

            srchdt devidr=3,dtr=7,found=.Lioal_qdev_chan_found
            # Not found, so build a brand new SCHIB

            tio    0,3                        # Test if the device is operational
            balr   6,0                        # Put the cc in bits 2,3
            sll    6,2                        # Put the cc in bits 0,1 (clear ILC)
            srl    6,30                       # Put the condition code in bits 30,31
            bc     0b0001,.Lioal_qdev_chan_return-0b(13)  # Not operational

            # Device is operational, so save the SCHIB
            mvi    0(2),0x00                  # Clear the SCHIB
            mvc    1(.LSCHIB_len-1,2),0(2)    # ..to zeros

            # Set the "installed" or "initial" values in the SCHIB
            sth    3,.LPMCW_dev(2)            # 1.2,3  Set the device number
            oi     .LPMCW_f1(2),.LPMCW_devval # 1.1    V bit
            mvi    .LPMCW_lpm(2),0x80         # 2.0    Logical Path Mask
            mvi    .LPMCW_pim(2),0x80         # 2.3    Path Installed Mask
            mvi    .LPMCW_pom(2),0xFF         # 3.2    Path Operational Mask
            mvi    .LPMCW_pam(2),0x80         # 3.3    Path Available Mask
            stcm   3,0b0010,.LPMCW_chpid0(2)  # 4.0    CHPID-0
            # Make sure all reserved or unsupported values are zero
            nc     .LSCHIB_PMCW(.LPMCW_len,2),.Lioal_pmcw_mask-0b(13)

            ch     6,.Lioal_cc1-0b(13)        # Did TIO save the CSW?
            bne    .Lioal_qdev_chan_saved-0b(13)  # ..no, SCHIB is done

            la     2,.LSCHIB_SCSW(2)         # Point to SCSW
            savecsw scswr=2                  # Save the CSW in the SCHIB's SCSW
            b      .Lioal_qdev_chan_saved-0b(13) # SCHIB has been saved

.Lioal_qdev_chan_found:
            mvc    0(.LSCHIB_len,2),0(7)     # "save" the SCHIB from the DT entry
            nc     0(.LSCHIB_len,2),.Lioal_pmcw_mask-0b(13) # Clear reserved bits

.Lioal_qdev_chan_saved:
            sr     6,6

.Lioal_qdev_chan_return:
            lr   2,6
            return

  # +------------------------------------------+
  # |  System/370 QUERY INTERRUPT abstraction  |
  # +------------------------------------------+ 

  # On entry:
  #    R2     IRB address
  #    R3     Device id (device CCUU address, bits 16-31)
  #    R4     IIB address (optional)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R6     Condition code
  #    R7     SCHIB in DEVICE TABLE entry
  #    R8     Concurrent SENSE data area in IRB
  #    R9     Active ASB
  #
  # On exit:
  #    R2     Condition code as it would be for a real STORE SUBCHANNEL instruction
  #              0 -->  Status was pending,
  #              1 -->  Status was not pending
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            func370 .Lioal_qint_chan
            push370

            ltr    4,4                              # IIB available?
            bz     .Lioal_qint_chan_find-0b(13)     # ..No, find in device table
            l      7,.LIIBG_pgm(4)                  # ..Yes, use its address
            b      .Lioal_qint_chan_found-0b(13)    # Found...

.Lioal_qint_chan_find:
            srchdt devidr=3,dtr=7,found=.Lioal_qint_chan_found
            # Not found, so treat as not operational

.Lioal_qint_chan_disabled:
            lh     2,.Lioal_cc3-0b(13)              # Set cc to 3
            b      .Lioal_qint_chan_return-0b(13)   # and return

.Lioal_qint_chan_found:
            tm     .LPMCW_f2(7),.LPMCW_enable       # Is SCHIB enabled?
            bno    .Lioal_qint_chan_disabled-0b(13) # ..Yes, also return cc 3
            
            tm     .LSCHIB_SCSW+.LSCSW_sc(7),.LSCSW_statpend # Status pending?
            bo     .Lioal_qint_chan_pending-0b(13)  # ..Yes, set cc to 0
            lh     6,.Lioal_cc1-0b(13)              # ..No, set cc to 1
            b      .Lioal_qint_chan_save_status-0b(13)  # Now save IRB
.Lioal_qint_chan_pending:
            sr     6,6                              # Set cc to 0
.Lioal_qint_chan_save_status:
            mvc    0(.LSCSW_len,2),.LSCHIB_SCSW(7)  # Move the SCSW into the IRB
            mvi    .LIRB_ESW(2),0x00                # Clear the rest of the IRB
            mvc    .LIRB_ESW+1(.LIRB_len-(.LSCSW_len+1),2),.LIRB_ESW(2)
            # Status is now nolonger pending
            ni     .LSCHIB_SCSW+.LSCSW_sc(7),0xFF-.LSCSW_statpend

            tm     .LPMCW_f2(7),.LPMCW_f2_cs        # Concurrent sense?
            bno    .Lioal_qint_chan_return_cc-0b(13)  # ..No, return now regardless
            tm     .LSCHIB_SCSW+.LSCSW_ds(7),.LSCSW_uc  # ..Yes, is SENSE needed?
            bno    .Lioal_qint_chan_return_cc-0b(13)  # ..No, return

            # Concurrent SENSE needed
            la      8,.LIRB_ECW(2)                   # Locate sense location
            mvi     0(8),0x00                        # Clear sense area 
            mvc     1(31,8),0(8)                     # ..to zeros
            mvc     .LIRB_ESW_erw(4,2),0(8)          # Clear ERW to zeros
            # Place the address in the SENSE CCW
            stcm    7,0b0111,.Lioal_qint_chan_sense_addr-0b(13)
            la      7,.Lioal_qint_chan_sense_ccw-0b(13) # Locate the command
            stcm    7,0b0111,.LIO_caw+1(0)           # Save it in the CAW
            mvi     .LIO_caw(0),0x00                 # Set storage key to zero

            sio    0,3                        # Start the I/O
            bc     0b0111,.Lioal_qint_chan_return_cc-0b(13)   # -> not started

            # Concurrent SENSE in progress
            oi     .LSCHIB_SCSW+.LSCSW_ctl(7),.LSCSW_docs
            l      9,.Lioal_asb-0b(13)        # Locate the active ASB
            lpsw   .LASB_waitcs(9)            # Wait for SENSE to complete

.Lioal_qint_cs_done:  # Interrupt handler will get us back here
            sr      0,0                              # Clear R0
            la      0,32                             # Set R0 to 32
            sh      0,.LIO_csw_cnt(0)                # Calculate sense bytes
            stc     0,.LIRB_ESW_erw+1(2)             # Set sense bytes in ERW
            oi      .LIRB_ESW_erw(2),.LIRB_ESW_csense   # Indicate sense present

.Lioal_qint_chan_return_cc:
            lr     2,6                              # Set the return code
.Lioal_qint_chan_return:
            return

            .align 8
.Lioal_qint_chan_sense_ccw:  # CCW0 used for concurrent sense emulation
            .byte  .LCCW_SENSE
.Lioal_qint_chan_sense_addr:
            .byte  0,0,0
            .byte  .LCCW_SLI,0
            .hword 32

  # +-------------------------------------+
  # |  System/370 SET DEVICE abstraction  |
  # +-------------------------------------+ 

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (device CCUU address, bits 16-31)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R6     Condition code from TEST I/O instruction
  #    R7     DT entry pointer for scanning the DT
  #    R8     Pointer to SCSW
  #    R9     Next DT SCHIB entry
  #    R10    Next entry will go here after this is added
  #    R11    Where 
  #
  # On exit:
  #    R2     Condition code as it would be for a real MODIFY SUBCHANNEL instruction
  #              0 -->  SCHIB modified
  #              1 -->  Status pending, SCHIB not modified
  #              2 -->  Busy, SCHIB not modified
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            func370 .Lioal_sdev_chan
            push370

            srchdt devidr=3,dtr=7,found=.Lioal_sdev_chan_found
            # Not found, so add a new device to the table

            tio    0,3                        # Test the device status
            savecc24 6                        # Place the cc in R6 for return
            bc     0b0001,.Lioal_sdev_chan_return-0b(13) # cc3 -> not oper

            # For all other conditions we will add the device to the table
            l      9,.Lioal_DT_end-0b(13)    # Locate next SCHIB entry
            lr     10,9                      # Copy it
            al     10,.Lioal_DT_size-0b(13)  # Locate the last byte would be +1
            cl     10,.Lioal_DT_max-0b(13)   # Go beyond reserved area?
            bc     0b0100,.Lioal_sdev_chan_new  # ..No, add it to the table
            lh     6,.Lioal_cc3-0b(13)       # ..Yes, then its not operational
            b      .Lioal_sdev_chan_return-0b(13) # Return to caller

.Lioal_sdev_chan_new:
            mvc    0(.LSCHIB_len,9),0(2)     # Add the new SCHIB to the table
            nc     0(.LPMCW_len,9),.Lioal_pmcw_mask-0b(13)  # Clear reserved bits
            st     10,.Lioal_DT_end-0b(13)   # Update the end of the table
            lr     7,9                       # Pretend like it was always there
            # Now determine if the SCSW needs to be updated
            ch     6,.Lioal_cc1-0b(13)       # CSW stored?
            be     .Lioal_sdev_chan_csw-0b(13)  # ..Yes, so update the SCSW
            b      .Lioal_sdev_chan_return-0b(13)  # ..No, just return then

.Lioal_sdev_chan_found:
            # Determine device status
            tio    0,3                        # Test the device status
            savecc24 6                        # Place the cc in R6 for return
            bc     0b1000,.Lioal_sdev_chan_avail    # cc0 --> available
            bc     0b0100,.Lioal_sdev_chan_csw      # cc1 --> CSW stored
            bc     0b0010,.Lioal_sdev_chan_return   # cc2 --> Busy

            # Not Operational
            oi     .LSCHIB_SCSW+.LSCSW_f1(7),.LSCSW_f1_nop
            b      .Lioal_sdev_chan_return-0b(13)  # Return to caller

.Lioal_sdev_chan_csw:
            # Status stored, need to make the current SCHIB status pending
            la     8,.LSCHIB_SCSW(7)         # Point to SCSW
            savecsw scswr=8                  # Save the CSW in the SCHIB's SCSW
            oi     .LSCSW_sc(8),.LSCSW_statpend    # Indicate status pending
            b      .Lioal_sdev_chan_return-0b(13)  # Return to caller

.Lioal_sdev_chan_avail:
            # Update the pseudo HAL SCHIB
            mvc    0(.LSCHIB_len,7),0(2)            # "Modify" the SCHIB
            nc     0(.LPMCW_len,7),.Lioal_pmcw_mask-0b(13) # Clear PMCW

.Lioal_sdev_chan_return:
            lr     2,6
            return

  # +---------------------------------------------+
  # |  System/370 STORE IO INTERRUPT Abstraction  |
  # +---------------------------------------------+
  # Access: public

  # On Entry:
  #    R2     Address of IIB
  #    R3     I/O Interruption class
  #    R4     Interrupting I/O device ID
  #    R5     CSW bits 0-31
  #             bits 0-3   - SCSW storage key
  #             bits 8-31  - SCSW CCW address
  #    R6     CSW bits 32-63
  #             bits 0-7   - SCSW device status
  #             bits 8-15  - Channel status
  #             bits 16-31 - CCW counte
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     ASB pointer
  #    R7     Interrupting device address (CCUU)
  #    R8     Device Table SCHIB pointer
  #    R9     SCSW address
  #
  # On Exit:
  #    R2     Address of returned IIB (same as on call) and IIB contains 
  #           subsystem interrupt information:
  #              IIB+0  == I/O interrution class
  #              IIB+4  == device id
  #              IIB+8  == interruption parameter
  #              IIB+12 == interruption id (interupt subclass)
  #              IIB+16 == device table address
  #           SCHIB updated with CSW information
  #        or zero if SCHIB not found

            func370 .Lioal_stio_chan
            push370

            l      6,.LIEIB_asb(0)        # Locate the active ASB
            lr     7,4                    # Locate the interrupting device address

            srchdt devidr=7 dtr=8 found=.Lioal_stio_found
            # Not found, ignore the interrupt
            sr     2,2                    # Clear returned IIB address
            b      .Lioal_stio_ret-0b(13) # Return to caller

.Lioal_stio_found:
            st     8,.LIIB_pgm(2)         # Save the device table address
            stm    2,3,.LIIB_class(2)     # Save the interruption class and dev id
            mvc    .LIIB_id1(4,2),.LPMCW_intp(8)  # Move the interruption parameter
            sr     0,0                    # Clear R0
            st     0,.LIIB_id2(1,2)       # Clear the interruption id
            mvc    .LIIB_id2(1,2),.LPMCW_isc(8) # Provide the subclass
            la     9,.LSCHIB_SCSW(8)      # Locate the SCSW in the SCHIB
            stcm   5,0b1000,.LSCSW_status(9)   # Set key in SCSW
            ni     .LSCSW_status(9),0xF0       # Clear SCSW bits 4-7
            stm    5,6,.LSCSW_ccw(9)           # Save CSW in SCSW
            mvi    .LSCSW_ccw(9),0x00          # bits 0-7 zero for 24-bit address
            oi     .LSCSW_sc(8),.LSCSW_statpend   # Status is now pending

.Lioal_stio_ret:
            return

  # THIS NEEDS WORK!!!  Change to use IOALLO functions
  # +--------------------------------------------------+
  # |  System/370 Concurrent Sense Emulation Function  |
  # +--------------------------------------------------+
  # Access: private

  # On Entry:
  #    R2     Address of IRB
  #    R3     device ID
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     ASB pointer
  #    R7     Interrupting device address (CCUU)
  #    R8     Device Table SCHIB pointer
  #    R9     SCSW address
  #
  # On Exit:
  #    R2     
  #    IRB updated with concurrent sense data

            func370 .Lioal_csns_chan

  # Local literal pool usage

  # CCW0 used for concurrent sense emulation
.Lioal_csns_abstract_ccw:
            .byte  .LCCW_SENSE
            .byte  0,0,0
            .byte  .LCCW_SLI,0
            .hword 32

  # Local stack frame usage
            fquad   .Lioal_csns_ccw

            push370

            la      8,.LIRB_ECW(2)                   # Locate sense location
            mvi     0(8),0x00                        # Clear sense area 
            mvc     1(31,8),0(8)                     # ..to zeros
            mvc     .LIRB_ESW_erw(4,2),0(8)          # Clear ERW to zeros
            # Move CCW to stack frame for safe usage
            mvc     .Lioal_csns_ccw(8,15),.Lioal_csns_abstract_ccw-0b(13)
            # Place the address in the SENSE CCW
            stcm    8,0b0111,.Lioal_csns_ccw+1(15)
            la      7,.Lioal_csns_ccw(15)            # Locate the command
            stcm    7,0b0111,.LIO_caw+1(0)           # Save it in the CAW
            mvi     .LIO_caw(0),0x00                 # Set storage key to zero

            sio    0,3                        # Start the I/O
            bc     0b0111,.Lioal_csns_ccw_ret-0b(13)   # -> not started

            # Concurrent SENSE in progress
            oi     .LSCHIB_SCSW+.LSCSW_ctl(7),.LSCSW_docs
            l      9,.Lioal_asb-0b(13)        # Locate the active ASB
            lpsw   .LASB_waitcs(9)            # Wait for SENSE to complete

.Lioal_csns_ccw_ret:            
            return

.endif # .if .Lhal_s370 scope

.if .Lhal_s390
           .sbttl "I/O Hardware Abstraction Layer - s390"
           .eject
  # +------------------------------+
  # |  ESA/390 IO DATA abstraction |
  # +------------------------------+ 

  # On entry:
  #    R2     ORB address (the ORB CCW address identified the CCW being modified)
  #    R3     Program data address
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Address of the CCW beign modified (CCW0 subroutine)
  #
  # On exit:
  #    CCW1 contains valid program data addressing

            func370 .Lioal_data_s390
            push370

            oi     .LORB_f2(2),.LORB_f2_F          # Set CCW1 use in ORB
            l      7,.LORB_pgm(2)                  # Fetch the ORB's CCW1 address
            st     3,.LCCW1_addr(7)                # Set data address in CCW1
            ni     .LCCW1_addr(7),0x7F             # Make sure high-order bit is 0
            ni     .LCCW1_flags(7),0xFF-.LCCW_IDA  # Indicate no IDAW in CCW1
            return

.if .Lhal_s390x

  # +----------------------------------+
  # |  ESA/390 IO DATA IDA abstraction |
  # +----------------------------------+ 

  # On entry:
  #    R2     IDAW2 address
  #    R3     ORB address  (the ORB CCW address identified the CCW being modified)
  #    R4     Program data address (bits 0-31)
  #    R5     Program data address (bits 32-64)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Data address for CCW0 subroutine
  #
  # On exit:
  #    R2     next IDAW2 address
  #    CCW1 contains valid program data addressing information 

            func370 .Lioal_datp_s390

  # Local literal pool
.Lioal_datp_s390_pagmsk:
            .long  0xFFFFF000
.Lioal_datp_s390_one:
            .long  1
.Lioal_datp_s390_pagsiz:
            .hword 4096

            push370

            ltr     4,4                      # Any high-order address bits set?
            bnz     .Lioal_datp_s390_ida     # ..Yes, must use IDAW2's
            ltr     5,5                      # Is bit 32 of 64-bit address set?
            bm      .Lioal_datp_s390_ida     # ..Yes, need IDAW2's too

            # CCW1 without IDAW's may be used, so use the CCW1 shared routine
            # Bits 0-32 of the 64-bit address are ignored
            lr      6,3                      # Pass the ORB to the CCW0 routine
            lr      7,5                      # Pass address to the CCW0 routine
            bas     11,.Lioal_ccw1-0b(13)    # Use the common CCW0 setup routine
            b       .Lioal_datp_s390_ret-0b(13)  # Return to caller

  # Register usage of the IDAW2 build process:
  #    R0      Number of bytes remaining to be covered by IDAW's
  #    R6      Byte position relative to a 4K page for the program data start
  #    R7      Number of count bytes to which this IDAW2 provides locations
  #    R8      CCW1 address (from ORB)

.Lioal_datp_s390_ida:
            l      8,.LORB_pgm(3)                # Fetch the CCW1 address from ORB
            sr     0,0                           # Clear R0
            icm    0,0b0011,.LCCW1_cnt(8)        # Get the program data byte count

            # Point the CCW1 to the IDAW2 list
            st     2,.LCCW1_addr(8)              # Set the address in the IDAW
            ni     .LCCW1_addr(8),0x7F           # Make sure bit 0 is zero
            oi     .LCCW1_flags(8),.LCCW_IDA     # Use the IDAW list

            # Determine number of bytes in current program data page
            lr     6,5                           # Calculate the starting page pos.
            n      6,.Lioal_datp_s390_pagmsk-0b(13)  # relative to page start
            lh     7,.Lioal_datp_s390_pagsiz-0b(13)  # Size of a page
            sr     7,6                           # Bytes in this page.

.Lioal_datp_s390_build:
            stm    4,5,0(2)                      # Create the first IDAW
            la     2,8(2)                        # Update the IDAW2 pointer

            # Can all of the bytes fit in this page
            sr     0,7                           # count -= covered by IDAW
            bnp    .Lioal_datp_s390_idaw2_done-0b(13)  # done if count <= 0?

            # More IDAW's needed - Increment program data by bytes covered
            alr    5,7
            bc     0b1100,.Lioal_datp_s390_nocarry-0b(13)
            al     4,.Lioal_datp_s390_one-0b(13)
.Lioal_datp_s390_nocarry:

            # Starting now on a page boundary
            lh     7,.Lioal_datp_s390_pagsiz-0b(13) # Have 4096 bytes available
            b      .Lioal_datp_s390_build-0b(13)    # Make next IDAW2

.Lioal_datp_s390_idaw2_done:
            ni     .LORB_f2(3),0xFF-.LORB_f2_T      # Using 4096-byte IDAW's
            oi     .LORB_f2(3),.LORB_f2_H           # Using Format-2 IDAW's

.Lioal_datp_s390_ret:
            return

.endif # .if ioal_s390x scope

  # +------------------------------+
  # |  ESA/390 INIT IO abstraction |
  # +------------------------------+

  # On entry:
  #    R2     Active ASB pointer
  #    R3     Starting address reserved for the Device Table (ignored) 
  #    R4     Last address reserved for the Device Table (ignored)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Pointer to the ASB
  #    R7     Used to test if interrupt abstractions are initialized
  #
  # On exit: none

            function .Lioal_init_s390
            push

            icm     7,0b1111,.Lihstk(0)    # Interrupt abstractions enabled?
            bnz     .+8-0b(13)             # ..yes, continue with INIT IO
            halabort error=0x000C          # ..no, need interrupt abstractions
            l       2,.LIEIB_asb(0)        # Locate the active ASB
            mvc     .LPSW_newio(8,0),.LASB_ionpsw(2)  # Set I/O new 64-bit PSW
            lctl    2,2,.LASB_cr2(2)       # Initialize CR2
            lctl    6,6,.LASB_cr6(2)       # Initialize CR6
            oc      .LASB_amode(2,2),.LASB_amode(2)  # Need to set address mode?
            bz      .Lioal_init_s390_return-0b(13)   # ..No, just return then
            ex      0,.LASB_amode(2)       # ..Yes, then set it

.Lioal_init_s390_return:
            return

  # +----------------------------------+
  # |  ESA/390 INITIATE IO abstraction |
  # +----------------------------------+

  # On entry:
  #    R2     ORB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by STORE SUBCHANNEL instruction    
  #
  # On exit:
  #    R2     Condition code returned by the START SUBCHANNEL instruction
  #              0 -->  I/O started
  #              1 -->  Status pending, I/O not started
  #              2 -->  Busy, I/O not started
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            function .Lioal_doio_s390
            push

            lr     1,3                     # Place SSID for START SUBCHANNEL
            ssch   0(2)                    # Now, issue START SUBCHANNEL
            savecc 2                       # Place the cc in R2 for return
            return

  # +------------------------------------+
  # |  ESA/390 QUERY DEVICE abstraction  |
  # +------------------------------------+

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by STORE SUBCHANNEL instruction  
  #    R6     Condition code from TEST I/O instruction
  #
  # On exit:
  #    R2     Condition code as it would be for a real STORE SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            function .Lioal_qdev_s390
            push

            lr     1,3                     # Place SSID for STORE SUBCHANNEL
            stsch  0(2)                    # Now, issue STORE SUBCHANNEL
            savecc 2                       # Place the cc in R2 for return
            return

  # +---------------------------------------+
  # |  ESA/390 QUERY INTERRUPT abstraction  |
  # +---------------------------------------+ 

  # On entry:
  #    R2     IRB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R1     SSID required by TEST SUBCHANNEL instruction  
  #
  # On exit:
  #    R2     Condition code from TEST SUBCHANNEL instruction
  #              0 -->  Status was pending, IRB updated
  #              1 -->  Status was not pending, IRB updated
  #              3 -->  Device is not operational

            function .Lioal_qint_s390
            push

            lr     1,3                     # Place SSID for TEST SUBCHANNEL
            tsch   0(2)                    # Now, issue TEST SUBCHANNEL
            savecc 2                       # Place cc in R2 for return
            return

  # +----------------------------------+
  # |  ESA/390 SET DEVICE abstraction  |
  # +----------------------------------+ 

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by MODIFY SUBCHANNEL instruction  
  #
  # On exit:
  #    R2     Condition code returned by MODIFY SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              1 -->  Status pending, SCHIB not modified
  #              2 -->  Busy, SCHIB not modified
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            function .Lioal_sdev_s390
            push

            lr     1,3                     # Place SSID for MODIFY SUBCHANNEL
            msch   0(2)                    # Now, issue MODIFY SUBCHANNEL
            savecc 2                       # Place cc in R2 for return
            return

  # +-----------------------------------------+
  # |  ESA/390 SET INTERRUPT PSW abstraction  |
  # +-----------------------------------------+ 

  # On entry:
  #    R2     Bits 33-63 of 64-bit interrupt PSW
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: 
  #    R6    Active ASB
  #
  # On exit: None

            function .Lioal_spsw_s390
            push

            l      6,.LIEIB_asb(0)        # Locate the ASB     
            st     2,.LASB_ionpsw(6)      # Make the supplied PSW the I/O new PSW
            oi     .LASB_ionpsw+4(6),0x80 # Expect to operate in amode=31
            mvc    .LPSW_newio(8,0),.LASB_ionpsw(6)  # Make it the active new PSW
            return

  # +------------------------------------------+
  # |  ESA/390 STORE IO INTERRUPT Abstraction  |
  # +------------------------------------------+

  # On Entry:
  #    R2     Address of IIB
  #    R3     I/O Interruption class
  #    R4     Interrupting I/O device ID (SSID)
  #    R5     Interruption parameter
  #    R6     Interruption identifier
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     ASB pointer
  #    R7     Interrupting device address (CCUU)
  #    R8     Device Table SCHIB pointer
  #    R9     SCSW address
  #
  # On Exit:
  #    R2     Address of returned IIB (same as on call) and IIB contains 
  #           subsystem interrupt information:
  #              IIB+0  == I/O interrution class
  #              IIB+4  == device id
  #              IIB+8  == interruption parameter
  #              IIB+12 == interruption identifier (interupt subclass)
  #              IIB+16 == not used

            func370 .Lioal_stio_s390
            push370

            stm    3,6,.LIIB(2)
            return

.endif # .if .Lioal_s390

.if .Lhal_s390x
           .sbttl "I/O Hardware Abstraction Layer - s390x"
           .eject

  # +------------------------------------+
  # |  z/Architectue IO DATA abstraction |
  # +------------------------------------+ 

  # On entry:
  #    R2     ORB address (the ORB CCW address identified the CCW being modified)
  #    R3     Program data address
  #    R4     IDAW2 address (or zero if not available)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Address of the CCW being modified
  #
  # On exit:
  #    R2     next IDAW2 address (equals the R4 entry value if not used)
  #    CCW1 contains valid program data addressing information

            functionx .Lioal_data_s390x

  # Local literals
.Lioal_data_s390x_max:
            .quad   0x000000007FFFFFFF
.Lioal_data_s390x_pagmsk:
            .quad   0xFFFFFFFFFFFFF000
.Lioal_data_s390x_zeros:
            .quad   0

  # Local stack frame usage:
  #          fquad  .Lioal_data_s390x_addr

            pushx

            clg    3,.Lioal_data_s390x_max-0b(13)  # IDAW's required?
            bnh    .Lioal_data_s390x_ccw1-0b(13)   # ..No, just use CCW1
            ltgr   4,4                             # IDAW2 area available?
            bnz    .Lioal_data_s390x_idaw2-0b(13)  # ..Yes, so use them
            halabort error=0x0006   # IDAW2's required, but not provided

.Lioal_data_s390x_ccw1:
            oi     .LORB_f2(2),.LORB_f2_F          # Set CCW1 use in ORB
            llgt   7,.LORB_pgm(2)                  # Fetch the CCW1 address from ORB
            st     3,.LCCW1_addr(7)                # Set data address in CCW1
            ni     .LCCW1_addr(7),0x7F             # Make sure high-order bit is 0
            ni     .LCCW1_flags(7),0xFF-.LCCW_IDA  # Indicate no IDAW in CCW1
            b      .Lioal_data_s390x_ret-0b(13)    # Return to caller

.Lioal_data_s390x_idaw2:
            clg    4,.Lioal_data_s390x_max-0b(13)  # IDAW2 area valid for CCW1?
            bl     .Lioal_data_s390x_build-0b(13)  # ..Yes, build IDAW2 list
            halabort error=0x0007                  # ..No, die with program int.

.Lioal_data_s390x_build:
            llgt    7,.LORB_pgm(2)               # Fetch the CCW1 address from ORB
            llgh    0,.LCCW1_cnt(7)              # Get the program data byte count

            # Point the CCW1 to the IDAW2 list
            st      4,.LCCW1_addr(7)             # Set the address in the IDAW
            oi     .LCCW1_flags(7),.LCCW_IDA     # Use the IDAW list

            # Determine number of bytes in current program data page
            lgr     6,5                          # Calculate the starting position
            ng      6,.Lioal_data_s390x_pagmsk-0b(13) # ..in the page
            llill   7,4096                       # Size of a page
            sgr     7,6                          # Bytes covered by first IDAW2

.Lioal_data_s390x_next:
            stg    3,0(4)                        # Create the first IDAW
            la     4,8(4)                        # Update the IDAW2 pointer

            # Can all of the bytes fit in this page
            sgr    0,7                           # count -= covered by IDAW
            bc     0b1100,.Lioal_data_s390x_done-0b(10) # done if count <= 0?

            # More IDAW's needed - Increment program data by bytes covered
            algr   5,7

            # Starting now on a page boundary
            llill   7,4096                        # Have 4096 bytes available
            b      .Lioal_data_s390x_next-0b(10)  # Make next IDAW2

.Lioal_data_s390x_done:
            ni     .LORB_f2(2),0xFF-.LORB_f2_T    # Using 4096-byte IDAW's
            oi     .LORB_f2(2),.LORB_f2_H         # Using Format-2 IDAW's

.Lioal_data_s390x_ret:
            lgr    2,4                            # Return next IDAW2 address
            returnx

  # +-----------------------------------------+
  # |  z/Architecture EXECUTE IO abstraction  |
  # +-----------------------------------------+

  # On entry:
  #    R2     SSID of device for which I/O operations is to be performed
  #    R3     Address of the ORB for the I/O operation
  #    R4     Address of the IRB for the I/O operation conclusion information
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID of device for which I/O operations is to be performed
  #    R2     START SUBCHANNEL condition code
  #    R6     Architecture Support Block
  #    R10    Local base register from 1b    
  #
  # On exit:
  #    R2     Condition code from START SUBCHANNEL instruction
  #              0 -->  IRB contains the results of this operation's interrupt
  #              1 -->  IRB contains results of some previous I/O interrupt
  #              2 -->  Device is busy, operation did not start
  #              3 -->  Device is not operational
  #    IRB saved to determine I/O conclusion status

            functionx .Lioal_io_s390x
            pushx

            lgr     10,1                    # Move local base register
            lg      6,.LIEIB_asbg(0)        # Locate current ASB
            lgr     1,2                     # Set up R1 for I/O instruction
            ssch    0(3)                    # Try to start I/O
            saveccg 2                       # Save the cc for return
            bc      0b0011,.Lioal_io_s390x_return-0b(13)  # -> busy or not oper
            bc      0b0100,.Lioal_io_s390x_pending_status-0b(13) # -> status pending
            # Start function started

.Lioal_io_s390x_started:
            lpsw    .LASB_waitpsw(6)        # Wait for I/O to complete

.Lioal_io_s390x_done:
            clm     1,0b1111,.LIO_ssid(0)   # Is the interrupt for our device?
            bne     .Lioal_io_s390x_started-0b(13)  # ..No, continue waiting

.Lioal_io_s390x_pending_status:            
            tsch     0(4)                    # ..Yes, save the IRB for caller
            # Caller is expected to inspect IRB for I/O results
            # and the interruption parameter or interruption id as required

.Lioal_io_s390x_return:
            returnx

  # +--------------------------------------+
  # |  z/Architecture INIT IO abstraction  |
  # +--------------------------------------+
  # Access: public

  # On entry:
  #    R2     Active ASB pointer
  #    R3     Starting address reserved for the Device Table (ignored) 
  #    R4     Last address reserved for the Device Table (ignored)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R2     Active ASB pointer
  #    R3     Device control table address or (0)
  #    R6     Pointer to the ASB
  #    R7     Test if interrupt abstractions initialized
  #
  # On exit: none

            functionx .Lioal_init_s390x
            pushx

            lg      7,.Lihstk(0)           # Fetch the starting stack address
            ltgr    7,7                    # Is it initialized?
            jnz     .+8                    # ..yes, may INIT I/O abstractions
            halabort error=0x000C          # ..no, abort, I need IH abstractions
            lg      2,.LIEIB_asbg(0)       # LocATE the active ASB
            mvc     .LPSW_newiog(16,0),.LASB_ionpsw(2)  # Set I/O new 128-bit PSW
            lctl    2,2,.LASBG_cr2(2)      # Initialize CR2
            lctl    6,6,.LASBG_cr6(2)      # Initialize CR6
            ex      0,.LASBG_amode(2)      # ..Yes, then set it
            returnx

  # +-----------------------------------------+
  # |  z/Architecture INITIATE IO abstraction |
  # +-----------------------------------------+
  # Access: public

  # On entry:
  #    R2     ORB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by STORE SUBCHANNEL instruction    
  #
  # On exit:
  #    R2     Condition code from START SUBCHANNEL instruction
  #              0 -->  I/O started
  #              1 -->  Status pending, I/O not started
  #              2 -->  Busy, I/O not started
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            functionx .Lioal_doio_s390x
            pushx

            lr     1,3                     # Place SSID for START SUBCHANNEL
            ssch   0(2)                    # Now, issue START SUBCHANNEL
            savecc 2                       # Place the cc in R2 for return
            returnx

  # +-------------------------------------------+
  # |  z/Architecture QUERY DEVICE abstraction  |
  # +-------------------------------------------+
  # Access: public

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by STORE SUBCHANNEL instruction  
  #    R6     Condition code from TEST I/O instruction
  #
  # On exit:
  #    R2     Condition code from STORE SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            functionx .Lioal_qdev_s390x
            pushx

            lgr     1,3                    # Place SSID for STORE SUBCHANNEL
            stsch   0(2)                   # Now, issue STORE SUBCHANNEL
            saveccg 2                      # Place the cc in R2 for return
            returnx

  # +----------------------------------------------+
  # |  z/Architecture QUERY INTERRUPT abstraction  |
  # +----------------------------------------------+
  # Access: public

  # On entry:
  #    R2     IRB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:  
  #    R1     SSID required by TEST SUBCHANNEL instruction  
  #
  # On exit:
  #    R2     Condition code from TEST SUBCHANNEL instruction
  #              0 -->  Status was pending, IRB updated
  #              1 -->  Status was not pending, IRB updated
  #              3 -->  Device is not operational

            functionx .Lioal_qint_s390x
            pushx

            lgr     1,3                    # Place SSID for TEST SUBCHANNEL
            tsch    0(2)                   # Now, issue TEST SUBCHANNEL
            saveccg 2                      # Place cc in R2 for return
            returnx

  # +-----------------------------------------+
  # |  z/Architecture SET DEVICE abstraction  |
  # +-----------------------------------------+
  # Access: public

  # On entry:
  #    R2     SCHIB address
  #    R3     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID required by MODIFY SUBCHANNEL instruction  
  #
  # On exit:
  #    R2     Condition code from MODIFY SUBCHANNEL instruction
  #              0 -->  SCHIB stored
  #              1 -->  Status pending, SCHIB not modified
  #              2 -->  Busy, SCHIB not modified
  #              3 -->  Device is not operational
  #    SCHIB saved to determine I/O conclusion status

            functionx .Lioal_sdev_s390x
            pushx

            lgr     1,3                    # Place SSID for MODIFY SUBCHANNEL
            msch    0(2)                   # Now, issue MODIFY SUBCHANNEL
            saveccg 2                      # Place the cc in R2 for the return
            returnx

  # +------------------------------------------------+
  # |  z/Architecture SET INTERRUPT PSW abstraction  |
  # +------------------------------------------------+
  # Access: public

  # On entry:
  #    R2     Bits 64-127 of 128-bit interrupt PSW
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R6     Active ASB
  #
  # On exit: None

  #          functionx .Lioal_spsw_s390x
  #          pushx

  #          lg     6,.Lioal_asbg-0b(13)  # Locate the active ASB
  #          stg    2,.LASB_ionpsw+8(6)   # Set the new handler address
  #          mvc    .LPSW_newiog(16,0),.LASB_ionpsw(6) # Make it the active new PSW
  #          returnx

  # +-------------------------------------------------+
  # |  z/Architecture STORE IO INTERRUPT Abstraction  |
  # +-------------------------------------------------+

  # On Entry:
  #    R2     Address of IIB
  #    R3     I/O Interruption class
  #    R4     Interrupting I/O device ID (SSID)
  #    R5     Interruption parameter
  #    R6     Interruption identifier
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     ASB pointer
  #    R7     Interrupting device address (CCUU)
  #    R8     Device Table SCHIB pointer
  #    R9     SCSW address
  #
  # On Exit:
  #    R2     Address of returned IIB (same as on call) and IIB contains 
  #           subsystem interrupt information:
  #              IIB+0  == I/O interrution class
  #              IIB+8  == device id
  #              IIB+16 == interruption parameter
  #              IIB+24 == interruption identifier (interupt subclass)
  #              IIB+32 == not used

            functionx .Lioal_stio_s390x
            pushx

            stmg   3,6,.LIIBG(2)
            returnx

.endif # .if .Lioal_s390x

.if .Lhal_32bit

  # +-------------------------------------------------------+
  # |  32-bit Abstract CCW Absolute Conversion Abstraction  |
  # +-------------------------------------------------------+
  # Access: public

  # On entry:
  #    R2     ORB address
  #    R3     Abstract Channel-program length
  #    R4     Address of the program data area address list (see Used)
  #    R5     IDA area starting address (see Used)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     Current CCW1 being converted (BRANCH ON INDEX sum value)
  #    R4     Pointer to the next program data area address to be used
  #    R5     Pointer to the next available IDA area location
  #    R6     Address of the active ASB
  #    R7     CCW address (either from the CCW1 or program list)
  #    R8     CCW size for process loop (BRANCH ON INDEX increment value)
  #    R9     Last CCW in abstract chain (BRANCH ON INDEX compare value)
  #    R10    Starting address of the chain
  #    R11,12 IDAW address from the program
  #
  # On exit:
  #    Abstract channel program converted to a real channel program
  #
  # The ASB field .LASB_idac controls the actions taken by this function:
  #
  #  0x80   Convert abstract CCW1's into real CCW0's

            func370 .Lioal_ccw32

 # Local literal values
.Lioal_ccw32_31max:
            .long  0
.Lioal_ccw32_adrmsk:
            .long  0x7FFFFFFF
.Lioal_ccw32_eight:
            .hword 8

.if .Lhal_s390x
 # Local stack frame usage
            fbytes  .Lioal_ccw32_sa,16  # R1-R4 save area
.endif # .if .Lioal_s390x scope

            push370

            l      6,.LIEIB_asb(0)         # Locate the active ASB
            ni     .LORB_pgm(2),0x7F       # Make sure high-order bit is zero
            l      1,.LORB_pgm(2)          # Set up start of CCW chain
            lh     8,.Lioal_ccw32_eight-0b(13)  # Set loop increment to 8
            lr     9,1                     # Locate the last CCW by
            ar     9,3                     # ..adding the channel program length
            sr     9,8                     # ..and then subtracting 8 (ccw length)
            lr     10,1                    # Save start for chain relative addr.

.Lioal_ccw32_current:  # Process the abstract CCW pointed to by R1
            cli    .LCCW1_cmd(1),.LCCW_TIC     # TRANSFER-IN-CHANNEL?
            bne    .Lioal_ccw32_nottic-0b(13)  # ..No, handle normal CCW's

            # Process the TIC for chain relative addressing
            icm    7,0b1111,.LCCW1_addr(1)          # Chain relative address?
            bc     0b1010,.Lioal_ccw32_next-0b(13)  # ..No, leave TIC alone
            n      7,.Lioal_ccw32_adrmsk-0b(13)     # ..yes, turn off flag
            ar     7,10                             # Calc. real address
            st     7,.LCCW1_addr(1)                 # Update the CCW address
            b      .Lioal_ccw32_next-0b(13)         # Process next CCW

.Lioal_ccw32_nottic:
            # Process standard CCW's
            tm     .LCCW1_flags(1),.LCCW_IDA|.LCCW_MIDA  # IDA in use?
            bz     .Lioal_ccw32_addr_zero-0b(13)    # Could have zero address
            bm     .Lioal_ccw32_next-0b(13)         # if either, leave alone
            halabort error=0x000A  # ERROR - both flags set

.Lioal_ccw32_addr_zero:
            # Determine if a program address is being supplied in a list
            icm    7,0b1111,.LCCW1_addr(1)          # Address == zero?
            bnz    .Lioal_ccw32_next-0b(13)         # ..No, leave it alone

.if .Lhal_s390x
            # Need to use program supplied address
            tm     .LORB_f2(2),.LORB_f2_H           # Using IDAW-2's?
            bno    .Lioal_ccw32_addr31-0b(13)       # ..No, this is a 31-bit addr

            # Handle 64-bit addresses

            stm    1,4,.Lioal_ccw32_sa(15)          # Save volatile regs

            sr     3,1                              # Pass abstract CCW to function
            callptr .Lioal_idaw2                    # Call IDAW2 function
            # Returns updated IDA pointer in R2
            l      5,2                              # Set current IDA pointer

            lm     1,4,.Lioal_ccw32_sa(15)          # R2-R4 Restoered
            la     4,8(4)                           # Point to next program addr.
            b      .Lioal_ccw32_next-0b(13)         # Process next abstract CCW 

.Lioal_ccw32_addr31:
.endif # .if .Lioal_s390x

            mvc    .LCCW1_addr(4,1),0(4)            # Set new address from list
            ni     .LCCW1_addr(1),0x7F              # Make sure bit 32 is zero
            la     4,4(4)                           # Point to next list address

            # Determine if abstract CCW1 needs to be converted to CCW0
            tm     .LASB_idac(6),0x80               # CCW0 needed?
            bno    .Lioal_ccw32_next-0b(13)         # ..No, we are done

            # Convert CCW1 into CCW0
            cli    .LCCW1_addr(1),0x00              # Valid 24-bit address
            be     .Lioal_ccw32_addr24-0b(13)       # ..Yes convert the CCW1 to 0
            halabort error=0x000B   # ERROR - 31-bit address will not fit!

.Lioal_ccw32_addr24:
            l      0,0(1)                           # Save flags and count
            mvc    .LCCW0_addr(3,1),.LCCW1_addr(1)  # Relocate the 24-bit address
            stcm   0,0b0100,.LCCW0_flags(1)         # Relocate flags
            sth    0,.LCCW0_cnt(1)                  # Relocate count
            mvi    .LCCW0_flags+1(1),0x00           # Clear unused area

.Lioal_ccw32_next:
            bxle   1,8,.Lioal_ccw32_current-0b(13)  # Process next abstract CCW
            # Whole abstract CCW chain has been converted to real CCW's

            return                                  # Return to caller

  # +---------------------------------+
  # |  32-bit Execute IO Abstraction  |
  # +---------------------------------+

  # On entry:
  #    R2     Device ID (CCUU in bits 16-31 or SSID)
  #    R3     Address of ORB for the I/O operation
  #    R4     Address of IRB for the I/O operation conclusion information
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     HAL function address
  #    R6     Address of the active ASB
  #    R7     not used
  #    R8     Address of the IRB for the I/O operation
  #    R9     Device ID
  #    R10    Pending status retry flag
  #
  # On exit:
  #    R2     Contains condition code of START I/O instruction or SENSE available
  #              0 -->  IRB contains the results of this operation
  #              1 -->  IRB unpredictable and I/O may not have started
  #              2 -->  Device busy
  #              3 -->  Device not operational
  #    IRB contains I/O conclusion status if R2 == 0

            func370 .Lioal_exio32  # May be called in either S/370 or ESA/390

 # Local literal pool
.Lioal_exio32_1: .hword 1

            push370

            l       6,.LIEIB_asb(0)           # Locate the active ASB
            lr      8,4                       # Preserve the IRB address
            lr      9,2                       # Preserve the device ID
            sr      10,10                     # Initial attempt to do I/O

.Lioal_exio32_try:
            l       1,.LASB_doio(6)           # Locate INITIATE IO abstraction
            callr   1                         # Start the I/O
            ltr     2,2                       # Did the I/O start OK?
            bz      .Lioal_exio32_wait-0b(13) # ..Yes, wait for result
            ch      2,.Lioal_exio32_1-0b(13)  # Status pending?
            bne     .Lioal_exio32_ret-0b(13)  # ..No, (busy or not oper), return

            # Clear pending status that inhibited the I/O from starting
            ltr     10,10                     # Test if status did not clear
            bnz     .Lioal_exio32_ret-0b(13)  # Give up with return code == 1
            lr      2,9                       # Set the device ID
            lr      3,4                       # Set the IRB address
            l       1,.LASB_qint(6)           # Locate QUERY INTERRUPT abstraction
            callr   1                         # Call it
            la      10,1                      # Indicate we did this once
            b       .Lioal_exio32_try-0b(13)  # Try again

.Lioal_exio32_wait:
            # Set handler --- could move to initialization routines
            la      2,.Lioal_exio32_done-0b(13) # Locate my handler
            l       1,.LASB_spsw(6)           # Locate SET INTERRUPT PSW
            callrx  1                         # Set me up for my handler

            # Wait for result
            lpsw    .LASB_waitpsw(6)          # Wait for it to finish

.Lioal_exio32_done:
            cl      9,.LIO_ssid(0)            # Is interrupt from my device?
            bne     .Lioal_exio32_wait-0b(13) # ..No, wait some more
            lr      2,9                       # Set the device ID
            lr      3,4                       # Set the IRB address
            l       1,.LASB_qint(6)           # Locate QUERY INTERRUPT abstraction
            callr   1                         # Get I/O results in IRB

.Lioal_exio32_ret:
            return

.if .Lhal_s390x
  # +--------------------------+
  # |  32-bit IDAW2 Generator  |
  # +--------------------------+

  # This function generates a 64-bit IDAW2 if the current program area list
  # 64-bit address requires it.  Otherwise it will update the abstract CCW.
  #
  # This function is only required if s390x is being supported by the IOAL but
  # the input/output operation for which CCW's are being created is running
  # in s390 mode.  Only absolute data area addresses are supported here.
  # 64-bit virtual addresses requires s390x operations with dynamic address
  # translation enabled in the PSW.  See the s390x IDA routine for virtual
  # addressing support.
  #
  # On entry:
  #    R2     ORB address
  #    R3     Address of abstract CCW for which IDAW2 may be required
  #    R4     Address of the program data area address list
  #    R5     IDA area starting address (see Used)
  #
  # Used:
  #    R1     IDAW controls pointer
  #    R5     Pointer to location where the next IDAW will be placed
  #    R7     Bytes remaining to be covered
  #    R8,R9  64-bit program data address
  #    R10    Subroutine pointer
  #    R11    Subroutine return
  #    R12    Number of bytes covered by current IDAW
  #
  # On return:
  #    R2     Next available IDA area address

            func370 .Lioal_idaw2

 # Local literal pool
.Lioal_idaw2_4K:
            .long  4096        # 4K IDAW coverage
            .long  0xFFFFF000  # 4K IDAW forward mask
            .long  0x00000FFF  # 4K IDAW backward mask
.Lioal_idaw2_2K:
            .long  2048        # 2K IDAW coverage
            .long  0xFFFFF800  # 2K IDAW forward mask
            .long  0x000007FF  # 2K IDAW backward mask
.Lioal_idaw2_fwd_rtns:
            .long  .Lioal_idaw2_fwd_first
            .long  .Lioal_idaw2_fwd_incr
.Lioal_idaw2_bwd_rtns:
            .long  .Lioal_idaw2_bwd_first
            .long  .Lioal_idaw2_bwd_decr
.Lioal_idaw2_one:
            .long  1

 # Local stack frame usage:
            flong  .Lioal_idaw2_first
            flong  .Lioal_idaw2_adjust
            fbyte  .Lioal_idaw2_dev_order

            push370

            lm     8,9,0(4)          # Fetch the 64-bit program data address
            ltr    8,8               # Are the high-order bits (0-31) zero?
            bnz    .Lioal_idaw2_64   # ..No, IDAW2 IS required
            ltr    9,9               # Is bit 32 zero?
            bm     .Lioal_idaw2_64   # ..No, so also need IDAW2
            # Bits 0-32 of the program data address are all zero, do not need IDAW2

            st     9,.LCCW1_addr(3)  # Set 31-bit address in the CCW
            ni     .LCCW1_addr(3),0x7F  # Make sure CCW bit 32 is zero
            b      .Lioal_idaw2_ret  # Return to caller

.Lioal_idaw2_64:  
   # Need to create a 64-bit IDAW2 and update abstract CCW
            st     5,.LCCW1_addr(3)           # Point the CCW to the first IDAW2 
            ni     .LCCW1_addr(3),0x7F        # Make sure bit 32 of the CCW is zero
            oi     .LCCW1_flags(3),.LCCW_IDA  # Turn on the IDA bit

   # Fetch total data length of I/O operation
            sr     7,7                            # Clear R7
            icm    7,0b0011,.LCCW1_len(3)         # Get total data length

   # Determine IDAW controls
            la     1,.Lioal_idaw2_4K-0b(13)       # Point to 4K controls
            tm     .LORB_f2(2),.LORB_f2_T         # Using 2K IDAW's?
            bz     .+8-0b(13)                     # ..No, 4K is good
            la     1,.Lioal_idaw2_4K-0b(13)       # Point to 2K controls

   # Building for read backward operation?
            mvi    .Lioal_idaw2_dev_order(15),0x0F    # Move device order mask
            # Isolate the read backward device order bits
            nc     .Lioal_idaw2_dev_order(1,15),.LCCW1_cmd(3)
            cli    .Lioal_idaw2_dev_order(15),0x0C   # Read backward?
            bne    .Lioal_idaw2_fwd-0b(13)      # ..no, build forward IDAW's
            mvc    .Lioal_idaw2_first(8,15),.Lioal_idaw2_bwd_rtns-0b(13)
            b      .Lioal_idaw2_start-0b(13)    # Build the backward IDAW's
.Lioal_idaw2_fwd:
            mvc    .Lioal_idaw2_first(8,15),.Lioal_idaw2_fwd_rtns-0b(13)

.Lioal_idaw2_start:
            l      10,.Lioal_idaw2_first(15)    # Locate first IDAW rtn
            basr   11,10        # Determine area covered by first IDAW
            # R12 now contains bytes covered by first IDAW

.Lioal_idaw2_build:
            stm    8,9,0(5)                     # Create the IDAW2
            la     5,8(5)                       # Update the IDAW2 pointer

            # Do all of the remaining bytes fit in this IDAW?
            sr     7,12                         # count -= covered by IDAW
            bnp    .Lioal_idaw2_ret-0b(13)      # done if count <= 0?

            # More IDAW's are needed
            # Adjust 64-bit program data by bytes covered in this IDAW
            l      10,.Lioal_idaw2_adjust(15)   # Locate 64-bit adjustment rtn
            balr   11,10                        # addr +/- R12

            # Starting now on a IDAW boundary and IDAW covers a complete area
            l      12,0(1)                      # Next IDAW is a full IDAW
            b      .Lioal_idaw2_build-0b(13)    # Make next IDAW2

.Lioal_idaw2_ret:
            lr     2,5               # Return current IDA pointer to caller
            return                   # and return

.Lioal_idaw2_bwd_decr:
    # Decrement 64-bit program data by bytes covered in this IDAW
            slr    9,12                       # addr.32-64 - coverage size
            bc     0b0011,.+8-0b(13)          # addr.0-31 correct if no borrow
            sl     8,.Lioal_idaw2_one-0b(13)  # addr.0-31 - 1
            br     11

.Lioal_idaw2_bwd_first:
    # Determine number of bytes covered by first backward IDAW
            lr     12,9              # Get low-order address bits
            n      12,8(1)           # Calculate bytes covered minus 1
            al     12,.Lioal_idaw2_one-0b(13)  # R12 = bytes covered by first IDAW
            br     11                # Return to main loop

.Lioal_idaw2_fwd_first:
    # Determine number of bytes covered by first forward IDAW
            lr     0,9                 # Get low-order address bits
            n      0,4(1)              # IDAW area relative position of first byte
            l      12,0(1)             # R12 = number of bytes per IDAW
            sr     12,0                # R12 = number of bytes of first IDAW
            br     11                  # Return to main loop

.Lioal_idaw2_fwd_incr:
    # Increment 64-bit program data by bytes covered in this IDAW
            alr    9,12                         # addr.32-64 + coverage size
            bc     0b1100,.+8-0b(13)            # addr.0-31 correct if no carry
            al     8,.Lioal_idaw2_one-0b(13)    # addr.0-31 + 1 for carry
            br     11                           # Return to main loop

.endif # .if .Lhal_s390x

.endif # .if .Lhal_32bit scope

.if .Lhal_64bit

  # +---------------------------------+
  # |  64-bit Execute IO Abstraction  |
  # +---------------------------------+

  # On entry:
  #    R2     Device ID (SSID)
  #    R3     Address of ORB for the I/O operation
  #    R4     Address of IRB for the I/O operation conclusion information
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     HAL function address
  #    R6     Address of the active ASB
  #    R7     Address of the ORB for the I/O operation
  #    R8     Address of the IRB for the I/O operation
  #    R9     Device ID
  #    R10    IIB Address
  #
  # On exit:
  #    R2     Contains condition code of START I/O instruction or SENSE available
  #              0 -->  IRB contains the results of this operation
  #              1 -->  IRB unpredictable
  #              2 -->  Device busy
  #              3 -->  Device not operational
  #    IRB contains I/O conclusion status if R2 == 0

            functionx .Lioal_exio64

 # Local literal pool
.Lioal_exio64_1: .long 1

 # Local stack frame usage
            fbytes .Lioal_exio_iib,.LIIBG_len  # Interrupt Information Block
            flong  .Lioal_exio_waits           # Number of devices to wait
            flong  .Lioal_exio_waitd           # Device waiting to complete

            pushx

            lg      6,.LIEIB_asbg(0)          # Locate the active ASB
            lgr     7,3                       # Preserve the ORB address
            lgr     8,4                       # Preserve the IRB address
            lgr     9,2                       # Preserve the device ID
            la      10,.Lioal_exio_iib(15)    # Locate the IIB

.Lioal_exio64_try:
            lg      1,.LASBG_doio(6)          # Locate INITIATE IO abstraction
            callrx  1                         # Start the I/O
            ltgr    2,2                       # Did the I/O start OK?
            jz      .Lioal_exio64_wait        # ..Yes, wait for result
            clg     2,.Lioal_exio64_1-0b(13)  # Status pending?
            jne     .Lioal_exio64_ret         # ..No, (busy or not oper), return

            # Clear pending status that inhibited the I/O from starting
            ltgr    10,10                     # Attempted to clear status?
            jnz     .Lioal_exio64_ret         # Give up
            lgr     2,9                       # Set the device ID
            lgr     3,8                       # Set the IRB address
            lg      1,.LASBG_qint(6)          # Locate QUERY INTERRUPT abstraction
            callrx  1                         # Call it
            la      10,1                      # Indicate we did this once
            j       .Lioal_exio64_try         # Try again

.Lioal_exio64_wait:
            la      2,.Lioal_exio_iib(15)     # Locate the IIB
            # Set up the device wait list
            mvc     .Lioal_exio_waits-0b(4,15),.Lioal_exio64_1-0b(13) # Count
            st      9,.Lioal_exio_waitd(15)   # device doing I/O
            la      3,.Lioal_exio_waits(15)   # Point to device list
            sgr     4,4                       # Not waiting on external ints.
            lg      1,.LASBG_ihwait(6)        # Locate INTERRUPT WAIT
            callrx  1                         # Wait for device to finish

.Lioal_exio64_done:
            # R2 already points to the IIB
            lgr    3,8                        # Set the IRB address
            lg     1,.LASBG_qint(6)           # Locate QUERY INTERRUPT abstraction
            callrx 1                          # Call it

.Lioal_exio64_ret:
            returnx

.endif # .if .Lioal_64bit scope

            .sbttl "I/O Hardware Abstraction Layer - Shared Subroutines"
            .eject

.if .Lhal_s370
  # +--------------------------+
  # |  CCW0 Shared Subroutine  |
  # +--------------------------+

  # On entry:                Usage in: ioal_data_chan         ioal_datp_chan
  #    R2                              ORB address            IDAW address
  #    R3                              Program data address   ORB address 
  #    R4                                                     not used
  #    R5                                                     Program data address
  #    R6     ORB address
  #    R7     Program data address
  #    R11    Caller's return address
  #    R13-R15 reserved
  #
  # Used:
  #    R8      CCW0 address (from ORB)
  #
  # Not Used:
  #    R10     Subroutine base register not required
  #
  # On exit:
  #    CCW0 contains valid program data addressing

           .align 2
.Lioal_ccw0:
           ni     .LORB_f2(6),0xFF-.LORB_f2_F   # Set ORB for CCW0
           l      8,.LORB_pgm(6)                # Fetch the CCW0 address from ORB     
           stcm   7,0b0111,.LCCW0_addr(8)       # Set data address in CCW0
           br     11                            # Return to caller

.endif # .if .Lhal_s370 scope

.if .Lhal_s390
  # +--------------------------+
  # |  CCW1 Shared Subroutine  |
  # +--------------------------+

  # On entry:                Usage in: ioal_data_s390         ioal_datp_s390
  #    R2                              ORB address            IDAW address
  #    R3                              Program data address   ORB address 
  #    R4                                                     not used
  #    R5                                                     Program data address
  #    R6     ORB address
  #    R7     Program data address
  #    R11    Caller's return address
  #    R13-R15 reserved
  #
  # Used:
  #    R8      CCW1 address (from ORB)
  #
  # Not Used:
  #    R10     Subroutine base register not required
  #
  # On exit:
  #    CCW0 contains valid program data addressing information

           .align 2
.Lioal_ccw1:
           oi     .LORB_f2(6),.LORB_f2_F        # Set CCW1 use in ORB
           l      8,.LORB_pgm(6)                # Fetch the CCW1 address from ORB
           st     7,.LCCW1_addr(8)              # Set data address in CCW1
           ni     .LCCW1_addr(8),0x7F           # Make sure high-order bit is zero
           br     11                            # Return to caller

.endif # .if .Lioal_s390

            .sbttl "I/O Hardware Abstraction Layer - Global Data"
            .eject
  # +-----------------------------+
  # |  I/O HAL Global Data Areas  |
  # +-----------------------------+

.Lioal_asbg:.long  0   # .quad  Active ASB 64-bit pointer
.Lioal_asb: .long  0   # .long  Active ASB 32-bit pointer
.Lioal_cc0: .hword 0   # .hword CC0 return code
.Lioal_cc1: .hword 1   # .hword CC1 return code
.Lioal_cc2: .hword 2   # .hword CC2 return code
.Lioal_cc3: .hword 3   # .hword CC3 return code

.if .Lhal_s370

 # s370 Device Table controls
.Lioal_DT_start: .long 0
.Lioal_DT_end:   .long 0
.Lioal_DT_max:   .long 0
.Lioal_DT_size:  .long .LSCHIB_len

 # Used to clear PMCW reserved fields and those managed by the subsystem
.Lioal_pmcw_mask:
            .long  0xFFFFFFFF   # 0      Interruption Parameter (program)
            .byte  0x38         # 1.0    I/O Interruption Subclass (program)
            .byte  0b10000001   # 1.1    Flag byte 1
            .hword 0xFFFF       # 1.2-3  Device Number
            .byte  0xFF         # 2.0    Logical Path Mask (program)
            .byte  0xFF         # 2.1    Path Not Operational (subsystem)
            .byte  0xFF         # 2.2    Last Path-Used Mask (subsystem)
            .byte  0xFF         # 2.3    Path Installed Mask (does not change)
            .hword 0x0000       # 3.0,1  Measurement Block Index (not supported)
            .byte  0xFF         # 3.2    Path Operational Mask (subsystem)
            .byte  0xFF         # 3.3    Path Available Mask (subsystem)
            .byte  0xFF         # 4.0    CHPID-0
            .byte  0x00         # 4.1    CHPID-1
            .hword 0x0000       # 4.2,3  CHPID-2,3
            .long  0x00000000   # 5      CHPID-4-7
            .long  0x00000001   # 6      F,X unsupported; S supported

.endif # .if .Lhal_s370 scope

.endif # .ifndef .Lioal_S scope
