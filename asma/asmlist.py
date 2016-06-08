#!/usr/bin/python3
# Copyright (C) 2014-2016 Harold Grovesteen
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

# This module generates the output listing for ASMA.

this_module="asmlist.py"

# Python imports: none
# SATK imports:
from listing import *      # Access the listing generator tools
from satkutil import byte2str   # Function that converts bytes to a string
from translate import E2A  # Character translation table

# ASMA imports
import assembler           # Access to some assembler objects
import lnkbase             # Access address objects


# This object helps in creation of assembly listing detail lines with potentially
# multipl physical lines (when continuation is present), multiple lines of object
# code are required (when PRINT DATA is in use) and potentially multiple errors.
class ListingLine(object):
    def __init__(self,loc=None,objcode=None,addr1=None,addr2=None,lineno=None,\
                 typ=" ",pline=None):
        # These values supply the detail line format 
        self.loc=loc             # Location columne
        self.objcode=objcode     # object code column
        self.addr1=addr1         # addr1 column
        self.addr2=addr2         # addr2 column
        self.lineno=lineno       # stmt number column
        self.typ=typ             # source type
        # This value is added to the detail after formatting
        self.pline=pline         # physical line
        
    def format(self,detail):
        values=[self.loc,self.objcode,self.addr1,self.addr2,self.lineno,self.typ]
        string=detail.string(values=values)
        if self.pline is not None:
            string="%s%s" % (string,self.pline.content)
        return string
    

class AsmListing(Listing):

    # This static method converts a single byte into a printable character.
    # EBCDIC and ASCII characters are both recognized.  Unprintable characters
    # are replaced with '.'.
    @staticmethod
    def print_hex(byte):
        char=E2A[byte]
        chrnum=ord(char)
        if chrnum<0x20 or chrnum>0x7E:
                char="."
        return char

    addr_max={16:0xFFFF,24:0xFFFFFF,31:0x7FFFFFFF,64:0xFFFFFFFFFFFFFFFF}
    def __init__(self,asm):
        self.linesize=132
        super().__init__(linesize=self.linesize,lines=55)
        self.asm=asm     # Access to the assembler for listing generation

        # Established by create() method when these structures actually exist
        self.stmts=None          # assembler Stmt objects
        self.ST=None             # the Symbol table
        self.imgwip=None         # binary Image work-in-progress
        self.image=None          # assembler output Image object (listing added)
        self.errors=None         # AssemblerError objects generated during assembly
        self.files=None          # List of copied file sources

        # More than one detail line may be created per assembly statement or other
        # components of the listing.  The following list is used to buffer such
        # details lines until requested by the super class.
        self.details=[]

        # Title established by create_title() method
        self.dir_title=""       # Title as supplied by TITLE assembler directive
        self.asmtitle=None      # Title object
        self.headers=8*[None,]  # Static headers for different parts

        # Part 1 - Assembly statement listing groups
        self.asmdet=None        # Group object for assembly line detail
        self.asmhdr=None        # Group object for assembly header line
        self.dirgrp=None        # Group for producing directive object code field
        self.instgrp=None       # Group for producing machine object code field

        # Part 2 - Symbol Table groups
        self.refgrp=None        # Group used to list symbol references
        self.symgrp=None        # Group for fixed columns
        self.rpl=None           # Number of references per line

        # Part 2_5 - Macro Cross Reference groups
        self.mrefgrp=None       # Group used to list macro references
        self.macgrp=None        # Group for fixed columns
        self.macgrpb=None       # Group for builtin macro fixed columns
        self.macrpl=None        # Number of reference per line

        # Part 3 - Image Map groups
        self.map_desc={}        # Map object type description dictionary
        self.mapgrp=None        # Group for a map detail line

        # Part 4 - Dump groups
        self.objgrp=None        # Group for object content
        self.chrgrp=None        # Group for character content
        self.dmpgrp=None        # Group for the dump detail line

        # Part 5 - Deck groups
        self.recgrp=None        # Group for each object deck dunp line

        # Part 6 - File list groups
        self.filgrp=None        # Group for file list detail line

        # Part 7 - Error list

        # Listing part management
        self.parts=None         # Defined listing parts (see create() method)
        self.prtparts=None      # List of actual parts to print (see create() method)
        self.next_part=0        # Next part of the listing to create
        self.next=0             # Next Stmt object index to be processed
        self.part=None          # Current listing part handler (see new_part() method)
        self.cur_part=None      # Current part number (see new_part() method)
        self.done=False         # Signals the listing is done

        # Shared information 
        self.max_line=None      # Maximum line number (the last line) for DecCol
        self.max_char=None      # Size in characters of maximum line number
        self.addrlen=None       # Size in characters of Part 1 LOC column

        # Data built for listing 
        self.stes=[]            # List of symbol table entries

        # Data built for macro cross-reference
        self.mtes=[]            # List of macro entries.
        self.max_mac=None       # Size in characters of maximum macro name
        self.mac_first=True     # Switch for first-time

        # Image map information
        self.part3_first=False  # Flag to inidicate first detail line
        self.entry=None         # Image entry point, if defined
        self.map_list=[]        # List of Map objects in image sequence
        self.max_pos=0          # Maximum image position value
        self.max_addr=0         # Maximum bound address value
        self.max_length=0       # Maximum length found in symbol table
        self.max_name=0         # Maximum length of an image map name
        self.max_value=0        # Maximum value found in the symbol table
        self.max_size=0         # Maximum map object length
        self.image=None         # Image object from the assembler

        # Dump information
        self.dump=False         # Dump option.
        self.part4_hdr=False    # Do a hearder without eject
        self.image_info=None    # The Map object for the image.
        self.reg_list=[]        # Regions in image order for dumping
        self.dumprecs=[]        # Dump object used to create dump output
        self.barray=None

        # Deck information
        self.hexchr="0123456789ABCDEF"
        self.deckdesc=None        # Detail line descriptions
        self.reccho=None          # High-order column positions as a string
        self.recclo=None          # Low-order column positions as a string

        # File list information
        self.name_len=0           # Maximum file name length
        self.max_fileno=0         # Maximum file number
        self.max_copy_stmt=0      # Maximum copy statement number

        # Error listing information
        self.part7_hdr=False      # Do a hearder without eject
        self.sorted_errors=None   # List of errors sorted by statement number
        self.num_errors=None      # Number of errors

    # This method extracts from the symbol table detail data and image related 
    # information.used in listing
    def __build(self):
        imginfo={}
        max_length=0
        max_value=0
        symbols=self.ST.getList(sort=True)
        for sym in symbols:
            # Build symbol table listing entry object list
            ste=self.ST[sym]
            name=sym
            value=ste.value()
            value=lnkbase.Address.extract(value)
            max_value=max(max_value,value)
            length=ste["L"]     # L' attribute
            max_length=max(max_length,value)
            defn=ste._defined
            refs=ste._refs
            typ=ste["T"]        # T' attribute
            s=Sym(name,typ,length,value,defn=defn,refs=refs)
            self.stes.append(s)
            # Build image map information (Image, Region and Control sections)
            if typ in ["1","2","J"]:
                image=ste["M"]  # M' attribute
                m=Map(name,typ,image,value,length)
                imginfo[name]=m
        self.max_length=max_length
        self.mac_value=max_value

        # Build the macro cross-reference list
        macs=self.asm.OMF.macros    # The dictionary of defined macros
        mtes=[]
        max_mac=0
        for macname in sorted(macs.keys()):
            mte=macs[macname]
            # mte is a MacroTable entry object, MTE.  It holds the XREF object
            xref=mte.xref
            macent=Mac(mte.name,xref)
            mtes.append(macent)
            max_mac=max(max_mac,len(macname))
        self.mtes=mtes
        self.max_mac=max_mac

        # Build the image map list
        name=self.imgwip.name
        iinfo=imginfo[name]
        self.image_info=iinfo      # Save to dump creation
        map_list=[iinfo,]
        reg_list=[]
        max_pos=0
        max_addr=0
        max_name=len(name)
        max_size=iinfo.length
        for r in self.imgwip.elements:
            name=r.name
            if name=="":
                # Unnamed region
                rinfo=Map("","2",r.img_loc,r.value().address,len(r))
                #print("pos: %s" % rinfo.pos)
                #print("bound: %s" % rinfo.bound)
                #print("length: %s" % rinfo.length)
                #print(rinfo)
            else:
                rinfo=imginfo[name]
            max_name=max(max_name,len(name))
            max_pos=max(max_pos,rinfo.pos_end)
            max_addr=max(max_addr,rinfo.bnd_end)
            map_list.append(rinfo)
            reg_list.append(rinfo)
            for c in r.elements:
                name=c.name
                if name=="":
                    # Unnamed section
                    cinfo=Map("","J",r.img_loc,r.value().address,len(r))
                else:
                    cinfo=imginfo[name]
                max_name=max(max_name,len(name))
                max_pos=max(max_pos,cinfo.pos_end)
                max_addr=max(max_addr,cinfo.bnd_end)
                map_list.append(cinfo)
        self.map_list=map_list
        self.reg_list=reg_list
        self.max_pos=max_pos
        self.max_addr=max_addr
        self.max_name=max_name
        self.max_size=max_size

        # Build file list
        sources=self.asm.IM.LB._files
        files={}
        for s in sources:
            fileno=s.fileno
            self.name_len=max(self.name_len,len(s.fname))
            self.max_fileno=max(self.max_fileno,fileno)
            if isinstance(s._stmtno,int):
                self.max_copy_stmt=max(self.max_copy_stmt,s._stmtno)
            try:
                fs=files[fileno]
                cls_str=assembler.eloc(self,"_build")
                raise ValueError("%s %s" % (cls_str,\
                    "duplicate file number: %s: %s" % (fs.fname,fileno)))
            except KeyError:
                files[s.fileno]=s
        filenums=list(files.keys())
        filenums.sort()
        file_list=[]
        for num in filenums:
            file_list.append(files[num])
        self.files=file_list

        # Build the dump records list
        if self.dump:
            dlines=[]
            for rndx in range(len(reg_list)):
                region=reg_list[rndx]
                regndx=rndx
                addr=region.bound
                pos=region.pos
                if region.length==0:
                    dlines.append(Dump(addr,pos,0,supbeg=32,region=regndx,empty=True))
                    continue
                # Region has something to actually dump
                endaddr=region.bnd_end+1
                while addr<endaddr:
                    beg_bounds=32*(addr // 32)   # 32 bytes per line
                    end_bounds=addr+32
                    supbeg=0
                    supend=0
                    if beg_bounds<addr:
                        supbeg=addr-beg_bounds
                    bytes_left=max(endaddr-addr,0)
                    bytes=min(bytes_left,32-supbeg)
                    filled=supbeg+bytes
                    if filled<32:
                        supend=32-filled

                    d=Dump(addr,pos,bytes,supbeg=supbeg,supend=supend,region=regndx)
                    regndx=None
                    dlines.append(d)
                    addr+=bytes   # Increment next address
                    pos+=bytes    # Increment the image position

            self.dumprecs=dlines

        # Build the assembler error list
        self.sorted_errors=sorted(self.errors,key=assembler.AssemblerError.sort)
        errors=0
        for e in self.sorted_errors:
            if e.info:
                continue
            errors+=1
        self.num_errors=errors

    # This method acts as the interface with the super class.  
    def create(self):
        # Get access to the assembler data needed for creating the listing
        self.stmts=self.asm.stmts     # Make available the Stmt objects
        self.ST=self.asm.ST           # Make available the Symbol Table
        self.imgwip=self.asm.imgwip   # Make available the binary Image object
        self.image=self.asm.img       # Make available the Image object (listing added)
        self.errors=sorted(self.image.aes,key=assembler.AssemblerError.sort)
        maxaddr=self.asm.laddrsize    # Maximum address size in bits
        self.addrmax=AsmListing.addr_max[maxaddr]   # Number of address characters
        self.entry=self.image.entry   # Image entry point (could be None)
        self.dump=self.asm.imgdump    # If True, dump CSECT's, regions and full image
        self.barray=self.image.image  # The actual image content
        self.deck=self.image.deck     # Card image deck if prepared

        # Generic listing part management
        self.parts=[Part1(0,self),\
                    Part2(1,self),\
                    Part2_5(2,self),\
                    Part3(3,self),\
                    Part4(4,self),\
                    Part5(5,self),\
                    Part6(6,self),\
                    Part7(7,self)]
        self.prtparts=[]
        for p in self.parts:
            if p.include(self):
                self.prtparts.append(p)

        self.__build()                # Build data for listing

        for p in self.prtparts:
            p.create()
        self.create_title()           # Create the default title
        self.new_part()               # Setup for part 1 of the listing

        # Generate the listing
        listing=self.generate()
        # Add it to the file Image object
        self.image.listing=listing

    def create_title(self):
        asmtitle=Title(self.linesize,pages=99999)
        version="ASMA Ver. %s.%s.%s" % assembler.asma_version
        asmtitle.setLeft([CharCol(size=len(version),default=version,sep=2),])
        asmtitle.setRight([DateTimeCol(now=self.asm.now,sep=2)],)
        asmtitle.setTitle(self.dir_title,center=False)
        self.asmtitle=asmtitle

   #
   #  These methods are called by the super class to provide either a title
   #  heading or detail line.
   #

    def detail(self,trace=False):
        cls_str="asmlist.py - %s.detail() -" % self.__class__.__name__
        try:
            det=self.pop()
            if trace:
                #cls_str="asmlist.py - %s.detail() -" % self.__class__.__name__
                print("%s detail 1: '%s'" % (cls_str,det))
            return det
        except IndexError:
            # Buffer empty pull more detail lines
            self.detail_lines()

        try:
            det=self.pop()
            if trace:
                print("%s detail 2: '%s'" % (cls_str,det))
            return det
        except IndexError:
            # Really done so tell the generate() method
            return None

    def heading(self):
        return self.headers[self.cur_part]

    def title(self):
        if self.asmtitle is None:
            #print("asmlist.py - title()")
            self.create_title()
        s=self.asmtitle.string(left=[None,],right=[None,])
        return s

    # Generic method for returning detail lines regardless of the listing part.
    def detail_lines(self):
        lines=[]
        if self.done:
            # Returning and empty list of detail lines ends the listing
            return lines
        # Detail line buffer empty so need to create new details.
        self.part()   # Call the active 'part' method

    # Return whether the listing is done or not
    def at_eol(self):
        return self.next_part>=len(self.prtparts)

    # initialize a new part of the listing
    def new_part(self):
        self.done=self.at_eol()
        if self.done:
            return

        part=self.prtparts[self.next_part]
        self.part=part.main
        self.cur_part=part.number
        self.next_part+=1

        self.next=0
        init=part.init
        init()   # Initialize the new part

   #
   #   PART 1 - Assembly Statement Listing
   #

    # This part generates lines and title for the main part of the listing
    def part1(self):
        while True:
            try:
                stmt=self.fetch()
            except IndexError:
                self.new_part()
                return
            if not stmt.prdir or stmt.error:
                # This processes assembler directives and machine instructions
                # Print directives in error are treated as normal statements for
                # the purpose of the listing
                if not stmt.pon:
                    # If PRINT OFF, ignore statement for listing
                    continue
                if stmt.gened and not stmt.pgen:
                    # If a generated macro statement and PRINT NOGEN, ignore 
                    continue
                line=self.part1_details(stmt)
                #print("line: [%s] %s\n    %s" % (stmt.lineno,len(line),line))
                # Note: line may be one detail line or a list of detail lines
                self.push(line)
                return

            # Processing for listing directives occurs here.
            directive=stmt.instu
            if directive=="SPACE":
                assert stmt.plist is not None,\
                    "[%s] SPACE statement missing plist" % stmt.lineno
                self.space(n=stmt.plist,eject=True)
                continue
            if directive=="TITLE":
                assert stmt.plist is not None,\
                    "[%s] TITLE statement missing plist" % stmt.lineno
                self.dir_title=stmt.plist
                if self.asmtitle is None:
                    self.create_title()
                else:
                    self.asmtitle.setTitle(self.dir_title,center=False)
                self.eject()
                continue
            elif directive=="EJECT":
                self.eject()
                continue
            else:
                cls_str="%s %s.part1() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s statement %s encountered unexpected listing "
                    "diretive: %s" % (cls_str,stmt.lineno,stmt.insn)) 

    def part1_create_detail(self):
        ad=[]
        ah=[]

        # The location column
        loc=HexCol(self.addrmax,sep=2,colnum=0)
        addrlen=loc.size
        self.addrlen=addrlen       # Save for other's use
        loch=CharCol(addrlen,just="center",sep=2,default="LOC",colnum=0)
        ad.append(loc)
        ah.append(loch)

        # The data column
        data=CharCol(17,just="left",sep=3,colnum=1)
        datah=CharCol(17,just="center",sep=3,default="OBJECT CODE",colnum=1)
        ad.append(data)
        ah.append(datah)

        # The ADDR1 Column
        size=max(5,addrlen)
        sep=max(2,size-addrlen+2)
        addr1=HexCol(self.addrmax,sep=sep,colnum=2)
        addr1h=CharCol(size,just="center",sep=2,default="ADDR1",colnum=2)
        ad.append(addr1)
        ah.append(addr1h)

        # The ADDR2 Column
        addr2=HexCol(self.addrmax,sep=sep,colnum=3)
        addr2h=CharCol(size,just="center",sep=2,default="ADDR2",colnum=3)
        ad.append(addr2)
        ah.append(addr2h)

        # STMT Column
        last_stmt=self.stmts[-1]
        max_line=last_stmt.lineno
        self.max_line=max_line            # Save for other's use
        size=Column.dec_size(max_line)
        self.max_char=size                # Save for other's use
        size=max(size,4)
        stmt=DecCol(maximum=max(max_line,9999),sep=0,colnum=4)
        stmth=CharCol(size,just="center",sep=0,default="STMT",colnum=4)
        ad.append(stmt)
        ah.append(stmth)

        # SOURCE Type
        stype=CharCol(1,sep=0,colnum=5)
        stypeh=CharCol(1,sep=0,colnum=5)
        ad.append(stype)
        ah.append(stypeh)
       
        # SOURCE Column
        default="  SOURCE STATEMENT"
        sh=CharCol(size=len(default),just="left",default=default,colnum=6)
        ah.append(sh)

        self.asmdet=Group(columns=ad)
        self.asmhdr=Group(columns=ah)

        # Create the header line using all default values
        asmhdr_str=self.asmhdr.string(values=[None,None,None,None,None,None])
        self.headers[0]=asmhdr_str

        dirgrp=[]
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=1))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        dirgrp.append(HexCol(maximum=0xFF,sep=0))
        self.dirgrp=Group(columns=dirgrp)

        instgrp=[]
        instgrp.append(HexCol(maximum=0xFF,sep=0))
        instgrp.append(HexCol(maximum=0xFF,sep=1))   
        instgrp.append(HexCol(maximum=0xFF,sep=0))
        instgrp.append(HexCol(maximum=0xFF,sep=1))
        instgrp.append(HexCol(maximum=0xFF,sep=0))
        instgrp.append(HexCol(maximum=0xFF,sep=1)) 
        self.instgrp=Group(columns=instgrp)

    def part1_details(self,stmt,trace=False):
        if trace:
            cls_str=assembler.eloc(self,"part1_details",module=this_module)
            
        # Retrieve the binary content of this statement
        content=stmt.content

        # Determine if object code is present and hence a value for the location
        # column is required.
        if content is None:
            loc=None
        else:
            loc=content.loc.lval()

        # Determine the content of the ADDR1 and ADDR2 columnes
        laddr=stmt.laddr    # This retrieves the list of two elements from the stmt

        if trace:
            print("%s [%s] addr fields: %s"  % (cls_str,stmt.lineno,len(laddr)))

        if stmt.asmdir:
            if trace:
                print("%s directive: %s" % (cls_str,stmt.instu))
            # Assembler directive
            addr1=lnkbase.Address.extract(laddr[0])
            addr2=lnkbase.Address.extract(laddr[1])
        else:
            # Machine instructions
            if len(laddr)==1:
                addr1=None
                addr2=lnkbase.Address.extract(laddr[0])
            elif len(laddr)==2:
                addr1=lnkbase.Address.extract(laddr[0])
                addr2=lnkbase.Address.extract(laddr[1])
            else:
                addr1=None
                addr2=None

        # Determinte the STMT number column
        lineno=stmt.lineno

        # Determine the statement type column: + for generated, space for open code
        if stmt.gened:
            stype="+"
        else:
            stype=" "

        # Break the object code into content for the object code columns
        data_lines=self.part1_data(stmt)
        # Determine the content for the last or only physical line 
        if len(data_lines)==0:
            data=None
        else:
            data=data_lines[0]
            del data_lines[0]

        # Determine the content of each listing line based upon the column values
        # and the number of physical lines.
        plines=stmt.logline.plines
        first=0               # First physical line
        last=len(plines)-1    # Last physical line
        dtlo=[]               # Created ListingLine objects

        for pndx,pline in enumerate(plines):
            if pndx==first and pndx==last:
                # Only one physical line
                dtl=ListingLine(loc=loc,objcode=data,addr1=addr1,addr2=addr2,\
                    lineno=lineno,typ=stype,pline=pline)
            elif pndx==first:
                # First of multiple physical lines
                dtl=ListingLine(loc=None,objcode=None,addr1=None,addr2=None,\
                    lineno=lineno,typ=stype,pline=pline)
            elif pndx==last:
                # Last of multiple physical lines
                dtl=ListingLine(loc=loc,objcode=data,addr1=addr1,addr2=addr2,\
                    lineno=None,typ=stype,pline=pline)
            else:
                # Midde physcial line
                dtl=ListingLine(loc=None,objcode=None,addr1=None,addr2=None,\
                    lineno=None,typ=stype,pline=pline)
            dtlo.append(dtl)

        # PRINT DATA in effect, need to create extra lines of OBJECT CODE
        # Create additional object code lines when PRINT DATA is active and more
        # than 8 bytes of object exist.
        if stmt.pdata:
            for n in data_lines:
                loc+=8
                dtl=ListingLine(loc=loc,objcode=n,addr1=None,addr2=None,\
                    lineno=None,typ=None,pline=None)
                dtlo.append(dtl)
              
        # This is the list of actual strings returned for this statement that
        # contstitute the listing for it.
        details=[]
        for dtl in dtlo:
            detail=dtl.format(self.asmdet)
            details.append(detail)

        # Add error(s) following the line in error
        if stmt.error:
            for ae in stmt.aes:
                spaces=" " * self.addrlen
                error_line="%s  ** %s" % (spaces,ae)
                details.append(error_line)

        return details

    # This method returns a list of strings destined for the OBJECT CODE column.
    def part1_data(self,stmt,trace=False):
        if trace:
            cls_str=assembler.eloc(self,"part1_data",module=this_module)
            print("%s stmt '%s' pdata=%s" % (stmt.inst,stmt.pdata))

        content=stmt.content
        if trace:
            print("%s content: %s" % (cls_str,content))
        if content is None:
            return [None,]

        data=content.barray
        if trace:
            print("%s data: %s" % (cls_str,data))
        if data is None:
            return [None,]
        if trace:
            print("%s len(data)=%s" % (cls_str,len(data)))
        if len(data)==0:
            return [None,]
        if (not stmt.pdata) or stmt.error:
            # List just the first 8 bytes if PRINT NODATA or error in statement
            data=data[:min(8,len(data))]
            dlist=[data,]
        else:
            # Break up object code into as many 8-byte chunks as needed
            dlist=[]
            for x in range(0,len(data),8):
                chunk=data[x:min(x+8,len(data))]
                dlist.append(chunk)

        data_lines=[]
        for chunk in dlist:
            if stmt.asmdir:
                # Create object code for assembler directive
                vals=8 * [None,]
                for ndx in range(len(chunk)):
                    byte=chunk[ndx]
                    vals[ndx]=byte
                chunk_str=self.dirgrp.string(values=vals)
                data_lines.append(chunk_str)
            else:
                vals=6 * [None,]
                for ndx in range(min(len(chunk),6)):
                    byte=chunk[ndx]
                    vals[ndx]=byte
                chunk_str=self.instgrp.string(values=vals)
                data_lines.append(chunk_str)
                break   # Bail after one instruction -- NEVER need more
        if trace:
            print("%s data_lines: %s" % data_lines)

        return data_lines

    def part1_init(self):
        self.detail_lines()       # Prime details (setting the first TITLE)

   #
   #   PART 2 - Symbol Table and Cross-reference Listing
   #

    def part2(self):
        try:
            ste=self.fetch_sym()
        except IndexError:
            self.new_part()
            return
        line=self.part2_details(ste)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part2_create_detail(self):
        hdr=[]
        det=[]

        # SYMBOL Column
        det.append(CharCol(16,sep=2,colnum=0))
        hdr.append(CharCol(16,just="center",sep=2,colnum=0,default="SYMBOL"))

        # TYPE Column
        det.append(CharCol(5,just="center",sep=2,colnum=1))
        hdr.append(CharCol(5,just="center",sep=2,colnum=1,default="TYPE"))

        # Value Column
        maximum=max(self.max_value,0xFFFFFF)
        size=Column.hex_size(maximum)
        det.append(HexCol(maximum=maximum,sep=2,colnum=2))
        hdr.append(CharCol(size,just="center",sep=2,colnum=2,default="VALUE"))

        # Length Column
        maximum=max(self.max_length,999999)
        size=Column.dec_size(maximum)
        det.append(DecCol(maximum=maximum,sep=2,colnum=3))
        hdr.append(CharCol(size,just="center",sep=2,colnum=3,default="LENGTH"))

        # Defn Column
        maximum=max(self.max_line,9999)
        size=Column.dec_size(maximum)
        det.append(DecCol(maximum=maximum,sep=2,colnum=4))
        hdr.append(CharCol(size,just="center",sep=2,colnum=3,default="DEFN"))

        #References
        ref="REFERENCES"
        hdr.append(CharCol(len(ref),just="left",colnum=5,default=ref))

        hdrgrp=Group(columns=hdr)
        hdrstr=hdrgrp.string(values=[None,None,None,None,None,None])
        self.headers[1]=hdrstr

        symgrp=Group(columns=det)
        self.symgrp=symgrp
        used_chars=len(symgrp)
        available_chars=self.linesize-used_chars
        colsize=self.max_char
        ref_size=colsize+2
        self.rpl=available_chars // ref_size

        refcol=[]
        for n in range(self.rpl):
            refcol.append(DecCol(maximum=self.max_line,sep=2,colnum=n))
        refgrp=Group(columns=refcol)
        self.refgrp=refgrp

    # Format one or more lines for a symbol table entry
    def part2_details(self,ste):
        details=[]      # List of detail lines being returned
        name=ste.name
        if len(name)>16:
            self.details.append(name)
            vals=[None,ste.typ,ste.value,ste.length,ste.defn]
        else:
            vals=[ste.name,ste.typ,ste.value,ste.length,ste.defn]
        detail=self.symgrp.string(values=vals)

        ref_info=self.part2_data(ste.refs)
        if len(ref_info)==0:
            refs=""
        else:
            refs=ref_info[0]
            del ref_info[0]

        det_line="%s%s" % (detail,refs)
        details.append(det_line)

        vals= 4*[None,]
        for ref in ref_info:
            det=self.symgrp.string(values=vals)
            det_line="%s%s" % (det,ref)
            details.append(det_line)

        return details

    def part2_data(self,refs):
        rpl=self.rpl
        # Break up object code into as many 8-byte chunks as needed
        rlist=[]            # List of a list of statement references
        refsize=len(refs)
        for x in range(0,refsize,self.rpl):
            chunk=refs[x:min(x+refsize,refsize)]
            rlist.append(chunk)

        data_lines=[]
        for chunk in rlist:
            vals=rpl * [None,]
            for ndx in range(min(len(chunk),rpl)):
                ref=chunk[ndx]
                vals[ndx]=ref
            ref_str=self.refgrp.string(values=vals)
            data_lines.append(ref_str)
        return data_lines

    def part2_init(self):
        self.eject()            # Force a new page starting part 2
        self.part2()            # Prime details

   #
   #   PART 2_5 - Macro Cross-Reference Listing
   #

    def part2_5(self):
        if self.mac_first:
            self.mac_first=False
            if len(self.mtes)==0:
                self.push("No defined macros")
                return
        try:
            m=self.fetch_mac()
        except IndexError:
            self.new_part()
            return
        line=self.part2_5_details(m)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return
        
    def part2_5_create_detail(self):
        hdr=[]
        det=[]

        # MACRO Column
        mac_col=max(5,self.max_mac)
        maccol=CharCol(mac_col,sep=2,colnum=0)
        det.append(maccol)
        hdr.append(CharCol(mac_col,just="center",sep=2,colnum=0,default="MACRO"))

        # Defn Column
        maximum=max(self.max_line,99990)
        size=Column.dec_size(maximum)
        det.append(DecCol(maximum=maximum,sep=2,colnum=1))
        hdr.append(CharCol(size,just="center",sep=2,colnum=1,default="DEFN"))

        #References
        ref="REFERENCES"
        hdr.append(CharCol(len(ref),just="left",colnum=2,default=ref))

        hdrgrp=Group(columns=hdr)
        hdrstr=hdrgrp.string(values=[None,None,None])
        self.headers[2]=hdrstr

        macgrp=Group(columns=det)
        self.macgrp=macgrp
        self.macgrpb=Group(columns=det)
        used_chars=len(macgrp)
        available_chars=self.linesize-used_chars
        colsize=self.max_char
        ref_size=colsize+2
        self.macrpl=available_chars // ref_size

        refcol=[]
        for n in range(self.macrpl):
            refcol.append(CharCol(ref_size,just="right",sep=1,colnum=n))
        mrefgrp=Group(columns=refcol)
        self.mrefgrp=mrefgrp

    def part2_5_data(self,refs):
        rpl=self.macrpl

        rlist=[]            # List of a list of statement references
        refsize=len(refs)
        for x in range(0,refsize,rpl):
            chunk=refs[x:min(x+refsize,refsize)]
            rlist.append(chunk)

        data_lines=[]
        for chunk in rlist:
            vals=rpl * [None,]
            for ndx in range(min(len(chunk),rpl)):
                ref=chunk[ndx]
                #vals[ndx]=ref
                # ref is an asmbase.xref object
                vals[ndx]="%s%s" % (ref.line,ref.flag)
            ref_str=self.mrefgrp.string(values=vals)
            data_lines.append(ref_str)

        return data_lines

    def part2_5_details(self,mte):
        details=[]      # List of detail lines being returned

        defn=mte.defn
        detail=self.macgrp.string(values=[mte.name,defn])

        ref_info=self.part2_5_data(mte.refs)

        if len(ref_info)==0:
            refs=""
        else:
            refs=ref_info[0]
            del ref_info[0]

        det_line="%s%s" % (detail,refs)
        details.append(det_line)

        vals= 2*[None,]
        for ref in ref_info:
            det=self.macgrp.string(values=vals)
            det_line="%s%s" % (det,ref)
            details.append(det_line)

        return details

    def part2_5_init(self):
        self.eject()            # Force a new page starting part 2
        self.part2_5()          # Prime details

   #
   #   PART 3 - IMAGE Map
   # 

    # Image Map
    def part3(self):
        try:
            m=self.fetch_map()
        except IndexError:
            self.new_part()
            return
        line=self.part3_details(m)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part3_create_detail(self):
        self.map_desc={"1":"Image",
                       "2":"  Region",
                       "J":"    CSECT"}
        lit0=self.map_desc["J"]
        hdr1=[]
        h1=0
        det1=[]

        # Image object type
        det1.append(CharCol(len(lit0),just="left",sep=2,colnum=0))
        hdr1.append(CharCol(len(lit0),just="center",sep=2,colnum=h1,default="DESC"))
        h1+=1

        # Name
        name_lit="SYMBOL"
        name_size=max(self.max_name,len(name_lit))
        det1.append(CharCol(name_size,just="left",sep=2,colnum=1))
        hdr1.append(CharCol(name_size,just="center",sep=2,colnum=h1,default=name_lit))
        h1+=1

        # 'Size:' literal
        # Length
        size_size=max(self.max_size,9999)
        size_col=DecCol(maximum=size_size,sep=2,colnum=2)
        det1.append(size_col)
        hdr1.append(CharCol(size_col.size,just="center",sep=2,colnum=h1,default="SIZE"))
        h1+=1

        # Starting position
        pos_beg=HexCol(maximum=self.max_pos,sep=0,colnum=3)
        det1.append(pos_beg)
        # '-' literal
        det1.append(CharCol(1,sep=0,default="-",colnum=4))
        # Ending position
        pos_end=HexCol(maximum=self.max_pos,sep=2,colnum=5)
        det1.append(pos_end)

        pos_size=pos_beg.size+pos_end.size+1
        hdr1.append(CharCol(pos_size,just="center",sep=2,colnum=h1,default="POS"))
        h1+=1

        # 'ADDR' literal
        addr_lit="ADDR"
        addr_beg=HexCol(maximum=self.max_addr,sep=0,colnum=6)
        addr_size=(2*addr_beg.size)+1
        end_sep=max(0,len(addr_lit)-addr_size)
        addr_size=max(addr_size,len(addr_lit))
        # Starting address
        det1.append(addr_beg)
        # '-' literal
        det1.append(CharCol(1,sep=0,default="-",colnum=7))
        # Ending address
        det1.append(HexCol(maximum=self.max_addr,sep=end_sep,colnum=8))
        hdr1.append(CharCol(addr_size,just="center",sep=0,colnum=h1,\
            default=addr_lit))

        det1_grp=Group(columns=det1)

        hdrg=Group(columns=hdr1)
        vals=(h1+1) * [None,]
        hdr_str=hdrg.string(values=vals)
        self.headers[3]=hdr_str

        self.mapgrp=det1_grp

    def part3_details(self,m):
        lines=[]
        if self.part3_first:
            if self.entry is None:
                entry="not defined"
            else:
                entry="%X" % self.entry
            self.push("Entry: %s" % entry)
            self.push("")
            self.part3_first=False
        vals=9 * [None,]
        vals[0]=self.map_desc[m.typ]
        vals[1]=m.name
        vals[2]=m.length
        vals[3]=m.pos
        vals[5]=m.pos_end
        vals[6]=m.bound
        vals[8]=m.bnd_end
        line=self.mapgrp.string(values=vals)
        return line

    def part3_init(self):
        # Going to actually print the object
        self.eject()            # Force a new page starting part 2
        self.part3_first=True   # First image map detail
        self.part3()            # Prime details

   #
   #   PART 4 - IMAGE Content Dump
   # 

    def part4(self):
        if self.part4_hdr:
            self.push("")
            self.push("")
            self.push(self.heading())
            self.push("")
            self.part4_hdr=False
        try:
            d=self.fetch_dump()
        except IndexError:
            self.new_part()
            return
        line=self.part4_details(d)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part4_create_detail(self):
        max_pos=max(self.max_pos,0xFFF)  # At least 3 hex digits for position
        max_addr=self.addrmax    # Match address size to main listing

        d1=[]
        dn=0
        # First group of 16 byes
        # First full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=0))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=1))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=2))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=3))
        # Second full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=4))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=5))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=6))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=7))
        # Third full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=8))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=9))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=10))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=11))
        # Fourth full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=12))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=13))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=14))
        d1.append(HexCol(maximum=0xFF,sep=2,colnum=15))

        # Second groups of 16 bytes
        # First full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=16))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=17))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=18))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=19))
        # Second full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=20))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=21))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=22))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=23))
        # Third full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=24))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=25))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=26))
        d1.append(HexCol(maximum=0xFF,sep=1,colnum=27))
        # Fourth full word
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=28))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=29))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=30))
        d1.append(HexCol(maximum=0xFF,sep=0,colnum=31))

        d1g=Group(columns=d1,sep=0)

        d3=[]
        d3.append(CharCol(1,just="left",sep=0,colnum=0,default="|"))
        d3.append(CharCol(16,just="left",sep=1,colnum=1))
        d3.append(CharCol(16,just="left",sep=0,colnum=2))
        d3.append(CharCol(1,just="left",sep=0,colnum=3,default="|"))
        d3g=Group(columns=d3,sep=0)

        d2=[]
        h2=[]

        # ADDR Column
        acol=HexCol(maximum=max_addr,sep=3,colnum=0)
        d2.append(acol)
        h2.append(CharCol(acol.size,just="center",sep=3,colnum=0,default="ADDR"))

        # POS Column
        pcol=HexCol(maximum=max_pos,sep=3,colnum=1)
        d2.append(pcol)
        h2.append(CharCol(pcol.size,just="center",sep=3,colnum=1,default="POS"))

        # object content
        obj_size=d1g.grpsize
        d2.append(CharCol(obj_size,sep=3,colnum=2))
        h2.append(CharCol(obj_size,just="center",sep=3,colnum=2,\
            default="OBJECT CONTENT"))

        # char content
        char_size=d3g.grpsize
        d2.append(CharCol(char_size,just="left",sep=0,colnum=3))
        h2.append(CharCol(char_size,just="center",sep=0,colnum=3,\
            default="CHARACTER CONTENT"))

        d2g=Group(columns=d2)

        h2g=Group(columns=h2)
        hdr_str=h2g.string(values=4*[None,])
        self.headers[4]=hdr_str

        self.objgrp=d1g
        self.chrgrp=d3g
        self.dmpgrp=d2g 

    def part4_details(self,m):
        detlines=[]

        # Create new region line with a blanc after it if this is a new region
        if m.region is not None:
            is_empty=m.empty
            if is_empty:
                emp=" (no content)"
            else:
                emp=""
            reg=self.reg_list[m.region]
            line="Region: %s%s" % (reg.name,emp)
            detlines.append("")
            detlines.append(line)
            detlines.append("")
            if is_empty:
                return detlines

        # Prepare object content group string
        vals=[]
        supbeg= m.supbeg * [None,]                # Do beginning suppressed bytes
        vals.extend(supbeg)

        objbyt=self.barray[m.beg_ndx:m.end_ndx]   # Do unsupressed bytes
        objlist=list(objbyt)
        vals.extend(objlist)

        supend= m.supend * [None,]                # Do ending suppressed bytes
        vals.extend(supend)

        objdata=self.objgrp.string(values=vals)

        # Prepare character content
        chrbeg= m.supbeg * " "
        chrend= m.supend * " "

        # Translate barray integers into ASCII printable string
        chrbytes=""
        chrbytes=byte2str(objbyt)
        chrbytes=assembler.CPTRANS.dumpa(chrbytes)

        # Create the character data group string
        chrs="%s%s%s" % (chrbeg,chrbytes,chrend)
        chr1=chrs[:16]
        chr2=chrs[16:]
        vals=[None,chr1,chr2,None]
        chrdata=self.chrgrp.string(values=vals)

        # Create final detail line group string
        vals=[m.addr,m.pos,objdata,chrdata]
        detline=self.dmpgrp.string(values=vals)

        detlines.append(detline)
        return detlines

    def part4_init(self):
        # Going to actually print the object
        # Need  2 lines, a new heading line, another line and a detail line = 5
        if self.remaining()>5:
            self.part4_hdr=True
        else:
            self.eject()        # Force a new page starting part 4
        self.part4()            # Prime details

   #
   #   PART 5 - Object Deck Contents
   # 

    def part5(self):
        try:
            rec=self.fetch_rec()
        except IndexError:
            self.new_part()
            return
        line=self.part5_details(rec)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part5_create_detail(self):
        # The same group is used for each of the five details lines used per
        # object deck record.
        #   line 1 - High-order column location
        #   line 2 - Low-order  column location
        #   line 3 - bits 0-4 of the column content
        #   line 4 - bits 5-7 of the column content
        #   line 5 - printable interpretation
        d=[]

        self.deckdesc=["COL","POS","HEX","   ","CHR"]

        d.append(CharCol(3,sep=2,colnum=0))    # Line description

        d.append(CharCol(10,sep=1,colnum=1))   # Col 1-10
        d.append(CharCol(10,sep=1,colnum=2))   # Col 11-20
        d.append(CharCol(10,sep=1,colnum=3))   # Col 21-30
        d.append(CharCol(10,sep=1,colnum=4))   # Col 31-40
        d.append(CharCol(10,sep=1,colnum=5))   # Col 41-50
        d.append(CharCol(10,sep=1,colnum=6))   # Col 51-60
        d.append(CharCol(10,sep=1,colnum=7))   # Col 61-70
        d.append(CharCol(10,sep=1,colnum=8))   # Col 71-80

        self.recgrp=Group(columns=d)
        self.headers[5]="OBJECT DECK"

        colpos_ho=[self.deckdesc[0],
                   "0000000001",
                   "1111111112",
                   "2222222223",
                   "3333333334",
                   "4444444445",
                   "5555555556",
                   "6666666667",
                   "7777777778"]
        colpos_lo=[self.deckdesc[1],]
        lo="1234567890"
        for n in range(8):
            colpos_lo.append(lo)

        self.reccho=self.recgrp.string(values=colpos_ho)
        self.recclo=self.recgrp.string(values=colpos_lo)

    def part5_details(self,rec):
        if self.remaining()<5:
            self.eject()
        details=[]
        hexchr=self.hexchr
        deckdesc=self.deckdesc

        hexacol=[deckdesc[2],]
        hexbcol=[deckdesc[3],]
        chrcol= [deckdesc[4],]

        for ndx in range(0,80,10):
            group=rec[ndx:ndx+10]
            hexa=""
            hexb=""
            chrs=""
            for n in group:
                col=hexchr[(n & 0xF0)>>4]
                hexa="%s%s" % (hexa,col)
                col=hexchr[n & 0x0f]
                hexb="%s%s" % (hexb,col)
                chrs="%s%s" % (chrs,AsmListing.print_hex(n))
            hexacol.append(hexa)
            hexbcol.append(hexb)
            chrcol.append(chrs)
        details.append(self.reccho)
        details.append(self.recclo)
        details.append(self.recgrp.string(values=hexacol))
        details.append(self.recgrp.string(values=hexbcol))
        details.append(self.recgrp.string(values=chrcol))
        details.append("")
        return details

    def part5_init(self):
        # Going to actually print the object
        self.eject()            # Force a new page starting part 2
        self.part5()            # Prime details

   #
   #   PART 6 - Referenced Files
   #

    def part6(self):
        try:
            fs=self.fetch_file()
        except IndexError:
            self.new_part()
            return
        line=self.part6_details(fs)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part6_create_detail(self):
        dc=[]
        hc=[]

        filecol=DecCol(maximum=self.max_fileno,sep=2,colnum=0)
        dc.append(filecol)
        hc.append(CharCol(filecol.size,sep=2,colnum=0))

        stmt_hdr="STMT"
        dc.append(DecCol(maximum=self.max_copy_stmt,sep=2,colnum=1))
        hc.append(CharCol(len(stmt_hdr),colnum=1,sep=2,default=stmt_hdr))

        name_hdr="FILE NAME"
        namesize=max(self.name_len,len(name_hdr))
        dc.append(CharCol(namesize,sep=2,colnum=2))
        hc.append(CharCol(namesize,just="center",sep=2,colnum=2,default=name_hdr))

        hgrp=Group(columns=hc)
        hdr=hgrp.string(values=[None,None,None])
        self.headers[6]=hdr

        self.filgrp=Group(columns=dc)

    def part6_details(self,src):
        #detail=[self.filgrp.string(values=[src.fileno,src.fname,src._stmtno]),]
        detail=[self.filgrp.string(values=[src.fileno,src._stmtno,src.fname]),]
        return detail

    def part6_init(self):
        self.eject()            # Force a new page starting part 2
        self.part6()            # Prime details


   #
   #   PART 7 - Sorted Assembly Errors 
   #

    def part7(self):
        if self.part7_hdr:
            self.push("")
            self.push("")
            self.push(self.heading())
            self.push("")
            self.part7_hdr=False
        try:
            ae=self.fetch_error()
        except IndexError:
            self.new_part()
            return
        line=self.part7_details(ae)
        # Note: line may be one detail line or a list of detail lines
        self.push(line)
        return

    def part7_create_detail(self):
        if self.num_errors==0:
            hdr="** NO ERRORS FOUND **"
        else:
            hdr="** ERRORS FOUND: %s **" % self.num_errors
        self.headers[7]=hdr

    def part7_details(self,ae):
        return "%s" % ae

    def part7_init(self):
        if self.remaining()>5:
            self.part7_hdr=True
        else:
            self.eject()        # Force a new page starting part 7
        self.part7()            # Prime details

    #
    # These methods work with various structures and objects from the Assembler
    #

    # Return a Stmt object.  IndexError indicates the end of the list
    def fetch(self):
        stmt=self.stmts[self.next]
        self.next+=1
        return stmt

    # Return a Dump object.  IndexError indicates the end of the list
    def fetch_dump(self):
       dump=self.dumprecs[self.next]
       self.next+=1
       return dump

    # Return an AssemblerError object
    def fetch_error(self):
        ae=self.errors[self.next]
        self.next+=1
        return ae

    # Return a file source.  Indexerror indicates the end of the list
    def fetch_file(self):
        source=self.files[self.next]
        self.next+=1
        return source

    # Returns a Mac object.  IndexError indicate the end of the list
    def fetch_mac(self):
        m=self.mtes[self.next]
        self.next+=1
        return m

    # Returns a Map object.  IndexError indicates the end of the list
    def fetch_map(self):
        m=self.map_list[self.next]
        self.next+=1
        return m

    # Returns an object deck record.  IndexError indicates the end of the list
    def fetch_rec(self):
        ndx=self.next*80
        if ndx >= len(self.deck):
            raise IndexError()
        endndx=ndx+80
        rec=self.deck[ndx:endndx]
        self.next+=1
        return rec

    # Return a Sym object.  IndexError indicates the end of the list
    def fetch_sym(self):
        ste=self.stes[self.next]
        self.next+=1
        return ste

   #
   # The pop() and push() methods manage the detail line buffer
   #

    # Return a detail line from the buffer.
    # An IndexError indicates the buffer is empty
    def pop(self):
        det=self.details[0]
        del self.details[0]
        return det

    # Provide a detail line to the buffer.
    def push(self,lines,trace=False):
        if trace:
            cls_str="asmlist.py %s.push() -" % self.__class__.__name__
            print("%s push(%s)" % (cls_str,lines))
        if isinstance(lines,list):
            for n in lines:
                if not isinstance(n,str):
                    cls_str="%s %s.push() -" % (this_module,self.__class__.__name__)
                    raise ValueError("%s detail buffer must only contain strings: %s" \
                        % (cls_str,n.__class__.__name__))
                self.details.append(n)
            if trace:
                print("%s push list\n    %s" % (cls_str,self.details))
        else:
            if not isinstance(lines,str):
                cls_str="%s %s.push() -" % (this_module,self.__class__.__name__)
                raise ValueError("%s detail buffer must only contains strings: %s" \
                    % (cls_str,lines.__class__.__name__))
            self.details.append(lines)
            if trace:
                print("%s push string\n    %s" % (cls_str,self.details))

# This object defines a listing part
class Part(object):
    def __init__(self,number,main,init,create):
        self.number=number     # Part number -1 for index into headers
        self.main=main         # Main processing method
        self.init=init         # Method initializing the part
        self.create=create     # Method creating groups and heading

    def __str__(self):
        return "%s - %s" % (self.__class__.__name__,self.number)

    # This method determines whether the part is included or not.  By default the
    # part is assumed to be included.  A part of the assembly needs to override
    # this if an inclusion test is required.
    def include(self,listing):
        return True

class Part1(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part1,listing.part1_init,listing.part1_create_detail)

class Part2(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part2,listing.part2_init,listing.part2_create_detail)

class Part2_5(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part2_5,listing.part2_5_init,listing.part2_5_create_detail)

class Part3(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part3,listing.part3_init,listing.part3_create_detail)

class Part4(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part4,listing.part4_init,listing.part4_create_detail)
    def include(self,listing):
        return listing.dump and listing.barray is not None

class Part5(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part5,listing.part5_init,listing.part5_create_detail)
    def include(self,listing):
        return listing.dump and listing.deck is not None

class Part6(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part6,listing.part6_init,listing.part6_create_detail)

class Part7(Part):
    def __init__(self,number,listing):
        super().__init__(number,\
            listing.part7,listing.part7_init,listing.part7_create_detail)

# These classes assists in development of the listing
class Dump(object):
    def __init__(self,addr,pos,bytes,supbeg=0,supend=0,region=None,empty=False):
        self.region=region       # If not None, indicates a new region being dumped
        self.addr=addr           # Starting content address
        self.pos=pos             # Starting image position
        self.supbeg=supbeg       # Number of beginning bytes not displayed
        self.supend=supend       # Number of ending bytes not displayed
        self.bytes=bytes         # Number of bytes displayed
        self.beg_ndx=pos         # image beginning index
        self.end_ndx=pos+bytes   # image ending index
        self.empty=empty         # Region is empty (just put out a single line)
        if empty:
            return
        # Perform line sanity check
        cls_str="%s %s.__init__() -" % (this_module,self.__class__.__name__)
        tot_bytes=self.supbeg+self.supend+self.bytes
        if tot_bytes!=32:
            raise ValueError("%s line not consistent: supbeg (%s) + bytes (%s) + "
                "supend (%s) != 32: %s" 
                % (self.supbeg,self.bytes,self.supend,tot_bytes))
        image_bytes=self.end_ndx-self.beg_ndx
        if image_bytes != self.bytes:
            raise ValueError("%s image bytes (%s) does not match line bytes: %s" \
                % (cls_str,image_bytes,self.bytes))

    def __str__(self):
        return "Dump(addr=0x%X,pos=0x%X,supbeg=%s,supend=%s,bytes=%s,"\
                "index=[0x%X:0x%X],region=%s,empty=%s)" \
                    % (self.addr,self.pos,self.supbeg,self.supend,self.bytes,\
                       self.beg_ndx,self.end_ndx,self.region,self.empty)


class Mac(object):
    def __init__(self,name,refs):
        self.name=name          # Macro name
        self.defn=None          # Statement defining the macro
        refents=refs.sort()     # List of sorted asmoper.xref objects
        if len(refents)>0:
            self.defn=refents[0].line  # The first xref entry is the first definition
            refents=refents[1:]        # The others go inte REFERENCES area
        self.refs=refents      # List of sorted asmoper.xref objects
    def __str__(self):
        return "Mac('%s',defn=%s,refs=%s)" % (self.name,self.defn,self.refs)


class Map(object):
    def __init__(self,name,typ,image,bound,length):
        self.name=name          # Image, Region, CSECT name
        self.typ=typ            # Type of map object
        self.length=length      # Length of the object.
        self.pos=image          # Starting location in the image
        self.pos_end=max(self.pos,self.pos+length-1)
        self.bound=bound        # Bound address
        self.bnd_end=max(self.bound,self.bound+length-1)
    def __str__(self):
        return "Map('%s',type='%s',pos=0x%X-0x%X,bound=0x%X-0x%X,length=%s)" \
            % (self.name,self.typ,self.pos,self.pos_end,self.bound,self.bnd_end,\
                self.length)

class Sym(object):
    def __init__(self,name,typ,length,value,defn=None,refs=[]):
        self.name=name          # Symbol Name
        self.typ=typ            # Symbol type
        self.length=length      # Symbol length
        self.value=value        # Symbol value
        self.defn=defn          # Statement defining the symbol
        self.refs=refs          # List of statements referencing the symbol
        for n,x in enumerate(self.refs):
            if x is None:
                print("Symbol: %s Reference ndx: %s is None" % (self.name,n))

if __name__ == "__main__":
    raise NotImplementedError("asmlist.py - intended for import use only")
