import pygame
import sys
import random
import string

class PlayerIDScreen:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.LIGHT_PURPLE = (200, 180, 230)
        self.GOLD = (255, 215, 0)
        self.SILVER = (192, 192, 192)
        self.RED = (255, 0, 0)
        
        # Input field
        self.input_field = InputField(
            pygame.Rect(self.width // 2 - 150, self.height // 2 - 25, 300, 50),
            "Enter your player ID"
        )
        
        # Buttons
        self.continue_button = Button(
            pygame.Rect(self.width // 2 - 100, self.height // 2 + 50, 200, 50),
            "Continue",
            color=(150, 100, 200),
            hover_color=(200, 150, 255)
        )
        
        self.random_button = Button(
            pygame.Rect(self.width // 2 - 100, self.height // 2 + 120, 200, 50),
            "Random ID",
            color=(100, 150, 200),
            hover_color=(150, 200, 250)
        )
        
        # Exit button
        self.exit_button = Button(
            pygame.Rect(self.width - 120, 20, 100, 40),
            "Exit",
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )
        
        self.status_message = ""
        self.status_color = self.BLACK

    def generate_random_id(self):
        """Generate a random player ID."""
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for i in range(8))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    # Update positions
                    self.input_field.rect = pygame.Rect(self.width // 2 - 150, self.height // 2 - 25, 300, 50)
                    self.continue_button.rect = pygame.Rect(self.width // 2 - 100, self.height // 2 + 50, 200, 50)
                    self.random_button.rect = pygame.Rect(self.width // 2 - 100, self.height // 2 + 120, 200, 50)
                    self.exit_button.rect = pygame.Rect(self.width - 120, 20, 100, 40)
                
                self.input_field.handle_event(event)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.continue_button.is_hovered:
                        if self.input_field.text:
                            return self.input_field.text
                        else:
                            self.status_message = "Please enter a player ID"
                            self.status_color = self.RED
                    elif self.random_button.is_hovered:
                        self.input_field.text = self.generate_random_id()
                    elif self.exit_button.is_hovered:
                        pygame.quit()
                        sys.exit()
            
            mouse_pos = pygame.mouse.get_pos()
            self.continue_button.update(mouse_pos)
            self.random_button.update(mouse_pos)
            self.exit_button.update(mouse_pos)
            
            # Draw UI
            self.screen.fill(self.WHITE)
            
            # Title
            title_text = "Enter Player ID"
            title_surf = self.font_large.render(title_text, True, self.GOLD)
            title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 4))
            pygame.draw.rect(self.screen, self.SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
            self.screen.blit(title_surf, title_rect)
            
            # Instructions
            instructions = self.font_small.render("This ID will be used to identify you in the game.", True, self.BLACK)
            self.screen.blit(instructions, (self.width // 2 - instructions.get_width() // 2, self.height // 3))
            
            # Draw input field and buttons
            self.input_field.draw(self.screen)
            self.continue_button.draw(self.screen)
            self.random_button.draw(self.screen)
            self.exit_button.draw(self.screen)
            
            # Status message
            if self.status_message:
                status = self.font_medium.render(self.status_message, True, self.status_color)
                self.screen.blit(status, (self.width // 2 - status.get_width() // 2, self.height // 2 + 200))
            
            pygame.display.flip()
        
        return None

class InputField:
    def __init__(self, rect, placeholder="", max_length=20):
        self.rect = rect
        self.text = ""
        self.placeholder = placeholder
        self.max_length = max_length
        self.active = True
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
