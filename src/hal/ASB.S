.ifndef .LASB_S
.LASB_S = 1
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

 # This module provides general or commonly used Hardware Abstraction Layer support
 #
 # Dependencies:
 #   psw.S     For PSW macros and PSW related assigned storage locations
 #   util.S    For HAL utility macros
 #
 # Public Macros:
 #   asb         Generate the displacements for use of the 32-bit ASB
 #   asbg        Generate the displacements for use of the 64-bit ASB
 #
 # Internal Macros:
 #   
 #   hahword32   Generate a 32-bit ASB table .hword field
 #   hahword64   Generate a 64-bit ASB table .hword field
 #   halabort    Force a program check to inidicate an unrecoverable error
 #   halong32    Generate a 32-bit ASB table .long field
 #   halong64    Generate a 64-bit ASB table .long field
 #   hapsw32     Generate a 32-bit ASB table 64-bit PSW
 #   hapsw64     Generate a 64-bit ASB table 64-bit PSW
 #   hapswe64    Generate a 64-bit ASB table 128-bit PSW
 #   haptr32     Generate a 32-bit ASB table 32-bit pointer
 #   haptr64     Generate a 65-bit ASB table 64-bit pointer
 #
 # Stuctures:
 #   ASB       Architecture Support Block

        .include "psw.S"     # If not already included
        .include "util.S"    # If not already included

         .macro asb
         asbdefn yes,lo=1,ih=1,io=1
         .endm

         .macro asbg
         asgdefng yes,lo=1,ih=1,io=1
         .endm

         .macro halign32 value:req s=no
    .ifc \s,yes
         salign  \value
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         .align   \value
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .align   \value
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .align   \value
         .popsection
    .endif
    .endif
         .endm

          .macro halign64 value:req s=no
    .ifc \s,yes
         salign  \value
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         .align  \value
         .popsection
    .endif
    .endif
         .endm

         .macro habyte32 field:req s370bc=0 s370=0 s390=0 s=no
    .ifc \s,yes
         sbyte   \field
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         .byte    \s370bc
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .byte    \s370
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .byte    \s390
         .popsection
    .endif
    .endif
         .endm

         .macro habyte64 field:req s390x=0 s=no
    .ifc \s,yes
         sbyte  \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         .byte  \s390x
         .popsection
    .endif
    .endif
         .endm

         .macro hahword32 field:req s370bc=0 s370=0 s390=0 s=no
    .ifc \s,yes
         shword  \field
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         .hword   \s370bc
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .hword   \s370
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .hword  \s390
         .popsection
    .endif
    .endif
         .endm

         .macro hahword64 field:req s390x=0 s=no
    .ifc \s,yes
         shword  \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         .hword  \s390x
         .popsection
    .endif
    .endif
         .endm

         .macro halabort error=0xFFFF
         .hword 0x00bd,\error
         .endm

         .macro halong32 field:req s370bc=0 s370=0 s390=0 s=no
    .ifc \s,yes
         slong  \field
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         .long   \s370bc
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .long   \s370
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .long   \s390
         .popsection
    .endif
    .endif
         .endm

         .macro halong64 field:req s390x=0 s=no
    .ifc \s,yes
         slong  \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         .long  \s390x
         .popsection
    .endif
    .endif
         .endm

         .macro hapsw32 field:req sbc=0 abc=0 sec=0 aec=0 s390=0 a390=0 s=no
    .ifc \s,yes
         squad  \field
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         s370pswbc s=\sbc,p=0,a=\abc
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         s370psw s=\sec,p=0,a=\aec
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         s390psw s=\s390,p=0,a=\a390
         .popsection
    .endif
    .endif
         .endm

         .macro hapsw64 field:req sys=0 a=0 s=no 
    .ifc \s,yes
         squad \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         s390psw s=\sys,p=0,a=\a
         .popsection
    .endif
    .endif
         .endm

         .macro hapswe64 field:req sys=0 a=0 s=no 
    .ifc \s,yes
         socta \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         s390xpsw s=\sys,p=0,a=\a
         .popsection
    .endif
    .endif
         .endm

         .macro haptr32 field:req s370bc=0 s370=0 s390=0 s=no
    .ifc \s,yes
         slong  \field
    .else
    .if .Lhal_s370bc
         .pushsection ".text",3
         .long   \s370bc
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .long   \s370
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .long   \s390
         .popsection
    .endif
    .endif
         .endm

         .macro haptr64 field:req s390x=0 s=no
    .ifc \s,yes
         squad  \field
    .else
    .if .Lhal_s390x
         .pushsection ".text",6
         .quad  \s390x
         .popsection
    .endif
    .endif
         .endm

         .macro asbdefn s=no lo=0 ih=0 io=0
    .ifc \s,yes
         struct   .LASB
    .else # .ifc \s,yes
         halign32  8,\s
    .if .Lhal_s370bc
         .pushsection ".text",3
         .align   8
.Lioal_s370bc_asb:
         .popsection
    .endif
    .if .Lhal_s370
         .pushsection ".text",4
         .align   8
.Lioal_s370_asb:
         .popsection
    .endif
    .if .Lhal_s390
         .pushsection ".text",5
         .align   8
.Lioal_s390_asb:
         .popsection
    .endif
    .endif # .ifc \s,yes
    .if .Lhal_iolo+\lo
         # IHAL IOLO Public Abstractions
         haptr32   .LASB_ccw,.Liolo_ccw_chan,.Liolo_ccw_chan,.Liolo_ccw_s390,\s
         haptr32   .LASB_ena,.Liolo_ena_chan,.Liolo_ena_chan,.Liolo_ena_s390,\s
         haptr32   .LASB_enio,.Liolo_enio_chan,.Liolo_enio_chan,.Liolo_enio_s390,\s
         haptr32   .LASB_find,.Liolo_find_chan,.Liolo_find_chan,.Liolo_find_s390,\s
         haptr32   .LASB_io,.Liolo_io_chan,.Liolo_io_chan,.Liolo_io_s390,\s
         # IHAL IOLO Private Data
         halign32  8,\s
         hapsw32   .LASB_waitpsw,0xFE02,2,0x020A,2,0x020A,2,\s
         hapsw32   .LASB_runpsw,0x0000,.Liolo_run32,0x0008,.Liolo_run32,0x0008,.Liolo_run32,\s
         hahword32 .LASB_iodev,.LPSW_oldio+2,.LIO_dev,0,\s
         habyte32  .LASB_iodmsk,0x01,0x45,0x45,\s
    .endif
    .if .Lhal_ih+\ih
         halign32  8,\s
         # IHAL Public Abstractions
         haptr32   .LASB_ihinit,.Lihal_init32,.Lihal_init32,.Lihal_init32,\s
         haptr32   .LASB_ihcls,.Lihal_cls32,.Lihal_cls32,.Lihal_cls32,\s
         haptr32   .LASB_ihwait,.Lihal_wait32,.Lihal_wait32,.Lihal_wait32,\s
         habyte32  .LASB_ihsamsk,.LIHSR_S370bc,.LIHSR_S370,.LIHSR_ESA390,\s
         halign32  8,\s
         # IHAL Private Data
         haptr32   .LASB_ihext,.Lihal_s370bc_ext,.Lihal_s3x0_ext,.Lihal_s3x0_ext,\s
         haptr32   .LASB_ihio, .Lihal_s370_io,.Lihal_s370_io,.Lihal_s390_io,\s
         haptr32   .LASB_ihpgm,.Lihal_s370bc_pgm,.Lihal_s3x0_pgm,.Lihal_s390_pgm,\s
         haptr32   .LASB_ihsvc,.Lihal_s370bc_svc,.Lihal_s3x0_svc,.Lihal_s3x0_svc,\s
         halong32  .LASB_enanpsw,0x00000000,0x00080000,0x00080000,\s
         halong32  .LASB_disnpsw,0x00020000,0x000A0000,0x000A0000,\s
         halong32  .LASB_extdis,0xDFFF000F,0xDFFF000F,0xDFFF000F,\s   # CR0 disable
         halong32  .LASB_extena,0x2000FEE0,0x2000FEE0,0x2000FE50,\s   # CR0 enable
         hahword32 .LASB_nowtmsk,0x00F1,0x44F9,0x44F9,\s
         # IHAL PSW manipulation information
         hahword32 .LASB_ilcdis,0x0004,0x0002,0x0002,\s
         hahword32 .LASB_ioemsk,0xFE00,0x02A0,0x02A0,\s
         hahword32 .LASB_exemsk,0x0120,0x01A0,0x01A0,\s
         habyte32  .LASB_fmtmsk,0x00,0x80,0x80,\s
    .endif # .if .Lhal_ih
    .if .Lhal_io+\io
         halign32  8,\s
         # IOAL Private Data
         halong32  .LASB_cr2,0x00000000,0xFFFFFFFF,0x00000000,\s
         halong32  .LASB_cr6,0x00000000,0x00000000,0xFF000000,\s
         hapsw32   .LASB_waitpsw,0xFE02,2,0x0202,2,0x0202,2,\s
         hapsw32   .LASB_waitcs,0xFE02,.Lioal_qint_cs_done,0x0202,.Lioal_qint_cs_done,0,0,\s
         hapsw32   .LASB_ionpsw,s=\s
         # IOAL Public Abstractions
         haptr32   .LASB_ccw,.Lioal_ccw32,.Lioal_ccw32,.Lioal_ccw32,\s
         haptr32   .LASB_ioinit,.Lioal_init_s370,.Lioal_init_s370,.Lioal_init_s390,\s
         haptr32   .LASB_data,.Lioal_data_chan,.Lioal_data_chan,.Lioal_data_s390,\s
     .if .Lhal_s390x
         haptr32   .LASB_datp,.Lioal_datp_chan,.Lioal_datp_chan,.Lioal_datp_s390,\s
     .else
         haptr32   .LASB_datp,.Lioal_unsup,.Lioal_unsup,.Lioal_unsup,\s
     .endif
         haptr32   .LASB_doio,.Lioal_doio_chan,.Lioal_doio_chan,.Lioal_doio_s390,\s
         haptr32   .LASB_exio,.Lioal_exio32,.Lioal_exio32,.Lioal_exio32,\s
         haptr32   .LASB_qdev,.Lioal_qdev_chan,.Lioal_qdev_chan,.Lioal_qdev_s390,\s
         haptr32   .LASB_qint,.Lioal_qint_chan,.Lioal_qint_chan,.Lioal_qint_s390,\s
         haptr32   .LASB_sdev,.Lioal_sdev_chan,.Lioal_sdev_chan,.Lioal_sdev_s390,\s
         haptr32   .LASB_spsw,.Lioal_spsw_chan,.Lioal_spsw_chan,.Lioal_spsw_s390,\s
         haptr32   .LASB_stio,.Lioal_stio_chan,.Lioal_stio_chan,.Lioal_stio_s390,\s
         # IOAL Private Data
         haptr32   .LASB_ida,.Lioal_unsup,0,0,\s
         halong32  .LASB_ida32,0,4,4,\s
         halong32  .LASB_ida64,0,0,8,\s
         halong32  .LASB_idasz,0x0000,0x2000,0x4000,\s
         hahword32 .LASB_ioid,.LPSW_oldio+2,.LIO_dev,.LIO_ssid,\s
         hahword32 .LASB_amode,0,0,0x010D,\s
         hahword32 .LASB_pswmsk,0x00F7,0x00FF,0x00FF,\s
         habyte32  .LASB_idac,0x80,0x80,0x00,\s
         halign32  8,\s
    .endif # .if .Lhal_io
    .ifc \s,yes
         shere     .LASB_len
    .endif
         .endm

         .macro asbdefng s=no lo=0 ih=0 io=0
    .ifc \s,yes
         struct   .LASBG
    .else # .ifc \s,yes
    .if .Lhal_s390x
         .pushsection ".text",6
         .align   8
.Lioal_s390x_asb:
         .popsection
    .endif
    .endif # .ifc \s,yes
    .if .Lhal_iolo+\lo
         # IHAL IOLO Public Abstractions
         haptr64   .LASBG_ccw,.Liolo_ccw_s390x,\s
         haptr64   .LASBG_ena,.Liolo_ena_s390x,\s
         haptr64   .LASBG_enio,.Liolo_enio_s390x,\s
         haptr64   .LASBG_find,.Liolo_find_s390x,\s
         haptr64   .LASBG_io,.Liolo_io_s390x,\s
         # IHAL IOLO Private Data
         hapswe64  .LASBG_waitpsw,0x0202,2,\s
         hapswe64  .LASBG_runpsw,0x0000,.Liolo_run64,\s
    .endif
    .if .Lhal_ih+\ih
         halign64 8,\s
         # IHAL Public Abstractions
         haptr64   .LASBG_ihinit,.Lihal_init64,\s
         haptr64   .LASBG_ihwait,.Lihal_wait64,\s
         # IHAL Private Data - none
         hapsw64   .LASBG_waitpsw,0x0200,2,\s
         hapsw64   .LASBG_runpsw,0x0000,.Liolo_run64,\s
    .endif # .if .Lhal_ih
    .if .Lhal_io+\io
         halign64  8,\s
         # IOAL Public Abstractions
         haptr64   .LASBG_ioinit,.Lioal_init_s390x,\s
         haptr64   .LASBG_exio,.Lioal_exio64,\s
         haptr64   .LASBG_data,.Lioal_data_s390x,\s
         haptr64   .LASBG_datp,.Lioal_unsup,\s
         haptr64   .LASBG_doio,.Lioal_doio_s390x,\s
         haptr64   .LASBG_qint,.Lioal_qint_s390x,\s
         haptr64   .LASBG_sdev,.Lioal_sdev_s390x,\s
         haptr64   .LASBG_stio,.Lioal_stio_s390x,\s
         # IOAL Private Data
         halong64  .LASBG_cr2,0x00000000,\s
         halong64  .LASBG_cr6,0xFF000000,\s
         halong64  .LASBG_idasz,0x4000,\s
         hahword64 .LASBG_amode,0x010E,\s
         halign64  8,\s
    .endif # .if .Lhal_io
    .ifc \s,yes
         shere     .LASBG_len
    .endif
         .endm

.endif # .ifndef .LASB_S scope
