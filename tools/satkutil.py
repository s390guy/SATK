#!/usr/bin/python3.3
# Copyright (C) 2013, 2014 Harold Grovesteen
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

# This module contains a set of useful functionality that does not easily fit 
# elsewhere.
#
# The mdoules includes the following classes:
#   dir_tree     Class useful in managing directory trees.
#   DM           A Debug Manager that interfaces with the argparse class.
#
# The module includes the following functions:
#   byte2str     Converts a bytes list or bytearray into a string without encoding
#   pythonpath   A function that allows management of the PYTHONPATH from within a
#                module.
#   satkroot     Determines the absolute path to the SATK root directory
# 

# Python imports
import os
import os.path
import sys

# SATK imports: none

# This class gathers directory and file lists recursively from within a root
# directory.  The class allows inclusion or exclusion of hidden files and 
# diretories, specific directory names or file suffixes.  A file name matching a 
# suffix is considered a match.  Tests for inclusion of files and directories take 
# precedence over tests for exclusion.
#
# For directories tests are performed in this sequence:
#
#   hidden directory test (match action determined by the 'hidden' argument)
#   include directory test (match includes the directory)
#   exclude directory test (match excludes the directory)
#
# For files tests are performed in this sequence:
#
#   hidden file test (match action determined by the 'hidden' argument)
#   include file test (match includes the file)
#   exclude file test (match excludes the file)
#
# Class instantiation arguments:
#   root    The root path upon which the dir_tree data is based.
#   hidden  Indicates whether hidden files should be excluded or not.  
#           Specify 'False' to include hidden files and directories.  
#           Specify 'True' to exclude hidden files and directories.  
#           Defaults to 'False', including hidden directories.
#   dirs    Specify the list of directories to be included and excluded.
#   files   Specify the list of file suffixes to be inclded and excluded.
#
# Both of the dirs and files lists are managed the same.
#   [None,None]      Indicates that all directories or file suffixes are included
#   [[list],None]    The list of directories or file suffixes included, all others
#                    are excluded
#   [None,[list]]    The list of directories or file suffixes excluded, all others
#                    are included
#   [[list1],[list2]]  List2 is ignored, treated as [[list1],None]
class dir_tree(object):
    def __init__(self,root,hidden=False,dirs=None,files=None):
        self.root=root
        self.hidden=hidden
        self.incdir=self.excdir=self.incfile=self.excfile=[]
        self.incdir,self.excdir=self._ckix_arg(dirs,"dirs")
        self.incfile,self.excfile=self._ckix_arg(files,"files")
        if len(self.excdir)>0 and len(self.incdir)>0:
            self.excdir=[]

        # These lists are built by self._recurse().
        self.dirs=[]
        self.files=[]
        self._recurse(self.root)
        
    def _ckix_arg(self,arg,name):
        if arg is None:
            return ([],[])
        if len(arg)!=2:
            raise ValueError("satkutil.py - dir_tree - %s requires a list of two "
                "elements: %s" % (name,arg))
        inlist=[]
        exlist=[]
        inc=arg[0]
        exc=arg[1]
        if inc is not None: 
            if isinstance(inc,list):
                inlist=inc
            else:
                raise ValueError("satkutil.py - dir_tree - %s requires first "
                    "element to be a list: %s" % (name,inc))

        if exc is not None:
            if isinstance(exc,list):
                exlist=exc
            else:
                raise ValueError("satkutil.py - dir_tree - %s requires second "
                    "element to be a list: %s" % (name,exc))
        
        if len(exlist)>0 and len(inlist)>0:
            exlist=[]
        return (inlist,exlist)
        
    # Parse the filter lists presented for directori
        
    # For a given directory, accumulate the list of its sub directories and files.
    # Return the two lists as a tuple.
    # Do not override this method.
    def _listdir(self,d):
        entries=os.listdir(d)
        dirpaths=[]
        filepaths=[]
        for x in entries:
            if self.hidden and self.hidden_test(x):
                continue
            path=os.path.join(d,x)
            if os.path.isdir(path):
                # Filter a directory
                if len(self.incdir)>0:
                    if self.filter_dirs(x,self.incdir,True):
                        dirpaths.append(path)
                    continue
                if len(self.excdir)>0 and self.filter_dirs(x,self.excdir,False):
                    continue
                dirpaths.append(path)
            else:
                # Filter a file
                if len(self.incfile)> 0:
                    if self.filter_files(x,self.incfile,True):
                        filepaths.append(path)
                    continue
                if len(self.excfile)>0 and self.filter_files(x,self.excfile,False):
                    continue
                filepaths.append(path)
        return (dirpaths,filepaths)
        
    # Populate the class attributes self.dirs and self.files with fully qualified
    # paths contained within the root directory.
    # Do not override this method.
    def _recurse(self,root):
        dirpaths,filepaths=self._listdir(root)
        self.dirs.extend(dirpaths)
        self.files.extend(filepaths)
        if len(dirpaths)>0:
            for x in dirpaths:
                self._recurse(x)

    # This method checks whether the directory name matches a name provided in the
    # list.
    # 
    # Method arguments:
    #    name    The directory name being filtered
    #    lst     the list used to recognize the filtered name
    #    include Specify 'True' is the directory in being included.  Specify 'False'
    #            if the directory is being excluded.  This argument is being 
    #            supplied for the benefit of a subclass that overrides this method.
    # Returns:
    #    True if the directory name is found in the list
    #    False if the directory name is not found in the list
    #
    # Override this method to change the directory filter algorithm
    def filter_dirs(self,name,lst,include):
        result=name in lst
        #print("checking '%s' in lst %s: %s" % (name,lst,result))
        return result

    # This method checks whether a file name matches a suffix provided in the list.
    # 
    # Method arguments:
    #    name    The file name being filtered
    #    lst     the list suffixes being recognized
    #    include Specify 'True' is the file in being included.  Specify 'False'
    #            if the file is being excluded.  This argument is being supplied
    #            for the benefit of a subclass that overrides this method.
    # Returns:
    #    True if the directory name is found in the list
    #    False if the directory name is not found in the list
    #
    # Override this method to change the directory filter algorithm
    def filter_files(self,name,lst,include):
        namel=len(name)
        for x in lst:
            namex=len(x)
            if namel<namex:
                return False
            suffix=name[-namex:]
            if suffix==x:
                #print("comparing '%s':'%s'" % (suffix,x))
                return True
        return False

    # This method takes a list and finds returns a list of duplicates when case
    # is ignored.
    def find_duplicates(self,lst):
        items=[]
        dups=[]
        for x in lst:
            y=x.lower()
            if not y in items:
                items.append(y)
            else:
                dups.append(x)
        return dups

    # Returns 'True' if a file or directory name is hidden.
    def hidden_test(self,name):
        if len(name)<1 or name[0]==".":
            return True
        return False

    # This method prints the found list of directories and files.  It also
    # provides an example of how to use the self.process() method.
    def print(self):
        print("\nDirectories:")
        self.process(self.print_entry,dirs=True)
        print("\nFiles:")
        self.process(self.print_entry,files=True)

    # Process method used by the print() method.
    def print_entry(self,path):
        print(path)

    # This method processes the lists.  The method arguments determine which lists
    # are processed.
    #   dirs    Indicate whether the directory list should be processed.  Specify
    #           'True' to process each directory with the process_dir() method.
    #           Defaults to 'False'.
    #   files   Indicate whether the selected list of files should processed.
    #           Specify 'True' to process each file path with the process_file()
    #           method.  Defaults to 'False'.
    def process(self,method,dirs=False,files=False):
        if dirs:
            for x in self.dirs:
                method(x)
        if files:
            for x in self.files:
                method(x)

#
# +-----------------+
# |                 |
# |  Debug Manager  |
# |                 |
# +-----------------+
#

# This class controls debug messaging and controls via argparse for the lanugage 
# system in particular, but for any application requiring such controls.
#   appl       Identifies application specific debug options as a list.  Defaults
#              to an empty list, [].
#   langutil   Identifies this application as a user of the langutil module by 
#              specifying True.   Specifying True implies the application also 
#              uses the LL1parser and lexer modules.
#   parser     Identifies this application as a user of the LL1parser module by
#              specifying True.  Specifying True implies the application is also
#              a user of the lexer module.
#   lexer      Identifies this application as a user of the lexer mdoule by
#              specifying True.
#   cmdline    This argument identifies the mulit-occurring command line argument
#              that enables a debugging option.
# 
# Instance methods:
#   add_argument Establishes the debug command line argument in an argparse parser
#   disable    Disables a previously defined debug option flag.
#   enable     Enables a previously defined debug option flag.
#   flag       Defines a specific string as a debug option flag.
#   init       Takes an argparse name space and set the flags based upon the 
#              values occurring in the command line for the command line argument
#              specified in the cmdline instance argument.
#   isdebug    Tests the current state of a defined debug flag.
#   print      Prints the current state of the defined debug option flags.
class DM(object):
    def __init__(self,appl=[],langutil=False,parser=False,lexer=False,\
                 cmdline="debug"):
        self.cmdline=cmdline       # Argparser command line argument
        self.flags={}              # Debug flags
         
        if isinstance(appl,list):
            a=appl
        elif isinstance(appl,str):
            a=[appl,]
        else:
            raise ValueError("satkutil - DM.__init__() - 'appl' must be a list or "
                "a string: %s" % appl)
            
        # Establish application specific debug options
        self.appl=a
        for x in self.appl:
            self.flag(x)
        
        # Langutil based application
        self.langutil=langutil
        
        # Parser based application
        if self.langutil:
            self.parser=True       # Langutil requires a parser
        else:
            self.parser=parser
        # Lexer based application
        if self.parser:
            self.lexer=True        # Parser requires a lexer
        else:
            self.lexer=lexer
        
        # Establish the language component debug option.
        if self.langutil:
            self.flag("kdebug")    # Display keyword types
        if self.lexer:
            self.flag("ldebug")    # Debug lexer processing
            self.flag("tdebug")    # Debug lexer Token type processing
        if self.parser:
            self.flag("cbtrace")   # Trace langutil call backs
            self.flag("pdebug")    # Parser debug flag
            self.flag("prdebug")   # Parser PRD debug flag
            self.flag("edebug")    # Parser error generation debug flag
            self.flag("gdebug")    # Grammar processing debug flag
            self.flag("gldebug")   # Grammar processing lexer debug flag
            self.flag("gtdebug")   # Grammar processing token debug flag
            self.flag("gLL1debug") # Granmar LL(1) analysis debug flag

    # Add a debug control argument to an argument parser.
    def add_argument(self,argparser,help=None):
        arg="--%s" % self.cmdline
        choose=[]
        for x in self.flags.keys():
            choose.append(x)
        choose=sorted(choose)
        argparser.add_argument(arg,action="append",choices=choose,default=[],help=help)

    # Disable a defined debug flag
    def disable(self,dflag):
        try:
            flag=self.flags[dflag]
        except KeyError:
            self.print()
            raise ValueError("%s.disable() - invalid debug flag: '%s'" \
                    % (self.__class__.__name__,x)) from None
        self.flags[dflag]=False
    
    # Enable a defined debug flag
    def enable(self,dflag):
        try:
            flag=self.flags[dflag]
        except KeyError:
            self.print()
            raise ValueError("%s.enable() - invalid debug flag: '%s'" \
                % (self.__class__.__name__,x)) from None
        self.flags[dflag]=True

    # Define a debug flag
    def flag(self,dflag):
        try:
            self.flags[dflag]
            raise ValueError("%s.flag() - debug flag already exists: '%s'" \
                % (self.__class__.__name__,dflag))
        except KeyError:
            self.flags[dflag]=False

    # From an argparse Namespace object extract and enable the requested debug
    # options.
    def init(self,args):
        dct=vars(args)
        debugs=dct[self.cmdline]
        for x in debugs:
            self.enable(x)

    # Test if a defined flag is enabled (returning True) or disabled (returning
    # False).
    def isdebug(self,dflag):
        try:
            return self.flags[dflag]
        except KeyError:
            self.print()
            raise ValueError("%s.isdebug() - invalid debug flag: '%s'" \
                % (self.__class__.__name__,dflag)) from None

    # Print the current state of the debug options.
    def print(self):
        string="DM setting:\n"
        keys=[]
        for x in self.flags.keys():
            keys.append(x)
        skeys=sorted(keys)
        for x in skeys:
            string="%s    %s=%s\n" % (string,x,self.flags[x])
        print(string[:-1])


#
# +-------------------------------------+
# |                                     |
# |  Path Environment Variable Manager  |
# |                                     |
# +-------------------------------------+
#

# This class manages paths environment variables for an applications opening
# files via search paths.  Path environment variables are registered with the
# class when instantiated or later using the path() method.  This class is designed
# to used for all paths, or individual instances may be used for a subset including
# one path.
#
# Instance arguments:
#    'variable'   A single string or list of strings identifying the supported
#                 environment variables.
class PathMgr(object):
    def __init__(self,variable=None,debug=False):
        self.debug=debug          # Enable debugging of all methods
        self.paths={}             # Dictionary of supported paths
        
        if variable is None:
            return
        elif isinstance(variable,list):
            for n in range(len(variable)):
                v=variable[n]
                if not isinstance(v,str):
                    clstr="satkutil.py - %s.__init__() -" % (self.__class__.__name__)
                    raise ValueError("%s 'variable' argument list element %s not a "
                        "string: %s" % (clsstr,n,v))
            vars=variable
        elif isinstance(variable,str):
            vars=[variable,]
        else:
            clstr="satkutil.py - %s.__init__() -" % (self.__class__.__name__)
            raise ValueError("%s 'variable' argument must be a list or str: %s" \
                % (clsstr,variable))
        
        for v in vars:
            self.path(v)

    # Registers an environment variable to be used for file search paths by the
    # application.
    #
    # Method arguments:
    #   variable    Environment variable string.
    #   debug       Specify True to enable debug message generation.
    def path(self,variable,debug=False):
        if not isinstance(variable,str):
            clsstr="satkutil.py - %s.path() -" % self.__class__.__name
            raise ValueError("%s 'variable' argument must be a string: %s" \
                % (clsstr,variable))

        ldebug=debug or self.debug
        pathlist=[]
        rawlist=[]
        try:
            path=os.environ[variable]
            if ldebug:
                print("satkuil.py - %s.path() - environment variable '%s': '%s'" \
                    % (self.__class__.__name__,variable,path))
            rawlist=path.split(os.pathsep)
        except KeyError:
            # Environment variable is not defined so ignore it
            if ldebug:
                print("satkutil.py - %s.path() - environment variable not "
                    "defined: '%s'" % (self.__class__.__name__,variable))
            

        #rawlist=path.split(os.pathsep)
        if ldebug:
            print("satkutil.py - %s.path() - path list: %s" \
                % (self.__class__.__name__,rawlist))

        for p in rawlist:
            pathlist.append(p.strip())
            
        # Add current working directory if not already in the path
        curwd=os.getcwd()
        if curwd not in pathlist:
            pathlist.append(curwd)
            
        # Register the recognized path
        self.paths[variable]=pathlist
        
    # Opens the file in the specified mode and returns the file object.  If supplied,
    # the predefined path variable is used to find the supplied relative path.
    # If an path variable is not supplied, or an absolute path is supplied, standard
    # Python processing occurs.
    #
    # Method arguments:
    #   filename    A path to a file to be opened. Required.
    #   mode        The mode in which the file is to be opened.  Defaults to "rt".
    #   variable    Recognized path environment variable string used to search for the 
    #               file.  Optional.  If not supplied, standard Python open processing
    #               applies.  The arguemnet string must have been defined when the
    #               class was instantiated (via the 'variable' argument or later
    #               added via the path() method.
    #   debug       Enable debug messages during the call.
    #
    # Returns the tuple:  (absolute_path, open_file_object)
    #   The absolute_path is the path that was used to successfully open the file.
    #   The open_file_object is ready to be used for file operations as allowed by
    #   the mode.
    #
    # Exceptions:
    #   ValueError  Raised if the file fails to open.  Note, this differs from normal
    #               file open processing that raises an IOError exception.  IOError
    #               exceptions are caught and not propagated upward.
    #
    def ropen(self,filename,mode="rt",variable=None,debug=False):
        ldebug=debug or self.debug

        # Try locating the path list to open the file.
        try:
            pathlist=self.paths[variable]
        except KeyError:
            pathlist=None
            if ldebug:
                clsstr="satkutil.py - %s.ropen() -" % (self.__class__.__name__)
                print("%s 'variable' argument not a defined path: '%s'" \
                    % (clsstr,variable))

        # For absolut paths or where a path variable name has not been supplied, or
        # the supplied variable is not recognized, default to Python's native behavior
        if os.path.isabs(filename) or variable is None or pathlist is None:
            try:
                return (filename,self.osopen(filename,mode,debug=ldebug))
            except IOError:
                raise ValueError("could not open in mode '%s' path: %s" \
                    % (mode,filename)) from None

        # Try using search path to open the relative path
        for p in pathlist:
            filepath=os.path.join(p,filename)
            try:
                return (filepath,self.osopen(filepath,mode,debug=ldebug))
                # on success, simply return the tuple (abspath,file_object)
            except IOError:
                continue

        raise ValueError("could not open in mode '%s' file '%s' with path: %s" \
            % (mode,filename,variable))
        
    def osopen(self,filename,mode,debug=False):
        if debug:
             print("satkutil.py - %s.osopen() - trying: open('%s','%s')" \
                   % (self.__class__.__name__,filename,mode))
        return open(filename,mode)

# This class accepts a string as its instance argument and will format the
# string for printing with line numbers.  It will either print the formatted
# text or return a string to allow it to be printed elsewhere.
#
# Instance Argument
#   text    A string object to be formatted and/or printed.
#
# Instance Methods:
#   cleanends   Removes whitespace from the end of the lines.
#   print       Formats the text for printing and either prints the formatted text
#               or returns the formatted text as a string.
class Text_Print(object):
    def __init__(self,text=""):
        if isinstance(text,list):
            self.lines=text
        elif isinstance(text,str):
            self.lines=text.splitlines()
        else:
            raise ValueError("satkutil.py - Text_Print.__init__() - 'text' "
                "argument not a list or string: %s" % text)
        
    # Remove whitespace at end of the text lines.  
    # Returns a list lines without trailing whitespace or a new string without
    # trailing whitespace.
    # 
    # Method argument:
    #    string     Specify 'True' to return a new string object of lines with
    #               trailing whitespace removed.  Specify 'False' to return a 
    #               list of lines from which trailing whitespace has been
    #               removed from each line.  Defaults to 'False'.
    def cleanends(self,string=False):
        new_lines=[]
        for line in self.lines:
            new_lines.append(line.rstrip())
        if string:
            return "\n".join(new_lines)
        return new_lines
        
    # Formats the text for printing with line numbers.
    # Method Argument:
    #    string    Specify 'True' to have the formatted text returned as a string.
    #              Specify 'False' to have the method do the printing itself.
    #              Defaults to 'False',
    def print(self,string=False):
        print_lines=self.cleanends()   # Clean up any trailing whitespace

        # Determine how big the line numbers are, allow space for '[',']' and ' ' 
        lines=len(print_lines)
        size=len("%s" % lines)+3

        s=""
        line_number=1
        for line in print_lines:
            number="[%s]" % line_number
            number=number.ljust(size)
            s="%s%s%s\n" % (s,number,line)
            line_number+=1
        if len(s)==0:
            s="[1]"       # If there were no lines pretend the first was empty
        else:
            s=s[:-1]      # Remove last '\n' in formatted string
        if string:
            return s      # string=True so just return the formatted text
        print(s)          # string=False so print the string here


# Convert a list of integers, bytes or bytesarray into a string independent of encoding
# If the integer value is greater
def byte2str(blist):
    if isinstance(blist,str):
        return blist
    if not isinstance(blist,list):
        bl=list(blist)
    else:
        bl=blist
    s=[]
    for n in range(len(bl)):
        c=bl[n]
        if c<0 or c>255:
            raise ValueError("list[%s] out of range (0-255): %s" % (n,c))
        s.append(chr(c))
    return "".join(s)


# For the supplied method object, returns a tuple: method's class name, method name)
def method_name(method):
    io=method.__self__   # Get the instance object from the method object 
    cls=io.__class__     # Get the class object from the instance object
    fo=method.__func__   # Get the function object from the method object
    return (cls.__name__,fo.__name__)


# Add a relative directory dynamically to the PYTHONPATH search path
def pythonpath(dir,debug=False):
    if os.path.isabs(dir):
        raise ValueError("satkutil.py - pythonpath() - 'dir' argument must be a "
            "relative path: '%s'" % dir)
    root=satkroot()
    if debug:
        print("satkutil.py - pythonpath() - SATK root: '%s'" % root)
    path=[os.path.join(root,dir),]
    if debug:
        print("satkutil.py - pythonpath() - adding path: '%s'" % path[0])
    path.extend(sys.path)
    sys.path=path
    if debug:
        print("satkutil.py - pythonpath() - sys.path=%s" % sys.path)


# Determine the SATK root directory from where this module resides.
def satkroot():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if __name__ == "__main__":
    raise NotImplementedError("satkutil.py - intended for import only")
