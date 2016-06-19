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

# This module creates a source of physical lines from a model.  It follows the normal
# sequence of processing for a logical line but from the perspective of a line being
# generated during macro invocation.

this_module="model.py"

# Python imports: None
# SATK imports: None
# ASMA imports:
import assembler
import asmbase
import macopnd
import macsyms


# Model statement processing is delegated to this object.  It may utilize the 
# statement object's methods for some of its processing.
#
# The generic model statement uses: alt=True (for macro statement models), sep=True
# (also required for macro statement models), and spaces=False.

# Three objects result from logical line processing with the following content:
#
#     Object     Content                         Creator
#
#   - LField    label field                      asmline.Logline.fields() method
#   - LField    operation field                  asmline.Logline.fields() method
#   - LOperand  indivdual operand field operand  ASMStmt.parse_line(), sep=True 
#
# These objects form the basis for symbolic variable replacement and statement 
# generation.  Statement generation creates text strings as if they had been read
# from a file using stream file format continuation conventions.
#
# For model statements coded with the normal statement format, what is expected
# resutls in the generated physical input lines.
#
# For model statements coded with the alternate statement format, comments on
# individual model statement lines are lost in the model statement.  All operands
# are compressed into one or more physical lines using standard statement format
# continuation conventions (of stream format text files).  This only occurs for
# macro model statements which normally are suppressed in the assembly listing.  This
# processing is only visible if the mcall command-line option is in use.
#
# This object is created by the asmstmts.ModelStmt class.  It is used during
# Pass0 processing for symbolic replacement recognition by creating ASMExprChar
# (character expression) objects.  The object is then passed to the macro engine
# operation responsible for generating model statements, asmmacs.Model.  During
# macro invocation the Model object uses this object to actually create the
# physcal input line images passed back to the assembler for assembly.
class Model(object):
    def __init__(self,asm,stmt,debug=False):
        self.asm=asm
        self.stmt=stmt
        self.debug=debug

        # These attributes are established during parsing operations
        self.label_fld=None       # See parse_label() method
        self.oper_fld=None        # See parse_operation() method      
        self.operands=[]          # See parse_operands() method
        self.comments=[]          # See find_comment() method
        self.comment_pos=None     # Starting position of the comment

        # Symbolic replacements:
        self.rlbl=''
        self.roper=None
        self.ropnd=[]
        
        # Handle loud comment model statements here
        self.loud=None
        logline=stmt.logline
        if __debug__:
            if debug:
                print("%s logline: %s" \
                    % (assembler.eloc(self,"__init__",module=this_module),logline))

        if logline.comment and not logline.quiet:
            self.loud=logline.plines[0].text

        if __debug__:
            if debug:    
                print("%s [%s] loud: %s" \
                    % (assembler.eloc(self,"__init__",module=this_module),\
                        stmt.lineno,self.loud))

    # Generate one or more physical lines for macro source object
    # Returns:
    #   a list of strings, one per "physical line" from the macro source
    def create(self,debug=False):
        ddebug=self.debug or debug
        if self.loud is not None:
            if __debug__:
                if ddebug:
                    print('%s returning loud comment: "%s"' \
                        % (assembler.eloc(self,"create",module=this_module),\
                            self.loud))
            return [self.loud,]

        # Generate the model statement fields
        label=self.rlbl.ljust(max(8,len(self.rlbl)))
        if __debug__:
            if ddebug:
                cls_str=assembler.eloc(self,"create",module=this_module)
                print("%s label: '%s'" % (cls_str,label))

        line="%s %s" % (label,self.roper)
        line=line.ljust(max(14,len(line)))
        operands=""
        for opnd in self.ropnd:
            operands="%s,%s" % (operands,opnd)
            if __debug__:
                if self.debug:
                    print("%s operands: '%s'" % (cls_str,operands))
        # Remove the first superfluous comma created by the loop      
        operands=operands[1:]
        if __debug__:
            if self.debug:
                print("%s operands: '%s'" % (cls_str,operands))

        line="%s %s" % (line,operands)
        if __debug__:
            if ddebug:
                print("%s line: '%s'" % (cls_str,line))
                
        # Make into continuatin lines if need be and add comment
        cont=" "*15
        plines=[]
        pline=None
        ndx=0
        end=len(line)
        while ndx<end:
            if pline is not None:
                pline="%s\\" % pline  # Add stream file format continuation
                plines.append(pline)
                pline=None
            if len(plines)==0:
                # First line - Use columns 1-71 (71 characters)
                pline_break=min(71,end)
                pline=line[ndx:pline_break]
                ndx+=len(pline)
                continue
            # Additional line - Use columns 16-71 (56 characters) for operands
            pline_break=min(ndx+56,end)
            plinec=line[ndx:pline_break]
            pline="%s%s" % (cont,plinec)
            ndx+=len(plinec)
            
        # pline is the last or maybe only physical line.  It gets the comment
        assert pline is not None,\
            "%s last generated physical line with operands not present" \
                % assembler.eloc(self,"create",module=this_module)
        
        if self.comment_pos is not None:
            ndx=0
            while ndx<len(self.comments):
                comment_pline=self.comments[ndx]  # The comment being added
                comment=comment_pline.text[comment_pline.comment_start:]
                comment=comment.rstrip()    # Leave off any trailing spaces
                if ndx!=0:
                    # Add the pending line
                    pline="%s\\" % pline
                    plines.append(pline)
                    pline=None
                    comment=self.comments[ndx].text
                    comment=comment.rstrip()
                    pline=comment  # This is now the pending line
                    ndx+=1
                    continue
                    
                # Last line of operands gets the comment
                if self.comment_pos>len(pline):
                    # Comment fits on last physical line add it
                    pline=pline.ljust(self.comment_pos)  # Extend line for position
                    pline="%s%s" % (pline,comment)
                    ndx+=1
                else:
                    # Need to put the comment on the next physical line because it
                    # overlaps with the generated operand field
                    # Continue the operand field line of the statement
                    pline="%s\\" % pline
                    plines.append(pline)
                    pline=" " * self.comment_pos
                    pline="%s%s" % (pline,comment)
                    ndx+=1

        assert pline is not None,\
            "%s last generated physical line with comments not present" \
               % assembler.eloc(self,"create",module=this_module)

        # Add the last physical line to the list
        plines.append(pline)

        if __debug__:
            if ddebug:
                for n,p in enumerate(plines):
                    print('%s returning[%s]: "%s"' \
                        % (assembler.eloc(self,"create",module=this_module),n,p))

        #print("%s plines: %s" \
        #    % (assembler.eloc(self,"create",module=this_module),plines))
        return plines

    # Performs a symbolic replacement parse of a field or operand
    def __parse(self,asm,stmt,field,debug=False):
        ddebug=self.debug or debug
        if __debug__:
            if ddebug:
                print("%s [%s] field.amp: %s" \
                    % (assembler.eloc(self,"__parse",module=this_module),\
                        stmt.lineno,field.amp))
        if not field.amp:
            return field.text
        pm=asm.PM
        try:
            return pm.parse_model(stmt,field,debug=ddebug)
        except assembler.AsmParserError as ape:
            raise assembler.AssemblerError(source=stmt.source,line=stmt.lineno,\
                msg=ape.msg)

    def __replace(self,fld,exp):
        if isinstance(fld,str):
            return fld

        # Evaluate character expression
        assert isinstance(fld,macopnd.PChrExpr),\
            "%s 'fld' argument must be an macopnd.PChrExpr object: %s" \
                % (assembler.eloc(self,"__replace",module=this_module),fld)

        v=fld.value(external=exp,debug=False,trace=False)
        if isinstance(v,(macsyms.C_Val,macsyms.A_Val,macsyms.B_Val)):
            return v.string()
        elif isinstance(v,str):
            return v

        # Result unsupported as replacement value within a model statement
        # Provide the logical line from within the macro that triggers the error
        # for debugging purposes.
        print("%s stmt[%s]:\n%s" \
            % (assembler.eloc(self,"__replace",module=this_module),\
                self.stmt.lineno,self.stmt.logline))
        raise ValueError("%s character expression result not C_Val or string: %s" \
            % (assembler.eloc(self,"__replace",module=this_module),v))

    # Returns a list of the normal statement format lines with comments
    # If alternate statement format lines are present, comments are ignored
    def find_comment(self,stmt,debug=False):
        # This processing depends upon information supplied during parse_line
        # within the physical line objects with regards to where comments occur
        first_comment=None       # Index of first line with comment
        comments=[]              # Physical lines with comments
        opnd_and_comment=[]      # Indexes of plines with both comments and operands

        if __debug__:
            if debug:
                cls_str=assembler.eloc(self,"find_comment",module=this_module)

        for n,pline in enumerate(stmt.logline.plines):
            if __debug__:
                if debug:
                    print("%s [%s] pline[%s]: %s" % (cls_str,stmt.lineno,n,pline))
            if pline.comment_start is None:
                continue
            if first_comment is None:
                first_comment=n
            comments.append(pline)
            if pline.operand_start is not None:
                opnd_and_comment.append(n)

        if __debug__:
            if debug:
                print("%s [%s] first comment: %s operand and comments: %s" \
                    % (cls_str,stmt.lineno,first_comment,opnd_and_comment))
                if comments:
                    print("%s [%s] comments:" % (cls_str,stmt.lineno))
                    for com in comments:
                        print("    %s" % com)

        if first_comment:
            for ndx in opnd_and_comment:
                if ndx>first_comment:
                    # We have operands following the first comment.  This occurs with
                    # alternate statement format comments, so we are ignoring these
                    # comments.
                    self.comments=[]
                    return

        # All comments follow the first normal line so these are returned
        if comments:
            self.comment_pos=comments[first_comment].comment_start
            self.comments=comments

    def parse(self,asm,stmt,debug=False):
        ddebug=self.debug or debug
        if self.loud is not None:
            # No parsing for loud comment model statements
            return
        self.parse_operation(asm,stmt,debug=ddebug)
        self.parse_label(asm,stmt,debug=ddebug)
        self.parse_operands(asm,stmt,debug=ddebug)
        self.find_comment(stmt,debug=ddebug)

    # Performs a symbolic replacement parse of the label field
    def parse_label(self,asm,stmt,debug=False):
        if not stmt.label_fld:
            self.label_fld=""
            return

        result=self.__parse(asm,stmt,stmt.label_fld,debug=debug)
        self.label_fld=self.prepare_result(stmt,result,"label",debug=debug)

    def parse_operands(self,asm,stmt,debug=False):
        for n,opnd in enumerate(stmt.operands):
            if opnd is None:
                self.operands.append("")
                continue
            popnd=self.__parse(asm,stmt,opnd,debug=debug)
            popnd=self.prepare_result(stmt,popnd,"opndp%s" % n,debug=debug)
            self.operands.append(popnd)

    def parse_operation(self,asm,stmt,debug=False):
        result=self.__parse(asm,stmt,stmt.oper_fld,debug=debug)
        self.oper_fld=self.prepare_result(stmt,result,"oper",debug=debug)

    # Returns the pratt token for evaluation
    def prepare_result(self,stmt,result,desc,debug=False):
        if isinstance(result,str):
            if __debug__:
                if debug:
                    print("%s [%s] %s: '%s'" \
                        % (assembler.eloc(self,"prepare_result",\
                            module=this_module),stmt.lineno,desc,result))
            return result

        if __debug__:
            if debug:
                print("%s [%s] %s: %s" \
                    % (assembler.eloc(self,"prepare_result",\
                        module=this_module),stmt.lineno,desc,result))
        result.prepare(stmt,"[%s] model-%s" % (stmt.lineno,desc))
        return result.ctoken()   

    # Perform any required symbolic replacement
    def replace(self,exp,debug=False):
        ddebug=self.debug or debug
        # Make sure my fields are empty
        self.rlbl=""
        self.roper=None
        self.ropnd=[]
        if __debug__:
            if ddebug:
                print("%s [%s] logline: %s" \
                    % (assembler.eloc(self,"replace",module=this_module),\
                        self.stmt.lineno,self.stmt.logline))
                print("%s [%s] loud: %s" \
                    % (assembler.eloc(self,"replace",module=this_module),\
                        self.stmt.lineno,self.loud))

        if self.loud is not None:
            # Nothing to do for a loud comment in a macro body.
            return
        self.rlbl=self.__replace(self.label_fld,exp)
        if __debug__:
            if ddebug:
                print("%s [%s] rlbl: '%s'" \
                    % (assembler.eloc(self,"replace",module=this_module),\
                        self.stmt.lineno,self.rlbl))

        self.roper=self.__replace(self.oper_fld,exp)
        if __debug__:
            if ddebug:
                print("%s [%s] roper: '%s'" \
                    % (assembler.eloc(self,"replace",module=this_module),\
                        self.stmt.lineno,self.roper))

        for n,opnd in enumerate(self.operands):
            res=self.__replace(opnd,exp)
            if __debug__:
                if ddebug:
                    print("%s [%s] ropnd[%s]: '%s'" \
                        % (assembler.eloc(self,"replace",module=this_module),\
                            self.stmt.lineno,n,res))
            self.ropnd.append(res)


if __name__ == "__main__":
    raise NotImplementedError("%s - this module only supports import usage" \
        % this_module)
        