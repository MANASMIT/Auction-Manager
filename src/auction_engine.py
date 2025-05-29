# --- auction_engine.py ---
import os
import re
import csv
import json
import argparse
from datetime import datetime

# --- Constants (mirrored from auction.py for now, could be shared) ---
LOG_SECTION_CONFIG = "[CONFIG]"
LOG_SECTION_TEAMS_INITIAL = "[TEAMS_INITIAL]"
LOG_SECTION_PLAYERS_INITIAL = "[PLAYERS_INITIAL]"
LOG_SECTION_AUCTION_STATES = "[AUCTION_STATES]"
LOG_SECTION_BID_INCREMENT_RULES = "[BID_INCREMENT_RULES]" # New
LOG_KEY_AUCTION_NAME = "AuctionName"
CSV_DELIMITER = ','

# DEFINE THE MISSING CONSTANTS FOR THE TEMPLATE
LOG_SECTION_PLAYER_ROLES = "[PLAYER_ROLES]" # Actual section format for future
LOG_SECTION_ROSTER_RULES = "[ROSTER_RULES]" # Actual section format for future

class AuctionError(Exception):
    """Base class for auction-specific errors."""
    pass

class InsufficientFundsError(AuctionError):
    pass

class ItemNotSelectedError(AuctionError):
    pass

class InvalidBidError(AuctionError):
    pass

class NoBidsError(AuctionError):
    pass

class LogFileError(AuctionError):
    pass

class InitializationError(AuctionError):
    pass

class AuctionEngine:
    def __init__(self):
        # Core auction state
        self.auction_name = "Untitled Auction"
        self.teams_data = {}  # {team_name: {"money": int, "inventory": {player_name: bid_amount}, "id": team_id}}
        self.players_initial_info = {}  # {player_name: {"base_bid": int, "id": player_id}}
        self.players_available = {}  # {player_name: base_bid} (subset of players_initial_info)

        # Bidding state
        self.current_item_name = None
        self.current_item_base_bid = 0
        self.current_bid_amount = 0
        self.highest_bidder_name = None
        self.bid_history_for_current_item = []  # List of tuples: (team_name or None, amount)
        self.bidding_active = False

        # Bid Increment Rules
        self.DEFAULT_BID_INCREMENT_RULES = [(0, 1), (50, 5), (100, 10), (200, 25)] # Threshold, Increment
        self.bid_increment_rules = list(self.DEFAULT_BID_INCREMENT_RULES) # Initialize with defaults, sorted later
        self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True) # Sort high-to-low for easy lookup

        # ID mapping for logging consistency (populated during init)
        self.team_name_to_id = {}
        self.team_id_to_name = {}
        self.player_name_to_id = {}
        self.player_id_to_name = {}

        # Logging utilities
        self.log_filepath = None
        self._log_file_handle = None
        self._csv_writer = None
        self.last_error_messages = [] # Store list of non-critical errors/warnings

    def _clear_state(self):
        self.auction_name = "Untitled Auction"
        self.teams_data = {}
        self.players_initial_info = {}
        self.players_available = {}
        self.current_item_name = None
        self.current_item_base_bid = 0
        self.current_bid_amount = 0
        self.highest_bidder_name = None
        self.bid_history_for_current_item = []
        self.bidding_active = False
        self.team_name_to_id = {}
        self.team_id_to_name = {}
        self.player_name_to_id = {}
        self.player_id_to_name = {}
        
        self.bid_increment_rules = list(self.DEFAULT_BID_INCREMENT_RULES) # Reset to defaults
        self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
        
        self.log_filepath = None
        if self._log_file_handle and not self._log_file_handle.closed:
            self._log_file_handle.close()
        self._log_file_handle = None
        self._csv_writer = None
        self.last_error_messages = []

    def _add_error(self, message):
        print(f"ENGINE_WARNING: {message}") 
        self.last_error_messages.append(message)

    def get_last_errors_and_clear(self):
        errors = list(self.last_error_messages)
        self.last_error_messages.clear()
        return errors

    def setup_new_auction(self, auction_name_from_setup, teams_list_dicts, players_list_dicts):
        self._clear_state() # Also resets bid_increment_rules to default
        self.auction_name = auction_name_from_setup
        
        safe_name = re.sub(r'[^\w\s_.-]', '', self.auction_name).strip().replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        LOG_FILE_EXTENSION = ".auctionlog" 
        self.log_filepath = f"{safe_name}_{timestamp}{LOG_FILE_EXTENSION}"

        for i, team_dict in enumerate(teams_list_dicts):
            name = team_dict["Team name"]
            money = int(team_dict["Team starting money"])
            team_id = f"T{i+1}"
            if not name.strip():
                raise InitializationError(f"Team name cannot be empty (from input data for team {i+1}).")
            self.teams_data[name] = {"money": money, "inventory": {}, "id": team_id}
            self.team_name_to_id[name] = team_id
            self.team_id_to_name[team_id] = name

        for i, player_dict in enumerate(players_list_dicts):
            name = player_dict["Player name"]
            base_bid = int(player_dict["Bid value"])
            player_id = f"P{101+i}"
            if not name.strip():
                raise InitializationError(f"Player name cannot be empty (from input data for player {i+1}).")
            self.players_initial_info[name] = {"base_bid": base_bid, "id": player_id}
            self.players_available[name] = base_bid
            self.player_name_to_id[name] = player_id
            self.player_id_to_name[player_id] = name
        
        if not self.teams_data:
            raise InitializationError("No teams provided for the new auction.")
        if not self.players_initial_info:
            raise InitializationError("No players provided for the new auction.")

        # Note: set_bid_increment_rules() will be called after this if custom rules from CSV
        self._init_logger_for_new_auction() # This will log the current bid_increment_rules (defaults at this point)
        self.log_auction_state("INITIAL_SETUP", "Initial auction state established.")

    def set_bid_increment_rules(self, rules_list_of_tuples):
        """Sets custom bid increment rules, typically from CSV. Overwrites defaults."""
        if rules_list_of_tuples and isinstance(rules_list_of_tuples, list):
            new_rules = []
            valid_rules_added = False
            for rule in rules_list_of_tuples:
                if isinstance(rule, (list, tuple)) and len(rule) == 2 and \
                   isinstance(rule[0], int) and isinstance(rule[1], int) and \
                   rule[0] >= 0 and rule[1] > 0:
                    new_rules.append(tuple(rule))
                    valid_rules_added = True
                else:
                    self._add_error(f"Invalid bid increment rule format skipped: {rule}")
            
            if valid_rules_added:
                self.bid_increment_rules = new_rules
                self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
                # Re-log initial setup if logger is already open, to capture new rules
                if self._log_file_handle and not self._log_file_handle.closed:
                    # This is tricky. The initial log is already written.
                    # For simplicity, we won't rewrite the whole log header.
                    # The next state log will reflect the current rules.
                    # Ideally, rules are set *before* _init_logger_for_new_auction.
                    # Or, _init_logger could take rules as an argument.
                    # For now, let's assume setup_new_auction is called, then this, then logging starts.
                    # We will ensure _init_logger_for_new_auction logs the *current* self.bid_increment_rules.
                    pass

            else: # Revert to defaults if all provided rules were invalid
                self.bid_increment_rules = list(self.DEFAULT_BID_INCREMENT_RULES)
                self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
                self._add_error("No valid custom bid increment rules provided or all were invalid; using defaults.")
        else: # No rules provided (None) or invalid format, ensure defaults are set and sorted.
            self.bid_increment_rules = list(self.DEFAULT_BID_INCREMENT_RULES)
            self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
            if rules_list_of_tuples is not None : # If it was explicitly not None, it was bad format
                 self._add_error("Custom bid increment rules not in expected list format; using defaults.")


    def load_auction_from_log(self, log_filepath):
        self._clear_state()
        self.log_filepath = log_filepath
        
        if not os.path.exists(self.log_filepath):
            raise LogFileError(f"Log file not found: {self.log_filepath}")

        try:
            with open(self.log_filepath, 'r', newline='', encoding='utf-8') as f_handle:
                reader = csv.reader(f_handle)
                self._parse_initial_setup_from_log(reader) # This will also load bid_increment_rules from log

            last_state_json = None
            with open(self.log_filepath, 'r', newline='', encoding='utf-8') as f_handle:
                reader = csv.reader(f_handle)
                in_states_section = False
                for row_num, row in enumerate(reader):
                    if not row: continue
                    try: first_cell = row[0].strip()
                    except IndexError: self._add_error(f"LogParse (L{row_num+1}): Malformed CSV row (empty)."); continue
                    
                    if first_cell == LOG_SECTION_AUCTION_STATES:
                        in_states_section = True
                        try: next(reader) 
                        except StopIteration: break 
                        continue
                    
                    if in_states_section and not first_cell.startswith('#'):
                        if len(row) >= 3: last_state_json = row[2]
                        else: self._add_error(f"LogParse (L{row_num+1}): Auction state row too short: {row}")

            if last_state_json:
                try:
                    snapshot_dict = json.loads(last_state_json)
                    self._apply_state_snapshot(snapshot_dict)
                except json.JSONDecodeError as e:
                    raise LogFileError(f"Error decoding latest JSON state: {e}. Snapshot: {last_state_json[:200]}")
            else:
                self.players_available = {name: data["base_bid"] for name, data in self.players_initial_info.items()}

        except FileNotFoundError: raise LogFileError(f"Log file not found during load: {self.log_filepath}")
        except IOError as e: raise LogFileError(f"IOError reading log file {self.log_filepath}: {e}")
        
        self._reopen_logger_for_append()
        if not self._log_file_handle: raise LogFileError(f"Could not open log {self.log_filepath} for append.")

    def _parse_initial_setup_from_log(self, reader):
        current_section = None
        initial_teams_loaded, initial_players_loaded = False, False
        # Temporarily clear bid_increment_rules to ensure log's rules are primary if found
        temp_bid_rules_from_log = [] 

        for row_num, row in enumerate(reader):
            if not row: continue
            try: line_cont = row[0].strip()
            except IndexError: self._add_error(f"LogParse (Initial L{row_num+1}): Malformed CSV row."); continue

            if line_cont.startswith('['): 
                current_section = line_cont
                if current_section == LOG_SECTION_AUCTION_STATES: break
                continue

            if current_section == LOG_SECTION_CONFIG:
                if line_cont.startswith('#') and CSV_DELIMITER in line_cont:
                    try:
                        # Split only on the first delimiter for key-value
                        key_part, value_part = line_cont[1:].split(CSV_DELIMITER, 1)
                        key = key_part.strip()
                        value = value_part.strip()

                        if key == LOG_KEY_AUCTION_NAME: self.auction_name = value
                        elif key == "BidIncrementRules" and value:
                            try:
                                loaded_rules = json.loads(value)
                                if isinstance(loaded_rules, list):
                                    for item in loaded_rules:
                                        if isinstance(item, list) and len(item) == 2 and \
                                           isinstance(item[0], int) and isinstance(item[1], int) and \
                                           item[0] >=0 and item[1] > 0:
                                            temp_bid_rules_from_log.append(tuple(item))
                                        else: self._add_error(f"LogParse (Config): Malformed item in BidIncrementRules: {item}")
                                else: self._add_error(f"LogParse (Config): BidIncrementRules not a list: {value}")
                            except json.JSONDecodeError: self._add_error(f"LogParse (Config): Bad BidIncrementRules JSON: {value}")
                    except ValueError: # If split fails
                        self._add_error(f"LogParse (Config L{row_num+1}): Malformed config line (not key-value): {line_cont}")

            elif current_section == LOG_SECTION_TEAMS_INITIAL: # Simplified, assuming CSV from engine
                if line_cont.startswith('#'): continue 
                try:
                    if len(row) >= 3:
                        name, team_id, money_str = row[0].strip(), row[1].strip(), row[2].strip()
                        if not name: self._add_error(f"LogParse (Teams L{row_num+1}): Empty name. Skip: {row}"); continue
                        if not team_id: self._add_error(f"LogParse (Teams L{row_num+1}): Empty ID for '{name}'. Skip: {row}"); continue
                        self.teams_data[name] = {"money": int(money_str), "inventory": {}, "id": team_id}
                        self.team_name_to_id[name] = team_id; self.team_id_to_name[team_id] = name
                        initial_teams_loaded = True
                    else: self._add_error(f"LogParse (Teams L{row_num+1}): Malformed. Skip: {row}")
                except (ValueError, IndexError) as e: self._add_error(f"LogParse (Teams L{row_num+1}): Error {e}. Skip: {row}")

            elif current_section == LOG_SECTION_PLAYERS_INITIAL: # Simplified
                if line_cont.startswith('#'): continue 
                try:
                    if len(row) >= 3:
                        name, player_id, bid_str = row[0].strip(), row[1].strip(), row[2].strip()
                        if not name: self._add_error(f"LogParse (Players L{row_num+1}): Empty name. Skip: {row}"); continue
                        if not player_id: self._add_error(f"LogParse (Players L{row_num+1}): Empty ID '{name}'. Skip: {row}"); continue
                        base_bid = int(bid_str)
                        self.players_initial_info[name] = {"base_bid": base_bid, "id": player_id}
                        self.player_name_to_id[name] = player_id; self.player_id_to_name[player_id] = name
                        initial_players_loaded = True
                    else: self._add_error(f"LogParse (Players L{row_num+1}): Malformed. Skip: {row}")
                except (ValueError, IndexError) as e: self._add_error(f"LogParse (Players L{row_num+1}): Error {e}. Skip: {row}")
        
        if temp_bid_rules_from_log:
            self.bid_increment_rules = temp_bid_rules_from_log
            self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
        else: # No rules in log, ensure defaults are set and sorted
            self.bid_increment_rules = list(self.DEFAULT_BID_INCREMENT_RULES)
            self.bid_increment_rules.sort(key=lambda x: x[0], reverse=True)
            if current_section != LOG_SECTION_AUCTION_STATES: # Only add error if we didn't break early
                 self._add_error("No BidIncrementRules found in log config; using defaults.")


        if not initial_teams_loaded: raise LogFileError("No valid initial team data found in log.")
        if not initial_players_loaded: raise LogFileError("No valid initial player data found in log.")

    def _apply_state_snapshot(self, snapshot_dict, from_history_viewer=False):
        for team_name in self.teams_data:
            self.teams_data[team_name]["money"] = 0 
            self.teams_data[team_name]["inventory"] = {}

        for team_id_snap, status in snapshot_dict.get("teams_status", {}).items():
            team_name = self.team_id_to_name.get(team_id_snap)
            if team_name and team_name in self.teams_data:
                self.teams_data[team_name]["money"] = status.get("money", 0)
                inventory_snap = status.get("inventory", {})
                current_inventory = {}
                for p_id_snap, p_val in inventory_snap.items():
                    p_name = self.player_id_to_name.get(p_id_snap)
                    if p_name and p_name in self.players_initial_info:
                        current_inventory[p_name] = p_val
                    else: self._add_error(f"SnapApply: P ID '{p_id_snap}' inv for '{team_name}' !initial. Skip.")
                self.teams_data[team_name]["inventory"] = current_inventory
            else: self._add_error(f"SnapApply: T ID '{team_id_snap}' !initial. Skip.")

        all_player_names_in_inventories = set()
        for team_data_val in self.teams_data.values():
            all_player_names_in_inventories.update(team_data_val["inventory"].keys())

        self.players_available = {}
        for p_name, p_data in self.players_initial_info.items():
            if p_name not in all_player_names_in_inventories:
                self.players_available[p_name] = p_data["base_bid"]

        cbri = snapshot_dict.get("current_bidding_round_item")
        self.current_item_name = None; self.current_item_base_bid = 0
        self.current_bid_amount = 0; self.highest_bidder_name = None
        self.bid_history_for_current_item = []

        if cbri and cbri.get("player_id"):
            p_id_snap = cbri["player_id"]
            p_name = self.player_id_to_name.get(p_id_snap)
            if p_name and p_name in self.players_initial_info:
                self.current_item_name = p_name
                self.current_item_base_bid = self.players_initial_info[p_name]["base_bid"]
                self.current_bid_amount = cbri.get("current_bid_amount", self.current_item_base_bid)
                
                highest_bidder_id_snap = cbri.get("highest_bidder_team_id")
                if highest_bidder_id_snap:
                    self.highest_bidder_name = self.team_id_to_name.get(highest_bidder_id_snap)
                    if not self.highest_bidder_name: self._add_error(f"SnapApply: HB ID '{highest_bidder_id_snap}' !found.")
                
                self.bid_history_for_current_item = []
                for hist_entry in cbri.get("bidding_history_for_item", []):
                    bidder_team_id_snap = hist_entry.get("bidder_team_id")
                    bidder_team_name = None
                    if bidder_team_id_snap: 
                        bidder_team_name = self.team_id_to_name.get(bidder_team_id_snap)
                        if not bidder_team_name: self._add_error(f"SnapApply: BidHist T ID '{bidder_team_id_snap}' !found. Skip."); continue
                    self.bid_history_for_current_item.append((bidder_team_name, hist_entry.get("amount")))
                
                if self.current_item_name in self.players_available:
                    del self.players_available[self.current_item_name]
            else: self._add_error(f"SnapApply: P ID '{p_id_snap}' for CBI !initial. Clear CBI.")
        
        self.bidding_active = snapshot_dict.get("bidding_active", False)
        if not self.current_item_name: self.bidding_active = False

    def load_state_from_json_string(self, json_state_string, loaded_timestamp, loaded_action_desc, loaded_serial_no):
        try:
            snapshot_dict = json.loads(json_state_string)
            self._apply_state_snapshot(snapshot_dict, from_history_viewer=True)
            log_comment = f"Loaded from log No.{loaded_serial_no} ('{loaded_action_desc}' at {loaded_timestamp})"
            self.log_auction_state("LOAD_HISTORY", log_comment)
            return True, f"Successfully loaded state from log entry No. {loaded_serial_no}."
        except json.JSONDecodeError as e: return False, f"Invalid JSON in log: {e}"
        except Exception as e: return False, f"Failed to apply state: {e}"

    def _init_logger_for_new_auction(self):
        try:
            if self._log_file_handle and not self._log_file_handle.closed: self._log_file_handle.close()
            
            with open(self.log_filepath, 'w', newline='', encoding='utf-8') as f:
                f.write(f"{LOG_SECTION_CONFIG}\n")
                f.write(f"#{LOG_KEY_AUCTION_NAME}{CSV_DELIMITER}{self.auction_name}\n")
                f.write(f"#Date{CSV_DELIMITER}{datetime.now().strftime('%Y-%m-%d')}\n")
                f.write(f"#Time{CSV_DELIMITER}{datetime.now().strftime('%H:%M:%S')}\n")
                f.write(f"#TotalInitialPlayers{CSV_DELIMITER}{len(self.players_initial_info)}\n")
                # Log the effective bid increment rules
                f.write(f"#BidIncrementRules{CSV_DELIMITER}{json.dumps(self.bid_increment_rules)}\n\n") 
                
                f.write(f"{LOG_SECTION_TEAMS_INITIAL}\n")
                team_writer = csv.writer(f); team_writer.writerow(["#TeamName", "TeamID", "StartingMoney"])
                for name, data in self.teams_data.items(): team_writer.writerow([name, data["id"], data["money"]])
                
                f.write("\n"); f.write(f"{LOG_SECTION_PLAYERS_INITIAL}\n")
                player_writer = csv.writer(f); player_writer.writerow(["#PlayerName", "PlayerID", "BaseBid"])
                for name, data in self.players_initial_info.items(): player_writer.writerow([name, data["id"], data["base_bid"]])
                
                f.write("\n"); f.write(f"{LOG_SECTION_AUCTION_STATES}\n")
                event_writer = csv.writer(f); event_writer.writerow(["#Timestamp", "ActionDescription", "JSONStateSnapshot", "Comment"])
            self._reopen_logger_for_append()
        except IOError as e:
            self._log_file_handle = None; self._csv_writer = None
            raise LogFileError(f"Error creating initial log {self.log_filepath}: {e}")

    def _reopen_logger_for_append(self):
        try:
            if self._log_file_handle and not self._log_file_handle.closed: self._log_file_handle.close()
            self.log_filepath = os.path.abspath(self.log_filepath)
            self._log_file_handle = open(self.log_filepath, 'a', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._log_file_handle)
        except IOError as e:
            self._log_file_handle = None; self._csv_writer = None
            self._add_error(f"Failed to open log {self.log_filepath} for append: {e}")

    def log_auction_state(self, action_description, comment=""):
        if not self._csv_writer or not self._log_file_handle or self._log_file_handle.closed:
            self._add_error("Log writer issue. Reopening..."); self._reopen_logger_for_append()
            if not self._csv_writer or not self._log_file_handle or self._log_file_handle.closed:
                self._add_error("Failed to reopen log. State not logged."); return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        teams_status_snapshot = {}
        for team_name, data in self.teams_data.items():
            team_id = self.team_name_to_id.get(team_name)
            inventory_snapshot = { self.player_name_to_id.get(p_name): p_val for p_name, p_val in data["inventory"].items() if self.player_name_to_id.get(p_name) }
            teams_status_snapshot[team_id] = {"money": data["money"], "inventory": inventory_snapshot}

        available_players_snapshot = [ {"id": self.player_name_to_id.get(p_name), "base_bid": base_bid} for p_name, base_bid in self.players_available.items() if self.player_name_to_id.get(p_name) ]
        
        current_bidding_round_snapshot = None
        if self.current_item_name and self.current_item_name in self.players_initial_info:
            p_id = self.player_name_to_id.get(self.current_item_name)
            if p_id:
                bid_history_snapshot = [ {"bidder_team_id": (self.team_name_to_id.get(b_name) if b_name else None), "amount": amt} for b_name, amt in self.bid_history_for_current_item ]
                highest_bidder_team_id_snap = self.team_name_to_id.get(self.highest_bidder_name) if self.highest_bidder_name else None
                current_bidding_round_snapshot = { "player_id": p_id, "base_bid": self.current_item_base_bid, "current_bid_amount": self.current_bid_amount, "highest_bidder_team_id": highest_bidder_team_id_snap, "bidding_history_for_item": bid_history_snapshot }
        
        state_snapshot = { "teams_status": teams_status_snapshot, "available_players_pool": available_players_snapshot, "current_bidding_round_item": current_bidding_round_snapshot, "bidding_active": self.bidding_active }
        json_state_string = json.dumps(state_snapshot)
        try:
            self._csv_writer.writerow([timestamp, action_description, json_state_string, comment])
            self._log_file_handle.flush()
        except Exception as e: self._add_error(f"Failed to write state snapshot to log: {e}")

    def close_logger(self):
        action, comment = "SESSION_END", "Auction session ended."
        if self.bidding_active and self.current_item_name:
            action = f"SESSION_END_AUTO_PASS: {self.current_item_name}"
            comment = "Session ended with item active."
        if self._log_file_handle and not self._log_file_handle.closed:
            self.log_auction_state(action, comment)
            try: self._log_file_handle.close()
            except Exception as e: self._add_error(f"Error closing log {self.log_filepath}: {e}")
        self._log_file_handle = None; self._csv_writer = None

    def select_item_for_bidding(self, player_name):
        if player_name not in self.players_available:
            raise ItemNotSelectedError(f"Player '{player_name}' not available.")
        passed_item_message = None
        if self.bidding_active and self.current_item_name and not self.highest_bidder_name:
            prev_item_name = self.current_item_name
            self.log_auction_state(f"PASS_ITEM_AUTO: {prev_item_name}", f"'{prev_item_name}' passed (new selection).")
            passed_item_message = f"Previous item '{prev_item_name}' was passed (no bids)."

        self.current_item_name = player_name
        self.current_item_base_bid = self.players_initial_info[player_name]["base_bid"]
        self.current_bid_amount = self.current_item_base_bid
        self.highest_bidder_name = None
        self.bid_history_for_current_item = [(None, self.current_bid_amount)]
        self.bidding_active = True
        if player_name in self.players_available: del self.players_available[player_name]
        self.log_auction_state(f"SELECT_ITEM: {player_name}", f"{player_name} selected for auction.")
        return passed_item_message

    def _calculate_next_bid_amount(self):
        bid_val = self.current_bid_amount if self.current_bid_amount is not None else 0
        increment_to_use = 1 
        # self.bid_increment_rules is sorted high-to-low threshold
        for threshold, increment_val in self.bid_increment_rules:
            if bid_val >= threshold:
                increment_to_use = increment_val
                break
        return (bid_val + increment_to_use) if self.highest_bidder_name else bid_val

    def place_bid(self, team_name):
        if not self.bidding_active or not self.current_item_name: raise ItemNotSelectedError("No item active.")
        if team_name not in self.teams_data: raise AuctionError(f"Team '{team_name}' not recognized.")
        if self.highest_bidder_name == team_name: raise InvalidBidError("You are already highest bidder.")
        proposed_bid = self._calculate_next_bid_amount()
        if self.teams_data[team_name]["money"] < proposed_bid:
            raise InsufficientFundsError(f"{team_name} has ₹{self.teams_data[team_name]['money']:,}, needs ₹{proposed_bid:,}")
        self.current_bid_amount = proposed_bid; self.highest_bidder_name = team_name
        self.bid_history_for_current_item.append((team_name, proposed_bid))
        self.log_auction_state(f"BID: {team_name} for {self.current_item_name} at {proposed_bid}", f"Bid by {team_name}")
        return self.current_bid_amount, self.highest_bidder_name

    def undo_last_bid(self):
        if not self.current_item_name or not self.bidding_active: raise ItemNotSelectedError("No active item/bid.")
        if len(self.bid_history_for_current_item) <= 1: raise InvalidBidError("No previous bid (only base).")
        last_bid_team, _ = self.bid_history_for_current_item.pop()
        prev_bidder_name, prev_bid_amount = self.bid_history_for_current_item[-1]
        self.current_bid_amount = prev_bid_amount; self.highest_bidder_name = prev_bidder_name
        self.log_auction_state(f"UNDO_BID: {last_bid_team or 'N/A'} for {self.current_item_name}", f"Last bid undone.")
        return self.current_bid_amount, self.highest_bidder_name

    def sell_current_item(self):
        if not self.bidding_active or not self.current_item_name: raise ItemNotSelectedError("No item up.")
        if not self.highest_bidder_name: raise NoBidsError(f"No bids for {self.current_item_name}.")
        winner_name, final_bid, sold_item_name = self.highest_bidder_name, self.current_bid_amount, self.current_item_name
        self.teams_data[winner_name]["money"] -= final_bid
        self.teams_data[winner_name]["inventory"][sold_item_name] = final_bid
        self.current_item_name = None; self.current_item_base_bid = 0; self.current_bid_amount = 0
        self.highest_bidder_name = None; self.bid_history_for_current_item = []; self.bidding_active = False
        log_message = f"{winner_name} bought {sold_item_name} for ₹{final_bid:,}"
        self.log_auction_state(f"SOLD: {sold_item_name} to {winner_name} for {final_bid}", log_message)
        return sold_item_name, winner_name, final_bid, log_message

    def pass_current_item(self, reason_comment="Player passed/unsold by auctioneer."):
        if not self.bidding_active or not self.current_item_name: raise ItemNotSelectedError("No item active.")
        passed_item_name = self.current_item_name
        if passed_item_name and passed_item_name in self.players_initial_info:
             self.players_available[passed_item_name] = self.players_initial_info[passed_item_name]["base_bid"]
        self.current_item_name = None; self.current_item_base_bid = 0; self.current_bid_amount = 0
        self.highest_bidder_name = None; self.bid_history_for_current_item = []; self.bidding_active = False
        self.log_auction_state(f"PASS_ITEM: {passed_item_name}", reason_comment)
        return passed_item_name

    def get_auction_name(self): return self.auction_name
    def get_all_team_data(self):
        teams_info = []
        team_names_sorted = sorted(self.teams_data.keys())
        for team_name in team_names_sorted:
            data = self.teams_data[team_name]
            inventory_display = [f"  › {p_name} (₹{val:,})" for p_name, val in sorted(data["inventory"].items())] if data["inventory"] else ["  ‹ No players yet ›"]
            teams_info.append({ "name": team_name, "money_raw": data["money"], "money_formatted": f"💰 ₹{data['money']:,}", "inventory_display_lines": inventory_display })
        return teams_info
    def get_available_players_info(self):
        return sorted([(name, bid, f"Base: ₹{bid:,}") for name, bid in self.players_available.items()])
    def get_current_bidding_status_display(self):
        if self.current_item_name:
            item_display_name = f"{self.current_item_name.upper()} (Base: ₹{self.current_item_base_bid:,})"
            status_text = f"₹{self.current_bid_amount:,} by {self.highest_bidder_name.upper()}" if self.highest_bidder_name else f"OPENING AT ₹{self.current_bid_amount:,}"
            status_color_key = "SUCCESS" if self.highest_bidder_name else "WARNING"
        else:
            item_display_name = "-- NONE SELECTED --"; status_text = "WAITING"; status_color_key = "SECONDARY_TEXT"
        return { "item_display_name": item_display_name, "status_text": status_text, "status_color_key": status_color_key, "bidding_active": self.bidding_active }
    def get_log_filepath(self): return self.log_filepath

def generate_template_csv_content():
    """Generates the content for a template CSV file that works directly
    with the current FileSelectPage parser."""
    # Using constants for section names
    template_str = f"""{LOG_SECTION_CONFIG}
{LOG_KEY_AUCTION_NAME},My New Auction
# You can add other specific configurations here if the engine supports them.
# Each config should be on a new line: Key{CSV_DELIMITER}Value

{LOG_SECTION_TEAMS_INITIAL}
Team name,Team starting money
# ^ This line above is the REQUIRED header for the all sections. Do not change its format.
# Add your team data below, one team per line:
Team Alpha,5000
Team Bravo,4800
Team Charlie,5200

{LOG_SECTION_PLAYERS_INITIAL}
Player name,Bid value
# ^ This line above is the REQUIRED header for the all sections. Do not change its format.
# Add your player data below, one player per line:
Player One,100
Player Two,80
Player Three (WK),75
Player Four (BAT),120
Player Five (BOWL),90
Player Six (ALL),110

{LOG_SECTION_BID_INCREMENT_RULES}
# This section is optional. If omitted, or if all rules are commented out,
# default bid increments will be used by the auction engine.
# ---
#Threshold,Increment 
#0,10
#100,20
#250,25
#500,50
#1000,100

# --- Future Sections (Examples - Not yet implemented by engine) ---
# These sections are placeholders and will be ignored by the current version.
# [{LOG_SECTION_PLAYER_ROLES}]
# Player name,Role
# Player One,BATSMAN
# Player Three (WK),WICKETKEEPER
# Player Five (BOWL),BOWLER

# [{LOG_SECTION_ROSTER_RULES}]
# RuleType,Value
# MAX_PLAYERS_PER_TEAM,11
# MIN_BATSMEN,3
# MIN_BOWLERS,3
# MAX_FOREIGN_PLAYERS,4
"""
    return template_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auction Engine utility. Can generate a template CSV for auction setup."
    )
    parser.add_argument(
        "-t", "--template",
        action="store_true",
        help="Generate a template CSV file named 'auction_setup_template.csv' in the current directory."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="auction_setup_template.csv",
        help="Specify the output filename for the template CSV (default: auction_setup_template.csv)."
    )

    args = parser.parse_args()

    if args.template:
        template_content = generate_template_csv_content()
        output_filename = args.output
        try:
            with open(output_filename, "w", newline='', encoding='utf-8') as f:
                f.write(template_content)
            print(f"Template CSV file '{output_filename}' generated successfully.")
        except IOError as e:
            print(f"Error writing template file '{output_filename}': {e}")
    else:
        print("Auction Engine module. Use -t or --template to generate a setup CSV template.",
              "\n\t | python auction_engine.py -t -o my_custom_template_name.csv")