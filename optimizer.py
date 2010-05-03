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
    # matches = match_sequential(block, [('LD')])
    return False

def remove_dead_jumps(block):
    for i, cfgnode in enumerate(block):
        if node_equal(cfgnode, (JUMP_PAT, WILD, 0, PC)):
            cfgnode.remove()
            del block[i]
            return True
    return False

def remove_unnecessary_loads(block):
    matches = match_sequential(block, [('ST', "$A", "$B", "$C"), 
                                       ('LD', "$A", "$B", "$C")])
    if matches:
        offset, nodes, bindings = matches
        block[offset].remove()
        
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

optimizations = [remove_dead_jumps, sequential_pushes, remove_unnecessary_loads]


def optimize(code5):
    data, code5 = reformat_code5(code5)
    
    # now we need to make the control flow diagram
    cfg = construct_CFG(code5)
    
    # and finally we begin running some optimizations
    for block in yield_blocks(cfg):
        while True:
            optimized = False
            for opt in optimizations:
                optimized = optimized or opt(block)
            
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
    
    test_fa6().runTest()
