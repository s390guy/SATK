#!/usr/bin/env python
# -*- coding: utf-8 -*-

this_module="forth_words.py"

definitions="""\
\ vim:ft=forth
\
\ Forth core language definitions.
\
\ Thanks to Richard W.M. Jones <rich@annexia.org> http://annexia.org/forth
\ Most parts of this file are based on his jonesforth, which is licensed as
\ public domain.

: 2DROP ( n n -- ) DROP DROP ;
: 2DUP  ( y x -- y x y x ) OVER OVER ;

\ The primitive word /MOD [DIVMOD] leaves both the quotient and the remainder
\ on the stack.  Now we can define the / and MOD in terms of /MOD and a few
\ other primitives.
: /   ( n -- n ) /MOD SWAP DROP ;
: MOD ( n -- n ) /MOD DROP ;

( simple math )
: 1+ ( n -- n ) 1 + ;   ( increment by one )
: 1- ( n -- n ) 1 - ;   ( decrement by one )
: 4+ ( n -- n ) 4 + ;   ( increment by four )
: 4- ( n -- n ) 4 - ;   ( decrement by four )

( Define some character constants )
( > ASCII code for line feed. )
: LF   10 ;
( > BL [BLank] is a standard FORTH word for space. )
: BL   32 ;

( > CR prints a carriage return. )
: CR 13 EMIT ;

( > SPACE prints a space. )
: SPACE BL EMIT ;

( > NEGATE leaves the negative of a number on the stack. )
: NEGATE 0 SWAP - ;

( Standard words for booleans. )
-1 CONSTANT TRUE
0 CONSTANT FALSE
: NOT   0= ;

( LITERAL takes whatever is on the stack and compiles LIT <foo> )
: LITERAL IMMEDIATE
        ' $LIT ,        \ compile LIT
        ,               \ compile the literal itself (from the stack)
        ;


\ Now we can use [ and ] to insert literals which are calculated at compile
\ time.  (Recall that [ and ] are the FORTH words which switch into and out of
\ immediate mode.) Within definitions, use [ ... ] LITERAL anywhere that '...' is
\ a constant expression which you would rather only compute once (at compile
\ time, rather than calculating it each time your word runs).
: ':'
        [               \ go into immediate mode (temporarily)
        CHAR :          \ push the number 58 (ASCII code of colon) on the parameter stack
        ]               \ go back to compile mode
        LITERAL         \ compile LIT 58 as the definition of ':' word
;


( A few more character constants defined the same way as above. )
: ';' [ CHAR ; ] LITERAL ;
: '(' [ CHAR 40 ] LITERAL ;
: ')' [ CHAR ) ] LITERAL ;
: '"' [ CHAR 34 ] LITERAL ;  ( " vim syntax hack )
: 'A' [ CHAR A ] LITERAL ;
: '0' [ CHAR 48 ] LITERAL ;
: '-' [ CHAR - ] LITERAL ;
: '.' [ CHAR . ] LITERAL ;

\      CONTROL STRUCTURES ----------------------------------------------------------------------
\
\ So far we have defined only very simple definitions.  Before we can go
\ further, we really need to make some control structures, like IF ... THEN and
\ loops.  Luckily we can define arbitrary control structures directly in FORTH.
\
\ Please note that the control structures as I have defined them here will only
\ work inside compiled words.  If you try to type in expressions using IF, etc.
\ in immediate mode, then they won't work.  Making these work in immediate mode
\ is left as an exercise for the reader.
\
( > Examples:
( >
( > - ``condition IF true-part THEN rest`` )
\      -- compiles to: --> condition 0BRANCH OFFSET true-part rest
\      where OFFSET is the offset of 'rest'
( > - ``condition IF true-part ELSE false-part THEN`` )
\      -- compiles to: --> condition 0BRANCH OFFSET true-part BRANCH OFFSET2 false-part rest
\      where OFFSET if the offset of false-part and OFFSET2 is the offset of rest
\
\ alternate form with mor common wording
( > - ``condition IF true-part ELSE false-part ENDIF`` )
\ IF is an IMMEDIATE word which compiles 0BRANCH followed by a dummy offset, and places
\ the address of the 0BRANCH on the stack.  Later when we see THEN, we pop that address
\ off the stack, calculate the offset, and back-fill the offset.

: IF IMMEDIATE
        ' $BRANCH0 ,    \ compile 0BRANCH
        HERE            \ save location of the offset on the stack
        0 ,             \ compile a dummy offset
;

( > See IF_. )
: THEN IMMEDIATE
        DUP
        HERE SWAP -     \ calculate the offset from the address saved on the stack
        SWAP !          \ store the offset in the back-filled location
;

( > Alias for THEN_, See IF_. )
: ENDIF IMMEDIATE
        DUP
        HERE SWAP -     \ calculate the offset from the address saved on the stack
        SWAP !          \ store the offset in the back-filled location
;

( > See IF_. )
: ELSE IMMEDIATE
        ' $BRANCH ,     \ definite branch to just over the false-part
        HERE            \ save location of the offset on the stack
        0 ,             \ compile a dummy offset
        SWAP            \ now back-fill the original (IF) offset
        DUP             \ same as for THEN word above
        HERE  SWAP -
        SWAP !
;


( > Example: ``BEGIN loop-part condition UNTIL`` )
\      -- compiles to: --> loop-part condition 0BRANCH OFFSET
\      where OFFSET points back to the loop-part
\ This is like do { loop-part } while (condition) in the C language
: BEGIN IMMEDIATE
         HERE            \ save location on the stack
;

( > See BEGIN_. )
: UNTIL IMMEDIATE
        ' $BRANCH0 ,    \ compile 0BRANCH
        HERE  -         \ calculate the offset from the address saved on the stack
        ,               \ compile the offset here
;

( > BEGIN loop-part AGAIN )
\      -- compiles to: --> loop-part BRANCH OFFSET
\      where OFFSET points back to the loop-part
\ In other words, an infinite loop which can only be returned from with EXIT
: AGAIN IMMEDIATE
        ' $BRANCH ,     \ compile BRANCH
        HERE  -         \ calculate the offset back
        ,               \ compile the offset here
;

( > Example: ``BEGIN condition WHILE loop-part REPEAT`` )
\      -- compiles to: --> condition 0BRANCH OFFSET2 loop-part BRANCH OFFSET
\      where OFFSET points back to condition (the beginning) and OFFSET2
\      points to after the whole piece of code
\ So this is like a while (condition) { loop-part } loop in the C language
: WHILE IMMEDIATE
        ' $BRANCH0 ,    \ compile 0BRANCH
        HERE            \ save location of the offset2 on the stack
        0 ,             \ compile a dummy offset2
;

( > See WHILE_. )
: REPEAT IMMEDIATE
        ' $BRANCH ,     \ compile BRANCH )
        SWAP            \ get the original offset (from BEGIN)
        HERE  - ,       \ and compile it after BRANCH
        DUP
        HERE SWAP -     \ calculate the offset2
        SWAP !          \ and back-fill it in the original location
;

( > UNLESS is the same as IF_ but the test is reversed. )

\ Note the use of [COMPILE]: Since IF is IMMEDIATE we don't want it to be
\ executed while UNLESS is compiling, but while UNLESS is running (which happens
\ to be when whatever word using UNLESS is being compiled -- whew!).  So we use
\ [COMPILE] to reverse the effect of marking IF as immediate.  This trick is
\ generally used when we want to write our own control words without having to
\ implement them all in terms of the primitives 0BRANCH and BRANCH, but instead
\ reusing simpler control words like (in this instance) IF.
: UNLESS IMMEDIATE
        ' NOT ,         \ compile NOT (to reverse the test)
        [COMPILE] IF    \ continue by calling the normal IF
;


( Some more complicated stack examples, showing the stack notation. )
: NIP ( x y -- y ) SWAP DROP ;
: TUCK ( x y -- y x y ) SWAP OVER ;

( With the looping constructs, we can now write SPACES, which writes n spaces to stdout. )
( > Write given number of spaces. Example:: ``20 SPACES``.)
: SPACES        ( n -- )
        BEGIN
                DUP 0>          \ while n > 0
        WHILE
                SPACE           \ print a space
                1-              \ until we count down to 0
        REPEAT
        DROP
;



( > ? Fetches the integer at an address and prints it. )
: ? ( addr -- ) @ . ;

( > ``c a b WITHIN`` returns true if a <= c and c < b )
( > or define without ifs: ``OVER - >R - R>  U<``  )
: WITHIN
        -ROT            ( b c a )
        OVER            ( b c a c )
        <= IF
                > IF            ( b c -- )
                        TRUE
                ELSE
                        FALSE
                THEN
        ELSE
                2DROP           ( b c -- )
                FALSE
        THEN
;


\       CASE ----------------------------------------------------------------------
\
\       CASE...ENDCASE is how we do switch statements in FORTH.  There is no generally
\       agreed syntax for this, so I've gone for the syntax mandated by the ISO standard
\       FORTH (ANS-FORTH).
( > ::
( >
( >               (some value on the stack)
( >               CASE
( >               test1 OF ... ENDOF
( >               test2 OF ... ENDOF
( >               testn OF ... ENDOF
( >               ... (default case)
( >               ENDCASE
)
\       The CASE statement tests the value on the stack by comparing it for equality with
\       test1, test2, ..., testn and executes the matching piece of code within OF ... ENDOF.
\       If none of the test values match then the default case is executed.  Inside the ... of
\       the default case, the value is still at the top of stack (it is implicitly DROP-ed
\       by ENDCASE).  When ENDOF is executed it jumps after ENDCASE (ie. there is no "fall-through"
\       and no need for a break statement like in C).
\
\       The default case may be omitted.  In fact the tests may also be omitted so that you
\       just have a default case, although this is probably not very useful.
\
\       An example (assuming that 'q', etc. are words which push the ASCII value of the letter
\       on the stack):
\
\               0 VALUE QUIT
\               0 VALUE SLEEP
\               KEY CASE
\                       'q' OF 1 TO QUIT ENDOF
\                       's' OF 1 TO SLEEP ENDOF
\                       (default case:)
\                       ." Sorry, I didn't understand key <" DUP EMIT ." >, try again." CR
\               ENDCASE
\
\       (In some versions of FORTH, more advanced tests are supported, such as ranges, etc.
\       Other versions of FORTH need you to write OTHERWISE to indicate the default case.
\       As I said above, this FORTH tries to follow the ANS FORTH standard).
\
\       The implementation of CASE...ENDCASE is somewhat non-trivial.  I'm following the
\       implementations from here:
\       http://www.uni-giessen.de/faq/archiv/forthfaq.case_endcase/msg00000.html
\
\       The general plan is to compile the code as a series of IF statements:
\
\       CASE                            (push 0 on the immediate-mode parameter stack)
\       test1 OF ... ENDOF              test1 OVER = IF DROP ... ELSE
\       test2 OF ... ENDOF              test2 OVER = IF DROP ... ELSE
\       testn OF ... ENDOF              testn OVER = IF DROP ... ELSE
\       ... (default case)            ...
\       ENDCASE                         DROP THEN [THEN [THEN ...]]
\
\       The CASE statement pushes 0 on the immediate-mode parameter stack, and that number
\       is used to count how many THEN statements we need when we get to ENDCASE so that each
\       IF has a matching THEN.  The counting is done implicitly.  If you recall from the
\       implementation above of IF, each IF pushes a code address on the immediate-mode stack,
\       and these addresses are non-zero, so by the time we get to ENDCASE the stack contains
\       some number of non-zeroes, followed by a zero.  The number of non-zeroes is how many
\       times IF has been called, so how many times we need to match it with THEN.
\
\       This code uses [COMPILE] so that we compile calls to IF, ELSE, THEN instead of
\       actually calling them while we're compiling the words below.
\
\       As is the case with all of our control structures, they only work within word
\       definitions, not in immediate mode.
: CASE IMMEDIATE
        0               \ push 0 to mark the bottom of the stack
;

( > See CASE_. )
: OF IMMEDIATE
        ' OVER ,        \ compile OVER
        ' = ,           \ compile =
        [COMPILE] IF    \ compile IF
        ' DROP ,        \ compile DROP
;

( > See CASE_. )
: ENDOF IMMEDIATE
        [COMPILE] ELSE  \ ENDOF is the same as ELSE
;

( > See CASE_. )
: ENDCASE IMMEDIATE
        ' DROP ,        \ compile DROP

        ( keep compiling THEN until we get to our zero marker )
        BEGIN
                ?DUP
        WHILE
                [COMPILE] THEN \ aka ENDIF
        REPEAT
;


( > Compile LIT_. )
: ['] IMMEDIATE
        ' $LIT ,         \ compile LIT
;

"""

if __name__ == '__main__':
    raise NotImplementedError("module %s only intended for import use" % this_module) 