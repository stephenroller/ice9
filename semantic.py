#!/usr/bin/env python

from ice9 import Ice9Error
from tree import Tree
from parser import parse
from ast import parse2ast

class Ice9SemanticError(Ice9Error):
    def __init__(self, node, error_message):
        self.line = node.line
        self.error = error_message

ice9_procs = None

ice9_types = None

ice9_symbols = None

def find_all_definitions(scopes, name):
    """Returns an iterator on all the definitions of name in scopes."""
    return [scope[name] for scope in scopes if name in scope]

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
            raise ValueError('unknown type: %s' % typeval)
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
        if equivalent_types(node.ice9_type, check_type):
            return True
        else:
            # FIXME: better error message
            raise Ice9SemanticError(), "types dont match"
    else:
        setattr(node, 'ice9_type', check_type)



##

def check(result, node, errormsg):
    if not result:
        raise Ice9SemanticError(node, errormsg)

def typenode_to_type(tnode):
    full_type = tnode.value
    for dimension_size in tnode.children:
        check(dimension_size.node_type == 'literal', dimension_size, 
            "Array sizes must be literal ints.")
        check(dimension_size.ice9_type == 'int', dimension_size, 
            "Array sizes must be literal ints.")
        check(dimension_size.value > 0, dimension_size,
            "array dimensions must be > 0")
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
    
    definitions = find_all_definitions(ice9_types, typename)
    check(len(definitions) == 0, dtnode, 
          'type ' + typename + ' is already defined in the current scope')
    
    define(ice9_types, typename, ice9_type)
    dtnode.kill()

def define_var(varnode):
    # Need to find the var's type
    assert len(varnode.children) == 1
    assert varnode.children[0].node_type == 'type'
    try:
        ice9_type = expand_type(typenode_to_type(varnode.children[0]))
    except ValueError, e:
        check(False, varnode.children[0], e)
    varnode.children.pop(0)
    
    varname = varnode.value
    assert len(varnode.children) == 0
    check(varname not in ice9_symbols[0],
          varnode,
          'var(s) already defined in scope')
    
    define(ice9_symbols, varname, ice9_type)
    varnode.kill()

def param(paramnode):
    assert len(paramnode.children) == 1
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
    check(defn is not None, identnode, "undeclared variable: %s" % identnode.value)
    check_and_set_type(identnode, expand_type(defn))

def operator(opnode):
    op = opnode.value
    
    if op in ('break', 'return', 'exit'):
        check_and_set_type(opnode, 'nil')
        check(len(opnode.children) == 0, opnode, op + " takes no arguments.")
    
        if op == 'break':
            check(opnode.loopcount > 0, opnode, "breaks may only appear within a loop")
    
    elif op == 'write' or op == 'writes':
        check_and_set_type(opnode, 'nil')
        check(len(opnode.children) == 1, opnode, op + " takes one parameter.")
        check(any(equivalent_types(t, opnode.children[0].ice9_type)
                for t in ('int', 'str')),
              opnode,
              'incompatible argument type to %s' % op)
    
    elif op == 'read':
        check_and_set_type(opnode, 'int')
        check(len(opnode.children) == 0, opnode, 'read takes no parameters.')
    
    elif len(opnode.children) == 1 and op == '-':
        check(opnode.children[0].ice9_type in ('bool', 'int'),
              opnode, 'incompatible type to unary operator %s' % op)
        check_and_set_type(opnode, opnode.children[0].ice9_type)
    
    elif len(opnode.children) == 1 and op == '?':
        check(opnode.children[0].ice9_type == 'bool', opnode, 
              'incompatible type to unary operator ?')
        check_and_set_type(opnode, 'int')
    
    elif op in ('<', '<=', '>', '>='):
        for c in opnode.children:
            check(c.ice9_type == 'int', opnode, 
                  "incompatible types to binary operator %s" % op)
        check_and_set_type(opnode, 'bool')
   
    elif op in ('/', '%'):
        for c in opnode.children:
            check(c.ice9_type == 'int', opnode,
                  "incompatible types to binary operator %s" % op)
        check_and_set_type(opnode, 'int')
    
    elif op in ('=', '!=', '-', '+', '*'):
        left, right = opnode.children[0:2]
        check(any(equivalent_types(left.ice9_type, t) for t in ('int', 'bool')),
              opnode,
              "incompatible types to binary operator %s" % op)
        
        check(equivalent_types(left.ice9_type, right.ice9_type),
              opnode,
              "incompatible types to binary operator %s" % op)
        if op == '=' or op == '!=':
            check_and_set_type(opnode, 'bool')
        else:
            check_and_set_type(opnode, opnode.children[0].ice9_type)
        
def array_reference(arrnode):
    vartype = first_definition(ice9_symbols, arrnode.value)
    assert vartype is not None
    vartype = expand_type(vartype)
    for c in arrnode.children:
        check(equivalent_types(c.ice9_type, 'int'), c, 
              "expressions for array dereference must evaluate to ints")
        check(vartype[0] == "array", c, "too many array dereferences in l-value")
        vartype = vartype[1]
    
    check_and_set_type(arrnode, vartype)

def assignment(setnode):
    cs = setnode.children
    
    check(cs[0].node_type == 'ident' or cs[0].node_type == 'array_reference',
          setnode, "Cannot assign to %s." % setnode.value)
    
    check(equivalent_types(cs[0].ice9_type, cs[1].ice9_type),
          setnode,
          "incompatible types to binary operator :=")
    
    check(first_definition(ice9_symbols, cs[0].value) != 'const',
          cs[0], "the fa variable (%s) cannot be written to in the loop body" % cs[0].value)
    
    check(expand_type(cs[1].ice9_type) in ("int", "bool", "str"),
          setnode,
          "binary operator := only defined for int, bool and str")

    check(expand_type(cs[0].ice9_type) in ("int", "bool", "str"),
          setnode,
          "binary operator := only defined for int, bool and str")
    
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
        define(ice9_symbols, procname, rettype)
    else:
        rettype = 'nil'
    proctype.insert(1, rettype)
    # check if we had a forward define it already.
    check_and_set_type(procnode, proctype)
    forward_defn_type = first_definition(ice9_procs, procname)
    if forward_defn_type is not None:
        check(type(forward_defn_type) == list and forward_defn_type[0] == 'forward',
              procnode,
              'proc %s is already defined' % procname)
        check(equivalent_types(proctype, forward_defn_type),
              procnode,
              "mismatch between forward and proc defns of %s" % procnode.value)
        forward_defn_type[0] = "proc"
        define(ice9_procs, procname, proctype)
    else:
        define(ice9_procs, procname, proctype)
    

def synthesized_proc(procnode):
    leave_scope()

def notype(node):
    check_and_set_type(node, 'nil')

def proc_call(pcnode):
    from itertools import izip_longest
    proctype = first_definition(ice9_procs, pcnode.value)
    check(proctype is not None, pcnode, "unknown proc %s" % pcnode.value)
        
    check(len(pcnode.children) == len(proctype[2:]),
          pcnode,
          "number of parameters mismatch in call to %s" % pcnode.value)
    for child, param in izip_longest(pcnode.children, proctype[2:]):
        check(equivalent_types(child.ice9_type, param),
              pcnode,
              "parameter type mismatch")
    
    check_and_set_type(pcnode, proctype[1])

def for_loop_inherited(fornode):
    add_scope()
    fornode.loopcount += 1
    varnode = fornode.children[0]
    assert varnode.node_type == 'ident'
    
    define(ice9_symbols, varnode.value, 'const')
    varnode.ice9_type = 'const'

def for_loop_synthesized(fornode):
    check_and_set_type(fornode, 'nil')
    check(equivalent_types(fornode.children[1].ice9_type, 'int'),
          fornode.children[1],
          'expressions in fa must evaluate to ints')
    check(equivalent_types(fornode.children[2].ice9_type, 'int'),
          fornode.children[2],
          'expressions in fa must evaluate to ints')
    
    leave_scope()

def do_loop_inherited(donode):
    donode.loopcount += 1

def do_loop(donode):
    check(equivalent_types(donode.children[0].ice9_type, 'bool'),
          donode.children[0],
          "if and do tests must evaluate to a boolean")

def cond(ifnode):
    for i in xrange(len(ifnode.children) / 2):
        check(equivalent_types(ifnode.children[2*i].ice9_type, 'bool'),
              ifnode.children[2*i],
              'if and do tests must evaluate to a boolean')
    
    check(len(ifnode.children) > 1, ifnode, 'if and do tests must evaluate to a boolean')


inherited_callbacks = {
    'define_type': define_type,
    'define': define_var,
    'proc': inherited_proc,
    'forward': forward,
    'for_loop': for_loop_inherited,
    'do_loop': do_loop_inherited,
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
    'for_loop': for_loop_synthesized,
    'do_loop': do_loop,
    'cond': cond
}

def semantic_helper(ast):
    if ast.parent is not None:
        ast.loopcount = ast.parent.loopcount
    
    if ast.node_type in inherited_callbacks:
        callback = inherited_callbacks[ast.node_type]
        callback(ast)
    
    for n in list(ast.children):
        semantic_helper(n)
    
    if ast.node_type in sythenisized_callbacks:
        callback = sythenisized_callbacks[ast.node_type]
        callback(ast)
    
    return True

def check_semantics(ast):
    global ice9_procs, ice9_types, ice9_symbols
    
    ice9_procs = [dict({
        'int': ['proc', 'int', ["param", "num", 'str']]
    })]

    ice9_types = [dict({
        'nil': 'base',
        'int': 'base',
        'str': 'base',
        'bool': 'base',
        'const': 'int',
    })]
    
    ice9_symbols = [ dict() ]
    
    ast.loopcount = 0
    
    retval = semantic_helper(ast)
    
    for k,v in ice9_procs[0].iteritems():
        check(type(v) == list and v[0] != 'forward',
              ast,
              'proc %s has no body' % k)
    
    
    return retval
    

if __name__ == '__main__':
    with file('test.txt') as f:
        ast = parse2ast(parse(f.read()))
        print ast
        print ""
        print ""
        print check_semantics(ast)
        print '%' * 80
        print ice9_procs
        print ""
        print ice9_types
        print ""
        print ice9_symbols
        print '-' * 80
        print ast