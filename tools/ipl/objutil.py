#!/usr/bin/python

# Utility to handle object code transformations in a standardized way 
# This module is imported by to provide the standard interface.  Each of the
# supported object file formats will create format specific subclasses of 
# the objutil classes.  The properties of the subclass instances are read
# only with respect to objutil.  Modifications to objutil values are local
# to the objutil superclasses and do not alter the object file specific data

import sys                # Access to command line arguments
from hexdump import *     # Access to hexdump utility functions

# Note: this module requires Python 2.6 or greater

# Generic Object Classes
#
#  adcon *  The generic relocation item.  It consists of two locations, the
#           address constant's residency in the module and the location to
#           which the address constant points.
#  address  A generic storage address superclass.  This class knows how to 
#           convert addresses between a binary string and a numeric value, 
#           how to display the address in human readable format.
#  binder   Generic class for constructing or interpreting address constants
#  code *   The generic object section or program segment
#  loc      The generic location.  It understands where a location is in
#           the module and where the same location's assigned storage address
#  module * The generic object file
#
#  * Each of these classes has init parms that allow the class to be cloned.
#    or created independently of the initial object format instance.
#
# Data relationships
#
#   module -------> code -------> adcon ------> loc ------> address8
#                    | ^                         |          address16
#                    | +-------------------------+          address24
#                    V                                      address31
#                   binder{}                                address64
#
# objutil class hierarchy
#
#   adcon
#   address ------> address8, address16, address24, address31, address64
#   code
#   loc
#   module
#   relo

class module(object):
    #
    # Generic object file wrapper
    #
    # Properties:
    #  RO  ProgramEntry   Module entry point (may return None)
    #  RO  Rmode          Residency mode (24, 31, 64)
    #
    # Instance Methods:
    #   init         initialize the module
    #   bind         bind a code area to a specific storage locations
    #   clone        create a separate copy of a module instance
    #   display      print the generic module information
    #   generate     Creates a new module from a list of areas
    #   getID        return a code area based upon its local id
    #   getNAME      return a code area based upon its assigned name
    #   isOBJO       test if the source object file was OBJO
    #   isOBJX       test if the source object file was OBJX
    #
    # Object Format Accessing Methods:
    #   getBinders   Returns a dict. mapping relocation types to binders
    #   getEntry     Returns the module's entry point (need to convert to loc)
    #   getLocal     Returns a dict. of code areas keyed to local id's
    #   getNames     Returns a dict. of code areas keyed to names
    # 
    sstruct={1:sbyte,
             2:shalfword,
             3:addr24,
             4:sfullword,
             8:sdblword}
    sstructb={1:sbyteb,
              2:shalfwordb,
              3:addr24b,
              4:sfullwordb,
              8:sdblwordb}
    ustruct={1:byte,
             2:halfword,
             3:addr24,
             4:fullword,
             8:dblword}
    ustructb={1:byteb,
              2:halfwordb,
              3:addr24b,
              4:fullwordb,
              8:dblwordb}
    format={1:bytef,2:halfwordf,4:fullwordf,8:dblwordf}
    formatX={1:byteX,2:halfwordX,4:fullwordX,8:dblwordX}
    addrfmt={1:bytef,2:halfwordf,3:addr24f,4:addr31f,8:dblwordf}
    addrfmtX={1:byteX,2:halfwordX,3:addr24X,4:addr31X,8:dblwordX}
    resbinders={}     # Residency address binders.  
    # Note: residency address binders are registered after the binder class
    # has been created.  See below.

    # Each object format must provide its own staticmethod create()
    # that takes a file path/name and returns a module instance
    def create(path,cls):
        return cls.create(path).init()
    create=staticmethod(create)
    def __init__(self,entry=None,names={},sections={},rmode=24):
        self._entry=entry       # Entry point of the module
        self._names=names       # Generic Sections indexed by name
        self._sections=sections # Generic Sections indexed by local identifier
        self._rmode=rmode       # Generic Module residency mode
    def init(self):
        # Initialize the generic module
        self._entry=self.getEntry()
        self._sections=self.getLocal()
        self._names=self.getNames()
        rmode=64
        for x in self._sections:
            code=self._sections[x]
            code.init(self)
            if code.Rmode<rmode:
                rmode=code.Rmode
        self._rmode=rmode
        return self
    #
    # module properties:
    @property
    def ProgramEntry(self):
        return self._entry
    @property
    def Rmode(self):
        return self._rmode
    #
    # module instance methods
    def bind(self,newaddr,id):
        for code in self._sections:
            codeid=code.ID
            for const in code.adcons:
                # The address constant points into this code area's id
                ptrid=const.ptrid
                # Regardless of where the address constant resides, if it
                # is not pointing to a location in the code area being 
                # bound ignore it
                if const.ptrid!=id:
                    continue
                # Fetch the code area related to the pointer's code area
                ptrcode=const.ptrloc.code
                # This is the size of the pointer
                poffset=code.ptrextract(const.resloc.offset,const.size)
                # Calculate the new pointer value
                new=poffset+newaddr
                # Store it back into the code area in which it resides
                code.ptrinsert(const.resloc.offset,const.size,new)
            if codeid==id:
                # Now relocate all of the adcons to the new resident address
                code.relo(newaddr)
    def binders(self,area=None,indent=""):
        # Return a string for displaying binder types
        if area is None:
            for x in self._sections.itervalues():
                binders=x.binders
                break
        else:
            try:
                binders=self.getNAME(area).binders
            except KeyError:
                raise ValueError("unrecognized code area: %s" % area)
        new_indent="    %s" % indent
        string=""
        types=binders.keys()
        types.sort()
        for x in types:
            string="%s%s\n" % (string,binders[x].display(new_indent))
        return string[:-1]
    def clone(self,entry=None,names=None,areas=None):
        myentry=self.ProgramEntry
        mynames=self._names
        myrelos=self._relos
        myareas=self._sections
        if entry!=None:
            myentry=entry
        if names!=None:
            mynames=names
        if areas!=None:
            myareas=areas
        return module(myentry,mynames,myareas)
    def display(self):
        if self.ProgramEntry==None:
            entry="None"
        else:
            entry="0x%X" % self.ProgramEntry
        string="%s Entry point: %s" \
            % (self.__class__.__name__,entry)
        names=self._names.keys()
        names.sort()
        string="%s\nNamed code areas:" % string
        for x in names:
            area=self.getNAME(x)
            string="%s\n    ID[%s] %s" % (string,area.ID,x)
        string="%s\nCode Areas:" % string
        ids=self._sections.keys()
        ids.sort()
        for x in ids:
            area=self.getID(x)
            string="%s\n%s" % (string,area.display("    "))
        return string
    def getID(self,id):
        # Returns the code instance based upon its local ID
        return self._sections[id]
    def getNAME(self,name):
        # Returns the code instance based upon its name
        return self._names[name]
    def isELFO(self):
        # Test if module instance is from an ELFO file
        return isinstance(self,ELFXO.elfo)
    def isELFX(self):
        # Test is module instance is from an EFLX file
        return isinstance(self,ELFXO.elfx)
    def isOBJO(self):
        # Test if module instance is from an OBJO file
        return isinstance(self,OBJO.objo)
    def isOBJX(self):
        # Test if module instance is from an OBJX file
        return isinstance(self,OBJX.objx)
    #
    # These methods are used by objutil to interrogate the object specific
    # format
    def getEntry(self):
        # Returns the module entry point, may be None
        raise NotImplementedError(
            "class %s must implement getEntry() method" \
            % self.__class__.__name__)
    def getLocal(self):
        # return a dictionary of code areas keyed to the local ids
        raise NotImplementedError(
            "class %s must implement getLocal() method" \
            % self.__class__.__name__)
    def getNames(self):
        # Return a dictionary of code areas keyed to name ids
        raise NotImplementedError(
            "class %s must implement getNames() method" \
            % self.__class__.__name__)
    def hexdump(self,indent=""):
        # Returns a string for printing of the binary contents of sections
        raise NotImplementedError(
            "class %s must implement hexdump() method" \
            % self.__class__.__name__)

class code(object):
    #
    # Program section or segment generic wrapper
    #
    # Properties:
    #   RO  adcons      a list of adcons ordered by residency offset
    #   R0  binders     Returns the dictionary of binders
    #       content     code area binary content
    #   RO  ID          local id of code area
    #   RO  length      length in bytes of the code area
    #       loadpt      address to which code area content will be loaded
    #   RO  Rmode       section residency mode
    #
    # code Instance Methods:
    #   init         initialize the code area from the object subclass
    #   clone        Returns a separate copy of a code instance
    #   display      prints the code area generic information.  Because 
    #                this class may be a super class of an object format
    #                __str__ is reserved for use by the object format classes
    #   dump         Print the contents using the load point as start
    #   extract      Retrieve a bytearray sequence of specified length from
    #                an offset into the code area content
    #   getBinder    Returns a binder instance based upon relocation type
    #   insert       Store a bytearray sequence at an offset into the code
    #                area content
    #   ordered      Creates an ordered list of adcons by offset
    #   ptrextract   Extract a pointer value from the code area content
    #   ptrinsert    Store a pointer value into the code area content
    #
    # Object Format Accessing Methods:
    #   getAdcons    Returns a list of adcon instances
    #   getBase      Returns the base of the code area
    #   getContent   Returns the code area binary content
    #   getID        Returns the code area's local identifier
    #   getRmode     Returns the code area's residency mode
    #
    rmode={24:3,31:4,64:8}  # Convert residency mode to address length
    def __init__(self,adcons={},myid=None,load=None,content=None,\
                 binders={},rmode=None):
        self._adcons=adcons    # Address constants keyed to address
        self._id=myid          # Local ID of this code area
        self._load=load        # load address of code area content
        self._content=content  # bytearray of code area content
        self._binders=binders  # the relocation type binders
        self._rmode=rmode      # code area residency mode
        # List of adcons ordered by offset
        self._adlist=self.ordered(self._adcons)
    def init(self,mod):
        # Uses the code area interface to complete the generic representation
        self._binders=self.getBinders()   # Get the binders for this area
        self._id=self.getID()
        self._load=self.getLoad()
        self._rmode=self.getRmode()
        adcons=self.getAdcons()
        self._content=self.getContent()
        self._adcons={}
        for x in adcons:
            # X is a subclass of adcon
            #x.size=x.getSize()
            #if x.size==0:
            #    print "Error: adcon of zero length encountered, ignored: %s"\
            #        % x.display()
            #    continue
            # Create and set the residence location
            offset=x.getResOff()
            resbinder=module.resbinders[self.Rmode]
            x.adjust=x.getAddend()*x.getPtrDir()
            x.resloc=loc(self.ID,offset,self.loadpt+offset,resbinder)
            # Create and set the pointer location
            x.setBinder(self.getBinder(x.rtype))
            ptrid=x.getPtrID()
            try:
                ptrcode=mod.getID(ptrid)  # Code area of the pointer
            except KeyError:
                print("Error: ID[%s] not found: %s" % (ptrid,x))
                continue
            ptrcodid=ptrcode.getID()
            x.adjust=x.getAddend()*x.getPtrDir()
            x.ptrloc=loc(ptrcodid,x.adjust,ptrcode.getLoad()+x.adjust,\
                 x.getBinder())
            # save the adcon based upon its memory address residency
            self._adcons[x.resloc.address]=x
        self._adlist=self.ordered(self._adcons)
    @property
    def adcons(self):
        return self._adlist
    @property
    def binders(self):
        return self._binders
    @property
    def content(self):
        return self._content
    @content.setter
    def content(self,bytearray):
        self._content=bytearray
    @property
    def ID(self):
        return self._id
    @property
    def loadpt(self):
        return self._load
    @loadpt.setter
    def loadpt(self,value):
        self._load=value
    @property
    def Rmode(self):
        return self._rmode
    @property
    def size(self):
        return len(self._content)
    #
    # code Instance Methods:
    def clone(self,adcons=None,myid=None,load=None,content=None,\
              binders=None,rmode=None):
        myadcons=self._adcons
        myid=self.ID
        myload=self.loadpt
        mycontent=self.content
        mybinders=self._binders
        if adcons!=None:
            myadcons=adcons
        if myid!=None:
            myid=myid
        if load!=None:
            myload=load
        if content!=None:
            mycontent=content
        if binders!=None:
            mybinders=binders
        if rmode!=None:
            myrmode=rmode
        return code(myadcons,myid,myload,mycontent,mybinders,myrmode)
    def display(self,indent=""):
        loadpt=self.loadpt
        loadend=self.loadpt+len(self.content)-1
        string="%sArea ID[%s]:      Content  %X-%X" \
            % (indent,self.ID,loadpt,loadend)
        for x in self._adlist:
            string="%s\n%s%s" % (string,indent,x.display("    "))
        return string
    def dump(self,indent=""):
        return dump(self._content,self._load,self.Rmode,indent="    ")
    def extract(self,offset,bytes):
        # Returns bytearray of requested bytes
        return self._content[offset:offset+bytes]
    def getBinder(self,rtype):
        # returns a specific binder for a relocation type
        try:
            return self.binders[rtype]
        except KeyError:
            raise ValueError(\
                "objutil.py code.getBineder() unrecognized relocation type: %s"\
                % rtype)
    def insert(self,offset,bytearray):
        # Replaces in bytearray content, bytearray of bytes at offset
        self._content[offset:offset+len(bytearray)]=bytearray
    def ordered(self,adict):
        # creates a list of adcons ordered by offset from a input dictionary
        order={}
        for x in adict:
            entry=adict[x]
            order[entry.resloc.offset]=entry
        byoffset=order.keys()
        byoffset.sort()
        offsetlist=[]
        for x in byoffset:
            offsetlist.append(order[x])
        return offsetlist
    def ptrextract(self,offset,size):
        # Ultimately I do not think this method will be needed
        method=module.ustruct[size]
        return method(str(self.extract(offset,size)))
    def ptrinsert(self,offset,size,value):
        method=module.ustructb[size]
        self.insert(offset,bytearray(method(value)))
    #
    # These methods define the objutil interface to code areas
    def getAdcons(self):
        # returns the list of local address constants
        raise NotImplementedError(
            "class %s must implement getAdcons() method" \
            % self.__class__.__name__)
    def getBinders(self):
        # Return a dictionary mapping relocation types to binder instances
        raise NotImplementedError(
            "class %s must implement getBinders() method" \
            % self.__class__.__name__)
    def getContent(self):
        # return a bytearray of the code area's content
        raise NotImplementedError(
            "class %s must implement getContent() method" \
            % self.__class__.__name__)
    def getID(self):
        # returns the local id of this code area
        raise NotImplementedError(
            "class %s must implement getID() method" \
            % self.__class__.__name__)
    def getLoad(self,value):
        # Set the code area load point
        raise NotImplementedError(
            "class %s must implement getLoad() method" \
            % self.__class__.__name__)
    def getRmode(self):
        # Returns the residency mode of the code area
        raise NotImplementedError(
            "class %s must implement getRmode() method" \
            % self.__class__.__name__)
    def hexdump(self,indent=""):
        # Returns a string for printing of this code areas binary contents
        raise NotImplementedError(
            "class %s must implement hexdump() method" \
            % self.__class__.__name__)

# Individual address constant
class adcon(object):
    #
    # Relocation item generic wrapper.
    # 
    # The generic address constant relocation item accommodates different 
    # styles of relocation definition by generalizing the concepts.  This 
    # results in a merger and adoption of mechanisms in both styles supported.
    #
    # Attribute                       ELFx                    OJBx
    #   type                  defined                  size implies, adopted
    #   pointer loc offset    in RELA item, addend     in resident object TXT
    #   constant size         implied by type          explicit
    #   relocation algorithm  implied by type          implied by size, flags
    #
    # Generic Acdon
    #   type                  uses explicit type       creates a type
    #   pointer loc offset    relies on EFLx           relies on OBKx
    #   constant size         ELFx created from type   OBJx uses RLD item size
    #   relocation algrithm   binder for pointer       binder for pointer
    #
    # Properties:
    #
    #       adjust   signed addend value applied to the pointer section loc
    #       ptrid    local id of the pointer's code area
    #   RO  ptrloc   Pointer's code area location
    #   RO  resid    local id of code area in which the address 
    #                constant resides
    #       resloc   location instance of this address constant
    #   R0  rtype    Relocation type (defines binder algorithms)
    #       size     physical size in bytes of the address constant
    #
    # adcon Instance methods:
    #   bind         Updates the address constant's binary contents based
    #                upon its pointer location information
    #   clone        Creates a separate copy of the instance
    #   diplay       Provides a string of the generic adcon, like __str__
    #   getBinder    Returns the address constant's pointer's binder instance
    #   setBinder    Set the adcon's pointer's binder instance from rtype
    #   setRtype     Set the instances relocation type.  Attribute rtype is
    #                read only.
    #   unbind       Extracts from the residency code area contents the
    #                adcons data as a tuple (preserved,value)
    #
    # Object Format Accessing Methods:
    #   getAddend    Returns the addend external from the code area
    #   getPtrDir    Returns the direction of the pointer addend
    #   getPtrid     Get the local ID of the code area to which this adcon
    #                points
    #   getResID     Get the local ID of the code ares in which this adcon
    #                resides
    #   getResLoc    sets the new address of this adcon when its resident
    #                code area is relocated
    #   getResOff    address constant's offset from the start of its
    #                code area
    #   getSize      Get the storage size of this address constant
    #   getType      Get the relocation type
    #
    def __init__(self,resloc=None,ptrloc=None,adjust=0,rtype=None,size=0):
        self._resloc=resloc   # Address constant's residence location instance
        self._ptrloc=ptrloc   # Pointer's code area starting location instance
        self._adjust=adjust   # Signed adjustment
        self._rtype=rtype     # relocation type
        self._binder=None     # set by code.init()
        self._size=None       # set by code.init() in self.setBinder()
    @property
    def adjust(self):
        return self._adjust
    @adjust.setter
    def adjust(self,val):
        self._adjust=val
    @property
    def ptrid(self):
        return self._ptrloc.code.ID
    @property
    def ptrloc(self):
        return self._ptrloc
    @ptrloc.setter
    def ptrloc(self,loctn):
        if not isinstance(loctn,loc):
            raise TypeError("ptrloc must be a loc instance: %s" % loctn)
        self._ptrloc=loctn
    @property
    def resid(self):
        return self._resloc.code.ID
    @property
    def resloc(self):
        return self._resloc
    @resloc.setter
    def resloc(self,loctn):
        if not isinstance(loctn,loc):
            raise TypeError("ptrloc must be a loc instance: %s" % loctn)
        self._resloc=loctn
    @property
    def rtype(self):
        return self._rtype
    @property
    def size(self):
        return self._size
    @size.setter
    def size(self,value):
        self._size=value
    #
    # adcon Instance Methods
    def bind(self,code,nmod,preserve=0):
        # unbinds this address constant from its resident code area
        ptr_address=self.ptrloc.address
        binder=self._binder
        new_ptr=binder.binary(preserve,self.ptrloc.address,self,code,nmod)
        # Note: because the needs of the binder algorithms are unknown, the
        # module, code area and source address constant are passed to the
        # binder
        return code.insert(self.resloc.offset,bytearray(new_ptr))
    def clone(self,resloc=None,ptrloc=None,adjust=None,rtype=None,size=None):
        myresloc=self.resloc.clone()
        myptrloc=self.prtloc.clone()
        myadjust=self.adjust
        mytype=self.rtype
        mysize=self.size
        if resloc!=None:
            myresloc=resloc
        if ptrloc!=None:
            myptrloc=ptrloc
        if adjust!=None:
            myadjust=adjust
        if rtype!=None:
            mytype=rtype
        if size!=None:
            mysize=size
        return adcon(myresloc,myptrloc,myadjust,mytype,mysize)
    def display(self,indent=""):
        # Provides a string of the adcon instance.  __str__() is reserved for
        # subclasses.
        return "%sRes(%s),Ptr(%s),Len(%s),Type(%s)" \
            % (indent,self._resloc,self._ptrloc,self._size,self._rtype)
    def getBinder(self):
        return self._binder
    def setBinder(self,bndr):
        self._binder=bndr
        self._size=bndr.length
    def setRtype(self,value):
        # Set the relocation type
        self._rtype=value
    def unbind(self,code,mod):
        # unbinds this address constant from its resident code area
        binder=self._binder
        res_offset=self.resloc.offset
        return self._binder.numeric(\
            str(code.extract(res_offset,binder.length)),\
            self,code,mod)
    #
    # These methods define the objutil interface to address constants
    def getAddend(self):
        # This method returns the externally stored addend value
        raise NotImplementedError(
            "class %s must implement getAddend() method" \
            % self.__class__.__name__)
    def getPtrDir(self):
        # This method returns the adjustment direction
        raise NotImplementedError(
            "class %s must implement getPtrDir() method" \
            % self.__class__.__name__)
    def getPtrID(self):
        # Returns the object format specific id of the section to which
        # the address constand actually points.
        raise NotImplementedError(
            "class %s must implement getPtrID() method" \
            % self.__class__.__name__)
    def getResID(self):
        # Returns the object format specific id of the code area in which this
        # relocation item phyiscally resides
        raise NotImplementedError(
            "class %s must implement getResID() method" \
            % self.__class__.__name__)
    def getResOff(self,base=0):
        # Return the offset into the section in which the address constant
        # resides.  code area's base in which the address constant resides
        # is provided.
        raise NotImplementedError(
            "class %s must implement getResOff() method" \
            % self.__class__.__name__)
    def getRtype(self):
        # Returns the relocation type of this address constant
        raise NotImplementedError(
            "class %s must implement getRtype() method" \
            % self.__class__.__name__)
    def getSize(self):
        # Return the physical size of the address constant residing in the
        # code area
        raise NotImplementedError(
            "class %s must implement getSize() method" \
            % self.__class__.__name__)

class address(object):
    #
    # This class abstracts mode sensitive address calculations
    # It is intended to be used in conjuction with the hexdump functions
    #
    # Overloaded methods (for relocation)
    #     self+value, self+=value, value+self
    #     self-value, self-=value
    # 
    # Properties
    #  RO  format   The storage format of this address.  Default is 24
    #      value    The numeric adress value, default is 0
    #
    def __init__(self,value,bndr):
        self.binder=bndr
        self.address=value
    def __add__(self,value):
        #  self+value
        newaddr=self.addr+value
        return address(self.addr+value,self.binder)
    def __iadd__(self,value):
        #  self+=value
        self.addr=self.wrap(self.addr+value)
        return self
    def __isub__(self,value):
        #  self-=value
        self.addr=self.wrap(self.addr-value)
        return self
    def __radd__(self,value):
        #  value+self
        return address(self.addr+value,self.binder)
    def __str__(self):
        return self.binder.format(self.addr)
    def __sub__(self,value):
        #  self-value
        return address(self.addr-value,self.binder)
    @property
    def address(self):
        return self.addr
    @address.setter
    def address(self,value):
        self.addr=self.wrap(value)
    @property
    def format(self):
        return self.binder.bits
    #
    # address instance methods
    def clone(self,address=None,binder=None):
        addr=self.address
        bndr=self.binder
        if address!=None:
            addr=address
        if binder!=None:
            bndr=binder
        return self.__class__(addr,bndr)
    def wrap(self,value):
        return self.binder.isolate(value)

class binder(object):
    #
    # This class is the superclass for all object format specific address
    # constant formats.  Each instance corresponds to an individual format.
    # binder instances are read-only.  Instance methods use the instance
    # attributes but do not change them.
    #
    # binder Properties
    #   RO  length     Number of bytes consumed by this address constant
    #   RO  rtype      Type of this address constant
    #   RO  size       Number of bites consumed by this address constant
    #
    # Overridable methods by subclasses
    #
    # The numeric address is a Python number that is a valid storage address
    # The address constant may be an encoded form of the numeric address
    # These two methods allow subclasses to perform these conversions.
    #
    #   address        Converts the numeric address constant into an address
    #                  By default, this method does nothing.
    #   content        Convers a numerioc address into an address constant
    def __init__(self,rtype,length,bits):
        if bits>length*8:
            raise ValueError(\
               "address bits %s exceed address constant size %s" \
               % (bits,length*8))
        self._type=rtype               # Binder's relocation type
        self._length=length            # Size of address constant in bytes
        self._bits=bits                # Low-order bits that are the address
        self._isolate=2**bits-1        # Mask to isolate relavant bits
        self._preserve=~self._isolate  # Mask of bits to preserve
        self._nummeth=module.ustruct[length]  # Numeric conversion method
        self._binmeth=module.ustructb[length] # Binary conversion method
        self._format=module.addrfmtX[length]  # Hex formatting string
    def __str__(self):
        # Create a string representing the binder
        isolate=self._format(self._isolate)
        preserve=self._format(self._preserve & ~self._isolate)
        return "Type %s bytes(%s),bits(%s),mask(%s),preserve(%s)" \
            % (self._type,self.length,self._bits,isolate,preserve)
    #
    # binder properties
    @property
    def length(self):
        return self._length
    @property
    def rtype(self):
        return self._type
    @property
    def size(self):
        return self._bits
    #
    # binder instance methods:
    def binary(self,preserve,numeric,adcon,code,mod):
        # Convert preserved bits and address to binary string
        #print "binder.binary(preserve=%X,numeric=%X)" % (preserve,numeric)
        stored_value=self.content(numeric,adcon,code,mod)  # Transform if needed
        # Note: because the content() method may be subclassed and the needs
        # of the subclass method are unknown, the adcon instance, resident code
        # area and module are passed to the method
        return self._binmeth(self.merge(preserve,stored_value))
    def display(self,indent=""):
        return "%s%s" % (indent,self)
    def format(self,address):
        # Format and address for printing
        return self._format(self.isolate(address))
    def isolate(self,value):
        return value & self._isolate
    def merge(self,static,variable):
        # Merges the preserved bits and address bits into a single value
        stat=static & self._preserve
        number=variable & self._isolate
        return stat|number
    def numeric(self,string,adcon,code,mod):
        if len(string)!=self.length:
            raise ValueError(\
                "expected address constant string length %s: %s" \
                % (self.length,len(string)))
        number=self._nummeth(string)
        preserved,content=self.separate(number)
        # Convert stored value if needed
        address=self.address(content,adcon,code,mod)
        # Note: because the address() method may be subclassed and the needs
        # of the subclass method are unknown, the adcon instance, resident 
        # code area and module are passed to the method
        return (preserved,address)
    def register(self,binders):
        # Register myself with a binders dictionary
        binders[self._type]=self
    def separate(self,value):
        # separates and returns the preserved bits and address bits
        return (value&self._preserve,value&self._isolate)
    #
    # instance methods intended to be overridden
    def address(self,value,adcon,code,mod):
        # Converts a variable part of an address constant to an address
        # The default method performs no transformation
        return value
    def content(self,value,adcon,code,mod):
        # Converts an address to the variable part of an address constant
        # The default method performs no transformation
        return value
        
binder(24,3,24).register(module.resbinders)
binder(31,4,31).register(module.resbinders)
binder(64,8,64).register(module.resbinders)

class loc(object):
    #
    # This class abstracts the concept of location
    # A location may be either a run-time memory address or an offset into
    # a code area.  A location always has both attributes simultaneously.
    # When the run-time address is being relocated,the address will change, 
    # but the code area offset never changes.
    #
    # Properties:
    #
    #   RO  address    Numeric value of the location's storage address
    #   RO  offset     Numeric value of the offset of the location
    #
    # loc instance methods:
    #   clone          Creates a separate copy of the instnace
    #
    def __init__(self,codeid,offset,addr,bndr=None):
        if not isinstance(bndr,binder):
            raise TypeError("bndr not a binder instance: %s" % bndr)
        self.codeid=codeid
        self.offset=offset
        self.binder=bndr
        self.addr=address(addr,self.binder)
    def __str__(self):
        return "%s @ ID[%s:%0X]" % (self.addr,self.codeid,self.offset)
    @property
    def address(self):
        return self.addr.address
    @address.setter
    def address(self,value):
        self.addr=self.addr.clone(address=value)
    #
    # loc instance methods
    def clone(self,code=None,offset=None,address=None,binder=None):
        mycodeid=self.codeid
        myoffset=self.offset
        myaddress=self.address
        mybinder=self.binder
        if code!=None:
            mycodeid=code
        if offset!=None:
            myoffset=offset
        if address!=None:
            myaddress=address
        if binder!=None:
            mybinder=binder
        return loc(mycodeid,myoffset,myaddress,mybinder)

# These modules must be imported here because the depend upon objects created
# above.
import OBJO               # Access the OBJO module
import OBJX               # Access the OBJX module
import ELFXO              # Access the ELF PyELF wrapper module

# Dictionary of supported object code formats
formats={"objo":OBJO.objo,
         "objx":OBJX.objx,
         "elfo":ELFXO.elfo,
         "elfx":ELFXO.elfx}

if __name__=="__main__":
   raise NotImplementedError("objutil.py is only imported")
       