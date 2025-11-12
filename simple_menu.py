import pygame
import sys
import subprocess
import time
import socket

# Constants
INITIAL_WIDTH = 1100
INITIAL_HEIGHT = 700
BUTTON_WIDTH = 450
BUTTON_HEIGHT = 120
BUTTON_MARGIN = 60
TITLE_FONT_SIZE = 90
BUTTON_FONT_SIZE = 45
MIN_WINDOW_WIDTH = 800   # Minimum window width to prevent layout issues
MIN_WINDOW_HEIGHT = 600  # Minimum window height to prevent cropping

# Colors
WHITE = (255, 255, 255)
LIGHT_PURPLE = (200, 180, 230)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

class Button:
    def __init__(self, rect, text, action=None, color=LIGHT_PURPLE, hover_color=None, text_color=GOLD):
        self.rect = rect
        self.text = text
        self.action = action
        self.color = color
        self.hover_color = hover_color if hover_color else tuple(min(c + 30, 255) for c in color)
        self.text_color = text_color
        self.is_hovered = False
        self.font = pygame.font.Font(None, BUTTON_FONT_SIZE)

    def draw(self, surface):
        # Draw button with background and silver border
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=15)
        pygame.draw.rect(surface, SILVER, self.rect, 5, border_radius=15)

        # Draw text
        text_surf = self.font.render(self.text, True, self.text_color)
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
        pygame.draw.rect(surface, WHITE, self.rect, border_radius=10)
        border_color = LIGHT_PURPLE if self.active else BLACK
        pygame.draw.rect(surface, border_color, self.rect, 3, border_radius=10)

        if self.text:
            text_surf = self.font.render(self.text, True, BLACK)
        else:
            text_surf = self.font.render(self.placeholder, True, BLACK)

        text_rect = text_surf.get_rect(midleft=(self.rect.left + 15, self.rect.centery))
        surface.blit(text_surf, text_rect)

        if self.active and pygame.time.get_ticks() % 1000 < 500:
            if self.text:
                cursor_pos = self.font.size(self.text)[0]
                pygame.draw.line(surface, BLACK,
                                (self.rect.left + 15 + cursor_pos, self.rect.top + 15),
                                (self.rect.left + 15 + cursor_pos, self.rect.bottom - 15), 2)
            else:
                pygame.draw.line(surface, BLACK,
                                (self.rect.left + 15, self.rect.top + 15),
                                (self.rect.left + 15, self.rect.bottom - 15), 2)

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

class SimpleMenu:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Chess Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.server_process = None
        self.update_layout(INITIAL_WIDTH, INITIAL_HEIGHT)

    def update_layout(self, width, height):
        # Enforce minimum window dimensions
        if width < MIN_WINDOW_WIDTH or height < MIN_WINDOW_HEIGHT:
            width = max(width, MIN_WINDOW_WIDTH)
            height = max(height, MIN_WINDOW_HEIGHT)
            pygame.display.set_mode((width, height), pygame.RESIZABLE)
            
        # Use a fixed scale factor to prevent layout issues on small screens
        scale_factor = min(width / INITIAL_WIDTH, height / INITIAL_HEIGHT)
        
        # Ensure minimum sizes for UI elements regardless of scale
        scaled_button_width = max(200, int(BUTTON_WIDTH * scale_factor))
        scaled_button_height = max(80, int(BUTTON_HEIGHT * scale_factor))
        scaled_margin = max(30, int(BUTTON_MARGIN * scale_factor))
        scaled_title_font_size = max(40, int(TITLE_FONT_SIZE * scale_factor))
        
        # Update font sizes with minimum thresholds
        self.title_font = pygame.font.Font(None, scaled_title_font_size)
        
        # Fixed spacing values to ensure consistent layout
        center_x = width // 2
        title_position = height * 0.12  # Title position is 12% from the top
        
        # Fixed positioning for a more predictable layout
        # The first button starts at 30% of screen height
        button_start_y = height * 0.3
        
        # Create buttons with fixed spacing - now with 3 buttons plus exit
        self.buttons = [
            Button(pygame.Rect(center_x - scaled_button_width // 2, button_start_y,
                   scaled_button_width, scaled_button_height), "Create Game", self.create_game),
            Button(pygame.Rect(center_x - scaled_button_width // 2, button_start_y + scaled_button_height + scaled_margin,
                   scaled_button_width, scaled_button_height), "Join Game", self.join_game),
            Button(pygame.Rect(center_x - scaled_button_width // 2, button_start_y + 2 * (scaled_button_height + scaled_margin),
                   scaled_button_width, scaled_button_height), "Spectate Game", self.spectate_game),
            Button(pygame.Rect(center_x - scaled_button_width // 4, button_start_y + 3 * (scaled_button_height + scaled_margin),
                   scaled_button_width // 2, scaled_button_height // 1.5), "Exit", self.exit_game, 
                   color=(200, 100, 100), hover_color=(250, 120, 120))
        ]

    def run(self):
        self.start_server()

        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            current_width, current_height = self.screen.get_size()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.stop_server()
                elif event.type == pygame.VIDEORESIZE:
                    # Apply minimum dimensions
                    new_width = max(event.w, MIN_WINDOW_WIDTH)
                    new_height = max(event.h, MIN_WINDOW_HEIGHT)
                    self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                    self.update_layout(new_width, new_height)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in self.buttons:
                        result = button.handle_event(event)
                        if result is not None:
                            return result

            for button in self.buttons:
                button.update(mouse_pos)

            # Draw white background
            self.screen.fill(WHITE)

            # Draw title with fixed positioning
            title_surf = self.title_font.render("Chess Game", True, GOLD)
            # Always place title at exactly 12% of screen height from top
            title_pos_y = int(current_height * 0.12)
            title_rect = title_surf.get_rect(center=(current_width // 2, title_pos_y))
            self.screen.blit(title_surf, title_rect)
            # Add border around title
            pygame.draw.rect(self.screen, SILVER, title_rect.inflate(20, 10), 5, border_radius=10)

            # Draw buttons
            for button in self.buttons:
                button.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        return None

    def start_server(self):
        if self.server_process and self.server_process.poll() is None:
            print("Server is already running")
            return

        print("Starting server...")
        try:
            self.server_process = subprocess.Popen([sys.executable, "simple_server.py"],
                                                  creationflags=subprocess.CREATE_NEW_CONSOLE)

            time.sleep(3.0)

            if self.server_process.poll() is not None:
                print("Server process exited immediately. Check for errors.")
            else:
                print("Server started successfully")

            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(2.0)
                test_socket.connect(("localhost", 50004))
                test_socket.close()
                print("Server connection verified")
            except:
                print("Warning: Could not verify server connection")
        except Exception as e:
            print(f"Error starting server: {e}")

    def create_game(self):
        try:
            subprocess.Popen([sys.executable, "simple_client.py", "create"],
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            return None
        except Exception as e:
            print(f"Error starting client: {e}")
            return None

    def join_game(self):
        try:
            subprocess.Popen([sys.executable, "simple_client.py", "join"],
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            return None
        except Exception as e:
            print(f"Error starting client: {e}")
            return None
            
    def spectate_game(self):
        try:
            subprocess.Popen([sys.executable, "simple_client.py", "spectate"],
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            return None
        except Exception as e:
            print(f"Error starting client in spectate mode: {e}")
            return None
    
    def exit_game(self):
        self.running = False
        self.stop_server()
        pygame.quit()
        sys.exit()

    def stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            print("Stopping server...")
            self.server_process.terminate()

class InputScreen:
    def __init__(self, screen, title, fields):
        self.screen = screen
        self.title = title
        self.fields = fields
        self.width, self.height = screen.get_size()
        self.title_font = pygame.font.Font(None, 48)
        self.label_font = pygame.font.Font(None, 36)

        button_width = 200
        button_height = 50
        self.continue_button = Button(
            pygame.Rect(self.width // 2 - button_width // 2, self.height - 150,
                       button_width, button_height),
            "Continue",
            None
        )
        
        # Add exit button
        self.exit_button = Button(
            pygame.Rect(self.width - 120, self.height - 60, 100, 40),
            "Exit",
            None,
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )

        self.status_message = ""
        self.status_color = BLACK

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            mouse_pos = pygame.mouse.get_pos()
            current_width, current_height = self.screen.get_size()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    # Enforce minimum dimensions
                    new_width = max(event.w, MIN_WINDOW_WIDTH)
                    new_height = max(event.h, MIN_WINDOW_HEIGHT)
                    self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                    self.width, self.height = self.screen.get_size()
                    self.continue_button.rect = pygame.Rect(self.width // 2 - 100, self.height - 150, 200, 50)
                    self.exit_button.rect = pygame.Rect(self.width - 120, self.height - 60, 100, 40)

                for label, field in self.fields:
                    if field.handle_event(event):
                        self.check_continue()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.continue_button.is_hovered:
                        result = self.check_continue()
                        if result:
                            return result
                    elif self.exit_button.is_hovered:
                        return None

            self.continue_button.update(mouse_pos)
            self.exit_button.update(mouse_pos)

            self.screen.fill(WHITE)

            # Position title with fixed positioning
            title_pos_y = int(current_height * 0.12)  # Always 12% from top
            title_surf = self.title_font.render(self.title, True, GOLD)
            title_rect = title_surf.get_rect(center=(current_width // 2, title_pos_y))
            self.screen.blit(title_surf, title_rect)

            for i, (label, field) in enumerate(self.fields):
                label_surf = self.label_font.render(label, True, BLACK)
                self.screen.blit(label_surf, (field.rect.left, field.rect.top - 50))
                field.draw(self.screen)

            self.continue_button.draw(self.screen)
            self.exit_button.draw(self.screen)

            if self.status_message:
                status_surf = self.label_font.render(self.status_message, True, self.status_color)
                status_rect = status_surf.get_rect(center=(self.width // 2, self.height - 200))
                self.screen.blit(status_surf, status_rect)

            pygame.display.flip()
            clock.tick(60)

        return None

    def check_continue(self):
        for label, field in self.fields:
            if not field.text:
                self.status_message = f"Please enter {label}"
                self.status_color = RED
                return None

        return {label: field.text for label, field in self.fields}

if __name__ == "__main__":
    menu = SimpleMenu()
    menu.run()
