import uuid

class Lobby:
    def __init__(self):
        self.waiting_players = {}  # player_id: socket
        self.games = {}  # game_id: {player_id: socket}

    def add_player(self, player_id, socket):
        print(f"Adding player {player_id}")
        if player_id in self.waiting_players:
            print(f"Player {player_id} already in waiting list")
            return None

        if not self.waiting_players:
            print(f"No waiting players, adding {player_id} to waiting list")
            self.waiting_players[player_id] = socket
            return None

        # Pair with a waiting player
        opponent_id, opponent_socket = next(iter(self.waiting_players.items()))
        print(f"Pairing {player_id} with {opponent_id}")
        del self.waiting_players[opponent_id]

        game_id = str(uuid.uuid4())
        self.games[game_id] = {
            opponent_id: opponent_socket,
            player_id: socket
        }
        print(f"Game {game_id} created with players {opponent_id} and {player_id}")
        return game_id

    def add_spectator(self, game_id, socket):
        print(f"Adding spectator to game {game_id}")
        if game_id in self.games:
            print(f"Game {game_id} found, spectator added")
            return True
        print(f"Game {game_id} not found")
        return False

    def get_game_players(self, game_id):
        print(f"Getting players for game {game_id}")
        return self.games.get(game_id, {})