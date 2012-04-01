.ifndef .Lihal_S
.Lihal_S = 1
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

 # This module provides the Interrupt Handler Abstraction Layer of the CPU that
 # include the abstracted interrupt handlers and abstract functions.
 #
 # ihal.S is automatically included by hal.S if required.
 #
 # The abstract interrupt handlers form the interface between the hardware
 # interrupt mechanism and the Interrupt Handler Function abstraction.  Within the
 # abstract handlers the following conventions are used for register usage.
 #
 # Current Design Capabilities:
 #
 # Interrupt handler functions may enable interrupts and generate their own
 # provided the interrupt handler function provides a save area linked to its
 # active save area.  With linked save areas, recursive interrupts are possible.
 # Recursive interrupts without a new linked save area is prohibited.  An
 # interrupt handler function that links a save area to the save area stack, must
 # unlink that save area before returning to the interrupt handler.  Disabled
 # interrupts must not be enabled by an interrupt handler unless a new save area
 # has been linked to the save area stack.
 #
 # If both an in-line wait and handler function are enabled for the classes that
 # support both, if the old PSW indicates the CPU was waiting, the in-line wait
 # handling takes precedence over the function call.

 # Abstract Interrupt Handler Register Usage
 #
 # On Entry: 
 #   R0-R15   Interrupted program's register content (preserved)
 #
 # Used:        Reference      Usage Description
 #
 #   R0         various        work register
 #   R1         Handler        Location of parameter setup logic (32-bit only)
 #   R2         ihentry[g]     Active save area pointer
 #   R3         Handler        Interrupt class
 #   R4         Arg setup      Interrupt code
 #   R5         Arg setup      Interruption information (part 1)
 #   R6         Arg setup      Interruption information (part 2)
 #   R7         ihentry[g]     Interrupt Handler Control Block pointer
 #   R8         ihentry[g]     Global Abstract handler base register to 0b
 #   R9         ihentry[g]     Architecture Support Block pointer
 #   R10        class handler  Next step base register
 #   R12        not used
 #   R13        Function call  Abstract handler function address
 #   R14        Function call  Abstract handler function return address
 #   R15        Function call  Interrupt handling ABI stack
 #
 # On Exit: 
 #    Interrupt handling completed
 #    R0-R15  Preserved interrupted program's register content restored

 # 
 # Dependencies:
 #
            .include "IHCB.S"   # Include the IH structures
            .include "psw.S"    # Assigned storage locations for PSW's

 # Macro definitions specific to ihal.S
 #
 # Macro        Description
 #   ihentry    32-bit Interrupt Handler entry following the interrupt mechanism
 #   ihentryg   64-bit Interrupt Handler entry following the interrupt mechanism
 #
 # Abstract Interrupt Handler Register Usage
 #
 # On Entry: interrupted program's register content (preserved)
 #
 # Used:        Reference      Usage Description
 #
 #   R0         various          work register
 #   R1         Handler          Location of parameter setup logic (32-bit only)
 #   R2         ihentry[g]    *  Active save area pointer
 #   R3         Handler       *  Interrupt class
 #   R4         Arg setup     *  Interrupt code
 #   R5         Arg setup     *  Interruption information (part 1)
 #   R6         Arg setup     *  Interruption information (part 2)
 #   R7         ihentry[g]       Interrupt Handler Control Block pointer
 #   R8         ihentry[g]       Global Abstract handler base register to 0b
 #   R9         ihentry[g]       Architecture Support Block pointer
 #   R10        class handler    Next step base register
 #   R12        not used
 #   R13        Function call    Abstract handler function address
 #   R14        Function call    Abstract handler function return address
 #   R15        Function call    Interrupt handling ABI stack
 #
 # On Exit: 
 #    Interrupt handling completed
 #    Preserved interrupted program's register content restored

.if .Lhal_32bit
            .eject
            .sbttl "Harware Abstraction Layer - Abstract Interrupt Handlers"

  # +----------------------------+
  # |  Setup Include conditions  |
  # +----------------------------+

.Lihal_s370_pgm_common = 0
.Lihal_s370bc_ext_inc = 0
.Lihal_s370_io_inc = 1
.Lihal_s370bc_pgm_inc = 0
.Lihal_s370bc_svc_inc = 0
.Lihal_s390_io_inc = 0
.Lihal_s390_pgm_inc = 0
.Lihal_s3x0_ext_inc = 0
.Lihal_s3x0_svc_inc = 0

.if .Lhal_s370bc
.Lihal_s370bc_ext_inc = 1
.Lihal_s370_io_inc = 1
.Lihal_s370bc_pgm_inc = 1
.Lihal_s3x0_pgm_common = 1
.Lihal_s370bc_svc_inc = 1
.endif # .if .Lhal_s370bc

.if .Lhal_s370
.Lihal_s3x0_ext_inc = 1
.Lihal_s370_io_inc = 1
.Lihal_s3x0_pgm_common = 1
.Lihal_s3x0_svc_inc = 1
.endif # .if .Lhal_s370

.if .Lhal_s390
.Lihal_s390_pgm_inc = 1
.Lihal_s390_io_inc = 1
.Lihal_s3x0_ext_inc = 1
.Lihal_s3x0_svc_inc = 1
.Lihal_s3x0_pgm_common = 1
.endif # .if .Lhal_s390

  # +---------------------------------------+
  # |  32-bit IH Handler Entry Logic Macro  |
  # +---------------------------------------+

 # ihentry - Interrupt Handler entry following the interrupt mechanism
 #
 # Macro Parameters:
 #   name       The symbol associated with the abstract interrupt handler. This is
 #              the real interrupt handler that gets control when an interrupt
 #              new PSW becomes the current PSW. (required)
 #   opsw       Assigned storage location of the interrupt class' old PSW (required)
 #   ihcb       Symbol representing the assigned storage allocated for this class'
 #              Interrupt Handler Control Block. (required)
 #   ptrap      Trap PSW symbol for program trap within macro.  Only needed for 
 #              program interrupt class.  (optional)

            .macro ihentry name:req cls:req opsw:req ihcb:req ptrap
            .align 2
\name:
            stm    7,8,\ihcb+.LIHCB_sa(0)     # Temporarily save R7 and R8
            basr   8,0                        # Create a local base register
1:          
    .ifnb \ptrap
            mvc    .LPSW_newpgm(8,0),\ptrap-1b(8)  # Make sure pgm trapped within macro
    .endif
            l      8,.Lihal_base_addr-1b(8)   # Set up global base
            l      7,.Lihsa(0)                # Locate active save area
            ts     .LIH_SR_state(7)           # Indicate save area has state
            bc     0b1000,.+8-0b(8)           # If save area not in use, good to go
            lpsw   .Lih_rec32-0b(8)           # Recursion! Die, immediately
            mvi    .LIH_SR_class(7),\cls      # Indicate the class that owns the sa
            mvc    .LIH_oPSW(8,7),\opsw(0)    # Save the old PSW 
            stm    0,15,.LIH_GR(7)            # Interrupt programs GR0-GR15 saved
            mvc    .LIH_R7(8,7),\ihcb+.LIHCB_sa(0)  # Now save R7 and R8
            lr     2,7                        # Establish the save area pointer
            la     7,\ihcb(0)                 # Establish IH control pointer
            l      9,.LIEIB_asb(0)            # Locate ASB
    .ifnb \ptrap
            mvc    .LPSW_newpgm(8,0),.Lihnpgm_PSW(0)  # Make sure pgm re-enabled
    .endif
            .endm

.Lihal_32base:
0: # Base address for 32-bit interrupt handling
  # +----------------------------+
  # |  32-bit HAL IH - External  |
  # +----------------------------+

  # IH Entry
       ihentry name=.Lih_ext32,cls=.LIH_ext_cls,opsw=.LPSW_oldext,ihcb=.Lihext

  # IH Function Setup
            lh     3,.Lihal_ext_cls-0b(8)     # R3 = interruption class
            l      1,.LASB_ihext(9)           # Locate setup routine
            la     10,.Lihal_inwait32-0b(8)   # Do in-line wait after setup
            br     1                          # Do the setup

  # +--------------------------------+
  # |  32-bit HAL IH - Input/Output  |
  # +--------------------------------+

  # IH Entry
       ihentry name=.Lih_io32,cls=.LIH_io_cls,opsw=.LPSW_oldio,ihcb=.Lihio

  # IH Function Setup
            lh     3,.Lihal_io_cls-0b(8)      # R3 = interruption class
            l      1,.LASB_ihio(9)            # Locate the I/O Handler
            la     10,.Lihal_inwait32-0b(8)   # Do in-line wait after setup.
            br     1                          # Do the setup

  # +---------------------------------+
  # |  32-bit HAL IH - Machine Check  |
  # +---------------------------------+

  # IH Entry
       ihentry name=.Lih_mck32,cls=.LIH_mck_cls,opsw=.LPSW_oldmck,ihcb=.Lihmck

  # IH Function Setup
            sr     3,3                        # R3 = interruption class
            lm     4,5,.LINT_mckcode(0)       # R4,R5 = machine check code
            b      .Lihal_func32-0b(8)        # Function/restore/exit

  # +---------------------------+
  # |  32-bit HAL IH - Program  |
  # +---------------------------+

  # IH Entry
       ihentry name=.Lih_pgm32,cls=.LIH_pgm_cls,opsw=.LPSW_oldpgm,ihcb=.Lihpgm,ptrap=.Lih_prec32

  # IH Function Setup
            lh     3,.Lihal_pgm_cls-0b(8)     # R3 = interruption class
            l      1,.LASB_ihpgm(9)           # Locate the Program Handler
            la     10,.Lihal_func32-0b(8)     # Setup next step base register
            br     1                          # Set arguments and call handler

  # +---------------------------+
  # |  32-bit HAL IH - Restart  |
  # +---------------------------+

  # IH Entry
       ihentry name=.Lih_rst32,cls=.LIH_rst_cls,opsw=.LPSW_oldrst,ihcb=.Lihrst

  # IH Function Setup
            lh     3,.Lihal_rst_cls-0b(8)     # R3 = interruption class
            la     10,.Lihal_func32-0b(8)     # Setup next step base register
            br     10                         # Function call, restore, and exit

  # +-----------------------------------+
  # |  32-bit HAL IH - Supervisor Call  |
  # +-----------------------------------+

  # IH Entry
       ihentry name=.Lih_svc32,cls=.LIH_svc_cls,opsw=.LPSW_oldsvc,ihcb=.Lihsvc

  # IH Function Setup
            lh     3,.Lihal_svc_cls-0b(8)     # R3 = interruption class
            l      1,.LASB_ihsvc(9)           # Locate the SVC handler
            la     10,.Lihal_func32-0b(8)     # Set up next step base register
            br     1 

  # +------------------------------------+
  # |  32-bit HAL IH In-line Wait Logic  |
  # +------------------------------------+

.Lihal_inwait32:
            tm     .LIHCB_flags(7),.LIHCB_wait   # In-line wait active?
            bno    .Lihal_func32-0b(8)           # ..no, Function/restore/exit
            tm     .LIH_oPSW+1(2),0x02           # Was this an in-line wait?
            bno    .Lihal_func32-0b(8)           # ..no, Function/restore/exit
            # Turn PSW into a running PSW with I/O interrupts disabled
            # following in-line wait
            nc     .LIH_oPSW(2,2),.LASB_nowtmsk(9) # Disable interrupts and waiting
            stm    3,5,.LIH_R3(2)                # Return interupt information
            tm     .LIHCB_flags(7),.LIHCB_func   # Function enabled?
            bz     .Lihal_exit32-0b(8)           # ..No, so just restore/exit
            b      .Lihal_func32_try-0b(8)       # ..Yes, try the function

  # +-------------------------------------------------+
  # |  32-bit HAL IH Function / Restore / Exit Logic  |
  # +-------------------------------------------------+

  # On Entry:
  #    R2      Program save area address
  #    R3      Pointer to new PSW for interrupt class
  #    R7      IHCB Pointer
  #    R10     Next step base register
  #
  # On Exit:
  #    All CPU state required to be restored has been restored
  #    Interrupt handling completed

.Lihal_func32:
  # Not an in-line wait so, use Interrupt Handler function
            tm      .LIHCB_flags(7),.LIHCB_func   # Function enabled?
            bz      .Lihal_func32_no_func-0b(8)   # ..no, can't handle interrupt
.Lihal_func32_try:
            icm     13,0b1111,.LIHCB_ihf(7)       # R13 = IH Function
            bnz     .Lihal_func32_do_func-0b(8)   # Call the function
.Lihal_func32_no_func:
            lpsw   .Lih_nofunc32-0b(8)            # ..Die if no function
.Lihal_func32_do_func:
            oc     .LIH_link(4,2),.LIH_link(2) # Are we already in Interrupt state?
            bnz    .+8-0b(10)                  # ..yes, use our stack pointer
            l      15,.Lihstk(0)               # R15 = new interrupt stack pointer
            basr   14,13                       # Call the IH Function
            # Note: R2 may contain a different save area

  # Exit interrupt handling
.Lihal_exit32:
            mvc    .Lihexit_PSW(8,0),.LIH_oPSW(2) # Setup old PSW for exit
            st     2,.Lihsa(0)                    # Update the active save area
            mvi    .LIH_SR_state(2),0x00          # Free up save area for next use
            lm     0,15,.LIH_GR(2)                # Restore CPU regs
            # All handler register content is now lost
            lpsw   .Lihexit_PSW(0)                # Exit interrupt handling

  # +----------------------------------+
  # |  32-bit HAL IH Shared PSW Traps  |
  # +----------------------------------+

.Lih_prec32: # Program interrupt within abstract program interrupt handler
            s370psw s=0,p=0,a=0x006660

.Lih_rec32:  # Interrupt recursion detected 
            s370psw s=0,p=0,a=0x006662

.Lih_nofunc32: # No handler function set for enabled interrupt class
            s370psw s=0,p=0,a=0x006664

            .eject
            .sbttl "Hardware Abstraction Layer - Interrupt Function Preparation"

.if .Lihal_s370bc_ext_inc
  # +------------------------------------------+
  # |  S/370 BC - External Interrupt Handling  |
  # +------------------------------------------+
  # Access: private

.Lihal_s370bc_ext:
            lh     4,.LIH_oPSW+2(2)           # R4 = external interruption code
            lh     4,.LINT_extcode(0)         # R4 = external interruption code
            br     10                         # Do next step
.endif # .if .Lhal_s370bc_ext_inc

.if .Lihal_s370bc_svc_inc
  # +---------------------------------------+
  # |  S/370 BC - Supervisor Call Handling  |
  # +---------------------------------------+
  # Access: private

.Lihal_s370bc_svc:
            sr     4,4
            ic     4,.LIH_oPSW+3(2)           # R4 = supervisor call code
            ic     5,.LIH_oPSW+4(2)           # ILC in bits 24,25 of R0
            # R5 = .... ....  .... ....  .... ....  LC.. ....
            n      5,.Lihal_s370_ilc-0b(8)    # Isolate ILC
            # R5 = 0000 0000  0000 0000  0000 0000  LC00 0000
            srl    5,5                        # Put ILC in bits 29 and 30
            # R5 = 0000 0000  0000 0LC0  0000 0000  0000 0LC0
            br     10                         # Do next step

.Lihal_s370_ilc:
            .long   0x000000C0   # ILC isolation mask
.endif # .if .Lihal_s370bc_svc_inc

.if .Lihal_s3x0_ext_inc
  # +------------------------------------------+
  # |  S/370 EC - External Interrupt Handling  |
  # +------------------------------------------+
  # Access: private

.Lihal_s3x0_ext:
            lh     4,.LINT_extcode(0)         # R4 = external interruption code
            lh     5,.LINT_extproc(0)         # R5 = external interruption processor
            l      6,.LINT_extparm(0)         # R6 = external interruption parameter
            br     10                         # Do next step
.endif # .if .Lihal_s370ec_ext_inc

.if .Lihal_s3x0_svc_inc
  # +---------------------------------------+
  # |  S/370 EC - Supervisor Call Handling  |
  # +---------------------------------------+
  # Access: private

.Lihal_s3x0_svc:
            lh     4,.LINT_svccode(0)         # R4 = supervisor call code
            lh     5,.LINT_svcilc(0)          # R5 = supervisor call ILC
            br     10                         # Do next step
.endif # .if .ihal_s370ec_svc_inc


.if .Lihal_s370_io_inc
  # +--------------------------------------------------+
  # |  S/370 - Input/Output Common Interrupt Handling  |
  # +--------------------------------------------------+
  # Access: private

.Lihal_s370_io:
            l      4,.LIEIB_asb(0)            # Locate the active ASB
            lh     4,.LASB_ioid(0)            # Locate where the IO ID is located
            lh     4,0(4)                     # R4 = device ID
            lm     5,6,.LIO_csw(0)            # R5,R6 = CSW
            br     10                         # Do next step

.endif # .if .Lihal_s370_io_inc

.if .Lihal_s390_io_inc
  # +---------------------------------------------+
  # |  ESA/390 - Input/Output Interrupt Handling  |
  # +---------------------------------------------+
  # Access: private

.Lihal_s390_io:
            l      4,.LIO_ssid(0)             # R4 = device ID
            lm     5,6,.LIO_intprm(0)         # R5 = int. parm, R6 = int. id.
            br     10                         # Do next step

.endif # .if .Lihal_s390_io_inc


.if .Lihal_s3x0_pgm_common

.if .Lihal_s370bc_pgm_inc
  # +-----------------------------------------+
  # |  S/370 BC - Program Interrupt Handling  |
  # +-----------------------------------------+
  # Access: private

.Lihal_s370bc_pgm:
            lh     3,.Lihal_pgm_cls-0b(8)     # R3 = interruption class
            ic     4,.LIH_oPSW+4(2)           # ILC in bits 24,25 of R0
            # R4 = .... ....  .... ....  .... ....  LC.. ....
            n      4,.Lihal_s370_ilc-0b(8)    # Isolate ILC
            # R4 = 0000 0000  0000 0000  0000 0000  LC00 0000
            sll    4,11                       # Put ILC in bits 13 and 14
            # R4 = 0000 0000  0000 0LC0  0000 0000  0000 0000
            icm    4,0b0011,.LIH_oPSW+2(2) # R4 = ILC and program code
            # R4 = 0000 0000  0000 0LC0  cccc cccc  cccc cccc
            b      .Lihal_s3x0_pgm_common-0b(8) # Perform common handling
.endif # .if .Lhal_s370bc_pgm_inc

.if .Lihal_s390_pgm_inc
  # +----------------------------------------+
  # |  ESA/390 - Program Interrupt Handling  |
  # +----------------------------------------+

.Lihal_s390_pgm:
           sr      6,6                        # Clear R6
           icm     6,0b0010,.LINT_pgmai(0)    # Bits 16-23 access id.
           ic      6,.LINT_pgmoi(0)           # Bits 24-31 operand access id.
           # Fall through to common handling

.endif # .if .Lihal_s390_pgm_inc

  # +---------------------------------------------+
  # |  S/370 - Program Common Interrupt Handling  |
  # +---------------------------------------------+
  # Access: private

.Lihal_s3x0_pgm:
            l      4,.LINT_pgmilc(0)          # R4 = program interruption code
.Lihal_s3x0_pgm_common:
            lr     0,4                        # Copy code for comparison
            n      0,.Lihal_noPER-0b(8)       # Clear any possible PER code
            clm    0,0b0011,.Lihal_mon-0b(8)  # Monitor interruption?
            bne    .Lihal_s3x0_pgm_not_mon-0b(8)   # ..no, normal interruption
            lh     5,.LINT_pgmmcls(0)         # R5 = program monitor class
            l      6,.LINT_pgmmcod(0)         # R6 = program monitor code
            br     10                         # Do next step

.Lihal_s3x0_pgm_not_mon:
            l      5,.LINT_pgmtran(0)         # R5 = translation / data id.
            br     10                         # Do next step

.endif # .if .Lihal_s370_pgm_common

  # +----------------------+
  # |  32-bit Common Data  |
  # +----------------------+

.Lihal_base_addr:.long  .Lihal_32base 
.Lihal_ext_cls:  .hword .LIH_ext_cls
.Lihal_io_cls:   .hword .LIH_io_cls
.Lihal_mck_cls:  .hword .LIH_mck_cls
.Lihal_pgm_cls:  .hword .LIH_pgm_cls
.Lihal_rst_cls:  .hword .LIH_rst_cls
.Lihal_svc_cls:  .hword .LIH_svc_cls


.Lihal_s370_zeros:
            .hword 0

            .eject
            .sbttl "Interrupt Hardware Abstraction Layer - 32-bit"
  # +------------------------------+
  # |  32-bit INIT IH Abstraction  |
  # +------------------------------+
  # Access: public

  # On entry:
  #    R2     Interrupt handler stack bottom address
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: None
  #
  # On exit: None

            func370 .Lihal_init32
            push370

            framecr stkr=2               # Create a stack frame at the bottom
            st     2,.Lihstk(0)          # Set the bottom frame as interrupt stack

            return

  # +---------------------------------+
  # |  32-bit INIT IH SA Abstraction  |
  # +---------------------------------+ 

  # On entry:
  #    R2     Pointer to save area
  #    R3     Proposed save area controls
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Active ASB 
  #
  # On exit: None

            func370 .Lihal_initsa32
            push370

            mvi    0(2),0x00                   # Clear
            mvc    1(256,2),0(2)               # entire
            mvc    257(.LIH_len-257,2),256(2)  # Save area

            return

  # +-------------------------------+
  # |  32-bit IH CLASS Abstraction  |
  # +-------------------------------+ 

  # On entry:
  #    R2     Interrupt class
  #    R3     Abstract interrupt handler function address when enabling the class,
  #           zero when disabling the class
  #    R4     Interrupt mask (see below)
  #    R5     Additional interruption class parameter (see below)
  #    R13    Abstract function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R2     Address of the interrupt class IHCB entry
  #    R7     Active ASB
  #    R8     Interrupt class / pointer to internal enable/disable table
  #    R9     Build table address
  #    R10    Shared subroutine base address / or exit logic
  #    R11    Shared subroutine return address
  #    R12    Local work registers
  #
  # On exit:
  #    Interrupt class is enabled or disabled depending upon the arguments.
  #    If I/O or external interrupts are targeted by the call, the I/O or external
  #    interrupt will be disabled upon return.  The program must enable the 
  #    interrupt in the PSW when it is ready to use the interrupt function.
  #
  #  Interrupt Class
  #                          R4 Meaning
  #  Input/Output    C2 channel masks or C6 subclass masks
  #  External        C0 external masks
  #  Machine check   C14 machine check masks
  #
  #                          R5 Meaning
  #                                      In-line wait    Function
  #  Input/Output    R5 == 0 ==>           disabled      disabled
  #  and External    R5 == 1 ==>           enabled       disabled
  #                  R5 == 2 ==>           disabled      enabled
  #                  R5 == 3 ==>           enabled       enabled
  #  Machine check   on S/370, contains the machine check logout area

            func370 .Lihal_cls32

  # Local frame usage
            fquad .Lihal_cls32_nPSW         # New PSW build area
            flong .Lihal_cls32_cr           # control register load work area
            fbyte .Lihal_cls32_sm           # System mask stored here
            fbyte .Lihal_cls32_class        # Place to save the interrupt class
            fbyte .Lihal_cls32_enasm        # System mask to enable interrupt

 # Local literal pool
            struct  .Lihal_btbl32
            sbytes  .Lihal_btbl32_nPSW,24
            sbytes  .Lihal_btbl32_oPSW,24
            sbytes  .Lihal_btbl32_handlers,24

  # Build Table
.Lihal_cls32_nPSW_addr:
            .long   .LPSW_newmck
            .long   .LPSW_newext
            .long   .LPSW_newio
            .long   .LPSW_newsvc
            .long   .LPSW_newrst
            .long   .LPSW_newpgm
.Lihal_cls32_oPSW_addr:
            .long   .LPSW_oldmck
            .long   .LPSW_oldext
            .long   .LPSW_oldio
            .long   .LPSW_oldsvc
            .long   .LPSW_oldrst
            .long   .LPSW_oldpgm
.Lihal_cls32_handlers:
            .long   .Lih_mck32
            .long   .Lih_ext32
            .long   .Lih_io32
            .long   .Lih_svc32
            .long   .Lih_rst32
            .long   .Lih_pgm32

.Lihal_cls32_options:
            .long    0x00000003              # Mask for options
.Lihal_cls32_iodis:
            stnsm   .Lihal_cls32_sm(15),0   # Executed to disable I/O interrupts
.Lihal_cls32_max:
            .long  0x00000014   # Maximum valid class id
.Lihal_cls32_size:
            .hword .LIHCB_len   # Length of a single IHCB entry

            push370

            lr     8,2                            # Save ID for reference below

            l      0,.Lihal_cls32_options-0b(13)   # Get mask
            nr     0,2                          # Low-order bits zeros?
            bz     .+8-0b(13)                   # ..Yes, continue checks
            halabort error=0x000D               # Cause abort

            ltr    2,2
            bnm    .+8-0b(13)                   # Id >= zero?
            halabort error=0x000E               # ..no, invalid value

            cl     2,.Lihal_cls32_max-0b(13)    # ID > 20?
            bnh    .+8-0b(13)                   # ..no, valid value, continue
            halabort error=0x000E               # ..yes, quit

            mh     2,.Lihal_cls32_size-0b(13)   # Calculate displacement to IHCB
            la     2,.Lih_area(2,0)             # Return the address of the IHCB
            # R2 now contains the address of the IHCB

            stc    8,.Lihal_cls32_class(15)       # Save the interrupt class
            la     9,.Lihal_cls32_nPSW_addr-0b(13)# Locate the build table
            l      7,.LIEIB_asb(0)                # Locate active ASB

    # Enable an interrupt class
            b      .+4-0b(8,13)             # Enable/Disable the interrupt class
            b      .Lihal_cls32_mck-0b(13)  # Enable/Disable machine checks
            b      .Lihal_cls32_ext-0b(13)  # Enable/Disable external interruptions
            b      .Lihal_cls32_io-0b(13)   # Enable/Disable I/O interruptions
            b      .Lihal_cls32_svc-0b(13)  # Enable/Disable SVC interruptions
            b      .Lihal_cls32_rst-0b(13)  # Enable/Disable restart interruptions
            b      .Lihal_cls32_pgm-0b(13)  # Enable/Disable program interruptions

    # Enable Machine Checks
.Lihal_cls32_mck:
            # WARNING: Machine checks are assumed to be disabled before entry
            ltr     3,3                           # Enabling or disabling?
            bz      .Lihal_cls32_dis_nPSW-0b(13)  # Disabling...

            # Set IHCB for machine-check interruptions
            st      3,.LIHCB_ihf(2)               # Set the IH Handler Function

            # Set control registers for machine checks
            tm      .LIEIB_run(0),.LIEIB_s370|.LIEIB_s370bc  # S/370 running?
            bz      .Lihal_cls32_mck_no_logout-0b(13)        # ..no, not logout
            st      5,.Lihal_cls32_cr(15)         # Save logout addr in frame
            lctl    15,15,.Lihal_cls32_cr(15)     # Load into C15
.Lihal_cls32_mck_no_logout:
            st      4,.Lihal_cls32_cr(15)         # Save C14 masks in frame
            lctl    14,14,.Lihal_cls32_cr(15)     # Load into C14

            # Establish new PSW for enabled interrupts
            mvi     .LIHCB_flags(2),.LIHCB_func   # Enable the function
            b       .Lihal_cls32_ena_nPSW-0b(13)  # Build the enabling PSW, return

    # Enable/Disable External Interruptions
.Lihal_cls32_ext:

            stnsm   .Lihal_cls32_sm(15),0xFE      # Disable external interrupts 
            # Now safe to clear IHCB

            n       5,.Lihal_cls32_options-0b(13) # Clear options
            bz      .Lihal_cls32_dis_nPSW-0b(13)  # Disable the interrupt class
            # We are enabling from this point forward

            # Set IHCB for external interrupts
            stc     5,.LIHCB_flags(2)             # Set the IHCB flags
            st      3,.LIHCB_ihf(2)               # Set the new IH function

            # Set control register for external interrupts
            n       4,.LASB_extena(7)             # Turn off non external bits
            stctl   0,0,.Lihal_cls32_cr(15)       # Fetch C0 into storage
            l       1,.Lihal_cls32_cr(15)         # Put it where I can touch it
            or      1,4                           # Turn on what was requested
            st      1,.Lihal_cls32_cr(15)         # Put C0 back in storage
            lctl    0,0,.Lihal_cls32_cr(15)       # Put new values in C0

            # Establish new PSW for enabled interrupts
            b       .Lihal_cls32_ena_nPSW-0b(13)  # Now build the new PSW

    # Enable Input/Output Interruptions
.Lihal_cls32_io:
            ic      1,.LASB_iodmsk(7)             # Get PSW I/O disable mask
            ex      1,.Lihal_cls32_iodis-0b(13)   # Diable input/output interrupts

            n       5,.Lihal_cls32_options-0b(13) # Clear options
            bz      .Lihal_cls32_dis_nPSW-0b(13)  # Disable the interrupt class
            # We are enabling from this point forward

            # Set IHCB for external interrupts
            stc     5,.LIHCB_flags(2)             # Set the IHCB flags
            st      3,.LIHCB_ihf(2)               # Set the new IH function

            # Set control register for input/output interrupts
            tm      .LIEIB_plt,.LIEIB_sch         # Use CR6 for masks?
            bo      .Lihal_cls32_io_sch-0b(13)    # ..Yes,
            st      4,.Lihal_cls32_cr(15)         # Put interrupts masks in storage
            lctl    2,2,.Lihal_cls32_cr(15)       # Set channel masks
            # Establish new PSW for enabled interrupts
            b       .Lihal_cls32_ena_nPSW-0b(13)  # Now build the new PSW

.Lihal_cls32_io_sch:
            sll     4,24                          # Position masks
            st      4,.Lihal_cls32_cr(15)         # Put interrupts masks in storage
            lctl    6,6,.Lihal_cls32_cr(15)       # Set I/O class masks
            b       .Lihal_cls32_ena_nPSW-0b(13)  # Now build the new PSW

    # Enable/disable Supervisor Call Interruptions
.Lihal_cls32_svc:
    # Enable/disable Restart Interruptions
.Lihal_cls32_rst:
    # Enable/disable Program Interruptions
.Lihal_cls32_pgm:

            ltr     3,3                           # Enabling or disabling?
            bz      .Lihal_cls32_dis_nPSW-0b(13)  # Disabling...

            # Set IHCB for interrupts
            mvi     .LIHCB_flags(2),.LIHCB_func   # Set the IHCB flags
            st      3,.LIHCB_ihf(2)               # Set the new IH function
            b       .Lihal_cls32_ena_nPSW-0b(13)

.Lihal_cls32_dis_nPSW:
            mvc    .Lihal_cls32_nPSW(4,15),.LASB_disnpsw(7) # Move the system area
            la     12,.Lihal_btbl32_oPSW(8,9)     # Locate the old PSW address
            mvc    .Lihal_cls32_nPSW+4(4,15),0(12) # Set the disable wait address

            mvi    0(2),0x00                      # Clear the
            mvc    1(.LIHCB_len-1,2),0(2)         # ..entire IHCB
            b       .Lihal_cls32_ret-0b(13)       # Return to caller

.Lihal_cls32_ena_nPSW:
            mvc    .Lihal_cls32_nPSW(4,15),.LASB_enanpsw(7) # Move the system area
            la     12,.Lihal_btbl32_handlers(8,9) # Locate the handler
            mvc    .Lihal_cls32_nPSW+4(4,15),0(12) # Move it to the new PSW

.Lihal_cls32_ret:
            tm     .LIEIB_run(0),.LIEIB_s390      # 31-bit capable?
            bno    .+8-0b(13)                     # ..no, Establish new PSW
            oi     .Lihal_cls32_nPSW+4(1),0x80    # Turn on 31-bit addressing

            la     12,.Lihal_cls32_nPSW_addr(8,9)  # Locate where to place the PSW
            cli    .Lihal_cls32_class(15),.LIH_pgm_cls  # Enabling program int?
            bne    .+10-0b(13)                    # ..no, just move the new PSW
            mvc    .Lihnpgm_PSW(8,0),.Lihal_cls32_nPSW(15)  # Set enabled pgm PSW

            mvc    0(8,12),.Lihal_cls32_nPSW(15)  # Enable/disable the interrupt
            return

  # +-------------------------------------+
  # |  32-bit INTERRUPT WAIT Abstraction  |
  # +-------------------------------------+ 
  # Access: public

  # Description
  # 
  # This abstract function performs an enabled wait for the set of I/O and/or
  # external interruption codes passed to the abstraction.  Following return 
  # to the abstraction by the abstract interrupt handler:
  #
  #   - registers 3-6 will contain the interruption information of the 
  #     interruption that terminated the wait
  # 
  # The abstraction will compare the interruption to the provided list.  If the 
  # interruption is found in the list, the abstraction will return to the caller 
  # with the information placed in the IIB previously passed to the abstraction
  # by its calledr.  Otherwise, the absraction will continue to wait.
  #
  # The first full word of the list of interruption codes contains the number of
  # interruption codes being waited upon.
  #
  # The following preset control registers dictate which interrupt soureces are
  # enabled for interruptions:
  #
  #    CR0 controls external interruptions,
  #    CR2 controls the channels that may cause I/O interruptions, and
  #    CR6 controls the subchannel classes that may cause I/O interruptions.
  #
  # Use the IH CLASS abstraction to manipulate these controls.
  #
  # On entry:
  #    R2     Pointer to IIB
  #    R3     Pointer to the list of I/O device ID's on which to wait
  #    R4     Pointer to the list of external interruption codes on which to wait
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R3     Interruption class (following wait)
  #    R4     Interruption code (following wait)
  #    R5     Interruption information - part 1 (following wait)
  #    R6     Interruption information - part 2 (following wait)
  #    R7     Active ASB 
  #
  # On exit: 
  #    IIB contains interrupt information following the wait

            func370 .Lihal_wait32

  # Local literal pool
.Lihal_wait32_31mask:
            .long  0x7FFFFFFF
.Lihal_wait32_extcls:
            .hword .LIH_ext_cls
.Lihal_wait32_iocls:
            .hword .LIH_io_cls

  # Local stack frame use
            fquad .Lihal_wait32_nPSW
            flong .Lihal_wait32_io
            flong .Lihal_wait32_ext

            push370

            l      7,.LIEIB_asb(0)               # Locate the active ASB
            mvi    .Lihal_wait32_nPSW(15),0x00   # Clear new PSW
            mvc    .Lihal_wait32_nPSW+1(7,15),.Lihal_wait32_nPSW(15)
            oc     .Lihal_wait32_nPSW+1(1,15),.LASB_fmtmsk(7) # Set PSW format
            ltr    3,3                           # Any I/O devices?
            bz     .+10-0b(13)                   # ..No, do not enable I/O
            oc     .Lihal_wait32_nPSW(2,15),.LASB_ioemsk(7) # ..Yes, enable I/O
            ltr    4,4                           # Any external interrupts?
            bz     .+10-0b(13)                   # ..No, do not enable external
            oc     .Lihal_wait32_nPSW(2,15),.LASB_exemsk(7) # ..Yes, enable external

            # Set up return address with correct addressing
            sr     8,8                           # Make sure high-order bits zero
            basr   8,0                           # Determine addressing mode
            n      8,.Lihal_wait32_31mask-0b(13) # High order bit set right
            la     8,.Lihal_wait32_here-0b(8,13) # Locate where wait ends
            st     8,.Lihal_wait32_nPSW+4(15)    # Save it in the PSW

            # Set up return with correct program mask
            lh     9,.LASB_ilcdis(7)             # Locate where ILC is in PSW
            la     9,.Lihal_wait32_nPSW(9,15)    # Locate where to store ILC
            balr   8,0                           # Get ILC, CC, PMSK in bits 0-8
            stcm   8,0b1000,0(9)                 # Place in PSW where they belong

            stm    3,4,.Lihal_wait32_io(15)      # Save input arguments
.Lihal_wait32_again:
            lpsw   .Lihal_wait32_nPSW(15)        # Now, actually wait
.Lihal_wait32_here:  # This is where control returns after the wait
            ch     3,.Lihal_wait32_iocls-0b(13)  # I/O interrupt?
            be     .Lihal_wait32_io-0b(13)       # ..yes, Process the I/O list
            ch     3,.Lihal_wait32_extcls-0b(13) # External interrupt?
            be     .Lihal_wait32_ext-0b(13)      # Process the external list
            halabort error=0x0010                # This should not occur

.Lihal_wait32_ext:
            l      9,.Lihal_wait32_ext(15)       # Locate the external list
            b      .Lihal_wait32_scan-0b(13)     # Scan the external list

.Lihal_wait32_io:
            l      9,.Lihal_wait32_io(15)        # Locate the I/O list

.Lihal_wait32_scan:
            icm    10,0b1111,0(9)                # Fetch the number of entries
            bc     0b0010,.+8-0b(13)             # If not negative or zero, cont.
            halabort error=0x0011
.Lihal_wait32_next:
            la     9,4(9)                        # Locate first or next entry
            cl     4,0(9)                        # Code we want?
            be     .Lihal_wait32_ret-0b(13)      # ..Yes, return from wait
            bct    10,.Lihal_wait32_next-0b(13)  # Any, more, check the next one
            b     .Lihal_wait32_again-0b(13)     # ..No, let's wait some more

.Lihal_wait32_ret:
            stm    3,6,.LIIB(2)                  # Save interrupt information
            return                               # Return to caller

.endif # .if .Lhal_32bit

.if .Lhal_64bit
            .eject
            .sbttl "Interrupt Hardware Abstraction Layer - 64-bit"

  # +---------------------------------------+
  # |  64-bit IH Handler Entry Logic Macro  |
  # +---------------------------------------+

 # ihentryg - Interrupt Handler entry following the interrupt mechanism
 #
 # Macro Parameters:
 #   name       The symbol associated with the abstract interrupt handler. This is
 #              the real interrupt handler that gets control when an interrupt
 #              new PSW becomes the current PSW. (required)
 #   opsw       Assigned storage location of the interrupt class' old PSW (required)
 #   ihcb       Symbol representing the assigned storage allocated for this class'
 #              Interrupt Handler Control Block. (required)
 #   ptrap      Trap PSW symbol for program trap within macro.  Only needed for 
 #              program interrupt class.  (optional)

            .macro ihentryg name:req cls:req opsw:req ihcb:req ptrap
            .align 2
\name:
            stmg   7,8,\ihcb+.LIHCB_sa(0)    # Temporarily save R7
            basr   8,0                       # Create a local base register
1:
    .ifnb \ptrap
            mvc    .LPSW_newpgmg(16,0),\ptrap-1b(8)  # Make sure pgm trapped within macro
    .endif
            larl   8,.Lihal_64base           # Setup global base register  
            lg     7,.Lihsag(0)              # Locate active save area
            ts     .LIHG_SR_state(7)         # Indicate save area has state
            brc    0b1000,.+8                # If save area not in use, good to go
            lpswe  .Lih_rec64-0b(8)          # Recursion! Die, immediately
            mvi    .LIHG_SR_class(7),\cls    # Indicate the class that owns the sa
            mvc    .LIHG_oPSW(16,7),\opsw(0) # Save the old PSW 
            stmg   0,15,.LIHG_GR(7)          # Interrupt programs GR0-GR14 saved
            mvc    .LIHG_R7(16,7),\ihcb+.LIHCB_sa(0)  # Now save R7 and R8
            lgr    2,7                       # Establish the save area pointer
            lghi   3,\cls                    # Establish the interruption class
            lghi   7,\ihcb                   # Establish IH control pointer
            lg     9,.LIEIB_asbg(0)          # Locate the ASB
            larl   10,.Lihal_func64          # Locate function routine
    .ifnb \ptrap
            mvc    .LPSW_newpgmg(16,0),.Lihnpgm_PSW(0)  # Make sure pgm re-enabled
    .endif
            .endm

.Lihal_64base:
0: # Base address for 64-bit interrupt handling
  # +----------------------------+
  # |  64-bit HAL IH - External  |
  # +----------------------------+

  # IH Entry
       ihentryg name=.Lih_ext64,cls=.LIH_ext_cls,opsw=.LPSW_oldextg,ihcb=.Lihext

  # IH Function Setup
            llgh   4,.LINT_extcode(0)       # R4 = external interruption code
            llgh   5,.LINT_extproc(0)       # R5 = external interruption processor
            llgf   6,.LINT_extparm(0)       # R6 = external interruption parameter
            j      .Lihal_ihwait64          # In-line wait

  # +--------------------------------+
  # |  64-bit HAL IH - Input/Output  |
  # +--------------------------------+

  # IH Entry
       ihentryg name=.Lih_io64,cls=.LIH_io_cls,opsw=.LPSW_oldiog,ihcb=.Lihio

  # IH Function Setup
            llgf   4,.LIO_ssid(0)             # R4 = device ID
            llgf   5,.LIO_intprm(0)           # R5 = I/O interruption parameter
            llgf   6,.LIO_intid(0)            # R6 = I/O interruption id
            j      .Lihal_ihwait64            # In-line wait

  # +---------------------------------+
  # |  64-bit HAL IH - Machine Check  |
  # +---------------------------------+

  # IH Entry
       ihentryg name=.Lih_mck64,cls=.LIH_mck_cls,opsw=.LPSW_oldmckg,ihcb=.Lihmck

  # IH Function Setup
            lg     4,.LINT_mckcode(0)         # R4 = machine check code
            j      .Lihal_func64              # Function call / restore / exit

  # +---------------------------+
  # |  64-bit HAL IH - Program  |
  # +---------------------------+

  # IH Entry
       ihentryg name=.Lih_pgm64,cls=.LIH_pgm_cls,opsw=.LPSW_oldpgmg,ihcb=.Lihpgm,ptrap=.Lih_prec64

  # IH Function Setup
            sr     6,6                        # Clear R6
            icm    6,0b0010,.LINT_pgmai(0)    # Bits 16-23 access id.
            ic     6,.LINT_pgmoi(0)           # Bits 24-31 operand access id.
            llgh   4,.LINT_pgmilc(0)          # R4 = program interruption code
            lgr    0,4                        # Get the code
            n      0,.Lihal_noPER-0b(8)       # Clear any possible PER code
            clm    0,0b0011,.Lihal_mon-0b(8)  # Monitor interruption?
            je     .Lihal_s390x_pgm_mon       # ..yes, handle monitor event
            clm    0,0b0011,.Lihal_data-0b(8) # Data exceptions?
            je     .Lihal_s390x_pgm_data      # ..yes, handle data exception
            lg     5,.LINT_pgmtrnx(0)         # Provide translation exception desc.
            br     10                         # Function call, restore, and exit

.Lihal_s390x_pgm_mon:
            llgh   5,.LINT_pgmmcls(0)         # R5 = program monitor class
            lg     6,.LINT_pgmmcdx(0)         # R6 = program monitor code
            br     10                         # Function call, restore, and exit

.Lihal_s390x_pgm_data:
            l      5,.LINT_pgmtran(0)         # R5 = translation / data id.
            br     10                         # Function call, restore, and exit

.Lihal_data: .hword  0x0007      # Data exception

  # +---------------------------+
  # |  64-bit HAL IH - Restart  |
  # +---------------------------+

  # IH Entry
       ihentryg name=.Lih_rst64,cls=.LIH_rst_cls,opsw=.LPSW_oldrstg,ihcb=.Lihrst

  # IH Function Setup
            j      .Lihal_func64              # Function call / restore / exit

  # +-----------------------------------+
  # |  64-bit HAL IH - Supervisor Call  |
  # +-----------------------------------+

  # IH Entry
       ihentryg name=.Lih_svc64,cls=.LIH_svc_cls,opsw=.LPSW_oldsvcg,ihcb=.Lihsvc

  # IH Function Setup
            llgh   4,.LINT_svccode(0)         # R4 = supervisor call code
            llgh   5,.LINT_svcilc(0)          # R5 = supervisor call ILC
            j      .Lihal_func64              # Function call / restore / exit

  # +------------------------------------+
  # |  64-bit HAL IH In-line Wait Logic  |
  # +------------------------------------+

.Lihal_ihwait64:
            tm     .LIHCB_flags(7),.LIHCB_wait   # In-line wait active?
            jno    .Lihal_func64_try             # ..no, setup for function call
            tm     .LIHG_oPSW+1(2),0x02          # Was this an in-line wait?
            jno    .Lihal_func64                 # ..No, setup for function call
            # Turn PSW into a running PSW with I/O interrupts disabled
            # following in-line wait
            nc     .LIHG_oPSW(2,2),.LASB_nowtmsk(9) # Disable interrupts and waiting
            stmg   3,6,.LIHG_R3(2)               # Return arguments to waiter
            j      .Lihal_exit64                 # Exit interrupt handling

  # +-------------------------------------------------+
  # |  64-bit HAL IH Function / Restore / Exit Logic  |
  # +-------------------------------------------------+

  # On Entry:
  #    R2      Program save area address
  #    R7      IHCB Pointer
  #    R10     Shared subroutine base address
  #
  # On Exit:
  #    All CPU state required to be restored has been restored
  #    Interrupt handling completed

.Lihal_func64:
  # Call the Interrupt Handler function
            tm      .LIHCB_flags(7),.LIHCB_func  # Function enabled for class?
            jz      .Lihal_func64_no_func     # Function not enabled
.Lihal_func64_try:
            icm     13,0b1111,.LIHCB_ihfg(7)  # R13 = IH Function
            jnz    .+8                        # Continue if function has been set
.Lihal_func64_no_func:
            lpswe  .Lih_nofunc64-0b(10)       # ..Die if no function
            oc     .LIHG_link(8,2),.LIHG_link(2)  # Are we already in Interrupt state?
            jnz    .+8                        # ..yes, use the stack pointer we have
            lg     15,.Lihstkg(0)             # R15 = interrupt stack pointer
            basr   14,13                      # Call the IH I/O Function
            # Note: R2 may contain a different save area

  # Exit interrupt handling
.Lihal_exit64:
            mvc    .Lihexit_PSW(16,0),.LIH_oPSW(2) # Setup old PSW for exit
            stg    2,.Lihsag(0)                    # Update the active save area
            mvi    .LIHG_SR_state(2),0x00          # Free up save area for next use
            lmg    0,15,.LIHG_GR(2)                # Restore CPU regs
            # All entry register content is now lost
            lpswe  .Lihexit_PSW(0)                 # Exit interrupt handling


  # +----------------------------------+
  # |  64-bit HAL IH Shared PSW Traps  |
  # +----------------------------------+

.Lih_prec64: # Program interrupt within abstract program interrupt handler
            s390xpsw s=0,p=0,a=0x006660

.Lih_rec64:  # Interrupt recursion detected 
            s390xpsw s=0,p=0,a=0x006662

.Lih_nofunc64: # No function set for enabled interrupt class
            s390xpsw s=0,p=0,a=0x006664

  # +------------------------------+
  # |  64-bit INIT IH Abstraction  |
  # +------------------------------+ 

  # On entry:
  #    R2     Interrupt handler stack bottom address
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used: None
  #
  # On exit: None

            functionx .Lihal_init64
            pushx

            framecrx stkr=2               # Calculate start of bottom frame
            stg    2,.Lihstkg(0)          # Establish the interrupt stack  

            returnx

  # +---------------------------------+
  # |  64-bit INIT IH SA Abstraction  |
  # +---------------------------------+ 

  # On entry:
  #    R2     Pointer to save area
  #    R3     Proposed save area controls
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R7     Active ASB 
  #
  # On exit: None

            functionx .Lihal_initsa64
            pushx

            mvi    0(2),0x00                    # Clear
            mvc    1(256,2),0(2)                # entire
            mvc    257(.LIHG_len-257,2),256(2)  # Save area

            returnx

  # +-------------------------------+
  # |  64-bit IH CLASS Abstraction  |
  # +-------------------------------+ 

  # On entry:
  #    R2     Interrupt class
  #    R3     Abstract interrupt handler function address when enalbing the class,
  #           zero when disabling the class
  #    R4     Interrupt mask (see below)
  #    R5     Additional interruption class parameter (see below)
  #    R13    Abstract function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R2     Address of the interrupt class IHCB entry
  #    R7     Build table index value
  #    R8     Interrupt class / pointer to internal enable/disable table
  #    R9     Build table address
  #    R10    Shared subroutine base address / or exit logic
  #    R11    Shared subroutine return address
  #    R12    Local work registers
  #
  # On exit:
  #    Interrupt class is enabled or disabled depending upon the arguments.
  #    If I/O or external interrupts are targeted by the call, the I/O or external
  #    interrupt will be disabled upon return.  The program must enable the 
  #    interrupt in the PSW when it is ready to use the interrupt function.
  #
  #  Interrupt Class
  #                          R4 Meaning
  #  Input/Output    C2 channel masks or C6 subclass masks
  #  External        C0 external masks
  #  Machine check   C14 machine check masks
  #
  #                          R5 Meaning
  #                                      In-line wait    Function
  #  Input/Output    R5 == 0 ==>           disabled      disabled
  #  and External    R5 == 1 ==>           enabled       disabled
  #                  R5 == 2 ==>           disabled      enabled
  #                  R5 == 3 ==>           enabled       enabled
  #  Machine check   on S/370, contains the machine check logout area

            functionx .Lihal_cls64

            struct  .Lihal_btbl64
            sbytes  .Lihal_btbl64_nPSW,24
            sbytes  .Lihal_btbl64_oPSW,24
            sbytes  .Lihal_btbl64_handlers,24

  # Build Table
.Lihal_cls64_nPSW_addr:
            .quad   .LPSW_newmck
            .quad   .LPSW_newext
            .quad   .LPSW_newio
            .quad   .LPSW_newsvc
            .quad   .LPSW_newrst
            .quad   .LPSW_newpgm
.Lihal_cls64_oPSW_addr:
            .quad   .LPSW_oldmck
            .quad   .LPSW_oldext
            .quad   .LPSW_oldio
            .quad   .LPSW_oldsvc
            .quad   .LPSW_oldrst
            .quad   .LPSW_oldpgm
.Lihal_cls64_handlers:
            .quad   .Lih_mck64
            .quad   .Lih_ext64
            .quad   .Lih_io64
            .quad   .Lih_svc64
            .quad   .Lih_rst64
            .quad   .Lih_pgm64

.Lihal_cls64_options:
            .quad    0x00000003             # Mask for options
.Lihal_cls64_max:
            .quad    0x14                   # Maximum valid class ID
.Lihal_cls64_extmask:
            .long    0x00000000,0x2000EE50
.Lihal_cls64_dis:
            .hword   0x0002,0x0001,0x1000,0x0000  # Bits 0-63 of enabled PSW
.Lihal_cls64_ena:
            .hword   0x0000,0x0001,0x1000,0x0000  # Bits 0-63 of enabled PSW

  # Local frame usage
            focta .Lihal_cls64_nPSW         # New PSW build area
            fquad .Lihal_cls64_cr           # control register load work area
            fbyte .Lihal_cls64_sm           # System mask stored here
            fbyte .Lihal_cls64_class        # Place to save the interrupt class
            fbyte .Lihal_cls64_enasm        # System mask to enable interrupt

            pushx

            lgr     8,2                         # Save ID for reference below

            lghi    0,0x3                       # Get mask
            ngr     0,2                         # Low-order bits zeros?
            bz     .+8-0b(13)                   # ..Yes, continue checks
            halabort error=0x000D               # Cause abort

            ltgr   2,2
            bnm    .+8-0b(13)                   # Id >= zero?
            halabort error=0x000E               # ..no, invalid value

            clg     2,.Lihal_cls64_max-0b(13)   # ID > 20?
            bnh    .+8-0b(13)                   # ..no, valid value, continue
            halabort error=0x000E               # ..yes, quit

            mghi   2,.LIHCB_len                 # Calculate displacement to IHCB
            la     2,.Lih_area(2,0)             # Return the address of the IHCB 
            # R2 now contains the address of the IHCB

            stc     8,.Lihal_cls64_class(15)    # Save the interrupt class

            la      9,.Lihal_cls64_nPSW_addr-0b(13)  # Locate the build table

            srlg    7,8,1                       # Create index for double words

    # Enable an interrupt class
            b       .+4-0b(8,13)            # Enable/Disable the interrupt class
            b       .Lihal_cls64_mck-0b(13) # Enable/Disable machine checks
            b       .Lihal_cls64_ext-0b(13) # Enable/Disable external interruptions
            b       .Lihal_cls64_io-0b(13)  # Enable/Disable I/O interruptions
            b       .Lihal_cls64_svc-0b(13) # Enable/Disable SVC interruptions
            b       .Lihal_cls64_rst-0b(13) # Enable/Disable restart interruptions
            b       .Lihal_cls64_pgm-0b(13) # Enable/Disable program interruptions

    # Enable Machine Checks
.Lihal_cls64_mck:
            # WARNING: Machine checks are assumed to be disabled before entry
            ltgr    3,3                           # Enabling or disabling?
            bz      .Lihal_cls64_dis_nPSW-0b(13)  # Disabling...

            # Set IHCB for machine-check interruptions
            stg     3,.LIHCB_ihfg(2)              # Set the IH Handler Function

            # Set control registers for machine checks
            stg     4,.Lihal_cls64_cr(15)         # Save C14 masks in frame
            lctlg   14,14,.Lihal_cls64_cr(15)     # Load into C14

            # Establish new PSW for enabled interrupts
            mvi     .LIHCB_flags(2),.LIHCB_func   # Enable the function
            b       .Lihal_cls64_ena_nPSW-0b(13)  # Build the enabling PSW, return

    # Enable/Disable External Interruptions
.Lihal_cls64_ext:

            stnsm   .Lihal_cls64_sm(15),0xFE      # Disable external interrupts 
            # Now safe to clear IHCB

            ng      5,.Lihal_cls64_options-0b(13) # Clear options
            bz      .Lihal_cls64_dis_nPSW-0b(13)  # Disable the interrupt class
            # We are enabling from this point forward

            # Set IHCB for external interrupts
            stc     5,.LIHCB_flags(2)             # Set the IHCB flags
            stg     3,.LIHCB_ihfg(2)              # Set the new IH function

            # Set control register for external interrupts
            ng      4,.Lihal_cls64_extmask-0b(13)# Turn off non external bits
            stctg   0,0,.Lihal_cls64_cr(15)       # Fetch C0 into storage
            lg      1,.Lihal_cls64_cr(15)         # Put it where I can touch it
            ogr     1,4                           # Turn on what was requested
            stg     1,.Lihal_cls64_cr(15)         # Put C0 back in storage
            lctlg   0,0,.Lihal_cls64_cr(15)       # Put new values in C0

            # Establish new PSW for enabled interrupts
            b       .Lihal_cls64_ena_nPSW-0b(13)  # Now build the new PSW

    # Enable Input/Output Interruptions
.Lihal_cls64_io:
            stnsm   .Lihal_cls64_sm(15),0x02      # Diable input/output interrupts

            ng      5,.Lihal_cls64_options-0b(13) # Clear options
            bz      .Lihal_cls64_dis_nPSW-0b(13)  # Disable the interrupt class
            # We are enabling from this point forward

            # Set IHCB for external interrupts
            stc     5,.LIHCB_flags(2)             # Set the IHCB flags
            stg     3,.LIHCB_ihfg(2)              # Set the new IH function

            # Set control register for input/output interrupts
            sllg    4,4,56                        # Position masks
            srlg    4,4,32                        # and clear high-order bits
            stg     4,.Lihal_cls64_cr(15)         # Put interrupts masks in storage
            lctlg   6,6,.Lihal_cls64_cr(15)       # Set I/O class masks
            b       .Lihal_cls64_ena_nPSW-0b(13)  # Now build the new PSW

    # Enable/disable Supervisor Call Interruptions
.Lihal_cls64_svc:
    # Enable/disable Restart Interruptions
.Lihal_cls64_rst:
    # Enable/disable Program Interruptions
.Lihal_cls64_pgm:

            ltr    3,3                           # Enabling or disabling?
            bz     .Lihal_cls64_dis_nPSW-0b(13)  # Disabling...

            # Set IHCB for interrupts
            mvi    .LIHCB_flags(2),.LIHCB_func   # Set the IHCB flags
            stg    3,.LIHCB_ihfg(2)              # Set the new IH function
            b      .Lihal_cls64_ena_nPSW-0b(13)

.Lihal_cls64_dis_nPSW:
            # Move bits 0-63 of new PSW to build area
            mvc    .Lihal_cls64_nPSW(4,15),.Lihal_cls64_dis-0b(13)
            la     12,.Lihal_btbl32_oPSW(7,9)     # Locate the old PSW address
            mvc    .Lihal_cls64_nPSW+4(8,15),0(12) # Set the disable wait address

            mvi    0(2),0x00                      # Clear the
            mvc    1(.LIHCB_len-1,2),0(2)         # ..entire IHCB
            b      .Lihal_cls64_ret-0b(13)        # Return to caller

.Lihal_cls64_ena_nPSW:
            # Move bits 0-63 of new PSW to build area
            mvc    .Lihal_cls64_nPSW(8,15),.Lihal_cls64_ena-0b(13)
            la     12,.Lihal_btbl32_handlers(7,9) # Locate the handler
            mvc    .Lihal_cls64_nPSW+8(8,15),0(12) # Move it to the new PSW

.Lihal_cls64_ret:
            la     12,.Lihal_cls64_nPSW_addr(7,9)  # Locate where to place the PSW
            cli    .Lihal_cls64_class(15),.LIH_pgm_cls  # Enabling program int?
            bne    .+10-0b(13)                    # ..no, just move the new PSW
            mvc    .Lihnpgm_PSW(16,0),.Lihal_cls64_nPSW(15)  # Set enabled pgm PSW

            mvc    0(8,12),.Lihal_cls64_nPSW(15)  # Enable/disable the interrupt
            returnx

  # +-------------------------------------+
  # |  64-bit INTERRUPT WAIT Abstraction  |
  # +-------------------------------------+ 
  # Access: public

  # Description
  # 
  # This abstract function performs an enabled wait for the set of I/O and/or
  # external interruption codes passed to the abstraction.  Following return 
  # to the abstraction by the abstract interrupt handler:
  #
  #   - registers 3-6 will contain the interruption information of the 
  #     interruption that terminated the wait
  # 
  # The abstraction will compare the interruption to the provided list.  If the 
  # interruption is found in the list, the abstraction will return to the caller 
  # with the information placed in the IIB previously passed to the abstraction
  # by its calledr.  Otherwise, the absraction will continue to wait.
  #
  # The first full word of the list of interruption codes contains the number of
  # interruption codes being waited upon.
  #
  # The following preset control registers dicated which interrupt soureces are
  # enabled for interruptions:
  #
  #    CR0 controls external interruptions,
  #    CR2 controls the channels that may cause I/O interruptions, and
  #    CR6 controls the subchannel classes that may cause I/O interruptions.
  #
  # Use the IH CLASS abstraction to manipulate these controls.
  #
  # On entry:
  #    R2     Pointer to IIB
  #    R3     Pointer to the list of I/O device ID's on which to wait
  #    R4     Pointer to the list of external interruption codes on which to wait
  #    R13    Function base address
  #    R14    Caller's return address
  #    R15    ABI Stack pointer
  #
  # Used:
  #    R3     Interruption class (following wait)
  #    R4     Interruption code (following wait)
  #    R5     Interruption information - part 1 (following wait)
  #    R6     Interruption information - part 2 (following wait)
  #    R7     Active ASB 
  #
  # On exit: 
  #    IIB contains interrupt information following the wait

            functionx .Lihal_wait64

  # Local literal pool
.Lihal_wait64_amask:
            .quad  0x0000000030000000
.Lihal_wait64_amode:
            .hword 0x0000  # 24-bit addressing
            .hword 0x0080  # 31-bit addressing
            .hword 0x0180  # 64-bit addressing

  # Local stack frame use
            focta .Lihal_wait64_nPSW
            fquad .Lihal_wait64_io
            fquad .Lihal_wait64_ext

            pushx

            l      7,.LIEIB_asbg(0)              # Locate the active ASB
            mvi    .Lihal_wait64_nPSW(15),0x00   # Clear new PSW
            mvc    .Lihal_wait64_nPSW+1(15,15),.Lihal_wait64_nPSW(15)
            ltgr    3,3                          # Any I/O devices?
            jz     .+8                           # ..No, do not enable I/O
            oi     .Lihal_wait64_nPSW(15),0x02   # ..Yes, enable I/O interrupts
            ltgr    4,4                          # Any external interrupts?
            jz     .+8                           # ..No, do not enable external
            oi     .Lihal_wait64_nPSW(15),0x01   # ..Yes, enable external ints.

            # Set up return address with correct addressing
            tam                  # Set cc based upon current addressing mode
            ipm    8             # Fetch the condition code (cc in bits 34,35)
            ng     8,.Lihal_wait64_amask-0b(13)  # Clear unused bits
            srlg   8,8,27        # Move cc to bits 61,62, zero in 63
            # R8 = AM (0==24-bit mode, 2==31-bit moe, 6==64-bit mode)
            la     8,.Lihal_wait64_amode-0b(8,13)  # Locate address mode for PSW
            mvc    .Lihal_wait64_nPSW+3(2,15),0(8) # Move it to PSW
            larl   8,.Lihal_wait64_here          # Locate where wait ends
            stg    8,.Lihal_wait64_nPSW+8(15)    # Save it in the PSW

            # Set up return with correct program mask
            balr   8,0                           # Get ILC, CC, PMSK in bits 0-8
            stcm   8,0b1000,.Lihal_wait64_nPSW+2(15)  # Place in PSW
            ni     .Lihal_wait64_nPSW+2,0x3F     # Make sure AS == 0

            stmg   3,4,.Lihal_wait64_io(15)      # Save input arguments
.Lihal_wait64_again:
            lpsw   .Lihal_wait32_nPSW(15)        # Now, actually wait
.Lihal_wait64_here:  # This is where control returns after the wait
            cghi   3,.LIH_io_cls                 # I/O interrupt?
            je     .Lihal_wait32_io              # ..yes, Process the I/O list
            cghi   3,.LIH_ext_cls                # External interrupt?
            je     .Lihal_wait64_ext             # Process the external list
            halabort error=0x0010                # This should not occur

.Lihal_wait64_ext:
            lg     9,.Lihal_wait64_ext(15)       # Locate the external list
            j      .Lihal_wait64_scan            # Scan the external list

.Lihal_wait64_io:
            lg     9,.Lihal_wait64_io(15)        # Locate the I/O list

.Lihal_wait64_scan:
            llgf   10,0(9)                       # Fetch the number of entries
            ltgr   10,10                         # Is number >0
            brc    0b0010,.+8                    # If not negative or zero, cont.
            halabort error=0x0011
.Lihal_wait64_next:
            la     9,4(9)                        # Locate first or next entry
            cl     4,0(9)                        # Code we want?
            je     .Lihal_wait64_ret             # ..Yes, return from wait
            brct   10,.Lihal_wait64_next         # Any, more, check the next one
            j      .Lihal_wait64_again           # ..No, let's wait some more

.Lihal_wait64_ret:
            stmg   3,6,.LIIBG(2)                 # Save interrupt information
            returnx                              # Return to caller


.endif # .if .Lhal_64bit

.Lihal_noPER: .long  0x0000FF7F  # Remove possible PER code
.Lihal_mon:   .hword 0x0040      # Monitor event program interruption code

.endif # .ifndef .Lihal_S scope
