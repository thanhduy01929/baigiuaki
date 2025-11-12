import pygame
import sys
import socket
import json
import time

class LobbyMenu:
    def __init__(self, client, screen, width=800, height=600):
        self.client = client
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
        
        # Buttons
        self.new_game_button = Button(
            pygame.Rect(0, 0, 300, 80),
            "Create New Game",
            color=(150, 100, 200),
            hover_color=(200, 150, 255)
        )
        
        self.join_game_button = Button(
            pygame.Rect(0, 0, 300, 80),
            "Join Game",
            color=(100, 150, 200),
            hover_color=(150, 200, 250)
        )
        
        self.spectate_button = Button(
            pygame.Rect(0, 0, 300, 80),
            "Spectate Game",
            color=(100, 200, 150),
            hover_color=(150, 250, 200)
        )
        
        self.exit_button = Button(
            pygame.Rect(0, 0, 100, 40),
            "Exit",
            color=(200, 100, 100),
            hover_color=(250, 120, 120)
        )
        
        self.selected_game = None
        self.status_message = ""
        self.status_color = self.BLACK

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
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.new_game_button.is_hovered:
                        return "NEW_GAME"
                    elif self.join_game_button.is_hovered:
                        return "JOIN"
                    elif self.spectate_button.is_hovered:
                        return "SPECTATE"
                    elif self.exit_button.is_hovered:
                        return "QUIT"
            
            mouse_pos = pygame.mouse.get_pos()
            self.new_game_button.update(mouse_pos)
            self.join_game_button.update(mouse_pos)
            self.spectate_button.update(mouse_pos)
            self.exit_button.update(mouse_pos)
            
            # Draw UI
            self.screen.fill(self.WHITE)
            
            # Title
            title_text = "Chess Lobby"
            title_surf = self.font_large.render(title_text, True, self.GOLD)
            title_rect = title_surf.get_rect(center=(self.width // 2, 100))
            pygame.draw.rect(self.screen, self.SILVER, title_rect.inflate(20, 10), 5, border_radius=10)
            self.screen.blit(title_surf, title_rect)
            
            # Position buttons
            button_start_y = 200
            button_spacing = 100
            self.new_game_button.rect.topleft = (self.width // 2 - 150, button_start_y)
            self.join_game_button.rect.topleft = (self.width // 2 - 150, button_start_y + button_spacing)
            self.spectate_button.rect.topleft = (self.width // 2 - 150, button_start_y + 2 * button_spacing)
            self.exit_button.rect.topleft = (self.width - 120, 20)
            
            # Draw buttons
            self.new_game_button.draw(self.screen)
            self.join_game_button.draw(self.screen)
            self.spectate_button.draw(self.screen)
            self.exit_button.draw(self.screen)
            
            # Player info
            if self.client.player_id:
                player_text = self.font_small.render(f"Player: {self.client.player_id}", True, self.BLACK)
                self.screen.blit(player_text, (20, self.height - 30))
            
            # Status message
            if self.status_message:
                status = self.font_medium.render(self.status_message, True, self.status_color)
                self.screen.blit(status, (self.width // 2 - status.get_width() // 2, self.height - 50))
            
            pygame.display.flip()
        
        return None

    def get_selected_game(self):
        return self.selected_game

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
