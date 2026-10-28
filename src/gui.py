"""A small window for making certificates without a terminal.

One form: which document, who it is for, which grade, which date, and which
kind of output.  The dōjō's own details (school, signatory, crest) live behind
a Settings button and are asked for once, on first run.  Everything here ends
in a call to build_diploma.main() with the same flags the command line takes,
so the window can never produce something the CLI could not.

Tkinter is used because it ships with Python, which keeps the packaged app
small and the code dependency-free.
"""

import datetime
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from menkyo import config as config_mod
from menkyo import paths
from menkyo.service import GRADES, OUTPUTS, FormError, make_argv, run_build

PAD = 8

class SettingsDialog(tk.Toplevel):
    """The dōjō's identity.  Saved to the per-user dojo.toml."""

    FIELDS = [
        ("art", "School / art (流派)", "e.g. 〇〇流柔術. Printed on the certificate and around the crest."),
        ("dojo", "Dōjō (道場)", "e.g. 〇〇道場"),
        ("crest_ring", "Crest lettering", "Four characters along the bottom of the crest; often the dōjō name without 道場."),
        ("signer_title", "Signatory's title", "e.g. 師範"),
        ("signer_name", "Signatory's name", "Kanji, or katakana for a Western name. Empty leaves it blank for hand signing."),
        ("motto", "Motto (optional)", "A short line printed quietly at the left. Empty for none."),
        ("honorific", "Honorific after names", "殿 is the formal form. Empty for none."),
    ]

    def __init__(self, master, cfg, on_saved):
        super().__init__(master)
        self.title("Dōjō settings")
        self.transient(master)
        self.resizable(False, False)
        self.cfg, self.on_saved = cfg, on_saved
        self.vars = {}

        frm = ttk.Frame(self, padding=PAD * 2)
        frm.grid()
        ttk.Label(frm, wraplength=460, text=(
            "These details are printed on every certificate. 〇〇 is the "
            "usual Japanese placeholder; replace it with your own.")
        ).grid(columnspan=2, sticky="w", pady=(0, PAD))

        for row, (key, label, hint) in enumerate(self.FIELDS, start=1):
            ttk.Label(frm, text=label).grid(row=row * 2 - 1, column=0, sticky="w",
                                            padx=(0, PAD), pady=(PAD, 0))
            var = tk.StringVar(value=getattr(cfg, key))
            self.vars[key] = var
            ttk.Entry(frm, textvariable=var, width=28).grid(
                row=row * 2 - 1, column=1, sticky="ew", pady=(PAD, 0))
            ttk.Label(frm, text=hint, wraplength=460, foreground="gray40").grid(
                row=row * 2, column=0, columnspan=2, sticky="w")

        bar = ttk.Frame(frm)
        bar.grid(columnspan=2, sticky="e", pady=(PAD * 2, 0))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Save", command=self.save).pack(side="right", padx=PAD)
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def save(self):
        values = {k: v.get().strip() for k, v in self.vars.items()}
        if len(values["crest_ring"]) > 5:
            messagebox.showerror(
                "Crest lettering", "The crest holds at most five characters "
                "(four looks best).", parent=self)
            return
        for key, value in values.items():
            setattr(self.cfg, key, value)
        try:
            config_mod.save(self.cfg)
        except OSError as e:
            messagebox.showerror("Could not save", str(e), parent=self)
            return
        self.on_saved()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Menkyo — dan & menkyo certificates")
        self.resizable(False, False)
        self.results = queue.Queue()
        self.cfg = config_mod.load()
        self.first_run = not os.path.exists(config_mod.USER_CONFIG)

        today = datetime.date.today()
        self.v_award = tk.StringVar()
        self.v_name = tk.StringVar()
        self.v_grade = tk.StringVar()
        self.v_year = tk.StringVar(value=str(today.year))
        self.v_month = tk.StringVar(value=str(today.month))
        self.v_day = tk.StringVar(value=str(today.day))
        self.v_date_blank = tk.BooleanVar(value=False)
        self.v_output = tk.StringVar(value=list(OUTPUTS)[0])
        self.v_folder = tk.StringVar(value=paths.default_output_dir())
        self.v_status = tk.StringVar()

        self._layout()
        self._refresh_awards()
        self.bind("<Return>", lambda e: self.create())
        if self.first_run:
            self.after(200, self.open_settings)

    # ------------------------------------------------------------ layout --
    def _layout(self):
        frm = ttk.Frame(self, padding=PAD * 2)
        frm.grid()

        self.summary = ttk.Label(frm, font=("TkDefaultFont", 0, "bold"))
        self.summary.grid(row=0, column=0, sticky="w")
        ttk.Button(frm, text="Dōjō settings…", command=self.open_settings).grid(
            row=0, column=1, sticky="e")

        def label(row, text):
            ttk.Label(frm, text=text).grid(row=row, column=0, sticky="w",
                                           padx=(0, PAD), pady=(PAD, 0))

        label(1, "Certificate")
        self.award_box = ttk.Combobox(frm, textvariable=self.v_award,
                                      state="readonly", width=30)
        self.award_box.grid(row=1, column=1, sticky="ew", pady=(PAD, 0))
        self.award_box.bind("<<ComboboxSelected>>", lambda e: self._sync_grade())

        label(2, "Recipient")
        ttk.Entry(frm, textvariable=self.v_name, width=32).grid(
            row=2, column=1, sticky="ew", pady=(PAD, 0))
        ttk.Label(frm, text="In katakana, e.g. ヤン・ヤンセン. Empty leaves it blank "
                            "for a calligrapher.", foreground="gray40",
                  wraplength=360).grid(row=3, column=1, sticky="w")

        label(4, "Grade")
        self.grade_box = ttk.Combobox(frm, textvariable=self.v_grade,
                                      values=GRADES, width=10)
        self.grade_box.grid(row=4, column=1, sticky="w", pady=(PAD, 0))
        self.grade_hint = ttk.Label(frm, foreground="gray40", wraplength=360)
        self.grade_hint.grid(row=5, column=1, sticky="w")

        label(6, "Date")
        d = ttk.Frame(frm)
        d.grid(row=6, column=1, sticky="w", pady=(PAD, 0))
        self.date_widgets = [
            ttk.Spinbox(d, from_=1900, to=2200, textvariable=self.v_year, width=6),
            ttk.Spinbox(d, from_=1, to=12, textvariable=self.v_month, width=3),
            ttk.Spinbox(d, from_=1, to=31, textvariable=self.v_day, width=3),
        ]
        for i, (w, sep) in enumerate(zip(self.date_widgets, ("年", "月", "日"))):
            w.pack(side="left")
            ttk.Label(d, text=sep).pack(side="left", padx=(2, 6))
        ttk.Checkbutton(frm, text="Leave the date blank", variable=self.v_date_blank,
                        command=self._sync_date).grid(row=7, column=1, sticky="w")

        label(8, "Output")
        ttk.Combobox(frm, textvariable=self.v_output, values=list(OUTPUTS),
                     state="readonly", width=40).grid(row=8, column=1, sticky="ew",
                                                      pady=(PAD, 0))

        label(9, "Save in")
        f = ttk.Frame(frm)
        f.grid(row=9, column=1, sticky="ew", pady=(PAD, 0))
        ttk.Entry(f, textvariable=self.v_folder, width=30).pack(side="left", fill="x",
                                                                expand=True)
        ttk.Button(f, text="Choose…", command=self.choose_folder).pack(side="left",
                                                                      padx=(PAD, 0))

        self.go = ttk.Button(frm, text="Create certificate", command=self.create)
        self.go.grid(row=10, column=0, columnspan=2, sticky="e", pady=(PAD * 2, 0))
        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(PAD, 0))
        ttk.Label(frm, textvariable=self.v_status, wraplength=460,
                  justify="left").grid(row=12, column=0, columnspan=2, sticky="w")

    # ------------------------------------------------------------ state ----
    def _refresh_awards(self):
        self.awards = {f"{a.heading}  ({a.slug})": a for a in self.cfg.awards}
        self.award_box["values"] = list(self.awards)
        if self.v_award.get() not in self.awards:
            self.v_award.set(next(iter(self.awards)))
        self.summary.config(text=f"{self.cfg.dojo}  ·  {self.cfg.art}")
        self._sync_grade()

    def _award(self):
        return self.awards[self.v_award.get()]

    def _sync_grade(self):
        has_grade = self._award().grade_column
        self.grade_box.config(state="normal" if has_grade else "disabled")
        self.grade_hint.config(
            text="" if has_grade else "This document names its own grade in the heading.")
        if not has_grade:
            self.v_grade.set("")

    def _sync_date(self):
        state = "disabled" if self.v_date_blank.get() else "normal"
        for w in self.date_widgets:
            w.config(state=state)

    def open_settings(self):
        SettingsDialog(self, self.cfg, self._settings_saved)

    def _settings_saved(self):
        self.cfg = config_mod.load()
        self._refresh_awards()

    def choose_folder(self):
        d = filedialog.askdirectory(initialdir=self.v_folder.get() or None,
                                    title="Save certificates in")
        if d:
            self.v_folder.set(d)

    # ------------------------------------------------------------ build ----
    def _argv(self):
        """Form -> command-line flags.  Raises FormError with a user message."""
        aw = self._award()
        if self.v_date_blank.get():
            date = ""
        else:
            try:
                date = datetime.date(int(self.v_year.get()), int(self.v_month.get()),
                                     int(self.v_day.get())).isoformat()
            except ValueError:
                raise FormError("That date does not exist. Please check the "
                                "year, month and day.")
        return make_argv(self.cfg, award=aw.slug, name=self.v_name.get(),
                         grade=self.v_grade.get(), date=date,
                         output=OUTPUTS[self.v_output.get()],
                         folder=self.v_folder.get().strip())

    def create(self):
        if str(self.go["state"]) == "disabled":
            return
        try:
            argv = self._argv()
        except FormError as e:
            messagebox.showwarning("Check the form", str(e), parent=self)
            return
        if self.cfg.source == config_mod.EXAMPLE_CONFIG:
            if not messagebox.askyesno(
                    "Placeholder details",
                    "The dōjō details are still the 〇〇 placeholders. "
                    "Create the certificate anyway?", parent=self):
                return self.open_settings()
        self.go.config(state="disabled")
        self.progress.start(12)
        self.v_status.set("Creating… this takes up to a minute.")
        threading.Thread(target=lambda: self.results.put(run_build(argv)),
                         daemon=True).start()
        self.after(150, self._poll)

    def _poll(self):
        try:
            ok, files, msg = self.results.get_nowait()
        except queue.Empty:
            self.after(150, self._poll)
            return
        self.progress.stop()
        self.go.config(state="normal")
        if not ok:
            self.v_status.set("Something went wrong.")
            messagebox.showerror("Could not create the certificate", msg, parent=self)
            return
        self.v_status.set(f"Done: {len(files)} file(s) saved.")
        if files:
            self._reveal(files[0])

    @staticmethod
    def _reveal(path):
        """Show the result: select it in Finder."""
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path])


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
