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

# As a command line executed script, the script provides repository inventory 
# creation for use by a Hercules Host Resource Access Facility based program.  
#
# Imported as a module, this script provides repository specification parsing and 
# repository inventory creation support.  The support is provided by subclassing
# the repository and or specstmt base classes.
#
# The information provided by the repository specification is specific to the 
# repository content.  The repository inventory merges information about the content
# with the repository-medium-specific data.  The repository and specstmt classes
# abstract the repository inventory creation process and content handling by a 
# specification statement, respectively.  Each class is intended to be a base class
# for subclasses that support a specific medium.  
#
# This module provides support for directly for use of the Hercules host file
# as a repository medium.  Access to the inventory and repository content requires
# use of the Hercules Resource Access facility.  It further illustrates how the base
# classes are utilized for inventory creation.
#
# A specstmt instance, or more specifically a specstmt subclass instance, must be
# created by the repository specification parse method of the repository base class.
# To ensure the parse method can create the instance, the signature of the __init__
# method of the subclass must not require any arguments.  All instance variables
# must be either explicitly set or established using properties.  This is true
# of specstmt subclass instances, too.  The subclass instance is created during
# repository specification parsing well before any medium specific repository 
# inventory data is available.
#
# Subclass Error Handling
# 
# Errors encountered while processing a specstmt instance should provide a message
# and set the error property to True.
#
# Errors encountered by repository subclass methods should increment the repository
# instance variable steperr.

# Python imports
import argparse             # command line argument parser
import os.path              # Access platform file system information
import re                   # Access the regular expression module
import sys
# SATK imports
from   hexdump import *     # Access hex dump utility methods/functions
from   translate import *   # Access EBCDIC/ASCII translation tables

def align(addr,align):
   return ((addr+align-1)//align)*align
   
def check_hex(string):
    if len(string)>2 and string[:2] == "0x":
        s = string[2:]
    else:
        s = string
    try:
        return int(s, 16)
    except ValueError:
        return None
   
class repository(object):
    namere = re.compile(r'[a-zA-Z_][\w_]{0,7}')
    
    @staticmethod
    def readspec(spec, script=""):
        # Utility function for reading repository specification file
        try:
            fo = open(spec,"rt")
        except IOError:
            print("%serror opening specification file for reading: %s" \
                % (script, spec))
            sys.exit(1)
        try:
            specfile = fo.read()
        except IOError:
            print("%serror reading specification file: %s" % (script, spec))
            sys.exit(1)
        try:
            fo.close()
        except IOError:
            print ("%serror closing specification file: %s" % (script, spec))
            sys.exit(1)
        return specfile

    def __init__(self,spec,absolute=False,start=0x10000,script=""):
        self.entry_size = 32      # The subclass can make this bigger
        self.absolute = absolute  # Use absolute paths in repository
        self.spec     = spec      # Repository specification file contents
        self.current  = start     # Current default load
        self.errors   = 0         # Number of specification statements with errors
        self.steperr  = 0         # Number of steps with errors
        self._statements = []     # List of specstmt subclass instances
        self._inv     = ""        # Built repository inventory
        self.script   = script    # Set error message prefix

    def _action(self, parm):
        p = parm.lower()
        if p == "branch":
            return "branch"
        if p == "call":
            return "call"
        if p == "load":
            return "load"
        return None
    def _check_parm(self, ckmethod, parmno, lineno, msg):
        p = self.parms[parmno]
        result = ckmethod(p)
        if result is None:
            print ("%s%s, line %s: %s" % (self.script, msg, lineno, p))
        else:
            self.attributes[parmno] = result
    def _file(self, parm):
        if os.path.isfile(parm):
            return os.path.abspath(parm)
        return None
    def _load(self, parm):
        if parm == "*":
            return "*"
        return check_hex(parm)
    def _name(self, parm):
        if repository.namere.match(parm):
            return parm
        return None

    def bootparm(self, text, line_no, script=""):
        parms = text[5:]
        parms = parms.strip()
        if len(parms)==0:
            print("%serror: $boot parameters missing, ignoring: %s" % line_no)
            return None
        parms = parms.split(None)
        parms = " ".join(parms)
        if len(parms)>31:
            print("%serror: $boot parms too long, '%s', length %s: %s" \
                % (script, parms, len(parms), line_no))
            return None
        parms + 31*" "
        parms = parms[:31]
        return bootparm(string=parms)
       
    def bootsparm(self, text, line_no, script=""):
        parms = text[6:]
        parms = parms.strip()
        if len(parms)==0:
            print("%serror: $boot parameters missing, ignoring: %s" % line_no)
            return None
        if parms[0]!='"' or parms[-1]!='"':
            print("%serror: $boots parameter string missing one or more enclosing "
                "double quotes: %s" % (script, line_no))
            return None
        parms=parms[1:-1]
        if len(parms)>31:
            print("%serror: $boots parameter too long, '%s', length %s: %s" \
                % (script, parms, len(parms), line_no))
            return None
        return bootparm(string=parms, boots=True)

    def inError(self):
        # Returns a value of True if any errors were encountered.
        return self.steperr!=0 or self.errors!=0
        
    def inventory(self, cls, strict=False, dryrun=False, display=False):
        # Returns the completed repository inventory.  This method must not be
        # overridden.  'cls' is the specstmt subclass used by the repository, 
        # instances of which will be provided by the subclass.
        #   'strict=True'  will terminate storing of data if errors occurred
        #   'dryrun=True'  will do everything except store the repository
        #   'display=True' will provide a hex dump of the inventory before saving
        #
        # The overall inventory creation process requires six steps to perform
        # Each step has been broken into individual methods, allowing a class
        # that implements a repository to control when each step is invoked.
        # Further, the creation of the repository is further shared between
        # the repository and specstmt base classes and their respecitve subclasses 
        # that provide medium specific support for the repository construction.
        # The subclass methods with an * are required to be supplied by the
        # subclass.
        #
        #                                 repository          specstmt
        #                              subclass method     subclass method
        self.step1(cls, strict)     #         init
        self.step2(strict, dryrun)  #                            store *
        self.step3(strict)          #         prep
        self.step4(strict)          #                            medium *
        self.step5(display)         #        finish
        self.step6(strict, dryrun)  #         store *
        
    def parse(self, cls, script=""):
        # This method parses the specification file returning a list of specstmt
        # subclass instances
        assert issubclass(cls, specstmt),"'cls' not a subclass of specstmt: %s" % cls
        current_load = self.current
        statements = []
        lines = self.spec.splitlines()
        for line_num in range(len(lines)):
            text = lines[line_num]
            comment_pos = text.find("#")
            if comment_pos != -1:
                text = text[:comment_pos]
            text = text.strip()   # Remove starting and trailing which space
            if len(text) == 0:
                # Ignore blank lines
                continue
                
            if len(text)>=6 and text[:6]=="$boots":
                bootp = self.bootsparm(text, line_num+1, script=script)
                if isinstance(bootp, bootparm):
                    statements.append(bootp)
                else:
                    self.errors+=1
                continue
                
            if len(text)>=5 and text[:5]=="$boot":
                bootp = self.bootparm(text, line_num+1, script=script)
                if isinstance(bootp, bootparm):
                    statements.append(bootp)
                else:
                    self.errors+=1
                continue
                
            self.parms = text.split(None, 4)
            if len(self.parms)>4:
                print("%serror: garbage at end of repository specification " \
                    "statement: %s - '%s'" \
                    % (self.script, line_num+1, self.parms[4]))
                continue
            if len(self.parms)<3:
                print("%serror: incomplete repository specification statement: %s" \
                    % (self.script, line_num+1))
                continue
                
            # attributes[0] = content name
            # attbitutes[1] = path
            # attributes[2] = default load location for content or "*"
            # attributes[3] = action
            self.attributes = [None,None,None,None]
            # Check for valid parameters
            self._check_parm(self._name, 0, line_num+1,\
                "invalid content name")
            self._check_parm(self._file, 1, line_num+1,\
                "content file does not exist")
            self._check_parm(self._load, 2, line_num+1,\
                "invalid content load location")
            if len(self.parms)==4:
                self._check_parm(self._action, 3, line_num+1, "invalid action")
            else:
                self.attributes[3]="noaction"
            self.error = False
            for x in self.attributes:
                if x is None:
                    self.error = True
            if self.error:
                self.errors+=1
                print("%serror statement ignored, line: %s" % (self.script, line_num+1))
                continue
                
            # Statement parameters are valid, build specstmt instance
            load = False
            enter = False
            
            stmt = cls()
            stmt.line = line_num
            stmt.name = self.attributes[0]
            
            stmt.size = os.path.getsize(self.attributes[1])
            
            if self.absolute:
                stmt.path = os.path.abspath(self.attributes[1])
            else:
                stmt.path = self.attributes[1]
                
            if self.attributes[2] == "*":
                stmt.loadpt = current_load
                stmt.current = True
            else:
                stmt.loadpt = self.attributes[2]
            current_load = align(stmt.loadpt+stmt.size,4096)
            
            if self.attributes[3] == "load":
                stmt.load = True
            if self.attributes[3] == "branch":
                stmt.enter = True
                stmt.call = False
                stmt.load = True
            if self.attributes[3] == "call":
                stmt.enter = True
                stmt.call = True
                stmt.load = True   
                
            statements.append(stmt)
        if len(statements)>0:
            statements[-1].last = True
        return statements

    def step1(self, cls, strict=False, script=""):
        # Step 1 - Parse the repository specification file
        self._statements = self.parse(cls, script=script)
        if len(self._statements)==0:
            print("%serror: no valid repository specification statements found" \
                % self.script)
            sys.exit(1)
        if self.errors!=0:
            if strict:
                print("%sprocessing terminated due to statements with errors: %s" \
                    % (self.script, self.errors))
                sys.exit(1)
            else:
                self.steperr+=1
                print("%swarning: statements with errors: %s"\
                    % (self.script, self.errors))
        self.init()
                
    def step2(self, strict=False, dryrun=False):
        # Step 2 - Store or process each statement and manage its content
        self.errors = 0
        for x in self._statements:
            if x.error:
                continue
            x.store(self, dryrun)
            if x.error:
                self.errors+=1
        if self.errors!=0:
            if strict:
                print("%sprocessing terminated due to content entries with errors: %s" \
                    % (self.script, self.errors))
                sys.exit(1)
            else:
                self.steperr+=1
                print("%swarning - content entries with errors: %s"\
                    % (self.script, self.errors))
                
    def step3(self, strict=False):
        # Step 3 - Pre-process individual statements for repository
        loadpt = self.current
        self.errors = 0
        self._statements = self.prep(self._statements)
        for x in self._statements:
            if x.error:
                self.errors+=1
            if isinstance(x, bootparm):
                continue  
            # Determine the load point
            if x.current:
                x.loadpt = loadpt
            else:
                loadpt = x.loadpt
            loadpt = ((loadpt+x.size+4095)//4096)*4096
        if self.errors!=0:
            if strict:
                print("%sprocessing terminated due to content entries with errors: %s" \
                    % (self.script, self.errors))
                sys.exit(1)
            else:
                self.steperr+=1
                print("%swarning: content entries with errors: %s"\
                    % (self.script, self.errors))

    def step4(self, strict=False):
        # Step 4 - Create the individual repository entries as a single string
        self._inv = ""
        self.errors = 0
        for x in self._statements:
            entry = x.inventory(self)
            assert len(entry)==self.entry_size,\
                "inventory entry must be %s bytes: %s" \
                % (self.entry_size, len(entry))
            if x.error:
                self.errors+=1
                continue
            self._inv = "%s%s" % (self._inv, entry)
        if self.errors!=0:
            if strict:
                print("%sprocessing terminated due to inventory errors: %s" \
                    % (self.script, self.errors))
                sys.exit(1)
            else:
                self.steperr+=1
                print("%swarning: inventory entries with errors: %s"\
                    % (self.script, self.errors))
                
    def step5(self, display=False):
        # Step 5 - Allow for medium specific changes to complete the inventory 
        self._inv = self.finish(self._inv, self._statements)
        if display:
            print("Repository Inventory:\n%s" % dump(self.inv,indent="    "))
            
    def step6(self, strict=False, dryrun=False):
        # Step 6 - Store the repository inventory on the medium
        if self.steperr!=0:
            if strict:
                print("%srepository processing terminated due to errors" 
                    % self.script)
                sys.exit(1) 
            else:
                print("%swarning - storing inventory with encountered errors" \
                    % self.script)
        if not dryrun:
            self.store(self._inv, self._statements)

    # The following methods may or must be overriden by the device specific
    # subclass.

    def init(self):
        # Initialize the repository subclass with subclass specific information
        # The subclass must provide the linkage to the device that will hold the
        # repository.  This method is intended to provide the opportunity to do so.
        #
        # This method is called by step1 after successfully parsing the repository
        # spectification file.
        return

    def prep(self, statements):
        # If the repository needs to globally process the entries before storing
        # this is the opportunity to do it.  This is in preparation for creating
        # the individual repository inventory entries.  The subclass must return
        # the prepared list of specstmt subclass instances.
        #
        # This method is called by step3
        return statements

    def finish(self, inventory, statements):
        # This method may be provided by a subclass.  This method provides the
        # completed specstmt subclass instances as a list in statements and the
        # binary form of the inventory to the subclass for final completion.
        # The subclass method must return the completed binary inventory as a 
        # string.
        #
        # This method is called by step5
        return inventory

    def store(self, inventory, statements):
        # Store the final inventory repository on the medium itself
        #
        # This method is called by step6
        raise NotImplementedError(\
            "class %s must provide store method: %s" % self.__class__.__name__)

class specstmt(object):
    zeros=8*"\x00"
    def __init__(self):
        self._dev_data   = 11*"\x00"  # Default medium specific data (all zeros)
        self._data       = 32*"\x00"  # Default entry data (all zeros)
        self._loadpt = None    # Content default load location
        self._name   = None    # Content name
        self._path   = None    # Content path
        self._size   = 0       # Content size in bytes
        self.line    = None    # Line number of specification statement
        self._error  = False   # Set to true if an error occurs during handling
        self._cur    = False   # Whether load point is explicit or current implied
        self._enter  = False   # Branch or call entry point (True/False)
        self._call   = False   # Call entry point (True/False, False implies branch)
        self._load   = False   # Content to be loaded
        self._last   = False   # default, this is not the last entry
        self._parm   = False   # set to True, indicates a boot parm entry
        #
        self.entry_data = ""   # File content to be stored
        
    def action(self,act):
        # Translate an action into flag settings
        if act == "load":
            self.load = True
            return
        if act == "branch":
            self.enter = True
            self.call = False
            return
        if act == "call":
            self.enter = True
            self.call = True
            return
        if act == None:
            self.load = False
            self.enter = False
            self.call = False
            return
        raise ValueError("unsupported repository statement action: %s" % act)
        
    def content(self, repo, script=""):
        # Reads the repository entry content for future storing into repository
        # Returns True is successful, False otherwise
        try:
            fo=open(self.path,"rb")
        except IOError:
            print("%serror: could not open for reading inventory "
                "entry content: %s" % (script,self.path))
            self.error = True
            return False
        try:
            self.entry_data=fo.read()
        except IOError:
            print("%serror: could not read inventory entry content: %s"\
                % (script, self.path))
            self.error = True
            return False
        try:
            fo.close()
        except IOError:
            print("%serror: could not close inventory entry content file: %s" \
                % (script, self,path))
            self.error = True
        self.size = len(self.entry_data)
        return True
        
    def display(self, indent=""):
        # Returns a string suitable for printing
        name = self.name+7*" "
        name = name[:8]
        if self.error:
            error_flag = "?"
        else:
            error_flag = " "
        if self.load:
            load_flag = "Y"
        else:
            load_flag = "N"
        if self.enter:
            enter_flag = "Y"
        else:
            enter_flag = "N"
        if self.call:
            call_flag = "Y"
        else:
            call_flag = "N"
        string = "%s%s %s LOAD=%s ENTER=%s CALL=%s Flags=%s\n" \
            "%sload @%s bytes %s path=%s" \
            % (indent, name, error_flag, load_flag, enter_flag, call_flag, \
            byteX(ord(self.data[31])), indent, fullwordX(self.loadpt), self.size, \
            self.path)
        return string
        
    def entry(self, indent=""):
        return dump(bytes(self.data),indent=indent)
        
    def inventory(self, repo):
        # This statement must not be overridden.  It generates a repository 
        # inventory entry as a 32-byte string.  It will call medium for the medium
        # specific data.
        assert isinstance(repo, repository),\
            "'repo' not a repository instance: %s" % repo

        dev_data=self.medium(repo)
        name = "%s%s" % (self.name, specstmt.zeros)
        name = name[:8]
        name = name.translate(A2E)

        load = dblwordb(self.loadpt)
        size = fullwordb(self.size)

        flags = 0
        if self.enter:
            flags |= 0x80
        if self.call:
            flags |= 0x40 
        if self.load:
            flags |= 0x20
        if self.current:
            flags |= 0x10
        if self.last:
            flags |= 0x01

        self.data = "%s%s%s%s%s" % (name, load, size, dev_data, chr(flags))
        return self.data
        
    def medium(self, repo):
        # This method must be supplied by the subclass to provides the 11 bytes of
        # medium specific data residing in bytes 20-30 of the repository inventory
        # entry.  The returned data must be a string, 11 bytes in length.
        raise NotImplementedError(\
            "class %s must provide medium method: medium" % self.__class__.__name__)
        
    def store(self, repo, dryrun=False):
        # This method must be supplied by the subclass to process the content for
        # inclusion into the storage medium.  Any content required for the medium
        # specific data must be preserved in the subclass instance for use by
        # the medium method that will format the data and deliver it for inclusion
        # into the inventory entry.  This method can also store the content on 
        # the storage medium.
        #   'dryrun=True' causes everything except actual storing to occur/
        raise NotImplementedError(\
            "class %s must provide store method: store" % self.__class__.__name__)

    @property
    def call(self):
        return self._call
    @call.setter
    def call(self, value):
        self._call = value

    @property
    def current(self):
        return self._cur
    @current.setter
    def current(self, value):
        self._cur = value

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, value):
        if len(value)!=32:
            raise ValueError("inventory data must be 32 bytes: %s" % len(value))
        self._data = value

    @property
    def dev_data(self):
        return self._dev_data
    @dev_data.setter
    def dev_data(self, value):
        if len(value)!=11:
            raise ValueError("medium data must be eleven bytes: %s" % len(value))
        self._dev_data = value

    @property
    def enter(self):
        return self._enter
    @enter.setter
    def enter(self, value):
        self._enter = value
        if self._enter:
            self._load = True

    @property
    def error(self):
        return self._error
    @error.setter
    def error(self, value):
        self._error = value

    @property
    def last(self):
        return self._last
    @last.setter
    def last(self, value):
        self._last = value

    @property
    def load(self):
        return self._load
    @load.setter
    def load(self, value):
        self._load = value
        if not self._load:
            self._enter = False
            self._call = False

    @property
    def loadpt(self):
        return self._loadpt
    @loadpt.setter
    def loadpt(self, value):
        self._loadpt = value

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, value):
        self._name = value

    @property
    def parm(self):
        return self._parm
    @parm.setter
    def parm(self, value):
        self._parm = value

    @property
    def path(self):
        return self._path
    @path.setter
    def path(self, value):
        self._path = value

    @property
    def size(self):
        return self._size
    @size.setter
    def size(self, value):
        self._size = value
    
class bootparm(specstmt):
    def __init__(self, string="", boots=False):
        super(bootparm,self).__init__()
        self.parm = True      # This is a parm entry
        self.string = string  # Here is the entry string data
        self.boots = boots    # This is a $boots entry (as opposed to a $boot entry)

    def display(self, indent=""):
        parm = self.data[:31]
        if self.boots:
            # Note: rstrip does not work on NULL's.  Have to do this manually
            for x in range(len(parm)):
                if parm[-1]!="\x00":
                    break
                parm = parm[:-1]
            stmt = "$boots"
        else:
            stmt = "$boot"
        string = "%s%s string='%s', Flags=%s" \
            % (indent, stmt, parm.translate(E2A), byteX(ord(self.data[31])))
        return string
    
    def inventory(self, repo):
        flags = 0x02
        if self.last:
            flags |= 0x01
        if self.boots:
            pad = 31*"\x00"
        else:
            pad = 31*" "
        data = self.string + pad
        data = data[:31]
        data = data.translate(A2E)
        data = data + chr(flags)
        self.data=data
        return self.data
        
    def store(self, repo, dryrun):
        repo.entries += 1
        return
    
class HRAFREPO(repository):
    # Host Resource Access Facility Repository
    def __init__(self,options):
        self.abs   = options.absolute    # Relative (False) or absolute paths (True)
        self.cur   = options.current     # Starting load location for content
        self.dry   = options.dryrun      # Inhibit creation of repository inventory
        self.inv   = options.inventory   # Output inventory file   
        self.spec  = options.repospec[0] # Input specification file
        self.strict= options.strict      # Fail with errors
        self.verb  = options.verbose     # Dump inventory or not
        self.paths = ""                  # List of paths
        
        specfile=repository.readspec(self.spec, script="repo.py: ")
        super(HRAFREPO, self).__init__(specfile,self.abs,self.cur,"repo.py: ")
    
    # Create the HRA Repository
    def create(self):
        super(HRAFREPO,self).inventory(HRAENTRY, strict=self.strict, \
            dryrun=self.dry, display=self.verb)
    # Add a path to the repository string list
    def addpath(self, path):
        self.paths="%s%s%s" % (self.paths, path, "\x00")
        
    #
    # Base class overrides
    #
    def finish(self, inventory, statements):
        # Add path strings to inventory
        # But, for now just return the repository
        topaths = len(statements)*32
        return inventory+self.paths
    
    def prep(self, statements):
        entrys = len(statements)*self.entry_size
        for x in statements:
            x.pathdisp += entrys
    
    # Save the HRA Repository in the file system
    def store(self, inventory, statements, dryrun=False):
        try:
            fo = open(self.inv,"wb")
        except IOError:
            print("repo.py - error opening repository inventory: %s" % self.inv)
            sys.exit(1)
        try:
            fo.write(inventory)
        except IOError:
            print("repo.py - error writing repository inventory: %s" % self.inv)
            sys.exit(1)
        try:
            fo.close()
        except IOError:
            print("repo.py - error closing repository inventory: %s" % self.inv)
            sys.exit(1)
       
class HRAENTRY(specstmt):
    def __init__(self):
        super(HRAENTRY, self).__init__()
        self.pathdisp = 0   # displacement from start of path strings to my path
    #
    # Base class overrides
    #
    # Sequence of method usage by base classes:
    #   Step 2 - HRAENTRY.store
    #   Step 3 - HRAFREPO.prep
    #   Step 4 - HRAENTRY.medium
    def medium(self, repo):
        # Return dummy data
        disp = fullwordb(self.pathdisp)
        return "%s%s" % (disp, 7*"\x00")
    def store(self, repo, dryrun=False):
        # This is where I process the path for the final inventory
        self.pathdisp = len(repo.paths)
        repo.addpath(self.path)
        return

# Command line argument parsing
def parse_arg_hex(string):
    value = check_hex(string)
    if value is None:
        msg = "'%s' is not a hexadecimal value" % string
        raise argparse.ArgumentTypeError(msg)
    return value
    
def parse_args():
    parser=argparse.ArgumentParser(prog="repo.py",
        description="creates Host Resource Access Facility repository")
    parser.add_argument("repospec",\
        help="input repository specification file",nargs=1)
    parser.add_argument("-i","--inventory",\
        help="output repository inventory",required=True)
    parser.add_argument("-a","--absolute",action="store_true",default=False,
        help="use absolute paths in repository")
    parser.add_argument("-c","--current",type=parse_arg_hex,default="0x10000",
        help="starting location of content loads")
    parser.add_argument("-d","--dryrun",action="store_true",default=False,
        help="does everything except creating the repository inventory")
    parser.add_argument("-s","--strict",action="store_true",default=False,
        help="repository inventory creation fails with any errors")
    parser.add_argument("-v","--verbose",action="store_true",default=False,
        help="provide hexadecimal dump of repository inventory")
    return parser.parse_args()   

if __name__=="__main__":
    HRAFREPO(parse_args()).create()
    