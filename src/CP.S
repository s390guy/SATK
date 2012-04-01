.ifndef .Lcp
.Lcp = 1
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

         .include "dwait.S"

 # Issue a command in-line
 
 # Note: ebcdic argument is the command in EBCDIC encoding.
 # It can be coded: "\xhh\xhh\xhh"
 
         .macro command rx:req ry:req ebcdic:req code:req satk=0 br=15 b=0b
         b      3f-\b(\br)
1:       .ascii "\ebcdic"
2:       .align 2
3:       la     \rx,1b-\b(\br)   # DIAGNOSE X'8' - Rx  (command address)
         la     \ry,2b-1b        # DIAGNOSE X'8' - Ry  (command length)
         diag   \rx,\ry,0x8      # Issue command
         bz     4f-\b(\br)       # DIAGNOSE failed?
         b      5f-\b(\br)       # ..Yes, disabled wait
4:       ltr    \ry,\ry          # Command error?
         bz     6f-\b(\br)       # ..No, proceed, command successful
5:       dwait  code=\code,program=\satk    # DIAGNOSE failed
6:
         .endm

 # Get real device information
 
         .macro rdevinfo devr:req notexist vrdcblokr am br=15 b=0b
         .ifb   \vrdcblokr
            b      1f+12-\b(\br)
            .align 4
1:          .hword 0,12,0,0,0,0
            sth    \devr,1b-\b(\br)
            la     \devr,1b-\b(\br)
            .ifb   \am
               diag   \devr,0,0x210
            .else
               sam31
               diag   \devr,0,0x210
               sam\am
            .endif
            .ifnb   \notexist
               bc     3,\notexist-\b(\br)
            .endif
            l      \devr,1b+8-\b(\br)
         .else
            sth    \devr,0(\vrdcblokr)
            .ifb   \am
               diag   \vrdcblokr,0,0x210
            .else
               sam31
               diag   \devr,0,0x210
               sam\am
            .endif
            .ifnb   \notexist
               bc     3,\notexist-\b(\br)
            .endif
            l      \devr,8(\vrdcblokr)
         .endif
         .endm
         
 # Issue Hercules 't-' command

         .macro traceoff rx:req ry:req br=15 b=0b
         command rx=\rx,ry=\ry,ebcdic="\xA3\x60",code=.Ldw_toffail,br=\br,b=\b
         .endm

 # Issue Hercules 't+' command

         .macro traceon rx ry br=15 b=0b
         command rx=\rx,ry=\ry,ebcdic="\xA3\x4E",code=.Ldw_tonfail,br=\br,b=\b
         .endm
         

.endif # .ifndef .Lcp
