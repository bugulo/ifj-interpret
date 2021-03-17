Implementační dokumentace k 1. úloze do IPP 2020/2021  
Jméno a příjmení: Michal Šlesár  
Login: xslesa01  

## Spracovanie spúšťacích parametrov

Na úplnom začiatku analyzátor načíta argumenty z globálnej premennej `argv`, skontroluje či tieto parametre existujú, teda či sa v scripte využívajú a následne spracuje do prehľadnejšej podoby pre ďalšie použitie. V prípade neexistujúceho parametru, alebo nesprávne kombinácie parametrov, script končí s návratovou hodnotou `10`.

## Tabuľka inštrukcií 

Všetky dostupné inštrukcie sú registrované v tabuľke inštrukcií, kde kľúč v tabuľke predstavuje `opcode` inštrukcie, a hodnota predstavuje zoznam požadovaných argumentov, respektíve ich typy, ktoré sú definované pomocou konštantných hodnôt `T_VAR`, `T_SYMB`, `T_LABEL` a `T_TYPE`.

## Spracovanie zdrojového kódu

Nasleduje spracovanie zrojového kódu načítaného z štandardného vstupu riadok po riadku. V jednotlivých riadkoch overujeme syntaktickú a lexikálnu správnosť inštrukcie pomocou regulárnych výrazov a zároveň pomocou nich extrahujeme informácie ktoré sú v danom kontexte potrebné. Kontroluje sa teda napríklad správny formát neterminálnych symbolov, správny počet argumentov inštrukcie a ich typy. Extrahované a syntakticky správne informácie postupne ukladáme do štruktúrovaného zoznamu inštrukcií. Pomocou tohto zoznamu je následne vytvorený výstupný XML súbor, generovaný triedou štandardnej knižnice, `DOMDocument`.

## Rozšírenie STATP

Toto rozšírenie má za úlohu spočítať rôzne štatistiky kódu a uložiť ich do požadovaných súborov, zadaných vrámci spúšťacích parametrov. Počas spracovania zdrojového kódu v predošlej časti sa počítajú iba vymazané komentáre. Všetky ostatné podporované štatistiky sa počítajú osobitne, až po spracovaní zdrojového kódu, nad štruktúrovaným zoznamom inštrukcií z predošlej časti. Argumenty sú spracované do prehľadnejšej podoby už vrámci spracovania spúšťacích parametrov na začiatku scriptu. Na konci sa teda iba prejde zoznam týchto spracovaných parametrov a do príslušných súborov sa uložia príslušné štatistiky. Rozšírenie podporuje ukladanie do viacerých súborov naraz, nemôžu mať ale rovnakú cestu, respektíve názov. Pokiaľ nešpecifikujeme súbor, do ktorého chceme zadané štatistiky ukladať, program končí chybou.