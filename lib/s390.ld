/* s390 Stand Alone Linker Script */
/*
Copyright (C) 2012 Harold Grovesteen

    This file is part of SATK.

    SATK is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SATK is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SATK.  If not, see <http://www.gnu.org/licenses/>.
*/

OUTPUT_FORMAT(elf32-s390)
OUTPUT_ARCH(s390:31-bit)
TARGET(elf32-s390)

MEMORY { memory : ORIGIN = 0, LENGTH = 0x80000000 }

/*
   The program must inform the linker of the location the start 
   at which the ELF executable will be loaded by defining as a 
   global symbol: loadpt.
   
   The 'loadpt' symbol must be defined in the linker command line.  
   This symbol defines where the ELF will be loaded into absolute
   storage.  The following toolsfun function will set its value:
   
       sa_sym loadpt 0x1000 # ELF will be loaded at address X'1000'
   
   How the loading of the ELF at the loadpt symbol's value is
   accomplished is outside the scope of the linker and must be 
   handled by non-linker mechanisms.
   
   The program can locate the start of the ELF executable by 
   defining as a global symbol:
   
   .Lelfbeg: .long loadpt    # Where the ELF is loaded
             .global loadpt  # Allow the linker to supply the value
             
   Additionally, the symbol _phdrs is provided by the linker to 
   inform the program of the number of bytes between the start of the
   .text section and the start of the EFL.  The value includes: 
   the ELF header, program segment headers and alignment padding.
*/

SECTIONS
{
  .text loadpt + sizeof_headers :
                 { /* .text section */
                      . = ALIGN(0x10) ;
                      _phdrs = ABSOLUTE ( . - loadpt ) ;
                      *(.text.*)
                   /* .rela section */
                      . = ALIGN (0x4) ;
                      *(.rela.text)
                   /* .rel section */
                      . = ALIGN (0x4) ;
                      *(.rel.*) ;
                   /* .data section */
                      . = ALIGN(0x10) ;
                      *(.data)
                   /* .bss section */
                      . = ALIGN(0x10) ;
                      *(.bss)
                 } >memory
}
