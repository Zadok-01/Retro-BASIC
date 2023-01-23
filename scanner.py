from tokens import Token


class Scanner:
    '''Reads a BASIC statement (or other input) and converts it to 
    a list tokens.
    
    >>> scanner = Scanner()
    >>> tokenlist = scanner.tokenise('100 LET I = 10')
    >>> print(tokenlist[0])
    Pos: 0, Cat: UNSIGNEDINT, Val: 100
    >>> tokenlist = scanner.tokenise('100 IF I <> 10')
    >>> print(tokenlist[3])
    Pos: 9, Cat: NOTEQUAL, Val: <>
    >>> tokenlist = scanner.tokenise('100 LET I = 3.45')
    >>> print(tokenlist[4])
    Pos: 12, Cat: UNSIGNEDFLOAT, Val: 3.45
    >>> tokenlist = scanner.tokenise('100 LET I = "HELLO"')
    >>> print(tokenlist[4])
    Pos: 12, Cat: STRING, Val: HELLO
    '''
    
    
    def __init__(self):
        self.stmt = ''  # Statement string being processed
        self.pos = 0    # Current position index
    
    
    def tokenise(self, stmt):
        '''Returns list of tokens derived from statement.'''
        self.stmt = stmt
        self.pos = 0
        tokenlist = []
        
        # Process end of string
        c = self.get_next_char()
        while c != '':
            
            # Skip whitespace
            while c.isspace():
                c = self.get_next_char()
            
            # Initialise token
            token = Token(self.pos - 1, None, '')
            
            # Process string
            if c == '"':
                token.cat = Token.STRING
                
                #Process charaters until next quotes
                c = self.get_next_char()
                
                # Deal with empty string
                if c == '"':
                    # token.val remains ''
                    c = self.get_next_char()
                
                else:
                    while True:
                        token.val += c  # Append current char
                        c = self.get_next_char()
                        if c == '':
                            raise SyntaxError("Mismatched quotes")
                        if c == '"':
                            c = self.get_next_char()  # Move past end quote
                            break
            
            # Process numbers
            elif c.isdigit():
                token.cat = Token.UNSIGNEDINT
                found_point = False
                
                # Process digits incl decimal point
                while True:
                    token.val += c  # Append current char
                    c = self.get_next_char()
                    
                    # Stop if not digit or another decimal point
                    if not c.isdigit():
                        if c == '.':
                            if not found_point:
                                found_point = True
                                token.cat = Token.UNSIGNEDFLOAT
                            else:
                                break  # Second decimal point
                        else:
                            break
            
            # Process keywords and names
            elif c.isalpha():
                # Process all letters
                while True:
                    token.val += c  # Append the current char
                    c = self.get_next_char()
                    
                    # Stop if not a letter, digit, underscore or dollar symbol
                    if not ((c.isalpha() or c.isdigit()) or c == '_' or c == '$'):
                        break
                
                # Convert keywords and names to upper case
                token.val = token.val.upper()
                
                # Is it a keyword or a variable name?
                if token.val in Token.keywords:
                    token.cat = Token.keywords[token.val]
                else:
                    token.cat = Token.NAME
                
                # Process remarks without checks
                if token.val == "REM":
                    while c!= '':
                        token.val += c
                        c = self.get_next_char()
            
            # Process operators
            elif c in Token.smalltokens:
                save = c
                c = self.get_next_char()
                double = save + c
                
                if double in Token.smalltokens:
                    token.cat = Token.smalltokens[double]
                    token.val = double
                    c = self.get_next_char() # Move past end of token
                
                else:
                    # Single char operators
                    token.cat = Token.smalltokens[save]
                    token.val = save
                    # No need to get next char in this case
            
            # Invalid token
            elif c != '':
                raise SyntaxError('Syntax error')
            
            # Append the new token to the list
            tokenlist.append(token)
        
        return tokenlist
    
    
    def get_next_char(self):
        '''Returns next character in statement.  
        If nothing left, returns an empty string.
        '''
        if self.pos < len(self.stmt):
            next_char = self.stmt[self.pos]
            self.pos += 1
            return next_char
        else:
            return ''


if __name__ == "__main__":
    from doctest import testmod
    testmod()

