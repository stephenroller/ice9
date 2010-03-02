#!/usr/bin/env python

from ice9 import Ice9Error
from tree import Tree
from parser import parse
from ast import parse2ast

class Ice9SemanticError(Ice9Error):
    pass

ice9_types = [{
    'nil': 'base',
    'int': 'base',
    'str': 'base',
    'bool': 'base',
}]

ice9_symbols = [ { } ]

def find_all_definitions(scopes, name):
    """
    Returns an iterator on all the definitions of name in scopes.
    """
    return (scope[name] for scope in scopes if name in scope)

def define(scopes, name, value):
    """
    Define name to be value in the latest scope of scopes.
    """
    assert len(scopes) > 0, 'The scope stack is empty. This should *not* happen.'
    scopes[0][name] = value

def add_scope():
    """
    Add a new scope.
    """
    ice9_types.insert(0, dict())
    ice9_symbols.insert(0, dict())

def leave_scope():
    """
    Leave the last scope.
    """
    ice9_types.pop(0)
    ice9_symbols.pop(0)
    
    assert len(ice9_types) > 0 and len(ice9_symbols) > 0, \
            'The scope stack is empty. This should *not* happen.'

def first_definition(scope, name):
    """
    Returns the first definition of name in scope, or None if none exists.
    """
    for d in find_all_definitions(scope, name):
        return d
    
    return None

def equivalent_types(type1, type2):
    """
    Returns true or false, if the types are equivalent.
    """
    return type1 == type2

def check_and_set_type(node, check_type):
    """
    If the node doesn't already have an ice9_type, set it to check_type.
    If the node has an ice9_type, check that ice9_type == check_type.
    If the types don't match, raise an exception.
    """
    if hasattr(node, 'ice9_type'):
        if equivalent_types(node.ice_type, check_type):
            return True
        else:
            # FIXME: better error message
            raise Ice9SemanticError, "types dont match"
    else:
        setattr(node, 'ice9_type', check_type)

def typenode_to_type(tnode):
    full_type = tnode.value
    for dimension_size in tnode.children:
        assert (dimension_size.node_type == 'literal'), "Array sizes must be literal ints."
        assert dimension_size.ice9_type == 'int', "Array sizes must be literal ints."
        full_type = ["array", full_type, dimension_size.value]
    
    return full_type

def define_type(dtnode):
    # process the type early
    assert len(dtnode.children) == 1
    assert dtnode.children[0].node_type == 'type'
    ice9_type = typenode_to_type(dtnode.children[0])
    dtnode.children.pop(0)
    
    typename = dtnode.value
    assert len(dtnode.children) == 0
    
    definitions = list(find_all_definitions(ice9_types, typename))
    assert len(definitions) == 0, 'type ' + typename + ' is already defined.'
    
    define(ice9_types, typename, ice9_type)
    dtnode.kill()

def define_var(varnode):
    # Need to find the var's type
    assert len(varnode.children) == 1
    assert varnode.children[0].node_type == 'type'
    ice9_type = typenode_to_type(varnode.children[0])
    varnode.children.pop(0)
    
    varname = varnode.value
    assert len(varnode.children) == 0
    
    definitions = list(find_all_definitions(ice9_symbols, varname))
    assert len(definitions) == 0, 'var ' + varname + ' is already defined.'
    
    define(ice9_symbols, varname, ice9_type)
    varnode.kill()
    
def ident(identnode):
    # represents a symbol lookup
    defn = None
    defn = first_definition(ice9_symbols, identnode.value)
    assert defn is not None, identnode.value + " is not defined."
    check_and_set_type(identnode, defn)

def operator(opnode):
    if opnode.value in ('write', 'writes', 'break', 'return', 'exit'):
        check_and_set_type(opnode, 'nil')

inherited_callbacks = {
    'define_type': define_type,
    'define': define_var,
}

sythenisized_callbacks = {
    # 'type': on_type,
    'ident': ident,
    'operator': operator
}

def check_semantics(ast):
    if ast.node_type in inherited_callbacks:
        callback = inherited_callbacks[ast.node_type]
        callback(ast)
    
    for n in list(ast.children):
        check_semantics(n)
    
    if ast.node_type in sythenisized_callbacks:
        callback = sythenisized_callbacks[ast.node_type]
        callback(ast)
    
    return True

if __name__ == '__main__':
    with file('test.txt') as f:
        ast = parse2ast(parse(f.read()))
        print check_semantics(ast)
        print '%' * 80
        print ice9_types
        print ""
        print ice9_symbols
        print '-' * 80
        print ast