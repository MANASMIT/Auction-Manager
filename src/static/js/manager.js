// --- static/js/manager.js ---
document.addEventListener('DOMContentLoaded', () => {
    // MY_TEAM_NAME and ACCESS_TOKEN are passed from the HTML template (or could be parsed from URL)
    // Let's assume ACCESS_TOKEN is available globally if passed via <script> tag, or parse from URL.
    let ACCESS_TOKEN = null;
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length >= 4 && pathParts[1] === 'manager') {
        // MY_TEAM_NAME is already globally defined by the template
        ACCESS_TOKEN = pathParts[3];
    }

    if (typeof MY_TEAM_NAME === 'undefined' || !ACCESS_TOKEN) {
        document.body.innerHTML = '<h1>Error: Manager context (Team Name or Access Token) is missing. Cannot connect.</h1>';
        console.error("MY_TEAM_NAME or ACCESS_TOKEN is not defined.");
        return;
    }

    const socket = io('/manager', {
        auth: { // Send token on connection
            team_name: MY_TEAM_NAME,
            access_token: ACCESS_TOKEN
        }
    });
    
    let currentItemNameGlobal = null; // To store the name of the item being bid on
    let allTeamsDataCache = {}; // Cache for team data

    const bidButton = document.getElementById('bid-button');
    const bidFeedback = document.getElementById('bid-feedback');
    const otherTeamsDropdown = document.getElementById('other-teams-dropdown');

    socket.on('connect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Connected to SocketIO server with token.`);
        // Client now sends token with request_initial_data
        socket.emit('request_initial_data', { team_name: MY_TEAM_NAME, access_token: ACCESS_TOKEN });
        fetchMyTeamStatus();
        if (otherTeamsDropdown) fetchAllTeamsDataForDropdown();
    });

    socket.on('connect_error', (err) => {
        console.error(`Manager ${MY_TEAM_NAME}: Connection Error: ${err.message}`);
        if (err.message.includes("Invalid token") || err.message.includes("refused")) {
             document.body.innerHTML = `<h1>Connection Refused: ${err.message}. Please check your access link or contact the admin.</h1>`;
        }
        // Handle other connection errors if necessary
    });
    
    socket.on('auth_error', (data) => { // Listen for specific auth errors from server
        console.error(`Manager ${MY_TEAM_NAME}: Authentication Error: ${data.message}`);
        setBidFeedback(`Auth Error: ${data.message}`, true);
        // Potentially disable UI elements or show a persistent error
    });

    socket.on('access_revoked', (data) => {
        console.warn(`Manager ${MY_TEAM_NAME}: Access Revoked by Admin: ${data.message}`);
        document.body.innerHTML = `<h1>Access Revoked: ${data.message}</h1>`;
        socket.disconnect(); // Disconnect the socket
    });

    socket.on('disconnect', () => {
        console.log(`Manager ${MY_TEAM_NAME}: Disconnected from SocketIO server`);
        if (bidButton) bidButton.disabled = true;
    });

    socket.on('full_state_update', (data) => {
        // console.log(`Manager ${MY_TEAM_NAME}: Full state update:`, data);
        updateCurrentItemDisplay(data.current_item);
        updateBiddingStatusDisplay(data.bid_status);

        if (data.current_item && data.current_item.name && data.is_item_active) {
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
                item_name: currentItemNameGlobal, // Though engine knows current item
                access_token: ACCESS_TOKEN
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
