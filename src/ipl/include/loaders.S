.ifndef .Lloaders_S
.Lloaders_S = 1
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

 # Embedded loader dependencies
        .include "psw.S"         # For PSW creation
        .include "interrupt.S"   # In-line interrupt handling macros

.ifndef __s370__
 # Set the IPL architecture mode
        psw_arch 390
        psw_amode 31
 # Include Subchannel I/O architecture loader
    .ifdef __FBA__
        .include "fbambed.S"
    .else  # 
        .ifdef __CKD__
            .include "ckdmbed.S"
        .else  # .ifdef __CKD__
            .ifdef __TAPE__
                .include "tapembed.S"
            .else  # .ifdef __TAPE__
                .ifdef __CARD__
                    .include "cardmbed.S"
                .else  # .ifdef __CARD__ 
                    .ifdef __CDROM__
                        .include "cdrommbed.S"
                    .else
                        .error "Recognized IPL device type symbol not defined"
                    .endif
                .endif # .ifdef __CARD__
            .endif # .ifdef __TAPE__
        .endif # .ifdef __CKD__
    .endif # .ifdef __FBA__

.else  # .ifndef __s370__  # Meaning IS S/370
    .ifdef __bcmode__            # S/370 BC-mode
        psw_arch bc
    .else  # .ifdef __bcmode__   # S/370 EC-mode
        psw_arch 370
    .endif 
        psw_amode 24
 # Include Channel I/O architecture loaders
    .ifdef __FBA__
        .include "fbam370.S"
    .else
        .error "Recognized IPL device type symbol not defined"
    .endif

.endif  # .ifndef __s370__

.endif  # .ifndef .Lloaders_S scope
