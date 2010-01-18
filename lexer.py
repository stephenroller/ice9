try: 
    from re import Scanner
except ImportError:
    from sre import Scanner

# parser handlers
# in part from http://code.activestate.com/recipes/457664/.

TOKENS = (
    ('comment',    r"#.*(?=\n)"),
    ('newline',    r"\n"),
    ('whitespace', r"[\t ]+"),
    ('semicolon',  r";"),
    ('keyword',    r"(if|else|fi|do|fa|break|exit|write|writes)"),
    ('ident',      r"[A-Za-z][A-Za-z0-9_]*"),
    ('int',        r"\d+"),
    ('string',     r'"[^"\n]*"'),
    ('string',     r"'[^'\n]*'"),
)

def make_token(typ):
    # ignore whitespace and comments right away
    if typ == 'whitespace' or typ == 'comment':
        return None
    
    # otherwise, return the token type along with the text of the token
    def _fn(scanner, token):
        return typ, token
    
    return _fn

scanner_tokens = [(regex, make_token(typ)) for typ, regex in TOKENS]
scanner = Scanner(scanner_tokens)

print scanner.scan(
"""
# bubble sort

var n, t: int
var a: int[100]

write "Input length of array (1-100):";
n := read;
if (n < 1) + (n > 100) -> write "wrong"; exit; fi

n := n - 1;	# set n to last element

fa i := 0 to n ->
  writes "Input ";
  writes i+1;
  writes ": ";
  a[i] := read;
af

fa i := 0 to n-1 ->
  fa j := i+1 to n ->
    if a[i] > a[j] ->
      t := a[i];
      a[i] := a[j];
      a[j] := t;
    fi
  af
af

write "Sorted list:";
fa i := 0 to n -> write a[i]; af
)
"""
)