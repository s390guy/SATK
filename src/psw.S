.ifndef .Lpsw_S
.Lpsw_S = 1
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

 # This module contains macros that generate PSW's in various formats,
 # sets symbols related to interrupt handling and provides interrupt
 # handling assist macros.
 #
 #   Macro       Description
 #  isk          System/370 INSERT STORAGE KEY instruction
 #  psw          Generate a 64-bit PSW based upon psw_amode and psw_arch
 #  pswe         Generate a 128-bit PSW based upon psw_amode
 #  psw_amode    Specify addressing mode for psw(e) macros
 #  psw_arch     Specify the PSW format for psw(e) macros
 #  rrb          System/370 RESET REFERENCE BIT instruction
 #  s370pswbc    Generate a System/370 Basic Control Mode PSW
 #  s370psw      Generate a System/370 Extended Control Mode PSW
 #  s390psw24    Generate a ESA/390 24-bit addressing mode PSW
 #  s390psw      Generate a ESA/390 31-bit addressing mode PSW
 #  s390xpsw24   Generate a z/Architecture 24-bit addressimg mode PSW
 #  s390xpsw31   Generate a z/Architecture 31-bit addressing mode PSW
 #  s390xpsw     Generate a z/Architecture 64-bit addressing mode PSW
 #  ssk          System/370 STORE STORAGE KEY instructin
 #  traps64      Generate a set of 64-bit interrupt trap PSW's
 #  traps128     Generate a set of 128-bit interrupt trap PSW's
 #  zarch        Enter z/Architecture mode from ESA/390 mode

 # Required PSW alignment is assumed

 # System/370 and ESA/390 interrupt handling assigned storage locations
.LPSW_newrst = 0x000
.LPSW_oldrst = 0x008
.LPSW_oldext = 0x018
.LPSW_oldsvc = 0x020
.LPSW_oldpgm = 0x028
.LPSW_oldmck = 0x030
.LPSW_oldio  = 0x038
.LPSW_newext = 0x058
.LPSW_newsvc = 0x060
.LPSW_newpgm = 0x068
.LPSW_newmck = 0x070
.LPSW_newio  = 0x078

 # z/Architecture interrupt handling assigned storage locations
.LPSW_oldrstg= 0x120
.LPSW_oldextg= 0x130
.LPSW_oldsvcg= 0x140
.LPSW_oldpgmg= 0x150
.LPSW_oldmckg= 0x160
.LPSW_oldiog = 0x170
.LPSW_newrstg= 0x1A0
.LPSW_newextg= 0x1B0
.LPSW_newsvcg= 0x1C0
.LPSW_newpgmg= 0x1D0
.LPSW_newmckg= 0x1E0
.LPSW_newiog = 0x1F0

 # Assigned Storage locations associated with Interrupts
.LINT_extparm= 0x080  # .long   External interrupt parameter
.LINT_extproc= 0x084  # .hword  External processor address
.LINT_extcode= 0x086  # .hword  External interrupt code
.LINT_svcilc = 0x088  # .hword  SVC ILC
.LINT_svccode= 0x08A  # .hword  SVC interruption code
.LINT_pgmilc = 0x08C  # .hword  Program ILC
.LINT_pgmcode= 0x08E  # .hword  Program interruption code
.LINT_pgmtran= 0x090  # .long   Program interruption translation / data exception id
.LINT_pgmmcls= 0x094  # .hword  Program monitor class
.LINT_pgmmcod= 0x09C  # .long   Program monitor code (32-bit)
.LINT_pgmai  = 0x0A0  # .byte   Program exception access identification
.LINT_pgmoi  = 0x0A2  # .byte   Program exception operand acces identification
.LINT_pgmtrnx= 0x0A8  # .quad   Program translation exception (64-bit)  
.LINT_pgmmcdx= 0x0B0  # .quad   Program monitor code (64-bit)
.LINT_mckcode= 0x0E8  # .quad   Machine check interruption code
 # S/370 I/O assigned storage locations
.Ls370bcipl  = 0x002  # .hword  Device address of the IPL device for S/370 BC-mode
.Ls370bcext  = .LPSW_oldext+2   # .hword  S/370 BC-mode external interrupt code
.Ls370bcsvc  = .LPSW_oldsvc+2   # .hword  S/370 BC-mode SVC interrupt code
.Ls370bcpgm  = .LPSW_oldpgm+2   # .hword  S/370 BC-mode program interrupt code

 # Machine-Check / Store-Status Save Areas
.LMCKAR = 0x120  # 0x120-0x15F - 32-bit Access Registers 0-15
.LMCKFR = 0x160  # 0x160-0x17F - 64-bit Floating Point Registers 0, 2, 4, 6 
.LMCKGR = 0x180  # 0x180-0x1BF - 32-bit General Registers 0-15
.LMCKCR = 0x1C0  # 0x1C0-0x1FF - 32-bit Control Registers 0-15

.LSSAFR = 0x1200 # 0x1200-0x127F - 64-bit Floating Point Registers 0-15
.LSSAGR = 0x1280 # 0x1280-0x12FF - 64-bit General Registers 0-15
.LSSAAR = 0x1340 # 0x1340-0x137F - 32-bit Access Registers 0-15
.LSSACR = 0x1380 # 0x1380-0x13FF - 64-bit Control Registers 0-15

 # Other Assigned Storage Locations
.Lstfl       = 0xC8   # .long   Store Facility List
.Lstflzins   = 0x40   # Indicates z/Architecture is installed
.Lnotas370   = 0xF0   # This location is not used on System/370

 # Control Registers
.Lcr0_ssm    = 0x80000000   # SSM-suppression control
.Lcr0_tod    = 0x40000000   # TOD-clock sync control
.Lcr0_lowadr = 0x20000000   # Low-address-protection control
.Lcr0_extauth= 0x10000000   # Extraction-authority control
.Lcr0_secspc = 0x08000000   # Secondary-space control
.Lcr0_fpovrd = 0x04000000   # Storage-protection-override control
.Lcr0_tf390  = 0x00B00000   # Translation format (ESA/390 or z/Architecture)
.Lcr0_afpreg = 0x00040000   # AFP-register control
.Lcr0_vectrl = 0x00020000   # Vector control
.Lcr0_aspfunc= 0x00010000   # Address-space function control
.Lcr0_malalrt= 0x00008000   # Malfunction-alert subclass mask
.Lcr0_emrsgnl= 0x00004000   # Emergency-signal subclass mask
.Lcr0_extcall= 0x00002000   # External-call subclass mask
.Lcr0_todsync= 0x00001000   # TOD-clock sync-check subclass mask
.Lcr0_clkcomp= 0x00000800   # Clock-comparator subclass mask
.Lcr0_cputimr= 0x00000400   # CPU-timer subclass mask
.Lcr0_srvsgnl= 0x00000200   # Service-signal subclass mask
 #             0x00000100   # Not defined
 #             0x00000800   # Not used
.Lcr0_intrkey= 0x00000040   # Interrupt-key subclass mask
 #             0x00000020   # Not used
.Lcr0_etrmask= 0x00000010   # ETR subclass mask
.Lcr0_pcfast = 0x00000008   # Program-call-fast control
.Lcr0_crypto = 0x00000004   # Crypto control

 # Specify the addressing mode recognized by the psw and pswe macros.  If the am 
 # parameter is missing the assembler symbol __amode__ is used.  If neither the
 # am argument is specified nor the __amode__ symbol is defined, the default
 # addressing modes for ESA/390 and z/Architecture are set, 31-bit and 64-bit
 # respectively.

       .macro psw_amode am
       .ifb \am                                      # Use __amode__ if parm missing
           .ifdef __amode__
                .ifeq __amode__-24                   # __amode__ is 24
.L__psw_amode  = 0
.L__pswe_amode = 0
                .else  # .ifeq __amode__-24          # __amode__ might be 31 or 64
                    .ifeq __amode__-31               # __amode__ is 31
.L__psw_amode  = 0x80000000
.L__pswe_amode = 0x00008000
                    .else  # .ifeq __amode__-31      # __amode__ might be 64
                         .ifeq __amode__-64          # __amode__ is 64
.L__psw_amode  = 0x80000000
.L__pswe_amode = 0x00018000
                         .else  # .ifeq __amode__-64 # Invalid __amode__ value
                             .warning "psw_amode: __amode__ value invalid, setting defaults"
.L__psw_amode  = 0x80000000 # Set the default ESA/390 addressing mode, 31-bit
.L__pswe_amode = 0x00018000 # Set the default z/Architecture addressing mode, 64-bit
                         .endif # .ifeq __amode__-64
                    .endif # .ifeq __amode__-31
                .endif # .ifeq __amode__-24
           .else  # .ifdef __amode__                 # Use arch symbol for default
              .ifdef __s370__             # If S/370, default amode is 24
.L__psw_amode  = 0
              .else  # .ifdef __s370__    # otherwise ESA/390 default 31
.L__psw_amode  = 0x80000000 # Set the default ESA/390 addressing mode, 31-bit
              .endif # .ifdef __s370__
.L__pswe_amode = 0x00018000 # Set the default z/Architecture addressing mode, 64-bit
           .endif # .ifdef __amode__
       .else  # .ifb \am                  # Use macro parameter for amode
           .ifc \am,24
.L__psw_amode  = 0
.L__pswe_amode = 0
           .else  # .ifc \am,24
               .ifc \am,31
.L__psw_amode  = 0x80000000
.L__pswe_amode = 0x00008000
               .else  # .ifc \am,31
                    .ifc \am,64
.L__psw_amode  = 0x80000000
.L__pswe_amode = 0x00018000
                    .else  # .ifc \am,64
                          .error "psw_amode: argument am invalid"
                    .endif # .ifc \am,64
               .endif # .ifc \am,31
           .endif # .ifc \am,24
       .endif # .ifb \am
       .endm

 # Set the __amode__ specifed addressing mode or defaults if not defined.
       psw_amode

 # Set the architecture mode recognized by the pswx macro.  Assembler symbols
 # recognized: __s390x__, __s390__, __s370__, __bcmode__.  The arch argument
 # recognizes z, 370, 390 and bc.  An arch argument value overrides a specified
 # assembler symbol setting.  The default architecture is 370 (extended mode).
 # The local symbol .L__psw_arch is set to one of the following values:
 # 0 for System/370 Basic-Control mode, 1 for System/370 Extended Control mode,
 # 2 for ESA/390 and 3 for z/Architecture

       .macro psw_arch arch
       .ifnb \arch
            .ifc \arch,z
.L__psw_arch = 3
            .else  # .ifc \arch,z
                 .ifc \arch,390
.L__psw_arch = 2
                 .else  # .ifc \arch,390
                      .ifc \arch,370
.L__psw_arch = 1                      
                      .else  # .ifc \arch,370
                           .ifc \arch,bc
.L__psw_arch = 0
                           .else  # .ifc \arch,bc
                                .error "psw_arch: argument arch invalid, ignored" 
                           .endif # .ifc \arch,bc
                      .endif # .ifc \arch,370
                 .endif # .ifc \arch,390
            .endif # .ifc \arch,z
       .else  # .ifnb \arch
            .ifdef __s390x__
.L__psw_arch = 3
            .else # .ifdef __s390x__
                 .ifdef __s390__
.L__psw_arch = 2
                 .else  # .ifdef __s390__
                      .ifdef __s370__
                           .ifdef __bcmode__           # S/370 BC-mode
.L__psw_arch = 0                           
                           .else   # .ifdef __s370__   # S/370 EC-mode
.L__psw_arch = 1
                           .endif # .ifdef __bcmode__
                      .else  # .ifdef __s370__
.L__psw_arch = 2   # Set the default architecture (ESA/390)
                      .endif # .ifdef __s370__
                 .endif # .ifdef __s390__
            .endif # .ifdef __s390x__
       .endif # .ifnb \arch
       .endm

 # Set the architecture based upon assembly symbols or the default
       psw_arch

 # dwait - Enter a disabled wait state from the current active architecture
 
         .macro dwait code=0 program=1 br=13 b=0b
         lpsw   1f-\b(\br)
         .align 8
         psw    s=0x0002,p=0,a=((\program& 0xFF)<<16)+(\code & 0xFFFF)
         .endm

 # Enter a disabled wait state from any architecture with register
 # supplied program designation and termination code

         .macro dwaitr coder:req programr:req br=13 b=0b
         stc    \programr,1f+5-\b(\br)
         sth    \coder,1f+6-\b(\br)
         lpsw   1f-\b(\br)
         .align 8
1:       .hword 0x000A,0x0000,0x0000,0x0000
         .endm

 # isk - INSERT STORAGE KEY instruction in S/370
 # Macro Parameters:
 #   r1       R1 instruction field (required)
 #   r2       R2 instruction field (required)

         .macro isk r1:req,r2:req
         .insn rr,0x0900,\r1,\r2
	     .endm

 # Generate a 64-bit PSW (ESA/390 or System/370) with format and addressing mode
 # based upon the psw_arch and psw_amode settings respectively.

       .macro psw s=0,p=0,a=0
    .ifeq .L__psw_arch       # If S/370 BC-mode
       .hword (\s)&0xFFF7,0
       .long  (((\p)&0xFF)<<8)+(\a)
    .else                    # If S/370 EC-mode, ESA/390 of z/Architecture
       .hword ((\s)&0x47FF)|8,((\p)&0xFF)<<8
       .long  .L__psw_amode+(\a)
    .endif
       .endm

 # Generate a 128-bit PSW (z/Architecture) with addressing mode based upon the 
 # psw_amode macro.

       .macro pswe s=0,p=0,a=0
       .hword (\s)&0x47F7
       .long  (((\p)&0xFF)<<24)|.L__pswe_amode
       .hword 0
       .quad  \a
       .endm

 # rrb - RESET REFERENCE BIT instruction in S/370 architecture
 # Macro Parameters:
 #   bd2      Base-displacement operand 2, d2(b2) (required)
 
         .macro rrb bd1:req
         .insn s,0xB2130000,\bd2
         .endm

 # Generate a System/370 Basic-control mode PSW

       .macro s370pswbc s=0,p=0,a=0
       .hword (\s)&0xFFF7,0
       .long  (((\p)&0xFF)<<8)+(\a)
       .endm

 # Generate a System/370 Extended-control mode PSW

       .macro s370psw s=0,p=0,a=0
       .hword (\s)&0x47FF|8,((\p)&0xFF)<<8
       .long  \a
       .endm

 # Genreate a ESA/390 mode 24-bit addressing PSW

       .macro s390psw24 s=0,p=0,a=0
       .hword (\s)&0x47FF|8,((\p)&0xFF)<<8
       .long  \a
       .endm

 # Generate a ESA/390 mode 31-bit addressing PSW

       .macro s390psw s=0,p=0,a=0
       .hword (\s)&0x47FF|8,((\p)&0xFF)<<8
       .long  0x80000000+(\a)
       .endm

 # Generate a z/Architecture mode 24-bit addressing PSW

       .macro s390xpsw24 s=0,p=0,a=0
       .hword (\s)&0x47F7,((\p)&0xFF)<<8,0,0
       .quad  \a
       .endm

 # Generate a z/Architecture mode 31-bit addressing PSW

       .macro s390xpsw31 s=0,p=0,a=0
       .hword (\s)&0x47F7,((\p)&0xFF)<<8,0x8000,0
       .quad  \a
       .endm

 # Generate a z/Architecture mode 64-bit addressing PSW

         .macro s390xpsw s=0,p=0,a=0
         .hword (\s)&0x47F7,(((\p)&0xFF)<<8)|1,0x8000,0
         .quad  \a
         .endm

 # ssk - SET STORAGE KEY instruction in S/370
 # Macro Parameters:
 #   r1       R1 instruction field (required)
 #   r2       R2 instruction field (required)

         .macro ssk r1=0,r2=0
         .insn rr,0x0800,\r1,\r2
         .endm
       
 # Intercept a Program Interrupt
 #
 # These macros are intended to be used where an instruction is executed
 # to detect available functionality and a program operation exception will
 # indicate absence of the functionality.  They are used like this:
 #
 #          insttrap wrkr:req br=15 b=0b
 #          [instruction being tested]
 #          insttest fail=.Lfail,succeed=.Lsucceed

       .macro insttrap wrkr:req br=13 b=0b
       .ifdef __zarch__
          la   \wrkr,1f-\b(\br)     # Locate the interrupt intercept
          stg  \wrkr,2f+24-\b(\br)  # Set it in the new PSW
          mvc  2f-\b(16,\br),.LPSW_newpgmg(0) # Save the current new PSW
          mvc  .LPSW_newpgmg(16,0),2f+16-\b(\br) # Set new one
       .endif
       .ifdef __s390__
          la   \wrkr,1f-\b(\br)     # Locate the interrupt intercept
          o    \wrkr,2f+16-\b(\br)  # Make it 31-bit addressing
          st   \wrkr,2f+12-\b(\br)  # Set it in the new PSW
          mvc  2f-\b(8,\br),.LPSW_newpgm(0) # Save the current new PSW
          mvc  .LPSW_newpgm(8,0),2f+8-\b(\br) # Set new one
       .else
          la   \wrkr,1f-\b(\br)     # Locate the interrupt intercept
          stcm \wrkr,0x7,2f+13-\b(\br)  # Set it in the new PSW
          mvc  2f-\b(8,\br),.LPSW_newpgm(0) # Save the current new PSW
          mvc  .LPSW_newpgm(8,0),2f+8-\b(\br) # Set new one
       .endif
       .endm

       .macro insttest wrkr:req fail:req succeed:req br=15 b=0b
       .ifdef __zarch__
          mvc   .LPSW_newpgmg(16,0),1f-\b(\br) # Restore PGM new PSW
          j     \succeed                  # Go to success
1:        la    \wrkr,\fail-\b(\br)       # Locate failed location
          mvc   .LPSW_newpgmg(16,0),2f-\b(\br) # Restore PGM new PSW
          stg   \wrkr,.LPSW_oldpgmg+8(0)  # Set the fail address
          lpswe .LPSW_oldpgmg+8(0)        # Go there
          .align 8
2:        .octa  0  # Current PGM new PSW
          s390xpsw  # Intercept new PGM new PSW
          .endif
       .ifdef __s390__
          mvc   .LPSW_newpgm(8,0),1f-\b(\br) # Restore PGM new PSW
          b     \succeed-\b(\br)
1:        la    \wrkr,\fail-\b(\br)     # Locate failed location
          mvc   .LPSW_newpgm(8,0),2f-\b(\br) # Restore PGM new PSW
          tm    .LPSW_oldpgm+4,0x80     # 31-bit addressing?
          bno   .+8-\b(\br)             # ..No, leave bit off
          o     \wrkr,2f+16-\b(\br)     # Make it 31-bit addressing
          st    \wrkr,.LPSW_oldpgm+4(0) # Set the fail address
          lpsw  .LPSW_oldpgmg+8(0)      # Go there
          .align 8
2:        .quad  0   # Current PGM new PSW
          s390psw    # Intercept new PGM new PSW
          .long  0x80000000
       .else
          mvc   .LPSW_newpgm(8,0),1f-\b(\br) # Restore PGM new PSW
          b     \succeed-\b(\br)
1:        la    \wrkr,\fail-\b(\br)          # Locate failed location
          mvc   .LPSW_newpgm(8,0),2f-\b(\br) # Restore PGM new PSW
          stcm  \wrkr,0x7,.LPSW_oldpgm+5(0)  # Set the fail address
          lpsw  .LPSW_oldpgmg+8(0)           # Go there
          .align 8
2:        .quad  0   # Current PGM new PSW
          s370psw    # Intercept new PGM new PSW
       .endif
       .endm

 # trap64 - Enable a set of 64-bit interrupt PSW's (see traps64)
 #
 # Macro Parameters:
 #   psws     Symbol associated with the 6 interrupt PSW's to be enabled (required)
 #   br       base register (defaults to 13)
 #   b        able of the current base (defaults to 0b)

           .macro trap64 psws:req br=13 b=0b
           mvc    0x00(8,0),\psws-\b(\br)     # Enable Restart New PSW
           mvc    0x58(56,0),\psws+8-\b(\br)  # Enable all of the other PSW's
           .endm

 # trap128 - Enable a set of 128-bit interrupt PSW's (see traps128)
 #
 # Macro Parameters:
 #   psws     Symbol associated with the 6 interrupt PSW's to be enabled (required)
 #   br       base register (defaults to 13)
 #   b        able of the current base (defaults to 0b)

           .macro trap128 psws:req br=13 b=0b
           mvc    0x1A0(96,0),\psws-\b(\br)  # Enable all of the PSW's
           .endm

 # traps64 - Create a set of 64-bit interrupt trap PSW's
 #
 # Macro Parameters: none

           .macro traps64
           psw    s=0x0002,a=0x008        # Restart Trap PSW
           psw    s=0x0002,a=0x018        # External Trap PSW
           psw    s=0x0002,a=0x020        # Supervisor Call Trap PSW
           psw    s=0x0002,a=0x028        # Program Trap PSW
           psw    s=0x0002,a=0x030        # Machine-Check Trap PSW
           psw    s=0x0002,a=0x038        # Input-Output Trap PSW
           .endm

 # traps128 - Create a set of 128-bit interrupt trap PSW's
 #
 # Macro Parameters: none

           .macro traps128
           pswe   s=0x0002,a=0x120        # Restart Trap PSW
           pswe   s=0x0002,a=0x130        # External Trap PSW
           pswe   s=0x0002,a=0x140        # Supervisor Call Trap PSW
           pswe   s=0x0002,a=0x150        # Program Trap PSW
           pswe   s=0x0002,a=0x160        # Machine-Check Trap PSW
           pswe   s=0x0002,a=0x170        # Input-Output Trap PSW
           .endm
           
 # zarch - Enters z/Architecture mode from ESA/390 mode
 #
 # Macro Parameters:
 #   statr    an even/odd register pair used by SIGP (required)
 #   cpur     register to be used for the CPU address (required)
 #   error    lable to which control is passed on a error (required)
 #   er       register to contain the point at which error occurred (defaults to 15)
 #   br       base register (defaults to 13)
 #   b        able of the current base (defaults to 0b)

           .macro   zarch statr:req cpur:req error:req er=15 br=13 b=0b
           stap     2f-\b(\br)               # Save my CPU address
           sr       \statr,\statr            # Clear status register
           la       \statr+1,1               # All CPU's set to z/Architecture
           lh       \cpur,2f-\b(\br)         # Specify myself as being signaled
           sigp     \statr,\cpur,0x12        # Set architecture order
           bc       8,.+10-\b(\br)           # ..If successful, continue
           bas      \er,\error-\b(\br)       # ..DIE, architecture change failed
2:         .hword   0                        # CPU address
           .endm

.endif # .ifndef .Lpsw_S
