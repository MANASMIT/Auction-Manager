# --- auction_UI.py ---
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, scrolledtext, font as tkFont
import os, sys
import re
import csv
import json, pathlib
import requests
from datetime import datetime
import threading
import webbrowser
import time # For shutdown check
import secrets # For generating secure tokens

# Conditional imports for Flask and SocketIO
try:
    from flask import Flask, render_template, jsonify # Already in auction_flask_app
    from flask_socketio import SocketIO, emit # Already in auction_flask_app
    # Import your flask app module
    import auction_flask_app 
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    auction_flask_app = None
    Flask = None # To avoid NameError if auction_flask_app is None
    SocketIO = None
    render_template = None
    jsonify = None
    request = None
    emit = None
    print("="*50)
    print("WARNING: Flask or Flask-SocketIO not installed, or auction_flask_app.py missing.")
    print("Webview features will be unavailable.")
    print("To enable, run: pip install Flask Flask-SocketIO")
    print("="*50)

from auction_engine import (
    AuctionEngine, AuctionError, InsufficientFundsError,
    ItemNotSelectedError, InvalidBidError, NoBidsError,
    LogFileError, InitializationError, generate_template_csv_content,
    PLAYER_PHOTO_PATH_KEY, TEAM_LOGO_PATH_KEY
)

# --- Constants --- (remain the same)
LOG_SECTION_CONFIG = "[CONFIG]"
LOG_SECTION_TEAMS_INITIAL = "[TEAMS_INITIAL]"
LOG_SECTION_PLAYERS_INITIAL = "[PLAYERS_INITIAL]"
LOG_SECTION_AUCTION_STATES = "[AUCTION_STATES]"
LOG_SECTION_BID_INCREMENT_RULES = "[BID_INCREMENT_RULES]"
LOG_KEY_AUCTION_NAME = "AuctionName"
LOG_FILE_EXTENSION = ".auctionlog"
CSV_DELIMITER = ','

# --- UI Styling Constants --- (remain the same)
THEME_BG_PRIMARY = "#1e272e"
THEME_BG_SECONDARY = "#2c3a47"
THEME_BG_CARD = "#28333D"
THEME_TEXT_PRIMARY = "#f1f2f6"
THEME_TEXT_SECONDARY = "#bababa"
THEME_TEXT_ACCENT = "#ffffff"
THEME_ACCENT_PRIMARY = "#00a8ff"
THEME_ACCENT_SECONDARY = "#e67e22"
THEME_ACCENT_TERTIARY = "#2ecc71"
THEME_BORDER_COLOR_LIGHT = "#4a5865"
THEME_HIGHLIGHT_BG = "#3b4a58"
THEME_HIGHLIGHT_FG = THEME_TEXT_PRIMARY # Make sure this is defined
FONT_FAMILY_PRIMARY = "Segoe UI"
FONT_FAMILY_FALLBACK = "Arial"
PRIMARY_BUTTON_BG = THEME_ACCENT_PRIMARY
PRIMARY_BUTTON_FG = THEME_TEXT_ACCENT
SECONDARY_BUTTON_BG = THEME_BG_CARD
SECONDARY_BUTTON_FG = THEME_TEXT_PRIMARY
HOVER_BG_COLOR_PRIMARY = "#007fcc"
HOVER_BG_COLOR_SECONDARY = THEME_HIGHLIGHT_BG

def get_font(size, weight="normal", slant="roman"):
    family_to_try = FONT_FAMILY_PRIMARY
    try:
        font = tkFont.Font(family=family_to_try, size=size, weight=weight, slant=slant)
        if font.actual("family").lower() != family_to_try.lower() and FONT_FAMILY_FALLBACK:
            font = tkFont.Font(family=FONT_FAMILY_FALLBACK, size=size, weight=weight, slant=slant)
        return font
    except tk.TclError:
        return tkFont.Font(family=FONT_FAMILY_FALLBACK, size=size, weight=weight, slant=slant)

def apply_hover_effect(widget, hover_bg, original_bg, hover_fg=None, original_fg_default=None):
    can_set_fg = hasattr(widget, 'cget') and 'fg' in widget.configure()
    original_fg_val = None
    if can_set_fg:
        try: original_fg_val = widget.cget("fg")
        except tk.TclError: can_set_fg = False
    final_original_fg = original_fg_val if original_fg_val is not None else original_fg_default
    final_hover_fg = hover_fg if hover_fg is not None else final_original_fg

    def on_enter(event):
        config_options = {"background": hover_bg}
        if can_set_fg and final_hover_fg is not None: config_options["fg"] = final_hover_fg
        widget.config(**config_options)
    def on_leave(event):
        config_options = {"background": original_bg}
        if can_set_fg and final_original_fg is not None: config_options["fg"] = final_original_fg
        widget.config(**config_options)
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

def get_executable_directory_path():
    """
    Returns the directory where the executable is located,
    or the script's directory if running as a .py file.
    This is suitable for bulding external data files placed alongside the executable.
    """
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        # However, for external files, we want the dir of the .exe itself.
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    return application_path

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class StyledButton(tk.Button):
    def __init__(self, master=None, cnf={}, **kw):
        default_style = {
            "font": get_font(11, "bold"), "relief": tk.FLAT, "pady": 8, "padx": 12,
            "borderwidth": 0, "activebackground": kw.get("bg", SECONDARY_BUTTON_BG),
            "activeforeground": kw.get("fg", SECONDARY_BUTTON_FG)
        }
        final_cnf = {**default_style, **cnf, **kw}
        super().__init__(master, **final_cnf)
        self.original_bg = self.cget("background")
        self.original_fg = self.cget("foreground")
        if self.original_bg == PRIMARY_BUTTON_BG:
            self.hover_bg, self.hover_fg = HOVER_BG_COLOR_PRIMARY, PRIMARY_BUTTON_FG
        elif self.original_bg == THEME_ACCENT_SECONDARY:
            self.hover_bg, self.hover_fg = "#d35400", THEME_TEXT_ACCENT
        elif self.original_bg == THEME_ACCENT_TERTIARY:
            self.hover_bg, self.hover_fg = "#27ae60", THEME_TEXT_ACCENT
        else:
            self.hover_bg, self.hover_fg = HOVER_BG_COLOR_SECONDARY, self.original_fg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e): self.config(background=self.hover_bg, foreground=self.hover_fg)
    def _on_leave(self, e): self.config(background=self.original_bg, foreground=self.original_fg)

class InitialPage(tk.Frame):
    def __init__(self, master, on_new_auction_selected, on_resume_auction_selected):
        super().__init__(master, bg=THEME_BG_PRIMARY)
        container = tk.Frame(self, bg=THEME_BG_PRIMARY, padx=60, pady=60); container.pack(expand=True, fill="both")
        tk.Label(container, text="AUCTION COMMAND", font=get_font(36, "bold"), bg=THEME_BG_PRIMARY, fg=THEME_ACCENT_PRIMARY).pack(pady=(20, 50))
        StyledButton(container, text="START NEW AUCTION", command=on_new_auction_selected, font=get_font(16, "bold"), bg=PRIMARY_BUTTON_BG, fg=PRIMARY_BUTTON_FG, width=28, pady=15).pack(pady=15)
        StyledButton(container, text="RESUME AUCTION", command=on_resume_auction_selected, font=get_font(16, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, width=28, pady=15).pack(pady=15)

class FileSelectPage(tk.Frame):
    def __init__(self, master, on_file_loaded_data, title="CREATE NEW AUCTION"):
        super().__init__(master, bg=THEME_BG_PRIMARY)
        self.on_file_loaded_data = on_file_loaded_data
        container = tk.Frame(self, bg=THEME_BG_PRIMARY, padx=50, pady=30)
        container.pack(expand=True, fill="both")
        tk.Label(container, text=title, font=get_font(28, "bold"), bg=THEME_BG_PRIMARY, fg=THEME_ACCENT_PRIMARY).pack(pady=(0, 40))
        tk.Label(container, text="Auction Name:", font=get_font(14), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_PRIMARY).pack(pady=(10,0), anchor="w")
        self.auction_name_entry = tk.Entry(container, font=get_font(14), width=35, relief=tk.FLAT, bd=2, insertbackground=THEME_TEXT_PRIMARY, bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, highlightthickness=1, highlightbackground=THEME_BORDER_COLOR_LIGHT, highlightcolor=THEME_ACCENT_PRIMARY)
        self.auction_name_entry.insert(0, "MyAuction")
        self.auction_name_entry.pack(pady=5, ipady=8, fill=tk.X)
        csv_info_frame = tk.Frame(container, bg=THEME_BG_PRIMARY)
        csv_info_frame.pack(pady=(20,0), fill=tk.X)
        tk.Label(csv_info_frame, text="Select Initial Setup File (.csv):", font=get_font(14), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_PRIMARY).pack(side=tk.LEFT, anchor="w")
        template_hyperlink_font = get_font(10, slant="italic")
        self.template_link_button = tk.Button(csv_info_frame, text="View .csv format help", font=template_hyperlink_font, fg=THEME_ACCENT_PRIMARY, bg=THEME_BG_PRIMARY, relief=tk.FLAT, bd=0, cursor="hand2", activeforeground=HOVER_BG_COLOR_PRIMARY, activebackground=THEME_BG_PRIMARY, command=self._generate_and_save_template)
        self.template_link_button.pack(side=tk.RIGHT, padx=(10,0), anchor="e")
        default_font_no_underline = get_font(10, slant="italic")
        hover_font_underline_actual = tkFont.Font(family=default_font_no_underline.cget("family"), size=default_font_no_underline.cget("size"), slant=default_font_no_underline.cget("slant"), underline=True)
        def on_link_enter(e): self.template_link_button.config(font=hover_font_underline_actual, fg=HOVER_BG_COLOR_PRIMARY)
        def on_link_leave(e): self.template_link_button.config(font=default_font_no_underline, fg=THEME_ACCENT_PRIMARY)
        self.template_link_button.bind("<Enter>", on_link_enter)
        self.template_link_button.bind("<Leave>", on_link_leave)
        StyledButton(container, text="BROWSE SETUP FILE", command=self.browse_csv_file, font=get_font(12, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, pady=10, padx=15).pack(pady=10, fill=tk.X)
    def _generate_and_save_template(self):
        template_content = generate_template_csv_content()
        filename = "auction_setup_template.csv"
        filepath = os.path.join(os.getcwd(), filename)
        try:
            with open(filepath, "w", newline='', encoding='utf-8') as f: f.write(template_content)
            messagebox.showinfo("Template Generated", f"'{filename}' created in:\n{os.getcwd()}", parent=self)
        except IOError as e: messagebox.showerror("Error Saving Template", f"Could not save '{filename}':\n{e}", parent=self)
        except Exception as e: messagebox.showerror("Unexpected Error", f"Error generating template:\n{e}", parent=self)
    def browse_csv_file(self):
        file_path = filedialog.askopenfilename(title="Select Setup CSV File", filetypes=[("CSV files", "*.csv")])
        if not file_path: return
        teams_list, players_list, bid_increment_rules_list = [], [], []
        parsed_team_header, parsed_player_header = False, False
        current_parsing_section = None; file_line_num_for_error = 0
        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                for file_line_num, row in enumerate(reader, 1):
                    file_line_num_for_error = file_line_num
                    if not any(field.strip() for field in row): continue
                    first_cell_stripped = row[0].strip()
                    if first_cell_stripped.lower() == LOG_SECTION_CONFIG.lower(): current_parsing_section = "CONFIG"; continue
                    elif first_cell_stripped.lower() == LOG_SECTION_TEAMS_INITIAL.lower(): current_parsing_section = "TEAMS"; parsed_team_header = False; continue
                    elif first_cell_stripped.lower() == LOG_SECTION_PLAYERS_INITIAL.lower(): current_parsing_section = "PLAYERS"; parsed_player_header = False; continue
                    elif first_cell_stripped.lower() == LOG_SECTION_BID_INCREMENT_RULES.lower(): current_parsing_section = "BID_RULES"; continue
                    if current_parsing_section == "CONFIG":
                        if first_cell_stripped.startswith('#'): continue
                        if CSV_DELIMITER in first_cell_stripped:
                             key_value_pair = first_cell_stripped.split(CSV_DELIMITER, 1)
                             if len(key_value_pair) == 2:
                                key, value = key_value_pair[0].strip(), key_value_pair[1].strip()
                                if key == LOG_KEY_AUCTION_NAME: self.auction_name_entry.delete(0, tk.END); self.auction_name_entry.insert(0, value)
                    elif current_parsing_section == "TEAMS":
                        if not parsed_team_header:
                            if first_cell_stripped.startswith('#'): continue
                            row_headers_lower = [h.strip().lower() for h in row]
                            if not (len(row_headers_lower) >= 2 and row_headers_lower[0] == "team name" and row_headers_lower[1] == "team starting money"):
                                messagebox.showerror("Format Error", f"Invalid team header (L{file_line_num}). Expected 'Team name,Team starting money[,{TEAM_LOGO_PATH_KEY}]'. Got: {', '.join(row)}"); return
                            parsed_team_header = True; continue
                        if first_cell_stripped.startswith('#'): continue
                        if len(row) >= 2:
                            name, money_str = row[0].strip(), row[1].strip()
                            logo_path = row[2].strip() if len(row) >= 3 and row[2].strip() else None
                            if not name: messagebox.showerror("Data Error", f"Team name empty (L{file_line_num})."); return
                            try: teams_list.append({"Team name": name, "Team starting money": int(money_str), TEAM_LOGO_PATH_KEY: logo_path})
                            except ValueError: messagebox.showerror("Data Error", f"Invalid money for '{name}' (L{file_line_num}): '{money_str}'."); return
                        else: messagebox.showerror("Format Error", f"Malformed team data (L{file_line_num})."); return
                    elif current_parsing_section == "PLAYERS":
                        if not parsed_player_header:
                            if first_cell_stripped.startswith('#'): continue
                            row_headers_lower = [h.strip().lower() for h in row]
                            if not (len(row_headers_lower) >= 2 and row_headers_lower[0] == "player name" and row_headers_lower[1] == "bid value"):
                                messagebox.showerror("Format Error", f"Invalid player header (L{file_line_num}). Expected 'Player name,Bid value[,{PLAYER_PHOTO_PATH_KEY}]'. Got: {', '.join(row)}"); return
                            parsed_player_header = True; continue
                        if first_cell_stripped.startswith('#'): continue
                        if len(row) >= 2:
                            name, bid_str = row[0].strip(), row[1].strip()
                            photo_path = row[2].strip() if len(row) >= 3 and row[2].strip() else None
                            if not name: messagebox.showerror("Data Error", f"Player name empty (L{file_line_num})."); return
                            try: players_list.append({"Player name": name, "Bid value": int(bid_str), PLAYER_PHOTO_PATH_KEY: photo_path})
                            except ValueError: messagebox.showerror("Data Error", f"Invalid bid for '{name}' (L{file_line_num}): '{bid_str}'."); return
                        else: messagebox.showerror("Format Error", f"Malformed player data (L{file_line_num})."); return
                    elif current_parsing_section == "BID_RULES":
                        if first_cell_stripped.startswith('#'): continue
                        if len(row) >= 2 and first_cell_stripped.lower() == "threshold" and row[1].strip().lower() == "increment": continue
                        try:
                            if len(row) >= 2:
                                threshold_str, increment_str = row[0].strip(), row[1].strip()
                                if not threshold_str and not increment_str: continue
                                threshold, increment = int(threshold_str), int(increment_str)
                                if threshold < 0 or increment <= 0: messagebox.showerror("Data Error", f"Bid Rule Error (L{file_line_num}): Thr>=0, Inc>0. Got: {threshold}, {increment}"); return
                                bid_increment_rules_list.append((threshold, increment))
                            elif any(field.strip() for field in row): messagebox.showerror("Format Error", f"Malformed bid rule (L{file_line_num})."); return
                        except ValueError: messagebox.showerror("Data Error", f"Invalid num in bid rule (L{file_line_num}): '{row[0].strip()}', '{row[1].strip()}'."); return
            if not teams_list: messagebox.showerror("Data Error", "No team data parsed."); return
            if not players_list: messagebox.showerror("Data Error", "No player data parsed."); return
            auction_name_input = self.auction_name_entry.get().strip()
            if not auction_name_input: messagebox.showerror("Input Error", "Auction Name empty."); return
            self.on_file_loaded_data(teams_list, players_list, auction_name_input, bid_increment_rules_list if bid_increment_rules_list else None)
        except FileNotFoundError: messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e: messagebox.showerror("CSV Loading Error", f"Error parsing CSV (L{file_line_num_for_error}):\n{type(e).__name__}: {e}")

class FileSelectPageForResume(FileSelectPage):
    def __init__(self, master, on_log_file_selected_for_resume):
        super().__init__(master, on_file_loaded_data=None, title="RESUME AUCTION")
        self.on_log_file_selected_for_resume = on_log_file_selected_for_resume
        container_frame = self.winfo_children()[0] # This gets the main container Frame
        # Iterate over a copy of children list for safe deletion
        for widget in list(container_frame.winfo_children()):
            if isinstance(widget, tk.Entry) and widget == self.auction_name_entry: # Explicitly remove auction name entry
                widget.destroy()
            elif isinstance(widget, tk.Frame): # This is for the csv_info_frame
                 # Check if it contains the specific label or button to identify it
                is_csv_info_frame = False
                for sub_widget in widget.winfo_children():
                    if hasattr(sub_widget, 'cget') and 'text' in sub_widget.configure():
                        text = sub_widget.cget("text")
                        if "Select Initial Setup File (.csv):" in text or "View .csv format help" in text:
                            is_csv_info_frame = True
                            break
                if is_csv_info_frame:
                    widget.destroy() # Destroy the whole csv_info_frame
            elif isinstance(widget, StyledButton) and "BROWSE SETUP FILE" in widget.cget("text"): # Remove browse CSV button
                widget.destroy()
            elif isinstance(widget, tk.Label) and "Auction Name:" in widget.cget("text"): # Remove auction name label
                widget.destroy()

        tk.Label(container_frame, text=f"Select Auction Log File (*{LOG_FILE_EXTENSION}):", font=get_font(14), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_PRIMARY).pack(pady=(20,0), anchor="w")
        StyledButton(container_frame, text=f"BROWSE LOG FILE", command=self.browse_log_file, font=get_font(12, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, pady=10, padx=15).pack(pady=10, fill=tk.X)
        self.file_label = tk.Label(container_frame, text="No log file selected.", font=get_font(10), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_SECONDARY); self.file_label.pack(pady=5)
    def browse_log_file(self):
        file_path = filedialog.askopenfilename(title="Select Auction Log", filetypes=[(f"Log Files", f"*{LOG_FILE_EXTENSION}"), ("All", "*.*")])
        if file_path:
            self.file_label.config(text=os.path.basename(file_path), fg=THEME_TEXT_PRIMARY)
            try:
                with open(file_path, 'r', encoding='utf-8') as f: f.readline()
                self.on_log_file_selected_for_resume(file_path)
            except Exception as e: messagebox.showerror("Error", f"Cannot read file: {e}"); self.file_label.config(text="Error: Invalid log", fg=THEME_ACCENT_SECONDARY)

class LogViewerDialog(tk.Toplevel):
    def __init__(self, master, log_filepath, load_state_callback):
        super().__init__(master)
        self.log_filepath = log_filepath; self.load_state_callback = load_state_callback
        self.title("Auction Log History Viewer"); self.geometry("1200x750"); self.configure(bg=THEME_BG_PRIMARY); self.grab_set(); self.focus_set()
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("Treeview", background=THEME_BG_SECONDARY, foreground=THEME_TEXT_PRIMARY, fieldbackground=THEME_BG_SECONDARY, font=get_font(10), rowheight=get_font(10).metrics('linespace') + 6, borderwidth=0, relief=tk.FLAT)
        style.configure("Treeview.Heading", font=get_font(11, "bold"), background=THEME_BG_CARD, foreground=THEME_ACCENT_PRIMARY, relief=tk.FLAT, borderwidth=0)
        style.map("Treeview.Heading", background=[('active', THEME_HIGHLIGHT_BG)])
        style.map("Treeview", background=[('selected', THEME_ACCENT_PRIMARY)], foreground=[('selected', THEME_TEXT_ACCENT)])
        style.configure("Vertical.TScrollbar", gripcount=0, background=THEME_BG_CARD, troughcolor=THEME_BG_PRIMARY, bordercolor=THEME_BG_PRIMARY, arrowcolor=THEME_TEXT_PRIMARY, relief=tk.FLAT, arrowsize=15, width=16)
        style.map("Vertical.TScrollbar", background=[('active', THEME_HIGHLIGHT_BG)], arrowcolor=[('pressed', THEME_ACCENT_PRIMARY)])
        style.configure("Horizontal.TScrollbar", gripcount=0, background=THEME_BG_CARD, troughcolor=THEME_BG_PRIMARY, bordercolor=THEME_BG_PRIMARY, arrowcolor=THEME_TEXT_PRIMARY, relief=tk.FLAT, arrowsize=15, height=16)
        style.map("Horizontal.TScrollbar", background=[('active', THEME_HIGHLIGHT_BG)], arrowcolor=[('pressed', THEME_ACCENT_PRIMARY)])
        top_controls_frame = tk.Frame(self, bg=THEME_BG_PRIMARY); top_controls_frame.pack(pady=(10,0), padx=10, fill="x")
        StyledButton(top_controls_frame, text="🔄 REFRESH", command=self.populate_log_tree, font=get_font(10, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, padx=10, pady=5).pack(side="left", padx=(0,10))
        self.load_button = StyledButton(top_controls_frame, text="✔️ LOAD SELECTED STATE", command=self.on_load_selected_state, font=get_font(10, "bold"), bg=PRIMARY_BUTTON_BG, fg=PRIMARY_BUTTON_FG, padx=10, pady=5, state=tk.DISABLED); self.load_button.pack(side="left")
        StyledButton(top_controls_frame, text="✖ CLOSE", command=self.destroy, font=get_font(10, "bold"), bg=THEME_ACCENT_SECONDARY, fg=THEME_TEXT_ACCENT, padx=10, pady=5).pack(side="right")
        tree_frame = tk.Frame(self, bg=THEME_BG_PRIMARY); tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
        cols = ("No.", "Timestamp", "Action Description", "Comment"); self.log_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col_name in cols: self.log_tree.heading(col_name, text=col_name)
        self.log_tree.column("No.", width=60, minwidth=50, stretch=tk.NO, anchor="center"); self.log_tree.column("Timestamp", width=180, minwidth=160, anchor="w")
        self.log_tree.column("Action Description", width=380, minwidth=250, anchor="w"); self.log_tree.column("Comment", width=300, minwidth=200, anchor="w")
        tree_ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_tree.yview, style="Vertical.TScrollbar")
        tree_xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.log_tree.xview, style="Horizontal.TScrollbar")
        self.log_tree.configure(yscrollcommand=tree_ysb.set, xscrollcommand=tree_xsb.set)
        tree_ysb.pack(side="right", fill="y"); tree_xsb.pack(side="bottom", fill="x"); self.log_tree.pack(side="left", fill="both", expand=True)
        self.log_tree.bind("<<TreeviewSelect>>", self.on_log_entry_select); self.log_data_store = []
        self.json_control_frame = tk.Frame(self, bg=THEME_BG_PRIMARY); self.json_control_frame.pack(pady=(5,0), padx=10, fill="x")
        self.toggle_json_button = StyledButton(self.json_control_frame, text="Show JSON Details ►", command=self._toggle_json_display, font=get_font(10, "bold"), bg=SECONDARY_BUTTON_BG, fg=THEME_TEXT_PRIMARY, padx=10, pady=5); self.toggle_json_button.pack(side="left")
        self.json_visible = False
        self.json_display_frame = tk.Frame(self, bg=THEME_BG_SECONDARY, bd=0, relief=tk.FLAT)
        tk.Label(self.json_display_frame, text="SELECTED STATE SNAPSHOT (JSON):", font=get_font(11, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY).pack(anchor="nw", padx=10, pady=(10,5))
        self.json_text = scrolledtext.ScrolledText(self.json_display_frame, height=10, font=get_font(10), wrap=tk.WORD, relief=tk.FLAT, bd=0, insertbackground=THEME_TEXT_PRIMARY, bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, highlightthickness=0); self.json_text.pack(fill="both", expand=True, padx=10, pady=(0,10)); self.json_text.configure(state=tk.DISABLED)
        self.populate_log_tree()
    def _toggle_json_display(self):
        if self.json_visible: self.json_display_frame.pack_forget(); self.toggle_json_button.config(text="Show JSON Details ►"); self.json_visible = False
        else: self.json_display_frame.pack(pady=(0,10), padx=10, fill="both", expand=True); self.toggle_json_button.config(text="Hide JSON Details ▼"); self.json_visible = True
    def populate_log_tree(self):
        for i in self.log_tree.get_children(): self.log_tree.delete(i)
        self.log_data_store.clear(); self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED)
        if self.json_visible: self.json_display_frame.pack_forget(); self.toggle_json_button.config(text="Show JSON Details ►"); self.json_visible = False
        serial_no_counter = 1
        try:
            if not os.path.exists(self.log_filepath): messagebox.showerror("Log Error", f"Not found: {self.log_filepath}", parent=self); return
            with open(self.log_filepath, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f); in_states_section = False
                for row_num, row in enumerate(reader):
                    if not row: continue
                    try: first_cell = row[0].strip()
                    except IndexError: continue
                    if first_cell == LOG_SECTION_AUCTION_STATES: in_states_section = True; next(reader, None); continue
                    if in_states_section and not first_cell.startswith('#'):
                        if len(row) >= 3:
                            timestamp, action_desc, json_str = row[0], row[1], row[2]; comment = row[3] if len(row) > 3 else ""
                            iid_val = str(serial_no_counter)
                            self.log_tree.insert("", "end", values=(serial_no_counter, timestamp, action_desc, comment), iid=iid_val)
                            self.log_data_store.append({'iid': iid_val, 'serial_no': serial_no_counter, 'ts': timestamp, 'action': action_desc, 'json': json_str, 'comment': comment})
                            serial_no_counter += 1
        except Exception as e: messagebox.showerror("Log Error", f"Reading log: {e}", parent=self)
    def on_log_entry_select(self, event):
        selected_item_iid = self.log_tree.focus()
        if not selected_item_iid: self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); return
        selected_data = next((item for item in self.log_data_store if item['iid'] == selected_item_iid), None)
        if selected_data:
            try:
                parsed_json = json.loads(selected_data['json']); pretty_json = json.dumps(parsed_json, indent=2)
                self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.insert("1.0", pretty_json); self.json_text.config(state=tk.DISABLED); self.load_button.config(state=tk.NORMAL)
            except json.JSONDecodeError: self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.insert("1.0", "Error: Invalid JSON."); self.json_text.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED)
        else: self.load_button.config(state=tk.DISABLED)
    def on_load_selected_state(self):
        selected_item_iid = self.log_tree.focus()
        if not selected_item_iid: messagebox.showwarning("No Selection", "Select log entry.", parent=self); return
        selected_data = next((item for item in self.log_data_store if item['iid'] == selected_item_iid), None)
        if selected_data and messagebox.askyesno("Confirm Load", f"Load state from No. {selected_data['serial_no']}?", parent=self, icon='warning'):
            self.load_state_callback(selected_data['json'], selected_data['ts'], selected_data['action'], selected_data['serial_no']); self.destroy()

class TopMenuBar(tk.Frame):
    def __init__(self, master, app_controller, **kwargs):
        super().__init__(master, bg=THEME_BG_CARD, **kwargs)
        self.app_controller = app_controller
        self.visible = False
        self.menu_items_frame = None

        self.toggle_button = StyledButton(self, text="▼ Menu",
                                          command=self.toggle_menu_visibility,
                                          font=get_font(9), padx=8, pady=4,
                                          bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY)
        self.toggle_button.pack(side=tk.LEFT, anchor="nw", padx=5, pady=2)

        if hasattr(master, 'master') and master.master is not None:
            master.master.bind_all("<Alt_L>", lambda e: self.toggle_menu_visibility())
            master.master.bind_all("<Alt_R>", lambda e: self.toggle_menu_visibility())
        else:
            master.bind_all("<Alt_L>", lambda e: self.toggle_menu_visibility())
            master.bind_all("<Alt_R>", lambda e: self.toggle_menu_visibility())

        self._create_menu_items()
        self.manager_links_window = None # To hold the manager links Toplevel window

    def _create_menu_items(self):
        self.menu_items_frame = tk.Frame(self, bg=THEME_BG_CARD)

        file_label = tk.Label(self.menu_items_frame, text="File", font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, padx=10)
        file_label.pack(side=tk.LEFT)
        exit_btn = StyledButton(self.menu_items_frame, text="Exit", command=self.app_controller.master.destroy, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        exit_btn.pack(side=tk.LEFT, padx=2)

        view_label = tk.Label(self.menu_items_frame, text="View", font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, padx=10)
        view_label.pack(side=tk.LEFT, padx=(10,0))

        # Presenter Toggle
        self.presenter_toggle_btn_text = tk.StringVar(value="Start Presenter Webview")
        presenter_btn = StyledButton(self.menu_items_frame, textvariable=self.presenter_toggle_btn_text,
                                     command=self.app_controller._handle_presenter_webview_toggle,
                                     font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        presenter_btn.pack(side=tk.LEFT, padx=2)

        # Manager Toggle & Links Button
        self.manager_toggle_btn_text = tk.StringVar(value="Enable Manager Access") # Text for main toggle
        manager_main_btn = StyledButton(self.menu_items_frame, textvariable=self.manager_toggle_btn_text,
                                     command=self.app_controller._handle_manager_access_toggle, # New method in AuctionApp
                                     font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        manager_main_btn.pack(side=tk.LEFT, padx=2)

        manager_show_links_btn = StyledButton(self.menu_items_frame, text="Show Manager Links",
                                     command=self.app_controller._show_manager_links_window, # New method in AuctionApp
                                     font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        manager_show_links_btn.pack(side=tk.LEFT, padx=2)


        logs_btn = StyledButton(self.menu_items_frame, text="Show Logs", command=self.app_controller._open_log_viewer, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        logs_btn.pack(side=tk.LEFT, padx=2)

        help_btn = StyledButton(self.menu_items_frame, text="Help", 
                                  command=self.app_controller._show_documentation, # New method in AuctionApp
                                  font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        help_btn.pack(side=tk.LEFT, padx=2)
        about_btn = StyledButton(self.menu_items_frame, text="About", command=self._show_about, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        about_btn.pack(side=tk.LEFT, padx=2)

    def toggle_menu_visibility(self, event=None):
        if self.visible:
            self.menu_items_frame.pack_forget()
            self.toggle_button.config(text="▼ Menu")
            self.visible = False
        else:
            self.menu_items_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.toggle_button.config(text="▲ Hide Menu")
            self.visible = True

    def _show_about(self):
        messagebox.showinfo("About Auction Command",
                            "Auction Command v1.2\n\nA Simple Auction Management Tool.",
                            parent=self.app_controller)

    # Method to potentially update links if the window is open and tokens change (e.g., server restart)
    def update_manager_links_display(self, team_access_links):
        if self.manager_links_window and self.manager_links_window.winfo_exists():
            self.manager_links_window.update_links(team_access_links)

    def manager_links_window_closed(self): # <--- ADD THIS METHOD HERE
        # This method is called by ManagerLinksWindow when its 'close' button is pressed.
        # It signifies that the window is hidden, not destroyed.
        # AuctionApp._show_manager_links_window will handle showing it again.
        # We don't need to do much here other than acknowledge it,
        # or potentially update a state variable if TopMenuBar itself needed to know.
        # For now, just having it prevents the AttributeError.
        # print("TopMenuBar: ManagerLinksWindow reported closed (hidden).")
        pass

class ManagerLinksWindow(tk.Toplevel):
    def __init__(self, master, team_access_links, base_url):
        super().__init__(master)
        self.title("Team Manager Access Links")
        self.geometry("650x450") # Slightly wider for full links
        self.configure(bg=THEME_BG_PRIMARY)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.app_controller = master

        self.base_url = base_url
        self.main_frame = tk.Frame(self, bg=THEME_BG_PRIMARY, padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.main_frame, text="Copy these links and provide them to the respective team managers.",
                 font=get_font(10), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_PRIMARY, wraplength=630).pack(pady=(0,10), fill=tk.X)

        canvas_frame = tk.Frame(self.main_frame, bg=THEME_BG_SECONDARY) # Frame to hold canvas and scrollbar
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.links_canvas = tk.Canvas(canvas_frame, bg=THEME_BG_SECONDARY, highlightthickness=0)
        self.links_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.links_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.links_canvas.configure(yscrollcommand=scrollbar.set)

        self.scrollable_frame = tk.Frame(self.links_canvas, bg=THEME_BG_SECONDARY)
        self.canvas_window_id = self.links_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        # Bind to the canvas's <Configure> event to adjust the width of the frame inside the canvas
        self.links_canvas.bind("<Configure>", self._on_canvas_configure) 
        
        self.link_widgets = {}
        self.update_links(team_access_links)

    def _on_frame_configure(self, event=None):
        # Update scrollregion whenever the scrollable_frame's size changes
        self.links_canvas.configure(scrollregion=self.links_canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        # Adjust the width of the scrollable_frame to match the canvas width
        self.links_canvas.itemconfig(self.canvas_window_id, width=event.width)

    def _copy_to_clipboard(self, text_to_copy):
        try:
            self.clipboard_clear()  # Clear the clipboard first
            self.clipboard_append(text_to_copy)  # Append the new text
            self.update_idletasks() # Optional: ensures the clipboard is updated immediately on some systems
            messagebox.showinfo("Copied", f"Link copied to clipboard:\n{text_to_copy}", parent=self)
        except tk.TclError as e: # Catch Tkinter-specific errors
            # This error can happen if a clipboard manager isn't available (e.g., on some minimal Linux setups)
            messagebox.showerror("Clipboard Error", 
                                 f"Could not copy to clipboard using Tkinter: {e}\n"
                                 "Ensure a clipboard manager (like xclip or xsel on Linux) is running, "
                                 "or try installing the 'pyperclip' library as an alternative.", 
                                 parent=self)
            print(f"Tkinter clipboard error: {e}")
        except Exception as e: # Catch any other unexpected errors
            messagebox.showerror("Copy Error", f"An unexpected error occurred while copying: {e}", parent=self)
            print(f"Unexpected clipboard copy error: {e}")


    def update_links(self, team_access_links):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.link_widgets.clear()

        if not team_access_links:
            tk.Label(self.scrollable_frame, text="Manager access is currently disabled or no teams loaded.",
                     font=get_font(12), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_SECONDARY).pack(pady=20, padx=10)
        else:
            for team_name, token in sorted(team_access_links.items()):
                link = f"{self.base_url}/manager/{team_name}/{token}"
                
                row_frame = tk.Frame(self.scrollable_frame, bg=THEME_BG_CARD, padx=5, pady=5)
                # Make row_frame fill width of scrollable_frame
                row_frame.pack(fill=tk.X, pady=3, padx=5) 

                tk.Label(row_frame, text=f"{team_name}:", font=get_font(11, "bold"), 
                         bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, width=15, anchor="w").pack(side=tk.LEFT, padx=(0,5))
                
                link_entry = tk.Entry(row_frame, font=get_font(10), relief=tk.FLAT, 
                                      bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY)
                link_entry.insert(0, link)
                link_entry.config(state='readonly') # Corrected state
                link_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
                
                copy_btn = StyledButton(row_frame, text="Copy", font=get_font(9), 
                                        command=lambda l=link: self._copy_to_clipboard(l),
                                        bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, padx=8, pady=2)
                copy_btn.pack(side=tk.LEFT, padx=5)
                self.link_widgets[team_name] = {'frame': row_frame, 'entry': link_entry, 'button': copy_btn}
        
        # Crucial: After populating, update idletasks so bbox is correct, then configure scrollregion
        self.scrollable_frame.update_idletasks() 
        self.links_canvas.config(scrollregion=self.links_canvas.bbox("all"))

    def _on_close(self):
        self.withdraw()
        if self.app_controller and hasattr(self.app_controller, 'menu_bar') and self.app_controller.menu_bar:
            self.app_controller.menu_bar.manager_links_window_closed()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_set()

class AuctionApp(tk.Frame):
    def __init__(self, master, auction_engine_instance):
        super().__init__(master, bg=THEME_BG_PRIMARY)
        self.pack(fill="both", expand=True)
        self.engine = auction_engine_instance
        self.team_card_frames = {}
        self.money_labels = {}
        self.inventory_listboxes = {}

        # Flask-SocketIO related attributes
        self.flask_app_instance = None # Will hold the Flask app object
        self.socketio_instance = None  # Will hold the SocketIO object from Flask app
        self.flask_thread = None
        self.flask_server_running = False
        self.flask_port = 5000 # Or make configurable
        self.stop_flask_event = threading.Event()
        
        self.presenter_active = False # New state for presenter view
        self.manager_access_enabled = False # New state for manager view
        self.team_manager_access_tokens = {} # {team_name: token}
        self.manager_links_window_instance = None
        self.shutdown_overlay = None # For the "Please Wait" overlay
        self.shutdown_status_var = tk.StringVar() # For updating overlay message
        
        
        self._setup_ui()
        self.refresh_all_ui_displays() # Initial display update

    def _setup_ui(self):
        self.menu_bar = TopMenuBar(self, app_controller=self)
        self.menu_bar.pack(fill=tk.X, side=tk.TOP)
        app_content_frame = tk.Frame(self, bg=THEME_BG_PRIMARY)
        app_content_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        header_frame = tk.Frame(app_content_frame, bg=THEME_BG_SECONDARY, padx=15, pady=10)
        header_frame.pack(fill=tk.X, pady=(0,10), side=tk.TOP)
        header_left = tk.Frame(header_frame, bg=THEME_BG_SECONDARY)
        header_left.pack(side=tk.LEFT)
        self.auction_name_label = tk.Label(header_left, text=self.engine.get_auction_name().upper(), font=get_font(18, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY)
        self.auction_name_label.pack(side=tk.LEFT, padx=(0,20))
        header_right = tk.Frame(header_frame, bg=THEME_BG_SECONDARY)
        header_right.pack(side=tk.RIGHT)
        tk.Label(header_right, text="STATUS:", font=get_font(10, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_SECONDARY).pack(side=tk.LEFT)
        self.bid_status_label = tk.Label(header_right, text="INITIALIZING", font=get_font(14, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_SECONDARY, anchor="e")
        self.bid_status_label.pack(side=tk.LEFT, padx=5)
        self.current_item_display_frame = tk.Frame(header_frame, bg=THEME_BG_SECONDARY)
        self.current_item_display_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10,10))
        self.current_item_display_frame.columnconfigure(0, weight=1)
        tk.Label(self.current_item_display_frame, text="CURRENT ITEM:", font=get_font(10, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_SECONDARY, anchor="sw").grid(row=0, column=0, sticky="sw")
        self.current_item_label = tk.Label(self.current_item_display_frame, text="-- NONE --", font=get_font(14, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, anchor="nw")
        self.current_item_label.grid(row=1, column=0, sticky="new") # Corrected sticky
        main_content_below_header = tk.Frame(app_content_frame, bg=THEME_BG_PRIMARY)
        main_content_below_header.pack(fill="both", expand=True, side=tk.TOP)
        main_content_below_header.grid_columnconfigure(0, weight=80); main_content_below_header.grid_columnconfigure(1, weight=20); main_content_below_header.grid_rowconfigure(0, weight=1)
        teams_outer_frame = tk.Frame(main_content_below_header, bg=THEME_BG_SECONDARY, bd=0, relief=tk.FLAT)
        teams_outer_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5)); teams_outer_frame.rowconfigure(1, weight=1); teams_outer_frame.columnconfigure(0, weight=1)
        tk.Label(teams_outer_frame, text="🏆 TEAMS OVERVIEW", font=get_font(16, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY, pady=10, padx=10, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        self.teams_canvas = tk.Canvas(teams_outer_frame, bg=THEME_BG_SECONDARY, highlightthickness=0)
        self.teams_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        teams_scrollbar_style = ttk.Style(self); teams_scrollbar_style.layout("Teams.Vertical.TScrollbar", [('Teams.Vertical.TScrollbar.trough', {'sticky': 'ns'}), ('Vertical.Scrollbar.uparrow', {'side': 'top', 'sticky': ''}), ('Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': ''}), ('Vertical.Scrollbar.thumb', {'sticky': 'ns', 'expand': 1})])
        teams_scrollbar_style.configure("Teams.Vertical.TScrollbar", gripcount=0, background=THEME_BG_CARD, troughcolor=THEME_BG_SECONDARY, bordercolor=THEME_BG_SECONDARY, arrowcolor=THEME_TEXT_PRIMARY, arrowsize=14, relief=tk.FLAT, width=16)
        teams_scrollbar_style.map("Teams.Vertical.TScrollbar", background=[('active', THEME_HIGHLIGHT_BG), ('!active', THEME_BG_CARD)], arrowcolor=[('pressed', THEME_ACCENT_PRIMARY), ('!pressed', THEME_TEXT_PRIMARY)])
        teams_scrollbar = ttk.Scrollbar(teams_outer_frame, orient="vertical", command=self.teams_canvas.yview, style="Teams.Vertical.TScrollbar")
        teams_scrollbar.grid(row=1, column=1, sticky="ns"); self.teams_canvas.configure(yscrollcommand=teams_scrollbar.set)
        self.scrollable_teams_frame = tk.Frame(self.teams_canvas, bg=THEME_BG_SECONDARY)
        self.teams_canvas_window_id = self.teams_canvas.create_window((0,0), window=self.scrollable_teams_frame, anchor="nw")
        self.scrollable_teams_frame.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind_all("<MouseWheel>", self._on_mousewheel_teams); self.teams_canvas.bind_all("<Button-4>", self._on_mousewheel_teams); self.teams_canvas.bind_all("<Button-5>", self._on_mousewheel_teams)
        self._create_team_cards_layout()
        right_pane = tk.Frame(main_content_below_header, bg=THEME_BG_PRIMARY); right_pane.grid(row=0, column=1, sticky="nsew", padx=(5,0)); right_pane.grid_rowconfigure(0, weight=1); right_pane.grid_rowconfigure(1, weight=0); right_pane.grid_columnconfigure(0, weight=1)
        player_list_frame = tk.Frame(right_pane, bg=THEME_BG_SECONDARY, bd=0); player_list_frame.grid(row=0, column=0, sticky="nsew", pady=(0,10)); player_list_frame.rowconfigure(1, weight=1); player_list_frame.columnconfigure(0, weight=1)
        tk.Label(player_list_frame, text="👤 AVAILABLE PLAYERS", font=get_font(16,"bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY, pady=10, padx=10, anchor="w").grid(row=0, column=0, sticky="ew")
        self.item_list_text = scrolledtext.ScrolledText(player_list_frame, width=40, font=get_font(10), wrap=tk.WORD, relief=tk.FLAT, bd=0, bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, highlightthickness=0, insertbackground=THEME_TEXT_PRIMARY); self.item_list_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10)); self.item_list_text.configure(state=tk.DISABLED)
        controls_frame = tk.Frame(right_pane, bg=THEME_BG_SECONDARY, bd=0, padx=15, pady=15); controls_frame.grid(row=1, column=0, sticky="ew"); controls_frame.columnconfigure(0, weight=1)
        tk.Label(controls_frame, text="⚡ AUCTION CONTROLS", font=get_font(16,"bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY, anchor="w").pack(fill=tk.X, pady=(0,15))
        btn_font = get_font(12, "bold"); btn_pady_controls = 12
        StyledButton(controls_frame, text="✔️ SELL ITEM", command=self.ui_sell_item,font=btn_font, bg=THEME_ACCENT_TERTIARY,fg=THEME_TEXT_ACCENT,pady=btn_pady_controls).pack(fill=tk.X, pady=6)
        StyledButton(controls_frame, text="➡️ PASS ITEM", command=self.ui_pass_item,font=btn_font, bg=THEME_ACCENT_SECONDARY,fg=THEME_TEXT_ACCENT,pady=btn_pady_controls).pack(fill=tk.X, pady=6)
        StyledButton(controls_frame, text="⏪ UNDO LAST BID", command=self.ui_undo_last_bid,font=btn_font, bg=THEME_BG_CARD,fg=THEME_TEXT_PRIMARY,pady=btn_pady_controls).pack(fill=tk.X, pady=6)

    def _configure_canvas_scrollregion(self, event, canvas, window_id):
        canvas.configure(scrollregion=canvas.bbox("all"))
        if hasattr(event, 'width'): canvas.itemconfig(window_id, width=event.width)

    def _open_log_viewer(self):
        log_filepath = self.engine.get_log_filepath()
        if not log_filepath or not os.path.exists(log_filepath): messagebox.showinfo("No Log", "Log not found.", parent=self); return
        LogViewerDialog(self, log_filepath, self._handle_load_selected_state_from_history)

    def _start_flask_server(self):
        if not FLASK_AVAILABLE or not auction_flask_app:
            messagebox.showerror("Webview Error", "Flask/SocketIO components not available. Cannot start webview.", parent=self)
            return False

        if self.flask_server_running:
            messagebox.showinfo("Webview Info", "Webview server is already running.", parent=self)
            return True

        try:
            # Pass the AuctionApp instance (self) to the Flask app creation function
            # This allows Flask routes/SocketIO handlers to access auction data/methods
            self.flask_app_instance, self.socketio_instance = auction_flask_app.create_flask_app(self)
            
            self.stop_flask_event.clear()

            def run_server():
                try:
                    print(f"Attempting to start Flask-SocketIO server on http://localhost:{self.flask_port}")
                    # use_reloader=False is important when running in a thread managed by another app
                    self.socketio_instance.run(self.flask_app_instance, host='0.0.0.0', port=self.flask_port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
                    print("Flask-SocketIO server has stopped.")
                except Exception as e:
                    print(f"Flask server thread error: {e}")
                    # Ensure UI reflects that server stopped if it crashes
                    if self.flask_server_running: # if it was marked as running
                        self.master.after(0, self._notify_server_stopped_unexpectedly)


            self.flask_thread = threading.Thread(target=run_server, daemon=True)
            self.flask_thread.start()
            
            # Give the server a moment to start before declaring it running
            # This is a bit of a guess; a better way is to have the server signal back.
            time.sleep(1) # Adjust as needed

            # Basic check if thread is alive (doesn't guarantee server is listening yet)
            if self.flask_thread.is_alive():
                self.flask_server_running = True
                self._emit_full_state_to_webview() # Send initial state
                return True
            else:
                # This happens when the port is used by some other app / simply try restarting the UI!
                messagebox.showerror("Webview Error", "Flask server thread failed to start.", parent=self)
                self.flask_server_running = False
                return False

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Webview Error", f"Failed to initialize Flask server: {e}", parent=self)
            self.flask_server_running = False
            return False

    def _notify_server_stopped_unexpectedly(self):
        if self.flask_server_running : # Check if it was supposed to be running
            messagebox.showwarning("Webview Warning", "The webview server seems to have stopped unexpectedly.", parent=self)
            self.flask_server_running = False
            if hasattr(self, 'menu_bar'):
                 self.menu_bar.presenter_toggle_btn_text.set("Start Presenter Webview")
            self.socketio_instance = None # Clear instance

    def _handle_load_selected_state_from_history(self, json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no):
        success, message = self.engine.load_state_from_json_string(json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no)
        if success:
            self.refresh_all_ui_displays() # This will also call _emit_full_state_to_webview
            self.full_reload_all_content() # Ensure all content is reloaded
            messagebox.showinfo("State Loaded", message, parent=self)
        else:
            messagebox.showerror("Load Error", message, parent=self)
        self._check_and_display_engine_warnings("Warning during state load from history:")

    def _start_flask_server_if_needed(self):
        """Starts the Flask server if it's not running and any web feature is active."""
        if not FLASK_AVAILABLE: return False
        if self.flask_server_running: return True # Already running

        if self.presenter_active or self.manager_access_enabled:
            print("Starting Flask server as a web feature is active.")
            return self._start_flask_server() # Your existing start server method
        return False # No need to start

    def _stop_flask_server_if_idle(self):
        """Stops the Flask server if it's running and no web features are active."""
        if not self.flask_server_running: return False
        
        if not self.presenter_active and not self.manager_access_enabled:
            print("Stopping Flask server as no web features are active.")
            return self._stop_flask_server() # Your existing stop server method
        return False # Still needed

    def _handle_presenter_webview_toggle(self):
        if not FLASK_AVAILABLE:
            messagebox.showerror("Feature Unavailable", "Flask/SocketIO not available.", parent=self)
            return

        if not self.presenter_active: # Trying to START presenter
            self.presenter_active = True
            # Attempt to start server if needed (might already be running for manager)
            server_started_or_was_running = self._start_flask_server_if_needed() 
            
            if server_started_or_was_running:
                self.menu_bar.presenter_toggle_btn_text.set("Stop Presenter Webview")
                messagebox.showinfo("Presenter Active",
                                    f"Presenter view access enabled.\n"
                                    f"Link: http://localhost:{self.flask_port}/presenter",
                                    parent=self)
                webbrowser.open(f"http://localhost:{self.flask_port}/presenter") # <--- OPEN BROWSER HERE
                self._emit_full_state_to_webview() 
            else: # Server failed to start
                self.presenter_active = False # Revert state
                self.menu_bar.presenter_toggle_btn_text.set("Start Presenter Webview (Error)")
        else: # Trying to STOP presenter
            self.presenter_active = False
            self.menu_bar.presenter_toggle_btn_text.set("Start Presenter Webview")
            # Don't show a messagebox here, just disable. Server stops if nothing else needs it.
            print("Presenter view access disabled by admin.")
            if self.socketio_instance:
                self.socketio_instance.emit('server_message', 
                                            {'message': 'Presenter view has been disabled by admin.'}, 
                                            namespace='/presenter')
            self._stop_flask_server_if_idle() # Stop server if manager also inactive

    def _generate_manager_tokens(self):
        self.team_manager_access_tokens.clear()
        if not self.engine or not self.engine.teams_data:
            return
        for team_name in self.engine.teams_data.keys():
            self.team_manager_access_tokens[team_name] = secrets.token_urlsafe(16)
        print("Generated new manager access tokens:", self.team_manager_access_tokens)
        # If links window is open, update it
        if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
            self.manager_links_window_instance.update_links(self.team_manager_access_tokens if self.manager_access_enabled else {})

    def _handle_manager_access_toggle(self):
        if not FLASK_AVAILABLE:
            messagebox.showerror("Feature Unavailable", "Flask/SocketIO not available.", parent=self)
            return

        if not self.manager_access_enabled: # Trying to ENABLE manager access
            self.manager_access_enabled = True
            self._generate_manager_tokens()
            # Attempt to start server if needed (might already be running for presenter)
            server_started_or_was_running = self._start_flask_server_if_needed()

            if server_started_or_was_running:
                self.menu_bar.manager_toggle_btn_text.set("Disable Manager Access")
                messagebox.showinfo("Manager Access Enabled", 
                                    "Manager access enabled. Use 'Show Manager Links' to get URLs.", 
                                    parent=self)
                # DO NOT open browser here automatically
                if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
                    self.manager_links_window_instance.update_links(self.team_manager_access_tokens)
                self._emit_full_state_to_webview() # Ensure managers get current state
            else: # Server failed to start
                self.manager_access_enabled = False # Revert
                self.menu_bar.manager_toggle_btn_text.set("Enable Manager Access (Error)")
        else: # Trying to DISABLE manager access
            self.manager_access_enabled = False
            self.menu_bar.manager_toggle_btn_text.set("Enable Manager Access")
            # Don't show a messagebox here, just disable. Server stops if nothing else needs it.
            print("Manager view access disabled by admin.")
            if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
                self.manager_links_window_instance.update_links({})
            if self.socketio_instance:
                self.socketio_instance.emit('access_revoked', 
                                            {'message': 'Manager access has been disabled by admin.'}, 
                                            namespace='/manager')
            self._stop_flask_server_if_idle() # Stop server if presenter also inactive

    def _show_manager_links_window(self):
        if not self.manager_access_enabled:
            messagebox.showwarning("Manager Access Disabled", 
                                   "Manager access is currently disabled. Enable it first to view links.", parent=self)
            return

        if not self.engine or not self.engine.teams_data:
            messagebox.showerror("Error", "No teams loaded to generate links for.", parent=self)
            return
        
        if not self.team_manager_access_tokens: # Should be generated when access is enabled
            self._generate_manager_tokens()

        base_url = f"http://localhost:{self.flask_port}" # Assuming server is running or will run

        if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
            self.manager_links_window_instance.update_links(self.team_manager_access_tokens)
            self.manager_links_window_instance.show()
        else:
            self.manager_links_window_instance = ManagerLinksWindow(self, self.team_manager_access_tokens, base_url)
            self.manager_links_window_instance.show()

    def on_app_frame_closing(self):
        if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
            self.manager_links_window_instance.destroy() # Properly destroy the Toplevel
        if self.engine: self.engine.close_logger()
        # Stop Flask server if it's running, regardless of individual feature states
        if self.flask_server_running:
            print("Attempting to stop Flask server on app close...")
            self._stop_flask_server() # This is your existing method
        print("AuctionApp closed.")

    def _on_mousewheel_teams(self, event):
        widget_under_mouse = self.winfo_containing(event.x_root, event.y_root); target_canvas = None; current_widget = widget_under_mouse
        while current_widget is not None:
            if current_widget == self.teams_canvas or current_widget == self.scrollable_teams_frame: target_canvas = self.teams_canvas; break
            if current_widget == self: break
            if hasattr(current_widget, 'master'): current_widget = current_widget.master
            else: break
        if target_canvas:
            if event.delta: target_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4: target_canvas.yview_scroll(-1, "units")
            elif event.num == 5: target_canvas.yview_scroll(1, "units")

    def _create_team_cards_layout(self):
        # ... (No changes, admin panel remains text-based for cards) ...
        for widget in self.scrollable_teams_frame.winfo_children(): widget.destroy()
        self.money_labels.clear(); self.inventory_listboxes.clear(); self.team_card_frames.clear()
        self.scrollable_teams_frame.grid_columnconfigure(0, weight=1); self.scrollable_teams_frame.grid_columnconfigure(1, weight=1)
        all_teams_data = self.engine.get_all_team_data(); row_num, col_num = 0, 0
        for team_info in all_teams_data:
            team_name = team_info["name"]
            card = tk.Frame(self.scrollable_teams_frame, bg=THEME_BG_CARD, padx=15, pady=12, relief=tk.FLAT, bd=0); card.configure(highlightbackground=THEME_BORDER_COLOR_LIGHT, highlightthickness=1); card.grid(row=row_num, column=col_num, sticky="ew", padx=5, pady=8); self.team_card_frames[team_name] = card
            header_info_frame = tk.Frame(card,bg=THEME_BG_CARD); header_info_frame.pack(fill=tk.X, pady=(0,8))
            tk.Label(header_info_frame,text=team_name.upper(),font=get_font(16,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_PRIMARY,anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
            money_label=tk.Label(header_info_frame,text="₹0",font=get_font(15,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_TERTIARY,anchor="e"); money_label.pack(side=tk.RIGHT); self.money_labels[team_name]=money_label
            tk.Label(card,text="INVENTORY:",font=get_font(10,"bold"), bg=THEME_BG_CARD,fg=THEME_TEXT_SECONDARY,anchor="w").pack(fill=tk.X,pady=(5,2))
            inventory_listbox=tk.Listbox(card,font=get_font(10),height=3,relief=tk.FLAT,bd=0, bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, selectbackground=THEME_ACCENT_PRIMARY, selectforeground=THEME_TEXT_ACCENT, highlightthickness=0, activestyle="none"); inventory_listbox.pack(fill=tk.X,expand=True,pady=(0,10)); self.inventory_listboxes[team_name]=inventory_listbox
            StyledButton(card,text="BID NOW 💸",font=get_font(12, "bold"), bg=THEME_ACCENT_PRIMARY,fg=THEME_TEXT_ACCENT, command=lambda t=team_name: self.ui_place_bid(t), pady=10).pack(fill=tk.X)
            col_num += 1;
            if col_num >= 2: col_num = 0; row_num += 1
        self.scrollable_teams_frame.update_idletasks()
        if self.teams_canvas.winfo_exists(): self.teams_canvas.config(scrollregion=self.teams_canvas.bbox("all"))

    def update_team_cards_display(self):
        # ... (No changes, admin panel remains text-based for cards) ...
        all_teams_data = self.engine.get_all_team_data()
        for team_info in all_teams_data:
            team_name = team_info["name"]
            if team_name in self.money_labels and self.money_labels[team_name].winfo_exists(): self.money_labels[team_name].config(text=team_info["money_formatted"])
            if team_name in self.inventory_listboxes and self.inventory_listboxes[team_name].winfo_exists():
                listbox = self.inventory_listboxes[team_name]; listbox.delete(0, tk.END)
                for line in team_info["inventory_display_lines"]: listbox.insert(tk.END, line)
        self.scrollable_teams_frame.update_idletasks()
        if self.teams_canvas.winfo_exists(): self.teams_canvas.config(scrollregion=self.teams_canvas.bbox("all"))

    def update_available_players_display(self):
        # ... (No changes, admin panel remains text-based) ...
        if hasattr(self,'item_list_text') and self.item_list_text.winfo_exists():
            self.item_list_text.config(state=tk.NORMAL); self.item_list_text.delete("1.0", tk.END)
            available_players = self.engine.get_available_players_info()
            for player_name, _, base_bid_formatted in available_players:
                item_button_container = tk.Frame(self.item_list_text, bg=THEME_BG_CARD, padx=10, pady=8); item_button_container.configure(highlightbackground=THEME_BORDER_COLOR_LIGHT, highlightthickness=1)
                player_name_label = tk.Label(item_button_container, text=player_name, font=get_font(12, "bold"), anchor='w', bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY); player_name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                base_bid_label = tk.Label(item_button_container, text=base_bid_formatted, font=get_font(11), anchor='e', bg=THEME_BG_CARD, fg=THEME_ACCENT_SECONDARY); base_bid_label.pack(side=tk.RIGHT, padx=(10,0))
                for widget_to_bind in [item_button_container, player_name_label, base_bid_label]:
                    widget_to_bind.bind("<Button-1>", lambda e, pn=player_name: self.ui_select_item(pn)); widget_to_bind.config(cursor="hand2")
                    original_fg, hover_fg = (THEME_ACCENT_SECONDARY, THEME_TEXT_ACCENT) if widget_to_bind == base_bid_label else (THEME_TEXT_PRIMARY, THEME_HIGHLIGHT_FG)
                    apply_hover_effect(widget_to_bind, THEME_HIGHLIGHT_BG, THEME_BG_CARD, hover_fg=hover_fg, original_fg_default=original_fg)
                self.item_list_text.window_create("end", window=item_button_container, padx=0, pady=3); self.item_list_text.insert("end","\n")
            self.item_list_text.config(state=tk.DISABLED)

    def update_bidding_status_display(self):
        # ... (No changes, admin panel display is text-based) ...
        status = self.engine.get_current_bidding_status_display()
        self.current_item_label.config(text=status["item_display_name"])
        fg_color = THEME_TEXT_SECONDARY
        if status["status_color_key"] == "SUCCESS": fg_color = THEME_ACCENT_TERTIARY
        elif status["status_color_key"] == "WARNING": fg_color = THEME_ACCENT_SECONDARY
        self.bid_status_label.config(text=status["status_text"], fg=fg_color)
        self.auction_name_label.config(text=self.engine.get_auction_name().upper())

    def full_reload_all_content(self):
        ''' Currently used in _handle_load_selected_state_from_history to ensure all UI displays 
        are refreshed after loading a state. '''
        if self.flask_server_running and self.socketio_instance:
            if self.presenter_active:
                self.socketio_instance.emit('reload_all_team_status', namespace='/presenter')
            
            if self.manager_access_enabled:
                self.socketio_instance.emit('reload_all_team_status', namespace='/manager')
    
    def refresh_all_ui_displays(self):
        # This method is called from the main Tkinter thread.
        self.update_team_cards_display()
        self.update_available_players_display()
        self.update_bidding_status_display()
        
        # Emit state to webview if server is running
        if self.flask_server_running and self.socketio_instance:
            # Ensure this is scheduled if refresh_all_ui_displays can be called from non-main thread
            self._emit_full_state_to_webview()
            
    def _emit_full_state_to_webview(self):
        if not self.socketio_instance or not self.flask_server_running:
            # print("DEBUG UI: SocketIO not ready or server not running, cannot emit.") # Keep for debugging if needed
            return

        auction_name = self.engine.get_auction_name()
        current_item_data = None
        # Initialize bid_status_data WITH next_potential_bid as None initially
        bid_status_data = {
            'highest_bidder_name': None,
            'bidder_logo_path': None,
            'bid_amount': 0,
            'highest_bidder_exists': False,
            'next_potential_bid': None
        }
        next_potential_bid_calculated = None # Use a temporary variable for clarity

        if self.engine.bidding_active and self.engine.current_item_name:
            # Get the raw player name for the current item
            raw_current_player_name = self.engine.current_item_name 
            player_photo_web_path = self._get_web_path(raw_current_player_name, is_logo=False)

            current_item_data = {
                'name': self.engine.current_item_name,
                'photo_path': player_photo_web_path,
                'base_bid': self.engine.current_item_base_bid,
            }

            # Populate existing bid_status fields
            if self.engine.highest_bidder_name:
                raw_highest_bidder_team_name = self.engine.highest_bidder_name
                bidder_logo_web_path = self._get_web_path(raw_highest_bidder_team_name, is_logo=True)
                bid_status_data['highest_bidder_name'] = self.engine.highest_bidder_name
                bid_status_data['bidder_logo_path'] = bidder_logo_web_path
                bid_status_data['bid_amount'] = self.engine.current_bid_amount
                bid_status_data['highest_bidder_exists'] = True
            else: # No highest bidder, but item is active
                bid_status_data['bid_amount'] = self.engine.current_bid_amount # Opening bid
                bid_status_data['highest_bidder_exists'] = False
                # Ensure other fields are explicitly None if not set above
                bid_status_data['highest_bidder_name'] = None
                bid_status_data['bidder_logo_path'] = None


            # Calculate and add next_potential_bid
            next_potential_bid_calculated = self.engine.get_next_potential_bid_amount()
            bid_status_data['next_potential_bid'] = next_potential_bid_calculated # Assign it here

        # If not (self.engine.bidding_active and self.engine.current_item_name), 
        # current_item_data remains None and bid_status_data['next_potential_bid'] remains None (from initialization)

        full_state = {
            'auction_name': auction_name,
            'current_item': current_item_data,
            'bid_status': bid_status_data, # This now *always* contains next_potential_bid (even if null)
            'is_item_active': bool(self.engine.bidding_active and self.engine.current_item_name)
        }
        
        try:
            if self.presenter_active:
                # print(f"PYTHON DEBUG (Presenter Emit): bid_status being sent: {bid_status_data}") # Optional debug
                self.socketio_instance.emit('full_state_update', full_state, namespace='/presenter')
            
            if self.manager_access_enabled:
                # print(f"PYTHON DEBUG (Manager Emit): bid_status being sent: {bid_status_data}") # KEEP THIS FOR VERIFICATION
                self.socketio_instance.emit('full_state_update', full_state, namespace='/manager')
            
        except Exception as e:
            print(f"ERROR emitting full state to webview: {e}")
            import traceback
            traceback.print_exc()

    def _get_web_path(self, local_path):
        if not local_path:
            return None
        
        # Make paths web-friendly (replace backslashes, ensure it's relative if possible)
        web_path = local_path.replace('\\', '/')

        # If the path is absolute, we can only use the filename assuming it's in static/images
        # If it's already relative and starts with "images/" or similar, it might be okay.
        # A robust solution involves copying/linking all used images to the static folder
        # or having a dedicated Flask route to serve images from arbitrary locations (with security checks).

        # Simplification: Assume all images are placed/copied into a "static/images" folder.
        # The local_path might be "path/to/logos/alpha_logo.png" or "C:/abs/path/player1.png"
        filename = os.path.basename(web_path)
        
        # Check if Flask app is running and has a static_url_path (usually '/static')
        # This is a basic approach. For complex setups, image management needs more thought.
        if self.flask_app_instance:
             # Assuming your static folder is named 'static' and images are in an 'images' subfolder.
            return f"/static/images/{filename}" 
        else: # Fallback if flask not running, though this path won't be used by webview then
            return f"images/{filename}" # Placeholder

    def _check_and_display_engine_warnings(self, context_message="Engine Warning(s):"):
        warnings = self.engine.get_last_errors_and_clear()
        if warnings:
            full_warning_message = context_message + "\n - " + "\n - ".join(warnings)
            messagebox.showwarning("Auction Engine Notice", full_warning_message, parent=self)

    def ui_select_item(self, player_name):
        # Name of item that IS actually passed, to be used for a single event emission.
        name_of_item_confirmed_passed = None 

        try:
            # Case 1: Current item has bids, requires explicit pass confirmation
            if self.engine.bidding_active and self.engine.current_item_name and self.engine.highest_bidder_name:
                current_active_item_with_bids = self.engine.current_item_name
                if not messagebox.askyesno("Confirm Item Change", 
                                           f"'{current_active_item_with_bids}' is active with bids from '{self.engine.highest_bidder_name}'.\n\n"
                                           f"Do you want to select '{player_name}' instead? \n"
                                           f"If yes, '{current_active_item_with_bids}' will be PASSED (returned to available players).", 
                                           icon='warning', parent=self):
                    return # User cancelled

                # User confirmed: Explicitly pass the current item with bids
                # engine.pass_current_item() returns the name of the item passed or None
                passed_item_name = self.engine.pass_current_item(
                    reason_comment=f"'{current_active_item_with_bids}' passed (with bids) due to new selection of '{player_name}'."
                )
                if passed_item_name:
                    name_of_item_confirmed_passed = passed_item_name
                    messagebox.showinfo("Item Passed", f"'{name_of_item_confirmed_passed}' (which had bids) was passed and returned to available players.", parent=self)
                    # EMIT PASS EVENT HERE for the item that was explicitly passed
                    if self.socketio_instance and self.flask_server_running:
                        self.socketio_instance.emit('item_passed_event', {'item_name': name_of_item_confirmed_passed}, namespace='/presenter')
                        self.socketio_instance.emit('item_passed_event', {'item_name': name_of_item_confirmed_passed}, namespace='/manager')
            
            # Now, select the new item.
            # The engine's select_item_for_bidding will auto-pass the *previous* item 
            # if it was active but had NO bids.
            item_name_before_select_new = self.engine.current_item_name # Capture before select_item_for_bidding changes it
            
            passed_message_from_engine_select = self.engine.select_item_for_bidding(player_name)

            if passed_message_from_engine_select: 
                # This means engine auto-passed 'item_name_before_select_new' (which had NO bids).
                # Ensure this is a different item than one explicitly passed above (if any).
                if item_name_before_select_new and item_name_before_select_new != name_of_item_confirmed_passed:
                    # Update name_of_item_confirmed_passed if this is a new pass event we need to send
                    name_of_item_confirmed_passed = item_name_before_select_new 
                    messagebox.showinfo("Item Auto-Passed", passed_message_from_engine_select, parent=self)
                    # EMIT PASS EVENT HERE for the item auto-passed by engine
                    if self.socketio_instance and self.flask_server_running:
                        self.socketio_instance.emit('item_passed_event', {'item_name': name_of_item_confirmed_passed}, namespace='/presenter')
                        self.socketio_instance.emit('item_passed_event', {'item_name': name_of_item_confirmed_passed}, namespace='/manager')
                elif not item_name_before_select_new and passed_message_from_engine_select:
                     # This case should ideally not happen if engine logic is sound (pass message implies an item was passed)
                     print(f"WARNING: select_item_for_bidding returned pass message ('{passed_message_from_engine_select}') but no prior current item was identified by UI.")


        except AuctionError as e: 
            messagebox.showerror("Selection Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays() # This emits full state for the NEWLY selected item.
            # The item_passed_event is now emitted within the 'try' block if a pass occurred.
            # No more item_passed_event emission here.
            self._check_and_display_engine_warnings()

    def ui_place_bid(self, team_name): # Called by Admin Panel
        try:
            self.engine.place_bid(team_name)
        except AuctionError as e: messagebox.showerror("Bid Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays() # Emits full state
            self._check_and_display_engine_warnings()

    def ui_place_bid_from_webview(self, team_name): # Called by Flask thread via root.after
        # This method MUST be called in the Tkinter main thread.
        # The Flask SocketIO handler should use self.master.after(0, lambda: self.ui_place_bid_from_webview(team_name))
        print(f"ADMIN_PANEL_INFO: Bid received from webview for team '{team_name}' for item '{self.engine.current_item_name}'")
        try:
            # Check if bidding is still valid (item might have been sold/passed by admin just before this executes)
            if not self.engine.bidding_active or not self.engine.current_item_name:
                print(f"ADMIN_PANEL_WARNING: Web bid for '{team_name}' arrived too late. Item no longer active.")
                if self.socketio_instance and self.flask_server_running: # Try to inform specific manager
                    # This is tricky as we don't have the original request.sid here easily
                    # For now, the global refresh will show the item is gone.
                     self.socketio_instance.emit('bid_error', {'message': 'Bidding for this item has just closed.'}, namespace='/manager') # Broadcast, less ideal
                return

            bid_amount, highest_bidder = self.engine.place_bid(team_name)
            print(f"ADMIN_PANEL_SUCCESS: Web bid by '{team_name}' for '{self.engine.current_item_name}' at {bid_amount} successful. Highest: {highest_bidder}")

        except InsufficientFundsError as e:
            print(f"ADMIN_PANEL_ERROR: Web bid by '{team_name}' failed: {e}")
            if self.socketio_instance and self.flask_server_running:
                 self.socketio_instance.emit('bid_error', {'message': str(e)}, namespace='/manager') # Broadcast
        except InvalidBidError as e: # e.g. already highest bidder
            print(f"ADMIN_PANEL_ERROR: Web bid by '{team_name}' failed: {e}")
            if self.socketio_instance and self.flask_server_running:
                 self.socketio_instance.emit('bid_error', {'message': str(e)}, namespace='/manager')
        except AuctionError as e:
            print(f"ADMIN_PANEL_ERROR: Web bid by '{team_name}' failed with general AuctionError: {e}")
            if self.socketio_instance and self.flask_server_running:
                 self.socketio_instance.emit('bid_error', {'message': str(e)}, namespace='/manager')
        finally:
            # This will update the admin UI and send a full_state_update to all web clients
            self.refresh_all_ui_displays()
            self._check_and_display_engine_warnings("Warning processing web bid:")

    def ui_undo_last_bid(self):
        try:
            self.engine.undo_last_bid()
        except AuctionError as e: messagebox.showerror("Undo Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays() # Emits full state
            self._check_and_display_engine_warnings()

    def ui_sell_item(self):
        sold_data_for_event = None
        try:
            item_name, winner, bid, message = self.engine.sell_current_item()
            messagebox.showinfo("Item Sold", message, parent=self)
            
            player_photo_web_path = self._get_web_path(item_name, is_logo=False) 
            team_logo_web_path = self._get_web_path(winner, is_logo=True)
            sold_data_for_event = {
                'player_name': item_name,
                'player_photo_path': player_photo_web_path,
                'winning_team_name': winner,
                'winning_team_logo_path': team_logo_web_path,
                'sold_price': bid
            }
        except AuctionError as e: messagebox.showerror("Sell Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays() 
            if sold_data_for_event and self.socketio_instance and self.flask_server_running:
                # print(f"DEBUG UI (Tkinter): Emitting 'item_sold_event': {sold_data_for_event}")
                self.socketio_instance.emit('item_sold_event', sold_data_for_event, namespace='/presenter')
                self.socketio_instance.emit('item_sold_event', sold_data_for_event, namespace='/manager')
            self._check_and_display_engine_warnings()

    def ui_pass_item(self):
        name_of_item_to_be_passed = None
        try:
            name_of_item_to_be_passed = self.engine.current_item_name # Get name before it's cleared
            if not name_of_item_to_be_passed:
                messagebox.showinfo("Pass Item", "No item currently active to pass.", parent=self)
                # No event to emit if nothing was to be passed.
                # refresh_all_ui_displays in finally will ensure client reflects no item.
                return # Exit early

            # Optional: Confirmation if item has bids (good UX)
            if self.engine.highest_bidder_name:
                 if not messagebox.askyesno("Confirm Pass", 
                                           f"'{name_of_item_to_be_passed}' has bids from '{self.engine.highest_bidder_name}'.\n\n"
                                           f"Are you sure you want to pass this item?",
                                           icon='warning', parent=self):
                    return # User cancelled

            # Proceed to pass the item
            passed_item_name_from_engine = self.engine.pass_current_item()
            
            if passed_item_name_from_engine: # Engine confirmed an item was passed
                messagebox.showinfo("Item Passed", f"'{passed_item_name_from_engine}' passed/unsold.", parent=self)
                # EMIT PASS EVENT HERE, BEFORE full_state_update
                if self.socketio_instance and self.flask_server_running:
                    self.socketio_instance.emit('item_passed_event', {'item_name': passed_item_name_from_engine}, namespace='/presenter')
                    self.socketio_instance.emit('item_passed_event', {'item_name': passed_item_name_from_engine}, namespace='/manager')
            # If passed_item_name_from_engine is None, it means engine.pass_current_item determined there was nothing to pass
            # (e.g., if state changed between name capture and pass call, though unlikely here).
            # The initial check for name_of_item_to_be_passed should mostly cover this.

        except AuctionError as e:
            messagebox.showerror("Pass Error", str(e), parent=self)
            # If an error occurred during pass, the actual pass might not have happened.
            # refresh_all_ui_displays will send the current (possibly unchanged or error) state.
            # No explicit item_passed_event if the pass itself failed.
        finally:
            self.refresh_all_ui_displays() # Emits full state (which will show item as null and bid status cleared if pass was successful)
            # item_passed_event is now emitted in the 'try' block above, BEFORE this refresh.
            self._check_and_display_engine_warnings()

    def _create_shutdown_overlay(self, initial_message="Please Wait: Initializing shutdown..."):
        if self.shutdown_overlay and self.shutdown_overlay.winfo_exists():
            self.shutdown_overlay.destroy()

        self.shutdown_overlay = tk.Toplevel(self.master) # Make it a child of root, not self (the Frame)
                                                        # This might help with transient behavior.
        self.shutdown_overlay.withdraw()
        self.shutdown_overlay.overrideredirect(True) # <<< REINSTATE for borderless
        self.shutdown_overlay.attributes("-alpha", 0.85)
        self.shutdown_overlay.transient(self.master) # Set as transient to the main window
        self.shutdown_overlay.title("Processing...") # Give it a minimal title
        # self.shutdown_overlay.attributes("-topmost", True) 

        self.master.update_idletasks()
        main_app_width = self.master.winfo_width()
        main_app_height = self.master.winfo_height()
        main_app_x = self.master.winfo_x()
        main_app_y = self.master.winfo_y()

        overlay_width = 350
        overlay_height = 100
        x_pos = main_app_x + (main_app_width // 2) - (overlay_width // 2)
        y_pos = main_app_y + (main_app_height // 2) - (overlay_height // 2)

        self.shutdown_overlay.geometry(f"{overlay_width}x{overlay_height}+{x_pos}+{y_pos}")
        self.shutdown_overlay.configure(bg=THEME_BG_CARD)

        self.shutdown_status_var.set(initial_message)
        status_label = tk.Label(self.shutdown_overlay,
                                textvariable=self.shutdown_status_var,
                                font=get_font(14, "bold"),
                                bg=THEME_BG_CARD,
                                fg=THEME_TEXT_ACCENT,
                                wraplength=overlay_width - 20)
        status_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        self.shutdown_overlay.deiconify()
        self.shutdown_overlay.grab_set() # Still grab to block main app interaction
        self.shutdown_overlay.lift() # Ensure it's above other app windows
        self.update_idletasks()

    def _update_shutdown_status(self, message):
        if self.shutdown_overlay and self.shutdown_overlay.winfo_exists():
            self.shutdown_status_var.set(f"Please Wait: {message}")
            self.shutdown_overlay.update_idletasks() # Refresh the label

    def _destroy_shutdown_overlay(self):
        if self.shutdown_overlay and self.shutdown_overlay.winfo_exists():
            self.shutdown_overlay.grab_release()
            self.shutdown_overlay.destroy()
            self.shutdown_overlay = None
        self.update_idletasks()

    def _stop_flask_server(self, silent_on_success=False): # Added silent_on_success
        if not self.flask_server_running:
            if not silent_on_success: # Only show if not part of a silent app close
                messagebox.showinfo("Webview Info", "Webview server is not running.", parent=self)
            return False
        
        # If not called from on_app_frame_closing, create/update overlay normally
        if not silent_on_success:
            self._create_shutdown_overlay("Signaling server to stop...")
        else: # Called from on_app_frame_closing, ensure status is updated if overlay already exists
            self._update_shutdown_status("Signaling server to stop...")
        self.update_idletasks()
        
        print("Attempting to stop Flask-SocketIO server via HTTP request...")
        shutdown_success = False
        try:
            self._update_shutdown_status("Sending shutdown request...")
            response = requests.post(f"http://localhost:{self.flask_port}/shutdown_server_please", timeout=3) # Increased timeout slightly
            print(f"Shutdown request response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                shutdown_success = True # Assume server got the message
        except requests.exceptions.RequestException as e:
            print(f"Could not connect to Flask server to shut it down: {e}")
            self._update_shutdown_status("Server connection error. Trying to join thread...")
        
        self.stop_flask_event.set() 

        if self.flask_thread and self.flask_thread.is_alive():
            self._update_shutdown_status("Waiting for server thread (max 5s)...")
            print("Waiting for Flask thread to join...")
            self.flask_thread.join(timeout=5) 
            if self.flask_thread.is_alive():
                print("Warning: Flask thread did not stop cleanly after timeout.")
                self._update_shutdown_status("Server thread did not exit cleanly.")
                # Consider more forceful termination if absolutely necessary, but it's risky
            else:
                print("Flask thread joined successfully.")
                self._update_shutdown_status("Server thread stopped.")
        
        self.flask_server_running = False
        if hasattr(self.menu_bar, 'presenter_toggle_btn_text'):
            self.menu_bar.presenter_toggle_btn_text.set("Start Presenter Webview")
        if hasattr(self.menu_bar, 'manager_toggle_btn_text'):
            self.menu_bar.manager_toggle_btn_text.set("Enable Manager Access")

        self.socketio_instance = None
        self.flask_app_instance = None
        self.flask_thread = None
        
        if not silent_on_success: # Check flag before destroying overlay and showing message
            self._destroy_shutdown_overlay()
            messagebox.showinfo("Webview Info", "Webview server has been stopped.", parent=self)
        else: # If silent, just destroy the overlay
            self._destroy_shutdown_overlay()
            print("Webview server stopped silently.")
        return True

    def on_app_frame_closing(self):
        if self.engine:
            self.engine.close_logger()

        if self.flask_server_running:
            print("Attempting to stop Flask server on app close...")
            # Create overlay if not already there (e.g. if stop was initiated by menu)
            if not (self.shutdown_overlay and self.shutdown_overlay.winfo_exists()):
                 self._create_shutdown_overlay("Closing application: Shutting down web server...")
            else: # Overlay might exist if user clicked "Stop server" then immediately "Close app"
                 self._update_shutdown_status("Closing application: Shutting down web server...")
            self.update_idletasks()
            
            self._stop_flask_server(silent_on_success=True) # Pass True to suppress final messagebox
            # Overlay is destroyed within _stop_flask_server
        
        if self.manager_links_window_instance and self.manager_links_window_instance.winfo_exists():
            self.manager_links_window_instance.destroy()
        
        print("AuctionApp closed. Main window will be destroyed by root protocol.")
        # self.master.destroy() # Let the root.protocol("WM_DELETE_WINDOW", on_root_close) handle this

    def _sanitize_for_filename(self, name, is_logo=False):
        if not name:
            return None
        # Replace spaces and special characters (except parentheses for player names) with hyphens
        # Keep parentheses for player names like "Player Three (WK)"
        if not is_logo and '(' in name and ')' in name:
            # For players like "Player Name (Role)" -> "Player-Name-(Role)"
            sanitized_name = re.sub(r'[^\w\s\(\)-]', '', name) # Allow word chars, whitespace, (), -
            sanitized_name = re.sub(r'\s+', '-', sanitized_name) # Replace spaces with hyphens
        else:
            # For team names or players without roles in parentheses
            sanitized_name = re.sub(r'[^\w\s-]', '', name) # Allow word chars, whitespace, -
            sanitized_name = re.sub(r'\s+', '-', sanitized_name) # Replace spaces with hyphens
        
        if is_logo:
            return f"{sanitized_name}-logo" # e.g., Team-Alpha-logo
        else:
            return sanitized_name # e.g., Player-One or Player-Three-(WK)

    def _find_image_filename_with_extension(self, base_filename_no_ext):
        if not base_filename_no_ext:
            return None

        app_base_dir = get_executable_directory_path() # Get executable's directory
        static_images_dir = os.path.join(app_base_dir, 'static', 'images')

        if not os.path.isdir(static_images_dir):
            print(f"Warning: External static images directory not found at {static_images_dir}")
            # Fallback: guess common extensions without checking existence
            return f"{base_filename_no_ext}.png" # Or another default behavior

        possible_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        for ext in possible_extensions:
            potential_filename = f"{base_filename_no_ext}{ext}"
            if os.path.exists(os.path.join(static_images_dir, potential_filename)):
                return potential_filename
        return f"{base_filename_no_ext}.png" # Fallback

    def _get_web_path(self, entity_name, is_logo=False):
        # entity_name is the raw player name (e.g., "Player One") or team name (e.g., "Team Alpha")
        if not entity_name:
            return None

        base_filename_no_ext = self._sanitize_for_filename(entity_name, is_logo)
        if not base_filename_no_ext:
            return None
            
        actual_filename_with_ext = self._find_image_filename_with_extension(base_filename_no_ext)
        if not actual_filename_with_ext:
            # This fallback means we couldn't even guess an extension, or sanitize failed badly.
            # Very unlikely if entity_name is valid.
            print(f"Warning: Could not determine image filename for '{entity_name}'.")
            return None

        if self.flask_app_instance: # Check if Flask is running
            return f"/static/images/{actual_filename_with_ext}"
        else:
            return None

    def _show_documentation(self):
        try:
            base_path = get_executable_directory_path()
            # Assuming documentation.html is directly in 'templates'
            # and 'templates' is either bundled (found via _MEIPASS) 
            # or a sibling to auction_UI.py in development.
            doc_filename = "documentation.html"
            doc_path_in_templates = os.path.join("templates", doc_filename) # Relative path for bundling
            
            # Construct the absolute path
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Bundled: path is relative to _MEIPASS
                doc_file_abs_path = os.path.join(base_path, doc_path_in_templates)
            else:
                # Development: path is relative to script or project root
                # Assuming 'templates' is a subdirectory of where auction_UI.py is, or where base_path points
                doc_file_abs_path = os.path.join(base_path, "templates", doc_filename)

            if not os.path.exists(doc_file_abs_path):
                # Fallback if structure is different (e.g. auction_UI in src, templates at root)
                alt_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                alt_doc_path = os.path.join(alt_base_path, "templates", doc_filename)
                if os.path.exists(alt_doc_path):
                    doc_file_abs_path = alt_doc_path
                else:
                    messagebox.showerror("Error", f"Documentation file not found at expected locations:\n1. {doc_file_abs_path}\n2. {alt_doc_path}", parent=self)
                    return

            # Convert to a file:/// URL
            doc_url = pathlib.Path(doc_file_abs_path).as_uri()
            print(f"Opening documentation: {doc_url}")
            webbrowser.open(doc_url)

        except Exception as e:
            messagebox.showerror("Error Opening Documentation", f"Could not open documentation: {e}", parent=self)
            import traceback
            traceback.print_exc()

def main():
    # ... (No changes from your provided code, includes handle_resume_auction_logic) ...
    root = tk.Tk(); root.title("Auction Command"); root.geometry("1300x850"); root.configure(bg=THEME_BG_PRIMARY)
    
    # --- SETTING THE WINDOW ICON ---
    try:
        # Icon is expected at the runtime root because of datas=[(..., '.')]
        icon_filename = "auction-command-icon.ico"
        icon_path_resolved = resource_path(icon_filename) # Pass only the filename

        if os.path.exists(icon_path_resolved):
             root.iconbitmap(icon_path_resolved)
        else:
            print(f"Warning: Window icon file not found at {icon_path_resolved}")
            # Fallback for development if running script directly from project root
            # where 'static/images/auction-command-icon.ico' exists
            dev_icon_path = os.path.join(os.path.abspath("."), "static", "images", icon_filename)
            if os.path.exists(dev_icon_path):
                print(f"Info: Found icon at development path: {dev_icon_path}")
                root.iconbitmap(dev_icon_path)
            else:
                 print(f"Warning: Window icon also not found at dev path: {dev_icon_path}")


    except tk.TclError:
        print("Warning: Could not set .ico window icon (TclError).")
    except Exception as e:
        print(f"Warning: An unexpected error occurred while setting window icon: {e}")
    # --- END OF ICON SETTING ---
    
    try:
        root.tk.call('tk_setPalette', 'background', THEME_BG_SECONDARY); root.tk.call('tk_setPalette', 'foreground', THEME_TEXT_PRIMARY)
        root.tk.call('tk_setPalette', 'activeBackground', THEME_HIGHLIGHT_BG); root.tk.call('tk_setPalette', 'activeForeground', THEME_TEXT_PRIMARY)
    except tk.TclError: print("Note: Could not set global messagebox palette.")
    current_page_widget = None; auction_engine_main = AuctionEngine()
    def clear_current_page():
        nonlocal current_page_widget
        if current_page_widget:
            if isinstance(current_page_widget, AuctionApp): current_page_widget.on_app_frame_closing()
            current_page_widget.destroy(); current_page_widget = None
    def show_page(page_class, *args, **kwargs):
        nonlocal current_page_widget; clear_current_page()
        try:
            current_page_widget = page_class(root, *args, **kwargs); current_page_widget.pack(fill="both", expand=True)
            if isinstance(current_page_widget, AuctionApp):
                warnings = auction_engine_main.get_last_errors_and_clear()
                if warnings: messagebox.showwarning("Auction Init Warning", "Issues during setup:\n - " + "\n - ".join(warnings), parent=current_page_widget)
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Page Load Error",f"Page load failed: {e}.\nDetails: {type(e).__name__}. Back to initial.")
            clear_current_page(); current_page_widget = InitialPage(root, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), handle_resume_auction_logic); current_page_widget.pack(fill="both", expand=True)
    def start_new_auction_ui(teams_data_dicts, players_data_dicts, auction_name_str, bid_increment_rules_from_csv=None):
        nonlocal auction_engine_main
        try:
            auction_engine_main.setup_new_auction(auction_name_str, teams_data_dicts, players_data_dicts)
            if bid_increment_rules_from_csv: auction_engine_main.set_bid_increment_rules(bid_increment_rules_from_csv)
            show_page(AuctionApp, auction_engine_instance=auction_engine_main)
        except (InitializationError, LogFileError, AuctionError) as e: messagebox.showerror("New Auction Error", f"Start failed: {e}", parent=root); show_page(InitialPage, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), handle_resume_auction_logic)
        except Exception as e: import traceback; traceback.print_exc(); messagebox.showerror("Critical Setup Error", f"Unexpected setup error: {e}", parent=root)
    def start_resumed_auction_ui(log_file_path_str):
        nonlocal auction_engine_main
        try: auction_engine_main.load_auction_from_log(log_file_path_str); show_page(AuctionApp, auction_engine_instance=auction_engine_main)
        except (LogFileError, AuctionError) as e: messagebox.showerror("Resume Error", f"Resume failed '{os.path.basename(log_file_path_str)}':\n{e}", parent=root); show_page(InitialPage, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), handle_resume_auction_logic)
        except Exception as e: import traceback; traceback.print_exc(); messagebox.showerror("Critical Load Error", f"Unexpected load error: {e}", parent=root)
    def handle_resume_auction_logic():
        cwd = os.getcwd()
        try:
            log_files_in_cwd = [f for f in os.listdir(cwd) if f.endswith(LOG_FILE_EXTENSION) and os.path.isfile(os.path.join(cwd, f))]
        except OSError as e:
            messagebox.showwarning("Directory Error", f"Could not scan current directory: {e}", parent=root); log_files_in_cwd = []
        if len(log_files_in_cwd) == 1:
            log_file_path_str = os.path.join(cwd, log_files_in_cwd[0])
            if messagebox.askyesno("Resume Auction", f"Found log file:\n'{log_files_in_cwd[0]}'\n\nResume this auction?", parent=root, icon='question'):
                start_resumed_auction_ui(log_file_path_str)
            else: show_page(FileSelectPageForResume, start_resumed_auction_ui)
        else:
            if not log_files_in_cwd: messagebox.showinfo("No Logs Found", "No .auctionlog files in current directory.", parent=root)
            elif len(log_files_in_cwd) > 1: messagebox.showinfo("Multiple Logs Found", "Multiple .auctionlog files in current directory. Select manually.", parent=root)
            show_page(FileSelectPageForResume, start_resumed_auction_ui)
    def on_root_close():
        nonlocal current_page_widget
        if isinstance(current_page_widget, AuctionApp): current_page_widget.on_app_frame_closing()
        elif auction_engine_main and auction_engine_main.get_log_filepath(): auction_engine_main.close_logger()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_root_close)
    show_page(InitialPage, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), handle_resume_auction_logic)
    root.mainloop()


if __name__ == "__main__":
    main()