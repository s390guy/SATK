.ifndef .Liortn370_S
.Liortn370_S=1
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

 # This module provides macros to assist with System/370 channel-based I/O operations.
 #
 #  Macro        Description
 #  iochan     Performs a S/370 Channel-based I/O operation
 #  peof370    Check if physical end-of-file encountered

 # Module Dependencies:
           .include "interrupt.S"  # Provides in-line I/O wait macro
           .include "io.S"         # For S/370 I/O assigned storage locations

 # iochan - Perform a channel-based I/O operation.
 #
 # A START IO instruction is issued to the device identified by the devr parameter.
 # Any condition code other than 0 (I/O operation initiated and channel proceding
 # with its execution), results in control passing to the error parameter location.
 #
 # Following successful completion of the I/O operation, control continues
 # following the macro.  If either the channel error (cerr parameter) or device
 # error (derr parameter) flags are recognized following the I/O, control is passed 
 # to the error parameter's location.  Waiting will continue until device end and 
 # channel end have been recognized.  
 #
 # For a program detecting physical end-of-file, the peof370 macro should be issued 
 # following the iochan macro and the status used to detect the end-of-file condition
 # should not be included in the derr parameter's mask.
 #
 # Status checks follow the following sequence:
 #
 #  - cerr, if present and an error detected, pass control to error parameter 
 #          location
 #  - derr, if present and an error detected, pass control to error parameter 
 #          location
 #  - sense, if present and UNIT CHECK present, pass control to sense parameter 
 #          location
 #  - if channel and device end present, pass control to location following the 
 #          iochan macro (always checked)
 #  - otherwise, wait for more status
 #
 # Macro Parameters:
 #   devr     Register containing the device address in low order 16 bits (required)
 #   ccws     Lable of a pointer to the CCW program to be executed (required)
 #   iostatus A halfword provided by the issuer for accumulating I/O status 
 #            (required)
 #   error    Lable of where to pass control on an error (required)
 #   cerr     Channel status mask used to detect channel errors (optional)
 #   derr     Device status mask used to detect device errors (optional)
 #   sense    Passes control to this locations on unit check status (optional)
 #   er       Register pointing to point of error+4 (defaults to 15)
 #   br       Base register (defaults to 12)
 #   b        Lable of the current base (defaults to 0b)
 #
 # derr parameter should not include CHANNEL END, DEVICE END, and if seprately
 # checked by use of the sense parameter, UNIT CHECK.
 #
 # Basic vs. extended control mode is detected based upon the psw_arch macro setting.
 # This macro has a dependency upon the src/interrupt.S module

            .macro iochan devr:req ccws:req iostatus:req error:req cerr derr sense er=15 br=13 b=0b
            mvc      .LIO_caw(4,0),\ccws-\b(\br)      # Identify CCW commands for I/O
            mvc      \iostatus-\b(2,\br),4f-2-\b(\br) # Clear accumulated status
2:          .insn    s,0x9C000000,0(\devr)     # Start I/O
            bc       0b1000,3f-\b(\br)         # If I/O started, wait for interrupt
            bas      \er,\error-\b(\br)        # ..otherwise, an error condition
3:          iowait   br=\br                    # Wait for I/O interrupt
    .ifeq .L__psw_arch             # Basic-Control Mode
            ch       \devr,.LPSW_oldio+2(0)    # Is this my device in the old PSW?
    .else  # .ifeq .L__psw_arch    # Extended-Control Mode
            ch       \devr,.LIO_dev(0)         # Is this my device in I/O int. area?
    .endif 
            bne      3b-\b(\br)                # ..No, wait some more
            oc       \iostatus-\b(2,\br),.LIO_csw_ds(0)  # Accumulate status
    .ifnb \cerr
            tm       \iostatus+1-\b(\br),\cerr # Any channel checks?
            bz       .+8-\b(\br)               # ..No, check how I/O went
            bas      \er,\error-\b(\br)        # ..Yes, pass control to error handler
    .endif # .ifnb \cerr
    .ifnb \derr
            tm       \iostatus-\b(\br),\derr   # Any device errors?
            bz       .+8-\b(\br)               # ..No, check if I/O is done
            bas      \er,\error-\b(\br)        # ..Yes, pass control to error handler
    .endif # ifnb \derr
    .ifnb \sense
            tm       \iostatus-\b(\br),0x02    # If a unit check
            bo       \sense-\b(\br)            # Go process the sense data
    .endif # .ifnb \sense
            tm       \iostatus-\b(\br),0x0C    # Channel/Device end?
            bo       4f-\b(\br)                # ..Yes, I/O is done!
            b        3b-\b(\br)                # ..No, wait for both to show up
            .hword   0                         # Clears accumulated status
4:
            .endm

 # peof370 - Macro to test physical end-of-file condition encountered
 #
 # Macro Parameters:
 #   eof      Lable to which control is passed on end of file (required)
 #   iostatus Lable of the halfword containing accumulated I/O status.  Typically 
 #            this is the same location supplied to the iochan macro's iostatus 
 #            parameter. (required)
 #   status   Device status condition used to detect physical end-of-file 
 #            (defaults to 0x01, unit exception)
 #   br       Base register (defaults to 13)
 #   b        Lable of the current base, defaults to 0b
 #
 # Note for use by SATK boot loaders:
 #
 # For 'P (physical end-of-file implies end of booted program), the iochan macro
 # should be followed by the peof370 macro. peof370 should pass control to the 
 # location that enters the booted program.
 #
 # For 'H (directed block header flag indicates the end of the booted program), 
 # peof370 should not follow the iochan macro.  Rather, the boot loader should 
 # examine the directed block header before calling issuing iochan to read the 
 # next directed block.

           .macro   peof370 eof:req iostatus:req status=0x01 br=13 b=0b
           tm       \iostatus-\b(\br),\status  # Did we hit end-of-file?
           bo       \eof-\b(\br)               # ..Yes, pass control
           .endm

.endif # .ifndef .Liortn370_S
