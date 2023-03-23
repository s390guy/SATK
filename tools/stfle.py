#!/usr/bin/python3
# Copyright (C) 2023 Harold Grovesteen
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

# This module provides services to manage and understand STFLE settings and
# analyze requirements.

this_module="stfle.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2023")

# Python imports
import sys
if sys.hexversion<0x03040500:
    raise NotImplementedError("%s requires Python version 3.4.5 or higher, "
        "found: %s.%s" % (this_module,sys.version_info[0],sys.version_info[1]))
import argparse       # Access command-line parser


#
#  +-------------------------+
#  |                         |
#  |   Facility Indicators   |
#  |                         |
#  +-------------------------+
#

# Facility Indicators used by various s390x systems.  The fac_ind_data string
# is used to contain the facility indicator bit and a verbal description of
# the indicator's meaning.  Add new indicator bit assignments to this string.
# Fac_Bits class instance reads the facility bit assignements and meanings,
# creating the fac_bits module attribute.
#
# Each line of the text starts with the assigned facility bit number being
# assigned, separated by one or more spaces from the following description.
# The entire description must be in a single line of text.  Refer to the
# Fac_Bits class for details of how the facility indicator definitions are
# processed and the resulting Python structures are used for decoding of
# the facility indicators supplied to the STFLE tool.

fac_ind_data=\
'''0 "N3" instructions installed
1 z/Architecture mode installed
2 z/Architecture mode active
3 DAT-enhancement 1
4 IDTE selective clear of TLB segment-table entries
5 IDTE selective clear of TLB region-table entries
6 ASN-and-LX reuse
7 store-facility-list-extended
8 enhanced-DAT 1
9 sense-running-status
10 conditional-SSKE
11 configuration-topology
12 IBM internal use only
13 IPTE-range
14 nonquiescing key-setting
15 IBM internal use only
16 extended-translation 2
17 message-security assist
18 long-displacement
19 long-displacement facility has high performance
20 HFP-multiply-and-add/subtract
21 extended-immediate
22 extended-translation 3
23 HFP-unnormalized-extension
24 ETF2-enhancement
25 store-clock-fast
26 parsing-enhancement
27 move-with-optional-specifications
28 TOD-clock-steering
30 ETF3-enhancement
31 extract-CPU-time
32 compare-and-swap-and-store
33 compare-and-swap-and-store 2
34 general-instructions-extension
35 execute-extensions
36 enhanced-monitor
37 floating-point extension
38 order-preserving-compression
39 IBM internal use only
40 load-program-parameters
41 floating-point-support-enhancement
42 DFP (decimal-floating-point)
43 DFP facility has high performance
44 PFPO instruction
45 distinct-operands, fast-BCR-serialization, highword, and population-count facilities, the interlocked-access facility 1, and the load/store-on-condition facility 1
46 IBM internal use only
47 CMPSC-enhancement
48 decimal-floating-point zoned-conversion
49 execution-hint, load-and-trap, and processor assist facilities, and the miscellaneous-instruction extensions facility 1 are installed in the z/Architecture architectural mode
50 constrained transactional-execution
51 local-TLB-clearing
52 interlocked-access 2
53 load/store-on-condition 2 and load-and zero-rightmost-byte
54 entropy-encoding compression
55 IBM internal use only
57 message-security-assist extension 5
58 miscellaneous-instruction-extensions 2
59 IBM internal use only
60 IBM internal use only
61 miscellaneous-instruction-extensions 3
62 IBM internal use only
63 IBM internal use only
64 IBM internal use only
65 IBM internal use only
66 reset-reference-bits-multiple
67 CPU-measurement counter
68 CPU-measurement sampling
69 IBM internal use only
70 IBM internal use only
71 IBM internal use only
72 IBM internal use only
73 transactional-execution
74 store-hypervisor-information
75 access-exception-fetch/store-indication
76 message-security-assist extension 3
77 message-security-assist extension 4
78 enhanced-DAT 2
80 decimal-floating-point packed-conversion
81 PPA-in-order
82 IBM internal use only
128 IBM internal use only
129 vector facility for z/Architecture
130 instruction-execution-protection
131 side-effect-access and enhanced suppression-on-protection
133 guarded-storage
134 vector packed decimal
135 vector enhancements facility 1
138 configuration-z/Architecture-mode
139 multiple-epoch
140 IBM internal use only
141 IBM internal use only
142 store-CPU-counter-multiple
144 test-pending-external-interruption
145 insert-reference-bits-multiple
146 message-security-assist-extension 8
147 Reserved for IBM use
148 vector-enhancements 2
149 move-page-and-set-key
150 enhanced-sort
151 DEFLATE-conversion
152 vector-packed-decimal-enhancement 1
153 IBM internal use only
155 message-security-assist-extension-9
156 IBM internal use only
158 ultravisor-call
161 secure-execution-unpack
165 neural-network-processing-assist
168 ESA/390-compatibility-mode
169 storage-key-removal
192 vector-packed-decimal-enhancement 2
193 BEAR-enhancement
194 reset-DAT-protection
196 processor-activity-instrumentation
197 processor-activity-instrumentation extension 1
'''

# The Fac_Bits class manages facility indicators and their descriptions.  An
# instance of this class is used to display facility indicator assignements
# and interpret a sequence of stored facility indicators.
#
# Instance Argument:
#   string   A multi-line string containing a description of each assigned
#            facility indicator.  The string is converted into a dictionary
#            whose key is the assigned facility bit number and the key's value
#            being the indicator text description.  Any facility number not
#            present in the data string is considered to be "unassigned".
class Fac_Bits:
    def __init__(self,string):
        # Create dictionary of facility bits, by number, mapped to the
        # facility's text description.  Unassigned bit numbers are not assigned
        self.num_bits=0   # Maximum assigned facility bit number
        self.num_size=0   # Number of decimal digits in number of assigned bits
        self.unassigned="unassigned"
        self.bits=self.convert(string)  # Dictionary of facility bit numbers

    # Separate the multi-line string into a dictionary of facility bit numbers,
    # integers, mapped to the facility's text description.  Unassigned
    # facility indicator bits are described as "unassigned".
    # Method Arguments:
    #   string      The multi-line string converted into a dictionary
    #   unassigned  Specify True to include all facility indicators including
    #               those unassigned.  Specify False to include only assigned
    #               numbers.
    def convert(self,string):
        # Separate the multi-line string into a list of strings without line
        # terminators.
        inds=string.splitlines()
        max_bit=0     # Maximum facility indicator in the multi-line string
        defined=[]    # A list of tuples, one tuple per facility bit assignment
        assigned={}   # The dictionary of facility bits
        for text_line in inds:
            # Ignore any empty lines
            if len(text_line) == 0:
                continue
            # Remove any spaces at the start or end of the line
            stripped=text_line.strip()
            # Convert the stripped line into a list containing the definition's
            # two parts: indicator bit number (as text) and text description
            separated=stripped.split(" ",1)
            try:
                a=int(separated[0])
            except ValueError:
                # If this error occurs fix the text line in the multi-line
                # string.
                raise ValueError("facility '%s' assigned to a value that is "\
                    "not an unsigned decimal" % (separated[1],separated[0]))
            max_bit = max(max_bit,a)
            tpl=(a,separated[1])
            defined.append(tpl)

        # Assign all facility bits with a description of "unassigned.
        unassigned=self.unassigned
        for n in range(max_bit):
            assigned[n]=unassigned

        # Assign facility indicators
        for tpl in defined:
            a,b=tpl
            assigned[a]=b

        # Return results of the conversion of multi-line string
        self.num_bits=max_bit
        self.num_size=len("%s" % self.num_bits)
        self.num_bytes=(max_bit+7) // 8
        self.bytes_size=len("%s" % self.num_bytes)
        return assigned

    def display(self):
        for key,value in self.bits.items():
            print("%s %s" % (key,value))

    # Returns the description of a facility bit assignment
    # Method Argument:
    #   bit_num   the requested description's assigned facility bit number
    # Exceptions:
    #   KeyError if bit_num exceeds the maximum facility number assigned by
    #            the database in the global attribute: fac_ind_data.
    def fetch(self,bit_num):
        return self.bits[bit_num]

# Global object encapsulating Facility Indicator bit assignment descriptions
FIB=Fac_Bits(fac_ind_data)
#FIB.display()  # Uncomment for debugging purposes


#
#  +------------------------+
#  |                        |
#  |   STFLE Bit Settings   |
#  |                        |
#  +------------------------+
#

# Instance arguments:
#   lst    the --fi command line argument list
#   debug  Specifies whether debug messages are produced.  Specify True to
#          display debug messages.  Specify False to inhibit debug messages.
#          Defaults to False
class Settings:
    hexdigits="0123456789abcdefABCDEF"
    def __init__(self,lst,debug=False):
        self.debug=debug   # Whether debug messages are displayed
        self.lst=lst       # --fi command-line arguments strings
        self.errors=0      # Number of encountered errors

    # Remove prefix and, if present, terminating suffix
    # Method Argument:
    #   a single string from the --fi command line argument
    def __prefix(self,string):
        if len(string) == 0:
            # Empty strings should be detected by the convert() method
            raise ValueError("empty strings may not be converted by "\
                "Settings.__prefix() method")
        elif len(string) >=2 and string[:2]=="0x":
            # Remove "0x" from "0xh...."
            return string[2:]
        # Treat entire string as hexadecimal digits
        return string

    # Convert the string of arguments from --fi to a sequence of hex ASCII
    # characters in upper case for digits A-F.
    #
    # Input strings may optionally include "0x" as a prefix.
    #
    # Errors may be encountered during conversion.  Conversion errors will
    # force termination of the tool.
    #
    # Returns:
    #   a tuple of two elements:
    #      tuple[0] - a integer of number of detected errors
    #      tuple[1] - a single string of concatenated hexadecima; digits or
    #                 None when errors were encountered
    def convert(self):
        digits=Settings.hexdigits
        errors=0   # Number of encountered errors
        strings=[]      # Valid hexadecimal strings
        lst=self.lst
        for n,s in enumerate(lst):
            if len(s) == 0:
                continue
            string=self.__prefix(s)

            for x in string:
                # Make sure each string contains only hexadecimal digits
                good=True
                if not x in digits:
                    errors+=1
                    print("ERROR: --fi argument %s not hexadecimal: %s" \
                        % (n+1,string))
                    good=False
            if good:
                strings.append(string.upper())

        if errors:
            return (errors,None)
        return (0,"".join(strings))


#
#  +-----------------------------+
#  |                             |
#  |   STFLE Command-Line Tool   |
#  |                             |
#  +-----------------------------+
#

class STFLE:

    # Converts a character hexadecimal digit into a list of zero and ones.
    hex2bits={"0":[0,0,0,0],\
              "1":[0,0,0,1],\
              "2":[0,0,1,0],\
              "3":[0,0,1,1],\
              "4":[0,1,0,0],\
              "5":[0,1,0,1],\
              "6":[0,1,1,0],\
              "7":[0,1,1,1],\
              "8":[1,0,0,0],\
              "9":[1,0,0,1],\
              "A":[1,0,1,0],\
              "B":[1,0,1,1],\
              "C":[1,1,0,0],\
              "D":[1,1,0,1],\
              "E":[1,1,1,0],\
              "F":[1,1,1,1]}

    def __init__(self,args):
        self.args=args      # Command line arguments
        self.debug=args.debug   # --debug command line argument present
        self.all=args.all       # --all command line argument present

        if self.debug:
            # Print the command-line Namespace object if debug is True
            print(args)

        # List of hexadecimal digits as one or more strings
        self.fi=args.fi         # --fi command-line argument

        # Settings object of facility indicators being interpreted
        self.settings=None

    # Display Facility Bits database by assigned bit number.
    # Method Argument:
    #   bits      The list of bit numbers for which descriptions are requested
    def display_description_by_bit(self,bits):
        #print("all_bits: %s" % all_bits)
        fib=FIB
        num_len=fib.num_size  # Length of facility numbers

        if len(bits) == 1 and bits[0]=="all":
            print("Facility Bit Assignments:")
            for n in range(fib.num_bits):
                description=fib.fetch(n)
                if description == fib.unassigned:
                    continue
                display_number="%s"  % n
                display_number=display_number.rjust(num_len)
                print("    %s  %s" % (display_number,description))
            return

        bit_numbers=[]
        error=False
        for n,bit_str in enumerate(bits):
            try:
                bit=int(bit_str,10)
                bit_numbers.append(bit)
            except ValueError:
                print("--bit argument %s not decimal: '%s'" % (n+1,bit_str))
                error=True

        if len(bit_numbers) == 0:
            return

        # Print selected decimal assignments
        max_bit=fib.num_bits-1
        print("Facility Bit Assignments:")
        for number in bit_numbers:
            display_number="%s"  % number
            display_number=display_number.rjust(num_len)
            try:
                description=fib.fetch(number)
            except KeyError:
                description="%s (exceeds maximum assigned bit: %s)" \
                    % (fib.unassigned,max_bit)
            print("    %s  %s" % (display_number,description))

    # Search facility bit databased descriptions for one or more strings
    # Method Arguments:
    #   strings  a list of strings supplied by the --search command-line
    #            argument
    #   and_comp  Specify True if the description must contain all strings or
    #            False if the description must contain at least one of the
    #            strings.
    def display_description_by_search(self,strings,and_comp=False):
        assert isinstance(strings,list),"'strings' argument must be a list: "\
            "%s" % strings

        # True means an 'and' comparison, False means an 'or' comparison
        compare=and_comp

        if len(strings) == 0:
            # Ignore the --search command-line argument if no values supplied
            return

        fib=FIB
        unassigned=fib.unassigned
        num_len=fib.num_size  # Length of facility numbers
        print_line="Facility Description Search: "

        if len(strings)==1:
            # Print search strings when only one string supplied
            print("    %s %s" % (print_line,strings[0]))
            compare=False
        else:
            # Print multiple strings with a final 'and' or 'or' indicating
            # how the compares are performed.
            last_ndx=len(strings)-1
            #print_line="    "
            for n,string in enumerate(strings):
                if n == 0:
                    # First string
                    print_line="%s %s" % (print_line,string)
                elif n < last_ndx:
                    # Middle string
                    print_line="%s, %s" % (print_line,string)
                else:
                    # Last string
                    if compare:
                        comp="and"
                    else:
                        comp="or"
                    print_line="%s, %s %s" % (print_line,comp,string)
            print("    %s" % print_line)  # Print strings being compared

        # strings attribute is used for scan of the FI database.
        found=[]    # List of found facility bits from description strings
        for n in range(fib.num_bits-1):
            n_desc=fib.fetch(n)
            if n_desc==unassigned:
                # If the facility bit is unassigned, ignore it
                continue
            if compare:
                # Perform and search
                fnd=self.search_desc_and(n_desc,strings)
            else:
                fnd=self.search_desc_or(n_desc,strings)
            if fnd:
                found.append(n)  # Add to list of displayed facility bits

        for fi_bit in found:
            display_number="%s"  % fi_bit
            display_number=display_number.rjust(num_len)
            description=fib.fetch(fi_bit)
            print("    %s  %s" % (display_number,description))

        num_found=len(found)
        if num_found == 1:
            s=""
        else:
            s="s"
        print("%s Facility Indicator%s found" % (num_found,s))

    # Displays in human readable form the facility indicators
    # Method Arguments:
    #   hexstr     A single string of hexadecimal digits with upper case
    #              A-F when present constituting the list of facility indicators
    #   longform   Specify True to create the long form display.  Specifiy
    #              False to create the short form display
    #   zero       The command-line --zero argument value
    def display_facility_indicators(self,hexstr,longform,zero=False):
        assert isinstance(hexstr,str),"'hexstr' must be a string: %s" % hexstr

        print("Facility Indicator Settings:")
        if not hexstr:
            print("    Facility List:   omitted")
            return

        print("    Facility List:   %s" % hexstr)

        bits=[]  # STFLE bit settings as a list of zeros and ones.
        xc2b=STFLE.hex2bits
        for c in hexstr:
            bits.extend(xc2b[c])

        fib=FIB
        num_len=fib.num_size
        unassigned=fib.unassigned

        if longform:
            # Set character to use to display unused facility in long form
            # analysis
            if zero:
                char="0"
            else:
                char="-"

            # Long form facility indicator analysis
            present=[]
            bytes_size=FIB.bytes_size
            ndx=0

            for n,bit_val in enumerate(bits):
                if bit_val:
                    present.append(n)
            for n in range(fib.num_bits):
                bit_num="%s" % n
                bit_num=bit_num.rjust(num_len)
                meaning=fib.fetch(n)

                byte_bit_num=n % 8
                if byte_bit_num == 0:
                    pr_ndx="%s" % ndx
                    pr_ndx=pr_ndx.ljust(bytes_size)
                    pr_ndx="+%s" % (pr_ndx)
                    ndx+=1
                else:
                    pr_ndx=" %s" % "".ljust(bytes_size)

                if n in present:
                    print("    %s %s  1  %s" % (pr_ndx,bit_num,meaning))
                else:
                    print("    %s %s  %s  %s" % (pr_ndx,bit_num,char,meaning))
        else:
            # Short form facility indicator analysis
            for n,bit_val in enumerate(bits):
                # Convert each facility bit into a string
                if not bit_val:
                    # Do not print facility indicators with a zero bit setting
                    continue

                bit_num="%s" % n
                # Bit number as a right justified string
                bit_num=bit_num.rjust(num_len)
                # Assigned meaning of the bit number
                meaning=fib.fetch(n)
                print("    %s  %s" % (bit_num,meaning))


    # Searches a facility string for all supplied search arguments.  When all
    # are found, the facility is considered 'found' for the purpose of the
    # search.
    # Method Arguments:
    #   desc    A string descritpion of a facility indicator in the data base.
    #   strings A list of strings, all of which are sought within the
    #           description.  When all are found the description MATCHES the
    #           search.
    # Returns:
    #   True if the description contains all of the sought for strings.
    #   False if the description contains fails to include all of the strings.
    def search_desc_and(self,desc,strings):
        for string in strings:
            try:
                desc.index(string)
            except ValueError:
                # description fails to contain a string, so quit looking for
                # more
                return False

        # All of the strings found so the description matches
        return True

    # Searches a facility string for a supplied search argument.  If any found
    # the facility is considered 'found' for the purpose of the search.
    # Method Arguments:
    #   desc   A string description of a facility indicator in the data base
    #   strings  A list of one or more strings sought within the description.
    #            When one found, the description MATCHES the search.
    # Returns:
    #   True if the description contains any one of the sought for strings.
    #   False if the description contains none of the strings.
    def search_desc_or(self,desc,strings):
        for string in strings:
            try:
                desc.index(string)
                # String found, can bail after the first one found
                return True
            except ValueError:
                # This string not found, search next one
                continue

        # None found, so the comparisons failed.
        return False

    def run(self):
        if self.debug:
            print("Conversion Flag: %s" % flag)

        # --bit command-line argument
        if self.args.bit:
            self.display_description_by_bit(self.args.bit)

        # --search command-line argument.
        # Also uses --and command-line argument
        if self.args.search:
            self.display_description_by_search(self.args.search,self.args.nd)

        # --fi command-line argument
        # Also uses --all and --zero command-line arguments
        if self.args.fi:
            self.settings=Settings(self.fi,debug=self.debug)
            flag,hexstr=self.settings.convert()
            if flag:
                print("ERROR: Analysis aborted due to --fi argument errors: %s" \
                    % flag)
            else:
                self.display_facility_indicators(hexstr,self.all,zero=args.zero)


#
# +----------------------------------------+
# |                                        |
# |   Command-Line Argument Definitions    |
# |                                        |
# +----------------------------------------+
#

# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog=this_module,\
        epilog=copyright,\
        description="STORE FACILITY LIST EXTENDED analysis.  Analyzes "\
            "facility list content as one or more hexadecimal strings. "\
            "Displays facility indicators by number, or searches facility "\
            "indicator descriptions for one or more strings. "\
            "If neither --fi, --bit, nor --search arguments supplied, "\
            "prints copyright notice.")

  # Input related argument

    # Query bits number description
    parser.add_argument("-b","--bit",nargs="*",metavar="DEC",default=[],\
        help="query facility bit descriptions by one or more decimal numbers, "\
            "optional. Specify 'all' for all bit number assignments.")

    # Input facility indicators as one or more groups of hexadecimal digits.
    parser.add_argument("--fi",nargs="*",metavar="HEX",default=[],\
        help="facility indicators as one or more hexadecimal sequences, "\
            "optional")

    # Search the facility number descriptions for one or more character
    # sequences
    parser.add_argument("-s","--search",nargs="*",metavar="CHAR",default=None,\
        help="search facility indicator descriptions for character "\
            "string(s), optional.")

  # Output related argument
    # Print all facility indicators
    parser.add_argument("-a","--all",action="store_true",default=False,\
        help="Enable long form facility analysis. Print all --fi indicators, "\
        "not just those set.  Do not confuse with 'all' as a --bit argument."\
        " Ignored if --fi not specified.")

    # Enable debug messages.
    parser.add_argument("-d","--debug",action="store_true",default=False,\
        help="enables debug messages")

    # Force 'and' string comparisons.
    parser.add_argument("--nd",action="store_true",default=False,\
        help="force 'and' comparison during --search argument.  Ignored if "\
            "--search not specified.")

    # Output a 0 for omitted facility indicator in long form analysis
    parser.add_argument("-z","--zero",action="store_true",default=False,\
        help="use '0' for omitted facility in list. Applies only to the "\
            "long form analysis.")

    return parser.parse_args()


if __name__ == "__main__":
    args=parse_args()
    print(copyright)
    STFLE(args).run()
