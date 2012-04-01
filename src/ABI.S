.ifndef .Labi_S
.Labi_S = 1
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

 # This module provides a set of generic wrapper scripts simplifying ABI programming
 # in an ABI transparent manner.  For details on the operations of these macros
 # refer to ABI-s390.S or ABI-s390x.S files.
 #
 #  Provided macros:
 #    Macro          Description
 #   abi          Explicitly select the ABI and its frame structure options
 #   abi_alloc    Dynamically allocate storage from the stack
 #   abi_call     Call an ABI declared function by symbol name
 #   abi_callp    Call an ABI declared function with an in-line pointer
 #   abi_callr    Call an ABI declared function based upon a register (or GOT ptr)
 #   abi_endrel   Mark or terminate the self relocation list
 #   abi_frame    Define the selected ABI frame structure
 #   abi_framecr  Create the initial stack frame based upon R15
 #   abi_func     Declare an ABI function
 #   abi_options  Select the ABI and its frame structure options based upon the
 #                __ARCH__ assembler symbol.  The ipl_elf assemble function in the
 #                medfun bash script defines this symbol in the GNU as command line.
 #   abi_push     Establish this function's stack frame on the stack
 #   abi_ptr      Create a self relocatalbe pointer
 #   abi_reloc    Enable self relocation
 #   abi_ret      Pop this function's stack frame from the stack and return to the
 #                function's caller.
 #   abi_reta     Return after dynamic stack allocation
 #   abi_run      Establish the run-time support for the selected ABI.
 #   abi_stack_start  Identify the bottom of the function call stack.
 #
 # Usage of the Macros:
 #
 #  These macros cooperate to provide in assembly language programs 32- or 64-bit 
 #  ABI functionality.  Three macros are provided to initialize the ABI.  Two are
 #  declarative in nature (abi, abi_options) and the other provides run-time
 #  initialization (abi_run).  They are typically used in the following sequence:
 #
 #          .include "ABI.S"         # bring in these macros
 #          abi_option               # Establish frame structure based upon __ARCH__
 #  # or
 #          abi                      # Establish frame structure by selection
 #
 #          .text                    # Start executable code
 #          basr   13,0              # Create my base register
 #  0b:  
 #     [ Perform some initialization, for example, establishing a base register]
 #          abi_run stack=.Lstack    # Enter 64-bit mode, if needed and set stack ptr.
 #     [ It is now possible to define and call functions. ]
 #
 #          abi_call .Lafunc         # Call a declared function 
 #                                   # abi_callp or abi_callr may also be used
 #
 #     [ other parts of the program ]
 #
 #  Declaring a function and establishing the local environment involves a sequence
 #  of macros at the start that preserves the caller's environment (abi_func), 
 #  define the local stack usage (the ABI-lcls.S macros) environment and then 
 #  establishes it (abi_push).
 #
 #     # Declare a new function
 #         abi_func .Lafunc
 #     [ define local stack usage with falign, fbyte, fbytes, fhword, flong, fquad]           
 #     [ define literals used - they of course can be anywhere addressable ]
 #         abi_push            # Now that my stack frame size is known, reserve it.
 #
 #     [ perform whatever this function is supposed to do ]
 #
 #         abi_ret             # Return to caller 
 #
 #  Finally, but not least, the stack needs to be established:
 #
 #         abi_stack_start .Lstack
 #         .end


 # abi - Explicitly select the ABI used by this assembly
 #  Macro Parameters:
 #      arch          Specify the desired ABI architecture: s370, s390 or s390x.
 #                    Defaults to s390 with a warning.
 #      packed/fp/bp  Meaning as defined in ABI-s390.S and ABI-s390x.S

        .macro abi arch=abi packed=no fp=hard bp=no
    .ifc \arch,s370
        stack370 packed=\packed fp=\fp bp=\bp
        frame
    .else
    .ifc \arch,s390
        stack packed=\packed fp=\fp bp=\bp
        frame
    .else
    .ifc \arch,s390x
        stackx packed=\packed fp=\fp bp=\bp
        framex
    .else
        .warning "unrecognized arch argument, defaulting to s390"
        stack packed=\packed fp=\fp bp=\bp
        frame
    .endif
    .endif
    .endif
        .endm

 # abi_alloc - Dynamically allocate storage on the stack
 #  Macro Parameters:
 #       lclr     Identify the register to be used after the allocation for access
 #                to the function's local area after the stack pointer has been 
 #                adjusted due to the storage allocation.  Register 15 must NOT be
 #                used.  (Required)
 #
 # Register Usage on Entry:
 #   R2  = Allocation size rounded to nearest doubleword (8 bytes)
 # Register Usage on Exit:
 #   R0  = Unpredictable
 #   R1  = Unpredictable
 #   R2  = Pointer to the area allocated
 #   R15 = New stack frame pointer.  Stack pointer before the macro call is 
 #         saved at the top of the stack.  Return from the function must use
 #         abi_reta instead of abi_ret because the mechanism for returning to the 
 #         calling function is different after storage has been allocated 
 #         dynamically.

        .macro abi_alloc lclr:req
    .ifeq .L_abi     # if .L_abi   == 0 --> abi_s370
        alloc370 \lclr
    .else
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        allocx \lclr
    .else            #                  --> abi_s390
        alloc \lclr
    .endif
    .endif
        .endm

 # abi_call - Call a declared function based upon its symbol name.
 #  Macro Parameters:
 #       name     Identify the function being called by its declared symbol. 
 #                (Required)

        .macro abi_call name:req
    .ifeq .L_abi     # if .L_abi   == 0 --> abi_s370
        callptr \name
    .else
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        callx \name
    .else            #                  --> abi_s390
        call \name
    .endif
    .endif
        .endm    

 # abi_callp - Call a declared function with an in-line pointer
 #  Macro Parmeters:
 #       func    The declared function's symbol as used in abi_func
 #       got     if not blank (got=yes), the pointer is fetched from the GOT
 #       br      Local base register (default 13, ABI standard)
 #       b       Local base location (default 0b)
 #       
        .macro abi_callp func:req br=13 b=0b 
     .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        callptrx \func br=\br b=\b
    .else             #                  --> abi_s390 or s370
        callptr \func br=\br b=\b
    .endif
        .endm

 # abi_callr - Call a declared function based upon an address in a register
 #  Macro Parameters:
 #       reg     Identify the register containing the function address.  Defaults
 #               to the ABI standard of register 1.
 #               abi_callr without arguments generates: basr 14,1
 #       got     When specified, optionally pre-loads the register from the GOT
 #               based upon the function's declared symbol.
 #               For example:  abi_callr got=.La_function

        .macro abi_callr reg=1 got
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        callrx reg=\reg \got
    .else            #                  --> abi_s390 or s370
        callr reg=\reg \got
    .endif
        .endm

 # abi_endrel - Mark a position or end the self relocation list
 #  Macro Parameters:
 #      name   Establish a symbol that identifies the end of the self relocation 
 #             list (required)

        .macro abi_endrel name:req
    .ifeq .L_abi-2    # if .L_abi-2 == 0 --> abi_s390x
        endrelx name=\name
    .else             #                  --> abi_s390 or s370
        endrel  name=\name
    .endif
        .endm

 # abi_frame - Define the frame structure used by this assembly, per selected ABI

        .macro abi_frame
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        framex
.Labi_fsize = .L_fsizeg
    .else            #                  --> abi_s390 or s370
        frame
.Labi_fsize = .L_fsize
    .endif
        .endm

 # abi_framecr - Create the initial stack frame based upon the contents of R15
 #  Macro Parameters:
 #     locals  Specify 'yes' to include room on the stack for local frame content
 #             (Default 'no')

        .macro abi_framecr locals=no
    .ifeq .L_abi     # if .L_abi   == 0 --> abi_s370
        framecr370 locals=\locals
    .else
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        framecrx locals=\locals
    .else            #                  --> abi_s390
        framecr locals=\locals
    .endif
    .endif 
         .endm

 # abi_func - Declare an ABI function
 #  Macro Parameters:
 #       name    Define the function's symbol (required)

        .macro abi_func name:req
    .ifeq .L_abi     # if .L_abi   == 0 --> abi_s370
        func370 \name
    .else
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        functionx \name
    .else            #                  --> abi_s390
        function \name
    .endif
    .endif
        .endm

  # abi_options - Establish the ABI specified by the __ARCH__ assembler symbol
  #  Macro Parameters:
  #      packed/fp/bp  Meaning as defined in ABI-s390.S and ABI-s390x.S

        .macro abi_options packed=yes fp=soft bp=no
  .ifdef __ARCH__
    .ifeq __ARCH__-1  # if __ARCH__-1 == 0      --> Architecture is s370
           abi arch=s370 packed=\packed fp=\fp bp=\bp
    .else
    .ifeq __ARCH__-3  # if __ARCH__-3 == 0      --> Architecture is s390x
           abi arch=s390x packed=\packed fp=\fp bp=\bp
    .else             # if __ARCH__=2 != 0      --> Assume __ARCH__ == 1, or s390       
           abi arch=s390 packed=\packed fp=\fp bp=\bp
    .endif # .ifeq __ARCH__-3 scope
    .endif # .ifeq __ARCH__-1 scope
  .else              # if __ARCH__ not defined  --> default to s390
           abi arch=s390 packed=\packed fp=\fp bp=\bp
  .endif  # .ifdef __ARCH__ scope
        .endm

 # abi_ptr - Create a self relocatable pointer
 #  Macro Parameters:
 #       ptr   An expression that defines the pointer's location (required)

        .macro abi_ptr ptr:req
     .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        pointerx ptr=\ptr
    .else             #                  --> abi_s390 or s370
        pointer  ptr=\ptr
    .endif
        .endm

 # abi_push - Establish this functions stack frame on the stack

        .macro abi_push
    .ifeq .L_abi     # if .L_abi   == 0 --> abi_s370
        push370
    .else
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        pushx
    .else            #                  --> abi_s390
        push
    .endif
    .endif
        .endm

 # abi_reloc - Establish ability for self relocation independent of the ELF
 #  Macro Parameters:
 #       name  Provides a name for locating the start of the self relocation 
 #             entries. (required)
 #       base  Identfies the base of the displacements stored in a self relocation
 #             entry (required)
        
        .macro abi_reloc name:req base:req
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        relocx name=\name,base=\base
    .else            #                  --> abi_s390 or s370
        reloc  name=\name,base=\base
    .endif
        .endm    

 # abi_ret - Return from a called function
        
        .macro abi_ret
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        returnx
    .else            #                  --> abi_s390 or s370
        return
    .endif
        .endm

 # abi_reta - Return to the calling function after stack storage has been 
 #            dynamically allocated.

        .macro abi_reta 
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        returnax
    .else            #                  --> abi_s390 or s370
        returna
    .endif
        .endm
        
 # abi_run - Establish the selected ABI's operational mode
 #  Macro Parameters:
 #       stack/got   Meaning as defined by abi32 (in ABI-s390.S) or abi64 
 #                   (in ABI-s390x.S)
 #       cpur/statr/fail  Meaning as defined by enable64 (in ABI-s390x.S) 
        
        .macro abi_run stack:req got cpur statr fail
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> abi_s390x
        enable64 cpur=\cpur,statr=\statr,fail=\fail
        abi64 stack=\stack got=\got
    .else            #                  --> abi_s390 or s370
        abi32 stack=\stack got=\got
    .endif
        .endm
        
 # abi_stack_start - Identify the start of the stack
 #  Macro Parameters
 #       name   Specifies the symbol name to be used for the pointer (required)
 #       size   Size of the stack to be created (required)
 #       end    Indicates the ending (lowest) address for the stack (defaults to .)
 #
 # Note: The stack grows downward in storage, meaning from higher storage addresses 
 # to lower storage addresses.  The highest storage address is referred to as the 
 # 'bottom' of the stack.  The lowest storage address (the end macro argument) is
 # referred to as the 'top' of the stack. An initialized stack contains a single 
 # stack frame that contains no local stack usage, in essence a place to store the 
 # context of the base program that includes an area to store its registers when 
 # calling an ABI function.  The initial stack frame size is determined by the 
 # options selected by the abi_frame macro.  The stack frame size for the assembly is 
 # provided by two assembler symbols: 
 #     .L_fsize (32-bit archs) and 
 #     .L_fsizeg (64-bit arch).
 # Conceptually this looks like this in storage:
 #
 # low address    +--->top of stack (end macro parameter)
 # |              |
 # V              |
 #                |
 #                |
 #                |                 ^ stack grows in this direction
 #    size parm --+                 |
 #                |                 |
 #                |      (start) 1st frame <-------+---R15 (stack pointer)
 #                |                                |
 #                |                                +------- .L_fsize or .L_fsizeg
 #                |                                |      initial frame (no locals)
 # high address   +--->bottom of stack     <-------+
 #
 # The purpose of this macro is to create an address constant with the address of
 # the 'start' location based upon the size of the stack (size parmaeter) and its 
 # top (end parameter).  The macro calculates the value of start and provides this:
 #
 # name:  .long   start or
 # name:  .quad   start
 #
 # Ultimately, the start address is used to initialze R15, the stack pointer.
 #
 # The macro also assumes that the current .text subsection is the highest numbered
 # subsection, being placed at the end of the ELF object .text section.  If the
 # abi_stack_start macro is used in a multiple subsection program, it is recommended
 # to create a symbol at the end of the highest number .text subsection and use that
 # symbol as the argument to the end parameter rather than letting it default to '.'.
 #
 # Further this macro assumes that the stack will follow (be at higher storage
 # addresses) than the IPL ELF program.  This does create the potential for the 
 # stack to overlay the IPL ELF during execution, but in practice, this has not been
 # a problem with a large stack size, for example, 4096.

        .macro abi_stack_start name:req size:req end=.
    .ifeq .L_abi-2   # if .L_abi-2 == 0 --> 64-bit ABI
        abi_stack64 name=\name size=\size end=\end
    .else            #                  --> 32-bit ABI
        abi_stack32 name=\name size=\size end=\end
    .endif           # .ifeq .L_abi-2 scope
        .endm

        .include "ABI-s390.S"
        .include "ABI-s390x.S"
        .include "ABI-lcls.S"

.endif # .ifndef .Labi_S
