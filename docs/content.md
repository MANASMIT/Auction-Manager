# Auction Command - User Documentation

## Introduction

Welcome to Auction Command! This application is designed to provide a robust and user-friendly platform for conducting player auctions. Key features include a powerful [desktop admin panel](#admin-auction-panel) for complete control, real-time [web-based views for presenters and team managers](#webview-features-optional) (often just linked as [Webview Features](#webview-features-optional)), detailed [auction logging and state recovery](#resuming-an-auction), setup via a flexible [CSV file](#csv-setup-file-format), and customizable [bid increment rules](#bid-increment-rules-bid_increment_rules). Whether you're running a small local draft or a more complex auction, Auction Command aims to make the process smooth, transparent, and efficient.

<strong>Version:</strong> 1.6<br>
<strong>Source Code:</strong> <a href="https://github.com/YouFoundJK/Auction-Manager.git">Auction Command | Github</a>

## Getting Started
To begin, launch the Auction Command application.

### Starting a New Auction
1.  On the initial screen, click "**START NEW AUCTION**".
2.  The "CREATE NEW AUCTION" page will appear.
    *   Enter an "**Auction Name**" for your session. This name will be used for display and for the log file.
    *   Click "**BROWSE SETUP FILE**" to select your auction data CSV file. The application will attempt to parse this file.
3.  See the [CSV Setup File Format](#csv-setup-file-format) section for details on how to prepare this file.
4.  If the CSV file is parsed successfully and the auction name is provided, the main auction admin panel will open.

### Resuming an Auction
All auction progress is automatically logged. To resume a previous session:
1.  On the initial screen, click "**RESUME AUCTION**".
2.  If a single `.auctionlog` file (e.g., `MyAuction_20230101_103000.auctionlog`) is found in the same directory as the application, you'll be asked to confirm if you want to resume that auction.
3.  If no logs or multiple logs are found, you'll be prompted to browse and select the desired `.auctionlog` file manually.
4.  The auction will load to its last saved state, allowing you to continue where you left off.

## CSV Setup File Format
The auction setup CSV file is crucial for initializing your auction with teams, players, and custom configurations. The file is divided into sections, each starting with a specific tag (e.g., `[CONFIG]`). Lines starting with `#` are treated as comments and ignored.

<div class="note">
<strong>Important:</strong> You can generate a template CSV by running the application from the command line:
<ul>
  <li><code>python auction_engine.py -t</code> (generates <code>auction_setup_template.csv</code> in the current directory)</li>
  <li><code>python auction_engine.py -t -o your_custom_name.csv</code> (generates a template with a custom filename)</li>
</ul>
This template provides the correct headers and structure.
</div>

### Config Section (`[CONFIG]`)
This section defines global auction settings.
```csv
[CONFIG]
AuctionName,My Grand Auction
#Date,YYYY-MM-DD (This is logged automatically, not set here)
#Time,HH:MM:SS (This is logged automatically, not set here)
```
-   `AuctionName`: The name of your auction. If provided here, it can pre-fill the name field when creating a new auction. The name entered in the UI takes precedence.

### Teams Section (`[TEAMS_INITIAL]`)
Defines the participating teams.
```csv
[TEAMS_INITIAL]
Team name,Team starting money,Logo Path
Team Alpha,50000,Team-Alpha-logo.png
Team Bravo,48000,Team-Bravo-logo.jpg
Team Charlie,52000,
# Last team has no logo specified
```
-   The header row `Team name,Team starting money,Logo Path` **is required**.
-   `Team name`: The unique name of the team.
-   `Team starting money`: The initial budget available to the team.
-   `Logo Path`: (Optional) Filename of the team's logo (e.g., `Team-Alpha-logo.png`). See [Image Paths for Logos and Photos](#image-paths-for-logos-and-photos) for critical details. If left blank, no logo will be associated.

### Players Section (`[PLAYERS_INITIAL]`)
Defines the players available for auction.
```csv
[PLAYERS_INITIAL]
Player name,Bid value,Profile Photo Path
Player One,1000,Player-One.png
Player Two (WK),800,Player-Two-(WK).jpg
Player Three (BAT),1200,
# Last player has no photo specified
```
-   The header row `Player name,Bid value,Profile Photo Path` **is required**.
-   `Player name`: The unique name of the player. You can include role indicators like "(WK)", "(BAT)", "(BOWL)", "(ALL)" directly in the name; these will be part of the display name.
-   `Bid value`: The base/starting bid amount for the player.
-   `Profile Photo Path`: (Optional) Filename of the player's profile photo (e.g., `Player-One.png`). See [Image Paths for Logos and Photos](#image-paths-for-logos-and-photos). If left blank, no photo will be associated.

### Bid Increment Rules (`[BID_INCREMENT_RULES]`)
(Optional) This section allows you to define custom bid increment rules. If this section is omitted, or if all rules are commented out/invalid, default bid increments will be used by the auction engine.
```csv
[BID_INCREMENT_RULES]
#Threshold,Increment (Header for clarity, not strictly parsed as one)
0,100
5000,200
10000,500
20000,1000
# Rules are evaluated from highest threshold downwards.
# Example: If current bid is 12000:
# - It's >= 10000, so next increment is 500. Next bid = 12500.
# Example: If current bid is 700:
# - It's >= 0, so next increment is 100. Next bid = 800.
```
-   Each data row defines a rule consisting of a `Threshold` and an `Increment`.
-   `Threshold`: If the current bid amount is greater than or equal to this value...
-   `Increment`: ...then the next bid will increase by this amount.
-   The engine sorts these rules by threshold in descending order to find the appropriate increment. Ensure your thresholds are non-negative and increments are positive.

### Image Paths (for Logos and Photos)
<div class="warning">
<strong>Action Required by Admin:</strong> For logos and profile photos to appear correctly in the web views (Presenter and Team Manager), you must follow these steps:
<ol>
  <li>Create a folder named <code>static</code> in the same directory where your Auction Command application executable (or main <code>.py</code> script) is located.</li>
  <li>Inside the <code>static</code> folder, create another folder named <code>images</code>. The full path will be <code>[YourAppDirectory]/static/images/</code>.</li>
  <li>Place all your team logo files and player photo files directly into this <code>static/images/</code> directory.</li>
</ol>
</div>

-   **In the CSV file:**
    -   For `Logo Path` and `Profile Photo Path` columns, specify **only the filename with its extension** (e.g., `Team-Alpha-logo.png`, `Player-One.jpg`).
    -   **Do NOT include any part of the path** (like `static/images/` or `C:\Users\...`) in the CSV. The application automatically looks for these files in the `static/images/` folder.
-   **Filename Sanitization:**
    -   The application tries to match filenames based on the names provided in the CSV.
    -   For **player photos**, if a player name is "Player X (WK)", the application will look for a file like `Player-X-(WK).png` (or other supported extensions). Spaces are converted to hyphens, and parentheses are preserved.
    *   For **team logos**, if a team name is "Team Alpha", the application will look for `Team-Alpha-logo.png`. The suffix "-logo" is appended before searching.
    -   It's highly recommended to pre-name your image files to match this sanitized format to ensure they are found. For example, if a player is "Player (Superstar!)" in the CSV, name the image file `Player-(Superstar!).png`.
-   **Supported Formats:** Common web formats like PNG, JPG/JPEG, GIF, and WEBP should work. PNG is generally recommended for logos with transparency.
-   If an image file is not found or not specified, a default placeholder or no image will be shown in the web views.

## Admin Auction Panel

### Overview
The main admin panel is your central hub for conducting the auction. It displays:
-   **Top Menu Bar:** Access to file operations, webview controls, logs, and help. (Press `Alt` to toggle if only "▼ Menu" is visible).
-   **Header:**
    -   **Auction Name:** The name of the current auction.
    -   **Current Item:** Displays the player currently up for bidding, including their name and base bid.
    -   **Status:** Shows the current highest bid amount and the name of the highest bidding team.
-   **Teams Overview (Main Left Area):**
    -   Scrollable section with cards for each participating team.
    -   Each card shows the team's name, logo (if provided correctly via CSV & image path), remaining money, and a list of players they have acquired.
    -   A "**BID NOW 💸**" button on each team card allows the admin to place a bid for that team.
-   **Available Players (Right Sidebar - Top):**
    -   A scrollable list of all players who are still available to be auctioned.
    -   Each player entry shows their name and base bid.
    -   Click on a player in this list to select them for bidding.
-   **Auction Controls (Right Sidebar - Bottom):**
    -   Buttons to manage the bidding process for the currently selected item: **SELL ITEM**, **PASS ITEM**, **UNDO LAST BID**.

### Menu Bar (Top Left)
The menu bar provides access to various application functions:
-   Initially, you might see a "**▼ Menu**" button. Click it (or press the `Alt` key) to expand/collapse the full menu.
-   **File**
    -   `Exit`: Closes the Auction Command application. It will save the current auction state to the log file and attempt to shut down the web server if it's running.
-   **View**
    -   `Start/Stop Presenter Webview`: Toggles the presenter webview. If starting, it ensures the web server is running (starting it if necessary) and may open `http://localhost:5000/presenter` in your default web browser.
    -   `Enable/Disable Manager Access`: Toggles the team manager webviews. Enabling this ensures the web server is running and generates unique, secure access tokens for each team. Disabling it revokes access.
    -   `Show Manager Links`: If manager access is enabled, this opens a new window displaying the unique access URLs for each team manager. These URLs include the access tokens.
    -   `Show Logs`: Opens the "Auction Log History Viewer" window, allowing you to inspect past auction states and potentially revert to one.
-   **Help**
    -   `Documentation`: Opens this user documentation file in your default web browser.
    -   `About`: Displays a small window with version information about Auction Command.

### Selecting a Player for Bidding
1.  In the "Available Players" list on the right, click on the name of the player you want to put up for auction.
2.  This player will become the "Current Item" displayed in the header. Their base bid will be the initial "Current Bid Amount".
3.  **Automatic Passing Logic:**
    *   If another player was previously selected as the "Current Item" **and had no bids placed on them**, that player is automatically passed (returned to the "Available Players" list) when you select a new player.
    *   If another player was previously selected **and had active bids on them**, you will be shown a confirmation dialog. If you confirm you want to select the new player, the previously active player (with bids) will be passed and returned to the "Available Players" list. This ensures no item with active bidding is accidentally discarded.

### Placing Bids (Admin)
Once a player is selected as the "Current Item":
1.  Locate the card of the team you want to bid for in the "Teams Overview" section.
2.  Click the "**BID NOW 💸**" button on that team's card.
3.  The bid amount will automatically increment based on the current bid and the defined [Bid Increment Rules](#bid-increment-rules).
4.  The "Status" in the header will update to show the new highest bid and the bidding team.
5.  The bidding team's remaining money will be checked. If they cannot afford the new bid, an error message will appear, and the bid will not be placed.

### Selling an Item
When you are ready to conclude bidding for the "Current Item":
1.  Ensure there is a "Highest Bidder" displayed in the status.
2.  Click the "**SELL ITEM**" button in the "Auction Controls" section.
3.  The player will be sold to the highest bidding team for the current bid amount.
    *   The player is added to the winning team's inventory.
    *   The bid amount is deducted from the winning team's money.
    *   The "Current Item" and "Status" will reset, ready for the next player.
    *   The sold player is removed from the "Available Players" list.
4.  A confirmation message will appear.

### Passing an Item
If you want to withdraw the "Current Item" from bidding without selling:
1.  Click the "**PASS ITEM**" button in the "Auction Controls" section.
2.  If the item had active bids, you will be asked to confirm that you want to pass it.
3.  The player will be returned to the "Available Players" list.
4.  The "Current Item" and "Status" will reset.
5.  A confirmation message will appear.

### Undoing the Last Bid
If a bid was placed in error or needs to be retracted:
1.  Click the "**UNDO LAST BID**" button.
2.  The most recent bid will be removed. The "Status" will revert to the previous highest bid and bidder, or to the opening bid if it was the only bid.
3.  This action cannot be used if the item has already been "SOLD" or "PASSED". It only affects bids on the currently active item.

### Auction Log History Viewer
Accessed via "View > Show Logs" from the menu bar. This powerful tool allows you to:
-   **View Past States:** See a chronological list of all significant auction events (item selection, bids, sales, passes) along with their timestamps and any comments.
-   **Inspect JSON Snapshots:** For each logged state, you can click "Show JSON Details ►" to view the raw JSON data representing the complete auction state at that moment (team funds, inventories, available players, current bidding item, etc.).
-   **Load Selected State:**
    1.  Select an entry in the log list.
    2.  Click the "**✔️ LOAD SELECTED STATE**" button.
    3.  Confirm the action. The auction will revert to the exact state recorded in that log entry.
    <div class="warning">
    <strong>Caution:</strong> Loading a past state is a powerful action. It overwrites the current auction progress with the selected historical state. This is useful for correcting major errors but should be used carefully.
    </div>

## Webview Features (Optional)
Auction Command can provide real-time web-based views for presenters and team managers. These are optional and require additional Python libraries to be installed.

**Installation for Webviews:**
Open a terminal or command prompt and run:
`pip install Flask Flask-SocketIO eventlet requests`
-   `Flask` and `Flask-SocketIO` are for the web server and real-time communication.
-   `eventlet` is a recommended high-performance web server for SocketIO.
-   `requests` is used by the admin panel to communicate with the web server for shutdown.

### Enabling Webviews
Control the webviews from the admin panel's menu bar ("View" section):
-   **Start/Stop Presenter Webview:** Toggles the live presenter display. When started, the application ensures the web server is running (it will start it if it's not already active). It may also attempt to open the presenter page (`http://localhost:5000/presenter`) in your default web browser.
-   **Enable/Disable Manager Access:** Toggles the availability of individual team manager views. When enabled, the web server is started (if not already active), and secure access tokens are generated for each team.
-   **Show Manager Links:** If manager access is currently enabled, selecting this opens a new window displaying the unique access URLs for each team manager. These URLs are essential for managers to access their views.

The web server, by default, runs on `http://localhost:5000`. If the computer running Auction Command is on a local network (e.g., Wi-Fi), other devices on the same network can typically access these views by replacing `localhost` with the host computer's local IP address (e.g., `http://192.168.1.10:5000/presenter`), provided your firewall allows connections on port 5000.

### Presenter View
-   **URL:** `http://localhost:5000/presenter` (or using the host PC's local IP).
-   **Purpose:** A read-only view designed for public display (e.g., on a projector).
-   **Features:**
    -   **Current Item:** Prominently displays the player currently up for bidding, including their name, photo (if available), and base bid.
    -   **Bidding Status:** Shows the current highest bid amount and the name/logo of the highest bidding team in real-time.
    -   **Sold Item Ticker:** A scrolling or updating list of recently sold players, showing who bought them and for how much.
    -   **Team Overview:** A display of all participating teams, often with their logos and remaining funds. Clicking on a team typically opens a modal/popup showing their current roster of acquired players.

### Team Manager View
-   **URL:** Unique for each team, e.g., `http://localhost:5000/manager/TeamAlpha/aBcDeFgHiJkLmNoPqRsTuV`
    -   These URLs are obtained from the "Show Manager Links" window in the admin panel. Each URL contains a secure access token.
-   **Purpose:** Allows individual team managers to monitor the auction and participate by placing bids for their team.
-   **Features:**
    -   **My Team Status:** Displays their team's name, logo, current funds, and acquired player roster.
    -   **Current Item:** Shows the player currently up for bidding (same as presenter view).
    -   **Place Bid Button:** A button allowing the manager to bid for the current item on behalf of their team.
        -   This button is only active when an item is up for bidding, their team is not already the highest bidder, and they have sufficient funds for the next calculated bid increment.
    -   **Overall Bidding Status:** Shows the current highest bid and bidder.
    -   **Other Teams' Rosters:** Often a dropdown or list to view the current rosters of other participating teams.
    -   **Sold Item Ticker:** Similar to the presenter view.

### Bidding from Manager View
When an item is selected by the admin and available for bidding:
1.  The "Place Bid" button in an eligible team manager's web view becomes active.
2.  If the manager clicks this button, a bid is submitted for their team.
3.  The auction engine (controlled by the admin panel) processes this bid as if the admin had manually placed it for that team.
4.  All views (admin panel, presenter, all manager views) update in real-time to reflect the new bid status.
5.  If a bid from the web manager is invalid (e.g., insufficient funds by the time it's processed, item sold just before), an error message might appear in their web view.

### Manager Access Links Window
-   Accessed via "View > Show Manager Links" in the admin panel's menu bar (only available if "Manager Access" is enabled).
-   This window lists each team name alongside its unique, secure URL for the Team Manager View.
-   Each URL contains an access token specific to that team.
-   **It is the administrator's responsibility to securely distribute these links to the correct team managers.**
-   A "Copy" button is provided next to each link for convenience.
-   If manager access is disabled and then re-enabled, new tokens (and thus new links) will be generated. The old links will no longer work.

## Troubleshooting

### Firewall Issues (Webview Access from Other Devices)
If you can access webviews on `localhost` but not from other devices on your network:
-   **Host Setting:** The Flask server in Auction Command is configured to listen on `0.0.0.0`, which is correct for network access.
-   **Firewall:** Your computer's firewall (e.g., Windows Defender Firewall, or third-party antivirus/firewall software) is likely blocking incoming connections.
    -   You need to create an **inbound rule** to allow connections on the TCP port the server is using (default is **5000**).
    -   Consult your firewall software's documentation for instructions on adding an inbound port rule.
-   **Network:** Ensure the device trying to access the webview is on the *same local network* as the PC running Auction Command (e.g., connected to the same Wi-Fi router).
-   **IP Address:** Use the correct local IP address of the host PC in the URL (e.g., `http://192.168.1.10:5000/presenter`). You can usually find your PC's local IP address in your network settings or by running `ipconfig` (Windows) or `ifconfig`/`ip addr` (Linux/macOS) in a command prompt/terminal.

### Images Not Showing in Webviews
-   **Directory:** Crucially, verify that you have created the `static/images/` directory structure (`[YourAppDirectory]/static/images/`) as described in the [Image Paths](#image-paths-for-logos-and-photos) section.
-   **File Placement:** Ensure all your logo and photo image files are placed *directly* inside this `static/images/` folder.
-   **Filenames in CSV:** Double-check that the filenames specified in the `Logo Path` and `Profile Photo Path` columns of your CSV file **exactly match** the actual filenames in the `static/images/` folder. This includes the file extension (e.g., `.png`, `.jpg`). File matching can be case-sensitive on some systems.
-   **Filename Sanitization:** Remember the application sanitizes names for file lookups (e.g., "Player X (WK)" becomes `Player-X-(WK).png`, "Team Alpha" becomes `Team-Alpha-logo.png`). It's best if your actual image filenames already match this pattern.
-   **Browser Console:** If images are still missing, open your web browser's developer console (usually by pressing `F12`) and look at the "Network" tab or "Console" tab for any 404 (Not Found) errors related to image URLs. This can help pinpoint which files are not being loaded.

### Web Server Port Issues
-   **"Address already in use" / Port 5000 Error:** If the application fails to start the web server and you see an error message mentioning that the address (specifically port 5000) is already in use, it means another application on your computer is currently using that port.
    -   You'll need to identify and close the other application, or (if this were a configurable feature, which it currently is not) change the port Auction Command uses.
-   **Server Fails to Start:** Check the command prompt or terminal window where you launched Auction Command (if you ran it from source) for any error messages related to Flask or SocketIO.
-   **Server Fails to Stop / "Please Wait" Overlay Stuck:**
    -   When stopping webviews or exiting the app, a "Please Wait: Shutting down..." overlay may appear. This indicates the admin panel is trying to tell the web server to shut down.
    -   If this process takes too long or seems stuck, the web server might not have responded. You can try closing the main application window. In rare cases, the web server's Python process might remain running in the background. You might need to manually terminate it via your operating system's Task Manager (look for Python processes).

### Common Application Errors or Warnings
-   **Engine Warnings:** The auction engine may sometimes produce non-critical warnings (e.g., an invalid bid increment rule in the CSV was skipped, using defaults instead). These are often displayed in a pop-up message box after certain operations (like loading an auction). Read them, as they might indicate minor issues with your setup.
-   **CSV Parsing Errors:** If there's a problem with the format or data in your setup CSV file, the application will usually show an error message indicating the line number and the nature of the problem during the "New Auction" setup process. Correct the CSV file and try again.
-   **Log File Errors:** If a `.auctionlog` file is corrupted or cannot be read during a "Resume Auction" attempt, an error will be shown.

---

## FAQ
**Q: Can I change bid increment rules mid-auction?**

A: No. Bid increment rules are set when an auction is first created (from the setup CSV file or using defaults if not specified) or when an auction is resumed (loaded from its log file). They cannot be modified through the admin panel UI during an active auction session.

**Q: How are player roles (like WK, BAT, BOWL, ALL) handled?**

A: Player roles are primarily for display purposes. If you include them in the "Player name" field in your setup CSV (e.g., "Player X (WK)"), they will appear as part of the player's name in lists and when they are selected for bidding. The auction engine itself does not currently have specific logic or rules based on these roles (e.g., roster composition rules).

**Q: What happens if I close the admin panel unexpectedly (e.g., power outage, crash)?**

A: The application logs the auction state after most significant actions (bids, sales, passes). If the application closes unexpectedly, you should be able to "Resume Auction" and load the last successfully logged state. Some very recent, unlogged actions might be lost. The web server (if active) might also remain running if the shutdown sequence was interrupted; see "Server Fails to Stop" in Troubleshooting.

**Q: Where is the `.auctionlog` file saved?**

A: The `.auctionlog` file is saved in the same directory where the Auction Command application executable (or main `auction_UI.py` script if running from source) is located. The filename typically includes the auction name and a timestamp (e.g., `MyAuction_20231027_143000.auctionlog`).

**Q: How do the team manager access tokens work? Are they persistent?**

A: Access tokens are unique, randomly generated strings created for each team when "Enable Manager Access" is toggled on in the admin panel. These tokens are part of the URLs provided in the "Show Manager Links" window.
    -   They are **not persistent** across disabling and re-enabling manager access. If you disable manager access and then enable it again, **new tokens will be generated**, and the old manager links will no longer work. You would need to redistribute the new links.
    -   They are, however, persistent for the duration that "Manager Access" remains enabled within a single application session.

**Q: Can I customize the appearance of the presenter or team manager web views?**

A: Not directly through settings within the Auction Command application. Customizing the visual appearance (colors, layout, fonts) of the web views would require modifying the underlying HTML (`templates/*.html`), CSS (`static/css/*`), and potentially JavaScript (`static/js/*`) files. This is an advanced modification.

**Q: What is the "Please Wait: Shutting down..." overlay for?**

A: This overlay appears when the admin panel is performing a potentially time-consuming background operation, specifically when it's trying to communicate with the web server to request its shutdown. It's there to let you know the application is busy and to prevent further interaction until the process completes or times out.