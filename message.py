class Msg:
	'''This class defines an object tahe can be returned by the Parser 
	to indicate change of execution sequence.  The information contained 
	in the object tells the 'program' the type of jump and, therefore, how 
	the return stack should be managed.
	
	>>> msg = Msg(type=FlowSignal.RETURN)
	>>> print(msg.target)
	-1
	
	>>> msg = Msg(target=100, type=FlowSignal.SIMPLE_JUMP)
	>>> print(msg.target)
	100
	>>> print(msg.type)
	0
	'''
	
	# Jump types:
	
	# Simple jump as the result of a GOTO or conditional branch.  
	# The target value should be the jump target, i.e. the line number 
	# being jumped to.
	SIMPLE_JUMP = 0
	
	# Subroutine call where the return address must be the line number of 
	# the instruction following the call.  The target value should be the 
	# line number of the first line of the subroutine.
	GOSUB = 1
	
	# Start of a FOR loop where loop variable has not reached the end value, 
	# and therefore the loop must be repeated.  There should be no associated 
	# target value.
	LOOP_BEGIN = 2
	
	# A message from a NEXT statement that the loop is to be repeated.  
	# Since the return address is already on the stack, a target value is not needed.
	LOOP_REPEAT = 3
	
	# An message from a FOR statement that the loop should be skipped 
	# because the loop variable has reached its final value.  The target 
	# should be the loop variable to look for in the terminating NEXT 
	# statement.
	LOOP_SKIP = 4
	
	# A subroutine RETURN has been processed.  Since the return address is 
	# on the return stack, there is no need for a target value.
	RETURN = 5
	
	# Execution should cease when a STOP statement is processed.  There should 
	# be target value.
	STOP = 6
	
	# Indication that a conditional result block should be executed.
	EXECUTE = 7

	def __init__(self, target=None, type=SIMPLE_JUMP, loop_var=None):
		'''Creates a new Msg for a branch.  If the jump target is supplied, 
		then the branch is assumed to be either a GOTO or conditional branch 
		and the type is assigned as SIMPLE_JUMP.  If no jump_target is 
		supplied, then a jump_type must be supplied (one of GOSUB, RETURN, 
		LOOP_BEGIN, LOOP_REPEAT, LOOP_SKIP or STOP).  In the case of 
		'loops' and 'stop', the target hold the value None.
		'''
		
		if type not in (self.GOSUB, self.SIMPLE_JUMP, self.LOOP_BEGIN, 
				self.LOOP_REPEAT, self.RETURN, self.LOOP_SKIP, self.STOP, 
				self.EXECUTE):
			raise TypeError('Invalid Msg type supplied: ' + str(type))
		
		if target == None and \
				type in [self.SIMPLE_JUMP, self.GOSUB, self.LOOP_SKIP]:
			raise TypeError('Invalid jump target supplied Msg type: ' + str(target))
		
		if target != None and \
				type in [self.RETURN, self.LOOP_BEGIN, self.LOOP_REPEAT, 
				self.STOP, self.EXECUTE]:
			raise TypeError('Wrong target supplied Msg ' + str(ftype))
		
		self.target = target
		self.type = type
		self.loop_var = loop_var

