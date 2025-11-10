import chess

class EnhancedChessPiece:
    """A wrapper class for chess.Piece that adds additional functionality."""
    
    def __init__(self, piece):
        """Initialize with a chess.Piece object."""
        self.piece = piece
        self.move_count = 0
        self.last_move_time = None
        self.captured_pieces = []
    
    @property
    def color(self):
        """Get the color of the piece."""
        return self.piece.color
    
    @property
    def piece_type(self):
        """Get the type of the piece."""
        return self.piece.piece_type
    
    @property
    def symbol(self):
        """Get the symbol of the piece."""
        return self.piece.symbol()
    
    def record_move(self, timestamp):
        """Record that this piece has moved."""
        self.move_count += 1
        self.last_move_time = timestamp
    
    def record_capture(self, captured_piece):
        """Record that this piece has captured another piece."""
        self.captured_pieces.append(captured_piece)
    
    def get_move_history(self):
        """Get the move history of this piece."""
        return {
            "move_count": self.move_count,
            "last_move_time": self.last_move_time,
            "captures": [p.symbol() for p in self.captured_pieces]
        }
    
    def __str__(self):
        """String representation of the piece."""
        return f"{self.symbol} (moves: {self.move_count})"