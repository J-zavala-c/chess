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

    def get_smart_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Busca el mejor movimiento combinando múltiples estrategias:
        1. Checkmate en 1 movimiento (si existe)
        2. Evitar perder el rey (defensa de jaque)
        3. Usar Stockfish si disponible (análisis profundo)
        4. Fallback a táctica inteligente
        """
        if not board.legal_moves:
            return None
        
        # 1. BUSCAR JAQUE MATE EN 1 (prioritario absoluto)
        for move in board.legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            if board_copy.is_checkmate():
                return move
        
        # 2. EVITAR JAQUE MATE EN 1 (defensa crítica)
        for move in board.legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            # Simular mejor movimiento del enemigo
            is_losing = False
            for opponent_move in board_copy.legal_moves:
                test_board = board_copy.copy()
                test_board.push(opponent_move)
                if test_board.is_checkmate():
                    is_losing = True
                    break
            if is_losing:
                continue  # Saltar movimientos que pierden
            # Si llegamos aquí, el movimiento no pierde inmediatamente
            # Usar este como candidato
        
        # 3. USAR STOCKFISH SI DISPONIBLE (análisis profundo)
        if self.engine:
            try:
                # Buscar con profundidad 15 o tiempo limitado
                sf_move = self.best_move(board, time_limit=0.8, depth=15)
                if sf_move:
                    return sf_move
            except Exception:
                pass
        
        # 4. FALLBACK A TÁCTICA INTELIGENTE
        # Combina capturas, defensa y desarrollo
        best_move = None
        best_score = -10000
        
        for move in board.legal_moves:
            score = 0
            board_copy = board.copy()
            board_copy.push(move)
            
            # No jugar movimientos que pierden (defensa)
            opponent_best = self._quick_eval_opponent(board_copy)
            if opponent_best < -100:
                continue
            
            # Capturas
            captured = board.piece_at(move.to_square)
            if captured:
                piece_val = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}.get(captured.piece_type, 0)
                score += 50 + piece_val * 10
            
            # Amenazas (forks, pins, clavadas)
            threats = self._count_threats(board_copy, chess.WHITE)
            score += threats * 5
            
            # Control del centro
            to_file = chess.square_file(move.to_square)
            to_rank = chess.square_rank(move.to_square)
            if 2 <= to_file <= 5 and 2 <= to_rank <= 5:
                score += 10
            
            # Desarrollo de piezas menores
            piece = board.piece_at(move.from_square)
            if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                if move.from_rank in [0, 1]:  # Solo si viene de la fila inicial
                    score += 15
            
            # Proteger piezas valiosas
            if not self._is_hanging(board_copy, move.to_square, chess.BLACK):
                score += 5
            
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move or next(iter(board.legal_moves), None)
    
    def _quick_eval_opponent(self, board: chess.Board) -> int:
        """Evaluación rápida: ¿qué puede hacer el enemigo después?"""
        if self.engine:
            try:
                info = self.analyze(board, time_limit=0.2, depth=5)
                if info and 'score' in info:
                    return int(info['score'].white().cp) if hasattr(info['score'], 'white') else 0
            except:
                pass
        return 0
    
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
