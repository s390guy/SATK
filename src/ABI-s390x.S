.ifndef .Labi_s390x_S
.Labi_s390x_S = 1
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
 
 # 64-bit ABI Support
 #
 #  The following macros establish the GCC stack options in use
 #     Macro        Description
 #     stackx    Define whether packed stack and/or back frame pointer is maintained
 #                  and how floating point registers are handled by s390x
 #
 #  The following macros establish the run-time register content for the ABI
 #     Macro        Description
 #     abi64     Enter 64-bit mode and setup the stack pointer (R15) and 
 #                  optionally the GOT register (R12)
 #
 #  The following macros define a function prolog
 #     Macro        Description
 #     functionx Defines the start of a s390x function and save
 #                  the caller's registers
 #
 #  The following macros define the current stack frame.
 #     Macro       Description
 #     framex    Start a s390x ABI stack frame definition
 #     framexcr  Create the initial frame on the s390x stack
 #
 #  The following macros define local fields on the stack frame.  These macros
 #  must be used following the function definition, but before the local frame
 #  is created using a push macro.  These macros are defined in ABI-lcls.S 
 #     falign    Align the current size of the stack frame
 #     fbyes     Define one or more bytes on the current stack frame
 #     fhword    Define a halfword on the current stack frame
 #     flong     Define a fullword on the current stack frame
 #     fquad     Define a quadword on the current stack frame
 #     fend      End the current stack frame definition
 #
 #  The following macros establish the preceding stack frame for the 
 #  current function
 #     Macro       Description
 #     pushx     Establishes this function's s390x stack frame
 #
 #  The following macros call a function
 #     Macro       Description
 #     callx     Call a local s390x function
 #     callrx    Call a s390x function from a register or GOT pointer
 #
 #  The following macros return to a caller from a called function
 #     Macro       Description
 #     lfpext    Restore a caller's non-volatile FP extension registers (s390x only)
 #     returnx   Return to a s390x caller
 #     returnax  Return to a s390x caller after dynamically allocating stack storage
 #
 #  The following macros dynamically allocate storage on the stack
 #     Macro       Description
 #     allocx    Dynamically allocate storage on stack in s390x environment
 #
 #  The following macros support self relocation
 #     Macro       Description
 #     endrelx   Terminate or mark a position within the self relocation list
 #     pointerx  Create a self relocatable pointer
 #     relocx    Enable self relocation
 #
 #  These macros cooperate to provide in assembly language programs 64-bit ABI 
 #  functionality.  Three macros are provided to initialize the ABI.  Two are
 #  declarative in nature (stackx, framex) and the other provides run-time
 #  initialization (abi64).  They are typically used in the following sequence:
 #
 #          .include "ABI-s390x.S"   # bring in these macros
 #          stackx                   # Establish frame structure
 #          framex                   # Define the stack frame in use.
 #          .text                    # Start executable code
 #          basr   13,0              # Create my base register
 #  0b:  
 #     [ Perform some initialization, for example, establishing a base register]
 #          abi64 stack=.Lstack      # Enter z/Architecture mode and stack pointer
 #     [ It is now possible to define an call functions. ]
 #
 #          callx .Lafunc            # Call a declared function 
 #                                   # callrx/callptrx may also be used
 #
 #     [ other parts of the program ]
 #
 #  Declaring a function and establishing the local environment involves a sequence
 #  of macros at the start that preserves the caller's environment (functionx), 
 #  define the local stack usage (the ABI-lcls.S macros) environment and then 
 #  establishes it (pushx).
 #
 #     # Declare a new function
 #         functionx .Lafunc
 #     [ define local stack usage with falign, fbytes, fhword, flong, fquad]           
 #     [ define literals used - they of course can be anywhere addressable ]
 #         pushx                # Now that my stack frame size is known, reserve it.
 #
 #     [ perform whatever this function is supposed to do ]
 #
 #         returnx              # Return to caller 
 #
 #  Finally, but not least, the stack needs to be established:
 #         abi_stack64 .Lstack
 #         .end
 
 # Establish the ABI register content _after_ entering 64-bit operating mode.  The
 # enable64 macro can be used to enter 64-bit operating mode.
 #  Macro Parameters:
 #       got     To enable use of the GOT, specify the register that will be the 
 #               GOT pointer.  Must be 12 for ABI compliance. (Optional)
 #       stack   To establish the stack poitner, specify the symbol containing 
 #               the stack starting address.  Can use the same symbol as provided 
 #               to the abi_stack64 macro's name argument.
 #       br      Current base register.  This defaults to the ABI standard of 13.
 #       b       Symbol reflecting the current base address.  Defaults to 0b.
 
        .macro abi64 got stack br=13 b=0b
   .ifnb \got
        b      .+12-\b(\br)         # Branch around GOT address
        .quad  _GOT_begin           # Generated linker scripts provide this symbol
        lg     \got,1b-\b(\br)      # Set up GOT pointer
.L_abi_uses_got = 1                 # Tell other macros got is enabled        
   .endif
   .ifnb \stack
        lg     15,\stack-\b(\br)    # Initialize the stack pointer
   .endif
        .endm

 # abi_stack64 - Establish a 64-bit stack starting location
 #  Macro Parameters:
 #       name   Specifies the symbol name to be used for the pointer (required)
 #       size   Size of the stack to be created (required)
 #       end    Indicates the ending (lowest) address for the stack (defaults to .)
 #
 # See the note for the abi_stack_start macro in ABI.S for details.

        .macro abi_stack64 name:req size:req end=.
    .ifc \end,.      # Allow for the stack constant being here
\name:  .quad  \end+((15+\size-.L_fsizeg)/8)*8
    .else            # Otherwise stack has a different end locaton
\name:  .quad  \end+((7+\size-.L_fsizeg)/8)*8    
    .endif           # .ifc \end scope
        .endm

 # callx - Call a ABI function using local branch relative long addressing
 #  Macro Parameters:
 #       func   symbol of the function being called (required)

        .macro callx func:req
        brasl  14,\func                     # Call the s390x function
        .endm

 # callptrx - Call a ABI function using an inline pointer
 #  Macro Parameters:
 #       func    Specifies the symbol of the function being called.
 #       br      Specified the local base register (defaults to 13)
 #       b       Specifies the local base (defaults to 0b)
 #
 # Intended to be the logical replacement in s370 for the s390 call macro, but may
 # also be used in s390 environments.

        .macro callptrx func:req br=13 b=0b
        lg     1,.+12-\b(\br)               # Locate the function being called
        basr   14,1                         # Call the function
        b      .+12-\b(\br)                 # Branch around the inline pointer
    .ifdef .L_relocbx
1:      .text  2                            # Enter relocation list sub section
        .quad  1b-.L_relocbx                # Define displacement to this pointer
        .text                               # Return to normal text sub section
    .endif
        .quad  \func                        # Function address
        .endm 

 # callrx - Call a ABI function using a pointer in a register
 #  Macro Parameters:
 #       reg     The register containing the pointer (defaults to 1)
 #       got     When specified, identifies the function symbol of the address to be
 #               retrieved from the GOT and placed in reg before calling the 
 #               function.  Requires the GOT to be enabled by the abi64 macro.

        .macro callrx reg=1 got
    .ifnb \got  # If got has a value use the name to load the register
        lgotx  \reg,\got                    # Load the register from GOT
    .endif
        basr   14,\reg                      # Call the function from a register
        .endm

 # enable64 - Enter 64-bit operational mode
 #
 # The size is adjusted for the minimum required when stack macro argument packed=yes
 # is specified.
 #
 #  Signal processor instruction usage:
 #    r1   = status register (even register of an even/odd pair, statr macro arg.)
 #    r1+1 = parameter (odd register of an even/odd pair)
 #           the parameter register must be set before issuing sigp
 #    d2   = order code
 #    r3   = CPU address (cpur macro argument)

        .macro enable64 cpur:req statr:req fail:req br=13 b=0b
        la     (\statr)+1,1         # Set parm for z/Arch from ESA/390
        stap   1f-\b(\br)           # Save the CPU address of this CPU
        lh     \cpur,1f-\b(\br)     # Set the CPU address
        sigp   \statr,\cpur,0x12    # Signal myself to change architecture
        bc     8,.+10-\b(\br)       # Branch around CPU address on success
        b      \fail-\b(\br)        # Branch to the failure routine if unsuccessful
1:      .hword 0                    # Where the CPU ID is stored 
        .endm

 # endrelx - Mark a position or end the self relocation list
 #  Macro Parameters:
 #      name   Establish a symbol that identifies the end of the self relocation 
 #             list (required)

        .macro endrelx name:req
        .pushsection ".text",2   # Enter relocation list sub section
\name:  .text            # Give it a symbol and return to the normal text sub section
        .popsection
        .endm
        
 # framecrx - Creates the initial stack frame based upon the contents of R15 in 
 #            s390x environments
 #  Macro Parameters: none
 #     locals  Specify 'yes' to include room on the stack for local frame content
 #             (Default 'no')
 #     stkr    Register containing the stack bottom address (default 15)

        .macro framecrx locals=no stkr=15
        srlg   \stkr,\stkr,3       # Make sure the stack is on a
        sllg   \stkr,\stkr,3       # ... doubleword boundary
     .ifc \locals,yes
        aghi   \stkr,(0-.L_local)  # Make room for my registers and locals
     .else
        aghi   \stkr,(0-.L_fsizeg) # Make room for my registers
     .endif
        .endm
        
 # framex - Establish the size and structure of the call stack frame
 #
 # The size is adjusted for the minimum required when stack macro argument packed=yes
 # is specified.

        .macro framex
    .ifdef .L_fsizeg
    .warning "ignoring attempt to redefine s390x frame"
    .else
    .ifeq .L_packx  # .L_packx == 0 --> frame not packed
.L_bptrg =      0
.L_G2    =      16
.L_G3    =      24
.L_G4    =      32
.L_G5    =      40
.L_G6    =      48
.L_G7    =      56
.L_G8    =      64
.L_G9    =      72
.L_G10   =      80
.L_G11   =      88
.L_G12   =      96
.L_G13   =      104
.L_G14   =      112
.L_G15   =      120
.L_FP0   =      128
.L_FP2   =      136
.L_FP4   =      144
.L_FP6   =      152
.L_fsizeg=      160
     .else           # .L_packx != 0 --> stack frame is packed
.L_G6    =      0
.L_G7    =      8
.L_G8    =      16
.L_G9    =      24
.L_G10   =      32
.L_G11   =      40
.L_G12   =      48
.L_G13   =      56
.L_G14   =      64
.L_G15   =      72
.L_fsizeg=      80
     .ifne .L_bpx    # .L_bpx != 0 --> stack frame back pointer is used
.L_bptrg =      88
.L_fsizeg=      96
     .endif          # End of .L_bpx scope
     .endif          # End of .L_packx scope
     .ifne .L_fpx    # .L_fpx !=0 --> fp=hard
.L_FP8   =      0+.L_fsizeg       
.L_FP9   =      16+.L_fsizeg
.L_FP10  =      24+.L_fsizeg
.L_FP11  =      32+.L_fsizeg
.L_FP12  =      40+.L_fsizeg
.L_FP13  =      48+.L_fsizeg
.L_FP14  =      56+.L_fsizeg
.L_FP15  =      64+.L_fsizeg
.L_fsizeg=      72+.L_fsizeg
     .endif          # End of .L_fpx scope
     .endif          # End of ifdef .L_fsizeg scope
        .endm

 # functionx - s390x Function Declaration
 #  Macro Parameters:
 #       name = Declared function's symbol (required)
 #
 #  Stack macro arguments fp and bp arguments will determine if the floating point 
 #  registers are saved or the back pointer is established.
 #       stack fp=soft ==> do not save caller's floating point registers
 #       stack fp=hard ==> save caller's floating point registers
 #       stack bp=no   ==> do not save back pointer in this function's call frame
 #       stack bp=yes  ==> Place frame back pointer in this function's call frame
 #
 #  .global pseudo operation must be provided separately to make the symbol visible
 #  to the ld linker
 #
 # Register on Entry:
 #   R0      = unpredictable
 #   R1      = Function entry addres, otherwise unpredictable (used by callrx macro)
 #   R2-R6   = non-floating point function parameters
 #   R7-R11  = Unpredictable
 #   R12     = Global Offset Table address if present
 #   R13     = Calling function's base register
 #   R14     = Calling functions return location
 #   R15     = Caller's stack frame pointer
 #   F0,F2,F4,F6     = Parameters passed to function (fp=hard  only)
 #   F1,F3,F5,F7-F15 = Unpredictable (fp=hard only)
 #   A0,A1   = Reserved for thread local storage pointer
 #   A2-A15  = unpredictable
 #
 # Registers available for function usage
 #   R0-R11  = available
 #   R12     = Global Offset Table address if present, otherwise available
 #   R13     = reserved for functions base register (set by functionx macro)
 #   R14     = available between function calls, volatile across calls
 #             (used by call or callrx macros)
 #   R15     = reserved for function's stack frame (set by pushx macro)
 #   F0-F15  = available
 #   A0,A1   = unavailable
 #   A2-A15  = available
 #
 # Registers on Exit:
 #   R0,R1   = unpredictable
 #   R2      = Returned value (if a non-floating point value is returned),
 #             otherwise unpredictable
 #   R3-R5   = unpredictable
 #  returnx macro restores caller's R6-R15 and optionally F8-F15
 #   R6-R12  = Calling function's original register content
 #   R13     = Calling function's base register
 #   R14     = Calling function's return location
 #   R15     = Calling function's stack frame pointer
 #   F0      = floating point return value (if return is a floating point value),
 #             otherwise unpredictable
 #   F1-F7   = unpredictable (fp=yes only)
 #   F8-F15  = Calling function's original register contents
 #   A0,A1   = Reserved for thread local storage pointer
 #   A2-A15  = unpredictable

        .macro functionx name:req
        .align 2
\name:
     .ifeq  .L_packx # If .L_packx == 0 --> packed=no
         stmg   2,15,.L_G2(15)              # Save registers in caller's stack frame
     .else           # If .L_packx != 0 --> packed=yes
         stmg   6,15,.L_G6(15)              # Save registers in caller's stack frame
     .endif
     .ifne  .L_fpx   # if .L_fpx   != 0 --> fp=hard
     .ifeq  .L_packx # if .L_packx == 0 --> packed=no
         std    0,.L_FP0(15)                # Save floating point register 0
         std    2,.L_FP2(15)                # Save floating point register 2
         std    4,.L_FP4(15)                # Save floating point register 4
         std    6,.L_FP6(15)                # Save floating point register 6
     .endif          # End of .L_packx scope
     .endif          # End of .L_fpx scope
         bras   13,9f                       # Setup base reg and lit pool pointer
.L_local =      .L_fsizeg                   # Set the default local frame size
0:
        .endm

 # lgotx - Load a 64-bit register with a GOT pointer
 #  Macro Parameters:
 #       reg   Register to be loaded with GOT pointer (required)
 #       name  Symbol name of the location to which the register will point 
 #             (required)

        .macro lgotx reg:req name:req
   .ifndef .L_abi_uses_got
        .error "GOT not enabled"
   .endif
        lg     \reg,\name@got(12)
        .endm

 # pushx - Push this function's stack frame onto the stack. 
 #         Adjusts stack pointer downward in s390x environments

        .macro pushx
.L_local = ((.L_local+7)/8)*8              # Make stack frame is doubleword sized
        .align 2                           # Make sure aligned after literal pool
    .ifne  .L_bpx     # If .L_bpx != 0 --> back pointer in use
9:      lgr    1,15                        # Load the current stack pointer
        aghi   15,-(.L_local)              # Allocate my frame on the stack
        stg    1,.L_bptrg(15)              # Save back pointer on my stack
    .else
9:      aghi   15,-(.L_local)              # Allocate my frame on the stack
    .endif
    .ifne  .L_fpx     # If .L_fpx != 0 --> fp=hard
        std    8,.L_FP8(15)                # Save floating point register 8
        std    9,.L_FP9(15)                # Save floating point register 9
        std    10,.L_FP10(15)              # Save floating point register 10
        std    11,.L_FP11(15)              # Save floating point register 11
        std    12,.L_FP12(15)              # Save floating point register 12
        std    13,.L_FP13(15)              # Save floating point register 13
        std    14,.L_FP14(15)              # Save floating point register 14
        std    15,.L_FP15(15)              # Save floating point register 15
    .endif
        .endm

 # lfpext - Load the Extended floating point registers from a stack frame
 #          Not normally required by programs, but used by returnx and returnax 
 #          macros.

        .macro lfpext lclr:req
        ld     8,.L_FP8(\lclr)              # Restore floating point register 8
        ld     9,.L_FP9(\lclr)              # Restore floating point register 9
        ld     10,.L_FP10(\lclr)            # Restore floating point register 10
        ld     11,.L_FP11(\lclr)            # Restore floating point register 11
        ld     12,.L_FP12(\lclr)            # Restore floating point register 12
        ld     13,.L_FP13(\lclr)            # Restore floating point register 13
        ld     14,.L_FP14(\lclr)            # Restore floating point register 14
        ld     15,.L_FP15(\lclr)            # Restore floating point register 15
        .endm
 
 # pointerx - Create a self relocatable pointer
 #  Macro Parameters:
 #       ptr   An expression that defines the pointer's location (required)
 
        .macro pointerx ptr:req
1:      .text  2
        .quad  1b-.L_relocbx
        .text
        .quad  \ptr
        .endm

 # relocx - Establish ability for self relocation
 #  Macro Parameters:
 #       name  Provides a name for locating the start of the self relocation 
 #             entries. (required)
 #       base  Identfies the base of the displacements stored in a self relocation
 #             entry (required)

        .macro relocx name:req base:req
.L_relocbx = \base
        .text  2
\name:  .text  0
        .endm
        
 # returnax - Return from an ABI function to its caller after dynamic stack 
 #            allocation.
 #  Macro Parameters:
 #       lclr    The register previously identified for the local frame usage
 #               after the dynamic allocation.
        
        .macro returnax lclr:req
    .ifne .L_fpx  # If .L_fpx != 0 --> using floating point registers
        lfpext \lclr                       # Restore caller's FP registers
    .endif
        lg     15,0(15)                    # Get back pointer from my stack
        lmg    6,15,.L_G6(15)              # Restore caller's R6-R15
        br     14                          # Return to caller
        .endm

 # returnx - Return from an ABI function to its caller
        
        .macro returnx
    .ifne .L_fpx  # If .L_fpx != 0
        lfpext 15                          # Restore caller's FP ext registers 
    .endif
    .ifne .L_bpx  # If .L_bpx != 0 --> return using back pointer
        lg     15,.L_bptrg(15)             # Get back pointer from my stack
.L_stack = 0
    .else
.L_stack = .L_local
    .endif
        lmg    6,15,.L_stack+.L_G6(15)     # Restore caller's R6-R15
        br     14                          # Return to caller
        .endm

 # stackx - Define the attributes of the 64-bit stack frame in this assembly
 #  Macro Parameters:
 #       packed   Determines whether the standard sized frame (packed=no) or a 
 #                compressed frame size is used (packed=yes).
 #       fp       Determines whether a caller's floating point registers should be 
 #                saved in the caller's stack frame (fp=hard) or not (fp=soft)
 #       bp       Determines whether the back pointer will be placed in the 
 #                called function's stack frame (bp=yes) or not (bp=no)
        
        .macro stackx packed=no fp=hard bp=no
    .ifc \packed,yes  # if packed == yes
.L_packx  = 1
    .else             # if packed != yes
.L_packx  = 0
    .endif
    .ifc \fp,hard     # if fp == hard
.L_fpx    = 1
    .else             # if fp != hard
.L_fpx    = 0
    .endif
    .ifc \bp,yes      # if bp == yes
.L_bpx    = 1
    .else             # if bp != yes
.L_bpx    = 0
    .endif
.L_abi    = 2         # Set the ABI to s390 64-bit
        .endm
        
 # allocx - Allocate dynamic storage on the stack frame
 #  Macro Parameters: none
 #   lclr  = register to be used to point to function's original frame pointer.
 #           This must not be 15.
 # Register Usage on Entry:
 #   R2  = Allocation size rounded to nearest doubleword (8 bytes)
 # Register Usage on Exit:
 #   R0  = Unpredictable
 #   R2  = Pointer to the area allocated
 #   R15 = New stack frame pointer.  Stack pointer before the macro call is 
 #         saved at the top of the stack.  Return from the function must use
 #         retbp or retbpx instead of return or returnx


        .macro allocx lclr:req
    .ifeq  \lclr-15  # 0= 0   # If new fpr is 15, error
        .error "New frame pointer register must not be 15"
        .exitm
    .endif
        lgr    \lclr,15              # Set up new local frame pointer
    .ifne  .L_bp  # If .L_bp != 0 (we have a local back pointer)
        lg     0,0(15)               # Get current back pointer
    .else
        lgr    0,15                  # Get the current stack pointer
        aghi   0,.L_local            # Calculate the back pointer
    .endif
        slgr   15,2                  # Allocate the storage (size in R2)
        lgr    2,15                  # Return the start of the allocated area
        aghi   15,-16                # Adjust for the back pointer area
        stg    0,0(15)               # Set the dynamic back pointer
        .endm
 
.endif # .ifndef .Labi_s390x_S
