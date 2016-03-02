#!/usr/bin/python3
# Copyright (C) 2013-2015 Harold Grovesteen
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
    def __init__(self,now=None,format="%d %b %Y",just="left",trunc=True,sep=0,colnum=0):
        if now is None:
            n=time.localtime()     # now is an instance of struct_time.
        else:
            n=now
        string=time.strftime(format,n)
        super().__init__(just=just,trunc=trun,size=len(string),sep=sep,\
            colnum=colnum,default=string)

class DateTimeCol(Column):
    def __init__(self,now=None,format="%d %b %Y %H:%M:%S",just="left",\
                 trunc=True,sep=0,colnum=0):
        if now is None:
            n=time.localtime()     # now is an instance of struct_time.
        else:
            n=now
        string=time.strftime(format,n)
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

    def setTitle(self,string,center=False):
        leftsize=0
        if self.left is not None:
            leftsize=len(self.left)
        rightsize=0
        if self.right is not None:
            rightsize=len(self.right)
        title_size=self.linesize-(leftsize+rightsize)

        if center:
            title=string.strip()
            ctitle=title.center(self.linesize)
            if title_size<len(title):
                cls_str="%s %s.setTitle() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s not enough room in line for title")
            else:
                ctitle=ctitle[leftsize:self.linesize-rightsize]
        else:
            ctitle=string.rstrip()
            if title_size<len(ctitle):
                ctitle=ctitle[:title_size]

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
        self.pagelines=0          # Number of detail lines on this page
        self.first_page=True      # Indicates whether this is the first new page

    # Completes the listing file by returning the report as a string or, if
    # filename is provided, writes the report to the file.  In this latter case
    # None is returned.
    def __eor(self,filename=None,filemode="wt"):
        # Add a final FF to report
        if self.report:
            self.report.append("\f")
        lines="".join(self.report)
        if filename is None:
            return lines

        try:
            fo=open(filename,filemode)
        except IOError:
            raise ValueError("%s could not open listing file for writing: %s"\
                % (eloc(self,"__eor"),filename)) from None

        try:
            fo.write(lines)
        except IOError:
            raise ValueError("%s could not completely write listing file: %s" \
                % (eloc(self,"__eor"),filename)) from None

        try:
            fo.close()
        except IOError:
            raise ValueError("%s could not close listing file: %s" \
                % (eloc(self,"__eor"),filename))

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
        if self.first_page:
            self.first_page=False
            ff=""
        else:
            ff="\f"
        line="%s%s\n" % (ff,title)
        self.report.append(line)
        self.pagelines=1
        self.space(n=1)
        line=self.heading()
        self.__line(line)
        self.space(n=1)

    # Subclass must generate a detail line when requested.  Return None when the
    # listing is complete.  Return an empty string to cause the listing to space.
    def detail(self):
        raise NotImplementedError(
            "%s subclass must provide detail() method" % eloc(self,"detail"))

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
        raise NotImplementedError(\
            "%s subclass must provide heading() method" % eloc(self,"heading"))

    # Returns the number of lines remaining on the current page.
    def remaining(self):
        return self.lines-self.pagelines

    # Inject an empty line into the listing
    def space(self,n=1,eject=False):
        if eject and self.pagelines+n>self.lines:
            self.pagelines=0
            return
        for x in range(n):
            self.__line("")

    # Subclass must generate a title line when requested.
    def title(self):
        raise NotImplementedError(\
            "%s subclass must provide title() method" % eloc(self,"title"))


# This object is used by the Multiline object to simplify managing different portions
# of the listing.
class ListingPart(object):
    def __init__(self,more,header=None,init=None):
        self.init=init             # A listing part's initialization callback method
        self.more=more             # A listing part's more callback method
        self.header=header         # A listing part's header callback method


# This object is used in conjunction with the Listing Manager to allow multiple lines
# to be generated and returned individually to the manager object.  Additionally,
# it provides support for different listing parts and sources of header lines and
# detail lines.
#
# When the buffer is empty it will call a user supplied bound callback method,
# retrieving more lines.  The method must support one argument, this object.  When a
# line or lines are generated, the callback method must call this object's own more()
# method to buffer the lines.  If no additional report lines are required, the method
# should simply return without calling the more() method.
#
# The user supplied more callback method must do one of the following:
#   1. Supply one or more lines via the Multline.more() method.  The same method
#      will be called the next time the buffer is empty.
#   2. Supply one or more lines and terminate the listing with 
#      Multiline.more(done=True).
#   3. Change to another more method by calling Multiline.details(method).
#   4. Return without adding lines to the listing and thereby ending the listing.
#
# A more method that returns lines using option one but really expects to be
# called only once will result in a infinite loop.
#
# Instance Argument:
#   report   The subclass of Listing that creates the report
#   details  Specifies a method for generating more detail lines when more lines are
#            needed.  Required.
#   header   Specifies a new method to be called when a header is required.
class Multiline(object):
    def __init__(self, report,details=None, header=None):
        assert isinstance(report,Listing),\
            "%s 'report' argument must be a Listing object: %r" \
                % (eloc(self,"__init__"),report)

        self._report=report    # The Listing subclass generating the report
        self._more=details     # Method called when buffer needs more lines
        self._header=header    # Header method called when a header is required.
        self._in_more=False    # Flag detecting when in the user's more callback.
        self._done=False       # Force end when buffer empty.  DO NOT CALL more()!

        # Listing Parts
        self._parts=[]         # List of ListingPart objects
        self._parts_done=False # List part definitions completed
        self._parts_ndx=0      # Index of next part to be created
        self._part_done=False  # Whether the current part is done

        # More than one detail line may be created.  The following list is used to 
        # buffer such details lines until requested by the detail() method.
        self._buffer=[]

    # Start a new listing part
    # Returns:
    #   False   if listing is _not_ at the end
    #   True    if listing _is_ at the and being terminated
    def _part(self):
        try:
            pt=self._parts[self._parts_ndx]
        except IndexError:
            # index exceeds parts list membership - listing is done
            self.details(None,header=None,cont=False)
            return True

        self._parts_ndx+=1    # Point to next part of the listing
        if pt.init is not None:
            pt.init()         # Initialize this part of the listing
        # Reset multiline callbacks
        self.details(pt.more,header=pt.header,cont=True)
        if pt.header is not None:
            # If a new header is being used, force an eject
            self._report.eject()
        self._part_done=False   # This new part is not done (just starting it)
        return False

    # Return a detail line from the buffer.
    #
    # Exception:
    #   IndexError  raised when the bugger is empty.
    def _pop(self):
        det=self._buffer[0]
        del self._buffer[0]
        return det

    # Provide a detail line to the buffer.
    #
    # Method Argument:
    #   lines   a single string or list of strings being added to the report
    def _push(self,lines,trace=False):
        if __debug__:
            if trace:
                cls_str=eloc(self,"_push")
                print("%s push(%s)" % (cls_str,lines))

        if isinstance(lines,list):
            for n in lines:
                if not isinstance(n,str):
                    if __debug__:
                        if trace:
                            raise ValueError(\
                                "%s detail buffer must only contain strings: %s" \
                                    % (eloc(self,"_push"),n.__class__.__name__))

                self._buffer.append(n)

            if __debug__:
                if trace:
                    print("%s push list\n    %s" % (cls_str,self._buffer))
        else:
            if not isinstance(lines,str):
                raise ValueError("%s detail buffer must only contains strings: %s" \
                    % (eloc(self,"_push"),lines.__class__.__name__))
            self._buffer.append(lines)
            if __debug__:
                if trace:
                    print("%s push string\n    %s" % (cls_str,self._buffer))

    # Return a detail line from the buffer generating more lines when needed
    # This is used strictly within the user's own detail() method when responding
    # to the Listing Manager's request for a detail line.
    #
    # This method is used within a Lister subclass supplied detail method like this:
    #
    #   def detail(self):
    #       return multiline.detail()
    def detail(self, trace=False):
        if self._in_more:
            raise NotImplementedError("%s detail() method must not be called while "
                "in 'more()' method" % eloc(self,"detail"))
        if __debug__:
            if trace:
                cls_str=eloc(self,"detail")

        # Normally, the while ends by returning a line from the buffer
        # If it does not, the self._cont is inspected to see if a new more() method
        # has been registered and we need to see if it provides any new input.  If
        # this second attempt fails to generate data in the input buffer, None is
        # returned to indicate the listing is complete.
        while True:
            if len(self._buffer)==0:
                if self._done:
                    break
                else:
                    if self._part_done:
                        # Previous call to my more() method indicated the current
                        # part was done.  So initialize and set callbacks for the
                        # next part.
                        if self._part():
                            # When _part returns True, the listing is done
                            return None
                    self._in_more=True
                    self._more(self)
                    self._in_more=False
            try:
                det=self._pop()
                if __debug__:
                    if trace:
                        print("%s detail: '%s'" % (cls_str,det))
                return det
            except IndexError:
                if self._cont:
                    self._cont=False
                    continue
                # Buffer is still empty after previous attempt to fill it, so we are 
                # really done.  return None
                return None
        return None

    # Change the more lines or header callback methods.
    # Method Argument
    #   detail   The new 'more()' callback method supplying detail lines.
    #   header   An optional new header callback method.  Specify a new header method.  If
    #            None is specified, the header method remains unchanged.  If a
    #            report eject is required, it must be driven by the subclass of
    #            Listing directly using this object.  Defaults to None
    #   cont     If True, retry with the new method for more lines.  Default is True.
    #
    # This is used in a more callback method to change the source of details lines
    # and, optionally, the source of the report header line when the currently
    # used more callback has determined it is at the end of its portion of a 
    # report.
    def details(self, detail,header=None,cont=True):
        # Update the header callback method if provided
        if header is not None:
            self._header=header
        # Update the more callback methid (required)
        self._more=detail
        # Specify whether the report is being continued or terminated.
        self._cont=cont

    # Use the supplied header method callback.
    # Returns:
    #    the string returned by the callback method
    #
    # Note a Lister subclass will normally use this method in the subclass supplied
    # heading method, like this:
    #   def heading(self):
    #       return self.multiline.header()
    def header(self):
        return self._header()

    # Add one or more detail lines to the buffer for report creation.
    # Method Arguments:
    #   lines    One or more lines to be added to the listing
    #   partdone If True, this part is done.
    #   done     If True, the user's 'more()' method is not called again, ending the
    #            listing.
    def more(self, lines=[],partdone=False,done=False):
        self._push(lines)
        self._done=done
        self._part_done=partdone

    # Start the next part of the listing by changing callbacks.
    def nextpart(self):
        if not self._in_more:
            raise NotImplementedError("%s nextpart() method must only be called "
                "from within a more callback method" % eloc(self,nextpart))
        end=self._part()
        return end

    # Define the callbacks used for the first part.  
    def start(self):
        if self._parts_ndx!=0:
            raise NotImplementedError("%s start() method must only be called for "
                "the first part, next part index: %s" \
                    % (eloc(self,"start"),self._parts_ndx))
        else:
            if len(self._parts)==0:
                raise ValueError("%s no listing parts defined")
        if not self._parts_done:
            # Initialize the first part. Not done with part(last=True)
            self._part()

    # Define a listing part
    # Method Arguments:
    #    more    Listing part detail callback method.  Required.
    #    header  Listing part header callback method.  Defaults to None.
    #    init    Listing part initialization callback method.  Defaults to None.
    #    last    Indicate this is the last part.  Automatically performs start
    def part(self, more,init=None,header=None,last=False):
        if self._parts_done:
            raise NotImplementedError(\
                "%s last listing part defined, more parts may not be added" \
                    % eloc(self,"part"))

        pt=ListingPart(more,header=header,init=init)
        self._parts.append(pt)
        if last:
            self._parts_done=True   # Don't allow part() method to be called again.
            self._part()            # Initialize the callbacks for the first part


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
