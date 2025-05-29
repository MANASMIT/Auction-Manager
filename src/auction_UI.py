# --- auction_UI.py ---
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, scrolledtext, font as tkFont
import os
import re
import csv
import json
from datetime import datetime

# Assuming Pillow is installed for Presenter View's image handling,
# but not directly used for display in *this* admin UI file.
# from PIL import Image, ImageTk, ImageDraw # Only if admin were to show images

from auction_engine import (
    AuctionEngine, AuctionError, InsufficientFundsError,
    ItemNotSelectedError, InvalidBidError, NoBidsError,
    LogFileError, InitializationError, generate_template_csv_content,
    PLAYER_PHOTO_PATH_KEY, TEAM_LOGO_PATH_KEY
)

# We need to import from presenter_view.py
# This assumes presenter_view.py is in the same directory
try:
    from presenter_view import PresenterWindow
except ImportError:
    PresenterWindow = None # Fallback if presenter_view.py is missing
    print("WARNING: presenter_view.py not found. Presenter mode will be unavailable.")


# --- Constants (from previous versions) ---
LOG_SECTION_CONFIG = "[CONFIG]"
LOG_SECTION_TEAMS_INITIAL = "[TEAMS_INITIAL]"
LOG_SECTION_PLAYERS_INITIAL = "[PLAYERS_INITIAL]"
LOG_SECTION_AUCTION_STATES = "[AUCTION_STATES]"
LOG_SECTION_BID_INCREMENT_RULES = "[BID_INCREMENT_RULES]" # For CSV parsing
LOG_KEY_AUCTION_NAME = "AuctionName" # For CSV parsing
LOG_FILE_EXTENSION = ".auctionlog"
CSV_DELIMITER = ',' # For CSV parsing

# --- UI Styling Constants - NEW THEME ---
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
THEME_BORDER_COLOR_DARK = "#171e24" 
THEME_HIGHLIGHT_BG = "#3b4a58"     
THEME_HIGHLIGHT_FG = THEME_TEXT_PRIMARY
FONT_FAMILY_PRIMARY = "Segoe UI"
FONT_FAMILY_FALLBACK = "Arial"
BG_COLOR = THEME_BG_PRIMARY
FRAME_BG_COLOR = THEME_BG_SECONDARY
TEXT_COLOR = THEME_TEXT_PRIMARY
PRIMARY_BUTTON_BG = THEME_ACCENT_PRIMARY
PRIMARY_BUTTON_FG = THEME_TEXT_ACCENT
SECONDARY_BUTTON_BG = THEME_BG_CARD
SECONDARY_BUTTON_FG = THEME_TEXT_PRIMARY
HOVER_BG_COLOR_PRIMARY = "#007fcc"
HOVER_BG_COLOR_SECONDARY = THEME_HIGHLIGHT_BG
BORDER_COLOR = THEME_BORDER_COLOR_LIGHT

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
    # ... (No changes from your provided code) ...
    def __init__(self, master, on_new_auction_selected, on_resume_auction_selected):
        super().__init__(master, bg=THEME_BG_PRIMARY)
        container = tk.Frame(self, bg=THEME_BG_PRIMARY, padx=60, pady=60); container.pack(expand=True, fill="both")
        tk.Label(container, text="AUCTION COMMAND", font=get_font(36, "bold"), bg=THEME_BG_PRIMARY, fg=THEME_ACCENT_PRIMARY).pack(pady=(20, 50))
        StyledButton(container, text="START NEW AUCTION", command=on_new_auction_selected, font=get_font(16, "bold"), bg=PRIMARY_BUTTON_BG, fg=PRIMARY_BUTTON_FG, width=28, pady=15).pack(pady=15)
        StyledButton(container, text="RESUME AUCTION", command=on_resume_auction_selected, font=get_font(16, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, width=28, pady=15).pack(pady=15)


class FileSelectPage(tk.Frame):
    # ... (No changes from your provided code, includes CSV template link and parsing for image paths) ...
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
    # ... (No changes from your provided code) ...
    def __init__(self, master, on_log_file_selected_for_resume):
        super().__init__(master, on_file_loaded_data=None, title="RESUME AUCTION")
        self.on_log_file_selected_for_resume = on_log_file_selected_for_resume
        container_frame = self.winfo_children()[0]
        widgets_to_remove_texts = ["Auction Name:", "Select Initial Setup File (.csv):", "BROWSE SETUP FILE", "View .csv format help"]
        for widget in list(container_frame.winfo_children()): # Iterate over a copy
            if isinstance(widget, tk.Entry): widget.destroy()
            elif isinstance(widget, tk.Frame): # For the csv_info_frame and its children
                for sub_widget in widget.winfo_children():
                    if hasattr(sub_widget, 'cget') and 'text' in sub_widget.configure() and \
                       any(rtxt in sub_widget.cget("text") for rtxt in widgets_to_remove_texts):
                        sub_widget.destroy()
                if not widget.winfo_children(): # If frame becomes empty
                    widget.destroy()
            elif hasattr(widget, 'cget') and 'text' in widget.configure() and any(rtxt in widget.cget("text") for rtxt in widgets_to_remove_texts): widget.destroy()
            elif isinstance(widget, StyledButton) and "SETUP FILE" in widget.cget("text"): widget.destroy()
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
    # ... (Changes for scrollbar styling and toggleable JSON as per your file) ...
    def __init__(self, master, log_filepath, load_state_callback):
        super().__init__(master)
        self.log_filepath = log_filepath; self.load_state_callback = load_state_callback
        self.title("Auction Log History Viewer"); self.geometry("1200x750"); self.configure(bg=THEME_BG_PRIMARY); self.grab_set(); self.focus_set()
        style = ttk.Style(self); style.theme_use("clam") # Ensure theme is used for ttk widgets
        style.configure("Treeview", background=THEME_BG_SECONDARY, foreground=THEME_TEXT_PRIMARY, fieldbackground=THEME_BG_SECONDARY, font=get_font(10), rowheight=get_font(10).metrics('linespace') + 6, borderwidth=0, relief=tk.FLAT)
        style.configure("Treeview.Heading", font=get_font(11, "bold"), background=THEME_BG_CARD, foreground=THEME_ACCENT_PRIMARY, relief=tk.FLAT, borderwidth=0)
        style.map("Treeview.Heading", background=[('active', THEME_HIGHLIGHT_BG)])
        style.map("Treeview", background=[('selected', THEME_ACCENT_PRIMARY)], foreground=[('selected', THEME_TEXT_ACCENT)])

        # Scrollbar styling (ensure it's applied correctly)
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
        super().__init__(master, bg=THEME_BG_CARD, **kwargs) # Menu bar background
        self.app_controller = app_controller # To call methods in AuctionApp
        self.visible = False
        self.menu_items_frame = None

        # Menu toggle button (arrow)
        self.toggle_button = StyledButton(self, text="▼ Menu", 
                                          command=self.toggle_menu_visibility,
                                          font=get_font(9), padx=8, pady=4,
                                          bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY)
        self.toggle_button.pack(side=tk.LEFT, anchor="nw", padx=5, pady=2)
        
        # Bind Alt key to the root window for toggling
        master.master.bind_all("<Alt_L>", lambda e: self.toggle_menu_visibility()) # master.master to get to root
        master.master.bind_all("<Alt_R>", lambda e: self.toggle_menu_visibility())

        self._create_menu_items() # Create but don't pack initially

    def _create_menu_items(self):
        self.menu_items_frame = tk.Frame(self, bg=THEME_BG_CARD)
        # Actual menu buttons will go here

        # File Menu (Conceptual - direct commands for now)
        file_label = tk.Label(self.menu_items_frame, text="File", font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, padx=10)
        file_label.pack(side=tk.LEFT)
        
        exit_btn = StyledButton(self.menu_items_frame, text="Exit", command=self.app_controller.master.destroy, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        exit_btn.pack(side=tk.LEFT, padx=2)

        # View Menu
        view_label = tk.Label(self.menu_items_frame, text="View", font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, padx=10)
        view_label.pack(side=tk.LEFT, padx=(10,0))

        presenter_btn = StyledButton(self.menu_items_frame, text="Toggle Presenter", command=self.app_controller._toggle_presenter_view, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        presenter_btn.pack(side=tk.LEFT, padx=2)

        logs_btn = StyledButton(self.menu_items_frame, text="Show Logs", command=self.app_controller._open_log_viewer, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        logs_btn.pack(side=tk.LEFT, padx=2)
        
        # Help Menu
        help_label = tk.Label(self.menu_items_frame, text="Help", font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_ACCENT_PRIMARY, padx=10)
        help_label.pack(side=tk.LEFT, padx=(10,0))
        
        about_btn = StyledButton(self.menu_items_frame, text="About", command=self._show_about, font=get_font(9), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=8, pady=2)
        about_btn.pack(side=tk.LEFT, padx=2)


    def toggle_menu_visibility(self, event=None): # event=None for direct calls
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
                            "Auction Command v1.0\n\nA Simple Auction Management Tool.",
                            parent=self.app_controller) # Parent to AuctionApp

class AuctionApp(tk.Frame):
    def __init__(self, master, auction_engine_instance):
        super().__init__(master, bg=THEME_BG_PRIMARY)
        self.pack(fill="both", expand=True) # Removed padx/pady from here
        self.engine = auction_engine_instance
        self.team_card_frames = {}
        self.money_labels = {}
        self.inventory_listboxes = {}
        # self._admin_image_references = {} # Not needed if admin doesn't show images

        self.presenter_window = None
        self.presenter_window_visible = False
        self._presenter_last_action_sell_pass = False


        self._setup_ui() # This will now include the menu bar
        self.refresh_all_ui_displays()

    def _setup_ui(self):
        # Top Menu Bar
        self.menu_bar = TopMenuBar(self, app_controller=self)
        self.menu_bar.pack(fill=tk.X, side=tk.TOP)

        # Main content frame below menu bar
        app_content_frame = tk.Frame(self, bg=THEME_BG_PRIMARY)
        app_content_frame.pack(fill="both", expand=True, padx=10, pady=(0,10)) # Add padding here

        header_frame = tk.Frame(app_content_frame, bg=THEME_BG_SECONDARY, padx=15, pady=10)
        header_frame.pack(fill=tk.X, pady=(0,10), side=tk.TOP)

        header_left = tk.Frame(header_frame, bg=THEME_BG_SECONDARY)
        header_left.pack(side=tk.LEFT)
        self.auction_name_label = tk.Label(header_left, text=self.engine.get_auction_name().upper(), font=get_font(18, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY)
        self.auction_name_label.pack(side=tk.LEFT, padx=(0,20))
        # Removed direct toggle presenter and logs buttons from here

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
        self.current_item_label.grid(row=1, column=0, sticky="new")

        main_content_below_header = tk.Frame(app_content_frame, bg=THEME_BG_PRIMARY)
        main_content_below_header.pack(fill="both", expand=True, side=tk.TOP)
        main_content_below_header.grid_columnconfigure(0, weight=80) # As per your file
        main_content_below_header.grid_columnconfigure(1, weight=20) # As per your file
        main_content_below_header.grid_rowconfigure(0, weight=1)

        teams_outer_frame = tk.Frame(main_content_below_header, bg=THEME_BG_SECONDARY, bd=0, relief=tk.FLAT)
        teams_outer_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        teams_outer_frame.rowconfigure(1, weight=1); teams_outer_frame.columnconfigure(0, weight=1)
        tk.Label(teams_outer_frame, text="🏆 TEAMS OVERVIEW", font=get_font(16, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY, pady=10, padx=10, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        self.teams_canvas = tk.Canvas(teams_outer_frame, bg=THEME_BG_SECONDARY, highlightthickness=0)
        self.teams_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))

        teams_scrollbar_style = ttk.Style(self) # Use self.master or self for style parent
        teams_scrollbar_style.layout("Teams.Vertical.TScrollbar", [('Teams.Vertical.TScrollbar.trough', {'sticky': 'ns'}), ('Vertical.Scrollbar.uparrow', {'side': 'top', 'sticky': ''}), ('Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': ''}), ('Vertical.Scrollbar.thumb', {'sticky': 'ns', 'expand': 1})])
        teams_scrollbar_style.configure("Teams.Vertical.TScrollbar", gripcount=0, background=THEME_BG_CARD, troughcolor=THEME_BG_SECONDARY, bordercolor=THEME_BG_SECONDARY, arrowcolor=THEME_TEXT_PRIMARY, arrowsize=14, relief=tk.FLAT, width=16)
        teams_scrollbar_style.map("Teams.Vertical.TScrollbar", background=[('active', THEME_HIGHLIGHT_BG), ('!active', THEME_BG_CARD)], arrowcolor=[('pressed', THEME_ACCENT_PRIMARY), ('!pressed', THEME_TEXT_PRIMARY)])
        teams_scrollbar = ttk.Scrollbar(teams_outer_frame, orient="vertical", command=self.teams_canvas.yview, style="Teams.Vertical.TScrollbar")
        teams_scrollbar.grid(row=1, column=1, sticky="ns")
        self.teams_canvas.configure(yscrollcommand=teams_scrollbar.set)
        self.scrollable_teams_frame = tk.Frame(self.teams_canvas, bg=THEME_BG_SECONDARY)
        self.teams_canvas_window_id = self.teams_canvas.create_window((0,0), window=self.scrollable_teams_frame, anchor="nw")
        self.scrollable_teams_frame.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind_all("<MouseWheel>", self._on_mousewheel_teams)
        self.teams_canvas.bind_all("<Button-4>", self._on_mousewheel_teams)
        self.teams_canvas.bind_all("<Button-5>", self._on_mousewheel_teams)
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

    def _toggle_presenter_view(self):
        if PresenterWindow is None:
            messagebox.showwarning("Presenter Mode Unavailable", "The presenter view component could not be loaded.", parent=self)
            return

        if self.presenter_window is None or not self.presenter_window.winfo_exists():
            self.presenter_window = PresenterWindow(self.master, auction_name=self.engine.get_auction_name())
            self.presenter_window_visible = True
            self.presenter_window.protocol("WM_DELETE_WINDOW", self._on_presenter_close)
            self._update_presenter_full_state()
        elif self.presenter_window_visible:
            self.presenter_window.withdraw()
            self.presenter_window_visible = False
        else:
            self.presenter_window.deiconify()
            self.presenter_window_visible = True
            self._update_presenter_full_state()

    def _on_presenter_close(self):
        if self.presenter_window:
            self.presenter_window.destroy()
        self.presenter_window = None
        self.presenter_window_visible = False
        # Optionally update menu item if it shows state: self.menu_bar.update_presenter_toggle_text()

    def _handle_load_selected_state_from_history(self, json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no):
        success, message = self.engine.load_state_from_json_string(json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no)
        if success:
            self.refresh_all_ui_displays() # This will update admin and trigger presenter update
            messagebox.showinfo("State Loaded", message, parent=self)
        else:
            messagebox.showerror("Load Error", message, parent=self)
        self._check_and_display_engine_warnings("Warning during state load from history:")

    def _on_mousewheel_teams(self, event):
        # ... (No changes from your provided code) ...
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


    def _create_team_cards_layout(self): # Admin panel has no images
        for widget in self.scrollable_teams_frame.winfo_children(): widget.destroy()
        self.money_labels.clear(); self.inventory_listboxes.clear(); self.team_card_frames.clear()
        self.scrollable_teams_frame.grid_columnconfigure(0, weight=1); self.scrollable_teams_frame.grid_columnconfigure(1, weight=1)
        all_teams_data = self.engine.get_all_team_data(); row_num, col_num = 0, 0
        for team_info in all_teams_data:
            team_name = team_info["name"]
            card = tk.Frame(self.scrollable_teams_frame, bg=THEME_BG_CARD, padx=15, pady=12, relief=tk.FLAT, bd=0); card.configure(highlightbackground=THEME_BORDER_COLOR_LIGHT, highlightthickness=1); card.grid(row=row_num, column=col_num, sticky="ew", padx=5, pady=8); self.team_card_frames[team_name] = card
            
            header_info_frame = tk.Frame(card,bg=THEME_BG_CARD); header_info_frame.pack(fill=tk.X, pady=(0,8))
            # No logo in admin panel
            tk.Label(header_info_frame,text=team_name.upper(),font=get_font(16,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_PRIMARY,anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True) # Name expands
            money_label=tk.Label(header_info_frame,text="₹0",font=get_font(15,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_TERTIARY,anchor="e"); money_label.pack(side=tk.RIGHT); self.money_labels[team_name]=money_label
            
            tk.Label(card,text="INVENTORY:",font=get_font(10,"bold"), bg=THEME_BG_CARD,fg=THEME_TEXT_SECONDARY,anchor="w").pack(fill=tk.X,pady=(5,2))
            inventory_listbox=tk.Listbox(card,font=get_font(10),height=3,relief=tk.FLAT,bd=0, bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, selectbackground=THEME_ACCENT_PRIMARY, selectforeground=THEME_TEXT_ACCENT, highlightthickness=0, activestyle="none"); inventory_listbox.pack(fill=tk.X,expand=True,pady=(0,10)); self.inventory_listboxes[team_name]=inventory_listbox
            StyledButton(card,text="BID NOW 💸",font=get_font(12, "bold"), bg=THEME_ACCENT_PRIMARY,fg=THEME_TEXT_ACCENT, command=lambda t=team_name: self.ui_place_bid(t), pady=10).pack(fill=tk.X)
            
            col_num += 1;
            if col_num >= 2: col_num = 0; row_num += 1
        self.scrollable_teams_frame.update_idletasks()
        if self.teams_canvas.winfo_exists(): self.teams_canvas.config(scrollregion=self.teams_canvas.bbox("all"))

    def update_team_cards_display(self): # Admin panel has no images
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
        # ... (No changes from your provided code - admin list is text-based) ...
        if hasattr(self,'item_list_text') and self.item_list_text.winfo_exists():
            self.item_list_text.config(state=tk.NORMAL); self.item_list_text.delete("1.0", tk.END)
            available_players = self.engine.get_available_players_info() # This getter in engine should not return image paths for admin UI
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

    def update_bidding_status_display(self): # Admin panel has no current player image
        status = self.engine.get_current_bidding_status_display()
        self.current_item_label.config(text=status["item_display_name"])
        fg_color = THEME_TEXT_SECONDARY
        if status["status_color_key"] == "SUCCESS": fg_color = THEME_ACCENT_TERTIARY
        elif status["status_color_key"] == "WARNING": fg_color = THEME_ACCENT_SECONDARY
        self.bid_status_label.config(text=status["status_text"], fg=fg_color)
        self.auction_name_label.config(text=self.engine.get_auction_name().upper())

    def refresh_all_ui_displays(self):
        self.update_team_cards_display()
        self.update_available_players_display()
        self.update_bidding_status_display()
        self._update_presenter_full_state() # Crucial for presenter sync

    def _update_presenter_full_state(self):
        """Updates the entire presenter window based on current engine state."""
        if not self.presenter_window or not self.presenter_window.winfo_exists() or not self.presenter_window_visible:
            return

        self.presenter_window.update_auction_name_display(self.engine.get_auction_name())

        if self.engine.bidding_active and self.engine.current_item_name:
            current_player_name = self.engine.current_item_name
            player_data = self.engine.players_initial_info.get(self.engine.current_item_name)
            player_photo_path = player_data.get(PLAYER_PHOTO_PATH_KEY) if player_data else None
            
           # <<< --- ADD DEBUG PRINT HERE --- >>>
            print(f"DEBUG AuctionApp _update_presenter: Player '{current_player_name}', Photo Path from engine: '{player_photo_path}'") 
            
            
            self.presenter_window.update_current_item(
                self.engine.current_item_name,
                player_photo_path,
                self.engine.current_item_base_bid
            )
            highest_bidder_name = self.engine.highest_bidder_name
            bidder_logo_path = None
            if highest_bidder_name:
                team_data = self.engine.teams_data.get(highest_bidder_name)
                bidder_logo_path = team_data.get(TEAM_LOGO_PATH_KEY) if team_data else None
            
                # <<< --- ADD DEBUG PRINT HERE --- >>>
                print(f"DEBUG AuctionApp _update_presenter: Bidder '{highest_bidder_name}', Logo Path from engine: '{bidder_logo_path}'")
            
            self.presenter_window.update_bid_status(
                highest_bidder_name, bidder_logo_path,
                self.engine.current_bid_amount, bool(highest_bidder_name)
            )
            self._presenter_last_action_sell_pass = False # Reset flag
        else:
            # If not actively bidding, but the last action was a sell/pass, presenter shows that.
            # Otherwise, clear it.
            if not self._presenter_last_action_sell_pass:
                 self.presenter_window.clear_current_item()
            # This flag will be set to False again if a new item is selected or bid happens
            # or at the start of the next _update_presenter_full_state if nothing changes.

    def _check_and_display_engine_warnings(self, context_message="Engine Warning(s):"):
        # ... (No changes from your provided code) ...
        warnings = self.engine.get_last_errors_and_clear()
        if warnings:
            full_warning_message = context_message + "\n - " + "\n - ".join(warnings)
            messagebox.showwarning("Auction Engine Notice", full_warning_message, parent=self)

    def ui_select_item(self, player_name):
        try:
            current_status = self.engine.get_current_bidding_status_display()
            if current_status["bidding_active"] and self.engine.highest_bidder_name:
                 if not messagebox.askyesno("Confirm Item Change", f"'{self.engine.current_item_name}' active with bids. Change? Current item passes.", icon='warning', parent=self): return

            prev_item_name_for_presenter = self.engine.current_item_name # Get before engine state changes
            passed_message = self.engine.select_item_for_bidding(player_name) # Engine updates

            if passed_message: # If an item was auto-passed
                messagebox.showinfo("Item Auto-Passed", passed_message, parent=self)
                if self.presenter_window_visible and self.presenter_window:
                    self.presenter_window.clear_current_item(passed=True, item_name=prev_item_name_for_presenter)
                    self._presenter_last_action_sell_pass = True
            else: # New item selected, no auto-pass
                 self._presenter_last_action_sell_pass = False

        except AuctionError as e: messagebox.showerror("Selection Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays() # This calls _update_presenter_full_state
            self._check_and_display_engine_warnings()

    def ui_place_bid(self, team_name):
        try:
            self.engine.place_bid(team_name)
            self._presenter_last_action_sell_pass = False # A bid means we are in active bidding
        except AuctionError as e: messagebox.showerror("Bid Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays()
            self._check_and_display_engine_warnings()

    def ui_undo_last_bid(self):
        try:
            self.engine.undo_last_bid()
            self._presenter_last_action_sell_pass = False # Undoing a bid, still in active bidding
        except AuctionError as e: messagebox.showerror("Undo Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays()
            self._check_and_display_engine_warnings()

    def ui_sell_item(self):
        try:
            item_name, winner, bid, message = self.engine.sell_current_item()
            messagebox.showinfo("Item Sold", message, parent=self)
            if self.presenter_window_visible and self.presenter_window:
                player_data = self.engine.players_initial_info.get(item_name)
                player_photo_path = player_data.get(PLAYER_PHOTO_PATH_KEY) if player_data else None
                team_data = self.engine.teams_data.get(winner)
                team_logo_path = team_data.get(TEAM_LOGO_PATH_KEY) if team_data else None
                self.presenter_window.show_item_sold(item_name, player_photo_path, winner, team_logo_path, bid)
                self._presenter_last_action_sell_pass = True
        except AuctionError as e: messagebox.showerror("Sell Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays()
            self._check_and_display_engine_warnings()

    def ui_pass_item(self):
        try:
            passed_item_name_for_presenter = self.engine.current_item_name
            if self.engine.bidding_active and passed_item_name_for_presenter and self.engine.highest_bidder_name:
                 if not messagebox.askyesno("Confirm Pass", f"'{passed_item_name_for_presenter}' has bids. Pass anyway?", icon='warning', parent=self): return
            passed_item_name = self.engine.pass_current_item()
            messagebox.showinfo("Item Passed", f"'{passed_item_name}' passed/unsold.", parent=self)
            if self.presenter_window_visible and self.presenter_window:
                self.presenter_window.clear_current_item(passed=True, item_name=passed_item_name)
                self._presenter_last_action_sell_pass = True
        except AuctionError as e: messagebox.showerror("Pass Error", str(e), parent=self)
        finally:
            self.refresh_all_ui_displays()
            self._check_and_display_engine_warnings()

    def on_app_frame_closing(self):
        if self.engine: self.engine.close_logger()
        if self.presenter_window and self.presenter_window.winfo_exists():
            self.presenter_window.destroy()
            self.presenter_window = None

def main():
    # ... (No changes from your provided code, includes the handle_resume_auction_logic) ...
    root = tk.Tk(); root.title("Auction Command"); root.geometry("1300x850"); root.configure(bg=THEME_BG_PRIMARY)
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
            clear_current_page(); current_page_widget = InitialPage(root, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), handle_resume_auction_logic); current_page_widget.pack(fill="both", expand=True) # Make sure handle_resume_auction_logic is defined if used here from previous step
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
    def handle_resume_auction_logic(): # From previous step
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