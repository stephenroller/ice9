#!/usr/bin/env python
import sys
from ice9 import Ice9Error
try: 
    # sre is deprecated in >=python2.5
    from re import Scanner
except ImportError:
    # the old way, as on the unity machines
    from sre import Scanner

__all__ = ['TOKENS', 'lex_source', 'Ice9LexicalError']

# parser handlers
# in part from http://code.activestate.com/recipes/457664/.

TOKENS = (
    ('comment',    r"#.*(?=\n?)"),
    ('newline',    r"\n"),
    ('whitespace', r"[\t ]+"),
    ('operator',   r"(\[\]|->|:=|!=|>=|<=|[<>\-?+*/%=])"),
    ('punc',       r"[;:,\[\]\(\)]"),
    ('keyword',    r"\b(if|fi|else|do|od|fa|af|to|proc|end|var)\b"),
    ('keyword',    r"\b(type|break|exit|forward|writes|write|read|return)\b"),
    ('bool',       r"\b(true|false)\b"),
    ('ident',      r"[A-Za-z][A-Za-z0-9_]*"),
    ('int',        r"\d+"),
    ('string',     r'"[^"\n]*"'),
    ('string',     r"'[^'\n]*'"),
)

class Ice9LexicalError(Ice9Error):
    pass

def make_token(typ):
    """
    Used for python's builtin Scanner class. Tokens are passed through
    filter functions. This builts filter functions that attach the type
    of regex they matched.
    """
    # ignore whitespace and comments right away
    if typ == 'whitespace' or typ == 'comment':
        return None
    
    # otherwise, return the token type along with the text of the token
    def _fn(scanner, token):
        return typ, token
    
    return _fn

def lex_source(source):
    """
    Lexes the source into ice9 tokens. Returns a list of 
    (token type, token string) pairs.
    
    May raise a ValueError in case of a syntax error.
    """
    scanner_tokens = [(regex, make_token(typ)) for typ, regex in TOKENS]
    scanner = Scanner(scanner_tokens)
    
    # use python's scanner class to tokenize the input
    tokenized, unused = scanner.scan(source)
    
    if unused != '':
        # unexpected character broke the flow!
        lineno = sum(1 for typ,tok in tokenized if typ == 'newline') + 1
        raise Ice9LexicalError(lineno, 'illegal character (%s)' % unused[0])
    
    # mark the start and end of the file
    tokenized.insert(0, ('SOF', 'start of file'))
    tokenized.append(('EOF', 'end of file'))
    return tokenized
