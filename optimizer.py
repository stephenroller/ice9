from cfg import construct_CFG, yield_blocks

def remove_dead_jumps(block):
    print "***"
    for cfgnode in block:
        pass
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
