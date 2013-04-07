.ifndef .Lstorages_S
.Lstorages_S = 1
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

.ifdef .Lstg_features

.if .Lstg_perm
            .include "memperm.S"   # Include the permanent memory allocator macros
            memperm
.endif # .if .Lstg_perm

.else
            .error "storages.S suppressed due to missing stgfeat macro options"
.endif # .ifdef .Lstg_features

.endif # .ifndef .Lstorages_S scope