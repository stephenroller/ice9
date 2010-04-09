    #!/usr/bin/env python

from semantic import first_definition
from itertools import izip

# REGISTERS
ZERO = 0 # always zero
AC1  = 1 # Accumulator 1
AC2  = 2 # Accumulator 2
AC3  = 3 # Accumulator 3
AC4  = 4 # Accumulator 4
FP   = 5 # points to the start of the frame
SP   = 6 # points to the top of the stack
PC   = 7 # points to the next instruction

activation_record_size = [0]

# variable locations, done the same as in type checking
# a global stack of dictionaries.
variables = [{}]
# global dictionary of proc locations
procs = {}

# Code generation utilities -------------------------------------------------

def type9_size(ice9_type):
    """Returns the full size of the ice9 type in words."""
    size = 1
    while type(ice9_type) is list and ice9_type[0] == "array":
        size *= ice9_type[2]
        ice9_type = ice9_type[1]
    return size

def memlookup(varname, ast):
    """
    Returns a tuple (code5, memloc, relreg) meaning after code5,
    varname will be in memory[memloc + reg[relreg]].
    """
    code5 = []
    memloc, relreg = first_definition(variables, varname)
    
    if ast and len(ast.children) > 0:
        # array reference. We need to do all our index calculations and such
        p = ast.parent
        while True:
            if hasattr(p, 'vars') and any(x == varname for x, t in p.vars):
                break
            else:
                p = p.parent
        
        arrayindexes = []
        vartype = dict(p.vars)[varname]
        while type(vartype) is list and vartype[0] == "array":
            arrayindexes.append(vartype[2])
            vartype = vartype[1]
        
        code5 += comment('%s is an array of size %s' % (varname, arrayindexes))
        
        from tree import Tree
        fakeast = Tree(node_type='operator', value='write')
        fakeast.children = [Tree(node_type='literal', value='Arrays bounds violation', ice9_type='str')]
        failcode  = comment('Array out of bounds error code:')
        failcode += generate_code(fakeast)
        failcode += [('HALT', 0, 0, 0, 'Array out of bounds')]
        failcode += comment('End array out of bounds error code')
        
        indexcode  = comment('Calculating memory location:')
        
        if relreg == FP:
            # we're in a proc, so what we have is a pointer that we'll
            # still need to dereference again
            indexcode += [('LD', AC4, memloc, relreg, 'Go ahead and dereference %s' % varname)]
            memloc, relreg = 0, AC4
        else:
            # we're just in the main body, so we already know the
            # direct location of the array.
            indexcode += [('LDA', AC4, memloc, relreg, 'Start array indexing at 0')]
            memloc, relreg = 0, AC4
        
        iteration = izip(ast.children, arrayindexes, arrayindexes[1:] + [1])
        for indexast, dimension_size, mul_size in iteration:
            indexcode += push_register(AC4, "Pushing array address to stack")
            indexcode += generate_code(indexast)
            indexcode += pop_register(AC4, "Popping array address from stack")
            jumpsize = code_length(failcode + indexcode)
            indexcode += [('JLT', AC1, - jumpsize - 1, PC, 'Check index >= 0'),
                          ('LDA', AC1, - dimension_size, AC1, 'Prepare for dimension check'),
                          ('JGE', AC1, - jumpsize - 3, PC, 'Check index < size'),
                          ('LDA', AC1, dimension_size, AC1, 'Undo dimension check'),
                          ('LDC', AC2, mul_size, 0, 'Prepare for dimension multiply'),
                          ('MUL', AC2, AC2, AC1, 'Multiply index * arraysize'),
                          ('ADD', AC4, AC4, AC2, 'Add this increment to our offset.')]
        
        code5 += [('JEQ', ZERO, code_length(failcode), PC, 'Skip array out of bounds failure.')]
        code5 += failcode
        code5 += indexcode
    
    return code5, memloc, relreg

def is_comment(inst5):
    "Returns whether this 'instruction' is just a comment."
    return type(inst5) is tuple and inst5[0] in ('comment', 'string', 'data')

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
        heapsize = activation_record_size[-1]
        address = heapsize
        heapsize += len(ast.value) + 1
        activation_record_size[-1] = heapsize
        return [('string', ast.value, 0, 0, 'string literal'),
                ('LDC', AC1, address, 0, 'Load pointer to string into memory.')]

def writes(ast):
    """Handles writing to output."""
    value = ast.children[0]
    valuecode = generate_code(value)
    
    if value.ice9_type in ('int', 'bool'):
        return valuecode + [('OUT', AC1, 0, 0, 'writing int')]
    elif value.ice9_type == 'str':
        return valuecode + push_register(AC2) + [
            ('LD', AC2, 0, AC1, 'Load next character into memory.'),
            ('JEQ', AC2, 3, PC, 'If we find the null terminator, stop.'),
            ('OUTC', AC2, 0, 0, 'Output the character'),
            ('LDA', AC1, 1, AC1, 'Increment character pointer'),
            ('JEQ', ZERO, -5, PC, 'Continue until null terminator')
        ] + pop_register(AC2)
    
    return valuecode

def write(ast):
    """Handles write command (contains a newline)."""
    return writes(ast) + [('OUTNL', 0, 0, 0, 'newline for write')]

def read(ast):
    return [('IN', AC1, 0, 0, 'Read input from command line.')]

def return9(returnnode):
    return [('return', 0, 0, 0, 'return')]

def exit9(exitnode):
    return [('exit', 0, 0, 0, 'exit')]

def break9(breaknode):
    return [('break', 0, 0, 0, 'break')]

def ident(ast):
    varname = ast.value
    code5, memloc, relreg = memlookup(varname, ast)
    if type(ast.ice9_type) is list and ast.ice9_type[0] == "array":
        code5 += [('LDA', AC1, memloc, relreg, 'Load pointer to %s in register 1' % varname)]
    elif relreg == SP or relreg == FP or relreg == ZERO or relreg == AC4:
        code5 += [('LD', AC1, memloc, relreg, 'Load %s to register 1' % varname)]
    else:
        code5 += [('LDA', AC1, memloc, relreg, 'Load %s to register 1' % varname)]
    
    return code5

def assignment(ast):
    var, val = ast.children
    varname = var.value
    lookupcode5, memloc, relreg = memlookup(varname, var)
    
    code5  = comment('ASSIGN to %s:' % varname) + generate_code(val)
    code5 += push_register(AC1, 'saving the set value to the stack')
    code5 += lookupcode5
    code5 += pop_register(AC1, 'getting the set value off the stack')
    code5 += [('ST', AC1, memloc, relreg, 'STORE variable %s' % varname)]
    code5 += comment('END ASSIGN TO %s' % varname)
    return code5

def program(ast):
    """Generates code for a whole program."""
    # make sure variable and proc locations are reset
    global variables, procs, activation_record_size
    variables = [{}]
    procs = {}
    
    code5 = comment("PREAMBLE")
    code5 += [('LD', SP, ZERO, ZERO, 'Set the stack pointer'),]
    # variable declarations:
    address = 1
    for var, type9 in ast.vars:
        variables[0][var] = address, ZERO
        address += type9_size(type9)
        code5 += comment('DECLARE "%s" (size: %s)' % (var, type9_size(type9)))
        code5 += [('data', 0, 0, 0, '%s initialization' % var)] * type9_size(type9)
    
    activation_record_size = [address]
    
    proccode5 = []
    children = ast.children
    # general program code.
    while len(children) > 0 and children[0].node_type == 'proc':
        procnode = children.pop(0)
        procname = procnode.value
        proclocation = code_length(proccode5) + 2
        procs[procname] = proclocation
        proccode5 += generate_code(procnode)
        
    if len(proccode5) > 0:
        code5 += [('JEQ', ZERO, code_length(proccode5), PC, 'skip proc definitions')]
    
    code5 += comment("END PREAMBLE")
    
    if len(proccode5) > 0:    
        code5 += comment("BEGIN PROCS")
        code5 += proccode5
        code5 += comment("END PROCS")
    
    code5 += comment("START OF PROGRAM")
    
    code5 += passthru(ast)
    
    # handle all remaining exits and returns
    code5 += [('HALT', 0, 0, 0, 'END OF PROGRAM')]
    codelen = code_length(code5)
    instno = 0
    for i, inst5 in enumerate(code5):
        if is_comment(inst5):
            continue
        
        if inst5[0] == "return" or inst5[0] == "exit":
            code5[i] = ('JEQ', ZERO, codelen - instno - 2, PC, 'early exit!')
        instno += 1
    
    
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

def modulus(modnode):
    # a % b = c => a - (a / b * b) = c
    left, right = modnode.children
    leftcode, rightcode = generate_code(left), generate_code(right)
    code5  = comment("Begin modulus")
    code5 += leftcode
    code5 += push_register(AC1, "Store left mod operand")
    code5 += rightcode
    code5 += pop_register(AC2, "Restore left mod operator")
    code5 += push_register(AC4, "Store old AC4 for modulus calculation")
    # AC1 = b, AC2 = a
    code5 += [('DIV', AC4, AC2, AC1, 'modcalc: a / b'),
              ('MUL', AC4, AC1, AC4, 'modcalc: (a / b) * b'),
              ('SUB', AC1, AC2, AC4, 'modcalc: c = a - ((a / b) * b)')]
    code5 += pop_register(AC4, "Restore old AC4 after modulus calculation")
    code5 += comment("End modulus")
    return code5

def comparison(comparenode):
    jumpinstrs = {'=': 'JEQ', '!=': 'JNE', 
                  '>': 'JGT', '>=': 'JGE', 
                  '<': 'JLT', '<=': 'JLE'}
    
    op = comparenode.value
    inst = jumpinstrs[op]
    
    code5  = comment("BEGIN COMPARISON %s" % op)
    code5 += binary_operator('SUB', comparenode)
    code5 += [
        (inst, AC1, 2, PC, 'skip set to false'),
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
        
        if not is_comment(inst5):
            i += 1

    code5 = realcode5
    
    return code5

def do_loop(ast):
    cond, body = ast.children
    condcode = generate_code(cond)
    bodycode = generate_code(body)
    
    codelen = code_length(bodycode)
    realbody = []
    i = 0
    for inst5 in bodycode:
        inst, r, s, t, com = inst5
        if inst == 'break':
            realbody.append(('JEQ', ZERO, codelen - i, PC, 'break'))
        else:
            realbody.append(inst5)
        if not is_comment(inst5):
            i += 1
    
    code5  = comment('BEGIN DO COND')
    code5 += condcode
    code5 += [('JEQ', AC1, code_length(bodycode) + 1, PC, 'jump if do cond is false')]
    code5 += comment('cond true, DO:')
    code5 += realbody
    code5 += [('JEQ', ZERO, -code_length(condcode + realbody) - 2, PC, 
                      'End of DO, go back to beginning')]
    
    return code5

def for_loop(fornode):
    variables.insert(0, {})
    
    code5  = comment('BEGIN FA:')
    
    if fornode.loopcount > 1:
        # we're in a nested for loop. Need to push the last fa variable onto
        # the stack and update its memory location
        
        p = fornode.parent
        while p.node_type != 'for_loop':
            p = p.parent
        # p contains the last for loop
        outer_fa_varname = p.children[0].value
        pmemloc = activation_record_size[0]
        activation_record_size[0] += 1
        
        if len(activation_record_size) == 1: 
            # global fa loop's go with global variables
            variables[0][outer_fa_varname] = (pmemloc, ZERO)
            code5 += [('data', 0, 0, 0, '%s initialization' % outer_fa_varname),
                      ('ST', AC3, pmemloc, ZERO, 'storing fa variable %s in heap' % outer_fa_varname)]
        else:
            # proc fa loops go in the activation_record
            code5 += comment('NESTED FA IN PROC, STORE LAST FA VAR ON THE STACK')
            code5 += push_register(AC3, 'storing last for loop variable')
            pmemloc = -pmemloc
        
            variables[0][outer_fa_varname] = (pmemloc, FP)
    
    var, lower, upper, body = fornode.children
    varname = var.value
    variables[0][varname] = (0, AC3) # store the fa variable in AC3
    
    code5 += generate_code(lower)
    code5 += [('LDA', AC3, 0, AC1, 'Store the loop lower in AC3')]
    
    temp = generate_code(body)
    bodycode  = comment('LOOP %s BODY:' % varname)
    bodycode += temp
    bodycode += [('LDA', AC3, 1, AC3, 'increment loop variable %s' % varname)]
    bodycode += comment('END OF FA BODY')
    
    codelen = code_length(bodycode)
    realbody = []
    i = 0
    for inst5 in bodycode:
        inst, r, s, t, com = inst5
        if inst == 'break':
            realbody.append(('JEQ', ZERO, codelen - i + 2, PC, 'break'))
        else:
            realbody.append(inst5)
        if not is_comment(inst5):
            i += 1
    
    code5 += [('JEQ', ZERO, code_length(bodycode), PC, 'Skip body until we check upper bound')]
    code5 += realbody
    
    uppercode = generate_code(upper)
    code5 += uppercode
    code5 += comment('LOADED FA UPPER VALUE INTO AC1')
    jumpsize = code_length(uppercode + bodycode)
    code5 += [('SUB', AC1, AC3, AC1, 'DIFFERENCE BETWEEN %s AND UPPER BOUND' % varname),
              ('JLE', AC1, - jumpsize - 2, PC, 'FA REPEAT JUMP')]
    code5 += comment('END FA')
    
    if fornode.loopcount > 1:
        if len(activation_record_size) == 1:
            # get the global var back off the heap
            code5 += [('LD', AC3, pmemloc, FP, 'restore old loop var off heap')]
        else:
            # get it off the stack
            code5 += pop_register(AC3, "restore old for loop variable")
        
    # remove the variable stack
    variables.pop(0)
    return code5

# proc stuff ---------------------------------------------------------------

# memory representation
# +------------------------------------------------------------------+
# | ... | var2 | var1| retval | retaddr | param1 | p2 | lastfp | ... |
# +------------------------------------------------------------------+
#       ^                     ^                       ^              ^
#       sp                    fp          fp + fpoffset           dmem

def proc(procnode):
    global variables, activation_record_size
    variables.insert(0, {})
    
    children = procnode.children
    procname = procnode.value
    body = children.pop(-1)
    
    code5  = comment('BEGIN PROC %s' % procname)
    code5 += [('LDA', FP, 0, SP, 'Set frame pointer')]
    
    # set memory locations of local variables
    i = 0
    if procnode.ice9_type[1] != 'nil':
        i += 1
    for var, type9 in procnode.vars:
        code5 += push_var(var, type9)
        i += type9_size(type9)
        variables[0][var] = (- i, FP)
    
    # set memory locations of params
    fpoffset = 1 
    for p in children:
        paramname = p.value
        paramloc = fpoffset
        variables[0][paramname] = (fpoffset, FP)
        fpoffset += 1
    
    # set location of return value
    if procnode.ice9_type[1] != 'nil':
        procnode.vars.insert(0, (procname, procnode.ice9_type[1]))
        variables[0][procname] = (-1, FP)
    
    activation_record_size.insert(0, i)
    
    # generate code of proc
    bodycode = generate_code(body)
    bodylen = code_length(bodycode)
    instno = 0
    for i, inst5 in enumerate(bodycode):
        if not is_comment(inst5):
            instno += 1
        if inst5[0] == "return":
            bodycode[i] = ('JEQ', ZERO, bodylen - instno + 1, PC, 'early return in %s' % procname)
        
    code5 += bodycode
    
    if procnode.ice9_type != 'nil':
        # handle return value
        code5 += [('LD', AC1, -1, FP, 'Store the return value in AC1')]
    
    code5 += pop_register(AC2, 'pop return address')
    
    code5 += [('LDA', SP, fpoffset, FP, 'Pop off local values from the stack')]
    code5 += [('LD', PC, 0, FP, 'Moving return address into PC')]
    code5 += comment('END PROC %s' % procname)
    
    activation_record_size.pop(0)
    variables.pop(0)
    return code5

def str_to_int(strnode):
    code5  = comment("converting string to integer:")
    code5 += passthru(strnode)
    # okay, a pointer to the string should be in AC1
    code5 += push_register(AC2)
    code5 += push_register(AC4)
    code5 += [('LDC', AC4, 0, 0, 'Start with a sum of 0'),
              ('LD', AC2, 0, AC1, 'Load the next character into memory')]
    
    loop  = push_register(AC1)
    loop += [('LDC', AC1, 10, 0, 'Prepare for multiply'),
              ('MUL', AC4, AC4, AC1, 'sum = sum * 10')]
    loop += pop_register(AC1)
    loop += [('LDA', AC2, -ord("0"), AC2, "Subtract the ascii '0'"),
             ('ADD', AC4, AC4, AC2, 'sum = sum + nextdigit'),
             ('LDA', AC1, 1, AC1, 'increment string pointer'),
             ('JEQ', ZERO, -code_length(loop) - 6, PC, 'Loop through rest of string')]
    
    code5 += [('JEQ', AC2, code_length(loop), PC, "Skip if we've hit the null terminator")]
    code5 += loop
    code5 += [('LDA', AC1, 0, AC4, 'Move the int value int AC1')]
    code5 += pop_register(AC4)
    code5 += pop_register(AC2)
    
    return code5

def proc_call(pcnode):
    # push the return address
    procname = pcnode.value
    
    if procname == 'int':
        # special case
        return str_to_int(pcnode)
    
    code5  = comment('BEGIN PROC CALL %s' % procname)
    for r in (AC2, AC3, AC4):
        code5 += push_register(r, 'save registers before proc call')
    
    code5 += push_register(FP, 'store the frame pointer before the call')
    
    params = pcnode.children # calling parameters
    params.reverse() # we want to push on in reverse so they'll be in order in mem
    for p in params:
        code5 += generate_code(p)
        code5 += push_register(AC1, 'push parameter %s' % p.value)
    
    code5 += [('LDA', AC2, 3, PC, 'Store return address in AC2')]
    code5 += push_register(AC2, 'store the return address')
    code5 += [('call', procname, 0, 0, 'CALL %s' % procname)]
    code5 += pop_register(FP, 'pop the frame pointer after call')
    
    for r in (AC4, AC3, AC2):
        code5 += pop_register(r, 'remember registers from before proc call')
    
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
    '%': modulus,
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
    'return': return9,
    'exit': exit9,
    'break': break9,
    'for_loop': for_loop,
    'read': read,
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
            output.append("%5d: %-9s %d,%2d(%d)\t\t* %s" % (ln, inst, r, s, t, com))
        elif inst in ('HALT', 'IN', 'OUT', 'INB', 'OUTB', 'OUTC', 
                      'ADD', 'SUB', 'MUL', 'DIV', 'OUTNL'):
            ln = linecounter.next()
            output.append("%5d: %-9s %d,%2d,%2d\t\t* %s" % (ln, inst, r, s, t, com))
        elif inst == 'comment':
            output.append("    *  %s" % com)
        elif inst == 'data':
            output.append('.DATA  \t\t%d\t\t\t* %s' % (r, com))
        elif inst == 'string':
            output.append('.SDATA \t\t"%s"' % r)
            output.append('.DATA  \t\t0\t\t\t* null terminator')
        else:
            raise ValueError("Can't print this instruction: %s" % inst)

    return "\n".join(output) + "\n"

def generate_code_str(ast):
    """Shorthand for creating the TM string code for the ast."""
    return code5str(generate_code(ast))
