.ifndef .Ldriver_S
.Ldriver_S = 1
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

 # This module provides the Driver Framework and the CMN_driver.  It provides driver 
 # management and access to all other driver functionality via the driver/driverx 
 # functions.  The driver/driverx functions are made accessable via the driver 
 # management functions .LDF_open or .LDF_open64.  These functions may only be 
 # called by name and are therefore only accessible to the program that includes 
 # driver.S as part of its assembly.

 # Driver Framework relate source modules:
 #      DRIVER.S   - Macros and symbols used by programs that call drivers
 #      DRVUTIL.S  - Macros and symbols used by drivers participating in the Driver
 #                   Framework
 #   *  driver.S   - Implements the Driver Framework.  Included by a program that
 #                   provides the framework with which drivers are registered or
 #                   called by users of the drivers themselves.
 #
 #   * This source module

 # Dependencies:
            .include "table.S"

.ifndef .LDRIVER_S
            .include "DRIVER.S"
.endif # .ifndef .LDRIVER_S

  # +-----------------------------------+
  # |  Action Token Table Entry (ATTE)  |
  # +-----------------------------------+
  # Access: private - the Driver Framework owns the ATTE
  # Macro: atte/attge - see DRVUTIL.S

            struct .LATTE
            slong  .LATTE_func   # Driver function that processes this action or
                                 # if .LATTE_cpte present, processes the results
            slong  .LATTE_cpt    # Channel Program Table address
            slong  .LATTE_tok    # Token Associated with this action
            shword .LATTE_proc   # DAF process model
            sreserve 2
            shere  .LATTE_len    # Action Token Table Entry length (16)


            struct .LATTGE
            squad  .LATTGE_func  # Driver function that processes this action or
                                 # if .LATTGE_cpte present, processes the results
            squad  .LATTGE_cpt   # Channel Program Table Entry index for this action
            slong  .LATTGE_tok   # Token Associated with this action
            shword .LATTGE_proc  # DAF process model
            sreserve 2
            shere  .LATTGE_len   # Action Token Table Entry length (24)

  # +------------------------------------+
  # |  Action Token Table Header (ATTH)  |
  # +------------------------------------+
  # Access: private - the Driver Framework owns the ATTE
  # Macro: att/attg - see DRVUTIL.S
  #
  # Note: An Action Token Table is a table composed of an extension header that
  # identifies the Driver ID with which are associated the action token entries 
  # that make up the table itself.  See the ATTE structure for details of an 
  # entry's content.  The ATTH is the same for 32- and 64-bit structures

            struct .LATTH
            shword .LATTH_drvid  # Driver ID associated with this ATTH
            sreserve 6
            shere  .LATTH_len    # Action Token Table Header length

  # +-------------------------------+
  # |  CCW Builder Structure (CBS)  |
  # +-------------------------------+
  # Access: private
  # Macro: cbs - see DRVUTIL.S

            struct .Lcbs
            shword .Lcbs_type   # CCW source of data
            shword .Lcbs_data   # CCW data source for deriving the CCW address
            shword .Lcbs_count  # CCW count value
            sbyte  .Lcbs_cmd    # CCW command code
            sbyte  .Lcbs_flags  # CCW command flags
            shere  .Lcbs_len    # CCW builder structure length


  # +---------------------------------------+
  # |  Channel Program Table Header (CPTH)  |
  # +---------------------------------------+
  # Access: private - Channel Program Table extention header
  # Macro: cpt/cptg - see DRVUTIL.S
  #
  # Note: A Channel Program Table is a table composed of CCW Builder Strutures
  # with an extension header that include the channel and device errors being
  # recognized.  This structure only defines the extention header.  See the CBS
  # structure for details of each CPT entry.

            struct .LCPTH
            sbyte  .LCPTH_cherr   # Channel errors to be detected
            sbyte  .LCPTH_chalt   # Channel alerts to be detected
            sbyte  .LCPTH_dverr   # Device errors to be detected
            sbyte  .LCPTH_dvalt   # Device alerts to be detected
            shere  .LCPTH_len     # Channel Program Table Entry length

.if .Lhal_32bit

  # +------------------------------------------+
  # |  32-bit Common Device Driver Structures  |
  # +------------------------------------------+
  # Access: Driver Framework

  # Define the Common Driver's 32-bit Action Token Table:

            att name=.LCMN_att,id=.LDRV_CMN,embed=no
               atte   token=.LCMN_Ena_Drv,func=.LCMN_0  # Enable Drivers
               atte   token=.LCMN_Reg_Drv,func=.LCMN_1  # Register Driver
               atte   token=.LCMN_Opn_Dev,func=.LCMN_2  # Open Device
            attend name=.LCMN_att

  # +-------------------------------+
  # |  32-bit Embedded Driver List  |
  # +-------------------------------+
  # Access: private

            .text  7
            .long  0     # Terminate the 32-bit embedded driver list
            .text  0

            .eject
  # +-------------------------------------------+
  # |  32-bit ENABLE DRIVER Framework Function  |
  # +-------------------------------------------+
  # Access: public

  # Enable the driver framework for use and enable the platform I/O infrastructure
  # for use.  The caller provides an address to an area for use by the Driver
  # Framework.  This area, the Driver Management Block, contains 16 slots for
  # information.  Each slot is 4-bytes in length for 32-bit architectures and
  # 8-bytes in length for 64-bit architectures, or 64-bytes in length for 32-bit
  # architectures and 128-bytes in length for 64-bit architectures.  
  # 
  # The first slot, slot 0, always contains the address of the general driver 
  # function.  The remainder of the area will contain N-1 managed slots.  Slot 1 
  # contains the first slot of the managed slots which is always the number of 
  # slots being managed exclusive of itself.  The default number of slots therefore
  # provides the Device Driver with 14 slots for each recognized device type.
  #
  # It is the program's responsibility to share the driver function address with
  # interested portions of the program.

  # On Entry:
  #     R2     Pointer to Driver Management Table (DMT)
  #
  # Used:
  #     R1     Work register (here and in subroutine)
  #     R2     Pointer to local DRB to register the Common Driver
  #     R3     Number of DMT table entries (14)
  #     R4     Size of each table entry
  #     R5     Size of the header extension
  #     R6     Contains 0
  #     R7     Pointer to the Common Driver's Action Token Table
  #
  # On Exit:
  #     Initialize DMT

            func370 .LDF_open

    # Local literal pool usage
.LDF_open_parms: # R3         R4  R5 R6 R7
            .long  .LDRV_IDS, 4,  0, 0, .LCMN_att

    # Local stack frame usage:
            fbytes .LDF_open_drb,.LDRB_len  # Create a DRB on the stack

            push370

            lm     3,7,.LDF_open_parms-0b(13)    # Set up parms
            la     10,.LDF_table-0b(13)          # Locate the table builder
            basr   11,10                         # Build the table

            tblscan tblr=2,ntryr=1
            st     6,0(1)                        # Clear the entry
            tblnext tblr=2,ntryr=1               # Continue until done
            st     2,.LCMN_dmt-0b(13)            # Save DMT for the future

            drbf   .LDF_open_drb,2               # Create a DRB
            st     7,.LDRB_addr32(2)             # Point DRB to CMN Driver ATT
            callptr .LCMN_1                      # Register the Common Driver

            sr     2,2                           # Make sure high order bits clear
            la     2,.LDF_daf-0b(13)             # Return the DAF to the caller

            return
.if 0
            .eject
  # +-------------------------------+
  # |  32-bit CCW Builder Function  |
  # +-------------------------------+
  # Access: public

  # On Entry:
  #     R2     I/O data area (.LIOLO structure)
  #     R3     Address of the current CCW builder structure entry (cbs macro)
  #     R4     Address of a list of model CCWs (referenced by cbs)
  #     R5     Address of the user area within the sdwa (used now)
  #
  # Used:
  #     R1     Work register
  #     R6     Number of CCWs left to be built
  #     R7     Current CCW being built
  #     R8     High-order CCW address, bits 0-31  (from shared subroutine)
  #     R9     Low-order CCW address,  bits 32-63 (from shared subroutine)
  #     R10    Address of shared subroutine
  #     R11    Shared subroutine return address
  #     R12    
  #
  # On Exit:
  #     CCW's ready for execution

            func370 .Ldrv_ccw32

    # Local stack frame use
            fbytes    .Ldrv_ccw32_spill,12
            flong     .Ldrv_ccw32_first_ccw

            push370

            lh     6,10(5)                  # Fetch the number of CCW's
            l      7,.LIOLO_ccw1(2)         # Locate where first CCW goes
            st     7,.Ldrv_ccw32_first_ccw(15) # Save for future reference
            la     10,.Ldrv_ccw_rtn-0b(13)  # Locate shared subroutine

.Ldrv_ccw32_next:
            basr   11,10                    # Build the CCW

            stm    3,5,.Ldrv_ccw32_spill(15) # Save R3-R5 during function call
            lr     3,8                      # Pass high-order address bits
            lr     4,9                      # Pass low-order address bits
            st     7,.LIOLO_ccw1(2)         # Point the CCW formatter to the current CCW
            l      1,.LIEIB_asb(0)          # Locate the active ASB
            l      1,.LASB_ccw(1)           # Locate the FORMAT CCW abstraction
            callr  1                        # Transform CCW

            lm     3,5,.Ldrv_ccw32_spill(15)# Restore R3-R5 after function call

            la     7,8(7)                   # Point to next CCW receiving location
            st     7,.LIOLO_ccw1(2)         # Update the CCW pointer
            la     3,.Lcbs_len(3)           # Point to next cbs entry
            bct    6,.Ldrv_ccw32_next-0b(13)   # Continue until done
    # CCW's have been built

            # Locate the first CCW for I/O execution
            mvc    .LIOLO_ccw1(4,2),.Ldrv_ccw32_first_ccw(15)
            return
.endif # .if 0 

            .eject
  # +-----------------------------------------------+
  # |  32-bit Driver Framework I/O Assist Function  |
  # +-----------------------------------------------+
  # Access: private

  # This function builds a channel program based upon the set of CCW Builder
  # Structures supplied in a table.  CCW's a categorized into three classes by 
  # type paramter on the cbs macro:
  #
  #   0x00   CCW data address and lengh supplied by a DRB and moved to DDE
  #          by the Driver Access Function.
  #   0x04   This is a TRANSFER-IN-CHANNEL CCW.  The CCW address specifies an
  #          index number within the channel program
  #   0x08   CCW data address is within the DDE.  The address is a displacement
  #          from the start of the DDE to the data.
  #   0x0C   Build an immediate CCW exactly as specified.
  #
  # After building the CCW format 1, the IOLO FORMAT CCW abstraction is called
  # to modify the CCW for the I/O architecture (and in some cases generate IDAW2's).
  #
  # The CPT header contains the I/O conditions to be recognized for the I/O
  # operation performed by the IOLO I/O abstraction.
  #
  # On Entry:
  #     R2     Device Definition Entry (DDE) address
  #     R3     Channel Program Table (CPT) address
  #
  # Used:
  #     R1     Work register
  #     R2     DDE Address (.LIOLO sits at the beginning of the DDE)
  #     R3     High-order 32-bits of program data address
  #     R4     Low-order 32-bits of program data address
  #     R6     Caller's DDE address
  #     R7     Caller's CPT address
  #     R8     CBS entry address within the CPT
  #     R9     Address where current CCW is being built
  #     R10    Address of the CCW formatter abstraction
  #     R11    CPT header address
  #     R12    Active ASB
  #
  # On Exit:
  #     R2     Return code returned by the IOLO I/O abstraction.

            func370 .LDF_io
            push370

            lr     6,2                   # Preserve the caller's DDE address
            lr     7,3                   # Preserve the caller's CPT address

            la     9,.LDDE_ccws(2)       # Identify where CCW's are being built
            la     1,.LDDE_idaws(2)      # Locate start of IDAW's
            st     1,.LIOLO_idaw2(2)     # and tell the CCW Formatting abstraction
            l      12,.LIEIB_asb(0)      # Locate the active ASB
            l      10,.LASB_ccw(12)      # Locate the FORMAT CCW abstraction

            tblscan tblr=7,ntryr=8       # Scan the CPT, processing each CBS
            # R8 points to the CBS

            mvc    .LCCW1_cmd(1,9),.Lcbs_cmd(8)       # Move command to CCW
            mvc    .LCCW1_flags(1,9),.Lcbs_flags(8)   # Move flags to CCW
            st     9,.LIOLO_ccw1(6)      # Point to the CCW for the formatter

            lh     1,.Lcbs_type(8)       # Fetch the CCW type
            b      .+4-0b(13)            # Selet the processing by type
            b      .LDF_io_pgm-0b(13)    # Process a program data CCW
            b      .LDF_io_tic-0b(13)    # Process a TIC CCW
            b      .LDF_io_dde-0b(13)    # Process a DDE resident data CCW
            b      .LDF_io_imd-0b(13)    # Process an immediate CCW

.LDF_io_pgm:
            mvc    .LCCW1_cnt(2,9),.LDDE_pgm_length(2)  # Move count to CCW
            lm     3,4,.LDDE_pgm_data_hi(2) # Prepare the address the CCW formatter
            b      .LDF_io_format-0b(13) # Format and process next CBS entry

.LDF_io_tic:
            sr     3,3                   # Clear high-order bits of address
            lh     4,.Lcbs_data(8)       # Fetch the CCW index from CBS
            sll    4,3                   # Calculate displacement ( x8 )
            la     4,.LDDE_ccws(4,6)     # Caluclate the address
            b      .LDF_io_format-0b(13) # Format and process next CBS entry

.LDF_io_dde:
            sr     3,3                   # Clear high-order bits of address
            lh     4,.Lcbs_data(8)       # Fetch the DDE displacement from CBS
            la     4,0(4,6)              # Calculate address within the DDE
            b      .LDF_io_format-0b(13) # Format and process next CBS entry

.LDF_io_imd:
            sr     3,3                   # Clear high-order bits of address
            lh     4,.Lcbs_data(8)       # Set low-order bits to CBS value
            mvc    .LCCW1_cnt(2,9),.Lcbs_count(8)  # Move the count to the CCW

.LDF_io_format:
            callr  10                    # Format the CCW
            la     9,8(9)                # Point to next CCW to be built
            tblnext tblr=7,ntryr=8       # Process the next CCW

    # Execute the I/O with the CCW's just built
            lhdr   11,tblr=7             # Locate the header
            mvc    .LIOLO_cherr(4,2),0(11)   # Set the I/O conditions from CPT
            la     1,.LDDE_ccws(6)       # Point to the CCW's to be used
            st     1,.LIOLO_ccw1(6)      # ..in the I/O operation

            lr     2,6                   # Pass the .LIOLO area to abstraction
            l      1,.LASB_io(12)        # Locate the INPUT/OUTPUT abstraction
            callr  1                     # Do the I/O operation

            return                       
            # R2 contains the IOLO return code
            # Accumulated I/O results in DDE channel and device errors and alerts             

            .eject
  # +---------------------------------+
  # |  32-bit Driver Access Function  |
  # +---------------------------------+
  # Access: public

  # The Driver Access Function is responsible for delivery of a caller's request
  # to an action function in a driver based upon the action token supplied by
  # the caller.  Requests specified in a Driver Request Block (DRB) structure are
  # provided by the caller.  To the caller the Driver Access Function is
  # transparent, although some functionality may be provided to assist the called
  # action in the performance of its assigned role.  The Driver Access Function
  # provides a symbol form of dynamic linking between a caller an an embedded or
  # external driver.  Driver's may use the DAF or call a driver action directly.
  #
  # The DAF performs its responsibility in two steps:
  #   1. Locate the driver's Action Token Table and the ATT entry of the requested
  #      action.
  #   2. Based upon the content of the ATT entry, the processing model
  #      specifically, initiate the process required by the driver action function.
  #
  # Step 1:
  #   If the DRB contains a DDE address (the address is not zero) use the DDE to
  #   locate the driver's ATT address if present (also not zero).  Otherwise
  #   locate the driver's ATT via the Driver Management Table.
  # Step 2:
  #   Based upon the action token table locate from the ATT entry associated with 
  #   the Action Token in the DRB.  From the located entry, use the process model 
  #   field of the ATT entry to direct the processing of the request:
  #
  #   Process Models:
  #      0x0000  -  Call the driver function, passing the caller's DRB and any 
  #                 other arguments.  This model is the default if the 'proc' 
  #                 parameter is not specified on the 'atte' or 'attge' macros.
  #      0x0004  -  Update the DDE with the program I/O arguments (data address and
  #                 data length) provided in the DRB and call the driver function, 
  #                 passing the DRB and DDE.
  #      0x0008  -  Update the DDE with the program I/O arguments (data address and
  #                 data length) provided in the DRB and call the Common Driver
  #                 I/O assistance function, passing the CCW Program Table provided
  #                 in the ATT entry and the DDE.
  #      0x000C  -  Same as 0x0008, except upon return the driver function is
  #                 called with the DDE to allow analysis of the results present in
  #                 the DDE.
  #      0x0010  -  Call the driver function in the ATT entry to prepare the I/O.
  #                 Then use the returned DRB to execute the I/O using the Common
  #                 Driver I/O assistance function.  This model is the reverse
  #                 sequence of the 0x000C model.
  #
  # Depending upon the process model in which the action function participates,
  # different arguments should be expected to be passed.  The arguments passed
  # are tailored to the function's role.
  #        Model   0x0000     0x0004      0x0008     0x000C        0x0010
  #     R2         DRB addr.  DRB addr.     not      DDE addr.     DRB addr.
  #     R3           --         --       applicable  .LDF_io rc      --


  # On Entry:
  #     R2     Driver Request Block (DRB) address
  #
  # Used:
  #     R1     Work register
  #     R2     DDE Address (for Driver Framework I/O assist)
  #     R3     CCW Program Table (for Driver Framework I/O assist)
  #     R6     Caller's DRB
  #     R7     Caller's DDE (if present)
  #     R8     ATTE pointer
  #     R9     ATT Pointer
  #     R10    Index register
  #     R12    DMT address
  #
  # On Exit:
  #     R2     Any value returned by the called driver function or I/O

            func370 .LDF_daf

    # Local literal pool usage
.LDF_daf_max_proc:
            .hword  0x0010

            push370

            lr     6,2                         # Preserve the caller's DRB

    # Step 1 - Locating the driver Action Table

            icm    7,0b1111,.LDRB_dde(6)       # Fetch the caller's DDE
            bz     .LDF_daf_use_dmt-0b(13)     # If absent, use the DMT
            icm    9,0b1111,.LDDE_att(7)       # Fetch the AT entry from DDE
            bnz    .LDF_daf_have_att_and_dde-0b(13)  # If present use DDE AT addr.

        # Use the Driver Management Table to locate the AT
.LDF_daf_use_dmt:
            icm    12,0b1111,.LCMN_dmt-0b(13)  # Locate the DMT
            bz     .LDF_daf_die_no_dmt-0b(13)  # If still zero, framework not open

            lh     10,.LDRB_at(6)              # Fetch the driver ID from DRB
            lndx   9,tblr=12,ndxr=10,error=.LDF_daf_die_drid_out_of_bounds
            icm    9,0b1111,0(9)               # Fetch the ATT pointer from DMT
            bz     .LDF_daf_die_unregisterd_driver-0b(13)  # Die if unregistered

            lhdr   1,tblr=9                             # Locate the ATT header
            clc    .LATTH_drvid(2,1),.LDRB_at(2)        # Driver ID's match??
            bne    .LDF_daf_die_att_at_mismatch-0b(13)  # ..No!! die

            icm    10,0b0011,.LDRB_at+2(6)     # Fetch the Token ID
            lndx   8,tblr=9,ndxr=10,error=.LDF_daf_die_actid_out_of_bounds
            # Already know there may not be a DDE, so must not try to prep it.
            b      .LDF_daf_0000-0b(13)        # Just call the function

        # Use the AT located via the DDE following an Open Device action
.LDF_daf_have_att_and_dde:
            icm    10,0b0011,.LDRB_at+2(6)     # Fetch the Token ID
            lndx   8,tblr=9,ndxr=10,error=.LDF_daf_die_actid_out_of_bounds

    # Step 2 - Process the ATTE (R8)

            lh     1,.LATTE_proc(8)            # Fetch the process model
            clm    1,0b0011,.LDF_daf_max_proc-0b(13)  # Process model valid?
            bh     .LDF_daf_die_model_hi-0b(13)       # ..No, die!
            b      .+4-0b(1,13)                # Select the model

                                  # Part  1          2             3
            b      .LDF_daf_0000-0b(13) # Call func
            b      .LDF_daf_0004-0b(13) # Prep DDE   call func
            b      .LDF_daf_0008-0b(13) # Prep DDE   call I/O ass.
            b      .LDF_daf_000C-0b(13) # Prep DDE   call I/O ass. Call func
            b      .LDF_daf_0010-0b(13) # Prep DDE   call func     call I/O ass.

.LDF_daf_0000:
          # Part 1
            # Note: R2-R6 may be have any content
            icm    1,0b1111,.LATTE_func(8)     # Fetch the action function addr.
            bz     .LDF_daf_die_no_action-0b(13) # If no function, die
            callr  1                           # Call the function
            b      .LDF_daf_ret-0b(13)         # Return to caller

.LDF_daf_0004: 
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: R2 points to the caller's DRB
            b      .LDF_daf_0000-0b(13)                  # Now call the function

.LDF_daf_0008:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: When calling the Driver Framework I/O function:
            #    R2 == the DDE address
            #    R3 == the CCW Program Table in use
            lr     2,7                         # Pass the DDE address
            icm    3,0b1111,.LATTE_cpt(8)      # Fetch the CCW Program table addr.
            bz     .LDF_daf_die_no_cpt-0b(13)  # If absent, die
            callptr .LDF_io                    # DF does I/O for driver
            b      .LDF_daf_ret-0b(13)         # Now return to caller

.LDF_daf_000C:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: When calling the Driver Framework I/O function:
            #    R2 == the DDE address
            #    R3 == the CCW Program Table in use
            lr     2,7                         # Pass the DDE address
            icm    3,0b1111,.LATTE_cpt(8)      # Fetch the CCW Program table addr.
            bz     .LDF_daf_die_no_cpt-0b(13)  # If absent, die
            callptr .LDF_io                    # DF does I/O for driver

          # Part 3
            # Note: When calling the function to analyze I/O results:
            #    R2 == the DDE address
            #    R3 == .LDF_io return code (the .Liolo_io abstraction return code)
            lr     3,2                         # Move the .LDF_io return code
            lr     2,7                         # DDE has results
            b      .LDF_daf_0000-0b(13)        # Now call the function

.LDF_daf_0010:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            l      1,.LATTE_func(8)            # Fetch the driver function addr.
            callr  1                           # Call the function
            # Function returns a CPT for the DF_io assist

          # Part 3
            # Note: When calling the Driver Framework I/O function for results
            #    R2 == the DDE address
            #    R3 == .LDF_io return code
            lr     3,2                         # Pass the CPT address
            lr     2,7                         # Pass the DDE address
            callptr .LDF_io                    # DF does I/O for driver

.LDF_daf_ret:
            return

.LDF_daf_die_no_dmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_daf_die_drid_out_of_bounds:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_daf_die_unregisterd_driver:
            drvabort error=.LDRV_nodr,dtype=.LDRV_CMN
.LDF_daf_die_att_at_mismatch:
            drvabort error=.LDRV_drne,dtype=.LDRV_CMN
.LDF_daf_die_actid_out_of_bounds:
            drvabort error=.LDRV_toob,dtype=.LDRV_CMN
.LDF_daf_die_no_action:
            drvabort error=.LDRV_noaf,dtype=.LDRV_CMN
.LDF_daf_die_no_cpt:
            drvabort error=.LDRV_nocp,dtype=.LDRV_CMN
.LDF_daf_die_model_hi:
            drvabort error=.LDRV_bdpr,dtype=.LDRV_CMN

            .eject
  # +------------------------------------------+
  # |  32-bit ACTION TOKEN 0 - Enable Drivers  |
  # +------------------------------------------+
  # Access: public
  # Token: .LCMN_Ena_Drv - 0x00000000

  # On Entry:
  #     R2     Device Request Block Address
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R3     ATT address being registered (by registration function)
  #     R8     Pointer to current embedded driver list being registered
  #     R9     Save location for user DRB address
  #     R10    Save location for number of DDE entries / Subroutine address
  #     R11    Shared subroutine return address
  #     R12    Location of my DRB
  #
  # On Exit:
  #     R2     DMT address

            func370 .LCMN_0

  # Local literal pool usage
.LDF_drvena_list:
            .long  .LDF_drivers  # Start of embedded driver list
.LDF_drvena_dde_parms:
            .long  .LDDE_len,0

  # Local stack frame usage:
            fbytes .LDF_drvena_drb,.LDRB_len  # Create a DRB on the stack

            push370

            cli    .LDF_drvena_sw-0b(13),0x00     # First time?
            be     .+8-0b(13)                     # ..Yes, continue
            drvabort error=.LDRV_ddtr,dtype=.LDRV_CMN  # ..No, abort

            lr     9,2                            # Save the caller's DRB

            drbf   .LDF_drvena_drb,12             # Locate and clear my DRB
            l      8,.LDF_drvena_list-0b(13)      # Locate the embedded list

.LDF_drvena_reg:
            icm    3,0b1111,0(8)                  # Locate the ATT
            bz     .LDF_drvena_dde-0b(13)         # List is done if zero address

            st     3,.LDRB_addr32(12)             # Point the DRB to the ATT
            lr     2,12                           # Point to my DRB for call
            callptr .LCMN_1                       # Register this driver
            la     8,4(8)                         # Point to next ATT in list
            b      .LDF_drvena_reg-0b(13)         # Register the next list

.LDF_drvena_dde:
            l      2,.LDRB_dde(9)           # Retrive the DDE table orign
            ltr    2,2                      # Pass DDE table origin if requested?
            bz     .LDF_drvena_io-0b(13)    # ..No, so enable I/O
            lh     3,.LDRB_length(9)        # ..Yes, pass the number of entries
            lm     4,5,.LDF_drvena_dde_parms-0b(13)  # Set DDE size
            la     10,.LDF_table-0b(13)     # Locate the table builder
            basr   11,10                    # Build the requested table

.LDF_drvena_io: # Enable the I/O abstractions drivers will use
            l      6,.LIEIB_asb(0)          # Locate the ASB
            l      1,.LASB_enio(6)          # Locate the ENABLE IO abstraction
            callr  1                        # Enable I/O operations

            mvi    .LDF_drvena_sw,0xFF      # Been here don't do it again
            return
.LDF_drvena_sw:
            .byte  0x00                     # Switch to trap calls here when
                                            # DRB has token==0x00000000

            .eject
  # +-------------------------------------------+
  # |  32-bit ACTION TOKEN 1 - Register Driver  |
  # +-------------------------------------------+
  # Access: public
  # Token: .LCMN_Reg_Drv - 0x00000001

  # On Entry:
  #     R2     Driver Request Block (DRB) address
  #     R3     Driver ATT address of driver to be registered
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R2     DMT address
  #     R3     Driver ATT address of driver to be registered
  #     R7     Driver ID being registered
  #     R8     Generated token to validate token symbols
  #     R9     ATTE pointer during ATT validation
  #
  # On Exit:
  #     R2     DMT address

            func370 .LCMN_1

  # Local Literal pool usage
.LDF_drvreg_1:
            .long  1

            push370

            l      3,.LDRB_addr32(2)            # Locate the ATT from the DRB
            icm    2,0b1111,.LCMN_dmt-0b(13)    # Locate the DMT
            bz     .LDF_drvreg_nodmt-0b(13)     # Die, if framework not initialized   
            lhdr   1,tblr=3                     # Locate the ATT header
            lh     7,.LATTH_drvid(1)            # Get the driver ID being registered

            lr     8,7                          # Move the driver ID
            sll    8,16                         # Create the initial token 

            # Check for inconsistencies between indexes and the token symbol.
            # This check can only be done at run-time.  So do it when registering
            # the driver.  A mismatch is an internal coding error.  This check
            # ensures that the token a program will use gets you to the right
            # driver and its intended function.  On a mismatch, either the wrong 
            # symbol was coded with the atte macro or the symbol equates to the 
            # wrong value.  Fix the one that is in error.

            tblscan tblr=3,ntryr=9
            cl     8,.LATTE_tok(9)              # Token symbol and index match?
            bne    .LDF_drvreg_badtok-0b(13)    # ..NO, internal error
            al     8,.LDF_drvreg_1-0b(13)       # Increment index value
            tblnext tblr=3,ntryr=9
            # All symbols and indexes match, can register

            # Locate the entry for this driver ID in the Driver Management Table
            lndx   r=1,tblr=2,ndxr=7,error=.LDF_drvreg_badid  # Die if out of bounds
            icm    0,0b1111,0(1)                # Is this ID already registered?
            bnz    .LDF_drvreg_dup-0b(13)       # ..Yes, die on duplicate
            st     3,0(1)                       # Register the driver

            return

.LDF_drvreg_nodmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_drvreg_badid:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_drvreg_dup:
            drvabort error=.LDRV_ddup,dtype=.LDRV_CMN
.LDF_drvreg_badtok:
            drvabort error=.LDRV_bdtk,dtype=.LDRV_CMN

            .eject
  # +---------------------------------------+
  # |  32-bit ACTION TOKEN 2 - Open Device  |
  # +---------------------------------------+
  # Access: public
  # Token: .LCMN_Opn_Dev

  # On Entry:
  #     R2     Device Request Block Address
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R6     Active ASB
  #     R7     Device Definition Entry of device being opened
  #     R8     Controlling driver
  #     R9     Driver Management Table address
  #     R10    Device ID
  #     R12    Caller's DRB
  #
  # On Exit:
  #     Device identified by DDE is ready for use

            func370 .LCMN_2

    # Local literal pool usage:
.LCMN_2_daf:.long  .LDF_daf

            push370

    # Process the device number / SSID

            lr     12,2                     # Preserve the caller's DRB address
            l      7,.LDRB_dde(12)          # Locate the DDE
            lh     8,.LDRB_misc(12)         # Fetch the controlling driver's id
            l      2,.LDRB_addr32(12)       # Fetch the device number
            tm     .LIEIB_plt,.LIEIB_chan   # Channel I/O in use?
            bo     .LDF_opndev_devid-0b(13) # ..Yes, do not need to find subchannel
            tm     .LDRB_addr32+1(10),0x01  # Already a subchannel?
            bo     .LDF_opndev_devid-0b(13) # ..Yes, also do not need to find it

            l      6,.LIEIB_asb(0)          # Locate the active ASB
            l      1,.LASB_find(6)          # Locate the abstraction
            callr  1                        # FIND SUBCHANNEL abstraction
            cl     2,.LDRB_addr32(10)       # Did we find the subchannel?
            bne    .LDF_opndev_devid-0b(13) # ..yes, device number not returned

            drvabort error=.LDRV_nosc,dtype=.LDRV_CMN

.LDF_opndev_devid:
            lr     10,2                     # Save the device id
            l      1,.LASB_ena(6)           # Locate the abstraction
            callr  1                        # ENABLE DEVICE abstraction
            ltr    2,2                      # Did we succeed?
            bnz    .LDF_devopn_enafail-0b(13)  # ..No, die then

            ltr     8,8                      # Clear R8
            bnz    .LDF_devopn_as-0b(13)    # Caller is supplying id, use it

            # The caller expects the driver framework to figure out the device
            # To be implemented (someday)
            drvabort error=.LDRV_tbd,dtype=.LDRV_CMN

.LDF_devopn_as:
            icm    9,0b1111,.LCMN_dmt-0b(13)  # Locate the DMT
            bz     .LDF_devopn_nodmt-0b(13)   # Die, if framework not initialized

            # Locate the entry for this driver ID in the Driver Management Table
            lndx   r=1,tblr=9,ndxr=8,error=.LDF_devopn_badid  # Die if out of bounds
            # R1 should now point to the controlling driver's DMT entry

            icm    1,0b1111,0(1)            # Fetch the driver's ATT address
            bz     .LDF_devopn_drvnor-0b(13)# ..If not registered (0), die!

            st     1,.LDDE_att(7)           # Set the device driver's ATT in DDE
            sth    8,.LDDE_drvid(7)         # Set the driver ID in use.
            st     10,.LIOLO_dev(7)         # Set the device id in it
            mvc    .LDDE_daf(4,7),.LCMN_2_daf-0b(13)  # Set the DAF address

            return

.LDF_devopn_nodmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_devopn_badid:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_devopn_drvnor:            
            drvabort error=.LDRV_nodr,dtype=.LDRV_CMN
.LDF_devopn_enafail:
            drvabort error=.LDRV_noen,dtype=.LDRV_CMN            

            .eject
  # +------------------------------------------+
  # |  32-bit Table Builder Shared Subroutine  |
  # +------------------------------------------+

  # On Entry:
  #     R2     Address where table is to reside
  #     R3     Number of table entries
  #     R4     Size of each table entry
  #     R5     Size of the header extension
  #     R10    Shared subroutine base register
  #     R11    Shared subroutine return address
  #
  # Used:
  #     R1     Work register
  #
  # On Exit:
  #     R2     Pointer to the built table

.LDF_table:
0:
            tblbld tblr=2,nr=3,sr=4,hdr=5,wrkr=1,br=10
            br     11                 # Return to caller


.LCMN_dmt:  .long  0   # Address of the Driver Management Table


.endif # .if .Lhal_32bit
            .eject
.if .Lhal_64bit

  # +------------------------------------------+
  # |  64-bit Common Device Driver Structures  |
  # +------------------------------------------+
  # Access: Driver Framework

  # Define the Driver's Action Token Table:

            attg name=.LCMN_att64,id=.LDRV_CMN,embed=no
               attge  token=.LCMN_Ena_Drv,func=.LCMNG_0  # Enable Drivers
               attge  token=.LCMN_Reg_Drv,func=.LCMNG_1  # Register Driver
               attge  token=.LCMN_Opn_Dev,func=.LCMNG_2  # Open Device
            attend name=.LCMN_att64

  # +-------------------------------+
  # |  64-bit Embedded Driver List  |
  # +-------------------------------+
  # Access: private

            .text  8
            .quad  0     # Terminate the 64-bit embedded driver list
            .text  0

            .eject
  # +-------------------------------------------+
  # |  64-bit ENABLE DRIVER Framework Function  |
  # +-------------------------------------------+
  # Access: public

  # On Entry:
  #     R2     Pointer to Driver Management Table (DMT)
  #     R3     Number of entries provided by the DMT (zero defaults to 14)
  #
  # Used:
  #     R1     Work register
  #     R3     Number of DMT table entries (14)
  #     R4     Size of each table entry
  #     R5     Size of the header extension
  #     R6     Contains zero
  #     R7     Pointer to the Common Driver's Action Token Table
  #
  # On Exit:
  #     Initialize DMT

            functionx .LDF_open64

    # Local literal pool usage
.LDF_open64_parms: # R3         R4  R5 R6 R7
            .quad    .LDRV_IDS, 8,  0, 0, .LCMN_att64

    # Local stack frame usage:
            fbytes .LDF_open64_drb,.LDRB_len     # Create a DRB on the stack

            pushx

            lmg    3,7,.LDF_open64_parms-0b(13)  # Set up parms
            la     10,.LDF_table64-0b(13)        # Locate the table builder
            basr   11,10                         # Build the table

            tblscang tblr=2,ntryr=1
            stg    6,0(1)                        # Clear the entry
            tblnextg tblr=2,ntryr=1              # Continue until done
            stg    2,.LCMNG_dmt-0b(13)           # Save DMT for the future

            drbf   .LDF_open64_drb,2             # Locate and clear my DRB
            stg    7,.LDRB_addr(2)               # Point to 64 CMN Driver ATT
            callptrx .LCMNG_1                    # Register it

            larl   2,.LDF_daf64                  # Return the DAF to the caller

            returnx

            .eject
  # +-------------------------------+
  # |  64-bit CCW Builder Function  |
  # +-------------------------------+
  # Access: public

  # On Entry:
  #     R2     I/O data area (.LIOLO structure)
  #     R3     Address of the current CCW builder structure entry (cbs macro)
  #     R4     Address of a list of model CCWs (referenced by cbs)
  #     R5     Address of the user area within the sdwa (used now)
  #
  # Used:
  #     R1     Work register
  #     R6     Number of CCWs left to be built
  #     R7     Current CCW being built
  #     R8     High-order CCW address, bits 0-31  (from shared subroutine)
  #     R9     Low-order CCW address,  bits 32-63 (from shared subroutine)
  #     R10    Address of shared subroutine
  #     R11    Shared subroutine return address
  #     R12    
  #
  # On Exit:
  #     CCW's ready for execution

            functionx .Ldrv_ccw64

    # Local stack frame use
            fbytes    .Ldrv_ccw64_spill,24
            flong     .Ldrv_ccw64_first_ccw

            pushx

            lgh    6,10(5)                  # Fetch the number of CCW's
            llgt   7,.LIOLO_ccw1(2)         # Locate where first CCW goes
            st     7,.Ldrv_ccw64_first_ccw(15) # Save for future reference
            la     10,.Ldrv_ccw_rtn-0b(13)  # Locate shared subroutine

.Ldrv_ccw64_next:
            basr   11,10                    # Build the CCW

            stmg   3,5,.Ldrv_ccw64_spill(15)# Save R3-R5 during function call

            lr     3,8                      # Pass high-order address bits
            lr     4,9                      # Pass low-order address bits
            st     7,.LIOLO_ccw1(2)         # Point the CCW formatter to the current CCW
            lg     1,.LIEIB_asbg(0)         # Locate the active ASB
            lg     1,.LASBG_ccw(1)          # Locate the FORMAT CCW abstraction
            callrx  1                       # Transform CCW

            lmg    3,5,.Ldrv_ccw64_spill(15)# Restore R3-R5 after function call

            la     7,8(7)                   # Point to next CCW receiving location
            st     7,.LIOLO_ccw1(2)         # Update the CCW pointer
            la     3,.Lcbs_len(3)           # Point to next cbs entry
            brctg  6,.Ldrv_ccw64_next       # Continue until done
    # CCW's have been built
 
            # Locate the first CCW for I/O execution
            mvc    .LIOLO_ccw1(4,2),.Ldrv_ccw64_first_ccw(15)
            returnx

  # +-----------------------------------------------+
  # |  64-bit Driver Framework I/O Assist Function  |
  # +-----------------------------------------------+
  # Access: private

  # This function builds a channel program based upon the set of CCW Builder
  # Structures supplied in a table.  CCW's a categorized into three classes by 
  # type paramter on the cbs macro:
  #
  #   0x00   CCW data address and lengh supplied by a DRB and moved to DDE
  #          by the Driver Access Function.
  #   0x04   This is a TRANSFER-IN-CHANNEL CCW.  The CCW address specifies an
  #          index number within the channel program
  #   0x08   CCW data address is within the DDE.  The address is a displacement
  #          from the start of the DDE to the data.
  #   0x0C   Builed an immediate CCW exactly as specified.
  #
  # After building the CCW format 1, the IOLO FORMAT CCW abstraction is called
  # to modify the CCW for the I/O architecture (and in some cases generate IDAW2's).
  #
  # The CPT header contains the I/O conditions to be recognized for the I/O
  # operation performed by the IOLO I/O abstraction.
  #
  # On Entry:
  #     R2     Device Definition Entry (DDE) address
  #     R3     Channel Program Table (CPT) address
  #
  # Used:
  #     R1     Work register
  #     R2     DDE Address (.LIOLO sits at the beginning of the DDE)
  #     R3     High-order 32-bits of program data address
  #     R4     Low-order 32-bits of program data address
  #     R6     Caller's DDE address
  #     R7     Caller's CPT address
  #     R8     CBS entry address within the CPT
  #     R9     Address where current CCW is being built
  #     R10    Address of the CCW formatter abstraction
  #     R11    CPT header address
  #     R12    Active ASB
  #
  # On Exit:
  #     R2     Return code returned by the IOLO I/O abstraction.

            functionx .LDF_io64
            pushx

            lgr    6,2                   # Preserve the caller's DDE address
            lgr    7,3                   # Preserve the caller's CPT address

            la     9,.LDDE_ccws(2)       # Identify where CCW's are being built
            la     1,.LDDE_idaws(2)      # Locate start of IDAW's
            st     1,.LIOLO_idaw2(2)     # and tell the CCW Formatting abstraction
            lg     12,.LIEIB_asbg(0)     # Locate the active ASB
            lg     10,.LASBG_ccw(12)     # Locate the FORMAT CCW abstraction

            tblscang tblr=7,ntryr=8      # Scan the CPT, processing each CBS
            # R8 points to the CBS

            mvc    .LCCW1_cmd(1,9),.Lcbs_cmd(8)       # Move command to CCW
            mvc    .LCCW1_flags(1,9),.Lcbs_flags(8)   # Move flags to CCW
            st     9,.LIOLO_ccw1(6)      # Point to the CCW for the formatter

            lgh    1,.Lcbs_type(8)       # Fetch the CCW type
            b      .+4-0b(13)            # Selet the processing by type
            j      .LDF_io_pgm64         # Process a program data CCW
            j      .LDF_io_tic64         # Process a TIC CCW
            j      .LDF_io_dde64         # Process a DDE resident data CCW
            j      .LDF_io_imd64         # Process an immediate CCW

.LDF_io_pgm64:
            mvc    .LCCW1_cnt(2,9),.LDDE_pgm_length(2)  # Move count to CCW
            # Formatter expects 64-bit address in regs 3,4
            lm     3,4,.LDDE_pgm_data_hi(6) # Prepare the address the CCW formatter
            j      .LDF_io_format64       # Format and process next CBS entry

.LDF_io_tic64:
            lgh    3,.Lcbs_data(8)       # Fetch the CCW index from CBS
            sllg   3,3,3                 # Calculate displacement ( x8 )
            la     3,.LDDE_ccws(3,6)     # Caluclate the address
            j      .LDF_io_format64      # Format and process next CBS entry

.LDF_io_dde64:
            lgh    3,.Lcbs_data(8)       # Fetch the DDE displacemtn from CBS
            la     3,0(3,6)              # Calculate address within the DDE
            j      .LDF_io_format64      # Format and process next CBS entry

.LDF_io_imd64:
            lgh    3,.Lcbs_data(8)       # Set low-order bits to CBS value
            mvc    .LCCW1_cnt(2,9),.Lcbs_count(8)  # Move the count to the CCW

.LDF_io_format64:
            callrx  10                   # Format the CCW
            la     9,8(9)                # Point to next CCW to be built
            tblnextg tblr=7,ntryr=8      # Process the next CCW

    # Execute the I/O with the CCW's just built
            lhdr   11,tblr=7             # Locate the header
            mvc    .LIOLO_cherr(4,2),0(11)   # Set the I/O conditions from CPT
            la     1,.LDDE_ccws(2)       # Point to the CCW's to be used
            st     1,.LIOLO_ccw1(2)      # ..in the I/O operation

            lgr    2,6                   # Pass the .LIOLO area to the abstraction
            lg     1,.LASBG_io(12)       # Locate the INPUT/OUTPUT abstraction
            callrx 1                     # Do the I/O operation

            returnx                       
            # R2 contains the IOLO return code
            # Accumulated I/O results in DDE channel and device errors and alerts

            .eject
  # +---------------------------------+
  # |  64-bit Driver Access Function  |
  # +---------------------------------+
  # Access: public

  # The Driver Access Function is responsible for delivery of a caller's request
  # to an action function in a driver based upon the action token supplied by
  # the caller.  Requests specified in a Driver Request Block (DRB) structure are
  # provided by the caller.  To the caller the Driver Access Function is
  # transparent, although some functionality may be provided to assist the called
  # action in the performance of its assigned role.  The Driver Access Function
  # provides a symbol form of dynamic linking between a caller and an embedded or
  # external driver.  Driver's may use the DAF or call a driver action directly.
  #
  # The DAF performs its responsibility in two steps:
  #   1. Locate the driver's Action Token Table and the ATT entry of the requested
  #      action.
  #   2. Based upon the content of the ATT entry, the processing model
  #      specifically, initiate the process required by the driver action function.
  #
  # Step 1:
  #   If the DRB contains a DDE address (the address is not zero) use the DDE to
  #   locate the driver's ATT address if present (also not zero).  Otherwise
  #   locate the driver's ATT via the Driver Management Table.
  # Step 2:
  #   Based upon the action token table locate from the ATT entry associated with 
  #   the Action Token in the DRB.  From the located entry, use the process model 
  #   field of the ATT entry to direct the processing of the request:
  #
  #   Process Models:
  #      0x0000  -  Call the driver function, passing the caller's DRB and any 
  #                 other arguments.  This model is the default if the 'proc' 
  #                 parameter is not specified on the 'atte' or 'attge' macros.
  #      0x0004  -  Update the DDE with the program I/O arguments (data address and
  #                 data length) provided in the DRB and call the driver function, 
  #                 passing the DRB and DDE.
  #      0x0008  -  Update the DDE with the program I/O arguments (data address and
  #                 data length) provided in the DRB and call the Common Driver
  #                 I/O assistance function, passing the CCW Program Table provided
  #                 in the ATT entry and the DDE.
  #      0x000C  -  Same as 0x0008, except upon return the driver function is
  #                 called with the DDE to allow analysis of the results present in
  #                 the DDE.
  #      0x0010  -  Call the driver function in the ATT entry to prepare the I/O.
  #                 Then use the returned DRB to execute the I/O using the Common
  #                 Driver I/O assistance function.  This model is the reverse
  #                 sequence of the 0x000C model.
  #
  # Depending upon the process model in which the action function participates,
  # different arguments should be expected to be passed.  The arguments passed
  # are tailored to the function's role.
  #        Model   0x0000     0x0004      0x0008     0x000C        0x0010
  #     R2         DRB addr.  DRB addr.     not      DDE addr.     DRB addr.
  #     R3           --         --       applicable  .LDF_io rc      --


  # On Entry:
  #     R2     Driver Request Block (DRB) address
  #
  # Used:
  #     R1     Work register
  #     R2     DDE Address (for Driver Framework I/O assist)
  #     R3     CCW Program Table (for Driver Framework I/O assist)
  #     R6     Caller's DRB
  #     R7     Caller's DDE (if present)
  #     R8     ATTE pointer
  #     R9     ATT Pointer
  #     R10    Index register
  #     R12    DMT address
  #
  # On Exit:
  #     R2     Any value returned by the called driver function or I/O

            functionx .LDF_daf64

    # Local literal pool usage
.LDF_daf64_max_proc:
            .hword  0x0010

            pushx

            lgr     6,2                        # Preserve the caller's DRB

    # Step 1 - Locating the driver Action Table

            llgt   7,.LDRB_dde(6)              # Fetch the caller's DDE
            ltgr   7,7                         # Is the DDE present?
            jz     .LDF_daf64_use_dmt          # ..No, use the DMT to find the ATT
            lg     9,.LDDGE_att(7)             # ..yes,Fetch the AT entry from DDE
            ltgr   9,9                         # Is the AT address present?
            jnz    .LDF_daf64_have_att_and_dde # ..Yes, use it

        # Use the Driver Management Table to locate the AT
.LDF_daf64_use_dmt:
            lg     12,.LCMNG_dmt-0b(13)        # Locate the DMT
            ltgr   12,12                       # Is the driver framework open?
            jz     .LDF_daf64_die_no_dmt       # ..No, die!

            lgh    10,.LDRB_at(6)              # Fetch the driver ID from DRB
            lndxg  9,tblr=12,ndxr=10,error=.LDF_daf64_die_drid_out_of_bounds
            lg     9,0(9)                      # Fetch the ATT pointer from DMT
            jz     .LDF_daf64_die_unregisterd_driver    # Die if unregistered

            lhdr   1,tblr=9                             # Locate the ATT header
            clc    .LATTH_drvid(2,1),.LDRB_at(2)        # Driver ID's match??
            jne    .LDF_daf64_die_att_at_mismatch       # ..No!! die

            llgh   10,.LDRB_at+2(6)            # Fetch the Action Token ID
            lndxg  8,tblr=9,ndxr=10,error=.LDF_daf64_die_actid_out_of_bounds
            # Already know there may not be a DDE, so must not try to prep it.
            j      .LDF_daf64_0000             # Just call the function

        # Use the AT located via the DDE following an Open Device action
.LDF_daf64_have_att_and_dde:
            llgh   10,.LDRB_at+2(6)            # Fetch the Action Token ID
            lndxg  8,tblr=9,ndxr=10,error=.LDF_daf64_die_actid_out_of_bounds

    # Step 2 - Process the ATTE (R8)

            lgh    1,.LATTGE_proc(8)           # Fetch the process model
            clm    1,0b0011,.LDF_daf64_max_proc-0b(13) # Process model valid?
            jh     .LDF_daf64_die_model_hi     # ..No, die!
            b      .+4-0b(1,13)                # Select the model

                                    # Part  1          2             3
            j      .LDF_daf64_0000        # Call func
            j      .LDF_daf64_0004        # Prep DDE   call func
            j      .LDF_daf64_0008        # Prep DDE   call I/O ass.
            j      .LDF_daf64_000C        # Prep DDE   call I/O ass. Call func
            j      .LDF_daf64_0010        # Prep DDE   call func     call I/O ass.

.LDF_daf64_0000:
          # Part 1
            # Note: R2-R6 may be have any content
            lg     1,.LATTGE_func(8)           # Fetch the action function addr.
            ltgr   1,1                         # Is a function in the ATT entry?
            jz     .LDF_daf64_die_no_action    # ..No, die
            callrx 1                           # Call the function
            j      .LDF_daf64_ret              # Return to caller

.LDF_daf64_0004: 
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: R2 points to the caller's DRB
            j      .LDF_daf64_0000                       # Now call the function

.LDF_daf64_0008:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: When calling the Driver Framework I/O function:
            #    R2 == the DDE address
            #    R3 == the CCW Program Table in use
            lgr    2,7                         # Pass the DDE address
            lg     3,.LATTGE_cpt(8)            # Fetch the CCW Program table addr.
            ltgr   3,3                         # Is the address in the ATT entry?
            jz     .LDF_daf64_die_no_cpt       # If absent, die
            callptrx .LDF_io64                # DF does I/O for driver
            j      .LDF_daf64_ret              # Now return to caller

.LDF_daf64_000C:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            # Note: When calling the Driver Framework I/O function:
            #    R2 == the DDE address
            #    R3 == the CCW Program Table in use
            lgr    2,7                         # Pass the DDE address
            lg     3,.LATTGE_cpt(8)            # Fetch the CCW Program table addr.
            ltgr   3,3                         # Is the address in the ATT entry?
            jz     .LDF_daf64_die_no_cpt       # If absent, die
            callptrx .LDF_io64                # DF does I/O for driver

          # Part 3
            # Note: When calling the function to analyze I/O results:
            #    R2 == the DDE address
            #    R3 == .LDF_io return code (the .Liolo_io abstraction return code)
            lgr    3,2                         # Move the .LDF_io return code
            lgr    2,7                         # DDE has results
            j      .LDF_daf64_0000             # Now call the function

.LDF_daf64_0010:
          # Part 1
            mvc    .LDDE_pgm_token(4,7),.LDRB_at(6)      # Pass token in DDE
            mvc    .LDDE_pgm_data_hi(8,7),.LDRB_addr(6)  # Pass address in DDE
            mvc    .LDDE_pgm_length(2,7),.LDRB_length(6) # Pass length in DDE

          # Part 2
            lg     1,.LATTGE_func(8)           # Fetch the action function addr.
            ltgr   1,1                         # Is a function in the ATT entry?
            jz     .LDF_daf64_die_no_action    # ..No, die
            callrx  1                          # Call the function
            # Function returns a CPT for the DF_io assist

          # Part 3
            # Note: When calling the Driver Framework I/O function:
            #    R2 == the DDE address
            #    R3 == the CCW Program Table in use
            lgr    3,2                         # Pass the CPT address
            lgr    2,7                         # Pass the DDE address
            #callptrx .LDF_io64                # DF does I/O for driver

.LDF_daf64_ret:
            returnx

.LDF_daf64_die_no_dmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_daf64_die_drid_out_of_bounds:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_daf64_die_unregisterd_driver:
            drvabort error=.LDRV_nodr,dtype=.LDRV_CMN
.LDF_daf64_die_att_at_mismatch:
            drvabort error=.LDRV_drne,dtype=.LDRV_CMN
.LDF_daf64_die_actid_out_of_bounds:
            drvabort error=.LDRV_toob,dtype=.LDRV_CMN
.LDF_daf64_die_no_action:
            drvabort error=.LDRV_noaf,dtype=.LDRV_CMN
.LDF_daf64_die_no_cpt:
            drvabort error=.LDRV_nocp,dtype=.LDRV_CMN
.LDF_daf64_die_model_hi:
            drvabort error=.LDRV_bdpr,dtype=.LDRV_CMN            

            .eject
  # +------------------------------------------+
  # |  64-bit ACTION TOKEN 0 - Enable Drivers  |
  # +------------------------------------------+
  # Access: public
  # Token: .LCMN_Ena_Drv - 0x00000000

  # On Entry:
  #     R2     Driver Request Block (DRV) address
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R3     ATT address being registered (by registration function)
  #     R8     Pointer to current embedded driver list being registered
  #     R9     Caller's DRB
  #     R10    Shared subroutine address
  #     R11    Shared subroutine return address
  #     R12    My DRB
  #
  # On Exit:
  #     R2     DMT address

            functionx .LCMNG_0

  # Local literal pool usage
.LDF_drvena64_list:
            .quad  .LDF_drivers64  # Start of embedded driver list
.LDF_drvena64_dde_parms:
            .quad  .LDDE_len,0

  # Local stack frame usage:
            fbytes .LDF_drvena64_drb,.LDRB_len    # Create a DRB on the stack

            pushx

            cli    .LDF_drvena64_sw-0b(13),0x00   # First time?
            be     .+8-0b(13)                     # ..Yes, continue
            drvabort error=.LDRV_ddtr,dtype=.LDRV_CMN  # ..No, abort

            lgr    9,2                            # Preserve caller's DRB
            drbf   .LDF_drvena64_drb,12           # Locate and clear my DRB
            lg     8,.LDF_drvena64_list-0b(13)    # Locate the embedded list

.LDF_drvena64_reg:
            lg     3,0(8)                         # Locate the ATT
            ltgr   3,3                            # ..Is the list done?
            jz     .LDF_drvena64_dde              # List is done if zero address
            stg    3,.LDRB_addr(12)               # Set the ATT address in the DRB
            lgr    2,12                           # Pass my DRB to action
            callptrx .LCMNG_1                     # Register this driver
            la     8,8(8)                         # Point to next ATT in list
            j      .LDF_drvena64_reg              # Register the next list

.LDF_drvena64_dde:
            llgt   2,.LDRB_dde(9)           # Retrive the DDE table orign
            ltr    2,2                      # Pass DDE table origin if requested?
            jz     .LDF_drvena64_io         # ..No, so enable I/O

            lgh    3,.LDRB_length(9)        # ..Yes, pass the number of entries
            lmg    4,5,.LDF_drvena64_dde_parms-0b(13)  # Set DDE size
            la     10,.LDF_table64-0b(13)   # Locate the table builder
            basr   11,10                    # Build the requested table

.LDF_drvena64_io: # Enable the I/O abstractions drivers will use
            lg     6,.LIEIB_asbg(0)         # Locate the ASB
            lg     1,.LASBG_enio(6)         # Locate the ENABLE IO abstraction
            callrx  1                       # Enable I/O operations

            mvi    .LDF_drvena64_sw-0b(13),0xFF  # Don't do this again
            returnx

.LDF_drvena64_sw:
            .byte  0x00                     # Switch to trap re-initialization
                                            # This is usually a bad DRB token that
                                            # equals 0x00000000

            .eject
  # +-------------------------------------------+
  # |  64-bit ACTION TOKEN 1 - Register Driver  |
  # +-------------------------------------------+
  # Access: public
  # Token: .LCMN_Reg_Drv

  # On Entry:
  #     R2     Driver Request Block (DRB) address
  #     R3     Driver ATT address of driver to be registered
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R2     DMT address
  #     R7     Driver ID being registered
  #     R8     Generated token to validate token symbols
  #     R9     ATTE pointer during ATT validation
  #     R10    Caller's DRB
  #
  # On Exit:
  #     R2     DMT address

            functionx .LCMNG_1
            pushx

            lgr    10,2                         # Preserve caller's DRB
            lg     2,.LCMNG_dmt-0b(13)          # Locate the DMT
            ltgr   2,2                          # Is, the framework initialized?
            jz     .LDF_drvreg64_nodmt          # ..No, die!
            lg     3,.LDRB_addr(10)             # Locate the ATT from DRB
            lhdr   1,tblr=3                     # Locate the ATT header
            lgh    7,.LATTH_drvid(1)            # Get the driver ID being registered

            sllg   8,7,16                       # Create the initial token 

            # Check for inconsistencies between indexes and the token symbol.
            # This check can only be done at run-time.  So do it when registering
            # the driver.  A mismatch is an internal coding error.  This check
            # ensures that the token a program will use gets you to the right
            # driver and its intended function.  On a mismatch, either the wrong 
            # symbol was coded with the atte macro or the symbol equates to the 
            # wrong value.  Fix the one that is in error.

            tblscang tblr=3,ntryr=9
            cl     8,.LATTGE_tok(9)             # Token symbol and index match?
            jne    .LDF_drvreg64_badtok         # ..NO, internal error
            ahi    8,1                          # Increment index value
            tblnextg tblr=3,ntryr=9
            # All symbols and indexes match, can register

            # Locate the entry for this driver ID in the Driver Management Table
            lndxg  r=1,tblr=2,ndxr=7,error=.LDF_drvreg64_badid  # Die if out of bounds
            lg     0,0(1)                       # Fetch the id's DMT entry
            lgr    0,0                          # ..Is this ID already registered?
            jz    .LDF_drvreg64_dup             # ..Yes, die on duplicate
            stg   3,0(1)                        # Register the driver

            returnx

.LDF_drvreg64_nodmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_drvreg64_badid:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_drvreg64_dup:
            drvabort error=.LDRV_ddup,dtype=.LDRV_CMN
.LDF_drvreg64_badtok:
            drvabort error=.LDRV_bdtk,dtype=.LDRV_CMN

            .eject
  # +---------------------------------------+
  # |  64-bit ACTION TOKEN 2 - Open Device  |
  # +---------------------------------------+
  # Access: public
  # Token: .LCMN_Opn_Dev - 0x00000002

  # On Entry:
  #     R2     Device Request Block Address
  #     R13    Function base register
  #     R14    Function return address
  #     R15    ABI Stack pointer
  #
  # Used:
  #     R1     Work register
  #     R6     Active ASB
  #     R7     Device Definition Entry of device being opened
  #     R8     Controlling driver
  #     R9     Driver Management Table address
  #     R10    Device ID 
  #     R11    Shared subroutine return address
  #     R12    Caller's DRB
  #
  # On Exit:
  #     R2     DMT address

            functionx .LCMNG_2

    # Local literal pool usage:
.LCMNG_2_daf64:
            .quad  .LDF_daf64

            pushx

     # Process the device number / SSID

            lgr    12,2                     # Preserve caller's DRB address
            llgt   7,.LDRB_dde(12)          # Locate the DDE
            llgh   8,.LDRB_misc(12)         # Fetch the controlling driver's id
            llgf   2,.LDRB_addr32(12)       # Fetch the device ID
            tm     .LDRB_addr32+1(12),0x01  # Already a subchannel?
            jo     .LDF_opndev64_devid      # ..Yes, also do not need to find it

            lg     6,.LIEIB_asbg(0)         # Locate the active ASB
            lg     1,.LASBG_find(6)         # Locate the abstraction
            callrx 1                        # FIND SUBCHANNEL abstraction
            cl     2,.LDRB_addr32(12)       # Did we find the subchannel?
            jne    .LDF_opndev64_devid      # ..yes, device number not returned

            drvabort error=.LDRV_nosc,dtype=.LDRV_CMN

    # Enable the device
.LDF_opndev64_devid:
            lgr    10,2                     # Save the device ID
            lg     1,.LASBG_ena(6)          # Locate the abstraction
            callrx 1                        # FIND SUBCHANNEL abstraction
            ltr    2,2                      # Did we enable the subchannel?
            jnz    .LDF_devopn64_noena      # ..No, die!

            ltgr   8,8                      # Is driver id provided by caller?
            jnz    .LDF_devopn64_as         # ..yes, Caller is supplying id, use it

            # The caller expects the driver framework to figure out the device
            # To be implemented (someday)
            drvabort error=.LDRV_tbd,dtype=.LDRV_CMN

.LDF_devopn64_as:
            lg     9,.LCMNG_dmt-0b(13)      # Locate the DMT
            ltgr   9,9                      # Is, the framework initialized?
            jz     .LDF_devopn64_nodmt      # ..No, die!

            # Locate the entry for this driver ID in the Driver Management Table
            lndxg  r=1,tblr=9,ndxr=8,error=.LDF_devopn64_badid  # Die if out of bounds
            # R1 now points to the controlling driver's DMT entry

            lg     1,0(1)                   # Fetch the driver's ATT address

            ltgr   1,1                      # Is the driver registered?
            jz     .LDF_devopn64_drvnor     # ..No, driver is not registered, die

            stg    1,.LDDGE_att(7)          # Set the device driver's ATT in DDE
            sth    8,.LDDE_drvid(7)         # Set the driver ID in use.
            st     10,.LIOLO_dev(7)         # Set the device ID in DDE
            mvc    .LDDGE_daf(8,7),.LCMNG_2_daf64-0b(13)  # Set the DAF address

            returnx

.LDF_devopn64_nodmt:
            drvabort error=.LDRV_nodf,dtype=.LDRV_CMN
.LDF_devopn64_badid:
            drvabort error=.LDRV_dbdr,dtype=.LDRV_CMN
.LDF_devopn64_drvnor:            
            drvabort error=.LDRV_nodr,dtype=.LDRV_CMN
.LDF_devopn64_noena:
            drvabort error=.LDRV_noen,dtype=.LDRV_CMN

            .eject
  # +------------------------------------------+
  # |  64-bit Table Builder Shared Subroutine  |
  # +------------------------------------------+

  # On Entry:
  #     R2     Address where table is to reside
  #     R3     Number of table entries
  #     R4     Size of each table entry
  #     R5     Size of the header extension
  #     R10    Shared subroutine base register
  #     R11    Shared subroutine return address
  #
  # Used:
  #     R1     Work register
  #
  # On Exit:
  #     R2     Pointer to the built table

.LDF_table64:
0:
            tblbldg tblr=2,nr=3,sr=4,hdr=5,wrkr=1
            br     11                 # Return to caller

.LCMNG_dmt: .quad  0   # Address of the Driver Management Table

.endif # .if .Lhal_64bit

            .eject
  # +-------------------------------------------+
  # |  32/64-bit CCW Builder Shared Subroutine  |
  # +-------------------------------------------+

  # On Entry:
  #     R2     I/O data area (.LIOLO structure)
  #     R3     Address of the current CCW builder structure entry (cbs macro)
  #     R4     Address of a list of model CCWs (referenced by cbs)
  #     R5     Address of the user area within the sdwa (used now)
  #     R6     Number of CCWs left to be built
  #     R7     Current CCW being built
  #     R10    Shared subroutine base address
  #     R11    Shared subroutine return address
  #
  # Used:
  #     R1     Work register
  #     R8     
  #     R9
  #     R12    
  #
  # On Exit:
  #     R8     Bits 0-31 of CCW address
  #     R9     Bits 32-64 of CCW address

.Ldrv_ccw_rtn:
0:
            mvc    .LCCW1_cmd(1,7),.Lcbs_cmd(3)       # Move the command code
            mvc    .LCCW1_flags(1,7),.Lcbs_flags(3)   # Move the flags

            lh     1,.Lcbs_count(3)         # Fetch count information
            ltr    1,1                      # ..Program size?
            bm     .Ldrv_ccw_plen-0b(10)    # ..Yes, use size from SDWA

            # Use the count from the CCW builder structure entry
            sth    1,.LCCW1_cnt(7)          # Set the CCW length
            b      .Ldrv_ccw_addr-0b(10)    # Setup the address in the CCW

.Ldrv_ccw_plen:
            mvc    .LCCW1_cnt(2,7),8(5)     # Move the program data length

.Ldrv_ccw_addr:
            cli    0(7),.LCCW_TIC           # TRANSFER-IN-CHANNEL Command?
            be     .Ldrv_ccw_tic-0b(10)     # ..Yes, handle TIC

    # Not TRANSFER-IN-CHANNEL
            lh     1,.Lcbs_data(3)          # Fetch the data pointer
            ltr    1,1                      # Program data?
            bm     .Ldrv_ccw_pdat-0b(10)    # ..Yes, use user supplied address

    # CCW address within the sdwa
            sr     8,8                      # High-order bits are zero
            la     9,0(1,2)                 # Locate the sdwa data area
            br     11

.Ldrv_ccw_tic:
     # TRANSFER-IN-CHANNEL CCW address within CCW chain
            lh     1,.Lcbs_data(3)          # Fetch the data pointer
            sll    1,3                      # Turn it into a CCW displacement
            la     9,0(10,1)                # Calculate the CCW address (low-order)
            sr     8,8                      # High-order bits are zero
            br     11                       # Return to caller

.Ldrv_ccw_pdat:
     # CCW address supplied by caller in the sdwa program area
            lm     8,9,0(5)                 # Setup data address for FORMAT CCW
            br     11                       # Return to caller

.endif # .ifndef .Ldriver_S
