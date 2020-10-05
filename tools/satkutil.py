#!/usr/bin/python3
# Copyright (C) 2013-2017 Harold Grovesteen
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
# The module includes a group of classes for simple management of individual file
# content and useful generic functions:
#  Functions:
#
#  Classes:
#   File         The base class of the group
#   FileError    An exception for delivering error information related to the group.
#   BinFile      Manages binary file content as bytes sequence
#   TextFile     Manages text file content as a string
#   TextLines    Manages text file content as a list of strings.
# Note: none of these object are enabled for use of environment path strings.
#
# The mdoule includes the following individual classes:
#   dir_tree     Class useful in managing directory trees.
#   DTYPES       A class providing various mainframe device types for various
#                families of devices.
#   Path         Manages the parts of a path.
#   DM           A Debug Manager that interfaces with the argparse class.
#   PathMgr      Manages one or more environment variables each of which defines
#                a directory search order using the native platforms path
#                conventions for locating relative paths to files, opening the file
#                when found.
#   Text_Print   Simple utility for printing multiple lines of text with line
#                numbers.
#
# The module includes the following functions:
#   byte2str     Converts a bytes list or bytearray into a string without encoding
#   eloc         Standardizes reporting of error locations
#   pythonpath   A function that allows management of the PYTHONPATH from within a
#                module.
#   satkdir      Determines the absolute path to an SATK directory
#   satkroot     Determines the absolute path to the SATK root directory
#

this_module="satkutil.py"

# Python imports
import os
import os.path
import re
import sys

# SATK imports: none


#
# +----------------------------+
# |                            |
# |   File Management Tools    |
# |                            |
# +----------------------------+
#


# Return an absolute path
# Method Argument:
#   filepath   a relative or absolute file path
# Returns
#   an absolute path relative to the current working directory or
#   for an absolute path, simply returns it unchanged.

def abspath(filepath):
    if os.path.isabs(filepath):
        return filepath
    return os.path.abspath(filepath)


# Query the operating system whether a file path exists.
def file_exists(filepath):
    assert isinstance(filepath,str) and len(filepath)>0,\
        "%s File.exists() - 'filepath' argument must be a non-empty string: %s" \
            % (this_module,filepath)

    return os.path.isfile(filepath)


# Read a binary or text file.
# Function Argument:
#   filepath   a non-empty string of file's path being opened for reading
#   binary     Whether a text file (False) or a binary (True) file is being read.
# Returns:
#   a string from a text file or bytes sequence from a binary file's contents.
# Exception:
#   FileError if an error occurs during reading of the file.

def file_read(filepath,binary=False):
    assert isinstance(filepath,str) and len(filepath)>0,\
        "%s File.file_read() - 'filepath' argument must be a non-empty string: %s" \
             % (this_module,filepath)

    if binary:
        fmode="rb"
        mode="binary"
    else:
        fmode="rt"
        mode="text"

    try:
        action="opening"
        fo=open(filepath,fmode)
        action="reading"
        data=fo.read()
        action="closing"
        fo.close()
    except IOError as ioe:
        raise FileError(msg="I/O error while %s %s file '%s'\n%s   " \
            % (action,mode,filepath,ioe))

    return data


# Write a file's contents.  If the file already exists it is truncated before
# writing occurs.
# Function Arguments:
#   filepath   the path to the file whose contents are being written
#   data       A string or bytes sequence.  A string causes a text file to be
#              written.  A bytes sequence causes a binary file to be written.
# Exeption:
#   FileError if a problem occurs during writing of the content

def file_write(filepath,data):
    assert isinstance(filepath,str) and len(filepath)>0,\
        "%s File.file_write() - 'filepath' argument must be a non-empty string: %s" \
            % (this_module,filepath)

    if isinstance(data,str):
        fmode="wt"
        mode="text"
    elif isinstance(data,(bytes,bytearray)):
        fmode="wb"
        mode="binary"
    else:
        raise ValueError(\
            "%s - file_write() - 'data' argument must be a string "\
                "or bytes sequence: %s" % (this_module,data))

    try:
        action="opening"
        fo=open(filepath,fmode)
        action="writing"
        fo.write(data)
        action="closing"
        fo.close()
    except IOError as ioe:
        raise FileError(msg="I/O error while %s %s file '%s'\n%s   " \
           % (action,mode,filepath,ioe))

# Joins together a directory and file name and an optional extension into a
# complete file path inserting path separator between the directory and
# filename.
# Method Arguments:
#   directory  a string of the directory, absolute or relative
#   filename   the file name with or without an extension
#   ext        the file name's extenstion if not part of the filenamt.
#              Defaults to an empty string.  ext should default of the file
#              name already contains the extension.
# Returns:
#   the complete path as a string

def path_join(directory,filename,ext=""):
    if len(ext)>0:
        if ext[0]==os.extsep:
            the_file="%s%s" % (filename,ext)
        else:
            the_file="%s%s%s" % (filename,os.extsep,ext)
    else:
        the_file=filename
    return os.path.join(directory,the_file)


# Separates the file's path into its constituent parts and returns them as
# a tuple.
# Function Arguments:
#   filepath  the path being separated
#   ext       Whether a file name extension is separated (True) or not (False).
#             Defaults to False
# Returns a tuple of two elements (
#   tuple[0]  the directory of the file
#   tuple[1]  the name of the file without the extension
# If ext=True:
#   tuple[2]  the extention beginning with a dot or empty if it does not exist

def path_sep(filepath,ext=False):
    directory,filename=os.path.split(filepath)
    if ext:
        filename,ext=os.path.splitext(filename)
        return (directory,filename,ext)
    return (diretory,filename)


# This object represents a generic file independent of its contents.  A subclass
# of this object manages the actual content.  Only subclasses of File may be
# directly instantiated.
#
# The static methods may be used without instantiating the object.
#
# Instance Arguments:
#   filepath   A string of the path to the file's content
class File(object):

    # Separates the file's path into its constituent parts and returns them as
    # a tuple:
    #   tuple[0]  the directory of the file
    #   tuple[1]  the name of the file without the extension
    #   tuple[2]  the extention beginning with a dot or empty if it does not exist
    #@staticmethod
    #def path_sep(filepath):
    #    directory,filename=os.path.split(filepath)
    #    filename,ext=os.path.splitext(filename)
    #    return (directory,filename,ext)

    @classmethod
    def _ck_path(cls,path):
        if isinstance(path,Path):
            return path
        if isinstance(path,str):
            assert len(path)>0,\
                "%s - %s._ck_path() - 'path' argument must not be an empty string" \
                    % (this_module,cls.__name__)
        else:
            raise ValueError(\
                "%s - %s._ck_path() - 'path' argument must be a string or "\
                    "Path object: %s" % (this_module,cls.__name__),path)

        return Path(filepath=path)


    # Read a file and return the file's content as a subclass object of File
    # This method must be called from a subclass that manages the file content.
    @classmethod
    def read(cls,filepath,binary=False):
        path=File._ck_path(filepath)
        path=path.absolute()
        data=file_read(path.filepath,binary=binary)
        return cls(filepath=path,data=data)

    def __init__(self,filepath):
        if filepath is None:
            self.po=None
        else:
            self.po=self.__class__._ck_path(filepath)

    def append(self,line):
        raise NotImplementedError("%s class %s does not suppor the append method()"\
            % (eloc(self,"append"),self.__class__.__name__))

    # Determines whether the current file path exists as a file.
    # Returns:
    #   False if the current file path does not exist (as a file)
    #   None if the current file path is None
    #   True if the current file past does exist.
    # Note: Within a Python if statement, None is treated as False.
    def exists(self):
        return self.po.exists()

    # Write data to the current file path
    # Method Argument:
    #   data   string of the data being written to the file
    # Exception:
    #   FileError if the file's path is unavailable or an error occurs during
    #              writing.
    def write(self,data):
        file_write(self.po.filepath,data)


# This excpetion is used when an error occurs relating to a file management
# operation.
#
# Instance Arguments:
#   msg     The nature of the error.  Defaults to an empty string
class FileError(Exception):
    def __init__(self,msg=""):
        self.msg=msg     # Nature of the error.
        super().__init__(self.msg)


# This class manages a binary file as a list of binary bytes.
class BinFile(File):

    # Read a binary file and retun a BinFile object of the file's content
    @classmethod
    def read(cls,filepath):
        return super().read(filepath,binary=True)

    # Create an object representing a binary file.
    # Method Arguments:
    #   filepath   The path to the binary content.  Defaults to None.
    #   data       The binary content of the file represented by this object.
    #              Must be a bytes sequence or None.
    def __init__(self,filepath=None,data=None):
        assert isinstance(data,(bytes,bytearray)) or data is None,\
            "%s 'data' argument must be bytes sequence: %s" \
                % (eloc(self,"__init__"),data)

        super().__init__(filepath)
        self._binary=data

    # Print or return as a string the binary content in dump format.
    # Method Arguments:
    #   indent   a string that is the indent of each dump line.  Defaults to "".
    #   string   returns the formatted dump as a string (True) or prints the
    #            formatted dump (False)
    # Returns:
    #   if string=True returns formatted dump as a string
    #   if string=False returns None after printing the formatted dump
    def display(self,indent="",string=False):
        str_data=dump(self._binary,indent=indent)
        if string:
            return str_data
        print(str_data)

    # Writes the binary contents to the file.  If the current content is None,
    # the file is truncated with nothing being written to it.
    # Method Argument:
    #   filepath   Change the current file path of this object to this path forcing
    #              this object to write the content to this new path rather than
    #              the path from which the file was read.
    def write(self,filepath=None):
        if filepath is not None:
            self.po=self.__class__._ck_path(filepath)
        if self._binary is None:
            data=bytes()
        else:
            data=self._binary
        super().write(data)


# This class manages a text file a single string with embedded line ends
class TextFile(File):

    # Read a text file and retun a TextFile object of the file's content
    @classmethod
    def read(cls,filepath):
        return super().read(filepath,binary=False)

    def __init__(self,filepath=None,data=None):
        assert isinstance(data,str) or data is None,\
            "%s 'data' argument must be a string: %s" % (eloc(self,"__init__"),data)

        super().__init__(filepath)
        self._text=data         # Text file data as string

    # Print the text or return the file content without formating.
    # Method Argument:
    #   string   Return the file content string (True) or print the file content
    #            (False).  Defaults to False.
    # Returns:
    #   if string=True returns the text file content without formatting
    #   if string=False returns None after printing the file content without
    #   formatting.
    def display(self,string=False):
        if string:
            return self._text
        print(self._text)

    # Write a text file.  If the file already exists, the file is truncated before
    # writing begins.
    # Method Argument:
    #   filepath   the file's path to which the contents of the text file are
    #              written.
    def write(self,filepath=None):
        if filepath is not None:
            self.po=self.__class__._ck_path(filepath)
        if self._text is None:
            data=""
        else:
            data=self._text
        super().write(data)


# This class manages a text file as a list of lines without line ends.
class TextLines(TextFile):

    # This method converts a list of strings into a single string where each string
    # element contains a line end.  This method
    # Method Arguments:
    #   lst   the list of strings being joined with line ends
    #   strip Remove trailing white space (True) or not (False) before joining the
    #         strings in the list.  Defaults to False
    #   end   Ensure the last line has a line end (True) or not (False).  Defaults
    #         to False.
    # Returns
    #   a single string composed of the joined elements of the list.
    @staticmethod
    def list2str(lst,strip=False,end=False):
        if strip:
            str_list=[]
            for l in lst:
                str_list.append(l.rstrip())
        else:
            str_list=lst
        string="\n".join(str_list)
        if end and string[-1] != "\n":
            string=string+"\n"
        return string

    # Converts a string into a list of individual lines without line ends
    # Method Arguments:
    #   string   the string being split
    #   strip    Whether to remove trailing white space (True) or not (False) from.
    #            each line.  Defaults to False.
    @staticmethod
    def str2list(string,strip=False):
        assert isinstance(string,str),\
            "%s - TextFile.str2list() - 'string' argument must be a string: %s" \
                % (this_module.data)

        # Split text into a list of strings without line ends
        lst=string.splitlines()

        if strip:
            strip_list=[]
            for l in lst:
                strip_list.append(l.rstrip())
            return strip_list
        return lst

    # Read a text file and retun a TextLines object of the file's content
    @classmethod
    def read(cls,filepath):
        return super().read(filepath)

    def __init__(self,filepath=None,data=None):
        assert isinstance(data,str) or data is None,\
            "%s 'data' argument must be a string: %s" % (eloc(self,"__init__"),data)

        super().__init__(filepath=filepath,data=data)
        self._lines=[]          # Text file lines as a list of lines
        if self._text is not None:
            self._lines=TextLines.str2list(self._text)

    def append(self,line):
        if isinstance(line,str):
            if len(line)==0:
                lst=["",]
            else:
                lst=TextLines.str2list(line)
        elif isinstance(line,list):
            lst=line
        else:
            raise ValueError("%s 'line' argument unexpected: %s" \
                % (eloc(self,"append"),line))
        self._lines.extend(lst)

    # Convert the lines into a numbered sequence of lines and joined as strings
    # Method Arguments:
    #   indent    A string represeting the amount of indent of the line.
    #             Defaults to "".
    #   string    Whether to return the numbered list as a string (True) or to
    #             print the string (False).  Defaults to False.
    # Returns:
    #   If string=True, the numbered lines as a string of
    #   if string=False, None after printing the lints
    def display(self,indent="",string=False):
        to=Text_Print(self._lines)
        str_data=to.print(indent=indent,string=True)
        if string:
            return str_data
        print(str_data)

    def write(self,filepath=None):
        if filepath is not None:
            self.po=self.__class__._ck_path(filepath)
        self._text=TextLines.list2str(self._lines,strip=True,end=True)
        super().write()


#
# +------------------------------+
# |                              |
# |  Useful Individual Classes   |
# |                              |
# +------------------------------+
#

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

    # Build command-line or configuration argument options and help
    # Returns:
    #   a tuple   tuple[0]  a list of choices for debugging
    #             tuple[1]  a help string
    def build_arg(self,help=None):
        choose=[]
        for x in self.flags.keys():
            choose.append(x)
        choose=sorted(choose)
        # build the help
        if help:
            help_str=help
        else:
            help_str="enable debugging output. Multiple occurences supported. " \
                "Available options:"
            for opt in choose:
                help_str="%s %s," % (help_str,opt)
            help_str=help_str[:-1]
        return (choose,help_str)


    # Add a debug control argument to an argument parser.
    # Method arguments:
    #   argparser   An instance of argparse.ArgumentParser to which debug options
    #               are being added.
    #   arg         The command-line argument.
    def add_argument(self,argparser,arg,help=None):
        choose,help_str = self.build_arg(help=help)
        argparser.add_argument(arg,action="append",metavar="OPTION",choices=choose,\
            default=[],help=help_str)

    # Build command-line or configuration argument options and help
    # Returns:
    #   a tuple   tuple[0]  a list of choices for debugging
    #             tuple[1]  a help string
    def build_arg(self,help=None):
        choose=[]
        for x in self.flags.keys():
            choose.append(x)
        choose=sorted(choose)
        # build the help
        if help:
            help_str=help
        else:
            help_str="enable debugging output. Multiple occurences supported. " \
                "Available options:"
            for opt in choose:
                help_str="%s %s," % (help_str,opt)
            help_str=help_str[:-1]
        return (choose,help_str)

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
# +----------------------------------+
# |                                  |
# |  Mainframe Device Type Manager   |
# |                                  |
# +----------------------------------+
#

# This class encapsulates mainframe device types for a number of families of devices.
# No instance arguments are required.
class DTYPES(object):
    def __init__(self):
        self.types={}
        self.families=[]
        self.dtype("CON","3215-C",["1052","3215","1052-C","3215-C","3270"])
        self.dtype("CKD","3330",\
            ["2306","2311","2314","3330","3340","3350","3380","3390","9345"])
        self.dtype("FBA","3310",\
            ["0671","0671-04","3310","3370","3370-2","9332","9332-600","9313",\
            "9335","9336","9336-20"])
        self.dtype("GRAF","3270",["3270",])
        self.dtype("PRT","1403",["1403","3211"])
        self.dtype("PUN","2525",["2525",])
        self.dtype("RDR","2501",["1442","2501","3505"])
        self.dtype("TAPE","3420",
            ["3410","3420","3422","3430","3480","3490","3590","8809","8347"])

    # Return a tuple for a device type family:
    #   tupple[0]  The default device model for the family, a string
    #   tupple[1]  A list of all device models supported by the family, a list of
    #              strings.
    def __getitem__(self,family):
        return self.types[family]

    # Define an alias family name for an existing family
    def alias(self,new_name,old_name):
        try:
            fam=self[new_name]
            raise ValueError(\
                "%s - %s.alias() - device family already defined: %s" \
                    % (this_module,self.__class__.__name__,new_name))
        except KeyError:
            self.types[new_name]=self[old_name]

    # Returns the default device type of a family
    # Returns:
    #   a string of the family's default device type
    # Exception:
    #   KeyError if the family name is unrecognized
    def default(self,family):
        dft,lst=self.types[family]
        return dft

    # Define device numbers and a default for a family of devices.
    # Allows creation of a new family of devices.
    # Method Arguments:
    #   family   a string defining the name of the family being defined
    #   default  the device type of the family's default device type.  Can be None.
    #   devices  a list of strings defining the device types belonging to the
    #            family.
    def dtype(self,family,default,devices):
        try:
            fam=self.types[family]
            raise ValueError("%s - %s.dtype() - device family already defined: %s" \
                % (this_module,self.__class__.__name__,family))
        except KeyError:
            self.types[family]=(default,devices)
            self.families.append(family)

    # Identify the device type family in which a device type belongs.
    # Note: alias names are not recognized by this process, only base family names.
    # Method Argument:
    #   dtype   A string of the device type being recognized
    # Returns:
    #   a string of the device type's family name
    # Exceptions:
    #   KeyError if device type can not be located
    def family(self,dtype):
        for f in self.families:
            default,lst=self.types[f]
            if dtype in lst:
                return f
        # Device type not in any family, so raise KeyError
        raise KeyError

    # Returns a list of a family's recognized device types
    # Returns:
    #   a list of strings.  Each string is a recognized device type
    # Exception:
    #   KeyError if the family name is unrecognized
    def types(self,family):
        dft,lst=self.types[family]
        return lst


#
# +------------------------------------+
# |                                    |
# |   Generic Path Part Manipulation   |
# |                                    |
# +------------------------------------+
#

# Manages parts of a file path
# The Path class may be used to breakdown a complete absolute or relative path
# into its consituent parts by using:
#   Path(filepath=the_path)
# or from a set of parts, create a full absolute or relative path by using:
#   Path(directory=dir,filename=name,ext=extension)
class Path(object):
    def __init__(self,filepath=None,directory=None,filename=None,ext=None):
        self.filepath=None       # The full file path
        self.directory=None      # The directory part of the file path
        self.filename=None       # The file name without an extension
        self.filenamex=None      # The file name with an extension
        self.ext=None            # The file's extension

        # Whether the path is absolute (True) or relative (False)
        self.isabs=None

        if filepath:
            self.isabs=os.path.isabs(filepath)
            self.filepath=filepath
            self.directory,self.filenamex=os.path.split(filepath)
            self.filename,self.ext=os.path.splitext(self.filenamex)
            return

        assert filename is not None,\
            "%s 'filename' argument is required when filepath is ommtted" \
                % eloc(self,"__init__")

        try:
            filename.index(os.extsep)
            assert ext is None,\
                "%s 'filename' argument with an extension may not exist with 'ext'"\
                " argument" % eloc(self,"__init__")
            self.filename,self.ext=os.path.splitext(self.filename)
            self.filenamex=filename
        except ValueError:
            # Extension is not present
            self.filename=filename
            self.ext=ext
            if ext:
                self.filenamex="%s%s%s" % (filename,os.extsep,ext)
            else:
                self.filenamex=filename

        if directory:
            self.filepath=os.path.join(directory,self.filenamex)
        else:
            self.filepath=self.filenamex

        self.isabs=os.path.isabs(self.filepath)

    def __str__(self):
        return "Path - %s - dir:%s  file:%s  ext:%s" \
            % (self.filepath,self.directory,self.filename,self.ext)

    # Make this relative path absolute or return the already absolute path
    # Method Argument:
    #   reldir   the absolute directory path to which this relative path is made
    #            absolute.
    # Returns:
    #   If this path is already absolute, returns self,
    #   otherwise, a Path object for the created absolute path is returned
    def absolute(self,reldir=None):
        if self.isabs:
            return self
        if reldir is None or reldir=="":
            d=os.getcwd()
        else:
            assert isinstance(reldir,str),\
                "%s 'reldir' argument must be a non-empty string: %s" \
                    % (eloc(self,"absolute"),reldir)
            assert os.path.isabs(reldir),\
                "%s 'reldir' argument must be an absolute path: %s" \
                    % (eloc(self,"absolute"),reldir)
            d=reldir
        abspath=os.path.join(d,self.filepath)
        return Path(filepath=abspath)

    def exists(self):
        return file_exists(self.filepath)

    # Convert this absolute path into a path relative to another absolute path
    # Method Argument:
    #   reldir    the absolute path
    # Returns:
    #   the Path object for the recognized relative path
    # Exception:
    #   ValueError if this path is not absolute or relative to the supplied path
    def relative(self,reldir):
        assert isinstance(reldir,str) and len(reldir)>0,\
            "%s 'reldir' arbument must be a non-empty string: %s" \
                % (eloc(self,"relative"),reldir)
        assert os.path.isabs(reldir),\
            "%s 'reldir' argument must be an absolute path: %s" \
                % (eloc(self,"relative"),reldir)
        if not self.isabs:
            raise ValueError("%s file path must be absolute: %s" \
                % (eloc(self,"relative"),self.filepath))

        common=os.path.commonprefix(reldir,self.filepath)
        if common != self.filepath[:len(common)]:
            raise ValueError("%s this path is not relative to:\n    %s\n    %s" \
                % (eloc(self,"relative"),self.filepath,reldir))
        relpath=self.filepath[len(common)+1:]
        return Path(filepath=relpath)


#
# +-------------------------------------------------------------+
# |                                                             |
# |   File/Path Manager with Environment Variable Replacement   |
# |                                                             |
# +-------------------------------------------------------------+
#

# This class performs environment variable replacement within a string.  Environment
# variables are initiated with '${' and terminated by '}' similar to some scripting
# tools.  If the environment variable is not found, it is replaced by an empty
# string.
#
# Instance Argument:
#   filepath   The string in which environment variable replacement is occurring
class FilePath(object):
    envre=re.compile("(\$\{)([_A-Za-z]+)(\})")  # Regular expression matching
    def __init__(self,filepath):
        self.path=filepath
        self.rep=None

    # Perform environment variable replacement within the string.
    # Returns:
    #   the string with environment variables replaced or
    #   if no environment variables are present the original string is returned
    def replace(self):
        path=self.path        # The string being searched for variables
        rep=""                # The replacement string being constructed
        next=0                # Position of the next pattern matching search
        end=len(path)         # The end position of the search
        pat=FilePath.envre    # The regular expressiong used to search for variables

        # Continue looking for variables until none are found in the string
        while next < end:
            mo=pat.search(path,next)
            if mo is None:
                # If a match object was not created no variables exist in the
                # remainder of the string.  Could occur on the first search
                rep=rep+path[next:end]  # Add remainder of string to the replacement
                break                   # End the search loop

            # Match object was created, so an environment variable has been found
            start=mo.start()            # Locate start of the variable
            if start>next:
                part=path[next:start]   # For part of the string that did not match
                rep=rep+part            # add it to the replacement

            # Try to retrieve the environment variable's value
            var=mo.group(2)
            try:
                val=os.environ[var]     # Environment variable exists, so use it
            except KeyError:
                val=""     # Environment variable does not exist use an empty string
            rep=rep+val    # Add the replacement string to the result
            next=mo.end()  # Search on next pass after the found variable

        self.rep=rep
        return rep


#
# +-------------------------------------+
# |                                     |
# |  Path Environment Variable Manager  |
# |                                     |
# +-------------------------------------+
#

# This class encapsulates the processing of a single search order path
class SOPath(object):
    def __init__(self,variable):
        self.variable=variable   # Environment variable
        self.directories=[]      # Directory source tuple list
        self.dir_list=[]         # Directory search list

    def __str__(self):
        return "SOPath %s: %s" % (self.variable,self.dir_list)

    def append(self,source,directory):
        t=(source,directory)
        self.directories.append(t)
        self.dir_list.append(directory)

    # Add a list of externally configured directories to the search order
    def config(self,lst):
        for d in lst:
            self.append("C",d)

    # Provide a config information list of directories
    def cinfo(self,indent=""):
        lst=[]
        for source,d in self.directories:
            string="%s%s %s" % (indent,source,d)
            lst.append(string)
        return lst

    # Add the current working directory if not present in the list
    # Method Argument:
    #   option   defines how the current working directory is to be handled when
    #            creating a search order path.
    #            Specify 'last' to add as the last directory if not explicitly used
    #            Specify 'first' to allways place the cwd as the first directory.
    #            Specify 'omit' or None to not automatically add the cwd.
    #            Defaults to None (or omit)
    # Note: the option argument implements the action requested by the site.cfg
    # SITE section configuration file option 'cwduse'.
    def cwd(self,option=None):
        if option is None or option=="omit":
            return
        elif option=="last":
            curwd=os.getcwd()
            if curwd not in self.dir_list:
                self.append("W",curwd)
        elif option=="first":
            curwd=os.getcwd()
            new_dirs=[("W",curwd),]
            new_dirs.extend(self.directories)
            self.directories=new_dirs
            new_list=[curwd,]
            new_list.extend(self.dir_list)
            self.dir_list=new_list
        else:
            clsstr="satkutil.py - %s.cwd() -" % (self.__class__.__name__)
            raise ValueError("%s 'option' argument unexpected value: %s" \
                % (clsstr,option))

    # Display the path information
    def display(self,indent="",string=False):
        lst=["%s%s path:" % (indent,self.variable),]
        lcl="%s    " % indent
        #for source,d in self.directories:
        #    s="%s\n%s%s %s" % (s,lcl,source,d)
        lst.extend(self.cinfo(indent=lcl))
        s="\n".join(lst)
        if string:
            return s
        print(s)

    # Populates the directory lists from the environment variable
    def environment(self,default=None,debug=False):
        try:
            path=os.environ[self.variable]
            if debug:
                clsstr="satkutil.py - %s.environment() -" % (self.__class__.__name__)
                print("%s environment variable '%s': '%s'" \
                    % (clsstr,self.variable,path))
        except KeyError:
            if default is not None:
                self.append("D",default)
            return
        rawlist=path.split(os.pathsep)
        for d in rawlist:
            self.append("E",d.strip())


# This class manages paths environment variables for an applications opening
# files via search paths.  Path environment variables are registered with the
# class when instantiated or later using the path() method.  This class is designed
# to used for all paths, or individual instances may be used for a subset including
# one path.
#
# Instance arguments:
#    'variable'   A single string or list of strings identifying the supported
#                 environment variables.
#    default      The default directory if an environment variable is not defined.
#                 Defaults to None.
class PathMgr(object):
    def __init__(self,variable=None,default=None,debug=False):
        self.debug=debug          # Enable debugging of all methods
        self.paths={}             # Dictionary of supported paths

        if __debug__:
            clstr="satkutil.py - %s.__init__() -" % (self.__class__.__name__)

        if variable is None:
            return
        elif isinstance(variable,list):
            for n,v in enumerate(variable):
                assert isinstance(v,str),\
                    "%s 'variable' argument list element %s not a string: %s" \
                        % (clsstr,n,v)
            vars=variable
        elif isinstance(variable,str):
            vars=[variable,]
        else:
            raise ValueError("%s 'variable' argument must be a list or str: %s" \
                % (clsstr,variable))

        for v in vars:
            self.path(v,default=default)

    def __str__(self):
        return "PathMgr: %s" % self.paths

    # Returns configuration information about the specific path
    def cinfo(self,variable):
        try:
            return self.paths[variable]
        except KeyError:
            clstr="satkutil.py - %s.cinfo() -" % (self.__class__.__name__)
            raise ValueError("%s 'variable' argument not a recognized path "
                "environment variable: %s" % (clsstr,variable))

    # Returns a list of file names in the path with the specified extension.
    # File names are not absolute.  ropen() method required to access the file.
    #
    # Method argument:
    #   variable    Environment variable string
    #   ext         Selects files with this extension.  If ommitted, all files returned
    #               The ext string must contain the initial "." to match
    def files(self,variable,ext=None,debug=False):
        if __debug__:
            clsstr="satkutil.py - %s.path() -" % self.__class__.__name__
        assert isinstance(variable,str),\
            "%s 'variable' argument must be a string: %s" % (clsstr,variable)

        fdebug=debug or self.debug
        try:
            path=self.paths[variable]
            pathlist=path.dir_list
        except KeyError:
            pathlist=[]
            if __debug__:
                if fdebug:
                    print("%s 'variable' argument not a defined path: '%s'" \
                        % (clsstr,variable))
        files=[]
        for d in pathlist:
            entries=os.listdir(d)
            for x in entries:
                if len(x)<1 or x[0]==".":
                    # Ignore hidden files
                    continue
                path=os.path.join(d,x)
                if not os.path.isdir(path):
                    # assume a file
                    if ext is not None:
                        fileroot,extension=os.path.splitext(path)
                        if extension!=ext:
                            continue
                    if x not in files:
                        files.append(x)
        return files

    # Perform the actual opening of the file
    def osopen(self,filename,mode,debug=False):
        if __debug__:
            if debug:
                print("satkutil.py - %s.osopen() - trying: open('%s','%s')" \
                    % (self.__class__.__name__,filename,mode))
        return open(filename,mode)

    # Registers an environment variable to be used for file search paths by the
    # application.
    #
    # Method arguments:
    #   variable    Environment variable string.
    #   config      Specifies one or more directories configured independently
    #               of the environment variable, appended to the environment variable
    #               list.  Configured directories are searched after environment
    #               variable directories.
    #   cwdopt      Specifies how current working directory is to be handled.
    #               Specify 'first' to always place cwd first in directory list
    #               Specify 'last' to place cwd as last directory if not in list
    #               Specify None to ignore current working directory.  Defaults to
    #               None.
    #   default     Specifies a default directory if the environment variable and is
    #               configured directories are both unavailable
    #   debug       Specify True to enable debug message generation.
    def path(self,variable,config=[],cwdopt=None,default=None,debug=False):
        if __debug__:
            clsstr="satkutil.py - %s.path() -" % self.__class__.__name__
        assert isinstance(variable,str),\
            "%s 'variable' argument must be a string: %s" % (clsstr,variable)
        assert default is None or isinstance(default,str),\
            "%s 'default' argument must be a string: %s" % (clsstr,default)

        ldebug=debug or self.debug

        path=SOPath(variable)

        # List of configured directories
        cfglist=[]
        if __debug__:
            if ldebug:
                print("%s config: %s" % (clsstr,config))
        for n,d in enumerate(config):
            assert isinstance(d,str),\
                "%s configured directory %s not a string: %s" % (clsstr,n,d)
            cfglist.append(d)
        if __debug__:
            if ldebug:
                print("%s cfglist: %s" % (clsstr,cfglist))

        # Populate the path from the environment variable (or default if
        # environment variable is not currently defined)
        path.environment(default=default)
        # Add the configured directories to the list
        path.config(cfglist)
        # Add current working directory if not already in the path
        path.cwd(option=cwdopt)

        # Register the recognized path
        self.paths[path.variable]=path
        if __debug__:
            if ldebug:
                print("%s %s" % (clsstr,path.display(string=True)))

    # Opens the file in the specified mode and returns the file object.  If
    # supplied, the predefined path variable is used to find the supplied
    # relative path.  If an path variable is not supplied, or an absolute path
    # is supplied, standard Python processing occurs.
    #
    # Method arguments:
    #   filename    A path or filename to a file to be opened. Required.
    #   mode        The mode in which the file is to be opened.  Defaults to "rt".
    #   variable    Recognized path environment variable string used to search for the
    #               file.  Optional.  If not supplied, standard Python open processing
    #               applies.  The arguemnet string must have been defined when the
    #               class was instantiated (via the 'variable' argument or later
    #               added via the path() method.
    #   stdio       Specify True to open a file object.
    #               Specify False to open a file descriptor object.
    #               Defaults to True.
    #   debug       Enable debug messages during the call.
    #
    # Returns when stdio=True:
    #   If 'variable' is a register path, returns the tuple:
    #     (absolute_path, open_file_object).  The absolute_path is the path
    #     that was used to _successfully_ open the file.  The open_file_object
    #     is ready to be used for file operations as allowed by the mode.
    #   If 'variable' is not a registered search path or 'filename' is an
    #     absolute path, returns the tuple (filename, open_file_object).
    #     The search path used to open the 'filename' is dictated by the host
    #     operating system in this case.
    #   Otherwise, None is returned.
    #
    # Returns when stdio=False:
    #   The same process is followed, but instead of an open file object,
    #   an open file descriptor is returned in a tuple:
    #   (absolute_path, open_file_descriptor).
    #
    # Refer to Python documentation for the operations allowed on file objects
    # vs. file descriptors.  Normally, file objects are used.
    #
    # Exceptions:
    #   ValueError  Raised if the file fails to open.  Note, this differs from normal
    #               file open processing that raises an IOError exception.  IOError
    #               exceptions are caught and not propagated upward.  Only can occur
    #               if path=False
    def ropen(self,filename,mode="rt",variable=None,stdio=True,debug=False):
        ldebug=debug or self.debug #or True

        #print("%s.%s - ropen() - filename: %s  mode: %s variable: %s stdio: %s"\
        #    " debug: %s" % (this_module,self.__class__.__name__,filename,mode,\
        #        variable,stdio,debug))

        # Try locating the path list to open the file.
        try:
            path=self.paths[variable]
            pathlist=path.dir_list
        except KeyError:
            pathlist=None
            if __debug__:
                if ldebug:
                    clsstr="satkutil.py - %s.ropen() -" % (self.__class__.__name__)
                    print("%s 'variable' argument not a defined path: '%s'" \
                        % (clsstr,variable))

        # For absolute paths or where a path variable name has not been
        # registered, default to Python's native behavior.
        if os.path.isabs(filename) or pathlist is None:
            #print("%s.%s - ropen() - filename: %s  absolute: %s variable: %s "\
            #"pathlist: %s" % (this_module,self.__class__.__name__,filename,\
            #    os.path.isabs(filename),variable,pathlist))

            if stdio:
                # Return the open file object
                try:
                    return (filename,self.osopen(filename,mode,debug=ldebug))
                except IOError as ie:
                    if __debug__:
                        if debug:
                            print(ie)
                    raise ValueError("could not open in mode '%s' file: %s" \
                        % (mode,filename)) from None
            else:
                # Return the open file descriptor.
                try:
                    return (filename,os.open(filename,os.O_RDONLY))
                except EnvironmentError:
                    return None

        # Try using search path to open the relative path
        if __debug__:
            if ldebug:
                clsstr="satkutil.py - %s.ropen() -" % (self.__class__.__name__)
                print("%s using path %s with directories: %s" \
                    % (clsstr,variable,pathlist))
        if stdio:
            # Return the open file object
            for p in pathlist:
                filepath=os.path.join(p,filename)
                try:
                    return (filepath,self.osopen(filepath,mode,debug=ldebug))
                # on success, simply return the tuple (abspath,file_object)
                except IOError as ie:
                    if __debug__:
                        if ldebug:
                            print("%s - %s.ropen() - FAILED to open: %s" \
                                 % (this_module,self.__class__.__name__,filepath))
                            print(ie)
                    continue

            raise ValueError(\
                "could not open in mode '%s' file '%s' with search path: %s" \
                    % (mode,filename,variable))

        else:
            # Return the open file descriptor object
            for p in pathlist:
                filepath=os.path.join(p,filename)

                try:
                    return (filepath,os.open(filepath,os.O_RDONLY))
                # on success, simply return the tuple (abspath,descriptor_object)
                except EnvironmentError:
                    continue

            raise ValueError(\
                "could not open file descriptor for file '%s' with search path: %s" \
                    % (mode,filename,variable))


# This class accepts a string as its instance argument and will format the
# string for printing with line numbers.  It will either print t'he formatted
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
    def print(self,indent="",string=False):
        print_lines=self.cleanends()   # Clean up any trailing whitespace

        # Determine how big the line numbers are, allow space for '[',']' and ' '
        lines=len(print_lines)
        size=len("%s" % lines)+3

        s=""
        line_number=1
        for line in print_lines:
            number="[%s]" % line_number
            number=number.ljust(size)
            s="%s%s%s%s\n" % (s,indent,number,line)
            line_number+=1
        if len(s)==0:
            s="[1]"       # If there were no lines pretend the first was empty
        else:
            s=s[:-1]      # Remove last '\n' in formatted string
        if string:
            return s      # string=True so just return the formatted text
        print(s)          # string=False so print the string here


#
# +--------------------+
# |                    |
# |  Useful Functions  |
# |                    |
# +--------------------+
#

# Convert a list of integers, bytes or bytesarray into a string independent of
# encoding.
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


# Produce a hex dump of a bytes/bytearray sequence as a string
# Function Arguments:
#   barray   the sequence being dumped
#   start    the initial starting address.  Defaults to 0
#   mode     the "address mode" used for the dump.  Accepts 24,31,64.  Defaults to 24
#   indent   a string constituting the line indent
# Returns:
#   a string of the hexadecimal represantation of the binary sequence
def dump(barray,start=0,mode=24,indent=""):
    #isstring=isinstance(barray,type(""))
    isstring=not isinstance(barray,(bytes,bytearray))
    if mode==31:
        format="%s%s%08X %s\n"
    else:
        if mode==64:
           format="%s%s%016X %s\n"
        else:
           format="%s%s%06X %s\n"
    string=""
    addr=start
    strlen=len(barray)
    #print("strlen: %s" % strlen)
    strend=strlen-1
    for x in range(0,strlen,16):
        #print("x=%s" % x)
        linestr=""
        for y in range(x,x+15,4):
            #print("y=%s" % y)
            wordstr=""
            if y>strend:
                continue
            last=min(y+4,strlen)
            for z in range(y,last,1):
                #print("z=%s" % z)
                if isstring:
                    wordstr="%s%02X" % (wordstr,ord(barray[z]))
                else:
                    wordstr="%s%02X" % (wordstr,barray[z])
            linestr="%s %s" % (linestr,wordstr)
        string=format % (string,indent,addr,linestr)
        addr+=16
    return string[:-1]


# This function returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exception string of:
#     'module - class_name.method_name() - error information'
#
# Use of this function outside of satkutil requires use of the module argument.
# Otherwise the module will be erroneously reported as this module.
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)


# For the supplied method object, returns a tuple: method's class name, method name)
def method_name(method):
    io=method.__self__   # Get the instance object from the method object
    cls=io.__class__     # Get the class object from the instance object
    fo=method.__func__   # Get the function object from the method object
    return (cls.__name__,fo.__name__)


# Add a relative directory dynamically to the PYTHONPATH search path
# Method Arguments:
#   dir    directory relative to SATK root
#   nodup  Whehter a duplicate directory may be added (False) or not (True).
#          Defaults to False.
#   debug  Whether debugging messages are to be generated
def pythonpath(dir,nodup=False,debug=False):
    new_dir=satkdir(dir,debug=debug)
    if nodup:
        for d in sys.path:
            if __debug__:
                if debug:
                    print("satkutil.py - pythonpath() - PYTHONPATH dir checked "\
                        "for being duplicate of '%s': '%s'" % (new_dir,d))
            # sys.path strings and strings generated here are not the same string
            # so have to use string comparison
            if d == new_dir:
                # Not a duplicate, check next directory
                if __debug__:
                   if debug:
                       print("satkutil.py - pythonpath() - directory alreaedy in "
                           "PYTHONPATH, ignoring: %s" % new_dir)
                return

    # Add the new directory to PYTHONPATH
    path=[new_dir,]
    if __debug__:
        if debug:
            print("satkutil.py - pythonpath() - adding path: '%s'" % path[0])
    path.extend(sys.path)
    sys.path=path
    if __debug__:
        if debug:
            print("satkutil.py - pythonpath() - sys.path=%s" % sys.path)


# Determine an SATK directory based upon the root
def satkdir(reldir,debug=False):
    assert not os.path.isabs(reldir),\
        "satkutil.py - satkdir() - 'reldir' argument must be a relative path: '%s'" \
            % reldir
    root=satkroot()
    if __debug__:
        if debug:
            print("satkutil.py - satkdir() - SATK root: '%s'" % root)
    return os.path.join(root,reldir)


# Determine the SATK root directory from where this module resides.
def satkroot():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import only" % this_module)
