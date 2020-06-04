#!/usr/bin/python3
# Copyright (C) 2014-2016 Harold Grovesteen
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

# This module provides a command line interface to the ASMA assembler.py module.

this_module="asma.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2014-2017")
# When changing this copyright update asma/asmconfig.copyright attribute.
# That copyright notice is the one actually printed when asma.py is run.

# Python imports
import sys
if sys.hexversion<0x03030000:
    raise NotImplementedError("%s requires Python version 3.3 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import time

# Remember import start times as early as possible for better time reporting.
import_start=process_start=time.process_time()
import_start_w=wall_start=time.time()

import argparse

# SATK imports:
# Setup PYTHONPATH
import satkutil
satkutil.pythonpath("asma")
satkutil.pythonpath("tools/lang")
satkutil.pythonpath("tools/ipl")

# ASMA imports
import asmconfig    # Usage by ASMA of the configuration system
import assembler    # The actual assembler


class ASMA(object):
    # Default MSL database file and CPU for recognized generic architecture
    archs={"s360": ("s360-insn.msl",  "s360"),
           "s370": ("s370-insn.msl",  "s370"),
           "s380": ("s380-insn.msl",  "s380"),
           "370xa":("s370XA-insn.msl","s370XA"),
           "e370": ("e370-insn.msl",  "e370"),
           "e390": ("e390-insn.msl",  "e390"),
           "s390": ("s390x-insn.msl", "s390"),
           "s390x":("s390x-insn.msl", "s390x"),
           "24":   ("all-insn.msl",   "24"),
           "31":   ("all-insn.msl",   "31"),
           "64":   ("all-insn.msl",   "64")}
    target_choices=\
        ["s360","s370","s380","370xa","e370","e390","s390","s390x","24","31","64"]
    def __init__(self,args,dm):
        
        self.dm=dm                # Global Debug Manager instance
        self.args=args            # Tool Config object
        self.args.display()       # If CINFO requested, display it
        self.clstats=args["stats"]   # Command-line statistics flag

        # Enable any command line debug flags
        for flag in args["debug"]:
            self.dm.enable(flag)

        self.aout=assembler.AsmOut(\
            deck=args["object"],\
            image=args["image"],\
            ldipl=args["gldipl"],\
            listing=args["listing"],\
            mc=args["store"],\
            rc=args["rc"],\
            vmc=args["vmc"])

        msl,cpu=self.target()
        mslpath=args["mslpath"]     # MSL PathMgr object
        cptrans,cpfile=self.code_page("94C")
        defn=self.defines()

        self.assembler=assembler.Assembler(cpu,msl,mslpath,self.aout,\
            addr=args["addr"],\
            case=args["case"],\
            debug=dm,\
            defines=defn,\
            dump=args["dump"],\
            error=args["error"],\
            nest=args["nest"],\
            otrace=args["oper"],\
            cpfile=cpfile,\
            cptrans=cptrans,\
            mcall=args["mcall"],\
            asmpath=args["asmpath"],\
            maclib=args["maclib"])

        self.source=args["input"]       # Source input file

        # Gather together time related data saved outside this object.
        self.process_start=process_start
        self.wall_start=wall_start
        self.import_start=import_start
        self.import_start_w=import_start_w
        self.objects_start=objects_start
        self.objects_start_w=objects_start_w

        # Timer information gathered during run() method
        self.assemble_end=None
        self.assemble_end_w=None
        self.out_end=None
        self.out_end_w=None

        # Save some of my own time information
        self.objects_end=time.process_time()
        self.objects_end_w=time.time()

    # Process --cp command-line argument
    def code_page(self,default):
        cp=self.args["cp"]
        if cp is None:
            return (default,None)
        return self.sep(cp,"--cp",optional=2)

    # Process -D command-line arguments
    def defines(self):
        lst=[]
        for d in self.args["symbol"]:
            dtuple=self.sep(d,"-D",optional=2)
            lst.append(dtuple)
        return lst

    # Execute the assembler
    def run(self):
        if self.clstats:
            stats=assembler.Stats
            stats.start("assemble_p")
            stats.start("assemble_w")

        try:
            result=self.assembler.assemble(filename=self.source)
        except Exception:
            # This attempts to give a clue where the error occurred
            print(self.assembler._error_passn())
            # Now output the exception information
            raise
            
        if result!=True:
            return  # return without outputting stats or any other output
            # Note: This is used when the initial input file can not be opened.
            # Any error message has already been printed but an exception is not
            # raised.

        self.assemble_end_w=time.time()
        self.assemble_end=time.process_time()

        self.out_start=time.process_time()
        self.out_start_w=time.time()
        # Retrieve the assembler.Image object containing the generated output
        img=self.assembler.image()

        # Output the requested output format(s)
        self.aout.write_listing(this_module,img.listing)
        self.aout.write_image(this_module,img.image)
        self.aout.write_deck(this_module,img.deck)
        self.aout.write_rc(this_module,img.rc)
        self.aout.write_vmc(this_module,img.vmc)
        self.aout.write_mc(this_module,img.mc)
        self.aout.write_ldipl(this_module,img.ldipl)

        # Provide the error report to the command-line if error-level is 2.
        # For error levels 0 or 1, error(s) have already been displayed.
        # For error level 3 errors are only reported in the listing
        if self.args["error"]==2:
            img.errors()

        self.out_end_w=time.time()
        self.out_end=time.process_time()

        # Report assembler stats if requested by the --stats argument
        if self.clstats:
            # Manually change to False to output stats from the assembler
            self.stats(update=True)

    # This method separates a name[=value] or name=value string into a tuple of one 
    # or two strings: (name,value) or (name,None)
    # Method Arguments:
    #   string   The command-line argument string being converted
    #   argument The command-line argument name for error reporting
    #   optional 1 indicates the first component is optional.  2 indicates the
    #            second component is optional and None indicates both are required.
    # Returns:
    #    (name,None)  One string and None when the value is optional and omitted
    # or (name,value) Two strings, one for the name and for for the value
    #
    # Used for --cp, --cpu and -D command-line arguments
    def sep(self,string,argument,optional=None):
        assert isinstance(string,str) and len(string)!=0,\
            "%s 'string' argument must be a non-empty string: %s" \
                % (assembler.eloc(self,"set",module=this_module),string)

        seps=string.count("=")
        if optional and seps==0:
            if optional==1:
                return (None,string)
            else:
                return (string,None)
        if seps!=1 or string[0]=="=":
            print("invalid %s argument ignored: %s" % (argument,string))

        name_value=string.split("=")
        return (name_value[0],name_value[1])

    # Report assembler stats
    def stats(self,update=True):
        stats=assembler.Stats
        if update:
            stats.update_start("process",self.process_start)
            stats.update_start("wall",self.wall_start)

            stats.update_start("import_p",self.import_start)
            stats.update_start("import_w",self.import_start_w)

            stats.update_start("objects_p",self.objects_start)
            stats.update_start("objects_w",self.objects_start_w)
            stats.update_stop( "objects_p",self.objects_end)
            stats.update_stop( "objects_w",self.objects_end_w)

            stats.update_stop( "assemble_p",self.assemble_end)
            stats.update_stop( "assemble_w",self.assemble_end_w)

            stats.update_start("output_p",self.out_start)
            stats.update_start("output_w",self.out_start_w)
            stats.update_stop( "output_p",self.out_end)
            stats.update_stop( "output_w",self.out_end_w)

        print(stats.report())

    # Determine target cpu and MSL database file from --target or --cpu
    def target(self):
        msl=None
        cpu=None
        args=self.args

        # Try the --target argument
        try:
            msl,cpu=ASMA.archs[args["target"]]
        except KeyError:
            pass

        # If present try --cpu argument
        arg_cpu=args["cpu"]
        if arg_cpu is not None:
            msl,cpu=self.sep(arg_cpu,"--cpu",optional=None)

        if msl is None or cpu is None:
            print("argument error: could not identify target instruction set by "
                "either --target or --cpu")
            sys.exit(1)

        return (msl,cpu)


# Parse the command line arguments and configuration files.
# Returns:
#   config.Tool object
def parse_args(dm=None):
    tool=asmconfig.asma()
    return tool.configure()

    # ALL OF THE FOLLOWING STATEMENTS MAY BE ELIMINATED
    parser=argparse.ArgumentParser(prog="asma.py",
        epilog=copyright, 
        description="from assembler source create a bare-metal usable file")

    # Source input file (Note: attribute source in the parser namespace will be a list)
    parser.add_argument("source",nargs=1,\
        help="input assembler source path.  Relative path requires ASMPATH "
             "environment variable directory search order.")

    parser.add_argument("-t","--target",default="24",metavar="ISA",\
        choices=ASMA.target_choices,\
        help="target instruction set architecture.  ISA may be: s360, s370, s380, "
             "s370xa, e370, e390, s390, s390x, 24, 31, or 64.  Defaults to 24.")

    # Override MSL maximum address size
    # May be specified in a local configuration
    parser.add_argument("-a","--addr",type=int,metavar="SIZE",\
        choices=[16,24,31,64],\
        help="overrides target CPU maximum address size (in bits) in the listing.  "
             "SIZE may be 16, 24, 31 or 64")

    # Specify error handling level
    # May be specified in a local configuration
    parser.add_argument("-e","--error",type=int,metavar="LEVEL",\
        choices=[0,1,2,3],default=2,\
        help="specifies error handling level.  Defaults to 2")

    # Specify the initial XMODE PSW format
    psw_formats=["S","360","67","BC","EC","380","XA","E370","E390","Z","none"]
    parser.add_argument("--psw",metavar="FORMAT",
        choices=psw_formats,\
        help="set the initial XMODE PSW format.  Overrides the value supplied by "
             "the target CPU definition.  FORMAT may be S, 360, 67, BC, EC, 380, XA, "
             "E370, E390, Z, or none (none disables the PSW directive)")

    # Specify the initial XMODE CCW format
    parser.add_argument("--ccw",metavar="FORMAT",choices=["0","1","none"],
        help="set the initial XMODE CCW format. Overrides the value supplited by "
             "the target CPU definition. FORMAT may be 0, 1 or none (none disables "
             "the CCW directive)")

    # Define a global SETC symbol via the comnand line
    parser.add_argument("-D",metavar="SYMBOL[=VALUE]",action="append",\
        default=[],\
        help="define a global read-only SETC symbolic variable (without the leading "
             "ampersand) to a value")

    # Dump the completed CSECT's, region's and image
    # May be specified in a local configuration
    parser.add_argument("-d","--dump",action="store_true",default=False,\
        help="listing provides the image content in storage dump format.")

    # Set macro call printing option
    parser.add_argument("-m","--mcall",action="store_true",default=False,\
        help="Include inner macro statements during PRINT ON listing option. "
             "By default inner macro statements are suppressed")

    # Generic list directed IPL option
    parser.add_argument("-g","--gldipl",metavar="FILEPATH",
        help="identifies the location of the list directed IPL file. All related "
             "files are written to the same diretory. If omitted, no files are "
             "created")

    # Path and filename of the written binary image file
    parser.add_argument("-i","--image",metavar="FILEPATH",
        help="binary image file containing content.  If omitted, no file is created.")

    # Machine Specification Language database source file
    parser.add_argument("-l","--listing",metavar="FILEPATH",
        help="assembly listing file.  If omitted, no listing file is created.")

    # Object Deck file name
    parser.add_argument("-o","--object",metavar="FILEPATH",
        help="loadable object deck file with assembled content.  If omitted, an "
             "object deck is not created")

    # Hercules RC script file
    parser.add_argument("-r","--rc",metavar="FILEPATH",
        help="Hercules RC script file with assembled content.  If omitted, a script "
             "file is not created.")

    # STORE command file
    parser.add_argument("-s","--store",metavar="FILEPATH",
        help="STORE command file with assembled content.  If omitted, a command file "
             "is not created.")

    # virtual machine STORE ommand file 
    parser.add_argument("-v","--vmc",metavar="FILEPATH",
        help="virtual machine STORE command file with assembled content.  If omitted, "
             "a command file is not created.")

    # Set case sensitivity
    parser.add_argument("--case",action="store_true",default=False,\
        help="Enable case sensitivity for labels, symbolic variables, and sequence "
             "symbols.  Defaults to case insensitive")

    # Enable statistics reporting
    # May be specified in a local configuration
    parser.add_argument("--stats",action="store_true",default=False,\
        help="enables statististics reporting.")

    # Specify the code page translation
    parser.add_argument("--cp",metavar="TRANS[=FILE]",default=None,\
        help="specify the code page translation and, if provided, the code page file "\
             "containing it. Defaults to '94C' in the default code page file")

    # Machine Target
    parser.add_argument("--cpu",metavar="MSLFILE=CPU",\
        help="identifies the CPU and its MSL file targeted by the assembly. MSLFILE "
             "must be found in the default MSL directory or a directory specified by "
             "the MSLPATH environment variable.")

    # Maximum depth of nested input sources.
    # May be specified in a local configuration
    nest_default=20
    parser.add_argument("--nest",type=int,default=nest_default,metavar="DEPTH",
        help="maximum depth of nested input sources (default %s)." % nest_default)

    # Build list of instructions or assembler directives to trace
    parser.add_argument("--oper",action="append",default=[],\
        help="indicate the operation by name to trace (may be used multiple times)")

    # Build list of passes to trace
    parser.add_argument("--pas",action="append",type=int,default=[],metavar="N",\
        help="indicate by number a pass to be traced (may be used multiple times) "
             "Either 1 or 2 may be specified.")

    # Add debug options from Debug Manager
    dm.add_argument(parser,"--debug")

    return parser.parse_args()


if __name__ == "__main__":
    objects_start=time.process_time()
    objects_start_w=time.time()

    dm=assembler.Assembler.DM()
    tool=parse_args(dm=None)  # config.py prints copyright notice
    ASMA(tool,dm).run()
