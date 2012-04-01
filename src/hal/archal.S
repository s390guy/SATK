.ifndef .Lprobe_S
.Lprobe_S = 1

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

 # This module provides support for the detection of the running architecture and 
 # architecture related functions. 
 # 
 # Underlying platform detection and creation of the IPL Environment Initialization 
 # Block (IEIB), starting at real storage location 0x250, is provided by the 
 # architecture initializaiton functions in hal.S.
 #
 # The logic in this module is called by means of a BRANCH AND SAVE instruction
 # in the probe or setarch macro's found in IEIB.S.  For considerations on using 
 # this module and either the probe or setarch macros, see IEIB.S.

 #  +----------------------+
 #  |  Main storage Usage  |
 #  +----------------------+
 #
 #   000000-0001FF  - Assigned Storage Locations

           .nolist
           .include "psw.S"        # PSW's and PSW assigned storage locations 
           .list

  # +-----------------------------------------+
  # |  Running Architecture Probe Subroutine  |
  # +-----------------------------------------+ 

  # This subroutine is called by means of the probe macro in IEIB.S.  If an 
  # architecture is detected that is unsupported by the program is or not enabled by 
  # the hal macro, the probe routine will enter a disabled wait state.  The 
  # instruction address of the PSW will indicate the unsupported architecture:
  #
  #   IA    Unsupported architecture
  #
  #  0x360  System/370 in basic control mode
  #  0x370  System/370 in extended control mode
  #  0x390  ESA/390
  #  0x900  z/Architecture

  # +-----------------------------------+
  # |  Detect the running architecture  |
  # +-----------------------------------+

  # The SVC instruction will cause a cascade of interruptions that results in the
  # detection of the running architecture and the following actions to be taken:
  #
  # If z/Architecture, the new 128-bit SVC SW at 0x1C0 passes control to... 
  # "z/Architecture Detected".  The architecture mode will be forced back to 
  # ESA/390 and control will be passed to...
  # "ESA/390 Capability Analysis"
  #
  # If ESA/390, the new 64-bit SVC PSW at 0x60 passes control to... 
  # "ESA/390 Capability Analysis"
  #
  # If System/370 EC-mode, the new 64-bit SVC PSW causes a program interruption
  # because it has 31-bit addressing set (valid for ESA/390, but not System/370).
  # The new 64-bit program PSW at 0x68 then causes control to pass to... 
  # "System/370 detected" where it will recognize the extended control mode and
  # pass control ultimately to... 
  # "System/370 Extended Control Mode Capability Analysis"
  # 
  # If System/370 BC-mode, the new 64-bit SVC PSW causes a program interruption
  # because it has 31-bit addressing set (valid for ESA/390, but not System/370).
  # The new 64-bit program PSW at 0x68 then causes control to pass to... 
  # "System/370 detected" where it will recognize the basic control mode from the
  # presence of the interruption code in the old SVC PSW and pass control 
  # ultimately to... 
  # "System/370 Basic Control Mode Capability Analysis"

            .align 2
.Lhal_arch_probe:
            mvc    .Lhal_psv_npgm-0b(8,13),.LPSW_newpgm    # Save LOWC trap pgm PSW
            mvc    .Lhal_psv_s390-0b(8,13),.LPSW_newsvc    # Save LOWC trap svc PSW
            mvc    .Lhal_psv_s390x-0b(16,13),.LPSW_newsvcg # Save LOWC trap svc PSW
            mvc    .LPSW_newsvcg(16,0),.Lck_s390x-0b(13)   # Set new z SVC PSW
            mvc    .LPSW_newsvc(8,0),.Lck_s390-0b(13)      # Set new ESA/390 SVC PSW
            mvc    .LPSW_newpgm(8,0),.Lck_s370-00b(13)     # Set new S/370 pgm PSW
            svc    0xFF  # Issue the SVC (can't be zero for S/370 BC mode detection)

 # Unsupported architecture PSW's
             .align 8
.Lhal_s370bc_dead:
            s370pswbc  s=0x0002,p=0,a=0x360
.Lhal_s370_dead:
            s370psw    s=0x0002,p=0,a=0x370
.Lhal_s390_dead:
            s390psw    s=0x0002,p=0,a=0x390
.Lhal_s390x_dead:
            s390xpsw   s=0x0002,p=0,a=0x900

 # Architecture detection PSW's
.Lck_s370:  s370psw    s=0,p=0,a=.Lhal_is_s370      # S/370 new pgm PSW
.Lck_s390:  s390psw    s=0,p=0,a=.Lhal_is_s390      # ESA/390 new svc PSW
.Lck_s390x: s390xpsw24 s=0,p=0,a=.Lhal_is_s390x     # z/Architecture new svc PSW

  # +-----------------------+
  # |  System/370 detected  |
  # +-----------------------+ 

  # Entry status: System/370 Extended Control Mode, 24-bit addressing
  #               From the new program interuption PSW triggered by attempt to load 
  #               the ESA/390 31-bit addressing mode SVC PSW (from SVC)      

            .align 2
.Lhal_is_s370:  # Determine which S/370 mode we were in
            # If the old PSW has a code, we were in basic control mode
            oc     .LPSW_oldsvc+2(2,0),.LPSW_oldsvc+2(0)
            bnz    .Lhal_is_s370bc-0b(13)  # ..Yes, this means BC-mode
            b      .Lhal_is_s370ec-0b(13)  # ..No, truly in EC-mode

  # +------------------------------------------+
  # |  System/370 Basic Control Mode Detected  |
  # +------------------------------------------+       

  # Entry Status: System/370 Extended Control Mode, 24-bit addressing
  #               Same status as in "System/370 Detected"

            .align 2
.Lhal_is_s370bc:
.if .Lhal_s370bc
            cli   0(14),0x00           # Is S/370 BC mode supported?
            be    .Lhal_s370bc_bad-0b(13)      # ..No, do disabled wait state
            bas   11,.Lhal_reset_traps-0b(13)  # Reset trap PSW's

            # The primary impact of the mode in which the System/370 system is
            # running is how interruptions are communicated to the program.  If 
            # the old PSW indicates the basic control mode, then the interruption
            # code is placed in bytes 2 and 3 of the old PSW.  Control is here
            # because we were running in System/370 basic control mode before the
            # architecture detection process.  However, the program new PSW 
            # actually puts us into EC, the S/370 EC mode and ESA/390 PSW formats
            # being the same.  So, we need to return to BC mode.  We will do that by 
            # introducing a new PSW and continue with the analysis.

            lpsw   .Lretbc-0b(13)                  # Continue analysis in BC mode
            .align 8
.Lretbc:    s370pswbc  s=0,p=0,a=.Lretbcmode       # Return to S/370 BC mode
.Lretbcmode: # Symbol for the PSW that returns us to BC mode

            # Make sure program interrupts keep us in BC mode and we do not slip
            # into EC-mode during a detection activity that depends upon program
            # interrupts.
            b      0(14)                           # Return to caller

.Lhal_s370bc_bad:
.endif # .if .Lhal_s370bc scope
            lpsw   .Lhal_s370bc_dead-0b(13)

  # +---------------------------------------------+
  # |  System/370 Extended Control Mode Detected  |
  # +---------------------------------------------+

  # Entry Status: System/370 Extended Control Mode, 24-bit addressing

            .align 2
.Lhal_is_s370ec:
.if .Lhal_s370
            cli    4(14),0x00                     # Is S/370 EC mode supported?
            be     .Lhal_s370ec_bad-0b(13)        # ..Yes, quit
            bas    11,.Lhal_reset_traps-0b(13)    # Reset trap PSW's
            b      4(14)                          # Return to caller

.Lhal_s370ec_bad:
.endif # .if .Lhal_s370 scope
            lpsw   .Lhal_s370_dead-0b(13)         # DIE!

  # +--------------------+
  # |  ESA/390 Detected  |
  # +--------------------+ 

  # Entry Status: ESA/390 Mode, 31-bit addressing (from new SVC PSW)

            .align 2
.Lhal_is_s390:
.if .Lhal_s390
            cli    8(14),0x00                     # Is s390 supported?
            be     .Lhal_s390_bad-0b(13)          # ..No, quit
            sam24                                 # ..Yes, set AMODE=24
            bas    11,.Lhal_reset_traps-0b(13)    # Reset trap PSW's
            b      8(14)                          # Return to caller

.Lhal_s390_bad:
.endif # .if .Lhal_s390 scope
            lpsw   .Lhal_s390_dead-0b(13)         # DIE!

  # +---------------------------+
  # |  z/Architecture detected  |
  # +---------------------------+ 

 # Entry status: z/Architectrure Mode, addressing mode unknown (from restart)

 # z/Architecture mode is impossible immediately following an IPL.  However, if the
 # program calls the detection logic immediately after enabling z/Architecture,
 # this logic will detect it.  Of course, if the program has done that, it has
 # no need of the probe logic.
 #
 # One case does exist where z/Architecture mode is the state upon program entry.
 # If Hercules is 
 #    1. configured for z/Architecture mode 
 #    2. a program is manually loaded into storage with a restart PSW and
 #    3. a manual restart is performed, 
 # the CPU will be in z/Architecture mode on entry.  In this scenario, no IPL 
 # device will be available because an IPL did not occur.  
 #
 # To use this approach, the following statements in a Hercules rc file will 
 # achieve it:
 #     archmode z/Arch
 #     loadcore /path/to/program 2000
 #     r 01A0=00000000
 #     r 01A4=00000000
 #     r 01A8=00000000
 #     r 01AC=00002080
 #     restart
 #
 # These statements assume that a s390x ELF has been loaded at location 0x2000.
 # The entry point would then be 0x2080, allowing for the ELF header information.
 #
            .align 2
.Lhal_is_s390x: 
.if .Lhal_s390x
            cli    12(14),0x00                 # Is z/Architecture supported?
            be     .Lhal_s390x_bad-0b(13)      # ..No, quit
            bas    11,.Lhal_reset_traps-0b(13) # Reset trap PSW's
            b      12(14)                      # ..Yes, return to caller

.Lhal_s390x_bad:
.endif # .if .Lhal_s390x scope
            lpsw   .Lhal_s390x_dead-0b(13)     # DIE!

  # +------------------------------------------------------------+
  # |  Reset trap PSW's following architecture probe Subroutine  |
  # +------------------------------------------------------------+

            .align 2
.Lhal_reset_traps:
            mvc    .LPSW_newpgm(8,0),.Lhal_psv_npgm-0b(13)    # Restore new PGM PSW 
            mvc    .LPSW_newsvc(8,0),.Lhal_psv_s390-0b(13)    # Restore new svc PSW
            mvc    .LPSW_newsvcg(16,0),.Lhal_psv_s390x-0b(13) # Restore new svc PSW
            br     11                                         # Return to caller

  # +-------------------------------+
  # |  Set Architecture Subroutine  |
  # +-------------------------------+

  # This subroutine is called by means of the setarch macro in IEIB.S.

  # On entry:
  #    R0     Requested architecture ( 0==ESA/390, 1==z/Architecture, 37==S/370 )
  #    R11    Caller's return address
  #    R13    Caller's base register (assumed to be equal to 0b)
  #    R14    Caller's return address
  #
  # Used:
  #    R1     New IEIB values
  #    R6-R8  SIGNAL PROCESSOR Instruction
  #    R9     Analysis of SIGNAL PROCESSOR status (returned in R6)
  #    R10    Local subroutine base register (assumed to be 1b, not 0b)
  #    R11    IEIB architecture values
  #
  # On exit:
  #    R13-R15 preserved
  #    CPU is running in the requested architecture
  #
  # Disabled Wait States:
  #   
  #    IA      Meaning
  #  00abad    Failed to enter valid requested architecture (see R6 for status)
  #  37abad    On Hercules, SIGP_SETARCH_S370 facility has not been enabled.
  #            On other platforms, 37abad is an invalid reqested architecture.
  #  XXabad    Invalid requested architecture.  XX are the eight low-order R0 bits
  #
           .align 2
.Lhal_set_arch:
            basr   10,0
1:
            ch     0,.Lhal_set_arch_parm_s390x-1b(10) # z/Architecture requested?
            be     .Lhal_set_arch_try-1b(10)     # ..yes, try and change the arch
            ch     0,.Lhal_set_arch_parm_s390-1b(10)  # ESA/390 requested?
            be     .Lhal_set_arch_try-1b(10)     # ..yes, try and change the arch
            ch     0,.Lhal_set_arch_parm_s370-1b(10)  # S/370 on Hercules requested?
            be     .Lhal_set_arch_try-1b(10)     # ..yes, try it
            b      .Lhal_set_arch_bad_arch-1b(10)     # ..no, bad request, die
.Lhal_set_arch_try:
            sth    0,.Lhal_set_arch_parm-1b(10)  # Set parameter (from setarch)
            stap   .Lhal_set_arch_cpu-1b(10)     # Save my CPU address
            lm     6,8,.Lhal_set_arch_parms-1b(10)  # Load up SIGP parms
.Lhal_set_arch_retry:
            sigp   6,8,0x12             # Signal myself to change architecture
            bcr    0b1000,11                             # Order accepted
            bc     0b0001,.Lhal_set_arch_fail-1b(10)     # Failed...
            bc     0b0010,.Lhal_set_arch_retry-1b(10)    # ..busy, try again
      # CC==1: Status stored, order not accepted
            lr     9,6                  # Inspect the status
            n      9,.Lhal_set_arch_invalid-1b(10)  # Invalid parameter?
            # The parameter is invalid if:
            #   1.  the parameter value is invalid
            #   2.  or the CPU is already in the requested architecture
            # The parameter was validated above, so the CPU must already be in
            # the requested architecture.
            bnzr    11
.Lhal_set_arch_bad_arch:
            stc    0,.Lhal_set_arch_psw+5-1b(10) # Set requested arch in PSW
.Lhal_set_arch_fail:
            lpsw   .Lhal_set_arch_psw-1b(10)     # Something else went wrong, DIE!

            .align 8
.Lhal_set_arch_psw:
            s370psw s=0x0002,p=0,a=0xabad    # Disabled wait PSW
.Lhal_set_arch_parms:
           .long   0xFFFFFFFF # R6 = status following SIGNAL PROCESSOR (set to -1)
           .hword  0          # R7 = SIGNAL PROCESSOR parameter
.Lhal_set_arch_parm:
           .hword  0
           .hword  0          # R8
.Lhal_set_arch_cpu:           
           .hword  0          # R6 = CPU address (low-order 16 bits of register)
.Lhal_set_arch_invalid:
           .long   0x00000100 # Invalid parameter status
.Lhal_set_arch_parm_s390:
           .hword  0          # SIGNAL PROCESSOR parameter for ESA/390
.Lhal_set_arch_parm_s390x:
           .hword  1          # SIGNAL PROCESSOR parameter for z/Architecture
.Lhal_set_arch_parm_s370:
           .hword  37         # SIGNAL PROCESSOR parameter for S/370 (Hercules only)

  # +----------------------------------+
  # |  Storage Areas Used by archal.S  |
  # +----------------------------------+

             .align 8
 # These locations are used to preserve the content of the assigned storage 
 # used in architecture detection process.

.Lhal_psv_npgm: .quad  0   # Save area for 32-bit archs new pgm trap PSW
.Lhal_psv_s390: .quad  0   # Save area for ESA/390 new SVC PSW during arch detection
.Lhal_psv_s390x:.octa  0   # Save area for z/Architecture new SVC PSW

 # IEIB Architecture Default Fields  
 #                      .LIEIB_run,   .LIEIB_avl
.Lhal_saib_s370: .byte  .LIEIB_s370,  .LIEIB_s370|.LIEIB_s370bc
.Lhal_saib_s390: .byte  .LIEIB_s390,  .LIEIB_s390
.Lhal_saib_s390x:.byte  .LIEIB_s390x, .LIEIB_s390|.LIEIB_s390x

.else
            .error "probe.S suppressed due to missing hal macro options"
.endif # ifdef .Lhal_options scope

.endif # ifndef .Lprobe_S scope
