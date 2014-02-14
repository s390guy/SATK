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

# This module generates the binary output for ASMA.

this_module="asmbin.py"

# Python imports: None

# ASMA imports
import assembler

# SATK imports:
from translate import A2E  # Character translation table

#
#  +---------------------------+
#  |                           |
#  |   Binary Output Manager   |
#  |                           | 
#  +---------------------------+
#

class AsmBinary(object):
    TXT=b"\x02\xE3\xE7\xE3"
    END=b"\x02\xC5\xD5\xC4"
    SPACE=b"\x40"
    def __init__(self):
        # Binary work in progress.  See __find_contig() method
        self.contig=None
        self.max_addr=0

    # Convert string to bytearray
    @staticmethod
    def str2array(string):
        array=bytearray(b"")
        for c in string:
            #char=ord(c)
            array.append(ord(c))
        return bytearray(array)

    # Scan all of the assembler statements looking for contiguous binary data.  For
    # each chunk it finds, create a Contig instance and add it to list, self.contig
    def __find_contig(self,asm):
        # If list already exists, no need to scan the statements again.
        if isinstance(self.contig,list):
            return

        current=None
        max_addr=0
        contig_list=[]

        for stmt in asm.stmts:
            if stmt.ignore:            # statement ignored?  The honor it
                continue
            content=stmt.content       # This is a Binary object or None
            if content is None:        # If no Binary object, ignore it
                continue
            barray=content.barray      # This is a bytearray or None
            if barray is None:         # If no data to add, ignore it
                continue
            loc=content.loc            # This is Address object or None
            if loc is None:            # If not address to go with the data, ignore it
                continue
            if not loc.isAbsolute():   # Only use data with an absolute address
                continue
            if len(barray)==0:         # If data is actually of zero length, ignore it
                continue

            # Found some actual data that could be contigous with other data
            addr=loc.address
            max_addr=max(max_addr,addr)   # Save maximum address
            if current is None:
                current=Contig(addr)
            if current.add(addr,barray):
                # True means it _was_ contigous so keep looking for more
                continue
            # False means it was _not_ contiguous.  Add what we have to complete list
            contig_list.append(current)
            # Start a new area and add the discontiguous data to it.
            current=Contig(addr)
            current.add(addr,barray)

        self.max_addr=max_addr          # Remember the maximum address

        # Done of all of the contiguous areas have been added to the list.
        if current is not None:
            # Add final contigous area to the list
            contig_list.append(current)

        self.contig=contig_list

    # Creates STORE comamnds:  STORE R S hexloc data
    def __store_commands(self,asm,cp=False):
        if cp:
            cpcmd="CP "
        else:
            cpcmd=""

        self.__find_contig(asm)   # Locate the chunks of contigous data.
        chunks=[]
        for c in self.contig:
            chunks.extend(c.chunks(16))  # maximum of 16 bytes stored
        cmdfile=""
        for c in chunks:
            cmdfile="%s%sSTORE R S %X %s\n" \
                % (cmdfile,cpcmd,c.addr,self.bytes_in_hex(c.data))
        #print("cmdfile:\n%s" % cmdfile)
        return cmdfile

    def bytes_in_hex(self,barray):
        hexdata=""
        for b in barray:
            hexdata="%s%02X" % (hexdata,b)
        return hexdata

    def card_sequence(self,number):
        num="%08d" % number
        num=num.translate(A2E)
        return bytearray(AsmBinary.str2array(num))

    # Return a object deck for loading assembled content from statements.
    def deck(self,asm):
        self.__find_contig(asm)   # Locate the chunks of contigous data.

        if self.max_addr>0xFFFFFF:
            print("addresses exceed supported object deck maximum (0xFFFFFF): 0x%X "
                "- object deck suppressed" % self.max_addr)
            return

        entry=asm.img.entry
        if entry is None:
            print("object deck requires ENTRY address - object deck suppressed")
            return

        chunks=[]
        for c in self.contig:
            chunks.extend(c.chunks(56))  # 56 is the maximum bytes in a TXT record

        # Prepare constants for deck generation
        blank1=AsmBinary.SPACE        # Position 5    in TXT record
        blank2=2*AsmBinary.SPACE      # Position 9,10 and 13,14 in TXT record
        TXT=bytearray(AsmBinary.TXT)
        END=bytearray(AsmBinary.END)
        ESDID=(0).to_bytes(2,byteorder="big")  # Positions 15 and 16 in TXT record
        number=1
        deck=[]

        # Generate TXT records
        for c in chunks:
            record=[]
            record.extend(TXT)                        # Pos 1-4
            record.extend(blank1)                     # Pos 5
            addr=c.addr.to_bytes(3,byteorder="big")
            record.extend(addr)                       # Pos 6-8
            record.extend(blank2)                     # Pos 9,10
            bytes=len(c.data).to_bytes(2,byteorder="big")
            record.extend(bytes)                      # Pos 11,12
            record.extend(blank2)                     # Pos 13,14
            record.extend(ESDID)                      # Pos 15,16
            blanks=56-len(c.data)
            blanks=blanks*blank1
            record.extend(c.data)
            record.extend(blanks)                     # Pos 17-72
            record.extend(self.card_sequence(number)) # Pos 73-80
            number+=1
            deck.extend(record)

        # Generate END record
        record=[]
        record.extend(END)                            # Pos 1-4
        record.extend(blank1)                         # Pos 5
        entry=entry.to_bytes(3,byteorder="big")
        record.extend(entry)                          # Pos 6-8
        record.extend(6*blank1)                       # Pos 9-14
        record.extend(ESDID)                          # Pos 15,16
        record.extend(56*blank1)                      # Pos 17-72
        record.extend(self.card_sequence(number))     # Pos 73-80
        deck.extend(record)

        return bytearray(deck)

    # Create tuple list of list for directed IPL content.
    # Each tuple contains:
    #   tuple[0] - file name within the list directed IPL directory
    #   tuple[1] - file content
    #   tupel[2] - Python open mode for writing the file
    def ldipl(self,asm):
        imgwip=asm.imgwip         # Get the work-in-progress version of Image
        regions=imgwip.elements   # Get the list of regions
        ldipl_list=[]
        ipl_content=""
        for r in regions:
            name=r.name
            address=r.loc.address
            content=r.barray
            filename="%s.bin" % name
            tup=(filename,content,"wb")
            ldipl_list.append(tup)
            ipl_content="%s%s 0x%X\n" % (ipl_content,filename,address)
        tup=("IMAGE.ipl",ipl_content,"wt")
        ldipl_list.append(tup)
        return ldipl_list

    # Create management console STORE connand file
    def mc_file(self,asm):
        return self.__store_commands(asm,cp=False)

    # Create Hercules real storage alter commands: r hexloc=data
    def rc_file(self,asm):
        self.__find_contig(asm)   # Locate the chunks of contigous data.
        chunks=[]
        for c in self.contig:
            chunks.extend(c.chunks(16))  # maximum of 16 bytes altered by r command
        rcfile=""
        for c in chunks:
            rcfile="%sr %X=%s\n" % (rcfile,c.addr,self.bytes_in_hex(c.data))

        return rcfile

    # Create a virtual machine STORE command file     
    def vmc_file(self,asm):
        return self.__store_commands(asm,cp=True)


class Chunk(object):
    def __init__(self,addr,data):
        self.addr=addr
        self.data=data
    def __str__(self):
        length=len(self.data)
        return "Chunk(start=0x%X,end=0x%X,bytes=%s)" \
            % (self.addr,self.addr+length-1,length)

class Contig(object):
    def __init__(self,start):
        self.start=start       # Starting address of contiguous area
        self.next=start        # Addres of next contiguous area
        self.data=[]           # Accumulated data

    def __str__(self):
        length=len(self.data)
        return "Contig(start=0x%X,end=0x%X,bytes=%s)" \
            % (self.start,self.start+length-1,length)

    # Accumulates contigous data.
    # Returns True if data is accepted as contiguous
    # Returns False if the data is not contiguous.
    def add(self,addr,data):
        if not isinstance(data,(bytes,bytearray)):
            cls_str=assembler.eloc(self,"add")
            raise ValueError("%s 'data' argument must be bytes or bytearray: %s" \
                % (cls_str,data))

        if addr!=self.next:
            return False
        if not isinstance(data,list):
            d=list(data)
        else:
            d=data

        self.data.extend(d)
        self.next+=len(d)
        return True

    # Returns a list of Chunk objects in the size requested
    def chunks(self,size):
        length=len(self.data)
        addr=self.start
        chunks=[]
        for ndx in range(0,length,size):
            c=self.data[ndx:min(ndx+size,length)]
            chunks.append(Chunk(addr+ndx,c))
        return chunks

if __name__ == "__main__":
    raise NotImplementedError("asmbin.py - intended for import use only")