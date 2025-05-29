// --- static/js/manager.js ---
document.addEventListener('DOMContentLoaded', () => {
    // MY_TEAM_NAME is passed from the HTML template
    if (typeof MY_TEAM_NAME === 'undefined') {
        console.error("MY_TEAM_NAME is not defined. Bid button will not work.");
        return;
    }

    const socket = io('/manager'); // Connect to the /manager namespace
    let currentItemNameGlobal = null; // To store the name of the item being bid on
    let allTeamsDataCache = {}; // Cache for team data

    const bidButton = document.getElementById('bid-button');
    const bidFeedback = document.getElementById('bid-feedback');
    const otherTeamsDropdown = document.getElementById('other-teams-dropdown');

    socket.on('connect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Connected to SocketIO server`);
        socket.emit('request_initial_data');
        fetchMyTeamStatus(); // Fetch initial status for "My Team" section
        if (otherTeamsDropdown) fetchAllTeamsDataForDropdown(); // For viewing other teams
    });

    socket.on('disconnect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Disconnected from SocketIO server`);
        if (bidButton) bidButton.disabled = true;
    });

    socket.on('full_state_update', (data) => {
        // console.log(`Manager ${MY_TEAM_NAME}: Full state update:`, data);
        updateCurrentItemDisplay(data.current_item);
        updateBiddingStatusDisplay(data.bid_status);

        if (data.current_item && data.current_item.name) {
            currentItemNameGlobal = data.current_item.name;
            if (bidButton) bidButton.disabled = false;
        } else {
            currentItemNameGlobal = null;
            if (bidButton) bidButton.disabled = true;
        }
        fetchMyTeamStatus(); // Refresh my team's funds/roster after any state change
        // If other team view is active, refresh it too
        if (otherTeamsDropdown && otherTeamsDropdown.value && document.getElementById('other-team-info').style.display !== 'none') {
            displayOtherTeamInfo(otherTeamsDropdown.value);
        }
    });

    socket.on('item_sold_event', (soldData) => {
        // console.log(`Manager ${MY_TEAM_NAME}: Item sold:`, soldData);
        updateSoldTicker(soldData);
        if (bidButton) bidButton.disabled = true; // Item is gone
        currentItemNameGlobal = null;
        setBidFeedback('');
        fetchMyTeamStatus(); // Update funds/roster if my team bought/sold
    });

    socket.on('item_passed_event', (passData) => {
        // console.log(`Manager ${MY_TEAM_NAME}: Item passed:`, passData);
        handleItemPassed(passData);
        if (bidButton) bidButton.disabled = true;
        currentItemNameGlobal = null;
        setBidFeedback('');
    });

    socket.on('bid_error', (data) => {
        console.error(`Manager ${MY_TEAM_NAME}: Bid Error:`, data.message);
        setBidFeedback(`Error: ${data.message}`, true);
    });
    
    socket.on('bid_accepted', (data) => { // If server sends an explicit acceptance before full update
        setBidFeedback(data.message || 'Bid submitted successfully!', false);
    });


    if (bidButton) {
        bidButton.addEventListener('click', () => {
            if (!currentItemNameGlobal) {
                setBidFeedback('No item selected for bidding.', true);
                return;
            }
            setBidFeedback('Submitting bid...');
            socket.emit('submit_bid_from_manager', {
                team_name: MY_TEAM_NAME,
                item_name: currentItemNameGlobal // Though engine knows current item
            });
        });
    }

    function setBidFeedback(message, isError = false) {
        if (bidFeedback) {
            bidFeedback.textContent = message;
            bidFeedback.className = isError ? 'feedback-message error' : 'feedback-message success';
        }
    }

    function fetchMyTeamStatus() {
        fetch(`/api/all_teams_status`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Error fetching my team status:", data.error);
                    return;
                }
                allTeamsDataCache = data; // Update cache
                const myTeam = data[MY_TEAM_NAME];
                if (myTeam) {
                    setText('my-team-funds', `₹${myTeam.money ? myTeam.money.toLocaleString() : '0'}`);
                    setImage('my-team-logo', myTeam.logo_path, `${MY_TEAM_NAME} Logo`);
                    const rosterUl = document.getElementById('my-team-roster');
                    if (rosterUl) {
                        rosterUl.innerHTML = '';
                        if (myTeam.inventory && Object.keys(myTeam.inventory).length > 0) {
                            for (const [player, price] of Object.entries(myTeam.inventory)) {
                                const li = document.createElement('li');
                                li.textContent = `${player} (₹${price.toLocaleString()})`;
                                rosterUl.appendChild(li);
                            }
                        } else {
                            rosterUl.innerHTML = '<li>No players yet.</li>';
                        }
                    }
                }
            })
            .catch(error => console.error('Error fetching my team status:', error));
    }

    function fetchAllTeamsDataForDropdown() {
         // The dropdown is populated by Jinja. This function is for when a selection is made.
         // It relies on allTeamsDataCache being populated by fetchMyTeamStatus or similar.
        if (otherTeamsDropdown) {
            otherTeamsDropdown.addEventListener('change', (event) => {
                const selectedTeam = event.target.value;
                if (selectedTeam) {
                    displayOtherTeamInfo(selectedTeam);
                } else {
                    document.getElementById('other-team-info').style.display = 'none';
                }
            });
        }
    }
    
    function displayOtherTeamInfo(teamName) {
        const teamData = allTeamsDataCache[teamName];
        const container = document.getElementById('other-team-info');
        if (teamData && container) {
            document.getElementById('other-team-name-display').textContent = teamName;
            setText('other-team-funds', `₹${teamData.money ? teamData.money.toLocaleString() : '0'}`);
            setImage('other-team-logo-display', teamData.logo_path, `${teamName} Logo`);
            
            const rosterUl = document.getElementById('other-team-roster-display');
            rosterUl.innerHTML = '';
            if (teamData.inventory && Object.keys(teamData.inventory).length > 0) {
                for (const [player, price] of Object.entries(teamData.inventory)) {
                    const li = document.createElement('li');
                    li.textContent = `${player} (₹${price.toLocaleString()})`;
                    rosterUl.appendChild(li);
                }
            } else {
                rosterUl.innerHTML = '<li>No players yet.</li>';
            }
            container.style.display = 'block';
        } else if (container) {
            container.style.display = 'none';
        }
    }

    // Initial setup for modal if it exists on this page (it doesn't, but good practice)
    setupModalCloseButton(); 
});
