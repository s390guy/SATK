#!/usr/bin/python3
# Copyright (C) 2015 Harold Grovesteen
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

# The primary purpose of this module is the creation of a standard approach to
# invoking SATK tools with command-line options and/or environment variables.  Both
# may be defined within a configuration file.  This module ultimately creates
# an argparser.parser (for command line argument parsing) and a 
# configparser.ConfigParser object (for configuration file parsing).  The base classes
# provide the interface to these object.s.  From the perspective of a specific
# tool, this module results in a configuration object similar to the argparser
# Namespace object.
#
# This module integrates the use of command-line options in combination with a
# set of configuration files.  Explicit command-line options always take precedence 
# over options supplied by a configuration file.  Explicit environment variables
# always have precedence over the values supplied by a configuration file.  
# Use of subclasses are expected for the purpose of integrating configuration file 
# information with command line information.  This module provides the framework for
# a specific tool's usage of options.  While managing the configuration system, this
# tool, config.py, also uses the configuration system.
#
# SATK tools that utilize configuration files use the following common strategy:
#
# Configuration information resides in a configuration root directory.  This
# directory's location is defined by either an environment variable, SATKCFG, or
# a key within a site.cfg configuration file residing in the SATK config directory.
# If neither are present, tool usage will require environment variables and command
# explicit command line options or command-line defaults.
#
# Within the configuration root directory, three types of configuration files are
# expected:
#
#   - a general satk.cfg configuration file and
#   - tool default configurations.
#
# Additional tool configurations may be established and selected by a tool's --cfg
# command-line argument.  This command-line argument defaults to the tool's default
# configuration.  Tool configuration files may contain sections that explicitly
# select environment and command line options for the specific input target.  The
# satk.cfg configuration file contains the key pointing to the tool configuration's
# location.  Tool configuration files may contain other sections useful to the
# target sections, for example search order paths and interpolation information as
# the user finds useful.

this_module="config.py"
# Note: __name__ can not be used because is distorts the name to '__main__.py'
# when the module is invoked as a script as opposed to when it is imported.
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2015")


# Python imports:
import sys
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))

import argparse     # Python command-line parser utility
import configparser # Python configuration file parser
import os.path      # Manipulate platform paths
import time         # Access date and time for run-time default options
#from collections import OrderedDict  # Dictionary used by the configparser module
# SATK imports
import satkutil     # Various utilities

# This method returns a standard identification of an error's location.
#
# It results in a string of:
#    'module.py - class_name.method_name() - '
# The results is normally used to populate a string:
#   "%s error information goes here" % eloc(self,"method_name")
def eloc(clso,method_name,module=None):
    if module is None:
        m=this_module
    else:
        m=module
    return "%s - %s.%s() -" % (m,clso.__class__.__name__,method_name)


#
#  +-------------------------------+
#  |                               |
#  |    Configuration Exception    |
#  |                               | 
#  +-------------------------------+
#

class ConfigError(Exception):
    def __init__(self,msg=""):
        self.msg=msg         # Text associated with the error
        super().__init__(self.msg)


#
#  +------------------------------------+
#  |                                    |
#  |    Configuration File Framework    |
#  |                                    | 
#  +------------------------------------+
#

# Provides the interface to configuration files via the Python configparser module.
#
# Instance Arguements:
#   parms     A Configuration object defining the options available to the 
#             configuration system.
#   defaults  An optional dictionary that defines run-time supplied configuration
#             file default values.
#   debug     Whether debug messages should be generated.
class ConfigFile(object):
    def __init__(self,parms,defaults={},debug=False):
        assert isinstance(parms,Configuration),\
            "%s 'parms' argument must be a Configuration object: %s" \
                % (eloc(self,"__init__"),parms)

        self.parms=parms  # Configuration object used by tool
        self.debug=debug  # Whether debug messages are enabled.
        
        # List of configuration files used by the tool
        self.files=[]

        # Option/Value delimiters: = :
        # Comment line prefixes: #  ;
        # Inline comments: #
        self.parser=configparser.ConfigParser(\
            delimiters=("=",":"),\
            comment_prefixes=("#",";"),\
            inline_comment_prefixes=("#"),\
            interpolation=configparser.ExtendedInterpolation(),\
            defaults=defaults)

        # List of available sections, updated after each config file is read
        self.sections=[]      # See read_cfg() method
        self.missing=[]       # Requested section but missing
        
        # Current default setting after reading a new config file
        self.defaults=self.defaults()   # Also, see read_cfg() method
        
        # Whether the configuration system is disabled (meaning it can't find
        # the site)
        #self.config_disabled=False

    # Return the defined configuration defaults
    def defaults(self):
        defaults=self.parser.defaults()
        return defaults

    def display(self,indent="",raw=False,string=False):
        self.defaults()
        #sections=self.parser.sections()
        for s in self.sections:
            self.section(s,raw=raw)

    # Retrieves an option from a section.
    #
    # Method Arguments:
    #   section   The section from which the value is retrieved
    #   option    The option being retrieved
    #   split     Whether the option is to be splic into a list of strings or
    #             returned as a sinlge string (with possible spaces and newlines).
    #             Specify True to split the string.  Specify False to return the
    #             entire string.  Defaults to False.
    #   raw       Whether interpolation is to be performed on the option string
    #             by the parser.  Defaults to True.
    # Returns:
    #   Option's value as a single string
    # Exception:
    #   KeyError if either the section or option does not exist in the configuration
    def option(self,section,option,raw=False):
        opt=option.lower()
        optv=None
        try:
            optv=self.parser.get(section,opt,raw=raw)
            # If the option is not found in the section but a default value
            # in the configuration system is available, it will be returned
            # by the parser.
        except configparser.NoOptionError:
            pass
            #print("error: option not found: %s" % opt)
            
        except configparser.NoSectionError:
            # Remember that the section is missing
            if not section in self.missing:
                self.missing.append(section)

        # Access defaults anyway
        if optv is None:
           optv=self.defaults.get(opt)  # If option is not in defaults returns None
        
        if __debug__:
            if self.debug:
                print("%s section:%s  option:%s = %s" \
                    % (eloc(self,"option"),section,option,optv))
        return optv

    # Updates the configuration information with tool defaults and any user
    # sections contained in the file.
    # Method Argument:
    #   dtfcfg  The TextFile object associated with the default tool config file
    def parse_defaults(self,dftcfg):
        assert isinstance(dftcfg,TextFile),\
            "%s 'dftcfg' argument must be a TextFile object: %s" \
                % (eloc(self,"parse_defaults"),dftcfg)
    
        # If the path is not a file or an absolute path, ignore it
        if dftcfg.ftype != "FA":
            print("WARNING: tool configuration file does not exist: %s"\
                % dftcfg.filepath)
            return
        self.read_cfg(dftcfg.filepath)

    # Updates the configuration system information from the site.cfg file
    # Method Arguments:
    #   satkdir   root SATK directory
    def parse_satk(self,satkcfg,verbose=False):
        assert isinstance(satkcfg,TextFile),\
            "%s 'satkcfg' argument must be a TextFile object: %s" \
                % (eloc(self,"parse_site"),satkcfg)

        return self.read_cfg(satkcfg.filepath)

    # Updates the configuration system information from the --cfg configuration file
    # Method Arguments:
    #   srccfg   TextFile object associated with the source config file
    def parse_source(self,srccfg):
        assert isinstance(srccfg,TextFile),\
            "%s 'srccfg' argument must be a TextFile object: %s" \
                % (eloc(self,"parse_defaults"),srccfg)
    
        # If the path is not a file or an absolute path, ignore it
        if srccfg.ftype != "FA":
            print("WARNING: user configuration file does not exist: %s"\
                % srccfg.filepath)
            return
        self.read_cfg(srccfg.filepath)

    # Read a configuration file, updating the parsed configuration.
    #
    # Note: The configparser.ConfigParser object may be in an unknown state and 
    # unreliable for access if a parser exception occurs during reading of the file.  
    # Therefore, an error within the file always terminates the tool.
    #
    # Method Arguments:
    #   filename   configuration file being read
    #   trace      Whether to trace file read activity with a message
    # Returns:
    #   True       If the file has been successfully opened and read
    #   False      If the file could not be opened.
    def read_cfg(self,filename,verbose=False):
        # Open the configuration file
        try:
            fo=open(filename)
            if verbose:
                print("INFO: reading configuration file: %s" % filname)
        except IOError as e:
            if verbose:
                print("CONFIGURATION FILE ERROR: %s" % e)
            return False

        # Read and interpret contents
        try:
            self.parser.read_file(fo)
        except configparser.Error as e:
            print("CONFIGURATION ERROR: %s" % e)
            fo.close()
            sys.exit(1)
        fo.close()
        self.sections=self.parser.sections()
        self.defaults=self.parser.defaults()
        self.files.append(filename)   # Add the config file to the list
        return True

    # Display the contents of a section.
    def section(self,sect,raw=False):
        options=self.parser.options(sect)
        # options includes section options and global defaults
        print("Section: %s" % (sect))
        for opt in options:
            # ignore default options is method argument raw=False
            if not raw and opt in self._defaults:
                continue
            v=self.parser.get(sect,opt,raw=raw)
            # Multiline and multiple values for an option are included as
            # a single string with spaces and new lines.  This logic separates
            # them into individual strings in a list.  Configuration option
            # processing must be sensitive to this handling of option values by
            # the parser
            nonl=v.split("\n")
            split=[]
            for s in nonl:
                split.extend(s.split())
            print("    %s = %s" % (opt,split))

  #
  #  Methods supplied by subclass
  #

    # Read and process the configuration file, updating the configuration parameters
    # This method must call self.recognize() with the filename to cause the
    # superclass to read and process the configuration file.  It must then
    # use the getStmts() method to retrieve the list of statements and update 
    # self.parms with the configuration argument values by calling the appropriate
    # Argument object's cfg method.
    def populate(self,filename):
        raise NotImplementedError("%s subclass %s must supply populate() method" \
            % (eloc(self,"popultate"),self.__class__.__name__))


#
#  +----------------------------------------+
#  |                                        |
#  |    Tool Configuration Specification    |
#  |                                        | 
#  +----------------------------------------+
#


# This is the base class for defining a command-line argument and/or a configuration
# file options.
#
# Instance Arguments:
#
# Generic option instance arguments
#   name     A string by which the argument is identified to the configuration system.
#   default  The default value as used globally
#   required Whether the configuration system requires the argument from some source
#   choices  The valid choises for the argument.
#   cl       Whether the option is used in the command-line
#   cfg      Whether the option is used in a configuration file
#   env      Whether the option is used by environment variables.  If a string 
#            is specified, the string in upper case overrides the name argument.
#   site     Whether the option is defined by the site.cfg file
#
# Command-line related instance arguments
#   short    The short version of the command line argument (without leading hyphen)
#   full     The long version of the command line argument (without double hyphens)
#   metavar  How the argparser.parser displays the argument value.
#   action   argument action performed by parser
#   help     Command-line help for option
#
# Configuration file related instance arguments
#   novalue  Whether no value is allowed for the option.  Defaults to False
class Option(object):
    
    # Method to check for configuration file option coded withou a value.
    #
    # Note: None is treated as a value in this context.  It usually results when
    # the option is coded no where (neither a default nor explicit).
    #
    # Returns:
    #   True  this is a 'no value' option
    #   False option has a value
    @staticmethod
    def isNoValue(value):
        return isinstance(value,str) and len(value)==0

    # Method to provide option sort key
    @staticmethod
    def sort(option):
        return option.name.lower()

    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,action=None,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        if __debug__:
            if cl:
                assert full is not None or short is not None,\
                    "%s either argument 'short' or 'full' may be None, but "\
                         "not both: %s" % (eloc(self,"__init__"),name)
                assert isinstance(help,str) or help is None,\
                     "%s 'help' argument must be a string: %s" \
                         % (eloc(self,"__init__"),help)

        # General configuration systme option information
        self.name=name     # Name of option as known by the configuration system
        # Whether debug message to be displayed.
        self.debug=False   # Enabled by Tool.populate() method.

        # General definitional information
        self.required=required # Whether the argument is required somewhere
        self.default=default   # Default value if not present from any source
        self.choices=choices   # Valid choices for the option

        # Definitional information argparser
        self.use_cl=cl         # Whether the option is a command-line option
        self.short=short       # Short name of command line option
        self.full=full         # Long name of command line option
        self.action=action     # command-line parser action for argument
        self.metavar=metavar   # METAVAR used by argparser.
        self.help=help         # command-line help information

        # Definitional information for configparser
        self.use_cfg=cfg   # Whether the option is a configuration option

        # Definitional information for environment variables
        self.use_env=False     # Whether the option is an environment variable option
        self.env_name=None     # Environment variable name used to access
        if isinstance(env,str):
            self.env_name=env.upper()
            self.use_env=True
        elif env:
            self.env_name=name.upper()
            self.use_env=True

        # Whether command line reflects it being required _in the command-line_.
        self.clreq= self.required and self.use_cl \
                    and (not self.use_cfg) and (not self.use_env)

        # Populated information from sources
        self.typ="?"       # Source of populated information
        self._cl=None          # Argument from command line
        self._cfg=None         # Argument from configuration
        self._env=None         # Argument from environment variables
        self.value=None        # Value (command-line, config-file, default)
        self.error=False       # Set to True if the option is in error.

    def __str__(self):
        string="%s %s %s=%s cl:%s=%s cfg:%s=%s env:%s=%s req: %s default: %s" % (\
            self.__class__.__name__,\
            self.typ,self.name,self.value,\
            self.use_cl,self._cl,\
            self.use_cfg,self._cfg,\
            self.use_env,self._env,\
            self.required,\
            self.default)
        return string

    # Display option choice error message
    def choice_error(self,value):
        ch=""
        for choice in self.choices:
            ch="%s,'%s'" % (ch,choice)
        ch=ch[1:]  # Forget first comma
        string="error: config option '%s': invalid choice: '%s' use (%s)" \
            % (self.name,value,ch)
        self.error=True
        self.value=None
        print(string)

    # Display invalid value error
    def invalid_error(self,value):
        string="error: config option '%s': invalid value: '%s'" % (self.name,value)
        self.error=True
        self.value=None
        print(string)
        
    # Display option value error if missing and required in config file
    def novalue_error(self):
        string="error: config option '%s': requires a value" % self.name
        self.error=True
        print(string)
        
  #
  #  Methods that may be overriden by a subclass
  #
  
    # Add the argument to an argument parser
    def add_argument(self,argparser):
        sopt=lopt=None
        if self.short:
            sopt="-%s" % self.short
        if self.full:
            lopt="--%s" % self.full
        if self.cl:
            if sopt is not None: 
                if lopt is not None:
                    if self.action is not None:
                        argparser.add_argument(sopt,lopt,action=self.action,\
                            help=self.help)
                    else:
                        argparser.add_argument(sopt,lopt,choices=self.choices,\
                            required=self.clreq,metavar=self.metavar,help=self.help)
                else:
                    if self.action is not None:
                        argparser.add_argument(sopt,action=self.action,help=self.help)
                    else:
                        argparser.add_argument(sopt,choices=self.choices,\
                            required=self.clreq,metavar=self.metavar,help=self.help)
            elif lopt is not None:
                if self.action is not None:
                    argparser.add_argument(lopt,action=self.action,help=self.help)
                else:
                    argparser.add_argument(lopt,choices=self.choices,\
                        required=self.clreq,metavar=self.metavar,help=self.help)
            else:
                raise ValueError("%s either argument 'full' or 'short' are required" \
                   % eloc(self,"argument"))
  
    # Populate the argument from the command-line parsers namespace (after
    # conversion to a dictionary)
    def cl(self,pargs):
        if self.use_cl:
            if self.full is None:
                self._cl=None
            else:
                self._cl=pargs[self.full]

    # Populate the argument from the configuration file
    def cfg(self,cfg,section):
        #print("%s %s use_cfg: %s" % (eloc(self,"cfg"),self.name,self.use_cfg))
        if not self.use_cfg:
            return

        # Fetch the option from the configuration.  A subclass may enhance the
        # processing of the string returned by the default method.
        try:
            cfgval=self.cfg_value(cfg,section)
        except KeyError:
            return

        self._cfg=cfgval

    # This method accesses the ConfigFile object to read an option from a secion
    # This is a lower level action than occurs with the cfg() method.  It provides
    # an opportunity for a subclass to impose additional constraints or
    # transformations on the the string retrieved from the configuration file
    # before returning the result to the Option object.
    #
    # Transformations should be explicit to aspects of the ConfigFile.  General
    # transformations independent of source should be made in the value_xform()
    # method.
    #
    # Subclasses must handle the case when no value has been supplied for the
    # option.
    #
    # Returns:
    #   the value string value from the configuration file.  Multiline and multiple
    #   options are not handled by this default method.  Override for those
    #   considerations.
    # Exception:
    #   KeyError if option not found 
    def cfg_value(self,cfg,section):
        if __debug__:
            if self.debug:
                print("%s section:%s  option:%s" \
                    % (eloc(self,"cfg_value"),section,self.name))
        try:
            return cfg.option(section,self.name)
        except KeyError:
            pass
        return cfg.defaults[self.name]

    # Add the argument's value to the Config object
    def config(self,config):
        config.arg(self.name,self.typ,self.value)

    # Populate the argument from the environment variables
    def env(self,env):
        if not self.use_env:
            return
        try:
            self._env=env[self.env.name]
        except KeyError:
            return

    # Establishes the option's value 
    def option(self,tool):
        value=None
        typ="?"
        if self.use_cl and self._cl:
            value=self._cl
            typ="*"
        elif self.use_env and self._env:
            value=self._env
            typ="E"
        elif self.use_cfg and self._cfg:
            value=self._cfg
            typ="C"
        if value is None: 
            if self.default is not None:
                value=self.default
                typ="D"
            else:
                value=None
                typ="O"
        if (value is not None) and self.choices and (value not in self.choices):
            self.choice_error(value)
            self.error=True
            typ="?"
        self.value=self.value_xform(value)
        self.typ=typ

    # Transform the value supplied from any source.  The result will be placed in
    # the final Config object for this option.  By default the value selected
    # is returned without alteration.  Override this method in a subclass to change
    # this default behavior.  An example for use of this method might be to
    # convert a string (which is typically returned by the configparser and
    # argparser) into an integer.
    def value_xform(self,value):
        return value


class Boolean(Option):

    # Recognized boolean values in a boolean option
    booleans={"True":True,"1":True,"true":True,"on":True,"enable":True,\
              "False":False,"0":False,"false":False,"off":False,"disable":False}

    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,action=None,novalue=False,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,action=action,
            help=help,cl=cl,cfg=cfg,env=env,site=site)

    # Process configuration boolean option.  No value supported as implied value.
    def cfg_value(self,cfg,section):
        value=super().cfg_value(cfg,section)
        #print("%s %s cfg value: %s" % (eloc(self,"cfg_value"),self.name,value))

        if value is None:
            return self.default
        elif Option.isNoValue(value):
            # Treat the option as a toggle switch
            if self.default is False:
                return True
            elif self.default is True:
                return False
            else:
                raise ValueError("%s unexpected default value: %s" \
                    % (eloc(self,"cfg_value"),self.default))

        # A value was coded, so interpret it as a boolean enable/disable value
        try:
            return Boolean.booleans[value]
        except KeyError:
            self.invalid_error(value)
            
class Flag(Boolean):
    def __init__(self,name,action,default,short=None,full=None,help=None,\
                 cl=True,cfg=True):
        super().__init__(name,short=short,full=full,action=action,default=default,\
            help=help,cl=cl,cfg=cfg)

    # Add the argument to an argument parser
    def add_argument(self,argparser):
        sopt=lopt=None
        if self.short:
            sopt="-%s" % self.short
        if self.full:
            lopt="--%s" % self.full
        if self.cl:
            if sopt is not None: 
                if lopt is not None:
                    argparser.add_argument(sopt,lopt,action=self.action,\
                        help=self.help)
                else:
                    argparser.add_argument(sopt,action=self.action,help=self.help)
            elif lopt is not None:
                argparser.add_argument(lopt,action=self.action,help=self.help)
            else:
                raise ValueError("%s either argument 'full' or 'short' are required" \
                   % eloc(self,"argument"))


# Supports an option of multiple values on a single line.  No value results in an
# error.  This option allows spaces to be present in a value.
class Option_ML(Option):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,action=None,novalue=False,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,action=action,
            help=help,cl=cl,cfg=cfg,env=env,site=site)

    # Process configuration option that supports a single values on each lines.  
    # Each value is a string returned in a list.  No value results in an error.
    def cfg_value(self,cfg,section):
        value=super().cfg_value(cfg,section)
        if Option.isNoValue(value):
            self.novalue_error()

        # Split value at line ends (do not keep them)
        lines=value.splitlines()
        values=[]
        for line in lines:
            values.append(line.strip())
        if len(values)==0:
            self.novalue_error()     
        return values


# This class supports an option with multiple values on multiple lines
class Option_MLMV(Option):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,action=None,novalue=False,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,action=action,
            help=help,cl=cl,cfg=cfg,env=env,site=site)

    # Process configuration option that supports multiple values on multiple lines.  
    # Each value is a string returned in a list.  No value results in an empty list.
    def cfg_value(self,cfg,section):
        try:
            value=cfg.option(section,self.name)
        except KeyError:
            return []
        if Option.isNoValue(value) or value is None:
            return []

        # Split values where white space occurs
        return value.split()


# This class supports an option with a single value
class Option_SV(Option):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,action=None,novalue=False,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,action=action,
            help=help,cl=cl,cfg=cfg,env=env,site=site)

    # Process configuration option that supports a single string value.  
    # No value is an error.  Other editing, for example, choices, is done elsewhere.
    def cfg_value(self,cfg,section):
        value=super().cfg_value(cfg,section)
        if Option.isNoValue(value):
            self.novalue_error()
        return value


class Choices(Option_SV):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        assert choices is not None,\
            "%s 'choices' argument must not be None" % eloc(self,"__init__")

        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,action=None,\
            novalue=False,help=help,cl=cl,cfg=cfg,env=env,site=site)
        
        
class Decimal(Option_SV):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 metavar=None,help=None,\
                 cl=False,cfg=False,env=False,site=False):

        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=None,metavar=metavar,action=None,\
            novalue=False,help=help,cl=cl,cfg=cfg,env=env,site=site)

    def value_xform(self,value):
        try:
            return int(value,10)
        except ValueError:
            self.invalid_error(value)
        
        
class IntChoices(Choices):
    def __init__(self,name,short=None,full=None,default=None,required=False,\
                 choices=None,metavar=None,help=None,\
                 cl=False,cfg=False,env=False,site=False):
        assert choices is not None,\
            "%s 'choices' argument must not be None" % eloc(self,"__init__")

        super().__init__(name,short=short,full=full,default=default,\
            required=required,choices=choices,metavar=metavar,help=help,\
            cl=cl,cfg=cfg,env=env,site=site)
        
    def value_xform(self,value):
        if value is None:
            return None
        return int(value)


class Disable(Flag):
    def __init__(self,name,short=None,full=None,help=None,cl=True,cfg=True):
        super().__init__(name,"store_false",True,short=short,full=full,help=help,\
            cl=cl,cfg=cfg)


class Enable(Flag):
    def __init__(self,name,short=None,full=None,help=None,cl=True,cfg=True):
        super().__init__(name,"store_true",False,short=short,full=full,help=help,\
            cl=cl,cfg=cfg)


class Environment(Option_SV):
    def __init__(self,name,full=None,default=None,metavar=None,\
                 help=None,cl=False,cfg=False,env=True,site=False):
        super().__init__(name,full=full,metavar=metavar,help=help,\
            cl=cl,cfg=cfg,env=env,site=site)
        # Whether this environment variable is a directory search order path
        self.path=False
        self.default=default  # Default directory of value if omitted

    # Populate the argument from the environment variables
    def env(self,env):
        if self.path:
            # Path variables are handled by the satkutil PathMgr object.
            # Only handle other environment variables here.
            return
        if not self.use_env:
            return
        try:
            variable=env[self.env_name]
        except KeyError:
            return
        self._env=variable


class ListArg(Option_MLMV):
    def __init__(self,name,short=None,full=None,metavar=None,help=None,\
                 required=False,choices=None,cl=False,cfg=False,env=False):
        super().__init__(name,short=short,full=full,default=[],metavar=metavar,\
            required=required,choices=choices,help=help,cl=cl,cfg=cfg,env=env)

    def add_argument(self,argparser):
        option=0
        if self.short is not None:
            option+=2
            short="-%s" % self.short
        if self.full is not None:
            option+=1
            full="--%s" % self.full
        if option == 1:
            # Full name only
            argparser.add_argument(full,action="append",metavar=self.metavar,\
                default=[],choices=self.choices,help=self.help)
        elif option==2:
            argparser.add_argument(short,action="append",metavar=self.metavar,\
                default=[],choices=self.choices,help=self.help)
        elif option==3:
            argparser.add_argument(short,full,action="append",metavar=self.metavar,\
                default=[],choices=self.choices,help=self.help)
        else:
            raise ValueError("%s neither a short nor full command-line argument"\
                % eloc(self,"add_argument"))
            
    # Establishes the option's value 
    def option(self,tool):
        value=None
        typ="?"
        if self.use_cl and self._cl:
            value=self._cl
            typ="*"
        elif self.use_env and self._env:
            value=self._env
            typ="E"
        elif self.use_cfg and self._cfg:
            value=self._cfg
            typ="C"
        if value is None: 
            if self.default is not None:
                value=self.default
                typ="D"
            else:
                value=[]
                typ="O"
        assert isinstance(value,list),\
            "%s option %s value not a list: %s" \
                % (eloc(self,"option"),self.name,value)
        tvals=[]
        for v in value:
            if self.choices is not None and value not in self.choices:
                self.choice_error(value)
                self.error=True
                typ="?"
            tvals.append(self.value_xform(v))
        self.value=tvals
        self.typ=typ


# Supports a directory search-order path as an environment variable or a
# a configuration option.
class Path(Option_MLMV):
    def __init__(self,name,default=None,cfg=False,site=False):
        super().__init__(name,cfg=cfg,default=default,env=name.upper(),site=site)
        self.path=True

    def env(self,env):
        if not self.use_env:
            return
        self._env=self.env_name

    def option(self,tool):
        cfg_value=[]
        if self.use_cfg and self._cfg:
            cfg_value=self._cfg   # The cfg_value() method returns a list

        patho=satkutil.PathMgr()
        # The PathMgr object will extract the environment variable and process
        # if for its directories.
        patho.path(self.env_name,config=cfg_value,cwdopt=tool.cwduse,\
            default=self.default)
        self.value=patho
        self.typ="P"
    

# Supports a source command-line option.  Configuration files or environment
# variables are not supported for an option of type Source.
#
# Instance Arguments:
#   name      The name of option as known by the configuration system
#   inopt     The input file option associated with this source section name
#   pathopt   The Path type option associated with this input source.
#   required  Whether the option must have a value or not.  Defaults to True.
#   help      Command-line help information.
#
# Note: arguments 'inopt' and 'pathopt' are only used in support of the config.py
# tool's --tool testing role.  Normally the tool defining this option marries the
# input option and path option in its code.  To support the config.py tool's test
# role, it needs to know which options are tied together.
class Source(Option):
    def __init__(self,name,inopt,pathopt=None,required=True,help=None):
        super().__init__(name,full=name,required=required,help=help,\
            cl=True,cfg=False,env=False)
        self.inopt=inopt  # input file option associated with this source
        self.pathopt=pathopt   # input path type option associated with this source

    def add_argument(self,argparser):
        if self.required:
            argparser.add_argument(self.full,nargs=1,help=self.help)
        else:
            argparser.add_argument(self.full,nargs="?",default=None,help=self.help)
        
    def cl(self,pargs):
        # The argument attributes supplied to the argparser.parser object
        # ensures that if present, a list of one element will be supplied and
        # if not required 
        if self.use_cl:
            item=pargs.get(self.full)
            if self.required:
                # nargs=1 returns a list of one element
                self._cl=item[0]
            else:
                # nargs="?" returns the item if present or None (default=None)
                self._cl=item


# This class encapsulates the specification of configuration parameters used in
# either the command-line (via a Python argparse.parser object) or configuration files
# (via Python configparser.ConfigParser object) or both.

# Required Instance Arguments:
#   prog       Program name used for command-line help information
#   copyright  Epilog information displayed following command-line arguement
#              descriptions.  Must include copyright information but may include
#              additional information.
#   desc       The program description when displaying command-line help
class Configuration(object):
    # Options expected in site.cfg.  The first element identifies the site directory
    # pointer.
    site=["satkcfg","cwduse"]

    def __init__(self,prog,copyright,desc):
        assert isinstance(prog,str),\
            "%s 'prog' argument must be a string: %s" \
                % (eloc(self,"__init__"),prog)
        assert isinstance(copyright,str),\
            "%s 'copyright' argument must be a string: %s" \
                % (eloc(self,"__init__"),copyright)
        assert isinstance(desc,str),\
            "%s 'desc' argument must be a string: %s" \
                % (eloc(self,"__init__"),desc)

        # Return to this definition when epilog not shown without help
        # Seems to be an error with Python 3.4.1
        #self.parser=argparse.ArgumentParser(prog=prog,\
        #    formatter_class=argparse.RawDescriptionHelpFormatter,\
        #    description=desc,epilog=copyright,add_help=True)
        self.parser=argparse.ArgumentParser(prog=prog,\
            description=desc,epilog=copyright,add_help=True)

        self._args={}         # defined options
        self._args_list=[]    # Tool specific arguments (Option objects)
        self._site_list=[]    # Argument objects associated with root (Option objects)
        self._tool_copyright=copyright  # Tool's copyright notice
        
        # Helpers for cinfo build methods.  See options() method.
        self._opt_list=None   # Sorted option names
        self._opt_len=0       # Maximum length of options

        # List of arguments from various sources for building separating option
        # sources.  All of these lists contain Option objects.
        self._cli_list=[]     # List of command-line arguments
        self._cfg_list=[]     # List of Option objects in the configuration system
        self._path_list=[]    # List of search order path environment variables
        self._env_list=[]     # list of other environment variables
        self._source=None     # input source Option object

    # Retrieve an Option object from the configuration.  If it has not been updated
    # by the populate() method it will have its value attribute still set at None.
    # Exceptions:
    #   KeyError  if the requested option is not defined
    def __getitem__(self,key):
        return self._args[key]

    # Define a command-line and configuration file attribute
    def arg(self,arg):
        assert isinstance(arg,Option),\
            "%s 'arg' argument must be an instance of Argument: %s" \
               % (eloc(self,"_arg"),arg)
        try:
            self._args[arg.name]
            raise ValueError("%s argument already defined: %s" \
                % (eloc(self,"_arg"),arg.name))
        except KeyError:
            pass

        # Determine when to update the argument
        self._args[arg.name]=arg
        if arg.name.lower() in Configuration.site:
            self._site_list.append(arg)
        else:
            self._args_list.append(arg)

        if arg.use_cl:
            self._cli_list.append(arg)
        if arg.use_cfg:
            self._cfg_list.append(arg)
        if arg.use_env:
            if arg.path:
                self._path_list.append(arg)
            else:
                self._env_list.append(arg)
                
        if isinstance(arg,Source):
            if self._source is None:
                self._source=arg
            else:
                raise ValueError("%s multiple Source objects encountered, source "
                    "%s already defined, can not define source: %s" \
                    % (eloc(self,"arg"),self._source.name,arg.name))

    # Build a command-line argument parser from the defined arguments
    def arg_parser(self):
        for arg in self._cli_list:
            arg.add_argument(self.parser)
        return self.parser

    # Determines if a given environment variable name is part of the configuration
    # system.
    def isVar(self,name):
        return name in self._path_list or name in self._env_list

    # Returns a list of all Option objects in sorted order.
    def options(self):
        if self._opt_list is not None:
            return self._opt_list
        optlen=0
        plist=[]
        for lst in [self._args_list,self._site_list]:
            for opt in lst:
                optlen=max(optlen,len(opt.name))
                plist.append(opt)
        plist.sort(key=Option.sort)
        self._opt_list=plist
        self._opt_len=optlen

        return plist

    # Returns a dictionary of option defaults.  Used by the config tool to
    # build the tool's DEFAULT section.
    def option_defaults(self):
        dct={}
        for lst in [self._args_list,self._site_list]:
            for opt in lst:
                if opt.default is None:
                    continue
                try:
                    dct[opt.name]
                except KeyError:
                    dct[opt.name]=opt.default

        return dct

    # Update the supplied Config object with the option information, checking for
    # errors.  The process is terminated if errors encountered.
    def update(self,config):
        assert isinstance(config,Config),\
            "%s 'config' argument must be a Config object: %s" \
                % (eloc(self,"update"),config)

        errors=0
        for lst in [self._site_list,self._args_list]:
            for opt in lst:
                #print("%s %s" % (eloc(self,"update"),opt))
                if opt.required and opt.value is None:
                    print("error: required config option %s: omitted" % opt.name)
                    errors+=1
                    continue
                if opt.error:
                    errors+=1
                    continue
                config[opt.name]=opt.value

        if errors:
            print("error: terminating: options in error: %s" % errors)
            # !!EXIT THE PROCESS
            sys.exit(1)

  #
  # Methods supplied by subclass
  #

    # This method returns the name of the configuration file to be used.  It is
    # called after the supplied command-line arguments have been called, making
    # those arguments available for inspection by this method.
    def config_file(self):
        raise NotImplementedError(\
            "%s subclass %s must supply config_file() method" \
                % (eloc(self,"config_file"),self.__class__.__name__))


#
#  +---------------------------+
#  |                           |
#  |    Config Info Utility    |
#  |                           | 
#  +---------------------------+
#

# This class encapsulates option cinfo processing.  It is supplied to the tool
# as an attribute of the Config class.

# Instance methods
class CINFO(object):
    
    # supported cinfo option request flags and default display order
    infoids="AYEVUFSDO"
    
    # Return a formatted string of configuration information options.
    @staticmethod
    def cinfo_options():
        return \
"""CINFO configuration information options:
    'A' = script arguments from the command-line,
    'D' = configuration defaults,
    'E' = tool environment variables,
    'F' = configruation files used by the tool,
    'L' = all information (equals '%s')
    'O' = configuration options and source,
    'S' = configruation sections,
    'U' = option usage specification,
    'V' = all process environment variables, or
    'Y' = PYTHONPATH as seen by the tool
""" % CINFO.infoids

    def __init__(self):
        self.info_dict={}      # List of detail strigns built by tool
        self.cinfo=None        # Information ids requested by cinfo option

        # How to display each option
        self.rtns={"A":self._display_A,
                   "D":self._display_D,
                   "E":self._display_E,
                   "F":self._display_F,
                   "O":self._display_O,
                   "S":self._display_S,
                   "U":self._display_U,
                   "V":self._display_V,
                   "Y":self._display_Y}

    def __getitem__(self,infoid):
        return self.info_dict[infoid]

    def __setitem__(self,infoid,lst):
        self.info_dict[infoid]=lst

    def _display_lines(self,lines,indent="    "):
        for line in lines:
            print("%s%s" % (indent,line))

    def _display_A(self):
        lines=self["A"]
        print("CINFO Option A - Script command-line arguments:")
        self._display_lines(lines,indent="")
        print("")

    def _display_D(self):
        lines=self["D"]
        hdr="CINFO Option D - Configuration Defaults:"
        if len(lines)==0:
            print("%s none" % hdr)
        else:
            print(hdr)
            self._display_lines(lines)
        print("")

    def _display_E(self):
        lines=self["E"]
        hdr="CINFO Option E - Tool related environment variables:"
        if len(lines)==0:
            print("%s none" % hdr)
        else:
            print(hdr)
            self._display_lines(lines)
        print("")

    def _display_F(self):
        lines=self["F"]
        hdr="CINFO Option F - Configuration files: %s" % len(lines)
        print(hdr)
        self._display_lines(lines)
        print("")

    def _display_O(self):
        lines=self["O"]
        hdr="CINFO Option O - Option settings:"
        if len(lines) == 0:
            print("%s none" % hdr)
        else:
            sources=  "\n  * = command-line, E = environment variable,"
            sources="%s\n  C = config file,  D = default," % sources
            sources="%s\n  O = omitted,      P = searh order path" % sources
            sources="%s\n  W = working dir   ? = error encountered\n" % sources
            hdr="%s%s" % (hdr,sources)
            print(hdr)
            self._display_lines(lines)
        print("")

    def _display_S(self):
        lines=self["S"]
        hdr="CINFO Option S - Configuration sections:"
        if len(lines)==0:
            print("%s none" % hdr)
        else:
            print(hdr)
            self._display_lines(lines)
        print("")

    def _display_U(self):
        lines=self["U"]
        hdr="CINFO Option U - Tool Confiuration option usage:"
        hdr="%s\n  A = command-line argument, C = configuration option," % hdr
        hdr="%s\n  E = environment variable,  M = multi-value," % hdr
        hdr="%s\n  O = optional,              P = search-order path," % hdr
        hdr="%s\n  R = required,              S = single value," % hdr
        hdr="%s\n  + = enable flag,           - = disable flag\n" % hdr
        print(hdr)
        self._display_lines(lines)
        print("")

    def _display_V(self):
        lines=self["V"]
        hdr="CINFO Option V - Process environment variables:"
        if len(lines)==0:
            print("%s none" % hdr)
        else:
            print(hdr)
            self._display_lines(lines)
        print("")

    def _display_Y(self):
        lines=self["Y"]
        hdr="CINFO Option Y - PYTHONPATH import search order:"
        if len(lines)==0:
            print("%s none" % hdr)
        else:
            print(hdr)
            self._display_lines(lines)
            print("")

    # Display in cinfo option order the various information summaries.  If the
    # 'A' option is used, the default order defined
    def display(self):
        # If there is no information data to display or none requested simply return
        if self.cinfo is None or len(self.info_dict)==0:
            return
        print("")
        for infoid in self.cinfo:
            try:
                rtn=self.rtns[infoid]
            except KeyError:
                raise ValueError("%s unrecognized CINFO option ID encountered: %s"\
                    % (eloc(self,"display"),infoid))

            try:
                data=self.info_dict[infoid]
            except KeyError:
                raise ValueError("%s no data for CINFO option ID: %s" \
                    % (eloc(self,"display"),infoid))
                    
            rtn()


#
#  +-----------------------+
#  |                       |
#  |    Tool Definition    |
#  |                       | 
#  +-----------------------+
#

# This class is used by the tool for management of the configuration text files
# themselves.
#
# Directory creation and the writing of files honors the command-line options
# --verbose, --exec, and --force.
#
# Instance Arguments:
#   directory   The absolute path of the directory containing the file.  Note if
#               specified as None, the filename is treated as the file path.
#   filename    File name of the file being created.
#   ro          Whether the file may only be read (True) or also written (False).
#               Defaults to True.
#   verbose     Whether progress messages are to be displayed
class TextFile(object):

    # Categorizes a path: DA, DR, FA, FR, EA, ER, NA, NR
    # D == directory, F == file, E == exists, N == nonexistent, 
    # A == absolute path, R == relative path
    @staticmethod
    def ftype(path):
        a=""
        if os.path.isabs(path):
            a="A"
        else:
            a="R"
        if os.path.isdir(path):
            return "D%s" % a
        if os.path.isfile(path):
            return "F%s" % a
        if os.path.exists(path):
            return "E%s" % a
        return "N%s" % a
    def __init__(self,directory,filename,ro=True,verbose=False):
        self.ro=ro      # Whether the file may be overwritten or not
        self.dtype="??"
        self.ftype="??"

        # Directory to be created and into which filename is written
        self.directory=directory
        if directory is not None:
            self.dtype=TextFile.ftype(directory)
            if verbose:
                print("directory %s type: %s" % (directory,self.dtype))

        # File name with extension into which content is written
        self.filename=filename
        # File path of the file
        if directory is not None:
            self.filepath=os.path.join(self.directory,self.filename)
        else:
            self.filepath=filename
        self.ftype=TextFile.ftype(self.filepath)
        if verbose:
            print("filepath %s type: %s" % (self.filepath,self.ftype))

    # Physically writes the file's content
    def _write(self,content,verbose=False):
        # We let IOError's just propagate.  They should not occur with the checks
        # already performed
        fo=open(self.filepath,"wt")
        if verbose:
            print("text file opened for writing: %s" % self.filepath)
        fo.writelines(content)
        fo.close()
        if verbose:
            print("%s lines written to text file: %s" % (len(content),self.filepath))

    # Writes text content to fhe file.  The TextFile object must have been created
    # with ro=False to be written.
    # Method arguments:
    #   content  List of strings to be written to the file
    #   verbose  Whether progress messages are to be generated
    #   force    Whether the file should be overwritten if it already exists
    def write(self,content,verbose=False,force=False):
        # Validate method input and whether it is eligible for being written
        assert isinstance(content,list),\
            "%s 'content' argument must be a list: %s" \
                % (eloc(self,"write"),content)
        if __debug__:
            for n,line in enumerate(content):
                if not isinstance(line,str):
                    raise ValueError(\
                        "%s 'content' argument item %s of %s not a string: %s" \
                            % (eloc(self,"write"),n,len(content),line))
        assert self.ro is False,\
            "%s writing of the file requires it to be established as ro=False: %s"\
                % (eloc(self,"write"),self.filepath)

        if not self.ftype in ["FA","NA"]:
            if "D" in self.ftype:
                raise ConfigError(\
                    msg="can not create file, path is a directory: %s" \
                    % self.filepath)
            raise ConfigError(msg="can not create file %s, unrecognized state: %s"\
                % (self.filepath,self.ftype))
        if self.ftype == "FA":
            if verbose:
                print("File exists: %s" % self.filepath)
            if not force:
                raise ConfigError(msg="can not overwrite existing file without "
                    "option --force: %s" % self.filepath)
            else:
                # File exists but option --force in effect
                self._write(content,verbose=verbose)
       
        else: # Assumes ftype state of "NA"
            self._write(content,verbose=verbose)

# Provides the basis for a tools interaction with the configuration system.
# Instance Arguments:
#   name      The name of the tool.
#   ro        Whether the config files may be written.  Specify True to inhibit
#             writing.  Specify False to enable writing.  Defaults to True.
#             Note: this option is primarily for use of the config.py tool itself
#             to allow it to write configuration files.
#   site      Whether the site directory contains a defaults config file for the tool
#             Defaults to True.
#   test      Whether this Tool is participating in a test driven by config.py.
#             Defaults to False.
#   debug     Whether to provide certain debug messages.  Specify True to provide 
#             the messages.  Specify False to disable them.  Defaults to False.
#             This option is manually driven when the tool subclass instantiates
#             the Tool object for the configuration system.  Normally CINFO should
#             be used for problem resolution.
#
# Note: The Tool object may be the foundation for the entire processing of the
# Tool (by making the tool a subclass) or the Tool object may be an intermediary
# and supply just the resultant Config object to the tools processor.
class Tool(object):
    def __init__(self,name,ro=True,site=True,test=False,debug=False):
        self.name=name          # Tool name as recognized by configuration system
        self.site=site          # Whether this tool is included in site directory
        self.test=test          # Whether this is a config test being performed
        self.debug=debug        # Whether debug messages are enabled.
        # Path information used by the configuration system
        self.satk=satkutil.satkroot()
        # Build the configuration options used by tool (Configuration object) 
        self.spec=self.tool_spec()
        if self.test:
            self.option_tool_test(self.spec)
        # Build the command-line parser (argparse.parser object)
        self.arg_parser=self.spec.arg_parser()
        self.notice=False    # Whether copyright notice has been displayed

        # Defer building the configuration interface (ConfigFile object) until
        # after command line arguments have been processed.
        self.cfg_parser=None  # See method create_cfg_parser()

        # Process supplied options
        self.cli_raw=sys.argv     # Unparsed command line script arguments as a list
        self.env_raw=os.environ   # Environment variables as a dictionary

        # Parsed command-line arguments. See cli_args() method
        self.cli_ns=None          # Argparse namespace object
        self.cli=None             # cli dictionary

        # Configuration Text File Management - TextFile objects
        #
        # These are established at different points in time depending upon whether
        # the config tool is in use or another tool.  The config tool has specific
        # requirements unique from other tools.
        self.ro=ro              # Whether the config files may be written
        self._satkcfg=None      # The site.cfg file in $SATK/config directory
        self._toolcfg=None      # The tool.cfg File in the site directory
        self._srccfg=None       # The --cfg option file from tool.cfg CONFIGS section

        # Bootstrap the configuration system
        self.cfgdir=satkutil.satkdir("config")
        self._satkcfg=TextFile(self.cfgdir,"site.cfg",ro=ro)
        self.site=None      # user's site configuration directory
        self.cwduse=None    # cwduse configuration option

        # Config being constructed by configuration system
        self.cinfo=None           # CINFO object.  See build_cinfo()
        self.config=Config()      # Config object supplied to tool

    # Build script command line options for cinfo
    def __build_cinfo_A(self,debug=False):
        lines=[" ".join(self.cli_raw),]
        if __debug__:
            if debug:
                print("Command Line:")
                for line in lines:
                    print(line)
                print("")
        return lines

    # Build configuration default information
    def __build_cinfo_D(self,debug=False):
        dfts=self.cfg_parser.defaults
        keylen=0
        pairs=[]
        lines=[]
        keys=sorted(dfts.keys())
        for key in keys:
            item=dfts[key]
            keylen=max(len(key),keylen)
            pairs.append((key,item))
        for d,v in pairs:
            string="%s = %s" % (d.ljust(keylen),v)
            lines.append(string)
        if __debug__:
            if debug:
                print("Configuration Defaults:")
                for line in lines:
                    print(line)
                print("")
        return lines

    # Build configuration process environment variables (used by both E and V ids):
    #   - Option E: SATK related variables only
    #   - Option V: All process environment variables
    def __build_cinfo_E(self,process=False,debug=False):
        env=self.env_raw
        variables=[]
        # Look at only environment variable I am interested in (is this a good thing?)
        if process:
            variables=list(env.keys())
        else:
            variables=[]
            for v in env.keys():
                if self.spec.isVar(v):
                    variables.append(v)
        variables.sort()

        varlen=0
        pairs=[]
        lines=[]
        for variable in variables:
            item=env[variable]
            varlen=max(len(variable),varlen)
            pairs.append((variable,item))
        for e,v in pairs:
            string="%s = %s" % (e.ljust(varlen),v)
            lines.append(string)

        return lines

    # Build configuration file information
    def __build_cinfo_F(self,debug=False):
        lines=self.cfg_parser.files
        if __debug__:
            if debug: 
                print("Configuration files: %s" % len(lines))
                for line in lines:
                    print(line)
                print("")
        return lines

    # Build multi value option information.  Used by cinfo option 'O'
    def __build_cinfo_MV(self,prefix,values=[]):
        if len(values)==0:
            return [prefix,]

        lines=[]
        line=prefix
        for n,p in enumerate(values):
            if n == 0:
                linelen=len(line)
                lines.append("%s%s" % (line,p))
                # remaining lines are indented to match the directory
                line=" " * linelen
            else:
                lines.append("%s%s" % (line,p))
        return lines

    # Build configuration options used
    def __build_cinfo_O(self,debug=False):
        options=self.spec.options()   # Get the options from the Configuration object
        keylen=self.spec._opt_len     # Maximum option name length

        lines=[]
        for opt in options:
            if opt.typ=="E":
                name=opt.env_name
            else:
                name=opt.name
            if isinstance(opt,Path):
                # Fetch the formatted dir search order from the satkutil.SOPath
                # object in the PathMgr object for this variable
                sopath=opt.value.cinfo(opt.env_name)
                path_lst=sopath.cinfo()
                
                # Format the first line with the option name
                line="%s  %s = " % (opt.typ,name.ljust(keylen))
                lines.extend(self.__build_cinfo_MV(line,values=path_lst))
            elif isinstance(Option_ML,Option_MLMV):
                line="%s  %s = " % (opt.typ,name.ljust(keylen))
                lines.extend(self.__build_cinfo_MV(line,values=opt.value))
            else:
                line="%s  %s = %s" % (opt.typ,name.ljust(keylen),opt.value)
                lines.append(line)

        return lines

    # Build configuration sections found
    def __build_cinfo_S(self,debug=False):
        lines=[]
        for sect in self.cfg_parser.sections:
            lines.append(sect)
        for sect in self.cfg_parser.missing:
            lines.append("%s (MISSING)" % sect)   
        if __debug__:
            if debug:
                print("Sections:")
                for line in lines:
                    print(line)
                print("")
        return lines

    # Build configuration system option usage information
    def __build_cinfo_U(self,debug=False):
        options=self.spec.options()   # Get the options from the Configuration object
        lines=[]
        for opt in options:
            cl=cfg=env=" "
            if opt.use_cl:
                cl="A"
            if opt.use_cfg:
                cfg="C"
            if opt.use_env:
                if opt.path:
                    env="P"
                else:
                    env="E"
            if opt.required:
                req="R"
            else:
                req="O"
            if isinstance(opt,Enable):
                n="+"
            elif isinstance(opt,Disable):
                n="-"
            elif isinstance(opt,(Option_ML,Option_MLMV)):
                n="M"
            else:
                n="S"
            if opt.short is None:
                short=" "
            else:
                short=opt.short
            string="%s %s %s %s %s  %s %s" % (cl,env,cfg,req,n,short,opt.name)
            if opt.default is not None:
                string="%s (default: %s)" % (string,opt.default)
            lines.append(string)
        if __debug__:
            if debug:
                print("Config option usage:")
                for line in lines:
                    print(line)
                print("")
        return lines
        
    # Build all process environment variables (including SATK related ones)
    def __build_cinfo_V(self,debug=False):
        return self.__build_cinfo_E(process=True,debug=debug)

    # Pythonpath directories
    def __build_cinfo_Y(self,debug=False):
        return sys.path

    # Return the run-time defaults as a dictionary supplied to the ConfigFile
    # object and ultimately to the configparser.
    def __run_time(self,inopt=None):
        defaults={}
        defaults["cwd"]=os.getcwd()
        defaults["date"]=time.strftime("%Y%m%d")
        defaults["time"]=time.strftime("%H%M%S")
        defaults["satk"]=self.satk

        try:
            defaults["home"]=self.env_raw["HOME"]
        except KeyError:
            pass
        
        if not inopt is None:
            defaults["input"]=inopt

        self.tool_config_defaults(defaults)  # Add tool specific defaults
        return defaults

    # This method updates the Config object with configuration options
    # Returns only if all required options are present and no errors encountered
    def __update(self):
        self.spec.update(self.config)

    # This private method construction the tool cinfo data based upon the cinfo option
    def build_cinfo(self,debug=False):
        cinfo=self.config["cinfo"]
        if cinfo is None:
            return
        cinfo=cinfo.upper()
        if "L" in cinfo:
            cinfo=CINFO.infoids
        rtns={"A":self.__build_cinfo_A,
              "D":self.__build_cinfo_D,
              "E":self.__build_cinfo_E,
              "F":self.__build_cinfo_F,
              "O":self.__build_cinfo_O,
              "S":self.__build_cinfo_S,
              "U":self.__build_cinfo_U,
              "V":self.__build_cinfo_V,
              "Y":self.__build_cinfo_Y}
        #print("%s cinfo: %s" % (eloc(self,"build_cinfo"),cinfo))
        
        cinfo_obj=CINFO()

        for infoid in cinfo:
            try:
                rtn=rtns[infoid]
            except KeyError:
                raise ValueError("%s no build routine for cinfo id: %s" \
                    % (eloc(self,"build_cinfo"),infoid))
            lines=rtn(debug=debug)
            cinfo_obj[infoid]=lines
        cinfo_obj.cinfo=cinfo   # Pass the option list to the CINFO object
        self.cinfo=cinfo_obj    # Remeber the CINFO object built here.

    # Establishes the argparser Namespace object and a dictionary.
    # Per standard SATK convention, the copyright notice is displayed following
    # parsing of the command-line arguments.  This is implemented here to
    # ensure it occurs.
    def cli_args(self):
        self.cli_ns=self.arg_parser.parse_args()
        if not self.notice:
            #print(copyright)
            print(self.spec._tool_copyright)
            self.notice=True
        self.cli=vars(self.cli_ns)   # Convert the Namespace into a dictionary

    # Uses the system to create the Config object containing consolitated
    # command-line arguments, environment variable data and configuration file
    # options.  Errors encountered during command-line argument parsing causes
    # the Python script to terminate with error messages.  Errors encountered
    # during configuration file processing are reported and the failure may or
    # may not terminate the script.
    #
    # Returns:
    #   Config object of the run-time configuration for the tool
    def configure(self,verbose=False):
        # First retreive all of the command-line arguments
        if self.cli is None:
            # This allows a tool to access the command line arguments before
            # calling this module.  In that case, self.cli is not None and so
            # this method call is avoided.  Otherwise it does it for a tool
            # that does not require this behavior.
            self.cli_args()
            
        # Determine input source
        source=self.cli_ns.source
        if source is not None:
            if isinstance(source,list) and len(source)>0:
                source=source[0]
            elif isinstance(source,str):
                pass
            else:
                raise ValueError("%s unexpected command-line source value: %s" \
                    % (eloc(self,"configure"),source))

        # Build the ConfigFile object to interface with the configuration system
        self.create_cfg_parser(inopt=source)
        # Update Argument objects with site information as needed
        # 
        self.parse_site()
        # Locate the site directory from its populated Option object
        self.site=self.find_site()  # Determine site directory location.
        # Figure out how to handle cwd in paths
        self.cwduse=self.find_option("cwduse")

        if self.site is not None:
            # site directory found so, proceed with the rest of the configuration
            self.parse_defaults()   # Access this tool's defaults
            self.parse_source()     # Access optional source config if supplied
            src_sect=source
        else:
            # site directory not found, so do not populate from the config files
            src_sect=None

        self.populate(self.spec._args_list,section=src_sect)

        # All of the options are set in the Config object.
        # If errors are encountered, the process ends without return
        self.__update()       # Update the Config object will all of the values
        self.build_cinfo(debug=False)    # Build the cinfo data
        self.config._cinfo=self.cinfo    # Add CINFO object to the Config object
        return self.config

    # Create the configuration file parser
    def create_cfg_parser(self,inopt=None):
        self.cfg_parser=ConfigFile(parms=self.spec,\
            defaults=self.__run_time(inopt=inopt),debug=self.debug)

    # This method creates the default section for the tool's tool.cfg file
    # Returns:
    #   a list of strings corresponding to the tools defaults.
    def create_default_section(self):
        lines=[]
        lines.append("# To enable a different default, uncomment and change "
            "the option's value\n")
        lines.append("[DEFAULT]\n")
        options=self.spec.options()
        for opt in options:
            if opt.default is None:
                continue
            lines.append("# %s: %s" % (opt.name,opt.default))
        return lines

    # Access configuration options before they have been passed to the Config
    # object for release to the tool.
    #
    # This method is used for access to values defined in site.cfg and needed
    # for other option value handling.
    def find_option(self,option):
        try:
            opt=self.spec[option]
        except KeyError:
            return None
        if opt.error:
            return opt.default  
        return opt.value

    # Find the site directory from its option object
    # Returns None if the site directory has not been identified
    def find_site(self):
        try:
            option=Configuration.site[0]
            # Retrieve the site option directly from the Configuration object.
            # The Config object has yet to be updated
            site=self.spec[option]
        except KeyError:
            return None
        return site.value

    def option_cfg(self,cfg):
        cfg.arg(Option("cfg",full="cfg",metavar="CFGFILE",\
            help="optional user configuration.",\
            cl=True,cfg=False))

    def option_cinfo(self,cfg):
        cfg.arg(Option("cinfo",full="cinfo",default=None,\
            help="requested configuration option related information in any order, "\
            "without intervening spaces and combined as a single option value. "\
            "Option sequence dictates presentation sequence. "\
            "If omitted no configuration information is supplied.",\
            cl=True,cfg=True))

    def option_cwd(self,cfg,cl=False):
        cfg.arg(Choices("cwduse",full="cwduse",default="omit",\
            choices=["first","last","omit"],\
            help="cwd_use value in SITE section. Defaults to 'omit'",\
            cl=cl,cfg=True,site=True))

    # Definte the standard option for locating the site directory
    # It is enabled for all source: command-line, environment variable and SITE
    # section in the site.cfg file.
    def option_satkcfg(self,cfg,cl=False):
        site_name=Configuration.site[0]   # site option name
        site_cli=site_name.lower()        # Command line argument: satkcfg
        site_name=site_name.upper()       # Environment variable name: SATKCFG
        cfg.arg(Environment(site_cli,full=site_cli,metavar="DIR",default=None,\
            help="identifies --init site targeted configuration site directory. "\
            "If command-line argument is omitted, --init site expects to find "\
            "the %s environment variable." % site_cli,\
            cl=cl,cfg=True,env=site_name))
        
    # Define the source/input file option pair
    # Require Method Arguments:
    #   cfg     Configuration object to which source/input file option pair is added
    #   source  command-line positional argument name
    #   inopt   configuration option name
    #   pathopt related directory search order environment variable
    # Optional Method Arguments:
    #   required  Specify True if required.  Defaults to False.
    #   shelp   Command line help information for 'source' argument
    #   ihelp   Configuration option help for 'inopt' arguement
    def option_source(self,cfg,source,inopt,pathopt,required=False,\
                      shelp=None,ihelp=None):
        cfg.arg(Source(source,inopt,pathopt=pathopt,required=required,help=shelp))
        cfg.arg(Option_SV(inopt,required=False,help=ihelp,\
            cl=False,env=False,cfg=True))

    # Define the --tool option when testing a tools configuration
    def option_tool_test(self,cfg):
        cfg.arg(Option_SV("tool",full="tool",required=False,\
            cl=True,env=False,cfg=False))

    # Read the tool.cfg default configuraiton file and update the Configuration
    # objects
    def parse_defaults(self):
        tooldft="%s.cfg" % self.name
        self._toolcfg=TextFile(self.site,tooldft)
        self.cfg_parser.parse_defaults(self._toolcfg)
        # Defaults are automatically updated by the parser.  Any additional sections
        # will be read but updating of the configuration occurs after the source
        # config has been read

    # Read the site.cfg configuration file and update Configuration object's
    # options.
    def parse_site(self):
        # Read the site.cfg directory, if present 
        found=self.cfg_parser.parse_satk(self._satkcfg)
        if not found:
            return
        self.populate(self.spec._site_list,section="SITE")

    # Read the source configuration file identified by the --cfg command-line
    # argument and defined in the default configuration file's CONFIGS section.
    def parse_source(self):
        src_name=self.cli_ns.cfg   # Fetch the command-line --cfg argument if any
        if src_name is None:
            return
        src_option = self.cfg_parser.option("CONFIGS",src_name)
        if src_option is None:
            # If the user configuration file is not in the tool CONFIG section
            # try for it in the site directory
            self._scrcfg=TextFile(self.site,src_option)
        else:
            self._srccfg=TextFile(None,src_option)
        self.cfg_parser.parse_source(self._srccfg)
        source=self.cli_ns.source[0]

    # This method populates the arguments of the list with information from:
    #  1. the command-line
    #  2. the environment variables
    #  3. the current state of the configuration file system
    # And then updates the Config object under construction
    #
    # Method Arguments:
    #   arg_list  a list of Option objects being populated
    #   section   configuration section from which options are being used
    #   debug     Whether processing of this method is displayed.
    def populate(self,arg_list,section=None,debug=False):
        dbg=debug or self.debug
        if __debug__:
            if dbg:
                print("%s section: %s" % (eloc(self,"populate"),section))

        for arg in arg_list:
            arg.cl(self.cli)
            arg.env(self.env_raw)
            arg.cfg(self.cfg_parser,section)
            # Set the Option object's value attribute.  Pass myself for access
            # to other configuration information.
            arg.option(self)
            if __debug__:
                if dbg:
                    # Enable debugging message in option
                    if self.debug:
                        arg.debug=self.debug
                    print("%s %s" % (eloc(self,"populate"),arg))

    # Update the defaults with the tool specific option
    # By, defaults, the default for input is supplied as the command-line source
    # value.  Override this method if that is not appropriate for the tool subclass.
    def tool_config_defaults(self,dfts):
        # Determine if a Source argument has been defined for the tool
        source=self.spec._source
        if source is None:
            # No source argument so return
            return
        # Establish the source's partner input option with a default from the 
        # command line.
        src=self.cli_ns.source
        if isinstance(src,list):
            src=src[0]
        dfts[source.inopt]=src

  #  
  #  Method's required from subclass
  #

    # Creates site specific content for the tool's default tool.cfg file
    # Returns:
    #   - a list of strings terminated by universal newlines.  Lines are appended
    #     to the definition, or
    #   - an empty list if no content is to be added to the tool.cfg file.
    def tool_site(self):
        raise NotImplementedError("%s subclass %s must provide tool_site() method" \
            % eloc(self,"site"),self.__class__.__name__)

    # Builds the tool's Configuration object containing its supported options.
    # Returns:
    #   a Configuration object containing the definitions.
    def tool_spec(self):
        raise NotImplementedError("%s subclass %s must provide tool_spec() method" \
            % eloc(self,"spec"),self.__class__.__name__)


#
#  +------------------------------+
#  |                              |
#  |    Run-time Configuration    |
#  |                              | 
#  +------------------------------+
#

# This object is produced by the subclass of Tool object as a result of processing
# the script command-line arguments, environment variables and configuration system
# options.
class Config(object):
    def __init__(self):
        # Configuration values.  Maps option name (Option.name) to a value
        self._values={}    
        self._cinfo=None    # option cinfo related data
        #self.paths=satkutil.PathMgr()

    # Retrieve the requested option value.
    # Exceptions:
    #   ValueError if the option as requested does not exist.
    def __getitem__(self,key):
        try:
            return self._values[key]
        except KeyError:
            # At the point the Config object is supplied to the using tool, all 
            # options should ave a value in this object, even if it is None.  
            # If the key does not exist, this is either a problem within the 
            # tool's Configuration object or in the coding of the key the tool is
            # using for option access.
            raise ValueError("%s 'key' argument is not a configured option: %s" \
                % (eloc(self,"__getitem__"),key))

    # Sets the options value
    # Exceptions:
    #   ValueError if option value has already been set.
    def __setitem__(self,key,value):
        try:
            val=self._values[key]
            raise ValueError("%s 'key' argument %s value already set: %s" \
                % (eloc(self,"__setitem__"),key,val))
        except KeyError:
            self._values[key]=value  

    def arg(self,arg):
        self._values[arg.name]=(arg.typ,arg.value)

    # Displays CINFO data
    def display(self):
        if self._cinfo is None:
            return
        self._cinfo.display()

    # Returns a list of strings for the requested infoid.  If the information id
    # has not been requested by the cinfo option, an empty list is supplied.  The
    # user should check for this case and determine how it should respond.
    #
    # The list of strings correspond to a line of text to be presented to the user.
    # Whether this is via a print() function or written to a file is up to the 
    # requesting tool.
    def cinfo(self,infoid):
        assert infoid in Tool.infoids,\
            "%s 'infoid' argument not a recognized cinfo option flag: %s" \
                % (eloc(self,"cinfo"),infoid)

        return self._cinfo.get(infoid,[])
        
    # Helper method for use of path options to open files.  This deals with upper/
    # lower case issues between configuration file options and environment variables
    #
    # Note: Alternatively a new object subclass of PathMgr could be developed for
    # use with configuration system paths.
    # Method Arguments:
    #   pathopt  The path option being selected (upper or lower case)
    #   filename The name of the file being opened
    #   mode     The mode in which the file is to be opened
    #   debug    Wether details of the ropen process are to be displayed.
    # Returns:
    #   the opened file object
    # Exceptions:
    #   ValueError if the pathopt option does not exist or PathMgr.ropen method can
    #              not open the file.
    def path_open(self,pathopt,filename,mode="rt",debug=False):
        assert isinstance(filename,str),\
            "%s 'filename' argument must be a string: %s" \
                % (eloc(self,"path_open"),filename)
        pathmgr=self[pathopt.lower()]
        assert isinstance(pathmgr,satkutil.PathMgr),\
            "%s option '%s' did not return a PathMgr object: %s" \
                % (eloc(self,"path_open"),pathopt,pathmgr)
        return pathmgr.ropen(filename,mode=mode,variable=pathopt.upper(),debug=debug)

#
#  +--------------------------+
#  |                          |
#  |    Configuration Tool    |
#  |                          | 
#  +--------------------------+
#

# The tool supplied by this module for simple setup of the configuration system and
# testing of it.  This is an example where the tool itself is integrated with the
# configuration system interface.
class config(Tool):
    # List of tools using the configuration system.  Must be defined before
    # the config object is created when this module is used as a tool
    tools=[]     # List of tool classes using the configuration system

    # Define a tool to the configuration system
    @staticmethod
    def deftool(toolcls):
        #assert issubclass(toolcls,Tool),\
        #    "%s - %s - 'toolcls' argument must be an sub class of Tool: %s" \
        #        % (this_module,"config.define()",toolcls.__name__)
        config.tools.append(toolcls)
    def __init__(self):
        # Build a list of tool objects that use the configuration system
        # Each must be inidividually imported when the config tool runs.

        self.tool_list=[]
        self.tool_names=[]
        self.tools={}
        for t in config.tools:
            print(t)
            toolo=t(test=True)

            try:
                self.tools[toolo.name]
                raise ValueError(\
                    "%s tool already defined to the configuration system: %s" \
                        % (eloc(self,"__init__"),toolo.name)) from None
            except KeyError:
                self.tools[toolo.name]=toolo
            self.tool_names.append(toolo.name)

        # Add myself to the list of tools
        name="config"
        self.tool_names.append(name)
        self.tools[name]=self
        # This needs to occur before the super class is initialized because the
        # superclass will call the tool_spec() method.  My spec() method needs 
        # the tool names so it can add them to the list of choices for my 
        # command-line argument --tool.

        # site.cfg set to allow writing
        super().__init__(name,ro=False,site=False)

    # Terminate the test normally
    # Method Argument:
    #   tool   the name of the tool as a string
    def __tool_test_complete(self,tool):
        print("--tool %s test: completed" % tool)
        sys.exit(0)

    def action_init(self):
        init=self.cli_ns.init
        verbose=self.cli_ns.verbose
        force=self.cli_ns.force
        if init is None:
            return

        if init=="satk":
            if verbose:
                print("\n--init satk: started ...")
            try:
                self.create_sitecfg(verbose=verbose,force=force)
            except ConfigError as ce:
                print("ERROR: %s" % ce)
                if verbose:
                    print("--init satk: failed\n")
                sys.exit(1)
            if verbose:
                print("--init satk: completed\n")
            sys.exit(0)

        elif init=="site":
            if verbose:
                print("\n--init site: started ...")
            try:
                self.create_site(verbose=verbose,force=force)
            except ConfigError as ce:
                print("ERROR: %s" % ce)
                if verbose:
                    print("--init site: failed\n")
                sys.exit(1)
            if verbose:
                print("--init site: completed\n")
            sys.exit(0)

        # This should not occur. option choices argument should filter out
        # unrecognized values.  If we get here it is a bug.
        raise ValueError("%s encountered unrecognized init option value: %s" \
            % (eloc(self,"action_init"),init))

    # Perform a simple test of the configuration system.  Use --cinfo to determine
    # output
    def action_test(self):
        tool=self.cli_ns.tool
        if tool is None:
            return
            
        print("\n--tool %s test: started ..." % tool)
        print("accessing configuration system")
        
        try:
            toolo=self.tools[tool]
        except KeyError:
            print("--tool %s test: failed, tool not located")
            return

        try:
            cfg=toolo.configure()  # Returns the cinfo object
        except ConfigError as ce:
            print("ERROR: %s" % ce)
            print("--tool %s test: failed\n" % tool)
            sys.exit(1)
        cfg.display()         # Display configuration information if requested

        # Gather options related to source option handling
        srcopt=toolo.spec._source  # Source option object
        if srcopt is None:
            print("tool %s does not utilize an input source" % toolo.name)
            self.__tool_test_complete(toolo.name)
            # Method does not return

        inopt=srcopt.inopt       # input file option name
        pathopt=srcopt.pathopt   # path option's name associated with input source

        if inopt is None:
            raise ValueError(\
                "%s tool %s source option '%s' does not provide an input file option" \
                    % (eloc(self,"action_test"),tool,srcopt.name))
        if pathopt is None:
            print("tool %s does not use a path associated with an input source" \
                % tool)
            print("file opening test bypassed")
            self.__tool_test_complete(toolo.name)
            # Method does not return

        try:
            inopt=cfg[inopt]
            # if successful, inopt is a file name or path string
        except KeyError:
            raise ValueError("%s tool %s source input file option '%s' not "
                "defined in its configuration" \
                    % (eloc(self,"action_test"),tool,inopt)) from None
        try:
            pathmgr=cfg[pathopt]
            # if successful pathmgr is an satkutil.PathMgr object
        except KeyError:
            raise ValueError("%s tool %s source input path option '%s' not "
                "defined in its configuration" \
                    % (eloc(self,"action_test"),tool,pathopt)) from None
        
        # Set verbose setting.  For config.py (the only tool that will not be
        # set for testing) use its verbose configuration option.  All others,
        # set verbose to True for more information.
        if not toolo.test:
            verbose=cfg["verbose"]
        else:
            verbose=True

        # Try to open the file using the defined path
        try:
            if verbose:
                print("opening with option %s: %s" % (pathopt,inopt))
            fo=cfg.path_open(pathopt,inopt,debug=verbose)
            fo.close()
        except ValueError as ve:
            print(ve)

        self.__tool_test_complete(tool)
        # Method does not return, config.py processing ends

    # Create the $SATK/config directory if needed
    def create_config_dir(self,verbose=False,force=False):
        satkcfg=self._satkcfg
        config_dir=satkcfg.directory
        dtype=satkcfg.dtype
        if not dtype in ["DA","NA"]:
            raise ValueError("%s unexpected $SATK/config directory %s file type: %s" \
                % (eloc(self,"create_satkcfg"),config_dir,dtype))
        if dtype == "DA":
            if verbose:
                print("directory exists: %s" % config_dir)
            return
        else:
            if verbose:
                print("directory does not exist: %s" % config_dir)
                print("creating directory: %s ..." % config_dir)
        os.mkdir(config_dir)
        if verbose:
            print("created directory: %s" % config_dir)

    # Create the site defaults in the site directory
    def create_site(self,verbose=False,force=False):
        # Build the ConfigFile object to interface with the configuration system
        self.create_cfg_parser()
        # Update Argument objects with site information as needed 
        self.parse_site()
        # Locate the site directory from its populated Option object
        self.site=self.find_site()  # Determine site directory location.

        # Validate site directory
        if self.site is None:
            raise ConfigError(msg="could not locate site directory")
        else:
            if verbose:
                print("found site directory: %s" % self.site)

        dtype=TextFile.ftype(self.site)
        if "A" not in dtype:
            raise ConfigError(\
                msg="site directory location must be an absolute path: %s" \
                    % self.site)
        if "D" not in dtype:
            raise ConfigError(msg="site directory location not a directory: %s" \
                % self.site)

        # Build tool default configuration files in the site directory
        for tool in self.tools.values():
            toolfile="%s.cfg" % tool.name
            toolcfg=TextFile(self.site,toolfile,ro=False)
            ftype=toolcfg.ftype
            if not ftype in ["NA","FA"]:
                raise ValueError(\
                    "%s unexpected tool default %s file type: %s" \
                        % (eloc(self,"create_site"),toolcfg.filepath,dtype))
            self.create_toolcfg(toolcfg,tool,verbose=verbose,force=force)

    # Create the SATK site.cfg file in the $SATK/config directory
    # Create the directory if needed.
    def create_sitecfg(self,verbose=False,force=False):
        satkcfg=self._satkcfg
        self.create_config_dir(verbose=verbose,force=force)

        # Locate where the site directory resides
        cli_site=self.cli_ns.satkcfg
        if cli_site is None:
            try:
                cli_site=self.env_raw["SATKCFG"]
            except KeyError:
                raise ConfigError(msg="neither command-line option --satkcfg nor "
                    "environment variable SATKCFG found, at least one required "\
                    "for SATK site directory location")

        if verbose:
            print("identified site diretory: %s" % cli_site)
            print("creating site.cfg file: %s ..." % satkcfg.filepath)
        
        cwduse=self.cli_ns.cwduse
        # Have to manually enforce default because we have not been through 
        # populate() method
        if cwduse is None:
            cwduse="omit"

        # config directory now exists
        lines=[]
        lines.append("# %s\n" % satkcfg.filepath)
        lines.append("# created by %s.py %s\n" % (self.name,time.asctime()))
        lines.append("\n")
        lines.append("[DEFAULT]\n")
        lines.append("# Specify default current working directory behavior\n")
        lines.append("cwduse = %s\n" % cwduse)
        lines.append("\n")
        lines.append("# Identify location of SATK site directory\n")
        lines.append("[SITE]\n")
        lines.append("%s=%s\n" % (Configuration.site[0],cli_site))

        # Write site.cfg file in config directory
        satkcfg.write(lines,verbose=verbose,force=force)

    # Returns the lines to be placed in the tool.cfg file
    # Method Argument:
    #   tfile   A TextFle object associated with the tool's configuration file
    #   tool    The tool's Tool object for access to default values and tool
    #           specific content.
    #   verbose Whether detailed output to be produced
    #   force   Whether an existing tool.cfg file is to be overwritten
    def create_toolcfg(self,tfile,tool,verbose=False,force=False):
        if verbose:
            print("creating tool configuration file: %s ..." % tfile.filepath)
        lines=[]
        lines.append("# %s\n" % tfile.filepath)
        lines.append("# created by %s.py %s\n" % (self.name,time.asctime()))
        lines.append("\n")
        
        # Create the DEFAULT section whether it has any options or not.  A
        # configuration file without any sections is seen as an error.
        lines.append("# Uncomment option default and alter its value for a "\
                "different site default\n")
        lines.append("[DEFAULT]\n")
        
        # Add defaults as comments to the DEFAULT section (if any)
        defaults=tool.spec.option_defaults()  # Retrieve default option dictionary
        #print("%s defaults: %s" % (eloc(self,"create_toolcfg"),len(defaults)))
        if len(defaults)>0:
            options=list(defaults.keys())
            options.sort()
            for opt in options:
                value=defaults[opt]
                lines.append("# %s = %s\n" % (opt,value))

        # Tool may have specific requirements for it default configuration file
        # so let is add its content now
        tool_data=self.tool_site()
        if len(tool_data)>0:
            lines.append("\n")
            lines.extend(tool_data)

        # Write the tool configuration file to the site directory
        tfile.write(lines,verbose=verbose,force=force)

    # Perform requested action for the config.py tool
    def process(self,debug=False):
        cli=self.cli_args()    # Retrieve the argparser Namespace object
        if __debug__:
            if debug:
                print("cli: %s" % cli)
        self.action_init()     # Perform config file initializaiton if requested
        self.action_test()     # Perform configuration tool test if requested

    # Defines the config.py specific content for the config.cfg file in the site
    # directory.  See the super class description of this method.
    def tool_site(self):
        return []

    # Define the config.py tool's configuration options
    def tool_spec(self):
        prog="%s.py" % self.name
        cfg=Configuration(prog,copyright,\
            "initializes or tests SATK configuration system")
        cfg.arg(Enable("verbose",short="v",full="verbose",\
            help="enable detailed output",cl=True,cfg=True))
        cfg.arg(Choices("init",full="init",choices=["satk","site"],default=None,
            help="perform an initialization of the satk.cfg file or the site "
            "directory",cl=True))
        self.option_satkcfg(cfg,cl=True)  # Standard satkcfg option
        self.option_cwd(cfg,cl=True)      # cwduse option value in SITE
        cfg.arg(Enable("force",full="force",\
            help="force overwriting of existing files by option --init",\
            cl=True,cfg=False))
        cfg.arg(Choices("tool",full="tool",choices=self.tool_names,\
            help="tool configuration being tested.",\
            cl=True,cfg=False))

        # Each tool that uses the configuration system should use these options:
        self.option_cfg(cfg)     # Standard cfg option definition
        self.option_cinfo(cfg)   # Standard configuration information option
        self.option_source(cfg,"source","input","tstpath",required=False,\
            shelp="tested tool's user provided input source section or FILENAME",\
            ihelp="identifies the tool's input file.  Option is of type FILENAME."\
                  "Defaults to option 'source'"\
            )

        # Add TSTPATH for testing path processing
        tst_path_dft=satkutil.satkdir("tools")
        cfg.arg(Path("tstpath",cfg=True,default=tst_path_dft))
        return cfg


if __name__ == "__main__":
    import satkutil
    satkutil.pythonpath("asma")       # Access asmconfig for assembler
    satkutil.pythonpath("tools/ipl")  # Access hexdump by assembler
    satkutil.pythonpath("tools/lang") # Access sopl by assembler
    import asmconfig                  # Access the ASMA configuration system usage
    config.deftool(asmconfig.asma)    # Add it to the list of possible tools
    tool=config().process()
