#!/usr/bin/env python

# REGISTERS
ZERO = 0 # always zero
AC1  = 1 # Accumulator 1
AC2  = 2 # Accumulator 2
AC3  = 3 # Accumulator 3
ST   = 4 # Temporary storage
FP   = 5 # points to the start of the frame
SP   = 6 # points to the top of the stack
PC   = 7 # points to the next instruction

def code5str(code5):
    """Converts from code5 to something actually usuable by TM."""
    from itertools import count
    output = []
    linecounter = count()
    for inst5 in code5:
        inst, r, s, t, com = inst5
        if inst in ('LDC', 'LDA', 'LD', 'ST', 'JLT', 'JLE', 'JEQ', 
                    'JNE', 'JGE', 'JGT'):
            ln = linecounter.next() # line number
            output.append("%5d: %-9s %d,%d(%d)\t%s" % (ln, inst, r, s, t, com))
        elif inst in ('HALT', 'IN', 'OUT', 'INB', 'OUTB', 'OUTC', 
                      'ADD', 'SUB', 'MUL', 'DIV', 'OUTNL'):
            ln = linecounter.next()
            output.append("%5d: %-9s %d,%d,%d\t\t%s" % (ln, inst, r, s, t, com))
        elif inst == 'comment':
            output.append("* %s" % com)
        else:
            raise ValueError("Can't print this instruction: %s" % inst)
        
    return "\n".join(output)

# NODE_TYPE RULES ------------
def comment(comment):
    """Makes a comment line."""
    return [('comment', 0, 0, 0, comment)]

def literal(ast):
    """Generates code for literal constants."""
    if ast.ice9_type == 'int' or ast.ice9_type == 'bool':
        return [('LDC', AC1, int(ast.value), 0, 'load constant: %s' % ast.value)]
    elif ast.ice9_type == 'str':
        # TODO: implement strings
        pass

def writes(ast):
    """Handles writing to output."""
    value = ast.children[0]
    if value.ice9_type == 'int':
        return [('OUT', AC1, 0, 0, 'writing int')]
    elif value.ice9_type == 'bool':
        return [('OUTB', AC1, 0, 0, 'writing bool')]
        return comment('writing bool')
    else:
        raise ValueError("unimplmented")

def write(ast):
    """Handles write command (contains a newline)."""
    return writes(ast) + [('OUTNL', 0, 0, 0, 'newline for write')]

def program(ast):
    return comment('END OF PROGRAM')

# the repeated callback paradigm
callbacks = {
    'literal': literal,
    'write': write,
    'writes': writes,
    'program': program,
}

def generate_code(ast):
    """
    Generates a list of 5-tuples describing instructions for TM code of the form
        (inst, r, s, t, comment)
    """
    from operator import add
    
    def noop(ast):
        # returns empty code
        return []
    
    code5 = []
    for node in ast.postfix_iter():
        if node.node_type == 'operator':
            cb = callbacks.get(node.value, noop)
        else:
            cb = callbacks.get(node.node_type, noop)
        
        # code 5 because callbacks return 5-tuples.
        setattr(node, 'code5', cb(node)) 
        code5 += node.code5
    
    return code5str(code5)

if __name__ == '__main__':
    from ice9 import compile
    source = file('test.9').read()
    print compile(source)
