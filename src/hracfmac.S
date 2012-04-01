.ifndef .Lhracmac_S
.Lhracfmac_S = 1
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

 # This module provides configuration macros for hracfmod.S hracf function.  It is
 # optional.  If none of the configuration macros are used, by default, hracfmod.S
 # will enable all supported operations.  The purpose of these macros is to tailor
 # the size of the module, allowing support to be provided for (and taking up room
 # in the ELF) only for the operations required by the program.
 #
 # This module must be included before any reference to one of the hracf tailoring 
 # macros occurs in the program.  The tailoring macros must be used before the
 # hracfmod.S module is inlcuded into the program.  This implies the following 
 # sequence, as an example:
 #
 #       .include hracfmac.S
 #       hracf_oclose enable=yes
 #       .include hradfmod.S
 #
 # Each operation that may be enabled or disables has its own macro.  The macro
 # names all begin with 'hracf_' followed by the operation name.  Each macro
 # has one parameter, enable.  For some operations the enable defaults to 'yes' for
 # some, 'no'.  Only the init operation may not be disabled.  It is always required.
 # The following table identifies the operations that may be enabled or disabled
 # in the hracfmod.S module and the default setting for operation.
 #
 # Operation   Default (enable=)  Description
 #  binary       no               Ability to set a file to binary read/write mode
 #  close        yes              Ability to open a file
 #  commit       no               Ability to commit pending file writes
 #  dump         no               Ability to diaplay the FOCPB
 #  errno        no               Ability to interpret errno
 #  oclose       no               Ability to perform orphan close
 #  open         yes              Ability to open a file 
 #  read         yes              Ability to read from a file
 #  rename       no               Ability to seek to rename a file
 #  seek         no               Ability to seek to a file position
 #  text         no               Abliity to set a file to text read/write mode
 #  unlink       no               Ability to unklink a file
 #  write        yes              Ability to write to a file

 # This macro is used internally by the individual tailoring macros and sets the
 # above defaults automatically.

        .macro _hracf_init_sws
.ifndef .Lhracf_sw_all
.Lhracf_sw_all     = 1   # Enable all operations 
.Lhracf_close_sw   = 1   # Enable close
.Lhracf_commit_sw  = 0   # Disable commit
.Lhracf_dump_sw    = 0   # Disable dump
.Lhracf_errno_sw   = 0   # Disable errno
.Lhracf_init_sw    = 1   # Enable init (required, can not be disabled)
.Lhracf_oclose_sw  = 0   # Disable oclose
.Lhracf_open_sw    = 1   # Enable open
.Lhracf_read_sw    = 1   # Enable read
.Lhracf_rename_sw  = 0   # Disable rename
.Lhracf_seek_sw    = 0   # Disable seek
.Lhracf_setbin_sw  = 0   # Disable set binary mode
.Lhracf_settext_sw = 0   # Disable set text mode
.Lhracf_unlink_sw  = 0   # Disable unlink
.Lhracf_write_sw   = 1   # Enable write
.endif
        .endm

        .macro hracf_close enable=yes
        _hracf_init_sws
.ifc \enable,no
.Lhracf_close_sw = 0
.else
.Lhracf_close_sw = 1
.endif
        .endm

        .macro hracf_binary enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_setbin_sw = 1
.else
.Lhracf_setbin_sw = 0
.endif
        .endm

        .macro hracf_commit enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_commit_sw = 1
.else
.Lhracf_commit_sw = 0
.endif
        .endm

        .macro hracf_dump enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_dump_sw = 1
.else
.Lhracf_dump_sw = 0
.endif
        .endm

        .macro hracf_errno enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_errno_sw = 1
.else
.Lhracf_errno_sw = 0
.endif
        .endm

        .macro hracf_init enable=yes
.ifc \enable,no
        .warning "Can not disable hracfmod.S init operation, required"
.endif
        .endm

        .macro hracf_oclose enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_oclose_sw = 1
.else
.Lhracf_oclose_sw = 0
.endif
        .endm  

        .macro hracf_open enable=yes
        _hracf_init_sws
.ifc \enable,no
.Lhracf_open_sw = 0
.else
.Lhracf_open_sw = 1
.endif
        .endm

        .macro hracf_read enable=yes
        _hracf_init_sws
.ifc \enable,no
.Lhracf_read_sw = 0
.else
.Lhracf_read_sw = 1
.endif
        .endm

        .macro hracf_rename enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_rename_sw = 1
.else
.Lhracf_rename_sw = 0
.endif
        .endm 

        .macro hracf_seek enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_seek_sw = 1
.else
.Lhracf_seek_sw = 0
.endif
        .endm 

        .macro hracf_text enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_settext_sw = 1
.else
.Lhracf_settext_sw = 0
.endif
        .endm 

        .macro hracf_write enable=yes
        _hracf_init_sws
.ifc \enable,no
.Lhracf_write_sw = 0
.else
.Lhracf_write_sw = 1
.endif
        .endm

        .macro hracf_unlink enable=no
        _hracf_init_sws
.ifc \enable,yes
.Lhracf_unlink_sw = 1
.else
.Lhracf_unlink_sw = 0
.endif
        .endm     

.endif  # .ifndef .Lhracmac_S scope
