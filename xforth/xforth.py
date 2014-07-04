#!/usr/bin/python3.3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Chris Liechti <cliechti@gmx.net>
# All Rights Reserved.
# Simplified BSD License (see LICENSE.txt for full text)

# xforth.py provides a generic framework for the creation of Forth-based cross-
# compilers.  It is based upon the MSP430 package cross-compiler, but only retains
# core Forth funcionality.
#
# It is expected that the classes offered by this module will be subclassed and
# if needed a command-line interface supplied.
#
# The original package can be found at this location:
# https://pypi.python.org/pypi/python-msp430-tools/0.6

# Modifications contributed by Harold Grovesteen under the Simplified BSD license
# Copyright (c) 2014 Harold Grovesteen
# All Right Reserved
# Simplified BSD License (see LICENSE.txt for full text)

# Python imports
import sys
import os
import codecs
import logging
import pprint
import re

# other imports:
from forth_words import definitions   # common host and target Forth words

this_module="xforth.py"

# The XFORTH cross-compiler consists of three primary components:
# 1. The FORTH text-intepreter, class Forth (or subclass)
# 2. Intermediate representation of the recognized words using class Frame and its
#    class FrameCell and their subclasses.
# 3. The Target class drives the compilation creating the final output file.  
#    The Target class must be subclassed tailoring its execution to the target
#    system's processor and forth threading model.
#
# See module msp430.py for an example of how these classes may be subclassed targeting
# a specific processor.
#
# xforth.py supports three process phases:
#
#    1. Interpretation Phase
#       Pre-built Python interpreted word definitions are automatically created in
#       the "builtin" name space.  text is then interpreted and compiled into
#       Python objects are placed wothin one of two additional name spaces.  Colon and
#       VARIABLE definitions are placed in the "namespace" name space.  Portions of
#       target output are compiled into the "target" name space.  Name spaces operate
#       like vocabularies during the Cross-Compilation Phase.
#
#       During the Interpretation Phase the Forth object subclass must drive the
#       assignment of memory type (RAM vs. ROM) and document tree location.  RAM vs.
#       ROM can be controlled by the corresponding RAM and ROM builtin words.
#       Document tree targeting is not presently exposed to the text interpreter.
#       Where RAM may be an option a separate name space, "variables", is used with
#       a generated name.
#                                                              "variable"
#    Word      name space Object          RAM/ROM    Doctree      name
#
#    :         namespace  Frame             --       assigned      --
#    CODE      target     NativeFrame       --       assigned      --
#    CREATE    namespace  Frame           current    assigned   cre+name
#    INTERRUPT target     InterruptFrame    --          --         --     
#    VALUE     namespace  Frame             --       assigned   val+name
#    VARIABLE  namespace  Frame             --       assigned   var+name
#    cre+name  variable   Frame             --          --         --
#    val+name  variable   Frame             --          --         --
#    var+name  variable   Frame             --          --         --
#
#       The CROSS-COMPILE word when executed from text interpretation or compiled
#       word determines the sequence in which root words are cross-compiled.  When all
#       text input is exhausted, the Interpretation Phase ends.  The COMPILE-MISSING
#       word causes referenced words not explicitly identified by a CROSS-COMPILE word
#       to be cross-compiled during the Cross-Compilation Phase.
#
#    2. Cross-Compilation Phase
#       The Cross-Compilation Phase is automatically entered following the
#       Interpretation Phase.  Identified root words are cross-compiled in the
#       order in which they were identified.  If the COMPILE-MISSING word was
#       interpreted during Interpretation Phase, all words referenced but not
#       explicitly identified are also cross-compiled.  The process of compiling
#       referenced words continues until all referenced words are compiled.
#       
#       Cross-compilation causes the subclass of Target to build the output for
#       the cross-compiler environment.  It is typically expected to be assembler
#       source statements, but nothing requires that to be the case.
#       The DocumentTree or its subclass is used to control output sequence of
#       the cross-compiler output.  Because words are not cross compiled in the
#       sequence in which they are interpreted and the targeted output may require
#       specific sequencing to satisfy the tool chain the implementation has
#       complete control over the constructed document tree.
#
# Supported Native code coding styles
#
# No standards exist for cross-compiler native code generation.  xforth.py supports
# three styles involving the words ASSEMBLE, CODE and CODE-WORD.  All native code
# words end with the used of the word END-CODE.  Native assembly code is used to
# create inline assembly statements and word definitions.  How the two different
# uses of native code are recognized and coded are defined by the coding style an 
# implementation will use.
#
#  1.  Word CODE generates all native assembly.  This coding style requires the
#      manual insertion of the native code word's exit logic.  Some threading models
#      will require use of Forth.assist_native_words() method for native words to
#      be used in word definitions.  The example in msp430.py uses this coding style
#      but the direct threading model does not require assist_native_words().
#      msp430.py uses the native word ASM-NEXT for manual exit logic insertion.
#  2.  Word CODE generates inline native assembly.  Word CODE-WORD generates native
#      assembly words used in word definitions.
#  3.  Word ASSEMBLE generates inline native assembly.  Word CODE generates native 
#      assembly words used in word definitions.  This case requires use of the
#      Forth.assist_code_is_word() by the cross-compiler implementation.
#
# The native code coding styile will influence the requirements of the NativeFrame
# subclass used by the cross-compiler.  In styles 2 and 3, the NativeFrame subclass
# method exit() must test the isword attribute for being True to determine if the
# native code word's exit logic must be generated.  In these two coding styles
# manual insertion of the exit logic is not required.
#
# The threading model can influence the use of assists.  Indirect and token-based
# threading models must know when a word must be bound to the binding table that
# links the cross-compiled word to the execution time logic.  In style one inline
# code vs a word definition are indistinguishable.  The Forth.assist_native_words()
# method supplied the name of one or more words when present cause the two types
# of native code to be recognized.  In the case of msp430.py, if it were to need
# this, the word ASM-NEXT would be supplied to the assist for word identification.

#
#  +---------------------------------+
#  |                                 |
#  |   FORTH Interpreter Exception   |
#  |                                 |
#  +---------------------------------+
#

class ForthError(Exception):
    def __init__(self, message, filename=None, lineno=None, column=None, \
                 offset=None, text=None):
        Exception.__init__(self, message)
        self.filename = filename or '<unknown>'
        self.lineno = lineno
        self.column = column
        self.offset = offset
        self.text = text


#
#  +------------------------------------+
#  |                                    |
#  |   XFORTH Builtin Word Decorators   |
#  |                                    |
#  +------------------------------------+
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
    function.forth_immediate = True
    return function

# The word decorator identifies a function as a builtin Forth word definition.
# It "tags" the function with the forth_name attribute used by the Forth class to
# identify its builtin words.  See the Forth.__init__() method for how this tag
# is used to idenfify builtin word definitions.
#
# The programmer's note quoted above applies to the nested definition of the 
# decorate_word() function the wrapper returns.
#
# The word decorator wrapper function adds annotates the method with the word's
# Forth attributes:
#   name   Specifies the Forth word's identifying name as a string.  The name is
#          added to the builtin namespace.
#   co     Specifies if the word is compile only.  Compile only words are not
#          recognized by the text interpreter but may occur in compiled frames.
#          Default is False (meaning the word is recognized by the text interpreter
def word(name,co=False):
    def decorate_word(function):
        function.forth_name = name.lower()  # word name in lower case
        function.forth_co= co               # whether word is compile-only
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

class Forth(list):
    # Regular expresssion for removal of line comments
    m_comment = re.compile('(#.*$)', re.UNICODE)
    
    # Generator supporting annotates the word's location before providing it to
    # the user of the iterator of Word objects.
    # Function arguments:
    #   sequence   an iterable sequence of Word objects and unicode strings.
    #   filename   Filename used to annotate each unicode string in the sequence.
    #              Defaults to None.
    #   lineno     Line number within the file of each unicode string in the sequence.
    #              Defaults to None.
    #   offset     Offset of each unicode string.  Ignored and defaults to None.
    #   text       Annotated text for each unicode string.
    # Warning: Exceptions raised within a generator cause it to silently terminate!!
    @staticmethod
    def annotated_words(sequence, filename=None, lineno=None, offset=None, text=None):
        for word in sequence:
            if isinstance(word, Word):
                yield word
            else:
                yield Word(word, filename, lineno, text)

    # Drives an interactive session with a Forth interpreter
    # Function arguments:
    #   namespace  Pre-established namespace if an interpreter object is not
    #              supplied.  Defaults to an empty dictionary.
    #   debug      Set to True to cause unexpected exceptions to be raised.
    #              Set to False to simply print unexpected exceptions without
    #              terminating the interpreter.  Defaults to False.
    #   cls        The class of the interpreter if an instance is not supplied.
    #              If the interpreter instance is not supplied with the clso
    #              argument, this class will be instantiated and its init() method
    #              will be called before the interactive session is started.
    #              Defaults to None in which case the class Forth is used.
    #   clso       An interpreter object used for the interactive session.  If
    #              supplied the cls argument is ignored.
    @staticmethod
    def interpreter_loop(namespace={}, cls=None, clso=None, debug=False):
        if cls is None:
            cls=Forth

        if clso is None:
            clso = cls(namespace)
            clso.init()
        while True:
            try:
                print()
                print(clso)
                words = input('> ')
                clso.interpret_sequence(words.split(), filename='<stdin>')
            except KeyboardInterrupt:
                print()
                break
            except SystemExit:
                raise
            except Exception as msg:
                if debug:
                    raise
                print("ERROR:", msg)

    # Simple word parser splitting words in a line
    @staticmethod
    def word_parser(line):
        return Forth.m_comment.sub('', line).split()
    
    # Word object generator.  Words are identified from a file.  Backslash line 
    # comments are removed before words are recognized.  Each word is annotated with
    # the filename and its line number (relative to 1) and the original line of text
    # from which the word was identifed.
    # Function arguments:
    #   filename         Path to the file being recognized.  Required.
    #   fileobj          A fileobj used to read text from a file.
    #                    If None, the filename is opened and UTF-8 encoding is applied
    #                    to the text file.  Defaults to None.
    #   include_newline  Specify True to cause a Word object to be generated for the
    #                    line termination sequence.
    # Warning: Exceptions raised within a generator cause it to silently terminate!!
    @staticmethod
    def words_in_file(filename, fileobj=None, include_newline=False, parser=None):
        if fileobj is None:
            fileobj = codecs.open(filename, 'r', 'utf-8')
        for n, line in enumerate(fileobj):
            for word in prsr(line):
                yield Word(word, filename, n+1, line)
            if include_newline:
                yield Word('\n', filename, n+1, line)

    # Word object generator.  Words are identified from a possible multi-line string.
    # Backslash line comments are removed before words are recognized.
    # Function arguments:
    #   data             The string from which words are identified.  Required.
    #   name             A name used to annotate the Word object for words from the
    #                    string.  Defaults to '<string>'.
    #   include_newline  Specify True to cause a Word object to be generated for the
    #                    line termination sequence.
    # Warning: Exceptions raised within a generator cause it to silently terminate!!
    @staticmethod
    def words_in_string(data, name='<string>', include_newline=False, parser=None):
        prsr = parser or Forth.word_parser
        for n, line in enumerate(data.splitlines()):
            for word in prsr(line):
                yield Word(word, name, n+1, line)
            if include_newline:
                yield Word('\n', name, n+1, line)

    # Initializes the Forth interpreter
    # Method arguments:
    #   threading  A string identifying the threading module to be used when
    #              compiling threaded word definitions.  Defaults to direct
    #   use_ram    Specifies the initial setting for memory type targets.  To 
    #              target ROM, specify False.  To target RAM, specify True.
    #              Defaults to False (or ROM).  The target compiler determines how
    #              the two settings are actually used to target the different memory
    #              types.
    def __init__(self, threading="direct", use_ram=False):
        super().__init__()
        self.clear()       # Initialize the interpreter data stack
        self.logger = logging.getLogger('xforth')  # Python logger.
        
        self.threading=threading     # Remember threading model

        # Interpreter initialization. See init() method:
        # The parser used to recognize words in a line of text
        self.parser=None             # Returned by init_parser() subclass method
        self.compiler=None           # Returned by cross_compiler() subclass method

        # Define the builtin host specific name space of decorated Python methods
        self.builtins = self.init_builtins()
        
        # Interpreter execution state:
        # current list of input Word objects being interpreted
        self._iterator = None        # Set by interpret() method from its argument
        # Current Frame object being executed or compiled
        self._frame_iterator = None

        # Define the threaded word name space (used on both host and target)
        # This dictionary maps a words name to its internal representation:
        #   - integers define CONSTANT definitions
        #   - Frame objects define : (colon) words
        #   - InterruptFrame objects define INTERRUPT words
        self.namespace = {}
        # the init() method starts word creation by interpreting forth_words.py
        # definitions

        # Define the target specific name space
        # This dictionary maps a native word's name to its NativeFrame content.
        # NativeFrame objects are created by ASSEMBLE, CODE or CODE-WORD definitions
        self.target_namespace = {}

        # Defined Variables.
        # This dictionary maps a name (generated at the time of creation) to a Frame
        # object.
        self.variables = {}

        # Interpreter compilation state:
        self.compiling = False        # Current Forth interpreter mode       
        self.frame = None             # Current Frame being compiled
        self.use_ram = use_ram        # Current target memory type - see RAM and ROM
        
        # These two dictionaries track words that need compiling 
        self.compiled_words = set()      # Track compiled words
        self.not_yet_compiled_words=set()# Track words not yet compiled words
        self.references={}            # Track number of times a word is referenced

        # Output document tree shared with the cross-compiler
        self.doctree = DocumentTree()
        
        # Cross-compiler assistance data and settings
        self.code_is_word=False       # See self.assist_code_is_word() method
        self.native_words=[]          # See self.assist_native_words() method

    # return a string describing the topmost elements from the stack
    # Used primarily by Forth.interpreter_loop() static method.
    def __str__(self):
        if self:
            N = min(4, len(self))
            tops = ["%s:%s" % ("xyzt"[i], self.printer(self[-i-1])) for i in range(N)]
            if len(self) > 4:
                tops.append(' (%d more)' % (len(self)-4,))
            return ' '.join(tops)
        return "stack empty"

    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)

    #
    # The following methods must be supplied by a subclass of this class
    # See msp430.py for an example of their usage.
    #

    # Required: Supplies inline data to a standard word Frame or InterruptFrame.
    # The object links the interpreter frame creation with the cross-compiler's
    # generation of a frame's content.
    #
    # The following interpreted words create inline data:
    #    '   "    ."    [CHAR]   CREATE   TO   VALUE   VARIABLE
    # and compiled literal numbers using word $LIT
    # Returns: The instantiated Inline subclass for the specified word.
    def create_inline(self, word, value):
        raise NotImplementedError(self._nie("create_inline()"))

    # Requried: This method returns an instantiated compiler based upon the supplied
    # threading string.  The actual string and its meaning to the target compiler
    # are specific to the capabilities of the targeted implementation.  Forth supplied
    # assist methods should be called by the subclass in this method.
    def cross_compiler(self, *args, **kwds):
        raise NotImplementedError(self._nie("cross_compiler()"))

    # Required: This method locates, accesses and interprets the included file.
    def include(self, name):
        raise NotImplementedError(self._nie("include()"))

    # This method locates and reads the named resource from a package.  It returns
    # a binary string if located.  If the resource is not found it returns None.
    # A subclass wanting to read forth source files as if they were a module must
    # provide this method
    def include_module(self, name):
        raise NotImplementedError(self._nie("include_module()"))

    # This method locates the file in the include search path by returning the
    # file's path.  If not found it returns None.  A subclass wishing to support
    # included files from a search path must provide this method.  It is the
    # the subclass responsibility to establish the directory search order and use
    # it to locate included source files
    def include_path(self, name):
        raise NotImplementedError(self._nie("include_path()"))

    # Required: Supplied the interpreter text parser.
    # The default is Forth.word_parser() staticmathe and should be returned if a 
    # replacement parser is not available.
    # Returns: A generator that parses the words in a line of text.
    def init_parser(self, *args, **kwds):
        raise NotImplementedError(self._nie("init_parser()"))

  #
  # Interpeter assists for the cross-compiler
  #

    # Causes use of the word CODE to create NativeFrame's with NativeFrame.isword
    # set to True.
    def assist_code_is_word(self):
        self.code_is_word=True

    # This method allows the cross-compiler (usually in the cross_compiler() subclass
    # method) to specify one or more words that when encountered cause a NativeFrame
    # to become recognized as word.  This is needed for certain threading models.
    # If the cross-compiler does not use those threading models or this technique
    # for native word recognition, it is not required.
    #
    # Although not required by msp430.py the word ASM-NEXT would be an example
    def assist_native_words(self, wordlist):
        if not isinstance(wordlist, list):
            self.native_words=[ wordlist, ]
        else:
            self.native_words=wordlist

  #
  # Callback methods exposed to subclass or cross-compiler
  #

    # Returns the current active doctree chapter name
    def current_chapter(self):
        return self.doctree.chapter_name

    # Drives cross compilation of a word's thread body.
    # Called by the cross-compiler when a thread body needs compiling.
    def compile_thread(self, frame):
        next = iter(frame).next 
        ndx=0   # Next cell being fetched 
        
        try:
            while True:
                # Determine if the next thread cell needs tagging as branch target
                if ndx in frame.tags:
                    tag=ndx
                else:
                    tag=None
                    
                # Fetch the thread cell being cross-compiled
                entry = next()
                ndx+=1 

                if callable(entry):
                    if self.isbuiltin(entry,name="$BRANCH"):
                        offset = next()
                        ndx+=1
                        self.compiler.compile_branch(selt, offset, tag=tag)
                        self.compiler.compile_remember('$BRANCH')
                    elif self.isbuiltin(entry,name="$BRANCH0"):
                        # branch needs special case as offset needs to be recalculated
                        offset = next()
                        ndx+=1
                        self.compiler.compile_branch_if_false(self, offset, tag=tag)
                        self.compiler.compile_remember('$BRANCH0')
                    elif self.isbuiltin(entry):
                        # all other built-ins just take the name of the function
                        self.compiler.compile_builtin(forth, entry, tag=tag)
                        self.compiler.compile_remember(entry.forth_name)
                    elif isinstance(entry, Frame):
                        self.compiler.compile_word(forth, entry, tag=tag)
                        self.compiler.compile_remember(entry.name)
                    elif isinstance(entry, Inline):
                        self.entry.cross_compile(self, self.compiler, self.doctree)
                    else:
                        raise ValueError('Cross compilation undefined for %r' % entry)
                else:
                    self.compiler.compile_value( self, entry, tag=tag)
        except StopIteration:
            pass

  #
  # Interpreter Methods
  #

    def compiled(self, name):
        pass

    # Create a Forth interrupt handler
    def create_interrupt(self, name, vector):
        frame=self.compiler.create_interrupt(self, name, vector)
        if not isinstance(frame, InterruptFrame):
            cls_str="%s - %s.create_interrupt() -" \
                % (this_module,self.__class__.__name__)
            msg="%s - invalid InterruptFrame object returned for interrupt %s:" \
                 "vector %s: %s"  % (cls_str,name,vector, frame)
            raise ValueError(msg)
        return frame

    # Create a native code word for the target
    def create_native(self, name, isword=False):
        frame=self.compiler.create_native(self, name, isword=isword)
        if not isinstance(frame, NativeFrame):
            cls_str="%s - %s.create_native() -" \
                % (this_module,self.__class__.__name__)
            msg="%s - invalid NativeFrame object returned for name %s:" \
                % (cls_str,name,frame)
            raise ValueError(msg)
        return frame

    # Create's a word defintion frame by calling the target compiler
    def create_word(self, name):
        frame=self.compiler.create_word(self, name)
        if isinstance(frame, (InterruptFrame, NativeFrame)) or \
           not isinstance(frame, Frame):
            cls_str="%s - %s.create_word() -" % (this_module,self.__class__.__name__)
            msg="%s - invalid Frame object returned for word %s: %s" \
                % (cls_str,name,frame)
            raise ValueError(msg)
        return frame

    def init(self,debug=False):
        # load core language definitions from forth_words.py
        name=self.__class__.__name__
        self.logger.info('%s.init() processing' % name)
        self.parser=self.init_parser()
        
        error=False
        # Initialize cross compiler
        compiler=self.cross_compiler()
        if isinstance(compiler,Target):
            self.compiler=compiler
            # Validate requested threading model and allow compiler to turn on interpreter
            # assists
            if not self.compiler.init_model(self.threading, self):
                msg="%s compiler does not support requested threading " \
                    "model: %s" % (self.compiler.__class__.__name__,self.threading)
                self.logger.error(msg)
                error=True

        if error:
            self.logger.error("%s.init() failed" % name)
            sys.exit(1)

        # Define foundational word definitions shared by the host and target
        # environments.
        data=definitions
        self.interpret(\
            Forth.words_in_string(data, name='init()',include_newline=True))
        if debug:
            self.word_LIST(None)

        # Interpreter initialization done.
        self.logger.info('%s.init() done' % name)

    def init_builtins(self):
        builtins={}
        for name in dir(self):
            function = getattr(self, name)
            if self.isbuiltin(function):
                builtins[function.forth_name] = function
        return builtins

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
        doctree=self.doctree
        if isinstance(item, Frame):
            item.enter(stack, doctree)
            item.cross_compile(stack, doctree)
            item.exit(stack, item)
        else:
            raise ValueError('don\'t know how to compile word %r' % (word,))

    # This needs to be replaced with a builtin word that corresponds to the 
    # target implementation.
    def instruction_output_text(self, stack):
        words = stack._frame_iterator.next()
        self.doctree.write(words)

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
                word = iterator.__next__()
                self.interpret_word(word)
        except StopIteration:
            pass
        except ForthError as fe:
            raise fe
        except Exception as e:
            filename = getattr(word, 'filename', '<unknown>')
            lineno = getattr(word, 'lineno', None)
            column = getattr(word, 'column', None)
            offset = getattr(word, 'offset', None)
            text = getattr(word, 'text', None)
            self.logger.exception(\
                '%s:%s: Error in word "%s": %s' % (filename, lineno, word, e))
            raise ForthError('Error in word "%s": %s' % (word, e), \
                filename, lineno, column, offset, text)
            # XXX consider showing the full traceback of the original exception
        finally:
            # restore state
            self._iterator = old_iterator

    def interpret_sequence(self, sequence, filename=None):
        """interpret a sequence of words"""
        self.interpret(Forth.annotated_words(sequence, filename))

    # Text interpreter subroutine to compile or execute a word
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
                if isinstance(self.frame,NativeFrame) and word in self.native_words:
                    self.frame.isword=True
                if callable(element):
                    # Track branches for assembler tagging of target locations
                    if self.isbranch(element):
                        self.frame.branches.append(len(self.frame))
                    self.frame.append(element)
                else:
                    self.frame.append(self.look_up("$LIT"))
                    self.frame.append(element)
                return
            else:
                # interpreting or immediate word while compiling
                if element.forth_co:
                    raise ValueError("compile-only word: %s" % word)
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
            self.frame.append(self.look_up("$LIT"))
            self.frame.append(self.create_inline("$LIT",number))
        else:
            self.push(number)

    # Determine whether a builtin compile-only branch
    def isbranch(self, method):
        return self.isbuiltin(method,name="$BRANCH") \
               or self.isbuiltin(method,name="$BRANCH0")

    # Return whether a method is a forth builtin or a specific builtin.
    # Method Argument:
    #   name   Specify a string to validate a method as a specific builtin method
    #          decorated with a specific Forth word where @word(name).
    #          Specify None to validate if the method is generically a builtin. 
    #          Default is None
    def isbuiltin(self, method, name=None):
        if hasattr(method, "forth_name"):
            if name:
                return method.forth_name==name.lower()
            else:
                return True
        else:
            return False

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

    # Returns the next word being interpreted
    def next_word(self):
        return self._iterator.__next__()

    def pop(self):
        """Get an element from the stack"""
        try:
            return list.pop(self)
        except IndexError:
            raise IndexError("pop called on empty stack")

    def pop2(self):
        """Get two elements from the stack"""
        return self.pop(), self.pop()

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

    # Remember to compile these referenced words
    def remember(self, name):
        word=name.lower()
        try:
            ref=self.not_yet_compiled_words[word]
        except KeyError:
            # first time this is referenced
            ref=0
        self.not_yet_compiled_words[word]=ref+1

    #
    # Builtin name space word definitions
    #

    # Compile-only builtins - interpreted within a frame but not by text interpreter
    
    @word('$BRANCH',co=True)
    def instruction_seek(self, stack):
        """Get offset from sequence and jump to this position."""
        difference = stack._frame_iterator.next()
        stack._frame_iterator.seek(difference - 1)

    @word('$BRANCH0',co=True)
    def instruction_branch_if_false(self, stack):
        """\
        Get offset from sequence and a boolean from stack. Jump if boolean was
        false.
        """
        difference = stack._frame_iterator.next()
        if not stack.pop():
            stack._frame_iterator.seek(difference - 1)

    @word('$LIT',co=True)
    def instruction_literal(self, stack):
        """Low level instruction to get a literal and push it on the stack."""
        inline=stack._frame_iterator.next()
        stack.push(inline.value)

    @word("$TEXT",co=True)
    def output_text(self, stack):
        text = stack._frame_iterator.next()
        # text is expected to be an instance of Inline
        self.doctree.write(words.value) 

    # Recognized by both text and frame interpreters

    @word("+")
    def add(self, stack):
        """Add two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(y + x)

    @word("/")
    def div(self, stack):
        """Divide two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(y / x)

    @word("==")
    def equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y == x))

    @word(">")
    def larger(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y > x))

    @word(">=")
    def larger_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y >= x))

    @word("*")
    def mul(self, stack):
        """Multiply two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(y * x)

    @word("!=")
    def not_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y != x))

    @word("<")
    def smaller(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y < x))

    @word("<=")
    def smaller_equal(self, stack):
        """Compare two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(bool(y <= x))

    @word("-")
    def sub(self, stack):
        """Subtract two numbers on the stack."""
        x, y = stack.pop2()
        stack.push(y - x)

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
        self.frame=self.create_word(name)
        self.compiling = True

    @word(',')
    def word_comma(self, stack):
        """Append value from stack to current definition."""
        if self.frame is None: raise ValueError('not in colon definition')
        value = stack.pop()
        if isinstance(value, Variable):
            # XXX special case for calculations with HERE
            value = value.offset
        elif self.isbranch(value):
            self.frame.branches.append(len(self.frame))
        else:
            pass
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
            #self.frame.append(self.instruction_output_text)
            self.frame.append(self.look_up("$TEXT"))
            self.frame.append(self.compiler.create_inline("$TEXT",text))
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
        self.frame.tag_branches()
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
            self.frame.append(self.look_up("$LIT"))
            self.frame.append(self.create_inline('"', text))
        else:
            self.push(text)

    @immediate
    @word("'")
    def word_tick(self, stack):
        """Push reference to next word on stack."""
        # Note this method creates inline data
        if self.frame is None: raise ValueError('not in colon definition')
        name = stack.next_word()
        word_frame=self.look_up(name)  # Frame or InterruptFrame
        self.frame.append(self.look_up("$LIT"))
        self.frame.append(self.create_inline("'", word_frame))

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
        stack[-1] = stack[-1] - 1

    @word("1+")
    def plus_1(self, stack):
        stack[-1] = stack[-1] + 1

    @word("2*")
    def arithmetic_shift_left(self, stack):
        stack[-1] = stack[-1]*2

    @word("2/")
    def arithmetic_shift_right(self, stack):
        stack[-1] = stack[-1]/2

    @word("2-")
    def minus_2(self, stack):
        stack[-1] = stack[-1] - 2

    @word("2+")
    def plus_2(self, stack):
        stack[-1] = stack[-1] + 2

    @word("4-")
    def minus_4(self, stack):
        stack[-1] = stack[-1] - 4

    @word("4+")
    def plus_4(self, stack):
        stack[-1] = stack[-1] + 4

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
        x, y = stack.pop2()
        stack.push(y & x)

    @immediate
    @word('ASSEMBLE')
    def word_assemble(self, stack):
        """\
        Begin defining a native inline code. CODE words are executed on the
        host to get cross compiled. Therefore they have to output assembler
        code for the target. MSP430 Example:

            ( > Increment value on stack by one. )
            ASSEMBLE 1+ ( n -- n )
                ." \\t inc 0(SP) \\n "
            END-CODE

        There is a number of supporting functions for outputting assembler.
        E.g. `ASM-NEXT`_, `ASM-DROP`_, `ASM-TOS->R15`_, `ASM-R15->TOS`_,
        `ASM-TOS->W`_, `ASM-W->TOS`_

        This word is equvalent to the word CODE when assist_code_is_word has not
        been used.
        """
        name = self.next_word()
        self.frame=self.create_native(name, isword=False)
        self.compiling = True

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
        # Note this word created inline data
        name = stack.next_word()
        value = ord(name[0])
        if self.compiling:
            if self.frame is None: raise ValueError('not in colon definition')
            self.frame.append(self.look_up("$LIT"))
            self.frame.append(self.create_inline("[CHAR]", value))
        else:
            raise ValueError('interpretation semantics undefined')

    @word("CLEAR")
    def clear(self, stack=None):
        """Clear stack."""
        if stack:
            del stack[:]
        else:
            del self[:]

    @immediate
    @word('CODE')
    def word_code(self, stack):
        """\
        Begin defining a native code function. CODE words are executed on the
        host to get cross compiled. Therefore they have to output assembler
        code for the target. MSP430 Example:

            ( > Increment value on stack by one. )
            CODE 1+ ( n -- n )
                ." \\t inc 0(SP) \\n "
                ASM-NEXT
            END-CODE

        There is a number of supporting functions for outputting assembler.
        E.g. `ASM-NEXT`_, `ASM-DROP`_, `ASM-TOS->R15`_, `ASM-R15->TOS`_,
        `ASM-TOS->W`_, `ASM-W->TOS`_

        Note that the NEXT instruction is not automatically inserted and must be
        added manually (see `ASM-NEXT`_ in example above).  See alternatively
        word CODE-WORD
        """
        name = self.next_word()
        self.frame=self.create_native(name, isword=self.native_code_is_word)
        self.compiling = True

    @immediate
    @word('CODE-WORD')
    def word_code_word(self, stack):
        """\
        Begin defining a native code function. CODE words are executed on the
        host to get cross compiled. Therefore they have to output assembler
        code for the target. MSP430 Example:

            ( > Increment value on stack by one. )
            CODE 1+ ( n -- n )
                ." \\t inc 0(SP) \\n "
            END-CODE

        This is essentially identical to the word CODE, but does not require
        the explicit use of ASM-NEXT.  If this word is used, the cross-compiler's
        subclass of NativeFrame will need to append the equvalent of ASM-NEXT during
        cross-compilation in the subcalss exit() method.
        """
        name = self.next_word()
        self.frame=self.create_native(name, isword=True)
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
        self.variables[name] = Frame('cre'+name,isword=False)
        self.variables[name].use_ram = self.use_ram
        self.frame = self.variables[name]

        # create a function that pushes the variables address
        frame = Frame(name)
        frame.chapter = self.doctree.chapter_name
        frame.append(self.look_up("$LIT"))
        frame.append(self.create_inline("CREATE", self.variables[name])) 
        self.namespace[name.lower()] = frame
        # XXX could also do a native impl with "push #adr;NEXT"

    @immediate
    @word('CROSS-COMPILE')
    def word_cross_compile(self, stack):
        """Output cross compiled version of function. Example:: ``CROSS-COMPILE DROP``"""
        word = stack.next_word()
        if self.compiling:
            # when compiling add call to self and the word to the Frame
            self.frame.append(self.look_up("CROSS-COMPILE"))
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
        self.compiler.cross_compile_missing()

    @word('CROSS-COMPILE-VARIABLES')
    def word_cross_compile_variables(self, stack):
        """\
        Output section with variables (values in RAM).
        """
        self.compiler.cross_compile_variables(stack)

    @immediate
    @word('DEPENDS-ON')
    def word_depends_on(self, stack):
        """\
        Mark word as used so that it is included in cross compilation. Useful
        when using other words within CODE_ definitions.
        """
        if self.compiling:
            word = stack.next_word()
            self.frame.append(self.word_depends_on)
            self.frame.append(word)
        else:
            word = stack._frame_iterator.next()
            self.compiler.compile_remember(word)

    @word("DROP")
    def drop(self, stack):
        """Remove and forget about topmost element on the stack."""
        stack.pop()

    @word("DUP")
    def dup(self, stack):
        """Duplicate the topmost element on the stack."""
        stack.push(stack[-1])

    @word('EMIT')
    def word_emit(self, stack):
        """Output number on stack as Unicode character."""
        self.doctree.write(unichr(stack.pop()))

    @immediate
    @word('END-CODE')
    def word_end_code(self, stack):
        """End definition of a native code function. See CODE_."""
        if self.frame is None: raise ValueError('not in colon definition')
        self.target_namespace[self.frame.name.lower()] = self.frame
        self.frame = None
        self.compiling = False

    @immediate
    @word('END-INTERRUPT')
    def word_end_interrupt(self, stack):
        """End definition of a native code function. See INTERRUPT_ for example."""
        if self.frame is None: raise ValueError('not in colon definition')
        self.frame.tag_branches()
        self.target_namespace[self.frame.name.lower()] = self.frame
        self.frame = None
        self.compiling = False

    @word("FLOAT")
    def word_FLOAT(self, stack):
        """Convert TOS to a floating point number."""
        stack.push(float(self.pop()))

    @word('HERE')
    def word_here(self, stack):
        """Put position [within frame] on stack"""
        stack.push(Variable(self.frame, len(self.frame)))

    @word("IFTE")
    def word_IFTE(self, stack):
        """\
        If then else for 3 values on the stack: predicate, value_true,
        value_false.
        """
        x, y = stack.pop2()
        z = stack.pop()
        if z:
            stack.push(y)
        else:
            stack.push(x)

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
        name = stack.next_word()
        self.include(name)

    @word("INT")
    def word_INT(self, stack):
        """Convert TOS to an integer."""
        stack.push(int(self.pop()))

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
        name = stack.next_word()
        vector = stack.pop()
        self.frame=self.create_interrupt(name, vector)
        self.compiling = True

    @word("INVERT")
    def bitnot(self, stack):
        stack.push(~stack.pop())

    @word("LIST")
    def word_LIST(self, stack):
        """testing only: print all knwon words to stdout"""
        for namespace in (self.builtins, self.namespace):
            pprint.pprint(namespace)

    @word("LSHIFT")
    def bit_shift_left(self, stack):
        x, y = stack.pop2()
        stack.push(y << x)

    @word("MAX")
    def maximum(self, stack):
        """Leave the larger of two values on the stack."""
        x, y = stack.pop2()
        stack.push(max(y, x))

    @word("MIN")
    def minimum(self, stack):
        """Leave the smaller of two values on the stack."""
        x, y = stack.pop2()
        stack.push(min(y, x))

    @word("NEG")
    def negate(self, stack):
        """Negate number on stack."""
        stack.push(-self.pop())

    @word("NOT")
    def word_NOT(self, stack):
        stack.push(not stack.pop())

    @word("OR")
    def bitor(self, stack):
        x, y = stack.pop2()
        stack.push(y | x)

    @word("OVER")
    def over(self, stack):
        """Push a copy of the second element on the stack."""
        stack.push(stack[-2])

    @word("PICK")
    def pick(self, stack):
        """Push a copy of the N'th element on the stack."""
        stack.push(stack[-stack.pop()])

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
        # put conditional branch operation in sequence, remember position of 
        # offset on stack
        self.frame.branches.append(len(self.frame))
        self.frame.append(self.instruction_branch_if_false)
        stack.push(len(self.frame))
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
        x, y = stack.pop2()
        stack.push(y >> x)

    @word('SHOW')
    def word_SHOW(self, stack):
        """Show internals of given word. Used to debug."""
        name = stack.next_word()
        sys.stderr.write('SHOW %r\n' % name)
        try:
            value = self.look_up(name)
        except KeyError:
            sys.stderr.write('     value -> <undefined>\n')
        else:
            if isinstance(value,int):
                sys.stderr.write("    word   -> True\n")
                sys.stderr.write("    co     -> False\n")
                sys.stderr.write('    value  -> %r\n' % value)
            elif isinstance(value,Frame):
                # Assume Frame object
                sys.stderr.write("    word   -> %s\n" % (value.isword))
                sys.stderr.write("    co     -> %s\n" % (value.forth_co))
                if value.use_ram:
                    sys.stderr.write("    memory -> RAM\n")
                else:
                    sys.stderr.write("    memory -> ROM\n")
                sys.stderr.write('    value  -> %r\n' % (value,))
                sys.stderr.write('    contents ->\n')
                for ndx, item in enumerate(value):
                    if self.isbuiltin(item):
                        sys.stderr.write('        [%s] %s   %r\n' \
                            % (ndx,item.forth_name,item))
                    else:
                        sys.stderr.write('        [%s] %r\n' % (ndx,item))
                sys.stderr.write('    branches -> %r\n' % value.branches)
                sys.stderr.write('    tag ndxs -> %r\n' % value.tags)
                sys.stderr.write('    chapter  -> %s\n' % value.chapter)
                sys.stderr.write('    section  -> %s\n' % value.section)
            elif self.isbuiltin(value):
                sys.stderr.write("    word   -> %s\n" % value.forth_name)
                sys.stderr.write("    co     -> %s\n" % value.forth_co)
                sys.stderr.write('    value  -> %r\n' % value)
            else:
                sys.stderr.write("    word   -> %s\n" % name)
                sys.stderr.write('    value -> <unrecognized> %r\n' % value)

    @word("SWAP")
    def swap(self, stack):
        """Exchange the two topmost elements on the stack."""
        stack[-1], stack[-2] = stack[-2], stack[-1]

    @word("TARGET")
    def word_TARGET(self, stack):
        """testing only: print all knwon words to stdout"""
        for namespace in (self.target_namespace, self.namespace):
            pprint.pprint(namespace)

    @immediate
    @word('TO')
    def word_to(self, stack):
        """Write to a VALUE_. Example: ``123 SOMEVALUE TO``"""
        name = "val" + stack.next_word()
        if self.compiling:
            self.frame.append(self.look_up("$LIT"))
            self.frame.append(self.create_inline("TO",self.variables[name]))
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
        self.variables[name] = Frame('val'+name,isword=False)
        self.variables[name].append(value)

        # create a function that pushes the variable's address
        frame = Frame(name)
        frame.chapter = self.doctree.chapter_name
        frame.append(self.look_up("$LIT"))
        frame.append(self.create_inline("VALUE", self.variables[name]))
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
        self.variables[name] = Frame('var'+name,isword=False)
        self.variables[name].append(0)

        # create a function that pushes the variables address
        frame = Frame(name)
        # Add subclass interface
        frame.chapter = self.doctree.chapter_name
        frame.append(self.look_up("$LIT"))
        #frame.append(self.variables[name])
        frame.append(self.create_inline("VARIABLE", self.variables[name]))
        self.namespace[name.lower()] = frame
        # XXX could also do a native impl with "push #adr;NEXT"

    @word('WORD')
    def word_word(self, stack):
        """Read next word from the source and put it on the stack."""
        stack.push(stack.next_word())

    @word("XOR")
    def bitxor(self, stack):
        x, y = stack.pop2()
        stack.push(y ^ x)


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


#
#  +---------------------------------------------+
#  |                                             |
#  |   FORTH Word Intermediate Representation    |
#  |                                             |
#  +---------------------------------------------+
#


# Base class for Shared Host and Target word definitions and other definitions
class Frame(list):
    def __init__(self, name, chapter=None, section=None, ram=False, \
                 isword=True, co=False):
        super().__init__()
        self.name = name         # Forth word name
        self.forth_co = co       # Compile-only status
        self.chapter = chapter   # Doctree chapter to which Frame is assigned
        self.section = section
        self.use_ram = ram
        self.isword=isword
        self.branches=[]
        self.tags=[]

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
    
    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)
  
  #
  # Methods used by the forth interpreter during compilation
  #

    def tag_branches(self):
        for n in self.branches:
            offset=self[n+1]
            tag=n+offset+1
            if not tag in self.tags: 
                self.tags.append(tag)
  
  #
  # These methods must be supplied by the cross-compiler using a subclass
  #

    # This method compiles the frame definition
    def cross_compile(self, forth, doctree):
        raise NotImplementedError(self._nie("compile_compile()"))
    
    # This method compiles the frame's entry requirements
    def enter(self, forth, doctree):
        raise NotImplementedError(self._nie("enter()"))
        
    # This method compiles the frame's exit requirements
    def exit(self, forth, doctree):
        raise NotImplementedError(self._nie("exit()"))

# Base class for inline data.  Inline data occupies an element in a Frame but
# are not directly executable.  They must be consumed by the previous Frame element
# when interpreted.  The purpose of the Inline object is to allow the cross-compiler
# to tailor inline data generation.  Python builtin's must also understand the
# Inline object.  The Inline object (a subclass usually) is supplied by the Forth
# subclass method create_inline() method.  The 
class Inline(object):
    def __init__(self, value):
        self.value=value

    def __repr__(self):
        if hasattr(self.value, "forth_name"):
            v="%s   %s" % (self.value.forth_name, self.value)
        else:
            v=self.value
        return '%s[%s]' % (self.__class__.__name__, v)
        
  #
  # This method is required to create the cross-compiler output for the inline data
  #

    # Required: Generate compiler output for the inline data
    # Method Arguments:
    #   forth     The interpreter is provided for method access
    #   compiler  The cross-compiler is provided for method access
    #   doctree   The output document tree is suppled for output generation
    def cross_compile(self, forth, compiler, doctree):
        method="cross_compile()"
        raise NotImplementedError("%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method))

# Interrupt Handling word definition
class InterruptFrame(Frame):
    def __init__(self, name, vector, \
                 chapter=None, section=None, ram=False, isword=True):
        super().__init__(name, \
            chapter=chapter, section=section, ram=ram, isword=isword)
        self.vector = vector


# Word or assembler sequence definition
class NativeFrame(Frame):
    def __init__(self,name, chapter=None, section=None, ram=False, isword=False):
        super().__init__(name, \
                         chapter=chapter, section=section, ram=ram, isword=isword)  


# Variable definition used by interpreter.  Not interpreted but may appear in 
# a frame as inline data.
class Variable(object):
    # typical variable usage: "HERE @". so the variable name would put the
    # address of the variable on the stack. The value of HERE is then also used
    # to write to (e.g. in the implementation of IF/ENDIF. As we do not have
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

# A string object annotated with the position in the source file from which it was
# read.
class Word(str):
    def __new__(cls, word, filename, lineno, text):
        self = str.__new__(cls, word)
        self.filename = filename
        self.lineno = lineno
        self.text = text
        return self

#
#  +--------------------------------------+
#  |                                      |
#  |   FORTH Target Compiler Interface    |
#  |                                      |
#  +--------------------------------------+
#

# Base class for a cross-compiler

class Target(object):
    def __init__(self,forth):
        self.forth=forth
        self.doctree=forth.doctree

    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)

  #
  # The following methods must be supplied by a subclass of this class
  #


    # Required: Compile a unconditional branch in a thread
    # Method Arguments:
    #   forth    the interpreter object
    #   target   the thread cell index being targeted by this branch
    #   tag      Tag of this branch if it is also a target of a branch
    def compile_branch(self, forth, target, tag=None):
        raise NotImplementedError(self._nie("compile_branch()"))

    # Required: Compile an unconditional branch when False in a thread
    # Method Arguments:
    #   forth    the interpreter object
    #   target   the thread cell index being targeted by this conditional branch
    #   tag      Tag of this conditional branch if it is also a target of a branch
    def compile_branch_if_false(self, forth, target, tag=None):
        raise NotImplementedError(self._nie("compile_branch_if_false()"))

    # Required: Compile a builtin word referenced in a thread
    # Method Arguments:
    #   forth    the interpreter object
    #   builtin  the interpreter method tagged as a word by the @word decorator
    #   tag      Tag of this builtin thread reference when a target of a branch.
    def compile_builtin(self, forth, builtin, tag=None):
        raise NotImplementedError(self._nie("compile_builtin()"))

    # Required: This remembers that a word is used and must be compiled
    # Method Arguments:
    #   forth  the interpreter object
    #   word   The word name that is being remembered for later compilation
    def compile_remember(self, forth, word):
        raise NotImplementedError(self._nie("compile_remember()"))

    # Required: Compilers or handles an undefined thread cell content that is
    # not recognized by the interpreter.
    # Method Arguments:
    #   forth  the interpreter object
    #   value  Non-callable element in frame, treat it as an explicit value
    #   tag    The thread index of this thread element when a branch target.
    def compile_value(self, forth, value, tag=None):
        raise NotImplementedError(self._nie("compile_unrecognized()"))

    # Required: Compile a word into a thread
    # Method Arguments:
    #   forth  the interpreter object
    #   frame  The Frame object of the word being referenced in a thread
    #   tag    Cell index of this word when tagging required for branch targets.
    def compile_word(self, forth, frame, tag=None):
        raise NotImplementedError(self._nie("compile_word()"))

    # Required: Returns an instance of InterruptFrame (or a subclass)
    # doctree locations, word status and memory type assignments should be done
    # here.
    # See Forth.create_interrupt() method for detail interpreter processing
    def create_interrupt(self, forth, name, vector):
        raise NotImplementedError(self._nie("create_interrupt()"))

    # Required: Returns an instance of NativeFrame (or a subclass)
    # doctree locations, word status and memory type assignments should be done
    # here.
    # See Forth.create_native() method for detail interpreter processing
    def create_native(self, forth, name, isword=False):
        raise NotImplementedError(self._nie("create_native()"))

    # Required: Returns an instance of Frame (or a subclass other than NativeFrame
    # or InterruptFrame)
    # doctree locations, word status and memory type assignments should be done
    # here.
    # See Forth.create_word() method for detail interpreter processing
    def create_word(self, forth, name):
        raise NotImplementedError(self._nie("create_word()"))

    # Required: Cross-compile all referenced words not yet compiled.
    def cross_compile_missing(self, forth):
        raise NotImplementedError(self._nie("cross_compile_missing()"))

    # Required: Cross-compile all defined variables
    def cross_compile_variables(self, forth):
        raise NotImplementedError(self._nie("cross_compile_variables()"))

    # Required: Validate requested threading model and set interpreter assists for
    # the target compiler.  Utilize forth object assist_XXXX methods to enable
    # desired assistance functionality.  See the Forth class for supported assist
    # methods.
    # Returns:
    #   True if model supported by the target compiler
    #   False or None if model not supported.
    def init_model(self, model, forth):
        raise NotImplementedError(self._nie("init_model()"))


if __name__ == '__main__':
    raise NotImplementedError("module %s only intended for import" % this_module)

