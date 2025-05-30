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
        fetchTeamsData();
        clearSoldTicker();
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Presenter SocketIO server');
    });

    socket.on('full_state_update', (data) => {
        updateCurrentItemDisplay(data.current_item);
        updateBiddingStatusDisplay(data.bid_status);
        // If team data is part of full_state_update and might change funds/inventory,
        // you might need to call fetchTeamsData() or a more specific update here.
        // For now, assuming fetchTeamsData is called separately or on connect/reload.
    });

    socket.on('item_sold_event', (soldData) => {
        showSoldAnimation(soldData);
        updateSoldTicker(soldData);
        fetchTeamsData(); // Update team funds/inventory after a sale
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

    function createTeamCardNode(teamName, team) {
        const teamCard = document.createElement('div');
        teamCard.className = 'team-card';
        teamCard.dataset.teamName = teamName;
    
        const logoPath = team.logo_path || '/static/images/default_item.jpeg';
    
        // Create image element separately to load and check validity
        const img = new Image();
        img.alt = `${teamName} logo`;
    
        img.onerror = () => {
            img.src = '/static/images/default_item.jpeg'; // fallback if image fails to load
        };
    
        img.src = logoPath;
    
        teamCard.innerHTML = `
            <div class="team-logo"></div>
            <div class="team-details">
                <h3 class="team-name">${teamName}</h3>
                <p class="team-funds">₹${team.money.toLocaleString()}</p>
                <div class="team-players-count">${Object.keys(team.inventory || {}).length} players</div>
            </div>
            <div class="bid-indicator"></div> 
        `;
    
        // Insert the image element once configured
        teamCard.querySelector('.team-logo').appendChild(img);
    
        teamCard.addEventListener('click', () => {
            showTeamModal(teamName, allTeamsData);
        });
    
        return teamCard;
    }

    function populateTeamsGrid(teams) {
        const leftContainer = document.getElementById('teams-container-left');
        const rightContainer = document.getElementById('teams-container-right');
        const bottomContainer = document.getElementById('teams-container-bottom');
        const mobileContainer = document.getElementById('teams-container-mobile');

        // Clear all containers
        if(leftContainer) leftContainer.innerHTML = '';
        if(rightContainer) rightContainer.innerHTML = '';
        if(bottomContainer) bottomContainer.innerHTML = '';
        if(mobileContainer) mobileContainer.innerHTML = '';

        const sortedTeamNames = Object.keys(teams).sort();
        const numTeams = sortedTeamNames.length;

        // Populate mobile container (always)
        if (mobileContainer) {
            sortedTeamNames.forEach(teamName => {
                mobileContainer.appendChild(createTeamCardNode(teamName, teams[teamName]));
            });
        }

        // Populate desktop containers based on rules (if they exist)
        if (leftContainer && rightContainer && bottomContainer) {
            if (numTeams === 0) {
                // No teams, do nothing further for desktop
            } else if (numTeams <= 2) {
                // Both to bottom
                sortedTeamNames.forEach(name => bottomContainer.appendChild(createTeamCardNode(name, teams[name])));
            } else if (numTeams === 3) {
                // 1 left, 1 right, 1 bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[2], teams[sortedTeamNames[2]]));
            } else if (numTeams === 4) {
                // 1 left, 1 right, 2 bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[2], teams[sortedTeamNames[2]]));
                bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[3], teams[sortedTeamNames[3]]));
            } else if (numTeams === 5) {
                // 1 left, 1 right, 3 bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                for (let i = 2; i < 5; i++) {
                    bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[i], teams[sortedTeamNames[i]]));
                }
            } else if (numTeams === 6) {
                // 2 left, 2 right, 2 bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[2], teams[sortedTeamNames[2]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[3], teams[sortedTeamNames[3]]));
                bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[4], teams[sortedTeamNames[4]]));
                bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[5], teams[sortedTeamNames[5]]));
            } else if (numTeams === 7) {
                // 2 left, 2 right, 3 bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[2], teams[sortedTeamNames[2]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[3], teams[sortedTeamNames[3]]));
                for (let i = 4; i < 7; i++) {
                    bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[i], teams[sortedTeamNames[i]]));
                }
            } else { // numTeams > 7
                // 2 left, 2 right, rest to bottom
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[0], teams[sortedTeamNames[0]]));
                leftContainer.appendChild(createTeamCardNode(sortedTeamNames[1], teams[sortedTeamNames[1]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[2], teams[sortedTeamNames[2]]));
                rightContainer.appendChild(createTeamCardNode(sortedTeamNames[3], teams[sortedTeamNames[3]]));
                for (let i = 4; i < numTeams; i++) {
                    bottomContainer.appendChild(createTeamCardNode(sortedTeamNames[i], teams[sortedTeamNames[i]]));
                }
            }

            // Apply column styling to bottom container based on numTeams
            if (numTeams > 7) {
                bottomContainer.classList.add('strict-three-columns');
                bottomContainer.classList.remove('flexible-columns');
            } else {
                bottomContainer.classList.remove('strict-three-columns');
                bottomContainer.classList.add('flexible-columns');
            }
        }
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
    
            const img = new Image();
            img.onload = () => {
                playerImg.src = itemData.photo_path;
                playerImg.style.display = 'block';
            };
            img.onerror = () => {
                playerImg.src = '/static/images/default_item.jpeg';
                playerImg.style.display = 'block';
            };
            img.src = itemData.photo_path || '/static/images/default_item.jpeg';
    
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
        Object.keys(teamCardAnimationTimeouts).forEach(teamNameInMap => {
            clearTimeout(teamCardAnimationTimeouts[teamNameInMap]);
            delete teamCardAnimationTimeouts[teamNameInMap]; 
        });

        document.querySelectorAll('.team-card').forEach(card => {
            card.classList.remove('bidding');
            const indicator = card.querySelector('.bid-indicator');
            if (indicator) {
                indicator.classList.remove('active');
            }
        });

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

        const timeoutId = setTimeout(() => {
            // Re-query elements within setTimeout as a safeguard against DOM changes
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

            teamCard.classList.add('bidding');
            bidIndicator.textContent = `₹${bidAmount.toLocaleString()}`;
            bidIndicator.classList.add('active');

            teamCardAnimationTimeouts[currentHighestBidderTeamName] = setTimeout(() => {
                const finalTeamCard = document.querySelector(`[data-team-name="${currentHighestBidderTeamName}"]`);
                if (finalTeamCard) {
                    finalTeamCard.classList.remove('bidding');
                    const finalBidIndicator = finalTeamCard.querySelector('.bid-indicator');
                    if (finalBidIndicator) {
                        finalBidIndicator.classList.remove('active');
                    }
                }
                delete teamCardAnimationTimeouts[currentHighestBidderTeamName]; // Clean up
            }, 5000); // Duration for classes to remain active

        }, 15); 
    }

    function showSoldAnimation(soldData) {
        const overlay = document.getElementById('sold-overlay');
    
        document.getElementById('sold-player-name').textContent = soldData.player_name;
        document.getElementById('sold-team-name').textContent = soldData.winning_team_name;
        document.getElementById('sold-price').textContent = `₹${soldData.sold_price.toLocaleString()}`;
    
        // Handle player photo
        const soldPlayerImage = document.getElementById('sold-player-image');
        const playerImage = new Image();
        playerImage.onload = () => {
            soldPlayerImage.src = soldData.player_photo_path;
            soldPlayerImage.style.display = 'block';
        };
        playerImage.onerror = () => {
            soldPlayerImage.src = '/static/images/default_item.jpeg';
            soldPlayerImage.style.display = 'block';
        };
        playerImage.src = soldData.player_photo_path || '/static/images/default_item.jpeg';
    
        // Handle team logo
        const soldTeamLogo = document.getElementById('sold-team-logo');
        const teamLogo = new Image();
        teamLogo.onload = () => {
            soldTeamLogo.src = soldData.winning_team_logo_path;
            soldTeamLogo.style.display = 'block';
        };
        teamLogo.onerror = () => {
            soldTeamLogo.src = '/static/images/default_item.jpeg';
            soldTeamLogo.style.display = 'block';
        };
        teamLogo.src = soldData.winning_team_logo_path || '/static/images/default_item.jpeg';
    
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

    function clearSoldTicker() {
        const tickerList = document.getElementById('ticker-list');
        while (tickerList.children.length > 0) {
                tickerList.removeChild(tickerList.lastChild);
        }
    }

    function handleItemPassed(passData) {
        console.log(`Item passed: ${passData.item_name}`);
        const noItemMsg = document.getElementById('no-item-message');
        const playerCard = document.getElementById('current-player-card');
        
        if (noItemMsg && playerCard) {
            noItemMsg.textContent = `${passData.item_name || 'Item'} - PASSED`;
            noItemMsg.style.display = 'block';
            playerCard.style.display = 'none';
            currentDisplayedItemName = `PASSED_${passData.item_name || Date.now()}`; 

            setTimeout(() => {
                if (noItemMsg.textContent === `${passData.item_name || 'Item'} - PASSED`) { 
                    noItemMsg.textContent = "No item currently up for auction.";
                }
            }, 3000);
        }
    }

    function showTeamModal(teamName, teamsData) {
        const team = teamsData[teamName];
        const modal = document.getElementById('team-modal');
    
        document.getElementById('modal-team-name').textContent = teamName;
        document.getElementById('modal-team-funds').textContent = `₹${team.money.toLocaleString()}`;
    
        if (team.logo_path) {
            document.getElementById('modal-team-logo').src = team.logo_path;
        } else {
            document.getElementById('modal-team-logo').src = '/static/images/default-item.jpeg'; // Fallback
        }
    
    
        const rosterList = document.getElementById('modal-team-roster');
        rosterList.innerHTML = '';
    
        if (team.inventory && Object.keys(team.inventory).length > 0) {
            // Sort players alphabetically, or by another criteria if needed
            const sortedPlayerNames = Object.keys(team.inventory).sort();
    
            sortedPlayerNames.forEach(playerName => {
                const playerData = team.inventory[playerName]; // playerData is now an object
                const li = document.createElement('li');
                li.innerHTML = `
                    <span class="player-name">${playerName}</span>
                    <span class="player-prices">
                        Sold: ₹${playerData.sold_price.toLocaleString()}
                        (Base: ₹${playerData.base_bid ? playerData.base_bid.toLocaleString() : 'N/A'})
                    </span>
                `;
                // Example of adding a class if sold price is much higher than base
                if (playerData.base_bid && playerData.sold_price > playerData.base_bid * 1.5) {
                    li.classList.add('good-buy');
                }
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