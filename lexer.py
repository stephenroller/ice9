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
    ('operator',   r"(->|:=|!=|>=|<=|[<>\-?+*/%=])"),
    ('punc',       r"[;:,\[\]\(\)]"),
    ('keyword',    r"(if|fi|else|do|od|false|true|fa|af|to|proc|end|return)"),
    ('keyword',    r"(var|type|break|exit|forward|writes|write|read)"),
    ('keyword',    r"(bool,int)"),
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

source = \
"""
var seive : bool [1000]
var N, L, cnt : int

N := 1000;
L := N/2;

seive[1] := false;  # one is not prime

fa i := 2 to 1000 -> seive[i] := true; af

# there is a tighter limit, but this will do
fa i := 2 to L ->
   #writes "working on number "; write i;

   fa j := i+1 to N ->
      if j % i = 0 ->
      	 # i divides j => j is not prime
	 seive[j] := false;
      fi
   af
af

writes "The prime numbers under "; writes N; write " are:";
writes "\\t";

cnt := 0;
fa i := 2 to N ->
  if seive[i] -> 
     writes i; 
     writes "\\t"; 
     cnt := cnt + 1; 
     if cnt > 8 -> 
       writes "\\n\\t";
       cnt := 0;
     fi   
  fi
af
write "";
"""

print source
print "-" * 80
tokenized, unused = scanner.scan(source)
for token in tokenized:
    print token
