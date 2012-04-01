.ifndef .LIHCB_S
.LIHCB_S = 1
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

 # +-----------------------------------+
 # |  Interrupt Handler Control Block  |
 # +-----------------------------------+
 # Access: private

        struct  .LIHCB                 # +0 Start of the IHCB structure
        shalptr .LIHCB_ihf,.LIHCB_ihfg # +0 Active Interrupt Handler Function address
        socta   .LIHCB_sa              # +8 Temp sa for R7 and R8
        sbyte   .LIHCB_flags           # +24 Interrupt class related flags
        salign  8                      # +25 Make sure next IHCB starts on a dword
        shere   .LIHCB_len             # +32 Length of the IHCB

 # Interrupt Handler Control Block Flags:
.LIHCB_wait = 0x01    # In-line wait active (not valid for all classes)
.LIHCB_func = 0x02    # Function active

 # +--------------------------------------+
 # |  32-bit Interrupt Handler Save Area  |
 # +--------------------------------------+
 # Access: public

        struct .LIH
    # Old Program Status Word
        squad  .LIH_oPSW
    # Link to previous active save area
        slong  .LIH_link
    # General Regster Save Area
        shere  .LIH_GR
        slong  .LIH_R0
        slong  .LIH_R1
        slong  .LIH_R2
        slong  .LIH_R3
        slong  .LIH_R4
        slong  .LIH_R5
        slong  .LIH_R6
        slong  .LIH_R7
        slong  .LIH_R8
        slong  .LIH_R9
        slong  .LIH_R10
        slong  .LIH_R11
        slong  .LIH_R12
        slong  .LIH_R13
        slong  .LIH_R14
        slong  .LIH_R15
    # Control Register Save Area
        shere  .LIH_CR
        slong  .LIH_C0
        slong  .LIH_C1
        slong  .LIH_C2
        slong  .LIH_C3
        slong  .LIH_C4
        slong  .LIH_C5
        slong  .LIH_C6
        slong  .LIH_C7
        slong  .LIH_C8
        slong  .LIH_C9
        slong  .LIH_C10
        slong  .LIH_C11
        slong  .LIH_C12
        slong  .LIH_C13
        slong  .LIH_C14
        slong  .LIH_C15
    # Basic Floating Point Registers
        squad  .LIH_F0
        squad  .LIH_F2
        squad  .LIH_F4
        squad  .LIH_F6
    # Save/Restore Control Information
        shere  .LIH_SR
        sbyte  .LIH_SR_pgm     # Reserved for program use
        sbyte  .LIH_SR_state   # CPU state present in save area
        sbyte  .LIH_SR_class   # Interruption class using this save area
        sbyte  .LIH_SR_flags   # Save/restore controls (see HAL.S)
    # End of the Level 1 architecture save area
        shere  .LIH_s370_len
    # Floating Point Control Register (Level 2 architectures only)
        slong  .LIH_FPC
    # Additional Floating Point Control Registers (Level 2 architetures only)
        squad  .LIH_F1
        squad  .LIH_F3
        squad  .LIH_F5
        squad  .LIH_F7
        squad  .LIH_F8
        squad  .LIH_F9
        squad  .LIH_F10
        squad  .LIH_F11
        squad  .LIH_F12
        squad  .LIH_F13
        squad  .LIH_F14
        squad  .LIH_F15
    # Access Registers (Level 2 architectures only)
        shere  .LIH_AR
        slong  .LIH_A0
        slong  .LIH_A1
        slong  .LIH_A2
        slong  .LIH_A3
        slong  .LIH_A4
        slong  .LIH_A5
        slong  .LIH_A6
        slong  .LIH_A7
        slong  .LIH_A8
        slong  .LIH_A9
        slong  .LIH_A10
        slong  .LIH_A11
        slong  .LIH_A12
        slong  .LIH_A13
        slong  .LIH_A14
        slong  .LIH_A15
    # End of the Level 2 architecture save area
        shere  .LIH_len

 # +--------------------------------------+
 # |  32-bit Interrupt Information Block  |
 # +--------------------------------------+
 # Access: public

         struct .LIIB
         slong  .LIIB_class   # Interruption class
         slong  .LIIB_code    # Interruption code
         slong  .LIIB_id1     # Interruption identification information (part 1)
         slong  .LIIB_id2     # Interruption identification information (part 2)
         slong  .LIIB_pgm     # reserved for abstraction or program information
         shere  .LIIB_len

 # +--------------------------------------+
 # |  64-bit Interrupt Handler Save Area  |
 # +--------------------------------------+
 # Access: public

        struct .LIHG
    # Old Program Status Word
        socta  .LIHG_oPSW        # +0x0
    # Link to previous active save area
        slong  .LIHG_link        # +0x10
        salign 8
    # General Regster Save Area
        shere  .LIHG_GR          # +0x20
        squad  .LIHG_R0          # +0x20
        squad  .LIHG_R1          # +0x28
        squad  .LIHG_R2          # +0x30
        squad  .LIHG_R3          # +0x38
        squad  .LIHG_R4          # +0x40
        squad  .LIHG_R5          # +0x48
        squad  .LIHG_R6          # +0x50
        squad  .LIHG_R7          # +0x58
        squad  .LIHG_R8          # +0x60
        squad  .LIHG_R9          # +0x68
        squad  .LIHG_R10         # +0x70
        squad  .LIHG_R11         # +0x78
        squad  .LIHG_R12         # +0x80
        squad  .LIHG_R13         # +0x88
        squad  .LIHG_R14         # +0x90
        squad  .LIHG_R15         # +0x98
    # Control Register Save Area
        squad  .LIHG_C0          # +0xA0
        squad  .LIHG_C1          # +0xA8
        squad  .LIHG_C2          # +0xB0
        squad  .LIHG_C3          # +0xB8
        squad  .LIHG_C4          # +0xC0
        squad  .LIHG_C5          # +0xC8
        squad  .LIHG_C6          # +0xD0
        squad  .LIHG_C7          # +0xD8
        squad  .LIHG_C8          # +0xE0
        squad  .LIHG_C9          # +0xE8
        squad  .LIHG_C10         # +0xF0
        squad  .LIHG_C11         # +0xF8
        squad  .LIHG_C12         # +0x100
        squad  .LIHG_C13         # +0x108
        squad  .LIHG_C14         # +0x110
        squad  .LIHG_C15         # +0x118
    # Basic Floating Point Registers
        squad  .LIHG_F0          # +0x120
        squad  .LIHG_F2          # +0x128
        squad  .LIHG_F4          # +0x130
        squad  .LIHG_F6          # +0x138
    # Save Area Control Information
        shere  .LIHG_SR          # +0x140
        sbyte  .LIHG_SR_pgm      # +0x140  Reserved for program use
        sbyte  .LIHG_SR_state    # +0x141  CPU state present in save area
        sbyte  .LIHG_SR_class    # +0x142  Interruption class using this save area
        sbyte  .LIHG_SR_flags    # +0x143  Save/restore controls (see HAL.S)
    # Floating Point Control Register
        slong  .LIHG_FPC         # +0x144
    # Additional Floating Point Control Registers
        squad  .LIHG_F1          # +0x148
        squad  .LIHG_F3          # +0x150
        squad  .LIHG_F5          # +0x158
        squad  .LIHG_F7          # +0x160
        squad  .LIHG_F8          # +0x168
        squad  .LIHG_F9          # +0x170
        squad  .LIHG_F10         # +0x178
        squad  .LIHG_F11         # +0x180
        squad  .LIHG_F12         # +0x188
        squad  .LIHG_F13         # +0x190
        squad  .LIHG_F14         # +0x198
        squad  .LIHG_F15         # +0x1A0
    # Access Registers
        shere  .LIHG_AR          # +0x1A8
        slong  .LIHG_A0          # +0x1A8
        slong  .LIHG_A1          # +0x1AC
        slong  .LIHG_A2          # +0x1B0
        slong  .LIHG_A3          # +0x1B4
        slong  .LIHG_A4          # +0x1B8
        slong  .LIHG_A5          # +0x1BC
        slong  .LIHG_A6          # +0x1CC
        slong  .LIHG_A7          # +0x1D0
        slong  .LIHG_A8          # +0x1D4
        slong  .LIHG_A9          # +0x1D8
        slong  .LIHG_A10         # +0x1DC
        slong  .LIHG_A11         # +0x1E0
        slong  .LIHG_A12         # +0x1E4
        slong  .LIHG_A13         # +0x1E8
        slong  .LIHG_A14         # +0x1EC
        slong  .LIHG_A15         # +0x1C0
    # End of the Level 3 architecture save area
        shere  .LIHG_len         # +0x1C4

 # +--------------------------------------+
 # |  64-bit Interrupt Information Block  |
 # +--------------------------------------+
 # Access: public

         struct .LIIBG
         squad  .LIIBG_class  # Interruption class
         squad  .LIIBG_code   # Interruption code
         squad  .LIIBG_id1    # Interruption identification information (part 1)
         squad  .LIIBG_id2    # Interruption identification information (part 2)
         squad  .LIIBG_pgm    # reserved for abstraction or program information
         shere  .LIIBG_len

 # +----------------------------------------------+
 # |  Interrupt Handler Control Block Allocations |
 # +----------------------------------------------+
 # Access: private

        struct  .Lih_area,at=0x2C0      # Start of the IHCB's
        sbytes  .Lihext, .LIHCB_len     # 0x2C0  External abstract IH IHCB
        sbytes  .Lihio,  .LIHCB_len     # 0x2E0  I/O abstract IH IHCB
        sbytes  .Lihmck, .LIHCB_len     # 0x300  Machine Check abstract IH IHCB
        sbytes  .Lihpgm, .LIHCB_len     # 0x320  Program abstract IH IHCB
        sbytes  .Lihrst, .LIHCB_len     # 0x340  Restart IH handler IHCB
        sbytes  .Lihsvc, .LIHCB_len     # 0x360  SVC abstract IH IHCB
        salign  8                       # Get on doubleword boundary
        socta   .Lihnpgm_PSW            # 0x380  Enabled program interrupt handler PSW
        socta   .Lihexit_PSW            # 0x390  Interrupt Handler exit PSW
        shalptr .Lihsa,  .Lihsag        # 0x3A0  Active save area
        shalptr .Lihstk, .Lihstkg       # 0x3A8  Stack pointer starting location
        salign  256                     # 0x3B0  Align on new 512-byte boundary
        sbytes  .Lihsapgm,.LIHG_len     # 0x400  Initial save-area (always exists)
        shere   .Lihend                 # 0x5C4  End of the IHCB's
.Lih_area_len = .Lihend-.Lih_area       # Length of the IHCB area

.endif # .ifndef .LIHCB_S scope
