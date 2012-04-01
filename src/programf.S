.ifndef .Lprogramf_S
.Lprogramf_S = 1
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

 # This module provides a number of useful macros to a program.
 #
 # Macros provided:
 #     Macro        Description
 #     clear24    Clear the high order bits of a 32-bit register for 24-bit addressing
 #     clear31    Clear the high order bits of a 32-bit register for 31-bit addressing
 #     clearg24   Clear the high order bits of a 64-bit register for 24-bit addressing
 #     clearg31   Clear the high order bits of a 64-bit register for 31-bit addressing
 #     ccndx      Convert the PSW in bits 30,31 or 62,63 into a branch table index
 #     fill       Fill each byte in an area of storage with a value (in-line MVC)
 #     fillloop   Fill each byte in an area of storage with a value (MVC loop)
 #     fillloopg  Fill each byte in an area of storage with a value (MVCLE loop)
 #     getcc      Get the PSW condition-code in bits 30,31 or 62,63 of a register
 #     getccndx   Get the PSW condition-code as a branch index 
 #     iplentry   Start an program that is entered by an IPL
 #     samx       Set the default address mode of the active architecture

 # Architecture sensitive set default address mode

         .macro samx
    .ifdef __s390x__
         sam64
    .else
    .ifdef __s390__
         sam31
    .endif
    .endif
         .endm

 # Clear high-order bits of registers for different addressing modes

         .macro clear24 reg
         sll    \reg,8
         srl    \reg,8
         .endm

         .macro clear31 reg
         sll    \reg,1
         srl    \reg,1
         .endm

         .macro clearg24 reg
         sllg   \reg,\reg,40
         srlg   \reg,\reg,40
         .endm

         .macro clearg31 reg
         sllg   \reg,\reg,33
         srlg   \reg,\reg,33
         .endm

 # Get the Condition Code from the current PSW

         .macro getcc reg:req
    .ifdef __s370__
         balr  \reg,0         # Get the cc for return in bits 2-3
         srl   \reg,28        # Put the condition code in bits 30,31
    .else
         ipm   \reg           # Get the cc for return bits 2-3
         srl   \reg,28        # Put the condition code in bits 30,31 or 62,63
    .endif
         .endm

 # Convert a condition code in a register to a branch index

         .macro ccndx reg:req
         sll   \reg,2         # Turn the cc into a branch index
         .endm

 # Get the Condition Code from the current PSW as a branch index

         .macro getccndx reg:req
         getcc  reg=\reg
         ccndx  reg=\reg
         .endm

 # fill - Fill an area of storage with a fixed value using in-line instructions
 #  Macro Parameters:
 #       startr Specify the register pointing to the start of the area (required)
 #       len    Specify the number of bytes to be filled (required)
 #       value  Specify the value to be placed in each byte (defaults to 0x00)
 #
 # This macro is limited to 4096 bytes to be cleared.  Use fillloop or fillloopg 
 # for more than 4096 bytes or when the length is unknown at assembly time.  This
 # macro will generate 16 MVC instructions for an area of 4096 bytes.  These MVC
 # instructions will consume 96 bytes within the program.  While the most efficient
 # in terms of instructions, this macro may take up more space.  This macro
 # requires the length to be known at assembly time.  If the length is not known
 # at assembly time use fillloop or fillloopg.

         .macro fill startr:req len:req value=0x00
         mvi    0(\start),\value
.L__fill_count = ((\len)+255)/256
.L__fill_len   = \len-1
.L__fill_disp  = 0
         .rept  .L__fill_count
     .ifge .L__fill_len-1        # If length >= 1 then generate an mvc instruction
     .ifge .L__fill_len-256
         mvc   .L__fill_disp+1(256,\startr),.L__fill_disp(\startr)
     .else
         mvc   .L__fill_disp+1(.L__fill_len),.L__fill_disp(\startr)
         .exitm
     .endif # .ifge .L__fill_len-256
.L__fill_len   = .L__fill_len-256
.L__fill_disp  = .L__fill_disp+256
         .endr  # .rept  .L__fill_count
         .endm

 # fillloop - Fill an area of storage with a fixed value using a MVC loop
 #  Macro Parameters:
 #       arearp An even or odd pair of registers.  The arearp register contains the
 #              address of the area to be filled.  The arearp+1 register contains
 #              the length of the area.
 #       valr   Specify the register whose low-order 8 bits contain the value to be 
 #              placed in each storage byte (required)
 #       br     The current base register (defaults to 13)
 #       b      The current base (defaults to 0b)
 #
 # This macro may be used in either 32-bit or 64-bit architectures provided the
 # area to be filled is not larger than 4G.  While requiring two register pairs, the 
 # fillloopg macro is recommended for z/Architecture.

         .macro fillloop arearp:req valr:req br=13 b=0b
         stc    \valr,0(\arearp)
         bct    (\arearp+1)&0xF,4f-\b(\br)
         la     (\arearp+1)&0xF,0xFF(0)
2:       cl     (\arearp+1)&0xF,4f-10-\b(\br)
         bnl    3f-\b(\br)
         lr     \valr,(\arearp+1)&0xF
         bctr   \valr,0
3:       ex     \valr,4f-6-\b(\br)
         la     \startr,1(\valr,\startr)
         sl     (\arearp+1)&0xF,4f-10-\b(\br)
         bc     0b0001,2b-\b(\br)
         b      4f-\b(\br)
         .long  256                        # 4f-10
         mvc    1(1,\arearp),0(\arearp)    # 4f-6
4:
         .endm

 # fillloopg - Fill an area of storage with a fixed value using a MVCLE loop
 #  Macro Parameters:
 #       arearp  An even or odd pair of registers.  The arearp register specifies
 #               the starting address of the area to be filled and the arearp+1
 #               register specifies the length of the area to be filled. (required)
 #       valr    A register containing the byte to fill the area
 #       workrp  An even or odd pair of work registers.
 #
 # This macro requires 64-bit architecture.  If running in a 32-bit architecture,
 # use fillloop

         .macro fillloopg arearp:req valr:req workrp:req
         sgr    \workrp,\workrp
         lgr    (\workrp+1)&0xF,\workrp
         mvcle  \arearp,\workrp,0(\valr)
         jc     0b0001,.-4
         .endm

 # iplentry - Start a program that will be IPL'd
 #  Macro Parameters:
 #       name   A global symbol identifying the programs entry point.  A local 
 #              symbol of the same name will also be created, .Lname 
 #              (defaults to 'start')
 #       iplparm Specify an address within the first 4096 bytes of storage where 
 #              the IPL parms (supplied in registers 0-15 by Hercules) are to be 
 #              stored.  Otherwise, registers 0-15 are not preserved
 #       clear  Specify 'yes' to set to zero registers 0-15.  The contents of the
 #              general registers are unpredictable if IPL parms have been provided
 #              or the program was loaded by a boot loader.  (defaults to 'no')
 #       br     Establishes the program base register.  (defaults to 13)
 #       b      Specify a symbol in addition to 0 whose value will correspond to the 
 #              base established in the br argument's register. (optional)
 #
 # The sample boot loaders will always save general registers 0-15 at address 0x200.
 # Some of the sample boot loaders provide the entry address in general register 1
 # and the location of the program's ELF header in general register 0.  If the
 # program depends upon these values, do not specify clear=yes.
 #
 # The global symbol 'start' is automatically recognized by the ipldpp.py linker 
 # generation utility as the program entry point.  If a name other than 'start', the
 # default, is used, then the --entry argument of ipldppp.py must be specified.

         .macro iplentry name iplparm clear=no br=13 b
         .ifb   \name   # Make sure start defined if using
start:   .global start
.Lstart:
         .else  # .ifb   \name
\name:   .global \name
.L\name:
         .endif # .ifb   \name
    .ifnb \iplparm
         stm   0,15,\iplparm(0)
    .endif # .ifnb \iplparm
    .ifc \clear,yes
         sr    0,0
         lr    1,0
         lr    2,0
         lr    3,0
         lr    4,0
         lr    5,0
         lr    6,0
         lr    7,0
         lr    8,0
         lr    9,0
         lr    10,0
         lr    11,0
         lr    12,0
         lr    13,0
         lr    14,0
         lr    15,0
     .endif # .ifc \clear,yes
         basr  \br,0
     .ifnb \b
\b:
     .endif # .ifnb \b
0:
         .endm

 # iplparmg - Retrieve the IPL parameter from low storage in z/Architecture
 #  Macro Parameters:
 #       parm   The symbol associated with the receiving location for the IPL parms
 #              (required)
 #       lenr   Register to contain the length of the IPL parms moved (required)
 #       wrkr   A work register (required)
 #       ipr    A work register that will point to the IPL parm savearea (required)
 #       ip     The prefix area location where the IPL parms are saved
 #              (defaults to 0x200)
 #       term   The character or byte value indicating the end of the IPL parms.
 #              (defaults to 0x00)
 #
 # The IPL parms are moved based upon the termination character to a specified
 # location.  The location must be large enough to hold the 64-bytes of parm
 # characters.  Note the termination character will be placed in ip+64 to ensure
 # the scan terminates.  This macro uses the MVST instruction only available in
 # z/Architecture

         .macro iplparmg parm:req lenr:req wrkr:req ipr:req ip=0x200 term=0x00
    .ifdef __s390x__
         la     \ipr,\ip        # Point to the start of the IPL parms
         mvi    16*4(\ipr),0x00 # Set the end of IPL parms
         lghi   0,\term         # Set the string termination character
         larl   \lenr,\parm     # Point to receiving area of the parm
         lgr    \wrkr,\lenr     # Save the start to figure out the length
         mvst   \lenr,\ipr      # Move the parm to my work area
         brc    1,.-4           # ..Continue if incomplete move
         slgr   \lenr,\wrkr     # Calculate the length
    .else
    .error "iplparmg requires z/Architecture to be enabled"
    .endif
         .endm

 # Establish a s370 Basic control mode program interrupt handler

         .macro pgmintb addr br=13 b=0b
         mvc    0x68(8,0),.+10-\b(\br)
         b      .+12-\b(\br)
1:       .hword 0x0000,0x0000
         .long  \addr
         .endm

 # Establish a s370 Extended control mode interrupt handler

         .macro pgminte addr br=13 b=0b
         mvc    0x68(8,0),.+10-\b(\br)
         b      .+12-\b(\br)
1:       .hword 0x0008,0x0000
         .long  \addr
         .endm

 # Establish a s390 program interrupt handler

         .macro pgmint addr br=13 b=0b
         mvc    0x68(8,0),.+10-\b(\br)
         b      .+12-\b(\br)
1:       .hword 0x0008,0x0000
         .long  \addr+0x80000000
         .endm

 # Establish a s390x program interrupt handler

         .macro pgmintx addr br=13 b=0b
         mvc    0x1D0(16,0),.+10-\b(\br)
         j      .+20
1:       .hword 0x0000,0x0001
         .long  0x80000000
         .quad  \addr
         .endm

 # Start a program

         .macro program name:req base br=13 b=0
\name:   .global \name
         basr  (\br),0
    .ifnb \base
\base:
    .endif # .ifnb \b
\b:
         .endm

 # Relocate dynamically a list of 32-bit address displacements
 # Registers 0-3 are used implicitly

         .macro rellst start end br=13 b=0b
         la    0,4                 # R3
         la    1,(\end-1)-\b(\br)  # R3+1
         la    2,\start-\b(\br)    # R1
         lr    3,\br               # -10
         al    3,0(2)              # -8
         st    3,0(2)              # -4
         bxle  2,0,(.-10)-\b(\br)
         .endm

 # Relocate dynamically a list of 64-bit addresses
 # Registers 0-3 are used implicitly

         .macro rellstg start end br b=0b
         la    0,4                 # R3
         la    1,(\end-1)-\b(\br)  # R3+1
         la    2,\start-\b(\br)    # R1
         lgr   3,\br               # -16
         alg   3,0(2)              # -12
         stg   3,0(2)              # -6
         bxleg 2,0,(.-16)-\b(\br)
         .endm

 # Relocate dynamically a 32-bit address displacement

         .macro relo addr br=13 b=0b wrkr=0 clear=no
         lr    \wrkr,\br
    .ifc \clear,yes
         clear24
    .endif # .ifnb \clear
         al    \wrkr,(\addr)-\b(\br)
         st    \wrkr,(\addr)-\b(\br)
         .endm

 # Relocate dynamically a 64-bit address displacement

         .macro relog addr br=13 b=0b wrkr=0 clear=no
         lgr    \wrkr,\br
    .ifc \clear,yes
         clearg31 \wrkr
    .endif
         alg    \wrkr,(\addr)-\b(\br)
         stg    \wrkr,(\addr)-\b(\br)
         .endm

.endif # .ifndef .Lprogramf_S scope
