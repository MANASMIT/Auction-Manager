// --- static/js/manager.js ---
document.addEventListener('DOMContentLoaded', () => {
    let ACCESS_TOKEN = null;
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length >= 4 && pathParts[1] === 'manager') {
        ACCESS_TOKEN = pathParts[3];
    }

    if (typeof MY_TEAM_NAME === 'undefined' || !ACCESS_TOKEN) {
        document.body.innerHTML = '<h1 style="color: red; text-align: center; margin-top: 50px;">Error: Manager context (Team Name or Access Token) is missing. Cannot connect.</h1>';
        console.error("MY_TEAM_NAME or ACCESS_TOKEN is not defined.");
        return;
    }

    const socket = io('/manager', {
        auth: {
            team_name: MY_TEAM_NAME,
            access_token: ACCESS_TOKEN
        }
    });
    
    let currentItemNameGlobal = null;
    let currentPhotoPathGlobal = null; // To cache the current photo path
    let allTeamsDataCache = {};

    // UI Element Getters
    const DEFAULT_PLAYER_PHOTO = '/assets/default-player.png';
    const myTeamFundsEl = document.getElementById('my-team-funds');
    
    // const noItemMessageEl = document.getElementById('no-item-message'); // REMOVED
    // const playerContentEl = document.getElementById('player-content'); // No longer toggled
    const itemPhotoEl = document.getElementById('item-photo');
    const itemNameEl = document.getElementById('item-name');
    const itemBaseBidEl = document.getElementById('item-base-bid');
    
    const currentBidAmountEl = document.getElementById('current-bid-amount');
    const currentBidderSectionEl = document.getElementById('current-bidder-section');
    const highestBidderNameEl = document.getElementById('highest-bidder-name');
    
    const nextBidValueEl = document.getElementById('next-bid-value');
    const moneyLeftAfterBidEl = document.getElementById('money-left-after-bid');
    const bidButton = document.getElementById('bid-button');
    const bidFeedbackEl = document.getElementById('bid-feedback');

    const myTeamRosterUl = document.getElementById('my-team-roster');
    const otherTeamsDropdown = document.getElementById('other-teams-dropdown');
    const otherTeamInfoDiv = document.getElementById('other-team-info');
    const otherTeamNameDisplayEl = document.getElementById('other-team-name-display');
    const otherTeamFundsEl = document.getElementById('other-team-funds');
    const otherTeamRosterUl = document.getElementById('other-team-roster-display');
    const soldTickerUl = document.querySelector('#sold-ticker ul');

    let lastFeedbackClearTimeout = null;

    function setBidFeedback(message, isError = false, autoClearDelay = 5000) {
        if (bidFeedbackEl) {
            clearTimeout(lastFeedbackClearTimeout); // Clear any existing auto-clear timeout

            if (message && message.trim() !== '') {
                bidFeedbackEl.textContent = message;
                bidFeedbackEl.className = 'feedback-message ' + (isError ? 'error' : 'success');
                
                // Auto-clear feedback after a delay, reverting to placeholder
                if (autoClearDelay > 0) {
                    lastFeedbackClearTimeout = setTimeout(() => {
                        bidFeedbackEl.textContent = '--';
                        bidFeedbackEl.className = 'feedback-message'; // Revert to default style
                    }, autoClearDelay);
                }
            } else { // No message, set to placeholder
                bidFeedbackEl.textContent = '--';
                bidFeedbackEl.className = 'feedback-message'; // Default style
            }
        }
    }

    function updateManagerCurrentItemDisplay(itemData) {
        const newPlayerName = (itemData && itemData.name) ? itemData.name : null;
        let newPhotoPath = itemData ? itemData.photo_path : DEFAULT_PLAYER_PHOTO;

        if (itemData && itemData.photo_path && itemData.photo_path.trim() !== '' && itemData.photo_path !== '#') {
            const img = new Image();
            img.onload = () => {
                newPhotoPath = itemData.photo_path;
            };
            img.onerror = () => {
                newPhotoPath = DEFAULT_PLAYER_PHOTO;
            };
            img.src = itemData.photo_path;
        } else {
            newPhotoPath = DEFAULT_PLAYER_PHOTO;
        }

        // Always ensure the image element is visible
        if (itemPhotoEl) {
            itemPhotoEl.style.display = 'block';
        }

        if (newPlayerName) { // Player is active
            if (newPlayerName !== currentItemNameGlobal) { // Player has changed
                currentItemNameGlobal = newPlayerName;
                currentPhotoPathGlobal = newPhotoPath; // Reset cached path for new player
                if (itemPhotoEl) {
                    itemPhotoEl.src = newPhotoPath;
                    itemPhotoEl.alt = newPlayerName + " photo";
                }
            } else { // Same player, check if photo path itself changed (e.g., admin updated it)
                if (newPhotoPath !== currentPhotoPathGlobal && itemPhotoEl) {
                    itemPhotoEl.src = newPhotoPath;
                    currentPhotoPathGlobal = newPhotoPath; // Update cache
                    // Alt text likely remains the same if only photo URL changed for the same player
                }
            }
            
            if (itemNameEl) itemNameEl.textContent = newPlayerName;
            if (itemBaseBidEl) itemBaseBidEl.textContent = `₹${itemData.base_bid ? itemData.base_bid.toLocaleString() : '0'}`;

        } else { // No player active or item is null
            currentItemNameGlobal = null;
            currentPhotoPathGlobal = DEFAULT_PLAYER_PHOTO; // Reset cache to default

            if (itemNameEl) itemNameEl.textContent = 'Waiting for Player...';
            if (itemPhotoEl) {
                itemPhotoEl.src = DEFAULT_PLAYER_PHOTO;
                itemPhotoEl.alt = 'Player Photo Placeholder';
            }
            if (itemBaseBidEl) itemBaseBidEl.textContent = '₹--';
            if (currentBidAmountEl) currentBidAmountEl.textContent = '₹--';
            if (highestBidderNameEl) highestBidderNameEl.textContent = '--';
            if (nextBidValueEl) nextBidValueEl.textContent = '--';
            if (moneyLeftAfterBidEl) moneyLeftAfterBidEl.textContent = '--';
            if (bidButton) {
                bidButton.disabled = true;
                bidButton.textContent = `Place Bid for ${MY_TEAM_NAME}`;
            }
            setBidFeedback(''); 
        }

        // Add error handler for the image to fallback to default if a specific player image fails
        if (itemPhotoEl && itemPhotoEl.src !== DEFAULT_PLAYER_PHOTO) {
            itemPhotoEl.onerror = function() {
                console.warn(`Image failed to load: ${itemPhotoEl.src}. Falling back to default.`);
                itemPhotoEl.src = DEFAULT_PLAYER_PHOTO;
                itemPhotoEl.alt = currentItemNameGlobal ? `${currentItemNameGlobal} (Photo Error)` : 'Player Photo Placeholder';
                itemPhotoEl.onerror = null; // Prevent infinite loop if default also fails
            };
        } else if (itemPhotoEl) {
            itemPhotoEl.onerror = null; // Clear error handler if it's already the default
        }
    }

    function updateManagerBiddingStatusDisplay(bidStatus) {
        if (bidStatus && currentItemNameGlobal) {
            if (currentBidAmountEl) currentBidAmountEl.textContent = `₹${bidStatus.bid_amount ? bidStatus.bid_amount.toLocaleString() : '0'}`;
            
            if (bidStatus.highest_bidder_exists && bidStatus.highest_bidder_name) {
                if (highestBidderNameEl) highestBidderNameEl.textContent = bidStatus.highest_bidder_name;
            } else {
                if (highestBidderNameEl) highestBidderNameEl.textContent = '--'; // Placeholder
            }
        } else {
            if (currentBidAmountEl) currentBidAmountEl.textContent = '₹--';
            if (highestBidderNameEl) highestBidderNameEl.textContent = '--'; // Placeholder
        }
        // currentBidderSectionEl is always visible by default css/html structure
    }
    
    function updateMoneyLeftStyling() {
        if (moneyLeftAfterBidEl && moneyLeftAfterBidEl.textContent !== '--' && moneyLeftAfterBidEl.textContent.trim() !== '') {
            const rawValue = moneyLeftAfterBidEl.textContent.replace(/[₹,]/g, '');
            if (rawValue === '' || isNaN(rawValue)) {
                 moneyLeftAfterBidEl.className = 'money-left-value'; 
                 return;
            }
            const value = parseInt(rawValue);
            moneyLeftAfterBidEl.className = 'money-left-value ' + (value >= 0 ? 'positive' : 'negative');
        } else if (moneyLeftAfterBidEl) {
            moneyLeftAfterBidEl.className = 'money-left-value'; 
        }
    }
    setInterval(updateMoneyLeftStyling, 500);

    function updateManagerSoldTicker(soldItemData) {
        if (!soldItemData || !soldTickerUl) return;
        
        const li = document.createElement('li');
        li.className = 'sold-item';
        li.innerHTML = `<strong>${soldItemData.player_name}</strong> sold to 
                        <em>${soldItemData.winning_team_name}</em> for 
                        ₹${soldItemData.sold_price.toLocaleString()}`;
        soldTickerUl.insertBefore(li, soldTickerUl.firstChild);
        
        while (soldTickerUl.children.length > 10) { 
            soldTickerUl.removeChild(soldTickerUl.lastChild);
        }
    }

    function renderRoster(ulElement, inventory, isMyTeam = false) {
        if (!ulElement) return;
        ulElement.innerHTML = '';
        if (inventory && Object.keys(inventory).length > 0) {
            for (const [player, price] of Object.entries(inventory)) {
                const li = document.createElement('li');
                li.className = 'roster-item';
                li.innerHTML = `
                    <span>${player}</span>
                    <span class="player-prices">
                        Sold: ₹${price.sold_price.toLocaleString()}
                        (Base: ₹${price.base_bid ? price.base_bid.toLocaleString() : 'N/A'})
                    </span>
                `;
                ulElement.appendChild(li);
            }
        } else {
            const li = document.createElement('li');
            li.className = 'roster-item';
            li.innerHTML = `<span>No players yet</span>`;
            ulElement.appendChild(li);
        }
    }

    // Socket.IO Event Handlers
    socket.on('connect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Connected.`);
        socket.emit('request_initial_data', { team_name: MY_TEAM_NAME, access_token: ACCESS_TOKEN });
        fetchMyTeamStatus(); 
        if (otherTeamsDropdown) setupOtherTeamsDropdownListener();
        
        // Initialize display with placeholder/default values
        updateManagerCurrentItemDisplay(null); 
        updateManagerBiddingStatusDisplay(null);
        setBidFeedback('');
    });

    socket.on('connect_error', (err) => {
        console.error(`Manager ${MY_TEAM_NAME}: Connection Error: ${err.message}`);
        if (err.message.includes("Invalid token") || err.message.includes("refused")) {
             document.body.innerHTML = `<h1 style="color: red; text-align: center; margin-top: 50px;">Connection Refused: ${err.message}. Please check your access link or contact the admin.</h1>`;
        }
        if (bidButton) bidButton.disabled = true;
    });
    socket.on('auth_error', (data) => {
        console.error(`Manager ${MY_TEAM_NAME}: Authentication Error: ${data.message}`);
        setBidFeedback(`Auth Error: ${data.message}`, true);
        if (bidButton) bidButton.disabled = true;
    });
    socket.on('access_revoked', (data) => {
        console.warn(`Manager ${MY_TEAM_NAME}: Access Revoked: ${data.message}`);
        document.body.innerHTML = `<h1 style="color: orange; text-align: center; margin-top: 50px;">Access Revoked: ${data.message}</h1>`;
        socket.disconnect();
    });
    socket.on('reload_all_team_status', () => {
        fetchMyTeamStatus();
        if (otherTeamsDropdown && otherTeamsDropdown.value && otherTeamInfoDiv.style.display !== 'none') {
             displayOtherTeamInfo(otherTeamsDropdown.value); 
        }
    });
    socket.on('disconnect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Disconnected`);
        if (bidButton) bidButton.disabled = true;
        setBidFeedback('Disconnected from server.', true, 0); // Don't auto-clear disconnect message
    });

    socket.on('full_state_update', (data) => {
        updateManagerCurrentItemDisplay(data.current_item);
        updateManagerBiddingStatusDisplay(data.bid_status);

        let nextBid = null;
        let currentItemExistsAndActive = (currentItemNameGlobal !== null && data.is_item_active === true);
        let amIHighestBidder = false;

        if (data.bid_status && data.bid_status.highest_bidder_name === MY_TEAM_NAME) {
            amIHighestBidder = true;
        }

        if (currentItemExistsAndActive) {
            if (data.bid_status && typeof data.bid_status.next_potential_bid === 'number') {
                nextBid = data.bid_status.next_potential_bid;
            }
        } else {
            if (nextBidValueEl) nextBidValueEl.textContent = '--';
            if (moneyLeftAfterBidEl) moneyLeftAfterBidEl.textContent = '--';
            if (bidButton) {
                bidButton.disabled = true;
                bidButton.textContent = `Place Bid for ${MY_TEAM_NAME}`;
            }
        }

        if (currentItemExistsAndActive && nextBid !== null) {
            if (nextBidValueEl) nextBidValueEl.textContent = `₹${nextBid.toLocaleString()}`;
            const myTeamData = allTeamsDataCache[MY_TEAM_NAME];
            if (myTeamData && typeof myTeamData.money === 'number' && moneyLeftAfterBidEl) {
                const moneyLeft = myTeamData.money - nextBid;
                moneyLeftAfterBidEl.textContent = `₹${moneyLeft.toLocaleString()}`;
            } else if (moneyLeftAfterBidEl) {
                moneyLeftAfterBidEl.textContent = '--';
            }
        } else {
            if (nextBidValueEl) nextBidValueEl.textContent = '--';
            if (moneyLeftAfterBidEl) moneyLeftAfterBidEl.textContent = '--';
        }
        updateMoneyLeftStyling();

        let enableBidButton = false;
        if (currentItemExistsAndActive && nextBid !== null && !amIHighestBidder) { 
            const myTeamCurrentMoney = (allTeamsDataCache[MY_TEAM_NAME] && typeof allTeamsDataCache[MY_TEAM_NAME].money === 'number')
                                       ? allTeamsDataCache[MY_TEAM_NAME].money
                                       : -Infinity;
            if (myTeamCurrentMoney >= nextBid) {
                enableBidButton = true;
            }
        }
        
        if (bidButton) {
            bidButton.disabled = !enableBidButton;
            if (amIHighestBidder && currentItemExistsAndActive) {
                bidButton.textContent = `You are Highest Bidder`;
            } else if (enableBidButton && nextBid !== null) {
                bidButton.textContent = `Bid ₹${nextBid.toLocaleString()} for ${MY_TEAM_NAME}`;
            } else if (currentItemExistsAndActive && nextBid !== null && !enableBidButton) {
                bidButton.textContent = `Cannot Afford Bid`;
            } else { 
                bidButton.textContent = `Place Bid for ${MY_TEAM_NAME}`;
            }
        }
        
        fetchMyTeamStatus(); 
        if (otherTeamsDropdown && otherTeamsDropdown.value && otherTeamInfoDiv.style.display !== 'none') {
            displayOtherTeamInfo(otherTeamsDropdown.value);
        }
    });

    socket.on('item_sold_event', (soldData) => {
        updateManagerSoldTicker(soldData);
        setBidFeedback(`${soldData.player_name} sold to ${soldData.winning_team_name} for ₹${soldData.sold_price.toLocaleString()}`, false);
        // currentItemNameGlobal will be set to null and photo to default by the next full_state_update
        // or by a direct call to updateManagerCurrentItemDisplay(null) if the server sends an empty current_item.
        fetchMyTeamStatus(); 
    });

    socket.on('item_passed_event', (passData) => {
        if (typeof handleItemPassed === 'function') handleItemPassed(passData);
        else console.log(`Item passed: ${passData.item_name}`);
        setBidFeedback(`${passData.item_name} passed (unsold).`, false);
        // The next full_state_update will reset the item display and bid button
    });

    socket.on('bid_error', (data) => {
        console.error(`Manager ${MY_TEAM_NAME}: Bid Error:`, data.message);
        setBidFeedback(`Error: ${data.message}`, true, 8000); // Longer display for errors
    });
    
    socket.on('bid_accepted', (data) => { // Server might send this before full_state_update
        setBidFeedback(data.message || 'Bid submitted successfully!', false);
        // Bid button will be disabled by full_state_update when amIHighestBidder becomes true
    });

    // Event Listeners
    if (bidButton) {
        bidButton.addEventListener('click', () => {
            if (!currentItemNameGlobal) {
                setBidFeedback('No item selected for bidding.', true);
                return;
            }
            // Check if already highest bidder (client-side quick check, server validates too)
            if (highestBidderNameEl && highestBidderNameEl.textContent === MY_TEAM_NAME) {
                 setBidFeedback('You are already the highest bidder.', true);
                 return;
            }

            setBidFeedback('Submitting bid...', false, 2000); // Short display, success/error will override
            socket.emit('submit_bid_from_manager', {
                team_name: MY_TEAM_NAME,
                item_name: currentItemNameGlobal,
                access_token: ACCESS_TOKEN
            });
        });
    }

    // --- Data Fetching and Display ---
    function fetchMyTeamStatus() {
        fetch(`/api/all_teams_status`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Error fetching all teams status:", data.error);
                    return;
                }
                allTeamsDataCache = data;
                const myTeam = data[MY_TEAM_NAME];
                if (myTeam) {
                    if (myTeamFundsEl) myTeamFundsEl.textContent = `₹${myTeam.money ? myTeam.money.toLocaleString() : '0'}`;
                    if (myTeamRosterUl) renderRoster(myTeamRosterUl, myTeam.inventory, true);
                }
                
                // Re-evaluate bid button after funds update, ONLY if an item is meant to be active
                let localCurrentItemExistsAndActive = (currentItemNameGlobal !== null); // Simpler check now
                const playerContentDiv = document.getElementById('player-content'); // Re-get to check visibility, though it's always visible now
                                                                                  // A better check is if currentItemNameGlobal is set AND item is active on server data (from full_state_update)
                
                // This re-evaluation logic might be better placed directly in full_state_update
                // after all data (item, bid_status, team_funds) is known.
                // For now, let's keep it minimal here as full_state_update is the main driver.
                // If the currentItemNameGlobal is set, full_state_update logic should handle the button correctly.
                // This fetch primarily updates funds which is then used by full_state_update's button logic.
            })
            .catch(error => console.error('Error fetching team status:', error));
    }
    
    function setupOtherTeamsDropdownListener() {
        if (otherTeamsDropdown) {
            otherTeamsDropdown.addEventListener('change', (event) => {
                const selectedTeamName = event.target.value;
                if (selectedTeamName) {
                    displayOtherTeamInfo(selectedTeamName);
                } else {
                    if (otherTeamInfoDiv) otherTeamInfoDiv.style.display = 'none';
                }
            });
        }
    }
    
    function displayOtherTeamInfo(teamName) {
        const teamData = allTeamsDataCache[teamName]; // Use cached data
        if (teamData && otherTeamInfoDiv) {
            if (otherTeamNameDisplayEl) otherTeamNameDisplayEl.textContent = teamName;
            if (otherTeamFundsEl) otherTeamFundsEl.textContent = `₹${teamData.money ? teamData.money.toLocaleString() : '0'}`;
            if (otherTeamRosterUl) {
                renderRoster(otherTeamRosterUl, teamData.inventory, false);
            }
            otherTeamInfoDiv.style.display = 'block';
        } else if (otherTeamInfoDiv) {
            otherTeamInfoDiv.style.display = 'none';
        }
    }
});