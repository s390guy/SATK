#!/usr/bin/python3
# Copyright (C) 2013,2014 Harold Grovesteen
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

this_module="inventory.py"
copyright_years="2013,2014"

# Python imports:
import sys        # Access system exit function and Python version information
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse   # Access the command line parser module
import functools  # Access cmp_to_key for sorting
import os         # Access OS facilities.

# SATK imports:
import satkutil   # Access utilities.

class analyze(object):
    # Returns the relative path from a root
    @staticmethod
    def relpath(path,root):
        common=os.path.commonprefix([path,root])
        if common!=root:
            return path
        relpath=path[len(common):]
        if relpath[0]==os.sep:
            relpath=relpath[1:]
        return relpath

    # Qualifies a file path based upon terminiating suffix.
    @staticmethod
    def suffix(name,suffix=""):
        suflen=len(suffix)
        if suflen==0:
            return True
        if len(name)<suflen:
            return False
        return name[-suflen:]==suffix
    
    # Creates the generic instance
    def __init__(self,suffix="",debug=[]):
        self.suffix=suffix    # File path suffix used to qualify file path.
        # List of fileo with absolute paths
        self.paths=[]         
        # Dictionary of absolute directories and the number of files in it
        self.dirs={} 
        # List of valid file objects
        self.files=[]
        # Debug options list (from inventory.py)
        self.debug=debug
        
    # Adds a qualified file to the file path list and counts the files in
    # related directories.  Qualifying suffix may be overriden
    def add_file(self,path,suffix=None):
        if suffix is None:
            sfx=self.suffix
        else:
            sfx=suffix
        if analyze.suffix(path,sfx):
            fileo=self.fileo(path)
            if self.isDebug("paths"):
                print("%s.add_file() - added to self.paths: %s(%s)" \
                    % (self.__class__.__name__,fileo.__class__.__name__,path))
            self.paths.append(fileo)
            return True
        if self.isDebug("paths"):
            print("%s.add_file() - path suffix '%s' did not match for path: %s" \
                % (self.__class__.__name__,sfx,path))
        return False

    # Add all the files in an individual tree instance.  Suffix may be overridden
    def add_tree(self,tree,suffix=None):
        if suffix is None:
            sfx=self.suffix
        else:
            sfx=suffix
        for x in tree.files:
            self.add_file(x,suffix=sfx)
            
    def build_refs(self):
        raise NotImplementedError("inventory.py - subclass must "
            "provide build_refs() method: %s" % self.__class__.__name__)

    # Increment the file count in dirctory dictionary
    def dir_count(self,fileo):
        d,f=os.path.split(fileo.path)
        try:
            dcnt=self.dirs[d]
        except KeyError:
            dcnt=0
        self.dirs[d]=dcnt+1
        
    # Create afile object instance - must be supplied by subclass
    def fileo(self,path):
        raise NotImplementedError("inventory.py - subclass must "
            "provide fileo() method: %s" % self.__class__.__name__)
        
    def file_summary(self,root):
        rep=""
        relpaths=[]
        for f in self.files:
            relpaths.append(analyze.relpath(f.path,root))
        sorted_paths=sorted(relpaths)
        for p in sorted_paths:
            rep="%s\n    %s" % (rep,p)
            
        return rep[1:]
        
    # Return whether the 'comp' debug option has been set.
    def isDebug(self,comp):
        return comp in self.debug
        
    def report(self,*args,**kwds):
        raise NotImplementedError("inventory.py - subclass must "
            "provide report() method: %s" % self.__class__.__name__)
        
    def sort_locs(self,*args,**kwds):
        raise NotImplementedError("inventory.py - subclass must "
            "provide sort_locs() method: %s" % self.__class__.__name__)

class assembler(analyze):
    def __init__(self,debug=[]):
        super().__init__(suffix=".S",debug=debug)
        self.ref_funcs=references("function")
        self.ref_includes=references("include")
        self.ref_macros=references("macro")
        self.ref_structs=references("struct")

    def build_refs(self):
        for f in self.files:
            for r in f.loc_func:
                self.ref_funcs.add_ref(r)
            for r in f.loc_include:
                self.ref_includes.add_ref(r)
            for r in f.loc_macro:
                self.ref_macros.add_ref(r)
            for r in f.loc_struct:
                self.ref_structs.add_ref(r)
        if self.isDebug("asm"):
            print("assembler.build_refs() - includes=%s, macros=%s, structures=%s, " 
                "functions=%s" \
                % (len(self.ref_includes),len(self.ref_macros),\
                    len(self.ref_structs),len(self.ref_funcs)))
            
    def fileo(self,path):
        return asm_dot_s(path,debug=self.debug)
    def report(self,root,inc=False,mac=False,struct=False,fun=False):
        rep="\nASSEMBLER File Summary"
        rep="%s\n%s" % (rep,self.file_summary(root))
        if inc:
            rep="%s\n%s" % (rep,"\nAssembler include references:")
            rep="%s\n%s" % (rep,self.ref_includes.report())
        if mac:
            rep="%s\n%s" % (rep,"\nAssembler macro definitions:")
            rep="%s\n%s" % (rep,self.ref_macros.report(single=True))
        if struct:
            rep="%s\n%s" % (rep,"\nAssembler structure definitions:")
            rep="%s\n%s" % (rep,self.ref_structs.report(single=True))
        if fun:
            rep="%s\n%s" % (rep,"\nAssembler function definitions:")
            rep="%s\n%s" % (rep,self.ref_funcs.report(single=True))    
        return rep
    def sort_locs(self):
        for r in [self.ref_funcs,self.ref_includes,self.ref_macros,self.ref_structs]:
            r.sort_locs()

class bash(analyze):
    def __init__(self,debug=[]):
        super().__init__(debug=debug)
    def build_refs(self): pass
    def fileo(self,path):
        return bash_script(path,debug=self.debug)
    def report(self,root):
        rep="\nBASH File Summary"
        rep="%s\n%s" % (rep,self.file_summary(root))
        return rep
    def sort_locs(self): pass

class python(analyze):
    def __init__(self,debug=[]):
        super().__init__(suffix=".py",debug=debug)
        self.ref_imports=references("import")
        self.ref_classes=references("class")
        self.ref_funcs=references("function")
        
    def build_refs(self):
        for f in self.files:
            for r in f.loc_import:
                self.ref_imports.add_ref(r)
            for r in f.loc_class:
                self.ref_classes.add_ref(r)
            for r in f.loc_func:
                self.ref_funcs.add_ref(r)
        if self.isDebug("python"):
            print("python.build_refs() - imports=%s, classes=%s, functions=%s" \
                % (len(self.ref_imports),len(self.ref_classes),len(self.ref_funcs)))
    def fileo(self,path):
        return python_script(path,debug=self.debug)
    def report(self,root,imp=False,obj=False):
        rep="\nPython File Summary"
        rep="%s\n%s" % (rep,self.file_summary(root))
        if imp:
            rep="%s\n%s" % (rep,"\nPython import references:")
            rep="%s\n%s" % (rep,self.ref_imports.report())
        if obj:
            rep="%s\n%s" % (rep,"\nPython class definitions:")
            rep="%s\n%s" % (rep,self.ref_classes.report(single=True))
            rep="%s\n%s" % (rep,"\nPython function definitions:")
            rep="%s\n%s" % (rep,self.ref_funcs.report(single=True))
        return rep
    def sort_locs(self):
        for r in [self.ref_imports,self.ref_classes,self.ref_funcs]:
            r.sort_locs()

class afile(object):
    def __init__(self,path,shb=None,debug=[]):
        self.path=path       # Absolute path to file
        self.shb=shb         # Test shebang string
        self.found=False     # Could we open the file
        
        self.debug=debug     # Debug options list (from inventory.py)
        
        # File content related attributes.  Set by getContent() method.
        # Indicates whether content is bytes (True) or list of lines (False)
        self.binary=None
        self.content=None      # File content
        
    # Read the files content for analysis
    def getContent(self,bin=False):
        #if self.isDebug("files"):
        #    print("%s.getContent() - reading file content (binary=%s): %s" \
        #        % (self.__class__.__name__,bin,self.path))
        self.found=False
        read=False
        closed=False
        if bin:
            mode="rb"
        else:
            mode="rt"
            
        # Open the file
        try:
            fo=open(self.path,mode=mode)
            self.found=True
        except IOError:
            print("%s.getContent() - Could not open file in mode '%s': %s" \
                % (self.__class__.__name__,mode,self.path))
            return self.found

        # Read the file
        try:
            if bin:
                self.content=fo.read()
                self.binary=True
            else:
                self.content=fo.readlines()
                self.binary=False
            read=True
        except IOError:
            print("%s.getContent() - Could not read file in mode '%s': %s" \
                % (self.__class__.__name__,mode,self.path))

        # Close the file   
        try:
            fo.close()
            closed=True
        except IOError:
            print("%s.getContent() - Could not close file in mode '%s': %s" \
                % (self.__class__.__name__,mode,self.path))

        result = self.found and read and closed
        
        if self.isDebug("files"):
            if result:
                print("%s.getContent() - successfully read file content "
                    "(binary=%s): %s" % (self.__class__.__name__,bin,self.path))
            else:
                print("%s.getContent() - file content failed "
                    "(found=%s, read=%s, closed=%s): %s" \
                    % (self.__class__.__name__,self.found,read,closed,self.path))
        
        return result

    # Return whether the 'comp' debug option has been set.
    def isDebug(self,comp):
        return comp in self.debug
        
    def isShebang(self):
        debug=self.isDebug("shebangs")
        res=False
        if self.binary:
            ftype="binary"
            if len(self.content)<len(self.shb):
                if debug:
                    print("%s.isShebang() - binary file too short: %s"
                        % (self.__class__.__name__,self.path))
                return False
            else:
                files=self.content[:len(self.shb)]
        else:
            ftype="text"
            ln=self.content[0]
            if len(ln)<len(self.shb):
                if debug:
                    print("%s.isShebang() - text file first line too short: %s"
                        % (self.__class__.__name__,self.path))
                return False
            else:
                files = ln[:len(self.shb)]
               
        res = files == self.shb    
        if debug:        
            if res:
                r="matched"
            else:
                r="did not match"
            print("%s.isShebang() - %s - %s file shebang='%s' ? shebang='%s': %s" \
                % (self.__class__.__name__,r,ftype,files,self.shb,self.path))
        return res
        
    # Removes a comment from a line
    # This is not a perfect algorithm, but is good enough for our purposes
    # It returns, the original string, a shorter string or even an empty string
    def remove_comment(self,line):
        try:
            start=line.rfind("#")
            return line[:start]
        except ValueError:
            return line
        
    def scan(self,*args,**kwds):
        raise NotImplementedError("inventory.py - afile.scan() - subclass %s must "
            "provide the scan() method" % self.__class__.__name__)
        
    # Test the files initial 'shebang' content.  Override this default with an
    # actual test in a subclass.
    def shebang(self):
        return self.isShebang()

class asm_dot_s(afile):
    # Macros used to declare ABI functions
    functions=["functionx","function","func370","abi_func"]
    def __init__(self,path,debug=[]):
        super().__init__(path,debug=debug)
        self.loc_func=[]      # List of functions definition locations
        self.loc_include=[]   # List of include statement locations
        self.loc_macro=[]     # List of macro definitions locations
        self.loc_struct=[]    # List of structures definition locations
      
    # Assumes words is ['function_macro','function_name'....]
    def found_function(self,lineno,words,root):
        if len(words)<2:
            return
        loc=location("function",words[1],self.path,lineno)
        loc.relpath(root)
        self.loc_func.append(loc)
      
    # Assumes words is ['.include','"filename"',...]
    def found_include(self,lineno,words,root):
        if len(words)<2:
            return
        incfile=words[1]
        if len(incfile)<2:
            return
        incfile=incfile.strip('"')
        loc=location("include",incfile,self.path,lineno)
        loc.relpath(root)
        self.loc_include.append(loc)
      
    # Assumes words is ['.macro','name',...]
    def found_macro(self,lineno,words,root):
        if len(words)<2:
            return
        loc=location("macro",words[1],self.path,lineno)
        loc.relpath(root)
        self.loc_macro.append(loc)
        
    # Assumes words is ['struct','name,...',...]
    def found_struct(self,lineno,words,root):
        if len(words)<2:
            return
        s=words[1]
        try:
            se=s.index(",")
            s=s[:se]
        except ValueError:
            pass
        loc=location("struct",s,self.path,lineno)
        loc.relpath(root)
        self.loc_struct.append(loc)
            
    def scan(self,root):
        in_macro=False
        for lineno in range(len(self.content)):
            if in_macro:
                continue
            ln=self.remove_comment(self.content[lineno])
            ln=ln.lstrip()
            words=ln.split()
            if len(words)==0:
                continue
            first=words[0]
            if first[-1]==":":  # A label?
                words=words[1:]
                if len(words)==0:
                    continue
                first=words[0]
            if first==".endm":
                in_macro=False
                continue
            if in_macro:
                continue
            if first==".macro":
                self.found_macro(lineno,words,root)
                in_macro=True
                continue
            if first==".include":
                self.found_include(lineno,words,root)
                continue
            if first=="struct":
                self.found_struct(lineno,words,root)
                continue
            #try:
            #    ln.index("func")
                #if self.isDebug("asm"):
                #    print("asm_dot_s.scan() - words=%s: %s[%s]" \
                #        % (words,self.path,lineno))
            #except ValueError:
            #    continue
            
            if first in asm_dot_s.functions:
                self.found_function(lineno,words,root)

        if self.isDebug("asm"):
            print("asm_dot_s.scan() - includes=%s macros=%s struct=%s functions=%s"
                ": %s" \
                % (len(self.loc_include),len(self.loc_macro),len(self.loc_struct),\
                   len(self.loc_func),self.path))

    def shebang(self):
        return True
      
class bash_script(afile):
    def __init__(self,path,debug=[]):
        super().__init__(path,shb="#!/bin/sh",debug=debug)
        
class python_script(afile):
    def __init__(self,path,debug=[]):
        super().__init__(path,shb="#!/usr/bin/python",debug=debug)
        self.loc_import=[]    # Location of import modules
        self.loc_class=[]     # Location of class definitions
        self.loc_func=[]      # location of function definitions

    # Assumes 'name(....)'
    def extract_name(self,string):
        name=string.split("(")
        name=name[0].strip()
        return name

    def found_class(self,lineno,line,root):
        words=line.split()
        if len(words)<2:
            return
        # Assumes ['class','name(...):']
        name=self.extract_name(words[1])
        loc=location("class",name,self.path,lineno)
        loc.relpath(root)
        self.loc_class.append(loc)

    def found_function(self,lineno,line,root):
        words=line.split()
        if len(words)<2:
            return
        # Assumes ['class','name(,,,):']
        name=self.extract_name(words[1])
        loc=location("function",name,self.path,lineno)
        loc.relpath(root)
        self.loc_func.append(loc)

    def found_import(self,lineno,line,root):
        words=line.split()
        if len(words)<2:
            return
        # Assumes: ['import','module',...] or
        #          ['from','module',...]
        module=words[1]
        loc=location("import",module,self.path,lineno)
        loc.relpath(root)
        self.loc_import.append(loc)

    def scan(self,root):
        for lineno in range(len(self.content)):
            ln=self.remove_comment(self.content[lineno])
            if ln.startswith("import"):
                self.found_import(lineno,ln,root)
                continue
            if ln.startswith("from"):
                self.found_import(lineno,ln,root)
                continue
            if ln.startswith("class"):
                self.found_class(lineno,ln,root)
                continue
            if ln.startswith("def"):
                self.found_function(lineno,ln,root)
        if self.isDebug("python"):
            print("python_script.scan() - imports=%s classes=%s functions=%s: %s" \
                % (len(self.loc_import),len(self.loc_class),len(self.loc_func),\
                self.path))

    def shebang(self):
        res=self.isShebang()
        return res

class inventory(object):
    def __init__(self,args):
        super().__init__()
        self.args=args                 # argparse parsed results

        # General report options
        self.all=args.all              # all options flag
        self.listing=args.listing      # inventory report file path
        self.debug=args.debug          # Enable debug messages
        if len(self.debug)>0:
            print("inventory.__init__() - debugging enabled for: %s" % self.debug)
        
        # File type flags
        self.bashopt=args.bash         # Bash scripts
        
        # Assembler report options
        self.funopt=args.functions     # Assembler function locations
        self.incopt=args.includes      # Assembler include relationships
        self.macopt=args.macros        # Assembler macro locations
        self.stropt=args.structs       # Assembler structure locations

        # Python script report options
        self.impopt=args.imports       # Module import relationships
        self.objopt=args.objects       # Class and function locations

        # Enable all of the listing options if --all specified
        if self.all:
            self.funopt=True
            self.incopt=True
            self.macopt=True
            self.stropt=True
            self.bashopt=True
            self.impopt=True
            self.objopt=True

        # File type options.
        self.asmopt  = self.funopt or self.incopt or self.macopt or self.stropt
        self.pyopt   = self.impopt or self.objopt
        self.toolopt = self.pyopt  or self.bashopt

        # Build lists of files and directories
        self.root=satkutil.satkroot()      # SATK 'root' directory
        src=os.path.join(self.root,"src")
        self.src_tree=satkutil.dir_tree(src,hidden=True,
            files=[[".S",],None])

        samples=os.path.join(self.root,"samples")
        self.samples_tree=satkutil.dir_tree(samples,hidden=True,
            files=[[".S",],None])
        
        tools=os.path.join(self.root,"tools")
        self.tools_tree=satkutil.dir_tree(tools,hidden=True,
            dirs=[None,["__pycache__",]],
            files=[None,[".pyc","~"]])
        
        asma=os.path.join(self.root,"asma")
        self.asma_tree=satkutil.dir_tree(asma,hidden=True,\
            dirs=[None,["__pycache__",]],
            files=[None,[".pyc","~"]])
        
        # Analysis class instances are populated by self.analysis1() method
        self.asm=assembler(debug=self.debug)
        self.bash=bash(debug=self.debug)
        self.py=python(debug=self.debug)

    # create assembler, bash and python analysis classes
    def analysis1(self):
        debug=self.isDebug("paths")
        if debug:
            print("inventory.analysis1() - self.asmop: %s" % self.asmopt)
            print("inventory.analysis1() - self.toolopt: %s" % self.toolopt)
            print("inventory.analysis1() - self.pyopt: %s" % self.pyopt)
            print("inventory.analysis1() - self.bashopt: %s" % self.bashopt)
        if self.asmopt:
            self.asm.add_tree(self.src_tree)
            self.asm.add_tree(self.samples_tree)
        if self.toolopt:
            pysfx=self.py.suffix
            for path in self.tools_tree.files:
                if analyze.suffix(path,pysfx):
                    if self.pyopt:
                        self.py.add_file(path)
                else:
                    if self.bashopt:
                        self.bash.add_file(path)
            for path in self.asma_tree.files:
                if analyze.suffix(path,pysfx):
                    if self.pyopt:
                        self.py.add_file(path)

    # Validate shebangs and analyze file content
    def analysis2(self):
        debug=self.isDebug("files")
        if debug:
            print("inventory.analysis2() - input assembler files: %s" \
                % len(self.asm.paths))
            print("inventory.analysis3() - input bash files: %s" \
                % len(self.bash.paths))
            print("inventory.analysis2() - input python files: %s" \
                % len(self.py.paths))
            
        for t in [self.asm,self.bash,self.py]:
            for f in t.paths:
                f.getContent()
        for t in [self.asm,self.bash,self.py]:
            tname=t.__class__.__name__
            for f in t.paths:
                valid=f.shebang()
                if valid:
                    t.files.append(f)
                    if debug:
                        print("inventory.analysis2 - added to %s.files: %s" \
                            % (tname,f.path))
                else:
                    if debug:
                        print("inventory.analysis2 - rejected by %s file: %s" \
                            % (tname,f.path))

        if debug:
            print("inventory.analysis2() - validated assembler files: %s" \
                % len(self.asm.files))
            print("inventory.analysis3() - validated bash files: %s" \
                % len(self.bash.files))
            print("inventory.analysis2() - validated python files: %s" \
                % len(self.py.files))

    # Build locations data
    def analysis3(self):
        for t in [self.asm,self.py]:
            for f in t.paths:
                f.scan(self.root)

    # Build refence dictionaries
    def analysis4(self):
        for t in [self.asm,self.py]:
            t.build_refs()
            
    # Sort reference locations in dictionary
    def analysis5(self):
        for t in [self.asm,self.py]:
            t.sort_locs()
            
    # create report
    def analysis6(self):
        rep=''
        if self.bashopt:
            rep="%s\n%s" % (rep,self.bash.report(self.root))
        if self.asmopt:
            rep="%s\n%s" % (rep,self.asm.report(self.root,\
                inc=self.incopt,mac=self.macopt,struct=self.stropt,fun=self.funopt))
        if self.pyopt:
            rep="%s\n%s" % (rep,self.py.report(self.root,\
                imp=self.impopt,obj=self.objopt))
        return rep[1:]

    # Return whether the 'comp' debug option has been set.
    def isDebug(self,comp):
        return comp in self.args.debug

    def print(self):
        print("\nsample files: %s" % self.samples_tree.root)
        self.samples_tree.print()
        print("\nsrc files: %s" % self.src_tree.root)
        self.src_tree.print()
        print("\ntools: %s" % self.tools_tree.root)
        self.tools_tree.print()
        
    # Analyze the files in preparation for reports.
    def run(self):
        self.analysis1()   # Build analysis and afile objects
        self.analysis2()   # Analyze files
        self.analysis3()   # Build location data
        self.analysis4()   # Build reference dictionaries
        self.analysis5()   # Sort location references in dictionaries
        rep=self.analysis6()        # Create the report
        suc=self.write_report(rep)  # Write it out
        if not suc:
            sys.exit(2)
        sys.exit(0)
        
    # Write inventory report to file system
    def write_report(self,rep):
        print("inventory.py - listing file: %s" % self.listing)
        try:
            fo=open(self.listing,mode="w+")
        except IOError:
            print("inventory.py - could not open listing file: %s" % self.listing)
            return False
        try:
            fo.write(rep)
        except IOError:
            print("inventory.py - could not write listing file: %s" % self.listing)
            return False
        try:
            fo.close()
        except IOError:
            print("inventory.py - could not close listing file: %s" % self.listing)
            return False
        return True

class location(object):
    @staticmethod
    def sort_by_name(a,b):
        if a.name<b.name:
            return -1
        if a.name>b.name:
            return 1
        return 0
    @staticmethod
    def sort_by_ref(a,b):
        if a.filename<b.filename:
            return -1
        if a.filename>b.filename:
            return 1
        if a.lineno<b.lineno:
            return -1
        if a.lineno>b.lineno:
            return 1
        return 0
    def __init__(self,typ,item,filename,lineno):
        self.typ=typ            # Item type
        self.name=item          # The name of the item 
        self.filename=filename  # The file in which the item is located
        self.lineno=lineno      # The line number in the file where it is located
    def relpath(self,root):
        self.filename=analyze.relpath(self.filename,root)
        
class references(object):
    def __init__(self,typ):
        self.typ=typ   # Type of references being tracked by this object
        self.refs={}   # Dictionary of reference locations.

        # Maximum reference name length. Set by sorted_refs() method
        self.maxname=None

    def __len__(self):
        return len(self.refs)

    def add_ref(self,item):
        if not isinstance(item,location):
            raise ValueError("inventory.py - references.add_ref() - item not a "
                "location instance: %s" % item)
        if self.typ != item.typ:
            raise ValueError("inventory.py - references.add_ref() - expected "
                "location item of type '%s', found: '%s'" % (self.typ,item.typ))
        try:
            i=self.refs[item.name]
        except KeyError:
            i=[]
        i.append(item)
        self.refs[item.name]=i

    def report(self,single=False):
        refs=self.sorted_refs()
        #print("refs: %s" % refs)
        just=self.maxname+4
        rep=""
        for x in refs:
            locs=self.refs[x]
            if single and len(locs)==1:
                l=locs[0]
                rep="%s\n%s%s[%s]" % (rep,x.ljust(just),l.filename,l.lineno)
                continue
            rep="%s\n%s" % (rep,x)
            locs=self.refs[x]
            for l in locs:
                rep="%s\n    %s[%s]" % (rep,l.filename,l.lineno)
        return rep[1:]

    def sort_locs(self):
        for k in self.refs:
            refs=self.refs[k]
            sorted_refs=sorted(refs,key=functools.cmp_to_key(location.sort_by_ref))
            self.refs[k]=sorted_refs
 
    def sorted_refs(self):
        maxname=0
        refnames=[]
        for k in self.refs:
            maxname=max(maxname,len(k))
            refnames.append(k)
        sorted_names=sorted(refnames)
        self.maxname=maxname
        return sorted_names

def parse_args():
    parser=argparse.ArgumentParser(prog="inventory.py",
        epilog="inventory.py Copyright (C) %s Harold Grovesteen" % copyright_years,
        description="creates SATK inventory report")
    parser.add_argument("-a","--all",action="store_true",default=False,\
        help="enable all report options")
    parser.add_argument("-b","--bash",action="store_true",default=False,\
        help="report option: bash scripts")
    parser.add_argument("-f","--functions",action="store_true",default=False,\
        help="report option: assembly function locations")
    parser.add_argument("-i","--includes",action="store_true",default=False,\
        help="report option: assembly source include relationships")
    parser.add_argument("-m","--macros",action="store_true",default=False,\
        help="report option: assembly source file macro locations")
    parser.add_argument("-p","--imports",action="store_true",default=False,\
        help="report option: Python import relationships")
    parser.add_argument("-o","--objects",action="store_true",default=False,\
        help="report option: Python object locations")
    #parser.add_argument("-A","--ASMA",action="store_true",default=False,
    #    help="report option: ASMA import relationships")
    #parser.add_argument("-O","--OBJECTS",action="store_true",default=False,
    #    help="report option: ASMA import relationships")
    parser.add_argument("-s","--structs",action="store_true",default=False,\
        help="report option: Assembler structure locations")
    parser.add_argument("-l","--listing",default="inventory.txt",\
        help="path to output inventory report file. Default is 'inventory.txt'")
    parser.add_argument("-d","--debug",action="append",default=[],\
        choices=["paths","files","shebangs","asm","bash","python"], \
        help="enable debugging.  The argument may be supplied multiple times")

    return parser.parse_args()   

if __name__ == "__main__":
    i=inventory(parse_args())
    i.run()
