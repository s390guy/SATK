#!/usr/bin/python
# Copyright (C) 2012 Harold Grovesteen
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

# This tool wraps an ELF executable into an 80-byte card image object deck.
# The intent of this tools is to allow a traditional object deck boot program
# to load into storage the ELF executable and pass control to it.  This is an 
# alternative to the IPL ELF ABI Supplement standard supported by iplmed.py for 
# loading an IPL ELF.  Any boot program that understands the object deck format
# may be used to pass control to the loaded ELF executable.
#
# This approach constrains the loaded ELF executable to the first 16-megabytes of
# storage.  It also requires the loaded ELF to change architecture mode if a mode
# is different than that set by the IPL function is required.
#
# See the samples/iplelf/card or samples/textseg/card directories for sample loaders 
# that boot object decks created by this tool.  These samples may be used as
# values to the --boot argument.

from PyOBJBuilder import *  # Object deck builder
from hexdump import *       # Access the dump tool
import argparse             # command line argument parser
import PyELF                # ELF inspection tool
import PyIPLELF             # IPL ELF wrapper
import sys

class ExeInObj(object):
    def __init__(self,options,debug=False):
        self.opts=options
        self.debug=self.opts.debug or debug   # Set debugging option
        if self.debug:
            print("exeinobj.py: debug: cli arguments:")
            for x in sys.argv:
                print("exeinobj.py: debug:    %s" % x)
        self.files=self.opts.exefile   # List of executables destined for deck
        self.boot=self.opts.boot       # Boot loader file or None
        self.csect=self.opts.csect[:min(8,len(self.opts.csect))]
        self.elfs=[]                   # List of PyIPLELF instances (openelfs method)
        self.modules=[]                # List of modules as strings
        self.amode=None                # Entered modules address mode (modes method)
        self.rmode=None                # Entered modules architecture (modes method)
        
        # Set entered object module's desired address mode
        #if self.opts.amode is None:
        #    self.amode=24
        #else:
        #    self.amode=self.opts.amode
            
        # Set entered object module's desired residency mode
        #if self.opts.rmode is None:
        #    self.rmode=24
        #else:
        #    self.rmode=self.opts.amode
        
        self.seqno=1                   # Running sequence number of deck in 72-80
        # Establish the constant, if any, to be used starting in column 72
        if self.opts.seq is None:
            self.sequence=""
        else:
            self.sequence=self.opts.seq[:min(4,len(self.opts.seq))]
        
        # Build list of PyIPLELF instances for command executables
        for f in range(len(self.files)):
            filename=self.files[f]
            if self.debug:
                print("exeinobj.py: debug: ELF %s: %s" % (f+1,filename))
            elf=PyELF.elf(filename)
            iplelf=PyIPLELF.PyIPLELF(elf,self.debug)
            
            # Force entire ELF to be booted for first executable in command line
            if (f==0) and (iplelf.elf_itself is None) and (not self.opts.bootseg):
                iplelf.elfseg()
                
            self.elfs.append(iplelf)
            if self.debug:
                print("exeinobj.py: debug:        %s" % iplelf)
              
    def build_elf(self,exe,csect,amode=24,rmode=24):
        # Adds the module to the module list.  
        # Each module is a list of 80-byte strings.
        if not isinstance(exe,PyIPLELF.PyIPLELF):
            raise ValueError("exeinobj.py: internal: elf not a PyIPLELF instance: %s"\
                % exe)
        obj=OBJBuilder()
        seg=exe.get_elf()   # Fetch the ELF as a segment
        
        # Create the START section 
        obj.SD(csect,address=seg.address,length=seg.size,amode=amode,rmode=rmode)
        
        # Put the ELF into the START section
        obj.TXT(text=seg.segment,address=seg.address,csect=csect)
        
        # Build the ESD records from the items
        obj.ESD()
        
        # Complete with the entry address
        obj.END(entry=exe.entry(),csect=csect,idr=self.build_idr(obj))
        if self.debug:
            obj.display_idrs()
            obj.display_esds()
            obj.display_esd()
            obj.display_txt()
            obj.display_end()
            
        adeck=obj.deck(seq=self.sequence,number=self.seqno)
        if self.debug:
            for x in adeck:
                print("\n%s" % dump(x))
        self.modules.append(adeck)
        self.seqno+=len(adeck)

    def build_idr(self,builder):
        idrdata=[]
        if self.opts.binutils is not None:
            gas_data=("GNU as",self.opts.binutils)
            idrdata.append(gas_data)
        if self.opts.gcc is not None:
            gcc_data=("GNU gcc",self.opts.gcc)
            idrdata.append(gcc_data)
        for x in idrdata:
            version=x[1].split(".")
            if len(version)>=2:
                ver=version[0]
                rel=version[1]
            elif len(version)==1:
                ver="00"
                rel=version[0]
            else:
                ver="00"
                rel="00"
            builder.IDR(proc=x[0],ver=ver,rel=rel)

    def build_segments(self,exe,csect,amode=24,rmode=24):
        # Adds the module to the module list.  
        # Each module is a list of 80-byte strings.
        if not isinstance(exe,PyIPLELF.PyIPLELF):
            raise ValueError("exeinobj.py: internal: elf not a PyIPLELF instance: %s"\
                % exe)
        obj=OBJBuilder()
        
        segments=[]
        segments.append(exe.sego("TEXT"))   # Get the TEXT segment
        segments=self.build_forced(exe,"CCW",self.opts.ccw,segments)
        segments=self.build_forced(exe,"LOADER",self.opts.lodr,segments)
        segments=self.build_forced(exe,"LOWC",self.opts.lowc,segments)
        # segments is now a list of IPLSegment instances to be included in deck
        
        lowaddr=0x1000000
        hiaddr=0
        for x in segments:
            lowaddr=min(lowaddr,x.address)
            hiaddr=max(hiaddr,x.address+x.size)
        # Create the START section 
        obj.SD(csect,address=lowaddr,length=hiaddr-lowaddr,amode=amode,rmode=rmode)
        
        for x in segments:
            # Put the ELF into the START section
            obj.TXT(text=x.segment,address=x.address,csect="START")
            
        # Build the ESD records from the items
        obj.ESD()
        
        # Complete with the entry address
        idr=self.build_idr()
        obj.END(entry=exe.entry(),csect="START",idr=self.build_idr(obj))
        if self.debug:
            obj.display_idrs()
            obj.display_esds()
            obj.display_esd()
            obj.display_txt()
            obj.display_end()
       
        adeck=obj.deck(seq=self.sequence,number=self.seqno)
        if self.debug:
            for x in adeck:
                print("\n%s" % dump(x))
        self.modules.append(adeck)
        self.seqno+=len(adeck)
        
    def build_forced(self,exe,seg,opt,lst):
        try:
            segment=exe.sego(seg)
            if opt:
                lst.append(segment)
        except KeyError:
            pass
        return lst
        
    def check_deck(self, deck,cli_parm,filename):
        if len(deck)==0:
            print("exeinobj.py: warning: %s file empty: %s" % (cli_parm,filename))
            return
        if (len(deck) % 80)!=0:
            print("exeinobj.py: error: %s file not 80-byte card images: %s"\
                % (cli_parm,filename))
            sys.exit(2)
        
    def generate(self):
        # This method converts the IPL ELF executables into an object deck
        # If command line option --dryrun specified, the deck will be suppressed.
        
        # There are two cases for the first exectable in the command line:
        #       Wrap the object deck around the ELF
        #       Wrap the object deck around specific segments
        # There is one case for the other executables:
        #       Wrap the object deck around the ELF
        for x in range(len(self.elfs)):
            if self.debug:
                print("exeinobj.py: debug: Building module for ELF %s" % (x+1))
            exe=self.elfs[x]
            
            if x==0:
                # The first executable in the list is the entered executable
                # It has special handling for its construction and is always
                # identified by the START control section.
                self.modes(exe)
                if self.opts.bootseg:
                    try:
                        self.build_segments(exe,\
                            csect=self.csect,amode=self.amode,rmode=self.rmode)
                    except StandardError,err:
                        if self.debug:
                            print err
                        print("exeinobj.py: abort: object deck conversion failed "\
                            "for executable: %s" % exe.filename)
                        sys.exit(2)
                else:
                    try:
                        self.build_elf(exe,\
                            csect=self.csect,amode=self.amode,rmode=self.rmode)
                    except StandardError,err:
                         if self.debug:
                             print err
                         print("exeinobj.py: abort: object deck conversion failed "\
                             "for executable: %s" % exe.filename)
                         sys.exit(2)
            else:
                # All executables that follow the first executable will have the
                # entire ELF loaded into storage and will be placed in the module's
                # MODULE control section.
                try:
                    obj=self.build_elf(exe,\
                        csect="MODULE",amode=exe.amode,rmode=exe.rmode)
                except StandardError,err:
                    if self.debug:
                        print err
                    print("exeinobj.py: abort: object deck conversion failed "\
                          "for executable: %s" % exe.filename)
                    sys.exit(2)

        if self.opts.dryrun:
            # If --dryrun specified just return now, done
            return
        self.write_deck()
        
    def modes(self,exe):
        # Set the amode and rmode from the executable if not overriden by a command
        # line option.
        if self.opts.amode is None:
            self.amode=exe.amode
        else:
            self.amode=self.opts.amode
        if self.opts.rmode is None:
            self.rmode=exe.rmode
        else:
            self.rmode=self.opts.rmode
    
    def write_deck(self):
        deck=""
        deckfile=self.opts.deck
        if deckfile is None:
            return

        try:
            fo=open(deckfile,"wb")
        except IOError:
            print("exeinobj.py: error: could not open --deck file for writing:" \
                "%s" % self.opts.deck)
            sys.exit(2)
        # Output --boot file to the deck if specified
        if self.opts.boot is not None:
            try:
                boot=open(self.opts.boot,"rb")
            except IOError:
                print("exeinobj.py: could not open for reading --boot file: %s" \
                    % self.opts.boot)
                sys.exit(2)
            try:
                deck=boot.read()
            except IOError:
                print("exeinobj.py: could not read --boot file: %s" % self.opts.boot)
                sys.exit(2)
            try:
                boot.close()
            except IOError:
                print("exeinobj.py: could not close --boot file: %s" \
                    % self.opts.boot)
                sys.exit(2)
            self.check_deck(deck,"--boot",self.opts.boot)

        # Add modules to the deck
        for x in self.modules:
            module="".join(x)
            deck+=module
        self.check_deck(deck,"--deck",deckfile)

        # Write the --deck file
        try:
            fo.write(deck)
        except IOError:
            print("exeinobj.py: error: while writing --deck file: %s" % self.opts.deck)
            sys.exit(2)
        try:
            fo.close()
        except IOError:
            print("exeinobj.py: error: while closing --deck file: %s" % self.opts.deck)
            sys.exit(2)
        
def parse_args():
    desc="Creates an object card deck containing one or more ELF executables, "\
         "preceded by an optional card boot loader"
    epi="Optional arguments --ccw, --lowc, and --lodr are only meaningful if "\
        "argument --bootseg has been specified.  The number of executable files "\
        "specified must be compatible with the boot loader used to load the deck.  "\
        "Executables are placed in the object deck in the sequence in which they "\
        "are placed in the command line.  By default the first executable will be"\
        "tagged for entry by providing a START control section."
    parser=argparse.ArgumentParser(description=desc,epilog=epi)
    parser.add_argument("exefile",\
        help="source ELF executable file(s)",nargs="+")
    parser.add_argument("--deck",\
        help="created object card deck emulating file",required=True)
    parser.add_argument("--seq",default=None,\
        help="1-4 letter string starting in column 72 of the deck for card "\
             "identification, otherwise columns 72-80 will contain a sequence "\
             "starting with 1")
    parser.add_argument("--binutils",default=None,\
        help="Binutils release used to produce ELF executable")
    parser.add_argument("--gcc",default=None,\
        help="GCC release used to produce the ELF executable")
    parser.add_argument("--amode",type=int,choices=[24,31,64],
        help="object deck address mode.  Address mode specifies the address mode "\
             "expected by the object deck when entered.  By default the machine "\
             "and ELF class determine the amode")
    parser.add_argument("--rmode",type=int,choices=[24,31,64],
        help="object deck address mode.  Residency mode specifies the architecture "\
             "in which the deck expects to operate.  By default the machine "\
             "and ELF class determine the rmode")
    parser.add_argument("--boot",default=None,\
        help="file name of boot loader, prepended to the object deck, that loads "\
             " and enters the loaded object deck")
    parser.add_argument("--bootseg",action="store_true",default=False,\
        help="include in the object deck only program segments from the first "\
              "exefile, not the entire executable")
    parser.add_argument("--csect",default="START",\
        help="specify the module CSECT name of the first executable")
    parser.add_argument("--ccw",action="store_true",default=False,\
        help="force inclusion of a CCW segment if present, othewise ignore segment")
    parser.add_argument("--lowc",action="store_true",default=False,\
        help="force inclusion of a LOWC segment if present, otherwise ignore segment")
    parser.add_argument("--lodr",action="store_true",default=False,\
        help="force inclusion of a LOADER segment if present, otherwise ignore "\
             "segment")
    parser.add_argument("--dryrun",action="store_true",default=False,\
        help="Suppresses writing of actual deck output")
    parser.add_argument("--debug",action="store_true",default=False,\
        help="enable debugging output")
    return parser.parse_args()   

if __name__=="__main__":
    print("exeinobj.py, Copyright, Harold Grovesteen, 2011")
    obj=ExeInObj(parse_args())
    obj.generate()
    sys.exit(0)
    