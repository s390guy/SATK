.ifndef .Lhal_S
.Lhal_S = 1

.ifdef .Lhal_options

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

 # This module includes the Hardware Abstraction Layer processing itself.  The 
 # contents of this module are considered private to the Hardware Abstraction
 # Layer.
 #
 #   +----------------------------------------------------+
 #   |  Non-ABI and ABI-Shared Subroutine Register Usage  |
 #   +----------------------------------------------------+
 #
 #   ABI-shared subroutines are subroutines used by both ABI and non-ABI code.
 #   This allows a single subroutine to function for both types of code.
 #
 #   R0       Available for use    
 #   R1       Available for use
 #   R2-R6    Subroutine parameters or available for subroutines shared with ABI
 #            functions
 #   R7-R10   Usage depends upon subroutine.  Volatile for ABI functions that use 
 #            shared subroutines.
 #   R10      Subroutine local base register
 #   R11      Subroutine return address for subroutines shared with ABI functions
 #   R12      Base address of global data (same as Phase 1 base address)
 #   R13      Base register
 #   R14      Subroutine or function return address
 #   R15      Reserved for ABI function stack pointer.  Not used in non-ABI code
 #
 #   When a disabled wait state occurs with an instruction address of 0xBAD, the
 #   old PSW contains the address at which point the unexpected error occurred.
 #
 #  +---------+
 #  |  Notes  |
 #  +---------+
 #
 #  1.  Assembly of hal.S requires s390x as its architecture because of the
 #      presence of z/Architecture instructions and 64-bit address constants.
 #
           .nolist
           .include "IHCB.S"       # Interrupt Handler Abstraction Layer  
           .include "IEIB.S"       # IPL Environement Information Block
           .include "io.S"         # Input/Output macros and storage locations
           .include "psw.S"        # PSW's and PSW assigned storage locations 
           .include "service.S"    # SERVICE CALL related structures and data
           .include "struct.S"     # Structure definition macro assists
           .include "SYSIB.S"      # System information block structures and data
           .list
           .eject

  # halfunc - Selects the 32-bit function entry prolog

           .macro halfunc name:req
    .if .Lhal_s390_only
           function \name
    .else
           func370 \name
    .endif
           .endm

  # halpush - Selects the 32-bit function push prolog

           .macro halpush
    .if .Lhal_s390_only
           push
    .else
           push370
    .endif
           .endm

  # pgmend - Establish the end of the program using a symbol
  #
  # Macro Parameters
  #   name     Symbol defining the end of the program (required)
  #   sub      Highest .text subsection used in the assembly (default 0)

           .macro pgmend name:req sub=0
           .pushsection ".text",\sub
\name:
           .endm

  # pgmreset - Re-establish the previous new program interrupt PSW as the active one
  #
  # Macro Parameters
  #   pswsave  Symbol identifying where to save the previously active new program 
  #            PSW had been saved (default .Lsv_npgm)
  #   br       Macro base register (default 13)
  #   b        Macro base (default 0b)

           .macro ioreset pswsave=.Lsv_nio br=13 b=0b
           mvc    .LPSW_newio(8,0),\pswsave-\b(\br)
           .endm

           .macro pgmreset pswsave=.Lsv_npgm br=13 b=0b
           mvc    .LPSW_newpgm(8,0),\pswsave-\b(\br)   # Restore the saved PSW
.Lhal_plat_common_inc = 1
           .endm

  # pgmresetx - Re-establish the previous new program interrupt PSW as the active one
  #
  # Macro Parameters
  #   pswsave  Symbol identifying where to save the previously active new program 
  #            PSW had been saved (default .Lsv_npgm)
  #   br       Macro base register (default 13)
  #   b        Macro base (default 0b)

           .macro ioresetx pswsave=.Lsv_niox br=13 b=0b
           mvc    .LPSW_newiog(8,0),\pswsave-\b(\br)
           .endm

           .macro pgmresetx pswsave=.Lsv_npgmx br=13 b=0b
           mvc    .LPSW_newpgmg(8,0),\pswsave-\b(\br)   # Restore the saved PSW
.Lhal_plat_common_inc = 1
           .endm

  # pgmtrans - Transfer control to a location on a program interrupt (32-bit)
  #
  # Macro Parameters
  #   to       Symbol to which control will pass upon a program interrupt (required)
  #   pswsave  Symbol identifying where to save the current new program PSW
  #            (default .Lsv_npgm)
  #   wrkr     Macro work register (default 0)
  #   br       Macro base register (default 13)
  #   b        Macro base (default 0b)

           .macro pgmtrans to:req pswsave=.Lsv_npgm wrkr=0 br=13 b=0b
           la     \wrkr,\to-\b(\br)          # Locate to where control will transfer
           st     \wrkr,.Lck_pgm+4-\b(\br)   # Set the location in the PSW
           mvc    \pswsave-\b(8,\br),.LPSW_newpgm(0)   # Save the current PSW
           mvc    .LPSW_newpgm(8,0),.Lck_pgm-\b(\br)   # Set the new PSW
.Lhal_plat_common_inc = 1
           .endm

  # pgmtransx - Transfer control to a location on a program interrupt (64-bit)
  #
  # Macro Parameters
  #   to       Symbol to which control will pass upon a program interrupt (required)
  #   pswsave  Symbol identifying where to save the current new program PSW
  #            (default .Lsv_npgm)
  #   wrkr     Macro work register (default 0)
  #   br       Macro base register (default 13)
  #   b        Macro base (default 0b)

           .macro pgmtransx to:req pswsave=.Lsv_npgmx wrkr=0 br=13 b=0b
           la     \wrkr,\to-\b(\br)          # Locate to where control will transfer
           stg    \wrkr,.Lck_pgmx+8-\b(\br)  # Set the location in the PSW
           mvc    \pswsave-\b(16,\br),.LPSW_newpgmg(0)   # Save the current PSW
           mvc    .LPSW_newpgmg(16,0),.Lck_pgmx-\b(\br)  # Set the new PSW
.Lhal_plat_common_inc = 1
           .endm

.Lhal_ck_cdrom_inc = 0
.Lhal_ck_D8_inc = 0
.Lhal_ck_herc_inc = 0
.Lhal_ck_for_z_inc = 0
.Lhal_ck_ioarch_inc = 0
.Lhal_ck_ipl_ccws_inc = 0
.Lhal_ck_plat_inc = 0
.Lhal_ck_plat_herc_inc = 0
.Lhal_ck_plat_vm_inc = 0
.Lhal_ck_vm_inc = 0
.Lhal_det_cons_device_id_inc = 0
.Lhal_det_cons_inc = 0
.Lhal_det_devids_s370_inc = 0
.Lhal_det_stg_s370_inc = 0
.Lhal_det_stg_s390_inc = 0
.Lhal_init_ieib_inc = 0
.Lhal_init_ihcb_inc = 0
.Lhal_plat_common_inc = 0
.Lhal_use_d24_for_console = 0

.ifndef .Lhal_s390_only
.Lhal_s390_only = 0
.endif

 # Include subroutines required by s370 basic control mode
.if .Lhal_s370bc
.if .Lhal_s390_only
       .warning "'halfeat s390=yes' forced to 'no' due to S/370 BC mode support"
.Lhal_s390_only = 0
.endif
.Lhal_32bit = 1
.if .Lhal_herc
.Lhal_ck_herc_inc = 1    # Only include Hercules platform if enabled by hal macro
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_ck_ioarch_inc = 1
.Lhal_ck_ipl_ccws_inc = 1
.if .Lhal_vm             # Only include vm platform if enabled by hal macro
.Lhal_ck_vm_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_det_cons_inc = 1
.Lhal_det_devids_s370_inc = 1
.Lhal_det_stg_s370_inc = 1
.Lhal_init_ieib_inc = 1
.Lhal_init_ihcb_inc = 1
.endif

 # Include subroutines required by s370 extended control mode
.if .Lhal_s370
.if .Lhal_s390_only
       .warning "'halfeat s390=yes' forced to 'no' due to S/370 EC mode support"
.Lhal_s390_only = 0
.endif
.Lhal_32bit = 1
.if .Lhal_herc           # Only include Hercules platform if enabled by hal macro
.Lhal_ck_herc_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_ck_ioarch_inc = 1
.Lhal_ck_ipl_ccws_inc = 1
.if .Lhal_vm             # Only include vm platform if enabled by hal macro
.Lhal_ck_vm_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_det_cons_inc = 1
.Lhal_det_devids_s370_inc = 1
.Lhal_det_stg_s370_inc = 1
.Lhal_init_ieib_inc = 1
.Lhal_init_ihcb_inc = 1
.endif

 # Include subroutines required by s390
.if .Lhal_s390
.Lhal_32bit = 1
.Lhal_init_ieib_inc = 1
.Lhal_init_ihcb_inc = 1
.Lhal_ck_cdrom_inc = 1
.Lhal_ck_for_z_inc = 1
.Lhal_ck_ioarch_inc = 1
.Lhal_ck_ipl_ccws_inc = 1
.if .Lhal_vm
.Lhal_ck_plat_vm_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.if .Lhal_herc
.Lhal_ck_plat_herc_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_det_cons_device_id_inc = 1
.Lhal_det_cons_inc = 1
.Lhal_det_stg_s390_inc = 1
.endif # .if .Lhal_s390

 # Include subroutines required by s390x
.if .Lhal_s390x
.Lhal_64bit = 1
.Lhal_init_ieib_inc = 1
.Lhal_init_ihcb_inc = 1
.Lhal_ck_cdrom_inc = 1
.Lhal_ck_ioarch_inc = 1
.Lhal_ck_ipl_ccws_inc = 1
.if .Lhal_vm
.Lhal_ck_plat_vm_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.if .Lhal_herc
.Lhal_ck_plat_herc_inc = 1
.Lhal_ck_D8_inc = 1
.Lhal_use_d24_for_console = 1
.endif
.Lhal_det_cons_device_id_inc = 1
.Lhal_det_cons_inc = 1
.endif

.if 0  # Change the 0 to 1 to see these messages during assembly
.if .Lhal_s370bc
.print "HAL - s370 BC  - enabled"
.else
.print "HAL - s370 BC  - disabled"
.endif

.if .Lhal_s370
.print "HAL - s370 EC  - enabled"
.else
.print "HAL - s370 EC  - disabled"
.endif

.if .Lhal_s390
.print "HAL - s390     - enabled"
.else
.print "HAL - s390     - disabled"
.endif

.if .Lhal_s390x
.print "HAL - s390x    - enabled"
.else
.print "HAL - s390x    - disabled"
.endif

.if .Lhal_vm
.print "HAL - vm       - enabled"
.else
.print "HAL - vm       - disabled"
.endif

.if .Lhal_herc
.print "HAL - Hercules - enabled"
.else
.print "HAL - Hercules - disabled"
.endif
.endif

            .eject
            .sbttl "Hardware Abstraction Layer - Architecture Support Blocks"
  # +-------------------------------+
  # |  Architecture Support Blocks  |
  # +-------------------------------+

.if .Lhal_32bit
         asbdefn
.endif # .if .Lhal_32bit
.if .Lhal_64bit
         asbdefng
.endif # .if .Lhal_64bit

            .eject
            .sbttl "Hardware Abstraction Layer - Platform Initialization"
  # +--------------------------------------------------+
  # |  Disabled Architecture Initialization attempted  |
  # +--------------------------------------------------+

.Lhal_init_disabled = 0

.ifeq .Lhal_s370bc
            .align 2
.Lhal_init_s370bc:
.Lhal_init_disabled = 1
.endif

.ifeq .Lhal_s370
            .align 2
.Lhal_init_s370:
.Lhal_init_disabled = 1
.endif

.ifeq .Lhal_s390
            .align 2
.Lhal_init_s390:
.Lhal_init_disabled = 1
.endif

.ifeq .Lhal_s390x
            .align 2
.Lhal_init_s390x:
.Lhal_init_disabled = 1
.endif

.if .Lhal_init_disabled
            halabort error=0x0009
.endif # .if .Lhal_init_disabled scope


.if .Lhal_s370bc
  # +---------------------------------------------------------+
  # |  System/370 Basic Control Mode Initialization Function  |
  # +---------------------------------------------------------+

  # On entry:
  #    R2     DIAGNOSE X'08' test message address
  #    R3     DIAGNOSE X'08' test message length
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            func370 .Lhal_init_s370bc
            push370

            bas    11,.Lhal_init_ieib-0b(13)            # Initialize IEIB
            mvc    .LIEIB_ipl+2(2,0),.Ls370bcipl(0)     # Set IPL device address
            ni     .Lck_pgm+1-0b(13),0xFF-0x04          # Stay in BC mode

.if .Lhal_tt
            # Set up translate table addresses in IEIB
            mvc    .LIEIB_a2eg(16,0),.Lhal_translate_tables-0b(13)
.endif # .if .Lhal_tt scope

.if .Lhal_ck_vm_inc
            bas    11,.Lhal_ck_vm-0b(13)            # Check if running under VM
.endif # .if .Lhal_ck_vm_inc scope  

.if .Lhal_ck_D8_inc
            bas    11,.Lhal_ck_D8-0b(13)            # Check for DIAGNOSE X'08'
.endif # .if .Lhal_ck_D8_inc scope

.if .Lhal_ck_herc_inc
            bas    11,.Lhal_ck_herc-0b(13)          # Check for Hercules
.endif # .if .Lhal_ck_herc_inc scope

.if .Lhal_det_stg_s370_inc
            bas    11,.Lhal_det_stg_s370-0b(13)     # Determine main storage size
.endif # .if .Lhal_det_stg_s370_inc scope

.if .Lhal_ck_ioarch_inc
            bas    11,.Lhal_ck_ioarch-0b(13)        # Determine I/O arch from IPL dev.
            tm     .LIEIB_plt(0),.LIEIB_chan        # Channel I/O found?
            bo     .+8-0b(13)                       # ..Yes, good to go.
            halabort error=0x0001                   # Unsupported I/O architecture
.endif # .if .Lhal_ck_ioarch_inc scope

.if .Lhal_ck_ipl_ccws_inc
            bas    11,.Lhal_ck_ipl_ccws-0b(13)      # Detect IPL device type
.endif # .if .Lhal_ck_ipl_ccws_inc

.if .Lhal_det_cons_inc
            bas    11,.Lhal_det_cons-0b(13)         # Determine console device number
.endif # .if .Lhal_det_cons_inc

.if .Lhal_det_devids_s370_inc
            bal    11,.Lhal_det_devids_s370-0b(13)  # Determine device ids and nums
.endif # .if .Lhal_det_devids_s370_inc scope

            mvc    .LIEIB_asb(4,0),.Lhal_init_s370bc_asb-0b(13) # ASB addr to IEIB

.if .Lhal_init_ihcb_inc
            bas    11,.Lhal_init_ihcb-0b(13)        # Clear IHCB area, set active sa
.endif

            return                                  # Return to caller


  # +--------------------------------------+
  # |  System/370 Identification Function  |
  # +--------------------------------------+ 
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            func370 .Lhal_id_s370bc
            push370

            la     10,.Lhal_id_s370bc_rtn-0b(13) # Locate the S/370 BC routine
            basr   11,10                         # S/370 BC running

            return

  # +------------------------------------------------+
  # |  System/370 BC IEIB initialization Subroutine  |
  # +------------------------------------------------+ 
  # Access: private

  # On entry:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # Used: none
  # On exit: none

.Lhal_id_s370bc_rtn:
0:
            mvc    .LIEIB_asb(4,0),.Lhal_init_s370bc_asb-0b(10) # ASB addr to IEIB
            mvc    .LIEIB_avl(2,0),.Lhal_ib_s370bc-0b(10) # Indicate available
            tm     .LIEIB_plt(0),.LIEIB_Herc|.LIEIB_VM  # Herc or VM?
            bnzr   11                             # ..yes, return
            oi     .LIEIB_plt(0),.LIEIB_phys      # ..no, must be physical
            br     11                             # Return to caller

            .align 4
.Lhal_init_s370bc_asb:
            .long  .Lioal_s370bc_asb

 # IEIB Architecture Default Fields  
 #                     .LIEIB_run,   .LIEIB_avl            
.Lhal_ib_s370bc:.byte  .LIEIB_s370bc,.LIEIB_s370|.LIEIB_s370bc

.endif # .if .Lhal_s370bc scope

.if .Lhal_s370
  # +------------------------------------------------------------+
  # |  System/370 Extended Control Mode Initialization Function  |
  # +------------------------------------------------------------+

  # On entry:
  #    R2     DIAGNOSE X'08' test message address
  #    R3     DIAGNOSE X'08' test message length
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None
            func370 .Lhal_init_s370
            push370

            bas    11,.Lhal_init_ieib-0b(13)          # Initialize IEIB
            mvc    .LIEIB_ipl(4,0),.LIO_ssid(0)       # Set IPL device address

.if .Lhal_tt
            # Set up translate table addresses in IEIB
            mvc    .LIEIB_a2eg(16,0),.Lhal_translate_tables-0b(13)
.endif # .if .Lhal_tt scope

.if .Lhal_ck_vm_inc
            bas    11,.Lhal_ck_vm-0b(13)          # Check if running under VM
.endif # .if .Lhal_ck_vm_inc scope

.if .Lhal_ck_D8_inc
            bas    11,.Lhal_ck_D8-0b(13)          # Check for DIAGNOSE X'08'
.endif # .if .Lhal_ck_D8_inc scope

.if .Lhal_ck_herc_inc
            bas    11,.Lhal_ck_herc-0b(13)        # Check for Hercules
.endif # .if .Lhal_ck_herc_inc scope

.if .Lhal_det_stg_s370_inc
            bas    11,.Lhal_det_stg_s370-0b(13)   # Determine main storage size
.endif # .if .Lhal_det_stg_s370_inc scope

.if .Lhal_ck_ioarch_inc
            bas    11,.Lhal_ck_ioarch-0b(13)      # Determine I/O arch from IPL dev.
            tm     .LIEIB_plt(0),.LIEIB_chan      # Channel I/O found?
            bo     .+8-0b(13)                     # ..Yes, good to go.
            halabort error=0x0001   # Unsupported I/O architecture
.endif # .if .Lhal_ck_ioarch_inc scope

.if .Lhal_ck_ipl_ccws_inc
            bas    11,.Lhal_ck_ipl_ccws-0b(13)    # Detect IPL device type
.endif # .if .Lhal_ck_ipl_ccws_inc scope

.if .Lhal_det_cons_inc
            bas    11,.Lhal_det_cons-0b(13)       # Determine console device number
.endif # .if .Lhal_det_cons_inc scope

.if .Lhal_det_devids_s370_inc
            bal    11,.Lhal_det_devids_s370-0b(13)# Determine device ids and nums
.endif # .if .Lhal_det_devids_s370_inc scope

            la     10,.Lhal_id_s370_rtn-0b(13)    # Locate the s370 routine
            basr   11,10                          # S/370 running

.if .Lhal_init_ihcb_inc
            bas    11,.Lhal_init_ihcb-0b(13)      # Clear IHCB area, set active sa
.endif

            return

  # +--------------------------------------+
  # |  System/370 Identification Function  |
  # +--------------------------------------+ 
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            func370 .Lhal_id_s370
            push370

            la     10,.Lhal_id_s370_rtn-0b(13)   # Locate the ESA/390 routine
            basr   11,10                         # ESA/390 running

            return

  # +---------------------------------------------+
  # |  System/370 IEIB initialization Subroutine  |
  # +---------------------------------------------+ 
  # Access: private

  # On entry:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # Used: none
  # On exit: none

.Lhal_id_s370_rtn:
0:
            mvc    .LIEIB_asb(4,0),.Lhal_init_s370_asb-0b(10) # ASB addr to IEIB
            mvc    .LIEIB_run(2,0),.Lhal_ib_s370ec-0b(10) # Indicate available
            tm     .LIEIB_plt(0),.LIEIB_Herc|.LIEIB_VM  # Herc or VM?
            bnzr   11                             # ..yes, return
            oi     .LIEIB_plt(0),.LIEIB_phys      # ..no, must be physical
            br     11                             # Return to caller

            .align 4
.Lhal_init_s370_asb:
            .long  .Lioal_s370_asb

 # IEIB Architecture Default Fields  
 #                     .LIEIB_run,   .LIEIB_avl
.Lhal_ib_s370ec:.byte  .LIEIB_s370,  .LIEIB_s370|.LIEIB_s370bc

.endif # .if .Lhal_s370 scope

.if .Lhal_s390
  # +-----------------------------------+
  # |  ESA/390 Initialization Function  |
  # +-----------------------------------+ 

  # On entry:
  #    R2     DIAGNOSE X'08' test message address
  #    R3     DIAGNOSE X'08' test message length
  #    R4     SCCB 4K page address
  #    R5     SYSIB 4K page address
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            halfunc .Lhal_init_s390

 # Local stack frame usage
.if .Lhal_det_cons_device_id_inc
            fbytes  .Lhal_init_s390_schib,.LSCHIB_len
.endif # .if .Lhal_det_cons_device_id_inc scope

            halpush

            bas    11,.Lhal_init_ieib-0b(13)          # Initialize the IEIB
            mvc    .LIEIB_ipl(4,0),.LIO_ssid(0)       # Set IPL device subsystem id

.if .Lhal_tt
            # Set up translate table addresses in IEIB
            mvc    .LIEIB_a2eg(16,0),.Lhal_translate_tables-0b(13)
.endif # .if .Lhal_tt scope

.if .Lhal_ck_D8_inc
            # Need to do this here because R2 gets used
            ltr    2,2                            # Is there a test message?
            bz     .Lhal_init_s390_noD8-0b(13)    # ..No, use default message
            st     2,.Lhal_D8_parms-0b(13)        # Set the test message address...
            st     3,.Lhal_D8_parms+8-0b(13)      # ...and now the message length
.Lhal_init_s390_noD8:
.endif # .if .Lhal_ck_D8_inc

.if .Lhal_det_stg_s390_inc
            st     4,.Lhal_sccb-0b(13)            # Set up for .Lhal_det_stg_s390
.endif # .if .Lhal_det_stg_s390_inc scope

.if .Lhal_ck_plat_herc_inc
            st     5,.Lhal_sysib-0b(13)           # Save SYS111 page address
.endif # .if .Lhal_ck_plat_herc_inc scope

.if .Lhal_ck_plat_vm_inc
            bas    11,.Lhal_ck_plat_vm-0b(13)     # Check if running in a VM
.endif # .if .Lhal_ck_plat_vm_inc

.if .Lhal_ck_plat_herc_inc
            bas    11,.Lhal_ck_plat_herc-0b(13)   # Check for Hercules
.endif # .if .Lhal_ck_plat_inc

.if .Lhal_ck_D8_inc
            bas    11,.Lhal_ck_D8-0b(13)          # Check for DIAGNOSE X'08'
.endif # .if .Lhal_ck_D8_inc

.if .Lhal_ck_for_z_inc
            bas    11,.Lhal_ck_for_z-0b(13)       # Check for z/Architecture
.else
            stfl   0(0)                           # Save facility list anyway
.endif # .if .Lhal_ck_for_z_inc scope

.if .Lhal_det_stg_s390_inc
            bas    11,.Lhal_det_stg_s390-0b(13)   # Determine main storage size
.endif # .if .Lhal_det_stg_s390_inc scope

.if .Lhal_ck_cdrom_inc
            bas    11,.Lhal_ck_cdrom-0b(13)       # Determine if CDROM IPL
.endif # .if .Lhal_ck_cdrom_inc scope

.if .Lhal_ck_ioarch_inc
            bas    11,.Lhal_ck_ioarch-0b(13)      # Determine I/O arch from IPL dev.
            tm     .LIEIB_plt(0),.LIEIB_sch       # Subsystem I/O found?
            bo     .+8-0b(13)                     # ..Yes, good to go.
            halabort error=0x0001   # Unsupported I/O architecture detected
.endif # .if .Lhal_ck_ioarch_inc scope

.if .Lhal_ck_ipl_ccws_inc
            bas    11,.Lhal_ck_ipl_ccws-0b(13)    # Detect IPL device type
.endif # .if .Lhal_ck_ipl_ccws_inc

.if .Lhal_det_cons_inc
            bas    11,.Lhal_det_cons-0b(13)       # Determine console device number
.endif

.if .Lhal_det_cons_device_id_inc
            la     7,.Lhal_init_s390_schib(15)    # Locate SCHIB area
            # Scan for console device id and IPL device number
            bas    11,.Lhal_det_cons_device_id-0b(13)
.endif

            la     10,.Lhal_id_s390_rtn-0b(13)    # Locate ESA/390 routine
            basr   11,10                          # Set ESA/390 running

.if .Lhal_init_ihcb_inc
            bas    11,.Lhal_init_ihcb-0b(13)      # Clear IHCB, set active sa
.endif

            return

  # +-----------------------------------+
  # |  ESA/390 Identification Function  |
  # +-----------------------------------+ 
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            halfunc .Lhal_id_s390
            halpush

            la     10,.Lhal_id_s390_rtn-0b(13)   # Locate the ESA/390 routine
            basr   11,10                         # ESA/390 running

            return

  # +------------------------------------------+
  # |  ESA/390 IEIB initialization Subroutine  |
  # +------------------------------------------+ 
  # Access: private

  # On entry:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # Used:
  #    R3     To establish Architecture Support Block
  #
  # On exit: none

.Lhal_id_s390_rtn:
0:
            l      3,.Lhal_init_s390_asb-0b(10)   # Locate the ESA/390 ASB
            st     3,.LIEIB_asb(0)                # Put it in the IEIB
            mvi    .LIEIB_run(0),.LIEIB_s390      # ESA/390 is running
            oc     .LIEIB_avl(1,0),.Lhal_ib_s390+1-0b(10) # Indicate available
            tm     .LIEIB_plt(0),.LIEIB_Herc      # Running on Hercules?
            jno    .Lhal_id_s390_rtn_phys         # ..No, see if hardware
            oi     .LIEIB_avl(0),.LIEIB_s370|.LIEIB_s370bc # S/370 also available

.Lhal_id_s390_rtn_phys:
            tm     .LIEIB_plt(0),.LIEIB_Herc|.LIEIB_VM  # Herc or VM?
            bnzr   11                             # ..yes, return
            oi     .LIEIB_plt(0),.LIEIB_phys      # ..no, must be physical
            br     11                             # Return to caller

            .align 4
.Lhal_init_s390_asb:
            .long  .Lioal_s390_asb

 # IEIB Architecture Default Fields  
 #                     .LIEIB_run,   .LIEIB_avl
.Lhal_ib_s390:  .byte  .LIEIB_s390,  .LIEIB_s390

.endif # .if .Lhal_s390 scope

.if .Lhal_s390x
  # +------------------------------------------+
  # |  z/Architecture Initialization Function  |
  # +------------------------------------------+     

  # On entry:
  #    R2     DIAGNOSE X'08' test message address
  #    R3     DIAGNOSE X'08' test message length
  #    R4     SCCB 4K page address
  #    R5     SYSIB 4K page address
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            functionx .Lhal_init_s390x

 # Local stack frame usage

.if .Lhal_det_cons_device_id_inc
            fbytes  .Lhal_init_s390x_schib,.LSCHIB_len
.endif # .if .Lhal_det_cons_device_id_inc scope

            pushx

            bas    11,.Lhal_init_ieib-0b(13)          # Initialize the IEIB
            mvc    .LIEIB_ipl(4,0),.LIO_ssid(0)       # Set IPL device subsystem id

.if .Lhal_tt
            # Set up translate table addresses in IEIB
            mvc    .LIEIB_a2eg(16,0),.Lhal_translate_tables-0b(13)
.endif # .if .Lhal_tt scope

.if .Lhal_ck_D8_inc
            # Need to do this here because R2 gets used
            ltgr   2,2                            # Is there a test message?
            bz     .Lhal_init_s390_64_noD8-0b(13) # ..No, use default message
            stg    2,.Lhal_D8_parms_64-0b(13)     # Set the test message address...
            stg    3,.Lhal_D8_parms_64+16-0b(13)  # ...and now the message length
.Lhal_init_s390_64_noD8:
.endif # .if .Lhal_ck_D8_inc scope

.if .Lhal_det_stg_s390_inc
            st     4,.Lhal_sccb-0b(13)            # Set up for .Lhal_det_stg_s390
.endif # .if .Lhal_det_stg_s390_inc scope

.if .Lhal_ck_plat_herc_inc
            stg     5,.Lhal_sysibg-0b(13)         # Save SYS111 page address
.endif # .if .Lhal_ck_plat_herc_inc scope

.if .Lhal_ck_plat_vm_inc
            bas    11,.Lhal_ck_plat_vm-0b(13)     # Check if running in a VM
.endif # .if .Lhal_ck_plat_vm_inc

.if .Lhal_ck_plat_herc_inc
            bas    11,.Lhal_ck_plat_hercx-0b(13)  # Check for Hercules
.endif # .if .Lhal_ck_plat_herc_inc

.if .Lhal_ck_D8_inc
            bas    11,.Lhal_ck_D8_64-0b(13)       # Check for DIAGNOSE X'8'
.endif # .if .Lhal_ck_D8_inc

            stfl   0(0)                           # Store the facility list

.if .Lhal_det_stg_s390_inc
            bas    11,.Lhal_det_stg_s390x-0b(13)  # Determine main storage size
.endif # .if .Lhal_det_stg_s390_inc scope

.if .Lhal_ck_cdrom_inc
            bas    11,.Lhal_ck_cdrom-0b(13)       # Determine if CDROM IPL
.endif # .if .Lhal_ck_cdrom_inc scope

.if .Lhal_ck_ioarch_inc
            bas    11,.Lhal_ck_ioarch-0b(13)      # Determine I/O arch from IPL dev.
            tm     .LIEIB_plt(0),.LIEIB_sch       # Subsystem I/O found?
            bo     .+8-0b(13)                     # ..Yes, good to go.
            halabort error=0x0001   # Unsupported I/O architecture detected
.endif # .if .Lhal_ck_ioarch_inc scope

.if .Lhal_ck_ipl_ccws_inc
            bas    11,.Lhal_ck_ipl_ccws-0b(13)    # Detect IPL device type
.endif # .if .Lhal_ck_ipl_ccws_inc

.if .Lhal_det_cons_inc
            bas    11,.Lhal_det_cons-0b(13)       # Determine console device number
.endif

.if .Lhal_det_cons_device_id_inc
            la     7,.Lhal_init_s390x_schib(15)    # Locate SCHIB area
            # Scan for console device id and IPL device number
            bas    11,.Lhal_det_cons_device_id-0b(13)
.endif

            larl   10,.Lhal_id_s390x_rtn          # Locate the z/Architecture rtn
            basr   11,10

.if .Lhal_init_ihcb_inc
            bas    11,.Lhal_init_ihcb-0b(13)      # Clear IHCB, set active sa
.endif

            returnx

  # +------------------------------------------+
  # |  z/Architecture Identification Function  |
  # +------------------------------------------+ 
  # Access: public

  # On entry:
  #    R13    Function base address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # On exit: None

            functionx .Lhal_id_s390x
            pushx

            larl   10,.Lhal_id_s390x_rtn         # Locate z/Architecture routine
            basr   11,10                         # z/Architecture running

            returnx

  # +-------------------------------------------------+
  # |  z/Architecture IEIB initialization Subroutine  |
  # +-------------------------------------------------+ 
  # Access: private

  # On entry:
  #    R10    Subroutine base address
  #    R11    Subroutine return address
  #
  # Used:
  #    R3     To establish Architecture Support Block
  #
  # On exit: none

.Lhal_id_s390x_rtn:
0:
            larl   3,.Lioal_s390x_asb             # Locate the 64-bit ASB
            stg    3,.LIEIB_asbg(0)               # Put it in the IEIB
            mvi    .LIEIB_run(0),.LIEIB_s390x     # z/Architecture is running
            oc     .LIEIB_avl(1,0),.Lhal_ib_s390x+1-0b(10) # Indicate available
            tm     .LIEIB_plt(0),.LIEIB_Herc      # Running on Hercules?
            jno    .Lhal_id_s390x_rtn_phys        # ..No, see if a hardware
            oi     .LIEIB_avl(0),.LIEIB_s370|.LIEIB_s370bc # S/370 also available

.Lhal_id_s390x_rtn_phys:
            tm     .LIEIB_plt(0),.LIEIB_Herc|.LIEIB_VM  # Herc or VM?
            bnzr   11                             # ..yes, return
            oi     .LIEIB_plt(0),.LIEIB_phys      # ..no, must be physical
            br     11                             # Return to caller

 # IEIB Architecture Default Fields  
 #                     .LIEIB_run,   .LIEIB_avl
.Lhal_ib_s390x: .byte  .LIEIB_s390x, .LIEIB_s390|.LIEIB_s390x

.endif # .if .Lhal_s390x scope

.if .Lhal_ck_cdrom_inc
  # +-------------------------------+
  # |  Detect CDROM IPL Subroutine  |
  # +-------------------------------+           

            .align 2
.Lhal_ck_cdrom:
            oc    .LIEIB_ipl(4,0),.LIEIB_ipl(0)   # Is the IPL device zeros?
            bnzr  11                              # ..No, then CDROM not used
            oi    .LIEIB_dtyp,.LIEIB_CDROM        # ..Yes, CDROM
            br    11                              # Now return

.endif # .if .Lhal_ck_cdrom_inc

.if .Lhal_ck_D8_inc
.if .Lhal_32bit
  # +-------------------------------------------------------------+
  # |  32-bit Detection of DIAGNOSE X'08' availability Subroutine |
  # +-------------------------------------------------------------+

            .align 2
.Lhal_ck_D8:
            basr    10,0
0:
            lm      2,5,.Lhal_D8_parms-0b(10) # Load parameters for DIAGNOSE X'8'
            pgmtrans to=.Lhal_noD8,br=10
            diag    2,4,0x8            # Issue command containing the message
            oi      .LIEIB_plt(0),.LIEIB_D8   # Indicate DIAGNOSE 8 is available
            ltr     4,4                # Did an error occur?
            bz      .Lhal_noD8-0b(10)  # ..No, return then after resetting trap
            halabort error=0x0002      # ..Yes, abort DIAGNOSE X'08' failure
.Lhal_noD8:
            pgmreset br=10
            bzr     11                 # ..No, return

            .align  4
.Lhal_D8_parms:  
            .long   .Lhal_ck_D8_test   # Rx = command string address
            .long   0                  # Rx+1 = response buffer address
            .long   .Lhal_ck_d8_len    # Ry = command length and flags (no response)
            .long   0                  # Ry+1 = response buffer length

.endif # .if .Lhal_32bit scope

.if .Lhal_64bit
  # +-------------------------------------------------------------+
  # |  64-bit Detection of DIAGNOSE X'08' availability Subroutine |
  # +-------------------------------------------------------------+

            .align 2
.Lhal_ck_D8_64:
            basr    10,0
0:
            lmg     2,5,.Lhal_D8_parms_64-0b(10) # Load parameters for DIAGNOSE X'8'
            pgmtransx to=.Lhal_noD8_64,br=10
            diag    2,4,0x8            # Issue command containing the message
            oi      .LIEIB_plt(0),.LIEIB_D8   # Indicate DIAGNOSE 8 is available
            ltgr    4,4                # Did an error occur?
            bz      .Lhal_noD8_64-0b(10)  # ..No, return then after resetting trap
            halabort error=0x0002      # ..Yes, abort DIAGNOSE X'08' failure

.Lhal_noD8_64:
            pgmresetx br=10
            bzr     11                 # ..No, return

            .align  4
.Lhal_D8_parms_64:  
            .quad   .Lhal_ck_D8_test   # Rx = command string address
            .quad   0                  # Rx+1 = response buffer address
            .quad   .Lhal_ck_d8_len    # Ry = command length and flags (no response)
            .quad   0                  # Ry+1 = response buffer length

.endif # .if .Lhal_64bit scope

.Lhal_ck_D8_test:
             # EBCDIC   M   S   G   N   O   H       *
            .ascii  "\xD4\xE2\xC7\xD5\xD6\xC8\x40\x5C\x40"
             # EBCDIC   D   I   A   G   N   O   S   E     
            .ascii  "\xC4\xC9\xC1\xC7\xD5\xD6\xE2\xC5\x40"
             # EBCDIC   X   '   0   8   '
            .ascii  "\xE7\x7D\xF0\xF8\x7D\x40"
             # EBCDIC   a   v   a   i   l   a   b   l   e
            .ascii  "\x81\xA5\x81\x89\x93\x81\x82\x93\x85"
.Lhal_ck_d8_len = .-.Lhal_ck_D8_test

.endif # .if .Lhal_ck_D8_inc scope

.if .Lhal_ck_for_z_inc
  # +----------------------------------------------------+
  # |  Detect if z/Architecture is available Subroutine  |
  # +----------------------------------------------------+           

            .align 2
.Lhal_ck_for_z:
            stfl   0(0)                            # Store the facility list
            tm     .Lstfl(0),.Lstflzins            # Is z/Architecture installed?
            bnor   11                              # ..No, just return
            oi     .LIEIB_avl(0),.LIEIB_s390x      # ..Yes, indicate that in IEIB
            br     11                              # Now, return

.endif # .if .Lhal_ck_for_z_inc scope

.if .Lhal_ck_herc_inc
  # +------------------------------------+
  # |  Detect S/370 Hercules Subroutine  |
  # +------------------------------------+           

            .align 2
.Lhal_ck_herc:
            basr    10,0
0:
            tm      .LIEIB_plt(0),.LIEIB_VM   # Running on VM?
            bor     11                        # ..Yes, not running on Hercules
            tm      .LIEIB_plt(0),.LIEIB_D8   # ..No, but is D8 available?      
            bo      .Lhal_is_herc-0b(10)      # ..Yes, then must be Hercules
            tm      .LIEIB_plt(0),.LIEIB_s390 # Is ESA/390 or higher available?
            bnor    11                        # ..No, can't detect Hercules
   # Use STSI to see if manufacturer is Hercules - last resort for detection
.Lhal_is_herc:
            oi      .LIEIB_plt(0),.LIEIB_Herc # ..Yes, so we are on Hercules
            br      11

.endif # .if .Lhal_ck_herc_inc

.if .Lhal_ck_ioarch_inc
  # +--------------------------------------+
  # |  Detect I/O architecture Subroutine  |
  # +--------------------------------------+   

            .align 2
.Lhal_ck_ioarch:
            basr  10,0
0:
            tm    .LIEIB_dtyp(0),.LIEIB_CDROM     # Is CDROM in use?
            bo    .Lhal_deft_io-0b(10)            # ..Yes, can't use IPL device
            tm    .LIEIB_ipl+1(0),0x01            # Is IPL device a subystem ID?
            bno   .Lhal_is_chan-0b(10)            # Yes, channel subsystem in use
.Lhal_is_sch:
            oi    .LIEIB_plt(0),.LIEIB_sch        # No, set channel subsystem in IEIB
            br    11                              # Return

.Lhal_is_chan:
            oi    .LIEIB_plt(0),.LIEIB_chan       # Set channels in IEIB
            br    11                              # Return

.Lhal_deft_io:
            # Use the default I/O architecture for the CPU architecture
            tm     .LIEIB_run(0),.LIEIB_s390|.LIEIB_s390x # Subsystem I/O default?
            bnz    .Lhal_is_sch-0b(10)            # ..Yes, indicate subsystem
            b      .Lhal_is_chan-0b(10)           # ..No, must be channels

.endif # .if .Lhal_ck_ioarch_inc scope

.if .Lhal_ck_ipl_ccws_inc
  # +--------------------------------------------------------+
  # |  Detect IPL device type from SATK IPL channel program  |
  # +--------------------------------------------------------+

  # The first two CCW's in the chain built by the SATK IPL Medium Preparation 
  # Processor can reliably detect IPL device type.  Note: this logic may not
  # detect the device type correctly if the SATK is not used for building the
  # IPL medium.
  #
  # CKD device  - CCW device order for IPLCCW1 is READ DATA (0x06)
  # Tape device - The first READ CCW (0x02) is not followed by a 
  #               TRANSFER IN CHANNEL (0x08)
  # FBA devine  - The first READ (0x02) is for 512 bytes
  # Card reader - The first READ (0x02) if for 80 bytes

           .align  2
.Lhal_ck_ipl_ccws:
           basr    10,0
0:
           cli     .LIEIB_dtyp(0),0x00  # An IPL device already detected?
           bner    11                   # ..Yes, return
           
           cli     8(0),0x06        # Is this a READ DATA CCW?
           bne     .Lhal_ck_ipl_ccws_tape-0b(10)  # ..No, maybe tape
           oi      .LIEIB_dtyp(0),.LIEIB_CKD      # ..Yes, indicate a CKD device
           br      11               # Return to caller

.Lhal_ck_ipl_ccws_tape:
           cli    8(0),0x02         # Is the first IPL CCW an IPL READ?
           bner   11                # ..No, do not know what I am seeing, bail
           cli    16(0),0x08        # Is the second CCW a TIC?
           be     .Lhal_ck_ipl_ccws_fba-0b(10)   # ..No, can't be a tape then
           oi     .LIEIB_dtyp(0),.LIEIB_TAPE     # ..Yes, indicate a tape
           br     11                # Return to caller

.Lhal_ck_ipl_ccws_fba:
           # Is the count field of the READ CCW 512?
           clc    8+.LCCW0_cnt(2,0),.Lhal_ck_ipl_ccws_512-0b(10)
           bne    .Lhal_ck_ipl_ccws_card-0b(10)   # ..No, maybe a card reader
           oi     .LIEIB_dtyp(0),.LIEIB_FBA       # ..Yes, indicate a FBA device
           br     11                # Return to caller

.Lhal_ck_ipl_ccws_card:
           # Is the count fielf of the RED CCW 80?
           clc    8+.LCCW0_cnt(2,0),.Lhal_ck_ipl_ccws_80-0b(10)
           bner   11       # ..No, return to caller without detecting anything
           oi     .LIEIB_dtyp(0),.LIEIB_RDR   # ..Yes, indicate a card reader
           br     11               # Return to caller

.Lhal_ck_ipl_ccws_512:
           .hword 512      # Count field of the initial FBA channel program
.Lhal_ck_ipl_ccws_80:
           .hword 80       # Count fielf of the initial Card channel program

.endif # .if .Lhal_ck_ipl_ccws_inc


.if .Lhal_ck_plat_vm_inc
  # +---------------------------------------------------------------+
  # |  Detect ESA/390 or z/Architecture Virtual Machine Subroutine  |
  # +---------------------------------------------------------------+

           .align  2
.Lhal_ck_plat_vm:
           basr    10,0
0:
           # Use STSI to determine platform configuration level
           sr      0,0                   # Clear registers..
           lr      1,0                   # ..R0 through..
           lr      2,0                   # ..R2
           stsi    0(2)                  # Determine the current function level
           bz      .Lhal_plat_fc-0b(10)  # Successful
           halabort error=0x0003         # Failed to STORE SYSTEM INFORMATION

.Lhal_plat_fc:
           clm     0,0b1000,.Lsysibfcvm-0b(10)   # Running as a virtual machine?
           bne     .Lhal_plat_novm-0b(10)        # ..No, see if Hercules
           oi      .LIEIB_plt(0),.LIEIB_VM       # Indicate VM in IEIB
.Lhal_plat_novm:
           br      11                            # Return to caller

.Lsysibfcvm:.byte  0x30            # Function level of a virtual machine

.endif # .if .Lhal_ck_plat_vm_inc scope

.if .Lhal_ck_plat_herc_inc
.if .Lhal_32bit
  # +----------------------------------------------+
  # |  Detect ESA/390 Hercules Machine Subroutine  |
  # +----------------------------------------------+

             .align  2
.Lhal_ck_plat_herc:
           basr    10,0
0:
           tm      .LIEIB_plt(0),.LIEIB_VM    # Did we detect VM before?
           bor     11                         # ..Yes, return with VM as platform
     # Now get the SYSIB 1.1.1 data
           lm      0,1,.Lsysib111-0b(10)      # Set up parms for SYSIB 1.1.1
           l       2,.Lhal_sysib-0b(10)       # Point to SYSIB 1.1.1 data area
           stsi    0(2)                       # Save SYSIB 1.1.1
           bz      .Lhal_plat_man_ck-0b(10)   # If successfull, check man.
           halabort error=0x0003              # Failed to STORE SYSTEM INFORMATION
.Lhal_plat_man_ck:
           st      2,.LIEIB_sys(0)            # Save the address in the IEIB
           tm      .LIEIB_plt(0),.LIEIB_VM    # Did we detect VM before?
           bor     11                         # ..Yes, return with VM as platform
           # Otherwise, see if the manufactuer is Hercules default
           clc     .Lhercules_manufacturer-0b(16,10),.LSYSIB111_man(2)
           be      .Lhal_plat_herc-0b(10)      # ..No, see if plant is Herc
           # See if the plant is the Hercules default
           clc     .Lhercules_plant-0b(4,10),.LSYSIB111_plant
           bner    11                          # ..No, return
.Lhal_plat_herc:
           oi      .LIEIB_plt(0),.LIEIB_Herc   # Indicate Hercules in IEIB
           br      11                          # Return to caller

 # Parmeters for STORE SYSTEM INFORATION instruction to retrieve SYSIB 1.1.1
.Lhal_sysib: .long  0              # R2 = Address of the SYSIB data area

.endif # .if .Lhal_32bit scope

.if .Lhal_64bit
  # +-----------------------------------------------------+
  # |  Detect z/Architecture Hercules Machine Subroutine  |
  # +-----------------------------------------------------+

             .align  2
.Lhal_ck_plat_hercx:
           basr    10,0
0:
           tm      .LIEIB_plt(0),.LIEIB_VM    # Did we detect VM before?
           bor     11                         # ..Yes, return with VM as platform
     # Now get the SYSIB 1.1.1 data
           lm      0,1,.Lsysib111-0b(10)      # Set up parms for SYSIB 1.1.1
           lg      2,.Lhal_sysibg-0b(10)      # Point to SYSIB 1.1.1 data area
           stsi    0(2)                       # Save SYSIB 1.1.1
           bz      .Lhal_plat_man_ckx-0b(10)  # If successfull, check man.
           halabort error=0x0003              # Failed to STORE SYSTEM INFORMATION
.Lhal_plat_man_ckx:
           st      2,.LIEIB_sysg(0)           # Save the address in the IEIB
           # Otherwise, see if the manufactuer is Hercules default
           clc     .Lhercules_manufacturer-0b(16,10),.LSYSIB111_man(2)
           be      .Lhal_plat_hercx-0b(10)     # ..No, see if plant is Herc
           # See if the plant is the Hercules default
           clc     .Lhercules_plant-0b(4,10),.LSYSIB111_plant
           bner    11                          # ..No, return
.Lhal_plat_hercx:
           oi      .LIEIB_plt(0),.LIEIB_Herc   # Indicate Hercules in IEIB
           br      11                          # Return to caller

 # Parmeter for STORE SYSTEM INFORATION instruction to retrive SYSIB 1.1.1
.Lhal_sysibg:.quad  0               # R2 = Address of the SYSIB data area

.endif # .if .Lhal_64bit scope

 # Basic Machine STORE SYSTEM INFORMATION selector information (R0,R1)
.Lsysib111: .quad  .LSYSIB_1_1_1    # R0,R1 = Request Basic machine information
.Lhercules_manufacturer:
            # EBCDIC  H   R   C
            .ascii "\xC8\xD9\xC3\x40\x40\x40\x40\x40"
            .ascii "\x40\x40\x40\x40\x40\x40\x40\x40"

.Lhercules_plant:
            # EBCDIC  Z   Z
            .ascii "\xE9\xE9\x40\x40"

.endif # .if .Lhal_ck_plat_herc_inc scope

.if .Lhal_ck_vm_inc
  # +-----------------------------------------+
  # |  Detect a S/370 VM platform Subroutine  |
  # +-----------------------------------------+

            .align 2
.Lhal_ck_vm: 
            stidp  .LIEIB_cpuid(0)                # Store the CPUID
            cli    .LIEIB_cpuid(0),0xFF           # Are we running in a VM?
            bner   11                             # ..No, return to caller
            oi     .LIEIB_plt(0),.LIEIB_VM        # ..Yes, indicate VM
            br     11                             # Return
.endif

.if .Lhal_det_cons_inc
  # +------------------------------------------------+
  # |  Determine Console Device Number Information   |
  # +------------------------------------------------+ 

            .align 2
.Lhal_det_cons:
            basr   10,0
0:
.if .Lhal_use_d24_for_console
            tm     .LIEIB_plt(0),.LIEIB_Herc|.LIEIB_VM
  .ifdef .Lhal_cons
            bnz    .Lhal_det_cons_d24-0b(10) # Get device num from DIAGNOSE X'24'
            # Use the default console device number
            mvc    .LIEIB_cdn(2,0),.Lhal_det_cons_dnum-0b(10)
            oi     .LIEIB_plt(0),.LIEIB_conn  # Device number is available
            br     11      # Return with default console device set
.Lhal_det_cons_dnum:  # Default console device number from hal macro
            .hword .Lhal_cons   # Default console device
.Lhal_det_cons_d24: # Use DIAGNOSE X'24' to get console device number

   .else
            bzr    11     # Not on Hercules or VM and no default, just return
   .endif # .ifdef .Lhal_cons
            l      8,.Lhal_det_cons_minus_one-0b(10)
            diag   8,6,0x24         # locate the console device
            clm    8,0b1000,.Lhal_det_cons_console_code-0b(10) 
            bner   11     # Return, not a recognized "console"
            sth    8,.LIEIB_cdn(0)  # Save the device number in the IEIB
            oi     .LIEIB_plt(0),.LIEIB_conn  # Device number is available
            br     11
.Lhal_det_cons_minus_one:
            .long  -1           # Request the virtual console device number
.Lhal_det_cons_console_code:
            .byte  0      # 3215 (VM/Herc), 3210 (VM), 2150 (VM), 1052 (VM/Herc)

.else  # .if .Lhal_use_d24_for_console - neither Hercules nor VM being supported

  .ifdef .Lhal_cons
            # Use the default console device number
            mvc    .LIEIB_cdn(2,0),.Lhal_det_cons_dnum-0b(10)
            oi     .LIEIB_plt(0),.LIEIB_conn  # Device number is available
            br     11      # Return with default console device set           
.Lhal_det_cons_dnum:  # Default console device number from hal macro
            .hword .Lhal_cons   # Default console device
  .else  # .ifdef .Lhal_cons
            .warning "hal.S can not identify the console on S/370"
            .warning "Specify a default console device number on the hal macro"
            br     11
  .endif # .ifdef .Lhal_cons

.endif # .if .Lhal_use_d24_for_console

.endif # .if .Lhal_det_cons_s370_inc scope

.if .Lhal_det_cons_device_id_inc
  # +-------------------------------------------------+
  # |  Determine Channel Subsystem Console Device Id  |
  # +-------------------------------------------------+

            .align 2
.Lhal_det_cons_device_id:
            basr   10,0
0:
            tm     .LIEIB_plt(0),.LIEIB_conn     # Device number available?
            bnor   11                            # ..No, can't find device id
            l      1,.Lhal_det_cons_first_subch-0b(10) # Locate first subchannel
            b      .Lhal_det_cons_scan-0b(10)    # Inspect it
.Lhal_det_cons_next:
            al     1,.Lhal_det_cons_one-0b(10)   # Look at next subchannel
.Lhal_det_cons_scan:
            stsch  0(6)                          # Store SCHIB where caller says
            bcr    0b0001,11                     # Return to caller if at end
            tm     .LPMCW_f1(6),.LPMCW_devval    # Device number valid?
            bno    .Lhal_det_cons_next-0b(10)    # ..No, look at next subchannel
            cl     1,.LIEIB_ipl(0)               # IPL device?
            bne    .Lhal_det_cons_dev-0b(10)     # ..No, see if maybe console
            mvc    .LIEIB_idn(2,0),.LPMCW_dev(6) # ..Yes, save device number
            tm     .LIEIB_plt,.LIEIB_cons        # Console SCHIB found?
            bor    11                            # ..Yes, done so leave
            b      .Lhal_det_cons_next-0b(10)    # ..No, keep scanning
.Lhal_det_cons_dev:
            clc    .LPMCW_dev(2,6),.LIEIB_cdn(0) # Is this the console device?
            bne    .Lhal_det_cons_next-0b(10)    # ..No, check out next subchannel
            st     1,.LIEIB_cdi(0)               # ..Yes, save in IEIB    
            oi     .LIEIB_plt,.LIEIB_cons        # Indicate console is available
            b      .Lhal_det_cons_next-0b(10)    # Check next for IPL device
.Lhal_det_cons_first_subch:
           .long   0x00010000
.Lhal_det_cons_one:
           .long   1

.endif # .if .Lhal_det_cons_device_id_inc

.if .Lhal_det_devids_s370_inc
  # +-------------------------------------------+
  # |  Determine S/370 Device Id's and numbers  |
  # +-------------------------------------------+

            .align 2
.Lhal_det_devids_s370:
            basr   10,0
0:
            tm     .LIEIB_plt(0),.LIEIB_conn     # Device number available?
            bno    .+14-0b(10)                   # ..no, don't update id or flag
            mvc    .LIEIB_cdi+2(2,0),.LIEIB_cdn  # Know device id now too
            oi     .LIEIB_plt(0),.LIEIB_cons     # Indicate console is available
            mvc    .LIEIB_idn(2,0),.LIEIB_ipl(0) # Know IPL device number too
            br     11                            # Return to caller

.endif # .if .Lhal_det_devids_s370_inc

.if .Lhal_det_stg_s370_inc
  # +------------------------------------------------+
  # |  Determine S/370 Main Storage Size Subroutine  |
  # +------------------------------------------------+ 

            .align 2
.Lhal_det_stg_s370:
            basr   10,0
0:          tm     .LIEIB_plt(0),.LIEIB_Herc        # Is this Hercules?
            bz     .Lhal_stg_probe-0b(10)           # ..No, need to probe storage
            # With Hercules we can use a DIAGNOSE to determine storage size
            sr     0,0               # Request highest addressable byte
            diag   2,0,0x260         # Get the information
            st     2,.LIEIB_stg+4    # Save it in IEIB
            br     11                # Return to caller

.Lhal_stg_probe:
            lm     0,2,.Lhal_stg_max-0b(10) # Set up memory scan registers
            # Terminate when we hit a program interruption
            pgmtrans to=.Lhal_stg_meg_end,wrkr=4,br=10 
.Lhal_stg_ck:
            cli    0(2),0x00                # ..No, try to access the storage
            # If we fell through, this megabyte is all or partially available
            alr    2,1                      # Incrment to next meg
            clr    0,2                      # Are we at max memory?
            be     .Lhal_stg_end-0b(10)     # ..Yes, end probe
            b      .Lhal_stg_ck-0b(10)      # ..No, see if this one is there

.Lhal_stg_meg_end: # Reset values to now scan the previous meg for its end
            pgmreset
            lr     0,2                      # The failing meg is the maximum
            slr    2,1                      # Locate start of previous megabyte
            la     1,0x800                  # Scan each 2K page for its presence
            # End mem. probe on program interrupt
            pgmtrans to=.Lhal_stg_end,wrkr=4,br=10
            b      .Lhal_stg_ck-0b(10)      # Now scan this megabyte

.Lhal_stg_end:
            pgmreset                        # Reset traps
            bctr   2,0                      # Calculate highest address
            st     2,.LIEIB_stg+4(0)        # Save it in the IEIB
            br     11                       # Return to caller

.Lhal_stg_max: .long 0x01000000      # R0 = Maximum incremented meg value plus 1
.Lhal_stg_meg: .long 0x00100000      # R1 = One megabyte
.Lhal_stg_ctr: .long 0x00100000      # R2 = Current size being tested

.endif # .Lhal_det_stg_s370_inc scope

.if .Lhal_det_stg_s390_inc
.if .Lhal_32bit

  # +--------------------------------------------------------------------+
  # |  Determine ESA/390 or z/Architecture Main Storage Size Subroutine  |
  # +--------------------------------------------------------------------+ 

           .align  2
.Lhal_det_stg_s390:
           basr    10,0
0:

      # Environmental setup for the SERVICE CALL instruction

            # This means we are running in either ESA/390 or z/Architecture mode.
            # The SERVICE CALL instruction will be used below to determine main
            # storage size.  The SERVICE CALL instruction requires that external
            # interrupts be enabled.  The CPU reset that is part of the Initial
            # Program Load function will set the CPU timer to zero.  Almost
            # immediately after IPL the CPU timer will be decremented to a negative
            # value.  As soon as this occurs, an external interrupt will be pending.
            # The interrupt is pending because all of the PSW's under which this
            # program runs upto this point will have the external interrupts
            # disabled.  The interrupt remains pending until external interrupts 
            # are enabled or the CPU timer value is set to a postive value, 
            # whichever comes first.  This SET CPU TIMER instruction will return 
            # the timer to a positive value, removing the pending interrupt.  If 
            # this is not done, the interrupt from the service processor indicating 
            # that the information requested is available in the SCCB will be 
            # missed.
            spt     .Lcpu_timer-0b(10)       # Make sure no interrupt from timer

            # We will use a 4096 byte SCCB area.  Because the SCCB must not cross
            # a page boundary, we will locate the start of the page following the
            # program.
            lm      2,4,.Lsccbparm-0b(10)    # Set up parameters for SERVICE CALL

            # Initialize the SCCB header
            mvi     0(3),0x00                # Clear the header to zeros
            mvc     1(.Lsscb_hdr_len-1,3),1(3)
            sth     4,.Lsccb_len(3)          # Set the length in the SCCB header

      # Use service processor to determine storage size

            mvc     .Lsv_s390-0b(8,10),.LPSW_newext(0)  # Save the external new PSW
            mvc     .LPSW_newext(8,0),.Lck_serv-0b(10)  # Set trap for SERVC int.
            lm      2,3,.Lsccbparm-0b(10)    # Set up registers for SERVC
            servc   2,3                      # Get the information
            bc      0b1000,.+8-0b(10)        # Successful?
            halabort error=0x0004            # ..No, SERVICE CALL failure
            stctl   0,0,.Lcr0save-0b(10)     # Save control register zero
            lctl    0,0,.Lservcena-0b(10)    # Enable service signal interrupts
            lpsw    .Lhal_ck_servw-0b(10)    # ..Yes, wait for returned results

.Lhal_serv_rtn: # Return here after external interrupt from service processor          
            mvc     .LPSW_newext(8,0),.Lsv_s390-0b(10) # Restore ext. new PSW
            lctl    0,0,.Lcr0save-0b(10)     # Restore CR0 to prevous state
            clc     .Lsccb_reason(2,3),.Lservok-0b(10) # SERVC returned info?
            be      .Lhal_serv_anal-0b(10)   # ..Yes, figure out storage size
            halabort error=0x0005            # SERVICE CALL failed to return data

.Lhal_serv_anal: # Analyze SERVC response
            st      3,.LIEIB_sccb(0)         # Save the SCCB address in the IEIB

      # Save LOADPARM

            la     3,.Lsscb_hdr_len(3)       # Point to the SCP information block
            mvc    .LIEIB_LP(8,0),.Lscp_loadparm(3)  # Set the LOADPARM in IEIB

      # Calculate highest addressable storage byte

            sr     5,5                       # Make sure R5 is zero
            lr     2,5                       # and R2 is zero
            ic     2,.Lscp_realiszm(3)       # R2 = Storage increment in megabytes
            icm    5,0b0011,.Lscp_realinum(3)# R5 = The number of increments
            mr     4,2                       # Total megabytes in R4,R5 pair
            sldl   4,20                      # R4, R5 = Size of storage in bytes
            sl     5,.Lone_64bit+4-0b(10)    # Subtract logical one from R5
            slb    4,.Lone_64bit-0b(10)      # Subtract borrow from R4 (if any)
            stm    4,5,.LIEIB_stg(0)         # Store highest address in IEIB
            br     11                        # Return

            .align 8
.Lck_serv:  s390psw24  s=0,p=0,a=.Lhal_serv_rtn   # Return from ESA/390 SERVC

 # Parameters to get SCP information via SERVICE CALL instruction
.Lsccbparm: .long  .Lsclp_read_scp_info  # R2 = Request
.Lhal_sccb: .long  0                     # R3 = Address of the SCCB
            .long  4096                  # R4 = size of SCCB

.endif # .if .Lhal_32bit scope

.if .Lhal_64bit

  # +---------------------------------------------------------+
  # |  Determine z/Architecture Main Storage Size Subroutine  |
  # +---------------------------------------------------------+ 

           .align  2
.Lhal_det_stg_s390x:
           basr    10,0
0:

     # Environmental setup for the SERVICE CALL instruction

            spt     .Lcpu_timer-0b(10)       # Make sure no interrupt from timer
            
            # We will use a 4096 byte SCCB area.  Because the SCCB must not cross
            # a page boundary, we will locate the start of the page following the
            # program.
            lmg     2,4,.Lsccbparmg-0b(10)   # Set up parameters for SERVICE CALL

            # Initialize the SCCB header
            mvi     0(3),0x00                # Clear the header to zeros
            mvc     1(.Lsscb_hdr_len-1,3),1(3)
            sth     4,.Lsccb_len(3)          # Set the length in the SCCB header

      # Use service processor to determine storage size

            mvc     .Lsv_s390x-0b(16,10),.LPSW_newextg(0)   # Save external new PSW
            mvc     .LPSW_newextg(16,0),.Lhal_ck_servx-0b(10)  # Set trap for SERVC
            servc   2,3                      # Get the information
            bc      0b1000,.+8-0b(10)        # Successful?
            halabort error=0x0004            # ..No, SERVICE CALL failure
            stctl   0,0,.Lcr0save-0b(10)     # Save control register zero
            lctl    0,0,.Lservcena-0b(10)    # Enable service signal interrupts
            lpsw    .Lhal_ck_servw-0b(10)    # ..Yes, wait for returned results


.Lhal_serv_rtnx: # Return here after external interrupt from service processor          
            mvc     .LPSW_newextg(16,0),.Lsv_s390x-0b(10) # Restore ext. new PSW
            lctl    0,0,.Lcr0save-0b(10)     # Restore CR0 to prevous state
            clc     .Lsccb_reason(2,3),.Lservok-0b(10) # SERVC returned info?
            be      .Lhal_serv_analx-0b(10)  # ..Yes, figure out storage size
            halabort error=0x0005            # SERVICE CALL failed to return data

.Lhal_serv_analx: # Analyze SERVC response
            stg     3,.LIEIB_sccbg(0)        # Save the SCCB address in the IEIB

      # Save LOADPARM

            la     3,.Lsscb_hdr_len(3)       # Point to the SCP information block
            mvc    .LIEIB_LP(8,0),.Lscp_loadparm(3)  # Set the LOADPARM in IEIB

      # Calculate highest addressable storage byte

            sgr    4,4                       # Make sure R4 is zero
            lgr    2,4                       # and R2 is zero
            ic     2,.Lscp_realiszm(3)       # R2 = Storage increment in megabytes
            icm    4,0b0011,.Lscp_realinum(3)# R4 = The number of increments
            msr    4,2                       # Total megabytes in R4
            sllg   4,4,20                    # R4 = Size of storage in bytes
            slg    4,.Lone_64bit-0b(10)      # Subtract logical one from R4
            stg    4,.LIEIB_stg(0)           # Store highest address in IEIB
            br     11                        # Return

            .align 8
.Lhal_ck_servx: s390xpsw24  s=0,p=0,a=.Lhal_serv_rtnx   # Return from z/Arch SERVC

 # Parameters to get SCP information via SERVICE CALL instruction
.Lsccbparmg:.quad  .Lsclp_read_scp_info  # R2 = Request
.Lhal_sccbg:.quad  0                     # R3 = Address of the SCCB
            .quad  4096                  # R4 = size of SCCB

.endif # .if .Lhal_64bit scope

.Lone_64bit:.quad  1    # Constant of one (used for determining highest address)
.Lcpu_timer:.quad  0x7FFFFFFFFFFFFFFF    # New CPU Timer to inhibit interrupts
.Lhal_ck_servw: s390psw24  s=0x0102,p=0,a=0      # Waiting for external interrupt
.Lcr0save:  .long  0                     # Save area for control register C0
.Lservcena: .long  .Lcr0_srvsgnl         # C0 to enable service signal interrupt
.Lservok:   .byte  .Lsccb_reas_none,.Lsccb_resp_info  # SERVICE CALL successful

.endif #.if .Lhal_det_stg_s390_inc scope

.if .Lhal_init_ihcb_inc
.Lhal_init_ihcb:
            # Clear the entire IHCB area
            mvi    .Lih_area(0),0x00
            mvc    .Lih_area+1(256,0),.Lih_area(0)
            mvc    .Lih_area+257(256,0),.Lih_area+256
            mvc    .Lih_area+513(256,0),.Lih_area+512
            mvc    .Lih_area+769(.Lih_area_len-768,0),.Lih_area+768
            sr     0,0                          # Clear r0
            la     0,.Lihsapgm(0)               # Locate the initial save area
            st     0,.Lihsa(0)                  # Set it as the active save area
            # Note: the high-order bits of .Lihsag were set to zero's by clearing
            br     11                           # Return to caller
.endif

.if .Lhal_init_ieib_inc
  # +----------------------------------+
  # |  Initialize the IEIB Subroutine  |
  # +----------------------------------+     

            .align 2
.Lhal_init_ieib:
            mvi    .LIEIB(0),0x00    # Clear the IPL Environment Information Block 
            mvc    .LIEIB+1(.LIEIB_len-1,0),.LIEIB(0)
            stap   .LIEIB_cpu(0)     # Save the CPU address of this CPU
            br     11
.endif

.if .Lhal_plat_common_inc
  # +--------------------------------------------------------+
  # |  Storage Areas Used by multiple routines within hal.S  |
  # +--------------------------------------------------------+

             .align 8
 # The .Lck_pgm PSW is used pass control to a specific location if a program 
 # interrupt occurs.  Normally, the address to which control should pass will be 
 # placed in this location, the current disabled wait trap will be saved in 
 # .Lsv_npgm and then this PSW will be placed in the 64-bit new program PSW assigned
 # storage location.  Because this mechanism is used in a number of places the
 # following macros are provided to simplify usage:
 #   Macro        Description
 #   pgmtrans   32-bit transfer control to a location if a program interrupt occurs.
 #   pgmtransx  64-bit transfer control to a location if a program interrupt occurs.
 #   pgmreset   32-bit reset the program interrupt new PSW to a disabled wait PSW
 #   pgmresetx  64-bit reset the program interrupt new PSW to a disabled wait PSW

.if .Lhal_32bit
.Lck_pgm:   s390psw24  s=0,p=0,a=0           # 32-bit Detection PSW template
.Lsv_npgm:  .quad  0       # Save area for 32-bit archs new pgm trap PSW
.Lsv_s390:  .quad  0       # Save area for ESA/390 new external PSW (for SERVC)
.endif # .if .Lhal_32bit scope

.if .Lhal_64bit
.Lck_pgmx:  s390xpsw24 s=0,p=0,a=0           # 64-bit Detection PSW template
.Lsv_npgmx: .octa  0       # Save area for 64-bit arch new pgm trap PSW
.Lsv_s390x: .octa  0       # Save area for z/Arch new external PSW (for SERVC)
.endif # .if .Lhal_64bit scope

.endif # .if .Lhal_plat_common_inc scope

.if .Lhal_tt
            .eject
            .sbttl "Hardware Abstraction Layer - ASCII/EBCDIC Translate Tables"
  # +---------------------------------+
  # |  ASCII/EBCDIC Translate Tables  |
  # +---------------------------------+

            .include "EBCDIC.S"
.Lhal_translate_tables:
            .quad  .Lhal_a2e
            .quad  .Lhal_e2a

.Lhal_a2e:
            TR_A_E
.Lhal_e2a:
            TR_E_A

.endif # .if .Lhal_tt scope

.if .Lhal_ih
            .eject
            .sbttl "Hardware Abstraction Layer - Interrupt Handler Abstractions"
            .include "ihal.S"   # Include the interrupt abstractions if requested
.endif # .if .Lhal_ih scope

.if .Lhal_iolo
            .eject
            .sbttl "I/O Low-Level Hardware Abstraction Layer"
            .include "ioallo.S"
.endif
.if .Lhal_io
            .sbttl "I/O Hardware Abstraction Layer"
            .eject
            .include "ioal.S"   # Include the I/O abstractions if being supported
.endif # .if .Lhal_io scope

.else
            .error "hal.S suppressed due to missing hal macro options"
.endif # ifdef .Lhal_options scope

.endif # ifndef .Lhal_S scope
