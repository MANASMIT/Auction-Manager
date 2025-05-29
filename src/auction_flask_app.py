# --- auction_flask_app.py ---
import os
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Disable werkzeug logs for cleaner terminal, or set to INFO for debugging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) # or logging.WARNING

# Global variable to hold the AuctionApp instance from Tkinter
# This is a simple way to share; for larger apps, consider more robust patterns.
tk_auction_app_instance = None
flask_socketio_instance = None

def create_flask_app(auction_app_ref):
    global tk_auction_app_instance, flask_socketio_instance

    tk_auction_app_instance = auction_app_ref

    # Determine template and static folder paths relative to this script's location
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_folder = os.path.join(base_dir, 'templates')
    static_folder = os.path.join(base_dir, 'static')

    if not os.path.isdir(template_folder):
        print(f"WARNING: Template folder not found at {template_folder}")
    if not os.path.isdir(static_folder):
        print(f"WARNING: Static folder not found at {static_folder}")


    flask_app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    flask_app.config['SECRET_KEY'] = os.urandom(24) # Essential for SocketIO sessions
    flask_app.config['TEMPLATES_AUTO_RELOAD'] = True # Useful for development

    # Use 'threading' for async_mode when running SocketIO with an external server (like Tkinter control)
    # For production with gunicorn/eventlet/gevent, this would be different.
    socketio = SocketIO(flask_app, async_mode='threading', cors_allowed_origins="*") # Allow all for simplicity
    flask_socketio_instance = socketio # Store for external emit access if needed

    # --- Routes ---
    @flask_app.route('/')
    def index():
        return "Auction Webview Server is running. Access /presenter or /manager/YourTeamName"

    @flask_app.route('/presenter')
    def presenter_view_route():
        if not tk_auction_app_instance:
            return "Auction App not initialized", 500
        return render_template('presenter_view.html',
                               auction_name=tk_auction_app_instance.engine.get_auction_name())

    @flask_app.route('/manager/<team_name>')
    def team_manager_view_route(team_name):
        if not tk_auction_app_instance:
            return "Auction App not initialized", 500
        
        engine_teams = tk_auction_app_instance.engine.teams_data
        if team_name not in engine_teams:
            return f"Team '{team_name}' not found in this auction.", 404
        
        # Provide all team names for the manager to view others
        all_team_names = sorted(list(engine_teams.keys()))

        return render_template('team_manager_view.html',
                               auction_name=tk_auction_app_instance.engine.get_auction_name(),
                               my_team_name=team_name,
                               all_team_names=all_team_names)

    # --- API Routes for dynamic data loading by JS ---
    @flask_app.route('/api/all_teams_status')
    def api_all_teams_status():
        if not tk_auction_app_instance: return jsonify({"error": "Auction not ready"}), 500
        
        teams_status = {}
        engine_teams = tk_auction_app_instance.engine.teams_data
        for team_name, data in engine_teams.items():
            teams_status[team_name] = {
                "money": data["money"],
                "logo_path": tk_auction_app_instance._get_web_path(data.get("logo_path")),
                "inventory": { # Convert player names to simple list or dict with purchase price
                    p_name: p_price 
                    for p_name, p_price in data.get("inventory", {}).items()
                }
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
            "photo_path": tk_auction_app_instance._get_web_path(player_info.get("photo_path"))
            # Add other details like role if available later
        })


    # --- SocketIO Event Handlers ---
    @socketio.on('connect', namespace='/presenter')
    def handle_presenter_connect(auth=None): # <--- FIX HERE (add auth=None or *args)
        print(f"Presenter client connected: {request.sid}")
        if tk_auction_app_instance:
            tk_auction_app_instance._emit_full_state_to_webview()

    @socketio.on('connect', namespace='/manager')
    def handle_manager_connect(auth=None): # <--- FIX HERE (add auth=None or *args)
        print(f"Manager client connected: {request.sid}")
        if tk_auction_app_instance:
            tk_auction_app_instance._emit_full_state_to_webview()

    @socketio.on('disconnect', namespace='/presenter')
    def handle_presenter_disconnect():
        print(f"Presenter client disconnected: {request.sid}")

    @socketio.on('disconnect', namespace='/manager')
    def handle_manager_disconnect():
        print(f"Manager client disconnected: {request.sid}")

    @socketio.on('request_initial_data', namespace='/presenter')
    @socketio.on('request_initial_data', namespace='/manager')
    def handle_request_initial_data():
        """Client explicitly requests full data load."""
        if tk_auction_app_instance:
            tk_auction_app_instance._emit_full_state_to_webview()

    @socketio.on('submit_bid_from_manager', namespace='/manager')
    def handle_bid_from_manager_webview(data):
        team_name = data.get('team_name')
        # current_item_name = data.get('item_name') # The item should be known by the engine

        if not tk_auction_app_instance or not tk_auction_app_instance.engine:
            emit('bid_error', {'message': 'Auction engine not ready.'}, room=request.sid)
            return

        engine = tk_auction_app_instance.engine
        if not engine.bidding_active or not engine.current_item_name:
            emit('bid_error', {'message': 'No item currently up for bidding.'}, room=request.sid)
            return
        
        if not team_name:
            emit('bid_error', {'message': 'Team name not provided for bid.'}, room=request.sid)
            return
            
        if team_name not in engine.teams_data:
            emit('bid_error', {'message': f"Team '{team_name}' is not recognized in this auction."}, room=request.sid)
            return

        # --- CRITICAL: Call the Tkinter app's method to place the bid ---
        # This ensures the bid goes through the same validation and state update logic,
        # and that Tkinter UI also updates.
        # The method in Tkinter app needs to handle being called from this (Flask) thread.
        # It should then trigger refresh_all_ui_displays() which includes _emit_full_state_to_webview().
        try:
            # We need a robust way for AuctionApp to schedule this in its main thread
            # or ensure its methods are thread-safe for this call.
            # For now, direct call and AuctionApp's refresh will handle emitting.
            # AuctionApp's place_bid method must handle its own Tkinter UI updates safely.
            tk_auction_app_instance.master.after(0, lambda: tk_auction_app_instance.ui_place_bid_from_webview(team_name))

            # No direct emit here; let AuctionApp's refresh logic send the global update.
            # emit('bid_accepted', {'message': 'Bid submitted, awaiting confirmation.'}, room=request.sid)
        except Exception as e:
            print(f"Error processing bid from manager '{team_name}': {e}")
            emit('bid_error', {'message': f'Error processing bid: {str(e)}'}, room=request.sid)

    return flask_app, socketio 
