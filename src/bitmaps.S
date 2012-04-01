.ifndef .Lbitmaps_S
.Lbitmaps_S = 1
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
 
 # This module provides a structure and initialization macro for managing a
 # bitmap.
 #
 # Regions and segments use 11 bits, or 2048 entries
 # Pages use 8 bits, or 256 entries per

 # Dependencies:
            .include "struct.S" 
          
 #  Structures provided by this module
 #     structure    Description
 #     bitmaps    Defines a bit map array
 #
 #  Macros provided by this module
 #     defbm      Builds in an assembly a bit map definition
 
            struct .Lbms       # Alignment to doubleword boundary recommended
            slong  .Lbmsa64    # Address of the bit map in storage (64-bit)
            slong  .Lbmsa      # Address of the bit map in storage (32-bit)
            slong  .Lbmsmax    # Maximum bit number supported by the bit map, 0-n
            slong  .Lbmslen    # Length of the bit map in bytes
            shere  .Lbms_len   # Length of the bms structure in bytes (not the bitmap)
            
 # defbm - Assemble a bitmap definition
 #  Macro Parameters:
 #       name   Specifies the symbol name of the bitmap definition (required)
 #       bits   Maximum number of bits supported by the bitmap (defaults to 0)
 #       addr   Symbol or absolute address of the bitmap array (defaults to 0)
 #       init   Byte value to which the bit map will be initialized (defaults to 0xFF)
 #
 # The 'addr' argument must not default to 0 if a bmbld macro will be used to
 # assemble the bitmap.
 
            .macro defbm name:req bits=0 addr=0 init=0xFF
            .align 8
\name:
     .ifeq .L__psw_arch-3    # 64-bit architecture
            .quad  \addr
     .else                   # 32-bit architecture
            .long  0,\addr   
     .endif # .ifeq .L__psw_arch-3
            .long  (\bits)-1
\name\()_len = (((\bits)+7)/8)*8
            .long  \name\()_len
\name\()_init = \init
            .endm
 
 # bmbld - Assemble a bitmap into the program based upon a defbm specification
 #  Macro Parameters:
 #       addr   Specifies the symbol of 'addr' defbm argument defining the bitmap
 #              (required)
 #       defbm  Specifies the symbol of 'name' defbm argument defining the bitmap
 #              (required)
 #
 # For run-time construction, see the functions .Lbmbld(64) 
 
           .macro bmbld addr:req defbm:req
\addr:     .fill  \defbm\()_len,1,\defbm\()_init
           .endm
 
.endif # .ifndef .ifndef .Lbitmaps_S