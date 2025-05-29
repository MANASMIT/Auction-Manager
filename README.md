# Auction Command 🏏⚽️🏆

Auction Command is a desktop application designed to manage player auctions smoothly and efficiently, with optional web-based views for presenters and team managers. It's ideal for sports leagues, fantasy drafts, or any scenario requiring a structured bidding process.

## ✨ Features

*   **Intuitive Admin Panel (Tkinter GUI):**
    *   Load auction setup from a CSV file (teams, players, starting money, base bids).
    *   Clear overview of teams, available players, and current bidding status.
    *   Select players for auction.
    *   Place bids for teams directly from the admin panel.
    *   Sell items to the highest bidder or pass items.
    *   Undo the last bid.
    *   Customizable bid increment rules.
    *   Automatic logging of all auction states and events to a `.auctionlog` file.
    *   Resume auctions from log files.
    *   View auction history from logs.
*   **Optional Web-Based Presenter View:**
    *   Live, read-only stream of the auction for an audience.
    *   Displays current item (with photo), bidding status (highest bidder with logo), and a ticker of recently sold items.
    *   Accessible via a web browser on the local network.
*   **Optional Web-Based Team Manager View:**
    *   Secure, unique access links for each team manager.
    *   Displays their team's status (funds, roster, logo).
    *   Shows current item for bidding and overall bidding status.
    *   Allows managers to place bids for their team directly from their web browser.
    *   Calculates and displays the "next potential bid" and "money left after bid" for easier decision-making.
    *   Ability to view other teams' rosters.
*   **Offline HTML Documentation:**
    *   Built-in help accessible from the admin panel, detailing setup and features.
*   **Image Handling:**
    *   Supports team logos and player profile photos in web views.
    *   Images are served from a local `static/images` directory and cached by browsers.

**Image Setup:**

1.  Create a directory structure `static/images/` in the root of the project directory (alongside `auction_UI.py`).
2.  Place all your team logo files and player photo files into this `static/images/` directory.
3.  In your auction setup CSV, for `Logo Path` and `Profile Photo Path` columns, specify **only the filename** (e.g., `My-Team-Logo.png`, `Player-One.jpg`).

## 🚀 Running the Application

1.  **Activate your virtual environment** (if you created one).
2.  **Run the main UI script:**
    ```bash
    python auction_UI.py
    ```
3.  **To generate a CSV template (optional):**
    ```bash
    python auction_engine.py -t -o my_auction_template.csv
    ```
    This will create `my_auction_template.csv` in the current directory. Fill it out according to the format specified in the template and the built-in documentation.

## 📄 CSV File Format

The application uses a CSV file to load initial auction data. Key sections include:

*   `[CONFIG]`: Auction name.
*   `[TEAMS_INITIAL]`: Team names, starting money, and logo filenames.
*   `[PLAYERS_INITIAL]`: Player names, base bid values, and profile photo filenames.
*   `[BID_INCREMENT_RULES]`: (Optional) Custom bid increment thresholds and values.

Refer to the built-in documentation (Help > Documentation in the app) or the generated template for detailed formatting.

## 🌐 Using Webview Features

1.  From the admin panel's top menu:
    *   **Presenter View:** Click "Start Presenter Webview". Access at `http://<your_pc_ip>:5000/presenter`.
    *   **Team Manager View:**
        *   Click "Enable Manager Access".
        *   Click "Show Manager Links" to get unique URLs for each team manager.
        *   Share these URLs with the respective managers. They can access their view at `http://<your_pc_ip>:5000/manager/<TeamName>/<AccessToken>`.
2.  Ensure your PC's firewall allows connections on port 5000 (or the configured port) if accessing from other devices on the network.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to check the [issues page](https://your-github-repo-url/AuctionCommand/issues).

## 📝 License

Provided under MIT License.
