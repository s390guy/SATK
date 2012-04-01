.ifndef .Labi_lcls_S
.Labi_lcls_S = 1 
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
 
 #  The following macros define local fields on the stack frame.  These macros
 #  must be used following the function definition, but before the local frame
 #  is created using a push macro 
 #     falign    Align the current size of the stack frame
 #     fbytes    Define any number of bytes on the current stack frame
 #     fend      End the current stack frame definition
 #     fhere     Define a symbol with the current stack frame displacement
 #     fhword    Define a halfword on the current stack frame
 #     finit     Initialize a 32-bit stack frame for local usage
 #     finitx    Initialize a 64-bit stack frame for local usage
 #     flong     Define a fullword on the current stack frame
 #     fquad     Define a quadword on the current stack frame
 #     freserve  Reserved unlabled space in the current stack frame
 #
 # finit[x] are not normally required for local frame usage.  However, for special
 # contexts, such as stack creation within interrupts handlers, finit[x] may be 
 # needed.

        .macro falign size:req
.L_local = ((.L_local+\size-1)/\size)*\size
        .endm

        .macro fbyte name:req
\name    =      .L_local
.L_local =      .L_local+1
        .endm
        
        .macro fbytes name:req number=1
\name    =      .L_local
.L_local =      .L_local+\number
        .endm
        
        .macro fend
        falign  8
        .endm
        
        .macro fhere name:req
\name   =       .L_local
        .endm

        .macro fhword name:req
\name    =      .L_local
.L_local =      .L_local+2
        .endm

        .macro finit
.L_local =      .L_fsize
        .endm
        
        .macro finitx
.L_local =      .L_fsizeg
        .endm
        
        .macro flong name:req
\name    =      .L_local
.L_local =      .L_local+4
         .endm
        
         .macro focta name:req
\name    =      .L_local
.L_local =      .L_local+16
         .endm
         
        .macro fquad name:req
\name    =      .L_local
.L_local =      .L_local+8
        .endm
        
        .macro freserve size:req
.L_local =      .L_local+\size
        .endm

.endif # .ifndef .Labi_lcls_S
