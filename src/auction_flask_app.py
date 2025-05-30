# auction_flask_app.py

import os, sys
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import logging
from flask import request as flask_request # Alias for clarity

# Disable werkzeug logs for cleaner terminal, or set to INFO for debugging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) # or logging.WARNING

tk_auction_app_instance = None
flask_socketio_instance = None

def get_executable_directory():
    """
    Get the directory of the executable or the script.
    This is reliable for finding data files placed alongside the executable,
    even for one-file PyInstaller bundles.
    """
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (e.g., by PyInstaller)
        # sys.executable is the path to the executable file (this works for one-file and one-dir)
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        # If run as a normal .py script
        application_path = os.path.dirname(os.path.abspath(__file__))
    else:
        # Fallback (e.g. if run from interactive interpreter without __file__)
        application_path = os.getcwd()
    return application_path

def create_flask_app(auction_app_ref):
    global tk_auction_app_instance, flask_socketio_instance
    tk_auction_app_instance = auction_app_ref
   
    base_dir = get_executable_directory()
    print(f"DEBUG: Base directory for resources: {base_dir}")

    template_folder = os.path.join(base_dir, 'templates')
    static_folder = os.path.join(base_dir, 'static')

    if not os.path.isdir(template_folder):
        print(f"WARNING: Template folder not found at {template_folder}")
    if not os.path.isdir(static_folder):
        print(f"WARNING: Static folder not found at {static_folder}")

    # --- Instantiate Flask App FIRST ---
    flask_app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    flask_app.config['SECRET_KEY'] = os.urandom(24)
    flask_app.config['TEMPLATES_AUTO_RELOAD'] = True

    socketio = SocketIO(flask_app, 
                    async_mode='threading', 
                    cors_allowed_origins="*",
                    logger=False,         # Turn on for debugging 
                    engineio_logger=False)# Turn on for debugging
    flask_socketio_instance = socketio

    # --- Now Define Routes ---
    @flask_app.route('/')
    def index():
        return "Auction Webview Server. Presenter: /presenter. Manager: /manager/TeamName/AccessToken"

    @flask_app.route('/presenter')
    def presenter_view_route():
        if not tk_auction_app_instance or not tk_auction_app_instance.presenter_active:
            return "Presenter view is not currently active or auction app not initialized.", 403
        return render_template('presenter_view.html',
                               auction_name=tk_auction_app_instance.engine.get_auction_name())

    @flask_app.route('/manager/<team_name>/<access_token>')
    def team_manager_view_route(team_name, access_token):
        if not tk_auction_app_instance or not tk_auction_app_instance.manager_access_enabled:
            return "Manager access is not currently enabled or auction app not initialized.", 403
        
        engine_teams = tk_auction_app_instance.engine.teams_data
        if team_name not in engine_teams:
            return f"Team '{team_name}' not found in this auction.", 404

        valid_tokens = tk_auction_app_instance.team_manager_access_tokens
        if valid_tokens.get(team_name) != access_token:
            print(f"Invalid access token attempt for team {team_name}. Provided: {access_token}, Expected: {valid_tokens.get(team_name)}")
            return "Invalid access token or team mismatch.", 403
        
        all_team_names = sorted(list(engine_teams.keys()))
        return render_template('team_manager_view.html',
                               auction_name=tk_auction_app_instance.engine.get_auction_name(),
                               my_team_name=team_name,
                               all_team_names=all_team_names,
                               access_token=access_token)

    # --- Special Shutdown Route ---
    def shutdown_server_function(): # Renamed to avoid conflict with flask_request.environ.get
        func = flask_request.environ.get('werkzeug.server.shutdown')
        if func is None:
            print('Not running with the Werkzeug Server or shutdown unavailable.')
            # This is not an HTTP response, just a server-side print
            # The client will likely hang or timeout if shutdown fails here.
            # Consider raising an error or returning a specific value to signal failure.
            return
        func()
        # No return here as server is shutting down.

    @flask_app.route('/shutdown_server_please', methods=['POST'])
    def shutdown_route(): # Renamed route function
        print("Flask app received shutdown request.")
        shutdown_server_function() # Call the actual shutdown
        return "Flask server is attempting to shut down." # This response might not always be sent if shutdown is immediate

    # --- API Routes for dynamic data loading by JS ---
    @flask_app.route('/api/all_teams_status')
    def api_all_teams_status():
        if not tk_auction_app_instance: return jsonify({"error": "Auction not ready"}), 500
        
        teams_status = {}
        engine = tk_auction_app_instance.engine  # Get a reference to the engine for easier access
        engine_teams = engine.teams_data
        engine_players_initial = engine.players_initial_info # Get initial player info
        for team_name, team_data in engine_teams.items():
            inventory_with_base_bid = {}
            for player_name_in_inventory, sold_price in team_data.get("inventory", {}).items():
                player_initial_detail = engine_players_initial.get(player_name_in_inventory)
                base_bid = player_initial_detail.get("base_bid") if player_initial_detail else None # Get base_bid

                inventory_with_base_bid[player_name_in_inventory] = {
                    "sold_price": sold_price,
                    "base_bid": base_bid
                }

            teams_status[team_name] = {
                "money": team_data["money"],
                "logo_path": tk_auction_app_instance._get_web_path(team_name, is_logo=True),
                "inventory": inventory_with_base_bid # Use the new inventory structure
            }
        return jsonify(teams_status)


    @flask_app.route('/api/player_details/<player_name>')
    def api_player_details(player_name):
        if not tk_auction_app_instance: return jsonify({"error": "Auction not ready"}), 500
        player_info = tk_auction_app_instance.engine.players_initial_info.get(player_name)
        if not player_info:
            return jsonify({"error": "Player not found"}), 404
        
        return jsonify({
            "name": player_name,
            "base_bid": player_info.get("base_bid"),
            "photo_path": tk_auction_app_instance._get_web_path(player_name, is_logo=False)
        })

    # --- SocketIO Event Handlers ---
    # ... (rest of your SocketIO handlers) ...
    @socketio.on('connect', namespace='/presenter')
    def handle_presenter_connect(auth=None): 
        if not tk_auction_app_instance or not tk_auction_app_instance.presenter_active:
            print(f"Presenter client connection refused (presenter_active=false): {flask_request.sid}")
            return False 
        print(f"Presenter client connected: {flask_request.sid}")
        if tk_auction_app_instance:
            tk_auction_app_instance._emit_full_state_to_webview() 

    @socketio.on('connect', namespace='/manager')
    def handle_manager_connect(auth_data): 
        if not tk_auction_app_instance or not tk_auction_app_instance.manager_access_enabled:
            print(f"Manager client connection refused (manager_access_enabled=false): {flask_request.sid}")
            return False 

        team_name = auth_data.get('team_name') if auth_data else None
        token = auth_data.get('access_token') if auth_data else None

        if not team_name or not token:
            print(f"Manager client {flask_request.sid} connection refused: Missing team_name or token in auth.")
            return False

        valid_tokens = tk_auction_app_instance.team_manager_access_tokens
        if valid_tokens.get(team_name) != token:
            print(f"Manager client {flask_request.sid} connection refused: Invalid token for team {team_name}.")
            return False
        
        print(f"Manager client for team '{team_name}' connected: {flask_request.sid}")
        if tk_auction_app_instance:
            tk_auction_app_instance._emit_full_state_to_webview()

    @socketio.on('disconnect', namespace='/presenter')
    def handle_presenter_disconnect():
        print(f"Presenter client disconnected: {flask_request.sid}")

    @socketio.on('disconnect', namespace='/manager')
    def handle_manager_disconnect():
        print(f"Manager client disconnected: {flask_request.sid}")

    @socketio.on('request_initial_data', namespace='/presenter')
    def handle_request_initial_data_presenter(): 
        if tk_auction_app_instance and tk_auction_app_instance.presenter_active:
            tk_auction_app_instance._emit_full_state_to_webview()

    @socketio.on('request_initial_data', namespace='/manager')
    def handle_request_initial_data_manager(data): 
        if not tk_auction_app_instance or not tk_auction_app_instance.manager_access_enabled:
            return

        team_name = data.get('team_name')
        token = data.get('access_token')
        valid_tokens = tk_auction_app_instance.team_manager_access_tokens
        if valid_tokens.get(team_name) == token:
            tk_auction_app_instance._emit_full_state_to_webview()
        else:
            print(f"Manager {flask_request.sid} (Team: {team_name}) requested initial data with invalid token.")
            emit('auth_error', {'message': 'Invalid session token for data request.'}, room=flask_request.sid)

    @socketio.on('submit_bid_from_manager', namespace='/manager')
    def handle_bid_from_manager_webview(data):
        if not tk_auction_app_instance or not tk_auction_app_instance.manager_access_enabled:
            emit('bid_error', {'message': 'Manager access currently disabled.'}, room=flask_request.sid)
            return

        team_name = data.get('team_name')
        token = data.get('access_token') 

        valid_tokens = tk_auction_app_instance.team_manager_access_tokens
        if valid_tokens.get(team_name) != token:
            emit('bid_error', {'message': 'Invalid access token for bidding.'}, room=flask_request.sid)
            print(f"Bid attempt from manager with invalid token. Team: {team_name}, SID: {flask_request.sid}")
            return
        
        engine = tk_auction_app_instance.engine
        if not engine.bidding_active or not engine.current_item_name:
            emit('bid_error', {'message': 'No item currently up for bidding.'}, room=flask_request.sid)
            return
        
        if not team_name:
            emit('bid_error', {'message': 'Team name not provided for bid.'}, room=flask_request.sid)
            return
            
        if team_name not in engine.teams_data:
            emit('bid_error', {'message': f"Team '{team_name}' is not recognized in this auction."}, room=flask_request.sid)
            return
        
        try:
            tk_auction_app_instance.master.after(0, lambda: tk_auction_app_instance.ui_place_bid_from_webview(team_name))
        except Exception as e:
            print(f"Error processing bid from manager '{team_name}': {e}")
            emit('bid_error', {'message': f'Error processing bid: {str(e)}'}, room=flask_request.sid)

    @socketio.on('access_revoked', namespace='/manager') 
    def handle_access_revoked_info(data):
        pass 

    return flask_app, socketio