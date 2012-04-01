.ifndef .Lstruct_S
.Lstruct_S = 1 
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

 #  The following macros define struct fields.
 #     salign    Align the current size of the structure
 #     sbyte     Define a byte in the structure
 #     sbytes    Define any number of bytes in the structure
 #     shere     Define a symbol with the current structure displacement
 #     shword    Define a halfword in the structure
 #     slong     Define a fullword in the structure
 #     squad     Define a quadword in the structure
 #     sreserve  Reserved unlabled space in the structure
 #     struct    Define the start of a new structure
 #

 # WARNING: If you encounter a "symbol definition loop" when using these macros
 # there is a missing 'struct' macro

 # Macro Parameters
 #   name     Establish a symbol associated with this field within the structure
 #            (required by sbyte, sbytes, shere, shword, slong, socta, squad)
 #   delta    A signed value indicating a change of the location by the signed
 #            value (sorg defaults to 0)
 #   loc      The symbol used to maintain the current location within the structure.
 #            Normally the default is sufficient, but is needed when more than one
 #            structure is being defined in parallel within the program.
 #            (all macros default to .L_struct)
 #   size     Provide the size related to the field definition
 #            (required by salign, sreserve; sbytes defaults to 1)

        .macro salign size:req loc=.L_struct
\loc      = ((\loc+\size-1)/\size)*\size
        .endm

        .macro sbyte name:req loc=.L_struct
\name    =      \loc
\loc     =      \loc+1
        .endm

        .macro sbytes name:req size=1 loc=.L_struct
\name    =      \loc
\loc     =      \loc+\size
        .endm

        .macro shere name:req loc=.L_struct
\name   =       \loc+0
        .endm

        .macro shword name:req loc=.L_struct
\name    =      \loc
\loc     =      \loc+2
        .endm

        .macro slong name:req loc=.L_struct
\name    =      \loc
\loc     =      \loc+4
        .endm

        .macro socta name:req loc=.L_struct
\name    =      .L_struct
.L_struct=      .L_struct+16        
        .endm

        .macro sorg delta=0 loc=.L_struct
\loc     =      \loc+\delta
        .endm

        .macro squad name:req loc=.L_struct
\name    =      \loc
\loc     =      \loc+8
        .endm
        
        .macro sreserve size:req loc=.L_struct
\loc     =      \loc+\size
        .endm

        .macro struct name:req at=0 loc=.L_struct
\name    =      \at
\loc     =      \at
        .endm

.endif # .ifndef .Lstruct_S
