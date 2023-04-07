#!/usr/bin/python3
# Copyright (C) 2023 Harold Grovesteen
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

# This module encapsulates the creation of and interpretation of a list-directed
# IPL root directory.  It provides a command-line interface for the display of a
# LDIPL directory content.
#
# It is a refactoring into a common set of objects the interpretation processing from
# iplasma.py and the creation processing from asma.asmbin.py.  Ultimately both
# should incorporate use of these objects directly or subclassed.
#

this_module="ldidlib.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2023")

# Python imports
import argparse
import os.path

# SATK imports
# Note: the module that imports this module must ensure the PYTHONPATH includes
# the tools directory.  This is normally accomplished by having the importer of
# this module be resident in the tools directory and it has added tools/ipl to
# the PYTHONPATH so it can import this module.
import satkutil

#
# +-------------------------------+
# |                               |
# |   Standard Error Reporting    |
# |                               |
# +-------------------------------+
#

# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exception string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)


# This excpetion is used when when an error occurs relating to a list-directed
# IPL element.
#
# Instance Arguments:
#   msg     The nature of the error.  Defaults to an empty string
class LDIPLError(Exception):
    def __init__(self,msg=""):
        self.msg=msg     # Nature of the error.
        super().__init__(self.msg)

#
# +--------------------------------+
# |                                |
# |   List Directed IPL Objects    |
# |                                |
# +--------------------------------+
#

# An object representing a LDID core image file and its metedata from
# the control file.
#
# Access to the core image object embedded within the Core object are
# provided by four methods:
#    insert  - modify based upon position within the binary image object
#    update  - modify based upon loaded memory address
#    extract - examine based upon position withih the binary image object
#    inspect - examine based upon loaded memory address
#
# Two methods are provided for enabling and disabling moditifications:
#     mutable - enable modifications by insert or update.
#     immutable - disable modifications by insert or update.
#
# Instance Arguments:
#   filepath    satkutil.Path to the core image file.  If None the instance
#               is created without file path information.  Useful for
#               dynamically built instances without an existing LDID source.
#   load        The address at which the core image file is placed into
#               memory during the IPL function.  Defaults to 0.
#   ro          Marks the LDID core image file as read only.
class Core(object):

    def __init__(self,filepath,load=0,ro=False):
        assert isinstance(filepath,satkutil.Path) or filepath is None,\
            "%s 'filepath' argument must be a satkutil.Path object: %s"\
                % (satkutil.eloc(self,"__init__",module=this_module),filepath)
        assert isinstance(load,int) and load>=0,\
           "%s 'load' argument must be a non-negative integer: %s"\
                % (satkutil.eloc(self,"__init__",module=this_module),load)

        self.po=None                # file path is initialized to None
        self.fname=None             # File name with ext initialized to None
        if filepath:
            self.po=filepath              # satkutil.Path object
            # File name with ext of this file
            self.fname=self.po.filenamex
            # Region name (file name no extention)
            self.region_name=self.po.filename
        self.load=load              # The load address of the core image file
        self._image=None            # The binary core image of this Core file
        self.ro=ro                  # Whether image is read-only

    def __len__(self):
        if self._image is None:
            return 0
        return len(self._image)

    def __str__(self):
        return "Core Image - load:0x%X  length:%s (0x%X)  %s" \
            % (self.load,len(self),len(self),self.fname)

    # Return the control file statement for this core file
    def control(self,cdir=None):
        if self.po.isabs:
            path=self.po
        else:
            path=self.po.relative(cdir)

        return "%s 0x%X\n" % (path.filenamex,self.load)

    # Return a copy of the entire binary image as immutable or mutable \
    # bytes type list.
    def copy(self,mutable=False):
        if mutable and isinstance(self._image,bytes):
            return bytearray(self._image)
        if not mutable and isinstance(self._image,bytearray):
            return bytes(self._image)
        return self._image

    # Display the core image file encapsulated by this object
    # Method Argument:
    #   verbose   When False only the core image file path is displayed.  When
    #             True both the file path and the file's contents are
    #             displayed
    def display(self,verbose=False):
        msg="Core: %s" % self.po.filepath
        if verbose:
            print("%s%s" % ("\n",msg))
            self.dump()
        else:
            print(msg)

    # Generate a dump of the LDID region content
    def dump(self,mode=24,indent="",string=False):
        if self._image is None:
            s=""
        else:
            s=satkutil.dump(self._image,start=self.load,indent=indent)
        if string:
            return s
        print(s)

    # Extract a portion of the core image content.
    # Method Arguments:
    #   start    The beginning of the area being extracted based upon a
    #            position relative to zero.
    #   length   The length of the area being extracted.
    # Returns
    #   an immutable bytes sequence
    # Exceptions:
    #   AssertionError:
    #     1. Start is a negative integer, or
    #     2. Length is not a positive integer of at lease 1.
    #   ValueError:
    #     if the extracted area extended beyond the end of the image file.
    def extract(self,start,length):
        assert isinstance(start,int) and start >= 0,"'start' must be a non-"\
            "negative integer: %s" % start
        assert isinstance(length,int) and length > 0,"'length' must be a "\
            "positive integer: %s" % length

        end = start + length
        if end > len(self):
            raise ValueError("end of extraction as position %s, but image "\
                "length is %s" % (end,len(self)))

        extraction = self._image[start:end]
        #if isinstance(extraction,bytearray):
        #    extraction = bytes(extraction)
        return extraction

    def image(self,data):
        assert isinstance(data,(bytes,bytearray)) or data is None,\
            "%s 'data' argument must be a bytes sequence: %s" \
                 % (satkutil.eloc(self,"__init__",module=this_module),data)
        self._image=data

    # Make the core image object inmutable, that is, unable to be changed.
    # Methods insert() and update() are prohibited.
    def immutable(self):
        if isinstance(self.image,bytes):
            # Already is immutable
            return
        self.image(bytes(self._image))

    # Inserts binary content relative to zero as the start of the image object.
    # Method Arguments:
    #    start   position relative to zero where binary content is placed
    #            within the image.
    #    binary  A bytes-like sequence
    # Returns: None
    # Exception:
    #    ValueError if the binary content being inserted will not fit.
    #    AssertionError
    #       1. if the starting position is negative, or
    #       2. the binary content is not a bytes-like sequence, or
    #       3. the image object is not mutable
    def insert(self,start,binary):
        assert isinstance(start,int),"'start' argument must be non-negative: "\
            "%s" % start
        assert isinstance(binary,(bytes,bytearray)),"'binary' argument must "\
            "be a bytes-like sequence: %s" % binary
        assert isinstance(self._image,bytearray),"image object not mutable"

        try:
            end=start+len(binary)
            self._image[start:end]=binary
        except IndexError:
            raise ValueError("binary content ending position %s exceeds core "\
                "file length: %s" % (end,len(self))) from None

    # Inspect a given portion of the core image with a starting address
    # and length.
    # Method Arguments:
    #   address   The starting address of the area to be inspected.  The core
    #             image starting address is the same as its load address.
    #   length    The length of the area being inspected.
    # Returns:
    #   an immutable bytes sequence of the inspected area
    # Exceptions:
    #   AssertionError if address or length are not non-negative integers.
    #   ValueError if the area falls outside of the regions memory locations.
    def inspect(self,address,length):
        assert isinstance(address,int) and address >= 0,"'address' argument "\
            "must be a non-negative integer: %s" % address
        assert isinstance(length,int) and length > 0,"'length' argument must "\
            "be a positive integer greater than 0: %s" % length

        # Make sure the inspected area is contained within the object
        if address < self.load:
            raise ValueError("starting address (0x%X) precedes core "
                "image load address (0x%X)" % (address,self.load))
        end_address = address + length - 1
        end_core = self.load + len(self) - 1
        if end_address > end_core:
            raise valueError("ending address (0x%x) follows core image "
                "end address (0x%X)" % (end_address,end_core))

        relative_start = address-self.load
        return self.extract(relative_start,length)

    # Make core image object mutable.  Methods insert() and update() require
    # a mutuable core image object.
    def mutable(self):
        if isinstance(self._image,bytearray):
            # Image is already mutable
            return
        self.image(bytearray(self._image))

    def read(self):
        # Opens, reads, and closes the file
        binfile=satkutil.BinFile.read(self.po)
        # Extract binary image from satkutil.BinFile object
        self._image=binfile._binary

    # This method updates the core image object with binary data.  Data is
    # placed at the core image objects memory load address.
    # Method Arguments:
    #   address Address at which data starts to be updated.  The core image
    #           object is located at its load address through its load address
    #           plus length -1.
    #   binary  a bytes-like object that is placed within the core image object
    #           starting at the address argument.
    # Returns: None
    # Exceptions:
    #   AssertionError:
    #      1. address is negative
    #      2. binary is not a bytes-like sequence.
    #   ValueError if the binary content will not fit within the core image
    #              object based upon the binary object's length and its
    #              starting address
    def update(self,address,binary):
        assert isinstance(address,int) and address >= 0,"'address' argument "\
            "must be a non-negative integer: %s" % address
        assert isinstance(binary,(bytes,bytearray)),"'binary' argument must "\
            "be a bytes-like sequence object: %s" % binary

        # Make sure the binary object is contained within the object
        if address < self.load:
            raise ValueError("starting binary address (0x%X) precedes core "
                "image load address (0x%X)" % (address,self.load))
        end_address = address + len(binary) - 1
        end_core = self.load + len(self) - 1
        if end_address > end_core:
            raise valueError("ending binary address (0x%x) follows core image "
                "end address (0x%X)" % (end_address,end_core))

        # Update the image object
        relative_start = address-self.load
        self.insert(relative_start,binary)

    # Write the core image file content to the LDIPL directory, if the image file
    # is present.  This allows pre-existing image files to be directly used.
    def write(self,modname=None):
        if self._image is None or self.ro:
            return
        if modname is None:
            mod=this_module
        else:
            mod=modname

        binfile=satkutil.BinFile(filepath=self.po.filepath,data=self._image)
        print("%s Writing: %s" % (mod,binfile.po.filepath))
        binfile.write()


# This class reads or writes a LDID control file.
# Instance Arguments:
#    fo           The absolute or relative path of the control file
#    ldid         The absolute path to the LDID directory
#    comment      A comment placed as the first line of the control file
class Ctrl(object):

    def __init__(self,fo,ldid):
        self.fo=fo               # Control file open file object
        self.ldid=ldid           # Absolute path to the LDID

        # List of Core objects referenced by the control file.
        self._lines=[]  # List of control file lines
        self.cores=[]   # see parse() method
        self.files={}   # Cores accessed by control file filename.
        # Core objects accessed by region name (filename without an extension)
        self.regions={} # Updated when a new Core object is added when writing
        # For regions read from a LDID, use the Core.region_name attribute

    def __str__(self):
        return "LDIPL Control: images:%s  file: %s" \
            % (len(self.cores),self.po.filepath)

    # Builds the LDIPL directory contents including the this control file based
    # upon the current set of Core objects.  Comments may be placed preceding
    # or following control statements.
    def build(self):
        for c in self.cores:
            self._lines.append(c.control())

    # Adds one or more comment lines to the start of the control file.
    def comment(self,cmnt):
        self._lines.append(cmnt)

    # Add a new Core object to the control file
    # Method Arguments:
    #   filename   The file name of the core image file from the control file
    #              or the satkutil.Path object of the file name.
    #   load       The address at which the core file is to loaded.  Defaults
    #              to 0.
    #   data       Optional core image data.  Not required when reading
    #   ro         Mark core image file as read only when True.
    def core(self,filename,load=0,data=None,ro=False):
        assert isinstance(data,(bytes,bytearray)) or data is None,\
            "%s 'data' argument must be a bytes sequence: %s" \
                % (eloc(self,"core"),data)

        if isinstance(filename,str):
            fpath=satkutil.Path(filepath=filename)
        elif isinstance(filename,satkutil.Path):
            fpath=filepath
        else:
            raise ValueError(\
                "%s 'filepath' argument must be a string or satkutil.Path "\
                    "object: %s" % (satkutil.eloc(self,"core",\
                        module=this_module),filepath))

        if not fpath.isabs:
            fpath=fpath.absolute(self.ldid)

        try:
            self.files[filename]
            raise LDIPLError("duplicate file name encountered: %s" % filename)
        except KeyError:
            pass
        c=Core(fpath,load=load,ro=ro)
        c.image(data)
        self.cores.append(c)
        self.files[filename]=c          # filename mapped to Core object
        self.regions[fpath.filename]=c  # region name mapped to Core object
        # The region name is the filename without an extension

    def ctrl_write(self):
        if self.fo is None:
            # This occurs when Create(dryrun=True)
            return
        self.fo.writelines(self._lines)
        self.fo.close()

    # Print the contents of the LDID
    # Method Argument:
    #   verbose   When False only file paths are displayed.  When True file
    #             content is also displayed.
    def display(self,verbose=False):
        print("Control File: %s" % self.fo.name)
        if verbose:
            for n,line in enumerate(self._lines):
                print("[%s] %s" % (n,line))
        for c in self.cores:
            c.display(verbose=verbose)

    # Parse the statements in the control file into Core objects.
    # Method Argument:
    #   ro   Mark core image files read as read only if True.
    def parse(self,ro=False):
        for lineno,line in enumerate(self._lines):
            # Ignore empty or comment lines
            if len(line)==0 or line[0]=="#":
                continue

            # Remove a trailing comment from the statement
            try:
                ndx=line.index("#")
                parms=line[:ndx]
            except ValueError:
                parms=line

            # Remove any whitespace following the statement
            parms=parms.strip()

            # Split the statement into its two pieces: file path and load address
            pieces=parms.split()
            if len(pieces)!=2:
                raise LDIPLError(msg="%s - unrecognized LDIPL control file "\
                    "statement: %s\n[%s] %s" \
                        % (this_module,self.cfile,lineno+1,line))

            binfile=pieces[0]   # Identify the binary file in the statement
            absfile=satkutil.Path(binfile)
            absfile=absfile.absolute(self.ldid)

            # Process the load address
            address=pieces[1]
            if len(address)<=2 or address[:2]!="0x":
                raise LDIPLError(msg="%s - unrecognized LDIPL control file "
                    "address: %s\n[%s] %s" \
                        % (this_module,address,lineno+1,line))
            try:
                address=int(address[2:],16)
            except ValueError as ve:
                raise LDIPLError(msg=\
                    "%s - unrecognized hexadecimal address '%s': %s\n[%s] %s" \
                        % (this_module,address,ve,lineno+1,line)) from None

            # Add the Core object for this statement to the list of Core objects
            self.cores.append(Core(absfile,load=address,ro=ro))

    # Read the control file
    def read(self):
        lines=self.fo.readlines()
        for line in lines:
            if line[-1] == "\n":
                self._lines.append(line[:-1])
            else:
                self._lines.append(line)
        self.fo.close()

    # Retrieve the core image data of this control file
    def retrieve(self):
        for c in self.cores:
            c.read()

    # Writes the LDID to its directory, each binary file and control file
    def write(self,modname=None):
        if modname is None:
            mod=this_module
        else:
            mod=modname
        for c in self.cores:
            c.write(modname=mod)
        print("%s Writing: %s" % (mod,self.fo.name))
        self.ctrl_write()   # Write the control file

#
# +-----------------------------------------------+
# |                                               |
# |   List Directed IPL Directory Manipulation    |
# |                                               |
# +-----------------------------------------------+
#
# Access - supports access of an existing LDID's contents by reading it
# Create - supports creation of a new LDID's content and writing it

# This class "opens" a LDID and reads its content.  The control file is
# is opened and the identified binary content are built.
# The primary public method is read().  The read() method returns Ctrl object
# that contains the LDID binary content and its meta data from the control file.
# During instantiation, the LDID control file is opened and results in a
# file object used to access the control file.
#
# This class may be subclassed to provide additional functionality and
# ease of access by the user module.
#
# Instance Arguements:
#   filepath   The file name or path to the LDID control file
#   pathmgr    An optional satkutil.PathMgr instance use to locate the control
#              file.
# Instance Exceptions:
#   ValueError is raised if the LDID control file can not be opened for reading
class Access(object):
    def __init__(self,filepath,pathmgr=None):
        assert isinstance(pathmgr,satkutil.PathMgr) or pathmgr is None,\
            "'pathmgr' arguement must be a satkutil.PathMgr: %s" % pathmgr

        self.filepath=filepath      # Control file name or path
        self.pathmgr=pathmgr        # satkutil.PathMgr or None
        self.var="LDIDS"            # Search order environment variable name

        # These attributes are set by the _open() method
        self.ctlpath=None           # Absolute path of the LDID control file
        self.ldid=None              # Absolute path of the LDID
        self.ctl_fo=None            # Control file's open file object

        # Open the LDID control file
        if self.pathmgr:
            abspath,fo=self.pathmgr.ropen(\
                self.filepath,mode="rt",variable=self.var)
            # May raise value error.
            ctlpath=abspath
            ldid=satkutil.Path(filepath=abspath)
            ldid=ldid.directory   # Directory containing the control path
        else:
            path=satkutil.Path(filepath=self.filepath)
            # Convert filepath to an absolute path based upon cwd
            abspath=path.absolute()
            ctlpath=abspath.filepath
            try:
                fo=open(ctlpath,mode="rt")  # Open the control file
            except IOError as ie:
                raise ValueError("could not open %s for reading: %s" \
                    % (ctlpath,ie)) from None
            ldid=abspath.directory

        self.ctlpath=ctlpath # Ctrl file absolute path
        self.ldid=ldid       # Absolute path to the LDID containing control file
        self.ctl_fo=fo       # Control file open file object

        # Objects read by the read() method
        self.ctl=None      # Ctrl object used for reading or creating an LDID
        self.cores=[]      # List of Core object read

    # Display the contents of the LDID encapsulated by this object.
    # Method Argument:
    #   verbose   When False only file paths are displayed.  When True both
    #             file paths and file contents are displayed.
    def display(self,verbose=False):
        self.ctrl.display(verbose=verbose)

    # Read the control file and identified binary content.
    # Method Argument:
    #   ro   Marks core image object as read only if True.  Defaults to True.
    #        Marking a core image object as read only inhibits the Core
    #        object from being overwritten with different content.
    # Returns:
    #   a Ctrl object representing the LDID and its contents.
    # Exception:
    #   ValueError if file not readable
    def read(self,ro=True):
        self.ctrl=Ctrl(self.ctl_fo,self.ldid)
        self.ctrl.read()       # Read the control file
        self.ctrl.parse(ro=ro) # Parse the lines just read into Core objects
        self.ctrl.retrieve()   # Read the image content of the Core objects
        # Make Core objects accessable from this object.
        self.cores=self.ctrl.cores

    def write(self,filepath):
        raise NotImplementedError("write() method in class %s prohibited" \
            % self.__class__.__name__)


# This class builds from library objects and LDID and writes the created LDID
# to the file system.
# Instance Argument:
#   ctl_path     Path to the control file.  Defines the directory into which
#                the core image objects are written.
#   dryrun       Whether this execution of Create is a dryrun (does not write
#                to the LDID), True, or does actually create the LDID, False.
#                Defaults to False (creates the LDID).
# Exception:
#   IOError if control file can not be opened.
class Create(object):
    def __init__(self,ctl_path,dryrun=False):

        # Convert ctl_path to an absolute satkutil.Path object
        self.ctl_path=satkutil.Path(ctl_path).absolute()
        # Directory into which core files are written
        self.core_dir=self.ctl_path.directory
        # These two attributes dictate where files are written for the LDID

        self.cores=[]   # List of core image objecte being written to the LDID
        if dryrun:
            ctl_fo=None
        else:
            ctl_fo=open(self.ctl_path.filepath,mode="wt")
        self.ctrl=Ctrl(ctl_fo,self.core_dir)  # Ctrl object. See build() method

    # Adds an already constructed core image object to the LDID.  It extracts
    # from the Core object, the parts that can be immediately used.  An
    # alternative to the register() method
    # Method Arguments:
    #   filename   The name of the file to which the core is written
    #   core       The Core object being written to the new LDID
    def add(self,filename,core):
        assert isinstance(core,Core),"'core' argument must be a Core object: "\
            "%s" % core
        self.register(filemame,Core.load,Core._image)

    # Adds one or more comment lines at the start of the control file as
    # comments.  Comment lines must start with a pound sign (#).  If the
    # commment line does not start with a pound sign, one will be prepended.
    #
    # Only strings or list of strings are allowed.  Anything that is not
    # a string or list of strings is ignored.
    #
    # Comment lines will start with a "#" and end with "\n".  Either that is
    # missing will be supplied before writing the comment line
    #
    # Method Argument:
    #   comment   A single string or a list of strings.
    def comment(self,comment):
        if isinstance(comment,str):
            if len(comment)>0:
                # Make sure comment starts with a comment symbol
                if comment[0]!="#":
                    cmnt="# %s" % comment
                else:
                    cmnt=comment
                # Make sure comment ends with a \n
                if cmnt[0]!="\n":
                    cmnt="%s\n" % cmnt
            self.ctrl.comment(cmnt)
        elif isinstance(comment,list):
            for cmnt in comment:
                if not isinstance(cmnt,str):
                    continue
                if len(comment)>0:
                    if comment[0]!="#":
                        cmt="# %s" % cmnt
                    else:
                        cmt=cmnt
                    if cmt[-1]!="\n":
                        cmt="%s\n"
                self.ctrl.comment(cmt)

    # Access generated LDID control file.
    # Returns:
    #   a list of strings containing the generated control file statements.
    #   This method must be called AFTER the write() method.
    def control_file(self):
        lines=self.ctrl._lines
        assert isinstance(lines,list) and len(lines)>0,"LDID control file not "\
            "yet generated, call control_file() after write() method"
        return lines

    def read(self,ro=True):
        raise NotImplementedError("read() method in class %s prohibited" \
            % self.__class__.__name__)

    # Registers a core object content with the LDID to be built.
    # Method Arguments:
    #   filename   Filename plus extension of the core object.
    #              Ctrl object creates the full filepath from the information
    #              it has about the LDID.
    #   load       Load address of the core image content
    #   data       Bytes sequence of the core image content
    def register(self,filename,load,data):
        self.ctrl.core(filename,load=load,data=data)

    # Writes the LDID to the file system.
    def write(self,modname=None):
        if modname is None:
            mod=this_module
        else:
            mod=modname
        self.ctrl.build()   # Construct the control file statements
        self.ctrl.write(modname=mod)   # Write the files to the LDID
        # Method control_file may now be called.


# This is a wrapper class for the process of reading an existing LDIPL directory's
# content or creating new content for a new LDIPL directory.  It may be subclassed.
#
# NOTE: THIS CLASS IS BEING REPLACED BY THE Access AND Create CLASSES!!
#
# This class reads a LDID and creates
#
# Instance Arguments
#   ctlfile    The file name of path to the control file of this LDID
#   pathmgr    An satkutil.PathMgr object for assist in opening files
#   create     Whether creating a new LDID of not.
class LDIPLx(object):
    def __init__(self,ctlfile=None,pathmgr=None,create=False):
        self.ctlfile=ctlfile     # Path to the LDIPL directory's control file
        self.pathmgr=pathmgr     # Optional path manager
        self.create=create       # Whether creating a new LDID or not

        # Ctrl object of the directory's control file.  See read() method
        self.control=None

    # Create a new LDID
    def build(self):
        if not self.create:
            raise ValueError(LDIPLError(msg="object not configured to build "
                "a LDID"))
        self.control.build()

    def core(self,filepath,load=0,data=None,ro=False):
        assert isinstance(data,(bytes,bytearray)),\
            "%s 'data' argument must be a bytes sequence: %s" \
                % (eloc(self,"core"),data)

        if self.control is None:
            raise LDIPLError("%s control file not established" % eloc(self,"core"))
        self.control.core(filepath,load=load,data=data,ro=ro)

    def display(self,mode=24,indent="",string=False):
        s="\nLDIPL Control File: %s" % self.ctlfile
        s="%s\n%s\n" % (s,self.control.display(indent="    ",string=True))

        for c in self.control.cores:
            s="%s\nCore Image File: %s" % (s,c.po.filepath)
            s="%s\n%s\n" % (s,c.dump(mode=mode,indent="    ",string=True))

        if string:
            return s
        print(s)

    # Create a new LDIPL control file
    def new(self,ctlfile):
        if not self.create:
            raise ValueError(LDIPLError(msg="object not configured to create "
                "a new LDID"))
        self.control=Ctrl(filepath=ctlfile)
        self.ctlfile=ctlfile

    # Read an entire LDIPL directory
    def read(self,ctlfile=None):
        cfile=None
        if ctlfile is not None:
            self.ctlfile=cfile=ctlfile
        elif self.ctlfile is not None:
            cfile=self.ctlfile
        if cfile is None:
            raise LDIPLError("%s control file path unavailable" % eloc(self,"read"))

        self.control=Ctrl.read(cfile)  # Read and parse the control file
        self.control.retrieve()        # Retrieve core image binary files

    # Write the contents of the LDIPL directory
    def write(self):
        if not self.create:
            raise ValueError(LDIPLError(msg="object not configured to write "
                "to an LDID"))
        if self.control is None:
            raise LDIPLError("%s control file content unavailable"
                % eloc(self,"write"))

        self.control.write()


# This class is used to test the ldidlib module.  Not intended for production
# use.
class LDID_Tool(object):
    def __init__(self,args):
        self.args=args
        self.ld=None
        self.ctlfile=args.ctlfile[0]     # ctlfile
        self.verbose=args.verbose

    def _build_core_ld(self,ctlpath,corepath):
        assert isinstance(ctlpath,satkutil.Path),\
            "%s 'ctlpath' must be a satkutil.Path object: %s" \
                % (eloc(self,"_build_core_ld"),ctlpath)
        assert isinstance(corepath,satkutil.Path),\
            "%s 'corepath' must be a satkutil.Path object: %s" \
                % (eloc(self,"_build_core_ld"),corepath)

        # Read the core image binary file.
        image=satkutil.BinFile.read(corepath)
        image_data=image._binary
        load=self.args.load

        ld=LDIPL()
        ld.new(ctlpath)
        ld.core(corepath,load=self.sysload,data=image_data,ro=True)
        if load !=0 and len(image_data)>=8:
            psw_data=image_data[:8]
            psw_filename="%s_PSW.bin" % corepath.filename
            ld.core(psw_filename,load=0,data=psw_data)
        ld.build()
        return ld

    def run(self):
        evar="LDIDS"  # Environment variable used for control file access
        acc=Access(self.ctlfile,\
            pathmgr=satkutil.PathMgr(variable=evar),var=evar)
        acc.read()
        acc.display(verbose=self.verbose)


#
# +-----------------------------+
# |                             |
# |   Command-line Interface    |
# |                             |
# +-----------------------------+
#

def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,\
        epilog=copyright,\
        description="create an LDID from a binary image or the contents of "\
            "an existing LDIPL directory")

    # Source input file
    parser.add_argument("ctlfile",nargs=1,metavar="FILEPATH",\
        help="the path to the LDIPL control file being displayed or created")

    parser.add_argument("--core",metavar="FILEPATH",default=None,\
        help="the binary image file used to create the LDIPL directory")

    parser.add_argument("--dump",type=int,choices=[24,31,64],default=24,
        help="size of the core image dump address: 24, 31, or 64. Defaults to 24.")

    parser.add_argument("-v","--verbose",action="store_true",default=False,\
        help="enable detailed messages")

    return parser.parse_args()


if __name__ == "__main__":
    raise NotImplementedError("%s is intended for import only" % this_module)
    # Comment out the preceding statement to test the library.
    args=parse_args()
    print(copyright)
    LDID_Tool(args).run()
