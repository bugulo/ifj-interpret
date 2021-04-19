Implementační dokumentace k 2. úloze do IPP 2020/2021  
Jméno a příjmení: Michal Šlesár  
Login: xslesa01  

## Interpret XML reprezentácie kódu
### Spracovanie spúšťacích parametrov

Na úplnom začiatku interpret načíta argumenty z globálnej premennej `sys.argv`. Následne kontroluje či tieto parametre existujú, teda či sa v skripte využívajú a spracuje ich do prehľadnejšej podoby pre ďalšie použitie. V prípade neexistujúceho parametru, alebo zakázanej kombinácie parametrov, končí skript s návratovou hodnotou `10`. V prípade neexistujúceho súboru zadaného v týchto parametroch, končí skript s návratovou hodnotou `11`.

### Tabuľka inštrukcií 

Všetky dostupné inštrukcie sú registrované v tabuľke inštrukcií, kde kľúč v tabuľke predstavuje `opcode` inštrukcie a hodnota predstavuje zoznam požadovaných argumentov. Tieto argumenty sú reprezentované požadovaným typom, definovaným pomocou datového typu `enum` `ArgumentType`, respektíve `VAR`, `SYMB`, `LABEL`, `TYPE` a `FLOAT`.

### Spracovanie vstupného kódu

Nasleduje spracovanie zrojového kódu načítaného zo štandardného vstupu, prípadne zo súboru zadaného v špúšťacích parametroch. Na prvotné spracovanie XML štruktúry je využitá knižnica `xml.etree`. Výsledná štruktúra je dodatočne kontrolovaná a táto kontrola ma za úlohu odhaliť chýbajúce atribúty v jednotlivých elementoch, nesprávne elementy, nesprávny formát datových typov po lexikálnej stránke, prípadne nezhodu datových typov oproti tabuľke inštrukcií. V takomto prípade končí skript s návratovou hodnotou `32`. Vrámci tohto spracovania sa taktiež ukladá poloha a názov návestí. Inštrukcie sa postupne ukladajú ako inštancia triedy `Instruction` do zoznamu inštrukcií a skript ďalej už pracuje iba s týmto zoznamom.

### Interpretácia inštrukcií

Interpretácia si ukladá index inštrukcie na ktorej sa nachádza. Tento index môžeme navyšovať, aby sme sa posunuli o inštrukciu dopredu, prípadne úplne zmeniť, čo sa využíva pri skokoch na konkrétnu inštrukciu. Interpretácia končí v momente, keď index aktuálnej inštrukcie presiahne veľkosť zoznamu inštrukcií. Na prácu s premennými a rámcami sa využíva inštancia triedy `Memory`, cez ktorú môžeme jednoducho pristupovať ku konkrétnym premenným, tieto premenné meniť, definovať nové premenné, pridávať a odstraňovať lokálne rámce. Na sémantické kontroly slúži funkcia `validate_arguments`, ktorá porovná zadané argumenty konkrétnej inštrukcie s požadovanými typmi a v prípade nezhody, ukončuje skript s návratovou hodnotou `53`. 

### Rozšírenie FLOAT

Toto rozšírenie pridáva v inštrukciách podporu pre prácu s typom float. Bolo ho teda  potrebné pridať do datového typu `ArgumentType`, upraviť spracovanie vstupného kódu a pre tento typ pridať relevantné lexikálne kontroly.

### Rozšírenie STATI

Toto rozšírenie má za úlohu spočítať rôzne štatistiky plynúce z interpretácie a uložiť ich do požadovaného súboru v požadovanom formáte. Tieto požadované informácie sú zadané vrámci spúšťacích parametrov. Na výpočet celkového počtu vykonaných inštrukcií  sa využíva počítadlo, navyšované každou vykonanou inštrukciou. Za účelom určenia inštrukcie, ktorá bola vykonaná najviac krát, bolo pridané do triedy `Instruction` počítadlo počtu jej prevedení. Na určenie maximálneho počtu inicializovaných premenných v akýkoľvek okamih, disponuje trieda `Memory` funkciou `var_count`, ktorá spočíta všetky takéto premenné vo všetkých dostupných rámcoch. Táto funkcia je následne volaná pred každým vykonaním inštrukcie.

## Testovací rámec
### Spracovanie spúšťacích parametrov

Skript pre testovací rámec podobne ako skript pre interpretáciu začína načítaním argumentov z globálnej premennej `argv`, overuje ich existenciu a v prípade zakázanej kombinácie jednotlivých argumentov ukončuje skript s návratovou hodnotou `10`. V prípade problémov s otvorením zadaných súborov sa jedná o chybu `41`.

### Získanie zoznamu všetkých súborov

Skript získava zoznam všetkých súborov pomocou inštancie triedy `DirectoryIterator`, respektíve `RecursiveDirectoryIterator` v prípade rekurzívneho načítavania. Skript následne iteruje touto triedou a získava všetky súbory, z ktorých filtruje práve tie s koncovkou .src a ukladá ich do výsledného zoznamu súborov. Následne sú dogenerované požadované súbory `.rc`, `.in`, `.out`, v prípade že neexistujú.

### Spúšťanie testov

Jednotlivé súbory sú potom pomocou vstavanej funkcie `exec` dosadzované do jednotlivých skriptov, porovnávajú sa návratové hodnoty a výsledok týchto testov je ukladaný do zoznamu prevedených testov, kde každá položka obsahuje názov testu, cestu k testu a prítomnosť chyby, respektíve chybovej hlášky.

### Generovanie súhrnnej správy

Na generovanie súhrnnej správy je využitá trieda `DOMDocument`. Táto súhrnná správa obsahuje zoradený zoznam spustených testov a ich výsledok. Testy sú intuitívne rozdelené do dvoch farebne odlišných stĺpcov, kde ľavý stĺpec predstavuje úspešné testy, a stĺpec vpravo predstavuje neúspešné testy.

### Rozšírenie FILES

Toto rozšírenie ma za úlohu špecifikovať konkrétne testy respektíve zložky, ktoré bude skript prechádzať. Súbory sú priamo pridané do zoznamu testov, pre zložky sú vytvorené iterátory. Rozšírenie taktiež pridáva funkcionalitu pre filtrovanie testov podľa regulérneho výrazu.