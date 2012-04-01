.ifndef .Ltracef_S
.Ltracef_S = 1
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
 #    ABI.S    - for ABI support
 #    dwait.S  - for disabled wait code
 #
 # These routines turn on or off instruction tracing
 #    traceon  - Turns instruction tracing on
 #    traceoff - Turns instruction tracing off
 #
 # Register Usage:
 #   Input:
 #          none
 #   Output:
 #          Disabled wait state if function fails
 #
 #   Processing:
 #          %r8  = Hercules command to turn on or off instruction tracing
 #          %r10  = Hercules command length

 # Issue Hercules command to start instruction tracing

         .include "programf.S"  # Include wait state codes if needed

         abi_func .Ltraceon
 
.Ltrc_tplus: .byte 0xA3,0x4E  # 't+' in EBCDIC
.Ltrc_plus_len = .-.Ltrc_tplus

         abi_push

         la     8,.Ltrc_tplus-0b(13)   # DIAGNOSE X'8' - Rx  (command address)
         la     10,.Ltrc_plus_len      # DIAGNOSE X'8' - Ry  (command length)
         diag   8,10,0x8               # Turn on instruction tracing
         bc     7,.Ltrc_failon-0b(13)  # DIAGNOSE failed
         ltr    10,10                  # Other error?
         bc     7,.Ltrc_failon-0b(13)  # DIAGNOSE failed

         abi_ret

.Ltrc_failon:
         dwait  code=0xF002,program=0

 # Issue Hercules command to stop instruction tracing

         abi_func  .Ltraceoff

.Ltrc_tminus: .byte 0xA3,0x60  # 't-' in EBCDIC
.Ltrc_minus_len = .-.Ltrc_tminus

         abi_push

         la     8,.Ltrc_tminus-0b(13)  # DIAGNOSE X'8' - Rx  (command address)
         la     10,.Ltrc_minus_len     # DIAGNOSE X'8' - Ry  (command length)
         diag   8,10,0x8               # Turn off instruction tracing
         bc     7,.Ltrc_failoff-0b(13) # DIAGNOSE failed
         ltr    10,10                  # Other error?
         bc     7,.Ltrc_failoff-0b(13) # DIAGNOSE failed

         abi_ret

.Ltrc_failoff:
         dwait  code=0xF003,program=0

.endif # .ifndef .Ltracef_S scope
