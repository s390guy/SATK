#!/usr/bin/python3
# Copyright (C) 2020 Harold Grovesteen
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


this_module="deck.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2020")

# Python imports
import argparse

# Setup PYTHONPATH
import satkutil      # Access environment variable handling
satkutil.pythonpath("tools/ipl")
import hexdump       # Access the dump utility function
import media         # Access tape medium
import recsutil      # Access tape records


#
# +-------------------+
# |                   |
# |   deck.py Tool    |
# |                   |
# +-------------------+
#

class DECKTOOL(object):

    errors=0   # Global error counter.  Controls whether output is produced

    # Manages relative paths using the DECKPATH environment variable
    pathmgr=satkutil.PathMgr(variable="DECKPATH",debug=False)

    def __init__(self,args):
        self.args=args

        # Whether output is produced (filepath) or suppressed (None)
        self.output=None       # Output command line filepath

        # The output file format: card (False), tape (True)
        self.tape=False

        self.dump=args.dump     # Whether input files are dumped in hex

        self.file_list=[]       # List of input file names from command line
        self.fileos=[]          # List of input FILE objects

    # Reads an input file using the DECKS environment variable for relative
    # paths.
    #
    # Method Arguments:
    #   filename   The file's name from the command line
    #   boot       Whether the file is from --boot (True) or source (False)
    #
    # Returns:
    #   a binary sequence of the file's content when successfully read.
    #   None if the file failed to be read.
    # Exceptions: None
    def read_file(self,filename,boot):

        try:
            fname,fo=DECKTOOL.pathmgr.ropen(\
                filename,mode="rb",variable="DECKS",debug=False)
        except ValueError as ve:
            DECKTOOL.errors+=1  # Increment global errors
            print("%s - %s" % this_module,ve)
            return None

        try:
            bin=fo.read()   # Read the entire file and return it
            fo.close()      # Then close it
        except IOError as ie:
            DECKTOOL.errors+=1   # Ignore future use of this object
            print("%s - %s" % this_module,ie)
            return None

        # Determine if binary file is a card deck or not
        records,extra = divmod(len(bin),80)
        if extra == 0:
            # Card deck
            rtn=CFILE(filename,fname,bin,cards=records,extra=extra,\
                boot=boot)
        else:
            # Generic binary file
            rtn=IFILE(filename,fname,bin,cards=records,extra=extra,\
                boot=boot)

        return rtn

    def run(self):
        args=self.args

        # Check --card and --tape command line options.
        if args.card and args.tape:
            print("%s - output suppressed: only --card or --tape option "\
                "may be used, not both" % this_module)
        else:
            # Only --card or --tape or neither specified in command-line
            if args.card:
                self.output=args.card
                self.tape=False
            elif args.tape:
                self.output=args.tape
                self.tape=True

        # Make --boot the first file when specified
        if args.boot:
            f=self.read_file(args.boot,True)
            if f:
                self.fileos.append(f)

        # Add source files to the input FILE object list.
        for filename in args.source:
            if args.boot:
                boot=True
            else:
                boot=False
            f=self.read_file(filename,False)
            if f:
                self.fileos.append(f)

        if len(self.fileos) == 0:
            print("%s - input files not present - procesing terminated"\
                % this_module)
            return

        # At this point each self.fileos object (CFILE/IFILE) contains the
        # binary data read or is ignored if a reading problem occurred.

        cfiles=0
        for fil in self.fileos:
            if isinstance(fil,CFILE):
                cfiles+=1
            else:
                DECKTOOL.errors+=1
                print("%s - input file not a card deck: %s" % (this_module,\
                    fil.fname))
            if self.dump:
                fil.dump()

        if DECKTOOL.errors:
            if self.output:
                print("%s - output processing suppressed due to errors: %s" \
                    % (this_module,DECKTOOL.errors))
            else:
                print("%s - encountered errors: %s" % (this_module,\
                    DECKTOOL.errors))
            return

        if not self.output:
            # No output requested quit
            return

     #
     #  Produce Output
     #
        if self.tape:
            # Create the Tape Output File object
            ofile=TFILE(self.output,self.fileos)
        else:
            # Create the Card Deck Output File object
            ofile=OFILE(self.output,self.fileos)

        # Output the file
        ofile.put()

#
# +-------------------------+
# |                         |
# |     Input File Types    |
# |                         |
# +-------------------------+
#

# Represents a successfully read input file
# Instance Arguments:
#    filename     The file's filename as supplied in the command line
#    fname        Actual file opened.  May be the same as filename
#    bin          The binary content of the file
#
#
class IFILE(object):

    def __init__(self,filename,fname,bin,cards=0,extra=0,boot=False):

        # These attributes are set by DECKTOOLS.__init__() method
        self.filename=filename   # Command-line filename of this file
        self.boot=boot           # Whether this is the --boot file

        # Python file attributes
        self.fname=fname         # Actual file path opened
        self.bin_data=bin        # Binary data read
        self.cards=cards         # Number of full cards in the binary file
        self.extra=extra         # Number of excess bytes in the binary file

        # File data:
        self.size=0       # Size of the file in bytes

        self.records,self.extra = divmod(len(self.bin_data),80)
        self.isdeck = self.extra == 0

    # Dump the binary file
    def dump(self):
        print(self.hdr(len(self.bin_data)))
        print(hexdump.dump(self.bin_data,indent="    "))

    # Return the binary file header
    def hdr(self,size):
        if self.boot:
            boot_lit="Boot "
        else:
            boot_lit=""
        return "Binary %sFile: %s   size: %s" % (boot_lit,self.fname,size)


class CFILE(IFILE):
    def __init__(self,filename,fname,bin,cards=0,extra=0,boot=False):
        super().__init__(filename,fname,bin,cards=cards,extra=extra,boot=boot)
        assert cards>0,"%s - CFILE.__init__() - 'card' argument must be "\
            "greater than 0: %s" % (this_module,card)

        self.isdeck=True         # This is a deck
        self.recs=cards          # Number of full cards in the deck
        self.records=[]          # list of byte sequences, one per card

    # Dump the card decks
    def dump(self):
        self.separate()
        print(self.hdr(len(self.bin_data)))
        for n,card in enumerate(self.records):
            cardn=n+1
            ncard="%s" % cardn
            print("Card %s" % ncard)
            print(hexdump.dump(card,indent="    "))

    # Return the card deck header
    def hdr(self,size):
        if self.boot:
            boot_lit="Boot "
        else:
            boot_lit=""
        return "Deck %sFile: %s  size: %s" % (boot_lit,self.fname,size)

    # Separates the binary file into individual records
    def separate(self,stats=True):
        if len(self.records) == self.recs:
            # Already separated
            return

        recs=[]
        bin=self.bin_data
        for ndx in range(0,len(bin),80):
            rec=bin[ndx:ndx+80]
            recs.append(rec)
        assert len(recs) == self.recs,"%s.CFILE.separate() - number of "\
            "separated cards (%s) must match number of full cards (%s)" \
                % (this_module,len(recs),self.recs)

        self.records=recs

#
# +--------------------------+
# |                          |
# |     Output File Types    |
# |                          |
# +--------------------------+
#

# Card Deck File Output
#
# Instance arguments:
#   filepath    The file path to which output card deck is written
#   fileos      List of CFILE object constituting the input decks
class OFILE(object):
    def __init__(self,filepath,fileos):
        self.filepath=filepath   # Output card deck's path
        self.fileos=fileos       # List of CFILE input instances

        self.output=self.combine()  # Combine input files for output

    # Returns the input decks combined into one object
    def combine(self):
        bin=bytes(0)
        for fil in self.fileos:
            bin+=fil.bin_data
        return bin

    # Output the combined Card Deck File
    def put(self):
        try:
            fo=open(self.filepath,"wb")
        except InputError as ie:
            print("%s - could not open for writing card deck - %s" \
                % (this_module,ie))
            return

        print("%s - writing output card deck: %s (size %s)" \
            % (this_module,self.filepath,len(self.output)))
        try:
            action="writing"
            fo.write(self.output)
            action="closing"
            fo.close()
        except IOError as ie:
            print("%s - could not complete %s of card deck - %s" \
                % (this_module,action,ie))

        # Output file creation complete
        return


# AWS Tape File Output
#
# Instance arguments:
#   filepath    The file path to which output card deck is written
#   fileos      List of CFILE object constituting the input decks
# AWS tape file output
class TFILE(OFILE):
    def __init__(self,filepath,fileos):
        super().__init__(filepath,fileos)

    # Returns the input decks combined into a list of 80-byte records
    # suitable for an AWS tape
    def combine(self):
        bin=[]
        for fil in self.fileos:
            fil.separate()
            bin.extend(fil.records)
        return bin

    # Output the combined AWS Tape File
    def put(self):
        device=media.device("3420")
        for rec in self.output:
            tape_rec=recsutil.tape(data=rec)
            device.record(tape_rec)

        print("%s - writing output AWS tape file: %s (80-byte records %s)" \
            % (this_module,self.filepath,len(self.output)))
        device.create(self.filepath)   # Write the AWS tape file


# PRESENTLY NOT USED
class STATS(object):
    def __init__(self,bin):
        self.bin=bin        # Binary sequence being inspected

        # Gathered stats
        self.size=len(bin)  # Size of the binary data in bytes
        self.ascii=0        # Number of ASCII characters detected
        self.ebcdc=0        # Number of EBCDIC characters detected
        self.other=0        # Number of bytes niether ASCII nor EBCDIC


#
# +----------------------------------------+
# |                                        |
# |   Command-Line Argument Definitions    |
# |                                        |
# +----------------------------------------+
#
# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,
        epilog=copyright,
        description=\
            "create an EBCDIC binary deck from multiple input binary decks")

  # Input arguments:

    # Source input files (Note: attribute source in the parser namespace will be
    # a list)
    parser.add_argument("source",nargs="+",metavar="FILENAME",\
        help="input binary source files")

    parser.add_argument("-b","--boot",metavar="FILENAME",\
        help="boot loader deck, when specified, always the first file in the "\
           "output. If omitted, the sequence of 'source' files prevails.")

    parser.add_argument("--dump",action="store_true",default=False,\
        help="produces hexadecimal dump of input files")

  # Output arguments:

    parser.add_argument("-c","--card",metavar="FILEPATH",\
        help="an output EBCDIC deck, a binary file without line terminations, "\
            "is created. If omitted no deck file is produced. May not be "\
            "used with --tape.")

    parser.add_argument("-t","--tape",metavar="FILEPATH",\
        help="an output EBCDIC deck in AWS tape file format is created. May "\
            "be used with --card. If omitted no AWS tape file is produced. "
            "May not be used with --card.")

    return parser.parse_args()


if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    tool=DECKTOOL(args)
    tool.run()
