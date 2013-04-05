.ifndef .LIEIB_S
.LIEIB_S = 1
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

 # This module contains definitions of the IPL Environment Information Block defined
 # in the document "SATK for s390 - IPL Medium Preparation Processor" and the
 # foundation Hardware Abstraction Layer configuration macros.
 
            .include "ASB.S"  # Include halptr definition if not already available
            .include "io.S"   # Include I/O definitions if not already available

 # hal - Hardware Abstraction Layer support f0r architecture modes and platforms 
 #  Macro Parameters:
 #       s370bc   Specify 'yes' to support System/370 basic control mode 
 #                (default 'no')
 #       s370     Specify 'yes' to support System/370 extended control mode
 #                (default 'no')
 #       s390     Specify 'yes' to support ESA/390 (default 'no')
 #       s390x    Specify 'yes' to support z/Architecture (default 'no')
 #       vm       Specify 'no' to disable virtual machine platform use 
 #                (default 'yes')
 #       hercules Specify 'no' to disable Hercules platform use (default 'yes')
 #                (default 'yes')

         .macro hal s370bc=no,s370=no,s390=no,s390x=no,vm=yes,hercules=yes
    .ifndef .Lhal_options
.Lhal_archprob_macro = 0
.Lhal_s370bc = 0
.Lhal_s370ec = 0
.Lhal_s370   = 0
.Lhal_s390   = 0
.Lhal_s390x  = 0
.Lhal_32bit  = 0
.Lhal_64bit  = 0
.Lhal_ih     = 0
.Lhal_io     = 0
.Lhal_iolo   = 0
.Lhal_mem    = 0
.Lhal_cio    = 0
.Lhal_sio    = 0
.Lhal_vm     = 1
.Lhal_herc   = 1
.Lhal_tt     = 1
.Lhal_options= 1
    .else
         .warning "attempt to redefine HAL options ignored"
         .exitm
    .endif
    .ifc \s370bc,yes
.Lhal_s370bc = 1
.Lhal_s370   = 1
.Lhal_32bit  = 1
.Lhal_cio    = 1
    .endif
    .ifc \s370,yes
.Lhal_s370ec = 1
.Lhal_s370   = 1
.Lhal_32bit  = 1
.Lhal_cio    = 1
    .endif
    .ifc \s390,yes
.Lhal_s390   = 1
.Lhal_32bit  = 1
.Lhal_sio    = 1
    .endif
    .ifc \s390x,yes
.Lhal_64bit  = 1
.Lhal_s390x  = 1
.Lhal_sio    = 1
    .endif
    .ifc \vm,no
.Lhal_vm     = 0
    .endif
    .ifc \hercules,no
.Lhal_herc   = 0
    .endif
         .endm

 # halfeat - Specify Hardware Abstraction Layer features enabled
 #  Macro Parameters:
 #       ih       Specify 'yes' to support interrupt handling abstractions 
 #                (default 'no')
 #       io       Specify 'yes' to support I/O abstractions (default 'no')
 #                Specify an absolute value to enable I/O abstractions and define
 #                a default console device address or device number
 #       s390     Specify 'yes' to force all 32-bit code to use ESA/390 prologs
 #       tt       Specify 'no' to suppress ASCII/EBCDIC translation tables 
 #                (default 'yes')
 #       cons     Specify the default console device number (default 0x001F)
 #
 # Note:
 # 1. ih=yes utilizes src/ihandlers.S when establishing the interrupt handler
 #    abstraction.  ihandlers.S depends upon access to the permanent memory 
 #    allocator in src/storage/memperm.S to allocate interrupt handler stacks.
 #    

         .macro halfeat ih=no,io=no,s390=no,tt=yes,cons=0x001F
    .ifndef .Lhal_options
         .error "hal macro architecture specifications missing"
         .exitm
    .endif # .ifndef .Lhal_options
    .ifdef .Lhal_features
         .warning "redefinition of hal features ignored"
         .exitm
    .endif # .ifdef .Lhal_features
.Lhal_features = 1

.Lhal_cons  = \cons
    .ifc  \io,low
.Lhal_iolo  = 1
    .endif
    .ifc \io,yes
.Lhal_io    = 1
.Lhal_iolo  = 1
    .endif # .ifc \io,yes

    .ifc  \ih,yes
.Lhal_ih = 1
    .else # .ifc  \ih,yes
    .if .Lhal_io
         .warning "'ih=yes' forced for I/O abstractions"
.Lhal_ih = 1 
    .endif # .if .Lhal_io
    .endif # .ifc  \ih,yes

    .ifc \s390,yes
.Lhal_s390_only = 1
    .else
.Lhal_s390_only = 0
    .endif # ifc \s390,yes

    .ifc \tt,no
.Lhal_tt    = 0
    .endif # .ifc \tt,no

    .if .Lhal_32bit
         asbdefn yes
    .endif # .if .Lhal_32bit
    .if .Lhal_64bit
         asbdefng yes
    .endif # .if .Lhal_64bit
         .endm

 # probe - Probe the platform to determine the running architecture
 #
 # This macro calls the architecture detection logic in archal.S to determine the
 # running architecture and passes control to the symbol identified by the program
 # for the detected architecture.
 #
 # If the program is not prepared to support the detected architecture (implied
 # by the omission of a symbol for the architecture), the detection logic will 
 # enter a disabled wait state.  The instruction address (IA) of the disabled wait 
 # state PSW identifies the unsupported detected architecture.
 #
 #  IA      Unsupported architecture
 #
 # 0x360    System/370 in basic control mode
 # 0x370    System/370 in extended control mode
 # 0x390    ESA/390
 # 0x900    z/Architecture
 #
 #  Macro Parameters
 #       s370bc   Symbol to which control is passed if S/370 basic control mode is
 #                detected.  If the --s370bc parmeter is provided to the IPL 
 #                Medium Preparation Processor, the platform will IPL into the 
 #                S/370 basic control mode.  If ommitted, unrequired
 #       s370     Symbol to which control is passed if S/370 extended control mode
 #                is detected.  On S/370 platforms, the IPL Medium Preparation
 #                Processor will by default IPL the platform into S/370 extended
 #                control mode.
 #       s390     Symbol to which control is passed if ESA/390 is detected.  On 
 #                ESA/390 or z/Architecture platforms, the IPL Medium Preparation
 #                Processor will IPL the platform into ESA/390 mode.
 #       s390x    Symbol to which control is passed if z/Architecture is detected.
 #                This mode is not possible by IPL but is possible when a program
 #                begins execution by means of a restart on the Hercules emulator
 #                platform.
 #       br       Local base register (default 13)
 #       b        Local base (default 0b)
 #
 # probe Macro Considerations:
 # 
 # The hal macro must have been coded prior to the use of the probe macro.
 #
 # archal.S Considerations:
 #
 # archal.S requires that a local base of 0b has been identified before archal.S
 # has been included in the program and that this location has been placed in
 # register 13 before the probe macro is executed by the program.  
 #
 # The hal macro must have been used prior to including probe.S into the program
 # establishing the architectures intended to be supported by the program.
 #
 # Program Considerations:
 #
 # Register contents following the transfer of control to the symbol associated 
 # with the detected architecture are as follows:
 #    
 #    R0-R12    unpredictable
 #    R13       the probe macro logic base register is preserved
 #    R14       the return address is preserved
 #    R15       preserved
 #
 # Coding Considerations:
 #
 # The various components of the HAL system expects the following general sequence
 # within the program:
 #                           Optional/
 #                           Required
 #
 #      .include "HAL.S"     #   R  Include the HAL macros and structures
 #      .include "STORAGE.S" #   O  halfeat ih=yes requires the storage subsystem
 #      hal                  #   R  Establish the HAL supported architectures
 #      halfeat              #   R  HAL features required by the program
 #      stgfeat              #   O  halfeat ih=yes uses the permanent memory allocator
 #      probe                #   O  Pass control based upon the running architecture
 #      .include "archal.S"  #   O  Actual probe processing (required for probe)
 #      .include "hals.S"    #   R  Include the Hardware Abstraction Layer itself
 #      .include "storage.S" #   O  halfeat ih=yes uses the permanent memory allocator

        .macro probe s370bc s370 s390 s390x br=13 b=0b
        bas   14,.Lhal_arch_probe-\b(\br)
    .ifndef .Lhal_options
        .error "probe macro requires previously specified hal macro options"
        .exitm
    .endif
    .ifnb \s370bc                # If probe s370bc specified
    .if .Lhal_s370bc             #    If hal s370bc enabled
        b      \s370bc-\b(\br)   #       Return from s370bc detection: b 0(14)
    .else                        #    hal s370bc option not enabled
        .warning "s370bc must be enabled by hal macro to detect s370 bc mode"
        .long  0                 #       Enter disabled wait with IA = 0x360
    .endif                       #    end of .if .Lhal_s370bc scope
    .else                        # probe s370bc not specfied
        .long  0                 #     Enter disabled wait with IA = 0x360
    .endif                       # end of .ifnb \s370bc scope
    .ifnb \s370
    .if .Lhal_s370
        b      \s370-\b(\br)     # Return from s370 detection: b 4(14)
    .else
        .warning "s370 must be enabled by hal macro to detect s370 ec mode"
        .long  0                 # Enter disabled wait with IA = 0x370
    .endif
    .else
        .long  0                 # Enter disabled wait with IA = 0x370
    .endif
    .ifnb \s390
    .if .Lhal_s390
        b      \s390-\b(\br)     # Return from s390 detection: b 8(14)
    .else
        .warning "s390 must be enabled by hal macro to detect s390 mode"
    .endif
    .else
        .long  0                 # Enter disabled wait with IA = 0x390
    .endif
    .ifnb \s390x
    .if .Lhal_s390x
        b      \s390x-\b(\br)    # Return from s390x detection: b 12(14)
    .else
        .warning "s390x must be enabled by hal macro to detect s390x mode"
    .endif
    .else
        .long  0                 # Enter disabled wait with IA = 0x900
    .endif
        .endm

 # setarch - Change the architecture of the running CPU
 #
 # This macro calls the architecture set architecture logic in archal.S to change
 # the running architecture.  Upon control returning from the set architecture
 # logic, the CPU is in the running architecture, whether an actual platform
 # change was required or not.
 #
 # If the architecture change fails, the instruction address (IA) of the disabled 
 # wait state PSW identifies these conditions.
 #
 #    IA        Unsupported architecture
 #
 #  0x00abad    Failed to enter valid requested architecture (see R6 for status)
 #  0x37abad    On Hercules, SIGP_SETARCH_S370 facility has not been enabled.
 #              On other platforms, 37abad is an invalid reqested architecture.
 #  0xXXabad    Invalid requested architecture.  XX are the eight low-order R0 bits
 #
 #  Macro Parameters
 #       arch     Specify the architecture desired: s370, s390, s390x
 #       br       Local base register (default 13)
 #       b        Local base (default 0b)
 #
 #  setarch Considerations:
 #
 #  The current architecture or platform must support and be enabled to enter the 
 #  requested architecture from the currently runnng architecture.  Otherwise, 
 #  a disabled wait state will be entered.
 #
 #  ABI Function Considerations:
 #  
 #  The code called by this macro uses the shared subroutine conventions that 
 #  allow the macro to be used within an ABI function.  HOWEVER, because the 
 #  architecture will change, care must be taken to appropriately adjust the
 #  the stack frame.

        .macro setarch arch:req br=13 b=0b
    .ifc \arch,s370
        la     0,0x25(0)       # Enter S/370 mode (Hercules specific capability)
    .else
    .ifc \arch,s390
        sr     0,0             # Enter ESA/390 mode from z/Architecture
    .else
    .ifc \arch,s390x
        la     0,0x01(0)       # Enter z/Architecture mode from ESA/390
    .else
        .error "'setarch' macro does not support the requested architecture"
    .endif
    .endif
    .endif
        bas    11,.Lhal_set_arch-\b(\br)
        .endm

 # +-------------------------------------+
 # |  IPL Environment Information Block  |
 # +-------------------------------------+

.LIEIB      =0x250   # Address where IEIB resides
.LIEIB_run  =0x250   # .byte  The running architecture (see Architecture Flags)
.LIEIB_avl  =0x251   # .byte  The architectures available from this architecture
.LIEIB_plt  =0x252   # .byte  The running platform (see Platform Information)
.LIEIB_dtyp =0x253   # .byte  The IPL device type (see Device Types)
.LIEIB_ipl  =0x254   # .long  The IPL device id (0x00000000 implies CDROM)
.LIEIB_LP   =0x258   # .quad  LOADPARM data
.LIEIB_cpuid=0x260   # .quad  CPU ID
             halptr  0x268, .LIEIB_st,   .LIEIB_stg    # Highest addressable byte
             halptr  0x270, .LIEIB_sccb, .LIEIB_sccbg  # Address of the SCCB
             halptr  0x278, .LIEIB_sys,  .LIEIB_sysg   # Address of SYSIB 1.1.1 data
             halptr  0x280, .LIEIB_asb,  .LIEIB_asbg   # Address of the ASB
             halptr  0x288, .LIEIB_dtc,  .LIEIB_dtcg   # Address of the DTC
             halptr  0x290, .LIEIB_a2e,  .LIEIB_a2eg   # ASCII->EBCDIC translate table
             halptr  0x298, .LIEIB_e2a,  .LIEIB_e2ag   # EBCDIC->ASCII translate table
.LIEIB_cpu = 0x2A0   # .hword CPU address
.LIEIB_idn = 0x2A2   # .hword IPL device number
.LIEIB_cdi = 0x2A4   # .long  Console device id
.LIEIB_cdn = 0x2A8   # .hword Console device number
 #.LIEIB_cdo = 0x2AA   # .byte  Console device options (reserved for program use)
 #.LIEIB_cdu = 0x2AB   # .byte  Console option in use  (reserved for program use)
.LIEIB_len = 0x2AA-.LIEIB   # Length of the IEIB in bytes
 # Note: IHCB allocations start at 0x2C0

 # Architectue Flags (.LIEIB_run and .LIEIB_avl)
.LIEIB_s390x = 0x08  # z/Architecture
.LIEIB_s390  = 0x04  # Enterprise Systems Architecture/390
.LIEIB_s370  = 0x02  # System/370 Extended Control Mode
.LIEIB_s370bc= 0x01  # System/370 Basic Control Mode

 # Platform Information (.LIEIB_plt)
.LIEIB_plmsk = 0xE0  # Mask to isolate platform type
.LIEIB_Herc  = 0x80  # Hercules platform (based upon DIAGNOSE 8 or STSI)
.LIEIB_VM    = 0x40  # Virtual machine platform (based upon CPUID or STSI)
.LIEIB_phys  = 0x20  # Physical hardware platform
.LIEIB_conn  = 0x10  # Console Device number is available
.LIEIB_D8    = 0x08  # DIAGNOSE 8 is available
.LIEIB_cons  = 0x04  # Console is available
.LIEIB_sch   = 0x02  # Channel Subsystem available
.LIEIB_chan  = 0x01  # Channel Input/Output available

 # Device Types (.LIEIB_dtyp)
.LIEIB_CKD   = 0x80  # Count-Key-Data Device
.LIEIB_FBA   = 0x40  # Fixed-Block Architecture Device
.LIEIB_TAPE  = 0x20  # Tape Device
.LIEIB_RDR   = 0x10  # Card Reader Device
.LIEIB_CDROM = 0x01  # CDROM Device


 # +------------------------------------+
 # |  Input/Output Low-level Operation  |
 # +------------------------------------+

            struct .LIOLO
     # Public I/O data
            slong  .LIOLO_dev       # +0    Device ID associated with the I/O
     # Private I/O data
            # Subchannel Information Block
            sbytes .LIOLO_schib,.LSCHIB_len  # +4   SCHIB (52 bytes)

            # Operation Request Block
            sbytes .LIOLO_orb,.LORB_len      # +56  ORB (32 bytes)

            # Interrupt Response Block
            shere  .LIOLO_irb                # +88  IRB (96 bytes)
            slong  .LIOLO_SCSW               # +88  SCSW 
            shere  .LIOLO_CSW                # +92
            slong  .LIOLO_CCWA               # +92  CCW address
            sbyte  .LIOLO_ds                 # +96  Device status
            sbyte  .LIOLO_cs                 # +97  Channel status
            shword .LIOLO_count              # +98  CCW residual count
            sreserve .LIRB_len-12            # +100 remainder of IRB

            # I/O related PSW's
            salign 8                # Make sure PSW's are aligned on doubleword
            socta  .LIOLO_sPSW      # +184  PSW save area (64- or 128-bit PSW)
            socta  .LIOLO_nPSW      # +192  I/O Wait new run PSW (64- or 128-bit PSW)
            socta  .LIOLO_wPSW      # +200  I/O Wait new PSW (64- or 128-bit PSW)

            # CCW related information
            slong  .LIOLO_ccw1      # +216  24- or 31-bit CCW or CCW chain address
            slong  .LIOLO_idaw2     # +220  next available IDWA2 address (updated)
    # Private I/O operational data (set to zeros at start of operation)
            # I/O Accumulated results and status
            shere  .LIOLO_rslts     # +224  Result area starts here
            sbyte  .LIOLO_cherr     # +224  Channel errors found
            sbyte  .LIOLO_chalt     # +225  Channel alerts found
            sbyte  .LIOLO_dverr     # +226  Device errors found
            sbyte  .LIOLO_dvalt     # +227  Device alerts found
            # I/O Accumulated status
            sbyte  .LIOLO_done      # +228  Accumulated completion status
            sbyte  .LIOLO_status    # +229  Completion status of last CSW
            shere  .LIOLO_rslts_end # +230  Results area ends here
.LIOLO_resp_len = .LIOLO_rslts_end-.LIOLO_rslts # Length of the results area
    # Public I/O Execution Options
            sbyte  .LIOLO_pgm       # +230  Reserved for program or driver use
            # I/O Execution options
            sbyte  .LIOLO_options   # +231  I/O execution options
.LIOLO_poll =      0x01             #  Poll for status instead of CPU wait
.LIOLO_noio =      0x02             #  Just look for status from device, no SIO/SSCH
            slong  .LIOLO_resv      # +232
            shere  .LIOLO_sio_len   # +232 Maximum I/O area length
            shere  .LIOLO_len       #  232 IOLO length

        # End of Subsystem I/O area

.endif # .ifndef .LIEIB_S scope
