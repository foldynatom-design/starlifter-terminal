# -*- coding: utf-8 -*-
"""
Universal Keyboard Shortcuts & Clipboard Handler for Starlifter Terminal.
Binds Ctrl+C (Copy), Ctrl+V (Paste), Ctrl+X (Cut), Ctrl+A (Select All)
globally to all Entry, CTkEntry, Textbox, and CTkTextbox widgets.
Handles clipboard exceptions safely without crashing the GUI.
"""

import tkinter as tk
import customtkinter as ctk


def safe_copy(widget):
    """Copy selected text from entry/textbox to system clipboard."""
    try:
        # Unwrap CustomTkinter inner widget if needed
        w = getattr(widget, '_entry', getattr(widget, '_textbox', widget))

        if hasattr(w, 'selection_get'):
            try:
                selected_text = w.selection_get()
                w.clipboard_clear()
                w.clipboard_append(selected_text)
            except Exception:
                pass
    except Exception:
        pass


def safe_paste(widget):
    """Paste text from system clipboard into entry/textbox."""
    try:
        w = getattr(widget, '_entry', getattr(widget, '_textbox', widget))

        try:
            clipboard_text = w.clipboard_get()
        except Exception:
            return  # Clipboard empty or non-text data

        if not clipboard_text:
            return

        # Replace newlines for single-line entry fields
        if not isinstance(widget, (tk.Text, ctk.CTkTextbox)):
            clipboard_text = clipboard_text.replace('\r\n', ' ').replace('\n', ' ')

        if hasattr(w, 'selection_present') and w.selection_present():
            try:
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except Exception: pass
            w.insert(tk.INSERT, clipboard_text)
        elif hasattr(w, 'insert'):
            try:
                idx = w.index(tk.INSERT)
                w.insert(idx, clipboard_text)
            except Exception:
                w.insert(tk.END, clipboard_text)
    except Exception:
        pass


def safe_cut(widget):
    """Cut selected text from entry/textbox to system clipboard."""
    try:
        safe_copy(widget)
        w = getattr(widget, '_entry', getattr(widget, '_textbox', widget))

        if hasattr(w, 'selection_present') and w.selection_present():
            try:
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except Exception: pass
    except Exception:
        pass


def safe_select_all(widget):
    """Select all text inside entry/textbox."""
    try:
        w = getattr(widget, '_entry', getattr(widget, '_textbox', widget))

        if hasattr(w, 'select_range'):
            w.select_range(0, tk.END)
            w.icursor(tk.END)
        elif hasattr(w, 'tag_add'):
            w.tag_add(tk.SEL, "1.0", tk.END)
            w.mark_set(tk.INSERT, "1.0")
            w.see(tk.INSERT)
    except Exception:
        pass


def enable_universal_shortcuts(root):
    """Bind Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A globally on the Tk root window."""

    def _on_key_event(event, action_func):
        widget = event.widget
        action_func(widget)

    for key_pattern, action in [
        ("<Control-a>", safe_select_all),
        ("<Control-A>", safe_select_all),
        ("<Control-c>", safe_copy),
        ("<Control-C>", safe_copy),
        ("<Control-v>", safe_paste),
        ("<Control-V>", safe_paste),
        ("<Control-x>", safe_cut),
        ("<Control-X>", safe_cut),
        ("<Command-a>", safe_select_all),
        ("<Command-c>", safe_copy),
        ("<Command-v>", safe_paste),
        ("<Command-x>", safe_cut),
    ]:
        try:
            root.bind_all(key_pattern, lambda e, act=action: _on_key_event(e, act))
        except Exception as ex:
            print(f"[ClipboardHelper] Warning binding {key_pattern}: {ex}")
