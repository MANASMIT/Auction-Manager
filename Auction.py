import tkinter as tk
from tkinter import messagebox, scrolledtext

class AuctionApp:
    def __init__(self, master):
        self.master = master
        master.title("Auction")

        self.teams = ["KAISER SQUADRA", "the minions", "Flat is Justice", "Team BKL(Bahut Khas Log)"]
        self.team_money = {team: 1000 for team in self.teams}  # Starting money for each team
        self.team_inventory = {team: {} for team in self.teams}  # Inventory for each team
        self.items = [("Neel Gajjar (Q15)", 120), ("Neha (Q17)", 50), ("Vishal Sai Vetrivel (Q15)", 75),
                      ("Sailesh Kumar Mahanta (Q15)", 75), ("Akshat Sharma (Q13)", 100),
                      ("Chanderpal (Q15)", 75), ("Ankit Gautam (Q16)", 75), ("Pratik Singh (Q15)", 50),
                      ("Sangram Tudu (Q16)", 75), ("Abhijit Jeffy (Q17)", 50), ("Manan Rawat (Q14)", 100),
                      ("Om Raval (Q14)", 50), ("Harsh Nagpal (Q17)", 120), ("Shreyas (Q16)", 75),
                      ("Subham Dey (Q16)", 75), ("Piyush Jena (Q16)", 50), ("Ankush Meena (Q17)", 50),
                      ("Manasmit Jena (Q13)", 100), ("Sahil (Q17)", 50), ("A Sai Govinda (Q17)", 50),
                      ("Atharva Raj (Q17)", 50), ("Rajeshwar Sahu (Q17)", 50), ("Parul (Q13)", 100),
                      ("Yashobanta Sahu (Q16)", 50)]

        self.current_item = None
        self.current_bid = 0
        self.highest_bidder = None
        self.separator_lines = []
        self.bidding_enabled = True  # Flag to control bidding process

        # Create labels for each team's money and inventory
        self.money_labels = {}
        self.inventory_labels = {}
        for i, team in enumerate(self.teams):
            money_label = tk.Label(master, text=f"{team} \n Money: ₹{self.team_money[team]}", font=('Arial', 12,'bold'))
            money_label.grid(row=2, column=i, pady=5, padx=5, sticky="ew")
            self.money_labels[team] = money_label

            inventory_label = tk.Label(master, text=f"{team} \n Inventory: ", font=('Arial', 12))
            inventory_label.grid(row=3, column=i, pady=5, padx=5, sticky="ew")
            self.inventory_labels[team] = inventory_label

            bid_button = tk.Button(master, text=f"Bid", font=('Arial', 12),
                                   command=lambda team=team: self.place_bid(team), width=12, height=2, bg="lightblue")
            bid_button.grid(row=10, column=i, pady=5, padx=5, sticky="s")

        # Label for current item and bidding status
        self.current_item_label = tk.Label(master, text="Current Item: ", font=('Arial', 14,'bold'))
        self.current_item_label.grid(row=0, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        self.bid_status_label = tk.Label(master, text="Bidding Status: ", font=('Arial', 14))
        self.bid_status_label.grid(row=1, column=0, columnspan=2, pady=10, padx=5, sticky="w")

        # Display items along with starting prices
        self.item_list_text = scrolledtext.ScrolledText(master, width=30, height=30, font=('Arial', 12), wrap=tk.WORD)
        self.item_list_text.grid(row=2, column=4, rowspan=6, columnspan=2, padx=5, pady=5, sticky="sew")
        for item, price in self.items:
            item_button = tk.Button(master, text=f"{item} (Starting Price: ₹{price})", font=('Arial', 12),
                                    command=lambda item=(item, price): self.select_item(item))
            item_button.grid(sticky="w")
            self.item_list_text.window_create("end", window=item_button)
            self.item_list_text.insert("end", "\n")

        # Button to end bidding round
        end_bidding_button = tk.Button(master, text="End Bidding Round", height=2, command=self.end_bidding_round, bg="red", font=('Arial', 12))
        end_bidding_button.grid(row=15, column=1, columnspan=2, pady=10, padx=5, sticky="nsew")

        # Set row and column weights for resizing
        for i in range(9):
            master.rowconfigure(i, weight=1)
        for i in range(6):
            master.columnconfigure(i, weight=1)

    def select_item(self, item):
        self.toggle_bidding_enabled()
        self.current_item = item
        self.current_bid = item[1]  # Set current bid to the starting price of the selected item
        self.highest_bidder = None
        self.update_labels()

    def place_bid(self, team):
        if self.bidding_enabled and self.current_item and self.team_money[team] >= int(self.current_bid):
            if self.highest_bidder != team:  # Only allow a bid from a different team
                if self.highest_bidder is None:  # Base price, no increment for the first bid
                    self.highest_bidder = team
                else:
                    # Increment logic based on current bid
                    if int(self.current_bid) < 50:
                        bid_increment = 0  # No increment for bids below 50
                    elif int(self.current_bid) < 100:
                        bid_increment = 5  # Increment by 5 for bids between 50-100
                    elif int(self.current_bid) < 200:
                        bid_increment = 10  # Increment by 10 for bids between 100-200
                    else:
                        bid_increment = 25  # Increment by 25 for bids above 200

                    self.current_bid += bid_increment
                    self.highest_bidder = team
                self.update_labels()

    def end_bidding_round(self):
        if self.bidding_enabled and self.highest_bidder:
            item_name, item_value = self.current_item
            self.team_money[self.highest_bidder] -= int(self.current_bid)
            self.team_inventory[self.highest_bidder][item_name] = int(self.current_bid)
            self.remove_current_item()  # Remove the current item from the items list
            messagebox.showinfo("Auction Result", f"{self.highest_bidder} won {item_name} for ₹{self.current_bid}!")
            self.toggle_bidding_disabled()  # Disable bidding until a new item is selected
            self.update_labels()
        else:
            messagebox.showinfo("Auction Result", "No bids were placed in this round.")

    def remove_current_item(self):
        if self.current_item in self.items:
            self.items.remove(self.current_item)
        # Clear the existing text in the item list widget
        self.item_list_text.config(state=tk.NORMAL)
        self.item_list_text.delete("1.0", tk.END)
        # Insert the updated items list
        for item, price in self.items:
            item_button = tk.Button(self.master, text=f"{item} (Starting Price: ₹{price})", font=('Arial', 12),
                                    command=lambda item=(item, price): self.select_item(item))
            item_button.grid(sticky="w")
            self.item_list_text.window_create("end", window=item_button)
            self.item_list_text.insert("end", "\n")
        self.item_list_text.config(state=tk.DISABLED)

    def update_labels(self):
        if self.current_item:
            self.current_item_label.config(
                text=f"Current Item: {self.current_item[0]} (Starting Price: ₹{self.current_item[1]})")
            if self.highest_bidder:
                self.bid_status_label.config(
                    text=f"Current Highest Bid: ₹{self.current_bid} by {self.highest_bidder}")
            else:
                self.bid_status_label.config(text=f"No bids placed yet")
            for team in self.teams:
                # Update money label
                self.money_labels[team].config(text=f"{team} \n Money: ₹{self.team_money[team]}")
                # Update inventory label
                inventory_text = "\n".join(
                    [f"{item} (Value: ₹{bid_price})" for item, bid_price in self.team_inventory[team].items()])
                self.inventory_labels[team].config(text=f"{team} \n Inventory:\n{inventory_text}")
        else:
            self.current_item_label.config(text="No items available for auction")

    def toggle_bidding_enabled(self):
        self.bidding_enabled = 1
        
    def toggle_bidding_disabled(self):
        self.bidding_enabled = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = AuctionApp(root)
    root.mainloop()
