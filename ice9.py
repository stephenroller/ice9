#!/usr/bin/env python
import sys

class Ice9Error(Exception):
    line = 1
    error = ""
    
    def __init__(self, line, error):
        self.line = line
        self.error = error
    
    def __str__(self):
        return "line %d: %s" % (self.line, str(self.error))

def compile(source, optimize=True):
    from parser import parse
    from ast import parse2ast
    from semantic import check_semantics
    from codegenerator import generate_code, code5str
    
    ast = check_semantics(parse2ast(parse(source)))
    if optimize:
        from astoptimizer import optimize_ast
        optimize_ast(ast)
    
    code = generate_code(ast)
    if optimize:
        import optimizer
        code = optimizer.optimize(code)
    
    return code5str(code)

def main(*args):
    from parser import Ice9SyntaxError
    from lexer import Ice9LexicalError
    from semantic import Ice9SemanticError
    
    if len(args) == 0:
        sourcefile = sys.stdin
        outfile = sys.stdout
    elif len(args) == 1:
        sourcefile = sys.stdin
        outfile = open(args[0], 'w')
    elif len(args) == 2:
        sourcefile = open(args[0])
        outfile = open(args[1], 'w')
    
    source = sourcefile.read()
    
    try:
        # try to parse the source and exit cleanly
        compiled = compile(source)
        outfile.write(compiled)
        outfile.close()
        sys.exit(0)
    except (Ice9Error, Ice9LexicalError, Ice9SyntaxError, Ice9SemanticError), e:
        # but if there's an error, print it out and exit.
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])
