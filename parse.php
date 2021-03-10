<?php
ini_set("display_errors", "stderr");

// Custom error function, writes message to stderr and then exists the program
function error(string $data, int $code) {
    error_log($data);
    exit($code);
}

if(in_array("--help", $argv)) {
    if(count($argv) != 2)
        error("--help can not be combined with other parameters", 10);

    echo "--help - List parser parameters\n";
    exit(0);
}

// Non-terminals 
const T_VAR = 1;
const T_SYMB = 2;
const T_LABEL = 3;
const T_TYPE = 4;

// List of all instructions and their coresponding arguments
$instruction_set = [
    // Frame and function related instructions
    "MOVE"          => [T_VAR, T_SYMB],
    "CREATEFRAME"   => [],
    "PUSHFRAME"     => [],
    "POPFRAME"      => [],
    "DEFVAR"        => [T_VAR],
    "CALL"          => [T_LABEL],
    "RETURN"        => [],
    // Data stack related instructions
    "PUSHS"         => [T_SYMB],
    "POPS"          => [T_VAR],
    // Arithmetic, relational, boolean and conversion instructions
    "ADD"           => [T_VAR, T_SYMB, T_SYMB],
    "SUB"           => [T_VAR, T_SYMB, T_SYMB],
    "MUL"           => [T_VAR, T_SYMB, T_SYMB],
    "IDIV"          => [T_VAR, T_SYMB, T_SYMB],
    "LT"            => [T_VAR, T_SYMB, T_SYMB],
    "GT"            => [T_VAR, T_SYMB, T_SYMB],
    "EQ"            => [T_VAR, T_SYMB, T_SYMB],
    "AND"           => [T_VAR, T_SYMB, T_SYMB],
    "OR"            => [T_VAR, T_SYMB, T_SYMB],
    "NOT"           => [T_VAR, T_SYMB],
    "INT2CHAR"      => [T_VAR, T_SYMB],
    "STRI2INT"      => [T_VAR, T_SYMB, T_SYMB],
    "INT2FLOAT"     => [T_VAR, T_SYMB],
    "FLOAT2INT"     => [T_VAR, T_SYMB],
    // IO related instructions
    "READ"          => [T_VAR, T_TYPE],
    "WRITE"         => [T_SYMB],
    // String related instructions 
    "CONCAT"        => [T_VAR, T_SYMB, T_SYMB],
    "STRLEN"        => [T_VAR, T_SYMB],
    "GETCHAR"       => [T_VAR, T_SYMB, T_SYMB],
    "SETCHAR"       => [T_VAR, T_SYMB, T_SYMB],
    // Type related instructions
    "TYPE"          => [T_VAR, T_SYMB],
    // Flow related instructions
    "LABEL"         => [T_LABEL],
    "JUMP"          => [T_LABEL],
    "JUMPIFEQ"      => [T_LABEL, T_SYMB, T_SYMB],
    "JUMPIFNEQ"     => [T_LABEL, T_SYMB, T_SYMB],
    "EXIT"          => [T_SYMB],
    // Debug instructions
    "DPRINT"        => [T_SYMB],
    "BREAK"         => []
];

// Statistics for parsed file
$statistics = [
    "comments" => 0,
    "labels" => 0,
    "jumps" => [
        "total" => 0,
        "forward" => 0,
        "backward" => 0,
        "bad" => 0
    ]
];

// List of parsed instructions
$instructions = [];

$header = false;

$current_line = 0;
while(!feof(STDIN)) {
    $current_line++;

    $line = fgets(STDIN);

    // Remove comment, trim the result and explode it to array
    $line = trim(preg_replace("/#.*$/", "", $line, -1, $found));
    $data = array_filter(explode(" ", $line));

    $statistics["comments"] += $found;

    // Line does not contain instruction, we can skip
    if(count($data) == 0) 
        continue;

    // If we didn't parse header yet, the next non-empty line has to be the header
    if(!$header) {
        if(strtoupper($data[0]) == ".IPPCODE21") {
            $header = true;
            continue;
        } else 
            error("Missing header", 21);
    }

    $instruction = [
        "opcode" => strtoupper($data[0]),
        "args" => []
    ];
    
    if(!array_key_exists($instruction["opcode"], $instruction_set))
        error("Undefined instruction ${instruction["opcode"]}", 22);

    $values = array_slice($data, 1);
    $types = $instruction_set[$instruction["opcode"]];

    if(count($values) != count($types))
        error("Incorrect number of arguments in instruction ${current_line}", 23);

    for($i = 0; $i < count($values); $i++) {    
        $value = $values[$i];
        $type = $types[$i];

        if($type == T_VAR && preg_match("/^(?:GF|LF|TF)\@[\p{L}\_\-\$\&\%\*\!\?]+[\p{L}\p{N}\_\-\$\&\%\*\!\?]*$/", $value)) {
            $instruction["args"][] = ["type" => "var", "value" => $value];
        } else if($type == T_LABEL && preg_match("/^[\p{L}\_\-\$\&\%\*\!\?]+[\p{L}\p{N}\_\-\$\&\%\*\!\?]*$/", $value)) {
            $instruction["args"][] = ["type" => "label", "value" => $value];
        } else if($type == T_TYPE && preg_match("/^(int|string|bool|float)$/", $value, $matches)) {
            $instruction["args"][] = ["type" => "type", "value" => $matches[1]];
        } else if($type == T_SYMB && preg_match("/^(string|int|bool|nil|float|GF|LF|TF)@(.*)$/", $value, $matches)) {
            if($matches[1] == "string") {
                $stripped = preg_replace("/\\\\\d\d\d/", "", $matches[2]);
                $stripped = preg_replace("/\<\>\&/", "", $stripped);

                preg_match("/^\#|\\\\|0x(?:[0-2][0-9]|3[0-2]|3[5-9]|[4-8][0-9]|9[0-2])$/", $stripped, $matches2);

                if(count($matches2) != 0)
                    error("Syntax error on line ${current_line}", 23);

                $instruction["args"][] = ["type" => "string", "value" => $matches[2]];
            } else if($matches[1] == "int" && preg_match("/^[+-]?\d+$/", $matches[2])) {
                $instruction["args"][] = ["type" => "int", "value" => $matches[2]];
            } else if($matches[1] == "bool" && ($matches[2] == "true" || $matches[2] == "false")) {
                $instruction["args"][] = ["type" => "bool", "value" => $matches[2]];
            } else if($matches[1] == "float" && preg_match("/^0x\d+(?:\.\d+)?p\+\d+$/", $matches[2])) {
                $instruction["args"][] = ["type" => "float", "value" => $matches[2]];
            } else if($matches[1] == "nil" && $matches[2] == "nil") {
                $instruction["args"][] = ["type" => "nil", "value" => "nil"];
            } else if(($matches[1] == "GF" || $matches[1] == "LF" || $matches[1] == "TF") && preg_match("/^[\p{L}\_\-\$\&\%\*\!\?]+[\p{L}\p{N}\_\-\$\&\%\*\!\?]*$/", $matches[2])) {
                $instruction["args"][] = ["type" => "var", "value" => $value];
            } else
                error("Syntax error on line ${current_line}", 23);
        } else
            error("Syntax error on line ${current_line}", 23);
    }

    $instructions[] = $instruction;
}

if(!$header)
    error("Missing header", 21);

// Calculate statistics for parsed instructions
foreach($instructions as $key => $data) {
    if(in_array($data["opcode"], ["JUMP", "JUMPIFEQ", "JUMPIFNEQ", "CALL"])) {
        $found = NULL;
        foreach($instructions as $target_key => $target_data)
            if($target_data["opcode"] == "LABEL" && $target_data["args"][0]["value"] == $data["args"][0]["value"])
                $found = $target_key;
        
        if($found > $key)
            $statistics["jumps"]["forward"]++;
        else if($found < $key)
            $statistics["jumps"]["backward"]++;
        else if($found == NULL)
            $statistics["jumps"]["bad"]++;

        $statistics["jumps"]["total"]++;
    } else if($data["opcode"] == "LABEL") {
        $statistics["labels"]++;
    } else if($data["opcode"] == "RETURN")
        $statistics["jumps"]["total"]++;
}

// Generate stat related files
/*$current_file = NULL;
array_shift($argv);
foreach($argv as $arg) {
    if(preg_match("/^--stats=(\S+)$/", $arg, $matches)) {
        if($matches[1] == $current_file)
            error("Multiple definitions of stats targeting the same file (${matches[1]})", 12);

        $current_file = $matches[1];
        if(file_put_contents($current_file, "") === false)
            error("Can't write into file ${current_file}", 12);
    } else if($current_file != NULL) {
        $output = 0;

        if($arg == "--loc")
            $output = count($instructions);
        else if($arg == "--comments")
            $output = $statistics["comments"];
        else if($arg == "--labels")
            $output = $statistics["labels"];
        else if($arg == "--jumps")
            $output = $statistics["jumps"]["total"];
        else if($arg == "--fwjumps")
            $output = $statistics["jumps"]["forward"];
        else if($arg == "--backjumps")
            $output = $statistics["jumps"]["backward"];
        else if($arg == "--badjumps")
            $output = $statistics["jumps"]["bad"];

        if(file_put_contents($current_file, $output . "\n", FILE_APPEND) === false)
            error("Can't write into file ${current_file}", 12);
    } else {
        error("Unknown command line argument", 10);
    }
}*/

$document = new DOMDocument("1.0", "UTF-8");
$document->formatOutput = true;

$program = $document->createElement("program");
$program->setAttribute("language", "IPPcode21");
$document->appendChild($program);

foreach($instructions as $key => $data) {
    $instruction = $document->createElement("instruction");
    $instruction->setAttribute("order", $key + 1);
    $instruction->setAttribute("opcode", $data["opcode"]);

    foreach($data["args"] as $key => $data) {
        $argument = $document->createElement("arg" . ($key + 1));
        $argument->setAttribute("type", $data["type"]);

        $text = $document->createTextNode($data["value"]);
        $argument->appendChild($text);

        $instruction->appendChild($argument);
    }

    $program->appendChild($instruction);
}

echo $document->saveXML();
exit(0);