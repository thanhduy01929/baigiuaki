import chess
import time
import threading
from common.message import Message
from enhanced_chess_pieces import EnhancedChessPiece
from server.utils import save_game_state, remove_game

class ChessGame:
    def __init__(self, game_id, time_limit):
        self.game_id = game_id
        self.board = chess.Board()
        self.players = {}  # {player_id: socket}
        self.player_colors = {}  # {player_id: color}
        self.spectators = []
        self.time_limit = time_limit
        self.current_turn_start = None
        self.current_player_id = None
        self.winner = None
        self.lock = threading.Lock()
        # Enhance pieces on the board
        self.enhanced_pieces = {}
        self.enhance_board_pieces()

    def enhance_board_pieces(self):
        """Enhance all pieces on the board using EnhancedChessPiece."""
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                self.enhanced_pieces[square] = EnhancedChessPiece(piece)

    def add_player(self, player_id, color, socket):
        self.players[player_id] = socket
        self.player_colors[player_id] = color
        if color == "white":
            self.current_player_id = player_id

    def add_spectator(self, socket):
        self.spectators.append(socket)

    def current_player(self):
        return self.current_player_id

    def make_move(self, player_id, move):
        with self.lock:
            if player_id != self.current_player_id:
                return False

            try:
                chess_move = chess.Move.from_uci(move)
                if chess_move not in self.board.legal_moves:
                    return False

                # Update enhanced pieces before the move
                if chess_move.from_square in self.enhanced_pieces:
                    del self.enhanced_pieces[chess_move.from_square]
                if chess_move.to_square in self.enhanced_pieces:
                    del self.enhanced_pieces[chess_move.to_square]

                self.board.push(chess_move)
                self.current_player_id = list(self.players.keys())[0 if self.current_player_id == list(self.players.keys())[1] else 1]

                # Update enhanced pieces after the move
                piece = self.board.piece_at(chess_move.to_square)
                if piece:
                    self.enhanced_pieces[chess_move.to_square] = EnhancedChessPiece(piece)

                # Save game state
                state = {
                    "board": self.board.fen(),
                    "current_player": self.current_player(),
                    "players": self.player_colors,
                    "game_over": self.board.is_game_over()
                }
                save_game_state(self.game_id, state)

                if self.board.is_game_over():
                    self.end_game(self.determine_winner())
                return True
            except Exception:
                return False
    def start_turn_timer(self):
        """Start or reset the turn timer."""
        self.current_turn_start = time.time()
        print(f"Turn timer started for {self.current_player_id}")

    def has_timed_out(self):
        """Check if the current player has timed out."""
        if self.current_turn_start is None:
            return False
        elapsed = time.time() - self.current_turn_start
        # Add debug logging
        print(f"Time check: elapsed={elapsed}, limit={self.time_limit}")
        return elapsed > self.time_limit

    def is_game_over(self):
        return self.board.is_game_over() or self.winner is not None

    def end_game(self, winner):
        self.winner = winner
        # Clean up game state
        remove_game(self.game_id)

    def determine_winner(self):
        if self.board.is_checkmate():
            return list(self.players.keys())[0 if self.current_player_id == list(self.players.keys())[1] else 1]
        return "Draw"

    def broadcast_chat(self, message, timestamp=None):
        # If the message contains a timestamp, use it
        if isinstance(message, dict) and "message" in message and "timestamp" in message:
            print(f"Server: Broadcasting chat with timestamp from client: {message['timestamp']}")
            chat_message = Message("CHAT", {
                "game_id": self.game_id,
                "message": message["message"],
                "timestamp": message["timestamp"]
            })
        else:
            # Otherwise, create a new message with the current timestamp
            current_time = time.time()
            print(f"Server: Creating new timestamp for chat: {current_time}")
            chat_message = Message("CHAT", {
                "game_id": self.game_id,
                "message": message,
                "timestamp": timestamp if timestamp else current_time
            })

        for player_id, socket in self.players.items():
            if socket:
                socket.send(chat_message.to_json().encode())
        for spectator_socket in self.spectators:
            if spectator_socket:
                spectator_socket.send(chat_message.to_json().encode())