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

# This module provides support for the creation of report listings.

# Python imports:
import time       # Access data/time formatting tools
# SATK imports: None
# ASMA imports: None

this_module="listing.py"

# Base class for the definition of a column.
#
# The format string method parsing is broken in Python 3.3 and some later versions.
# For this reason the % syntax is used to implement these methods.  At a later date
# use of the format method will likely simplify this class.
class Column(object):

    # For a given integer, return the number of characters required to display it.
    @staticmethod
    def dec_size(value):
        return len("%d" % value)

    # For a given integer, return the number of hex digits required to display it.  
    @staticmethod
    def hex_size(value):
        return len("%X" % value)

    def __init__(self,format="%s",just="left",trunc=True,\
                 size=1,sep=0,colnum=0,default=None):
        self.colnum=colnum       # Column number starting with 0
        self.sep=sep             # Number of characters separating the next column
        self.setSeparator(sep)   # Set the separator spaces
        self.format=format       # string method format() string for value
        self.size=size           # size of the column into which value is placed
        # Allow truncation after justification (the default)
        # or fail if string doesn't fit.
        self.trunc=trunc
        self.default=default     # Default value for column (useful for constants)
        try:
            self.justify={"left":self.left,
                          "right":self.right,
                          "center":self.center}[just]
        except KeyError:
            cls_str="%s %s.__init__() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'just' argument must be either 'left', 'right' or "
                "'center': %s" % (cls_str,just))

    def __len__(self):
        return self.sep+self.size

    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__,self.colnum)

    def center(self,string):
        s=string.center(self.size)
        if len(s)>self.size:
            if self.trunc:
                return s[:self.size]
            else:
                cls_str="%s %s.center() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s - 'string' argument too long to center, "
                    "maximum is  %s: %s" % (cls_str,self.size,len(s)))
        return s

    def left(self,string):
        s=string.ljust(self.size)
        if len(s)>self.size:
            if self.trunc:
                return s[:self.size]
            else:
                cls_str="%s %s.center() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s - 'string' argument too long to left justify, "
                    "maximum is  %s: %s" % (cls_str,self.size,len(s)))
        return s

    def right(self,string):
        s=string.rjust(self.size)
        if len(s)>self.size:
            if self.trunc:
                return s[len(s)-self.size:]
            else:
                cls_str="%s %s.center() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s - 'string' argument too long to right justify, "
                    "maximum allowed is %s: %s" % (cls_str,self.size,len(s)))
        return s

    def setSeparator(self,length):
        self.spaces=length * " "

    # This method creates a string conforming to the column's formating.  Special
    # handling must be subclassed.
    def string(self,value=None):
        if value is None:
            if self.default is not None:
                data=self.default
            else:
                data=self.size * " "
                return "%s%s" % (data,self.spaces)
        else:
            data=value
        data=self.format % data
        data=self.justify(data)
        return "%s%s" % (data,self.spaces)

class CharCol(Column):
    def __init__(self,size,just="left",trunc=True,sep=0,colnum=0,default=None):
        super().__init__(just=just,trunc=trunc,size=size,sep=sep,\
            colnum=colnum,default=default)

class DateCol(Column):
    def __init__(self,format="%d %b %Y",just="left",trunc=True,sep=0,colnum=0):
        now=time.localtime()     # now is an instance of struct_time.
        string=time.strftime(format,now)
        super().__init__(just=just,trunc=trun,size=len(string),sep=sep,\
            colnum=colnum,default=string)

class DateTimeCol(Column):
    def __init__(self,format="%d %b %Y %H:%M:%S",just="left",trunc=True,sep=0,colnum=0):
        now=time.localtime()     # now is an instance of struct_time.
        string=time.strftime(format,now)
        super().__init__(just=just,trunc=trunc,size=len(string),sep=sep,\
            colnum=colnum,default=string)

class DecCol(Column):
    def __init__(self,maximum=1,trunc=True,sep=0,colnum=0):
        width=Column.dec_size(maximum)
        spec="%s%sd" % ("%",width)
        super().__init__(format=spec,just="right",trunc=trunc,size=width,\
            sep=sep,colnum=colnum)

class HexCol(Column):
    def __init__(self,maximum=1,trunc=True,sep=0,colnum=0):
        width=Column.hex_size(maximum)
        spec="%s0%sX" % ("%",width)
        super().__init__(format=spec,just="right",trunc=trunc,size=width,\
            sep=sep,colnum=colnum)

class TimeCol(Column):
    def __init__(self,format="%H:%M:%S",just="left",trunc=True,sep=0,colnum=0):
        now=time.localtime()     # now is an instance of struct_time.
        string=time.strftime(format,now)
        super().__init__(just=just,trunc=trun,size=len(string),sep=sep,\
            colnum=colnum,default=string)

class Group(Column):
    def __init__(self,columns=[],just="left",sep=0,colnum=0):
        self.columns=[]
        self.sep=sep        # Separation of this column group from the next
        self.grpsize=0      # Number of characters presently in the group.
        self.done=False     # Set when no more columns can be added.

        # Initizalize myself
        for n in columns:
            self.column(n)
        self.done=True      # Can't add any more 
        super().__init__(self,just=just,size=self.grpsize,sep=self.sep,colnum=colnum)

    def __len__(self):
        return self.grpsize+self.sep

    def __str__(self):
        s=""
        for n in self.columns:
            s="%s %s" % (s,n)
        return s[1:]

    # Add a column to the group
    def column(self,col):
        if not isinstance(col,Column):
            cls_str="%s %s.column() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s 'col' argument must be an instance of Column: %s" \
                % (cls_str,col))

        if self.done:
            cls_str="%s %s.column() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s column group full and/or completed" % col.colnum)

        colwidth=col.size+col.sep

        # Add the column to the group
        col.colnum=len(self.columns)
        self.grpsize+=colwidth
        self.columns.append(col)

    def string(self,values=[]):
        if len(values)>len(self.columns):
            cls_str="%s %s.string() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s number of values exceeds number of columns "
                "(%s): %s" % (cls_str,len(self.columns),len(values)))
        s=""
        for ndx in range(len(values)):
            col=self.columns[ndx]
            val=values[ndx]
            #print("Group.string() - [%s] %s.string(%s)" % (ndx,col,val))
            colstr=col.string(val)
            s="%s%s" % (s,colstr)
        s=self.justify(s)
        return s

# The Title ojbect is a Group of groups.  The left group appears at the left
# margin of the line.  The right group appears at the right margin.  The title
# appears centered within the page.  The right group has as its minimum 'Page nnnn'
# Additional column may preceded the page number in the right group.
class Title(object):
    def __init__(self,linesize,pages):
        self.linesize=linesize
        self.pages=pages
        self.pageno=0

        self.left=None       # Left column group
        self.right=None      # Right column group
        self.title=None      # Title to be placed in Title line (change with setTitle)

    def __len__(self):
        return self.linesize

    def __str__(self):
        s=  "Title left:  %s\n" % self.left
        s="%sTitle:       %s\n" % (s,self.title)
        s="%sTitle right: %s"   % (s,self.right)
        return s

    def setLeft(self,columns=[]):
        self.left=Group(columns)

    def setRight(self,columns=[]):
        pg=CharCol(4,sep=1,default="Page")
        num=DecCol(maximum=self.pages)
        rcols=columns
        rcols.extend([pg,num])
        self.right=Group(rcols)

    def setTitle(self,string):
        title=string.strip()
        ctitle=string.center(self.linesize)
        leftsize=0
        if self.left is not None:
            leftsize=len(self.left)
        rightsize=0
        if self.right is not None:
            rightsize=len(self.right)
        title_size=self.linesize-(leftsize+rightsize)
        if title_size<len(title):
            cls_str="%s %s.setTitle() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s not enough room in line for title")
        ctitle=ctitle[leftsize:self.linesize-rightsize]
        self.title=CharCol(title_size,default=ctitle)

    def string(self,left=[],right=[]):
        s=self.left.string(values=left)

        s="%s%s" % (s,self.title.string())

        rval=right
        self.pageno+=1
        rval.extend([None,self.pageno])

        s="%s%s" % (s,self.right.string(rval))
        if len(s)!=self.linesize:
            cls_str="%s %s.string() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s title not entire line (%s): %s" \
                % (cls_str,self.linesize,len(s)))
        return s


#
#  +---------------------------+
#  |                           |
#  |   Listing Manager Class   |
#  |                           | 
#  +---------------------------+
#

# This class manages creation of listings.  It is expected to be subclassed by a user
# that instantiates other classes or their subclasses found in this module.  It deals
# strictly in entire output lines.  It expects to provide all line formatting
# characters.  The report is built in memory and returned to the subclass or written
# to a file.  It operates on a "pull" design.  The lines are requested from the
# subclass as the listing file needs them, hence "pulling" them from the subclass.
#
# There is no requirement to utilize the various Column related classes when using
# this class.  The interface here are strings.  The Column classes are intended to 
# assist a subclass in constructing the individual detail and title lines.
class Listing(object):
    def __init__(self,linesize=132,lines=55):
        self.linesize=linesize    # Maximum size of a line in the listing
        self.lines=lines          # Lines per page
        self.report=[]            # Lines later merged into a string
        self.pagelines=0

    # Completes the listing file by returning the report as a string or, if
    # filename is provided, writes the report to the file.  In this latter case
    # None is returned.
    def __eor(self,filename=None,filemode="wt"):
        lines="".join(self.report)
        if filename is None:
            return lines

        try:
            fo=open(filename,filemode)
        except IOError:
            cls_str="%s %s.__eor() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s could not open listing file for writing: %s"\
                % filename) from None

        try:
            fo.write(lines)
        except IOError:
            cls_str="%s %s.__eor() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s could not completely write listing file: %s" \
                % (cls_str,filename)) from None

        try:
            fo.close()
        except IOError:
            cls_str="%s %s.__eor() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s could not close listing file: %s" \
                % (cls_str,filename))

    # Output a single line, while performing top of form output.
    def __line(self,line):
        if self.pagelines==0:
            self.__new_page()
        outline="%s\n" % line.rstrip()
        self.report.append(outline)
        self.pagelines+=1
        if self.pagelines>self.lines:
            self.pagelines=0  # Generate a title next time around

    # Outputs a new page title and heading line
    def __new_page(self):
        title=self.title()
        title=title.rstrip()
        line="\f%s\n" % title
        self.report.append(line)
        self.pagelines=1
        self.space(n=1)
        line=self.heading()
        self.__line(line)
        self.space(n=1)

    # Subclass must generate a detail line when requested.  Return None when the
    # listing is complete.  Return an empty string to cause the listing to space.
    def detail(self):
        cls_str="%s - %s.init() -" % (this_module,self.__class__.__name__)
        raise NotImplementedError("%s subclass must provide detail() method" % cls_str)

    # This will force the subclass to generate a new title line.  It must be called
    # by the subclass before the detail line is returned and will cause the returned
    # detail line to follow a new title line.
    def eject(self):
        self.pagelines=0

    # Generate the report and return it as a string if filename is not provided,
    # otherwise write the listing to the supplied filenmame with supplied filemode.
    def generate(self,filename=None,filemode="wt"):
        self.report=[]
        self.pagelines=0

        while True:
            det=self.detail()
            #print("listing.generates det: '%s'" % det)
            if det is None:
                return self.__eor(filename,filemode=filemode)
            self.__line(det)

    # Subclass must generate a heading line when requested.
    def heading(self):
        cls_str="%s - %s.init() -" % (this_module,self.__class__.__name__)
        raise NotImplementedError("%s subclass must provide heading() method" % cls_str)

    # Returns the number of lines remaining on the current page.
    def remaining(self):
        return self.lines-self.pagelines

    # Inject an empty line into the listing
    def space(self,n=1):
        for x in range(n):
            self.__line("")

    # Subclass must generate a title line when requested.
    def title(self):
        cls_str="%s - %s.init() -" % (this_module,self.__class__.__name__)
        raise NotImplementedError("%s subclass must provide title() method" % cls_str)

if __name__ == "__main__":
    raise NotImplementedError("listing.py - intended for import use only")
