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
                try:
                    node.value = int(node.children[0].value)
                except ValueError:
                    node.value = 0
                node.children = []

def cond_elimination(ast):
    "Eliminates cond branches that will never execute."
    for node in list(ast.postfix_iter()):
        if node.node_type != 'cond':
            continue
        
        children = node.children
        i = 0
        while i < len(children):
            condition = children[i]
            if condition.value == True:
                # branch will always execute
                del children[i+2:]
                del children[i]
            elif condition.value == False:
                # dead branch, will never execute
                del children[i + 1]
                del children[i]
            else:
                i += 2
        
        if len(children) == 1:
            # we have an else
            node.become_child()
        
    
    return False

def remove_arithmetic_identities(ast):
    for node in list(ast.postfix_iter()):
        if node.node_type != 'operator' or len(node.children) != 2:
            continue
        
        left, right = node.children
        if left.node_type == 'literal':
            literal, dynamic = left, right
        elif right.node_type == 'literal':
            literal, dynamic = right, left
        else:
            # Neither must be a literal.
            continue
        
        if node.value in ('+', '-') and literal.value == 0:
            if node.value == '+' or right.value == 0:
                node.children = [dynamic]
                node.become_child()
            elif node.value == '-' and left.value == 0:
                node.children = [dynamic]
        elif node.value == '*':
            if literal.value == 0:
                node.children = [literal]
                node.become_child()
            elif literal.value == 1:
                node.children = [dynamic]
                node.become_child()
        elif node.value in ('%', '/'):
            if right.value == 0:
                from ice9 import Ice9Error
                raise Ice9Error(node.line, "Cannot divide by zero!")
            else:
                node.children = [literal]
                node.become_child()
        
                
        

def optimize_ast(ast):
    static_str_to_int(ast)
    constant_propagation(ast)
    remove_arithmetic_identities(ast)
    constant_propagation(ast)
    cond_elimination(ast)


if __name__ == '__main__':
    from ice9 import compile


    source = """
    if read > 3 ->
    write read * 1;
    fi
    """

    print compile(source, False)
    print "-" * 80
    print
    print compile(source, True)    