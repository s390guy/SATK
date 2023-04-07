#!/usr/bin/python3
# Copyright (C) 2022 Harold Grovesteen
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
#
# NOTICES:
# -------
# IBM and z/Architecture are trademarks of International Business Machines
# Corporation.

# qelf.py packages into a single ELF executable file one or more ASMA assembled
# regions.  The regions are assembled into one or more list-directed-IPL
# directories and placed into the ELF as a single package.  The ELF is designed
# for compatibility with the Qemu hardware emulator configured for the s390x
# target.

this_module="qelf.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2022")

# Python imports
import argparse     # Access command-line parser
import os.path      # Path management
import sys          # Access exit() function

# SATK imports
import bintools     # uCP binary functions
import ldidlib      # uCP LDID libary package (will need to move this to SATK)
import satkutil     # SATK utility software


#
# +------------------------------------------------+
# |                                                |
# |   Command-Line Argument Parsing and Analysis   |
# |                                                |
# +------------------------------------------------+
#

# Primary object containing command-line input arguments
class INPUT:
    def __init__(self,args):
      # During INPUT instantiation all command-line arguments are validated
      # for syntax correctness.  Aspects relating to logical use and
      # correctness with referenced input LDID's are part of the semantic
      # analysis done elsewhere.
        self.args=args

        self.err_msgs=[]           # Errors are accumulated here
        self.errors=False          # No errors until found

        # Command-line sourced attributes used by qelf.py.
        self.dups=args.dups        # Whether duplicate region names allowed
        self.elf=args.elf          # Filepath to the output ELF file
        self.verbose=args.verbose  # Enable verbose output
        self.enter_spec=None       # ENTER_SPEC object when present
        self.need_ipl_psw=False    # Whether an IPL PSW is needed
        self.in_specs=[]           # List of INPUT_SPEC objects
        self.memmap=None           # Memory map address (implies creation)

        # Analyze --map command-line argument
        if args.map:
            try:
                self.memmap=int(args.map,16)
            except ValueError:
                self.error("ERROR: --map address not hexadecimal: %s" % \
                    args.mem)

        # Analyze ENTER_SPEC from the command line
        if args.enter:
            ntr_spec=ENTER_SPEC(args.enter,self)
            if not ntr_spec.errors:
                self.enter_spec=ntr_spec
        else:
            self.need_ipl_psw=True

        # Analyze INPUT_SPEC's from the command line
        for inspec in args.regns:
            in_spec=INPUT_SPEC(inspec,self)
            if not in_spec.errors:
                self.in_specs.append(in_spec)

        # Output any error messages
        for msg in self.err_msgs:
            print(msg)

    def __str__(self):
        string=      "INPUT - ELF output: %s" % self.elf
        if self.need_ipl_psw:
            string="%s\n        IPL PSW contains program entry" % string
        else:
            string="%s\n        %s" % (string,self.enter_spec)
        string=    "%s\n        "   % string
        spaces=         "       "
        for n,insp in enumerate(self.in_specs):
            if n == 0:
                string="%s%s" % (string,insp)
            else:
                string="%s\n%s%s" % (string,spaces,insp)
        if self.dups or self.verbose:
            flags="    "
            if self.dups:
                flags="%s --dups" % flags
            if self.verbose:
                flags="%s --verbose" % flags
            string="%s\n        Flags: %s" % (string,flags)
        return string

    # This method accumulates errors as encountered by command-line
    # analysis or other sources.
    def error(self,desc):
        self.err_msgs.append(desc)
        self.errors=True

    # Convenience method for accessing the enter information from the
    # ENTER_SPEC object
    # Returns:
    #   tuple[0]  The region name being entered
    #   tuple[1]  The offset into the region being entered.  May be 0.
    def fetch_enter(self):
        return (self.enter_spec.region,self.enter_spec.offset)

    # Conventence method for accessing the input specifications in the
    # INPUT_SPEC objects.
    # Returns:
    #   A list of INPUT_SPEC objects
    def fetch_input(self):
        return self.in_specs


# Command-line ENTER_SPEC argument
class ENTER_SPEC:
    def __init__(self,ntr_spec,inputo):
        self.inputo=inputo       # INPUT object
        self.ntr_spec=ntr_spec   # ENTER_SPEC string from command-line
        self.errors=False        # No errors until found

        # Values used by qelf.py specifying ELF entry point
        self.region=None   # Name of region being entered by ELF
        self.offset=None   # Offset into the region of the ELF entry point

      # Analyze the command-line ENTER_SPEC argument
        try:
            plus_ndx=ntr_spec.index("+")
            offset_str=ntr_spec[plus_ndx+1:]
            if len(offset_str)==0:
                inputo.error("ENTER_SPEC missing offset: '%s" % ntr_spec)
                self.errors=True
                return
        except ValueError:
            # '+' sign not present in ENTER_SPEC, so offset is zero.
            self.region=ntr_spec  # The entire ENTER_SPEC is the region name
            self.offset=0
            return

        # Offset (+) present in ENTER_SPEC
        if plus_ndx == 0:  # Check whether region is missing
            inputo.error("ENTER_SPEC missing region name: '%s" % ntr_spec)
            self.errors=True
            return

        # Region name present as well as an offset
        # Validate the offset: decimal and hexadecimal preceded by '0x' are
        # both valid
        try:
            if len(offset_str)>=3 and offset_str[:2]=="0x":
                self.offset=int(offset_str[2:],base=16)
            else:
                self.offset=int(offset_str,base=10)
        except ValueError:
             inputo.error("ENTER_SPEC offset not valid: '%s'" % offset_str)
             self.errors=True
             return
        self.region=ntr_spec[:plus_ndx]

    def __str__(self):
        if self.errors:
            return "ENTER_SPEC: IN ERROR '%s'" % self.ntr_spec
        return "ENTER_SPEC: Region %s, Offset (hex) %X" % (self.region,\
            self.offset)


# Command line INPUT_SPEC argument
class INPUT_SPEC:
    def __init__(self,in_spec,inputo):
        self.inputo=inputo       # INPUT object
        self.in_spec=in_spec     # INPUT_SPEC string from command-line
        self.errors=False        # No errors until found

        self.ldid=None           # File path to LDID control file
        self.regions=[]          # List of region names being included
        self.all_regions=True    # All regions are by default included

      # Analyze the command-line INPUT_SPEC argument
        try:
            colon_ndx=in_spec.index(":")
        except ValueError:
            # : not present so entire LDID being packaged
            self.ldid=in_spec     # Identify the LDID being included
            return

        # Colon present
        if colon_ndx == 0:
            inputo.error("INPUT_SPEC: missing LDID control file path '%s'"\
                % in_spec)
            self.errors=True
            return

        # LDID control file path also present.
        self.ldid=in_spec[:colon_ndx]
        regions=in_spec[colon_ndx+1:]
        regions=regions.split(sep=",")
        region_lst=[]
        for n,rgn in enumerate(regions):
            if len(rgn) == 0:
                inputo.error("INPUT_SPEC region %s missing: '%s" \
                    % (n+1,regions))
                self.errors=True
            region_lst.append(rgn)
        if self.errors:
             return

        self.regions=region_lst
        self.all_regions=False

    def __str__(self):
        spec="INPUT_SPEC: %s" % self.ldid
        if self.all_regions:
            return spec
        spec="%s:" % spec
        for rgn in self.regions:
            spec="%s%s," % (spec,rgn)
        return spec[:-1]


#
# +---------------------------+
# |                           |
# |   Region / LDID Manager   |
# |                           |
# +---------------------------+
#

# The CONTENT class encapsulates the content destined to be packaged into
# an ELF file.  This class creates the memory map when requested.  CONTENT
# is used by the RegnMgr to communicate to the QELF object the content of
# the ELF.
# Instance Arguments:
#   nter     An ENTER object defining how to enter the program
#   seq      A list of REGN objects constituting the regions loaded from the
#            packaged ELF.
#   memmap   Memory map load address when the map is produced and included in
#            the packaged ELF.  When a memory map is not included, specify
#            None.
#   verbose  Whether verbose output requested: yes (True) or no (False).
class CONTENT:
    def __init__(self,entero,seq,memmap,verbose=False):
        assert isinstance(entero,ENTER),"'nter' argument must be an ENTER "\
            "object: %s" % nter
        assert isinstance(seq,list),"'seq' argument must be a list: %s" % seq
        assert memmap is None or (isinstance(memmap,int) and memmap>= 0),\
            "'memmap' argument argument must be non-negtive integer or None: "\
            "%s" % memmap

        self.entero=entero     # The ENTER object defining program entry
        self.seq=seq           # REGN object list packaged in ELF
        self.map_addr=memmap   # Memory map load address when requested.
        self.mapo=None         # MAP object or None if not requested
        if self.map_addr:
            self.mapo=MAP(self.map_addr,self.seq)

    def __str__(self):
        if isinstance(self.entero,IPL_PSW):
            nter="IPL PSW in %s" % self.entero.regn.name
        else:
            nter="%s" % self.entero.regn.name
            if self.entero.offset:
                nter="%s+0x%X" % (nter,self.entero.offset)
        if self.map_addr:
            memmap="@0x%X" % self.map_addr
        else:
            memmap="none"

        return "ELF Content: Regions - %s, Enter - %s, Memory map - %s" \
            % (len(self.seq),nter,memmap)

    # Calculate the entry address for the packager, the ELF object
    def entry_addr(self):
        return self.entero.calc_entry()


    # Returns a tuple
    #   tuple[0] a list of LOADABLE objects destined for packaging into the ELF
    #   tuple[1] memory entry address as an integer
    def package(self):
        # Create the list of LOADABLE objects
        loadables=[]
        for regn in self.seq:
            regn.loadable()
            loadables.append(regn)
        if self.mapo:
            loadables.append(self.mapo)

        return (loadables,self.entry_addr())


# ENTER is the superclass of the classes that encapsulate program entry.  It
# manages the information from the region associated with program entry
# required to enter the program.
# Instance Argument:
#   regn   The REGN object upon which program entry in based.
class ENTER:
    def __init__(self,regn,qelfo):
        #assert isinstance(regn,REGN),"'regn' argument must be a REGN object:"\
        #    " %s" % regn
        self.regn=regn   # REGN associated with object.  None for IPL_PSW.
        self.qelfo=qelfo # QELF object for error reporting

    def calc_entry(self):
        raise NotImplementedError("subclass must implement calc_entry() "\
            "method: %s" % self.__class__.__name__)


# ENTER_REGN encapsulates the ENTER_SPEC mechanism for entering the program
# via a region and optional offset.  It is a subclass of ENTER.
# Instance Arguments:
#   regn   The REGN object of the region that is entered
#   offset The integer specifying the offset into the region of the entry point.
class ENTER_REGN(ENTER):
    def __init__(self,regn,offset,qelfo):
        assert isinstance(offset,int),"'offset' argument must be an integer: "\
            " %s" % offset
        assert offset >= 0,"'offset' argument must be a non-negative value: "\
            " %s" % offset
        assert isinstance(qelfo,QELF),"'qelfo' argument must be a QELF object:"\
            " %s" % qelfo

        super().__init__(regn,qelfo)
        self.offset=offset
        self.qelfo=qelfo

    # Calculate from the start of the entry region the entry address
    # Returns:
    #   an integer that is the entry memory address
    def calc_entry(self):
        regn_load=self.regn.core.load
        regn_len=len(self.regn.core)
        if self.offset > regn_len:
            self.qelfo.cb_error("WARNING: entry offset exceeds region %s"\
                "length, %s: %s" % (self.regn.name,regn_len,self.offset),\
                    error=False)
        regn_load+=self.offset
        return regn_load


# IPL_PSW encapsulates the use of an IPL PSW in a region loaded at address
# X'000' containing a short PSW in the first eight bytes of the region's
# binary content.  This entry mechanism is used when an ENTER_SPEC is not
# used in the commmand line.  It is the "fall back" approach.  IPL_PSW is
# a subclass of ENTER.
# Instance Argument:
#   regn   The REGN object of the region loaded at address X'000' containing
#          the IPL PSW.
#   qelfo  The QELF object of the tool for user error reporting.
class IPL_PSW(ENTER):
    def __init__(self,regn,qelfo):
        #assert isinstance(regn,REGN),"'regn' argument must be a REGN object:"\
        #    " %s" % regn
        # For IPL_PSW objects, the actual region is determined later in the
        # process.  It is OK that the REGN object is None
        assert isinstance(qelfo,QELF),"'qelfo' argument must be a QELF object:"\
            " %s" % qelfo

        super().__init__(regn,qelfo)
        
    def add_load_zero_regn(self,regno):
        assert isinstance(regn,REGN),"'regn' argument must be a REGN object:"\
            " %s" % regn
        self.regn=regno

    # Calculates the entry point from the IPL PSW embedded in the region
    # Returns:
    #   the entry memory address as an integer.
    def calc_entry(self):
        regn_core=self.regn.core.copy(mutable=False)
        if len(regn_core)<8:
            self.qelfo.cb_error("ERROR: Region %s must be at least 8 bytes "\
                "when supplying IPL PSW: %s" % len(regn_core,error=True))
            return None

        # Extract PSW address from the region core:
        PSW=regn_core[4:8]   # bytes object
        address=int.from_bytes(PSW,byteorder="big",signed=False)
        address &= 0x7FFFFFFE  # Remove address mode bits for short PSW
        return address


# This class manages LDID's and regions for the ELF packager
# Instance Arguments:
#   ldid       A string constituting the file path to the LDID control file
#              Internally converted to an absolute path, allowing none absolute
#              paths and absolute paths to be included in the INPUT_SPEC.
#   qelfo      QELF object containing the run() method.
#   all_regns  Whether all regions from the LDID are being included (True/False)
#   verbose    Whether verbose messages are generated (True) or not (False).
class LDID:
    def __init__(self,ldid,qelfo,all_regns=True,verbose=False):
        self.qelfo=qelfo       # QELF object (for call backs)
        self.verbose=verbose   # Whether to generate verbose messages
        self.all_regns=all_regns  # Whether all regions are packaged.

        # Absolute path to the LDID control file
        self.ldid=os.path.abspath(ldid)

        # Dictionary of region names mapped to ldidlib.Core objects
        self.regions={}    # See access() method
        self.region_seq=[] # ldidlbi.Core object of region being packaged
        # Need both.  If the region is explicitly coded in the INPUT_SPED,
        # then it must be available by its name.  If no regions are coded,
        # then the sequence encountered in the control file must be maintained.

    # Access the LDID control file and read all regions
    # Note: region names are unique because they are file names within the
    # host file system which must be unique additionally, the file names are
    # derived from the assembler START statement that creates an assembler
    # label for the region name.  Assembler label's must also be unique.
    #
    # Exceptions Raised, but not caught here:
    #   ValueError when control file can not be read
    #   ldidlib.LDIPLError when core image file can not be read
    def access(self):
        access_ldid=ldidlib.Access(self.ldid)
        # May generate ValueError (not caught here)
        access_ldid.read()
        # May generate LDIPLError (not caught here)
        # Control file and core image files have now been read

        ctrl=access_ldid.ctrl    # Ctrl object
        # Create dictionary of region names mapped to ldidlib.Core objects
        for c in ctrl.cores:
            assert isinstance(c,ldidlib.Core),"core must be a ldidlib.Core "\
                "object: %s" % c
            if self.verbose:
                print("Adding region: %s" % c.region_name)
            self.regions[c.region_name]=c
            self.region_seq.append(c)

    # Returns the ldidlib.Core object of the corresponding region name
    # Method Argument:
    #   regn_name   Name of the region being fetched
    # Returns:
    #   ldidlib.Core object
    def fetch_core(self,regn_name):
        return self.regions[regn_name]


# The LOADABLE base class makes the subclass loadable into the ELF as a
# program segment.  When the subclass is ready to make itself loadable, it
# calls the make_loadable() method.  The MAP and REGN classes are subclasses
# of LOADABLE.
class LOADABLE:

    PT_LOAD = 1    # Program Segment Table Entry type - loadable

    # p_flags values:
    PF_R = 4       # Segment may be read
    PF_W = 2       # Segment may be written
    PF_X = 1       # Segment may be executed
    p_flags=PF_R + PF_W + PF_X  # Segment may be read, written, and executed

    # p_align encoding as bytearray
    p_align=bytearray((3).to_bytes(8,byteorder="big",signed=False))

    # Program Segment Table Entry Length
    PTSE_LEN=56     # Length in bytes

    def __init__(self):
        self.seg_addr=None   # Segment load address
        self.seg_len=None    # Segment length in bytes
        self.seg_bin=None    # Segment binary content as a bytes sequence
        self.is_loadable=False   # Not made 'loadable' yet.

        self.seg_offset=None # Segment's location offset within the ELF.

        # Actual Program Segment Table Entry ELF content.  See encode_pste()
        self.pste=None       # Encoded Program Segment Table Entry

    # Creates the binary content of this LOADABLE object's ELF Program Segment
    # Table Entry.
    # Returns:
    #   a mutable bytearray sequence
    def encode_pste(self):
        assert self.loadable() == True,"encode_pste() can only be called "\
            "if the LOADABLE object is loadable: %s" % self.loadable()

        bin=bytearray(LOADABLE.PT_LOAD.\
            to_bytes(4,byteorder="big",signed=False))
        bin+=LOADABLE.p_flags.to_bytes(4,byteorder="big",signed=False)
        bin+=self.seg_offset.to_bytes(8,byteorder="big",signed=False)
        p_vaddr=self.seg_addr.to_bytes(8,byteorder="big",signed=False)
        bin+=p_vaddr    # Set p_vaddr value
        bin+=p_vaddr    # Set p_paddr value the same as p_vaddr
        p_filesz=self.seg_len.to_bytes(8,byteorder="big",signed=False)
        bin+=p_filesz   # Set p_filesz value
        bin+=p_filesz   # Set p_memsz value the same as p_filesz
        bin+=LOADABLE.p_align   # Set p_align value

        assert len(bin) == LOADABLE.PTSE_LEN,"Program Segement Table Entry "\
            "length must be %s: %s" % (LOADABLE.PTSE_LEN,len(bin))
        return bin

    # This method in the subclass causes the subclass to make itself loadable
    # by calling the make_loadable() method.  The subclass must implement
    # this method.
    def load(self):
        raise NotImplementedError("load() method must be implememted by "\
            "subclass: %s" % self.__class__.__name__)

    # Returns whether this object is loadable (True) or not (False).
    # The object is loadable after make_loadable() has been called by the
    # subclass in its implementation of the load() method.
    def loadable(self):
        return self.is_loadable

    # Subclass calls this method making itself loadable into the ELF
    # Method Arguments:
    #   addr   Address at which program segment is loaded
    #   bin    A bytes type sequence of the program's content
    def make_loadable(self,addr,bin):
        #print("called make_loadable() %r" % self)
        assert isinstance(addr,int) and addr >=0,"'addr' argument must be "\
            "a non-negative integer: %s" % addr
        assert isinstance(bin,(bytes,bytearray)),"'bin' argument must be a "\
            "bytes type sequence (bytes or bytearray): %s" % bin
        # The check for a zero length binary object is performed in 
        # ELF_HDR.update() method.  When encountered the zero length binary
        # generates a warning message and is not included in the ELF, although
        # it will be included in the memory map.
        #assert len(bin)>0,"'bin' argument must not be of zero length: %s" % \
        #    len(bin)
        
        #assert isinstance(self.seg_offset,int) \
        #    and self.seg_offset>=ELF_HDR.length,"'seg_offset' attribute must "\
        #        "be an integer greater than %s: %s" \
        #            % (ELF_HDR.e_hsize,self.seg_offset)

        assert not self.loadable(),"can not call make_loadable() more "\
            "than once"

        self.seg_addr=addr
        self.seg_len=len(bin)
        if isinstance(bin,bytearray):
            self.seg_bin=bytes(bin)
        else:
            self.seg_bin=bin
        self.is_loadable=True

    # Sets the offset of this loadable
    # Returns:
    #   an updated file offset for the next segment
    def set_file_offset(self,offset):
        #print("called sef_file_offset() %r" % self)
        self.seg_offset=offset
        return self.seg_offset + len(self.seg_bin)


# The MAP class generates a memory map when requested.
# Instance Arguments:
#   address   The load address of the Memory Map
#   regions   A list of REGN object being incorporated into the map.
class MAP(LOADABLE):

    header=32    # Length of a Memory Map header

    def __init__(self,address,regions):
        super().__init__()

        assert isinstance(regions,list),"'regions' argument must be a list: "\
            "%s" % regions
        assert isinstance(address,int) and address>=0,"'address' argument "\
            "must be a non-negative integer: %s" % address

        self.addr_beg=address   # Memory Map load address
        self.addr_end=address   # The last byte of the memory map
        self.regions=regions    # A REGN list included in the map

        # Length of the Map including header and all map entries
        self.total_entries=len(self.regions)+1  # Number of memory map entries
        # the +1 is for the entry devoted to the Memory Map itself.
        self.total_length=( self.total_entries * MAP_ENTRY.length ) \
            + MAP.header
        self.addr_end=self.addr_beg + self.total_length - 1

        # A list of MAP_ENTRY objects.  See build() method
        self.entries=[]
        for regn in self.regions:
            core=regn.core
            self.entries.append(MAP_ENTRY(regn.mapname,core.load,len(core)))
        # Add this memory map to the map as its own entry.
        self.entries.append(\
            MAP_ENTRY("MEMMAP64",self.addr_beg,self.total_length))

        # The encoded Memory Map ready to be packaged as an ELF program segment
        self.map_bin=self.encode()  # bytearray sequence

    def __len__(self):
        return len(self.map_bin)

    # Convert the Memory Map to a bytes sequence the Memory Map
    # Returns:
    #   a bytes object containing the binary map content
    def encode(self):
        bin=bytearray("MMAP")     # Eye-catcher
        bin+=bytearray([0,0,0,0])  # four reserved bytes
        bin+=bytearray(self.addr_beg.to_bytes(8,byteorder="big",signed=False))
        bin+=bytearray(MAP_ENTRY.length.to_bytes(8,byteorder="big",\
            signed=False))
        bin+=bytearray(self.addr_end.to_bytes(8,byteorder="big",signed=False))
        assert len(bin) == MAP.header,"'bin' header must be of length %s: %s" \
            % (MAP.header,len(bin))

        for entry in self.entries:
            bin+=entry.encode()

        assert len(bin) == self.total_length,"'bin' map must be of length: %s:"\
            " %s" % (self.total_length,len(bin))

        return bytes(bin)

    # Make this Memory Map packagable as a program segment in the ELF.
    def load(self):
        self.make_loadable(self.addr_beg,self.map_bin)


# The MAP_ENTRY class encapsulates a single entry in a memory map.
class MAP_ENTRY:

    length=24    # Length of a Memory Map entry in bytes

    def __init__(self,name,load,length):
        self.name=name       # Region name
        self.load=load       # Region starting memory address
        self.length=length   # Region length in bytes

    # Encode the Memory Map content as a bytearray mutable sequence.
    def encode(self):
        bin=bytesarray(self.name.ljust(8))
        bin+=bytesarray(self.load.to_bytes(8,byteorder="big",signed=False))
        bin+=bytesarray(self.length.to_bytes(8,byteorder="big",signed=False))
        assert len(bin)==MAP_ENTRY.length,"'bin' value must be of length %s: "\
            "%s" % (MAP_ENTRY.length,len(bin))
        return bin


# This class manages the names in a name space.  It monitors the names for
# duplicates and tracks information found.
class NAME_SPACE:
    def __init__(self,ident):
        self.ident=ident       # NAME_SPACE identification
        self.unique_names={}   # Dictionary of names mapped to name count
        self.dups=False        # Duplicate names found

    # This method adds a name to the name space.  Tracking for duplicates
    # occurs in this method.
    def add_name(self,name):
        assert isinstance(name,str),"'name' argument must be a string %s" \
            % name

        try:
            count=self.unique_names[name]
            # Found so already encountered.  A duplicate name has been found
            self.unique_names[name]=count+1
            self.dups=True
        except KeyError:
            # Name not found, so is new.  Set initial count to 1
            self.unique_names[name]=1

    # Display the duplicate names encountered
    # Method Arguments:
    #   desc   A string describing the list of duplicates.
    #   qelfo  The QELF object against which call back is made
    #   error  Whether the description of an error (True) or not (False)
    def display(self,desc,qelfo,error):
        dup_names=self.duplicates()
        num_dups=len(dup_names)
        if num_dups > 1:
            s="s"
        else:
            s=""
        qelfo.cb_error("%s%s encountered: %s" % (desc,s,num_dups),error=error)
        for name in dup_names:
            qelfo.cb_error("    %s" % name)

    # Returns a list of strings of duplicate names in the name space.  Should
    # only be called after all names have been added to the name space.
    def dulicates(self):
        d=[]  # List of duplicate names
        for name,count in self.unique_names.items:
            if count > 1:
                d.append(name)
        return d

    # Fetch the count of a specific region name.
    # Returns:
    #   integer number of times the region name is present in the INPUT_SPECs
    #           either implicitly or explicitly.
    # Exceptions:
    #   KeyError if the name is not present in the name space
    def fetch_count(self,name):
        return self.unique_names[name]


# Input Region Object representing a single included region.
# Instance Arguments:
#   ldld        LDID object in which this region resides
#   regn_core   Region ldidlib.Core object.
class REGN(LOADABLE):
    def __init__(self,ldid,regn_core):
        super().__init__()

        assert isinstance(ldid,LDID),"'ldid' argument must bea LDID object: %s"\
            % ldid
        assert isinstance(regn_core,ldidlib.Core),"'regn_core' "\
            "argument must be a ldidlib.Core object: %s" % regn_core

        self.ldid=ldid       # LDID object of this regions LDID control file
        self.core=regn_core  # ldidlib.Core object or bytes sequence
        self.name=regn_core.region_name   # Specific LDID region being included

        # Memory Map region name.  Actual region name truncated to eight
        # characters.  Mostly never used, but ASMA supports labels longer than
        # eight characters so it "could" happen.  Memory Map structure is
        # constrained to a limit of eight characters in the name.
        self.map_name=self.name[:min(8,len(self.name))]
        
    def __len__(self):
        return len(self.core)

    def encode(self):
        return self.core.copy(mutable=True)

    # Make this region packable into the ELF.
    def load(self):
        self.make_loadable(self.core.load,self.core.copy(mutable=False))


class RegnMgr:
    def __init__(self,inputo,qelfo):
        assert isinstance(inputo,INPUT),"'inputo' must be an INPUT object: "\
            "%s" % inputo

        self.inputo=inputo   # INPUT object driving the run()
        self.dups=inputo.dups        # Whether duplicate region names allowed
        self.verbose=inputo.verbose  # Whether verbose output created
        self.qelfo=qelfo     # QELF object containing run() method
        self.errors=0        # Number of encountered errors.
        # First REGN object that loads at address zero
        self.load_zero=None  # used when ENTER_SPEC is omitted for IPL PSW

      # ENTER_SPEC data
        self.enter_name=None     # Enter region name
        self.enter_regn=None     # REGN object of entry region
        self.enter_offset=0      # Offset into region of entry
        self.enter_ipl=False     # Use region with 0 address as having IPL PSW

        if inputo.need_ipl_psw:
            self.enter_ipl=True
        else:
            self.enter_name,self.enter_offset=inputo.fetch_enter()


      # INPUT_SPEC data
        self.in_specs=inputo.fetch_input()  # List of INPUT_SPEC objects
        self.region_seq=[]       # In-order list of REGN objects.
        # This becomes the order in which the Core objects are added to the ELF.
        self.unique_ldids={}     # Unique LDID's from input spec's
        # LDID Core objects are created for each region in the LDID.

        # Extract INPUT_SPEC objects from the INPUT object.
        self.in_specs=inputo.fetch_input()

        # Build dictionary of unique LDID objects and convert INPUT_SPECs
        # to LDID and REGN objects.  LDID objects are used when the INPUT_SPEC
        # does not list any expicit regions.  REGN objects are used when the
        # INPUT_SPEC contains explicit region names.  LDID objects are expanded
        # to a list of reqions based upon the LDID control file region sequence.
        regn_ns=NAME_SPACE("region")
        for in_spec in self.in_specs:
            try:
                ldido=self.unique_ldids[in_spec.ldid]
                # LDID control file already encountered.  LDID has been
                # read the first time, so just proceed to next INPUT_SPEC.
            except KeyError:
                ldido=LDID(in_spec.ldid,self.qelfo,\
                    all_regns=in_spec.all_regions)
                # New LDID control file, add it to the dictionary of unique
                # LDID's and read the regions from the LDID.
                try:
                    ldido.access()   # Read all regions in the LDID
                except ValueError as ve:
                    # Could not read the control file
                    self.qelfo.error("ERROR: %s" % ve,error=True)
                    self.errors+=1
                    continue
                except ldidlib.LDIPLError as le:
                    # Could not read a region core image file
                    self.qelfo.error("ERROR: %s" % le,error=True)
                    self.errors+=1
                    continue
                # If errors encountered reading the LDID, the errors are
                # queued with QELF and processing continues with the next
                # INPUT_SPEC object.

                # No errors, so add this LDID to the list of unique LDIDs.
                self.unique_ldids[in_spec.ldid]=ldido

            if in_spec.all_regions:
                # All regions implicitly packaged from this LDID
                #   ldid_control_file_path without regions
                for regn_core in ldido.region_seq:
                    regno=REGN(ldido,regn_core)
                    self.region_seq.append(regno)
            else:
                # LDID with explicit region packaged.
                #   ldid_control_file_path:name1,name2,....
                for regn_name in in_spec.regions:
                    coreo=ldido.fetch_core(regn_name)
                    regno=REGN(ldido,coreo)
                    self.region_seq.append(regno)

        # Handle each region now independent of the LDID source.
        for regno in self.region_seq:
            if self.enter_ipl:
                if self.load_zero is None and regno.core.load==0:
                    self.load_zero=regno
                    #print("setting self.load_zero: %s" % self.load_zero)
            elif self.enter_name and self.enter_name == regno.name:
                self.enter_regn=regno  # Remember entry REGN object
                
            regn_ns.add_name(regno.name)

        # Check for duplicate region names if --dups NOT present
        if not self.dups and regn_ns.dups:
            regn_ns.display("ERROR: duplicate region name",self.qelfo,\
                error=True)

        # Check that ENTER_SPEC region found
        if self.enter_regn is None:
            self.qelfo.cb_error("ERROR: enter region not found: %s" \
                % self.enter_name,error=True)


      # Memory Map Data
        self.memmap=inputo.memmap    # Memory Map load address
        # Determine if a memory map is being constructed
        if inputo.memmap != None:
            self.is_memmap=True
        else:
            self.is_memmap=False

        # Memory Map Region names space
        map_ns=NAME_SPACE("map")

        if self.is_memmap:
            # Producing a memory map so check for possible duplicate memory
            # map names.
            for regno in self.region_seq:
                map_ns.add_name(regno.map_name)
            if map_ns.dups:
                map_ns.display("WARNING: duplicate memory map name",self.qelfo,\
                    False)

        if self.verbose:
            if len(self.unique_ldids) == 0:
                print("LDID's: None")
            else:
                print("LDID's:")
                for ldid in self.unique_ldids.keys():
                     print("    %s" % ldid)
                print("Region Sequence:")
                for regno in self.region_seq:
                    print("    %s - %s" % (regno.name,regno.core))

    # Summarize ELF content by creating the CONTENT object
    # Returns:
    #   a CONTENT object.
    def content(self):
        if self.enter_ipl:
            nter=IPL_PSW(self.load_zero,self.qelfo)
        else:
            nter=ENTER_REGN(self.enter_regn,self.enter_offset,self.qelfo)
        if self.is_memmap:
            memmap=self.memmap
        else:
            memmap=None
        return CONTENT(nter,self.region_seq,memmap,verbose=self.verbose)


#
# +-----------------------------------------------+
# |                                               |
# |   ELF (Execute and Linking Format) Creation   |
# |                                               |
# +-----------------------------------------------+
#

# ELF and its related classes create binary content of the packaged regions.
# This is not a complete implementation of an ELF construction library.  It
# Only creates the portions of the ELF required for this utility.  While the
# implementation is complete from the perspective to the ELF standard, field
# names used in the standard are used here simplifying references to the
# standard.
#
# Each of the following ELF components has its own class.
#    ELF_HDR -  ELF Header
#    ELF_PSTE - contained within the LOADABLE object
#    ELF_SEG  - contained within the LOADABLE object
#
# If a memory map is being created, ELF_PTE and ELF_PROG objects will be
# created for the map.  The map itself is built by the CONTENT.memory_map()
# method.

# Instance Arguments:
#   loadables      a list of MAP or REGN objects loadable from the ELF
#   program_entry  the memory address used to enter the ELF
#   qelfo          QELF object allowing access to call back methods
#   verbose        Whether verbose message are generated (True) or not (False)
class ELF:
    def __init__(self,loadables,program_entry,qelfo,verbose=False):
        self.verbose=verbose     # Whether verbose messages generated
        self.loadables=loadables # Program segments being loaded
        self.program_entry=program_entry

        # Build the ELF Header and Program Segment Table
        self.headero=ELF_HDR(self.loadables,self.program_entry,qelfo)

        # ELF Related lengths
        self.hdr_len=ELF_HDR.e_hsize
        self.pste_off=self.hdr_len
        self.pst_len=self.headero.total_pst_len
        self.elf_file_len=self.headero.total_file_len

        self.elf_hdr_bin=self.headero.encode()
        self.elf_bin=bytearray(0)       # Inititalize ELF file content
        self.elf_bin+=self.elf_hdr_bin  # Add ELF header

        self.pste_bin=self.headero.pste # Program Segment Table binary content
        self.elf_bin+=self.pste_bin

        self.pst_off_first=self.headero.pst_off_first  # First Segment offset
        self.pst_bin=self.headero.pst   # Program Segments binary content
        self.elf_bin+=self.pst_bin
        assert len(self.elf_bin) == self.headero.total_file_len,"ELF binary "\
            "calculated lenght, %s, does not match binary content length: %s"\
                % (self.header.total_file_len,len(self.elf_bin))

        if self.verbose:
            print("\nELF Header:")
            print(satkutil.dump(self.elf_hdr_bin,start=0,mode=24,indent="    "))
            
            print("\nELF Program Segment Table")
            print(satkutil.dump(self.pste_bin,start=self.pste_off,mode=24,\
                indent="    "))
            
            if len(self.loadables)>1:
                s="s"
            else:
                s=""
            print("\nELF Program Segment%s" % s)
            print(satkutil.dump(self.pst_bin,start=self.pst_off_first,\
                mode=24,indent="    "))


# Creates the ELF Header binary content
# Instance Arguments:
#     loadables   A list of MAP or REGN objects being loaded from the ELF
class ELF_HDR:

    e_hsize=64 # Length of the ELF Header in bytes

    # ELF Magic values
    MAG0=0x7F  # X'7F'
    MAG1=0x45  # E - ASCII
    MAG2=0x4C  # L - ASCII
    MAG3=0x46  # F - ASCII
    MAGIC=bytearray([MAG0,MAG1,MAG2,MAG3])  # ELF MAGIC as a list of integers

    HDR=MAGIC

    CLASS    =0x02  # 64-bit values in ELF
    DATA     =0x02  # values are in "big-endian" bit sequence
    VERSION  =0x01  # Current ELF version
    OSABI    =0x03  # Linux ELF
    PAD      =[0,0,0,0,0,0,0,0]  # PAD as a list of integers

    HDR=MAGIC
    HDR+=bytearray([CLASS,DATA,VERSION,OSABI])
    HDR+=bytearray(PAD)
    assert len(HDR)==16,"HDR must be 16 bytes: %s" % len(HDR)

    e_type   =0x0002  # Executable ELF
    HDR+=bytearray(e_type.to_bytes(2,byteorder="big",signed=False))

    e_machine=22      # or 0x16 - IBM(R) S390 z/Architecture(R)
    HDR+=bytearray(e_machine.to_bytes(2,byteorder="big",signed=False))

    e_version=1       # Original ELF version
    HDR+=bytearray(e_version.to_bytes(4,byteorder="big",signed=False))

    e_entry=0         # ELF entry address.  Inserted by encode() method
    HDR+=bytearray((0).to_bytes(8,byteorder="big",signed=False))
    # Insertion: [24:32]  See update() method

    # Offset of program segment table start. Immediately follows the ELF Header.
    e_phoff=e_hsize
    HDR+=bytearray(e_phoff.to_bytes(8,byteorder="big",signed=False))

    # Offset of the section table header.
    e_shoff=0    # ELF contains no sections, so the offset is zero.
    HDR+=bytearray(e_shoff.to_bytes(8,byteorder="big",signed=False))

    e_flags=0    # Not used by e_machine target.
    HDR+=bytearray(e_flags.to_bytes(4,byteorder="big",signed=False))

    # Length of the ELF Header in bytes
    HDR+=bytearray(e_hsize.to_bytes(2,byteorder="big",signed=False))

    # Program Segment Table Entry length in bytes
    e_phentsize=56  # can not be set until the ELF is built.
    HDR+=bytearray(e_phentsize.to_bytes(2,byteorder="big",signed=False))

    # Number of entries in the Program Segment Table
    e_phnum=0      # can not be set until the ELF is built.
    HDR+=bytearray(e_phnum.to_bytes(2,byteorder="big",signed=False))
    # Insertion: [56:58]  See update() method

    # Size of the Section Header Entry in bytes
    e_shentsize=0  # No sections, so set this to zero
    HDR+=bytearray(e_shentsize.to_bytes(2,byteorder="big",signed=False))

    # Number of entries in the Section Header Table
    e_shnum=0      # No Section Header Table entries
    HDR+=bytearray(e_shnum.to_bytes(2,byteorder="big",signed=False))

    # Section header index containing section names
    e_shstrndx=0   # No sections so no index of the section header
    HDR+=bytearray(e_shnum.to_bytes(2,byteorder="big",signed=False))

    assert len(HDR) == e_hsize,"'HDR' class attribute must be of length %s:" \
        " %s" % (e_hsize,len(HDR))

    def __init__(self,loadables,e_entry,qelfo):
        self.qelfo=qelfo           # QELF object to enable call backs
        self.loadables=loadables   # List of LOADABLE objects

        self.hdr_bin=ELF_HDR.HDR   # Binary content as a mutable bytearray

        # Number of Program Segment Table entries
        self.e_phnum=len(loadables)
        # Total length of the Program Segment headers
        #self.ephentsize=self.e_phnum * ELF_HDR.e_phentsize

        self.e_entry=e_entry         # Program entry memory address

      # Data used in constructing ELF but not part of the header itself
        self.pste=None          # Program Segment Table binary
        self.total_pst_len=0   # Length of total Program Segment Table
        self.total_file_len=0  # Calculated Length of the complete ELF file

        self.update(self.e_entry)

    # Creates binary content of the ELF Header.
    def encode(self):
        assert len(self.hdr_bin) == ELF_HDR.e_hsize,"self.hdr_bin length "\
            "must be %s: %s" % (ELF_HDR.e_hsize,len(self.hdr_bin))
        return self.hdr_bin

    # Updates the ELF Header with the build time determined entry point and
    # Program Segment Table values.
    # The following three values are set in the ELF Header binary content.
    #   [24:32]  e_entry
    #   [56:58]  e_phnum
    # The Program Segment Table containing SATK regions is also built
    def update(self,entry):
        assert isinstance(entry,int) and entry>=0,"'entry' argument must be "\
            "a non-negative integer: %s" % entry

        self.e_entry=entry
        self.hdr_bin[24:32]=bytearray(self.e_entry.to_bytes(8,byteorder="big",\
            signed=False))
        self.hdr_bin[56:58]=bytearray(self.e_phnum.to_bytes(2,byteorder="big",\
            signed=False))

        self.total_pst_len=self.e_phentsize * self.e_phnum
        self.pst=bytearray(0)   # Initialize the Program Segment Table

        # Calculate Program Segment offsets in the file.  The Program
        # Segments start immediately following the Program Segment Table
        for loadable in self.loadables:
            loadable.load()

        # Now that we have the length of the program segment image, we can
        # assign the file offset.
        self.pst_off=ELF_HDR.e_hsize + self.total_pst_len
        self.pst_off_first=self.pst_off   # First segment's offset
        for loadable in self.loadables:
            self.pst_off=loadable.set_file_offset(self.pst_off)

        # Initialize the Program Segments and Program Segment Table
        pst=bytearray(0)   # Initialize the Program Segments
        pste=bytearray(0)  # Initialize the Program Segment Table
        
        # Add each Program Segment to the Program Segment Table and
        # its entry in the Program Segment Table Entries.
        for loadable in self.loadables:
            if len(loadable) == 0:
                qelfo.cb_error("WARNING: zero length region excluded: %s" \
                    % loadable.name,error=False,abort=False)
                continue
            pst+=loadable.encode()
            pste+=loadable.encode_pste()

        self.pst=pst   # Add the PS's to the ELF_HDR object
        self.pste=pste # Add the PSTE to the ELF_HDR object
        self.total_file_len=self.pst_off  # This is how big the file should be.


#
# +------------------+
# |                  |
# |   qelf.py Tool   |
# |                  |
# +------------------+
#

# Instance Arguments:
#   inputo   An instance of INPUT containing command-line arguments
class QELF:
    def __init__(self,inputo):
        assert isinstance(inputo,INPUT),"'inputo' must be an INPUT "\
            "object: %s" % inputo
        self.inputo=inputo

        self.messages=[]      # List of accumulated messages
        self.errors=0         # Number of error messages cb_error(error=True)
        self.inputo=inputo    # INPUT object
        self.verbose=inputo.verbose  # Whether verbose output enabled

        if self.verbose:
            # Print command formatted command-line
            print(inputo)

        # Everything from this point down is created by the run() method or
        # methods called by the run() method.
        self.rgnmgr=None

        # The ELF content.  See the run() method
        self.content=None

    # Error message handling call back.
    # Method Arguments:
    #   msg     A string that constitutes the message.
    #   abort   Whether to immediately abort qelf.py upon encountered error.
    #           Otherwise accummulate.  Takes precedence over error argument.
    #   error   Whether message is an error (True) or a warning (False)
    def cb_error(self,msg,error=False,abort=False):
        if abort:
            print(string)
            sys.exit(1)
        self.messages.append(msg)
        if error:
            self.errors+=1

    def run(self):
        if self.inputo.errors:
            print("%s: ERROR: processing aborted due to command-line errors"\
                % (this_module))
            return

        # Create region manager from the command-line
        self.rgnmgr=RegnMgr(self.inputo,self)
        # Gather ELF content into a CONTENT object
        self.content=self.rgnmgr.content()
        if self.verbose:
            print(self.content)

        # Fetch the list of loadable program segments and program entry address
        loadables,pgm_entry=self.content.package()  # Package
        for n,pgm in enumerate(loadables):
            assert isinstance(pgm,LOADABLE),"loadables[%s] must be a MAP or "\
                "REGN object: %s" % (n,pgm)

        # Generate the ELF file content
        elf=ELF(loadables,pgm_entry,self,verbose=self.verbose)

        # Write the ELF file
        elf_fp=self.inputo.elf
        output_data=elf.elf_bin
        assert len(output_data) > 0,"output data length: 0"
        if elf_fp:
            elf_out=satkutil.BinFile(filepath=elf_fp,data=elf.elf_bin)
            print("writing ELF: %s" % elf_fp)
            elf_out.write()


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
        description="SATK ASMA assembled regions packaged into a single ELF")

    parser.add_argument("regns",nargs="+",metavar="INPUT_SPEC",\
        help="one or more packaged input region specifications.  At least "\
            "one is required.")

    parser.add_argument("-d,","--dups",action="store_true",default=False,\
        help="allow duplicate region names. Not recommended with --map.")

    parser.add_argument("--elf",metavar="FILEPATH",default=None,\
        help="filepath to output ELF file.  Required.")

    parser.add_argument("--enter",metavar="ENTER_SPEC",default=None,\
        help="enter specification for packaged ELF. If omitted, an IPL PSW "\
            "is assumed present")

    parser.add_argument("--map",metavar="ADDRESS",default=None,\
        help="include a memory map with the packaged regions")

    parser.add_argument("-v","--verbose",action="store_true",default=False,\
        help="enable verbose output")

    return parser.parse_args()


if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    cmd_line=INPUT(args)  # Perform syntactical analysis of command-line
    QELF(cmd_line).run()  # Package and output ELF
