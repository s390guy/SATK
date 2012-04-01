.ifndef .Labi_s390_S
.Labi_s390_S = 1
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

 # ABI 32-bit Support
 #
 #  The following macros establish the GCC stack options in use
 #     Macro        Description
 #     stack     Define whether packed stack and/or back frame pointer is maintained
 #                  and how floating point registers are handled for s390
 #     stack370  Define whether packed stack and/or back frame pointer is maintained
 #                  and how floating point registers are handled for s370
 #
 #  The following macros initializes the ABI run-time environment
 #     Macro        Description
 #     abi32     Intitialize the stack and, optionally, the GOT registers
 #     abi_stack32  Provide a pointer for initializing the stack.  The pointer may
 #                  be used by the abi32 macro
 #
 #  The following macros define a function prolog
 #     Macro        Description
 #   * function  Defines the start of a s390 function and saves 
 #                  the caller's registers
 #     func370   Defines the start of a s370 function ans saves
 #                  the caller's registers
 #
 #  The following macros define the current stack frame.
 #     Macro        Description
 #     frame     Start a s390 or s370 ABI stack frame definition
 #     framecr   Create the initial frame on the s390 stack
 #     framecr370 Create the initial frame on the s370 stack
 #
 #  The following macros establish the preceding stack frame for the 
 #  current function
 #     Macro       Description
 #   * push      Establishes this function's s390 stack frame
 #     push370   Establishes this function's s370 stack frame
 #
 #  The following macros call a function
 #     Macro       Description
 #   * call      Call a local s390 function using PC relative addressing
 #     callr     Call a s390 function from a register (or GOT pointer)
 #     callptr   Call a local s370/s390 function with an inline pointer
 #
 #  The following macros return to a caller from a called function
 #     Macro       Description
 #     return    Return to a s370 or s390 caller
 #     returna   Return to a s370 or s390 caller after dynamic stack allocation
 #
 #  The following macros provide for dynamic allocation of stack storage
 #     Macro       Description
 #     alloc     Allocate storage from stack in s390 environment
 #     alloc370  Allocate storage from stack in s370 environment
 #
 #  The following macros support self relocation
 #     Macro       Description
 #     endrel    Terminate or mark a position within the self relocation list
 #     pointer   Create a self relocatable pointer
 #     reloc     Enable self relocation
 #
 #  * These macros may only be used in s390 environments.  These macros use
 #    instructions unavailable in s370.  If you want compatibility with both s370 
 #    and s390 environments, use the macros not flagged with an asterisk for this
 #    note.
 #
 #  These macros cooperate to provide in assembly language programs 32-bit ABI 
 #  functionality.  Three macros are provided to initialize the ABI.  Two are
 #  declarative in nature (stackx, framex) and the other provides run-time
 #  initialization (abi32).  They are typically used in the following sequence:
 #
 #          .include "ABI-s390.S"    # bring in these macros
 #          stack                    # Establish frame structure
 #          frame                    # Define the stack frame in use.
 #          .text                    # Start executable code
 #          basr   13,0              # Create my base register
 #  0b:                               
 #     [ Perform any additional initialization ]
 #          abi32 stack=.Lstack      # Establish the stack pointer
 #     [ It is now possible to define an call functions. ]
 #
 #          call  .Lafunc            # Call a declared function 
 #                                   # callr/callptr may also be used
 #
 #     [ other parts of the program ]
 #
 #  Declaring a function and establishing the local environment involves a sequence
 #  of macros at the start that preserves the caller's environment (functionx), 
 #  define the local stack usage (the ABI-lcls.S macros) environment and then 
 #  establishes it (pushx).
 #
 #     # Declare a new function
 #         function .Lafunc
 #      or fucn370  .Lafunc
 #     [ define local stack usage with falign, fbytes, fhword, flong, fquad]           
 #     [ define literals used - they of course can be anywhere addressable ]
 #         push/push370         # Now that my stack frame size is known, reserve it.
 #
 #     [ perform whatever this function is supposed to do ]
 #
 #         return               # Return to caller
 #
 #
 #  Finally, but not least, the stack needs to be established:
 #         abi_stack32 .Lstack  # Creates a pointer usable by abi32.  Room for the
 #                              # main entry to issues functions calls is provided.
 #         .end
 #

 # abi32 - Establish the run-time ABI register contents
 #  Macro Parameters:
 #       got    When specified, identifies the GOT register to be established and
 #              enables GOT usage.  The ABI requires register 12 to be specified.
 #       stack  When specified, the stack pointer register, 15, is initialized from
 #              the contents of the symbol specified.  This argument may use the 
 #              same symbol as specified by the abi_stack32 macro name argument.
 #       br     Specified the local base register (defaults to 13)
 #       b      Specifies the local base (defaults to 0b)

          .macro abi32 got stack br=13 b=0b
    .ifnb \stack
        l      15,\stack-\b(\br)    # Initialize the stack pointer
    .endif
    .ifnb \got
        l      \got,.+8-\b(\br)     # Location of the GOT table (provided by linker)
        b      .+8-\b(\br)          # Branch around the pointer
        .long  _GOT_begin           # Generated linker scripts provide this symbol
.L_abi_uses_got = 1                 # Tell other macros got is enabled 
    .endif
        .endm
        
 # abi_stack32 - Establish a 32-bit stack starting location
 #  Macro Parameters:
 #       name   Specifies the symbol name to be used for the pointer (required)
 #       size   Size of the stack to be created (required)
 #       end    Indicates the ending (lowest) address for the stack (defaults to .)
 #
 # See the note for the abi_stack_start macro in ABI.S for details.
        
        .macro abi_stack32 name:req size:req end=.
    .ifc \end,.      # Allow for the stack constant being here 
\name:  .long  \end+((11+\size-.L_fsize)/8)*8
    .else
\name:  .long  \end+((7+\size-.L_fsize)/8)*8
    .endif           # .ifc \end scope
        .endm

 # alloc370/alloca/allocax - Allocate dynamic storage in the stack frame
 #  Macro Parameters: none
 #   lclr  = register to be used to point to function's original frame pointer.
 #           This must not be 15.
 # Register Usage on Entry:
 #   R2  = Allocation size rounded to nearest doubleword (8 bytes)
 # Register Usage on Exit:
 #   R0  = Unpredictable
 #   R1  = Unpredictable
 #   R2  = Pointer to the area allocated
 #   R15 = New stack frame pointer.  Stack pointer before the macro call is 
 #         saved at the top of the stack.  Return from the function must use
 #         retbp or retbpx instead of return or returnx

        .macro alloc lclr:req
    .ifeq  \lclr-15  # 0= 0   # If new fpr is 15, error
        .error "New frame pointer register must not be 15"
        .exitm
    .endif
        lr     \lclr,15              # Set up new local frame pointer
    .ifne  .L_bp  # If .L_bp != 0 (we have a local back pointer)
        l      0,0(15)               # Get current back pointer
    .else
        lr     0,15                  # Get the current stack point
        ahi    0,.L_fsize            # Calculate the back pointer
    .endif
        slr    15,2                  # Allocate the storage (size in R2)
        lr     2,15                  # Return the start of the allocated storage
        ahi    15,-8                 # Adjust for the back pointer area
        st     0,0(15)               # Set the dynamic back pointer
        .endm
        
         .macro alloc370 lclr:req
    .ifeq  \lclr-15  # 0= 0   # If new fpr is 15, error
        .error "New frame pointer register must not be 15"
        .exitm
    .endif
        lr     \lclr,15              # Set up new local frame pointer
    .ifne  .L_bp  # If .L_bp != 0 (we have a local back pointer)
        l      0,0(15)               # Get current back pointer
    .else
        lr     0,15                  # Get the current stack point
        sl     0,9b-4(13)            # Calculate the back pointer (from push370)
    .endif
        slr    15,2                  # Allocate the storage (size in R2)
        lr     2,15                  # Return the start of the allocated storage
        la     1,8                   # Set up size of back pointer area
        slr    15,1                  # Adjust for back pointer area
        st     0,0(15)               # Set the dynamic back pointer
        .endm
        
 # call - Call a ABI function using local branch relative addressing
 #  Macro Parameters:
 #       func   symbol of the function being called (required)
 
        .macro call func:req
        bras   14,\func                     # Call the s390 function
        .endm

 # callptr - Call a ABI function using an inline pointer
 #  Macro Parameters:
 #       func    Specifies the symbol of the function being called.
 #       br      Specified the local base register (defaults to 13)
 #       b       Specifies the local base (defaults to 0b)
 #
 # Intended to be the logical replacement in s370 for the s390 call macro, but may
 # also be used in s390 environments.

        .macro callptr func:req reloc=no br=13 b=0b
        l      1,.+10-\b(\br)               # Locate the function being called
        basr   14,1                         # Call the function
        b      .+8-\b(\br)                  # Branch around the inline pointer
    .ifdef .L_relocb
1:      .text  1                            # Enter relocation list sub section
        .long  1b-.L_relocb                 # Define displacement to this pointer
        .text                               # Return to normal text sub section
    .endif
        .long  \func                        # Function address
        .endm

 # callr - Call a ABI function using a pointer in a register
 #  Macro Parameters:
 #       reg     The register containing the pointer (defaults to 1)
 #       got     When specified, identifies the function symbol of the address to be
 #               retrieved from the GOT and placed in reg before calling the 
 #               function.  Requires the GOT to be enabled by the abi32 macro.
 #
 #  May be used in either s370 or s390 environments.

        .macro callr reg=1 got
    .ifnb \got
        lgot   \reg,\got                    # Load the register from the GOT
    .endif
        basr   14,\reg                      # Call the function from a register
        .endm

 # endrel - Mark a position or end the self relocation list
 #  Macro Parameters:
 #      name   Establish a symbol that identifies the end of the self relocation 
 #             list (required)

        .macro endrel name:req
        .text  1         # Enter relocation list sub section
\name:  .text            # Give it a symbol and return to the norma text sub section
        .endm
        
 # frame - Establish the size and structure of the call stack frame
 #
 # The size is adjusted for the minimum required when stack macro argument packed=yes
 # is specified.

        .macro frame
    .ifdef .L_fsize
    .warning "ignoring attempt to redefine s370/s390 frame"
    .else
    .ifeq .L_pack    # .L_pack == 0, --> frame not packed
.L_bptr  =      0
.L_R2    =      8
.L_R3    =      12
.L_R4    =      16
.L_R5    =      20
.L_R6    =      24
.L_R7    =      28
.L_R8    =      32
.L_R9    =      36
.L_R10   =      40
.L_R11   =      44
.L_R12   =      48
.L_R13   =      52
.L_R14   =      56
.L_R15   =      60
.L_F0    =      64
.L_F2    =      72
.L_F4    =      80
.L_F6    =      88
.L_fsize =      96
     .else           # .L_pack != 0 --> stack frame is packed
.L_R6    =      0
.L_R7    =      4
.L_R8    =      8
.L_R9    =      12
.L_R10   =      16
.L_R11   =      20
.L_R12   =      24
.L_R13   =      28
.L_R14   =      32
.L_R15   =      36
.L_fsize =      40
     .ifne .L_fp # .L_fp !=0 --> fp=hard
.L_F4    =      40
.L_F6    =      48
.L_fsize =      56
     .endif          # End of .L_fphard scope
     .ifne .L_bp     # .L_bp != 0 --> stack frame back pointer is used
.L_bptr  =      .L_fsize
.L_fsize =      4+.L_fsize
     .endif          # End of .L_bp scope
     .endif          # End of .L_packed scope
     .endif          # End of ifdef .L_fsize scope
        .endm

 # framecr - Creates the initial s390 stack frame based upon the contents of R15
 #           environments
 #  Macro Parameters:
 #      locals Specify 'yes' to include room on the stack for local frame content
 #             (Default 'no')
 #      stkr   Register containing the bottom of the stack address (default 15)

        .macro framecr locals=no stkr=15
        srl    \stkr,3      # Make sure the stack is on a
        sll    \stkr,3      # ... doubleword boundary
     .ifc \locals,yes
        ahi    \stkr,(0-.L_local)  # Make room for my registers and locals
     .else
        ahi    \stkr,(0-.L_fsize)  # Make room for my registers
     .endif
        .endm

 # framecrx - Creates the initial stack s390x frame based upon the contents of R15
 #            environments
 #  Macro Parameters:
 #      locals Specify 'yes' to include room on the stack for local frame content
 #             (Default 'no')
 #      stkr   Register containing the bottom of the stack address (default 15)

        .macro framecr locals=no stkr=15
        srlg   \stkr,\stkr,3       # Make sure the stack is on a
        sllg   \stkr,\stkr,3       # ... doubleword boundary
     .ifc \locals,yes
        aghi   \stkr,(0-.L_local)  # Make room for my registers and locals
     .else
        aghi   \stkr,(0-.L_fsize)  # Make room for my registers
     .endif
        .endm
        
        
 # framecr370 - Creates the initial s370 stack frame based upon the contents of R15
 #  Macro Parameters:
 #      locals Specify 'yes' to include room on the stack for local frame content
 #             (Default 'no')
 #      stkr   Register containing the bottom of the stack address (default 15)
 #      br     Local base register (default 13)
 #      b      Local base (default 0b)
 
        .macro framecr370 locals=no stkr=15 br=13 b=0b
        srl    \stkr,3             # Make sure the stack is on a
        sll    \stkr,3             # ... doubleword boundary
        sl     \stkr,.+8-\b(\br)   # Make room for stack frame and optionally locals
        b      .+8-\b(\br)         # Branch around the frame size
     .ifc \locals,yes
        .long  .L_local
     .else  # .ifc \locals,yes
        .long  .L_fsize
     .endif # .ifc \locals,yes
        .endm
 
        
 # function - s390 Function Declaration
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
 #   R1      = Function address or unpredictable (if used, set by callr macro)
 #   R2-R6   = Function parameters, otherwise unpredictable
 #   R7-R11  = Unpredictable
 #   R12     = Global Offset Table address if present
 #   R13     = Calling function's base register (set by function macro)
 #   R14     = Calling functions return location (set by call or callr macro)
 #   R15     = Caller's stack frame pointer
 #   F0,F2   = Parameters passed to function (fp=hard only)
 #   F4,F6   = Unpredictable (fp=yes only)
 #   A0      = Reserved for thread local storage pointer
 #   A1-A15  = unpredictable
 #
 # Registers available for function usage
 #   R0-R11  = available
 #   R12     = Global Offset Table address if present, otherwise available
 #   R13     = reserved for function base register (set by function macro)
 #   R14     = available between function calls, but volatile across calls
 #   R15     = Called function's stack frame pointer (set by push macro)
 #   F0,F2,F4,F6 = available
 #   A0      = Reserved for thread local storage pointer
 #   A1-A15  = available
 #
 # Registers on Exit:
 #   R0,R1   = unpredictable
 #   R2      = Returned value (if a non-floating point value is returned),
 #             otherwise unpredictable
 #   R3-R5   = unpredictable
 #  return macro restores caller's R6-R15 and optionally F4 and F6
 #   R6-R12  = Calling function's original register content
 #   R13     = Calling function's base register
 #   R14     = Calling function's return location
 #   R15     = Calling function's stack frame pointer
 #   F0      = floating point return value (if return is a floating point value),
 #             otherwise unpredictable
 #   F2      = unpredictable
 #   F4,F6   = Calling function's original register content (fp=hard only)
 #   A0      = Reserved for thread local storage pointer
 #   A1-A15  = unpredictable

        .macro function name:req
        .align 2
.L_local = .L_fsize                        # Initialize local area on stack
\name:
     .ifeq  .L_pack  # If .L_pack == 0 --> packed=no
         stm    2,15,.L_R2(15)             # Save registers in caller's stack frame
     .else           # If .L_pack != 0 --> packed=yes
         stm    6,15,.L_R6(15)             # Save registers in caller's stack frame
     .endif          # end of .L_pack scope
     .ifne  .L_fp    # if .L_fp   != 0 --> fp=hard 
     .ifeq  .L_pack  # if .L_pack == 0 --> packed=no
         std    0,.L_F0(15)                # Save floating point register 0
         std    2,.L_F2(15)                # Save floating point register 2
     .endif
         std    4,.L_F4(15)                # Save floating point register 4
         std    6,.L_F6(15)                # Save floating point register 6
     .endif
         bras   13,9f                      # Setup base reg and lit pool pointer
0:
        .endm

 # func370 - s370 Function Declaration
 #  Macro Parameters:
 #       name = Declared function's symbol (required)
 #       abi    Specifies if it is safe to use r1 as the prolog base address
 #              (abi=yes) or not (abi=no). Defaults to no to play it safe.
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
 #   R1      = Funcion entry address (established in call370 macro used by caller)
 #   R2-R6   = non-floating point function parameters, otherwise unpredictable
 #   R7-R11  = Unpredictable
 #   R12     = Global Offset Table address if present, otherwise unpredictable
 #   R13     = Calling function's base register (set in func370 macro)
 #   R14     = Calling functions return location (set in call370 macro)
 #   R15     = Caller's stack frame pointer (provided by caller)
 #   F0,F2   = Parameters passed to function (fp=yes  only)
 #   F4,F6   = Unpredictable (fp=yes only)
 #
 # Registers available for function usage
 #   R0-R11  = available
 #   R12     = Global Offset Table address if present, otherwise available
 #   R13-R14 = unavailable
 #   R15     = function's stack frame (established by push370 macro)
 #   F0,F2,F4,F6 = available
 #
 # Registers on Exit:
 #   R0,R1   = unpredictable
 #   R2      = Returned value (if a non-floating point value is returned),
 #             otherwise unpredictable
 #   R3-R5   = unpredictable
 #  ret370 or ret370a resore R6-R15 and optionally F4 and F6
 #   R6-R12  = Calling function's original register content
 #   R13     = Calling function's base register
 #   R14     = Calling function's return location
 #   R15     = Calling function's stack frame pointer
 #   F0      = floating point return value (if return is a floating point value),
 #             otherwise unpredictable
 #   F2      = unpredictable
 #   F4,F6   = Calling function's original register content (fp=hard)
 
        .macro func370 name:req abi=no
.L_local = .L_fsize                 # Initialize local area on stack
        .align 2
\name:                              # R1 points here if ABI call
      .ifeq  .L_pack  # If .L_pack == 0 --> packed=no
         stm    2,15,.L_R2(15)      # Save registers in caller's stack frame
     .else            # If .L_pack != 0 --> packed=yes
         stm    6,15,.L_R6(15)      # Save registers in caller's stack frame
     .endif
     .ifne  .L_fp     # if .L_fp   != 0 --> fp=yes
     .ifeq  .L_pack   # if .L_pack == 0 --> packed=no
         std    0,.L_F0(15)         # Save floating point register 0
         std    2,.L_F2(15)         # Save floating point register 2
     .endif
         std    4,.L_F4(15)         # Save floating point register 4
         std    6,.L_F6(15)         # Save floating point register 6
     .endif
     .ifc \abi,yes
         bas    13,9f-\name(1)      # Setup function base and branch around literals
0:       
     .else
         basr   13,0                # Setup function base reg and lit pool pointer
0:       b      9f-.(13)            # R13 points here.  Branch around literals.
     .endif
        .endm
        
 # lgot - Load a 32-bit register with a GOT pointer
 #  Macro Parameters:
 #       reg   Register to be loaded with GOT pointer (required)
 #       name  Symbol name of the location to which the register will point 
 #             (required)

        .macro lgot reg:req name:req
    .ifndef .L_abi_uses_got
        .error "GOT not enabled"
    .endif
        l      \reg,\name@got(12)
        .endm

 # pointer - Create a self relocatable pointer
 #  Macro Parameters:
 #       ptr   An expression that defines the pointer's location (required)
 
        .macro pointer ptr:req
1:      .pushsection ".text",1
        .long  1b-.L_relocb
        .popsection
        .long  \ptr
        .endm
        
 # push - Push this function's stack frame onto the stack. 
 #        Adjusts stack pointer downward in s390 environments creating a stack
 #        frame on the stack.

        .macro push
.L_local = ((.L_local+7)/8)*8              # Make stack frame is doubleword sized
        .align 2                           # Make sure aligned after literal pool
    .ifne  .L_bp     # If .L_bp   != 0 --> fp=hard
9:      lr     1,15                        # Load the current stack pointer
        ahi    15,-(.L_local)              # Allocate my frame on the stack
        st     1,.L_bptr(15)               # Save back pointer on my stack
    .else
9:      ahi    15,-(.L_local)              # Allocate my frame on the stack
    .endif
        .endm

 # push370 - Push this function's stack frame onto the stack. 
 #           Adjusts stack pointer downward in s370 environments

        .macro push370
.L_local = ((.L_local+7)/8)*8              # Make stack frame is doubleword sized
        .align 2                           # Make sure aligned after literal pool
        b      .-0b+8(13)                  # Branch around my frame size (do I need?)
        .long  .L_local                    # Local frame size
    .ifne  .L_bp     # If .L_bp   != 0 --> bp=yes
9:      lr     1,15                        # Load the current stack pointer
        sl     15,9b-0b-4(13)              # Allocate my frame on the stack
        st     1,.L_bptr(15)               # Save back pointer on my stack
    .else            # If .L_bp   == 0 --> bp=no
9:      sl     15,9b-0b-4(13)              # Allocate my frame on the stack
    .endif
        .endm
        
 # reloc - Establish ability for self relocation
 #  Macro Parameters:
 #       name  Provides a name for locating the start of the self relocation 
 #             entries. (required)
 #       base  Identfies the base of the displacements stored in a self relocation
 #             entry (required)

        .macro reloc name:req base:req
.L_relocb = \base
        .text  1
\name:  .text  0
        .endm
        
 # return - Return from an ABI function to its caller
        
        .macro return
    .ifne .L_bp      # If .L_bp   != 0 --> return using back pointer (bp=yes)
        l      15,.L_bptr(15)              # Get back pointer from my stack
.L_stack = 0                               # Use regular stack displacement
    .else            # If .L_bp   == 0 --> return without using back pointer (bp=no)
.L_stack = .L_local                        # Use my stack size + stack displacement
    .endif
    .ifne .L_fp      # If .L_fp   != 0 --> using floating point registers
        ld     4,.L_stack+.L_F4(15)        # Restore caller's F4
        ld     6,.L_stack+.L_F6(15)        # Restore caller's F6
    .endif
        lm     6,15,.L_stack+.L_R6(15)     # Restore caller's R6-R15
        br     14                          # Return to caller
        .endm

        .macro returna
        l      15,0(15)                    # Get back pointer from my stack
    .ifne .L_fp      # If .L_fp   != 0 --> using floating point registers
        ld     4,.L_F4(15)                 # Restore caller's F4
        ld     6,.L_F6(15)                 # Restore caller's F6
    .endif
        lm     6,15,.L_R11(15)             # Restore caller's R6-R15
        br     14                          # Return to caller
        .endm

 # stack/stack370 - Define the attributes of the 32-bit stack frame in this assembly
 #  Macro Parameters:
 #       packed   Determines whether the standard sized frame (packed=no) or a 
 #                compressed frame size is used (packed=yes). (Default packed=no)
 #       fp       Determines whether a caller's floating point registers should be 
 #                saved in the caller's stack frame (fp=hard) or not (fp=soft).
 #                (Default fp=hard)
 #       bp       Determines whether the back pointer will be placed in the 
 #                called function's stack frame (bp=yes) or not (bp=no). 
 #                (Default bp=no)
 
        .macro stack packed=no fp=soft bp=no
    .ifc \packed,yes  # if packed == yes
.L_pack   = 1
    .else             # if packed != yes
.L_pack   = 0
    .endif
    .ifc \fp,hard     # if fp == hard
.L_fp     = 1
    .else             # if fp != hard
.L_fp     = 0
    .endif
    .ifc \bp,yes      # if bp == yes
.L_bp     = 1
    .else             # if bp != yes
.L_bp     = 0
    .endif
.L_abi    = 1         # Set the ABI to s390 32-bit
        .endm
        
        .macro stack370 packed=no fp=hard bp=no
        stack  packed=\packed fp=\fp bp=\bp
.L_abi    = 0         # Set the ABI to s370 32-bit (overrides the setting by stack)
        .endm

.endif # .ifndef .Labi_s390_S
