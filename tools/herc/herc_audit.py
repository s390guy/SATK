#!/usr/bin/python3
# Copyright (C) 2016 Harold Grovesteen
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

# This module reads the Hercules opcodes.c and s37x.c files and compares their content
# to the corresponding ASMA MSL configuration files.  A report listing is generated
# and written to the requested output file.
#
# The module is tightly coupled to the coding style present in the two Hercules
# source modules upon which the comparison is performed.  The module has been tested
# with Hyperion.  Results are unpredictable with any other version of Hercules.

this_module="herc_audit.py"

# Python Imports
import functools        # Used to aid in sorting complex compares
import os
import os.path
# SATK Imports:
from listing import *   # Access the listing generator tools
#import retest           # Re-use regular expression test module
import satkutil         # Access the generic path manager object
# ASMA Imports:
import msldb            # Access an MSL database


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
#  +----------------------------------+
#  |                                  |
#  |   C Language Module Processing   |
#  |                                  |
#  +----------------------------------+
#


# opcode.c table entry
# Instance Arguments:
#   lineno    Line number in opcode.c of the entry's definition
#   gen       GEN options
#   function  function and other values of the entry
#   opcode    Operation code comment from the entry
class CEntry(object):
    def __init__(self,lineno,pos,gen,function,opcode):
        self.null=False           # Whether this is a null entry
        self.lineno=lineno        # opcode.c line number of the entry
        self.opcode=opcode        # Operation Code in Hex
        self.pos=pos              # Index of the entry in the Hercules table
        self.opsize=0             # Opcode size in bits
        self.level2=False         # Is this a level 1 pointor for level 2?

        archs=gen.split("x")
        self.s370="370" in archs
        self.s37x="37X" in archs
        self.s390="390" in archs
        self.s900="900" in archs

        if function:
            sep=function.split(",")
            self.function=sep[0]
            self.format=sep[1]
            self.mnemonic=sep[2][1:-1]
            # Special handling for pointer to level 2 recognizer function
            if len(self.function)>15 and self.function[:15]=="execute_opcode_":
                self.level2=True
            # Special hndling for Assist instruction with duplicate names:
            if self.mnemonic=="Assist":
                self.mnemonic="Assist_%s" % self.opcode
                #print("[%s] %s" % (self.lineno,self.mnemonic))
        else:
            self.mnemonic=self.format=self.function=""
        self.s37x_func=None      # Function name referenced by s37x
        self.s37x_line=None      # s37x.c line number for instruction

        # Validate index and opcode values
        opcl=len(opcode)
        if opcl==0:
            return
        elif opcl==2:
            opc=int(self.opcode,16)
            self.opsize=8
        elif opcl==4:
            if opcode[2]=="x":
                opc=int(opcode[3],16)
                self.opsize=12
            else:
                opc=int(opcode[2:],16)
                self.opsize=16
        else:
            print("[%s] unexpected opcode length '%s': %s" \
                % (self.lineno,opcode,len(opcode)))
            return

        if pos!=opc:
            print("[%s] opcode %s does not match table index position: 0x%2X" \
                % (self.lineno,opcode,pos))

    def __str__(self):
        if self.s370:
            string="370"
        else:
            string="   "
        if self.s37x:
            string="%s 37X" % string
        else:
            string="%s    " % string
        if self.s390:
            string="%s 390" % string
        else:
            string="%s    " % string
        if self.s900:
            string="%s 900" % string
        else:
            string="%s    " % string

        opc=self.opcode.ljust(4)
        m=self.mnemonic.ljust(6)
        f=self.format.ljust(9)

        return "[%s] %s %s %s %s %s" \
            % (self.lineno,string,opc,m,f,self.function)


# opcode.c null table entry 
class CEntry_Null(CEntry):
    def __init__(self,lineno,pos,gen,opcode):
        super().__init__(lineno,pos,gen,None,opcode)
        self.null=True


# s37x.c table entry
class CEntry_S37X(object):
    def __init__(self,lineno,function,ndx,opcode):
        self.lineno=lineno        # Line number in s37x.c where entry occurs
        self.function=function    # Function associated with the opcdoe processing
        self.ndx=ndx              # Index into opcode.c table of the instruction
        self.opcode=opcode        # Opcode

        self.opcode_line=None     # Line number in opcode.c

        # Validate index and opcode values
        if len(opcode)==0:
            return
        elif len(opcode)==2:
            opc=int(self.opcode,16)
            self.opsize=8
        elif len(opcode)==4:
            if opcode[2]=="x":
                opc=int(opcode[3],16)
                self.opsize=12
            else:
                opc=int(opcode[2:],16)
                self.opsize=16
        else:
            print("[%s] unexpected opcode length: %s" % (self.lineno,opcode))
            return

        if ndx!=opc:
            print("[%s] opcode %s does not match index position: 0x%2X" \
                % (self.lineno,opcode,pos))

    def __str__(self):
        ndx="0x%02X" % self.ndx
        opc=self.opcode.ljust(4)
        return "[%s] %s %s %s" % (self.lineno,opc,ndx,self.function)


# Object encapsulating a C source input line, preserving its source lineno.
# Line termination characters are removed, whitespace at the end of the line is
# removed and if the entire line is empty, it is flags as such
#
# Instance Arguments:
#   n      source file line number
#   line   source file line as a string
class CLine(object):
    def __init__(self,n,line):
        self.lineno=n
        if line[-1]=="\n":
            self.line=line[:-1]
        else:
            self.line=line
        self.line=self.line.rstrip()
        if self.line is None:
            raise ValueError("self.line is None")
        self.empty=len(self.line)==0

    def __str__(self):
        return "[%s] %s" % (self.lineno,self.line)
        
    # Tests whether the line starts with a given string
    # Returns
    #   False  If the line is shorter than string or it doesn't start with the string
    #   True   If the line does start with the test string
    def starts_with(self,string):
        line=self.line.rstrip()
        if len(line)>=len(string):
            return line[:len(string)]==string
        return False


# Base class for a Hercules C language source module.  Subclasses understand
# and process a specific source module.
class CSource(object):
    def __init__(self,filename):
        self.filename=filename
        self.srclines=0
        self.clines=[]

    def __str__(self):
        return "%s: file: %s (lines: %s, non-empty: %s)" \
            % (self.__class__.__name__,self.filename,self.srclines,len(self.clines))   

    def getSource(self,hdir):
        path=os.path.join(hdir,self.filename)
        try:
            fo=open(path,"rt")
        except IOError as ie:
            print("could not open for reading of text: %s" % ie)
            return
        lineno=1
        try:
            for line in fo:
                l=CLine(lineno,line)
                lineno+=1
                if l.empty:
                    continue
                self.clines.append(l)
            self.srclines=lineno
        except IOError as ie:
            print("could not read: %s" % ie)
        try:
            fo.close()
        except IOError:
            print("could not close: %s" % ie)

    def parse(self):
        raise NotImplementedError("%s subclass %s must provide parse() method"\
            % (eloc(self,"parse"),self.__class__.__name__))


# This object encapsulates an opcode table from opcode.c
# Instance Arguments:
#   name    Table name
#   begin   line number of the start of the table
#   end     line number of the table end
#   entries A list of CEntry objects representing the individual entries.
class CTable(object):
    S37X_table={}

    # This method initializes the reverse lookup of CTable_S37X.
    @staticmethod
    def init_S37X_table():
        newd={}
        S37X=CTable_S37X.ctable
        for key in S37X.keys():
            ctable=S37X[key]
            try:
                newd[ctable]
                raise ValueError("duplicate ctable found in CTable_S37x.ctable: %s" \
                    % ctable)
            except KeyError:
                newd[ctable]=key

        # Expose the table
        CTable.S37X_table=newd

    def __init__(self,name,begin,end,entries=[],ignored=False):
        self.name=name         # Table name
        self.begin=begin       # Table line number start
        self.end=end           # Table line number end
        self.entries=entries   # List of CEntry objects
        self.ignored=ignored   # This table was ignored in the source
        self.vector=self.name[:2]=="v_"
        if self.ignored:
            return

        # Determine associated s37c table name, if any
        try:
            self.other=CTable.S37X_table[name]
        except KeyError:
            self.other=None

        # Count the number of non-empty entries
        c=0
        for e in entries:
            if e.null:
                continue
            c+=1
        self.count=c           # Non-empty entry count

    def __str__(self):
        return "Opcode table: [%s-%s] %s - entries: %s" \
            % (self.begin,self.end,self.name,len(self.entries))

    def display(self,null=False):
        for entry in self.entries:
            if entry.null:
                if null:
                    print(entry)
            else:
                print(entry)


class CTable_Ignored(CTable):
    def __init__(self,name,begin):
        super().__init__(name,begin,None,ignored=True)


class CTable_S37X(object):
    ctable={"00":"opcode_table",
            "a7":"opcode_a7_x",
            "b2":"opcode_b2xx",
            "b3":"opcode_b3xx",
            "b9":"opcode_b9xx",
            "c0":"opcode_c0_x",
            "c2":"opcode_c2_x",
            "c4":"opcode_c4_x",
            "c6":"opcode_c6_x",
            "c8":"opcode_c8_x",
            "e3":"opcode_e3xx",
            "e5":"opcode_e5xx",
            "eb":"opcode_ebxx",
            "ec":"opcode_ecxx",
            "ed":"opcode_edxx"}
    def __init__(self,name,begin,end,entries=[]):
        self.name=name
        self.begin=begin
        self.end=end
        self.entries=entries           # List of CEntry_S37X objects
        self.count=len(self.entries)   # Entry count

        # Determine opcode.c table name with which table is associated.
        try:
            self.other=CTable_S37X.ctable[name]
        except KeyError:
            raise ValueError(\
                "%s [%s] CTable_S37X.ctable does not have the opcode.c table "
                    "updated from this s37x.c table: %s" \
                        % (eloc(self,"__init__"),begin,name))
            # Note: if a s37x.c table truly does not require an opcode.c table and
            # it to the ctable dictionary assigning its value as None.

    def __str__(self):
        return "S37X Opcode table: [%s-%s] %s - entries: %s" \
            % (self.begin,self.end,self.name,len(self.entries))

    def display(self):
        for entry in self.entries:
            print(entry)


class CUndef(object):
    def __init__(self,feature):
        self.feature=feature      # feature to which function belongs
        self.functions={}         # CFunction objects that are undefined

    def __str__(self):
        string="%s (%s instructions):" % (self.feature,len(self.functions))
        for f in self.functions:
            string="%s\n    %s" % (string,f)
        return string
        
    def function(self,name,lineno):
        #if name in self.functions:
        #    raise ValueError("%s function already undefined: %s" \
        #        % (eloc(self,"function"),name))
        try:
            self.functions[name]
            raise ValueError("%s function already undefined: %s" \
                % (eloc(self,"function"),name))
        except KeyError:
            self.functions[name]=CFunction(name,lineno)


class CFunction(object):
    def __init__(self,name,lineno):
        self.name=name         # Function name from undefined function
        self.lineno=lineno     # Opcode.c line number where function is undefined
        self.hfeature=None     # HFeature object associated with the CFunction
        
    def __str__(self):
        if self.hfeature :
            feat=self.hfeature.name
        else:
            feat=self.hfeature
        return "%s function, opcode.c[%s], in %s" \
            % (self.name,self.lineno,feat)
        
    def add_feature(self,hfeature):
        assert isinstance(hfeature,HFeature),\
            "%s 'hfeature' argument must be a HFeature object: %s" \
                % (eloc(self,"add_feature"),hfeature)

        self.hfeature=hfeature # Point back to HFeature owner


# Objects for processing of the Hercules featxxx.h modules
class CFeature(CSource):
    def __init__(self,module):
        super().__init__(module)
        self.features={}

    def define(self,cline):
        if cline.empty or cline.starts_with("//"):
            return False
        if not cline.starts_with("#define "):
            return False

        # Remove any trailing comments on the line
        line=cline.line.lstrip()  # and ignore any beginning spaces
        try:
            # Some lines have #define FEATURE_XXXX    /* a comment */
            # We remove the comment and any preceding spaces here
            line=line[:line.index("/*")]
            line=line.rstrip()
        except ValueError:
            pass
        items=line.split()
        if len(items)==2:
            # #define has no value
            # Found: #define FEATURE_XXXXX...
            return items[1]   # Return defined feature
        return False

    def new_feature(self,name):
        try:
            self.features[name]
            raise ValueError("%s feature already defined: %s" \
                % (eloc(self,"new_feature"),name))
        except KeyError:
            self.features[name]=[]

    def parse(self):
        for cline in self.clines:
            name=self.define(cline)
            if name:
                self.new_feature(name)

    def summary(self):
        feats=sorted(self.features.keys())
        print("%s Features: %s" \
            % (self.__class__.__name__[-3:],len(feats)))
        for f in feats:
            print("    %s" % f)


class CFeat370(CFeature):
    def __init__(self):
        super().__init__("feat370.h")


class CFeat390(CFeature):
    def __init__(self):
        super().__init__("feat390.h")


class CFeat900(CFeature):
    def __init__(self):
        super().__init__("feat900.h")


# This object gathers from multiple sources, feature related information
# The foundation is the parsed feat370.h, feat390.h and feat900.h source modules
# Instruction functions for a given feature is added from the feature UNDEF
# statements in the opcode.c source module.
class HFeature(object):
    archs=["370","390","900"]
    def __init__(self,name):
        self.name=name     # Feature name
        self.archs=[False,False,False]  # Whether arch supports the feature
        
        # Instruction functions used by this feature.  The key is the function
        # name.  Initially it is added as a key mapped to None.  Later it will
        # be updated with instruction operation code information, replacing
        # None.  See the add_functions method().
        self.functions={}
        
    def __str__(self):
        archs=HFeature.archs
        flags=""
        for n in range(3):
            if self.archs[n]:
                flags="%s %s" % (flags,archs[n])
            else:
                flags="%s %s" % (flags,"   ")
        return "%s - %s %s" % (flags,len(self.functions),self.name)
        
    def add_functions(self,func):
        assert isinstance(func,CUndef),\
            "%s 'func' argument must be a CUndef object: %s" \
                % (eloc(self,"add_function"),func)
                
        # List of instruction functions
        for f,cf in func.functions.items():
            assert isinstance(cf,CFunction),\
                "%s %s function %s cf not a CFunction: %s" \
                    % (eloc(self,"add_functions"),self.name,f,cf)
            try:
                self.functions[f]
                raise ValueError("%s %s already has function defined: %s" \
                    % (eloc(self,"add_functions"),self.name,f))
            except KeyError:
                # Add the function to the function dictionary
                cf.add_feature(self)
                self.functions[f]=cf


class HFeatures(object):
    def __init__(self,s370,s390,s900):
        assert isinstance(s370,CFeat370),\
            "%s 's370' argument must be a CFeat370 object: %s" \
                % (eloc(self,"__init__"),s370)
        assert isinstance(s390,CFeat390),\
            "%s 's370' argument must be a CFeat390 object: %s" \
                % (eloc(self,"__init__"),s390)
        assert isinstance(s900,CFeat900),\
            "%s 's370' argument must be a CFeat900 object: %s" \
                % (eloc(self,"__init__"),s900)
        
        self.s370=s370   # S/370 defined features
        self.s390=s390   # S/390 defined features
        self.s900=s900   # S/900 defined features

        self.features={}  # Dictionary of HFeature objects by feature name
        # Dictionary of instruction functions to owning HFeature object
        self.functions={}

        # Update each HFeature object with the archs that enable it.
        for n,arch in enumerate([self.s370,self.s390,self.s900]):
            for feat in arch.features.keys():
                feature=self.get_feature(feat)
                feature.archs[n]=True

    # Add instruction function names to the feature.  Function names derived from
    # opcode.c UNDEF statements.
    def add_functions(self,undef_list):
        assert isinstance(undef_list,list),\
            "%s 'undef_list' argument must be a list: %s" \
                % (eloc(self,"add_functions"),undef_list)

        for n,u in enumerate(undef_list):
            assert isinstance(u,CUndef),\
            "%s udef_list[%s] must be a CUndef object: %s" \
                % (eloc(self,"add_functions"),n,u)

            feat=self.get_feature(u.feature)
            # Note: it is possible to encounter features referenced in opcode.c
            # that are not defined in any of the featxxx.c modules.  This occurs
            # because the test in opcode.c if for undefined features.  Excluding
            # them from featxxx.h had the effect of causing the feature to be
            # undefined, satifying the test.  Features added at this point
            # will not be enabled for any architecture level, as expected.

            feat.add_functions(u)
            
        # Consolidate functions into a single global dictionary
        for feat in self.features.values():
            for f,cf in feat.functions.items():
                # f is the function name as a string
                # cf is its CFunction object
                assert isinstance(cf,CFunction),\
                    "%s %s cf for function %s not a CFunction object: %s" \
                        % (eloc(self,"add_functions"),feat.name,f,cf)
                try:
                    def_func=self.functions[f]
                    assert isinstance(def_func,CFunction),\
                        "%s function %s definition not a CFunction object: %s" \
                            % (eloc(self,"add_functions"),f,def_func)
                    
                    raise ValueError(\
                        "%s %s already defined, "
                           "can't define by %s: opcode.c[%s]"\
                                % (eloc(self,"add_functions"),def_func,\
                                    feat.name,cf.lineno))
                except KeyError:
                    self.functions[f]=cf

    def get_feature(self,name):
        try:
            feat=self.features[name]
        except KeyError:
            feat=HFeature(name)
            self.features[feat.name]=feat
        return feat
        
    def summary(self):
        feats=sorted(self.features.keys())
        for feat in feats:
            f=self.features[feat]
            print(f)


# Object for processing of the Hercules opcode.c module
class COpcodes(CSource):
    ignore_tables=["opcode_15__","opcode_18__","opcode_1E__","opcode_1F__",\
                   "opcode_41_0","opcode_47_0","opcode_50_0","opcode_55_0",\
                   "opcode_58_0","opcode_91xx","opcode_A7_4","opcode_BF_x",\
                   "opcode_D20x","opcode_D50x","opcode_E3_0","opcode_E3_0______04",\
                   "opcode_E3_0______24"]
    def __init__(self):
        super().__init__("opcode.c")

        # Parse state
        #  0 == Looking for start of an opcode table
        #  1 == Within an opcode table
        #  2 == Looking for feature being undefined
        #  3 == Adds indidivual function names to the UNDEF'ed feature
        self.state=2

        # Parse results
        self.tables={}       # Dictionary of CTable objects by name
        self.tbllist=[]      # List of CTable objects as found in opcode.c
        self.vtables={}      # Dictionary of vector CTable objects
        self.vtbllist=[]     # List of vector CTable objects

        self.ignored=[]      # List of ignored tables
        
        self.undefined=[]    # List of CUndef objects as found in opcode.c

        # Accumulated data while within an opcode definition
        self.start=None      # First line of the opcode table
        self.end=None        # Ending line of the opcode table
        self.table_name=None # Table being extracted
        self.pos=None        # Index in table of definition
        self.opcodes=[]      # Accumulated lines of opcode definitions
        
        # Accumulated data while processing undefined features
        self.undef=None      # Current CUndef object being created

        # Correct incorrect comment opcodes
        self.fix_opcode={3335:"B9A4",3708:"E3A4",3729:"E3B9",4487:"EBA4",4508:"EBB9",\
            5026:"EDB9"}

    # Add a new entry destined for the table.
    # Side Effects:
    #   - increments the table index for the next table entry
    def new_entry(self,entry):
        assert isinstance(entry,CEntry),\
            "%s 'entry' argument must be a CEntry object: %s" \
                % (eloc(self,"new_entry"),entry)

        self.opcodes.append(entry)
        self.pos+=1

    def new_table(self,tbl):
        assert isinstance(tbl,CTable),\
            "%s 'tbl' argument must be a CTable object: %s" \
                % (eloc(self,"new_table"),tbl)

        if tbl.vector:
            # Add vector instruction table to the module
            self.vtables[tbl.name]=tbl
            self.vtbllist.append(tbl)
        else:
            # Add normal instruction table to the module
            self.tables[tbl.name]=tbl
            self.tbllist.append(tbl)
        self.reset()

    def parse(self,debug=False):
        for cline in self.clines:
            if self.state==0:
                # Looking for start of a table
                self.table_begin(cline)
            elif self.state==1:
                # processing table entries
                self.table_entry(cline)
            elif self.state==2:
                # Looking for feature being undefined
                self.undef_begin(cline)
            elif self.state==3:
                # Processing UNDEF entries in feature
                self.undef_function(cline)
            else:
                raise ValueError("%s unexpected parse state: %s" \
                    % eloc(self,"parse"),self.state)

        if not debug:
            return

        for table in self.tbllist:
            print("")
            print(table)
            table.display()

    # Reset table parse information for next table
    def reset(self):
        self.state=0
        self.begin=None
        self.end=None
        self.table_name=None
        self.opcodes=[]

    def summary(self):
        entries=0
        for t in self.tbllist:
            entries+=t.count
        for t in self.vtbllist:
            entries+=t.count
        tables=len(self.tbllist)+len(self.vtbllist)+len(self.ignored)
        print("   tables: %s, entries: %s" % (tables,entries))
        for t in self.tbllist:
            name=t.name.ljust(13)
            entry="    %s  entries: %3d instructions: %3d" \
                % (name,len(t.entries),t.count)
            if t.other:
                entry="%s  %s" % (entry,t.other)
            print(entry)
        for t in self.vtbllist:
            name=t.name.ljust(15)
            print("    %s  entries: %3d instructions: %3d" \
                % (t.name,len(t.entries),t.count))
        for t in self.ignored:
            name=t.name.rstrip()
            name=name.ljust(13)
            print("    %s  ignored" % name)

    # Detects the start of a new table definition
    # Side Effects:
    #   - Preserves table start line number and the table's name
    #   - Entry index set to 0 for first entry.
    #   - Parser self.state set to 1, indicating within a table definition.
    def table_begin(self,cline):
        # A table is started with this sequence in column 1.  Static content is
        # identified by a hyphen under the content.  Question marks identify variable
        # information.
        #
        #     static zz_func opcode_table_name[0x100][GEN_MAXARCH] = {
        #     ------ ------- ?????????????????-?????-------------- - -
        #     [ 0  ]   [1]   [               2                   ] 3 4
        # 
        # The numbers indicate the index of the split items - five required
        
        # Adjust lineno to enable debugging of a specific opcode.c line.  Line
        # numbers start at 1, so 0 disabled debug messages.
        debug = cline.lineno==0

        if debug:
            print(cline)

        s=cline.line.split()
        if debug:
            print("[%s]: s: %s" % (cline.lineno,s))
        if len(s)<5:
            if debug:
                print("[%s] items less than 5 in split line" % cline.lineno)
            return
        if s[0]!="static" or s[1]!="zz_func" or s[3]!="=" or s[4]!="{":
            if debug:
                print("[%s] is not start of a table" % cline.lineno)
            return

        # Process the name item
        #
        #     opcode_table_name[0x100][GEN_MAXARCH]
        #     ????????????????? ------ ------------
        #     [        0      ] [ 1  ] [     2    ]

        # Now extract the table name
        ns=s[2].split("[")
        if len(ns)!=3:
            print("expected three items in name item, found: %s" % ns)
        if ns[2]!="GEN_MAXARCH]":
            print("warning: unexpected item in name not found: [%s" % ns[2])
        if ns[0] in COpcodes.ignore_tables:
            tbl=CTable_Ignored(ns[0],cline.lineno)
            self.ignored.append(tbl)
            return

        self.table_name=ns[0]
        self.start=cline.lineno
        self.pos=0
        if debug:
            print("starting table: [%s] %s" % (self.start,self.table_name))

        self.state=1

    def table_entry(self,cline):
        # This statement controls debugging.  Modify the line number from 0 to the
        # desired line number.
        debug=cline.lineno==0
        if debug:
            print(cline)

        # A table entry has this format starting in column 2.  The final entry
        # ends with a semicolon ";" preceded by a right curly-brace "}".
        #
        #      /*05*/   GENx370x390x900 (branch_and_link_register,RR,"BALR"),
        #     ---??--   ----???-???-??? -????????????????????????-??-??????-?
        #      [ 0  ]   [       1     ] [                  2                ]
        #
        # The final entry looks like this:
        #
        #      /*FF*/   GENx___x___x___  };
        #     ---??--   ----???-???-???  ??
        text=cline.line

        # Determine if this is the last entry of the table
        try:
            end=text.rindex(";")
            text=text[:end]
            self.end=cline.lineno
            end_of_table=True
            if debug:
                print("[%s] is the last table entry - ';' found at %s" \
                    % (cline.lineno,end+1))
        except ValueError:
            end_of_table=False
            if debug:
                print("[%s] is not the last entry" % cline.lineno)

        # Separate string at whitespace. 
        s=text.split()

        # For some unexplained (unresearched) reason when whitespace is removed
        # some of the items of seprated strings end up being empty (zero length).
        # This removes them.  Suspect tabs might be the reason.
        removed=[]
        for item in s:
            if item!="":
                removed.append(item)
        if debug:
            print("[%s] removed: %s" % (cline.lineno,removed))
        if len(removed)<3:
            raise ValueError("[%s] expected at least three items in line, found: %s" \
                % (cline.lineno,removed))

        opcode=removed[0]
        if opcode in ["#define","/*"]:
            return
        if len(opcode)>8:
            print("[%s] comment line - %s" % (cline.lineno,cline))
            return
        if opcode[:2]!="/*" or opcode[-2:]!="*/":
            print("[%s] unrecognized opcode: %s" % (cline.lineno,opcode))
            return

        # Correct opcode comments that are wrong in opcode.c.
        # Ultimately opcode.c needs to be fixed for these.
        try:
            opcode=self.fix_opcode[cline.lineno]
        except KeyError:
            # Extract opcode from comment: /*XX*/ or /*XXXX*/
            opcode=opcode[2:-2]

        gen=removed[1]
        if len(gen)!=15:
            print("[%s] GEN... not 15 characters: '%s': %s" % (cline,gen,len(gen)))
            return
        if gen[:4]!="GENx":
            print("[%s] warning, not a GEN line" % cline)
            return

        # Default to a null table entry if anything goes wrong in the analysis
        entry=CEntry_Null(cline.lineno,self.pos,gen,opcode)

        error=False   # Set to True if an error occurs in the entry
        if gen!="GENx___x___x___":
            # Build a full entry for an opcode in at least one architecture
            error=False     # Set to True if an error occurs in the entry

            function=removed[2]
            try:
                parms=function.rindex(")")
                parms=function[:parms]
                if parms[0]=="(":
                    parms=parms[1:]
                else:
                    print("[%s] function left parenthesis not found" % cline.lineno)
                    error=True
            except ValueError:
                if opcode in ["B2A6","B2A7"]:
                    # Special handling for function with embedded space and parens
                    parms='%s"' % function[1:]
                else:
                    print("[%s] function '%s' right parenthesis not found" \
                        % (cline,function))
                    error=True

            if not error:
                entry=CEntry(cline.lineno,self.pos,gen,parms,opcode)
            else:
                print("[%s] unrecognized table entry replaced with null" \
                    % cline.lineno)

        # Add the entry to the table
        self.new_entry(entry)

        if end_of_table:
            table=CTable(self.table_name,self.start,self.end,entries=self.opcodes)
            self.new_table(table)

    def undef_begin(self,cline):
        # Look for start of instruction table creation
        if cline.starts_with("DEF_INST(dummy_instruction)"):
            self.state=0   # start table processing
            return

        # Not a new undefined feature so keep looking
        if not cline.starts_with("#if !defined(FEATURE_"):
            return

        # Remove a possible comment
        line=cline.line.lstrip()  # and ignore any beginning spaces
        try:
            # Some lines have #define FEATURE_XXXX    /* a comment */
            # We remove the comment and any preceding spaces here
            line=line[:line.index("/*")]
            line=line.rstrip()
        except ValueError:
            pass
        
        try:
            rparen=line.index(")")
        except ValueError:
            raise ValueError("%s missing right parenthesis: %s" \
                % (eloc(self,"undef_begin"),cline)) from None
            
        feature=line[13:rparen]
        self.undef=CUndef(feature)
        self.state=3           # Start adding undef entries
        
    def undef_function(self,cline):
        # Look for end of feature undefines
        if cline.starts_with("#endif"):
            print(self.undef)
            self.undefined.append(self.undef)  # Save CUndef object in list
            self.undef=None    # Reset the CUndef being built to None
            self.state=2       # Return to looking for another feature
            return

        if not cline.starts_with(" UNDEF_INST("):
            return

        # Extract the function name from the entry
        line=cline.line.rstrip()
        try:
            rparen=line.index(")")
        except ValueError:
            raise ValueError("%s missing right parenthesis: %s" \
                % (eloc(self,"undef_function"),cline)) from None

        function=line[12:rparen]
        self.undef.function(function,cline.lineno)



# Object for processing of the Hercules s37x.c module
class C37x(CSource):
    def __init__(self):
        super().__init__("s37x.c")

        # Parse state
        #  0 == Looking for start of an opcode table
        #  1 == Within an opcode table
        self.state=0

        # Parse results
        self.tables={}       # Dictionary of CTable objects by name
        self.tbllist=[]      # List of CTable objects as found in opcode.c

        # Accumulated data while within an optode definition
        self.start=None      # First line of the opcode table
        self.end=None        # Ending line of the opcode table
        self.table_name=None # Table being extracted
        self.opcodes=[]      # Accumulated lines of opcode definitions

    # Adds a new table to the module and resets table parse information for next table
    def new_table(self,tbl):
        assert isinstance(tbl,CTable_S37X),\
            "%s 'tbl' argument not a CTable_S37X object: %s" \
                % (eloc(self,"new_table"),tbl)

        self.tables[self.table_name]=tbl
        self.tbllist.append(tbl)
        self.reset()

    def parse(self,debug=False):
        for cline in self.clines:
            if self.state==0:
                # Looking for start of a table
                self.table_begin(cline)
            elif self.state==1:
                # processing table entries
                self.table_entry(cline)
            else:
                raise ValueError("unexpected parse state: %s" % self.state)

        if not debug:
            return

        for table in self.tbllist:
            print("")
            print(table)
            table.display()

    # Reset parse state for a new table
    def reset(self):
        self.end=self.start=self.table_name=None
        self.opcodes=[]
        self.state=0

    # Provide a summary of the table information.
    def summary(self):
        entries=0
        for t in self.tbllist:
            entries+=t.count
        print("   tables: %s, entries: %s" % (len(self.tbllist),entries))
        for t in self.tbllist:
            entry="    %s  entries: %2d instructions: %2d" % (t.name,t.count,t.count)
            if t.other:
                entry="%s  %s" % (entry,t.other)
            print(entry)

    # Determine if a new table is being started
    # Side effects when starting:
    #    - preserves table name and module line number for later reference
    #    - sets self.start to 1, indicating a table is being processed
    def table_begin(self,cline):
        text=cline.line
        start="INST37X_TABLE_START"
        slen=len(start)
        if len(text)<slen:
            return
        if text[:slen]!=start:
            return
        # Start of table detected
        self.table_name=text[slen+1:-1]
        self.start=cline.lineno
        self.state=1

    # Detect the end of a table.
    # Returns:
    #   True  if end of table statement found
    #   False if table ending statement not found
    # Side Effects when True returned:
    #   - table parse information reset by new_table() method.
    #   - sets self.state to 0, indicating outside of a table definition.
    def table_end(self,cline):
        text=cline.line
        end="INST37X_TABLE_END"
        elen=len(end)
        if len(text)<elen:
            return False
        if text[:elen]!=end:
            return False
        # End of table found
        self.end=cline.lineno

        if len(text)!=elen+4:
            print("[%s] end of table statement length unexpected (%s): %s - %s" \
                % (cline.lineno,elen+4,len(text),cline))

        end_name=text[elen+1:-1]
        if end_name != self.table_name:
            print("[%s] table name and end of table name do not agree: %s:%s - %s" \
                % (cline.lineno,self.table_name,end_name,cline))
            return False

        # Add the current table being contstructed to the module
        tbl=CTable_S37X(self.table_name,self.start,self.end,self.opcodes)
        self.new_table(tbl)   # Add the new table to the module
        # Table parse information is reset.

        return True

    def table_entry(self,cline):
        if self.table_end(cline):
            return
        text=cline.line
        if len(text)>=2 and text[:2]=="//":
            # Ignore comment lines
            return
        sep=cline.line.split()
        if len(sep)!=3:
            print("unexpected enty format: sep: %s - %s" % (sep,cline))
            return
        if sep[1]!="INST37X":
            print("unexpected entry name: %s - %s" % (sep[1],cline))
            return

        opcode=sep[0]
        if opcode[:2]!="/*" or opcode[-2:]!="*/":
            print("unrecognized opcode: %s" % cline)
            return
        opcode=opcode[2:-2]

        function=sep[2]
        if len(function)<2:
            print("unexpected function: %s - %s" % (function,cline))
            return
        if function[0]!="(" or function[-1]!=")":
            print("function paranethensis not found: %s" % cline)
            return
        function=function[1:-1]   # Remove the parenthesis
        sep=function.split(",")
        if len(sep)!=2:
            print("function contains more than one comma: %s - %s" % (sep,cline))
            return
        func=sep[0]
        pos=sep[1]
        if len(pos)<=2:
            try:
                pos=int(pos)
            except ValueError:
                print("invalid decimal index: '%s' - %s" % (pos,cline))
                return
        elif pos[:2]=="0x":
            try:
                pos=int(pos[2:],16)
            except ValueError:
                print("invalid hexadecimal index: %s - %s" % (pos,cline))
                return
        else:
            print("opcode table index invalid: '%s' - %s" % (pos,cline))
            return

        entry=CEntry_S37X(cline.lineno,func,pos,opcode)
        self.opcodes.append(entry)


#
#  +-------------------------------+
#  |                               |
#  |   Hercules Table Processing   |
#  |                               |
#  +-------------------------------+
#

# This object encapsulates a single instruction operation code definition
class Op(object):
    def __init__(self,opc,source):
        assert isinstance(opc,int),\
            "%s 'opc' argument must be an integer: %s" \
                % (eloc(self,"__init__"),opc)

        self.opc=opc          # The opcode as an integer
        self.source=source    # The object on which this entry is based

        self.mnem=[]          # The mnemnic's for the opcode as a list of strings

    def __str__(self):
        opc="%02X" % self.opc
        opc=opc.ljust(4)
        if len(self.mnem)==0:
            return opc
        elif len(self.mnem)==1:
            return "%s %s" % (opc,self.mnem[0])
        else:
            return "%s %s" % (opc,self.mnem)

    def add_mnem(self,mnem):
        self.mnem.append(mnem)


# Hercules instructions are unique based upon operation codes.  MSL database
# instructions are unique based upon mnemonic.  This object will build an opcode
# table based upon operation codes from either source.  It is Opcode objects that
# are compared in the audit process when the Opcode.audit() is called.
class Opcode(object):
    def __init__(self,arch,obj,source=None):
        self.name=arch      # Architecture name
        self.inst={}        # Dictionary of supported opcodes (integers) to mnemonics
        self.source=source  # Source of the operation codes: 'MSL' or 'Hercules'

        self.build_from_source(obj)

    def __str__(self):
        return "%s from %s, operation codes: %s" \
            % (self.name,self.source,len(self.inst))

    # This method examines all of this Op objects residing in the inst attribute 
    # of two Opcodes objects.
    #
    # Returns:
    #   a tuple of lists:
    #   tuple[0]  All of this Opcode's inst entries (Op objects) found in the other
    #   tupel[1]  All of this Opcode's inst entries not found in the other
    def audit(self,other):
        assert isinstance(other,Opcode),\
            "%s 'other' argument must be an Opcode object: %s" \
                % (eloc(self,"audit"),other)
   
        oinst=other.inst
        in_other=[]
        not_in_other=[]

        for op in self.inst.keys():
            try:
                oinst[op]
                in_other.append(self.inst[op])
            except KeyError:
                not_in_other.append(self.inst[op])
        return (in_other,not_in_other)

    def dump(self):
        keys=list(self.inst.keys())
        keys.sort()
        for k in keys:
            print(self.inst[k])

  #
  # Methods that must be supplied by a subclass
  #

    def build_from_source(self,obj):
        raise NotImplementedError(\
            "%s subclass %s must supply build_from_source() method" \
                % (eloc(self,"build_from_source"),self.__class__.__name__))


# This object normalizes the information from the Hercules for an architecture
# into a dictionary of Op objects.  An instance of this object is created by
# the architecture's HArch object in the HArch.build() method.
#
# Instance Arbuments:
#   arch   The name of the architecture
#   obj    The source HArch object.  HArch presents itself for normalization in the
#          HArch.build() method.
class HOpcode(Opcode):
    def __init__(self,arch,obj):
        assert isinstance(obj,HArch),\
            "%s 'obj' argument must be an instance of HArch: %s" \
                % (eloc(self,"__init__"),obj)

        super().__init__(arch,obj,source="Hercules")

    # Convert the source HArch information into a dictionary of Op objects
    # keyed to the instruction opcode encoded as an integer.
    def build_from_source(self,obj):
        # The inst dictionary is keyed by instruction operation codes.  The MSL
        # database may support multiple mnemonics for the same operation code.
        # So, a list is created for each operation code of its valid mnemonics.
        for opc in obj.opcodes:
            # opc is a CEntry object
            opcode=opc.opcode
            try:
                mnem=self.inst[opcode]
                # If found in the dictionary, mnem is an Op object.
            except KeyError:
                # Convert Hercules opcode string into an integer
                if len(opcode)==4 and opcode[2]=="x":
                    op="%s%s" % (opcode[:2],opcode[3])
                    op=int(op,16)
                else:
                    op=int(opcode,16)
                mnem=Op(op,opc)
            mnem.add_mnem(opc.mnemonic)
            self.inst[op]=mnem


# This object normalizes the information from the MSL database for an architecture
# into a dictionary of Op objects.  An instance of this object is created by the 
# architecture's HArch object during the HArch object's instantiation.
#
# Instance Arbuments:
#   arch   The name of the architecture
#   obj    The source MSL database object (an instance of msldb.CPUX).
class MOpcode(Opcode):
    def __init__(self,arch,obj):
        assert isinstance(obj,msldb.CPUX),\
            "%s 'obj' argument must be an instance of msldb.CPUX: %s" \
                % (eloc(self,"__init__"),obj)

        super().__init__(arch,obj,source="MSL")

    # Convert the source msldb.CPUX information into a dictionary of Op objects
    # keyed to the instruction opcode encoded as an integer.
    def build_from_source(self,obj):
        # Get the dictionary of instruction mnemonics
        factors=msldb.Inst.opcode_factor
        for mnem,inst in obj.inst.items():
            if inst.extended:
                # Ignore extended instruction mnemonics
                continue

            # Convert the opcode information in the MSL database to an integer
            op1=inst.opcode[0]
            op2=inst.opcode[1]
            if op1 in [0x80,0x82,0x93,0x9C,0x9D,0x9E,0x9F] and op2==0:
                # Special handling for MSL instructions treated as multi-byte when
                # one byte ops.
                opc=op1
            else:
                opc=(op1*factors[inst.opc_len])+op2

            # opc is the opcode as an integer
            try:
                mnem=self.inst[opc]
            except KeyError:
                mnem=Op(opc,inst)
            mnem.add_mnem(inst.mnemonic)
            self.inst[opc]=mnem


# This object contains all of the information for _one_ Hercules architecture.
# The results of the parsed modules and the MSL database for the architecture
# form the basis of the objects information.
#
# The object creates two instances of the Opcode object.  One uses the MOpcode
# subclass to convert the MSL database information into a normalized format
#
# The other Opcode object results from use of this object to consolidate the
# information from the Hercules opcode.c source module for the architecture.
# The information from opcode.c is supplied via the add() method.  Once the
# information is available, the second Opcode object, the HOpcode subclass, can
# be created using the build() method.  Both the add() and build() methods are
# called by the instantiator of the HArch object, namely, the HTables object, in
# the HTables.sanity() method.
#
# Ultimately the two Opcode objects (an HOpcode and MOpcode instance) are compared
# by the audit() method when it is called by the HTables.sanity() method.
class HArch(object):
    def __init__(self,name,mslpath,mslfile,mslcpu):
        self.name=name        # Architecture name

        # These objects contain the consolidated results for an architecture
        # found in the parsed Hercules source modules.
        self.opcodes=[]       # CEntry list of operations defined for the arch.
        self.mnemonic={}      # CEntry dictionary of operations by mnemonic

        # MSL related information and CPU database
        self.mslpath=mslpath          # Default MSL path
        self.mslfile=mslfile          # MSL file for verification
        self.mslcpu=mslcpu            # MSL cpu for verification
        self.cpu=self.getCPU()        # Expanded CPU definition from MSL file.

        self.duplicates=[]    # Duplicate instructions

        # These two Opcode objects form the basis of the operation code audit
        self.msl=MOpcode(self.name,self.cpu)
        self.herc=None   # See build() method

        # Opcode Audit results for this Hercules architecture.
        # Each list contains Op objects corresponding to the list information.
        self.h_in_m=[]        # Op objects in Hercules _and_ in MSL database
        self.h_not_in_m=[]    # Op objects in Hercules _not_ in MSL database
        self.m_in_h=[]        # Op objects in MSL database and in Hercules
        self.m_not_in_h=[]    # Op objects in MSL database _not_ in Hercules
        # Note: the opcodes in self.h_in_m and self.m_in_h are the same.  Howether
        # the sources are different and the information is used differently in
        # the detail lines.  Both sets are required for the report.

    def __str__(self):
        if len(self.duplicates)>0:
            dup=" duplicates: %s" % len(self.duplicates)
        else:
            dup=""
        return "Hercules: %s instructions: %s%s" % (self.name,len(self.opcodes),dup)

    # Add information extracted from Hercules opcode.c.
    def add(self,entry):
        assert isinstance(entry,CEntry),\
            "%s 'entry' argument must be a CEntry object: %s" \
                % (eloc(self,"add"),entry)

        self.opcodes.append(entry)
        try:
            found=self.mnemonic[entry.mnemonic]
            print("%s instruction '%s' already defined at opcode.c[%s]: %s" \
                % (self.name,entry.mnemonic,found.lineno,entry))
            self.duplicates.append(found)
        except KeyError:
            self.mnemonic[entry.mnemonic]=entry

    # Perform the audit of the Hercules architecture against the MSL database
    def audit(self):
        self.h_in_m,self.h_not_in_m=self.herc.audit(self.msl)
        self.m_in_h,self.m_not_in_h=self.msl.audit(self.herc)
        print("%s Hercules vs. MSL opcodes: match: %s  no match: %s" \
            % (self.name,len(self.h_in_m),len(self.h_not_in_m)))
        print("%s MSL vs. Hercules opcodes: match: %s  no match: %s" \
            % (self.name,len(self.m_in_h),len(self.m_not_in_h)))

    # This method creates the Hercules version of the Opcode object after all of
    # the opcode.c information has been incorporated by the add() method.
    def build(self):
        self.herc=HOpcode(self.name,self)
        print(self.herc)
        print(self.msl)

    # Retrieves the CPU definition from the MSL database.  It uses the MSL database
    # selection information saved when this object is instantiated to access the
    # MSL database.
    # Returns:
    #   msldb.CPUX object.  This object contains all of the supported mnemonics
    #   and operation codes for the selected cpu defined in the selected MSL file.
    def getCPU(self,debug=False):
        # Determine the directory search order for the MSL database
        pathmgr=satkutil.PathMgr(variable="MSLPATH",default=self.mslpath,\
            debug=debug)
        # Create MSL database processor that reads MSL definitions.
        mslproc=msldb.MSL(pathmgr=pathmgr,debug=debug)
        # Build an instance of the database for a specific architecture definition
        mslproc.build(self.mslfile,fail=True)
        # Extract from the architecture (in expanded format) the definition for the
        # specific CPU.  Return the msldb.CPUX object for this CPU.
        return mslproc.expand(self.mslcpu)

    # Update final report with detail information
    def report(self,rpt):
        assert isinstance(rpt,Report),\
            "%s 'rpt' argument must be a Report object: %s" \
                % (eloc(self,"report"),rpt)

        arch=self.name
        for n in self.h_in_m:
            rpt.h_in_m(arch,n)
        for n in self.h_not_in_m:
            rpt.h_not_in_m(arch,n)
        for n in self.m_in_h:
            rpt.m_in_h(arch,n)
        for n in self.m_not_in_h:
            rpt.m_not_in_h(arch,n)


# This class extracts from the module parsed results for all Hercules architectures
# and the corresponding MSL cpu definitions.  The Hercules information is processed
# for internal integrety and merged with the MSL database information.
# 
# Instance Arguments:
#   opcode   Infomration extracted from Hercules opcode.c source module
#   s37x     Information extracted from Hercules s37x.c source module
#   mslpath  The path to the MSL database.
class HTables(object):
    def __init__(self,opcode,s37x,mslpath,hfeatures):
        assert isinstance(opcode,COpcodes),\
            "%s 'opcode' argument must be a COpcodes object: %s" \
                % (eloc(self,"__init__"),opcode)
        assert isinstance(s37x,C37x),\
            "%s 's37x' argument must be a C37x object: %s" \
                % (eloc(self,"__init__"),s37x)
        assert isinstance(hfeatures,HFeatures),\
            "%s 'hfeatures' argument must be a HFeatures object: %s" \
                % (eloc(self,"__init__"),hfeatures)

        # s37x.c Tables (CTable_S37X objects):
        self.s37xd=s37x.tables      # Tables by name
        self.s37xs=s37x.tbllist     # Tables by sequence found

        # Feature tables from featxxx.h and opcode.c
        self.hfeatures=hfeatures    # Features from featxxx.h
        # Update features with instruction function information from opcode.c
        self.hfeatures.add_functions(opcode.undefined)

        # opcode.c Tables (CTable objects):
        self.opcd=opcode.tables     # Table by name
        self.opcs=opcode.tbllist    # Table by sequence found
        self.vopcd=opcode.vtables   # Vector tables by name
        self.vopcs=opcode.vtables   # Vector tables by sequence found
        self.iopcs=opcode.ignored   # Ignored optimization tables by sequence found

        # The following attributes are built by the sanity() method

        # CEntry objects with GENx37X but... no s37x.c table entry
        self.missing_s37x=[]       # ... no s37x.c table entry
        self.wrong_s37x=[]         # --- wrong s37x.c function in entry
        # CEntry_S37X objects referencing opcode.c entry not enabled for s37x:
        self.wrong_opcode=[]

        # Final instruction tables by architecuture.
        self.s370=HArch("370",mslpath,"s370-insn.msl", "s370")
        self.s37x=HArch("37X",mslpath,"s380-insn.msl", "s380")
        self.s390=HArch("390",mslpath,"s390x-insn.msl","s390")
        self.s900=HArch("900",mslpath,"s390x-insn.msl","s390x")
        self.alist=[self.s370,self.s37x,self.s390,self.s900]
        # Each HArch object has already read the MSL database.

        # Performs sanaty checks and build the instruction data from Hercules
        # source files and perform the audit.
        self.sanity()

    # Perform a set of sanity checks on the Hercules information and separate
    # the supported instructions by architecture.  Finally performs the audit
    # agains the MSL database.
    def sanity(self):
        # Check that s37x.c entry has a corresponding entry in opcode.c
        for t in self.s37xs:
            # t is a CTable_S37X object
            try:
                ot=self.opcd[t.other]    # opcode.c table name for this s37x.c table
                # ot is a CTable object
            except KeyError:
                raise ValueError("%s unrecognized opcode.c table name %s: %s" \
                    % (eloc(self,"sanity"),t,t.other)) from None
            for ntry in t.entries:
                # ntry is a CEntry_S37X object
                try:
                    oe=ot.entries[ntry.ndx]
                    # oe is an CEntry object
                except IndexError:
                    raise ValueError(\
                        "%s opcode.c table %s has no entry for index: %s" \
                            % (eloc(self,"sanity"),ot.name,ntry.ndx)) from None
                ntry.opcode_line=oe.lineno    # Update s37x.c with opcode.c line
                oe.s37x_line=ntry.lineno      # Update opcode.c with s37x.c line
                oe.s37x_func=ntry.function    # Update opcode.c with s37x.c function
                if not oe.s37x:
                    self.wrong_opcode.append(ntry)

        # Check that each opcode.c entry enabled for s37x has a function and it
        # matches the other architecture functions
        for t in self.opcs:
            # t is an CTable object
            for ntry in t.entries:
                # ntry is a CEntry object
                if ntry.null or ntry.level2:
                    # ignore null entries and level 2 entries
                    continue
                if ntry.s37x:
                    if ntry.s37x_func is None:
                        ntry.s37x=False
                        self.missing_s37x.append(ntry)
                    elif ntry.function!=ntry.s37x_func:
                        ntry.s37x=False
                        self.wrong_s37x.append(ntry)
                if ntry.s370:
                    self.s370.add(ntry)
                    self.s37x.add(ntry)
                if ntry.s37x:
                    self.s37x.add(ntry)
                if ntry.s390:
                    self.s390.add(ntry)
                if ntry.s900:
                    self.s900.add(ntry)

        # Print summary errors.
        if len(self.wrong_opcode)>0:
            print("s37x.c entries referencing opcode.c entryies not GENx37X" \
                % len(self.wrong_opcode))
        if len(self.missing_s37x)>0:
            print("opcode.c GENx37X entries not enabled by s37x.c: %s" \
                % len(self.missing_s37x))
            for n in self.missing_s37x:
                print("    [%s] %s %s" % (n.lineno,n.opcode,n.mnemonic))
        if len(self.wrong_s37x)>0:
            print("s37x.c entries with wrong instruction function: %s" \
                % len(self.wrong_s37x))

        for a in self.alist:
            a.build()

        for a in self.alist:
            a.audit()

    # This method updates the report with information for the detail lines.
    def report(self,rpt):
        assert isinstance(rpt,Report),\
            "%s 'rpt' argument must be a Report object: %s" \
                % (eloc(self,"report"),rpt)

        # For each architecture add its audit information to the detail lines.
        for a in self.alist:
            a.report(rpt)



#
#  +----------------------------+
#  |                            |
#  |   Opcode Audit Reporting   |
#  |                            |
#  +----------------------------+
#

# This object encapsulates the Hercules and MSL database data for an individual
# operation code.  It is the information contained in a report detail line.
#
# The Detail object is created the first time an opcode is encountered.  See the 
# Report.getDetail() method.  Thereafter the object is updated with information
# about the opcode's availability in the four supported Hercules architecture
# contexts and corresponding availability in the MSL database for the corresponding
# architecture.
class Detail(object):
    # Instruction opcodes using four bits for extended opcode.  All other extended
    # opcodes use eight additional bits.
    bits12=[0xA5,0xA7,0xC0,0xC2,0xC4,0xC6,0xC8,0xCC]

    # This method is used to compare operation codes between two Detail objects
    # when being sorted.
    #
    # Returns:
    #   1  if this object is "greater than" the other object
    #   0  if this object is "equal" to the other object
    #  -1  if this object is "less than" the other object
    #
    # Objects considered "less than" appear before the "greater than" object
    # Equal objects (actually not possible in this case) will sort in the
    # order they are encountered.
    #
    # See method Report.sort() for usage.
    @staticmethod
    def compare(self,other):
        if self.opc1<other.opc1:
            return -1
        if self.opc1>other.opc1:
            return 1

        # Bits 0-7 of operation code are equal
        # Compare additional bits.
        # Additional bits are considered greater than no additional bits
        if self.opc2 is None:
            if self.opc2 is not None:
                return -1
            return 0
        if other.opc2 is None:
            return 1

        # Both Detail objects have a numeric value for the bits 8-11 or bits 8-15
        if self.opc2<other.opc2:
            return -1
        if self.opc2>other.opc2:
            return 1

        # Consider these object equal
        return 0

    def __init__(self):
        self.opc=None      # Instruction opcode
        self.opc1=None     # Bits 0-7 of instruction operation code
        self.opc2=None     # Bits 7+ of instruction operation code
        # Hercules Architecture specific detail:
        #          370   37X   390   900
        self.arch=[False,False,False,False]    # True when Hercules supports opcd
        self.hnem=[None, None, None, None]     # Hercules mnemonics (strings)
        self.mnem=[None, None, None, None]     # MSL Database mnemonics (string list)
        # These lists are update by:
        #  self.arch - Report.h_in_m and Report.h_not_in_m (setting entry to True)
        #  self.hnem - Report.h_in_m and Report.h_not_in_m
        #  self.mnem - Report.m_in_h and Reprot.m_not_in_h

    # This method formats the architecture column in the operation code's detail
    # line.
    # Method Arguments:
    #   ndx   An index corresponding to the architecture.
    #   maxsz The maximum size of the mnemonic for the column.
    #
    # Returns:
    #   A string, left justified and of length maxsz when maxsz used 
    #
    #  ' H:MNEMONIC' if supported by Hercules and MSL database
    #  '?H:MNEMONIC' if supported by Hercules and MSL database, but mnemonics differ.
    #                The Hercules MNEMONIC is used.
    #  '*H:MNEMONIC' if supported by Hercules but not defined in MSL database
    #  ' M:MNEMONIC' if not supported by Hercules but present in MSL database
    #  '           '  if not supported by either Hercules or MSL database.
    def fmt_arch(self,ndx,maxsz=None):
        arch=self.arch[ndx]
        hnem=self.hnem[ndx]     # A single string
        mnem=self.mnem[ndx]     # A list of strings
        if arch:
            if maxsz:
                ntry=hnem.ljust(maxsz)
            else:
                ntry=hnem
            if mnem is None or len(mnem)==0:
                flag="*"
            else:
                if hnem in mnem:
                    flag=" "
                else:
                    flag="?"
            ntry="%sH:%s" % (flag,ntry)
        else:
            # Instruction not supported by Hercules for this architecture index
            if mnem is None:
                # Instruction is also not defined for this architecture in MSL
                return ""

            # MSL database has it defined
            assert isinstance(mnem,list),\
                "%s opcode %s arch index %s MSL mnemonic not a list: %s" \
                    % (eloc(self,"fmt_arch"),self.fmt_opcode(),ndx,mnem)

            # Use the first entry of the MSL list
            mnem=mnem[0]
            if mnem:
                if maxsz:
                    ntry=mnem.ljust(maxsz)
                else:
                    ntry=mnem
                ntry=" M:%s" % ntry
            else:
                if maxsz:
                    ntry=" ".ljust(maxsz+3)
                else:
                    ntry=""
        return ntry

    # This method formats the opcode column in the operation code's detail line.
    def fmt_opcode(self):
        opcode="%02X" % self.opc1
        if self.opc2 is not None:
            if self.opc1 in Detail.bits12:
                opcode="%s%X" % (opcode,self.opc2)
            else:
                opcode="%s%02X" % (opcode,self.opc2)
        return opcode

    # This method formats the detail line when being displayed using the Python
    # print() method.
    # Returns:
    #   A string representing the detail line.
    def format(self,maxsz):
        string=self.fmt_opcode()
        string=string.ljust(6)
        for n in range(4):
            m=maxsz[n]
            string="%s %s" % (string,self.fmt_arch(n,m))
        return string

    # Sets the operation code and splits multibyte opcodes
    def opcode(self,opc):
        self.opc=opc
        if opc<0x100:
            self.opc1=opc
            # self.opc2 will remain None.  This is why the compare() method must
            # check for None when comparing Detail objects.
            return
        elif opc<0x1000:
            opc1,opc2=divmod(opc,16)
            if opc1 in Detail.bits12:
                self.opc1=opc1
                self.opc2=opc2
                return
        self.opc1,self.opc2=divmod(opc,256)


class Report(object):
    ndx={"370":0,"37X":1,"390":2,"900":3}
    def __init__(self):
        self.details=[]       # List of Detail objects 
        self.detopc={}        # Where Detail objects are constructed
        self.maxsz=[0,0,0,0]  # Maximum mnemonic length by arch

    def __str__(self):
        return "Report operation codes: %s" % len(self.detopc)

    def __max(self,ndx,name):
        assert isinstance(name,str),\
            "%s 'name' argument must be a string: %s" \
                % (eloc(self,"__max"),name)

        size=self.maxsz[ndx]
        maxsz=max(size,len(name))
        self.maxsz[ndx]=maxsz

    def display(self):
        for detail in self.sort():
            print(detail.format(self.maxsz))

    # This method creates a new Detail object for an operation code and returns
    # the new object or the previously created object.
    def getDetail(self,op):
        assert isinstance(op,Op),\
            "%s 'op' argument must be an Op object: %s" \
                % (eloc(self,"getOp"),op)

        try:
            return self.detopc[op.opc]
        except KeyError:
            detail=Detail()
            detail.opcode(op.opc)
            self.detopc[op.opc]=detail
            return detail

    # Returns the Mnemonic information
    def getHercMnem(self,op):
        m=op.mnem
        if len(m)==0:
            return ""
        elif len(m)==1:
            return m[0]
        else:
            print("Multiple Hercules mnemonics: %s" % op)
            return m

    # Update the Detail object from: defined by Hercules and MSL database, saving
    # Hercules information.
    def h_in_m(self,arch,op):
        ndx=Report.ndx[arch]

        # Update Detail object with Hercules info
        det=self.getDetail(op)
        det.arch[ndx]=True
        m=self.getHercMnem(op)
        det.hnem[ndx]=m
        self.__max(ndx,m)

    # Update the Detail object from: defined by Hercules but not MSL database, 
    # saving Hercules information.
    def h_not_in_m(self,arch,op):
        self.h_in_m(arch,op)

    # Create the report listing.  This is similar to the display() method but
    # fully formats the report with pages, headings, etc.
    def listing(self,filename=None):
        report=ReportListing(self)
        report.create(listing=filename)

    # Update the Detail object from: defined by MSL database and Hercules, saving
    # MSL information.  While the opcodes will be the same as h_in_m, the mnemonics
    # may differ.  This is used to detect differences in mnemonic usage.
    def m_in_h(self,arch,op):
        ndx=Report.ndx[arch]

        # Update Detail object with MSL info
        det=self.getDetail(op)
        mnem=op.mnem
        det.mnem[ndx]=mnem
        for m in mnem:
            self.__max(ndx,m)
        if len(mnem)>1:
            print("Multiple MSL mnemonics (%s): %s" % (arch,op))

    # Update the Detail object from: defined by MSL database and not supported by
    # Hercules, saving the MSL information.
    def m_not_in_h(self,arch,op):
        self.m_in_h(arch,op)

    # Returns a list of Detail objects sorted by opcode
    def sort(self):
        ops=list(self.detopc.values())
        ops.sort(key=functools.cmp_to_key(Detail.compare))
        return ops


# This object uses the listing.py tool to create a paged listing.  The generic
# Report object is supplied for access to the detailed information being reported.
#
# The listing tool separates the title, heading and detail line creation from the
# actual report creation.   The corresponding lines are created using a set of
# objects.  The objects help in formating the line.  The report creation object,
# based upon listing.Listing, simply requests strings for the separate portions of
# the page.  These strings may be created however the specific report requires,
# using or not the formatting tools provided by the listing module.
class ReportListing(Listing):
    def __init__(self,rpt):
        assert isinstance(rpt,Report),\
            "%s 'rpt' argument must be a Report object: %s" \
                % (eloc(self,"__init__"),rpt)

        super().__init__(self)
        self.rpt=rpt          # Report object providing support for the listing
        self.linesize=90      # Length of the report line

        # Detail line creation uses these attributes
        self.details=self.rpt.sort()   # List of Detail objects for the report
        self.next=0                    # Index of next Detail object

        # These attributes are provided by the build() method.  They are used
        # to format specific portions of the listing page.
        self.ttl=None        # Report title Listing.Title object
        self.header=None     # Heading - string
        self.det=None        # Detail - Listing.Group object

        # Use different methods to supply detail lines in the report
        self.multiline=Multiline(self)

    # Create listing format opbjects for this report.
    def build(self):
        # Craate the report title
        title=Title(self.linesize,pages=99999)
        title.setLeft(columns=[DateTimeCol(now=None,sep=2),])
        title.setRight(columns=[])
        title.setTitle("Hercules Instruction Operation Codes",center=True)
        self.ttl=title

        # Create detail and heading formats
        d=[]
        h=[]

        opc=CharCol(4,just="left",sep=3,colnum=0)
        opch=CharCol(4,just="center",sep=3,default="OPCD",colnum=0)
        d.append(opc)
        h.append(opch)

        archs=["370","37X","390","900"]
        for n,size in enumerate(self.rpt.maxsz):
            col=n+1
            colsz=size+3
            arch=CharCol(colsz,just="left",sep=3,colnum=col)
            archh=CharCol(colsz,just="center",sep=3,default=archs[n],colnum=col)
            d.append(arch)
            h.append(archh)

        header=Group(columns=h)
        self.header=header.string(values=[None,None,None,None,None])
        self.det=Group(columns=d)

        # Create Part
        self.multiline.part(self.multiline_key,header=self.multiline_heading)
        self.multiline.part(self.multiline_detail)
        self.multiline.start()

    # Create the listing
    def create(self,listing=None):
        self.build()             # Create format objects for the report
        # Create the actual listing
        listing=self.generate(filename=listing)

  #
  #  These methods are called by the super class to provide either a title
  #  heading or detail line.
  #

    def detail(self):
        return self.multiline.detail()

    def heading(self):
        return self.multiline.header()

    def title(self):
        return self.ttl.string(left=[None,],right=[])

  #
  # These methods support individual listing parts
  #

    def multiline_detail(self,multiline):
        if self.next>=len(self.details):
            multiline.more([],done=True)
            return None       # Return None when listing is complete
        detail=self.details[self.next]
        self.next+=1

        fields=[]
        fields.append(detail.fmt_opcode())
        for arch in range(4):
            fields.append(detail.fmt_arch(arch))

        multiline.more(self.det.string(values=fields))

    def multiline_heading(self):
        return self.header

    def multiline_key(self,multiline):
        lines=[]
        lines.append("Key:  H - Hercules and MSL support, Hercules mnemonic reported")
        lines.append("     *H - Hercules only supports, Hercules mnemonic reported")
        lines.append("     ?H - Hercules and MSL support, reported Hercules "
            "mnemonic differs from MSL")
        lines.append("      M - MSL only supports, MSL mnemonic reported")
        lines.append("")
        lines.append("")
        multiline.more(lines,partdone=True)


#
#  +-------------------------------------+
#  |                                     |
#  |   Opcode Audit Utility Processing   |
#  |                                     |
#  +-------------------------------------+
#

class Hercules_Opcodes(object):
    # The classes that process specific source modules
    file_cls=[CFeat370,CFeat390,CFeat900,COpcodes,C37x]
    def __init__(self,args,mslpath):
        self.args=args         # argparse Namespace object
        self.mslpath=mslpath   # Root directory of MSL filles

        # Locate the Hercules root source directory
        if args.Hercules is None:
            self.herc_dir=os.getcwd()
        else:
            self.herc_dir=args.Hercules
        self.listing=args.listing

        # Determine if report is displayed
        self.verbose=args.verbose

        # Determine location of output report
        self.listing=None
        if args.listing is not None:
            self.listing=args.listing
        else:
            # Otherwise force report display
            self.verbose=True

        # Hercules source file objects:
        self.source={}   # dictionary of source input files as text strings
        self.src_seq=[]  # list of source objects in sequence

        # Initialize the CTable dictionary that points a CTable to its CTable_S37X
        # table that modifies it.
        CTable.init_S37X_table()
        # Now the CTable objects can be mapped to their corresponding CTable_S37X
        # object

        # Run-time information
        self.hfeatures=None
        self.htables=None

        # Report
        self.report=Report()

    # Perform the operation code audit
    def run(self,debug=False):
        # Parse Hercules source files:
        self.src_seq=[]
        for fcls in Hercules_Opcodes.file_cls:
            source=fcls()
            source.getSource(self.herc_dir)
            self.source[source.filename]=source
            self.src_seq.append(source)

        if debug:
            for csrc in self.src_seq:
                print(csrc)
                csrc.parse()
                csrc.summary()
                print("")
                
        # Build the feature comparison information
        self.hfeatures=HFeatures(\
            self.source["feat370.h"],
            self.source["feat390.h"],
            self.source["feat900.h"])

        # Consolidate Hercules tables into one object
        self.htables=HTables(self.source["opcode.c"],self.source["s37x.c"],\
            self.mslpath,self.hfeatures)
        self.hfeatures.summary()
        # At this point the audit against the MSL database has been completed for
        # all of the Hercules architectures.

        self.htables.report(self.report)
        print(self.report)
        # Report detail lines have been created for output creation

        # Create the listing
        self.report.listing(filename=self.listing)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)
