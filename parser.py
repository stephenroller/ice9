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
    ast = Tree(node_type='rule-expansion', value='root')
    current_node = ast
    
    def __init__(self, token_stream):
        self.stream = token_stream
        # remove the SOF token
        self.next_type_is('SOF')
    
    def into_child(self, **kwargs):
        self.current_node = self.current_node.add_child(**kwargs)
    
    def backtrack(self):
        dead_branch = self.current_node
        self.current_node = self.current_node.parent
        dead_branch.kill()
        return self.current_node
    
    def up_to_parent(self):
        self.current_node = self.current_node.parent
    
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
            toktype, tokval = self.current_word()
            self.current_node.add_child(node_type='token', value=tokval, token_type=toktype)
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
    
    def next_type_is(self, expected_type):
        """
        Expects the next type and pushes forward if it's found. Raise a
        syntax error if it isn't.
        """
        if self.is_next_type(expected_type):
            return True
        else:
            raise Ice9SyntaxError(self)

    def is_next_type(self, expected_type):
        """
        Checks the next type and pushes forward if it's found. Returns false
        if it isn't.
        """
        tokentype, tokenvalue = self.current_word()
        if tokentype == expected_type:
            toktyp, tokval = self.current_word()
            self.current_node.add_child(node_type='token', value=tokval, token_type=toktyp)
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

# voodo python magic here to add an extra parameter to all my grammar
# rules via a sneaky decorator
def grammar_rule(rule):
    # adds an optional "mandatory" paramater to rules so they throw a
    # syntax error if it doesn't work out
    def modified_rule(stream, mandatory=False):
        stream.into_child(node_type='rule-expansion', value=rule.func_name)
        retval = rule(stream)
        if mandatory and not retval:
            raise Ice9SyntaxError(stream)
        else:
            if retval:
                stream.up_to_parent()
            else:
                stream.backtrack()
            return retval
    
    modified_rule.func_name = rule.func_name
    return modified_rule

# here begins the grammar

@grammar_rule
def program(stream):
    while var(stream) or ice9_type(stream) or forward(stream) or proc(stream):
        pass
    
    return stms(stream)

@grammar_rule
def stms(stream):
    stm(stream, True)
    
    while stm(stream):
        pass
    
    return True

@grammar_rule
def stm(stream):
    return (ice9_if(stream) or ice9_do(stream) or fa(stream) or
            (stream.is_next('break') and stream.next_is(';')) or
            (stream.is_next('exit') and stream.next_is(';')) or
            (stream.is_next('return') and stream.next_is(';')) or
            (stream.is_next('write') and expr(stream, True) and stream.next_is(';')) or
            (stream.is_next('writes') and expr(stream, True) and stream.next_is(';')) or
            (expr(stream) and stream.next_is(';')) or
            stream.is_next(';'))

@grammar_rule
def ice9_if(stream):
    if stream.is_next('if'):
        if (expr(stream) and stream.next_is('->') and 
            stms(stream) and if_prime(stream)):
                return True
        else:
                raise Ice9SyntaxError(stream)

@grammar_rule
def if_prime(stream):
    if stream.is_next('[]'):
        return fi(stream)
    else:
        return stream.next_is('fi')

@grammar_rule
def fi(stream):
    if stream.is_next('else'):
        return (stream.next_is('->') and stms(stream) and 
                stream.next_is('fi'))
    else:
        return (expr(stream) and stream.next_is('->') and stms(stream) and
                if_prime(stream))

@grammar_rule
def ice9_do(stream):
    return (stream.is_next('do') and expr(stream) and 
            stream.next_is('->') and stms(stream) and stream.next_is('od'))

@grammar_rule
def fa(stream):
    return (stream.is_next('fa') and stream.next_type_is('ident') and
            stream.next_is(':=') and expr(stream) and 
            stream.next_is('to') and expr(stream) and 
            stream.next_is('->') and stms(stream) and stream.next_is('af'))

@grammar_rule
def proc(stream):
    return (stream.is_next('proc') and stream.next_type_is('ident') and
            stream.next_is('(') and dec_list(stream) and 
            stream.next_is(')') and proc_prime(stream))

@grammar_rule
def proc_prime(stream):
    if stream.is_next(':'):
        return type_id(stream) and proc_end(stream)
    else:
        return proc_end(stream)

@grammar_rule
def proc_end(stream):
    while ice9_type(stream) or var(stream):
        pass
    
    while stm(stream):
        pass
    
    return stream.next_is('end')

@grammar_rule
def id_list(stream):
    if not stream.is_next_type('ident'):
        return False
    
    while stream.is_next(','):
        if not stream.next_type_is('ident'):
            return False
    
    return True

@grammar_rule
def var(stream):
    return stream.is_next('var') and var_list(stream, True)

@grammar_rule
def var_list(stream):
    firsthalf = id_list(stream) and stream.is_next(':') and type_id(stream)
    
    if not firsthalf:
        return False
    
    while stream.is_next('['):
        stream.next_type_is('int')
        stream.next_is(']')
    
    if stream.is_next(','):
        var_list(stream, True)
    
    return True

@grammar_rule
def forward(stream):
    if not stream.is_next('forward'):
        return False
    
    if not (stream.next_type_is('ident') and
            stream.next_is('(') and 
            dec_list(stream, True) and 
            stream.next_is(')')):
                raise Ice9SyntaxError(stream)
    
    if stream.is_next(':'):
        return type_id(stream, True)
    
    return True

@grammar_rule
def dec_list(stream):
    if id_list(stream) and stream.next_is(':') and type_id(stream, True):
        while stream.is_next(','):
            dec_list(stream, True)
    
    return True

@grammar_rule
def ice9_type(stream):
    if not stream.is_next('type'):
        return False
        
    stream.next_type_is('ident')
    stream.next_is('=')
    type_id(stream, True)
    
    while stream.is_next('['):
        if not (stream.next_type_is('int') and 
                stream.next_is(']')):
                    return False
    
    return True

@grammar_rule
def type_id(stream):
    return stream.next_type_is('ident')

@grammar_rule
def expr(stream):
    return low(stream) and expr_prime(stream)

@grammar_rule
def expr_prime(stream):
    for o in ('=', '!=', '>', '<', '>=', '<='):
        if stream.is_next(o):
            return low(stream, True)
    return True

@grammar_rule
def low(stream):
    return med(stream) and low_prime(stream)

@grammar_rule
def low_prime(stream):
    if stream.is_next('+') or stream.is_next('-'):
        return med(stream, True) and low_prime(stream)
    return True 

@grammar_rule
def med(stream):
    return high(stream) and med_prime(stream)

@grammar_rule
def med_prime(stream):
    for o in ('*', '/', '%'):
        if stream.is_next(o):
            return med(stream, True) and med_prime(stream)
    return True

@grammar_rule
def high(stream):
    if stream.is_next('-') or stream.is_next('?'):
        return expr(stream, True)
    else:
        return end(stream)

@grammar_rule
def end(stream):
    if stream.is_next('('):
        return expr(stream, True) and stream.next_is(')')
    
    if stream.is_next('read'):
        return True
    
    for t in ('int', 'string', 'bool'):
        if stream.is_next_type(t):
            return True
    
    if stream.is_next_type('ident'):
        if stream.is_next('('):
            return proc_call(stream, True)
        else:
            return lvalue_prime(stream, True) and value_or_assignment(stream, True)
    else:
        return False

@grammar_rule
def lvalue_prime(stream):
    if stream.is_next('['):
        return (expr(stream, True) and stream.next_is(']') and 
                lvalue_prime(stream, True))
    
    return True

@grammar_rule
def value_or_assignment(stream):
    if stream.is_next(':='):
        return expr(stream, True)
    
    return True

@grammar_rule
def proc_call(stream):
    if stream.is_next(')'):
        return True
    else:
        expr(stream, True)
        
        while stream.is_next(','):
            expr(stream, True)
        
        return stream.next_is(')')


def parse(source, rule=program):
    stream = TokenStream(lex_source(source))
    retval = rule(stream) and stream.next_type_is('EOF')
    
    from ast import parse2ast
    parse2ast(stream.ast)
    print stream.ast
    return retval

