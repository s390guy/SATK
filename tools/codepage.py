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

# This module provides support for custom EBCDIC/ASCII code page translations.  The
# file interface is based upon the Statement-Oriented Parameter Language tool sopl.py
# found in the ${SATK_DIR}/tools/lang directory.  The tool also supports a string
#

# Python imports:
import argparse       # Access Python command line parser
import sys            # Access the Python system interface for exits.

# SATK imports:
if __name__ == "__main__":
    # Access the Statement-Oriented Parameter Language Tool Kit for local test
    import lang.sopl
    sopl=lang.sopl    # Make import look like its from the PYTHONPATH
else:
    # Access the Statement-Oriented Parameter Language Tool Kit from PYTHONPATH
    import sopl

this_module="codepage.py"
copyright="%s Copyright (C) %s Harold Grovesteen" % (this_module,"2014")

default=\
"""
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

# Default Code Page Definitions

characters EBCDIC-local
# Add your local EBCDIC characters here

characters ASCII-local
# Add your local ASCII characters here


characters ASCII-uppercase-letters
 a A 41
 a B 42
 a C 43
 a D 44
 a E 45
 a F 46
 a G 47
 a H 48
 a I 49
 a J 4A
 a K 4B
 a L 4C
 a M 4D
 a N 4E
 a O 4F
 a P 50
 a Q 51
 a R 52
 a S 53
 a T 54
 a U 55
 a V 56
 a W 57
 a X 58
 a Y 59
 a Z 5A

characters EBCDIC-uppercase-letters
 e A C1
 e B C2
 e C C3
 e D C4
 e E C5
 e F C6
 e G C7
 e H C8
 e I C9
 e J D1
 e K D2
 e L D3
 e M D4
 e N D5
 e O D6
 e P D7
 e Q D8
 e R D9
 e S E2
 e T E3
 e U E4
 e V E5
 e W E6
 e X E7
 e Y E8
 e Z E9

characters ASCII-lowercase-letters
 a a 61
 a b 62
 a c 63
 a d 64
 a e 65
 a f 66
 a g 67
 a h 68
 a i 69
 a j 6A
 a k 6B
 a l 6C
 a m 6D
 a n 6E
 a o 6F
 a p 70
 a q 71
 a r 72
 a s 73
 a t 74
 a u 75
 a v 76
 a w 77
 a x 78
 a y 79
 a z 7A

characters EBCDIC-lowercase-letters
 e a 81
 e b 82
 e c 83
 e d 84
 e e 85
 e f 86
 e g 87
 e h 88
 e i 89
 e j 91
 e k 92
 e l 93
 e m 94
 e n 95
 e o 96
 e p 97
 e q 98
 e r 99
 e s A2
 e t A3
 e u A4
 e v A5
 e w A6
 e x A7
 e y A8
 e z A9

characters ASCII-numbers
 a 0 30
 a 1 31
 a 2 32
 a 3 33
 a 4 34
 a 5 35
 a 6 36
 a 7 37
 a 8 38
 a 9 39

characters EBCDIC-numbers
 e 0 F0
 e 1 F1
 e 2 F2
 e 3 F3
 e 4 F4
 e 5 F5
 e 6 F6
 e 7 F7
 e 8 F8
 e 9 F9

characters ASCII-special
 a space 20
 a cent  A2
 a period 2E
 a lt  3C
 a lpar 28
 a plus 2B
 a vbar 7C
 a amp 26
 a xclam 21
 a dollar 24
 a asterisk 2A
 a rpar 29
 a semi 3B
 a splitvbar A6
 a not AA
 a minus 2D
 a slash 2F
 a comma 2C
 a percent 25
 a us 5F
 a gt 3E
 a quest 3F
 a colon 3A
 a numsign 23
 a atsign 40
 a ssq 27
 a eq 3D
 a sdq 22

characters EBCDIC-special
 e space 40
 e cent 4A
 e period 4B
 e lt  4C
 e lpar 4D
 e plus 4E
 e vbar 4F
 e amp  50
 e xclam 5A
 e dollar 5B 
 e asterisk 5C
 e rpar 5D
 e semi 5E
 e not  5F
 e minus 60
 e slash 61
 e comma 6B
 e percent 6C
 e splitvbar 6A
 e us 6D
 e gt 6E
 e quest 6F
 e colon 7A
 e numsign 7B
 e atsign 7C
 e ssq 7D
 e eq 7E
 e sdq 7F

codepage 94C-ASCII ASCII
 chars ASCII-uppercase-letters ASCII-lowercase-letters ASCII-numbers
 chars ASCII-special ASCII-local
codepage 94C-EBCDIC EBCDIC
 chars EBCDIC-uppercase-letters EBCDIC-lowercase-letters EBCDIC-numbers
 chars EBCDIC-special EBCDIC-local

# '94C' is a mapping of the 94 EBCDIC characters mapped to code page 00037 (USA/
# Canada - CECP (Country Extended Code Page), except for four characters: RSP
# (Required Space) - X'41', SHY (Soft Hyphen) - X'CA', NSP (Numeric Space) - X'E1', 
# and EO (Eight Ones) - X'FF'.  No ASCII or EBCDIC control characters are mapped.

translation 94C          # This is the default translation dumping only ASCII
 ascii 94C-ASCII
 ebcdic 94C-EBCDIC
 dumpa period ebcdic
 dumpe period ebcdic

translation 94Ca         # This is the default translation dumping only ASCII
 ascii 94C-ASCII
 ebcdic 94C-EBCDIC
 dumpa period ascii
 dumpe period ascii

translation 94Cea        # This is the default translation dumping both ASCII
 ascii 94C-ASCII         # and EBCDIC but dumping EBCDIC if a code point is also
 ebcdic 94C-EBCDIC       # used by ASCII
 dumpa period ebcdic merge
 dumpe period ebcdic merge

translation 94Cae        # This is the default translation dumping both ASCII
 ascii 94C-ASCII         # and EBCDIC but dumpint ASCII if a code point is also
 ebcdic 94C-EBCDIC       # used by EBCDIC
 dumpa period ascii merge
 dumpe period ascii merge

"""


#
#  +--------------------------+
#  |                          |
#  |   Code Page Definition   |
#  |                          | 
#  +--------------------------+
#

# codepage <codepgid>
#     chars <charid> [charid]...
class CodePage(object):
    def __init__(self,stmt,CP):
        self.name=stmt.ID
        self.chars={}       # Maps a code point name to its integer value
        self.cbytes={}      # Maps code point integer value to code point name

        if len(stmt.attr)!=1:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="codepage statement requires one attribute: %s" % len(stmt.attr[0]))
        cset=stmt.attr[0].upper()
        if cset not in ["ASCII","EBCDIC"]:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="codepage statement attribute unrecognized: '%s'" % cset)
        self.cset=cset

        for parm in stmt.parms:
            for s in parm.attr:
                try:
                    lsto=CP.clists[s]
                except KeyError:
                    raise sopl.SOPLError(loc=stmt.source,\
                        msg="codepage chars parameter character list undefiend: '%s'" \
                            % s)
                if cset=="ASCII":
                    lst=lsto.ascii
                else:
                    lst=lsto.ebcdic
                for point,cbyte in lst:
                    self.__char(point,cbyte,stmt.source)

    # Defines a code point name to a code point value.
    # Code point names and values must be unique
    def __char(self,point,cbyte,loc):
        if not isinstance(point,str):
            cls_str="codepage.py - %s.char() -" % self.__class__.__name__
            raise ValueError("%s 'point' argument must be a string: %s" \
                % (cls_str,point))
        if not isinstance(cbyte,int):
            cls_str="codepage.py - %s.char() -" % self.__class__.__name__
            raise ValueError("%s 'cbyte' argument must be an integer: %s" \
                % (cls_str,cbyte))
        try:
            self.chars[point]
            raise sopl.SOPLError(loc=loc,\
                msg="code point name must be unique: %s" % point)
        except KeyError:
            pass
        try:
            self.cbytes[cbyte]
            raise sopl.SOPLError(loc=loc,\
                msg="code point value must be unique: %s" % hex(cbyte))
        except KeyError:
            pass
        self.chars[point]=cbyte
        self.cbytes[cbyte]=point

    def point(self,pt):
        return self.chars[pt]

    def name(self,pt):
        return self.cbytes[pt]

# Define a list of characters and their respective single byte values
#
# characters <charid>
#     a <charname> <codepoint>      # Defines ascii characters
#     e <charname> <codepoint>      # Defines ebcdic characters
# Note: any number of a or e parameter lines are allowed
# The <codepoint> attribute is a hexadecimal value between 0x00 and 0xFF
class CLIST(object):
    def __init__(self,stmt,CP):
        self.ascii=[]
        self.ebcdic=[]

        self.name=stmt.ID

        for parm in stmt.parms:
            ptyp=parm.typ.upper()
            if len(parm.attr)!=2:
                raise sopl.SOPLError(loc=parm.source,\
                    msg="characters statement parameter requires two attributes: %s" \
                        % len(parm.attr))
            name=parm.attr[0]
            point=parm.attr[1]
            try:
                pvalue=int(point,16)
            except IndexError:
                raise sopl.SOPLError(loc=parm.source,\
                    msg="characters parameter code point not hexadecimal value: '%s'"
                        % point)
            if pvalue<0 or pvalue>255:
                raise sopl.SOPLError(loc=parm.source,\
                    msg="code point value out of range (0-255): '%s'" % pvalue)
            tup=(name,pvalue)
            if ptyp=="A":
                self.ascii.append(tup)
            elif ptyp=="E":
                self.ebcdic.append(tup)

# This object is used to map codepoints to assigned characters
class RTMap(object):
    def __init__(self,point):
        self.point=point
        self._ascii=None        # ASCII TMap object
        self._ebcdic=None       # EBCDIC TMap object

    def __str__(self):
        string="point: %02X" % self.point
        string="%s\n  %s" % (string,self._ascii)
        string="%s\n  %s" % (string,self._ebcdic)
        return string

    # Return the ASCII character name assigned to this code point or an empty string
    def ascii(self):
        if self._ascii is None:
            return ""
        return self._ascii.name

    # Perform the selection for mappint this code point to a dump character
    # Method Arguments:
    #   select   A string identifying the selection criteria
    #              'MEA'  - ASCII & EBCDIC, EBCDIC primary to ASCII
    #              ' EA'  - EBCDIC only to ASCII
    #              'MAA'  - ASCII & EBCDIC, ASCII primary to ASCII
    #              ' AA'  - ASCII only to ASCII
    #              'MEE'  - ASCII & EBCDIC, EBCDIC primary to EBCDIC
    #              ' EE'  - EBCIDC only to EBCDIC
    #              'MAE'  - ASCII & EBCDIC, ASCII primary to EBCDIC
    #              ' AE'  - ASCII only to EBCDIC
    def dump(self,select):
        ascii=self._ascii
        ebcdic=self._ebcdic

        if select=="MEA":                          # Merging, EBCDIC primary -> ASCII
            if ebcdic is not None:
                return ebcdic.ascii
            if ascii is not None:
                return ascii.ascii
        elif select==" EA" and ebcdic is not None: # Select only EBCDIC -> ASCII
            if ebcdic is not None:
                return ebcdic.ascii
        elif select=="MAA":                        # Merging, ASCII primary -> ASCII
            if ascii is not None:
                return ascii.ascii
            if ebcdic is not None:
                return ebcdic.ascii
        elif select==" AA" and ascii is not None:  # Select only ASCII -> ASCII
            if ascii is not None:
                return ascii.ascii
        elif select=="MEE":                        # Merging, EBCDIC primary -> EBCDIC
            if ebcdic is not None:
                return ebcdic.ebcdic
            if ascii is not None:
                return ascii.ebcdic
        elif select==" EE":                        # Select only EBCDIC -> EBCDIC
            if ebcdic is not None:
                return ebcdic.ebcdic
        elif select=="MAE":                        # Merging, ASCII primary -> EBCDIC
            if ascii is not None:
                return ascii.ebcdic
            if ebcdic is not None:
                return ebcdic.ebcdic
        elif select==" AE":                        # Select only ASCII -> EBCDIC
            if ascii is not None:
                return ascii.ebcdic
        else:
            return None

    # Return the EBCDIC character assigned to this code point or an empty string
    def ebcdic(self):
        if self._ebcdic is None:
            return ""
        return self._ebcdic.name

# This object is used by the Translation object in displaying translation mappings
class TMap(object):
    def __init__(self,name):
        self.name=name
        self.ascii=None        # ASCII code point assigned to this character name
        self.ebcdic=None       # EBCDIC code point assigned to this character name
    def __str__(self):
        ebcdic=ascii="None"
        if self.ascii is not None:
            ascii="%02X" % self.ascii
        if self.ebcdic is not None:
            ebcdic="%02X" % self.ebcdic
        return "TMap %s: ASCII=%s, EBCDIC=%s" % (self.name,ascii,ebcdic)

# This object is used to define binary translation options
class BinDump(object):
    def __init__(self,fill,output,primary,limit,merge=False):
        self.fillchar=fill     # Name of the "fill" character
        self.output=output     # Output code set: ASCII or EBCDIC
        self.primary=primary   # Primary translation of: ASCII or EBCDIC
        self.merge=merge       # If True both primary and secondary being interpreted
        self.ctl_limit=limit   # Control character limit
        
        # These attributes are established by the select() method
        self._select=None       # Selection "code"
        self._fill=None         # fill char code assignment
        
    def __str__(self):
        string="BinDump fill: %s output:%s primary:%s limit:%02X merge:%s" \
             % (self.fillchar,self.output,self.primary,self.ctl_limit,self.merge)
        if self._select is not None:
            string="%s select:%s" % (string,self._select)
        if self._fill is not None:
            string="%s fill:%02X" % (string,self._fill)
        return string

    def select(self,asciicp,ebcdiccp):
        if self.output=="ASCII":
            output="A"
            try:
                self._fill=asciicp.point(self.fillchar)
            except KeyError:
                self._fill=0x2E   # ASCII period
        else:
            output="E"
            try:
                self._fill=ebcdiccp.point(self.fillchar)
            except KeyError:
                self._fill=0x4B   # EBCDIC period
        
        if self.primary=="ASCII":
            primary="A"
        else:
            primary="E"
            
        if self.merge:
            merge="M"
        else:
            merge=" "
            
        self._select="%s%s%s" % (merge,primary,output)
        
        

# Define the ASCII and EBCDIC code pages to be translated.  Only characters with the
# same names will be translated between the two code pages.  Code points that are
# not defined in both code pages will not be translated if encountered.  All
# parameter lines are required.
#
# translation <transid>           # Define the translation ID
#     ascii  <codepgid>           # Codepage ID of the set of ASCII characters
#     ebcdic <codepgid>           # Codepage ID of the set of EBCDIC characters
#
#
# The dump parameter line identifies how binary data will be interpreted.
# The <charid> is the ASCII character used for undefined code points.  The 'ascii' or
# 'ebcdic' attribute identifies the primary codepage used to translate binary data.
# The optional 'merge' attribute indicates that codepoints not defined by the primary
# codepage will use the secondary codepage for codepoint character interpretation.
#     dump   <charid> <ascii|ebcdic> [merge]
class Translation(object):
    def __init__(self,stmt,CP):
        self.name=stmt.ID     # Translation ID
        self.ascii_parm=None  # ascii parameter Parm object
        self.ebcdic_parm=None # ebcdic parameter Parm object
        self.dumpa_parm=None  # dumpa parameter Parm object
        self.dumpe_parm=None  # dumpe parmeter Parm object
        self.cp=CP            # CODEPAGE object

        # ascii parameter values
        self.ascii=None       # ASCII code page name
        self.asciicp=None     # ASCII CodePage object

        # ebcdic parameter values
        self.ebcdic=None      # EBCDIC code page name
        self.ebcdiccp=None    # EBCDIC CodePage object

        # Dump parameter values
        self.dumpa=None
        self.dumpe=None

        # Attributes used by display() method and built by __tmap() method
        self.tmaps={}         # TMap objects are stored here by character id
        self.rtmaps={}        # Reverse TMaps are stored here
        self.max_char=0       # Maximum length of character names

        for parm in stmt.parms:
            parmid=parm.typ
            if parmid=="ascii":
                if len(parm.attr)!=1:
                    raise sopl.SOPLError(loc=parm.source,\
                        msg="translation %s parameter requires one attribute: %s" \
                            % (parmid,len(parm.attr)))
                self.ascii_parm=parm
                self.ascii,self.asciicp=self.__find_codepage(parm,CP)
            elif parmid=="ebcdic":
                if len(parm.attr)!=1:
                    raise sopl.SOPLError(loc=parm.source,\
                        msg="translation %s parameter requires one attribute: %s" \
                            % (parmid,len(parm.attr)))
                self.ebcdic_parm=parm
                self.ebcdic,self.ebcdiccp=self.__find_codepage(parm,CP)
            elif parmid=="dumpa":
                self.dumpa_parm=parm
                self.dumpa=self.__process_dump(parm,"ASCII",0x20)
            elif parmid=="dumpe":
                self.dumpe_parm=parm
                self.dumpe=self.__process_dump(parm,"EBCDIC",0x40)
            else:
                cls_str="codepage.py - %s.__init__() -" % self.__class__.__name__
                raise ValueError("%s unexpected parameter ID: %s" % (cls_str,parm.ID))

        # Make sure all of the translation parameters have been specified
        if self.ascii is None:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="translation statement required ascii parameter missing")
        if self.ebcdic is None:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="translation statement required ebcdic parameter missing")
        if self.dumpa is None:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="translation statement required dumpa parameter missing")
        if self.dumpe is None:
            raise sopl.SOPLError(loc=stmt.source,\
                msg="translation statement required dumpa parameter missing")
        
        self.dumpa.select(self.asciicp,self.ebcdiccp)
        self.dumpe.select(self.asciicp,self.ebcdiccp)

    # Finds the CodePage object in an ebcdic or ascii parameter line
    def __find_codepage(self,parm,typ):
        cp=parm.attr[0]
        try:
            return (cp,self.cp.codepages[cp])
        except KeyError:
            raise sopl.SOPLError(loc=parm.source,\
                msg="translation %s parameter code page undefined: '%s'"\
                    % (parm.ID,cp))

    def __dump_to(self,bindump):
        tbl=TransTable()
        fill=bindump._fill
        for n in range(256):
            tbl.mapping(n,fill)

        select=bindump._select
        limit=bindump.ctl_limit

        for rtmap in self.rtmaps.values():
            dump=rtmap.dump(select)
            if dump is None:
                continue
            # Replace any selected dump character that is format disrupting, for
            # example, a carriage return or line feed, or not printable with the 
            # fill character.
            if dump < limit:
                dump=fill
            point=rtmap.point
            tbl.mapping(point,dump)

        tbl.table()  # Finish the translation table
        return tbl

    # Create a TransTable object
    # Method Arguments
    #   ebcdic   Specify True if translation if from EBCDIC to ASCII.
    #            Specify False if translation is from ASCII to EBCDIC
    def __from_to(self,ebcdic=False):
        tbl=TransTable()
        for t in self.tmaps.values():
            if t.ascii is None or t.ebcdic is None:
                continue
            if ebcdic:
                tbl.mapping(t.ebcdic,t.ascii)
            else:
                tbl.mapping(t.ascii,t.ebcdic)
        tbl.table()
        return tbl

    # Analyze a dump statement's parameter lines
    def __process_dump(self,parm,output,limit):
        attr=parm.attr
        attrs=len(attr)
        if attrs <2 or attrs> 3:
            raise sopl.SOPLError(loc=parm.source,\
                msg="translation statement %s parameter requires 2 or 3 "
                    "attributes: %s" % (parm.typ,attrs))
        fillchar=attr[0]
        primary=attr[1]
        merge=False
        if attrs==3:
            if attr[2]=="merge":
                merge=True
            else:
                raise sopl.SOPLError(loc=parm.source,\
                    msg="translation statement %s parameter unrecognized: '%s'" \
                        % (parm.typ,attr[2]))
        dump=BinDump(fillchar,output,primary.upper(),limit,merge=merge)
        return dump

    # Builds the reverse TMap dictionary form regular TMap
    def __rtmap(self):
        rtmaps=self.rtmaps
        for tmap in self.tmaps.values():
            ascii=tmap.ascii
            ebcdic=tmap.ebcdic
            if ascii is not None:
                point=tmap.ascii
                try:
                    rtmap=rtmaps[point]
                    rtmap._ascii=tmap
                except KeyError:
                    rtmap=RTMap(point)
                    rtmap._ascii=tmap
                rtmaps[point]=rtmap
            if ebcdic is not None:
                point=tmap.ebcdic
                try:
                    rtmap=rtmaps[point]
                    rtmap._ebcdic=tmap
                except KeyError:
                    rtmap=RTMap(point)
                    rtmap._ebcdic=tmap
                rtmaps[point]=rtmap
        self.rtmaps=rtmaps

    # Builds the TMap dictionary from a code page
    def __tmap(self,codepage,ebcdic=False):
        maximum=self.max_char
        tmaps=self.tmaps
        for charname,codepoint in codepage.chars.items():
            maximum=max(maximum,len(charname))
            try:
                tmap=tmaps[charname]
            except KeyError:
                tmap=TMap(charname)
            if ebcdic:
                tmap.ebcdic=codepoint
            else:
                tmap.ascii=codepoint
            tmaps[charname]=tmap
        self.max_char=maximum

    # Prints the ASCII and EBCDIC code page data
    def pages(self):
        print("Translation id: %s" % self.name)
        print("  total characters: %s" % len(self.tmaps))
        max_char=self.max_char
        print("    %s  EBCDIC  ASCII  CHAR" % "NAME".ljust(max_char))
        chars=[]
        for c in self.tmaps.keys():
            chars.append(c)
        chars.sort()
        fill=" ".center(6)
        for char in chars:
            tmap=self.tmaps[char]
            name=tmap.name.ljust(max_char)

            # Format EBCDIC code point
            ebcdic=tmap.ebcdic
            if ebcdic is None:
                ebcdic=fill
            else:
                ebcdic="0x%02X" % ebcdic
                ebcdic=ebcdic.center(6)

            # Format ASCII code point
            ascii=tmap.ascii
            if ascii is None:
                ascii=fill
                rep=""
            else:
                codept=ascii
                ascii="0x%02X" % ascii
                ascii=ascii.center(6)
                rep="  %s" % chr(codept).__repr__()
            print("    %s  %s  %s%s" % (name,ebcdic,ascii,rep))

    # Displays code point usage
    def points(self):
        print("Translation id: %s" % self.name)
        print("  total code points: %s" % len(self.rtmaps))
        max_char=self.max_char
        e_chars=max(max_char,6)+2
        a_chars=max(max_char,5)+2
        acol="ASCII".ljust(a_chars)
        ecol="EBCDIC".ljust(e_chars)
        print("    POINT  %s%s" % (acol,ecol))
        for point in self.rtmaps.values():
            pt="%02X" % point.point
            pt=pt.center(5)
            ascii=point.ascii().ljust(a_chars)
            ebcdic=point.ebcdic().ljust(e_chars)
            line="    %s  %s%s" % (pt,ascii,ebcdic)
            line=line.rstrip()
            print(line)

    # Returns a Translator object as specified by this Translation object 
    def translator(self):
        self.__tmap(self.asciicp,ebcdic=False)
        self.__tmap(self.ebcdiccp,ebcdic=True)
        self.__rtmap()

        a2e=self.__from_to(ebcdic=False)
        e2a=self.__from_to(ebcdic=True)
        dumpa=self.__dump_to(self.dumpa)
        dumpe=self.__dump_to(self.dumpe)
        return Translator(a2e,e2a,dumpa,dumpe)


class Translator(object):
    def __init__(self,a2e,e2a,dumpa,dumpe):
        self._a2e=a2e     # TransTable object for ASCII-to-EBCDIC
        self._e2a=e2a     # TransTable object for EBCDIC-to-ASCII
        self._dumpa=dumpa   # TransTable object for binary interpretation into ASCII
        self._dumpe=dumpe   # TransTable object for binary interpretation into EBCDIC

    # Translate ASCII string to EBCDIC string
    def a2e(self,string):
        return self._a2e.translate(string)
    # Translate ASCII bytes list to EBCDIC bytes list
    def a2eb(self,b):
        return self._a2e.translateb(b)
    # Translate ASCII bytesarray to EBCDIC bytesarray
    def a2eba(self,ba):
        return self._a2e.translateba(ba)
    # Translate EBCDIC string to ASCII string
    def e2a(self,string):
        return self._e2a.translate(string)
    # Translate EBCDIC bytes list to ASCII bytes list
    def e2ab(self,b):
        return self._e2a.translateb(b)
    # Translate EBCDIC bytesarray, bytes list or integer list to an ASCII bytesarray
    def e2aba(self,ba):
        return self._e2a.translateba(ba)
    # Do binary interpretation of a string, bytes list, integer list  or bytesarray 
    # into an ASCII string
    def dumpa(self,string):
        return self._dumpa.translate_s(string)
    # Do binary interpretation of a string, bytes list, integer list  or bytesarray 
    # into an EBCDIC string 
        return self._dumpe.translate_s(string)

# Helper class for translation tables
class TransTable(object):
    def __init__(self):
        self._bytes=bytearray(range(256))
        self._table=None

    # Defines a mapping from a source code point value to another
    def mapping(self,frm,to):
        self._bytes[frm]=to

    # Completes the table from the defined mappings.
    def table(self):
        c=[]
        for v in self._bytes:
            c.append(chr(v))
        self._table="".join(c)
        self._bytes=bytes(self._bytes)

    # Translate a string into another string
    def translate(self,string):
        return string.translate(self._table)

    # Translate a bytes list or integer list to a bytes list
    def translate_b(self,b,string=False):
        to=[]
        tbl=self._bytes
        for v in b:
            to.append(tbl[v])  
        return bytes(to)

    # Translate a bytes list or bytesarray or integer list to a bytesarray
    def translate_ba(self,b):
        to=[]
        tbl=self._bytes
        for v in b:
            to.append(tbl[v])
        return bytesarray(to)

    # Translate a string or integer based sequence into a string
    def translate_s(self,string):
        if isinstance(string,str):
            return string.translate(self._table)
        # This is a different seqeence.
        to=[]
        tbl=self._table
        for v in string:
            to.append(tbl[v])
        return "".join(to)


#
#  +------------------------+
#  |                        |
#  |   Code Page Tool Kit   |
#  |                        | 
#  +------------------------+
#

# This is the primary interface to the tool kit.  
class CODEPAGE(sopl.SOPL):
    def __init__(self):
        self.clists={}
        self.codepages={}
        self.translations={}

        self.my_statements=\
            {"characters":(CLIST,self.clists),
             "codepage":(CodePage,self.codepages),
             "translation":(Translation,self.translations)}

        super().__init__(variable="CDPGPATH",debug=False)

    def __process(self):
        for s in self.getStmts():
            typ=s.typ
            try:
                cls,d=self.my_statements[typ]
            except KeyError:
                cls_str="codepage.py - %s.__process() -" % self.__class__.__name__
                raise ValueError("%s unrsupported statement ID: %s" % (cls_str,typ))\
                    from None
            obj=cls(s,self)
            d[obj.name]=obj

     # Raises a KeyError if translation is not defined
    def __translator(self,name=None):
        if name is None:
            trans="default"
        else:
            trans=name
        t=self.translations[name]
        return t.translator()

    def build(self,trans="94C",filename=None,fail=False):
        if filename is None:
            self.multiline(default,fail=fail)
        else:
            self.recognize(filename,fail=fail)
        self.__process()
        try:
            return self.__translator(name=trans)
        except KeyError:
            raise sopl.SOPLError(msg="requested translation not defined: '%s'" \
                % trans) from None

    def bytes2str(self,blist):
        c=[]
        for b in blist:
            c.append(chr(b))
        return bytes(c)

    def register(self):
        self.regStmt("characters",parms=["a","e"])
        self.regStmt("codepage",parms=["chars",])
        self.regStmt("translation",parms=["ebcdic","ascii","dumpa","dumpe"])

    def str2bytes(self,string):
        b=[]
        for n in range(len(string)):
            b.append(ord(string[n]))
        return bytes(b)

    def translation(self,name):
        return self.translations[name]

#
#  +-------------------------------------------------------+
#  |                                                       |
#  |   Command Line Interface for the Code Page Tool Kit   |
#  |                                                       | 
#  +-------------------------------------------------------+
#

class CDPGIF(object):
    def __init__(self,args):
        self.args=args           # command line argument information

        # Code page source file (None if not provided)
        self.source=args.cpfile
        # Code page translation ID ('default' if not provided)
        self.trans=args.cptrans

        # Output options
        self.a2e=args.a2e            # Display ASCII-to-EBCDIC translation table
        self.pages=args.codepages    # Display the codepages
        self.dumpa=args.dumpa        # Display Dump translation table to ASCII
        self.dumpe=args.dumpe        # Display Dump translation table to EBCDIC
        self.e2a=args.e2a            # Display EBCDIC-to-ASCII translation table
        self.points=args.codepoints  # Display code point usage
        
        # Test option
        self.test=args.test          # Test string if not 'none'
        
        # Write file option
        self.write=args.write        # Output the definitions as a file

        # Established by main() method
        self.cp=None             # The CODEPAGE object managing code pages
        self.translator=None     # Resultant Translator object from manager

        # Used by __trans_table() method when displaying a translation table
        heading="    "
        for c in "0123456789ABCDEF":
            column="_%s" % c
            heading="%s %s" % (heading,column.center(2))
        self.heading=heading

    def __trans_table(self,tbl):
        print(self.heading)
        for x in range(16):
            x_start="%X_" % x
            x_start=x_start.center(4)
            row=x_start
            row_start=x*16
            for y in range(16):
                ndx=row_start+y
                col=ord(tbl[ndx])
                char="%02X" % col
                row="%s %s" % (row,char)
            print(row)

    # Main entry point for command line processing
    def main(self):
        self.cp=CODEPAGE()       # Create the code page manager
        # Build the Translator object
        try:
            self.translator=self.cp.build(trans=self.trans,filename=self.source)
        except sopl.SOPLError as se:
            self.cp._do_error(error=se)

        if self.cp.isErrors():
            self.cp.printWarnings()
            self.cp.printErrors()
            sys.exit(1)

        translation=self.cp.translation(self.trans)

        if self.pages:
            translation.pages()

        if self.points:
            translation.points()

        if self.a2e:
            print("\n%s ASCII to EBCDIC Translation Table" % self.trans)
            self.__trans_table(self.translator._a2e._table)

        if self.e2a:
            print("\n%s EBCDIC to ASCII Translation Table" % self.trans)
            self.__trans_table(self.translator._e2a._table)

        if self.dumpa:
            print("\n%s Dump Binary to Character Interpretation Table to ASCII" \
                % self.trans)
            self.__trans_table(self.translator._dumpa._table)

        if self.dumpe:
            print("\n%s Dump Binary to Character Interpretation Table to EBCDIC" \
                % self.trans)
            self.__trans_table(self.translator._dumpe._table)

        if self.test is not None:
            self.self_test()
            
        if self.write is not None:
            self.write_codepages()

    def self_test(self):
        string=self.test
        print("Test ASCII string: %s" % string.__repr__())
        ebcdic=self.translator.a2e(string)
        h=""
        for c in ebcdic:
            h="%s\\x%02x" % (h,ord(c))
        print("Test string translated to EBCDIC: '%s'" % h)
        dump=self.translator.dump(ebcdic)
        print("EBCDIC string dumped: %s" % dump.__repr__())
        
    def write_codepages(self):
        fo=open(self.write,"wt")
        fo.write(default)
        fo.close()
        print("code page file successfully written: %s" % self.write)
        

# Parse the command line arguments
def parse_args():
    parser=argparse.ArgumentParser(prog="codepage.py",
        epilog=copyright, 
        description="Manages ASCII and EBCDIC code pages")

    # Swith to print ASCII-to-EBCDIC translation table
    parser.add_argument("-a","--a2e",default=False,action="store_true",\
        help="display ASCII-to-EBCDIC translation table")

    # Switch to print out code pages from the translation ID
    parser.add_argument("-c","--codepages",default=False,action="store_true",\
        help="display the code page information by character ID's")

    # Swith to print EBCDIC-to-ASCII translation table
    parser.add_argument("-e","--e2a",default=False,action="store_true",\
        help="display EBCDIC-to-ASCII translation table")

    # Swith to print code point usage for ASCII and EBCDIC
    parser.add_argument("-p","--codepoints",default=False,action="store_true",\
        help="display EBCDIC-to-ASCII translation table")

    # Source input file
    parser.add_argument("--cpfile",\
        help="input code page source file in CDPGPATH environment search path")

    # Translation ID in input file or built-in definition
    parser.add_argument("--cptrans",default="94C",\
        help="code page ASCII/EBCDIC translation ID (default is '94C')")

    # Switch to print binary character interpretation table in ASCII dumps
    parser.add_argument("--dumpa",default=False,action="store_true",\
        help="display the ASCII dump character interpretation table")

    # Switch to print binary character interpretation table in EBCDIC dumps
    parser.add_argument("--dumpe",default=False,action="store_true",\
        help="display the EBCDIC dump character interpretation table")

    # Runs the supplied translation tests on a supplied string
    parser.add_argument("--test",\
        help="perform a simple sanity test with supplied string")

    # Write the default code page definition to a file
    parser.add_argument("--write",\
        help="output as a text file the supplied translation definitions")

    return parser.parse_args()


if __name__ == "__main__":
    cp=CDPGIF(args=parse_args())
    print(copyright)
    cp.main()
