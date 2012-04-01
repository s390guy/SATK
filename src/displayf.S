.ifndef .Ldisplayf_S
.Ldisplayf_S = 1
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

 # Dependencies:
 #    ABI.S      - for ABI macros
 #    EBCDIC.S   - for ASCII to EBCDIC translation table
 #    programf.S - for dwait macro
 #
 # This function displays an ASCII or EBCDIC message on the 
 # hardware maintenance console.
 #
 # The formatf.S macros call this function correctly.
 #
 # Register Usage:
 #   Input:
 #          %r2  = Address of the message to be displayed
 #          %r3  = Length of the message to be displayed
 #          %r4  = Message encoding: 0 == ASCII, not 0 == EBCDIC
 #   Output:
 #          Disabled wait state if display fails
 #
 #   Processing:
 #          %r3  = EXECUTE instruction length

            .align 2

            abi_func .Ldispmsgf
            
 # Set up my literals:
 
 # EBCDIC command header executed via DIAGNOSE 8
.Ldmg_msg:  .ascii "\xD4\xE2\xC7\xD5\xD6\xC8\x40"  # 'MSGNOH ' in EBCDIC
            .ascii "\x5C\x40\xC1\xE3\x40\x5C\x40"  # '* AT * ' in EBCDIC
.Ldmg_prfx  =  .-.Ldmg_msg

 # Set up my local stack usage
            fbytes .Ldmg_hdr,number=.Ldmg_prfx
            fbytes .Ldmg_area,number=256
            abi_push

            # Move the ASCII message text to the internal buffer
            cl    3,.Ldmg_max-0b(13)    # Message length more than 256?
            bnh   .Ldmg_ok-0b(13)       # ..No, proceed
            l     3,.Ldmg_max-0b(13)    # ..Yes, truncate to 256
            # This is a bit cleaner than simply using the low order 
            # byte length where a length of 257 would turn into 1

.Ldmg_ok:
            # decrement message text length for EXECUTE instructions
            bctr  3,0
            # Move text content to message buffer
            ex    3,.Ldmg_move-0b(13)

            ltr   4,4                   # Is the message ASCII?
            bnz   .Ldmg_notr-0b(13)     # ..No, it's EBCDIC, do not translate
            # Translate the ASCII text to EBCDIC
            ex    3,.Ldmg_tran-0b(13)

.Ldmg_notr:
            mvc   .Ldmg_hdr(.Ldmg_prfx,15),.Ldmg_msg-0b(13)
            # Use DIAGNOSE X'8' to display the message
            la    2,.Ldmg_prfx+1(3)     # Ry: zero flags, set length
            la    1,.Ldmg_hdr(15)       # Rx: point to command
            diag  1,2,0x008             # issue command

            # Test for two levels of errors: the DIAGNOSE and command
            # cc!=0 means the DIAGNOSE instruction failed
            bnz   .Ldmg_diagerr-0b(13)
            # rc!=0 means the command itself failed
            ltr   2,2
            bnz   .Ldmg_cmderr-0b(13)

            # Successful DIAGNOSE, return to caller
            abi_ret

.Ldmg_diagerr:
            dwait code=0xF000,program=0

.Ldmg_cmderr:
            dwait code=0xF001,program=0

            .align 2
.Ldmg_max:  .long 256   # Maximum supported text size

            # move text to buffer with EXECUTE
.Ldmg_move: mvc   .Ldmg_area(1,15),0(2)

            # Translate message to EBCDIC with EXECUTE
.Ldmg_tran: tr    .Ldmg_area(1,15),.Ldmg_a2e-0b(13)

           .include "EBCDIC.S"   # Include translation tables if needed

.Ldmg_a2e:  TR_A_E

.endif # .ifndef .Ldisplay_S scope
