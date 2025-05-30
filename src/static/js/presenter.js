// Theme Toggle Functionality
const themeToggle = document.getElementById('theme-toggle-btn');
const body = document.body;

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-theme');
    body.classList.toggle('light-theme');
});

// Socket.IO and Core Functionality
document.addEventListener('DOMContentLoaded', () => {
    const socket = io('/presenter');
    let allTeamsData = {};
    let currentDisplayedItemName = null;
    const teamCardAnimationTimeouts = {};

    socket.on('connect', () => {
        console.log('Connected to Presenter SocketIO server');
        socket.emit('request_initial_data');
        fetchTeamsData();
    });

    socket.on('reload_all_team_status', () => {
        // refresh all team status after loading history
        fetchTeamsData();
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Presenter SocketIO server');
    });

    socket.on('full_state_update', (data) => {
        updateCurrentItemDisplay(data.current_item);
        updateBiddingStatusDisplay(data.bid_status);
    });

    socket.on('item_sold_event', (soldData) => {
        showSoldAnimation(soldData);
        updateSoldTicker(soldData);
    });

    socket.on('item_passed_event', (passData) => {
        handleItemPassed(passData);
    });

    function fetchTeamsData() {
        fetch('/api/all_teams_status')
            .then(response => response.json())
            .then(data => {
                allTeamsData = data;
                populateTeamsGrid(data);
            })
            .catch(error => console.error('Error fetching teams data:', error));
    }

    function populateTeamsGrid(teams) {
        const container = document.getElementById('teams-container');
        container.innerHTML = ''; // Clear existing cards

        Object.keys(teams).sort().forEach(teamName => {
            const team = teams[teamName];
            const teamCard = document.createElement('div');
            teamCard.className = 'team-card';
            teamCard.dataset.teamName = teamName; // Used as the primary selector for the card
            
            teamCard.innerHTML = `
                <div class="team-logo">
                    <img src="${team.logo_path || '/static/images/default-item.jpeg'}" alt="${teamName} logo">
                </div>
                <div class="team-details">
                    <h3 class="team-name">${teamName}</h3>
                    <p class="team-funds">₹${team.money.toLocaleString()}</p>
                    <div class="team-players-count">${Object.keys(team.inventory || {}).length} players</div>
                </div>
                <div class="bid-indicator"></div> 
            `; // .bid-indicator is the class for the indicator element

            teamCard.addEventListener('click', () => {
                showTeamModal(teamName, allTeamsData);
            });

            container.appendChild(teamCard);
        });
    }

    function updateCurrentItemDisplay(itemData) {
        const noItemMsg = document.getElementById('no-item-message');
        const playerCard = document.getElementById('current-player-card');
        const newItemName = itemData ? itemData.name : null;

        if (itemData && itemData.name) {
            noItemMsg.style.display = 'none';
            playerCard.style.display = 'block';
            
            document.getElementById('item-name').textContent = itemData.name;
            document.getElementById('item-base-bid').textContent = `₹${itemData.base_bid ? itemData.base_bid.toLocaleString() : '0'}`;
            
            const playerImg = document.getElementById('item-photo');
            if (itemData.photo_path) {
                playerImg.src = itemData.photo_path;
                playerImg.style.display = 'block';
            } else {
                playerImg.style.display = 'none';
            }

            if (newItemName !== currentDisplayedItemName) {
                playerCard.classList.add('player-entrance');
                setTimeout(() => {
                    playerCard.classList.remove('player-entrance');
                }, 1000);
            }
        } else {
            noItemMsg.style.display = 'block';
            playerCard.style.display = 'none';
        }
        currentDisplayedItemName = newItemName;
    }

    function updateBiddingStatusDisplay(bidStatus) {
        if (bidStatus && typeof bidStatus.bid_amount === 'number') {
            document.getElementById('current-bid-amount').textContent = `₹${bidStatus.bid_amount.toLocaleString()}`;
            
            if (bidStatus.highest_bidder_name) {
                showBidAnimation(bidStatus.highest_bidder_name, bidStatus.bid_amount);
            } else {
                // No highest bidder, so clear all active bid animations
                Object.keys(teamCardAnimationTimeouts).forEach(teamNameInTimeout => {
                    clearTimeout(teamCardAnimationTimeouts[teamNameInTimeout]);
                    const teamCardToClear = document.querySelector(`[data-team-name="${teamNameInTimeout}"]`);
                    if (teamCardToClear) {
                        const bidIndicatorToClear = teamCardToClear.querySelector('.bid-indicator');
                        if (bidIndicatorToClear) bidIndicatorToClear.classList.remove('active');
                        teamCardToClear.classList.remove('bidding');
                    }
                    delete teamCardAnimationTimeouts[teamNameInTimeout];
                });
            }
        } else {
            document.getElementById('current-bid-amount').textContent = '₹0';
            // Also clear all animations if bidStatus is invalid or no bid_amount
            Object.keys(teamCardAnimationTimeouts).forEach(teamNameInTimeout => {
                clearTimeout(teamCardAnimationTimeouts[teamNameInTimeout]);
                const teamCardToClear = document.querySelector(`[data-team-name="${teamNameInTimeout}"]`);
                if (teamCardToClear) {
                    const bidIndicatorToClear = teamCardToClear.querySelector('.bid-indicator');
                    if (bidIndicatorToClear) bidIndicatorToClear.classList.remove('active');
                    teamCardToClear.classList.remove('bidding');
                }
                delete teamCardAnimationTimeouts[teamNameInTimeout];
            });
        }
    }

    function showBidAnimation(currentHighestBidderTeamName, bidAmount) {
        // 0. Clear all existing timeouts to prevent them from interfering.
        Object.keys(teamCardAnimationTimeouts).forEach(teamNameInMap => {
            clearTimeout(teamCardAnimationTimeouts[teamNameInMap]);
            delete teamCardAnimationTimeouts[teamNameInMap]; // Clean up the map entry
        });

        // 1. Remove 'bidding' and 'active' classes from ALL team cards and indicators first.
        // This ensures a completely clean slate before attempting to animate the target.
        document.querySelectorAll('.team-card').forEach(card => {
            card.classList.remove('bidding');
            const indicator = card.querySelector('.bid-indicator');
            if (indicator) {
                indicator.classList.remove('active');
            }
        });

        // 2. Get the target elements (we'll re-query inside setTimeout for safety)
        const targetTeamCardForText = document.querySelector(`[data-team-name="${currentHighestBidderTeamName}"]`);
        if (!targetTeamCardForText) {
            console.error(`Initial query failed for team card: ${currentHighestBidderTeamName}`);
            return;
        }
        const targetBidIndicatorForText = targetTeamCardForText.querySelector('.bid-indicator');
        if (!targetBidIndicatorForText) {
            console.error(`Initial query failed for bid indicator: ${currentHighestBidderTeamName}`);
            return;
        }

        // 3. Use a minimal setTimeout to add the classes.
        const timeoutId = setTimeout(() => {
            const teamCard = document.querySelector(`[data-team-name="${currentHighestBidderTeamName}"]`);
            if (!teamCard) {
                console.error(`Team card not found in setTimeout for: ${currentHighestBidderTeamName}`);
                return;
            }
            const bidIndicator = teamCard.querySelector('.bid-indicator');
            if (!bidIndicator) {
                console.error(`Bid indicator not found in setTimeout for: ${currentHighestBidderTeamName}`);
                return;
            }

            // Add classes to trigger animation
            teamCard.classList.add('bidding');
            bidIndicator.textContent = `₹${bidAmount.toLocaleString()}`;
            bidIndicator.classList.add('active');

            // Store this timeout ID so it can be cleared if another bid comes in quickly.
            // And set another timeout to remove the classes after animation.
            teamCardAnimationTimeouts[currentHighestBidderTeamName] = setTimeout(() => {
                // Check if elements still exist before removing classes
                const finalTeamCard = document.querySelector(`[data-team-name="${currentHighestBidderTeamName}"]`);
                if (finalTeamCard) {
                    finalTeamCard.classList.remove('bidding');
                    const finalBidIndicator = finalTeamCard.querySelector('.bid-indicator');
                    if (finalBidIndicator) {
                        finalBidIndicator.classList.remove('active');
                    }
                }
                delete teamCardAnimationTimeouts[currentHighestBidderTeamName]; // Clean up
            }, 3000); // Duration for classes to remain active

        }, 10);
    }

    function showSoldAnimation(soldData) {
        const overlay = document.getElementById('sold-overlay');
        
        document.getElementById('sold-player-name').textContent = soldData.player_name;
        document.getElementById('sold-team-name').textContent = soldData.winning_team_name;
        document.getElementById('sold-price').textContent = `₹${soldData.sold_price.toLocaleString()}`;
        
        const soldPlayerImage = document.getElementById('sold-player-image');
        if (soldData.player_photo_path) {
            soldPlayerImage.src = soldData.player_photo_path;
            soldPlayerImage.style.display = 'block';
        } else {
            soldPlayerImage.src = '/static/images/default-item.jpeg'; // Default
            soldPlayerImage.style.display = 'block';
        }

        const soldTeamLogo = document.getElementById('sold-team-logo');
        if (soldData.winning_team_logo_path) {
            soldTeamLogo.src = soldData.winning_team_logo_path;
            soldTeamLogo.style.display = 'block';
        } else {
            soldTeamLogo.src = '/static/images/default-item.jpeg'; // Default
            soldTeamLogo.style.display = 'block';
        }

        overlay.classList.add('active');
        
        setTimeout(() => {
            overlay.classList.remove('active');
        }, 5000);
    }

    function updateSoldTicker(soldData) {
        const tickerList = document.getElementById('ticker-list');
        const newItem = document.createElement('li');
        newItem.innerHTML = `<strong>${soldData.player_name}</strong> → <em>${soldData.winning_team_name}</em> (₹${soldData.sold_price.toLocaleString()})`;
        
        if (tickerList.firstChild) {
            tickerList.insertBefore(newItem, tickerList.firstChild);
        } else {
            tickerList.appendChild(newItem);
        }
        
        while (tickerList.children.length > 10) {
            tickerList.removeChild(tickerList.lastChild);
        }
    }

    function handleItemPassed(passData) {
        console.log(`Item passed: ${passData.item_name}`);
        const noItemMsg = document.getElementById('no-item-message');
        const playerCard = document.getElementById('current-player-card');
        
        if (noItemMsg && playerCard) { // Ensure elements exist
            noItemMsg.textContent = `${passData.item_name || 'Item'} - PASSED`;
            noItemMsg.style.display = 'block';
            playerCard.style.display = 'none';
            currentDisplayedItemName = `PASSED_${passData.item_name || Date.now()}`; // Make it unique

            setTimeout(() => {
                // Check if the message is still the "PASSED" message before resetting
                if (noItemMsg.textContent === `${passData.item_name || 'Item'} - PASSED`) { 
                    noItemMsg.textContent = "No item currently up for auction.";
                }
            }, 3000);
        }
    }

    function showTeamModal(teamName, teamsDataRef) {
        const team = teamsDataRef[teamName];
        if (!team) {
            console.error("Team data not found for modal:", teamName);
            return;
        }
        const modal = document.getElementById('team-modal');
        
        document.getElementById('modal-team-name').textContent = teamName;
        document.getElementById('modal-team-funds').textContent = `₹${team.money.toLocaleString()}`;
        
        const modalTeamLogo = document.getElementById('modal-team-logo');
        if (team.logo_path) {
            modalTeamLogo.src = team.logo_path;
            modalTeamLogo.style.display = 'block';
        } else {
            modalTeamLogo.src = '/static/images/default-item.jpeg'; // Default
            modalTeamLogo.style.display = 'block';
        }

        const rosterList = document.getElementById('modal-team-roster');
        rosterList.innerHTML = '';
        
        if (team.inventory && Object.keys(team.inventory).length > 0) {
            Object.entries(team.inventory).forEach(([player, price]) => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="player-name">${player}</span><span class="player-price">₹${price.toLocaleString()}</span>`;
                rosterList.appendChild(li);
            });
        } else {
            rosterList.innerHTML = '<li class="no-players">No players acquired yet</li>';
        }

        modal.classList.add('active');
    }

    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('team-modal').classList.remove('active');
    });

    document.querySelector('.modal-backdrop').addEventListener('click', () => {
        document.getElementById('team-modal').classList.remove('active');
    });
});
// --- END OF FILE presenter.js ---