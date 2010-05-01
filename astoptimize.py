import operator

def sub_(*L):
    if len(L) == 2:
        return operator.sub(*L)
    else:
        return operator.neg(*L)

bool_operators = {
    '+': operator.or_,
    '*': operator.and_,
    '?': int,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
    '!=': operator.ne,
    '=': operator.eq,
}

int_operators = {
    '+': operator.add,
    '-': sub_,
    '*': operator.mul,
    '/': operator.div,
    '%': operator.mod,
}

def constant_propagation(ast):
    for node in list(ast.postfix_iter()):
        if node.node_type != 'operator':
            continue
        
        all_literals = True
        for c in node.children:
            all_literals = all_literals and c.node_type == 'literal'
        
        if not all_literals:
            # can't do constant propagation
            continue
        
        operator = node.value
        func = None
        if node.ice9_type == 'int':
            func = int_operators.get(operator, None)
        elif node.ice9_type == 'bool':
            func = bool_operators.get(operator, None)
        
        if not func:
            continue
        
        operands = [c.value for c in node.children]
        node.node_type = 'literal'
        node.value = func(*operands)
        node.children = []

def static_str_to_int(ast):
    for node in list(ast.postfix_iter()):
        if (node.node_type == 'proc_call' and node.value == 'int' and
            node.children[0].node_type == 'literal'):
                # can get away with converting this string at compile time.
                node.node_type = 'literal'
                node.value = int(node.children[0].value)
                node.children = []

def optimize_ast(ast):
    static_str_to_int(ast)
    constant_propagation(ast)

if __name__ == '__main__':
    from ice9 import compile
    print compile("write int('4') + 3 + int('8');")