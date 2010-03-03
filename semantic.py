#!/usr/bin/env python

from ice9 import Ice9Error
from tree import Tree
from parser import parse
from ast import parse2ast

class Ice9SemanticError(Ice9Error):
    pass

ice9_procs = [ {
    'int': ['proc', 'int', ["param", "num", 'str']]
} ]

ice9_types = [{
    'nil': 'base',
    'int': 'base',
    'str': 'base',
    'bool': 'base',
}]

ice9_symbols = [ { } ]


def find_all_definitions(scopes, name):
    """Returns an iterator on all the definitions of name in scopes."""
    return (scope[name] for scope in scopes if name in scope)




def define(scopes, name, value):
    """Define name to be value in the latest scope of scopes."""
    assert len(scopes) > 0, 'The scope stack is empty. This should *not* happen.'
    scopes[0][name] = value

def add_scope():
    """Add a new scope."""
    ice9_types.insert(0, dict())
    ice9_symbols.insert(0, dict())

def leave_scope():
    """Leave the last scope."""
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


def expand_type(typeval):
    """Keeps expanding out typeval until it hits a base."""
    if type(typeval) is str:
        subtype = first_definition(ice9_types, typeval)
        if subtype is not None:
            if subtype == 'base':
                return typeval
            else:
                return expand_type(subtype)
        else:
            raise Exception, "Dead type!"
    elif type(typeval) == list:
        if typeval[0] == "array":
            return ["array", expand_type(typeval[1])] + typeval[2:]
        elif typeval[0] == "param":
            return expand_type(typeval[2])
        elif typeval[0] == "forward" or typeval[0] == "proc":
            return ["proc"] + [expand_type(t) for t in typeval[1:]]
        else:
            raise Exception, "You forgot to expand the type of " + typeval[0]


def equivalent_types(type1, type2):
    """Returns true or false, if the types are equivalent."""
    return expand_type(type1) == expand_type(type2)


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
            raise Ice9SemanticError(), "types dont match"
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
    
    # definitions = list(find_all_definitions(ice9_symbols, varname))
    # assert len(definitions) == 0, 'var ' + varname + ' is already defined.'
    
    define(ice9_symbols, varname, ice9_type)
    varnode.kill()


def param(paramnode):
    assert len(paramnode.children) == 1
    assert paramnode.children[0].node_type == 'type'
    ice9_type = typenode_to_type(paramnode.children[0])
    paramnode.children.pop(0)
    
    paramname = paramnode.value
    assert len(paramnode.children) == 0
    paramnode.ice9_type = ice9_type
    paramnode.children = []
    

def ident(identnode):
    # represents a symbol lookup
    defn = None
    defn = first_definition(ice9_symbols, identnode.value)
    assert defn is not None, identnode.value + " is not defined."
    check_and_set_type(identnode, defn)


def operator(opnode):
    op = opnode.value
    
    if op in ('break', 'return', 'exit'):
        check_and_set_type(opnode, 'nil')
        assert len(opnode.children) == 0, op + " takes no arguments."
    
        if op == 'break':
            # check loop here
            pass
        
    
    elif op == 'write' or op == 'writes':
        check_and_set_type(opnode, 'nil')
        assert len(opnode.children) == 1, op + " takes one parameter."
        assert opnode.children[0].ice9_type in ('bool', 'int', 'str'), \
            op + ' cannot use type ' + opnode.children[0].ice9_type
    
    elif len(opnode.children) == 1 and op == '-':
        assert opnode.children[0].ice9_type in ('bool', 'int')
        check_and_set_type(opnode, opnode.children[0].ice9_type)
    
    elif len(opnode.children) == 1 and op == '?':
        assert opnode.children[0].ice9_type == 'int', '? takes a bool.'
        check_and_set_type(opnode, 'int')
    
    elif op in ('<', '<=', '>', '>='):
        for c in opnode.children:
            assert c.ice9_type == 'int', c.value + " is not an int."
        check_and_set_type(opnode, 'bool')
   
    elif op in ('/', '%'):
        for c in opnode.children:
            assert c.ice9_type == 'int', c.value + " is not an int."
        check_and_set_type(opnode, 'int')
    
    elif op in ('=', '!=', '-', '+', '*'):
        assert opnode.children[0].ice9_type == opnode.children[1].ice9_type, \
            "arguments of " + op + " must be the same."
        assert opnode.children[0].ice9_type in ('int', 'bool', 'str')
        check_and_set_type(opnode, opnode.children[0].ice9_type)
        

def array_reference(arrnode):
    vartype = first_definition(ice9_symbols, arrnode.value)
    assert vartype is not None
    vartype = expand_type(vartype)
    for c in arrnode.children:
        assert c.ice9_type == 'int'
        assert vartype[0] == "array"
        vartype = vartype[1]
    
    check_and_set_type(arrnode, vartype)

def assignment(setnode):
    cs = setnode.children
    assert equivalent_types(cs[0].ice9_type, cs[1].ice9_type), \
           ("Types " + cs[0].ice9_type + " and " + cs[1].ice9_type +
            " are incompatible.")
    assert cs[1].ice9_type != 'nil', ' '.join(
            'Cannot assign variable', cs[1].value)
    assert first_definition(ice9_types, cs[0].ice9_type) == "base", ''.join(
            "Cannot assign to non-base type ", cs[0].ice9_type)
    
    check_and_set_type(setnode, 'nil')

def forward(forwardnode):
    if len(forwardnode.children) >= 1 and forwardnode.children[0].node_type == 'type':
        return_type = typenode_to_type(forwardnode.children.pop(0))
    else:
        return_type = 'nil'
    
    check_and_set_type(forwardnode, return_type)
    forwardtype = ["forward", return_type]
    for c in forwardnode.children:
        assert c.node_type == 'param', "What's a non-param doing in a forward?"
        param(c)
        forwardtype.append(["param", c.value, c.ice9_type])
    
    define(ice9_procs, forwardnode.value, forwardtype)
    forwardnode.kill()

def inherited_proc(procnode):
    add_scope()
    
    procname = procnode.value
    proctype = ["proc"]
    for c in procnode.children:
        if c.node_type == 'param':
            param(c)
            proctype.append(["param", c.value, c.ice9_type])
            define(ice9_symbols, c.value, c.ice9_type)
    
    if procnode.children[0].node_type == 'type':
        rettype = typenode_to_type(procnode.children.pop(0))
    else:
        rettype = 'nil'
    proctype.insert(1, rettype)
    # check if we had a forward define it already.
    check_and_set_type(procnode, proctype)
    forward_defn_type = first_definition(ice9_procs, procname)
    if forward_defn_type is not None:
        assert equivalent_types(proctype, forward_defn_type), \
               "proc " + procname + " does not match the signature of its forward."
        forward_defn_type[0] = "proc"
    else:
        define_type(ice9_procs, procname, proctype)
    
def synthesized_proc(procnode):
    leave_scope()

def notype(prognode):
    check_and_set_type(prognode, 'nil')

def proc_call(pcnode):
    from itertools import izip_longest
    pctype = first_definition(ice9_procs, pcnode.value)
    for child, param in izip_longest(pcnode.children, pctype[2:]):
        assert equivalent_types(child.ice9_type, param), str(
            "parameter " + " takes a " + param.ice9_type +
            ", not a " + child.ice9_type)
    
    check_and_set_type(pcnode, pctype[1])

inherited_callbacks = {
    'define_type': define_type,
    'define': define_var,
    'proc': inherited_proc,
    'forward': forward,
}

sythenisized_callbacks = {
    'ident': ident,
    'operator': operator,
    'assignment': assignment,
    'array_reference': array_reference,
    'proc': synthesized_proc,
    'proc_call': proc_call,
    'program': notype,
    'statements': notype,
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
        print ice9_procs
        print ""
        print ice9_types
        print ""
        print ice9_symbols
        print '-' * 80
        print ast