import pygame
import os

class ChessAssets:
    def __init__(self):
        self.piece_images = {}
        self.load_piece_images()
        
    def load_piece_images(self):
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
            
            try:
                if os.path.exists(asset_path):
                    # Load from assets directory
                    image = pygame.image.load(asset_path)
                    self.piece_images[symbol] = image
                else:
                    # Create a fallback image
                    image = self.create_piece_image(symbol)
                    self.piece_images[symbol] = image
            except Exception as e:
                print(f"Error loading piece image for {symbol}: {e}")
                image = self.create_piece_image(symbol)
                self.piece_images[symbol] = image
    
    def create_piece_image(self, piece):
        """Create a simple piece image if the actual image is not available"""
        is_white = piece.isupper()
        color = (255, 255, 255) if is_white else (0, 0, 0)
        bg_color = (0, 0, 0) if is_white else (255, 255, 255)
        
        # Create a surface for the piece
        surface = pygame.Surface((60, 60))
        surface.fill(bg_color)
        
        # Draw a circle for the piece
        pygame.draw.circle(surface, color, (30, 30), 25)
        
        # Add the piece symbol
        font = pygame.font.Font(None, 36)
        text = font.render(piece.upper(), True, bg_color)
        text_rect = text.get_rect(center=(30, 30))
        surface.blit(text, text_rect)
        
        return surface
    
    def get_piece_image(self, piece):
        """Get the image for a chess piece"""
        symbol = piece.symbol()
        if symbol in self.piece_images:
            return self.piece_images[symbol]
        else:
            return self.create_piece_image(symbol)
