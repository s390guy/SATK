.ifndef .LSTORAGE_S
.LSTORAGE_S = 1
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

 # This module brings into the assembly all of the publicly exposed storage
 # management interfaces.  The storage subsystem integrates with the Hardware
 # Abstraction Layer but does not require it.
 #
 # Currently only the permament memory allocator is supported.  Future additions
 # may be page allocators or slob/slab type allocators, bit maps, etc.

 # stgfeat - Specify storage subsystem features enabled
 #  Macro Parameters:
 #       perm     Specify 'yes' to support permanent memory allocator (default 'no')
 #       bit32    Specify 'yes' to generate 32-bit functions (default 'no')
 #       bit64    Specify 'yes' to generate 64-bit functions (default 'no')
 #       s390     Specify 'yes' to generate s390 functions (default 'no')
 #       hal      Specify 'yes' to use halfeat assembly options.  Overrides bit32, 
 #                bit64 and s390 parameters (default 'no')

            .macro stgfeat perm=no,bit32=no,bit64=no,s390=no,hal=no
    .ifdef .Lstg_features
            .warning "redefinition of storage subsytem features ignored"
            .exitm
    .endif # .ifdef .Lstg_features
.Lstg_features = 1

.Lstg_perm = 0
.Lstg_32bit = 0
.Lstg_64bit = 0
.Lstg_s390_only = 0

     .ifc \perm,yes
.Lstg_perm = 1
     .endif # .ifc perm,yes

     .ifc \hal,yes
        .ifndef .Lhal_features
            .error "halfeat macro missing, required when 'hal=yes' specified"
            .exitm
        .else
.Lstg_32bit = .Lhal_32bit
.Lstg_64bit = .Lstg_64bit
.Lstg_s390_only = .Lstg_s390_only
        .endif # .ifndef .Lhal_features 
     .else
        .ifc \bit32,yes
.Lstg_32bit = 1     
        .endif # .ifc \bit32,yes
        .ifc \bit64,yes
.Lstg_64bit = 1
        .endif # .ifc \bit64,yes
        .ifc \s390,yes
.Lstg_32bit = 1
.Lstg_s390_only = 1
        .endif # .ifc \s390,yes
     .endif # .ifc \hal,yes
     .ifeq .Lstg_32bit+.L64bit
            .error "neither 32- nor 64-bit functions specified, one is required"
            .exitm
     .endif # .ifeq .Lstg_32bit+.L64bit

     .ifc \perm,yes
.Lstg_perm = 1
     .endif # .ifc perm,yes
            .endm

.endif # .ifndef .LSTORAGE_S scope
