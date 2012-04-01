.ifndef .Lerrnotbl_S
.Lerrnotbl_S = 1
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

 # This table is designed to be searched using BXLE instruction
        .macro errnotbl platform:req name:req
    .ifc \platform,linux
        .align 2
\name:  .long  7f,10,8f
7:      .hword 0
        .ascii "SUCCESS "
        .hword -1
        .ascii "EPERM   "
        .hword -2
        .ascii "ENOENT  "
        .hword -3
        .ascii "ESRCH   "
        .hword -4
        .ascii "EINTR   "
        .hword -5
        .ascii "EIO     "
        .hword -6
        .ascii "ENXIO   "
        .hword -7
        .ascii "E2BIG   "
        .hword -8
        .ascii "ENOEXEC "
        .hword -9
        .ascii "EBADF   "
        .hword -10
        .ascii "ECHILD  "
        .hword -11
        .ascii "EAGAIN  "
        .hword -12
        .ascii "ENOMEM  "
        .hword -13
        .ascii "EACCES  "
        .hword -14
        .ascii "EFAULT  "
        .hword -15
        .ascii "ENOTBLK "
        .hword -16
        .ascii "EBUSY   "
        .hword -17
        .ascii "EEXIST  "
        .hword -18
        .ascii "EXDEV   "
        .hword -19
        .ascii "ENODEV  "
        .hword -20
        .ascii "ENOTDIR "
        .hword -21
        .ascii "EISDIR  "
        .hword -22
        .ascii "EINVAL  "
        .hword -23
        .ascii "ENFILE  "
        .hword -24
        .ascii "EMFILE  "
        .hword -25
        .ascii "ENOTTY  "
        .hword -26
        .ascii "ETXTBSY "
        .hword -27
        .ascii "EFBIG   "
        .hword -28
        .ascii "ENOSPC  "
        .hword -29
        .ascii "ESPIPE  "
        .hword -30
        .ascii "EROFS   "
        .hword -31
        .ascii "EMLINK  "
        .hword -32
        .ascii "EPIPE   "
        .hword -33
        .ascii "EDOM    "
        .hword -34
8:      .ascii "ERANGE  "
        .hword 0x8000
        .ascii "UNKNOWN "
    .endif
        .endm
.endif # .ifndef .Lerrnotbl_S scope
