.ifndef .Lutil_S
.Lutil_S = 1
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

 # This module provides useful macros for programs intended for multiple
 # architectures, for example, the Hardware Abstraction Layer itself or programs
 # that use the HAL.  Some macros have arhitecture specific variants useful in
 # a specific architecture.
 #
 # Dependencies:
 #   struct.S    For structure assist macros
 #
 # Public Macros:
 #   halptr      Specify a Hardware Abstraction Layer pointer's location
 #   halptr32    Define a Hardware Abstraction Layer 32-bit pointer
 #   halptr64    Define a Hardware Abstraction Layer 64-bit pointer
 #   iam         Insert a new addressing mode into the PSW on ESA/390 or 
 #               z/Architecture platforms
 #   iam32       Insert or set a new addressing mode on any 32-bit platform
 #   savecc24    Save condition code on System/370 mode platforms
 #   savecc      Save condition code on ESA/390 mode platforms
 #   saveccg     Save condition code on z/Architecture mode platforms
 #   shalptr     Specify a Hardware Abstraction Layer pointer in a structure
 #   xam         Extract the current addressing mode from the PSW on any 32-bit
 #               platform
 #   xamg        Extract the current addressing mode from the PSW on 
 #               z/Architecture platforms
 #
 # Stuctures:
 #   ASB       Architecture Support Block

        .include "struct.S"  # If not already included

 # halptr - Specify a Hardware Abstraction Layer pointer's location in a structure
 #  Macro Parameters:
 #       disp   Displacement from the start of the structure of this HAL pointer
 #              (required)
 #       bit32  Symbol name of the 32-bit HAL pointer (required)
 #       bit64  Symbol name of the 64-bit HAL pointer (required)

         .macro halptr disp:req bit32:req bit64:req
\bit64  =      \disp
\bit32  =      \disp+4
        .endm

 # halptr32 - Define a Hardware Abstraction Layer 32-bit pointer
 #  Macro Parameters:
 #       name   Symbol of the location to which this pointer points (required)

        .macro halptr32 name:req
        .long  0,\name
        .endm

 # halptr64 - Define a Hardware Abstraction Layer 64-bit pointer
 #  Macro Parameters:
 #       name   Symbol of the location to which this pointer points (required)

        .macro halptr64 name:req
        .quad  \name
        .endm

 # iam - Insert addressing mode in ESA/390 or z/Architecture
 #  Macro Parameters:
 #       reg    Register containing the value previously provided by a xam or xamg
 #              macro.  The contents of reg are altered during the macro's 
 #              execution.  reg must not be the same as the current base register.
 #       br     Current base register (default 13)
 #       b      Current base symbol (default 0b)
 #
 # Warning: When going from a lower addressing mode to a higher addression mode,
 # for example from 31-bit to 64-bit addressing mode, high order register bits 
 # previously ignored will start to be used.  Ensure high order register bits used 
 # for addressing purposes are zeros before use following the addressing mode change.
 # This is best done before the iam macro is likely to know which register contents
 # have addressing significance.

         .macro iam reg:req br=13 b=0b
         ic     \reg,.+8-\b(\reg,\br)
         b      .+10-\b(\br)
         .byte  0x0C,0x0D,0x00,0x0E
         .hword 0x0100   # SAM24, SAM31, SAM64 instruction template
         ex     \reg,.-2-\b(\br)  # Change the addressing mode
         .endm

 # iam32 - Insert addressing mode in any 32-bit architecture
 #  Macro Parameters:
 #       reg    Either a register containing the value previously provided by the 
 #              xam macro or the register to be used in setting the addressing mode
 #              specified by the am parameter. (required)
 #       am     The required addressing mode.  Specify either '24' or '31'.  
 #              Otherwise the contents of register specified by the reg parameter
 #              is used.  (Default is to use the reg parameter)
 #       br     Current base register (default 13)
 #       b      Current base symbol (default 0b)
 #
 # Note: A general 32-bit platform specific implementation is required because
 # not all 32-bit architectures support SET ADDRESSING MODE instructions.  When
 # specifying either '24' or '31'.  The am parameter allows this macro to be 
 # used in lieu of a SET ADDRESSING MODE instruction.
 #
 # Warning: If reg is specified as '0', the addressing mode is unchanged.
 # The warning for the iam macro also applies.

        .macro iam32 reg:req am=reg br=13 b=0b
   .ifc \am,24
        sr     \reg,\reg
   .endif
   .ifc \am,31
        la     \reg,1(0)
   .endif
        sll    \reg,31
        la     \reg,.+6-\b(\br)
        basm   0,\reg
        .endm

 # savecc24 - Save condition code on System/370 mode platforms
 #  Macro Parameters:
 #       reg    Register in which condition code is to be saved
 #
 # Note: A s/370 specific implementation is required because S/370 does not 
 # support the INSERT PROGRAM MASK instruction.

        .macro savecc24 reg:req
        balr   \reg,0      # Get the cc in bits 2,3
        sll    \reg,2      # Clear the ILC from the register (cc in bits 0,1)
        srl    \reg,30     # Move cc to bits 30,31
        .endm

 # savecc - Save condition code on ESA/390 mode platforms
 #  Macro Parameters:
 #       reg    Register in which condition code is to be saved

        .macro savecc reg:req
        ipm    \reg         # Get the cc in bits 2,3
        srl    \reg,28      # Move the cc to bits 30,31
        .endm

 # saveccg - Save condition code on z/Architecture mode platforms
 #  Macro Parameters:
 #       reg    Register in which condition code is to be saved

        .macro saveccg reg:req
        ipm    \reg          # Get the cc in bits 34,35
        sllg   \reg,\reg,32  # Clear unchanged bits 0-31 (cc in bits 2,3)
        srlg   \reg,\reg,60  # Move cc to bits 62,63
        .endm

 # shalptr - Specify a Hardware Abstraction Layer pointer in a structure
 #  Macro Parameters:
 #       bit32  Symbol name of the 32-bit HAL pointer (required)
 #       bit64  Symbol name of the 64-bit HAL pointer (required)

         .macro shalptr bit32:req bit64:req
         slong  \bit64
         slong  \bit32
         .endm

 # xam - Extract the current addressing mode in ESA/390
 #  Macro Parameters:
 #       reg    Register into which the addressing mode is to be extracted

         .macro xam reg:req
         basr   \reg,0
         srl    \reg,31
         .endm

 # xamg - Extract the current addressing mode in z/Architecture
 #  Macro Parameters:
 #       reg    Register into which the addressing mode is to be extracted

         .macro xamg reg:req
         tam
         saveccg \reg
         .endm

.endif # .ifndef .Lutil_S scope
