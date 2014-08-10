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

# This module provides support for the Statement Oriented Parameter Language.  This
# simple language forms the basis for the Machine Specification Language (MSL).

# Python imports: None
# SATK impoorts:
import satkutil      # Access path_open class

#
#  +--------------------------+
#  |                          |
#  |   SOPL Error Exception   |
#  |                          |
#  +--------------------------+
#

class SOPLError(Exception):
    def __init__(self,loc=None,msg=""):
        self.msg=msg                    # Text associated with the error
        if isinstance(loc,Line):
            self.source=loc.source      # get Source object from the Line object
        elif isinstance(loc,Source):
            self.source=loc             # use supplied Source object
        else:
            self.source=None

        string=""
        if self.source is not None:
            string="%s" % self.source
        if len(string)>0:
            string="%s " % string
        if len(self.msg)>0:
            string="%s%s" % (string,self.msg)
        super().__init__(string)

#
#  +-----------------------------+
#  |                             |
#  |   Input File Line Objects   |
#  |                             |
#  +-----------------------------+
#

# This is the output of the readfile() method
class Line(object):
    def __init__(self,source,stmt):
        self.text=stmt        # input line of stripped text
        self.source=source    # Source object of input text
    def __str__(self):
        string="%s" % self.source
        if len(string)>0:
            string="%s " % string
        return "%s%s" % (string,self.text)
    def isStmt(self):
        return self.text[0]!=" "

# This encapsulates statement location information for consistent reporting
class Source(object):
    def __init__(self,fileno=None,lineno=None):
        self.fileno=fileno
        self.lineno=lineno
    def __str__(self):
        # This results in the following location strings
        # [lineno]-fileno            
        # [lineno]                   fileno is None
        # or no position             fileno and line are both None
        string=""
        if self.lineno is not None:
            string="[%s]" % self.lineno
            if self.fileno is not None:
                string="%s-%s" % (string,self.fileno)
        return string

#
#  +------------------------------------+
#  |                                    |
#  |   Intermediate Statement Objects   |
#  |                                    |
#  +------------------------------------+
#

# Encapsulates a Parmeter line and its attributes into a single object
class Parameter(object):
    def __init__(self,aline):
        # statement is an instance of Line
        self.aline=aline       # The statement or paramter Line object
        self.source=aline.source  # Source of this element
        
        units=aline.text.split()
        if len(units)==0:
            cls_str="msldb.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s Parameter contains zero text units, SHOULD NOT OCCUR")
        self.units=units
        self.typ=None
        self.attr=[]
        self.parse_units()

    def dump(self,indent="",string=True):
        s="%sPARM:  type:%s  attr:%s" % (indent,self.typ,self.attr)
        if string:
            return s
        print(s)

    def parse_units(self):
        #     [0]       [1]...    self.unit indexes  
        #  parm-type  attributes
        self.typ=self.units[0]
        self.attr=self.units[1:]

# Encapsulates a statement, its attributes and related parameter lines
class Statement(Parameter):
    def __init__(self,aline,stmtd):
        self.ID=None           # Statement identifier
        self.parms=[]          # Parameters are added as they are encountered

        super().__init__(aline)
        if len(self.units)<2:
            raise SOPLError(loc=aline.source,\
                msg="statement requires at least two text units in line: %s" \
                    % len(units))

        try:
            self.valid_parms=stmtd[self.typ]
        except KeyError:
            raise SOPLError(loc=self.source,\
                msg="invalid statement type: %s" % self.typ)

    def addParm(self,aline):
        el=Parameter(aline)
        if el.typ not in self.valid_parms:
            raise SOPLError(loc=el.source,\
                msg="invalid parameter type for %s statement: %s" % (self.typ,el.typ))
        self.parms.append(el)

    def dump(self,indent="",string=False):
        s="STMT:  type:%s  ID:%s attr:%s" % (self.typ,self.ID,self.attr)
        lcl="%s    " % indent
        for x in self.parms:
            s="%s\n%s" % (s,x.dump(indent=lcl,string=True))
        if string:
            return s
        print(s)

    def parse_units(self):
        #     [0]       [1]         [2]...      self.unit indexes  
        #  stmt-type  stmt-id   attributes
        self.typ=self.units[0]
        self.ID=self.units[1]
        if len(self.units)>2:
            self.attr=self.units[2:]

#
#  +-------------------------------------------+
#  |                                           |
#  |   Statement Oriented Parameter Language   |
#  |                  (SOPL)                   |
#  |                                           |
#  +-------------------------------------------+
#

# This is the base class for all languages based upon SOPL.  A specific instance of
# SOPL will subclass this class.  The language registers with the base class its
# statements and parameters.
#
# Instance arguments:
#   variable   Environment variable to be used for include file searches.  Default
#              is 'PATH' environment variable.
#   default    Default directory if path environment variable is missing
#   debug      Specify True to enable PathMgr debugging
class SOPL(object):
    def __init__(self,variable="PATH",default=None,debug=False):
        self.fail=False         # If True fail immediately on an error
        self.soplpath=variable  # Environment variable used for includes
        self.opath=\
            satkutil.PathMgr(variable=self.soplpath,default=default,debug=debug)

        # This is a dictionary of statement line id's mapped to a list of valid
        # parameter line id's.  It is built by the subclass calling regStmt() method.
        self.statements={}

        # Generated during processing of statements and parameters.
        self.errors=[]           # List of SOPLError objects for messages
        self.warnings=[]         # List of SOPLError objects treated as warnings

        # Attributes supplied by SOPL.readfile() method
        self.lines=[]            # List of stripped Line objects
        self.files=[]            # list of include files.
        # Attribute supplied by SOPL.pre_process() method.  Return by getStmts() method
        self.stmts=[]            # List of Statement objects

        # Used by __badchars() method to detect invalid input characters.
        translate="\x00" * 0x20                               # 32 chars   (0x20)
        translate="%s%s" % (translate,"\xFF" * (0x7F-0x20))   # 95 chars   (0x5F)
        translate="%s%s" % (translate,"\x00" * (0x100-0x7F))  # 129 chars  (0x81)
        if len(translate)!=256:
            raise ValueError("translate table is not 256 bytes: %s" % len(translate))
        self._translate=translate # Used to detect invalid characters

        # Force subclass to register its statements
        self.register()          # Subclass calls regStmt() method in this method 

    # Make sure an input line contains only valid ASCII characters
    def __badchars(self,source,string):
        good=string.translate(self._translate)
        try:
            index=good.index("\x00")
            self._do_error(self,line=source,msg="contains one or more invalid "
                "character starting at position: %s" % index)
            return True
        except ValueError:
            pass
            # no binary zeros, so all are good
        return False

    # Process 'include' statement during pre-processing
    def __do_include(self,source,stmt):
        parts=stmt.split()
        if len(parts)>2:
            self._do_error(line=source,\
                msg="too many arguements in 'include' statement: %s" % len(parts))
        self.__readfile(parts[1],line=source)

    # Recognize a comment  or empty line
    def __is_comment(self,text):
        if len(text)==0:
            return True
        cont=text[0]
        return cont in ["#","*"]

    # Convert Line objects from readfile() method into Statement objects.
    def __pre_process(self,debug=False):
        stmtd=self.statements
        stmt=None
        for x in self.lines:
            if x.isStmt():
                if stmt is not None:
                    self.stmts.append(stmt)
                try:
                    stmt=Statement(x,stmtd)
                except SOPLError as me:
                    self._do_error(error=me)
            else:
                try:
                    stmt.addParm(x)
                except SOPLError as me:
                    self._do_error(error=me)
        if stmt is not None:
            self.stmts.append(stmt)
        if debug:
            self.dumpStmts()

    # Read, honoring include statements, the primary input file.
    def __readfile(self,filename,line=None):
        try:
            abspath,fo=self.opath.ropen(filename,variable=self.soplpath)
        except ValueError:
            self._do_error(line=line,
                msg="could not open for reading file: %s" % filename)
            return                  # just return if file does not open

        # Ignore previously included file
        if abspath in self.files:
            self._do_warning(line=line,\
                msg="file may not be included more than once, ignored: %s" % abspath)
            fo.close()              # close the open file without reading it
            return

        self.files.append(abspath)
        fileno=len(self.files)
        lineno=0
        try:
            for lin in fo:
                lineno+=1
                if len(lin)==0:
                    continue

                # Drop the line termination
                if lin[-1]=="\n":
                    text=lin[:-1]
                else:
                    text=lin
                #print("text: '%s'" % text)

                # If now empty without the line termination, ignore it too
                if len(text)==0:
                    continue

                # Ignore a comment line
                cont=text[0]
                if cont in ["#","*"]:
                    continue

                # Look for and remove a comment at the end of a line
                try:
                    comment=text.index("#")
                    stmt=text[:comment-1]
                except ValueError:
                    try:
                        comment=text.index("*")
                        stmt=text[:comment-1]
                    except ValueError:
                        stmt=text

                # Most likely, now have some text needing to be processed
                source=Source(fileno=fileno,lineno=lineno)

                # Generate an error is bad characters in line and cease processing it
                if self.__badchars(source,stmt):
                    continue   # Error message queued so just ignore it here

                # Remove any trailing blanks (between statment and comment/end-of-line)
                stmt=stmt.rstrip()  # Remove trailing blanks.
                if len(stmt)==0:
                    continue

                # Look for an include statement and include it
                if len(stmt)>7 and stmt[0:7]=="include":
                    self.__do_include(source,stmt)
                    # The include statement itself is removed from the input
                    continue

                # This is a valid statement or parameter line add it for processing
                ln=Line(source,stmt)
                self.lines.append(ln)

        except IOError:
            self._do_error(line=line,\
                msg="problem reading input file: %s" % filename)
        try:
            fo.close()
        except IOError:
            self._do_error(line=line,\
                msg="could not properly close input file: %s" % filename)

        # self.lines contains the list of recognized Line objects

    # Removes an comment at the end of a line
    def __remove_comment(self,text):
        try:
            comment=text.index("#")
            stmt=text[:comment-1]
        except ValueError:
            try:
                comment=text.index("*")
                stmt=text[:comment-1]
            except ValueError:
                stmt=text
        return stmt

    # Execute the -f, --fail protocol during pre-processing
    def _do_error(self,line=None,msg="",error=None):
        if error is None:
            e=SOPLError(loc=line,msg=msg)
        else:
            e=error
        if self.fail:
            raise e from None
        self.errors.append(e)

    # Treat an error as a warning
    def _do_warning(self,line=None,msg="",error=None):
        if error is None:
            e=SOPLError(loc=line,msg=msg)
        else:
            e=error
        self.warnings.append(e)

    def dumpLines(self):
        print("Input Lines:")
        for x in self.lines:
            print(x)

    def dumpStmts(self):
        print("Input Statements:")
        for x in self.stmts:
            x.dump()

    # Returns the list of identified Statement objects.
    def getStmts(self):
        return self.stmts

    # Provides status of build errors.
    #  Returns True if errors present.  Otherwise returns False.
    def isErrors(self):
        return len(self.errors)>0

    # This method is the logical equivalent of recognize, except file inclusions
    # are not recognized.  It is strictly for the use of an embedded multiline string
    # obviating the need for paths or filenames.
    def multiline(self,string,fail=False,debug=False):
        if not isinstance(string,str):
            cls_str="sopl.py - %s.multiline() -" % self.__class__.__name__
            raise ValueError("%s 'string' argument must be a string: %s" \
                % (cls_str,string))

        self.fail=fail
        # Separate string into individual lines without ends
        lines=string.splitlines()
        lineno=0
        for line in lines:
            lineno+=1
            if self.__is_comment(line):
                continue
            stmt=self.__remove_comment(line)
            source=Source(lineno=lineno)
            # Generate an error is bad characters in line and cease processing it
            if self.__badchars(source,stmt):
                continue   # Error message queued so just ignore it here

            # Remove any trailing blanks (between statment and comment/end-of-line)
            stmt=stmt.rstrip()  # Remove trailing blanks.
            if len(stmt)==0:
                 continue

            ln=Line(source,stmt)
            self.lines.append(ln)
        if debug:
            self.dumpLines()
        # SOPL processes text into Statement and Parameter objects
        self.__pre_process(debug=debug)
        # Access Statement and Parameter objects via getStmts() method

    # prints out queued errors
    def printErrors(self):
        if len(self.errors)>0:
            for e in self.errors:
                print(e)

    # prints out queued warnings
    def printWarnings(self):
        if len(self.warnings)>0:
            for e in self.warnings:
                print(e)

    # This is the primary method used to recognize a SOPL based language.
    def recognize(self,filename,fail=False,debug=False):
        if not isinstance(filename,str):
            cls_str="sopl.py - %s.recognize() -" % self.__class__.__name__
            raise ValueError("%s 'filename' argument must be a string: %s" \
                % (cls_str,filename))
        self.fail=fail
        self.__readfile(filename,line=None)
        if debug:
            self.dumpLines()
        # SOPL processes text into Statement and Parameter objects
        self.__pre_process(debug=debug)
        # Access Statement and Parameter objects via getStmts() method

    # Subclass provided method for registering statement types and associated
    # parameter lines.
    def register(self):
        raise NotImplementedError("subclass %s must provide register() method" \
            % self.__class__.__name__)

    # Registers a statement type and its associated parameter lines.  Called by
    # subclass from its supplied register() method.
    def regStmt(self,typ,parms=[]):
        if not isinstance(parms,list):
            raise ValueError("'parms' argument must be a list: %s" % parms)
        try:
            stmt=self.statements[typ]
            raise ValueError("statement type already registered: %s" % typ)
        except KeyError:
            self.statements[typ]=parms
