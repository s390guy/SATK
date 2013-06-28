.ifndef .Lihsave_S
.Lihsave_S = 1
 # Copyright (C) 2013 Harold Grovesteen
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

 # This module is a companion to the ihandler.S module.  The ihandler.S module is
 # focused on basic interrupt handler entry and exit.  Saving the minimal amount of
 # the interrupted program's state in the CPU prefix area and creating an ABI
 # execution environment from within the handler.
 #
 # This module, ihsave.S, is focused strictly on managing more advanced CPU state
 # management.
 #
 # Structures .LIH and .LIH64 define the save area.  Different sizes make sense
 # for different architecture levels.  The macros provided here depend upon the
 # the ihandler.S ihandler_define[64] macros and .LIHS[64] structures.

 # Dependencies:
        .include "ihandler.S" # Structure definitions needed (.LIHS and .LIHS64)
        .include "psw.S"      # for PSW generation macros
        .include "struct.S"   # for structure specification macros

 # The following macros are provided by this module:
 #
 #   Macro                   Description
 #   ihsgbl       Defines two global symbols based upon an explicit architecture
 #                level or architecture defined by a psw_arch macro.
 #   ihsdrst      Restores 32-bit CPU state per run time controls (see .LIH)
 #   ihsdrstg     Restores 64-bit CPU state per run time controls (see .LIHG)
 #   ihsdsav      Save 32-bit CPU state per run time controls (see .LIH)
 #   ihsdave      Save 64-bit CPU state per run time controls (see .LIHG)
 #   ihsrst       Restores saved CPU state from a 32-bit save area (see .LIH).
 #   ihsrstg      Restores saved CPU state from a 64-bit save area (see .LIHG).
 #   ihssav       Saves into a 32-bit save area (see .LIH) required CPU state.
 #   ihssavg      Saves into a 64-bit save area (see .LIHG) required CPU state.
 #
 #   The ihrst[g] an ihssav[g] provide the optimal save/restore logic with no
 #   run time flexibility for the system.  The ihdrst[g] and ihdsave[g] provide 
 #   the maximum run-time flexibility at the cost of the speed.  Unless there is 
 #   a strong need for run-time flexibility, the global ihrst[g] and ihsav[g] 
 #   macros are recommended. 

 # +-----------------------------------------------+
 # |  Interrupt Handler Save Area Global Controls  |
 # +-----------------------------------------------+

 # ihsgbl - Define global symbols for save area controls.
 #            .LIHSLVL - the architecture level in use
 #            .LIHSGBL - the global controls applied to the CPU state
 #            .LIHSIZE - the save area size in bytes used by the architecture level
 #          These values may be used within macros or defined in a structure.  When
 #          allocating a save area use:
 #             sbytes .Lsarea,.LIHSIZE within a structure
 #             fbytes .Lsarea,.LIHSIZE within a local stack frame 
 #
 #  Macro Parameters:
 #       level    Architecture level supported by save area.  This value determines
 #                the size of the save area.
 #                   0  for S/360 or S/370 BC-mode
 #                   1  for S/370 EC-mode
 #                   2  for S/390 or
 #                   3  for z/Architecture
 #                If omitted, level is inferred from the current psw_arch setting.
 #       control  Specifies the controls to be used by the architecture level.  If
 #                omitted, the default for the identified architecture level are
 #                used.
 #
 #       Each of the following parameters modify the controls.  Specify 'yes' to
 #       force saving of the CPU state.  Specify 'no' to disable saving of the CPU
 #       state.  All are optional:
 #
 #       cr       Override control register controls
 #       ar       Override access register controls
 #       fp       Override additional floating point controls
 #       afp      Override additional floating point controls
 #       fpc      Override floating point controls

        .macro ihsgbl level control cr ar fp afp fpc
    .ifnb \level        # level is specified.  Check for valid values.
       .ifeq \level
.LIHSLVL = 0
.LIHSIZE = .LIH_s360_len
       .else
         .ifeq \level-1
.LIHSLVL = 1
.LIHSIZE = .LIH_s370_len
         .else
            .ifeq \level-2
.LIHSLVL = 2
.LIHSIZE = .LIH_len
            .else
                .ifeq \level-3
.LIHSLVL = 3
.LIHSIZE = .LIHG_len
                .else
        .error "ihsave.S: ihsgbl macro: level argument not between 0-3"
                .endif # End of .ifeq \level-3
            .endif # End of .ifeq \level-2
         .endif # End of .ifeq \level-1
       .endif # End of .ifeq \level
    .else               # level not specified.  Infer it from psw_arch values.
.LIHSLVL = .L__psw_arch # architecture level values use the same ones as psw_arch.
    .endif # End of .ifnb \level
    .ifnb \control         # If control specified use it
.LIHSGBL = \control
    .else                  # Overwise set the default for the architecture level
         .ifeq .LIHSLVL    # If level is 0
.LIHSGBL = .LIHSR_S370bc   # then set the default controls for S/370 BC-mode
.LIHSVALID = .LIHSR_L0
        .else
           .ifeq .LIHSLVL-1  # If level is 1
.LIHSGBL = .LIHSR_S370       # then set the default controls for s/370 EC-mode
.LIHSVALID = .LIHSR_L1
           .else
               .ifeq .LIHSLVL-2  # If level is 2
.LIHSGBL = .LIHSR_ESA390         # then set the default controls for ESA/390
.LIHSVALID = .LIHSR_L2
               .else             # otherwise
.LIHSGBL = .LIHSR_zarch          # Assume we are using z/Architecture
.LIHSVALID = .LIHSR_L3
               .endif # End of .ifeq .LIHSLVL-2
           .endif # End of.ifeq .LIHSLVL-1
        .endif # End of .ifeq \.LIHSLVL
    .endif # End of .ifnb \control
    .ifnb \cr      # If cr was specified
        .ifc \cr,yes
.LIHSGBL = .LIHSGBL | (.LIHSVALID & .LIHSR_CR)   # Enable controls registers
        .else
.LIHSGBL = .LIHSGBL & ( ~.LIHSR_CR)
        .endif  # End of .ifc \cr,yes
    .endif # End of .ifnb \cr
    .ifnb \fp      # If fp was specified
        .ifc \fp,yes
.LIHSGBL = .LIHSGBL | (.LIHSVALID & .LIHSR_FP)   # Enable controls registers
        .else
.LIHSGBL = .LIHSGBL & ( ~.LIHSR_FP)
        .endif  # End of .ifc \cr,yes
    .endif # End of .ifnb \fp
    .ifnb \afp      # If afp was specified
        .ifc \afp,yes
.LIHSGBL = .LIHSGBL | (.LIHSVALID & .LIHSR_AFP)   # Enable controls registers
        .else
.LIHSGBL = .LIHSGBL & ( ~.LIHSR_AFP)
        .endif  # End of .ifc \afp,yes
    .endif # End of .ifnb \afp
    .ifnb \fpc      # If fpc was specified
        .ifc \fpc,yes
.LIHSGBL = .LIHSGBL | (.LIHSVALID & .LIHSR_FPC)   # Enable controls registers
        .else
.LIHSGBL = .LIHSGBL & ( ~.LIHSR_FPC)
        .endif  # End of .ifc \fpc,yes
    .endif # End of .ifnb \afp   
        .endm

 # ihsdrst   - Restore 32-bit CPU state per run time controls
 # ihsdrstg  - Restore 64-bit CPU state per run time controls
 #
 #  Macro Parameters:
 #    handler  Symbol used identifying the ihandler.S defined interrupt handler
 #             (required)
 #    sa       A symbol identifying the start of the save area (required)
 #    error    A symbol to which control is passed if an error detected. (required)
 #    sar      The base register for the symbol used in the 'sa' parameter
 #             (default to 15, the local stack)
 #    br       Specified the local base register (defaults to 13)
 #    b        Specifies the local base (defaults to 0b)
 #
 # WARNING: Restoration of control registers may require additional logic before
 # exiting the interrupt handler. 

        .macro ihsdrst handler:req sa:req error:req sar=15 br=13 b=0b
        tm    \sa+.LIH_SR_state,.LIHSR_pres       # Any state present?
        bno   \error-\b(\br)                      # ..No, Now that is a problem!
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_AR   # Restoring AR's?
        bno   .+(2*4)-\b(\br)                     # ..No, skip restore
        lam   0,15,\sa+.LIH_AR                       # Restore CPU AR's
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_AFP  # Restoring additional FP reg.?
        bno   .+(13*4)-\b(\br)                    # ..No, skip restore
        ld    1,\sa+.LIH_F1(\sar)                     # Restore CPU FP1
        ld    3,\sa+.LIH_F3(\sar)                     # Restore CPU FP3
        ld    5,\sa+.LIH_F5(\sar)                     # Restore CPU FP5
        ld    7,\sa+.LIH_F7(\sar)                     # Restore CPU FP7
        ld    8,\sa+.LIH_F8(\sar)                     # Restore CPU FP8
        ld    9,\sa+.LIH_F9(\sar)                     # Restore CPU FP9
        ld    10,\sa+.LIH_F10(\sar)                   # Restore CPU FP10
        ld    11,\sa+.LIH_F11(\sar)                   # Restore CPU FP11
        ld    12,\sa+.LIH_F12(\sar)                   # Restore CPU FP12
        ld    13,\sa+.LIH_F13(\sar)                   # Restore CPU FP13
        ld    14,\sa+.LIH_F14(\sar)                   # Restore CPU FP14
        ld    15,\sa+.LIH_F15(\sar)                   # Restore CPU FP15
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_FPC   # Restoring FP control reg?
        bno   .+(2*4)-\b(\br)                      # ..No, skip restore
        lfpc \sa+.LIH_FPC(\sar)                        # Restore CPU FP control
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_FP    # Restoring base FP regs?
        bno   .+(5*4)-\b(\br)                      # ..No, skip restore
        ld    0,\sa+.LIH_F0(\sar)                     # Restore CPU FP0
        ld    2,\sa+.LIH_F2(\sar)                     # Restore CPU FP2
        ld    4,\sa+.LIH_F4(\sar)                     # Restore CPU FP4
        ld    6,\sa+.LIH_F6(\sar)                     # Restore CPU FP6
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_CR    # Restoring control regs?
        bno   .+(2*4)-\b(\br)                      # ..No, skip restore
        lctl  0,15,\sa+.LIH_CR(\sar)                  # Restore CPU CR's
        mvc    \handler()_sa(16*4,0),\sa+.LIH_GR(16*4,\sar) # Restore GRs to prefix
        mvc    \handler\()_opsw(8,0),\sa+.LIH_oPSW(8,\sar)  # Restore old PSW
        ni     \sa+.LIH_SR_state(\sar),0xFF & .LIHSR_pres    # Indidate no state
       .endm
     
        .macro ihsdrstg sa:req handler:req error:req sar=15 br=13 b=0b
        tm    \sa+.LIH_SR_state,.LIHSR_pres        # Any state present?
        jno   \error                               # ..No, Now that is a problem!
        tm    \sa+.LIHG_SR_flags(\sar),.LIHSR_AR   # Restoring AR's?
        bno   .+(2*4)-\b(\br)                      # ..No, skip restore
        lam   0,15,\sa+.LIHG_AR                       # Restore CPU AR's
        tm    \sa+.LIHG_SR_flags(\sar),.LIHSR_AFP  # Restoring additional FP reg.?
        jno   .+(13*4)                             # ..No, skip restore
        ld    1,\sa+.LIHG_F1(\sar)                    # Restore CPU FP1
        ld    3,\sa+.LIHG_F3(\sar)                    # Restore CPU FP3
        ld    5,\sa+.LIHG_F5(\sar)                    # Restore CPU FP5
        ld    7,\sa+.LIHG_F7(\sar)                    # Restore CPU FP7
        ld    8,\sa+.LIHG_F8(\sar)                    # Restore CPU FP8
        ld    9,\sa+.LIHG_F9(\sar)                    # Restore CPU FP9
        ld    10,\sa+.LIHG_F10(\sar)                  # Restore CPU FP10
        ld    11,\sa+.LIHG_F11(\sar)                  # Restore CPU FP11
        ld    12,\sa+.LIHG_F12(\sar)                  # Restore CPU FP12
        ld    13,\sa+.LIHG_F13(\sar)                  # Restore CPU FP13
        ld    14,\sa+.LIHG_F14(\sar)                  # Restore CPU FP14
        ld    15,\sa+.LIHG_F15(\sar)                  # Restore CPU FP15
        tm    \sa+.LIHG_SR_flags(\sar),.LIHSR_FPC  # Restoring FP control reg?
        jno   .+(2*4)                                 # ..No, skip restore
        lfpc \sa+.LIHG_FPC(\sar)                      # Restore CPU FP control
        tm    \sa+.LIHG_SR_flags(\sar),.LIHSR_FP   # Restoring base FP regs?
        jno   .+(5*4)                              # ..No, skip restore
        ld    0,\sa+.LIHG_F0(\sar)                    # Restore CPU FP0
        ld    2,\sa+.LIHG_F2(\sar)                    # Restore CPU FP2
        ld    4,\sa+.LIHG_F4(\sar)                    # Restore CPU FP4
        ld    6,\sa+.LIHG_F6(\sar)                    # Restore CPU FP6
        tm    \sa+.LIH_SR_flags(\sar),.LIHSR_CR    # Restoring control regs?
        jno   .+(2*4)                              # ..No, skip restore
        lctlg  0,15,\sa+.LIH_CR(\sar)                 # Restore CPU CR's
        mvc    \handler()_sa64(16*8,0),\sa+.LIHG_GR(16*4,\sar) # Restore GRs to pfx
        mvc    \handler\()_opsw64(16,0),\sa+.LIHG_oPSW(8,\sar) # Restore old PSW
        ni     \sa+LIHG_SR_state(\sar),0xFF ^ .LIHSR_pres      # Indidate no state
        .endm
     
 # ihsdsav   - Save 32-bit CPU state per run time controls
 # ihsdsavg   - Save 64-bit CPU state per run time controls
 #
 #  Macro Parameters:
 #    handler  Symbol used identifying the ihandler.S defined interrupt handler
 #             (required)
 #    sa       A symbol identifying the start of the save area (required)
 #    ctrl     Symbol locating the dynamic control in place (required)
 #    ctrlr    Base register for 'ctrl' symbol (Defaults to 15, the local stack)
 #    sar      The base register for the symbol used in the 'sa' parameter
 #             (default to 15, the local stack)
 #    br       Specified the local base register (defaults to 13)
 #    b        Specifies the local base (defaults to 0b)
  
        .macro ihsdsav handler:req sa:req ctrl:req ctrlr=15 sar=15 br=13 b=0b
        mvc    \sa+.LIH_oPSW(8,\sar),\handler\()_opsw   # Save prefix OLD PSW
        mvc    \sa+.LIH_GR(16*4,\sar),\handler()_sa     # Save prefix area GR's
        oi     \sa+.LIH_SR_state(\sar),.LIHSR_pres      # Indidate state present
        mvi    \sa+.LIH_SR_class(\sar),\handler()_cls   # Set interrupt class
        tm     \ctrl(\ctrlr),.LIHSR_FP    # Saving floating point registers?
        bno    .+(5*4)-\b(\br)            # ..No, skip saves
        std    0,\sa+.LIH_F0(\sar)           # Save CPU FP0
        std    2,\sa+.LIH_F2(\sar)           # save CPU FP2
        std    4,\sa+.LIH_F4(\sar)           # Save CPU FP4
        std    6,\sa+.LIH_F6(\sar)           # Save CPU FP6
        tm     \ctrl(\ctrlr),.LIHSR_FP    # Saving control registers?
        bno    .+(2*4)-\b(\br)            # ..No, skip save
        stctl  0,15,\sa+.LIH_CR(\sar)        # Save CPU control registers
        tm     \ctrl(\ctrlr),.LIHSR_FPC   # Saving floating point control register?
        bno    .+(2*4)-\b(\br)            # ..No, skip save
        stfpc  \sa+.LIH_FPC(\sar)            # Save CPU floating point control
        tm     \ctrl(\ctrlr),.LIHSR_AFP   # Saving addtional floating point registers?
        bno    .+(14*4)-\b(\br)           # ..No, skip saves
        std    1,\sa+.LIH_F1(\sar)           # Save CPU FP1
        std    3,\sa+.LIH_F3(\sar)           # Save CPU FP3
        std    5,\sa+.LIH_F5(\sar)           # Save CPU FP5
        std    7,\sa+.LIH_F7(\sar)           # Save CPU FP7
        std    8,\sa+.LIH_F8(\sar)           # Save CPU FP8
        std    9,\sa+.LIH_F9(\sar)           # Save CPU FP9
        std    10,\sa+.LIH_F10(\sar)         # Save CPU FP10
        std    11,\sa+.LIH_F11(\sar)         # Save CPU FP11
        std    11,\sa+.LIH_F11(\sar)         # Save CPU FP11
        std    12,\sa+.LIH_F12(\sar)         # Save CPU FP12
        std    13,\sa+.LIH_F13(\sar)         # Save CPU FP13
        std    14,\sa+.LIH_F14(\sar)         # Save CPU FP14
        std    15,\sa+.LIH_F15(\sar)         # Save CPU FP15
        tm     \ctrl(\ctrlr),.LIHSR_AR    # Saving addtional access registers?
        bno    .+(2*4)-\b(\br)            # ..No, skip save
        stam   0,15,\sa+.LIH_AR              # Save CPU access registers
        mvc    \sa+.LIH_SR_flags(\sar,1),\ctrl(\ctrlr)  # Save the controls used
        .endm
     
        .macro ihsdsavg handler:req sa:req ctrl:req ctrlr=15 sar=15 br=13 b=0b
        mvc    \sa+.LIHG_oPSW(8,\sar),\handler\()_opsw64   # Save prefix OLD PSW
        mvc    \sa+.LIHG_GR(16*4,\sar),\handler()_sa64     # Save prefix area GR's
        oi     \sa+.LIHG_SR_state(\sar),.LIHSR_pres        # Indidate state present
        mvi    \sa+.LIHG_SR_class(\sar),\handler()_cls64   # Set interrupt class
        tm     \ctrl(\ctrlr),.LIHSR_FP    # Saving floating point registers?
        jno    .+(5*4)                    # ..No, skip saves
        std    0,\sa+.LIHG_F0(\sar)          # Save CPU FP0
        std    2,\sa+.LIHG_F2(\sar)          # save CPU FP2
        std    4,\sa+.LIHG_F4(\sar)          # Save CPU FP4
        std    6,\sa+.LIHG_F6(\sar)          # Save CPU FP6
        tm     \ctrl(\ctrlr),.LIHSR_FP    # Saving control registers?
        jno    .+(2*4)                    # ..No, skip save
        stctl  0,15,\sa+.LIHG_CR(\sar)       # Save CPU control registers
        tm     \ctrl(\ctrlr),.LIHSR_FPC   # Saving floating point control register?
        jno    .+(2*4)                    # ..No, skip save
        stfpc  \sa+.LIHG_FPC(\sar)           # Save CPU floating point control
        tm     \ctrl(\ctrlr),.LIHSR_AFP   # Saving addtional floating point registers?
        jno    .+(13*4)-\b(\br)           # ..No, skip saves
        std    1,\sa+.LIHG_F1(\sar)          # Save CPU FP1
        std    3,\sa+.LIHG_F3(\sar)          # Save CPU FP3
        std    5,\sa+.LIHG_F5(\sar)          # Save CPU FP5
        std    7,\sa+.LIHG_F7(\sar)          # Save CPU FP7
        std    8,\sa+.LIHG_F8(\sar)          # Save CPU FP8
        std    9,\sa+.LIHG_F9(\sar)          # Save CPU FP9
        std    10,\sa+.LIHG_F10(\sar)        # Save CPU FP10
        std    11,\sa+.LIHG_F11(\sar)        # Save CPU FP11
        std    12,\sa+.LIHG_F12(\sar)        # Save CPU FP12
        std    13,\sa+.LIHG_F13(\sar)        # Save CPU FP13
        std    14,\sa+.LIHG_F14(\sar)        # Save CPU FP14
        std    15,\sa+.LIHG_F15(\sar)        # Save CPU FP15
        tm     \ctrl(\ctrlr),.LIHSR_AR    # Saving addtional access registers?
        jno    .+(2*4)                    # ..No, skip save
        stam   0,15,\sa+.LIHG_AR             # Save CPU access registers
        mvc    \sa+.LIHG_SR_flags(\sar,1),\ctrl(\ctrlr)  # Save the controls used
        .endm

 # ihsrst    - Restore 32-bit CPU state per current assembly time controls
 # ihsrstg   - Restore 64-bit CPU state per current assembly time controls
 #
 #  Macro Parameters:
 #    handler  Symbol used identifying the ihandler.S defined interrupt handler
 #    sa       A symbol identifying the start of the save area
 #    control  Assembly time value defining the save area content controls
 #             (defaults to .LIHSGBL set by ihsgbl macro.) 
 #    sar      The base register for the symbol used in the 'sa' parameter
 #             (default to 15, the local stack)
 #    br       Specified the local base register (defaults to 13)
 #    b        Specifies the local base (defaults to 0b)
 #
 # WARNING: Restoration of control registers may require additional logic before
 # exiting the interrupt handler. 

 .      .macro ihsrst handler:req sa:req control=.LIHSGBL sar=15 br=13 b=0b
    .if \control & .LIHSR_AFP  # Restoring access registers?
        lam   0,15,\sa+.LIH_AR       # Restore CPU access registers
    .endif
    .if \control & .LIHSR_AFP   # Restoring additional floating point registers?
         ld    1,\sa+.LIH_F1(\sar)    # Restore CPU FP1
         ld    3,\sa+.LIH_F3(\sar)    # Restore CPU FP3
         ld    5,\sa+.LIH_F5(\sar)    # Restore CPU FP5
         ld    7,\sa+.LIH_F7(\sar)    # Restore CPU FP7
         ld    8,\sa+.LIH_F8(\sar)    # Restore CPU FP8
         ld    9,\sa+.LIH_F9(\sar)    # Restore CPU FP9
         ld    10,\sa+.LIH_F10(\sar)  # Restore CPU FP10
         ld    11,\sa+.LIH_F11(\sar)  # Restore CPU FP11
         ld    12,\sa+.LIH_F12(\sar)  # Restore CPU FP12
         ld    13,\sa+.LIH_F13(\sar)  # Restore CPU FP13
         ld    14,\sa+.LIH_F14(\sar)  # Restore CPU FP14
         ld    15,\sa+.LIH_F15(\sar)  # Restore CPU FP15
    .endif
    .if \control & .LIHSR_FPC  # Restoring floating point control register?
        lfpc \sa+.LIH_FPC(\sar)       # Restore CPU floating point control
    .endif
    .if \control & .LIHSR_FP   # Restoring base floating point registers?
        ld    0,\sa+.LIH_F0(\sar)     # Restore CPU FP0
        ld    2,\sa+.LIH_F2(\sar)     # Restore CPU FP2
        ld    4,\sa+.LIH_F4(\sar)     # Restore CPU FP4
        ld    6,\sa+.LIH_F6(\sar)     # Restore CPU FP6
    .endif
    .if \control & .LIHSR_CR   # Restoring control registers?
        lctl  0,15,\sa+.LIH_CR(\sar)  # Restore CPU control registers
    .endif
        mvc    \handler()_sa(16*4,0),\sa+.LIH_GR(16*4,\sar) # Restore GRs to prefix
        mvc    \handler\()_opsw(8,0),\sa+.LIH_oPSW(8,\sar)  # Restore old PSW
        ni     \sa+LIH_SR_state(\sar),0xFF & .LIHSR_pres    # Indidate no state
        .endm

        .macro ihsrstg handler:req sa:req control=.LIHSGBL sar=15 br=13 b=0b
    .if \control & .LIHSR_AFP  # Restoring access registers?
        lam   0,15,\sa+.LIHG_AR       # Restore CPU access registers
    .endif
    .if \control & .LIHSR_AFP  # Restoring additional floating point registers?
         ld    1,\sa+.LIHG_F1(\sar)   # Restore CPU FP1
         ld    3,\sa+.LIHG_F3(\sar)   # Restore CPU FP3
         ld    5,\sa+.LIHG_F5(\sar)   # Restore CPU FP5
         ld    7,\sa+.LIHG_F7(\sar)   # Restore CPU FP7
         ld    8,\sa+.LIHG_F8(\sar)   # Restore CPU FP8
         ld    9,\sa+.LIHG_F9(\sar)   # Restore CPU FP9
         ld    10,\sa+.LIHG_F10(\sar) # Restore CPU FP10
         ld    11,\sa+.LIHG_F11(\sar) # Restore CPU FP11
         ld    12,\sa+.LIHG_F12(\sar) # Restore CPU FP12
         ld    13,\sa+.LIHG_F13(\sar) # Restore CPU FP13
         ld    14,\sa+.LIHG_F14(\sar) # Restore CPU FP14
         ld    15,\sa+.LIHG_F15(\sar) # Restore CPU FP15
    .endif
    .if \control & .LIHSR_FPC  # Restoring floating point control register?
        lfpc \sa+.LIHG_FPC(\sar)      # Restore CPU floating point control
    .endif
    .if \control & .LIHSR_FP   # Restoring base floating point registers?
        ld    0,\sa+.LIHG_F0(\sar)    # Restore CPU FP0
        ld    2,\sa+.LIHG_F2(\sar)    # Restore CPU FP2
        ld    4,\sa+.LIHG_F4(\sar)    # Restore CPU FP4
        ld    6,\sa+.LIHG_F6(\sar)    # Restore CPU FP6
    .endif
    .if \control & .LIHSR_CR   # Restoring control registers?
        lctlg  0,15,\sa+.LIH_CR(\sar) # Restore CPU control registers
    .endif
        mvc    \handler()_sa64(16*8,0),\sa+.LIHG_GR(16*4,\sar) # Restore GRs to pfx
        mvc    \handler\()_opsw64(16,0),\sa+.LIHG_oPSW(8,\sar) # Restore old PSW
        ni     \sa+LIHG_SR_state(\sar),0xFF ^ .LIHSR_pres      # Indidate no state
        .endm

 # ihssav   - Save 32-bit CPU state per current assembly time controls
 # ihssavg  - Save 64-bit CPU state per current assembly time controls
 #
 #  Macro Parameters:
 #    handler  Symbol used identifying the ihandler.S defined interrupt handler
 #    sa       A symbol identifying the start of the save area
 #    control  Assembly time value defining the save area content controls
 #             (defaults to .LIHSGBL set by ihsgbl macro.) 
 #    sar      The base register for the symbol used in the 'sa' parameter
 #             (default to 15, the local stack)
 #    br       Specified the local base register (defaults to 13)
 #    b        Specifies the local base (defaults to 0b)

 .      .macro ihssav handler:req sa:req control=.LIHSGBL sar=15 br=13 b=0b
        mvc    \sa+.LIH_oPSW(8,\sar),\handler\()_opsw   # Save prefix OLD PSW
        mvc    \sa+.LIH_GR(16*4,\sar),\handler()_sa     # Save prefix area GR's
        oi     \sa+.LIH_SR_state(\sar),.LIHSR_pres      # Indidate state present
        mvi    \sa+.LIH_SR_class(\sar),\handler()_cls   # Set interrupt class
    .if \control & .LIHSR_FP   # Saving floating point registers?
        std    0,\sa+.LIH_F0(\sar)     # Save CPU FP0
        std    2,\sa+.LIH_F2(\sar)     # save CPU FP2
        std    4,\sa+.LIH_F4(\sar)     # Save CPU FP4
        std    6,\sa+.LIH_F6(\sar)     # Save CPU FP6
    .endif
    .if \control & .LIHSR_CR   # Saving control registers?
        stctl  0,15,\sa+.LIH_CR(\sar)  # Save CPU control registers
    .endif
    .if \control & .LIHSR_FPC  # Saving floating point control register?
        stfpc \sa+.LIH_FPC(\sar)       # Save CPU floating point control
    .endif
    .if \control & .LIHSR_AFP  # Saving additional floating point registers?
        std    1,\sa+.LIH_F1(\sar)   # Save CPU FP1
        std    3,\sa+.LIH_F3(\sar)   # Save CPU FP3
        std    5,\sa+.LIH_F5(\sar)   # Save CPU FP5
        std    7,\sa+.LIH_F7(\sar)   # Save CPU FP7
        std    8,\sa+.LIH_F8(\sar)   # Save CPU FP8
        std    9,\sa+.LIH_F9(\sar)   # Save CPU FP9
        std    10,\sa+.LIH_F10(\sar) # Save CPU FP10
        std    11,\sa+.LIH_F11(\sar) # Save CPU FP11
        std    12,\sa+.LIH_F12(\sar) # Save CPU FP12
        std    13,\sa+.LIH_F13(\sar) # Save CPU FP13
        std    14,\sa+.LIH_F14(\sar) # Save CPU FP14
        std    15,\sa+.LIH_F15(\sar) # Save CPU FP15
    .endif
    .if \control & .LIHSR_AR  # Saving access registers?
        stam   0,15,\sa+.LIH_AR      # Save CPU access registers
    .endif
        mvi     \sa+.LIH_SR_flags(\sar),\control
        .endm

        .macro ihssavg handler:req sa:req control=.LIHSGBL sar=15 br=13 b=0b
        mvc    \sa+.LIHG_oPSW(16,\sar),\handler\()_opsw64   # Save prefix OLD PSW
        mvc    \sa+.LIHG_GR(16*8,\sar),\handler()_sa64      # Save prefix area GR's
        oi     \sa+.LIHG_SR_state(\sar),.LIHSR_pres       # Indidate state present
        mvi    \sa+.LIHG_SR_class(\sar),\handler()_cls64  # Set interrupt class
    .if \control & .LIHSR_FP   # Saving floating point registers?
        std    0,\sa+.LIHG_F0(\sar)     # Save CPU FP0
        std    2,\sa+.LIHG_F2(\sar)     # save CPU FP2
        std    4,\sa+.LIHG_F4(\sar)     # Save CPU FP4
        std    6,\sa+.LIHG_F6(\sar)     # Save CPU FP6
    .endif
    .if \control & .LIHSR_CR   # Saving control registers?
        stctg  0,15,\sa+.LIHG_CR(\sar)  # Save CPU control registers
    .endif
    .if \control & .LIHSR_FPC  # Saving floating point control register?
        stfpc \sa+.LIHG_FPC(\sar)       # Save CPU floating point control
    .endif
    .if \control & .LIHSR_FP   # Saving additional floating point registers?
         std    1,\sa+.LIHG_F1(\sar)   # Save CPU FP1
         std    3,\sa+.LIHG_F3(\sar)   # Save CPU FP3
         std    5,\sa+.LIHG_F5(\sar)   # Save CPU FP5
         std    7,\sa+.LIHG_F7(\sar)   # Save CPU FP7
         std    8,\sa+.LIHG_F8(\sar)   # Save CPU FP8
         std    9,\sa+.LIHG_F9(\sar)   # Save CPU FP9
         std    10,\sa+.LIHG_F10(\sar) # Save CPU FP10
         std    11,\sa+.LIHG_F11(\sar) # Save CPU FP11
         std    12,\sa+.LIHG_F12(\sar) # Save CPU FP12
         std    13,\sa+.LIHG_F13(\sar) # Save CPU FP13
         std    14,\sa+.LIHG_F14(\sar) # Save CPU FP14
         std    15,\sa+.LIHG_F15(\sar) # Save CPU FP15
    .endif
    .if \control & .LIHSR_AR   # Saving access registers?
         stam   0,15,\sa+.LIHG_AR      # Save CPU access registers
    .endif
        mvi     \sa+.LIHG_SR_flags(\sar),\control
        .endm

 # +---------------------------------------------------------------+
 # |  Interrupt Handler Save Area Save/Restore Controls and State  |
 # +---------------------------------------------------------------+

 # The abstraction layer preserves only the PSW and general registers.  It is the 
 # programs responsibility to preserve additional state.  The following flags are
 # provided for use by the program for this purpose, but it is the choice of the
 # program how it manages CPU state preservation.

.LIHSR_CR  = 0x80   # Save/Restore Control registers
.LIHSR_AR  = 0x40   # Save/Restore Access registers
.LIHSR_AFP = 0x04   # Save/Restore additional Floating Point registers
.LIHSR_FPC = 0x02   # Save/Restore Floating Point Control register
.LIHSR_FP  = 0x01   # Save/Restore basic Floating Point (F0, F2, F4, F6) registers
.LIHSR_L0  = 0x01   # Valid controls for Level 0
.LIHSR_L1  = 0x81   # Valid controls for Level 1
.LIHSR_L2  = 0xC7   # Valid controls for Level 2
.LIHSR_L3  = 0xC7   # Valid controls for Level 3

 # Valid controls for specific architecture
.LIHSR_S370bc = .LIHSR_FP                                            # Level 0
.LIHSR_S370   = .LIHSR_FP|.LIHSR_CR                                  # Level 1
.LIHSR_S370XA = .LIHSR_FP|.LIHSR_CR                                  # Level 1
.LIHSR_ESA370 = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR                        # Level 2
.LIHSR_ESA390 = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR|.LIHSR_AFP|.LIHSR_FPC  # Level 2
.LIHSR_zarch  = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR|.LIHSR_AFP|.LIHSR_FPC  # Level 3

 # Valid state
.LIHSR_pres   = 0x01   # CPU state present

 # +--------------------------------------+
 # |  32-bit Interrupt Handler Save Area  |
 # +--------------------------------------+
 # Access: public

        struct .LIH
    # Old Program Status Word
        squad  .LIH_oPSW         # +0x0
    # Link to previous active save area
        slong  .LIH_link         # +0x8
    # Save/Restore Control Information
        shere  .LIH_SR           # +0xC
        sbyte  .LIH_SR_pgm       # +0xC   Reserved for program use
        sbyte  .LIH_SR_state     # +0xD   CPU state present in save area
        sbyte  .LIH_SR_class     # +0xE   Interruption class (see .ihandler.S)
        sbyte  .LIH_SR_flags     # +0xF   Save/restore controls (see above)
    # General Regster Save Area
        shere  .LIH_GR           # +0x10
        slong  .LIH_R0           # +0x10
        slong  .LIH_R1           # +0x14
        slong  .LIH_R2           # +0x18
        slong  .LIH_R3           # +0x1C
        slong  .LIH_R4           # +0x20
        slong  .LIH_R5           # +0x24
        slong  .LIH_R6           # +0x28
        slong  .LIH_R7           # +0x2C
        slong  .LIH_R8           # +0x30
        slong  .LIH_R9           # +0x34
        slong  .LIH_R10          # +0x38
        slong  .LIH_R11          # +0x3C
        slong  .LIH_R12          # +0x40
        slong  .LIH_R13          # +0x44
        slong  .LIH_R14          # +0x48
        slong  .LIH_R15          # +0x4C
    # Basic Floating Point Registers
        shere  .LIH_FR           # +0x50
        squad  .LIH_F0           # +0x50
        squad  .LIH_F2           # +0x58
        squad  .LIH_F4           # +0x60
        squad  .LIH_F6           # +0x68
    # End of the Level 0 architecture save area
        shere  .LIH_s360_len     # +0x70
    # Control Register Save Area
        shere  .LIH_CR           # +0x70
        slong  .LIH_C0           # +0x70
        slong  .LIH_C1           # +0x74
        slong  .LIH_C2           # +0x78
        slong  .LIH_C3           # +0x7C
        slong  .LIH_C4           # +0x80
        slong  .LIH_C5           # +0x84
        slong  .LIH_C6           # +0x88
        slong  .LIH_C7           # +0x8C
        slong  .LIH_C8           # +0x90
        slong  .LIH_C9           # +0x94
        slong  .LIH_C10          # +0x98
        slong  .LIH_C11          # +0x9C
        slong  .LIH_C12          # +0xA0
        slong  .LIH_C13          # +0xA4
        slong  .LIH_C14          # +0xA8
        slong  .LIH_C15          # +0xAC
    # End of the Level 1 architecture save area
        shere  .LIH_s370_len     # +0xB0
    # Additional Floating Point Registers (Level 2 architetures only)
        squad  .LIH_F1           # +0xB0
        squad  .LIH_F3           # +0xB8
        squad  .LIH_F5           # +0xC0
        squad  .LIH_F7           # +0xC8
        squad  .LIH_F8           # +0xD0
        squad  .LIH_F9           # +0xD8
        squad  .LIH_F10          # +0xE0
        squad  .LIH_F11          # +0xE8
        squad  .LIH_F12          # +0xF0
        squad  .LIH_F13          # +0xF8
        squad  .LIH_F14          # +0x100
        squad  .LIH_F15          # +0x108
    # Access Registers (Level 2 architectures only)
        shere  .LIH_AR           # +0x110
        slong  .LIH_A0           # +0x110
        slong  .LIH_A1           # +0x114
        slong  .LIH_A2           # +0x118
        slong  .LIH_A3           # +0x11C
        slong  .LIH_A4           # +0x120
        slong  .LIH_A5           # +0x124
        slong  .LIH_A6           # +0x128
        slong  .LIH_A7           # +0x12C
        slong  .LIH_A8           # +0x130
        slong  .LIH_A9           # +0x134
        slong  .LIH_A10          # +0x138
        slong  .LIH_A11          # +0x13C
        slong  .LIH_A12          # +0x140
        slong  .LIH_A13          # +0x144
        slong  .LIH_A14          # +0x148
        slong  .LIH_A15          # +0x14C
    # Floating Point Control Register (Level 2 architectures only)
        slong  .LIH_FPC          # +0x150
        salign 8                 # +0x154
    # End of the Level 2 architecture save area
        shere  .LIH_len          # +0x158

 # +--------------------------------------+
 # |  64-bit Interrupt Handler Save Area  |
 # +--------------------------------------+
 # Access: public

        struct .LIHG
    # Old Program Status Word
        socta  .LIHG_oPSW        # +0x0
    # Link to previous active save area
        squad  .LIHG_link        # +0x10
    # Save Area Control Information
        shere  .LIHG_SR          # +0x18
        sbyte  .LIHG_SR_pgm      # +0x18  Reserved for program use
        sbyte  .LIHG_SR_state    # +0x19  CPU state present in save area
        sbyte  .LIHG_SR_class    # +0x1A  Interruption class using this save area
        sbyte  .LIHG_SR_flags    # +0x1B  Save/restore controls
    # Floating Point Control Register
        slong  .LIHG_FPC         # +0x1C
    # General Regster Save Area
        shere  .LIHG_GR          # +0x20
        squad  .LIHG_R0          # +0x20
        squad  .LIHG_R1          # +0x28
        squad  .LIHG_R2          # +0x30
        squad  .LIHG_R3          # +0x38
        squad  .LIHG_R4          # +0x40
        squad  .LIHG_R5          # +0x48
        squad  .LIHG_R6          # +0x50
        squad  .LIHG_R7          # +0x58
        squad  .LIHG_R8          # +0x60
        squad  .LIHG_R9          # +0x68
        squad  .LIHG_R10         # +0x70
        squad  .LIHG_R11         # +0x78
        squad  .LIHG_R12         # +0x80
        squad  .LIHG_R13         # +0x88
        squad  .LIHG_R14         # +0x90
        squad  .LIHG_R15         # +0x98
    # Control Register Save Area
        squad  .LIHG_C0          # +0xA0
        squad  .LIHG_C1          # +0xA8
        squad  .LIHG_C2          # +0xB0
        squad  .LIHG_C3          # +0xB8
        squad  .LIHG_C4          # +0xC0
        squad  .LIHG_C5          # +0xC8
        squad  .LIHG_C6          # +0xD0
        squad  .LIHG_C7          # +0xD8
        squad  .LIHG_C8          # +0xE0
        squad  .LIHG_C9          # +0xE8
        squad  .LIHG_C10         # +0xF0
        squad  .LIHG_C11         # +0xF8
        squad  .LIHG_C12         # +0x100
        squad  .LIHG_C13         # +0x108
        squad  .LIHG_C14         # +0x110
        squad  .LIHG_C15         # +0x118
    # Basic Floating Point Registers
        squad  .LIHG_F0          # +0x120
        squad  .LIHG_F2          # +0x128
        squad  .LIHG_F4          # +0x130
        squad  .LIHG_F6          # +0x138
    # Additional Floating Point Control Registers
        squad  .LIHG_F1          # +0x140
        squad  .LIHG_F3          # +0x148
        squad  .LIHG_F5          # +0x150
        squad  .LIHG_F7          # +0x158
        squad  .LIHG_F8          # +0x160
        squad  .LIHG_F9          # +0x168
        squad  .LIHG_F10         # +0x170
        squad  .LIHG_F11         # +0x178
        squad  .LIHG_F12         # +0x180
        squad  .LIHG_F13         # +0x188
        squad  .LIHG_F14         # +0x190
        squad  .LIHG_F15         # +0x198
    # Access Registers
        shere  .LIHG_AR          # +0x1A0
        slong  .LIHG_A0          # +0x1A0
        slong  .LIHG_A1          # +0x1A4
        slong  .LIHG_A2          # +0x1A8
        slong  .LIHG_A3          # +0x1AC
        slong  .LIHG_A4          # +0x1B0
        slong  .LIHG_A5          # +0x1B4
        slong  .LIHG_A6          # +0x1B8
        slong  .LIHG_A7          # +0x1BC
        slong  .LIHG_A8          # +0x1C0
        slong  .LIHG_A9          # +0x1C4
        slong  .LIHG_A10         # +0x1C8
        slong  .LIHG_A11         # +0x1CC
        slong  .LIHG_A12         # +0x1D0
        slong  .LIHG_A13         # +0x1D4
        slong  .LIHG_A14         # +0x1D8
        slong  .LIHG_A15         # +0x1DC
    # End of the Level 3 architecture save area
        shere  .LIHG_len         # +0x1E0

.endif # .ifndef .Lihsave_S scope
