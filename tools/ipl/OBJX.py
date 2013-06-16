#!/usr/bin/python

# Utility to handle z390 load modules

import objutil            # Access the generic object module interface
import sys                # Access to command line arguments
from translate import *   # ASCII/EBCDIC translate tables
from hexdump import *     # Access to useful binary methods


# Note: this module requires Python 2.6 or greater

# Data relationships
#
#    objutil:  module  ------> codearea --- ----> adcon
#               ^               ^  |  ^            |  ^
#               |               |  |  +------------+  |
#               |               |  V                  |
#               |               | binders             |
#               |               |  ^                  |
#               |               |  |                  |
#    OBJX:      |               |  |                  |
#               |               |  |                  |
#               |               |  |                  |
#              objx ---------> segment ------------> rld
#               |
#               V
#              header
#                

class objx(objutil.module):
    # For objx instances, code area base and load point are always zero.
    def create(path):
        mod=pythonize.loadmodule(path)
        return objx.pythonize(mod).init()
    create=staticmethod(create)
    def pythonize(mod,strict=True):
        # Converts, a load module into an objx instance
        hdr=header(mod[0:20])  # Interpret header
        # Now I know where things are
        rld_start=20+hdr.length
        rlds=mod[rld_start:rld_start+(8*hdr.rlds)]
        rldlist=pythonize.rlds(rlds,hdr)
        seg=segment(mod[20:rld_start],rldlist,hdr.rmode)
        return objx(hdr,seg)
    pythonize=staticmethod(pythonize)
    def __init__(self,header,segment):
        objutil.module.__init__(self)
        self.hdr=header
        self.segment=segment
    def __str__(self):
        return "%s\n%s" % (self.hdr,self.segment)
    def hexdump(self,indent=""):
        return dump(self.segment.text,0,indent)
    #
    # These methods are used by objutil to interrogate the object instance
    def getEntry(self):
        # Return the load module entry point
        return self.hdr.entry
    def getLocal(self):
        # Return a dictionary of code area objects indexed by the local ids
        return {1:self.segment}
    def getNames(self):
        return {"TXT":self.segment}
    def hexdump(self,indent=""):
        # Return a string of the contents of the load module
        return dump(self.segment.text,0,self.segment.getRmode(),indent)

class pythonize(object):

    # This method operates on the entire load module file
    def loadmodule(path,strict=True):
        # Converts, a load module into a tuple of load modules areas
        # (header,
        try:
            fo=open(path,"rb")
        except IOError:
            raise IOError("Could not open for reading: %s" % path)
        try:
            module=fo.read()
        except IOError:
            raise IOError("Error reading: %s" % path)
        try:
            fo.close()
        except IOError:
            raise IOError("Error closing: %s" % path)
        return module
    loadmodule=staticmethod(loadmodule)
    
    # This method operates on all of the RLD items in the load module
    def rlds(rldbin,header):
        rldlist=[]
        for x in range(0,len(rldbin)-1,5):
            rldlist.append(rld(rldbin[x:x+5],header.rmode))
        return rldlist
    rlds=staticmethod(rlds)
    
class header(object):
    def __init__(self,header):
        if len(header)!=20:
            raise ValueError("header must be 20 bytes: %s" % len(header))
        self.amode=None         # Address mode of load module
        self.rmode=None         # Residency mode of load module
        self.length=0           # Length of program segment
        self.rlds=0             # Number of RLD entries in load module
        self.version=header[0:4]
        if header[4]=="T":
            self.amode=31
        else:
            self.amode=24
        if header[5]=="T":
            self.rmode=31
        else:
            self.rmode=24
        self.length=fullword(header[8:12])
        self.entry=fullword(header[12:16])
        self.rlds=fullword(header[16:20])
    def __str__(self):
        return "OBJX load module AM(%s), RM(%s), segment(%s), RLDs(%s)\n" \
            "    ENTRY(%06X)" \
            % (self.amode,self.rmode,self.length,self.rlds,self.entry)

class segment(objutil.code):
    binders={}
    def __init__(self,content,rlds,rmode):
        objutil.code.__init__(self)
        self.text=bytearray(content)   # Bytearray of load module text
        self.rlds=rlds                 # List of RLD items
        for x in rlds:                 # Point each
            x.ressect=self             # RLD back to me
        self.rmode=rmode               # Set my residency mode
        self.setLoad(0)                # Init load point to zero
    def __str__(self):
        str="    TXT %06X-%06X length(%s)" \
            % (0,len(self.text)-1,len(self.text))
        for x in self.rlds:
            str="%s\n    %s" % (str,x)
        return str
    def bytes(self,offset,length):
        # returns a bytearray of the specified length starting at the
        # specified offset from the start of the content
        return self.text[offset:offset+length]
    #
    # These methods support the objutil code area interface
    def getAdcons(self):
        # Return a list of adcon instances (rlditems)
        return self.rlds
    def getBinders(self):
        # return the relocation type binders mappings
        return segment.binders
    def getContent(self):
        # Return the code area's content
        return self.text
    def getID(self):
        return 1
    def getLoad(self):
        # Return the load point of the code area's content
        return self.load
    def getReloEngine(self):
        return objxrelo(self.getRmode())
    def getRmode(self):
        # Return the residency mode of the code area
        return self.rmode
    def setContent(self,bytearray):
        self.text=bytearray
    def setLoad(self,value):
        self.load=value

class rld(objutil.adcon):
    convert={1:byte,
             2:halfword,
             3:addr24,
             4:fullword,
             5:dblword}
    def __init__(self,rldbin,rmode):
        objutil.adcon.__init__(self)
        self.rmode=rmode       # Rmode of the segment
        self.offset=None       # Offset into segment of RLD location
        self.length=None       # Length of the RLD item at location
        self.direction=None    # Direction from base
        self.ressect=None      # Provided by segment.__init__
        if len(rldbin)!=5:
            raise ValueError(\
                "OBJX rld item must be 5 bytes: %s" % len(rldbin))
        self.offset=fullword(rldbin[0:4])
        length=sbyte(rldbin[4])
        if length<0:
            self.direction=-1
            length*=-1
        else:
            self.direction=1
        self.length=length
        self.setRtype(self.getRtype())  # Set my type.  It depends on length
    def __str__(self):
        str="AL%s" % self.length
        if self.direction>0:
            dir="+"
        else:
            dir='-'
        return "%s @ offset %06X %spointer" % (str,self.offset,dir)
    # These methods are used by objutil.py to interogate the RLD item
    def getAddend(self):
        # Extracts the address constant addend from the resident 
        # section's content
        bytes=str(self.ressect.bytes(self.offset,self.length))
        return rld.convert[self.length](bytes)
    def getAdjust(self):
        # This method returns how the address constants contents relates to
        # the base of section to which the address constant relates
        return self.direction
    def getPtrDir(self):
        # Return the direction of pointer addend
        return self.direction
    def getPtrID(self):
        # Returns the object format specific id of the section to which
        # the address constand actually points.  OBJX only has one segment
        # so return 1
        return 1
    def getResid(self):
        # This method returns the local id of the section in which this
        # relocation item phyiscally resides.  OBJX only has one segment
        # so return 1
        return 1
    def getResOff(self,base=0):
        # Return the offset into the section in which the address constant
        # resides.  objutil will provide the section's base for use by 
        # this method.  The object format may not require it.
        #
        # RLD items generated by z390 contain in the RLD address field an
        # an offset into the section where the address constant resides
        # This may not be consistent with HLASM - requires further research
        return self.offset
    def getRmode(self): # Need to access header for this information.
        pass
    def getSize(self):
        # Return the physical size of the address constant residing in the
        # section
        return self.length
    def getRtype(self):
        # Return the relocation type for this adcon
        # Use the length of the adcon for the type.  The length defines the 
        # algorithm
        return self.length
    def isRel(self):
        # This object format stores the adjustment value in the code area
        return True
    def isRela(self):
        # This object format does not store the adjustment outside of 
        # the code area
        return False
        
def usage():
    print("Usage: OBJX.py [dump|print| module")
        
if __name__=="__main__":
   args=sys.argv
   if len(args)<3:
       usage()
       sys.exit(1)
   obj=objx.create(args[2])
   #mod=pythonize.loadmodule(args[2])
   #obj=objx.pythonize(mod)
   if args[1]=="print":
       print(obj)
       sys.exit(0)
   if args[1]=="dump":
       print(obj.hexdump())
       sys.exit(0)
   print("Invalid option: %s" % args[1])
   usage()
   sys.exit(1)