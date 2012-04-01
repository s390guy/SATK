.ifndef .LHAL_S
.LHAL_S = 1
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

 # This module brings into the assembly all of the user exposed structures.  It is
 # required by any program that will use the abstraction layer or that will include
 # the abstraction layer.

 # Include the following public read-only structures:
 #  Structure   Source      Description
 #    IEIB      IEIB.S    IPL Environment Information Block
 #    IH        IHCB.S    32-bit Architecture CPU state save area
 #    IHG       IHCB.S    64-bit Architecture CPU state save area
 #
 # Include the following abstraction provider public macros:
 #   Macro      Source      Description
 #    hal       IEIB.S    Defines the architectures and platforms supported by the 
 #                        Hardware Abstraction Layer
 #    halfeat   IEIB.S    Specifies the features of the HAL to be used
 #    probe     IEIB.S    Detect the current running architecture
 #    setarch   IEIB.S    Issue a hardware architecture change
 #
 # Include the following abstraction user public macros:
 #   Macro      Source      Description 
 #    asb       ASB.S     Generate the 32-bit ASB structure based upon features
 #    asbg      ASB.S     Generate the 64-bit ASB structure based upon features

 #  +--------------------------+
 #  |  .text subsection usage  |
 #  +--------------------------+

 #  0   - The IPL ELF itself
 #  1   - 32-bit self-relocation information independent of the ELF
 #  2   - 64-bit self-relocation information independent of the ELF
 #  3   - The s370bc Architecture Support Block
 #  4   - The s370   Architecture Support Block
 #  5   - The s390   Architecture Support Block
 #  6   - The s390x  Architecture Support Block
 #  7   - 32-bit Embedded driver list
 #  8   - 64-bit Embedded driver list

 #  +----------------------+
 #  |  Real storage Usage  |
 #  +----------------------+
 #
 #   000000-0001FF  - reserved for platform assigned storage locations
 #   000200-00024F  - reserved for IPL ELF ABI usage
 #   000250-0005FF  - Hardware Abstraction Layer structures
 #   000250-0002BF       Reserved for IEIB - public structure
 #   0002C0-0003FF       Reserved for IHCB - private structure
 #   000400-0005FF       Reserved for initial program save area

 # +-------------------+
 # |  HAL Error Codes  |
 # +-------------------+

 #    Code   Module       Description
 #   0x0001  hal.S        Unsupported I/O architecture encountered
 #   0x0002  hal.S        DIAGNOSE X'08' error return
 #   0x0003  hal.S        STORE SYSTEM INFORMATION failure
 #   0x0004  hal.S        SERVICE CALL failure
 #   0x0005  hal.S        SERVICE CALL failed to return data
 #   0x0006  ioal.S       IDAW2 area required, but not provided (z/Architecture)
 #   0x0007  ioal.S       IDAW2 area not addressable by CCW1    (z/Architecture)
 #   0x0008  ioal.S       Unsupported I/O Abstraction Layer function
 #   0x0009  hal.S        Unsupported architecture initialization attempted
 #   0x000A  ioal.S       Abstract CCW has both IDA and MIDA flags set
 #   0x000B  ioal.S       Abstract CCW 31-bit address will not convert to 24-bit
 #   0x000C  ioal.S       Required interrupt abstractions not initialized
 #   0x000D  ihal.S       Interrupt class ID low-order two bits not zero
 #   0x000E  ihal.S       Interrupt class ID not within valid range (0<=id<=20)
 #   0x000F  ihal.S       IH CLASS function address zero
 #   0x0010  ihal.S       Unexpected interrupt class during IH WAIT absractions
 #   0x0011  ihal.S       IH WAIT interrupt list count negative or zero
 #   0x0012  ioallo.S     Exhausted IDAW's provided by program

 # +------------------------------------+
 # |  Device Type and Driver ID Values  |
 # +------------------------------------+

 #                   Hex   ID     Device
.Lioal_drvr = 0    # 0x00   0   Unknown device or common driver functionality
.Lioal_fba  = 4    # 0x04   1   Fixed-Block Architecture DASD
.Lioal_ckd  = 8    # 0x08   2   (Extended) Count-Key-Data DASD
.Lioal_tape = 12   # 0x0C   3   Tape drive device
.Lioal_rdr  = 16   # 0x10   4   Card reader device
.Lioal_cons = 20   # 0x14   5   Line-oriented console (1052, 3215)
.Lioal_pun  = 24   # 0x18   6   Card punch device
.Lioal_prt  = 28   # 0x1C   7   Line printer device
.Lioal_3270 = 32   # 0x20   8   3270 Display System device
.Lioal_tcu  = 36   # 0x24   9   Transmission Control Unit (270x)
.Lioal_ccu  = 40   # 0x28  10   Communications Control Unit (370x)
.Lioal_ctc  = 44   # 0x2C  11   Channel-to-channel Adapter
.Lioal_lcs  = 48   # 0x30  12   LAN Channel Station
.Lioal_osa  = 52   # 0x34  13   Open System Adapter
.Lioal_types= 14   #            Number of recognized device types

 # +------------------------+
 # |  Interruption Classes  |
 # +------------------------+

.LIH_mck_cls = 0x0000    # Machine-check maskable interruption class
.LIH_ext_cls = 0x0004    # External maskable interruption class
.LIH_io_cls  = 0x0008    # Input/Output maskable interruption class
.LIH_svc_cls = 0x000C    # Suprvisor Call non-maskable interruption class
.LIH_rst_cls = 0x0010    # Restart non-maskable interruption class
.LIH_pgm_cls = 0x0014    # Program non-maskable interruption class

 # +-----------------------------------------------------+
 # |  Interrupt Handler Save Area Save/Restore Controls  |
 # +-----------------------------------------------------+

 # The abstraction layer preserves only the PSW and general registers.  It is the 
 # programs responsibility to preserve additional state.  The following flags are
 # provided for use by the program for this purpose, but it is the choice of the
 # program how it manages CPU state preservation.

.LIHSR_CR  = 0x80   # Save/Restore Control registers
.LIHSR_AR  = 0x40   # Save/Restore Accress registers
.LIHSR_AFP = 0x04   # Save/Restore additional Floating Point registers
.LIHSR_FPC = 0x02   # Save/Restore Floating Point Control register
.LIHSR_FP  = 0x01   # Save/Restore basic Floating Point Control registers
.LIHSR_L1  = 0x81   # Valid controls for Level 1
.LIHSR_L2  = 0xC7   # Valid controls for Level 2
.LIHSR_L3  = 0xC7   # Valid controls for Level 3

 # Valid controls for specific architecture
.LIHSR_S370bc = .LIHSR_FP
.LIHSR_S370   = .LIHSR_FP|.LIHSR_CR
.LIHSR_S370XA = .LIHSR_FP|.LIHSR_CR
.LIHSR_ESA370 = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR
.LIHSR_ESA390 = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR|.LIHSR_AFP|.LIHSR_FPC
.LIHSR_zarch  = .LIHSR_FP|.LIHSR_CR|.LIHSR_AR|.LIHSR_AFP|.LIHSR_FPC

             .include "IEIB.S"
             .include "IHCB.S"

.endif # .ifndef .LHAL_S scope
