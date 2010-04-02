import unittest
import ice9
import os
from StringIO import StringIO
from ice9 import Ice9Error
from lexer import lex_source, Ice9LexicalError
from parser import *
from subprocess import Popen, PIPE

def make_community_test(test_id):
    """
    Makes a unit test that runs a community test.
    """
    class CommunityTest(unittest.TestCase):
        def __str__(self):
            return '(community test %d)' % test_id
        
        def runTest(self):
            fakestderr = StringIO()
            realstderr, sys.stderr = sys.stderr, fakestderr
            try:
                ice9.main('community_tests/tests/test%d.9' % test_id)
            except SystemExit:
                pass
            sys.stderr = realstderr
            out = fakestderr.getvalue()
            expected = file('community_tests/expected/test%d.out' % test_id).read()
            assert out.rstrip() == expected.rstrip(), (
                "output '%s' != expected '%s'" % (out.rstrip(), expected.rstrip()))
    
    return CommunityTest

def make_compile_test(source, expected):
    """
    Makes a unit test that compiles and runs the program, ensuring its output
    is correct.
    """
    expected = expected.rstrip()
    class CompileTest(unittest.TestCase):
        def __str__(self):
            return repr(source)
        
        def runTest(self):
            FILENAME = 'test.tm'
            
            code = ice9.compile(source)
            
            f = open(FILENAME, 'w')
            f.write(code)
            f.close()
            
            pipe = Popen(['tm', '-b', FILENAME], stdin=PIPE, stdout=PIPE, close_fds=True)
            pipe.stdin.write(code)
            pipe.stdin.close()
            
            output = pipe.stdout.read()
            output = output.rstrip().split('\n')
            
            # skip 'Loading...' 
            output = output[1:]
            # and remove 'Number of instructions' stuff.
            pos = output[-1].rindex("Number of instructions")
            output[-1] = output[-1][:pos]
            
            output = '\n'.join(output).rstrip()
            
            pipe.stdout.close()
            
            # and get rid of the test file
            os.remove(FILENAME)
            
            assert output == expected, (
                   "Output (%s) is not expected (%s)" % 
                        (repr(output), repr(expected)))
    
    return CompileTest

# basic writes
write_int = make_compile_test("write 3;", "3")
write_true = make_compile_test("write true;", "T")
write_false = make_compile_test("write false;", "F")

# integer tests
test_negint = make_compile_test("write - 3;", "-3")
test_add = make_compile_test("write 1 + 2;", "3")
test_sub = make_compile_test("write 2 - 1;", "1")
test_mul = make_compile_test("write 2 * 3;", "6")
test_div = make_compile_test("write 8 / 2;", "4")

# boolean tests
test_or1 = make_compile_test("write true + true;", "T")
test_or2 = make_compile_test("write true + false;", "T")
test_or3 = make_compile_test("write false + false;", "F")
test_and1 = make_compile_test("write true * true;", "T")
test_and2 = make_compile_test("write true * false;", "F")
test_and3 = make_compile_test("write false * true;", "F")
test_neg = make_compile_test("write - true;", "F")
test_neg2 = make_compile_test("write - false;", "T")

# if tests
test_if1 = make_compile_test("if true -> write 1; fi", "1")
test_if2 = make_compile_test("if false -> write 1; fi", "")
test_if3 = make_compile_test("if true -> write 1; [] else -> write 2; fi", "1")
test_if4 = make_compile_test("if false -> write 1; [] else -> write 2; fi", "2")
test_if5 = make_compile_test(
    "if false -> write 1; [] true -> write 2; [] else -> write 3; fi", 
    "2"
)
test_if5 = make_compile_test(
    "if false -> write 1; [] false -> write 2; [] else -> write 3; fi", 
    "3"
)
# var tests
test_var = make_compile_test("var i : int; i := 3; write i;", "3")
test_var_add = make_compile_test("var i : int; i := 1; i := i + 2; write i;", "3")

# loop tests
test_do_loop = make_compile_test(
    "var i : int; do i < 3 -> i := i + 1; write i; od;", 
    "1 \n2 \n3"
)
# proc tests
test_basic_proc = make_compile_test("proc a() write 1; end; a(); a();", "1 \n1")
test_compnd_proc = make_compile_test(
    "proc a(); write 0; end proc b() write 1; a(); end; b();", 
    "1 \n0"
)
test_proc_retval = make_compile_test(
    "proc add(x, y : int) : int add := x + y; end; write add(3, 4);", 
    "7"
)

# test short circuiting
test_sc1 = make_compile_test(
    """
    proc rettrue() : bool
        rettrue := true;
        write rettrue;
    end
    proc retfalse() : bool
        retfalse := false;
        write retfalse;
    end
    
    # short circuit or, should print true true
    write rettrue() + retfalse();
    # long circuit or, should print false true true
    write retfalse() + rettrue();
    # short circuit and, should print false false
    write retfalse() * retfalse();
    # long circuit and, should print true false false
    write rettrue() * retfalse();
    """,
    ' \n'.join(c for c in 'TTFTTFFTFF')
)

# fa loops
test_fa1 = make_compile_test("fa i := 1 to 3 -> writes i; af", "1 2 3")
test_fa2 = make_compile_test("fa i := 1 to 3 -> fa j := i to 3 -> writes j; af; af", "1 2 3 2 3 3")
test_fa3 = make_compile_test("fa i := 1 to 3 -> writes 1 + 2 + i; af", "4 5 6")
test_fa4 = make_compile_test("fa i := 1 to 3 -> fa j := i to 3 -> writes 1 + 2 + i; af; af", "4 4 4 5 5 6")
test_fa5 = make_compile_test("""
proc doublefa () 
    fa i := 1 to 3 ->
        fa j := i to 3 ->
            writes 1 + j + 2 + i;
        af
    af
end

doublefa();
""",
"5 6 7 7 8 9")

if __name__ == '__main__':
    unittest.main()
