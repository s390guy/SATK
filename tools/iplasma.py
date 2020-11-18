#!/usr/bin/python3
# Copyright (C) 2015-2020 Harold Grovesteen
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
#
# Other than the absolute loader deck, the image file and a list-directed IPL
# directory may be either a bare-metal program that is IPL'd or a bare-metal
# program that is boot loaded by another bare-metal program initiated via IPL.
#
# The absolute loader deck requires both a card reader device and a boot loader
# for execution.
#
# Boot loaders may only be implemented using a list-directed IPL directory.
#
# In all cases, the image file, list-directed IPL directory or absolute loader
# deck is created by ASMA, as indicated above.
#
# Again, with the exception of an absolute loader deck, the list-directed IPL
# directory and image file are converted to an instance of a Loadable object.
#
# The following subclasses of Loadable are used:
#    - IMAGE for a bare-metal program executed via an IPL from an image file
#    - LDIPL for a bare-metal program executed via an IPL from the directory
#    - LOADER for a boot loader executed by an IPL from the directory
#    - BOOTED for a LDIPL directory loaded by a boot loader
#    - BOOTEDIMAGE for an image file loaded by a boot loader
#
# Ultimately all Loadable objects consist of REGION objects.  In the case
# of an image file, the regions are manufactured from the IMAGE file.  In the
# case of a list directed IPL directory, the regions are created from
# the directory itself.


this_module="iplasma.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2015-2020")

# Python imports
import sys
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse
import os          # For stat method
import os.path


# Setup PYTHONPATH
import satkutil
satkutil.pythonpath("tools/ipl")

# SATK imports
import fbautil    # Access the FBA device support
import fbadscb    # Access the FBA data set control block definitions (for VOL1)
from hexdump import dump   # Access the dump() function
import media      # Access the device independent and device specific modules
import rdrpun     # Access the CARD device support
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
# +-----------------------------------+
# |                                   |
# |     File Content Encapsulation    |
# |                                   |
# +-----------------------------------+
#

# The base class for loaded content from outside of iplasma.py itself (except
# for an absolute object deck).
#
#    Loadable - base class
#       IMAGE - subclass for an image file that participates in IPL
#           BOOTEDIMAGE - subclass for a booted image file.
#       LDIPL - subclass for a list-directed IPL directory
#           BOOTED - subclass for a list-directed IPL directory that is booted

class Loadable(object):

    # Converts a REGION object into a sequence of directed load records,
    # BOOTREC objects.
    #
    # Method Arguments:
    #   regn    A REGION object
    #   recl    Maximum data length NOT including the header
    # Returns:
    #   tuple[0] - cummulative length of the region's content
    #   tuple[1] - a list of BOOTREC object from which directed load
    #              records can be created on the IPL medium
    #
    # Note: The directed load header will be added to the binary data
    # when the BOOTREC object is converted into binary data.
    @staticmethod
    def region_to_bootrecs(regn,recl):
        #print("called Loadable.region_to_bootrecs(%s,%s)" \
        #    % (regn,recl))
        assert isinstance(regn,REGION),"%s.Loadable.region_to_bootrecs - "\
            "'regn' argument must be a REGION object: %s" \
                % (this_module,regn)
        bdata=regn.bdata         # Complete region's binary content
        addr=regn.address        # The regions starting load address
        dlen=len(bdata)          # Total REGION binary data being booted
        last_ndx=len(bdata)    # Last index of the binary data
        recs=[]
        cumlen=0
        for ndx in range(0,dlen,recl):
            chunk=bdata[ndx:min(ndx+recl,last_ndx)]
            #print("%s.Loadable - region_to_bootrecs() - len(chunk): %s" \
            #    % (this_module,len(chunk)))
            recs.append(BOOTREC(addr,chunk))
            addr+=len(chunk)
            cumlen+=len(chunk)
            #print("%s.Loadable - region_to_bootrecs() - cumlen: %s" \
            #    % (this_module,cumlen))

        return (cumlen,recs)

    def __init__(self):
        # Establshed by subclass supplied loadable() method.
        self.bcmode=False   # Whether a manufactured PSW is to be in BC-mode.
        self.psw=None       # PSW REGION object if available
        self.asa=None       # ASA REGION object if available
        self.load_list=[]   # List of program REGION objects

        # Directed load records when using a boot loader
        self.cum_len=0         # Cumulative length of all BOOTREC objects
        self.boot_records=[]   # List of BOOTREC objects
        # Note: this list is empty for LDIPL, LOADER and IMAGE objects.
        # It only contains elements when the Loadable is a BOOTED or
        # BOOTEDIMAGE object.

    # Calculate the number of boot records required for the booted program
    # by converting all of the loadable regions into boot records.
    #
    # Method Arguments
    #    recl     Maximum record length of directed load records
    #    length   Whether directed records' headers contain a length field.
    #             Specify True if they do.  Specify False if they do not.
    #             Defaults to False.
    # Returns:
    #    the number of directed load records required on the medium
    # Note: This method MUST be called AFTER self.loadable()
    def boot_recs(self,recl,length=False):
        if length:
            hdr=6
        else:
            hdr=4
        boot_len=recl-hdr

        for regn in self.load_list:
            regn_len,recs=Loadable.region_to_bootrecs(regn,boot_len)
            self.cum_len+=regn_len
            self.boot_records.extend(recs)

        if len(self.boot_records) > 0:
             last_rec=self.boot_records[-1]
             last_rec.islast()

        return len(self.boot_records)

    # Returns the high-water mark of the load-list regions.  Returns None if the
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

    # Produces a description of the loadable object as a series of strings.
    def description(self,indent=""):
        raise NotImplementedError("%s subclass %s must provide description method"\
            % (this_module,self.__class__.__name__))


    # Creates a list of program containing REGION objects.
    # IPL PSW (from --psw), ASA (from --asa) are excluded from this list.
    # The PSW or ASA are dealt with explicitly.
    def loadable(self,psw=None,asa=None,bcmode=False,exc=[]):
        raise NotImplementedError("%s subclass %s must provide loadable method"\
            % (this_module,self.__class__.__name__))


#
# +----------------------------------+
# |                                  |
# |   Generic Progam Encapsulation   |
# |                                  |
# +----------------------------------+
#

class PROGRAM(object):
    def __init__(self,controls):
        assert isinstance(controls,(IMAGE_CTLS,LDIPL_CTLS)),\
            "%s.%s - __init__() - 'controls' argument must be either an " \
                "IMAGE_CTLS or LDIPL_CTLS object: %s" \
                    % (this_module,self.__class__.__name__,\
                        controls.__class__.__name__)

        # Manages the state of the object.  Certain methods may be required
        # in a specific order.  This attribute allows the object to understand
        # what has been done.
        self.state=0    # Initialize state
        # 1 => loadable() method has been called
        # 2 => ensure_psw() method has been called

        # File/Directory control object
        self.controls=controls

        # These attributes are established by the loadable() method
        self.psw=None         # Program's IPL region (if any)
        self.asa=None         # Program's ASA region (if any)
        self.load_list=[]     # Program's executable content, required

    # This method analyzes the REGION objects retrieved or created from
    # the program file or directory to ensure a PSW region exists.  If not
    # it will create one from the available data.
    #
    # Exceptions:
    #   AssertionError when...
    #     Load list does not contain any loadable regions
    #   ValueError when...
    #     1. Invalid object state detected - bug
    #     2. IPL PSW region does not start at address 0x0 - user fixes
    #     3. IPL PSW region does not contain a PSW (too short) - user fixes
    def ensure_psw(self,bcmode=False):
        if self.state != 1:
            raise ValueError("%s.%s - ensure_psw() state not 1: %s" \
                % (this_module,self.__class__.__name__,self.state))

        if self.psw:
            # Have a PSW region, just make sure it is valid.
            if self.psw.address != 0:
                raise ValueError("%s.%s - ensure_psw() IPL PSW region, %s, not at "\
                    "address 0: %s" % (this_module,self.__class__.__name__,\
                        self.psw.name,self.psw.address))
            if len(self.psw)<8:
                raise ValueError("%s.%s - ensure_psw() IPL PSW region, %s, does not "\
                    "contain a PSW, length: %s" % (this_module,\
                        self.__class__.__name__,self.psw.name,len(self.psw)))
            # Good to go...
            self.state=2
            return

        if self.asa and self.asa.address == 0 and len(self.asa) >= 8:
            # Use ASA as the PSW source
            self.psw=REGION("ASAPSW",0,self.asa.bdata[0:8])
            self.state=2
            return

        # Otherwise use the first REGION in the load list as the program entry
        assert len(self.load_list)>=1,\
            "%s.%s - ensure_psw() load list has no loadable regions" \
                % (this_module,self.__class__.__name__)

        if bcmode:
            psw=PSWBC(0,0,0,self.load_list[0].address).binary()
        else:
            psw=PSWEC(0,0,0,self.load_list[0].address).binary()
        self.psw=REGION(psw.__class__.__name__,0,psw.binary())
        self.state=2   # ensure_psw() called

    # Creates a list of program containing REGION objects.
    # IPL PSW (from --psw), ASA (from --asa) are excluded from this list.
    # The PSW or ASA are dealt with explicitly.
    def loadable(self,psw=None,asa=None,bcmode=False,load=None,exc=[]):
        if self.state != 0:
            raise ValueError("%s.%s - loadable() state not 0: %s" \
                % (this_module,self.__class__.__name__,self.state))

        self.psw,self.asa,self.load_list=\
            self.controls.loadable(psw=psw,asa=asa,bcmode=False,load=load,\
                exc=[])

        self.state=1   # Indicate loadable() has been called.

#
# +----------------------------------------+
# |                                        |
# |   Absolute Object Deck Encapsulation   |
# |                                        |
# +----------------------------------------+
#

class DECK_CTLS(object):
    def __init__(self,deck_path):

        # Set the absolute path to the IMAGE file
        if os.path.isabs(deck_path):
            self.dfile=imgfile
        else:
            self.dfile=os.path.abspath(deck_path)

        # Make sure the image file actually exists
        if not os.path.exists(self.dfile):
            raise ValueError("%s - absolute deck file does not exist: %s"\
                % (this_module,self.dfile))

        # Bytes sequence of the absolute object file
        self.deck=self.__read_deck(self.dfile)

    # This method reads binary data as an object deck.
    # Returns:
    #   the object deck file as a list of bytes.
    def __read_deck(self,dfile):
        filepath=self.source
        try:
            fo=open(dfile,"rb")
        except IOError:
            self.error("could not open object deck file: %s" % dfile)

        try:
            bindata=fo.read()
        except IOError:
            self.error("could not read object deck file: %s"% dfile)
        finally:
            fo.close()

        return bindata


#
# +------------------------------+
# |                              |
# |   Image File Encapsulation   |
# |                              |
# +------------------------------+
#

# This class encapsulates the interface to an IMAGE file ndependent of the
# role played within the loading process by the file.  Used for either an
# IMAGE file that is an IPL'd program (an IMAGE object) or a booted program
# (a BOOTEDIMAGE object).
#
# Instance Arguments:
#
#   img_path   File path to the image file
#
class IMAGE_CTLS(object):
    def __init__(self,img_path):

        # Set the absolute path to the IMAGE file
        if os.path.isabs(img_path):
            self.ifile=imgfile
        else:
            self.ifile=os.path.abspath(img_path)

        # Make sure the image file actually exists
        if not os.path.exists(self.ifile):
            raise ValueError("%s - image file does not exist: %s"\
                % (this_module,self.ifile))

        # Bytes sequence of the image file
        self.image=self.__binary_read(self.ifile)

    def __len__(self):
        return len(self.image)

    def __binary_read(self,ifile):
        try:
            fo=open(ifile,"rb")
        except IOError:
            raise ValueError("%s - could not open image file: %s" \
                % (this_module,ifile)) from None

        try:
            bindata=fo.read()
        except IOError:
            raise ValueError("%s - could not read image file: %s" \
                % (this_module,ifile)) from None
        finally:
            fo.close()

        return bindata

    # Returns a list of bare-metal program elements:
    #
    # Method Arguments:
    #   psw    PSW region name for LDIPL.  None for IMAGE file
    #   asa    ASA region name for LDIPL.  None for IMAGE file
    #   bcmode True if a manufactured PSW uses BC-mode.  False otherwise
    #   load   IMAGE file load point.  None for LDIPL file
    #   exc    List of excluded regions (from --noload)
    # Returns: a tuple
    #   tuple[0]  The PSW REGION object, required
    #   tuple[1]  The ASA REGION object or None
    #   tuple[2]  a list of loaded REGION objects excluding a PSW or ASA region
    def loadable(self,psw=None,asa=None,bcmode=False,load=None,exc=[]):
        if len(self.image)<10:
            # At least an IPL PSW and one instruction required
            return
        load_list=[REGION("IMAGE",load,self.image),]
        psw=REGION("PSW",0,self.image[0:8])
        return (psw,None,load_list)

# IMAGE file as an IPL'd program
class IMAGE(Loadable):
    def __init__(self,imgfile,load=0,booted=False):
        self.isbooted=booted    # Whether this object is bootable
        super().__init__()

        self.load=load          # Load address of the image (from --load)

        # Read the IMAGE file
        self.img_ctls=IMAGE_CTLS(imgfile)
        self.program=PROGRAM(self.img_ctls)
        self.program.loadable(psw=None,asa=None,load=self.load)

        self.psw=None
        self.asa=None
        self.load_list=[]

    def directed(self,recl,length=False):
        raise NotImplementedError(\
            "%s.%s - directed() - %s can not be booted, must be a BOOTEDIMAGE object"\
                % (this_module,self.__class__.__name__,self.__class__.__name__))


class BOOTEDIMAGE(IMAGE):
    def __init__(self,imgfile,load=0):
        super().__init__(imgfile,load=0,booted=True)

        # Attributes set by self.directed() method
        self.records=0        # Number of directed records

    # Builds a list of BOOTREC objects used by the boot loader.
    #
    # Method Arguments:
    #   recl    The maximum record length of a directed boot record
    #           Includes the header(s) as required by the device.
    #   length  Specify True if the header includes a 2-byte length field
    #           following the 4-btye address field.  Specify False if no
    #           length field is used.  Defaults to False
    def directed(self,recl,length=False):
        self.records=self.boot_recs(recl,length=length)
        # As a side effect, self.boot_records is now set to a list of
        # BOOTREC objects and self.cum_len contains the length of all booted
        # program data.


#
# +-----------------------------------------------+
# |                                               |
# |   List-Directed IPL Directory Encapsulation   |
# |                                               |
# +-----------------------------------------------+
#

# This class encapsulates the interface to a LDIPL directory independent
# of the role played within the loading process by the file.  Used for
# either LDIPL IPL'd program or IPL'd LOADER directory or booted program BOOTED
# directory.
#
# Instance Arguments:
#
#   ctl_path   File path to the LDIPL control file
#   psw_name   PSW region file name (whether present or not)
#   asa_file   ASA region file name (whether present or not
class LDIPL_CTLS(object):
    def __init__(self,ctl_path,psw_name,asa_name):
        self.ctl_path=ctl_path   # From command line 'source' or '--boot'
        self.psw_name=psw_name   # From command line '--psw' or '--lpsw'
        self.asa_name=asa_name   # From command line '--asa' or '--lasa'

        # Region and load address management.  Created by __cfile_read()
        self.names={}      # Maps region name to its load address
        # Preserves the region name's sequence in the control file
        self.sequence=[]

        # Region objects read from the LDIPL directory.
        # Created by __binary_read()
        regions={}

        # Set the absolute path to the LDIPL control file
        if os.path.isabs(self.ctl_path):
            self.cfile=self.ctl_path
        else:
            self.cfile=os.path.abspath(self.ctl_path)

        # Make sure the control file actually exists
        if not os.path.exists(self.cfile):
            raise ValueError("%s - list-directed IPL control file does not exist: %s"\
                % (this_module,self.cfile))

        # Extract the directory in which the control file exists
        self.directory=os.path.dirname(self.cfile)

        # Identify regions and load addresses from the control file
        self.names={}        # Maps region name to its load address
        self.sequence=[]     # Preserves the region sequence from the control file

        self.__cfile_read()  # Creates self.names and self.sequence
        # Uncaught ValueErrors may occur

        # Encapsulate REGIONS read from the LDIPL directory
        self.regions=self.__binary_read()  # Dictionary of REGION objects
        # Uncaught ValueErrors may occur

    # Read the LDIPL directory binary files identified in the control file
    #
    # Returns a list of REGION objects
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

    # Read the LDIPL control file and analyzes its contents
    #
    # Exceptions:
    #   ValueError if an error condition occurs.
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

    # Returns a list of bare-metal program elements.
    # Required by PROGRAM object
    #
    # Method Arguments:
    #   psw    PSW region name for LDIPL.  None for IMAGE file
    #   asa    ASA region name for LDIPL.  None for IMAGE file
    #   bcmode True if a manufactured PSW uses BC-mode.  False otherwise
    #   load   IMAGE file load point.  None for LDIPL file
    #   exc    List of excluded regions (from --noload)
    # Returns: a tuple
    #   tuple[0]  The PSW REGION object, required
    #   tuple[1]  The ASA REGION object or None
    #   tuple[2]  a list of loaded REGION objects excluding a PSW or ASA region
    def loadable(self,psw=None,asa=None,bcmode=False,load=None,exc=[]):
        #print("LDIPL.loadable() - psw:%s asa:%s bcmode:%s exc:%s" \
        #    % (psw,asa,bcmode,exc))
        self.bcmode=bcmode   # Remember whether a BC-mode PSW might be needed
        exclude=exc          # Excluded region names
        load=[]              # Loaded program REGION objects by sequence
        if psw and psw not in exclude:
            try:
                mypsw=self.region(psw)
                print("LDIPL: setting self.psw: %s" % self.psw)
                exclude.append(psw)
            except KeyError:
                mypsw=None

        if asa and asa not in exclude:
            try:
                myasa=self.region(asa)
                exclude.append(asa)
            except KeyError:
                myasa=None

        for reg in self.sequence:
            if reg in exclude:
                continue
            load.append(self.regions[reg])

        return (mypsw,myasa,load)

    # Returns an individual REGION object
    # Exception:
    #    KeyError if the the region is not found
    def region(self,name):
        return self.regions[name]


# A Bare-Metal Program from a List-Directed IPL Directory
#
# Instance Arguments:
#    ctlfile    LDID control file name
#    psw_file   Filename of the LDID psw region
#    asa_file   Filename of the LDID asa region
#    booted     Whether this KDID is booted (True) or IPL'd (False)
class LDIPL(Loadable):

    def __init__(self,ctlfile,psw_file,asa_file,bcmode=False,exc=[],booted=False):
        self.isbooted=booted       # Whether this object is booted
        super().__init__()

        self.controls=LDIPL_CTLS(ctlfile,psw_file,asa_file)
        self.program=PROGRAM(self.controls)
        self.program.loadable(psw=psw_file,asa=asa_file,bcmode=bcmode,exc=exc)

        self.psw=self.program.psw
        self.asa=self.program.asa
        self.load_list=self.program.load_list

    # Print worthy description as a string
    def description(self,indent=""):
        if self.psw:
            lines="%sPSW   %s" % (indent,self.psw.description())
        else:
            lines="%sPSW    None" % indent
        if self.asa:
            if self.isbooted:
                ign="  IGNORED"
            else:
                ign=""
            lines="%s\n%sASA   %s%s" \
                % (lines,indent,self.asa.description(),ign)
        else:
            lines="%s\n%sASA    None" % (lines,indent)
        if len(self.load_list) == 0:
            lines="%s\n%sLoad   None" % (lines,indent)
        elif len(self.load_list) == 1:
            lines="%s\n%sLoad  %s" \
                % (lines,indent,self.load_list[0].description())
        else:
            lines="%s\n%sLoad List:" % (lines,indent)
            for regn in self.load_list:
                lines="%s\n%s    %s" % (lines,indent,regn.description())
        return lines

    def directed(self,recl,length=False):
        raise NotImplementedError(\
            "%s.%s - directed() - %s can not be booted, must be a BOOTED object"\
                % (this_module,self.__class__.__name__,self.__class__.__name__))


# A Booted Program from a LDIPL directory
#
# Instance Arguments:
#    source   This booted program's LDID control file
#    psw_file This booted program's LDID psw file name
#    asa_file This booted program's LDID asa file name
#    hdr_len  Whether the two byte length field is contained within the directed
#             load header.
class BOOTED(LDIPL):

    def __init__(self,source,psw_file,asa_file,bcmode=False,exc=[],hdr_len=False):
        super().__init__(source,psw_file,asa_file,bcmode=bcmode,exc=exc,\
            booted=True)

        self.program.ensure_psw()
        self.psw=self.program.psw

        self.hdr_len=hdr_len  # Whether directed records have a length field
        # Attributes set by self.directed() method
        self.records=0        # Number of BOOTREC objects in the list
        self.boot_records=[]  # List of BOOTREC objects loaded by boot loader

    # Builds a list of BOOTREC objects used by the boot loader.
    #
    # Method Arguments:
    #   recl    The maximum record length of a directed boot record
    #           Includes the header(s) as required by the device.
    #   length  Specify True if the header includes a 2-byte length field
    #           following the 4-btye address field.  Specify False if no
    #           length field is used.  Defaults to False
    def directed(self,recl,length=False):
        #print("called %s.directed(%s,length=%s)" \
        #    % (self.__class__.__name__,recl,length))
        self.records=self.boot_recs(recl,length=length)
        #print("%s.%s - directed() - self.cum_len: %s" \
        #    % (this_module,self.__class__.__name__,self.cum_len))

        # As a side effect, self.boot_records is now set to a list of
        # BOOTREC objects and self.cum_len is the length of all booted data

        # Loadable static method in superclass used by self.boot_recs


# A Boot Loader from a LDIPL directory
#
# Instance Arguments:
#   args    Command line arguments submitted to the tool
#   obj     Whether the boot loader supports an absolute object deck (True)
#           or directed load records (False).  The default is False.
#   length  Whether the length field is containted within the directed record
#           header.
class LOADER(LDIPL):

    def __init__(self,args,obj=False,length=False):
        super().__init__(args.boot,args.lpsw,args.lasa,booted=False)

        # Replaced by command-line argument (--zarch)
        #self.arch=args.zarch        # Whether it should change architectures

        # Object deck loading is only supported by a card or tape oriented loader
        self.obj=obj                # Whether it supports object deck loading

        # IPL medium dictates this
        self.length=length          # Whether directed records require a length

        # Booted program boot records (Instances of BOOTREC)
        self.boot_records=[]


# A directed load record.
# BOOTREC objects are created by LOADER.region_to_bootrecs()
#
# Instance Arguments:
#   address   Address at which the directed load record starts in memory
#   bdata     The binary data associated with the directed load record
#
# Note: BOOTREC objects are created by LOADER.region_to_bootrecs().  When
# created, the directed load record's address field, and, when required, its
# length field.
class BOOTREC(object):
    def __init__(self,address,bdata):
        self.address=address     # Address where the record is to be loaded
        self.bdata=bdata         # Binary content to be loaded

        # The value used for the last record flag:
        #  0x00000000  -> this is not the last directed record
        #  0x80000000  -> this is the last direcred record
        # Use method islast() to set this flag
        self.last=0

    def __len__(self):
        return len(self.bdata)

    # Mark this record as the last directed record of the device
    def islast(self):
        self.last=0x80000000

    # Returns the binary boot record
    def record(self,length=False):
        # data address with last record flag
        bytes=fword(self.address | self.last)
        if length:
            bytes+=hword(len(self))
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

    # Print worthy description
    def description(self,indent=""):
        if len(self.name) <= 12:
            name=self.name.ljust(12)
        else:
            name=self.name
        return "%s%06X  %s  Length: %s (0x%0X)" \
            % (indent,self.address,name,len(self),len(self))


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
        
    # Returns an Allocation object associated with a specific name
    def __getitem__(self,key):
        return self.allocs[key]

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
            raise ValueError("allocation not found: %s" % name) from None

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

    # Establishes the Allocation's size in slots if its position has not been
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

    # Provide structure's binary representation
    # Subclass must supply this method.  Supplied by CompoundStruct
    # Returns: a bytearray sequence of binary data
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
NONE=0x00         # No CCW flags
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
        
    def __str__(self):
        return "CCWO - command: %02X  iolen: %s  flags: %02X  address: %06X" \
            % (self.command,self.iolen,self.flags,self.ioarea)

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


# Defines FBA LOCATE command parameters
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
        self.sys=sys | 0x08   # System masks
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
        bdata+=fword(self.IA | self.AM)
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

# LOD1 - IPL Record 4
#
# LOD1 is instantiated by IPLVOL object by calling its medium specific
# subclass method
#
# Instance Arguments:
#   dtypeo   DTYPE object of targeted IPL device
#   psw      Booted program PSW content (from BOOTEDIMAGE or BOOTED object)
#   am       Addressing mode at entry to booted program
#   flags    Any of the following: "zarch", "AM64", "traps", "CCW1"
#
# Instance Exceptions:
#   AssertionError if any unrecognized value. Should not occur, but just in case
class LOD1(BaseStruct):

    # LOD1 booted program entry addressing mode:
    entry_am={24:0,31:0x80000000,64:0x00000001}

    # LOD1 record flag byte values
    #flags={"zarch":0x80,"AM64":0x40,"traps":0x20,"CCW1":0x01}
    flags={"zarch":0x80,"traps":0x20,"CCW1":0x01}

    # LOD1 field formats:
    formats={1:"%02X",2:"%04X",3:"%06X",4:"%08X"}

    def __init__(self,dtypeo,psw,am=24,flags=[]):
        # LOD1 is 80 bytes by design
        super().__init__(length=80,address=0x240,mloc=None,align=1)
        assert isinstance(dtypeo,DTYPE),\
            "%s.%s.__init__() - invalid 'dtypeo' argument: %s" \
                % (this_module,self.__class__.__name__,dtypeo)
        assert isinstance(psw,REGION),\
            "%s.%s.__init__() - 'psw' argument must be a REGION object: %s" \
                % (this_module,self.__class__.__name__,psw)
        assert isinstance(flags,list),\
            "%s.%s.__init__() - invalid 'flags' argument, must be a list: %s" \
                % (this_module,self.__class__.__name__,flags)

        self.max_rec=dtypeo.max_rec   # Maximum physical record size for device

        # LOD1 Bytes 0-3   - LOD1 record identification in EBCDIC
        self.recid=bytes([0xD3,0xD6,0xC4,0xF1])

        # LOD1 Byte 4      - Device type flag
        self.dtype=dtypeo.lod1_flag
        # Set from instance argument 'dtypeo' created in IPLTOOL.__init__()
        if dtypeo.dlen:
            self.dtype |= 0b00000010

        # LOD1 Byte 5      - Boot loader flags
        self.flags=0         # Set by iplasma.py
        for flag in flags:
            try:
                flag_value=LOD1.flags[flag]
            except KeyError:
                raise ValueError(\
                    "%s.%s.__init__() - unrecognized LOD1 record flag: %s" \
                        % (this_module,self.__class__.__name__,flag))
            self.flags = self.flags | flag_value
        # Set from instance argument 'flags'

        # LOD1 Bytes 6,7   - Maximum length of a physical directed record
        # Set by iplasma.py volcls.__init__() using self.set_directed_length()
        self.recl=None

        # LOD1 Bytes 8-11  - Cumulative length of booted program
        # Set by iplasma.py volcls.set_directed_records() using
        # self.set_booted_length()
        self.size=None

        # LOD1 Bytes 12-15 - Cumulative length of booted program read
        self.booted_len=0    # Set by boot loader

        # LOD1 Bytes 16-19 - Booted program's entry branch address from BOOTED
        #                    or BOOTEDIMAGE psw region
        amode=LOD1.entry_am[am]
        address=int.from_bytes(psw.bdata[4:8],byteorder="big",signed=False)
        self.psw=fword(address | amode)   # Add addressing mode bits to address
        #self.psw=psw.bdata[4:8]    # Set by iplasma.py
        # Set from instance argument 'psw'.

        # LOD1 Byte 20     - Boot Loader CPU Operating Environment
        self.boot_oper=0     # Set by boot loader

        # LOD1 Byte 21     - Boot Loader I/O architecture and mode
        self.boot_io=0       # Set by boot loader

        # LOD1 Byte 22     - Boot Loader addressing mode
        self.boot_am=0       # Set by boot loader

        # LOAD Byte 23     - Boot Loader services
        self.boot_serv=0     # Set by boot loader

        # LOD1 Bytes 24-27 - Starting sector of booted program directed records
        self.sector=0        # value established by set_FBA_start() method

        # LOD1 Bytes 28-35 - CKD related values for booted program's records
        self.cyl=0           # CKD values established by set_CKD() method
        self.head=0          # Set by iplasma.py
        self.rec=0
        self.recs=0
        self.max_cyl=0
        self.max_head=0

        # LOD1 Bytes 36,37 - Subchannel device number of IPL device
        self.devnum=0        # Set by boot loader

        # LOD1 Bytes 38-41 - IPL device hardware identification from IPL
        self.ipl_device=0    # Set by boot loader

        # LOD1 Bytes 42-45 - I/O area used by the boot loader
        self.ioarea=None     # Set by iplasma.py IPLVOL.__init__()

        # LOD1 Bytes 46-49 - Boot loader service table address
        self.boot_tbl=0      # Set by boot loader

        # LOD1 Bytes 50-79 - reserved, must be zeros
        self.resv2=bytes(28)

    # Used to format a line of the LOD1 record contents
    def __format_field(self,address,binary,desc,indent):
        format_str=LOD1.formats[len(binary)]
        data="%s  %s" % ("%06X",format)
        integer=int.from_bytes(binary,byteorder="big")
        data=format_str % integer
        data=data.ljust(10)
        return (address+len(binary),\
            "%s%06X  %s  %s" % (indent,address,data,desc))

    # Returns binary representation of LOD1 (IPL Record 4).
    #
    # Note: until this method is called, the LOD1 object accumulates
    # information destined for the record.  The various "set_" methods
    # are used to accumulate this data.  Once called the final version
    # of the LOD1 record is communicated for installation on the IPL medium.
    def binary(self):
        bdata=self.recid               # Bytes 0-3     0x240
        bdata+=byte(self.dtype)        # Byte 4        0x244
        bdata+=byte(self.flags)        # Byte 5        0x245
        bdata+=hword(self.recl)        # Bytes 6,7     0x246
        bdata+=fword(self.size)        # Bytes 8-11    0x248
        bdata+=fword(self.booted_len)  # Bytes 12-15   0x24C
        bdata+=self.psw                # Bytes 16-19   0x250
        bdata+=byte(self.boot_oper)    # Byte 20       0x254
        bdata+=byte(self.boot_io)      # Byte 21       0x255
        bdata+=byte(self.boot_am)      # Byte 22       0x256
        bdata+=byte(self.boot_serv)    # Byte 23       0x257

        # FBA Data - Bytes 24-27
        bdata+=fword(self.sector)      # Bytes 24-27   0x258

        # CKD Data - Bytes 28-37:
        bdata+=hword(self.cyl)         # Bytes 28,29   0x25C
        bdata+=hword(self.head)        # Bytes 30,31   0x25E
        bdata+=byte(self.rec)          # Byte 32       0x260
        bdata+=byte(self.recs)         # Byte 33       0x261
        bdata+=hword(self.max_cyl)     # Bytes 34,35   0x262
        bdata+=hword(self.max_head)    # Bytes 36,37   0x264

        bdata+=hword(self.devnum)      # Bytes 38,39   0x266
        bdata+=fword(self.ipl_device)  # Bytes 40-43   0x268
        bdata+=fword(self.ioarea)      # Bytes 44-47   0x26C  Not correct
        bdata+=fword(self.boot_tbl)    # Bytes 48-51   0x270
        bdata+=self.resv2              # Bytes 52-79

        assert len(bdata) == 80,"LOD1 record must be of length 80: %s" \
            % len(bdata)

        return bdata

    # Prints the contents of a binary version of LOD1 record
    def format(self,bin,indent=""):
        addr=0x240   # Location where LOD1 always resides in memory

        # 0x240
        addr,line=self.__format_field(addr,bin[0:4],"LOD1 Record ID",indent)
        print(line)

        # 0x244
        addr,line=self.__format_field(addr,bin[4:5],"IPL medium information",indent)
        print(line)

        # 0x245
        addr,line=self.__format_field(addr,bin[5:6],"Boot loader flags",indent)
        print(line)

        # 0x246
        addr,line=self.__format_field(addr,bin[6:8],\
            "Maximum length of boot directed records in bytes",indent)
        print(line)

        # 0x248
        addr,line=self.__format_field(addr,bin[8:12],\
            "Cumulative length of booted program on medium in bytes",indent)
        print(line)

        # 0x24C
        addr,line=self.__format_field(addr,bin[12:16],\
            "Boot Loader Supplied: cumulative length of loaded program in bytes",indent)
        print(line)

        # 0x250
        addr,line=self.__format_field(addr,bin[16:20],\
            "Booted program's entry address",indent)
        print(line)

        # 0x254
        addr,line=self.__format_field(addr,bin[20:21],\
            "Boot Loader Supplied: Boot Loader's operating environment",indent)
        print(line)

        # 0x255
        addr,line=self.__format_field(addr,bin[21:22],\
            "Boot Loader Supplied: Boot Loader's I/O architecture and mode",indent)
        print(line)

        # 0x256
        addr,line=self.__format_field(addr,bin[22:23],\
            "Boot Loader Supplied: Boot Loader services",indent)
        print(line)

        # 0x257
        addr,line=self.__format_field(addr,bin[23:24],\
            "Boot Loader Supplied: Booted program entry addressing mode",indent)
        print(line)

        # 0x258
        addr,line=self.__format_field(addr,bin[24:28],\
            "Booted program starting physical FBA sector number",indent)
        print(line)

        # 0x25C
        addr,line=self.__format_field(addr,bin[28:30],\
            "Booted program starting CKD cylinder number",indent)
        print(line)

        # 0x25E
        addr,line=self.__format_field(addr,bin[30:32],\
            "Booted program starting CKD track (head) number",indent)
        print(line)

        # 0x260
        addr,line=self.__format_field(addr,bin[32:33],\
            "Booted program starting CKD record number",indent)
        print(line)

        # 0x261
        addr,line=self.__format_field(addr,bin[33:34],\
            "Number of CKD directed records per track",indent)
        print(line)

        # 0x262
        addr,line=self.__format_field(addr,bin[34:36],\
            "Maximum CKD cylinder number",indent)
        print(line)

        # 0x264
        addr,line=self.__format_field(addr,bin[36:38],\
            "Maximum CKD track (head) number",indent)
        print(line)

        # 0x266
        addr,line=self.__format_field(addr,bin[38:40],\
            "Boot Loader Supplied: Device Number of IPL subchannel",indent)
        print(line)

        # 0x268
        addr,line=self.__format_field(addr,bin[40:44],\
            "Boot Loader Supplied: I/O address of IPL device",indent)
        print(line)

        # 0x26C
        addr,line=self.__format_field(addr,bin[44:48],\
            "Boot Loader I/O area starting address",indent)
        print(line)

        # 0x270
        addr,line=self.__format_field(addr,bin[48:52],\
            "Boot Loader Supplied: Boot Loader services address",indent)
        print(line)

        # 0x274
        addr,line=self.__format_field(addr,bin[52:56],\
            "RESERVED",indent)
        print(line)

        # 0x278
        addr,line=self.__format_field(addr,bin[56:60],\
            "RESERVED",indent)
        print(line)

        # 0x27C
        addr,line=self.__format_field(addr,bin[60:64],\
            "RESERVED",indent)
        print(line)

        # 0x280
        addr,line=self.__format_field(addr,bin[64:68],\
            "RESERVED",indent)
        print(line)

        # 0x284
        addr,line=self.__format_field(addr,bin[68:72],\
            "RESERVED",indent)
        print(line)

        # 0x288
        addr,line=self.__format_field(addr,bin[72:76],\
            "RESERVED",indent)
        print(line)

        # 0x28C
        addr,line=self.__format_field(addr,bin[76:80],\
            "RESERVED",indent)
        print(line)

    # Define the values related to booting a program from a CKD volume.
    def set_CKD(self,cyl,head,rec,recs,max_cyl,max_head):
        assert isinstance(cyl,int) and cyl>=0,\
            "%s.%s.set_CKD() - invalid 'cyl' argument: %s" \
                % (this_module,self.__class__.__name__,cyl)
        assert isinstance(head,int) and head>0,\
            "%s.%s.set_CKD() - invalid 'head' argument: %s" \
                % (this_module,self.__class__.__name__,head)
        assert isinstance(rec,int) and rec>0,\
            "%s.%s.set_CKD() - invalid 'rec' argument: %s" \
                % (this_module,self.__class__.__name__,rec)
        assert isinstance(recs,int) and recs>0,\
            "%s.%s.set_CKD() - invalid 'recs' argument: %s" \
                % (this_module,self.__class__.__name__,recs)
        assert isinstance(max_cyl,int) and max_cyl>0,\
            "%s.%s.set_CKD() - invalid 'max_cyl' argument: %s" \
                % (this_module,self.__class__.__name__,max_cyl)
        assert isinstance(max_head,int) and max_head>0,\
            "%s.%s.set_CKD() - invalid 'max_head' argument: %s" \
                % (this_module,self.__class__.__name__,max_head)
        self.cyl=cyl
        self.head=head
        self.rec=rec
        self.recs=recs
        self.max_cyl=max_cyl
        self.max_head=max_head

    # Set cumulative length of booted program from directed records
    def set_booted_length(self,length):
        assert isinstance(length,int),"%s.%s - set_booted_length() "\
            "length must be an integer: %s" % (this_module,\
                self.__class__.__name__,length)
        self.size=length

    # Set the directed record physical length
    def set_directed_length(self,length):
        self.recl=length

    # Define the start of the booted program on an FBA volume
    def set_FBA_start(self,sector):
        assert isinstance(sector,int) and sector>0,\
            "%s.%s.set_FBA_start() - invalid 'sector' argument: %s" \
                % (this_module,self.__class__.__name__,sector)
        self.sector=sector

    # Externally set the boot loader's I/O area start
    def set_ioarea(self,address):
        self.ioarea=address


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

        self.media=None      # Locate the area on a medium.  See mloc() method

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

# Defines and builds the IPL Medium INDEPENDENT of the actual device type.
# Device type specifics are encapsulated in a subclass that implements a set
# of methods for the device type.
#
# Instance Arguments:
#   program   The LDIPL object associated with the bare-metal program (a
#             LDIPL or IMAGE object) or boot loader (a LDIPL object).
#   boot      The LDIPL object associated with the booted program if a boot
#             loader is used. A BOOTED or BOOTEDIMAGE object.  Otherwise must
#             be None
#   dtype     IPL volume device medium
#   bc        Specify True to cause a basic-control mode PSW to be manufactered.
#   verbose   Whether detailed messages are to be displayed
class IPLVOL(object):

    def __init__(self,args,program,boot,dtypeo,bc=False,verbose=False):
        self.args=args           # Command-line arguments
        self.dtypeo=dtypeo       # DTYPE object
        self.verbose=verbose     # Whether verbose messages enabled
        self.dtype=dtypeo.hardware  # Physical volume device type string

        # IPL Program related information
        self.program=program     # LDIPL, LOADER or IMAGE object of IPL'd program
        self.psw=program.psw     # PSW region of IPL'd program
        self.asa=program.asa     # ASA initialization image region

        # Booted program related information
        #
        # BOOTED or BOOTEDIMAGE object of booted program or objdeck
        self.booted=boot
        self.deck=isinstance(boot,bytes)  # Whether self.booted is an object deck

        # Memory management object.  Memory usage is similar for all device types
        self.mem=Memory()        # Memory Manager

        self.areas=[]       # List of Area objects requiring medium locations

        # Areas created during IPLVOL instantiation
        # IPL function areas
        self.lod1=None           # LOD1 record area (LOD1 instance)
        self.lod1_area=None      # LOD1 area for IPL reading
        self.lod1_bin=None       # LOD1 binary content, set by volcls.write_IPL4()
        self.prog_regns=[]       # Bare-metal program regions being IPL'd
        self.asa_area=None       # ASA  Assigned Stroage Area initialization
        self.psw_area=None       # PSW  The PSW used to enter the bare-metal program
        self.ipl_hwm=None        # IPL program high water mark

        # Booted program information (read by the boot loader)
        self.boot_regns=[]       # Booted program regions
        self.boot_hwm=None       # Booted program's high water mark (hwm)
        self.boot_addr=None      # Bytes 4-7 of booted program's entry PSW
        self.hwm=None            # Location where IPL Record 1 is read

        # Areas created by build() method
        self.r0_area=None        # IPL0 IPL Record 0 area
        self.r1_area=None        # IPL1 IPL Record 1 area
        self.ccw_area=None       # CCW0 CCWs used in IPL Record 0
        self.boot_io=None        # Loader I/O area address destined for LOD1
        self.preads=[]           # List of device reads for reading the program

        # Start creation of LOD1 if needed
        if self.booted and not self.deck:
            # Create LOD1 with the medium independent information
            self.boot_hwm=self.booted.hwm()
            lod1_flags=[]
            #if self.args.zarch:
            #    lod1_flags.append("zarch")
            #if self.args.ccw1:
            #    lod1_flags.append("CCW1")

            # Create the LOD1 object.  Some additional information is
            # added by the subclass implementation
            self.lod1=self.create_LOD1(am=self.args.am,flags=lod1_flags)  # LOD1 object
            self.lod1_area=Area("LOD1",beg=0x200,bytes=512)
            # Note: self.lod1 will be updated with additional data later

        # Create IPL program areas
        self.ipl_hwm=self.program.hwm()
        for reg in self.program.load_list:
            parea=self.region_to_area(reg.name,reg,debug=False)
            self.prog_regns.append(parea)
            self.areas.append(parea)

        # Establish HWM for locating IPL Record 1 in memory
        if self.boot_hwm:
            self.hwm=align(max(self.ipl_hwm,self.boot_hwm),8)
            # This places IPL Record 1 AFTER a booted program
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
        if self.booted:
            if self.deck:
                boot=" BOOT: DECK"
            else:
                boot=" BOOT: LDIPL"
        return "%s IPL: %s%s" % (self.dtype,ipl,boot)

    # Generic build and install process for all IPL media types except CARD
    def build(self):

      # Build logical IPL records

        # Some devices needs to process before IPL records built
        #self.build_init()   # Keep this????

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

        # Allocate LOD1 in the memory allocation map
        self.mem.allocate(self.lod1_area)

        # Allocate booted program in the memory map allocation
        # And set boot loader I/O area
        if self.booted and not self.deck:
            # Allocate booted program in memory
            lwm=self.booted.lwm()
            hwm=self.booted.hwm()
            allocation=Allocation("BOOTED",slots=hwm-lwm+1)
            allocation.position(lwm,format="06X")
            self.mem.allocate(allocation)

            # Assign boot loader I/O area and set it in the LOD1 record
            self.boot_io=align(self.r1_area.range.end,8)
            self.lod1.set_ioarea(self.boot_io)

        # Report boot loader I/O area address here, before memory map
        if self.verbose and self.boot_io:
            print("%s - Boot Loader I/O area: %06X" \
                % (this_module,self.boot_io))

        if self.verbose:
            print("Memory Map:")
            print(self.mem.display(indent="    "))

        # Write the IPL records to the volume.  The medium specific subclass,
        # where these methods are implemented, must handle any physical
        # sequencing issues.
        self.write_IPL0()      # IPL0
        self.write_IPL1()      # IPL1
        self.write_VOL1()      # VOL1
        self.write_areas()     # IPL2's
        if self.asa_area:
            self.write_IPL3()   # ASA
        if self.lod1:
            self.write_IPL4()   # LOD1

        # Some devices need to complete the write process.
        #self.fini()

        if self.verbose:
            if self.lod1_bin:
                print("LOD1 IPL Record 4:")
                self.lod1.format(self.lod1_bin,indent="    ")
            else:
                print("LOD1 IPL Record 4 not created")

        # Write booted directed records to the volume
        if self.booted and not self.deck:
            self.write_directed_records()

    # Converts a REGION object into an Area object, registering the Area with memory
    # and returning the resulting Area object.
    def region_to_area(self,name,region,alloc=True,debug=False):
        assert isinstance(region,REGION),"region must be a REGION object: %s" % region
        if debug:
            print("region_to_area(): %s: %s" % (name,region))
        area=Area(name,beg=region.address,bytes=region.bdata)
        if alloc:
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
    #  2. ASA loaded at 0 - use it for the IPL PSW and put a disabled wait PSW in R0
    #                       ASA will overwrite the start of IPL2
    #  3. PSW loaded at 0 - if ASA, update it with the PSW and proceed with case 2
    #                     - if no ASA, use the PSW in R0
    #  4. Create a PSW based upon IPL2 being loaded elsewhere in R0
    # For both cases 1 and 2, the disabled wait will get overwritten
    # Returns the bytes constituting the IPL PSW placed in IPL Record 0
    def set_IPLPSW(self,debug=False):
        at0=self.mem.find(0)
        # This dictionary is of areas by area name (not REGION name)
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
            else:
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
                    "an IPL PSW: length: %s" % asa_len)
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

        # No regions are loaded at 0, so manufacture a PSW from the program's
        # starting address.
        if len(at_zero)==0:
            # Use the first byte of the first region loaded as the program entry
            load_point=self.program.load_list[0]
            #load_point=load_point.range.beg
            load_point=load_point.address
            hwords,odd=divmod(load_point,2)
            if odd != 0:
                raise MediumError(msg="Program starting location not on a half "
                    "word boundary, PSW can not be created: %06X" % load_point)
            address=load_point.to_bytes(3,byteorder="big")
            if self.program.bcmode:
                psw=PSWBC(0,0,0,load_point)
            else:
                psw=PSWEC(0,0,0,load_point)
            return psw.binary()

        # NOTE:This diverges from the IPLASMA.odt document.  It says that
        # lower-priority loaded records will get a disabled wait PSW.  But
        # this logic does not do that.  Figure which to fix, the doc or the
        # code.

        # More than one region loaded at 0, so need to update the one loaded last with
        # the higher priority PSW.
        high_pri=at_zero[0]   # The first area in the list is the higher priority
        low_pri=at_zero[-1]   # The last area in the list is loaded last
        psw=high_pri.content[0:8]
        # Update the last area to be loaded with it
        low_pri.content[0:8]=psw
        # And return it as the IPL Record 0 PSW.
        return psw

  #
  # Methods that must be implemented by the subclass
  #

    # IPL record build initialization
    #def build_init(self):
    #    raise NotImplementedError("%s - class %s must provide build_init() " \
    #        "method" % (this_module,self.__class__.__name__))

    # Creates the emulated IPL volume
    def create(self,path,minimize=True,comp=False,progress=False,debug=False):
        raise NotImplementedError("%s - class %s must provide create() method" \
            % (this_module,self.__class__.__name__))

    # Create a LOD1 record.  See subclass for
    # Returns: a LOD1 object
    def create_LOD1(self,am=24,flags=[]):
        raise NotImplementedError("%s - class %s must provide create_LOD1() "
            "method" % (this_module,self.__class__.__name__))

    # Dumps to the console the IPL medium's records
    # Note: should only be called after IPL and directed load records have
    # been writen to the device.  That is, after write_XXXX() methods have been
    # called.
    def dump(self):
        raise NotImplementedError("%s - class %s must provide dump() method" \
            % (this_module,self.__class__.__name__))

    # Some devices (cards in particular) can not write any of the IPL records
    # until all of the IPL data content has been established.  Other device
    # types do not need this method.
    #def fini(self):
    #    raise NotImplementedError("%s - class %s must provide fini() method" \
    #        % (this_module,self.__class__.__name__))

    # Returns the Area containing the IPL CCW's destined for IPL Record 0
    def ipl_ccw(self):
        raise NotImplementedError("%s - class %s must provide ipl_ccw() method" \
            % (this_module,self.__class__.__name__))

    # Returns the Area containing IPL Record 1
    def ipl_rec1(self,name):
        raise NotImplementedError("%s - class %s must provide ipl_rec1() method" \
            % (this_module,self.__class__.__name__))

    # Returns the maximum record length supported by the volume's read CCW.
    def max_recl(self):
        raise NotImplementedError("%s - class %s must provide max_recl() method" \
            % (this_module,self.__class__.__name__))

    # Assign a medium location to an Area
    # Method Arguments:
    #   area   an Area instance being located on the medium.
    def mloc(self,area):
        raise NotImplementedError("%s - class %s must provide mloc() method" \
            % (this_module,self.__class__.__name__))

    def write_boot_records(self):
        raise NotImplementedError(\
            "%s - class %s must provide write_boot_records() method" \
                 % (this_module,self.__class__.__name__))

    # Write IPL Record 0 - IPL PSW + first two IPL CCWs
    def write_IPL0(self):
        raise NotImplementedError("%s - class %s must provide write_IPL0() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 1 - remaining IPL CCWs
    def write_IPL1(self):
        raise NotImplementedError("%s - class %s must provide write_IPL1() method" \
            % (this_module,self.__class__.__name__))

    # Write Bere-metal program regions as IPL records,
    # aka IPL Record 2
    def write_areas(self):
        raise NotImplementedError("%s - class %s must provide write_areas() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 3 - Assigned Storage Area initialization
    def write_IPL3(self):
        raise NotImplementedError("%s - class %s must provide write_IPL3() method" \
            % (this_module,self.__class__.__name__))

    # Write IPL Record 4 - Boot Loader LOD1 record
    def write_IPL4(self):
        raise NotImplementedError("%s - class %s must provide write_IPL4() method" \
            % (this_module,self.__class__.__name__))

    # Write the volume's VOL1 - Volume Label
    def write_VOL1(self):
        raise NotImplementedError("%s - class %s must provide write_VOL1() method" \
            % (this_module,self.__class__.__name__))

#
# +-------------------+
# |                   |
# |   CARD IPL Deck   |
# |                   |
# +-------------------+
#

class CRDECK(IPLVOL):
    def __init__(self,args,program,boot,dtypeo,verbose=False):
        super().__init__(args,program,boot,dtypeo,verbose=verbose)

        self.dir_len=None  # Directed record length in bytes
        self.ipl_areas=[]  # List of areas to be read during IPL

        # The object from which the IPL card stream is written
        self.deck=ADECK(self.verbose)   # From which the IPL deck is created

        if self.booted and not self.deck:
            self.dir_len=80
            self.lod1.set_directed_length(self.dir_len)

            # Create directed records for the booted program
            self.booted.directed(self.dir_len,length=True)
            self.lod1.set_booted_length(self.booted.cum_len)

        if verbose:
            # Mimic the information supplied by fba_util.__str__() method
            string="Volume:  TYPE=%s LFS=False" % (dtypeo.hardware)
            string="%s\nHost:    FILE=variable" % string
            string="%s\nRecord:  LENGTH=80 RECORDS=variable" % string
            print(string)

        # Must use an emulated "punch" device to create a card deck image
        # that can be read by a program.
        self.device=media.device("3525")

        # A device allocation map is not used for a sequential device.

    # Converts an Area object into a list of ACARD objects
    # Method Argument:
    #   area   The Area object being converted
    # Returns:
    #   a list of ACARD objects
    def area_to_cards(self,area):
        assert isinstance(area,Area),"'area' argument must be an Area: %s" \
            % area

        cur_addr=area.range.beg     # Determine area's starting address
        content=area.content
        length=len(content)
        cards=[]         # ACARD instances destined for deck

        for ndx in range(0,length,80):
            byt=content[ndx:min(ndx+80,length)]
            cards.append(ACARD(None,byt,addr=cur_addr))  # Note no ID value
            cur_addr+=80

        return cards


    # Card decks use an entirely different set of records for loading program
    # content than the other device types.  This method overrides the
    # IPLVOL.build() method in its entirety.
    #
    # At the logical level, all of the IPL Records are supported by an IPL deck.
    # However the manner in which they are loaded is entirely different for
    # cards.  With cards all IPL loaded data from all records 2 and above are
    # merged with the corresponding data that would in other contexts be a
    # separate IPL Record 1 (the channel program).  Other devices separate
    # the data into separate physical records.
    #
    # See the manual doc/asma/IPLASMA.odt or doc/asma/IPLASMA.pdf for details on
    # the IPL deck created by this module.
    def build(self):
        if self.verbose:
            # Insert note about 3525 device type.
            print("NOTE: an emulated punch device is used to create the IPL " \
                "deck")

    # Build logical card IPL records

        # Allocate the two buffers for the IPL channel commands (logical
        # IPL Record 1).
        self.r1_area=self.set_IPL1("IPL1",debug=False) # Two card buffers..
        self.mem.allocate(self.r1_area) # ..are allocated

        # Create the IPL CCW's in IPL Record 0
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

  # CANDIDATE FOR ITS OWN METHOD IN IPLVOL
  #
        # Allocate LOD1 in the memory allocation map
        if self.booted:
            self.mem.allocate(self.lod1_area)

        # Allocate booted program in the memory map allocation
        # And set boot loader I/O area
        if self.booted and not self.deck:
            # Allocate booted program in memory
            lwm=self.booted.lwm()
            hwm=self.booted.hwm()
            allocation=Allocation("BOOTED",slots=hwm-lwm+1)
            allocation.position(lwm,format="06X")
            self.mem.allocate(allocation)

            # Assign boot loader I/O area and set it in the LOD1 record
            self.boot_io=align(self.r1_area.range.end,8)
            self.lod1.set_ioarea(self.boot_io)

        # Report boot loader I/O area address here, before memory map
        if self.verbose and self.boot_io:
            print("%s - Boot Loader I/O area: %06X" \
                % (this_module,self.boot_io))
  #
  # CANDIDATE FOR ITS OWN METHOD IN IPLVOL

        # Establish IPL Record 1 cards' buffer addresses
        # Updates the ALG class attribute buffer_addr.
        ipl1_obj=self.mem["IPL1"]      # Fetch the Allocation object for IPL1
        begina=ipl1_obj.range.beg       # Determine beginning address
        beginb=begina+80
        ALG.buffer_addr["A"]=begina    # Buffer A is at the beginning address
        ALG.buffer_addr["B"]=beginb    # Beffer B is the 80 bytes beyond that
        
        if self.verbose:
            print("Memory Map:")
            print(self.mem.display(indent="    "))
            print("        CCW Record Buffer A: %06X-%06X" \
                % (begina,begina+79))
            print("        CCW Record Buffer B: %06X-%06X" \
                % (beginb,beginb+79))

        # Build the deck content (not the deck yet)
        self.write_IPL0()      # IPL0
        #self.write_IPL1()      # IPL1  IPL1 is intermixed with data
        #self.write_VOL1()      # VOL1  A Card deck does not have a VOL1 record
        self.write_areas()     # IPL2's IPL2 records intermixed with CCW's
        if self.asa_area:
            self.write_IPL3()   # ASA
        if self.lod1:
            self.write_IPL4()   # LOD1
        # The ADECK object has been primed with data

    # Create the IPL medium
    def create(self,path,minimize=True,comp=False,progress=False,debug=False):
        self.deck.create()    # Convert deck into a load stream
        
        # Dump the physical cards here for more information in the output
        if self.verbose:
            self.deck.dump()

        #print("CRDECK.create() - self.device: %r" % self.device)
        for card in self.deck.cards:
            real_card=recsutil.card(data=card.content)
            self.device.record(real_card)
            
        self.device.create(path)  # Write the IPL medium file    

    # Dumps the card records
    def dump(self):
        pass

    # Returns the CCW's used to construct IPL Record 0
    def ipl_ccw(self,name,debug=False):
        # Reads the first card of read CCW's into the first buffer
        self.iplccw1=CCW0(IPLREAD,80,self.iplrec1_start,CC)
        # Transfers channel control to the first card now in the buffer
        self.iplccw2=TICCCW(self.iplrec1_start)

        # Build the CCWs into a byte sequence
        ccws=IPLREC0_CCWS()
        ccws.append(self.iplccw1)
        ccws.append(self.iplccw2)
        ccws.loc(8)
        ccws.length=16
        ccws.build()

        # Return an Area object for the CCWs in IPL Record 0
        return Area(name,beg=ccws.address,bytes=ccws.content)

    def ipl_rec1(self,name,debug=False):
        # The returned area's content is binary zeros.  The IPL Record 1 Area
        # object defines the two I/O buffers used by the channel commands of
        # the dispersed IPL Record 1 chain throughout the IPL deck.
        self.iplrec1_start=align(self.hwm+80,8)
        area=Area(name,beg=self.iplrec1_start,bytes=bytes(2*80))

        # This allows the two buffer areas to be allocated, but the content of
        # this Area is not used in the IPL deck.
        return area

    # Create data records from an area and add to the deck
    # IPLVOL.__init__() has created the areas in self.areas
    def write_areas(self):
        for area in self.prog_regns:
             self.deck.add_data(self.area_to_cards(area))

    # Add IPL Record 0 to the deck in process
    def write_IPL0(self):
        card_ipl0=ACARD("IPL0",self.r0_area.content,addr=0)
        self.deck.add_IPL0(card_ipl0)   # Add IPL Record 0 to output deck

    #def write_IPL1(self):
    #   Method not used for a card deck
    #   Logical equivalent created by ADECK.create() method

    #def write_IPL2(self):
    #   Method not used for a card deck
    #   Logical equivalent created by ADECK.create() method

    # Add ASA content to the deck in process
    def write_IPL3(self):
        self.deck.add_data(self.area_to_cards(self.asa_area))

    # Write LOD1 to the deck in process.  LOD1 fits on a single card
    def write_IPL4(self):
        self.deck.add_data(self.area_to_cards(self.lod1_area))

# This class encapsulates a card for the IPL deck.  It creates a card
# whose content can be punched by the emulated punch device
#
# Instance Arguments:
#   ID     A character string ID'ing the card record. Required.
#   byt    A bytes-type sequence of content for the card.  If omitted, a card
#          consisting of all EBCDIC spaces is produced.
#   pad    Whether the content provided by the byt argument can be padded
#          to the full 80 bytes with EBCDIC spaces.  Specify True to pad byt.
#          Specify False to inhibit padding.  When padding is inhibited, the
#          content provided by byt must be 80 bytes in length.  If omitted,
#          the default is False.
class ACARD(object):

    # Immutable blank card with EBCDIC spaces
    blank=bytes([64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64, \
                 64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64, \
                 64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64, \
                 64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64, \
                 64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64])

    # Use bytearray(ACARD.blank) to create a mutuable copy

    def __init__(self,ID,byt,addr=None):
        assert isinstance(ID,str) or ID is None,\
            "'byt' argument must be a string: %s" % (this_module,addr)
        assert isinstance(byt,(bytes,bytearray)),"ACARD.__init__() - byt " \
            "argument not a bytes sequence: %s" % byt

        self.ID=ID        # Give this card a recognized name
        self.content=byt  # Card binary content
        # Content length used in CCW
        self.addr=addr    # Address to which this card is written (for CCW)
        self.islast=False # Whether this is the last card of deck
        # Note: when this is True, the CCW that reads it is NOT command chained.

    def __str__(self):
        return "ACARD %s @ %06X length: %s" \
            % (self.ID,self.addr,len(self.content))
            
    # Pad the current content with additional EBCDIC spaces until full
    # content is 80 bytes.  Make sure the content is inmutable.
    def pad(self):
        length=len(self.content)
        assert length <= 80,"content length not <= 80 bytes: %s" % length
        if length < 80:
            # Content already 80 bytes, no padding required
            blank=bytearray(ACARD.blank)   # Get an "empty" mutable card image
            blank[0:length]=self.content   # Update with unpadded data
            padded=bytes(blank)            # Convert back to immutable object
            self.content=padded            # Set my padded content
            
        # Make sure we have an immutable bytes sequence for recsutil
        if isinstance(self.content,bytearray):
            self.content=bytes(self.content)


# This is an intermediate object for creating the card IPL deck
class ADECK(object):
    def __init__(self,verbose):
        self.verbose=verbose   # --verbose from comamand-line
        self.ipl0=None    # IPL 0 record added here (only one!)
        self.data=[]      # All data loaded by the IPL process goes here
        self.algs=[]      # All ACARD Load Group instances (from self.data)

        # This is the source of the actual deck written to the file
        self.cards=[]     # List of ACARD card images to be written

        self.lg_num_recs=[]  # The number of data records for each load group

    # Add a single ALG instance to the list.  Used by create() method
    def add_alg(self,alg):
        assert isinstance(alg,ALG),\
            "'alg' argument not an ALG instance: %s" % alg
        self.algs.append(self.algs)

    # Add a single ACARD instance as IPL Record zero.
    def add_IPL0(self,ipl0):
        assert isinstance(ipl0,ACARD),\
            "'ipl0' argument not an ACARD instance: %s" % ipl0
        assert self.ipl0 is None,\
            "self.ipl0 must be None: %s" % self.ipl0
        self.ipl0=ipl0    # Add IPL0 ACARD instance

    # Add data ACARDs (one or a list of ACARDs to the list)
    def add_data(self,data):
        #print("ADECK.add_data: %s" % data)
        # Add a list of ACARDs to the data list
        if isinstance(data,list):
            assert len(data)>0,"'data' argument list must not be empty"
            for card in data:
                self.add_data(card)  # This ensures all list entries are ACARDs
            return

        # Add a single ACARD instance to the data list
        assert isinstance(data,ACARD),\
            "'data' argument not an ACARD instance: %s" % data
        self.data.append(data)   # Add a data card to the list of data cards

    # Creates the load groups and ultimate card deck that is written to the
    # output medium, self.cards
    def create(self):
      # Step 1 - Add meaninful ID's to the ACARD data objects
        for n,acard in enumerate(self.data):
            card_num=n+1
            acard.ID="D%s" % card_num

      # Step 2 - Tag the last card
        self.data[-1].islast=True

      # Step 3 - Calculate the size of the load groups in terms of ACARD
      #          data objects

        if self.verbose:
            print("IPL Record 2 data cards: %s" % len(self.data))

        full,extra = divmod(len(self.data),8)
        #print("ADECK.create() - full,extra: %s,%s" % (full,extra))
        grp_ndxs=[]
        num_data_cards=[]
        
        if full:
            # At least one full CCW card of 8 CCW's
            for n in range(full):
                grp_ndxs.append(n*8)
                num_data_cards.append(8)
            if extra <= 2:
                # Add extra data cards to last load group
                num_data_cards[-1]=num_data_cards[-1]+extra
            else:
                # Add another load group to the list
                #print("ADECK.create() - grp_ndxs: %s" % grp_ndxs)
                grp_ndxs.append(grp_ndxs[-1]+8)
                num_data_cards.append(extra)
        else:
            # First CCW card not full of CCW's
            # Incomplete first card
            # Do we need to check for an empty image???
            grp_ndxs.append(0)
            num_data_cards.append(extra)

      # Step 4 - Create load groups

        next_buffer="B"
        a_buf_num = 1
        b_buf_num = 1
        for n,ndx in enumerate(grp_ndxs):
            data=self.data[ndx:ndx+num_data_cards[n]]
            # Create ALG and its CCW record ID
            if next_buffer == "A":
                ID="B%s" % b_buf_num
                b_buf_num+=1
            else:
                ID="A%s" % a_buf_num
                a_buf_num+=1
            lg=ALG(ID,data,next_buffer)
            self.algs.append(lg)

            # Identify the next buffer
            if next_buffer == "A":
                next_buffer = "B"
            else:
                next_buffer = "A"
                
        if self.verbose:
            print("IPL Record 1 CCW cards:  %s" % len(self.algs))

        # Tag the last load group
        last_lg=self.algs[-1]
        last_lg.islast=True    # The last load group does not chain
        last_lg.nxt_buf=None   # The next buffer to which this group chains

      # Step 5 - Create CCW0 objects for each load group
      
        for alg in self.algs:
            alg.build_ccws()
            
        # Tweak next to last CCW length and flag if needed
        self.tweak_ccw()

        if self.verbose:
            for alg in self.algs:
                buf="%s" % alg.nxt_buf
                buf=buf.ljust(4)
                alg_ccws="%s" % len(alg.ccwos)
                alg_ccws=alg_ccws.ljust(2)
                alg_cards="%s" % len(alg.cards)
                alg_cards=alg_cards.ljust(2)
                if alg.tweaked:
                    alg_last="%s" % alg.islast
                    alg_last=alg_last.ljust(5)
                    alg_last="%s  (adjusted)" % (alg_last)
                else:
                    alg_last="%s" % alg.islast
                print("    %s  CCWs: %s  data cards read: %s  next buffer: %s"
                    "  LAST: %s" % (alg.ID,alg_ccws,alg_cards,buf,alg_last))
                
      # Step 6 - Create the final card deck: IPL Record 0
      
        self.ipl0.pad()
        self.cards.append(self.ipl0)
        
        for alg in self.algs:
            alg.create_ccw_card()
            # All ALG ACARD objects are now ready to go
            
            # Add the ALG ACARD objects to the deck's list
            self.cards.append(alg.ccw_card)
            self.cards.extend(alg.cards)
            
    def dump(self):
        for n,card in enumerate(self.cards):
            print("CARD %s - %s @ %06X" % (n+1,card.ID,card.addr))
            print(dump(card.content,indent="    "))
    
    # Tweak the next to last CCW card reading command for the last load group.
    # This is required because by default the command preceding the one that
    # transfers control to the other buffer always is created to read an entire
    # card.  While this would work, it is preferable to only read what you
    # need.  So, once all of the load groups have had the CCW's created as
    # CCW0 objects, it becomes possible to adjust this CCW in the next to
    # last load group with the actual values needed by the last load group.
    #
    # This must be done here where all load groups (ALG objects) are available.
    def tweak_ccw(self):
        if len(self.algs) < 2:
            # Only if there are two or more load groups is tweaking possibly
            # needed
            return
        
        # Determine if CCW tweaking is needed.  This occurs if the last
        # load group's CCW card does not contain all 10 CCWs.
        last_alg=self.algs[-1]
        
        # Number of CCW's in last load group's CCW record
        last_ccws=len(last_alg.ccwos)   
        if last_ccws == 10:
            # The entire card is needed, so no tweaking to I/O length
            return
           
        # Tweaking _is_ needed to the next to last load group's CCW read
        # command's length to read only the CCW's it needs.
        # Here we are reaching into the CCW0 object and making adjustments
        next=self.algs[-2]
        tweak_ccw=next.ccwos[-2] # -2 reads next CCWS, -1 TIC's to next buffer
        tweak_ccw.iolen = last_ccws * 8  # Adjust length to what we need
        tweak_ccw.flags |= SLI   # Suppress incorrect length
        # Incorrect length is signaled by the channel because we are now not
        # reading the entire card, just the CCW's we need.  So it is needs
        # suppression for the IPL channel program to continue.
        next.tweaked=True


# ACARD Load Group: one channel ccw command card plus one or more data ACARDs
class ALG(object):

    buffer_addr={}    # Initialized by CRDECK when IPL 1 buffers allocated

    def __init__(self,ID,ldata,nxt_buf):
        assert isinstance(ldata,list),"'ldata' argument must be a list: %s" \
            % ldata

        self.ID=ID             # This load group's ID
        self.nxt_buf=nxt_buf   # Next Buffer to which the ccw_card chains
        self.islast=False      # Whether this is the last load group
        
        # Set my buffer for my card based upon the next buffer.
        # P.S. I am in the other one with its address
        if nxt_buf == "A":
            self.my_buf = "B"
        else:
            self.my_buf = "A"
        
        # List of CCW0 objects destined for a card
        self.ccwos=[]          # See build_ccws() method
        
        # ACARD object of the CCW's - they read the data records
        self.ccw_card=None     # See create_ccw() method
        
        # List of ACARD objects of the load group's binary data
        self.cards=ldata       # Provided by instantiator
        
        # Whether this load group was tweaked (see ADECK.tweak_ccw() method)
        self.tweaked=False     # See ADECK.tweak_ccw() method

    def __str__(self):
        return "ALG %s - data cards: %s  ccws: %s  next buffer: %s  last: %s" \
            % (self.ID,len(self.cards),len(self.ccwos),self.nxt_buf,\
                self.islast)

    # This method creates the CCW0 objects placed in the IPL Record 1 CCW
    # cards.
    def build_ccws(self):
        ccws=[]                # List of CCW0 objects
        for dcard in self.cards:
            # dcard is an ACARD object
            if dcard.islast:
                flag=NONE
            else:
                flag=CC
            length=len(dcard.content)
            assert length > 0 and length <= 80,"dcard content length not " \
                "between 1 and 80: %s" % length
            if length < 80:
                # Suppress incorrect length if the whole card is not read
                flag |= SLI
                
            # Read a data card of this load group
            ccw=CCW0(READ,length,dcard.addr,flags=flag)
            ccws.append(ccw)

        if not self.islast:
            # If not the last load group then we need to read the ccw card
            # for the next load group and transfer channel control to its
            # buffer.
            try:
                buf_addr=ALG.buffer_addr[self.nxt_buf]
            except KeyError:
                raise KeyError(\
                    "ALG.buffer_addr not initialized for buffer: %s" \
                        % self.nxt_buf) from None

            # Reads the next card into the next CCW buffer area
            ccw=CCW0(READ,80,buf_addr,flags=CC)
            ccws.append(ccw)

            # Transfers channel program control to the next buffer
            ccw=TICCCW(buf_addr)
            ccws.append(ccw)
            
        self.ccwos=ccws  # Remember for later use
        # CCW that reads in the last load group needs tweaking for the last
        # load group.  This can not be done here.  So we are remembering it
        # for later usage at a higher level where all load groups area
        # available.
        
    # Create actual binary CCW0
    def create_ccw_card(self):
        bin=bytearray(0)    # An empty bytearray sequence
        for ccw in self.ccwos:
            bin.extend(ccw.binary())
        
        # Create my actual CCW card's ACARD object
        self.ccw_card=ACARD(self.ID,bin,addr=ALG.buffer_addr[self.my_buf])
        self.ccw_card.pad()
        
        # Pad my data cards too
        for card in self.cards:
            card.pad()
            
    # Returns the number of cards in this load group
    def num_cards(self):
        return len(self.cards)


#
# +--------------------------+
# |                          |
# |   FBA DASD IPL Volume    |
# |                          |
# +--------------------------+
#

# IPL enabled FBA DASD Volume
#
# Instance Arguments:
#    program  The IPL'd program.
#    boot     The booted program.  May be None.
#    dtypeo   The DTYPE object of this device type.
#    verbose  Whether the tool produces verbose messages.  Specify True to
#             generate such messages.  Specify False to generate standard
#             messages.  Defaults to False.
# Exceptions:
#   MediumError if --recl not supplied by required
class FBAVOL(IPLVOL):
    def __init__(self,args,program,boot,dtypeo,verbose=False):
        super().__init__(args,program,boot,dtypeo,verbose=verbose)

        #self.args=args      # Command line arguments (used for LOD1 record)

        # Directed record length (rounded down to full sectors)
        self.dir_len=None   # Directed record length in bytes
        self.dir_sec=None   # Directed record length in sectors

        # Prepare a booted program for writing on the FBAVOL
        if self.booted and not self.deck:
            if self.args.recl:
                # Process command-line --recl option if required
                self.dir_sec=self.args.recl // 512
                self.dir_len=self.dir_sec * 512
                self.lod1.set_directed_length(self.dir_len)
                #self.lod1.recl=self.dir_len * 512
            else:
                raise MediumError(msg="--recl required for booted program")
            # Create directed records for the booted program
            self.booted.directed(self.dir_len,length=True)
            self.lod1.set_booted_length(self.booted.cum_len)

        recsutil.fba.strict=False   # Turn off global flag for strict sector sizes

        self.info=fbautil.fba_info(dtypeo.hardware)
        if verbose:
            print(self.info)

        self.device=media.device(self.dtype)
        self.maxsect=65535//512         # Maximum sectors in a single read
        self.maxrecl=self.maxsect*512   # Maximum record length (65,024)
        self.maxipl1=512-24             # Maximim IPL Record 1 length (488)

        # Allocate (but do not yet establish content) for each record in
        # the IPL sequence.
        self.fbamap=FBAMAP(self.info.sectors)
        self.fbamap.assign("IPL0",1)
        self.fbamap.assign("VOLLBL",1)
        if self.asa_area:
            self.fbamap.assign("ASA",1)
        if self.lod1:
            self.fbamap.assign("LOD1",1)
        for n,area in enumerate(self.prog_regns):
            assert isinstance(area,Area),"%s.%s - __init__()  'area' %s not an "\
                "Area object: %s" % (this_module,self.__class__.__name__,\
                    n,area.__class__.__name__)
            # For each area (from a memory region from within the LDIPL directory)
            # sector assignments are made
            self.fbamap.assign(area.name,FBAMAP.sectors(len(area)))
        if self.booted and not self.deck:
            self.fbamap.assign("BOOTED",self.booted.records)
            booted_allocation=self.fbamap.allocation("BOOTED")
            self.lod1.set_FBA_start(booted_allocation.range.beg)

        if verbose:
            print("FBA DASD Map:")
            print(self.fbamap.display(indent="    "))

        # Assign medium locations to areas
        for area in self.areas:
            sectors=self.fbamap.allocation(area.name)
            sector=sectors.range.beg
            area.mloc(sector)

    # Not used by FBA devices
    #def build_init(self):
    #    pass

    # Create the FBA Volume
    def create(self,path,minimize=True,comp=False,progress=False,debug=False):
        self.device.create(path=path,\
            minimize=minimize,comp=comp,progress=progress,debug=debug)

    # Method Argument:
    #   am      Booted program's entry addressing mode: 24, 31, or 64
    #   flags   Any of the following: "zarch", "traps", "CCW1"
    def create_LOD1(self,am=24,flags=[]):
        return LOD1(self.dtypeo,self.booted.psw,am=am,flags=flags)

    # Dump the FBA volume sectors
    def dump(self):
        for r in self.device.sequence:
            print(r.dump())

    # FBA devices do not use this method.
    #def fini(self):
    #    return

    # Return the Area associated with the IPL CCW's, part of IPL Record 0
    # (IPL Record 1 coresides with IPL Record 0 for FBA).
    def ipl_ccw(self,name,debug=False):
        # IPL Record 0 and 1 elements
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

    # Returns the memory area, and Area object, of IPL Record 1
    # (Physically this will coreside with IPL Record 0 in sector 0)
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
                FBAREAD(0x200,self.fbamap.allocation("LOD1").range.beg,1))

        # Build IPL Record 1
        #  - locate CCW ----+
        #  - read CCW-------|----Where sector resides in memory
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

        # Convert the Python objects in IPLREC1 object into binary content
        iplrec1.build()

        content=iplrec1.content
        if len(content)>self.maxipl1:
            raise MediumError(\
                msg="Use boot loader - IPL Record 1 exceeds maximum supported "
                    "length (%s): %s" % (self.maxipl1,len(content)))

        return Area(name,beg=iplrec1.address,bytes=content)

    # Return the maximum record length supported by the volume
    def max_recl(self):
        return self.maxrecl

    # Assign starting sector to area
    def mloc(self,area):
        assert isinstance(area,Area),\
            "%s - 'area' argument must be an instance of Area: %s" \
                % (this_module,area)
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
        for regn in self.prog_regns:
            content=regn.content
            area_len=len(regn)
            area_secs=FBAMAP.sectors(area_len)
            beg_sec=regn.media
            cur_sec=beg_sec
            addr=regn.range.beg
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

    # Set up I/O data for reading a single record of variable length
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
                # Pull out of the area the chunk of bytes for this sector
                chunk=content[beg:min(beg+512,end)]
                # The the Python object expected by the device for
                # sector initialization is created
                rec=recsutil.fba(data=bytes(chunk),sector=sec)
                # Add the sector to the FBA emulated device
                self.device.record(rec)
                sec+=1

    # Write a booted program's directed boot records to the FBA volume
    def write_directed_records(self):
        disk_map_alloc=self.fbamap.allocation("BOOTED")
        sector=disk_map_alloc.range.beg
        for n,dir_rec in enumerate(self.booted.boot_records):
            assert isinstance(dir_rec,BOOTREC),\
                "%s.%s - write_directed_records() "\
                    "self.booted.boot_records[%s] must be a BOOTREC object: %s"\
                        % (this_module,self.__class__.__name__,dir_rec)
            record_bin=dir_rec.record(length=True)
            rec=recsutil.fba(data=record_bin,sector=sector)
            self.device.record(rec)  # Add directed record to FBA volume
            sector+=self.dir_sec

    # Write IPL Record 0 - IPL PSW + first two IPL CCW's
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
        lod1=bytes(64)             # Leave space for Hercules IPL parameters
        self.lod1_bin=self.lod1.binary()   # Create binary LOD1 record
        lod1+=self.lod1_bin        # Add the actual LOD1 record data

        rec=recsutil.fba(data=lod1,sector=sector.range.beg)
        self.device.record(rec)

    # Write the volume label to the device if a volser is provided, otherwise
    # it is not supplied.
    def write_VOL1(self):
        if not self.args.volser:
            return
        sector=self.fbamap.allocation("VOLLBL")

        # Note: sector here is not the sector of the volume label contained
        # in the preceding sector attribute.  'sector' here is the start of
        # the volume table of contents.  A VTOC is not created by iplasma.py so
        # this field in the volume label is set to zero.
        vol1=fbadscb.VOL1(volser=self.args.volser,sector=0,cisize=512,\
            owner=self.args.owner,debug=False)
        if self.args.verbose:
            print("%s - %s" % (this_module,vol1))
        vol1_data=bytes(vol1.to_bytes())
        rec=recsutil.fba(data=vol1_data,sector=sector.range.beg)
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


# Allocation Map of FBA IPL device sectors.
class FBAMAP(Alloc):
    @staticmethod
    def sectors(length):
        return (length+511)//512
    def __init__(self,sectors):
        super().__init__(sectors,protected=True)

    def assign(self,name,sectors):
        self.allocate(self.here(Allocation(name,slots=sectors)))


#
# +--------------------------+
# |                          |
# |   Device Type Database   |
# |                          |
# +--------------------------+
#

class DTYPE(object):

    # Media types and related values including corresponding hardware types.
    # Values are a tuple:
    #    tuple[0]  Whether a sequencial device (True) or not (False)
    #    tuple[1]  LOD1 flag device type flag
    #    tuple[2]  Generic device type's actual device type value
    #    tuple[3]  Maximum logical record size for actual device type. Impacts
    #              IPL Record 2's size, the IPL'd program.  Note: for CKD
    #              devices, each device type has a different maximum logical
    #              record size.  See dictionary for DTYPE.ckd_max for these
    #              values.  CKD uses None as a tuple[3] place holder.
    #    tuple[4]  Whether directed load records require a length field
    #    tuple[5]  Default directed record length including header(s)
    #    tuple[6]  List of actual supported devices of this device type.
    media={"CARD":(True,0x04,"3525",80,True,80,
               ["3525",]),
           "TAPE":(True,0x08,"3420",65535,False,512,
               ["3410","3420","3422","3430","3480","3490","3590","8809","8347"]),
           "FBA": (False,0x10,"3310",65024,True,512,
               ["0671","0671-04","3310","3370","3370-2","9332","9332-600",
                "9313","9335","9336","9336-20"]),
           "CKD": (False,0x20,"3330",None,False,512,
               ["3410","3420","3422","3430","3480","3490","3590","8809",
                "8347"])
          }
           #"ECKD":(0x10,None,None)

    ckd_max={"2305":14136,
             "2311":3625,
             "2314":7294,
             "3330":13030,
             "3340":8368,
             "3350":19069,
             "3375":35616,
             "3380":47476,
             "3390":56664,
             "9345":46456}

    # Set the device type attributes
    # Exceptions:
    #   ValueError if the class can not instantiate itself because the
    #   dtype argument is not recognized.
    def __init__(self,dtype):
        # Supported devices
        self.classes={ "CARD":CRDECK,
                       "FBA": FBAVOL}

        # Device Type attributes used
        self.hdwtype=None        # Medium generic device class
        self.hardware=None       # Hardware device type
        self.lod1_flag=None      # LOD1 record device type flag
        self.max_rec=None        # Maximum supported record size for device
        self.dlen=None           # Whether directed records need a length field
        self.dir_default=None    # Default directed record size
        self.volcls=None         # Class used to instantiate IPL medium
        self.recongized=False    # Whether the dtype was recognized or not
        self.supported=False     # Whether the device is supported

        typ=dtype.upper()        # Generic device type in uppercase

        for generic in ["CARD","TAPE","FBA","CKD"]:
            seq,lod1_flag,dflt,max_rec,dlen,dir_len,dev_list=DTYPE.media[generic]

            # Process generic device type.  If the generic device type being
            # targeted is found, fill in its respective attributes.
            if generic == typ:
                self.hdwtype=generic      # From for loop
                self.hardware=dflt        # From tuple[2]
                self.seq=seq              # From tuple[0]
                self.lod1_flag=lod1_flag  # From tuple[1]
                self.max_rec=max_rec      # From tuple[3]
                self.dlen=dlen            # From tuple[4]
                self.dir_default=dir_len  # From tuple[5]
                self.recognized=True
                break

            if typ not in dev_list:
                # If device type is not in the generic device's supported
                # device types, try a different generic device.  Might be
                # valid there.  If not found in any of the generic device
                # type lists, then the for loop will terminate with nothing
                # found.  That is, self.recognized is still False
                continue

            # dtype is in the generic device's dev_list.
            # Fill the instance's values for it
            self.hdwtype=generic          # From for loop
            self.hardware=typ             # From instance argument
            self.seq=seq                  # From tuple[0]
            self.lod1_flag=lod1_flag      # From tuple[1]
            self.dlen=dlen                # From tuple[4]
            self.dir_default=dir_len      # From tuple[5]

            # For CKD devices, access the maximum record size from the CKD
            # specific dictionary.  Otherwise use the value provided by the
            # generic device.
            if generic == "CKD":
                self.max_rec=DTYPE.ckd_max[hardware]  # From CKD dict.
            else:
                self.max_rec=max_rec                  # From tuple[3]

            self.recognized=True

        # If the device type was recognized, determine if supported and by
        # what class.
        if self.recognized:
            try:
                self.volcls=self.classes[self.hdwtype]  # From attribute dict.
                self.supported=True
            except KeyError:
                pass
                # self.supported still False.


#
# +------------------------------+
# |                              |
# |   IPL Medium Creation Tool   |
# |                              |
# +------------------------------+
#

class IPLTOOL(object):

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

        self.__check_for_boot_options()  # when no boot loader identified

        # Medium information
        self.medium=self.args.medium     # Path to emulated IPL capable medium

        # Establish targered IPL medium device type
        self.dtype=DTYPE(self.args.dtype)     # IPL device type DTYPE object
        if not self.dtype.recognized:
            self.error("unrecognized device type: %s" % self.args.dtype)
        if not self.dtype.supported:
            self.error("unsupported device type: %s" % self.args.dtype)

        self.seq=self.dtype.seq     # True if sequential device type
        self.volcls=self.dtype.volcls  # IPLVOL subclass for output generation
        # Whether directed records require a length field
        self.dlen=self.dtype.dlen

        # Set Boot Loader directed record length -includes header field(s)
        if self.args.boot:
            if self.args.recl:
                if self.args.recl > self.dtype.max_rec:
                    self.recl=self.dtype.dir_default
                    print("%s - WARNING: --recl option exceeds device maximum "
                        "record size, %s, set to device default: %s" \
                            % (this_module,self.dtype.max_rec,\
                                self.dtype.dir_default))
                else:
                    # Use --recl for directed record size
                    self.recl=self.args.recl
            else:
                # Set default boot loader record length
                self.recl=self.dtype.dir_default

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
        objdeck=None                 # Object deck being loaded
        program=None                 # program LDIPL directory (LDIPL object)
        loader=None                  # loader LDIPL directory (LOADER object)
        self.pswreg=None             # PSW argument if a region is specified
        self.bcpsw=False             # True if a BC-mode PSW to be used

        # IPL Capable Medium Content
        #
        # THESE ATTRIBUTES CONSTITUTE WHAT AND HOW IT IS PLACED ON THE IPL
        # MEDITUM
        #
        # This participates in the IPL function
        self.ipl=None     # Either a LDIPL object or its subclass LOADER
        # This is loaded by a boot loader (only if self.ipl is a LOADER object)
        self.booted=None  # Either a BOOTED or BOOTEDIMAGE object or deck

        # Process --psw for mode or region name
        if self.args.psw:
            if self.args.psw=="ec":
                self.bcpsw=False
            elif self.args.psw=="bc":
                self.bcpsw=True
            else:
                self.pswreg=self.args.psw

        # Process --boot
        if self.args.boot:
            loader=LOADER(self.args,length=self.dtype.dlen)
            #print("IPLTOOL.__init__() - loader: %s" % loader)

            if len(loader.load_list)==0:
                self.error("IPL boot loader contains no loadable regions")
            psw_len=0
            psw_in="unknown"
            if loader.psw:
                psw_in="PSW"
                has_psw=loader.psw
                psw_len=len(has_psw)
            if loader.asa:
                psw_in="ASA"
                has_psw=loader.asa
                psw_len=len(has_psw)
            if psw_len < 8:
                self.error(\
                    "boot loader PSW in %s region must be a 64-bit PSW: %s" \
                        % (psw_in,psw_len))

        objdeck=None     # Set to a value if booting an object deck

        if self.fmt == "ld":
            # --format=ld
            #print("IPLTOOL.__init__() - self.source: %s" % self.source)
            if loader:
                program=BOOTED(self.source,self.args.psw,self.args.asa,\
                    hdr_len=self.dtype.dlen)
                if len(program.load_list)==0:
                    self.error("Booted program contains no loadable regions")
            else:
                program=LDIPL(self.source,self.args.psw,self.args.asa,\
                    bcmode=self.bcpsw,exc=self.args.noload)
                if len(program.load_list)==0:
                    self.error("IPL program contains no loadable regions")

        elif self.fmt == "image":
            # --format=image (the default)
            try:
                load=int(self.args.load,16)
            except ValueError:
                raise ValueError("--load argument not hexadecimal: '%s'" \
                    % self.args.load) from None

            if loader:
                program=BOOTEDIMAGE(self.source,load=load)
                if len(program.load_list)==0:
                    self.error("Booted image contains no loadable regions")
            else:
                program=IMAGE(self.source,load=load)
                if len(program.load_list)==0:
                    self.error("IPL image contains no loadable regions")
            #program.loadable()

        elif self.fmt == "object":
            # --format=object
            if not self.seq:
                self.error("option --object requires sequential device "
                    "type, --dtype not sequential: %s" % self.dtype)
            if not loader:
                self.error(\
                    "option --object requires a boot loader using --boot")
            if self.recl and self.recl!=80:
                print("%s - forcing --recl to 80 for option --object" % this_module)
            self.recl=80
            objdeck=DECK_CTLS(self.source)

        else:
            # Note: this should not occur, the argparser will recognize the
            # incorrent --format choice, but it also doesn't hurt.
            raise ValueError("%s unexpected --format option: %s" \
                % (this_module,self.fmt))

        # Establish what content will participate in the IPL function and
        # what will be brought into memory by means of a boot loader.
        # If a boot loader (option --boot) is supplied, it is always used.
        #
        self.ipl=None             # Content participating in IPL function
        self.booted=None          # Content loaded by boot loader if any
        # Only these content attributes are visible outside of the tool's
        # instantiation.

        if loader:
            self.ipl=loader
            if objdeck:
                self.booted=objdeck
            else:
                self.booted=program
        else:
            self.ipl=program

        # Print description of the input programs
        self.__description()

        # Control of the tool now moves to the run() method

    # Prints the IPL program's and, if present, the booted program's information
    def __description(self):

        # Print IPL'd program information
        if isinstance(self.ipl,LOADER):
            print("\nIPL program - Boot Loader: %s" % self.ipl.controls.ctl_path)
            print(self.ipl.description(indent="    "))
        elif isinstance(self.ipl,LDIPL):
            print("\nIPL program - list-directed load: %s" \
                 % self.ipl.controls.ctl_path)
            print(self.ipl.description(indent="    "))
        elif isinstance(self.ipl,IMAGE):
            print("\nIPL program - Image: %s" % self.ipl.img_ctls.ifile)
        else:
            raise ValueError(\
                "%s.%s - __description() - unexcepted IPL program: %s" \
                    % (this_module,self.__class__.__name__,self.ipl))

        if self.booted:
            # Print booted program information
            if isinstance(self.booted,BOOTED):
                print("\nBooted program - list-directed source: %s" \
                    % self.booted.controls.ctl_path)
                print(self.booted.description(indent="    "))
                print("")
            elif isinstance(self.booted,BOOTEDIMAGE):
                print("\nBooted program - image source: %s" \
                    % self.booted.img_ctls.ifile)
            elif isinstance(self.booted,DECK_CTLS):
                print("\nBooted program - absolute deck: %s\n" \
                    % self.booted.dfile)
            else:
                raise ValueError(\
                    "%s.%s - __description() - unexcepted booted program: %s" \
                        % (this_module,self.__class__.__name__,self.booted))

    # This checks for --boot related command-line arguments being specified
    # when --boot NOT specified.  Error messages are printed and the arguments
    # are ignored.
    def __check_for_boot_options(self):
        args=self.args
        if args.boot:
            return
        if args.recl:
            print(\
                "%s - option --recl ignored, option --boot missing" % this_module)

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
        if self.ipl_hwm>0xFFFFFF and self.booted is None:
            raise MediumError(msg="boot loader required for regions resident "
                "above X'FFFFFF', region high-water-mark: X'%08X'" % self.ipl_hwm)

        if isinstance(self.booted,Loadable) and len(self.booted.load_list)==0:
            raise MediumError(msg="boot loaded program contains no loadable "
                "program content")

        # Create the IPL volume content
        volume=self.volcls(self.args,self.ipl,self.booted,self.dtype,\
            verbose=self.verbose)
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
        try:
            filesize=os.stat(self.args.medium).st_size
            print("%s - emulated medium %s created with file size: %s" \
                % (this_module,self.args.medium,filesize))
        except FileNotFoundError:
            print("%s - NOT CREATED emulated medium file: %s" % (this_module,\
                self.args.medium))

        # If requested dump the volume records
        if self.args.records:
            volume.dump()


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

    # Source input file (Note: attribute source in the parser namespace will be
    # a list)
    parser.add_argument("source",nargs=1,metavar="FILEPATH",\
        help="input source path to bare-metal program")

    parser.add_argument("-f","--format",choices=["image","ld","object"],\
        default="image",\
        help="format of input source: "\
             "'image' for ASMA --image output file, "\
             "'ld' for ASMA --gldipl output control file "\
             "'object' for ASMA --object absolute load deck. "\
             "Defaults to 'image'. 'object' also requires --boot option.")

    # Input image load address
    parser.add_argument("--load",metavar="ADDRESS",default="0",\
        help="the hexadacimal memory address at which the image file is loaded. "
             "Defaults to 0")

    # List directed IPL directory's region whose first eight bytes contains the
    # IPL PSW
    parser.add_argument("--psw",metavar="FILENAME",default="IPLPSW.bin",
        help="region containing the bare-metal program's entry PSW. "
             "If region does not exist, the region identified by the --asa option or "
             "the location of the first region defines the entry location.")

    # A boot loader's list directed IPL directory's region containing its
    # first eight bytes.
    parser.add_argument("--lpsw",metavar="FILENAME",default="IPLPSW.bin",
        help="boot loader's PSW region file name, when --boot specified.")

    # List directed IPL directory's region initializing the assigned storage area
    parser.add_argument("--asa",metavar="FILENAME",default="ASALOAD.bin",
        help="region containing the assigned storage area.  Ignored if region does "
             "not exist")

    # A boot laoder's list directed IPL directory's region containing its
    # assigned storage region.
    parser.add_argument("--lasa",metavar="FILENAME",default="ASALOAD.bin",
        help="boot loader's PSW region file name, when --boot specified.")

  # Output IPL medium arguments
    # Output emulated IPL medium device type
    parser.add_argument("-d","--dtype",metavar="DTYPE",default="FBA",
        help="device type of output IPL medium. Defaults to FBA")

    # Volume serial of DASD volume
    parser.add_argument("--volser",metavar="ID",default=None,
        help="When specified, a volume label is created for a DASD volume with"
        "this volume serial. Ignored if not DASD.")

    # Owner of the DASD volume
    parser.add_argument("-o","--owner",metavar="NAME",default="SATK",
        help="Sets a volume's owner when a volume label is created. Defaults "
        "to SATK.")

    # Output emulated IPL medium
    parser.add_argument("-m","--medium",metavar="FILEPATH",required=True,
        help="created output emulated medium.  Required.")

    # Causes the filename in the list-directed IPL directory to be ignored
    parser.add_argument("-n","--noload",metavar="FILENAME",default=[],\
        action="append",
        help="ignore region file when loading the program. Multiple "
             "occurences allowed.")

    # Specify the DASD sizing
    parser.add_argument("-s","--size",choices=["std","mini","comp"],default="mini",\
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

  # Boot loader arguments
    # Boot loader list directed IPL control file
    parser.add_argument("-b","--boot",metavar="FILEPATH",\
        help="boot loader list-directed IPL control file path")

    # Boot loader uses CCW1 format for loading directed records (implies
    # 31-bit addressing for booted program)
    #parser.add_argument("--ccw1",action="store_true",default=False,\
    #    help="boot loader uses CCW-1 format for directed records")

    # Boot loader directed record length
    parser.add_argument("-r","--recl",metavar="SIZE",type=int,\
        help="boot loader record size in bytes. If omitted, defaults to "
             "512 or for CARD device 80")

    # Enables verbose messages
    parser.add_argument("-v","--verbose",default=False,action="store_true",\
        help="enable verbose message generation")

    # Booted program entry addressing mode
    parser.add_argument("-a","--am",default=24,choices=[24,31,64],\
        help="booted program entry addressing mode. Default 24.")

    # Request boot loader to change architecture before entering program
    #parser.add_argument("-z","--zarch",action="store_true",\
    #    help="change architecture before entering program")

    return parser.parse_args()

if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    tool=IPLTOOL(args)
    try:
        tool.run()
    except MediumError as me:
        tool.error(me.msg)
