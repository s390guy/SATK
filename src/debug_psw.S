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

.ifdef .L__psw_arch
    .ifeq .L__psw_arch
       #  S/370 Basic-control mode (.L__psw_arch == 0)
    .endif
    .ifeq .L__psw_arch-1
       #  S/370 Extended-control mode (.L__psw_arch == 1)
    .endif
    .ifdef .L__psw_arch-2
        # ESA/390 mode (.L__psw_arch == 2)
    .endif
    .ifdef .L__psw_arch-4
        # z/Architecture mode (.L__psw_arch == 3)
    .endif
.else
        # .L__psw_arch not defined
.endif
