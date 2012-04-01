.ifndef .Linterrupt_S
.Linterrupt_S = 1
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

 # This module contains interrupt handling support macros that establish
 # First-Level interrupt handlers, and perform in-line wait operations with
 # and without First-Level interrupt handlers.  Unless otherwise indicated, the 
 # assumption is that a System/370 CPU is running in 24-bit addressing mode, a 
 # ESA/390 CPU is running in 31-bit addressing mode and a z/Architecture CPU is 
 # running in 64-bit addressing mode.
 #
 #  Provided macros:
 #      Macro          Description
 #   flih            Install a ESA/390 First-Level Interrupt Handler
 #   flihg           Install a z/Architecture First-Level Interrupt Handler
 #   flih_entry      Enter a ESA/390 First-Level Interrupt Handler
 #   flih_return     Return to the interrupted program from a ESA/390 First-Level
 #                   Interrupt Handler
 #   flihg_entry     Enter a z/Architecture First-Level Interrupt Handler
 #   flihg_return    Return to the interrupted program from a z/Architecture First-
 #                   Level Interrupt Handler
 #   flihx           Install a First-Level Interrupt Handler based upon the assembly
 #                   architecture symbols: __zarch__, __s390__ (default System/370)
 #   flihx_cc        Set the condition code for the interrupted program independent
 #                   of architecture
 #   flihx_entry     Enter a First-Level Interrupt Handler based upon the assembly
 #                   architecture sybol: __zarch__ (default 32-bit architecture)
 #   flihx_reset     Reset the system mask of the interrupted program independent
 #                   of architecture
 #   flihx_return    Return to the interrupted program from an interrupt handler
 #                   based upon the assembly architecure symbol: __zarch__
 #                   (default 32-bit architecture)
 #   flihx_run       Independent of the architecture, make sure the interrupted
 #                   program runs.
 #   flih370         Install a System/370 First-Level Interrupt Handler
 #   flih370_entry   Enter a System/370 First-Level Interrupt Handler
 #   flih370_return  Return to the interrupt program from a System/370 First-Level
 #                   Interrupt Handler
 #   flihx_opsw      Locate the old PSW based upon assembly architecture symbol:
 #                   __zarch__ (default a 32-bit architecture)
 #
 # The following macros cause the CPU to enter a wait state.  A First-Level
 # Interrupt Handler is required to return control to the point at which the
 # wait macro occurs by setting the old PSW to the run state before loading the 
 # old PSW, returning control to the waiting program.
 #
 #   wait            Cause the ESA/390 CPU to enter a wait state
 #   waitg           Cause the z/Architecture CPU to enter a wait state
 #   waitx           Cause the CPU to enter a wait state based upon assembly 
 #                   architecture symbols: __zarch__, __s390__ (default System/370) 
 #   wait370         Cause the System/370 CPU to enter a wait state
 #   wait_ext        Cause the CPU to wait for an external interruption based upon
 #                   assembly architecture symbols:  __zarch__, __s390__ (default
 #                   System/370)
 #   wait_ext_io     Cause the CPU to wait for either an external or input/output 
 #                   interruption based upon assembly architecture symbols:  
 #                   __zarch__, __s390__ (default System/370) 
 #   wait_io         Cause the CPU to wait for an input/output interruption based 
 #                   upon assembly architecture symbols:  __zarch__, __s390__ 
 #                   (default System/370)
 #
 # The following macros provide for in-line waiting by a program without the need
 # of an established First-Level Interrupt Handler.  The macro effectively provides
 # its own First-Level Interrupt Handler releaving the programmer from establishing
 # one.  These macros only effect the PSW state.  Control register settings may be 
 # required for proper interrupt recognition.
 #
 # These macros depend upon the psw_arch and psw_amode macros for proper
 # settings.  The default is 24-bit addressing in the System/370 Extended Control
 # mode architecture.  These defaults are established when psw.S is included in
 # the assembly.
 #
 #   extwait        Wait for an external interrupt. Processing continues with 
 #                  external interrupts disabled following the interrupt.
 #   iowait         Wait for an input/output interrupt.  Processing continues with 
 #                  input/output interrupts disabled following the interrupt.
 #   iowait_ext     Wait for either an I/O or external interrupt.  Processing
 #                  continues following the I/O interrupt or control is passed to
 #                  identified symbol if the external interrupt occurs first.  In
 #                  both cases input/output and external interrupts are disabled
 #                  following the recognition of either interrupt.

            .include "psw.S"       # Depends upon psw module

 # Install a First Level Interrupt Handler

            .macro flih handler:req npsw:req s=0 br=13 b=0b
            mvc   \npsw(8),1f-\b(\br)       # Move the New PSW
            b     1f+8-\b(\br)              # Branch around New PSW
1:          s390psw s=\s,a=\handler         # New PSW to be installed
            .endm

            .macro flihg handler:req npswg:req s=0 br=13 b=0b
            mvc   \npswg(16),1f-\b(\br)     # Move the New PSW
            j     1f+16                     # Branch around New PSW
1:          s390xpsw s=\s,a=\handler        # New PSW to be installed
            .endm

            .macro flih370  handler:req npsw:req s=0 br=13 b=0b
            mvc   \npsw(8),1f-\b(\br)       # Move the New PSW
            b     1f+8-\b(\br)              # Branch around New PSW
1:          s370psw s=\s,a=\handler         # New PSW to be installed
            .endm

            .macro flihx handler:req npsw:req npswg:req s=0 br=13 b=0b
            .ifdef __zarch__
               flihg handler=\handler,npswg=\npswg,s=\s,br=\br,b=\b
            .else
               .ifdef __s390__
                  flih handler=\handler,npsw=\npsw,s=\s,br=\br,b=\b
               .else
                  flih370 handler=\handler,npsw=\npsw,s=\s,br=\br,b=\b
               .endif
            .endif
            .endm

  # Enter a First Level Interrupt Handler (flih)
  # WARNING: The entry macros need to be modified to support use of ABI conventions

            .macro flih_entry handler:req sa:req call base=0 sar=13 br=15 b=0b
            .align 2
\handler:   stg  0,15,\sa
            basr \br,0
\base:
            .ifc \call,yes
               initsar sar=\sar,br=\br,b=\b
            .endif
            .endm

            .macro flihg_entry handler:req sa:req call base=0 sar=13 br=15 b=0b
            .align 2
\handler:   stmg  0,15,\sa
            basr  \br,0
\base:
            .ifc \call,yes
               initsarg sar=\sar,br=\br,b=\b
            .endif
            .endm

            .macro flih370_entry handler:req sa:req call base=0 sar=13 br=15 b=0b
            flih_enter handler=\hander,sa=\sa,call=\call,base=\base,sar=\sar,br=\br,b=\b
            .endm

            .macro flihx_entry handler:req sa:req call base=0 sar=13 br=15 b=0b
            .ifdef __zarch__
               flihg_entry handler=\handler,sa=\sa,call=\call,base=\base,sar=\sar,br=\br,b=\b
            .else
               flih_entry handler=\handler,sa=\sa,call=\call,base=\base,sar=\sar,br=\br,b=\b
            .endif
            .endm

 # Locate the old PSW depending upon the architecture

            .macro flihx_opswr reg:req opsw:req opswg:req
            .ifdef __zarch__
               la    \reg,\opswg
            .else
               la    \reg,\opsw
            .endif
            .endm

 # In-line wait for an interrupt

            .macro wait s:req wrkr:req br=13 b=0b
            la    \wrkr,1f+8-\b(\br)    # Locate where we continue
            st    \wrkr,1f+4-\b(\br)    # Place it in the wait PSW
            oi    1f+4-0b(\br),0x80     # Set 31-bit addressing in the PSW
            lpsw  1f-\b(\br)            # And wait
            .align 8
1:          s390psw s=\s,a=0
            .endm

            .macro waitg s:req wrkr:req br=13 b=0b
            la    \wrkr,1f+16-\b(\br)   # Locate where we continue
            stg   \wrkr,1f+8-\b(\br)    # Place it in the wait PSW
            lpswe 1f-\b(\br)            # And wait
            .align 8
1:          s390xpsw s=\s,a=0           # Wait PSW
            .endm

            .macro wait370 s:req wrkr:req br=13 b=0b
            la    \wrkr,1f+8-\b(\br)    # Locate where we continue
            st    \wrkr,1f+4-\b(\br)    # Place it in the wait PSW
            lpsw  1f-\b(\br)            # And wait
            .align 8
1:          s370psw s=\s,a=0
            .endm

            .macro waitx s:req wrkr:req br=13 b=0b
            .ifdef __zarch__
            waitg s=\s,wrkr=\wrkr,br=\br,b=\b
            .else
            .ifdef __s390__
            wait s=\s,wrkr=\wrkr,br=\br,b=\b
            .else
            wait370 s=\s,wrkr=\wrkr,br=\br,b=\b
            .endif
            .endif
            .endm

            .macro wait_ext wrkr:req br=13 b=0b
            waitx s=0x0100,wrkr=\wrkr,br=\br,b=\b
            .endm

            .macro wait_ext_io wrkr:req br=13 b=0b
            waitx s=0x0300,wrkr=\wrkr,br=\br,b=\b
            .endm

            .macro wait_io wrkr:req br=13 b=0b
            waitx s=0x0200,wrkr=\wrkr,br=\br,b=\b
            .endm

 # Return from a First Level Interrupt Handler

            .macro flih_return sa:req opsw:req br=13 b=0b
            lm    0,15,\sa         # Restore the interrupt registers
            lpsw  \opsw            # Return to point of interruption
            .endm

            .macro flihg_return sa:req opswg:req br=13 b=0b
            lmg   0,15,\sa         # Restore the interrupt registers
            lpswe \opswg           # Return to point of interruption
            .endm

            .macro flih370_return sa:req opsw:req br=13 b=0b
            flih_return sa=\sa,opsw=\opsw,br=\br,b=\b
            .endm

            .macro flihx_return sa:req opsw:req opswg:req br=13 b=0b
            .ifdef __zarch__
            flihg_return sa=\sa,opswg=\opswg,br=\br,b=\b
            .else
            flih_return sa=\sa,opsw=\opsw,br=\br,b=\b
            .endif
            .endm

 # Set the condition code before returning

            .macro flihx_cc opswr:req cc:req br=13 b=0b
            ni   2(\opswr),0xCF          # Clear the condition code in old PSW
            oi   2(\opswr),(0x3&\cc)<<4  # Set the condition code
            .endm

 # Reset the system mask, PSW bits 0-7 before returning

            .macro flihx_reset opswr:req s:req
            ni   0(\opswr),0xFF-\s
            .endm

 # Ensure the program to which control is returning is in the running state.

            .macro flihx_run opswr:req
            ni   1(\opswr),0xFF-0x02
            .endm

 # The following macros perform an in-line wait for an interrupt that do no
 # require a First-Level Interrupt Handler.  Or more accurately, the First-Level
 # Interrupt Handler is provided in-line by the macro.  The current First-Level 
 # Interrupt Handler is preserved by the macro.  These macros rely upon psw_arch 
 # and psw_amode settings.

     # This macro performs an in-line wait for an external interrupt

            .macro extwait s=0,br=13 b=0b
       .ifeq .L__psw_arch-3  # 64-bit architecture
            mvc    1f-\b(16,\br),.LPSW_newextg(0)     # Save current new PSW
            mvc    .LPSW_newextg(16,0),1f+16-\b(\br)  # Set the return PSW
            nc     .LPSW_newextg(2,0),1f+18-\b(\br)   # New PSW must run
            lpswe  1f+16-\b(\br)                      # Wait for interrupt
            .align 8                                  # Doubleword align PSW's
1:          .octa  0                                  # 1f    new PSW save area
            pswe   s=(\s)&0x45F7|0x0102,a=1b+34       # 1f+16 Wait PSW
            .hword 0xFEFD                             # 1f+32 New PSW run mask
            mvc    .LPSW_newextg(16,0),1b-\b(\br)     # 1f+34 Restore new PSW
       .else                 # 32-bit architecture
            mvc    1b-\b(8,\br),.LPSW_newext(0)       # Save current new PSW
            mvc    .LPSW_newext(8,0),1f+8-\b(\br)     # Set the return PSW
            nc     .LPSW_newext(0),1f+16-\b(\br)      # New PSW must run
            lpsw   1f+8-\b(\br)                       # Wait for interrupt
            .align 8                                  # Doubleword align PSW's
1:          .quad  0                                  # 1f    new PSW save area
         .ifeq .L__psw_arch     # S/370 BC-mode
            psw s=(\s)&0x00FC|0x0102,a=1b+18          # 1f+8  Wait PSW
            .hword 0xFEF5                             # 1f+16 New PSW run mask
         .else                  # S/370 EC-mode or ESA/390
            psw s=(\s)&44FF|0x0102,a=1b+18            # 1f+8  Wait PSW
            .hword 0xFEFD                             # 1f+16 New PSW run mask
         .endif
            mvc    .LPSW_newext(8,0),1b-\b(\br)       # 1f+18 Restore new PSW
       .endif
            .endm

    # This macro performs an in-line wait for an I/O interrupt

            .macro iowait s=0,br=13 b=0b
       .ifeq .L__psw_arch-3  # 64-bit architecture
            mvc    1f-\b(16,\br),.LPSW_newiog(0)     # Save current new PSW
            mvc    .LPSW_newiog(16,0),1f+16-\b(\br)  # Set the return PSW
            nc     .LPSW_newiog(2,0),1f+32-\b(\br)   # New PSW must run
            lpswe  1f+16-\b(\br)                     # Wait for interrupt
            .align 8                                 # Doubleword align PSW's
1:          .octa  0                                 # 1f     new PSW save area
            pswe   s=(\s)&0x46F7|0x0202,a=1b+34      # 1f+16  Wait PSW
            .hword 0x45F5                           # 1f+32 # 1f+32  New PSW run mask
            mvc    .LPSW_newiog(16,0),1b-\b(\br)     # 1f+34  Restore new PSW
       .else               # 32-bit architecture
            mvc    1f-\b(8,\br),.LPSW_newio(0)       # Save current new PSW
            mvc    .LPSW_newio(8,0),1f+8-\b(\br)     # Set the return PSW
            nc     .LPSW_newio(2,0),1f+16-\b(\br)    # New PSW must run
            lpsw   1f+8-\b(\br)                      # Wait for interrupt
            .align 8                                 # Doubleword align PSW's
1:          .quad  0                                 # 1f     new PSW save area
         .ifeq .L__psw_arch  # System/370 Basic Control Mode
            psw    s=(\s)&0x0001|0xFE00,a=1b+18      # 1f+8   Wait PSW
            .hword 0x01F5                            # 1f+16  New PSW run mask
         .else               # System/370 Extended Control Mode or ESA/390
            psw    s=(\s)&0x0001|0x0202,a=1b+18      # 1f+8   Wait PSW
            .hword 0x45FD                            # 1f+16  New PSW run mask
         .endif
            mvc    .LPSW_newio(8,0),1b-\b(\br)       # 1f+18  Restore new PSW
       .endif
            .endm

    # This macro performs an in-line wait for either an I/O or external interrupt

            .macro iowait_ext ext:req,s=0,br=13 b=0b
       .ifeq .L__psw_arch-3  # 64-bit architecture
            mvc    1f-\b(16,\br),.LPSW_newiog(0)     # Save current..
            mvc    1f+16-\b(16,\br),.LPSW_newextg(0) # ..new PSw's
            mvc    .LPSW_newiog(16,0),1f+32-\b(\br)  # Set the return PSW
            mvc    .LPSW_newextg(16,0),1f+32-\b(br)  # Set the return PSW
            nc     .LPSW_newiog(2,0),1f+48-\b(\br)   # Set run system mask
            nc     .LPSW_newextg(2,0),1f+48-\b(\br)  # Set run system mask
            oi     .LPSW_newextg+2(0),0x10           # Set cc=1 for external int.
            lpswe  1f+16-\b(\br)                     # Wait for interrupt
            .align 8                                 # Doubleword align PSW's
1:          .octa  0                                 # 1f     I/O new PSW save area
            .octa  0                                 # 1f+16  ext. new PSW save area
            pswe   s=(\s)&0x47F7|0x0302,a=1b+50      # 1f+32  Wait PSW
            .hword 0x44FD                            # 1f+48  New PSW system mask
            mvc    .LPSW_newiog(16,0),1b-\b(\br)     # Restore I/O new PSW
            mvc    .LPSW_newextg(16,0),1b+16-b(\br)  # Restore external new PSW
            brcl   1,\ext        # Go to handle an external interrupt
       .else               # 32-bit architecture
            mvc    1f-\b(8,\br),.LPSW_newio(0)       # Save current new PSW
            mvc    1f+8-\b(8,\br),.LPSW_newext(0)    # Save current new PSW
            mvc    .LPSW_newio(8,0),1f+8-\b(\br)     # Set the return PSW
            mvc    .LPSW_newext(8,0),1f+8-\b(\br)    # Set the return PSW
            nc     .LPSW_newio(2,0),1f+24-\b(\br)    # New PSW must run
            nc     .LPSW_newext(2,0),1f+24-\b(\br)   # New PSW must run
         .ifeq .L__psw_arch   # System/370 Basic Control Mode 
            oi     .LPSW_newext+4(0),0x10            # cc = 1 for external int.
         .else
            oi     .LPSW_newext+2(0),0x10            # cc = 1 for external int.   
         .endif
            lpsw   1f+16-\b(\br)                     # Wait for an interrupt
            .align 8                                 # Doubleword align PSW's
1:          .quad  0                                 # 1f     I/O new PSW save area
            .quad  0                                 # 1f+8   ext. new PSW save area
         .ifeq .L__psw_arch  # System/370 Basic Control Mode
            psw    s=(\s)|0xFF02,a=1b+26             # 1f+16  New PSW
            .hword 0x01F5                            # 1f+24  New PSW run mask
         .else               # System/370 Extended Control Mode or ESA/390
            psw    s=(\s)|0x0302,a=1b+26             # 1f+16  New PSW
            .hword 0x44FD                            # 1f+24  New PSW run mask
         .endif
            mvc    .LPSW_newio(8,0),1b-\b(\br)    # 1f+26  Restore new PSW
            mvc    .LPSW_newext(8,0),1b+8-\b(\br) #        Restore new PSW
         .ifeq .L__psw_arch-2       # ESA/390 can use relative branch
            brc    1,\ext           # Go to ESA/390 external interrupt handling
         .else                      # System/370
            bc     1,\ext-\b(\br)   # Go to System/370 external interrupt handling
         .endif                     # Fall through to I/O interrupt handling
       .endif
            .endm

.endif # .ifndef .Linterrupt_S
