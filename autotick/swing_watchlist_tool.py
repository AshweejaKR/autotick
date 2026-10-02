# -*- coding: utf-8 -*-
"""
Created on Wed Sep 30 2026

@author: ashwe

Small NSE watchlist builder. Run: python -m autotick.swing_watchlist_tool
"""

from __future__ import annotations

import csv
import math
import os
import re
import subprocess
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from zoneinfo import ZoneInfo

from autotick.providers.brokers.angelone.session import AngelOneSession


def positive_price(value, name):
    try:
        price = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive price") from exc
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"{name} must be a positive finite price")
    return price


def validate_row(session, symbol, trigger):
    """Resolve the actual NSE symbol and compare trigger against broker LTP."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Enter a symbol, for example INFY-EQ")
    trigger = positive_price(trigger, "Trigger price")
    symbol, token = session.get_instrument(symbol, "NSE")
    response = session.call(session.client.ltpData, "NSE", symbol, token)
    if not isinstance(response, dict) or response.get("status") is not True:
        raise ValueError(f"AngelOne LTP unavailable for {symbol}")
    data = response.get("data")
    ltp = positive_price(data.get("ltp") if isinstance(data, dict) else None, "LTP")
    difference = (trigger - ltp) / ltp * 100
    magnitude = abs(difference)
    note = "STRONG >10%" if magnitude > 10 else "WARNING >5%" if magnitude > 5 else "OK"
    return symbol.upper(), trigger, ltp, difference, note


def write_import(folder, rows):
    """Write only symbol/trigger columns, without overwriting an existing file."""
    if not rows:
        raise ValueError("Add at least one validated symbol")
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    path = Path(folder) / f"swing_watchlist_import_{now:%Y%m%d_%H%M%S}.csv"
    stream = path.open("x", newline="", encoding="utf-8")
    try:
        with stream:
            writer = csv.writer(stream)
            writer.writerow(["symbol", "trigger_price"])
            writer.writerows((row[0], row[1]) for row in rows)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def upload_import(path, host, key, folder):
    """SCP the CSV to a temporary name, then rename it in the EC2 folder."""
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9.-]*", host):
        raise ValueError("SSH target must be user@hostname")
    if not re.fullmatch(r"/[A-Za-z0-9_./-]*", folder):
        raise ValueError("EC2 folder must be an absolute path without spaces")
    if not Path(key).is_file() or not Path(path).is_file():
        raise ValueError("CSV and SSH private key must exist")
    if not re.fullmatch(r"swing_watchlist_import_\d{8}_\d{6}\.csv", Path(path).name):
        raise ValueError("Choose a generated import CSV")
    options = ["-i", str(Path(key).resolve()), "-o", "BatchMode=yes",
               "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new"]
    remote = f"{folder.rstrip('/')}/{Path(path).name}"
    for command in (
        ["scp", *options, str(Path(path).resolve()), f"{host}:{remote}.upload"],
        ["ssh", *options, host, f"mv -- {remote}.upload {remote}"],
    ):
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "EC2 upload failed")


class WatchlistWindow:
    def __init__(self, root):
        self.root, self.session, self.saved = root, None, None
        self.saved_bytes, self.rows, self.busy = b"", {}, False
        self.pool = ThreadPoolExecutor(max_workers=1)
        root.title("AutoTick - Swing watchlist builder")
        root.geometry("790x440")
        self.status = tk.StringVar(value="Choose angelone_keys.env to log in. Exchange: NSE")
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)
        self.login_button = ttk.Button(frame, text="Login: choose keys file", command=self.login)
        self.login_button.pack(anchor="w")
        entry = ttk.Frame(frame)
        entry.pack(fill="x", pady=12)
        ttk.Label(entry, text="Symbol").pack(side="left")
        self.symbol = ttk.Entry(entry, width=22)
        self.symbol.pack(side="left", padx=8)
        ttk.Label(entry, text="Trigger price").pack(side="left")
        self.trigger = ttk.Entry(entry, width=14)
        self.trigger.pack(side="left", padx=8)
        self.add_button = ttk.Button(entry, text="Add + Validate", command=self.add)
        self.add_button.pack(side="left")
        self.table = ttk.Treeview(frame, columns=("symbol", "trigger", "ltp", "difference", "note"),
                                  show="headings", height=10)
        for column, label, width in zip(self.table["columns"],
                ("Symbol", "Trigger", "Broker LTP", "Difference %", "Note"), (170, 110, 110, 120, 160)):
            self.table.heading(column, text=label)
            self.table.column(column, width=width, anchor="w")
        self.table.tag_configure("WARNING >5%", background="#fff1c2")
        self.table.tag_configure("STRONG >10%", background="#ffd9d9")
        self.table.pack(fill="both", expand=True)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=10)
        self.remove_button = ttk.Button(buttons, text="Remove selected", command=self.remove)
        self.create_button = ttk.Button(buttons, text="Create CSV", command=self.create)
        self.review_button = ttk.Button(buttons, text="Review saved CSV", command=self.review)
        self.upload_button = ttk.Button(buttons, text="Upload to EC2 (optional)", command=self.upload)
        for button in (self.remove_button, self.create_button, self.review_button, self.upload_button):
            button.pack(side="left", padx=(0, 8))
        ttk.Label(frame, text="Difference = (trigger - LTP) / LTP. LTP is broker reported, including last price when closed.").pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, wraplength=750).pack(anchor="w", pady=(6, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.controls()

    def controls(self):
        for widget, enabled in (
            (self.login_button, self.session is None), (self.add_button, self.session is not None),
            (self.create_button, bool(self.rows)), (self.remove_button, bool(self.rows)),
            (self.review_button, self.saved is not None), (self.upload_button, self.saved is not None),
            (self.symbol, True), (self.trigger, True),
        ):
            widget.configure(state="normal" if enabled and not self.busy else "disabled")

    def run(self, action, done):
        self.busy = True
        self.status.set("Working...")
        self.controls()
        future = self.pool.submit(action)

        def poll():
            if not future.done():
                self.root.after(100, poll)
                return
            self.busy = False
            self.controls()
            try:
                done(future.result())
            except Exception as exc:
                self.status.set("Failed; correct the input and retry.")
                messagebox.showerror("Watchlist", str(exc))
            self.controls()

        self.root.after(100, poll)

    def login(self):
        path = filedialog.askopenfilename(title="Select angelone_keys.env", filetypes=[("Environment file", "*.env"), ("All files", "*")])
        if not path:
            return

        def connect():
            session = AngelOneSession(path)
            session.login()
            return session

        def connected(session):
            self.session = session
            self.status.set("Logged in. Add NSE symbols and trigger prices one by one.")

        self.run(connect, connected)

    def display(self):
        self.table.delete(*self.table.get_children())
        for symbol, trigger, ltp, difference, note in self.rows.values():
            self.table.insert("", "end", iid=symbol, values=(symbol, f"{trigger:g}", f"{ltp:g}", f"{difference:+.2f}", note), tags=(note,))

    def add(self):
        symbol, trigger = self.symbol.get(), self.trigger.get()

        def added(row):
            if row[0] in self.rows:
                raise ValueError(f"{row[0]} already added; remove it first to change its trigger")
            self.rows[row[0]] = row
            self.saved = None
            self.display()
            self.symbol.delete(0, "end")
            self.trigger.delete(0, "end")
            self.status.set(f"{row[0]}: {row[4]}. Add another symbol or create CSV.")

        self.run(lambda: validate_row(self.session, symbol, trigger), added)

    def remove(self):
        for symbol in self.table.selection():
            self.rows.pop(symbol)
        self.saved = None
        self.display()
        self.controls()

    def create(self):
        folder = filedialog.askdirectory(title="Choose folder containing swing_watchlist.csv",
                                         initialdir=str(Path(__file__).parent / "config"))
        if not folder:
            return
        self.saved = None
        rows = list(self.rows.values())

        def save():
            refreshed = [validate_row(self.session, row[0], row[1]) for row in rows]
            return refreshed, write_import(folder, refreshed)

        def saved(result):
            refreshed, self.saved = result
            self.rows = {row[0]: row for row in refreshed}
            self.saved_bytes = self.saved.read_bytes()
            self.display()
            self.status.set(f"Saved: {self.saved}")
            messagebox.showinfo("CSV created", "Review the CSV and the price warnings in the table.\nUpload to EC2 only when satisfied.")

        self.run(save, saved)

    def review(self):
        try:
            os.startfile(self.saved)
        except (AttributeError, OSError) as exc:
            messagebox.showinfo("Review CSV", f"Open this file manually:\n{self.saved}\n\n{exc}")

    def upload(self):
        try:
            if self.saved.read_bytes() != self.saved_bytes:
                raise ValueError("Update rows in the window and create the CSV again before uploading.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("CSV changed or unavailable", str(exc))
            return
        if not messagebox.askyesno("Confirm manual review", f"Have you manually reviewed this CSV and its warnings?\n\n{self.saved}\n\nUpload it to EC2?"):
            return
        host = simpledialog.askstring("EC2", "SSH target (ec2-user@hostname):")
        if not host:
            return
        key = filedialog.askopenfilename(title="Select SSH private key (.pem)")
        if not key:
            return
        folder = simpledialog.askstring("EC2", "Absolute folder containing swing_watchlist.csv:")
        if folder:
            self.run(lambda: upload_import(self.saved, host.strip(), key, folder.strip()),
                     lambda _: self.status.set(f"Uploaded {self.saved.name} to {host}:{folder}"))

    def close(self):
        if self.busy:
            messagebox.showinfo("Working", "Wait for the current operation to finish before closing.")
            return
        self.pool.shutdown(wait=False)
        self.root.destroy()


def main():
    root = tk.Tk()
    window = WatchlistWindow(root)
    try:
        root.mainloop()
    finally:
        if window.session is not None:
            try:
                window.session.logout()
            except Exception:
                pass


if __name__ == "__main__":
    main()
