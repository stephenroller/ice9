#!/usr/bin/env

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

@transformation_rule
def value_or_assignment(va_node):
    if len(va_node.children) > 0:
        assignment_token = va_node.children.pop(0)
        assert assignment_token.value == ':='
        
        va_node.parent.children.remove(va_node)
        va_node.parent.children += va_node.children
        va_node.parent.node_type = 'assignment'
        va_node.parent.value = ':='


@transformation_rule
@collapsable
def if_prime(ifp_node):
    if ifp_node.children[0].value == '[]':
        ifp_node.children.pop(0)

@transformation_rule
def fi(fi_node):
    # first, let's get rid of that nasty -> token
    assert fi_node.children[1].value == '->'
    fi_node.children.pop(1)

@transformation_rule
def dec_list(dec_list_node):
    return
    
    new_children = []
    while len(dec_list_node.children) > 0:
        variable_name = dec_list_node.children.pop(0).value
        variable_type = dec_list_node.children.pop(0).value
        
        new_children.append(Tree(parent=dec_list_node.parent,
                                 node_type='variable',
                                 value=variable_name,
                                 ice9_type=variable_type
                                 ))
    dec_list_node.children = new_children

@transformation_rule
def proc_call(proc_call_node):
    p = proc_call_node.parent
    p.node_type = 'proc_call'
    p.value = p.children[0].value
    p.children = proc_call_node.children


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
                continue
            
            elif node.token_type in  ('string', 'int', 'bool'):
                # it's a literal
                node.node_type = 'literal'
                setattr(node, 'ice9_type', node.token_type)
                
                if node.ice9_type == 'string':
                    node.value = node.value[1:-1] # remove the quotes                
                elif node.ice9_type == 'int':
                    node.value = int(node.value) 
                elif node.ice9_type == 'bool':
                    if node.value == 'true':
                        node.value = True
                    elif node.value == 'false':
                        node.value = False
                
        elif node.node_type == 'rule-expansion':
            
            if len(node.children) == 0:
                # Empty node, let's just kill it and go onto the next
                node.kill()
                continue
            
            elif node.value in transform_rules:
                transform_rules[node.value](node)
            
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
                        p.children = node.children[1:]
                
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
                        p.children = [left, right]

    
    return parse_tree