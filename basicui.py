from tokens import Token
from scanner import Scanner
from program import Program
from sys import stderr


def main():
	'''This is the user interface to the BASIC programming environment.  
	Programs may be entered, listed and ran.  They can also be saved to 
	disk or loaded back into memory.
	'''
	print('\nWelcome to RETRO - BASIC\n')
	
	scanner = Scanner()
	program = Program()
	
	# Keep accepting input and take action until 'EXIT' is entered.
	while True:
		stmt = input('> ')
		
		try:
			tokenlist = scanner.tokenise(stmt)
			
			# Execute commands immediately or add statements 
			# to the current BASIC program
			
			if len(tokenlist) > 0:
				
				# Exit the UI
				if tokenlist[0].cat == Token.EXIT:
					break
				
				# Remove the program from memory
				elif tokenlist[0].cat == Token.NEW:
					program.delete()
				
				# Load program
				elif tokenlist[0].cat == Token.LOAD:
					program.load(tokenlist[1].val)
					print('Program loaded')
				
				# Add new statement
				elif tokenlist[0].cat == Token.UNSIGNEDINT and len(tokenlist) > 1:
					program.add_stmt(tokenlist)
				
				# Delete statement
				elif tokenlist[0].cat == Token.UNSIGNEDINT and len(tokenlist) == 1:
					program.del_stmt(int(tokenlist[0].val))
				
				# List program
				elif tokenlist[0].cat == Token.LIST:
					if len(tokenlist) == 2:
						program.list(int(tokenlist[1].val), int(tokenlist[1].val))
					elif len(tokenlist) == 3:
						# if there are 3 tokens
						# it might be LIST x y (for a range)
						# or LIST -y or LIST x- (for start to y or x to end)
						if tokenlist[1].val == '-':
							program.list(None, int(tokenlist[2].val))
						elif tokenlist[2].val == '-':
							program.list(int(tokenlist[1].val), None)
						else:
							program.list(int(tokenlist[1].val), \
									int(tokenlist[2].val))
					elif len(tokenlist) == 4:
						# if there are 4 tokens, assume LIST x-y
						program.list(int(tokenlist[1].val), int(tokenlist[3].val))
					else:
						program.list()
				
				# Renumber program
				elif tokenlist[0].cat == Token.RENUM:
					if len(tokenlist) == 2:
						program.renum(int(tokenlist[1].val), None)
					elif len(tokenlist) == 3:
						# if there are 3 tokens
						# it might be RENUM x y (with start and step values)
						# or RENUM -y or RENUM x- (using default start or step)
						if tokenlist[1].val == '-':
							program.renum(None, int(tokenlist[2].val))
						elif tokenlist[2].val == '-':
							program.renum(int(tokenlist[1].val), None)
						else:
							program.renum(int(tokenlist[1].val), \
									int(tokenlist[2].val))
					elif len(tokenlist) == 4:
						# if there are 4 tokens, assume RENUM x-y
						program.renum(int(tokenlist[1].val), int(tokenlist[3].val))
					else:
						program.renum()
				
				# Save the program
				elif tokenlist[0].cat == Token.SAVE:
					program.save(tokenlist[1].val)
					print('Program saved')
				
				# Run the program
				elif tokenlist[0].cat == Token.RUN:
					try:
						program.run()
					except KeyboardInterrupt:
						print('Program terminated')
				
				# Unknown command
				else:
					print('Unrecognised command', file=stderr)
					for token in tokenlist:
						token.disp_val()
					print(flush=True)
		
		
		# Catch all errors to keep UI running.
		except Exception as e:
			print(e, file=stderr, flush=True)


if __name__ == "__main__":
	main()

