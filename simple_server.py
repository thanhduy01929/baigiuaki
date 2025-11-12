import socket
import threading
import json
import time
import uuid
import chess

# Constants
HOST = "localhost"
PORT = 50004
DEFAULT_TIME_LIMIT = 300  # 5 minutes per player in seconds

# Game state
games = {}  # game_id -> {board, players, current_player}

class SimpleServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

    def start(self):
        # Make sure we can bind to the port
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Try to bind to all interfaces to make it more robust
            self.server_socket.bind(("0.0.0.0", PORT))
            self.server_socket.listen(10)
            print(f"Server started on 0.0.0.0:{PORT}")
        except:
            # Fall back to localhost if that fails
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(10)
            print(f"Server started on {HOST}:{PORT}")

        print("Waiting for connections...")

        self.accept_connections()

    def accept_connections(self):
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                break

    def handle_client(self, client_socket, addr):
        try:
            # Set a timeout for receiving data
            client_socket.settimeout(60.0)

            # Receive initial message
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                print(f"No data received from {addr}, closing connection")
                client_socket.close()
                return

            # Parse message
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "CREATE_GAME":
                self.handle_create_game(client_socket, message)
            elif message_type == "JOIN_GAME":
                self.handle_join_game(client_socket, message)
            elif message_type == "SPECTATE":
                self.handle_spectate_game(client_socket, message)
            elif message_type == "JOIN_LOBBY":
                self.handle_join_lobby(client_socket, message)
            elif message_type == "GET_GAMES":
                self.handle_get_games(client_socket, message)
            else:
                print(f"Unknown message type: {message_type}")
                self.send_message(client_socket, {"type": "ERROR", "message": "Unknown message type"})
                client_socket.close()

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            client_socket.close()

    def handle_get_games(self, client_socket, message):
        """Handle a request for the list of active games"""
        print("Handling GET_GAMES request")
        
        with self.lock:
            # Create a list of game information
            game_list = []
            for game_id, game in games.items():
                # Only include games that are active (waiting or playing)
                if game["status"] in ["waiting", "playing"]:
                    game_info = {
                        "game_id": game_id,
                        "status": game["status"],
                        "spectator_count": len(game.get("spectators", [])),
                        "players": {}
                    }
                    
                    # Add player information
                    for color, player_data in game["players"].items():
                        if isinstance(player_data, dict) and "name" in player_data:
                            game_info["players"][color] = player_data["name"]
                    
                    game_list.append(game_info)
            
            # Send the game list to the client
            self.send_message(client_socket, {
                "type": "GAME_LIST",
                "games": game_list
            })
            print(f"Sent list of {len(game_list)} games")

    def handle_create_game(self, client_socket, message):
        player_name = message.get("player_name")
        player_id = message.get("player_id")
        time_limit = message.get("time_limit", DEFAULT_TIME_LIMIT)  # Get time limit or use default

        if not player_name or not player_id:
            self.send_message(client_socket, {"type": "ERROR", "message": "Missing player information"})
            return

        # Create a new game with a shorter, more readable ID
        # Use a combination of letters and numbers for easier sharing
        import random
        letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ'  # Removed similar looking characters
        numbers = '23456789'  # Removed 0/1 to avoid confusion with O/I

        # Create a 6-character game ID (3 letters + 3 numbers)
        game_id = ''.join(random.choice(letters) for _ in range(3)) + \
                 ''.join(random.choice(numbers) for _ in range(3))

        with self.lock:
            games[game_id] = {
                "board": chess.Board(),
                "players": {
                    "white": {"name": player_name, "id": player_id, "socket": client_socket, 
                             "time_remaining": time_limit}
                },
                "current_player": "white",
                "status": "waiting",
                "spectators": [],
                "created_at": time.time(),  # Add timestamp for sorting
                "time_limit": time_limit,  # Store time limit
                "turn_start_time": None,  # When the current turn started
                "last_move_time": time.time()  # Time of the last move
            }

        print(f"Game {game_id} created by {player_name} ({player_id}) with time limit {time_limit}s")

        # Notify the client
        self.send_message(client_socket, {
            "type": "GAME_CREATED",
            "game_id": game_id,
            "color": "white",
            "time_limit": time_limit
        })

        # Wait for opponent
        self.wait_for_opponent(client_socket, game_id)

    def handle_join_game(self, client_socket, message):
        player_name = message.get("player_name")
        player_id = message.get("player_id")
        game_id = message.get("game_id")

        if not player_name or not player_id or not game_id:
            self.send_message(client_socket, {"type": "ERROR", "message": "Missing information"})
            return

        print(f"Attempting to join game {game_id} with player {player_name} ({player_id})")

        # Check if game exists
        with self.lock:
            if game_id not in games:
                print(f"Game {game_id} not found")
                self.send_message(client_socket, {"type": "ERROR", "message": "Game not found"})
                return

            game = games[game_id]

            # Check if game is waiting for a player
            if game["status"] != "waiting":
                print(f"Game {game_id} is already full")
                self.send_message(client_socket, {"type": "ERROR", "message": "Game is already full"})
                return

            # Add player to game
            time_limit = game.get("time_limit", DEFAULT_TIME_LIMIT)
            game["players"]["black"] = {
                "name": player_name, 
                "id": player_id, 
                "socket": client_socket,
                "time_remaining": time_limit
            }
            game["status"] = "playing"

        print(f"Player {player_name} ({player_id}) joined game {game_id}")

        try:
            # Notify the client
            self.send_message(client_socket, {
                "type": "GAME_JOINED",
                "game_id": game_id,
                "color": "black",
                "opponent": game["players"]["white"]["name"],
                "time_limit": time_limit
            })

            # Notify the other player
            white_socket = game["players"]["white"]["socket"]
            self.send_message(white_socket, {
                "type": "OPPONENT_JOINED",
                "opponent": player_name
            })

            # Give a short delay to ensure messages are processed
            time.sleep(0.5)

            # Start the game
            self.start_game(game_id)
        except Exception as e:
            print(f"Error during game join process: {e}")
            # Try to recover by setting game back to waiting
            with self.lock:
                if game_id in games:
                    games[game_id]["status"] = "waiting"
                    if "black" in games[game_id]["players"]:
                        del games[game_id]["players"]["black"]

    def handle_join_lobby(self, client_socket, message):
        player_id = message.get("player_id")
        if not player_id:
            self.send_message(client_socket, {"type": "ERROR", "message": "Missing player ID"})
            return
        
        print(f"Player {player_id} joining lobby")
        self.send_message(client_socket, {"type": "WAITING", "message": "Waiting for opponent..."})
        
        # In a real implementation, you would match this player with another waiting player
        # For now, just keep the connection open until the client disconnects
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    print(f"Client {player_id} disconnected from lobby")
                    break
                
                # Handle any messages from the client while in the lobby
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "GET_GAMES":
                    # Send list of available games
                    with self.lock:
                        available_games = []
                        for game_id, game in games.items():
                            if game["status"] == "waiting":
                                available_games.append(game_id)
                        
                        self.send_message(client_socket, {
                            "type": "GAME_LIST",
                            "games": available_games
                        })
        except Exception as e:
            print(f"Error in lobby for player {player_id}: {e}")
        finally:
            client_socket.close()

    def handle_spectate_game(self, client_socket, message):
        player_name = message.get("player_name")
        player_id = message.get("player_id")
        game_id = message.get("game_id")

        if not player_name or not player_id or not game_id:
            self.send_message(client_socket, {"type": "ERROR", "message": "Missing information"})
            return

        print(f"Attempting to spectate game {game_id} with player {player_name} ({player_id})")

        # Check if game exists
        with self.lock:
            if game_id not in games:
                print(f"Game {game_id} not found")
                self.send_message(client_socket, {"type": "ERROR", "message": "Game not found"})
                return

            game = games[game_id]

            # Add spectator to game
            if "spectators" not in game:
                game["spectators"] = []
            
            game["spectators"].append({
                "name": player_name,
                "id": player_id,
                "socket": client_socket
            })

        print(f"Player {player_name} ({player_id}) is now spectating game {game_id}")

        try:
            # Get time information
            white_time = game["players"]["white"]["time_remaining"]
            black_time = game["players"]["black"]["time_remaining"] if "black" in game["players"] else game["time_limit"]
            
            # Notify the spectator
            self.send_message(client_socket, {
                "type": "SPECTATE_START",
                "game_id": game_id,
                "board": game["board"].fen(),
                "white_time": white_time,
                "black_time": black_time,
                "current_player": game["current_player"]
            })

            # Notify players that a spectator joined
            for color in ["white", "black"]:
                if color in game["players"] and isinstance(game["players"][color], dict):
                    player_socket = game["players"][color].get("socket")
                    if player_socket:
                        self.send_message(player_socket, {
                            "type": "SPECTATOR_JOINED",
                            "spectator_name": player_name,
                            "spectator_count": len(game["spectators"])
                        })

            # Start a thread to handle the spectator
            threading.Thread(target=self.handle_spectator,
                           args=(client_socket, game_id, player_id),
                           daemon=True).start()
        except Exception as e:
            print(f"Error during spectate process: {e}")
            # Remove spectator on error
            with self.lock:
                if game_id in games and "spectators" in games[game_id]:
                    games[game_id]["spectators"] = [s for s in games[game_id]["spectators"] if s["id"] != player_id]

    def wait_for_opponent(self, client_socket, game_id):
        # This function handles the client that created the game
        try:
            while True:
                with self.lock:
                    if game_id not in games:
                        # Game was deleted
                        return

                    game = games[game_id]
                    if game["status"] == "playing":
                        # Game has started
                        break

                # Wait for messages (like move requests)
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        print(f"Client disconnected while waiting for opponent")
                        self.remove_player_from_game(client_socket, game_id)
                        return

                    message = json.loads(data)
                    if message.get("type") == "CANCEL_GAME":
                        self.remove_player_from_game(client_socket, game_id)
                        return
                except socket.timeout:
                    # Just a timeout, keep waiting
                    continue

            # Handle the game
            self.handle_game(client_socket, game_id, "white")

        except Exception as e:
            print(f"Error waiting for opponent: {e}")
            self.remove_player_from_game(client_socket, game_id)

    def start_game(self, game_id):
        try:
            with self.lock:
                if game_id not in games:
                    print(f"Game {game_id} not found when starting")
                    return

                game = games[game_id]

                # Verify both players are connected
                if "white" not in game["players"] or "black" not in game["players"]:
                    print(f"Missing players in game {game_id}")
                    return

                # Set the turn start time
                game["turn_start_time"] = time.time()
                game["last_move_time"] = time.time()
                
                # Get time limits
                white_time = game["players"]["white"]["time_remaining"]
                black_time = game["players"]["black"]["time_remaining"]

                # Send initial board state to both players
                board_fen = game["board"].fen()

                print(f"Starting game {game_id} with board: {board_fen}")

                # Send to white player
                try:
                    white_socket = game["players"]["white"]["socket"]
                    self.send_message(white_socket, {
                        "type": "GAME_START",
                        "board": board_fen,
                        "current_player": "white",
                        "white_time": white_time,
                        "black_time": black_time
                    })
                    print(f"Sent GAME_START to white player in game {game_id}")
                except Exception as e:
                    print(f"Error sending start message to white player: {e}")
                    return

                # Send to black player
                try:
                    black_socket = game["players"]["black"]["socket"]
                    self.send_message(black_socket, {
                        "type": "GAME_START",
                        "board": board_fen,
                        "current_player": "white",
                        "white_time": white_time,
                        "black_time": black_time
                    })
                    print(f"Sent GAME_START to black player in game {game_id}")
                except Exception as e:
                    print(f"Error sending start message to black player: {e}")
                    return

                # Start a thread to handle the black player
                try:
                    black_socket = game["players"]["black"]["socket"]
                    threading.Thread(target=self.handle_game,
                                   args=(black_socket, game_id, "black"),
                                   daemon=True).start()
                    print(f"Started thread for black player in game {game_id}")
                except Exception as e:
                    print(f"Error starting thread for black player: {e}")

                # Start a thread to manage the timer
                threading.Thread(target=self.manage_timer, args=(game_id,), daemon=True).start()
                print(f"Started timer thread for game {game_id}")

        except Exception as e:
            print(f"Error in start_game: {e}")

    def manage_timer(self, game_id):
        """Manage the timer for a game"""
        print(f"Timer management started for game {game_id}")
        try:
            while True:
                with self.lock:
                    if game_id not in games:
                        print(f"Game {game_id} no longer exists, stopping timer")
                        return

                    game = games[game_id]
                    
                    if game["status"] == "finished":
                        print(f"Game {game_id} is finished, stopping timer")
                        return
                    
                    # Only update time if the game is in progress
                    if game["status"] == "playing" and game["turn_start_time"] is not None:
                        current_player = game["current_player"]
                        
                        # Calculate elapsed time since turn start
                        current_time = time.time()
                        elapsed = current_time - game["turn_start_time"]
                        
                        # Update the player's remaining time
                        if current_player in game["players"]:
                            player = game["players"][current_player]
                            player["time_remaining"] = max(0, player["time_remaining"] - elapsed)
                            
                            # Check for timeout
                            if player["time_remaining"] <= 0:
                                print(f"Player {current_player} in game {game_id} has run out of time")
                                game["status"] = "finished"
                                game["winner"] = "black" if current_player == "white" else "white"
                                
                                # Notify both players
                                for color, player_data in game["players"].items():
                                    if "socket" in player_data:
                                        self.send_message(player_data["socket"], {
                                            "type": "GAME_OVER",
                                            "winner": game["winner"],
                                            "reason": "timeout"
                                        })
                                
                                # Notify spectators
                                for spectator in game.get("spectators", []):
                                    if "socket" in spectator:
                                        self.send_message(spectator["socket"], {
                                            "type": "GAME_OVER",
                                            "winner": game["winner"],
                                            "reason": "timeout"
                                        })
                                
                                return
                        
                        # Update turn start time for next calculation
                        game["turn_start_time"] = current_time
                        
                        # Send time updates every second
                        if current_time - game["last_move_time"] >= 1.0:
                            game["last_move_time"] = current_time
                            
                            # Get current time values
                            white_time = game["players"]["white"]["time_remaining"]
                            black_time = game["players"]["black"]["time_remaining"]
                            
                            # Send time updates to players
                            for color, player_data in game["players"].items():
                                if "socket" in player_data:
                                    self.send_message(player_data["socket"], {
                                        "type": "TIME_UPDATE",
                                        "white_time": white_time,
                                        "black_time": black_time,
                                        "current_player": current_player
                                    })
                            
                            # Send time updates to spectators
                            for spectator in game.get("spectators", []):
                                if "socket" in spectator:
                                    self.send_message(spectator["socket"], {
                                        "type": "TIME_UPDATE",
                                        "white_time": white_time,
                                        "black_time": black_time,
                                        "current_player": current_player
                                    })
                
                # Sleep for a short time to avoid excessive CPU usage
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error in timer management for game {game_id}: {e}")

    def handle_game(self, client_socket, game_id, color):
        try:
            while True:
                with self.lock:
                    if game_id not in games:
                        # Game was deleted
                        return

                    game = games[game_id]
                    if game["status"] == "finished":
                        # Game is over
                        return

                # Wait for messages
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        print(f"Client disconnected during game")
                        self.handle_player_disconnect(client_socket, game_id, color)
                        return

                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "MOVE":
                        self.handle_move(client_socket, game_id, color, message)
                    elif message_type == "CHAT":
                        self.handle_chat(client_socket, game_id, color, message)
                    elif message_type == "RESIGN":
                        self.handle_resign(client_socket, game_id, color)

                except socket.timeout:
                    # Just a timeout, keep waiting
                    continue

        except Exception as e:
            print(f"Error handling game: {e}")
            self.handle_player_disconnect(client_socket, game_id, color)

    def handle_spectator(self, client_socket, game_id, spectator_id):
        try:
            while True:
                with self.lock:
                    if game_id not in games:
                        # Game was deleted
                        return

                    game = games[game_id]
                    if game["status"] == "finished":
                        # Game is over
                        return

                # Wait for messages (only chat from spectators)
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        print(f"Spectator disconnected")
                        self.handle_spectator_disconnect(client_socket, game_id, spectator_id)
                        return

                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "CHAT":
                        self.handle_spectator_chat(client_socket, game_id, spectator_id, message)

                except socket.timeout:
                    # Just a timeout, keep waiting
                    continue

        except Exception as e:
            print(f"Error handling spectator: {e}")
            self.handle_spectator_disconnect(client_socket, game_id, spectator_id)

    def handle_spectator_chat(self, client_socket, game_id, spectator_id, message):
        """Handle a chat message from a spectator"""
        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]

            # Get the spectator's name
            spectator_name = None
            for spec in game.get("spectators", []):
                if spec["id"] == spectator_id:
                    spectator_name = spec["name"]
                    break

            if not spectator_name:
                return

            chat_text = message.get("message", "")
            if not chat_text:
                return

            # Add [Spectator] prefix to the message
            formatted_message = f"[Spectator] {spectator_name}: {chat_text}"
            print(f"Chat from spectator {spectator_name} in game {game_id}: {chat_text}")

            # Forward the message to both players
            for color in ["white", "black"]:
                if color in game["players"]:
                    player_socket = game["players"][color]["socket"]
                    self.send_message(player_socket, {
                        "type": "CHAT",
                        "player_name": f"[Spectator] {spectator_name}",
                        "message": chat_text
                    })

            # Forward to other spectators
            for spec in game.get("spectators", []):
                if spec["id"] != spectator_id:
                    self.send_message(spec["socket"], {
                        "type": "CHAT",
                        "player_name": f"[Spectator] {spectator_name}",
                        "message": chat_text
                    })

    def handle_spectator_disconnect(self, client_socket, game_id, spectator_id):
        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]
            
            # Get spectator name before removing
            spectator_name = None
            for spec in game.get("spectators", []):
                if spec["id"] == spectator_id:
                    spectator_name = spec["name"]
                    break
            
            # Remove spectator from the game
            if "spectators" in game:
                game["spectators"] = [s for s in game["spectators"] if s["id"] != spectator_id]
                print(f"Spectator {spectator_id} disconnected from game {game_id}")
                
                # Notify players that a spectator left
                for color in ["white", "black"]:
                    if color in game["players"] and isinstance(game["players"][color], dict):
                        player_socket = game["players"][color].get("socket")
                        if player_socket:
                            self.send_message(player_socket, {
                                "type": "SPECTATOR_LEFT",
                                "spectator_name": spectator_name,
                                "spectator_count": len(game["spectators"])
                            })

    def handle_move(self, client_socket, game_id, color, message):
        move_uci = message.get("move")

        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]

            # Check if it's this player's turn
            if game["current_player"] != color:
                self.send_message(client_socket, {
                    "type": "ERROR",
                    "message": "Not your turn"
                })
                return

            # Try to make the move
            try:
                move = chess.Move.from_uci(move_uci)
                if move in game["board"].legal_moves:
                    # Make the move
                    game["board"].push(move)

                    # Update current player
                    next_player = "black" if color == "white" else "white"
                    game["current_player"] = next_player
                    
                    # Reset turn start time for the next player
                    game["turn_start_time"] = time.time()
                    game["last_move_time"] = time.time()

                    # Check for game end conditions
                    game_over = False
                    winner = None

                    if game["board"].is_checkmate():
                        game_over = True
                        winner = color
                        game["status"] = "finished"
                        game["winner"] = winner
                    elif game["board"].is_stalemate() or game["board"].is_insufficient_material():
                        game_over = True
                        winner = "draw"
                        game["status"] = "finished"
                        game["winner"] = winner

                    # Get current time values
                    white_time = game["players"]["white"]["time_remaining"]
                    black_time = game["players"]["black"]["time_remaining"]

                    # Send updated board to both players and spectators
                    self.broadcast_game_state(game, white_time, black_time)
                else:
                    self.send_message(client_socket, {
                        "type": "ERROR",
                        "message": "Invalid move"
                    })
            except Exception as e:
                self.send_message(client_socket, {
                    "type": "ERROR",
                    "message": f"Error processing move: {e}"
                })

    def handle_chat(self, client_socket, game_id, color, message):
        """Handle a chat message from a player"""
        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]

            # Get the player's name
            player_name = message.get("player_name", "Unknown")
            chat_text = message.get("message", "")

            if not chat_text:
                return

            print(f"Chat from {player_name} in game {game_id}: {chat_text}")

            # Forward the message to the other player
            other_color = "black" if color == "white" else "white"
            if other_color in game["players"]:
                other_socket = game["players"][other_color]["socket"]
                self.send_message(other_socket, {
                    "type": "CHAT",
                    "player_name": player_name,
                    "message": chat_text
                })
                
            # Forward to all spectators
            for spectator in game.get("spectators", []):
                self.send_message(spectator["socket"], {
                    "type": "CHAT",
                    "player_name": player_name,
                    "message": chat_text
                })

    def handle_resign(self, client_socket, game_id, color):
        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]
            game["status"] = "finished"

            # The other player wins
            winner = "black" if color == "white" else "white"
            game["winner"] = winner

            # Notify both players
            for player_color, player in game["players"].items():
                self.send_message(player["socket"], {
                    "type": "GAME_OVER",
                    "winner": winner,
                    "reason": "resignation"
                })
                
            # Notify spectators
            for spectator in game.get("spectators", []):
                self.send_message(spectator["socket"], {
                    "type": "GAME_OVER",
                    "winner": winner,
                    "reason": "resignation"
                })

    def handle_player_disconnect(self, client_socket, game_id, color):
        with self.lock:
            if game_id not in games:
                return

            game = games[game_id]
            game["status"] = "finished"

            # The other player wins
            winner = "black" if color == "white" else "white"
            game["winner"] = winner

            # Notify the other player
            other_color = "black" if color == "white" else "white"
            if other_color in game["players"]:
                other_socket = game["players"][other_color]["socket"]
                self.send_message(other_socket, {
                    "type": "GAME_OVER",
                    "winner": winner,
                    "reason": "disconnect"
                })
                
            # Notify spectators
            for spectator in game.get("spectators", []):
                self.send_message(spectator["socket"], {
                    "type": "GAME_OVER",
                    "winner": winner,
                    "reason": "disconnect"
                })

    def broadcast_game_state(self, game, white_time, black_time):
        """Send the current game state to all players and spectators."""
        try:
            state = {
                "board": game["board"].fen(),
                "current_player": game["current_player"],
                "game_over": game["status"] == "finished",
                "winner": game.get("winner"),
                "white_time": white_time,
                "black_time": black_time
            }
            
            message = {
                "type": "BOARD_UPDATE",
                "board": state["board"],
                "current_player": state["current_player"],
                "game_over": state["game_over"],
                "winner": state["winner"],
                "white_time": state["white_time"],
                "black_time": state["black_time"]
            }
            
            # Send to both players with error handling for each
            for color in ["white", "black"]:
                if color in game["players"]:
                    try:
                        player_socket = game["players"][color]["socket"]
                        self.send_message(player_socket, message)
                    except Exception as e:
                        print(f"Error sending to {color} player: {e}")
            
            # Send to all spectators with error handling for each
            for spectator in game.get("spectators", []):
                try:
                    self.send_message(spectator["socket"], message)
                except Exception as e:
                    print(f"Error sending to spectator: {e}")
                    
        except Exception as e:
            print(f"Error in broadcast_game_state: {e}")

    def remove_player_from_game(self, client_socket, game_id):
        with self.lock:
            if game_id in games:
                del games[game_id]

    def send_message(self, socket, message):
        try:
            data = json.dumps(message).encode('utf-8')
            socket.send(data)
        except Exception as e:
            print(f"Error sending message: {e}")

if __name__ == "__main__":
    server = SimpleServer()
    server.start()
