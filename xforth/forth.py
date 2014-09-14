#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Chris Liechti <cliechti@gmx.net>
# All Rights Reserved.
# Simplified BSD License (see LICENSE.txt for full text)

"""\
Minimalistic Forth like language interpreter.

Its purpose is to process files in Forth syntax, provide an environment to
execute its functions.  Forth functions are stored in a way that allows to
cross compile them to targeted assembler code.  Native code functions are also
supported with "CODE ... END-CODE" but they are not executable on the host.

Cross compiling includes selection of only the used functions. The program on
the target does not provide a (interactive) Forth system (unless the user
program creates it).

XXX Currently under development - not all useful words are yet defined!
"""

# This module, forth.py, is based upon python-msp430-tools found at 
# https://pypi.python.org/pypi/python-msp430-tools/0.6
#
# The majority of the MSP430 package is designed to cross-compile a Forth application
# or system for the MSP430 embedded processor.  Only the basic Forth interpreter
# written in Python from the MSP430 package has been incorporaed into this project.
# The remaining tool chain modules and MSP430 explicit code were not utilized.
#
# This module is based upon the following files from the MSP430 package:
#    - python-msp430-tools/msp430/asm/forth.py
#    - python-msp430-tools/msp430/asm/rpn.py
#    - python-msp430-tools/msp430/asm/forth/__init__.forth
#
# The Python Forth interpreter from the MSP430 package has been modified in the
# following ways:
#   1. It has been structured as a single module rather than the original two:
#      forth.py and rpn.py.
#   2. ForthError has replaced the RPNError exception class entirely
#   3. The rpn.RPNBase class has been merged into the Forth class creating a single
#      interpreter class.  rpn.py is used by MSP430 as a text parser in other
#      contexts.  For the objectives of this project a single forth.py module was
#      preferred.
#   4. Mixin word definition classes rpn.RPNBitOps and rpn.RPNLogicOps and 
#      class RPN eliminated.  The RPN class was replaced by the Forth class. 
#   4. Mixin word definition classes have all been merged into the Forth class.
#   5. The file __init__.forth has been converted into the module forth_words.py.
#      It has been kept separate due to its public domain licensing.
#   6. Functions eval(), python_function() and rpn_function() are commented out due to 
#      lack of usage.  They are preserved as comments solely to document them in case
#      their is an unperceived need for them.
#   6. Non-functional coding style changes mostly related to method or class
#      sequencing within the module.
#   7. Comments relating to the design and structure of the interpreter.
#
# The following corrections or functional changes have been made:
#   1. Word \n in forth_words.py eliminated because it just will not compile with 
#      the utf-8 codecs correctly.  The original file coded it as '\n'.  The resulting
#      word name included the quotes.  Any elimination of the quotes caused a utf8
#      codec error.
#   2. Word CR in forth_words.py changed to use ASCII carriage-return character
#      explicitly rather than the eliminated \n word.
#   3. Forth._include() method usage of the words_in_file function changed to 
#      include_newline=True.  With include_newline=False (the default) included
#      files were not compiled.  The use of line comments requires
#      include_newline=True, otherwise a line comment will never terminate.
#   4. Forth.init() method may use either the string from forth_words.py module or
#      explicitly include the __init__.forth file depending upon the usefile
#      keyword argument.  A debug argument has been added that causes the namespaces
#      to be displayed by the forth.word_LIST() method when set to True.  By default
#      the forth_words.py module is used.  See the comment in the main() method.
#
# Following these changes, this forth interpreter should remain functional
# with the MSP430 package under Python 2.7.  Explicit testing was not successful
# due to the lack of the file msp430.forth, a file included by the forth example
# source files, but not distributed with the MSP430 package.  It may exist elsewhere,
# but attempts by the author to locate it failed.
#
# Numerous changes are planned for the Forth cross-compiler that will break it
# for use with MSP430 (without additional work).  The module xforth.py in this
# project will incorporate these changes, turning this Forth interpreter into a
# generic extensible cross-compiler.  As it stands, this module is the foundation
# for these extensions in the xforth.py module.  This module's real purpose was to
# familiarize the author with the MSP430 Forth implementation.
#
# I want to express my personal thanks to Chris Liechti and the other contributors
# to the MSP430 package for the Forth interpreter.  The interpreter provides a
# significant jump start in the targeting of a Python Forth cross-compiler to a
# different processor architecture.  Forth-based cross-compilers require an
# interpreter as their foundation.  MSP430 provides a readily extensible one.
#
# Thank you,
# Harold Grovesteen


# Python imports
from __future__ import division
import sys
import os
import codecs
import logging
import pprint
import re

# other imports:
import forth_words   # Access high-level definitions used by both host and target
definitions=forth_words.definitions.decode("utf8","replace")

m_comment = re.compile('(#.*$)', re.UNICODE)    # regexp to remove line comments

#
#  +---------------------------------+
#  |                                 |
#  |   FORTH Interpreter Exception   |
#  |                                 |
#  +---------------------------------+
#

class ForthError(Exception):
    """interpreter error"""
    def __init__(self, message, filename=None, lineno=None, column=None, \
                 offset=None, text=None):
        Exception.__init__(self, message)
        self.filename = filename or '<unknown>'
        self.lineno = lineno
        self.column = column
        self.offset = offset
        self.text = text

    #~ def __str__(self):
        #~ return '%s:%s: %s' % (self.filename, self.lineno, self.message)

#
#  +----------------------------------------+
#  |                                        |
#  |   FORTH Interpreter Helper Functions   |
#  |                                        |
#  +----------------------------------------+
#

# The following functions support various activities involved in interpretation
# independent of the Forth object itself.

# Interator supporting that annotates the word's location before providing it to
# the user of the iterator of Word objects.
# Function arguments:
#   sequence   an iterable sequence of Word objects and unicode strings.
#   filename   Filename used to annotate each unicode string in the sequence.
#              Defaults to None.
#   lineno     Line number within the file of each unicode string in the sequence.
#              Defaults to None.
#   offset     Offset of each unicode string.  Ignored and defaults to None.
#   text       Annotated text for each unicode string.
def annotated_words(sequence, filename=None, lineno=None, offset=None, text=None):
    """Wrap words and annotate them with given filename etc."""
    for word in sequence:
        if isinstance(word, Word):
            yield word
        else:
            yield Word(word, filename, lineno, text)

#def eval(words, stack=[], namespace={}):
#    """evaluate code with given stack and return the topmost object from the stack"""
#    rpn = RPN(namespace)
#    if stack is not None:
#        for element in stack:
#            rpn.push(element)
#    rpn.interpret(iter(words))
#    return rpn.pop()

# Drives an interactive session with a Forth interpreter
# Function arguments:
#   namespace    Pre-established namespace if an interpreter object is not supplied.
#                Defaults to an empty dictionary.
#   debug        Set to True to cause unexpected exceptions to be raised.
#                Set to False to simply print unexpected exceptions without
#                terminating the interpreter.  Defaults to False.
#   rpn_class    The class of the interpreter if an instance is not supplied.
#                If the interpreter instance is not supplied with the rpn_instance
#                argument, this class will be instantiated and its init() method
#                will be called before the interactive session is started.
#                Defaults to the None in which case the class Forth is used.
#   rpn_instance An interpreter object used for the interactive session.  If supplied
#                the rpn_class argument is ignored.
def interpreter_loop(namespace={}, debug=False, rpn_class=None, rpn_instance=None):
    """run an interactive session"""
    if rpn_class is None:
        rpn_class=Forth

    if rpn_instance is None:
        rpn_instance = rpn_class(namespace)
        rpn_instance.init()
    while True:
        try:
            print
            print rpn_instance
            words = raw_input('> ')
            rpn_instance.interpret_sequence(words.split(), filename='<stdin>')
        except KeyboardInterrupt:
            print
            break
        except SystemExit:
            raise
        except Exception, msg:
            if debug: raise
            print "ERROR:", msg

#def python_function(code, namespace={}):
#    """wrapper command generator, used to wrap RPN and make it callable from python"""
#    def wrapper(*args):
#        return eval(code, args, namespace)
#    return wrapper

#def rpn_function(code):
#    """wrapper command generator, used to inject RPN functions into the namespace"""
#    def wrapper(stack):
#        stack.interpret(code)
#    return wrapper

# Word object iterator.  Words are identified from a possible multi-line string.
# Backslash line comments are removed before words are recognized.
# Function arguments:
#   data             The string from which words are identified.  Required.
#   name             A name used to annotate the Word object for words from the
#                    string.  Defaults to '<string>'.
#   include_newline  Specify True to cause a Word object to be generated for the
#                    line termination sequence.
def words_in_string(data, name='<string>', include_newline=False):
    """\
    Yield word for word of a string, with comments removed. Words are annotated
    with position in source string.
    """
    for n, line in enumerate(data.splitlines()):
        for word in m_comment.sub('', line).split():
            yield Word(word, name, n+1, line)
        if include_newline:
            yield Word('\n', name, n+1, line)

# Word object iterator.  Words are identified from a file.  Backslash line comments
# are removed before words are recognized.  Each word is annotated with the filename
# and its line number (relative to 1) and the original line of text from which the
# word was identifed.
# Function arguments:
#   filename         Path to the file being recognized.  Required.
#   fileobj          A fileobj used to read text from a file.
#                    If None, the filename is opened and UTF-8 encoding is applied
#                    to the text file.  Defaults to None.
#   include_newline  Specify True to cause a Word object to be generated for the
#                    line termination sequence.
def words_in_file(filename, fileobj=None, include_newline=False):
    """\
    Yield word for word of a file, with comments removed. Words are annotated
    with position in source file.
    """
    if fileobj is None:
        fileobj = codecs.open(filename, 'r', 'utf-8')
    for n, line in enumerate(fileobj):
        for word in m_comment.sub('', line).split():
            yield Word(word, filename, n+1, line)
        if include_newline:
            yield Word('\n', filename, n+1, line)


#
#  +-----------------------------------+
#  |                                   |
#  |   FORTH Builtin Word Decorators   |
#  |                                   |
#  +-----------------------------------+
#

# Decorators
# ----------
#
# Per the Python glossary a "decorator" is:
#   A function returning another function, usually applied as a function
#   transformation using the @wrapper syntax.
#
# Further information is provided in the language reference section 7.6, "Function
# definitions":
#   A function definition may be wrapped by one or more decorator expressions.
#   Decorator expressions are evaluated when the function is defined, in the scope
#   that contains the function definition.  The result must be callable, which is
#   invoked with the function object as the only argument.  The returned value
#   is bound to the function name instead of the function object.  Multiple
#   decorators are applied in nested fashion.  For example, the following code:
#
#   @f1(arg)
#   @f2
#   def func(): pass
#
#   is equivalent to:
#
#   def func(): pass
#   func=f1(arg)(f2(func))
#
# The wrapper syntax requires that the "wrapper" function be defined somewhere.
# For Python builtin decorators, the wrapper function is defined by Python itself.
# The staticmethod decorator is an example.  In the case of this module, the two
# decorator wrapper functions are defined here as functions within the module
# namespace.
#
# This section in the Python Language reference has the following Programmer's note:
#    Functions are first-class objects.  A "def" form executed inside a function
#    defines a local function that can be returned or passed around.  Free variables
#    used in the nested function can access the local variables of the function
#    containing the def.

# The immediate dedorator informs the Forth class that the following function
# is an immediate word definition and should be executed (rather than compiled) when
# encountered during a word definition.
# If used the immediate decorator must be used before the word decorator.
# 
# See Forth.interpret_word() method for how this decorator influences the interpreter.
def immediate(function):
    """\
    Function decorator used to tag Forth methods that will be executed
    immediately even when in compile mode.
    """
    function.forth_immediate = True
    return function

# The word decorator identifies a function as a builtin Forth word definition.
# It "tags" the function with the rpn_name attribute used by the Forth class to
# identify its builtin words.  See the Forth.__init__() method for how this tag
# is used to idenfify builtin word definitions.
#
# The programmer's note quoted above applies to the nested definition of the 
# decorate_word() function the wrapper returns.
#
# The word decorator wrapper function takes one argument:
#   name   Specifies the Forth word's identifying name as a string.  The name is
#          added to the builtin namespace.
def word(name):
    """\
    Function decorator used to tag methods that will be visible in the Forth
    builtin namespace.
    """
    def decorate_word(function):
        function.rpn_name = name.lower()
        return function
    return decorate_word


#
#  +--------------------------------+
#  |                                |
#  |   Output Document Management   |
#  |                                |
#  +--------------------------------+
#

# Creates and manages a tree of text destined for output.
#
# The tree is:
#   chapter " DEFAULT "          created by first call to chapter() method
#      section " TOPLEVEL "      created by chapter() method
#         optional text string   added by write() method
#         optional text string   added by write() method
#      optional section          created by section() method
#         optional text string   added by write() method
#         optional text string   added by write() method
#      section additional        created by section() method
#   optional chapter             created by chapter() method
#      section " TOPLEVEL "      created by chapter() method
#      optional section          created by section() method
#
# In the context of the document tree, a section has nothing to do with object
# format sections.  A section is just a named grouping of text strings.
#
# This class assumes use of the MSP430 package tool chain assembler when creating
# chapter separators.
#
# Aside from the " DEFAULT " chapter, chapters are created when a file is included.
# A special chapter "__VARIABLES__" is created when all variable words are compiled.
# Each Frame object creates a new section within the current chapter.  Chapter and
# section creation is not exposed to the Forth program being compiled.

class DocumentTree(object):
    """\
    Maintain a list of chapters where each contains a list of sections.
    Track current section to write to. Data is buffered and sorted
    alphabetically when output.
    """

    def __init__(self):
        # Document state: FIFO stack of the tuple:
        #                 (chapter name, chapter dictionary, and section list)
        self._state = []
        # output is buffered in memory first. this allows to group commands and
        # to output in alphabetical order
        
        self.chapters = {}               # Chapter dictonary
        self.chapter_name = None         # Current chapter name
        self.current_chapter = None      # Current chapter dictionary
        self.current_section = None      # Current section list.
        self.chapter()    # create default chapter

    # Set the current chapter being built.  The current section if always the
    # " TOPLEVEL " section when this method is called.
    # Method Argument:
    #   name    Specifiy the chapter name being started or continued.  Defaults
    #           to " DEFAULT ".
    def chapter(self, name=' DEFAULT '):
        """Select chapter to put text sections in"""
        self.chapter_name = name
        
        # Create a new chapter or continue the specified chapter.
        # A "chapter" is a named dictionary of sections.
        self.current_chapter = self.chapters.setdefault(name, {})
        # " TOPLEVEL " becomes the current section of the current chapter
        self.section(' TOPLEVEL ')
        # Note: Use of the push_state() and pop_state() causes an interrupted section
        # to be continued, bypassing the the chapter() and section() methods.

    # Set the current section of the current chapter being built.
    # Method Argument:
    #   name    Specify the name of the section within the current chapter being
    #           started or continued.  Required.
    def section(self, name):
        """Select name of text section to append output"""
        # Create or continue a section of the current chapter
        # A "section" is a named list.  The list contains zero or more strings.
        self.current_section = self.current_chapter.setdefault(name, [])

    # Adds text to the current section under construction.
    def write(self, text):
        self.current_section.append(text)

    # Push the current state of the document manager to a FIFO stack
    def push_state(self):
        self._state.append((self.chapter_name, self.current_chapter, \
            self.current_section))

    # Restore the document manager state from the FIFO stack
    def pop_state(self):
        self.chapter_name, self.current_chapter, self.current_section \
            = self._state.pop()

    # Output the constructed document.  The sequence is chapters sorted by name
    # and within each chapter, sections sorted by name.  The output is text typically
    # an assembly source file targeted to the cross-compiler's tool chain.
    # Separator comments are generated between each non " DEFAULT " chapter.
    # Method argument:
    #   output  An object that supports the write() method.  Typically a file object
    #           or codec writer generating the output.  Required.
    def render(self, output):
        """Write sorted list of text sections"""
        #~ # XXX document tree as info
        #~ for chapter_name, sections in sorted(self.chapters.items()):
            #~ print '"%s"' % chapter_name
            #~ for section_name, text in sorted(sections.items()):
                #~ print '    "%s"' % section_name
        for chapter_name, sections in sorted(self.chapters.items()):
            heder_not_yet_done = True
            for name, text in sorted(sections.items()):
                if text and heder_not_yet_done:
                    if chapter_name != ' DEFAULT ':
                        output.write(u'; %s\n' % ('='*75))
                        output.write(u'; == %s\n' % chapter_name)
                        output.write(u'; %s\n' % ('='*75))
                    heder_not_yet_done = False
                output.write(u''.join(text))


#
#  +--------------------------------+
#  |                                |
#  |   FORTH Language Interpreter   |
#  |                                |
#  +--------------------------------+
#

# This FORTH language interpreter utilizes three "vocabularies" of defined words.
#   builtins   - Words defined as methods of the Forth object and executed as such.
#                Not defined in any Forth input.
#   namespace  - Forth words defined in terms of other words.  Used on both the
#                target system and the Forth host interpreter.  Defined as colon
#                word definitions.  Words defined in either __init__.forth file
#                or forth_words.py are compiled into this vocabulary.
#   target     - Forth words defined on the target system but not the interpreter.
#                Defined as CODE word definitions.
#
# Host word search order:
#    1. builtins           @word decorated methods
#    2. namespace          : word definitions
# Target word search order: 
#    1. target             CODE word definitions
#    2. namespace          : word definitions (same as on host)
#
# Builtin words required on the target system must have separate implementations
# in the target vocabulary.
#
# The primary purpose of the Forth object is the creation of an input file to a
# tool chain that can be utilized to build a Forth application for the target system.
# This object assumes use of the MSP430 toolchain provided by the MSP430 package.
#
# Interpreted numbers conform to Python integer or float literal conventions.  See the
# _interpret_word() method.
#
# The Forth data stack is the Forth object itself (a subclass of the Python list)
# The Forth return stack is the Python interpreter stack.  Executed words are called. 
# This is why namespace Frame objects contain sequences of executables (interspersed
# with a few other elements recognized by the "internal" words).
#
# Cross compiled words use the direct threading model.  See discussion at the end
# of the class concerning the "Compilation Limitations" resulting from the direct
# threading model as used by the MSP430 processor.

class Forth(list):
    """\
    Forth like language interpreter.
    """
    def __init__(self, namespace=None):
        list.__init__(self)
        self.clear()       # Initialize the interpreter data stack

        # Interpreter execution state
        # current list of input Word objects being interpreted
        self._iterator = None        # Set by interpret() method from its argument
        # Current Frame object being executed
        self._frame_iterator = None

        # Define the threaded word name space (used on both host and target)
        self.namespace = namespace if namespace is not None else {}

        # Define the builtin host specific name space
        self.builtins = {}
        # extend built-ins name space with all methods that were marked with
        # the @word decorator
        for name in dir(self):
            function = getattr(self, name)
            if hasattr(function, 'rpn_name'):
                self.builtins[function.rpn_name] = function

        # Define the target specific name space
        self.target_namespace = {}

        # Defined Variables
        self.variables = {}

        # Interpreter compilation state
        self.compiling = False        # Current Forth interpreter mode       
        self.frame = None             # Current Frame being compiled
        self.use_ram = False          # Current target memory type - see RAM and ROM
        self.label_id = 0             # Sequence number for generated assembly lables
        self.compiled_words = set()   # Track compiled words
        self.not_yet_compiled_words = set()  # Track uncompiled but referenced words

        # Include file management
        # Include search path 
        self.include_path = []        # built by function main() from command line
        # Included files (file include recursion not supported)
        self.included_files = []      # Modified by _include() and init() methods
        
        self.logger = logging.getLogger('forth')  # Python logger.
        
        # Output document tree
        self.doctree = DocumentTree()

    def __str__(self):
        """return a string describing the topmost elements from the stack"""
        if self:
            N = min(4, len(self))
            tops = ["%s:%s" % ("xyzt"[i], self.printer(self[-i-1])) for i in range(N)]
            if len(self) > 4:
                tops.append(' (%d more)' % (len(self)-4,))
            return ' '.join(tops)
        return "stack empty"

    def _compile_frame(self, frame):
        """\
        Compilation of forth functions. Words referenced by this function are
        remembered and can be output later, either manually with `CROSS-COMPILE`_
        or automatically with `CROSS-COMPILE-MISSING`_.
        """
        self.doctree.chapter(frame.chapter)
        self.doctree.section(frame.name)
        self.doctree.write(u'.text\n.even\n')
        self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'; compilation of word %s\n' % frame.name)
        self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'%s:\n' % self.create_asm_label(frame.name))
        # compilation of the thread
        self.doctree.write('\tbr #%s\n' % self.create_asm_label('DOCOL'))
        #~ self.doctree.write('\tjmp %s\n' % self.create_asm_label('DOCOL'))
        self._compile_thread(frame)
        self.doctree.write('\t.word %s\n\n' % self.create_asm_label('EXIT'))

    def _compile_interrupt_frame(self, frame):
        """Compilation of interrupt function"""
        self.doctree.section(frame.name)
        self.doctree.write(u'.text\n.even\n')
        self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'; compilation of interrupt %s\n' % frame.name)
        self.doctree.write(u';%s\n' % ('-'*76))

        # interrupt entry code
        self.doctree.write(u'__vector_%s:\n' % (frame.vector))
        self.doctree.write(u'\tsub #4, RTOS     ; prepare to push 2 values on return stack\n')
        self.doctree.write(u'\tmov IP, 2(RTOS)  ; save IP on return stack\n')
        self.doctree.write(u'\tmov SP, 0(RTOS)  ; save SP pointer on return stack it points to SR on stack\n')
        self.doctree.write(u'\tmov #%s, IP      ; Move address of thread of interrupt handler in IP\n'\
            % self.create_asm_label(frame.name))
        self.doctree.write('\tbr  #%s\n' % self.create_asm_label('DO-INTERRUPT'))
        # the thread for the interrupt handler
        self.doctree.write(u'%s:\n' % self.create_asm_label(frame.name))
        self._compile_thread(frame)
        self.doctree.write('\t.word %s\n\n' % self.create_asm_label('EXIT-INTERRUPT'))
        self._compile_remember('DO-INTERRUPT')
        self._compile_remember('EXIT-INTERRUPT')

    def _compile_native_frame(self, frame):
        """Compilation of native code function"""
        self.doctree.chapter(frame.chapter)
        self.doctree.section(frame.name)
        self.doctree.write(u'.text\n.even\n')
        self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'; compilation of native word %s\n' % frame.name)
        self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'%s:\n' % self.create_asm_label(frame.name))
        # native code blocks are executed. They are expected to print out
        # assembler code
        frame(self)
        self.doctree.write('\n') # get some space between this and next word

    def _compile_remember(self, word):
        """\
        Remember that a word used. This ensures that it is included in the list
        of cross compiled words.
        """
        # track what is not yet done
        word = word.lower()
        if word not in self.compiled_words:
            self.not_yet_compiled_words.add(word)

    def _compile_thread(self, frame):
        next = iter(frame).next
        try:
            while True:
                entry = next()
                if callable(entry):
                    if entry == self.instruction_output_text:
                        label = self.create_label()
                        self.doctree.write('\t.word %s, %s\n' % (
                                self.create_asm_label('__write_text'),
                                self.create_asm_label(label)))
                        self._compile_remember('__write_text')
                        # output the text separately
                        frame = NativeFrame(label)
                        frame.chapter = self.doctree.chapter_name
                        self.target_namespace[label] = frame
                        self._compile_remember(label)
                        text = next()
                        frame.append(self.instruction_output_text)
                        frame.append('\t.asciiz "%s"\n' \
                            % (codecs.escape_encode(text)[0],))
                    elif entry == self.instruction_literal:
                        value = next()
                        if isinstance(value, Frame):
                            self.doctree.write('\t.word %s, %s\n' % (
                                    self.create_asm_label('LIT'),
                                    self.create_asm_label(value.name),))
                        else:
                            self.doctree.write('\t.word %s, %-6s ; 0x%04x\n' % (
                                    self.create_asm_label('LIT'),
                                    value,
                                    value & 0xffff))
                        self._compile_remember('LIT')
                    elif entry == self.instruction_seek:
                        # branch needs special case as offset needs to be recalculated
                        offset = next()
                        self.doctree.write('\t.word %s, %s\n' \
                            % (self.create_asm_label('BRANCH'), offset*2))
                        self._compile_remember('BRANCH')
                    elif entry == self.instruction_branch_if_false:
                        # branch needs special case as offset needs to be recalculated
                        offset = next()
                        self.doctree.write('\t.word %s, %s\n' \
                            % (self.create_asm_label('BRANCH0'), offset*2))
                        self._compile_remember('BRANCH0')
                    elif hasattr(entry, 'rpn_name'):
                        # for built-ins just take the name of the function
                        self.doctree.write('\t.word %s\n' \
                            % self.create_asm_label(entry.rpn_name.upper()))
                        self._compile_remember(entry.rpn_name)
                    elif isinstance(entry, Frame):
                        self.doctree.write('\t.word %s\n' \
                            % self.create_asm_label(entry.name))
                        self._compile_remember(entry.name)
                    else:
                        raise ValueError('Cross compilation undefined for %r' % entry)
                else:
                    self.doctree.write('\t.word %r\n' % (entry,))
                    #~ raise ValueError('Cross compilation undefined for %r' % entry)
        except StopIteration:
            pass

    def _include(self, name):
        """Include given filename. The Forth code is directly executed."""
        # put all data from include in one chapter. remember previous chapter
        # at restore it at the end
        self.doctree.push_state()
        self.doctree.chapter(name)
        if name not in self.included_files:
            for prefix in self.include_path:
                path = os.path.join(prefix, name)
                if os.path.exists(path):
                    self.logger.info('processing include %s' % (name,))
                    self.interpret(words_in_file(path,include_newline=True))
                    self.logger.info('done include %s' % (name,))
                    self.included_files.append(name)
                    break
            else:
                # as fallback, check internal library too
                try:
                    data = pkgutil.get_data('msp430.asm', 'forth/%s' % (name,))
                except IOError:
                    raise ValueError('file not found: %s' % (name,))
                else:
                    self.logger.info('processing include %s' % (name,))
                    self.interpret(words_in_string(data, name='forth/%s' % (name,), \
                        include_newline=True))
                    self.logger.info('done include %s' % (name,))
                    self.included_files.append(name)
        self.doctree.pop_state() # restore previous chapter and section

    def create_asm_label(self, name):
        """\
        There are a number of symbols that are not allowed in assembler
        labels, translate to printable strings.
        """
        for t_in, t_out in (
                ('.', '_dot_'),
                ('-', '_dash_'),
                ('+', '_plus_'),
                ('*', '_star_'),
                ('?', '_qmark_'),
                ('/', '_slash_'),
                ('\\', '_backslash_'),
                ('|', '_or_'),
                ('&', '_and_'),
                ('@', '_fetch_'),
                ('[', '_open_bracket_'),
                (']', '_close_bracket_'),
                ('!', '_store_'),
                ('<', '_less_'),
                ('>', '_bigger_'),
                ('=', '_eq_'),
                ('NOT', '_NOT_'),
                ("'", '_tick_'),
        ):
            name = name.replace(t_in, t_out)
        return '_' + name

    def create_label(self):
        """Create a new assembler label"""
        self.label_id += 1
        return '__lbl%s' % (self.label_id,)

    def init(self,usefile=False,debug=False):
        # load core language definitions from a forth file
        if usefile:
            # load core language definitions from a forth file
            self._include('__init__.forth')
        else:
            # load core language definitions forth_words module
            name="__init__.forth"
            #data=forth_words.definitions
            data=definitions
            self.logger.info('processing include %s' % (name,))
            self.interpret(words_in_string(data, name='forth/%s' % (name,), \
                include_newline=True))
            self.logger.info('done include %s' % (name,))
            self.included_files.append(name)
        if debug:
            self.word_LIST(None)

    def instruction_cross_compile(self, stack, word=None):
        """\
        Cross compile word. This function can be called directly (w/ word
        parameter) or be part of a Frame.
        """
        if word is None:
            word = self._frame_iterator.next()
        # when interpreting, execute the actual functionality
        # track what is done
        self.compiled_words.add(word)
        if word in self.not_yet_compiled_words:
            self.not_yet_compiled_words.remove(word)
        # get the frame and compile it - prefer target_namespace
        try:
            item = self.look_up_target(word)
        except KeyError:
            raise ValueError('word %r is not available on the target' % (word,))
        # translate, depending on type
        if isinstance(item, NativeFrame):
            self._compile_native_frame(item)
        elif isinstance(item, InterruptFrame):
            self._compile_interrupt_frame(item)
        elif isinstance(item, Frame):
            self._compile_frame(item)
        else:
            raise ValueError('don\'t know how to compile word %r' % (word,))

    def interpret(self, iterator):
        """\
        Interpret a sequence of words given a 'next' function that get the
        next word from the sequence.
        """
        # keep old reference in case of nested calls
        old_iterator = self._iterator
        # store function to make it available to called functions
        self._iterator = iterator
        word = None # in case next_word raises an exception
        try:
            while True:
                word = iterator.next()
                self.interpret_word(word)
        except StopIteration:
            pass
        except ForthError:
            raise
        except Exception as e:
            filename = getattr(word, 'filename', '<unknown>')
            lineno = getattr(word, 'lineno', None)
            column = getattr(word, 'column', None)
            offset = getattr(word, 'offset', None)
            text = getattr(word, 'text', None)
            logging.getLogger('rpn').exception(\
                '%s:%s: Error in word "%s": %s' % (filename, lineno, word, e))
            raise ForthError('Error in word "%s": %s' \
                % (word, e), filename, lineno, column, offset, text)
            # XXX consider showing the full traceback of the original exception
        finally:
            # restore state
            self._iterator = old_iterator

    def instruction_output_text(self, stack):
        words = stack._frame_iterator.next()
        self.doctree.write(words)

    def interpret_sequence(self, sequence, filename=None):
        """interpret a sequence of words"""
        self.interpret(annotated_words(sequence, filename))

    def interpret_word(self, word):
        """Depending on mode a word is executed or compiled"""
        #~ print "XXX", word
        # newlines are in the steam to support \ comments, they are otherwise ignored
        if word == '\n':
            return
        try:
            element = self.look_up(word)
        except KeyError:
            pass
        else:
            if self.compiling and not hasattr(element, 'forth_immediate'):
                if callable(element):
                    self.frame.append(element)
                else:
                    self.frame.append(self.instruction_literal)
                    self.frame.append(element)
                return
            else:
                if callable(element):
                    element(self)
                else:
                    self.push(element)
                return
        # if it's not a symbol it might be a number
        try:
            # The strings content defines the base.  If the string starts with
            # '0b' the base is 2.  If the string starts with  '0x' the base is 16.
            # Otherwise, the base is 10.  If the string starts with '0o' the base is
            # 8.
            number = int(word, 0)
        except ValueError:
            try:
                number = float(word)
            except ValueError:
                filename = getattr(word, 'filename', '<unknown>')
                lineno = getattr(word, 'lineno', None)
                column = getattr(word, 'column', None)
                offset = getattr(word, 'offset', None)
                text = getattr(word, 'text', None)
                raise ForthError("neither known symbol nor number: %r" \
                    % (word,), filename, lineno, column, offset, text)
        if self.compiling:
            self.frame.append(self.instruction_literal)
            self.frame.append(number)
        else:
            self.push(number)

    def look_up(self, word):
        """Find the word in one of the name spaces for the host and return the value"""
        # target words are included w/ least priority. they must be available
        # so that compiling words on the host works
        lowercased_word = word.lower() # case insensitive
        for namespace in (self.namespace, self.builtins, self.target_namespace):
            try:
                element = namespace[lowercased_word]
            except KeyError:
                pass
            else:
                return element
        raise KeyError('%r not in any namespace (host)' % (word,))

    def look_up_target(self, word):
        """Find the word in one of the namespaces for the target and return the value"""
        # builtin namespace is not searched as it only includes words
        # implemented in python. target name space has priority over normal
        # space.
        lowercased_word = word.lower() # case insensitive
        for namespace in (self.target_namespace, self.namespace):
            try:
                element = namespace[lowercased_word]
            except KeyError:
                pass
            else:
                return element
        raise KeyError('%r not in any namespace (target)' % (word,))

    def next_word(self):
        return self._iterator.next()

    def pop(self):
        """Get an element from the stack"""
        try:
            return list.pop(self)
        except IndexError:
            raise IndexError("pop called on empty stack")

    def pop2(self):
        """Get two elements from the stack"""
        return self.pop(), self.pop()

    # Not used
    def prettyprint(self, stack):
        pprint.pprint(self.pop())

    # Used by the __str__() method
    def printer(self, obj):
        """\
        convert object to string, for floating point numbers, 
        use engineering format
        """
        t = type(obj)
        if type(t) == float:
            e = int(math.log10(abs(obj)))
            e = int(e/3)*3
            if e:
                return "%ge%s" % ((obj/10**e), e)
            else:
                return "%g" % (obj)
        else:
            return repr(obj)

    def push(self, obj):
        """Push an element on the stack"""
        self.append(obj)

    #
    # Builtin name space word definitions
    #

    @word("+")
    def add(self, stack):
        """Add two numbers on the stack."""
        x, y = self.pop2()
        self.push(y + x)

    @word("/")
    def div(self, stack):
        """Divide two numbers on the stack."""
        x, y = self.pop2()
        self.push(y / x)

    @word("==")
    def equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y == x))

    @word(">")
    def larger(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y > x))

    @word(">=")
    def larger_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y >= x))

    @word("*")
    def mul(self, stack):
        """Multiply two numbers on the stack."""
        x, y = self.pop2()
        self.push(y * x)

    @word("!=")
    def not_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y != x))

    @word("<")
    def smaller(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y < x))

    @word("<=")
    def smaller_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = self.pop2()
        self.push(bool(y <= x))

    @word("-")
    def sub(self, stack):
        """Subtract two numbers on the stack."""
        x, y = self.pop2()
        self.push(y - x)

    @word('@')
    def word_at(self, stack):
        reference = stack.pop()
        if isinstance(reference, Variable):
            stack.push(reference)
        else:
            raise ValueError(\
                'limited support for @: no compatible object on stack: %r' \
                    % (reference,))

    @immediate
    @word(':')
    def word_colon(self, stack):
        """Begin defining a function. Example: ``: ADD-ONE 1 + ;``"""
        name = self.next_word()
        self.frame = Frame(name)
        self.frame.chapter = self.doctree.chapter_name
        self.compiling = True

    @word(',')
    def word_comma(self, stack):
        """Append value from stack to current definition."""
        if self.frame is None: raise ValueError('not in colon definition')
        value = stack.pop()
        if isinstance(value, Variable):
            # XXX special case for calculations with HERE
            value = value.offset
        self.frame.append(value)

    @immediate
    @word('(')
    def word_comment_start(self, stack):
        """\
        Start a comment and read to its end (``)``).

        There is a special comment ``( > text... )`` which is recognized by the
        documentation tool. All these type of comments are collected and
        assigned to the next declaration.
        """
        while True:
            word = self.next_word()
            if ')' in word:
                break
        if not word.endswith(')'):
            raise ValueError('limitation, comment end ")" followed by data: %r' \
                % (word,))

    @immediate
    @word(']')
    def word_compile(self, stack):
        """Change to compilation mode."""
        self.compiling = True

    @immediate
    @word('."')
    def word_copy_words(self, stack):
        """Output a string."""
        words = []
        while True:
            word = self.next_word()
            if word.endswith('"'):
                # emulate character wise reading
                if word != '"':
                    words.append(word[:-1])
                break
            words.append(word)
        text = codecs.escape_decode(u' '.join(words))[0]
        if self.compiling:
            self.frame.append(self.instruction_output_text)
            self.frame.append(text)
        else:
            self.doctree.write(text)

    @word('/MOD')
    def word_divmod(self, stack):
        """Put quotient and reminder on stack."""
        a = stack.pop()
        b = stack.pop()
        d, m = divmod(a, b)
        stack.push(d)
        stack.push(m)

    @word('.')
    def word_dot(self, stack):
        """Output element on stack."""
        self.doctree.write(unicode(stack.pop()))

    @word('=')
    def word_equals1(self, stack):
        """Compare two numbers for equality"""
        a = stack.pop()
        b = stack.pop()
        stack.push(a == b)

    @immediate
    @word('[')
    def word_interpret(self, stack):
        """Change to interpretation mode."""
        self.compiling = False

    @word('-ROT')
    def word_is_nrot(self, stack):
        """Rotate 3 items on the stack. 1st gets 3rd."""
        a = stack.pop()
        b = stack.pop()
        c = stack.pop()
        stack.push(a)
        stack.push(c)
        stack.push(b)

    @immediate
    @word('\\')
    def word_line_comment_start(self, stack):
        """Start a line comment and read to its end."""
        while True:
            word = self.next_word()
            if '\n' in word:
                break
        if not word.endswith('\n'):
            raise ValueError(\
                'limitation, line comment end "\\n" followed by data: %r' % (word,))

    @word('?DUP')
    def word_Qdup(self, stack):
        """DUP top of stack but only if not zero."""
        if stack[-1]:
            stack.push(stack[-1])

    @immediate
    @word(';')
    def word_semicolon(self, stack):
        """End definition of function. See `:`_"""
        if self.frame is None: raise ValueError('not in colon definition')
        #~ print "defined", self.frame.name, self.frame     # XXX DEBUG
        self.namespace[self.frame.name.lower()] = self.frame
        self.frame = None
        self.compiling = False

    @word('!')
    def word_store(self, stack):
        reference = stack.pop()
        value = stack.pop()
        if isinstance(reference, Variable):
            if reference.frame != self.frame:
                raise ValueError('!: Frame mismatch for variable %r != %r' \
                    % (reference.frame, self.frame))
            if isinstance(value, Variable):
                reference.set(value.offset)
            else:
                reference.set(value)
        else:
            raise ValueError(\
                'limited support for !: no compatible object on stack %r' \
                    % (reference,))

    @immediate
    @word('"')
    def word_string_literal(self, stack):
        """Put a string on the stack."""
        words = []
        while True:
            word = self.next_word()
            if word.endswith('"'):
                # emulate character wise reading
                if word != '"':
                    words.append(word[:-1])
                break
            words.append(word)
        text = codecs.escape_decode(u' '.join(words))[0]
        if self.compiling:
            self.frame.append(self.instruction_literal)
            self.frame.append(text)
        else:
            self.push(text)

    @immediate
    @word("'")
    def word_tick(self, stack):
        """Push reference to next word on stack."""
        if self.frame is None: raise ValueError('not in colon definition')
        name = stack.next_word()
        self.frame.append(self.instruction_literal)
        self.frame.append(self.look_up(name))

    @word('0>')
    def word_is_positive(self, stack):
        """Check if number is positive"""
        a = stack.pop()
        stack.push(a > 0)

    @word('0=')
    def word_is_zero(self, stack):
        """Check if number is not zero"""
        a = stack.pop()
        stack.push(a == 0)

    @word("1-")
    def minus_1(self, stack):
        self[-1] = self[-1] - 1

    @word("1+")
    def plus_1(self, stack):
        self[-1] = self[-1] + 1

    @word("2*")
    def arithmetic_shift_left(self, stack):
        self[-1] = self[-1]*2

    @word("2/")
    def arithmetic_shift_right(self, stack):
        self[-1] = self[-1]/2

    @word("2-")
    def minus_2(self, stack):
        self[-1] = self[-1] - 2

    @word("2+")
    def plus_2(self, stack):
        self[-1] = self[-1] + 2

    @word("4-")
    def minus_4(self, stack):
        self[-1] = self[-1] - 4

    @word("4+")
    def plus_4(self, stack):
        self[-1] = self[-1] + 4

    @word('ALLOT')
    def word_allot(self, stack):
        """Allocate memory in RAM or ROM."""
        count = stack.pop()
        if count > 0:
            if count & 1: raise ValueError('odd sizes currently not supported')
            self.frame.extend([0]*(count/2))
        else:
            raise ValueError('negative ALLOT not supported')

    @word("AND")
    def bitand(self, stack):
        x, y = self.pop2()
        self.push(y & x)

    @word('BRANCH')
    def instruction_seek(self, stack):
        """Get offset from sequence and jump to this position."""
        difference = stack._frame_iterator.next()
        stack._frame_iterator.seek(difference - 1)

    @word('BRANCH0')
    def instruction_branch_if_false(self, stack):
        """\
        Get offset from sequence and a boolean from stack. Jump if boolean was
        false.
        """
        difference = stack._frame_iterator.next()
        if not stack.pop():
            stack._frame_iterator.seek(difference - 1)

    @immediate
    @word('CHAR')
    def word_char(self, stack):
        """Push ASCII code of next character."""
        name = stack.next_word()
        value = ord(name[0])
        stack.push(value)

    @immediate
    @word('[CHAR]')
    def word_compile_char(self, stack):
        """Compile ASCII code of next character."""
        name = stack.next_word()
        value = ord(name[0])
        if self.compiling:
            if self.frame is None: raise ValueError('not in colon definition')
            self.frame.append(self.instruction_literal)
            self.frame.append(value)
        else:
            raise ValueError('interpretation semantics undefined')

    @word("CLEAR")
    def clear(self, stack=None):
        """Clear stack."""
        del self[:]

    @immediate
    @word('CODE')
    def word_code(self, stack):
        """\
        Begin defining a native code function. CODE words are executed on the
        host to get cross compiled. Therefore they have to output assembler
        code for the target. Example::

            ( > Increment value on stack by one. )
            CODE 1+ ( n -- n )
                ." \\t inc 0(SP) \\n "
                ASM-NEXT
            END-CODE

        There is a number of supporting functions for outputting assembler.
        E.g. `ASM-NEXT`_, `ASM-DROP`_, `ASM-TOS->R15`_, `ASM-R15->TOS`_,
        `ASM-TOS->W`_, `ASM-W->TOS`_

        Note that the NEXT instruction is not automatically inserted and must be
        added manually (see `ASM-NEXT`_ in example above).
        """
        name = self.next_word()
        self.frame = NativeFrame(name)
        self.frame.chapter = self.doctree.chapter_name
        self.compiling = True

    @immediate
    @word('[COMPILE]')
    def word_BcompileB(self, stack):
        """\
        Get next word, look it up and add it to the current frame (not
        executing immediate functions).
        """
        if self.frame is None: raise ValueError('not in colon definition')
        item = self.look_up(stack.next_word())
        self.frame.append(item)

    @word('CONSTANT')
    def word_constant(self, stack):
        """\
        Declare a constant. Assign next word to value from stack.
        Example: ``0 CONSTANT NULL``
        """
        value = stack.pop()
        name = stack.next_word()
        stack.namespace[name.lower()] = value

    @word('CREATE')
    def word_create(self, stack):
        """Create a frame, typically used for variables."""
        name = stack.next_word()
        # allocate separate memory
        # (cross compiled to RAM)
        self.variables[name] = Frame('cre'+name)
        self.variables[name].use_ram = self.use_ram
        self.frame = self.variables[name]
        # create a function that pushes the variables address
        frame = Frame(name)
        frame.chapter = self.doctree.chapter_name
        frame.append(self.instruction_literal)
        frame.append(self.variables[name])
        self.namespace[name.lower()] = frame
        # XXX could also do a native impl with "push #adr;NEXT"

    @immediate
    @word('CROSS-COMPILE')
    def word_cross_compile(self, stack):
        """Output cross compiled version of function. Example:: ``CROSS-COMPILE DROP``"""
        word = self.next_word()
        if self.compiling:
            # when compiling add call to self and the word to the Frame
            self.frame.append(self.instruction_cross_compile)
            self.frame.append(word)
        else:
            # in interpretation mode, compile it now
            self.instruction_cross_compile(stack, word)

    @word('CROSS-COMPILE-MISSING')
    def word_cross_compile_missing(self, stack):
        """\
        Compile all the words that are used by other compiled words but are not
        yet translated. While compiling words, new words can be found which are
        then also compiled.
        """
        while self.not_yet_compiled_words:
            self.instruction_cross_compile(self, \
                word=self.not_yet_compiled_words.pop())

    @word('CROSS-COMPILE-VARIABLES')
    def word_cross_compile_variables(self, stack):
        """\
        Output section with variables (values in RAM).
        """
        self.doctree.push_state()
        self.doctree.chapter('__VARIABLES__')
        #~ self.doctree.write(u';%s\n' % ('-'*76))
        #~ self.doctree.write(u'; Variables\n')
        #~ self.doctree.write(u';%s\n' % ('-'*76))
        self.doctree.write(u'.bss\n')
        # XXX check .use_ram attribute
        for name, variable in sorted(self.variables.items()):
            variable.name
            self.doctree.write(u'%s:  .skip %d \n' % (
                    self.create_asm_label(variable.name),
                    2*len(variable)))
            self.doctree.write('\n')
        self.doctree.pop_state()

    @immediate
    @word('DEPENDS-ON')
    def word_depends_on(self, stack):
        """\
        Mark word as used so that it is included in cross compilation. Useful
        when using other words within CODE_ definitions.
        """
        if self.compiling:
            word = self.next_word()
            self.frame.append(self.word_depends_on)
            self.frame.append(word)
        else:
            word = stack._frame_iterator.next()
            self._compile_remember(word)

    @word("DROP")
    def drop(self, stack):
        """Remove and forget about topmost element on the stack."""
        self.pop()

    @word("DUP")
    def dup(self, stack):
        """Duplicate the topmost element on the stack."""
        self.push(self[-1])

    @word('EMIT')
    def word_emit(self, stack):
        """Output number on stack as Unicode character."""
        self.doctree.write(unichr(stack.pop()))

    @immediate
    @word('END-CODE')
    def word_end_code(self, stack):
        """End definition of a native code function. See CODE_."""
        if self.frame is None: raise ValueError('not in colon definition')
        #~ print "defined code", self.frame.name, self.frame     # XXX DEBUG
        self.target_namespace[self.frame.name.lower()] = self.frame
        self.frame = None
        self.compiling = False

    @immediate
    @word('END-INTERRUPT')
    def word_end_interrupt(self, stack):
        """End definition of a native code function. See INTERRUPT_ for example."""
        if self.frame is None: raise ValueError('not in colon definition')
        #~ print "defined code", self.frame.name, self.frame     # XXX DEBUG
        self.target_namespace[self.frame.name.lower()] = self.frame
        self.frame = None
        self.compiling = False

    @word("FLOAT")
    def word_FLOAT(self, stack):
        """Convert TOS to a floating point number."""
        self.push(float(self.pop()))

    @word('HERE')
    def word_here(self, stack):
        """Put position [within frame] on stack"""
        v=Variable(self.frame, len(self.frame))
        stack.push(v)
        print("HERE: %s" % v)

    @word("IFTE")
    def word_IFTE(self, stack):
        """\
        If then else for 3 values on the stack: predicate, value_true,
        value_false.
        """
        x, y = self.pop2()
        z = self.pop()
        if z:
            self.push(y)
        else:
            self.push(x)

    @immediate
    @word('IMMEDIATE')
    def word_immediate(self, stack):
        """\
        Tag current function definition as immediate. This means that it is
        executed even during compilation.
        """
        if self.frame is None: raise ValueError('not in colon definition')
        self.frame.forth_immediate = True

    @word('INCLUDE')
    def word_INCLUDE(self, stack):
        """\
        Include and execute definitions from an other file. Example:
        ``INCLUDE helper.forth``
        """
        name = self.next_word()
        self._include(name)

    @word("INT")
    def word_INT(self, stack):
        """Convert TOS to an integer."""
        self.push(int(self.pop()))

    @immediate
    @word('INTERRUPT')
    def word_interrupt(self, stack):
        """\
        Begin defining an interrupt function. Example::

            PORT1_VECTOR INTERRUPT handler_name
                WAKEUP
                0 P1IFG C!
            END-INTERRUPT

        Words defined with ``INTERRUPT`` must not be called from user code.
        """
        name = self.next_word()
        vector = self.pop()
        self.frame = InterruptFrame(name, vector)
        self.compiling = True

    @word("INVERT")
    def bitnot(self, stack):
        self.push(~self.pop())

    @word("LIST")
    def word_LIST(self, stack):
        """testing only: print all knwon words to stdout"""
        for namespace in (self.namespace, self.builtins):
            pprint.pprint(namespace)

    @word('LIT')
    def instruction_literal(self, stack):
        """Low level instruction to get a literal and push it on the stack."""
        stack.push(stack._frame_iterator.next())

    @word("LSHIFT")
    def bit_shift_left(self, stack):
        x, y = self.pop2()
        self.push(y << x)

    @word("MAX")
    def maximum(self, stack):
        """Leave the larger of two values on the stack."""
        x, y = self.pop2()
        self.push(max(y, x))

    @word("MIN")
    def minimum(self, stack):
        """Leave the smaller of two values on the stack."""
        x, y = self.pop2()
        self.push(min(y, x))

    @word("NEG")
    def negate(self, stack):
        """Negate number on stack."""
        self.push(-self.pop())

    @word("NOT")
    def word_NOT(self, stack):
        self.push(not self.pop())

    @word("OR")
    def bitor(self, stack):
        x, y = self.pop2()
        self.push(y | x)

    @word("OVER")
    def over(self, stack):
        """Push a copy of the second element on the stack."""
        self.push(self[-2])

    @word("PICK")
    def pick(self, stack):
        """Push a copy of the N'th element on the stack."""
        self.push(self[-self.pop()])

    @word('RAM')
    def word_ram(self, stack):
        """Select RAM as target for following CREATE_ calls."""
        self.use_ram = True

    @immediate
    @word('RECURSE')
    def word_recurse(self, stack):
        """\
        Call currently defined word. This is used to write recursive functions.
        """
        if not self.compiling: raise ValueError('not allowed in immediate mode')
        if self.frame is None: raise ValueError('not in colon definition')
        # put conditional branch operation in sequence, remember position of offset on stack
        self.frame.append(self.instruction_branch_if_false)
        self.push(len(self.frame))
        self.frame.append(0)

    @word('ROM')
    def word_rom(self, stack):
        """Select ROM/Flash as target for following CREATE_ calls."""
        self.use_ram = False

    @word('ROT')
    def word_is_rot(self, stack):
        """Rotate 3 items on the stack. 3rd gets 1st."""
        a = stack.pop()
        b = stack.pop()
        c = stack.pop()
        stack.push(b)
        stack.push(a)
        stack.push(c)

    @word("RSHIFT")
    def bit_shift_right(self, stack):
        x, y = self.pop2()
        self.push(y >> x)

    @word('SHOW')
    def word_SHOW(self, stack):
        """Show internals of given word. Used to debug."""
        name = self.next_word()
        sys.stderr.write('SHOW %r\n' % name)
        try:
            value = self.look_up(name)
        except KeyError:
            sys.stderr.write('    value -> <undefined>\n')
        else:
            sys.stderr.write('    value -> %r\n' % (value,))
            if isinstance(value, Frame):
                sys.stderr.write('    contents -> \n')
                for item in value:
                    sys.stderr.write('        %r\n' % item)

    @word("SWAP")
    def swap(self, stack):
        """Exchange the two topmost elements on the stack."""
        self[-1], self[-2] = self[-2], self[-1]

    @immediate
    @word('TO')
    def word_to(self, stack):
        """Write to a VALUE_. Example: ``123 SOMEVALUE TO``"""
        name = stack.next_word()
        if self.compiling:
            self.frame.append(self.instruction_literal)
            self.frame.append(self.variables[name])
            self.frame.append(self.look_up('!'))
        else:
            value = stack.pop()
            self.variables[name][0] = value # XXX

    @word('VALUE')
    def word_value(self, stack):
        """\
        Allocate a variable. Creates space in RAM and a value getter
        function.

        Example::

            0 VALUE X
            X       \ -> puts 0 on stack
            5 X TO
            X       \ -> puts 5 on stack
        """
        value = stack.pop()
        name = stack.next_word()
        # allocate separate memory for the variable
        # (cross compiled to RAM)
        self.variables[name] = Frame('val'+name)
        self.variables[name].append(value)
        # create a function that pushes the variables address
        frame = Frame(name)
        frame.chapter = self.doctree.chapter_name
        frame.append(self.instruction_literal)
        frame.append(self.variables[name])
        frame.append(self.look_up('@'))
        self.namespace[name.lower()] = frame

    @word('VARIABLE')
    def word_variable(self, stack):
        """\
        Allocate a variable. Creates space in RAM and an address getter
        function.
        """
        name = stack.next_word()
        # allocate separate memory for the variable
        # (cross compiled to RAM)
        self.variables[name] = Frame('var'+name)
        self.variables[name].append(0)
        # create a function that pushes the variables address
        frame = Frame(name)
        frame.chapter = self.doctree.chapter_name
        frame.append(self.instruction_literal)
        frame.append(self.variables[name])
        self.namespace[name.lower()] = frame
        # XXX could also do a native impl with "push #adr;NEXT"

    @word('WORD')
    def word_word(self, stack):
        """Read next word from the source and put it on the stack."""
        stack.push(stack.next_word())

    @word("XOR")
    def bitxor(self, stack):
        x, y = self.pop2()
        self.push(y ^ x)

#
#  +-----------------------------+
#  |                             |
#  |   Compilation Limitations   |
#  |                             |
#  +-----------------------------+
#

# The direct threading module is the simplest thread design.  Each cell in the
# compiled word contains an address of the assembler code which executes it.  For
# compiled word definitions this requires a preamble of assembler code that enters
# the word.  This works nicely for conversion to a assembler program because each
# referenced word becomes an address identified by the word's assembler label.
#
# However, this approach to compiling words does not work for the indirect threading
# model or token based model.  No mechanism exists for building the indirect address
# or token table.
#
# Use of variable length tokens is complicated by the fact that no mechanism exists
# to allow prioritization of assigned tokens to higher usage words.  The use of Python
# sets does now allow those distinctions.  Word reference counting is required.
#
# The native code threading model and a variable-sized token threading model both
# cause complications in the current implementation for branches within a word.  The
# MSP430 apparently uses fixed sized cells within a thread.  This allows the index
# of the cell within the base Frame object to be used to calculate a branch offset.
# In a case where the size of each "cell" may vary, no mechanism exists to allow
# calculation of the offset.
#
# No mechanism exists to differentiate between native code sequences and native code
# words.  Such is not necessary for a direct threading model.  But where indirect
# threading or token based threading is used, native code words must be identified
# so they may participate in the indirect word table or the table allowing conversion
# of a token to its word address.
#
# The compilation design as implemented follows essentially a single pass approach.  
# Some of these more complex threading models require multiple passes before the
# final assembler code can be generated for output.
# 
# In summary, some separation is required between the definition phase and the output
# stage.  This is needed for the option of supporting multiple architectures and
# multiple threading models.  A mechansim that sits between the forth interpreter
# and the document tree containing the generated assembler source file is needed.

#
#  +----------------------------------------------+
#  |                                              |
#  |   FORTH Compiled Word Definition Framework   |
#  |                                              |
#  +----------------------------------------------+
#

class Frame(list):
    """Storage for function definitions"""

    def __init__(self, name):
        list.__init__(self)
        self.name = name
        self.use_ram = False

    def __call__(self, stack):
        """Execute code in frame"""
        iterable = SeekableIterator(self)
        old_iterator = stack._frame_iterator
        stack._frame_iterator = iterable
        try:
            while True:
                instruction = iterable.next()
                instruction(stack)
        except StopIteration:
            pass
        finally:
            stack._frame_iterator = old_iterator

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self.name,)

class InterruptFrame(Frame):
    """\
    Interrupt frames are like normal Frames in most aspects but need different
    entry/exit code.
    """
    def __init__(self, name, vector):
        Frame.__init__(self, name)
        self.vector = vector


class NativeFrame(Frame):
    """\
    Storage for native function definitions. It is a separate class so that
    the objects can be identified.
    """


class SeekableIterator(object):
    """\
    An iterator with the additional functionality to adjust the read pointer
    while it is running. This is needed to implement jumps in
    Frame/NativeFrame.
    """
    def __init__(self, some_list):
        self.some_list = some_list
        self.position = 0

    def next(self):
        if self.position < len(self.some_list):
            item = self.some_list[self.position]
            self.position += 1
            return item
        raise StopIteration()

    def seek(self, difference):
        new_position = self.position + difference
        # allow positioning to size, one behind the last element
        # this is used if a branch/seek instruction wants to jump to the end of
        # the sequence
        if not 0 <= new_position <= len(self.some_list):
            raise ValueError('position not within size of sequence')
        self.position = new_position


class Variable(object):
    """This emulates what on a target would be an address."""
    # typical variable usage: "HERE @". so the variable name would put the
    # address of the variable on the stack. The value of HERE is then also used
    # to write to (e.g. in the implementation of IF/ENDIF. As we don't not have
    # linear address space but frames for each dictionary entry that start
    # counting at zero, the value needs to remember the frame it belongs to.

    def __init__(self, frame, offset):
        self.frame = frame
        self.offset = offset

    def __add__(self, other):
        if isinstance(other, Variable):
            if self.frame is not other.frame: 
                raise ValueError('Variables point to different frames')
            return Variable(self.frame, self.offset + other.offset)
        else:
            return Variable(self.frame, self.offset + other)

    def __sub__(self, other):
        if isinstance(other, Variable):
            if self.frame is not other.frame:
                raise ValueError('Variables point to different frames')
            return Variable(self.frame, self.offset - other.offset)
        else:
            return Variable(self.frame, self.offset - other)

    def set(self, value):
        self.frame[self.offset] = value

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.frame, self.offset)


class Word(unicode):
    """\
    Like a string but annotated with the position in the source file it was read from.
    """
    def __new__(cls, word, filename, lineno, text):
        self = unicode.__new__(cls, word)
        self.filename = filename
        self.lineno = lineno
        self.text = text
        return self

    #~ def __repr__(self):
        #~ return "%s(%s, %s, %s)" % (
                #~ self.__class__.__name__,
                #~ unicode.__repr__(self),
                #~ self.filename,
                #~ self.lineno)


#
#  +--------------------------------+
#  |                                |
#  |   FORTH Language Interpreter   |
#  |     Command Line Interface     |
#  |                                |
#  +--------------------------------+
#

def main():
    from optparse import OptionParser
    logging.basicConfig(level=logging.ERROR)

    parser = OptionParser(usage="""\
%prog [options] [FILE...]|-]

If no input files are specified data is read from stdin."""
            )
    parser.add_option(
            "-o", "--outfile",
            dest="outfile",
            help="write outputs to given file",
            metavar="FILE",
            default=None)

    parser.add_option(
            "-v", "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="print status messages")

    parser.add_option(
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="print debug messages")

    parser.add_option(
            "-i", "--interactive",
            action="store_true",
            dest="interactive",
            default=False,
            help="interactive mode is started")

    parser.add_option("-D", "--define",
                      action = "append",
                      dest = "defines",
                      metavar = "SYM[=VALUE]",
                      default = [],
                      help="define symbol")

    parser.add_option("-I", "--include-path",
                      action = "append",
                      dest = "include_paths",
                      metavar = "PATH",
                      default = [],
                      help="Add directory to the search path list for includes")

    (options, args) = parser.parse_args()

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif options.verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARN)

    # prepare output
    if options.outfile is not None:
        out = codecs.open(options.outfile, 'w', 'utf-8')
    else:
        out = codecs.getwriter("utf-8")(sys.stdout)

    # XXX make stderr unicode capable
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

    instructions = []
    include_paths = []
    for filename in args:
        if filename == '-':
            if options.verbose:
                sys.stderr.write(u'reading stdin...\n')
            instructions.extend(words_in_file('<stdin>', fileobj=sys.stdin, include_newline=True))
            include_paths.append('.')
        else:
            if options.verbose:
                sys.stderr.write(u'reading file "%s"...\n'% filename)
            try:
                instructions.extend(words_in_file(filename, include_newline=True))
            except IOError as e:
                sys.stderr.write('forth: %s: File not found\n' % (filename,))
                sys.exit(1)
            include_paths.append(os.path.dirname(os.path.abspath(filename)))

    try:
        forth = Forth()
        # Change this to: forth.init(usefile=True) to use the __init__.forth file
        # By default this method will use forth_words.py to populate the initial
        # Forth word name space.
        forth.init()
        # default to source directory as include path
        forth.include_path = include_paths
        # extend include search path
        forth.include_path.extend(options.include_paths)

        # insert defined symbols
        for definition in options.defines:
            if '=' in definition:
                symbol, value = definition.split('=', 1)
            else:
                symbol, value = definition, '1'
            forth.namespace[symbol.lower()] = value # XXX inserted as string only

        #~ forth.doctree.chapter(filename)
        forth.interpret(iter(instructions))
        forth.doctree.render(out)
    except ForthError as e:
        sys.stderr.write(u"%s:%s: %s\n" % (e.filename, e.lineno, e))
        if options.debug and e.text:
            sys.stderr.write(u"%s:%s: input line was: %r\n" % (e.filename, e.lineno, e.text))
        #~ if options.debug: raise
        sys.exit(1)
    finally:
        # enter interactive loop when desired
        if options.interactive:
            interpreter_loop(debug = options.debug, rpn_instance=forth)

if __name__ == '__main__':
    main()
