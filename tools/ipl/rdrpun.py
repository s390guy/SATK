#!/usr/bin/python
# Copyright (C) 2012 Harold Grovesteen
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

# This module provides utility functions for accessing AWS Tapes from Python
#
# It is one of a number of modules that support Hercules emulated device
# media:
#
#    media.py      Instances of media records are converted to emulated
#                  media: card images, AWS tape image file, FBA image file
#                  or CKD image file.  All image files are uncompressed.
#    recsutil.py   Python classes for individual records targeted to a device
#                  type: card, tape, fba or ckd
#    rdrpun.py     This module. Handles writing and reading card decks.
#    awsutil.py    Handles writing and reading AWS tape image files.
#    fbautil.py    Handles writing and reading of FBA image files.
#    ckdutil.py    Handles writing and reading of CKD image files.
#
# See media.py for usage of AWS tape file images

class reader(object):
    # To open a card deck for reading: deck=reader.load(filename)
    # To read a card: card=deck.read()
    # To test for end-of-file: reader.eof(card)
    # To close the card deck: deck.unload()
    record="card"  # recsutil class name of card deck records
    def eof(card):
        return len(card)==0
    eof=staticmethod(eof)
    def load(filename):
        try:
            fo=open(self.filename,"rb")
        except IOError:
            raise IOError(\
                "Could not open existing card deck: %s" % self.filename)
        return rdr(fo)
    load=staticmethod(load)
    def __init__(self,fo):
        self.fo=fo         # Card deck file object
    def read(self):
        card=self.fo.read(80)    # Read the card
        if len(card)==80 or len(card)==0:
           return card
        # Incomplete card, pad with EBCDIC blanks
        pad=80*"\x40"
        padded=card+pad
        return padded[:80]
    def unload(self):
        try:
            self.fo.close()
        except IOError:
            raise IOError("Could not unload card deck: %s" % self.fo.name)

class punch(object):
    # To open a card deck for writing: deck=punch.load(filename)
    # To write a card: deck.punch(card)
    # To finish the deck: deck.unload()
    record="card"  # recsutil class name of card deck records
    def load(filename):
        try:
            fo=open(filename,"wb")
        except IOError:
            raise IOError(\
                "Could not open card deck for punching: %s" % filename)
        return punch(fo)
    load=staticmethod(load)
    def size(hwm=None):
        # This method is required by media.py to size a emulating media file
        return None     # Card decks do not have predetermined sizes
    size=staticmethod(size)
    def __init__(self,fo):
        self.fo=fo         # Card deck file object
    def punch(self,card):
        if len(card)!=80:
            raise TypeError("card not 80 bytes: %s" % len(card))
            
        card=self.fo.write(card)   # Write the card
    def unload(self):
        try:
            self.fo.close()
        except IOError:
            raise IOError("Could not unload card deck: %s" % self.fo.name)

rdrpun_devices={}

# media.py expects this function to be available
def register_devices(dtypes):
    for x in [0x1442,0x2501,0x3505]:
        string="%04X" % x
        dtypes.dtype(string,reader)
        dtypes.dndex(dtypes.number(x),string)
        rdrpun_devices[string]=(x,1)
    for x in [0x3525,]:
        string="%04X" % x
        dtypes.dtype(string,punch)
        dtypes.dndex(dtypes.number(x),string)
        rdrpun_devices[string]=(x,1)
    dtypes.dtype("rdr",reader)
    dtypes.dtype("pun",punch)

if __name__=="__main__":
    print "rdrpun.py is only intended for import"