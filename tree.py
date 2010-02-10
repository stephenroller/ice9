#!/usr/bin/env python

class Tree():
    """Represents a generic tree."""
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        
        # extra attributes
        for k,v in kwargs.iteritems():
            setattr(self, k, v)
        
        self.children = []
    
    def kill(self):
        if self.parent is None:
            raise ValueError('root of the tree cannnot die.')
        
        self.parent.children.remove(self)
        self.parent = None

    def add_child(self, **kwargs):
        child = Tree(parent=self, **kwargs)
        self.children.append(child)
        return child

    def adopt_grandchildren(self):
        """
        Gets rid of all the children and takes all the grandchildren in
        directly.
        """
        print "adoption!"
        grandchildren = []
        for child in self.children:
            grandchildren += child.children
        self.children = grandchildren

    
    def postfix_iter(self):
        for child in self.children:
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
        out.append(tab + str(getattr(self, 'token', "NULL")))
        for child in self.children:
            out.append(child.__str__(tab + "-"))
        return "\n".join(out)

