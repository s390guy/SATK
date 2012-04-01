.ifndef .Lstrings_S
.Lstrings_S = 1
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

 # This module contains various macros used to assist in handling strings

 # Move a variable length string based upon an ending character
 # Arguments:
 #   %r0   = the ending character
 #   destr = register pointing to the destination
 #   srcr  = Input: register pointing to the start of the string
 #           Output: points to the byte following the ending character
 #   lenr  = Input: maximum length of the string including the ending char.
 #           Output: actual length moved including the ending char.
 #   wrkr  = Used internally by the macro

         .macro movestrg destr srcr lenr wrkr term=0x00
         lghi   0,\term           # Set the termination character
         stc    0,0(\srcr,\lenr)  # Make sure we end the MVST
         lgr    \wrkr,\srcr       # Use the wrkr to preserve src
         lgr    \lenr,\destr      # Use the lenr for destination
         mvst   \lenr,\wrkr       # Move the parm to my work area
         brc    1,.-4             # ..Continue if incomplete move
         slgr   \lenr,\destr      # Calculate the length
         la     \srcr,1(\srcr,\lenr) # Update source to point after the string
         .endm

 # These tables check for valid decimal characters and optional signs
 # They are intended for used with the TRT instruction
 #   Terminating function codes in general register R2
 #     0x04 == decimal string, R1 contains the end of string
 #     0x08 == Invalid decimal character found, R1 points to the char.
 #     0x0C == String longer than maximum length
 #     0x10 == Minus sign, R1 points to the minus sign

            .macro cvtckda
            .space 0x00-0x00+1,0x04  # 0x00      - End of valid dec string
            .space 0x2A-0x01+1,0x08  # 0x01-0x2F - invalid decimal
            .space 0x2B-0x2B+1,0x04  # 0x2B      - plus sign
            .space 0x2C-0x2C+1,0x0C  # 0x2C      - invalid decimal
            .space 0x2D-0x2D+1,0x14  # 0x2D      - minus sign
            .space 0x2F-0x2E+1,0x0C  # 0x2E-0x2F - invalid decimal
            .space 0x39-0x30+1,0x00  # 0x30-0x39 - valid decimal
            .space 0xFF-0x3A+1,0x08  # 0x3A-0xFF - invalid decimal
            .endm

            .macro cvtckde
            .space 0x00-0x00+1,0x04  # 0x00       - End of valid dec string
            .space 0x4D-0x01+1,0x0C  # 0x01-0x4D - invalid decimal
            .space 0x4E-0x4E+1,0x10  # 0x4E      - plus sign
            .space 0x5F-0x4F+1,0x0C  # 0x4F-0x5F - invalid decimal
            .space 0x60-0x60+1,0x14  # 0x60      - minus sign
            .space 0xEF-0x61+1,0x0C  # 0x61-0xEF - invalid decimal
            .space 0xF9-0xF0+1,0x00  # 0xF0-0xF1 - 0-9 valid decimal
            .space 0xFF-0xFA+1,0x0C  # 0xFA-0xFF - invalid decimal
            .endm

 # These tables check for valid hexadecimal characters
 # They are intended to be used with TRT
 #   Terminating function codes in general register R2:
 #     0x04 == Hexadecimal string, R1 contains the end of string
 #     0x08 == Invalid hexadecimal character found, R1 points to the char.
 #     0x0C == String longer than maximum length

 # ASCII hexadecimal validation table

            .macro cvtckxa
            .space 0x00-0x00+1,0x04  # 0x00      - End of valid hex string
            .space 0x38-0x01+1,0x08  # 0x01-0x28 - invalid hexadecimal
            .space 0x39-0x30+1,0x00  # 0x30-0x39 - 0-9 valid hexadecimal
            .space 0x3F-0x3A+1,0x08  # 0x3A-0x3F - invalid hexadecimal
            .space 0x46-0x41+1,0x00  # 0x41-0x46 - A-F valid hexadecimal
            .space 0x60-0x47+1,0x08  # 0x47-0x60 - invalid hexadecimal
            .space 0x66-0x61+1,0x00  # 0x61-0x66 - a-f valid hexadecimal
            .space 0xFF-0x67+1,0x08  # 0x67-0xFF - invalid hexadecimal
            .endm

 # EBCDIC hexadecimal validation table

            .macro cvtckxe
            .space 0x00-0x00+1,0x04  # 0x00      - End of valid hex string
            .space 0x80-0x01+1,0x08  # 0x01-0x80 - invalid hexdecimal
            .space 0x86-0x81+1,0x00  # 0x81-0x86 - Lower-case a-f valid
            .space 0xC0-0x87+1,0x08  # 0x87-0xC0 - invalid hexadecimal
            .space 0xC6-0xC1+1,0x00  # 0xC1-0xC6 - Upper-case A-F valid
            .space 0xEF-0xC7+1,0x08  # 0xC7-0xEF - invalid hexadecimal
            .space 0xF9-0xF0+1,0x00  # 0xF0-0xF1 - 0-9 valid hexadecimal
            .space 0xFF-0xFA+1,0x08  # 0xFA-0xFF - invalid hexadecimal
            .endm

 # This macro creates a translate table for decimal or hex that allows
 # the resulting bytes to be packed.  It assumes all characters are valid

            .macro cvttr
            .space 0x2F-0x00,0x00    
            .ascii  "0123456789"                 # 0x30-0x39 0-9 ASCII hex/dec
            .space 0x40-0x3A+1,0x00
            .byte  0x4A,0x4B,0x4C,0x4D,0x4E,0x4F # 0x41-0x46 A-F ASCII hex
            .space 0x60-0x47+1,0x00
            .byte  0x6A,0x6B,0x6C,0x6D,0x6E,0x6F # 0x61-0x66 a-f ASCII hex
            .space 0x80-0x67,0x00
            .byte  0x8A,0x8B,0x8C,0x8D,0x8E,0x8F # 0x81-0x86 a-f EBCDIC hex
            .space 0xC0-0x87+1,0x00
            .byte  0x8A,0x8B,0x8C,0x8D,0x8E,0x8F # 0xC1-0xC6 A-F EBCDIC hex
            .space 0xEF-0xC7+1,0x00
            .ascii "0123456789"                  # 0xF0-0xF1 0-9 EBCDIC hex/dec
            .space 0xFF-0xFA+1,0x00
            .endm

 # Check if the string is a valid hexadecimal or decimal string
 # The maximum length in \lenr does not include the 0x00 string terminator
 # but the terminator is checked. The termination code in R2 reflects the
 # status of the check. 0x00 is never the termination code.
 #
 # Note: General registers 1 and 2 are implied by the TRT instruction

            .macro cvtckg cktr str maxr br=15 b=0b
            sgr    2,2                # Clear the function byte reg
            lghi   2,0x0C             # Set length error indicator
            ex     \maxr,.+8-\b(\br)  # Use TRT to check validity
            j      .+10               # Branch around translate
            trt    0(1,\str),0(\cktr) # Check for validity
            .endm

            .macro cvthex str binr lenr wrkr br=15 b=0b
            xc     0(16,\wrkr),0(\wrkr)  # Clear the packed data area
            ex     \lenr,1f-\b(\br)      # Pack the hex data
            lg     \binr,7(\wrkr)        # Load the result
            j      .+10                  # Jump around packa
1:          pka    0(\wrkr),0(1,\str)    # Packs the data
            .endm

 # When converting hex to binary:
 #   str =                                     Fx.Fy.Fz.F?
 # ocat1 = 00.00.00.00.00.00.00.00.00.00.00.00.00.0x.yz.?S
 #         +0 +1 +2 +3 +4 +5 +6 +7 +8 +9 +A +B +C +D +E +F
 #                              <----binary result---->
            .macro cvtworkg
            .octa  0    # \wrkr+0    # Packed data
            .endm
            # determine remaining structure for decimal data
            #.octa  0    # \wrkr+16
            #.byte  0    # \wrkr+33
            #.byte  0x0C # Packed decimal zero

.endif
