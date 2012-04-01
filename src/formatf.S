.ifndef .Lformatf_S
.Lformatf_S = 1
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

 # This module provides macros for formatting numeric and hex data
 # into ASCII characters.  Macros are ABI comformant and can use the stack for the
 # work area or storage within the executable.  All macros may be used in any
 # architecture.
 #
 #  Macro      Description
 #  dispcx     Field-based character hexadecimal ASCII/EBCDIC display conversion
 #  dispcxr    Register-based character hexadecimal ASCII/EBCDIC display conversion
 #  dispfdr    Register-based signed decimal ASCII/EBCDIC display conversion
 #  dispfx     Field-based full word hexadecimal ASCII/EBCDIC display conversion
 #  disphx     Field-based half word hexadecimal ASCII/EBCDIC display conversion
 #  disphxr    Register-based half word hexadecimal ASCII/EBCDIC display conversion
 #  disptr     Create translate tables and pointers for use with formatf.S macros
 #  dispwork   Establishes a work area in local storage (program or stack)
 #
 # The macros function together to support conversion of binary data into decimal
 # or hexadecimal displayable ASCII or EBCDIC character sequences.  The following
 # example illustrates how the macros are used within an ABI function to perform
 # these conversions.  Only details relavant to the macro relationships are
 # illustrated.  Refer to individual macros for a complete description of a macro's
 # parameters.
 #
 #            abi_func .Lafunction
 #            
 #            dispwork name=.Lworkarea,stack=yes
 #
 #            abi_push
 #
 #            la       8,.Lworkarea(15)      # Locate the work area in the stack
 #            l        7,.Lasciitt-0b(13)    # Locate the translate table
 #            dispcx   ...,wpr=8,tpr=7,...
 #            
 #            abi_return
 #
 #            disptr ascii=.Lasciitt,ebcdic=.Lebcdictt
 #
 # No macros or functions are provided to convert character data in binary at this
 # point.

 # dispwork - Generate the work area needed by the formatting macros.  The macros
 #            utilize a work area and destination area as described below.
 #
 #  Macro Parameters:
 #      name     The symbol associated with the generated work area (required)
 #      stack    Specify 'yes' to define the work area within the local stack area,
 #               otherwise generate the work area within the executable.
 #               (defaults to 'no')
 #
 # Work area usage:
 #      +0 +1 +2 +3 +4 +5 +6 +7 +8 +9 +10 +11
 #      ff ff ff ff ff ff ff ff ?? .. ..  ..   dispfx
 #      00 00 09 99 99 99 99 9s .. .. ..  ..   dispfr
 #      .. .. .. hh hh hh hh ?? .. HH HH  ??   disphx, disphxr
 #      .. .. .. .. .. cc cc ?? .. .. CC  ??   dispcx, dispcxr
 #
 # Destination area usage:
 # Size +0 +1 +2 +3 +4 +5 +6 +7 +8 +9 +10 +11 +12 +13 +14 +15
 #  16  hx hx hx hx hx hx hx hx .. .. ..  ..  ..  ..  ..  ..   dispfx
 #  10  F9 F9 F9 F9 F9 F9 F9 F9 F9 F9 ss  ..  ..  ..  ..  ..   dispfr
 #   4  hx hx hx hx .. .. .. .. .. .. ..  ..  ..  ..  ..  ..   disphx, disphxr

        .macro dispwork name:req stack=no
    .ifc \stack,yes
        falign 8
        fbytes name=\name,number=12
    .else
        .align 8
\name:
        .quad  0
        .long  0
    .endif
        .endm

 # disptr - Generate translate tables and pointers to be used with formatf.S macros.
 #          64-bit pointers are generated is __s390x__ is defined, otherwise 32-bit
 #          pointers are generated.
 #
 #  Macro Parameters:
 #      ascii    Specify a symbol associated with the address of the generated 
 #               ASCII translate table.  If ommitted, an ASCII trasnslate table is
 #               not generated.
 #      ebcdic   Specify a symbol associated with the address of the generated
 #               ASCII translate table.  If ommitted, an ASCII trasnslate table is
 #               not generated.
 #
 # The address of the translate table must be supplied in a register when one of
 # formatting macros is used.  This allows the macros to support either ASCII or
 # EBCDIC conversion.
 #
 # When using a EBCDIC oriented device for providing end user data, EBCDIC is
 # required.  When using DIAGNOSE X'08' for message display, either ASCII or 
 # EBCDIC may be used in conjunction with. respectively, the dispa[p] or dispe[p] 
 # macros.  Because the GNU tools utilized by SATK are ASCII based, it is frequently
 # easier to work with ASCII rather than EBCDIC.

        .macro disptr ascii ebcdic
    .ifnb \ascii
    .ifdef __s390x__             # 64-bit architecture
        .align 8
\ascii: .quad  .+8-0xF0
    .else # .ifdef __s390x__     # 32-bit architecture
        .align 4
\ascii: .long  .+4-0xF0
    .endif
        .ascii "0123456789ABCDEF-"
    .endif
    .ifnb \ebcdic
    .ifdef __s390x__             # 64-bit architecture
        .align 8
\ebcdic:.quad  .+8-0xF0
    .else  # .ifdef __s390x__    # 32-bit architecture
        .align 4
\ebcdic:.long  .+4-0xF0
    .endif # .ifdef __s390x__
        .ascii "\xF0\xF1\xF2\xF3\xF4\xF5\xF6\xF7\xF8\xF9\xC1\xC2\xC3\xC4\xC5\x60"
    .endif
        .endm

 # dispcx - Format for ASCII/EBCDIC display in hexadecimal of a 8-bit local field's 
 #          content
 #
 #  Macro Parameters:
 #      dest     2-byte local storage field to contain the ASCII hexadecimal 
 #               (required)
 #      src      8-bit local storage field to be displayed (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #      stack    If specified stack=yes, source and destination are on the stack
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)

        .macro dispcx dest:req src:req wpr:req tpr:req stack=no br=13 b=0b
    .ifc \stack,yes
        unpk  5(3,\wpr),\src(2,15)
        tr    5(2,\wpr),0(\tpr)
        mvc   \dest(2,15),5(\wpr)
    .else
        unpk  5(3,\wpr),(\src)-0b(2,\br)
        tr    5(2,\wpr),0(\tpr)
        mvc   (\dest)-0b(2,\br),5(\wpr)
    .endif
        .endm

 # dispcxr - Format for ASCII/EBCDIC hexadecimal display the low-order 8-bits of a
 #           register's content.
 #
 #  Macro Parameters:
 #      destpr   Register pointing to where the formatted data will be placed.
 #               The destination area requires 2 bytes (required)
 #      srcr     Register containing the 8-bits intended for display (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #                   Preparation example:  l tpr,name-0b(13)

        .macro dispcxr destpr:req srcr:req wpr:req trr:req
        stc   \srcr,10(\wpr)
        unpk  5(3,\wpr),10(2,\wpr)
        tr    5(2,\wpr),0(\tpr)
        mvc   0(2,\destpr),5(\wpr)
        .endm

 # dispfdr - Format for ASCII/EBCDIC display in base 10, with sign, a 32-bit register's 
 #           content.
 #  Macro Parameters:
 #      destpr   Register pointing to where the formatted data will be placed.
 #               The destination area requires 10 bytes (required)
 #      srcr     Register containing the fullword inteded for display (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)

        .macro dispfdr destpr:req srcr:req wpr:req tpr:req br=13 b=0b
        mvi   10(\destpr),0x20
        ltr   \srcr,\srcr
        bnm   .+8-\b(\br)
        mvc   10(\destpr),16(\tpr)
        cvd   \srcr,0(\wpr)
        oi    7(\wpr),0x0F
        unpk  0(10,\destpr),2(6,\wpr)
        tr    0(10,\destpr),0(\tpr)
        .endm

 # dispfx - Format for ASCII/EBCDIC display in base 16 a 32-bit local field's 
 #          content
 #
 #  Macro Parameters:
 #      dest     8-byte local storage field to contain the ASCII hexadecimal 
 #               (required)
 #      src      32-bit local storage field to be displayed (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #                   Preparation example:  l tpr,name-0b(13)
 #      stack    If specified stack=yes, source and destination are on the stack
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)

         .macro dispfx dest:req src:req wpr:req tpr:req stack=no br=13 b=0b
    .ifc \stack,yes
         unpk   0(9,\wpr),\src(5,15)
         tr     0(8,\wpr),0(\tpr)
         mvc    \dest(8,15),0(\wpr)
    .else
         unpk   0(9,\wpr),(\src)-0b(5,\br)
         tr     0(8,\wpr),0(\tpr)
         mvc    (\dest)-0b(8,\br),0(\wpr)
    .endif
         .endm

 # disphx - Format for ASCII/EBCDIC display, in base 16, a 16-bit local field's 
 #          content
 #
 #  Macro Parameters:
 #      dest     4-byte local storage field to contain the ASCII hexadecimal 
 #               (required)
 #      src      16-bit local storage filed containing for display (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #                   Preparation example:  l tpr,name-0b(13)
 #      stack    If specified stack=yes, source and destination are on the stack
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)

        .macro disphx dest:req src:req wpr:req trr:req stack=no br=13 b=0b
    .ifc \stack,yes
        unpk    3(5,\wpr),\src(15)
        tr      3(4,\wpr),0(\trr)
        mvc     \dest(4,15),3(\wpr)
    .else
        unpk   3(5,\wpr),(\src)-0b(3,\br)
        tr     3(4,\wpr),0(\trr)
        mvc    (\dest)-0b(4,\br),3(\wpr)
    .endif
        .endm

 # disphxr - Format for ASCII display in base 16 low-order 16-bits of a register's 
 #           content.
 #  Macro Parameters:
 #      destpr   Register pointing to where the formatted data will be placed.
 #               The destination area requires 4 bytes (required)
 #      srcr     Register containing the 16-bits inteded for display (required)
 #      wpr      Register pointing to the 12-byte doubleword aligned work area
 #               (required)
 #      tpr      Register pointing to the translate table.  Must be the pointer
 #               generated by the asxii=name parameter of the disptr macro.
 #               (required)
 #                   Preparation example:  l tpr,name-0b(13)
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)  

        .macro disphxr destpr:req srcr:req wpr:req trr:req br=13 b=0b
        sth    \srcr,9(\wpr)
        unpk   3(5,\wpr),9(3,\wpr)
        tr     3(4,\wpr),0(\trr)
        mvc    0(4,\destpr),3(\wpr)
        .endm

 # dispap - Display on the HMC using DIAGNOSE 8 an ASCII message. A pointer is used
 #          to locate the dispmsg function in displayf.S
 #  Macro Parameters:
 #      msg      Symbol identifying the message location
 #      len      The length of the message to be displayed
 #      stack    If specified as stack=yes, the message is located on the stack
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)        

         .macro dispap msg:req len:req stack=no br=13 b=0b
    .ifc \stack,yes
         la     %r2,\msg(%r15)
    .else
         la     %r2,\msg-\b(\br)
    .endif
         la     %r3,\len
         sr     %r4,%r4
         abi_callp .Ldispmsgf
         .endm 

 # dispep - Display on the HMC using DIAGNOSE 8 an EBCDIC message. A pointer is used
 #          to locate the .Ldispmsgf function in displayf.S
 #  Macro Parameters:
 #      msg      Symbol identifying the message location
 #      len      The length of the message to be displayed
 #      stack    If specified as stack=yes, the message is located on the stack
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)        

         .macro dispep msg:req len:req stack=no br=13 b=0b
    .ifc \stack,yes
         la     %r2,\msg(%r15)
    .else
         la     %r2,(\msg)-\b(\br)
    .endif
         la     %r3,\len
         la     %r4,1
         abi_callp .Ldispmsgf
         .endm 

 # dispa - Display on the HMC using DIAGNOSE 8 an ASCII message. A base-displacement
 #         or PC-relative method is used to locate the dispmsg function in 
 #         displayf.S
 #  Macro Parameters:
 #      msg      Symbol identifying the message location
 #      len      The length of the message to be displayed
 #      stack    Specified 'yes' to locate the message within the local stack area, 
 #               otherwise the message is located within the executable using
 #               base-displacement addressing.  (defaults to 'no')
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)     

         .macro dispa msg:req len:req stack=no br=13 b=0b
    .ifc \stack,yes
         la     %r2,\msg(%r15)
    .else
         la     %r2,\msg-\b(\br)       # Point to message
    .endif
         la     %r3,\len               # ..its length
         sr     %r4,%r4                # Display ASCII message
         abi_call .Ldispmsgf           # ..and display it
         .endm

 # Display an EBCDIC text message using relative addressing
 # dispe - Display on the HMC using DIAGNOSE 8 an EBCDIC message. A 
 #         base-displacement or PC-relative method is used to locate the dispmsg 
 #         function in displayf.S
 #  Macro Parameters:
 #      msg      Symbol identifying the message location
 #      len      The length of the message to be displayed
 #      stack    Specified 'yes' to locate the message within the local stack area, 
 #               otherwise the message is located within the executable using
 #               base-displacement addressing.  (defaults to 'no')
 #      br       Local base register (default 13 for ABI conformance)
 #      b        Local base (default 0b for ABI conformance)     

        .macro dispe msg:req len:req stack=no br=13 b=0b 
    .ifc \stack,yes
        la     %r2,\msg(%r15)
    .else
        la     %r2,\msg-\b(\br)       # Point to message
    .endif
        la     %r3,\len               # ..its length
        la     %r4,1                  # Display EBCDIC message
        abi_call .Ldispmsgf            # ..and display it 
        .endm

.endif # .ifndef .Lformatf_S scope
