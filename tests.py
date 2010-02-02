import unittest
from ice9 import Ice9Error
from lexer import lex_source, Ice9LexicalError
from parser import *

# syntactic shorthand for all that boiler plate
def test_parse_true(rule, source):
    """
    Makes a unit test that says source *should* match rule.
    """
    class TrueTestCase(unittest.TestCase):
        def __str__(self):
            return '(%s) %s' % (rule.func_name, source)
        
        def runTest(self):
            assert parse(source, rule)
    
    return TrueTestCase

def test_full_program_file(filename):
    """
    Makes a unit test that ensures an entire program is valid
    """
    return test_parse_true(program, open(filename).read())

def test_parse_false(rule, source):
    """
    Makes a unit test that says source should *not* match rule.
    """
    class FalseTestCase(unittest.TestCase):
        def __str__(self):
            return '(not %s) %s' % (rule.func_name, source)
        
        def runTest(self):
            assert not parse(source, rule)

    return FalseTestCase


def test_parse_error(rule, source, error_value):
    """
    Makes a unit test that says source should throw an error.
    """
    class SyntaxErrorTestCase(unittest.TestCase):
        def __str__(self):
            return '(error %s) %s' % (rule.func_name, source)
        
        def runTest(self):
            try:
                parse(source, rule)
                # We should throw an error!
                assert False, 'No error thrown'
            except (Ice9Error, Ice9LexicalError, Ice9SyntaxError), e:
                assert e.error == error_value
    
    return SyntaxErrorTestCase

# some lexer tests
lexerr_illegal_character = test_parse_error(program, '@', 'illegal character (@)')
lexerr_2illegal_characters = test_parse_error(program, '$ @', 'illegal character ($)')

# expr tests
true_number = test_parse_true(expr, '3')
true_string = test_parse_true(expr, '"string test"')
true_ident = test_parse_true(expr, 'x')
true_arithmetic = test_parse_true(expr, 'x / 3 + 2 * (4 % 3) - x')
true_unary_minus = test_parse_true(expr, '- x')
true_unary_question = test_parse_true(expr, '? x')
true_compound_unary = test_parse_true(expr, 'y + - - - x')

true_proc_call = test_parse_true(expr, 'my_call(3, 4, 5)')
true_proc_call_no_param = test_parse_true(expr, 'my_call()')
true_array = test_parse_true(expr, 'foobar[1]')
true_multi_array = test_parse_true(expr, 'foobar[1][i]')

false_empty = test_parse_false(expr, '')
false_blank_statement = test_parse_false(stm, '')

se_missing_op = test_parse_error(expr, '3 x', 'syntax error near x')
se_missing_operand = test_parse_error(expr, '3 -', 'syntax error near EOF')
se_missing_un_oper = test_parse_error(expr, '?', 'syntax error near EOF')
se_extra_ident = test_parse_error(expr, '3 + 3 x', 'syntax error near x')
se_unfinished_array = test_parse_error(expr, 'foobar[1][', 'syntax error near EOF')

# stm tests
true_empty_statement = test_parse_true(stm, ';')
se_blank_statements = test_parse_error(stms, '', 'syntax error near EOF')

# if, fa, do
true_if = test_parse_true(ice9_if, 'if true -> write "hello world" ; fi')
true_if_else = test_parse_true(ice9_if, 'if true -> 3 ; [] else -> 5 ; fi')
true_if_if_else = test_parse_true(ice9_if, 'if true -> 1 ; [] false -> 2 ; fi')
true_if_if_else_else = test_parse_true(ice9_if, 'if true -> 2 ; [] false -> ; [] else -> ; fi')

se_if_missing_expr = test_parse_error(ice9_if, 'if', 'syntax error near EOF')
se_if_missing_arrow = test_parse_error(ice9_if, 'if true', 'syntax error near EOF')
se_if_missing_stm = test_parse_error(ice9_if, 'if true ->', 'syntax error near EOF')
se_if_missing_fi = test_parse_error(ice9_if, 'if true -> ;', 'syntax error near EOF')

# full programs
test_bsort = test_full_program_file('bsort.9.txt')
test_dice = test_full_program_file('dice.9.txt')
test_fact = test_full_program_file('fact.9.txt')
test_fib = test_full_program_file('fib.9.txt')
test_ifact = test_full_program_file('ifact.9.txt')
test_sticks = test_full_program_file('sticks.9.txt')


if __name__ == '__main__':
    unittest.main()