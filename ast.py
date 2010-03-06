#!/usr/bin/env python

"""
Used for converting a parse tree into an AST.
"""

from tree import Tree

# global dictionary of transformation rules
transform_rules = dict()

# lispy functions to help with the various transformations ------------------

def transformation_rule(trans):
    """
    Marks the rule as a transformation from the parse tree to the AST.
    """
    transform_rules[trans.func_name] = trans
    return trans

def collapsable(rule):
    def _modified_rule(node):
        rule(node)
        
        if len(node.children) == 1:
            # If it's a single expansion, just collapse the node
            #  a          a
            # / \        / \
            # b  c  ==> d   c
            # |
            # d
            node.become_child()
    
    # make sure we properly emulate the original function
    _modified_rule.func_name = rule.func_name
    # and return the rule that checks for collapsing
    return _modified_rule

# begin our transformations ------------------------------------------------

# basic rules we just want to collapse if they have a single child. 

@transformation_rule
@collapsable
def root(n):
    # The root node is unnecessary at this point. It should always have a 
    # program rule underneath it. Let's just collapse it.
    pass

@transformation_rule
@collapsable
def stm(n):
    pass

@transformation_rule
@collapsable
def med(n):
    pass

@transformation_rule
@collapsable
def high(n):
    pass

@transformation_rule
@collapsable
def end(n):
    pass

@transformation_rule
@collapsable
def low(n):
    pass

@transformation_rule
@collapsable
def expr(n):
    pass

@transformation_rule
def stms(n):
    n.node_type = 'statements'
    n.value = ''

@transformation_rule
def program(n):
    n.node_type = 'program'
    n.value = ''


# Now for the more complicated rules

UNARY_OPS = list('?-')
BINARY_OPS = list('=+-*/%<>') + ['<=', '>=', '!=']

# let's go ahead and handle these transformations now

# arrays
@transformation_rule
def lvalue_prime(lvp_node):
    if lvp_node.parent.value == 'lvalue_prime':
        # If this is a multidimensional array, just collapse it with the
        # parent
        lvp_node.become_child()
        pass
    else:
        # now we're either a singledimensional array, or we've collapsed
        # all the dimensions into one list. Either way, we need to usurp the
        # token
        lvp_node.adopt_left_sibling()
        lvp_node.node_type = 'array_reference'
        name = lvp_node.children.pop(0)
        lvp_node.value = name.value

# assignment
@transformation_rule
def value_or_assignment(va_node):
    if len(va_node.children) > 0:
        assert va_node.children.pop(0).value == ':='
        
        va_node.parent.children.remove(va_node)
        va_node.parent.children += va_node.children
        va_node.parent.node_type = 'assignment'
        va_node.parent.value = ':='


# if / if else / if else if rules
@transformation_rule
def ice9_if(if_node):
    assert if_node.children.pop(0).value == 'if'
    assert if_node.children.pop(1).value == '->'
    assert if_node.children.pop(-1).value == 'fi'
    if_node.node_type = 'cond'
    if_node.value = ''

@transformation_rule
@collapsable
def if_prime(ifp_node):
    if ifp_node.children[0].value == '[]':
        ifp_node.children.pop(0)
        ifp_node.remove_and_promote()

@transformation_rule
@collapsable
def fi(fi_node):
    # first, let's get rid of that nasty -> token
    assert fi_node.children.pop(1).value == '->'
    
    if fi_node.children[0].value == 'else':
        # remove the else
        fi_node.children.pop(0)
        pass
    
    fi_node.remove_and_promote()

# fa and do
@transformation_rule
def fa(fa_node):
    assert fa_node.children.pop(0).value == 'fa'
    assert fa_node.children.pop(1).value == ':='
    assert fa_node.children.pop(2).value == 'to'
    assert fa_node.children.pop(3).value == '->'
    assert fa_node.children.pop(-1).value == 'af'
    fa_node.node_type = 'for_loop'
    fa_node.value = ''

@transformation_rule
def ice9_do(do_node):
    assert do_node.children.pop(0).value == 'do'
    assert do_node.children.pop(1).value == '->'
    assert do_node.children.pop(-1).value == 'od'
    do_node.node_type = 'do_loop'
    do_node.value = ''

# declaration list

@transformation_rule
def dec_list(dec_list_node):
    if dec_list_node.parent.value != 'dec_list':
        for c in list(dec_list_node.children):
            if c.node_type == 'rule-expansion' and c.value == 'id_list':
                param = c.children[0]
                param.node_type = 'param'
                c.remove_and_promote()
                param.adopt_right_sibling()
    
    dec_list_node.remove_and_promote()

# proc call

@transformation_rule
def forward(fnode):
    assert fnode.children.pop(0).value == 'forward'
    namenode = fnode.children.pop(0)
    assert namenode.node_type == 'ident'
    fnode.node_type = 'forward'
    fnode.value = namenode.value
    if len(fnode.children) >= 2 and fnode.children[-1].node_type == 'type':
        fnode.children.insert(0, fnode.children.pop(-1))
    

@transformation_rule
def proc_call(proc_call_node):
    p = proc_call_node.parent
    p.node_type = 'proc_call'
    p.value = p.children[0].value
    p.children = proc_call_node.children

@transformation_rule
def type_id(t_node):
    t_node.node_type = 'type'
    t_node.value = t_node.children.pop(0).value
    siblings = t_node.parent.children
    myindex = siblings.index(t_node)
    for right_sibling in list(siblings[myindex+1:]):
        if (right_sibling.node_type == 'literal' and 
            right_sibling.ice9_type == 'int'):
                t_node.children.append(right_sibling)
                right_sibling.parent = t_node
                siblings.remove(right_sibling)
        else:
            break

@transformation_rule
def ice9_type(type_node):
    type_node.node_type = 'define_type'

    assert type_node.children.pop(0).value == 'type'
    name = type_node.children.pop(0)
    assert name.node_type == 'ident'
    type_node.value = name.value
    assert type_node.children.pop(0).value == '='

@transformation_rule
def var(var_node):
    assert var_node.children.pop(0).value == 'var'
    var_lists = var_node.children
    var_node.children = []
    for vl_node in var_lists:
        id_list = vl_node.children.pop(0)
        # type
        type_info = vl_node.children
        assert type_info[0].node_type == 'type'
        vl_node.children = []
        assert id_list.value == 'id_list'
        for def_id in id_list.children:
            assert def_id.node_type == 'ident'
            var_node.add_child(node_type = 'define',
                               value = def_id.value,
                               children = type_info[:]
                               )
    
    var_node.remove_and_promote()
    

@transformation_rule
@collapsable
def var_list(vl_node):
    n = vl_node
    while n.value != 'var':
        n = n.parent
    
    vl_node.parent.children.remove(vl_node)
    n.children.append(vl_node)
    vl_node.parent = n

# proc definition

@transformation_rule
def proc(proc_node):
    assert proc_node.children.pop(0).value == 'proc'
    ident = proc_node.children.pop(0)
    assert ident.node_type == 'ident'
    proc_node.node_type = 'proc'
    proc_node.value = ident.value
    
    # first child is left as type and second as statements
    if len(proc_node.children) >= 2 and proc_node.children[-2].node_type == 'type':
        proc_node.children.insert(0, proc_node.children.pop(-2))

@transformation_rule
def proc_prime(pp_node):
    pp_node.remove_and_promote()

@transformation_rule
def proc_end(pe_node):
    assert pe_node.children.pop(-1).value == 'end'
    pe_node.node_type = 'statements'
    pe_node.value = ''

# ---------------------------------------------------------------------------

# Handles the driving logic of changing a parse tree into an AST

def parse2ast(parse_tree):
    """
    Converts a parse tree into an AST.
    """
    for node in list(parse_tree.postfix_iter()):
        if node.node_type == 'token':
            if node.token_type in ('SOF', 'EOF', 'punc'):
                # go ahead and filter unncessary punctuation tokens
                node.kill()
            
            elif node.token_type in ('str', 'int', 'bool'):
                # it's a literal
                node.node_type = 'literal'
                setattr(node, 'ice9_type', node.token_type)
                
                if node.ice9_type == 'str':
                    node.value = node.value[1:-1] # remove the quotes                
                elif node.ice9_type == 'int':
                    node.value = int(node.value) 
                elif node.ice9_type == 'bool':
                    if node.value == 'true':
                        node.value = True
                    elif node.value == 'false':
                        node.value = False
            
            elif node.token_type == 'ident':
                node.node_type = 'ident'
            
            elif node.value in ('write', 'writes', 'break', 'exit', 'return'):
                node.parent.node_type = 'operator'
                node.parent.value = node.value
                assert node.parent.children.pop(0) == node
                
        elif node.node_type == 'rule-expansion':
            if len(node.children) == 0:
                # Empty node, let's just kill it and go onto the next
                node.kill()
                continue
            
            elif len(node.children) == 2:
                
                # Let's check for unary ops
                if (node.children[0].node_type == 'token' and
                    node.children[0].value in UNARY_OPS and
                    node.parent.node_type == 'rule-expansion' and
                    len(node.parent.children) == 1):
                        #  node.parent         op
                        #     |                |
                        #    node       =>     right
                        #    /  \
                        #  op   right
                        p = node.parent
                        op = node.children[0].value
                        p.node_type = 'operator'
                        p.value = op
                        p.line = node.children[0].line
                        p.children = node.children[1:]
                        for n in p.children:
                            n.parent = p
                        continue
                
                # let's check for those binary operators
                elif (node.children[0].node_type == 'token' and 
                      node.children[0].value in BINARY_OPS and
                      node.parent.node_type == 'rule-expansion' and
                      len(node.parent.children) == 2):
                        #   node.parent          op                      
                        #     /  \              /  \
                        #  left  node    =>   left right
                        #         / \
                        #       op   right
                        p = node.parent
                        left = node.parent.children[0]
                        right = node.children[1]
                        op = node.children[0].value
                        p.node_type = 'operator'
                        p.value = op
                        p.line = node.children[0].line
                        p.children = [left, right]
                        left.parent = p
                        right.parent = p
                        continue
            
            if node.value in transform_rules:
                transform_rules[node.value](node)
            

    return parse_tree