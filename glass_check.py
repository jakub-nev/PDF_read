"""Kontrola skla — GUI: cross-check a glass order xlsx against an invoice pdf."""
from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from invoice_parser import parse_invoice
from matcher import match_items
from order_parser import parse_order
from report import result_row, write_report

_TAG_COLORS = {"OK": "#c6efce", "WARNING": "#ffeb9c",
               "MISSING": "#ffc7ce", "EXTRA": "#ffc7ce"}
_COLUMNS = ["Stav", "Objekt", "Pozice", "Rozměr obj.", "Rozměr fakt.",
            "Ks obj.", "Ks fakt.", "Skladba obj.", "Skladba fakt.", "Problémy"]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kontrola skla — objednávka vs. faktura")
        self.geometry("1200x600")
        self.pdf_path = tk.StringVar()
        self.xlsx_path = tk.StringVar()
        self.results = []

        picker = ttk.Frame(self, padding=8)
        picker.pack(fill="x")
        self._file_row(picker, 0, "Faktura (PDF):", self.pdf_path,
                       [("PDF", "*.pdf")])
        self._file_row(picker, 1, "Objednávka (Excel):", self.xlsx_path,
                       [("Excel", "*.xlsx")])
        picker.columnconfigure(1, weight=1)

        bar = ttk.Frame(self, padding=(8, 0, 8, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="Zkontrolovat", command=self.check).pack(side="left")
        self.export_btn = ttk.Button(bar, text="Uložit report",
                                     command=self.export, state="disabled")
        self.export_btn.pack(side="left", padx=8)
        self.summary = ttk.Label(bar, text="", font=("", 10, "bold"))
        self.summary.pack(side="left", padx=16)

        self.tree = ttk.Treeview(self, columns=_COLUMNS, show="headings")
        widths = (110, 110, 70, 100, 100, 60, 60, 150, 260, 320)
        for col, w in zip(_COLUMNS, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, stretch=col == "Problémy")
        for status, color in _TAG_COLORS.items():
            self.tree.tag_configure(status, background=color)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _file_row(self, parent, row, text, var, types):
        ttk.Label(parent, text=text, width=18).grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1,
                                                 sticky="ew", padx=4)
        ttk.Button(parent, text="Vybrat…",
                   command=lambda: var.set(
                       filedialog.askopenfilename(filetypes=types) or var.get())
                   ).grid(row=row, column=2)

    def check(self) -> None:
        if not self.pdf_path.get() or not self.xlsx_path.get():
            messagebox.showwarning("Kontrola skla",
                                   "Vyberte prosím oba soubory.")
            return
        try:
            invoice_items = parse_invoice(self.pdf_path.get())
            order_items = parse_order(self.xlsx_path.get())
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Chyba při čtení souborů", str(exc))
            return
        if not invoice_items:
            messagebox.showerror(
                "Kontrola skla",
                "Formát faktury nebyl rozpoznán — nenašel jsem žádné položky.")
            return
        if not order_items:
            messagebox.showerror(
                "Kontrola skla",
                "V objednávce nebyly nalezeny žádné řádky.")
            return

        self.results = match_items(order_items, invoice_items)
        self.tree.delete(*self.tree.get_children())
        for r in self.results:
            values = result_row(r)
            self.tree.insert("", "end", values=values, tags=(r.status,))
        ok = sum(1 for r in self.results if r.status == "OK")
        total = len(self.results)
        problems = total - ok
        self.summary.config(
            text=f"{ok} z {total} položek v pořádku, {problems} "
                 + ("problém" if problems == 1 else
                    "problémy" if 2 <= problems <= 4 else "problémů"))
        self.export_btn.config(state="normal")

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile="kontrola_skla.xlsx")
        if not path:
            return
        try:
            write_report(self.results, path)
        except Exception as exc:
            messagebox.showerror("Chyba při ukládání", str(exc))
            return
        messagebox.showinfo("Kontrola skla", f"Report uložen:\n{path}")


if __name__ == "__main__":
    App().mainloop()
