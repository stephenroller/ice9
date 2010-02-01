#!/usr/bin/env python
import sys
from lexer import lex_source
from tree import Tree

class _SyntaxError(Exception):
    def __init__(self, expected):
        self.expected = expected

class TokenStream:
    line = 1
    stream = None
    
    def __init__(self, token_stream):
        self.stream = token_stream
        # remove the SOF token
        self.next()
    
    def current_word(self):
        if self.stream is None or len(self.stream) == 0:
            return None
        return self.stream[0]
    
    def expecting(self, expected):
        ct = self.current_word()
        if ct is None:
            return False
        
        tokentype, tokenvalue = ct
        if type(expected) is tuple and len(expected) == 2:
            return expected == (tokentype, tokenvalue)
        else:
            return expected == tokenvalue
    
    def is_next(self, expected):
        """
        Tests if the next character is expected and pushes forward if it is.
        If it isn't, returns false.
        """
        if self.expecting(expected):
            self.next()
            return True
        else:
            return False
    
    def next_is(self, expected):
        """
        Expects a character and pushes forward if it's found. If it isn't
        found, throws a syntax error.
        """
        if self.is_next(expected):
            return True
        else:
            raise _SyntaxError(expected)
    
    def next_type_is(self, expected_type):
        """
        Expects the next type and pushes forward if it's found. Raise a
        syntax error if it isn't.
        """
        if self.is_next_type(expected_type):
            return True
        else:
            raise _SyntaxError(expected_type)

    def is_next_type(self, expected_type):
        """
        Checks the next type and pushes forward if it's found. Returns false
        if it isn't.
        """
        tokentype, tokenvalue = self.current_word()
        if tokentype == expected_type:
            self.next()
            return True
        else:
            return False
        

    def next(self):
        while True:
            self.stream.pop(0)
            if self.current_word() == ('newline', '\n'):
                self.line += 1
            else:
                break


# Recursive descent parser that (hopefully) implements the grammar.txt file.
# Andrew Austin and I worked together to transform the grammar in the 
# spec to the predictive version listed in grammar.txt.

# code is entirely my own.

def _program(stream):
    while _var(stream) or _type(stream) or _forward(stream) or _proc(stream):
        pass
    
    return _stms(stream) and stream.is_next('EOF')

def _stms(stream):
    if not _stm(stream):
        return False
    
    while _stm(stream):
        pass
    
    return True

def _stm(stream):
    return (_if(stream) or _do(stream) or _fa(stream) or
            (stream.is_next('break') and stream.next_is(';')) or
            (stream.is_next('exit') and stream.next_is(';')) or
            (stream.is_next('return') and stream.next_is(';')) or
            (stream.is_next('write') and _Expr(stream) and stream.next_is(';')) or
            (stream.is_next('writes') and _Expr(stream) and stream.next_is(';')) or
            (_Expr(stream) and stream.next_is(';')) or
            stream.is_next(';'))

def _if(stream):
    return (stream.is_next('if') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and _ifPrime(stream))

def _ifPrime(stream):
    if stream.is_next('[]'):
        return _fi(stream)
    else:
        return stream.next_is('fi')

def _fi(stream):
    if stream.is_next('else'):
        return (stream.next_is('->') and _stms(stream) and 
                stream.next_is('fi'))
    else:
        return (_Expr(stream) and stream.next_is('->') and _stms(stream) and
                _ifPrime(stream))

def _do(stream):
    return (stream.is_next('do') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and stream.next_is('od'))

def _fa(stream):
    return (stream.is_next('fa') and stream.next_type_is('ident') and
            stream.next_is(':=') and _Expr(stream) and 
            stream.next_is('to') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and stream.next_is('af'))

def _proc(stream):
    return (stream.is_next('proc') and stream.next_type_is('ident') and
            stream.next_is('(') and _declist(stream) and 
            stream.next_is(')') and _procPrime(stream))

def _procPrime(stream):
    if stream.is_next(':'):
        return _typeid(stream) and _procEnd(stream)
    else:
        return _procEnd(stream)

def _procEnd(stream):
    while _type(stream) or _var(stream):
        pass
    
    while _stm(stream):
        pass
    
    return stream.next_is('end')

def _idlist(stream):
    if not stream.is_next_type('ident'):
        return False
    
    while stream.is_next(','):
        if not stream.next_type_is('ident'):
            return False
    
    return True

def _var(stream):
    return stream.is_next('var') and _varlist(stream)

def _varlist(stream):
    firsthalf = _idlist(stream) and stream.is_next(':') and _typeid(stream)
    
    if not firsthalf:
        return False
    
    while stream.is_next('['):
        if not (stream.next_type_is('int') and stream.next_is(']')):
            return False
    
    while stream.is_next(','):
        if not _varlist(stream):
            return False
    
    return True

def _forward(stream):
    firsthalf = (stream.is_next('forward') and 
                 stream.is_next_type('ident') and
                 stream.is_next('(') and 
                 _declist(stream) and 
                 stream.is_next(')'))
    
    if not firsthalf:
        return False
    
    if stream.is_next(':'):
        return _typeid(stream)
    
    return True

def _declist(stream):
    if _idlist(stream) and stream.next_is(':') and _typeid(stream):
        while stream.is_next(','):
            _declist(stream)
    return True

def _type(stream):
    firsthalf = (stream.is_next('type') and 
                 stream.next_type_is('ident') and
                 stream.is_next('=') and
                 _typeid(stream))
    
    if not firsthalf:
        return False
    
    while stream.is_next('['):
        if not (stream.next_type_is('int') and 
                stream.next_is(']')):
                    return False
    
    return True

def _typeid(stream):
    return stream.next_type_is('ident')

def _Expr(stream):
    return _Low(stream) and _ExprPrime(stream)

def _ExprPrime(stream):
    for o in ('=', '!=', '>', '<', '>=', '<='):
        if stream.is_next(o):
            return _Low(stream) and _ExprPrime(stream)
    return True

def _Low(stream):
    return _Med(stream) and _LowPrime(stream)

def _LowPrime(stream):
    if stream.is_next('+') or stream.is_next('-'):
        return _Med(stream) and _LowPrime(stream)
    return True 

def _Med(stream):
    return _High(stream) and _MedPrime(stream)

def _MedPrime(stream):
    for o in ('*', '/', '%'):
        if stream.is_next(o):
            return _Med(stream) and _MedPrime(stream)
    return True

def _High(stream):
    return _End(stream) and _HighPrime(stream)

def _HighPrime(stream):
    if stream.is_next('-') or stream.is_next('?'):
        return _Expr(stream)
    return True

def _End(stream):
    if stream.is_next('('):
        return _Expr(stream) and stream.next_is(')')
    
    for k in ('true', 'false', 'read'):
        if stream.is_next(k):
            return True
    
    for t in ('int', 'string'):
        if stream.is_next_type(t):
            return True
    
    if stream.is_next_type('ident'):
        if stream.is_next('('):
            return _ProcCall(stream)
        else:
            return _lvaluePrime(stream) and _ValueOrAssn(stream)
    else:
        return False

def _lvaluePrime(stream):
    if stream.is_next('['):
        return (_Expr(stream) and stream.next_is(']') and 
                _lvaluePrime(stream))
    
    return True

def _ValueOrAssn(stream):
    if stream.is_next(':='):
        return _Expr(stream)
    return True

def _ProcCall(stream):
    if stream.is_next(')'):
        return True
    else:
        if not _Expr(stream):
            return False
        
        while stream.is_next(','):
            if not _Expr(stream):
                return False
        
        return stream.next_is(')')

def parse(source, rule=_program):
    stream = TokenStream(lex_source(source))
    try:
        return rule(stream)
    except _SyntaxError, e:
        sys.stderr.write("line %d: syntax error near %s\n" % 
                         (stream.line, stream.current_word()[1]))
        sys.exit(2)
        return False


if __name__ == '__main__':
    source = open('bsort.9.txt').read()
    parse(source)
