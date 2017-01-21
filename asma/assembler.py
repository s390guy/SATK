#!/usr/bin/python3
# Copyright (C) 2014-2017 Harold Grovesteen
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
# binary image files from a simple source language.  It is intended for import use 
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

this_module="%s.py" % __name__

# ASMA version tuple:
asma_version=(0,2,0)

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
        #self.proc_timer("pass0_p")
        #self.wall_timer("pass0_w")
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
        #string="%s\n      pass 0  %s" % (string,self.__format(wt,timer="pass0_w"))
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
        #string="%s\n      pass 0  %s" % (string,self.__format(pt,timer="pass0_p"))
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
            "%s %s timer already stopped" % (eloc(self,"stop"),self.name)

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

#
#  +--------------------------------------------+
#  |                                            |
#  |  ASMA Shared Regular Expression Patterns   |
#  |                                            | 
#  +--------------------------------------------+
#

# These definitions provide consistency between different modules definitions
# Note: These module attributes must be defined before other imported ASMA modules 
# access them when imported below.
char="\$@\#_"                        # Special characters used in names
multiline="(?m)"                    # Turns on multiline for start/end match
cmt="\*|\.\*"                       # An asterisk or a period followed by an asterisk
inst="[a-zA-Z]+[0-9]*"              # An instruction pattern
ws="[ \t\r\f\v]"                    # White space characters
stuff=".*"                          # Stuff at the end of the line
opend="([ ]|$)"                     # End of operands, a space or end of string

# Label pattern with special chracters
label="[a-zA-Z%s][a-zA-Z0-9%s]*" % (char,char)
label_re=re.compile(label)

# ASMA imports (do not change the sequence)
import lnkbase      # 0.2 - Access linkage editing base classes
import asmtokens    #       Access various tokens
import asmbase      # 0.2 - Access assembler base classes
import asmline      # 0.2 - Access the logical line input manager
import asmstmts     # 0.2 - Directive, instruction and macro statements
import macopnd      # 0.2 - Macro operand handling
import asmbin       #       Access binary output generator
import asminput     #       Access the input handler for the assembler
import asmlist      #       Access the assembler listing generator
import asmmacs      #       Access the macro framework
import asmoper      #       Access the operation management framework
import asmopnd      # 0.2 - Assembler operand processing
import parsers      # 0.2 - Consolidates parser management module
import insnbldr     #       Access the machine instruction construction machinery
import literal      # 0.2 - Access the literal pool support.  See late imports
import msldb        #       Access the Format class for type checking

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
        if token is not None:
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

    def __init__(self,source=None,line=None,linepos=None,msg="",info=False,\
                 nostmt=False):
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
        # If True, error not reported with statment only in the summary
        self.nostmt=nostmt

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
#  +----------------------+
#  |                      |
#  |   Shared Functions   |
#  |                      | 
#  +----------------------+
#

# Determine if a string is a valid label
def isLabel(string):
    mo=label_re.match(string)
    if mo is None:
        return False
    # If matching substring is the same as the value, it is a label
    return mo.group()==string


#
#  +---------------------------------+
#  |                                 |
#  |   A Small Mainframe Assembler   |
#  |                                 | 
#  +---------------------------------+
#


# This class manages output options directed to the assembler.  None implies the 
# output is not written to the file system (although it might be created internally).
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


# This class implements a small mainframe assembler consisting of a subset of 
# mainframe assembler functions.  Its output is a binary image of the assembled
# statements.
#
# The Assembler is designed to be a backend supporting some front end process that 
# presents source statements to the assembler for assembly.  The asma.py module
# provides a command line interface to this assembler.
#
# The following instance methods are used by the front end process:
#
#   assemble     Assembles queued statements and creates the output Image instance
#                AsmOut object containing the various supported output.
#   image        Retrieves the AsmOut object used to generate output.  Output
#                generation is the responsibility for the front end process.
#

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
    debug=["stmt","insns","exp","tracexp"]

    # Lexical analyzers (created by __init_parsers() method)
    lexer=None     # Default Lexical analyzer used by most FSM-based parsers
    sdterm=None    # Self-defining term parser used by SETC symbols

    # Returns my global debug manager.
    @staticmethod
    def DM():
        return satkutil.DM(appl=Assembler.debug,lexer=True,parser=False)

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

    # Assembler object.  All processing occurs via this class.  Global state is
    # managed here.  The object is passed around to various methods accessing or 
    # updating global state.
    #
    # Instance arguments:
    #
    #   machine     The string ID of the targeted system or cpu in the MSL database
    #   msl         The requested MSL database file
    #   mslpath     Path Manager for  the Machine Specification Language database
    #   aout        AsmOut object describing output characteristics.
    #   addr        Size of addresses in this assembly.  Overrides MSL CPU statement
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
    #   mcall       Specify True to enable inner macro statement printing when
    #               PRINT ON is the current printing statements.
    #   stats       Specify True to enable statistics reporting at end of pass 2.  
    #               Should be False if an external driver is updating statistics.
    # Path Managers for various input sources:
    #   asmpath     Assembler source COPY directive PathMgr object
    #   maclib      Macro library PathMgr object
    def __init__(self,machine,msl,mslpath,aout,addr=None,case=False,\
                 debug=None,defines=[],dump=False,eprint=False,error=2,nest=20,\
                 ccw=None,psw=None,ptrace=[],otrace=[],cpfile=None,cptrans="94C",\
                 mcall=False,stats=False,asmpath=None,maclib=None):

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
        self.case=case              # Specifies if case sensitivity is enabled.
        self.cpfile=cpfile          # Code page source file (defaults to built-in)
        self.cptrans=cptrans        # Code page translation definition to use
        self.gblc=defines           # GBLC/SETC definitions from driver.
        self.mcall=mcall            # Print inner macro statements

        # PathMgr objects
        self.asmpath=asmpath        # Assembler COPY directive search order path
        self.macpath=maclib         # Macro library search order path

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

        # Statement operand parsers. See __init_parsers() method
        self.PM=self.__init_parsers()
        Assembler.sdterm=self.PM.parsers["sdterm"]
        
        # Statement processor drives processing
        self.SP=STMTProcessor(self,depth=nest)
        # Input manager used by processor (access provided for new input sources)
        self.IM=self.SP.IM     # An asmline.LineMgr object
        
        # MACLIB processor for macro library definitions
        self.MP=MACLIBProcessor(self)

        # Operation Management Framework
        self.OMF=asmoper.OperMgr(self,machine,msl,mslpath)
        self.OMF.init_xmode(ccw,psw)      # Initialize XMODE settings
        self.addrsize=self.OMF.addrsize   # Maximum address size in bits

        # Create the machine instruction construction engine and CPU related values
        self.builder=insnbldr.Builder(trace=self.dm.isdebug("insns"))
        # Create structure templates
        self.__init_templates(self.builder) # Updates class attribute struct

      #
      #   Sequence dependent initialization completed
      #   Remaining initialization is sequence independent
      #

        # Prepare operation trace for internal use
        self.__init_otrace()

        # Manage ASCII/EBCDIC codepages by building the codepage.Translator object
        self.trans=self.__init_codepage()
        # The Translater object is available now via this object attribute and
        # in modules that import assembler via assembler.CPTRANS
        
        # Literal Pool Management
        self.LPM=literal.LiteralPoolMgr(self)

        # Macro Language processing manager
        self.MM=asmmacs.MacroLanguage(self)
        # Define external global SETC symbols
        for sym,val in self.gblc:
            try:
                self.MM._init_gblc(sym,val)
            except asmmacs.MacroError as me:
                self._ae_excp(AssemblerError(msg=me.msg),None)

        # Manage output binary data
        self.OM=asmbin.AsmBinary()

        # These attributes are constructed and manipulated by statement() method
        self.lineno=1         # Next statement number for source listing
        self.stmts=[]         # List of parsed Stmt instances
        # These attributes are manipulated by the assemble() method
        self.cur_stmt=None    # In numbered pass processing, current Stmt instance
        self.cur_pass=0       # Current Pass

        # Current Location Counter - value of an asterisk in address expression
        self.cur_loc=LocationCounter()

        # These attributes are constructed and manipulated during the various 
        # assembler passes performed on the statements stored in self.stmts list.

        # Base register assignment manager
        self.bases=BaseMgr(extended=machine=="360-20")

        # Symbol Table used for all symbols
        self.ST=asmbase.ASMSymTable(asmbase.ASMSymEntry,asmtokens.ATTR,\
            wo=True,case=self.case)
        # ADD unique name here!!!
        self.imgwip=Img()     # Work in progress image container of Regions

        # These lists assist in finalizing output both the image data and listing.
        self.dcs=[]           # List of DC Stmt objects that must fill in barray
        self.dsects=[]        # DSECT list to allow finalization
        self.equates=[]       # These must be bound to an absolute address
        self.usings=[]        # These too must be bound to an absolute address

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
        # Listing stack controlled by the PUSH and POP directives
        self.pstack=[]        # Stack of tuples: (pon,pgen,pdata)

        # Stop object timers
        Stats.stop("objects_w")
        Stats.stop("objects_p")

  #
  # PRIVATE METHODS - Only callable by this object
  #


    # Initialize the code page translator and make it globally available via
    # the assembler.CPTRANS for modules that import assembler.
    def __init_codepage(self):
        global CPTRANS
        trans=codepage.CODEPAGE().build(trans=self.cptrans,filename=self.cpfile)
        CPTRANS=trans
        return trans

    # Process command line --oper arguments for internal use.
    def __init_otrace(self):
        new_list=[]
        for ot in self.otrace:
            new_list.append(ot.upper())
        self.otrace=new_list

    def __init_parsers(self,debug=False):
        # These lexical analyzers are assigned to Assembler class attributes.
        Assembler.lexer=parsers.AsmLexer(self.dm).init()

        # These syntactical analyzers are assigned to Assembler class attributes,
        # and are not part of the Assembler object's parsers attribute dictionary.
        return parsers.ParserMgr(self).init()

    # Initialize structure template used by most TemplateStmt subclasses
    def __init_templates(self,builder):
        asmstmts.CCW0.structure(builder)
        asmstmts.CCW1.structure(builder)
        asmstmts.PSWS.structure(builder)
        asmstmts.PSW360.structure(builder)
        asmstmts.PSW67.structure(builder)
        asmstmts.PSWBC.structure(builder)
        asmstmts.PSWEC.structure(builder)
        asmstmts.PSW380.structure(builder)
        asmstmts.PSWXA.structure(builder)
        asmstmts.PSWE370.structure(builder)
        asmstmts.PSWE390.structure(builder)
        asmstmts.PSWZ.structure(builder)

  #
  # QUASI PUBLIC METHODS - METHODS USED BY STATEMENT PROCESSING METHODS
  #

    # Performs generic AssemblerError exception handling
    def _ae_excp(self,ae,stmt,string="",debug=False):
        if stmt is not None:
            stmt.ae_error(ae)
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
    def _check_cur_reg(self,start=0,debug=False):
        if self.cur_reg is not None:
            return
        # No current region.  This occurs only in an assembly lacks a START directive.
        # The START directive will always create either a named or unnamed region
        # and activate it.
        if self.unname_reg is None:
            # Unnamed region does not exist, so create it
            self.unname_reg=self._region_unname(0,debug=debug)
        # Activate the unnamed region.  This can result in an unassigned active 
        # section if the unnamed region just created is activated.
        self._region_activate(self.unname_reg,debug=debug)

    # Checks to make sure the current active section is assigned
    # If not, if necessary, it creates an unnamed section and activates it
    #
    # An active section is not assigned when the assembly has neither a START nor
    # a CSECT statement.  Automatic creation of an unnamed section occurs when
    # binary content is created or space is allocated without an active section.
    def _check_cur_sec(self,debug=False):
        if self.cur_sec is not None:
            return
        # Unnamed section does not exist, create it
        if self.unname_sec is None:
            self.unname_sec=self._csect_unname(debug=debug)
        # Automatically activate the unnamed section
        # Activation may trigger creation of an unnamed region if one is not active
        self._csect_activate(self.unname_sec,debug=debug)

    def _csect_activate(self,section,debug=False):
        assert isinstance(section,Section),\
            "%s 'section' argument must be a CSECT: %s" \
                % (eloc(self,"_csect_activate"),section)
        assert not section._dummy,"%s 'section' argument must be a CSECT: %s" \
            % (eloc(self,"_csect_activate"),section)
        assert self.cur_reg is not None,\
            "%s current active region must not be None" \
                % eloc(self,"_csect_activate")

        self.cur_reg=section.container
        self.cur_sec=section
        self.cur_reg.cur_sec=section
        self.cur_loc.establish(section.current())

        if __debug__:
            if debug:
                cls_str=eloc(self,"_csect_activate")
                print("%s current active region is:  '%s'" \
                    % (cls_str,self.cur_reg.name))
                print("%s current active section is: '%s'" \
                    % (cls_str,self.cur_sec.name))

    # Creates a new CSECT, adds it to the active region and symbol table.
    # Returns the new Section instance to the caller.
    def _csect_new(self,line,csect_name,debug=False):
        if not self.case:
            csect=Section(csect_name.upper())
        else:
            csect=Section(csect_name)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"_csect_new"),csect))

        self._check_cur_reg(debug=debug)
        self.cur_reg.append(csect)

        if __debug__:
            if debug:
                print("%s added %s to current region: '%s'" \
                    % (eloc(self,"_csect_new"),csect.name,self.cur_reg.name))

        symbol=LabelSymbol(csect.name,csect,T="J")
        self._symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s CSECT added to symbol table: '%s'" \
                    % (eloc(self,"_csect_new"),csect_name))

        return csect

    # Access symbol table to retrieve a CSECT instance
    # Raises a KeyError if not present in the symbol table.
    # Raises an AssemblerError if symbol defined but isn't a CSECT
    def _csect_ref(self,stmt,sect_name):
        ste=self._symbol_ref(sect_name)

        if ste["T"] != "J":
            raise AssemblerError(line=stmt.lineno,\
                msg="symbol already defined: '%s'" % sect_name)

        return ste.value()

    # Determines if it is safe to create a new named csect.
    # Raises an AssemblerError if not.
    def _csect_safe(self,stmt,sect_name):
        try:
            self._symbol_ref(sect_name)
            # Success by this method means the named CSECT is already defined
            raise AssemblerError(line=stmt.lineno,\
                msg="can not create CSECT, CSECT name defined: %s" % sect_name)
        except KeyError:
            pass

    # Create an unnamed control section and regiser it with the active region
    def _csect_unname(self,debug=False):
        section=Section("")

        if __debug__:
            if debug:
                print("%s Created new: %s" \
                    % (eloc(self,"_csect_unname"),section))

        self._check_cur_reg(debug=debug)
        self.cur_reg.append(section)

        if __debug__:
            if debug:
                print("%s added %s to current region: '%s'" \
                    % (eloc(self,"_csect_unname"),section.name,self.cur_reg.name))

        return section

    # Tests whether the unnamed control section can be created.
    def _csect_unname_safe(self,stmt):
        if self.unname_sec:
            raise AssemblerError(line=stmt.lineno,msg="unnamed CSECT already exists")

    def _dsect_activate(self,section,debug=False):
        assert isinstance(section,Section) and section.isdummy(),\
            "%s 'section' argument must be a DSECT: %s" \
                % (eloc(self,"_dsect_activate"),section)

        self.cur_sec=section
        self.cur_loc.establish(section.current())

        if __debug__:
            if debug:
                cls_str=eloc(self,"_dsect_activate")
                print("%s current active region is:  '%s'" % (cls_str,self.cur_reg))
                print("%s current active section is: '%s'" \
                    % (cls_str,self.cur_sec.name))

    # Creates a new CSECT, adds it to the active region and symbol table.
    # Returns the new Section instance to the caller.    
    def _dsect_new(self,line,dsect_name,debug=False):
        if not self.case:
            dsect=Section(dsect_name.upper(),dummy=True)
        else:
            dsect=Section(dsect_name,dummy=True)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"_dsect_new"),dsect))

        self.dsects.append(dsect)
        symbol=LabelSymbol(dsect.name,dsect,T="4")
        self._symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s DSECT added to symbol table: '%s'" \
                    % (eloc(self,"_dsect_new"),dsect_name))

        return dsect

    # Access symbol table to retrieve a DSECT instance
    # Raises a KeyError if not present in the symbol table.
    # Raises an AssemblerError if symbol defined but isn't a CSECT
    def _dsect_ref(self,stmt,sect_name):
        ste=self._symbol_ref(sect_name)

        try:
            sect=ste.value()
        except NotImplementedError:  
            # This means the symbol value is not Content, so not a DSECT
            raise AssemblerError(line=stmt.lineno,\
                msg="symbol already defined: '%s'" % sect_name)

        if not isinstance(sect,Section) or not sect.isdummy():
            raise AsseblerError(line=stmt.lineno,\
                msg="symbol is not a DSECT: '%s'" % sect_name)
        return sect

    # Semi-private method intended to provide information about an internal error
    # while processing a statement in Pass 1 or 2.
    # Returns: an information string
    def _error_passn(self):
        phase=self.SP.cur_phase
        if self.cur_stmt:
            line=self.cur_stmt.logline
            line="[%s] %s" % (self.cur_stmt.lineno,line.plines[0].content)
            return "Phase '%s' INTERNAL ERROR WHILE PROCESSING THIS STATEMENT" \
                "\n    %s" % (phase,line)
        return \
            "Phase '%s' INTERNAL ERROR LIKELY DURING PRE- OR POST-PASS PROCESSING" \
                % phase

    # Finish the Image (with the exception of the listing)
    def _finish(self):
        wip=self.imgwip
        image=self.img

        image.load=lnkbase.Address.extract(self.load)
        image.entry=lnkbase.Address.extract(self.entry)
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

    def _getAttr(self,name,attr,line):
        ste=self._symbol_ref(name)
        try:
            #value=ste.attrRef(attr)
            value=ste[attr]
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

    # Return the O attribute of an operation name
    # WARNING: Any changes to method arguments must be matched with the arguments of
    # the asmmacs.Invoker._getAttr_O() method.
    def _getAttr_O(self,oper):
        return self.OMF.get_O_attr(oper)

    # Returns the symbol table entry without generating a symbol reference
    # WARNING: Any changes to method arguments must be matched with the arguments of
    # the asmmacs.Invoker._getSTE_Ref() method.
    def _getSTE(self,name):
        return self._symbol_ref(name)

    # Returns the symbol table entry in its entirety (including symbol attributes).
    # Generates a reference to the symbol for the supplied line.
    def _getSTE_Ref(self,name,line):
        ste=self._symbol_ref(name)
        ste.reference(line)
        return ste

    # Returns a symbols value and updates its list of referenced lines.
    # Raises KeyError if not defined
    def _getSymbol(self,string,line):
        ste=self._symbol_ref(string)
        value=ste.value()
        ste.reference(line)
        return value

    # Adds the Img as a symbol
    def _image_new(self,debug=False):
        image=self.imgwip
        symbol=LabelSymbol(image.name,image,T="1")
        symbol.update(M=0)
        self._symbol_define(symbol,0)

    # Returns whether a specific operation is being traced:
    def _is_otrace(self,oper):
        return oper.upper() in self.otrace

    # Defines a label based upon the supplied statement's location.
    # Label's location is based upon the Stmt.content object's location
    # Method Arguments:
    #   stmt    The Stmt object whose label is being defined.  The Stmt.content's
    #           Binary object defines the label's value.
    #   label   The label being defined
    #   length  The length assigned to the label.  If None is specified or ommitted,
    #           the length of the of the Stmt.content Binary object becomes the
    #           label's assigned length.  Defaults to None.
    def _label_create(self,stmt,label,length=None,T="U",S=0,I=0):
        bin=stmt.content
        if length is None:
            leng=bin._length
        else:
            leng=length

        sym=LabelSymbol(label,bin.loc,length=leng,T=T,S=S,I=I)
        #print("%s %s" % (eloc(self,"_label_create",module=this_module),sym))
        self._symbol_define(sym,line=stmt.lineno)

    # The supplied region becomes the active region and its active CSECT the 
    # active CSECT of the assembly.
    def _region_activate(self,region,debug=False):
        assert isinstance(region,Region),\
            "%s 'region' argument must be an instance of Region: %s"\
                % (eloc(self,"_region_activate"),region)

        if __debug__:
            if debug:
                print("%s region activation started" % eloc(self,"_region_activate"))

        self.cur_reg=region
        self.cur_sec=region.cur_sec
        if self.cur_sec:
            self.cur_loc.establish(self.cur_sec.current())

        if __debug__:
            if debug:
                print("%s current active region is:  '%s'" 
                    % (eloc(self,"_region_activate"),self.cur_reg.name))
                if self.cur_sec is None:
                    print("%s current active section is: None" \
                        % eloc(self,"_region_activate"))
                else:
                    print("%s current active section is: '%s'" \
                        % (eloc(self,"_region_activate"),self.cur_sec.name))

    # Creates a new region, adds it to the region list and symbol table.
    # Returns the new Region instance to the caller.
    def _region_new(self,line,region_name,start,debug=False):
        # Now that we have successfully processed the START statement, the new Region
        # instance can be built.
        if not self.case:
            region=Region(region_name.upper(),start)
        else:
            region=Region(region_name,start)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"_region_new"),region))

        symbol=LabelSymbol(region.name,region,T="2")
        self._symbol_define(symbol,line)

        if __debug__:
            if debug:
                print("%s region added to symbol table: '%s'" \
                    % (eloc(self,"_region_new"),region_name))

        self.imgwip.append(region)

        if __debug__:
            if debug:
                print("%s regions in Img: %s" \
                    % (eloc(self,"_region_new"),len(self.imgwip.elements)))

        return region

    # Access symbol table to retrieve a Region instance.
    def _region_ref(self,stmt,reg_name):
        try:
            ste=self._symbol_ref(reg_name)
        except KeyError:
            raise AssemblerError(line=stmt.lineno,\
                msg="region symbol is undefined: '%s'" % reg_name)

        # symbol is defined, but determine if it is a Region or not
        if ste["T"] != "2":
            raise AssemblerError(line=stmt.lineno,\
                msg="region symbol already defined: '%s'" & reg_name)

        # Symbol defines a region so return it without having raised any exceptions
        #return region.content()
        return ste.value()

    # Determines if it is safe to create a new named region
    # Raises an AssemblerError if not.
    def _region_safe(self,stmt,reg_name):
        try:
            self._symbol_ref(reg_name)
            raise AssemblerError(line=stmt.lineno,\
                msg="can not create named region, region name defined: %s" % reg_name)
        except KeyError:
            pass

    # Creates an unnamed region, adding it to the image being created
    # Returns:
    #   the created unnamed region
    def _region_unname(self,start,debug=False):
        region=Region("",start)

        if __debug__:
            if debug:
                print("%s Created new: %s" % (eloc(self,"_region_unname"),region))

        self.imgwip.append(region)

        if __debug__:
            if debug:
                print("%s regions in Img: %s" \
                    % (eloc(self,"_region_unname"),len(self.imgwip.elements)))

        return region

    def _region_unname_safe(self,stmt):
        if self.unname_reg:
            raise AssemblerError(line=stmt.lineno,\
                msg="unnamed region already exists")

    # Attempt to resolve an address into its base/displacement pair of values.
    # Raises an AssemblerError exception if resolution fails.
    def _resolve(self,address,lineno,opn,size,trace=False):
        try:
            return self.bases.find(address,size,self,trace=trace)
        except KeyError:
            raise AssemblerError(line=lineno,\
                msg="operand %s could not resolve implied base register for "
                    "location: %s" % (opn+1,address)) from None

    # Define a unique symbol in the symbol table.
    def _symbol_define(self,sym,line):
        self.ST.add(sym,line=line)

    # Return a symbol table entry (STE) being referenced.  Does NOT update the list
    # of referencing line numbers.
    # Raises KeyError if not defined
    def _symbol_ref(self,sym):
        return self.ST.get(sym)

    # Retrieve the name of the current active constrol section.  If no active
    # section exists, the empty string (indicating the unnamed control section)
    # it returned
    def _sysect(self):
        if self.cur_sec is None:
            return ""
        return self.cur_sec.name

    # Pass 2 - track the statement location in the location counter and the statement
    #
    # Note: During Pass 1 this tracking is handled by the individual statements that
    # need it: EQU, ORG, USING
    def _track_loc(self,stmt):
        new_con=stmt.content
        if new_con:
            new_loc=new_con.loc
            if __debug__:
                if stmt.trace:
                    print("%s [%s] statements binary location: %s" 
                        % (eloc(self,"_track_loc"),stmt.lineno,new_loc))
            if new_loc:
                stmt.location=stmt.p2_loc=new_loc
                self.cur_loc.establish(new_loc,debug=stmt.trace)
                if __debug__:
                    if stmt.trace:
                        print("%s [%s] Updated location counter: %s" \
                            % (eloc(self,"assemble"),stmt.lineno,\
                                self.cur_loc.location))

  #
  # PUBLIC METHODS
  #

    # Assemble source from an input file returning result from processor
    # Returns:
    #   True if a successful run
    #   False if an unsuccessful run
    def assemble(self,filename):
        return self.SP.run(self,filename)

    # Returns the completed Image instance for processing
    # See asma.py for an example.
    def image(self):
        return self.img


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
        assert isinstance(addr,lnkbase.Address),\
            "%s 'addr' argument must be an instance of lnkbase.Address: %s" \
                % (eloc(self,"__init__"),addr)
        assert (direct is None) or isinstance(direct,lnkbase.AbsAddr),\
            "%s 'direct' argument must be None or an instance of " \
                "lnkbase.AbsAddr: %s" % (eloc(self,"__init__"),direct)

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
        assert isinstance(addr,lnkbase.Address),\
            "%s 'addr' argument must be an instance of lnkbase.Address: %s" \
                % (eloc(self,"getDisp"),addr)

        return addr.base()-self.address
        # Note: no checks are performed on the actual displacement.  Different
        # values are allowed for different instruction formats.  Whether the
        # displacement is appropriate for the instruction must be tested elsewhere.


# This class manages base registers, USING, DROP and base/disp resolution
class BaseMgr(object):

    # These class attributes manage direct mode addressing
    # One direct mode register in use
    #direct1={0:AbsAddr(0x0000)}       # 4K        0x0000 ->       0
    direct1={0:lnkbase.AbsAddr(0x0000)}       # 4K        0x0000 ->       0
    # Eight direct mode registers in use
    direct8=\
        {0:Base(0,lnkbase.AbsAddr(0x0000)),   # 4K        0x0000 ->       0
         1:Base(1,lnkbase.AbsAddr(0x1000)),   # 8K        0x1000 ->   4,096
         2:Base(2,lnkbase.AbsAddr(0x2000)),   # 12K       0x2000 ->   8,192
         3:Base(3,lnkbase.AbsAddr(0x3000)),   # 16K       0x3000 ->  12,288
         4:Base(4,lnkbase.AbsAddr(0x0000)),   # 4K        0x4000 ->  16,384
         5:Base(5,lnkbase.AbsAddr(0x1000)),   # 8K        0x5000 ->  20,480
         6:Base(6,lnkbase.AbsAddr(0x2000)),   # 12K       0x6000 ->  24,576
         7:Base(7,lnkbase.AbsAddr(0x3000))}   # 16K       0x7000 ->  28,672

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

         based=None
         try:
             based=self.bases[reg]
         except KeyError:
             pass
         # Check to see if the base has already been dropped
         if based is None:
             return
             # Nothing more to do for an already dropped base

         try:
             del based[reg]        # Remove the base assigned to the register
         except KeyError:
             pass
         try:
             self.bases[reg]=None  # This means the base is now dropped
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
        assert isinstance(addr,lnkbase.Address),\
            "%s 'addr' argument must be an instance of lnkbase.Address: %s" \
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
        assert isinstance(addr,lnkbase.Address),\
            "%s 'addr' argument must be an instance of lnkbase.Address: %s" \
                % (cls_str,addr)
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
        self.section=None
        self.location=None
        self.disp=0
        
    def __str__(self):
        return "LocCtr: sec:%s loc:%s disp:%s" \
            % (self.section,self.location,self.disp)

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
           assert isinstance(new_loc,lnkbase.Address) and \
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
        assert isinstance(loc,lnkbase.Address),\
            "%s 'loc' argument must be a lnkbase.Address object: %s" \
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
                print("%s bin: %s" % (eloc(self,"increment"),bin))
        if bin:
            self.establish(bin.loc+len(bin),debug=debug)

    def retrieve(self):
        if self.location is None:
            return None
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
        return "%s(alignment=%s,length=%s,barray=%s,loc=%s)" \
            % (self.__class__.__name__,self._align,self._length,barray,self.loc)

    def assigned(self,loc):
        self.loc=loc
        if isinstance(loc,lnkbase.SectAddr):
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
                    desc="%s '%s'" % (cls_str,self.name)
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
        assert isinstance(self.barray,bytearray),\
            "%s can not update %s, self.barray is not a bytearray: %r" \
                % (eloc(self,"update"),self.__class__.__name__,self.barray)
        if isinstance(data,str):
            #print("%s data is a string: %s"\
            #    % (eloc(self,"update"),data))
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
        
        # Allocation system - Supplied by subclass during initialization, if used.
        #self._allocation=None

    # Return the current lengh
    def __len__(self):
        return self._alloc

    # Align the current location to the content's requirement
    def align(self,content):
        assert isinstance(content,Binary),\
            "%s 'content' argument must be an instance of Binary: %s" \
                % (eloc(self,"align"),content)

        #self._allocation.align(content._align)

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
            
        #self._allocation.alloc(siz)

        self._current+=siz
        self._alloc=max(self._alloc,self._current-self._base)

    # Add an element to this content container.  Elements are unallocated and unbound
    def append(self,content):
        assert isinstance(content,self.cls),\
            "%s 'content' argument must be an instance of %s: %s" \
                % (eloc(self,"append"),content)
        assert content.container is None,\
            "%s 'content' argument must not already be in a container, %s in %s" \
                % (eloc(self,"append"),content,content.container)

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
        assert isinstance(bindto,lnkbase.Address),\
            "%s 'bindto' argument must be an instancce of lnkbase.Address: %s" \
                % (eloc(self,"bind"),bindto)
        assert bindto.isAbsolute(),\
            "%s 'bindto' argument must be an absolute address: %s" \
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

        ste.update(L=len(self),M=self.img_loc)

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
        self.name=name
        super().__init__(8,Binary)
        self._current=0           # I start from 0
        self._base=0              # My base is also zero
        self._dummy=dummy         # From DSECT
        if dummy:
            self.loc=lnkbase.DDisp(0,self)
        else:
            self.loc=lnkbase.SectAddr(0,self)
            
        #self._allocation=lnkbase.Allocation(self.name,typ="S")
            
        # List of location counters associated with this
        self.counters=[]

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
            return lnkbase.DDisp(self._current,self)
        return lnkbase.SectAddr(self._current,self)

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

    def lval(self):
        return self.loc.lval()

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
        self.make_barray(trace=trace)
        for b in self.elements:
            b.make_barray(trace=trace)

    def new_counter(self):
        ctr=LocationCounter(self)
        self.counters.append(ctr)
        return ctr

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
        ste.update(L=len(self))                  #   L         yes     yes
        if not self.isdummy():                   #
            ste.update(M=self.img_loc)           #   M         yes     no


# This class represent the top of the image content hierarchy.  It contains CSECT
# section instances.  A Regoion is created by a START statement and is added to the
# list of regions to be placed in the image.
class Region(Content):
    def __init__(self,name,start):
        self.name=name
        super().__init__(8,Section)
        # Value retrieved as a symbol (the start address)
        self.loc=lnkbase.AbsAddr(start) # This value is static, it it the Regions STE
        self._base=start                # This never changes, used to calculate length
        self._current=start             # I start from my start address
        self.cur_sec=None               # The active section in this region
        
        #self._allocation=lnkbase.Allocation(self.name,typ="R",start=start)

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
        return lnkbase.AbsAddr(self._current)

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

    def lval(self):
        return self.loc.lval()

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
        self.name="IMAGE"       # May be updated by END statement
        super().__init__(0,Region)
        self.img_cur=0
        
        self._allocation=lnkbase.Allocation(self.name,typ="I",start=self.img_cur)

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

    def lval(self):
        return self.value().address

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

        ste.update(L=len(self),M=0)

    # The value provided by the first region is the image's value.
    def value(self):
        # If there are no regions, then assume this object starts at absolute zero.
        # No regions exist for an assembly that does not create them, for example
        # when there are only DSECT's being assembled.
        if len(self.elements) == 0:
            return lnkbase.AbsAddr(0)

        region=self.elements[0]
        return region.value()


#
#  +---------------------------------+
#  |                                 |
#  |   Assembler Symbol Table Entry  |
#  |                                 |
#  +---------------------------------+
#

# Note: This object is defined here because of its dependence upon Section,
# Region and Img object definitions.
class LabelSymbol(asmbase.ASMSymEntry):
    def __init__(self,name,entry,length=None,T="U",S=0,I=0):
        super().__init__(name,entry,length=length,T=T,S=S,I=I)
        # Assembler XREF information
        self._defined=None       # source statement number defining the symbol
        self._refs=[]            # source statements referencing this symbol

        # Define attributes:
        if length is None:
            self["L"]=len(entry)
        else:
            self["L"]=length

    # Returns the underlying value that participates in computations
    def compute(self):
        obj=self._value
        if isinstance(obj,int):
            return obj
        if isinstance(obj,lnkbase.Address):
            # Instruction generation needs this for implied lengths
            obj.length=self["L"]
            return obj
        elif isinstance(obj,(Section,Region,Img)):
            addr=obj.loc
            addr.length=self["L"]  # Do we need this here???
            return addr

        raise ValueError("%s unexpected symbol table object '%s': %s" \
            % (eloc(self,"compute"),self.symbol,obj))

    # Add a reference to the symbol
    def reference(self,line):
        assert isinstance(line,int),\
            "%s 'line' argument must be an integer" % eloc(self,"reference")

        if not line in self._refs:
            self._refs.append(line)
            
            
#
#  +---------------+
#  |               |
#  |   A LITERAL   |
#  |               | 
#  +---------------+
#

# This class defines a single occurence of a literal within a pool
# Instance Argument:
#   asm    the global assembler.Assembler object
#   stmt   the ASMStmt object initially referencing the statement.
#   opnd   An asmline.LOperand object
#   ndx    The operand index of the literal in the initially referencing statement
# Note: this object is defined here because of its dependence upon the LabelSymbol
# object.
class Literal(LabelSymbol):
    def __init__(self,asm,stmt,opnd,ndx):
        assert isinstance(opnd,asmline.LOperand),\
            "%s 'opnd' argument must be an asmline.LOperand object: %s" \
                % (assembler.eloc(self,"__init__",module=this_module),opnd)

        self.length=0          # Actual constant length for group selection

        super().__init__(opnd.text,self,length=None,T="U",S=0,I=0)

        self.asm=asm           # The global assembler.Assembler object
        self.stmt=stmt         # Defining or referencing statment
        self.operand=opnd      # The logical operand on which this object is based
        self.stmt=stmt         # initial referencing statment
        self.ndx=ndx           # Operand index number in statement

        # The trace setting of the originating LTORG statement
        # Used to enable tracing of a asmstmts.LiteralStmt object
        self.trace=False       # See literal.LiteralPool.create() method

        self.reference(stmt.lineno)  # Remember the first reference

        # Professing state
        #   0 - instantiated
        #   1 - parsed            See parse() method
        #   2 - Pass 0            See Pass0() method
        #   3 - Pass 1            See Pass1() method
        #   4 - Placed in group   See literal.LiteralPool.create() method
        #   5 - Created
        self.state=0           # Sequential processing steps

        # See parse() method
        self.constant=None     # asmdcds.DCDS_Operand object

        # See Pass0() method
        self.unique=False      # Whether this literal is unique.

        # See Pass1() method
        self.length=None       # Actual constant length for group selection
        self.nominals=[]       # asmdcds.Nominal objects

        def __str__(self):
            return "[%s] LITERAL: operand %s: %s length=%s\n    constant: %s"\
                "\n    nominals: %s\n    loc: %s length: %s" \
                    % (self.stmt.lineno,self.ndx,self.operand,self.name,\
                        self.constant,self.nominals,self._value,self.length)

    def __len__(self):
        return self.length

    # Set the attributes.
    def attributes(self,loc,T="U",S=0,I=0):
        self._value=loc
        self["T"]=T
        self["S"]=S
        self["I"]=I

    # Make this object look like an expression for operand evaluation in Pass 2
    def evaluate(self,asm,debug=False,trace=False):
        val=self.compute()
        if __debug__:
            if debug:
                print("%s literal operand evalutates to: %s" \
                    % (eloc(self,"evaluate"),val))
        return val

    # Parse the literal constant
    def parse(self,debug=False):
        assert self.state==0,\
            "%s Literal.state not 0: %s" \
                % (assembler.eloc(self,"parse",module=this_module),self.state)

        try:
            scope=self.asm.PM.parse_constants(self.stmt,self.name[1:])
        except AsmParserError as ape:
            raise AssemblerError(line=self.stmt.lineno,\
                msg="literal operand %s invalid: %s" % (self.ndx+1,ape.msg)) from None

        operands=scope.operands
        if len(operands)>1:
            raise AssemblerError(line=self.stmt.lineno,\
                msg="literal operand %s has more than one constant type, found: %s"\
                    % (self.ndx+1,len(operands)))

        self.constant=operands[0]
        if __debug__:
            if debug:
                print("%s parsed constant: %s" \
                    % (eloc(self,"parse",module=this_module),self.constant))
        self.state=1

    def Pass0(self,debug=False):
        assert self.state==1,\
            "%s Literal.state not 1: %s" \
                % (eloc(self,"parse",module=this_module),self.state)
        assert isinstance(self.operand,asmbase.ASMString),\
            "%s Literal.operand not an asmbase.ASMSTring object: %s" \
                % (eloc(self,"parse",module=this_module),self.operand)

        self.constant.Pass0(\
            self.stmt,self.asm.PM,self.ndx+1,True,update=self.operand)
        self.unique=self.constant.unique   # Whether this is a unique literal
        if __debug__:
            if debug:
                print("%s parsed constant unique: %s" \
                    % (eloc(self,"Pass0",module=this_module),self.unique))
        self.state=2

    def Pass1(self,debug=False):
        assert self.state==2,\
            "%s Literal.state not 2: %s" \
                % (eloc(self,"parse",module=this_module),self.state)

        self.nominals=self.constant.Pass1(self.stmt,self.asm,debug=debug)
        if self.constant.dup == 0:
            raise AssemblerError(line=self.stmt.lineno,\
                msg="literal operand %s duplication factor must not be zero" \
                    % self.ndx+1)

        # Set the literal's actual length
        self.length=self.constant.act_len   # This selects the literal pool group
        self["L"]=self.length               # This is used for instruction length
        self.state=3

    def __str__(self):
        return "[%s] LITERAL: %s operand: %s" \
            % (self.stmt.lineno,self.name,self.operand)



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
        #self.source=[]       # Supplied by Assembler.statement() as received
        # This list is used strictly for reporting Pass 0 internal errors.  
        # Should it be just the current logical line?

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
    #def _statement(self,line):
    #    self.source.append(line)

    def errors(self):
        aes=sorted(self.aes,key=AssemblerError.sort)
        for ae in aes:
            print(ae)


#
#  +---------------------------------------+
#  |                                       |
#  |    STATEMENT PROCESSING CONTROLLER    |
#  |                                       |
#  +---------------------------------------+
#
#                                                        Next phase
#                                        Full Pass  
# Pass 0 - Phase 0 - input and parsing          Y    1         4      6           
# Pass 1 - Phase 1 - evaluation                 N        2     4  
#          Phase 2 - evaluation retry           N           3  4      6
#          Phase 3 - allocation                 Y              4      6                      
# Pass 2 - Phase 4 - object generation          N                 5   6
#          Phase 5 - object module creation     Y                     6
# Pass 3 - Phase 6 - Listing creation           Y                        7
#          Phase 7 - output creation            -

# Processing of statements involves a number of inter-dependencies:
#   1. Expressions can not be completed until all labels are defined as addresses
#   2. Space can not be allocated until all expressions are completed (DC/DS/EQU)
#   3. All labels can not be defined until all space is allocated:
#      DC/DS/EQU/Inst/CCW/PSWx/ORG
#   4. Position objects can not be converted to addresses until all space has
#      been allocated (LOCTR,CSECT)
#
# Here are the dependencies:
#      1     2    3     4
# Depends on:
#      4     1    2     2

# Label Definition and sizing process for object generating statements:
#    1.  Align statement within the current location counter (if required).  All
#        previous statements in the location counter must have been successfully 
#        aligned and sized.
#    2.  Assign the statement its position in the location counter.
#    3.  Define the unique label if required
#    4.  Evaluate size if needed then size the statement (DC/DS). If this fails
#        no more labels may be defined or statements positioned in this location 
#        counter.  This relates to DC/DS duplication and explicit lengths.
#        Mark retry=True
#
# Label Definition process for EQU statements
#    1.  Evaluate the expression.  If it fails mark retry=True, and undef=True
# Statement status:
#   retry  1   Whether an expression has an undefined symbol and needs evalutation
#              This occurs when LabelError is raised.  This is a definition issue
#   unaddr 4   Whether expression requires address (rather than Positions)
#              This occurs when PosArithError is raised which can only occur
#              after labels have been defined.  This is a sizing issue
#   undef  3   Whether a label needs to be defined by this statement
#   

class STMTProcessor(asmbase.ASMProcessor):
    def __init__(self,asm,depth=1):
        super().__init__(asm)
        self.infile=None        # Supplied by the run() method
        self.initial=True
        self.eprint=asm.eprint  # Immediately prints errors (--error 1)

        # Macro Builder
        self.MB=asmmacs.MacroBuilder(asm)

        # Manage input:
        self.IM=asmline.LineMgr(asm,self.MB,depth=depth,env="ASMPATH",\
            pathmgr=asm.asmpath)

        # Pass 0
        self.stmts=[]        # Populated by initial input pass
        self.lineno=1        # Global statement lineno assingments

        self.deferred=[]     
        self.cur_pass=None   # The current method handling this pass
        
    def init(self):
        self.defPhase("pass0_1",self.Pass0_1)
        self.defPhase("pass1_post",self.Pass1_Post)
        self.defPhase("pass2_pre",self.Pass2_Pre)
        self.defPhase("pass2",self.Pass2)
        self.defPhase("pass2_post",self.Pass2_Post)
        self.defPhase("fini",self.final)

    # Retrieves input until an exception occurs.
    # Exceptions:
    #   BufferEmpty  when all input has been consumed, signalling normal end of thie
    #                process.  This method should not be called again in this event
    #   MacroError   Occurs when an error in an invoked macro occurs or during
    #                macro definition.  The MacroError indicates which.  Macro
    #                invocation is really an input generating process.  The
    #                caller should handle the MacroError and then call this method
    #                resuming input.
    #   AssemblerError  When the assembler detects an error.  There error should
    #                be handled by the caller and input should continue.
    def getStmts0_1(self,asm,fail=False,debug=False):
        fail=asm.fail
        mb=self.MB
        while True:
            ln=self.IM.getLogical(debug=debug)
            # Create the ASMStmt subclass for the operation and populate it
            # with operation definition information.
            stmtcls=ln.optn.stmtcls
            if __debug__:
                if debug:
                #if True:
                    print("%s [%s] %s" % (eloc(self,"getStmts0_1"),self.lineno,ln))
                    print("%s [%s] Creating ASMStmt subclass: %s" \
                            % (eloc(self,"getStmts0_1"),self.lineno,\
                                stmtcls.__name__))
            # Create the asmbase.ASMStmt subclass for the operation
            asm.cur_stmt=s=stmtcls(self.lineno,ln)
            self.lineno+=1       # Increment global statement counter
            # Set the print status for this statement based upon the current
            # global settings and statement data.
            s.pr_set(on=asm.pon,gen=asm.pgen,data=asm.pdata,mcall=asm.mcall)

            # add the statement to our list of ASMStmt objects and pre-process.
            asm.stmts.append(s)
            # At the end of this process, the statement is queued for later 
            # assembly via the assemble() method.
            if isinstance(s,asmstmts.StmtError):
                # Raises an AssemblerError
                s.le_error()

            if s.ignore:
                # Empty lines and comments are skipped here
                continue

            macdefn=mb.defining(s,debug=False)
            # Did the Macro Language intercept the statement as part of a definition?
            if macdefn:
                s.ignore=True  # Intercepted, so no need to do anything more
                continue

            # WARNING: DO NOT set either argument debug or trace here
            s.Pass0(asm,macro=mb)

            if s.ignore:
                # Errors in Pass0() method skipped here
                continue

            # WARNING: DO NOT set either argument debug or trace here
            s.Pass1(asm)

    def Pass0_1(self,asm,fail=False,debug=False):
        Stats.start("pass1_p")
        Stats.start("pass1_w")
        
        debug=asm.dm.isdebug("stmt")
        while True:
            try:
                self.getStmts0_1(asm,fail=fail,debug=debug)
            except asmmacs.MacroError as me:
                # An error was detected in a macro invocation.
                # If we are failing immediately upon any detected error, 
                # do so now
                if asm.fail:
                    raise me from None
                # Not failing immediately, so we need to terminate the remainder
                # of the macro.
                ae=AssemblerError(line=me.line,linepos=me.linepos,msg=me.msg)
                if me.invoke:
                    # Invoked macro error
                    if self.eprint:
                        # Reporting errors when they occur, so output it now
                        print(ae)
                    # Queue it for ultimate output
                    asm.img._error(ae)
                    # The invoked macro has terminated, but continue reading input
                    # the the source that invoked the macro.
                else:
                    # Macro definition error handled as an assembler error of the
                    # current statement
                    asm._ae_excp(ae,self.cur_stmt,\
                        string=eloc(self,"Pass0_1"),debug=debug)
                asm.cur_stmt=None
                continue
            except AssemblerError as ae:
                if asm.fail:
                    raise ae from None
                asm._ae_excp(ae,asm.cur_stmt,\
                    string=eloc(self,"Pass0_1"),debug=debug)
                asm.cur_stmt=None
                continue
            except asminput.BufferEmpty:
                break

    def Pass1_Post(self,asm,fail=False,debug=False):
        ctrace=debug or asm._is_otrace("csect")
        rtrace=debug or asm._is_otrace("region")
        dtrace=debug or asm._is_otrace("dsect")
        
        # For an assembly that has created no sections or regions
        # This ensures the remainder of Pass 1 post processing succeeds.
        asm._check_cur_sec(debug=ctrace)
        
        # Place all of the CSECTS into their respective Regions, assigning
        # them an absolute starting address
        for r in asm.imgwip.elements:
            r.assign_all(debug=ctrace)

        # Make all of the self.loc relative adresses into absolute addresses and
        # do the same for equate symbols.
        for r in asm.imgwip.elements:
            r.make_absolute(debug=ctrace)
        for e in asm.equates:
            e.makeAbs()

        # Establish the physical location within the image of each region and CSECT
        asm.imgwip.locate_all(trace=rtrace)
        asm.imgwip.make_barray_all(trace=rtrace)

        # Update the symbol table attributes of the Regions and CSECTS with image
        # data.  The Assembler object is passed to provide assistance.
        asm.imgwip.updtAttr_all(asm,trace=rtrace)
        asm._image_new(asm.imgwip)   # Add the IMAGE to the symbol table
        for dsect in asm.dsects:
            dsect.make_barray_all(trace=rtrace)
            dsect.updtAttr(asm,trace=dtrace)

        Stats.stop("pass1_p")
        Stats.stop("pass1_w")

    def Pass2_Pre(self,asm,fail=False):
        Stats.start("pass2_p")
        Stats.start("pass2_w")

        # Reset the Location Counter
        asm.cur_loc=LocationCounter()
        asm.cur_loc.establish(lnkbase.AbsAddr(0))

    def Pass2(self,asm,fail=False,debug=False):
        for s in asm.stmts:
            if s.ignore:
                if __debug__:
                    if debug:
                        print("%s [%s] phase %s ignoring:\n    %s" 
                           % (eloc(self,"Pass2"),s.lineno,self.cur_phase,s))
                continue

            asm.cur_stmt=s   # Make current statement referencable globally

            asm._track_loc(s)

            if fail:
                # WARNING: DO NOT set either argument debug or trace here
                s.Pass2(asm)
            else:
                try:
                    # WARNING: DO NOT set either argument debug or trace here
                    s.Pass2(asm)
                except AssemblerError as ae:
                    asm._ae_excp(ae,s,string=eloc(self,"Pass2"),debug=False)

            asm.cur_loc.increment(s.content)
            asm.cur_stmt=None   # De-reference the current statement

    def Pass2_Post(self,asm,fail=False,debug=False):
        # Complete the image build
        asm.imgwip.insert(trace=debug)
        for dc in asm.dcs:
            dc.content.insert(trace=debug)
        Stats.stop("pass2_p")
        Stats.stop("pass2_w")

    def final(self,asm,fail=False,debug=False):
        Stats.start("output_p")
        Stats.start("output_w")
        asm._finish()    # Complete the Image before providing to listing generator
        asm.LM.create()  # Generate listing and place it in the final Image object
        Stats.stop("output_w")
        Stats.stop("output_p")
        
        Stats.stop("assemble_w")
        Stats.stop("assemble_p")
        Stats.stop("wall")
        Stats.stop("process")
        Stats.statements(len(asm.stmts))

        # Print statistics if requested here.

        if asm.stats:
            print(Stats.report())
            
        # Return to asma.py True to indicate successful execution
        return True

    # Runs the assembler.
    # Returns:
    #   True if successul run
    #   False if unsussessful run
    def run(self,asm,filename):
        assert isinstance(filename,str),\
            "%s 'filename' argument must be a string: %s" \
                % (eloc(self,"__init__"),filename)

        self.infile=filename
        try:
            self.IM.newFile(filename)
        except AssemblerError as ae:
            print(ae.msg)
            return False
        # Initialize initial file system variable symbols
        # This has to wait until the initial input file is found and opened
        asm.MM._init_gblc_file(self.IM.InputPath())
        return self.process()   # Return the result of last phase run


#
#  +-----------------------------------+
#  |                                   |
#  |   MACLIB PROCESSING CONTROLLER    |
#  |                                   |
#  +-----------------------------------+
#


# This statement processor manages implicit macro definitions triggered by
# source statements referencing a macro defined in a MACLIB directory.
# The file processing starts with by the run() method being called.  It may be
# serially reused for a new library file.  It is in essence a stripped down
# version of STMTProcessor with a single pass and phase.
#
# While the MACLIBProcessor and StmtProcessor are logically separate,
# MACLIBProcessor.run() is actually called, albeit quite indirectly, by
# STMTProcessor.run().  This is only significant for exceptions triggered during
# MACLIBProcessor.run() that do not get caught and propagate upward to
# STMTProcessor.run().  While this is highly unlikely generally, one exception
# in particular can have an interesting side effect, namely the BufferEmpty
# exception.  If it ends up not being caught by MACLIBProcessor, it will get caught
# by STMTProcessor and be interpreted as then end of the input processing for the
# entire assembly rather than just the end of input for the macro library file.
# The listing mysteriously quits.  For this reason the  closeSource() method is
# used to prematurely close the input source file when prematurely terminating
# the processing of the maclib file.  Mention is made of this purely for any
# future changes and something about which to be aware.
class MACLIBProcessor(asmbase.ASMProcessor):
    def __init__(self,asm,depth=1):
        super().__init__(asm)

        self.infile=None        # Supplied by the run() method
        self.eprint=asm.eprint  # Immediately prints errors (--error 1)

        # Macro Builder
        self.MB=asmmacs.MacroBuilder(asm)

        # Manage input:
        self.IM=asmline.LineMgr(asm,self.MB,depth=depth,env="MACLIB",\
            pathmgr=asm.macpath)

        # Supplied by run() method
        self.macro=None         # Macro name being defined from library
        self.infile=None        # Supplied by the run() method

    # The macro processor has a single "phase".  It reads the macro file looking
    # for a macro definition to define to the operation management framework.
    def init(self):
        self.defPhase("MACLIB",self.MacLib)

    # This method uses the directory list in the MACLIB environment variable to
    # determine if a macro definition (in reality a file of the same name) exists.
    # Note: Python requires the file to be opened, but because we are not actually
    # reading the definition, the file is immediately closed.
    def getAttr_O(self,macname):
        macnm=macname.upper()
        filename="%s.mac" % macnm
        try:
            path,fo=self.IM.LB._opath.ropen(filename,variable="MACLIB",debug=False)
        except ValueError:
            # File not found in search path or could not be opened.  Either way it
            # does not exist.
            return None

        fo.close()  # Just close the file, we don't actually read it
        return asmbase.ASMOper(macnm,None,O="S")

    # Retrieves input until an exception occurs.
    # Exceptions:
    #   BufferEmpty  when all input has been consumed, signalling normal end of thie
    #                process.  This method should not be called again in this event
    #   MacroError   Occurs when an error in an invoked macro occurs or during
    #                macro definition.  The MacroError indicates which.  Macro
    #                invocation is really an input generating process.  The
    #                caller should handle the MacroError and then call this method
    #                resuming input.
    #   AssemblerError  When the assembler detects an error.  There error should
    #                be handled by the caller and input should continue.
    def getStmts(self,asm,fail=False,debug=False):
        fail=asm.fail
        mb=self.MB
        while True:
            ln=self.IM.getLogical()
            # Create the ASMStmt subclass for the operation and populate it
            # with operation definition information.
            stmtcls=ln.optn.stmtcls
            if __debug__:
                if debug:
                    print("%s [%s] Creating ASMStmt subclass: %s" \
                            % (eloc(self,"getStmts"),self.lineno,\
                                stmtcls.__name__))
            # Create the asmbase.ASMStmt subclass for the operation
            s=stmtcls(self.lineno,ln)
            self.lineno+=1       # Increment global statement counter

            if isinstance(s,asmstmts.StmtError):
                raise AssemblerError(msg=s.error.msg)

            if s.ignore:
                # Empty lines and comments are skipped here
                continue

            macdefn=mb.defining(s,debug=False)
            # Was the statement intercepted as part of a macro definition?
            if macdefn:
                s.ignore=True  # Intercepted, so no need to do anything more
                continue

            # MACRO directives occur as open code, but they enter macro definition
            # mode.
            if isinstance(s,asmstmts.MACRO):
                s.Pass0(asm,macro=mb)  # Enter macro definition mode
                continue

            # Any other ppen code statement found in maclib file is an error
            raise AssemblerError(line=s.lineno,\
                msg="open code operation encountered in MACLIB file: %s" % s.instu)

    # Define macro found in the MACLIB
    def MacLib(self,asm,fail=False):
        assert self.MB.indefn is None,\
            "%s macro '%s' definition in progress can not define a macro "\
                "from maclib" % (eloc(self,MacLib),asm.MM.indefn)

        debug=asm.dm.isdebug("stmt")
        result=None
        while True:
            try:
                self.getStmts(asm,fail=fail,debug=debug)
            except asmmacs.MacroError as me:
                # An error was detected in a macro invocation.
                # If we are failing immediately upon any detected error, 
                # do so now
                if asm.fail:
                    raise me
                # Not failing immediately, so we need to terminate the remainder
                # of the macro.
                if me.invoke:
                    # THIS SHOULD NEVER HAPPEN HERE
                    raise NotImplementedError(\
                        "%s MacroError during a macro invocation should not occur "\
                        "while a library macro is being defined" \
                            % eloc(self,"MacLib"))
                else:
                    # Macro definition error handled as an assembler error of the
                    # current statement
                    result=asmline.LineError(\
                        source="[%s]-%s" % (self.macro,self.lineno),\
                        msg=me.msg,maclib=True)
                self.IM.LB.closeSource()  # without BufferEmpty being triggered
                break
            except AssemblerError as ae:
                if asm.fail:
                    raise ae from None
                # Convert the error into a LineError for handling by the asmline
                # module.  The asmline module triggers this processor when it tries
                # to identify an operation only to find it undefined.  The asmoper
                # module then calls this module's run() method to define it.
                # By treating the error as a LineError, we can ultimately get the
                # error reported with the original input line.
                result=asmline.LineError(\
                    source="[%s]-%s" % (self.macro,self.lineno),\
                    msg=ae.msg,maclib=True)
                self.IM.LB.closeSource()  # without BufferEmpty being triggered
                break
            except asminput.BufferEmpty:
                # Note: the source file is already closed if this exception is raised
                if self.MB.state!=0:
                    result=asmline.LineError(\
                        source="[%s]-%s" % (self.macro,self.lineno),\
                        msg="end-of-file encountered before MEND",maclib=True)
                break

        return result

    # Define the macro or macros in a macro library file
    # Exception:
    #   asmline.LineError if a macro definition fails.
    def run(self,asm,macname):
        assert isinstance(macname,str),\
            "%s 'filename' argument must be a string: %s" \
                % (eloc(self,"__init__"),filename)
        self.macro=macname.upper()
        self.infile="%s.mac" % self.macro
        self.lineno=1
        #print("%s opening macro library file: %s" % (eloc(self,"run"),self.infile))
        self.IM.newFile(self.infile)

        # Process the MACLIB file
        result=self.process()
        #print("%s MACLIB result: %s" % (eloc(self,run),result))
        if isinstance(result,asmline.LineError):
            raise result
        return result


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
