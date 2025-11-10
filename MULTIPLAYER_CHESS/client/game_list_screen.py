import pygame
import sys
import socket
import json
import time
from pygame.locals import *

class GameListScreen:
    def __init__(self, screen, width=800, height=600):
        self.screen = screen
        self.width = width
        self.height = height
        self.font_large = pygame.font.Font(None, 90)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.LIGHT_PURPLE = (200, 180, 230)
        self.GOLD = (255, 215, 0)
        self.SILVER = (192, 192, 192)
        self.RED = (255, 0, 0)
        self.GREEN = (100, 200, 100)
        self.BLUE = (100, 100, 200)
        
        # Game list
        self.games = []
        self.selected_game = None
        self.scroll_offset = 0
        self.max_visible_games = 8
        
        # Buttons
        self.refresh_button = Button(
            pygame.Rect(0, 0, 150, 40),
            "Refresh",
            color=(100, 150, 200),
            hover_color=(150, 200, 250)
        )
        
        self.spectate_button = Button(
            pygame.Rect(0, 0, 200, 50),
            "Spectate Game",
            color=(150, 100, 200),
            hover_color=(200, 150, 255)
        )
        
        self.back_button = Button(
            pygame.Rect(0, 0, 150, 40),
            "Back",
            color=(200, 100, 100),
            hover_color=(250, 150, 150)
        )
        
        # Exit button
        self.exit_button = Button(
            pygame.Rect(0, 0, 100, 40),
            "Exit",
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )
        
        # Input fields for manual game ID entry
        self.name_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your name")
        self.id_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your ID")
        self.game_field = InputField(pygame.Rect(0, 0, 300, 50), "Or enter game ID manually")
        
        self.status_message = ""
        self.status_color = self.BLACK
        
        # Socket for server communication
        self.socket = None
        self.connected = False

    def connect_to_server(self):
        """Connect to the chess server"""
        if self.connected:
            return True
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect(("localhost", 50004))
            self.socket.settimeout(None)
            self.connected = True
            print("Connected to server")
            return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.status_message = f"Connection error: {e}"
            self.status_color = self.RED
            return False

    def send_message(self, message):
        """Send a message to the server"""
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
        """Receive a message from the server"""
        if not self.connected:
            return None
        try:
            self.socket.settimeout(5.0)  # Set timeout for receiving
            data = self.socket.recv(1024).decode('utf-8')
            self.socket.settimeout(None)  # Reset timeout
            if not data:
                print("Server closed connection")
                self.connected = False
                return None
            return json.loads(data)
        except socket.timeout:
            print("Timeout waiting for server response")
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            self.connected = False
            return None

    def fetch_games(self):
        """Fetch the list of active games from the server"""
        self.status_message = "Connecting to server..."
        self.status_color = self.BLACK
        self.draw()
        pygame.display.flip()
        
        if not self.connect_to_server():
            return False
            
        self.status_message = "Fetching games..."
        self.status_color = self.BLACK
        self.draw()
        pygame.display.flip()
        
        if not self.send_message({"type": "GET_GAMES"}):
            self.status_message = "Failed to request games"
            self.status_color = self.RED
            return False
            
        response = self.receive_message()
        if not response or response.get("type") != "GAME_LIST":
            self.status_message = "Failed to get game list"
            self.status_color = self.RED
            return False
            
        self.games = response.get("games", [])
        if not self.games:
            self.status_message = "No active games found"
            self.status_color = self.BLUE
        else:
            self.status_message = f"Found {len(self.games)} active games"
            self.status_color = self.GREEN
            
        return True

    def run(self):
        # Fetch games when the screen is first shown
        self.fetch_games()
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), RESIZABLE)
                
                # Handle input field events
                self.name_field.handle_event(event)
                self.id_field.handle_event(event)
                self.game_field.handle_event(event)
                
                # Handle mouse events
                if event.type == MOUSEBUTTONDOWN:
                    # Check if a game in the list was clicked
                    if event.button == 1:  # Left click
                        game_list_rect = pygame.Rect(self.width // 2 - 300, 200, 600, 40 * self.max_visible_games)
                        if game_list_rect.collidepoint(event.pos):
                            # Calculate which game was clicked
                            y_offset = event.pos[1] - game_list_rect.top
                            index = self.scroll_offset + y_offset // 40
                            if 0 <= index < len(self.games):
                                self.selected_game = self.games[index]["game_id"]
                    
                    # Check if refresh button was clicked
                    if self.refresh_button.is_hovered:
                        self.fetch_games()
                        self.selected_game = None
                    
                    # Check if spectate button was clicked
                    if self.spectate_button.is_hovered:
                        if self.selected_game or self.game_field.text:
                            game_id = self.selected_game if self.selected_game else self.game_field.text
                            if self.name_field.text and self.id_field.text:
                                return {
                                    "name": self.name_field.text,
                                    "id": self.id_field.text,
                                    "game_id": game_id
                                }
                            else:
                                self.status_message = "Please enter your name and ID"
                                self.status_color = self.RED
                        else:
                            self.status_message = "Please select a game or enter a game ID"
                            self.status_color = self.RED
                    
                    # Check if back button was clicked
                    if self.back_button.is_hovered:
                        return None
                        
                    # Check if exit button was clicked
                    if self.exit_button.is_hovered:
                        pygame.quit()
                        sys.exit()
                
                # Handle mouse wheel for scrolling
                if event.type == MOUSEWHEEL:
                    self.scroll_offset = max(0, min(len(self.games) - self.max_visible_games, 
                                                  self.scroll_offset - event.y))
            
            # Update button hover states
            mouse_pos = pygame.mouse.get_pos()
            self.refresh_button.update(mouse_pos)
            self.spectate_button.update(mouse_pos)
            self.back_button.update(mouse_pos)
            self.exit_button.update(mouse_pos)
            
            # Draw UI
            self.draw()
            pygame.display.flip()
        
        return None

    def draw(self):
        self.screen.fill(self.WHITE)
        
        # Title
        title_text = "Available Games"
        title_surf = self.font_large.render(title_text, True, self.GOLD)
        title_rect = title_surf.get_rect(center=(self.width // 2, 80))
        pygame.draw.rect(self.screen, self.SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
        self.screen.blit(title_surf, title_rect)
        
        # Position buttons
        self.refresh_button.rect.topleft = (self.width // 2 + 320, 200)
        self.back_button.rect.topleft = (50, self.height - 60)
        self.spectate_button.rect.topleft = (self.width // 2 - 100, self.height - 70)
        self.exit_button.rect.topleft = (self.width - 120, self.height - 60)
        
        # Position input fields
        self.name_field.rect.topleft = (50, self.height - 200)
        self.id_field.rect.topleft = (50, self.height - 130)
        self.game_field.rect.topleft = (self.width - 350, self.height - 130)
        
        # Draw game list
        list_rect = pygame.Rect(self.width // 2 - 300, 200, 600, 40 * self.max_visible_games)
        pygame.draw.rect(self.screen, (240, 240, 240), list_rect)
        pygame.draw.rect(self.screen, self.SILVER, list_rect, 2)
        
        # Draw column headers
        header_y = list_rect.top - 30
        pygame.draw.line(self.screen, self.BLACK, (list_rect.left, header_y + 25), 
                        (list_rect.right, header_y + 25), 2)
        
        id_header = self.font_small.render("Game ID", True, self.BLACK)
        self.screen.blit(id_header, (list_rect.left + 10, header_y))
        
        status_header = self.font_small.render("Status", True, self.BLACK)
        self.screen.blit(status_header, (list_rect.left + 150, header_y))
        
        players_header = self.font_small.render("Players", True, self.BLACK)
        self.screen.blit(players_header, (list_rect.left + 250, header_y))
        
        spectators_header = self.font_small.render("Spectators", True, self.BLACK)
        self.screen.blit(spectators_header, (list_rect.left + 450, header_y))
        
        # Draw games
        if not self.games:
            no_games_text = self.font_medium.render("No games available", True, self.BLUE)
            self.screen.blit(no_games_text, (list_rect.centerx - no_games_text.get_width() // 2, 
                                           list_rect.centery - no_games_text.get_height() // 2))
        else:
            visible_games = self.games[self.scroll_offset:self.scroll_offset + self.max_visible_games]
            for i, game in enumerate(visible_games):
                game_rect = pygame.Rect(list_rect.left, list_rect.top + i * 40, list_rect.width, 40)
                
                # Highlight selected game
                if game["game_id"] == self.selected_game:
                    pygame.draw.rect(self.screen, (220, 220, 255), game_rect)
                
                # Draw game ID
                game_id_text = self.font_small.render(game["game_id"], True, self.BLACK)
                self.screen.blit(game_id_text, (game_rect.left + 10, game_rect.top + 10))
                
                # Draw status
                status_color = self.GREEN if game["status"] == "playing" else self.BLUE
                status_text = self.font_small.render(game["status"].capitalize(), True, status_color)
                self.screen.blit(status_text, (game_rect.left + 150, game_rect.top + 10))
                
                # Draw players
                players_text = ""
                if "players" in game:
                    if "white" in game["players"] and game["players"]["white"]:
                        players_text += f"W: {game['players']['white']}"
                    if "black" in game["players"] and game["players"]["black"]:
                        if players_text:
                            players_text += " vs "
                        players_text += f"B: {game['players']['black']}"
                
                if not players_text:
                    players_text = "Unknown"
                
                players_surf = self.font_small.render(players_text, True, self.BLACK)
                self.screen.blit(players_surf, (game_rect.left + 250, game_rect.top + 10))
                
                # Draw spectator count
                spectator_count = game.get("spectator_count", 0)
                spectator_text = self.font_small.render(str(spectator_count), True, self.BLACK)
                self.screen.blit(spectator_text, (game_rect.left + 450, game_rect.top + 10))
                
                # Draw separator line
                pygame.draw.line(self.screen, (200, 200, 200), 
                               (game_rect.left, game_rect.bottom), 
                               (game_rect.right, game_rect.bottom), 1)
        
        # Draw scroll indicators if needed
        if len(self.games) > self.max_visible_games:
            if self.scroll_offset > 0:
                pygame.draw.polygon(self.screen, self.BLACK, 
                                  [(list_rect.right + 20, list_rect.top + 10),
                                   (list_rect.right + 30, list_rect.top + 20),
                                   (list_rect.right + 10, list_rect.top + 20)])
            
            if self.scroll_offset < len(self.games) - self.max_visible_games:
                pygame.draw.polygon(self.screen, self.BLACK, 
                                  [(list_rect.right + 20, list_rect.bottom - 10),
                                   (list_rect.right + 30, list_rect.bottom - 20),
                                   (list_rect.right + 10, list_rect.bottom - 20)])
        
        # Draw input fields and labels
        name_label = self.font_medium.render("Your Name:", True, self.BLACK)
        self.screen.blit(name_label, (50, self.height - 230))
        self.name_field.draw(self.screen)
        
        id_label = self.font_medium.render("Your ID:", True, self.BLACK)
        self.screen.blit(id_label, (50, self.height - 160))
        self.id_field.draw(self.screen)
        
        game_label = self.font_medium.render("Manual Game ID:", True, self.BLACK)
        self.screen.blit(game_label, (self.width - 350, self.height - 160))
        self.game_field.draw(self.screen)
        
        # Draw buttons
        self.refresh_button.draw(self.screen)
        self.spectate_button.draw(self.screen)
        self.back_button.draw(self.screen)
        self.exit_button.draw(self.screen)
        
        # Draw status message
        if self.status_message:
            status = self.font_medium.render(self.status_message, True, self.status_color)
            self.screen.blit(status, (self.width // 2 - status.get_width() // 2, 150))

class Button:
    def __init__(self, rect, text, action=None, color=(150, 100, 200), hover_color=(200, 150, 255)):
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