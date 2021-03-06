#!/usr/bin/python3.3
# Copyright (C) 2013 Harold Grovesteen
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

# This module provides a sample mini language processor using the modules in the
# tools/lang directory of SATK.  See "SATK for s390 - Language Processing Tools" in
# the SATK doc directory for a description of how the modules are used.

# Python imports: None

# SATK imports:
import lang       # Access the language tools' semantic analyzer framework.
import lexer      # Access the language tools' lexical analyzer
import LL1parser  # Access the language tools' syntactical analyzer
import syntax     # Access the AST nodes

class MyLexer(lexer.Lexer):
    def __init__(self,debug=False,tdebug=False):
        self.gdebug=debug
        self.tdebug=tdebug
        super().__init__()

    # Initialize the lexer
    def init(self):
        tdebug=self.tdebug
        self.type(lexer.Type("name",r"[a-zA-Z][a-zA-Z0-9]*",debug=tdebug))
        self.type(lexer.Type("number",r"[0-9]+",debug=tdebug))
        self.type(lexer.Type("operator",r"\+|-|\*|/",debug=tdebug))
        self.type(lexer.Type("ws",r"[ \t\r\f\v]+",ignore=True,debug=tdebug))
        self.type(lexer.Type("comment",r"#[^\n]*",ignore=True,debug=tdebug))
        self.type(lexer.Type("nl",r"(?m)\n+",eol=True,debug=tdebug))
        self.type(lexer.EOSType("eos"))
        self.type(lexer.EmptyType())
        if self.gdebug:
            self.types()
        return self

class MyLanguage(lang.Processor):
    def __init__(self,debug=False,cbdebug=False,gdebug=False,edebug=False,
                 tdebug=False,ldebug=False,ll1debug=False):
       super().__init__()
       self.debug=debug
       self.cbdebug=cbdebug
       self.gdebug=gdebug
       self.edebug=edebug
       self.ldebug=ldebug
       self.tdebug=tdebug
       self.ll1debug=ll1debug
       self.init()
       
#
#  These methods are used to create the language processor
#

    # Create my lexer - called by the lang.Language.create() method 
    def create_lexer(self):
         return MyLexer(debug=self.ldebug,tdebug=self.tdebug).init()

    # Define syntactical analysis - called by the lang.Language.create() method.
    # It returns a tuple of two strings: the grammar text specification and the 
    # PID of the starting production.
    #
    # To avoid conflict with other uses of the name 'grammar', it is recommended
    # when using the name 'grammar' as an attribute for the grammar text that it
    # be defined as a local variable within the define_parser() method, as below.
    def define_parser(self):

        grammar=\
"""# A test grammar
prod -> any_statements*!

any_statements -> statements
any_statements -> nl
any_statements -> EMPTY

statements -> name_statement
statements -> number_statement
statements -> operator_statement

name_statement -> name names*! nl
names -> name
names -> EMPTY

number_statement -> number numbers*! nl
numbers -> number
numbers -> EMPTY

operator_statement -> operator operators*! nl
operators -> operator
operators -> EMPTY

"""

        return (grammar,"prod")

    # Initialize the language processor and return it
    def configure(self,lang,debug=False,cbdebug=False,gdebug=False,edebug=False,\
            ll1debug=False):
        lang.flag("cbtrace")          # Define my debug flag
        # These flags control debug information provided by MyLexer and 
        # the parser.Parser classes debug options
        if self.debug or debug:
            lang.debug(pdebug=True)   # debug MyLanguage parser
            lang.debug(prdebug=True)  # debug my productions in the grammar
            lang.debug(ldebug=True)   # debug MyLexer when running
            self.ldebug=True
            
        if self.cbdebug or cbdebug:
            lang.debug(cbtrace=True)  # debug my call backs

        # These flags control debug information for Grammar and GLexer
        if self.gdebug or gdebug:
            lang.debug(gdebug=True)    # debug the Grammar operation
            lang.debug(gtdebug=True)   # debug the GLexer
            lang.debug(gldebug=True)   # debug the Grammar lexical processing
            
        # This flag controls debug information produced by the LL(1) analysis
        if self.ll1debug or ll1debug:
            lang.debug(gLL1debug=True) # debug LL1 analysis

        # Debug error generation
        if self.edebug or edebug:
            lang.debug(edebug=True)   # debug my errors

        # Set up my callback methods
        lang.cbreg("name_statement","beg",self.name_statement_beg)
        lang.cbreg("name_statement","token",self.name_statement_token)
        lang.cbreg("name_statement","end",self.name_statement_end)
        lang.cbreg("names","token",self.names_token)
        lang.cbreg("number_statement","beg",self.number_statement_beg)
        lang.cbreg("number_statement","token",self.number_statement_token)
        lang.cbreg("number_statement","end",self.number_statement_end)
        lang.cbreg("numbers","token",self.numbers_token)
        lang.cbreg("operator_statement","beg",self.operator_statement_beg)
        lang.cbreg("operator_statement","token",self.operator_statement_token)
        lang.cbreg("operator_statement","end",self.operator_statement_end)
        lang.cbreg("operators","token",self.operators_token)
        lang.cbreg("prod","beg",self.prod_beg)
        lang.cbreg("prod","end",self.prod_end)
        lang.cbreg("statements","beg",self.statements_beg)
        lang.cbreg("statements","empty",self.statements_empty)
        lang.cbreg("statements","end",self.statements_end)

    # Syntactical analyzer call back method
    def name_statement_beg(self,gs,pid):
        if self.lang.isdebug("cbtrace"):
            print("        Begining 'name_statement' pid=%s" % pid)
        gs.names_list=[]
    def name_statement_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'name_statement' pid=%s n=%s token=%s" \
                % (pid,n,token))
        if token.istype("nl"):
            return
        gs.names_list.append(token)
    def name_statement_end(self,gs,pid,failed,eo=[]):
        if self.lang.isdebug("cbtrace"):
            print("        Ending 'name_statement' pid=%s failed=%s" \
                % (pid,failed))
        
        if failed:
            gs.names_list=None
            return False
        if gs.names is None:
            gs.names=syntax.NT("names")
        for x in gs.names_list:
            gs.names.addChild(syntax.T(x))
        if self.lang.isdebug("cbtrace"):
            print("        gs.names: %s" % gs.names)
        gs.names_list=None

    def names_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'names' pid=%s n=%s token=%s" % (pid,n,token))
        gs.names_list.append(token)
        if self.lang.isdebug("cbtrace"):
            print("        gs.numbers: %s" % gs.names_list)

    def number_statement_beg(self,gs,pid):
        if self.lang.isdebug("cbtrace"):
            print("        Begining 'number_statement' pid=%s" % pid)
        gs.numbers_list=[]
    def number_statement_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'number_statement' pid=%s n=%s token=%s" \
                % (pid,n,token))
        if token.istype("nl"):
            return  
        gs.numbers_list.append(token)
    def number_statement_end(self,gs,pid,failed,eo=[]):
        if self.lang.isdebug("cbtrace"):
            print("        Ending 'number_statement' pid=%s failed=%s" \
                % (pid,failed))

        if failed:
            gs.numbers_list=None
            return False
        if gs.numbers is None:
            gs.numbers=syntax.NT("numbers")
        for x in gs.numbers_list:
            gs.numbers.addChild(syntax.T(x))
        if self.lang.isdebug("cbtrace"):
            print("        gs.numbers: %s" % gs.numbers)
        gs.numbers_list=None
        
    def numbers_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'numbers' pid=%s n=%s token=\n"
                  "            %s" % (pid,n,token))
        gs.numbers_list.append(token)
        if self.lang.isdebug("cbtrace"):
            print("        gs.numbers: %s" % gs.numbers_list)

    def operator_statement_beg(self,gs,pid):
        if self.lang.isdebug("cbtrace"):
            print("        Begining 'operator_statement' pid=%s" % pid)
        gs.operators_list=[]
    def operator_statement_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'operator_statement' pid=%s n=%s token=\n"
                  "            %s" % (pid,n,token))
        if token.istype("nl"):
            return
        gs.operators_list.append(token)
    def operator_statement_end(self,gs,pid,failed,eo=[]):
        if self.lang.isdebug("cbtrace"):
            print("        Ending 'operator_statement' pid=%s failed=%s" % (pid,failed))

        if failed:
            gs.operators_list=None
            return False
        if gs.operators is None:
            gs.operators=syntax.NT("operators")
        for x in gs.operators_list:
            gs.operators.addChild(syntax.T(x))
        if self.lang.isdebug("cbtrace"):
            print("        gs.operators: %s" % gs.operators)
        gs.operators_list=None
    
    def operators_token(self,gs,pid,n,token):
        if self.lang.isdebug("cbtrace"):
            print("        'operators' pid=%s n=%s token=\n"
                  "            %s" % (pid,n,token))
        gs.operators_list.append(token)
        if self.lang.isdebug("cbtrace"):
            print("        gs.operators: %s" % gs.operators_list)
    
    def prod_beg(self,gs,pid):
        if self.lang.isdebug("cbtrace"):
            print("        Begining 'prod' pid=%s" % pid)
        gs.root=syntax.AST()
        gs.numbers=None
        gs.operators=None
        gs.names=None
    def prod_end(self,gs,pid,failed=False,eo=[]):
        if self.lang.isdebug("cbtrace"):
            print("        'prod' ending - pid=%s failed=%s" % (pid,failed))

        if gs.numbers is not None:
            gs.root.addChild(gs.numbers)
        if gs.operators is not None:
            gs.root.addChild(gs.operators)
        if gs.names is not None:
            gs.root.addChild(gs.names)

    def statements_beg(self,gs,pid):
        if self.lang.isdebug("cbtrace"):
            print("         Begining 'statements' pid=%s" % pid)
    def statements_empty(self,gs,pid,n):
        if self.lang.isdebug("cbtrace"):
            print("         Empty string found 'statements' pid=%s n=%s" % (pid,n))
    def statements_end(self,gs,pid,failed,eo=[]):
        if self.lang.isdebug("cbtrace"):
             print("        Ending 'statements' pid=%s failed=%s" % (pid,failed))

#
#  These methods are used during syntactical analysis.
#
#  filter() method excludes from presentation to the parser of specific lexical 
#  tokens.
#  analyze() method drives the parsing process with the correct arguments
#  presented to the parser.Parser parse() method.
#

    # Filter the input tokens for just the ones I need
    def filter(self,gs,tok):
        if tok.istype("unrecognized"):
            gs.mgr.report(LL1parser.ErrorUnrecognized(tok))
            return None
        if tok.ignore:
            return None
        return tok
    # Process the supplied text
    def analyze(self,text):
        self.prepare()
        self.parse(text,depth=20,lines=True,fail=False)
         
# 
# These methods are used post syntactical analysis for processing the syntax tree
# and printing errors.
#

    # Print accumulated errors with help of the error manager
    def errors(self):
        mgr=self.manager()
        lst=mgr.present()
        if len(lst)==0:
            print("no errors found")
        else:
            print("Errors found: %s" % len(lst))
        for x in lst:
            x.print(debug=self.debug)

    # Print any errors and then walk the AST.
    def process(self,trace=False,debug=False):
        gs=self.scope()
        if debug:
            print("Tree: %s" % gs.root)
            print("names: %s" % gs.names)
            print("numbers: %s" % gs.numbers)
            print("operators: %s" % gs.operators)
        walker=MyWalker()
        walker.walk(gs.root,trace=trace,debug=debug)

class MyWalker(syntax.Visitor):
    def __init__(self):
        super().__init__()
    # These methods print generic information about the nodes
    def print_NT_nodes(self,node):
        print("%s node: nid=%s" % (node.__class__.__name__,node.nid))
    def print_T_nodes(self,node,token):
        print("%s node: tid=%s, string=%s" \
            % (node.__class__.__name__,token.tid,token.string))
        
    # These methods visit specific node id's
    def visit_name(self,node,debug=False):
        self.print_T_nodes(node,node.token)
    def visit_names(self,node,debug=False):
        self.print_NT_nodes(node)
    def visit_number(self,node,debug=False):
        self.print_T_nodes(node,node.token)
    def visit_numbers(self,node,debug=False):
        self.print_NT_nodes(node)
    def visit_operator(self,node,debug=False):
        self.print_T_nodes(node,node.token)
    def visit_operators(self,node,debug=False):
        self.print_NT_nodes(node)
    def visit_AST(self,node,debug=False):
        print("%s Root" % node.__class__.__name__)   

if __name__ == "__main__":
    # The test input text
    ti="""sdf asd asdf asdf
79808098 809  @#$
+ - * /
ewrwr werwerw werwrw
78909 rewwr
%^$
"""

    # Create the sample language processor     
    p=MyLanguage(ll1debug=True,gdebug=False,edebug=False)
    # Print grammar related information
    p.lang.grammar()
    p.lang.productions()
    
    # MyLanguage processing the test input
    print("\nMyLanguage parsing the test input...")
    p.lang.analyze(ti)
    
    # MyLanguage tree walker (it just prints it)
    print("\nMyLangage AST for parsed input text")
    p.process(trace=False,debug=False)
    
    # MyLanguage errors found
    print()
    p.errors()
    
    # Print text related information
    p.text()
    p.tokens()
