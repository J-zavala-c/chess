"""
Módulo: engine.game_manager
Responsable de la lógica del juego usando python-chess.
"""
from __future__ import annotations
import chess
import chess.pgn
import io
from typing import List, Optional

class GameManager:
    def __init__(self):
        self.board = chess.Board()

    def reset(self):
        self.board.reset()

    def push(self, move: chess.Move) -> bool:
        """Intenta aplicar un movimiento. Devuelve True si se aplicó."""
        if move in self.board.legal_moves:
            self.board.push(move)
            return True
        return False

    def undo(self):
        if self.board.move_stack:
            self.board.pop()

    def legal_moves_from(self, square: int) -> List[chess.Move]:
        return [m for m in self.board.legal_moves if m.from_square == square]

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def result(self) -> str:
        return self.board.result()

    def export_pgn(self, white: str = 'White', black: str = 'Black', result: Optional[str] = None) -> str:
        """
        Exporta la partida actual a PGN (con cabeceras).
        Si result no es None, lo incluye en el header 'Result'.
        """
        game = chess.pgn.Game()
        game.headers['White'] = white
        game.headers['Black'] = black
        if result is not None:
            game.headers['Result'] = result
        node = game
        for mv in self.board.move_stack:
            node = node.add_variation(mv)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return game.accept(exporter)

    def load_pgn_text(self, pgn_text: str):
        """
        Carga un texto PGN y aplica los movimientos al tablero.
        Lanza ValueError si no es un PGN válido.
        """
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            raise ValueError('Invalid PGN')
        self.board.reset()
        node = game
        while node.variations:
            node = node.variations[0]
            self.board.push(node.move)

    # Helpers para la UI
    def piece_at(self, square: int):
        return self.board.piece_at(square)

    def fen(self) -> str:
        return self.board.fen()

    def set_fen(self, fen: str):
        self.board.set_fen(fen)
