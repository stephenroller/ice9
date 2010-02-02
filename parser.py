#!/usr/bin/env python
import sys
from ice9 import Ice9Error
from lexer import lex_source
from tree import Tree

class Ice9SyntaxError(Ice9Error):
    def __init__(self, token_stream):
        self.line = token_stream.line
        self.error = 'syntax error near %s' % token_stream.current_word()[1]


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
            raise Ice9SyntaxError(self)
    
    def nextice9_type_is(self, expectedice9_type):
        """
        Expects the next type and pushes forward if it's found. Raise a
        syntax error if it isn't.
        """
        if self.is_next_type(expectedice9_type):
            return True
        else:
            raise Ice9SyntaxError(self)

    def is_next_type(self, expectedice9_type):
        """
        Checks the next type and pushes forward if it's found. Returns false
        if it isn't.
        """
        tokentype, tokenvalue = self.current_word()
        if tokentype == expectedice9_type:
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

def program(stream):
    while var(stream) or ice9_type(stream) or forward(stream) or proc(stream):
        pass
    
    return stms(stream)

def stms(stream):
    if not stm(stream):
        raise Ice9SyntaxError(stream)
    
    while stm(stream):
        pass
    
    return True

def stm(stream):
    return (ice9_if(stream) or ice9_do(stream) or fa(stream) or
            (stream.is_next('break') and stream.next_is(';')) or
            (stream.is_next('exit') and stream.next_is(';')) or
            (stream.is_next('return') and stream.next_is(';')) or
            (stream.is_next('write') and expr(stream) and stream.next_is(';')) or
            (stream.is_next('writes') and expr(stream) and stream.next_is(';')) or
            (expr(stream) and stream.next_is(';')) or
            stream.is_next(';'))

def ice9_if(stream):
    if stream.is_next('if'):
        if (expr(stream) and stream.next_is('->') and 
            stms(stream) and if_prime(stream)):
                return True
        else:
                raise Ice9SyntaxError(stream)

def if_prime(stream):
    if stream.is_next('[]'):
        return fi(stream)
    else:
        return stream.next_is('fi')

def fi(stream):
    if stream.is_next('else'):
        return (stream.next_is('->') and stms(stream) and 
                stream.next_is('fi'))
    else:
        return (expr(stream) and stream.next_is('->') and stms(stream) and
                if_prime(stream))

def ice9_do(stream):
    return (stream.is_next('do') and expr(stream) and 
            stream.next_is('->') and stms(stream) and stream.next_is('od'))

def fa(stream):
    return (stream.is_next('fa') and stream.nextice9_type_is('ident') and
            stream.next_is(':=') and expr(stream) and 
            stream.next_is('to') and expr(stream) and 
            stream.next_is('->') and stms(stream) and stream.next_is('af'))

def proc(stream):
    return (stream.is_next('proc') and stream.nextice9_type_is('ident') and
            stream.next_is('(') and dec_list(stream) and 
            stream.next_is(')') and proc_prime(stream))

def proc_prime(stream):
    if stream.is_next(':'):
        return type_id(stream) and proc_end(stream)
    else:
        return proc_end(stream)

def proc_end(stream):
    while ice9_type(stream) or var(stream):
        pass
    
    while stm(stream):
        pass
    
    return stream.next_is('end')

def id_list(stream):
    if not stream.is_next_type('ident'):
        return False
    
    while stream.is_next(','):
        if not stream.nextice9_type_is('ident'):
            return False
    
    return True

def var(stream):
    return stream.is_next('var') and var_list(stream)

def var_list(stream):
    firsthalf = id_list(stream) and stream.is_next(':') and type_id(stream)
    
    if not firsthalf:
        return False
    
    while stream.is_next('['):
        if not (stream.nextice9_type_is('int') and stream.next_is(']')):
            return False
    
    while stream.is_next(','):
        if not var_list(stream):
            return False
    
    return True

def forward(stream):
    if not stream.is_next('forward'):
        return False
    
    if not (stream.nextice9_type_is('ident') and
            stream.next_is('(') and 
            dec_list(stream) and 
            stream.next_is(')')):
                raise Ice9SyntaxError(stream)
    
    if stream.is_next(':'):
        return type_id(stream)
    
    return True

def dec_list(stream):
    if id_list(stream) and stream.next_is(':') and type_id(stream):
        while stream.is_next(','):
            dec_list(stream)
    return True

def ice9_type(stream):
    firsthalf = (stream.is_next('type') and 
                 stream.nextice9_type_is('ident') and
                 stream.is_next('=') and
                 type_id(stream))
    
    if not firsthalf:
        return False
    
    while stream.is_next('['):
        if not (stream.nextice9_type_is('int') and 
                stream.next_is(']')):
                    return False
    
    return True

def type_id(stream):
    return stream.nextice9_type_is('ident')

def expr(stream):
    return low(stream) and expr_prime(stream)

def expr_prime(stream):
    for o in ('=', '!=', '>', '<', '>=', '<='):
        if stream.is_next(o):
            return low(stream) and expr_prime(stream)
    return True

def low(stream):
    return med(stream) and low_prime(stream)

def low_prime(stream):
    if stream.is_next('+') or stream.is_next('-'):
        return med(stream) and low_prime(stream)
    return True 

def med(stream):
    return high(stream) and med_prime(stream)

def med_prime(stream):
    for o in ('*', '/', '%'):
        if stream.is_next(o):
            return med(stream) and med_prime(stream)
    return True

def high(stream):
    return end(stream) and high_prime(stream)

def high_prime(stream):
    if stream.is_next('-') or stream.is_next('?'):
        return expr(stream)
    return True

def end(stream):
    if stream.is_next('('):
        return expr(stream) and stream.next_is(')')
    
    for k in ('true', 'false', 'read'):
        if stream.is_next(k):
            return True
    
    for t in ('int', 'string'):
        if stream.is_next_type(t):
            return True
    
    if stream.is_next_type('ident'):
        if stream.is_next('('):
            return proc_call(stream)
        else:
            return lvalue_prime(stream) and value_or_assignment(stream)
    else:
        return False

def lvalue_prime(stream):
    if stream.is_next('['):
        return (expr(stream) and stream.next_is(']') and 
                lvalue_prime(stream))
    
    return True

def value_or_assignment(stream):
    if stream.is_next(':='):
        return expr(stream)
    return True

def proc_call(stream):
    if stream.is_next(')'):
        return True
    else:
        if not expr(stream):
            return False
        
        while stream.is_next(','):
            if not expr(stream):
                return False
        
        return stream.next_is(')')

def parse(source, rule=program):
    stream = TokenStream(lex_source(source))
    
    retval = rule(stream)
    
    if not stream.expecting('EOF'):
        raise Ice9SyntaxError(stream)
    
    return retval

