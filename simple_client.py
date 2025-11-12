import pygame
import sys
import socket
import json
import threading
import chess
import time
import os
import datetime
from MULTIPLAYER_CHESS.client.game_list_screen import GameListScreen

# Constants
HOST = "localhost"
PORT = 50004
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700
BOARD_SIZE = 560
SQUARE_SIZE = BOARD_SIZE // 8

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (255, 255, 0)
MOVE_HINT = (0, 255, 0, 128)
BLUE = (0, 120, 255)
LIGHT_BLUE = (100, 180, 255)
RED = (255, 100, 100)
GREEN = (100, 255, 100)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)

class Button:
    def __init__(self, rect, text, action=None, color=BLUE, hover_color=LIGHT_BLUE):
        self.rect = rect
        self.text = text
        self.action = action
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.font = pygame.font.Font(None, 36)

    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=15)
        pygame.draw.rect(surface, (255, 255, 0), self.rect, 3, border_radius=15)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            if self.action:
                return self.action()
        return None

class InputField:
    def __init__(self, rect, placeholder="", max_length=20):
        self.rect = rect
        self.text = ""
        self.placeholder = placeholder
        self.max_length = max_length
        self.active = False
        self.font = pygame.font.Font(None, 36)

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 180, 255), self.rect, border_radius=10)
        border_color = (255, 255, 0) if self.active else (150, 100, 200)
        pygame.draw.rect(surface, border_color, self.rect, 3, border_radius=10)
        if self.text:
            text_surf = self.font.render(self.text, True, (0, 0, 0))
        else:
            text_surf = self.font.render(self.placeholder, True, (180, 180, 180))
        text_rect = text_surf.get_rect(midleft=(self.rect.left + 10, self.rect.centery))
        surface.blit(text_surf, text_rect)
        if self.active and pygame.time.get_ticks() % 1000 < 500:
            cursor_pos = self.font.size(self.text)[0]
            pygame.draw.line(surface, (0, 0, 0), (self.rect.left + 10 + cursor_pos, self.rect.top + 10), (self.rect.left + 10 + cursor_pos, self.rect.bottom - 10), 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return True
            elif len(self.text) < self.max_length:
                self.text += event.unicode
        return False

class ChessClient:
    def __init__(self, mode):
        self.mode = mode
        self.socket = None
        self.connected = False
        self.running = True
        self.player_name = None
        self.player_id = None
        self.game_id = None
        self.color = None
        self.opponent = None
        self.board = chess.Board()
        self.current_player = "white"
        self.selected_square = None
        self.legal_moves = []
        self.game_over = False
        self.winner = None
        self.status_message = ""
        self.piece_images = {}
        self.chat_messages = []  # Will store dicts with text, timestamp, sender, status
        self.chat_input = ""
        self.chat_input_active = False
        self.is_spectator = mode == "spectate"
        self.spectator_count = 0
        self.last_message_check = time.time()  # For checking expired messages

        # Time control
        self.white_time = 300  # 5 minutes in seconds
        self.black_time = 300
        self.time_limit = 300
        self.last_time_update = time.time()

        # Initialize pygame with minimum size constraint
        pygame.init()
        self.min_width = 700
        self.min_height = 600
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Chess Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

        # Exit button
        self.exit_button = Button(
            pygame.Rect(WINDOW_WIDTH - 120, 20, 100, 40),
            "Exit",
            self.exit_game,
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )

        # Load chess piece images
        self.load_piece_images()

    def exit_game(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        pygame.quit()
        sys.exit()

    def load_piece_images(self):
        # Create a pieces directory if it doesn't exist
        if not os.path.exists("pieces"):
            os.makedirs("pieces")

        # Define piece symbols and their corresponding file names
        piece_symbols = {
            'p': 'black_pawn.png',
            'r': 'black_rook.png',
            'n': 'black_knight.png',
            'b': 'black_bishop.png',
            'q': 'black_queen.png',
            'k': 'black_king.png',
            'P': 'white_pawn.png',
            'R': 'white_rook.png',
            'N': 'white_knight.png',
            'B': 'white_bishop.png',
            'Q': 'white_queen.png',
            'K': 'white_king.png'
        }

        # Check if we have the piece images in the MULTIPLAYER_CHESS/client/assets directory
        assets_dir = "MULTIPLAYER_CHESS/client/assets"

        for symbol, filename in piece_symbols.items():
            # Try to load from assets directory first
            asset_path = f"{assets_dir}/{filename.lower()}"
            pieces_path = f"pieces/{symbol}.png"

            try:
                if os.path.exists(asset_path):
                    # Load from assets directory
                    image = pygame.image.load(asset_path)
                    image = pygame.transform.scale(image, (SQUARE_SIZE - 10, SQUARE_SIZE - 10))
                    self.piece_images[symbol] = image
                else:
                    # Create a fallback image
                    image = self.create_piece_image(symbol)
                    image = pygame.transform.scale(image, (SQUARE_SIZE - 10, SQUARE_SIZE - 10))
                    self.piece_images[symbol] = image
                    # Save the fallback image for future use
                    pygame.image.save(image, pieces_path)
            except Exception as e:
                print(f"Error loading piece image for {symbol}: {e}")
                image = self.create_piece_image(symbol)
                image = pygame.transform.scale(image, (SQUARE_SIZE - 10, SQUARE_SIZE - 10))
                self.piece_images[symbol] = image

    def create_piece_image(self, piece):
        is_white = piece.isupper()
        color = WHITE if is_white else BLACK
        bg_color = BLACK if is_white else WHITE
        surface = pygame.Surface((SQUARE_SIZE - 10, SQUARE_SIZE - 10))
        surface.fill(bg_color)
        pygame.draw.circle(surface, color, (SQUARE_SIZE // 2 - 5, SQUARE_SIZE // 2 - 5), SQUARE_SIZE // 2 - 10)
        font = pygame.font.Font(None, 36)
        text = font.render(piece.upper(), True, bg_color)
        text_rect = text.get_rect(center=(SQUARE_SIZE // 2 - 5, SQUARE_SIZE // 2 - 5))
        surface.blit(text, text_rect)
        return surface

    def connect_to_server(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"Connection attempt {attempt+1}/{max_attempts}...")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)
                self.socket.connect((HOST, PORT))
                self.socket.settimeout(None)
                self.connected = True
                print("Connected to server")
                return True
            except Exception as e:
                print(f"Error connecting to server (attempt {attempt+1}): {e}")
                if attempt < max_attempts - 1:
                    print("Retrying in 2 seconds...")
                    time.sleep(2.0)
                else:
                    self.status_message = f"Connection error: {e}"
                    return False
        return False

    def send_message(self, message):
        if not self.connected:
            print("Not connected to server")
            return False
        try:
            data = json.dumps(message).encode('utf-8')
            self.socket.send(data)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False

    def receive_message(self):
        if not self.connected:
            return None
        try:
            data = self.socket.recv(1024).decode('utf-8')
            if not data:
                print("Server closed connection")
                self.connected = False
                return None
            return json.loads(data)
        except Exception as e:
            print(f"Error receiving message: {e}")
            self.connected = False
            return None

    def create_game(self, player_name, player_id):
        self.player_name = player_name
        self.player_id = player_id
        self.status_message = "Connecting to server..."
        self.draw_game()
        pygame.display.flip()
        if not self.connect_to_server():
            self.status_message = "Failed to connect to server. Is the server running?"
            return False
        self.status_message = "Creating game..."
        self.draw_game()
        pygame.display.flip()
        message = {
            "type": "CREATE_GAME",
            "player_name": player_name,
            "player_id": player_id,
            "time_limit": self.time_limit
        }
        if not self.send_message(message):
            self.status_message = "Failed to send game creation request."
            return False
        self.status_message = "Waiting for server response..."
        self.draw_game()
        pygame.display.flip()
        start_time = time.time()
        timeout = 10.0
        while time.time() - start_time < timeout:
            response = self.receive_message()
            if response:
                if response.get("type") == "GAME_CREATED":
                    self.game_id = response.get("game_id")
                    self.color = response.get("color")
                    self.time_limit = response.get("time_limit", 300)
                    self.white_time = self.time_limit
                    self.black_time = self.time_limit
                    self.status_message = f"Game created! ID: {self.game_id}. Waiting for opponent..."
                    print(f"Game created with ID: {self.game_id}")
                    return True
                else:
                    self.status_message = f"Error: {response.get('message', 'Unknown error')}"
                    return False
            time.sleep(0.1)
        self.status_message = "Server response timeout. Try again."
        return False

    def join_game(self, player_name, player_id, game_id):
        self.player_name = player_name
        self.player_id = player_id
        self.game_id = game_id
        self.status_message = "Connecting to server..."
        self.draw_game()
        pygame.display.flip()
        if not self.connect_to_server():
            self.status_message = "Failed to connect to server. Is the server running?"
            return False
        self.status_message = "Joining game..."
        self.draw_game()
        pygame.display.flip()
        message = {"type": "JOIN_GAME", "player_name": player_name, "player_id": player_id, "game_id": game_id}
        if not self.send_message(message):
            self.status_message = "Failed to send join request."
            return False
        self.status_message = "Waiting for server response..."
        self.draw_game()
        pygame.display.flip()
        start_time = time.time()
        timeout = 10.0
        while time.time() - start_time < timeout:
            response = self.receive_message()
            if response:
                if response.get("type") == "GAME_JOINED":
                    self.color = response.get("color")
                    self.opponent = response.get("opponent")
                    self.time_limit = response.get("time_limit", 300)
                    self.white_time = self.time_limit
                    self.black_time = self.time_limit
                    self.status_message = f"Joined game! Opponent: {self.opponent}"
                    print(f"Joined game {game_id} against {self.opponent}")
                    return True
                else:
                    error_msg = response.get('message', 'Unknown error')
                    self.status_message = f"Error: {error_msg}"
                    print(f"Error joining game: {error_msg}")
                    return False
            time.sleep(0.1)
        self.status_message = "Server response timeout. Try again."
        return False

    def spectate_game(self, player_name, player_id, game_id):
        self.player_name = player_name
        self.player_id = player_id
        self.game_id = game_id
        self.status_message = "Connecting to server..."
        self.draw_game()
        pygame.display.flip()
        if not self.connect_to_server():
            self.status_message = "Failed to connect to server. Is the server running?"
            return False
        self.status_message = "Joining game as spectator..."
        self.draw_game()
        pygame.display.flip()
        message = {"type": "SPECTATE", "player_name": player_name, "player_id": player_id, "game_id": game_id}
        if not self.send_message(message):
            self.status_message = "Failed to send spectate request."
            return False
        self.status_message = "Waiting for server response..."
        self.draw_game()
        pygame.display.flip()
        start_time = time.time()
        timeout = 10.0
        while time.time() - start_time < timeout:
            response = self.receive_message()
            if response:
                if response.get("type") == "SPECTATE_START":
                    self.board = chess.Board(response.get("board", chess.STARTING_FEN))
                    self.white_time = response.get("white_time", 300)
                    self.black_time = response.get("black_time", 300)
                    self.current_player = response.get("current_player", "white")
                    self.status_message = f"Spectating game {game_id}"
                    print(f"Spectating game {game_id}")
                    return True
                else:
                    error_msg = response.get('message', 'Unknown error')
                    self.status_message = f"Error: {error_msg}"
                    print(f"Error spectating game: {error_msg}")
                    return False
            time.sleep(0.1)
        self.status_message = "Server response timeout. Try again."
        return False

    def start(self):
        if self.mode == "create":
            self.show_create_screen()
        elif self.mode == "join":
            self.show_join_screen()
        elif self.mode == "spectate":
            self.show_game_list_screen()
        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.run_game()

    def show_create_screen(self):
        name_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your name")
        id_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your ID")
        time_field = InputField(pygame.Rect(0, 0, 300, 50), "Time limit (seconds)")
        time_field.text = "300"  # Default 5 minutes

        button = Button(pygame.Rect(0, 0, 200, 50), "Create Game", color=(150, 100, 200), hover_color=(200, 150, 255))
        exit_button = Button(pygame.Rect(0, 0, 100, 40), "Exit", color=(200, 100, 100), hover_color=(250, 120, 120))

        status_message = ""
        status_color = BLACK
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((max(event.w, self.min_width), max(event.h, self.min_height)), pygame.RESIZABLE)
                name_field.handle_event(event)
                id_field.handle_event(event)
                time_field.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button.is_hovered:
                        if name_field.text and id_field.text:
                            try:
                                time_limit = int(time_field.text)
                                if time_limit < 30:
                                    status_message = "Time limit must be at least 30 seconds"
                                    status_color = RED
                                else:
                                    self.time_limit = time_limit
                                    if self.create_game(name_field.text, id_field.text):
                                        running = False
                                    else:
                                        status_message = "Failed to create game. Check server connection."
                                        status_color = RED
                            except ValueError:
                                status_message = "Time limit must be a number"
                                status_color = RED
                        else:
                            status_message = "Please fill in all fields"
                            status_color = RED
                    elif exit_button.is_hovered:
                        pygame.quit()
                        sys.exit()

            mouse_pos = pygame.mouse.get_pos()
            button.update(mouse_pos)
            exit_button.update(mouse_pos)

            win_w, win_h = self.screen.get_size()
            title_font = pygame.font.Font(None, 90)
            title_text = "Create a New Game"
            title_surf = title_font.render(title_text, True, GOLD)
            title_rect = title_surf.get_rect(center=(win_w // 2, 100))

            # Position input fields
            name_field.rect.topleft = (win_w // 2 - 150, 200)
            id_field.rect.topleft = (win_w // 2 - 150, 280)
            time_field.rect.topleft = (win_w // 2 - 150, 360)
            button.rect.topleft = (win_w // 2 - 100, 440)
            exit_button.rect.topleft = (win_w - 120, 20)

            self.screen.fill((240, 240, 255))
            pygame.draw.rect(self.screen, SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
            self.screen.blit(title_surf, title_rect)

            # Draw labels with proper alignment
            name_label = self.font.render("Your Name:", True, BLACK)
            name_label_rect = name_label.get_rect(midleft=(name_field.rect.left, name_field.rect.top - 20))
            self.screen.blit(name_label, name_label_rect)

            id_label = self.font.render("Your ID:", True, BLACK)
            id_label_rect = id_label.get_rect(midleft=(id_field.rect.left, id_field.rect.top - 20))
            self.screen.blit(id_label, id_label_rect)

            time_label = self.font.render("Time Limit (seconds):", True, BLACK)
            time_label_rect = time_label.get_rect(midleft=(time_field.rect.left, time_field.rect.top - 20))
            self.screen.blit(time_label, time_label_rect)

            name_field.draw(self.screen)
            id_field.draw(self.screen)
            time_field.draw(self.screen)
            button.draw(self.screen)
            exit_button.draw(self.screen)

            if status_message:
                status = self.font.render(status_message, True, status_color)
                self.screen.blit(status, (win_w // 2 - status.get_width() // 2, 500))

            pygame.display.flip()
            self.clock.tick(60)

    def show_join_screen(self):
        name_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your name")
        id_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your ID")
        game_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter game ID")
        button = Button(pygame.Rect(0, 0, 200, 50), "Join Game", color=(150, 100, 200), hover_color=(200, 150, 255))
        exit_button = Button(pygame.Rect(0, 0, 100, 40), "Exit", color=(200, 100, 100), hover_color=(250, 120, 120))

        status_message = ""
        status_color = BLACK
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((max(event.w, self.min_width), max(event.h, self.min_height)), pygame.RESIZABLE)
                name_field.handle_event(event)
                id_field.handle_event(event)
                game_field.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button.is_hovered:
                        if name_field.text and id_field.text and game_field.text:
                            if self.join_game(name_field.text, id_field.text, game_field.text):
                                running = False
                            else:
                                status_message = "Failed to join game. Check game ID and server connection."
                                status_color = RED
                        else:
                            status_message = "Please fill in all fields"
                            status_color = RED
                    elif exit_button.is_hovered:
                        pygame.quit()
                        sys.exit()

            mouse_pos = pygame.mouse.get_pos()
            button.update(mouse_pos)
            exit_button.update(mouse_pos)

            win_w, win_h = self.screen.get_size()
            title_font = pygame.font.Font(None, 90)
            title_text = "Join a Game"
            title_surf = title_font.render(title_text, True, GOLD)
            title_rect = title_surf.get_rect(center=(win_w // 2, 100))

            # Position input fields
            name_field.rect.topleft = (win_w // 2 - 150, 200)
            id_field.rect.topleft = (win_w // 2 - 150, 270)
            game_field.rect.topleft = (win_w // 2 - 150, 340)
            button.rect.topleft = (win_w // 2 - 100, 420)
            exit_button.rect.topleft = (win_w - 120, 20)

            self.screen.fill((240, 240, 255))
            pygame.draw.rect(self.screen, SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
            self.screen.blit(title_surf, title_rect)

            # Position labels 30 pixels above their respective input fields
            name_label = self.font.render("Your Name:", True, BLACK)
            self.screen.blit(name_label, (win_w // 2 - 150, name_field.rect.top - 30))
            id_label = self.font.render("Your ID:", True, BLACK)
            self.screen.blit(id_label, (win_w // 2 - 150, id_field.rect.top - 23))
            game_label = self.font.render("Game ID:", True, BLACK)
            self.screen.blit(game_label, (win_w // 2 - 150, game_field.rect.top - 23))

            name_field.draw(self.screen)
            id_field.draw(self.screen)
            game_field.draw(self.screen)
            button.draw(self.screen)
            exit_button.draw(self.screen)

            if status_message:
                status = self.font.render(status_message, True, status_color)
                self.screen.blit(status, (win_w // 2 - status.get_width() // 2, 500))

            pygame.display.flip()
            self.clock.tick(60)

    def show_game_list_screen(self):
        """Show the game list screen for spectating"""
        game_list_screen = GameListScreen(self.screen, self.screen.get_width(), self.screen.get_height())
        result = game_list_screen.run()

        if result:
            # User selected a game to spectate
            self.player_name = result["name"]
            self.player_id = result["id"]
            self.game_id = result["game_id"]

            # Attempt to spectate the selected game
            if not self.spectate_game(self.player_name, self.player_id, self.game_id):
                # If spectating fails, show the game list screen again
                self.show_game_list_screen()

    def receive_messages(self):
        print("Message receiving thread started")
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.running:
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue

                message = self.receive_message()
                if not message:
                    print("No message received or connection lost")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"Too many consecutive errors ({consecutive_errors}), disconnecting")
                        self.connected = False
                    time.sleep(0.5)  # Wait before retrying
                    continue

                # Reset error counter on successful message
                consecutive_errors = 0

                message_type = message.get("type")
                print(f"Received message: {message_type}")
                if message_type == "WAITING":
                    print("Waiting for opponent...")
                elif message_type == "OPPONENT_JOINED":
                    self.opponent = message.get("opponent")
                    self.status_message = f"Opponent joined: {self.opponent}"
                    print(f"Opponent joined: {self.opponent}")
                elif message_type == "GAME_START":
                    try:
                        board_fen = message.get("board", chess.STARTING_FEN)
                        print(f"Received board FEN: {board_fen}")
                        self.board = chess.Board(board_fen)
                        self.current_player = message.get("current_player", "white")
                        self.white_time = message.get("white_time", 300)
                        self.black_time = message.get("black_time", 300)
                        self.status_message = "Game started!"
                        print("Game started!")
                    except Exception as e:
                        print(f"Error processing GAME_START message: {e}")
                elif message_type == "BOARD_UPDATE":
                    try:
                        board_fen = message.get("board", chess.STARTING_FEN)
                        print(f"Received board update: {board_fen}")
                        self.board = chess.Board(board_fen)
                        self.current_player = message.get("current_player", "white")
                        self.white_time = message.get("white_time", self.white_time)
                        self.black_time = message.get("black_time", self.black_time)
                        self.game_over = message.get("game_over", False)
                        self.winner = message.get("winner")
                        if self.game_over:
                            if self.winner == "draw":
                                self.status_message = "Game over! It's a draw."
                            elif self.winner == self.color:
                                self.status_message = "Game over! You won!"
                            else:
                                self.status_message = "Game over! You lost."
                        else:
                            if self.is_spectator:
                                self.status_message = f"Current turn: {self.current_player}"
                            elif self.current_player == self.color:
                                self.status_message = "Your turn"
                            else:
                                self.status_message = "Opponent's turn"
                    except Exception as e:
                        print(f"Error processing BOARD_UPDATE message: {e}")
                elif message_type == "TIME_UPDATE":
                    self.white_time = message.get("white_time", self.white_time)
                    self.black_time = message.get("black_time", self.black_time)
                    self.current_player = message.get("current_player", self.current_player)
                elif message_type == "GAME_OVER":
                    self.game_over = True
                    self.winner = message.get("winner")
                    reason = message.get("reason", "")
                    if self.winner == "draw":
                        self.status_message = "Game over! It's a draw."
                    elif self.winner == self.color:
                        self.status_message = f"Game over! You won by {reason}!"
                    else:
                        self.status_message = f"Game over! You lost by {reason}."
                elif message_type == "CHAT":
                    player_name = message.get('player_name', 'Unknown')
                    chat_text = message.get('message', '')
                    timestamp = message.get('timestamp', time.time())

                    if player_name and chat_text:
                        # Mark any pending messages as confirmed when we receive a reply
                        for msg in self.chat_messages:
                            if isinstance(msg, dict) and msg.get('status') == 'pending':
                                msg['status'] = 'confirmed'
                                print(f"Message confirmed: {msg['text']}")

                        # Add the received message with timestamp
                        self.chat_messages.append({
                            'text': f"{player_name}: {chat_text}",
                            'timestamp': timestamp,
                            'sender': 'other',
                            'status': 'confirmed'
                        })
                        print(f"Received chat: {player_name}: {chat_text} at {timestamp}")
                elif message_type == "SPECTATOR_JOINED":
                    spectator_name = message.get('spectator_name', 'Unknown')
                    self.spectator_count = message.get('spectator_count', 0)
                    self.chat_messages.append(f"System: {spectator_name} is now spectating")
                    print(f"Spectator joined: {spectator_name}")
                elif message_type == "SPECTATOR_LEFT":
                    spectator_name = message.get('spectator_name', 'Unknown')
                    self.spectator_count = message.get('spectator_count', 0)
                    self.chat_messages.append(f"System: {spectator_name} has left")
                    print(f"Spectator left: {spectator_name}")
                elif message_type == "ERROR":
                    error_msg = message.get('message', 'Unknown error')
                    self.status_message = f"Error: {error_msg}"
                    print(f"Error from server: {error_msg}")
                pygame.event.post(pygame.event.Event(pygame.USEREVENT))
            except Exception as e:
                print(f"Error in receive_messages: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"Too many consecutive errors ({consecutive_errors}), disconnecting")
                    self.connected = False
                time.sleep(0.5)  # Wait before retrying

    def run_game(self):
        running = True
        chat_input = ""
        chat_input_active = False
        while running:
            mouse_pos = pygame.mouse.get_pos()

            # Check for expired messages (older than 1 minute without reply)
            current_time = time.time()
            if current_time - self.last_message_check > 1.0:  # Check every second
                self.check_expired_messages()
                self.last_message_check = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((max(event.w, self.min_width), max(event.h, self.min_height)), pygame.RESIZABLE)
                    # Update exit button position
                    win_w = self.screen.get_size()[0]
                    self.exit_button.rect.topleft = (win_w - 120, 20)
                elif event.type == pygame.USEREVENT:
                    pass
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.exit_button.is_hovered:
                        self.exit_game()
                    elif hasattr(self, 'chat_input_rect') and self.chat_input_rect.collidepoint(event.pos):
                        chat_input_active = True
                    elif hasattr(self, 'send_button_rect') and self.send_button_rect.collidepoint(event.pos):
                        if chat_input.strip():
                            self.send_chat_message(chat_input.strip())
                            chat_input = ""
                    else:
                        chat_input_active = False
                        if not self.game_over and not self.is_spectator:
                            self.handle_mouse_click(event.pos)
                if event.type == pygame.KEYDOWN and chat_input_active:
                    if event.key == pygame.K_BACKSPACE:
                        chat_input = chat_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        if chat_input.strip():
                            self.send_chat_message(chat_input.strip())
                            chat_input = ""
                    elif len(chat_input) < 50:
                        chat_input += event.unicode

            # Update exit button hover state
            self.exit_button.update(mouse_pos)

            self.chat_input = chat_input
            self.chat_input_active = chat_input_active
            self.draw_game()
            pygame.display.flip()
            self.clock.tick(60)
        print("Game loop ended, cleaning up resources")
        self.running = False
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
                print("Socket closed")
        except Exception as e:
            print(f"Error closing socket: {e}")
        self.connected = False

    def check_expired_messages(self):
        """Check for messages that should expire (pending for more than 1 minute)"""
        current_time = time.time()
        for message in self.chat_messages:
            if isinstance(message, dict) and message.get('status') == 'pending':
                if current_time - message.get('timestamp', 0) > 60:  # 60 seconds = 1 minute
                    message['status'] = 'expired'
                    print(f"Message expired: {message['text']}")

    def send_chat_message(self, message):
        if not message or not self.connected:
            return

        # Create timestamp
        timestamp = time.time()

        # Add to local chat with pending status
        self.chat_messages.append({
            'text': f"{self.player_name}: {message}",
            'timestamp': timestamp,
            'sender': 'self',
            'status': 'pending'
        })

        # Send to server with timestamp
        self.send_message({
            "type": "CHAT",
            "player_name": self.player_name,
            "message": message,
            "timestamp": timestamp
        })

    def handle_mouse_click(self, pos):
        if self.is_spectator:
            return  # Spectators can't make moves

        _, win_h = self.screen.get_size()
        board_size = min(BOARD_SIZE, win_h - 80)
        board_x = 40
        board_y = (win_h - board_size) // 2
        square_size = board_size // 8
        if (pos[0] < board_x or pos[0] >= board_x + board_size or
            pos[1] < board_y or pos[1] >= board_y + board_size):
            return
        col = (pos[0] - board_x) // square_size
        row = 7 - (pos[1] - board_y) // square_size
        square = chess.square(col, row)
        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece:
                piece_color = "white" if piece.color == chess.WHITE else "black"
                if piece_color == self.color:
                    self.selected_square = square
                    self.legal_moves = [move for move in self.board.legal_moves if move.from_square == square]
        else:
            move = None
            for legal_move in self.legal_moves:
                if legal_move.to_square == square:
                    move = legal_move
                    break
            if move:
                self.send_message({"type": "MOVE", "move": move.uci()})
            self.selected_square = None
            self.legal_moves = []

    def format_time(self, seconds):
        """Format time in seconds to MM:SS format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def draw_game(self):
        win_w, win_h = self.screen.get_size()
        self.screen.fill(WHITE)

        board_size = min(BOARD_SIZE, win_h - 80)
        board_x = 40
        board_y = (win_h - board_size) // 2

        panel_x = board_x + board_size + 40
        panel_width = win_w - panel_x - 40
        panel_y = 40
        panel_height = win_h - 80

        if panel_width <= 0 or panel_height <= 0:
            error_text = self.font.render("Window too small! Please resize.", True, RED)
            self.screen.blit(error_text, (10, 10))
            return

        # Draw exit button
        self.exit_button.rect.topleft = (win_w - 120, 20)
        self.exit_button.draw(self.screen)

        # Draw timers
        white_timer = self.format_time(self.white_time)
        black_timer = self.format_time(self.black_time)

        # White timer at the top
        white_timer_text = self.font.render(f"White: {white_timer}", True,
                                          GREEN if self.current_player == "white" else BLACK)
        white_timer_rect = white_timer_text.get_rect(midtop=(board_x + board_size // 2, board_y - 40))
        self.screen.blit(white_timer_text, white_timer_rect)

        # Black timer at the bottom
        black_timer_text = self.font.render(f"Black: {black_timer}", True,
                                          GREEN if self.current_player == "black" else BLACK)
        black_timer_rect = black_timer_text.get_rect(midbottom=(board_x + board_size // 2, board_y + board_size + 40))
        self.screen.blit(black_timer_text, black_timer_rect)

        self.draw_chess_board(board_x, board_y, board_size)

        panel_bg = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_bg.fill((240, 240, 240, 220))
        self.screen.blit(panel_bg, (panel_x, panel_y))

        self.draw_game_info(panel_x, panel_y, panel_width)

        self.draw_chat_area(panel_x, panel_y + 150, panel_width, panel_height - 150)

        if self.status_message:
            self.draw_status_message()

    def draw_chess_board(self, board_x, board_y, board_size):
        square_size = board_size // 8
        for row in range(8):
            for col in range(8):
                color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                pygame.draw.rect(self.screen, color,
                               (board_x + col * square_size,
                                board_y + (7 - row) * square_size,
                                square_size, square_size))
                if col == 0:
                    text = self.small_font.render(str(row + 1), True, BLACK)
                    self.screen.blit(text, (board_x - 20, board_y + (7 - row) * square_size + square_size // 2 - 8))
                if row == 0:
                    text = self.small_font.render(chr(97 + col), True, BLACK)
                    self.screen.blit(text, (board_x + col * square_size + square_size // 2 - 5, board_y + board_size + 10))
        if self.selected_square:
            col = chess.square_file(self.selected_square)
            row = chess.square_rank(self.selected_square)
            pygame.draw.rect(self.screen, HIGHLIGHT,
                           (board_x + col * square_size,
                            board_y + (7 - row) * square_size,
                            square_size, square_size), 3)
        for move in self.legal_moves:
            col = chess.square_file(move.to_square)
            row = chess.square_rank(move.to_square)
            highlight = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
            highlight.fill(MOVE_HINT)
            self.screen.blit(highlight, (board_x + col * square_size, board_y + (7 - row) * square_size))
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                col = chess.square_file(square)
                row = chess.square_rank(square)
                piece_symbol = piece.symbol()
                if piece_symbol in self.piece_images:
                    image = self.piece_images[piece_symbol]
                    self.screen.blit(image,
                                   (board_x + col * square_size + 5,
                                    board_y + (7 - row) * square_size + 5))

    def draw_game_info(self, x, y, width):
        padding = 15
        line_height = 30
        current_y = y + padding
        header = self.font.render("Game Information", True, BLACK)
        self.screen.blit(header, (x + padding, current_y))
        current_y += line_height + 10
        if self.game_id:
            game_id_text = self.small_font.render(f"Game ID: {self.game_id}", True, BLACK)
            self.screen.blit(game_id_text, (x + padding, current_y))
            current_y += line_height
        if self.player_name:
            if self.is_spectator:
                player_text = self.small_font.render(f"Spectating as: {self.player_name}", True, BLACK)
            else:
                player_text = self.small_font.render(f"You: {self.player_name} ({self.color})", True, BLACK)
            self.screen.blit(player_text, (x + padding, current_y))
            current_y += line_height
        if self.opponent:
            opponent_text = self.small_font.render(f"Opponent: {self.opponent}", True, BLACK)
            self.screen.blit(opponent_text, (x + padding, current_y))
            current_y += line_height
        if self.spectator_count > 0:
            spectator_text = self.small_font.render(f"Spectators: {self.spectator_count}", True, BLACK)
            self.screen.blit(spectator_text, (x + padding, current_y))
            current_y += line_height
        if self.game_id and self.color == "white" and not self.opponent:
            pygame.draw.rect(self.screen, (230, 255, 230), (x + padding, current_y, width - padding*2, line_height*1.5), border_radius=5)
            hint_text = self.small_font.render("Share this Game ID with your opponent", True, (0, 100, 0))
            self.screen.blit(hint_text, (x + padding + 10, current_y + 5))

    def draw_chat_area(self, x, y, width, height):
        padding = 15
        header = self.font.render("Chat Messages", True, BLACK)
        self.screen.blit(header, (x + padding, y + padding))
        pygame.draw.line(self.screen, (180, 180, 180), (x + padding, y + padding + 40), (x + width - padding, y + padding + 40), 2)
        chat_history_y = y + padding + 50

        # Filter out expired messages
        visible_messages = []
        for msg in self.chat_messages:
            if isinstance(msg, dict):
                if msg.get('status') != 'expired':
                    visible_messages.append(msg)
            else:
                # Legacy string messages
                visible_messages.append(msg)

        # Display only the most recent messages
        max_messages = 10
        start_idx = max(0, len(visible_messages) - max_messages)
        for i, msg in enumerate(visible_messages[start_idx:]):
            if isinstance(msg, dict):
                # Format message with timestamp
                msg_text = msg['text']
                timestamp = msg.get('timestamp', 0)
                time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                display_text = f"[{time_str}] {msg_text}"

                # Use different color for pending messages
                text_color = (100, 100, 100) if msg.get('status') == 'pending' else BLACK
                msg_text = self.small_font.render(display_text, True, text_color)
            else:
                # Legacy string messages
                msg_text = self.small_font.render(msg, True, BLACK)

            self.screen.blit(msg_text, (x + padding, chat_history_y + i * 22))
        input_box_y = y + height - 70
        input_box_height = 40
        input_box_color = (220, 220, 250) if self.chat_input_active else (200, 200, 200)
        input_box_rect = pygame.Rect(x + padding, input_box_y, width - padding*2 - 70, input_box_height)
        pygame.draw.rect(self.screen, input_box_color, input_box_rect, border_radius=5)
        input_text = self.small_font.render(self.chat_input, True, BLACK)
        self.screen.blit(input_text, (x + padding + 10, input_box_y + 10))
        send_button_rect = pygame.Rect(x + width - padding - 60, input_box_y, 60, input_box_height)
        pygame.draw.rect(self.screen, (100, 150, 255), send_button_rect, border_radius=5)
        send_text = self.small_font.render("Send", True, WHITE)
        text_rect = send_text.get_rect(center=send_button_rect.center)
        self.screen.blit(send_text, text_rect)
        self.chat_input_rect = input_box_rect
        self.send_button_rect = send_button_rect

    def draw_status_message(self):
        if not self.status_message:
            return
        status_text = self.font.render(self.status_message, True, BLACK)
        text_width = status_text.get_width()
        text_height = status_text.get_height()
        status_bg = pygame.Surface((text_width + 20, text_height + 10), pygame.SRCALPHA)
        status_bg.fill((240, 240, 240, 200))
        status_x = self.screen.get_width() // 2 - text_width // 2
        status_y = self.screen.get_height() - 50
        self.screen.blit(status_bg, (status_x - 10, status_y - 5))
        self.screen.blit(status_text, (status_x, status_y))

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ["create", "join", "spectate"]:
        print("Usage: python simple_client.py [create|join|spectate]")
        sys.exit(1)
    mode = sys.argv[1]
    client = ChessClient(mode)
    client.start()
