from tokens import Token
from message import Msg
from math import pi, sqrt, atan, cos, exp, floor, log, sin, tan
from random import random, randint, seed
from time import monotonic


class BASICArray:
    '''Implements a BASIC array, which may a maximum of 
    three dimensions of fixed size.
    '''
    
    def __init__(self, dimensions, elem_type):
        '''Initialises an array object with the given number of dimensions; 
        maximum is three.
        Variable 'dimensions' is a list of dimension sizes.
        Variable 'elem_type' indicates the item type, either 'str' or 'num'.
        '''
        
        self.dims = min(3, len(dimensions))
        if self.dims == 0:
            raise SyntaxError('Zero dimensional array specified')
        
        # Check valid sizes and type (int)
        for i in range(self.dims):
            if dimensions[i] < 0:
                raise SyntaxError('Negative array size specified')
            # Allow sizes like 1.0, but not 1.1
            if dimensions[i] != int(dimensions[i]):
                raise SyntaxError('Fractional array size specified')
            dimensions[i] = int(dimensions[i])
        
        # Initialize to zero or empty string
        # Overdim by one, as some dialects are 1 based and expect to use 
        # the last item at index = size
        if self.dims == 1:
            xd = dimensions[0] + 1
            if elem_type == 'num':
                self.data = [0 for x in range(xd)]
            else:
                self.data = ['' for x in range(xd)]
        elif self.dims == 2:
            xd, yd  = dimensions
            xd += 1; yd += 1
            if elem_type == 'num':
                self.data = [ [0 for y in range(yd)] for x in range(xd) ]
            else:
                self.data = [ ['' for y in range(yd)] for x in range(xd) ]
        else:
            xd, yd, zd = dimensions
            xd += 1; yd += 1; zd += 1
            if elem_type == 'num':
                self.data = [ [ [0 for z in range(zd)] for y in range(yd) ] 
                        for x in range(xd) ]
            else:
                self.data = [ [ ['' for z in range(zd)] for y in range(yd) ] 
                        for x in range(xd) ]
    
    
    def __str__(self):
        return str(self.data)


class Parser:
    '''Implements a BASIC parser that parses a single statement 
    when supplied.
    '''
    
    def __init__(self, basicdata):
        # Symbol table to hold variable names mapped to values
        self.symbol_table = {}
        
        # Stack where operands are stored during expression evaluation
        self.operand_stack = []
        
        # BasicDATA object containing program DATA Statements
        self.data = basicdata
        # List to hold values read from DATA statements
        self.data_values = []
        
        # To be initialised as required for each statement
        self.tokenlist = []
        self.tokenindex = None
        
        # Previous message (msg) (determines initializion of loop variable
        self.last_msg = None
        
        # Keeps track of print position across multiple print statements
        self.prnt_column = 0
        
        # File handle list
        self.file_handles = {}
    
    
    def parse(self, line_num, tokenlist):
        '''Must be initialised with a list of tokens to be processed.  
        These tokens represent a BASIC statement without the line number.
        The line number is passed separately.  This method returns None 
        or a message object to indicate any branching necessary.
        '''
        
        # Remember the line number to aid error reporting
        self.line_num = line_num
        self.tokenlist = []
        self.tokenindex = 0
        linetokenindex = 0
        for token in tokenlist:
            # IF statements will always be the last statement processed on 
            # a line so any colons found after an IF are part of the 
            # conditionally executed statements and will be processed in 
            # the recursive call to parse.
            if token.cat == token.IF:
                # Process IF statement to move tokenidex to the code block
                # of the THEN or ELSE and then call PARSE recursively to 
                # process that code block.
                # This will terminate the token loop by RETURNing to 
                # the calling module.
                #
                # **Warning** if an IF stmt is used in the THEN code block 
                # or multiple IF statement are used in a THEN or ELSE block, 
                # the block grouping is ambiguous and logical processing 
                # may not function as expected.  There is no ambiguity when 
                # single IF statements are placed within ELSE blocks.
                linetokenindex += self.tokenindex
                self.tokenindex = 0
                self.tokenlist = tokenlist[linetokenindex:]
                
                # Assign the first token
                self.token = self.tokenlist[0]
                flow = self.stmt()  # process IF statement
                if flow and (flow.type == Msg.EXECUTE):
                    # Recursive call to process THEN / ELSE block
                    try:
                        return self.parse(line_num, tokenlist[linetokenindex + \
                                self.tokenindex:])
                    except RuntimeError as err:
                        raise RuntimeError(str(err) + ' in line ' + \
                                str(self.line_num))
                else:
                    # Branch on original syntax 'IF cond THEN lineno [ELSE lineno]'
                    # In this syntax the then or else code block is not 
                    # a legal basic statement so recursive processing can't 
                    # be used
                    return flow
            elif token.cat == token.COLON:
                # Found a COLON, process tokens found to this point
                linetokenindex += self.tokenindex
                self.tokenindex = 0
                
                # Assign the first token
                self.token = self.tokenlist[self.tokenindex]
                
                flow = self.stmt()
                if flow:
                    return flow
                
                linetokenindex += 1
                self.tokenlist = []
            elif token.cat == token.ELSE and self.tokenlist[0].cat != token.OPEN:
                # If we find an ELSE and we are not processing an OPEN 
                # statement, we must be in a recursive call and processing 
                # a THEN block.  Since we're processing the THEN block we are 
                # done if we hit an ELSE.
                break
            else:
                self.tokenlist.append(token)
        
        # Reached end of statement, process tokens collected since last COLON 
        # (or from start if no COLONs)
        linetokenindex += self.tokenindex
        self.tokenindex = 0
        # Assign the first token
        self.token = self.tokenlist[self.tokenindex]
        
        return self.stmt()
    
    
    def advance(self):
        '''Advances to the next token.'''
        
        # Move to the next token
        self.tokenindex += 1
        # Get the next token if any left
        if not self.tokenindex >= len(self.tokenlist):
            self.token = self.tokenlist[self.tokenindex]
    
    
    def consume(self, expected_cat):
        '''Consumes a token from the list.'''
        
        if self.token.cat == expected_cat:
            self.advance()
        else:
            raise RuntimeError('Expecting ' + Token.catnames[expected_cat] + \
                    ' in line ' + str(self.line_num))
    
    
    def stmt(self):
        '''Parses a program statement.
        Returns None or a "message" to tell the program how to branch.
        '''
        
        if self.token.cat in (Token.FOR, Token.IF, Token.NEXT, Token.ON):
            return self.compoundstmt()
        else:
            return self.simplestmt()
    
    
    def compoundstmt(self):
        '''Parses compound statements, i.e. for loops, if and on statements.'''
        
        if self.token.cat == Token.FOR:
            return self.forstmt()
        if self.token.cat == Token.NEXT:
            return self.nextstmt()
        if self.token.cat == Token.IF:
            return self.ifstmt()
        elif self.token.cat == Token.ON:
            return self.ongosubstmt()
    
    
    def simplestmt(self):
        '''Parses simple statements, i.e. non-compound statements.'''
        
        if self.token.cat == Token.NAME:
            self.assignmentstmt()
            return None
        if self.token.cat == Token.PRINT:
            self.printstmt()
            return None
        if self.token.cat == Token.LET:
            self.letstmt()
            return None
        if self.token.cat == Token.GOTO:
            return self.gotostmt()
        if self.token.cat == Token.GOSUB:
            return self.gosubstmt()
        if self.token.cat == Token.RETURN:
            return self.returnstmt()
        if self.token.cat == Token.STOP:
            return self.stopstmt()
        if self.token.cat == Token.INPUT:
            self.inputstmt()
            return None
        if self.token.cat == Token.DIM:
            self.dimstmt()
            return None
        if self.token.cat == Token.RANDOMIZE:
            self.randomizestmt()
            return None
        if self.token.cat == Token.DATA:
            self.datastmt()
            return None
        if self.token.cat == Token.READ:
            self.readstmt()
            return None
        if self.token.cat == Token.RESTORE:
            self.restorestmt()
            return None
        if self.token.cat == Token.OPEN:
            return self.openstmt()
        if self.token.cat == Token.CLOSE:
            self.closestmt()
            return None
        if self.token.cat == Token.FSEEK:
            self.fseekstmt()
            return None
        # Ignore comments, but raise an error for anything else
        if self.token.cat != Token.REM:
            raise RuntimeError('Expecting program statement in line ' + \
                    str(self.line_num))
    
    
    def printstmt(self):
        '''Parses a PRINT statement.  
        The value at the top of the operand stack is printed to the screen.
        '''
        
        self.advance()   # Advance past PRINT
        
        fileIO = False
        if self.token.cat == Token.HASH:
            fileIO = True
            
            # Process the # keyword
            self.consume(Token.HASH)
            
            # Get the file number
            self.expr()
            filenum = self.operand_stack.pop()
            
            if self.file_handles.get(filenum) == None:
                raise RuntimeError('PRINT: file #' + str(filenum) + \
                        ' not open in line ' + str(self.line_num))
            
            # Process the comma
            if self.tokenindex < len(self.tokenlist) and \
                    self.token.cat != Token.COLON:
                self.consume(Token.COMMA)
        
        # Check there are items to print
        if not self.tokenindex >= len(self.tokenlist):
            prntTab = (self.token.cat == Token.TAB)
            self.logexpr()
            
            if prntTab:
                if self.prnt_column >= len(self.operand_stack[-1]):
                    if fileIO:
                        self.file_handles[filenum].write('\n')
                    else:
                        print()
                    self.prnt_column = 0
                
                current_pr_column = len(self.operand_stack[-1]) - self.prnt_column
                self.prnt_column = len(self.operand_stack.pop()) - 1
                if current_pr_column > 1:
                    if fileIO:
                        self.file_handles[filenum].write(' ' * (current_pr_column-1))
                    else:
                        print(' ' * (current_pr_column-1), end='')
            else:
                self.prnt_column += len(str(self.operand_stack[-1]))
                if fileIO:
                    self.file_handles[filenum].write(str(self.operand_stack.pop()))
                else:
                    print(self.operand_stack.pop(), end='')
            
            while self.token.cat == Token.SEMICOLON:
                if self.tokenindex == len(self.tokenlist) - 1:
                    # If semicolon at end of line, don't print a newline
                    self.advance()
                    return
                self.advance()
                prntTab = (self.token.cat == Token.TAB)
                self.logexpr()
                
                if prntTab:
                    if self.prnt_column >= len(self.operand_stack[-1]):
                        if fileIO:
                            self.file_handles[filenum].write('\n')
                        else:
                            print()
                        self.prnt_column = 0
                    current_pr_column = len(self.operand_stack[-1]) - self.prnt_column
                    if fileIO:
                        self.file_handles[filenum].write(' ' * (current_pr_column-1))
                    else:
                        print(' ' * (current_pr_column-1), end='')
                    self.prnt_column = len(self.operand_stack.pop()) - 1
                else:
                    self.prnt_column += len(str(self.operand_stack[-1]))
                    if fileIO:
                        self.file_handles[filenum].write(str(self.operand_stack.pop()))
                    else:
                        print(self.operand_stack.pop(), end='')
        
        # Final newline
        if fileIO:
            self.file_handles[filenum].write('\n')
        else:
            print()
        self.prnt_column = 0
    
    
    def letstmt(self):
        '''Parses LET statement, i.e. consumes the LET token.'''
        
        self.advance()  # Advance past LET
        self.assignmentstmt()
    
    
    def gotostmt(self):
        '''Parses GOTO statement.  
        Returns a "message" containing the target line number.
        '''
        
        self.advance()  # Advance past GOTO
        self.expr()
        
        # Set up and return message
        return Msg(target=self.operand_stack.pop())
    
    
    def gosubstmt(self):
        '''Parses a GOSUB statement.  
        Returns a "message" containing the start of the subroutine.
        '''
        
        self.advance()  # Advance past GOSUB
        self.expr()
        
        # Set up and return message
        return Msg(target=self.operand_stack.pop(), type=Msg.GOSUB)
    
    
    def returnstmt(self):
        '''Parses a RETURN statement.'''
        
        self.advance()  # Advance past RETURN
        
        # Set up and return message
        return Msg(type=Msg.RETURN)
    
    
    def stopstmt(self):
        '''Parses a STOP statement.'''
        
        self.advance()  # Advance past STOP
        
        for handle in self.file_handles:
            self.file_handles[handle].close()
        self.file_handles.clear()
        
        return Msg(type=Msg.STOP)
    
    
    def assignmentstmt(self):
        '''Parses an assignment statement.  
        Makes an entry in the symbol table.
        '''
        
        left = self.token.val  # Save val of the current token
        self.advance()
        
        if self.token.cat == Token.LEFTPAREN:
            self.arrayassignmentstmt(left)  # Assigning to an array
        
        else:  # Assigning to a simple variable
            self.consume(Token.ASSIGNOP)
            self.logexpr()
            
            # Check that we are using the correct variable name format
            right = self.operand_stack.pop()
            
            if left.endswith('$') and not isinstance(right, str):
                raise SyntaxError('Syntax error: Attempt to assign non-string ' \
                        + 'to string variable in line ' + str(self.line_num))
            
            elif not left.endswith('$') and isinstance(right, str):
                raise SyntaxError('Syntax error: Attempt to assign string to ' \
                        + 'numeric variable in line ' + str(self.line_num))
            
            self.symbol_table[left] = right
    
    
    def arrayassignmentstmt(self, name):
        '''Parses assignment to array variable.'''
        
        self.consume(Token.LEFTPAREN)
        
        # Get index variables and extract dimensions
        indexvars = []
        
        if not self.tokenindex >= len(self.tokenlist):
            self.expr()
            indexvars.append(self.operand_stack.pop())
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                indexvars.append(self.operand_stack.pop())
        
        try:
            BASICarray = self.symbol_table[name + '_array']
        
        except KeyError:
            raise KeyError('Array could not be found in line ' + \
                    str(self.line_num))
        
        if BASICarray.dims != len(indexvars):
            raise IndexError('Incorrect number of indices applied to array ' + \
                    'in line ' + str(self.line_num))
        
        self.consume(Token.RIGHTPAREN)
        self.consume(Token.ASSIGNOP)
        
        self.logexpr()
        
        # Check that we are using the correct variable name format
        right = self.operand_stack.pop()
        
        if name.endswith('$') and not isinstance(right, str):
            raise SyntaxError('Attempt to assign non-string to string array' + \
                    ' in line ' + str(self.line_num))
        
        elif not name.endswith('$') and isinstance(right, str):
            raise SyntaxError('Attempt to assign string to numeric array' + \
                    ' in line ' + str(self.line_num))
        
        # Assign to the specified array index
        try:
            if len(indexvars) == 1:
                BASICarray.data[indexvars[0]] = right
            
            elif len(indexvars) == 2:
                BASICarray.data[indexvars[0]][indexvars[1]] = right
            
            elif len(indexvars) == 3:
                BASICarray.data[indexvars[0]][indexvars[1]][indexvars[2]] = right
        
        except IndexError:
            raise IndexError('Array index out of range in line ' + \
                    str(self.line_num))
    
    
    def dimstmt(self):
        '''Parses DIM statement and creates a symbol table entry with 
        appropriate dimensions.
        '''
        
        self.advance()  # Advance past DIM keyword
        
        # Allow dims of multiple arrays delimited by commas
        while True:
            # Get array name, append a suffix so we can distinguish 
            # from simple variables
            name = self.token.val + '_array'
            self.advance()  # Advance past array name
            
            self.consume(Token.LEFTPAREN)
            
            # Get dimensions
            dimensions = []
            if not self.tokenindex >= len(self.tokenlist):
                self.expr()
                dimensions.append(self.operand_stack.pop())
                
                while self.token.cat == Token.COMMA:
                    self.advance()  # Advance past comma
                    self.expr()
                    dimensions.append(self.operand_stack.pop())
            
            self.consume(Token.RIGHTPAREN)
            
            if len(dimensions) > 3:
                raise SyntaxError('Maximum number of array dimensions is ' + \
                'three in line ' + str(self.line_num))
            
            # Ensure array is initialised with correct values
            if name.endswith('$_array'):
                self.symbol_table[name] = BASICArray(dimensions, 'str')
            else:
                self.symbol_table[name] = BASICArray(dimensions, 'num')
            
            if self.tokenindex == len(self.tokenlist):  # All tokens parsed
                return
            else:
                self.consume(Token.COMMA)
    
    
    def openstmt(self):
        '''Parses an open statement.  
        Opens the given file and paces the file handle in the handle table.
        '''
        
        self.advance()  # Advance past OPEN
        
        # Get file name
        self.logexpr()
        filename = self.operand_stack.pop()
        
        # Process the FOR keyword
        self.consume(Token.FOR)
        
        if self.token.cat == Token.INPUT:
            accessMode = 'r'
        elif self.token.cat == Token.APPEND:
            accessMode = 'a'
        elif self.token.cat == Token.OUTPUT:
            accessMode = 'w'
        else:
            raise SyntaxError('Invalid Open access mode in line ' + \
                    str(self.line_num))
        
        self.advance()  # Advance past access type
        
        if self.token.val != "AS":
            raise SyntaxError('Expecting AS in line ' + str(self.line_num))
        
        self.advance()  # Advance past AS keyword
        
        # Process the # keyword
        self.consume(Token.HASH)
        
        # Acquire the file number
        self.expr()
        filenum = self.operand_stack.pop()
        
        branchOnError = False
        if self.token.cat == Token.ELSE:
            branchOnError = True
            self.advance()  # Advance past ELSE
            
            if self.token.cat == Token.GOTO:
                self.advance()  # Advance past optional GOTO
            
            self.expr()
        
        if self.file_handles.get(filenum) != None:
            if branchOnError:
                return Msg(target=self.operand_stack.pop())
            else:
                raise RuntimeError('File #', filenum, ' already opened in line ' + \
                        str(self.line_num))
        
        try:
            self.file_handles[filenum] = open(filename, accessMode)
        
        except:
            if branchOnError:
                return Msg(target=self.operand_stack.pop())
            else:
                raise RuntimeError('File ' + filename + ' could not be ' + \
                        'opened in line ' + str(self.line_num))
        
        if accessMode == 'a':
            self.file_handles[filenum].seek(0)
            filelen = 0
            for lines in self.file_handles[filenum]:
                filelen += len(lines)+1
            
            self.file_handles[filenum].seek(filelen)
        
        return None
    
    
    def closestmt(self):
        '''Parses a close.  
        Closes the file and removes file handle from handle table.
        '''
        
        self.advance() # Advance past CLOSE
        
        # Process the # keyword
        self.consume(Token.HASH)
        
        # Get the file number
        self.expr()
        filenum = self.operand_stack.pop()
        
        if self.file_handles.get(filenum) == None:
            raise RuntimeError('CLOSE: file #' + str(filenum) + ' is not open ' + \
                    'in line ' + str(self.line_num))
        
        self.file_handles[filenum].close()
        self.file_handles.pop(filenum)
    
    
    def fseekstmt(self):
        '''Parses fseek statement.  Seeks the given file position.'''
        
        self.advance()  # Advance past FSEEK
        
        # Process the # keyword
        self.consume(Token.HASH)
        
        # Get the file number
        self.expr()
        filenum = self.operand_stack.pop()
        
        if self.file_handles.get(filenum) == None:
            raise RuntimeError('FSEEK: file #' + str(filenum) + ' is not open ' + \
                    'in line ' + str(self.line_num))
        
        # Process the comma
        self.consume(Token.COMMA)
        
        # Get the file position
        self.expr()
        
        self.file_handles[filenum].seek(self.operand_stack.pop())
    
    
    def inputstmt(self):
        '''Parses input statement.
        Gets input from the user and put thr values in the symbol table.
        '''
        
        self.advance()  # Advance past INPUT
        
        fileIO = False
        if self.token.cat == Token.HASH:
            fileIO = True
            
            # Process the # keyword
            self.consume(Token.HASH)
            
            # Get the file number
            self.expr()
            filenum = self.operand_stack.pop()
            
            if self.file_handles.get(filenum) == None:
                raise RuntimeError('INPUT: file #' + str(filenum) + \
                        ' is not open in line ' + str(self.line_num))
            
            # Process the comma
            self.consume(Token.COMMA)
        
        prompt = '? '
        if self.token.cat == Token.STRING:
            if fileIO:
                raise SyntaxError('Input prompt specified for file I/O ' + \
                        'in line ' + str(self.line_num))
            
            # Get the input prompt
            self.logexpr()
            prompt = self.operand_stack.pop()
            self.consume(Token.SEMICOLON)
        
        # Get the comma separated input variables
        variables = []
        if not self.tokenindex >= len(self.tokenlist):
            if self.token.cat != Token.NAME:
                raise ValueError('Expecting NAME in INPUT statement ' + \
                        'in line ' + str(self.line_num))
            variables.append(self.token.val)
            self.advance()  # Advance past variable
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                variables.append(self.token.val)
                self.advance()  # Advance past variable
        
        valid_input = False
        while not valid_input:
            # Get input from the user and put into variables
            if fileIO:
                inputvals = ((self.file_handles[filenum].readline()\
                        .replace('\n','')).replace('\r',''))\
                        .split(',', (len(variables)-1))
                valid_input = True
            else:
                inputvals = input(prompt).split(',', (len(variables)-1))
            
            for variable in variables:
                left = variable
                
                try:
                    right = inputvals.pop(0)
                    
                    if left.endswith('$'):
                        self.symbol_table[left] = str(right)
                        valid_input = True
                    
                    elif not left.endswith('$'):
                        try:
                            if '.' in right:
                                self.symbol_table[left] = float(right)
                            
                            else:
                                self.symbol_table[left] = int(right)
                            
                            valid_input = True
                        
                        except ValueError:
                            if not fileIO:
                                valid_input = False
                            print('Non-numeric input provided to a numeric ' + \
                                    'variable - redo from start')
                            break
                
                except IndexError:
                    # No more input to process
                    if not fileIO:
                        valid_input = False
                    print('Not enough values input - redo from start')
                    break
    
    
    def restorestmt(self):
        '''Parses RESTORE statement.'''
        
        self.advance() # Advance past RESTORE
        
        # Get the line number
        self.expr()
        
        self.data_values.clear()
        self.data.restore(self.operand_stack.pop())
    
    
    def datastmt(self):
        '''Parses a DATA statement.'''
        pass
    
    
    def readstmt(self):
        '''Parses READ statement.'''
        
        self.advance()  # Advance past READ
        
        # Get the comma separated input variables
        variables = []
        if not self.tokenindex >= len(self.tokenlist):
            variables.append(self.token.val)
            self.advance()  # Advance past variable
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                variables.append(self.token.val)
                self.advance()  # Advance past variable
        
        # Get input from the DATA statement and put into variables
        for variable in variables:
            
            if len(self.data_values) < 1:
                self.data_values = self.data.readData(self.line_num)
            
            left = variable
            right = self.data_values.pop(0)
            
            if left.endswith('$'):
                # Python puts quotes around input data
                if isinstance(right, int):
                    raise ValueError('Non-string input provided to a string ' + \
                            'variable in line ' + str(self.line_num))
                
                else:
                    self.symbol_table[left] = right
            
            elif not left.endswith('$'):
                try:
                    numeric = float(right)
                    if int(numeric) == numeric:
                        numeric = int(numeric)
                    self.symbol_table[left] = numeric
                
                except ValueError:
                    raise ValueError('Non-numeric input provided to a ' + \
                            'numeric variable in line ' + str(self.line_num))
    
    
    def ifstmt(self):
        '''Parses if-then-else statements.
        Returns a "message" telling the program how to branch, if required, 
        or None.
        '''
        
        self.advance()  # Advance past IF
        self.logexpr()
        
        # Save result of expression
        saveval = self.operand_stack.pop()
        
        # Process the THEN part and save the jump value
        self.consume(Token.THEN)
        
        if self.token.cat != Token.UNSIGNEDINT:
            if saveval:
                return Msg(type=Msg.EXECUTE)
        else:
            self.expr()
            
            # Jump if the expression evaluated to True
            if saveval:
                # Set up and return the message
                return Msg(target=self.operand_stack.pop())
        
        # Advance to ELSE
        while self.tokenindex < len(self.tokenlist) and self.token.cat != Token.ELSE:
            self.advance()
        
        # Check if there is an ELSE part
        if self.token.cat == Token.ELSE:
            self.advance()
            
            if self.token.cat != Token.UNSIGNEDINT:
                return Msg(type=Msg.EXECUTE)
            else:
                
                self.expr()
                
                # Set up and return message
                return Msg(target=self.operand_stack.pop())
        
        else:
            # No ELSE action
            return None
    
    
    def forstmt(self):
        '''Parses for loops.
        Returns a "message" showing that a loop has been started.
        '''
        
        # Set up default loop increment value
        step = 1
        
        self.advance()  # Advance past FOR
        
        # Process the loop variable initialisation
        loop_variable = self.token.val  # Save val of current token
        
        if loop_variable.endswith('$'):
            raise SyntaxError('Syntax error: Loop variable is not numeric' + \
                    ' in line ' + str(self.line_num))
        
        self.advance()  # Advance past loop variable
        self.consume(Token.ASSIGNOP)
        self.expr()
        
        # Check using correct variable name format for numeric variables
        start_val = self.operand_stack.pop()
        
        # Advance past the TO
        self.consume(Token.TO)
        
        # Process the end value
        self.expr()
        end_val = self.operand_stack.pop()
        
        # Check if there is STEP value
        increment = True
        if not self.tokenindex >= len(self.tokenlist):
            self.consume(Token.STEP)
            
            # Get the step value
            self.expr()
            step = self.operand_stack.pop()
            
            # Check whether incrementing or decrementing
            if step == 0:
                raise IndexError('Zero step value supplied for loop' + \
                        ' in line ' + str(self.line_num))
            
            elif step < 0:
                increment = False
        
        # Now determine the status of the loop
        
        # Note: Cannot use the presence of the loop variable in symbol table for 
        # this test, as the same variable may already have been used somewhere 
        # else in the program.
        
        # Need to initialise the loop variable anytime the FOR statement is 
        # reached from a statement other than an active NEXT.
        
        from_next = False
        if self.last_msg:
            if self.last_msg.type == Msg.LOOP_REPEAT:
                from_next = True
        
        if not from_next:
            self.symbol_table[loop_variable] = start_val
        
        else:
            # Change loop variable according to the STEP value
            self.symbol_table[loop_variable] += step
        
        # If the loop variable has reached the end value, remove it from 
        # the set of current loop variables to signal that this is last 
        # iteration.
        stop = False
        if increment and self.symbol_table[loop_variable] > end_val:
            stop = True
        
        elif not increment and self.symbol_table[loop_variable] < end_val:
            stop = True
        
        if stop:
            # Terminate loop
            return Msg(type=Msg.LOOP_SKIP, target=loop_variable)
        else:
            # Set up and return message
            return Msg(type=Msg.LOOP_BEGIN, loop_var=loop_variable)
    
    
    def nextstmt(self):
        '''Parses a NEXT statement.
        Return a "message" indicating that loop has be processed.
        '''
        
        self.advance()  # Advance past NEXT
        
        # Perform loop variable initialisation
        loop_variable = self.token.val  # Save val of current token
        
        if loop_variable.endswith('$'):
            raise SyntaxError('Syntax error: Loop variable is not numeric' + \
                    ' in line ' + str(self.line_num))
        
        return Msg(type=Msg.LOOP_REPEAT, loop_var=loop_variable)
    
    
    def randomizestmt(self):
        '''Seeds the random number generator.'''
        
        self.advance()  # Advance past RANDOMIZE
        
        if not self.tokenindex >= len(self.tokenlist):
            self.expr()  # Process the seed
            new_seed = self.operand_stack.pop()
            
            seed(new_seed)
        
        else:
            seed(int(monotonic()))
    
    
    def ongosubstmt(self):
        '''Parses ON-GOSUB statement.
        Returns a "message" giving subroutine line number if condition 
        is true, or None otherwise.
        '''
        
        self.advance()  # Advance past ON
        self.expr()
        
        # Save result of expression
        saveval = self.operand_stack.pop()
        
        if self.token.cat == Token.GOTO:
            self.consume(Token.GOTO)
            branchtype = 1
        else:
            self.consume(Token.GOSUB)
            branchtype = 2
        
        branch_values = []
        # Acquire the comma separated values
        if not self.tokenindex >= len(self.tokenlist):
            self.expr()
            branch_values.append(self.operand_stack.pop())
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                branch_values.append(self.operand_stack.pop())
        
        if saveval < 1 or saveval > len(branch_values) or len(branch_values) == 0:
            return None
        elif branchtype == 1:
            return Msg(target=branch_values[saveval - 1])
        else:
            return Msg(target=branch_values[saveval - 1], type=Msg.GOSUB)
    
    
    def logexpr(self):
        '''Parses a logical expression.'''
        
        self.notexpr()
        
        while self.token.cat in (Token.OR, Token.AND):
            savecat = self.token.cat
            self.advance()
            self.notexpr()
            
            right = self.operand_stack.pop()
            left = self.operand_stack.pop()
            
            if savecat == Token.OR:
                self.operand_stack.append(left or right)  # Push result (T or F)
            
            elif savecat == Token.AND:
                self.operand_stack.append(left and right)  # Push result (T or F)
    
    
    def notexpr(self):
        '''Parses a logical not expression.'''
        
        if self.token.cat == Token.NOT:
            self.advance()
            self.relexpr()
            right = self.operand_stack.pop()
            self.operand_stack.append(not right)
        else:
            self.relexpr()
    
    
    def relexpr(self):
        '''Parses a relational expression.'''
        
        self.expr()
        
        # BASIC uses same operator for both assignment and equality, 
        # so need to check
        if self.token.cat == Token.ASSIGNOP:
            self.token.cat = Token.EQUAL
        
        if self.token.cat in (Token.LESSER, Token.LESSEQUAL, Token.GREATER, \
                    Token.GREATEQUAL, Token.EQUAL, Token.NOTEQUAL):
            savecat = self.token.cat
            self.advance()
            self.expr()
            
            right = self.operand_stack.pop()
            left = self.operand_stack.pop()
            
            if savecat == Token.EQUAL:
                self.operand_stack.append(left == right)  # Push result (T or F)
            
            elif savecat == Token.NOTEQUAL:
                self.operand_stack.append(left != right)  # Push result (T or F)
            
            elif savecat == Token.LESSER:
                self.operand_stack.append(left < right)  # Push result (T or F)
            
            elif savecat == Token.GREATER:
                self.operand_stack.append(left > right)  # Push result (T or F)
            
            elif savecat == Token.LESSEQUAL:
                self.operand_stack.append(left <= right)  # Push result (T or F)
            
            elif savecat == Token.GREATEQUAL:
                self.operand_stack.append(left >= right)  # Push result (T or F)
    
    
    def expr(self):
        '''Parses a numerical expression consisting of two terms being added or 
        subtracted, leaving the result on the operand stack.
        '''
        
        self.term()  # Pushes value of left term onto to stack
        
        while self.token.cat in (Token.PLUS, Token.MINUS):
            savedcat = self.token.cat
            self.advance()
            self.term()  # Pushes value of right term onto stack
            rightoperand = self.operand_stack.pop()
            leftoperand = self.operand_stack.pop()
            
            if savedcat == Token.PLUS:
                self.operand_stack.append(leftoperand + rightoperand)
            
            else:
                self.operand_stack.append(leftoperand - rightoperand)
    
    
    def term(self):
        '''Parses a numerical expression consisting of two factors being 
        multiplied, leaving the result on the operand stack.
        '''
        
        self.sign = 1  # Set sign to keep track of unary minus
        self.factor()  # Leaves value of term on top of stack
        
        while self.token.cat in (Token.TIMES, Token.DIVIDE, Token.MODULO):
            savedcat = self.token.cat
            self.advance()
            self.sign = 1  # Set sign
            self.factor()  # Leaves value of term on top of stack
            rightoperand = self.operand_stack.pop()
            leftoperand = self.operand_stack.pop()
            
            if savedcat == Token.TIMES:
                self.operand_stack.append(leftoperand * rightoperand)
            
            elif savedcat == Token.DIVIDE:
                self.operand_stack.append(leftoperand / rightoperand)
            
            else:
                self.operand_stack.append(leftoperand % rightoperand)
    
    
    def factor(self):
        '''Evaluates a numerical expression and leaves its value on top of 
        the operand stack.
        '''
        
        if self.token.cat == Token.PLUS:
            self.advance()
            self.factor()
        
        elif self.token.cat == Token.MINUS:
            self.sign = -self.sign
            self.advance()
            self.factor()
        
        elif self.token.cat == Token.UNSIGNEDINT:
            self.operand_stack.append(self.sign * int(self.token.val))
            self.advance()
        
        elif self.token.cat == Token.UNSIGNEDFLOAT:
            self.operand_stack.append(self.sign * float(self.token.val))
            self.advance()
        
        elif self.token.cat == Token.STRING:
            self.operand_stack.append(self.token.val)
            self.advance()
        
        elif (self.token.cat == Token.NAME \
                and self.token.cat not in Token.functions):
            # Check if this is a simple or array variable.
            # BASIC allows simple and complex variables to have the same id.
            # Not a good idea, but it can be used in programs, so check 
            # whether if next token is parens.
            if ((self.token.val + "_array") in self.symbol_table \
                    and self.tokenindex < len(self.tokenlist) - 1 \
                    and self.tokenlist[self.tokenindex + 1].cat == \
                    Token.LEFTPAREN):
                # Get the current val
                arrayname = self.token.val + '_array'
                
                # Array must be processed
                # Capture the index variables
                self.advance()  # Advance past the array name
                
                try:
                    self.consume(Token.LEFTPAREN)
                    indexvars = []
                    if not self.tokenindex >= len(self.tokenlist):
                        self.expr()
                        indexvars.append(self.operand_stack.pop())
                        
                        while self.token.cat == Token.COMMA:
                            self.advance()  # Advance past comma
                            self.expr()
                            indexvars.append(self.operand_stack.pop())
                    
                    BASICarray = self.symbol_table[arrayname]
                    arrayval = self.get_array_val(BASICarray, indexvars)
                    
                    if arrayval != None:
                        self.operand_stack.append(self.sign * arrayval)
                    
                    else:
                        raise IndexError('Empty array value returned in line ' \
                                + str(self.line_num))
                except RuntimeError:
                    raise RuntimeError('Array used without index in line ' \
                            + str(self.line_num))
            
            elif self.token.val in self.symbol_table:
                # Simple variable must be processed
                self.operand_stack.append(self.sign * \
                        self.symbol_table[self.token.val])
            
            else:
                raise RuntimeError('Name ' + self.token.val + \
                        ' is not defined' + ' in line ' + str(self.line_num))
            
            self.advance()
        
        elif self.token.cat == Token.LEFTPAREN:
            self.advance()
            
            # Save sign because expr() calls term() which resets sign to 1
            savesign = self.sign
            self.logexpr()  # Value of expr is pushed onto stack
            
            if savesign == -1:
                # Change sign of expression
                self.operand_stack[-1] = -self.operand_stack[-1]
            
            self.consume(Token.RIGHTPAREN)
        
        elif self.token.cat in Token.functions:
            self.operand_stack.append(self.evaluate_function(self.token.cat))
        
        else:
            raise RuntimeError('Expecting factor in numeric expression' + \
                    ' in line ' + str(self.line_num) + self.token.val)
    
    
    def get_array_val(self, BASICarray, indexvars):
        '''Retreives a value from a BASICArray at the location specified by a 
        list of indices, one for each dimension.
        '''
        
        if BASICarray.dims != len(indexvars):
            raise IndexError('Incorrect number of indices applied to array ' + \
                    'in line ' + str(self.line_num))
        
        # Get the value from the array
        try:
            if len(indexvars) == 1:
                arrayval = BASICarray.data[indexvars[0]]
            
            elif len(indexvars) == 2:
                arrayval = BASICarray.data[indexvars[0]][indexvars[1]]
            
            elif len(indexvars) == 3:
                arrayval = BASICarray.data[indexvars[0]][indexvars[1]][indexvars[2]]
        
        except IndexError:
            raise IndexError('Array index out of range in line ' + \
                    str(self.line_num))
        
        return arrayval
    
    
    def evaluate_function(self, cat):
        '''Evaluate a function in a statement and return result.'''
        
        self.advance()  # Advance past function name
        
        # Process arguments according to function
        if cat == Token.RND:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            arg = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            # Old BASIC would return the same value if given 0 (zero) as 
            # argument.  This is not implemented.
            # A negative argument would reseed the generator.
            # Otherwise returns a random value between 0 and 1.
            if arg < 0:
                seed(arg)
            
            return random()
        
        if cat == Token.RNDINT:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            lo = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            hi = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return randint(lo, hi)
            
            except ValueError:
                raise ValueError('Invalid value supplied to RNDINT in line ' + \
                        str(self.line_num))
        
        if cat == Token.PI:
            return pi
        
        if cat == Token.MAX:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            value_list = [self.operand_stack.pop()]
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                value_list.append(self.operand_stack.pop())
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return max(*value_list)
            
            except TypeError:
                raise TypeError('Invalid type supplied to MAX in line ' + \
                        str(self.line_num))
        
        if cat == Token.MIN:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            value_list = [self.operand_stack.pop()]
            
            while self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                value_list.append(self.operand_stack.pop())
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return min(*value_list)
            
            except TypeError:
                raise TypeError('Invalid type supplied to MIN in line ' + \
                        str(self.line_num))
        
        if cat == Token.POW:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            base = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            exponent = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return base ** exponent
            
            except ValueError:
                raise ValueError('Invalid value supplied to POW in line ' + \
                        str(self.line_num))
        
        if cat == Token.TERNARY:
            self.consume(Token.LEFTPAREN)
            
            self.logexpr()
            condition = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            whentrue = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            whenfalse = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            
            return whentrue if condition else whenfalse
        
        if cat == Token.LEFT:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            instring = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            chars = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return instring[:chars]
            
            except TypeError:
                raise TypeError('Invalid type supplied to LEFT$ in line ' + \
                        str(self.line_num))
        
        if cat == Token.RIGHT:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            instring = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            chars = self.operand_stack.pop()
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                return instring[-chars:]
            
            except TypeError:
                raise TypeError('Invalid type supplied to RIGHT$ in line ' + \
                        str(self.line_num))
        
        if cat == Token.MID:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            instring = self.operand_stack.pop()
            
            self.consume(Token.COMMA)
            
            self.expr()
            # Old BASIC dialects were always one-based
            start = self.operand_stack.pop() - 1
            
            if self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                chars = self.operand_stack.pop()
            else:
                chars = None
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                if chars:
                    return instring[start:start+chars]
                else:
                    return instring[start:]
            
            except TypeError:
                raise TypeError('Invalid type supplied to MID$ in line ' + \
                        str(self.line_num))
        
        if cat == Token.INSTR:
            self.consume(Token.LEFTPAREN)
            
            self.expr()
            haystackstring = self.operand_stack.pop()
            if not isinstance(haystackstring, str):
                raise TypeError('Invalid type supplied to INSTR in line ' + \
                        str(self.line_num))
            
            self.consume(Token.COMMA)
            
            self.expr()
            needlestring = self.operand_stack.pop()
            
            start = end = None
            if self.token.cat == Token.COMMA:
                self.advance()  # Advance past comma
                self.expr()
                # Old BASIC dialects were always one-based
                start = self.operand_stack.pop() - 1
                
                if self.token.cat == Token.COMMA:
                    self.advance()  # Advance past comma
                    self.expr()
                    end = self.operand_stack.pop() - 1
            
            self.consume(Token.RIGHTPAREN)
            
            try:
                # Old BASIC dialects are one-based, so the return value needs 
                # to be incremented by one.  ALSO, this moves the -1 not found 
                # value to 0 (this indicated not found in most dialects).
                return haystackstring.find(needlestring, start, end) + 1
            
            except TypeError:
                raise TypeError('Invalid type supplied to INSTR in line ' + \
                        str(self.line_num))
        
        self.consume(Token.LEFTPAREN)
        
        self.expr()
        value = self.operand_stack.pop()
        
        self.consume(Token.RIGHTPAREN)
        
        if cat == Token.SQR:
            try:
                return sqrt(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to SQR in line ' + \
                        str(self.line_num))
        
        if cat == Token.ABS:
            try:
                return abs(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to ABS in line ' + \
                        str(self.line_num))
        
        if cat == Token.ATN:
            try:
                return atan(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to ATN in line ' + \
                        str(self.line_num))
        
        if cat == Token.COS:
            try:
                return cos(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to COS in line ' + \
                        str(self.line_num))
        
        if cat == Token.EXP:
            try:
                return math.exp(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to EXP in line ' + \
                        str(self.line_num))
        
        if cat == Token.INT:
            try:
                return floor(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to INT in line ' + \
                        str(self.line_num))
        
        if cat == Token.ROUND:
            try:
                return round(value)
            
            except TypeError:
                raise TypeError('Invalid type supplied to ROUND in line ' + \
                        str(self.line_num))
        
        if cat == Token.LOG:
            try:
                return log(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to LOG in line ' + \
                        str(self.line_num))
        
        if cat == Token.SIN:
            try:
                return sin(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to SIN in line ' + \
                        str(self.line_num))
        
        if cat == Token.TAN:
            try:
                return tan(value)
            
            except ValueError:
                raise ValueError('Invalid value supplied to TAN in line ' + \
                        str(self.line_num))
        
        if cat == Token.CHR:
            try:
                return chr(value)
            
            except TypeError:
                raise TypeError('Invalid type supplied to CHR$ in line ' + \
                        str(self.line_num))
            
            except ValueError:
                raise ValueError('Invalid value supplied to CHR$ in line ' + \
                        str(self.line_num))
        
        if cat == Token.ASC:
            try:
                return ord(value)
            
            except TypeError:
                raise TypeError('Invalid type supplied to ASC in line ' + \
                        str(self.line_num))
            
            except ValueError:
                raise ValueError('Invalid value supplied to ASC in line ' + \
                        str(self.line_num))
        
        if cat == Token.STR:
            return str(value)
        
        if cat == Token.VAL:
            try:
                numeric = float(value)
                if int(numeric) == numeric:
                    return int(numeric)
                return numeric
            
            # BASIC returns zero for non-numeric argument
            except ValueError:
                return 0
        
        if cat == Token.LEN:
            try:
                return len(value)
            
            except TypeError:
                raise TypeError('Invalid type supplied to LEN in line ' + \
                        str(self.line_num))
        
        if cat == Token.UPPER:
            if not isinstance(value, str):
                raise TypeError('Invalid type supplied to UPPER$ in line ' + \
                        str(self.line_num))
            
            return value.upper()
        
        if cat == Token.LOWER:
            if not isinstance(value, str):
                raise TypeError('Invalid type supplied to LOWER$ in line ' + \
                        str(self.line_num))
            
            return value.lower()
        
        if cat == Token.TAB:
            if isinstance(value, int):
                return ' ' * value
            
            else:
                raise TypeError('Invalid type supplied to TAB in line ' + \
                        str(self.line_num))
        
        raise SyntaxError('Unrecognised function in line ' + \
                str(self.line_num))

