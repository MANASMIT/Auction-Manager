import tkinter as tk
from tkinter import messagebox, scrolledtext
import random

class AuctionApp:
    def __init__(self, master):
        self.master = master
        master.title("Auction")

        self.teams = ["Team 1", "Team 2", "Team 3", "Team 4"]
        self.team_money = {team: 1000000 for team in self.teams}  # Starting money for each team
        self.team_inventory = {team: {} for team in self.teams}  # Inventory for each team
        self.items = [("Neel Gajjar",1000), ("Neha Q17",1000), ("Vishal Sai Vetrivel",1000), ("Sailesh Kumar Mahanta",1000), ("Akshat Sharma",1000), 
                      ("Chanderpal",1000), ("Ankit Gautam",1000), ("Pratik Singh",1000), ("Sangram Tudu",1000), ("Abhijeet Jeffy",1000),
                        ("Om Raval",1000), ("Harsh Nagpal",1000), ("Shreyas",1000), ("Subham Dey",1000), ("Piyush Jena",1000), ("Ankush Meena",1000),
                        ("Manasmit Jena",1000), ("Sahil",1000), ("A Sai Govinda",1000), ("Atharva raj",1000), ("Rajeshwar Sahu",1000), ("Parul",1000)]
        self.current_item = None
        self.current_bid = 0
        self.highest_bidder = None
        self.separator_lines = []
        
        # Create labels for each team's money and inventory
        self.money_labels = {}
        self.inventory_labels = {}
        for i, team in enumerate(self.teams):
            money_label = tk.Label(master, text=f"{team} Money: ₹{self.team_money[team]}", font=('Arial', 12))
            money_label.grid(row=2, column=i, pady=5, padx=5, sticky="w")
            self.money_labels[team] = money_label

            inventory_label = tk.Label(master, text=f"{team} Inventory: ", font=('Arial', 12))
            inventory_label.grid(row=3, column=i, pady=5, padx=5, sticky="w")
            self.inventory_labels[team] = inventory_label

            bid_button = tk.Button(master, text=f"Bid {team}",font =('Arial',12), command=lambda team=team: self.place_bid(team), width=10, height=2, bg="lightblue",)
            bid_button.grid(row=10, column=i, pady=5, padx=5, sticky="s")

        # Label for current item and bidding status
        self.current_item_label = tk.Label(master, text="Current Item: ", font=('Arial', 14))
        self.current_item_label.grid(row=0, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        self.bid_status_label = tk.Label(master, text="Bidding Status: ", font=('Arial', 14))
        self.bid_status_label.grid(row=1, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        
        # Display items along with starting prices
        self.item_list_text = scrolledtext.ScrolledText(master, width=30, height=30, font=('Arial', 12), wrap=tk.WORD)
        self.item_list_text.grid(row=2, column=4, rowspan=6, columnspan=2, padx=5, pady=5, sticky="sew")
        for item, price in self.items:
            self.item_list_text.insert(tk.END, f"{item} (Starting Price: ₹{price})\n\n")
        self.item_list_text.config(state=tk.DISABLED)

        # Button to start the auction
        start_button = tk.Button(master, text="Start Auction", command=self.start_auction, bg="lightgreen")
        start_button.grid(row=14, column=1, columnspan=2, pady=10, padx=5, sticky="nsew")

        # Button to end bidding round
        end_bidding_button = tk.Button(master, text="End Bidding Round", command=self.end_bidding_round, bg="red")
        end_bidding_button.grid(row=15, column=1, columnspan=2, pady=10, padx=5, sticky="nsew")

        # Set row and column weights for resizing
        for i in range(9):
            master.rowconfigure(i, weight=1)
        for i in range(6):
            master.columnconfigure(i, weight=1)

    def start_auction(self):
        self.current_item = random.choice(self.items)
        self.current_bid = self.current_item[1]  # Starting bid is the item's starting value
        self.highest_bidder = None
        self.update_labels()

    def place_bid(self, team):
        if self.current_item and self.team_money[team] > self.current_bid:
            # Increment bid by a random amount
            bid_increment = 10
            self.current_bid += bid_increment
            self.highest_bidder = team
            self.update_labels()

    def end_bidding_round(self):
        if self.highest_bidder:
            item_name, item_value = self.current_item
            self.team_money[self.highest_bidder] -= self.current_bid
            self.team_inventory[self.highest_bidder][item_name] = self.current_bid
            self.remove_current_item()  # Remove the current item from the items list
            messagebox.showinfo("Auction Result", f"{self.highest_bidder} won {item_name} for ₹{self.current_bid}!")
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
            self.item_list_text.insert(tk.END, f"{item} (Starting Price: ₹{price})\n\n")
        self.item_list_text.config(state=tk.DISABLED)
        
    def update_labels(self):
        if self.current_item:
            self.current_item_label.config(text=f"Current Item: {self.current_item[0]} (Starting Price: ₹{self.current_item[1]})")
            if self.highest_bidder:
                self.bid_status_label.config(text=f"Current Highest Bid: ₹{self.current_bid} by {self.highest_bidder}")
            else:
                self.bid_status_label.config(text=f"No bids placed yet")
            for team in self.teams:
                # Update money label
                self.money_labels[team].config(text=f"{team} Money: ₹{self.team_money[team]}")
                # Update inventory label
                inventory_text = "\n".join([f"{item} (Value: ₹{bid_price})" for item, bid_price in self.team_inventory[team].items()])
                self.inventory_labels[team].config(text=f"{team} Inventory:\n{inventory_text}")
        else:
            self.current_item_label.config(text="No items available for auction")


if __name__ == "__main__":
    root = tk.Tk()
    app = AuctionApp(root)
    root.mainloop()
