.ifndef .LOBJ_S
.LOBJ_S = 1
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

 # This module provides structure definitions for object module card image records.
 # Refer for details to IBM publication "SA22-7644-09, MVS Program Management: 
 # Advanced Facilities", Appendix A, Object module input conventions and record 
 # formats, pages 189-194.

        .include "struct.S"      # Structure definition macros

 # Object record format:

        struct .LOBJ             # Columns:  Description
        slong  .LOBJ_type        # 1-4: Record type:
.LOBJ_sym = 0x02E2E8D4           #          SYM record
.LOBJ_esd = 0x02C5E2C4           #          ESD record
.LOBJ_txt = 0x02E3E7E3           #          TXT record
.LOBJ_rld = 0x02D9D3C4           #          RLD record
.LOBJ_end = 0x02C5D5C4           #          END record
.LOBJ_id  = .LOBJ_type+2         # 3:   Single character ID
.LOBJ_sym_id = 0xE8              #          SYM record (EBCDIC 'Y')
.LOBJ_esd_id = 0xE2              #          ESD record (EBCDIC 'S')
.LOBJ_txt_id = 0xE7              #          TXT record (EBCDIC 'X')
.LOBJ_rld_id = 0xD3              #          RLD record (EBCDIC 'L')
.LOBJ_end_id = 0xD5              #          END record (EBCDIC 'N')
                                 #                       SYM  ESD  TXT  RLD  END
        sbyte  .LOJB_resv1       # 5:     reserved        B    B    B    B    B
        sbytes .LOBJ_addr,3      # 6-8:   address         B    B   yes   B   y(1)/B(2)
        sbytes .LOBJ_resv2,2     # 9,10:  reserved        B    B    B    B    B
        shword .LOBJ_dlen        # 11,12: data length    yes  yes  yes  yes   B
        sbytes .LOBJ_resv3,2     # 13,14: reserved        B    B    B    B    B
        shword .LOBJ_esdid       # 15,16: ESD ID          B   y/B  yes   B   y/B
        shere  .LOBJ_data        # 17-72: 56 data bytes  yes  yes  yes  yes  yes

      # END record use of data area                    END record Type  1     2
        sbytes .LOBJ_END_symbol,8  # 17-24: entry symbol                B    yes
        sbytes .LOBJ_END_resv1,4   # 25-28: reserved                    B     B
        slong  .LOBJ_END_SD_len    # 29-32: Length of SD w/o a length  yes   yes
        sbyte  .LOBJ_END_IDR_flag  # 33:    IDR Flag EBCDIC '1','2'    y/B   y/B
        sbytes .LOBJ_END_IDR1,19   # 34-52: IDR data (flag='1'or '2')  y/B   y/B
        sbytes .LOBJ_END_IDR2,19   # 53-71: IDR data (flag='2')        y/B   y/B
        sbyte  .LOBJ_END_resv2     # 72:    reserved                    B     B

      # Unused area                                      SYM  ESD  TXT  RLD  END
        sbytes .LOBJ_unused,8    # 73-80: unused         any  any  any  any  any
        shere  .LOBJ_len         # Length of an Object record

 # External Symbol Dictionary

        struct .LESD            # Position              SD  PC  LD  PR  CM  ER  WX
        sbytes .LESD_symbol,8   # 1-8:    Symbol        yes  B  yes yes y/B yes yes
        sbyte  .LESD_type       # 9:      ESD item type
.LESD_CM = 0x05  # fullword aligned Common
.LESD_CM8= 0x0F  # quad-aligned Common
.LESD_ER = 0x02  # External Reference
.LESD_LD = 0x01  # Label Definition
.LESD_PC = 0x04  # fullword aligned Private Code
.LESD_PC8= 0x0E  # quad-aligned Private Code
.LESD_PR = 0x06  # Pseudo Register
.LESD_SD = 0x00  # fullword aligned Section Definition
.LESD_SD8= 0x0D  # quad-aligned Section Definition
.LESD_WX = 0x0A  # Weak External Reference
        sbytes .LESD_addr,3      # 10-12: Address       yes yes yes B   B   B   B
        sbyte  .LESD_attr        # 13:    Attributes    yes yes B   yes B   B   B
   # PR Attributes
.LESD_PR_align8 = 0x07
.LESD_PR_align4 = 0x03
.LESD_PR_align2 = 0x01
.LESD_PR_align1 = 0x00
   # SD, PC Attributes
.LESD_SD_rmode64 = 0x20
.LESD_SD_rmode31 = 0x04
.LESD_SD_amodemsk= 0x03
.LESD_SD_amodeany= 0x03
.LESD_SD_amode64 = 0x10
.LESD_SD_amode31 = 0x02
.LESD_SD_amode24 = 0x01
.LESD_SD_readonly= 0x80
        sbytes .LESD_length,3    # 14-16: Item length   yes yes B   yes yes B   B
        shere  .LESD_len         # Length of an ESD item

 # Relocation Dictionary

        # The Relocation Dictionary defines locations of address constants that
        # must be relocated if the section is bound to a different address Two key pointers are used in the relocation dictionary: 
        #   Relocation (R) pointer - the symbol to which the address constant 
        #                            refers.  The relocation pointer is an ESD ID.
        #                            It will refer to either a SD, PC, EX or WX item
        #   Position (P) pointer   - the position within a control section where 
        #                            the address constant resides.  The position
        #                            pointer is composed of two values, the ESD ID
        #                            in which the address constant resides, a SD
        #                            or PC item, and a address within the section.
        #                            The address constant is added or subtracted
        #                            from the R-pointer's assigned address as
        #                            indicated by the flag byte.

        struct .LRLD
        shword .LRLD_r_esd   # Relocation pointer.  If zero, this item defines the 
                             # cumulative length of the pseudo register located at 
                             # the P-ptr.
        shword .LRLD_p_esd   # Position pointer ESD ID.
        sbyte  .LRLD_flag    # Defines attributes of the address constsant
 # Relative immediate usage
.LRLD_relmsk= 0x7C   # Mask to isolate relative addressing type
.LRLD_rel2  = 0x70   # This RLD item refers to a two-byte relative immediate item
.LRLD_rel4  = 0x78   # This RLD item refers to a four-bite relative immediate item
.LRLD_incr4 = 0x40   # If 1, add 4 to the LL bits
 # Address constant usage
.LRLD_typmsk= 0x30   # Mask to isolate address constant type
.LRLD_Acon  = 0x00   # A-con address constant (locally defined symbol)
.LRLD_Vcon  = 0x10   # V-con address constant (externally defined symbol)
.LRLD_Qcon  = 0x20   # Q-con address constant (a DSECT or external dummy DXD)
.LRLD_CXD   = 0x30   # Cumulative length of an external dummy section
.LRLD_LL    = 0x0C   # Address constant length minus 1 (0-3 for 1-4 bytes)
.LRLD_sign  = 0x02   # relocation constant is subtracted, otherwise added
.LRLD_same  = 0x01   # P-esd and R-esd omitted from next RLD item because they are 
                     # the same as this RLD item
        sbytes .LRLD_p_addr  # Assigned address within the P-esd of the address 
                             # constant
        shere  .LRLD_len     # Length of a full RLD item
.LRLD_short = .LRLD_len-4    # Length of a short RLD item (without P-esd and R-esd)

 # IDR Data Item

        struct .LIDR                 # All fields contain EBCDIC data
        sbytes .LIDR_translator,10   # Translator, left justified padded with blanks
        sbytes .LIDR_version,2       # Version, 01-99
        sbytes .LIDR_release,2       # Release, 01-99
        sbytes .LIDR_year,2          # Year of compilation or assembly
                                     # 65-99 represent 19XX dates
                                     # 00-64 represent 20XX dates
        sbytes .LIDR_julday,3        # 001-366 is the Julian date of the module
        shere  .LIDR_len             # Length of an IDR item

.endif # .ifndef .LOBJ_S scope
