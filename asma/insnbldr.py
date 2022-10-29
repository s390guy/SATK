#!/usr/bin/python3
# Copyright (C) 2014-2022 Harold Grovesteen
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

this_module="insnbldr.py"

# Python imports: None
# SATK imports: None

# ASMA imports:
import assembler
import asmstmts


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
# of assembler.Stmt presented to the build engine.  The Stmt instance is updated with
# the constructed instruction.
class Builder(object):
    def __init__(self,trace=False):
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

    # This method returns a generated instruction as a list of bytes.
    def build(self,stmt,trace=False):
        assert isinstance(stmt,asmstmts.MachineStmt),\
            "%s 'stmt' argument requires instance of assembler.Stmt: %s" \
                % (assembler.eloc(self,"build",module=this_module),stmt)

        fmt=stmt.format       # msldb.Format instance
        insn=stmt.insn        # assembler.MSLentry instance
        line=stmt.lineno      # Source object of statement's input location
        if trace:
            insn.dump()       # Dump the MSL DB information

        # Marshall what we need to create the instruction
        i=Instruction(stmt.bin_oprs,insn,fmt,line)
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

    # This method performs a check on the presented value for its fit in a field
    # of a specific size.  The check is sensitive to signed and unsigned data.
    # A RangeCheckError is raised if the check fails.  The caller should except the
    # RangeCheckError and handle it appropriately for the context.
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
    def s2u_int(self,value,bits):
        if bits<2:
            raise ValueError("%s 'bits' argument must be at least 2: %s" \
                % (assembler.eloc(self,"s2u_int",module=this_module),bits))

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


# This class supports use of field filters in MSL 'inst' statement 'fixed'
# parameters.  The class applies the filter and returns the filtered field's
# value.
#
# New filters are added to this class as a method.
class FieldFilters:
    def __init__(self):
        # This is a dictionary of filter methods supported by MSL inst fixed
        # parameter.  It maps the filter name (used in MSL) to a method in
        # this instance.
        self.fms={"MINUS":   self._minus,
                  "MINUST":  self._minust,
                  "NOP":     self._nop,
                  "OR_01":   self._or_01,
                  "OR_02":   self._or_02,
                  "OR_03":   self._or_03,
                  "OR_08":   self._or_08,
                  "TAONE":   self._taone,
                  "TAZERO":  self._tazero,
                  "31MINUSZ":self._31minusz,
                  "32MINUS": self._32minus,
                  "32PLUS":  self._32plus}

  #
  # MSL Filter Methods
  #

    # This method calculates the value -X for certain ROTATE instructions
    # without setting or unsetting T or Z bits
    # Instance Argument:
    #   value   The assembler operand value
    def _minus(self,value):
        return ( 64 - value )


    # This method calculates the value -X for certain ROTATE instructions
    # Instance Argument:
    #   value   The assembler operand value
    def _minust(self,value):
        return ( 64 - value ) & 0x3F 

    # This method performs no actual alteration of the value but is useful
    # for debugging.
    # Instance Argument:
    #   value   The assembler operand value
    def _nop(self,value):
        return value

    # Binary OR of the value with 0x01, forcing bit 7 to a 1.
    # Instance Argument:
    #   value   The assembler operand value
    def _or_01(self,value):
        return value | 0x01
        
    # Binary OR of the value with 0x02, forcing bit 6 to a 1.
    # for debugging.
    # Instance Argument:
    #   value   The assembler operand value
    def _or_02(self,value):
        return value | 0x02
        
    # Binary OR of the value with 0x02, forcing bits 6 and 7 to a 1.
    # for debugging.
    # Instance Argument:
    #   value   The assembler operand value
    def _or_03(self,value):
        return value | 0x03
        
    # Binary OR of the value with 0x08, forcing bit 4 to a 1.
    # for debugging.
    # Instance Argument:
    #   value   The assembler operand value
    def _or_08(self,value):
        return value | 0x08

    # This method treats in ROTATE instructions as 1 the T-bit
    # Instance Argument:
    #   value   The assembler operand value
    def _taone(self,value):
        return value | 0x80

    # This method treats in ROTATE instructions as 0 the T-bit
    # Instance Argument:
    #   value   The assembler operand value
    def _tazero(self,value):
        return value & 0x7F
        
    # This method calculates the instruction field value by subtracting it
    # from 31 AND setting the Z bit to one
    # Instance Argument:
    #   value   The assembler operand value
    def _31minusz(self,value):
        return ( 31 - value ) | 0x80
        
    # This method calculates the instruction field value by adding to it 32
    # Instance Argument:
    #   value   The assembler operand value
    def _32minus(self,value):
        return  32 - value 
        
    # This method calculates the instruction field value by adding to it 32
    # Instance Argument:
    #   value   The assembler operand value
    def _32plus(self,value):
        return  32 + value 

  #
  # Externally callable method
  #

    # This is the only method supported for external calls by the FieldFilter
    # object.
    def apply_filter(self,name,field_value):
        try:
            filter_method=self.fms[name]
        except KeyError:
            # If this KeyError occurs, either correct msldb.py or add the
            # filter name to this module
            raise ValueError("%s filter name not defined by insnbldr: %s" % \
                (assembler.eloc(self,"apply_filter",module=this_module),name))

        return filter_method(field_value)


# This class is where the results of the assembler are merged with the MSL database
# format information of a given instruction in preperation for generation of the
# machine instruction itself.
class AOper(object):

    filters=FieldFilters()  # Process instruction field filters

    def __init__(self,operand,soper,fixed,filtered):
        self.operand=operand        # asmbase.Operand subclass object
        self.soper=soper            # msldb.soper object

        # Dictionary of fixed content for this field from inst statement
        # fixed paramater field (hex value)
        self.fixed=fixed

        # Dictionary of field filter applied to this field from inst statement
        # fixed parameter (string)
        self.filtered=filtered

    # Returns a list of Field objects with their respective values from the assembly
    def fields(self,fmt):
        mach=fmt.mach  # Dictionary of machine field definitions
        my_fields=[]
        # Determine values for all fixed content fields
        vector=False
        filter_name=None
        for mfield,mf in mach.items():
            vector = vector or mf.typ=="V"  # Detect vector registers
            if mf.fixed:
                try:
                    fixed_value=self.fixed[mfield]
                except KeyError:
                    # WARNING: this should not occur if msldb has done a
                    # proper validation. Correct the bug in msldb.py if this
                    # is raised.
                    raise ValueError("%s instruction definition does not define "
                        "fixed value for field: %s" \
                            % (assembler.eloc(self,"fields",module=this_module)\
                                ,mfield))
                fld=Field(mfield=mf,value=fixed_value)
                my_fields.append(fld)

        # Process values from statement operands
        rxb=0
        for mfield in self.soper.mfields:
            try:
                mf=mach[mfield]
                # mf is the msldb.mfield object for which the operand provides its value
            except KeyError:
                # WARNING: this should not occur if msldb has done proper validation.
                # Correct the bug in msldb.py if this is raised.
                raise ValueError("%s instruction format %s does not define mach "
                    "field: %s" % (assembler.eloc(self,"fields",\
                        module=this_module),fmt.ID,mfield))

            mf_typ=mf.typ    # This is the machine field type

            # The Operand object now provides its value for this mfield type
            value=self.operand.field(mf_typ)

            if len(self.filtered) > 0:
                try:
                    filter_name=self.filtered[mfield]
                except KeyError:
                    filter_name=None

                if filter_name:
                    # This tests if a filter name applies

                    value=AOper.filters.apply_filter(filter_name,value)

            if mf_typ=="V":
                if value<0 or value>31:
                    raise assembler.AssemblerError(line=line,\
                        msg="%s field outside of valid vector register range: %s" \
                            % (mf.name,value))
                vreg=value & 0xF
                if value>15:
                    rxb |= mf.rxb
                fld=Field(mfield=mf,value=vreg)
            else:
                fld=Field(mfield=mf,value=value)
            my_fields.append(fld)

        # Generate RXB field if required
        if rxb:
            try:
                mf_rxb=mach["RXB"]
            except KeyError:
                # WARNING: this should not occur if msldb has done a proper validation.
                # Correct the bug in msldb.py if this is raised.
                raise ValueError(\
                    "%s instruction definition does not define field RXB" \
                        % assembler.eloc(self,"fields",module=this_module))
            fld=Field(mfield=mf_rxb,value=rxb)
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
#    filter_name  String name of filter being applied to this field
class Field(object):

    filters=FieldFilters()  # Process instruction field filters

    def __init__(self,mfield=None,value=None,\
                 name=None,size=None,start=None,signed=False,filter_name=None):
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
        if self.value is None:
            v="None"
        else:
            v=hex(self.value)
        s="%s %s size: %s value: %s (%s) signed: %s" \
           % (self.__class__.__name__,self.name,self.size,self.value,v,\
               self.signed)
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
        self.aops=[]            # From Step 1a - List of AOper objects
        self.fixed={}           # From Step 1b -
        self.fields=[]          # From Step 2  - List of Field objects
        self.laddr=[]           #

        # Step 1a - build the AOper list (one per assembler statement operand)
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

            # Link the assembly results with the format, instruction fixed content
            aop=AOper(operand,soper,self.inst.fixed,self.inst.filters)
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


if __name__ == "__main__":
    raise NotImplementedError("insnbldr.py - intended for import use only")
