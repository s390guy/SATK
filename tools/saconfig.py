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

# This module provides configuration support for SATK.  It will configure and 
# create build scripts for a single stand-alone program incorporating ultimately
# support for the emerging micro-kernel in src/cp.
#
# For now all of the documentation will be in this module in the following
# comments.  A separate manual may ultimately be created.
#
# +------------+
# |  Overview  |
# +------------+
#
# saconfig.py uses three methods of input: environmnet variables, command-line
# arguments and a configuration file containing statements recognized by the
# saconfig.py utility.  The utility will output a script that will build stand-
# alone programs using the SATK conventions and facilities and generate other
# files related to creation of the micro-kernel.
#
# The utility requires knowledge of the locations of:
#   - the SATK root directory,
#   - the directory in which the cross-compiler tools are built and version
#     information,
#   - various run-time input directories used in creating a program and
#   - various output-directories used in creating the stand-alone program.

# +-------------------------+
# |  Environment Variables  |
# +-------------------------+
#
#  The following environment variables are used.  Each defines a required location
#  that may be supplied by a command-line override value.
#
#  $HOME     absolute path to the "home" directory.  Corresponding command-line
#            argument is '--home'.
#  $XTOOLS   The directory in which the cross-compiler executables reside.  
#            Corresponding command-line argument is '--xtools'.  If neiter are
#            present it defaults to '$HOME/crossbuild/run/bin'.
#  $SATK     The location of the SATK root directory.  It defaults to that derived
#            by the satkutil.satkroot() function.  Corresponding command-line
#            argument is '--satk'.
#  $BUILD    The directory in which the program is built.

# +----------------------+
# |  Command Line usage  |
# +----------------------+

# +----------------------------------------+
# |  Configuration Statement Descriptions  |
# +----------------------------------------+
#
# Statements are free form.  Standard comments (starting with a '#') are allowed.
# Minimal input requires a SYSTEM statement. 

copyright_years="2013"

# Python imports:
import argparse
import os
import sys

# SATK imports:
import satkutil
satkutil.pythonpath("tools/lang")   # Dynamically add language tools to PYTHONPATH
from langutil import *

# The key-word language processor for SA configuration
class SACFG(KWLang):
    def __init__(self,dm,case="M",recovery=False):
        super().__init__()      # Override required TID names here if needed
        self.dm=dm              # The global debug manager
        outcase="upper"         # Reserved word converted to uppercase
        
        # Define the Keyword Language
        tdebug=self.dm.isdebug("tdebug")
      
        defn=self.begin(ptrace=False)
        defn.opt(WordType("ARCHS",\
            words=["S/370BC","S/370","ESA/390","z/Architecture"],\
            case=outcase,debug=tdebug))
        defn.opt(NamType("NAME"))
        defn.opt(StrType("DSTR",quotes="d"))
        la=defn.la
        
        # SYSTEM <name> ARCH=<archs> type=[IPL|CP]
        sys=Stmt("system",la,required=True)
        sys.pos("name")
        sys.keyword("arch",val=["ARCHS",],required=True)
        sys.keyword("type",val=["IPL","CP"])
        defn.add(sys)
        
        # SCRIPT <name> SUFFIX="string"
        script=Stmt("script",la)
        script.pos("name")
        script.keyword("suffix",val="dstr")
        defn.add(script)

        self.init_lang(dm=self.dm,recovery=recovery,incase=case,outcase="upper")

# The language processing tools requires a wrapper that handles various roles.
#   1. Accessing the text to be processed by the language tools
#   2. Instantiating the tools for use
#   3. Driving the processing by the tools
#   4. Handling the back end processing of resulting AST
# The SACONFIG class provides the user interface for use of the configuration 
# language parser and creating its output config.S text file.
class SACONFIG(object):
    def __init__(self,args,dm):
        self.args=args      # argparse arguments
        self.dm=dm          # Debug Manager
        self.dm.init(args)  # Enable debugging
        self.cfgtext=""     # Input configuration file text string
        self.statements=[]  # List of recognized statements, KWStatement instance

        self.kwlang=SACFG(dm=self.dm,\
                          case=self.args.case,\
                          recovery=self.args.recovery)

    # This method checks for errors and override flags for a step
    # Returns true if next step should be attempted, False otherwise
    # (If we did not do this step, then we should not attempt the next one)
    def __try_step(self,method,message,flag=False):
        errors=self.kwlang.errors()
        if ( not errors ) or flag:
            method()
            return True
        plural=""
        if errors>1:
            plural="s"
        self.error("_SACONFIG__try_step",type="",message="%s%s" % (message,plural))
        return False
     
    # Report an error to the error manager for later reporting
    def error(self,source,type="C",token=None,message=""):
        self.kwlang.semerror(source,type=type,token=token,message=message)
        
    # This method reads the configuration text file.
    def file_read(self,path,mode="rt"):
        try:
            fo=open(path,mode="rt")
        except IOError:
            print("saconfig.py - Could not open for reading text file: '%s'" % path)
            sys.exit(2)
        try:
            fdata=fo.read()   # Read the entire file
        except KeyError:
            print("saconfig.py - Could not read file: '%s'" % path)
            sys.exit(2)
        try:
            fo.close()
        except IOError:
            print("saconfig.py - Could not close file: '%s'" % path)
            sys.exit(2)
        return fdata
        
    # This method generates utility output
    def output(self): 
        print("SACONFIG.output() called")
        
    # This method drives the saconfig.py utility processing
    def run(self):
        self.cfgtext=self.file_read(self.args.cfgfile[0],mode="rt")

        if self.args.recovery:
            abort=None
        else:
            abort=2
            
        # Parse and build statement instances
        self.statements=self.kwlang.analyze(self.cfgtext,\
            sdebug=self.dm.isdebug("sdebug"),abort=abort)
        
        if self.args.print:
            print("saconfig.py - SACONFIG.run() - Statement objects returned: %s" \
                % len(self.statements))
            for x in self.statements:
                print("%s" % x.print())

        msg="saconfig.py - statement processing suppressed due to error"
        next=self.__try_step(self.process,msg,flag=self.args.ignore)

        if next:
            msg="saconfig.py - output creation suppressed due to error"
            self.__try_step(self.output,msg,flag=self.args.force)

        self.kwlang.report()
        
    # This method processes successfully recognized statements
    def process(self):
        print("SACONFIG.process() called")

def parse_args(dm):
    parser=argparse.ArgumentParser(prog="saconfig.py",
        epilog="saconfig.py Copyright (C) %s Harold Grovesteen" % copyright_years, 
        description="configures a control program")
    parser.add_argument("cfgfile",\
        help="configuration source text file",nargs=1)
        # Note: cfgfile is a list.  Use cfgfile[0] to extract the filename
    parser.add_argument("-c","--case",choices=["M","L","U","E"],default="M",
        help="reserved word input text case: mixed (M), only upper (U), "
             "only lower (L), or either (E) upper or lower")
    parser.add_argument("-f","--force",action="store_true",default=False,
        help="force output creation regardless of input text semantic errors")
    parser.add_argument("-i","--ignore",action="store_true",default=False,
        help="process statements regardless of input text semantic errors")
    parser.add_argument("-r","--recovery",action="store_true",default=False,
        help="attempt to recover from parsing errors, otherwise terminate parsing "
             "immediately upon detecting an error")
    parser.add_argument("-t","--target",default=os.getcwd(),
        help="target directory, defaults to current working directory")
    parser.add_argument("--print",action="store_true",default=False,
        help="display recognized statements as seen by the processor")
    parser.add_argument("--satk",default=False,
        help="Stand-alone Toolkit root directory overriding 'SATK' environment "
             "variable")
    parser.add_argument("--xtools",default=False,
        help="Directory where compiler toolchain executables reside overriding "
             "'XTOOLS' environment variable.  Defaults to "
             "'$HOME/crossbuild/run/bin' if neither are available")
    # Add debug argument(s) using the debug manager
    dm.add_argument(parser)
    return parser.parse_args()   

dm=satkutil.DM(cmdline="debug",appl=["bdebug","sdebug"],langutil=True)

if __name__ == "__main__":
    #print("$HOME='%s'" % os.environ["HOME"])
    #print("$HOME/SATK='%s'" % os.path.expandvars("$HOME/SATK"))
    #os.environ["HOME"]="other"
    #print("$HOME/SATK='%s'" % os.path.expandvars("$HOME/SATK"))
    SACONFIG(parse_args(dm),dm).run()
