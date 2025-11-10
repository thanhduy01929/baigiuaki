import socket
import threading
import json
import time
from server.lobby import Lobby
from server.game_logic import ChessGame
from common.message import Message
from common.constants import HOST, PORT, CHAT_PORT, TIME_LIMIT_SECONDS

class ChessServer:
    def __init__(self):
        self.lobby = Lobby()
        self.games = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

    def start(self):
        self.server_socket.bind(("0.0.0.0", PORT))
        self.server_socket.listen(10)
        self.chat_socket.bind(("0.0.0.0", CHAT_PORT))
        self.chat_socket.listen(10)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        print(f"Server started on 0.0.0.0:{PORT}")
        print(f"Chat server started on 0.0.0.0:{CHAT_PORT}")

        threading.Thread(target=self.accept_chat_connections, daemon=True).start()
        self.accept_connections()

    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"New connection from {addr}")
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

    def accept_chat_connections(self):
        while True:
            chat_socket, addr = self.chat_socket.accept()
            print(f"New chat connection from {addr}")
            chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            threading.Thread(target=self.handle_chat, args=(chat_socket, addr), daemon=True).start()

    def handle_client(self, client_socket, addr):
        connected = True
        while connected:
            try:
                client_socket.settimeout(30.0)
                print(f"Waiting for data from {addr}...")
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    print(f"No data received from {addr}, closing connection")
                    connected = False
                    break
                print(f"Raw data received from {addr}: {data}")
                try:
                    message = Message.from_json(data)
                    print(f"Received message from {addr}: {message.type}")
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from {addr}: {e}")
                    self.send_message(client_socket, Message("ERROR", {"message": "Invalid message format"}))
                    continue

                if message.type == "JOIN_LOBBY":
                    player_id = message.data.get("player_id", f"Player_{addr[1]}")
                    print(f"Received JOIN_LOBBY from {player_id}")
                    with self.lock:
                        game_id = self.lobby.add_player(player_id, client_socket)
                        if game_id:
                            print(f"Starting game {game_id} for {player_id}")
                            self.start_game(game_id, client_socket, player_id)
                        else:
                            print(f"{player_id} is waiting for an opponent")
                            self.send_message(client_socket, Message("WAITING", {"message": "Waiting for opponent..."}))
                elif message.type == "SPECTATE":
                    game_id = message.data.get("game_id")
                    print(f"Received SPECTATE request for game {game_id}")
                    with self.lock:
                        if self.lobby.add_spectator(game_id, client_socket):
                            self.games[game_id].add_spectator(client_socket)
                            self.send_message(client_socket, Message("SPECTATE_START", {"game_id": game_id, "board": self.games[game_id].board.fen()}))
                        else:
                            self.send_message(client_socket, Message("ERROR", {"message": "Game not found"}))
                elif message.type == "GET_GAMES":
                    print(f"Received GET_GAMES from {addr}")
                    with self.lock:
                        game_list = list(self.games.keys())
                        print(f"Preparing to send game list to {addr}: {game_list}")
                        message = Message("GAME_LIST", {"games": game_list})
                        self.send_message(client_socket, message)
                        print(f"Sent GAME_LIST to {addr}, keeping connection open")
                else:
                    print(f"Unknown message type from {addr}: {message.type}")
                    self.send_message(client_socket, Message("ERROR", {"message": "Unknown message type"}))

            except socket.timeout:
                print(f"Timeout waiting for data from {addr}")
                connected = False
                break
            except Exception as e:
                print(f"Error handling client {addr}: {e}")
                connected = False
                break
        try:
            client_socket.close()
            print(f"Closed connection with {addr}")
        except:
            pass

    def start_game(self, game_id, client_socket, player_id):
        with self.lock:
            if game_id not in self.games:
                self.games[game_id] = ChessGame(game_id, TIME_LIMIT_SECONDS)
            
            game = self.games[game_id]
            players = self.lobby.get_game_players(game_id)
            print(f"Players in game {game_id}: {list(players.keys())}")
            
            if len(players) == 2:
                game.add_player(list(players.keys())[0], "white", players[list(players.keys())[0]])
                game.add_player(list(players.keys())[1], "black", players[list(players.keys())[1]])
                
                for pid, socket in players.items():
                    color = "white" if pid == list(players.keys())[0] else "black"
                    print(f"Sending GAME_START to {pid} as {color}")
                    self.send_message(socket, Message("GAME_START", {
                        "game_id": game_id,
                        "color": color,
                        "opponent": list(players.keys())[0] if pid == list(players.keys())[1] else list(players.keys())[1],
                        "board": game.board.fen()
                    }))
                
                threading.Thread(target=self.manage_turns, args=(game,), daemon=True).start()
            
            self.handle_game_moves(game, client_socket, player_id)

    def handle_game_moves(self, game, client_socket, player_id):
        try:
            client_socket.settimeout(30.0)
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    print(f"No move data received from {player_id}")
                    break

                message = Message.from_json(data)
                print(f"Received {message.type} from {player_id}")
                if message.type == "MOVE":
                    move = message.data["move"]
                    if game.make_move(player_id, move):
                        self.broadcast_game_state(game)
                    else:
                        self.send_message(client_socket, Message("INVALID_MOVE", {"message": "Invalid move"}))

        except socket.timeout:
            print(f"Timeout waiting for moves from {player_id}")
        except Exception as e:
            print(f"Error handling moves for {player_id}: {e}")

    def manage_turns(self, game):
        while not game.is_game_over():
            current_player = game.current_player()
            game.start_turn_timer()
            
            while game.current_player() == current_player and not game.is_game_over():
                if game.has_timed_out():
                    game.end_game(f"{current_player} timed out")
                    self.broadcast_game_state(game)
                    break
                threading.Event().wait(1)

    def handle_chat(self, chat_socket, addr):
        try:
            chat_socket.settimeout(30.0)
            while True:
                message = chat_socket.recv(1024).decode('utf-8')
                if not message:
                    print(f"No chat data received from {addr}")
                    break
                chat_msg = Message.from_json(message)
                print(f"Received chat message from {addr}: {chat_msg.type}")
                if chat_msg.type == "CHAT":
                    game_id = chat_msg.data["game_id"]
                    if game_id in self.games:
                        self.games[game_id].broadcast_chat(chat_msg.data["message"])
        except socket.timeout:
            print(f"Timeout waiting for chat from {addr}")
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
        
        for player_id, socket in game.players.items():
            if socket:
                print(f"Broadcasting game state to {player_id}")
                self.send_message(socket, message)
        for spectator_socket in game.spectators:
            if spectator_socket:
                self.send_message(spectator_socket, message)

    def send_message(self, socket, message):
        try:
            print(f"Sending message to {socket.getpeername()}: {message.type}")
            json_data = message.to_json()
            # Add validation to ensure the JSON is valid
            json.loads(json_data)  # Test if the JSON is valid
            socket.send(json_data.encode('utf-8'))
            time.sleep(0.2)  # Increased delay to ensure client receives the message
        except json.JSONDecodeError as e:
            print(f"Invalid JSON message: {e}")
            # Send a simplified error message instead
            error_msg = {"type": "ERROR", "data": {"message": "Server error"}}
            socket.send(json.dumps(error_msg).encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
