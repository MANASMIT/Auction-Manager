# Auction Command: Desktop Auction Application

Auction Command is a desktop application built with Python and Tkinter, designed to manage live player auctions. It provides a user-friendly interface for auctioneers to conduct auctions, track bids, manage team budgets, and maintain a persistent log of all auction events.

## Features ✨

*   **New Auction Setup:** Start a new auction by importing team and player data from a CSV file.
*   **Resume Auction:** Load and continue a previously saved auction from an `.auctionlog` file.
*   **Player Selection:** Easily select players from an "Available Players" list to bring them up for bidding.
*   **Bidding System:**
    *   Teams can place bids with a single click.
    *   Automatic bid increment calculation based on configurable rules.
    *   Tracks the current highest bidder and bid amount.
*   **Sell/Pass Items:** Auctioneer can sell the current item to the highest bidder or pass the item if unsold.
*   **Undo Last Bid:** Option to revert the last bid placed.
*   **Team Management:**
    *   Displays each team's current budget and acquired players (inventory).
    *   Prevents teams from bidding beyond their available funds.
*   **Persistent Logging:**
    *   All significant auction events (item selection, bids, sales, passes, errors) are logged to a `.auctionlog` file.
    *   Ensures auction state can be recovered.
*   **Log Viewer:**
    *   Inspect the history of auction states from the log file.
    *   Ability to load a previous state from the log, effectively rolling back the auction.
*   **Customizable Bid Increment Rules:** Define bid increment tiers (e.g., bids up to 50 increment by 1, bids from 50-100 increment by 5, etc.) via the setup CSV.
*   **Template CSV Generation:** Generate a template `auction_setup_template.csv` file to guide users in preparing their auction data.
*   **Modern Themed UI:** A visually appealing interface for better user experience.

## Requirements 🛠️

*   Python 3.x (Tkinter is typically included with standard Python distributions)
*   No external libraries are required beyond the Python standard library.

## Installation & Setup ⚙️

1.  **Clone the repository (or download the files):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```
    Or simply download `auction_engine.py` and `auction_UI.py` in `src/` into the same directory.

2.  **Ensure Python 3 is installed.** You can check by running `python --version` or `python3 --version`.

3.  **(Optional but Recommended) Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

## How to Run 🚀

1.  **To start the Auction Command application (GUI):**
    ```bash
    python auction_UI.py
    ```

2.  **To generate a template CSV file for auction setup:**
    Open your terminal or command prompt in the directory containing `auction_engine.py` and run:
    ```bash
    python auction_engine.py --template
    ```
    This will create a file named `auction_setup_template.csv` in the current directory. You can specify a different output filename:
    ```bash
    python auction_engine.py --template -o my_custom_setup.csv
    ```

## Usage Guide 📖

### 1. Preparing the Setup CSV File

Before starting a new auction, you need a CSV file containing the initial auction data. You can generate a template using the command mentioned above (`python auction_engine.py --template`).

The CSV file is structured into sections:

*   `[CONFIG]`:
    *   `AuctionName,YourAuctionTitle`: Sets the name of the auction.
*   `[TEAMS_INITIAL]`:
    *   Header: `Team name,Team starting money`
    *   Data: Each row represents a team (e.g., `Team Alpha,5000`).
*   `[PLAYERS_INITIAL]`:
    *   Header: `Player name,Bid value`
    *   Data: Each row represents a player and their base bid (e.g., `Player One,100`).
*   `[BID_INCREMENT_RULES]` (Optional):
    *   Header (optional, but good for clarity): `Threshold,Increment`
    *   Data: Each row defines a rule (e.g., `0,10` means for bids starting at 0, the increment is 10; `100,20` means for bids at or above 100, increment is 20). If this section is omitted or empty, default rules are used.
    *   Lines starting with `#` are comments and are ignored.

### 2. Starting a New Auction

1.  Run `python auction_UI.py`.
2.  Click "START NEW AUCTION".
3.  In the "CREATE NEW AUCTION" screen:
    *   Optionally, edit the "Auction Name" if the one from the CSV isn't desired (though the CSV value will override the entry if `AuctionName` is present in `[CONFIG]`).
    *   Click "BROWSE SETUP FILE" and select your prepared CSV file.
4.  The main auction interface will load with your teams and players.

### 3. Resuming an Auction

1.  Run `python auction_UI.py`.
2.  Click "RESUME AUCTION".
3.  Click "BROWSE LOG FILE" and select the `.auctionlog` file from a previous session.
4.  The auction will load to its last saved state.

### 4. During the Auction

*   **Selecting a Player for Bidding:**
    *   The "👤 AVAILABLE PLAYERS" list on the right shows players yet to be auctioned.
    *   Click on a player's name in this list to bring them up for bidding.
    *   If an item is already active with bids, you'll be asked to confirm, as selecting a new player will pass the current active item.
*   **Placing Bids:**
    *   Each team has a card on the left displaying their name, remaining money, and current inventory.
    *   To bid for the current player, the corresponding team representative clicks the "BID NOW 💸" button on their team's card.
    *   The bid amount automatically increases based on the defined increment rules.
    *   The "STATUS" and "CURRENT ITEM" displays at the top will update with the highest bidder and current bid.
*   **Auctioneer Controls (bottom right):**
    *   `✔️ SELL ITEM`: Sells the current player to the highest bidder. The player is added to the winning team's inventory, and their budget is debited.
    *   `➡️ PASS ITEM`: If no bids are received, or the auctioneer decides not to sell, this button passes the player. The player returns to the "Available Players" pool (unless the behavior is modified for unsold players to be permanently out).
    *   `⏪ UNDO LAST BID`: Reverts the most recent bid, restoring the state to the previous bid (or opening bid if it was the first).
*   **Viewing Logs / Loading History:**
    *   Click the "🕒 LOGS" button in the header.
    *   The "Auction Log History Viewer" will appear.
    *   You can see all logged states. Select a state to view its JSON snapshot.
    *   Click "✔️ LOAD SELECTED STATE" to roll the auction back to the selected historical state. (Use with caution!)

### 5. Log File (`.auctionlog`)

*   An `.auctionlog` file is automatically created/updated in the same directory as the script (or an absolute path if loaded from elsewhere).
*   It contains the initial setup and a chronological record of all auction states in CSV format, with each state snapshot as a JSON string.
*   This file is crucial for resuming auctions and for auditing.


## Contributing 🤝

Contributions, issues, and feature requests are welcome! Please feel free to:
*   Open an issue for bugs or suggestions.
*   Submit a pull request for improvements.

## License 📜

This project is open-source.