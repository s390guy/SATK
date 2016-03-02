#!/usr/bin/python3
# Copyright (C) 2015,2016 Harold Grovesteen
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

# This module integrates the configuration system into the ASMA launcher script.

this_module="%s.py" % __name__

# ASMA displayed copyright information.  This must match the copyright in asma.py
copyright="asma.py Copyright (C) %s Harold Grovesteen" % "2014-2016"

# Python imports: None
# ASMA/SATK imports:
import assembler   # access an assembler static method
import config      # access the configuration system
import satkutil    # access SATK path functions.

class asma(config.Tool):
    target_choices=\
        ["s360","s370","s380","370xa","e370","e390","s390","s390x","24","31","64"]

    # Formatted string of environment variables used by ASMA
    variables=\
"""Directory search order environment variables (upper case) or config options (lower case):
    ASMPATH  Locates the initial source file and COPY directive files.
    MACLIB   Locates macro library definitions.
    MSLPATH  Loactes Machine Specification Language files.  Defaults to asma/msl.
    CDPGPATH Locates user supplied code page definitions.
"""

    def __init__(self,test=False):
        super().__init__("asma",ro=False,site=False,test=test)

    def tool_spec(self):
        prog="%s.py" % self.name
        
        # Return to full usage when epilog not shown whithout help
        # Seems to be an error with Python 3.4.1
        #epilog="%s\n%s\n%s" % (asma.variables,config.CINFO.cinfo_options(),copyright)
        epilog=copyright
        cfg=config.Configuration(prog,epilog,\
            "from assembler source create a bare-metal usable file")

        cfg.arg(config.Choices("target",short="t",full="target",metavar="ISA",\
            choices=asma.target_choices,default="24",\
            help="target instruction set architecture.  ISA may be: s360, s370, s380, "\
                 "s370xa, e370, e390, s390, s390x, 24, 31, or 64.  Defaults to 24.",\
            cl=True,cfg=True))

        # Override MSL maximum address size
        # May be specified in a local configuration
        cfg.arg(config.IntChoices("addr",short="a",full="addr",metavar="SIZE",\
            choices=["16","24","31","64"],\
            help="overrides target CPU maximum address size (in bits) in the "\
                 "listing. SIZE may be 16, 24, 31 or 64.",\
            cl=True,cfg=True))

        # Specify error handling level
        # May be specified in a local configuration
        cfg.arg(config.IntChoices("error",short="e",full="error",metavar="LEVEL",\
            choices=["0","1","2","3"],default="2",\
            help="specifies error handling level.  Defaults to 2.",\
            cl=True,cfg=True))

        # Specify the initial XMODE PSW format
        psw_formats=["S","360","67","BC","EC","380","XA","E370","E390","Z","none"]
        cfg.arg(config.Choices("psw",full="psw",metavar="FORMAT",\
            choices=psw_formats,\
            cl=True,cfg=True))

         # Specify the initial XMODE CCW format
        cfg.arg(config.Choices("ccw",full="ccw",metavar="FORMAT",\
            choices=["0","1","none"],\
            help="set the initial XMODE PSW or CCW format. Overrides the value "
                 "supplited by the target CPU definition.",\
            cl=True,cfg=True))

        # Define a global SETC symbol via the comnand line
        cfg.arg(config.ListArg("symbol",short="D",metavar="SYMBOL[=VALUE]",\
            help="define a global read-only SETC symbolic variable (without the "
                 "leading ampersand) to a value.",\
            cl=True,cfg=True))

        # Dump the completed CSECT's, region's and image
        cfg.arg(config.Enable("dump",short="d",full="dump",\
            help="listing provides the image content in storage dump format.",\
            cl=True,cfg=True))

        # Set macro call printing option
        cfg.arg(config.Enable("mcall",short="m",full="mcall",\
            help="Include inner macro statements during PRINT ON listing option. "
                 "By default inner macro statements are suppressed.",\
            cl=True,cfg=True))

        # Generic list directed IPL option
        cfg.arg(config.Option_SV("gldipl",short="g",full="gldipl",\
            metavar="FILEPATH",\
            help="identifies the location of the list directed IPL file. All related "
                 "files are written to the same diretory. If omitted, no files are "
                 "created.",
            cl=True,cfg=True))

        # Path and filename of the written binary image file
        cfg.arg(config.Option_SV("image",short="i",full="image",metavar="FILEPATH",\
            help="binary image file containing content.  If omitted, no file is "
                 "created.",\
            cl=True,cfg=True))

        # Assembling listing
        cfg.arg(config.Option_SV("listing",short='l',full="listing",\
            metavar="FILEPATH",\
            help="assembly listing file.  If omitted, no listing file is created.",\
            cl=True,cfg=True))

        # Object Deck file name
        cfg.arg(config.Option_SV("object",short="o",full="object",\
            metavar="FILEPATH",\
            help="loadable object deck file with assembled content.  If omitted, an "
                 "object deck is not created.",\
            cl=True,cfg=True))

        # Hercules RC script file
        cfg.arg(config.Option_SV("rc",short="r",full="rc",metavar="FILEPATH",\
            help="Hercules RC script file with assembled content.  If omitted, "
                 "a script file is not created.",\
            cl=True,cfg=True))

        # STORE command file
        cfg.arg(config.Option_SV("store",short="s",full="store",\
            metavar="FILEPATH",\
            help="STORE command file with assembled content.  If omitted, a "
                 "command file is not created.",\
            cl=True,cfg=True))

        # virtual machine STORE ommand file
        cfg.arg(config.Option_SV("vmc",short="v",full="vmc",metavar="FILEPATH",\
            help="virtual machine STORE command file with assembled content. If "
                 "omitted, a command file is not created.",\
            cl=True,cfg=True))

        # Set case sensitivity
        cfg.arg(config.Enable("case",full="case",\
            help="Enable case sensitivity for labels, symbolic variables, and "
            "sequence symbols.  Defaults to case insensitive.",\
            cl=True,cfg=True))

        # Enable statistics reporting
        cfg.arg(config.Enable("stats",full="stats",\
            help="enables statististics reporting.",\
            cl=True,cfg=True))

        # Specify the code page translation
        cfg.arg(config.Option_SV("cp",full="cp",metavar="TRANS[=FILE]",\
            help="specify the code page translation and, if provided, the code page "
                 "file containing it. Defaults to '94C' in the default code page "
                 "file.",\
            cl=True,cfg=True))

        # Machine Target
        cfg.arg(config.Option_SV("cpu",full="cpu",metavar="MSLFILE=CPU",\
            help="identifies the CPU and its MSL file targeted by the assembly. "
                 "MSLFILE must be found in the default MSL directory or a directory "
                 "specified by the MSLPATH environment variable.",\
            cl=True,cfg=True))

        # Maximum depth of nested input sources.
        # May be specified in a local configuration
        nest_default="20"
        cfg.arg(config.Decimal("nest",full="nest",default=nest_default,\
            metavar="DEPTH",
            help="maximum depth of nested input sources (default %s)." % nest_default,\
            cl=True,cfg=True))

        # Build list of instructions or assembler directives to trace
        cfg.arg(config.ListArg("oper",full="oper",metavar="OPER",\
            help="indicate the operation by name to trace (may be used multiple "
                 "times).",\
            cl=True,cfg=True))

        # Add debug options from Debug Manager
        dm=assembler.Assembler.DM()
        choices,help_str=dm.build_arg()
        cfg.arg(config.ListArg("debug",full="debug",metavar="OPTION",\
            choices=choices,help=help_str,cl=True,cfg=True))

        # Each tool that uses the configuration system should use these options:
        self.option_cfg(cfg)     # Standard cfg option definition
        self.option_cinfo(cfg)   # Standard configuration information option
        self.option_source(cfg,"source","input","asmpath",required=True,\
            shelp="identifies the input assembler source file. Option is of type "\
                  "FILENAME. Defaults to the value of the configuration option "\
                  "'input'.",\
            ihelp="input source file name"\
            )
        
        # ENVIRONMENT VARIABLE USAGE
        self.option_satkcfg(cfg)      # Standard satkcfg option
        self.option_cwd(cfg)          # cwduse option value in SITE
        cfg.arg(config.Path("asmpath",cfg=True))
        cfg.arg(config.Path("maclib",cfg=True))
        cfg.arg(config.Path("mslpath",default=satkutil.satkdir("asma/msl")))
        cfg.arg(config.Path("cdpgpath",cfg=True))
        
        return cfg