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
import lang     # Access the language tools' semantic analyzer framework.
import lexer    # Access the language tools' lexical analyzer
import parser   # Access the language tools' syntactical analyzer
import syntax   # Access the AST nodes

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
        if self.gdebug:
            self.types()
        return self

class MyLanguage(lang.Language):
    def __init__(self):
       super().__init__()
#
#  These methods are used to create the language processor
#

    # Create my lexer - called by the lang.Language.create() method 
    def create_lexer(self):
         return MyLexer(\
            debug=self.isdebug("ldebug"),
            tdebug=self.isdebug("tdebug")).init()

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
prod -> statements*
statements -> name_statement  <!nl+>
statements -> number_statement
statements -> operator_statement
name_statement -> name+ nl
number_statement -> number+ nl
operator_statement -> operator+ nl
"""

        return (grammar,"prod")

    # Initialize the language processor and return it
    def init(self,debug=False,cbdebug=False,gdebug=False,edebug=False):
        self.flag("cbtrace")          # Define my debug flag
        # These flags control debug information provided by MyLexer and 
        # the parser.Parser classes debug options
        if debug:
            self.debug(pdebug=True)   # debug MyLanguage parser
            self.debug(prdebug=True)  # debug my productions in the grammar
            self.debug(ldebug=True)   # debug MyLexer when running
            
        if cbdebug:
            self.debug(cbtrace=True)  # debug my call backs

        # These flags control debug information for Grammar and GLexer
        if gdebug:
            self.debug(gdebug=True)   # debug the Grammar operation
            self.debug(gtdebug=True)  # debug the GLexer
            self.debug(gldebug=True)  # debug the Grammar lexical processing

        # Debug error generation
        if edebug:
            self.debug(edebug=True)   # debug my errors

        # Set up my callback methods
        self.cbreg("name_statement","beg",self.name_statement_beg)
        self.cbreg("name_statement","token",self.name_statement_token)
        self.cbreg("name_statement","end",self.name_statement_end)
        self.cbreg("number_statement","beg",self.number_statement_beg)
        self.cbreg("number_statement","token",self.number_statement_token)
        self.cbreg("number_statement","end",self.number_statement_end)
        self.cbreg("operator_statement","beg",self.operator_statement_beg)
        self.cbreg("operator_statement","token",self.operator_statement_token)
        self.cbreg("operator_statement","end",self.operator_statement_end)
        self.cbreg("prod","beg",self.prod_beg)
        self.cbreg("prod","end",self.prod_end)
        self.cbreg("statements","beg",self.statements_beg)
        self.cbreg("statements","end",self.statements_end)

        # Create the language processor
        self.create()
        return self

    # Syntactical analyzer call back method
    def name_statement_beg(self,pid):
        if self.isdebug("cbtrace"):
            print("Begining 'name_statement' pid=%s" % pid)
        self.gs.names_list=[]
    def name_statement_token(self,pid,n,token):
        if self.isdebug("cbtrace"):
            print("'name_statement' pid=%s n=%s token=%s" % (pid,n,token))
        if token.istype("nl"):
            return
        self.gs.names_list.append(token)
    def name_statement_end(self,pid,failed,eo=[]):
        if self.isdebug("cbtrace"):
            print("Ending 'name_statement' pid=%s failed=%s" % (pid,failed))
        gs=self.gs
        if failed:
            gs.names_list=None
            return True
        if gs.names is None:
            gs.names=syntax.NT("names")
        for x in gs.names_list:
            gs.names.addChild(syntax.T(x))
        if self.isdebug("cbtrace"):
            print("gs.names: %s" % gs.names)
        gs.name_list=None

    def number_statement_beg(self,pid):
        if self.isdebug("cbtrace"):
            print("Begining 'number_statement' pid=%s" % pid)
        self.gs.numbers_list=[]
    def number_statement_token(self,pid,n,token):
        if self.isdebug("cbtrace"):
            print("'number_statement' pid=%s n=%s token=%s" % (pid,n,token))
        if token.istype("nl"):
            return  
        self.gs.numbers_list.append(token)
    def number_statement_end(self,pid,failed,eo=[]):
        if self.isdebug("cbtrace"):
            print("Ending 'number_statement' pid=%s failed=%s" % (pid,failed))
        gs=self.gs
        if failed:
            gs.numbers_list=None
            return True
        if gs.numbers is None:
            gs.numbers=syntax.NT("numbers")
        for x in gs.numbers_list:
            gs.numbers.addChild(syntax.T(x))
        if self.isdebug("cbtrace"):
            print("gs.numbers: %s" % gs.numbers)
        gs.numbers_list=None
    
    def operator_statement_beg(self,pid):
        if self.isdebug("cbtrace"):
            print("Begining 'operator_statement' pid=%s" % pid)
        self.gs.operators_list=[]
    def operator_statement_token(self,pid,n,token):
        if self.isdebug("cbtrace"):
            print("'operator_statement' pid=%s n=%s token=%s" % (pid,n,token))
        if token.istype("nl"):
            return
        self.gs.operators_list.append(token)
    def operator_statement_end(self,pid,failed,eo=[]):
        if self.isdebug("cbtrace"):
            print("Ending 'operator_statement' pid=%s failed=%s" % (pid,failed))
        gs=self.gs
        if failed:
            gs.operators_list=None
            return True
        if gs.operators is None:
            gs.operators=syntax.NT("operators")
        for x in gs.operators_list:
            gs.operators.addChild(syntax.T(x))
        if self.isdebug("cbtrace"):
            print("gs.operators: %s" % gs.operators)
        gs.operators_list=None
    
    def prod_beg(self,pid):
        if self.isdebug("cbtrace"):
            print("Begining 'prod' pid=%s" % pid)
        gs=self.gs
        gs.root=syntax.AST()
        gs.numbers=None
        gs.operators=None
        gs.names=None
    def prod_end(self,pid,failed=False,eo=[]):
        if self.isdebug("cbtrace"):
            print("'prod' ending - pid=%s failed=%s" % (pid,failed))
        gs=self.gs
        if gs.numbers is not None:
            gs.root.addChild(gs.numbers)
        if gs.operators is not None:
            gs.root.addChild(gs.operators)
        if gs.names is not None:
            gs.root.addChild(gs.names)

    def statements_beg(self,pid):
        if self.isdebug("cbtrace"):
            print("Begining 'statements' pid=%s" % pid)
    def statements_end(self,pid,failed,eo=[]):
        if self.isdebug("cbtrace"):
             print("Ending 'statements' pid=%s failed=%s" % (pid,failed))

#
#  These methods are used during syntactical analysis.
#
#  filter() method excludes from presentation to the parser of specific lexical 
#  tokens.
#  analyze() method drives the parsing process with the correct arguments
#  presented to the parser.Parser parse() method.
#

    # Filter the input tokens for just the ones I need
    def filter(self,tok):
        if tok.istype("unrecognized"):
            self.gs.mgr.report(parser.ErrorUnrecognized(tok))
            #print("[%s:%s] unrecognized text ignored: '%s'" \
            #    % (tok.line,tok.linepos,tok.string))
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
        mgr=self.gs.mgr
        lst=mgr.present()
        #print(lst)
        if len(lst)==0:
            print("no errors found")
        else:
            print("Errors found: %s" % len(lst))
        debug=self.isdebug("edebug")
        for x in lst:
            x.print(debug=debug)

    # Print any errors and then walk the AST.
    def process(self,trace=False,debug=False):
        gs=self.gs
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
    p=MyLanguage().init(debug=False,cbdebug=True,gdebug=False,edebug=False)
    # Print grammar related information
    p.grammar()
    p.productions()
    
    # MyLanguage processing the test input
    print("\nMyLanguage parsing the test input...")
    p.analyze(ti)
    
    # MyLanguage tree walker (it just prints it)
    print("\nMyLangage AST for parsed input text")
    p.process(trace=False,debug=False)
    
    # MyLanguage errors found
    print()
    p.errors()
    
    # Print text related information
    p.source()
    p.tokens()
