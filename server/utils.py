import json
import os

def save_game_state(game_id, state):
    """Save the game state to chess_games_list.json."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chess_games_list.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"games": []}

    # Update or add the game state
    game_entry = {"game_id": game_id, "state": state}
    existing_game = next((game for game in data["games"] if game["game_id"] == game_id), None)
    if existing_game:
        data["games"].remove(existing_game)
    data["games"].append(game_entry)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def load_game_state(game_id):
    """Load the game state from chess_games_list.json."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chess_games_list.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        game_entry = next((game for game in data["games"] if game["game_id"] == game_id), None)
        return game_entry["state"] if game_entry else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def remove_game(game_id):
    """Remove a game from chess_games_list.json."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chess_games_list.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        data["games"] = [game for game in data["games"] if game["game_id"] != game_id]
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
