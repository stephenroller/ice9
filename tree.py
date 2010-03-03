#!/usr/bin/env python

class Tree():
    """Represents a generic tree."""
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.children = []
        
        # extra attributes
        for k,v in kwargs.iteritems():
            setattr(self, k, v)
    
    def kill(self):
        if self.parent is None:
            raise ValueError('root of the tree cannnot die.')
        
        if self in self.parent.children:
            self.parent.children.remove(self)
        self.parent = None

    def add_child(self, **kwargs):
        child = Tree(parent=self, **kwargs)
        self.children.append(child)
        return child
    
    def become_child(self):
        """
        Effectively removes the node from the tree by replacing it with its first child.
        """
        # hack to make sure we don't accidentally lose ice9 typing
        if hasattr(self.children[0], 'ice9_type'):
            assert not hasattr(self, 'ice9_type')
            setattr(self, 'ice9_type', self.children[0].ice9_type)
        
        self.line = self.children[0].line
        self.node_type = self.children[0].node_type
        self.value = self.children[0].value
        self.children = self.children[0].children
        
        for c in self.children:
            c.parent = self
    
    def remove_and_promote(self):
        """
        Kills this node and gives its children to its parent.
        """
        for c in self.children:
            c.parent = self.parent
        i = self.parent.children.index(self)
        spc = self.parent.children
        self.parent.children = spc[:i] + self.children + spc[i+1:]
    
    def adopt_right_sibling(self):
        i = self.parent.children.index(self)
        # remove the left sibling
        left_sibling = self.parent.children.pop(i+1)
        # and move it to the front
        self.children.insert(0, left_sibling)
        left_sibling.parent = self
    
    def adopt_left_sibling(self):
        i = self.parent.children.index(self)
        # remove the left sibling
        left_sibling = self.parent.children.pop(i-1)
        # and move it to the front
        self.children.insert(0, left_sibling)
        left_sibling.parent = self
    
    def postfix_iter(self):
        for child in self.children.__reversed__():
            for x in child.postfix_iter():
                yield x
        yield self
    
    def prefix_iter(self):
        yield self
        for child in self.children:
            for x in child.prefix_iter():
                yield x
    
    def __str__(self, tab=""):
        out = []
        print_attr = ('line', 'node_type', 'value', 'ice9_type')
        as_str = '\t'.join(s + ": " + str(getattr(self, s)) 
                                          for s in print_attr if hasattr(self, s))
        out.append(tab + as_str)
        for child in self.children:
            out.append(child.__str__(tab + "- "))
        return "\n".join(out)

