Copyright (C) 2013 Harold Grovesteen

    This file is part of SATK.

    SATK is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    SATK is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with SATK.  If not, see <http://www.gnu.org/licenses/>.

                              SATK Samples
                      
The 'samples' directory contains examples and tests of various SATK components.
All device types have not been tested in all settings.  All devices have been tested
but not in all CPU architectures.  All CPU architectures have been tested but not 
with all devices.  The tool kit is now starting to include builds and testable 
device images.  These will expand over time.  Previously testing had been done 
outside of the tool kit and only the base software was provided.  The FBA device
type has been tested the most.

The following directories are provided:

     decklodr  Tests loading an ELF embedded within an object deck of emulated card 
               images.  The object contains the usual TXT records, etc.  The TXT
               records contain the ELF executable itself.
     embedded  Builds and tests various device type images created from an IPL ELF
               executable that includes an embedded boot loader.
               The device image contains
                  - a boot loader targeting various CPU architectures that  
                  - enters a program it loads from the device.
     external  Builds and tests various device type images created from:
                  - an IPL ELF executable targeting various CPU architectures and 
                  - a loader from a separate IPL ELF executable, for example as 
                    found in the embedded directory.
     ihandlers Builds an IPL ELF that tests the HAL interrupt handler processes in
               different CPU architectures loaded from an FBA device.
     iplelf    Builds and tests various device type images containing:
                   - an IPL ELF executable and 
                   - its direct IPL in various CPU architectures.
     textseg   Builds and tests various device type images containing:
                   - a TEXT segment from an IPL ELF executable and 
                   - its direct IPL in various CPU architectures.

Common code and any bash scripts are in the samples/xxxx directory to which they 
apply.  Each class of devices will have its own sub-directory.  Each CPU 
architecture has its own subdirectory for the device type.  The CPU architecture
directory has two sub directories: build and test.  The IPL ELF executable is 
built within the 'build' directory and the IPL ready device is test results are in
the 'test' directory.  The CPU architecture will be: s370, s370bc, s390 or s390x.
The supported device classes are: card, cdrom, ckd, fba and tape.  SATK builds
the device images.

This is the directory structure used for example with a fba device.  The SATK 
bash functions use a single module name to identify most of the build files.  In
the sample below the module name is 'module'.  In some cases, files related to 
more than one module may be present.

fba/<CPU-arch>/hercules.<env>.<date>.<time>.log - Hercules test console log
               module.3310     - IPL ready device of type 3310 (from iplmed.py)
               <CPU-arch>.conf - Hercules configuration file
               <CPU-arch>.rc   - Hercules RC file 
               build/module         - IPL ELF executable (from GNU ld)
                     module.exe.txt - IPL ELF executable content (from objdump)
                     module.lst     - Assembler listing (from GNU as)
                     module.lds     - Linkage editor statements (from ipldpp.py) 
                     module.map     - Linkage editor map (from GNU ld)
                     module.o       - IPL ELF object (from GNU as)
                     module.obj.txt - IPL ELF object content (from objdump)
    
The test matrices provided below describe the level of testing done and whether
the particular device/CPU architecture combination is included with the tool kit
repository.  'tested' indicates the combination has been built and tested external 
to SATK.  'SATK' indicates the combination is available in the repository.
    
The remainder of this file contains notes about specific sample directories.

embedded directory
------------------

The embedded directory uses the module name 'default'.
Devices built to directly IPL the program without a loader use the name 
'default.<device_type>'.
Devices built to IPL a boot loader which then loads the program from the device use
the name 'embed.<device_type>'.

Test/availability matrix for IPL ELF loaded directly by the IPL function.

+----------------------------------------------------------+
|   Device   |                CPU architecture             |
|    Type    |---------------------------------------------+
|            |   s370bc  |  s370   |    s390    |   s390x  |
+------------+-----------+---------+------------+----------+
|    card    |     --    |   --    |   tested   |     --   |
+------------+-----------+---------+------------+----------+
|   cdrom    |     --    |   --    |   tested   |     --   |
+------------+-----------+---------+------------+----------+
|    ckd     |     --    |   --    |   tested   |     --   |
+------------+-----------+---------+------------+----------+
|    fba     |     --    |   --    |   tested   |     --   |
+------------+-----------+---------+------------+----------+
|    tape    |     --    |   --    |   tested   |     --   |
+------------+-----------+---------+------------+----------+


iplelf directory
----------------

The textseg directory uses the module name 'iplelf'.
Devices built to directly IPL the program's complete IPL ELF uses the name
'iplelf.<device_type>'.

Test/availability matrix for IPL ELF loaded directly by the IPL function.

+----------------------------------------------------------+
|   Device   |                CPU architecture             |
|    Type    |---------------------------------------------+
|            |   s370bc  |  s370   |    s390    |   s390x  |
+------------+-----------+---------+------------+----------+
|    card    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|   cdrom    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|    ckd     |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|    fba     |    SATK   |  SATK   |    SATK    |   SATK   |
+------------+-----------+---------+------------+----------+
|    tape    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+


textseg directory
-----------------

The textseg directory uses the module name 'textseg'.
Devices built to directly IPL the program's TEXT segment use the name
'textseg.<device_type>'.

Test/availability matrix for IPL ELF loaded directly by the IPL function.

+----------------------------------------------------------+
|   Device   |                CPU architecture             |
|    Type    |---------------------------------------------+
|            |   s370bc  |  s370   |    s390    |   s390x  |
+------------+-----------+---------+------------+----------+
|    card    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|   cdrom    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|    ckd     |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+
|    fba     |    SATK   |  SATK   |    SATK    |   SATK   |
+------------+-----------+---------+------------+----------+
|    tape    |     --    |   --    |     --     |    --    |
+------------+-----------+---------+------------+----------+