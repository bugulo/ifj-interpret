import re
import sys
import argparse
import os.path
import xml.etree.ElementTree as ElementTree

from enum import Enum

# Custom error function to print message and exit with provided return code
def throw_error(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)

# Check if string in hexadecimal format is float
def is_hexstring_float(string):
    try:
        float.fromhex(string)
        return True
    except:
        return False

# Check if string is int
def is_string_int(string):
    try: 
        int(string)
        return True
    except:
        return False

# Custom type for working with undefined values
class VarState(Enum):
    UNDEFINED = 1

# Type that the interpret is working with
class Type(Enum):
    INT = 1
    STRING = 2
    BOOL = 3
    FLOAT = 4

# Argument type
class ArgumentType(Enum):
    VAR = 1
    SYMB = 2
    LABEL = 3
    TYPE = 4
    FLOAT = 5

# Frame type
class FrameType(Enum):
    LOCAL = 1
    GLOBAL = 2
    TEMPORARY = 3

# List of all available instructions and their coresponding arguments
instruction_table = {
    # Frame and function related instructions
    "MOVE":         [ArgumentType.VAR, ArgumentType.SYMB],
    "CREATEFRAME":  [],
    "PUSHFRAME":    [],
    "POPFRAME":     [],
    "DEFVAR":       [ArgumentType.VAR],
    "CALL":         [ArgumentType.LABEL],
    "RETURN" :      [],
    # Data stack related instructions
    "PUSHS":        [ArgumentType.SYMB],
    "POPS":         [ArgumentType.VAR],
    # Arithmetic, relational, boolean and conversion instructions
    "ADD":          [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "SUB":          [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "MUL":          [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "IDIV":         [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "DIV":          [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "LT":           [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "GT":           [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "EQ":           [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "AND":          [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "OR":           [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "NOT":          [ArgumentType.VAR, ArgumentType.SYMB],
    "INT2CHAR":     [ArgumentType.VAR, ArgumentType.SYMB],
    "STRI2INT":     [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "INT2FLOAT":    [ArgumentType.VAR, ArgumentType.SYMB],
    "FLOAT2INT":    [ArgumentType.VAR, ArgumentType.SYMB],
    # IO related instructions
    "READ":         [ArgumentType.VAR, ArgumentType.TYPE],
    "WRITE":        [ArgumentType.SYMB],
    # String related instructions 
    "CONCAT":       [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "STRLEN":       [ArgumentType.VAR, ArgumentType.SYMB],
    "GETCHAR":      [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    "SETCHAR":      [ArgumentType.VAR, ArgumentType.SYMB, ArgumentType.SYMB],
    # Type related instructions
    "TYPE":         [ArgumentType.VAR, ArgumentType.SYMB],
    # Flow related instructions
    "LABEL":        [ArgumentType.LABEL],
    "JUMP":         [ArgumentType.LABEL],
    "JUMPIFEQ":     [ArgumentType.LABEL, ArgumentType.SYMB, ArgumentType.SYMB],
    "JUMPIFNEQ":    [ArgumentType.LABEL, ArgumentType.SYMB, ArgumentType.SYMB],
    "EXIT":         [ArgumentType.SYMB],
    # Debug instructions
    "DPRINT":       [ArgumentType.SYMB],
    "BREAK":        []
}

# Instruction instance
class Instruction:
    def __init__(self, name: str, order: int):
        self.name = name       # Name of instruction
        self.order = order     # Order of instruction
        self.arguments = []    # Arguments of instruction
        self.calls = 0         # How many times was the instruction called


class Variable: 
    def __init__(self, frame: FrameType, name: str):
        self.frame = frame     # What frame is the variable referring to
        self.name = name       # Identifier of variable

# Parse command line arguments
file_source = None
file_input = None
file_stats = None

# Requested stats
stats = []

for arg in sys.argv[1:]:
    if arg == "--help" and len(sys.argv[1:]) == 1:
        print("--help - List interpret parameters\n")
        print("--source=file - Set source file")
        print("--input=file - Set input file\n")
        print("--stats=file - Target file for stats")
        print("--insts - Save number of called instructions to stats")
        print("--vars - Save maximum number of initialized variables to stats")
        print("--hot - Save order of instruction that was called the most to stats")
        sys.exit(0)
    elif re.match(r"^--source=(\S+)$", arg) and file_source == None:
        file_source = re.match(r"^--source=(\S+)$", arg).groups()[0]
    elif re.match(r"^--input=(\S+)$", arg) and file_input == None:
        file_input = re.match(r"^--input=(\S+)$", arg).groups()[0]
    elif re.match(r"^--stats=(\S+)$", arg) and file_stats == None:
        file_stats = re.match(r"^--stats=(\S+)$", arg).groups()[0]
    elif arg == "--insts":
        stats.append("insts")
    elif arg == "--vars":
        stats.append("vars")
    elif arg == "--hot":
        stats.append("hot")
    else:
        throw_error("Unknown argument or invalid combination of arguments [1]", 10)

# At least one optional argument must be provided
if file_input == None and file_source == None:
    throw_error("Unknown argument or invalid combination of arguments [2]", 10)

if file_stats == None and len(stats) != 0:
    throw_error("Unknown argument or invalid combination of arguments [3]", 10)

# Check if provided file in source argument exists
if file_source and not os.path.isfile(file_source):
    throw_error(f"File '{file_source}' does not exist", 11)

# Check if provided file in input argument exists
if file_input and not os.path.isfile(file_input):
    throw_error(f"File '{file_input}' does not exist", 11)

# Parse input source file and check if it is well-formed
try:
    file_parsed = ElementTree.parse(file_source if file_source else sys.stdin)
except:
    throw_error(f"Input source file is not well-formed", 31)

root = file_parsed.getroot()
if root.tag != "program" or "language" not in root.attrib or root.attrib["language"].lower() != "ippcode21":
    throw_error(f"Input source file has unknown structure [1]", 32)

# Redirect input file to stdin if provided
if file_input:
    sys.stdin = open(file_input, "r")

# List of all parsed instructions
instructions = []

# List of all parsed labels
labels = {}

# Save last parsed order of instruction so we can check there are no instructions with same order
last_order = 0

instruction_elements = sorted(root, key=lambda x: int(x.attrib["order"]) if "order" in x.attrib and x.attrib["order"].isdigit() else 0)
for instruction_i, elem_instruction in enumerate(instruction_elements):
    # Verify that instruction element has correct attributes
    if elem_instruction.tag != "instruction" or "order" not in elem_instruction.attrib or not is_string_int(elem_instruction.attrib["order"]) or "opcode" not in elem_instruction.attrib:
        throw_error(f"Input source file has unknown structure [2]", 32)

    order = int(elem_instruction.attrib["order"])
    opcode = elem_instruction.attrib["opcode"]

    # Order needs to be bigger than 0 and there can't be two instructions with same order
    if order < 1 or order == last_order:
        throw_error(f"Input source file has unknown structure [3]", 32)

    last_order = order

    instruction = Instruction(opcode.upper(), order)

    if instruction.name not in instruction_table:
        throw_error(f"Undefined instruction {instruction.name}", 32)

    arg_elements = sorted(elem_instruction, key=lambda x: x.tag)
    
    if len(arg_elements) != len(instruction_table[instruction.name]):
        throw_error(f"Input source file has unknown structure [4]", 32)

    for arg_i, elem_arg in enumerate(arg_elements):
        # Verify that arg element has correct attributes
        if re.match(r"^arg\d+$", elem_arg.tag) == None or "type" not in elem_arg.attrib or len(list(elem_arg)) != 0:
            throw_error(f"Input source file has unknown structure [5]", 32)

        index = int(elem_arg.tag[3:]) - 1

        # Wrong number of arguments
        if index != arg_i:
            throw_error(f"Input source file has unknown structure [6]", 32)

        arg_type = elem_arg.attrib["type"]
        arg_text = elem_arg.text

        required = instruction_table[instruction.name][index]

        if (required == ArgumentType.VAR or required == ArgumentType.SYMB) and arg_type == "var" and re.match(r"^(?:GF|LF|TF)\@[\w\_\-\$\&\%\*\!\?]+[\w\_\-\$\&\%\*\!\?]*$", arg_text) != None:
            frame, name = arg_text.split("@", 1)

            frame_type = None
            if frame == "GF":
                frame_type = FrameType.GLOBAL
            elif frame == "LF":
                frame_type = FrameType.LOCAL
            elif frame == "TF":
                frame_type = FrameType.TEMPORARY

            instruction.arguments.append(Variable(frame_type, name))
        elif required == ArgumentType.SYMB and arg_type == "string":
            string = arg_text if arg_text != None else ""
            for code in re.findall(r'\\\d\d\d', string):
                string = string.replace(code, chr(int(code[1:])))
            instruction.arguments.append(string)
        elif required == ArgumentType.LABEL and arg_type == "label" and re.match(r"[\w\_\-\$\&\%\*\!\?]+[\w\_\-\$\&\%\*\!\?]*", arg_text) != None:
            instruction.arguments.append(arg_text)
        elif required == ArgumentType.TYPE and arg_type == "type" and re.match(r"^(int|string|bool|float)$", arg_text) != None:
            if arg_text == "int":
                instruction.arguments.append(Type.INT)
            elif arg_text == "string":
                instruction.arguments.append(Type.STRING)
            elif arg_text == "bool":
                instruction.arguments.append(Type.BOOL)
            elif arg_text == "float":
                instruction.arguments.append(Type.FLOAT)
        elif required == ArgumentType.SYMB and arg_type == "bool" and re.match(r"^(true|false)$", arg_text) != None:
            if arg_text == "true":
                instruction.arguments.append(True)
            elif arg_text == "false":
                instruction.arguments.append(False)
        elif required == ArgumentType.SYMB and arg_type == "float" and is_hexstring_float(arg_text):
            instruction.arguments.append(float.fromhex(arg_text))
        elif required == ArgumentType.SYMB and arg_type == "int" and is_string_int(arg_text):
            instruction.arguments.append(int(arg_text))
        elif required == ArgumentType.SYMB and arg_type == "nil" and arg_text == "nil":
            instruction.arguments.append(None)
        else:
            throw_error("Input source file has unknown structure [7]", 32)

    # Labels need to be unique
    if instruction.name == "LABEL":
        if arg_text in labels:
            throw_error(f"Label '{arg_text}' already exists", 52)

        labels[arg_text] = len(instructions)

    instructions.append(instruction)

# Check if jumping instructions refer to existing label
for instruction in instructions:
    if instruction.name == "CALL" or instruction.name == "JUMP" or instruction.name == "JUMPIFEQ" or instruction.name == "JUMPIFNEQ":
        if instruction.arguments[0] not in labels:
            throw_error(f"Undefined label {instruction.arguments[0]}", 52)

# Class representing memory, providing wrapper for manipulation with variables and handling frames
class Memory:
    # Global frame
    frame_global = {}
    # Temporary frame
    frame_temporary = None
    # Stack of local frames
    frame_local = []

    # Create/overwrite temporary frame
    def create_frame(self):
        self.frame_temporary = {}

    # Push temporary frame to stack of local frames
    def push_frame(self):
        if self.frame_temporary == None:
            throw_error("There is no temporary frame to push", 55)

        self.frame_local.append(self.frame_temporary)
        self.frame_temporary = None
    
    # Pop top of local frames stack into temporary frame
    def pop_frame(self):
        if len(self.frame_local) == 0:
            throw_error("There is no local frame to pop", 55)

        self.frame_temporary = self.frame_local.pop()

    # Get coresponding frame of variable
    def get_variable_frame(self, var: Variable, throw=True):
        frame = None
        if var.frame == FrameType.GLOBAL:
            frame = self.frame_global
        elif var.frame == FrameType.LOCAL:
            frame = self.frame_local[-1] if len(self.frame_local) > 0 else None
        elif var.frame == FrameType.TEMPORARY:
            frame = self.frame_temporary

        if frame == None and throw:
            throw_error(f"Trying to access undefined frame: {var.frame}", 55)
        
        return frame

    # Define variable but do not set its value
    def def_variable(self, var: Variable):
        frame = self.get_variable_frame(var)

        if var.name in frame:
            throw_error(f"Trying to redefine variable '{var.name}' that already exists in frame '{var.frame}'", 52)

        frame[var.name] = VarState.UNDEFINED

    # Change value of variable
    def set_variable(self, var: Variable, value):
        frame = self.get_variable_frame(var)

        if var.name not in frame:
            throw_error(f"Trying to access variable '{var.name}' that does not exist in frame '{var.frame}'", 54)

        frame[var.name] = value

    # Get variable instance
    def get_variable(self, var: Variable, throwIfUndefined=True):
        frame = self.get_variable_frame(var)

        if var.name not in frame:
            throw_error(f"Trying to access variable '{var.name}' that does not exist in frame '{var.frame}'", 54)

        if type(frame[var.name]) == type(VarState.UNDEFINED) and throwIfUndefined:
             throw_error(f"Variable '{var.name}' is defined in frame '{var.frame}' but does not have any value", 56)

        return frame[var.name]

    # Get value of variable in memory
    def get_value(self, value, throwIfUndefined=True):
        if type(value) is Variable:
            return self.get_variable(value, throwIfUndefined)
        else:
            return value
        
    # Count all initialized variables in memory
    def var_count(self):
        total = 0
        total = total + sum(type(x) != VarState.UNDEFINED for x in self.frame_global)
        
        if self.frame_temporary != None:
           total = total + sum(type(x) != VarState.UNDEFINED for x in self.frame_temporary)

        for frame in self.frame_local:
            total = total + sum(type(x) != VarState.UNDEFINED for x in frame)

        return total

memory = Memory()

# Semantic analysis of provided arguments
def validate_arguments(instruction: Instruction, types, equals=True, throw=True):
    types_got = []
    for i, type_options in types.items():
        type_actual = type(memory.get_value(instruction.arguments[i]))

        if type_actual in type_options:
            types_got.append(type_actual)
        
    if len(types_got) != len(types):
        if throw:
            throw_error(f"Incorrect operand types in instruction {instruction.name}", 53)
        else:
            return False

    if equals and types_got.count(types_got[0]) != len(types_got):
        if throw:
            throw_error(f"Operand mismatch in instruction {instruction.name}", 53)
        else:
            return False
    
    return True

# Total number of called instructions
total = 0

# Maximum number of initialized variables
max_var = 0

# What instruction is interpret on
index = 0

# Available stacks
call_stack = []
data_stack = []

# Return code that will interpret exit with
return_code = 0
while True:
    if(index >= len(instructions)):
        break

    # Check how many variables are initialized and save if it is largest number so far
    var_ct = memory.var_count()
    if var_ct > max_var:
        max_var = var_ct
    
    instruction = instructions[index]

    # Frame and function related instructions
    if instruction.name == "MOVE":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]))
    elif instruction.name == "CREATEFRAME":
        memory.create_frame()
    elif instruction.name == "PUSHFRAME":
        memory.push_frame()
    elif instruction.name == "POPFRAME":
        memory.pop_frame()
    elif instruction.name == "DEFVAR":
        memory.def_variable(instruction.arguments[0])
    elif instruction.name == "CALL":
        call_stack.append(index)
        index = labels[instruction.arguments[0]]
    elif instruction.name == "RETURN":
        if len(call_stack) == 0:
            throw_error(f"Call stack is empty", 56)

        index = call_stack.pop()
    
    # Data stack related instructions
    elif instruction.name == "PUSHS":
        data_stack.append(memory.get_value(instruction.arguments[0]))
    elif instruction.name == "POPS":
        if len(data_stack) == 0:
            throw_error(f"Data stack is empty", 56)

        memory.set_variable(instruction.arguments[0], data_stack.pop())

    # Arithmetic, relational, boolean and conversion instructions
    elif instruction.name == "ADD":
        validate_arguments(instruction, {1: [int, float], 2: [int, float]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) + memory.get_value(instruction.arguments[2]))
    elif instruction.name == "SUB":
        validate_arguments(instruction, {1: [int, float], 2: [int, float]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) - memory.get_value(instruction.arguments[2]))
    elif instruction.name == "MUL":
        validate_arguments(instruction, {1: [int, float], 2: [int, float]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) * memory.get_value(instruction.arguments[2]))
    elif instruction.name == "IDIV":
        validate_arguments(instruction, {1: [int], 2: [int]})

        if memory.get_value(instruction.arguments[2]) == 0:
            throw_error("Division by zero", 57)

        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) // memory.get_value(instruction.arguments[2]))
    elif instruction.name == "DIV":
        validate_arguments(instruction, {1: [float], 2: [float]})

        if memory.get_value(instruction.arguments[2]) == 0:
            throw_error("Division by zero", 57)

        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) / memory.get_value(instruction.arguments[2]))
    elif instruction.name == "LT":
        validate_arguments(instruction, {1: [int, bool, str, float], 2: [int, bool, str, float]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) < memory.get_value(instruction.arguments[2]))
    elif instruction.name == "GT":
        validate_arguments(instruction, {1: [int, bool, str, float], 2: [int, bool, str, float]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) > memory.get_value(instruction.arguments[2]))
    elif instruction.name == "EQ":
        option1 = validate_arguments(instruction, {1: [int, bool, str, float, type(None)], 2: [int, bool, str, float, type(None)]}, True, False)
        option2 = validate_arguments(instruction, {1: [type(None)], 2: [int, bool, str, float]}, False, False)
        option3 = validate_arguments(instruction, {2: [type(None)], 1: [int, bool, str, float]}, False, False)

        if not option1 and not option2 and not option3:
            throw_error(f"Incorrect operand types in instruction {instruction.name}", 53)

        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) == memory.get_value(instruction.arguments[2]))
    elif instruction.name == "AND":
        validate_arguments(instruction, {1: [bool], 2: [bool]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) and memory.get_value(instruction.arguments[2]))
    elif instruction.name == "OR":
        validate_arguments(instruction, {1: [bool], 2: [bool]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) or memory.get_value(instruction.arguments[2]))
    elif instruction.name == "NOT":
        validate_arguments(instruction, {1: [bool]})
        memory.set_variable(instruction.arguments[0], not memory.get_value(instruction.arguments[1]))
    elif instruction.name == "INT2CHAR":
        validate_arguments(instruction, {1: [int]})

        try:
            result_chr = chr(memory.get_value(instruction.arguments[1]))
        except:
            throw_error("Could not convert int to char", 58)

        memory.set_variable(instruction.arguments[0], result_chr)
    elif instruction.name == "STRI2INT":
        validate_arguments(instruction, {1: [str], 2: [int]}, False)

        string = memory.get_value(instruction.arguments[1])
        position = memory.get_value(instruction.arguments[2])

        if position < 0 or position >= len(string):
            throw_error("Index out bounds in STRI2INT", 58)

        memory.set_variable(instruction.arguments[0], ord(string[position]))
    elif instruction.name == "INT2FLOAT":
        validate_arguments(instruction, {1: [int]})
        memory.set_variable(instruction.arguments[0], float(memory.get_value(instruction.arguments[1])))
    elif instruction.name == "FLOAT2INT":
        validate_arguments(instruction, {1: [float]})
        memory.set_variable(instruction.arguments[0], int(memory.get_value(instruction.arguments[1])))

    # IO related instructions
    elif instruction.name == "READ":
        validate_arguments(instruction, {1: [type(Type.INT), type(Type.BOOL), type(Type.STRING), type(Type.FLOAT)]})

        target_type = instruction.arguments[1]

        try:
            result = input()

            if target_type == Type.INT and is_string_int(result):
                memory.set_variable(instruction.arguments[0], int(result))
            elif target_type == Type.STRING:
                memory.set_variable(instruction.arguments[0], result)
            elif target_type == Type.BOOL: 
                memory.set_variable(instruction.arguments[0], True if result.lower() == "true" else False)
            elif target_type == Type.FLOAT and is_hexstring_float(result):
                memory.set_variable(instruction.arguments[0], float.fromhex(result))
            else:
                memory.set_variable(instruction.arguments[0], None)
        except:
            memory.set_variable(instruction.arguments[0], None)
            
    elif instruction.name == "WRITE":
        value = memory.get_value(instruction.arguments[0])

        if value == None:
            value = ""
        
        if type(value) == bool:
            value = "true" if value else "false"

        if type(value) == float:
            value = float.hex(value)

        print(value, end ="")

    # String related instructions 
    elif instruction.name == "CONCAT":
        validate_arguments(instruction, {1: [str], 2: [str]})
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) + memory.get_value(instruction.arguments[2]))
    elif instruction.name == "STRLEN":
        validate_arguments(instruction, {1: [str]})
        memory.set_variable(instruction.arguments[0], len(memory.get_value(instruction.arguments[1])))
    elif instruction.name == "GETCHAR":
        validate_arguments(instruction, {1: [str], 2: [int]}, False)

        string = memory.get_value(instruction.arguments[1])
        position = memory.get_value(instruction.arguments[2])

        if position < 0 or position >= len(string):
            throw_error("Index out bounds in GETCHAR", 58)

        memory.set_variable(instruction.arguments[0], string[position])
    elif instruction.name == "SETCHAR":
        validate_arguments(instruction, {0: [str], 1: [int], 2: [str]}, False)

        value = memory.get_value(instruction.arguments[0])
        position = memory.get_value(instruction.arguments[1])
        string = memory.get_value(instruction.arguments[2])

        if position < 0 or position >= len(value) or len(string) == 0:
            throw_error("Index out bounds in GETCHAR", 58)

        value = value[:position] + string[0] + value[position + 1:]
        memory.set_variable(instruction.arguments[0], value)

    # Type related instructions
    elif instruction.name == "TYPE":
        result = None 
        
        value = memory.get_value(instruction.arguments[1], False)

        if type(value) == int:
            result = "int"
        elif type(value) == str:
            result = "string"
        elif type(value) == float:
            result = "float"
        elif type(value) == bool:
            result = "bool"
        elif type(value) == type(None):
            result = "nil"
        elif type(value) == type(VarState.UNDEFINED):
            result = ""

        memory.set_variable(instruction.arguments[0], result)

    # Flow related instructions
    elif instruction.name == "LABEL":
        pass
    elif instruction.name == "JUMP":
        index = labels[instruction.arguments[0]]
    elif instruction.name == "JUMPIFEQ":
        option1 = validate_arguments(instruction, {1: [int, bool, str, float, type(None)], 2: [int, bool, str, float, type(None)]}, True, False)
        option2 = validate_arguments(instruction, {1: [type(None)], 2: [int, bool, str, float]}, False, False)
        option3 = validate_arguments(instruction, {2: [type(None)], 1: [int, bool, str, float]}, False, False)

        if not option1 and not option2 and not option3:
            throw_error(f"Incorrect operand types in instruction {instruction.name}", 53)

        if memory.get_value(instruction.arguments[1]) == memory.get_value(instruction.arguments[2]):
            index = labels[instruction.arguments[0]]
    elif instruction.name == "JUMPIFNEQ":
        option1 = validate_arguments(instruction, {1: [int, bool, str, float, type(None)], 2: [int, bool, str, float, type(None)]}, True, False)
        option2 = validate_arguments(instruction, {1: [type(None)], 2: [int, bool, str, float]}, False, False)
        option3 = validate_arguments(instruction, {2: [type(None)], 1: [int, bool, str, float]}, False, False)

        if not option1 and not option2 and not option3:
            throw_error(f"Incorrect operand types in instruction {instruction.name}", 53)

        if memory.get_value(instruction.arguments[1]) != memory.get_value(instruction.arguments[2]):
            index = labels[instruction.arguments[0]]
    elif instruction.name == "EXIT":
        validate_arguments(instruction, {0: [int]})

        return_code = memory.get_value(instruction.arguments[0])

        if return_code < 0 or return_code > 49:
            throw_error(f"Invalid exit code, only range 0-49 is supported", 57)

        index = len(instructions) + 1
    
    # Debug instructions
    elif instruction.name == "DPRINT":
        #print(memory.get_value(instruction.arguments[0]), file=sys.stderr)
        pass
    elif instruction.name == "BREAK":
        pass

    # Increment total instructions called
    if instruction.name != "LABEL" and instruction.name != "DPRINT" and instruction.name != "BREAK":
        instruction.calls = instruction.calls + 1
        total = total + 1

    index = index + 1


# Get the instruction with 
hot_instruction = None
for instruction in instructions:
    if hot_instruction == None or instruction.calls > hot_instruction.calls:
        hot_instruction = instruction

# Create stats file if specified
if file_stats != None:
    try:
        file = open(file_stats,"w")
        file.truncate(0)
    except:
        throw(f"Could not open file '{file_stats}'", 12)

    for stat_name in stats:
        if stat_name == "insts":
            file.write(f"{total}\n")
        elif stat_name == "hot":
            file.write(f"{hot_instruction.order if hot_instruction != None else 0}\n")
        elif stat_name == "vars":
            file.write(f"{max_var}\n")

    file.close()

sys.exit(return_code)