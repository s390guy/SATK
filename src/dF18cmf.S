.ifndef .Ldf18cmf_S
.Ldf18cmf_S = 1
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

 # Macros facilitating use of Hercules Host Resource Access Facility for host file 
 # system access in compatibility mode in an ABI compliant environment.  Macros
 # assume ABI register usage.
 #
 # Note: These macros make use of the available fields within the FOCPB to simplify
 # usage.  The FOCPB then becomes analogous to a DTF (in DOS/VS) or DCB (in MVS) for
 # host file access.  Such usage may not be appropriate for all scenarios.
 #

 # Usage of the FOCPB available fields:
.Lcmfcode = .Lfcavail     # Subcode for Compatibility Mode Host File Access (Rx)
.Lcmfopts = .Lfcavail+4   # Operational options used for this files access (Rx+1)
.Lcmfhndl = .Lfcavail+8   # File handle provided on successful open

 # focpb - Create an FOCPB for use with these macros
 #  Macro Parameters:
 #      name     Name of the FOCPB being created
 #      options  Operational options to be used with the file

        .macro focpb name:req options:req ver=0x1
        .align 8
\name:  .octa  0
        .long  0,0,.Ldf18cf,(\options)|\ver
        .octa  0
        .octa  0
        .endm

 # Register usage by macros:
 #  R0 and R1 used for DIAGNOSE Rx and Rx+1 operands, respectively

 # hracf - Issue a Compatibility Mode Host File System Access
 # Restart is automatically handled by the macro.
 #  Macro Parameters
 #      pbr      Register pointing to the DIAGNOSE X'F18' FOCPB
 #      wrkpr    Pair of even/odd registers used by the access
 #      br       Local base register (default 13 for ABI standard usage)
 #      b        Local base (default 0b)

        .macro hracf focpbr:req wrkpr:req br=13 b=0b
    .ifndef .Ldf18pbs_S    # Have parameter block definitions been provided?
        .error "dF18pbs.S must be included"
    .endif
        sr     \wrkpr,\wrkpr                        # Set register to zero
        st     \wrkpr,.Lfcorstrt(\focpbr)           # Indicate new operation
        lm     \wrkpr,\wrkpr+1,.Lcmfcode(\focpbr)   # Set subcode and options
        diag   \wrkpr,\focpbr,0xF18                 # Issue DIAGNOSE
        oc     .Lfcorstrt(4,\focpbr),.Lfcorstrt(\focpbr)  # Need to restart?
        bnz    .-10-\b(\br)                         # ..Yes, try again to finish
        .endm

 # cfbin - Set the file access mode to binary
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      nop      If specified 'nop=yes', setup but do not close (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: previous mode - 4==binary, 8=text
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfbin focpbr:req nop=no resultr fail
        mvc    .Lfcohnba(4,\focpbr),.Lcmfhndl(\focpbr) # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_mode          # Set for the setmode operation
        sr     0,0                                     # Set register to zero
        st     0,.Lfcoarg1(\focpbr)                    # Set for binary mode 
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                   # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfcheck - Check the results of an operation
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      resultr  Register used to provide the result for testing (required)
 #      fail     Symbol to which control will pass on a failure (optional)
 #      eof      Symbol to which control is passed on eof (optional)
 #      br       Local base register (default 13 for ABI standard usage)
 #      b        Local base (default 0b)

        .macro cfcheck focpbr:req resultr:req fail eof br=13 b=0b
        icm    \resultr,0xF,.Lfcorsult(\focpbr)     # Ckeck result?
    .ifnb \fail
        bc     4,\fail-\b(\br)                      # ..If fail (<0), deal with it
    .endif
    .ifnb \eof
        bc     8,\eof-\b(\br)                       # ..If EOF (=0), deal with that
    .endif
        .endm

 # cfclose - Close the file
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      nop      If specified 'nop=yes', setup but do not close (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: zero
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfclose focpbr:req nop=no resultr fail
        mvc    .Lfcohnba(4,\focpbr),.Lcmfhndl(\focpbr) # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_close         # Set for the close operation
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                   # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfcommit - Complete pending open file writes
 #  Macro Parameters:
 #      focbpr   Register pointing to the FOCPB area (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not read the file
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: zero
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)
 
        .macro cfcommit focpbr:req nop=no resultr fail
        mvc    .Lfcohnba(4,\focpbr),.Lcmfhndl(\focpbr) # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_commit        # Set for the commit operation
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                   # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif        
        .endm  

 # cfinit - Dynamically initialize the FOCPB for use with these macros
 #  Macro Parameters:
 #      focbpr   Register pointing to the FOCPB area (required)
 #      optionsr Register containing the operatoinal options for this file
 #      wrkr     Work register to use (default 0)
 #      clear    If specified 'clear=yes' the FOCPB area will be cleared (default no)

        .macro cfinit focpbr:req optionsr:req wrkr=0 clear=no
    .ifc \clear,yes
        mvi    0(\focpbr),0x00                      # Clear FOCPB...
        mvc    1(.Lfcopb_len-1,\focpbr),0(\focpbr)  # ...to zeros
        mvi    .Lcmfcode+3(\focpbr),.Ldf18cf        # Set the subcode
    .else
        la     \wrkr,.Ldf18cf                       # Determine the subcode
        st     \wrkr,.Lcmfcode(\focpbr)             # Set it in the FOCPB
    .endif
        st     \optionsr,.Lcmfopts(\focpbr)         # Set the operational options
        .endm

 # cfoclose - Close an orphan open file using its name
 #  Macro Parmeters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      namer    Register pointing to a consecitive null terminated EBCDIC string
 #               identfying the existing file being inlinked (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not unlink the file
 #               (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: zero
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfoclose focpbr:req namer:req nop=no resultr fail
        st     \namer,.Lfcohnba(\focpbr)         # Identify file to be closed
        mvi    .Lfcoper+3(\focpbr),.Lfco_orphan  # Set for the orphan close operation
     .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0             # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfopen - Open a host file
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      namer    Register pointing to a NULL terminated EBCDIC file name string
 #               (required)
 #      flags    Open flags to be used by the file (default 0x00)
 #      perms    Permissions to be used for the file (default 0x00)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not open the file
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: Host file handle
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)
 #
 # Note: flags set to 0x00 implies "read only from an existing binary file"
 # If nop=yes is specified, bytes 48-51 of the FOCPB must be set by the program
 # to the returned file handle from the successful cfopen macro for use by
 # cfbin, cfclose, cfread, cfseek, cftext and cfwrite.

        .macro cfopen focpbr:req namer:req flags=0x00 perms=0x00 nop=no resultr fail
    .ifnb \flags
        mvi    .Lfcoarg1+3(\focpbr),\flags          # Set the open flags
    .endif
    .ifnb \perms
        mvi    .Lfcoarg2+3(\focpbr),\perms          # Set the file permissions
    .endif
        st     \namer,.Lfcohnba(\focpbr)            # Point to the file name
        mvi    .Lfcoper+3(\focpbr),.Lfco_open       # Set the open operation
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
        st     \resultr,.Lcmfhndl(\focpbr)          # Save the file handle for later
    .endif
        .endm

 # cfread - Read from an open file
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      iobufr   Register containing the I/O buffer area (required)
 #      bytesr   Register containin the maximum number of bytes to read (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not read the file
 #               (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: number of bytes read from the file
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)
 #      eof      Symbol to which control is passed on eof (optional)

        .macro cfread focpbr:req iobufr:req bytesr:req nop=no resultr fail eof
        mvc    .Lfcoarg1(4,\focpbr),.Lcmfhndl(\focpbr)  # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_read         # Set for the read operation
        st     \iobufr,.Lfcohnba(\focpbr)             # Set the I/O buffer address
        st     \bytesr,.Lfcoarg2(\focpbr)             # Set bytes to read
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                  # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail,eof=\eof
    .endif
        .endm

 # cfrename - rename a non-open file
 #  Macro Parmeters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      stringr  Register pointing to two consecitive null terminated EBCDIC strings
 #               identfying the existing file name and new file name, respectively
 #      nop      If specified as 'nop=yes', setup FOCPB but do not rename the file
 #               (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: zero
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfrename focpbr:req stringr:req nop=no resultr fail
        st     \stringr,.Lfcohnba(\focpbr)       # Identify file to be renamed.
        mvi    .Lfcoper+3(\focpbr),.Lfco_rename  # Set for the rename operation
     .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0            # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfseek - Seek to a position within an open file
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      bytesr   Register containin the maximum number of bytes to read (required)
 #      originr  Register with: 0==file start, 1==current, 2==file end (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not seek (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: new position relative to the file start
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)      

        .macro cfseek focpbr:req bytesr:req originr:req nop=no resultr fail
        mvc    .Lfcohnba(4,\focpbr),.Lcmfhndl(\focpbr)  # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_seek         # Set for the read operation
        st     \bytesr,.Lfcoarg1(\focpbr)             # Set bytes to read
        st     \originr,.Lfcoarg2(\focpbr)            # Set seek origin
     .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                  # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cftext - Set the file access mode to text
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      nop      If specified 'nop=yes', setup but do not close (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: previous mode - 4==binary, 8=text
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cftext focpbr:req nop=no resultr fail
        mvc    .Lfcohnba(4,\focpbr),.Lcmfhndl(\focpbr) # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_mode          # Set for the setmode operation
        la     0,4                                     # Set register to 4
        st     0,.Lfcoarg1(\focpbr)                    # Set for text mode 
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                   # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfunlink - Unlink a non-open file
 #  Macro Parmeters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      stringr  Register pointing to a consecitive null terminated EBCDIC string
 #               identfying the existing file being inlinked (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not unlink the file
 #               (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: zero
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfunlink focpbr:req stringr:req nop=no resultr fail
        st     \stringr,.Lfcohnba(\focpbr)       # Identify file to be renamed.
        mvi    .Lfcoper+3(\focpbr),.Lfco_unlink  # Set for the unlink operation
     .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0             # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

 # cfwrite - Write to an open file
 #  Macro Parameters:
 #      focpbr   Register pointing to the FOCPB used for this operation (required)
 #      iobufr   Register containing the I/O buffer area (required)
 #      bytesr   Register containing the number of bytes to write (required)
 #      nop      If specified as 'nop=yes', setup FOCPB but do not read the file
 #               (default no)
 #      resultr  Result register used to test results (required if nop=no)
 #               Successful result: Number of bytes written to the file
 #      fail     Symbol to where control should be passed on a failure (required 
 #               if nop=no)

        .macro cfwrite focpbr:req iobufr:req bytesr:req nop=no resultr fail
        mvc    .Lfcoarg1(4,\focpbr),.Lcmfhndl(\focpbr)  # Set the file handle
        mvi    .Lfcoper+3(\focpbr),.Lfco_write          # Set for the read operation
        st     \iobufr,.Lfcohnba(\focpbr)             # Set the I/O buffer address
        st     \bytesr,.Lfcoarg2(\focpbr)             # Set bytes to write
    .ifnc \nop,yes
        hracf  focbr=\focpbr,wrkpr=0                  # Do the operation
        cfcheck focpbr=\focpbr,resultr=\resultr,fail=\fail
    .endif
        .endm

.endif  # .ifndef .Ldf18cmf_S
