// presenter.js

// --- START OF UTILITY FUNCTIONS ---

/**
 * Escapes HTML special characters in a string.
 * @param {string} str The string to escape.
 * @returns {string} The escaped string.
 */
function escapeHTML(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[&<>"']/g, function (match) {
        return {
            '&': '&',
            '<': '<',
            '>': '>',
            '"': '"',
            "'": "'",
        }[match];
    });
}

/**
 * Sets the source for an image element with a fallback.
 * Preloads the image and updates the src, handling errors.
 * @param {HTMLImageElement} imgElement The image element to update.
 * @param {string} newSrc The new image source URL.
 * @param {string} defaultSrc The fallback image source URL.
 */
function setProtectedImageSource(imgElement, newSrc, defaultSrc) {
    if (!imgElement) return;

    const tempImg = new Image();
    tempImg.onload = () => {
        imgElement.src = newSrc; // Use the originally intended newSrc
        imgElement.style.display = 'block';
    };
    tempImg.onerror = () => {
        imgElement.src = defaultSrc;
        imgElement.style.display = 'block';
    };

    // Start loading. If newSrc is falsy, it will effectively trigger onerror for defaultSrc.
    tempImg.src = newSrc || defaultSrc;
}

/**
 * Creates a new Image object with error handling for src.
 * @param {string} src The primary source for the image.
 * @param {string} defaultSrc The fallback source if the primary fails.
 * @param {string} altText The alt text for the image.
 * @returns {HTMLImageElement} The configured Image object.
 */
function createImageWithFallback(src, defaultSrc, altText = '') {
    const img = new Image();
    img.alt = altText;
    img.onerror = () => {
        img.src = defaultSrc; // Fallback if primary src fails or is invalid
    };
    img.src = src || defaultSrc; // If src is falsy, attempt to load defaultSrc directly
    return img;
}

// --- END OF UTILITY FUNCTIONS ---


// Theme Toggle Functionality
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const body = document.body;

if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        body.classList.toggle('dark-theme');
        body.classList.toggle('light-theme');
        // Optional: Store preference in localStorage
        // if (body.classList.contains('dark-theme')) {
        //     localStorage.setItem('theme', 'dark');
        // } else {
        //     localStorage.setItem('theme', 'light');
        // }
    });
    // Optional: Load theme preference on init
    // const preferredTheme = localStorage.getItem('theme');
    // if (preferredTheme === 'dark') {
    //     body.classList.add('dark-theme');
    //     body.classList.remove('light-theme');
    // } else {
    //     body.classList.add('light-theme');
    //     body.classList.remove('dark-theme');
    // }
}


// Socket.IO and Core Functionality
document.addEventListener('DOMContentLoaded', () => {
    // Cached DOM Elements
    const noItemMsgEl = document.getElementById('no-item-message');
    const initialNoItemMessage = noItemMsgEl ? noItemMsgEl.textContent : "No item currently up for auction.";
    const playerCardEl = document.getElementById('current-player-card');
    const itemNameEl = document.getElementById('item-name');
    const itemBaseBidEl = document.getElementById('item-base-bid');
    const itemPhotoEl = document.getElementById('item-photo');
    const currentBidAmountEl = document.getElementById('current-bid-amount');

    const soldOverlayEl = document.getElementById('sold-overlay');
    const soldPlayerNameEl = document.getElementById('sold-player-name');
    const soldTeamNameEl = document.getElementById('sold-team-name');
    const soldPriceEl = document.getElementById('sold-price');
    const soldPlayerImageEl = document.getElementById('sold-player-image');
    const soldTeamLogoEl = document.getElementById('sold-team-logo');

    const tickerListEl = document.getElementById('ticker-list');

    const teamModalEl = document.getElementById('team-modal');
    const modalTeamNameEl = document.getElementById('modal-team-name');
    const modalTeamFundsEl = document.getElementById('modal-team-funds');
    const modalTeamLogoEl = document.getElementById('modal-team-logo');
    const modalTeamRosterEl = document.getElementById('modal-team-roster');
    const closeModalBtn = document.getElementById('close-modal');
    const modalBackdropEl = document.querySelector('.modal-backdrop');

    const teamsContainerLeft = document.getElementById('teams-container-left');
    const teamsContainerRight = document.getElementById('teams-container-right');
    const teamsContainerBottom = document.getElementById('teams-container-bottom');
    const teamsContainerMobile = document.getElementById('teams-container-mobile');

    const socket = io('/presenter');
    let allTeamsData = {};
    let currentDisplayedItemName = null;
    const teamCardAnimationTimeouts = {}; // Stores timeouts for bid animations per team

    const DEFAULT_PLAYER_PHOTO = '/assets/default-player.png';
    const DEFAULT_TEAM_LOGO = '/assets/default-team-logo.png';
    const MAX_TICKER_ITEMS = 10;
    const SOLD_ANIMATION_DURATION = 5000;
    const BID_HIGHLIGHT_DURATION = 20000;
    const PASSED_ITEM_MESSAGE_DURATION = 3000;
    const PLAYER_ENTRANCE_ANIMATION_DURATION = 1000;

    // --- NEW: Canvas Fireworks Logic ---
    let fireworksCanvasInstance = (function() {
        let canvas, ctx;
        let fireworks = [];
        let particles = [];
        let animationFrameId = null; // To store the requestAnimationFrame ID
        let isRunning = false; // Flag to control the animation loop

        // Classes for Firework and Particle (copied directly from index.js)
        class Firework {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = canvas.height;
                this.sx = Math.random() * 3 - 1.5;
                this.sy = Math.random() * -3 - 3;
                this.size = Math.random() * 2 + 1;
                const colorVal = Math.round(0xffffff * Math.random());
                [this.r, this.g, this.b] = [colorVal >> 16, (colorVal >> 8) & 255, colorVal & 255];
                this.shouldExplode = false;
            }
            update() {
                this.shouldExplode = this.sy >= -2 || this.y <= 100 || this.x <= 0 || this.x >= canvas.width;
                this.sy += 0.01;
                [this.x, this.y] = [this.x + this.sx, this.y + this.sy];
            }
            draw() {
                ctx.fillStyle = `rgb(${this.r},${this.g},${this.b})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        class Particle {
            constructor(x, y, r, g, b) {
                [this.x, this.y, this.sx, this.sy, this.r, this.g, this.b] = [x, y, Math.random() * 3 - 1.5, Math.random() * 3 - 1.5, r, g, b];
                this.size = Math.random() * 2 + 1;
                this.life = 100;
            }
            update() {
                [this.x, this.y, this.life] = [this.x + this.sx, this.y + this.sy, this.life - 1];
            }
            draw() {
                ctx.fillStyle = `rgba(${this.r}, ${this.g}, ${this.b}, ${this.life / 100})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        function animate() {
            if (!isRunning) { // Stop animation if not running
                return;
            }

            // Clear the canvas with a transparent fill
            ctx.fillStyle = "rgba(0, 0, 0, 0.2)"; // Adjust alpha for fade effect
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Control the number of fireworks (adjust 0.25 for density)
            if (Math.random() < 0.25) {
                fireworks.push(new Firework());
            }

            fireworks.forEach((firework, i) => {
                firework.update();
                firework.draw();
                if (firework.shouldExplode) {
                    for (let j = 0; j < 50; j++) particles.push(new Particle(firework.x, firework.y, firework.r, firework.g, firework.b));
                    fireworks.splice(i, 1);
                }
            });

            particles.forEach((particle, i) => {
                particle.update();
                particle.draw();
                if (particle.life <= 0) particles.splice(i, 1);
            });

            animationFrameId = requestAnimationFrame(animate);
        }

        function init() {
            canvas = document.getElementById("fireworksCanvas");
            if (!canvas) {
                console.error("Fireworks canvas not found!");
                return;
            }
            ctx = canvas.getContext("2d");

            // Set initial size
            canvas.width = soldOverlayEl.offsetWidth; // Use overlay's dimensions
            canvas.height = soldOverlayEl.offsetHeight;

            // Resize listener specifically for the overlay dimensions
            // No need for window resize listener if canvas resizes with overlay
            // But if the overlay is fixed, it will always be window dimensions anyway.
            // So, for simplicity, tie it to window resize directly if it's full-screen.
            window.addEventListener("resize", () => {
                if(canvas) { // Ensure canvas exists if resize happens early
                    canvas.width = window.innerWidth;
                    canvas.height = window.innerHeight;
                }
            });
            // If the sold overlay is not always 100% width/height, then this needs to be more dynamic.
            // Given the current CSS, it effectively is window dimensions when active.
        }

        function start() {
            if (!canvas || !ctx) {
                init(); // Initialize if not already done
                if (!canvas || !ctx) return; // Exit if init failed
            }
            if (!isRunning) {
                isRunning = true;
                fireworks = []; // Clear any old fireworks
                particles = []; // Clear any old particles
                animationFrameId = requestAnimationFrame(animate); // Start the loop
            }
        }

        function stop() {
            isRunning = false;
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
            // Clear canvas completely when stopping
            if (ctx) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            }
            // Clear all current fireworks and particles for a clean stop
            fireworks = [];
            particles = [];
        }

        // Return the control functions
        return {
            init: init,
            start: start,
            stop: stop
        };

    })(); // End of Canvas Fireworks Instance IIFE
    // --- END NEW: Canvas Fireworks Logic ---

    fireworksCanvasInstance.init();

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
        if (data.current_item !== undefined) updateCurrentItemDisplay(data.current_item);
        if (data.bid_status !== undefined) updateBiddingStatusDisplay(data.bid_status);
        // Consider if fetchTeamsData is needed or if state contains team updates
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
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
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

        const logoPath = team.logo_path;
        const funds = team.money ? team.money.toLocaleString() : '0';
        const playerCount = Object.keys(team.inventory || {}).length;

        const logoImg = createImageWithFallback(logoPath, DEFAULT_TEAM_LOGO, `${teamName} logo`);

        teamCard.innerHTML = `
            <div class="team-logo"></div> <!-- REVERTED: Was team-logo-container -->
            <div class="team-details">
                <h3 class="team-name">${escapeHTML(teamName)}</h3>
                <p class="team-funds">₹${funds}</p>
                <div class="team-players-count">${playerCount} players</div>
            </div>
            <div class="bid-indicator"></div>
        `;
        // Append the pre-created and configured image to the .team-logo div
        teamCard.querySelector('.team-logo').appendChild(logoImg); // REVERTED

        teamCard.addEventListener('click', () => {
            showTeamModal(teamName, allTeamsData);
        });

        return teamCard;
    }

    function populateTeamsGrid(teams) {
        const containers = [teamsContainerLeft, teamsContainerRight, teamsContainerBottom, teamsContainerMobile];
        containers.forEach(container => {
            if (container) container.innerHTML = '';
        });

        const sortedTeamNames = Object.keys(teams).sort();
        const numTeams = sortedTeamNames.length;

        // Populate mobile container (always, if it exists)
        if (teamsContainerMobile) {
            sortedTeamNames.forEach(teamName => {
                teamsContainerMobile.appendChild(createTeamCardNode(teamName, teams[teamName]));
            });
        }

        // Populate desktop containers (if they exist)
        if (teamsContainerLeft && teamsContainerRight && teamsContainerBottom) {
            let counts = { left: 0, right: 0, bottom: 0 };

            if (numTeams === 0) {
                // No teams, counts remain 0
            } else if (numTeams <= 2) {
                counts.bottom = numTeams;
            } else if (numTeams === 3) {
                counts = { left: 1, right: 1, bottom: 1 };
            } else if (numTeams === 4) {
                counts = { left: 1, right: 1, bottom: 2 };
            } else if (numTeams === 5) {
                counts = { left: 1, right: 1, bottom: 3 };
            } else if (numTeams === 6) {
                counts = { left: 2, right: 2, bottom: 2 };
            } else if (numTeams === 7) {
                counts = { left: 2, right: 2, bottom: 3 };
            } else { // numTeams > 7
                counts = { left: 2, right: 2, bottom: numTeams - 4 };
            }

            let teamIndex = 0;
            const appendToContainer = (container, count) => {
                for (let i = 0; i < count; i++) {
                    if (teamIndex < numTeams) {
                        container.appendChild(createTeamCardNode(sortedTeamNames[teamIndex], teams[sortedTeamNames[teamIndex]]));
                        teamIndex++;
                    } else break;
                }
            };

            appendToContainer(teamsContainerLeft, counts.left);
            appendToContainer(teamsContainerRight, counts.right);
            appendToContainer(teamsContainerBottom, counts.bottom);

            // Apply column styling to bottom container
            if (numTeams > 7) {
                teamsContainerBottom.classList.add('strict-three-columns');
                teamsContainerBottom.classList.remove('flexible-columns');
            } else {
                teamsContainerBottom.classList.remove('strict-three-columns');
                teamsContainerBottom.classList.add('flexible-columns');
            }
        }
    }

    function updateCurrentItemDisplay(itemData) {
        const newItemName = itemData ? itemData.name : null;

        if (itemData && itemData.name) {
            if(noItemMsgEl) noItemMsgEl.style.display = 'none';
            if(playerCardEl) playerCardEl.style.display = 'block';

            if(itemNameEl) itemNameEl.textContent = escapeHTML(itemData.name);
            if(itemBaseBidEl) itemBaseBidEl.textContent = `₹${itemData.base_bid ? itemData.base_bid.toLocaleString() : '0'}`;

            setProtectedImageSource(itemPhotoEl, itemData.photo_path, DEFAULT_PLAYER_PHOTO);

            if (newItemName !== currentDisplayedItemName && playerCardEl) {
                playerCardEl.classList.add('player-entrance');
                setTimeout(() => {
                    playerCardEl.classList.remove('player-entrance');
                }, PLAYER_ENTRANCE_ANIMATION_DURATION);
            }
        } else {
            if(noItemMsgEl) noItemMsgEl.style.display = 'block';
            if(playerCardEl) playerCardEl.style.display = 'none';
        }
        currentDisplayedItemName = newItemName;
    }

    function clearAllBidAnimations() {
        document.querySelectorAll('.team-card.bidding').forEach(card => {
            card.classList.remove('bidding');
            const indicator = card.querySelector('.bid-indicator');
            if (indicator) {
                indicator.classList.remove('active');
                indicator.textContent = ''; // Clear bid amount text
            }
        });
        Object.keys(teamCardAnimationTimeouts).forEach(teamName => {
            clearTimeout(teamCardAnimationTimeouts[teamName]);
            delete teamCardAnimationTimeouts[teamName];
        });
    }

    function updateBiddingStatusDisplay(bidStatus) {
        if (bidStatus && typeof bidStatus.bid_amount === 'number') {
            if(currentBidAmountEl) currentBidAmountEl.textContent = `₹${bidStatus.bid_amount.toLocaleString()}`;

            if (bidStatus.highest_bidder_name) {
                showBidAnimation(bidStatus.highest_bidder_name, bidStatus.bid_amount);
            } else {
                clearAllBidAnimations(); // No highest bidder, clear all
            }
        } else {
            if(currentBidAmountEl) currentBidAmountEl.textContent = '₹0';
            clearAllBidAnimations(); // Invalid bidStatus or no bid_amount, clear all
        }
    }

    function showBidAnimation(currentHighestBidderTeamName, bidAmount) {
        clearAllBidAnimations(); // Clear previous animations and timeouts

        // Small delay to allow DOM to update / CSS transitions to catch
        const animationDelay = 15; 
        const timeoutId = setTimeout(() => {
            const teamCard = document.querySelector(`.team-card[data-team-name="${currentHighestBidderTeamName}"]`);
            if (!teamCard) {
                console.error(`Team card not found for bid animation: ${currentHighestBidderTeamName}`);
                return;
            }
            const bidIndicator = teamCard.querySelector('.bid-indicator');
            if (!bidIndicator) {
                console.error(`Bid indicator not found for: ${currentHighestBidderTeamName}`);
                return;
            }

            teamCard.classList.add('bidding');
            bidIndicator.textContent = `₹${bidAmount.toLocaleString()}`;
            bidIndicator.classList.add('active');

            // Store timeout to clear this specific animation after a duration
            teamCardAnimationTimeouts[currentHighestBidderTeamName] = setTimeout(() => {
                // Re-query in case card is removed/changed, though less likely here
                const finalTeamCard = document.querySelector(`.team-card[data-team-name="${currentHighestBidderTeamName}"]`);
                if (finalTeamCard) {
                    finalTeamCard.classList.remove('bidding');
                    const finalBidIndicator = finalTeamCard.querySelector('.bid-indicator');
                    if (finalBidIndicator) {
                        finalBidIndicator.classList.remove('active');
                        // Optionally clear text: finalBidIndicator.textContent = '';
                    }
                }
                delete teamCardAnimationTimeouts[currentHighestBidderTeamName];
            }, BID_HIGHLIGHT_DURATION);

        }, animationDelay);
        // While timeoutId is captured, it's primarily managed via teamCardAnimationTimeouts for this specific pattern
    }

function showSoldAnimation(soldData) {
        if (!soldOverlayEl) return;

        if(soldPlayerNameEl) soldPlayerNameEl.textContent = escapeHTML(soldData.player_name);
        if(soldTeamNameEl) soldTeamNameEl.textContent = escapeHTML(soldData.winning_team_name);
        if(soldPriceEl) soldPriceEl.textContent = `₹${soldData.sold_price.toLocaleString()}`;

        setProtectedImageSource(soldPlayerImageEl, soldData.player_photo_path, DEFAULT_PLAYER_PHOTO);
        setProtectedImageSource(soldTeamLogoEl, soldData.winning_team_logo_path, DEFAULT_TEAM_LOGO);

        soldOverlayEl.classList.add('active');

        fireworksCanvasInstance.start(); // NEW: Start canvas fireworks

        setTimeout(() => {
            fireworksCanvasInstance.stop(); // NEW: Stop canvas fireworks
            soldOverlayEl.classList.remove('active');
        }, SOLD_ANIMATION_DURATION);
    }

    function updateSoldTicker(soldData) {
        if (!tickerListEl) return;

        const newItem = document.createElement('li');
        newItem.innerHTML = `<strong>${escapeHTML(soldData.player_name)}</strong> → <em>${escapeHTML(soldData.winning_team_name)}</em> (₹${soldData.sold_price.toLocaleString()})`;

        if (tickerListEl.firstChild) {
            tickerListEl.insertBefore(newItem, tickerListEl.firstChild);
        } else {
            tickerListEl.appendChild(newItem);
        }

        while (tickerListEl.children.length > MAX_TICKER_ITEMS) {
            tickerListEl.removeChild(tickerListEl.lastChild);
        }
    }

    function clearSoldTicker() {
        if (tickerListEl) {
            tickerListEl.innerHTML = '';
        }
    }

    function handleItemPassed(passData) {
        console.log(`Item passed: ${passData.item_name}`);
        const passedMessage = `${escapeHTML(passData.item_name) || 'Item'} - PASSED`;

        if (noItemMsgEl && playerCardEl) {
            noItemMsgEl.textContent = passedMessage;
            noItemMsgEl.style.display = 'block';
            playerCardEl.style.display = 'none';
            // Ensure currentDisplayedItemName is unique to trigger animations if item reappears
            currentDisplayedItemName = `PASSED_${passData.item_name || Date.now()}`;

            setTimeout(() => {
                // Only reset if the "PASSED" message is still displayed
                if (noItemMsgEl.textContent === passedMessage) {
                    noItemMsgEl.textContent = initialNoItemMessage;
                }
            }, PASSED_ITEM_MESSAGE_DURATION);
        }
    }

    function showTeamModal(teamName, teamsData) {
        const team = teamsData[teamName];
        if (!team || !teamModalEl || !modalTeamNameEl || !modalTeamFundsEl || !modalTeamLogoEl || !modalTeamRosterEl) {
            console.error("Modal elements not found or team data missing for modal.");
            return;
        }

        modalTeamNameEl.textContent = escapeHTML(teamName);
        modalTeamFundsEl.textContent = `₹${team.money ? team.money.toLocaleString() : '0'}`;

        // --- START IMAGE OPTIMIZATION (REVISED) ---
        let useDirectSrc = false;
        const teamCardImageEl = document.querySelector(`.team-card[data-team-name="${escapeHTML(teamName)}"] .team-logo img`);

        if (teamCardImageEl && teamCardImageEl.src) {
            const cardSrcNormalized = new URL(teamCardImageEl.src, window.location.href).href;
            const defaultLogoNormalized = new URL(DEFAULT_TEAM_LOGO, window.location.href).href;

            if (cardSrcNormalized === defaultLogoNormalized) {
                // If the card is ALREADY showing the default logo, it means the original logo
                // likely failed to load (or wasn't specified).
                // So, the modal should also just use the default logo without a new network attempt.
                modalTeamLogoEl.src = DEFAULT_TEAM_LOGO;
                modalTeamLogoEl.style.display = 'block';
                useDirectSrc = true;
            } else if (cardSrcNormalized && !cardSrcNormalized.endsWith('undefined')) {
                // If the card has a valid, non-default src, reuse it for the modal.
                modalTeamLogoEl.src = teamCardImageEl.src;
                modalTeamLogoEl.style.display = 'block';
                useDirectSrc = true;
            }
        }

        if (!useDirectSrc) {
            // Fallback: If the card image wasn't found, or if its src was problematic (e.g. undefined),
            // or if some other edge case, then use the robust loading method.
            // This will attempt to load team.logo_path and fall back to DEFAULT_TEAM_LOGO if it fails.
            // This path WILL cause a 404 in the console if team.logo_path points to a non-existent file.
            setProtectedImageSource(modalTeamLogoEl, team.logo_path, DEFAULT_TEAM_LOGO);
        }
        // --- END IMAGE OPTIMIZATION (REVISED) ---

        modalTeamRosterEl.innerHTML = ''; // Clear previous roster
        // ... (rest of the function remains the same) ...
        if (team.inventory && Object.keys(team.inventory).length > 0) {
            const sortedPlayerNames = Object.keys(team.inventory).sort();

            sortedPlayerNames.forEach(playerName => {
                const playerData = team.inventory[playerName];
                const li = document.createElement('li');
                li.innerHTML = `
                    <span class="player-name">${escapeHTML(playerName)}</span>
                    <span class="player-prices">
                        Sold: ₹${playerData.sold_price ? playerData.sold_price.toLocaleString() : 'N/A'}
                        (Base: ₹${playerData.base_bid ? playerData.base_bid.toLocaleString() : 'N/A'})
                    </span>
                `;
                if (playerData.base_bid && playerData.sold_price > playerData.base_bid * 1.5) {
                    li.classList.add('good-buy');
                }
                modalTeamRosterEl.appendChild(li);
            });
        } else {
            modalTeamRosterEl.innerHTML = '<li class="no-players">No players acquired yet</li>';
        }

        teamModalEl.classList.add('active');
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            if (teamModalEl) teamModalEl.classList.remove('active');
        });
    }

    if (modalBackdropEl) {
        modalBackdropEl.addEventListener('click', () => {
            if (teamModalEl) teamModalEl.classList.remove('active');
        });
    }
});