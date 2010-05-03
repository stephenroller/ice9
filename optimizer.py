import re
from cfg import construct_CFG, yield_blocks, fix_jumps
from itertools import izip
from codegenerator import is_comment, code5str
from codegenerator import ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

WILD = ".*"
JUMP_PAT = r'J(EQ|NE|LT|LE|GT|GE)'

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

def always_jumps(block):
    matches = match_sequential(block, [('LDC', "$A", 1, WILD), ('JEQ', "$A", WILD, WILD)])
    if matches:
        print matches
    return False

def sequential_pushes(block):
    matches = match_sequential(block, [('ST', "$R1", "$A", SP),
                                       ('LDA',   SP, "$A", SP),
                                       ('ST', "$R2",   -1, SP),
                                       ('LDA',   SP,   -1, SP)])
    if matches:
        offset, nodes, b = matches
        # nodes[0] remains unchanged
        nodes[1].remove()
        nodes[2].inst5 = ('ST', b["R2"], b["A"] - 1, SP, nodes[2].comment)
        nodes[3].inst5 = ('LDA', SP, b["A"] - 1, SP, nodes[3].comment)
        
        del block[offset]
        
        return block
    
    return False

def sequential_pops(block):
    # 160: LD        5, 0(6)        * pop the frame pointer after call
    # 161: LDA       6, 1(6)        * Move (pop) the stack pointer
    # 162: LD        4, 0(6)        * remember registers from before proc call
    # 163: LDA       6, 1(6)        * Move (pop) the stack pointer
    match = match_sequential(block, [('LD',  "$R1", "$B", SP),
                                     ('LDA',    SP, "$A", SP),
                                     ('LD',  "$R2",    0, SP),
                                     ('LDA',    SP,    1, SP)])
    if match is False:
        return False
    
    offset, nodes, b = match
    nodes[1].remove()
    del block[offset + 1]
    nodes[2].inst5 = ('LD', b["R2"], b["B"] + 1, SP, nodes[2].comment)
    nodes[3].inst5 = ('LDA', SP, b["A"] + 1, SP, nodes[3].comment)
    return block

def remove_dead_jumps(block):
    for i, cfgnode in enumerate(block):
        if cfgnode.outlink is cfgnode.next and cfgnode.outlink is not None:
            cfgnode.remove()
            del block[i]
            return block
    return False

def remove_unnecessary_loads(block):
    matches = match_sequential(block, [('ST', "$A", "$B", "$C"), 
                                       ('LD', "$A", "$B", "$C")])
    if matches:
        offset, nodes, bindings = matches
        nodes[1].remove()
        del block[offset + 1]
        return block
        
    return False

def invert_sign(block):
    match = match_sequential(block, [('LDC', "$A", -1, WILD),
                                     ('MUL', "$B", "$B", "$A")])
    if match:
        offset, nodes, b = match
        nodes[0].remove()
        del block[offset]
        nodes[1].inst5 = ('SUB', b["B"], ZERO, b["B"], nodes[1].comment)
        return block
    
    return False

def times_two(block):
    # 5: LDC       1, 2(0)      * load constant: 2
    # 6: LD        2, 0(6)      * Get reg 2 off the stack
    # 7: LDA       6, 1(6)      * Move (pop) the stack pointer
    # 8: MUL       1, 2, 1      * MUL left and right.
    match = match_sequential(block, [('LDC', "$A", 2, WILD),
                                     ('LD',  "$B", 0, SP),
                                     ('LDA',   SP, 1, SP),
                                     ('MUL', "$A", "$B", "$A")])
    if match is False:
        return False
        
    offset, nodes, b = match
    nodes[0].remove()
    nodes[1].inst5 = ('LD', b["A"], 0, SP, 'get A off of stack')
    nodes[3].inst5 = ('ADD', b["A"], b["A"], b["A"], 'A * 2')
    del block[offset]
    return block

def addsub_constant(block):
    # 3: ST        1,-1(6)      * Store reg 1 on the stack
    # 4: LDA       6,-1(6)      * Move (push) the stack pointer
    # 5: LDC       1,-2(0)      * load constant: -2
    # 6: LD        2, 0(6)      * Get reg 2 off the stack
    # 7: LDA       6, 1(6)      * Move (pop) the stack pointer
    # 8: ADD       1, 2, 1      * ADD left and right.
    match = match_sequential(block, [('ST',  "$R1",    -1, SP),
                                     ('LDA',    SP,    -1, SP),
                                     ('LDC', "$R1",  "$C", WILD),
                                     ('LD',  "$R2",     0, SP),
                                     ('LDA',    SP,     1, SP),
                                     ('(ADD|SUB)', "$R1", "$R2", "$R1")])
    if match is False:
        return False
    
    offset, nodes, b = match
    if nodes[5].inst == 'ADD':
        nodes[0].inst5 = ('LDA', b["R1"], b["C"], b["R1"], "Add %d" % b["C"])
    else:
        nodes[0].inst5 = ('LDA', b["R1"], - b["C"], b["R1"], "Subtract %d" % b["C"])
    
    for n in nodes[1:]:
        n.remove()
    del block[offset+1:offset+len(nodes)-1]
    return block

def muldiv_constant(block):
    # 3: ST        1,-1(6)      * Store reg 1 on the stack
    # 4: LDA       6,-1(6)      * Move (push) the stack pointer
    # 5: LDC       1,-2(0)      * load constant: -2
    # 6: LD        2, 0(6)      * Get reg 2 off the stack
    # 7: LDA       6, 1(6)      * Move (pop) the stack pointer
    # 8: MUL       1, 2, 1      * ADD left and right.
    match = match_sequential(block, [('ST',  "$R1",    -1, SP),
                                     ('LDA',    SP,    -1, SP),
                                     ('LDC', "$R1",  "$C", WILD),
                                     ('LD',  "$R2",     0, SP),
                                     ('LDA',    SP,     1, SP),
                                     ('(MUL|DIV)', "$R1", "$R2", "$R1")])
    if match is False:
        return False

    offset, nodes, b = match
    nodes[0].remove()
    nodes[1].remove()
    nodes[2].remove()
    nodes[3].remove()
    nodes[4].inst5 = ('LDC', b["R2"], b["C"], ZERO, 'Prepare multiply by %d' % b["C"])
    nodes[5].inst5 = (nodes[5].inst, b["R1"], b["R1"], b["R2"], nodes[5].comment)
    del block[offset:offset + 3]
    return block

def push_pop(block):
    # 2: ST        1,-1(6)      * saving the set value to the stack
    # 3: LDA       6,-1(6)      * Move (push) the stack pointer
    # 4: LD        1, 0(6)      * getting the set value off the stack
    # 5: LDA       6, 1(6)      * Move (pop) the stack pointer
    match = match_sequential(block, [('ST', "$A", -1, SP),
                                     ('LDA', SP, -1, SP),
                                     ('LD', "$A", 0, SP),
                                     ('LDA', SP, 1, SP)])
    if match:
        offset, nodes, b = match
        for n in nodes:
            n.remove()
        del block[offset:offset+len(nodes)]
        return block
    
    return False

def jump_based_on_boolean(block):
    # 3: JGT       1, 2(7)      * skip set to false
    # 4: LDC       1, 0(0)      * comparison is bad, set reg 1 to false
    # 5: LDA       7, 1(7)      * skip set to true
    # 6: LDC       1, 1(0)      * compairson is good, set reg 1 to true
    # 7: JEQ       1, 0(7)      * if false, jump to next cond
    match = match_sequential(block, [(JUMP_PAT, "$R1",   2, PC),
                                     ('LDC',    "$R1",   0, WILD),
                                     ('LDA',      PC,    1, PC),
                                     ('LDC',    "$R1",   1, WILD),
                                     ('JEQ',    "$R1", "$A", "$B")
                                     ])
    if match is False:
        return False
    
    offset, nodes, b = match
    
    inverseinsts = dict(JEQ='JNE', JNE='JEQ', JLT='JGE', JGT='JLE', 
                        JLE='JGT', JGE='JLT')
    inverseinst = inverseinsts[nodes[0].inst]
    nodes[-1].inst5 = (inverseinst, b["R1"], b["A"], b["B"], nodes[-1].comment)
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

def optimize(code5):
    data, code5 = reformat_code5(code5)
    
    # now we need to make the control flow diagram
    cfg = construct_CFG(code5)
    
    fix_jumps(cfg)
    remove_dead_code(cfg)
    
    jump_based_on_boolean(list(iter(cfg)))
    
    # and finally we begin running some optimizations
    for block in yield_blocks(cfg):
        while True:
            optimized = False
            for opt in optimizations:
                result = opt(block)
                if result is not False:
                    block = result
                    optimized = True
                    break
            
            if not optimized:
                # none of our optimizations optimized; we're done!
                break
    
    fix_jumps(cfg)
    
    optimizedcode = [n.inst5 for n in cfg]
    return data + optimizedcode


if __name__ == '__main__':
    from ice9 import compile
    from tests import *
    
    source = """
    
    """
    source = open("test.9").read()
    
    print compile(source, False)
    print "-" * 80
    print
    print compile(source, True)
