import re
from cfg import construct_CFG, yield_blocks, fix_jumps
from itertools import izip
from codegenerator import is_comment, code5str
from codegenerator import ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

# constants
WILD = ".*"
JUMP_PAT = r'J(EQ|NE|LT|LE|GT|GE)'

# utility functions
def inst_equal(inst5, pattern, bindings=None):
    if bindings is None:
        bindings = dict()
    
    assert len(pattern) == 4
    assert len(inst5) == 5
    for p, i in izip(pattern, inst5):
        if type(p) is str and p.startswith("$"):
            # variable!
            varname = p[1:]
            if varname not in bindings:
                bindings[varname] = i
            elif bindings[varname] != i:
                return False
        elif not (p == WILD or p == i or re.match("^%s$" % p, str(i))):
            return False
    return True

def match_sequential(block, pattern):
    for i in range(0, len(block) - len(pattern)):
        window = block[i:i + len(pattern)]
        b = {}
        matches = all(node_equal(c, p, b) for c, p in izip(window, pattern))
        if matches:
            return i, window, b
        
    return False

def node_equal(node, pattern, bindings=None):
    return inst_equal(node.inst5, pattern, bindings)

# ----------------------------------------------------------------

# "macro" for optimization. You'll see how it's used.
def optimization(pattern):
    assert len(pattern) > 0
    
    def _opter(opt):    
        def mod_opt(block):
            assert len(block) > 0
            
            # find the pattern
            match = match_sequential(block, pattern)
            
            if match is False:
                # didn't even match the pattern, skip this one
                return False
            
            # we'll use these to rebuild our block
            first = block[0]
            end = block[-1].next
            
            # match information
            offset, nodes, bindings = match
            # we matched the pattern, so let's let run the actual optimization
            result = opt(nodes, **bindings)
            
            if result is False:
                return
            
            # since nodes were likely deleted, we need to rebuild our block
            # for the main loop
            newblock = []
            n = first.prev is not None and first.prev.next or first
            while n != end:
                newblock.append(n)
                n = n.next
            
            # return the modified block
            return newblock
            
        return mod_opt
    return _opter

# begin optimizations --------------------------------

def always_jumps(block):
    matches = match_sequential(block, [('LDC', "$A", 1, WILD), ('JEQ', "$A", WILD, WILD)])
    if matches:
        print matches
    return False


@optimization([('ST', "$R1", "$A", SP),
               ('LDA',   SP, "$A", SP),
               ('ST', "$R2",   -1, SP),
               ('LDA',   SP,   -1, SP)])
def sequential_pushes(nodes, R1, A, R2):
    nodes[1].remove()
    nodes[2].inst5 = ('ST',  R2, A - 1, SP, nodes[2].comment)
    nodes[3].inst5 = ('LDA', SP, A - 1, SP, nodes[3].comment)


@optimization([('LD',  "$R1", "$B", SP),
               ('LDA',    SP, "$A", SP),
               ('LD',  "$R2",    0, SP),
               ('LDA',    SP,    1, SP)])
def sequential_pops(nodes, R1, B, A, R2):
    nodes[1].remove()
    nodes[2].inst5 = ('LD',  R2, B + 1, SP, nodes[2].comment)
    nodes[3].inst5 = ('LDA', SP, A + 1, SP, nodes[3].comment)


def remove_dead_jumps(block):
    for i, cfgnode in enumerate(block):
        if cfgnode.outlink is cfgnode.next and cfgnode.outlink is not None:
            cfgnode.remove()
            del block[i]
            return block
    return False


@optimization([('ST', "$A", "$B", "$C"), 
               ('LD', "$A", "$B", "$C")])
def remove_unnecessary_loads(nodes, A, B, C):
    nodes[1].remove()


@optimization([('LDC', "$A", -1, WILD),
               ('MUL', "$B", "$B", "$A")])
def invert_sign(nodes, A, B):
    nodes[0].remove()
    nodes[1].inst5 = ('SUB', B, ZERO, B, nodes[1].comment)


@optimization([('LDC', "$A",    2, WILD),
               ('LD',  "$B",    0, SP),
               ('LDA',   SP,    1, SP),
               ('MUL', "$A", "$B", "$A")])
def times_two(nodes, A, B):
    nodes[0].remove()
    nodes[1].inst5 = ('LD', A, 0, SP, 'get A off of stack')
    nodes[3].inst5 = ('ADD', A, A, A, 'A * 2')


@optimization([('ST',  "$R1",    -1, SP),
               ('LDA',    SP,    -1, SP),
               ('LDC', "$R1",  "$C", WILD),
               ('LD',  "$R2",     0, SP),
               ('LDA',    SP,     1, SP),
               ('(ADD|SUB)', "$R1", "$R2", "$R1")])
def addsub_constant(nodes, R1, R2, C):
    if nodes[5].inst == 'ADD':
        nodes[0].inst5 = ('LDA', R1, C, R1, "Add %d" % C)
    else:
        nodes[0].inst5 = ('LDA', R1, -C, R1, "Subtract %d" % C)
    
    for n in nodes[1:]:
        n.remove()


@optimization([('ST',  "$R1",    -1, SP),
               ('LDA',    SP,    -1, SP),
               ('LDC', "$R1",  "$C", WILD),
               ('LD',  "$R2",     0, SP),
               ('LDA',    SP,     1, SP),
               ('(MUL|DIV)', "$R1", "$R2", "$R1")])
def muldiv_constant(nodes, R1, R2, C):
    for i in (0, 1, 2, 3):
        nodes[i].remove()
    nodes[4].inst5 = ('LDC', R2, C, ZERO, 'Prepare multiply by %d' % C)
    nodes[5].inst5 = (nodes[5].inst, R1, R1, R2, nodes[5].comment)


@optimization([('ST', "$A", -1, SP),
               ('LDA',  SP, -1, SP),
               ('LD', "$A",  0, SP),
               ('LDA',  SP,  1, SP)])
def push_pop(nodes, A):
    for n in nodes:
        n.remove()


def jump_based_on_boolean(block):
    # 3: JGT       1, 2(7)      * skip set to false
    # 4: LDC       1, 0(0)      * comparison is bad, set reg 1 to false
    # 5: LDA       7, 1(7)      * skip set to true
    # 6: LDC       1, 1(0)      * compairson is good, set reg 1 to true
    # 7: JEQ       1, 0(7)      * if false, jump to next cond
    
    n = block[0]
    while n.prev != None:
        n = n.prev
    block = list(iter(n))
    
    match = match_sequential(block, [(JUMP_PAT, "$R1",   2, PC),
                                     ('LDC',    "$R1",   0, WILD),
                                     ('LDA',      PC,    1, PC),
                                     ('LDC',    "$R1",   1, WILD),
                                     ('(JEQ|JNE)', "$R1", "$A", "$B")
                                     ])
    if match is False:
        return False
    
    offset, nodes, b = match
    if nodes[-1].inst == 'JEQ':
        inverseinsts = dict(JEQ='JNE', JNE='JEQ', JLT='JGE', JGT='JLE', 
                            JLE='JGT', JGE='JLT')
        inverseinst = inverseinsts[nodes[0].inst]
        nodes[-1].inst5 = (inverseinst, b["R1"], b["A"], b["B"], nodes[-1].comment)
    else:
        nodes[-1].inst5 = (nodes[-1].inst, b["R1"], b["A"], b["B"], nodes[-1].comment)
    for n in nodes[:-1]:
        n.remove()
    del block[offset:offset + 4]
    return block


def reformat_code5(code5):
    # first let's strip out comments and data.
    data = []
    realcode = []
    for inst5 in code5:
        if is_comment(inst5):
            if inst5[0] == 'comment':
                continue
            # not a "comment", but a data statement. We'll put all those in
            # front later
            data.append(inst5)
        else:
            realcode.append(inst5)
    return data, realcode


optimizations = [remove_dead_jumps, 
                 jump_based_on_boolean,
                 sequential_pushes,
                 sequential_pops,
                 times_two,
                 push_pop,
                 invert_sign,
                 addsub_constant,
                 muldiv_constant,
                 remove_unnecessary_loads,
                 ]

def _paint_visited(node):
    if node is None or hasattr(node, '_painted'):
        return
    
    setattr(node, '_painted', True)
    if node.outlink is not None:
        if node.inst not in ('LD', 'LDA'):
            _paint_visited(node.next)
        _paint_visited(node.outlink)
    else:
        _paint_visited(node.next)

def remove_dead_code(cfg):
    _paint_visited(cfg)
    for n in cfg:
        if not hasattr(n, '_painted'):
            n.remove()

# end optimizations ------------------------------------------------

# main driver
def optimize(code5):
    data, code5 = reformat_code5(code5)
    
    # now we need to make the control flow diagram
    cfg = construct_CFG(code5)
    
    remove_dead_code(cfg)
    
    # and finally we begin running some optimizations
    for block in yield_blocks(cfg):
        while True:
            optimized = False
            for opt in optimizations:
                result = opt(block)
                if result is not False:
                    block = result
                    optimized = True
                    fix_jumps(cfg)
                    break
            
            if not optimized:
                # none of our optimizations optimized; we're done!
                break

    
    optimizedcode = [n.inst5 for n in cfg]
    return data + optimizedcode


if __name__ == '__main__':
    from ice9 import compile
    from tests import *
    
    source = """
    
    """
    # source = open("examples/fib.9.txt").read()
    source = open('test.9').read()
    
    print compile(source, False)
    print "-" * 80
    print
    print compile(source, True)
