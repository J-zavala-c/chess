"""
Módulo: engine.stockfish_ai
Encapsula la comunicación con Stockfish mediante python-chess.engine.
Incluye sistema de niveles de dificultad y análisis de evaluación.
"""
from __future__ import annotations
import chess
import chess.engine
from typing import Optional, Tuple

# Ajusta la ruta si tu ejecutable no está en PATH
STOCKFISH_PATH = "stockfish"

# Niveles de dificultad del IA
DIFFICULTY_LEVELS = {
    "fácil": {"depth": 5, "time": 0.2, "name": "Fácil (principiante)"},
    "medio": {"depth": 12, "time": 0.8, "name": "Medio (intermedio)"},
    "difícil": {"depth": 20, "time": 2.0, "name": "Difícil (experto)"},
}

class StockfishAI:
    def __init__(self, path: Optional[str] = None, difficulty: str = "medio"):
        self.path = path or STOCKFISH_PATH
        self.engine: Optional[chess.engine.SimpleEngine] = None
        self.difficulty = difficulty if difficulty in DIFFICULTY_LEVELS else "medio"
        self.difficulty_config = DIFFICULTY_LEVELS[self.difficulty]
        self.last_evaluation = None  # Almacenar evaluación para mostrar

    def start(self):
        """Inicia el motor (si no está iniciado). Lanza excepción si falla."""
        if self.engine:
            return
        self.engine = chess.engine.SimpleEngine.popen_uci(self.path)

    def set_difficulty(self, difficulty: str):
        """Cambiar el nivel de dificultad"""
        if difficulty in DIFFICULTY_LEVELS:
            self.difficulty = difficulty
            self.difficulty_config = DIFFICULTY_LEVELS[difficulty]

    def stop(self):
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass
            self.engine = None

    def best_move(self, board: chess.Board, time_limit: Optional[float] = None, depth: Optional[int] = None) -> Optional[chess.Move]:
        """
        Devuelve el mejor movimiento según Stockfish.
        Si depth/time_limit no se proporcionan, usa la configuración de dificultad actual.
        """
        if not self.engine:
            self.start()
        if not self.engine:
            return None
        try:
            # Usar configuración de dificultad si no se especifica
            if depth is None and time_limit is None:
                depth = self.difficulty_config["depth"]
                time_limit = self.difficulty_config["time"]
            
            if depth is not None:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=time_limit)
            res = self.engine.play(board, limit)
            return res.move
        except Exception:
            return None

    def analyze(self, board: chess.Board, time_limit: Optional[float] = None, depth: Optional[int] = None):
        """
        Devuelve el diccionario de info resultante del análisis (score, pv, etc.).
        """
        if not self.engine:
            self.start()
        if not self.engine:
            return None
        try:
            # Usar configuración de dificultad si no se especifica
            if depth is None and time_limit is None:
                depth = self.difficulty_config["depth"]
                time_limit = self.difficulty_config["time"]
            
            if depth is not None:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=time_limit)
            info = self.engine.analyse(board, limit)
            # Guardar evaluación para mostrar en GUI
            if info and "score" in info:
                self.last_evaluation = info["score"]
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

    def get_smart_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Busca el mejor movimiento combinando múltiples estrategias.
        Usa la dificultad configurada para ajustar profundidad/tiempo.
        """
        if not board.legal_moves:
            return None
        
        # 1. BUSCAR JAQUE MATE EN 1 (prioritario absoluto)
        for move in board.legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            if board_copy.is_checkmate():
                return move
        
        # 2. USAR STOCKFISH SI DISPONIBLE (análisis con dificultad configurada)
        if self.engine:
            try:
                sf_move = self.best_move(board)
                if sf_move:
                    # También obtener evaluación para mostrar
                    analysis = self.analyze(board)
                    return sf_move
            except Exception:
                pass
        
        # 3. FALLBACK A TÁCTICA INTELIGENTE
        best_move = None
        best_score = -10000
        
        for move in board.legal_moves:
            score = 0
            board_copy = board.copy()
            board_copy.push(move)
            
            # A. Capturas (prioritario)
            captured = board.piece_at(move.to_square)
            if captured:
                piece_val = {
                    chess.PAWN: 1, 
                    chess.KNIGHT: 3, 
                    chess.BISHOP: 3, 
                    chess.ROOK: 5, 
                    chess.QUEEN: 9
                }.get(captured.piece_type, 0)
                score += 100 + piece_val * 20
                
                if board_copy.is_check():
                    score -= 1000
            
            # B. Amenazas múltiples (forks)
            threats = self._count_threats(board_copy, chess.BLACK)
            score += threats * 30
            
            # C. Control del centro
            to_file = chess.square_file(move.to_square)
            to_rank = chess.square_rank(move.to_square)
            if 2 <= to_file <= 5 and 2 <= to_rank <= 5:
                score += 20
            
            # D. Desarrollo
            piece = board.piece_at(move.from_square)
            if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                from_rank = chess.square_rank(move.from_square)
                if from_rank == 7:
                    score += 25
            
            # E. Defensa
            if self._is_hanging(board_copy, move.to_square, chess.WHITE):
                score -= 20
            
            # F. Check
            if board_copy.is_check():
                score += 50
            
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move or next(iter(board.legal_moves), None)
    
    def get_evaluation(self, board: chess.Board) -> Tuple[Optional[float], Optional[str]]:
        """
        Devuelve (evaluación numérica, texto descriptivo) de la posición actual.
        Evaluación positiva = ventaja para blancas, negativa = ventaja para negras
        """
        if not self.engine:
            return None, None
        
        try:
            analysis = self.analyze(board)
            if not analysis or "score" not in analysis:
                return None, None
            
            score_obj = analysis["score"]
            
            # Convertir score a número
            if score_obj.is_mate():
                # Jaque mate
                moves_to_mate = score_obj.mate()
                if moves_to_mate > 0:
                    return float('inf'), f"Mate blancas en {abs(moves_to_mate)} movimientos"
                else:
                    return float('-inf'), f"Mate negras en {abs(moves_to_mate)} movimientos"
            else:
                # Evaluación en centipeones (1/100 de peón)
                eval_score = score_obj.cp / 100.0  # Convertir a peones
                eval_score = eval_score * (-1 if board.turn == chess.BLACK else 1)  # Ajustar por turno
                
                # Descripción textual
                if abs(eval_score) < 0.5:
                    desc = "Posición igualada"
                elif eval_score > 3:
                    desc = "Ventaja significativa para blancas"
                elif eval_score > 1:
                    desc = "Ligera ventaja para blancas"
                elif eval_score < -3:
                    desc = "Ventaja significativa para negras"
                elif eval_score < -1:
                    desc = "Ligera ventaja para negras"
                else:
                    desc = "Posición igualada"
                
                return eval_score, desc
        except Exception:
            return None, None
    
    def _count_threats(self, board: chess.Board, color: int) -> int:
        """Cuenta cuántas piezas enemigas están siendo amenazadas"""
        count = 0
        enemy_color = chess.BLACK if color == chess.WHITE else chess.WHITE
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == enemy_color:
                if board.is_attacked_by(color, square):
                    count += 1
        return count
    
    def _is_hanging(self, board: chess.Board, square: int, attacker_color: int) -> bool:
        """¿Está la pieza en 'square' siendo atacada sin defensa?"""
        piece = board.piece_at(square)
        if not piece:
            return False
        
        # Contar atacantes y defensores
        attackers = sum(1 for _ in board.attackers(attacker_color, square))
        defenders = sum(1 for _ in board.attackers(not attacker_color, square))
        
        # Si hay más atacantes que defensores, está colgante
        return attackers > defenders
