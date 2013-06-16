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

# This module provides a set of classes for defining and processing a file whose
# content contains a set of statements each of which uses keywords to define
# the statements.  
# 
# At its core is the SPECFILE class.  This module is only intended for use as an 
# imported module by other modules.

# Text files processed by this module contain single line statements of the form:
#
#    statement_id (keyword=value|keyword="value with spaces")...
#
# The specific keywords supported by a statement are defined by the define class 
# method in the statement's subclass.  How the keyword argument is processed is
# defined by the specific subclass of ARG used when the argument is defined.
# 
# See the ipl/volume.py module for an example of how this module is used.

# Python modules used
import os
import os.path
import re
import sys

# SATK modules used
from translate import *       # ASCII-EBCDIC translation tables
#from hexdump import *         # Bigendian binary conversion routines

# The following classes and their subclasses are used to process spcecification
# file statements.
#   SPECFILE - Overall processing of specification file content
#   STATEMENT - A specification of a statememt
#   ARG - Definition of a statement's argument.

# Exception thrown for errors detected during specfile creation
class SpecfileException(Exception):
    def __init__(self,*args):
        super(SpecfileException,self).__init__(*args)

# This is the base class for an argument
class ARG(object):
    def __init__(self,keyword):
        self.keyword=keyword.lower()
    
    # This method must be supplied by each subclass.  Failure to process the 
    # keyword value must result in a ValueError exception.
    def parse(self,string,debug=False):
        raise NotImplementedError("specfile.py - ARG subclass must provide 'parse' "
            "method: %s" % self.__class__.__name__)
        
# These are a set of predefined argument processors.  They may be extended or
# new subclasses defined based upon a specific file processor's needs.

# Return a string in the correct character set for a name, otherwise raise a 
# ValueError
class AorE(ARG):
    namere=re.compile(r'(?P<name>[a-zA-Z0-9$\._-]+)(?P<set>:[EA])?')
    def __init__(self,keyword):
        super(AorE,self).__init__(keyword)
    # The input string takes the form:
    #     'characters', 'characters:A' or 'characters:E'.
    #
    # A tuple containing the string in the correct character set and 
    # True or False indicating if the string is EBCDIC or not on successful 
    # parsing of the input string.  Otherwise a ValueError exception is raised.
    def parse(self,string,debug=False):
        isEBCDIC=False
        match=AorE.namere.match(string)
        if match is None:
            if debug:
                print("specfile.py - AorE.parse - match object returned None")
            raise ValueError
        ascii_name=match.group("name")
        name_set=match.group("set")
        endmatch=match.end(match.lastgroup)
        if debug:
            print("specfile.py - AorE.parse - re match group 'name' is '%s'" \
                % ascii_name)
            print("specfile.py - AorE.parse - re match group 'set' is '%s'" \
                % name_set)
            print("specfile.py - AorE.parse - re match last group end %s, " \
                "last string index %s" % (endmatch,len(string)))
        if endmatch!=len(string):
            raise ValueError # Not all of the string matched
        if name_set==":E":
            isEBCDIC=True
            ascii_name=ascii_name.translate(A2E)
        if debug:
            print("specfile.py - AorE.parse - return name string: '%s'" \
                % repr(ascii_name))
        return (ascii_name,isEBCDIC)

# Convert a string to a base-10 value, returning the value.  If the conversion
# fails, throw a ValueError
class DEC(ARG):
    def __init__(self,keyword):
        super(DEC,self).__init__(keyword)
    def parse(self,string,debug=False):
        try:
            return int(string,10)
        except IndexError:
            raise ValueError
            
# Convert a string to a base-16 value, returning the value.  If the conversion
# fails, throw a ValueError
class HEX(ARG):
    def __init__(self,keyword):
        super(HEX,self).__init__(keyword)
    def parse(self,string,debug=False):
        try:
            return int(string,16)
        except IndexError:
            raise ValueError

# This method returns an absolute path for the supplied path.  It does not generate 
# a ValueError exception.
class PATH(ARG):
    def __init__(self,keyword):
        super(PATH,self).__init__(keyword)
    def parse(self,string,debug=False):
        trial_path=string
        if debug:
            print("specfile.py - PATH.parse - specification path: %s" % string)
        trial_path=string
        # This does not work!  Further research is required to determine whether
        # and how to expand variables in paths.
        #trial_path=os.path.expandvars(string)
        #if debug:
        #    print("specfile.py - PATH.path - path with expanded variables: %s" \
        #        % trial_path)
        if not os.path.isabs(trial_path):
            trial_path=os.path.abspath(trial_path)
            if debug:
                print("specfile.py - PATH.parse - absolute path: %s" % trial_path)
        else:
            if debug:
                print("specfile.py - PATH.parse - path is absolute")
        return trial_path

# Removes double quotes from a string
class QSTRING(ARG):
    def __init__(self,keyword):
        super(QSTRING,self).__init__(keyword)
    def parse(self,string,debug=False):
        if len(string)<2:
            return string
        s=string
        if string[0]=='"':
            s=s[1:]
        if string[-1]=='"':
            s=s[:-1]
        return s
        
# Dummy method for strings
class STRING(ARG):
    def __init__(self,keyword):
        super(STRING,self).__init__(keyword)
    def parse(self,string,debug=False):
        return string
        
# Check for a value within a list of potential values.  If found the input string
# in lower case is returned as the result.  Otherwise a ValueError exception is 
# raised.
class STRING_LIST(ARG):
    def __init__(self,keyword,lst):
        super(STRING_LIST,self).__init__(keyword)
        self.lst=lst
    def parse(self,string,debug=False):
        lowercase=string.lower()
        if lowercase in self.lst:
            return lowercase
        raise ValueError
        
# Check for a yes/no value.  Returns True or False respectively.  If provided
# string is not 'yes', 'no', 'y', or 'n' (case insensitive), a ValueError is thrown.
class Y_N(ARG):
    def __init__(self,keyword):
        super(Y_N,self).__init__(keyword)
    def parse(self,string,debug=False):
        upper_string=string.upper()
        if upper_string == "YES" or upper_string == "Y":
            return True
        if upper_string == "NO" or upper_string == "N":
            return False
        raise ValueError

class SPECFILE(object):

    # Regular expressions used to parse portions of a statement
    stmt_re=re.compile(r'([\S]+)(\s+)')
    #     RE Groups      <--0--><-1->

    kv_re=re.compile(r'(\w+="[^"]+")([\s$]*)|(\w+=\S+)([\s$]*)')
    #     RE Groups    <-----0-----><---1--> <---2---><--3--->

    def __init__(self,module="specfile.py",debug=False):
        self.text=''     # Line of text as it is being processed
        
        self.classes={}       # Maps a statement id string to its class
        self.statements=[]    # List of valid statements

        self.errors=0         # Statements in error
        
        # Values shared between the parse methods
        self.begin=0          # Controls where in the string parsing should occur
        self.module=module    # Module name used for error messages.
        
    # This method processes a file whose content has been defined by a sub class 
    # of this class
    def process(self,filename,debug=False):
        fo=open(filename,"rt")
        self.lineno=0
        for line in fo:
            if line[-1]=="\n":
                self.text=line[:-1]
            else:
                self.text=line
            self.lineno+=1
            
            self.debug_line(debug)
            # Ignore blank or comment lines and strip left and right whitespace
            if self.is_comment():
                continue
            self.debug_line(debug)
            # Strip off any trailing comment and white space
            self.remove_comment(debug)
            self.debug_line(debug)
            
            # Create a list of parameters, the first identifying the statement
            # and the remaining ones being key-word arguments.
            
            try:
                self.parms=self.parse(self.text,debug=debug)
            except ValueError:
                self.errors+=1
                continue
            if debug:
                print("%s - SPECFILE.process - parms: %s" \
                    % (self.module,self.parms))

            if len(self.parms)==0:
                continue
            
            try:
                stmtcls=self.classes[self.parms[0].upper()]
            except KeyError:
                print("%s - ERROR - unrecognized statement [%s]: %s ..." \
                    % (self.module,self.lineno,self.parms[0]))
                self.errors+=1
                continue
            
            try:
                statement=stmtcls(self.lineno,self.parms[1:],debug=debug)
            except ValueError:
                print("%s - ERROR - statement in error [%s]: %s" \
                    % (self.module,self.lineno,self.text))
                self.errors+=1
                continue

            post_result=self.post_process(statement)
            if post_result is None:
                self.error+=1
                continue
            
            self.statements.append(statement)

        fo.close()
        
        if debug:
            for s in self.statements:
                print("%s" % s)

        if self.errors:
            print("%s - ERROR - specification statements in error: %s" \
                % (self.module,self.errors))
            raise ValueError
        
        # The specification file has now been turned into a VOLUME instance as
        # self.volume and a list of FILE instances as self.files

    def debug_line(self,debug):
        if debug:
            print("%s - SPECFILE - [%s]: '%s'" % (self.module,self.lineno,self.text))

    # Check for an empty line and strip left and right whitespace from the line
    def is_comment(self):
        self.text=self.text.strip()    # Remove leading and trailing white space
        if len(self.text)==0:   # If nothing is left, this is an empty line
            return True
        if self.text[0]=="#":   # If first non-blank character is a '#', a comment
            return True
        return False

    # Parses a line into a string (matching the statement) and a list of keyword
    # arguments.  By using regular expressions a keyword argument value of a 
    # string can be supported.
    def parse(self,string,debug=False):
        parms=[]          # Parsed parameters are added to this list
        s=string.strip()  # remove beginning and ending white space.

        if len(s)==0:     # If an empty line, then return no parms
            return parms

        stmt=self.parse_stmt(s,debug=debug)
        if debug:
            print("specfile.py - SPECFILE.parse - self.begin: %s" % self.begin)
            print("specfile.py - SPECFILE.parse - identified statement: %s" % stmt)
        parms.append(stmt)

        while self.begin<len(s):
             kv=self.parse_kv(s,debug=debug)
             if debug:
                 print("specfile.py - SPECFILE.parse - self.begin: %s" % self.begin)
                 print("specfile.py - SPECFILE.parse - identified kv pair: %s" \
                     % repr(kv))
             parms.append(kv)
        if debug:
            print("specfile.py - SPECFILE.parse - parms: %s" % repr(parms))   
        return parms

    def parse_kv(self,string,debug=False):
        # Returns a keyword/value pair as a string either: 
        #   'keyword=value' or 
        #   'keyword="string"'
        kv_match=SPECFILE.kv_re.match(string,self.begin)
        if kv_match is None:
            if debug:
                print("specfile.py - SPECFILE.parse_kv - kv_re returned None")
            raise ValueError
        kv_groups=kv_match.groups()
        if debug:
            print("specfile.py - SPECFILE.parse_kv - kv_groups: %s" \
                % repr(kv_groups))
        # WARNING: these statements are tied to the kv_re regular expression
        # Changes to the expression may cause changes to the group numbers
        if kv_groups[0] is not None:
            parm=kv_groups[0]
        else:
            if kv_groups[2] is not None:
                parm=kv_groups[2]
            else:
                print("%s - ERROR - malformed keyword/value pair near "
                    "pos: %s" % (self.module,self.begin))
                raise ValueError
        kv_end=kv_match.end()
        if kv_end<=self.begin:
            raise ValueError("kv_end (%s) not past begin (%s)" \
                % (kv_end,self.begin))
        if debug:
            print("specfile.py - SPECFILE.parse_kv - remaining to parse: '%s'" %
                string[kv_end:])
        self.begin=kv_end
        return parm

    def parse_stmt(self,string,debug=False):
        # Returns the statement name as a string,
        stmt_match=SPECFILE.stmt_re.match(string)
        if stmt_match is None:
            if debug:
                print("specfile.py - SPECFILE.parse_stmt - stmt_re returned None")
            print("%s - malformed statement, could not identify statement "
                "type" % self.module)
            raise ValueError
        stmt_groups=stmt_match.groups()
        if debug:
            print("specfile.py - SPECFILE.parse_stmt - stmt_groups: %s" \
                % repr(stmt_groups))

        self.begin=stmt_match.end()  # Indicate where parse continues.
        if debug:
            print("specfile.py - SPECFILE.parse_stmt - remaining to parse: '%s'" %
                string[self.begin:])
        return stmt_groups[0]  # Group zero is the statement

    # Register a STATEMENT subclass for processing.  Only registered statement
    # classes will be recognized.
    def register(self,name,cls,debug=False):
        if not issubclass(cls,STATEMENT):
            raise TypeError("SPECFILE.register requires a subclass of STATEMENT: "
                "%s" % cls)
        try:
            self.classes[name]
            raise SpecfileException("duplicate statement id (class=%s) being "
                "registered:" % (cls.__name__,name))
        except KeyError:
            self.classes[name]=cls
        cls.init(debug=debug)
    
    # Remove a trailing statement, allow for more than one '#' sign
    def remove_comment(self,debug=False):
        not_done=True
        while not_done:
            rcomment=self.text.rfind("#")
            if debug:
                print("specfile.py - SPECFILE.remove_comment rcomment=%s, text='%s'" \
                    % (rcomment,self.text))
            if rcomment==-1:
                not_done=False
            else:
                self.text=self.text[:rcomment]
            self.text=self.text.rstrip()  # Remove any trailing white space too
            
    # This method may be overriden by a subclass
    def post_process(self,stmt):
        return stmt

class STATEMENT(object):
    # Initialize the required attributes of a subclass
    @staticmethod
    def register(cls,arg,debug=False):
        if not isinstance(arg,ARG):
            raise TypeError("STATEMENT.register - 'arg' must be a subclass of ARG: "
                "%s" % arg)
        args=cls.arguments
        try:
            args[arg.keyword]
            raise SpecfileException("Duplicate argument being registered with "
                "statement subclass %s: %s" % (cls.__name__,arg.keyword))
        except KeyError:
            args[arg.keyword]=arg

    # Class methods that must NOT be overridden by subclasses

    # Define an optional keyword argument for the STATEMENT subclass along with 
    # its default value.  Usually called by a subclass" class method define.
    @classmethod
    def default(cls,argo,value=None,debug=False):
        if debug:
            print("specfile.py - STATEMENT.default - argument '%s' for class %s: "
                "%s=%s" % (argo.keyword,cls.__name__,argo.__class__.__name__,value))
        STATEMENT.register(cls,argo,debug=debug)
        cls.dft[argo.keyword]=value

    # Initialize and define a STATEMENT subclass.
    @classmethod
    def init(cls,debug=False):

        if debug:
            print("specfile.py - STATEMENT.init - inializing class: %s" \
                % cls.__name__)

        # Initialize the class attributes associated
        cls.arguments={}   # keyword argument names mapped to argument instances
        cls.req=[]         # list of required argument keyword names
        cls.dft={}         # optional keyword argument names and default values
        cls.define(debug=debug)  # This class method must be provided by subclass

    # Define a keyword argument, neither required nor providing a default value
    @classmethod
    def keyword(cls,argo,debug=False):
        if debug:
            print("specfile.py - STATEMENT.keyword - argument '%s' for class %s: "
                "%s" % (argo.keyword,cls.__name__,argo.__class__.__name__))
        STATEMENT.register(cls,argo,debug=debug)

    # Define a required keyword argument for the STATEMENT subclass.  Usually
    # called by a subclass' class method define.
    @classmethod
    def required(cls,argo,debug=False):
        if debug:
            print("specfile.py - STATEMENT.required - argument '%s' for class %s: "
                "%s" % (argo.keyword,cls.__name__,argo.__class__.__name__))
        STATEMENT.register(cls,argo,debug=debug)
        cls.req.append(argo.keyword)
        
    # Class methods that MUST be proivded by subclasses
    
    # Class method provided by a subclass that defines the statements keyword
    # arguments.
    @classmethod
    def define(cls,*args,**kwds):
        raise NotImplementedError("STATEMENT.define - subclass must provide "
            "classmethod define: %s" % cls.__name__)
    
    def __init__(self,lineno,args,module="specfile.py",debug=False):
        self.lineno=lineno
        self.args=args
        self.debug=debug
        self.module=module # Module name used in error messages
        self.values={}     # A dictionary of supplied key-word values
        self.errors=0

        # These are READ-ONLY references to the static sub class attributes.
        self.arguments=self.__class__.arguments
        self.req=self.__class__.req
        self.dft=self.__class__.dft

        for x in args:
            kv=x.split("=")
            if len(kv)!=2:
                print("%s - ERROR - invalid argument in line [%s]: %s" \
                    % (self.module,self.lineno,x))
                self.errors+=1
                continue
            keyword=kv[0]
            key=keyword.lower()
            value=kv[1]  
            try:
                parser=self.arguments[key]
                if self.debug:
                    print("specfile.py - STATEMENT.__init__ - argument '%s' using "
                        "ARG subclass: %s" % (key,parser))
            except KeyError:
                print("%s - ERROR - unrecognized keyword in line [%s]: %s" \
                    % (self.module,self.lineno,keyword))
                self.errors+=1
                continue

            try:
                val=parser.parse(value,debug=self.debug)
            except ValueError:
                print("%s - ERROR - invalid value for argument '%s' in line"\
                    " [%s]: '%s'" % (self.module,keyword,self.lineno,value))
                self.errors+=1
                continue
                
            try:
                found=self.values[key]
                print("%s - ERROR - argument specified more than once in "
                    "line [%s]: %s" % (self.module,self.lineno,keyword))
                self.errors+=1
            except KeyError:
                self.values[key]=val

        # Ensure all required arguments are present in the statement
        for x in self.req:
            try:
                self.values[x]
            except KeyError:
                print("%s - ERROR - required argument missing in line [%s]: "\
                    " %s" % (self.module,self.lineno, x))
                self.errors+=1
        if self.errors:
            raise ValueError
          
        # Ensure all default values are specified
        for x in self.dft.keys():
            try:
                self.values[x]
            except KeyError:
                self.values[x]=self.dft[x]

    def __str__(self):
        return "%s:%s" % (self.__class__.__name__,self.string_values())

    def string_values(self,pad="   "):
        string=""
        keys=self.values.keys()
        keys.sort()
        for x in keys:
            val=self.values[x]
            if type(val)==type(""):
                val=repr(val)
            else:
                if type(val)==type(0):
                    val="%s (%s)" % (val,hex(val))
            string="%s\n%s%s=%s" %  (string,pad,x,val)
        return string

def copyright():
    print("specfile.py Copyright, Harold Grovesteen, 2012")

if __name__ == "__main__":
    copyright()
    raise NotImplementedError("specfile.py - ERROR - supports only module import")
