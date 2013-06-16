#!/usr/bin/python

# Utility to handle s390 ELF relocatable object and executable files

import PyELF              # Access the generic ELF module
import objutil            # Access the generic object module interface
import sys                # Access to command line arguments
from hexdump import *     # Access to hexdump methods

# Note: this module requires Python 2.6 or greater

# Data relationships
#                                +------------------------------+
#                                V                              |
#    PyELF:    elf ----------> Section -------> RELA -------> Symtab
#               |                V                              |
#               |              StringSection<-------------------+
#               |
#               +------------> Program
#
#    objutil:  module  ------> codearea ------> adcon
#               ^               ^  | ^           |  ^
#               |               |  | +-----------+  |
#               |               |  V                |
#               |               |binders{}          |
#               |               |  ^                |
#               |               |  |                |
#    ELFXO:    elfxo            |  |                |
#               ^               |  |                |
#               |               |  |                |
#               +----elfo ---> sect_code -----> sect_adcon
#               |               ^                ^
#               |               |                |
#               +----elfx ---> pgm_code  -----> pgm_adcon

class elfxo(objutil.module):
    # ELF Section types
    codearea=1
    symtab=2
    stringtbl=3
    rela=4
    # Mapping RELA type to adcon sizes:
    rela32={0:None,1:1,2:2,3:2,4:4,5:4,6:2,7:4,8:4,9:None,10:4,11:None,
        12:4,13:4,14:4,15:2,16:2,17:2,18:2}
    rela64={0:None,1:8,2:2,3:2,4:4,5:4,6:2,7:4,8:4,9:None,10:8,11:None,
        12:8,13:8,14:8,15:2,16:2,17:2,18:2,19:4,20:4,21:4,22:8,23:8,24:8,25:8,
        26:32}
    # This super class is useful in providing functionality common to both 
    # elfo and elfx instances.  In particular it provides common access to 
    # the PyELF.elf instance privided when elfxo is instantiated
    def __init__(self,elf):
        objutil.module.__init__(self)
        self.elf=elf
        if self.elf.is64:
            self.relasizes=elfxo.rela64
        else:
            self.relasizes=elfxo.rela32
        # Strutures needed by elfxo built by buildSectDict
        self.sectdct={}     # Section instances keyed to section table index
        self.sections=[]    # List of PROGBITS sections
        self.relas=[]       # List of RELA sections
        self.syms=[]        # List of SYMTAB sections (needed?)
        # Build the above structures from the PyELF.elf instance
        self.buildSectDict(elfxo.codearea,self.sections)
        self.buildSectDict(elfxo.rela,self.relas)
        self.buildSectDict(elfxo.symtab,self.syms)
        self.buildSectDict(elfxo.stringtbl,None)
        # objutil subclass instances
        self.sectids={}       # sections keyed by local ids (section table index)
        self.sectnames={}     # sections keyed by name
        self.buildCodeAreas() # Create dicts of objutil.codearea instances
        self.buildAdcons()    # Create adcons and connect to resident codearea
    def __str__(self):
        string="PROGBITS: %s, RELA: %s, SYMTAB: %s" \
            % (len(self.sections),len(self.relas),len(self.syms))
        for x in self.sections:
            string="%s\n\n%s" % (string,x)
        for x in self.relas:
            string="%s\n\n%s" % (string,x)
            for y in x.content.entries:
                string="%s\n%s" % (string,y)
        for x in self.syms:
            string="%s\n\n%s" % (string,x)
            for y in range(len(x.content.entries)):
                entry=x.content.entries[y]
                string="%s\n\nSYMTAB Entry %s\n%s" % (string,y,entry)
        return string
    def buildSectDict(self,typ,lst=None):
        # Build the PyELF related structures
        for x in self.elf.SctTbl.entries:
            #section=self.elf.SctTbl[x]
            if x.typ==typ:
                self.sectdct[x.index]=x
                if lst!=None:
                    lst.append(x)
    def buildAdcons(self):
        for x in self.relas:
            # x is a PyELF.Section instance
            relatbl=x.content
            # PyELF.SymTbl instance associated with RELA table
            symtab=self.get(relatbl.symtabndx).content
            # codearea containing the adcons
            code=self.sectids[relatbl.resndx]
            for y in relatbl.entries:         # Process the RELA entries
                syment=symtab.entries[y.sym]  # Get the SYMTAB entry
                code.buildAdcon(y,syment)
    def get(self,sectndx,entry=None):
        # Returns a PyELF.Section instance based upon index, if entry==None or
        # Returns the PyELF instance of an entry in a section.
        try:
            sect=self.sectdct[sectndx]
        except KeyError:
            raise KeyError("unknown section index requested: % %s" % sectndx)
        if entry==None:
            return sect
        if sect.type==elfxo.stringtbl:
            return sect.getString(entry)
        try:
            ent=sect.entries[entry]
        except IndexError:
            raise IndexError("invalid section %s, 0-%s entries: %s" \
                % (sectndx,len(sect.entries-1),entry))
        return ent
    def getRmode(self):
        if self.elf.is64():
            return 64
        if self.elf.header.machine==PyELF.elf.s370:
            return 24
        return 31
    #
    # Methods required of elfxo subclasses
    def buildAdcon(self,rela,symtab):
        # Create and add to my list a single adcon entry
        raise NotImplementedError(\
            "class %s must provide buildAdcon() method" \
            % self.__class__.__name__)
    def buildCodeAreas(self):
        # Create module level dictionaries required by objutil
        raise NotImplementedError(\
            "class %s must provide buildCodeAreas() method" \
            % self.__class__.__name__)
    #
    # These methods are used by objutil to interrogate the object instance.
    # They are common for both 
    def getEntry(self):
        raise NotImplementedError("class %s must provide getEntry method" \
            % self.__class__.__name__)
    def getLocal(self):
        # Return a dictionary of code area objects keyed to their local ids
        return self.sectids
    def getNames(self):
        # Return a dictionary of code area objects keyed to their names
        return self.sectnames
    def getReloEngine(self):
        return elfrelo(self.getRmode())
    def hexdump(self,indent=""):
        # Return a string of the sections' binary contents
        names=self.sectnames.keys()
        names.sort()
        str=""
        newindent="%s%s" % (indent,"    ")
        for x in names:
            sect=self.sectnames[x]
            str="%s%sContents of ID[%s] %s\n%s\n" \
                % (str,indent,\
                sect.sect.index,sect.sect.name,sect.hexdump(newindent))
        return str[:-1]

class elfo(elfxo):
    def create(path):
        # This staticmethod is required by objutil to create an instance
        elf=PyELF.elf(path)
        if elf.header.typ!=PyELF.elf.relocatable:
            raise TypeError("ELF must be a relocatable object: %s" % path)
        return elfo(elf).init()
    create=staticmethod(create)
    def __init__(self,elf):
        elfxo.__init__(self,elf)
        self.segments=[]          # List of program segments
    def buildCodeAreas(self):
        # Create dictionaries required by objutil
        for x in self.sections:
            if x.size==0:
                continue
            sect=sect_code(self,x,x.index)
            self.sectids[x.index]=sect
            if len(x.name)==0:
                name="Segment_%s" % x.index
            else:
                name=x.name
            self.sectnames[name]=sect
    #
    # This method is used by objutil to interrogate the object instance
    def getEntry(self):
        # Return the entry point.  Entry points are assumed to be determined
        # at linkage editing of an object module.  None is returned
        return None
    
class elfx(elfxo):
    def create(path):
        # This staticmethod is required by objutil to create an instance
        elf=PyELF.elf(path)
        if elf.header.typ!=PyELF.elf.executable:
            raise TypeError("ELF must be an executable: %s" % path)
        return elfx(elf).init()
    create=staticmethod(create)
    def __init__(self,elf):
        elfxo.__init__(self,elf)
        self.segments=None
    def buildCodeAreas(self):
        # Create module level dictionaries required by objutil
        for x in self.sections:
            if x.size==0:
                continue
            sect=pgm_code(self,x,x.index)
            self.sectids[x.index]=sect
            if len(x.name)==0:
                name="Segment_%s" % x.index
            else:
                name=x.name
            self.sectnames[name]=sect
    #
    # This method is used by objutil to interrogate the object instance
    def getEntry(self):
        # Return the linkage editor determined entry point.
        return self.elf.header.entry
    def getLocal(self):
        # Return a dictionary of code area objects keyed to their local ids
        return self.sectids
    def getNames(self):
        # Return a dictionary of code area objects keyed to their names
        return self.sectnames
    def hexdump(self,indent=""):
        # Return a string of the sections' binary contents
        names=self.sectnames.keys()
        names.sort()
        str=""
        newindent="%s%s" % (indent,"    ")
        for x in names:
            sect=self.sectnames[x]
            str="%s%sContents of ID[%s] %s\n%s\n" \
                % (str,indent,\
                sect.sect.index,sect.sect.name,sect.hexdump(newindent))
        return str[:-1]

class sect_adcon(objutil.adcon):
    def __init__(self,sect,rela_item,symtab_item,size):
        objutil.adcon.__init__(self)
        self.sect=sect
        self.rela=rela_item
        self.symtab=symtab_item
        self.size=size
        self.setRtype(self.getRtype())
    def __str__(self):
        return "RELA(%s)\nSYMTAB(%s)" % (self.rela,self.symtab)
    # These methods are used by objutil.py to interogate the RLD item
    def getAddend(self):
        return abs(self.rela.addend)
    def getPtrDir(self):
        # This method returns how the address constants contents relates to
        # the base of section to which the address constant relates
        if self.rela.addend<0:
            return -1
        return 1
    def getPtrID(self):
        # Returns the object format specific id of the section to which
        # the address constand actually points.
        return self.symtab.secndx
    def getResID(self):
        # This method returns the local id of the section in which this
        # relocation item physically resides
        return self.rela.resndx
    def getResOff(self,base=0):
        # Return the offset into the section in which the address constant
        # resides.  objutil will provide the section's base for use by 
        # this method.  The object format may not require it.
        #
        # RLD items generated by z390 contain in the RLD address field an
        # offset into the section where the address constant resides.
        # This may not be consistent with HLASM - requires further research
        return self.rela.offset
    def getRmode(self):
        # Returns the residency mode of this section.
        return self.sect.getRmode()
    def getRtype(self):
        # Return the relocation type.
        # s370 executables return negative relocation types
        if self.getRmode()==24:
            return -1*self.rela.typ
        return self.rela.typ
    def getSize(self):
        # Return the physical size of the address constant residing in the
        # section
        return self.size
        
class pgm_adcon(sect_adcon):
    def __init__(self,sect,rela_item,symtab_item,size):
        sect_adcon.__init__(self,sect,rela_item,symtab_item,size)
    # These methods are used by objutil.py to interogate the RLD item
    def getResOff(self,base=0):
        # Return the offset into the section in which the address constant
        # resides.  objutil will provide the section's base for use by 
        # this method.  The object format may not require it.
        #
        # RLD items generated by z390 contain in the RLD address field an
        # offset into the section where the address constant resides.
        # This may not be consistent with HLASM - requires further research
        return self.rela.offset-self.sect.sect.addr
    
class sect_code(objutil.code):
    binders=None    # Set in first call to sect_code.getBinders()
    def __init__(self,module,elfsect,myid):
        objutil.code.__init__(self)
        self.sect=elfsect             # My PyELF Section instance
        self.module=module            # My elfo instance
        self.myid=myid                # My local ID
        self.myname=self.sect.name    # My name
        self.mybase=0
        self.relas=[]
    def __str__(self):
        string="ID[%s] %s" % (self.myid,self.myname)
        for x in self.relas:
            string="%s\n    %s" % (string,x)
        return string
    def buildAdcon(self,rela,symtab):
        # Build an adcon from the rela and symtab entry
        self.relas.append(sect_adcon(self,\
            rela,symtab,self.module.relasizes[rela.typ]))
    #
    # These methods support the objutil code area interface
    def getAdcons(self):
        # Return a list of my adcons
        return self.relas
    def getBinders(self):
        # Return the binder mappings
        # Return the binder dictionary
        if sect_code.binders is None:
            sect_code.binders={}
            objutil.binder(1,1,8).register(sect_code.binders)
            objutil.binder(2,2,12).register(sect_code.binders)
            objutil.binder(3,2,16).register(sect_code.binders)
            objutil.binder(4,4,31).register(sect_code.binders)
            objutil.binder(22,8,64).register(sect_code.binders)
        return sect_code.binders
    def getContent(self):
        # Return a copy of the section's content
        return bytearray(self.sect.data)
    def getID(self):
        # Return the code area's local identifier
        return self.myid
    def getLoad(self):
        # Return the storage residency start address of the code area's content
        return self.sect.addr
    def getReloEngine(self):
        # Returns the relocation engine for this code area
        return elfrelo(self.getRmode())
    def getRmode(self):
        # Returns the residency mode of this code area
        return self.module.getRmode()
    def hexdump(self,indent=""):
        # Returns the contents of this section
        return dump(self.content,self.sect.addr,self.getRmode(),indent)

class pgm_code(sect_code):
    def __init__(self,module,elfsect,myid):
        sect_code.__init__(self,module,elfsect,myid)
    def buildAdcon(self,rela,symtab):
        # Build an adcon from the rela and symtab entry
        self.relas.append(pgm_adcon(self,\
            rela,symtab,self.module.relasizes[rela.typ]))
    #
    # These methods support the objutil code area interface
    def getBase(self):
        # Return the code area's address constant base address
        return self.sect.addr

def instantiate(path):
    elf=PyELF.elf(path)
    if elf.typ==PyELF.elf.relocatable:
        return elfo(elf)
    if elf.typ==PyELF.elf.executable:
        return elfx(elf)
    raise TypeError("Unrecognized ELF file type: %s" % elf.typ)

if __name__=="__main__":
   args=sys.argv
   if len(args)<3:
       print("Usage: ELFXO.py [dump|print] elffile")
       sys.exit(1)
   elf=instantiate(path)
   if args[1]=="print":
       print(elf)
       sys.exit(0)
   if args[1]=="dump":
       print(elf.hexdump())
       sys.exit(0)
   print("Invalid option: %s" % args[1])
   sys.exit(1)
       