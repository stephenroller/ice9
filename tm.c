/**************************************************************/
/* File: tm.c                                                 */
/* The TM ("Tiny Machine") computer                           */
/* Compiler Construction: Principles and Practice             */
/*                                                            */
/* v2.7.3  Modified VW Freeh March 9, 2010 		      */
/*	   Added command line options.			      */
/* v2.7.2  Modified VW Freeh February 23, 2010 		      */
/*	   Added OUTC instr.				      */
/*	   Added .DATA and .SDATA directives.		      */
/* v2.7.1  Modified Robert Heckendorn Nov  13, 2009           */
/*         bug fix                                            */
/* v2.7 Modified Robert Heckendorn for CS445 Apr  6, 2006     */
/*         empty line -> step, nicer tracing message          */
/* v2.6 Modified Robert Heckendorn for CS445 Mar 20, 2006     */
/*         Added OUTNL and modified OUTB and OUT instr.       */
/* v2.5 Modified Robert Heckendorn for CS445 May 11, 2005     */
/*         record at each data location the address of the    */
/*         instruction that last assigned a value there       */
/* v2.4 Modified Robert Heckendorn for CS445 Apr 22, 2004     */
/*         fix eof bug, 'd' w/o args uses last arguments and  */
/*         fixed some obscure bugs added 'u' command.         */
/* v2.3 Modified Robert Heckendorn for CS445 Apr 28, 2003     */
/*         marks memory as used or not, added 'e', -n on 'd'  */
/* v2.2 Modified Robert Heckendorn for CS445 Apr 22, 2003     */
/*         saves comments in imem, breakpoint, input break    */
/*         abort limit and other fixes                        */
/* v2.1 Modified Robert Heckendorn for CS445 Apr 21, 2003     */
/*         INB, OUTB                                          */
/* v2.0 Modified Robert Heckendorn for CS445 Apr 11, 2003     */
/*         =, load, more state reported                       */
/* v1.0 Kenneth C. Louden                                     */
/*                                                            */
/* TO COMPILE: gcc tm.c -o tm                                 */
/*                                                            */
/**************************************************************/

char *versionNumber ="TM version 2.7.3";

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
#define TRACE 1
#define NOTRACE 0
#define NOTUSED -1
#define DATA -2
#define SDATA -3
#define USED 1

/******* const *******/
#define   IADDR_SIZE  10000	/* increase for large programs */
#define   DADDR_SIZE  10000	/* increase for large programs */
#define   NO_REGS 8
#define   PC_REG  7

#define   LINESIZE  200
#define   WORDSIZE  1000        /* maximum length of a word of text */
#define   DEFAULT_ABORT_LIMIT 20000

/******* type  *******/

typedef enum
{
    opclRR,			/* reg operands r, s, t */
    opclRM,			/* reg r, mem d+s */
    opclRA			/* reg r, int d+s */
} OPCLASS;

typedef enum
{
    /* RR instructions */
    opHALT,			/* RR     halt, operands are ignored */
    opIN,			/* RR     read integer into reg(r); s and t are ignored */
    opINB,			/* RR     read bool into reg(r); s and t are ignored */
    opOUT,			/* RR     write integer from reg(r), s and t are ignored */
    opOUTB,			/* RR     write bool from reg(r), s and t are ignored */
    opOUTC,			/* RR     write char from reg(r), s and t are ignored */
    opOUTNL,			/* RR     write newline regs r, s and t are ignored */
    opADD,			/* RR     reg(r) = reg(s)+reg(t) */
    opSUB,			/* RR     reg(r) = reg(s)-reg(t) */
    opMUL,			/* RR     reg(r) = reg(s)*reg(t) */
    opDIV,			/* RR     reg(r) = reg(s)/reg(t) */
    opRRLim,			/* limit of RR opcodes */

    /* RM instructions */
    opLD,			/* RM     reg(r) = mem(d+reg(s)) */
    opST,			/* RM     mem(d+reg(s)) = reg(r) */
    opRMLim,			/* Limit of RM opcodes */

    /* RA instructions */
    opLDA,			/* RA     reg(r) = d+reg(s) */
    opLDC,			/* RA     reg(r) = d ; reg(s) is ignored */
    opJLT,			/* RA     if reg(r)<0 then reg(7) = d+reg(s) */
    opJLE,			/* RA     if reg(r)<=0 then reg(7) = d+reg(s) */
    opJGT,			/* RA     if reg(r)>0 then reg(7) = d+reg(s) */
    opJGE,			/* RA     if reg(r)>=0 then reg(7) = d+reg(s) */
    opJEQ,			/* RA     if reg(r)==0 then reg(7) = d+reg(s) */
    opJNE,			/* RA     if reg(r)!=0 then reg(7) = d+reg(s) */
    opRALim			/* Limit of RA opcodes */
} OPCODE;

typedef enum
{
    srOKAY,
    srHALT,
    srIMEM_ERR,
    srDMEM_ERR,
    srZERODIVIDE
} STEPRESULT;

char *stepResultTab[] = {
    "OK", 
    "Halted", 
    "ERROR: Instruction Memory Fault",
    "ERROR: Data Memory Fault", 
    "ERROR: Division by 0"
};


typedef struct
{
    int iop;
    int iarg1;
    int iarg2;
    int iarg3;
    char *comment;
} INSTRUCTION;

/******** global vars ********/
int iloc = 0;
int dloc = 0;
int promptflag = TRUE;
int traceflag = FALSE;
int icountflag = FALSE;
int abortLimit = DEFAULT_ABORT_LIMIT;
int pc, lastpc;
int savedbreakpoint, breakpoint;
char *emptyString = "";
char pgmName[WORDSIZE];
int instrCount = 0;
int dmemStart = 0;
int dmemCount = 0;
int dmemDown = TRUE;

INSTRUCTION iMem[IADDR_SIZE];
int iMemTag[IADDR_SIZE];
int dMem[DADDR_SIZE]; 
int dMemTag[DADDR_SIZE];
int reg[NO_REGS];

char *opCodeTab[] = {
  "HALT", "IN", "INB", "OUT", "OUTB", "OUTC", "OUTNL", "ADD", "SUB", "MUL", "DIV", "????",
    /* RR opcodes */
    "LD", "ST", "????",		/* RM opcodes */
    "LDA", "LDC", "JLT", "JLE", "JGT", "JGE", "JEQ", "JNE", "????"
    /* RA opcodes */
};





char in_Line[LINESIZE];
int lineLen;
int inCol;
int num;
char word[WORDSIZE];
char ch;

/********************************************/
int opClass(int c)
{
    if (c <= opRRLim)
	return (opclRR);
    else if (c <= opRMLim)
	return (opclRM);
    else
	return (opclRA);
}				/* opClass */



/********************************************/
void writeInstruction(int loc, int trace)
{
    printf("%4d: ", loc);
    if ((loc >= 0) && (loc<IADDR_SIZE)) {
	printf("%4s%3d,", opCodeTab[iMem[loc].iop], iMem[loc].iarg1);
	switch (opClass(iMem[loc].iop)) {
	case opclRR:
	    printf("%3d, %1d ", iMem[loc].iarg2, iMem[loc].iarg3);
	    if (trace) {
                printf("  | before:");
		printf("  r[%1d]: %-4d", iMem[loc].iarg1, reg[iMem[loc].iarg1]);
		printf("  r[%1d]: %-4d", iMem[loc].iarg2, reg[iMem[loc].iarg2]);
		printf("  r[%1d]: %-4d", iMem[loc].iarg3, reg[iMem[loc].iarg3]);
                printf("  | ");
	    }
	    break;
	case opclRM:
	case opclRA:
	    printf("%4d(%1d)", iMem[loc].iarg2, iMem[loc].iarg3);
	    if (trace) {
                int tmp;

                printf("  | before:");
		printf("  r[%1d]: %-4d", 
                       iMem[loc].iarg1, 
                       reg[iMem[loc].iarg1]);
		printf("  r[%1d]: %-4d", 
                       iMem[loc].iarg3, 
                       reg[iMem[loc].iarg3]);
//zzz
                tmp = iMem[loc].iarg2 + reg[iMem[loc].iarg3];
                if ((tmp >= 0) && (tmp<DADDR_SIZE)) {

                    printf("  m[%d]: %-4d", 
                           iMem[loc].iarg2 + reg[iMem[loc].iarg3], 
                           dMem[iMem[loc].iarg2 + reg[iMem[loc].iarg3]]);
                    printf("  | ");
                }
            }
	    break;
	}
	printf(" %s\n", iMem[loc].comment);
    }
    fflush(stdout);
}				/* writeInstruction */



/********************************************/
void getCh()
{
    if (++inCol<lineLen)
	ch = in_Line[inCol];
    else
	ch = ' ';
}				/* getCh */



/********************************************/
int nonBlank(void)
{
    while ((inCol<lineLen) && 
	   ((in_Line[inCol] == ' ') || (in_Line[inCol] == '\t'))) inCol++;
    if (inCol<lineLen) {
	ch = in_Line[inCol];
	return TRUE;
    }
    else {
	ch = ' ';
	return FALSE;
    }
}				/* nonBlank */



/********************************************/
// returns the number in num.
// returns success or failure in function value
int getNum(void)
{
    int sign;
    int term;
    int temp = FALSE;
    num = 0;

    nonBlank();
    do {
	sign = 1;
	while ((ch == '+') || (ch == '-')) {
	    temp = FALSE;
	    if (ch == '-')
		sign = -sign;
	    getCh();
	}
	term = 0;
	while (isdigit(ch)) {
	    temp = TRUE;
	    term = term*10 + (ch - '0');
	    getCh();
	}
	num = num + (term*sign);
    }
    while ((ch == '+') || (ch == '-'));
    return temp;
}				/* getNum */


/********************************************/
int getWord(void)
{
    int temp = FALSE;
    int length = 0;
    if (nonBlank()) {
	while (isalnum(ch) || ch=='=' || ch=='?') {
	    if (length<WORDSIZE - 1)
		word[length++] = ch;
	    getCh();
	}
	word[length] = '\0';
	temp = (length != 0);
    }
    return temp;
}				/* getWord */


/********************************************/
int getBool(void)
{
    nonBlank();

    num = 1;
    if ((ch=='F') || (ch=='f') || (ch=='0')) num = 0;
    getWord();

    return TRUE;
}


/********************************************/
int skipCh(char c)
{
    int temp = FALSE;
    if (nonBlank() && (ch == c)) {
	getCh();
	temp = TRUE;
    }
    return temp;
}				/* skipCh */



/********************************************/
/* note this returns a duplicate string and not true or false */
char *getRemaining(void)
{
    skipCh(')');
    if (nonBlank()) return strdup(&in_Line[inCol]);
    return emptyString;
}



/********************************************/
int atEOL(void)
{
    return (!nonBlank());
}				/* atEOL */



/********************************************/
int error(char *msg, int lineNo, int instNo)
{
    printf("ERROR: Line %d", lineNo);
    if (instNo >= 0)
	printf(" (Instruction %d)", instNo);
    printf("   %s\n", msg);
    return FALSE;
}				/* error */



/* clear registers and data memory */
void clearMachine()
{
    int regNo, loc;

    iloc = 0;
    dloc = 0;
    for (regNo = 0; regNo<NO_REGS; regNo++) reg[regNo] = 0;
    dMem[0] = DADDR_SIZE - 1;
    dMemTag[0] = NOTUSED;
    for (loc = 1; loc<DADDR_SIZE; loc++) {
      if (dMemTag[loc] != DATA && dMemTag[loc] != SDATA) {
	dMem[loc] = 0;
	dMemTag[loc] = NOTUSED;
      }
    }
    dmemStart = dMem[0];
    dmemCount = -10;
    dmemDown = TRUE;
    instrCount = 0;
}

/* clear registers, data and instruction memory */
void fullClearMachine()
{
    int loc;

    /* clear registers and data memory */
    clearMachine();
    savedbreakpoint = breakpoint = -1;

    /* zero out instruction memory */
    for (loc = 0; loc<IADDR_SIZE; loc++) {
	iMem[loc].iop = opHALT;
	iMem[loc].iarg1 = 0;
	iMem[loc].iarg2 = 0;
	iMem[loc].iarg3 = 0;
	iMem[loc].comment = "* initially empty";
	iMemTag[loc] = NOTUSED;
    }
}


int readInstructions(char *fileName)
{
    FILE *pgm;
    OPCODE op;
    int arg1, arg2, arg3;
    int loc, regNo, lineNo;
    static int datamem=1;

    /* load program */
    if (*fileName!='\0') strcpy(pgmName, fileName);
    if (strchr(pgmName, '.') == NULL) strcat(pgmName, ".tm");
    pgm = fopen(pgmName, "r");
    if (pgm == NULL) {
	printf("ERROR: file '%s' not found\n", pgmName);
	return FALSE;
    }
    printf("Loading file: %s\n", pgmName);

    /* clear the way for the new program */
    fullClearMachine();

    /* load program */
    lineNo = 0;
    while (!feof(pgm)) {
	fgets(in_Line, LINESIZE - 2, pgm);
	inCol = 0;
	lineNo++;
	lineLen = strlen(in_Line) - 1;
	if (in_Line[lineLen] == '\n')
	    in_Line[lineLen] = '\0';
	else
	    in_Line[++lineLen] = '\0';
	if ((nonBlank()) && (in_Line[inCol] == '.')) {
	  /* processing data statement */
	  if (!strncmp(".SDATA", in_Line+inCol, strlen(".SDATA"))) {
	    inCol += strlen(".SDATA");
	    for ( ; inCol < lineLen; inCol++)
	      if (in_Line[inCol] != ' ' && in_Line[inCol] != '\t')
		break;
	    if (inCol >= lineLen)
	      return error("Illegal sdata statement--no data", lineNo, loc);
	    if (in_Line[inCol] != '"')
	      return error("Illegal sdata statement--invalid format", 
			   lineNo, loc);
	    { int start=++inCol;
	      for ( ; inCol < lineLen; inCol++)
		if (in_Line[inCol] == '"')
		    break;
	      if (in_Line[inCol] !=  '"')
		return error("Illegal sdata statement--format invalid", 
			     lineNo, loc);
	      for ( ; start < inCol; start++) {
		dMemTag[datamem] = SDATA;
		dMem[datamem++] = in_Line[start];
	      }
	    }
	  }
	  else if (!strncmp(".DATA", in_Line+inCol, strlen(".DATA"))) {
	    inCol += strlen(".DATA");
	    for ( ; inCol < lineLen; inCol++)
	      if (in_Line[inCol] != ' ' && in_Line[inCol] != '\t')
		break;
	    if (inCol >= lineLen)
	      return error("Illegal data statement--no data", lineNo, loc);
	    dMemTag[datamem] = DATA;
	    dMem[datamem++] = atoi(in_Line+inCol);
	  }
	  else {
	    return error("Illegal data statement", lineNo, loc);
	  }
	}
	else if ((nonBlank()) && (in_Line[inCol] != '*')) {
	    if (!getNum())
		return error("Bad location", lineNo, -1);
	    loc = num;
	    if (loc>=IADDR_SIZE)
		return error("Location too large", lineNo, loc);
	    if (!skipCh(':'))
		return error("Missing colon", lineNo, loc);
	    if (!getWord())
		return error("Missing opcode", lineNo, loc);
	    op = opHALT;
	    while ((op<opRALim)
		   && (strncmp(opCodeTab[op], word, 4) != 0))
		op++;
	    if (strncmp(opCodeTab[op], word, 4) != 0)
		return error("Illegal opcode", lineNo, loc);
	    switch (opClass(op)) {
	    case opclRR:
                /***********************************/
		if ((!getNum()) || (num<0) || (num >= NO_REGS))
		    return error("Bad first register", lineNo, loc);
		arg1 = num;
		if (!skipCh(','))
		    return error("Missing comma", lineNo, loc);
		if ((!getNum()) || (num<0) || (num >= NO_REGS))
		    return error("Bad second register", lineNo, loc);
		arg2 = num;
		if (!skipCh(','))
		    return error("Missing comma", lineNo, loc);
		if ((!getNum()) || (num<0) || (num >= NO_REGS))
		    return error("Bad third register", lineNo, loc);
		arg3 = num;
		break;

	    case opclRM:
	    case opclRA:
                /***********************************/
		if ((!getNum()) || (num<0) || (num >= NO_REGS))
		    return error("Bad first register", lineNo, loc);
		arg1 = num;
		if (!skipCh(','))
		    return error("Missing comma", lineNo, loc);
		if (!getNum())
		    return error("Bad displacement", lineNo, loc);
		arg2 = num;
		if (!skipCh('(') && !skipCh(','))
		    return error("Missing LParen", lineNo, loc);
		if ((!getNum()) || (num<0) || (num >= NO_REGS))
		    return error("Bad second register", lineNo, loc);
		arg3 = num;
		break;
	    }
	    iMem[loc].iop = op;
	    iMem[loc].iarg1 = arg1;
	    iMem[loc].iarg2 = arg2;
	    iMem[loc].iarg3 = arg3;
	    iMem[loc].comment = getRemaining();
	    iMemTag[loc] = USED;  // correctly counts assignments to same loc
	}
    }
    return TRUE;
}				/* readInstructions */



/********************************************/
STEPRESULT stepTM(void)
{
    INSTRUCTION currentinstruction;
    int r, s, t, m;
    int ok;

    pc = reg[PC_REG];
    if ((pc<0) || (pc>=IADDR_SIZE))
	return srIMEM_ERR;

    if (pc == breakpoint) {
	savedbreakpoint = breakpoint;
	breakpoint = -1;
	return srHALT;
    }
    breakpoint = savedbreakpoint;

    lastpc = pc;
    reg[PC_REG] = pc + 1;
    currentinstruction = iMem[pc];
    instrCount++;
    switch (opClass(currentinstruction.iop)) {
    case opclRR:
        /***********************************/
	r = currentinstruction.iarg1;
	s = currentinstruction.iarg2;
	t = currentinstruction.iarg3;
	break;

    case opclRM:
        /***********************************/
	r = currentinstruction.iarg1;
	s = currentinstruction.iarg3;
	m = currentinstruction.iarg2 + reg[s];
	if ((m<0) || (m>=DADDR_SIZE)) 
	    return srDMEM_ERR;
	break;

    case opclRA:
        /***********************************/
	r = currentinstruction.iarg1;
	s = currentinstruction.iarg3;
	m = currentinstruction.iarg2 + reg[s];
	break;
    }				/* case */

    switch (currentinstruction.iop) {
	/* RR instructions */
    case opHALT:
        /***********************************/
	return srHALT;
	/* break; */

    case opIN:
        /***********************************/
	do {
	    if (promptflag) printf("Enter integer value: ");
	    fflush(stdin);
	    fflush(stdout);

            fgets(in_Line, LINESIZE - 2, stdin);
            { 
                char *p;
	    
                for (p=in_Line; *p; p++) {
                    if (*p=='\n') {
                        *p='\0';
                        break;
                    }
                }
                lineLen = p-in_Line;
            }

	    if (!promptflag) printf("entered: %s\n", in_Line);

	    inCol = 0;
	    ok = getNum();
	    if (!ok) {
		printf("Illegal value in input: \"%s\"\n", in_Line);
                exit(1);
            }
	    else {
		reg[r] = num;
            }
	}
	while (!ok);
	if (skipCh('#')) return srHALT;
	break;

    case opINB:
        /***********************************/
	if (promptflag) printf("Enter Boolean value: ");
	fflush(stdin);
	fflush(stdout);

	fgets(in_Line, LINESIZE - 2, stdin);
	{ 
	    char *p;
	    
	    for (p=in_Line; *p; p++) {
		if (*p=='\n') {
		    *p='\0';
		    break;
		}
	    }
	    lineLen = p-in_Line;
	}

	if (!promptflag) printf("entered: %s\n", in_Line);

	inCol = 0;
	getBool();
	reg[r] = num;
	if (skipCh('#')) return srHALT;
	break;

    case opOUT:
	printf("%d ", reg[r]);
        fflush(stdout);
	break;

    case opOUTB:
	if (reg[r]) printf("T ");
	else printf("F ");
        fflush(stdout);
	break;

    case opOUTC:
	printf("%c", reg[r]);
        fflush(stdout);
	break;

    case opOUTNL:
	printf("\n");
        fflush(stdout);
	break;

    case opADD:
	reg[r] = reg[s] + reg[t];
	break;

    case opSUB:
	reg[r] = reg[s] - reg[t];
	break;

    case opMUL:
	reg[r] = reg[s]*reg[t];
	break;

    case opDIV:
        /***********************************/
	if (reg[t] != 0)
	    reg[r] = reg[s]/reg[t];
	else
	    return srZERODIVIDE;
	break;

        /*************** RM instructions ********************/
    case opLD:
	reg[r] = dMem[m];
	break;
    case opST:
	dMem[m] = reg[r];
	dMemTag[m] = pc;
	break;

        /*************** RA instructions ********************/
    case opLDA:
	reg[r] = m;
	break;
    case opLDC:
	reg[r] = currentinstruction.iarg2;
	break;
    case opJLT:
	if (reg[r]<0)
	    reg[PC_REG] = m;
	break;
    case opJLE:
	if (reg[r] <= 0)
	    reg[PC_REG] = m;
	break;
    case opJGT:
	if (reg[r]>0)
	    reg[PC_REG] = m;
	break;
    case opJGE:
	if (reg[r] >= 0)
	    reg[PC_REG] = m;
	break;
    case opJEQ:
	if (reg[r] == 0)
	    reg[PC_REG] = m;
	break;
    case opJNE:
	if (reg[r] != 0)
	    reg[PC_REG] = m;
	break;

	/* end of legal instructions */
    }				/* case */
    return srOKAY;
}				/* stepTM */




/********************************************/
void usage()
{
    printf("%s\n", versionNumber);
    printf("\nCommands are:\n");
    printf(" a(bortLimit <<n>> Maximum number of instructions between halts (default is %d).\n", DEFAULT_ABORT_LIMIT);
    printf(" b(reakpoint <<n>> Set a breakpoint for instr n.  No n means clear breakpoints.\n");
    printf(" c(lear            Reset simulator for new execution of program\n");
    printf(" d(Mem <b <n>>     Print n dMem locations starting at b (n can be negative to count up)\n");
    printf(" e(xecStats        Print execution statistics since last load or clear\n");
    printf(" g(o               Execute TM instructions until HALT\n");
    printf(" h(elp             Cause this list of commands to be printed\n");
    printf(" i(Mem <b <n>>     Print n iMem locations starting at b\n");
    printf(" l(oad filename    Load filename into memory (default is last file)\n");
    printf(" n(ext             Print the next command that will be executed\n");
    printf(" p(rint            Toggle printing of total instructions executed ('go' only)\n");
    printf(" q(uit             Terminate the simulation\n");
    printf(" r(egs             Print the contents of the registers\n");
    printf(" s(tep <n>         Execute n (default 1) TM instructions\n");
    printf(" t(race            Toggle instruction trace\n");
    printf(" u(nprompt)        Unprompted for script input\n");
    printf(" x(it              Terminate the simulation\n");
    printf(" = <r> <n>         Set register number r to value n (e.g. set the pc)\n");
    printf(" (empty line does a step)\n");
    printf("Also a # character placed after input will cause TM to halt\n  after processing the IN or INB commands (e.g. 34#  or f# )\n");
}



int doCommand(void)
{
    char cmd;
    int i;
    int printcnt;
    int stepResult;
    int regNo, loc;
    int stepcnt; 

    stepcnt = 0;
    do {
	if (promptflag) printf("Enter command: ");
	fflush(stdin);
	fflush(stdout);

	fgets(in_Line, LINESIZE - 2, stdin);
	if (feof(stdin)) {
	    word[0] = 'q';
	    word[1] = '\0';
	    break;
	}

	{ 
	    char *p;
	    
	    for (p=in_Line; *p; p++) {
		if (*p=='\n') {
		    *p='\0';
		    break;
		}
	    }
	    lineLen = p-in_Line;
	}
	inCol = 0;
    }
    while ((lineLen>0) && !getWord());

    if (lineLen==0) {
        word[0] = 's';
        word[1] = '\0';
    }

    if (! promptflag) printf("command: %s\n", in_Line);

    cmd = word[0];
    switch (cmd) {
    case 'l':
        /***********************************/
	if (!getWord()) *word = '\0';
	readInstructions(word);
	break;

    case 't':
        /***********************************/
	traceflag = !traceflag;
	printf("Tracing now ");
	if (traceflag)
	    printf("on.\n");
	else
	    printf("off.\n");
	break;

        /***********************************/
    case 'u':
        printf("\n");
	promptflag = FALSE;
	break;

    case '?':
    case 'h':
        /***********************************/
	usage();
	break;

    case 'p':
        /***********************************/
	icountflag = !icountflag;
	printf("Printing instruction count now ");
	if (icountflag)
	    printf("on.\n");
	else
	    printf("off.\n");
	break;

    case 'a':
        /***********************************/
        if (getNum()) {
	    abortLimit = abs(num);
        }
	else {
	    abortLimit = 0;
	    printf("Abort limit turned off.\n");
        }
	break;

    case 's':
        /***********************************/
	if (atEOL())
	    stepcnt = 1;
	else if (getNum())
	    stepcnt = abs(num);
	else
	    printf("Step count?\n");
	break;

    case 'e':
        /***********************************/
    { int cnt;
            printf("EXEC STAT: Number of instructions executed: %d\n", instrCount);

	    cnt = 0;
	    for (i = 0; i<IADDR_SIZE; i++) if (iMemTag[i]==USED) cnt++;
	    printf("EXEC STAT: Instruction memory used: %d\n", cnt);
	    
	    cnt = 0;
	    for (i = 0; i<IADDR_SIZE; i++) if (dMemTag[i]>=0) cnt++;
	    printf("EXEC STAT: Data memory used: %d\n", cnt);
    }
    break;

    case 'g':
        /***********************************/
	stepcnt = 1;
	break;

    case 'r':
        /***********************************/
	for (i = 0; i<NO_REGS; i++) {
	    printf("r[%1d]: %-4d   ", i, reg[i]);
	    if ((i%4) == 3) printf("\n");
	}
	break;

    case '=':
        /***********************************/
	if (getNum()) {
	    loc = num;
	    if (getNum()) {
		if (loc<0 || loc>=NO_REGS) printf("%d is not a legal register number\n", loc);
		else reg[loc] = num;
	    }
	    else printf("Register value?\n");
	}
        else printf("Register number?\n");
        break;

        /***********************************/
    case 'n':
	iloc = reg[PC_REG];
	if ((iloc >= 0) && (iloc<IADDR_SIZE)) writeInstruction(iloc, TRACE);
	break;

    case 'i':
        /***********************************/
	printcnt = 1;
	if (getNum()) {
	    iloc = num;
	    if (getNum())
		printcnt = num;
	}
	if (!atEOL())
	    printf("Instruction locations?\n");
	else {
	    while ((iloc >= 0) && (iloc<IADDR_SIZE) && (printcnt>0)) {
		writeInstruction(iloc, NOTRACE);
		iloc++;
		printcnt--;
	    }
	}
	break;

    case 'd':
        /***********************************/
    { int down;

            if (getNum()) {
                dmemStart = num;
                if (getNum()) {
                    dmemDown = FALSE;
                    if (num<0) dmemDown = TRUE;
                    dmemCount = abs(num);
                }
            }
            dloc = dmemStart;
            printcnt = dmemCount;
            down = dmemDown;
            printf("%5s: %5s", "addr", "value");
            printf("    %s\n", "instr that last assigned this loc");
            while ((dloc >= 0) && (dloc<DADDR_SIZE) && (printcnt>0)) {
		switch (dMemTag[dloc]) {
		case NOTUSED:
		  printf("%5d: %5d", dloc, dMem[dloc]);
		  printf("    %s\n", "unused");
		  break;
		case DATA:
		  printf("%5d: %5d", dloc, dMem[dloc]);
		  printf("    %s\n", "data");
		  break;
		case SDATA:
		  printf("%5d:   '%c'", dloc, dMem[dloc]);
		  printf("    %s\n", "data");
		  break;
		default:
		  printf("%5d: %5d", dloc, dMem[dloc]);
		  printf("    %d\n", dMemTag[dloc]);
		  break;
		}
                if (down) dloc--;
                else dloc++;
                printcnt--;
            }
    }
    break;

    case 'b':
	if (atEOL()) {
	    savedbreakpoint = breakpoint = -1;
	}
	else if (getNum())
	    savedbreakpoint = breakpoint = abs(num);
	else
	    printf("Breakpoint location?\n");
	break;
	

    case 'c':
        /***********************************/
	clearMachine();
	lastpc = 0;
	stepcnt = 0;
	break;

    case 'q':
    case 'x':
	return FALSE;		/* break; */

    default:
	printf("Command %c unknown.\n", cmd);
	usage();
	break;
    }				/* case */

    stepResult = srOKAY;
    if (stepcnt>0) {
	if (cmd == 'g') {
	    stepcnt = 0;
	    while ((stepResult == srOKAY) && ((abortLimit==0) || (stepcnt<abortLimit))) {
		iloc = reg[PC_REG];
		if (traceflag)
		    writeInstruction(iloc, TRACE);
		stepResult = stepTM();
		stepcnt++;
	    }
	    if ((stepcnt>=abortLimit) && (abortLimit!=0)) {
		stepResult = srHALT;
		printf("Abort limit reached! (limit = %d) (see 'a' command in help).\n", abortLimit);
	    }
	    if (icountflag)
		printf("Number of instructions executed = %d\n", stepcnt);
	}
	else {
	    while ((stepcnt>0) && (stepResult == srOKAY)) {
		iloc = reg[PC_REG];
		if (traceflag)
		    writeInstruction(iloc, TRACE);
		stepResult = stepTM();
		stepcnt--;
	    }
	}
	printf("%s\n", stepResultTab[stepResult]);
	if (stepResult!=srOKAY) {
	    printf("Last executed cmd: ");
	    writeInstruction(lastpc, TRACE);
	}
	printf("PC was %d, PC is now %d\n", lastpc, reg[PC_REG]);
    }
    return TRUE;
}				/* doCommand */



/********************************************/
/* E X E C U T I O N   B E G I N S   H E R E */
/********************************************/

int clusage(char *name) {
  printf("%s -[abl] <tmfile>\n", name);
  printf("\t-a|--abort <limit>\tset abort limit (default 20000)\n");
  printf("\t-b|--batch\t\trun in batch mode\n");
  printf("\t-l|--list\t\tlist instructions and exit\n");
  exit(-1);
}

int main(int argc, char *argv[])
{
  int file=-1;
  int a;
  int batch = 0, list=0;

  for (a = 1; a < argc; a++) {
    if (!strcmp("-a", argv[a]) || !strcmp("--abort", argv[a])) {
      if (++a < argc) {
	abortLimit = atoi(argv[a]);
	if (abortLimit < 0) {
	  printf("abort limit must be positive, was %d\n", abortLimit);
	  exit(-1);
	}
      }
      else
	clusage(argv[0]);
    }
    else if (!strcmp("-b", argv[a]) || !strcmp("--batch", argv[a])) {
      batch = 1;
    }
    else if (!strcmp("-h", argv[a]) || !strcmp("--help", argv[a])) {
      clusage(argv[0]);
    }
    else if (!strcmp("-l", argv[a]) || !strcmp("--list", argv[a])) {
      list = 1;
    }
    else {
      if (file == -1)
	file = a;
      else
	clusage(argv[0]);
    }
  }
  if (list && batch) {
    printf("select one of -l and -b\n");
    usage(argv[0]);
  }
    /* guarantee a full clear even if the file load fails */
    fullClearMachine();

  if (list) {
    int iloc;
    
    readInstructions(argv[file]);
    for (iloc = 0; iloc < IADDR_SIZE-1; iloc++) {
      writeInstruction(iloc, NOTRACE);
      if (iMemTag[iloc] <= 0) break;
    }
  }
  else if (batch) {
    int stepcnt, stepResult;
    readInstructions(argv[file]);
    for (stepcnt=0; stepcnt < abortLimit; stepcnt++) {
      stepResult = stepTM();
      if (stepResult == srHALT)
	break;
      else if (stepResult != srOKAY) {
	printf("Abnormal termination\nLast executed cmd: ");
	writeInstruction(lastpc, TRACE);
      }
    }
    if (stepcnt >= abortLimit) {
      printf("Abort limit reached\nLast executed cmd: ");
      writeInstruction(lastpc, TRACE);
    }
    printf("Number of instructions executed = %d\n", stepcnt);
    
  }
  else {
    printf("%s (enter h for help)...\n\n", versionNumber);

    /* tell the user how much space they have */
    printf("Memory Configuration: Data Addresses: 0-%d  Instruction Addresses: 0-%d\n", DADDR_SIZE-1, IADDR_SIZE-1);
    printf("Abort Limit: %d\n", abortLimit);

    /* read the program if supplied as an argument */
    if (file != -1) readInstructions(argv[file]);

    /* do stuff */
    while (doCommand());

    printf("Bye.\n");
  }
    return 0;
}
