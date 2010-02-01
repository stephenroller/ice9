#!/usr/bin/env python
from lexer import lex_source
from tree import Tree

class TokenStream:
    line = 1
    stream = None
    
    def __init__(self, token_stream):
        self.stream = token_stream
    
    def next_word(self):
        if self.stream is None or len(self.stream) == 0:
            return None
        return self.stream[0]
    
    def expecting(self, expected):
        ct = self.next_word()
        if ct is None:
            return False
        
        tokentype, tokenvalue = ct
        if type(expected) is tuple and len(expected) == 2:
            return expected == (tokentype, tokenvalue)
        else:
            return expected == tokenvalue or expected == tokentype
    
    def next_is(self, expected):
        """
        Expect a character and push forward if it's found.
        """
        if self.expecting(expected):
            self.next()
            return True
        else:
            return False
    
    def next_type_is(self, expected_type):
        if self.next_word() is None:
            return False
        
        tokentype, tokenvalue = self.next_word()
        if tokentype == expected_type:
            self.next()
            return True
        return False
    
    def peak(self, n=1):
        """
        Look n characters ahead, where n=0 is the current token, n=1 is the
        second token, etc.
        """
        return self.stream[n] or None
    
    def next(self):
        while True:
            self.stream.pop(0)
            if self.next_word() == ('newline', '\n'):
                self.line += 1
            else:
                break


def _program(stream):
    while _var(stream) or _type(stream) or _forward(stream) or _proc(stream):
        pass
    
    return _stms(stream) and stream.next_is('EOF')

def _stms(stream):
    if not _stm(stream):
        return False
    
    while _stm(stream):
        pass
    
    return True

def _stm(stream):
    return (_if(stream) or _do(stream) or _fa(stream) or
            (stream.next_is('break') and stream.next_is(';')) or
            (stream.next_is('exit') and stream.next_is(';')) or
            (stream.next_is('return') and stream.next_is(';')) or
            (stream.next_is('write') and _Expr(stream) and stream.next_is(';')) or
            (stream.next_is('writes') and _Expr(stream) and stream.next_is(';')) or
            (_Expr(stream) and stream.next_is(';')) or
            stream.next_is(';'))

def _if(stream):
    return (stream.next_is('if') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and _ifPrime(stream))

def _ifPrime(stream):
    if stream.next_is('[]'):
        return _fi(stream)
    else:
        return stream.next_is('fi')

def _fi(stream):
    if stream.next_is('else'):
        return (stream.next_is('->') and _stms(stream) and 
                stream.next_is('fi'))
    else:
        return (_Expr(stream) and stream.next_is('->') and _stms(stream) and
                _ifPrime(stream))

def _do(stream):
    return (stream.next_is('do') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and stream.next_is('od'))

def _fa(stream):
    return (stream.next_is('fa') and stream.next_type_is('ident') and
            stream.next_is(':=') and _Expr(stream) and 
            stream.next_is('to') and _Expr(stream) and 
            stream.next_is('->') and _stms(stream) and stream.next_is('af'))

def _proc(stream):
    return (stream.next_is('proc') and stream.next_type_is('ident') and
            stream.next_is('(') and _declist(stream) and 
            stream.next_is(')') and _procPrime(stream))

def _procPrime(stream):
    if stream.next_is(':'):
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
    if not stream.next_type_is('ident'):
        return False
    
    while stream.next_is(','):
        if not stream.next_type_is('ident'):
            return False
    
    return True

def _var(stream):
    return stream.next_is('var') and _varlist(stream)

def _varlist(stream):
    firsthalf = _idlist(stream) and stream.next_is(':') and _typeid(stream)
    
    if not firsthalf:
        return False
    
    while stream.next_is('['):
        if not (stream.next_type_is('int') and stream.next_is(']')):
            return False
    
    while stream.next_is(','):
        if not _varlist(stream):
            return False
    
    return True

def _forward(stream):
    firsthalf = (stream.next_is('forward') and 
                 stream.next_type_is('ident') and
                 stream.next_is('(') and 
                 _declist(stream) and 
                 stream.next_is(')'))
    
    if not firsthalf:
        return False
    
    if stream.next_is(':'):
        return _typeid(stream)
    
    return True

def _declist(stream):
    if _idlist(stream) and stream.next_is(':') and _typeid(stream):
        while stream.next_is(','):
            _declist(stream)
    return True

def _type(stream):
    firsthalf = (stream.next_is('type') and 
                 stream.next_type_is('ident') and
                 stream.next_is('=') and
                 _typeid(stream))
    
    if not firsthalf:
        return False
    
    while stream.next_is('['):
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
        if stream.next_is(o):
            return _Low(stream) and _ExprPrime(stream)
    return True

def _Low(stream):
    return _Med(stream) and _LowPrime(stream)

def _LowPrime(stream):
    if stream.next_is('+') or stream.next_is('-'):
        return _Med(stream) and _LowPrime(stream)
    return True 

def _Med(stream):
    return _High(stream) and _MedPrime(stream)

def _MedPrime(stream):
    for o in ('*', '/', '%'):
        if stream.next_is(o):
            return _Med(stream) and _MedPrime(stream)
    return True

def _High(stream):
    return _End(stream) and _HighPrime(stream)

def _HighPrime(stream):
    if stream.next_is('-') or stream.next_is('?'):
        return _Expr(stream)
    return True

def _End(stream):
    if stream.next_is('('):
        return _Expr(stream) and stream.next_is(')')
    
    for k in ('true', 'false', 'read'):
        if stream.next_is(k):
            return True
    
    for t in ('int', 'string'):
        if stream.next_type_is(t):
            return True
    
    if stream.next_is('ident'):
        if stream.next_is('('):
            return _ProcCall(stream)
        else:
            return _lvaluePrime(stream) and _ValueOrAssn(stream)
    
    return False

def _lvaluePrime(stream):
    if stream.next_is('['):
        return (_Expr(stream) and stream.next_is(']') and 
                _lvaluePrime(stream))
    
    return True

def _ValueOrAssn(stream):
    if stream.next_is(':='):
        return _Expr(stream)
    return True

def _ProcCall(stream):
    if stream.next_is(')'):
        return True
    else:
        if not _Expr(stream):
            return False
        
        while stream.next_is(','):
            if not _Expr(stream):
                return False
        
        return stream.next_is(')')

if __name__ == '__main__':
    source = open('sticks.9.txt').read()
    print source
    print "-" * 80
    stream = TokenStream(lex_source(source))
    print _program(stream)
