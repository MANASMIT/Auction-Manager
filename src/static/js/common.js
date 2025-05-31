 // --- static/js/common.js ---

// Helper to safely update text content
function setText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text || '--'; // Default to '--' if text is null/undefined
    } else {
        // console.warn(`Element with ID '${elementId}' not found.`);
    }
}

// static/js/common.js

// Helper to update image source and visibility
function setImage(elementId, src, altText = "Image") {
    const imgElement = document.getElementById(elementId);
    if (imgElement) {
        if (src && typeof src === 'string' && src.trim() !== '' && src !== '#') { // Check if src is a non-empty string and not just '#'
            imgElement.src = src;
            imgElement.alt = altText;
            imgElement.style.display = 'block'; // Or 'inline', 'inline-block' depending on your layout needs

            // Optional: Add an error handler to hide if the valid-looking src still results in a 404
            imgElement.onerror = function() {
                console.warn(`Image failed to load: ${src}. Hiding element ${elementId}.`);
                imgElement.style.display = 'none';
                imgElement.onerror = null; // Prevent infinite loops if the placeholder also fails
            };
        } else {
            // If src is null, undefined, empty, or just '#', hide the image element
            imgElement.style.display = 'none';
            imgElement.src = '#'; // Clear src to avoid potential lingering request for old image
            imgElement.alt = '';  // Clear alt text
            imgElement.onerror = null; // Clear any previous error handler
        }
    } else {
        // console.warn(`Image element with ID '${elementId}' not found.`);
    }
}

const soldTickerItems = [];
const MAX_TICKER_ITEMS = 10;

function updateSoldTicker(soldItemData) {
    // soldItemData: { player_name, winning_team_name, sold_price, player_photo_path, winning_team_logo_path }
    if (!soldItemData) return;

    soldTickerItems.unshift(soldItemData); // Add to the beginning
    if (soldTickerItems.length > MAX_TICKER_ITEMS) {
        soldTickerItems.pop(); // Remove the oldest
    }

    const tickerUl = document.querySelector('#sold-ticker ul');
    if (tickerUl) {
        tickerUl.innerHTML = ''; // Clear existing items
        soldTickerItems.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${item.player_name}</strong> sold to 
                            <em>${item.winning_team_name}</em> for 
                            ₹${item.sold_price.toLocaleString()}`;
            tickerUl.appendChild(li);
        });
    }
}

function updateCurrentItemDisplay(itemData) {
    // itemData: { name, photo_path, base_bid } or null
    const noItemMsg = document.getElementById('no-item-message');
    const itemNameEl = document.getElementById('item-name');
    // const bidButton = document.getElementById('bid-button'); // Exists in manager view

    if (itemData && itemData.name) {
        if (noItemMsg) noItemMsg.style.display = 'none';
        setText('item-name', itemData.name);
        setImage('item-photo', itemData.photo_path, itemData.name);
        setText('item-base-bid', `₹${itemData.base_bid ? itemData.base_bid.toLocaleString() : 'N/A'}`);
        // if (bidButton) bidButton.disabled = false;
    } else {
        if (noItemMsg) noItemMsg.style.display = 'block';
        setText('item-name', '');
        setImage('item-photo', null);
        setText('item-base-bid', '₹0');
        // if (bidButton) bidButton.disabled = true;
    }
}

function updateBiddingStatusDisplay(bidStatus) {
    // bidStatus: { highest_bidder_name, bidder_logo_path, bid_amount, highest_bidder_exists }
    if (bidStatus) {
        setText('current-bid-amount', `₹${bidStatus.bid_amount ? bidStatus.bid_amount.toLocaleString() : '0'}`);
        if (bidStatus.highest_bidder_exists && bidStatus.highest_bidder_name) {
            setText('highest-bidder-name', bidStatus.highest_bidder_name);
            setImage('bidder-logo', bidStatus.bidder_logo_path, bidStatus.highest_bidder_name + " logo");
        } else {
            setText('highest-bidder-name', '--');
            setImage('bidder-logo', null);
        }
    } else { // Reset if no bidStatus
        setText('current-bid-amount', '₹0');
        setText('highest-bidder-name', '--');
        setImage('bidder-logo', null);
    }
}

function handleItemPassed(data) {
    // data: { item_name }
    console.log(`Item passed: ${data.item_name}`);
    // Could show a temporary notification on the screen
    // The full_state_update should clear the current item section correctly.
    // If there's a specific UI element for "last passed item", update it here.
}

function displayTeamRosterInModal(teamName, teamsData) {
    const team = teamsData[teamName];
    if (!team) return;

    document.getElementById('modal-team-name').textContent = `${teamName}'s Roster (Funds: ₹${team.money.toLocaleString()})`;
    const rosterList = document.getElementById('modal-team-roster-list');
    rosterList.innerHTML = ''; // Clear previous
    if (team.inventory && Object.keys(team.inventory).length > 0) {
        for (const [playerName, price] of Object.entries(team.inventory)) {
            const li = document.createElement('li');
            li.textContent = `${playerName} (₹${price.toLocaleString()})`;
            rosterList.appendChild(li);
        }
    } else {
        rosterList.innerHTML = '<li>No players yet.</li>';
    }
    document.getElementById('team-roster-modal').style.display = 'block';
}

function setupModalCloseButton() {
    const modal = document.getElementById('team-roster-modal');
    const span = document.getElementsByClassName("close-button")[0];
    if (span) {
        span.onclick = function() {
            modal.style.display = "none";
        }
    }
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
}
