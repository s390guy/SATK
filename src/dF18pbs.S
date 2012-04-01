.ifndef .Ldf18pbs_S
.Ldf18pbs_S = 1
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

 # Host Resource Access Facility (DIAGNOSE X'F18') Parameter Block Definitions
 # and basic macros
 #
 #  .diag   Rx,Ry,0xF18
 #
 # DIAGNOSE X'F18' Register Usage:
 #   Rx    Subcode in even register of an even/odd pair
 #   Rx+1  Operations Flags (see CPB Operation Capability Flags) in rightmost
 #         16 bits of the odd register in the Rx even/odd pair
 #   Ry    Parameter Block address.  Rx Even/odd pair determines structure and
 #         usage of the parameter block

.Ldf18query = 0  # Query Subcode
.Ldf18cs    = 1  # Host Socket Access in TCPIP instruction compatility mode 
.Ldf18cf    = 2  # Host File System Access in NFILE instruction compatibility mode
.Ldf18ns    = 3  # Host Socket Access in native mode
.Ldf18nf    = 4  # Host File System Access in native mode

 # Capability Parameter Block (CPB) Displacements
.Ldf18cpb  = 0   #        Start of the CPB
.Ldf18IPv6 = 0   # .byte  IPv6 Stack Capabilities (see IP Capability Flags)
.Ldf18IPv4 = 1   # .byte  IPv4 Stack Capabilities (see IP Capability Flags)
.Ldf18hrsc = 2   # .byte  Host Resources supported by DIAGNOSE X'F18' and modes
.Ldf18host = 3   # .byte  Host Platform (see Platform Flags)
.Ldf18copt = 4   # .hword Compatiblity Mode options (see Operations Capability Flags)
.Ldf18nopt = 6   # .hword Native Mode options (see Operations Capability Flags)
.Ldf18maxs = 8   # .hword Maximum number of shadow sockets supported
.Ldf18cpb_len = 16  # Total length of the CPB

 # CPB IP Capability Flags 
 #   Applies to .Ldf18IPv6 and .Ldf18IPv4 CPB fields
.Ldf18IPdg = 0x02  # Datagram sockets supported
.Ldf18IPsg = 0x01  # Stream sockets supported

 # CPB Operations Capability Flags
 #   Applies to .Ldf18copt, .Ldf18nopt and DIAGNOSE Rx+1 rightmost 16 bits
 # Byte 0 of the options field:
.Ldf18resv = 0xFF  # Reserved, must be zeros
 # Byte 1 of the options field:
.Ldf18trns   = 0x80   # Hercules code page ASCII/EBCDIC translation supported/requested
                      # otherwise compatibility mode translation available/requested
.Ldf18real   = 0x40   # Real addresses supported/used in Parameter Block
.Ldf18prim   = 0x20   # Primary virtual addresses supported/used in Parameter Block
.Ldf18alet   = 0x10   # ALET translation supported/used in Parameter Block
.Ldf18vbit   = 0x0F   # Bits used for DIAGNOSE version control
.Ldf18curv   = 0x01   # Current version of the DIAGNOSE available/required
 # Note .Ldf18real, .Ldf18prim and .Ldf18alet mutually exclusive in DIAGNOSE Rx+1

 # CPB Platform Flags
 #   Applies to .Ldf18host
.Ldf18lfs    = 0x80  # Host supports large file system
.Ldf18hbit   = 0x7F  # Isolates host plaftorm bits
.Ldf18unkn   = 0x00  # Host platform is unknown
.Ldf18lin    = 0x01  # Host platform is Linux
.Ldf18win    = 0x02  # Host platform is Microsoft Windows
.Ldf18sol    = 0x03  # Host platform is Oracle Solaris or OpenSolaris
.Ldf18osx    = 0x04  # Host plaftorm is Apple OS/X
.Ldf18bsd    = 0x05  # Host platform is FreeBSD
.Ldf18aix    = 0x06  # Host platform is IBM AIX

 # File Operation Compatibility Parameter Block (FOCPB) Displacements
.Ldf18focpb  = 0     #        Start of the FOCPB
.Lfcorstrt   = 0     # .long  Restart State (zero implies no restart required)
.Lfcoper     = 4     # .long  File Operation (see File Operations)
.Lfcohnba    = 8     # .long  Host file descriptor or buffer address
.Lfcoarg1    = 12    # .long  Argument 1 depends on operation
.Lfcoarg2    = 16    # .long  Argument 2 depends on operation
.Lfcrsv      = 20    #        4 bytes reserved - MUST NOT BE USED BY THE PROGRAM
.Lfcavail    = 24    #        36 bytes available for program use
.Lfcorsult   = 60    # .long  Result (>=0 - success, <0 - errno * -1)
.Lfcopb_len  = 64    # Length of the FOCPB

 # File Operations
 #   Applies to .Lfcoper
.Lfco_rename = 0     # Rename a host file
.Lfco_unlink = 1     # Unlink a file (platform specific operation)
.Lfco_open   = 2     # Open a file (see File Open flags)
.Lfco_orphan = 3     # Perform an orphan file close based upon the file name
.Lfco_read   = 4     # Read from an open file
.Lfco_write  = 5     # Write to an open file
.Lfco_seek   = 6     # Seek within an open file
.Lfco_commit = 7     # Complete pending writes for an open file
.Lfco_close  = 8     # Close an open file
.Lfco_mode   = 9     # Set text translation mode for an open file (platform sensitive)

 # File Open Operation Flags 
 #   Applies to .Lfcoarg1
.Lfco_excl   = 0x80  # Open fails if the file exists when creating a new file
.Lfco_creat  = 0x40  # Create a new file if it does not exist
.Lfco_trunc  = 0x20  # If the file exists, truncate to zero length when opening.
.Lfco_append = 0x10  # Append writes to end of file regardless of seeks
.Lfco_text   = 0x04  # Treat file data as textual (use .Lfco_mode for translation)
.Lfco_rdwr   = 0x02  # Opens the file for both reading and writing
.Lfco_wronly = 0x01  # Open the file for writing only
.Lfco_rdonly = 0xFC  # Logical and mask to enforce opening the file for reading only
.Lfco_binary = 0xFB  # Logical and mask to enforce binary treatment of file data

 # File Seek Operation Origin
.Lfco_skbeg  = 0     # Seek from the begining of the file
.Lfco_skcur  = 1     # Seek from the current file position
.Lfco_skend  = 2     # Seek from the end of the file

 # Socket Operation Compatibility Parameter Block (SOCPB) Displacments
.Ldf18socpb  = 0     #        Start of the SOCPB
.Lscfrstrt   = 0     # .long  Restart State (zero implies no restart required)
.Lscfrlen    = 4     # .long  Host buffer length
.Lscrsv1     = 8     #        4 bytes reserved - MUST NOT BE USED BY THE PROGRAM
.Lscfunc     = 12    # .long  Socket Function (0==Host Request, 1==Host Response)
.Lscfhrslt   = 16    # .long  Host response funtion result
.Lscfreqa    = 20    # .long  Reguest function buffer address
.Lscfrspa    = 24    # .long  Response function buffer address
.Lscosock    = 28    # .hword Shadow number
.Lscavail1   = 30    #        1 byte available for program use
.Lscoper     = 31    # .byte  Host request socket operation (see Socket Operations)
.Lscoarg1    = 32    # .long  Socket operation argument 1 depends on .Lscoper
.Lscoarg2    = 36    # .long  Socket operation argument 2 depends on .Lscoper
.Lscavail2   = 40    #        16 bytes available for program use
.Lscrsv2     = 56    #        4 bytes reserved - MUST NOT BE USED BY THE PROGRAM
.Lscfrsult   = 60    # .long  Socket function result ( 0 == success, -1 == failure)
.Lsocpb_len  = 64    # Length of SOCPB

 # SOCKADDR_IN Displacements
.Lsockin     = 0     #        Start of the SOCKADDR_IN structure
.Lsockin_fam = 0     # .hword Address Family, always X'0002'
.Lsockin_port= 2     # .hword TCP port number
.Lsockin_addr= 4     # .long  IPv4 address
.Lsockin_len = 16    # Length of the SOCKADDR_IN structure

 # Socket Operations
 #   Applies to .Lscoper
.Lsco_init   = 1     # Initialize socket operations
.Lsco_sockerr= 2     # Return a socket's host error for its previous error
.Lsco_error  = 3     # Return the previous failing operation's error
.Lsco_ghbn   = 4     # Perform GETHOSTBYNANE operation
.Lsco_socket = 5     # Create a guest shadow socket
.Lsco_bind   = 6     # Bind a shadow socket to an address and port
.Lsco_connect= 7     # Establish a connection from the shadow socket
.Lsco_listen = 8     # Listen on the shadow socket for connections
.Lsco_accept = 9     # Have the listening socket spawn a new socket for a connection
.Lsco_send   = 10    # Send data on a connection to a remote partner
.Lsco_recv   = 11    # Receive data on a connection from a remote partner
.Lsco_close  = 12    # Terminate socket operations by this partner
.Lsco_e2a    = 13    # Translate EBCDIC data to ASCII
.Lsco_a2e    = 14    # Translate ASCII data to EBCDIC
.Lsco_ioctl  = 15    # Perform a device IOCTL function on the host socket
.Lsco_getname= 16    # Returns a SOCKADDR_IN structure for the socket
.Lsco_select = 17    # Perform guest synchronous I/O multiplexing on sockets

 # Select Sub-operation codes
.Lsco_sinit  = 0     # Initialize guest synchronous I/O multiplexing
.Lsco_siread = 1     # Provide a read event File Descriptor Set
.Lsco_siwrite= 2     # Provide a write event File Descriptor Set
.Lsco_siexctn= 3     # Provide an exception event File Descriptor Set
.Lsco_syncio = 4     # Perform host synchronous I/O multiplexing for provided sockets
.Lsco_srread = 5     # Retrieve the resulting read event File Descriptor Set
.Lsco_srwrite= 6     # Retrieve the resulting write event File Descriptor Set
.Lsco_srexctn= 7     # Retrieve the resulting exception event File Descriptor Set
.Lsco_sfini  = 8     # Reles the synchronous I/O multiplexing resources

 # df18cpb - Generate Capability Parameter Block
 #  Macro Parameters:
 #      name     Symbol assigned to the generated parameter block (required)

        .macro df18cpb name:req
        .align 8
\name:  .octa  0
        .endm

 # df18qry - Query DIAGNOSE X'F18' Capability
 #  Macro Parameters:
 #      cpbr     Register pointing to the Capability Parameter Block (required)
 #      wrkpr    Even register of even/odd pair used for DIAGNOSE X'F18'

        .macro df18qry cpbr:req wrkpr=0
        sr      \wrkpr,\wrkpr       # Set subcode for Capability Query
        diag    \wrkpr,\cpbr,0xF18  # Issue Query
        .endm

.endif  # .ifndef .Ldf18pbs_S scope



