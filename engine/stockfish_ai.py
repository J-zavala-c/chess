"""
Módulo: engine.stockfish_ai
Encapsula la comunicación con Stockfish mediante python-chess.engine.
"""
from __future__ import annotations
import chess
import chess.engine
from typing import Optional

# Ajusta la ruta si tu ejecutable no está en PATH
STOCKFISH_PATH = "stockfish"

class StockfishAI:
    def __init__(self, path: Optional[str] = None):
        self.path = path or STOCKFISH_PATH
        self.engine: Optional[chess.engine.SimpleEngine] = None

    def start(self):
        """Inicia el motor (si no está iniciado). Lanza excepción si falla."""
        if self.engine:
            return
        self.engine = chess.engine.SimpleEngine.popen_uci(self.path)

    def stop(self):
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass
            self.engine = None

    def best_move(self, board: chess.Board, time_limit: Optional[float] = 0.5, depth: Optional[int] = None) -> Optional[chess.Move]:
        """
        Devuelve el mejor movimiento según Stockfish.
        Si depth es proporcionado se usa como límite, si no, se usa time_limit (segundos).
        """
        if not self.engine:
            self.start()
        if not self.engine:
            return None
        try:
            if depth is not None:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=time_limit)
            res = self.engine.play(board, limit)
            return res.move
        except Exception:
            return None

    def analyze(self, board: chess.Board, time_limit: Optional[float] = 0.5, depth: Optional[int] = None):
        """
        Devuelve el diccionario de info resultante del análisis (score, pv, etc.).
        """
        if not self.engine:
            self.start()
        if not self.engine:
            return None
        try:
            if depth is not None:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=time_limit)
            info = self.engine.analyse(board, limit)
            return info
        except Exception:
            return None

    def get_tactical_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Busca movimientos tácticos: capturas y ataques a piezas enemigas.
        Prioriza capturas sobre piezas de mayor valor.
        """
        if not board.legal_moves:
            return None
        
        best_move = None
        best_value = -1000
        
        for move in board.legal_moves:
            # Evaluar movimiento
            value = 0
            
            # 1. Capturas (prioritario)
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                # Valor relativo de la pieza capturada
                piece_values = {
                    chess.PAWN: 1,
                    chess.KNIGHT: 3,
                    chess.BISHOP: 3,
                    chess.ROOK: 5,
                    chess.QUEEN: 9,
                    chess.KING: 0
                }
                piece_value = piece_values.get(captured_piece.piece_type, 0)
                value += 100 + piece_value  # Prioriza capturas
                
                # 2. Evitar capturas donde se pierde más material
                attacking_piece = board.piece_at(move.from_square)
                if attacking_piece:
                    attacker_value = piece_values.get(attacking_piece.piece_type, 0)
                    if piece_value < attacker_value:
                        value -= 50  # Castigo por cambio desfavorable
            
            # 3. Ataques a piezas sin captura inmediata
            board_copy = board.copy()
            board_copy.push(move)
            
            # Contar piezas blancas atacadas después del movimiento
            for target_square in chess.SQUARES:
                target_piece = board_copy.piece_at(target_square)
                if target_piece and target_piece.color == chess.WHITE:
                    # Ver si está bajo ataque
                    if board_copy.is_attacked_by(chess.BLACK, target_square):
                        attackable_values = {
                            chess.PAWN: 1,
                            chess.KNIGHT: 3,
                            chess.BISHOP: 3,
                            chess.ROOK: 5,
                            chess.QUEEN: 9
                        }
                        value += attackable_values.get(target_piece.piece_type, 0) * 10
            
            # 4. Movimientos de desarrollo (si no hay capturas)
            if value == 0:
                # Puntuación por movimiento de pieza (desarrollo)
                piece = board.piece_at(move.from_square)
                if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    value += 5
                # Centro del tablero es mejor
                to_file = chess.square_file(move.to_square)
                to_rank = chess.square_rank(move.to_square)
                if 2 <= to_file <= 5 and 2 <= to_rank <= 5:
                    value += 3
            
            if value > best_value:
                best_value = value
                best_move = move
        
        return best_move
