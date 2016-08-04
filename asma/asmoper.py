#!/usr/bin/python3.3
# Copyright (C) 2015, 2016 Harold Grovesteen
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

# This module manages all assembler operation field recognition.  It defines
# all assembler and macro directives and interfaces with the MSL database for
# instruction definition.  Definitions reside here.

this_module="%s.py" % __name__

# Python imports: None
# SATK imports: None
# ASMA imports:
import assembler    # Access the assembler for error reporting
import asmbase      # Access the base operation management classes
import asmstmts     # Access the statement classes
import asmline      # Addess a LineError exception
import msldb        # Access the Machine Specification Language Processor


# Information from the MSL directory is not readily usable by the assembler.
# This class performs the necessary actions to make the information more readily
# usable.  The MSL cache is built lazily.  As instructions are encountered that
# are not in the cache they will be added.  MSLentry objects are built as needed.
# The instruction mnemonic is the key to the cache.
class MSLcache(object):
    def __init__(self,cpux):
        assert isinstance(cpux,msldb.CPUX),\
            "%s 'cpux' argument must be an instance of msldb.CPUX: %s" \
                % (eloc(self,"__init__",module=this_module),cpux)

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

    # Return an MSLEntry object based upon the instruction mnemonic
    def getInst(self,item):
        return self[item.upper()]

    # Return the msldb.Format object based upon the format identification
    # Currently this method is not used
    def getFormat(self,item):
        return self.cpux.formats[item]


class MSLentry(object):
    def __init__(self,mslinst,mslformat):
        self.mslinst=mslinst           # The original inst statement from the MSL DB
        self.mslformat=mslformat       # The original format statement from the MSL DB

        # Data from the MSL Inst object
        self.mnemonic=mslinst.mnemonic  # The instruction mnemonic
        self.opcode=mslinst.opcode      # The opcode field value(s) [for OP, for OPX]
        self.fixed=mslinst.fixed_value  # Fixed instruction content field:value dict.
        self.extended=mslinst.extended  # Whether this is an extended mnemonic

        # Data from the MSL Format object
        self.format=mslformat.ID        # The format ID
        self.length=mslformat.length    # length of instruction in bytes

    def dump(self):
        self.mslinst.dump()
        self.mslformat.dump()

    # Return the number of source operands
    def num_oprs(self):
        return len(self.mslformat.soper_seq)

    # Return the source operands types in sequence
    def src_oprs(self,debug=False):
        return self.mslformat.stype_seq


# The OperMgr class manages specifications for all assembler and macro directives
# machine instructions and, because it influences asmstmts statement class selection
# macro definition state.
#
# Instance Arguments
#   asm     The Assembler object
#   machine The MSL cpu definition being requested from the MSL file
#   msl     The MSL filename requested
#   mslpath PathMgr object of the MSL database
#   debug   Specify True to enable debugging of the file access operations
class OperMgr(asmbase.ASMOperTable):
    # XMODE values accepted
    ccw_xmode={"0":"CCW0",0:"CCW0","1":"CCW1",1:"CCW1","none":None,"NONE":None}
    psw_xmode={"S":"PSWS","PSWS":"PSWS",
               "360":"PSW360","PSW360":"PSW360",360:"PSW360",
               "67":"PSW67","PSW67":"PSW67",67:"PSW67",
               "BC":"PSWBC","PSWBC":"PSWBC",
               "EC":"PSWEC","PSWEC":"PSWEC",
               "380":"PSW380","PSW380":"PSW380",380:"PSW380",
               "XA":"PSWXA","PSWXA":"PSWXA",
               "E370":"PSWE370","PSWE370":"PSWE370",
               "E390":"PSWE390","PSWE390":"PSWE390",
               "Z":"PSWZ","PSWZ":"PSWZ",
               "none":None,"NONE":None}

    def __init__(self,asm,machine,msl,mslpath,debug=False):
        super().__init__()
        self.asm=asm         # The Assembler object
        # Legacy AsmPasses objects for assembler directives
        self.asmpasses={}

        # Build the MSL cache and other assembler parameters from the MSL database.
        self.addrsize=None   # Maximum address size supported by the CPU
        self.ccw=None        # Expected CCw format used by the CPU
        self.psw=None        # Expected PSW format used by the CP
        self.cache=self.__getMachine(machine,msl,mslpath=mslpath,debug=debug)

        # Manage Directive Statements
        self.def_adirs()     # Define Assembler directives
        self.def_mdirs()     # Define Macro directives

        # Defined macros
        self.macros=MacroTable()  # Manages definition/redefinition and X-ref

        # Create the operator synonym translation dictionary
        self.opsyn={}

        # XMODE settings
        self.xmode=None      # Initialized by init_xmode() method
        # Modes and settings used by XMODE directive.
        self.xmode_dir={"PSW":OperMgr.psw_xmode,
                        "CCW":OperMgr.ccw_xmode}

    # Create the MSL cache and supplies maximum address size for listing
    # Method arguments are passed from the instance arguments.
    def __getMachine(self,machine,mslfile,mslpath,debug=False):
        mslproc=msldb.MSL(default=None,pathmgr=mslpath,debug=debug)
        mslproc.build(mslfile,fail=True)
        cpux=mslproc.expand(machine)  # Return the expanded version of cpu
        self.addrsize=cpux.addrmax    # Set the maximum address size for CPU
        self.ccw=cpux.ccw             # Set the expected CCW format of the CPU
        self.psw=cpux.psw             # Set the expected PSW format of the CPU
        cache=MSLcache(cpux)          # Create the cache handler
        return cache

    # Set XMODE.  Setting is validated against the above class attributes as supplied
    # by the caller.
    def __xmode_setting(self,mode,setting,sdict):
        v=sdict[setting]    # This may raise a KeyError
        if v is None:
            try:
                del self.xmode[mode]  # If none, remove the XMODE setting entirely 
            except KeyError:
                pass                  # Alredy gone, that is OK, that's what we wanted 
        else:
            self.xmode[mode]=v

    # Define an individual directive
    def def_dir(self,oper,stmtcls,O="U",info=None):
        d=asmbase.ASMOper(oper,stmtcls,info=info)
        self[d.oper]=d

    # Define the assembler directives
    def def_adirs(self):
        self.def_dir("AMODE",    asmstmts.AMODE,    O="A")
        self.def_dir("ATRACEOFF",asmstmts.ATRACEOFF,O="A")
        self.def_dir("ATRACEON", asmstmts.ATRACEON, O="A")
        self.def_dir("CCW",      asmstmts.CCW0,     O="A")
        self.def_dir("CCW0",     asmstmts.CCW0,     O="A")
        self.def_dir("CCW1",     asmstmts.CCW1,     O="A")
        self.def_dir("CNOP",     asmstmts.CNOP,     O="A")
        self.def_dir("COPY",     asmstmts.COPY,     O="A")
        self.def_dir("CSECT",    asmstmts.CSECT,    O="A")
        self.def_dir("DC",       asmstmts.DC,       O="A")
        self.def_dir("DROP",     asmstmts.DROP,     O="A")
        self.def_dir("DS",       asmstmts.DS,       O="A")
        self.def_dir("DSECT",    asmstmts.DSECT,    O="A")
        self.def_dir("EJECT",    asmstmts.EJECT,    O="A")
        self.def_dir("END",      asmstmts.END,      O="A")
        self.def_dir("ENTRY",    asmstmts.ENTRY,    O="A")
        self.def_dir("EQU",      asmstmts.EQU,      O="A")
        self.def_dir("MACRO",    asmstmts.MACRO,    O="A")
        self.def_dir("MHELP",    asmstmts.MHELP,    O="A")
        self.def_dir("MNOTE",    asmstmts.MNOTE,    O="A")
        self.def_dir("OPSYN",    asmstmts.OPSYN,    O="A")
        self.def_dir("ORG",      asmstmts.ORG,      O="A")
        self.def_dir("POP",      asmstmts.POP,      O="A")
        self.def_dir("PRINT",    asmstmts.PRINT,    O="A")
        self.def_dir("PSWS",     asmstmts.PSWS,     O="A")
        self.def_dir("PSW360",   asmstmts.PSW360,   O="A")
        self.def_dir("PSW67",    asmstmts.PSW67,    O="A")
        self.def_dir("PSWBC",    asmstmts.PSWBC,    O="A")
        self.def_dir("PSWEC",    asmstmts.PSWEC,    O="A")
        self.def_dir("PSW380",   asmstmts.PSWBi,    O="A")
        self.def_dir("PSWXA",    asmstmts.PSWBi,    O="A")
        self.def_dir("PSWE370",  asmstmts.PSWBi,    O="A")
        self.def_dir("PSWE390",  asmstmts.PSWBi,    O="A")
        self.def_dir("PSWZ",     asmstmts.PSWZ,     O="A")
        self.def_dir("PUSH",     asmstmts.PUSH,     O="A")
        self.def_dir("REGION",   asmstmts.REGION,   O="A")
        self.def_dir("RMODE",    asmstmts.RMODE,    O="A")
        self.def_dir("SPACE",    asmstmts.SPACE,    O="A")
        self.def_dir("START",    asmstmts.START,    O="A")
        self.def_dir("TITLE",    asmstmts.TITLE,    O="A")
        self.def_dir("USING",    asmstmts.USING,    O="A")
        self.def_dir("XMODE",    asmstmts.XMODE,    O="A")
        self.def_dir("?",        asmstmts.StmtError)    # Logical line error

    # Defines a new macro
    # Method Arguments:
    #   macro   The asmmacs.Macro object of the macro definition
    #   O       The O' attribute to be assigned to the macro
    #              M - is a macro definition from within the assembly
    #              S - is a macro definition from a macro library
    def def_macro(self,macro):
        oper=asmbase.ASMOper(macro.name,asmstmts.MacroStmt,O="M",info=macro)
        self.macros.define(oper)
        #self.macros[macro.name]=oper

    # Define the macro directives and other miscelaneous statement types
    def def_mdirs(self):
        self.def_dir("ACTR", asmstmts.ACTR, O="A")
        self.def_dir("AGO",  asmstmts.AGO,  O="A")
        self.def_dir("AIF",  asmstmts.AIF,  O="A")
        self.def_dir("ANOP", asmstmts.ANOP, O="A")
        self.def_dir("GBLA", asmstmts.GBLA, O="A")
        self.def_dir("GBLB", asmstmts.GBLB, O="A")
        self.def_dir("GBLC", asmstmts.GBLC, O="A")
        self.def_dir("LCLA", asmstmts.LCLA, O="A")
        self.def_dir("LCLB", asmstmts.LCLB, O="A")
        self.def_dir("LCLC", asmstmts.LCLC, O="A")
        self.def_dir("MEND", asmstmts.MEND, O="A")
        self.def_dir("SETA", asmstmts.SETA, O="A")
        self.def_dir("SETB", asmstmts.SETB, O="A")
        self.def_dir("SETC", asmstmts.SETC, O="A")
        self.def_dir("MEXIT",asmstmts.MEXIT,O="A")

    # Returns the ASMOper objectobject of the directive.  No exception raised
    # Returns:
    #   The ASMOper object of the directive, if found
    #   None, if directive not found
    # Exception:
    #   KeyError if the directive is not defined
    def getDir(self,directive):
        #return self[directive]
        return self.get(directive)

    # Return operation a type for ignored logical lines
    def getComment(self,quiet=False):
        if self.asm.MM.state==2 and not quiet:
            # If this is a loud comment wihin a macro body, treat it as a model stmt.
            return asmbase.ASMOper("*",asmstmts.ModelStmt)
        return asmbase.ASMOper("*",asmstmts.StmtComment)
        #return self["*"]

    # Return operation for a logical line error
    def getError(self):
        return self["?"]

    # Returns an ASMOper object for an instruction statement's operation field or
    # None if not found.  No exception raised
    # Method Argument:
    #   opname   The operation identified in the statement's operation field
    def getInsn(self,opname):
        try:
            insn=self.getMSL(opname)
            # insn is an instance of MSLentry
            # Note, this needs to stay here as it controls Insn selection from the
            # machine definition or the assembler pseudo instruction definition.
        except KeyError:
            return None

        # Instruction found, so build an ASMOper object for it, and return it
        if insn.extended:
            O_attr="E"
        else:
            O_attr="O"
        return asmbase.ASMOper(opname,asmstmts.MachineStmt,O=O_attr,info=insn)

    # Returns the MSLEntry object retrieved from the MSL database cache
    # Excpetion:
    #   KeyError  if the instruction is not defined in the MSL database
    def getMSL(self,inst):
        return self.cache.getInst(inst)

    # Accesses and optionally defines a macro (or macros if more than one) in a 
    # MACLIB file.  Returns the associated ASMOper object of the defined macro.
    # Method Arguments:
    #   macname  MACLIB macro file being sought from the search path.
    #   macread  Specify False to simply search for the file in the search path.
    #            Specify True to define the macro(s) contained in the file.  Defaults
    #            to False.
    # Returns:
    #   - ASMOper object of newly defined macro or an ASMOper object representing the
    #     macro definition file found in the file; or
    #   - None if the the maclib file was not found or the macro definition failed.
    # Exception:
    #   LineError if the library macro definition fails.
    def getMacLib(self,macname,macread=False):
        asm=self.asm
        if not macread:
            # Not reading the file so just looking for it (O' attribute operation)
            # in the MACLIB directories.  Use the MacroProcessor to do this.
            return asm.MP.getAttr_O(macname)

        # Actually reading the file so macros will be defined
        # An asmline.LineError is raised if this fails.  asmline.LineMgr.categorize()
        # method does the actual trapping of the error.
        try:
            asm.MP.run(asm,macname)  # Run the MACROProcessor to define the macro
        except assembler.AssemblerError as ae:
            # Fetching of the macro from the macro library failed for some reason
            # We need to treat this as a LineError of the physical line

            #oper=self.getError()
            #oper.info=ae
            #return oper
            raise asmline.LineError(msg=ae.msg) from None
            
            
        # This time the macro should be defined.
        mte=self.macros.get(macname)
        if mte:
            return mte.oper
        return None

    # Returns an ASMOper object (see def_macro() method) or None if not defined
    def getMacro(self,macname,macread=False,debug=False):
        try:
            mte=self.macros[macname]
            oper=mte.oper   # Retrieve the ASMOper object from the macro table entry
        except KeyError:
            # Not found - need to try macro libarary paths
            oper=self.getMacLib(macname,macread=macread)

        if oper is not None:
            assert isinstance(oper,asmbase.ASMOper),\
                "%s mte not an asmbase.ASMOper object: %s" \
                    % (assembler.eloc(self,"getMacro",module=this_module),oper)
            return oper
        return None

    # Returns the operation attribute, O', of a name
    # Uses the same search as normal operation recognition.
    def get_O_attr(self,name):
        try:
            oper=self.getOper(name,macread=False)
            assert isinstance(oper,asmbase.ASMOper),\
                "%s getOper did not return an asmbase.ASMOper instance: %s" \
                    % (assembler.eloc(self,"oper",module=this_module),oper)
        except KeyError:
            return "U"
        return oper.O

    # Returns operation specification information based upon the operation name.
    # Identification of the statement operation is performed in the following
    # sequence:
    #  1. OPSYN conversion
    #  2. Macro name
    #  3. Machine instruction operation mnemonic
    #  4. XMODE directive setting
    #  5. Assembler directive
    # During macro definition the sequence is different:
    #  1. Recognize a macro statement
    #  2. Assume a model statement otherwise.
    # Method Arguements
    #   opname  operation name (in upper case) being retrieved
    #   mbstate The state of the current MacroBuilder object
    #   macread Specify True to read a definition from the MACLIB path.  Specify
    #           False to only open (for search purposes) the MACLIB file.  Defaults
    #           to False.
    #   lineno  The location of the line.  For logical lines this is its source
    #   debug   Specify True to enable various process messages
    # Returns:
    #   ASMOper object of the operation
    # Exception:
    #   KeyError  if the operation is unrecognized
    def getOper(self,opname,mbstate=0,macread=False,lineno=None,debug=False):
        # Locate the instruction or statement data
        opcode=None     # The effective opcode after OPSYN translation

        if __debug__:
            if debug:
                print("%s opname:%s mbstate:%s macread:%s lineno:%s debug:%s" \
                    % (assembler.eloc(self,"getOper",module=this_module),\
                        opname,mbstate,macread,lineno,debug))

    # Handle operation identification during macro definition

        if mbstate!=0:
            if mbstate==1:
                # Prototype statement
                return asmbase.ASMOper(opname,asmstmts.MacroProto,info=None)

            elif mbstate==2:
                # Body statements
                try:
                    # Only recognize macro directives here
                    oper=self[opname]
                    if oper.stmtcls.typ not in ["MD","MO","ML","MS"]:
                        raise KeyError
                    return oper
                except KeyError:
                    # All other statements are model statements
                    return asmbase.ASMOper(opname,asmstmts.ModelStmt)

            elif mbstate==3:
                # Found end of bad macro
                if opname=="MEND":
                    return self[opname]
                # Suppressing statement in bad macro. Treat as a comment
                return self.getComment()
            else:
                raise ValueError("%s unexpected MacroBuilder state: %s" \
                    % (assembler.eloc(self,"getOper",module=this_module),mbstate))

     # Operation recoginition outside of macro definitions

        # Perform OPSYN replacement.  A deleted operation may be restored by another
        # OPSYN directive that defines the operation to its original value.
        if __debug__:
            cls_str=assembler.eloc(self,"getOper",module=this_module)
            if debug:
                print("%s DEBUG OPSYN Table:\n%s" % (cls_str,self.opsyn))

        # Translate an operation synonym to its underlying definition or use
        # the name unaltered.
        opcode=self.getOPSYN(opname)
        if __debug__:
            if debug:
                if opcode!=opname:
                    print("%s DEBUG OPSYN redefined operation from %s to: %s" \
                         % (cls_str,opname,opcode))
                else:
                    print("%s DEBUG OPSYN using original operation: %s" \
                         % (cls_str,opcode))

        # Try to locate the operation synonym
        if opcode is None:
            # Operation deleted by OPSYN directive.  Could still be a macro, though
            if __debug__:
                if debug:
                    print("%s DEBUG operation deleted: %s" \
                        % (cls_str,opname))
            pass
        else:
            # Operation exists.  Try to identify the machine instruction
            oper=self.getInsn(opcode)
            if oper is not None:
                if __debug__:
                    if debug:
                        print("%s DEBUG found instruction: %s" \
                            % (cls_str,oper.info.mnemonic))
                return oper
            else:
                # Instruction mnemonic not found, try to find assmebler directive:
                # first by locating an XMODE setting, then by finding the actual
                # directive.
                # Note: XMODE settings translate a generic directive into a specific
                # machine sensitive one.
                operation=self.getXMODE(opcode)
                if __debug__:
                    if debug:
                        print("%s DEBUG XMODE %s returned: %s" \
                            % (cls_str,opcode,operation))

                # Now get the directive
                oper=self.getDir(operation)
                if oper is not None:
                    if __debug__:
                        if debug:
                            print("%s DEBUG found directive: %s" % (cls_str,operation))
                    return oper
                else:
                    if __debug__:
                        if debug:
                            print("%s DEBUG directive not found: %s" \
                                % (cls_str,operation))
        
        # Try to locate the macro definition
        if __debug__:
            if debug:
                print("%s DEBUG looking for macro: %s" % (cls_str,opcode))
        oper=self.getMacro(opcode,macread=macread)
        if __debug__:
            if debug:
                print("%s DEBUG looking for macro returned: %s" % (cls_str,oper))
        # Note: if macread is True, and the macro is not defined, the getMacro method
        # will attempt to access the macro libary path to find the macro definition.
        # If found the MACLIBProcessor will be run to define the macro.  The
        # ASMOper object of the newly defined macro is returned, as if it was already
        # defined.
        if oper is not None:
            if __debug__:
                if debug:
                    print("%s DEBUG found macro: %s" % (cls_str,opcode))
            assert isinstance(oper,asmbase.ASMOper),\
                "%s getMacro did not return an asmbase.ASMOper instance: %s" \
                    % (assembler.eloc(self,"getOper",module=this_module),oper)
            return oper

        if oper is None:
            if __debug__:
                if debug:
                    print("%s DEBUG macro not found: %s" % (cls_str,operation))
            raise KeyError()

        raise ValueError("%s operation search algorithm failed to either return "\
            "the ASMOper object or result is None: %s" \
                % (assembler.eloc(self,"getOper",module=this_module),oper))

    # Return the underlying operation name for an operator synonym
    # Returns:
    #   the underlying operation name, if defined
    #   None, if the operation was deleted
    #   the unchanged synonym, if a synonym is not defined.  No exception is raised
    def getOPSYN(self,syn):
        return self.opsyn.get(syn,syn)

    # Returns the current XMODE setting.  No exceptions raised
    # Returns:
    #   The XMODE setting, if defined or or the orignal name
    #   The original name, if not defined or the XMODE was disabled 
    def getXMODE(self,xmode):
        #return self.xmode[xmode]
        setting=self.xmode.get(xmode,xmode)
        if setting is None:
            return xmode
        return setting

    # Initialize the XMODE settings.  The ccw and psw method arguments are from the 
    # command line argparse values.
    # The values are initialized from the MSL database.  The externally supplied 
    # arguments override the MSL database.
    #
    # If the arguments are supplied via the asma.py command line interface, invalid 
    # arguments will not be accepted.
    #
    # If the arguments are supplied by an external user of the Assembler class as
    # an embedded assembler, the values could be invalid.  The checks here are for
    # that case.
    #
    # Method Arguments:
    #   ccw   Command-line xmode ccw setting or None if absent
    #   psw   Command-line XMODE PSW setting or None if absent
    def init_xmode(self,ccw,psw):
        d={}
        # Note: the CPU MSL statement ccw parameter is optional.  It could be None.
        # and is none for the 360-20.  It does not use CCW's.
        if self.ccw is not None:        # Coming from the MSL database they should
            d["CCW"]=self.ccw.upper()   # already be upper case, but just in case
        d["PSW"]=self.psw.upper()       # change happens, make sure.

        self.xmode=d         # Initially establish MSL database defaults 

        # Use command-line options to override MSL database defaults if provided.
        if ccw is not None:  # External override provided
            try:
                self.__xmode_setting("CCW",ccw,Assembler.ccw_xmode)
            except KeyError:
                raise ValueError("%s 'ccw' xmode argument invalid: %s" \
                    % (eloc(self,"init_xmode"),ccw)) from None

        if psw is not None:  # External override provided
            try:
                self.__xmode_setting("PSW",psw,Assembler.psw_xmode)
            except KeyError:
                raise ValueError("%s 'psw' xmode argument invalid: %s" \
                    % (eloc(self,"init_xmode"),psw)) from None

    # Print the OPSYN table.  Used by OPSYN directive
    def opsyn_print(self,stmt):
        # Do the OPSYN table dump to sysout because no label was supplied
        print("[%s] OPSYN Table:" % stmt.lineno)
        for op in sorted(self.opsyn.keys()):
            val=self.opsyn[op]
            if val is None:
                val="deleted"
            print("    %s: %s" % (op,val))

    # Assing an operator synonym.  Assigning None 'deletes' the synonym
    def opsyn_setting(self,syn,oper):
        self.opsyn[syn]=oper

    # Assign an XMODE from the assembler directive
    def xmode_setting(self,stmt,mode,setting):
        try:
            mdict=self.xmode_dir[mode]
        except KeyError:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="XMODE mode not recognized: %s" % mode) from None
        try:
            self.__xmode_setting(mode,setting,mdict)
        except KeyError:
            raise assembler.AssemblerError(line=stmt.lineno,\
                msg="XMODE %s setting invalid: %s" % (mode,setting)) from None


# Macro Definition Table
class MacroTable(object):
    def __init__(self):
        self.macros={}
    
    # Retrieve the MTE for this macro name
    def __getitem__(self,name):
        return self.macros[name]

    # Define / redefine the macro with this name
    def define(self,oper):
        assert isinstance(oper,asmbase.ASMOper),\
            "%s 'oper' argument must be an asmbase.ASMOper object: %s" \
                % (assembler.eloc(self,"define",module=this_module),oper)
        assert oper.info._defined is not None,\
            "%s macro definition line is None: %s" \
                % (assembler.eloc(self,"define",module=this_module),macro)

        name=oper.info.name
        try:
            entry=self.macros[name]
            # Macro is being redefined
            entry.redefine(oper)
        except KeyError:
            # First macro definition with this name
            self.macros[name]=MTE(oper)

    # Emulate dictionary get method
    def get(self,key,default=None):
        return self.macros.get(key,default)

    # Return iterable on macro names
    def keys(self):
        return self.macros.keys()


# Macro Definition Table Entry
class MTE(object):
    def __init__(self,oper):
        self.oper=oper            # ASMOper object of this macro
        self.name=oper.info.name  # Macro name

        self.xref=asmbase.XREF()  # Cross-reference object tracks references
        self.xref.define(oper.info._defined)
        # Allow external users to update this macro refs. via the macro object
        oper.info._xref=self.xref
        # By passing the same XREF object to each definition of macros with the
        # same names, all references and all definitions of the macros are
        # accumulated here.  The listing module uses _this_ to preprare the report.

    # Redifine the macro with this entry's name
    def redefine(self,oper):
        assert oper.info.name==self.name,\
            "%s macro entry name, '%s' does not match macro definition: '%s'" \
                % (assembler.eloc(self,"redefine",module=this_module),\
                    self.name,oper.info.name)

        self.oper=oper             # The ASMOper object has the macro definition!
        # Allow external users to update this macro refs. via the macro object
        oper.info._xref=self.xref
        self.xref.define(oper.info._defined)

    # Add a reference to this macro
    def reference(self,line):
        self.xref.ref(line)


if __name__ == "__main__":
    raise NotImplementedError("%s - intended for import use only" % this_module)