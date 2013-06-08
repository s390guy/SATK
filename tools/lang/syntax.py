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

# This module is intended to be imported for use by other modules for the purpose
# utilizing an Abstract Syntax Tree (AST) within a language processoe.  Refer to the 
# document "SATK for s390 - Language Processing Tools" in the SATK doc directory for
# a description of this module's usage.

# Python imports: None

# SATK imports: None

# The following classes provide support for generic tree nodes:
#
# Node    The base class for all tree nodes.
# Leaf    The base class for leaf nodes which do not have children nodes. These
#         nodes are at the bottom of the tree.
# Parent  The base class for parent nodes supporting children.
# Tree    Aids in building trees buy allowing the definition of node id's and the
#         corresponding syntax.Node subclass used to create it.
# Visitor This class does a depth first walk of a supplied tree from its "root'
#         node.
#
# The following classes provide syntax tree related nodes, derived from the 
# generic nodes
#
# NT      Non-terminal nodes created from productions by syntax analysis.
# T       Terminal nodes created from lexical tokens of import to the syntax and
#         later semantic analysis.
# Tree

# Base class for all Abstract Syntax Tree nodes.  AST nodes are created during
# syntax analysis and processed during semantic processing in a language processor.
# 
# Instance arguments:
#   nid      Language specific node id name or subclass name if not provided.
class Node(object):
    def __init__(self,nid=None):
        if nid is None:
            self.nid=self.__class__.__name__
        else:
            self.nid=nid
        self._parent=None
        self._children=[]
        
    def __str__(self):
        string="%s: %s Children:" % (self.__class__.__name__,self.nid)
        for x in self._children:
            string="%s %s" % (string,x.nid)
        return string
        
    def _addChild(self,n):
        if not isinstance(n,Node):
            raise TypeError("syntax.Node.addChild() - child node not a syntax.Node "
                "subclass: %s" % n)
        n._addParent(self)
        self._children.append(n)
        
    def _addParent(self,parent):
        if not isinstance(parent,Node):
            raise TypeError("syntax.Node._addParent() - parent node not a "
                "syntax.Node subclass: %s" % parent)
        self._parent=parent

    def _isnid(self,nids=[]):
        if len(nids)==0:
            return True
        return self.nid in nids

    def init(self,*args,**kwds):
        raise NotImplementedError("syntax.Node.init() - subclass %s must provide "
            "the init() method" % self.__class__.__name__)

    def visit(self,visitor):
        return visitor.visit(self)

#
# These three subclasses of Node are generic in nature and usable for any tree.
#
class Leaf(Node):
    def __init__(self,nid=None):
        super().__init__(nid=nid)
    def addChild(self,n):
        raise NotImplementedError("syntax.Leaf.addChild() - leaf nodes do not "
            "support children")
    def addChildren(self,*args,**kwds):
        raise NotImplementedError("syntax.Leaf.addChildren() - leaf nodes do not "
            "support children")
    def getAllChildren(self,*args,**kwds):
        raise NotImplementedError("syntax.Leaf.getAllChildren() - leaf nodes do "
            "not support children")
    def getChildren(self,*args,**kwds):
        raise NotImplementedError("syntax.Leaf.getChildren() - leaf nodes do "
            "not support children")
    def getChild(self,*args,**kwds):
        raise NotImplementedError("syntax.Leaf.getChild() - child nodes not "
            "supported")

class Parent(Node):
    def __init__(self,nid=None):
        super().__init__(nid=nid)
    def addChild(self,n):
        self._addChild(n)
    def addChildren(self,c):
        for x in c:
            self._addChild(x)
    def getAllChildren(self,nids=[]):
        f=[]
        for i in self._children:
            if not i._isnid(nids):
                continue
            if len(i._children)>0:
                f.extend(i.getAllChildren(nids=nids))
            else:
                f.append(i)
        f.append(self)
        return f
    def getChildren(self,nids=[]):
        f=[]
        for n in self._children:
            if not n._isnid(nids):
                continue
            f.append(n)
        
class Root(Parent):
    def __init__(self,nid=None):
        super().__init__(nid=nid)
    def _addParent(self,parent):
        raise NotImplementedError("syntax.Root._addParent() - root nodes do not "
            "support adding a parent")
       
#
# These three subclasses of the generic nodes are tailored in name and function for
# use in Abstract Syntax Trees
#
class AST(Root):
    def __init__(self,nid=None):
        super().__init__(nid=nid)
       
class NT(Parent):
    def __init__(self,nid=None):
        super().__init__(nid=nid)

class T(Leaf):
    def __init__(self,token,nid=None):
        self.token=token
        if nid is None:
            n=token.tid
        else:
            n=nid
        super().__init__(nid=n)

# This class manages the creation of abstract syntax tree nodes for a specific
# instance of a tree.  The tree itself exists outside of the syntax.Tree class
# or subclass.  This class is really used for convenience.  syntax.Node instances
# can be completely managed by the language processor.
#
# Instance arguments:
#    default  Specify default=class to specify a default class used to instantiate
#             unregistered node ids.
#
# Instance methods used to tailor an Abstract Syntax Tree
#    init   Method used to tailor a specifc Tree in a syntax.Tree subclass.
#           It will call the syntax.nid method() for that purpose.
#    nid    Register a node id and its corresponding syntax.Node subclass used to
#           create it.
#
# Instance methods used during language processing:
#    node   Create a syntax.Node or subclass instance.
def Tree(object):
    def __init__(self,default=None):
        self.default=None
        if default is not None and not issubclass(default,Node):
           raise TypeError("syntax.Tree.__init__() - default class is not subclass "
               "of Node: %s" % default)
        else:
           self.default=default
        self.nids={}
        
    # This method tailors a given Tree for use by defining the set of nids that 
    # require a specific subclass of Node.  Unregistered node id's will default
    # to an instance of Node.
    # WARNING: the init() method of a subclass is NOT called by this method.  The
    # caller of this method must do that if the subclass requires it.
    # It could be done this way:
    #    node=Tree.node().init(<my_init_args)
    def init(self,*args,**kwds):
        raise NotImplementedError("syntax.Tree.init() - subclass of syntax.Tree "
            "must provide init() method: %s" % self.__class__.__name__)
        
    # Register a Node subclass and its corresponding node id.  If the node id is
    # not supplied, the subclass name is registered.
    def nid(self,cls,nid=None):
        if not issubclass(cls,Node):
            raise TypeError("syntax.Tree.nid() - supplied class not a "
                "subclass of Node: %s" % cls)
        if nid is None:
            n=cls.__name__
        else:
            n=nid
        try:
            i=self.nids[n]
            raise ValueError("syntax.Tree.nid() - duplicate node id "
                "encountered: %s" % n)
        except KeyError:
            self.nids[n]=cls
            
    # Create an Abstract Syntax Tree node instance from its node id.  The subclass
    # registered for the nid is used, otherwise the base syntax.Node class will be
    # used.
    # WARNING: the init() method of a subclass is NOT called by this method.  The
    # caller of this method must do that if the subclass requires it.
    # It could be done this way:
    #    node=Tree.node("nid").init(<my_node_init_args>)
    def node(self,nid):
        if default is None:
            try:
                cls=self.nids[nid]
            except KeyError:
                raise ValueError("syntax.Tree.node() - node id is not registered:"
                    "%s" % (self.__class__.__name__,nid)) from None
        else:
            cls=self.nids.get(nid,self.default)
        return cls(nid)

# The Visitor class manages a tree walk and its processing
#
class Visitor(object):
    def __init__(self):
        self.debug=False
        self.trace=False
        self.cls=self.__class__.__name__
 
    # This internal method "visits" a node in the abstract syntax tree by calling a 
    # method associated with the node's id or the default method.
    def _visit(self,node):
        method=getattr(self,"visit_%s" % node.nid,self.default)
        if self.trace:
            cls=self.cls
            mstr=method.__name__
            print("%s.visit() - calling: %s(%s,debug=%s)" \
                % (cls,mstr,node,self.debug))
        result=method(node,debug=self.debug)
        if self.trace:
            print("%s.visit() - return:  %s=%s()" % (cls,result,mstr))
        return result
        
    # This method is intended to be overriddent by a subclass for processing
    # of nodes for which a method has not been explicitly associated with its
    # node ide.  Otherwise, it bypasses the node.
    def default(self,node,debug=False): pass
    
    # This method gives a subclass (by overriding it and calling the _visit() method
    # itself) to capture the results of the visited method.  Otherwise the results
    # are simply discarded.
    def visit(self,node):
        return self._visit(node)
    
    # This method walks the abstract syntax tree identified by its "root" node,
    # visiting just those nodes identified by the nids argument or all if omitted.
    # "Visiting" the node means that the node  is passed to a method within this 
    # object associated with the node it (or the default method).  If the default 
    # method is not overridden, the node will be bypassed.
    #
    # A method is associated with a node id by coding a method in the subclass
    # by preceding the node id with "visit_".  For example, a node with the id of
    # "name" would be visited by defining this method.
    #
    #   def visit_name(self,node,debug=False):
    #
    # All methods used for visiting a node must use the above 
    #
    # Method arguments:
    #    ast   The "root" node of the tree being walked.  Any node of a tree may
    #          be walked.
    #    nids  Only node ids of the supplied list of strings will be selected for
    #          visiting.  If the argument is omitted, all nodes will be visited
    # 
    def walk(self,ast,nids=[],trace=False,debug=False):
        self.trace=trace
        self.debug=debug
        if self.debug:
            print(ast)
        children=ast.getAllChildren(nids)
        if debug:
            print("syntax.Visitor.walk() - children:\n%s" % children)
        for child in children:
            if debug:
                print(child)
            res=self.visit(child)
            if self.debug and res is not None:
                print("%s.walk() - %s=self.visit(%s)" % (self.cls,res,child))

if __name__ == "__main__":
    raise NotImplementedError("syntax.py - must only be imported")
