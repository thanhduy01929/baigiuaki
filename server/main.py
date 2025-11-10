import socket
import threading
import json
import time
from server.lobby import Lobby
from server.game_logic import ChessGame
from common.message import Message
from common.constants import (
    HOST, PORT, CHAT_PORT, TIME_LIMIT_SECONDS
)

class ChessServer:
    def __init__(self):
        self.lobby = Lobby()
        self.games = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

    def start(self):
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(10)
        self.chat_socket.bind((HOST, CHAT_PORT))
        self.chat_socket.listen(10)
        print(f"Server started on {HOST}:{PORT}")
        print(f"Chat server started on {HOST}:{CHAT_PORT}")

        threading.Thread(target=self.accept_chat_connections, daemon=True).start()
        self.accept_connections()

    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

    def accept_chat_connections(self):
        while True:
            chat_socket, addr = self.chat_socket.accept()
            threading.Thread(target=self.handle_chat, args=(chat_socket, addr), daemon=True).start()

    def handle_client(self, client_socket, addr):
        try:
            # Receive initial message to determine client type
            data = client_socket.recv(1024).decode()
            message = Message.from_json(data)

            if message.type == "JOIN_LOBBY":
                player_id = message.data.get("player_id", f"Player_{addr[1]}")
                with self.lock:
                    game_id = self.lobby.add_player(player_id, client_socket)
                    if game_id:
                        self.start_game(game_id, client_socket, player_id)
                    else:
                        # Player is in lobby waiting for opponent
                        self.send_message(client_socket, Message("WAITING", {"message": "Waiting for opponent..."}))

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()

    def start_game(self, game_id, client_socket, player_id):
        with self.lock:
            if game_id not in self.games:
                self.games[game_id] = ChessGame(game_id, TIME_LIMIT_SECONDS)

            game = self.games[game_id]
            players = self.lobby.get_game_players(game_id)

            if len(players) == 2:
                # Assign colors and start the game
                game.add_player(players[0], "white")
                game.add_player(players[1], "black")

                # Notify both players
                for pid, socket in players.items():
                    color = "white" if pid == players[0] else "black"
                    self.send_message(socket, Message("GAME_START", {
                        "game_id": game_id,
                        "color": color,
                        "opponent": players[0] if pid == players[1] else players[1],
                        "board": game.board.fen()
                    }))

                # Start turn management
                threading.Thread(target=self.manage_turns, args=(game,), daemon=True).start()

            # Handle game moves
            self.handle_game_moves(game, client_socket, player_id)

    def handle_game_moves(self, game, client_socket, player_id):
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break

                message = Message.from_json(data)
                if message.type == "MOVE":
                    move = message.data["move"]
                    if game.make_move(player_id, move):
                        # Broadcast updated board to all players and spectators
                        self.broadcast_game_state(game)
                    else:
                        self.send_message(client_socket, Message("INVALID_MOVE", {"message": "Invalid move"}))

            except Exception as e:
                print(f"Error handling moves for {player_id}: {e}")
                break

    def manage_turns(self, game):
        """Manage the turns and time control for a game."""
        print(f"Turn management started for game {game.game_id}")
        try:
            while not game.is_game_over():
                current_player = game.current_player()
                game.start_turn_timer()

                # Wait for the turn to complete or timeout
                wait_start = time.time()
                while game.current_player() == current_player and not game.is_game_over():
                    # Check for timeout every second
                    if game.has_timed_out():
                        print(f"Player {current_player} timed out")
                        game.end_game(f"{current_player} timed out")
                        self.broadcast_game_state(game)
                        break

                    # Prevent infinite loop by adding a maximum wait time
                    if time.time() - wait_start > 300:  # 5 minutes max wait
                        print(f"Maximum wait time exceeded for {current_player}")
                        break

                    # Sleep briefly to avoid high CPU usage
                    threading.Event().wait(1)

                print(f"Turn ended for {current_player}")
        except Exception as e:
            print(f"Error in manage_turns: {e}")
            import traceback
            traceback.print_exc()

    def handle_chat(self, chat_socket, addr):
        try:
            while True:
                message = chat_socket.recv(1024).decode()
                if not message:
                    break
                chat_msg = Message.from_json(message)
                if chat_msg.type == "CHAT":
                    game_id = chat_msg.data["game_id"]
                    print(f"Server received chat message for game {game_id}: {chat_msg.data}")
                    if game_id in self.games:
                        # Pass the entire data object to broadcast_chat to preserve timestamp
                        self.games[game_id].broadcast_chat(chat_msg.data)
        except Exception as e:
            print(f"Error handling chat for {addr}: {e}")
        finally:
            chat_socket.close()

    def broadcast_game_state(self, game):
        state = {
            "board": game.board.fen(),
            "current_player": game.current_player(),
            "game_over": game.is_game_over(),
            "winner": game.winner
        }
        message = Message("GAME_UPDATE", state)

        # Send to all players and spectators
        for player_id, socket in game.players.items():
            self.send_message(socket, message)
        for spectator_socket in game.spectators:
            self.send_message(spectator_socket, message)

    def send_message(self, socket, message):
        try:
            socket.send(message.to_json().encode())
        except Exception as e:
            print(f"Error sending message: {e}")

def start_server():
    server = ChessServer()
    server.start()
