# Generátor školních testů

Jednoduchý pomocník na generování testů pro žáky základních a středních škol pro libovlný počet skupin.


## Jak to funguje?

- nadefinují se kategorie testu
 - každá kategorie testu obsahuje otázky a správné odpovědi
 - z každé kategorie se náhodně (podle skupiny) vybere definovaný počet otázek
- skript vše zkombinuje do dvou výsledných PDF souborů
 - jeden pro žáky
 - druhý s autorským řešením
- jeden test může rozšiřovat jiný test


## Co je podporováno za otázky?

- každá otázka má jeden úvodní text s jedním nebo více řádky
- každé otázka může obsahovat libovolný počet podotázek typu:
  - volný text
  - výběr z možností


## Použití

Příkaz

```bash
python3 compile.py rozsirujici-test.yaml 6
```

vygeneruje 6 skupin rozšiřujícího testu.
