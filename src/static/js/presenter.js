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
    let currentBidTimeout = null;

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
        container.innerHTML = '';

        Object.keys(teams).sort().forEach(teamName => {
            const team = teams[teamName];
            const teamCard = document.createElement('div');
            teamCard.className = 'team-card';
            teamCard.dataset.teamName = teamName;
            
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
            `;

            teamCard.addEventListener('click', () => {
                showTeamModal(teamName, allTeamsData);
            });

            container.appendChild(teamCard);
        });
    }

    function updateCurrentItemDisplay(itemData) {
        const noItemMsg = document.getElementById('no-item-message');
        const playerCard = document.getElementById('current-player-card');

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

            // Animate player card entrance
            playerCard.classList.add('player-entrance');
            setTimeout(() => {
                playerCard.classList.remove('player-entrance');
            }, 1000);
        } else {
            noItemMsg.style.display = 'block';
            playerCard.style.display = 'none';
        }
    }

    function updateBiddingStatusDisplay(bidStatus) {
        if (bidStatus && bidStatus.bid_amount) {
            document.getElementById('current-bid-amount').textContent = `₹${bidStatus.bid_amount.toLocaleString()}`;
            
            if (bidStatus.highest_bidder_name) {
                showBidAnimation(bidStatus.highest_bidder_name, bidStatus.bid_amount);
            }
        } else {
            document.getElementById('current-bid-amount').textContent = '₹0';
        }
    }

    function showBidAnimation(teamName, bidAmount) {
        // Clear existing timeout
        if (currentBidTimeout) {
            clearTimeout(currentBidTimeout);
        }

        // Find team card and show bid indicator
        const teamCard = document.querySelector(`[data-team-name="${teamName}"]`);
        if (teamCard) {
            const bidIndicator = teamCard.querySelector('.bid-indicator');
            bidIndicator.textContent = `₹${bidAmount.toLocaleString()}`;
            bidIndicator.classList.add('active');
            teamCard.classList.add('bidding');

            // Remove animation after 3 seconds
            currentBidTimeout = setTimeout(() => {
                bidIndicator.classList.remove('active');
                teamCard.classList.remove('bidding');
            }, 3000);
        }
    }

    function showSoldAnimation(soldData) {
        const overlay = document.getElementById('sold-overlay');
        
        // Populate sold animation data
        document.getElementById('sold-player-name').textContent = soldData.player_name;
        document.getElementById('sold-team-name').textContent = soldData.winning_team_name;
        document.getElementById('sold-price').textContent = `₹${soldData.sold_price.toLocaleString()}`;
        
        if (soldData.player_photo_path) {
            document.getElementById('sold-player-image').src = soldData.player_photo_path;
        }
        if (soldData.winning_team_logo_path) {
            document.getElementById('sold-team-logo').src = soldData.winning_team_logo_path;
        }

        // Show animation
        overlay.classList.add('active');
        
        // Hide after 5 seconds
        setTimeout(() => {
            overlay.classList.remove('active');
        }, 5000);
    }

    function updateSoldTicker(soldData) {
        const tickerList = document.getElementById('ticker-list');
        const newItem = document.createElement('li');
        newItem.innerHTML = `<strong>${soldData.player_name}</strong> → <em>${soldData.winning_team_name}</em> (₹${soldData.sold_price.toLocaleString()})`;
        
        tickerList.insertBefore(newItem, tickerList.firstChild);
        
        // Keep only 10 items
        while (tickerList.children.length > 10) {
            tickerList.removeChild(tickerList.lastChild);
        }
    }

    function handleItemPassed(data) {
        console.log(`Item passed: ${data.item_name}`);
        // Could add a "PASSED" animation here
    }

    function showTeamModal(teamName, teamsData) {
        const team = teamsData[teamName];
        const modal = document.getElementById('team-modal');
        
        document.getElementById('modal-team-name').textContent = teamName;
        document.getElementById('modal-team-funds').textContent = `₹${team.money.toLocaleString()}`;
        
        if (team.logo_path) {
            document.getElementById('modal-team-logo').src = team.logo_path;
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

    // Modal close functionality
    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('team-modal').classList.remove('active');
    });

    document.querySelector('.modal-backdrop').addEventListener('click', () => {
        document.getElementById('team-modal').classList.remove('active');
    });
});