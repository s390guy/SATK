#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Chris Liechti <cliechti@gmx.net>
# All Rights Reserved.
# Simplified BSD License (see LICENSE.txt for full text)

# msp430.py uses the generic framework provided by xforth.py creating a MSP430
# targeting Forth-based cross-compiler.  It is based upon the MSP430 package
# cross-compiler.
#
# The original package can be found at this location:
# https://pypi.python.org/pypi/python-msp430-tools/0.6

# Modifications contributed by Harold Grovesteen under the Simplified BSD license
# Copyright (c) 2014 Harold Grovesteen
# All Right Reserved
# Simplified BSD License (see LICENSE.txt for full text)


# Python imports
import sys
import codecs
import logging

# other imports:
import xforth       # Access the FORTH-based cross-compiler framework.
# Allow the Forth interpreter subclass to add builtin defintions
word=xforth.word
immediate=xforth.immediate

this_module="msp430.py"


#
#  +---------------------------+
#  |                           |
#  |   MSP430 Forth Language   |
#  |      Cross-Compiler       |
#  |         (Example)         |
#  |                           |
#  +---------------------------+
#

# This class extends the cross-compiler framework targeting the MSP430 processor.
#
# Note: additional builtin words can be added to a sub-class by using the decorator
# functions above.  The BYE word is used to illustrate this below.
class MSP430(xforth.Forth):
    def __init__(self):
        super().__init__( use_ram=False)
        # Include file management
        # Include search path
        self.include_path = []        # built by function main() from command line
        # Included files (file include recursion not supported)
        self.included_files = []      # Modified by _include() and init() methods

        # These two sets track words that need compiling
        self.compiled_words = set()      # Track compiled words
        self.not_yet_compiled_words=set()# Track words not yet compiled words

        # Inline object usage.  See create_inline() method
        self.inlines={"$LIT":    InlineNumber,
                      '$TEXT':   InlineText,
                      "'":       InlineFrame,
                      '"':       InlineText,
                      "CREATE":  xforth.Variable,
                      "DEPENDS-ON":InlineText,
                      "VALUE":   xforth.Variable,
                      "VARIABLE":xforth.Variable,
                      "TO":      xforth.Variable,
                      "[CHAR]":  InlineNumber,}

    def colon_begin(self, name):
        self.compile_mode_begin(self.create_word(name))

    def colon_end(self):
        self.compile_mode_end(self.frame, self.namespace)

    def create_inline(self, word, value, info=None):
        try:
            return self.inlines[word](value, info=info)
        except KeyError:
            raise ValueError("inline object not defined for word: %s" % word)

    def cross_compiler(self):
        # self.assist_native_words("ASM-NEXT")     # For illustrative purposes.
        return MSP430_Compiler(self)

    def document(self):
        return MSP430_Document()

    # Include given filename.  The Forth code is directly executed using the
    # parser from init_parser() method.
    def include(self, name):
        # put all data from include in one chapter. remember previous chapter
        # and restore it at the end.
        self.doctree.push_state()
        self.doctree.chapter(name)

        if self.include_path(name):
            self.logger.info('processing include %s' % (name,))
            self.interpret(Forth.words_in_file(path,include_newline=True, \
                parser=self.parser))
            self.logger.info('done include %s' % (name,))
            self.included_files.append(name)

        else:
            data=self.include_module(name)
            if data:
                self.logger.info('processing include %s' % (name,))
                self.interpret(Forth.words_in_string(data, \
                    name='forth/%s' % (name,), include_newline=True, \
                    parser=self.parser))
                self.logger.info('done include %s' % (name,))
                self.included_files.append(name)
            else:
                raise ValueError('file not found: %s' % (name,))

        self.doctree.pop_state() # restore previous chapter and section

    def include_module(self, name):
        data=None
        try:
            data = pkgutil.get_data('msp430.asm', 'forth/%s' % (name,))
        except IOError:
            pass
        return data

    def include_path(self, name):
        if name not in self.included_files:
            for prefix in self.include_path:
                path = os.path.join(prefix, name)
                if os.path.exists(path):
                    return path

    def init_parser(self):
        pass  # Use default word parser Forth.word_parser() static method

    # Perform immeidate cross-compilation
    def interpret_cross_compile(self,  word):
        self.instruction_cross_compile(self, word)

    def interrupt_begin(self, name, vector):
        self.compile_mode_begin(self.create_interrupt(name, vector))

    def interrupt_end(self):
        self.compile_mode_end(self.frame, self.target_namespace)

    # Allocate even number of bytes in current frame
    def memory_allot(self, count):
        if count > 0:
            if count & 1: raise ValueError('odd sizes currently not supported')
            self.frame.extend([0]*(count/2))
        else:
            raise ValueError('negative ALLOT not supported')

    def native_begin(self, name):
        self.compile_mode_begin(self.create_native(name))

    def native_end(self):
        self.compile_mode_end(self.frame, self.target_namespace)

    # Recognize an in-line comment
    def recognize_comment(self):
        self.default_comment_recognizer()

    # Recognize a line comment
    def recognize_line_comment(self):
        self.default_line_comment_recognizer()

    # Recognize a double-quote terminated string.
    def recognize_string(self):
        return self.default_string_recognizer()

    # Output cross-compiled application
    def render(self, out):
        self.doctree.render(out)

    def track_compiled(self, word):
        self.compiled_words.add(word)
        if word in self.not_yet_compiled_words:
            self.not_yet_compiled_words.remove(word)

class MSP430_Compiler(xforth.Target):
    def __init__(self,forth):
        super().__init__(forth)

        self.label_id = 0             # Sequence number for generated assembly labels

        # Used to generate specific assembler labels for compile-only builtins
        self.labels={"$branch":"branch",
                     "$branch0":"branch0",
                     "$lit": "lit",
                     "$text":"__write_text",}

    def compile_branch(self, forth, target, ndx=None):
        self.doctree.write('\t.word %s, %s\n' \
                           % (self.create_asm_label('branch'), target*2))
        self.compile_remember(forth, "$branch")

    def compile_branch_if_false(self, forth, target, ndx=None):
        self.doctree.write('\t.word %s, %s\n' \
                            % (self.create_asm_label('branch0'), target*2))
        self.compiler_remember(forth, "$branch0")

    def compile_builtin(self, forth, builtin, ndx=None):
        name=built.forth_name.upper()
        self.doctree.write('\t.word %s\n' % self.create_asm_label(name))
        self.compile_remember(self, forth, name)

    def compile_remember(self, forth, word):
        """\
        Remember that a word used. This ensures that it is included in the list
        of cross compiled words.
        """
        # track what is not yet done
        word = word.lower()
        if word not in self.compiled_words:
            self.not_yet_compiled_words.add(word)

    def compile_value(self, forth, value, ndx=None):
        self.doctree.write('\t.word %r\n' % (value,))

    def compile_word(self, forth, frame):
        self.doctree.write('\t.word %s\n' \
                            % self.create_asm_label(frame.name))
        self.compile_remember(forth, frame.name)

    def create_interrupt( self, forth, name, vector):
        frame=MSP430_Interrupt(name, vector)
        frame.chapter=forth.current_chapter()
        return frame

    def create_native(self, forth, name):
        frame=MSP430_Native(name)
        frame.chapter=forth.current_chapter()
        return frame

    def create_word(self, forth, name):
        frame=MSP430_Word(name)
        frame.chapter=forth.current_chapter()
        return frame

    def cross_compile_missing(self, forth):
        """\
        Compile all the words that are used by other compiled words but are not
        yet translated. While compiling words, new words can be found which are
        then also compiled.
        """
        while forth.not_yet_compiled_words:
            forth.instruction_cross_compile(forth, \
                word=forth.not_yet_compiled_words.pop())

    def cross_compile_variables(self, forth):
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
        for name, variable in sorted(forth.variables.items()):
            #variable.name
            self.doctree.write(u'%s:  .skip %d \n' % (
                    self.create_asm_label(variable.name),
                    2*len(variable)))
            self.doctree.write('\n')
        self.doctree.pop_state()

    # This method validates support for the requested threading model and optionally
    # enables any interpreter assists required to support it.
    # For MSP430, only the direct threading model is supported and no assists are
    # required.
    def init_model(self, forth):
        return True

    #
    # Methods used by the MSP430 Cross-compiler
    # These methods are not part of the Target superclass interface.
    #

    def create_asm_label(self, forth, name):
        """\
        There are a number of symbols that are not allowed in assembler
        labels, translate to printable strings.
        """
        try:
            return self.labels[name]
        except KeyError:
            pass

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

class MSP430_Document(xforth.DocumentTree):
    def __init__(self):
        super().__init__()
    def chapter_header(self, chapter):
        if chapter_name != ' DEFAULT ':
            separeter='=' * 75
            header='; %s\n' % separater
            header=header+'; == %s\n' % chapter_name
            return header+'; %s\n' % separator
        return None

#
#  +----------------------------------+
#  |                                  |
#  |   MSP430 Cross-Compiler Frames   |
#  |                                  |
#  +----------------------------------+
#

class MSP430_Interrupt(xforth.InterruptFrame):
    def __init__(self, name, vector, chapter=None):
        super().__init__(name, vector, chapter=chapter, ram=False, isword=True)

    def cross_compile(self, forth, doctree):
        """Compilation of interrupt function"""
        # the thread for the interrupt handler
        doctree.write(u'%s:\n' % self.create_asm_label(self.name))
        forth.compile_thread(self)

    def enter(self, forth, doctree):
        doctree.section(self.name)
        doctree.write(u'.text\n.even\n')
        doctree.write(u';%s\n' % ('-'*76))
        doctree.write(u'; compilation of interrupt %s\n' % self.name)
        doctree.write(u';%s\n' % ('-'*76))

        # interrupt entry code
        doctree.write(\
            u'__vector_%s:\n' % (self.vector))
        doctree.write(\
            u'\tsub #4, RTOS     ; prepare to push 2 values on return stack\n')
        doctree.write(\
            u'\tmov IP, 2(RTOS)  ; save IP on return stack\n')
        doctree.write(\
            u'\tmov SP, 0(RTOS)  ; save SP pointer on return stack it points to SR on stack\n')
        doctree.write(\
            u'\tmov #%s, IP      ; Move address of thread of interrupt handler in IP\n'\
            % self.create_asm_label(frame.name))
        doctree.write('\tbr  #%s\n' % self.create_asm_label('DO-INTERRUPT'))

    def exit(self, forth, doctree):
        doctree.write('\t.word %s\n\n' % self.create_asm_label('EXIT-INTERRUPT'))
        self.compile_remember('DO-INTERRUPT')
        self.compile_remember('EXIT-INTERRUPT')

    def finalize(self, forth):
        pass


class MSP430_Native(xforth.NativeFrame):
    def __init__(self,name, chapter=None):
        super().__init__(name, chapter=chapter, ram=False, isword=False)

    def cross_compile(self, forth, doctree):
        """Compilation of native code function"""
        doctree.write(u'%s:\n' % self.create_asm_label(self.name))
        # native code blocks are executed. They are expected to print out
        # assembler code
        self(forth)

    def enter(self, forth, doctree):
        doctree.chapter(self.chapter)
        doctree.section(self.name)
        doctree.write(u'.text\n.even\n')
        doctree.write(u';%s\n' % ('-'*76))
        doctree.write(u'; compilation of native word %s\n' % frame.name)
        doctree.write(u';%s\n' % ('-'*76))

    def exit(self, forth, doctree):
        doctree.write('\n') # get some space between this and next word

    def finalize(self, forth):
        pass


class MSP430_Word(xforth.Frame):
    def __init__(self, name):
        super().__init__(name)

    def cross_compile(self, forth, doctree):
        """\
        Compilation of forth functions. Words referenced by this function are
        remembered and can be output later, either manually with `CROSS-COMPILE`_
        or automatically with `CROSS-COMPILE-MISSING`_.
        """
        doctree.write('\tbr #%s\n' % self.create_asm_label('DOCOL'))
        # Use the interpreter to drive the actual compilation of the thread
        forth.compile_thread(self)

    def enter(self, forth, doctree):
        name=self.name
        doctree.chapter(self.chapter)
        doctree.section(name)
        doctree.write(u'.text\n.even\n')
        doctree.write(u';%s\n' % ('-'*76))
        doctree.write(u'; compilation of word %s\n' % name)
        doctree.write(u';%s\n' % ('-'*76))
        doctree.write(u'%s:\n' % self.create_asm_label(name))

    def exit(self, forth, doctree):
        doctree.write('\t.word %s\n\n' % self.create_asm_label('EXIT'))

    def finalize(self, forth):
        pass

#
#  +---------------------------------------+
#  |                                       |
#  |   MSP430 Cross-Compiler Inline Data   |
#  |                                       |
#  +---------------------------------------+
#

# Used by builtins: '    CREATE   TO   VALUE   VARIABLE
class InlineFrame(xforth.Inline):
    def __init__(self, value, info=None):
        super().__init__(value, info=info)

    def cross_compile(self, forth, compiler, doctree):
        doctree.write('\t.word %s\n' % \
            compiler.create_asm_label(self.value.name),)
        compiler.compile_remember(self.value.name)


# Used by builtins: LIT   [CHAR]
class InlineNumber(xforth.Inline):
    def __init__(self, value, info=None):
        super().__init__(value, info=info)

    def cross_compile(self, forth, compiler, doctree):
        doctree.write('\t.word %-6s ; 0x%04x\n' % (self.value, self.value & 0xffff))


# Use by builtins: "    ."
class InlineText(xforth.Inline):
    def __init__(self, value, info=None):
        super().__init__(value, info=info)

    def cross_compile(self, forth, compiler, doctree):
        label = self.create_label()
        asmlabel=self.create_asm_label(label)
        self.doctree.write('\t.word %s\n' % self.create_asm_label(label))

        # output the text separately
        frame = MPS430_Native(label,)
        # This will not work!
        # The interpreter executes native frames to compile them using ." to
        # output text data.  The simple parser can not handle double quotes around
        # text as originally coded.
        frame.append('." %s .asciiz "%s"\"' \
            % (asmlabel,codecs.escape_encode(self.value)[0],))

        forth.target_namespace[label] = frame
        compiler.compile_remember(label)

#
#  +---------------------------------------+
#  |                                       |
#  |   MSP430 Cross-Compiler Interpreter   |
#  |        Command Line Interface         |
#  |                                       |
#  +---------------------------------------+
#

def main():
    logging.basicConfig(level=logging.ERROR)
    from argparse import ArgumentParser

    parser = ArgumentParser(prog=this_module,usage="""\
%s [options] [FILE...]|-]

If no input files are specified data is read from stdin.""" % this_module)

    parser.add_argument("-o", "--outfile",metavar="FILE",
            help="write outputs to given file")
    parser.add_argument("-v", "--verbose",action="store_true",default=False,
            help="print status messages")
    parser.add_argument("--debug",action="store_true",default=False,
            help="print debug messages")
    parser.add_argument("-i", "--interactive",action="store_true",default=False,
            help="interactive mode is started")
    parser.add_argument("-D", "--define",action = "append",default = [],
            metavar = "SYM[=VALUE]",
            help="define symbol SYM[=VALUE]")
    parser.add_argument("-I", "--include-path",action = "append",default = [],
            metavar = "PATH",
            help="Add directory to the search path list for includes")
    parser.add_argument("source",default=[],metavar="FILE",
        help="input assembler source file path",nargs="*")

    options=parser.parse_args()
    args=options.source

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
        out = sys.stdout

    # XXX make stderr unicode capable
    #sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

    instructions = []
    include_paths = []
    for filename in args:
        if filename == '-':
            if options.verbose:
                sys.stderr.write(u'reading stdin...\n')
            instructions.extend(Forth.words_in_file('<stdin>', \
                fileobj=sys.stdin, include_newline=True))
            include_paths.append('.')
        else:
            if options.verbose:
                sys.stderr.write(u'reading file "%s"...\n'% filename)
            try:
                instructions.extend(Forth.words_in_file(filename, \
                    include_newline=True))
            except IOError as e:
                sys.stderr.write('forth: %s: File not found\n' % (filename,))
                sys.exit(1)
            include_paths.append(os.path.dirname(os.path.abspath(filename)))

    try:
        forth = MSP430()
        # Change this to: forth.init(usefile=True) to use the __init__.forth file
        # By default this method will use forth_words.py to populate the initial
        # Forth word name space.
        forth.init(chapter="__init__",debug=options.debug)
        forth.logger.info("compiler: %s" % forth.compiler.__class__.__name__)
        # default to source directory as include path
        forth.include_path = include_paths
        # extend include search path
        forth.include_path.extend(options.include_path)

        # insert defined symbols
        for definition in options.define:
            if '=' in definition:
                symbol, value = definition.split('=', 1)
            else:
                symbol, value = definition, '1'
            forth.namespace[symbol.lower()] = value # XXX inserted as string only

        #~ forth.doctree.chapter(filename)
        forth.interpret(iter(instructions))
        forth.render(out)
    except xforth.ForthError as e:
        sys.stderr.write(u"%s:%s: %s\n" % (e.filename, e.lineno, e))
        if options.debug and e.text:
            sys.stderr.write(u"%s:%s: input line was: %r\n" % (e.filename, e.lineno, e.text))
        #~ if options.debug: raise
        sys.exit(1)
    except Exception as ex:
        forth.logger.exception(ex)
    # Note: finally gets in the way not used

    # enter interactive loop when desired
    if options.interactive:
        print("Ctrl-C to exit...")
        xforth.Forth.interpreter_loop(clso=forth, debug = options.debug)


if __name__ == '__main__':
    main()
