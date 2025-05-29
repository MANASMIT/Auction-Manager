// --- static/js/presenter.js ---
document.addEventListener('DOMContentLoaded', () => {
    const socket = io('/presenter'); // Connect to the /presenter namespace
    let allTeamsData = {}; // Cache for team data

    socket.on('connect', () => {
        console.log('Connected to Presenter SocketIO server');
        socket.emit('request_initial_data'); // Ask for the latest state
        fetchTeamsData(); // Fetch static team data for roster display
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Presenter SocketIO server');
    });

    socket.on('full_state_update', (data) => {
        // console.log('Presenter: Full state update received:', data);
        updateCurrentItemDisplay(data.current_item);
        updateBiddingStatusDisplay(data.bid_status);
        // Note: Sold ticker is handled by 'item_sold_event'
    });

    socket.on('item_sold_event', (soldData) => {
        // console.log('Presenter: Item sold event:', soldData);
        updateSoldTicker(soldData);
        // The full_state_update that follows will clear the current item.
    });
    
    socket.on('item_passed_event', (passData) => {
        // console.log('Presenter: Item passed event:', passData);
        handleItemPassed(passData);
        // The full_state_update that follows will clear the current item.
    });

    function fetchTeamsData() {
        fetch('/api/all_teams_status')
            .then(response => response.json())
            .then(data => {
                allTeamsData = data;
                populateTeamsOverview(data);
            })
            .catch(error => console.error('Error fetching teams data:', error));
    }

    function populateTeamsOverview(teams) {
        const teamsListDiv = document.getElementById('teams-list');
        if (!teamsListDiv) return;
        teamsListDiv.innerHTML = ''; // Clear existing

        Object.keys(teams).sort().forEach(teamName => {
            const team = teams[teamName];
            const card = document.createElement('div');
            card.className = 'team-card';
            card.innerHTML = `<h4>${teamName}</h4>
                              <p>Funds: ₹${team.money.toLocaleString()}</p>`;
            if (team.logo_path) {
                const logo = document.createElement('img');
                logo.src = team.logo_path;
                logo.alt = `${teamName} logo`;
                card.appendChild(logo);
            }
            card.addEventListener('click', () => displayTeamRosterInModal(teamName, allTeamsData));
            teamsListDiv.appendChild(card);
        });
    }
    
    setupModalCloseButton();
});
