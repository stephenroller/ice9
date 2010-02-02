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


def main(*args):
    from parser import parse
    from parser import Ice9SyntaxError
    from lexer import Ice9LexicalError
    
    if len(args) == 0:
        # if no filename is specified, use stdin
        f = sys.stdin
    else:
        # if a filename is specified, use that file
        f = open(args[0])
    
    source = f.read()
    
    try:
        # try to parse the source and exit cleanly
        if parse(source):
            sys.exit(0)
        else:
            raise Ice9Error(0, 'invalid input')
    except (Ice9Error, Ice9SyntaxError, Ice9LexicalError), e:
        # but if there's an error, print it out and exit.
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])
