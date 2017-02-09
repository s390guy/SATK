#!/usr/bin/python3
# Copyright (C) 2015, 2017 Harold Grovesteen
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

# This module creates IPL media from ASMA generated output:
#
#  - a list-directed IPL directory (created using ASMA option --gldipl)
#  - an image file (using ASMA option (created using ASMA option --image), or
#  - an absolute loader deck (created using ASMA option --object).


this_module="iplasma.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2015, 2017")

# Python imports
import sys
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse
import importlib
import os          # For stat method
import os.path


# Setup PYTHONPATH
import satkutil
satkutil.pythonpath("tools/ipl")

# SATK imports
import fbautil    # Access the FBA device support
from hexdump import dump   # Access the dump() function
import media      # Access the device independent and device specific modules
import recsutil   # Access the device record module


#
#  +----------------------+
#  |                      |
#  |   Useful Functions   |
#  |                      | 
#  +----------------------+
#

# Returns a value at the next higher aligned location from a supplied value
# For example, align(0x31,4) returns the next fullword aligned value (0x34)
def align(value,alignment):
    return ((value+alignment-1)//alignment)*alignment
    
# Returns a value at the preceding aligned location from a supplied value
# For example, align_down(0x31,4) returns the preceding fullword aligned value (0x30)
def align_down(valuet,alignment):
    return (value//alignment)*alignment

# Convert a signed or unsigned integer into a bytes list of one element
def byte(value):
    return bytes([value,])

# Convert a bytes list into a printable hex string
def bytes2hex(bin):
    h=""
    for b in bin:
        h="%s%02X" % (h,b)
    return h

# Convert an unsigned integer into a half word of two bytes
def hword(value):
    return value.to_bytes(2,byteorder="big")

# Convert a signed integer into a half word of two bytes
def hwords(value):
    return value.to_bytes(2,byteorder="big",signed=True)

# Convert an unsigned integer into a three-byte address
def addr3(value):
    return value.to_bytes(3,byteorder="big")

# Convert an unsigned integer into a full word of four bytes
def fword(value):
    return value.to_bytes(4,byteorder="big")

# Convert a signed integer into a full word of four bytes
def fwords(value):
    return value.to_bytes(4,byteorder="big",signed=True)


#
#  +------------------+
#  |                  |
#  |   Medium Error   |
#  |                  | 
#  +------------------+
#

# This exception raised by the volume creation process when it encounters an error
class MediumError(Exception):
    def __init__(self,msg=""):
        self.msg=msg
        super().__init__(self.msg)


#
# +---------------------------+
# |                           |
# |   __boot__.py Interface   |
# |                           |
# +---------------------------+
#

# The __boot__.py file allows the bootstrap loader to communicate its capabilities
# to this tool.  It must import from this module, instantiate the bootstrap class 
# and assign it to the __boot__.capabilities module variable:
#
#   import iplasma
#   capabilities=iplasma.bootstrap(parms as required)
# 
# This module will add the list-directed IPL directory to its PYTHONPATH, import
# the __boot__ module and then access the capabilities object.

class bootstrap(object):
    dtypes={"CARD":["3525",],
            "CKD":["2306","2311","2314","3330","3340","3350","3380","3390","9345"],
            "FBA":["0671","0671-04","3310","3370","3370-2","9332","9332-600","9313",
                   "9335","9336","9336-20"],
            "TAPE":["3410","3420","3422","3430","3480","3490","3590","8809","8347"]}

    def __init__(self,psw="IPLPSW.bin",asa="ASALOAD.bin",bootstrap="PROGRAM.bin",\
                 devices=[],traps=False,arch=False,ccw1=False,obj=False,\
                 directed=False,length=False):
        self.psw=psw                # Loader's entry PSW region
        self.asa=asa                # Loader's ASA initialization region
        self.bootstrap=bootstrap    # The loader's bare-metal program region
        self.traps=traps            # Whether it supports new PSW trap initialization
        self.arch=arch              # Whather it can change architectures
        self.ccw1=ccw1              # Whether it can use CCW1 (and channel subsystem)
        self.obj=obj                # Whether it supports object deck loading
        self.directed=directed      # Whether it supports directed record loading
        self.length=length          # Whether directed records require a length

        # Device types supported by the bootstrap loader
        self.types(devices)

    # Convert generic device type to numeric device type
    def types(self,dtype):
        if isinstrance(dtype,list) or not isinstance(dtype,str):
            self.devices=dtype
            return
        try:
            self.devices=bootstrap.dtypes[dtype.upper()]
        except KeyError:
            self.devices=dtype

#
# +------------------------------+
# |                              |
# |   Image File Encapsulation   |
# |                              |
# +------------------------------+
#

class Loadable(object):
    def __init__(self):
        self.load_lst=[]       # List of regions for loading onto medium

        # Establshed by loadable() method.  Each contains REGION objects
        self.bcmode=False   # Whether a manufactured PSW is to be in BC-mode.
        self.psw=None       # PSW REGION object if available
        self.asa=None       # ASA REGION object if available
        self.load_list=[]   # List of program REGION objects

    # Returns the high-water mark if the load-list regions.  Returns None if the
    # load list is empty.
    def hwm(self):
        hwm=None
        for region in self.load_list:
            if hwm is None:
                hwm=region.address+len(region)-1
            else:
                hwm=max(hwm,region.address+len(region)-1)
        return hwm

    # Returns the low-water mark if the load-list regions.  Returns None if the load
    # list is empty.
    def lwm(self):
        lwm=None
        for region in self.load_list:
            if lwm is None:
                lwm=region.address
            else:
                lwm=min(lwm,region.address)
        return lwm

    def loadable(self,psw=None,asa=None,bcmode=False,exc=[]):
        raise NotImplementedError("%s subclass %s must provide loadable method"\
            % (this_module,self.__class__.__name__))


class IMAGE(Loadable):
    def __init__(self,imgfile,load=0):
        super().__init__()

        # Set the absolute path to the LDIPL control file
        if os.path.isabs(imgfile):
            self.ifile=imgfile
        else:
            self.ifile=os.path.abspath(imgfile)

        # Make sure the image file actually exists
        if not os.path.exists(self.ifile):
            raise ValueError("%s - image file does not exist: %s"\
                % (this_module,self.ifile))

        self.image=self.__binary_read()
        self.load=load

    def __binary_read(self):
        try:
            fo=open(self.ifile,"rb")
        except IOError:
            raise ValueError("%s - could not open image file: %s" \
                % (this_module,filepath)) from None

        try:
            bindata=fo.read()
        except IOError:
            raise ValueError("%s - could not read image file: %s" \
                % (this_module,filepath)) from None
        finally:
            fo.close()

        return bindata

    def loadable(self,psw=None,asa=None,bcmode=False,exc=[]):
        if len(self.image)<10:
            return
        self.load_list=[REGION("IMAGE",self.load,self.image),]
        self.psw=REGION("PSW",0,self.image[0:8])


#
# +-----------------------------------------------+
# |                                               |
# |   List-Directed IPL Directory Encapsulation   |
# |                                               |
# +-----------------------------------------------+
#

class LDIPL(Loadable):
    def __init__(self,ctlfile):
        super().__init__()

        # Set the absolute path to the LDIPL control file
        if os.path.isabs(ctlfile):
            self.cfile=ctlfile
        else:
            self.cfile=os.path.abspath(ctlfile)

        # Make sure the control file actually exists
        if not os.path.exists(self.cfile):
            raise ValueError("%s - list-directed IPL control file does not exist: %s"\
                % (this_module,self.cfile))

        # Extract the directory in which the control file exists
        self.directory=os.path.dirname(self.cfile)

        # Identify regions and load addresses from the control file
        self.names={}        # Maps region name to is load address
        self.sequence=[]     # Preserves the region sequence from the control file
        self.__cfile_read()
        # Encapsulate REGIONS read from the LDIPL directory
        self.regions=self.__binary_read()  # Dictionary of REGION objects

        # Establshed by loadable() method.  Each contains REGION objects
        #self.bcmode=False   # Whether a manufactured PSW is to be in BC-mode.
        #self.psw=None       # PSW REGION object if available
        #self.asa=None       # ASA REGION object if available
        #self.load_list=[]   # List of program REGION objects

    # Read the LDIPL directory binary files identified in the control file
    def __binary_read(self):
        regions={}
        errors=0

        # Read binary image files from the LDIPL directory
        for binfile,address in self.names.items():
            filepath=os.path.join(self.directory,binfile)
            try:
                fo=open(filepath,"rb")
            except IOError:
                print("%s - could not open LDIPL binary file: %s" \
                    % (this_module,filepath))
                errors+=1
                continue
            error=False
            try:
                 bindata=fo.read()
            except IOError:
                print("%s - could not read LDIPL binary file: %s" \
                    % (this_module,filepath))
                errors+=1
                error=True
            finally:
                fo.close()
            if error:
                continue    
            ldipl=REGION(binfile,address,bindata)
            regions[ldipl.name]=ldipl

        if errors:
            raise ValueError("%s - one or more errors encountered while "
                "reading LDIPL directory: %s" % (this_module,self.directory))

        return regions

    # Read the LDIPL control file and analyze its contents
    def __cfile_read(self):
        try:
            fo=open(self.cfile,"rt")
        except IOError:
            raise ValueError("%s - could not open for reading control file: %s" \
                % (this_module,self.cfile)) from None

        lines=[]
        lineno=0
        names={}
        seq=[]
        try:
            for lineno,line in enumerate(fo):
                if len(line)==0 or line[0]=="#":
                    continue
                try:
                    ndx=line.index("#")
                    parms=line[:ndx]
                except ValueError:
                    parms=line
                parms=parms.strip()
                pieces=parms.split()
                if len(pieces)!=2:
                    raise ValueError("%s - unrecognized LDIPL control file "
                        "statement: %s\n[%s] %s" \
                        % (this_module,self.cfile,lineno+1,line))

                binfile=pieces[0]   # Identify the binary file in the directory

                # Process the load address
                address=pieces[1]
                if len(address)<=2 or address[:2]!="0x":
                    raise ValueError("%s - unrecognized LDIPL control file "
                        "address: %s\n[%s] %s" \
                        % (this_module,address,lineno+1,line))
                try:
                    address=int(address[2:],16)
                except ValueError as ve:
                    raise ValueError(\
                        "%s - unrecognized hexadecimal address '%s': %s\n[%s] %s" \
                        % (this_module,address,ve,lineno+1,line)) from None
                # address is now an integer
                names[binfile]=address
                seq.append(binfile)
        except IOError:
            raise ValueError("%s - could read control file at line %s: %s" \
                % (this_module,lineno+1,self.cfile)) from None
        finally:
            fo.close()

        self.names=names
        self.sequence=seq

    # Returns a list of REGION objects that require loading, excludes PSW and ASA
    # CCW or explicitly supplied IPL Record 1 regions or command-line list if 
    # specified.
    # Method Argumets:
    #   psw    IPL PSW region name
    #   asa    Assigned Storage Area initialization region name
    #   bcmode If a Basic-control mode PSW is to be generate, if needed
    #   exc    List of region names to be excluded, if present in the directory
    def loadable(self,psw=None,asa=None,bcmode=False,exc=[]):
        self.bcmode=bcmode   # Remember whether a BC-mode PSW might be needed
        exclude=exc          # Excluded region names
        load=[]              # Loaded program REGION objects by sequence
        if psw and psw not in exclude:
            try:
                self.psw=self.region(psw)
                exclude.append(psw)
            except KeyError:
                pass

        if asa and asa not in exclude:
            try:
                self.asa=self.region(asa)
                exclude.append(asa)
            except KeyError:
                pass

        for reg in self.sequence:
            if reg in exclude:
                continue
            load.append(self.regions[reg])

        self.load_list=load

    # Returns an individual REGION object
    # raises a KeyError if the the region is not found
    def region(self,name):
        return self.regions[name]


class LOADER(LDIPL):
    def __init__(self,ctlfile):
        super().__init__(ctlfile)

        # Import bootstrap loader __boot__.py module if requested
        self.bootcap=self.__import_boot()

        # Booted program boot records (Instances of BOOTREC)
        self.boot_records=[]

    # import __boot__.py from LDIPL bootstrap loader directory
    #
    # The __boot__.py module assumes the following content
    #   import iplasma
    #   capabilities=iplasma.bootstrap(parms...)
    def __import_boot(self):
        sys.path.append(self.directory)
        try:
            mod=importlib.import_module("__boot__")
            cap=mod.capabilities
        except ImportError:
            print("%s - import of __boot__.py for bootstrap loader failed: %s" \
                % (this_module,self.directory))
            cap=None
        sys.path.pop()   # Remove the directory from the PYTHONPATH
        return cap

    # Calculate the number of bootstrap records required for the booted program
    # by converting all of the loadable regions into boot records and returning the
    # number.
    #
    # The boot arguments is the booted program's LDIPL object
    def boot_recs(self,boot,recl):
        if self.bootcap.length:
            hdr=6
        else:
            hdr=4
        boot_len=recl-hdr

        for regn in self.load_list:
            self.boot_records.extend(self.region_to_bootrecs(regn,boot_len))

        return len(self.boot_records)

    # Bootstrap capabilities defines a bootstrap loader's PSW and ASA names,
    # not an external source.
    def loadable(self,psw=None,asa=None):
        return super().loadable(psw=self.bootcap.psw,asa=self.bootcap.asa)

    # Converts a REGION object into a list of BOOTREC objects
    def region_to_bootrecs(self,regn,boot_len):
        bdata=regn.bdata         # Complete region's binary content
        addr=regn.address        # The regions starting load address
        dlen=len(bdata)
        last_ndx=len(bdata)-1
        recs=[]
        for ndx in range(0,dlen,boot_len):
            chunk=bdata[ndx:min(ndx+bootlen,last_ndx)]
            recs.append(BOOTREC,addr,chunk)
            addr+=len(chunk)
        return recs


class BOOTREC(object):
    def __init__(self,address,bdata):
        self.address=address     # Address where the record is to be loaded
        self.bdata=bdata         # Binary content to be loaded

    def __len__(self):
        return len(self.bdata)

    # Returns the binary boot record
    def record(self,length=False):
        bytes=fullword(self.address)
        if length:
            bytes+=halfword(len(self))
        return bytes+self.bdata


class REGION(object):
    def __init__(self,name,address,bdata):
        self.name=name         # Region Name from LDIPL directory
        self.address=address   # load address of the binary content
        self.bdata=bdata       # bytes list of binary content

    def __len__(self):
        return len(self.bdata)

    def __str__(self):
        return "REGION(%s,0x%X,length=%s)" \
            % (self.name,self.address,len(self))


#
# +------------------------------+
# |                              |
# |   IPL Medium Creation Tool   |
# |                              |
# +------------------------------+
#

class IPLTOOL(object):
    dtypes={"CARD":"2525",
            "CKD":"3330",
            "FBA":"3310",
            "TAPE":"3420"}

    @staticmethod
    def load_list_names(llist):
        regions=""
        for reg in llist:
            regions="%s%s, " % (regions,reg.name)
        return regions[:-2]

    def __init__(self,args):
        self.args=args               # Command-line arguments
        self.verbose=args.verbose    # Whether to generate verbose messages

        # Perform general sanity check on input options
        self.fmt=args.format         # Source format string: 'image' or 'ld'
        self.source=args.source[0]   # Input file/path string

        self.__check_for_boot_options()  # when no bootstrap loader identified

        # Medium information
        self.medium=self.args.medium     # Path to emulated IPL capable medium
        self.recl=self.args.recl         # Bootstrap loader record length
        self.dtype=None                  # IPL device type
        self.seq=False                   # True if sequential device type
        self.volcls=None                 # IPLVOL subclass for output generation
        self.__set_dtype_info()

        # Size DASD volumes (ignored for other device types)
        sizing=self.args.size
        if sizing=="std":
            self.minimize=False
            self.compress=False
        elif sizing=="comp":
            self.minimize=True
            self.compress=True
        else: # Otherwize, assume the third choice 'mini'
            self.minimize=True
            self.compress=False

        # Loaded program content
        self.objdeck=None                # Object deck being loaded
        self.program=None                # program LDIPL directory (LDIPL object)
        self.bootstrap=None              # bootstrap LDIPL directory (LOADER object)
        self.pswreg=None                 # PSW argument if a region is specified
        self.bcpsw=False                 # True if a BC-mode PSW to be used

        # Bootstrap loader information
        self.recl=None                   # Bootstrap logical record length
        self.arch=None                   # Bootstrap loader changes architecture
        self.traps=None                  # Bootstrap loader set new PSW traps

        # Process --psw for mode or region name
        if self.args.psw:
            if self.args.psw=="ec":
                self.bcpsw=False
            elif self.args.psw=="bc":
                self.bcpsw=True
            else:
                self.pswreg=self.args.psw

        if self.fmt == "ld":
            # --fornat=ld
            self.program=LDIPL(self.source)

            # Baremetal program uses either the command line or default CCW
            # and IPL Record 1 region names, if used at all
            self.program.loadable(psw=self.pswreg,asa=self.args.asa,\
                bcmode=self.bcpsw,exc=self.args.noload)
            if len(self.program.load_list)==0:
                self.error("IPL program contains no loadable regions")

        elif self.fmt == "image":
            # --fornat=image (the default)
            try:
                load=int(self.args.load,16)
            except ValueError:
                raise ValueError("--load argument not hexadecimal: '%s'" \
                    % self.args.load) from None

            self.program=IMAGE(self.source,load=load)
            self.program.loadable()
            if len(self.program.load_list)==0:
                self.error("IPL image contain no loadable content")

        else:
            # Note: this should not occur, the argparser will recognize the
            # incorrent --format choice, but it also doesn't hurt.
            raise ValueError("%s unexpected --format option: %s" \
                % (this_module,self.fmt))

        if self.args.boot:
            self.boostrap=LOADER(self.args.boot)
            if not self.bootstrap.bootcap:
                self.error("bootstrap loader capabilities unknown, __boot__.py "
                    "module not found")

            # Bootstrap loader must use default region names
            self.bootstrap.loadable()

            if len(self.bootstrap.load_list)==0:
                self.error("IPL bootstrap loader contains no loadable regions")
            self.recl=self.args.recl
            self.arch=self.args.arch
            self.traps=self.args.traps
            if len(self.boostrap.load_list)!=1:
                self.error("bootstrap loader must contain only one loadable program "
                    "region: %s" % IPLTOOL.load_list_names(self.bootstrap.load_list))
            if len(self.bootstrap.psw)!=8:
                self.error("bootstrap loader PSW must be 64-bit PSW: %s" \
                    % len(self.bootstrap.psw)*8)

        if self.fmt == "object":
            if not self.seq:
                self.error("option --object requires sequential device "
                    "type, --dtype not sequential: %s" % self.dtype)
            if self.recl and self.recl!=80:
                print("%s - forcing --recl to 80 for option --object" % this_module)
            self.recl=80
            self.objdeck=self.__read_deck()

        if len(self.program.load_list)!=1 and self.bootstrap is None:
            self.error("option --boot required for multiple loadable program "
                "regions: %s" % IPLTOOL.load_list_names(self.program.load_list))

        self.ipl=None                    # Content participating in IPL function
        self.boot=None                   # Content loaded by bootstrap loader if any

        # Establish what content will participate in the IPL function and
        # what will be brought into memory by means of a bootstrap loader.
        # If a bootstrap loader (option --boot), is supplied it is always used.
        if self.bootstrap:
            self.ipl=self.bootstrap
            if self.objdeck:
                self.boot=self.objdeck
            else:
                self.boot=self.program
        else:
            self.ipl=self.program

    def __check_for_boot_options(self):
        args=self.args
        if args.boot:
            return
        if args.recl:
            print(\
                "%s - option --recl ignored, option --bldipl missing" % this_module)
        if args.arch:
            print(\
                "%s - option --arch ignored, option --bldipl missing" % this_module)
        if args.traps:
            print(\
                "%s - option --traps ignored, option --bldipl missing" % this_module)

    def __read_deck(self):
        filepath=self.source
        try:
            fo=open(filepath,"rb")
        except IOError:
            self.error("could not open object deck file: %s" % filepath)

        try:
            bindata=fo.read()
        except IOError:
            self.error("could not read object deck file: %s"% filepath)
        finally:
            fo.close()

        return bindata

    def __set_dtype_info(self):
        dtype=self.args.dtype
        try:
            # Convert generic device (CARD, CKD, FBA, TAPE) into the default 
            # hardware device type
            self.dtype=IPLTOOL.dtypes[dtype.upper()]
        except KeyError:
            # Otherwise assume it is a hardware device type presented
            self.dtype=dtype

        dtype=self.dtype
        types=bootstrap.dtypes

        # Validate hardware device types and prepare for volume creation
        if dtype in types["CARD"]:
            self.seq=True
            self.volcls=None
        elif dtype in types["TAPE"]:
            self.seq=True
            self.volcls=None
        elif dtype in types["CKD"]:
            self.seq=False
            self.volcls=None
        elif dtype in types["FBA"]:
            self.seq=False
            self.volcls=FBAVOL
        if not self.volcls:
            # self.volcls is initialized to None
            self.error("unsupported device type: %s" % self.args.dtype)

    def error(self,msg):
        print("%s - %s" % (this_module,msg))
        sys.exit(1)

    # Create IPL capable medium
    def run(self):
        ipl_load=self.ipl.load_list
        if len(ipl_load)==0:
            raise MediumError(msg="no loadable program content available")
        self.ipl_lwm=self.ipl.lwm()
        self.ipl_hwm=self.ipl.hwm()
        if self.ipl_hwm>0xFFFFFF and self.boot is None:
            raise MediumError(msg="bootstrap loader required for regions resident "
                "above X'FFFFFF', region high-water-mark: X'%08X'" % self.ipl_hwm)

        if isinstance(self.boot,LDIPL) and len(self.boot.load_list)==0:
            raise MediumError(msg="bootstrap loaded program contains no loadable "
                "program regions")

        # Create the IPL volume content
        volume=self.volcls(self.ipl,self.boot,self.dtype,verbose=self.verbose)
        if self.verbose:
            print(volume)
        volume.build()  # Convert LDIPL/LOADER/IMAGE objects into medium content

        # Create the emulated volume
        volume.create(self.args.medium,\
            minimize=self.minimize,\
            comp=self.compress,\
            progress=True,debug=False)
        # At this point the emulated medium has been written and closed

        # Output success message
        filesize=os.stat(self.args.medium).st_size
        print("%s - emulated medium %s created with file size: %s" \
            % (this_module,self.args.medium,filesize))

        # If requested dump the volume records
        if self.args.records:
            volume.dump()


#
# +--------------------------------+
# |                                |
# |   Generic Allocation System    |
# |                                |
# +--------------------------------+
#

# These classes form the basis for a generic allocation system managing and
# allocating resource slots, for example:
#   -  Memory management
#   -  FBA DASD sector management
#   -  CKD DASD track management
#
# In each case, the base classes are expected to be subclassed for the specific
# context.
#
# Classes:
#    Alloc       Base class for a specific type of resource management
#    Allocation  Base class for a named allocated portion of the resource slots
#    Range       Base class representing a one or more allocated sequential resource 
#                slots.


# This is the base class that manages allocations of some "unit".  Units are
# numbered from 0 to n-1, where 'n' is the maximum unit available.  The base
# class operates on generic units.  The generic units location may be derived from
# a complex of 
# Instance Arguments:
#    maximum   The maximum number of slots available
#    protected Specify True to ensure requested allocations do not overlap existing
#              allocations.  Useful for device media.
class Alloc(object):
    def __init__(self,slots,protected=False,format="s"):
        self.slots=slots          # Number of of allocatable slots
        self.next=0               # Next available slot
        self.allocs={}            # Dictionary of Allocations by name
        self.protected=protected  # Whether allocated areas by overlap
        self.format=format        # Default format type for range values

    # Returns the presented Allocation after it has been assigned a range succeeding 
    # another named allocation
    def after(self,name,alloc,align=1):
        assert isinstance(alloc,Allocation),"alloc must be an Allocation object: %s"\
            % alloc
        target=self.alloc(name)
        alloc.range=target.range.after(len(alloc),align=align,format=self.format)
        return alloc

    # Adds an Allocation to the managed slots
    def allocate(self,alloc):
        assert isinstance(alloc,Allocation),"alloc must be an Allocation object: %s"\
            % alloc
        loc=alloc.range
        assert loc is not None,"alloc not assigned a range"
        assert loc.end < self.slots,"alloc extends beyond last slot " \
            "(0x%X): %s" % (self.slots,area.loc)
        assert alloc.name is not None,"can not allocate unnamed Allocation"
        name=alloc.name

        # Detect overlap if slot allocations must not overlap
        if self.protected:
            for p in self.allocs.values():
                ploc=p.range
                if ploc.overlap(loc):
                    raise ValueError("allocation %s (%s) overlaps another: %s (%s) "
                        "%s (%s)" % (name,loc,p.name,ploc))

        # Accept the allocation if not already established
        try:
            self.allocs[alloc.name]
            raise ValueError("Allocation name already exists: %s" % name)
        except KeyError:
            self.allocs[alloc.name]=alloc
        self.next=max(self.next,loc.follow)

    # Retrieves an allocation based upon its name
    def allocation(self,name):
        try:
            return self.allocs[name]
        except KeyError:
            raise ValueError("undefined allocation: %s" % name) from None

    # Returns the Allocation after it has been assigned a range preceding another 
    # named allocation
    def before(self,name,alloc,align=1):
        assert isinstance(alloc,Allocation),"alloc must be an Allocation object: %s"\
            % alloc
        target=self.alloc(name)
        alloc.range=target.range.before(len(alloc),align=align,format=self.format)
        return alloc

    # This method checks that slots are integers.
    # Because slots are always integers, this method must NOT be overridden
    def check_slots(self,slots):
        if not isinstance(slots,int):
            raise ValueError("Location units must be an integer: %s" % slots)

    # Create a printable version of the allocations
    def display(self,indent=""):
        string=""
        #for x in self.allocs.values():
        for x in sorted(self.allocs.values(),key=lambda a: a.range.beg):
            string="%s\n%s%s: %s" % (string,indent,x.name,x.range)
        return string[1:]

    # Finds all Allocation's starting at a given slot
    def find(self,slot):
        found={}
        for a in self.allocs.values():
            loc=a.range
            if loc.beg == slot:
                found[a.name]=a
        return found

    def here(self,alloc):
        assert isinstance(alloc,Allocation),"alloc must be an Allocation object: %s"\
            % alloc
        alloc.range=Range(self.next,alloc.slots)
        return alloc

  #
  # Overridden methods for context unit to managed slot conversions
  #

    # This method validates that the context units are integers.
    # Subclass must override this method if the context units are not integers.
    # Returns the 
    def check_units(self,units):
        if not isinstance(units,int):
            raise ValueError("Location subunits must be an integer: %s" % units)
        return units

    # Converts slots to context units.
    # Default behavior assumes there is a one-to-one correspondence between managed
    # slots and context integer units.  
    # Override in a subclass if the context requires different behavior.
    # Returns:  The presented slots as context unit integers
    # Exception:
    #   ValueError if slots is not an integer
    def from_slots(self,slots):
        return self.check_slots(slots)

    # Returns the slots associated with the presented context units.
    # The default behavior assumes there is a one-to-one correspondence between context
    # integer units and managed slots.
    # Override in a subclass if the context requires different behavior.
    # Returns:  The presented context units as managed slots
    # Exception:
    #   ValueError if context units is not an integer
    def to_slots(self,units):
        return self.check_units(units)


class Allocation(object):
    def __init__(self,name,slots=None):
        self.name=name        # A name identifying the allocation, required
        self.slots=slots      # Number of units consumed by this allocation
        self.range=None       # Beginning and ending allocated slots

    # Returns the number of managed slots required/used by the allocation
    def __len__(self):
        if self.slots is None:
            return 0
        return self.slots

    def __str__(self):
        if range is None:
            return "%s: length: %s" % (self.name,len(self))
        return "%s: %s" % (self.name,self.range)

    # Establishes the allocation's position from a beginning slot as a Range.  
    def position(self,begin,format="s"):
        assert self.slots is not None,"can not position allocation %s because its "\
            "size has not been established" % self.name
        self.range=Range(begin,self.slots,format=format)

    # Establishes the Allocation's size in slots if its position as not been
    # established
    def size(self,slots):
        assert self.range is None,"allocation %s range already established: %s" \
            % (self.name,self.range)
        self.slots=slots
        

# Define an allocation range in terms of managed slots
# Instance Arguments:
#   beg     Beginning slot of the range of slots
#   size    Number of slots consumed by the range.
#   format  Integer format string used when creating a diplayable version of the
#           Range.
class Range(object):
    @staticmethod
    # Create a Range object based upon a beginning and ending slot number
    def slots(beg,end):
        assert beg<end,"begining slot (%s) must precede ending slot %s" \
            % (beg,end)
        return Range(beg,(end-beg)+1)

    # Define an area of memory independent of binary content
    def __init__(self,beg,size,format="s"):
        assert size>0,"range size must be greater than zero: %s" % size
        assert beg>=0,"range begining slot must not be negative: %s" % beg
        self.beg=beg              # First managed slot of the range
        self.end=beg+size-1       # Last managed slot of the range
        self.follow=beg+size      # Managed slot following this range
        self.format=format        # Format string for slots, defaults to 's'

    # Returns the length of the range in slots
    def __len__(self):
        return self.end-self.beg+1

    # Presents the decimal range.  Overrided in subclass for other behavior
    def __str__(self):
        fstr="%" + self.format + "-%" + self.format
        return fstr % (self.beg,self.end)

    # Return the range managed slot following this range
    def after(self,size,align=1,format="s"):
        return Range(align(self.follow,align=align),size,format=format)

    # Create a range succeeding this range of a given size and alignment
    def before(self,size,align=1,format="s"):
        return Range(align_down(self.beg-size),size,format=format)

    # Determines whether two ranges are identical or not
    def equal(self,other):
        assert isinstance(other,Range),"range equality requires another Range:%s" \
            % other
        return self.beg == other.beg and self.end == other.end

    # Extend the Range by the specified slots
    def extend(self,size):
        self.end+=size
        self.follow+=size

    # Test for an overlap with another range
    # Returns True if the ranges overlap, False otherwise
    def overlap(self,other):
        assert isinstance(other,Range),"range object required for overlap: %s" % other
        if other.end<self.beg or other.beg>self.end:
            return False
        return True

    # Returns True if an address or range is within this range
    def within(self,other):
        if isinstance(other,int):
            return self.beg <= other and self.follow > other
        if isinstance(other,Range):
            return self.beg <= other.beg and self.end >= other.end   


#
# +-----------------------------+
# |                             |
# |   Hierarchical Structures   |
# |                             |
# +-----------------------------+
#

# Base class for an object defining a structure.  Always subclassed.
# Instance Arguments:
#   length     Define the length of the structure (see size() method)
#   address    Specify the structure's address (see loc() method)
#   mloc       Specify where the structure resides on a medium (see mloc() method)
#   align      Specify any required alignment of the structure
#
# Attribute Related Methods:
#   __len__  * Returns the object's length via the Python builtin function len()
#   ck_bin     Validates that an externally supplied bytes list conforms to the
#              objects current length
#   loc      * Assigns a memory location to the structure
#   mloc       Assigns a device medium location to the structure
#   size       Set the objects required binary length
#
# Binary Content Related Methods:
#   binary   * Returns the object into a bytes list of binary data.  Must be supplied
#              by a subclass of BaseStruct but not a subclass of CompoundStruct.
#   set_bin    Sets the objects binary content to the externally derived  bytes list
#              provided it conforms to the objects length.
#   build    * Uses binary() method to build the objects binary content and then
#              assigns it to the object using the set_bin() method.
#
# * These methods are overriden by the CompoundStruct subclass.
class BaseStruct(object):
    def __init__(self,length=None,address=None,mloc=None,align=1):
        self.length=length       # Binary length of the structure
        self.address=address     # Address of this structure when determined
        self.media=mloc          # Locate the structure on a medium (optional)
        self.alignment=align     # Any required memory alignment of the structure

        # Set by the build() or set_bin() methods
        self.content=None        # Sets binary data to the structure

    # Returns the length of the BaseStruct, overriden by CompoundStruct
    def __len__(self):
        if self.length is None:
            return 0
        return self.length

    # Create binary content, validate its length and set self.content
    def build(self):
        bdata=self.binary()
        self.set_bin(bdata)

    # Validates binary data length. used by CompoundStruct
    def ck_bin(self,bdata):
        assert self.length is not None,"%s - %s object requires a length" \
            % (this_module,self.__class__.__name__)
        if len(bdata)!=self.length:
            raise ValueError("%s - binary data not of length %s: %s" \
                % (this_module,self.length,len(bdata)))

    # Set the memory address of the structure. overridden by CompoundStruct
    # Method Arguments:
    #   address   The address to which the structure is being assigned.  Must be
    #             aligned to structure's alignment requirements
    def loc(self,address):
        if address!=align(address,self.alignment):
            raise ValueError("%s - address 0x%X not aligned: %s" \
                % (this_module,address,self.alignment))
        self.address=address

    # Set the structures medium location.  used by CompoundStruct
    def mloc(self,mloc):
        self.media=mloc

    # Preserve the structure's binary content.  used by CompoundStruct
    def set_bin(self,bdata):
        self.ck_bin(bdata)
        self.content=bdata

    # Set the length of the structure.  used by CompoundStruct
    def size(self,length):
        self.length=length

    # Returns a bytes list of the structure
    # Subclass must supply this method.  Supplied by CompoundStruct
    def binary(self):
        raise NotImplementedError("%s - subclass %s requires binary() method" \
            % (this_module,self.__class__.__name__))


# This class provides the same interface for a structure composed of multiple
# structures 
class CompoundStruct(BaseStruct):
    def __init__(self,length=None,address=None,mloc=None,align=1):
        super().__init__(length=length,address=address,mloc=mloc,align=align)
        self.elements=[]

    # Return the length of the CompoundStructure
    def __len__(self):
        length=0
        for e in self.elements:
            length+=len(e)
        return length

    # Add an element to the compound structure
    def append(self,element):
        assert isinstance(element,BaseStruct),"%s - element must be an instance of "\
            "BaseStruct: %s" % (this_module,element)
        self.elements.append(element)

    # Build the entire structure, and pad if necessary
    def build(self,pad=False):
        bdata=bytes(0)
        for n,e in enumerate(self.elements):
            try:
                e.build()
                bdata+=e.content
            except ValueError as ve:
                raise ValueError("%s - element %s %s" % (this_module,n,ve))
        if pad and len(bdata)<self.length:
            bdata+=bytes(self.length-len(bdata))
        self.set_bin(bdata)

    # Assign a location to the compound structure and each of its elements
    def loc(self,address):
        super().loc(address)
        addr=self.address
        for e in self.elements:
            e.loc(addr)
            addr+=len(e)

    # Creates the binary content of the compound structure
    def binary(self):
        bdata=bytearray()
        for e in self.elements:
            bdata=bdata+e.binary()
        return bdata


#
# +-----------------------------+
# |                             |
# |   Input/Output Structures   |
# |                             |
# +-----------------------------+
#

# CCW Commands:
CKD_RDATA=0x06    # CKD READ DATA command
CKD_SEEK=0x07     # CKD SEEK cylinder and track command
CKD_SIDEQ=0xB1    # CKD SEARCH ID EQUAL command
IPLREAD=0x02      # READ IPL command
TIC=0x08          # TRANSFER IN CHANNEL command
FBA_READ=0x42     # FBA Read Sectors command
FBA_LOC=0x43      # FBA Locate blocks command
READ=0x02         # Unit record read command

# CCW flags:
CD=0x80           # Chain data
CC=0x40           # Command chain
SLI=0x20          # Suppress length indication
SKIP=0x10         # Skip data

# FBA Locate Operations
FBAL_WRITE=0x01   # Write data
FBAL_RDREP=0x02   # Read replicated data
FBAL_FORMT=0x04   # Format defective sectors
FBAL_WRTVR=0x05   # Write data and verify
FBAL_READ =0x06   # Read sectors


# Defines a Format-0 Channel Command Word
class CCW0(BaseStruct):
    def __init__(self,command,iolen,ioarea,flags=0,address=None,mloc=None):
        super().__init__(length=8,address=address,mloc=mloc,align=8)

        self.command=command          # Channel command
        self.iolen=iolen              # I/O area length
        self.ioarea=ioarea            # I/O area location
        self.flags=flags              # Command flags

    def binary(self):
        bdata=byte(self.command)      # +0 1 Command
        bdata+=addr3(self.ioarea)     # +1 3 IOAREA
        bdata+=bytes([self.flags,0])  # +4 2 flags, X'00'
        bdata+=hword(self.iolen)      # +6 2 IOLEN
        return bdata
        
    # Turn off command chaining
    def last(self):
        self.flags &= (255-CC)

class TICCCW(CCW0):
    def __init__(self,ioarea,address=None,mloc=None):
        super().__init__(TIC,1,ioarea,address=address,mloc=mloc)


# CKD DASD Record ID.  May double as a seek location by preceding it with 2 zero bytes
# Padding allows positioning of following data
class CKDID(BaseStruct):
    def __init__(self,cc,hh,r,seek=False,pad=0,address=None,mloc=None):
        length=5+pad
        if seek:
            sk=2
        else:
            sk=0
        length+=sk
        super().__init__(length=length,address=address,mloc=mloc)

        self.cc=cc       # Cylinder of CKD record ID
        self.hh=hh       # Track of CKD record ID
        self.r=r         # Record number of CKD record ID
        self.seek=sk     # Number of seek pad bytes before CKDID
        self.pad=pad     # Number of trailing pad bytes (if used typically 1)

    def binary(self):
        bdata=bytes(self.seek)
        bdata+=hword(self.cc)
        bdata+=hword(self.hh)
        bdata+=byte(self.r)
        bdata+=bytes(self.pad)
        return bdata


# CKD SEEK parmaters
class CKDSEEK(BaseStruct):
    def __init__(self,cc,hh,address=None,mloc=None):
        super().__init__(length=6,address=address,mloc=mloc)
        
        self.cc=cc      # Seek cylinder
        self.hh=hh      # Seek track

    def binary(self):
        bdata=bytes(2)
        bdata+=hword(self.cc)
        bdata+=hword(self.cc)
        return bdata


# Defines FBA LOCATA command parameters
class FBALOC(BaseStruct):
    def __init__(self,operation,sector,sectors,repl=0,address=None,mloc=None):
        super().__init__(length=8,address=address,mloc=mloc)
        self.opr=operation                    # FBA Locate operation
        self.sector=sector                    # FBA starting sector
        self.sectors=sectors                  # FBA number of sectors
        self.repl=repl                        # FBA replication count

    def binary(self):
        bdata=bytes([self.opr,self.repl])     # +0 2  Oper, replication
        bdata+=hword(self.sectors)            # +2 2  Number of sectors
        bdata+=fword(self.sector)             # +4 4  Starting sector
        return bdata


# Defines one or more zero filled bytes
class ZEROS(BaseStruct):
    def __init__(self,zeros,address=None,mloc=None):
        super().__init__(length=zeros,address=address,mloc=mloc)
        self.zeros=zeros           # Number of binary zero bytes to create

    def binary(self):
        return bytes(self.zeros)


#
# +--------------------------+
# |                          |
# |   Program-Status Words   |
# |                          |
# +--------------------------+
#

class PSWBC(BaseStruct):
    def __init__(self,masks,sys,prog,IA,address=None,mloc=None):
        super().__init__(length=8,address=address,mloc=mloc,align=8)
        self.masks=masks
        self.sys=sys
        self.prog=prog
        self.IA=IA

    def binary(self):
        bdata=bytes([self.masks,self.sys,0,0,self.prog])
        bdata+=addr3(self.IA)
        return bdata


class PSWEC(BaseStruct):
    def __init__(self,masks,sys,prog,IA,AM=24,address=None,mloc=None):
        super().__init__(length=8,address=address,mloc=mloc,align=8)
        self.masks=masks      # Interruption masks
        self.sys=sys | 0x80   # System masks
        self.prog=prog        # Progam masks and condition code
        self.IA=IA            # Instruction address
        if AM == 24:
            self.AM=0
        elif AM==31:
            self.AM=0x80000000
        else:
            raise ValueError("%s - PSW address mode invalid: %s" \
                % (this_module,AM))

    def binary(self):
        bdata=bytes([self.masks,self.sys,self.prog,0])
        bdata+=fword(self.ia | self.AM)
        return bdata

#
# +----------------------------------+
# |                                  |
# |   Initial Program Load Records   |
# |                                  |
# +----------------------------------+
#


# Basic IPL Record 1.  Various structures are added to it when built.
class IPLREC1(CompoundStruct):
    def __init__(self):
        super().__init__(align=8)
        
    # Mark last element added CCW read sequence as the last
    def last(self):
        ele=self.elements[-1]
        assert isinstance(ele,CCW0),\
            "%s - last IPLREC1 element must be a CCW0 object: %s" % (this_module,ele)

        ele.last()


# Basic CCW's of IPL Record 0
class IPLREC0_CCWS(CompoundStruct):
    def __init__(self):
        super().__init__(align=8)


#
# +------------------------+
# |                        |
# |   Memory Management    |
# |                        |
# +------------------------+
#


# Define memory content with or without an assigned address
class Area(Allocation):
    def __init__(self,name,beg=None,bytes=None):
        if bytes:
            self.content=bytearray(bytes)  # Create area with initial content
        else:
            assert beg is None,"can not assign a position to an empty area"
            self.content=bytearray()       # Create area with empty bytearray

        super().__init__(name,slots=len(self))
        if beg is not None:
            self.position(beg,format="06X")
            
        self.media=None          # Locate the area on a medium.  See mloc() method

    # Return the length of the area
    def __len__(self):
        return len(self.content)

    # Print a hexadecimal dump of the area
    def dump(self,indent=""):
        if self.media:
            print("%s Medium: %s" % (indent,self.media))
        print(dump(self.content,start=self.range.beg,indent=indent))

    # Extend the area, updating its range if available
    def extend(self,bytes):
        self.content.extend(bytes)
        if loc:
            self.reassign(self.begin)

    # Set the area's medium location.
    def mloc(self,mloc):
        self.media=mloc

    # Reassign a range to the area
    def reassign(self,beg,align=1):
        assert self.range is not None,"area must already be assigned for reassignement"
        self.loc=Range(beg,len(self.content))


class Memory(Alloc):
    def __init__(self,maximum=0xFFFFFF):
        super().__init__(maximum,format="06X")


#
# +-------------------------+
# |                         |
# |   Logical IPL Volume    |
# |                         |
# +-------------------------+
#

# Defines and builds the IPL Medium
# Instance Arguments:
#   program   The LDIPL object associated with the bare-metal program or bootstrap
#             loader
#   boot      The LDIPL object associated with the booted program if a bootstrap
#             loader is used.  Otherwise must be None
#   dtype     IPL volume device medium
#   bc        Specify True to cause a basic-control mode PSW to be manufactered.
#   verbose   Whether detailed messages are to be displayed
class IPLVOL(object):
    def __init__(self,program,boot,dtype,bc=False,verbose=False):
        self.verbose=verbose     # Whether verbose messages enabled
        self.dtype=dtype         # Physical volume device type
        self.program=program     # LDIPL or LOADER or IMAGE object of IPL'd program
        self.psw=program.psw     # PSW region of IPL'd program
        self.asa=program.asa     # ASA initialization image region
        self.boot=boot           # LDIPL of booted program or objdeck
        self.deck=isinstance(boot,bytes)  # Whether booted program is an object deck
        self.mem=Memory()        # Memory management

        self.areas=[]            # List of areas requiring medium locations
        
        # Areas created during object instantiation
        self.lod1=None           # LOD1 record area
        self.prog_areas=[]       # Bare-metal program areas (regions) being IPL'd
        self.asa_area=None       # ASA  Assigned Stroage Area initialization
        self.psw_area=None       # PSW  The PSW used to enter the bare-metal program
        self.boot_hwm=None       # Booted program's hwm
        self.ipl_hwm=None        # IPL program hwm
        self.hwm=None            # Location where IPL Record 1 is read

        # Areas created by build() method
        self.r1_area=None        # IPL1 IPL Record 1 area
        self.r0_area=None        # IPL0 IPL Record 0 area
        self.ccw_area=None       # CCW0 CCWs used in IPL Record 0
        self.preads=[]           # List of device reads for reading the program

        # Start creation of LOD1 if needed
        if self.boot and not self.deck:
            # Create LOD1 with the medium independent information
            self.boot_hwm=self.boot.hwm()
            self.lod1=self.create_LOD1()
            self.areas.append(self.lod1)

        # Create IPL program areas
        self.ipl_hwm=self.program.hwm()
        for reg in self.program.load_list:
            parea=self.region_to_area(reg.name,reg,debug=False)
            self.prog_areas.append(parea)
            self.areas.append(parea)

        # Establish HWM for locating IPL Record 1 in memory
        if self.boot_hwm:
            self.hwm=align(max(self.ipl_hwm,self.boot_hwm),8)
        else:
            self.hwm=align(self.ipl_hwm,8)
        if verbose:
            print("%s - IPL HWM:  %06X" % (this_module,self.ipl_hwm))
            if self.boot_hwm:
                print("%s - Boot HWM: %06X" % (this_module,self.boot_hwm))
            print("%s - Used HWM: %06X" % (this_module,self.hwm))

        # Create ASA area
        if self.asa:
            self.asa_area=self.region_to_area("ASA",self.asa,debug=False)
            self.areas.append(self.asa_area)
        # Create PSW area
        if self.psw:
            self.psw_area=self.region_to_area("PSW",self.psw)
            # PSW area is part of IPL record 0.  The area itself is not mapped to
            # a medium location

        # Construct program portion of IPL Record 0, the IPL PSW
        self.ipl_psw=self.set_IPLPSW(debug=False)  # Destined for IPL Record 0
        if verbose:
            print("%s - IPL PSW: %s" % (this_module,bytes2hex(self.ipl_psw)))
        # Construction from this point forward is performed by the medium specific
        # subclass, whose initialization follows from here.
        # Once both classes have been initialized, the build() method creates
        # content dependent on the medium specific subclass supplied methods

    def __str__(self):
        ipl=self.program.__class__.__name__
        boot=""
        if self.boot:
            if self.deck:
                boot=" BOOT: DECK"
            else:
                boot=" BOOT: LDIPL"
        return "%s IPL: %s%s" % (self.dtype,ipl,boot)

    # Generic build process for all IPL media types
    def build(self):
        # IPL Record 1 constructed
        self.r1_area=self.set_IPL1("IPL1",debug=False)
        self.mem.allocate(self.r1_area)
        if self.verbose:
            print("%s - IPL Record 1:" % this_module)
            self.r1_area.dump(indent="    ")
        self.ipl_r1=self.r1_area.content

        # Construct the device specific portion of IPL Record 0, the one/two CCW's
        self.ccw_area=self.set_IPLCCW("CCW0",debug=False)
        if self.verbose:
            print("%s - IPL Record 0 - CCWs:" % this_module) 
            self.ccw_area.dump(indent="    ")
        self.mem.allocate(self.ccw_area)

        # IPL Record 0 can now be constructed
        self.r0_area=Area("IPL0",beg=0,\
            bytes=self.ipl_psw+self.ccw_area.content)
        self.mem.allocate(self.r0_area)
        if self.verbose:
            print("%s - IPL Record 0:" % this_module) 
            self.r0_area.dump(indent="    ")

        if self.verbose:
            print("Memory Map:")
            print(self.mem.display(indent="    "))
            
        # Write the IPL records to the volume.  The subclass must handle any
        # physical sequencing issues.
        self.write_IPL0()
        self.write_IPL1()
        self.write_areas()  # The bare-metal program regions
        if self.asa_area:
            self.write_IPL3()
        if self.lod1:
            raise NotImplementedError()
            # Need to complete boostrap program processing

    def create_LOD1(self):
        raise NotImplementedError()

    # Converts a REGION object into an Area object, registering the Area with memory
    # and returning the resulting Area object.
    def region_to_area(self,name,region,debug=False):
        assert isinstance(region,REGION),"region must be a Region object: %s" % region
        if debug:
            print("region_to_area(): %s: %s" % (name,region))
        area=Area(name,beg=region.address,bytes=region.bdata)
        self.mem.allocate(area)
        return area

    # Two sources of IPL1 exist:
    #   - a IPL Record 1 region (identified by --r1 argument/default name) or
    #   - created by the tool
    # This method returns the IPL Record 1 memory area and content 
    def set_IPL1(self,name,debug=False):
        return self.ipl_rec1(name)

    # Two source for IPL CCW's exist:
    #  - a CCW region (identified by the --ccws argument/default name) or
    #  - created by the tool from IPL Record 1
    def set_IPLCCW(self,name,debug=False):
        return self.ipl_ccw(name,debug=debug)

    # There are multiple sources for the IPL PSW in IPL Record 0 depending upon
    # what is loaded where.
    #  1. bare-metal region loaded at 0 - use it for the IPL PSW and put a disabled
    #                       wait PSW in R0
    #  2. ASA loaded at 0 - use if for the IPL PSW and put a disabled wait PSW in R0
    #                       ASA will overwrite the start of IPL2
    #  3. PSW loaded at 0 - if ASA, update it with the PSW and proceed with case 2
    #                     - if no ASA, use the PSW in R0
    #  4. Create a PSW based upon IPL2 being loaded elsewhere in R0
    # For both cases 1 and 2, the disabled wait will get overwritten
    # Returns the bytes constituting the IPL PSW placed in IPL Record 0
    def set_IPLPSW(self,debug=False):
        at0=self.mem.find(0)
        # This dictionary is of areas by area name
        # The priority is:
        #   1. Explicit PSW area (PSW)
        #   2. Program region loaded at address 0
        #   3. ASA area (ASA)
        #   4. Program load point other than 0 (no region loaded at 0)
        load_list=self.program.load_list

        IPL2=None
        for n in range(len(load_list)-1,0,-1):
            reg=load_list[n]
            reg=at0.get(reg)
            if reg:
                IPL2=reg
                break

        PSW=at0.get("PSW")
        ASA=at0.get("ASA")

        at_zero=[]   # List of regions loaded at 0 in IPL function sequence
        # This sequence defines the priority of the source.
        if PSW:
            psw_len=len(PSW)
            if psw_len == 8:
                at_zero.append(PSW)
            elif psw_len == 16:
                raise MediumError(msg="128-bit IPL PSW requires option --bldipl")
            elif psw_len !=8:
                raise MediumError(msg="IPL PSW invalid length: %s" % psw_len)

        if IPL2:
            ipl2_len=len(IPL2)
            if ipl2_len<8:
                raise MediumError(msg="bare-metal program region does not contain "
                    "an IPL PSW: length is %s" % ipl2_len)
            at_zero.append(IPL2)

        if ASA:
            asa_len=len(ASA)
            if asa_len<8:
                raise MediumError(msg="assigned storage area region does not contain "
                    "an IPL PSW: length is %s" % asa_len)
            at_zero.append(ASA)

        if __debug__:
            if debug:
                areas="at_zero areas: "
                for a in at_zero:
                    areas="%s%s, " % (areas,a.name) 
                print(areas[:-2])

        # If only one region loaded at zero, use that for the IPL Record 0
        # Most likely this is the IPL PSW for the bare-metal program (although
        # it might not).
        if len(at_zero)==1:
            ipl_region=at_zero[0]
            return ipl_region.content[0:8]

        # No regions are loaded at 0, so manufacture a PSW from the program's starting
        # address
        if len(at_zero)==0:
            # Use the first byte of the first region loaded as the program entry
            load_point=self.program.load_list[0]
            load_point=load_point.range.beg
            hwords,odd=divmod(load_point,2)
            if odd != 0:
                raise MediumError(msg="Program starting location not on an half work "
                    "boundary, PSW can not be created: %06X" % load_point)
            address=load_point.to_bytes(3,byteorder="big")
            if self.program.bcmode:
                psw=PSWBC(0,0,0,load_point)
            else:
                psw=PSWEC(0,0,0,load_point)
            return psw.binary()

        # More than one region loaded at 0, so need to update the one loaded last with
        # the higher priority PSW.
        high_pri=at_zero[0]   # The first area in the list is the higher priority
        low_pri=at_zer0[-1]   # The last area in the list is loaded last
        psw=high_pri.content[0:8]
        # Update the last area to be loaded with it
        low_pri.content[0:8]=psw
        # And return it as the IPL Record 0 PSW.
        return psw

    # Creates the emulated IPL volume
    def create(self,path,minimize=True,comp=False,progress=False,debug=False):
        raise NotImplementedError("%s - class %s must provide create() method" \
            % (this_module,self.__class__.__name__))

    # Dumps to the console the IPL medium's records
    def dump(self):
        raise NotImplementedError("%s - class %s must provide dump() method" \
            % (this_module,self.__class__.__name__))

    # Returns the area containing the IPL CCW's destined for IPL Record 0
    def ipl_ccw(self):
        raise NotImplementedError("%s - class %s must provide ipl_ccw() method" \
            % (this_module,self.__class__.__name__))

    # Returns the area containing IPL Record 1
    def ipl_rec1(self,name):
        raise NotImplementedError("%s - class %s must provide ipl_rec1() method" \
            % (this_module,self.__class__.__name__))

    # Returns the maximum record length supported by the volume
    def max_recl(self):
        raise NotImplementedError("%s - class %s must provide max_recl() method" \
            % (this_module,self.__class__.__name__))

    # Assign a medium location to an area
    def mloc(self):
        raise NotImplementedError("%s - class %s must provide mloc() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 0 - IPL PSW + first IPL CCWs
    def write_IPL0(self):
        raise NotImplementedError("%s - class %s must provide write_IPL0() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 1 - remaining IPL CCWs
    def write_IPL1(self):
        raise NotImplementedError("%s - class %s must provide write_IPL1() method" \
            % (this_module,self.__class__.__name__))

    # Write Bere-metal program regions as IPL records (1 or more)
    def write_areas(self):
        raise NotImplementedError("%s - class %s must provide write_areas() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 3 - Assigned Storage Area initialization
    def write_IPL3(self):
        raise NotImplementedError("%s - class %s must provide write_IPL3() method" \
            % (this_module,self.__class__.__name__))

   # Write IPL Record 4 - Bootstrap Loader LOD1 record
    def write_IPL4(self):
        raise NotImplementedError("%s - class %s must provide write_IPL4() method" \
            % (this_module,self.__class__.__name__))


#
# +--------------------------+
# |                          |
# |   FBA DASD IPL Volume    |
# |                          |
# +--------------------------+
#

class FBAVOL(IPLVOL):
    def __init__(self,program,boot,dtype,verbose=False):
        super().__init__(program,boot,dtype,verbose=verbose)      

        recsutil.fba.strict=False   # Turn off global flag for strict sector sizes

        self.info=fbautil.fba_info(dtype)
        if verbose:
            print(self.info)

        self.device=media.device(self.dtype)
        self.maxsect=65535//512         # Maximum sectors in a single read
        self.maxrecl=self.maxsect*512   # Maximum record length (65,024)
        self.maxipl1=512-24             # Maximim IPL Record 1 length

        self.fbamap=FBAMAP(self.info.sectors)
        self.fbamap.assign("IPL0",1)
        self.fbamap.assign("VOLLBL",1)
        if self.asa_area:
            self.fbamap.assign("ASA",1)
        if self.lod1:
            self.fbamap.assign("LOD1",1)
        for area in self.prog_areas:
            self.fbamap.assign(area.name,FBAMAP.sectors(len(area)))

        if verbose:
            print("FBA DASD Map:")
            print(self.fbamap.display(indent="    "))

        # Assign medium locations to areas
        for area in self.areas:
            sectors=self.fbamap.allocation(area.name)
            sector=sectors.range.beg
            area.mloc(sector)

    # Create the FBA Volume
    def create(self,path,minimize=True,comp=False,progress=False,debug=False):
        self.device.create(path=path,\
            minimize=minimize,comp=comp,progress=progress,debug=debug)

    # Dump the FBA volume sectors
    def dump(self):
        for r in self.device.sequence:
            print(r.dump())

    # Return the Area associated with the IPL CCW's of IPL Record 0
    def ipl_ccw(self,name,debug=False):
        # IPL Record 0 elements
        # self.iplpsw provided by my super class, IPLVOL
        self.iplccw1=CCW0(IPLREAD,512,self.iplrec1_start,CC) # Reread all of sector 0
        self.iplccw2=TICCCW(self.iplrec1_start+24)    # TIC to IPL Record 1 CCWs

        ccws=IPLREC0_CCWS()
        ccws.append(self.iplccw1)
        ccws.append(self.iplccw2)
        ccws.loc(8)
        ccws.length=16
        ccws.build()

        return Area(name,beg=ccws.address,bytes=ccws.content)

    # Returns the memory area of IPL Record 1
    def ipl_rec1(self,name,debug=False):
        # Locate where in memory IPL Record 1 will be loaded
        # For FBA this must follow the last sector read for the program.  Assume
        # the worst case secnario and simply add 512, aligning it to double words.
        self.iplrec1_start=align(self.hwm+512,8)

        # IPL Record 1 elements
        # Define how the IPL loaded content is read from the volume
        self.ipl_reads=[]
        self.ipl_reads.extend(self.prog_reads())
        if self.asa_area:
            self.ipl_reads.append(self.setup_read(self.asa_area,"ASA"))
        if self.lod1:
            self.ipl_reads.append(\
                FBAREAD(0x200,self.fbamap.allocation("LOD1").beg,1))

        # Build IPL Record 1
        #  - locate CCW ----+
        #  - read CCW       |
        #  etc              |
        #                   |
        #  - locate parms <-+
        #  etc.
        iplrec1=IPLREC1()
        recl=0

        # Add read sequence CCW's to the record
        for rd in self.ipl_reads:
            item=rd.locccw
            iplrec1.append(item)
            recl+=len(item)
            item=rd.readccw
            iplrec1.append(item)
            recl+=len(item)
        iplrec1.last()       # Identify the last read in the sequence
        
        # Add LOCATE CCW parameters to the IPL REC
        for rd in self.ipl_reads:
            item=rd.locparms
            iplrec1.append(item)
            recl+=len(item)
        iplrec1.length=recl
        iplrec1.loc(self.iplrec1_start+24)
        for rd in self.ipl_reads:
            rd.update_locccw()
        iplrec1.build()

        content=iplrec1.content
        if len(content)>self.maxipl1:
            raise MediumError(\
                msg="Use boostrap loader - IPL Record 1 exceeds maximum supported "
                    "length (%s): %s" % (self.maxipl1,len(content)))

        return Area(name,beg=iplrec1.address,bytes=content)

    # Return the maximum record length supported by the volume
    def max_recl(self):
        return self.maxrecl
    
    # Assign starting sector to area
    def mloc(self,area):
        assert isinstance(area,Area),\
            "%s - area must be an instance of Area: %s" % (this_module,area)
        # Because IPL0 and IPL1 are combined into a single sector, only assign
        # a starting sector to IPL0.  Ignore a request for IPL1.
        if area.name=="IPL1":
            return
        area.mloc(self.fbamap.allocation(area.name))

    # Returns a list of FBAREAD objects for the load list and preserves it in
    # self.preads attribute for later use.  Each individual region is also
    # broken up into binary content to be written to the volume (and of course
    # later read during the IPL function).
    def prog_reads(self):
        reads=[]
        max_read=self.max_recl()
        for area in self.prog_areas:
            content=area.content
            area_len=len(area)
            area_secs=FBAMAP.sectors(area_len)
            beg_sec=area.media
            cur_sec=beg_sec
            addr=area.range.beg
            for ndx in range(0,area_len,max_read):
                chunk=content[ndx:min(ndx+max_read,area_len)]
                chunk_len=len(chunk)
                sectors=FBAMAP.sectors(chunk_len)
                read=FBAREAD(address=addr,sector=cur_sec,sectors=sectors)
                read.content=chunk
                reads.append(read)
                cur_sec+=sectors
                addr+=chunk_len
            assert area_secs == cur_sec-beg_sec,"%s %s region read sectors (%s) "\
                "does not match FRAREAD sectors (%s)" \
                    % (this_module,area.name,area_secs,cur_sec-beg_sec)
        self.preads=reads
        return reads    

    # Set up I/O data for reading a single record
    def setup_read(self,area,fbaname):
        sectors=self.fbamap.allocation(fbaname)
        num_sect=len(sectors)
        return FBAREAD(area.range.beg,sectors.range.beg,num_sect)

    # Writes bare-metal program region content to the volume.  Content prepared
    # by the prog_reads() method.
    def write_areas(self):
        reads=self.preads
        for rd in reads:
            content=rd.content
            end=len(content)
            sec=rd.sector
            for beg in range(0,end,512):
                chunk=content[beg:min(beg+512,end)]
                rec=recsutil.fba(data=bytes(chunk),sector=sec)
                self.device.record(rec)
                sec+=1

    # Write IPL Record 0 - IPL PSW + first IPL CCW's
    def write_IPL0(self):
        ipl0=self.r0_area.content
        ipl0+=self.r1_area.content
        sector=self.fbamap.allocation("IPL0")
        rec=recsutil.fba(data=bytes(ipl0),sector=sector.range.beg)
        self.device.record(rec)     # Add Sector 0 to FBA volume

    # Write IPL Record 1 - Rest of IPL CCW's
    def write_IPL1(self):
        # Do not need to do anything.  IPL Record 1 included in IPL Record 0's sector
        pass

    # Write IPL Record 3 - Assigned Storage Initialization
    def write_IPL3(self):
        sector=self.fbamap.allocation("ASA")
        ipl3=self.asa_area.content
        rec=recsutil.fba(data=bytes(ipl3),sector=sector.range.beg)
        self.device.record(rec)
        
    # Write IPL Record 4 - Bootstrap Loader LOD1 record
    def write_IPL4(self):
        sector=self.fbamap.allocation("LOD1")

        # Create LOD1 sector content. LOD1 sector gets read at 0x200
        lod1=bytes(64)            # Leave space for Hercules IPL parameters
        lod1+=self.lod1.content   # Add the actual LOD1 record data

        rec=recsutil.fba(data=lod1,sector=sector.range.beg)
        self.device.record(rec)


# Reading one or more sectors from a FBA volume requires three components:
#  - LOCATE command parameters identifying the sectors to be read
#  - LOCATE CCW that passes the LOCATE parameters to the disk and
#  - READ CCW that actually reads the sectors.
# For construction purposes these three elements are constructed together for each
# set of sectors read and later separated into contiguous areas when IPL Record 1
# is built.
class FBAREAD(object):
    def __init__(self,address,sector,sectors):
        self.locparms=FBALOC(FBAL_READ,sector,sectors)
        self.locccw=CCW0(FBA_LOC,8,None,CC)
        self.readccw=CCW0(FBA_READ,sectors*512,address,CC)
        
        # Optional attributes for content assigned to the read sequence
        self.sector=sector
        self.content=None

    # Update the LOCATE CCW with the address of its parameters
    def update_locccw(self):
        self.locccw.ioarea=self.locparms.address


class FBAMAP(Alloc):
    @staticmethod
    def sectors(length):
        return (length+511)//512
    def __init__(self,sectors):
        super().__init__(sectors,protected=True)

    def assign(self,name,sectors):
        self.allocate(self.here(Allocation(name,slots=sectors)))


#
# +----------------------------------------+
# |                                        |
# |   Command-Line Argument Definitions    |
# |                                        |
# +----------------------------------------+
#
# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,
        epilog=copyright, 
        description="create a IPL capable medium in Hercules device emulation format")

  # Input arguments:

    # Source input file (Note: attribute source in the parser namespace will be a list)
    parser.add_argument("source",nargs=1,metavar="FILEPATH",\
        help="input source path for --in argument")

    parser.add_argument("-f","--format",choices=["image","ld","object"],\
        default="image",\
        help="format of input source: "\
             "'image' for ASMA --image output file, "\
             "'ld' for ASMA --gldipl output control file "\
             "'object' for ASMA --object absolute load deck. "\
             "Defaults to 'image'. 'object' also requires --boot option.")

    # Input generic list directed IPL control file
    #parser.add_argument("-g","--gldipl",metavar="FILEPATH",
    #    help="identifies the location of the input bare-metal program list directed "
    #         "IPL file converted to an IPL capable medium.  Incompatible with "
    #         "option --object.")

    # Input image information
    #parser.add_argument("-i","--image",metavar="FILEPATH",\
    #    help="identifies the location of the input image file.  Incompatible with "\
    #         "option --gldipl")

    # Input image load address
    parser.add_argument("--load",metavar="ADDRESS",default="0",\
        help="the hexadacimal memory address at which the image file is loaded. "
             "Defaults to 0")

    # List directed IPL directory's region whose first eight bytes contains the 
    # IPL PSW
    parser.add_argument("--psw",metavar="FILENAME",default="IPLPSW.bin",
        help="region containing the bare-metal program's entry PSW. "
             "If region does not exist, the region identified by the --asa option or "
             "the location of the region specified by the --bare option defines the "
             "entry location.")

    # List directed IPL directory's region initializing the assigned storage area
    parser.add_argument("--asa",metavar="FILENAME",default="ASALOAD.bin",
        help="region containing the assigned storage area.  Ignored if region does "
             "not exist")

    # Input object deck file name
    #parser.add_argument("-o","--object",metavar="FILEPATH",
    #    help="input loadable object deck converted into IPL an IPL capable medium. "
    #         "Incompatible with option --gldipl")

  # Output IPL medium arguments
    # Output emulated IPL medium device type
    parser.add_argument("-d","--dtype",metavar="DTYPE",default="FBA",
        help="device type of output IPL medium. Defaults to FBA")

    # Output emulated IPL medium
    parser.add_argument("-m","--medium",metavar="FILEPATH",required=True,
        help="created output emulated medium.  Required.")

    # Causes the filename in the list-directed IPL directory to be ignored
    parser.add_argument("-n","--noload",metavar="FILENAME",default=[],\
        action="append",
        help="ignore region file when loading the program. Multiple "
             "occurences allowed.")
    
    # Specify the DASD sizing
    parser.add_argument("-s","--size",choices=["std","mini","comp"],default="mini",
        help="Specify the sizing of a DASD volume. 'std' creates a full sized volume "
             "as specified by the --dtype option.  'mini' creates a minimal mini "
             "disk to be created with the attributes of --dtype.  'comp' creates "
             "a Hercules compression eligible (but not compressed) mini disk with "
             "the attributes specified by the --dtype option.  Genarally the "
             "relationship of the sizing options are: mini  <=  comp  <= std. "
             "Defaults to 'mini'.")

    # Option causes the IPL records to be dumped.
    parser.add_argument("--records",default=False,action="store_true",\
        help="Dumps volume record content in hex.")

  # Bootstrap loader arguments
    # Bootstrap loader list directed IPL control file
    # The regions and capabilites of the bootstrap loader are defined in its 
    # __boot__.capabilities object created in its __boot__.py file, an instance of 
    # class bootstrap defined above.
    parser.add_argument("-b","--boot",metavar="FILEPATH",
        help="bootstrap loader list-directed IPL control file path")

    # Bootstrap loader record length
    parser.add_argument("-r","--recl",metavar="SIZE",type=int,
        help="bootstrap loader record syze in bytes. If omitted, default size "
             "suported by the selected bootstrap loader used.")

    # Enables verbose messages
    parser.add_argument("-v","--verbose",default=False,action="store_true",\
        help="enable verbose message generation")

    # Request bootstrap loader to change architecture before entering program
    parser.add_argument("--arch",choices=["change","64"],metavar="ACTION",
        help="change architecture before entering program and optionally set AMODE "
             "to 64")

    # Request bootstrap loader to set trap PSW's before entering bare-metal program
    parser.add_argument("--traps",action="store_true",default=False,
        help="set new PSW traps before entering bare-metal program")

    return parser.parse_args()

if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    tool=IPLTOOL(args)
    try:
        tool.run()
    except MediumError as me:
        tool.error(me.msg)
