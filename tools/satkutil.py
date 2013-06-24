#!/usr/bin/python3.3
# Copyright (C) 2013 Harold Grovesteen
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

# Python imports
import os
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

# Determine the SATK root directory from where this module resides.
def satkroot():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if __name__ == "__main__":
    raise NotImplementedError("satkutil.py - intended for import only")
