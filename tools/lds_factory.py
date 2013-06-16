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

# This module provides a set of classes that can create GNU ld linker scripts.
#
# The following hierarchy of classes is used
#   lds_base          May register
#       lds_alias
#       lds_align
#       lds_assign
#       lds_entry
#       lds_in        
#       lds_memory    lds_region
#       lds_out       lds_align, lds_in, lds_provide
#       lds_phdr
#       lds_provide
#       lds_script    lds_format, lds_arch, lds_target, lds_memory, 
#                     lds_alias, lds_entry, lds_headers, lds_sections
#       lds_sections  lds_out
#
# Currently unsupported commands:
#   REGION_ALIAS

class lds_base(object):
    # This class defines the base signature of each factory class and provides
    # useful functions for the sub classes
    def __init__(self,classes=[],dicts=[],lists=[],seq=[]):
        self.dicts=self.cklist(dicts,len(classes),"dicts")
        self.lists=self.cklist(lists,len(classes),"lists")
        self.classes=classes
        self.seq=seq
    def add(self,ldsobject):
        if len(self.classes)==0:
            raise NotImplementedError(\
                "lds_base: error: class %s has not enabled registration" \
                % self.__class__.__name__)
        idx=self.isValidClass(ldsobject)
        d=self.dicts[idx]
        l=self.lists[idx]
        if d!=None:
            name=ldsobject.Name()
            d[name]=ldsobject
        if l!=None:
            l.append(ldsobject)
    def body(self,script,indent=""):
        # registers items with the class
        raise NotImplementedError(\
            "lds_base: error: class %s must provide method: body" \
            % (self.__class__.__name__))
    def cklist(self,lst,n,value):
        if len(lst)==0:
            l=[]
            for x in range(n):
                l.append(None)
            return l
        if len(lst)==1:
            l=[]
            entry=lst[0]
            for x in range(n):
                l.append(entry)
            return l
        if len(lst)!=n:
            raise IndexError(\
                "lds_base: error: %s must contain %s entries: %s" \
                % (value,n,len(lst)))
        return lst
    def isValidClass(self,instance):
        for x in range(len(self.classes)):
            cls=self.classes[x]
            if isinstance(instance,cls):
                return x
        raise TypeError(\
            "%s: error: class not authorized for registration: %s" \
             % (self.__class__.__name__,instance.__class__.__name__))
    def Name(self):
        # Return the name by which the instance is recognized
        try:
            return self.name
        except AttributeError:
            raise AttributeError("%s: error: can not be registerd by name"\
                % (self.__class__.__name__))
    def prefix(self,script,indent=""):
        return script
    def sequence(self):
        for x in self.seq:
            self.sequence_list(x)
    def sequence_list(self,lst):
        # Effectively an in place sort of the presented list
        sort_list=[]
        for x in range(len(lst)):
            entry=lst[x]     # entry being sorted
            cls_pos=self.classes.index(entry.__class__)  # where in class list
            sentry=sort(cls_pos,x,entry)
            sort_list.append(sentry)
        #sort_list.sort()
        new_list=sorted(sort_list,key=functools.cmp_to_key(sort.compare))
        for x in range(len(new_list)):
            lst[x]=sort_list[x].obj
        #return lst
    def suffix(self,script,indent=""):
        return script
            
class lds_script(lds_base):
    def __init__(self):
        self.cmdlist=[]
        lds_base.__init__(self,\
            classes=[lds_format,lds_arch,lds_target,lds_entry,lds_memory,\
                     lds_alias,lds_headers,lds_sections],\
            lists=[self.cmdlist],\
            seq=[self.cmdlist])
    def body(self,script,indent=""):
        for x in self.cmdlist:
            script=x.prefix(script)
            script=x.body(script)
            script=x.suffix(script)
            if not isinstance(script,type("")):
                raise TypeError(\
                    "%s body method did not return string" \
                    % x.__class__.__name__)
        return script
    def generate(self,script=""):
        self.sequence()
        script=self.prefix(script)
        script=self.body(script)
        script=self.suffix(script)
        return script

class lds_alias(lds_base):
    def __init__(self,alias,region):
        lds_base.__init__(self)
        self.name=alias
        self.region=region

class lds_align(lds_base):
    def __init__(self,alignment):
        lds_base.__init__(self)
        self.align=alignment
    def body(self,script,indent=""):
        return "%s%s. = ALIGN(%s) ;\n" % (script,indent,self.align)

class lds_arch(lds_base):
    def __init__(self,arch):
        lds_base.__init__(self)
        self.arch=arch
    def body(self,script,indent=""):
        return "%s%sOUTPUT_ARCH(%s)\n" % (script,indent,self.arch)

class lds_assign(lds_base):
    def __init__(self,lable,value="."):
        lds_base.__init__(self)
        self.lable=lable
        self.value=value
        self.name=self.lable
    def body(self,script,indent=""):
        return "%s%s%s = %s;\n" % (script,indent,self.lable,self.value)

class lds_entry(lds_base):
    def __init__(self,symbol):
        lds_base.__init__(self)
        self.symbol=symbol
    def body(self,script,indent=""):
        return "%s%sENTRY(%s)\n" % (script,indent,self.symbol)

class lds_format(lds_base):
    def __init__(self,default,big=None,little=None):
        lds_base.__init__(self)
        self.default=default
        self.big=None
        self.little=None
        if (big is None) and (little is None):
            return
        if (big is None) and (little!=None):
            print("lds_format: warning: required little missing, big ignored")
            return
        if (little is None) and (big!=None):
            print("lds_format: warning: required big missing, little ignored")
            return
        self.big=big
        self.little=little
    def body(self,script,indent=""):
        if (self.big!=None) and (self.little!=None):
            return "%s%sOUTPUT_FORMAT(%s, %s, %s)\n" \
                % (script,indent,self.default,self.big,self.little)
        return "%s%sOUTPUT_FORMAT(%s)\n" % (script,indent,self.default)
    def prefix(self,script,indent=""):
        return script
    def suffix(self,script,indent=""):
        return script

class lds_headers(lds_base):
    def __init__(self):
        self.phdrdict={}
        self.phdrlist=[]
        lds_base.__init__(self,\
            classes=[lds_phdr],\
            dicts=[self.phdrdict],\
            lists=[self.phdrlist])
    def body(self,script,indent=""):
        for x in self.phdrlist:
            script=x.body(script,indent="%s    " % indent)
        return script
    def prefix(self,script,indent=""):
        return "%s%sPHDRS\n{\n" % (script,indent)
    def suffix(self,script,indent=""):
        return "%s%s}\n\n" % (script,indent)

class lds_in(lds_base):
    def __init__(self,section):
        lds_base.__init__(self)
        self.section=section
    def body(self,script,indent=""):
        return "%s%s%s\n" % (script,indent,self.section)

class lds_memory(lds_base):
    def __init__(self):
        self.reglist=[]
        self.regdict={}
        lds_base.__init__(self,\
            classes=[lds_region],\
            dicts=[self.regdict],
            lists=[self.reglist])
    def body(self,script,indent=""):
        for x in self.reglist:
            script=x.body(script,indent="%s    " % indent)
        return script
    def prefix(self,script,indent=""):
        return "%s\n%sMEMORY\n{\n" % (script,indent)
    def suffix(self,script,indent=""):
        return "%s%s}\n\n" % (script,indent)
        
class lds_out(lds_base):
    types=["NOLOAD","DSECT","COPY","INFO","OVERLAY",None]
    constraints=["ONLY_IF_RO","ONLY_IF_RW",None]
    def __init__(self,name,address=None,type=None,at=None,align=None,\
                 subalign=None,constraint=None,region=None,atlma=None,\
                 phdr=None,fill=None):
        self.inlist=[]
        lds_base.__init__(self,\
            classes=[lds_align,lds_in,lds_provide],\
            dicts=[None],\
            lists=[self.inlist])
        self.name=name
        self.address=address
        if type in lds_out.types:
            self.typ=type
        else:
            print("lds_out: invalid type ignored: %s" % type)
            self.typ=None
        self.at=at
        self.align=align
        self.subalign=subalign
        if constraint in lds_out.constraints:
            self.constraint=constraint
        else:
            print("lds_out: invalid constraint ignored: %s" % constraint)
            self.constraint=None
        self.region=region
        self.atlma=atlma
        self.phdr=phdr
        self.fill=fill
    def body(self,script,indent=""):
        for x in self.inlist:
            script=x.body(script,indent="%s    " % indent)
        return script
    def prefix(self,script,indent=""):
        if self.address is None:
            addr=""
        else:
            addr="0x%X" % self.address
        if self.typ is None:
            typ=""
        else:
            typ=self.typ
        if self.at is None:
            at=""
        else:
            at="AT(0x%X)" % self.at
        if self.align is None:
            align=""
        else:
            align="ALIGN(%s)" % self.align
        if self.subalign is None:
            subalign=""
        else:
            subalign="SUBALIGN(%s)" % self.subalign
        if self.constraint is None:
            con=""
        else:
            con=self.constraint
        return "%s%s%s %s %s : %s %s %s %s\n%s{\n" \
            % (script,indent,self.name,addr,typ,at,align,subalign,con,indent)
    def suffix(self,script,indent=""):
        if self.region is None:
            reg=""
        else:
            reg=">%s" % self.region
        if self.atlma is None:
            atlma=""
        else:
            atlma="AT>%s" % self.atlma
        if self.phdr is None:
            phdr=""
        else:
            phdr=":%s" % self.phdr
        
        return "%s%s} %s %s %s\n\n" % (script,indent,reg,atlma,phdr)
        
class lds_phdr(lds_base):
    types={"PT_NULL":0,
           "PT_LOAD":1,
           "PT_DYNAMIC":2,
           "PT_INTERP":3,
           "PT_NOTE":4,
           "PT_SHLIB":5,
           "PT_PHDR":6}
    def __init__(self,name,type=None,at=None,flags=None,filehdr=False,phdrs=False):
        lds_base.__init__(self)
        self.name=name
        self.typ=type
        self.at=at
        self.filehdr=filehdr
        self.phdrs=phdrs
        self.flags=flags
    def body(self,script,indent=""):
        if self.typ is None:
            typ=""
        else:
            try:
                lds_phdr.types[self.typ]
                typ=self.typ
            except KeyError:
                typ="0x%08X" % self.typ
        if self.filehdr:
            filehdr="FILEHDR"
        else:
            filehdr=""
        if self.phdrs:
            phdrs="PHDRS"
        else:
            phdrs=""
        if self.at is None:
            at=""
        else:
            at="AT 0x%X" % self.at
        if self.flags is None:
            flags=""
        else:
            flags="FLAGS ( 0x%08X )" % self.flags
        return "%s%s%s %s %s %s %s %s ;\n" % \
            (script,indent,self.name,typ,filehdr,phdrs,at,flags)

class lds_provide(lds_base):
    def __init__(self,symbol):
        lds_base.__init__(self)
        self.symbol=symbol
    def body(self,script,indent=""):
        return "%s%sPROVIDE(%s = .);\n" % (script,indent,self.symbol)

class lds_region(lds_base):
    def __init__(self,name,origin,length,attr=None):
        lds_base.__init__(self)
        self.name=name
        self.origin=origin
        if attr is not None:
            for x in range(len(attr)):
                if attr[x] in "RrWwXxAaIiLl!":
                    continue
                print("lds_memory: warning: invalid attr: '%s'" % attr[x])
        self.attr=attr
        if length is not None and length<=0:
            print("lds_memory: warning: invalid length: %s" % length)
        self.length=length
    def body(self,script,indent=""):
        if self.attr is not None:
            attr=self.attr
        else:
            attr=""
        return "%s%s%s (%s) : ORIGIN = 0x%X, LENGTH = 0x%X\n" \
            % (script,indent,self.name,attr,self.origin,self.length)

class lds_sections(lds_base):
    def __init__(self):
        self.outdict={}
        self.outlist=[]
        lds_base.__init__(self,\
            classes=[lds_out,lds_assign],\
            dicts=[self.outdict],\
            lists=[self.outlist])
    def body(self,script,indent=""):
        for x in self.outlist:
            script=x.prefix(script,indent="%s    " % indent)
            script=x.body(script,indent="%s    " % indent)
            script=x.suffix(script,indent="%s    " % indent)
        return script
    def prefix(self,script,indent=""):
        return "%s%sSECTIONS\n{\n" % (script,indent)
    def suffix(self,script,indent=""):
        return "%s%s}\n\n" % (script,indent)

class lds_target(lds_base):
    def __init__(self,target):
        lds_base.__init__(self)
        self.target=target
    def body(self,script,indent=""):
        return "%s%sTARGET(%s)\n" % (script,indent,self.target)
            
class sort(object):
    # Utility class for sequencing output.  The staticmethod is used by the 
    # functools comp_to_key to create a key function usable by the sorted() built-in
    # function.  This is required for Version 3.
    @staticmethod
    def compare(a,b):
        return a.__cmp__(b)
        #if a.seq<b.seq:
        #    return -1
        #if a.seq>b.seq:
        #    return 1
        #if a.pos<b.pos:
        #    return -1
        #if a.pos>b.pos:
        #    return 1
        #return 0
    def __init__(self,seq,pos,obj):
        self.seq=seq
        self.pos=pos
        self.obj=obj
    def __cmp__(self,other):
        if self.seq<other.seq:
            return -1
        if self.seq>other.seq:
            return 1
        if self.pos<other.pos:
            return -1
        if self.pos>other.pos:
            return 1
        return 0

if __name__ == "__main__":
    raise NotImplementedError("lds_factory.py - must only be imported")