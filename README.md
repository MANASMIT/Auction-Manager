# Auction Command - v1.7

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-green.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Docs](https://img.shields.io/badge/Documentation-v_1.7-blue)](https://youfoundjk.github.io/Auction-Command/)

**Auction Command** is a desktop application designed to streamline player auctions with powerful admin controls and optional real-time web interfaces for team managers and audiences. Whether you're managing a sports league, fantasy draft, or any structured bidding event, Auction Command provides a robust and user-friendly auctioning experience.


## 🚀 Quick Start
1. Download the latest Release from [here](https://github.com/YouFoundJK/Auction-Command/releases/latest).
2. Extract it and run the executable file.
3. Use 'START NEW ACTION' -> 'View .csv format help' then 'Browse Setup File' and load the `.csv` file that has appeared next to the executable file.
4. You are ready to go. Enjoy!

---

## Key Features

### 🎛️ Admin Panel (Desktop App - Tkinter)

* Load auction data from a CSV file (teams, players, budget, base bids).
* Live dashboard with bidding status, available players, and team funds.
* Run auctions smoothly:

  * Select players for auction.
  * Place and track bids.
  * Sell or pass items.
  * Undo previous bids.
* Supports custom bid increment rules.
* Logs all auction actions to a `.auctionlog` file.
* Resume auctions from saved logs.
* View full bidding history.

### 🌐 Web-Based Interfaces (Optional)

#### Presenter View

* Read-only, real-time stream for audiences.
* Displays:

  * Current player (with photo)
  * Highest bid and bidder (with logo)
  * Ticker of recently sold players
* Accessible over local network via web browser.

#### Team Manager View

* Unique, secure access links per team.
* Allows team managers to:

  * View their roster, budget, and bid status.
  * Place live bids.
  * Preview potential bids and remaining funds.
  * View other team rosters.
* Web interface accessible from any browser on the local network.

### 🖼️ Image Support

* Display team logos and player photos in the web views.
* Files served from a local `static/images/` directory.
* Browsers automatically cache assets for performance.

---

## 📁 Directory Structure for Images

1. Create a folder:

   ```
   static/images/
   ```
2. Place all image files (team logos and player photos) here.
3. In your CSV setup, refer to images using **just the filename**:
   Example: `Team-Logo.png`, `Player1.jpg`

---

## 📄 CSV Format

The auction setup is based on a structured CSV file. Key sections include:

* `[CONFIG]` – General auction settings (e.g., auction name).
* `[TEAMS_INITIAL]` – List of teams with their starting money and logo image.
* `[PLAYERS_INITIAL]` – Player list with base bid values and profile photo names.
* `[BID_INCREMENT_RULES]` – *(Optional)* Define bid increments based on price ranges.

💡 Use the built-in documentation or generate a template to ensure correct formatting.

---
## 🌐 Webview Setup

Access web features from the Admin Panel's top menu:

### Presenter View

* Go to:
  `Admin Panel > Start Presenter Webview`
* Access in browser at:

  ```
  http://<your_pc_ip>:5000/presenter
  ```

### Team Manager View

* Enable access:
  `Admin Panel > Enable Manager Access`
* Show secure team URLs:
  `Admin Panel > Show Manager Links`
* Team managers access their dashboards at:

  ```
  http://<your_pc_ip>:5000/manager/<TeamName>/<AccessToken>
  ```

> 🛡️ Ensure firewall settings allow connections to port 5000 for local network access.

---

## 📚 Documentation

Check [here](https://youfoundjk.github.io/Auction-Command/) or access the same offline within the app at:

```
Admin Panel > Help > Documentation
```

Includes instructions for:

* CSV formatting
* Image setup
* Webview configuration
* Resuming from logs

---

## 🤝 Contributing

We welcome contributions, bug reports, and feature requests!
Feel free to [submit an issue](https://github.com/YouFoundJK/AuctionCommand/issues) or fork the repo and open a merge request.
---

## 🛠️ Tech Stack

* **Frontend:** Tkinter (desktop), HTML/CSS (webviews)
* **Backend:** Python (Flask for web interface)
* **File Handling:** CSV for data, local file system for images
* **Logging:** Custom `.auctionlog` format for state saving and recovery

