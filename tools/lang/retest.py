#!/usr/bin/python3
# Copyright (C) 2014, 2016, 2017 Harold Grovesteen
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
# The module is standalone and has no dependencies upon SATK so it is useful in other
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

# Simple object that compiles and performs a match of an regular expression.
class retest(object):
    def __init__(self,pattern,debug=False):
        self.debug=debug       # Whether debug messages are generated
        self.rec=None          # Compiles re object
        try:
            self.rec=re.compile(pattern)
        except Exception as ex:
            msg="regular expression pattern compilation failed: %s" % pattern
            msg="%s\n   exception class: %s" % (msg,ex.__class__.__name__)
            msg="%s\n   exception: %s" % (msg,ex)
            raise ValueError(msg) from None

        if __debug__:
            if self.debug:
                print_re(self.rec)
        
    # Perform a match using the object's compiled regular expression object.
    # If debugging is enabled, details of the result will be printed.
    #
    # Returns:
    #   match object if match is successful
    #   None if match failed.
    def match(self,string):
        string_msg="%s" % string.__repr__()
        self.mo=None
        try:
            mo=self.rec.match(string)
        except Exception as ex:
            msg="pattern match failed for: %s" % string_msg
            msg="%s\n   exception class: %s" % (msg,ex.__class__.__name__)
            msg="%s\n   exception: %s" % (msg,ex)
            if __debug__:
                if self.debug:
                    print(msg)
            return

        if __debug__:
            if self.debug:
                if mo is None:
                    print("no match object returned for: %s" % string_msg)
                else:
                    print_mo(mo)
        return mo

if __name__ == "__main__":
    debug=True

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

    #pattern="('[^']*')+"
    #ctest=retest(pattern,debug=debug)
    #ctest.match("'this is a quoted string'")
    #ctest.match("''")
    #ctest.match("'a field''s value'other stuff")

    #inf="[Ii] *[Nn] *[Ff] *"
    #nan="[QqSs]? *[Nn] *[Aa] *[Nn] *"
    #mx="[Mm] *[Aa] *[Xx] *"
    #mn="[Dd]? *[Mm] *[Ii] *[Nn] *"
    #pattern="(?P<sign>[ +-]+)?(?P<spec>\( *(%s|%s|%s|%s)\) *)" % (inf,nan,mx,mn)
    #ftest=retest(pattern,debug=debug)
    #ftest.match("- + ( i n f )'")
    #ftest.match("(nan)")
    #ftest.match("-(max)")
    #ftest.match(" ( d m i n )'")

    #'(?P<sign>[ +-]+)?(?P<spec>\\( *([Ii] *[Nn] *[Ff] *|[QqSs]? *[Nn] *[Aa] *[Nn] *|[Mm] *[Aa] *[Xx] *|[Dd]? *[Mm] *[Ii] *[Nn] *)\\) *)'
    # ASMA
    #'(?P<sign>[ +-]+)?(?P<spec>\\( *([Ii] *[Nn] *[Ff] *|[QqSs]? *[Nn] *[Aa] *[Nn] *|[Mm] *[Aa] *[Xx] *|[Dd]? *[Mm] *[Ii] *[Nn] *)\\) *)'
    
    #char="\$@\#_"
    #pattern="[a-zA-Z%s][a-zA-Z0-9%s]*" % (char,char)
    #test=retest(pattern,debug=debug)
    #test.match("svc#old")
    
    #pat="&?%s" % pattern
    #test=retest(pat,debug=debug)
    #test.match("&GA")

    pattern="(\$\{)([_A-Za-z]+)(\})"
    test=retest(pattern,debug=debug)
    test.match("${PATH}")
    test.match("${}")
    

    