#!/usr/bin/python3.3
# Copyright (C) 2013 Harold Grovesteen
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

# Python imports:
import functools    # Access the comparison to key function for sorting in V3.
from ipl.translate import A2E  # Access the EBCDIC to ASCII translation table

# This module provides support for generation of GNU as source primarily intended
# for wrapper functionality, not detailed assembler insructions.
#
# The following hierarchy of classes is used


class as_base(object):
    # This class defines the base signature of each factory class and provides
    # useful functions for the sub classes
    #
    # Instance arguments:
    #    classes   A list of all of the classes of which its instances are
    #              valid for the subclass
    #    dicts     Controls which instances of valid classes will be tracked by
    #              Name.  For each class tracked by name, the corresponding 
    #              entry in the dicts list will be the dictionary instance in which
    #              it is tracked.  For classes not tracked by name, its 
    #              corresponding entry should be None. If omitted, the default is no
    #              classes are tracked by name.  If a single dictionary is provided
    #              in the dicts argument list, all valid classes will be tracked
    #              in that dictionary.  It is the responsibility of the tracked
    #              subclass to provide its tracking name via the Name() method.
    #    lists     Controls which instances of valid classes will be tracked in a
    #              list in the order in which it was added.  For each class that
    #              is kept in the order created will be the list in which the class
    #              instance is tracked.  If a single list is provided, all valid
    #              classes will be tracked in the single list.  If omitted, no
    #              valid classes will be tracked.
    def __init__(self,classes=[],dicts=[],lists=[]):
        self.dicts=self._cklist(dicts,len(classes),"dicts")
        self.lists=self._cklist(lists,len(classes),"lists")
        self.classes=classes
        #self.seq=seq
       
    # Add an object to a tracking list and/or dictionary.
    def _add(self,aso):
        if len(self.classes)==0:
            raise NotImplementedError(\
                "as_base: error: class %s has not enabled instance tracking" \
                % self.__class__.__name__)
        idx=self._isValidClass(aso)
        d=self.dicts[idx]
        l=self.lists[idx]
        if d!=None:
            name=aso._name()
            d[name]=aso
        if l!=None:
            l.append(aso)

    # This method validates that only valid classes are tracked.  It returns the
    # index corresponding to the element in the 'dicts' or 'lists' lists that 
    # controls tracking of the class.
    # 
    # If the class is not valid for this as_base subclass, it will raise a
    # TypeError.  This is a coding problem that needs remedy.
    def _isValidClass(self,instance):
        for x in range(len(self.classes)):
            cls=self.classes[x]
            if isinstance(instance,cls):
                return x
        raise TypeError(\
            "%s: error: class not authorized for registration: %s" \
             % (self.__class__.__name__,instance.__class__.__name__))
       
    # This method checks that the 'dicts' and 'lists' arguments are make sense
    # and are builds the list appropriately based upon the supplied arguments
    # values.
    def _cklist(self,lst,n,value):
        if len(lst)==0:
            l=[]
            for x in range(n):
                l.append(None)
            return l
        if value=="dicts":
            valid=dict
        else:
            valid=list
        if len(lst)==1:
            l=[]
            entry=lst[0]
            if not isinstance(entry,valid):
                raise ValueError(\
                    "as_base: error: entry 1 in %s argument not a: %s"\
                    % (value, valid.__name__))
            for x in range(n):
                l.append(entry)
            return l
        if len(lst)!=n:
            raise IndexError(\
                "as_base: error: %s must contain %s entries: %s" \
                % (value,n,len(lst)))
        for x in range(n):
            entry=lst[x]
            if entry is not None and not isinstance(entry,valid):
                raise ValueError(\
                    "as_base: error: entry %s in %s argument not a: %s"\
                    % (x, value, valid.__name__))
        return lst

    # This method returns the subclass' name by which it is tracked.
    # If subclass does not provide a name attribute the class cannot be tracked and
    # raises a AttributeError.  This is a coding error that must be remedied by
    # either supplying a name or removing the class from the 'dicts' argument of
    # the subclass tracking the instances.
    def _name(self):
        # Return the name by which the instance is recognized
        try:
            return self.name
        except AttributeError:
            raise AttributeError("%s: error: can not be registerd by name"\
                % (self.__class__.__name__))

    # This method is called when a subclass generates the primary content of one
    # of its subclasses.  It must return a string and it must be supplied by each
    # as_base subclass that generates GNU as content.
    def body(self,script,indent=""):
        raise NotImplementedError(\
            "as_base: error: class %s must provide method: body" \
            % (self.__class__.__name__))
    
    def generate(self,script):
        s=self.prefix(script)
        if not isinstance(s,str):
            raise ValueError("as_base: error: did not return a string: %s.prefix()"\
                % (self.__class__.__name__))
        s=self.body(s)
        if not isinstance(s,str):
            raise ValueError("as_base: error: did not return a string: %s.body()"\
                % (self.__class__.__name__))
        s=self.suffix(s)
        if not isinstance(s,str):
            raise ValueError("as_base: error: did not return a string: %s.suffix()"\
                % (self.__class__.__name__))
        return s
    
    # This method gives the opportunity for a subclass that generates GNU as output
    # to add content before the body itself is generated.  By default it simply
    # returns the current script being built without change.  If overridden by a
    # subclass it must return a string.
    def prefix(self,script):
        return script
        
    # This method gives the opportunity for a subclass that generates GNU as output
    # to add content following that of the body.  By default this method returns
    # the current script being built without change.  If overridden by a subclass
    # it must return a string.
    def suffix(self,script):
        return script

    #def sequence(self):
    #    for x in self.seq:
    #        self.sequence_list(x)
    #def sequence_list(self,lst):
        # Effectively an in place sort of the presented list
    #    sort_list=[]
    #    for x in range(len(lst)):
    #        entry=lst[x]     # entry being sorted
    #        cls_pos=self.classes.index(entry.__class__)  # where in class list
    #        sentry=sort(cls_pos,x,entry)
    #        sort_list.append(sentry)
    #    #sort_list.sort()
    #    new_list=sorted(sort_list,key=functools.cmp_to_key(sort.compare))
    #    for x in range(len(new_list)):
    #        lst[x]=sort_list[x].obj
    #    #return lst
            
class as_source(as_base):
    def __init__(self):
        self.cmdlist=[]
        self.macros={}
        # If a class is not in this list, it can't be added to the source
        self.cls=[]
        self.dct=[]
        self.lst=[]
        self.define(as_align,lst=self.cmdlist)
        self.define(as_ascii,lst=self.cmdlist)
        self.define(as_byte,lst=self.cmdlist)
        self.define(as_comment,lst=self.cmdlist)
        self.define(as_ebcdic,lst=self.cmdlist)
        self.define(as_else,lst=self.cmdlist)
        self.define(as_endif,lst=self.cmdlist)
        self.define(as_global,lst=self.cmdlist)
        self.define(as_hword,lst=self.cmdlist)
        self.define(as_ifdef,lst=self.cmdlist)
        self.define(as_ifndef,lst=self.cmdlist)
        self.define(as_incbin,lst=self.cmdlist)
        self.define(as_include,lst=self.cmdlist)
        self.define(as_label,lst=self.cmdlist)
        self.define(as_long,lst=self.cmdlist)
        self.define(as_macro,lst=self.cmdlist)
        self.define(as_octa,lst=self.cmdlist)
        self.define(as_quad,lst=self.cmdlist)
        self.define(as_set,lst=self.cmdlist)
        self.define(as_short,lst=self.cmdlist)
        self.define(as_text,lst=self.cmdlist)
        self.define(macro,dct=self.macros)
        super().__init__(classes=self.cls,dicts=self.dct,lists=self.lst)
        self.indent=" "*12
        
    def add(self,aso):
        self._add(aso)
        # Update object with default indent if not specified when the object
        # was created.
        if isinstance(aso,macro):
            return
        if aso.ind is None:
            aso.ind=self.indent
        
    # Generates the GNU as source body based upon added command instances
    def body(self,script):
        for x in self.cmdlist:
            script=x.generate(script)
        return script
        
    # This is the primary method that returns the generated GNU as source
    def create(self):
        return self.generate("")

    # Builds the lists for the as_base superclass
    def define(self,func,dct=None,lst=None):
        self.cls.append(func)
        self.dct.append(dct)
        self.lst.append(lst)

    # These methods generate more complex sequences of related statements
    def align(self, stg,ignore=False):
        if not isinstance(stg,as_stg):
            raise ValueError("gas_factory: error: as_source can only naturally "
                "align instances of as_stg, encountered: %s" % stg)
        alignment=stg.alignment
        if alignment>1:
            self.add( as_align(alignment,ignore=ignore) )
        self.add(stg)
        
    def align_local(self,align,symbol):
        self.add( as_align(align) )
        self.add( as_label(symbol,gbl=gbl) )
        
    def align_global(self,align,symbol):
        self.add( as_align(align) )
        self.add( as_global(symbol,label=symbol,gbl=True) )
        
    def macro(self,name,**kwds):
        try:
            mac=self.macros[name]
        except KeyError:
            raise ValueError("gas_factory: error: src.macro() did not find macro "
                "definition: %s" % name)
        parms=mac.sig(kwds)
        self.add( as_macro(name,parms) )

class as_cond(as_base):
    def __init__(self,ignore=False,ind=None):
        super().__init__()
        self.ignore=ignore
        self.ind=ind
    def format(self):
        if self.ignore:
            return ""
        return self.ind

# This class manages all statements that can be expected to have a label.
# The label is manages to be part of the indent area or on the preceding line
# It is the responsibility of the subclass to manage label placement and generation
#
# Instance arguments:
#   label   The label applied to this statement, a string or instance of as_symbol
#   gbl     If label is a string, is this a global label (True) or local (False).
#           Defaults to 'False'
#   ign     Indicates whether the statement will ignore indent handling.  Specify
#           as 'True' to ignore indent handling.  Defaults to 'False'
class as_stmt(as_base):
    def __init__(self,label=None,gbl=False,ignore=False,ind=None):
        super().__init__()
        self.ignore=ignore
        self.ind=ind
        if label is None:
            self.length=0
            self.label=""
            return
        sym=as_symbol(label,gbl=gbl)
        self.label="%s: " % sym.string()
        self.length=len(self.label)      # Make sure room for the label

    def format(self):
        if self.ignore:
            ind=""
        else:
            ind=self.ind
        if self.length==0:
            return ind
        if self.length>len(ind):
            return "%s\n%s" % (self.label,ind)
        lbl=self.label
        return lbl.ljust(max(len(lbl),len(ind)))

class as_stg(as_stmt):
    def __init__(self,content,d,label=None,gbl=False,usehex=False,
                 ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.as_dir=d
        self.content=self.validContent(content,usehex=usehex)
    def body(self,script):
        d=self.as_dir
        d=d.ljust(max(len(d),6))
        return "%s%s%s %s\n" % (script,self.format(),d,self.content.string())
    def validContent(self,content,usehex=False):
        if content.__class__ in [as_symbol,as_value,as_number,int]:
            return as_value(content,usehex=usehex)
        raise ValueError("gas_factory: error: as_stg unexpected content: %s" \
            % content)

class as_align(as_stmt):
    def __init__(self,align,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.align=align
    def body(self,script):
        return "%s%s.align %s\n" % (script,self.format(),self.align)
            
class as_ascii(as_stmt):
    def __init__(self,ascii,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.ascii=ascii
    def body(self,script):
        return '%s%s.ascii "%s"\n' % (script,self.format(),self.ascii)

class as_byte(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,\
        ignore=False,ind=None):
        super().__init__(content,".byte",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=ind)
        self.alignment=1

class as_comment(as_cond):
    def __init__(self,content="",ignore=True,ind=None):
        super().__init__(ignore=ignore,ind=ind)
        if len(content)>0 and content[0]!="#":
            self.content="# %s" % content
        else:
            self.content=content
    def body(self,script):
        return "%s%s%s\n" % (script,self.format(),self.content)

# This class creates the illusion of a .ebcdic directive similar to .ascii
class as_ebcdic(as_stmt):
    def __init__(self,ebcdic,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        ebc=ebcdic.translate(A2E)
        asc=""
        for x in range(len(ebc)):
            val="0"+hex(ord(ebc[x]))[2:]
            asc="%s\\x%s" % ( asc,val[-2:].upper() )
        self.ascii=asc
    def body(self,script):
        return '%s%s.ascii "%s"\n' % (script,self.format(),self.ascii)

class as_else(as_cond):
    def __init__(self,ignore=True,ind=None):
        super().__init__(ignore=ignore,ind=ind)
    def body(self,script):
        return "%s%s.else\n" % (script,self.format())
        
class as_endif(as_cond):
    def __init__(self,ignore=True,ind=None):
        super().__init__(ignore=ignore,ind=ind)
    def body(self,script):
        return "%s%s.endif\n" % (script,self.format())

class as_global(as_stmt):
    def __init__(self,symbol,label=None,gbl=False,ind=None):
        super().__init__(label=symbol,gbl=gbl,ignore=False,ind=ind)
        self.sym=self.validSymbol(symbol)
    def body(self,script):
        return "%s%s.global %s\n" % (script,self.format(),self.sym.string())
    def validSymbol(self,symbol):
        if isinstance(symbol,as_symbol): 
            if symbol.gbl:
                return symbol
            else:
                raise ValueError("gas_factory: error: as_global received local "
                "'symbol' argument: %s" % symbol.string())
        if isinstance(symbol,str):
            return as_symbol(symbol,gbl=True)
        raise ValueError("gas_factory: error: as_global received unexpected "
                "'symbol' argument: %s" % symbol)

class as_hword(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,\
                 ignore=False,ind=None):
        super().__init__(content,".hword",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=ind)
        self.alignment=2

class as_ifdef(as_cond):
    def __init__(self,sym,gbl=False,ignore=True,ind=None):
        super().__init__(ignore=ignore,ind=ind)
        if isinstance(sym,as_symbol):
            self.sym=sym.string()
        else:
            self.sym=as_symbol(sym,gbl=gbl).string()
    def body(self,script):
        return "%s%s.ifdef %s\n" % (script,self.format(),self.sym)

class as_ifndef(as_cond):
    def __init__(self,sym,gbl=False,ignore=True,ind=None):
        super().__init__(ignore=ignore,ind=ind)
        if isinstance(sym,as_symbol):
            self.sym=sym.string()
        else:
            self.sym=as_symbol(sym,gbl=gbl).string()
    def body(self,script):
        return "%s%s.ifndef %s\n" % (script,self.format(),self.sym)

class as_incbin(as_stmt):
    def __init__(self,filename,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.filename=filename
    def body(self,script):
        return '%s%s.incbin "%s"\n' % (script,self.format(),self.filename)

class as_include(as_stmt):
    def __init__(self,filename,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.filename=filename
    def body(self,script):
        return '%s%s.include "%s"\n' % (script,self.format(),self.filename)

class as_label(as_stmt):
    def __init__(self,label,gbl=False):
        super().__init__(label=label,gbl=gbl,ignore=True,ind=None)
    def body(self,script):
        return "%s%s\n" % (script,self.label)
    def symbol(self):
        return self.label

class as_long(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,\
                 ignore=False,ind=None):
        super().__init__(content,".long",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=ind)
        self.alignment=4

class as_macro(as_stmt):
    def __init__(self,macro,parms,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.macro=macro
        self.parms=parms  # From macro.sig() method
    def body(self,script):
        return "%s%s%s %s\n" % (script,self.format(),self.macro,self.parms)

# This class manages numeric values
class as_number(object):
    def __init__(self,number,usehex=False):
        if not isinstance(number,int):
            raise ValueError("gas_factory: error: as_number requires integer as"
                "'number' argument: %s" % self.number.__class__.__name__)
        self.num=number
        self.usehex=usehex
    def string(self):
        if self.usehex:
            return hex(self.num)
        return "%s" % self.num

class as_octa(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,\
                 ignore=False,ind=None):
        super().__init__(content,".octa",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=None)
        self.alignment=16

class as_quad(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,
                 ignore=False,ind=None):
        super().__init__(content,".quad",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=None)
        self.alignment=8

class as_set(as_cond):
    def __init__(self,symbol,value,gbl=False,usehex=False,ignore=False,ind=None):
        super().__init__(ignore=ignore,ind=ind)
        self.sym=self.validSymbol(symbol)
        self.val=self.validValue(value,gbl=gbl,usehex=usehex)
    def body(self,script):
        return "%s%s.set   %s,%s\n" \
            % (script,self.format(),self.sym.string(),self.val.string())
    def validSymbol(self,symbol,gbl=False):
        if symbol.__class__ in [str,as_symbol]:
            return as_value(symbol,gbl=gbl)
        raise ValueError("gas_factory: error: as_set encountered unexpected "
            "sybmol: %s" % symbol)
    def validValue(self,value,gbl=False,usehex=False):
        if value.__class__ in [str,int,as_symbol,as_number,as_value]:
            return as_value(value,gbl=gbl,usehex=usehex)
        raise ValueError("gas_factory: error: as_set encountered unexpected "
            "value: %s" % value)

class as_short(as_stg):
    def __init__(self,content,label=None,gbl=False,usehex=False,\
                 ignore=False,ind=None):
        super().__init__(content,".hword",label=label,gbl=gbl,usehex=usehex,\
            ignore=ignore,ind=ind)
        self.alignment=2

class as_text(as_stmt):
    def __init__(self,sub=0,label=None,gbl=False,ignore=False,ind=None):
        super().__init__(label=label,gbl=gbl,ignore=ignore,ind=ind)
        self.sub=sub
    def body(self,script):
        return "%s%s.text  %s\n" % (script,self.format(),self.sub)
        
# This class manages a label, making it a global or local.  It must not be
# registered for tracking by the as_source class.
class as_symbol(object):
    def __init__(self,label,gbl=False):
        if isinstance(label,int) and label>=0 and label<=9:
            self._string=self.LL_string
            self._len=self.LL_length
            self.label=label
            return
        if isinstance(label,str):
            if len(label)==0:
                raise ValueError("as_symbol: error: label must not be of zero "
                    "length")
            if gbl:
                self._string=self.GS_string
                self._len=self.GS_length
            else:
                self._string=self.LS_string
                self._len=self.LS_length
            self.label=label
            return
        raise ValueError("gas_factory: error: as_symbol argument must be"
             "a string: %s" % label)
    def __len__(self):
        return self._len()
    # These two methods are for GNU as global symbols
    def GS_length(self):
        return len(self.label)
    def GS_string(self):
        return self.label
    # These two methods are for GnU as local labels
    def LL_length(self):
        return 1
    def LL_string(self):
        return "%s" % self.label
    # These two methods are for GNU as local symbols
    def LS_length(self):
        return len(self.label)+2
    def LS_string(self):
         return ".L%s" % self.label
    # Public method for returning the symbol as a string
    def string(self):
        return self._string()
        
# This class manages command arguments that may be either labels or numbers
class as_value(object):
    def __init__(self,value,gbl=False,usehex=False):
        if isinstance(value,str):
            self.val=as_symbol(value,gbl=gbl)
        elif isinstance(value,int):
            self.val=as_number(value,usehex=usehex)
        elif isinstance(value,as_symbol):
            self.val=value
        elif isinstance(value,as_number):
            self.val=value
        elif isinstance(value,self.__class__):
            sefl.val=value
        else:
            raise ValueError("gas_factory: error: as_value received unexpected "
                "'value' argument: %s" % value)
    def string(self):
        return self.val.string()

class macro(as_base):
    def __init__(self,name):
        super().__init__()
        self.name=name
        # Dictionary of macro parameters:
        #  args['parm']==macro_opt  implies the parameter is optional
        #  args['parm']==macro_dft  implies the parameter a default value
        #  args['parm']==macro_req  implies the parameter is required
        self.parms=[]
        self.args={}
    def _ckdup(self,parm):
        try:
            p=self.args[parm]
            raise ValueError("gas_factory: error: duplicate macro parameter: %s" \
                % parm)
        except KeyError:
            return
    def _name(self):
        return self.name
    def dft(self,parm,default):
        self._ckdup(parm)
        self.args[parm]=macro_dft(parm,default)
        self.parms.append(parm)
    def opt(self,parm):
        self._ckdup(parm)
        self.args[parm]=macro_opt(parm)
        self.parms.append(parm)
    def req(self,parm):
        self._ckdup(parm)
        self.args[parm]=macro_req(parm)
        self.parms.append(parm)
    def sig(self,kwds):
        arguments=""
        for x in self.parms:
            p=self.args[x]
            a=p.vdict(kwds)
            if a is None:
                continue
            arguments="%s%s " % (arguments,a)
        return arguments[:-1]
    
class macro_parm(object):
    def __init__(self,name):
        self.name=name
        
class macro_dft(macro_parm):
    def __init__(self,name,default):
        super().__init__(name)
        self.default=default
    def vdict(self,dct):
        try:
            p=dct[self.name]
        except KeyError:
            return None
        if p==self.default:
            return None
        return "%s=%s" % (self.name,p)

class macro_req(macro_parm):
    def __init__(self,name):
        super().__init__(name)
    def vdict(self,dct):
        try:
            p=dct[self.name]
        except KeyError:
            raise ValueError("gas_factory.py: error: required macro argument "
                "missing: %s" % self.name)
        return p

class macro_opt(macro_parm):
    def __init__(self,name):
        super().__init__(name)
    def vdict(self,dct):
        try:
            p=dct[self.name]
            return p
        except KeyError:
            return None

if __name__ == "__main__":
    raise NotImplementedError("gas_factory.py - must only be imported")
    # Uncomment the preceding statement to run local tests.
    
    src=as_source()
    src.add( as_ifndef("name_S") )
    src.add( as_set("name_S",1,ignore=True) )
    src.add( as_comment("Let's try a comment") )
    src.add( as_text() )
    src.add( as_ascii("abc",label="s1") )
    src.add( as_ebcdic("abc",label="s2") )
    src.add( as_byte(0,label="a1") )
    src.add( as_hword(0,label="a_very_long_symbol",usehex=True) )
    src.add( as_long(0,label="lgenough",usehex=True) )
    src.align_global(4,"thesym")
    src.align( as_quad(0,usehex=True) )
    src.add( as_octa(0,label=0,usehex=True) )
    src.add( as_endif() )
    m1=macro("amacro")
    m1.req("req1")
    m1.req("req2")
    m1.opt("opt2")
    m1.dft("b","0b")
    m1.dft("br","13")
    src.add( m1 )
    src.macro("amacro",req1="a",req2="b",opt2="yes",br="13")
    print(src.create())