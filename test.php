<?php
ini_set("display_errors", "stderr");

// Custom error function, writes message to stderr and then exists the program
function error(string $data, int $code) {
    error_log($data);
    exit($code);
}

// Custom echo function, writes message to stdout and exists with return code 0
function success(string $data) {
    echo $data;
    exit(0);
}

$arguments = [
    "directory" => false,
    "recursive" => false,
    "parse-script" => false,
    "int-script" => false,
    "parse-only" => false,
    "int-only" => false,
    "jexamxml" => false,
    "jexamcfg" => false,
    "testlist" => false,
    "match" => false
];

array_shift($argv);
foreach($argv as $arg) {
    if($arg == "--help" && count($argv) == 1) {
        success("--help - List test script parameters\n");
    } else if(preg_match("/^--directory=(\S+)$/", $arg, $matches) && $arguments["testlist"] === false) {
        $arguments["directory"] = $matches[1];
    } else if(preg_match("/^--parse-script=(\S+)$/", $arg, $matches)) {
        $arguments["parse-script"] = $matches[1];
    } else if(preg_match("/^--int-script=(\S+)$/", $arg, $matches)) {
        $arguments["int-script"] = $matches[1];
    } else if(preg_match("/^--jexamxml=(\S+)$/", $arg, $matches)) {
        $arguments["jexamxml"] = $matches[1];
    } else if(preg_match("/^--jexamcfg=(\S+)$/", $arg, $matches)) {
        $arguments["jexamcfg"] = $matches[1];
    } else if(preg_match("/^--testlist=(\S+)$/", $arg, $matches) && $arguments["directory"] === false) {
        $arguments["testlist"] = $matches[1];
    } else if(preg_match("/^--match=(\S+)$/", $arg, $matches) && @preg_match($matches[1], null) !== false) {
        $arguments["match"] = $matches[1];
    } else if($arg == "--recursive") {
        $arguments["recursive"] = true;
    } else if($arg == "--parse-only" && $arguments["int-only"] === false && $arguments["int-script"] === false) {
        $arguments["parse-only"] = true;
    } else if($arg == "--int-only" && $arguments["parse-only"] === false && $arguments["parse-script"] === false) {
        $arguments["int-only"] = true;
    } else 
        error("Unknown argument ${arg} or invalid combination of arguments", 10);
}

// If specific script path wasn't provided, set it to default value
if($arguments["directory"] === false) $arguments["directory"] = "./";
if($arguments["parse-script"] === false) $arguments["parse-script"] = "parse.php";
if($arguments["int-script"] === false) $arguments["int-script"] = "interpret.py";
if($arguments["jexamxml"] === false) $arguments["jexamxml"] = "/pub/courses/ipp/jexamxml/jexamxml.jar";
if($arguments["jexamcfg"] === false) $arguments["jexamcfg"] = "/pub/courses/ipp/jexamxml/options";

// Verify that file or directory exists
function assert_path_exists(string $path, bool $dir = false, int $error) {
    if(!file_exists($path) || is_dir($path) !== $dir)
        error("File or path ${path} does not exists", $error);
}

// Check if all provided scripts exist
assert_path_exists($arguments["directory"], true, 41);
assert_path_exists($arguments["parse-script"], false, 41);
assert_path_exists($arguments["int-script"], false, 41);
assert_path_exists($arguments["jexamxml"], false, 41);
assert_path_exists($arguments["jexamcfg"], false, 41);

if($arguments["testlist"] !== false)
    assert_path_exists($arguments["testlist"], false, 41);

// List of all iterators that will be used to fetch files
$iterators = [];

// List of all test files
$files = [];

// Check if filepath has .src extension and if yes, return the path without extension
function extract_src_file(string $filename) {
    $info = pathinfo($filename);

    if($info["extension"] != "src")
        return false;

    if($arguments["match"] === true && !preg_match($arguments["match"], $info["filename"]))
        return false;

    return "${info["dirname"]}/{$info["filename"]}";
}

// If there is testlist provided, load all src files and directory iterators
if($arguments["testlist"] !== false) {
    $file = file_get_contents($arguments["testlist"]);

    if($file === false)
        error("Could not read provided testlist file", 41);

    $lines = array_filter(array_map("trim", explode("\n", $file)));
    foreach($lines as $line) {
        if(!file_exists($line))
            error("File or path ${line}, provided in testlist file does not exists", 11); // ??????????????????????

        if(!is_dir($line)) {
            $src_file = extract_src_file($line);
            if($src_file !== false && !in_array($src_file, $files))
                $files[] = $src_file;
        } else {
            $iterators[] = $arguments["recursive"] === true ? 
                new RecursiveIteratorIterator(new RecursiveDirectoryIterator($line)) :
                new IteratorIterator(new DirectoryIterator($line));
        }
    }
} else {
    $iterators[] = $arguments["recursive"] === true ? 
        new RecursiveIteratorIterator(new RecursiveDirectoryIterator($arguments["directory"])) :
        new IteratorIterator(new DirectoryIterator($arguments["directory"]));
}

// Iterate all provided directories and save .src files if available
foreach($iterators as $iterator) {
    foreach($iterator as $file) {
        if ($file->isDir())
            continue;

        $src_file = extract_src_file($file);
        if($src_file !== false && !in_array($src_file, $files))
            $files[] = $src_file;
    }
}

// Check if file exists and create one if it does not
function assert_file_created(string $filename, string $content) {
    if(file_exists($filename))
        return;
    
    if(file_put_contents($filename, $content) === false)
        error("Could not create file ${filename}", 11);
}

// Create missing files if they do not exist
foreach($files as $file) {
    assert_file_created("${file}.in", "");
    assert_file_created("${file}.out", "");
    assert_file_created("${file}.rc", "0");
}

// List of all performed tests
$tests = [];

// Run all provided tests
foreach($files as $file) {
    $test = [
        "path" => dirname($file),
        "name" => basename($file),
        "error" => false
    ];

    // Return code that we expect to get
    $expected_rc = intval(file_get_contents("${file}.rc"));

    if($arguments["parse-only"] === true) {    
        exec("php7.4 ${arguments["parse-script"]} < ${file}.src > testphp_tmp 2>&1", $output, $actual_rc);

        // Return codes do not match, either wrong parser implementation or incorrect return code in test file
        if($actual_rc != $expected_rc) {
            $test["error"] = "Parser returned with code ${actual_rc}, but {$expected_rc} was expected";
            $tests[] = $test;
            continue;
        }

        // Parser returned some XML output, compare it to test output
        if($actual_rc == 0) {
            exec("java -jar ${arguments["jexamxml"]} testphp_tmp ${file}.out /dev/null ${arguments["jexamcfg"]}", $output, $actual_rc);
            
            // XML files are not the same
            if($actual_rc != 0)
                $test["error"] = "Parser output xml file does not match the test one";
        }
    } else if($arguments["int-only"] === true) {
        exec("python3.8 ${arguments["int-script"]} < ${file}.src > testphp_tmp 2>&1", $output, $actual_rc);

        // Return codes do not match, either wrong interpret implementation or incorrect return code in test file
        if($actual_rc != $expected_rc) {
            $test["error"] = "Interpret returned with code ${actual_rc}, but {$expected_rc} was expected";
            $tests[] = $test;
            continue;
        }

        // Compare interpret output to test output
        if($actual_rc == 0) {
            exec("diff testphp_tmp ${file}.out 2>&1", $output, $actual_rc);

            if($actual_rc != 0)
                $test["error"] = "Interpret output file does not match the test one";
        }
    } else {
        exec("php7.4 ${arguments["parse-script"]} < ${file}.src > testphp_tmp 2>&1", $output, $actual_rc);

        // Return codes do not match, either wrong parser implementation or incorrect return code in test file
        if($actual_rc != 0 && $actual_rc != $expected_rc) {
            $test["error"] = "Parser returned with code ${actual_rc}, but {$expected_rc} was expected";
        }

        if($actual_rc == 0) {
            exec("python3.8 ${arguments["int-script"]} < testphp_tmp > testphp_tmp 2>&1", $output, $actual_rc);

            // Return codes do not match, either wrong interpret implementation or incorrect return code in test file
            if($actual_rc != $expected_rc) {
                $test["error"] = "Interpret returned with code ${actual_rc}, but {$expected_rc} was expected";
                $tests[] = $test;
                continue;
            }

            // Compare interpret output to test output
            exec("diff testphp_tmp ${file}.out 2>&1", $output, $actual_rc);

            if($actual_rc != 0)
                $test["error"] = "Interpret output file does not match the test one";
        }
    }

    $tests[] = $test;
}

if(file_exists("testphp_tmp"))
    unlink("testphp_tmp");

sort($tests);

// Generate output HTML summary
$document = new DOMDocument("1.0", "UTF-8");

// Generate core HTML structure
$html = $document->appendChild($document->createElement("html"));
$head = $html->appendChild($document->createElement("head"));
$body = $html->appendChild($document->createElement("body"));

// Add custom styles
$styles = $document->createElement("style", ".test-list{display:flex}.test-list .column{flex:1;margin:10px}.test-list .column .item{padding:10px;margin-top:5px}.test-list .column .passed{background-color:green}.test-list .column .failed{background-color:red}.test-list .column .item .name{font-size:20px;font-weight:700}");
$head->appendChild($styles);

// Main element, contains two columns
$list = $body->appendChild($document->createElement("div"));
$list->setAttribute("class", "test-list");

// Left column, contains passed tests
$passed_column = $list->appendChild($document->createElement("div"));
$passed_column->setAttribute("class", "column");

// Right column, contains failed tests
$failed_column = $list->appendChild($document->createElement("div"));
$failed_column->setAttribute("class", "column");

// Text header in left column, contains number of passed tests
$passed_header = $document->createElement("h2");
$passed_column->appendChild($passed_header);

// Text header in right column, contains number of passed tests
$failed_header = $document->createElement("h2");
$failed_column->appendChild($failed_header);

$passed = 0;
$failed = 0;

foreach($tests as $test) {
    $element = $document->createElement("div");
    $element->setAttribute("class", $test["error"] ? "item failed" : "item passed");

    $name = $element->appendChild($document->createElement("div", $test["name"]));
    $name->setAttribute("class", "name");

    $path = $element->appendChild($document->createElement("div", $test["path"]));
    $path->setAttribute("class", "path");

    $error = $element->appendChild($document->createElement("div", "Result: " . ($test["error"] ? $test["error"] : "Success")));
    $error->setAttribute("class", "error");

    if($test["error"] !== false) {
        $failed_column->appendChild($element);
        $failed++;
    } else {
        $passed_column->appendChild($element);
        $passed++;
    }
}

$failed_header->appendChild($document->createTextNode("Failed tests: " . $failed));
$passed_header->appendChild($document->createTextNode("Passed tests: " . $passed));

success($document->saveHTML());