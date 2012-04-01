.ifndef .LCMS_S
.LCMS_S = 1
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

 # CMS Volume ID Structure
.LCMS_VOLID  = 0
.LCMS_cms1   = 0x00   # .byte 4  CMS1 EBCDIC constand
.LCMS_volume = 0x04   # .byte 6  Volume ID in EBCDIC
.LCMS_ver    = 0x0A   # .hword   Version, must be zero
.LCMS_blksiz = 0x0C   # .long    Disk block size
.LCMS_fsorig = 0x10   # .long    CMS File system origin in blocks
.LCMS_usable = 0x14   # .long    Usable Cylinders or blocks
.LCMS_formatd= 0x18   # .long    Formated Cylinders or blocks
.LCMS_disksiz= 0x1C   # .long    Disk size in CMS blocks
.LCMS_used   = 0x20   # .long    Number of CMS blocks in use
.LCMS_fstsize= 0x24   # .long    FST size in bytes
.LCMS_fstpblk= 0x28   # .long    Number of FST's per CMS block
.LCMS_fmtdate= 0x2C   # .byte 6  Format Date 0xYY,0xMM,0xDD,0xHH,0xMM,0xSS
.LCMS_resv1  = 0x32   # .hword   reserved
.LCMS_reservd= 0x34   # .long    Disk offset from block 1 to 1st reserved blk
.LCMS_nxthole= 0x38   # .long    Allocation map next hole (0xff)
.LCMS_hblkhol= 0x3C   # .long    HBLK displacement to next hole (0xff)
.LCMS_usermap= 0x40   # .long    Displacement to user part of alloc map (0xff)
.LCMS_resv2  = 0x44   # .long    reserved
.LCMS_segment= 0x48   # .byte 8  Name of shared segment (all 0x00's)
.LCMD_VOLID_len = 80

 # CMS1 constant
 
            .macro cms1
            .ascii "\xC3\xD4\xE2\xF1"
            .endm

.endif # .ifndef .Lcp
