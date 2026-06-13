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

## macOS aplikace (.app)

Aplikaci pro macOS sestaví GitHub Actions v cloudu (workflow
`.github/workflows/build-macos.yml`) — není potřeba vlastní Mac. Po nahrání
změn na GitHub se v záložce **Actions** spustí build pro Intel i Apple Silicon
a výsledné `.dmg` se objeví v sekci **Artifacts** daného běhu. Build lze spustit
i ručně tlačítkem **Run workflow**.

Aplikace není podepsaná, takže ji při prvním spuštění otevřete přes pravé
tlačítko → **Open** (jinak ji Gatekeeper zablokuje).
