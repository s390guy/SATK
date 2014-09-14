#!/usr/bin/python3.3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Chris Liechti <cliechti@gmx.net>
# All Rights Reserved.
# Simplified BSD License (see LICENSE.txt for full text)

# xforth.py provides a generic framework for the creation of Forth-based cross-
# compilers.  It is based upon the MSP430 package cross-compiler, but only retains
# core Forth funcionality from that package.
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
#
# The XFORTH cross-compiler consists of four primary components:
# 1. The FORTH text-intepreter, class Forth (or subclass)
# 2. Intermediate representation of the recognized words using class Frame and its
#    class FrameCell and their subclasses.
# 3. The Target class drives the compilation creating the final output file.  
#    The Target class must be subclassed tailoring its execution to the target
#    system's processor and forth threading model.
# 4. A document manager.  The document manager must be a subclass of DocumentTree. 
#
# See module msp430.py for an example of how these classes may be subclassed targeting
# a specific processor.
#
# xforth.py supports four phase process:
#
#    1. Interpretation Phase
#       Pre-built Python interpreted word definitions are automatically created in
#       the "builtin" name space.  text is then interpreted and compiled into
#       Python objects placed within one of two additional name spaces.  Colon and
#       VARIABLE definitions are placed in the "namespace" name space.  Portions of
#       target output are compiled into the "target" name space.  Name spaces operate
#       like vocabularies during the Cross-Compilation Phase.
#
#       During the Interpretation Phase, the Forth object subclass must drive the
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
#       The CROSS-COMPILE word when executed from the text interpreter or compiled
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
#    3. Output Document Creation
#       The output document content is derived during the cross-compilation Phase.
#       However the sequence of the content is managed by the document manager, a
#       subclass of the DocumentTree class.  It constructs and outputs the content
#       to a file.  Content is assigned a named chapter and a named section within 
#       the chapter.  Output file content is placed in the output file based upon
#       the collating sequence of chapter names and within the chapter by the
#       collating sequence of sections within the chapter.
#
#    4. Interactive Mode
#       Following output of the document, the text interpreter can then enter
#       interactive mode.  This allows the user to enter Forth operations via
#       the user interface following which the input is interpreted by the text
#       interpreter.  This allows manual inspection of the results of the
#       interpretation phase and testing of the host name space content.  Interactive
#       Mode is enabled via the implementation specific command-line interface.
#
#  Targeting the Cross-Compiler Framework
#  --------- --- -------------- ---------
#
#  Each of the primary classes in the framework requires a number of methods to be
#  supplied by an implementation targeting a specific processor or system.  The
#  various methods fall into three broad categories corresponding to the primary roles
#  of the main classes:
#
#     - Input management, interaction with compilation mode, cross-compilation
#       and the interactive phase;
#     - Cross-compiler generation supplies methods to class Target and Frame objects;
#       and
#     - Output management supplies methods to class DocumentTree.
#
#  By design, no default handling of these methods is supplied.  This ensures that
#  a new target implementer must make conscious decisions about what each method
#  should do.  The letter 'R' indicates the method is required.  The letter 'O'
#  indicates the word is optional.
#
#  Forth subclass methods initializing the target implementation:
#
#    R register_builtin   Allows implementation specific handling of builtins
#    
#  Forth subclass methods managing file input:
#
#    R include        Called by word INCLUDE to locate and access a file
#    O include_module Uses the Python module system to locate a file
#    O include_path   Locates a file by means of a search path.
#
#  Forth subclass methods related to Forth interpretion mode:
#
#    R init_parser    returns a callable that parses text input into Word objects.
#                     See the information below on requirements for replacing the
#                     default parser.
#    O memory_fetch   Retrieves a value from "memory"
#    O memory_store   Place a vlue into "memory"
#    O recognize_comment  Identifies and ignores in-line comments.  Called by word (
#    O recognize_line_comment  Identifies and ignores line comments.  Called by word \
#    R recognize_string   Identifies and returns the string following some words like
#                     " and ."
#
#  Forth subclass methods related to Forth compilation mode.  Compilation mode
#  creates Frame objects or its subclass.
#
#    R colon_begin     Starts a colon thread word definition
#    R colon_end       Ends a colon thread word definition
#    R create_inline   Returns an Inline object associated with multi element compiled
#                      words.
#    R interrupt_begin Starts an interrupt thread word
#    R interrupt_end   Ends an interrupt thread word
#    R native_begin    Starts a native word definition
#    R native_end      Ends a native word definition
#
#  Forth subclass methods related to cross-compilation:
#
#    R cross_compiler  Returns the implementation specific Target subclass object.
#    R interpret_cross_compile  Provides the interpretation semantics of the word
#                      CROSS-COMPILE.
#    R track_compiled  Remembers that a Frame has been cross-compiled.
#
#  Forth subclass methods related to output creation:
#
#    R document       returns the implementation specific DocumentTree subclass
#    R render          Creates the output resulting from cross-compilation using
#                      the implementation supplied DocumentTree subclass.
#
#  In addition to the preceding methods, the Forth subclass may provide additional
#  builtin words by using the word and immediate decorators to identify additional
#  methods as builtin words.  The semantics of word supplied by the framework may
#  also be altered by redefining the builtin word methods or using the same word
#  name with an other method.
#
#  The Target object defines the interface between the Forth text interpreter, the
#  subclass of the Forth object, and actions required during cross-compilation.
#  Cross-compilation processes individual Frame objects into output statements.
#  Output required by a Frame object is created by methods supplied by a subclass
#  of Frame and Inline.  Detailed compilation of Forth threads are supplied by the
#  subclass of Target.
#
#  Frame object methods required for cross-compilation.  Each subclass of Frame
#  requires its own method.  If a particulater method is not required by a specific
#  frame it can be defined used the pass statement.
#
#    R enter          Creates preamble output for the frame
#    R cross-compile  Creates the Frame's body.
#    R exit           Creates the postamble output for the frame.
#    R finalize       Performs any book-keeping operations required by the target.
#
#  Inline objects require one method from an Inline subclass:
#
#    R cross-compile  Creates the ouput associated with a specific Inline object
#                     used in a Frame during cross-compilation.

#  Cross compilation of a thread occurs through the supplied methods of the Target
#  subclass.
#
#    R compile_branch     Cross-compiles an unconditional branch in the thread.
#    R compile_branch_if_false  Cross-compiles a conditional branch in the thread.
#    R compile_builtin    Cross-compiles a builtin into a thread
#    R compile_remember   Remember that a referenced word needs compilation.
#    R compile_value      Cross-compiles a value into a thread.
#    R compile_word       Cross-compiles a referenced word into a thread.
#    R create_interrupt   Returns an Interrupt Frame object for word INTERRUPT
#    R create_native      Returns a Native Frame object for word CODE
#    R create_word        Returns a Frame object for word :
#    R cross_compile_missing   Called by word CROSS-COMPILE-MISSING to cross-compile
#                         all referenced frames not yet compiled.
#    R cross_compile_variables  Called by word CROSS-COMPILE-VARIABLES to 
#                         cross-compile variables.
#    R init_model         Validates the threading model used during cross-compilation.
#                         The threading model will influence what is generated
#                         during cross-compilation.
#
#  The Target subclass may also create Frame subclasses not used by the framework
#  itself.  The Forth subclass will need to provide builtins associated with these
#  words.
# 
#
#  Replacing the Default Parser
#  --------- --- ------- ------
#
#  The default parser 

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
#          Default is False (meaning the word is recognized by the text interpreter)
#   io     Specifies if the word can not be compiled, meaning only text interpreter
#          semantics is supported.  Defaults is False.
def word(name, co=False, io=False):
    def decorate_word(function):
        function.forth_name = name.lower()  # word name in lower case
        function.forth_co = co              # whether word is compile-only
        function.forth_io = io              # Whether word can not be compiled
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

    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)

  #
  # Document subclass supplied method
  #
 
    # Returns a string written out as the chapter header.  Return None if chapter
    # heading is not created.
    # Method Argument:
    #   chapter  The chapter name being rendered.
    def chapter_header(self, chapter):
        raise NotImplementedError(self._nie("chapter_header()"))

  #
  # Document methods that may be overriden
  #

    # Collate the chapter and section names by the ASCII collating sequence
    # Method Argument:
    #   names   A list of (name, value) tuples
    # Returns a
    #   The tuples placed in the desired collating sequence order.
    def collate(self, names=[]):
        return sorted(names)

  #
  # Document handler methods
  #

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
        #print("doctree.write() - text: %r" % text)
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
    # and within each chapter, sections sorted by name.  The output text is typically
    # an assembly source file targeted to the cross-compiler's tool chain.
    # Method argument:
    #   output   An object that supports the write() method.  Typically a text output
    #            file object.  Required.
    #   newline  Specifies how a universal newline, \\n, is to be handled.  Specify
    #            None to disable universal newline handling.  Defaults to a real 
    #            universal newline.
    #   tab      Specifies how a tab, \\t, is to be handled. Specify None to disable
    #            tab handling.  Defaults to a real tab.
    #   snewline Specifies how a universal newline in a string, \n, will be handled.
    #            Specify None to disable real universal newline handling.  Defautls
    #            to None.
    #   stab     Specifies how a tab within a string is to be handled.  Specify
    #            None to disable tab handling within a string.  Defaults to None
    # A two character universal newline or tab is encountered in file input.  Real
    # tabs or universal newlines are encountered when the cross-compiler inserts
    # text output directly to the document.
    #
    # There are no real differences in Python 3 between a str object and a unicode
    # object as in Python 2.  Unicode encoding is automatically handled by the file
    # input and output processing.
    #
    # Due to the manner in which strings are handled by the default parser, it is
    # impossible to place a space at the beginning of a string.  When using the
    # default parser, this limitation is addressed by inserting a tab at the beginning
    # of the string.  The arguments to this method allow the initial tab to be
    # replaced with one or more spaces which is the norm for assembler output lacking
    # a statement label.  Other parsers may not have this limitation.
    def render(self, output, newline="\n", tab="\t", snewline=None, stab=None):
        for chapter_name, sections in self.collate(self.chapters.items()):
            heder_not_yet_done = True
            for name, text in self.collate(sections.items()):
                if text and heder_not_yet_done:
                    header=self.chapter_header(chapter_name)
                    if header is not None:
                        output.write(header)
                    heder_not_yet_done = False
                otext=''.join(text)
                # Handle line feeds and tabs in cross-compiled output
                if newline:
                    otext=otext.replace("\\n",newline)
                if tab:
                    otext=otext.replace("\\t",tab)
                if snewline:
                    otext=otext.replace("\n",snewline)
                if stab:
                    otext=otext.replace("\t",stab)
                # Output text to the file
                output.write(otext)


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

    # Default parser
    @staticmethod
    def default_parser(string, name, include_newline=True):
        if not isinstance(string, str):
            raise ValueError("default parser 'string' requires a string: %s" \
                % string)
        for n, line in enumerate(string.splitlines()):
            for word in Forth.word_parser(line):
                yield Word(word, name, n+1, line)
            if include_newline:
                yield Word('\n', name, n+1, line)

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
                clso.interpret_sequence(words, filename="<stdin>", parser=clso.parser)
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
        prsr = parser or Forth.default_parser

        if fileobj is None:
            fileobj = open(filename, 'rt')
        filedata=fileobj.read()
        fileoobj.close()

        for word in prsr(filedata, filename, include_newline=include_newline):
            yield word

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
        prsr = parser or Forth.default_parser
        for word in prsr(data, name, include_newline=include_newline):
            yield word

    # Initializes the Forth interpreter
    # Method arguments:
    #   use_ram    Specifies the initial setting for memory type targets.  To 
    #              target ROM, specify False.  To target RAM, specify True.
    #              Defaults to False (or ROM).  The target compiler determines how
    #              the two settings are actually used to target the different memory
    #              types.
    #   logger     Logging ID.  Defaults to "xforth"
    def __init__(self, use_ram=False, logger="xforth"):
        super().__init__()
        self.clear()       # Initialize the interpreter data stack
        self.logger = logging.getLogger(logger)  # Python logger.

        # Interpreter initialization. See init() method:
        # The parser used to recognize words in a line of text
        self.parser=None             # Returned by init_parser() subclass method
        self.compiler=None           # Returned by cross_compiler() subclass method
        self.doctree=None            # Returned by document() subclass method

        # Interpreter execution state:
        # current list of input Word objects being interpreted
        self._iterator = None        # Set by interpret() method from its argument
        # Current Frame object being executed or compiled
        self._frame_iterator = None

        # Define the builtin host specific name space of decorated Python methods
        self.builtins = {}
        self.init_builtins()

        # Define the threaded word name space (used on both host and target)
        # This dictionary maps a words name to its internal representation:
        #   - integers define CONSTANT definitions
        #   - Frame objects define : (colon) words
        #   - InterruptFrame objects define INTERRUPT words
        self.namespace = {}
        # the init() method starts word creation by interpreting forth_words.py
        # definitions.

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

        # Output document tree shared with the cross-compiler. Returned by subclass
        # supplied method document() when called by the init() method.
        self.doctree = None

        # Attribute supplied for search-order management if desired.
        self._active=None

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

    # Returns the NotImplementedError exception message
    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)
            
    # Returns the ForthError message when interpretation semantics are not defined
    def _nis(self,word):
        return "interpretation semantics not defined for word %s" % word

    #
    # The following methods must be supplied by a subclass of this class
    # See msp430.py for an example of their usage.
    #

    # Required: Initiates a colon word definition
    # Method argument:
    #   name    Name of the word being defined
    def colon_begin(self, name):
        raise NotImplementedError(self._nie("colon_begin()"))
        
    # Required: Terminates a colon word definition
    def colon_end(self):
        raise NotImplementedError(self._nie("colon_end()"))

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

    # Required: Returns the implementation's DocumentTree subclass
    def document(self):
        raise NotImplementedError(self._nie("document()"))

    # Required: Looks-up a word in the interpreter namespace sequence
    def look_up(self, word):
        raise NotImplementedError(self._nie("look_up()"))

    # Required: This method locates, accesses and interprets the included file.
    def include(self, name):
        raise NotImplementedError(self._nie("include()"))

    # Optional: This method locates and reads the named resource from a package.  It
    # returns a binary string if located.  If the resource is not found it returns
    # None.  A subclass wanting to read forth source files as if they were a Python
    # module must provide this method
    def include_module(self, name):
        raise NotImplementedError(self._nie("include_module()"))

    # Optional: This method locates the file in the include search path by returning
    # the file's path.  If not found it returns None.  A subclass wishing to support
    # included files from a search path must provide this method.  It is the
    # the subclass responsibility to establish the directory search order and use
    # it to locate included source files.
    def include_path(self, name):
        raise NotImplementedError(self._nie("include_path()"))

    # Required: Supplied the interpreter text parser.
    # The default is Forth.word_parser() staticmathe and should be returned if a 
    # replacement parser is not available.
    # Returns: A generator that parses the words in a line of text.
    def init_parser(self, *args, **kwds):
        raise NotImplementedError(self._nie("init_parser()"))

    # Required: Provides interpretation semantics for word CROSS-COMPILE.  Cross-
    # compilation can be immediate or deferred.  How deferred cross-compiled words
    # are managed is implementation specific.
    # Method Argument:
    #   word   Word name of frame to be cross-compiled
    def interpret_cross_compile(self, word):
        raise NotImplementedError(self._nie("interpret_cross_compile()"))

    # Required: Initiates an interupt thread word definition
    # Method argument:
    #   name    Name of the word being defined
    def interrupt_begin(self, name, vector):
        raise NotImplementedError(self._nie("interrupt_begin()"))
        
    # Required: Terminates an interrupt thread definition
    def interrupt_end(self):
        raise NotImplementedError(self._nie("interrupt_end()"))

    # Required: Allocate space in memory.  See word ALLOT
    def memory_allot(self, size):
        raise NotImplementedError(self._nie("memory_allot()"))

    # Obtional: Retrieve a memory cell's content.
    # "Memory" as defined by the implementation is implied when word @ encounters
    # an integer on the stack instead of a Variable object.
    # Method Argument:
    #   address   An implementation understood "memory" location 
    def memory_fetch(self, address):
        raise NotImplementedError(self._nie("memory_fetch()"))

    # Optional: Set a memory cell's content.
    # "Memory" as defined by the implementation is implied when word ! encounters
    # an integer on the stack instead of a Variable object.
    # Method Argument:
    #   address   An implementation understood "memory" location
    #   value     The "value" stored at the location.
    def memory_store(self, address, value):
        raise NotImplementedError(self._nie("memory_store()"))

    # Required: Initiates a native word definition
    # Method argument:
    #   name    Name of the word being defined
    def native_begin(self, name):
        raise NotImplementedError(self._nie("native_begin()"))
        
    # Required: Terminates a native word definition
    def native_end(self):
        raise NotImplementedError(self._nie("native_end()"))

    # This method is used by the text intepreter to recognize and ignore in-line
    # comments.  In-line comments begin with the word ( and end with the word ) .
    # If in-line comments are inherently recognized and ignored by the supplied parser
    # this method is not required.
    # Returns: None
    def recognize_comment(self):
        raise NotImplementedError(self._nie("recognize_comment()"))

    # This method is used by the text intepreter to recognize and ignore line
    # comments.  Line comments begin with the word \ and end with the line
    # termination sequence, a universal newline.  Optional if the parser inherently
    # recognizes line comments.  Required by the default parser.
    # Returns: None
    def recognize_line_comment(self):
        raise NotImplementedError(self._nie("recognize_line_comment()"))

    # This method used by the text interpreter extracts a string from the input
    # stream.  This method is influenced by the text parser supplied by the
    # target implementation.  Used by builtins that are followed by a string,
    # for example builtin ."
    # Returns:
    #   the recognized string from the input text.
    def recognize_string(self):
        raise NotImplementedError(self._nie("recognize_string()"))

    # Required: Generate cross-compiled output
    # Method Argument:
    #   out   The output file object or codec used to write output file
    def render(self, out):
        raise NotImplementedError(self._nie("render()"))
 
    # Required: Track a word that is compiled
    # Method Argument:
    #   word   The word that is compiled and being tracked
    def track_compiled(self, word):
        raise NotImplementedError(self._nie("track_compiled()"))

  #
  # The following methods may be overriden by a subclass to alter or enhance these
  # default behaviors
  #

    # Enter text interpreter compile mode
    # Method Arguments:
    #   frame    The Frame object whose compilation is starting
    #   so       New search order list.  Defaults to []
    def compile_mode_begin(self, frame, so=[]):
        self._active=so
        self.frame=frame
        self.compiling = True

    # Ends text interpreter compile mode and returns to interpretation mode
    # Method Arguments:
    #   frame     The Frame object whose compilation is complete
    #   namesapce The namespace dictionary to which it is added
    #   so        Search order following compiled frame.
    def compile_mode_end(self, frame, namespace, so=[]):
        frame.finalize(self)                  # Finalize the frame
        namespace[frame.name.lower()]=frame   # Add it to the its namespace
        self.frame=None                       # Remove it from its build place
        self.compiling=False                  # Return to text interpretation
        self._active=so                       # Set new search order

    # Identifies whether a callable is interpretable by the text interpreter or not.
    # Returns:
    #   True   If interpretation semantics are defined for the frame or builtin
    #   False  If interpretation semantics are not defined for the frame or builtin.
    # If interpretation semantics are assumed to be defined for all words.
    # This method recognizes co=True builtins as not interpetable.  All frames are
    # considered interpretable.
    def interpretable(self, element):
        if self.isbuiltin(element) and element.forth_co:
            return False
        return True

    # This method looks up host Forth words
    def look_up(self, word):
        """Find the word in one of the name spaces for the host and return the value"""
        # target words are included w/ least priority. they must be available
        # so that compiling words on the host works
        try:
            return self.look_up_word(word, [self.namespace, self.builtins])
        except KeyError:
            raise KeyError('%r not in any namespace (host)' % (word,)) from None

    # This method looks up target words
    def look_up_target(self, word):
        """Find the word in one of the namespaces for the target and return the value"""
        # builtin namespace is not searched as it only includes words
        # implemented in python. target name space has priority over normal
        # space.
        try:
            return self.look_up_word(word, [self.target_namespace, self.namespace])
        except KeyError:
            raise KeyError('%r not in any namespace (target)' % (word,)) from None

    # This method registers a builtin word.  If the implementation expects to
    # use the interpreter builtin dictionary, the override should call this
    # superclass method.
    # Method Arguments:
    #   function   The decorated method implementing the builtin word.
    def register_builtin(self,function):
        self.builtins[function.forth_name] = function

    def show(self, word, indent=""):
        string="%sSHOW %r\n" % (indent, word)
        local_indent="%s    " % indent
        try:
            value = self.look_up(word)
        except KeyError:
            return "%s%s" % (string, self.show_undefined(word, indent=local_indent))
        else:
            if isinstance(value,int):
                string="%s%s" \
                    % (string, self.show_integer(value, indent=local_indent))
            elif isinstance(value,Frame):
                string="%s%s" \
                    % (string, self.show_frame(value, indent=local_indent))
            elif self.isbuiltin(value):
                string="%s%s" \
                    % (string,self.show_builtin(value, indent=local_indent))
            else:
                string="%s%s" \
                    % (string, self.show_unrecognized(value, indent=local_indent))
        return string

    def show_builtin(self, builtin, indent=""):
        return "%svalue -> %r\n" % (indent, builtin)

    def show_frame(self, frame, indent=""):
        string=  "%svalue -> %r\n" % (indent, frame)
        string="%s%scontents -> \n" % (string, indent)
        local_indent="%s    " % indent
        for item in frame:
            string="%s%s%r\n" % (string,local_indent,item)
        return string

    def show_integer(self, integer, indent=""):
        return "%svalue -> %r\n" % (indent, integer)

    def show_undefined(self, undefined, indent=""):
        return "%svalue -> <undefined>\n" % indent

    def show_unrecognized(self, unrecognized, indent=""):
        return "%svalue -> %r\n" % (indent, unrecognized)

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
        ndx=0    # cell being compiled 

        try:
            while True:  
                # Fetch the thread cell being cross-compiled
                entry = next()

                if callable(entry):
                    if self.isbuiltin(entry,name="$BRANCH"):
                        # branch needs special case as offset needs to be recalculated
                        offset = next()
                        ndx+=1
                        self.compiler.compile_branch(selt, offset, ndx=ndx)
                    elif self.isbuiltin(entry,name="$BRANCH0"):
                        # branch needs special case as offset needs to be recalculated
                        offset = next()
                        ndx+=1
                        self.compiler.compile_branch_if_false(self, offset, ndx=ndx)
                    elif self.isbuiltin(entry):
                        # all other built-ins just take the name of the function
                        self.compiler.compile_builtin(forth, entry, ndx=ndx)
                    elif isinstance(entry, Frame):
                        self.compiler.compile_word(forth, entry, ndx=ndx)
                    else:
                        raise ValueError('Cross compilation undefined for %r' % entry)
                else:
                    if isinstance(entry, Inline):
                        self.entry.cross_compile(self, self.compiler, self.doctree)
                    else:
                        self.compiler.compile_value( self, entry, ndx=ndx)
                ndx+=1
        except StopIteration:
            pass

  #
  # Interpreter Methods
  #

    # Create a Forth interrupt handler
    # Warning: the returned object from the cross-compiler is not validated
    def create_interrupt(self, name, vector):
        return self.compiler.create_interrupt(self, name, vector)

    # Create a native code word for the target
    # Warning: the returned object from the cross-compiler is not validated
    def create_native(self, name, isword=False):
        return self.compiler.create_native(self, name, isword=isword)

    # Create's a word defintion frame by calling the target compiler
    # Warning: the returned object from the cross-compiler is not validated
    def create_word(self, name):
        return self.compiler.create_word(self, name)

    # This method provides default in-line comment recognition.  In-line comments
    # start with the word ( and end with the word ) .
    #
    # The subclass provided recognize_comment() method should call this method
    # if the default parser is in use.
    # Returns: None
    def default_comment_recognizer(self):
        while True:
            word = self.next_word()
            if ')' in word:
                break
        if not word.endswith(')'):
            raise ValueError('limitation, comment end ")" followed by data: %r' \
                % (word,))

    # This method provides the default line-comment recognizer.  Line comments start
    # with the back-slash word \ and continue to the end of the line.
    #
    # The subclass provided recognize_line_comment() method should call this method
    # if the default parser is in use.
    # Returns: None
    def default_line_comment_recognizer(self):
        while True:
            word = self.next_word()
            if '\n' in word:
                break
        if not word.endswith('\n'):
            raise ValueError(\
                'limitation, line comment end "\\n" followed by data: %r' % (word,))

    # This is the string recognizer that should be used with the default parser.
    # The subclass supplied recognize_string() method should call this method
    # if the default parser is in use and return the results of this method.
    # 
    # This method read individual strings until it encounters one that ends with
    # a double-quote.  It then joins each string with an intervening space.  The
    # effect of the default parser operation and this method is that spaces following
    # the word that recognizes strings are removed and and extra spaces between
    # non-space portions of the string are reduced to a single space.
    #
    # For example:
    #   source    ."    this as   an example"
    #   returned: 'this is an example'
    def default_string_recognizer(self):
        words = []
        while True:
            word = self.next_word()
            if word.endswith('"'):
                # emulate character wise reading
                if word != '"':
                    words.append(word[:-1])
                break
            words.append(word)
        text = ' '.join(words)
        return text

    # Initialize the interpreter by 
    #   1. establishing the text parser 
    #   2. the Target cross-compiler and
    #   3. compiling core words (from forth_words.py)
    # Method Arguments
    #   chapter   Specify the chapter into which core words will be cross-compiled
    #             Defaults to None (which implies the ' DEFAULT ' chapter is used).
    #   debug     Causes the core and builtin words to be listed at initialization
    #             end.
    def init(self,chapter=None,debug=False):
        # load core language definitions from forth_words.py
        name=self.__class__.__name__
        self.logger.info('%s.init() processing' % name)
        self.parser=self.init_parser()
        
        error=False
        # Initialize the document handler
        doc=self.document()
        if isinstance(doc,DocumentTree):
            self.doctree=doc
        else:
            msg="document handler is not a subclass of DocumentTree: %s" % doc
            self.logger.error(msg)
            error=True

        # Initialize cross compiler
        compiler=self.cross_compiler()
        if isinstance(compiler,Target):
            self.compiler=compiler
            # Validate requested threading model and allow compiler to turn on 
            # interpreter assists
            if not self.compiler.init_model(self):
                msg="%s compiler does not support requested threading " \
                    "model: %s" % (self.compiler.__class__.__name__,self.threading)
                self.logger.error(msg)
                error=True
        else:
            msg="cross-compiler not a subclass of Target: %s" % compiler
            self.logger.error(msg)
            error=True

        if error:
            self.logger.error("%s.init() failed" % name)
            sys.exit(1)

        # Define foundational word definitions shared by the host and target
        # environments.
        if chapter:
            self.doctree.chapter(chapter)
        data=definitions
        self.interpret(\
            Forth.words_in_string(\
                data, name='init()',include_newline=True,parser=self.parser))
        if debug:
            self.word_LIST(None)

        # Interpreter initialization done.
        self.logger.info('%s.init() done' % name)

    # Initialize builtin word from decorated interpreter methods
    def init_builtins(self):
        for name in dir(self):
            function = getattr(self, name)
            if self.isbuiltin(function):
                # This method may be overridden to add implementation specific
                # functionality, and called via the super() class to implement
                # the registration in the builtins attribute.
                self.register_builtin(function)

    def instruction_cross_compile(self, stack, word=None):
        """\
        Cross compile word. This function can be called directly (w/ word
        parameter) or be part of a Frame.
        """
        if word is None:
            word = self._frame_iterator.next()
        # when interpreting, execute the actual functionality

        # get the frame and compile it - prefer target_namespace
        try:
            item = self.look_up_target(word)
            self.logger.debug("found target for cross-compiling %s: %s" \
                % (word,item))
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
        # track what is done
        self.track_compiled(word)

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
                word = self.next_word()
                self.logger.debug("interpreting: %s" % word)
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
                filename, lineno, column, offset, text) from None
            # XXX consider showing the full traceback of the original exception
        finally:
            # restore state
            self._iterator = old_iterator

    def interpret_sequence(self, sequence, filename=None, parser=None):
        """interpret a sequence of words"""
        if parser:
            iterable=parser(sequence, filename, include_newline=True)
        else:
            iterable=iter(\
                Forth.default_parser(sequence, filename, include_newline=True))
        self.interpret(iterable)

    # Text interpreter subroutine to compile or execute a word
    def interpret_word(self, word):
        """Depending on mode a word is executed or compiled"""
        # newlines are in the steam to support \ comments, they are otherwise ignored
        if word == '\n':
            return
        try:
            element = self.look_up(word)
            self.logger.debug("found word %s: %r" % (word,element))
        except KeyError:
            pass
        else:
            #if self.compiling and not hasattr(element, 'forth_immediate'):
            if self.compiling and not self.isimmediate(element):
                self.logger.debug("compiling element: %r" % element)
                if callable(element):
                    self.frame.cell(element, self)
                else:
                    self.frame.cell(self.look_up("$LIT"),self)
                    self.frame.cell(element, self)
                return
            else:
                # interpreting or immediate word while compiling
                self.logger.debug("interpreting element: %r" % element)
                if callable(element):
                    if not self.interpretable(element):
                        raise ValueError("intepretation semantics not defined for "
                            "word: %s" % word)
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
                    % (word,), filename, lineno, column, offset, text) from None
        if self.compiling:
            self.frame.cell(self.look_up("$LIT"), self)
            self.frame.cell(self.create_inline("$LIT",number), self)
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

    # Returns whether a method or frame is immediate
    # Method Argument:
    #   item   The object that is potentially immediate
    # Returns:
    #   True if word is immediate
    #   False if word is not immediate
    def isimmediate(self, item):
        return hasattr(item, "forth_immediate")

    # Foundational name space search method.
    # Method Arguements:
    #   name        The Word object or name as a string being accessed
    #   namespaces  A list of name space dictionaries being searched 
    # Returns:
    #   The Frame object or subclass associated with the name
    # Excpetions:
    #   KeyError if word is not located
    def look_up_word(self, name, namespaces=None):
        """Find the word in one of the name spaces for the host and return the value"""
        lcword = name.lower() # case insensitive
        so=namespaces or self._active
        for namespace in so:
            try:
                return namespace[lcword]
            except KeyError:
                pass
        raise KeyError()

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

    @word("$SSTR",co=True)
    def instruction_counted_string(self, stack):
        inline=stack._frame_interator.next()
        stack.push(inline)
        stack.push(len(inline.value))

    @word('$LIT',co=True)
    def instruction_literal(self, stack):
        """Low level instruction to get a literal and push it on the stack."""
        inline=stack._frame_iterator.next()
        if isinstance(inline, Variable):
            stack.push(inline)
        else:
            stack.push(inline.value)

    @word("$TEXT",co=True)
    def output_text(self, stack):
        text = stack._frame_iterator.next()
        # text is expected to be an instance of Inline
        otext=text.value
        self.doctree.write(otext) 

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

    # ( location -- location's value)
    @word('@')
    def word_at(self, stack):
        reference = stack.pop()
        if isinstance(reference, Variable):
            stack.push(reference.get())
        elif isinstance(reference, int):
            stack.push(self.memory_fetch(reference))
        else:
            raise ValueError(\
                'limited support for @: no compatible object on stack: %r' \
                    % (reference,))

    @immediate
    @word(':')
    def word_colon(self, stack):
        """Begin defining a function. Example: ``: ADD-ONE 1 + ;``"""
        name = self.next_word()
        self.colon_begin(name)

    @word(',')
    def word_comma(self, stack):
        """Append value from stack to current definition."""
        if self.frame is None: raise ValueError('not in colon definition')
        value = stack.pop()
        if isinstance(value, Variable):
            # XXX special case for calculations with HERE
            value = value.info
        self.frame.cell(value, self)

    @immediate
    @word('(')
    def word_comment_start(self, stack):
        """\
        Start a comment and read to its end (``)``).

        There is a special comment ``( > text... )`` which is recognized by the
        MSP430 documentation tool. All these type of comments are collected and
        assigned to the next declaration.
        """
        self.recognize_comment()

    @immediate
    @word(']')
    def word_compile(self, stack):
        """Change to compilation mode."""
        self.compiling = True

    @immediate
    @word('."')
    def word_copy_words(self, stack):
        """Output a string."""
        text=self.recognize_string()
        if self.compiling:
            self.frame.cell(self.look_up("$TEXT"), self)
            self.frame.cell(self.create_inline("$TEXT",text), self)
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
        self.recognize_line_comment()

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
        self.colon_end()

    # ( value reference -- )
    # reference now set to value
    @word('!')
    def word_store(self, stack):
        reference = stack.pop()
        value = stack.pop()
        if isinstance(reference, Variable):
            if isinstance(value, Variable):
                reference.set(value.info)
            else:
                reference.set(value)
        elif isinstance(reference, int):
            self.memory_store(reference, value)
        else:
            raise ValueError(\
                'limited support for !: no compatible object on stack %r' \
                    % (reference,))

    @immediate
    @word('C"',co=True)
    def word_string_literal(self, stack):
        """Put a string on the stack."""
        text=self.recognize_string()
        if self.compiling:
            self.frame.cell(self.look_up("$LIT"), self)
            self.frame.cell(self.create_inline('C"', text), self)
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
        self.frame.cell(self.look_up("$LIT"), self)
        self.frame.cell(self.create_inline("'", word_frame), self)

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
        self.memory_allot(count)

    @word("AND")
    def bitand(self, stack):
        x, y = stack.pop2()
        stack.push(y & x)

    @immediate
    @word('C"',co=True)
    def word_string_literal(self, stack):
        """Put a string on the stack."""
        text=self.recognize_string()
        if self.compiling:
            self.frame.cell(self.look_up("$LIT"), self)
            self.frame.cell(self.create_inline('"', text), self)
        else:
            raise ValueError(self._nis('C"'))

    @immediate
    @word('CHAR')
    def word_char(self, stack):
        """Push ASCII code of next character."""
        name = stack.next_word()
        try:
            value=int(name,0)
        except ValueError:
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
            self.frame.cell(self.look_up("$LIT"), self)
            self.frame.cell(self.create_inline("[CHAR]", value), self)
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
        self.native_begin(name)

    @immediate
    @word('[COMPILE]')
    def word_BcompileB(self, stack):
        """\
        Get next word, look it up and add it to the current frame (not
        executing immediate functions).
        """
        if self.frame is None: raise ValueError('not in colon definition')
        item = self.look_up(stack.next_word())
        self.frame.cell(item, self)

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
        vframe=self.compiler.create_word( self, 'cre'+name)
        vframe.use_ram = self.use_ram
        self.variables[name] = vframe
        self.frame = vframe

        # create a function that pushes the variables address
        frame = self.compiler.create_word( self, name)
        frame.chapter = self.doctree.chapter_name
        frame.cell(self.look_up("$LIT"), self)
        frame.cell(self.create_inline("CREATE", vframe, info=0), self)
        frame.finalize(self)
        self.namespace[name.lower()] = frame
        # XXX could also do a native impl with "push #adr;NEXT"

    @immediate
    @word('CROSS-COMPILE')
    def word_cross_compile(self, stack):
        """Output cross compiled version of function. Example:: ``CROSS-COMPILE DROP``"""
        word = stack.next_word()
        if self.compiling:
            # when compiling add call to self and the word to the Frame
            self.frame.cell(self.look_up("CROSS-COMPILE"), self)
            self.frame.cell(word, self)
        else:
            # in interpretation mode, cross-compile it now
            self.interpret_cross_compile(word)

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
            self.frame.cell(self.look_up("DEPENDS-ON"), self)
            self.frame.cell(self.create_inline("DEPENDS-ON", word), self)
        else:
            word = stack._frame_iterator.next()
            self.compiler.compile_remember(word.value)

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
        self.native_end()

    @immediate
    @word('END-INTERRUPT')
    def word_end_interrupt(self, stack):
        """End definition of a native code function. See INTERRUPT_ for example."""
        if self.frame is None: raise ValueError('not in colon definition')
        self.interrupt_end()

    @word("FLOAT")
    def word_FLOAT(self, stack):
        """Convert TOS to a floating point number."""
        stack.push(float(self.pop()))

    @word('HERE')
    def word_here(self, stack):
        """Put position [within frame] on stack"""
        stack.push(Variable(self.frame, info=len(self.frame)))

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
        self.interrupt_begin(name, vector)

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
        self.frame.cell(self.look_up("$BRANCH0"), self)
        stack.push(len(self.frame))
        # This needs fixing!!!
        self.frame.cell(self.create_inline("$BRANCH0", 0), self)

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

    @word('S"',co=True)
    def word_SSTRING(self, stack):
        text=self.recognize_string()
        if self.compiling:
            self.frame.cell(self.look_up("$SSTR"), self)
            self.frame.cell(self.create_inline('S"', text), self)
        else:
            raise ValueError(self._nis('S"'))

    @word('SHOW')
    def word_SHOW(self, stack):
        """Show internals of given word. Used to debug."""
        name = stack.next_word()
        sys.stderr.write(self.show(name))

    @word("SWAP")
    def swap(self, stack):
        """Exchange the two topmost elements on the stack."""
        stack[-1], stack[-2] = stack[-2], stack[-1]

    @immediate
    @word('TO')
    def word_to(self, stack):
        """Write to a VALUE_. Example: ``123 SOMEVALUE TO``"""
        name = "val" + stack.next_word()
        if self.compiling:
            self.frame.cell(self.look_up("$LIT"), self)
            self.frame.cell(self.create_inline("TO",self.variables[name],info=0), self)
            self.frame.cell(self.look_up('!'), self)
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
        vframe=self.compiler.create_word(self, 'val'+name)
        vframe.cell(value, self)
        vframe.finalize(self)
        self.variables[name] = vframe

        # create a function that pushes the variable's address
        frame = self.compiler.create_word( self, name)
        frame.chapter = self.doctree.chapter_name
        frame.cell(self.look_up("$LIT"), self)
        frame.cell(self.create_inline("VALUE", vframe, info=0), self)
        frame.cell(self.look_up('@'), self)
        frame.finalize(self)
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
        vframe=self.compiler.create_word( self,'var'+name)
        vframe.cell(0, self)
        vframe.finalize(self)
        self.variables[name] = vframe

        # create a function that pushes the variables address
        frame = self.compiler.create_word( self, name)
        # Add subclass interface
        frame.chapter = self.doctree.chapter_name
        frame.cell(self.look_up("$LIT"), self)
        frame.cell(self.create_inline("VARIABLE", vframe, info=0), self)
        frame.finalize(self)
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

# Decorated method wrapper.  To the interpreter, it looks and acts just like a
# decorated method, but is writable allowing additional attributes to be added or
# updated.  
#
# If an implementation requires this object, it is recommended it be subclassed for
# the implementation specific functionality.  The subclass can be instantiated in the
# implementation's override of xforth.register_builtin() method.
class BUILTIN(object):
    def __init__(self, function):
        # Replicate the decorated method's information here
        self.forth_name=self.name=function.forth_name
        self.forth_io=function.forth_io
        self.forth_co=function.forth_co
        self.function=function
        if hasattr(function, "forth_immediate"):
            self.forth_immediate=function.forth_immediate

    # Call the builtin method indirectly through this method
    def __call__(self, stack):
        # Execute the decorated method here
        self.function(stack)

    def __repr__(self):
        return "%s[%s]" % (self.__class__.__name__,self.forth_name)


# Base class for Shared Host and Target word definitions and other definitions
class Frame(list):
    def __init__(self, name):
        super().__init__()
        self.name = name         # Forth word name
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
    
    def _nie(self,method):
        return "%s - %s.%s - subclass must provide %s method" \
            % (this_module,self.__class__.__name__,method,method)


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

    # Finalize this Frame
    def finalize(self, forth):
        raise NotImplementedError(self._nie("finalize()"))

  #
  # This method may be overriden to provide additional functionality
  #
  
    def cell(self, element, forth):
        self.append(element)


# Base class for inline data.  Inline data occupies an element in a Frame but
# are not directly executable.  They must be consumed by the previous Frame element
# when interpreted.  The purpose of the Inline object is to allow the cross-compiler
# to tailor inline data generation.  Python builtin's must also understand the
# Inline object.  The Inline object (a subclass usually) is supplied by the Forth
# subclass method create_inline() method.  The 
class Inline(object):
    def __init__(self, value, info=None):
        self.value=value
        self.info=info

    def __repr__(self):
        if hasattr(self.value, "forth_name"):
            v="%s   %s" % (self.value.forth_name, self.value)
        else:
            v=self.value
        if self.info is not None:
            return '%s[%s][%s]' % (self.__class__.__name__, v, self.info)
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
        super().__init__(name)
        self.vector = vector


# Word or assembler sequence definition
class NativeFrame(Frame):
    def __init__(self,name, chapter=None, section=None, ram=False, isword=False):
        super().__init__(name, \
                         chapter=chapter, section=section, ram=ram, isword=isword)  


# Variable definition used by interpreter.  Not interpreted but may appear in 
# a frame as inline data.  The Variable object is the Python analogue to an
# address, but only within a frame.
class Variable(Inline):
    # typical variable usage: "HERE @". so the variable name would put the
    # address of the variable on the stack. The value of HERE is then also used
    # to write to (e.g. in the implementation of IF/ENDIF. As we do not have
    # linear address space but frames for each dictionary entry that start
    # counting at zero, the value needs to remember the frame it belongs to.

    def __init__(self, frame, info=None):
        super().__init__(frame, info=info)

    def __add__(self, other):
        if isinstance(other, Variable):
            if self.value is not other.value: 
                raise ValueError('Variables point to different frames')
            return self.__class__(self.value, info=(self.info + other.info))
        else:
            return self.__class__(self.value, info=(self.info + other))

    def __sub__(self, other):
        if isinstance(other, Variable):
            if self.value is not other.value:
                raise ValueError('Variables point to different frames')
            return self.__class__(self.value, info=(self.info - other.info))
        else:
            return self.__class__(self.value, info=(self.info - other))

    # Return the value at the frame cell's index
    def get(self):
        try:
            return self.value[self.info]
        except IndexError:
            raise ForthError("index exceeds word %s frame's allocated size (%s): %s" \
                % (self.value.name, len(self.value), self.info)) from None

    # Set a valua at the frame cell's index
    def set(self, value):
        try:
            self.value[self.info] = value
        except IndexError:
            raise ForthError("index exceeds word %s frame's allocated size (%s): %s" \
                % (self.value.name, len(self.value), self.info)) from None

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
    #   ndx      Index of the cell being compiled
    def compile_branch(self, forth, target, ndx=None):
        raise NotImplementedError(self._nie("compile_branch()"))

    # Required: Compile an unconditional branch when False in a thread
    # Method Arguments:
    #   forth    the interpreter object
    #   target   the thread cell index being targeted by this conditional branch
    #   ndx      Index of the cell being compiled
    def compile_branch_if_false(self, forth, target, ndx=None):
        raise NotImplementedError(self._nie("compile_branch_if_false()"))

    # Required: Compile a builtin word referenced in a thread
    # Method Arguments:
    #   forth    the interpreter object
    #   builtin  the interpreter method tagged as a word by the @word decorator
    #   ndx      Index of the cell being compiled
    def compile_builtin(self, forth, builtin, ndx=None):
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
    #   ndx      Index of the cell being compiled
    def compile_value(self, forth, value, ndx=None):
        raise NotImplementedError(self._nie("compile_unrecognized()"))

    # Required: Compile a word into a thread
    # Method Arguments:
    #   forth  the interpreter object
    #   frame  The Frame object of the word being referenced in a thread
    #   ndx      Index of the cell being compiled
    def compile_word(self, forth, frame, ndx=None):
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
    # methods.  It is the responsiblity of the subclass of Forth to provide a
    # threading module to the compiler.
    # 
    # Returns:
    #   True  if model supported by the target compiler or thread model variations
    #         are not supported.
    #   False or None if model not supported.
    def init_model(self, forth):
        raise NotImplementedError(self._nie("init_model()"))


if __name__ == '__main__':
    raise NotImplementedError("module %s only intended for import" % this_module)

