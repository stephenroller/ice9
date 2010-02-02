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
                assert False
            except (Ice9Error, Ice9LexicalError, Ice9SyntaxError), e:
                assert e.error == error_value
    
    return SyntaxErrorTestCase


# expr tests
test_number = test_parse_true(expr, '3')
test_string = test_parse_true(expr, '"string test"')
test_ident = test_parse_true(expr, 'x')
test_arithmetic = test_parse_true(expr, 'x / 3 + 2 * (4 % 3) - x')
test_unary_minus = test_parse_true(expr, '- x')
test_unary_question = test_parse_true(expr, '? x')
test_compound_unary = test_parse_true(expr, 'y + - - - x')


if __name__ == '__main__':
    unittest.main()