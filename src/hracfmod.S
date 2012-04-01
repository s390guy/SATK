.ifndef .Lhracfmod_S
.Lhracfmod_S = 1
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

 # This module provides a ABI callable interface for HRA Compatibility Mode File 
 # Access

 # Dependencies:
 #    ABI.S      - for ABI macros
 #    dF18cmf.S  - for Compatibility mode host file access
 #    dF18pbs.S  - for DIAGNOSE X'F18' parameter blocks 
 #    program.S  - for dwait macro
 #
 # Optional:
 #    hracfmac.S - Tailoring of this module
 #
 # This function displays an ASCII or EBCDIC message on the 
 # hardware maintenance console.
 #
 # Register Usage:
 #   ABI Call Parameters:
 #          %r2  = Operation Number
 #          %r3  = FOCPB address
 #          %r4  = Parameter 1
 #          %r5  = Parameter 2
 #          %r6  = Parameter 3
 #
 #   ABI Return Value:
 #          %r2  = Host access return value
 #
 #                %r2       %r4         %r5         %r6           %r2
 #   Operation  Number    Parm 1      Parm 2       Parm 3        Return
 #     rename     0       pointer                                result
 #     unlink     1       filename                               result
 #     open       2       filename    flags        permissions   result
 #     oclose     3       filename                               result
 #     read       4       buffer      count                      bytes read/result
 #     write      5       buffer      count                      bytes written/result
 #     seek       6       offset      origin                     new position/result
 #     commit     7                                              result
 #     close      8                                              result
 #     setbin     9                                              prev mode/result
 #     settext   10                                              prev mode/result
 #     init      11       options
 #     errno     12       result                                 pointer to name
 #     dump      13
 #
 #   Processing:
 #          %r0,%r1 = wrkpr register pair
 #          %r8/%r9 = wrkpr register pair

.ifndef .Lhracf_sw_all   # If module operations have not been set
.Lhracf_sw_all     = 1   # Enable all operations 
.Lhracf_close_sw   = 1   # Enable close
.Lhracf_dump_sw    = 1   # Enable dump
.Lhracf_errno_sw   = 1   # Enable errno
.Lhracf_init_sw    = 1   # Enable init
.Lhracf_commit_sw  = 1   # Enable commit
.Lhracf_oclose_sw  = 1   # Enable oclose
.Lhracf_open_sw    = 1   # Enable open
.Lhracf_read_sw    = 1   # Enable read
.Lhracf_rename_sw  = 1   # Enable rename
.Lhracf_seek_sw    = 1   # Enable seek
.Lhracf_setbin_sw  = 1   # Enable set binary mode
.Lhracf_settext_sw = 1   # Enable set text mode
.Lhracf_unlink_sw  = 1   # Enable unlink
.Lhracf_write_sw   = 1   # Enable write
.endif
            .align 2

            abi_func .Lhracf

 # Set up my literals:
 #.Lhracf_oper:.long  13
.Lhracf_oper: .long ((.Lfracf_tbl_end-.Lfracf_tbl)/4)-1

.if .Lhracf_init_sw
 # init operation literal
.Lhracf_init_mask: .long 0x0000000F     # Mask to isolate version
.endif
.if .Lhracf_dump_sw
                  disptr ascii=.Lhracf_tr   # ASCII Hexadecimal Translate table
.Lhracf_focpb:    .ascii "FOCPB at:   "
.Lhracf_fcorstrt: .hword 0
                  .ascii " +0 FOCRSTRT"
.Lhracf_fcoper:   .hword 4
                  .ascii " +4 FCOPER  "
.Lhracf_fcohnba:  .hword 8
                  .ascii " +8 FCOHNBA "
.Lhracf_fcoarg1:  .hword 12
                  .ascii "+12 FCOARG1 "
.Lhracf_fcoarg2:  .hword 16
                  .ascii "+16 FCOARG2 "
.Lhracf_cmfcode:  .hword 24
                  .ascii "+24 cmfcode "
.Lhracf_cmfopts:  .hword 28
                  .ascii "+28 cmfopts "
.Lhracf_cmfhndl:  .hword 32
                  .ascii "+32 cmfhndl "
.Lhracf_fcorslt:  .hword 60
                  .ascii "+60 FCORSULT"
.endif

 # Set up my local stack usage here
.if .Lhracf_dump_sw   # These areas are required by the dump operation
            dispwork name=.Lhracf_dump_work,stack=yes
            flong name=.Lhracf_dump_binary
            fbytes name=.Lhracf_dump_lable,number=12
            freserve size=1
            fbytes name=.Lhracf_dump_value,number=10
            fhere name=.Lhracf_dump_msgend
.Lhracf_msg_len = .Lhracf_dump_msgend-.Lhracf_dump_lable
.endif
            abi_push

            ltr   1,2                      # Is the operation negative?
            bm    .Lhracf_bad_oper-0b(13)  # ..Yes, that's bad
            cl    1,.Lhracf_oper-0b(13)    # Past the maximum operation?
            bh    .Lhracf_bad_oper-0b(13)  # ..Yes, that's also bad
            
            # Valid Operation
            sll   1,2                      # Get displacement into branch table
            b     .+4-0b(1,13)             # Branch to the proper routine
.Lfracf_tbl:
.if .Lhracf_rename_sw
            b     .Lhracf_rename-0b(13)    # ..rename
.else
            b     .Lhracf_bad_oper-0b(13)  # rename not enabled
.endif
.if .Lhracf_unlink_sw
            b     .Lhracf_unlink-0b(13)    # ..unlink
.else
            b     .Lhracf_bad_oper-0b(13)  # unlink not enabled
.endif
.if .Lhracf_open_sw
            b     .Lhracf_open-0b(13)      # ..open
.else
            b     .Lhracf_bad_oper-0b(13)  # open not enabled
.endif
.if .Lhracf_oclose_sw
            b     .Lhracf_oclose-0b(13)    # ..oclose
.else
            b     .Lhracf_bad_oper-0b(13)  # oclose not enabled
.endif
.if .Lhracf_read_sw
            b     .Lhracf_read-0b(13)      # ..read
.else
            b     .Lhracf_bad_oper-0b(13)  # read not enabled
.endif
.if .Lhracf_write_sw
            b     .Lhracf_write-0b(13)     # ..write
.else
            b     .Lhracf_bad_oper-0b(13)  # read not enabled
.endif
.if .Lhracf_seek_sw
            b     .Lhracf_seek-0b(13)      # ..seek
.else
            b     .Lhracf_bad_oper-0b(13)  # read not enabled
.endif
.if .Lhracf_commit_sw
            b     .Lhracf_commit-0b(13)    # ..commit
.else
            b     .Lhracf_bad_oper-0b(13)  # commit not enabled
.endif
.if .Lhracf_close_sw
            b     .Lhracf_close-0b(13)     # ..close
.else
            b     .Lhracf_bad_oper-0b(13)  # close not enabled
.endif
.if .Lhracf_setbin_sw
            b     .Lhracf_setbin-0b(13)    # ..set binary mode
.else
            b     .Lhracf_bad_oper-0b(13)  # set binary mode not enabled
.endif
.if .Lhracf_settext_sw
            b     .Lhracf_settext-0b(13)   # ..set text mode
.else
            b     .Lhracf_bad_oper-0b(13)  # set text mode not enabled
.endif
.if .Lhracf_init_sw
            b     .Lhracf_init-0b(13)      # ..init
.else
            b     .Lhracf_bad_oper-0b(13)  # init not enabled
.endif
.if .Lhracf_errno_sw
            b     .Lhracf_errno-0b(13)     # ..errno
.else
            b     .Lhracf_bad_oper-0b(13)  # errno not enabled
.endif
.if .Lhracf_dump_sw
            b     .Lhracf_dump-0b(13)      # ..dump
.else
            b     .Lhracf_bad_oper-0b(13)  # errno not enabled
.endif
.Lfracf_tbl_end:
            
.if .Lhracf_close_sw
.Lhracf_close: # Close the FOCPB file
            cfclose focpbr=3,nop=yes       # Setup close
            b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif
            
.if .Lhracf_commit_sw
.Lhracf_commit: # Commit pending writes to the FOCPB file
            cfcommit focpbr=3,nop=yes      # Setup commit
            b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_dump_sw
.Lhracf_dump:  # Need to implement this
            la   8,.Lhracf_dump_work(15)   # Point to work area on stack
            l    9,.Lhracf_tr-0b(13)       # Point to the translate table
            lr   10,3                      # Preserve FOCPB pointer

            # Display the FOCPB address
            st   10,.Lhracf_dump_binary(15) # Set the FOCPB address for display
            mvi  .Lhracf_dump_lable(15),0x20 # Move an ascii space
            mvc  .Lhracf_dump_lable+1(.Lhracf_msg_len-1,15),.Lhracf_dump_lable(15)
            dispfx dest=.Lhracf_dump_value,src=.Lhracf_dump_binary,wpr=8,tpr=9,stack=yes
            mvc  .Lhracf_dump_lable(12,15),.Lhracf_focpb-0b(13)
            dispap msg=.Lhracf_dump_lable,len=.Lhracf_msg_len,stack=yes

            # Display the FOCPB fields:
            la     11,.Lhracf_fcorstrt-0b(13)# Point to the field definition
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_fcoper-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_fcohnba-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_fcoarg1-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_fcoarg2-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_cmfcode-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_cmfopts-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_cmfhndl-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            la     11,.Lhracf_fcorslt-0b(13)
            bas    4,.Lhracf_hex-0b(13)      # Call the display routine
            b      .Lhracf_ret-0b(13)        # Return to the caller
.endif

.if .Lhracf_errno_sw
.Lhracf_errno:  # Need to implement this
  # R7 = table start
  # R8 = increment
  # R9 = compare (when R7<=R9, branch is taken, otherwise not)
  # Falling through implies not found
            lm   7,9,.Lhracf_errno_table-0b(13)
.Lhracf_errno_next:
            ch     4,0(7)                        # Is this the errno?
            be     .Lhracf_errno_found-0b(13)    # ..Yes, found it
            bxle   7,8,.Lhracf_errno_next-0b(13) # ..No, try again
  # If here, R7 points to the last default entry in the table ("UNKNOWN")
.Lhracf_errno_found:
            la     2,2(7)
            b      .Lhracf_ret-0b(13)        # Return to the caller
.endif

.if .Lhracf_init_sw
.Lhracf_init:  # Initialize the FOCPB for function usage
            mvi    0(3),0x00               # Set the first byte to zero
            mvc    1(.Lfcopb_len-1,3),1(3) # ..and zero the rest of the FOCPB
            mvi    .Lfcoper+3(3),11        # Indicate "init" last operation
            la     0,.Ldf18cf              # Specify my DIAGNOSE X'F18' subcode
            st     0,.Lcmfcode(3)          # Set it in the FOCPB
            lr     1,4                     # Get the options
            n      1,.Lhracf_init_mask-0b(13) # Isolate and test if version present
            bnz    .Lhracf_init_ver-0b(13) # ..present, store by operational options
            la     4,1(4)                  # ..missing, forcer version to 1
.Lhracf_init_ver:  # Store my operational options
            st     4,.Lcmfopts(3)          # Set the operational options in FOCPB
            sr     2,2                     # Return success
            b      .Lhracf_ret-0b(13)      # Return to the caller
.endif

.if .Lhracf_oclose_sw
.Lhracf_oclose: # Perform an orphan close with the FOCPB
            cfoclose focpbr=3,namer=4,nop=yes  # Setup oclose
            b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_open_sw
.Lhracf_open:  # Open the file
            st    2,.Lfcoper(3)            # Set the open operation
            stm   4,6,.Lfcohnba(3)         # Set the file name pointer
            hracf focpbr=3,wrkpr=0         # Open the file

            # Check the open, if it failed exit with the results
            cfcheck focpbr=3,resultr=2,fail=.Lhracf_ret
            st     2,.Lcmfhndl(3)          # Save the handle
            b      .Lhracf_ret-0b(13)      # ..and return
.endif

.if .Lhracf_read_sw
.Lhracf_read:  # Read from the open file
           cfread focpbr=3,iobufr=4,bytesr=5,nop=yes
           b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_rename_sw
.Lhracf_rename: # Rename a file using the FOCPB
           cfrename focpbr=3,stringr=4,nop=yes         # Setup the rename
           b     .Lhracf_do_oper-0b(13)                # ..and do it
.endif

.if .Lhracf_seek_sw
.Lhracf_seek:
           cfseek focpbr=3,bytesr=4,originr=5,nop=yes  # Setup the seek
           b     .Lhracf_do_oper-0b(13)                # ..and do it
.endif

.if .Lhracf_setbin_sw
.Lhracf_setbin:
           cfbin focpbr=3,nop=yes         # Setup for binary mode
           b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_settext_sw
.Lhracf_settext:
           cftext focpbr=3,nop=yes        # Setup for text mode
           b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_unlink_sw
.Lhracf_unlink:
           cfunlink focpbr=3,stringr=4,nop=yes         # Setup for file unlink
           b     .Lhracf_do_oper-0b(13)                # ..and do it
.endif

.if .Lhracf_write_sw
.Lhracf_write:
           cfwrite focpbr=3,iobufr=4,bytesr=5,nop=yes
           b     .Lhracf_do_oper-0b(13)   # ..and do it
.endif

.if .Lhracf_dump_sw  # This subroutine used by dump operation
 # Format a fielf of FOCPB and print it in hexadecimal
 # Register usage:
 #    1 - used as a work register
 #    4 - used as a return register
 #    8 - points to the display work area on the stack
 #    9 - points to the tranlsate table to use
 #   10 - points to FOCPB
 #   11 - points to the field definition
 #   
.Lhracf_hex:   # Format a field of the FOCPB and print it in hexadecimal
            lh   1,0(11)         # Locate the displacement of the FOCPB field
            l    1,0(1,10)       # Fetch the field being displayed   
            st   1,.Lhracf_dump_binary(15) # Set the data being displayed
            mvi  .Lhracf_dump_lable(15),0x20 # Move an ascii space
            mvc  .Lhracf_dump_lable+1(.Lhracf_msg_len-1,15),.Lhracf_dump_lable(15)
            dispfx dest=.Lhracf_dump_value,src=.Lhracf_dump_binary,wpr=8,tpr=9,stack=yes
            mvc  .Lhracf_dump_lable(12,15),2(11)
            lr   11,4            # Save the return register
            dispap msg=.Lhracf_dump_lable,len=.Lhracf_msg_len,stack=yes
            br   11
.endif  # .if .Lhracf_dump_sw scope

.Lhracf_bad_oper:
           la   2,22                      # Return EINVAL for bad operation
           lnr  2,2                       # Turn it into -22
           b    .Lhracf_ret-0b(13)        # ..and return 

.Lhracf_do_oper:  # Perform the operation and restart if needed
           hracf  focpbr=3,wrkpr=0
           l      2,.Lfcorsult(3)

.Lhracf_ret: # return to caller
           abi_ret

.if .Lhracf_errno_sw
         .include "errnotbl.S"
 # Linux errno interpretation table required by errno operation
          errnotbl platform=linux,name=.Lhracf_errno_table
.endif

.endif # .ifndef .Lhracfmod_S scope
