#!/usr/bin/python3
# Copyright (C) 2014 Harold Grovesteen
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

# This module builds machine instructions for ASMA.

# Python imports: None
# SATK imports: None

# ASMA imports:
import assembler
import msldb        # Access the Machine Specification Language Processor


#
#  +--------------------------------------+
#  |                                      |
#  |   Range Check User Error Exception   |
#  |                                      | 
#  +--------------------------------------+
#

class RangeCheckError(Exception):
    def __init__(self,low,high,size,value):
        self.low=low         # Minimum value in range
        self.high=high       # Maximum value in range
        self.value=value     # Value that is out of range
        self.size=size       # Size of the field
        string="value outside of range for %s-bit field ( %s - %s ): %s"\
            % (self.size,self.low,self.high,self.value)
        super().__init__(string)


#
#  +---------------------------------------------+
#  |                                             |
#  |   Instruction Builder and Related Classes   |
#  |                                             | 
#  +---------------------------------------------+
#

# This class supports the construction of machine instructions based upon an instance
# of assembler.Stmt presented to the build engine.  The instance is updated with 
# the constructed instruction.
class Builder(object):
    type_check=True     # method argument type check switch
    def __init__(self,machine,msl,msldft=None,trace=False):
        # Each of these lists is indexed by number of bits in a field.  The first
        # entry (index 0) is nonsensical, because you need at least 1 bit for a field.
        # The second entry in the signed field (index 1) is nonsensical because you
        # you need at least two bits for a signed value, one for the sign and one for
        # two's complement value.  These lists are used to ensure values can fit within
        # a machine instruction field.  An AssemblerError is generated if the value
        # supplied by the assembler is out of range.

        # tuple of ranges for unsigned fields
        self.fld_range=[(None,None),]
        # tuple of ranges for signed fields
        self.fld_srange=[(None,None),(None,None)]

        # Calculate signed and unsigned values for signed and unsigned fields upto
        # 64-bits, the maximum single field used in any instruction or other structure.
        for n in range(1,65):
            this_max=1<<n

            unsigned_max=this_max-1
            rang=(0,unsigned_max)
            self.fld_range.append(rang)

            if n<2:
                continue
            signed_max=this_max>>1
            rang=(-1*signed_max,signed_max-1)
            self.fld_srange.append(rang)

        if trace:
            print("Build unsigned field ranges:")
            for n in range(len(self.fld_range)):
                rang=self.fld_range[n]
                minimum=rang[0]
                maximum=rang[1]
                print("    [%s] %s - %s" % (n,minimum,maximum))
            print("Build signed field ranges:")
            for n in range(len(self.fld_srange)):
                rang=self.fld_srange[n]
                minimum=rang[0]
                maximum=rang[1]
                print("    [%s] %s - %s" % (n,minimum,maximum))

        # These attributes are set by __getMachine()
        self.addrsize=None   # Maximum address size supported by the CPU
        self.ccw=None        # Expected CCw format used by the CPU
        self.psw=None        # Expected PSW format used by the CPU
        self.cache=self.__getMachine(machine,msl,msldft=msldft)

    # Create the MSL cache and supply maximum address size for listing
    def __getMachine(self,mach,mslfile,msldft=None):
        mslproc=msldb.MSL(default=msldft)
        mslproc.build(mslfile,fail=True)
        cpux=mslproc.expand(mach)   # Return the expanded version of cpu
        self.addrsize=cpux.addrmax  # Set the maximum address size for CPU
        self.ccw=cpux.ccw           # Set the expected CCW format of the CPU
        self.psw=cpux.psw           # Set the expected PSW format of the CPU
        cache=MSLcache(cpux)        # Create the cache handler
        return cache

    # This method returns an generated instruction as a list of bytes.
    def build(self,stmt,trace=False):
        cls_str="insnbldr.py - %s.build() -" % self.__class__.__name__
        if Builder.type_check:
            if not isinstance(stmt,assembler.Stmt):
                raise ValueError("%s 'stmt' argument requires instance of "
                    "assembler.Stmt: %s" % (cls_str,stmt))
        fmt=stmt.format       # msldb.Format instance
        insn=stmt.insn        # assembler.MSLentry instance
        line=stmt.lineno      # Source object of statement's input location
        if trace:
            insn.dump()       # Dump the MSL DB information

        # Marshall what we need to create the instruction
        i=Instruction(stmt.operands,insn,fmt,line)
        if trace:
            i.dump()
        # NOW!!! build the instruction
        barray=i.generate(self)

        if trace:
            print("%s: " % insn.mnemonic)
            s=""
            for x in barray:
                s="%s %s" % (s,hex(x))
            print("    %s" % s)

        # Update the statenent's binary object
        bin=stmt.content    # Get Binary object from the Stmt
        bin.update(barray,at=0,full=True,finalize=True,trace=trace)

    def getInst(self,inst):
        return self.cache.getInst(inst)

    # Returns the XMODE default settings from the MSL database
    def init_xmode(self):
        d={}
        # Note: the CPU MSL statement ccw parameter is optional.  It could be None.
        # and is none for the 360-20.  It does not use CCW's.
        if self.ccw is not None:        # Coming from the MSL database they should
            d["CCW"]=self.ccw.upper()   # already be upper case, but just in case
        d["PSW"]=self.psw.upper()       # change happens, make sure.
        return d      # Return the default XMODE settings.

    # This method performs a check on the presented value for its fit in a field
    # of a specific size.  The check is sensitive to signed and unsigned data.
    # A ValueError is raised if the check fails.  The caller should except the
    # ValueError and handle it appropriately for the context.
    #
    # Method arguments:
    #    size     The size of the target field in bits
    #    value    The value to be placed in the target field
    #    signed   Specify True for a signed value.  Specify False for an unsigned value.
    #             Defaults to False (unsigned).
    # Exceptions:
    #    ValueError when value is out of range.
    def range_check(self,size,value,signed=False):
        if signed:
            cmin,cmax=self.fld_srange[size]
        else:
            cmin,cmax=self.fld_range[size]
        if value<cmin or value>cmax:
            raise RangeCheckError(cmin,cmax,size,value)

    # Provides conversion of a signed Python integer into an unsigned Python integer.
    # This is necessary for inserting sigend values corretnly into bytes or bytearrays.
    # 
    # Method arguments:
    #   value    The signed value being converted
    #   bits     The field length in bits
    #
    def s2u_int(self,value,bits):
        if bits<2:
            cls_str="insnbldr.py - %s.s2u_int() -" % self.__class__.__name__
            raise ValueError("%s 'bits' argument must be at least 2: %s" \
                % (cls_str,bits))

        # Calculate the number of bytes needed for the conversion process.
        # This is a requirement of the Python int class and the methods used below
        byte_size,excess=divmod(bits+7,8)
        # we ignore the excess

        # Convert the signed integer to an unsigned integer by using bytes as the
        # intermediary.
        bytes=value.to_bytes(byte_size,byteorder="big",signed=True)
        integer=int.from_bytes(bytes,byteorder="big",signed=False)

        # Make sure the returned value is the number of bits provided
        umin,umax=self.fld_range[bits]
        integer &= umax
        return integer

# This class is where the results of the assembler are merged with the MSL database
# format information of a given instruction in preperation for generation of the 
# machine instruction itself.
class AOper(object):
    def __init__(self,operand,soper):
        self.operand=operand        # Assembler.Operand subclass object
        self.soper=soper            # msldb.soper object

    # Returns a list of Field objects with their respecfive values from the assembly
    def fields(self,fmt):
        mach=fmt.mach
        my_fields=[]
        for mfield in self.soper.mfields:
            try:
                mf=mach[mfield]
                # mf is the msldb.mfield object for which the operand provides its value
            except KeyError:
                # WARNING: this should not occur if msldb has done proper validation.
                # Correct the bug in msldb.py if this is raised.
                cls_str="insnbldr.py - %s.fields() -" % self.__class__.__name__
                raise ValueError("%s instruction format %s does not define mach "
                    "field: %s" % (cls_str,fmt.ID,mfield))

            # Get the value provided by the assembler
            mf_typ=mf.typ    # This is the machine field type
            # The Operand object now provides its value for this mfield type
            value=self.operand.field(mf_typ)
            fld=Field(mfield=mf,value=value)
            my_fields.append(fld)

        return my_fields

# This object places bit fields into an instructrion or other structures created
# by assembler directives.
#
# Instance arguments for machine instructios:
#    mfield    MSL database mfield object
#    value     value being inserted into instruction field.
#
# Instance arguments for assembler directives:
#    value     value being inserted into structure field
#    name      name of the field
#    size      size of the field in bits
#    start     starting bit number of field within the structure
#    signed    Specify True if the value is treated as singed, False otherwise.
#              Default is False (unsigned).
class Field(object):
    def __init__(self,mfield=None,value=None,\
                 name=None,size=None,start=None,signed=False):
        self.name=None                   # name of the field
        self.size=None                   # Field size in bits
        self.signed=None                 # Signed field
        self.start=None                  # starting bit position in inst. or structure
        self.mfield=None                 # mfield object if provided

        if mfield is not None:
            self.mfield=mfield
            self.size=mfield.end-mfield.beg+1
            self.start=mfield.beg
            self.signed=mfield.signed
            self.name=mfield.name
        else:
            self.size=size
            self.start=start
            self.signed=signed
            self.name=name

        self.value=value

    def __str__(self):
        s="%s %s size: %s value: %s (%s)" \
           % (self.__class__.__name__,self.name,self.size,self.value,hex(self.value))
        return s

    # This presents the contents of the 
    def dump(self,indent="",string=False):
        s="%s%s" % (indent,self)
        if string:
            return s
        print(s)

    # This method, checks the value for a valid range, positions the field and inserts
    # it into the instruction being built.
    #
    # Method arguments:
    #   length    Instruction length in bytes
    #   inst      The Python integer containing the current instruction content
    #   bldr      The Builder object for access to field ranges.
    def insert(self,length,inst,bldr,line,signed=False):
        value=self.value
        try:
            bldr.range_check(self.size,value,signed=signed)
        except RangeCheckError as re:
            raise assembler.AssemblerError(line=line,\
                msg="%s field %s" \
                    % (self.name,re)) from None

        # Prepare value for insertion into instruction if needed.
        if signed:
            uint=bldr.s2u_int(value,self.size)
        else:
            uint=value 

        # This codes takes the field and
        # positions it for insertion into
        # the instruction being built
        #                                 # |0                         inst_bits|         |
        #  This diagram shows what        # |            |<-field->|            |
        #  this code is doing to          # <----------instruction-------------->
        #  accomplish this.               #              ^         ^  |   uint  |
        inst_bits=length*8                #              |         |  |         |
        unshifted=inst_bits-self.size     #              |         |  +<--unshifted
                                          #              |    left |  |
        left_shift=unshifted-self.start   # field start->+<---shift---+
        to_insert=uint<<left_shift        #              |  field  |
                                          #              | in pos. |

        # This adds the field to the instruction
        inst |= to_insert
        return inst  # This is the instruction with the new field added to it

# This class merges the high-level information related to building an instruction:
# the results of the assembling all of the source operands, the instruction definition
# within the MSL database and the instruction format definition also from the MSL
# database.
class Instruction(object):
    def __init__(self,operands,inst,fmt,line):
        self.operands=operands        # list of assembler.Operand instances
        self.inst=inst                # MSLentry instance
        self.mnemonic=inst.mnemonic   # Instruction mnemonic
        self.fmt=fmt                  # msldb.Format instance
        self.length=fmt.length        # Instruction length
        self.line=line                # Stmt Line number

        # These attributes contain
        self.aops=[]            # From Step 1 - List of AOper objects
        self.fields=[]          # From Step 2 - List of Field objects
        self.laddr=[]           # 

        # Step 1 - build the AOper list (one per assembler statement operand)
        soper_seq=fmt.soper_seq
        if len(operands)!=len(soper_seq):
            cls_str="insnbldr.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s number of operands from assembler.Stmt object "
                "for line %s does not match source operands in msldb.Format object for "
                "mnemonic %s: %s != %s" \
                % (cls_str,line,self.mnemonic,len(operands),len(soper_seq)))
        for n in range(len(operands)):
            name=soper_seq[n]        # A source parameter type/id attribute
            soper=fmt.soper[name]    # The msldb.soper object it defines
            operand=operands[n]      # The assembler.Operand object for the soper object
            aop=AOper(operand,soper) # Link the assembly results with the format
            self.aops.append(aop)    # Add to the list.
        # The aops list is an intermediate step in figuring out how to build the 
        # instruction.

        # Step 2 - build the list of Field objects (one per machine field)

        #   Step 2a - add the opcode machine fields to the list from msldb.Format and 
        #             msldb.Inst objects.
        opc_fields=fmt.opcode
        opcode=Field(mfield=opc_fields["OP"],value=inst.opcode[0])
        self.fields.append(opcode)
        try:
            opx=opc_fields["OPX"]
            opxf=Field(mfield=opx,value=inst.opcode[1])
            self.fields.append(opxf)
        except KeyError:  # Instruction does not have an extended opcode field
            pass

        #   Step 2b - add the other fields to the list from the assembler output and
        #             msldb.Format object.
        for aop in self.aops:
            flds=aop.fields(self.fmt)
            # Add the operand's fields it is sourcing to the list.
            self.fields.extend(flds)
        # The final fields list now has everything needed to build the instruction.

    # Display the final list of fields to be put into the instruction.
    def dump(self,indent="",string=False):
        s="%s%s Format: %s" % (indent,self.mnemonic,self.fmt.ID)
        lcl="%s    " % indent
        for fld in self.fields:
            s="%s\n%s%s" % (s,lcl,fld)
        if string:
            return s
        print(s)

    # Generate this instruction as a list of bytes.
    def generate(self,bldr):
        inst=0
        for fld in self.fields:
            # Insert each field individually into the instruction.
            inst=fld.insert(self.length,inst,bldr,self.line,signed=fld.signed)
        # Return the instruction as bytes list.
        return inst.to_bytes(self.length,byteorder="big",signed=False)

# Information from the MSL directory is not readily usable by the assembler.
# This class performs the necessary actions to make the information more readily
# usable.  The MSL cache is built lazily.  As instructions are encountered that
# are not in the cache they will be added.  MSLentry objects are built as needed.
# The instruction mnemonic is the key to the cache.
class MSLcache(object):
    def __init__(self,cpux):
        if not isinstance(cpux,msldb.CPUX):
            cls_str="assembler.py - %s.__init__() -" % self.__class__.__name__
            raise ValueError("%s 'cpux' argement must be an instance of "
                "msldb.CPUX: %s" % (cls_str,cpux))
        self.cpux=cpux
        self.cache={}

    def __getitem__(self,item):
        try:
            # Try to get the instrution cached entry
            return self.cache[item]
        except KeyError:
            pass  # Try to create a cache entry for the future

        # Try again against the MSL information.  A KeyError here is for real
        inst=self.cpux.inst[item]
        # Let the KeyError this time reflect this is an undefined instruction
        fmt=self.cpux.formats[inst.format]   
        entry=MSLentry(inst,fmt)
        # Put the instruction into the cache
        self.cache[item]=entry
        # Return it as it it had been there all along.
        return entry

    def getInst(self,item):
        return self[item.upper()]

    def getFormat(self,item):
        return self.cpux.formats[item]

class MSLentry(object):
    def __init__(self,mslinst,mslformat):
        self.mslinst=mslinst           # The original inst statement from the MSL DB
        self.mslformat=mslformat       # The original format statement from the MSL DB

        # Data from the MSL Inst object
        self.mnemonic=mslinst.mnemonic # The instruction mnemonic
        self.opcode=mslinst.opcode     # The opcode field value(s) [for OP, for OPX]

        # Data from the MSL Format object
        self.format=mslformat.ID       # The format ID
        self.length=mslformat.length   # length of instruction in bytes

    def dump(self):
        self.mslinst.dump()
        self.mslformat.dump()

    def num_oprs(self):
        return len(self.mslformat.soper_seq)   # Return the number of source operands

    def src_oprs(self,debug=False):
        return self.mslformat.stype_seq  # Return the source operands types in sequence

if __name__ == "__main__":
    raise NotImplementedError("insnbldr.py - intended for import use only")
