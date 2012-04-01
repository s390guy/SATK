#!/usr/bin/python
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

# This module is intended to be imported for use by other modules
import struct
import sys

# This modules can not be migrated to Python 3.0 or greater until
# a 3.0+ struct module exists.

# The ABI and its two subclasses, ABI32 and ABI64, understand the structure 
# of the two different ELF formats: 32-bit and 64-bit.
#
# The meaning of the fields are the same.  The understanding of the field contents
# and usage are represented by the ELF related classes:
#
# ELF - The ELF file structure
#    Ident - The ELF identification field
#    Header - The ELF header
#    Table - Generic ELF table super class
#        ProgTbl - The Program table
#            Prog - Individual entries of the program table
#        DynamicTbl - Dynamic linkage table
#            DynamicEntry - Dynamic linkage table entry
#        RelaTbl - Relocation table
#            RelaEntry - A .rela entry
#        SectTbl - The Section table
#            Section - An actual section
#        StringTbl - A special section containing strings
#        SymTbl - Symbol table
#            SymEntry - Symbol table entry

class ABI(object):
   # This class documents the generic structure of ABI elements
   # The two subclasses, ABI32 and ABI64, tailer the generic definition for
   # The constructor argument is the ELF file as a string
   ident_size=16
   # These structures have the same type of fields and sequence in both ABI's
   HEADER=["Half","Half","Word","Addr","Off","Off","Word",\
           "Half","Half","Half","Half","Half","Half"]
   def endian(ident):
      # This function accpets as input:
      #   An Ident instance
      #   A raw string of an ELF file's ident area
      #   A string "big" for big-endian
      #   A string "little" for little-endian
      #   A string "host" for same as host
      #   A value of 0 for same as host
      #   A value of 1 for little-endian
      #   A value of 2 for big-endian
      # It returns the appropriate struct endianness format character
      # A ValueError is raised if none of these are found
      if isinstance(ident,type("")):
          if len(ident)==ABI.ident_size:
              indxo=Ident(ident)
              indx=ident.endian
          elif ident=="big":
              indx=2
          elif ident=="little":
              indx=1
          elif ident=="host":
              indx=0
          else:
              raise ValueError("Invalid endian string: %s" % ident)
      elif isinstance(ident,Ident):
          indx=ident.endian
      elif isinstance(ident,type(0)):
          if (ident<0 or ident>2):
              raise ValueError("Invalid endian value: %s" % ident)
          else:
              indx=ident
      else:
          raise ValueError("Invalid endian argument %s" % ident)
      return "@<>"[indx]
   endian=staticmethod(endian)
   def isELF(elf_file):
       if len(elf_file)<ABI.ident_size:
           return False
       string=ABI._get_ident(elf_file)
       version=ord(elf_file[6])   # must be 1
       magic=elf_file[0:4]
       if magic!=ABI.magic or version!=1:
           return False
       arch=ord(string[4])      # 1=32-bit, 2= 64-bit
       endian=ord(string[5])    # 1=little, 2=big
       return Ident(arch,endian)
   isELF=staticmethod(isELF)
   def gen_formats(endian,filename):
      abi32=ABI(endian,False)
      abi64=ABI(endian,True)
      string=""
      string='%s%s="%s"\n' % (string,"abi32_header",abi32.header.fmt)
      string='%s%s="%s"\n' % (string,"abi32_section",abi32.section.fmt)
      string='%s%s="%s"\n' % (string,"abi32_program",abi32.program.fmt)
      string='%s%s="%s"\n' % (string,"abi32_dynamic",abi32.dynamic.fmt)
      string='%s%s="%s"\n' % (string,"abi32_rel",abi32.rel.fmt)
      string='%s%s="%s"\n' % (string,"abi32_rela",abi32.rela.fmt)
      string='%s%s="%s"\n' % (string,"abi32_sym",abi32.sym.fmt)
      string='%s%s="%s"\n' % (string,"abi64_header",abi64.header.fmt)
      string='%s%s="%s"\n' % (string,"abi64_section",abi64.section.fmt)
      string='%s%s="%s"\n' % (string,"abi64_program",abi64.program.fmt)
      string='%s%s="%s"\n' % (string,"abi64_dynamic",abi64.dynamic.fmt)
      string='%s%s="%s"\n' % (string,"abi64_rel",abi64.rel.fmt)
      string='%s%s="%s"\n' % (string,"abi64_rela",abi64.rela.fmt)
      string='%s%s="%s"\n' % (string,"abi64_sym",abi64.sym.fmt)
      fo=open(filename,"wt")
      fo.write(string)
      fo.close()
   gen_formats=staticmethod(gen_formats)
   def ident(elf_file):
      return [elf_file[:4],
              ord(elf_file[4]),
	          ord(elf_file[5]),
	          ord(elf_file[6]),
              ord(elf_file[7]),
	          ord(elf_file[8])
	         ]
   ident=staticmethod(ident)
   def select(ident,is64=False):
      if isinstance(ident,Ident) and ident.is64() or is64:
	 #print ident #ident.is64():
         return ABI64(ident)
      else:
         return ABI32(ident)
   select=staticmethod(select)
   def __init__(self,ident):
       # Each of these will be initialized by the subclass
       self.abi=None
       self.header=None
       self.section=None
       self.program=None
       self.dynamic=None
       self.rel=None
       self.rela=None
       self.symbol=None
   def rela_info(self,sym,typ):
       raise NotImplementedError("class %s must provide rela_info method" \
           % self.__class__.__name__)
   def rela_sym(self,value):
       raise NotImplementedError("class %s must provide rela_sym method" \
           % self.__class__.__name__)
   def rela_typ(value):
       raise NotImplementedError("class %s must provide rela_type method" \
           % self.__class__.__name__)
   def sym_bind(self,value):
       return value>>4
   def sym_info(self,bind,typ):
       return (bind<<4)+(typ & 0xF)
   def sym_type(self,value):
       return value & 0xF
   def unpkdyn(self,dyn):
       return self.dynamic.unpack(dyn)
   def unpkhdr(self,hdr):
       return self.header.unpack(hdr)
   def unpkpgm(self,pgm):
       flds=self.program.unpack(pgm)
       return self.pgmorder(flds)
   def unpkrela(self,rela):
       return self.rela.unpack(rela)
   def unpksct(self,sct):
       return self.section.unpack(sct)
   def unpksym(self,sym):
       return self.symbol.unpack(sym)


class ABI32(ABI):
   STRUCT={"Addr":"L","Half":"H","Off":"L","Sword":"i","Word":"L","Char":"B"}
   SECTION=["Word","Word","Word","Addr","Off","Word","Word","Word","Word","Word"]
   PROGRAM=["Word","Off","Addr","Addr","Word","Word","Word","Word"]
   DYNAMIC=["Sword","Word"]
   REL=["Addr","Word"]
   RELA=["Addr","Word","Sword"]
   SYM=["Word","Addr","Word","Char","Char","Half"]
   def __init__(self,ident,is64=False):
       ABI.__init__(self,ident)
       self.endian=ABI.endian(ident)
       self.header=ABIFMT(ABI.HEADER,self,"ABI32 ELF Header")
       self.section=ABIFMT(ABI32.SECTION,self,"ABI32 Section Header")
       self.program=ABIFMT(ABI32.PROGRAM,self,"ABI32 Program Header")
       self.dynamic=ABIFMT(ABI32.DYNAMIC,self,"ABI32 Dynamic Entry")
       self.rel=ABIFMT(ABI32.REL,self,"ABI32 Rel Entry")
       self.rela=ABIFMT(ABI32.RELA,self,"ABI32 Rela Entry")
       self.symbol=ABIFMT(ABI32.SYM,self,"ABI32 Symbol Entry")
   def pgmorder(self,fields):
       return fields
   def rela_info(self,sym,typ):
       return (sym<<8)+(typ & 0xFF)
   def rela_sym(self,value):
       return value>>8
   def rela_type(self,value):
       return value & 0xFF
   def symorder(self,fields):
       return fields

class ABI64(ABI):
   STRUCT={"Addr":"Q","Half":"H","Off":"Q","Sword":"l","Word":"L","Char":"B",\
           "Xword":"Q","Sxword":"q"}
   SECTION=["Word","Word","Xword","Addr","Off","Xword","Word","Word",\
            "Xword","Xword"]
   PROGRAM=["Word","Word","Off","Addr","Addr","Xword","Xword","Xword"]
   PGMORDER=[0,6,1,2,3,4,5,7]
   DYNAMIC=["Sxword","Xword"]
   REL=["Addr","Xword"]
   RELA=["Addr","Xword","Sxword"]
   SYM=["Word","Char","Char","Half","Addr","Xword"]
   SYMORDER=[0,3,4,5,1,2]
   def __init__(self,ident,is64=True):
       ABI.__init__(self,ident)
       self.endian=ABI.endian(ident)
       self.header=ABIFMT(ABI.HEADER,self,"ABI64 ELF Header")
       self.section=ABIFMT(ABI64.SECTION,self,"ABI64 Section Header")
       self.program=ABIFMT(ABI64.PROGRAM,self,"ABI64 Program Header")
       self.dynamic=ABIFMT(ABI64.DYNAMIC,self,"ABI64 Dynamic Entry")
       self.rel=ABIFMT(ABI64.REL,self,"ABI64 Rel Entry")
       self.rela=ABIFMT(ABI64.RELA,self,"ABI64 Rela Entry")
       self.symbol=ABIFMT(ABI64.SYM,self,"ABI64 Symbol Entry")
   def pgmorder(self,fields):
       res=[0,0,0,0,0,0,0,0]
       for x in range(len(ABI64.PGMORDER)):
           res[ABI64.PGMORDER[x]]=fields[x]
       return res
   def rela_info(self,sym,typ):
       return (sym<<32)+(typ & 0xFFFFFFFF)
   def rela_sym(self,value):
       return value>>32
   def rela_type(self,value):
       return value & 0xFFFFFFFF
   def symorder(self,fields):
       res=[0,0,0,0,0,0]
       for x in range(len(ABI64.SYMORDER)):
           res[ABI64.SYMORDER[x]]=fields[x]
       return res

class ABIFMT(object):
   def bldfmt(fmt,abi):
      struct=abi.__class__.STRUCT
      string=""
      for x in fmt:
          try:
              string+=struct[x]
          except KeyError:
               string+=x
      return abi.endian+string
   bldfmt=staticmethod(bldfmt)
   def __init__(self,fmt,abi,name):
      self.name=name
      self.fmt=ABIFMT.bldfmt(fmt,abi)
      self.size=struct.calcsize(self.fmt)
   def unpack(self,bytes):
      if len(bytes)!=self.size:
	 # print "struct format: %s" % self.fmt
          raise ValueError(\
              "Required size for %s format %s is %s, encountered: %s"\
	      % (self.name,self.fmt,self.size,len(bytes)))
      return struct.unpack(self.fmt,bytes)

class display(object):
   # Utility for displaying fields
   def string(flds):
      disp=""
      for x in flds:
          disp="%s%s\n" % (disp,x.fmt())
      return disp[:-1]
   string=staticmethod(string)
   def __init__(self,name,format,value):
      self.name=name
      self.format=format
      self.value=value
   def fmt(self):
      fmt="%s="+"%"+self.format
      try:
          return fmt % (self.name,self.value)
      except TypeError as err:
          print "Problem printing %s" % self.name
          raise err

class elf(object):
   # Ident Architecture
   bit32=1
   bit64=2
   # Ident Endianess
   little_endian=1
   big_endian=2
   # Header Machine Ids
   s370=9
   s390=22
   # Header Types
   relocatable=1
   executable=2
   shared=3
   core=4
   def hexchar(s):
      x=""
      for c in s:
          x="%s %s" % (x,hex(ord(c)))
      return x
   hexchar=staticmethod(hexchar)
   def __init__(self,flnm,ostypes=None,proctypes=None):
      self.name=flnm
      self.segtyps={0:"NULL",1:"LOAD",2:"DYNAMIC",3:"INTERP",4:"NOTE",\
                    5:"SHLIB",6:"PHDR",7:"TLS"}
      if ostypes!=None:
          self.segtyps.update(ostypes)
      if proctypes!=None:
          self.segtyps.update(proctypes)
      if isinstance(flnm,elf_source):
          self.fil=flnm.getObject()
      else:
          s=elf_source(filename=flnm)
          self.fil=s.source
      self.ident=Ident(self.fil)
      self.ABI=ABI.select(self.ident)
      self.header=Header(self)
      self.SctTbl=self.header.getSectionTable()
      self.strings=self.SctTbl.getStringTable()
      self.PgmTbl=self.header.getProgramTable()
   def __getitem__(self,key):
      return self.SctTbl.fetchSection(key)
   def bytes(self,offset,bytes):
      return self.fil[offset:offset+bytes]
   def elfis(self,mach,arch,endian,typ):
      return mach==self.header.machine and \
             arch==self.ident.arch and \
	         endian==self.ident.endian and \
	         typ==self.header.typ
   def findProgramType(self,n):
      return self.PgmTbl.findSegment(n)
   def getEntry(self):
      return self.header.entry
   def getProgram(self,n):
      self.PgmTbl.fetchProgram(n)
   def getProgramStart(self,n):
      pgm=self.getProgram(n)
      return pgm.virt_addr
   def getSection(self,section):
      if isinstance(section,type("")):
          return self.SctTbl.fetchSection(section)
      return self.SctTbl.fetchSectionNumber(section)
   def getDataSegment(self):
      data=self.PgmTbl.data
      if data==None:
          return None
      return data
   def getTextSegment(self):
      text=self.PgmTbl.text
      if text==None:
          return None
      return text
   def isexec(self):
       return self.header.typ==elf.executable
   def iss370(self):
       return self.header.machine==elf.s370
   def is64(self):
      return self.ident.arch==elf.bit64
   def prt(self,details=False):
      print "--Ident--"
      print self.ident
      print "--Header--"
      print self.header
      print "--Section Table--"
      self.SctTbl.prtNumbers()
      if details:
          self.SctTbl.prtDetail()
      print "--Program Table--"
      self.PgmTbl.prtSegments()
      if details:
          self.PgmTbl.prtDetail()
   def write(self,sectn,filename,pad=1):
      if pad<1:
          raise ValueError("Padding must not be less than 1: %s" % pad)
      written=0
      data=self.data(sectn)
      padlen=len(data)%pad
      if padlen!=0:
          padlen=pad-padlen
      padchar=padlen*chr(0)
      out=open(filename,"wb")
      out.write(data)
      written=len(data)
      out.write(padchar)
      written+=len(padchar)
      out.close()
      return written
   def __str__(self):
      endian=["Invalid","little","big"]
      endian=endian[self.ident.endian]
      arch=["Invalid","32","64"]
      arch=arch[self.ident.arch]
      return "%s-bit %s-endian ELF" % (arch,endian)
      
class elf_source(object):
   def __init__(self,**kwds):
      if "filename" in kwds:
         self.getfile(kwds["filename"])
      else:
         self.source=kwds["string"]
   def getfile(self,flnm):
      try:
          fo=open(flnm,"rb")
          self.source=fo.read()
          fo.close()
      except IOError:
          raise ValueError("could not open input file: %s" % flnm)
   def getObject(self):
      return self.source

class Header(object):
   types=["None","Relocatable","Executable","Shared Object","Core"]
   mach={elf.s370:"S/370",elf.s390:"S/390"}
   def __init__(self,elf):
      self.elf=elf
      self.size=self.elf.ABI.header.size
      fields=self.decode()
      self.typ=fields[0]        # Type of ELF file
      self.machine=fields[1]    # Machine identification
      self.version=fields[2]    # ELF Version
      self.entry=fields[3]      # Entry point
      self.phoff=fields[4]      # Program's header table's offset
      self.shoff=fields[5]      # Program's section header table offset
      self.flags=fields[6]      # Processor specific flags
      self.ehsize=fields[7]     # ELF header's size in bytes
      self.phentsize=fields[8]  # Size of one entry in the program header table
      self.phnum=fields[9]      # Number of entries in the program header table
      self.shentsize=fields[10] # Section header size in bytes
      self.shnum=fields[11]     # Number of entries in the section header table
      self.shstrndx=fields[12]  # Section header table index of section name table
   def decode(self):
      hdr=self.elf.bytes(ABI.ident_size,self.size)
      return self.elf.ABI.unpkhdr(hdr)
   def getProgramTable(self):
      return ProgTbl(self.elf,
                     self.phoff,\
                     self.phnum,\
                     self.phentsize)
   def getSectionTable(self):
      return SectTbl(self.elf,
                     self.shoff,\
                     self.shnum,\
                     self.shentsize,
		     self.shstrndx)
   def getStringIndex(self):
      return self.shstrndx
   def __str__(self):
      try:
          typ=Header.types[self.typ]
      except KeyError:
          typ="%X" % self.typ
      try:
          machine=Header.mach[self.machine]
      except KeyError:
          machine=self.machine
      fields=[display("type","s",typ),
              display("machine","s",machine),
	      display("version","s",self.version),
	      display("entry (hex)","X",self.entry),
	      display("phoff","s",self.phoff),
	      display("shoff","s",self.shoff),
	      display("flags (hex)","X",self.flags),
	      display("ehsize","s",self.ehsize),
	      display("phentsize","s",self.phentsize),
	      display("phnum","s",self.phnum),
	      display("shentsize","s",self.shentsize),
	      display("shnum","s",self.shnum),
	      display("shstndx","s",self.shstrndx)\
	     ]
      return display.string(fields)

class Ident(object):
   magic="\x7fELF"
   def __init__(self,elf_file):
      if len(elf_file)<ABI.ident_size:
         raise ValueError("Not ELF - Too small") 
      fields=ABI.ident(elf_file)
      self.magic=fields[0]
      self.arch=fields[1]     # +4 1=32-bit, 2=64-bit
      self.endian=fields[2]   # +5 1=little, 2=big
      self.version=fields[3]  # +6 Must be 1
      self.osabi=fields[4]    # +7 OS specific ABI
      self.osabiver=fields[5] # +8 OS specific ABI version
      if not self.isELF():
         raise TypeError("Not ELF - Invalid identification")
   def is64(self):
      return self.arch==2
   def isELF(self):
     if self.magic!=Ident.magic or self.version!=1:
         return False
     return True
   def __str__(self):
      fields=\
        [display("MAG0",       "X",ord(self.magic[0])),
         display("MAG1",       "s",self.magic[1]),
	     display("MAG2",       "s",self.magic[2]),
	     display("MAG3",       "s",self.magic[3]),
	     display("class",      "s",32*self.arch),
	     display("encoding",   "s",["?","2LSB (litle)","2MSB (big)"][self.endian]),
	     display("ABI version","s",self.version),
	     display("OS ABI",     "s",self.osabi),
	     display("OS version", "s",self.osabiver)]
      return display.string(fields)

class DynamicEntry(object):
   types=["DT_NULL","DT_NEEDED","DT_PLTRELSZ","DT_PLTGOT","DT_HASH",\
          "DT_STRTAB","DT_SYMTAB","DT_RELA","DT_RELASZ","DT_RELAENT",\
	      "DT_STRSZ","DT_SYMENT","DT_INIT","DT_FINI","DT_SONAME",\
	      "DT_RPATH","DT_SYMBOLIC","DT_REL","DT_DEBUG","DT_TEXTREL",\
	      "DT_JMPREL","DT_BIND_NOW","DT_INIT_ARRAY","DT_FINI_ARRAY",\
	      "DT_INIT_ARRAYSZ","DT_FINI_ARRAYSZ","DT_RUNPATH","DT_FLAGS",\
	      "DT_ENCODING","DT_PREINIT_ARRAY","DT_PREINIT_ARRAYSZ"]
   uns={"DT_NULL":"ignored",\
        "DT_NEEDED":"val",\
	    "DT_PLTRELSZ":"val",\
	    "DT_PLTGOT":"ptr",\
	    "DT_HASH":"ptr",\
	    "DT_STRTAB":"ptr",\
	    "DT_SYMTAB":"ptr",\
	    "DT_RELA":"ptr",\
	    "DT_RELASZ":"val",\
	    "DT_RELAENT":"val",\
	    "DT_STRSZ":"val",\
	    "DT_SYMENT":"val",\
	    "DT_INIT":"ptr",\
	    "DT_FINI":"ptr",\
	    "DT_SONAME":"val",\
	    "DT_RPATH":"val",\
	    "DT_SYMBOLIC":"ignored",\
	    "DT_REL":"ptr",\
	    "DT_DEBUG":"ptr",\
	    "DT_TEXTREL":"ignored",\
	    "DT_JMPREL":"ptr",\
	    "DT_BIND_NOW":"ignored",\
	    "DT_INIT_ARRAY":"ptr",\
	    "DT_FINI_ARRAY":"ptr",\
	    "DT_INIT_ARRAYSZ":"val",\
	    "DT_FINI_ARRAYSZ":"val",\
	    "DT_RUNPATH":"val",\
	    "DT_FLAGS":"val",\
	    "DT_ENCODING":"val",\
	    "DT_PREINIT_ARRAY":"ptr",\
	    "DT_PREINIT_ARRAYSZ":"val",
	    "DT_OS":"un",\
	    "DT_PROC":"un",\
	    "unknown":"un"}
   def __init__(self,pgmhdr,entry):
      self.pgmhdr=pgmhdr
      self.elf=self.pgmhdr.elf
      fields=self.elf.ABI.unpkdyn(entry)
      self.tag=fields[0]
      self.un=fields[1]
      if self.tag>=0x6000000D and self.tag<=0x6FFFF000:
         self.tagstr="DT_OS"
      elif self.tag>=0x70000000 and self.tag<=0x7FFFFFFF:
         self.tagstr="DT_PROC"
      elif self.tag>=0 and self.tag<=33:
         self.tagstr=DynamicEntry.types[self.tag]
      else:
         self.tagstr="unknown"
      self.unstr=DynamicEntry.uns[self.tagstr]
   def __str__(self):
      if self.tag<=33:
         tag="%s" % self.tag
      else:
         tag="%s" % hex(self.tag)
      if self.unstr=="val":
         un="%s" % self.un
      else:
         un="%s" % hex(self.un)
      return "%s %s : %s (%s)" % (tag,self.tagstr,un,self.unstr)

class Program(object):
   def __init__(self,elf,pgmhdr,ndx):
      self.elf=elf
      self.index=ndx
      fields=self.elf.ABI.unpkpgm(pgmhdr)
      self.typ=fields[0]
      self.offset=fields[1]
      self.virt_addr=fields[2]
      self.phys_addr=fields[3]
      self.file_size=fields[4]
      self.mem_size=fields[5]
      self.flags=fields[6]
      self.align=fields[7]
      self.data=self.fetch()
      self.isexec=(0!=(self.flags & 0x01))
      self.isread=(0!=(self.flags & 0x04))
      self.iswrite=(0!=(self.flags & 0x02))
      self.isdata=self.isread and self.iswrite
      self.istext=self.isread and self.isexec
      if self.typ==2:
         self.content=DynamicTable(self)
      else:
         self.content=None
   def fetch(self):
      data=self.elf.bytes(self.offset,self.file_size)
      if self.mem_size>self.file_size:
         data="%s%s" % (data,(self.mem_size-self.file_size)*"\x00")
      return data
   def load(self):
      return self.virt_addr
   def prtContent(self):
      return "%s" % self.content
   def typs(self):
      try:
         return self.elf.segtyps[self.typ]
      except KeyError:
         if self.typ>=0x60000000 and self.typ<=0x6FFFFFFF:
            return "OS(%08X)" % self.typ
         elif self.typ>=0x70000000 and self.typ<=0x7FFFFFFF:
            return "Proc(%08X)" % self.typ
         else:
            return "Unknown(08X)" % self.typ
   def __str__(self):
      fields=[display("type","s",self.typs()),
              display("offset","s",self.offset),
	      display("virtual address (hex)","X",self.virt_addr),
	      display("physical address (hex)","X",self.phys_addr),
	      display("file size (hex)","X",self.file_size),
	      display("memory size (hex)","X",self.mem_size),
	      display("flags (hex)","02X",self.flags),
	      display("alignment","s",self.align),
	      display("execute","s",self.isexec),
	      display("read","s",self.isread),
	      display("write","s",self.istext),
	      display("Data Segment","s",self.isdata),
	      display("Text Segment","s",self.istext)\
	     ]
      return display.string(fields)

class Section(object):
   types=["NULL","PROGBITS","SYMTAB","STRTAB","RELA","HASH","DYNAMIC","NOTE",
          "NOBITS","REL","SHLIB","DYNSYM","INIT_ARRAY","FINI_ARRAY",
	  "PREINIT_ARRAY","GROUP","SYMTAB_SHNDX"]
   def __init__(self,elf,sechdr,index):
       self.elf=elf
       self.index=index
       fields=self.elf.ABI.unpksct(sechdr)
       self.namndx=fields[0]
       self.typ=fields[1]
       self.flags=fields[2]
       self.addr=fields[3]
       self.offset=fields[4]
       self.size=fields[5]
       self.link=fields[6]
       self.info=fields[7]
       self.addralign=fields[8]
       self.entry_size=fields[9]
       self.name=""
       self.data=self.fetch()
       self.content=None
       if self.typ==2:
           self.content=SymTbl(\
               self.elf,self.link,self.offset,self.size,self.elf.ABI)
       if self.typ==3:
           self.content=StringTable(self.data)
       if self.typ==4:
           self.content=RelaTbl(\
               self.elf,self.link,self.info,self.offset,self.size,self.elf.ABI)
          
   def fetch(self):
      # This function extracts the section's data content from the file.
      if self.typ==0 or self.typ==8:   # No data if the SHT_NULL or SHT_NOBITS type.
          return ""
      if self.size==0:
          return ""
      return self.elf.bytes(self.offset,self.size)
   def getString(self,index):
      if not isinstance(self.content,StringTable):
         return None
      return self.content.getString(index)
   def setName(self,str_sect):
      string=str_sect.getString(self.namndx)
      self.name=str_sect.getString(self.namndx)
   def __str__(self):
      try:
         typ=Section.types[self.typ]
      except IndexError:
         typ="%X" % set.typ
      fields=[display("type",       "s",  typ),
              display("index",      "s",  self.index),
              display("name",       "s",  self.name),
              display("namndx",     "s",  self.namndx),
              display("type",       "s",  typ),
	          display("flags (hex)","03X",self.flags),
	          display("addr (hex)", "X",  self.addr),
	          display("offset",     "s",  self.offset),
	          display("size (hex)", "X",  self.size),
	          display("link",       "s",  self.link),
	          display("info",       "s",  self.info),
	          display("addralign",  "s",  self.addralign),
	          display("entry_size", "s",  self.entry_size)]
      return display.string(fields)

class StringTable(object):
   def __init__(self,data):
      self.data=data
   def getString(self,index):
      x=index
      name=""
      if index>=len(self.data):
         raise ValueError("index beyond end of string table (%s): %s" % \
	                  (len(self.data),index))
      while x<len(self.data):
         byte=self.data[x]
         if byte=="\x00":
            return name
         x+=1
         name+=byte
      return name
	 
class Table(object):
   def __init__(self,elf,offset,entries,entsize):
      #print "Table.__init__(offset=%s,entries=%s,entsize=%s)" \
      #    % (offset,entries,entsize)
      self.array=[]  # Array of raw binary entries
      if entsize==0:
         return
      for x in range(offset,offset+(entries*entsize),entsize):
         data=elf.bytes(x,entsize)
         self.array.append(data)
   def __getitem__(self,ndx):
      return self.array[ndx]
      
class DynamicTable(Table):
   types=["DT_NULL","DT_NEEDED","DT_PLTRELSZ","DT_PLTGOT","DT_HASH",\
          "DT_STRTAB","DT_SYMTAB","DT_RELA","DT_RELASZ","DT_RELAENT",\
	  "DT_STRSZ","DT_SYMENT","DT_INIT","DT_FINI","DT_SONAME",\
	  "DT_RPATH","DT_SYMBOLIC","DT_REL","DT_DEBUG","DT_TEXTREL",\
	  "DT_JMPREL","DT_BIND_NOW","DT_INIT_ARRAY","DT_FINI_ARRAY",\
	  "DT_INIT_ARRAY","DT_FINI_ARRAY","DT_INIT_ARRAYSZ",\
	  "DT_FINI_ARRAYSZ","DT_RUNPATH","DT_FLAGS","DT_ENCODING",\
	  "DT_PREINIT_ARRAY","DT_PREINIT_ARRAYSZ"]
   def __init__(self,pgmhdr):
      self.pgm=pgmhdr
      self.elf=pgmhdr.elf
      self.entsize=self.elf.ABI.dynamic.size
      self.offset=pgmhdr.offset
      self.num_entries=len(pgmhdr.data)//self.entsize
      self.entries=[]  # Array of decoded entries
      Table.__init__(self,self.elf,self.offset,self.num_entries,self.entsize)
      for x in self.array:
          self.entries.append(DynamicEntry(self.pgm,x))
   def __str__(self):
      x=""
      for y in self.entries:
          x="%s\n%s" % (x,y)
      return x

class ProgTbl(Table):
   types=["NULL","LOAD","DYNAMIC","INTERP","NOTE","SHLIB","PHDR","TLS"]
   def __init__(self,elf,offset,entries,entsize):
      Table.__init__(self,elf,offset,entries,entsize)
      self.elf=elf
      self.entries=[]  # Array of decoded entries
      self.data=None   # Data segment number
      self.text=None   # Text segment number
      for x in range(len(self.array)):
         entry=self.array[x]
         self.entries.append(Program(self.elf,entry,x))
      for x in self.entries:
         if x.isdata and self.data==None:
            self.data=x
         if x.istext and self.text==None:
            self.text=x
   def fetchSegment(self,n):
      segment=self.getSegment(n)
      return segment.fetch()
   def findSegment(self,typ):
      for x in range(self.entries):
         seg=self.entries[x]
         if seg.typ==typ:
            return x
      return None
   def getSegment(self,n):
      return self.entries[n]
   def getSegmentLoad(self,n):
      segment=self.getSegment(n)
      return segment.load()
   def prtDetail(self):
      print "--Program Table Detail--" 
      for x in range(len(self.entries)):
         print "--Program Table Entry %s--" % x 
         pgm=self.entries[x]
         print pgm 
         print "--Program Table Content %s--" % x 
         print pgm.prtContent() 
   def prtSegments(self):
      for x in range(len(self.entries)):
         pgm=self.entries[x]
         begin=pgm.virt_addr
         if pgm.mem_size>0:
            end=pgm.virt_addr+pgm.mem_size-1
         else:
            end=begin
         print "%s %s %X-%X" % (x,pgm.typs(),begin,end) 

class RelaEntry(object):
     def __init__(self,rela,resndx,abi,exe=False):
         self.resndx=resndx
         self.exe=exe
         fields=abi.unpkrela(rela)
         self.offset=fields[0]
         self.info=fields[1]
         self.addend=fields[2]
         self.typ=abi.rela_type(self.info)
         self.sym=abi.rela_sym(self.info)
     def __str__(self):
         if self.exe:
             return "Info(0x%X) SYMTAB NDX(%s) type(%s) address(0x%X) addend(0x%X)" \
                 % (self.info,self.sym,self.typ,self.offset,self.addend)
         return "Info(0x%X) SYMTAB NDX(%s) type(%s) offset(0x%X) addend(0x%X)" \
             % (self.info,self.sym,self.typ,self.offset,self.addend)

class RelaTbl(Table):
    def __init__(self,elf,symtabndx,resndx,offset,size,abi):
        self.elf=elf                  # elf instance
        self.symtabndx=symtabndx      # SYMTAB section index
        self.resndx=resndx            # Relocation residence section index
        self.tbloffset=offset         # Offset of RELA table in ELF
        self.tblsize=size             # Size of RELA table in bytes
        self.rela=abi.rela            # ABI RELA instance
        self.relasize=self.rela.size  # Size of individual RELA entry
        Table.__init__(self,elf,offset,\
            self.tblsize//self.relasize,self.relasize)
        self.entries=[]               # Array of actual decoded Rela entries
        for x in self.array:
            self.entries.append(RelaEntry(x,self.resndx,abi,elf.isexec()))
    def __str__(self):
        string="RELA Table:"
        for x in self.entries:
            string="%s\n%s" % (string,x)
        return string

class SectTbl(Table):
   def __init__(self,elf,offset,entries,entsize,strndx):
      Table.__init__(self,elf,offset,entries,entsize)
      self.entries=[]  # Array of actual decoded sections
      self.strndx=strndx
      #print "strndx: %s" % strndx
      for x in range(len(self.array)):
	  #print "SectTbl index: %s" % x
          self.entries.append(Section(elf,self[x],x))
      self.names=self.setNames(self.entries[self.strndx])
   def fetchSection(self,name):
      return self.getSection(name).data
   def fetchSectionNumber(self,n):
      return self.entries[n].data
   def getSection(self,name):
      return self.entries[self.names[name]]
   def getString(self,ndx):
      return self.getStringTable().getString(ndx)
   def getStringTable(self):
      return self.entries[self.strndx]
   def prtDetail(self):
      print "--Section Table Detail--" 
      for x in range(len(self.entries)):
         print "--Section Table Entry %s--" % x 
         print self.entries[x]
   def prtNames(self):
      names=self.names.keys()
      names.sort()
      for x in names:
         print "%s %s" % (self.names[x],x)
   def prtNumbers(self):
      for x in range(len(self.entries)):
         print "%s %s" % (x,self.entries[x].name)
   def setNames(self,str_sect):
      names={}
      for x in range(len(self.array)):
         sect=self.entries[x]
         sect.setName(str_sect)
         names[sect.name]=x
      return names
      
class SymEntry(object):
    shndx={}
    binding={0:"LOCAL",
             1:"GLOBAL",
             2:"WEAK"}
    types={0:"NOTYPE",
           1:"OBJECT",
           2:"FUNC",
           3:"SECTION",
           4:"FILE",
           5:"COMMON",
           6:"TLS"}
    visibility={0:"DEFAULT",
                1:"INTERNAL",
                2:"HIDDEN",
                3:"PROTECTED"}
    def init():
        for x in range(0xff00,0xFF1F,1):
            SymEntry.shndx[x]="processor specific"
        for x in range(0xFF20,0xFF3F,1):
            SymEntry.shndx[x]="OS specific"
        for x in range(0xFF40,0xFFFF,1):
            SymEntry.shndx[x]="reserved"
        SymEntry.shndx[0]="UNDEF"
        SymEntry.shndx[0xFFF1]="ABSOLUTE"
        SymEntry.shndx[0xFFF2]="COMMON"
        SymEntry.shndx[0xFFFF]="XINDEX"
        for x in [10,11,12]:
            SymEntry.binding[x]="OS binding"
            SymEntry.types[x]="OS type"
        for x in [13,14,15]:
            SymEntry.binding[x]="Proc binding"
            SymEntry.types[x]="Proc type"
    init=staticmethod(init)
    def __init__(self,stringndx,sym,abi):
        self.stringndx=stringndx
        fields=abi.unpksym(sym)
        self.namndx=fields[0]  # Index into string table of symbol's name
        self.value=fields[1]   # absolute value, address, etc.
        self.size=fields[2]    # symbol size
        self.info=fields[3]    # binding and type
        self.other=fields[4]   # visibility
        self.secndx=fields[5]  # section table entry index of the symbol
        self.visibility=self.other & 0x3
        self.bind=abi.sym_bind(self.info)
        self.typ=abi.sym_type(self.info)
    def __str__(self):
        try:
            index=SymEntry.shndx[self.namndx]
        except KeyError:
            index="0x%X" % self.namndx
        try:
            typ=SymEntry.types[self.typ]
        except IndexError:
            typ="%X" % self.typ
        try:
            binding=SymEntry.binding[self.bind]
        except KeyError:
            binding="%X" % self.bind
        fields=\
            [display("sect index","s",index),
             display("type","s",typ),
	         display("binding","s",binding),
             display("string table","s",self.stringndx),
             display("name index","s",self.namndx),
	         display("value (hex)","X",self.value),
	         display("size (hex)","X",self.size),
	         display("vis","s",SymEntry.visibility[self.visibility]),]
        return display.string(fields)
SymEntry.init()
      
class SymTbl(Table):
    def __init__(self,elf,stngndx,offset,size,abi):
        self.elf=elf
        self.strngtbl=stngndx        # Section index of string table
        self.offset=offset           # SYMTAB offset in ELF
        self.tblsize=size            # Size of SYMTAB in bytes
        self.sym=abi.symbol          # SYMTAB ABI instance
        self.symsize=self.sym.size   # Size of SYMTAB entry
        Table.__init__(self,elf,offset,self.tblsize//self.symsize,self.symsize)
        self.entries=[] # Array of actual decoded Sym entries
        for x in self.array:
            self.entries.append(SymEntry(self.strngtbl,x,abi))
    def __str__(self):
        string="SYMTAB:"
        for x in ranage(len(self.entries)):
            entry=self.entries[x]
            string="%s\nSYMTAB Entry %s\n%s" % (string,x,entry)
        return string

def write_section(infile,section,outfile,pad=1):
   elf_file=elf(infile)
   bytes=0
   try:
      bytes=elf_file.write(section,outfile,pad)
   except KeyError:
      print "Input file does not contain section: %s" % section 
      return 1
   except ValueError:
      print "Problem with padding, input file or input not ELF: %s" % infile
      return 1
   except IOError:
      print "Problem outputing file: %s" % outfile
      return 1
   print "%s section of ELF %s" % (section,infile)
   print "%s bytes written to file: %s" % (bytes,outfile)
   return 0
   

if __name__ == "__main__":
   #ELF=elf(sys.argv[1])
   #print ELF
   #ELF.prt(True)
   #ret=write_section(sys.argv[1],sys.argv[2],sys.argv[3],padding)
   #sys.exit(ret)
   ABI.gen_formats("big","abi_formats.py")
