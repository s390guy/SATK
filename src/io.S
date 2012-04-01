.ifndef .Lio_S
.Lio_S = 1
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

 # This module contains macros that generate Input/Output structures, S/370 I/O
 # instructions, structure displacements and assigned storage locations
 # associated with input/output operations.

 #   Macro       Description
 #  bchanio      Branch on channel-based I/O
 #  ccw0         Format 0 Channel Command Word
 #  ccw1         Format 1 Channel Command Word
 #  clrio        System/370 CLEAR IO instruction
 #  hdv          System/370 HALT DEVICE instruction
 #  hio          System/370 HALT IO instruction
 #  irb          Interrupt Response Block (IRB)
 #  orb          Operation Request Block (ORB)
 #  orbf1        Define a symbol whose value sets the ORB flag 1 field content
 #  orbf2        Define a symbol whose value sets the ORB flag 2 field content
 #  orbf3        Define a symbol whose value sets the ORB flag 2 field content
 #  rdd          System/370 READ DIRECT instruction
 #  scsw         Subchannel Status Word (SCSW)
 #  schib        Subchannel Information Block (SCHIB)
 #  sio          System/370 START IO instruction
 #  siof         System/370 START IO FAST RELEASE instruction
 #  stidc        System/370 STORE CHANNEL ID instruction
 #  tch          System/370 TEST CHANNEL instruction
 #  tio          System/370 TEST IO instruction
 #  vrdcblok     Virtual/Real Device Block
 #  wrd          System/370 WRITE DIRECT instruction


 # bchanio - Branch on detection of channel-based I/O interrupt
 # Macro Parameters:
 #   hwar     Register containing the I/O interrupt ID (required)
 #   lable    Symbol associated with the location to pass control
 #   br       Base register (defaults to 13)
 #   b        Current base (defaults to 0b)

         .macro bchanio hwar:req lable:req br=13 b=0b
         clm    \hwar,0b1100,1f-\b(\br)
         be     \lable-\b(\br)
         b      1f+2-\b(\br)
1:       .hword 0
         .endm

 # clrio - CLEAR IO instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro clrio bd2:req
         .insn s,0x9D010000,\bd
         .endm

 # hdv - HALT DEVICE instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro hdv bd2:req
         .insn s,0x9E010000,\bd2
         .endm

 # hio - HALT IO instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro hio d=0,b=0
         .insn s,0x9E000000,\bd2
         .endm

 # rdd - READ DIRECT instruction in S/370 architecture
 # Macro Parameters:
 #   bd1      Base-displacement operand 1, d1(b1) (required)
 #   i2       Immediate operand 2, i2 (required)

         .macro rdd bd1:req i:req
         .insn si,0x85000000,\db1,\i2
	     .endm

 # sio - START IO instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro sio bd2:req
         .insn s,0x9C000000,\bd2
         .endm

 # siof - START IO FAST RELEASE instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro siof bd2:req
         .insn s,0x9C010000,\bd2
         .endm

 # stidc - STORE CHANNEL ID instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro stidc bd2:req
         .insn s,0xB2030000,\bd2
         .endm

 # TCH - TEST CHANNEL instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro tch bd2:req
         .insn s,0x9F000000,\bd2
         .endm

 # TIO - TEST IO instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)

         .macro tio bd2:req
         .insn s,0x9D000000,\bd2
         .endm

 # wrd - WRITE DIRECT instruction in S/370 architecture
 # Macro Parameters:
 #   bd1      Base-displacement operand 1, d1(b1) (required)
 #   i2       Immediate operand 2, i2 (required)

         .macro wrd bd1:req i2:req
         .insn si,0x94000000,\bd1,\i2
	     .endm

 # Required alignments are assumed

 # Assigned Storage Locations Related to Channel Subsystem I/O
.LIO_ssid    = 0xB8  # .long   Interrupting subchannel
.LIO_intprm  = 0xBC  # .long   Interruption parameter
.LIO_intid   = 0xC0  # .long   Interruption identification

 # Assigned Storage Locations Related to Channel I/O
.Lio_devbc   = 0x02  # .hword  IPL device in S/370 BC-mode
.LIO_csw     = 0x40  # .quad   Channel I/O Channel Status Word (CSW)
.LIO_csw_key = 0x40  # .byte   Storage key
.LIO_csw_ccw = 0x41  # 3-bytes CSW Channel Command Word address
.LIO_csw_ds  = 0x44  # .byte   CSW Device status
.LIO_csw_cs  = 0x45  # .byte   CSW Channel status
.LIO_csw_cnt = 0x46  # .hword  CSW byte count
.LIO_caw     = 0x48  # .long   Channel I/O - Channel Address Word
.LIO_chanid  = 0xA8  # .long   Channel I/O - Channel identification
.LIO_chantyp = 0xA8  # .byte   Channel I/O - Channel type
.LIO_chanmodl= 0xA8  # .hword  Channel I/O - Channel model number
.LIO_chanioel= 0xAA  # .hword  Channel I/O - Channel I/O Extended Logout length
.LIO_ioeladdr= 0xAC  # .long   Channel I/O - I/O Extended logout address
.LIO_ltdchlg = 0xB0  # .long   Limited Channel Logout
.LIO_chanio  = 0xB8  # .hword  Zeros stored for channel I/O interrupting device
.LIO_dev     = 0xBA  # .hword  Channel I/O Interrupting device

 # Channel ID
.LIO_chnmsk  = 0xF0  # Mask to isolate channel type mask
.LIO_selector= 0x00  # Selector channel
.LIO_bytemux = 0x10  # Byte multiplexor channel
.LIO_blockmux= 0x20  # Block Multiplexor channel

 # Common Channel Command Word Flags
.LCCW_CD    = 0x80   # Chain Data
.LCCW_CC    = 0x40   # Command Chain
.LCCW_SLI   = 0x20   # Suppress Length Indication
.LCCW_skip  = 0x10   # Skip transfering data to main storage
.LCCW_PCI   = 0x08   # Cause an intermediate interruption to occur
.LCCW_IDA   = 0x04   # Causes address to specify first IDAW
.LCCW_susp  = 0x02   # Channel program suspended before command execution
.LCCW_MIDA  = 0x01   # Causes address to specify first MIDAW

 # Common Channel Command Word Commands
.LCCW_WRITE = 0x01   # Write data
.LCCW_READ  = 0x02   # Read data
.LCCW_CONTROL=0x03   # Control
.LCCW_SENSE = 0x04   # Basic Sense
.LCCW_SENSEID=0xE4   # Sense ID
.LCCW_TIC   = 0x08   # Transfer in channel

 # Common Channel Status Flags
.LCS_pci    = 0x80   # Program-controlled interrupt
.LCS_ic     = 0x40   # Incorrect length
.LCS_pck    = 0x20   # Program check
.LCS_protck = 0x10   # Protection check
.LCS_datack = 0x08   # Channel-data check
.LCS_ccck   = 0x04   # Channel-control check
.LCS_ifck   = 0x02   # Interface-control check
.LCS_chainck= 0x01   # Chaining check

 # Common Device Status Flags
.LDS_attn   = 0x80   # Device attention
.LDS_sm     = 0x40   # Status modifier
.LDS_cue    = 0x20   # Control unit end
.LDS_busy   = 0x10   # Device busy
.LDS_ce     = 0x08   # Channel end
.LDS_de     = 0x04   # Device end
.LDS_uc     = 0x02   # Unit check
.LDS_ux     = 0x01   # Unit exception

 # Format 0 Channel Command Word (CCW)
 # Alignment: .align 8

.LCCW0_cmd  =  0
.LCCW0_addr =  1
.LCCW0_flags=  4
.LCCW0_resv =  5
.LCCW0_cnt  =  6
.LCCW0_len  =  8

           .macro ccw0 cmd:req,addr=0,flags=0,cnt=0
           .long  (((\cmd)&0xFF)<<24)+(\addr)
           .byte  (\flags)&0xFE,0
           .hword \cnt
           .endm

 # Format 1 Channel Command Word (CCW)
 # Alignment: .align 8

.LCCW1_cmd  =   0
.LCCW1_flags=   1
.LCCW1_cnt  =   2
.LCCW1_addr =   4
.LCCW1_len  =   8

           .macro ccw1 cmd:req,addr=0,flags=0,cnt=0
           .byte  \cmd,(\flags)&0xFE
	   .hword \cnt
           .long  \addr
	   .endm

 # Interruption Response Block (IRB)
 # Alignment: .align 4

.LIRB_SCSW    = 0    # Subchannel-Status Word
.LIRB_ESW     = 12   # Extended-Status Word
.LIRB_ESW_scl = 12   # ESW-Subchannel Logout
.LIRB_ESW_erw = 16   # ESW-Extended-Report Word
.LIRB_ESW_csense = 0x01  # Flag in ERW byte 0 that concurrent sense is present
.LIRB_ESW_fsa = 20   # ESW-Failing-Storage Address
.LIRB_ESW_csa = 28   # ESW-Secondary-CCW Address
.LIRB_ECW     = 32   # Extended-Control Word
.LIRB_EMW     = 64   # Extended-Measurement Word
.LIRB_EMW_dct = 64   # EMW-Device-Connect Time
.LIRB_EMW_fpt = 68   # EMW-Function-Pending Time
.LIRB_EMW_ddt = 72   # EMW-Device Disconnect Time
.LIRB_EMW_cuqt= 76   # EMW-Control-Unit-Queueing Time
.LIRB_EMW_daot= 80   # EMW-Device-Active-Only Time
.LIRB_EMW_dbt = 84   # EMW-Device-Busy Time
.LIRB_EMW_icrt= 88   # EMW-Initial-Command Response Time
.LIRB_len     = 96   

           .macro irb
           scsw                   # Subchannel-Status Word
           .long  0,0,0,0,0       # Extended-Status Word
           .long  0,0,0,0,0,0,0,0 # Extended-Control Word
           .long  0,0,0,0,0,0,0,0 # Extended-Measurement Word
           .endm

 # Operation-Request Block (ORB)
 # Alignment: .align 4

.LORB_intp = 0      # .long  Interruption parameter
.LORB_key  = 4      # .byte  Bits 0-3, Subchannel key
.LORB_f1   = 4      #        Bits 3-7, Flag 1 bits (f1)
.LORB_f2   = 5      # .byte  Bits 0-7, Flag 2 bits (f2)
.LORB_LPM  = 6      # .byte  Logical path mask
.LORB_f3   = 7      # .byte  Bits 0-7, Flag 3 bits (f3)
.LORB_pgm  = 8      # .long  Channel program address
.LORB_css  = 12     # .byte  Channel subsystem priority
 #         = 13     # .byte  reserved
.LORB_cu   = 14     # .byte  Control-unit priority
 #           15     # .byte  reserved
 #           16     # .octa  reserved
.LORB_keymk= 0xF0
.LORB_len  = 32

 # Operation-Request-Block Flags
.LORB_f1_S = 0x08   # Suspend control
.LORB_f1_C = 0x04   # Streaming-mode control
.LORB_f1_M = 0x02   # Modification control
.LORB_f1_Y = 0x01   # Synchronization control
.LORB_f2_F = 0x80   # CCW-format control (0==CCW0, 1==CCW1)
.LORB_f2_P = 0x40   # Prefetch control
.LORB_f2_I = 0x20   # Initial-status-interruption control
.LORB_f2_A = 0x10   # Address-limit-checking control
.LORB_f2_U = 0x08   # Supress-suspended-interruption control
.LORB_f2_0 = 0x04   # Reserved
.LORB_f2_H = 0x02   # Format-2-IDAW control
.LORB_f2_T = 0x01   # 2K-IDAW control
.LORB_f3_L = 0x80   # Incorrect-length-suppression mode
.LORB_f3_X = 0x01   # ORB-extension control

           .macro orb pgm=0,intp=0,key=0,lpm=0xFF,css=0,cu=0,f1=0,f2=0,f3=0
           .long  \intp
           .byte  (((\key)&0xF)<<4)|((\f1)&0xF)
           .byte  (\f2)&0xFB
           .byte  \lpm
           .byte  ((\f3)&0x81)
           .long  (\pgm)&0x7FFFFFFF
           .byte  \css,0,\cu,0
           .long  0,0,0,0
           .endm

           .macro orbf1 name:req,s=0,c=0,m=0,y=0
\name      .set   ((\s)&1)*0x8
\name      .set   \name|(((\c)&1)*0x4)
\name      .set   \name|(((\m)&1)*0x2)
\name      .set   \name|((\y)&1)
           .endm

           .macro orbf2 name:req,f=0,p=0,i=0,a=0,u=0,h=0,t=0
\name      .set   ((\f)&1)*0x80
\name      .set   \name|(((\p)&1)*0x40)
\name      .set   \name|(((\i)&1)*0x20)
\name      .set   \name|(((\a)&1)*0x10)
\name      .set   \name|(((\u)&1)*0x08)
\name      .set   \name|(((\h)&1)*0x02)
\name      .set   \name|((\t)&1)
           .endm

           .macro orbf3 name:req,l=0,x=0
\name      .set   (((\f)&1)*0x80)|((\x)&1)
           .endm

 # Subchannel-Status Word (SCSW)
.LSCSW_status=  0     # .long  Bits 0-31 status bits
.LSCSW_f0    =  0

.LSCSW_f1    =  1
.LSCSW_f1_nop=  0x01  # Path not operational

.LSCSW_ctl   =  2     # Subchannel control
.LSCSW_docs  =  0x80  # Doing concurrent sense
.LSCSW_start =  0x40  # Start in progress
.LSCSW_busy  =  0xF0  # Busy mask

.LSCSW_sc    =  3     # Status control bits 27-31 of status
.LSCSW_alert    = 0x10  # Alert (bit 27)
.LSCSW_primary  = 0x04  # Primary status (bit 29) - I/O is done
.LSCSW_statpend = 0x01  # Status pending (bit 31)

.LSCSW_ccw   =  4     # .long  CCW address

.LSCSW_ds    =  8     # .byte  Device status
.LSCSW_attn  =  0x80  # Attention
.LSCSW_sm    =  0x40  # Status Modifier
.LSCSW_cue   =  0x20  # Control-unit end
.LSCSW_busy  =  0x10  # Busy
.LSCSW_ce    =  0x08  # Channel end
.LSCSW_de    =  0x04  # Device end
.LSCSW_cede  =  .LSCSW_ce+.LSCSW_de
.LSCSW_uc    =  0x02  # Unit Check (sense required)
.LSCSW_uex   =  0x01  # Unit Exception

.LSCSW_cs    =  9     # .byte Channel status
.LSCSW_pci   =  0x80  # Program-controlled interruption
.LSCSW_il    =  0x40  # Incorrect length
.LSCSW_pgmck =  0x20  # Program check
.LSCSW_prot  =  0x10  # Protection check
.LSCSW_dck   =  0x08  # Channel-data check
.LSCSW_ccck  =  0x04  # Channel-control check
.LSCSW_icck  =  0x02  # Interface-control check
.LSCWS_chnck =  0x01  # Chaining check

.LSCSW_cnt   =  10    # .byte CCW residusal count
.LSCSW_len   =  12    # Length of the SCSW structure

           .macro scsw
           .long  0,0,0
           .endm

 # Subchannel-Information Block (SCHIB)
 # Alignment: .align 4

.LSCHIB_PMCW =  0
.LPMCW_intp  =  0
.LPMCW_isc   =  4

.LPMCW_f1    =  5
.LPMCW_devval=  0x01
.LPMCW_enable=  0x80

.LPMCW_f2    =  6

.LPMCW_dev   =  6
.LPMCW_lpm   =  8
.LPMCW_pnom  =  9
.LPMCW_lpum  =  10
.LPMCW_pim   =  11
.LPMCW_mbi   =  12
.LPMCW_pom   =  14
.LPMCW_pam   =  15
.LPMCW_chpid0=  16
.LPMCW_chpid1=  17
.LPMCW_chpid2=  18
.LPMCW_chpid3=  19
.LPMCW_chpid4=  20
.LPMCW_chpid5=  21
.LPMCW_chpid6=  22
.LPMCW_chpid7=  23
.LPMCW_zeros =  24

.LPMCW_f2    =  27
.LPMCW_f2_cs =  0x01   # Concurrent Sense

.LPMCW_len   =  28

.LSCHIB_SCSW =  28
.LMDA1       =  40
.LMBA        =  40
.LMDA2       =  44
.LSCHIB_len  =  52

           .macro schib
           .long  0,0,0,0,0,0,0  # Path Management Control Word (PMCW)
           scsw                  # Subchannel Status Word
           .long  0,0            # Model-dependent area or measurement block
           .long  0              # Model-dependent area
           .endm

           .macro iodev devr:req
           lh     \devr,.Liodev(0)
           .endm

           .macro scdev devr:req schibr:req
           lh     \devr,6(\schibr) # Fetch the device number
           .endm

           .macro testsccs schibr:req status:req
           tm     37(\schibr),\status
           .endm

           .macro testscds schibr:req status:req
           tm     36(\schibr),\status
           .endm

 # Virtual/Real Device Block (VRDCBLOK)
 # Alignment: .align 4

.Lvrdcdvno =  0x0   # .hword Device Number
.Lvrdclen  =  0x2   # .hword Buffer length
.Lvrdvcla  =  0x4   # .byte
.Lvrdcvtyp =  0x5   # .byte
.Lvrdcvsta =  0x6   # .byte
.Lvrdcvfla =  0x7   # .byte
.Lvrdcrccl =  0x8   # .byte
.Lvrdccrty =  0x9   # .byte
.Lvrdccrmd =  0xA   # .byte
.Lvrdccrft =  0xB   # .byte
.Lvrdcundv =  0xC   # .byte
.Lvrdcrdaf =  0xD   # .byte
.Lvrdcres1 =  0xE   # .hword reserved (must be zeros)
.Lvrdcddi  =  0x10  # Device Dependent Information (64-bytes)
.Lvrdcpgid =  0x50  # 11-bytes
.Lvrdcres2 =  0x5B
.Lvrdcvers =  0x60
.Lvrdcrdev =  0x80  # .hword

            .macro vrdcblok len:req
            .hword 0
            .hword \len
            .space \len-4,0x00
            .endm

.endif # .ifndef .Lio_S scope
