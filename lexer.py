#!/usr/bin/env python
try: 
    # sre is deprecated in >=python2.5
    from re import Scanner
except ImportError:
    # the old way, as on the unity machines
    from sre import Scanner

__all__ = ['TOKENS', 'lex_source']

# parser handlers
# in part from http://code.activestate.com/recipes/457664/.

TOKENS = (
    ('comment',    r"#.*(?=\n)"),
    ('newline',    r"\n"),
    ('whitespace', r"[\t ]+"),
    ('operator',   r"(->|:=|!=|>=|<=|[<>\-?+*/%=])"),
    ('punc',       r"[;:,\[\]\(\)]"),
    ('keyword',    r"(if|fi|else|do|od|false|true|fa|af|to|proc|end|return)"),
    ('keyword',    r"(var|type|break|exit|forward|writes|write|read)"),
    ('keyword',    r"(bool|int)"),
    ('ident',      r"[A-Za-z][A-Za-z0-9_]*"),
    ('int',        r"\d+"),
    ('string',     r'"[^"\n]*"'),
    ('string',     r"'[^'\n]*'"),
)

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
        lineno = sum(1 for typ,tok in tokenized if typ == 'newline') + 1
        raise ValueError('line %d: illegal character (%s)' %
                         (lineno, unused[0]))
    
    return tokenized

if __name__ == '__main__':
    source = open('ifact.9.txt').read()
    
    print source
    print "-" * 80
    
    tokenized = lex_source(source)
    for token in tokenized:
        print token
