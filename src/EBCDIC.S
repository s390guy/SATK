.ifndef .LEBCDIC_S
.LEBCDIC_S = 1
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

 # Based upon Hercules default CODEPAGE.C

 # Default ASCII/EBCDIC Translation Tables
 #   Maximum coorrespondence between various ASCII and EBCDIC code sets.
 #   Invalid ASCII or EBCDIC characters are left untranslated.

        .macro TR_A_E
 #              .0         .4         .8         .C
        .long 0x00010203,0x372D2E2F,0x1605250B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x3C3D3226,0x18191A27,0x221D351F  # 1.
        .long 0x405A7F7B,0x5B6C507D,0x4D5D5C4E,0x6B604B61  # 2.
        .long 0xF0F1F2F3,0xF4F5F6F7,0xF8F97A5E,0x4C7E6E6F  # 3.
        .long 0x7CC1C2C3,0xC4C5C6C7,0xC8C9D1D2,0xD3D4D5D6  # 4.
        .long 0xD7D8D9E2,0xE3E4E5E6,0xE7E8E9AD,0xE0BD5F6D  # 5.
        .long 0x79818283,0x84858687,0x88899192,0x93949596  # 6.
        .long 0x979899A2,0xA3A4A5A6,0xA7A8A9C0,0x6AD0A107  # 7.
        .long 0x68DC5142,0x43444748,0x52535457,0x56586367  # 8.
        .long 0x719C9ECB,0xCCCDDBDD,0xDFECFCB0,0xB1B2B3B4  # 9.
        .long 0x4555CEDE,0x49690406,0xAB08BAB8,0xB7AA8A8B  # A.
        .long 0x090A14BB,0x15B5B617,0x1BB91C1E,0xBC20BEBF  # B.
        .long 0x21232428,0x292A2B2C,0x3031CA33,0x343638CF  # C.
        .long 0x393A3B3E,0x41464A4F,0x5962DA64,0x65667072  # D.
        .long 0x73E17475,0x76777880,0x8C8D8EEB,0x8FEDEEEF  # E.
        .long 0x909A9B9D,0x9FA0ACAE,0xAFFDFEFB,0x3FEAFAFF  # F.
        .endm

        .macro TR_E_A
 #              .0         .4         .8         .C
        .long 0x00010203,0xA609A77F,0xA9B0B10B,0x0C0D0E0F  # 0.
        .long 0x10111213,0xB20A08B7,0x18191AB8,0xBA1DBB1F  # 1.
        .long 0xBDC01CC1,0xC20A171B,0xC3C4C5C6,0xC7050607  # 2.
        .long 0xC8C916CB,0xCC1ECD04,0xCED0D1D2,0x1415D3FC  # 3.
        .long 0x20D48384,0x85A0D586,0x87A4D62E,0x3C282BD7  # 4.
        .long 0x26828889,0x8AA18C8B,0x8DD82124,0x2A293B5E  # 5.
        .long 0x2D2FD98E,0xDBDCDD8F,0x80A57C2C,0x255F3E3F  # 6.
        .long 0xDE90DFE0,0xE2E3E4E5,0xE6603A23,0x40273D22  # 7.
        .long 0xE7616263,0x64656667,0x6869AEAF,0xE8E9EAEC  # 8.
        .long 0xF06A6B6C,0x6D6E6F70,0x7172F1F2,0x91F392F4  # 9.
        .long 0xF57E7374,0x75767778,0x797AADA8,0xF65BF7F8  # A.
        .long 0x9B9C9D9E,0x9FB5B6AC,0xABB9AAB3,0xBC5DBEBF  # B.
        .long 0x7B414243,0x44454647,0x4849CA93,0x9495A2CF  # C.
        .long 0x7D4A4B4C,0x4D4E4F50,0x5152DA96,0x8197A398  # D.
        .long 0x5CE15354,0x55565758,0x595AFDEB,0x99EDEEEF  # E.
        .long 0x30313233,0x34353637,0x3839FEFB,0x9AF9FAFF  # F.
        .endm

 # ASCII Code Page 437/EBCDIC Code Page 037 Translation Tables
 #  ASCII = Personal Computer (Code Page 437)
 #  EBCDIC = USA/Canada - Country Extended Code Page (Code Page 037)
 #  Invalid ASCII and EBCDIC codes are translated as "?"

        .macro TR_A437_E037
 #              .0         .4         .8         .C
        .long 0x00010203,0x372D2E2F,0x1605150B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x3C3D3226,0x18193F27,0x221D1E1F  # 1.
        .long 0x405A7F7B,0x5B6C507D,0x4D5D5C4E,0x6B604B61  # 2.
        .long 0xF0F1F2F3,0xF4F5F6F7,0xF8F97A5E,0x4C7E6E6F  # 3.
        .long 0x7CC1C2C3,0xC4C5C6C7,0xC8C9D1D2,0xD3D4D5D6  # 4.
        .long 0xD7D8D9E2,0xE3E4E5E6,0xE7E8E9BA,0xE0BBB06D  # 5.
        .long 0x79818283,0x84858687,0x88899192,0x93949596  # 6.
        .long 0x979899A2,0xA3A4A5A6,0xA7A8A9C0,0x4FD0A107  # 7.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # 8.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # 9.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # A.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # B.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # C.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # D.
        .long 0x3F593F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # E.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x903F3F3F,0x3FEA3FFF  # F.
        .endm

            .macro TR_E037_A437
 #              .0         .4         .8         .C
        .long 0x00010203,0x0709077F,0x0707070B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x070A0807,0x18190707,0x07070707  # 1.
        .long 0x07071C07,0x070A171B,0x07070707,0x07050607  # 2.
        .long 0x07071607,0x07070704,0x07070707,0x1415071A  # 3.
        .long 0x20FF8384,0x85A00786,0x87A49B2E,0x3C282B7C  # 4.
        .long 0x26828889,0x8AA18C07,0x8DE12124,0x2A293BAA  # 5.
        .long 0x2D2F078E,0x0707078F,0x80A5072C,0x255F3E3F  # 6.
        .long 0x07900707,0x07070707,0x70603A23,0x40273D22  # 7.
        .long 0x07616263,0x64656667,0x6869AEAF,0x070707F1  # 8.
        .long 0xF86A6B6C,0x6D6E6F70,0x7172A6A7,0x91079207  # 9.
        .long 0xE67E7374,0x75767778,0x797AADAB,0x07070707  # A.
        .long 0x5E9C9DFA,0x070707AC,0xAB075B5D,0x07070707  # B.
        .long 0x7B414243,0x44454647,0x48490793,0x9495A207  # C.
        .long 0x7D4A4B4C,0x4D4E4F50,0x51520796,0x8197A398  # D.
        .long 0x5CF65354,0x55565758,0x595AFD07,0x99070707  # E.
        .long 0x30313233,0x34353637,0x38390707,0x9A070707  # F.
        .endm


 # ASCII Code Page 437/EBCDIC Code Page 500 Translation Tables
 # ASCII = Personal Computer (Code Page 437)
 # EBCDIC = International #5 (Code Page 500)
 # Invalid ASCII and EBCDIC codes are translated as "?"

        .macro TR_A437_E500
 #              .0         .4         .8         .C
        .long 0x00010203,0x372D2E2F,0x1605150B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x3C3D3226,0x18193F27,0x221D1E1F  # 1.
        .long 0x404F7F7B,0x5B6C507D,0x4D5D5C4E,0x6B604B61  # 2.
        .long 0xF0F1F2F3,0xF4F5F6F7,0xF8F97A5E,0x4C7E6E6F  # 3.
        .long 0x7CC1C2C3,0xC4C5C6C7,0xC8C9D1D2,0xD3D4D5D6  # 4.
        .long 0xD7D8D9E2,0xE3E4E5E6,0xE7E8E94A,0xE05A5F6D  # 5.
        .long 0x79818283,0x84858687,0x88899192,0x93949596  # 6.
        .long 0x979899A2,0xA3A4A5A6,0xA7A8A9C0,0xBBD0A107  # 7.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # 8.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # 9.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # A.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # B.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # C.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # D.
        .long 0x3F593F3F,0x3F3F3F3F,0x3F3F3F3F,0x3F3F3F3F  # E.
        .long 0x3F3F3F3F,0x3F3F3F3F,0x903F3F3F,0x3FEA3FFF  # F.
        .endm

        .macro TR_E500_A437
 #              .0         .4         .8         .C
        .long 0x00010203,0x0709077F,0x0707070B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x070A0807,0x18190707,0x07070707  # 1.
        .long 0x07071C07,0x070A171B,0x07070707,0x07050607  # 2.
        .long 0x07071607,0x07070704,0x07070707,0x1415071A  # 3.
        .long 0x20FF8384,0x85A00786,0x87A45B2E,0x3C282B21  # 4.
        .long 0x26828889,0x8AA18C07,0x8DE15D24,0x2A293B5E  # 5.
        .long 0x2D2F078E,0x0707078F,0x80A5072C,0x255F3E3F  # 6.
        .long 0x07900707,0x07070707,0x70603A23,0x40273D22  # 7.
        .long 0x07616263,0x64656667,0x6869AEAF,0x070707F1  # 8.
        .long 0xF86A6B6C,0x6D6E6F70,0x7172A6A7,0x91079207  # 9.
        .long 0xE67E7374,0x75767778,0x797AADAB,0x07070707  # A.
        .long 0x9B9C9DFA,0x070707AC,0xAB07AA7C,0x07070707  # B.
        .long 0x7B414243,0x44454647,0x48490793,0x9495A207  # C.
        .long 0x7D4A4B4C,0x4D4E4F50,0x51520796,0x8197A398  # D.
        .long 0x5CF65354,0x55565758,0x595AFD07,0x99070707  # E.
        .long 0x30313233,0x34353637,0x38390707,0x9A070707  # F.
        .endm

 # ASCII Code Page 850/EBCDIC Code Page 273 Translation Tables
 #  ASCII = Personal Computer - Multilingual (Code Page 850)
 #  EBCDIC = Austria/Germany (Code Page 273)

        .macro TR_A850_E273
 #              .0         .4         .8         .C
        .long 0x00010203,0x372D2E2F,0x1605250B,0x0C0D0E0F  # 0.
        .long 0x10111213,0x3C3D3226,0x18193F27,0x1C1D1E1F  # 1.
        .long 0x404F7F7B,0x5B6C507D,0x4D5D5C4E,0x6B604B61  # 2.
        .long 0xF0F1F2F3,0xF4F5F6F7,0xF8F97A5E,0x4C7E6E6F  # 3.
        .long 0xB5C1C2C3,0xC4C5C6C7,0xC8C9D1D2,0xD3D4D5D6  # 4.
        .long 0xD7D8D9E2,0xE3E4E5E6,0xE7E8E963,0xECFC5F6D  # 5.
        .long 0x79818283,0x84858687,0x88899192,0x93949596  # 6.
        .long 0x979899A2,0xA3A4A5A6,0xA7A8A943,0xBBDC5907  # 7.
        .long 0x68D05142,0xC0444748,0x52535457,0x56584A67  # 8.
        .long 0x719C9ECB,0x6ACDDBDD,0xDFE05A70,0xB180BFFF  # 9.
        .long 0x4555CEDE,0x49699A9B,0xABAFBAB8,0xB7AA8A8B  # A.
        .long 0x2B2C0921,0x28656264,0xB4383134,0x33B0B224  # B.
        .long 0x22172906,0x202A4666,0x1A350839,0x36303A9F  # C.
        .long 0x8CAC7273,0x740A7576,0x77231514,0x04CC783B  # D.
        .long 0xEEA1EBED,0xCFEFA08E,0xAEFEFBFD,0x8DADBCBE  # E.
        .long 0xCA8F1BB9,0xB67CE19D,0x90BDB3DA,0xFAEA3E41  # F.
        .endm

        .macro TR_E273_A850
 #              .0         .4         .8         .C
        .long 0x00010203,0xDC09C37F,0xCAB2D50B,0x0C0D0E0F  # 0.
        .long 0x10111213,0xDBDA08C1,0x1819C8F2,0x1C1D1E1F  # 1.
        .long 0xC4B3C0D9,0xBF0A171B,0xB4C2C5B0,0xB1050607  # 2.
        .long 0xCDBA16BC,0xBBC9CC04,0xB9CBCEDF,0x1415FE1A  # 3.
        .long 0x20FF837B,0x85A0C686,0x87A48E2E,0x3C282B21  # 4.
        .long 0x26828889,0x8AA18C8B,0x8D7E9A24,0x2A293B5E  # 5.
        .long 0x2D2FB65B,0xB7B5C78F,0x80A5942C,0x255F3E3F  # 6.
        .long 0x9B90D2D3,0xD4D6D7D8,0xDE603A23,0xF5273D22  # 7.
        .long 0x9D616263,0x64656667,0x6869AEAF,0xD0ECE7F1  # 8.
        .long 0xF86A6B6C,0x6D6E6F70,0x7172A6A7,0x91F792CF  # 9.
        .long 0xE6E17374,0x75767778,0x797AADA8,0xD1EDE8A9  # A.
        .long 0xBD9CBEFA,0xB840F4AC,0xABF3AA7C,0xEEF9EF9E  # B.
        .long 0x84414243,0x44454647,0x4849F093,0xDD95A2E4  # C.
        .long 0x814A4B4C,0x4D4E4F50,0x5152FB96,0x7D97A398  # D.
        .long 0x99F65354,0x55565758,0x595AFDE2,0x5CE3E0E5  # E.
        .long 0x30313233,0x34353637,0x3839FCEA,0x5DEBE99F  # F.
        .endm

.endif
