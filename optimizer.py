import re
from cfg import construct_CFG, yield_blocks, fix_jumps
from itertools import izip
from codegenerator import is_comment, ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

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
    matches = match_sequential(block, [])

def remove_dead_jumps(block):
    for i, cfgnode in enumerate(block):
        if node_equal(cfgnode, (JUMP_PAT, WILD, 0, PC)):
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
        return nodes[:1]
        
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
                 push_pop,
                 remove_unnecessary_loads,
                 invert_sign]


def optimize(code5):
    data, code5 = reformat_code5(code5)
    
    # now we need to make the control flow diagram
    cfg = construct_CFG(code5)
    
    # and finally we begin running some optimizations
    for block in yield_blocks(cfg):
        while True:
            optimized = False
            for opt in optimizations:
                result = optimized or opt(block)
                if not optimized and result is not False:
                    block = result
                    optimized = True
            
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
