# Project 4 README
## Stephen Roller

**I opt to use ice9 input for my program.**

**_Please run 'add python25' before running my program_**

My ice9 compiler runs with optimizations turned on by default. The -s flag
(s for slow) can be passed to ice9 in order to specify optimizations should
be turned off.

Optimizations on:

    $ ./ice9 < infile.9 > outfile.tm

Optimizations **off**:

    $ ./ice9 -s < infile.9 > outfile.tm


My unit tests may be run with:

    $ python tests.py

and you may view them in in the tests.py. Each unit tests is run optimized
and unoptimized to ensure both outputs match the target.

-----------------------------------------------------------------------------

Implemented Optimizations
=========================

AST Level Optimizations
-----------------------

### Constant Folding
Most of the constant folding was performed at the AST level (astoptimizer.py).

    $ echo "writes 3 + 4;"  | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 7(0)        * load constant: 7
        2: OUT       1, 0, 0        * writing int
        3: HALT      0, 0, 0        * END OF PROGRAM

### Identity operations (* 1, + 0, etc)
These were somewhat performed by tree transformations, but were also further 
improved later on.

    $ echo "writes read + 0;"  | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: IN        1, 0, 0        * Read input from command line.
        2: OUT       1, 0, 0        * writing int
        3: HALT      0, 0, 0        * END OF PROGRAM

### Known conditionals
If statements are checked for true/false in their tests to see if the branch
will *always* or *never* be taken.

    $ echo "if true -> writes 3; fi" | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 3(0)        * load constant: 3
        2: OUT       1, 0, 0        * writing int
        3: HALT      0, 0, 0        * END OF PROGRAM
    
    $ echo "if false -> writes 3; fi" | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: HALT      0, 0, 0        * END OF PROGRAM

### Static string-to-integer conversion
int(s : string) will be precomputed for any non-dynamic strings:

    $ echo "writes int('3');" | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 3(0)        * load constant: 3
        2: OUT       1, 0, 0        * writing int
        3: HALT      0, 0, 0        * END OF PROGRAM

Peephole Optimizations
----------------------
I also wrote a number of peephole optimizations. All the patterns can be seen
in optimizer.py, but here is a summary:

### Sequential adds
Similar to constant folding, this will take an LDC followed by an LDA or two 
sequential LDAs and collapse them into just one operation. (See next example).

### Unnecessary pushes/pops
Any pushes followed by pops will be removed. (This one is difficult to 
demonstrate alone, but it is apparent when combined with constant folding).

    $ echo 'var a : int; a := 3; a := a + 4; writes a;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 7(1)        * load result: 7
        2: ST        1, 1(0)        * STORE variable a
        3: OUT       1, 0, 0        * writing int
        4: HALT      0, 0, 0        * END OF PROGRAM

### Strength reduction
Several operations, such as multiplying by 2 or -1, will be reduced to ADD 
or SUB operations.

    $ echo '-1 *  read;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: IN        1, 0, 0        * Read input from command line.
        2: SUB       1, 0, 1        * Invert sign.
        3: HALT      0, 0, 0        * END OF PROGRAM
    
    $ echo '2 * read;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: IN        1, 0, 0        * Read input from command line.
        2: ADD       1, 1, 1        * A * 2
        3: HALT      0, 0, 0        * END OF PROGRAM

### Sequential pops or pushes

Without optimization:

    $ echo 'proc foo() write 2; end; foo();' | ice9 -s
        ...
        11: ST        2,-1(6)       * save registers before proc call
        12: LDA       6,-1(6)       * Move (push) the stack pointer
        13: ST        3,-1(6)       * save registers before proc call
        14: LDA       6,-1(6)       * Move (push) the stack pointer
        15: ST        4,-1(6)       * save registers before proc call
        16: LDA       6,-1(6)       * Move (push) the stack pointer
        17: ST        5,-1(6)       * store the frame pointer before the call
        18: LDA       6,-1(6)       * Move (push) the stack pointer
        ...
        23: LD        5, 0(6)       * pop the frame pointer after call
        24: LDA       6, 1(6)       * Move (pop) the stack pointer
        25: LD        4, 0(6)       * remember registers from before proc call
        26: LDA       6, 1(6)       * Move (pop) the stack pointer
        27: LD        3, 0(6)       * remember registers from before proc call
        28: LDA       6, 1(6)       * Move (pop) the stack pointer
        29: LD        2, 0(6)       * remember registers from before proc call
        30: LDA       6, 1(6)       * Move (pop) the stack pointer
        ...

With optimization:

    $ echo 'proc foo() write 2; end; foo();' | ice9
        ...
        11: ST        2,-1(6)       * save registers before proc call
        12: ST        3,-2(6)       * save registers before proc call
        13: ST        4,-3(6)       * save registers before proc call
        14: ST        5,-4(6)       * store the frame pointer before the call
        15: LDA       6,-4(6)       * Move (push) the stack pointer
        ...
        20: LD        5, 0(6)       * pop the frame pointer after call
        21: LD        4, 1(6)       * remember registers from before proc call
        22: LD        3, 2(6)       * remember registers from before proc call
        23: LD        2, 3(6)       * remember registers from before proc call
        24: LDA       6, 4(6)       * Move (pop) the stack pointer
        ...

Other Optimizations
-------------------

### Dead code removal
A depth-first search of the CFG is used to find dead code
and eliminate it.

Example 1: Removing an uncalled proc:

    $ echo 'proc foo() write 2; end; write 4;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 4(0)        * load constant: 4
        2: OUT       1, 0, 0        * writing int
        3: OUTNL     0, 0, 0        * newline for write
        4: HALT      0, 0, 0        * END OF PROGRAM

Example 2: Removing unreachable code:

    $ echo 'write 1; exit; write 2;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 1(0)        * load constant: 1
        2: OUT       1, 0, 0        * writing int
        3: OUTNL     0, 0, 0        * newline for write
        4: HALT      0, 0, 0        * END OF PROGRAM

### Remove dead jumps
Useless jumps (like skipping empty proc definitions) are removed.

Without optimization (Note instruction #1):

    $ echo 'write 3;' | ice9 -s
        *  PREAMBLE
        0: LD        6, 0(0)        * Set the stack pointer
        1: JEQ       0, 0(7)        * skip proc definitions
        *  END PREAMBLE
        *  START OF PROGRAM
        2: LDC       1, 3(0)        * load constant: 3
        3: OUT       1, 0, 0        * writing int
        4: OUTNL     0, 0, 0        * newline for write
        5: HALT      0, 0, 0        * END OF PROGRAM

With optimization:

        $ echo 'write 3;' | ice9 
            0: LD        6, 0(0)        * Set the stack pointer
            1: LDC       1, 3(0)        * load constant: 3
            2: OUT       1, 0, 0        * writing int
            3: OUTNL     0, 0, 0        * newline for write
            4: HALT      0, 0, 0        * END OF PROGRAM

### Boolean conditional jumps
A special cases of the form __if (y > x) ->__, where AC1 would normally be
explicitly set to 0 or 1, and then JEQ'd.

Without optimization (note instructions #8-13)

    $ echo 'if (read > 3) -> write 4; fi' | ice9 -s
         0: LD        6, 0(0)       * Set the stack pointer
         1: JEQ       0, 0(7)       * skip proc definitions
         2: IN        1, 0, 0       * Read input from command line.
         3: ST        1,-1(6)       * Store reg 1 on the stack
         4: LDA       6,-1(6)       * Move (push) the stack pointer
         5: LDC       1, 3(0)       * load constant: 3
         6: LD        2, 0(6)       * Get reg 2 off the stack
         7: LDA       6, 1(6)       * Move (pop) the stack pointer

         8: SUB       1, 2, 1       * SUB left and right.
         9: JGT       1, 2(7)       * skip set to false
        10: LDC       1, 0(0)       * comparison is bad, set reg 1 to false
        11: JEQ       0, 1(7)       * skip set to true
        12: LDC       1, 1(0)       * compairson is good, set reg 1 to true
        13: JEQ       1, 4(7)       * if false, jump to next cond

        14: LDC       1, 4(0)       * load constant: 4
        15: OUT       1, 0, 0       * writing int
        16: OUTNL     0, 0, 0       * newline for write
        17: JEQ       0, 0(7)       * jump to end of if-then-else
        18: HALT      0, 0, 0       * END OF PROGRAM

With optimization (Note instructions #2-3):

    $ echo 'if (read > 3) -> write 4; fi' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: IN        1, 0, 0        * Read input from command line.

        2: LDA       1,-3(1)        * Subtract 3
        3: JLE       1, 3(7)        * if false, jump to next cond

        4: LDC       1, 4(0)        * load constant: 4
        5: OUT       1, 0, 0        * writing int
        6: OUTNL     0, 0, 0        * newline for write
        7: HALT      0, 0, 0        * END OF PROGRAM

Overall results
---------------

    File         # Instrs Unopt  # Instrs Opt  % Change
    --------     --------------  ------------  --------
    bsort.9           398            340          14.6%
    dice.9            248            183          26.2%
    fact.9            168            107          36.3%
    fib.9             196            123          37.2%
    ifact.9           135             97          28.1%
    sieve.9           310            251          19.0%
    sticks.9          876            556          36.5%
    ---------------------------------------------------
    Total            2331           1657          28.9%

Limitations & Unimplemented
---------------------------
Sometimes my optimizer is over-eager and will optimize out side-effect
operations. In this example, the read operation is optimized out, so the
user is never prompted at all:

    $ echo '0 * read;' | ice9
        0: LD        6, 0(0)        * Set the stack pointer
        1: LDC       1, 0(0)        * load constant: 0
        2: HALT      0, 0, 0        * END OF PROGRAM

I did not optimize array references or jump chaining. I ran out of time to
do array references and I had difficulty creating trivial examples of jump
chaining.