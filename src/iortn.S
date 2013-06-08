.ifndef .Liortn_S
.Liortn_S = 1
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

 # This module provides macros to assist with ESA/390 or z/Architecture 
 # subchannel-based I/O operations.
 #
 #  Macro        Description
 #  iosch      Performs a subchannel-based I/O operation
 #  peof       Checks if physical end-of-file encountered

 # Module Dependencies
           .include "io.S"        # For I/O structures and assigned storage locations
           .include "interrupt.S" # For in-line interrupt wait macros

 # iosch - Perform a subchannel-based I/O operation.
 #
 # A START SUBCHANNEL instruction is issued to the device SSID identified in general
 # register R1 with the ORB identified by the orb parameter.  Any condition code 
 # other than 0 (start function initiated), results  in control passing to the error 
 # parameter location.  The ORB must contain the address of the CCW's to be executed
 # by the device before the iosch macro is issued.
 #
 # Following successful completion of the I/O operation, control continues
 # following the macro.  If either the channel error (cerr parameter) or device
 # error (derr parameter) flags are recognized following the I/O, control is passed 
 # to the error parameter's location.  Waiting will continue until the subchannel
 # provides primary status.  If channel end and device end are not present by the
 # time primary status is provided, an error condition is recognized.
 #
 # For a program detecting physical end-of-file, the peof370 macro should be issued 
 # following the iosch macro and the status used to detect the end-of-file condition
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
 # This macro issues initiates subchannel input/output operations at the device.
 #
 # Following successful completion of the I/O operation, control returns to the
 # issuer following the iosch macro.
 #
 # WARNING: Unsolicited interruptions from other devices can be lost.  Unsolicited
 # interruptions from the targeted device between I/O operations will be treated as 
 # an error condition of the START SUBCHANNEL instruction.
 #
 # Macro Parameters:
 #   orb      Lable of Operation Request Block (ORB) (required)
 #   irb      Lable of Interrupt Response Block (IRB) (required)
 #   error    Lable of where to pass control on an error (required)
 #   iostatus Lable of a fullword into which I/O status is accumulated (required)
 #   cerr     Channel status mask used to detect channel errors (optional)
 #   derr     Device status mask used to detect end of input (optional)
 #   er       Register pointing to the instruction following the point of error 
 #            (defaults to 15)
 #   br       Base register (defaults to 13)
 #   b        Lable of the current base (defaults to 0b)
 #
 # Required Register Usage:
 #   R1     Contains the SSID of the device intended to execute the I/O operation.

            .macro iosch orb:req irb:req iostatus:req error:req cerr derr sense er=15 br=13 b=0b
            mvc      \iostatus-\b(4,\br),5f-4-\b(\br)  # Clear accumulated status
2:          ssch     \orb-\b(\br)             # Start Subchannel
            bc       0b1000,3f-\b(\br)        # If start function initiated, wait
            bas      \er,\error-\b(\br)       # ..otherwise, an error condition
3:          
            iowait   s=0,br=\br,b=\b          # Wait for the I/O interrupt
            cl       1,.LIO_ssid(0)           # Is this my device?
            bne      3b-\b(\br)               # ..No, keep waiting
            tsch     \irb-\b(\br)             # Test Subchannel
            bc       0b0100,3b-\b(\br)        # CC1 (status not pending) ignore status
            bc       0b1000,4f-\b(\br)        # CC0 (status was pending) check it
            bas      \er,\error-\b(\br)       # CC3 (not operational) an error then
4:          # Combine status
            oc       \iostatus-\b(2,\br),\irb+.LSCSW_ds-\b(\br) # add dev,chn status
            oc       \iostatus+2-\b(1,\br),\irb+.LSCSW_sc-\b(\br)  # add SC info
            tm       \iostatus+2-\b(\br),.LSCSW_primary  # Primary status?
            bno      3b-\b(\br)               # ..No, wait for primary status
    .ifnb \cerr
            tm       \iostatus+1-\b(\br),\cerr  # Any channel checks?
            bz       .+8-\b(\br)              # ..No, check how I/O went
            bas      \er,\error-\b(\br)       # ..DIE: Channel program error
    .endif # .ifnb \cerr
    .ifnb \derr
            tm       \iostatus-\b(\br),\derr  # Any device errors?
            bz       .+8-\b(\br)              # ..No, check how I/O went
            bas      \er,\error-\b(\br)       # ..DIE: device error
    .endif # .ifnb \derr
    .ifnb \sense
            tm       \iostatus-\b(\br),0x02   # If a unit check
            bo       \sense-\b(\br)           # Go process the sense data
    .endif # .ifnb \sense
            tm       \irb+8-\b(\br),0x0C      # Channel/Device end?
            bo       5f-\b(\br)               # ..Yes, I/O operation done
            bas      \er,\error-\b(\br)       # Primary status, but no CE,DE, error!
            .long    0                        # Used to clear accumulated status
5:
            .endm

 # peof - Macro to test physical end-of-file condition encountered
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

           .macro   peof eof:req iostatus:req status=0x01 br=13 b=0b
           tm       \iostatus-\b(\br),\status  # Did we hit end-of-file?
           bo       \eof-\b(\br)               # ..Yes, pass control
           .endm

.endif # .ifndef .Liortn_S
