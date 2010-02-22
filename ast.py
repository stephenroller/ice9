#!/usr/bin/env

"""
Used for converting a parse tree into an AST.
"""

from tree import Tree

transform_rules = dict()

def transformation_rule(trans):
    transform_rules[trans.func_name] = trans
    return trans


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

def parse2ast(parse_tree):
    """
    Converts a parse tree into an AST.
    """
    for node in list(parse_tree.postfix_iter()):
        if node.node_type == 'token':
            toktype, tokval = node.token_type, node.value
            if toktype in ('SOF', 'EOF', 'punc'):
                node.kill()
                continue
        elif node.node_type == 'rule-expansion':
            if node.value in transform_rules:
                transform_rules[node.value](node)
            
            if len(node.children) == 0:
                # Empty node, let's just kill it and go onto the next
                node.kill()
                continue
                
            elif len(node.children) == 1:
                # If it's a single expansion, just collapse the node
                #  a          a
                # / \        / \
                # b  c  ==> d   c
                # |
                # d
                node.value = node.children[0].value
                node.node_type = node.children[0].node_type
                node.children = node.children[0].children
            
            if len(node.children) == 2:
                UNARY_OPS = list('?-')
                BINARY_OPS = list('=+-*/%<>') + ['<=', '>=', '!=', ':=']
                
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
                        #  left  node      => left right
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