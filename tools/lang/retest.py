#!/usr/bin/python3.3
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

# SATK language tools are heavily dependent upon Python regular expressions.  This
# module is intended strictly for experimentation of regular expressions and the
# results of regular expressions matched against or recognized within a test string.
#
# The module is standalone and has no dependencies upon SATK so it useful in other
# contexts.  Additionaly the functions print_mo(), print_re(), print_re_flags()
# may be imported in providing debugging information for regular expression operations

this_module="retest.py"

# Python imports:
import re          # Provides access to the Python re module.

def print_mo(mo,indent=""):
    local="%s    " % indent
    local_indent="%s    " % local
    print("%smo: %s" % (indent,mo))
    print("%sre:              %s" % (local,mo.re))
    print("%sin string:       %s" % (local,mo.string.__repr__()))
    print("%sin pos:          %s" % (local,mo.pos))
    print("%sin endpos:       %s" % (local,mo.endpos))
   
    # Print the match information for the entire string
    match=mo.group(0)
    start=mo.start(0)
    end=mo.end(0)
    print("%sout match [%s:%s]: %s" % (local,start,end,match.__repr__()))
    
    # Print the match information for each group (if any)
    grps=list(mo.groups())
    # The groups() method returns a tuple.  We turn it into a list here.
    if len(grps)==0:
        print("%sout groups(): %s" % (local,grps))
    else:
        print("%sout groups():" % local)
        for n in range(len(grps)):
            grp=grps[n]
            # Note that to locate where the group is located in the string,
            # the value is increased by one.  This is because the start() and end()
            # methods use 0 for the entire match.  However, the groups() method
            # only returns the matched groups.  See above when printing the match.
            start=mo.start(n+1)
            end=mo.end(n+1)
            print("%s[%s] [%s:%s] %s" % (local_indent,n,start,end,grp.__repr__()))
            
    # Print the group dictionary entries (if any)
    grpdict=mo.groupdict()
    if len(grpdict)==0:
        print("%sout groupdict(): %s" % (local,grpdict))
    else:
        print("%sout groupdict():" % local)
        for key,val in grpdict.items():
            print("%s%s: %s" % (local_indent,key,val.__repr__()))

def print_re(rec,indent=""):
    local="%s    " % indent
    local_indent="%s    " % local
    print("re: %s" % rec)
    print("%sflags: %s" % (local,rec.flags))
    if rec.flags!=0:
        print_re_flags(flags=rec.flags,indent=local_indent)
    if len(rec.groupindex)==0:
        print("%sgroupindex: %s" % (local,rec.groupindex))
    else:
        print("%sgroupindex:" % local)
        for key,val in rec.groupindex.items():
            print("%s%s: %s" % (local_indent,key,val))
    print("%spattern: %s" % (local,rec.pattern.__repr__()))

def print_re_flags(flags=None,indent=""):
    if flags is None:
        print("%sre.IGNORECASE: %s" % (indent,re.IGNORECASE))
        print("%sre.LOCALE:     %s" % (indent,re.LOCALE))
        print("%sre.MULTILINE:  %s" % (indent,re.MULTILINE))
        print("%sre.DOTALL:     %s" % (indent,re.DOTALL))
        print("%sre.UNICODE:    %s" % (indent,re.UNICODE))
        print("%sre.VERBOSE:    %s" % (indent,re.VERBOSE))
        print("%sre.ASCII:      %s" % (indent,re.ASCII))
        return
    f=flags
    if f >= re.ASCII:
        print("%sre.ASCII:      %s" % (indent,re.ASCII))
        f-=re.ASCII
        if f==0:
            return
    if f >= re.VERBOSE:
        print("%sre.VERBOSE:    %s" % (indent,re.VERBOSE))
        f-=re.ASCII
        if f==0:
            return
    if f >= re.UNICODE:
        print("%sre.UNICODE:    %s" % (indent,re.UNICODE))
        f-=re.UNICODE
        if f==0:
            return
    if f >= re.DOTALL:
        print("%sre.DOTALL:     %s" % (indent,re.DOTALL))
        f-=re.UNICODE
        if f==0:
            return
    if f >= re.MULTILINE:
        print("%sre.MULTILINE:  %s" % (indent,re.MULTILINE))
        f-=re.MULTILINE
        if f==0:
            return
    if f >= re.LOCALE:
        print("%sre.LOCALE:     %s" % (indent,re.LOCALE))
        f-=re.MULTILINE
        if f==0:
            return
    if f >= re.IGNORECASE:
        print("%sre.IGNORECASE: %s" % (indent,re.IGNORECASE))
        f-=re.IGNORECASE
        if f==0:
            return
    print("%sunexpected flag(s) encountered: %s" (indent,f))

class retest(object):
    def __init__(self,pattern):
        self.rec=None
        try:
            self.rec=re.compile(pattern)
        except Exception as ex:
            print("regular expression pattern compilation failed: %s" % pattern)
            print("   exception class: %s" % ex.__class__.__name__)
            print("   exception: %s" % ex)
        print_re(self.rec)
        
    def match(self,string):
        string_msg="%s" % string.__repr__()
        self.mo=None
        try:
            mo=self.rec.match(string)
        except Exception as ex:
            print("pattern match failed for: %s" % string_msg)
            print("   exception class: %s" % ex.__class__.__name__)
            print("   exception: %s" % ex)
            return

        if mo is None:
            print("no match object returned for: %s" % string_msg)
            return
        print_mo(mo)

if __name__ == "__main__":
    # Code tests here under this 'if' statement
    #print_re_flags()
    #reif=retest("(?P<A>.)?(?P<B>.)?")
    #reif.match("")
    #reif.match("AB")

    #res=retest("('[^']*')+")
    #res.match("''")
    #res.match("''''")
    #res.match("'abc'")
    #res.match("'abc''def'")

    #sdchr=retest("([Cc][EeAa]?)(''''|'[^']')")
    #sdchr.match("C'a'")
    #sdchr.match("C''''")
    
    #pattern="([%s]')?([%s][%s0-9]*)" % ("KkNn","A-Za-z","A-Za-z")
    #lattr=retest(pattern)
    #lattr.match("Alabel")
    #lattr.match("K'Alabel")
    #lattr.match("N'Alable")
    #lattr.match("A'Alable")
    #lattr.match("K'")
    
    pattern="('[^']*')+"
    ctest=retest(pattern)
    ctest.match("'this is a quoted string'")
    ctest.match("''")
    ctest.match("'a field''s value'other stuff")
    

    