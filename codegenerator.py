#!/usr/bin/env python

# REGISTERS
ZERO = 0 # always zero
AC1  = 1 # Accumulator 1
AC2  = 2 # Accumulator 2
AC3  = 3 # Accumulator 3
AC4  = 4 # Accumulator 4
FP   = 5 # points to the start of the frame
SP   = 6 # points to the top of the stack
PC   = 7 # points to the next instruction

def code4str(code4):
    """Converts from code4 to something actually usuable by TM."""
    output = []
    for inst4 in code4:
        inst, a, b, c = inst4
        if inst in ('LDC', 'LDA', 'LD', 'ST', 'JLT', 'JLE', 'JEQ', 
                    'JNE', 'JGE', 'JGT'):
            output.append("%3s %d, %d(%d)" % inst4)
        elif inst in ('HALT', 'IN', 'OUT', 'INB', 'OUTB', 'OUTC', 
                      'ADD', 'SUB', 'MUL', 'DIV', 'OUTNL'):
            output.append("%3s %d, %d, %d" % inst4)
        elif inst == 'comment':
            output.append("* %s" % a)
        else:
            raise ValueError("Can't print this instruction: %s" % inst)
        
    return "\n".join("%d: %s" % (i, x) for i, x in enumerate(output))

# NODE_TYPE RULES ------------

def literal(ast):
    if ast.ice9_type == 'int' or ast.ice9_type == 'bool':
        return [('LDC', AC1, int(ast.value), ZERO)]

def writes(ast):
    value = ast.children[0]
    if value.ice9_type == 'int':
        return [('OUT', AC1, ZERO, ZERO)]

def write(ast):
    return writes(ast) + [('OUTNL', ZERO, ZERO, ZERO)]

# the repeated callback paradigm
callbacks = {
    'literal': literal,
    'write': write,
    'writes': writes,
}

def generate_code(ast):
    """
    Generates a list of 4-tuples describing instructions for TM code.
    """
    from operator import add
    
    def noop(ast):
        # returns empty code
        return []
    
    code4 = []
    for node in ast.postfix_iter():
        if node.node_type == 'operator':
            cb = callbacks.get(node.value, noop)
        else:
            cb = callbacks.get(node.node_type, noop)
        
        # code 4 because callbacks return 
        setattr(node, 'code4', cb(node)) 
        code4 += node.code4
    
    return code4str(code4)

if __name__ == '__main__':
    from ice9 import compile
    source = file('test.9').read()
    print compile(source)
