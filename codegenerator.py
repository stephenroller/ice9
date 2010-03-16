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

# the repeated callback paradigm
callbacks = {}

def generate_rule(rule):
    callbacks[rule.func_name] = rule

@generate_rule
def literal(ast):
    if ast.ice9_type == 'int' or ast.ice9_type == 'bool':
        return [('LDC', AC1, int(ast.value), ZERO)]

def noop(ast):
    return []

def code4str(code4):
    """Converts from code4 to something actually usuable by TM."""
    output = []
    for inst, a, b, c in code4:
        if inst in ('LDC', 'LDA', 'LD', 'ST', 'JLT', 'JLE', 'JEQ', 
                    'JNE', 'JGE', 'JGT'):
            output.append("%3s %d, %d(%d)" % (inst, a, b, c))
        elif inst in ('HALT', 'IN', 'OUT', 'INB', 'OUTB', 'OUTC', 
                      'ADD', 'SUB', 'MUL', 'DIV'):
            output.append("%3s %d, %d, %d")
        elif inst == 'comment':
            output.append("* %s" % a)
        else:
            raise ValueError("Can't print this instruction: %s" % inst)
        
    return "\n".join("%d: %s" % (i, x) for i, x in enumerate(output))

def generate_code(ast):
    """
    Generates a list of 4-tuples describing instructions for TM code.
    """
    from operator import add
    
    for node in ast.postfix_iter():
        cb = callbacks.get(node.node_type, noop)
        # code 4 because callbacks return 
        setattr(node, 'code4', cb(node)) 
    
    code4 = reduce(add, (n.code4 for n in node.prefix_iter()))
    
    return code4str(code4)


if __name__ == '__main__':
    from ice9 import compile
    source = file('test.9').read()
    print compile(source)
