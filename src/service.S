.ifndef .Lservice_S
.Lservice_S = 1
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

 # This module contains definitions for use of the Service Processor and 
 # the SERVICE CALL instruction

 # Relationship of Service Processor control blocks for writing text messages 
 # spccb
 #   spevb
 #      spmdb
 #        spgo   May be repeated
 #        spmto  May be repeated
 #           "message text to write"
 #
 # Example message
 # sccb:
 #          SPCCB = 0x8000
 #  +----dc    XL8 '00.81.00.00.00.00.ff.ff'  129=0x81  8000 + 81 = 8081
 #  |              |_____| =========================^
 #  |       SPEVB = 0x8008
 #  |+---dc    XL6 '00.79.02.00.00.00'        121=0x79  8008 + 79 = 8081
 #  ||             |_____| =========================^
 #  ||      SPMDB = 0x800E
 #  ||+--dc    XL12'00.73.00.01.d4.c4.c2.40.00.00.00.01' 
 #  |||            |     |                    115=0x73  800e + 73 = 8081
 #  |||            |_____| =========================^
 #  |||     SPGO  = 0x801A
 #  ||| +-dc    XL4'00.38.00.01'              56=0x38   801a + 38 = 8052
 #  ||| |          |_____| ====================================^
 #  ||| +-dc    52x'00'
 #  |||     SPMTO = 0x8052
 #  ||| +-dc    XL4'00.2f.00.04'              47=0x2F   8052 + 2f = 8081
 #  ||| |           |____| ====================================^
 #  ||| | dc    XL6'10.00.00.00.00.00'
 #  ||| |   Message = 0x805C
 #  +++-+-dc   CL37'This is a test message'
 #          end of message = 0x8081
 #
 # Here is an example of how to code a Message Data Write SCCB using the macros
 # Each of the identified length fields must be increased by the length of the 
 # actual message being written
 #
 #            .align   16
 #.Lucp2spcb:
 #            spccb    to=.Lucp2msg                   # Length increased for text
 #.Lucp2sevb:
 #            spevb    to=.Lucp2msg,type=.Lspe_msg    # Length increased for text
 #.Lucp2smdb:
 #            spmdb    to=.Lucp2msg                   # Length increased for text
 #            spgo
 #.Lucp2smto:
 #            spmto    to=.Lucp2msg                   # Length increased for text
 #.Lucp2msg:
 #            .fill    256,1,0x40                     # Message text buffer area

 # servc - Macro to generate SERVICE CALL instruction

        .macro servc r1:req r2:req
        .insn  rre,0xB2200000,\r1,\r2
        .endm

 # Service Call Comamnds (servc r1)
.Lsclp_read_scp_info    = 0x00020001
.Lsclp_read_ifl_info    = 0x00120001
.Lsclp_read_chp_info    = 0x00030001
.Lsclp_read_csi_info    = 0x001C0001
.Lsclp_read_xst_map     = 0x00250001
.Lsclp_write_event_data = 0x00760005
.Lsclp_read_event_data  = 0x00770005
.Lsclp_write_event_mask = 0x00780005

 # Service Call Control Block (servc r2)
.Lsccb_len      = 0     # .hword  Total length of the SCCB
.Lsccb_flag     = 2     # .byte   Flag byte
.Lsscb_sync     = 0x80  #            Sychronous request flag
.Lsccb_resv1    = 3     # .hword  reserved
.Lsccb_type     = 5     # .byte   Request type
.Lsccb_var      = 0x80  #            Variable request type
.Lsccb_reason   = 6     # .byte   Reason code (See SCCB Reason Codes)
.Lsccb_resp     = 7     # .byte   Response class code (See SCCB Response Codes)
.Lsscb_hdr_len  = 8     #         Lenghth of the SCCB header

 # SCCB Reason Codes
.Lsccb_reas_none        = 0x00
.Lsccb_reas_not_pgbndry = 0x01
.Lsccb_reas_odd_length  = 0x02
.Lsccb_reas_too_short   = 0x03
.Lsccb_reas_noaction    = 0x02
.Lsccb_reas_standby     = 0x04
.Lsccb_reas_invalid_cmd = 0x01
.Lsccb_reas_invalid_rscp= 0x03
.Lsccb_reas_improper_rsc= 0x05
.Lsccb_reas_invalid_rsc = 0x09

 # SCCB Response Codes
.Lsccb_resp_block_error = 0x00   # Data block error
.Lsccb_resp_info        = 0x10   # Information returned
.Lsccb_resp_complete    = 0x20   # Command complete
.Lsccb_resp_backout     = 0x40   # Command backed out
.Lsccb_resp_reject      = 0xF0   # Command rejected

	        .macro spccb to sync=0x00 var=0x00
	        .word  \to-.                  # length    # _SCCB_HEADER
	        .byte  \sync                  # flag
	        .word  0                      # resv1
	        .byte  \var                   # type
	        .byte  0xFF                   # reason code
	        .byte  0xFF                   # response class
	        .endm

 # SCP Info Request (follows SCCB header)
.Lscp_realinum  = 0      # .hword  Number of storage increments installed
.Lscp_realiszm  = 2      # .byte   Size of each real storage increment in MB
.Lscp_realbszk  = 3      # .byte   Size of each storage block in KB
.Lscp_realiint  = 4      # .hword  Real storage increment block interleave interval
.Lscp_resv2     = 6      # .hword  reserved
.Lscp_numvpu    = 8      # .hword  Number of CPU's
.Lscp_offcpu    = 10     # .hword  Offset from the start to the CPU info array
.Lscp_numhsa    = 12     # .hword  Number of HSA's
.Lscp_offhsa    = 14     # .hword  Offset from the start to the HSA info array
.Lscp_loadparm  = 16     # .quad   LOADPARM value
.Lscp_xpndinum  = 24     # .long   Number of expanded storage increments installed
.Lscp_xpndsz4K  = 28     # .long   Number of 4K blocks per expanded storage increment
.Lscp_xpndenum  = 32     # .hword  Number of expanded storage elements installed
.Lscp_resv3     = 34     # .hword  reserved
.Lscp_vectssiz  = 36     # .hword  Vector section size
.Lscp_vectpsum  = 38     # .hword  Vector partial sum number
.Lscp_ifm       = 40     # .quad   Installed facilities
.Lscp_resv4     = 48     # .quad   reserved
.Lscp_maxresgp  = 56     # .hword  Maximum resource group
.Lscp_resv5     = 58     # 6 bytes reserved
.Lscp_nummpf    = 64     # .hword  Number of entries in MPF information array
.Lscp_offmpf    = 66     # .hword  Offset from the start to the MPF info array
.Lscp_resv6     = 68     # .long   reserved
.Lscp_cfg       = 72     # 6 bytes Config characteristics
.Lscp_rcci      = 78     # .long   Capacity
.Lscp_cfg11     = 82     # .byte   Config characteristics byte 11
.Lscp_numcrl    = 83     # .byte   Maximum number of copy and reassign list elements
.Lscp_etrtol    = 84     # .long   ETR sync check tolerance
.Lscp_resv60    = 88     # 3 bytes reserved
.Lscp_maxvm     = 91     # .byte   Maximum guest storage size
.Lscp_grzm      = 92     # .long   Address increment size in units of 1M
.Lscp_grnmx     = 96     # .quad   Maximum incr num when larger than 64K or ESAME
.Lscp_resv8     = 104    # 16 bytes reserved
.Lscp_len       = 120

 # CPU Information Array Entry
.Lcpu_cpa       = 0      # .byte    CPU Address
.Lcpu_tod       = 1      # .byte    TOD clock number
.Lcpu_cpf       = 2      # 12 bytes RCPU faclity map
.Lcpu_ptyp      = 14     # .byte    Processor type
.Lcpu_ksid      = 15     # .byte    Crypto unit identifier
.Lcpu_len       = 16     # Length of the CPU Information Array Entry

 # Processor Types
.Lcpu_CP        = 0      # Central Processor
.Lcpu_ICF       = 1      # Coupling Facility
.Lcpu_IFA       = 2      # Integrated Facility Application Processor (ZAP)
.Lcpu_IFL       = 3      # Integrated Facility for Linux
.Lcpu_SUP       = 5      # Subsystem Processor

# Service Processor Event Block
.Lspe_len       = 0      # .hword   Service Processor Event Length
.Lspe_type      = 2      # .byte    Event type
.Lspe_flag      = 3      # .byte    Event flag
.Lspe_resv      = 4      # .hword   reserved
.Lspe_blk_len   = 6      # Event structure length

# Service Processor Event Block Types
.Lspe_opcmb  = 0x01      # Operator Command (read)
.Lspe_msg    = 0x02      # Message from CP (write)
.Lspe_statch = 0x08      # State change
.Lspe_pri    = 0x09      # Priority message (read/write)
.Lspe_cpid   = 0x0B      # Control Program Ident (write)
.Lspe_cpcmd  = 0x20      # Control Program operator command (read)

# Service Processor Event Block Flags
.Lspe_succ   = 0x80      # Event successful

        .macro spevb to type flag=0x00
        .word  \to-.                   # totlen   # _SCCB_EVD_HDR
        .byte  \type                   # type
        .byte  \flag                   # flag
        .word  0                       # resv
        .endm

# Service Processor Message Data Block
.Lspd_len       = 0      # .hword   Service Processor Message Data Block length
.Lspd_type      = 2      # .hword   Data block type (0x0001 = Message Block)
.Lspd_tag       = 4      # .long    0xD4C4C240 = 'MDB ' = Tag
.Lspd_rev       = 8      # .long    Revision code (0x00000001)

	    .macro spmdb to
	    .word  \to-.                   # Length
	    .word  1                       # type     # _SCCB_MCB_BK
	    .long  0xd4c4c240              # tag
	    .long  1                       # revision code
	    .endm

# Service Processor Graphic Object

        .macro spgo
	    .word  8f-.                    # length   # _SCCB_OBJ_HDR
	    .word  1                       # type
	    .long  0                       # seq      # _SCCB_MGO_BK
	    .byte  0,0,0,0,0,0,0,0,0,0,0   # time
	    .byte  0                       # resv1
	    .byte  0,0,0,0,0,0,0           # date
	    .byte  0                       # resv2
	    .long  0                       # mflag
	    .long  0                       # presattr
	    .long  0                       # bckattr
	    .byte  0,0,0,0,0,0,0,0         # sysname
	    .byte  0,0,0,0,0,0,0,0         # jobname
8:
	    .end

 # Service Processor Message Text Object
.Lspm_len       = 0      # .hword   Message structure length (including mssage)
.Lspm_type      = 2      # .hword   0x0004 = Message Text Object
.Lspm_lt0       = 4      # .byte    Line Type Flag byte 0
.Lspm_lt1       = 5      # .byte    Line Type Flag byte 1
.Lspm_ctl       = 6      # .byte    Pres attr - byte 0 - control
.Lspm_clr       = 7      # .byte    Pres attr - byte 1 - color
.Lspm_hi        = 8      # .byte    Pres attr - byte 2 - highlighting
.Lspm_int       = 9      # .byte    Pres attr - byte 3 - intensity
.Lspm_to_len    = 10     # Service Processor Message Text Object Header Length

 # Service Processor Message Flag 0 Line Types
.Lspm_ctrl      = 0x80   # Control text
.Lspm_label     = 0x40   # Label text
.Lspm_data      = 0x20   # Data text
.Lspm_end       = 0x10   # Last line
.Lspm_prompt    = 0x08   # Prompt line
.Lspm_dbcs      = 0x04   # Double byte character set
.Lspm_mix       = 0x02   # Mixed single and double byte chars

 # Service Processor Message Flag 1 Line Types
.Lspm_ovrrid    = 0x01   # Foreground presentation field override

 # Service Processor Message Control Flags
.Lspm_alarm      = 0x80  # Sound alarm

 # Service Processor Message Intensity
.Lspm_hilit      = 0xE8  # Highlighting
.Lspm_norm       = 0xE4  # Normal

.macro spmto to lt=0x10 over=0x00 alarm=0x00 int=0x00
	    .word  \to-.                   # length   # _SCCB_OBJ_HDR
	    .word  4                       # type
	    .byte  \lt                     # ltflag - byte 0  # _SCCB_MTO_BK
	    .byte  \over                   # ltflag - byte 1
	    .byte  \alarm                  # presattr - byte 0
	    .byte  0                       # presattr - byte 1
	    .byte  0                       # presattr - byte 2
	    .byte  \int                    # presattr - byte 3
	    .endm

.endif # .ifndef .Lservice_S scope
