.ifndef .Lihandler_S
.Lihandler_S = 1
 # Copyright (C) 2012,2013 Harold Grovesteen
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

 # The ihandler.S module provides a set of building blocks for the implementation
 # of First-Level Interrupt Handlers.  These tools can utilize the abi within the
 # context of an interrupt stack.
 #
 # Interrupt Handler Requirements
 #
 # 1.  The handler's entry address.
 # 2.  New PSW containing the handler's entry address.
 # 3.  A 64- or 128-bytes save area within the first 4096-byte real page for the 
 #     interrupted program's registers.
 # 4.  A hardware assigned location for the new PSW. 
 # 5.  A hardware assigned location for the old PSW.
 #
 # For a given interrupt handler, the old and new PSW locations (requirements 3 and 
 # 4) above are fixed.  The actual entry point is being defined by this module's 
 # tools.  That only leaves the register save area as undefined.  The module 
 # satkpfx.S has save areas specified for each interrupt handler.  These may be
 # used and are the default values used by the individual interrupt class handler
 # macros ihandler_xxx[64].
 #
 # Additional Optional Requirements
 #
 # 6.  The size of the ABI stack area required by the interrupt handler if the stack
 #     is not shared with the interrupted program.
 # 7.  The starting location (high address) of an ABI stack area if the stack is not
 #     shared with the interrupted program.
 # 8.  A programming address that can be used for an interrupt code function 
 #     dispatch table or other program specific uses.
 #
 # These requirements constitute the Interrupt Handler Specification (IHS).  The
 # supplied macros allow the IHS to be specified at assembly time or dynamically
 # at run-time.  Two formats are provided for the IHS.  A 32-bit structure, IHS, and
 # a 64-bit structure IHS64.  An ABI stack area is best specified at run-time.  The 
 # memperm macro is memperm.S can be used to provide the run-time interrupt 
 # handler's ABI stack address.

 #   Macro                   Description
 #   ihandler_abi[64]      Create a ABI environment for interrupt handler use
 #   ihandler_disable[64]  Disable a 32- or 64-bit interrupt handler
 #   ihandler_enable[64]   Enable a 32 or 64-bit interrupt handler
 #   ihandler_enable[64]r  Enable a 32 or 64-bit interrupt handler from IHS ptr
 #   ihandler_enter[64]    Enter a 32 or 64-bit interrupt handler
 #   ihandler_exit[64]     Exit a 32 or 64-bit interrupt handler
 #   ihandler_ext[64]      Define a 32 or 64-bit external interrupt handler
 #   ihandler_io[64]       Define a 32 or 64-bit input/output interrupt handler
 #   ihandler_mck[64]      Define a 32 or 64-bit machine check interrupt handler
 #   ihandler_pgm[64]      Define a 32 or 64-bit program interrupt handler
 #   ihandler_rst[64]      Define a 32 or 64-bit restart interrupt handler
 #   ihandler_svc[64]      Define a 32 or 64-bit supervisor call interrupt handler
 #   ihandler_table[64]    Define a table of interrupt handler IHS[64] structures
 #   ihandlers_enable[64]  Enable 32- or 64-bit interrupts handlers in an
 #                         ihandler_table[64]
 #   ihs[64]               Create a 32 or 64-bit Interrupt Handler Specification
 #   trap                  Initialize all 64-bit new PSW's with disabled wait traps
 #   trap64                Initialize all 128-bit new PSW's with disabled wait traps

 # The following illustrates the relationships of the various macros and storage
 # areas used by the low-level interrupt system.
 #
 # Prefix Storage Area (0x000-0xFFF)
 #    
 #   0x000-0x1FF - Assigned Storage Locations
 #
 #  +--> New PSW's ---------------+ 
 #  |                             |
 #  +--> Old PSW's                |
 #  |                             |
 #  +---------------------+       |
 #                        |       |
 #                        |       |
 #   0xD00-0xFFF          |       |
 #     R0-R15 Save area           |
 #     (1 per interrupt <-+       |
 #     class)             |       |
 #                        |       |
 # Program Content        |       |
 #     (0x2000+)          |       |       +---------------------------------------+
 #                        |       |       |           INTERRUPT HANDLER           |
 #                        |       |       |                                       |
 #                        |       +-----------> ihandler_enter[64]                |
 #                        |               |     R13 is the default base register  |
 #                        |               |                                       |
 #                        |               |     finit[x]  # Initialize locals     |
 #                        |               |     ABI_lcls.S local defintions       |
 #                        +------------+  |  (optional if ihandler_abi[64] used)  |
 #                                     |  |                                       |
 #                                     |  |                                       |
 #                                     |  |     ihandler_abi[64] (optional)       |
 #      ihandler_enable[64][r]---------|------> Reserved Interrupt ABI Stack <--+ |        
 #      (one per handler)----------+   |  |     (1 per handler if used)         | |
 #                                 |   |  |   or the current ABI stack          | |
 #      ihandler_disable[64][r]----+   |  |     R13 is the base register        | |
 #                                 |   |  |     R14 points to ihandler_exit[64] | |
 #   +-------------------------+   |   |  |     R15 is the stack frame pointer  | |
 #   |  ihandler_table[64]     |   |   |  |                                     | |
 #   |  (multiple handlers)--------+   |  |                                     | |
 #   |           ^             |   |   |  |                                     | |
 #   |           |             |   |   |  |                                     | |
 #   |  ihandlers_enable[64]   |   |   |  |     ihandler_exit[64]               | |
 #   |  (multiple stacks)      |   |   +--------(contains IHS[64] structure)    | |
 #   |                         |   +------------> ihs[64]-----------------------+ |
 #   |    optional             |          |       (ihandler_define[64]            |
 #   +--------------------------          |        or ihandler_xxx[64]            |
 #                                        |        macros specify content)        |
 #                                        +---------------------------------------+ 

 # Coding Considerations
 #
 # These interrupt handling assistance macros in this module only directly support
 # the saving of the interrupted program's general registers and current PSW.  Any
 # more sophisticated context requirements, for example floating point registers or
 # control registers that require saving must be provided by the interrupt handler
 # itself.   Such additional program context may be stored in a location identified 
 # by means of content of the .LIHS[64]_pgm field or the ABI stack as local content.
 # The ihandler_define pgm parameter allows initialization of the .LIHS[64]_pgm
 # field of the IHS.  In this case, the ihandler_exit[64] macro expects the general
 # registers being restored to be in the IHS specified prefix page location and the
 # interrupt class' old PSW to be the PSW to be loaded to return control to the 
 # interrupted program.
 #
 # The IHS[64] structure of an interrupt class can be located by the interrupt 
 # handler via the symbol \ihandler\()_ihs generated by the ihandler_exit[64] macro.  
 # The IHS[64] structure is created within the interrupt handler for easy access by 
 # the handler using base/displacement addressing.  External to the interrupt handler,
 # the program can use a pointer to \ihandler\()_ihs to locate the IHS[64] structure 
 # for manipulation of a specific interrupt class definition.

 # Dependencies:
        .include "psw.S"      # for PSW generation macros
        .include "struct.S"   # for structure specification macros
        .include "table.S"    # for ihandler table related macros

 # +------------------------+
 # |  Interruption Classes  |
 # +------------------------+

.Lih_mck_cls = 0x0000   # Machine-check maskable interruption class
.Lih_ext_cls = 0x0004   # External maskable interruption class
.Lih_io_cls  = 0x0008   # Input/Output maskable interruption class
.Lih_svc_cls = 0x000C   # Suprvisor Call non-maskable interruption class
.Lih_rst_cls = 0x0010   # Restart non-maskable interruption class
.Lih_pgm_cls = 0x0014   # Program non-maskable interruption class
        
        
 # Interrupt Handler Specification Structure
 # Alignment: doubleword

        struct .LIHS            # 32-bit IHS structure
        squad  .LIHS_enapsw     # +0  Interrupt Handler enabling New PSW
        squad  .LIHS_dispsw     # +8  Interrupt Handler disabling New PSW
        squad  .LIHS_recpsw     # +16 Interrupt Handler recursion trap PSW
        slong  .LIHS_stkloc     # +24 High address of the ABI stack
        slong  .LIHS_pgm        # +28 Interrupt handler specific field
        slong  .LIHS_stksize    # +32 Size of the ABI stack.
        shword .LIHS_npsw       # +36 Assigned storage location of new PSW
        shword .LIHS_opsw       # +38 Assigned storage location of old PSW
        shere  .LIHS_len        # +40 Length of the IHS structure

        struct .LIHS64          # 64-bit IHS structure
        socta  .LIHS64_enapsw   # +0  Interrupt Handler enabling New PSW 
        socta  .LIHS64_dispsw   # +16 Interrupt Handler disabling New PSW
        socta  .LIHS64_recpsw   # +32 Interrupt Handler recursion trap PSW
        squad  .LIHS64_stkloc   # +48 High address of the ABI stack
        squad  .LIHS64_pgm      # +56 Interrupt handler specific field
        slong  .LIHS64_stksize  # +64 Size of the ABI stack.  Zero implies absent
        shword .LIHS64_npsw     # +68 Assigned storage location of new PSW
        shword .LIHS64_opsw     # +70 Assigned storage location of old PSW
        shere  .LIHS64_len      # +72 Length of the IHS64 structure

 # icode_ext   - Load a 32-bit external interruption code into a register
 # icode_ext64 - Load a 64-bit external interruption code into a register
 #
 # Macro Parameters:
 #       r         Register into which interruption code is loaded (required)
 #       multiple  Specify 'yes' to recognize multiple 32-bit architectures, 
 #                 otherwise only the current defined architecture is supported.  
 #                 (defaults to 'no')
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro icode_ext r:req multiple=no br=13 b=0b
    .ifc \multiple,yes
        tm     0b00001000,.LPSW_oldext+1(0)   # Was this a BC-mode PSW?
        bo     .+12-\b(br)                    # ..No, use standard icode
        lh     \r,.LPSW_oldext+2(0)           # ..Yes, load icode from old PSW
        b      .+8-\b(\br)                    # ..Otherwise
        lh     \r,.LINT_extcode(0)            # Load icode from standard location
    .else
      .ifdef __bcmode__
        lh     \r,.LPSW_oldext+2(0)           # Load a S/370 BC-mode interrupt code
      .else
        lh     \r,.LINT_extcode(0)            # Load icode from standard location
      .endif
    .endif
        .endm

        .macro icode_ext64 r:req
        llgh   \r,.LINT_extcode(0)            # Load icode from standard location
        .endm

 # icode_io   - Load a 32-bit I/O interrupt code (device address or SSID)
 # icode_io64 - Load a 64-bit I/O interrupt code (Subsytem ID)
 #
 # Macro Parameters:
 #       r         Register into which interruption code is loaded (required)
 #       multiple  Specify 'yes' to recognize multiple 32-bit architectures, 
 #                 otherwise only the current defined architecture is supported.  
 #                 (defaults to 'no')
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro icode_io r:req multiple=no br=13 b=0b
    .ifc \multiple,yes
        tm     0b00001000,.LPSW_oldio+1(0)   # Was this a BC-mode PSW?
        bo     .+12-\b(br)                   # ..No, use standard S/370 channel
        lh     \r,.LPSW_oldio+2(0)           # ..Yes, load icode from old PSW
        b      .+8-\b(\br)                   # ..Otherwise
        l      \r,0xB8(0)                    # Load icode from standard location
    .else
      .ifdef __bcmode__
        lh      \r,.LPSW_oldio+2(0)          # ..Yes, load icode from old PSW
     .else
        l       \r,0xB8(0)                   # Load icode from standard location
     .endif
    .endif
        .endm
        
        .macro icode_io64 r:req
        llgf    \r,0xB8(0)                   # Load icode from standard location
        .endm

 # icode_pgm   - Load a 32-bit program interrupt code
 # icode_pgm64 - Load a 64-bit program interrupt code
 #
 # Macro Parameters:
 #       r         Register into which interruption code is loaded (required)
 #       multiple  Specify 'yes' to recognize multiple 32-bit architectures, 
 #                 otherwise only the current defined architecture is supported.  
 #                 (defaults to 'no')
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro icode_pgm r:req multiple=no br=13 b=0b
    .ifc \multiple,yes
        tm     0b00001000,.LPSW_oldpgm+1(0)  # Was this a BC-mode PSW?
        bo     .+12-\b(br)                   # ..No, use standard program icode
        lh     \r,.LPSW_oldpgm+2(0)          # ..Yes, load icode from old PSW
        b      .+8-\b(\br)                   # ..Otherwise
        lh      \r,.LINT_pgmcode(0)          # Load icode from standard location
    .else
      .ifdef __bcmode__
        lh      \r,.LPSW_oldio+2(0)          # ..Yes, load icode from old PSW
     .else
        lh      \r,.LINT_pgmcode(0)          # Load icode from standard location
     .endif
    .endif
        .endm

        .macro icode_pgm64 r:req
        llgh   \r,.LINT_pgmcode(0)           # Load icode from standard location
        .endm

 # icode_svc   - Load a 32-bit supervisor call interrupt code
 # icode_svc64 - Load a 64-bit supervisor call interrupt code
 #
 # Macro Parameters:
 #       r         Register into which interruption code is loaded (required)
 #       multiple  Specify 'yes' to recognize multiple 32-bit architectures, 
 #                 otherwise only the current defined architecture is supported.  
 #                 (defaults to 'no')
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro icode_svc r:req multiple=no br=13 b=0b
    .ifc \multiple,yes
        tm     0b00001000,.LPSW_oldsvc+1(0)  # Was this a BC-mode PSW?
        bo     .+12-\b(br)                   # ..No, use standard SVC code
        lh     \r,.LPSW_oldsvc+2(0)          # ..Yes, load icode from old PSW
        b      .+8-\b(\br)                   # ..Otherwise
        lh      \r,.LINT_svccode(0)          # Load icode from standard location
    .else
      .ifdef __bcmode__
        lh      \r,.LPSW_oldio+2(0)          # ..Yes, load icode from old PSW
     .else
        lh      \r,.LINT_svccode(0)          # Load icode from standard location
     .endif
    .endif
        .endm

        .macro icode_svc64 r:req
        llgh   \r,.LINT_svccode(0)           # Load icode from standard location
        .endm

 # ihandler_abi   - Establish ABI register usage within a 32-bit interrupt handler
 # ihandler_abi64 - Establish ABI register usage within a 64-bit interrupt handler
 #
 # Establish an ABI context within the interrupt handler.  Two approaches to the
 # establishment of the ABI stack are supported:
 #   - a single stack assigned to the interrupt class when the interrupt class is
 #     enabled (ihandler_enable[64]) or
 #   - shared usage by the interrupt handler of the running program's ABI stack
 #
 # Which stack strategy is used is dictated by the value specified for the 
 # ihandler_define[64] macro size parameter.  Defaulting or specification of '0' for
 # size parameter dictates that the interrupt handler will share the current ABI
 # stack with the interrupted program's ABI stack.  This assumes and requires the 
 # interrupted program is using a stack.  Use of the interrupted program's ABI 
 # stack allows for interrupt recursion, for example a supervisor call interrupt 
 # handler making use of supervisor calls.
 #
 #  Macro Parameters:
 #       handler   Name of the handler using ABI conventions (required)
 #       skstate   Specify 'yes' to allocate space on the stack into which the
 #                 full program state can be saved
 #       s390      Specify 'yes' to cause only ESA/390 instruction generation
 #                 (Default 'no').  Only available with ihandler_abi macro
 #       finit     Specify 'no' if the IHS[64] reserved stack location already
 #                 has reserved space for the initial stack frame.  Specifying 'yes'
 #                 is required if the stack is shared with the program or the
 #                 initial frame was not reserved when the ihandler was enabled.
 #                 Specifying 'yes' is required if the ihandlers_enable[64] macro
 #                 has finit specified as 'no'.  (Defaults to 'yes')
 #       ireturn   Specify a symbol to override the default of the handler's
 #                 ihandler_exit[64] macro as the return from interrupt processing
 #                 (optional)
 #       br        Current base register established by ihandler_enter[64] 
 #                 (defaults to 13)
 #       b         Current base (defaults to 0b)
 #

        .macro ihandler_abi handler:req s390=no finit=yes ireturn br=13 b=0b
    .ifnc \br,13
        lr     13,\br      # Establish R13 as local base for ABI compliance
    .endif # .ifnc \br,13
    .ifc \s390,yes  # Generate s390 specific instructions
    .if \handler\()_stksz  # Use assigned stack for interrupt class
        larl   14,\handler\()_exit    # ihandler_exit does the return
        l      15,\handler\()_ihs+.LIHS_stkloc-\b(\br)  # Locate the stack
      .ifnb \ireturn
        larl   14,\ireturn            # Override default return location
      .endif # .ifnb \ireturn
    .else  # .if \handler\()_sktsz   Share the program stack with the ihandler
        l      15,\handler()_sa+15*4(0)         # Fetch the program's stack pointer
      .ifnb \ireturn
        larl   14,\ireturn            # Override default return location
      .else
        larl   14,\handler\()_exit    # Use the default exit logic
      .endif # .ifnb \ireturn
    .endif # .if \handler\()_sktsz
    .ifc \finit,yes
        framecr locals=yes
    .endif # .ifc \finit,yes
    .else  # .ifc \s390,yes  # Generate s370 instructions for both s370/s390
    .if \handler()_stksz  # Use assigned stack for interrupt class
        la     14,\handler\()_exit-\b(\br)         # ihandler_exit does the return
        l      15,\handler\()_ihs+.LIHS_stkloc-\b(\br)  # Locate the stack
      .ifnb \ireturn
        la     14,\ireturn-\b(\br)          # Override default exit logic
      .endif # .ifnb \ireturn
    .else  # .if \handler()_stksz           Share the program stack with the ihandler
        l      15,\handler()_sa+15*4(0)     # Fetch the program's stack pointer
      .ifnb \ireturn
        la     14,\ireturn-\b(\br)          # Override default exit logic
      .else  # .ifnb \ireturn
        la     14,\handler()\_exit-\b(\br)  # Use the default exit logic
      .endif # .ifnb \ireturn
    .endif # .if \handler()_stksz
    .ifc \finit,yes
        framecr370 locals=yes
    .endif # .ifc \finit,yes
    .endif # .ifc \s390,yes
        .endm

        .macro ihandler_abi64 handler:req finit=yes ireturn br=13 b=0b
    .ifnc \br,13
        lgr    13,\br                            # Establish R13 as base for ABI
    .endif # .ifnc \br,13
    .if \handler\()_stksz64
        larl   14,\handler\()_exit               # ihandler_exit does the return
        lg     15,\handler\()_ihs+.LIHS64_stkloc-\b(\br) # Set the stack pointer
    .else  # .if \handler\()_stksz64   Share the program stack with the ihandler
        lg     15,\handler\()_sa+15*8(0)         # Fetch the program's stack pointer
      .ifnb \ireturn
        larl   14,\ireturn                       # Override the default exit logic
      .else
        larl   14,\handler()_exit                # Use the default exit logic
      .endif # .ifnb \ireturn
    .endif # .if \handler\()_stksz64
    .ifc \finit,yes
        framecrx locals=yes
    .endif # .ifc \finit,yes
        .endm

 # ihandler_define    - Define a 32-bit interrupt handler
 # ihandler_define64  - Define a 64-bit interrupt handler
 #
 # The ihandler_define macros
 #
 #  Macro Parameters:
 #       handler   Name of the handler being defined (required)
 #       cls       Interrupt handler class (see for defined symbols)
 #       n         New PSW assigned storage location (required)
 #       o         Old PSW assigned storage location (required)
 #       sa        Prefix page 64- or 128-byte general register save area (required)
 #       s         New PSW system area, bits 0-15 (defaults to 0x0000)
 #       p         New PSW program area, bits 16-31 (defaults to 0x0000)
 #       size      ABI stack size. zero implies no ABI stack (defaults to 0)
 #       pgm       Handler specific data (defaults to 0)
 #       recurse   Specify 'yes' to enable interrupt recursion detection.  Detection
 #                 of an interrupt recursion causes a disabled wait.
 #                 (defaults to 'no')
 #
 # Notes:
 # 1. Interrupt recursion detects when an interrupt of the same class occurs
 #    while processing an interrupt of the same class.  Examples would be a program
 #    interrupt while processing a program interrupt, or an SVC being issued while
 #    executing an SVC.  In the first example, the second program interrupt is likely
 #    a problem.  In the second example, the SVC might be by design.  By specifying 
 #    'yes' for the recurse parameter, a disabled wait state will occur if an 
 #    interrupt recursion is detected.  For maskable interruptions, the sa parameter
 #    can inhibit recursion by disabling the interrupt, and recursion detection
 #    becomes a mechanism to trap a program bug that prematurely enables the
 #    interruption class.
 # 2. Symbols are used by these macros as a way to provide both run-time data via
 #    the ihs/ihs64 macros and assembly-time data allowing code generation 
 #    consistent with the interrupt definition.

        .macro ihandler_define handler:req cls:req n:req o:req sa:req s=0 p=0 size=0 pgm=0 recurse=no
\handler\()_define = 1
\handler\()_cls  = \cls
\handler\()_npsw = \n
\handler\()_opsw = \o
\handler\()_sa   = \sa
\handler\()_psws = \s
\handler\()_pswp = \p
\handler\()_pswl = 8
\handler\()_stksz= \size
\handler\()_pgm  = \pgm
    .ifc \recurse,yes
\handler\()_recurse = 1
    .else
\handler\()_recurse = 0
    .endif
        .endm

        .macro ihandler_define64 handler:req cls:req n:req o:req sa:req s=0 p=0 size=0 pgm=0 recurse=no
\handler\()_define64 = 1
\handler\()_cls64  = \cls
\handler\()_npsw64 = \n
\handler\()_opsw64 = \o
\handler\()_sa64   = \sa
\handler\()_psws64 = \s
\handler\()_pswp64 = \p
\handler\()_pswl64 = 16
\handler\()_stksz64= \size
\handler\()_pgm64  = \pgm
    .ifc \recurse,yes
\handler\()_recurse64 = 1
    .else
\handler\()_recurse64 = 0
    .endif
        .endm

 # ihandler_disable   - Disable a 32-bit interrupt handler based upon its IHS
 # ihandler_disable64 - Disable a 64-bit interrupt handler based upon its IHS64
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro ihandler_disable handler:req br=13 b=0b
    .ifndef \handler\()_define
        .error "ihandler_enable: error: ihandler_define missing"
    .endif
        mvc    \handler\()_npsw(8,0),\handler\()_ihs+.LIHS_dispsw-\b(\br) # Disable
        .endm

        .macro ihandler_disable64 ihsr:req wrkr:req
    .ifndef \handler\()_define64
        .error "ihandler_disable64: error: ihandler_define64 missing"
    .endif
        mvc    \handler\()_npsw64(16,0),\handler\()_ihs64+.LIHS64_dispsw-\b(\br)
        .endm

 # ihandler_disabler   - Disable a 32-bit interrupt handler, register points to IHS
 # ihandler_disable64r - Disable a 64-bit interrupt handler, register points to IHS64
 #
 #  Macro Parameters:
 #       ihsr      Register that points to a handlers IHS[64] (required)
 #       wrkr      Work register (required)

        .macro ihandler_disabler ihsr:req wrkr:req
        lh     \wrkr,.LIHS_npsw(\ihsr)           # Locate the new PSW location
        mvc    0(8,\wrkr),.LIHS_disapsw(\ihsr)   # Disable the interrupt
        .endm

        .macro ihandler_disable64r ihsr:req wrkr:req stkr=req
        lgh    \wrkr,.LIHS64_npsw(\ihsr)         # Locate the new PSW location
        mvc    0(16,\wrkr),.LIHS64_dispsw(\ihsr) # Disable the interrupt
        .endm

 # ihandler_enable - Enable a 32-bit interrupt handler based upon its IHS
 # ihandler_enable64 - Enable a 64-bit interrupt handler based upon its IHS64
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       stkr      Register containing the ABI stack location for enabled handler
 #                 if a stack size other than zero specified. (defaults to 0)
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro ihandler_enable handler:req stkr=0 br=13 b=0b
    .ifndef \handler\()_define
        .error "ihandler_enable: error: ihandler_define missing"
    .endif
    .if \handler\()_stksz
        st     \stkr,\handler\()_ihs+.LIHS_stkloc-\b(\br)  # Set ABI stack loc.
    .endif
        mvc    \handler\()_npsw(8,0),\handler\()_ihs+.LIHS_enapsw-\b(\br) # Enable
        .endm

        .macro ihandler_enable64 handler:req stkr=0 br=13 b=0b
    .ifndef \handler\()_define64
        .error "ihandler_enable64: error: ihandler_define64 missing"
    .endif
    .if \handler\()_stksz64
        st     \stkr,\handler\()_ihs+.LIHS_stkloc-\b(\br)  # Set ABI stack location
    .endif
        mvc    \handler\()_npsw64(16,0),\handler\()_ihs64+.LIHS64_enapsw-\b(\br)
        .endm

 # ihandler_enabler   - Enable a 32-bit interrupt handler, register points to IHS
 # ihandler_enable64r - Enable a 64-bit interrupt handler, register points to IHS64
 #
 #  Macro Parameters:
 #       ihsr      Register that points to a handlers IHS[64] (required)
 #       wrkr      Work register (required)
 #       stkr      Register containing the ABI stack location for enabled handler
 #                 if a stack size other than zero specified. (required)
 #       br        Current base register (defaults to 13)
 #       b         Current base (defaults to 0b)

        .macro ihandler_enabler ihsr:req wrkr:req stkr:req br=13 b=0b
        icm    \wrkr,0b1111,.LIHS_stksize(\ihsr) # Is a stack required?
        bz     .+8-\b(\br)                       # ..No, do not set stack location
        st     \stkr,.LIHS_stkloc(\ihsr)         # Set ABI stack loc.
        lh     \wrkr,.LIHS_npsw(\ihsr)           # Locate the new PSW location
        mvc    0(8,\wrkr),.LIHS_enapsw(\ihsr)    # Enable the interrupt
        .endm

        .macro ihandler_enable64r ihsr:req wrkr:req stkr=req sizer br=13 b=0b
        lgf    \wrkr,.LIHS64_stksize(\ihsr)      # Get the ABI stack size
        ltgr   \wrkr,\wrkr                       # Is the stack required?
        jz     .+10                              # ..No, do not set stack location
        stg    \stkr,.LIHS64_stkloc(\ihsr)       # Set ABI stack location
        lgh    \wrkr,.LIHS64_npsw(\ihsr)         # Locate the new PSW location
        mvc    0(16,\wrkr),.LIHS64_enapsw(\ihsr) # Enable the interrupt
        .endm

 # ihandler_enter - Enter a 32-bit interrupt handler
 # ihandler_enter64 - Enter a 64-bit interrupt handler
 #
 # Macro Parameters:
 #       handler   Symbol defining the interrupt handler entry address (required)
 #       br        Base register to be used by interrupt handler (defaults to 13)
 #       b         Base used by interrupt handler (defaults to 0b)
 #       base      Base established by the handler (defaults to 0)

        .macro ihandler_enter handler:req br=13 b=0b base=0
    .ifndef \handler\()_define
        .error "ihandler_enter: error: ihandler_define missing"
    .endif
        .align 2
\handler:
        stm    0,15,\handler\()_sa(0)   # Save interrupted program's registers
        basr   \br,0                    # Establish the handler's base register
\base:
    .if \handler\()_recurse
        mvc    \handler\()_npsw(8,0),\handler\()_ihs+.LIHS_recpsw-\b(\br) # Set trap
    .endif # .if \handler\()_recurse
        .endm

        .macro ihandler_enter64 handler:req br=13 b=0b base=0
    .ifndef \handler\()_define64
        .error "ihandler_enter64: error: ihandler_defi64 missing"
    .endif
        .align 2
\handler:
        stmg   0,15,\handler\()_sa64(0)    # Save interrupted program's registers
        basr   \br,0           # Establish the handler's base register
\base:
    .if \handler\()_recurse64
        mvc    \handler\()_npsw64(16,0),\handler\()_ihs64+.LIHS64_recpsw-\b(\br)
    .endif # .if \handler\()_recurse64
        .endm

 # ihandler_exit - Exit a 32-bit interrupt handler
 # ihandler_exit64 - Exit a 64-bit interrupt handler
 #
 # Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       br        Base register to be used by interrupt handler (defaults to 13)
 #       b         Base used by interrupt handler (defaults to 0b)

        .macro ihandler_exit handler:req br=13 b=0b
     .ifndef \handler\()_define
        .error "ihandler_exit: error: ihandler_define missing"
    .endif
        .align 2
\handler\()_exit:             # Identify exit for ihandler_enable
    .if \handler\()_recurse
        mvc      \handler\()_npsw(8,0),\handler\()_ihs+.LIHS_enapsw-\b(\br)
    .endif # .if \handler\()_recurse
        lm       0,15,\handler\()_sa(0)  # Restore interrupted programs registers
        lpsw     \handler\()_opsw(0)     # Load interrupted program's PSW for return
        .align 8
\handler\()_ihs:
        ihs \handler
        .endm

        .macro ihandler_exit64 handler:req br=13 b=0b
    .ifndef \handler\()_define64
        .error "ihandler_exit64: error: ihandler_defin64 missing"
    .endif
        .align 2
\handler\()_exit:             # Identify exit for ihandler_enable
    .if \handler\()_recurse64
        mvc      \handler\()_npsw64(16,0),\handler\()_ihs64+.LIHS64_enapsw-\b(\br)
    .endif # .if \handler\()_recurse64
        lmg       0,15,\handler\()_sa64(0)  # Restore interrupted programs registers
        lpswe     \handler\()_opsw64(0)     # Load interrupted program's PSW
        .align 8
\handler\()_ihs64:
        ihs64 \handler
        .endm

 # ihs - Define a 32-bit Interrupt Handler Specification structure
 # ihs64 - Define a 64-bit Interrupt Handler Specification structure
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 # 
 # The ihs[64] macro depends upon the psw_amode and psw_arch macros in psw.S having 
 # been set for proper generation of the new PSW.  Most of the content is provided
 # by the ihandler_define[64] macros.  Only the ABI stack location is provided
 # during run-time by the ihandler_enable[64] macro when the insterrupt in 
 # enabled.  The ABI stack size specified in the ihandler_define[64] macro
 # may be overridden by using the sizer parameter on the ihandler_enable[64] or
 # ihandler_enabler[64] macro.

        .macro ihs handler:req
        psw    s=\handler\()_psws,p=\handler\()_pswp,a=\handler  # Enable nPSW
        psw    s=0x0002,p=0,a=\handler\()_opsw                   # Disable nPSW
        psw    s=0x0002,p=0,a=\handler\()_npsw                   # Recurse trap nPSW
        .long  0,\handler\()_pgm,\handler\()_stksz
        .hword \handler\()_npsw,\handler\()_opsw
        .endm

        .macro ihs64 handler:req
        pswe   s=\handler\()_psws64,p=\handler\()_pswp64,a=\handler # Enable nPSW
        pswe   s=0x0002,p=0,a=\handler\()_opsw64                    # Disable nPSW
        pswe   s=0x0002,p=0,a=\handler\()_npsw64               # Recurse trap nPSW
        .quad  0,\handler\()_pgm64
        .long  \handler\()_stksz64
        .hword \handler\()_npsw64,\handler\()_opsw64
        .endm

 # ihandler_ext   - Define a 32-bit external interrupt handler
 # ihandler_ext64 - Define a 64-bit external interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xD00)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'no')

        .macro ihandler_ext handler:req sa=0xD00 s=0 p=0 size=0 pgm=0 recurse=no
        ihandler_define \handler cls=.Lih_ext_cls n=0x58 o=0x18 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_ext64 handler:req sa=0xD00 s=0 p=0 size=0 pgm=0 recurse=no
        ihandler_define64 \handler cls=.Lih_ext_cls n=0x1B0 o=0x130 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

 # ihandler_io   - Define a 32-bit input/output interrupt handler
 # ihandler_io64 - Define a 64-bit input/output interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xE00)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'no')

        .macro ihandler_io handler:req sa=0xE00 s=0 p=0 size=0 pgm=0 recurse=no
        ihandler_define \handler cls=.Lih_io_cls n=0x78 o=0x38 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_io64 handler:req sa=0xE00 s=0 p=0 size=0 pgm=0 recurse=no
        ihandler_define64 \handler cls=.Lih_io_cls n=0x1F0 o=0x170 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse 
        .endm

 # ihandler_mck   - Define a 32-bit machine check interrupt handler
 # ihandler_mck64 - Define a 64-bit machine check interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xD80)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'yes')

        .macro ihandler_mck handler:req sa=0xD80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define \handler cls=.Lih_mck_cls n=0x70 o=0x30 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_mck64 handler:req sa=0xD80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define64 \handler cls=.Lih_mck_cls n=0x1E0 o=0x160 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

 # ihandler_pgm   - Define a 32-bit program interrupt handler
 # ihandler_pgm64 - Define a 64-bit program interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xF00)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'yes')

        .macro ihandler_pgm handler:req sa=0xF00 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define \handler cls=.Lih_pgm_cls n=0x68 o=0x28 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_pgm64 handler:req sa=0xF00 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define64 \handler cls=.Lih_pgm_cls n=0x1D0 o=0x150 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

 # ihandler_rst   - Define a 32-bit restart interrupt handler
 # ihandler_rst64 - Define a 64-bit restart interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xF80)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'yes')

        .macro ihandler_rst handler:req sa=0xF80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define \handler cls=.Lih_rst_cls n=0x00 o=0x08 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_rst64 handler:req sa=0xF80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define64 \handler cls=.Lih_rst_cls n=0x1A0 o=0x120 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

 # ihandler_svc   - Define a 32-bit supervisor call interrupt handler
 # ihandler_svc64 - Define a 64-bit supervisor call interrupt handler
 #
 #  Macro Parameters:
 #       handler   handler symbol used in ihandler_entry[64] macro (required)
 #       sa        see ihandler_define[64] (defaults to 0xE80)
 #       s         see ihandler_define[64] (defaults to 0x0000)
 #       p         see ihandler_define[64] (defaults to 0x0000)
 #       size      see ihandler_define[64] (defaults to 0)
 #       pgm       see ihandler_define[64] (defaults to 0)
 #       recurse   see ihandler_define[64] (defaults to 'yes')

        .macro ihandler_svc handler:req sa=0xE80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define \handler cls=.Lih_svc_cls n=0x60 o=0x20 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

        .macro ihandler_svc64 handler:req sa=0xE80 s=0 p=0 size=0 pgm=0 recurse=yes
        ihandler_define64 \handler cls=.Lih_svc_cls n=0x1C0 o=0x140 sa=\sa s=\s p=\p size=\size pgm=\pgm recurse=\recurse
        .endm

 # ihandler_table   - Define a 32-bit interrupt handler table
 # ihandler_table64 - Define a 64-bit interrupt handler table
 #
 #  Macro Parameters:
 #       table   name of the interrupt table (required)
 #       rst     Restart interrupt handler symbol (optional)
 #       ext     External interrupt handler symbol (optional)
 #       svc     Supervisor call interrupt handler symbol (optional)
 #       pgm     Program interrupt handler symbol (optional)
 #       mck     Machine check interrupt handler symbol (optional)
 #       io      Input/Outpit interrupt handler symbol (optional)
 #
 # The symbols required for the interrupt handler class is always the value
 # used on the ihandler_entry[64] macro's handler argument.  Because handler
 # symbols are optional without defaults, they should be coded as keyword argument,
 # for example,  ihandler_table table=.Lih_tbl,ext=.Lext_handle,io=.Lio_handler

         .macro ihandler_table table:req rst ext svc pgm mck io
         table  name=\table,len=4
    .ifnb \rst
         .long  \rst\()_ihs
    .endif # .ifnb \rst
    .ifnb \ext
         .long  \ext\()_ihs
    .endif # .ifnb \ext
    .ifnb \svc
         .long  \svc\()_ihs
    .endif # .ifnb \ext
    .ifnb \pgm
         .long  \pgm\()_ihs
    .endif # .ifnb \pgm
    .ifnb \mck
         .long  \mck\()_ihs
    .endif # .ifnb \mck
    .ifnb \io
         .long  \io\()_ihs
    .endif # .ifnb \io
         tablend name=\table
         .endm

         .macro ihandler_table64 table:req rst ext svc pgm mck io
         tableg  name=\table,len=8
    .ifnb \rst
         .quad  \rst\()_ihs64
    .endif # .ifnb \rst
    .ifnb \ext
         .quad  \ext\()_ihs64
    .endif # .ifnb \ext
    .ifnb \svc
         .quad  \svc\()_ihs64
    .endif # .ifnb \ext
    .ifnb \pgm
         .quad  \pgm\()_ihs64
    .endif # .ifnb \pgm
    .ifnb \mck
         .quad  \mck\()_ihs64
    .endif # .ifnb \mck
    .ifnb \io
         .quad  \io\()_ihs64
    .endif # .ifnb \io
         tablend name=\table
         .endm

 # ihandlers_enable   - Enable 32-bit interrupt handlers in an ihandler_table
 # ihandlers_enable64 - Enable 64-bit interrupt handlers in an ihandler_table64
 #
 #  Macro Parameters:
 #       table    ihandler_table[64] name (required)
 #       tblr     Register pointing to the ihandler_table[64] (required)
 #       ntryr    Register pointing to the ihandler entry in the ihandler_table[64]
 #                (required)
 #       ihsr     Register containing the current IHS[64] structure pointer 
 #                (required)
 #       wrkr     ihandler_enable[64] work register
 #       finit    Specify 'yes' to cause the IHS[64] to set the stack frame pointer 
 #                with space reserved for the initial ABI stack frame.  Specifying 
 #                'yes' eliminates the need for any ihandler using a reserved stack
 #                area from using the framecr[370|x] macro when establishing the 
 #                frame.  Do not specify 'yes' if any of the ihandlers with reserved 
 #                stack frames expects to place local values on the initial stack 
 #                frame.  (Defaults to 'no')
 #       br       Current base register (Defaults to 13)
 #       b        Current base (Defaults to 0b)
 #
 # This macro allocates stacks for any interrupt handlers that require them and
 # enables the interrupt.  The memperm[64] function is used to allocate the
 # stack area.  ABI compatible register usage must have been established before the
 # ihandlers_enable[64] macro is used.

         .macro ihandlers_enable table:req tblr:req ntryr:req ihsr:req wrkr:req finit=no br=13 b=0b
         l      \tblr,3f-\b(\br)     # Locate the ihandler_table
         tblscan tblr=\tblr,ntryr=\ntryr,eot=2f,next=1
         l      \ihsr,0(\ntryr)      # Locate the ihandler IHS structure
         icm    1,0b1111,.LIHS_stksize(\ihsr) # Determine if a stack is needed?
         bz     4f-\b(\br)           # ..No, do not allocate a stack
         sr     2,2                  # Clear R2
         la     2,8(0)               # Set allocation alignment to doubleword (8)
         abi_call .Lmemperm          # Allocate the stack
         al     1,.LIHS_stksize(\ihsr) # Point to the bottom of the stack
     .ifc \finit,yes
         framecr370 stkr=1           # Allocate the interrupt handler's frame
     .endif # .ifc \finit,yes
4:       ihandler_enabler ihsr=\ihsr,wrkr=\wrkr,stkr=1  # Enable the interrupt
         tblnext tblr=\tblr,ntryr=\ntryr,next=1b   # Process the next entry
         b      3f+4-\b(\br)         # Branch around table location
3:       .long \table                # Location of the table
         .endm

         .macro ihandlers_enable64 table:req tblr:req ntryr:req ihsr:req wrkr:req finit=no br=13 b=0b
         lg     \tblr,3f-\b(\br)          # Locate the ihandler_table64
         tblscang tblr=\tblr,ntryr=\ntryr,eot=2f,next=1
         lg     \ihsr,0(\ntryr)           # Locate the ihandler IHS64 structure
         llgf   1,.LIHS64_stksize(\ihsr)  # Fetch the stack size
         ltgr   1,1                       # Is a stack required?
         bz     4f-\b(\br)                # ..No, do not allocate a stack
         sr     2,2                       # Clear R2
         la     2,8(0)                    # Set allocation alignment to doubleword
         abi_call .Lmempermg              # Allocate the stack
         algf   1,.LIHS64_stksize(\ihsr)  # Point to the bottom of the stack
     .ifc \finit,yes
         framecrx stkr=1                  # Allocate the interrupt handler's stack frame
     .endif # .ifc \finit,yes
4:       ihandler_enable64r ihsr=\ihsr,wrkr=\wrkr,stkr=1
         tblnextg tblr=\tblr,ntryr=\ntryr,next=1b  # Process the next entry
         j      3f+8                      # Jump around the table address
3:       .quad  \table                    # Location of the table
         .endm

 # trap   - Initialize all 64-bit new PSW's with disabled wait traps
 # trap64 - Initialize all 128-bit new PSW's with disabled wait traps
 #
 #  Macro Parameters:
 #       br        Base register to be used by interrupt handler (defaults to 13)
 #       b         Base used by interrupt handler (defaults to 0b)
 #
 # The IPL ELF standard provides for the initialization of absolute addresses
 # 0x000-0x01FF with content during the IPL function.  By default the iplmed.py IPL 
 # medium preparation processor will provide disabled wait new PSW's for all 
 # interrupts in all architectures during the Initial Program Load function.  Only 
 # if these iplmed.py defaults are disabled are these macros useful.

         .macro trap br=13 b=0b
         mvc  0x000(8,0),.+16-\b(\br)       # Setup restart new stub PSW
         mvc  0x058(5*8,0),.+18-\b(\br)     # Setup remaining new stub PSW's
         b    (.+(6*8)+4)-\b(\br)           # Branch around trap PSW's
         .hword 0x000A,0x0000,0x0008,0x666  # Restart New PSW
         .hword 0x000A,0x0000,0x0018,0x666  # External New PSW
         .hword 0x000A,0x0000,0x0020,0x666  # Supervisor Call new PSW
         .hword 0x000A,0x0000,0x0028,0x666  # Program New PSW
         .hword 0x000A,0x0000,0x0030,0x666  # Machine-Check New PSW
         .hword 0x000A,0x0000,0x0038,0x666  # Input-Output New PSW
         .endm

         .macro trap64 br=13 b=0b
         mvc  0x1A0(6*16,0),.+10-\b(\br)           # Setup new stub PSW's
         b    (.+(6*16)+4)-\b(\br)                 # Branch around trap PSW's
         .long  0x00020000,0x80000000,0,0x01200666 # Restart New PSW
         .long  0x00020000,0x80000000,0,0x01300666 # External New PSW
         .long  0x00020000,0x80000000,0,0x01400666 # Supervisor Call new PSW
         .long  0x00020000,0x80000000,0,0x01500666 # Program New PSW
         .long  0x00020000,0x80000000,0,0x01600666 # Machine-Check New PSW
         .long  0x00020000,0x80000000,0,0x01700666 # Input-Output New PSW
         .endm

.endif # .ifndef .Lihandler_S
