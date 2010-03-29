#!/usr/bin/env python

from semantic import first_definition

# REGISTERS
ZERO = 0 # always zero
AC1  = 1 # Accumulator 1
AC2  = 2 # Accumulator 2
AC3  = 3 # Accumulator 3
ST   = 4 # Temporary storage
FP   = 5 # points to the start of the frame
SP   = 6 # points to the top of the stack
PC   = 7 # points to the next instruction

# variable locations, done the same as in type checking
# a global stack of dictionaries.
variables = [{}]
# global dictionary of proc locations
procs = {}

# Code generation utilities -------------------------------------------------

def type9_size(ice9_type):
    """Returns the full size of the ice9 type in words."""
    return 1

def is_comment(inst5):
    "Returns whether this 'instruction' is just a comment."
    return type(inst5) is tuple and inst5[0] == 'comment'

def code_length(code5):
    """Returns the length of the code with comments removed."""
    return len([1 for inst5 in code5 if not is_comment(inst5)])

def push_register(reg, comment=None):
    """Creates code for pushing a register onto the stack."""
    if not comment:
        comment = 'Store reg %s on the stack' % reg
    return [('LDA', SP, -1, SP, 'Move (push) the stack pointer'),
            ('ST', reg, 0, SP, comment)]

def pop_register(reg, comment=None):
    """Creates code for popping a register off the stack."""
    if not comment:
        comment = 'Get reg %d off the stack' % reg
    return [('LD', reg, 0, SP, comment),
            ('LDA', SP, 1, SP, 'Move (pop) the stack pointer')]

def push_var(varname, vartype):
    """Allocates room for a variable on the stack."""
    return [('LDA', SP, - type9_size(vartype), SP, "Make room for %s on the stack" % varname)]

def comment(comment):
    """Makes a comment line."""
    return [('comment', 0, 0, 0, comment)]

def passthru(ast):
    """
    Code generated by this item is the sequential concatenation of its
    children. Useful for statements, etc.
    """
    from operator import add
    return reduce(add, [generate_code(c) for c in ast.children], [])

# NODE_TYPE RULES ---------------------------------------------------------

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
    childcode = generate_code(ast.children[0])
    if value.ice9_type == 'int':
        return childcode + [('OUT', AC1, 0, 0, 'writing int')]
    elif value.ice9_type == 'bool':
        return childcode + [('OUTB', AC1, 0, 0, 'writing bool')]
    else:
        raise ValueError("unimplmented")

def write(ast):
    """Handles write command (contains a newline)."""
    return writes(ast) + [('OUTNL', 0, 0, 0, 'newline for write')]

def ident(ast):
    varname = ast.value
    memloc, relreg = first_definition(variables, varname)
    return [('LD', AC1, memloc, relreg, 'Load %s to register 1' % varname)]

def assignment(ast):
    var, val = ast.children
    varname = var.value
    code5  = comment('ASSIGN to %s:' % varname) + generate_code(val)
    memloc, relreg = first_definition(variables, varname)
    code5 += [('ST', AC1, memloc, relreg, 'STORE variable %s' % varname)]
    code5 += comment('END ASSIGN TO %s' % varname)
    return code5

def program(ast):
    """Generates code for a whole program."""
    # make sure variable and proc locations are reset
    global variables, procs
    variables = [{}]
    procs = {}
    
    code5 = comment("PREAMBLE")
    # variable declarations:
    i = 1
    for var, type9 in ast.vars:
        code5 += [('alloc', type9_size(type9), 0, 0, var)]
        code5 += comment('DECLARE "%s"' % var)
        variables[0][var] = i, ZERO
        i += 1
    
    children = ast.children
    # general program code.
    while len(children) > 0 and children[0].node_type == 'proc':
        procnode = children.pop(0)
        procname = procnode.value
        proclocation = code_length(code5) + 1
        procs[procname] = proclocation
        code5 += generate_code(procnode)
        

    code5.insert(1, ('JEQ', ZERO, code_length(code5), PC, 
                        'skip variable and proc declarations'))
    
    # set the stack pointer
    code5 += [('LD', SP, ZERO, ZERO, 'Set the stack pointer')]
    
    code5 += comment("END PREAMBLE")
    code5 += comment("START OF PROGRAM")
           
    code5 += passthru(ast)
    
    code5 += comment('END OF PROGRAM')
    
    # we need to go back and add all our proc call jumps
    realcode5 = []
    for inst5 in code5:
        inst, r, s, t, com = inst5
        if inst == 'call':
            procname = r
            memloc = procs[procname]
            realcode5.append(('LDC', PC, memloc, ZERO, com))
        else:
            realcode5.append(inst5)
            
    code5 = realcode5
    return code5

# Binary operators ---------------------------------------------------------
def binary_operator(opinst, ast):
    """
    Generic binary operator handler. opinst should one of ADD, SUB, DIV or 
    MUL. ast is the AST including the operator node.
    """
    left, right = ast.children
    
    # Store the result of the left operand on the stack.
    code5  = generate_code(left)
    code5 += push_register(AC1)
    
    # store value of right operand is in AC1
    code5 += generate_code(right)
    
    # Get the left value off the stack and put it in AC2
    code5 += pop_register(AC2)
    
    # And add the two and store in AC1
    code5 += [(opinst, AC1, AC2, AC1, '%s left and right.' % opinst)]
    return code5

def add(ast):
    """Handles integer addition and boolean OR."""
    if ast.ice9_type == 'int':
        # integer addition
        return binary_operator('ADD', ast)
    else:
        assert ast.ice9_type == 'bool'
        # boolean OR
        left, right = ast.children
        leftcode = generate_code(left)
        rightcode = generate_code(right)
        
        code5  = comment('boolean OR')
        code5 += leftcode
        code5 += [('JNE', AC1, code_length(rightcode), PC, 'short circuit boolean OR')]
        code5 += rightcode
        code5 += comment('end boolean OR')
        return code5

def mul(ast):
    """Handles integer multiplication and boolean AND."""
    if ast.ice9_type == 'int':
        # integer multiplication
        return binary_operator('MUL', ast)
    else:
        # boolean AND
        assert ast.ice9_type == 'bool'
        left, right = ast.children
        leftcode = generate_code(left)
        rightcode = generate_code(right)
        
        code5  = comment('boolean AND')
        code5 += leftcode
        code5 += [('JEQ', AC1, code_length(rightcode), PC, 'short circuit boolean AND')]
        code5 += rightcode
        code5 += comment('end boolean AND')
        return code5

def div(ast):
    """Handles division."""
    return binary_operator('DIV', ast)

def sub(ast):
    """Handles both binary and unary subtraction."""
    if len(ast.children) == 1:
        if ast.ice9_type == 'int':
            # unary subtract, we really should just multiply by -1
            return generate_code(ast.children[0]) + comment('integer negation:') + [
                        ('LDC', AC2, -1, ZERO, 'Prepare to invert sign.'),
                        ('MUL', AC1, AC1, AC2, 'Invert sign.')
                    ]
        else:
            # boolean negation
            assert ast.ice9_type == 'bool'
            return generate_code(ast.children[0]) + comment('boolean negation:') + [
                        ('LDC', AC2, -1, ZERO, 'Prepare invert sign.'),
                        ('MUL', AC1, AC1, AC2, 'Invert sign.'),
                        ('LDA', AC1, 1, AC1, 'Convert back to boolean.')
                    ]
    else:
        # integer subtraction
        assert len(ast.children) == 2, "Subtract should only have two nodes"
        assert ast.ice9_type == 'int', "Must be integer subtraction"
        return binary_operator('SUB', ast)

def comparison(comparenode):
    jumpinstrs = {'=': 'JEQ', '!=': 'JNE', 
                  '>': 'JGT', '>=': 'JGE', 
                  '<': 'JLT', '<=': 'JLE'}
    
    op = comparenode.value
    inst = jumpinstrs[op]
    
    code5  = comment("BEGIN COMPARISON %s" % op)
    code5 += binary_operator('SUB', comparenode)
    code5 += [
        (inst, AC1, 1, PC, 'skip set to false'),
        ('LDC', AC1, 0, 0, 'comparison is bad, set reg 1 to false'),
        ('JEQ', ZERO, 1, PC, 'skip set to true'),
        ('LDC', AC1, 1, 0, 'compairson is good, set reg 1 to true'),
    ]
    code5 += comment("END COMPARISON %s" % op)
    return code5

# end binary operators ------------------------------------------------------

# condition code ----------------------------------------------------------
def cond(ast):
    children = ast.children
    
    code5 = []
    
    while len(children) > 1:
        cond = children.pop(0)
        dothen = children.pop(0)
        
        stmtcode = generate_code(dothen)
        condcode = generate_code(cond)
        
        code5 += comment('IF condition:')
        code5 += condcode
        code5 += [('JEQ', AC1, code_length(stmtcode) + 1, PC, 'if false, jump to next cond')]
        code5 += comment('IF was true, THEN:')
        code5 += stmtcode
        code5 += ['jumpend']
        
    if len(children) == 1:
        stmtcode = generate_code(children.pop(0))
        code5 += comment("ELSE:") + stmtcode
    
    # total number of instructions with comments excluded
    codecount = code_length(code5)
    
    # need to go back and replace our jump labels with the real instruction offsets
    realcode5 = []
    i = 0
    for inst5 in code5:
        if inst5 == 'jumpend':
            # label telling us to jump to the end of the statement
            numleft = codecount - i - 1
            realcode5.append(('JEQ', ZERO, numleft, PC, 'jump to end of if-then-else'))
        else:
            realcode5.append(inst5)
        
        if not is_comment(code5):
            i += 1

    code5 = realcode5
    
    return code5

def do_loop(ast):
    cond, stmt = ast.children
    condcode = generate_code(cond)
    stmtcode = generate_code(stmt)
    
    code5  = comment('BEGIN DO COND')
    code5 += condcode
    code5 += [('JEQ', AC1, code_length(stmtcode) + 1, PC, 'jump if do cond is false')]
    code5 += comment('cond true, DO:')
    code5 += stmtcode
    code5 += [('JEQ', ZERO, -code_length(condcode + stmtcode) - 2, PC, 
                      'End of DO, go back to beginning')]
    
    return code5

# proc stuff ---------------------------------------------------------------

# memory representation
# +-------------------------------------------------------------------------------+
# | program... | ... | var2 | var1| retval | retaddr | param1 | p2 | lastfp | ... |
# +-------------------------------------------------------------------------------+
#                    ^                     ^                       ^              ^
#                    sp                    fp          fp + fpoffset           dmem

def proc(procnode):
    global variables
    variables.insert(0, {})
    
    children = procnode.children
    procname = procnode.value
    body = children.pop(-1)
    
    code5  = comment('BEGIN PROC %s' % procname)
    code5 += [('LDA', FP, 0, SP, 'Set frame pointer')]
    
    # set memory locations of params
    fpoffset = 1 
    for p in children:
        paramname = p.value
        paramloc = fpoffset
        variables[0][paramname] = (fpoffset, FP)
        fpoffset += type9_size(fpoffset)
    
    # set memory locations of local variables
    vars = procnode.vars
    if procnode.ice9_type != 'nil':
        vars.insert(0, (procname, procnode.ice9_type))
    
    i = 0
    for var, type9 in procnode.vars:
        code5 += push_var(var, type9)
        i += type9_size(type9)
        variables[0][var] = (- i, FP)
    
    # generate code of proc
    code5 += generate_code(body)
    
    if procnode.ice9_type != 'nil':
        # handle return value
        code5 += [('LD', AC1, -1, FP, 'Store the return value in AC1')]
    
    code5 += pop_register(AC2, 'pop return address')
    
    code5 += [('LDA', SP, fpoffset, FP, 'Pop off local values from the stack')]
    code5 += [('LD', PC, 0, FP, 'Moving return address into PC')]
    code5 += comment('END PROC %s' % procname)
    
    variables.pop(0)
    return code5

def proc_call(pcnode):
    # push the return address
    procname = pcnode.value
    code5  = comment('BEGIN PROC CALL %s' % procname)
    code5 += push_register(FP, 'store the frame pointer before the call')
    
    params = pcnode.children # calling parameters
    params.reverse() # we want to push on in reverse so they'll be in order in mem
    for p in params:
        code5 += generate_code(p)
        code5 += push_register(AC1, 'push parameter')
    
    code5 += [('LDA', AC2, 3, PC, 'Store return address in AC2')]
    code5 += push_register(AC2, 'store the return address')
    code5 += [('call', procname, 0, 0, 'CALL %s' % procname)]
    code5 += pop_register(FP, 'pop the frame pointer after call')
    code5 += comment('END PROC CALL %s' % procname)
    return code5

# core algorithm ---------------------------------------------------------

# the repeated callback paradigm
callbacks = {
    'literal': literal,
    'write': write,
    'writes': writes,
    'program': program,
    'statements': passthru,
    '+': add,
    '*': mul,
    '/': div,
    '-': sub,
    '?': passthru,
    'cond': cond,
    'do_loop': do_loop,
    'ident': ident,
    'assignment': assignment,
    '=': comparison,
    '!=': comparison,
    '<': comparison,
    '<=': comparison,
    '>': comparison,
    '>=': comparison,
    'proc': proc,
    'proc_call': proc_call,
}

def generate_code(ast):
    """
    Generates a list of 5-tuples describing instructions for TM code of the form
        (inst, r, s, t, comment)
    """
    def noop(ast):
        # returns empty code
        return comment('NOOP')
    
    code5 = []
    if ast.node_type == 'operator':
        cb = callbacks.get(ast.value, noop)
    else:
        cb = callbacks.get(ast.node_type, noop)
    
    # code 5 because callbacks return 5-tuples.
    setattr(ast, 'code5', cb(ast)) 
    return ast.code5

# STRING OUTPUT ------------------------------------------------------------

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
            output.append("%5d: %-9s %d,%2d(%d)\t\t%s" % (ln, inst, r, s, t, com))
        elif inst in ('HALT', 'IN', 'OUT', 'INB', 'OUTB', 'OUTC', 
                      'ADD', 'SUB', 'MUL', 'DIV', 'OUTNL'):
            ln = linecounter.next()
            output.append("%5d: %-9s %d,%2d,%2d\t\t%s" % (ln, inst, r, s, t, com))
        elif inst == 'alloc':
            size = r
            for i in xrange(0, size):
                ln = linecounter.next()
        elif inst == 'comment':
            output.append("* %s" % com)
        else:
            raise ValueError("Can't print this instruction: %s" % inst)

    return "\n".join(output)

def generate_code_str(ast):
    """Shorthand for creating the TM string code for the ast."""
    return code5str(generate_code(ast))

# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from ice9 import compile
    source = file('test.9').read()
    print compile(source)
