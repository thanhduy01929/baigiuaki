import pygame
import sys
from pygame.locals import *

class SpectatorScreen:
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
        
        # Input fields
        self.name_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your name")
        self.id_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter your ID")
        self.game_field = InputField(pygame.Rect(0, 0, 300, 50), "Enter game ID")
        
        # Buttons
        self.spectate_button = Button(
            pygame.Rect(0, 0, 200, 50),
            "Spectate Game",
            color=(150, 100, 200),
            hover_color=(200, 150, 255)
        )
        
        # Exit button
        self.exit_button = Button(
            pygame.Rect(0, 0, 100, 40),
            "Exit",
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )
        
        self.status_message = ""
        self.status_color = self.BLACK

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), RESIZABLE)
                
                self.name_field.handle_event(event)
                self.id_field.handle_event(event)
                self.game_field.handle_event(event)
                
                if event.type == MOUSEBUTTONDOWN:
                    if self.spectate_button.is_hovered:
                        if self.name_field.text and self.id_field.text and self.game_field.text:
                            return {
                                "name": self.name_field.text,
                                "id": self.id_field.text,
                                "game_id": self.game_field.text
                            }
                        else:
                            self.status_message = "Please fill in all fields"
                            self.status_color = self.RED
                    elif self.exit_button.is_hovered:
                        pygame.quit()
                        sys.exit()
            
            mouse_pos = pygame.mouse.get_pos()
            self.spectate_button.update(mouse_pos)
            self.exit_button.update(mouse_pos)
            
            # Draw UI
            self.screen.fill(self.WHITE)
            # Title
            title_text = "Spectate a Game"
            title_surf = self.font_large.render(title_text, True, self.GOLD)
            title_rect = title_surf.get_rect(center=(self.width // 2, 100))
            pygame.draw.rect(self.screen, self.SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
            self.screen.blit(title_surf, title_rect)
            
            # Position input fields
            self.name_field.rect.topleft = (self.width // 2 - 150, 200)
            self.id_field.rect.topleft = (self.width // 2 - 150, 270)
            self.game_field.rect.topleft = (self.width // 2 - 150, 340)
            self.spectate_button.rect.topleft = (self.width // 2 - 100, 420)
            self.exit_button.rect.topleft = (self.width - 120, 20)
            
            # Labels
            name_label = self.font_medium.render("Your Name:", True, self.BLACK)
            self.screen.blit(name_label, (self.width // 2 - 150, self.name_field.rect.top - 30))
            id_label = self.font_medium.render("Your ID:", True, self.BLACK)
            self.screen.blit(id_label, (self.width // 2 - 150, self.id_field.rect.top - 23))
            game_label = self.font_medium.render("Game ID:", True, self.BLACK)
            self.screen.blit(game_label, (self.width // 2 - 150, self.game_field.rect.top - 23))
            
            # Draw input fields and button
            self.name_field.draw(self.screen)
            self.id_field.draw(self.screen)
            self.game_field.draw(self.screen)
            self.spectate_button.draw(self.screen)
            self.exit_button.draw(self.screen)
            
            # Status message
            if self.status_message:
                status = self.font_medium.render(self.status_message, True, self.status_color)
                self.screen.blit(status, (self.width // 2 - status.get_width() // 2, 500))
            
            pygame.display.flip()
        
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