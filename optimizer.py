import re
from cfg import construct_CFG, yield_blocks
from itertools import izip
from codegenerator import ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

WILD = ".*"
JUMP_PAT = r'J(EQ|NE|LT|LE|GT|GE)'

def inst_equal(inst5, pattern):
    assert len(pattern) == 4
    assert len(inst5) == 5
    for p, i in izip(pattern, inst5):
        if not (p == WILD or p == i or re.match("^%s$" % p, str(i))):
            return False
    return True

def node_equal(node, pattern):
    return inst_equal(node.inst5, pattern)

def remove_dead_jumps(block):
    for cfgnode in block:
        if node_equal(cfgnode, (JUMP_PAT, WILD, 0, PC)):
            cfgnode.remove()
            return True
    return False


optimizations = [remove_dead_jumps]

def optimize(code5):
    # first let's strip out comments and data.
    from codegenerator import is_comment
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
    code5 = realcode
    
    # now we need to make the control flow diagram
    cfg = construct_CFG(code5)
    
    # first optimization, just get rid of all our useless jumps
    remove_dead_jumps(cfg)
    
    # and finally we begin running some optimizations
    
    # for block in yield_blocks(cfg):
    #     print "Block: %d" % len(block)
    #     for b in block:
    #         print b.inst5
    #     print "-" * 40
    # 
    #     while True:
    #         optimized = False
    #         for opt in optimizations:
    #             optimized = optimized or opt(block)
    #         
    #         if not optimized:
    #             # none of our optimizations optimized; we're done!
    #             break
    
    optimizedcode = [n.inst5 for n in cfg]
    return data + optimizedcode
        


if __name__ == '__main__':
    from parser import parse
    from ast import parse2ast
    from semantic import check_semantics
    from codegenerator import generate_code, code5str
    
    source = """
    if true ->
    write 3 + 4;
    write 8;
    [] false ->
    write 4;
    fi
    """
    
    code5 = generate_code(check_semantics(parse2ast(parse(source))))
    
    print code5str(code5)
    print "-" * 80
    print
    
    print code5str(optimize(code5))
