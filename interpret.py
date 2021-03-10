import re
import sys
import xml.etree.ElementTree as ElementTree

from enum import Enum

def throw_error(message, code):
    print(message)
    sys.exit(code)

class Type(Enum):
    INT = 1
    STRING = 2
    BOOL = 3
    FLOAT = 4

class ArgumentType(Enum):
    VAR = 1
    SYMB = 2
    LABEL = 3
    TYPE = 4
    FLOAT = 5

class FrameType(Enum):
    LOCAL = 1
    GLOBAL = 2
    TEMPORARY = 3

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

class Instruction:
    def __init__(self, name: str):
        self.name = name
        self.arguments = []


class Variable: 
    def __init__(self, frame: FrameType, name: str):
        self.frame = frame
        self.name = name

labels = {}
instructions = []

for element in ElementTree.parse("output.xml").findall("instruction"):
    instruction = Instruction(element.attrib["opcode"])
    
    for index, children in enumerate(element):
        if instruction.name not in instruction_table:
            throw_error(f"Undefined instruction {instruction.name}", 52)

        required = instruction_table[instruction.name][index]
        provided = children.attrib["type"]

        if (required == ArgumentType.VAR or required == ArgumentType.SYMB) and provided == "var":
            result = re.match(r'^(..)@(.+)$', children.text)

            frame_type = None
            if result[1] == "GF":
                frame_type = FrameType.GLOBAL
            elif result[1] == "LF":
                frame_type = FrameType.LOCAL
            elif result[1] == "TF":
                frame_type = FrameType.TEMPORARY

            instruction.arguments.append(Variable(frame_type, result[2]))
        elif required == ArgumentType.SYMB and provided == "bool":
            if children.text == "true":
                instruction.arguments.append(True)
            elif children.text == "false":
                instruction.arguments.append(False)
        elif required == ArgumentType.SYMB and provided == "string":
            string = children.text if children.text != None else ""
            for code in re.findall(r'\\\d\d\d', string):
                string = string.replace(code, chr(int(code[1:])))
            instruction.arguments.append(string)
        elif required == ArgumentType.SYMB and provided == "int":
            instruction.arguments.append(int(children.text))
        elif required == ArgumentType.SYMB and provided == "float":
            instruction.arguments.append(float.fromhex(children.text))
        elif required == ArgumentType.SYMB and provided == "nil" and children.text == "nil":
            instruction.arguments.append(None)
        elif required == ArgumentType.LABEL and provided == "label":
            instruction.arguments.append(children.text)
        elif required == ArgumentType.TYPE and provided == "type":
            instruction.arguments.append(children.text)
        else:
            throw_error("Undefined format", 1)

    if instruction.name == "LABEL":
        labels[children.text] = int(element.attrib["order"]) - 1

    instructions.append(instruction)

class Memory:
    frame_global = {}
    frame_temporary = None

    frame_local = []

    def create_frame(self):
        self.frame_temporary = {}

    def push_frame(self):
        self.frame_local.append(self.frame_temporary)
        self.frame_temporary = None

    def pop_frame(self):
        self.frame_temporary = self.frame_local.pop()

    def get_variable_frame(self, var: Variable):
        if var.frame == FrameType.GLOBAL:
            return self.frame_global
        elif var.frame == FrameType.LOCAL:
            return self.frame_local[-1]
        elif var.frame == FrameType.TEMPORARY:
            return self.frame_temporary

    def set_variable(self, var: Variable, value):
        self.get_variable_frame(var)[var.name] = value

    def get_variable(self, var: Variable):
        return self.get_variable_frame(var)[var.name]

    def var_count(self):
        total = 0
        total = total + len(self.frame_global)
        
        if self.frame_temporary != None:
           total = total + len(self.frame_temporary)

        for frame in self.frame_local:
            total = total + len(frame)

        return total


    def get_value(self, value):
        if type(value) is Variable:
            return self.get_variable(value)
        else:
            return value

memory = Memory()

index = 0
call_stack = []
data_stack = []

def validate_arguments(instruction: Instruction, types, equals=False):
    for index, argument in enumerate(instruction.arguments):
        if index in types:
            if type(memory.get_value(argument)) != types[index]:
                throw_error(f"Incorrect operand types in instruction {instruction.name}", 57)

total = 0
max_var = 0

while True:
    if(index >= len(instructions)):
        break

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
        memory.set_variable(instruction.arguments[0], None)
    elif instruction.name == "CALL":
        call_stack.append(index)
        index = labels[instruction.arguments[0]]
    elif instruction.name == "RETURN":
        index = call_stack.pop()
    
    # Data stack related instructions
    elif instruction.name == "PUSHS":
        data_stack.append(memory.get_value(instruction.arguments[0]))
    elif instruction.name == "POPS":
        memory.set_variable(instruction.arguments[0], data_stack.pop())

    # Arithmetic, relational, boolean and conversion instructions
    elif instruction.name == "ADD":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) + memory.get_value(instruction.arguments[2]))
    elif instruction.name == "SUB":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) - memory.get_value(instruction.arguments[2]))
    elif instruction.name == "MUL":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) * memory.get_value(instruction.arguments[2]))
    elif instruction.name == "IDIV":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) / memory.get_value(instruction.arguments[2]))
    elif instruction.name == "LT":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) < memory.get_value(instruction.arguments[2]))
    elif instruction.name == "GT":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) > memory.get_value(instruction.arguments[2]))
    elif instruction.name == "EQ":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) == memory.get_value(instruction.arguments[2]))
    elif instruction.name == "AND":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) and memory.get_value(instruction.arguments[2]))
    elif instruction.name == "OR":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) or memory.get_value(instruction.arguments[2]))
    elif instruction.name == "NOT":
        memory.set_variable(instruction.arguments[0], not memory.get_value(instruction.arguments[1]))
    elif instruction.name == "INT2CHAR":
        memory.set_variable(instruction.arguments[0], chr(memory.get_value(instruction.arguments[1])))
    elif instruction.name == "STRI2INT":
        memory.set_variable(instruction.arguments[0], ord(memory.get_value(instruction.arguments[1])[memory.get_value(instruction.arguments[2])]))

    # IO related instructions
    elif instruction.name == "READ":
        result = input()

        if instruction.arguments[1] == "int":
            memory.set_variable(instruction.arguments[0], int(result))
        elif instruction.arguments[1] == "string":
            memory.set_variable(instruction.arguments[0], result)
        ##elif instruction.arguments[1] == Type.BOOL: 
            ##memory.set_variable(instruction.arguments[0], result)
        elif instruction.arguments[1] == "float":
            memory.set_variable(instruction.arguments[0], float(result))
    elif instruction.name == "WRITE":
        print(memory.get_value(instruction.arguments[0]), end ="")

    # String related instructions 
    elif instruction.name == "CONCAT":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1]) + memory.get_value(instruction.arguments[2]))
    elif instruction.name == "STRLEN":
        memory.set_variable(instruction.arguments[0], len(memory.get_value(instruction.arguments[1])))
    elif instruction.name == "GETCHAR":
        memory.set_variable(instruction.arguments[0], memory.get_value(instruction.arguments[1])[memory.get_value(instruction.arguments[2])])
    elif instruction.name == "SETCHAR":
        value = memory.get_value(instruction.arguments[0])
        value[memory.get_value(instruction.arguments[1])] = memory.get_value(instruction.arguments[2])[0]
        memory.set_variable(instruction.arguments[0], value)

    # Type related instructions
    elif instruction.name == "TYPE":
        result = None 
        value = memory.get_value(instruction.arguments[1])

        if type(value) == int:
            result = "int"
        elif type(value) == str:
            result = "string"
        elif type(value) == float:
            result = "float"
        elif type(value) == bool:
            result = "bool"
        elif type(value) == None:
            result = "nil"

        memory.set_variable(instruction.arguments[0], result)

    # Flow related instructions
    elif instruction.name == "LABEL":
        pass
    elif instruction.name == "JUMP":
        index = labels[instruction.arguments[0]]
    elif instruction.name == "JUMPIFEQ":
        if memory.get_value(instruction.arguments[1]) == memory.get_value(instruction.arguments[2]):
            index = labels[instruction.arguments[0]]
    elif instruction.name == "JUMPIFNEQ":
        if memory.get_value(instruction.arguments[1]) != memory.get_value(instruction.arguments[2]):
            index = labels[instruction.arguments[0]]
    elif instruction.name == "EXIT":
        index = len(instructions) + 1
    
    # Debug instructions
    elif instruction.name == "DPRINT":
        pass
    elif instruction.name == "BREAK":
        pass

    else:
        sys.exit(f"Runtime: Undefined instruction {instruction.name}")

    index = index + 1

print(max_var)