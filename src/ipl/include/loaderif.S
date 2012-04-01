.ifndef .Lloaderif_S
.Lloaderif_S=1
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

 # This macro creates the loader interface
 # Arguments:
 #   rec    = physical block size of IPL program
 #   fmt    = 'S for stream block format or 'D for directed block format
 #   lowc   = 'Y for LOWC segment supported, 'N if not supported
 #   eop    = 'P uses physical end-of-file, 'H uses header directed header flag
 #   pad    = 'Y for padding to physical block size, 'N for no padding
 #   data   = 'Y if processor updates interface data, 'N if it does not
 #   dev    = device support flags
 #   arch   = architecture support flags
 #   adj    = fullword containing the adjustment to base for 0b location
 #   br     = base register, defaults to 12
 #   b      = lable of the current base, defaults to 0b

           .macro   loaderif rec fmt lowc eop pad data dev arch adj br=12 b=0b
           .section .loader,"a",@progbits   # Start .loader section
.Llodr:
0:
.Lrecsize  =        \rec
.Lreadsiz: .hword   .Lrecsize                # Physical block size
           .byte    \fmt,\lowc,\eop,\pad,\data,\dev,\arch  # Parms and flags
           .fill    7,1,0x00                 # reserved, must be zero
.Lprepdat:                                   # preparation process data
.Lpgmntry:#.long    0                        # CDROM: Boot program entry address
.Lpgmsec: #.long    0                        # FBA: Boot program starting sector
.Lpgmcyl:  .hword   0                        # CKD: IPL program's starting cyl #
.Lpgmtrk:  .hword   0                        # CKD: IPL program's starting head #
.Lpgmrec:  .byte    0                        # CKD: IPL program's starting record #
.Lckdblks: .byte    0                        # CKD: Number of blocks per track
.Lckdmcyl: .hword   0                        # CKD: Maximum CKD cylinder number
.Lckdmtrk: .hword   0                        # CKD: Maximum CKD head number
           .fill    4,1,0x00
.Lreqarch: .byte    0                        # required CPU architecture
.Lreqdev:  .byte    0                        # required device support
           .align   2
           stm      0,15,0x200               # Save IPL parameters in IPLP area
           basr     \br,0                    # R12 as base
.Llodrtemp:   # Temporary base until base register is adjusted to point to 0: above
           sll      12,1                     # Make sure high-order bit is zero,
           srl      12,1                     # ..otherwise, 64-bit problems later
           sl       12,\adj-.Llodrtemp(12)   # Now loader header is addressable
           .endm

 # This macro generates the standard disabled wait conditions:
 #   000FFF = General non-specific error
 #   000FFE = I/O problem with IPL device
 #   000FFD = Problem entering z/Architecture
 #   000FFC = Problem entering program

           .macro exits fff=.Lexit ffe=.Lexitio ffd=.Lexitarch ffc=.Lexitpgm br=12 b=0b
\fff:      lpsw     .Lpswfff-\b(\br)
\ffe:      lpsw     .Lpswffe-\b(\br)
\ffd:      lpsw     .Lpswffd-\b(\br)
\ffc:      lpsw     .Lpswffc-\b(\br)
           .align   8
.Lpswffc:  psw      s=0x0002,p=0,a=0x0ffc
.Lpswffd:  psw      s=0x0002,p=0,a=0x0ffd
.Lpswffe:  psw      s=0x0002,p=0,a=0x0ffe
.Lpswfff:  psw      s=0x0002,p=0,a=0x0fff
           .endm

.endif # .ifndef .Lloaderif_S scope
