          .title "ihandlers Sample - IPL ELF"
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
          
 # ih.S is a sample program illustrating the use of various SATK components,
 # but specifically how to establish interrupt handlers.
 #
 # Memory Usage:
 #   0x0200-0x023F    Hercules IPL parms in 32-bit R0-R15 on entry
 #   0X0D00-0x0FFF    Interrupt Handler R0-R15 save areas
 #
 #   0x2000+          ih IPL ELF loaded at 0x2000
 #
 #   The IPL ELF headers are accommodated by the SATK IPL media preparation tools 
 #   regardless of their presence in the IPL media.  This is a consequence of the
 #   ELF file structure.  So to go from a location in the assembly listing to a
 #   real storage address during execution, add the appropriate value to the 
 #   assembly listing location:
 #
 #      32-bit IPL ELF executable - 0x2060 (S/370 or ESA/390) or
 #      64-bit IPL ELF executable - 0x2080 (z/Architecture).
 #
 #   If examining a Hercules trace or display of real storage, the above value
 #   must be subtracted from the real storage address to translate back to an 
 #   assembly listing location.

           .nolist
           .include "ABI.S"        # Generic ABI macros (all archs)
           .nolist
           .include "ABI-s390.S"   # 32-bit ELF ABI macros (for s370 and s390)
           .nolist
           .include "ABI-s390x.S"  # 64-bit ELF ABI macros (for s390x)
           .include "ABI-lcls.S"   # Macros that define local usage of the stack
           .include "formatf.S"    # Macros for binary to character conversions
           .include "psw.S"        # Macros for PSW generation
           .include "programf.S"   # Disabled wait error code macros for displayf.S
           .include "ihandler.S"   # Macros for interrupt handlers
           .include "memperm.S"    # Macro for .Lmemperm/.Lmempermg functions
           .list
           .list
           .eject
 # Establish ABI for this assembly based upon command line symbol __ARCH__
 #   packed=yes fp=soft and bp=no provide the smallest function call frame size.
 #   This means a minimal amount of debugging information.

           abi_options packed=yes fp=soft bp=no
 # TEXT Segment
           .text
.L_ipl:
_start:    .global _start
           stm     0,15,0x200       # Save IPL parameters before doing anything else
           basr    13,0
0:
 # Establish ABI registers (and if required enter 64-bit mode)
           abi_run  stack=.Lstack cpur=6 statr=8 fail=.Lendbad      

.ifdef __s390x__             # 64-bit system

           la    1,.L_fsizeg+16(15)  # Allocate past my stack area
           lghi  2,16                # Align on a 16-byte boundary
           abi_call .Lmempermg       # Allocate the storage I am currently using
           sr    1,1                 # Allocate zero bytes to force alignment
           lgf   2,.Lpagesize-0b(13) # Align allocated memory to next page boundary
           abi_call .Lmempermg       # Allocate out to next page boundary
          
           # we are now set to allocate interrupt handler stacks and enable them
          
           ihandlers_enable64 table=.Lhandler_table64,tblr=7,ntryr=8,wrkr=9,ihsr=10
                    
           # We can now issue SVC's

           svc   .L__psw_arch         # Test the SVC

           b     .Lendgood-0b(13)     # End the program 
           
.Lendgood: lpswe  .Lendgoodp-0b(13)
.Lendbad:  lpswe  .Lendbadp-0b(13)

           .align 8
.Lendbadp: pswe   s=0x0002,a=0xdead
.Lendgoodp:pswe   s=0x0002,a=0

.else  # .ifdef __s390x__   # 32-bit system

           la    1,.L_fsize+16(15)    # Allocate past my stack area
           la    2,16                 # Align on a 16-byte boundary
           abi_call .Lmemperm         # Allocate the storage I am currently using
           sr    1,1                  # Allocate zero bytes to force alignment
           l     2,.Lpagesize-0b(13)  # Align allocated memory to next page boundary
           abi_call .Lmemperm         # Allocate out to next page boundary

           # we are now set to allocate interrupt handler stacks and enable them

           ihandlers_enable table=.Lhandler_table,tblr=7,ntryr=8,wrkr=9,ihsr=10
          
           # We can now issue SVC's

           svc   .L__psw_arch         # Test the SVC
          
           b     .Lendgood-0b(13)     # End the program
           
.Lendgood: lpsw    .Lendgoodp-0b(13)
.Lendbad:  lpsw    .Lendbadp-0b(13)

           .align 8
.Lendbadp: psw    s=0x0002,a=0xdead
.Lendgoodp:psw    s=0x0002,a=0

.endif # .ifdef __s390x__

          .align  8

.Lpagesize:.long  4096
          
 # End bad if can not enter z/Architecture 64-bit mode
.Lendbad:  lpsw    .Lendbadp-0b(13)
.Lendgood: lpsw    .Lendgoodp-0b(13)
           .align  8
.Lendbadp:  psw    s=0x0002,a=0xdead
.Lendgoodp: psw    s=0x0002,a=0

.ifdef __s390x__             # 64-bit system

 # Define 64-bit handlers and tables

           .eject
           .sbttl "mempermg function"

           memperm bit64=yes        # Generate the 64-bit permanent memory allocator

           .eject
           .sbttl "ihandler table"
          
           # Table of interrupt handlers to be enabled by ihandler_enable64
           ihandler_table64 table=.Lhandler_table64,svc=.LSVC

           .eject
           .sbttl "Supervisor Call Interrupt Handler"
           ihandler_svc64 handler=.LSVC,size=4096  # Define the SVC handler

           ihandler_enter64 handler=.LSVC          # Enter handler on SVC interrupt

           icode_svc64 r=2                         # Load the SVC code into R2
           abi_call .Lsvc_processor

           ihandler_exit64 handler=.LSVC           # Return to interrupted program

.else  # .ifdef __s390x__    # 32-bit system

 # Define 32-bit handlers and tables
 
           .eject
           .sbttl "memperm function"

           memperm bit32=yes        # Generate the 32-bit permanent memory allocator

           .eject
           .sbttl "ihandler table"

           # Table of interrupt handlers to be enabled by ihandler_enable
           ihandler_table table=.Lhandler_table,svc=.LSVC
          
           .eject
          .sbttl "Supervisor Call Interrupt Handler"
           ihandler_svc handler=.LSVC,size=4096 # Define the SVC handler
          
           ihandler_enter handler=.LSVC         # Enter handler on SVC interrupt
           
           icode_svc r=2                        # Load the SVC code into R2
           abi_call .Lsvc_processor
           
           ihandler_exit handler=.LSVC          # Return to interrupted program
          
.endif # .ifdef __s390x__

           .eject
           .sbttl "Supervisor-Call Interrupt Function"
           
 # Entry Register Usage:
 #
 #   R2  = interruption code in low-order 8-bits of register
 #   R13 = Function base register
 #   R14 = Function return address
 #   R15 = Local stack pointer
 #
 # Exit Register Usage: none

            abi_func .Lsvc_processor
           
 # Local literal pool:
.Lmsg:      .ascii "SUPERVISOR CALL: "
.Lmsg_code: .ascii "??"
.Lmsg_len   =      .-.Lmsg
            disptr   ascii=.Lascii

 # Local stack frame area
           dispwork .Lworkarea,stack=yes
           fbytes   .Lmsgwk,.Lmsg_len
           fbyte    .Lsvccode
           
           abi_push
           
           mvc      .Lmsgwk(.Lmsg_len,15),.Lmsg-0b(13)   # Put message in work area
           stc      2,.Lsvccode(15)                      # Put code into stack
           la       7,.Lworkarea(15)                     # Point to workarea
           
    .ifdef __s390x__
           lg       8,.Lascii-0b(13)                     # Locate translate table
    .else
           l        8,.Lascii-0b(13)                     # Locate translate table
    .endif
           dispcx   dest=.Lmsg_code-.Lmsg+.Lmsgwk,src=.Lsvccode,wpr=7,tpr=8,stack=yes
           
           dispa    msg=.Lmsgwk,len=.Lmsg_len,stack=yes 
           
           abi_ret

           .eject
           .sbttl "DIAGNOSE X'08' Message Display Function"
           .include "displayf.S"
           
           .eject
           .sbttl "Establish program run-time stack"

 # Create a pointer to a stack that starts at 4096 bytes beyond this location
           .align  4
           abi_stack_start name=.Lstack size=4096 
           .end
