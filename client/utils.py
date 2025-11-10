import chess

def format_move(move):
    """Format a move string for display."""
    return move.replace(" ", "")

def parse_board_state(fen):
    """Parse a FEN string into a more readable format for the client."""
    board = chess.Board(fen)
    state = {}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            row, col = chess.square_rank(square), chess.square_file(square)
            state[f"{chr(97 + col)}{8 - row}"] = piece.symbol()
    return state

def square_to_position(square, square_size=64):
    """Convert a chess square to pixel position on the board."""
    row, col = 7 - chess.square_rank(square), chess.square_file(square)
    return (col * square_size, row * square_size)