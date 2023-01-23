from tokens import Token
from scanner import Scanner
from message import Msg
from parser import Parser


class BASICData:
    '''Handles DATA statements (for use be READ).'''
    
    def __init__(self):
        self.datastmts = {}  # Dict of DATA statements
        self.next_data = 0   # Data pointer
    
    
    def delete(self):
        self.datastmts.clear()
        self.next_data = 0
    
    
    def delData(self, line_num):
        if self.datastmts.get(line_num) != None:
            del self.datastmts[line_num]
    
    
    def addData(self, line_num, tokenlist):
        '''Adds the given token list to the DATA store.  If a token list 
        with the same line number already exists, it is replaced.
        '''
        
        try:
            self.datastmts[line_num] = tokenlist
        except TypeError as err:
            raise TypeError('Invalid line number: ' + str(err))
    
    
    def getTokens(self,line_num):
        '''Returns the tokens from a DATA statement.'''
        
        return self.datastmts.get(line_num)
    
    
    def readData(self, read_line_num):
        if len(self.datastmts) == 0:
            raise RuntimeError('No DATA statements available to READ in \
                    line ' + str(read_line_num))
        
        data_values = []
        
        line_nums = sorted(self.datastmts.keys())
        
        if self.next_data == 0:
            self.next_data = line_nums[0]
        elif line_nums.index(self.next_data) < len(line_nums) - 1:
            self.next_data = line_nums[line_nums.index(self.next_data) + 1]
        else:
            raise RuntimeError('No DATA statements available to READ in \
                    line ' + str(read_line_num))
        
        tokenlist = self.datastmts[self.next_data]
        
        sign = 1
        for token in tokenlist[1:]:
            if token.cat != Token.COMMA:
                # data_values.append(token.val)
                if token.cat == Token.STRING:
                    data_values.append(token.val)
                elif token.cat == Token.UNSIGNEDINT:
                    data_values.append(sign * int(token.val))
                elif token.cat == Token.UNSIGNEDFLOAT:
                    data_values.append(sign * eval(token.val))
                elif token.cat == Token.MINUS:
                    sign = -1
                # else:
                    # data_values.append(token.val)
            else:
                sign = 1
        
        return data_values
    
    
    def restore(self, restoreLineNo):
        if restoreLineNo == 0 or restoreLineNo in self.datastmts:
            if restoreLineNo == 0:
                self.next_data = restoreLineNo
            
            else:
                line_nums = sorted(self.datastmts.keys())
                
                indexln = line_nums.index(restoreLineNo)
                if indexln == 0:
                    self.next_data = 0
                else:
                    self.next_data = line_nums[indexln - 1]
        
        else:
            raise RuntimeError('Attempt to RESTORE but no DATA statement \
                    at line ' + str(restoreLineNo))


class Program:
    '''Class representing a BASIC program in a dictionary.  
    Keys are line numbers, values are lists of tokens forming a statement.
    '''
    
    def __init__(self):
        self.program = {}        # Dict holding program
        self.next_stmt = 0       # Program counter
        self.return_stack = []   # Stack for subroutine returns
        self.return_loop = {}    # Dict for loop returns
        self.data = BASICData()  # Setup DATA store
    
    
    def delete(self):
        '''Deletes the program by clearing dicts.'''
        self.program.clear()
        self.data.delete()
    
    
    def load(self, file):
        '''Loads a program.'''
        
        # Delete any existing program
        self.delete()
        
        if not file.lower().endswith('.bas'):
            file += '.bas'
        try:
            scanner = Scanner()
            with open(file) as infile:
                for line in infile:
                    line = line.replace('\r', '').replace('\n', '').strip()
                    tokenlist = scanner.tokenise(line)
                    self.add_stmt(tokenlist)
        
        except OSError:
            raise OSError('Could not read file')
    
    
    def add_stmt(self, tokenlist):
        '''Adds a new line to the program.  The first token should be 
        a line number.  If a line with the same number already exists 
        it is replaced.
        '''
        
        if len(tokenlist) > 0:
            try:
                line_num = int(tokenlist[0].val)
                if tokenlist[1].val == "DATA":
                    self.data.addData(line_num, tokenlist[1:])
                    self.program[line_num] = [tokenlist[1],]
                else:
                    self.program[line_num] = tokenlist[1:]
            
            except TypeError as err:
                raise TypeError('Invalid line number: ' + str(err))
    
    
    def del_stmt(self, line_num):
        '''Deletes the specified line if it exists.'''
        
        self.data.delData(line_num)
        try:
            del self.program[line_num]
        except KeyError:
            raise KeyError('Line number does not exist')
    
    
    def list(self, start_line=None, end_line=None):
        '''Lists the program.'''
        
        line_nums = self.line_numbers()
        if not start_line:
            start_line = int(line_nums[0])
        if not end_line:
            end_line = int(line_nums[-1])
        
        for line_num in line_nums:
            if int(line_num) >= start_line and int(line_num) <= end_line:
                print(self.str_stmt(line_num), end='')
    
    
    def renum(self, start_num=None, step=None):
        '''Renumbers the program.'''
        
        line_nums = self.line_numbers()
        if not start_num:
            start_num = 10
        if not step:
            step = 10
        
        # Build correspondence table
        stop_num = start_num + len(line_nums) * step
        match = dict(zip(line_nums, range(start_num, stop_num, step)))
        
        # Renumber program lines
        new_prog = {}
        for old_num, new_num in match.items():
            new_prog[new_num] = self.program[old_num]
        
        # Replace program
        self.program.clear()
        self.program.update(new_prog)
        
        # Change line content
        line_nums = self.line_numbers()
        for line_num in line_nums:
            statement = self.program[line_num]
            if statement[0].cat in (Token.GOTO, Token.GOSUB, Token.RESTORE):
                old = int(statement[1].val)
                new = match[old]
                statement[1].val = str(new)
            
            if statement[0].cat == Token.OPEN:
                if statement[-2].cat == Token.ELSE:
                    replace_line_num(statement[-1], match)
            
            if statement[0].cat == Token.ON:
                pos = find_token(statement[1:], Token.GOTO, Token.GOSUB)
                for token in statement[pos+2:]:
                    if token.cat == Token.UNSIGNEDINT:
                        replace_line_num(token, match)
            
            if statement[0].cat == Token.IF:
                pos1 = find_token(statement[1:], Token.GOTO, Token.GOSUB)
                if pos1 != -1:
                    replace_line_num(statement[pos1+2], match)
                # Repeat in case there is another in an ELSE clause
                pos2 = find_token(statement[pos1+2:], Token.GOTO, Token.GOSUB)
                if pos2 != -1:
                    replace_line_num(statement[pos1+pos2+3], match)
            
            if statement[0].cat == Token.IF:
                if statement[-2].cat in (Token.THEN, Token.ELSE):
                    replace_line_num(statement[-1], match)
            
            if statement[0].cat == Token.IF:
                pos = find_token(statement[1:], Token.THEN)
                if pos + 3 < len(statement):
                    if statement[pos+3].cat == Token.ELSE:
                        replace_line_num(statement[pos+2], match)
    
    
    def line_numbers(self):
        '''Return a sorted list of all line numbers used in the program.'''
        
        return sorted(self.program.keys())
    
    
    def str_stmt(self, line_num):
        line_text = str(line_num) + " "
        
        statement = self.program[line_num]
        if statement[0].cat == Token.DATA:
            statement = self.data.getTokens(line_num)
        for token in statement:
            # Add in quotes for strings
            if token.cat == Token.STRING:
                line_text += '"' + token.val + '" '
            
            else:
                line_text += token.val + ' '
        line_text += '\n'
        return line_text
    
    
    def save(self, file):
        '''Saves the program.'''
        
        if not file.lower().endswith('.bas'):
            file += '.bas'
        try:
            with open(file, 'w') as outfile:
                outfile.write(str(self))
        
        except OSError:
            raise OSError("Could not save to file")
    
    
    def __str__(self):
        program_text = ''
        line_nums = self.line_numbers()
        for line_num in line_nums:
            program_text += self.str_stmt(line_num)
        return program_text
    
    
    def run(self):
        '''Run the program.'''
        
        self.parser = Parser(self.data)
        self.data.restore(0)  # reset data pointer
        line_nums = self.line_numbers()
        
        if len(line_nums) > 0:
            # Index into the ordered list of line numbers for sequential 
            # statement execution.  The index is will be incremented by one, 
            # unless modified by a jump
            index = 0
            self.next_stmt = line_nums[index]

            # Run through the program until the last has line number 
            # has been reached.
            while True:
                
                msg = self.execute(self.next_stmt)
                self.parser.last_msg = msg
                
                if msg:
                    if msg.type == Msg.SIMPLE_JUMP:
                        # GOTO or conditional branch found
                        try:
                            index = line_nums.index(msg.target)
                        
                        except ValueError:
                            raise RuntimeError('Invalid line number supplied \
                                    in  GOTO or conditional branch: ' + \
                                    str(msg.target))
                        
                        self.next_stmt = msg.target
                    
                    elif msg.type == Msg.GOSUB:
                        # Subroutine call found
                        # Push next line number onto stack
                        if index + 1 < len(line_nums):
                            self.return_stack.append(line_nums[index + 1])
                        
                        else:
                            raise RuntimeError('GOSUB at end of program, \
                                    nowhere to return')
                        
                        # Set the index to start of subroutine
                        try:
                            index = line_nums.index(msg.target)
                        
                        except ValueError:
                            raise RuntimeError('Invalid line number supplied \
                                    in subroutine call: ' + str(msg.target))
                        
                        self.next_stmt = msg.target
                    
                    elif msg.type == Msg.RETURN:
                        # RETURN found
                        # Pop return address from stack
                        try:
                            index = line_nums.index(self.return_stack.pop())
                        
                        except ValueError:
                            raise RuntimeError('Invalid subroutine return in \
                                    line ' + str(self.next_stmt))
                        
                        except IndexError:
                            raise RuntimeError('RETURN encountered without \
                                    matching subroutine call in line ' \
                                    + str(self.next_stmt))
                        
                        self.next_stmt = line_nums[index]
                    
                    elif msg.type == Msg.STOP:
                        break
                    
                    elif msg.type == Msg.LOOP_BEGIN:
                        # Loop start found
                        # Put loop line number on stack
                        # so that loop repeat can return to it
                        self.return_loop[msg.loop_var] = line_nums[index]
                        
                        # Continue to the next statement in the loop
                        index += 1
                        
                        if index < len(line_nums):
                            self.next_stmt = line_nums[index]
                        
                        else:
                            # Reached end of program
                            raise RuntimeError('Program terminated within a loop')
                    
                    elif msg.type == Msg.LOOP_SKIP:
                        # Loop variable at final value
                        # so move past matching NEXT statement
                        index += 1
                        while index < len(line_nums):
                            next_line_num = line_nums[index]
                            temp_tokenlist = self.program[next_line_num]
                            
                            if temp_tokenlist[0].cat == Token.NEXT and \
                                    len(temp_tokenlist) > 1:
                                # Check loop variable to ensure we have not 
                                # found NEXT belonging to a nested loop
                                if temp_tokenlist[1].val == msg.target:
                                    # Move the statement after this NEXT, 
                                    # if there is one
                                    index += 1
                                    if index < len(line_nums):
                                        next_line_num = line_nums[index]
                                        # This is statement after NEXT
                                        self.next_stmt = next_line_num
                                        break
                            
                            index += 1
                        
                        # Check whether at end of program
                        if index >= len(line_nums):
                            # Terminate the program
                            break
                    
                    elif msg.type == Msg.LOOP_REPEAT:
                        # Loop repeat found
                        # Pop the loop start address from the stack
                        try:
                            index = line_nums.index(self.return_loop.pop(msg.loop_var))
                        
                        except ValueError:
                            raise RuntimeError('Invalid loop exit in line ' \
                                    + str(self.next_stmt))
                        
                        except KeyError:
                            raise RuntimeError('NEXT encountered without \
                                    matching FOR loop in line ' \
                                    + str(self.next_stmt))
                        
                        self.next_stmt = line_nums[index]
                
                else:
                    index += 1
                    if index < len(line_nums):
                        self.next_stmt = line_nums[index]
                    
                    else:
                        # At end of program
                        break
        
        else:
            raise RuntimeError('No statements to execute')
    
    
    def execute(self, line_num):
        ''' Execute the specified line.'''
        
        if line_num not in self.program:
            raise RuntimeError('Line number ' + line_num + ' does not exist')
        
        statement = self.program[line_num]
        
        try:
            return self.parser.parse(line_num, statement)
        
        except RuntimeError as err:
            raise RuntimeError(str(err))


def replace_line_num(token, corresp):
    '''Helper function for RENUM command.  
    Replaces the value (val) of a token representing a line number given 
    the original token and a correspondence tbale matching old line numbers 
    to new in the form of a dict mappping ints to ints.  
    Returns the changed token.
    '''
    
    old = int(token.val)
    if old not in corresp:
        return token
    new = corresp[old]
    token.val = str(new)
    return token


def find_token(stmt, *cats):
    '''Helper function for RENUM command.  
    Finds the position of the first token in a statement (or part statement) 
    whose category (cat) matches any of those supplied.
    Return the index of the token or -1 if none found that match.
    '''
    
    pos = -1
    for ix in range(len(stmt)):
        if stmt[ix].cat in cats:
            pos = ix
            break
    return pos

