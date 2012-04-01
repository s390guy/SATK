.ifndef .Larch_S
.Larch_S = 1
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

 # Set symbols for the architecture values
         .macro archs s370bc=.Larch_s370bc s370ec=.Larch_s370ec s390=.Larch_s390 z=.Larch_z
\s370bc = 0   # System/370 Basic-control mode
\s370ec = 1   # System/370 Extended-control mode
\s390   = 2   # ESA/390 mode
\z      = 3   # z/Architecture mode
         .endm

  # Probe the running architecture

         .macro probarch s370bc=.Lra_0 s370ec=.Lra_1 s390=.Lra_2 z=.Lra_3 br=15 b=0b
         .align 2
         la     0,(1f+32)-\b(\br)     # Locate the System/370 mode detection logic
         stcm   0,0x7,(1f+5)-\b(\br)  # Set up the program new PSW
         la     0,\s390-\b(\br)   # Locate the ESA/390 logic
         o      0,(1f+12)-\b(\br) # Make sure 31-bit addressing is used
         st     0,(1f+12)-\b(\br) # Set the address in the new SVC PSW
         la     0,\z-\b(\br)      # Locate the z/Architecture logic
         st     0,(1f+28)-\b(\br) # Set the address in the new SVC PSW
         mvc    0x1D0(16,0),(1f+16)-\b(\br)  # Set the new z SVC PSW
         mvc    0x060(8,0),(1f+8)-\b(\br)    # Set the new ESA/390 SVC PSW
         mvc    0x068(8,0),1f-\b(\br)        # Set the S/370 new program PSW
         svc    0xFF              # Issue the SVC
         .align 4
1:       .hword 0x0008,0x0000,0x0000,0x0000  # 1f    8-bytes s/370 new pgm PSW
         .hword 0x0008,0x0000,0x8000,0x0000  # 1f+8  8-bytes ESA/390 new SVC PSW
         .hword 0x0008,0x0000                # 1f+16 4-bytes z/Architecture..
         .long  0x80000000,0                 # 1f+20 8-bytes ..new SVC
         .long  0                            # 1f+28 4-bytes ..PSW
         oc     0x02A(2,0),0x02A(0)  # Does the old PSW have a code?
         bnz    \s370bc-\b(\br)      # Yes, this means BC-mode
         b      \s370ec-\b(\br)      # No, this means EC-mode
         .endm

 # Establish the global runarch and runarchg variables

         .macro runarch s370bc=.Lra_0 s370ec=.Lra_1 s390=.Lra_2 z=.Lra_3 br=15 b=0b
         b      1f-\b(\br)
         .align 8
runarchg:.global runarchg
         .long  -1
runarch: .global runarch
         .long  -1
\s370bc:
         mvi    runarchg+7-\b(\br),0x00
         b      1f-\b(\br)
\s370ec:
         mvi    runarchg+7-\b(\br),0x01
         b      1f-\b(\br)
\s390:
         mvi    runarchg+7-\b(\br),0x02
         b      1f-\b(\br)
\z:
         mvi    runarchg+7-\b(\br),0x03
1:       xc     runarchg-\b(7,\br),runarchg-\b(\br)
         .endm

 # Set a desired architecture
 #   This macro is dependent upon setarch routine
 #   being included in the assembly from setarch.S

         .macro setarch current desired wrkr br=15 b=0b
         lr     0,\current       # Set the current architecture
         lr     1,\desired       # Set the desired architecture

         clr    1,0              # Are we in the architecture we want?
         be     3f-\b(\br)       # ..Yes, don't bother with the call
         cl     0,2f+4-\b(\br)   # Are we in z/Architecture?
         bne    1f-\b(\br)       # ..No, use a pointer call
         oc     8(8,\br),8(\br)  # Is this mainline?
         jnz    3f               # ..No, can not do the change
         # Yes, use a relative z/Architecture call to the routine
         callrelg .Lsetarchg,sar=13,retr=14,rtnr=15,stub=yes
         
         b      4f-\b(\br)       # Update the running architecture
         
1:       relo   2f,\br,\b,\wrkr  # Make the setarch routine addressable
         callp  2f,sar=13,retr=14,rtnr=15,pbr=\br,pb=\b,stub=yes
         b      4f-\b(\br)       # Update the running architecture

         .align 4
2:       .long  .Lsetarch-\b     # Displacement to the setarch routine
         .long  3                # z/Architecture designator

3:       dwait  code=.Ldw_notmain,program=0
         
4:       stc    1,runarch+3-\b(\br)  # Update the running arch
         .endm
         
 # Signal the running processor
 #    r1   = status register (even register of an even/odd pair)
 #    r1+1 = parameter (odd register of an even/odd pair)
 #           the parameter register must be set before issuing sigself
 #    d2   = order code
 #    r3   = CPU address
 #    
         .macro sigself cpur statr order=0x00 br=15 b=0b
         stap   1f-\b(\br)           # Save the CPU address of this CPU
         lh     \cpur,1f-\b(\br)     # Set the CPU address
         sigp   \statr,\cpur,\order  # Signal myself
         b      1f+2-\b(\br)         # Branch around CPU address
1:       .hword 0   # Where the CPU ID is stored
         .endm
         
 # Set System/370 architecture
         
         .macro s370arch succeed fail cpur=2 statr=0 br=15 b=0b
         la     (\statr+1),37     # Set parm for S/370 (Hercules only)
         sigself cpur=\cpur,statr=\statr,order=0x12,br=\br,b=\b
         bc     8,\succeed-\b(\br)
         b      \fail-\b(\br)
         .endm
         
 # Set ESA/390 architecture
 
         .macro s390arch succeed fail cpur=2 statr=0 br=15 b=0b
         sr     (\statr)+1,(\statr)+1 # Set parm for z/Arch to ESA/390
         sigself cpur=\cpur,statr=\statr,order=0x12,br=\br,b=\b
         bc     8,\succeed-\b(\br)
         b      \fail-\b(\br)
         .endm

 # Set z/Architecture

         .macro s390xarch succeed fail cpur=2 statr=0 br=15 b=0b
         la     (\statr)+1,1       # Set parm for z/Arch to ESA/390
         sigself cpur=\cpur,statr=\statr,order=0x12,br=\br,b=\b
         bc     8,\succeed-\b(\br)
         b      \fail-\b(\br)
         .endm

.endif  # .ifndef .Larch_S scope
