#!/usr/bin/python3
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

# Other Notices:
# z/Architecture is a registered trademark of International Business Machines 
# Corporation.

# This module provides an Python based mainframe assembler for the creation of 
# binary omage files from a simple source language.  It is intended for import use 
# only.  Use asma.py for a command line interface.

#
#  +---------------------+
#  |                     |
#  |   ASMA Highlights   |
#  |                     |
#  +---------------------+
#

# The following information assumes a measure of familiarity with mainframe
# assemblers.

# ASMA specific behavior
#  - Instuction mnemonics and assembler directives are case insensitive
#  - EQU second optional operand allows explicit specification of equate symbol
#    length.
#  - ORG only operates with relative addresses within the active CSECT or DSECT
#  - REGION statement specific to ASMA.
#  - Multiple START statements allowed supporting multiple region
#
# Supported assembler directives: 
#    CCW, CCW0, CCW1, CSECT, DC, DROP, DS, DSECT, END, EQU, ORG, PRINT, REGION, 
#    START, TITLE, USING, various PSW formats.
#
# All machine instruction formats are supported through 2012.  Specific instructions
# are defined in a separate file that constitutes the Machine Specification Language
# database.  Only instruction supported in the input MSL file are supported for a
# given execution of the assembler.
#
# Supported storage/constant types: A, AD, B, C, CA, CE, D, F, FD, H, P, S, X, Y, Z 
# 
# Limitations from traditional mainframe assembler
#  - D constant type is a synonym for FD.  Floating point constants are not supported.
#  - Only the assembler directives identified above are supported
#  - Only the storage/constant types identified above are supported
#
# Summary of assembler pass processing
#
#  Pass 0 - Statement Parsing - statement() method
#  ------
#
#  The first pass on a statement occurs when it is submitted to the assembler via the
#  statement() method.  The statement is separated into fields and the operands are
#  parsed using the parsers in the asmparsers, asmfsmbp or asmfsmcs modules.  The
#  output of this pass is a list of Stmt class instances upon which the other passes
#  incrementally create the final output.
#
#  Pass 1 - Relative Addressing - assemble() method
#  ------
#
#  During pass 1 all CSECT's, DSECT'S and REGION's are established.  ORG statements
#  are acted upon.  Relative addresses are asigned to image content generating 
#  statements and associated symbols.  CSECT's are bound to physical addresses
#  with their respective regions and regions are located within the final image.
#  Note: actual binary image content has yet to be built.
#
#  Pass 2 - Object Generation - assemble() method
#  ------
#
#  All expressions that have not as of yet been evaluted are done so.  The results
#  are used to create the object content of constants and machine instructions.  At
#  the end of the pass, all object content is consolidated into their respective 
#  regions and CSECTS.  The regions are concatenated together to in the sequence 
#  of their START statements to form the final output.

this_module="assembler.py"

# ASMA version tuple:
asma_version=(0,1,0)

# This method returns a standard identification of an error's location.
# It is expected to be used like this:
#
#     cls_str=assembler.eloc(self,"method")
# or
#     cls_str=assembler.eloc(self,"method",module=this_module)
#     raise Exception("%s %s" % (cls_str,"error information"))
#
# It results in a Exceptin string of:
#     'module - class_name.method_name() - error information'
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)

#
#  +---------------------------+
#  |                           |
#  |   Statistics Management   |
#  |                           | 
#  +---------------------------+
#

# Python imports early for statistics
import time          # Access to local time, process timer and wall clock timer

class AsmStats(object):
    def __init__(self):
        self.timers={}       # Active timers
        self.stmts=None      # Number of statements processes
        
        # These three timers may be updated with better times from an external source.
        # asma.py understands how to update these timers.  Use it as an example
        # for use of ASMA in a different embedded context.

        # Overall process timers
        self.proc_timer("process")
        self.start("process")
        self.wall_timer("wall")
        self.start("wall")
        # Import timers, may be updated from external source with better times
        self.proc_timer("import_p")
        self.wall_timer("import_w")
        # Instantiation timers
        self.proc_timer("objects_p")
        self.wall_timer("objects_w")

        # The remaining timers are managed by ASMA and should not be updated
        # from any external source.

        # Assembly processing
        self.proc_timer("assemble_p")
        self.wall_timer("assemble_w")
        # Pass 0 timers
        self.proc_timer("pass0_p")
        self.wall_timer("pass0_w")
        # Pass 1 timers
        self.proc_timer("pass1_p")
        self.wall_timer("pass1_w")
        # Pass 2 timers
        self.proc_timer("pass2_p")
        self.wall_timer("pass2_w")
        # Output creation timers
        self.proc_timer("output_p")
        self.wall_timer("output_w")

    def __format(self,total,timer=None,time=None):
        if timer is None:
            val=time
        else:
            val=self.report_time(timer)
        pc=(val/total)*100
        pc="%7.4f" % pc
        pc=pc.rjust(8)
        return "%s  %s" % (pc,val)

    def __fetch(self,tname,method_name):
        try:
            return self.timers[tname]
        except KeyError:
            raise ValueError("%s %s timer does not exist" \
                % (eloc(self,method_name),tname))
            
    # Returns whether a timer has been created
    def available(self,tname):
        try:
            self.timers[tname]
        except KeyError:
            return False
        return True    

    # Returns a timer's elapsed time. 
    def elapsed(self,tname):
        timer=self.__fetch(tname,"running")
        return timer.elapsed()

    # Create a process timer
    def proc_timer(self,tname):
        try:
            timer=self.timers[tname]
            raise ValueError("%s timer already created: %s" \
                % (eloc(self,"proc_timer"),timer))
        except KeyError:
            self.timers[tname]=AsmProcTimer(tname)

    # Report the available statistics.  An external source of better information
    # should perform the timer updates before calling this method.  Calling this
    # method will implicitly stop the overall timers 'process' and 'wall'.  Calling
    # this method should be the very last thing done by the reporting module before
    # exiting completely.
    def report(self):
        stmts=self.stmts
        total="\nTotal statements: %s\n" % stmts

        wt=self.report_time("wall")
        pt=self.report_time("process")
 
        assembly=self.report_time("assemble_w")
        string="%s\nWall Clock    percent   seconds" % total
        string="%s\n  total       %s" % (string,self.__format(wt,time=wt))
        string="%s\n    import    %s" % (string,self.__format(wt,timer="import_w"))
        string="%s\n    objects   %s" % (string,self.__format(wt,timer="objects_w"))
        string="%s\n    assembly  %s" % (string,self.__format(wt,time=assembly))
        string="%s\n      pass 0  %s" % (string,self.__format(wt,timer="pass0_w"))
        string="%s\n      pass 1  %s" % (string,self.__format(wt,timer="pass1_w"))
        string="%s\n      pass 2  %s" % (string,self.__format(wt,timer="pass2_w"))
        string="%s\n      output  %s" % (string,self.__format(wt,timer="output_w"))
        string="%s\n      rate    %7.4f  (stmt/sec)\n" % (string,stmts/assembly)

        assembly=self.report_time("assemble_p")
        string="%s\nProcess       percent   seconds" % string
        string="%s\n  total       %s" % (string,self.__format(pt,time=pt))
        string="%s\n    import    %s" % (string,self.__format(pt,timer="import_p"))
        string="%s\n    objects   %s" % (string,self.__format(pt,timer="objects_p"))
        string="%s\n    assembly  %s" % (string,self.__format(pt,time=assembly))
        string="%s\n      pass 0  %s" % (string,self.__format(pt,timer="pass0_p"))
        string="%s\n      pass 1  %s" % (string,self.__format(pt,timer="pass1_p"))
        string="%s\n      pass 2  %s" % (string,self.__format(pt,timer="pass2_p"))
        string="%s\n      output  %s" % (string,self.__format(pt,timer="output_p"))
        string="%s\n      rate    %7.4f  (stmt/sec)" % (string,stmts/assembly)

        return string
        
    # Returns a timer's elapsed time.  If the timer has not been stopped it stops
    # it and provides a warning.  If the timer was never started it returns None.  
    def report_time(self,tname):
        timer=self.__fetch(tname,"running")
        if not timer.started():
            return None
        if not timer.stopped():
            print("%s WARNING: stopping timer for reporting: %s" \
                % (eloc(self,"report_time"),tname))
            timer.stop()
        return timer.elapsed()

    # Returns whether a timer is running
    def running(self,tname):
        timer=self.__fetch(tname,"running")
        return timer.running()

    # Set a timer's start time from an external source
    def set_start(self,tname,start):
        timer=self.__fetch(tname,"set_start")
        timer.set_start(start)

    # Set a timer's stop time from an external source
    def set_stop(self,tname,stop):
        timer=self.__fetch(tname,"set_stop")
        timer.set_stop(stop)

    # Start a timer
    def start(self,tname):
        timer=self.__fetch(tname,"start")
        timer.start()

    # Returns True if timer is started
    def started(self,tname):
        timer=self.__fetch(tname,"started")
        return timer.started()

    # Supply the number of assembler statements processed for per/statement stats
    def statements(self,number):
        assert isinstance(number,int),\
            "%s 'number' argument must be an integer: %s"\
                % (eloc(self,"statements"),number)

        self.stmts=number

    # Stop a timer
    def stop(self,tname):
        timer=self.__fetch(tname,"stop")
        timer.stop()

    # Returns True if timer is stopped
    def stopped(self,tname):
        timer=self.__fetch(tname,"stoped")
        return timer.stopped()

    # Update a timer with a better start time
    def update_start(self,tname,time,force=False):
        timer=self.__fetch(tname,"update_start")
        timer.update_start(time,force=force)

    # Update a timer with a better end time
    def update_stop(self,tname,time,force=False):
        timer=self.__fetch(tname,"update_stop")
        timer.update_start(time,force=force)

    # Create a wall-clock timer
    def wall_timer(self,tname):
        try:
            timer=self.timers[tname]
            cls_str=eloc(self,"wall_timer")
            raise ValueError("%s timer already created: %s" % (cls_str,timer))
        except KeyError:
            self.timers[tname]=AsmWallTimer(tname)


# This class implements a single usage timer.  Once created it may be started once
# and stopped once.  After which it may be report the elapsed process time between
# the time is was started and the time it was stopped.
# Note: the elapsed time is _not_ wall-clock time.
class AsmTimer(object):
    def __init__(self,name):
        self.name=name
        self.begin=None
        self.end=None

    def __str__(self):
        return "%s('%s',begin=%s,end=%s)" \
            % (self.__class__.__name__,self.name,self.begin,self.end)

    # Return the current time.  The subclass controls how the time is acquired and the
    # type of time being monitored.
    def _get_time(self):
        raise NotImplementedError("%s subclass %s must implement _get_time() method" \
            % (eloc(self,"_get_time"),self.__class__.__name__))

    # Return the time elapsed time is fractional seconds
    def elapsed(self):
        assert self.begin is not None,\
            "%s %s timer has not been started" % (eloc(self,"elapsed"),self.name)
        assert self.end   is not None,\
            "%s %s timer is still running" % (eloc(self,"elapsed"),self.name)

        return self.end-self.begin

    # Set the timer's start time from an external time source, causing timer to be
    # in the running state.
    def set_start(self,time):
        assert not self.running(),\
            "%s %s timer is already running" % (eloc(self,"set_start"),self.name)

        self.begin=time

    # Set the timer's end time from an external time source, causing the running
    # timer to enter the stopped state.
    # Method argument:
    #   time   A time value of the correct time for the timer
    def set_stop(self,time):
        assert self.running(),\
            "%s %s timer is not running" % (eloc(self,"set_start"),self.name)
        assert time>=self.begin,\
            "%s %s 'time' argument must be less than start time (%s): %s" \
                % (eloc(self,"set_start"),self.name,self.begin,time)

        self.end=time

    # Start the timer
    def start(self):
        assert not self.started(),\
            "%s %s timer already started" % (eloc(self,"start"),self.name)

        self.begin=self._get_time()

    # Returns True if timer is running
    def running(self):
        return self.started() and not self.stopped()

    # Returns True if the time has been started
    def started(self):
        return self.begin is not None

    # Stop the timer
    def stop(self):
        assert not self.stopped(),\
            "%s %s timer already stopped" % (cls_str,self.name) \
                % (eloc(self,"stop"),self.name)

        self.end=self._get_time()

    # Returns True if the timer is stopped
    def stopped(self):
        return self.end is not None

    # Update with a better start time
    def update_start(self,time,force=False):
        if not self.started():
            self.begin=time
            return
        if time<self.begin:
            self.begin=time
        else:
            if not force:
                return
            if time>self.end:
                self.begin=self.end
            else:
                self.begin=time

    # Update with a better stop time
    def updates_stop(self,time,force=False):
        if not self.stopped():
            self.end=time
            return
        if time>self.end:
            self.begin=time
        else:
            if not force:
                return
            if time<self.begin:
                self.end=self.begin
            else:
                self.end=time


# A timer for process time consumption
class AsmProcTimer(AsmTimer):
    def __init__(self,name):
        super().__init__(name)
    def _get_time(self):
        return time.process_time()


# A timer for wall-clock time consumption
class AsmWallTimer(AsmTimer):
    def __init__(self,name):
        super().__init__(name)
    def _get_time(self):
        return time.time()

Stats=AsmStats()
Stats.start("import_p")
Stats.start("import_w")

# Python imports
import functools     # Allow sorting of instances
import os.path       # Access to path management for AsmOut.
import re            # Regular expression support
import sys           # Need hexversion attribute and exit function

# SATK imports - PYTHONPATH must include tools/lang, tools/ipl
import satkutil      # Useful miscelaneous functionality
import codepage      # Access ASCII/EBCDIC code pages
import hexdump       # Useful ad hoc dumping of binary data
import lang          # Access SATK language tools Interface for the symbol table
from LL1parser import ParserAbort      # Access the exception
from seqparser import SequentialError  # Access the exception

#
#  +--------------------------------------------+
#  |                                            |
#  |  ASMA Shared Regular Expression Patterns   |
#  |                                            | 
#  +--------------------------------------------+
#

# These definitions provide consistency between different modules definitions
# Note: These module attributes must be defined before other imported ASMA modules 
# access them when imported below. These should move to asmfsmbp.py module
char="\$@_"                         # Special characters used in names
multiline="(?m)"                    # Turns on multiline for start/end match
cmt="\*|\.\*"                       # An asterisk or a period followed by an asterisk
inst="[a-zA-Z]+[0-9]*"              # An instruction pattern
ws="[ \t\r\f\v]"                    # White space characters
stuff=".*"                          # Stuff at the end of the line
opend="([ ]|$)"                     # End of operands, a space or end of string

# Label pattern with special chracters
label="[a-zA-Z%s][a-zA-Z0-9%s]*" % (char,char)

# ASMA imports (do not change the sequence)
import asmbin       # Access binary output generator
import asmcards     # Access the line continuation handler
import asminput     # Access the input handler for the assembler
import asmlist      # Access the assembler listing generator
import asmmacs      # Access the macro framework
import asmparsers   # Access all of my parsers of statement operands
import expression   # Access to Pratt parser interface
import insnbldr     # Access the machine instruction construction machinery
import asmfsmbp     # Access the finite state machine parsing technology
import asmfsmcs     # Access objects related to context sensitive parsing
import msldb        # Access the Format class for type checking

Stats.stop("import_w")
Stats.stop("import_p")


#
#  +--------------------------------+
#  |                                |
#  |   Assembler Parser Exception   |
#  |                                | 
#  +--------------------------------+
#

# This exception is used by parsers to indicate a problem encountered in Parsing
# See modules asmfsmbp.py and asmfsmcs.py for usage

class AsmParserError(Exception):
    def __init__(self,token,msg=""):
        self.msg=msg         # Text associated with the error
        self.token=token     # Lexcal token in error.

        string=""
        if len(self.msg)>0:
            string="%s: " % self.msg
        string="%s%s" % (string,self.token)
        super().__init__(string)

#
#  +-------------------------------------+
#  |                                     |
#  |   Assembler User Error Exceptions   |
#  |                                     | 
#  +-------------------------------------+
#

# This excpetion is used to discontinue processing and report a user generated
# error.  These errors are user correctable.  All ofther excpetions raised by this 
# module represent unexpected situations encountered by the assembler and require
# programming corrections.

class AssemblerError(Exception):
    @staticmethod
    def sort(item):
        if item.line is None:
            return 0
        return item.line
    def __init__(self,source=None,line=None,linepos=None,msg="",info=False):
        assert line is None or isinstance(line,int),\
            "%s 'line' argument must be None or integer:\n    line: %s\n    msg='%s'"\
                % (eloc(self,"__init__"),line,msg)

        self.msg=msg         # Text associated with the error
        self.linepos=linepos # Error location in the line
        if source is not None:
            source.linepos=linepos  # Position relative to start of the line
        self.source=source   # source statement source information generating the error
        self.line=line       # Global statement number of Line where the error occurred
        self.info=info       # If True, not an error, an informational message

        # This results in the following location strings
        # [line] @[line:pos]-fileno  source is present
        # [line:linepos]             line and position in line is availalbe
        # [line]                     only line is available
        # or no position             line and source are both None
        src=""
        string=""
        if self.source:
            src=" @%s" % self.source
        if self.line:
            if self.linepos:
                string="[%s:%s]" % (self.line,self.linepos)
            else:
                string="[%s]%s" % (self.line,src)
        if len(string)>0:
            string="%s " % string
        if len(self.msg)>0:
            string="%s%s" % (string,self.msg)
        super().__init__(string)


# This exception is also raised in the event of a user related problem.  It has the
# identical arguments as the AssemblerError exception.  However, this exception is
# never caught by the assembler.  The user of the assembler may want to do some
# orderly cleanup.
class AssemblerAbort(Exception):
    def __init__(self,line=None,linepos=None,msg="ASMA ABORT!"):
        self.msg=msg         # Text associated with the error
        self.line=line       # Line in the string where the error occurred
        self.linepos=linepos # Position relative to start of the line

        string=""
        if self.linepos is not None:
            string="%s[%s:%s]" % (string,self.line,self.linepos)
        elif self.line is not None:
            string="%s[%s]" % (string,self.line)
        if len(self.msg)>0:
            string="%s %s" % (string,self.msg)
        super().__init__(string)

#
#  +-----------------+
#  |                 |
#  |   Label Error   |
#  |                 | 
#  +-----------------+
#

class LabelError(Exception):
    def __init__(self,label,ltok=None,msg=""):
        self.ltok=ltok       # Lexical token where label occurs
        self.label=label     # Label for which error is detected
        self.msg="%s: %s" % (msg,self.label)
        super().__init__(self.msg)


#
#  +---------------------------------------+
#  |                                       |
#  |   Statement Operand Related Classes   |
#  |                                       | 
#  +---------------------------------------+
#

# This class is the base class for managing an instruction's or assembler directive's
# operands.  Each operand in the source input is convered into a subclass of Operand.
class Operand(object):
    def __init__(self,name):
        self.name=name       # An operand name.  
        #For MSLDB Format the source sfield (without a number) is the name.

        # These attributes hold the state of the validation results, good or bad
        self.source=0b000    # From validate_source() method
        self.exprs=[]        # From validate_source() method
        self.fields=0x000    # From validate_expr() method (valid and invalid)

        # Evaluated expressions.  Only an Address or int object is returned by 
        # expression evalution.  Attribute is set by the evaluate() method
        self.values=[None,None,None]

        # Address for listing set by resolve() method 
        self.laddr=None

    def __str__(self):
        return '%s("%s",exprs: %s,repr=%s)' \
            % (self.__class__.__name__,self.name,self.exprs,repr(self))

    def evaluate(self,debug=False,trace=False):
        cls_str="assembler.py - %s.evaluate() -" % self.__class__.__name__
        values=[]
        if trace:
            print("%s %s.exprs: %s" % (cls_str,self,self.exprs))
        for n in range(len(self.exprs)):
            exp=self.exprs[n]
            if exp is None:
                values.append(None)
                continue
            exp.evaluate(debug=debug,trace=trace)
            #value=exp.value
            # I can trust the result to be either an integer or Address
            values.append(exp.value)
        if len(values)==3:
            self.values=values
        else:
            raise ValueError("%s %s expression values not three: %s" \
                % (cls_str, self, values))

    # This method is used by the instruction builder to extract a machine field's
    # value based upon its type.
    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() subclass must supply field() method" \
            % cls_str)

    # This method is used by assembler directives to retrieve the results of 
    # evaluating the operand.
    def getValue(self):
        cls_str="assembler.py - %s.getValue() -" % self.__class__.__name__
        raise NotImplementedError("%s getValue() method not supported by this operand" \
            % cls_str)

    def resolve(self):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported by this operand" \
            % cls_str)

    # Returns a string for reporting a failure to pass validate_source() method
    def source_error(self):
        cls_str="asmparsers.py - %s.source_error() -" % self.__class__.__name__
        raise NotImplementedError("%s source_error() method not supported by this "
            "operand" % cls_str)

    # Validates the types resulting from the expression evaluation.
    # Return:
    #   True   if type is valid for each expression
    #   False  if any of the expressions evaluates to an unexpected result
    def validate_expr(self,trace=False):
        if trace:
            cls_str="assembler.py - %s.validate_expr() -" % self.__class__.__name__
            print("%s values: %s" % (cls_str,self.values))
        state=0
        opr=0xF00
        shift=0
        for val in self.values:
            if trace:
                print("%s value: %s" % (cls_str,val))
            if val is None:
                typ=0x000
            elif isinstance(val,int):
                typ=0x100
            elif isinstance(val,Address):
                typ=0x200
            else:
                typ=0x300
            typ_shifted=typ>>shift
            if trace:
                print("%s typ: %s" % (cls_str,hex(typ_shifted)))
            state|=(typ>>shift)
            if trace:
                print("%s state: %s" % (cls_str,hex(state)))
            shift+=4
        self.fields=state
        valid=self.__class__.valid_expr
        if trace:
            print("%s valid_expr: %s" % (cls_str,valid))
        return state in valid

    # Validates that the list of Expression instances in the Parsed instance makes
    # sense for this operand. This validate source input structure.  Parser is trusted
    # because of its checks in CommonParser.operand_done() method.  This means that 
    #  - None     -> expression missing in source input
    #  - not None -> expression.Expression object derived from source
    # This validation is done in pass 1.  Whether the expressions evaluate into
    # correct values (addresses vs integers) occurs in pass 2 with the validate_expr()
    # method()
    # Return:
    #   True   if structure of the source operand is valid for this operand
    #   False  if unexpected expression encountered.
    def validate_source(self,exprs,trace=False):
        if trace:
            cls_str="assembler.py - %s.validate_source() -" % self.__class__.__name__
            print("%s operand: %s" % (cls_str,self))
        state=0
        opr=0b100
        for exp in exprs:
            if trace:
                print("%s exp: %s" % (cls_str,exp))
            if exp is not None:
                state|=opr
            if trace:
                print("%s state: %s" % (cls_str,bin(state)))
            opr=opr>>1
            if trace:
                print("%s mask: %s" % (cls_str,bin(opr)))
        self.source=state
        self.exprs=exprs
        if trace:
            print("%s %s exprs: %s" % (cls_str,self,self.exprs))
        valid=self.__class__.valid_source
        if trace:
            print("%s valid_source: %s" % (cls_str,valid))
        return state in valid

    # Returns a string for reporting a failure to pass validate_expr() method
    def value_error(self):
        cls_str="assembler.py - %s.value_error() -" % self.__class__.__name__
        raise NotImplementedError("%s value_error() method not supported by this "
            "operand" % cls_str)

# This class supports a single statement operand that must evaluate to an integer
# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                          self.values list
#   fields     Source statement syntax             [0]    [1]    [2]
#
#   0x100 -  integer-expression                   [int,   None, None]
class Single(Operand):
    valid_expr=[0x100,]
    valid_source=[0b100,]        # int -> register or mask or immediate

    def __init__(self,name):
        super().__init__(name)
        self.immediate=None

    # Return operand values for 'I', 'M' or 'R' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ in ["I","M","R","RI"]:
            return self.immediate
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Returns this single operand's value.  Used by assembler directives
    def getValue(self):
        return self.values[0]

    # This is used by machine instructions to finalize immediate/masks/regs
    def resolve(self,asm,line,opn,trace=False):
        self.immediate=self.values[0]

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must not be an address (error=%s): %s" \
            % (hex(self.fields),self.values[0])

# This class supports a single statement operand that must evaluate to an address
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]
#   0x200 -  DSECT-Address-expression             [isDummy(),    None, None]
class SingleAddress(Operand):
    valid_expr=[0x200,]
    valid_source=[0b100,]        # Address -> directive address
    def __init__(self,name):
        super().__init__(name)

    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() method not supported for directive "
            "only operand" % cls_str)

    # Returns this single operand's value.
    def getValue(self):
        return self.values[0]

    def resolve(self,asm,stmt,opn,trace=False):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported for directive "
            "only operand" % cls_str)

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must be an address (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x100 -  integer-expression                   [int,          None, None]
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]  
#   0x200 -  DSECT-Address-expression             [isDummy(),    None, None]
class SingleAny(Operand):
    valid_expr=[0x100,0x200,]
    valid_source=[0b100,]    # Address or integer       -> directive operand
    def __init__(self,name):
        super().__init__(name)

    def field(self,typ):
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise NotImplementedError("%s field() method not supported for directive "
            "only operand" % cls_str)

    # Returns this single operand's value.
    def getValue(self):
        return self.values[0]

    def resolve(self,asm,stmt,opn,trace=False):
        cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
        raise NotImplementedError("%s resolve() method not supported for directive "
            "only operand" % cls_str)

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "unexpected value (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that must evaluate to an address
# This class supports a single statement operand that can evaluate to either an
# address or an integer.
#
#    self.                                              self.values list
#   fields     Source statement syntax             [0]           [1]   [2]
#
#   0x200 -  CSECT-Address-expression             [isAbsolute(), None, None]
class SingleRelImed(Operand):
    valid_expr=[0x200,]
    valid_source=[0b100,]     
    def __init__(self,name):
        super().__init__(name)
        self.relimed=None
        self.isladdr=True

    # Return operand value for 'RI' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ == "RELI":
            return self.relimed
        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Returns this single operand's target destination
    def getValue(self):
        cls_str="assembler.py - %s.getValue() -" % self.__class__.__name__
        raise NotImplementedError("%s getValue method not supported for instruction "
            "only operand" % cls_str)

    # Resolve instruction field values in preparation for instruction construction
    def resolve(self,asm,stmt,opn,trace=False):
        dest=self.values[0]
        if not dest.isAbsolute:
            raise AssemblerError(line=stmt.lineno,\
                msg="operand %s (%s) encountered unexpected %s as relative "
                    "target: %s" % (opn,self.name,dest.description(),dest))
        self.laddr=dest        # Save for listing
        binary=stmt.content
        relative=dest-binary.loc
        relative_abs=max(relative,-relative)
        halfwords,excess=divmod(relative_abs,2)
        if excess:
            raise AssemblerError(line=stmt.lineno,\
                msg="operand %s (%s) encountered unexpected odd value as relative "
                    "target: %s" % (opn,self.name,relative))
        
        self.relimed=relative//2

    def source_error(self):
        return "unexpected index and/or base register specified (error=%s)" \
            % self.source

    def value_error(self):
        return "must be an address (error=%s): %s" % (hex(self.fields),self.values[0])

# This class supports a single statement operand that takes the form of a simple
# storage reference.  It supports the following constructs:
#
#    self.                                              self.values list     Base
#   fields     Source statement syntax             [0]       [1]   [2]
#
#   0x100 -  disp                                 [int1,       None, None]     0
#   0x110 -  disp(base)                           [int1,       int2, None]    int2
#   0x200 -  region-address                       [isAbsolute, None, None]   implied
#   0x200 -  DSECT-Address                        [isDummy,    None, None]   implied
#   0x210 -  region-address(base)                 [isAbsolue,  int,  None]     int
#   0x210 -  DSECT-Address(base)                  [isDummy,    int,  None]     int
#
# Note: 0x210 is equivalent to 0x200 with expicit USING statement.  Is this useful?
#
# Preparing this operand for presentation to the machinery that builds machine
# instructions requires the following actions:
#
#    Operand.evaluate()    - Builds self.values list from self.operands,
#    Storage.resolve()     - establishes all values explicit or implied
class Storage(Operand):
    valid_expr=[0x100,0x110,0x200,0x210]
    valid_source=[0b100,     # Address/int, None, None  ->  UA/Disp (UA=base implied)
                  0b110]     # Address/int, int, None   ->  UA/Disp,base

    # Displacement size.  Used for both Storage and StorageExt
    disp_size={"S":12,"SY":20,"SL":12,"SR":12,"SX":12,"SYL":20,"SYX":20}
    def __init__(self,name):
        super().__init__(name)
        self.size=Storage.disp_size[self.name]   # Set the displacement field size
        self.base=None       # This is the base register that resolves for address
        self.disp=None       # This is the displacement that resolves for address

    # Return operand values for 'B' or 'D' type machine fields
    # Results depend upon the resolve() having completed its work.
    def field(self,typ):
        if typ == "B":                  # Used by source type: S and SY
            return self.base
        if typ == "D":                  # Used by source type: S
            return self.disp
        if typ == "DH":                 # Used by source type: SY
            return self.disp // 4096
        if typ == "DL":                 # Used by source type: SY
            return self.disp %  4096

        cls_str="assembler.py - %s.field() -" % self.__class__.__name__
        raise ValueError("%s upsupported machine type requested: %s" \
            % (cls_str,typ))

    # Resolves explicit/implicit values for operand 'opn' in statement number 'line'
    def resolve(self,asm,stmt,opn,trace=False):
        if self.fields==0x100:
            self.base=0
            self.laddr=self.disp=self.values[0]
        elif self.fields==0x110:
            self.base=self.values[1]
            self.laddr=self.disp=self.values[0]
        elif self.fields==0x200:
            # Note, if this fails, an AssemblerError exception is raised.
            dest=self.values[0]
            self.laddr=dest.lval()
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
            self.laddr=dest.address
        elif self.fields==0x210:
            disp=self.values[0]
            if disp.isDummy():
                # Use the DSECT relative address as displacement
                self.disp=disp.lval()
            elif disp.isAbsolute():
                # Use absolute address as displacement
                self.disp=disp.address
            else:
                raise AssemblerError(line=stmt.lineno,\
                    msg="operand %s (%s) encountered unexpected displacement: %s" \
                        % (opn,self.name,disp.description()))

            self.base=self.values[1]
            self.laddr=self.disp=disp
        else:
            cls_str="assembler.py - %s.resolve() -" % self.__class__.__name__
            raise ValueError("%s unexpected self.fields: 0x%03X" \
                % (cls_str,self.fields))
        # Make sure we are good to go before leaving
        if not isinstance(self.base,int) or not isinstance(self.disp,int):
            cls_str=eloc(self,"resolve")
            raise ValueError("%s [%s] could not set base/displacement: %s/%s" \
                % (cls_str,stmt.lineno,self.base,self.disp))

    def source_error(self):
        return "unexpected index register (error=%s)" % self.source

    def value_error(self):
        return "explicit base register must be an integer (error=%s)" \
            % (hex(self.fields),self.values[2])

# This class supports a single statement operand that takes the form of a full
# storage reference.  It supports the following constructs:
#
#    self.                                self.values list       Instruction Usage
#   fields   Source statement syntax   [0]           [1]   [2]  Index/Length    Base
#
#   0x100 -  disp                      [int,        None, None]   0     1        0
#   0x101 -  disp(,base)               [int1,       None, int2]   0     1       int2
#   0x110 -  disp(ndx/len)             [int1,       int2, None]   0    int2       0
#   0x111 -  disp(ndx/len,base)        [int1,       int2, int3]  int2  int2     int3
#   0x200 -  CSECT-Addr                [isAbsolute, None, None]   0  implied   implied
#   0x200 -  DSECT-Addr                [isDummy,    None, None]   0  implied   implied
#   0x210 -  CSECT-Addr(ndx/len)       [isAbsolute, int,  None]  int   int     implied
#   0x210 -  DSECT-Addr(ndx/len)       [isDummy,    int,  None]  int   int     implied
#   0x211 -  DSECT-Addr(ndx/len,base)  [isDummy,    int1, int2]  int1  int1     int2
#
# Base register for an absolute address is implied from the current absolute USING 
# registers assignments.
#
# Base register for DSECT displacements is implied from the current relative USING
# asignments.
#
# Lengths are implied from the expression's root symbol's length.  The expression's
# root symbol is the one to which an integer value is added or subtracted.
class StorageExt(Storage):
    valid_expr=[0x100,0x101,0x110,0x111,0x200,0x210,0x211]
    valid_source=[0b100,     # Address/int, None, None  -> UA/Disp  (UA==base implied)
                  0b110,     # Address/int, int, None   -> UA/Disp,index
                  0b101,     # int, None, int           -> Disp,base
                  0b111]     # int, int, int            -> Disp,index,base
    disp_size={"SL":12,"SX":12,"SYL":20,"SYX":20}
    isIndex=["SX","SYX"]
    def __init__(self,name):
        super().__init__(name)
        # Indicates whether field is an index register (True) or length (False)
        self.isIndex=(name in StorageExt.isIndex)

        self.index=None
        self.length=None
        # self.base, self.disp and self.size and self.isladdr are inherited from
        # Storage superclass.

    def __setNdxLen(self,value):
        if self.isIndex:
            self.index=value
        else:
            self.length=value

    # Return operand values for 'B', 'D', 'DH', 'DL', 'R','X' or 'L' type machine fields
    # Results depend upon the resolve() method having completed its work.
    def field(self,typ):
        if typ == "B":
            return self.base
        elif typ == "D":
            return self.disp   # caller has to sort out DH vs. DL values
        elif typ == "DH":
            return self.disp // 4096
        elif typ == "DL":
            return self.disp %  4096
        elif typ == "R":
            return self.length
        elif self.isIndex and typ == "X":
            return self.index
        else:
            if typ == "L":
                return max(0,self.length-1) 

        raise ValueError("%s upsupported machine type requested: %s index=%s" \
            % (eloc(self,"field"),typ,self.isIndex))

    def resolve(self,asm,stmt,opn,trace=False):
        if self.fields==0x100:
            self.base=0
            self.laddr=self.disp=self.values[0]
            if self.isIndex:
                self.index=0
            else:
                self.length=1
        elif self.fields==0x101:
            self.base=self.values[2]
            self.laddr=self.disp=self.values[0]
            if self.isIndex:
                self.index=0
            else:
                self.length=1
        elif self.fields==0x110:
            self.base=0
            self.laddr=self.disp=self.values[0]
            self.__setNdxLen(self.values[1])
        elif self.fields==0x111:
            self.base=self.values[2]
            self.disp=self.values[0]
            self.__setNdxLen(self.values[1])
        elif self.fields==0x200:
            # Note, if this fails, an AssemblerError exception is raised.
            self.laddr=dest=self.values[0]
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
            if self.isIndex:
                self.index=0
            else:
                self.length=self.values[0].length
        elif self.fields==0x210:
            self.laddr=dest=self.values[0]
            self.base,self.disp=asm._resolve(dest,stmt.lineno,opn,self.size,\
                trace=trace)
            self.laddr=dest.address
            self.__setNdxLen(self.values[1])
        elif self.fields==0x211:
            self.base=self.values[2]
            disp=self.values[0]
            if disp.isDummy():
                # Use the DSECT relative address as displcement
                self.disp=disp.lval()
            elif disp.isAbsolute():
                # Use absolute address as displacement
                self.disp=disp.address
            else:
                raise AssemblerError(line=stmt.lineno,\
                    msg="operand %s (%s) encountered unexpected %s as "
                        "displacement: %s" % (opn,self.name,disp.description()))
            self.laddr=disp
            self.__setNdxLen(self.values[1])
        else:
            raise ValueError("%s unexpected self.fields: 0x%03X" \
                % (eloc(self,"resolve"),self.fields))

        # Make sure we are good to go before leaving
        if not isinstance(self.base,int) or not isinstance(self.disp,int):
            raise ValueError("%s could not set base/displacement: %s/%s" \
                % (cls_str,self.base,self.disp))
        if self.isIndex:
            if not isinstance(self.index,int):
                raise ValueError("%s cound not set index register: %s" \
                    % (cls_str,sle.index))
            else:
                pass
        else:
            if not isinstance(self.length,int):
                raise ValueError("%s cound not set length: %s" \
                    % (cls_str,self.length))

    def source_error(self):
        if self.fields & 0x0F0 == 0x020:
            return "explicit index register must be an integer (error=%s): %s" \
                % (hex(self.fields),self.values[1])
        if self.fields & 0x00F == 0x002:
            return "explicit base register must be an integer (error=%s): %s" \
                % (hex(self.fields),self.values[2])

        raise ValueError("%s unexpected expression value (error=%s): %s" \
            % (eloc(self,"source_error"),hex(self.fields),self.values))

#
#  +--------------------------------+
#  |                                |
#  |   The Statement Fields Class   |
#  |                                | 
#  +--------------------------------+
#

# The assembler and macro languages of ASMA depend upon each statement following
# a basic structure of four fields:
#
# name    operation   operands  comments
#
# Each field other than operation is optional.  The fields are separated by required
# spaces.  Depending upon the context (assembler vs. macro language) and the operation
# certain fields may be required or restricted to specific forms.  This class forms
# the basis for managing and enforcing the the operation specific options.
# It is the base class for determining a statement's field properties.
#
# This class also operates a global scope for the asmfsmbp.FieldParser object.
# This parser is used by the assembler to recognize statement fields and the 
# macro language for the same purpose.  The single instance object informs the
# global scope object as to the context of the parse.  Additional token types are
# allowed in the macro language as opposed to the assembly language.  At the point
# Pass 0 and Pass 1 are merged these differences may go away.
class StmtFields(object):
    def __init__(self):
        # Text from which fields were identified
        self.text=None      # Input text
        self.source=None    # assembler.Source object related to input
        # Comment statement information 
        self.comment=False  # True if a comment statement
        self.silent=False   # True if _also_ a silent comment
        self.empty=False    # Line contains no content

        # Name field type information.  All values will be False if omitted
        self.name_ltok=None # The lexical token associated with the name
        self.label=False    # True if the present name is a location label
        self.labelsym=False # True if the location label contains a symbolic variable
        self.sequence=False # True if the present name is a sequence symbol
        self.symbol=False   # True if the present name is a variable symbol
        # Set based upon the type of name field
        self.name=None      # The name field if a label or sequence symbol is present
        self.symid=None     # SymbolID object of a symbolic variable symbol

        # Operation Field
        self.oper_ltok=None # Operation field lexical token
        self.operation=None # Operation field from statement
        self.opersym=False  # True is the operation field contains a symbolic variable
        self.opuc=None      # Operation in upper case
        self.oppos=None     # Position in line of operation
        
        # Operand and comment field
        self.operpos=None   # Operand starting position in logical line
        self.operands=None  # Operand string and possible comment field
        self.oprnd=None     # StmtOperands object.

    def __str__(self):
        if self.comment:
            return "%s: comment silent=%s" % (self.__class__.__name__,self.silent)

        if self.sequence or self.label:
            name="'%s'" % self.name
        elif self.symbol:
            name="%s" % self.symid
        else:
            name="None"

        return "%s: name=%s, operation='%s' operands='%s'" \
            % (self.__class__.__name__,name,self.opuc,self.operands)

    # This method checks for presence of conditional assembly elements in
    # assembler language statements.  It raises an AssemblerError if present.
    # This method is only used by assembly language processing
    def cond_asm_ck(self,stmt):
        if self.sequence:
            raise AssemblerError(lineno=stmt.lineno,\
                msg="assembly language name field may not contain a sequence "
                "symbol: %s" % self.name)
        if self.labelsym:
            raise AssemblerError(lineno=stmt.lineno,\
                msg="assembly language name field may not contain a symbolic "
                    "variable: %s" % self.name)
        if self.opersym:
            raise AssemblerError(lineno=stmt.lineno,\
                msg="assembly language operation field may not contain a symbolic "
                "variagble: %s" % self.operation)

    # Handle normal line continuation conventions.
    # May raise asmcards.LineError exception
    def normal(self,lineo):
        assert isinstance(lineo,asminput.Line),\
            "%s 'lineo' must be an instance of asminput.Line: %s" \
                % (eloc(self,"normal"),lineo)

        # Handle normal continuation conventions.  May raise asmcards.LineError
        lineo.normal()
        self.text=lineo.text

        if self.operpos is None:
             # No operands detected after operation field so nothing to be done here
             return
        self.oprnd=oprnd=StmtOperands(lineo.logline,self.operpos)
        # This should normalize processing beyond after continuation
        self.operands=oprnd.operands

    # Recognize individual statement fields
    def parse(self,asm,stmt,debug=False):
        if __debug__:
            if debug:
                cls_str=assembler.eloc(self,"parse",module=this_module)
        line=stmt.line
        self.comment=line.comment
        self.silent=line.silent
        self.text=line.text
        self.source=line.source
        self.empty=line.empty

        # Do not parse comment lines or empty lines
        if line.comment:
            self.normal(line)  # Set up listing line
            return
        if line.empty:
            return

        # May raise AssemblerError 
        # Note: This object is its own FSM parser scope object.
        #print("StmtFields.macdefn: %s" % self.macdefn)
        asm.fsmp.parse_statement(stmt,"fields",scope=self)

        # Update various attributes after successful recognition.
        if self.name_ltok is not None:
            self.name_ltok.update(stmt,0,source=stmt.source)
            if self.symbol:
                self.symid=self.name_ltok.SymID(asm.case)
        if self.oper_ltok is not None:
            self.oper_ltok.update(stmt,0,source=stmt.source)
            self.oppos=self.oper_ltok.beg

    # Set the name field information for a sequence symbol from a lexer.Token object
    def NameLabel(self,ltoken):
        self.name_ltok=ltoken
        self.name=ltoken.string
        self.label=True

    # Set the name field information from a lexer.Token object for a label containing
    # a symbolic variable
    def NameLabelSym(self,ltoken):
        self.NameLabel(ltoken)
        self.labelsym=True

    # Set the name field information for a sequence symbol from a lexer.Token object
    def NameSeq(self,ltoken):
        self.name_ltok=ltoken
        self.name=ltoken.string
        self.sequence=True

    # Set the name field information for a symbolic variable with optional subscript
    def NameSym(self,ltoken):
        self.name_ltok=ltoken
        self.symbol=True

    # Extract the operand and commment fields from the input text
    def Operands(self,ltoken):
        self.operpos=ltoken.beg

    # Set the operation field information from a lexical token
    def Operation(self,ltoken):
        self.oper_ltok=ltoken
        string=ltoken.string
        self.operation=string
        self.opuc=string.upper()
        
    # Seth the operation field information from a lexical token that contains a
    # symbolic variable.
    def OperSym(self,ltoken):
        self.Operation(ltoken)
        self.opersym=True

class StmtOperands(object):
    def __init__(self,logline,pos):
        #print("StmtOperands: %s,%s" % (logline,pos))
        assert isinstance(logline,asmcards.LogLine),\
            "%s 'line' argument must be an instance of smcards.LogLine: %s" \
                % (eloc(self,"__init__"),logline)
        assert isinstance(pos,int),\
            "%s 'pos' argument must be an integer: %s" \
                % (eloc(self,"__init__"),pos)        
        
        self.logline=logline             # The asmcards.LogLine object
        self.pos=pos                     # position of operands in logical line
        # Input control object from asmcards.LogLine object
        self.ictl=logline.ictl           # Needed to handle lexical tokens
        logical_line=logline.line        # The entire logical line string
        self.operands=logical_line[pos:] # Extract just the operands

#
#  +-------------------------+
#  |                         |
#  |   The Statement Class   |
#  |                         | 
#  +-------------------------+
#

class Stmt(object):
    # Source statement operand types      Evaluated results of expressions
    types={"I":  Single,                  # unsigned int
           "M":  Single,                  # unsigned int
           "R":  Single,                  # unsigned int
           "RI": Single,                  # signed int
           "RELI": SingleRelImed,         # signed integer 
           "S":  Storage,                 # addr or int(int)
           "SY": Storage,                 # addr or int(int)
           "SR": StorageExt,              # addr or addr(integer) or int(int,int)
           "SL": StorageExt,              # addr or addr(integer) or int(int,int)
           "SX": StorageExt,              # addr or addr(integer) or int(int,int)
           "SYL":StorageExt,              # addr or addr(integer) or int(int,int)
           "SYX":StorageExt}              # addr or addr(integer) or int(int,int)

    def __init__(self,line,trace=False):
        self.line=line                    # asminput.Line object
        line.validate()                   # Validate the logical line
        self.source=line.source           # Input line source info.
        self.lineno=line.lineno           # Global Line number of statement
        # The full statement is available after continuation handling has been done
        self.stmt=None             # original statement string
        self.trace=trace           # Causes statement tracing in all passes
        self.gened=line.macro      # True if statement generated by a macro

        # General state flags.  Once eithr is set True future processing is inhibited
        # Master processing switch.  All passes check this to determine if the 
        # statement should be processed.  
        self.ignore=False          # Ignore if True (empty or comment statements)
        self.error=False           # Assume the statement is good.
        # When setting self.error to True, self.ignore should also be set to True
        self.aes=[]                # List of AssemblerError objects.

        # Listing state flags:
        self.pon=True              # Assume "PRINT ON" directive
        self.pgen=True             # Assume "PRINT GEN" directive
        self.pdata=False           # Assume "PRINT NODATA" directive
        self.plist=None            # Information passed to listing manager
        self.laddr=[]              # Addresses from operand evaluations
        # Note: Assembler directives will set the values as [addr1,addr2].
        # Instructions will set laddr as the address is encountered.  The asmlist
        # module will need to figure out which address is "first" and which is "last"
        # for proper placement in the listing ADDR1 and ADDR2 columns for instructions.
        # During Pass 1 some directives may save some information in the laddr 
        # attribute for use in Pass 2 where the final values are established for some
        # directives.

        # Provided by Assembler.__classifier() method using Stmt.classified()
        # StmtFields object: name, operation, operands and comments
        self.fields=None
        self.label=None            # Label if present, None otherwise
        self.inst=None             # Instruction field of the statement
        self.instu=None            # The instruction/operation field in upper case
        # As the various assembler statements move to their own FSM-based parsers,
        # these attributes will no longer be needed.  They are already established
        # in the StmtFields object
        self.rem=None              # Parsable portion of statement (operand, comment)
        self.rempos=None           # Position in line of remainder

        # Provided by Assembler.__oper_id() method 
        self.insn=None             # MSLentry object of instruction
        self.insn_fmt=None         # msldb.Format instance of instruction's format
        self.asmdir=False          # True means this is an assembler directive
        self.prdir=False           # True means this is a print directive
        self.macro=None            # The asmmacs.Macro object if a macro statement
        self.asmpasses=None        # AsmPasses instance of this instruction
        self.trace=trace           # Causes statement tracing in all passes

        # Provided by Assembler.__parse() method
        # Output from all syntactical analyzer: Parsed object or DSDC object
        self.oprs=[]               # Possible statement operands from create_types
        # Output from syntactical analyzer of found operands.  Must be either a list
        # oof asmparsers.Parsed objects or a scope object from a FSM asmfsmbp parser.
        self.parsed=[]             # Output from syntactical analyzer of found operands

        # This list of Operand subclass objects is used by all users of the 
        # CommonParser.  Throughout the assembly life cycle these objects are
        # updated with additional information.
        #
        #    After parsing      - linked as the Parsed.operand attribute
        #    After __parse      - evaluation ready Expression objects in 
        #                         Operand.exprs list
        #    After evaluation   - evaluated expressions in Operand.values list
        #
        # Evaluation may occur in either Pass 1 or Pass 2 depending on the needs of
        # the statment
        self.operands=[]  

        # This attribute is used to contain a global scope object from a FSM-based
        # parser.  The scope object is specific to the statement operation and is 
        # tightly coupled to the _operation_Pass1() and _operation_Pass2() methods.
        # This is returned by the __parsefsm() method usually called by the
        # _spp_operation() method.  It is the logical equivalent of the previous
        # self.operands attribute following the __parse() method.  Evalutation
        # will update this attribute with results.
        self.gscope=None

        # Provided by Assembler._insn_Pass1() method
        self.format=None           # msldb.Format instance for instruction

        # Binary instance created in pass 1, image data provided in pass 2
        self.content=None          # Binary instance for image content creation

    def __str__(self):
        if self.label:
            lbl='%s' % self.label
        else:
            lbl="None"
        return "Stmt(lineno=%s,label='%s',inst='%s',rem='%s',rempos=%s)" \
            % (self.lineno,self.label,self.inst,self.rem,self.rempos)

    # Update with information from Assembler.__classifier() method in the 
    # StmtFields object it creates.
    def classified(self):
        fields=self.fields
        if fields.empty:
            self.ignore=True
            return

        if fields.comment:
            fields.normal(self.line)
            self.ignore=True
            return

        # Statement operation field
        self.inst=oper=fields.operation
        self.instu=oper.upper()

        # Statement Name field
        if fields.label is not None:
            self.label=fields.name

    def continuation(self):
        if self.ignore:
            return
            
        # Statement operands and comment field
        # Parsers or special pre-processor functions must separate the two 'fields'
        # based upon operation specific knowledge of operands.
        operando=self.fields.oprnd
        if operando is None:
            self.rem=""
            self.rempos=1
        else:
            self.rem=operando.operands
            self.rempos=operando.pos
        self.stmt=self.fields.text

    # Create the list of Operand instances populated by syntactical analysis
    def create_types(self,debug=False):
        cls_str="assembler.py - %s.create_types() -" % self.__class__.__name__

        # Create assembler directive types
        if self.asmdir:
            asmpasses=self.asmpasses
            oprs=[]
            n=1
            if asmpasses.max_operands is not None:
                for x in range(self.num_oprs()):
                    name="I%s" % n
                    #oprs.append(asmparsers.Single(name))
                    cls=asmpasses.operand_cls[x]
                    oprs.append(cls(name))
                    n+=1

            if __debug__:
                if debug:
                    print("%s DEBUG %s.oprs: %s" \
                        % (eloc(self,"create_types"),self.insn,oprs))

            self.oprs=oprs
            return

        # Create machine instruction types
        # Note: self.insn is an MSLentry object
        oprs=self.insn.src_oprs(debug=debug)

        if __debug__:
            if debug:
                print("%s DEBUG %s format %s oprs: %s" % (eloc(self,"create_types"),\
                    self.insn.mnemonic,self.insn_fmt.ID,oprs))

        lst=[]
        for op in oprs:
            cls=Stmt.types[op]

            if __debug__:
                if debug:
                    print("%s DEBUG creating Operand subclass: %s('%s')" \
                        % (eloc(self,"create_types"),cls.__name__,op))

            opro=cls(op)
            lst.append(opro)

        self.oprs=lst

    # Return the location of the statement.  This is the value of the '*' symbol
    def current(self):
        if self.content is None:
            raise AssemblerError(line=self.lineno,\
                msg="current location (*) is undefined")
        contnt=self.content
        if contnt.loc is None:
            raise AssemblerError(line=self.lineno,\
                msg="current location (*) is unassigned")
        return self.content.loc

    # For each Operand instance in self.operands, evalute their values
    def evaluate_operands(self,debug=False,trace=False):
        cls_str="assembler.py - %s.evaluate_operands() -" % self.__class__.__name__
        for n in range(len(self.operands)):
            opr=self.operands[n]

            if __debug__:
                if trace:
                    print("%s operand: %s" % (eloc(self,"evaluate_operands"),opr))

            try:
                opr.evaluate(debug=debug,trace=trace)
            except LabelError as le:
                raise AssemblerError(line=self.lineno,source=self.source,\
                    msg="undefined label: %s" % le.label) from None

            if not opr.validate_expr(trace=trace):
                raise AssemblerError(line=self.lineno,\
                    msg="operand %s %s" % (n+1,opr.value_error()))

    # Get an Operand instance based upon its position in the source starting with 0.
    # May raise an IndexError.  Used by parser callback routines.
    def get_operand(self,ndx):
        opr=self.oprs[ndx]

        if __debug__:
            if self.trace:
                print("%s returning to parser oprs[%s]: %s" \
                    % (eloc(self,"get_operand"),ndx,opr))

        return opr

    # Return the location following this statement
    # Returns:
    #   None            If either Stmt.content or content.loc are None
    #   Address object  The address of the content plus its length
    # This is needed to ensure that the current location counter is updated after
    # a statement.  This is needed for directives that may reference the current
    # location counter but themselves do not have any binary content that tracks
    # the location counter.  This occurs particularly with the EQU directive.
    def next(self):
        content=self.content
        if content is None:
            return
        loc=content.loc
        if loc is None:
            return None
        return loc+len(content)

    # Returns the number of operands required by the statement
    def num_oprs(self):
        return self.asmpasses.num_oprs()

    # Check the correct number of operands are present in the statement and, if 
    # required, the label is present
    def validate(self,trace=False):
        passes=self.asmpasses

        self.validate_label()

        # Check on the number of operands using AsmPasses instance 
        operands=self.num_oprs()
        present=len(self.parsed)
        error=passes.operands_ok(present)

        if error:
            min_num=passes.min_operands
            max_num=passes.max_operands
            opr_str="operand"
            if min_num > 1:
                opr_str="%ss" % opr_str
            if error==1:   # n or more required
                raise AssemblerError(line=self.lineno, \
                   msg="%s requires at least %s %s, found: %s" 
                       % (passes.name,min_num,opr_str,present))
            elif error==2: # n requires
                raise AssemblerError(line=self.lineno,\
                   msg="%s requires %s %s, found: %s" \
                       % (passes.name,min_num,opr_str,present))
            elif error==3: # m-n required
                raise AssemblerError(line=self.lineno,\
                   msg ="%s requires %s-%s operands, found: %s" \
                       % (passes.name,min_num,max_num,present))
            else:
                 raise ValueError("%s instruction %s AsmPasses.operands_ok() " 
                     "returned unexpected problem error number: %s" \
                     % (eloc(self,"validate"),passes.name,error))

        # Validate parsed expressions are valid for the Operand with which they are
        # associate.  All Parsed objects have a three element list (Parsed.exprs)
        # for each of the individual expressions that may be encountered in the
        # operands.  The expressions are identified from the parsed text and may
        # or may not conform with the requirements of the individual assembler
        # directive or machine instruction.  This loop validates that each source
        # text operand conforms to the correct _structure_ for the operand.  
        # Validation of the actual values derived from evaluation of the expression
        # occurs when the expression is evaluated.
        # 
        # Exception:
        #   AssemblerError may be raised if an error is encountered
        for n in range(len(self.parsed)):
            obj=self.parsed[n]
            #if isinstance(obj,asmparsers.DCDS):
            #    self.operands.append(obj)
            #    continue
            # Must be a Parsed object
            obj.validate_operand(self.lineno,n+1,trace=self.trace)
            # Safe to add to list of actual operands found
            self.operands.append(obj.operand)  # Add to list of actual operands

    def validate_label(self):
        # Check for required or optional label field in the instruction
        passes=self.asmpasses
        if not passes.optional and self.label is None:
            raise AssemblerError(line=self.lineno,\
                msg="required label missing from statement: %s" % (passes.name))


#
#  +---------------------------------+
#  |                                 |
#  |   A Small Mainframe Assembler   |
#  |                                 | 
#  +---------------------------------+
#

# This class implements a small mainframe assembler consisting of a subset of 
# mainframe assembler functions.  Its output is a binary image of the assembled
# statements.  

# The Assembler is designed to be a backend supporting some front end process that 
# presents source statements to the assembler for assembly.  The asma.py module
# provides a command line interface to this assembler.
#
# The following instance methods are used by the front end process:
#
#   statement    Does initial statement parsing and queues statements for assembly
#   assemble     Assembles queued statements and creates the output Image instance
#   image        Retrieves the output object used to generate output.  Output
#                generation is the responsibility for the front end process.
#

# Presently local configurations are not yet supported.  The future of the AsmConfigs
# and AsmConfig classes are yet to be determined.  When supported they may move
# to the asma.py module and be transparent to this module.
#
# These two classes form the foundation for local configurations
class AsmConfigs(object):
    def __init__(self):
        self.configs={}

    def config(self,name=None,addr=None,ccw=None,cpfile=None,cptrans=None,\
            dump=None,error=None,msldb=None,nest=None,psw=None,stats=None,\
            *args,**kwds):
    
        assert len(args)==0,\
            "%s position parameters are not allowed: %s" \
                % (eloc(self,"config"),args)

        if __debug__:
            if len(kwds):
                string=""
                for kwd,val in kwds.items():
                    string="%s,%s=%s" % (string,kwd,val)
                string=string[1:]
                assert False,\
                    "%s unrecognized keyword parameter(s): %s" \
                        % (eloc(self,"config"),string)

        assert isinstance(name,str),\
            "%s 'name' argument must be a string: %s" % (eloc(self,"config"),name)

        config=AsmConfig(name,\
            addr=addr,
            ccw=ccw,
            cpfile=cpfile,
            cptrans=cptrans,
            dump=dump,
            error=error,
            msldb=msldb,
            nest=nest,
            psw=psw,
            stats=stats)
        
        n=config._name
        try:
            self.configs[n]
            cls_str="%s %s.config() -" % (this_module,self.__class__.__name__)
            raise ValueError("%s configuration alread defined: %s" % (cls_str,n))
        except KeyError:
            self.configs[n]=config

    # This method defines all local configurations
    def local(self):
        self.config(name="default")
        # Add additional calls to the config method here for your local configuration
        # definitions, specifying a unique name and a keyword argument for each
        # argument you wish to specify for the configuration.
        
    def retrieve(self,name):
        try:
            return self.configs[name]
        except KeyError:
            raise ValueError("%s undefined local configuration: %s" \
                % (eloc(self,"retrieve"),name))

class AsmConfig(object):
    psw_formats=["S","360","67","BC","EC","380","XA","E370","E390","Z","none"]
    def __init__(self,name,addr=None,case=None,ccw=None,cpfile=None,cptrans=None,
                 dump=None,error=None,msldb=None,nest=None,psw=None,stats=None):
        assert isinstance(name,str),\
            "%s 'name' argument must be a string: %s" \
                % (eloc(self,"__init__"),name)

        self._name=name
        self.addr(addr)
        self.case(case)
        self.ccw(ccw)
        self.cpfile(cpfile)
        self.cptrans(cptrans)
        self.dump(dump)
        self.error(error)
        self.msldb(msldb)
        self.nest(nest)
        self.psw(psw)
        self.stats(stats)

    def addr(self,addr=None):
        assert addr is None or addr in [16,24,31,64],\
            "%s 'addr' argument must be either 16, 24, 31 or 64: %s" \
                % (eloc(self,"addr"),addr)

        self._addr=addr

    def case(self,case=None):
        assert case is None or case in [True,False],\
            "%s 'case' argument must be either True or False: %s" \
                % (eloc(self,"addr"),addr)

        self._case=case

    def ccw(self,ccw=None):
        assert ccw is None or ccw in [0,1,"none"],\
            "%s 'ccw' argument must be either 0, 1 or 'none': %s" \
                % (eloc(self,"ccw"),ccw)

        self._ccw=ccw

    def cpfile(self,cpfile=None):
        assert cpfile is None or isinstance(cpfile,str),\
            "%s 'cpfile' argument must be a string: %s" \
                % (eloc(self,"cpfile"),cpfile)

        self._cpfile=cpfile

    def cptrans(self,cptrans=None):
        assert cptrans is None or isinstance(cptrans,str),\
            "%s 'cptrans' argument must be a string: %s" \
                % (eloc(self,"cptrans"),cptrans)

        self._cptrans=cptrans

    def dump(self,dump=None):
        assert dump is None or dump in [True,False],\
            "%s 'dump' argument must be either True or False: %s" \
                % (eloc(self,"dump"),dump)

        self._dump=dump

    def error(self,error=None):
        assert error is None or error in [0,1,2,3],\
            "%s 'error' argument must be 0, 1, 2 or 3: %s" \
                % (eloc(self,"error"),error)

        self._error=error

    def msldb(self,msldb=None):
        assert msldb is None or isinstance(msldb,str),\
            "%s 'msldb' argument must be a string: %s" \
                % (eloc(self,"msldb"),msldb)

        self._msldb=msldb

    def nest(self,nest=None):
        assert nest is None or (isinstance(nest,int) and nest>=1),\
            "%s 'nest' argument must be an integer >=1: %s" \
                % (eloc(self,nest),nest)

        self._nest=nest

    def psw(self,psw=None):
        assert psw is None or psw in AsmConfig.psw_formats,\
            "%s 'psw' argument not a recognized format: %s" \
                % (eloc(self,"psw"),psw)

        self._psw=psw

    def stats(self,stats=None):
        assert stats is None or stats in [True,False],\
            "%s 'stats' argument must be either True or False: %s" \
                % (eloc(self,"stats"),stats)

        self._stats=stats

#local=AsmConfigs()
# Establish the documented default command-line options
#local.config(\
#    name="default",
#    addr=None,
#    ccw=None,
#    cptrans="94C",
#    dump=False,
#    error=2,
#    msldb="msl.txt",
#    nest=20,
#    stats=False)
#import asmlocal   # This will add the local configurations.


# This class manages output options directed to the assembler.  None implies the output
# is not written the file system (although it might be created internally).
class AsmOut(object):
    def __init__(self,deck=None,image=None,ldipl=None,listing=None,mc=None,rc=None,\
                 vmc=None):
        self.deck=deck          # Object deck file name or None
        self.image=image        # Image file name or None
        self.ldipl=ldipl        # List directed IPL file and implied base dir. or None
        self.listing=listing    # Assembly listing file or None.
        self.mc=mc              # Management console command file or None
        self.rc=rc              # Hercules RC script file commands or None
        self.vmc=vmc            # Virtual machine STORE commands file or None

    def write_file(self,module,filename,mode,content,desc,silent=False):
        if filename is None:
            return
        try:
            fo=open(filename,mode)
        except OSError:
            print("%s - could not open for writing %s file: %s" \
                % (module,desc,filename))
            return

        # Once the file is open, any problems writing the file or closing it 
        # represent a major issue.  In this case we bail entirely with a message.
        try:
            fo.write(content)
        except OSError:
            print("%s - could not complete writing of %s file: %s" \
                % (module,desc,filename))
            sys.exit(2)
        finally:
            try:
                fo.close()
            except OSError:
                print("%s - could not close output file: %s" % (module,filename))
                sys.exit(2)

        # File completed successfully.  Print message if not running silently.
        if not silent:
            print("%s - %s file written: %s" % (module,desc,filename))

    def write_deck(self,module,deck,silent=False):
        if deck is None:
            return
        self.write_file(module,self.deck,"wb",deck,"object deck",silent=silent)

    def write_image(self,module,image,silent=False):
        self.write_file(module,self.image,"wb",image,"image",silent=silent)

    def write_ldipl(self,module,ldipl_list,silent=False):
        ldipl_dir=self.ldipl
        if ldipl_dir is None:
            return
        abs_path=os.path.abspath(self.ldipl)
        dirname,filename=os.path.split(abs_path)
        for filename,content,mode in ldipl_list:
            if mode == "wt":   # This is the IPL list file
                fullpath=abs_path
            else:
                fullpath=os.path.join(dirname,filename)
            self.write_file(module,fullpath,mode,content,"list directed IPL",\
                silent=silent)
        return

    def write_listing(self,module,listing,silent=False):
        self.write_file(module,self.listing,"wt",listing,"listing",silent=silent)

    def write_mc(self,module,mcfile,silent=False):
        self.write_file(module,self.mc,"wt",mcfile,"STORE command",silent=silent)

    def write_rc(self,module,rcfile,silent=False):
        self.write_file(module,self.rc,"wt",rcfile,"RC script",silent=silent)

    def write_vmc(self,module,vmcfile,silent=False):
        self.write_file(module,self.vmc,"wt",vmcfile,"STORE command",silent=silent)


# This is the base class for the assembler.  It assembles individiual assembler
# statements presented to it.  Final output is returned in the form of an Image
# class instance.  The image class attributes are the various forms of output from
# the ASMA assembler.
#
# It is the responsibility of the instantiator to present the individual statements
# to the class instance for assembly and determine the destination of the returned 
# attributes of the returned Image instance.
class Assembler(object):
    # Recognized debug options.  May be used directly in argparse choices argument
    debug=["stmt","tokens","insns","exp","tracexp","classify","grammar",\
        "continuation"]
    # Values recognized in bimodal PSW's
    bimodes={0:0,1:1,24:0,31:1}
    bi67modes={0:0,1:1,24:0,32:1}   # S/360 Model 67 bimodal addressing
    biprog={"PSW380": 0b10111111, 
            "PSWXA":  0b10111111,
            "PSWE370":0b11111111,
            "PSWE390":0b11111111}
    # Values recognize in trimodal PSW
    trimodes={0:0,1:1,3:3,24:0,31:1,64:3}
    # XMODE values accepted
    ccw_xmode={"0":"CCW0",0:"CCW0","1":"CCW1",1:"CCW1","none":None,"NONE":None}
    psw_xmode={"S":"PSWS","PSWS":"PSWS",
               "360":"PSW360","PSW360":"PSW360",360:"PSW360",
               "67":"PSW67","PSW67":"PSW67",67:"PSW67",
               "BC":"PSWBC","PSWBC":"PSWBC",
               "EC":"PSWEC","PSWEC":"PSWEC",
               "380":"PSW380","PSW380":"PSW380",380:"PSW380",
               "XA":"PSWXA","PSWXA":"PSWXA",
               "E370":"PSWE370","PSWE370":"PSWE370",
               "E390":"PSWE390","PSWE390":"PSWE390",
               "Z":"PSWZ","PSWZ":"PSWZ",
               "none":None,"NONE":None}
    # Lexical analyzers (created by __init_parsers() method)
    lexer=None     # Defau;t Lexical analyzer used by most FSM-based parsers
    
    # Syntactic analyzers (created by __init_parsers() method)
    fields=None    # Statement field FSM-based recognizer
    mhelp=None     # MHELP FSM-based recognizer

    # Returns my global debug manager.
    @staticmethod
    def DM():
        return satkutil.DM(appl=Assembler.debug,lexer=True,parser=True)

    # Test we are running version 3.3 or greater of Python
    @staticmethod
    def test_version():
        ver=sys.hexversion
        if ver < 0x03030000:
            raise ValueError("assembler.py - Assembler.test_version() - "
                "Python version requires 3.3 or greater: %08X" % ver)

    #
    #  PRIVATE METHODS
    #

    # Assembler object.  All processing occurs via this class.
    #
    # Instance arguments:
    #
    #   machine     The string ID of the targeted system or cpu in the MSL database
    #   msl         Path the Machine Specification Language database source
    #   aout        AsmOut object describing output characteristics.
    #   msldft      Default MSL directory if MSLPATH not defined
    #   addr        Size of addresses in this assembly.  Overrides MSL CPU statement
    #   bltin       Enables built-in macros if True.
    #   case        Enables case sensitivity for lables, symbolic variables and
    #               sequence symbols.  Defaults to case insensitive.
    #   debug       The global Debug Manager to be used by the instance.  In None
    #               is specified, one will be generated.  Defaults to None.
    #   defines     A list of GBLC/SETC symbol,value tuples.
    #   dump        Causes completed CSECT's, region's and image to be printed
    #   eprint      Forces printing of errors when they occur in either error
    #               levels 1 or 2.
    #   error       Specifies the error level:
    #                 0  - AssemblerErrors not trapped, immediate failure occurs
    #                 1  - prints errors on sysout when encountered
    #                 2  - lists errors at end of listing
    #               Defaults to 2.
    #   nest        Specify the number of nested include files allowed.  Defaults to
    #               20.
    #   ccw         Specify the initial execution mode for CCW's: 0 or 1 or 'none'.
    #               None implies no external option is supplied and the execution mode
    #               specified in the MSL database for the target machine is used.
    #   psw         Specify the initial execution mode for PSW's.  See the dictionary
    #               Assembler.psw_xmode for supported options.  None implies no
    #               external option is supplied and the execution mode specified in 
    #               the MSL database for the target machine is used.
    #   ptrace      A list of integers identifying which passes will be traced in
    #               their entirety.  This is a diagnostic option.
    #   otrace      A list of the machine instructions or assembler directives to
    #               be traced in all passs including initial parsing.
    #   stats       Specigy True to enable statistics reporting at end of pass 2.  
    #               Should be False if an external driver is updating statistics.
    def __init__(self,machine,msl,aout,msldft=None,addr=None,bltin=False,case=False,\
                 debug=None,defines=[],dump=False,eprint=False,error=2,nest=20,\
                 ccw=None,psw=None,ptrace=[],otrace=[],cpfile=None,cptrans="94C",\
                 stats=False):

        # Before we do anything else start my timers
        Stats.start("objects_p")
        Stats.start("objects_w")
        self.timers_started=False

        Assembler.test_version()     # Make sure we have the right Python
        self.version=asma_version    # Current version of the assembler
        
        self.now=time.localtime()    # now is an instance of struct_time.

        assert isinstance(aout,AsmOut),\
            "%s 'aout' argument must be an aout object: %s" \
                % (eloc(self,"__init__"),aout)

        if debug is None:
            self.dm=Assembler.DM()  # Global debug manager, satkutil.DM instance
        else:
            self.dm=debug           # Global debug manager from user

        self.aout=aout              # AsmOut object
        self.imgdump=dump           # Dumps completed CSECT's, regions and image
        self.ptrace=ptrace          # Passes to be traced
        self.otrace=otrace          # statements to be traced.
        self.bltin=bltin            # Enables/disables builtin macros
        self.case=case              # Specifies if case sensitivity is enabled.
        self.cpfile=cpfile          # Code page source file (defaults to built-in)
        self.cptrans=cptrans        # Code page translation definition to use
        self.gblc=defines           # GBLC/SETC definitions from driver.
        

        # Error handling flag
        self.error=error
        self.fail=self.error==0
        self.eprint=eprint or error==1  # Prints errors when encountered

        # Statistics flag
        self.stats=stats

      #
      #   Assembler initialization begins
      #   DO NOT CHANGE THE SEQUENCE!  Dependencies exist between methods
      #

        # Statement classifier regular expressions and other RE users. 
        # See __init_res() and related _spp methods
        self.sqtre=None       # Recognizes a single quoted string (COPY)
        self.__init_res()     # Create regular expressions for __classifier() method

        # Statement operand parsers. See __init_parsers() method
        self.parsers={}       # Parsers identified by a name
        self.__init_parsers() 

        # These attributes drive statement processing
        # Dictionary of AsmPasses instances.  see __init_statements()
        self.asminsn=None    # Generic machine instruction AsmPasses instance
        # Define how to process statements
        self.asmpasses=self.__init_statements()
        # Define how to process passes.
        self.passes=self.__init_passes()      # List of Pass instances
        # Create the machine instruction construction engine and CPU related values
        self.builder=insnbldr.Builder(machine,msl,msldft=msldft,\
            trace=self.dm.isdebug("insns"))
        self.addrsize=self.builder.addrsize   # Maximum address size in bits
        self.xmode={}
        self.__init_xmode(ccw,psw) # Initialize XMODE settings
        # Modes and settings used by XMODE directive.
        self.xmode_dir={"PSW":Assembler.psw_xmode,
                        "CCW":Assembler.ccw_xmode}
        # Create structure templates
        self.templates=self.__init_templates() # Dictionary of structure templates

      #
      #   Sequence dependent initialization completed
      #   Remaining initialization is sequence independent
      #

        # Manage ASCII/EBCDIC codepages by building the codepage.Translator object
        self.trans=self.__init_codepage()
        # The Translater object is available now via this object attribute and
        # in modules that import assembler via assembler.CPTRANS
       
        # Manage input text
        self.LB=asminput.LineBuffer(depth=nest)

        # Macro Language processing manager
        self.MM=asmmacs.MacroLanguage(self)
        # Define external global SETC symbols
        for sym,val in self.gblc:
            try:
                self.MM._init_gblc(sym,val)
            except asmmacs.MacroError as me:
                self.__ae_excp(AssemblerError(msg=me.msg),None)

        # Manage output binary data
        self.OM=asmbin.AsmBinary()

        # These attributes are constructed and manipulated by __parse() method
        # assembler passes.
        self.lineno=1         # Next statement number for source listing
        self.stmts=[]         # List of parsed Stmt instances
        self.cur_stmt=None    # In numbered pass processing, current Stmt instance
        self.cur_pass=0       # Current Pass

        # Current Location Counter - value of an asterisk in address expression
        self.cur_loc=LocationCounter()

        # These attributes are constructed and manipulated during the various 
        # assembler passes performed on the statements stored in self.stmts list.

        # Base register assignment manager
        self.bases=BaseMgr(extended=machine=="360-20")

        self.ST=ST()          # Symbol Table used for all symbols
        # ADD unique name here!!!
        self.imgwip=Img()     # Work in progress image container of Regions

        # These lists assist in finalizing output both the image data and listing.
        self.dcs=[]           # List of DC Stmt objects that must fill in barray
        self.dsects=[]        # DSECT list to allow finalization
        self.equates=[]       # These must be bound to an absolute address

        self.cur_reg=None     # Current active Region into which Sections are added
        self.cur_sec=None     # Current active Section into which Content is added
        
        # Unnamed REGION and CSECT if created.  
        # These objects are maintained here not via the symbol table.
        self.unname_reg=None  # The unnamed region if created
        self.unname_sec=None  # The unnamed section if created

        # Global assembly state attributes
        self.aborted=False    # Set to True if an AssemblerAbort is raised
        self.assemble_called=False  # Set to True when assemble() method called

        # Final output of the assembler, an Image instance
        self.img=Image()      # Output Image class instance
        self.load=None        # Load point of Image content
        self.entry=None       # Entry point of the Image content

        # Manage output listing
        self.LM=asmlist.AsmListing(self)
        if addr is None:
            self.laddrsize=self.addrsize
        else:
            self.laddrsize=addr
        # Listing state flags controlled by PRINT directive.
        self.pon=True         # Assume "PRINT ON" directive
        self.pgen=True        # Assume "PRINT GEN" directive
        self.pdata=False      # Assume "PRINT NODATA" directive
        
        # Stop object timers
        Stats.stop("objects_w")
        Stats.stop("objects_p")

    def __abort(self,line,msg):
        self.aborted=True
        raise AssemblerAbort(line=line,msg=msg) from None

    # Performs generic AssemblerError exception handling
    def __ae_excp(self,ae,stmt,string="",debug=False):
        if (not ae.info) and stmt is not None:
            stmt.ignore=True
            stmt.error=True
            stmt.aes.append(ae)
        self.img._error(ae)

        if __debug__:
            if debug:
                print("%s DEBUG - AE %s" % (string,ae))
                return

        if self.eprint:
            print(ae)


    # Checks to make sure the current active region is assigned
    # If not assigned, if necessary, it creates an unnamed region, and activates the
    # unnamed region
    #
    # Active region state is unchanged if it is assigned.  It is only not assigned
    # in the case where an assembly has neither a CSECT nor START in the assembly and
    # binary content has been created or locations are allocated.
    # Method Arguments:
    #   start   Assigns the starting address of the region.  Defaults to 0
    #   debug   Enables debug messages if True.
    def __check_cur_reg(self,start=0,debug=False):
        if self.cur_reg is not None:
            return
        # No current region.  This occurs only is an assembly lacks a START directive.
        # The START directive will always create either a named or unnamed region
        # and activate it.
        if self.unname_reg is None:
            # Unnamed region does not exist, so create it
            self.unname_reg=self.__region_unname(0,debug=debug)
        # Activate the unnamed region.  This can result in an unassigned active 
        # section if the unnamed region just created is activated.
        self.__region_activate(self.unname_reg,debug=debug)

    # Checks to make sure the current active section is assigned
    # If not, if necessary, it creates an unnamed section and activates it
    #
    # An active section is not assigned when the assembly has neither a START nor
    # a CSECT statement.  Automatic creation of an unnamed section occurs when
    # binary content is created or space is allocated without an active section.
    def __check_cur_sec(self,debug=False):
        if self.cur_sec is not None:
            return
        # Unnamed section does not exist, create it
        if self.unname_sec is None:
            self.unname_sec=self.__csect_unname(debug=debug)
        # Automatically activate the unnamed section
        # Activation may trigger creation of an unnamed region if one is not active
        self.__csect_activate(self.unname_sec,debug=debug)

    # This method classifies a statement and updates an instance of Stmt
    def __classifier(self,s,debug=False):
        # debug is controlled by debug option 'stmt'
        
        # This uses the StmtFields object to parse the statement fields
        s.fields=fields=StmtFields()
        fields.parse(self,s,debug=debug)
        s.classified()

    # Perform normal assembler continuation handling of multi-line statements.
    # This creates a single string of operands (in the StmtOperands object) for
    # parsing or special processing
    def __continuation(self,s,debug=False):
        fields=s.fields
        try:
            fields.normal(s.line)
        except asmcards.LineError as le:
            raise AssemblerError(source=le.source,line=s.lineno,msg=le.msg) \
                from None
        s.continuation()

    # Define how directives are processed in each pass
    def __define_dir(self,iset,insn,spp=None,parser=None,pass1=None,pass2=None,\
                     optional=True,min=None,max=None,cls=[],debug=False):
        if parser is None:
            parsr=None
        else:
            try:
                parsr=self.parsers[parser]
            except KeyError:
                raise ValueError("%s unrecognized parser for insn '%s': '%s'" \
                    % (eloc(self,"__define_dir"),insn.mnemonic,parser))

        dr=AsmPasses(insn,spp=spp,parser=parsr,pass1=pass1,pass2=pass2,\
            optional=optional,min=min,max=max,cls=cls)
        iset[dr.name]=dr

    def __error(self,string=None):
        if string is None:
            raise ValueError("assembler terminated due to error") from None
        raise ValueError("%s\nassembler terminated" % string) from None

    # This method uses the Pratt parser to evaluate in individual expression.
    # It is called by a statement's pass processing method.
    # An AssemblerError exception is possible.  The assemble methods fail argument
    # dictates how the exception is handled
    def __evaluate_operand(self,parsed,debug=False,trace=False):
        parsed.evaluate(debug=debug,trace=trace)
        # The result is placed in the Operand instance.  The attribute depends 
        # upon the type of operand: Single, Storage, or StorageExp.

    # Finish the Image (with the exception of the listing)
    def __finish(self):
        wip=self.imgwip
        image=self.img

        image.load=Address.extract(self.load)
        image.entry=Address.extract(self.entry)
        image.image=wip.barray

        # Generate remaining forms of binary output and put them in the Image object
        if self.aout.deck is not None:
            image.deck=self.OM.deck(self)
        if self.aout.rc is not None:
            image.rc=self.OM.rc_file(self)
        if self.aout.vmc is not None:
            image.vmc=self.OM.vmc_file(self)
        if self.aout.mc is not None:
            image.mc=self.OM.mc_file(self)
        if self.aout.ldipl is not None:
            image.ldipl=self.OM.ldipl(self)   

    # Initialize the code page translator and make it globally available via
    # the assembler.CPTRANS for modules that import assembler.
    def __init_codepage(self):
        global CPTRANS
        trans=codepage.CODEPAGE().build(trans=self.cptrans,filename=self.cpfile)
        CPTRANS=trans
        return trans

    def __init_parsers(self,debug=False):
        gdebug=self.dm.isdebug("grammar")
        parser=asmparsers.CommonParser(self.dm,asm=self)
        self.parsers["common"]=parser
        if gdebug:
            print("Grammar of 'common' parser:")
            parser.grammar()
            print("")

        # These lexical analyzers are assigned to Assembler class attributes.
        Assembler.lexer=asmfsmbp.AsmLexer(self.dm).init()

        # These syntactical analyzers are assigned to Assembler class attributes,
        # and are not part of the Assembler object's parsers attribute dictionary.
        self.fsmp=asmfsmbp.Parsers(self).init()
        Assembler.fields=self.fsmp.parsers["fields"]

    def __init_passes(self):
        pass_list=[Pass(1,proc="pass1_p",wall="pass1_w",post=self.__Pass1_Post),\
                   Pass(2,proc="pass2_p",wall="pass2_w",post=self.__Pass2_Post)]

        # Create list of Pass instances
        num_pass=len(pass_list)
        p=[None,] * (num_pass+1)

        for pas in pass_list:
            pn=pas.pas
            if p[pn] is not None:
                cls_str="assembler.py - %s.__init_passes() -" % self.__class__.__name__
                raise ValueError("%s pass already defined: %s" % (cls_str,pn))
            if pn in self.ptrace:
                pas.trace=True
            p[pn]=pas

        return p     # Return the completed list

    def __init_res(self,debug=False):
        # debug is controlled by debug option 'stmt'

        # Recognizes a single quoted string in directives (COPY only)
        p=r"'[^']*'"
        self.sqtre=re.compile(p)
        if __debug__:
            if debug:
                print("sqtre pattern: '%s'" % self.titre.pattern)

    # This method initializes among other things, the methods used in each pass
    # for each directive or machine instruction.  The following table summarizes
    # the method usage.
    #
    #   Directive  Pre-Proc        Pass 1         Pass 2
    #    CCW       "common"     _ccw0_pass1    _ccw0_pass2
    #    CCW0      "common"     _ccw0_pass1    _ccw0_pass2
    #    CCW1      "common"     _ccw1_pass1    _ccw1_pass2
    #    COPY      _spp_copy        --             --
    #    CSECT     "common"     _csect_pass1       --
    #    DC        _spp_dcds    _dcds_pass1    _dc_pass2
    #    DS        _spp_dcds    _dcds_pass1        --
    #    DSECT     "common"     _dsect_pass1       --
    #    END       _spp_end     _end_pass1     _end_pass2
    #    ENTRY     "common"     _entry_pass1   _entry_pass2
    #    EQU       "common"     _equ_pass1         --
    #    <macro>   _spp_invoke      --             --
    #    MNOTE     _spp_mnote       --             --
    #    ORG       "common"     _org_pass1         --
    #    PRINT     _spp_print       --             --
    #    PSWS      "common"     _psw20_pass1   _psw20_pass2
    #    PSW360    "common"     _psw360_pass1  _psw360_pass2
    #    PSW67     "common"     _psw67_pass1   _psw67_pass2
    #    PSWBC     "common"     _pswbc_pass1   _pswbc0_pass2
    #    PSWEC     "common"     _pswec_pass1   _pswec_pass2
    #    PSW380    "common"     _pswbi_pass1   _pswbi_pass2
    #    PSWXA     "common"     _pswbi_pass1   _pswbi_pass2
    #    PSWE370   "common"     _pswbi_pass1   _pswbi_pass2
    #    PSWE390   "common"     _pswbi_pass1   _pswbi_pass2
    #    PSWZ      "common"     _pswz_pass1    _pswz_pass2
    #    REGION    "common"     _region_pass1  _region_pass2
    #    START     _spp_start   _start_pass1   _start_pass2
    #    TITLE     _spp_title       --             --
    #    USING     "common"     _using_pass1   _using_pass2
    #    XMODE     _spp_xmode       --             --
    #  instruction "common"     _insn_pass1    _insn_pass2
    def __init_statements(self):
        idebug=self.dm.isdebug("insns")
        dset={}


        # CCW - Build a Channel Command Word based upon XMODE CCW setting
        # 
        # [label] CCW0    command,address,flags,count
        #
        # CCW is implemented through the self.xmode dictionary used by __oper_id()
        # method.  An explicit entry in self.asmpasses dictionary is not needed.

        # CCW0 - Build a Channel Command Word Format-0
        # 
        # [label] CCW0    command,address,flags,count
        self.__define_dir(dset,"CCW0",parser="common",\
            pass1=self._ccw0_pass1,pass2=self._ccw0_pass2,optional=True,\
            min=4,max=4,cls=[Single,SingleAny,Single,Single])


        # CCW1 - Build a Channel Command Word Format-1
        # 
        # [label] CCW1    command,address,flags,count
        self.__define_dir(dset,"CCW1",parser="common",\
            pass1=self._ccw1_pass1,pass2=self._ccw1_pass2,optional=True,\
            min=4,max=4,cls=[Single,SingleAny,Single,Single])


        # COPY - Insert into the input stream the contents of a file
        # 
        # [label] COPY  'path/filename'
        self.__define_dir(dset,"COPY",spp=self._spp_copy,optional=True)


        # CSECT - start or continue a control section
        # 
        # [label] CSECT   # no operands
        self.__define_dir(dset,"CSECT",parser="common",\
            pass1=self._csect_pass1,pass2=self._csect_pass2,optional=True,\
            min=0,max=0)


        # DC - Define Constant (Extended)
        #
        # [label] DC   desc'values',...
        self.__define_dir(dset,"DC",spp=self._spp_dcds,\
            pass1=self._dcds_pass1,pass2=self._dc_pass2,optional=False)


        # DROP - Remove a previous base register assignment
        #
        # [label] DROP   reg (1-16 operands allowed)
        drop_cls=[Single,]*16
        self.__define_dir(dset,"DROP",parser="common",\
            pass1=self._drop_pass1,pass2=self._drop_pass2,\
            min=1,max=16,cls=drop_cls)


        # DS - Define Constant
        #
        # [label] DS   desc'values',...
        self.__define_dir(dset,"DS",spp=self._spp_dcds,\
            pass1=self._dcds_pass1,optional=False)


        # DSECT - start of continue a dummy section
        # 
        # label DSECT   # no operands
        self.__define_dir(dset,"DSECT",parser="common",\
            pass1=self._dsect_pass1,optional=False,min=0,max=0)


        # EJECT - Introduce a new page in the listing (with the current title)
        # 
        # [label] EJECT   # no operands
        self.__define_dir(dset,"EJECT",spp=self._spp_eject,optional=True,min=0,max=0)


        # END - terminate the assembly and calculate the address of the entry-point.
        # 
        # [label] END     # no operands
        self.__define_dir(dset,"END",spp=self._spp_end,optional=True,\
            pass1=self._end_pass1,pass2=self._end_pass2)


        # ENTRY - Define and report an entry-point of the image.
        # 
        # [label] ENTRY  <address>
        self.__define_dir(dset,"ENTRY",parser="common",optional=True,min=1,max=1,\
            pass1=self._entry_pass1,pass2=self._entry_pass2,cls=[SingleAddress,])


        # EQU - Define a symbol
        # 
        # label EQU     expression
        self.__define_dir(dset,"EQU",parser="common",
            pass1=self._equ_pass1,optional=False,min=1,max=2,cls=[SingleAny,Single])


        # MACRO - Initiate a macro definition
        # 
        # [label] MACRO  [comments]
        self.__define_dir(dset,"MACRO",spp=self._spp_macro,optional=True)


        # MHELP - Specify macro assistance options
        # 
        # [label] MHELP  <action>
        self.__define_dir(dset,"MHELP",spp=self._spp_mhelp,optional=True)


        # MNOTE - Define a symbol
        # 
        # [label] MNOTE sev,'message'
        self.__define_dir(dset,"MNOTE",spp=self._spp_mnote,optional=True)
        

        # ORG - adjust current location
        #
        # [label] ORG  expression
        self.__define_dir(dset,"ORG",parser="common",\
            pass1=self._org_pass1,optional=True,min=1,max=1,cls=[SingleAny,])


        # PRINT - set listing option(s)
        #
        #         PRINT  option[,option]...
        self.__define_dir(dset,"PRINT",spp=self._spp_print,optional=True,min=1,max=6)


        # PSW - Build a Program Status Word based upon XMODE PSW setting
        # 
        # [label] PSW    sys,key,a,prog,addr[,amode]
        #
        # PSW is implemented through the self.xmode dictionary used by __oper_id()
        # method.  An explicit entry in self.asmpasses dictionary is not needed.


        # PSWS - Create a S/360-20 32-bit PSW
        # sys-> bits 7 (CM), key not used, a -> bit 6 (A), prog -> bits 2,3 (CC),
        # addr -> bits 16-31, amode not used
        #
        # [label] PSWS   sys,key,a,prog,addr[,amode]
        self.__define_dir(dset,"PSWS",parser="common",\
            pass1=self._psws_pass1,pass2=self._psws_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSW360 - Create a standard S/360 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 34-39
        # addr -> bits 40-63, amode not used
        #
        # [label] PSW360 sys,key,amwp,prog,addr[,amode]
        self.__define_dir(dset,"PSW360",parser="common",\
            pass1=self._psw360_pass1,pass2=self._psw360_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSW67 - Create a standard S/360 64-bit PSW
        # sys -> bits 5-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 16-23
        # addr -> bits 32-63, amode -> bit 4
        #
        # [label] PSW67 sys,key,amwp,prog,addr[,amode]
        self.__define_dir(dset,"PSW67",parser="common",\
            pass1=self._psw67_pass1,pass2=self._psw67_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWBC - Create an S/370 Basic Control mode 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-11, mwp -> bits 13-15, prog -> bits 34-39
        # addr -> bits 40-63, amode not used
        #
        # [label] PSWBC  sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWBC",parser="common",\
            pass1=self._pswbc_pass1,pass2=self._pswbc_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWEC - Create an S/370 Extended Control mode 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 40-63, amode not used
        #
        # [label] PSWEC  sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWEC",parser="common",\
            pass1=self._pswec_pass1,pass2=self._pswec_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSW380 - Create a Hercules S/380 mode 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 33-63, amode -> bit 32 
        #
        # [label] PSW380 sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSW380",parser="common",\
            pass1=self._pswbi_pass1,pass2=self._pswbi_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWXA - Create an S/370-XA 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 33-63, amode -> bit 32 
        #
        # [label] PSWXA  sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWXA",parser="common",\
            pass1=self._pswbi_pass1,pass2=self._pswbi_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWE370 - Create an ESA/370 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 33-63, amode -> bit 32 
        #
        # [label] PSWE370  sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWE370",parser="common",\
            pass1=self._pswbi_pass1,pass2=self._pswbi_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWE390 - Create an ESA/390 64-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 33-63, amode -> bit 32 
        #
        # [label] PSWE390  sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWE390",parser="common",\
            pass1=self._pswbi_pass1,pass2=self._pswbi_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # PSWZ - Create a z/Architecture (R) mode 128-bit PSW
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-24
        # amode -> bits 31,32, addr -> 64-127
        #
        # [label] PSWZ   sys,key,mwp,prog,addr[,amode]
        self.__define_dir(dset,"PSWZ",parser="common",\
            pass1=self._pswz_pass1,pass2=self._pswz_pass2,optional=True,\
            min=5,max=6,cls=[Single,Single,Single,Single,SingleAny,Single])


        # REGION - continue an existing region
        #
        # label REGION  # no operands
        self.__define_dir(dset,"REGION",parser="common",\
            pass1=self._region_pass1,pass2=self._region_pass2,optional=False,\
            min=0,max=0)


        # SPACE - insert space(s) into listing
        #
        #         SPACE [n]
        self.__define_dir(dset,"SPACE",spp=self._spp_space,optional=True)


        # START - start a new control section and optionally a new region
        #
        # label START address
        self.__define_dir(dset,"START",spp=self._spp_start,\
            pass1=self._start_pass1,pass2=self._start_pass2,optional=True,)


        # TITLE - set listing title
        #
        #         TITLE  'new listing title'
        self.__define_dir(dset,"TITLE",spp=self._spp_title,optional=True)


        # USING - define base register(s)
        #
        # [label] USING address,reg   (1 to 16 registers allowed)
        using_cls=[SingleAddress,]
        using_cls.extend([Single,]*16)
        self.__define_dir(dset,"USING",parser="common",\
            pass1=self._using_pass1,pass2=self._using_pass2,\
            optional=True,min=2,max=17,cls=using_cls)


        # XMODE - set execution mode options
        #
        #         XMODE  mode,setting
        self.__define_dir(dset,"XMODE",spp=self._spp_xmode,optional=True)


        # Create the generic AsmPasses instance used by all machine instructions
        parser=self.parsers["common"]
        self.asminsn=AsmPasses("insn",parser=parser,\
            pass1=self._insn_pass1,pass2=self._insn_pass2,directive=False)

        # Make sure all operations in the otrace list are upper case
        new_list=[]
        for ot in self.otrace:
            new_list.append(ot.upper())
        self.otrace=new_list
        return dset

    # Initialize template dictionary with Structure objects.
    def __init_templates(self):
        tdict={}    # Dictionary returned by this method

        #
        #  CCW and CCW0 Templates
        #

        for name in ["CCW","CCW0"]:
            # Build an insnbldr.Field object for each CCW field
            fields=[]
            desc="%s command code" % name
            fld=insnbldr.Field(value=None,name=desc,size=8,start=0)
            fields.append(fld)

            desc="%s address" % name
            fld=insnbldr.Field(value=None,name=desc,size=24,start=8)
            fields.append(fld)

            desc="%s flags" % name
            fld=insnbldr.Field(value=None,name=desc,size=8,start=32)
            fields.append(fld)

            desc="%s byte count" % name
            fld=insnbldr.Field(value=None,name=desc,size=16,start=48)
            fields.append(fld)

            s=Structure(name,self.builder,fields)
            tdict[s.name]=s

        #
        #  CCW1 Template
        #

        fields=[insnbldr.Field(value=None,name="CCW1 command code",size=8,start=0),
                insnbldr.Field(value=None,name="CCW1 flags",size=8,start=8),
                insnbldr.Field(value=None,name="CCW1 byte count",size=16,start=16),
                insnbldr.Field(value=None,name="CCW1 address",size=31,start=33)]
        s=Structure("CCW1",self.builder,fields)
        tdict[s.name]=s

        #
        #  PSWS Template
        #

        # sys-> bit 7 (CM), a -> bit 6 (A), prog -> bits 2,3 (CC), addr -> bits 16-31
        fields=[insnbldr.Field(value=None,name="PSWS system field",size=1,start=7),
                insnbldr.Field(value=None,name="PSWS A field",size=1,start=6),
                insnbldr.Field(value=None,name="PSWS program field",size=2,start=2),
                insnbldr.Field(value=None,name="PSWS address field",size=16,start=16)]
        s=Structure("PSWS",self.builder,fields)
        tdict[s.name]=s


        #
        #  PSW360 Template
        #

        # sys -> bits 0-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 34-39
        # addr -> bits 40-63
        fields=[insnbldr.Field(value=None,name="PSW360 system field",size=8,start=0),
                insnbldr.Field(value=None,name="PSW360 key field",size=4,start=8),
                insnbldr.Field(value=None,name="PSW360 AMWP field",size=4,start=12),
                insnbldr.Field(value=None,name="PSW360 program field",size=6,start=34),
                insnbldr.Field(value=None,name="PSW360 address field",size=24,start=40)]
        s=Structure("PSW360",self.builder,fields)
        tdict[s.name]=s


        #
        #  PSW67 Template
        #

        # sys -> bits 5-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 16-23
        # addr -> bits 32-63, amode -> bit 4
        fields=[insnbldr.Field(value=None,name="PSW67 system field",size=3,start=5),
                insnbldr.Field(value=None,name="PSW67 key field",size=4,start=8),
                insnbldr.Field(value=None,name="PSW67 AMWP field",size=4,start=12),
                insnbldr.Field(value=None,name="PSW67 program field",size=8,start=16),
                insnbldr.Field(value=None,name="PSW67 address field",size=32,start=32),
                insnbldr.Field(value=None,name="PSW67 amode field",size=1,start=4)]
        s=Structure("PSW67",self.builder,fields)
        tdict[s.name]=s


        #
        #  PSWBC Template
        #

        # sys -> bits 0-7, key -> bits 8-11, mwp -> bits 13-15, prog -> bits 34-39
        # addr -> bits 40-63
        fields=[insnbldr.Field(value=None,name="PSWBC system field",size=8,start=0),
                insnbldr.Field(value=None,name="PSWBC key field",size=4,start=8),
                insnbldr.Field(value=None,name="PSWBC MWP field",size=3,start=13),
                insnbldr.Field(value=None,name="PSWBC program field",size=6,start=34),
                insnbldr.Field(value=None,name="PSWBC address field",size=24,start=40)]
        s=Structure("PSWBC",self.builder,fields)
        tdict[s.name]=s


        #
        #  PSWEC Template
        #

        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
        # addr -> bits 40-63
        fields=[insnbldr.Field(value=None,name="PSWEC system field",size=8,start=0),
                insnbldr.Field(value=None,name="PSWEC key field",size=4,start=8),
                insnbldr.Field(value=1,   name="PSWEC mode field",size=1,start=12),
                insnbldr.Field(value=None,name="PSWEC MWP field",size=3,start=13),
                insnbldr.Field(value=None,name="PSWEC program field",size=8,start=16),
                insnbldr.Field(value=None,name="PSWEC address field",size=24,start=40)]
        s=Structure("PSWEC",self.builder,fields)
        tdict[s.name]=s


        #
        #  PSW380, PSWXA, PSWE370 and PSWE390 Templates
        #

        for name in ["PSW380","PSWXA","PSWE370","PSWE390"]:
            # Build an insnbldr.Field object for each PSW field
            fields=[]

            desc="%s system field" % name
            fld=insnbldr.Field(value=None,name=desc,size=8,start=0)
            fields.append(fld)

            desc="%s key field" % name
            fld=insnbldr.Field(value=None,name=desc,size=4,start=8)
            fields.append(fld)

            desc="%s mode field" % name
            fld=insnbldr.Field(value=1,name=desc,size=1,start=12)
            fields.append(fld)

            desc="%s MWP field" % name
            fld=insnbldr.Field(value=None,name=desc,size=3,start=13)
            fields.append(fld)

            desc="%s program field" % name
            fld=insnbldr.Field(value=None,name=desc,size=8,start=16)
            fields.append(fld)

            desc="%s amode field" % name
            fld=insnbldr.Field(value=None,name=desc,size=1,start=32)
            fields.append(fld)

            desc="%s address field" % name
            fld=insnbldr.Field(value=None,name=desc,size=31,start=33)
            fields.append(fld)

            s=Structure(name,self.builder,fields)
            tdict[s.name]=s


        #
        #  PSWZ Template
        #
        
        # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-24
        # addr -> 64-127, amode -> bits 31,32
        fields=[insnbldr.Field(value=None,name="PSWZ system field",size=8,start=0),
                insnbldr.Field(value=None,name="PSWZ key field",size=4,start=8),
                insnbldr.Field(value=None,name="PSWZ MWP field",size=3,start=13),
                insnbldr.Field(value=None,name="PSWZ program field",size=8,start=16),
                insnbldr.Field(value=None,name="PSWZ amode field",size=2,start=31),
                insnbldr.Field(value=None,name="PSWZ address field",size=64,start=64)]
        s=Structure("PSWZ",self.builder,fields)
        tdict[s.name]=s

        # Return completed dictionary
        return tdict

    # Initialize the XMODE settings.  The ccw and psw method arguments are from the 
    # command line argparse values.
    # The values are initialized from the MSL database.  The externally supplied 
    # arguments override the MSL database.
    #
    # If the arguments are supplied via the asma.py command line interface, invalid 
    # arguments will not be accepted.
    #
    # If the arguments are supplied by an external user of the Assembler class as
    # an embedded assembler, the values could be invalid.  The checks here are for
    # that case.
    def __init_xmode(self,ccw,psw):
        self.xmode=self.builder.init_xmode()   # Get MSL database defaults.

        if ccw is not None:  # External override provided
            try:
                self.__xmode_setting("CCW",ccw,Assembler.ccw_xmode)
            except KeyError:
                raise ValueError("%s 'ccw' xmode argument invalid: %s" \
                    % (eloc(self,"__init_xmode"),ccw)) from None

        if psw is not None:  # External override provided
            try:
                self.__xmode_setting("PSW",psw,Assembler.psw_xmode)
            except KeyError:
                raise ValueError("%s 'psw' xmode argument invalid: %s" \
                    % (eloc(self,"__init_xmode"),psw)) from None


    # Returns True if a given STE subclass or name is defined in the symbol table,
    # False otherwise.
    def __is_defined(self,symbol):
        return self.ST.isdefined(symbol)

    # Returns whether a specific operation is being traced:
    def __is_otrace(self,oper):
        return oper.upper() in self.otrace

    # Accepts a Stmt object from the statement field classifier and identifies
    # the operation of the statement.  A number of Stmt attributes are set based
    # upon what it finds.
    #
    # Identification of the statement operation is performed in the following
    # sequence:
    #  1. Macro name
    #  2. Machine instruction operation mnemonic
    #  3. XMODE directive setting
    #  4. Assembler directive
    def __oper_id(self,stmt,debug=False):
        assert isinstance(stmt,Stmt),\
            "%s 'stmt' argument must be an instance of Stmt: %s" \
                % (eloc(self,"__oper_id"),stmt)

        idebug=self.dm.isdebug("insns")
        if idebug:
            cls_str=eloc(self,"__oper_id")
        lineno=stmt.lineno

        # Locate the instruction or statement data
        insn=None
        insn_fmt=None
        macro=None
        asmpasses=None
        try:
            macro=self.MM.find(stmt.instu)
            asmpasses=macro.passes(self)    # Pass myself, so my methods can be found
            if idebug:
                print("%s DEBUB found macro: %s" % (cls_str,stmt.inst))
        except KeyError:
            # Macro not found, try to identify the instruction mnemonic
            try:
                insn=self.builder.getInst(stmt.inst)
                # insn is an instance of MSLentry
                # Note, this needs to stay here as it controls Insn selection from the
                # machine definition or the assembler pseudo instruction definition.
                insn_fmt=insn.mslformat  # insn_fmt is an instance of msldb.Format

                asmpasses=AsmInsn(insn,insn_fmt,self.asminsn)
                if idebug:
                    print("%s DEBUG found instruction: %s" % (cls_str,insn.mnemonic))
            except KeyError:
                # Instruction mnemonic not found, try to find assmebler directive:
                # first by locating an XMODE setting, then by finding the actual
                # directive.
                # Note: XMODE settings translate a generic directive into a specific
                # machine sensitive one.
                try:
                    operation=self.xmode[stmt.instu]   # Find XMODE instruction
                except KeyError:
                    operation=stmt.instu               # If none use statement directly
                try:
                    asmpasses=self.asmpasses[operation]
                    if idebug:
                        print("%s DEBUG found directive: %s" % (cls_str,operation))
                except KeyError:
                    if idebug:
                        raise ValueError("%s AsmPasses not defined for "
                            "instruction: %s" % (cls_str,operation)) from None

        if asmpasses is None:
            stmt.error=True   # Mark this statement to avoid future processing

            # See comment in asmfsmbp.Parsers.parse_statement() method's handling
            # of the assembler.AsmParserError exception for why we are doing this
            # here.
            stmt.fields.normal(stmt.line)  # See comment in asmfsmbp.Parsers.
            raise AssemblerError(line=lineno,\
                msg="unrecognized instruction or directive: '%s'" % stmt.inst)

        stmt.insn=insn             # MSLentry object
        stmt.insn_fmt=insn_fmt     # msldb.Format object
        stmt.macro=macro           # asmmacs.Macro object
        stmt.asmpasses=asmpasses   # Set the pass dispatch table for this statement
        stmt.asmdir=asmpasses.directive  # Set the assembler directive flag
        if stmt.asmdir:
            stmt.laddr=[None,None] # Initialize laddr for assembler directives
        # Set trace flag if we are tracing this
        stmt.trace=asmpasses.name in self.otrace


    # This method excepts as input a Stmt instance returned by __classifier.
    # to have determined the instruction or directive. This method uses the syntactical
    # analyzer identified in AsmPasses to parse its operands.  
    #
    # Successful return of the input Stmt object simply means the statement was 
    # parsable.
    #
    # WARNING: No evaluations of expressions have occurred.  Operands have not been
    # validated for conformity to instruction operand formats.  Symbols have not
    # been created.
    def __parse(self,stmt):
        cls_str=eloc(self,"__parse()")
        assert isinstance(stmt,Stmt),\
            "%s 'stmt' argument must be an instance of Stmt: %s" \
                % (cls_str,stmt)

        idebug=self.dm.isdebug("insns") or stmt.trace
        sdebug=self.dm.isdebug("stmt") or stmt.trace

        lineno=stmt.lineno         # Fetch the statement's line number
        asmpasses=stmt.asmpasses   # Set the pass dispatch table for this statement

        # Build the Scope object for this parse
        scope=lang.Scope()
        scope.stmt=stmt
        scope.insn=stmt.insn       # Pass the Insn object in the parser scope
        scope.operands=stmt.num_oprs()    # Place in scope the number of operands

        # Used by _asmparse.filter() to adjust token locations in source statements
        # to reflect only partial parsing of statements
        scope.lineno=lineno
        scope.linepos=stmt.rempos

        # If there are no operands, there is nothing to parse, return stmt, 
        # it is complete
        if scope.operands==0:
            if idebug:
                print("%s DEBUG no operands to parse, returning statement" % cls_str)
            return stmt

        # Operands to parse, so build the Operand instances that will be populated
        # during parsing.
        stmt.create_types(debug=idebug)

        # Enable callback tracing if it is already enabled or statement tracing
        # in effect.  Parsing happens before the formal passes, so cbtrace is not
        # effected by the pass trace option.
        cbtrace=self.dm.isdebug("cbtrace")
        if cbtrace or stmt.trace:
            self.dm.enable("cbtrace")
        else:
            self.dm.disable("cbtrace")

        if sdebug:
            print("%s DEBUG parsing remainder of statement: '%s'" % (cls_str,stmt.rem))

        # Perform the actual parse of the operands returning the Scope object
        parse_eo=None
        try:
            gs=asmpasses.do_parse(stmt,scope=scope)
        except ParserAbort as eo:
            parse_eo=eo

        # Reset the cbtrace debug option
        if cbtrace:
            self.dm.enable("cbtrace")
        else:
            self.dm.disable("cbtrace")

        # The parser caved entirely, so treat it as failed parse with the 
        # information from the parser.
        if parse_eo:
            raise AssemblerError(line=stmt.lineno,msg=parse_eo.print(string=True))

        # Process any parser related errors
        mgr=gs.mgr
        if mgr.quantity():
            msg=mgr.print(string=True,count=False)
            raise AssemblerError(msg=msg)

        stmt.parsed=gs.parsed  # transfer parser results to Stmt instance
        if sdebug:
            string="%s DEBUG stmt.parsed:" % cls_str
            for p in stmt.parsed:
                string="%s\n    %s" % (string,p)
            print(string)
        return stmt

    def __pre_process(self,s,debug=False):
        assert isinstance(s,Stmt),\
            "%s 's' argument must be an instance of Stmt: %s" \
                % (eloc(self,"__pre_process"),s)

        sdebug=debug
        fail=self.fail

        # Classifies statement and identify statement fields: lable, instruction, and
        # operands.
        # Raises an AssemblerError if the statement structure makes no sense
        if fail:
            self.__classifier(s,debug=self.dm.isdebug("classify"))
        else:
            try:
                self.__classifier(s,debug=self.dm.isdebug("classify"))
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return

        # Access the Macro Language when defining macros
        # The Macro Language will return 'True' if the statement was handled
        if fail:
            macdefn=self.MM.defining(s)
        else:
            try:
                macdefn=self.MM.defining(s)
            except asmmacs.MacroError as me:
                ae=AssemblerError(source=s.source,line=s.lineno,msg=me.msg)
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return

        # Did the Macro Language intercept the statement as part of a definition?
        if macdefn:
            s.ignore=True  # Intercepted, so no need to do anything more with this
            return

        if s.ignore:
            if __debug__:
                if sdebug:
                    print("%s DEBUG: empty line: %s\n    %s" \
                        % (eloc(self,"__pre_process"),s.lineno,s.stmt))
            return

        if __debug__:
            if sdebug:
                print("%s DEBUG: classified statement\n    %s" \
                    % (eloc(self,"__pre_process"),s))
                
        # Make sure seq symbols or symbolic variables are not present in assembly
        # language name or operation statements.  These will detected in the
        # operands during operand parsing.
        # Note: macro model statements should have all references to symbolic
        # variables removed during replacement processing before being submitted
        # to the input stream.
        if fail:
            s.fields.cond_asm_ck(s)
        else:
            try:
                s.fields.cond_asm_ck(s)
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)

        # Identifies the operation in the operation field and updatas Stmt attributes
        # for further processing of the statement
        #
        # Raises an AssemblerError if the operation is not identified
        if fail:
            self.__oper_id(s,debug=self.dm.isdebug("classify"))
        else:
            try:
                self.__oper_id(s,debug=self.dm.isdebug("classify"))
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return

        if fail:
            self.__continuation(s,debug=self.dm.isdebug("continuation"))
        else:
            try:
                self.__continuation(s,debug=self.dm.isdebug("continuation"))
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return

        # Test of a special pre-processor in lieu of the parser
        spp=s.asmpasses.spp
        if spp is not None:
            if fail:
                spp(s,debug=sdebug)
            else:
                try:
                    spp(s,debug=sdebug)
                except AssemblerError as ae:
                    self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
            return
            # We exit here because this statement does not use a formal parser

        # Raises an AssemblerError if the statement operands are not parsable.
        if fail:
            self.__parse(s)
        else:
            try:
                self.__parse(s)
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)
                return
        if sdebug:
            print(s)

        # Raises an AssemblerError if the operands do not make sense.
        # The correct number must be present.  And no single expression operand 
        # contains a storage type operand (as detected by the parser.
        if fail:
            s.validate()
        else:
            try:
                s.validate()
            except AssemblerError as ae:
                self.__ae_excp(ae,s,string=eloc(self,"__pre_process"),debug=sdebug)

    # Set XMODE.  An invalid setting will raise a KeyError
    def __xmode_setting(self,mode,setting,sdict):
        v=sdict[setting]    # This may raise a KeyError
        if v is None:
            try:
                del self.xmode[mode]  # If none, remove the XMODE setting entirely 
            except KeyError:
                pass                  # Alredy gone, that is OK, that's what we wanted 
        else:
            self.xmode[mode]=v

    # Semi-private method intended to provide information about an internal error
    # while processing a line during Pass 0.
    # Returns: an information string
    def _error_pass0(self):
        lines=self.img.source
        if len(lines):
            last=lines[-1]
            if isinstance(last,asminput.Line):
                last=last.text
            return "Pass 0 INTERNAL ERROR WHILE PROCESSING THIS OR NEXT INPUT " \
                "LINE\n    %s" % last
        return "Pass 0 INTERNAL ERROR WHILE PROCESSING FIRST INPUT LINE"

    # Semi-private method intended to provide information about an internal error
    # while processing a statement in Pass 1 or 2.
    # Returns: an information string
    def _error_passn(self):
        if self.cur_stmt:
            line=self.cur_stmt.line
            line="[%s] %s" % (self.cur_stmt.lineno,line.text)
            return "Pass %s INTERNAL ERROR WHILE PROCESSING THIS STATEMENT\n    %s" \
                % (self.cur_pass,line)
        return "Pass %s INTERNAL ERROR LIKELY DURING PRE- OR POST-PASS PROCESSING" \
            % self.cur_pass

    # Returns the current XMODE setting for a supported mode (currently CCW or PSW)
    # Exception:
    #   KeyError if the mode has not been set.
    def _xmode_fetch(self,mode):
        return self.xmode[mode]

    # Generic routine for handling comma separate operands in pre-processed statements
    def __spp_operands(self,stmt,debug=False):
        # Extract the operand field from the statement
        operfld=stmt.rem
        # Look for first space (terminating the operands)
        try:
            ndx=operfld.index(" ")
            opers=operfld[:ndx]
        except ValueError:
            opers=operfld
        operands=opers.split(",")   # separate operands
        if not isinstance(operands,list):
            operands=[operands,]
        return operands

    # Special pre-processing for COPY directive
    def _spp_copy(self,stmt,debug=False):
        operfld=stmt.rem
        mo=self.sqtre.match(operfld)
        if mo is None:
            return
        filename=operfld[mo.pos:mo.endpos]     # "'include file name'"
        fname=filename[1:-1]   # remove single quotes "include file name"
        self.LB.newFile(fname,stmtno=stmt.lineno)
        stmt.ignore=True        


    # Special pre-processing for DS/DC directives
    def _spp_dcds(self,stmt,debug=False):
        fsmp=self.fsmp
        # Either of these two methods may raise an AssemblerError
        # Create asmfsmcs.DCDS_Scope by parser
        scope=fsmp.parse_scope(stmt,"dcds",required=True)
        # Use scope to complete Pass 0
        scope.Pass0(stmt,fsmp,debug=debug)
        stmt.gscope=scope


    # Special pre-processing for EJECT directive
    def _spp_eject(self,stmt,debug=False):
        stmt.prdir=True           # This statement requires processing during listing
        stmt.ignore=True          # No more processing needed by assembler passes


    # Special pre-processing for END directive
    def _spp_end(self,stmt,debug=False):
        fsmp=self.fsmp
        stmt.parsed=fsmp.parse_operands(stmt,"addr",required=False)


    # Special pre-processor for invoking a macro definition
    # 
    # This method creates the interface between the macro invocation processing
    # and the input line buffer into which model statements are supplied
    def _spp_invoke(self,stmt,debug=False):
        # Separate the comma separated macro parameters into a list
        operands=self.__spp_operands(stmt,debug=debug)
        
        # Create an asmmacs.Expander object.  The object runs the macro interpreter.
        # &SYSNDX value and MHELP limits are managed by the macstmt() method
        exp=self.MM.macstmt(stmt)
        if exp is None:  # This means MHELP maximum sysndx has been reached
            stmt.ignore=True
            return       # Silently ignore the macro statement

        # Create a new input source, that is, the macro being invoked
        self.LB.newMacro(exp,stmtno=stmt.lineno)
        # Done with the macro statement that triggered the expansion.
        # The macro engine now runs under control of the LineBuffer with the new 
        # macro input source.
        stmt.ignore=True


    # Special pre-processor for MACRO directive, initiating a new MACRO definition
    def _spp_macro(self,stmt,debug=False):
        # Determine if optional 'DEBUG' operand present and set definition debug
        ddebug=False
        operfld=stmt.rem
        try:
            ndx=operfld.index(" ")
            opers=operfld[:ndx]
        except ValueError:
            opers=operfld
        ddebug=opers.upper()=="DEBUG"

        self.MM.define(debug=ddebug)
        stmt.ignore=True


    # Special pre-processor for MHELP directive
    def _spp_mhelp(self,stmt,debug=False):
        fsmp=self.fsmp
        scope=fsmp.parse_operands(stmt,"mhelp",required=True)
        desc="MHELP %s" % stmt.lineno
        expr=fsmp.L2ArithExpr(desc,stmt,ltoks=scope.lextoks,debug=debug)
        operand=expr.evaluate(None,debug=debug,trace=False)

        # Update the mhelp data in the macro manager (asmmacs.MacroLanguage object)
        self.MM.mhelp(operand,debug=debug)


    # Special pre-processor for MNOTE directive
    def _spp_mnote(self,stmt,debug=False):
        fsmp=self.fsmp
        scope=fsmp.parse_operands(stmt,"mnote",required=True)
        note=scope.message.convert()
        if scope.comment:
            info=True
            sev="*"
        else:
            if scope.severity is None:
                desc="MNOTE %s" % stmt.lineno
                expr=fsmp.L2ArithExpr(desc,stmt,ltoks=scope.lextoks,debug=debug)
                operand=expr.evaluate(None,debug=debug,trace=False)
            else:
                operand=scope.severity
            if operand < 0 or operand> 255:
                operand=255
            info=False
            sev=operand

        raise AssemblerError(line=stmt.lineno,\
            msg="MNOTE %s,%s" % (sev,note),info=info)


    # Special pre-processing for PRINT directive
    def _spp_print(self,stmt,debug=False):
        # Extract the operand field from the statement
        operfld=stmt.rem
        # Look for first space (terminating the operands)
        try:
            ndx=operfld.index(" ")
            opers=operfld[:ndx]
        except ValueError:
            opers=operfld
        operands=opers.split(",")   # separate operands
        if not isinstance(operands,list):
            operands=[operands,]
        for ndx in range(len(operands)):
            original=operands[ndx]
            operand=original.upper()
            if operand == "ON":
                self.pon=True
            elif operand == "OFF":
                self.pon=False
            elif operand == "GEN":
                self.pgen=True
            elif operand == "NOGEN":
                self.pgen=False
            elif operand == "DATA":
                self.pdata=True
            elif operand == "NODATA":
                self.pdata=False
            else:
                raise AssemblerError(line=stmt.lineno,
                    msg="PRINT directive operand %s unrecognized: %s" \
                        % (ndx+1,original))
        stmt.ignore=True          # No more processing for a PRINT directive


    # Special pre-processsor for SPACE directive
    def _spp_space(self,stmt,debug=False):
        fsmp=self.fsmp
        scope=fsmp.parse_operands(stmt,"space",required=False)
        if scope is None:
            operand=1
        else:
            desc="SPACE %s" % stmt.lineno
            expr=fsmp.L2ArithExpr(desc,stmt,ltoks=scope.lextoks,debug=debug)
            operand=expr.evaluate(None,debug=debug,trace=False)

        stmt.plist=operand        # Communicate number of spaces to listing manager
        stmt.prdir=True           # This statement requires processing during listing
        stmt.ignore=True          # No more processing needed by assembler passes


    # Special pre-processor for START directive
    def _spp_start(self,stmt,debug=False):
        fsmp=self.fsmp
        # Either of these two methods may raise an AssemblerError
        scope=fsmp.parse_scope(stmt,"start")
        scope.Pass0(stmt,fsmp,debug=debug)

        stmt.gscope=scope


    # Special pre-processing for TITLE directive
    def _spp_title(self,stmt,debug=False):
        stmt.prdir=True           # This statement requires processing during listing
        stmt.ignore=True          # No more processing needed by assembler passes
        operfld=stmt.rem
        scope=self.fsmp.parse_operands(stmt,"title",required=True)
        token=scope.str_end()     # asmtokens.StringToken object
        # Extract the string, double quotes handles by the token
        data=token.convert()
        # Handle double ampersands here
        stmt.plist=data.replace("&&","&")    # New title in listing


    # Special pre-processing for XMODE directive
    def _spp_xmode(self,stmt,debug=False):
        operands=self.__spp_operands(stmt,debug=debug)
        if len(operands)!=2:
            raise AssemblerError(line=stmt.lineno,\
                msg="XMODE directive requires two operands: %s" % len(operands))
        mode=operands[0].upper()
        setting=operands[1].upper()
        try:
            mdict=self.xmode_dir[mode]
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="XMODE mode not recognized: %s" % mode) from None
        try:
            self.__xmode_setting(mode,setting,mdict)
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="XMODE %s setting invalid: %s" % (mode,setting)) from None
        stmt.ignore=True          # Processing completed


    #
    # PASS PRE- AND POST-PROCESSING METHODS
    #

    # PASS 1 - POST PROCESS ABSOLUTE ADDRESS BINDING

    # At the completion of Pass 1, all labels and Binary instances have their
    # associated CSECT relative addresses assigned.  This also means the size of
    # all of the CSECT's are known, so they can be bound to their respective regions.
    # Once the binding is done, all of the associated Binary instances can be bound
    # to their absolute addresses.

    def __Pass1_Post(self,trace=False):
        ctrace=trace or self.__is_otrace("csect")
        rtrace=trace or self.__is_otrace("region")
        dtrace=trace or self.__is_otrace("dsect")
        
        # For an assembly that has created no sections or regions
        # This ensures the remainder of Pass 1 post processing succeeds.
        self.__check_cur_sec(debug=ctrace)
        
        # Place all of the CSECTS into their respective Regions, assigning
        # them an absolute starting address
        for r in self.imgwip.elements:
            r.assign_all(debug=ctrace)

        # Make all of the self.loc relative adresses into absolute addresses and
        # do the same for equate symbols.
        for r in self.imgwip.elements:
            r.make_absolute(debug=ctrace)
        for e in self.equates:
            e.makeAbs()

        # Establish the physical location within the image of each region and CSECT
        self.imgwip.locate_all(trace=rtrace)
        self.imgwip.make_barray_all(trace=rtrace)

        # Update the symbol table attributes of the Regions and CSECTS with image
        # data.  The Assembler object is passed to provide assistance.
        self.imgwip.updtAttr_all(self,trace=rtrace)
        self.__image_new(self.imgwip)   # Add the IMAGE to the symbol table
        for dsect in self.dsects:
            dsect.make_barray_all(trace=rtrace)
            dsect.updtAttr(self,trace=dtrace)

    # PASS 2 - POST PROCESS IMAGE CREATION

    def __Pass2_Post(self,trace=False):
        # Complete the image build
        self.imgwip.insert(trace=trace)
        for dc in self.dcs:
            dc.content.insert(trace=trace)


    #
    # METHODS USED BY STATEMENT PROCESSING METHODS
    #

    # This method uses a list of insnbldr.Field objects to create a structure
    # It is the same basic algorithm used in insnbldr.Instruction generate() method,
    # but tailored for use by an assembler directive.
    #
    # Method arguments:
    #   name       Template name for the structure
    #   stmt       Stmt object of the statemet for which the structure is being built
    #   values     A list of of values to be placed in the template.
    def __build_structure(self,name,stmt,values=[],trace=False):
        try:
            template=self.templates[name]
        except KeyError:
            raise ValueError("%s [%s] undefined structure template: %s" \
                % (eloc(self,"__build_structure"),stmt.lineno,name))
            
        return template.build(stmt,values,trace=trace)

    def __csect_activate(self,section,debug=False):
        assert isinstance(section,Section),\
            "%s 'section' argument must be a CSECT: %s" \
                % (eloc(self,"__csect_activate"),section)
        assert not section._dummy,"%s 'section' argument must be a CSECT: %s" \
            % (eloc(self,"__csect_activate"),section)

        self.cur_reg=section.container
        self.cur_sec=section
        self.cur_loc.establish(section.current())

        if __debug__:
            if debug:
                cls_str=eloc(self,"__csect_activate")
                print("%s current active region is:  '%s'" \
                    % (cls_str,self.cur_reg.name))
                print("%s current active section is: '%s'" \
                    % (cls_str,self.cur_sec.name))

    # Creates a new CSECT, adds it to the active region and symbol table.
    # Returns the new Section instance to the caller.    
    def __csect_new(self,line,csect_name,debug=False):
        if not self.case:
            csect=Section(csect_name.upper())
        else:
            csect=Section(csect_name)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"__csect_new"),csect))

        self.__check_cur_reg(debug=debug)
        self.cur_reg.append(csect)

        if __debug__:
            if debug:
                print("%s added %s to current region: '%s'" \
                    % (eloc(self,"__csect_new"),csect.name,self.cur_reg.name))

        symbol=SymbolContent(csect)
        self.__symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s CSECT added to symbol table: '%s'" \
                    % (eloc(self,"__csect_new"),csect_name))

        return csect

    # Access symbol table to retrieve a CSECT instance
    # Raises a KeyError if not present in the symbol table.
    # Raises an AssemblerError if symbol defined but isn't a CSECT
    def __csect_ref(self,stmt,sect_name):
        ste=self.__symbol_ref(sect_name)
        sect=ste.content()
        if not isinstance(sect,Section) or sect.isdummy():
            raise AsseblerError(line=stmt.lineno,\
                msg="symbol is not a CSECT: '%s'" % sect_name)
        return sect

    # Determines if it is safe to create a new named csect.
    # Raises an AssemblerError if not.
    def __csect_safe(self,stmt,sect_name):
        try:
            self.__symbol_ref(sect_name)
            # Success by this method means the named CSECT is already defined
            raise AssemblerError(line=stmt.lineno,\
                msg="can not create CSECT, CSECT name defined: %s" % sect_name)
        except KeyError:
            pass

    # Create an unnamed control section and regiser it with the active region
    def __csect_unname(self,debug=False):
        section=Section("")

        if __debug__:
            if debug:
                print("%s Created new: %s" \
                    % (eloc(self,"__csect_unname"),section))

        self.__check_cur_reg(debug=debug)
        self.cur_reg.append(section)

        if __debug__:
            if debug:
                print("%s added %s to current region: '%s'" \
                    % (eloc(self,"__csect_unname"),section.name,self.cur_reg.name))

        return section

    # Tests whether the unnamed control section can be created.
    def __csect_unname_safe(self,stmt):
        if self.unname_sec:
            raise AssemblerError(line=stmt.lineno,msg="unnamed CSECT already exists")

    def __dsect_activate(self,section,debug=False):
        assert isinstance(section,Section) and section.isdummy(),\
            "%s 'section' argument must be a DSECT: %s" \
                % (eloc(self,"__dsect_activate"),section)

        self.cur_sec=section

        if __debug__:
            if debug:
                cls_str=eloc(self,"__dsect_activate")
                print("%s current active region is:  '%s'" % (cls_str,self.cur_reg))
                print("%s current active section is: '%s'" \
                    % (cls_str,self.cur_sec.name))

    # Creates a new CSECT, adds it to the active region and symbol table.
    # Returns the new Section instance to the caller.    
    def __dsect_new(self,line,dsect_name,debug=False):
        if not self.case:
            dsect=Section(dsect_name.upper(),dummy=True)
        else:
            dsect=Section(dsect_name,dummy=True)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"__dsect_new"),dsect))

        self.dsects.append(dsect)
        symbol=SymbolContent(dsect)
        self.__symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s DSECT added to symbol table: '%s'" \
                    % (eloc(self,"__dsect_new"),dsect_name))

        return dsect

    # Access symbol table to retrieve a DSECT instance
    # Raises a KeyError if not present in the symbol table.
    # Raises an AssemblerError if symbol defined but isn't a CSECT
    def __dsect_ref(self,stmt,sect_name):
        ste=self.__symbol_ref(sect_name)
        sect=ste.content()
        if not isinstance(sect,Section) or not sect.isdummy():
            raise AsseblerError(line=stmt.lineno,\
                msg="symbol is not a DSECT: '%s'" % sect_name)
        return sect

    # Adds the Img as a symbol
    def __image_new(self,debug=False):
        image=self.imgwip
        symbol=SymbolContent(image)
        symbol.attrSet("I",0)
        self.__symbol_define(symbol,0)

    # Defines a label based upon the supplied statement's location.
    # Label's location is based upon the Stmt.content object's location
    # Method Arguments:
    #   stmt    The Stmt object whose label is being defined.  The Stmt.content's
    #           Binary object defines the label's value.
    #   length  The length assigned to the label.  If None is specified or ommitted,
    #           the length of the of the Stmt.content Binary object becomes the
    #           label's assigned length.  Defaults to None.
    def __label_create(self,stmt,length=None):
        if stmt.label is None:
            return

        bin=stmt.content
        if length is None:
            leng=bin._length
        else:
            leng=length

        sym=Symbol(stmt.label,bin.loc,leng)
        self.__symbol_define(sym,line=stmt.lineno)

    # Pass 1 - Create the binary content for a new statement.
    #
    # Method arguments:
    #   stmt       The Stmt instance for which the new content is being created
    #   alignment  Alignement of the binary content.
    #   length     Length of the binary content (can be zero)
    def __new_content(self,stmt,alignment=0,length=0,debug=False):
        # Create Binary instance for the new content
        bin=Binary(alignment,length)
        # Establish the content for this statement 
        stmt.content=bin
        # Make sure a section exists to which the binary content is added
        self.__check_cur_sec(debug=debug)
        # Assign to it its '*' value
        self.cur_sec.assign(bin)
        # Current location counter is start of binary with a section relative address
        self.cur_loc.assign(bin)
        # If a label is present, assign it this value and length
        self.__label_create(stmt)

    # The supplied region becomes the active region and its active CSECT the 
    # active CSECT of the assembly.
    def __region_activate(self,region,debug=False):
        assert isinstance(region,Region),\
            "%s 'region' argument must be an instance of Region: %s"\
                % (eloc(self,"__region_activate"),region)

        if __debug__:
            if debug:
                print("%s region activation started" % eloc(self,"__region_activate"))

        self.cur_reg=region
        self.cur_sec=region.cur_sec
        if self.cur_sec:
            self.cur_loc.establish(self.cur_sec.current())

        if __debug__:
            if debug:
                print("%s current active region is:  '%s'" 
                    % (eloc(self,"__region_activate"),self.cur_reg.name))
                if self.cur_sec is None:
                    print("%s current active section is: None" \
                        % eloc(self,"__region_activate"))
                else:
                    print("%s current active section is: '%s'" \
                        % (eloc(self,"__region_activate"),self.cur_sec.name))

    # Creates a new region, adds it to the region list and symbol table.
    # Returns the new Region instance to the caller.
    def __region_new(self,line,region_name,start,debug=False):
        # Now that we have successfully processed the START statement, the new Region
        # instance can be built.
        if not self.case:
            region=Region(region_name.upper(),start)
        else:
            region=Region(region_name,start)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"__region_new"),region))

        symbol=SymbolContent(region)
        self.__symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s region added to symbol table: '%s'" \
                    % (eloc(self,"__region_new"),region_name))

        self.imgwip.append(region)

        if __debug__:
            if debug:
                print("%s regions in Img: %s" \
                    % (eloc(self,"__region_new"),len(self.imgwip.elements)))

        return region

    # Access symbol table to retrieve a Region instance.
    def __region_ref(self,stmt,reg_name):
        try:
            ste=self.__symbol_ref(reg_name)
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="region symbol is undefined: '%s'" % reg_name)

        # symbol is defined, but determine if it is a Region or not
        try:
            region=ste.content()
            if not isinstance(content,Region):
                # The symbol defines content, but not Region content
                region=None
        except NotImplementedError:  
            # This means the symbol value is not Content, so not a Region
            region=None

        if region is None:
            raise AssemblerError(line=stmt.lineno,\
                msg="symbol is not a region: '%s'" % reg_name)

        # Symbol defines a region so return it without having raised any exceptions
        return region

    # Determines if it is safe to create a new named region
    # Raises an AssemblerError if not.
    def __region_safe(self,stmt,reg_name):
        try:
            self.__symbol_ref(reg_name)
            raise AssemblerError(line=stmt.lineno,\
                msg="can not create named region, region name defined: %s" % reg_name)
        except KeyError:
            pass

    # Creates an unnamed region, adding it to the image being created
    # Returns:
    #   the created unnamed region
    def __region_unname(self,start,debug=False):
        region=Region("",start)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"__region_unname"),region))

        self.imgwip.append(region)

        if __debug__:
            if debug:
                print("%s regions in Img: %s" \
                    % (eloc(self,"__region_unname"),len(self.imgwip.elements)))

        return region

    def __region_unname_safe(self,stmt):
        if self.unname_reg:
            raise AssemblerError(line=stmt.lineno,\
                msg="unnamed region already existst")

    # Returns the address to be used in a structure:
    #   Absolute Address - returns the absolute address
    #   CSECT Relative - raises a AssemblerError
    #   DSECT Relative - returns the relative displacement (treating it as an integer)
    #   integer - returns the integer.
    def __struct_address(self,stmt,opn,addr):
        if isinstance(addr,int):
            return addr
        if isinstance(addr,Address): 
            if addr.isAbsolute():
                return addr.address
            if addr.isDummy():
                return addr.value
        raise MSLError(line=stmt.lineno,\
            msg="%s operand %s may not be CSECT relative: %s" \
                % (stmt.instu,opn,addr))

    # Returns the value to be used in a bimodal address mode PSW
    # raises an AssemblerError if an invalid value is supplied.
    def __struct_bimode(self,stmt,opn,amode):
        try:
            return Assembler.bimodes[amode]
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s is an invalid bimodal address mode: %s" \
                    % (stmt.instu,opn,amode))

    # This method validates that amode is consistent for 24-bit vs 31-bit
    def __struct_bimode_check(self,stmt,opn,am,addr):
        if not am and (addr > 0xFFFFFF):
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s must be a 24-bit address: %s" \
                    % (stmt.instu,opn,hex(addr)))

    # Returns the value to be used in a trimodal address mode PSW
    # raises an AssemblerError if an invalid value is supplied.
    def __struct_trimode(self,stmt,opn,amode):
        try:
            return Assembler.trimodes[amode]
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s is an invalid trimodal address mode: %s" \
                    % (stmt.instu,opn,amode))

    # This method validates that amode is consistent for 24-bit vs 31-bit
    def __struct_trimode_check(self,stmt,opn,am,addr):
        if am == 0 and (addr > 0xFFFFFF):
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s must be a 24-bit address: %s" \
                    % (stmt.instu,opn,hex(addr)))
        if am == 1 and (addr > 0x7FFFFFFF):
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s must be a 31-bit address: %s" \
                    % (stmt.instu,opn,hex(addr)))

    # Define a unique symbol in the symbol table.
    def __symbol_define(self,sym,line):
        self.ST.add(sym,line=line)

    # Return a symbol table entry (STE) being referenced.  Does NOT update the list
    # of referencing line numbers.
    # Raises KeyError if not defined
    def __symbol_ref(self,sym):
        return self.ST.get(sym)

    #
    # QUASI PUBLIC METHODS
    #

    def _getAttr(self,name,attr,line):
        ste=self.__symbol_ref(name)
        try:
            value=ste.attrRef(attr)
        except KeyError:  # attr not defined for symbol
            raise AssemblerError(line=line,\
                msg="symbol '%s' does not support attribute: '%s'" \
                    % (name,attr))

        assert value is not None,\
            "%s attribute of symbol '%s' not initialized: '%s'" \
                % (eloc(self,"_getAttr"),name,attr)

        # Good attribute reference, so update STE with reference
        ste.reference(line)
        return value

    # Returns the symbol table entry without generating a symbol reference
    def _getSTE(self,name):
        return self.__symbol_ref(name)

    # Returns the symbol table entry in its entirety (including symbol attributes).
    # Generates a reference to the symbol for the supplied line.
    def _getSTE_Ref(self,name,line):
        ste=self.__symbol_ref(name)
        ste.reference(line)
        return ste

    # Returns a symbols value and updates its list of referenced lines.
    # Raises KeyError if not defined
    def _getSymbol(self,string,line):
        ste=self.__symbol_ref(string)
        value=ste.value()
        ste.reference(line)
        return value

    # Attempt to resolve an address into its base/displacement pair of values.
    # Raises an AssemblerError exception if resolution fails.
    def _resolve(self,address,lineno,opn,size,trace=False):
        try:
            return self.bases.find(address,size,self,trace=trace)
        except KeyError:
            raise AssemblerError(line=lineno,\
                msg="operand %s could not resolve implied base register for "
                    "location: %s" % (opn,address)) from None

    #
    # INSTRUCTION AND DIRECTIVE PASS PROCESSING METHODS
    #
    # All methods share the same signature:  
    #      method_name(Stmt-instance,trace=False)
    # These methods are called by the public assemble() method
    #
    # These methods do not need to validate operand quantity or the presenct of
    # a required label.  This has already been done in the Stmt.validate() method 
    # called by Assembler.statement() method before the statement has been queued
    # for processing.  If we got here, we are good to go in these matters.

    # PASS 1 and 2 METHODS


    # CCW  - Build a Channel Command Word based on XMODE CCW settiong
    #
    # [label] CCW    command,address,flags,count
    # 
    # CCW is an XMODE generic directive.  The current XMODE CCW setting dictates
    # whether CCW0 or CCW1 is selected.  If CCW XMODE is set to 'none', the CCW
    # directive will not be recognized.
    #
    # CCW is totally implemented within __oper_id() method through operation selection.
    # Nothing is required here for it.
   
    
    # CCW0 - Build a Channel Command Word Format-0 (format 0 explicit)
    # 
    # [label] CCW0    command,address,flags,count
    def _ccw0_pass1(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8,debug=idebug)

    def _ccw0_pass2(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract CCW/CCW0 operand values after expression evalution
        code=stmt.operands[0].getValue()
        address=stmt.operands[1].getValue()
        flags=stmt.operands[2].getValue()
        count=stmt.operands[3].getValue()

        ccwflags=flags & 0xFE # Make sure bit 39 is zero

        inst=stmt.instu

        # Validate CCW/CCW0 Address - Operand 2
        if isinstance(address,Address):
            if not address.isAbsolute():
                raise AssemblerError(line=stmt.lineno,\
                    msg="%s operand 2 result must be an absolute address: %s" \
                        % (inst,address))
            ccwaddr=address.address
        else:
            ccwaddr=address

        # Build an insnbldr.Field object for each CCW field
        inst=stmt.instu

        # Build the CCW or CCW0 content
        values=[code,ccwaddr,ccwflags,count]
        bytes=self.__build_structure(inst,stmt,values=values)
        # Update the statements binary content with the CCW0
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=idebug)


    # CCW1 - Build a Channel Command Word Format-1
    # 
    # [label] CCW1    command,address,flags,count
    def _ccw1_pass1(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _ccw1_pass2(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract CCW1 operand values after expression evalution
        code=stmt.operands[0].getValue()
        address=stmt.operands[1].getValue()
        flags=stmt.operands[2].getValue()
        count=stmt.operands[3].getValue()

        ccwflags=flags & 0xFE   # Make sure bit 15 is 0

        # Validate CCW1 Address - Operand 2
        if isinstance(address,Address):
            if not address.isAbsolute():
                raise AssemblerError(line=stmt.lineno,\
                    msg="CCW0 operand 2 result must be an absolute address: %s" \
                        % address)
            ccwaddr=address.address
        else:
            ccwaddr=address

        # Build the CCW1 content
        values=[code,ccwflags,count,ccwaddr]
        bytes=self.__build_structure("CCW1",stmt,values=values)
        # Update the statements binary content with the CCW1
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=idebug)


    # CSECT - start or continue a named or unnamed control section
    # 
    # [label] CSECT    # no operands
    def _csect_pass1(self,stmt,trace=False):
        cdebug=trace or stmt.trace

        csect_name=stmt.label   # Fetch the CSECT name from the label field
        if csect_name is None:
            # No label, so the unnamed CSECT is being targeted
            if self.unname_sec is None:
                # Create the unnamed CSECT if it does not exist
                csect=self.__csect_unname(debug=cdebug)
            else:
                # Continue the existing unnamed CSECT
                csect=self.unname_sec
        else:
            # Label is present, so targeting a named CSECT
            try:
                csect=self.__csect_ref(stmt,csect_name)
                # Continuing an existing CSECT
            except KeyError:
                # Create a new named CSECT
                csect=self.__csect_new(stmt.lineno,csect_name,debug=cdebug)

        # Make the found or newly created CSECT the active section
        self.__csect_activate(csect,debug=cdebug)
        stmt.laddr=csect

    def _csect_pass2(self,stmt,trace=False):
        csect=stmt.laddr
        addr1=csect.loc
        addr2=addr1+max(len(csect)-1,0)
        stmt.laddr=[addr1,addr2]


    # DC - Define Constant
    # DS - Define Storage
    #
    # [label] DC   desc'values',...
    # [label] DS   desc,...
    def _dcds_pass1(self,stmt,trace=False):
        edebug=otrace=False
        if __debug__:
            cls_str=eloc(self,"_dcds_pass1")
            otrace=self.__is_otrace("dc")
            edebug=self.dm.isdebug("exp")
           
        # Make sure we have an active current section before doing anything more
        self.__check_cur_sec(debug=otrace)

        gscope=stmt.gscope

        # Unroll operands into a series of objects.
        gscope=stmt.gscope
        gscope.Pass1(stmt,self,debug=edebug,trace=trace)
        values=gscope.values

        # If the statement truly has no operands, that is an error that should
        # have been detected long before here.  This suggests a problem with
        # the Pass0 and/or Pass1 processing in asmfsmcs.DCDS_Scope or
        # asmfsmcs.DCDS_Operand objects.
        assert len(values)>0,\
            "%s [%s] DS/DS statement failed to produce values" \
                % (eloc(self,"_dcds_pass1"),stmt.lineno)

        if __debug__:
            if otrace:
                for item in values:
                    print("%s - %r" % (item,item))

        area=Area()
        cur_sec=self.cur_sec

        # Assemble each nominal value or storage allocation.
        for value in values:
            # value is either a asmfsmcs.DCDS_Operand or asmdcds.Nominal object.
            if __debug__:
                if otrace:
                    print("%s operand: %s" % (cls_str,value))

            # Note: both asmfsmcs.DCDS_Operand and asmdcds.Nominal support the
            # align() and length() methods so that they can both be the basis
            # of binary object.
            if isinstance(value,asmfsmcs.DCDS_Operand):
                bin=Binary(value.align(),0)
            else:
                bin=Binary(value.align(),value.length())
            cur_sec.assign(bin)

            if __debug__:
                if otrace:
                    print("%s cur_sec %s _alloc=%s" \
                        % (cls_str,self.cur_sec,self.cur_sec._alloc))

            area.append(bin)
            value.content=bin
            
            if __debug__:
                if otrace:
                    print("%s value.content: %s" % (cls_str,value.content))

        area.fini(trace=otrace)
        # Note the binary images in the area object are also linked to the Section
        # object via its elements list.

        stmt.content=area

        # Define the statement's label, if present, using the length and location
        # of the initial nominal value. (In this case the location of the initial
        # nominal value is the same as the location of the Area object.)
        self.__label_create(stmt,length=values[0].length())

    def _dc_pass2(self,stmt,trace=False):
        edebug=etrace=False
        if __debug__:
            edebug=self.dm.isdebug("exp")
            etrace=self.dm.isdebug("tracexp") or trace or stmt.trace \
                or self.__is_otrace("dc")
            cls_str=eloc(self,"_dc_pass2")

        for n,value in enumerate(stmt.gscope.values):
            if __debug__:
                if etrace:
                    print("%s %s" % (cls_str,value))
                    
            

            # Build and store image content in Binary
            value.build(stmt,self,n,debug=edebug,trace=etrace)

        if __debug__:
            if trace:
                print(stmt.content.elements)

        self.dcs.append(stmt)  # remember to fill in my binary data for the listing


    # DROP - Remove a previous base register assignment
    #
    # [label] DROP   reg (1-16 operands allowed)
    def _drop_pass1(self,stmt,trace=False):
        otrace=trace or self.__is_otrace("drop")
        bin=Binary(0,0)    # Create a dummy Binary instance for the statement
        stmt.content=bin   # Establish the DROP statement's binary content
        self.__check_cur_sec(debug=otrace)
        self.cur_sec.assign(bin)   # Assign to it its '*' value
        self.__label_create(stmt)  # If a label is present, assign it this value
        # Nothing else to do in pass 1

    def _drop_pass2(self,stmt,trace=False):
        dtrace=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or dtrace
        edebug=self.dm.isdebug("exp")
        if __debug__:
            if dtrace:
                print("%s %s operands: %s" \
                    % (eloc(self,"_drop_pass2"),stmt.inst,stmt.operands))

        stmt.evaluate_operands(debug=edebug,trace=etrace)
        regs=[]
        for x in range(len(stmt.operands)):
            if dtrace:
                print("%s register operand number: %s" % (cls_str,x))
            reg=stmt.operands[x].getValue()
            regs.append(reg)
            
        if __debug__:
            if dtrace:
                print("%s bases being dropped for registers: %s" \
                    % (eloc(self,"_drop_pass2"),regs))

        for r in regs:
            self.bases.drop(r,trace=dtrace)

        if __debug__:
            if dtrace:
                print("%s\n%s" % (eloc(self,"_drop_pass2"),\
                    self.bases.print(indent="    ",string=True)))


    # DSECT - start of continue a dummy section
    # 
    # label DSECT   # no operands
    def _dsect_pass1(self,stmt,trace=False):
        # Continue an existing DSECT or start a new one
        cls_str="assembler.py - %s._csect_pass1() -" % self.__class__.__name__
        ddebug=trace or stmt.trace

        dsect_name=stmt.label   # Fetch the DSECT name from the label field

        try:
            sect=self.__dsect_ref(stmt,dsect_name)
            # Continuing an existing DSECT
        except KeyError:
            dsect=self.__dsect_new(stmt.lineno,dsect_name,debug=ddebug)

        # Make the found or newly created CSECT the active section
        self.__dsect_activate(dsect,debug=ddebug)


    # END - terminate the assembly and assign the output image to the label
    #       field symbol if present.  Image symbol defaults to IMAGE
    #
    # [label] END     [comments]
    def _end_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=0,length=0)

        self.LB.end()      #  Tell Line Buffer, no more input

    def _end_pass2(self,stmt,trace=False):
        scope=stmt.parsed
        if scope is None:
            # No entry address, so nothing to do
            return
        # Calculate entry address
        desc="END %s" % stmt.lineno
        fsmp=self.fsmp
        expr=fsmp.L2ArithExpr(desc,stmt,ltoks=scope.lextoks)
        self.entry=entry=expr.evaluate(self,debug=False,trace=trace)
        stmt.laddr=[None,entry]


    # ENTRY - Define a reported entry point address
    # 
    # [label] ENTRY   <entry-point>
    def _entry_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=0,length=0)

    def _entry_pass2(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        entry=stmt.operands[0].getValue()
        stmt.laddr[0]=entry       # Print the value in the listing in ADDR1
        self.entry=entry          # Report this value.


    # EQU - Define a symbol
    # 
    # label EQU     expression
    def _equ_pass1(self,stmt,trace=False):
        etrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or etrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)
        new_symbol=stmt.label
        equate=stmt.operands[0]

        new_length=None
        if len(stmt.operands)==2:
            new_length=stmt.operands[1].getValue()
        new_value=equate.getValue()
        if isinstance(new_value,SectAddr):
            self.equates.append(new_value)
        if isinstance(new_value,Address):
            if new_length is None:
                # Reach back into the original PToken pratt parser list to find
                # the first symbol in the expression token stream
                common_parser=self.parsers["common"]
                pparser=common_parser.pratt
                plit=pparser.extract_symbol(equate.exprs[0])
                if plit is None:
                    new_length=0
                else:
                    # Now reach back into the symbol table and pluck out the length
                    # attribute
                    lsym=plit.symbol()
                    ste=self.__symbol_ref(lsym)
                    new_length=ste.attrGet("L")
        else:
            # Must be an integer
            if new_length is None:
                new_length=1
 
        new_ste=Symbol(new_symbol,new_value,new_length)
        self.__symbol_define(new_ste,stmt.lineno)
        stmt.laddr=[new_value,new_length]


    # MNEMONIC - Machine Instruction generation
    # 
    # [label] MNEMONIC  [instruction operands as needed]
    def _insn_pass1(self,stmt,trace=False):
        insn=stmt.insn         # Instruction cache entry (MSLentry object)    
        length=insn.length     # length of the instruction in bytes

        # Create the content definition for the machine instruction
        bin=Binary(2,length)   # Always put instructions on half word boundary

        # Assign space in the active section for the machine instruction
        self.__check_cur_sec(debug=trace)
        self.cur_sec.assign(bin)

        # Update the stmt instance with instruction format and content information
        stmt.format=insn.mslformat   # msldb.Format instance
        stmt.content=bin             # Plece in statement

        # Define the statement's label if present
        self.__label_create(stmt)

    def _insn_pass2(self,stmt,trace=False):
        idebug=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or idebug
        edebug=self.dm.isdebug("exp")

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Resolve all values in preparation for machine instruction construction:
        # calculate base/displacements, relative immediate, find lengths, etc.
        operands=stmt.operands
        laddrs=[]
        for ndx in range(len(operands)):
            opr=operands[ndx]
            opr.resolve(self,stmt,ndx,trace=idebug)
            if opr.laddr is not None:
                laddrs.append(opr.laddr)
        
        # Figure out what should go into the ADDR1 and ADDR2 listing fields
        if len(laddrs)==1:
            stmt.laddr.append(laddrs[0])
        elif len(laddrs)>=2:
            stmt.laddr.append(laddrs[0])
            stmt.laddr.append(laddrs[-1])
        else:
            pass
            
        self.builder.build(stmt,trace=idebug)


    # ORG - adjust current location
    #
    # [label] ORG  expression
    def _org_pass1(self,stmt,trace=False):
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or trace or stmt.trace

        bin=Binary(0,0)    # Create a dummy Binary instance for the statement
        stmt.content=bin   # Establish the ORG statements binary content
        self.__check_cur_sec(stmt.lineno)  # Check that a CSECT is active
        self.cur_sec.assign(bin)   # Assign to it its '*' value
        addr1=bin.loc              # Save value for listing
        self.__label_create(stmt)  # If a label is present, assign it this value

        # Now adjust to new location
        # Evaluate the starting address
        stmt.evaluate_operands(debug=edebug,trace=etrace)
        operand=stmt.operands[0]
        new_loc=operand.getValue()

        # Validate we can use the result to adjust the location
        if not isinstance(new_loc,Address):
            AssemblerError(line=stmt.lineno,\
                msg="ORG result must be an address: %s" % new_loc)
        if not new_loc.isRelative():
             AssemblerError(line=stmt.lineno,\
                msg="ORG result must be a relative address: %s" % new_loc)

        cur_sec=self.cur_sec
        if new_loc.section!=cur_sec:
            AssemblerError(line=stmt.lineno,\
                msg="ORG result must be in the active section ('%s'): %s" \
                    % (cur_sec.name,new_loc))

        cur_sec.org(new_loc)
        self.cur_loc.establish(new_loc)
        stmt.laddr=[addr1,new_loc]


    # PSW  - Build a Program Status Word based on XMODE PSW settiong
    #
    # [label] PSW   sys,key,a,prog,addr[,amode]
    # 
    # PSW is an XMODE generic directive.  The current XMODE PSW setting dictates
    # which of PSW related directives is selected.  If PSW XMODE is set to 'none', the
    # PSW directive will not be recognized.
    #
    # PSW is totally implemented within __oper_id() method through operation selection.
    # Nothing is required here for it.


    # PSWS - Create a S/360-20 32-bit PSW
    # sys-> bit 7 (CM), key not used, a -> bit 6 (A), prog -> bits 2,3 (CC), 
    # addr -> bits 16-31, amode not used
    #
    # [label] PSWS    sys,key,a,prog,addr[,amode]
    def _psws_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=1,length=4)

    def _psws_pass2(self,stmt,trace=False): 
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract PSWS operand values after expression evalution
        sys=stmt.operands[0].getValue()
        a=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        # Validate PSWS Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Build the PSWS content
        values=[sys,a,prog,pswaddr]
        bytes=self.__build_structure("PSWS",stmt,values=values)
        # Update the statements binary content with the PSWS
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSW360 - Create a standard S/360 64-bit PSW
    # sys -> bits 0-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 34-39
    # addr -> bits 40-63, amode not used
    #
    # [label] PSW360 sys,key,amwp,prog,addr[,amode]
    def _psw360_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _psw360_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract PSW360 operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        amwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        # Validate PSW360 Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Build the PSW360 content
        values=[sys,key,amwp,prog,pswaddr]
        bytes=self.__build_structure("PSW360",stmt,values=values,trace=ptrace)
        # Update the statements binary content with the PSW360
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSW67 - Create a standard S/360 64-bit PSW
    # sys -> bits 0-7, key -> bits 8-11, amwp -> bits 12-15, prog -> bits 34-39
    # addr -> bits 40-63
    #
    # [label] PSW67 sys,key,amwp,prog,addr
    def _psw67_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _psw67_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract PSW360 operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        amwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()
        if len(stmt.operands)==6:
            amode=stmt.operands[5].getValue()
        else:
            amode=0

        # Validate PSW67 Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Validate PSW67 Address Mode - Operand 6
        try:
            pswamode=Assembler.bi67modes[amode]
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="%s operand %s is an invalid 360-67 bimodal address mode: %s" \
                    % (stmt.instu,opn,amode))

        # Build the PSW360 content
        values=[sys,key,amwp,prog,pswaddr,pswamode]
        bytes=self.__build_structure("PSW67",stmt,values=values)
        # Update the statements binary content with the PSW360
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSWBC - Create an basic control mode 64-bit PSW
    # sys -> bits 0-7, key -> bits 8-11, mwp -> bits 13-15, prog -> bits 34-39
    # addr -> bits 40-63, amode not used
    #
    # [label] PSWBC  sys,key,mwp,prog,addr[,amode]
    def _pswbc_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _pswbc_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract PSWBC operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        mwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        # Validate PSWBC Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Build the PSWBC content
        values=[sys,key,mwp,prog,pswaddr]
        bytes=self.__build_structure("PSWBC",stmt,values=values)
        # Update the statements binary content with the PSWBC
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSWEC - Create an S/370 Extended Control mode 64-bit PSW
    # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-24
    # addr -> bits 40-63, amode not used
    #
    # [label] PSWEC  sys,key,mwp,prog,addr[,amode]
    def _pswec_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _pswec_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract PSWEC operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        mwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        sys =  sys  & 0b01000111   # Make sure PSW bits 0 and 2-4 are zero
        prog = prog & 0b10111111   # Make sure PSW bit 17 is zero

        # Validate PSWEC Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Build the PSWEC content
        values=[sys,key,None,mwp,prog,pswaddr]
        bytes=self.__build_structure("PSWEC",stmt,values=values)
        # Update the statements binary content with the PSWEC
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSW380  - Create a Hercles S/380 mode 64-bit PSW
    # PSWXA   - Create an S/370-XA 64-bit PSW
    # PSWE370 - Create an ESA/370 64-bit PSW
    # PSWE390 - Create an ESA/390 64-bit PSW
    #
    # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-23
    # addr -> bits 33-63, amode -> 32
    #
    # [label] PSW380   sys,key,mwp,prog,addr[,amode]
    # [label] PSWXA    sys,key,mwp,prog,addr[,amode]
    # [label] PSWE370  sys,key,mwp,prog,addr[,amode]
    # [label] PSWE390  sys,key,mwp,prog,addr[,amode]
    def _pswbi_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=8)

    def _pswbi_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        inst=stmt.instu

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        mwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        if len(stmt.operands)==6:
            amode=stmt.operands[5].getValue()
        else:
            amode=0

        try:
            pmask=Assembler.biprog[inst]
        except KeyError:
            raise ValueError("%s unrecognized instruction for bimodal prog field "
                "mask: %s" % (eloc(self,"_pswbi_pass2"),inst))

        prog = prog & pmask        # Make sure any reserved bits are zero
        sys =  sys  & 0b01000111   # Make sure PSW bits 0 and 2-4 are zero

        # Validate Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Validate Address Mode - Operand 6
        am=self.__struct_bimode(stmt,6,amode)

        # Make sure we have a 24-bit address if the address mode is 24
        self.__struct_bimode_check(stmt,6,am,pswaddr)

        # Build the content
        values=[sys,key,None,mwp,prog,am,pswaddr]
        bytes=self.__build_structure(inst,stmt,values=values)
        # Update the statements binary content with the PSW
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # PSWZ - Create a z/Architecture mode 128-bit PSW
    # sys -> bits 0-7, key -> bits 8-12, mwp -> bits 13-15, prog -> bits 16-24
    # addr -> 64-127, amode -> bits 31,32
    #
    # [label] PSWZ   sys,key,mwp,prog,addr[,amode]
    def _pswz_pass1(self,stmt,trace=False):
        # Create the binary content and assign a label if present in the statement
        self.__new_content(stmt,alignment=8,length=16)

    def _pswz_pass2(self,stmt,trace=False):
        ptrace=trace or stmt.trace
        edebug=self.dm.isdebug("exp")
        etrace=self.dm.isdebug("tracexp") or ptrace

        inst=stmt.instu

        stmt.evaluate_operands(debug=edebug,trace=etrace)

        # Extract operand values after expression evalution
        sys=stmt.operands[0].getValue()
        key=stmt.operands[1].getValue()
        mwp=stmt.operands[2].getValue()
        prog=stmt.operands[3].getValue()
        addr=stmt.operands[4].getValue()

        if len(stmt.operands)==6:
            amode=stmt.operands[5].getValue()
        else:
            amode=0

        # Validate Address - Operand 5
        pswaddr=self.__struct_address(stmt,5,addr)

        # Validate Address Mode - Operand 6
        am=self.__struct_trimode(stmt,6,amode)

        # Make sure we have a 24-bit address if the address mode is 24 or
        # we have a 31-bit address if the address mode is 31.
        self.__struct_trimode_check(stmt,6,am,pswaddr)

        # Build the content
        values=[sys,key,mwp,prog,am,pswaddr]
        bytes=self.__build_structure("PSWZ",stmt,values=values)
        # Update the statement's binary content with the PSW
        stmt.content.update(bytes,at=0,full=True,finalize=True,trace=ptrace)


    # REGION - continue an existing region
    #
    # label REGION  # no operands
    def _region_pass1(self,stmt,trace=False):
        # Continue an existing region
        rdebug=trace or stmt.trace

        region_name=stmt.label  # Fetch the region name from the label field

        # the REGION must already be defined, we are continueing one already started
        if __debug__:
            if rdebug:
                print("%s referencing region in symbol table: '%s'" \
                    % (eloc(self,"_region_pass1"),region_name))

        region=self.__region_ref(stmt,region_name)
        # If the region is not defined, an AssemblerError will have bailed us out

        # Make the found region the current one.
        self.__region_activate(region,debug=rdebug)
        stmt.laddr=region

    def _region_pass2(self,stmt,trace=False):
        region=stmt.laddr
        addr1=region.loc
        addr2=addr1+(max(len(region)-1,0))
        stmt.laddr=[addr1,addr2]


    # START - start a new control section and an optional region
    #
    # [label] START [address][,[region]]
    def _start_pass1(self,stmt,trace=False):
        csect_name=stmt.label

        # If the CSECT can not be created an AssemblerError is raised
        if csect_name:
            self.__csect_safe(stmt,csect_name)
        else:
            self.__csect_unname_safe(stmt)

        scope=stmt.gscope   # Scope is a asmfsmcs.START_Scope object
        region=scope.region
        start=0
        if scope.new_region:
            # Creating a new region too...
            # If the region can not be created an AssemblerError is generated
            if region:
                self.__region_safe(stmt,region)
            else:
                self.__region_unname_safe(stmt)

            # Calculate the region's starting address if provided, use 0 otherwise
           
            if scope.expr:
                start=self.fsmp.evaluate_expr(self,stmt,scope.expr,\
                    debug=False,trace=False)

            # Create the new region before creating the control section
            if region:
                region=self.__region_new(stmt.lineno,scope.region,start,debug=False)
                # Named region is now in the symbol table and added to the image
            else:
                region=self.__region_unname(start,debug=False)
                # The unnamed region is now added to the image.
            # Make the new region the current active region
            self.__region_activate(region,debug=False)

        # Create the new control section
        if csect_name:
            csect=self.__csect_new(stmt.lineno,csect_name,debug=False)
            # Named control section is now in the symbol table and added to the 
            # current active region.
        else:
            csect=self.__csect_unname()
            # The unnamed control section is now part of the current active region.

        # If there was no active region, a new unnamed region was automatically
        # created even if no operands defining a region were supplied.

        # Make the new control section the active one.
        self.__csect_activate(csect)

        # If this is the first START directive
        if self.load is None:
            self.load=start
            self.entry=start  # An END directive can supply a different entyr point

        stmt.laddr=csect

    def _start_pass2(self,stmt,trace=False):
        csect=stmt.laddr
        addr1=csect.loc
        addr2=addr1+max(len(csect)-1,0)
        stmt.laddr=[addr1,addr2]


    # USING - define base register(s)
    #
    # [label] USING address,reg   (1 to 16 registers allowed)
    def _using_pass1(self,stmt,trace=False):
        bin=Binary(0,0)    # Create a dummy Binary instance for the statement
        stmt.content=bin   # Establish the USING statement's "binary" content
        self.cur_sec.assign(bin)   # Assign to it its '*' value
        # Define the statement's label if present
        self.__label_create(stmt)

    def _using_pass2(self,stmt,trace=False):
        utrace=trace or stmt.trace
        etrace=self.dm.isdebug("tracexp") or utrace
        edebug=self.dm.isdebug("exp")
        if utrace:
            cls_str="assembler.py - %s._using_pass2() -" % self.__class__.__name__
            print("%s %s operands: %s" % (cls_str,stmt.inst,stmt.operands))

        stmt.evaluate_operands(debug=edebug,trace=etrace)
        addr=stmt.operands[0].getValue()
        regs=[]
        for x in range(1,len(stmt.operands)):
            if utrace:
                print("%s register operand number: %s" % (cls_str,x))
            reg=stmt.operands[x].getValue()
            regs.append(reg)
        if utrace:
            print("%s bases being assigned to registers: %s" % (cls_str,regs))

        for r in regs:
            self.bases.using(r,addr,trace=utrace)
            addr=addr+4096

        if utrace:
            print("%s\n%s" % (cls_str,self.bases.print(indent="    ",string=True)))

    #
    # PUBLIC METHODS
    #

    # Assemble queued statements.
    #
    # As each statement in the list of queued statements is encountered, its
    # defimed processing method for the current pass is called.  If the method
    # is None or the statement has been flagged as ignore=True, the statememt is not
    # processed.
    def assemble(self):
        # Because the statement() method may be called multiple times, I don't
        # really know we are done with input until this method is called.
        if not Stats.stopped("pass0_p"):
            Stats.stop("pass0_p")
            Stats.stop("pass0_w")

        cls_str="assembler.py - %s.assemble() -" % self.__class__.__name__
        if self.aborted:
            raise ValueError("%s ASMA has aborted - can not assemble statememts" \
                % cls_str)
        self.assemble_called=True
        passes=len(self.passes)
        fail=self.fail

        for pas in range(1,passes):
            self.cur_pass=pas

        # START PASS PROCESSING
            paso=self.passes[pas]       # Get the Pass instance for this Pass
            if paso is None:
                raise ValueError("%s Pass instance undefined for pass: %s" \
                    (cls_str,pas))
            Stats.start(paso.proc)
            Stats.start(paso.wall)
            pdebug=paso.trace           # set the pass trace variable
            if pdebug:
                print("%s PASS %s STARTED" % (cls_str,pas))

            # DO PRE-STATEMENT PROCESSING
            pre_method=paso.pre         # Get the method for pre-processing
            if pre_method is None:
                if pdebug:
                    print("%s PASS %s has no pre statement processing" \
                        % (cls_str,pas))
            else:
                if pdebug:
                    method="%s.%s()" % satkutil.method_name(pre_method)
                    print("%s PASS %s pre-processing method: %s - STARTED" \
                        % (cls_str,pas,method))
                pre_method(trace=pdebug)
                if pdebug:
                    print("%s PASS %s pre-processing method: %s - COMPLETED" \
                        % (cls_str,pas,method))

            # DO STATMENT PROCESSING
            if paso.stmts:              # Process statements if Pass object says to
                if pdebug:
                    print("%s PASS %s statement processing..." % (cls_str,pas))
                for s in self.stmts:
                    if s.ignore:
                        if pdebug:
                            print("%s pass %s ignoring:\n    %s" % (cls_str,pas,s))
                        continue
                    method=s.asmpasses[pas]
                    if method is None:
                        continue

                    if pdebug:
                        name="%s.%s()" % satkutil.method_name(method)
                        print("%s pass %s:method=%s" % (cls_str,pas,name))

                    self.cur_stmt=s   # Make current statement referencable globally
                    if pas==2:
                        self.cur_loc.update(s.content)
                    if fail:
                        method(s,trace=pdebug)
                    else:
                        try:
                            method(s,trace=pdebug)
                        except AssemblerError as ae:
                            cls_str="assembler.py - %s.%s() -" \
                                % satkutil.method_name(method)
                            self.__ae_excp(ae,s,string=cls_str,debug=False)

                    self.cur_loc.increment(s.content)
                    self.cur_stmt=None   # De-reference the current statement
            else:
                if pdebug:
                    print("%s PASS %s does not process statements" % (cls_str,pas))

            # DO POST STATEMENT PROCESSING
            post_method=paso.post         # Get the method for pre-processing
            if post_method is None:
                if pdebug:
                    print("%s PASS %s has no post statement processing" \
                        % (cls_str,pas))
            else:
                if pdebug:
                    method="%s.%s()" % satkutil.method_name(post_method)
                    print("%s PASS %s post-processing method: %s - STARTED" \
                        % (cls_str,pas,method))
                post_method(trace=pdebug)
                if pdebug:
                    print("%s PASS %s post-processing method: %s - COMPLETED" \
                        % (cls_str,pas,method))

            if pdebug:
                print("%s PASS %s COMPLETED" % (cls_str,pas))
            
            Stats.stop(paso.wall)
            Stats.stop(paso.proc)
        # PASS PROCESSING COMPLETED

        # Complete Processing
        Stats.start("output_p")
        Stats.start("output_w")
        self.__finish()   # Complete the Image before providing to listing generator
        self.LM.create()  # Generate listing and place it in the final Image object
        Stats.stop("output_w")
        Stats.stop("output_p")
        
        Stats.stop("assemble_w")
        Stats.stop("assemble_p")
        Stats.stop("wall")
        Stats.stop("process")
        Stats.statements(len(self.stmts))
        
        # Print statistics if requested here.
        
        if self.stats:
            print(Stats.report())

    # Returns the completed Image instance for processing
    def image(self):
        return self.img

    # Parses an input line of text
    # Identifies the type of statement
    # Recognizes the instruction or directive
    # Validates operand syntax is compatible with the instruction/directive operands
    #
    # At successful conclusion of this process, a Stmt instance will be queued for
    # assembly within the Assembler (stmts attribute).  And each input text line
    # will be added to the Image instance to print the original source input.
    #
    # Any error will raise an AssemblerError exception
    def statement(self,string=None,filename=None):
        if not self.timers_started: 
            if not Stats.started("assemble_p"):
                Stats.start("assemble_p")
                Stats.start("assemble_w")
            if not Stats.started("pass0_p"):
                Stats.start("pass0_p")
                Stats.start("pass0_w")
        # Either I started the timers or they were already started.
        # Whichever the case, I don't need to do this again
        self.timers_started=True

        # Try to avoid recall if a big problem happened.
        if self.aborted:
            raise ValueError("%s ASMA has aborted - statements not accepted" \
                % eloc(self,"statement"))
        if self.assemble_called:
            self.__abort(msg="%s statement not accepted after assemble called")

        self.cur_pass=0

        # Accept input.  With a LIFO stack, a string if submitted with a filename
        # will be seen for processing before the file input.
        if string is not None:
            assert isinstance(string,str),\
                "%s 'string' argument if provided must be a string: %s" \
                    % (eloc(self,"statement"),string)

            self.LB.line(string)

        # Accept input...
        if filename is not None:
            assert isinstance(filename,str),\
                "%s 'filename' argument if provided must be a string: %s" \
                    % (eloc(self,"statement"),filename)

            self.LB.newFile(filename)

        sdebug=self.dm.isdebug("stmt")

        # Pre-process all buffered input lines and any more that get included during
        # the processing.
        try:
            while True:
                try:
                    ln=self.LB.getline()
                    if __debug__:
                        if sdebug:
                            print("%s: Processing line:\n    %s" \
                                % (eloc(self,"statement"),ln))
                except asmmacs.MacroError as me:
                    # An error was detected in a macro invocation.
                    # If we are failing immediately upon any detected error, do so now
                    if self.fail:
                        raise me from None
                    # Not failing immediately, so we need to terminate the remainder
                    # of the macro.
                    ae=AssemblerError(line=me.line,linepos=me.linepos,msg=me.msg)
                    # Queue it for ultimate output
                    self.img._error(ae)
                    # The invoked macro has terminated, but continue reading input
                    # from the source that generated the macro statement invocation.
                    continue

                # Add the line to ths wip image after symbol replacement
                self.img._statement(ln)

                s=Stmt(ln)
                # Set the print status for this statement based upon the current
                # global settings.
                s.pon=self.pon          # PRINT ON or PRINT OFF
                s.pgen=self.pgen        # PRINT GEN or PRINT NOGEN
                s.pdata=self.pdata      # PRINT DATA or PRINT NODATA
              
                # add the statement to our list of Stmt objects and pre-process.
                self.stmts.append(s)
                
                # The following actions occur during pre-processing:
                #   1. statement is classified;
                #   2. operation name is recognized (directive vs. machine 
                #      instruction vs. defined macro);
                #   3. if special pre-processing is specified, it is performed, for
                #      example invoked macros;
                #   4. otherwise, the assembler directive or machine instruction
                #      operands are parsed and results validated, although expressions
                #      have not yet been evaluated.
                # At the end of this process, the statement is queued for later 
                # assembly via the assemble() method.
                self.__pre_process(s,debug=sdebug)
        except asminput.BufferEmpty:
            pass

#
#  +------------------------------------+
#  |                                    |
#  |   Internal Tables and Structures   |
#  |                                    | 
#  +------------------------------------+
#

# This object drives statement processing through the various passes and provides other
# statement specific information.
#
# Instance Arguments:
#    instruction     This is the Insn instance associated with the instruction
#    parser          Identifies the operand parser for this statement
#    spp             Special pre-processor method used instead of parser
#    pass1-passN     Specifies the method to be called during pass of the assembler
#    optional        Specify True if the label field of the instruction is optional.
#                    Specify False if the label field is required in the instruction.
#                    Default is True (that is, a label defaults to being optional).
#    min             The minimal number of operands alloweds by this statement
#    max             The maximum number of operands allowed.  None implies no limit.
#    cls             List of classes to be used to validate directive operands.
#                    These are the classes themselves, all subclass of Operand, not
#                    instantiated objects.  Not used for machine instructions.
#    directive       Specify True to indicate this statement is a directive.
#                    Specify False to indicate a machine instruction.  Default is True.
class AsmPasses(object):
    def __init__(self,name=None,spp=None,parser=None,pass1=None,pass2=None,\
        optional=True,min=None,max=None,cls=[],directive=True):
        super().__init__()

        # Note, attributes with an '*' are updated by the AsmInsn.__init__()

        # These attributes are shared by both directives and instructions
        # Attributes with an '*' are updated by the AsmInsn.__init__()
        self.name=name                 # Name of the directive or instruction
        self.min_operands=min          # Minimum number of operands
        self.max_operands=max          # Maximum number of operands
        self.directive=directive       # True means a directive, False an instruction
        self.parser=parser             # syntactical analyzer for statement operands
        self.optional=optional         # If False, label is not optional, required
        # This attribute is update by AsmInsn in __init__ rather than being 
        # initialized in its call to this super class method.
        self.passes=[None,pass1,pass2] # * assembler pass methods

        # These attributes are specific to assembler directives:
        self.spp=spp                   # Special pre-processor in lieu of parser
        self.operand_cls=cls           # List of operand classes for parser.

    def __getitem__(self,item):
        return self.passes[item]

    def __str__(self):
        return "%s(instrution=%s,passes=%s)"\
            % (self.__class__.__name__,self.name,self.passes)

    # Returns the language processor global scope object after parsing the statement
    def do_parse(self,stmt,scope):
        return self.parser.lang.analyze(stmt.rem,scope=scope,\
            recovery=False,lines=False,fail=False)

    def num_oprs(self):
        return self.max_operands

    # Determines if the number of operands provided in the 'number' argument
    # are compatible with the statement for which this AsmPasses instance.
    # Return True if the operands are ok.  Returns False otherwise.
    #
    # The tests are based upon the attributes self.min_operands and self.max_operands
    # Method returns the failing case number or 0 if ok
    def operands_ok(self,number,debug=False):
        minimum=self.min_operands
        maximum=self.max_operands

        # Case 1 - n or more required
        if maximum is None:
            if number<minimum:
                return 1
            else:
                return 0

        # Case 2 - n required
        if minimum==maximum:
            if number!=minimum:
                return 2
            else:
                return 0

        # Case 3 - m-n operands required
        if number<minimum or number>maximum:
            return 3
        return 0  # Operands OK

# This is a subclass of AsmPasses used by the template for instruction processing
# It will clone itself
class AsmInsn(AsmPasses):
    def __init__(self,ins,fmt,template):
        if __debug__:
            #cls_str="assembler.py - %s.__init__() -" % self.__class__.__name__
            cls_str=eloc(self,"__init__")
            assert isinstance(ins,insnbldr.MSLentry),\
                "%s 'insn' argument must be an instance of MSLentry: %s" \
                    % (cls_str, insn)
            assert isinstance(fmt,msldb.Format),\
                "%s 'fmt' argument must be an instance of msldb.Format: %s" \
                % (cls_str, insn)
            assert isinstance(template,AsmPasses),\
                "%s 'template' argument must be an instance of AsmPasses: %s" \
                    % (cls_str,template)

        operands=ins.num_oprs()
        super().__init__(name=ins.mnemonic,parser=template.parser,optional=True,\
            min=operands,max=operands,directive=False)

        # Initialize the machine instruction specific attributes
        self.insn=ins                 # MSLentry cache instance of instruction
        self.format=fmt               # msldb.Format instance of instruction
        self.length=fmt.length        # length of the instruction in bytes

        # Update for pass methods from template
        self.passes=template.passes

# Similar to the AsmPasses object facilitating processing of statements, Passes drives
# overall processing within a pass itself.
#
# Instance arguments:
#
#   pas          The number of the pass, 1-n, to which the object applies.
#   wall         The name of this passes wall clock timer
#   proc         The name of this passes process timer
#   pre          The method to be called before any statements are processed.
#   statements   Indicates whether statements are to be processed within this pass.
#                Defaults to True.
#   post         The method called upon completion of all statement processing within 
#                the pass but before the pass is completed.
#   trace        whether all processing within the pass will be traced.
class Pass(object):
    def __init__(self,pas,wall=None,proc=None,pre=None,statements=True,post=None,\
        trace=False):
        self.pas=pas                 # Pass number of this object
        self.wall=wall               # Wall clock timer name
        self.proc=proc               # Process timer name
        self.pre=pre                 # Pre statement processing method
        self.post=post               # Post statement processing method
        self.stmts=statements        # Statement processing, True or False, this pass
        self.trace=trace             # Whether this pass is traced or no


#
#  +---------------------+
#  |                     |
#  |   Address Objects   |
#  |                     | 
#  +---------------------+
#

# The Address class represents all addresses created during the assembly, both
# relative and absolute.  During the assembly pass 1, Binary content has an address
# assigned to it using an Address object.  If the content has an accompanying label
# in the symbol table, the actual Address object is used to provide the symbol's
# value.  During the address binding process, the address is converted from a
# relative address into an absolute addres.  Because the very same object is used in
# the symbol table, the change in the content address is automatically seen in the 
# symbol table.
# 
# The Address class and its subclasses are designed to pariticipate in Python
# arithmetic operations using overloading methods.  This allow them to paricipate
# directly in expression evaluation as would a standard Python integer.

# This exception is raised when problems arise during address arithemtic.  It
# should be caught and an AssemblerError with relevant context information should 
# then be raised.
class AddrArithError(Exception):
    def __init__(self,msg=None):
        self.msg=msg
        super().__init__(msg)

# This is the base class for all Address Types
class Address(object):
    @staticmethod
    def extract(addr):
        if addr is None:
            return None
        if isinstance(addr,int):
            return addr
        return addr.lval()

    def __init__(self,typ,rel,section,address,length=1):
        if __debug__:
            cls_str=eloc(self,"__init__")
            assert isinstance(typ,int),\
                "%s 'typ' argument must be an integer: %s" % (cls_str,typ)
            assert typ>=1 and typ<=3,\
                "%s 'typ' argument invalid (1-3): %s " % (cls_str,typ)
            assert isinstance(length,int),\
                "%s 'length' argument must be an integer: %s" \
                     % (cls_str,length)

            if typ==1:
                # Dummy section displacement
                assert isinstance(section,Section) and section.isdummy(),\
                    "%s 'section' argument must be DSECT for typ %s: %s" \
                        % (cls_str,typ,section)
                assert address is None,\
                    "%s 'address' argument must be None for typ %s: %s" \
                        % (cls_str,type,address)

            elif typ==2:
                # Section relative address
                assert isinstance(section,Section) and not section.isdummy(),\
                    "%s 'section' argument must be CSECT for typ %s: %s" \
                        % (cls_str,typ,section)  
                assert address is None,\
                    "%s 'address' argument must be None for typ %s: %s" \
                        % (cls_str,typ,address)

            else:
                # Absolute Address
                assert isinstance(address,int), \
                    "%s 'address' argument must be integer for typ %s: %s" \
                        % (cls_str,typ,address)
                assert rel is None, \
                     "%s 'rel' argument must be None for typ %s: %s" \
                         % (cls_str,typ,rel)
                assert section is None, \
                     "%s 'section' argument must be None for typ %s: %s" \
                         % (cls_str,typ,section)

        self.value=rel          # Address relative to the section start
        self.section=section    # Section instance in which this address is located
        self.address=address    # Absolute address of the relative location
        self.typ=typ            # Set my type (1, 2 or 3, relative or absolute)
        self.length=length      # This attibute is used for implied length values

    def __repr__(self):
        string="%s(typ=%s,value=%s,address=%s,length=%s" \
            % (self.__class__.__name__,self.typ,self.value,self.address,self.length)
        string="%s\n    section=%s)" % (string,self.section)
        return string

    def __str__(self):
        if self.isRelative():
            return self._rel_str()
        return self._abs_str()

    def _abs_str(self):
        return "ABS:0x%X" % self.address

    def _ck(self,v,a,op,b,rsup=False):
        if v>=0:
            return v
        if rsup:
            raise AddrArithError(msg="negative address not supported %s %s %s: %s" \
                % (b,op,a,v))
        raise AddrArithError(msg="negative address not supported %s %s %s: %s" \
            % (a,op,b,v))

    def _cmp(self,other,op):
        typo=self._type(other)
        if typo==0 or typo!=self.typ:    # Can only compare same address types
            self._no_sup(op,other)
        if typo==3:       # Both are absolute addresses
            return (self.address,other.address)
        # Both are either DSECT displacements or relative addresses, same rules
        if self.section!=other.section:
            self._no_sup(op,other)
        return (self.value,other.value)

    def _no_sup(self,op,b):
        raise AddrArithError(msg="can't perform: %s %s %s" % (self,op,b))

    def _no_rsup(self,op,b):
        raise AddrArithError(msg="can't perform: %s %s %s" % (b,op,self)) 

    def _rel_str(self):
        return "%s+0x%X" % (self.section.name,self.value)

    # Categorizes Address argument in calculations by type:
    #   0 == integer
    #   1 == dummy section displacement (treat like integer with other addresses)
    #   2 == relative address
    #   3 == absoulute address
    #   4 == anything else
    def _type(self,other):
        if isinstance(other,int):
            return 0
        if isinstance(other,Address):
            return other.typ
        return 4

    def __div__(self,other):
        self._no_sup("/",other)
    def __floordiv__(self,other):
        self._no_sup("/",other)
    def __mul__(self,other):
        self._no_sup("*",other)
    def __radd__(self,other):
        return self.__add__(other,rsup=True)
    def __rdiv__(self,other):
        self._no_rsup("/",other)
    def __rfloordiv__(self,other):
        self._no_rsup("/",other)
    def __rmul__(self,other):
        self._no_rsup("*",other)
    def __rsub__(self,other):
        self._no_rsup("-",other)

    # Comparison overloads for addresses
    def __lt__(self,other): 
        me,other=self._cmp(other,"<")
        return me<other
    def __le__(self,other):
        me,other=self._cmp(other,"<=")
        return me<=other
    def __eq__(self,other):
        me,other=self._cmp(other,"==")
        return me==other
    def __ne__(self,other):
        me,other=self._cmp(other,"!=")
        return me!=other
    def __gt__(self,other):
        me,other=self._cmp(other,">")
        return me>other
    def __ge__(self,other):
        me,other=self._cmp(other,">=")
        return me>=other

    # Returns the intgeger value to be used in Base/Displacement calculation.
    def base(self):
        raise NotImplementedError("%s subclass must implement base() method" \
            % eloc(self,"base"))

    def clone(self):
        raise NotImplementedError("%s subclass must implement clone() method" \
            % eloc(self,"clone"))

    def description(self):
        raise NotImplementedError("%s subclass must implement description() method" \
            % eloc(self,"description"))

    def isAbsolute(self):
        raise NotImplementedError("%s subclass must implement isAbsolute() method" \
            % eloc(self,"isAbsolute"))

    def isDummy(self):
        raise NotImplementedError("%s subclass must implement isDummy() method" \
            % eloc(self,"isAbsolute"))

    def isRelative(self):
        raise NotImplementedError("%s subclass must implement isRelative() method" \
            % eloc(self,"isRelative"))

    def lval(self):
        raise NotImplementedError("%s subclass must implement lval() method" \
            % eloc(self,"lval"))


class DDisp(Address):
    def __init__(self,rel,section,length=1):
        super().__init__(1,rel,section,None,length=length)

    def __add__(self,other,rsup=False):
        typo=self._type(other)    # The other objects type number
                       # I'm a Dummy displacement
        if typo==0:    #    Other is an integer
            new_rel=self._ck(\
               self.value+other,other,"+",self,rsup=rsup)
            return DDisp(new_rel,self.section,length=self.length)
        elif typo==2:  #    Other is a relative address (treat me like int)
            new_rel=self._ck(\
                self.value+other.value,self,"+",other,rsup=rsup)
            return SectAddr(new_rel,other.section,other.length)
        elif typo==3:  #    Other is an absolute address (treat me like int)
            new_addr=self._ck(\
                self.value+other.address,self,"+",other,rsup=rsup)
            return AbsAddr(address=new_addr,length=other.length)
        if rsup:
            self._no_rsup("+",other)
        self._no_sup("+",other)  

    def __sub__(self,other):
        typo=self._type(other)    # The other objects type number
                       # I'm a Dummy displacement
        if typo==0:    #    Other is an integer
            new_rel=self._ck(self.value-other,self,"-",other)
            return DDisp(new_rel,self.section)
        elif typo==1:  #    Other is a DSECT displacement
            if self.section!=other.section:
                self._no_sup("-",other)
            return self.value-other.value
        self._no_sup("-",other)

    def __str__(self):
        return self._rel_str()

    def base(self):
        return self.value

    def clone(self):
        return DDisp(self.value,self.section)

    def description(self):
        return "DSECT-relative address"

    def isAbsolute(self):
        return False

    def isDummy(self):
        return True

    def isRelative(self):
        return True

    def lval(self):
        return self.value

class AbsAddr(Address):
    def __init__(self,address=None,rel=None,section=None,typ=3,length=1):
        super().__init__(typ,rel,section,address,length=length)

    def __add__(self,other,rsup=False):
        typo=self._type(other)    # The other objects type number
                       # I'm an absolute address
        if typo==0:    #    other is an integer
            new_addr=self._ck(\
                self.address+other,self,"+",other,rsup=rsup)
            return AbsAddr(new_addr,length=self.length)
        elif typo==1:  #    other is a DSECT displacement
               return AbsAddr(self.address+other.value,length=self.length)
        if rsup:
            self.__no_rsup("+",other)
        self.__no_sup("+",other)  

    def __sub__(self,other):
        typo=self._type(other)    # The other objects type number
                       # I'm an absolute address
        if typo==0:    #    Other is an integer
            new_addr=self._ck(self.address-other,self,"-",other)
            return AbsAddr(new_addr)
        elif typo==1:  #    Other is a DSECT displacement
            new_addr=self._ok(self.address-other.value,self,"-",other)
            return AbsAddr(new_addr)
        elif typo==3:  #    Other is an absolute address
            return self.address-other.address
        self.__no_sup("-",other)

    def base(self):
        return self.address

    def clone(self):
        return AbsAddr(self.address)

    def description(self):
        return "absolute address"

    def isAbsolute(self):
        return True

    def isDummy(self):
        return False

    def isRelative(self):
        return False

    def isAbsolute(self):
        return True

    def lval(self):
        return self.address

class SectAddr(AbsAddr):
    def __init__(self,rel,section,length=1):
        super().__init__(rel=rel,section=section,typ=2,length=length)

    def __add__(self,other,rsup=False):
        if self.typ==3:  # Use super class if I am an absolute address now
            return super().__add__(other)

        typo=self._type(other)    # The other objects type number
                       # I'm a CSECT Relative address
        if typo==0:    #   other is an integer
           new_rel=self._ck(\
               self.value+other,self,"+",other,rsup=rsup)
           return SectAddr(new_rel,self.section)
        if typo==1:     #   other is a DSECT displacement
           return SectAddr(self.value+other.value,self.section)

        if rsup:
            self._no_rsup("+",other)
        self._no_sup("+",other) 

    def __sub__(self,other,rsup=False):
        if self.typ==3:  # Use super class if I am an absolute address now
            return super().__sub__(other)

        typo=self._type(other)    # The other objects type number
                       # I'm a CSECT Relative address
        if typo==0:    #    Other is integer
            new_rel=self._ck(self.value-other,self,"-",other)
            return SectAddr(new_rel,self.section)
        elif typo==2 or typo==1:   #    Other is a relative address (CSECT or DSECT)
            if self.section!=other.section:
                self._no_sup("-",other)
            return self.value-other.value
        self._no_sup("-",other) 

    def base(self):
        if self.isRelative():
            return self.value
        return self.address

    def clone(self):
        if self.isRelative():
            return SectAddr(self.value,self.section)
        return super().clone()

    def makeAbs(self):
        if self.typ!=2:
            raise ValueError("%s relative (%s) already absolute: %s" \
                % (eloc(self,"makeAbs"),self._rel_str(),self._abs_str()))

        section=self.section
        if section.isdummy():
            sec_addr=self.section.value()
            self.address=sec_addr+self.value
        else:
            sec_addr=self.section.value()
            if not sec_addr.isAbsolute():
                raise ValueError("%s section address is not absolute: %s" \
                    % (eloc(self,"makeAbs"),repr(sec_addr)))
            self.address=sec_addr.address+self.value
            self.typ=3

    def description(self):
        if self.typ==2:
            return "CSECT-relative address"
        return "absolute address"

    def isDummy(self):
        return False

    def isRelative(self):
        return self.typ==2

    def isAbsolute(self):
        return self.typ==3

    def lval(self):
        if self.isRelative():
            return self.value
        return self.address

#
#  +------------------------------+
#  |                              |
#  |   Base Register Management   |
#  |                              | 
#  +------------------------------+
#

# This object encapsulates the information provided by USING statements within the
# BaseMgr class.  It is designed to facilitate resolution of base/displacement
# addressing for addresses, relative or absolute, performed in the BaseMgr.find()
# BaseMgr.__select() methods.
class Base(object):
    # This method is used by the functools for sorting of Base objects
    @staticmethod
    def compare(a,b):
        return a.__cmp__(b)

    def __init__(self,reg,addr,direct=None):
        assert isinstance(reg,int),\
            "%s 'reg' argument must be an integer: %s" % (eloc(self,"__init__"),reg)
        assert isinstance(addr,Address),\
            "%s 'addr' argument must be an instance of Address: %s" \
                % (eloc(self,"__init__"),addr)
        assert (direct is None) or isinstance(direct,AbsAddr),\
            "%s 'direct' argument must be None or an instance of AbsAddr: %s" \
                % (eloc(self,"__init__"),direct)

        # The absolute address associated with this register when used for
        # direct addressing.  This applies to register 0 only for all but one
        # mainframe system.  The 360-20 utilizes eight registers (0-7) for direct
        # mode addressing.  This asembler supports both situations.
        #
        # Regardless of the registered address, direct allways defaults to its
        # absolute address.  This works for register 0 getting assigned a DSECT
        # as its base.  Pretty unpredictable results are likely for other direct
        # registers.  Assigning a DSECT to register 1, when 1 is a direct mode
        # register, will really assign it to address DSECT start plus 4096.
        self.direct=direct

        # The register with which this Base instance represents its most recent
        # USING assigment
        self.reg=reg

        # The address assigned by the USING directive.  The address may be
        # relative or absolute.  At the stage of the assingment within the
        # assembler, a CSECT will be utilizing absolute addresses and only a DSECT
        # symbol provide a relative address.  Because many of the addresses will be 
        # relative addresses converted to absolute, the test for absolute or relative
        # MUST use the isAbsolute() or isRelative() method tests, NOT a class 
        # isinstance test.
        self.loc=addr 

        # The purpose of this class is to convert an address into a base/displacement
        # pair.  In terms of the Python implementation, the class converts an Address 
        # instance into a tuple of integers representing the base register and 
        # displacement.  The calculation is always performed on the Address.address
        # attribute regardless of whether it is a relative address or not being
        # assigned by the USING directive.
        if direct is not None:
            self.address=direct.address
        else:
            self.address=addr.base()       # Absolute address or relative displacement

        # A register assigned a relative address can ONLY be used as a base register
        # of another relative address within the same CSECT or DSECT.  Per above
        # the only case that should occur is relative addresses related to DSECT's.
        # This saves the Section instance related to the assigned relative address.
        # It is used by the BaseMgr.find() method to ensure this base register
        # assignment is only considered for a relative address in the same section.
        if addr.isRelative():
            self.section=addr.section  # CSECT/DSECT for relative address only
        else:
            self.section=None          # absolute addresses only

        # Set to allow comparison of base register options on displacement
        self.disp=None
        
        if self.address is None:
            raise ValueError("%s Base address is None: %s" \
                % (eloc(self,"__init__"),repr(addr)))


    # This method is used to comapre two Base instances for sorting purposes.  The
    # staticmethod BaseMgr.compare() is just a wrapper for this method.  The
    # staticmethod is required because functools requires an unbound method or
    # function.
    #
    # The rules for selection are as follows:
    #
    # 1. Select the base register with the smallest displacement.
    # 2. If the displacement's are equal select the highest numbered register unless
    #    direct mode base register, in which case select the lowest numbered
    #    register.
    #
    # Because the actual displacement has not been calculated the highest address
    # results in the smallest displacement.  (We know that a base location is eligible
    # or it would not be in the list being sorted.  Eligible means the base address
    # or displacement is less than or equal to the address for which a base is 
    # sought.)
    def __cmp__(self,other):
        assert self.disp is not None,\
            "%s displacement not set, can not sort Base instance: reg=%s,address=%s"\
                % (eloc(self,"__cmp__"),self.reg,self.loc)

        if self.disp<other.disp:
            return -1 
        if self.disp>other.disp:
            return 1

        # displacements are equal so select on register, highest register is chosen.
        # For direct registers always pick the lowest.
        if self.direct is not None:
            # pick the lowest direct register candidate
            if self.reg<other.reg:
                return -1
            if self.reg>other.reg:
                return 1
        else:
            # pick the higest base/displacement register candidate
            if self.reg<other.reg:
                return 1
            if self.reg>other.reg:
                return -1
        raise ValueError("%s two base register candidates with the same register "
            "and displacement detected: %s:%s" % (eloc(self,"__cmp__"),self,other))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        cls=self.__class__.__name__
        if self.disp is None:
            disp="None"
        else:
            disp=hex(self.disp)
        if self.direct:
            return "%s(reg=%s,addr=%s,disp=%s,direct=True)" \
                % (cls,self.reg,self.address,disp)
        return "%s(reg=%s,addr=%s,disp=%s)" % (cls,self.reg,self.loc,disp)

    # Return the displacement for the supplied address.
    def getDisp(self,addr):
        assert isinstance(addr,Address),\
            "%s 'addr' argument must be an instance of Address: %s" \
                % (eloc(self,"getDisp"),addr)

        return addr.base()-self.address
        # Note: no checks are performed on the actual displacement.  Different
        # values are allowed for different instruction formats.  Whether the
        # displacement is appropriate for the instruction must be tested elsewhere.


# This class manages base registers, USING, DROP and base/disp resolution
class BaseMgr(object):

    # These class attributes manage direct mode addressing
    # One direct mode register in use
    direct1={0:AbsAddr(0x0000)}       # 4K        0x0000 ->       0
    # Eight direct mode registers in use
    direct8=\
        {0:Base(0,AbsAddr(0x0000)),   # 4K        0x0000 ->       0
         1:Base(1,AbsAddr(0x1000)),   # 8K        0x1000 ->   4,096
         2:Base(2,AbsAddr(0x2000)),   # 12K       0x2000 ->   8,192
         3:Base(3,AbsAddr(0x3000)),   # 16K       0x3000 ->  12,288
         4:Base(4,AbsAddr(0x0000)),   # 4K        0x4000 ->  16,384
         5:Base(5,AbsAddr(0x1000)),   # 8K        0x5000 ->  20,480
         6:Base(6,AbsAddr(0x2000)),   # 12K       0x6000 ->  24,576
         7:Base(7,AbsAddr(0x3000))}   # 16K       0x7000 ->  28,672

    # This is established when BaseMgr in instantiated  
    direct=None

    def __init__(self,extended=False):
        # This dicitionary maps a register to one of the other dictionaries when it
        # is actively engaged.  It is used by DROP to find the actual using to be
        # removed.  Direct registers are here but never change.
        self.bases={}     # Active USING assignments. reg number points to the other

        # This dictionary contains the active "base" for all absolute addresses
        # including direct registers.
        self.abases={}    # Active USING assignments to absolute bases

        # This dictionary contains the active base for relative addresses (for
        # example DSECT symbols).
        self.rbases={}    # Active USING assignments to relative bases

        if extended:  # Extended direct mode is supported only on the 360-20
            BaseMgr.direct=BaseMgr.direct8
        else:         # All other systems only support direct mode with register 0
            BaseMgr.direct=BaseMgr.direct1

    # This method selects a base register from a list of possible candidates.
    # All of the bases supplied to this method ARE eligible for use in resolving
    # a symbol to a base/displacement combination.

    def __select(self,addr,possible,trace=False):
        if len(possible)==0:
            raise KeyError           # No possibilies exist, quit now.
        elif len(possible)==1:
            select_list=possible     # Only one possible, no need to sort the list
        else:
            select_list=sorted(possible,key=functools.cmp_to_key(Base.compare))
        if trace:
            print(select_list)
        selected=select_list[0]      # The first one is the chosen one
        disp=selected.getDisp(addr)  # Calculate the displacement from the chosen base
        reg=selected.reg
        return (reg,disp)            # Return the base/displacement tuple

    # This method removes a previously registered base.  If it was not previously
    # registered it is silenty ignored.  The effect of the DROP statement is to 
    # make a register unavailable for use as a base.  It does not matter whether
    # it wss previously available or not.
    def drop(self,reg,trace=False):
         assert isinstance(reg,int),\
            "%s 'reg' argument must be an integer: %s" % (eloc(self,"drop"),reg)

         based=self.bases[reg]
         try:
             del based[reg]
         except KeyError:
             pass
         try:
             self.bases[reg]=None
         except KeyError:
             pass

    # Resolve an address into a tuple of two integers (basereg,displacement)
    # If no base is found, a KeyError is raised to alert the caller to the 
    # failure.  It is the responsibility of the caller to provide any user
    # reporting.
    # Method Arguments:
    #   addr    The Address object being resolved into a base/displacment pair
    #   size    Size of the displacement field in bits
    #   asm     The Assembler object providing assistance
    #   trace   Enable trace messages if True
    # Note: A KeyError actually originates in the __select() method, but to the
    # caller it appears to be raised here because it is not caught.
    def find(self,addr,size,asm,trace=False):
        assert isinstance(addr,Address),\
            "%s 'addr' argument must be an instance of Address: %s" \
                % (eloc(self,"find"),addr)

        possible=[]
        if addr.isAbsolute():
            for base in self.abases.values():
                if base.address <= addr.address:
                    disp=base.getDisp(addr)
                    try:
                        asm.builder.range_check(size,disp)
                    except insnbldr.RangeCheckError:
                        # will not fit, not a candidate
                        continue
                    base.disp=disp
                    possible.append(base)
            # This can raise and uncaught KeyError when resolution is not possible
            return self.__select(addr,possible,trace=trace)

        for base in self.rbases.values():
            #if base.section == addr.section and base.address <= addr.address:
            base_addr=addr.base()
            assert base_addr is not None,\
                "%s Base address is None: %s" % (eloc(self,"find"),repr(addr))

            if base.section == addr.section and base.address <= addr.base():
                disp=base.getDisp(addr)
                try:
                    asm.builder.range_check(size,disp)
                except insnbldr.RangeCheckError:
                    # will not fit, not a candidate
                    continue
                base.disp=disp
                possible.append(base)
        # This can raise an uncaught KeyError when resolution is not possible
        return self.__select(addr,possible,trace=trace)

    def print(self,indent="",string=False):
        string="%sBase Manager:\n" % indent
        lcl="%s    " % indent
        for r in range(16):
            try:
                bdict=self.bases[r]
                if bdict is None:
                    continue
            except KeyError:
                continue
            assigned=bdict[r]
            rstr="R%s" % r
            rstr=rstr.ljust(3)
            string="%s%s%s  %s\n" % (string,lcl,rstr,assigned)
        if string:
            return string
        print(string)

    # This method registers a specific register and its associated base address.
    # Per the semantics of the USING directive, a new registration supercedes
    # a previous one.
    def using(self,reg,addr,trace=False):
        cls_str="assembler.py %s.using() -" % self.__class__.__name__
        # In theory these sanity checks should not be needed.  The USING directive's
        # pass 2 method should only use correct values.  Experience has shown that
        # there is value in quickly finding operands that are incorrect.  This is
        # particularly valuable during initial development and later when changes
        # occur.
        if __debug__:
            cls_str=eloc(self,"using")
            if trace:
                print("%s defining base for register %s: %s" % (cls_str,reg,addr))
        assert isinstance(reg,int),\
            "%s 'reg' argument must be an integer: %s" % (cls_str,reg)
        assert isinstance(addr,Address),\
            "%s 'addr' argument must be an instance of Address: %s" % (cls_str,addr)
        assert addr.isAbsolute() or addr.isDummy(),\
            "%s only absolute or DSECT relative should occur: %s" % (cls_str,addr)

        # Determine if direct mode addressing applies to the register being assigned
        # a base value.  When a register participates in direct mode addressing
        # it does not matter what address is assigned, the base for the address
        # will always be the direct mode address for absolute addresses or
        # the section start plus the direct mode address.
        try:
            dbase=BaseMgr.direct[reg]
        except KeyError:
            dbase=None

        if addr.isAbsolute():
            self.abases[reg]=Base(reg,addr,direct=dbase)
            self.bases[reg]=self.abases
        else:
            self.rbases[reg]=Base(reg,addr,direct=dbase)
            self.bases[reg]=self.rbases
        return

#
#  +---------------------+
#  |                     |
#  |   Location Object   |
#  |                     | 
#  +---------------------+
#

# This object represents a location within an object module.  Location objects
# participate in relocation.  They consist of an anchor address and a positive or
# negative adjustment.  The anchor address may be a section relative address or an
# absolute address.  When a section relative address, the section will dictate the
# ESDID used for the location.  The adjustment is always an integer.
class Location(object):
    def __init__(self,anchor,adjustment=0):
        self.anchor=anchor          # Location's anchor address
        self.adjust=adjustment      # Location's adjustment


#
#  +-----------------------------+
#  |                             |
#  |   Global Location Counter   |
#  |                             | 
#  +-----------------------------+
#

# The location counter is used during pass 1 to define statement locations.
# In pass 2 the location of the binary content of the statement defines the location.
# This object is used to globally track the addresses assigned to Binary objects.
class LocationCounter(object):
    def __init__(self):
        self.location=None

    # Sets the current location counter to the starting address of the supplied
    # Binary object.  During Pass 1 this is a section relative address (SectAddr
    # object).  During Pass 2 this is an absolute address (AbsAddr object)
    def assign(self,bin,debug=False):
        assert isinstance(bin,Binary),\
            "%s 'bin' argument must be a Binary object: %s" \
                % (eloc(self,"assign"),bin)
                
        # Binary object's location has not been set, so simply return
        if bin.loc is None:
            return

        if __debug__:
           new_loc=bin.loc
           assert isinstance(new_loc,Address) and \
               (new_loc.isRelative() or new_loc.isAbsolute()),\
               "%s Binary object loc attribute is neither relative nor absolute: %s"\
                   % (eloc(self,"assign"),bin.loc)

        self.location=bin.loc

        if __debug__:
            if debug:
                print("%s location: %s" % (eloc(self,"assign"),self.location))

    # This happens whenever a section changes or the statements ending location
    # is being set.
    def establish(self,loc,debug=False):
        # If no location is provided, simply leave the location as is.
        if loc is None:
            return
        assert isinstance(loc,Address),\
            "%s 'loc' argument must be a Address object: %s" \
                % (eloc(self,"establish"),loc)
        assert loc.isRelative() or loc.isAbsolute(),\
            "%s 'loc' argument must be a relative or absolute address object: %s" \
                % (eloc(self,"establish"),loc)

        self.location=loc.clone()

        if __debug__:
            if debug:
                print("%s location: %s" % (eloc(self,"establish"),self.location)) 

    def increment(self,bin,debug=False):
        if __debug__:
            if debug:
                print("%s bin: %s" % eloc(self,"increment"),bin)
        if bin:
            self.establish(bin.loc+len(bin),debug=debug)

    def retrieve(self):
        return self.location.clone()

    # Based upon the content of the statement the location counter will be upated
    # for next statement.
    def update(self,bin,debug=False):
        if __debug__:
            if debug:
                print("%s bin: %s" % (eloc(self,"update"),bin))

        if bin:
            self.assign(bin,debug=debug)


#
#  +-------------------------------------+
#  |                                     |
#  |   Binary Structure Template Class   |
#  |                                     | 
#  +-------------------------------------+
#

# The Structure class creates a template for the generation of any binary structure.
# For assembler directives, it is analogous to the insnbldr.Instruction class used
# for generating an instruction.  The template is instantiated once and then reused
# each time the corresponding structure is generated by a directive.
#
# Templage Field objects supplied with a value will override a value supplied to the 
# build() method when being built.  Note that a value must be supplied for the field
# when the build() method is called.  The value is simply ignored.  It is recommended
# that None be used for such fields when the build() method is called.
#
# Instance arguments:
#    fields    A list of insnbldr.Field objects defining the structure's template
class Structure(object):
    def __init__(self,name,builder,fields=[]):
        self.name=name                  # Template name
        self.builder=builder            # The single insnbldr.Builder object. 
        self.fields=fields              # List of insnbldr.Field objects
        self.num_flds=len(self.fields)  # Number of Field objects in list

    # Generate the structure as a bytes sequence.
    # Method arguments:
    #    stmt      The Stmt object of the statement associated with the directive
    #    values    A list of integers (may include None) to be placed in each field
    #              of the template.
    def build(self,stmt,values=[],trace=False):
        num_flds=self.num_flds
        assert len(values)==num_flds,\
            "%s number of supplied values does not match the number of fields "\
                "(%s): %s" % (eloc(self,"build"),num_flds,len(values))

        fields=self.fields
        builder=self.builder
        binlen=len(stmt.content)
        lineno=stmt.lineno

        # This is the structure being built.  Python integers may be of any size.
        # The algorithm used below uses this fact letting a Python integer be the
        # structure while under construction.  The Python 3.3 enhancements allow
        # this integer to be turned in a bytes sequence, subsequently used as the
        # binary content of the structure.
        bin=0      # This is the structure being built
        for ndx in range(num_flds):
            fld=fields[ndx]
            was_none=False
            if fld.value is None:
                was_none=True         # This ensures values don't get reused 
                fld.value=values[ndx]

            if __debug__:
                if trace:
                    print("%s field %s: %s" % (eloc(self,"build"),ndx,fld))

            # Insert each field individually into the structure
            bin=fld.insert(binlen,bin,builder,lineno,signed=fld.signed)
            # This ensures values don't get reused on the next use of the template
            if was_none:
                fld.value=None

        # Return the structure as bytes list.
        return bin.to_bytes(binlen,byteorder="big",signed=False)


#
#  +---------------------------+
#  |                           |
#  |   Image Content Classes   |
#  |                           | 
#  +---------------------------+
#

# The image content classes form a hierarchy of embedded containers.  This describes
# the logical relationship of the containers.
#     Region contains
#        Section contains
#            Binary
#
# From a class perspective, Binary is the base class.  Its content is raw binary data.
# The other two containers in the hierarchy contain, the others.  The Content class
# is the foundation for each of the container classes, providing common functionality
# to both Region and Section.  Content is the super class of both the Region and 
# Section classes, and is a subclass of Binary.  The Content class is never itself
# instantiated directly.

# This is the base class for all image content.
class Binary(object):
    def __init__(self,alignment,length):
        super().__init__()
        self._align=alignment      # Alignment within parent container
        self._length=length        # Length of binary content whether present or not
        self.barray=None           # Binary content as a byte array or bytes list

        # These attributes are established during pass 1 processing
        #
        # Location relative or absolute address, an instance of Address
        self.loc=None
        # Initial relative location
        self.rloc=None
        # Set when object is added to a container by the container's append() method
        self.container=None    # Container in which this object resides.

    # Return the length of the content    
    def __len__(self):
        return self._length

    def __str__(self):
        if self.barray is None:
            barray="None"
        else:
            barray=len(self.barray)
        return "%s(alignment=%s,length=%s,barray=%s)" \
            % (self.__class__.__name__,self._align,self._length,barray)

    def assigned(self,loc):
        self.loc=loc
        if isinstance(loc,SectAddr):
            self.rloc=loc.clone()

    # Returns as a string the hex representation of the barray upto the number
    # of bytes specified.  Default max bytes is 16
    def bhex(self,max_bytes=16):
        string=""
        for n in range(min(max_bytes,len(self.barray))):
            byte=self.barray[n]
            string="%s%02X " % (string,byte)
        return string[:-1]

    # Make the byte array immutable by converting it into a bytes list of integers
    def fini(self,trace=False):
        self.barray=bytes(self.barray)

        if __debug__:
            if trace:
                cls_str=eloc(self,"fini")
                cls=self.__class__.__name__
                beg_addr=self.loc
                blen=len(self.barray)
                end_addr=beg_addr+blen-1
                hexdata=self.bhex()
                if blen==1:
                    print("%s %s finalized %s byte: %s: %s" \
                        % (cls_str,cls,blen,beg_addr,hexdata))
                else:
                    print("%s %s finalized %s bytes: %s - %s: %s" \
                        % (cls_str,cls,blen,beg_addr,end_addr,hexdata))

    def make_absolute(self,debug=False):
        if debug:
            prev=self.loc.clone()
        self.loc.makeAbs()

        if __debug__:
            if debug:
                print("%s converted %s to absolute %s" \
                    % (eloc(self,"make_absolute"),prev,self.loc))

    def make_barray(self,trace=False):
        length=len(self)    # Use this or subclasses way to determine its length
        self.barray=bytearray(length)
        # we now have zero filled image content for this Binnary or its subclass
        if __debug__:
            if trace:
                cls_str=eloc(self,"make_barray")
                if isinstance(self,Content):
                    desc="%s '%s'" % (cls,self.name)
                else:
                    desc="Binary @ %s barray" % (self.loc)
                print("%s %s barray length: %s" 
                    % (cls_str,desc,len(self.barray)))

    def str2bytes(self,string):
        b=bytearray(0)
        for x in string:
            b.append(ord(x))
        return bytes(b)

    # Update the binary imaage content in self.barray.  The data argument must be
    # slicable into the bytearray.
    #
    # Method arguments:
    #   data     This must be an immutable bytes list
    #   at       The position relative to the start of the bytearray object at 
    #            which the bytes list will be placed.  It is the first argument
    #            of a slice.  The second argument will be the sum of the at position
    #            and the length of the supplied bytes list in the data argument.
    #   full     If specified true the bytes list in the data argunent must be 
    #            exactly match the length of the image content bytearray in length.
    #            When full=True is used, the at argument must be 0.
    def update(self,data,at=0,full=False,finalize=False,trace=False):
        if isinstance(data,str):
            d=self.str2bytes(data)
        elif isinstance(data,bytes):
            d=data
        else:
            raise ValueError("%s 'data' argument must be an instance of "
                "bytes or string: %s" % (eloc(self,"update"),data))

        dlen=len(d)
        if __debug__:
            if full:
                blen=len(self.barray)
                assert at==0,\
                    "%s 'at' argument must be 0 when full=True is specified: %s" \
                        % (eloc(self,"update"),at)
                assert dlen==blen,\
                    "%s - 'data' argument length must match bytearray length of %s: %s"\
                        % (eloc(self,"update"),blen,dlen)

        end=at+dlen

        if __debug__:
            if trace:
                print("%s %s %s bytearray[%s:%s] updated with bytes of length %s" \
                    % (eloc(self,"update"),self.__class__.__name__,\
                        self.loc,at,end,dlen))

        # Upate the binary image content
        self.barray[at:end]=d

        if finalize:
            self.fini(trace=trace)

    # This method returns the value referenced by this binary or container's symbol
    # ALL SUBCLASSES USE THIS METHOD
    def value(self):
        return self.loc

# This class is used to hold storage content from DC/DS statements
# The container holds one or more Binary objects.  It takes the alignement
# of the first Binary and location of the first Binary opject in the area.
# The Area derives its length of all of the combined Binary objects, similar to 
# a Section, but embedded within a section.  This is a pseudo-container.  It is
# only used in a Stmt instance to establish the size of a symbol associated with
# a DC statement.  Such symbols have the length attribute of the operands.
#
# This class is also the foundation for PRINT DATA to display the entire set of
# DC/DS constants in the listing.
class Area(Binary):
    def __init__(self):
        super().__init__(0,0)
        self.elements=[]     # List of accumulated Binary objects in the area

    def append(self,bin):
        assert isinstance(bin,Binary),\
            "%s 'bin' argument must be an instance of Binary: %s" \
                % (eloc(self,"append"),bin)

        self.elements.append(bin)

    # This method adjusts the area's Binary instance attributes to conform to the
    # effects of all of the operands in the DS statement.  This will cause a
    # statement symbol to reflect the alignment of the first operand and the length
    # of the sum of all of the arguments taking duplication, alignment and length
    # into effect.  This method must only be called after all elements of the area
    # have been appended.
    def fini(self,trace=False):
        assert len(self.elements)>0,\
            "%s area contains zero Binary elements" % eloc(self,"fini")

        bin_1st=self.elements[0]
        self._align=bin_1st._align
        self.loc=bin_1st.loc
        if len(self.elements)>1:
            bin_last=self.elements[-1]
            self._length=(bin_last.loc - bin_1st.loc) + bin_last._length
        else:
            self._length=bin_1st._length
        self.make_barray(trace=trace)

    def insert(self,trace=False):
        my_loc=self.loc
        for bin in self.elements:
            bin_loc=bin.loc
            #assert bin_loc.isAbsolute(),\
            #    "%s enrountered non absolute address: %s" \
            #        % (eloc(self,"insert"),bin)

            # Calculate where the data is supposed to go
            barray=bin.barray
            length=len(barray)
            # Note this may result in an AddrArithError, if so, it is a bug
            start=bin_loc-my_loc
            end=start+length
            if length==0:
                # ORG statements create Binary objects which have 0 bytes of data.
                # Ignore them
                if __debug__:
                    if trace:
                        print("%s @ %s inserted [0x%X:0x%X] bytes: %s IGNORED" \
                            % (eloc(self,"insert"),bin_loc,start,end,length))
                continue

            if __debug__:
                if trace:
                    print("%s @ %s inserted [0x%X:0x%X] bytes: %s " \
                        % (eloc(self,"insert"),bin_loc,start,end,length))

            self.barray[start:end]=barray

        # Make me immutable
        self.barray=bytes(self.barray)

        if __debug__:
            if trace:
                dumpdata=hexdump.dump(self.barray,start=my_loc.address,indent="    ")
                print("\nArea Image Content:\n\n%s\n" % dumpdata)


# This is the base class for all image container classes, built on Binary.
class Content(Binary):
    # Methods inherited from Binary: __str__(), value()
    def __init__(self,alignment,cls):
        # Attributes inherited from Binary: 
        #   self._align, self._length, self.barray, self.container, self.loc,
        #   self.address
        super().__init__(alignment,0)
        self.elements=[]      # List of Binary instances of this container's content
        self._alloc=0         # max allocated size
        self.cls=cls          # Only instances of this class may be appended
        self.frozen=False     # No more additions may be made
        #
        # Provide by Img.locate_all() method
        self.img_cur=None
        self.img_loc=None           # This is the displacement from image start

        # These must be initialized by the subclass AFTER calling my __init__
        self._current=None    # Current target initialized by subclass
        self._base=None

    # Return the current lengh
    def __len__(self):
        return self._alloc

    # Align the current location to the content's requirement
    def align(self,content):
        assert isinstance(content,Binary),\
            "%s 'content' argument must be an instance of Binary: %s" \
                % (eloc(self,"align"),content)

        align=content._align
        if align<2:
            return
        cur=self._current
        units=(cur+(align-1))//align
        aligned=units*align
        needed=aligned-cur
        if needed>0:
            self.alloc(needed)

    # Allocate a number of bytes from the current location within the content
    def alloc(self,size):
        if isinstance(size,Binary):
            siz=size._length
        else:
            siz=size
        self._current+=siz
        self._alloc=max(self._alloc,self._current-self._base)

    # Add an element to this content container.  Elements are unallocated and unbound
    def append(self,content):
        assert isinstance(content,self.cls),\
            "%s 'bin' argument must be an instance of %s: %s" \
                % (eloc(self,"append"),content)

        self.elements.append(content)
        content.container=self

    # Align the container and assign a location to the supplied content and 
    # allocate space in this container for the added content
    def assign(self,content,append=True):
        assert isinstance(content,Binary),\
            "%s 'content' argument must be an instance of Binary: %s" \
                % (eloc(self,"assign"),content)

        self.align(content)
        content.assigned(self.current())
        self.alloc(len(content))
        if append:
            self.append(content)

    # Assign all elements their locations after aligning them
    def assign_all(self,debug=False):
        for c in self.elements:
            self.assign(c,append=False)

            if __debug__:
                if debug:
                    print("%s %s" % (eloc(self,"assign_all"),c.info()))

    # Bind an address to the start of this content
    def bind(self,bindto):
        assert isinstance(bindto,Address),\
            "%s 'bindto' argument must be an instancce of Address: %s" \
                % (eloc(self,"bind"),bindto)
        assert bindto.isAbsolute(),\
            "%s 'bindto' argument must be an instancce of Address: %s" \
                % (eloc(self,"bind"),bindto)

        loc=self.loc
        if loc.isAbsolute():
            raise ValueError("%s address already bound: %s" % (cls_str,loc))
        bindaddr=bindto.address
        loc.address=loc.value+bindaddr
        loc.typ=3
        # By setting the Address.address value, the location becomes absolute

    # Bind all elements to their address
    def bind_all(self):
        bindto=self.loc
        assert not bindto.isRelative(),\
            "%s container %s can not bind using a relative address: %s" \
                % (eloc(self,"bind_all"),bindto)
        for c in self.elements:
            c.bind(bindto)

    def current(self):
        raise NotImplementedError("%s subclass %s must implement current() method" \
            % (eloc(self,"current"),self.__class__.__name__))

    def freeze(self):
        self._length=self._alloc
        self.frozen=True

    # Insert all of my elements' barray lists into mine.  This bubbles up the
    # hierarchy tree
    def insert(self):
        raise NotImplementedError("%s subclass %s must implement insert() method" \
            % (eloc(self,"insert"),self.__class__.__name__))

    # Return the current length of the allocated content
    def length(self):
        return len(self)

    def locate_all(self,base):
        raise NotImplementedError("%s subclass %s must implement locate_all() method" \
            % (eloc(self,"locate_all"),self.__class__.__name__))

    def make_barray_all(self,trace=False):
        raise NotImplementedError("%s subclass %s must implement make_barray_all() "
            "method" % (eloc(self,"make_barray_all"),self.__class__.__name__))

    def updtAttr(self,asm,trace=False):
        if self.name=="":
            # Unnamed region or control section not in symbol table,
            # Nothing to update
            return
        try:
            ste=asm._getSTE(self.name)
        except KeyError:
            raise ValueError("%s element not in symbol table: %s" \
                % (eloc(self,"updtAttr"),self))

        ste.attrSet("L",len(self))
        ste.attrSet("I",self.img_loc)

    def updtAttr_all(self,asm,trace=False):
        for ele in self.elements:
            ele.updtAttr(asm)
            if issubclass(ele.__class__,Region):
                ele.updtAttr_all(asm)


# This class represents.  It is create when either CSECT and DSECT creates a new
# section.  It is contained within a Region container and is made part of the 
# active REGION when created during processing of a CSECT statement.  DSECT's are
# not associated with any Region, but stand alone.
class Section(Content):
    # methods inherited from Binary: value().
    def __init__(self,name,dummy=False):
        super().__init__(8,Binary)
        self._current=0           # I start from 0
        self._base=0              # My base is also zero
        self.name=name
        self._dummy=dummy         # From DSECT
        if dummy:
            self.loc=DDisp(0,self)
        else:
            self.loc=SectAddr(0,self)

    def __str__(self):
        if self.isdummy():
            dum=",dummy=True"
        else:
            dum=""
        string="%s('%s'%s)" % (self.__class__.__name__,self.name,dum)
        if self.container is None:
            return string
        return "%s in '%s' @ %s" % (string,self.container.name,self.loc)

    def current(self):
        if self.isdummy():
            return DDisp(self._current,self)
        return SectAddr(self._current,self)

    def dump(self,indent="",string=False):
        lcl="%s    " % indent
        dumpdata=hexdump.dump(self.barray,start=self.loc.address,indent=lcl)
        dumpdata="\n%sCSECT %s Image Content:\n\n%s\n" % (indent,self.name,dumpdata)
        if string:
            return dumpdata
        print(dumpdata)

    def info(self):
        if self.isdummy():
            typ="DSECT"
        else:
            typ="CSECT"
        container=self.container
        if container is None:
            reg="Unassigned"
        else:
            reg="REGION %s" % container.name
        return "%s %s in %s address: %s length: %s " \
            % (typ,self.name,reg,self.loc,len(self))

    # Insert all of my Binary instance's bytes list into my bytearray.  Convert
    # it to a bytes when done.
    def insert(self,trace=False):
        #cls_str="assembler.py - %s.insert() -" % self.__class__.__name__
        my_loc=self.loc
        for bin in self.elements:
            bin_loc=bin.loc
            if not bin_loc.isAbsolute():
                raise ValueError("%s enrountered non absolute address: %s" \
                    % (eloc(self,"insert"),bin))

            # Calculate where the data is supposed to go
            barray=bin.barray
            length=len(barray)
            start=bin_loc-my_loc
            end=start+length
            if length==0:
                if __debug__:
                    if trace:
                        print("%s %s @ %s inserted [0x%X:0x%X] bytes: %s IGNORED" \
                            % (eloc(self,"insert"),self.name,\
                                bin_loc,start,end,length))

                # ORG statements create Binary objects which have 0 bytes of data.
                # Ignore them
                continue

            if __debug__:
                if trace:
                    print("%s %s @ %s inserted [0x%X:0x%X] bytes: %s " \
                        % (eloc(self,"insert"),self.name,bin_loc,start,end,length))

            self.barray[start:end]=barray

        # Make me immutable
        self.barray=bytes(self.barray)

        if __debug__:
            if trace:
                dumpdata=hexdump.dump(self.barray,start=my_loc.address,indent="    ")
                print("\nCSECT %s Image Content:\n\n%s\n" % (self.name,dumpdata))

    def isdummy(self):
        return self._dummy

    def make_absolute(self,debug=False):
        if __debug__:
            if debug:
                print("%s CSECT %s converting Binary to absolute" \
                    % (eloc(self,"make_absolute"),self.name))

        for b in self.elements:
            b.make_absolute(debug=debug)

    def org(self,address):
        # Note: _org_pass1() method checked for an address within the current section
        self._current=address.value
        self._alloc=max(self._alloc,self._current)

    def make_barray_all(self,trace=False):
        #assert not self.isdummy(),\
        #    "%s method not supported for DSECT" % eloc(self,"make_barray_all")
        self.make_barray(trace=trace)
        for b in self.elements:
            b.make_barray(trace=trace)

    def updtAttr(self,asm,trace=False):
        if self.name=="":
            # Unnamed region or csect is not in the symbol table
            return
        try:
            ste=asm._getSTE(self.name)
        except KeyError:
            raise ValueError("%s element not in symbol table: %s" \
                % (eloc(self,"updtAttr"),self)) from None

                                                 # Update for CSECT   DSECT
        ste.attrSet("L",len(self))               #   L         yes     yes
        if not self.isdummy():                   #
            ste.attrSet("value",self.value())    # value       yes     no
            ste.attrSet("I",self.img_loc)        #   I         yes     no


# This class represent the top of the image content hierarchy.  It contains CSECT
# section instances.  A Regoion is created by a START statement and is added to the
# list of regions to be placed in the image.
class Region(Content):
    def __init__(self,name,start):
        super().__init__(8,Section)
        self.name=name
        # Value retrieved as a symbol (the start address)
        self.loc=AbsAddr(start)     # This value is static, it it the Regions STE
        self._base=start            # This never changes, used to calculate length
        self._current=start         # I start from my start address
        self.cur_sec=None           # The active section in this region

    def __len__(self):
        return self._alloc

    def __str__(self):
        return "%s(name='%s',start=%s)" \
            % (self.__class__.__name__,self.name,self.loc)

    def bind(self,address):
        # As sitting at the top of the hierarchy, a region can not be bound to a
        # higher level container.
        raise NotImplementedError("%s region does not support bind operation" \
            % eloc(self,"bind"))

    def current(self):
        return AbsAddr(self._current)

    def dump(self,indent="",string=False):
        lcl="%s    " % indent
        dumpdata=hexdump.dump(self.barray,start=self.loc.address,indent=lcl)
        dumpdata="\n%sRegion %s Image Content:\n\n%s\n" % (indent,self.name,dumpdata)
        if string:
            return dumpdata
        print(dumpdata)

    def dump_all(self):
        for c in self.elements:
            c.dump()
        self.dump()

    def locate_all(self,trace=False):
        my_base=self._base
        my_image_disp=self.img_loc
        for c in self.elements:
            # Calculates how far into this region is a csect based upon addresses
            csect_addr=c.loc.address
            csect_disp=csect_addr-my_base
            c.img_loc=my_image_disp+csect_disp

    # Insert all of my CSECT instance's bytes list into my bytearray.  Convert
    # it to a bytes when done.
    def insert(self,trace=False):
        cls_str="assembler.py - %s.insert() -" % self.__class__.__name__
        my_loc=self.loc
        for c in self.elements:
            c_loc=c.loc

            assert c_loc.isAbsolute(),\
                "%s enrountered non absolute address: %s" \
                    % (eloc(self,"insert"),c)

            # Calculate where the data is supposed to go
            barray=c.barray
            length=len(barray)
            start=c_loc-my_loc
            end=start+length
            if length==0:
                # A CSECT could have no data. Just ignore it
                if __debug__:
                    if trace:
                        print("%s %s @ %s inserted CSECT %s [0x%X:0x%X] bytes: %s "
                            "IGNORED" % (cls_str,self.name,c_loc,c.name,start,end,\
                                length))
                continue

            if __debug__:
                if trace:
                    print("%s %s @ %s inserted CSECT %s [0x%X:0x%X] bytes: %s " \
                        % (cls_str,self.name,c_loc,c.name,start,end,length))

            self.barray[start:end]=barray

        # Make me immutable
        self.barray=bytes(self.barray)

        if trace:
            self.dump()

    # Make all of by Binary insance's relative location addresses into absolute
    def make_absolute(self,debug=False):
        if __debug__:
            if debug:
                print("%s REGION %s making CSECT's absolute" \
                    % (eloc(self,"make_absolute"),self.name))

        for n in self.elements:
            n.make_absolute(debug=debug)

    def make_barray_all(self,trace=False):
        self.make_barray(trace=trace)
        for c in self.elements:
            c.make_barray_all(trace=trace)

# This is the content container for Regions.  It is used to ultimately create
# the binary image output provided by the Image object.
class Img(Content):
    def __init__(self):
        super().__init__(0,Region)
        self.name="IMAGE"       # May be updated by END statement
        self.img_cur=0

    def __str__(self):
        return "Img(name=%s,length=%s)" % (self.name,len(self))

    def bind(self,address):
        # As sitting at the top of the hierarchy, an Img can not be bound to a
        # higher level container.
        raise NotImplementedError("%s Image does not support bind operation" \
            % eloc(self,"bind"))

    def dump(self,indent="",string=False):
        lcl="%s    " % indent
        dumpdata=hexdump.dump(self.barray,start=0,indent=lcl)
        dumpdata="\n%s%s Image Content:\n\n%s\n" % (indent,self.name,dumpdata)
        if string:
            return dumpdata
        print(dumpdata)

    def dump_all(self):
        for r in self.elements:
            r.dump_all()
        self.dump()

    # Insert all of my Regions into my binary image byte array.  Convert it to a bytes 
    # list when done.
    def insert(self,trace=False):
        my_loc=0
        for r in self.elements:
            for c in r.elements:
                c.insert(trace=trace)   # Insert all the Binary's into the CSECT
            r.insert(trace=trace)       # Insert all the CSECT's into the Region
            # Insert each region into the imaga

            r_loc=r.img_loc

            # Calculate where the data is supposed to go
            barray=r.barray
            length=len(barray)
            start=r_loc-my_loc
            end=start+length
            self.barray[start:len(barray)]=barray

            # A region could have no data. Just ignore it
            if length==0:
                if __debug__:
                    if trace:
                        print("%s: %s @ +0x%X inserted region %s [0x%X:0x%X] "
                            "bytes: %s IGNORED" \
                            % (eloc(self,"insert"),self.name,r_loc,r.name,start,end,\
                                length))

                continue

            if __debug__:
                if trace:
                    print("%s %s @ +0x%X inserted region %s [0x%X:0x%X] bytes: %s " \
                        % (eloc(self,"insert"),self.name,r_loc,r.name,start,end,\
                            length))

        self.barray=bytes(self.barray)

        if trace:
            self.dump()

    # Locates Regions and CSECT's within the image.
    def locate_all(self,trace=False):
        for r in self.elements:
            r.img_loc=self.img_cur
            self.img_cur+=len(r)
            r.locate_all(trace=trace)
        self._alloc=self.img_cur     # This establishes the image length

    def make_barray_all(self,trace=False):
        self.make_barray(trace=trace)
        for r in self.elements:
            r.make_barray_all(trace=trace)

    def updtAttr(self,asm,trace=False):
        try:
            ste=asm._getSTE(self.name)
        except KeyError:
            raise ValueError("%s element not in symbol table: %s" \
                % (eloc(self,"updtAttr"),self))

        ste.attrSet("L",len(self))
        ste.attrSet("I",0)

    # The value provided by the first region is the image's value.
    def value(self):
        assert len(self.elements),\
            "%s image value depends upon its first region, no regions present" \
                % eloc(self,"value")

        region=self.elements[0]
        return region.value()


#
#  +------------------+
#  |                  |
#  |   Symbol Table   |
#  |                  | 
#  +------------------+
#

class Symbol(lang.STE):
    common_attributes=["L","value"]
    def __init__(self,name,entry,length=1,attr=[]):
        assert isinstance(entry,(Address,int,Section,Region,Img)),\
            "%s 'value' argument not of supported type: %s" \
                % (eloc(self,"__init__"),entry)

        self._attr=self._build_attr(attr)   # symbol's attribute dictionary
        self._entry=entry                   # Original source entry
        self._defined=None       # source statement number defining the symbol
        self._refs=[]            # source statements referencing this symbol
        self.__init(entry,length)           # Initialize attributes
        super().__init__(name)

    def _build_attr(self,attrs):
        if not isinstance(attrs,list):
            attr_list=[attrs,]
        else:
            attr_list=attrs

        for attr in Symbol.common_attributes:   
            if attr not in attr_list:
               attr_list.append(attr)

        attr_dict={}
        for attr in attr_list:
            assert isinstance(attr,str),\
                "%s attribute list entry not a string: %s" \
                % (eloc(self,"_build_attr"),attr)

            attr_dict[attr]=None

        return attr_dict

    def __init(self,entry,length):
        if isinstance(entry,Content):
            self.attrSet("L",len(entry))
            self.attrSet("value",entry.value())
        else:
            self.attrSet("L",length)
            self.attrSet("value",entry)

    def __len__(self):
        return self._attr["L"]

    def __str__(self):
        length=len(self)
        value=self.value()
        return "%s('%s',value=%s,length=%s,defn=%s,refs=%s)" \
            % (self.__class__.__name__,self.name,value,length,\
                self._defined,self._refs)

    # Retrive an attribute value.  Used internally and should not raise ValueError
    def attrGet(self,attr):
        try:
            return self._attr[attr]
        except KeyError:
            raise ValueError("%s 'attr' argument not a valid attribute for symbol "
                "%s: %s" % (eloc(self,"attrGet"),self.name,attr)) from None

    # Attempts to retrieve an attribute.  Will raise a KeyError if not defined
    # for the symbol.  The caller should catch the error and process it appropriately.
    def attrRef(self,attr):
        return self._attr[attr]

    # Retrive an attribute value.  Used internally and should not raise ValueError
    def attrSet(self,attr,value):
        try:
            self._attr[attr]
        except KeyError:
            raise ValueError("%s 'attr' argument not a valid attribute for symbol "
                "%s: %s" % (eloc(self,"attrSet"),self.name,attr)) from None
        self._attr[attr]=value

    def attrUpdate(self):
        raise NotImplementedError("%s subclass %s must implement attrUpdate() method" \
            % (eloc(self,"attrUpdate"),self.__class__.__name__))

    def content(self):
        raise NotImplementedError("%s content not supported by Symbol class" \
            % eloc(self,"content"))

    def queryType(self):
        entry=self._entry
        if isinstance(entry,Img):
            return "I"                       # I -> image
        if isinstance(entry,Region):
            return "R"                       # R -> region
        elif isinstance(entry,Section):
            if entry.isdummy():
                 return "D"                  # D -> DSECT
            else:
                 return "C"                  # C -> CSECT
        elif isinstance(entry,Address):
             return "A"                      # A -> address
        elif isinstance(entry,int):
             return "L"                      # L -> literal
        else:
             return "?"                      # ? -> NOT A GOOD SIGN

    # Add a reference to the symbol
    def reference(self,line):
        if not line in self._refs:
            self._refs.append(line)

    # This method returns the entries value attribute
    def value(self):
        return self.attrGet("value")

class SymbolContent(Symbol):
    def __init__(self,entry):
        assert isinstance(entry,(Section,Region,Img)),\
            "%s 'value' argument not of supported type: %s" \
                % (eloc(self,"__init__"),entry)

        super().__init__(entry.name,entry,attr="I")

    def __len__(self):
        value=self.value()
        return len(value)

    def __str__(self):
        value=self.value()
        return "%s(value=%s,defn=%s,refs=%s)" \
            % (self.__class__.__name__,value,self._defined,self._refs)

    def attrUpdate(self):
        self.attrSet("L",len(self))

    # Returns the defining Content instance
    def content(self):
        return self._entry

class ST(lang.SymbolTable):
    def __init__(self,case=False):
        super().__init__(write_once=True)
        self.case=case   # Enables or disables case sensitivity

    # Add a new lang.STE entry.  The 'line' argument is the defining statement number  
    # AssemblerError is raised if symbol already exists in the table
    def add(self,entry,line):
        if not self.case:
            entry.name=entry.name.upper()
        try:
            n=self[entry.name]
            raise AssemblerError(line=line,\
                msg="region, section or symbol already defined: '%s'" % entry.name) \
                from None
        except KeyError:
            pass
        entry._defined=line
        self[entry.name]=entry

    # Fetch a symbol by name.  Returns an instance of lang.STE.  
    # Raises KeyError if symbol is not defined 
    def get(self,item):
        if not self.case:
            return self[item.upper()]
        return self[item]

    # Returns a list of all symbol names.  If sort=True is specified the returned
    # list will be sorted.
    def getList(self,sort=False):
        labels=list(self.labels())
        if sort:
            labels.sort()
        return labels

    # Returns True if item is defined, False otherwise
    def isdefined(self,item):
        try:
            if not self.case:
                self[item.upper()]
            self[item]
        except KeyError:
            return False
        return True

    # This method produces a human readable view of the Symbol Table.  If string is 
    # True, a string suitable for printing is supplied.  Otherwise, each line is
    # printed when built.  It is still somewhat internally focus and is not
    # really ready for a listing.
    def print(self,indent="",string=False):
        # Sort the symbols
        labels=[]
        for lbl in self.labels():
            labels.append(lbl)
        labels.sort()        # Sort the entries

        length=0
        for lbl in labels:
            length=max(length,len(lbl))

        lclindent="%s%s" % (indent," " * (length+5))
        s=''
        for lbl in labels:
            sym=self.get(lbl)        # STE object
            entry=sym._entry         # entry object
            typ=sym.queryType()      # entry type (see queryType() method)

            attrs=sym._attr.keys()
            attr=[]
            for a in attrs:
                attr.append(a)
            attr.sort()

            attr_str=""
            for a in attr:
                at=sym.attrGet(a)
                attr_str="%s%s:%s " % (attr_str,a,at)
            attr_str=attr_str[:-1]  # Drop last space
            lbl_str=lbl.ljust(length)
            line1="%s%s  %s  %s\n" % (indent,lbl_str,typ,attr_str)
            if typ in ["A","L"]:
                line2=""
            else:
                line2="%sentry: %s\n" % (lclindent,entry)
            line3="%sdefn: %s, refs: %s" % (lclindent,sym._defined,sym._refs)
            s="%s%s%s%s\n" % (s,line1,line2,line3)

        s=s[:-1]       # Drop the trailing line termination
        if string:
            return s
        print(s)


#
#  +-------------------------+
#  |                         |
#  |   Output Image Object   |
#  |                         | 
#  +-------------------------+
#

# The output of the Assembler class instance.  Provided by Assembler.image() method
class Image(object):
    def __init__(self):
        self.source=[]       # Supplied by Assembler.statement() as received
        self.aes=[]          # List of AssemblerError exceptions generated
        self.deck=None       # Supplied by AsmBinary.deck()
        self.ldipl=None      # Supplied by AsmBinary.ldipl() - see Note below
        self.listing=None    # Supplied by Assembler.LM.create()
        self.mc=None         # Supplied by AsmBinary.mc_file()
        self.rc=None         # Supplied by AsmBinary.rc_file()
        self.vmc=None        # Supplied by AsmBinary.vmc_file()
        self.load=None       # Supplied by Assembler.__finish()
        self.entry=None      # Supplied by Assembler.__finish()
        self.image=None      # Supplied by Assembler.__finish() from imqwip
        # Note: self.ldipl when used will contain a list of three element tuples
        # Each tuple will contain:
        #   tuple[0] - file name within the list directed IPL directory
        #   tuple[1] - file content
        #   tupel[2] - Python open mode for writing the file

    # Add an error to the Image
    def _error(self,ae):
        self.aes.append(ae)

    # Add an input Line instance to the source list
    def _statement(self,line):
        self.source.append(line)

    def errors(self):
        aes=sorted(self.aes,key=AssemblerError.sort)
        for ae in aes:
            print(ae)

    def statements(self,string=False):
        locsize=0
        for stmt in self.source:
            locsize=max(locsize,stmt.prefix())

        if string:
            st=""
            for stmt in self.source:
                st="%s%s\n" % (st,stmt.print(locsize=locsize,string=string))
            return st[:-1]
        for stmt in self.source:
            stmt.print(locsize=locsize)  


if __name__ == "__main__":
    raise NotImplementedError("assembler.py - intended for import use only")
