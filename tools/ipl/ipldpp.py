#!/usr/bin/python3.3
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

# Utility to preprocess IPL ELF object files 
# and creating a tailored ld linker script for IPL ELF executable creation

# This lds class, in conjuction with the section, segment and area classes,
# manages the linker script generation.
#
# The generated linker script combines elements of the elf_s390 or 
# elf64_s390 .xr and .xbn standard scripts.  Additionally the generated script 
# excludes sections related to dynamic linking, C++ and debugging (both stabs 
# and DWARF).  The exclusion of relocation information is optional and is the
# default.  The following table identifies how each input section that might
# be encouuntered is handled.
#
# The objective is to minimize the size of the TEXT segment (into which all
# program related sections are placed) allowing it to be stored within the
# physical constraints that exist for the IPL medium.
#
# WARNING: If an IPL ELF section is not marked as allocatable and containing
#          data, the segment header may not include the correct addresses or
#          segment size.  Use this code in the assembler source:
#               .section name,"a",@progbits
#
# WARNING: A warning is issued by the linker if any other type besides PT_LOAD
#          is used.  The warning is spurious but by using PT_LOAD the warning
#          is avoided.
#
#
#                                                          linker
# input section       type         included   excluded   controlled
#
# .interp             dyn linking                 X
# .note.gnu.build-id  GNU specific                X
# .hash               dyn linking                 X
# .gnu.hash           dyn linking                 X
# .dynsym             dyn linking                 X
# .dynstr             dyn linking                 X
# .gnu.version        GNU specific                X
# .gnu.version_d      GNU specific                X
# .gnu.version_r      GNU specific                X
# .rela.init          relocation                               -r
# .rela.text          relocation    optional
# .rela.fini          relocation    optional
# .rela.rodata        relocation    optional
# .rela.data.rel.ro   relocation    optional
# .rela.data          relocation    optional
# .rela.tdata         relocation    optional
# .rela.tbss          relocation    optional
# .rela.ctors         C++                         X
# .rela.dtors         C++                         X
# .rela.got           relocation    optional
# .rela.bss           relocation    optional
# .rela.iplt          dyn linking                 X
# .rela.plt           dyn linking                 X
# .init               program           X
# .plt                dyn linking                 X
# .iplt               dyn linking                 X
# .text               program           X
# .fini               program           X
# .rodata             program           X
# .reodata1           program           X
# .eh_frame_hdr       C++                         X
# .eh_frame           C++                         X
# .gcc_except_table   C++                         X
# .tdata              thread local      X
# .tbss               thread local      X
# .preinit_array      program           X
# .init_array         program           X
# .fini_array         program           X
# .jcr                java                         X
# .dynamic            dyn linking                  X
# .got                execution                                 X  
# .got.plt            execution                                 X
# .data               program           X
# .data1              program           X
# .bss                program           X
# .stab family        debugging                    X
# .comment            debugging                    X
# .debug              debugging                    X
# .line               debugging                    X
# .debug family       debugging                    X
# .gnu.attibutes      debugging                    X
# .shstrtab           execution                                 X
# .strtab             incr. linking  optional                  -s
# .symtab             dyn linking    optional                  -s



# SATK imports
from lds_factory import *   # GNU ld script generator
import PyELF                # ELF utility
# Python imports
import argparse             # command line argument parser
import functools            # Access the compare to key function method for sorting
import re                   # access to regular expression utility
import sys                  # system values

# Note: this module requires Python 2.6 or 2.7.  It can not be migrated to 
# Python 3.0 until PyELF can be migrated to Python 3.0

class area(object):
    def __init__(self,name,start,end,attr=None):
        self.name=name
        self.start=start
        self.end=end
        self.attr=attr
        if end<=start:
            raise ValueError(\
                "invalid area end: start=% >= end=%s" % (start,end))
        self.length=end-start+1
        #self.sequence=sequence  # sequence in which segments assigned to area
        self.present=False
        self.segments=[]   # segments assigned to this area
        iplelf.areas[self.name]=self
        self.ldso=None     # lds_factory instance created in lds method
    def __str__(self):
        p=" "
        if self.present:
            p="*"
        s="%s  %s %06X-%06X: " % (self.name,p,self.start,self.end)
        for x in self.segments:
            s="%s%s," % (s,x.name)
        return s[:-1]
    def adjust(self,size):
        # shrinks area by increasing start location
        self.start+=size
        self.length-=size
    def extend(self,size):
        # increases area by increasting end location
        self.end=size-1
        self.length=self.end-self.start+1
    def lds(self):
        self.ldso=lds_region(self.name,self.start,self.length,attr=self.attr)
        

class iplelf(object):
    ELFCLASS32=1
    ELFCLASS64=2
    EM_S370=9
    EM_S390=22
    areas={}     # Defined storage areas
    sections={}  # Recognized sections
    segments={}  # Recognized segments
    def __init__(self,proc=None,loader=False,ipl=".ipl"):
        # Note: areas are defined in the relative sequence they will appear
        # in the ld script
        #
        # s370 and s390 areas
        if isinstance(proc,s370) or isinstance(proc,s390):
            area("ELF1",0x1000,0xFFFFFF,attr="rwx")
            area("TXT0",0x300,0xFFFFFF,attr="rwx")
        # s390x areas
        if isinstance(proc,s390x):
            area("ELF2",0x2000,0xFFFFFF,attr="rwx")
            area("TXT2",0x1400,0xFFFFFF,attr="rwx")
            area("TXT1",0x300,0x11FF,attr="rwx")
        # Common area
        area("LOWC",0x0,0x2FF,attr="rw")
        area("/DISCARD/",0x0,0x1,attr="")
        #
        # Recognized sections
        self.loading=proc.targets(ipl)
        # [0]=segment flags, [1]=TEXT/ELF [2]=storage area

        # Recognized segments
        segment("TEXT",ptype="PT_LOAD",sections=[".text"],pflags=0x00000007)
        segment("LODR",ptype="PT_LOAD",sections=[".lodr"],pflags=0xF0000007)
        segment("CCW",ptype="PT_LOAD",sections=[".ccw"],pflags=0x20000004)
        segment("IPL",ptype="PT_LOAD",sections=[ipl],pflags=self.loading[0])
        segment("LOWC",ptype="PT_LOAD",sections=[".lowc"],pflags=0x30000006)
        segment("/DISCARD/",ptype=None)
        #
        # Process parameters
        self.loader=loader>0  # LOADER segment is being generated
        self.processor=proc   # Processor of ELF
        self.iplsect=ipl      # IPL section
    def __str__(self):
        if self.processor is None:
            p="None"
        else:
            p=self.processor.__class__.__name__
        return "IPL ELF processor(%s) loader(%s)" % (p,self.loader)

class lds(object):
    # This class, in conjuction with the section, segment and area classes,
    # manages the linker script generation.
    #
    # The generated linker script combines elements of the elf_s390 or 
    # elf64_s390 .xr and .xbn standard scripts.  Additionally the generated
    # script excludes sections related to dynamic linking, C++ and debugging 
    # (both stabs and DWARF)
    insects=[]                 # section_in instances register here
    ingroups={}                # section_group instances register here
    outsects={}                # section_out instances register here
    def __init__(self,addr=None,entry=None,relo=False):
        self.addr=addr         # load point of ELF or TEXT segment
        self.entry=entry       # link edit entry point
        self.relo=relo         # Whether self relocation is enabled
        self.sections_in=[]    # Input Sections being included in IPL ELF
        self.segments=[]       # Segments in this IPL ELF executable
        self.areas=[]          # Areas in this IPL ELF executable
        self.load=None         # Determined when generating
        self.sections_out={}   # Output sections
        self.action(relo=relo) # Build the sections_in and sections_out lists
    def __str__(self):
        return "IPL ELF options: load(%s) entry(%s) relo(%s)" \
            % (self.__hexfmt(self.addr),self.entry,self.relo)
    def __hexfmt(self,value):
       if value is None:
           return "None"
       return "0x%06X" % value
    def action(self,relo=False):
        # create the possible output sections
        section_out(".ipl",segment="IPL")
        section_out(".iplt",segment="IPL")
        section_out(".text",segment="TEXT")
        section_out(".lowc",segment="LOWC")
        section_out(".lodr",segment="LODR")
        section_out(".ccw",segment="CCW")
        discard()
        # create the possible input section groups
        #   Note: This was a failed attempt to make the RELA entries directly 
        #   addressable from the TEXT segment.
        #   section_grp(".rela",out_section=".text",align=0x10,provide="_rela")
        # Set the actions for all recognized input sections
        ext=r'(\.[A-Za-z0-9\_]+)*'
        exteol=ext+r'$'
        # .lowc output section sequence of input sections
        section_in(re.escape(".asl")+r'$',include=True,\
            out_section=".lowc")
        section_in(re.escape(".iplp")+r"$",include=True,\
            out_section=".lowc",align=512,post_align=256)
        # .ipl output section single input section
        section_in(re.escape(".ipl")+exteol,include=True,\
            out_section=".ipl",align=None)
        # .ipl output section single input section
        section_in(re.escape(".iplt")+exteol,include=True,\
            out_section=".iplt",align=None)
        # .ccw output section single input section
        section_in(re.escape(".ccw")+r'$',include=True,\
            out_section=".ccw",align=8)
        # .lodr output section single input section
        section_in(re.escape(".loader")+r'$',include=True,\
            out_section=".lodr",align=None)
        # .text output section sequence of input sections
        section_in(re.escape(".text")+ext+r'|(\.stub)$',include=True,\
            out_section=".text")
        section_in(re.escape(".init")+r'$',include=True,\
            out_section=".init")
        section_in(re.escape(".fini")+r'$',include=True,\
            out_section=".fini")
        section_in(re.escape(".data")+exteol,include=True,\
            out_section=".text")
        section_in(re.escape(".rodata")+r'$',include=True,\
            out_section=".text")
        section_in(re.escape(".rodata1")+r'$',include=True,\
            out_section=".text")
        section_in(re.escape(".tdata")+exteol,include=True,\
            out_section=".tdata")
        section_in(re.escape(".tbss")+exteol,include=True,\
            out_section=".text")
        section_in(re.escape(".preinit_array")+r'$',include=True,\
            out_section=".text")
        section_in(re.escape(".init_array")+exteol,include=True,\
            out_section=".text")
        section_in(re.escape(".fini_array")+exteol,include=True,\
            out_section=".text")
        section_in(re.escape(".got")+r'$',include=True,\
            out_section=".text",provide="_GOT",force=".got")
        section_in(re.escape(".data1"),include=True,\
            out_section=".text")
        section_in(re.escape(".rela.init")+r'$',include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.fini")+r'$',include=relo,\
            out_section=".text")
        section_in(re.escape(".shstrtab")+r'$',include=relo, \
            out_section=".text")
        section_in(re.escape(".symtab")+r'$',include=relo, \
            out_section=".text")
        section_in(re.escape(".strtab")+r'$',include=relo, \
            out_section=".text")
        #section_in(re.escape(".rela.text")+exteol,include=relo,\
        #    out_section=".text")
        section_in(re.escape(".rela.text")+r'$',include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.rodata")+exteol,include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.data")+exteol,include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.tdata")+exteol,include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.tbss")+exteol,include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.got")+exteol,include=relo,\
            out_section=".text")
        section_in(re.escape(".rela.bss")+exteol,include=relo,\
            out_section=".text")
        section_in(r'(\.bss'+ext+r'|COMMON)$',include=True,\
            out_section=".text")
        # Not included input sections that might be encountered
        section_in(re.escape(".rela.ipl")+exteol,include=False,ignore=True)
        section_in(re.escape(".rela.iplt")+exteol,include=False,ignore=True)
        section_in(re.escape(".rela.ccw")+r'$',include=False,ignore=True)
        section_in(re.escape(".rela.asl")+r'$',include=False,ignore=True)
        section_in(re.escape(".rela.iplp")+r'$',include=False,ignore=True)
        section_in(re.escape(".rela.loader")+r'$',include=False,ignore=True)
        section_in(re.escape(".interp")+r'$',include=False)
        section_in(re.escape(".note.gnu.build-id")+r'$',include=False)
        section_in(re.escape(".hash")+r'$',include=False)
        section_in(re.escape(".gnu.hash")+r'$',include=False)
        section_in(re.escape(".dynsym")+r'$',include=False)
        section_in(re.escape(".dynstr")+r'$',include=False)
        section_in(re.escape(".gnu.version")+r'$',include=False)
        section_in(re.escape(".gnu.version_d")+r'$',include=False)
        section_in(re.escape(".gnu.version_r"),include=False)
        section_in(re.escape(".rela.ctors")+r'$',include=False)
        section_in(re.escape(".rela.dtors")+r'$',include=False)
        section_in(re.escape(".rela.iplt")+r'$',include=False)
        section_in(re.escape(".rela.plt")+r'$',include=False)
        section_in(re.escape(".eh_frame_hdr")+r'$',include=False)
        section_in(re.escape(".eh_frame")+r'$',include=False)
        section_in(re.escape(".gcc_except_table")+r'$',include=False)
        section_in(re.escape(".jcr")+r'$',include=False)
        section_in(re.escape(".dynamic")+r'$',include=False)
        section_in(re.escape(".stab")+exteol,include=False)
        section_in(re.escape(".comment")+r'$',include=False)
        section_in(re.escape(".debug")+exteol,include=False)
        section_in(re.escape(".line")+r'$',include=False)
        section_in(re.escape(".gnu.attibutes")+r'$',include=False)
    def generate(self,ipl_elf,elf,debug=False):
        #
        # Determine target storage area in case of loader and multiple targets
        # targets maps segments to target storage areas.
        if ipl_elf.loader:
            targets=ipl_elf.processor.__class__.loader
            self.load="ELF"
            txt_area=targets["TEXT"]
            ldr_area=targets["LODR"]
            area=iplelf.areas[txt_area]
            area.sequence=["TEXT","CCW","IPL"]
            area=iplelf.areas[txt_area]
            area.sequence=["LODR"]
        else:
            targets=ipl_elf.processor.__class__.noldr
            self.load=ipl_elf.loading[1]
            area=iplelf.areas[ipl_elf.loading[2]]
            area.sequence=["TEXT","CCW","IPL"]
            targets["TEXT"]=area.name
            targets["IPL"]=area.name
            targets["CCW"]=area.name
        #
        #  Process ELF object file for sections
        elf_sects=elf.SctTbl.entries
        for x in elf_sects:
            if x.typ==0:
                # Ignore NULL section
                continue
            try:
                insect=self.recognize(x.name)
            except ValueError:
                print("ipldpp.py: warning: unrecognized input section: %s" \
                    % x.name)
                continue
            if not insect.include:
                if debug:
                    print("ipldpp.py: debug - section not included: %s" % x.name)
                insect.discard()
                if not insect.ignore:
                    print("ipldpp.py: warning: section ignored: %s" % x.name)
            else:
                if debug:
                    print("ipldpp.py: debug - section included: %s" % x.name)
            self.in_section(x.name,insect,debug)
        
        #
        # Add forced sections:
        for x in lds.insects:
            if not x.force:
                continue
            self.in_section(x.force_sect,x,debug)
        
        #
        # Assign output sections to segments and sequence the input sections
        #for x in self.sections_out.itervalues():
        for x in iter(self.sections_out.values()):
            self.sequence(x)
            seg=iplelf.segments[x.segment]
            x.sego=seg
            seg.assigned.append(x)
            if debug:
                print("ipldpp.py: debug - assigning output section %s to segment %s"\
                    % (x.name, seg.name))
            seg.present=True
        #
        # Assign segments to storage areas
        #for x in iplelf.segments.itervalues():
        for x in iter(iplelf.segments.values()):
            if x.present:
                if x.name!="/DISCARD/":
                    tar_area=targets[x.name]
                else:
                    tar_area="/DISCARD/"
                seg_area=iplelf.areas[tar_area]
                seg_area.present=True
                seg_area.segments.append(x)
                x.area=seg_area
                if debug:
                    print("ipldpp.py: debug - assigned segment %s to area %s" \
                         % (x.name, seg_area.name))
                self.segments.append(x)
        #
        # Identify the areas needed in the IPL ELF executable
        #for x in iplelf.areas.itervalues():
        for x in iter(iplelf.areas.values()):
            if x.present:
                self.areas.append(x)
        #
        # Need to adjust load point for headers if loading the ELF
        # area is the area in which the TEXT segment will be loaded
        headers=0
        if area.name in ["ELF1","ELF2"]:
            seghdr=ipl_elf.processor.seghdr
            elfhdr=ipl_elf.processor.elfhdr
            headers=(seghdr*len(self.segments))+elfhdr
            area.adjust(headers)
            if ipl_elf.loader:
                # If using an embedded loader, can load IPL ELF anywhere
                area.extend(ipl_elf.processor.storage)
        #
        if self.addr is not None:
            txtout=self.sections_out[".text"]
            txtout.addr=self.addr+headers
        #
        # Print debug info if requested
        if debug:
            print("ipldpp.py: debug: input sections in object:"\
                " %s" % len(self.sections_in))
            for x in self.sections_in:
                print("  %s" % x)
            values=lds.ingroups.values()
            print("ipldpp.py: debug: input section groups: %s"\
                % len(values))
            for x in lds.ingroups.values():
                print("  %s" % x)
                for y in x.sections:
                    print("     %s" % y)
            values=self.sections_out.values()
            print("ipldpp.py: debug: sections in executable:"\
                " %s" % len(values))
            for x in values:
                print("  %s" % x)
            print("ipldpp.py: debug: segments in executable:"\
                " %s" % len(self.segments))
            for x in self.segments:
                print("   %s" % x)
            print("ipldpp.py: debug: areas in executable:"\
                " %s" % len(self.areas))
            for x in self.areas:
                print("   %s" % x)
    #
    # Create linker script
        
        # Instantiate lds_factory objects
        sects_out=[]
        for x in iter(self.sections_out.values()):
            sects_out.append(x)
        create_lds=[self.areas,\
                    self.segments,\
                    #self.sections_out.itervalues(),\
                    sects_out,\
                    self.sections_in]
        for x in create_lds:
            for y in x:
                y.lds()
        # Generate GNU ld script
        fact=lds_script()
        fact.add(lds_format(ipl_elf.processor.elf_format))
        fact.add(lds_arch(ipl_elf.processor.elf_arch))
        fact.add(lds_target(ipl_elf.processor.elf_target))
        if self.entry is not None:
            fact.add(lds_entry(self.entry))
        # Build the MEMORY command
        memory=lds_memory()
        for x in self.areas:
            # Create the memory region for each area
            if x.name!="/DISCARD/":
                memory.add(x.ldso)
        fact.add(memory)
        # Build the PHDRS command
        headers=lds_headers()
        sections=lds_sections()
        for x in self.segments:
            # Create the headers for each segment
            if x.name!="/DISCARD/":
                headers.add(x.ldso)
        fact.add(headers)
        # Build the SECTIONS command
        #   Output sections need to be placed in sequence based upon how 
        #   the segments have been assigned to an area
        sections=lds_sections()
        # WARNING: Adding this statement to the script causes ld to segment fault
        # sections.add(lds_assign(lable="_phdrs",value="SIZEOF_HEADERS"))
        areas_seq=[]
        make_last=None
        for x in self.areas:
            if x.name=="/DISCARD/":
                make_last=x
            else:
                areas_seq.append(x)
        if not make_last is None:
            areas_seq.append(make_last)     
        for x in areas_seq:
            # Process each area (x is an area instance)
            if debug:
                print("ipldpp.py - processing area: %s" % x.name)
            for y in x.segments:
                # Process each segment in the area (y is a segment instance)
                if debug:
                    print("ipldpp.py -   processing segment: %s" % y.name)
                for z in y.assigned:
                    # Process each output section in each segment
                    # (z is a section_out instance)
                    if debug:
                        print("ipldpp.py -     processing output section: %s"\
                            % z.name)
                    for a in z.in_sections:
                        # Process each input section
                        if debug:
                            print("ipldpp.py -       processing input section: %s"\
                                % a.name)
                        a.generate(z.ldso)
                        #z.ldso.add(a.ldso)
                    sections.add(z.ldso)
        fact.add(sections)
        # Now finally generate the linker script
        script=fact.generate(self.lds_prefix("",ipl_elf.processor))
        return script
    def in_section(self,name,insect,debug=False):
        try:
            if debug:
                print("ipldpp.py: debug - input section %s expects to be in "\
                    " output section %s" \
                    % (name, insect.out_section))
            outsect=self.sections_out[insect.out_section]
            assert outsect.name==insect.out_section,\
                "ipldpp.py: internal error - output section %s returned " \
                "section %s" % (insect.out_section, outsect.name)
        except KeyError:
            try:
                outsect=lds.outsects[insect.out_section]
            except KeyError:
                raise ValueError("ipldpp.py: internal error - unrecognized "
                    "output section by input section %s: %s" \
                    % (name, insect.out_section))
            self.sections_out[insect.out_section]=outsect
        if debug:
            print("ipldpp.py: debug - output section is: %s" % outsect.name)
        s=section(name,\
            align=insect.align,\
            post_align=insect.palign,\
            provide=insect.provide,\
            seq=insect.seq)
        s.out_section=outsect.name
        if debug:
            print("ipldpp.py: debug: adding section %s to output section %s" \
                % (s.name, outsect.name))
        outsect.add(s)
        self.sections_in.append(s)    
    def lds_prefix(self,script,processor):
        s="%s/* %s Stand-Alone Linker Script      \n" \
            % (script,processor.__class__.__name__)
        s="%s   Generated by ipldpp.py - DO NOT EDIT */\n\n" % s
        return s
    def recognize(self,name):
        # Returns either a section_in instance, or raises a ValueError
        for x in lds.insects:
            if x.is_this(name,debug=False):
                return x
        raise ValueError
    def sequence(self,out_section):
        # This method uses the old way of sorting using decorator-sort-undecorate
        # method.  The object and its sort key values are encapsulated in a 
        # class instance.  These class instances are sorted and the embedded object
        # is extracted and placed in its own sequence.  For version 3, the 
        # decorator has been maintained, but the sorting mechanism uses a key
        # function instead of the instance compare method.
        seq=[]
        # Create the decorated list
        for x in range(len(out_section.in_sections)):
            insect=out_section.in_sections[x]
            #print("sequence: insect=%s" % insect.__class__)
            seq.append(sort(insect.seq,x,insect))
        #seq.sort()
        # For Version 3, the seq.sort() statement is replaced with the built-in
        # function sorted.  It uses a key function that is a staticmethod in the
        # decorator class.  The staticmethod was added to support Version 3.
        sorted_seq=sorted(seq,key=functools.cmp_to_key(sort.compare))
        newseq=[]
        for x in sorted_seq:
            newseq.append(x.obj)
        out_section.in_sections=newseq

class LDPP(object):
    def __init__(self,opts,debug=False):
        self.options=opts
        self.debug=debug or self.options.debug
        self.objfile=self.options.objfile[0]
        self.ldsfile=self.options.lds
        # Values set by input analysis
        self.area=None        # Area into which ELF or TEXT is to be loaded
        self.processor=None   # Processor and supplement of ELF
        self.ldsctl=None      # lds instance defining how to structure script
        # Process the ELF
        self.elf=PyELF.elf(PyELF.elf_source(filename=self.objfile))
        if self.debug:
            self.elf.prt(details=True)
        self.ipl_elf=iplelf(\
            loader=self.isSection(".loader"),\
            proc=self.identifyProcessor(),\
            ipl=self.iplsection())
        print("ipldpp.py: IPL ELF object: %s" % self.objfile)
        print("ipldpp.py: %s" % self.ipl_elf)
        try:
            if self.options.addr!=None:
                self.ldaddr=int(self.options.addr,16)
            else:
                self.ldaddr=None
        except:
            print("ipldpp.py: invalid addr parameter '%s',"\
                " using area start: %06X" \
                % self.options.addr,iplelf.areas[self.area].start)
        self.ldsctl=lds(\
            addr=self.ldaddr,\
            relo=self.options.relo,\
            entry=self.options.entry)
        print("ipldpp.py: %s" %self.ldsctl)
    def generate(self,debug=False):
        script=self.ldsctl.generate(self.ipl_elf,self.elf,self.debug)
        try:
            fo=open(self.ldsfile,"wt")
            fo.write(script)
            fo.close()
        except IOError:
            print("ipldpp.py: error: could not write linker script: %s" \
                % self.ldsfile)
        print("ipldpp.py: IPL ELF script: %s" % self.ldsfile)
    def iplsection(self):
        # Determine the .ipl section
        iplsect=".ipl"
        iplsects=0
        for x in self.elf.SctTbl.entries:
            if self.isIPLSection(x.name):
                iplsects+=1
                iplsect=x.name
        if iplsects>1:
            print("ipldpp.py: error: ELF object file contains multiple" \
                " .ipl sections")
            sys.exit(1)
        return iplsect
    def isIPLSection(self,name):
        if len(name)>=5 and name[:5]==".iplt":
            return True
        if len(name)>=4 and name[:4]==".ipl":
            return True
        return False
    def isSection(self,name):
        try:
            return len(self.elf.getSection(name))
        except KeyError:
            return 0
    def identifyProcessor(self):
        s370()
        s390()
        s390x()
        elfcls=self.elf.ident.arch
        elfmch=self.elf.header.machine
        try:
            self.processor=processor.identify(elfcls,elfmch)
            return self.processor
        except KeyError:
            print("ipldpp.py: error: unrecognized ELF: "
                  "e_machine=%s, EI_CLASS=%s" % (elfmch,elfcls))
            sys.exit(1)   

# These classes map ELF header content to the valid IPL ELF storage areas for
# the processor
class processor(object):
    instances=[]
    @staticmethod
    def identify(cls,machine):
        for x in processor.instances:
           if x.ei_class==cls and x.e_machine==machine:
               return x
        raise KeyError
    def __init__(self,cls,machine):
        self.name=self.__class__.__name__
        self.ei_class=cls        # ELF header class
        self.e_machine=machine   # ELF header machine
        processor.instances.append(self)  # Add me to the list
    def lds_prefix(self):
        # Provide processor prefix information
        return script
    def lds_body(self):
        # Provide processor information
        return "OUTPUT_FORMAT(%s)\nOUTPUT_ARCH(%s)\nTARGET(%s)\n" \
            % (self.elf_format,self.elf_arch,self.elf_target)
    def ldx_suffix(self):
        # Provide processor suffix information
        return ""
    def targets(self,section):
        try:
            targs=self.loading[section]
            # [0]=segment flags, [1]=TEXT/ELF [2]=storage area
        except KeyError:
            print("ipldpp.py: error: unrecognized ipl section: %s" % section)
            sys.exit(0)
        return targs
        
        
class proc32bit(processor):
    # These dictionaries map segments to eligible storage areas
    loader={"IPL"   :"ELF1",
            "LOWC"  :"LOWC",
            "LODR"  :"TXT0",
            "TEXT"  :"ELF1",
            "CCW"   :"ELF1"}
    noldr= {"IPL"   :["TXT1","ELF1"],
            "LOWC"  :"LOWC",
            "IPLP"  :"LOWC",
            "TEXT"  :["TXT1","ELF1"],
            "CCW"   :["TXT1","ELF1"]}
    def __init__(self,machine):
        processor.__init__(self,iplelf.ELFCLASS32,machine)
        self.areas=["ELF1","TXT0"]
        self.dftelf="ELF1"
        self.dftext="TXT0"
        self.elfhdr=52  # Size of the ELF header
        self.seghdr=32  # Size of a segment header
        self.loading={".ipl":[0x14000004,"ELF","ELF1"],
                      ".ipl.txt0":[0x11000004,"ELF","TXT0"],
                      ".ipl.elf1":[0x14000004,"ELF","ELF1"],
                      ".iplt":[0x19000004,"TEXT","TXT0"],
                      ".iplt.txt0":[0x19000004,"TEXT","TXT0"],
                      ".iplt.elf1":[0x1C000004,"TEXT","ELF1"]}
        self.elf_format="elf32-s390"
        self.elf_arch='s390:31-bit'
        self.elf_target=self.elf_format
    def assignArea(self,iplelf,area,loader=False):
        if loader:
            # assign areas with loader
            return proc32bit.loader
        return proc32bit.noldr   
        
class proc64bit(processor):
    # These dictionaries map segments to eligible storage areas
    loader={"IPL"   :"ELF2",
            "LOWC"  :"LOWC",
            "LODR"  :"TXT1",
            "TEXT"  :"ELF2",
            "CCW"   :"ELF2"}
    noldr= {"IPL"   :["TXT1","TXT2","ELF2"],
            "LOWC"  :"LOWC",
            "IPLP"  :"LOWC",
            "TEXT"  :["TXT1","TXT2","ELF2"],
            "CCW"   :["TXT1","TXT2","ELF2"]}
    def __init__(self,machine):
        processor.__init__(self,iplelf.ELFCLASS64,machine)
        self.areas=["ELF2","TXT1","TXT2"]
        self.dftelf="ELF2"
        self.dftext="TXT2"
        self.elfhdr=64  # Size of the ELF header
        self.seghdr=56  # Size of a segment header
        self.loading={".ipl":[0x15000004,"ELF","ELF2"],
                      ".ipl.txt1":[0x12000004,"ELF","TXT1"],
                      ".ipl.txt2":[0x13000004,"ELF","TXT2"],
                      ".ipl.elf2":[0x15000004,"ELF","ELF2"],
                      ".iplt":[0x1A000004,"TEXT","TXT1"],
                      ".iplt.txt1":[0x1A000004,"TEXT","TXT1"],
                      ".iplt.txt2":[0x1B000004,"TEXT","TXT2"],
                      ".iplt.elf2":[0x1D000004,"TEXT","ELF2"]}
        self.elf_format="elf64-s390"
        self.elf_arch="s390:64-bit"
        self.elf_target=self.elf_format
    def assignArea(self,iplelf,area,loader=False):
        if loader:
            # assign areas with loader
            return proc64bit.loader
        return proc64bit.noldr   
        
class s370(proc32bit):
    def __init__(self):
        proc32bit.__init__(self,iplelf.EM_S370)
        self.storage=0x1000000
        
class s390(proc32bit):
    def __init__(self):
        proc32bit.__init__(self,iplelf.EM_S390)
        self.storage=0x80000000
        
class s390x(proc64bit):
    def __init__(self):
        proc64bit.__init__(self,iplelf.EM_S390)
        self.storage=0x10000000000000000

class section(object):
    # Individual input sections accepted for output processing
    def __init__(self,name,align=None,post_align=None,provide=None,seq=None):
        self.name=name
        self.align=align        # alignment required by section
        self.palign=post_align  # align content following sections
        self.present=False
        self.out_section=None   # Output section to which section is included
        self.provide=provide    # provide xxx_begin and xxx_end lables
        self.seq=seq            # sequence number
        iplelf.sections[self.name]=self
        self.ldso=None          # lds factory instance created by lds method
    def __str__(self):
        p=" "
        seg="None"
        if self.present:
            p="*"
        s="%s%s @%s" % (format(self.name,"<7s"),p,self.out_section)
        return s
    def generate(self,lds_output):
        if self.align is not None:
            lds_output.add(lds_align(self.align))
        if self.provide is not None:
            lds_output.add(lds_provide("%s_begin" % self.provide))
        lds_output.add(self.ldso)
        if self.provide is not None:
            lds_output.add(lds_provide("%s_end" % self.provide))
        if self.palign is not None:
            lds_output.add(lds_align(self.palign))
    def lds(self):
        self.ldso=lds_in("*(%s)" % self.name)

# This class allows input sections to be grouped with starting and ending 
# addresses provided for the group.  It was developed for use with the failed
# attempt to bring RELA entries into the TEXT segment.  It is left in the file
# as a capability that might prove useful in the future, but is presently not
# being used.
class section_grp(object):
    # This class allows multiple input sections within a segment to be treated as 
    # a single group.  It essentially wrappers individual section instances.
    def __init__(self,name,out_section=".text",align=None,post_align=None,\
                 provide=None):
        self.name=name       # Group name
        self.align=align            # Alignment required for group or not
        self.post_align=post_align  # Alignment required following group or not
        self.provide=provide  # Provide begin and end symbols or not
        self.sections=[]      # List of sections actually part of the group
        self.out_section=out_section    # Output section into which group is placed
        lds.ingroups[self.name]=self    # Register myself for later reference
        self.seg=None         # sequence method will assign
    def __str__(self):
        return "%s G @%s" % (self.name,self.out_section)
    def add(self,section):
        self.sections.append(section)
    def generate(self,lds_output):
        # generate the lds instances and add it to the output
        if self.align is not None:
            lds_output.add(lds_align(self.align))
        if self.provide is not None:
            lds_output.add(lds_provide("%s_begin" % self.provide))
        for x in self.sections:
            x.lds()
            x.generate(lds_output)
        if self.provide is not None:
            lds_output.add(lds_provide("%s_end" % self.provide))
        if self.post_align is not None:
            lds_output.add(lds_align(self.post_align))
    def lds(self):
        # Does not do anything.
        pass
    def sequence(self):
        seq=[]
        for x in range(len(self.sections)):
            insect=self.sections[x]
            seq.append(sort(insect.seq,x,insect))
        seq.sort()
        newseq=[]
        for x in seq:
            newseq.append(x.obj)
        self.in_sections=newseq
        if len(self.in_sections)>0:
            self.seq=self.in_sections[0].seq

class section_in(object):
    # This class assists with managing how various input sections in the 
    # ELF object file will be handled.  Each instance is a set of possible
    # input sections.  Individual input sections are represented by a instance
    # of class section.
    def __init__(self,regex,include=False,out_section=".text",\
                align=16,post_align=None,ignore=False,provide=None,grp=None,\
                force=""):
        self.regex=regex               # original input expression
        self.ro=re.compile(regex)      # used to recognize this section
        self.include=include           # Should section be included or not
        if self.include:
            self.out_section=out_section   # Output section where this section goes
        else:
            self.out_section="/DISCARD/"   # Put the input section in /DISCARD/
        self.align=align               # alignment required by input section
        self.palign=post_align         # align following section
        self.ignore=ignore             # If true, do not report error if present
        self.provide=provide           # provide begin/end labels or not
        self.seq=len(lds.insects)      # Sequence number for relative placement
        self.group=grp                 # This input section is part of a group
        self.force_sect=force          # Name of section to force
        self.force=force!=""           # Force inclusion in linker script
        lds.insects.append(self)       # register myself for later reference
    def discard(self):
        # This is used to discard the input section
        self.align=None
        self.palign=None
        self.provide=None
        self.group=None
        self.out_section="/DISCARD/"
    def is_this(self,string,debug=False):
        match=self.ro.match(string)
        if debug:
            print("section_in.is_this(): r'%s' match '%s' == %s" \
                % (string,self.regex,match))
        if match is None:
            return False
        return True

class section_out(object):
    def __init__(self,name,segment=None,align=None,addr=None):
        self.name=name
        self.align=align         # alignment of output section in area
        self.addr=addr           # address of output section
        self.in_sections=[]      # section or section_grp instances
        self.segment=segment     # segment instance in which this will be placed
        lds.outsects[name]=self
        self.sego=None           # segment instance to which this is assigned
        self.ldso=None           # lds factory instance created by lds method
        self.discard=False       # If this is a discard output section
    def __str__(self):
        if self.sego is None:
            segname="None"
        else:
            segname=self.sego.name
        s="%s @%s: " % (format(self.name,"<5s"),format(segname,"<5s"))
        for x in self.in_sections:
            s="%s%s(%s)," % (s,x.name,x.seq)
        return s[:-1]
    def add(self,section):
        self.in_sections.append(section)
    def lds(self):
        self.ldso=lds_out(self.name,\
            address=self.addr,\
            align=self.align,\
            region=self.sego.area.name,\
            phdr=self.sego.name,\
            fill=None)
           
class discard(section_out):
    def __init__(self):
        section_out.__init__(self,"/DISCARD/","/DISCARD/")
        self.discard=True
        self.segment="/DISCARD/"
        self.sego=iplelf.segments[self.segment]
    def lds(self):
        self.ldso=lds_out(self.name,\
            address=None,\
            align=None,\
            region=None,\
            phdr=None,\
            fill=None)

class segment(object):
    def __init__(self,name,ptype="PT_LOAD",sections=[],pflags=None):
        self.name=name          # segment name
        self.sections=sections  # sections contributing to this segment
        self.p_flag=pflags      # Segment permissions flags
        self.p_type=ptype       # Segment type
        self.present=False
        self.area=None    # assigned storage area
        self.assigned=[]  # sections assigned to this segment
        iplelf.segments[self.name]=self
        self.ldso=None    # lds factory instance created by lds method
    def __str__(self):
        p=" "
        area=None
        flags="None"
        if self.present:
            p="*"
        if self.area!=None:
            area=self.area.name
        if self.p_flag!=None:
            flags="0x%08X" % self.p_flag
        s="%s %s p_flag(%s) @%s: " % (format(self.name,"<5s"),p,flags,area)
        for x in self.assigned:
            s="%s%s," % (s,x.name)
        return s[:-1]
    def lds(self):
        self.ldso=lds_phdr(self.name,type=self.p_type,flags=self.p_flag)

class sort(object):
    @staticmethod
    def compare(a,b):
        if a.seq<b.seq:
            return -1
        if a.seq>b.seq:
            return 1
        if a.pos<b.pos:
            return -1
        if a.pos>b.pos:
            return 1
        return 0
    def __init__(self,seq,pos,obj):
        self.seq=seq
        self.pos=pos
        self.obj=obj
    def __cmp__(self,other):
        # For Python 3.0 convert this to __lt__ method
        if self.seq<other.seq:
            return -1
        if self.seq>other.seq:
            return 1
        if self.pos<other.pos:
            return -1
        if self.pos>other.pos:
            return 1
        return 0

def parse_args():
    parser=argparse.ArgumentParser(\
        description="preprocess an IPL ELF object file for linking")
    parser.add_argument("objfile",\
        help="ELF object file preprocessed",nargs=1)
    parser.add_argument("--lds",\
        help="generated ld linker script",required=True)
    parser.add_argument("--entry",\
        help="ELF executable entry point")
    parser.add_argument("--load",dest="addr",\
        help="TEXT or ELF load point (hex)")
    parser.add_argument("--relo",action="store_true",default=False,\
        help="enable self relocation")
    parser.add_argument("--debug",action="store_true",default=False,\
        help="enable debuging information")
    return parser.parse_args()   

if __name__=="__main__":
    pp=LDPP(parse_args())
    pp.generate(debug=True)
    