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

# Python imports:
import argparse
import sys

# SATK imports:
import satkutil
satkutil.pythonpath("tools/lang")   # Dynamically add language tools to PYTHONPATH
from langutil import *

copyright_years="2013"

# The key-word language processor for CP configuration
class CPCFG(KWLang):
    def __init__(self,debug=False,cbdebug=False,edebug=False,gdebug=False,
                 kdebug=False,tdebug=False):
        super().__init__()
      
        self.token(WordType("ARCH",words="M:arch",debug=tdebug))
        self.token(WordType("ARCHS",\
            words=["S/370BC","S/370","ESA/390","z/Architecture"],debug=tdebug))
        self.token(WordType("SYSTEM",words="M:system",debug=tdebug))
        self.token(NamType("NAME",debug=tdebug))

        # The following statements reference the tokens defined above

        # Define SYSTEM statement
        sys=KWDef("SYSTEM",required=True)
        sys.positional("NAME")
        sys.keyword(KWKeyWord("ARCH",arguments="ARCHS"))
        self.statement(sys)

        self.init_lang(debug=debug,cbdebug=cbdebug,edebug=edebug,gdebug=gdebug,
            kdebug=kdebug,tdebug=tdebug)

# The language processing tools requires a wrapper that handles various roles.
#   1. Accessing the text to be processed by the language tools
#   2. Instantiating the tools for use
#   3. Driving the processing by the tools
#   4. Handling the back end processing of resulting AST
# The CPCONFIG class provides the user interface for use of the configuration 
# language parser and creating its output config.S text file.
class CPCONFIG(object):
    def __init__(self,args):
        self.args=args
        self.cfgtext=""   # Input configuration file text string
        
        self.kwlang=CPCFG(debug=self.args.debug,
                          cbdebug=self.args.cbdebug,
                          edebug=self.args.edebug,
                          gdebug=self.args.gdebug,
                          kdebug=self.args.kdebug,
                          tdebug=self.args.tdebug)
        
    # This method checks for errors and override flags for a step
    # Returns true if next step should be attempted, False otherwise
    # (If we did not do this step, then we should not attempt the next one)
    def __try_step(self,method,flag,message):
        errors=self.kwlang.errors()
        if ( not errors ) or flag:
            method()
            return True
        plural=""
        if errors>1:
            plural="s"
        self.error(message="%s%s" % (message,plural))
        return False
     
    # Report an error to the error manager for later reporting
    def error(self,token=None,message=""):
        self.kwlang.semerror("CPCONFIG.error",type="C",token=token,message=message)
        
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
        statements=self.kwlang.analyze(self.cfgtext,sdebug=self.args.sdebug)
        if self.args.print:
            for x in statements:
                print("%s" % x)

        msg="cpconfig.py - statement processing suppressed due to error"
        next=self.__try_step(self.process,self.args.ignore,msg)

        if next:
            msg="cpconfig.py - output creation suppressed due to error"
            self.__try_step(self.output,self.args.force,msg)

        self.kwlang.report()
        
    # This method processes successfully recognized statements
    def process(self):
        print("CPCONFIG.process() called")

def parse_args():
    parser=argparse.ArgumentParser(prog="cpconfig.py",
        epilog="cpconfig.py Copyright (C) %s Harold Grovesteen" % copyright_years, 
        description="configures a control program")
    parser.add_argument("cfgfile",\
        help="configuration source text file",nargs=1)
    # Note: cfgfile is a list.  Use cfgfile[0] to extract the filename
    parser.add_argument("-c","--cbdebug",action="store_true",default=False,
        help="enable config language processor callback debugging")
    parser.add_argument("-f","--force",action="store_true",default=False,
        help="force output creation even if statement processing encountered errors")
    parser.add_argument("-i","--ignore",action="store_true",default=False,
        help="process statements regardless of intput text errors encountered")
    parser.add_argument("-d","--debug",action="store_true",default=False,
        help="enable config language debugging")
    parser.add_argument("-e","--edebug",action="store_true",default=False,
        help="enable error debugging")
    parser.add_argument("-g","--gdebug",action="store_true",default=False,
        help="enable grammar debugging")
    parser.add_argument("-k","--kdebug",action="store_true",default=False,
        help="enable keyword language debugging")
    parser.add_argument("-p","--print",action="store_true",default=False,
        help="display recognized statements")
    parser.add_argument("-s","--sdebug",action="store_true",default=False,
        help="enable token stream debugging")
    parser.add_argument("-t","--tdebug",action="store_true",default=False,
        help="enable token debugging")
    return parser.parse_args()   

if __name__ == "__main__":
    CPCONFIG(parse_args()).run()