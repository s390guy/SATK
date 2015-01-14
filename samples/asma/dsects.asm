* Copyright (C) 2015 Harold Grovesteen
*
* This file is part of SATK.
*
*     SATK is free software: you can redistribute it and/or modify
*     it under the terms of the GNU General Public License as published by
*     the Free Software Foundation, either version 3 of the License, or
*     (at your option) any later version.
*
*     SATK is distributed in the hope that it will be useful,
*     but WITHOUT ANY WARRANTY; without even the implied warranty of
*     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*     GNU General Public License for more details.
*
*     You should have received a copy of the GNU General Public License
*     along with SATK.  If not, see <http://www.gnu.org/licenses/>.

         TITLE 'dsects.asm - Stand-Alone Tool Kit DSECTs'
* This program assembles all SATK standard DSECTs.  DSECTs are placed in alphabetical
* order.
         PRINT OFF,NOPRINT
         COPY  'satk.mac'
         COPY  'function.mac'
         COPY  'table.mac'
         PRINT ON,NOPRINT
         TITLE 'ARCHLVL  dsects.asm'
         ARCHLVL
         SPACE 1
         TITLE 'ASA      dsects.asm'
         DSECTS NAME=ASA
         SPACE 1
         TITLE 'ASAZ     dsects.asm'
         DSECTS NAME=ASAZ
         SPACE 1
         TITLE 'CCW0     dsects.asm'
         DSECTS NAME=CCW0
         SPACE 1
         TITLE 'CCW1     dsects.asm'
         DSECTS NAME=CCW1
         SPACE 1
         TITLE 'CSW      dsects.asm'
         DSECTS NAME=CSW
         SPACE 1
         TITLE 'FRAME    dsects.asm'
         DSECTS NAME=FRAME   Depends upon architecture level
         SPACE 1
         TITLE 'IOCB     dsects.asm'
         DSECTS NAME=IOCB
         SPACE 1
         TITLE 'IRB      dsects.asm'
         DSECTS NAME=IRB
         SPACE 1
         TITLE 'ORB      dsects.asm'
         DSECTS NAME=ORB
         SPACE 1
         TITLE 'PSW      dsects.asm'
         DSECTS NAME=PSW     Depends upon architecture level
         SPACE 1
         TITLE 'SCHIB    dsects.asm'
         DSECTS NAME=SCHIB
         SPACE 1
         TITLE 'SCSW     dsects.asm'
         DSECTS NAME=SCSW
         SPACE 1
         TITLE 'TBL      dsects.asm'
         DSECTS NAME=TABLE
         SPACE 1
         END