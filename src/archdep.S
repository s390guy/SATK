.ifndef .Larchdep_S
.Larchdep_S = 1
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
 
 # This module provides low level architecture dependent instruction macros.
 # These macros are for coding convenience.
 
 # Architecture dependent word alignment
 
            .macro alignx
            .ifdef __zarch__
               .align 8
            .else
               .align 4
            .endif
            .endm
 
 # Architecture dependent BRANCH ON COUNT REGISTER macro
 
            .macro bctxr r1:req r2:req
            .ifdef __zarch__
               bctgr \r1,\r2
            .else
               bctr \r1,\r2
            .endif
            .endm
 
 # Architecture dependent LOAD CONTROL macro
 
            .macro lctlx r1:req r3:req b2d2:req
            .ifdef __zarch__
               lctlg \r1,\r3,\b2d2
            .else
               lctl  \r1,\r3,\b2d2
            .endif
            .endm
            
 # Architecture dependent LOAD macro
 
            .macro lx  r1:req b2d2:req
            .ifdef __zarch__
               lg  \r1,\b2d2
            .else
               l   \r1,\b2d2
            .endif
            .endm
 
 # Architecture dependent LOAD AND TEST REGISTER macro
 
            .macro ltxr r1:req r2:req
            .ifdef __zarch__
               ltgr   \r1,\r2
            .else
               ltr    \r1,\r2
            .endif
            .endm
            
 # Architecture dependent LOAD REGISTER macro
 
            .macro lxr r1:req r2:req
            .ifdef __zarch__
               lgr  \r1,\r2
            .else
               lr   \r1,\r2
            .endif
            .endm

 # Architecture dependent SHIFT RIGHT SINGLE LOGICAL macor
 
            .macro srlx r1:req b2d2:req
            .ifdef __zarch__
               srlg  \r1,\r1,\b2d2
            .else
               srl   \r1,\b2d2
            .endif
            .endm
            
 # Architecture dependent STORE CONTROL macro
 
            .macro stctx r1:req r3:req b2d2:req
            .ifdef __zarch__
               stctg \r1,\r3,\b2d2
            .else
               stctl \r1,\r3,\b2d2
            .endif
            .endm
            
 # Architecture dependent STORE REGISTER macro
 
            .macro stx  r1:req b2d2:req
            .ifdef __zarch__
               stg  \r1,\b2d2
            .else
               st   \r1,\b2d2
            .endif
            .endm
            
 # Architecture dependent SUBTRACT REGISTER macro
 
            .macro sxr r1:req r2:req
            .ifdef __zarch__
               sgr  \r1,\r2
            .else
               sr   \r1,\r2
            .endif
            .endm

 # Architecture dependent word macro
 
            .macro wordx val:req
            .ifdef __zarch__
               .quad \val
            .else
               .long \val
            .endif
            .endm
            
.endif
