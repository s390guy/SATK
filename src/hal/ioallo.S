.ifndef .Lioallo_S
.Lioallo_S = 1
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

 # This module contains a set of low level I/O Hardware Abstraction Layer 
 # ABI-compliant functions.
 #
 # 
 #
 # ioallo.S is automatically included by platform.S if io=low or io=yes was
 # specified on the halfeat macro.
 #
 # Functions:
 #
 #  Abstraction   32-bit channel    32-bit I/O subsystem     64-bit I/O subsystem
 #  Included ifdef .Lhal_s370           .Lhal_s390             .Lhal_s390x
 #
 #  CCW PREP      .Liolo_ccw_chan   .Liolo_ccw_s390          .Liolo_ccw_s390x
 #  ENABLE DEVICE .Liolo_ena_chan   .Liolo_ena_s390          .Liolo_ena_s390   
 #  FIND DEVICE   .Liolo_find_chan  .Liolo_find_s390         .Liolo_find_s390
 #  INPUT/OUTPUT  .Liolo_io_chan    .Liolo_io_s390           .Liolo_io_s390x
 #
 # HAL Error Codes
 #  See HAL.S for a complete listing of error codes
 #
 # Dependencies:
 #

    .ifndef .LASB_S
            .include "ASB.S"   # Include HAL Support if not already included
    .endif
    .ifndef .Lio_S
            .include "io.S"    # I/O Structures if not already included
    .endif
    .ifndef .Ls370_S
            .include "s370.S"  # S/370 I/O instruction macros
    .endif

  # +----------------------------------------------+
  # |  Unsupported I/O Abstraction Layer function  |
  # +----------------------------------------------+

  # On Entry:
  #    R14    Caller's return address
  #
  # On Exit:
  #    Program interrupt due to halabort

            .align 2
.Lioal_unsup:
            halabort error=0x0008

.if .Lhal_iolo
            
.if .Lhal_s370
            .sbttl "s370 Low Level I/O Hardware Abstraction Layer"
            .eject
  # +----------------------------------------+
  # |  System/370 CCW FORMATING abstraction  |
  # +----------------------------------------+

  # This abstraction formats a CCW1 into a CCW0 for use with the channel I/O
  # system.
  #
  # On entry:
  #    R2     I/O data area address (.LIOLO structure)
  #    R3     not used (should be zero)
  #    R4     24-bit CCW address in register bits 8-31, register bits 0-7 ignored
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Address of CCW1 being converted to CCW0
  #    R8     CCW1 data being relocated
  #
  # On exit:
  #    The CCW1 identified by the .LIOLO_ccw1 area has been converted to a CCW0

            func370 .Liolo_ccw_chan
            push370

            l      7,.LIOLO_ccw1(2)          # Locate the CCw1 for conversion
            l      8,0(7)                    # Fetch the CCW1 data being relocated
            # CCW0 and CCW1 command is in the same position, no action taken
            stcm   4,0b0111,.LCCW0_addr(7)   # Set the CCW0 address
            stcm   8,0b0100,.LCCW0_flags(7)  # Set the CCW0 flags
            ni     .LCCW0_flags(7),0xFE      # Set reserved bit to zero
            mvi    .LCCW0_resv(7),0x00       # Set the CCW0 reserved bits to zero
            sth    8,.LCCW0_cnt(7)           # Set the CCW0 count
            # CCW0 and CCW1 data length is in the same position, no action taken

            return

  # +-------------------------------------+
  # |  System/370 ENABLE I/O abstraction  |
  # +-------------------------------------+
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    C2     Enables channels for interrupts
  #
  # On exit: None

            func370 .Liolo_enio_chan

    # Local literal pool
.Liolo_enio_chan_cr2:
            .long  0xFFFFFFFF  # Enable all channels for interrupts

            push370

            lctl   2,2,.Liolo_enio_chan_cr2-0b(13)  # Enable interrupts

            return

  # +--------------------------------------------+
  # |  System/370 ENABLE SUBCHANNEL abstraction  |
  # +--------------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Device id (device address in bits 16-31)
  #
  # On exit:
  #    R2     Whether ready for use
  #             0 == success, device usable
  #             3 == could not enable, device not operational

            func370 .Liolo_ena_chan

  # Local literal pool
.Liolo_ena_chan_cc3:
            .long  3

            push370

            lr    7,2                                # Free up return code reg.
            sr    2,2                                # Set return code to zero
            tio   0,7                                # Test the device
            bc    0b1110,.Liolo_ena_chan_ret-0b(13)  # Operational, rc == 0
            l     2,.Liolo_ena_chan_cc3-0b(13)       # Not operational, rc == 3

.Liolo_ena_chan_ret:
            return

  # +--------------------------------------+
  # |  System/370 FIND DEVICE abstraction  |
  # +--------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: none
  # On exit: none

            func370 .Liolo_find_chan
            push370

            sll    2,16       # Just clear high-order bits
            srl    2,16       # to make sure this is a channel I/O device id
            return

  # +---------------------------------------+
  # |  System/370 INPUT/OUTPUT abstraction  |
  # +---------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device id (zeros in bits 0-15, device CCUU address in bits 16-31)
  #    R3     I/O results data and options (.LIOLO structure)     
  #    R4     Condition checks                        Suggested Masks
  #            Bits 0-7    Channel status error masks      0x3F (all channel checks)
  #            Bits 8-15   Channel alert masks             0x80 (IL)   PCI ignored
  #            Bits 16-23  Device status error masks       0x02 (UC)   busy ignored
  #            Bits 24-31  Device status alert masks       0xC1 (AT,SM,UE)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     Device ID for which I/O is to occur  
  #    R7     Active ASB
  #    R8     Used by subroutine to accumulate results
  #    R9     Wait subroutine address
  #
  # On exit:
  #    R2     I/O condition
  #      Bits   Bits 
  #      0-7    8-31  (may be used in branch table)
  #       0       0     I/O successful, CSW also stored in .LIOLO
  #       0       4     SIO failed to initiate or I/O did not complete, 
  #                     path (channel, subchannel or device) not operational
  #       0       8     Device status lost
  #       0      12     Channel errors in .LIOLO_cherr, CSW also stored in .LIOLO
  #       0      16     Channel alert in .LIOLO_chalt,  CSW also stored in .LIOLO
  #       0      20     Device errors in .LIOLO_dverr,  CSW also stored in .LIOLO
  #       0      24     Device alert in .LIOLO_dvalt,   CSW also stored in .LIOLO

            func370 .Liolo_io_chan

 # Local stack frame usage
            fquad  .Liolo_chan_nPSW    # PSW used to continue after waiting
            fquad  .Liolo_chan_sPSW    # Save area for nPSW

            push370

            l        7,.LIEIB_asb(0)            # Locate active ASB
            mvi      .LIOLO(3),0x00             # Clear results area
            mvc      .LIOLO+1(.LIOLO_resp_len-1,3),.LIOLO(3)
            l        8,.LIOLO_dev(2)            # Set device address

            tm       .LIOLO_options(2),.LIOLO_noio # Do, I/O?
            bo       .Liolo_chan_wait-0b(13)    # ..No, just look for status
            mvc      .LIO_caw(4,0),.LIOLO_ccw1(2)  # Set Channel Address Word

.Liolo_chan_retry:   # If I/O is attempted again        
            sio      0,8                             # Start I/O
            bc       0b1000,.Liolo_chan_status-0b(13)# CC0 (initiated) continue
            bc       0b0100,.Liolo_chan_csw-0b(13)   # CC1 (status stored) check
            bc       0b0010,.Liolo_chan_retry-0b(13) # CC2 (chan/subch busy)
            # Fall through                           # CC3 (not operational) end

.Liolo_chan_nop:  # Device not operational return code == 4
            sr       2,2
            la       2,4
            b        .Liolo_chan_ret-0b(13)

.Liolo_chan_status:
            tm       .LIOLO_options(2),.LIOLO_poll   # Wait or poll for completion?
            bz       .Liolo_chan_wait-0b(13)         # ..wait if option is zero

.Liolo_chan_test:
            tio      0,8                             # Test I/O
            bc       0b0100,.Liolo_chan_csw-0b(13)   # CC1 (status stored) check it
            bc       0b0001,.Liolo_chan_nop-0b(13)   # CC3 (not operational) end
            bc       0b0010,.Liolo_chan_test-0b(13)  # CC2 (busy) still executing
            # Fall through                           # CC0 (available) status lost

            # I/O status lost return code == 8
            sr       2,2
            la       2,8
            b        .Liolo_chan_ret-0b(13)

.Liolo_chan_wait:
            mvc      .LIOLO_nPSW(8,2),.LASB_runpsw(7)  # Set my run PSW
            mvc      .LIOLO_wPSW(8,2),.LASB_waitpsw(7) # Set my wait PSW
            la       9,.Liolo_wait32-0b(13)          # Locate the wait routine
.Liolo_chan_wait_again:
            basr     11,9                            # Wait for the I/O interrupt
            lh       8,.LASB_iodev(7)                # Locate where device addr is
            lh       8,0(8)                          # Fetch the device
            cr       1,8                             # Device we expected?
            bne      .Liolo_chan_wait_again-0b(13)   # ..No, continue waiting

.Liolo_chan_csw:
            mvi      0(3),0x00
            mvc      .LIOLO_CSW+1(7,2),.LIO_csw(0)   # Store CSW
            la       10,.Liolo_csw_anal-0b(13)   # Locate CSW analysis subroutine
            basr     11,10                       # Analyze, set completion status

            tm       .LIOLO_options(2),.LIOLO_noio # Just looking for status?
            bo       .Liolo_chan_wait-0b(13)     # ..Yes, have it, set rc and return

            cli      .LIOLO_done(4),0x0C         # I/O done
            bne      .Liolo_chan_status-0b(13)   # ..No, look for completion
            
            sr       2,2
            la       10,.Liolo_results-0b(13)    # Analyze results
            basr     11,10                       # and set the return code

.Liolo_chan_ret:
            return

.endif # .if .Lhal_s370 scope

.if .Lhal_s390
           .eject
           .sbttl "s390 Low Level I/O Hardware Abstraction Layer"
  # +-------------------------------------+
  # |  ESA/390 CCW FORMATING abstraction  |
  # +-------------------------------------+
  # Access: public

  # This abstraction formats the CCW and generates, if necessary, IDAW2 values.
  #
  # IDAW2's are required only when ESA/390 is operating in a platform in which
  # z/Architecture is also present AND the CCW data address is larger than 31 bits.
  # When IDAW2's are required they are handled as follows:
  #
  # The next available IDAW2 field is located via the .LIOLO_idaw2 field.  This
  # field at the start of a set of CCW formatting operation points to the first 
  # IDAW2 in the list.  The list is assumed to be initialized to zeros with the 
  # high-order bit (bit 0) set to one of the LAST IDAW2 in the list.  As the 
  # formatting operations proceed, entries from the IDAW2 list are consumed and the
  # .LIOLO_idaw2 field is updated until the formatting operations are complete, 
  # or the IDAW2 list is exhaused.  If the IDAW2 list is exhaused, an abort is 
  # performed.
  #
  # On entry:
  #    R2     I/O data area address (.LIOLO structure)
  #
  #  The register usage of R3-R4 is dependent upon the enabled architecture
  #                 ESA/390 only                 ESA/390 and z/Architecture
  #    R3     not used (should be zero)      64-bit data address (bits 0-31)
  #    R4     31-bit data address            64-bit data address (bits 32-64)
  #
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R0,R1  By IDAW shared subroutine
  #    R5     IDAW2 list address
  #    R6     By IDAW shared subroutine
  #    R7     CCW1 address
  #    R8,R9  By IDAW shared subroutine
  #    R10    Shared subroutine address
  #    R11    Shared subroutine return address
  #
  # On exit:
  #    The CCW1 identified by the .LIOLO_ccw1 area has been updated with the
  #    data (and IDAW2's built if necessary).

            func370 .Liolo_ccw_s390
            push370

            l       7,.LIOLO_ccw1(2)      # Fetch the CCW1 being formatted for I/O
.if .Lhal_s390x
            # Test if 64-bit address requires IDAW's
            ltr     3,3                            # Is address bits 0-31 zero?
            bnz     .Liolo_ccw_s390_set-0b(13)     # ..No, need to build IDAW's
            ltr     4,4                            # Is address bit 32 zero?
            bnm     .Liolo_ccw_s390_set-0b(13)     # ..Yes, do not need IDAW's
            l       5,.LIOLO_idaw2(2)              # Locate the IDAW2 list
            la      10,.Liolo_sio_idaw2-0b(13)     # Locate shared subroutine
            basr    11,10                          # Build IDAW2's
            b       .Liolo_ccw_s390_ret-0b(13)     # Return to caller

.Liolo_ccw_s390_set:
.endif # .if .Lhal_390x

    # Store the CCW data address as in the CCW
           st       4,4(7)                # Place the data address in the CCW
           ni       .LCCW1_flags(7),0xFE  # Make sure reserved bit is zero
           ni       .LCCW1_addr(7),0x7F   # Make sure bit 0 is zero

.Liolo_ccw_s390_ret:
           return

  # +----------------------------------+
  # |  ESA/390 ENABLE I/O abstraction  |
  # +----------------------------------+
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    C6     Enables all subclasses for interrupts
  #
  # On exit: None

            func370 .Liolo_enio_s390

    # Local literal pool
.Liolo_enio_s390_cr6:
            .long  0xFF000000  # Enable all subchannel subclasses for interrupts

            push370

            lctl   6,6,.Liolo_enio_s390_cr6-0b(13)  # Enable interrupts

            return

  # +-----------------------------------------+
  # |  ESA/390 ENABLE SUBCHANNEL abstraction  |
  # +-----------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID for I/O instructions (shared subroutine)
  #    R7     Address of the SCHIB
  #
  # On exit:
  #    R2     Whether successfully modified or not
  #             0 == success
  #             1 == could not enable, subchannel status pending
  #             2 == could not enable, subchannel busy
  #             3 == could not enable, subchannel not operational

            func370 .Liolo_ena_s390

  # Local stack frame usage
            fbytes .Liolo_ena_s390_schib,.LSCHIB_len

            push370

            lr    1,2
            la    7,.Liolo_ena_s390_schib(15)
            la    10,.Liolo_sio_enable-0b(13)
            basr  11,10
            savecc 2
            return

  # +---------------------------------------+
  # |  ESA/390 FIND SUBCHANNEL abstraction  |
  # +---------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device number
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: 
  #    R1     SSID for I/O instructions
  #    R7     Pointer to the SCHIB storage area
  #
  # On exit:
  #    R2     Subchannel if found, device number if not found

            halfunc .Liolo_find_s390

  # Local literal pool usage
.Liolo_find_s390_ssid_ck:
            .hword 0x0000

  # Local stack frame usage
            fbytes .Liolo_find_s390_schib,.LSCHIB_len

            halpush

            clm    2,0b1100,.Liolo_find_s390_ssid_ck-0b(13) # Device number?
            bnzr   2                              # ..No, already a SSID
            la     7,.Liolo_find_s390_schib(15)   # Locate the SCHIB area
            la     10,.Liolo_sio_find-0b(13)      # Locate the find subroutine
            basr   11,10                          # Try to find the subchannel
            return

  # +------------------------------------+
  # |  ESA/390 INPUT/OUTPUT abstraction  |
  # +------------------------------------+
  # Access: public

  # On entry:
  #    R2     I/O data address (.LIOLO structure)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID for I/O instructions (in shared subroutine)
  #    R3     Condtion checks (in shared subroutine)
  #            Bits 0-7    Channel status error masks      0x3F (all channel checks)
  #            Bits 8-15   Channel alert masks             0x80 (IL)   PCI ignored
  #            Bits 16-23  Device status error masks       0x02 (UC)   busy ignored
  #            Bits 24-31  Device status alert masks       0xC1 (AT,SM,UE)
  #    R6     Subsystem I/O shared routine address
  #    R7     Active ASB (not used by shared subroutine, but preserved)
  #    R8     ORB address or used by subroutine to accumulate results
  #    R9     I/O wait shared subroutine address
  #    R10    Shared subroutine address
  #    R11    Shared subroutine return address
  #    R12    Subsytem I/O shared routine return address
  #
  # On exit:
  #    R2     I/O condition
  #      Bits   Bits 
  #      0-7    8-31  (may be used in branch table)
  #       0       0     I/O successful, CSW also stored
  #       0       4     SIO failed to initiate or I/O did not complete, 
  #                     path (channel, subchannel or device) not operational
  #       0       8     Device status lost
  #       0      12     Channel errors in .LIOLO_cherr, CSW also stored
  #       0      16     Channel alert in .LIOLO_chalt,  CSW also stored
  #       0      20     Device errors in .LIOLO_dverr,  CSW also stored
  #       0      24     Device alert in .LIOLO_dvalt,   CSW also stored

            func370 .Liolo_io_s390
            push370

            l      7,.LIEIB_asb(0)           # Locate active ASB
            la     9,.Liolo_wait32-0b(13)    # Locate wait subroutine
            mvc    .LIOLO_nPSW(8,2),.LASB_runpsw(7)  # Set my new I/O PSW
            mvc    .LIOLO_wPSW(8,2),.LASB_waitpsw(7) # Set my I/O wait PSW
            la     6,.Liolo_sio-0b(13)       # Locate the I/O shared subroutine
            basr   12,6                      # Do the I/O

            return                           # Return to caller

.endif # .if .Lhal_s390

.if .Lhal_s390x
           .sbttl "s390x - Low Level I/O Hardware Abstraction Layer"
           .eject

  # +--------------------------------------------+
  # |  z/Architecture CCW FORMATING abstraction  |
  # +--------------------------------------------+
  # Access: public

  # This abstraction formats the CCW and generates, if necessary, IDAW2 values.
  #
  # IDAW2's are required only when z/Architecture needs to access real storage above
  # the 2G boundary.  See the description of IDAW2 handling by the ESA/390 CCW
  # FORMATING abstraction.
  #
  # On entry:
  #    R2     I/O data area 64-bit address (.LIOLO structure)
  #    R3     64-bit address high-order bits (in register bits 32-63)
  #    R4     64-bit address low-order bits (in register bits 32-63)
  #
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R0,R1  By IDAW shared subroutine
  #    R5     IDAW2 list address
  #    R6     By IDAW shared subroutine
  #    R7     CCW1 address
  #    R8,R9  By IDAW shared subroutine
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # On exit:
  #    The CCW1 identified by the .LIOLO_ccw1 area has been updated with the
  #    data (and IDAW2's built if necessary).

            functionx .Liolo_ccw_s390x

    # Local literal pool usage
.Liolo_ccw_s390x_max:
            .quad  0x000000007FFFFFFF        # Maximum 31-bit address

            pushx

            llgt   5,.LIOLO_idaw2(2)         # Locate the IDAW2 list
            llgt   7,.LIOLO_ccw1(2)          # Locate the CCW1 that may need IDAWs

            ltr    3,3                       # Are high-order bits in use?
            jnz    .Liolo_ccw_s390x_idaw2    # ..yes, IDAW's are needed
            ltr    4,4                       # Is bit 32 set to one?
            jm     .Liolo_ccw_s390x_max      # ..yes, IDAW's needed?
            j      .Liolo_ccw_s390x_set      # ..No, just set up the CCW   

.Liolo_ccw_s390x_idaw2:
            # Shared subroutine will treat R3 and R4 as 32-bit registers
            la     10,.Liolo_sio_idaw2-0b(13)   # Locate shared subroutine
            basr   11,10                     # Build IDAW2's
            j      .Liolo_ccw_s390x_ret      # Return done

.Liolo_ccw_s390x_set:
            st     4,.LCCW1_addr(7)          # Set the CCW1 address
            ni     .LCCW1_flags(7),0xFE      # Make sure reserved bit is zer0

.Liolo_ccw_s390x_ret:
            returnx

  # +-----------------------------------------+
  # |  z/Architecture ENABLE I/O abstraction  |
  # +-----------------------------------------+
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    C6     Enables all subclasses for interrupts
  #
  # On exit: None

            functionx .Liolo_enio_s390x

    # Local literal pool
.Liolo_enio_s390x_cr6:
            .long  0xFF000000  # Enable all subchannel subclasses for interrupts

            pushx

            lctl   6,6,.Liolo_enio_s390x_cr6-0b(13)  # Enable interrupts

            returnx

  # +------------------------------------------------+
  # |  z/Architecture ENABLE SUBCHANNEL abstraction  |
  # +------------------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device id (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID for I/O instructions (shared subroutine)
  #    R7     Address of the SCHIB
  #
  # On exit:
  #    R2     Whether successfully modified or not
  #             0 == success
  #             1 == could not enable, subchannel status pending
  #             2 == could not enable, subchannel busy
  #             3 == could not enable, subchannel not operational

            functionx .Liolo_ena_s390x

  # Local stack frame usage
            fbytes .Liolo_ena_s390x_schib,.LSCHIB_len

            pushx

            lr    1,2
            la    7,.Liolo_ena_s390x_schib(15)
            la    10,.Liolo_sio_enable-0b(13)
            basr  11,10
            saveccg 2
            returnx

  # +----------------------------------------------+
  # |  z/Architecture FIND SUBCHANNEL abstraction  |
  # +----------------------------------------------+
  # Access: public

  # On entry:
  #    R2     Device number (SSID)
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: 
  #    R1     SSID for I/O instructions
  #    R7     Pointer to the SCHIB storage area
  #
  # On exit:
  #    R2     Subchannel if found, device number if not found

            functionx .Liolo_find_s390x

  # Local stack frame usage
            fbytes .Liolo_find_s390x_schib,.LSCHIB_len

            pushx

            la     7,.Liolo_find_s390x_schib(15)  # Locate the SCHIB area
            la     10,.Liolo_sio_find-0b(13)      # Locate the find subroutine
            basr   11,10                          # Try to find the subchannel
            sllg   2,2,32                         # Make sure high-order..
            srlg   2,2,32                         # ..bits are zero
            returnx

  # +-------------------------------------------+
  # |  z/Architecture INPUT/OUTPUT abstraction  |
  # +-------------------------------------------+
  # Access: public

  # This abstraction performs subsystem I/O a 64-bit architecture
  #
  # On entry:
  #    R2     .LIOLO structure address
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R1     SSID for I/O instructions (in shared subroutine)
  #    R3     Condition checks (in shared subroutine)
  #            Bits 32-39  Channel status error masks      0x3F (all channel checks)
  #            Bits 40-47  Channel alert masks             0x80 (IL)   PCI ignored
  #            Bits 48-55  Device status error masks       0x02 (UC)   busy ignored
  #            Bits 56-64  Device status alert masks       0xC1 (AT,SM,UE)
  #    R6     Subsystem I/O shared routine address
  #    R7     Active ASB
  #    R8     ORB/IRB address or used by subroutine to accumulate results
  #    R9     I/O wait shared subroutine address
  #    R10    Shared subroutine address
  #    R11    Shared subroutine return address
  #    R12    Subsytem I/O shared routine return address
  #
  # On exit:
  #    R2     I/O condition
  #      Bits   Bits 
  #      0-7    8-31  (may be used in branch table)
  #       0       0     I/O successful, CSW also stored
  #       0       4     SIO failed to initiate or I/O did not complete, 
  #                     path (channel, subchannel or device) not operational
  #       0       8     Device status lost
  #       0      12     Channel errors in .LIOLO_cherr, CSW also stored
  #       0      16     Channel alert in .LIOLO_chalt,  CSW also stored
  #       0      20     Device errors in .LIOLO_dverr,  CSW also stored
  #       0      24     Device alert in .LIOLO_dvalt,   CSW also stored

            functionx .Liolo_io_s390x
            pushx

            lg     7,.LIEIB_asbg(0)          # Locate active ASB
            la     9,.Liolo_wait64-0b(13)    # Locate wait subroutine
            mvc    .LIOLO_nPSW(16,2),.LASBG_runpsw(7)  # Set my new I/O PSW
            mvc    .LIOLO_wPSW(16,2),.LASBG_waitpsw(7) # Set my I/O wait PSW
            la     6,.Liolo_sio-0b(13)       # Locate the I/O shared subroutine
            basr   12,6                      # Do the I/O
            sllg   2,2,32                    # Clear high-order
            srlg   2,2,32                    # bits of return code

            returnx


.endif # .if .Lhal_s390x

.if .Lhal_32bit
  # +---------------------------------------+
  # |  Null I/O Abstraction Layer function  |
  # +---------------------------------------+

  # On Entry:
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: none
  # On Exit: none

            func370 .Liolo_null32
            push370
            return

  # +-----------------------------------------------+
  # |  32-bit I/O Interrupt Wait Shared Subroutine  |
  # +-----------------------------------------------+
  # Access: private

  # On Entry:
  #    R2     Pointer to Low-Level Input/Output Area (.LIOLO structure)
  #    R9     This shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used: none
  #    
  # On Exit:
  #    An I/O interrupt has occurred

.Liolo_wait32:
0:
            mvc    .LIOLO_sPSW(8,2),.LPSW_newio(0)   # Save the current I/O new PSW
            mvc    .LPSW_newio(8,0),.LIOLO_nPSW(2)   # Set my I/O new PSW
            lpsw   .LIOLO_wPSW(2)                    # Wait...
.Liolo_run32: # Control returns here from .LASB_runpsw
            mvc    .LPSW_newio(8,0),.LIOLO_sPSW(2)   # Restore previous I/O new PSW
            br     11

.endif # .if .Lhal_32bit

.if .Lhal_64bit
  # +-----------------------------------------------+
  # |  64-bit I/O Interrupt Wait Shared Subroutine  |
  # +-----------------------------------------------+
  # Access: private

  # On Entry:
  #    R2     Pointer to Low-Level Input/Output Area (.LIOLO structure)
  #    R9     This shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used: none
  #    
  # On Exit:
  #    An I/O interrupt has occurred

.Liolo_wait64:
0:
            mvc    .LIOLO_sPSW(16,2),.LPSW_newiog(0) # Save the current I/O new PSW
            mvc    .LPSW_newiog(16,0),.LIOLO_nPSW(2) # Set my I/O new PSW
            lpswe  .LIOLO_wPSW(2)                    # Wait...
.Liolo_run64: # Control returns here from .LASB_runpsw
            mvc    .LPSW_newiog(16,0),.LIOLO_sPSW(2) # Restore previous I/O new PSW
            br     11

.endif # .if .Lhal_64bit

.if .Lhal_sio

.if .Lhal_s390x
  # +---------------------------+
  # |  IDAW2 Shared Subroutine  |
  # +---------------------------+
  # Access: private

  # This shared subroutine builds a list of IDAW2s when called
  # WARNING: Tape device READ BACKWARD commands are not supported

  # On Entry:
  #    R2     Pointer to Low-Level Input/Output Area (.LIOLO structure)
  #    R3,R4  64-bit data address
  #    R5     IDAW2 address
  #    R7     CCW1 address
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used:
  #    R0      Number of bytes remaining to be covered by IDAW's
  #    R1      Holds the IDAW2 end-of-list flag to detect list exhaustion
  #    R5      IDAW2 pointer
  #    R6      Byte position relative to a 4K page for the program data start
  #    R8      CCW1 address (from ORB)
  #    R9      Number of count bytes to which this IDAW2 provides locations

.Liolo_sio_idaw2:
0:
            sr     0,0                           # Clear R0
            lr     1,0                           # and R1
            icm    0,0b0011,.LCCW1_cnt(7)        # Get the program data byte count
            ni     .LIOLO_idaw2(2),0x7F          # Make sure bit 0 is zero
            # (ESA/390 does not care, but z/Architecture 64-bit addressing will)
            l      5,.LIOLO_idaw2(2)             # Locate the IDAW


            # Point the CCW1 to the IDAW2 list
            st     5,.LCCW1_addr(7)              # Set the IDA address in CCW1
            ni     .LCCW1_addr(7),0x7F           # Make sure bit 0 is zero
            oi     .LCCW1_flags(7),.LCCW_IDA     # Use the IDAW list

            # Determine number of bytes in current program data page
            lr     6,4                           # Calculate the starting page pos.
            n      6,.Liolo_sio_idaw2_pagmsk-0b(10)  # relative to page start
            lh     9,.Liolo_sio_idaw2_pagsiz-0b(10)  # Size of a page
            sr     9,6                           # Bytes in this page.

.Liolo_sio_idaw2_build:
            stm    3,4,0(5)                      # Create the first IDAW
            la     5,8(5)                        # Update the IDAW2 pointer
            ic     1,0(5)                        # Save IDAW2 end-of-list flag

            # Can all of the bytes fit in this page
            sr     0,9                           # count -= covered by IDAW
            bnp    .Lioal_sio_idaw2_done-0b(10)  # done if count <= 0?

            # More IDAW's needed - Increment program data by bytes covered
            ltr    1,1                           # Any more IDAW"s?
            bz     .Liolo_sio_idaw2_incr-0b(10)  # ..Yes, continue
            halabort error=0x0012                # ..no, abort

            # Increment program data by bytes covered
.Liolo_sio_idaw2_incr:
            alr    4,9
            bc     0b1100,.Liolo_sio_idaw2_nocarry-0b(10)
            al     3,.Liolo_sio_idaw2_one-0b(10)
.Liolo_sio_idaw2_nocarry:

            # Starting now on a page boundary
            lh     9,.Liolo_sio_idaw2_pagsiz-0b(10) # Have 4096 bytes available
            b      .Liolo_sio_idaw2_build-0b(10)    # Make next IDAW2

.Lioal_sio_idaw2_done:
            ni     .LIOLO_orb+.LORB_f2(2),0xFF-.LORB_f2_T  # Using 4096-byte IDAW's
            st     5,.LIOLO_idaw2(2)                # Update IDAW2 address
            br     11                               # Return to caller

            .align 4
.Liolo_sio_idaw2_one:
            .long  0x00000001   # Constant of one
.Liolo_sio_idaw2_pagmsk:
            .long  0x00000FFF   # 4K IDAW page boundary mask
.Liolo_sio_idaw2_pagsiz:
            .long  0x00001000   # 4K IDAW page size

.endif # .if .Lhal_s390x

  # +---------------------------------------------+
  # |  Subchannel Input/Output Shared Subroutine  |
  # +---------------------------------------------+
  # Access: private

  # This subroutine performs subsystem I/O for both 32-bit and 64-bit archs.
  #
  # On entry:
  #    R2     Low Level Input/Output Area (31/64 bit address .LIOLO structure)
  #    R6     This shared subroutine's base address (31/64 bit)
  #    R7     Active ASB (not used, but preserved)
  #    R9     I/O wait shared subroutine address (31/64 bit)
  #    R10    Shared subroutine base address (31/64 bit)
  #    R11    Shared subroutine return address (31/64 bit)
  #    R12    This shared subroutine's return address (31/64 bit)
  #
  # Used:
  #    R1     SSID for I/O instructions (from .LIOLO)
  #    R3     Requested I/O condition checks (from .LIOLO)
  #    R8     I/O instruction ORB or IRB address (31/64 bit)
  #    
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  # 
  # On return:
  #    R2     Contains return code (32-bit)

            .align 2
.Liolo_sio:
0:
            l      1,.LIOLO_dev(2)            # Set SSID for I/O instructions
            l      3,.LIOLO_cherr(2)          # Set the condition checks
            mvi    .LIOLO_rslts(2),0x00       # Clear results area
            mvc    .LIOLO_rslts+1(.LIOLO_resp_len-1,2),.LIOLO_rslts(2)

            tm     .LIOLO_options(2),.LIOLO_noio  # Just looking for status?
            bo     .Liolo_sio_status-0b(6)    # ..Yes, (like a console ATTN)
            la     8,.LIOLO_orb(2)            # Point to ORB for SSCH
            mvi    0(8),0x00                  # Clear the..
            mvc    1(.LORB_len-1,8),0(8)      # ..ORB
            mvc    .LORB_pgm(4,8),.LIOLO_ccw1(2)  # Move CCW1 address to the ORB 
            ni     .LORB_pgm(8),0x7F          # Make sure bit 0 is zero in ORB
.if .Lhal_s390x
            tm     .LIEIB_avl(0),.LIEIB_s390x # Is 64-bit architecture possible?
            bz     .Liolo_sio_orb_s390-0b(6)  # ..No, then use s390 ORB flags
            oc     4(4,8),.Liolo_sio_orb_mask_s390x-0b(6)  # Set s390x ORB flags
.Liolo_sio_orb_s390:
.endif # .if .Lhal_s390x
            oc     4(4,8),.Liolo_sio_orb_mask_s390-0b(6)  # Set s390 ORB flags

.Liolo_sio_retry:   # If I/O is attempted again        
            ssch   0(8)                              # Start I/O
            bc     0b1000,.Liolo_sio_status-0b(6)    # CC0 (initiated) continue
            bc     0b0100,.Liolo_sio_csw-0b(6)       # CC1 (status pending) get it
            bc     0b0010,.Liolo_sio_retry-0b(6)     # CC2 (subch busy)
            # Fall through                           # CC3 (not operational) end

.Liolo_sio_nop:  # Device not operational return code == 4
            la     2,4
            b      .Liolo_sio_ret-0b(6)            # Return to calle
.Liolo_sio_status:
            tm     .LIOLO_options(2),.LIOLO_poll   # Wait or poll for status?
            bo    .Liolo_sio_test-0b(6)            # ..poll if bit 6 is one

.Liolo_sio_wait:
            basr   11,9                            # Wait for I/O interrupt
            cl     1,.LIO_ssid(0)                  # SSID expected?
            bne    .Liolo_sio_wait-0b(6)           # ..No, continue waiting

.Liolo_sio_test:
            la     8,.LIOLO_irb(2)                 # Locate the IRB
.Liolo_sio_ckd:
            tsch   0(8)                            # Test I/O
            bc     0b1000,.Liolo_sio_csw-0b(6)     # CC0 (status stored) analyze
            bc     0b0001,.Liolo_sio_nop-0b(6)     # CC3 (not operational) end
            b      .Liolo_sio_ckd-0b(6)            # CC1 (no status) test again

.Liolo_sio_csw:
            #mvc    .LIOLO_SCSW(12,2),.LIRB_SCSW(8)  # Store SCSW in .LIOLO
            la     10,.Liolo_csw_anal-0b(6)    # Locate CSW analysis subroutine
            basr   11,10                       # Analyze, set completion status

            tm     .LIOLO_options(2),.LIOLO_noio  # Just looking for status?
            bo     .Liolo_sio_setrc-0b(6)      # ..Yes, have it, set rc and return

            tm     .LIOLO_SCSW(2),.LSCSW_primary # Primary status?
            bo     .Liolo_sio_setrc-0b(6)      # ..Yes, we are Done
            #cli    .LIOLO_done(2),0x0C         # I/O done
            #bne    .Liolo_sio_status-0b(6)     # ..No, look for completion

.Liolo_sio_setrc:
            la     10,.Liolo_results-0b(6)     # Analyze results
            basr   11,10                       # and set the return code

.Liolo_sio_ret:
            br     12                          # Return to caller

.if .Lhal_s390x
.Liolo_sio_orb_mask_s390x:
            .long  0x0082FF00  # CCW-1's, 4K Format-2 IDAW's if present, any path
.endif
.Liolo_sio_orb_mask_s390:
            .long  0x0080FF00  # CCW-1's, IDAW's not required, any path

  # +-------------------------------------------+
  # |  Subchannel I/O Enable Shared Subroutine  |
  # +-------------------------------------------+
  # Access: private

  # This subroutine enables a device
  #
  # On entry:
  #    R2     Contains subchannel SSID
  #    R7     Points to the SCHIB area
  #    R8     Device Id for which we are waiting
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used:
  #    R1     SSID for I/O instructions
  # 
  # On return:
  #    cc set for return code

.Liolo_sio_enable:

            lr     1,2                          # Set SSID for I/O instruction
            stsch  0(7)                         # Store the SCHIB
            bcr    0b0111,11                    # Return if SCHIB not stored
            oi     .LPMCW_f1(7),.LPMCW_enable   # Enable the subchannel
            mvi    .LPMCW_isc(7),0x08           # Set subclass 0
            mvi    .LPMCW_lpm(7),0xFF           # Use any available path
            msch   0(7)                         # Update the SCHIB
            br     11                           # Return to caller

  # +---------------------------------------------------+
  # |  Subchannel Find Device Number Shared Subroutine  |
  # +---------------------------------------------------+
  # Access: private

  # This subroutine enables a device
  #
  # On entry:
  #    R2     Contains device number
  #    R7     Points to the SCHIB area
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used:
  #    R1     SSID for I/O instructions
  # 
  # On return:
  #    R2     Contains the subchannel if found, device number otherwise

.Liolo_sio_find:
0:
           l       1,.Liolo_sio_find_start-0b(10)

.Liolo_sio_find_scan:
           stsch   0(7)          # Save the SCHIB
           bcr     0b0001,11     # If not operational, end of subhcannels, return
           tm      .LPMCW_f1(7),.LPMCW_devval   # Is the device number valid?
           bno     .Liolo_sio_find_next-0b(10)  # ..No, skip this one
           ch      2,.LPMCW_dev(7)              # This the device we want?
           be      .Liolo_sio_find_ret-0b(10)   # ..Yes, found it, return result

.Liolo_sio_find_next:
           al      1,.Liolo_sio_find_inc-0b(10) # Increment to the next subchannel
           b       .Liolo_sio_find_scan-0b(10)  # ..and check the next subchannel

.Liolo_sio_find_ret:
           lr      2,1                          # Return the SSID
           br      11                           # Return to caller

.Liolo_sio_find_start:
           .long   0x00010000  # Initial suchannel
.Liolo_sio_find_inc:
           .long   0x00000001  # Increment the subchannel

.endif

  # +------------------------------------------------------------+
  # |  Low-level Channel Status Word Analyzer Shared Subroutine  |
  # +------------------------------------------------------------+
  # Access: private

  # This subroutine analyzes the CSW and updates the accumulated results
  # in the .LIOLO structure
  #
  # On entry:
  #    R2     Pointer to .LIOLO structure
  #    R3     Condition checks requested by low-level caller
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used:
  #    R8     Holds accumulated results
  # 
  # On return:
  #    .LIOLO structure updated

.Liolo_csw_anal:
0:
            mvi      .LIOLO_status(2),0x0C              # Set CE,DE mask
            nc       .LIOLO_status(1,2),.LIOLO_ds(2)    # Update status from (S)CSW
            oc       .LIOLO_done(1,2),.LIOLO_status(2)  # Update completion status
            icm      8,0b1000,.LIOLO_cs(2)        # Load
            icm      8,0b0100,.LIOLO_cs(2)        # (S)CSW status
            icm      8,0b0010,.LIOLO_ds(2)        # into 
            icm      8,0b0001,.LIOLO_ds(2)        # register
            nr       8,3                          # Examine all of the relavant bits
            o        8,.LIOLO_cherr(2)            # Update accumulated results
            st       8,.LIOLO_cherr(2)            # Update structure with results
            br       11                           # Return to caller

  # +---------------------------------------------------+
  # |  I/O Low-level Return Code Set Shared Subroutine  |
  # +---------------------------------------------------+
  # Access: private

  # This subroutine examines the accumulated I/O results and sets the 
  # appropriate return code
  #
  # On entry:
  #    R2     Pointer to results storage area (.LIOLO structure)
  #    R10    Shared subroutine base address
  #    R11    Shared subroutine return address
  #
  # Used:
  #    R0     Counter of number of result fields to check
  #    R2     Calculates the return code
  #    R8     Points to error/alert field
  # 
  # On return:
  #    R2     Return code set

.Liolo_results:
0:
            lh     0,.Liolo_results_num-0b(10)   # Number of fields to scan
            la     8,.LIOLO_cherr(2)             # Starting field
            icm    2,0b1111,0(8)                 # Fetch all conditions
            bzr    11                            # If all zeros, done
            lh     2,.Liolo_results_rc-0b(10)    # Set initial return code
.Liolo_results_test:
            cli    0(8),0x00                     # Did a condition occur?
            bnzr   11                            # ..Yes, return with rc set
            la     2,4(2)                        # ..No, Increment rc by 4
            la     8,1(8)                        # Point to next condition field
            bct    0,.Liolo_results_test-0b(10)  # Continue, if not done
            # No errors or alerts, return code == 0
            sr     2,2
            br     11

.Liolo_results_num:
            .hword  4
.Liolo_results_rc:
            .hword  12


.endif # .if .Lhal_iolo

.endif # .ifndef .Lioallo_S scope
           
