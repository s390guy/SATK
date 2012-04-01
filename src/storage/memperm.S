.ifndef .Lmemperm_S
.Lmemperm_S = 1
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

 # This module provides for permanent memory allocation.  Allocations start from
 # absolute address 0 and proceed to higher addresses.  The permanent memory
 # allocator is provided as a macro, allowing either a 32-bit, a 64-bit or both 
 # allocators to be generated depending upon the stgfeat macro options.

 #   Macro        Description
 #   memperm    Permamnently allocate portions of absolute storage.

 # memperm - Permamnently allocate portions of absolute storage.  No mechanism
 #           is provided to free these allocations, hence, their permanent status.
 #  Macro Parameters:
 #       br     Current base register (defaults to 13)
 #       b      Current base (defaults to 0b)
 #
 # .Lmemperm  - 32-bit permanent memory allocation function
 # .Lmempermg - 64-bit permanent memory allocation function
 #
 # Register Usage for both functions:
 #   Input:
 #      R1   = Size in bytes of area to be allocated.  A value of 0 will cause
 #             the next allocation to be based upon the next higher aligned location.
 #      R2   = Allocation alignment in bytes.  Values must be in units of powers of
 #             2, for example, 1, 2, 4, 8, etc.  Values <=0 are ignored.
 #   Output:
 #      R1   = Start of permanently allocated area
 #   Processing:
 #      R7   = Alignment factor
 #      R8   = Next address to allocate
 #      R9   = Alignment mask
 #      R10  = Allocation size

        .macro memperm br=13 b=0b
    .ifndef .Lstg_features
        .error "memperm suppressed due to missing stgfeat macro in assembly"
        .exitm
    .endif
    .if .Lstg_32bit
      .if .Lstg_s390_only
        function .Lmemperm               # Start the s390 .Lmemperm function
        push                             # Create stack frame and save caller's regs
      .else
        func370 .Lmemperm                # Start the .Lmemperm function
        push370                          # Create stack frame and save caller's regs
      .endif # .if .Lstg_s390_only
        lr     10,1                      # Save allocation size
        l      8,.L_memperm-\b(\br)      # Fetch the next address
        ltr    7,2                       # Was an alignment provided?
        bnp    .L_memperm_no_align-\b(\br)   # ..No, just allocate
        bctr   7,0                       # Turn value into alignment mask/factor
        alr    8,7                       # Add the alignment factor - 1
        x      7,.L_memperm_xor-\b(\br)  # Turn factor -1 into mask
        nr     8,7                       # starting location now aligned
.L_memperm_no_align:
        lr     1,8                       # Return the new starting location
        alr    8,10                      # Add the allocation size
        st     8,.L_memperm-\b(\br)      # Set the new next available location
        return                           # Return to caller
    .ifeq .Lstg_64bit
        .align 4
.L_memperm:     .long 0                  # Next available absolute location
.L_memperm_xor: .long -1                 # Value to turn alignment factor into a mask
    .endif # .ifeq .Lstg_64bit
    .endif # .if .Lstg_32bit
    .if .Lstg_64bit
        functionx .Lmempermg             # Start the .Lmempermg function
        pushx                            # Create stack frame and save caller's regs
        lgr    10,1                      # Save allocation size
        lg      8,.L_mempermg-\b(\br)    # Fetch the next address
        ltgr    7,2                      # Was an alignment provided?
        jnp    .L_mempermg_no_align      # ..No, just allocate (ignore <= 0)
        bctgr  7,0                       # Turn value into alignment mask/factor
        algr    8,7                      # Add the alignment factor - 1
        xg      7,.L_mempermg_xor-\b(\br) # Turn factor - 1 into mask
        ngr     8,7                      # starting location now aligned
.L_mempermg_no_align:
        lgr     1,8                      # Return the new starting location
        algr    8,10                     # Add the allocation size
        stg     8,.L_mempermg-\b(\br)    # Set the new next available location
        returnx                          # Return to caller
        .align 8
.L_mempermg:.quad 0                      # Next available address for allocation
.L_mempermg_xor: .quad -1 
    .if .Lstg_32bit
.L_memperm = .L_mempermg+4               # Provide symbols for 32-bit function
.L_memperm_xor = .L_mempermg_xor
    .endif # .if .Lstg_32bit
    .endif # .if .Lstg_64bit
        .endm

.endif # .ifndef .Lmemperm_S
