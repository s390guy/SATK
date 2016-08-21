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

# This module supports literal pools and their management.  Actual Literal objects
# are defined in the assembler module due to object reference dependencies.

# Python imports: None
# SATK imports: None
# ASMA imports: None
import asmbase
import asmline
import assembler

this_module="literal.py"


#
#  +--------------------+
#  |                    |
#  |   A LITERAL POOL   |
#  |                    | 
#  +--------------------+
#

# The literal pool manages the literals defined for the pool and provides the
# external interface of a symbol table.
class LiteralPool(asmbase.ASMSymTable):
    def __init__(self):
        super().__init__(assembler.Literal,"TtSsIiLl",wo=True,case=True)
        self._align=0        # Required alignment of the pool
        self.literals={}     # Dictionary of shared literals identified by its string
        self.unique=[]       # List of unshared unqiue literal
        self.ltorg=None      # The asmstmts.LTORG object creating this pool

        # Literal groups by sequence in which they are created
        self.group_seq=[LiteralGroup(size=16),
                        LiteralGroup(size=8),
                        LiteralGroup(size=4),
                        LiteralGroup(size=2),
                        LiteralGroup(size=1)]

        # Literal groups by aligned sizes
        self.groups={}
        for grp in self.group_seq:
            self.groups[grp.size]=grp
            
        # Pool ID - used to identify this pool object
        self.pool_id=None      # See LiteralPoolMgr.pool_new() method
            
        # This is the list of literals to be created in sequence
        self.pool_list=None    # See create() method

    def __len__(self):
        return len(self.literals)+len(self.unique)

    def __str__(self):
        if self.ltorg:
            ln=" [%s]" % self.ltorg
        else:
            ln=""
        return "LITERAL POOL%s: total: %s  shared: %s  unique: %s" \
            % (ln,len(self),len(self.literals),len(self.unique))

    # Creates the list of literals being created
    # Method Argument:
    #   line   the statement line number of the LTORG creating this pool
    #   debug  value passed on with Literal objects to allow enabling debugging of
    #          LiteralStmt objects.  This allow LiteralStmt objects to "inherit"
    #          the debug setting from the generating LTORG statement
    def create(self,line,debug=False):
        assert self.ltorg is None,\
            "%s pool has already been created by line number: %s" \
                % (assembler.eloc(self,"create",module=this_module),self.ltorg)

        for lit in self.literals.values():
            lit.trace=debug
            self.group(lit)
        for lit in self.unique:
            lit.trace=debug
            self.group(lit)

        lits=[]
        for grp in self.group_seq:
            if not grp.isEmpty():
                self._align= max(self._align,grp.size)
                lits.extend(grp.literals)
        self.pool_list=lits   # Save the list of literals for LTORG
        self.ltorg=line       # Remeber the line number that created me

    # Provide a formatted display of the literal pool
    # Method Arguments:
    #   indent  a string applied to each line for indenting
    #   string  Whether to return the final string (True) or print the display (False)
    def display(self,indent="",string=False):
        if self.ltorg:
            ln="[%s] " % self.ltorg
        else:
            ln=""
        lcl="%s    " % indent
        tot=0
        g=""
        for grp in self.group_seq:
            tot+=len(grp)
            g="%s\n%s%s" % (g,indent,grp.display(indent=lcl,string=True))
        s="%s%sLITERAL POOL %s - Entries:%s  Align: %s%s" \
            % (indent,ln,self.pool_id,tot,self._align,g)
        if string:
             return s
        print(s)

    # Return the Literal object for a given string.
    # Method Argument:
    #   lit_str  the complete literal string including the leading equal, =, sign.
    # Returns:
    #   a Literal object of the existing Literal being constructed
    # Exception:
    #   KeyError if the literal is new
    def fetch(self,lit_str,debug=False):
        assert isinstance(lit_str,str),\
            "%s 'lit_str' argument not a string: %s" \
                % (assembler.eloc(self,"fetch",module=this_module),lit_str)
        assert len(lit_str)>1 and lit_str[0]=="=",\
            "%s 'lit_str' argument is not a valid literal: '%s'" \
                % (assembler.eloc(self,"fetch",module=this_module),lit_str)

        lit=self.literals[lit_str]
        if __debug__:
            if debug:
                print("%s RETURNING LITERAL OBJECT: %r" \
                    % (assembler.eloc(self,"fetch",module=this_module),lit))
        return lit

    # Return all of the literals as a list
    def getList(self):
        lst=list(self.literals.values())
        lst.extend(self.unique)
        return lst

    # Identify the group for a specific literal
    # Returns:
    #   the LiteralGroup object into which the literal will be placed for creation
    def group(self,lit):
        assert lit.state==3,\
            "%s Literal.state not 3: %s" \
                % (eloc(self,"parse",module=this_module),lit)

        try:
            grp=self.groups[lit.length]
        except KeyError:
            grp=self.group_seq[4]
        lit.state=4
        grp.append(lit)

    # Returns True if the literal pool is empty, False otherwise
    def isEmpty(self):
        return (len(self.literals)+len(self.unique)) == 0

    # Add a new literal to the pool
    # Method Arguments:
    #   lit     an assembler.Literal being added to the pool
    #   line    the line number of the initial referencing statement
    def literal_new(self,lit,line,debug=False):
        lit.reference(line)
        if lit.unique:
            self.unique.append(lit)
            if __debug__:
                if debug:
                    print("%s [%s] LITERAL POOL %s ADDING UNIQUE: %r" \
                        % (assembler.eloc(self,"literal_new",module=this_module),\
                            line,self.pool_id,lit))
        else:
            self.literals[lit.name]=lit
            if __debug__:
                if debug:
                    print("%s [%s] LITERAL POOL %s ADDING: %r" \
                        % (assembler.eloc(self,"literal_new",module=this_module),\
                            line,self.pool_id,lit))

    # This method groups the pending literals by size in preparation for creation
    def select(self):
        for lit in self.literals.values():
            self.group(lit)
        for lit in self.unique:
            self.group(lit)


# This object maintains the group of literals in the sequence constructed.
class LiteralGroup(object):
    def __init__(self,size=None):
        self.size=size       # Length of all literals in the group.
        self.literals=[]     # A list of the literals in this group.
    
    def __len__(self):
        return len(self.literals)
    
    def __str__(self):
        return "LITERAL GROUP - size: %s  Literals: %s" % (self.size,self.literals)
    
    def append(self,lit):
        self.literals.append(lit)
        
    def display(self,indent="",string=False):
        #print("%s indent: '%s'" \
        #    % (assembler.eloc(self,"display",module=this_module),indent))
        s="%sLITERAL GROUP - Size: %s" % (indent,self.size)
        lcl="%s    " % indent
        for lit in self.literals:
            s="%s\n%s    state:%s  %r %s" % (s,lcl,lit.state,lit,lit)
        if string:
            return s
        print(s)
        
    def isEmpty(self):
        return len(self.literals)==0


#
#  +--------------------------+
#  |                          |
#  |   LITERAL POOL MANAGER   |
#  |                          | 
#  +--------------------------+
#

class LiteralPoolMgr(object):
    def __init__(self,asm):
        self.asm=asm         # The global assembler.Assembler object
        self.pools=[]        # List of literal pools in the order of creation
        self.cur_pool=None   # Current active literal pool
        self.pool_ndx=None   # Current pool index
        self.pool_new()      # Create the initial literal pool

    # Fetchs from the current literal pool the Literal object for the presented 
    # literal string
    # Method Argument:
    #   lit_str   The string that is the literal including its starting '=' sign
    # Returns:
    #   a Literal object
    # Exception:
    #   KeyError
    def fetch(self,lit_str,line,debug=False):
        #entry=self.cur_pool[lit_str]
        entry=self.cur_pool.fetch(lit_str,debug=debug)
        entry.reference(line)
        return entry

    # Generate the pool and create the new pool
    # Returns:
    #   the LiteralPool object corresponding to this pool
    # Method Arguments:
    #   line    The statement line number of the LTORG directive creating the pool
    def create(self,line,debug=False):
        pool=self.cur_pool
        pool.create(line,debug=debug)
        self.pool_new()
        return pool

    # Return the current literal pool
    def current(self):
        return self.cur_pool

    # Return all literals from all pools as a list
    # Method Argument:
    #   sort   Specify True to return the list sorted by literal name.
    def getList(self,sort=False):
        lst=[]
        # Create the list of all literals in the assembly
        for pool in self.pools:
            lst.extend(pool.getList())
        if sort:
            # If requested, sort the list in place by the name attribute, 
            # the literal specification.
            lst.sort(key=lambda literal:literal.name)
        return lst

    # Returns whether the current pool is empty (True) or not (False)
    def isEmpty(self):
        return self.cur_pool.isEmpty()

    def literal_new(self,lit,line,debug=False):
        assert isinstance(lit,assembler.Literal),\
            "%s 'lit' argument must be a Literal object: %s" \
                % (assembler.eloc(self,"literal_new",module=this_module),lit)

        self.cur_pool.literal_new(lit,line,debug=debug)

    def pool_new(self):
        self.cur_pool=pool=LiteralPool()
        self.pool_ndx=len(self.pools)
        pool.pool_id=self.pool_ndx
        self.pools.append(pool)

    def pool_next(self):
        self.pool_ndx+=1
        self.cur_pool=self.pools[self.pool_ndx]

    def pool_reset(self):
        self.pool_ndx=0
        self.cur_pool=self.pools[0]


if __name__ == "__main__":
    raise NotImplementedError("%s - this module only supports import usage" \
        % this_module)