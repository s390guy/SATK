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

.ifdef __s370__
   .ifdef __bcmode__
       #  S/370 Basic-control mode (__s370__ defined, __bcmode__ defined)
   .else
       #  S/370 Extended-control mode (__s370__ defined, __bcmode__ not defined)
   .endif
.endif
.ifdef __s390__
        # ESA/390 mode (__s390__ defined)
.endif
.ifdef __s390x__
        # z/Architecture mode (__s390x__ defined)
.endif
.ifdef __zarch__
        # z/Architecture mode (__zarch__ defined)
.endif
