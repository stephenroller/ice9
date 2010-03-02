#!/usr/bin/env python

from ice9 import Ice9Error
from tree import Tree
from parser import parse
from ast import parse2ast

class Ice9SemanticError(Ice9Error):
    pass

ice9_types = [{
    'int': 'base',
    'str': 'base',
    'bool': 'base',
}]

ice9_vars = [ { } ]

def on_type(tnode):
    for c in tnode.children:
        pass

inherited_callbacks = {
    'type': on_type,
}

sythenisized_callbacks = {
    
}

def check_semantics(ast):
    if ast.node_type in inherited_callbacks:
        callback = inherited_callbacks[ast.node_type]
        callback(ast)
    
    for n in ast.children:
        check_semantics(n)
    
    if ast.node_type in sythenisized_callbacks:
        callback = sythenisized_callbacks[ast.node_type]
        callback(ast)
    
    return True

    
if __name__ == '__main__':
    with file('test.txt') as f:
        p = parse2ast(parse(f.read()))
        print p
        print check_semantics(p)