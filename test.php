<?php

$iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator("tests"));
$files = array(); 

foreach ($iterator as $file) {
    if ($file->isDir()){ 
        continue;
    }
    $files[] = $file->getPathname(); 
}

$total = count(array_filter($files, function($x) {
    return substr_compare($x, ".src", -4) === 0;
}));

$completed = 1;
foreach($files as $file) {
    $info = pathinfo($file);

    if($info["extension"] == "src") {
        echo "Running test: ${info["dirname"]}/${info["filename"]} (${completed}/${total})\n";
        $expected = intval(file_get_contents("${info["dirname"]}/${info["filename"]}.rc"));

        exec("php7.4 parse.php < ${info["dirname"]}/${info["filename"]}.src > output.xml 2>&1", $output, $retval);

        if($retval != $expected) {
            echo "- Return code mismatch. Expected: ${expected}, Got: ${retval}\n";
            exit;
        } else {
            echo "- Return codes are the same\n";
        }

        if($expected == 0) {
            //exec("mdcxml output.xml ${info["dirname"]}/${info["filename"]}.out", $output, $retval);
            exec("java -jar /pub/courses/ipp/jexamxml/jexamxml.jar output.xml ${info["dirname"]}/${info["filename"]}.out /dev/null options", $output, $retval);
            
            if($retval != 0) {
                echo "- Output XML is not identical (${info["dirname"]}/${info["filename"]})\n";
                exit;
            } else {
                echo "- Output XML is the same\n";
            }
        }

        $completed++;
    }
}