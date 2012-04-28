          .title "IPL ELF IPL Function Sample"
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
 
 # This is a test source module to develop support for the IPL ELF ABI Supplement.  
 # The program's text segment is loaded directly into storage by the IPL function
 # including the default LOWC content.  The booted program is nothing more than a 
 # hello world program.  A boot loader is not used with this program.
 #
 # The lodrtest bash script in this program's directory is used to build and test 
 # the IPL medium containing this program.
          
          .sbttl "IPL Program"
          
    .ifdef __s390x__
          .include "psw.S"
    .endif

 # TXT Segment
          .text
.L_ipl:
 # Because this program is loaded by the IPL function constrained to Format 0 CCW's
 # it may only be loaded into the first 16M of storage. It will be entered in either
 # an S/370 mode or in ESA/390 mode depending upon the hardware architecture. The
 # program must enter z/Architecture mode itself as determined by assembly time
 # defined symbols.

_start:   .global _start
          basr    15,0
0:        
    .ifdef __s390x__
          zarch   statr=10,cpur=12,error=.Lendbad,er=13,br=15
    .endif
          lm      2,5,.Lparms-0b(15)
          diag    2,4,0x8          # Issue command containing the message
          ltr     4,4              # Did an error occur?
          bz      .Lendok-0b(15)   # ..No, end OK
          lpsw    .Lendbad-0b(15)  # ..Yes, end BAD
.Lendok:  lpsw    .Lendpsw-0b(15)  # End with a disabled wait (code 0)
.Lparms:  .long   .Lmsg       # Rx = command string address
          .long   0           # Rx+1 = response buffer address
          .long   .Lmsglen    # Ry = command string length and flags (no response)
          .long   0           # Ry+1 = response buffer length
.Lmsg:    .byte   0xD4,0xE2,0xC7,0xD5,0xD6,0xC8,0x40  # 'MSGNOH'  in EBCDIC
          .byte   0x40,0x5C,0x40                      # ' * '     in EBCDIC
          .byte   0xC8,0x85,0x93,0x93,0x96,0x40       # 'Hello '  in EBCDIC
          .byte   0xA6,0x96,0x99,0x93,0x84            # 'world'   in EBCDIC
.Lmsglen  =       .-.Lmsg
          .align  8
.Lendpsw: .hword  0x000A,0
          .long   0
.Lendbad: .hword  0x000A,0
          .long   0xbad

          .end
