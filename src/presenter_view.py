# presenter_view.py
import os
import tkinter as tk
from tkinter import ttk, font as tkFont
from PIL import Image, ImageTk, ImageDraw, ImageFont # For image handling and placeholders

# --- Constants (can be adjusted) ---
PRESENTER_BG_PRIMARY = "#000033"  # Dark blue
PRESENTER_BG_SECONDARY = "#000055" # Slightly lighter dark blue
PRESENTER_TEXT_PRIMARY = "#FFFFFF" # White
PRESENTER_TEXT_ACCENT = "#FFD700" # Gold
PRESENTER_TEXT_SOLD = "#00FF00"   # Bright Green
PRESENTER_TEXT_BID = "#FFA500"    # Orange

DEFAULT_PLAYER_PHOTO_SIZE = (200, 280)
DEFAULT_TEAM_LOGO_SIZE = (100, 100)
SOLD_ITEM_PHOTO_SIZE = (60, 84)
SOLD_ITEM_LOGO_SIZE = (50, 50)

FONT_FAMILY_PRESENTER = "Impact" # Or "Arial Black", "Verdana"
FONT_FAMILY_FALLBACK = "Arial"

def get_presenter_font(size, weight="normal", slant="roman", family=FONT_FAMILY_PRESENTER):
    try:
        font = tkFont.Font(family=family, size=size, weight=weight, slant=slant)
        if font.actual("family").lower() != family.lower() and FONT_FAMILY_FALLBACK:
             font = tkFont.Font(family=FONT_FAMILY_FALLBACK, size=size, weight=weight, slant=slant)
        return font
    except tk.TclError:
        return tkFont.Font(family=FONT_FAMILY_FALLBACK, size=size, weight=weight, slant=slant)

def load_and_resize_image(path, size, default_color="grey", text_on_placeholder=None):
    """Loads, resizes an image, or creates a placeholder if missing/error."""

    absolute_path = "N/A" # Default if path is None
    if path:
        # IMPORTANT: Resolve path relative to the script's CWD if it's not absolute
        if not os.path.isabs(path):
            # This assumes paths in CSV are relative to where auction_UI.py is run
            # If CSV paths are relative to the CSV file itself, you'd need the CSV file's directory
            absolute_path = os.path.abspath(os.path.join(os.getcwd(), path))
        else:
            absolute_path = path
    print(f"Attempting to load image from (original path): '{path}'")
    print(f"Attempting to load image from (absolute path): '{absolute_path}'")
    
    try:
        if path and os.path.exists(path):
            img = Image.open(path)
        else:
            raise FileNotFoundError("Image path not found or is None.")
    except Exception as e:
        # print(f"Image load error for '{path}': {e}. Creating placeholder.")
        img = Image.new('RGB', size, color=default_color)
        if text_on_placeholder:
            draw = ImageDraw.Draw(img)
            try:
                placeholder_font = ImageFont.truetype("arial.ttf", size[1] // 6)
            except IOError:
                placeholder_font = ImageFont.load_default()
        
            text_bbox = draw.textbbox((0,0), text_on_placeholder, font=placeholder_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            text_x = (size[0] - text_width) / 2
            text_y = (size[1] - text_height) / 2
            draw.text((text_x, text_y), text_on_placeholder, fill=(255,255,255), font=placeholder_font)

    img.thumbnail(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)


class PresenterWindow(tk.Toplevel):
    def __init__(self, master, auction_name="Auction"):
        super().__init__(master)
        self.title(f"{auction_name} - Presenter View")
        self.geometry("1280x720") # Standard 720p, adjust as needed
        self.configure(bg=PRESENTER_BG_PRIMARY)
        # self.attributes("-fullscreen", True) # Optional: for true fullscreen

        self.auction_name = auction_name
        self._image_references = {} # To prevent garbage collection of PhotoImage objects

        self._setup_ui()
        self.update_auction_name_display(self.auction_name) # Initial name display

    def _setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self, bg=PRESENTER_BG_PRIMARY)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top: Auction Name
        self.auction_name_label = tk.Label(main_frame, text=self.auction_name, font=get_presenter_font(30, "bold"),
                                           bg=PRESENTER_BG_PRIMARY, fg=PRESENTER_TEXT_ACCENT)
        self.auction_name_label.pack(pady=(0, 20))

        # Content Area (Player Info and Bid Info side-by-side)
        content_frame = tk.Frame(main_frame, bg=PRESENTER_BG_PRIMARY)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1) # Player info
        content_frame.columnconfigure(1, weight=1) # Bid info
        content_frame.rowconfigure(0, weight=1)

        # --- Left Side: Current Player ---
        player_frame = tk.Frame(content_frame, bg=PRESENTER_BG_SECONDARY, padx=15, pady=15)
        player_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.player_photo_label = tk.Label(player_frame, bg=PRESENTER_BG_SECONDARY)
        self.player_photo_label.pack(pady=10)
        self._image_references['player_photo'] = load_and_resize_image(None, DEFAULT_PLAYER_PHOTO_SIZE, PRESENTER_BG_SECONDARY, "No Player")
        self.player_photo_label.config(image=self._image_references['player_photo'])

        self.player_name_label = tk.Label(player_frame, text="NO PLAYER SELECTED", font=get_presenter_font(36, "bold"),
                                          bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY, wraplength=400)
        self.player_name_label.pack(pady=10)

        self.player_base_bid_label = tk.Label(player_frame, text="Base Bid: ---", font=get_presenter_font(22),
                                              bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY)
        self.player_base_bid_label.pack(pady=5)

        # --- Right Side: Bidding / Sold Info ---
        bid_sold_frame_outer = tk.Frame(content_frame, bg=PRESENTER_BG_SECONDARY, padx=15, pady=15)
        bid_sold_frame_outer.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # This frame will hold either bidding info or sold info
        self.bid_sold_content_frame = tk.Frame(bid_sold_frame_outer, bg=PRESENTER_BG_SECONDARY)
        self.bid_sold_content_frame.pack(fill=tk.BOTH, expand=True)

        self._setup_bidding_info_ui(self.bid_sold_content_frame) # Initially show bidding UI
        self._setup_sold_info_ui(self.bid_sold_content_frame) # Create sold UI, but hide it

        # --- Bottom: Recently Sold Ticker (simplified for now) ---
        self.sold_ticker_frame = tk.Frame(main_frame, bg=PRESENTER_BG_SECONDARY, height=100)
        self.sold_ticker_frame.pack(fill=tk.X, pady=(20, 0))
        tk.Label(self.sold_ticker_frame, text="RECENTLY SOLD", font=get_presenter_font(16, "bold"),
                 bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_ACCENT).pack(pady=5)
        self.sold_items_display_frame = tk.Frame(self.sold_ticker_frame, bg=PRESENTER_BG_SECONDARY)
        self.sold_items_display_frame.pack(fill=tk.X, expand=True, padx=10)
        self.recent_sold_items = [] # Store data for last few sold items

        self.clear_current_item() # Set initial state

    def _setup_bidding_info_ui(self, parent_frame):
        self.bidding_info_frame = tk.Frame(parent_frame, bg=PRESENTER_BG_SECONDARY)
        # This frame will be packed/unpacked

        tk.Label(self.bidding_info_frame, text="CURRENT BID", font=get_presenter_font(28, "bold"),
                 bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY).pack(pady=(20, 5))
        self.current_bid_amount_label = tk.Label(self.bidding_info_frame, text="₹ ---", font=get_presenter_font(72, "bold"),
                                                 bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_BID)
        self.current_bid_amount_label.pack(pady=5)

        tk.Label(self.bidding_info_frame, text="HIGHEST BIDDER", font=get_presenter_font(28, "bold"),
                 bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY).pack(pady=(20, 5))
        
        self.bidder_logo_label = tk.Label(self.bidding_info_frame, bg=PRESENTER_BG_SECONDARY)
        self.bidder_logo_label.pack(pady=5)
        self._image_references['bidder_logo'] = load_and_resize_image(None, DEFAULT_TEAM_LOGO_SIZE, PRESENTER_BG_SECONDARY, "Team")
        self.bidder_logo_label.config(image=self._image_references['bidder_logo'])
        
        self.highest_bidder_name_label = tk.Label(self.bidding_info_frame, text="---", font=get_presenter_font(32, "bold"),
                                                  bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY)
        self.highest_bidder_name_label.pack(pady=5)

    def _setup_sold_info_ui(self, parent_frame):
        self.sold_info_frame = tk.Frame(parent_frame, bg=PRESENTER_BG_SECONDARY)
        # This frame will be packed/unpacked initially hidden

        self.sold_message_label = tk.Label(self.sold_info_frame, text="SOLD!", font=get_presenter_font(60, "bold"),
                                      bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_SOLD)
        self.sold_message_label.pack(pady=(30,10))

        self.sold_to_team_logo_label = tk.Label(self.sold_info_frame, bg=PRESENTER_BG_SECONDARY)
        self.sold_to_team_logo_label.pack(pady=10)
        self._image_references['sold_to_logo'] = load_and_resize_image(None, (150,150), PRESENTER_BG_SECONDARY, "Winning Team") # Larger logo
        self.sold_to_team_logo_label.config(image=self._image_references['sold_to_logo'])

        self.sold_to_team_name_label = tk.Label(self.sold_info_frame, text="TEAM NAME", font=get_presenter_font(30, "bold"),
                                            bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_PRIMARY)
        self.sold_to_team_name_label.pack(pady=5)

        self.sold_for_price_label = tk.Label(self.sold_info_frame, text="FOR ₹ PRICE", font=get_presenter_font(40, "bold"),
                                         bg=PRESENTER_BG_SECONDARY, fg=PRESENTER_TEXT_ACCENT)
        self.sold_for_price_label.pack(pady=10)


    def _show_bidding_layout(self):
        self.sold_info_frame.pack_forget()
        self.bidding_info_frame.pack(fill=tk.BOTH, expand=True, anchor="center")

    def _show_sold_layout(self):
        self.bidding_info_frame.pack_forget()
        self.sold_info_frame.pack(fill=tk.BOTH, expand=True, anchor="center")

    def update_auction_name_display(self, auction_name):
        self.auction_name = auction_name
        self.auction_name_label.config(text=auction_name.upper())
        self.title(f"{auction_name} - Presenter View")

    def update_current_item(self, player_name, player_photo_path, base_bid):
        self._show_bidding_layout() # Ensure bidding layout is visible
        self.player_name_label.config(text=player_name.upper() if player_name else "NO PLAYER SELECTED")
        
        photo = load_and_resize_image(player_photo_path, DEFAULT_PLAYER_PHOTO_SIZE, PRESENTER_BG_SECONDARY, "No Photo")
        self._image_references['player_photo'] = photo
        self.player_photo_label.config(image=photo)

        self.player_base_bid_label.config(text=f"Base Bid: ₹{base_bid:,}" if player_name else "Base Bid: ---")
        # Reset bid status for new item
        self.update_bid_status(None, None, base_bid, False)


    def update_bid_status(self, bidder_team_name, bidder_logo_path, bid_amount, highest_bidder_exists):
        self._show_bidding_layout() # Ensure bidding layout is visible
        self.current_bid_amount_label.config(text=f"₹{bid_amount:,}")
        if highest_bidder_exists and bidder_team_name:
            self.highest_bidder_name_label.config(text=bidder_team_name.upper())
            logo = load_and_resize_image(bidder_logo_path, DEFAULT_TEAM_LOGO_SIZE, PRESENTER_BG_SECONDARY, "Logo")
            self._image_references['bidder_logo'] = logo
            self.bidder_logo_label.config(image=logo)
        else:
            self.highest_bidder_name_label.config(text="--- NO BIDS YET ---")
            logo = load_and_resize_image(None, DEFAULT_TEAM_LOGO_SIZE, PRESENTER_BG_SECONDARY, "Team") # Placeholder
            self._image_references['bidder_logo'] = logo
            self.bidder_logo_label.config(image=logo)

    def show_item_sold(self, player_name_sold, player_photo_path, winning_team_name, winning_team_logo_path, sold_price):
        self._show_sold_layout()
        # Update player info on the left to show who was just sold
        self.player_name_label.config(text=f"{player_name_sold.upper()} - SOLD!")
        photo = load_and_resize_image(player_photo_path, DEFAULT_PLAYER_PHOTO_SIZE, PRESENTER_BG_SECONDARY, "No Photo")
        self._image_references['player_photo'] = photo # Keep reference
        self.player_photo_label.config(image=photo)
        self.player_base_bid_label.config(text="") # Clear base bid

        # Update sold info on the right
        self.sold_message_label.config(text=f"SOLD TO {winning_team_name.upper()}!")
        
        sold_team_logo = load_and_resize_image(winning_team_logo_path, (150,150), PRESENTER_BG_SECONDARY, "Team")
        self._image_references['sold_to_logo'] = sold_team_logo
        self.sold_to_team_logo_label.config(image=sold_team_logo)
        
        self.sold_to_team_name_label.config(text=winning_team_name.upper())
        self.sold_for_price_label.config(text=f"FOR ₹{sold_price:,}")

        self._add_to_sold_ticker({
            "name": player_name_sold, "photo_path": player_photo_path,
            "team_name": winning_team_name, "logo_path": winning_team_logo_path,
            "price": sold_price
        })


    def clear_current_item(self, passed=False, item_name=None): # Item passed or new item selected
        self._show_bidding_layout() # Switch back to bidding layout
        self.player_name_label.config(text="SELECTING NEXT PLAYER..." if not passed else f"{item_name.upper() if item_name else 'ITEM'} PASSED")
        
        photo = load_and_resize_image(None, DEFAULT_PLAYER_PHOTO_SIZE, PRESENTER_BG_SECONDARY, "Waiting...")
        self._image_references['player_photo'] = photo
        self.player_photo_label.config(image=photo)

        self.player_base_bid_label.config(text="Base Bid: ---")
        self.update_bid_status(None, None, 0, False) # Reset bid status

    def _add_to_sold_ticker(self, sold_item_data):
        max_ticker_items = 5 # Show last 5
        self.recent_sold_items.insert(0, sold_item_data)
        if len(self.recent_sold_items) > max_ticker_items:
            self.recent_sold_items.pop()
        
        # Clear previous ticker items
        for widget in self.sold_items_display_frame.winfo_children():
            widget.destroy()

        for item in reversed(self.recent_sold_items): # Show newest on the right or adjust packing
            item_card = tk.Frame(self.sold_items_display_frame, bg=PRESENTER_BG_PRIMARY, padx=5, pady=5)
            item_card.pack(side=tk.LEFT, padx=5) # Adjust side (LEFT for horizontal)

            p_photo = load_and_resize_image(item["photo_path"], SOLD_ITEM_PHOTO_SIZE, default_color=PRESENTER_BG_PRIMARY)
            self._image_references[f"ticker_p_{item['name']}"] = p_photo
            tk.Label(item_card, image=p_photo, bg=PRESENTER_BG_PRIMARY).pack()
            
            tk.Label(item_card, text=item["name"], font=get_presenter_font(10), fg=PRESENTER_TEXT_PRIMARY, bg=PRESENTER_BG_PRIMARY).pack()
            
            t_logo = load_and_resize_image(item["logo_path"], SOLD_ITEM_LOGO_SIZE, default_color=PRESENTER_BG_PRIMARY)
            self._image_references[f"ticker_t_{item['team_name']}"] = t_logo
            tk.Label(item_card, image=t_logo, bg=PRESENTER_BG_PRIMARY).pack(pady=(0,2))
            
            tk.Label(item_card, text=f"₹{item['price']:,}", font=get_presenter_font(11, "bold"), fg=PRESENTER_TEXT_ACCENT, bg=PRESENTER_BG_PRIMARY).pack()

if __name__ == '__main__':
    # For testing PresenterWindow independently
    root = tk.Tk()
    root.withdraw() # Hide the main root window if only testing presenter
    
    # Example data
    player_photo_example = "path/to/your/sample_player.png" # Create a dummy image or use a real one
    team_logo_example = "path/to/your/sample_logo.png"     # Create a dummy image or use a real one
    # Make sure these paths exist or placeholders will be shown

    if not os.path.exists("path/to/your"): os.makedirs("path/to/your", exist_ok=True)
    if not os.path.exists(player_photo_example): Image.new('RGB', (10,10), "blue").save(player_photo_example)
    if not os.path.exists(team_logo_example): Image.new('RGB', (10,10), "green").save(team_logo_example)


    presenter_win = PresenterWindow(root, auction_name="TEST AUCTION LEAGUE")
    
    # Test update methods
    presenter_win.update_current_item("VIRAT KOHLI", player_photo_example, 200)
    # presenter_win.update_bid_status("TEAM RED", team_logo_example, 250, True)
    # presenter_win.after(3000, lambda: presenter_win.update_bid_status("TEAM BLUE", None, 260, True))
    # presenter_win.after(5000, lambda: presenter_win.show_item_sold(
    #     "VIRAT KOHLI", player_photo_example,
    #     "TEAM BLUE", None, 260
    # ))
    # presenter_win.after(8000, lambda: presenter_win.update_current_item("ROHIT SHARMA", None, 150))

    root.mainloop()