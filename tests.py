import unittest
import ice9
import os
import sys
from StringIO import StringIO
from ice9 import Ice9Error
from lexer import lex_source, Ice9LexicalError
from parser import *
from subprocess import Popen, PIPE

def make_community_test(test_id):
    """
    Makes a unit test that runs a community test.
    """
    sourcefile = 'community_tests/tests/test%d.9' % test_id
    expectedfile = 'community_tests/expected/test%d.out' % test_id
    inputfile = 'community_tests/tests/input%d.txt' % test_id
    
    try:
        source = open(sourcefile).read()
        expected = open(expectedfile).read()
        expected = expected[0:expected.rindex("Number of ")]
        expected = expected[expected.index("\n")+1:]
    except IOError, e:
        return
    
    if os.path.exists(inputfile):
        inputtext = open(inputfile).read()
    else:
        inputtext = ""
        
    source = "# test #%d\n" % test_id + source
    return make_compile_test(source, expected, inputtext)
    

def make_compile_test(source, expected, pgrminput=""):
    """
    Makes a unit test that compiles and runs the program, ensuring its output
    is correct.
    """
    expected = expected.rstrip()
    
    class CompileTest(unittest.TestCase):
        def __str__(self):
            return repr(source)
        
        def _run_file(self, filename):
            pipe = Popen(['./tm', '-b', filename], 
                         stdin=PIPE, stdout=PIPE, close_fds=True)
            
            if pgrminput:
                pipe.stdin.write(pgrminput)
            
            output = pipe.stdout.read()
            output = output.rstrip().split('\n')
            
            # skip 'Loading...' 
            output = output[1:]
            # and remove 'Number of instructions' stuff.
            pos = output[-1].rindex("Number of instructions")
            output[-1] = output[-1][:pos]
            
            output = '\n'.join(output).rstrip()
            
            pipe.stdout.close()
            
            return output
        
        def _run_source(self, source, optimize):
            import tempfile
            code = ice9.compile(source, optimize)
            # f = tempfile.NamedTemporaryFile('w', suffix='.tm')
            f = open("test.tm", "w")
            f.write(code)
            f.close()
            output = self._run_file("test.tm")
            return output
            
        
        def runTest(self):
            unoptimized_output = self._run_source(source, False)
            
            assert unoptimized_output == expected, (
                   "Unoptimized output: \n%s\n\nis not expected:\n%s" % 
                        (repr(unoptimized_output), repr(expected)))
            
            optimized_output = self._run_source(source, True)
            
            assert optimized_output == expected, (
                   "Optimized output: \n%s\n\nis not expected:\n%s" % 
                        (repr(optimized_output), repr(expected)))
    
    return CompileTest

# basic writes
write_int = make_compile_test("write 3;", "3")
write_true = make_compile_test("write true;", "1")
write_false = make_compile_test("write false;", "0")

# integer tests
test_negint = make_compile_test("write - 3;", "-3")
test_add = make_compile_test("write 1 + 2;", "3")
test_sub = make_compile_test("write 2 - 1;", "1")
test_mul = make_compile_test("write 2 * 3;", "6")
test_div = make_compile_test("write 8 / 2;", "4")

test_arith0 = make_compile_test("writes 1 - 1 - 1;", "-1")
test_arith1 = make_compile_test("writes 5 - 5 - 5 - 5;", "-10")
test_arith2 = make_compile_test("writes 16 / 4 / 3;", "1")
test_arith3 = make_compile_test("writes (4 - 3) * 2;", "2")
test_arith4 = make_compile_test("writes - - - 5;", "-5")
test_arith5 = make_compile_test("writes - - 5;", "5")
test_arith6 = make_compile_test("writes 0 - - - 5;", "-5")

# modulus
test_mod1 = make_compile_test("writes 3 % 2;", "1")
test_mod2 = make_compile_test("writes 3 % 1;", "0")
test_mod3 = make_compile_test("writes 3 % 3;", "0")
test_mod4 = make_compile_test("writes 5 % 2;", "1")
test_mod5 = make_compile_test("writes -3 % 2;", "-1")
test_mod6 = make_compile_test("writes 8 % 5 / 2;", "1")
test_mod7 = make_compile_test("writes 8 / 5 % 2;", "1")

# boolean tests
test_or1 = make_compile_test("write true + true;", "1")
test_or2 = make_compile_test("write true + false;", "1")
test_or3 = make_compile_test("write false + false;", "0")
test_and1 = make_compile_test("write true * true;", "1")
test_and2 = make_compile_test("write true * false;", "0")
test_and3 = make_compile_test("write false * true;", "0")
test_neg = make_compile_test("write - true;", "0")
test_neg2 = make_compile_test("write - false;", "1")

# comparison tests
test_compare1 = make_compile_test("writes ? (3 = 3);", "1 ")
test_compare2 = make_compile_test("writes ? (3 = 4);", "0 ")
test_compare3 = make_compile_test("writes ? (3 != 3);", "0 ")
test_compare4 = make_compile_test("writes ? (3 != 4);", "1 ")
test_compare5 = make_compile_test("writes ? (1 < 3);", "1 ")
test_compare6 = make_compile_test("writes ? (3 < 3);", "0 ")
test_compare7 = make_compile_test("writes ? (3 > 3);", "0 ")
test_compare8 = make_compile_test("writes ? (4 > 3);", "1 ")
test_compare9 = make_compile_test("writes ? (4 >= 3);", "1 ")
test_compare10 = make_compile_test("writes ? (4 <= 3);", "0 ")
test_compare11 = make_compile_test("writes ? (3 <= 4);", "1 ")


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
test_do_false = make_compile_test("var i : int; do i < 0 -> i := i + 1; writes i; od", "")

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
test_proc_earlyreturn = make_compile_test("""
    proc test ()
    	writes 1;
    	return;
    	writes 2;
    end
    test();
    writes 3;
    """,
    "1 3 "
)
test_proc_earlyreturn2 = make_compile_test("""
    proc test() : int
        test := 1;
        return;
        test := 2;
    end
    
    writes test();
    """,
    "1 "
)

# return/exit stuff
test_exit = make_compile_test("writes 1; exit; writes 2;", "1 ")
test_returnexit = make_compile_test("writes 1; return; writes 2;", "1 ")
test_proc_exit = make_compile_test("proc test () writes 1; exit; writes 2; end; test(); writes 3;", "1")

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
    ' \n'.join(c for c in '1101100100')
)

# fa loops
test_fa1 = make_compile_test("fa i := 1 to 3 -> writes i; af", "1 2 3")
test_fa2 = make_compile_test("fa i := 1 to 3 -> fa j := i to 3 -> writes j; af; af", "1 2 3 2 3 3")
test_fa3 = make_compile_test("fa i := 1 to 3 -> writes 1 + 2 + i; af", "4 5 6")
test_fa4 = make_compile_test("fa i := 1 to 3 -> fa j := i to 3 -> writes 1 + 2 + i; af; af", "4 4 4 5 5 6")
test_fa5 = make_compile_test("fa i := 1 to 0 -> writes i; af", "")
test_fa6 = make_compile_test("""
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

test_faexit = make_compile_test("fa i := 1 to 3 -> writes i; exit; af", "1 ")

test_fa7 = make_compile_test("""
fa i := 1 to 2 -> 
    fa i := 1 to 2 -> 
        fa i := 1 to 3 ->
            writes i; 
        af
        writes i;
    af 
    writes i;
af
""", "1 2 3 1 1 2 3 2 1 1 2 3 1 1 2 3 2 2")

test_arrays1 = make_compile_test("""
var a : int[3]
fa i := 0 to 2 ->
    a[i] := i;
    writes a[i];
af;
""",
"0 1 2")

test_arrays2 = make_compile_test("""
var a : int[3]
fa i := 1 to 3 ->
    a[i - 1] := i - 1;
af
fa i := 1 to 3 ->
    writes a[i - 1];
af
""",
"0 1 2")

test_arrays3 = make_compile_test("""
var a : int[3][2]

a[0][0] := 1;
a[1][0] := 2;
a[0][1] := 3;
a[1][1] := 4;
a[2][0] := 5;
a[0][0] := 6;

writes a[0][0];
writes a[1][0];
writes a[0][1];
writes a[1][1];
writes a[2][0];
""",
"6 2 3 4 5")

test_arrays4 = make_compile_test("""
type rgb = int[3]
var color : rgb

proc setcolor(a : rgb)
    fa i := 0 to 5 ->
        a[i % 3] := i;
    af
end

setcolor(color);

fa i := 0 to 5 ->
    writes color[i % 3];
af
""",
"3 4 5 3 4 5")

test_arrays5 = make_compile_test("""
# mixed global and local array referencing

type rgb = int[3]
var color : rgb

proc c(a : rgb)
    writes a[0];
    writes a[1];
    writes a[2];
    
    a[2] := 4;
    
    writes color[0];
    writes color[1];
    writes color[2];
end

color[0] := 2;
color[1] := 3;
c(color);

writes color[0];
writes color[1];
writes color[2];
""",
"2 3 0 2 3 4 2 3 4")

test_array_out_of_bounds = make_compile_test(
    "var a : int[3] ; writes a[-1];",
    "Arrays bounds violation\n"
)
test_array_out_of_bounds = make_compile_test(
    "var a : int[3] ; writes a[3];",
    "Arrays bounds violation\n"
)

test_strings1 = make_compile_test("""
write 'test';
write 'foo';
""",
"test\nfoo\n")

test_strings2 = make_compile_test("""
var test : str;

test := "this is a test";

write test;
""",
"this is a test\n")

test_multi_push = make_compile_test("""
proc foo ()
	writes 0;
end

fa i := 1 to 3 ->
    foo (); 
    writes i;
af
""", 
"0 1 0 2 0 3")

test_times_2 = make_compile_test("""
var a : int;
a := 3;
a := a * 2;
writes a;
""",
"6")

test_times_neg2 = make_compile_test("""
var a : int;
a := 3;
a := a * -2;
writes a;
""",
"-6")

test_add_2 = make_compile_test("""
var a : int;
a := 3;
a := a + -2;
writes a;
""",
"1")

test_sub_const = make_compile_test(
    "if read > 3 -> write 5; fi",
    "Enter integer value: 5",
    "4\n"
)

test_sub_const2 = make_compile_test(
    "if read > 3 -> write 5; fi",
    "Enter integer value: ",
    "3\n"
)

test_div_const = make_compile_test(
    "var a : int; a := 5; write a / 4;",
    "1"
)


# for i in xrange(1, 258):
#     globals()["community_test%d" % i] = make_community_test(i)

if __name__ == '__main__':
    unittest.main()
