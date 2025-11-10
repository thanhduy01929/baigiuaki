import pygame
import chess
import time
import datetime
from chess_assets import ChessAssets
from common.message import Message
from common.constants import FPS

class ChessGUI:
    def __init__(self, client):
        self.client = client
        self.screen = pygame.display.set_mode((800, 800))
        pygame.display.set_caption("Two-Player Chess")
        self.clock = pygame.time.Clock()
        self.board = chess.Board()
        self.assets = ChessAssets()
        self.square_size = 100
        self.selected_square = None
        self.legal_moves = []
        # Enhanced chat messages structure to store metadata
        self.chat_messages = []  # Will store dicts with text, timestamp, sender, status
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.chat_input = ""
        self.input_active = False
        self.last_message_check = time.time()  # For checking expired messages

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.client.running = False
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_press(event)

            # Check for expired messages (older than 1 minute without reply)
            current_time = time.time()
            if current_time - self.last_message_check > 1.0:  # Check every second
                self.check_expired_messages()
                self.last_message_check = current_time

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_mouse_click(self, pos):
        col = pos[0] // self.square_size
        row = 7 - (pos[1] // self.square_size)
        square = chess.square(col, row)

        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece and ((self.client.color == "white" and piece.color == chess.WHITE) or (self.client.color == "black" and piece.color == chess.BLACK)):
                self.selected_square = square
                self.legal_moves = [move for move in self.board.legal_moves if move.from_square == square]
        else:
            move = None
            for legal_move in self.legal_moves:
                if legal_move.to_square == square:
                    move = legal_move
                    break

            if move:
                self.client.send_move(move.uci())
            self.selected_square = None
            self.legal_moves = []

    def handle_key_press(self, event):
        if event.key == pygame.K_RETURN:
            if self.input_active:
                if self.chat_input:
                    # Add message to local chat with pending status
                    timestamp = time.time()
                    message_text = f"{self.client.player_id}: {self.chat_input}"

                    # Add to local chat with pending status
                    self.add_pending_message(message_text, timestamp)

                    # Send to server
                    self.client.send_chat(self.chat_input, timestamp)
                    self.chat_input = ""
                self.input_active = False
            else:
                self.input_active = True
        elif event.key == pygame.K_ESCAPE:
            self.input_active = False
            self.chat_input = ""
        elif self.input_active:
            if event.key == pygame.K_BACKSPACE:
                self.chat_input = self.chat_input[:-1]
            else:
                self.chat_input += event.unicode

    def draw(self):
        self.screen.fill((255, 255, 255))

        # Draw chessboard
        for row in range(8):
            for col in range(8):
                color = (240, 217, 181) if (row + col) % 2 == 0 else (181, 136, 99)
                pygame.draw.rect(self.screen, color, (col * self.square_size, (7 - row) * self.square_size, self.square_size, self.square_size))

        # Highlight selected square
        if self.selected_square is not None:
            col = chess.square_file(self.selected_square)
            row = chess.square_rank(self.selected_square)
            pygame.draw.rect(self.screen, (255, 255, 0), (col * self.square_size, (7 - row) * self.square_size, self.square_size, self.square_size), 3)

        # Highlight legal moves
        for move in self.legal_moves:
            col = chess.square_file(move.to_square)
            row = chess.square_rank(move.to_square)
            pygame.draw.circle(self.screen, (0, 255, 0), ((col * self.square_size) + self.square_size // 2, (7 - row) * self.square_size + self.square_size // 2), 10)

        # Draw pieces
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                col = chess.square_file(square)
                row = chess.square_rank(square)
                image = self.assets.get_piece_image(piece)
                if image:
                    self.screen.blit(image, (col * self.square_size + (self.square_size - image.get_width()) // 2, (7 - row) * self.square_size + (self.square_size - image.get_height()) // 2))

        # Draw chat
        chat_rect = pygame.Rect(0, 600, 800, 200)
        pygame.draw.rect(self.screen, (200, 200, 200), chat_rect)

        # Display up to 5 most recent messages
        visible_messages = [msg for msg in self.chat_messages[-5:] if msg.get('status') != 'expired']
        for i, message in enumerate(visible_messages):
            # Format message with timestamp
            msg_text = message['text']
            timestamp = message.get('timestamp', 0)
            time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')

            # Display message with time
            display_text = f"[{time_str}] {msg_text}"
            print(f"Displaying message: {display_text}, status: {message.get('status')}")  # Debug print

            # Use different color for pending messages
            text_color = (100, 100, 100) if message.get('status') == 'pending' else (0, 0, 0)
            text = self.font.render(display_text, True, text_color)
            self.screen.blit(text, (10, 610 + i * 30))

        if self.input_active:
            input_text = self.font.render(self.chat_input, True, (0, 0, 0))
            pygame.draw.rect(self.screen, (255, 255, 255), (10, 760, 780, 30))
            self.screen.blit(input_text, (10, 760))

    def update_board(self, fen):
        self.board.set_fen(fen)
        self.selected_square = None
        self.legal_moves = []

    def add_pending_message(self, message_text, timestamp):
        """Add a message with pending status to the chat"""
        self.chat_messages.append({
            'text': message_text,
            'timestamp': timestamp,
            'sender': 'self',
            'status': 'pending'
        })

    def display_chat(self, message, timestamp=None):
        """Display a received chat message"""
        # If this is a system message (like game over)
        if not timestamp:
            timestamp = time.time()
            self.chat_messages.append({
                'text': message,
                'timestamp': timestamp,
                'sender': 'system',
                'status': 'confirmed'
            })
            return

        # Mark any pending messages as confirmed if we received a reply
        self.confirm_pending_messages()

        # Add the received message
        self.chat_messages.append({
            'text': message,
            'timestamp': timestamp,
            'sender': 'other',
            'status': 'confirmed'
        })

    def confirm_pending_messages(self):
        """Mark all pending messages as confirmed when a reply is received"""
        for message in self.chat_messages:
            if message.get('status') == 'pending':
                message['status'] = 'confirmed'

    def check_expired_messages(self):
        """Check for messages that should expire (pending for more than 1 minute)"""
        current_time = time.time()
        for message in self.chat_messages:
            if (message.get('status') == 'pending' and
                current_time - message.get('timestamp', 0) > 60):  # 60 seconds = 1 minute
                message['status'] = 'expired'
                print(f"Message expired: {message['text']}")  # Debug print

    def show_game_over(self, winner):
        print(f"Game Over! Winner: {winner}")
        self.display_chat(f"Game Over! Winner: {winner}")

    def shutdown(self):
        pygame.quit()


