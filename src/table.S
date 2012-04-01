.ifndef .Ltable_S
.Ltable_S = 1
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

 # This module provides support for the creation of generic tables.
 # Entries are indexed relative to zero
 # A program header may be included in the table's header

 #  The following macros are provided
 #
 #    32-bit    64-bit       Description
 #
 #    ftable    ftableg    Define and start a function table
 #    fte       fteg       Define a function table entry
 #    ftval     ftvalg     Extract the a function table entry's value
 #    lhdr      lhdr       Load the address of a table's user header extension
 #    lndx      lndxg      Load the address of a table entry from its index
 #    table     tableg     Define and start a table
 #    tablend   tablend    Terminate a previously started table
 #    tblbld    tblbldg    Dynamically Build a table header
 #    tblscan   tblscang   Scan a table's entries
 #    tblnext   tblnextg   Continue scanning a table's entries
 #
 # Tables are created like this:
 #
 #          table  name=.Ltable,len=8
 #          entry     # 8 byte entry
 #          entry     # 8 byte entry
 #          tablend name=.Ltable
 #
 # If a user header is included, the table is created like this:
 #
 #          table name=.Ltable,len=8,hdr=4
 #          header    # 4-byte user header
 #          entry     # 8-byte entry
 #          entry     # 8-byte entry
 #          tablend end=.Ly
 #
 # To scan one of the above tables:
 #
 #          la      x,.Ltable-0b(13)           # Point to the table
 #          tblscan tblr=x,ntryr=y,done=.Ldone
 #
 #          [process the entry pointed to by y ]
 #
 #          tlbnext tblr=x,ntryr=y             # Process the next entry
 #
 # .Ldone:  # Continue with other processing
 #
 # A function table is a table that contains an address at the start of the
 # entry intended to be used in calling a function.  The macros that start with
 # 'ft' are wrappers that use the standard table macros to handle such tables.

 # ftable/ftableg - Define and start a function table
 #
 #  Macro Parameters:
 #       name   Symbol used to define the table and by which the table is
 #              referenced (required)
 #       usr    Lenght of the optional entry user extension (default 0)
 #       hdr    Length of an optional header table (default 0)   

            .macro ftable name:req usr=0 hdr=0
            table name=\name,len=4+\usr,hdr=\hdr
            .endm

            .macro ftableg name:req usr=0 hdr=0
            table name=\name,len=8+\usr,hdr=\hdr
            .endm

 # ftcall/ftcallx -  Call a function table entry
 #
 #  Macro Parameters:
 #       r      Register into which the function address is loaded (required)
 #       tblr   Register pointing to the table header (required)
 #       nxdr   Register containing the table index (required)
 #       error  Symbol to which control is passed if the value is zero (required)
 #       argr   Register into which the table entry is passed as an argument
 #              (optional) 
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro ftcall r:req tblr:req ndxr:req error:req argr br=13 b=0b
            ftval r=\r,ndxr=\ndxr,tblr=\tblr,error=\error,addr=\argr,br=\br,b=\b
            callr \r
            .endm

            .macro ftcallx r:req tblr:req ndxr:req error:req argr br=13 b=0b
            ftvalg r=\r,ndxr=\ndxr,tblr=\tblr,error=\error,addr=\argr,br=\br,b=\b
            callrx \r
            .endm

 # fte/fteg - Create a function table entry 
 #
 # Any user data must be placed following the func/funcg macro for the entry 
 # or a the entry must contains the function at the beginning of the entry.
 #
 #  Macro Parameters:
 #       name   Symbol used to define the function in the table (required)

            .macro fte name:req
            .long  \name
            .endm

            .macro fteg name:req
            .quad  \name
            .endm

 # ftend - Terminate a previously started function table
 #
 #  Macro Parameters:
 #       name   Symbol used to define the function in the table (required)

             .macro ftend name:req
\name\()_end:
            .endm

 # ftval/ftvalg -  Extract the function entry value from the function table
 #
 #  Macro Parameters:
 #       r      Register into which the address is loaded (required)
 #       tblr   Register pointing to the table header (required)
 #       nxdr   Register containing the table index (required)
 #       error  Symbol to which control is passed if the value is zero or the
 #              index is beyond the end of the table (required)
 #       addr   Register into which the table entry address is also provided
 #              (optional)
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro ftval r:req tblr:req ndxr:req error:req addr br=13 b=0b
            lndx   r=\r,tblr=\tblr,ndxr=\ndxr,error=\error,br=\br,b=\b
    .ifnb \addr
            lr     \addr,\r   # Save the entry address
    .endif
            l      \r,0(\r)   # Retrieve the value
            ltr    \r,\r      # Is the value zero?
            bz     \error-\b(\br) # ..Yes, also an error
            .endm

            .macro ftvalg r:req tblr:req ndxr:req error:req addr br=13 b=0b
            lndxg  r=\r,tblr=\tblr,ndxr=\ndxr,error=\error,br=\br,b=\b
    .ifnb \addr
            lgr    \addr,\r   # Save the entry address
    .endif
            lg     \r,0(\r)   # Retrieve the value
            ltgr   \r,\r      # Is the value zero?
            jz     \error     # ..Yes, also an error
            .endm

 # lhdr - Load the address of the table user header extension into a register
 #
 #  Macro Parameters:
 #       r      Register into which the address is loaded (required)
 #       tblr   Register pointing to the table header (required)

            .macro lhdr r:req tblr:req
            la     \r,16(\tblr)      # Locate start of user header
            .endm

 # lndx/lndxg - Load an address into a register based upon a table's entry index
 #
 #  Macro Parameters:
 #       r      Register into which the address is loaded (required)
 #       tblr   Register pointing to the table header (required)
 #       nxdr   Register containing the table index (required)
 #       error  Symbol to which control is passed is the index is beyond the end
 #              of table (optional)
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro lndx r:req tblr:req ndxr:req error br=13 b=0b
            lr     \r,\ndxr       # Fetch the index
            mh     \r,6(\tblr)    # convert index into displacement
            al     \r,0(\tblr)    # Locate entry address
            la     \r,0(\r,\tblr) # Convert disp. into address
    .ifnb  \error
            cl     \r,8(\tblr)    # is the entry beyond the end?
            bnl    \error-\b(\br) # ..Yes, go to handle error
    .endif
            .endm

            .macro lndxg r:req tblr:req ndxr:req error br=13 b=0b
            llgfr  \r,\ndxr       # Fetch the index and zero bits (0-31)
            mh     \r,6(\tblr)    # Convert index into disp.
            algf   \r,0(\tblr)    # Adjust for the header
            la     \r,0(\r,\tblr) # Convert disp. into address
    .ifnb  \error
            clg    \r,8(\tblr)    # is the entry beyond the end?
            jnl    \error         # ..Yes, go to handle error
     .endif
            .endm

 # table/tableg - Define and start a table
 #
 #  Macro Parameters:
 #       name   Symbol used to define the table and by which the table is
 #              referenced (required)
 #       len    Length of each entry in the table (required)
 #       hdr    Length of an optional header table (default 0)

            .macro table name:req len:req hdr=0
\name\()_len = \len
\name\()_hdr = \hdr+16
\name:
            .long  \name\()_hdr,\name\()_len,\name\()_end,0
            .endm

            .macro tableg name:req len:req hdr=0
\name\()_len = \len
\name\()_hdr = \hdr+16
\name:
            .long  \name\()_hdr,\name\()_len
            .quad  \name\()_end
            .endm

 # tablend - Terminate a previously started table.
 #
 #  Macro Parameters:
 #       name   Symbol used to define the table being terminated (required)

            .macro tablend name:req
\name\()_end:
            .endm

 # tblbld/tblbldg - Dynamically build a table
 #  Macro Parameters:
 #       tblr   Register pointing the location to build the table (required)
 #       nr     Register containing the number of table entries (required)
 #       sr     Register containing the size of the individual entries (required)
 #       hdr    Register containing the size of the header (required)
 #       wrkr   Work register (required)
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro tblbld tblr:req nr:req sr:req hdr:req wrkr:req br=13 b=0b
            lh     \wrkr,.+40-\b(\br) # +40 Work register contains the header size
            alr    \wrkr,\hdr         # +36 Work register is the total header size
            st     \wrkr,0(\tblr)     # +34 Set the header size in the header
            st     \sr,4(\tblr)       # +30 Set the entry size in the header
            lr     \wrkr,\nr          # +26 Work register contains the number of entries
            mh     \wrkr,6(\tblr)     # +24 Calculate the total table entry size
            al     \wrkr,0(\tblr)     # +20 Calculate the total table size
            alr    \wrkr,\tblr        # +16 Caluclate the byte following the table
            st     \wrkr,8(\tblr)     # +14 Save the end of the table in the header
            sr     \wrkr,\wrkr        # +10 Clear the work register
            st     \wrkr,12(\tblr)    # +8  Clear the unused word
            b      .+6-\b(\br)        # +4  Branch around the constant
            .hword 16
            .endm

            .macro tblbldg tblr:req nr:req sr:req hdr:req wrkr:req
            lghi   \wrkr,16           # Work register contains the header size
            algr   \wrkr,\hdr         # Work register is the total header size
            st     \wrkr,0(\tblr)     # Set the header size in the header
            st     \sr,4(\tblr)       # Set the entry size in the header
            lgr    \wrkr,\nr          # Work register contains the number of entries
            mh     \wrkr,6(\tblr)     # Calculate the total table entry size
            al     \wrkr,0(\tblr)     # Calculate the total table size
            algr   \wrkr,\tblr        # Caluclate the byte following the table
            stg    \wrkr,8(\tblr)     # Save the end of the table in the header
            .endm

 # tblnext/tblnextg -  Continue the scanning of the table
 #
 #  Macro Parameters:
 #       r      Register into which the address is loaded (required)
 #       tblr   Register pointing to the table header (required)
 #       ntryr  Register pointint to the current entry being scanned
 #       next   Provides a symbol for passing control on the next scan cycle
 #              (default 1b) 
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro tblnext tblr:req ntryr:req next=1b br=13 b=0b
            al     \ntryr,4(\tblr)  # Point to the next entry
            b      \next-\b(\br)    # See, if past end of table
2:
            .endm

            .macro tblnextg tblr:req ntryr:req next=1b br=13 b=0b
            algf   \ntryr,4(\tblr)  # Point to the next entry
            j      \next            # See, if past end of table
2:
           .endm

 # tblscan/tblscang -  Start the scan of a table 
 #
 #  Macro Parameters:
 #       tblr   Register pointing to the table header (required)
 #       ntryr  Register pointing to the current entry being scanned
 #       next   Provides a symbol for passing control on the next scan cycle
 #              (default 1) 
 #       eot    Symbol to which control is passed upon completing the scan
 #              (default 2f)
 #       br     Current active base register (default 13)
 #       b      Current active base symbol (default 0b)

            .macro tblscan tblr:req ntryr:req eot=2f next=1 br=13 b=0b
            lr     \ntryr,\tblr     # Get the table start
            al     \ntryr,0(\tblr)  # Locate the first entry
\next:      cl     \ntryr,8(\tblr)  # Beyond end of table?
            bnl     \eot-\b(\br)    # ..Yes, end scan
            .endm

            .macro tblscang tblr:req ntryr:req eot=2f next=1 br=13 b=0b
            lgr    \ntryr,\tblr     # Get the table hdr
            algf   \ntryr,0(\tblr)  # locate the first entry
\next:      clg    \ntryr,8(\tblr)  # Beyond end of table?
            jnl    \eot             # ..Yes, end
            .endm

 # tblsize - Assign a symbol the calculated table size
 #
 #  Macro Parameters:
 #       name     Symbol whose value is assigned the calculated table size
 #                (required)
 #       entry    Size of each table entry (required)
 #       entries  The number of entries in the table (required)
 #       header   Size of the header extension (required)

           .macro tblsize name:req entry:req entries:req header:req
\name = 16+(\entry*\entries)+\header
           .endm

.endif # .ifndef .Ltable_S
