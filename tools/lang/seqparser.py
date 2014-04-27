#!/usr/bin/python3.3
# Copyright (C) 2014 Harold Grovesteen
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

# It is sometimes over kill to use a full scale grammar based parser.  The Sequential
# Parser provides a middle ground parser.  The Sequential Parser uses a sequential
# set of regular expressions to parse a string into separate parts.  Parts may be
# required or optional.  Failure to recognize an optional part causes the parser to
# simply look for the next part.  
#
# The result of the parsing operation is a list of recognized parts.  Unrecognized
# optional parts are represented in the list by a None object.  Failure to recognize
# a required part results in an exception.
#
# Similarly, a pattern may be searched within a string. The result is a list of parts
# where the pattern matched.  An exception is raised if the pattern is not found
# in the string.

# Python imports:
import re

# SATK imports: None

# This exception is raised if a sequential parse or search fails
# Instance Arguments:
#   msg    A string constituting a message related to the error. Defaults to ''.
#   n      The failing part number. Defaults to None.
#   pos    Position in the string where error occurred
class SequentialError(Exception):
    def __init__(self,msg="",n=None,pos=None):
        self.msg=msg
        self.n=n
        self.pos=pos
        super().__init__(msg)


# This object represents a recognized portion of a string.
# Instance arguments:
#   mo     The regular expression match object corresponding to the Part 
class Part(object):
    def __init__(self,mo,name):
        self.name=name            # PartRE object name
        self.mo=mo                # Regular expression match object
        self.match=mo.group()     # Total string matching the part
        # self.match is the same as string[self.beg:self.end]
        self.beg=mo.start()       # Starting position in the string of the match
        self.end=mo.end()         # Ending position in the string of the match
        self.groups=mo.groups()

    def __str__(self):
        return "Part RE '%s' [%s:%s]='%s' groups: %s" \
            % (self.name,self.beg,self.end,self.match,self.groups)

    # Returns the beginning position of a group
    def begin(self,n):
        return self.mo.start(n)

    # Returns the string matching a specific group in the regular expression
    def group(self,n):
        return self.groups[n]

    # Test if parse should continue.  By default, the parse continue with.  Override
    # for a different behavior
    # Method Arguments:
    #   n     The current part recognized
    # Returns:
    #   None  Causes the parse to end
    #   n+1   Causes the parse to proceed with the next Part (default behavior)
    #   x     Causes the parse to continue with the returned part.
    def test(self,n):
        return n+1


# This class provides support for parsing of an individual part.
# Instance arguments:
#   name      A string identifying the regular expression used for parsing
#   pattern   A string defining the regular expression pattern
#   cls       If specified it identifies the class to be instantiated when a match
#             is found.  Default to a Part object
#  Methods:
#   match     performs a match on a string from a specified position.
#   test      Indicates the next action of the parser
class PartRE(object):
    def __init__(self,name,pattern,cls=None,optional=False):
        self.name=name               # A name used to identify a failing match
        self.re_str=re               # Regular expression defining a part
        self.rec=re.compile(pattern) # Compiled re
        self.optional=optional       # Whether this part is optional.
        if cls is None:
            self.cls=Part            # Use default class for a Part
        else:
            self.cls=cls             # Use this subclass of Part 

    # Performs Part
    def match(self,string,pos=0,debug=False):
        if debug:
             cls_str="seqparser.py - %s.match() -" % self.__class__.__name__
             print("%s RE: %s matching '%s' from pos %s: '%s'"\
                 % (cls_str,self.name,string,pos,string[pos:]))
        mo=self.rec.match(string,pos)
        if mo is None:
            if debug:
                print("%s RE: %s match not found" % (cls_str,self.name))
            return None
        if debug:
            print("%s RE: %s match found: '%s'" % (cls_str,self.name,mo.group()))
        return self.cls(mo,self.name)

    # This method allows the most recently tested part to be inspected if the 
    # parse should continue.  Missing required parts are detected here as well.
    # Method Arguments:
    #   part    A Part object
    #   n       The part being tested by the SeqParser object
    #   pos     Position in the string of the failing part
    # Returns:
    #   -1      If this optional part is missing, parse continues with next PartRE
    #   n       A value supplied by the part
    # Exceptions:
    #   SequentialError if this resquired part is missing.
    def test(self,part,n,pos):
        if part is None:
            if not self.optional:
                raise SequentialError(\
                    msg="RE '%s' failed for part: %s " % (self.name,n),n=n,pos=pos)
            else:
                return n+1
        return part.test(n)


# This class provides support for parsing of a string into individual parts.
# Instance arguments: None
#  Methods:
#   RE      defines and adds a regular expression recognizing a part
#   parse   parses a string into recognized parts
class SeqParser(object):
    def __init__(self):
        self.res=[]             # regular expressions used for sequential parsing

    # Defines and adds to the sequence a regular expression identifyin a part
    # Method Arguments:
    #   name       A string identifying the pattern used in the search
    #   re         The regular expression being used in the search
    #   cls        If specified the class is used to create a matching part.  
    #              Defaults to Part.
    #   optional   Specify True is the part is optional.  Otherwise it is required.
    # Returns: None
    # Excpetions: None
    def RE(self,name,re,cls=None,optional=False):
        repart=PartRE(name,re,cls=cls,optional=optional)
        self.res.append(repart)

    # Parse a string into its constituent parts.
    # Method Arguments:
    #   string     The string being parsed
    # Returns:
    #   a list of Part (or Part subclass) objects.  Missin optional parts are
    #   represented by a None object.
    # Exceptions:
    #   SequentialError if a required Part is not recognized
    def parse(self,string,debug=False):
        parts=len(self.res)   # Number of parts available for recognition
        if parts==0:          # If no parts defined, return an empty part list
            cls_str=assembler.eloc(self,"parse",module=this_module)
            raise ValueError("%s no parts defined for recognition" % cls_str)
        pos=0                 # Current position in string being recognized
        cur_part=0            # Current PartRe being recognized
        result=[]
        while True:
            # A value in excess of the available parts terminates the part
            if cur_part>=parts:
                break
            partre=self.res[cur_part]
            part=partre.match(string,pos,debug=debug)
            cont=partre.test(part,n=cur_part,pos=pos)
            # If this does not raise a SequentialError, then we can add the result
            result.append(part)
            if part is not None:
                pos=part.end
            if cont is None:
                break
            if cont<0:
                cur_part+=1
            else:
                cur_part=cont
            if cont>=parts:
                break

        return result
        
    # Returns the part name for a specific part
    def part(self,n):
        repart=self.res[n]
        return repart.name

# Class used to search a string for a pattern
# Instance arguments:
#   name    A string identifying the pattern used in the search
#   pattern The regular expression being used in the search
#   cls     If specified the class is used to create a matching part.  Defaults to Part
# Methods:
#   search  Searches a string for a pattern
class SeqSearch(object):
    def __init__(self,name,pattern,cls=None):
        self.name=name
        self.restr=re
        self.rec=re.compile(pattern)
        if cls is None:
            self.cls=Part
        else:
            self.cls=cls

    # Searches a string for a pattern.
    # Method Arguments:
    #   string   The string being searched
    # Returns:
    #   a list of matching substring as a Part or specified class object.
    #   If no matches found, the list is empty.
    def search(self,string):
        pos=0
        found=[]
        while True:
            mo=self.rec.search(string,pos)
            if mo is not None:
                p=self.cls(mo,self.name)
                found.append(p)
                pos=p.end
            else:
                break
        return found


if __name__ == "__main__":
    # Comment out the following statement to perform tests.
    raise NotImplementedError("seqparser.py - intended for import use only")
    
    # Test the SeqSearch object
    searcher=SeqSearch("symbol","&[a-z]")
    syms=searcher.search("this string has a symbole here &a and one here &b")
    for s in syms:
        print(s)
    s="this string has no symbols"
    try:
        syms=searcher.search(s)
    except SequentialError:
        print("search found no substrings as expected in '%s'" % s)

    # Test the SeqParser object
    parser=SeqParser()
    parser.RE("number","([0-9]+)(,)")
    parser.RE("string","('[^']+')( |$)")
    syms=parser.parse("9,'a string' and more")
    for s in syms:
        print(s)
    for s in syms:
        print(s.groups)
    syms=parser.parse("9,'a string'")
    for s in syms:
        print(s)
    for s in syms:
        print(s.groups)
