#!/usr/bin/env python
from lexer import lex_source
from tree import Tree

class TokenStream:
    line = 1
    stream = None
    
    def __init__(self, token_stream):
        self.stream = token_stream
    
    def current_token(self):
        if self.stream is None or len(self.stream) == 0:
            return None
        return self.stream[0]
    
    def expecting(self, expected):
        tokentype, tokenvalue = self.current_token()
        if type(expected) is tuple and len(expected) == 2:
            return expected == (tokentype, tokenvalue)
        else:
            return expected == tokenvalue or expected == tokentype
    
    def expecting_next(self, expected):
        """
        Expect a character and push forward if it's found.
        """
        if self.expecting(expected):
            self.next()
            return True
        else:
            return False
    
    def expecting_type_next(self, expected_type):
        tokentype, tokenvalue = self.current_token() 
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
            if self.current_token() == ('newline', '\n'):
                self.line += 1
            else:
                break


def _Expr(stream):
    return _Low(stream) and _ExprPrime(stream)

def _ExprPrime(stream):
    for o in ('=', '!=', '>', '<', '>=', '<='):
        if stream.expecting_next(o):
            return _Low(stream) and _ExprPrime(stream)
    return True

def _Low(stream):
    return _Med(stream) and _LowPrime(stream)

def _LowPrime(stream):
    if stream.expecting_next('+') or stream.expecting_next('-'):
        return _Med(stream) and _LowPrime(stream)
    return True 

def _Med(stream):
    return _High(stream) and _MedPrime(stream)

def _MedPrime(stream):
    for o in ('*', '/', '%'):
        if stream.expecting_next(o):
            return _Med(stream) and _MedPrime(stream)
    return True

def _High(stream):
    return _End(stream) and _HighPrime(stream)

def _HighPrime(stream):
    if stream.expecting_next('-') or stream.expecting_next('?'):
        return _Expr()
    return True

def _End(stream):
    if stream.expecting_next('('):
        return _Expr(stream) and stream.expecting_next(')')
    
    for k in ('true', 'false', 'read'):
        if stream.expecting_next(k):
            return True
    
    for t in ('int', 'string'):
        if stream.expecting_type_next(t):
            return True
    
    if stream.expecting_next('ident'):
        if stream.expecting_next('('):
            return _ProcCall(stream)
        else:
            return _lvaluePrime(stream) and _ValueOrAssn(stream)
    
    return False

def _lvaluePrime(stream):
    if stream.expecting_next('['):
        return (_Expr(stream) and stream.expecting_next(']') and 
                _lvaluePrime(stream))
    
    return True

def _ValueOrAssn(stream):
    if stream.expecting_next(':='):
        return _Expr(stream)
    return True

def _ProcCall(stream):
    if stream.expecting_next(')'):
        return True
    else:
        if not _Expr(stream):
            return False
        
        while stream.expecting_next(','):
            if not _Expr(stream):
                return False
        
        return stream.expecting_next(')')

if __name__ == '__main__':
    import pdb
    # pdb.set_trace()
    stream = TokenStream(lex_source('((x + x * stephen[stephen][2])) = 2'))
    print _Expr(stream)
