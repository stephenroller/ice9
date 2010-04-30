"""
Post-codegen optimizations.
"""

from itertools import takewhile

from codegenerator import ZERO, AC1, AC2, AC3, AC4, SP, FP, PC

JUMP_INSTS = ('JEQ', 'JNE', 'JLT', 'JLE', 'JGT', 'JGE')
LOAD_INST  = ('LD', 'LDA', 'LDC')

class CFGNode:
    "Represents a node in the Control Flow Diagram"
    inst5 = (None, None, None, None, None)
    
    inlinks = None
    outlink = None
    
    # the normal flow is represented as a doubly linked list.
    next = None
    prev = None
    
    def __init__(self, inst5, prev):
        self.inst5 = inst5
        self.inlinks = set()
        
        self.prev = prev
        if prev is not None:
            self.prev.next = self
    
    def __iter__(self):
        n = self
        while n is not None:
            yield n
            n = n.next
    
    def __getitem__(self, index):
        "Returns the CFGNode of relative offset."
        from codegenerator import is_comment
        n = self
        while index > 0:
            n = n.next
            index -= 1
        
        while index < 0:
            n = n.prev
            index += 1
        
        return n

def construct_CFG(code5):
    "Creates a control flow graph for the given code5."
    if len(code5) == 0:
        return None
    
    # build the beginning linked list.
    cfg = None
    node = None
    for inst5 in code5:
        node = CFGNode(inst5, node)
        if cfg is None:
            # need to keep the link to the first one
            cfg = node
    
    # Now we want to look for any jumps
    
    for node in cfg:
        inst, r, s, t, com = node.inst5
        
        if inst in JUMP_INSTS:
            # hey, a jump! need to set the in and out links.
            
            # this instruction, depending on value of reg[r], 
            # jumps to s + reg[t].
            if t == PC:
                # relative jump
                jumpto = node[s + 1]
            elif t == ZERO:
                # absolute jump
                jumpto = cfg[s]
            else:
                raise ValueError("Couldn't calculate jump location of %s" % inst5)
            
            # actually set the link
            jumpto.inlinks.add(node)
            node.outlink = jumpto
        elif inst in LOAD_INST and r == PC:
            if inst == 'LDA':
                # loading an offset
                assert t == PC # don't know how to handle any other case
                jumpto = node[s + 1]
            elif inst == 'LDC':
                # direct jump
                jumpto = cfg[s]
            elif inst == 'LD':
                # must be a return, let's just emulate 
                jumpto = node
            
            # actually set the link
            jumpto.inlinks.add(node)
            node.outlink = jumpto
    
    return cfg

def yield_blocks(cfg):
    "Finds blocks in the given CFG. Yields lists of CFGNodes."
    # is_safe returns whether inst5 is safe in a block:
    is_safe = lambda x: x.outlink is None and len(x.inlinks) == 0
    is_unsafe = lambda x: not is_safe(x)
    
    cfgiter = iter(cfg)
    block = []
    for c in cfgiter:
        block.append(c)
        if not is_safe(c):
            yield block
            block = []
    if block:
        yield block

def remove_dead_jumps(block):
    print "***"
    for cfgnode in block:
        if cfgnode.inst5
    return False

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
    
    # and finally we begin running some optimizations
    optimizations = [remove_dead_jumps]
    
    for block in yield_blocks(cfg):
        print "Block: %d" % len(block)
        for b in block:
            print b.inst5
        print "-" * 40
    
        while True:
            optimized = False
            for opt in optimizations:
                optimized = optimized or opt(block)
            
            if not optimized:
                # none of our optimizations optimized; we're done!
                break
    
    return data + realcode
        

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
    