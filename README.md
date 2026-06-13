# Kontrola skla

Porovná objednávku skel (Excel) s fakturou od dodavatele (PDF) a upozorní na
rozdíly v rozměrech, počtech kusů a skladbě skla.

## Spuštění

    pip install pdfplumber openpyxl
    python glass_check.py

1. Vyberte fakturu (PDF) a objednávku (Excel).
2. Klikněte na **Zkontrolovat**.
3. Zelené řádky jsou v pořádku, oranžové mají rozdíl (popsaný ve sloupci
   Problémy), červené položky chybí na faktuře nebo jsou tam navíc.
4. **Uložit report** vytvoří barevný Excel s výsledky.

Položky se párují podle rozměru (šířka × výška, případně prohozené) a
porovnává se počet kusů a skladba (tloušťky skel a meziskelní rámeček).

## Testy

    pip install pytest
    pytest
