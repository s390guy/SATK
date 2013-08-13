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

# This module provides configuration support for the CPTK software provided in
# the src/cp directory.  It uses the language tools to parse configuration
# statements.
#
# Statements are free form.  Standard comments (starting with a '#') are allowed
# Minimal input requires a SYSTEM statement.
# 

copyright_years="2013"

# Python imports:
import argparse
import os
import sys

# SATK imports:
import satkutil
satkutil.pythonpath("tools/lang")   # Dynamically add language tools to PYTHONPATH
from langutil import *

# The key-word language processor for CP configuration
class CPCFG(KWLang):
    def __init__(self,dm):
        super().__init__()
        self.dm=dm
        tdebug=self.dm.isdebug("tdebug")
      
        # Define statements
        self.token(WordType("SYSTEM",words="M:system",debug=tdebug))
        # Define keywords
        self.token(WordType("ARCH",words="M:arch",debug=tdebug))
        self.token(WordType("TYPE",words="M:type",debug=tdebug))
        # Define keyword arguments
        self.token(WordType("ARCHS",\
            words=["S/370BC","S/370","ESA/390","z/Architecture"],debug=tdebug))
        self.token(WordType("SYSTYPE",\
            words=["M:IPL","M:CP"],case="upper",debug=tdebug))
        # This token must be here
        self.token(NamType("NAME",debug=tdebug))

        # The following statements reference the tokens defined above

        # Define SYSTEM statement
        sys=KWDef("SYSTEM",required=True)
        sys.positional("NAME")
        sys.keyword(KWKeyWord("ARCH",arguments="ARCHS"))    # required
        sys.keyword(KWKeyWord("TYPE",arguments="SYSTYPE"))  # required
        self.statement(sys)

        self.init_lang(dm=self.dm)

# The language processing tools requires a wrapper that handles various roles.
#   1. Accessing the text to be processed by the language tools
#   2. Instantiating the tools for use
#   3. Driving the processing by the tools
#   4. Handling the back end processing of resulting AST
# The CPCONFIG class provides the user interface for use of the configuration 
# language parser and creating its output config.S text file.
class CPCONFIG(object):
    def __init__(self,args,dm):
        self.args=args      # argparse arguments
        self.dm=dm          # Debug Manager
        self.dm.init(args)  # Enable debugging
        self.cfgtext=""     # Input configuration file text string
        self.statements=[]  # List of recognized statements, KWStatement instance

        self.kwlang=CPCFG(dm=self.dm)

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
        self.error("CPCONFIG__try_step",type="",message="%s%s" % (message,plural))
        return False
     
    # Report an error to the error manager for later reporting
    def error(self,source,type="C",token=None,message=""):
        self.kwlang.semerror(source,type=type,token=token,message=message)
        
    # This method reads the configuration text file.
    def file_read(self,path,mode="rt"):
        try:
            fo=open(path,mode="rt")
        except IOError:
            print("cpconfig.py - Could not open for reading text file: '%s'" % path)
            sys.exit(2)
        try:
            fdata=fo.read()   # Read the entire file
        except KeyError:
            print("cpconfig.py - Could not read file: '%s'" % path)
            sys.exit(2)
        try:
            fo.close()
        except IOError:
            print("cpconfig.py - Could not close file: '%s'" % path)
            sys.exit(2)
        return fdata
        
    # This method generates utility output
    def output(self): 
        print("CPCONFIG.output() called")
        
    # This method drives the cpconfig.py utility processing
    def run(self):
        self.cfgtext=self.file_read(self.args.cfgfile[0],mode="rt")
        self.statements=self.kwlang.analyze(self.cfgtext,\
            sdebug=self.dm.isdebug("sdebug"))
        if self.args.print:
            for x in statements:
                print("%s" % x)

        msg="cpconfig.py - statement processing suppressed due to error"
        next=self.__try_step(self.process,msg,flag=self.args.ignore)

        if next:
            msg="cpconfig.py - output creation suppressed due to error"
            self.__try_step(self.output,msg,flag=self.args.force)

        self.kwlang.report()
        
    # This method processes successfully recognized statements
    def process(self):
        print("CPCONFIG.process() called")

def parse_args(dm):
    parser=argparse.ArgumentParser(prog="cpconfig.py",
        epilog="cpconfig.py Copyright (C) %s Harold Grovesteen" % copyright_years, 
        description="configures a control program")
    parser.add_argument("cfgfile",\
        help="configuration source text file",nargs=1)
        # Note: cfgfile is a list.  Use cfgfile[0] to extract the filename
    parser.add_argument("-f","--force",action="store_true",default=False,
        help="force output creation even if statement processing encountered "
             "errors")
    parser.add_argument("-i","--ignore",action="store_true",default=False,
        help="process statements regardless of intput text errors encountered")
    parser.add_argument("-t","--target",default=os.getcwd(),
        help="target directory, defaults to current working directory")
    parser.add_argument("--print",action="store_true",default=False,
        help="display recognized statements")
    # Add debug argument using the debug manager
    dm.add_argument(parser)
    return parser.parse_args()   

if __name__ == "__main__":
    dm=satkutil.DM(cmdline="debug",appl=["sdebug"],langutil=True)
    CPCONFIG(parse_args(dm),dm).run()