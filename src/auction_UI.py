# --- auction.py ---
import tkinter as tk
from tkinter import ttk 
from tkinter import filedialog, messagebox, scrolledtext, font as tkFont
import os
import re 
import csv 
import json 
from datetime import datetime 

from auction_engine import (
    AuctionEngine, AuctionError, InsufficientFundsError, 
    ItemNotSelectedError, InvalidBidError, NoBidsError, 
    LogFileError, InitializationError, generate_template_csv_content
)

# Constants from engine if needed by UI directly (e.g. LogViewer parsing)
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
    except tk.TclError: return tkFont.Font(family=FONT_FAMILY_FALLBACK, size=size, weight=weight, slant=slant)

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
    widget.bind("<Enter>", on_enter); widget.bind("<Leave>", on_leave)

class StyledButton(tk.Button):
    def __init__(self, master=None, cnf={}, **kw):
        default_style = { "font": get_font(11, "bold"), "relief": tk.FLAT, "pady": 8, "padx": 12, "borderwidth": 0, "activebackground": kw.get("bg", SECONDARY_BUTTON_BG), "activeforeground": kw.get("fg", SECONDARY_BUTTON_FG) }
        final_cnf = {**default_style, **cnf, **kw}
        super().__init__(master, **final_cnf)
        self.original_bg = self.cget("background"); self.original_fg = self.cget("foreground")
        if self.original_bg == PRIMARY_BUTTON_BG: self.hover_bg, self.hover_fg = HOVER_BG_COLOR_PRIMARY, PRIMARY_BUTTON_FG 
        elif self.original_bg == THEME_ACCENT_SECONDARY: self.hover_bg, self.hover_fg = "#d35400", THEME_TEXT_ACCENT
        elif self.original_bg == THEME_ACCENT_TERTIARY: self.hover_bg, self.hover_fg = "#27ae60", THEME_TEXT_ACCENT
        else: self.hover_bg, self.hover_fg = HOVER_BG_COLOR_SECONDARY, self.original_fg 
        self.bind("<Enter>", self._on_enter); self.bind("<Leave>", self._on_leave)
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

        # --- CSV Template Hyperlink ---
        csv_info_frame = tk.Frame(container, bg=THEME_BG_PRIMARY)
        csv_info_frame.pack(pady=(20,0), fill=tk.X)

        tk.Label(csv_info_frame, text="Select Initial Setup File (.csv):", font=get_font(14), bg=THEME_BG_PRIMARY, fg=THEME_TEXT_PRIMARY).pack(side=tk.LEFT, anchor="w")

        template_hyperlink_font = get_font(10, slant="italic") # Basic font
        self.template_link_button = tk.Button(
            csv_info_frame,
            text="View .csv format help",
            font=template_hyperlink_font,
            fg=THEME_ACCENT_PRIMARY, # Blue color like a link
            bg=THEME_BG_PRIMARY,    # Match background
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            activeforeground=HOVER_BG_COLOR_PRIMARY, # Darker blue on click
            activebackground=THEME_BG_PRIMARY,
            command=self._generate_and_save_template
        )
        self.template_link_button.pack(side=tk.RIGHT, padx=(10,0), anchor="e")

        # Simple hover effect for underline (optional but nice for hyperlinks)
        default_font_no_underline = get_font(10, slant="italic")
        hover_font_underline = get_font(10, slant="italic", weight="normal") # Underline doesn't work well with italic in some Tk versions
                                                                             # Let's try a subtle weight change or color change
        hover_font_underline_actual = tkFont.Font(family=default_font_no_underline.cget("family"),
                                                  size=default_font_no_underline.cget("size"),
                                                  slant=default_font_no_underline.cget("slant"),
                                                  underline=True)


        def on_link_enter(e):
            self.template_link_button.config(font=hover_font_underline_actual, fg=HOVER_BG_COLOR_PRIMARY)
        def on_link_leave(e):
            self.template_link_button.config(font=default_font_no_underline, fg=THEME_ACCENT_PRIMARY)

        self.template_link_button.bind("<Enter>", on_link_enter)
        self.template_link_button.bind("<Leave>", on_link_leave)
        # --- End CSV Template Hyperlink ---

        StyledButton(container, text="BROWSE SETUP FILE", command=self.browse_csv_file, font=get_font(12, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, pady=10, padx=15).pack(pady=10, fill=tk.X)

    def _generate_and_save_template(self):
        template_content = generate_template_csv_content()
        filename = "auction_setup_template.csv"
        filepath = os.path.join(os.getcwd(), filename)

        try:
            with open(filepath, "w", newline='', encoding='utf-8') as f:
                f.write(template_content)
            messagebox.showinfo(
                "Template Generated",
                f"'{filename}' has been created in your current working directory:\n\n{os.getcwd()}",
                parent=self
            )
        except IOError as e:
            messagebox.showerror(
                "Error Saving Template",
                f"Could not save the template file '{filename}':\n{e}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                "Unexpected Error",
                f"An unexpected error occurred while generating the template:\n{e}",
                parent=self
            )
    def browse_csv_file(self):
        file_path = filedialog.askopenfilename(title="Select Setup CSV File", filetypes=[("CSV files", "*.csv")])
        if not file_path: return
        
        teams_list, players_list, bid_increment_rules_list = [], [], []
        # Flags to ensure headers are found once per relevant section
        parsed_team_header, parsed_player_header = False, False 
        current_parsing_section = None # None, "CONFIG", "TEAMS", "PLAYERS", "BID_RULES"
        file_line_num_for_error = 0 # For more accurate error reporting

        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                for file_line_num, row in enumerate(reader, 1):
                    file_line_num_for_error = file_line_num 
                    
                    # Skip fully empty rows
                    if not any(field.strip() for field in row):
                        continue

                    # Use the first cell (stripped) for most checks
                    # but keep original 'row' for accessing multiple columns
                    first_cell_stripped = row[0].strip() 

                    # Section Detection
                    if first_cell_stripped.lower() == LOG_SECTION_CONFIG.lower():
                        current_parsing_section = "CONFIG"
                        continue # Move to next line after identifying section
                    elif first_cell_stripped.lower() == LOG_SECTION_TEAMS_INITIAL.lower():
                        current_parsing_section = "TEAMS"
                        parsed_team_header = False # Reset header flag for this section
                        continue
                    elif first_cell_stripped.lower() == LOG_SECTION_PLAYERS_INITIAL.lower():
                        current_parsing_section = "PLAYERS"
                        parsed_player_header = False # Reset header flag for this section
                        continue
                    elif first_cell_stripped.lower() == LOG_SECTION_BID_INCREMENT_RULES.lower():
                        current_parsing_section = "BID_RULES"
                        # No specific header flag needed here as "Threshold,Increment" is also data-like
                        continue
                    
                    # Data Parsing based on current_parsing_section
                    if current_parsing_section == "CONFIG":
                        if first_cell_stripped.startswith('#'):  # Skip comments in config section
                            continue
                        # Example: AuctionName,MyAuction
                        if CSV_DELIMITER in first_cell_stripped: 
                             # Use first_cell_stripped which is row[0].strip() for key-value
                             # if config values are only in the first cell.
                             # If value can be in row[1], adjust accordingly.
                             key_value_pair = first_cell_stripped.split(CSV_DELIMITER, 1)
                             if len(key_value_pair) == 2: # Ensure it's a pair
                                key, value = key_value_pair[0].strip(), key_value_pair[1].strip()
                                if key == LOG_KEY_AUCTION_NAME:
                                     self.auction_name_entry.delete(0, tk.END)
                                     self.auction_name_entry.insert(0, value)
                        # Add more specific config item parsing here if needed

                    elif current_parsing_section == "TEAMS":
                        if not parsed_team_header:
                            if first_cell_stripped.startswith('#'): # Skip comment lines when looking for header
                                continue 
                            # Check for the specific team header
                            if not (len(row) >= 2 and first_cell_stripped.lower() == "team name" and row[1].strip().lower() == "team starting money"):
                                messagebox.showerror("Format Error", f"Invalid team header (L{file_line_num}). Expected 'Team name,Team starting money'."); return
                            parsed_team_header = True
                            continue # Header found, move to next line for data
                        
                        # If header is parsed, now parsing actual team data lines
                        if first_cell_stripped.startswith('#'): # Skip comment lines in the data part of the section
                            continue 
                        
                        if len(row) >= 2:
                            name, money_str = row[0].strip(), row[1].strip() 
                            if not name: 
                                messagebox.showerror("Data Error", f"Team name cannot be empty (L{file_line_num})."); return
                            try:
                                teams_list.append({"Team name": name, "Team starting money": int(money_str)})
                            except ValueError:
                                messagebox.showerror("Data Error", f"Invalid money value for team '{name}' (L{file_line_num}): '{money_str}'. Must be an integer."); return
                        else: 
                            # This means the line is not a comment, and not a valid team data row (e.g. only 1 column)
                            messagebox.showerror("Format Error", f"Malformed team data (L{file_line_num}). Each team entry requires a name and starting money."); return

                    elif current_parsing_section == "PLAYERS":
                        if not parsed_player_header:
                            if first_cell_stripped.startswith('#'): 
                                continue
                            if not (len(row) >= 2 and first_cell_stripped.lower() == "player name" and row[1].strip().lower() == "bid value"):
                                messagebox.showerror("Format Error", f"Invalid player header (L{file_line_num}). Expected 'Player name,Bid value'."); return
                            parsed_player_header = True
                            continue
                        
                        if first_cell_stripped.startswith('#'): 
                            continue 
                        
                        if len(row) >= 2:
                            name, bid_str = row[0].strip(), row[1].strip()
                            if not name:
                                messagebox.showerror("Data Error", f"Player name cannot be empty (L{file_line_num})."); return
                            try:
                                players_list.append({"Player name": name, "Bid value": int(bid_str)})
                            except ValueError:
                                messagebox.showerror("Data Error", f"Invalid bid value for player '{name}' (L{file_line_num}): '{bid_str}'. Must be an integer."); return
                        else:
                            messagebox.showerror("Format Error", f"Malformed player data (L{file_line_num}). Each player entry requires a name and bid value."); return

                    elif current_parsing_section == "BID_RULES":
                        if first_cell_stripped.startswith('#'): # Skip any general comment line first
                            continue
                        
                        # Explicitly check for and skip the "Threshold,Increment" data header if present
                        if len(row) >= 2 and \
                           first_cell_stripped.lower() == "threshold" and \
                           row[1].strip().lower() == "increment":
                            continue # It's the data header for rules, skip it

                        # Now parse actual numerical rule lines
                        try:
                            if len(row) >= 2:
                                threshold_str, increment_str = row[0].strip(), row[1].strip()
                                # Skip if the line becomes fully empty after stripping (e.g. just ", ")
                                if not threshold_str and not increment_str:
                                    continue 
                                
                                threshold = int(threshold_str)
                                increment = int(increment_str)
                                
                                if threshold < 0 or increment <= 0:
                                    messagebox.showerror("Data Error", f"Bid Increment Rule Error (L{file_line_num}): Threshold must be >=0, Increment >0. Got: {threshold}, {increment}"); return
                                bid_increment_rules_list.append((threshold, increment))
                            # If the line is not a comment, not the header, not empty, but also not 2 columns, it's an error for a rule.
                            elif any(field.strip() for field in row): # Check if the row has any content at all
                                 messagebox.showerror("Format Error", f"Malformed bid increment rule (L{file_line_num}). Expected 2 columns (Threshold, Increment), a comment, or the 'Threshold,Increment' header."); return
                        except ValueError:
                            # This will catch if int() fails for non-numeric threshold/increment values
                            messagebox.showerror("Data Error", f"Invalid number in bid increment rule (L{file_line_num}): '{row[0].strip()}', '{row[1].strip()}'. Ensure values are numeric."); return
            
            # --- After processing all lines ---
            if not teams_list:
                messagebox.showerror("Data Error", "No team data was parsed. Please ensure the [TEAMS_INITIAL] section and its data are correctly formatted in the CSV file."); return
            if not players_list:
                messagebox.showerror("Data Error", "No player data was parsed. Please ensure the [PLAYERS_INITIAL] section and its data are correctly formatted in the CSV file."); return
            
            auction_name_input = self.auction_name_entry.get().strip()
            if not auction_name_input:
                messagebox.showerror("Input Error", "Auction Name cannot be empty."); return
            
            # Pass the parsed data to the callback. If bid_increment_rules_list is empty, engine uses defaults.
            self.on_file_loaded_data(teams_list, players_list, auction_name_input, bid_increment_rules_list if bid_increment_rules_list else None)

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e:
            # Catch any other unexpected errors during parsing
            messagebox.showerror("CSV Loading Error", f"An unexpected error occurred while parsing the CSV file (near line {file_line_num_for_error}):\n{type(e).__name__}: {e}")

class FileSelectPageForResume(FileSelectPage):
    def __init__(self, master, on_log_file_selected_for_resume):
        super().__init__(master, on_file_loaded_data=None, title="RESUME AUCTION")
        self.on_log_file_selected_for_resume = on_log_file_selected_for_resume
        container_frame = self.winfo_children()[0]
        widgets_to_remove_texts = ["Auction Name:", "Select Initial Setup File (.csv):", "BROWSE SETUP FILE"]
        for widget in list(container_frame.winfo_children()):
            if isinstance(widget, tk.Entry): widget.destroy()
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
    def browse_csv_file(self): pass # Override parent

class LogViewerDialog(tk.Toplevel):
    def __init__(self, master, log_filepath, load_state_callback):
        super().__init__(master)
        self.log_filepath = log_filepath
        self.load_state_callback = load_state_callback
        self.title("Auction Log History Viewer")
        self.geometry("1200x750") # Using the increased width from previous change
        self.configure(bg=THEME_BG_PRIMARY)
        self.grab_set()
        self.focus_set()

        style = ttk.Style(self)
        # ... (style configurations remain the same) ...
        style.configure("Treeview", background=THEME_BG_SECONDARY, foreground=THEME_TEXT_PRIMARY, fieldbackground=THEME_BG_SECONDARY, font=get_font(10), rowheight=get_font(10).metrics('linespace') + 6)
        style.configure("Treeview.Heading", font=get_font(11, "bold"), background=THEME_BG_CARD, foreground=THEME_ACCENT_PRIMARY, relief=tk.FLAT, borderwidth=0)
        style.map("Treeview.Heading", background=[('active', THEME_HIGHLIGHT_BG)])
        style.map("Treeview", background=[('selected', THEME_ACCENT_PRIMARY)], foreground=[('selected', THEME_TEXT_ACCENT)])

        top_controls_frame = tk.Frame(self, bg=THEME_BG_PRIMARY)
        top_controls_frame.pack(pady=(10,0), padx=10, fill="x")
        StyledButton(top_controls_frame, text="🔄 REFRESH", command=self.populate_log_tree, font=get_font(10, "bold"), bg=SECONDARY_BUTTON_BG, fg=SECONDARY_BUTTON_FG, padx=10, pady=5).pack(side="left", padx=(0,10))
        self.load_button = StyledButton(top_controls_frame, text="✔️ LOAD SELECTED STATE", command=self.on_load_selected_state, font=get_font(10, "bold"), bg=PRIMARY_BUTTON_BG, fg=PRIMARY_BUTTON_FG, padx=10, pady=5, state=tk.DISABLED)
        self.load_button.pack(side="left")
        StyledButton(top_controls_frame, text="✖ CLOSE", command=self.destroy, font=get_font(10, "bold"), bg=THEME_ACCENT_SECONDARY, fg=THEME_TEXT_ACCENT, padx=10, pady=5).pack(side="right")

        tree_frame = tk.Frame(self, bg=THEME_BG_PRIMARY)
        tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
        # ... (Treeview and scrollbar setup remains the same) ...
        cols = ("No.", "Timestamp", "Action Description", "Comment"); self.log_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col_name in cols: self.log_tree.heading(col_name, text=col_name)
        self.log_tree.column("No.", width=60, minwidth=50, stretch=tk.NO, anchor="center"); self.log_tree.column("Timestamp", width=180, minwidth=160, anchor="w")
        self.log_tree.column("Action Description", width=380, minwidth=250, anchor="w"); self.log_tree.column("Comment", width=300, minwidth=200, anchor="w")
        tree_ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_tree.yview, style="Vertical.TScrollbar"); tree_xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.log_tree.xview, style="Horizontal.TScrollbar")
        self.log_tree.configure(yscrollcommand=tree_ysb.set, xscrollcommand=tree_xsb.set)
        style.configure("Vertical.TScrollbar", gripcount=0, background=THEME_BG_CARD, darkcolor=THEME_BG_SECONDARY, lightcolor=THEME_BG_SECONDARY, troughcolor=THEME_BG_PRIMARY, bordercolor=THEME_BG_PRIMARY, arrowcolor=THEME_TEXT_PRIMARY, arrowsize=14, relief=tk.FLAT, width=16)
        style.map("Vertical.TScrollbar",
            background=[('active', THEME_HIGHLIGHT_BG), ('!active', THEME_BG_CARD)],
            arrowcolor=[('pressed', THEME_ACCENT_PRIMARY), ('!pressed', THEME_TEXT_PRIMARY)]
        )
        style.configure("Horizontal.TScrollbar", 
            gripcount=0, 
            background=THEME_BG_CARD,
            darkcolor=THEME_BG_SECONDARY,   
            lightcolor=THEME_BG_SECONDARY,  
            troughcolor=THEME_BG_PRIMARY,
            bordercolor=THEME_BG_PRIMARY,
            arrowcolor=THEME_TEXT_PRIMARY, 
            arrowsize=14,
            relief=tk.FLAT,
            height=16       
        )
        style.map("Horizontal.TScrollbar",
            background=[('active', THEME_HIGHLIGHT_BG), ('!active', THEME_BG_CARD)],
            arrowcolor=[('pressed', THEME_ACCENT_PRIMARY), ('!pressed', THEME_TEXT_PRIMARY)]
        )

        tree_ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_tree.yview, style="Vertical.TScrollbar")
        tree_xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.log_tree.xview, style="Horizontal.TScrollbar") # Apply the style
        
        self.log_tree.configure(yscrollcommand=tree_ysb.set, xscrollcommand=tree_xsb.set)
        
        tree_ysb.pack(side="right", fill="y"); tree_xsb.pack(side="bottom", fill="x"); self.log_tree.pack(side="left", fill="both", expand=True)

        self.log_tree.bind("<<TreeviewSelect>>", self.on_log_entry_select)
        self.log_data_store = []

        # --- JSON Display Section ---
        # Frame to hold the toggle button for the JSON display
        self.json_control_frame = tk.Frame(self, bg=THEME_BG_PRIMARY)
        self.json_control_frame.pack(pady=(5,0), padx=10, fill="x")

        self.toggle_json_button = StyledButton(
            self.json_control_frame,
            text="Show JSON Details ►", # Initial text
            command=self._toggle_json_display,
            font=get_font(10, "bold"),
            bg=SECONDARY_BUTTON_BG, # Or THEME_BG_CARD
            fg=THEME_TEXT_PRIMARY,
            padx=10,
            pady=5
        )
        self.toggle_json_button.pack(side="left")
        
        self.json_visible = False # State for the toggle

        # This frame will be shown/hidden
        self.json_display_frame = tk.Frame(self, bg=THEME_BG_SECONDARY, bd=0, relief=tk.FLAT)
        # Note: self.json_display_frame is NOT packed here initially, it's packed by _toggle_json_display

        tk.Label(self.json_display_frame, text="SELECTED STATE SNAPSHOT (JSON):", font=get_font(11, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY).pack(anchor="nw", padx=10, pady=(10,5))
        self.json_text = scrolledtext.ScrolledText(self.json_display_frame, height=10, font=get_font(10), wrap=tk.WORD, relief=tk.FLAT, bd=0, insertbackground=THEME_TEXT_PRIMARY, bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, highlightthickness=0)
        self.json_text.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.json_text.configure(state=tk.DISABLED)
        
        self.populate_log_tree()

    def _toggle_json_display(self):
        if self.json_visible:
            # Hide it
            self.json_display_frame.pack_forget()
            self.toggle_json_button.config(text="Show JSON Details ►")
            self.json_visible = False
        else:
            # Show it
            # Pack it below the json_control_frame (which is already packed)
            self.json_display_frame.pack(pady=(0,10), padx=10, fill="both", expand=True)
            self.toggle_json_button.config(text="Hide JSON Details ▼")
            self.json_visible = True
            # self.update_idletasks() # May not be strictly necessary but can help ensure layout updates

    def populate_log_tree(self):
        for i in self.log_tree.get_children(): self.log_tree.delete(i)
        self.log_data_store.clear()
        self.json_text.config(state=tk.NORMAL)
        self.json_text.delete("1.0", tk.END)
        self.json_text.config(state=tk.DISABLED)
        self.load_button.config(state=tk.DISABLED)

        # Reset JSON visibility on refresh
        if self.json_visible:
            self.json_display_frame.pack_forget()
            self.toggle_json_button.config(text="Show JSON Details ►")
            self.json_visible = False
            
        serial_no_counter = 1
        # ... (rest of the populate_log_tree method remains the same) ...
        try:
            if not os.path.exists(self.log_filepath): messagebox.showerror("Log Error", f"Not found: {self.log_filepath}", parent=self); return
            with open(self.log_filepath, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f); in_states_section = False
                for row_num, row in enumerate(reader): 
                    if not row: continue
                    try: first_cell = row[0].strip()
                    except IndexError: continue 
                    if first_cell == LOG_SECTION_AUCTION_STATES:
                        in_states_section = True; next(reader, None); continue # Skip header of states
                    if in_states_section and not first_cell.startswith('#'):
                        if len(row) >= 3:
                            timestamp, action_desc, json_str = row[0], row[1], row[2]; comment = row[3] if len(row) > 3 else ""
                            iid_val = str(serial_no_counter) 
                            self.log_tree.insert("", "end", values=(serial_no_counter, timestamp, action_desc, comment), iid=iid_val)
                            self.log_data_store.append({'iid': iid_val, 'serial_no': serial_no_counter, 'ts': timestamp, 'action': action_desc, 'json': json_str, 'comment': comment})
                            serial_no_counter += 1 
        except Exception as e: messagebox.showerror("Log Error", f"Reading log: {e}", parent=self)


    def on_log_entry_select(self, event): # Logic same
        # ... (this method remains the same, it just populates self.json_text) ...
        selected_item_iid = self.log_tree.focus() 
        if not selected_item_iid: 
            self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.config(state=tk.DISABLED)
            self.load_button.config(state=tk.DISABLED)
            return
        selected_data = next((item for item in self.log_data_store if item['iid'] == selected_item_iid), None)
        if selected_data:
            try:
                parsed_json = json.loads(selected_data['json']); pretty_json = json.dumps(parsed_json, indent=2)
                self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.insert("1.0", pretty_json); self.json_text.config(state=tk.DISABLED)
                self.load_button.config(state=tk.NORMAL)
            except json.JSONDecodeError: 
                self.json_text.config(state=tk.NORMAL); self.json_text.delete("1.0", tk.END); self.json_text.insert("1.0", "Error: Invalid JSON."); self.json_text.config(state=tk.DISABLED)
                self.load_button.config(state=tk.DISABLED)
        else: 
            self.load_button.config(state=tk.DISABLED)

    def on_load_selected_state(self): # Logic same
        # ... (this method remains the same) ...
        selected_item_iid = self.log_tree.focus()
        if not selected_item_iid: messagebox.showwarning("No Selection", "Select log entry.", parent=self); return
        selected_data = next((item for item in self.log_data_store if item['iid'] == selected_item_iid), None)
        if selected_data and messagebox.askyesno("Confirm Load", f"Load state from No. {selected_data['serial_no']}?", parent=self, icon='warning'):
            self.load_state_callback(selected_data['json'], selected_data['ts'], selected_data['action'], selected_data['serial_no']); self.destroy()

class AuctionApp(tk.Frame): # No changes needed here from previous full version
    def __init__(self, master, auction_engine_instance):
        super().__init__(master, bg=THEME_BG_PRIMARY); self.pack(fill="both", expand=True, padx=10, pady=10)
        self.engine = auction_engine_instance; self.team_card_frames = {}; self.money_labels = {}; self.inventory_listboxes = {}
        self._setup_ui(); self.refresh_all_ui_displays()

    def _setup_ui(self):
        header_frame = tk.Frame(self, bg=THEME_BG_SECONDARY, padx=15, pady=10); header_frame.pack(fill=tk.X, pady=(0,10), side=tk.TOP)
        header_left = tk.Frame(header_frame, bg=THEME_BG_SECONDARY); header_left.pack(side=tk.LEFT)
        self.auction_name_label = tk.Label(header_left, text=self.engine.get_auction_name().upper(), font=get_font(18, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY); self.auction_name_label.pack(side=tk.LEFT, padx=(0,20))
        self.view_log_button = StyledButton(header_left, text="🕒 LOGS", command=self._open_log_viewer, font=get_font(10, "bold"), bg=THEME_BG_CARD, fg=THEME_TEXT_PRIMARY, padx=10, pady=5); self.view_log_button.pack(side=tk.LEFT, padx=(0,20))
        header_right = tk.Frame(header_frame, bg=THEME_BG_SECONDARY); header_right.pack(side=tk.RIGHT)
        tk.Label(header_right, text="STATUS:", font=get_font(10, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_SECONDARY).pack(side=tk.LEFT)
        self.bid_status_label = tk.Label(header_right, text="INITIALIZING", font=get_font(14, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_SECONDARY, anchor="e"); self.bid_status_label.pack(side=tk.LEFT, padx=5)
        self.current_item_display_frame = tk.Frame(header_frame, bg=THEME_BG_SECONDARY); self.current_item_display_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10,10)) 
        tk.Label(self.current_item_display_frame, text="CURRENT ITEM:", font=get_font(10, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_SECONDARY, anchor="e").pack(side=tk.LEFT)
        self.current_item_label = tk.Label(self.current_item_display_frame, text="-- NONE --", font=get_font(14, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, anchor="w"); self.current_item_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        main_content = tk.Frame(self, bg=THEME_BG_PRIMARY)
        main_content = tk.Frame(self, bg=THEME_BG_PRIMARY); main_content.pack(fill="both", expand=True, side=tk.TOP); main_content.grid_columnconfigure(0, weight=80); main_content.grid_columnconfigure(1, weight=20); main_content.grid_rowconfigure(0, weight=1)

        teams_outer_frame = tk.Frame(main_content, bg=THEME_BG_SECONDARY, bd=0, relief=tk.FLAT)
        teams_outer_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        teams_outer_frame.rowconfigure(1, weight=1)
        teams_outer_frame.columnconfigure(0, weight=1)
        
        tk.Label(teams_outer_frame, text="🏆 TEAMS OVERVIEW", font=get_font(16, "bold"), bg=THEME_BG_SECONDARY, fg=THEME_ACCENT_PRIMARY, pady=10, padx=10, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        
        self.teams_canvas = tk.Canvas(teams_outer_frame, bg=THEME_BG_SECONDARY, highlightthickness=0) # Ensure canvas BG matches
        self.teams_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        
        teams_scrollbar_style = ttk.Style()
        teams_scrollbar_style.layout("Teams.Vertical.TScrollbar",
            [('Teams.Vertical.TScrollbar.trough', {'sticky': 'ns'}),
             ('Vertical.Scrollbar.uparrow', {'side': 'top', 'sticky': ''}),
             ('Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': ''}),
             ('Vertical.Scrollbar.thumb', {'sticky': 'ns', 'expand': 1})]) # Ensure thumb is part of layout

        teams_scrollbar_style.configure("Teams.Vertical.TScrollbar", gripcount=0, background=THEME_BG_CARD, troughcolor=THEME_BG_SECONDARY, bordercolor=THEME_BG_SECONDARY, arrowcolor=THEME_TEXT_PRIMARY, arrowsize=14, relief=tk.FLAT, width=16)
        teams_scrollbar_style.map("Teams.Vertical.TScrollbar",
            background=[('active', THEME_HIGHLIGHT_BG), ('!active', THEME_BG_CARD)],
            arrowcolor=[('pressed', THEME_ACCENT_PRIMARY), ('!pressed', THEME_TEXT_PRIMARY)]
        )

        teams_scrollbar = ttk.Scrollbar(teams_outer_frame, orient="vertical", command=self.teams_canvas.yview, style="Teams.Vertical.TScrollbar")
        teams_scrollbar.grid(row=1, column=1, sticky="ns")
        self.teams_canvas.configure(yscrollcommand=teams_scrollbar.set)
        
        self.scrollable_teams_frame = tk.Frame(self.teams_canvas, bg=THEME_BG_SECONDARY) # Ensure this also matches
        self.teams_canvas_window_id = self.teams_canvas.create_window((0,0), window=self.scrollable_teams_frame, anchor="nw")
        
        self.scrollable_teams_frame.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind("<Configure>", lambda e, c=self.teams_canvas, w_id=self.teams_canvas_window_id: self._configure_canvas_scrollregion(e, c, w_id))
        self.teams_canvas.bind_all("<MouseWheel>", self._on_mousewheel_teams)
        self.teams_canvas.bind_all("<Button-4>", self._on_mousewheel_teams)
        self.teams_canvas.bind_all("<Button-5>", self._on_mousewheel_teams) 
        
        self._create_team_cards_layout()
        
        right_pane = tk.Frame(main_content, bg=THEME_BG_PRIMARY); right_pane.grid(row=0, column=1, sticky="nsew", padx=(5,0)); right_pane.grid_rowconfigure(0, weight=1); right_pane.grid_rowconfigure(1, weight=0); right_pane.grid_columnconfigure(0, weight=1)
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
    def _handle_load_selected_state_from_history(self, json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no):
        success, message = self.engine.load_state_from_json_string(json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no)
        if success: self.refresh_all_ui_displays(); messagebox.showinfo("State Loaded", message, parent=self)
        else: messagebox.showerror("Load Error", message, parent=self)
        self._check_and_display_engine_warnings("Warning during state load from history:")
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
        for widget in self.scrollable_teams_frame.winfo_children(): widget.destroy()
        self.money_labels.clear(); self.inventory_listboxes.clear(); self.team_card_frames.clear()
        self.scrollable_teams_frame.grid_columnconfigure(0, weight=1); self.scrollable_teams_frame.grid_columnconfigure(1, weight=1)
        all_teams_data = self.engine.get_all_team_data(); row_num, col_num = 0, 0
        for team_info in all_teams_data:
            team_name = team_info["name"]
            card = tk.Frame(self.scrollable_teams_frame, bg=THEME_BG_CARD, padx=15, pady=12, relief=tk.FLAT, bd=0); card.configure(highlightbackground=THEME_BORDER_COLOR_LIGHT, highlightthickness=1); card.grid(row=row_num, column=col_num, sticky="ew", padx=5, pady=8); self.team_card_frames[team_name] = card
            col_num += 1; 
            if col_num >= 2: col_num = 0; row_num += 1
            header_info_frame = tk.Frame(card,bg=THEME_BG_CARD); header_info_frame.pack(fill=tk.X, pady=(0,8))
            tk.Label(header_info_frame,text=team_name.upper(),font=get_font(16,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_PRIMARY,anchor="w").pack(side=tk.LEFT)
            money_label=tk.Label(header_info_frame,text="₹0",font=get_font(15,"bold"), bg=THEME_BG_CARD,fg=THEME_ACCENT_TERTIARY,anchor="e"); money_label.pack(side=tk.RIGHT); self.money_labels[team_name]=money_label
            tk.Label(card,text="INVENTORY:",font=get_font(10,"bold"), bg=THEME_BG_CARD,fg=THEME_TEXT_SECONDARY,anchor="w").pack(fill=tk.X,pady=(5,2))
            inventory_listbox=tk.Listbox(card,font=get_font(10),height=3,relief=tk.FLAT,bd=0, bg=THEME_BG_SECONDARY, fg=THEME_TEXT_PRIMARY, selectbackground=THEME_ACCENT_PRIMARY, selectforeground=THEME_TEXT_ACCENT, highlightthickness=0, activestyle="none"); inventory_listbox.pack(fill=tk.X,expand=True,pady=(0,10)); self.inventory_listboxes[team_name]=inventory_listbox
            StyledButton(card,text="BID NOW 💸",font=get_font(12, "bold"), bg=THEME_ACCENT_PRIMARY,fg=THEME_TEXT_ACCENT, command=lambda t=team_name: self.ui_place_bid(t), pady=10).pack(fill=tk.X)
        self.scrollable_teams_frame.update_idletasks()
        if self.teams_canvas.winfo_exists(): self.teams_canvas.config(scrollregion=self.teams_canvas.bbox("all"))
    def update_team_cards_display(self):
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
        status = self.engine.get_current_bidding_status_display()
        self.current_item_label.config(text=status["item_display_name"])
        fg_color = THEME_TEXT_SECONDARY
        if status["status_color_key"] == "SUCCESS": fg_color = THEME_ACCENT_TERTIARY
        elif status["status_color_key"] == "WARNING": fg_color = THEME_ACCENT_SECONDARY
        self.bid_status_label.config(text=status["status_text"], fg=fg_color)
        self.auction_name_label.config(text=self.engine.get_auction_name().upper())
    def refresh_all_ui_displays(self): self.update_team_cards_display(); self.update_available_players_display(); self.update_bidding_status_display()
    def _check_and_display_engine_warnings(self, context_message="Engine Warning(s):"):
        warnings = self.engine.get_last_errors_and_clear()
        if warnings:
            full_warning_message = context_message + "\n - " + "\n - ".join(warnings)
            messagebox.showwarning("Auction Engine Notice", full_warning_message, parent=self)
    def ui_select_item(self, player_name): 
        try:
            current_status = self.engine.get_current_bidding_status_display()
            if current_status["bidding_active"] and self.engine.highest_bidder_name:
                 if not messagebox.askyesno("Confirm Item Change", f"'{self.engine.current_item_name}' active with bids. Change? Current item passes.", icon='warning', parent=self): return
            passed_message = self.engine.select_item_for_bidding(player_name)
            if passed_message: messagebox.showinfo("Item Auto-Passed", passed_message, parent=self)
        except AuctionError as e: messagebox.showerror("Selection Error", str(e), parent=self)
        finally: self.refresh_all_ui_displays(); self._check_and_display_engine_warnings()
    def ui_place_bid(self, team_name): 
        try: self.engine.place_bid(team_name)
        except AuctionError as e: messagebox.showerror("Bid Error", str(e), parent=self)
        finally: self.refresh_all_ui_displays(); self._check_and_display_engine_warnings()
    def ui_undo_last_bid(self): 
        try: self.engine.undo_last_bid()
        except AuctionError as e: messagebox.showerror("Undo Error", str(e), parent=self)
        finally: self.refresh_all_ui_displays(); self._check_and_display_engine_warnings()
    def ui_sell_item(self): 
        try:
            item_name, winner, bid, message = self.engine.sell_current_item()
            messagebox.showinfo("Item Sold", message, parent=self)
        except AuctionError as e: messagebox.showerror("Sell Error", str(e), parent=self)
        finally: self.refresh_all_ui_displays(); self._check_and_display_engine_warnings()
    def ui_pass_item(self): 
        try:
            if self.engine.bidding_active and self.engine.current_item_name and self.engine.highest_bidder_name:
                 if not messagebox.askyesno("Confirm Pass", f"'{self.engine.current_item_name}' has bids. Pass anyway?", icon='warning', parent=self): return
            passed_item_name = self.engine.pass_current_item()
            messagebox.showinfo("Item Passed", f"'{passed_item_name}' passed/unsold.", parent=self)
        except AuctionError as e: messagebox.showerror("Pass Error", str(e), parent=self)
        finally: self.refresh_all_ui_displays(); self._check_and_display_engine_warnings()
    def on_app_frame_closing(self):
        if self.engine: self.engine.close_logger()

def main(): 
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
            clear_current_page(); current_page_widget = InitialPage(root, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), lambda: show_page(FileSelectPageForResume, start_resumed_auction_ui)); current_page_widget.pack(fill="both", expand=True)
    def start_new_auction_ui(teams_data_dicts, players_data_dicts, auction_name_str, bid_increment_rules_from_csv=None):
        nonlocal auction_engine_main
        try:
            auction_engine_main.setup_new_auction(auction_name_str, teams_data_dicts, players_data_dicts)
            if bid_increment_rules_from_csv: auction_engine_main.set_bid_increment_rules(bid_increment_rules_from_csv)
            show_page(AuctionApp, auction_engine_instance=auction_engine_main)
        except (InitializationError, LogFileError, AuctionError) as e: messagebox.showerror("New Auction Error", f"Start failed: {e}", parent=root); show_page(InitialPage, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), lambda: show_page(FileSelectPageForResume, start_resumed_auction_ui))
        except Exception as e: import traceback; traceback.print_exc(); messagebox.showerror("Critical Setup Error", f"Unexpected setup error: {e}", parent=root)
    def start_resumed_auction_ui(log_file_path_str):
        nonlocal auction_engine_main
        try: 
            auction_engine_main.load_auction_from_log(log_file_path_str)
            show_page(AuctionApp, auction_engine_instance=auction_engine_main)
        except (LogFileError, AuctionError) as e: 
            messagebox.showerror("Resume Error", f"Resume failed '{os.path.basename(log_file_path_str)}':\n{e}", parent=root)
            show_page(InitialPage, 
                      lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), 
                      handle_resume_auction_logic) # Use the new handler here for fallback
        except Exception as e: 
            import traceback
            traceback.print_exc()
            messagebox.showerror("Critical Load Error", f"Unexpected load error: {e}", parent=root)
            # Fallback to initial page on critical error
            show_page(InitialPage, 
                      lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), 
                      handle_resume_auction_logic)
    
    def handle_resume_auction_logic():
        cwd = os.getcwd()
        try:
            log_files_in_cwd = [
                f for f in os.listdir(cwd) 
                if f.endswith(LOG_FILE_EXTENSION) and os.path.isfile(os.path.join(cwd, f))
            ]
        except OSError as e:
            messagebox.showwarning("Directory Error", f"Could not scan current directory for log files: {e}", parent=root)
            log_files_in_cwd = [] # Proceed as if no files found

        if len(log_files_in_cwd) == 1:
            log_file_path_str = os.path.join(cwd, log_files_in_cwd[0])
            if messagebox.askyesno(
                "Resume Auction", 
                f"Found one log file in the current directory:\n'{log_files_in_cwd[0]}'\n\nDo you want to resume this auction?", 
                parent=root,
                icon='question'
            ):
                # Attempt to load this single file directly
                start_resumed_auction_ui(log_file_path_str)
            else:
                # User declined the auto-selected file, show the manual browser
                show_page(FileSelectPageForResume, start_resumed_auction_ui)
        else:
            if not log_files_in_cwd: # len is 0
                messagebox.showinfo(
                    "No Logs Found", 
                    "No .auctionlog files found in the current directory.\nPlease browse to locate one.", 
                    parent=root
                )
            elif len(log_files_in_cwd) > 1:
                 messagebox.showinfo(
                    "Multiple Logs Found", 
                    "Multiple .auctionlog files found in the current directory.\nPlease select one manually.", 
                    parent=root
                )
            # Proceed to show the manual file browser page
            show_page(FileSelectPageForResume, start_resumed_auction_ui)
    
    def on_root_close():
        nonlocal current_page_widget
        if isinstance(current_page_widget, AuctionApp): current_page_widget.on_app_frame_closing()
        elif auction_engine_main and auction_engine_main.get_log_filepath(): auction_engine_main.close_logger()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_root_close)
    show_page(InitialPage, lambda: show_page(FileSelectPage, start_new_auction_ui, title="CREATE NEW AUCTION"), 
              handle_resume_auction_logic)
    root.mainloop()

if __name__ == "__main__":
    main()