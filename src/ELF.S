.ifndef .LELF_S
.LELF_S    = 1
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

 # ELF.S module provides macros and structure definitions for those structure
 # independent of the ABI architecture.

 #   Macro       Description
 #  elfarch      Inspect an ELF and determine its architecture
 #  elfend       Locate the storage byte following the end of the ELF
 #  elfstart     Locate the start of the ELF in which the current code resides

 # Module dependencies:
         .include "struct.S"

 # elfarch - Inspect an ELF and determine its architecture.
 # Macro Parameters:
 #   archr    32-bit register containing the results of the inspection.  (required) 
 #            The following values may be set by the macro:
 #                0  ->  unrecognized architecture
 #                1  ->  s370, 32-bit ELF with s370 machine (9)
 #                2  ->  s390, 32-bit ELF with s390 machine (22)
 #                3  ->  s390x, 64-bit ELF with s390 machine (22)
 #   elfr     Register pointing to the start of the ELF in storage (required)
 #   br       Base register (defaults to 13)
 #   b        Current base (defaults to 0b)

         .macro elfarch archr:req elfr:req br=13 b=0b
         sr     \archr,\archr          # Set the result value to 'unrecognized'
         cli    .Leicls(\elfr),.Lei32  # 32-bit ELF?
         be     1f-\b(\br)             # ..Yes, determine which arch
         cli    .Leicls(\elfr),.Lei64  # 64-bit ELF?
         bne    3f-\b(\br)             # ..No, exit with 0 in archr
         clc    4f-\b(2,\br),.Lemach32(\elfr) # s390x?
         bne    3f-\b(\br)             # ..No, don't know what it is
         la     \archr,3               # ..Yes, set z/Architecture
         b      3f-\b(\br)             # Exit macro
4:       .hword .Lems390               # ESA/390 machine desired
         .hword .Lems370               # System/370 machine desired
1:       clc    4b-\b(2,\br),.Lemach32(\elfr)  # Want ESA/390?
         bne    2f-\b(\br)             # ..No, maybe System/370
         la     \archr,2               # Set ESA/390
         b      3f-\b(\br)             # Exit macro
2:       clc    4b+2-\b(2,\br),.Lemach32(\elfr) # Want System/370?
         bne    3f-\b(\br)             # ..No, handle unknown
         la     \archr,1               # Set System/370 Extended-control
3:
         .endm

 # Locates the end of the ELF + 1

 # elfend - Determine the address following the end of the ELF
 # Macro Parameters:
 #   endr    32-bit register containing the address following the ELF. (required)
 #   elfr    32-bit register containing the address of the ELF start. (required)
 #   br       Base register (defaults to 13)
 #   b        Current base (defaults to 0b)
 #
 # This macro depends upon the structure of an ELF executable created by the GNU
 # linker, ld.  See the description of the elfstart macro for details.

         .macro elfend endr elfr br=13 b=0b
         cli    .Leicls(\elfr),.Lei32   # 32-bit ELF?
         be     1f-\b(\br)              # ..Yes, calculate with 32-bit header
         lh     \endr,.Leshnum64(\elfr) # fetch the number of section hdrs.
         mh     \endr,.Leshent64(\elfr) # times the size of each header
         al     \endr,.Leshoff64+4(\elfr) # add the offset of sect hdrs
         alr    \endr,\elfr             # add start of ELF
         b      2f-\b(\br)              # \endr has the byte after the ELF
1:       lh     \endr,.Leshnum32(\elfr) # fetch the number of section hdrs.
         mh     \endr,.Leshent32(\elfr) # times the size of each header
         al     \endr,.Leshoff32(\elfr) # add the offset of sect hdrs
         alr    \endr,\elfr             # add the start of the ELF
2:
         .endm

 # elfstart - Locate the start of the ELF
 # Macro Parameters:
 #   elfr    32-bit register containing the starting address of the ELF in storage.
 #           (required).  The elfr register will contain the address of the ELF or
 #           zero if it failed to locate the start. 
 #   name    Assembler symbol representing the start of the program segment.
 #           (defaults to 'start')
 #
 # This macro makes certain assumptions about how the ELF is constructed that appear
 # to be true for the GBU linker, ld.  The structure appears to be as follows for
 # an executable:
 #
 #    ELF Ident - start of the ELF.
 #    ELF Header
 #    Program Segment Table
 #
 #    inserted space to place the first program segment in the correct position
 #    from the start of the page.
 #
 #    Program segments
 #    Section Table
 #    (end of the ELF)
 #
 # The ld linker assumes that the ELF Ident will be loaded on a 4096-byte page
 # boundary.  If the first program segment is not linked, allowing for alignment,
 # to the location immediately following the end of the Program Segment Table, the 
 # linker will insert space following the segment table that will place the segment
 # at the proper displacement from the start of the page.  This macro therefore
 # assumes the start of the ELF is at the start of the page in which the first
 # segment resides (.text or TEXT). 

         .macro elfstart elfr:req name=start br=13 b=0b
         l      \elfr,1f-\b(\br)      # Get the start of the program segment
         srl    \elfr,12              # Locate the start of the page
         sll    \elfr,12              # in which the segment resides
         clc    1f+4-\b(4,\br),0(\elfr)  # Did we actually locate the ELF start?
         be     1f+8-\b(\br)          # ..yes, Branch around values
         sr     \eflr,\elfr           # ..No, set start address to zero.
         b      1f+8-\b(\br)          # Now branch around the values
         .align 4
1:       .long  \name                 # Size of ELF headers
         .ascii "\x7FELF"             # the ELF magic
         .endm

 # The following macros assist in ELF relocation shared by both 32-bit and 64-bit
 # ELF formats.

         .macro st_quad64 reg itemr
         stg    \reg,0(\itemr)
         .endm

         .macro st_word32 reg itemr
         st     \reg,0(\itemr)
         .endm

         .macro st_half16 reg itemr
         sth    \reg,0(\itemr)
         .endm

         .macro st_low12 reg itemr wrkr
         sgr    \wrkr,\wrkr
         icm    \wrkr,0x2,0(\itemr)
         or     \reg,\wrkr
         sth    \reg,0(\itemr)
         .endm

         .macro st_byte8 reg itemr
         stc    \reg,0(\itemr)
         .endm

 # +------------------------+
 # |   ELF Identification   |
 # +------------------------+

         struct .Leident     # ELF ident area
         slong  .Leimag      # ELF Magic: 0x7F,0x45,0x4C, 0x46 ("\x7FELF")
         sbyte  .Leicls      # ELF class:
.Lei32   =      1            #   32-bit ELF
.Lei64   =      2            #   64-bit ELF
         sbyte  .Leidata     # ELF data order:
.Leiltl  =      1            #   Little-endian byte order
.Leibig  =      2            #   Big-endian byte order
         sbyte  .Leiver      # ELF Version
.Leicur  =      1            #   Only version 1 allowed
         sbyte  .Leiosabi    # OS ELF ABI Extensions
.Leiosno =      0            #   No OS ELF ABI extensions
         sbyte  .Leiabiver   # OS ABI Version
.Leiabino=      0            #   No OS ABI version specified
         sbytes .Leipad,size=7  # Ident padding
         shere  .Leident32      # Start of the 32-bit ELF ABI Header
         shere  .Leident64      # Start of the 64-bit ELF ABI Header
         shere  .Leident_len # Length of the ELF Ident area

 # +-----------------------+
 # |   32-bit ABI Header   |
 # +-----------------------+

         struct .Lehdr32     # 32-bit ABI Header
         shword .Letype32    # File type (see etype values below)
         shword .Lemach32    # File machine architecture (see emach values below)
         slong  .Lever32     # ELF File version (see ever values below)
         slong  .Lentry32    # ELF Entry point (normally zero implies none)
         slong  .Lephoff32   # Program header table offset from start of ELF
         slong  .Leshoff32   # Section header table offset from start of ELF
         slong  .Leflags32   # Machine specific flags
         shword .Leehsiz32   # ELF header size in bytes
         shword .Lephent32   # Program header table entry size in bytes
         shword .Lephnum32   # Number of program header table entries (0==none)
         shword .Leshent32   # Section header table entry size in bytes
         shword .Leshnum32   # Number of section header table entries (0==none)
         shword .Leshstr32   # Shared string table section header index (0==none)
         shere  .Lehdr32_len # Length of the 32-bit ABI Header

 # +-----------------------+
 # |   64-bit ABI Header   |
 # +-----------------------+

         struct .Lehdr64     # 64-bit ABI Header
         shword .Letype64    # File type (see etype values below)
         shword .Lemach64    # File machine architecture (see emach values below)
         slong  .Lever64     # ELF File version (see ever values below)
         squad  .Lentry64    # ELF Entry point (normally zero implies none)
         squad  .Lephoff64   # Program header table offset from start of ELF
         squad  .Leshoff64   # Section header table offset from start of ELF
         slong  .Leflags64   # Machine specific flags
         shword .Leehsiz64   # ELF header size in bytes
         shword .Lephent64   # Program header table entry size in bytes
         shword .Lephnum64   # Number of program header table entries (0==none)
         shword .Leshent64   # Section header table entry size in bytes
         shword .Leshnum64   # Number of section header table entries (0==none)
         shword .Leshstr64   # Shared string table section header index (0==none)

 # +--------------------------+
 # |   Common Header Values   |
 # +--------------------------+

 # etype values:
.Letnone      = 0            #   No file type
.Letrel       = 1            #   Relocatable file
.Letexec      = 2            #   Executable file
.Letdyn       = 3            #   Shared object file
.Letcore      = 4            #   Core file
.Letloos      = 0xFE00       #   Operating system-specific file low value
.Lethios      = 0xFEFF       #   Operating system-spefific file high value
.Letloproc    = 0xFF00       #   Processor-specific file low value
.Lethiproc    = 0xFFFF       #   Processor-specific file high value

 # enach values:
.Lems370      = 9            # System/370
.Lems390      = 22           # System/390

 # ever values:
.Levnone      = 0            # Invalid version
.Levcurrent   = 1            # Current version (only valid value)

 # +-------------------------------+
 # |   32-bit ABI Program Header   |
 # +-------------------------------+

         struct .Lephdr32    # 32-bit Program Header
         slong  .Lptype32    # Program segment type (see type values below)
         slong  .Lpoff32     # Program segment offset from ELF start
         slong  .Lpvaddr32   # Virtual address of program segment residency (real for SATK)
         slong  .Lppaddr32   # Physical address of program segment (not used)
         slong  .Lpsize32    # Size of program segment in the ELF file (may be zero)
         slong  .Lpmemsiz32  # Size of program segment in memory (may be >= psize32)
         slong  .Lpflags32   # Segment flags (see flags values below)
         slong  .Lpalign32   # Segment alignment (pvaddr overrides for SATK)
         shere  .Lephdr32_len # Length of the 32-bit Program Header

 # +-------------------------------+
 # |   64-bit ABI Program Header   |
 # +-------------------------------+

         struct .Lephdr64    # Program segment type (see type values below)
         slong  .Lpflags64   # Segment flags (see flags values below)
         squad  .Lpoff64     # Program segment offset from ELF start
         squad  .Lpvaddr64   # Virtual address of program segment residency (real for SATK)
         squad  .Lppaddr64   # Physical address of program segment (not used)
         squad  .Lpsize64    # Size of program segment in the ELF file (may be zero)
         squad  .Lpmemsiz64  # Size of program segment in memory (may be >= psize64)
         squad  .Lpalign64   # Segment alignment (pvaddr overrides for SATK)
         shere  .Lephdr64_len # Length of the 64-bit Program Header

 # +----------------------------------+
 # |   Common Program Header Values   |
 # +----------------------------------+

 # flags values:
.Lpfx         = 1            # Execute
.Lpfw         = 2            # Write
.Lpfr         = 4            # Read
.Lpfmaskos    = 0x0FF00000   # OS-specific flags
.Lpfmaskprc   = 0xF0000000   # Processor-specific flags

 # type values:
.Lptnull      = 0            # This entry is unused
.Lptload      = 1            # Load into memory using pvaddr, pmemsize and psize
.Lptdynamic   = 2            # Dynamic linking information
.Lptinterp    = 3            # Program Interpreter
.Lptnote      = 4            # Auxiliary Information
.Lptshlib     = 5            # Reserved, if present, non-ABI conforming
.Lptphdr      = 6            # Location of program header table itself
.Lpttls       = 7            # Thread-Local storage
.Lptloos      = 0x60000000   # Operating specific semantics low value
.Lpthios      = 0x6FFFFFFF   # Operating specific semantics high value
.Lptloproc    = 0x70000000   # Processor specific semantics low value
.Lpthiproc    = 0x7FFFFFFF   # Processor specific semantics high value

 # +-------------------------------+
 # |   32-bit ABI Section Header   |
 # +-------------------------------+

         struct .Leshdr32    # 32-bit ABI Section Header
         slong  .Lshname32   # Section name index in section header string table
         slong  .Lshtype32   # Section type (see type values below)
         slong  .Lshflags32  # Section flags (see flag value below)
         slong  .Lshaddr32   # Address of the section in memory
         slong  .Lshoff32    # Section offset from ELF start
         slong  .Lshsize32   # Size of the section in bytes
         slong  .Lshlink32   # Section link information (see link info values below)
         slong  .Lshinfo32   # Section information (see section info values below)
         slong  .Lshalign32  # Alignment as a power of two
         slong  .Lshentsz32  # Size of entries of fixed size in the section

 # +-------------------------------+
 # |   64-bit ABI Section Header   |
 # +-------------------------------+

         struct .Leshdr64    # 64-bit ABI Section Header
         slong  .Lshname64   # Section name index in section header string table
         slong  .Lshtype64   # Section type (see type values below)
         squad  .Lshflags64  # Section flags (see flag value below)
         squad  .Lshaddr64   # Address of the section in memory
         squad  .Lshoff64    # Section offset from ELF start
         squad  .Lshsize64   # Size of the section in bytes
         slong  .Lshlink64   # Section information (see section info values below)
         squad  .Lshalign64  # Alignment as a power of two
         squad  .Lshentsz64  # Size of entries of fixed size in the section

 # +---------------------------------+
 # |  Common Section Header Values   |
 # +---------------------------------+

 # flag values:
.Lshf_write   = 1            # Data that should be writable
.Lshf_alloc   = 2            # This section occupies memory
.Lshf_exec    = 4            # This section contains executable instructions
.Lshf_merge   = 0x10         # Elements of this section may be merged
.Lshf_str     = 0x20         # This section contains null terminated strings
.Lshf_info    = 0x40         # shinfo contains a section header index
.Lshf_order   = 0x80         # This section had special ordering requirements
.Lshf_nocon   = 0x100        # This section is non conforming
.Lshf_group   = 0x200        # This section is a member of a group
.Lshf_tls     = 0x400        # This section contains thread local storage
.Lshf_mskos   = 0x0FF00000   # These flags reserved for OS use
.Lshf_mskpr   = 0xF0000000   # These flags reserved for processor use

 # section header index values:
.Lshn_undef   = 0            # Undefined section
.Lshn_lores   = 0xFF00       # Lower bound of reserved indexes
.Lshn_lopr    = 0xFF00       # Low processor special section
.Lshn_hipr    = 0xFF1F       # High processor special section
.Lshn_loos    = 0xFF20       # Low OS special section
.Lshn_hios    = 0xFF3F       # High OS special section
.Lshn_abs     = 0xFFF1       # This section indicates absolute values
.Lshn_com     = 0xFFF2       # Common symbols defined in this section
.Lshn_xindx   = 0xFFFF       # Actual section header index found elsewhere
.Lshn_hires   = 0xFFFF       # High bound of reserved indexes

 # section type values:
.Lsht_null    = 0            # Null, inactive section
.Lsht_progbits= 1            # The section holds program information
.Lsht_symtab  = 2            # Symbol table
                             #   shlink=string table section header index
                             #   shinfo=last local symbol index + 1
.Lsht_strtab  = 3            # String table
.Lsht_rela    = 4            # Relocation entries with addends (see rela entry below)
                             #   shlink=symbol table section header index
                             #   shinfo=section header index of relocated section
.Lsht_hash    = 5            # Hash table
.Lsht_dynamic = 6            # Dynamic linking information
.Lsht_note    = 7            # Note section
.Lsht_nobits  = 8            # This section contains no bits
.Lsht_rel     = 9            # Relocation entries without addends (see rel entry below)
                             #   shlink=symbol table section header index
                             #   shinfo=section header index of relocated section
.Lsht_shlib   = 10           # reserved for unspecified semantics
.Lsht_dsym    = 11           # Dynamic symbol table (shlink -see sht_sym)
.Lsht_init    = 14           # Initialization array function of pointers
.Lsht_fini    = 15           # Termination array of function pointers
.Lsht_pinit   = 16           # Pre-initialization array of function pointers
.Lsht_group   = 17           # Group section
.Lsht_symdx   = 18           # Symbol table escape section indexes
.Lsht_loos    = 0x60000000   # Low value for operating specific sections
.Lsht_hios    = 0x6FFFFFFF   # High value for operating specific sections
.Lsht_loprc   = 0x70000000   # Low value for processor specific sections
.Lsht_hiprc   = 0x7FFFFFFF   # High value for processor specific sections
.Lsht_lousr   = 0x80000000   # Low value for application program use
.Lsht_hiusr   = 0xFFFFFFFF   # High value for application program use

 # +---------------------------------------------------------------+
 # |   32-bit ABI Relocation Entries With Addends  (rela entries)  |
 # +---------------------------------------------------------------+

         struct .Lrela32       # 32-bit rela section entry
         slong  .Lrelaoff32    # Item location (section offset or address in exe)
         sbytes .Lrelasym32,size=3  # Symbol table index of the relocation
         sbyte  .Lrelatyp32    # Relocation type (see rela type values below)
         slong  .Lrelaadd32    # Signed addend of value
         shere  .Lrela32_len   # Length of a 32-bit rela entry

 # +---------------------------------------------------------------+
 # |   64-bit ABI Relocation Entries With Addends  (rela entries)  |
 # +---------------------------------------------------------------+

         struct .Lrela64       # 64-bit relat section entry
         squad  .Lrelaoff64    # Item location (section offset or address in exe)
         slong  .Lrelasym64    # Symbol table index of the relocation
         slong  .Lrelatyp64    # Relocation type (see rela type values below)
         squad  .Lrelaadd64    # Signed addend of value
         shere  .Lrela64_len   # Length of a 64-bit rela entry

 # +---------------------------+
 # |   Common ABI rela values  |
 # +---------------------------+         

 # rela type values:
 #                    32-/64-bit ABI:                 Relocation symbols:
.Lr390none    = 0            #   no relocation         A  Represents the addend
.Lr390_8      = 1            #   byte8   S + A       * B  Shared object base address
.Lr390_12     = 2            #   low12   S + A         G  Global Offset table address
.Lr390_16     = 3            #   half16  S + A       * L  PLT entry address
.Lr390_32     = 4            #   word32  S + A         O  Symbol's GOT entry offset
.Lr390_pc32   = 5            #   word32  S + A - P     P  Address of relocated item
.Lr390_got12  = 6            #   low12   O + A         S  Symbol value from symbol
.Lr390_got32  = 7            #   word32  O + A            table entry
.Lr390_plt32  = 8            # * word32  L + A
.Lr390_copy   = 9            # *                      * Relocation types associated
.Lr390_glob   = 10           # * quad64  S + A          with shared object and/or
.Lr390_jmp    = 11           # *                        dynamic linking.
.Lr390_rel    = 12           # * quad64  B + A
.Lr390_gotof  = 13           #   quad64  S + A - G
.Lr390_gotpc  = 14           #   quad64  G + A - P
.Lr390_got16  = 15           #   half16  O + A
.Lr390_pc16   = 16           #   half16  S + A - P
.Lr390_pc16d  = 17           #   pc16   (S + A - P) >> 1
 #                    64-bit only:
.Lr390_pc32d  = 19           #   pc32   (S + A - P) >> 1
.Lr390_plt32d = 20           # * pc32   (L + A - P) >> 1
.Lr390_gotd   = 21           #   pc32   (G + A - P) >> 1
.Lr390_64     = 22           #   quad64  S + A
.Lr390_pc64   = 23           #   quad64  S + A - P
.Lr390_got64  = 24           #   quad64  O + A
.Lr390_plt64  = 25           # * quad64  L + A
.Lr390_gotnt  = 26           #   pc32   (G + O + A - P) >> 1

 # +----------------------------------+
 # |   32-bit ABI Symbol Table Entry  |
 # +----------------------------------+

         struct .Lesym32     # 32-bit ABI Symbol Table Entry
         slong  .Lstname32   # String table section offset of the symbol's name
         slong  .Lstname32   # The value of the symbol
         slong  .Lstsize32   # Size of the object in bytes
         sbyte  .Lstinfo32   # Symbol type and binding (see stinfo values below)
         sbyte  .Lstoth32    # Symbol visibility (see stoth values below)
         shword .Lstshndx32  # Section header table index of the symbol's location
         shere  .Lesym32_len # Length of a 32-bit symbol table entry

 # +----------------------------------+
 # |   64-bit ABI Symbol Table Entry  |
 # +----------------------------------+

         struct .Lesym64     # 64-bit ABI Symbol Table Entry
         slong  .Lstname64   # Index to the string table
         sbyte  .Lstinfo64   # Symbol type and binding (see stinfo values below)
         sbyte  .Lstoth64    # Symbol visibility (see stoth values below)
         shword .Lstshndx64  # Section header table index of the symbol's location
         squad  .Lstval64    # The value of the symbol
         squad  .Lstsize64   # Size of the object
         shere  .Lesym64_len # Length of a 64-bit symbol table entry

 # +-------------------------------+
 # |   Common Symbol Table Values  |
 # +-------------------------------+

 # stinfo values:
 #                    Binding Values
.Lstbindmsk   = 0xF0         # Mask for binding value
.Lstblocal    = 0x00         # Local binding
.Lstbglobal   = 0x10         # Global binding
.Lstbweak     = 0x20         # Weak binding
.Lstbloos     = 0xA0         # Low OS binding type
.Lstbhios     = 0xC0         # High OS binding type
.Lstblopr     = 0xD0         # Low processor binding type
.Lstbhipr     = 0xF0         # High processor binding type
 #                    Type Values
.Lsttypemsk   = 0x0F         # Mask for type
.Lsttnone     = 0            # Unspecified type
.Lsttobj      = 1            # Symbol is associated with a data object
.Lsttfunc     = 2            # Symbol is associated with a function or code
.Lsttsect     = 3            # Symbol is associated with a section
.Lsttfile     = 4            # Symbol is the name of the source file
.Lsttcommon   = 5            # Symbol labels an unintialized common block
.Lstttls      = 6            # TLS offset
.Lsttloos     = 10           # Low OS symbol type
.Lstthios     = 12           # High OS symbol type
.Lsttlopr     = 13           # Low processor symbol type
.Lstthipr     = 15           # High processor symbol type

 # stoth values:
.Lstvmask     = 0x03         # Visibility mask
.Lstvdft      = 0            # Default, uses symbol binding type
.Lstvint      = 1            # Internal visibility
.Lstvhidden   = 2            # Hidden visibility
.Lstvprot     = 3            # Protected visibility

.endif
