import re
from cfg import construct_CFG, yield_blocks, fix_jumps
from itertools import izip
from codegenerator import is_comment, ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

WILD = ".*"
JUMP_PAT = r'J(EQ|NE|LT|LE|GT|GE)'

def inst_equal(inst5, pattern):
    assert len(pattern) == 4
    assert len(inst5) == 5
    for p, i in izip(pattern, inst5):
        if not (p == WILD or p == i or re.match("^%s$" % p, str(i))):
            return False
    return True

# def match_sequential(block, pattern):
#     for i in range(0, len(block) - len(pattern)):
#         window = block[i:]
#         matches = all(node_equal(c, p) for c, p in izip(window, pattern))
#         return window
#     return False

def node_equal(node, pattern):
    return inst_equal(node.inst5, pattern)

def remove_dead_jumps(block):
    for i, cfgnode in enumerate(block):
        if node_equal(cfgnode, (JUMP_PAT, WILD, 0, PC)):
            cfgnode.remove()
            del block[i]
            return True
    return False

def remove_unnecessary_loads(block):
    i = 0
    for a, b in izip(block, block[1:]):
        insta, ra, sa, ta, coma = a.inst5
        instb, rb, sb, tb, comb = b.inst5
        
        if (insta == 'ST' and instb == 'LD' and ra == rb and 
            sa == sb and ta == tb):
                b.remove()
                del block[i + 1]
                return True
        
        i += 1
    return False


optimizations = [remove_dead_jumps]

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
    
    source = """var a : int[3]
fa i := 1 to 3 ->
    a[i - 1] := i - 1;
af
fa i := 1 to 3 ->
    writes a[i - 1];
af
"""
    
    test_fa6 = make_compile_test(source, "0 1 2")
    
    print compile(source, False)
    print "-" * 80
    print
    print compile(source, True)
    
    test_fa6().runTest()
