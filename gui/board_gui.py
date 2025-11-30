"""
Board GUI mejorada con imágenes de piezas, guardar/cargar partidas, y mejor anotación
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import chess
import chess.pgn
import random
import traceback
import os
import io
from pathlib import Path
from PIL import Image, ImageTk
from engine.game_manager import GameManager
from engine.stockfish_ai import StockfishAI
from database.db_manager import DBManager
import sys

SQUARE_SIZE = 80
BOARD_COLOR_LIGHT = "#EEEED2"
BOARD_COLOR_DARK = "#769656"

# Mapeo de piezas a archivos PNG
PIECE_IMAGES = {
    "P": "wP.png", "R": "wR.png", "N": "wN.png", "B": "wB.png", "Q": "wQ.png", "K": "wK.png",
    "p": "bP.png", "r": "bR.png", "n": "bN.png", "b": "bB.png", "q": "bQ.png", "k": "bK.png"
}

# Símbolos Unicode de respaldo si no carga la imagen
PIECE_SYMBOLS = {
    "P": "♙", "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔",
    "p": "♟", "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚"
}

def dbg(*args, **kwargs):
    print("[DBG]", *args, **kwargs)
    sys.stdout.flush()

class BoardGUI(tk.Tk):
    def __init__(self, game: GameManager, ai: StockfishAI, db: DBManager):
        super().__init__()
        self.title("♟ Ajedrez — Jugador (blancas) vs IA (negras)")
        self.geometry("1050x750")
        self.resizable(False, False)

        self.game = game
        self.ai = ai
        self.db = db
        
        # Path para las imágenes de piezas
        self.pieces_path = Path(__file__).parent.parent / "pieces"
        self.piece_images_cache = {}  # Cache de imágenes cargadas
        self.canvas_images = []  # Lista para mantener referencias vivas de PhotoImage en canvas

        self.selected_square = None
        self.suggested_moves = set()  # Moves suggested for the selected piece
        self.game_over = False
        self.ai_thinking = False
        self.move_history = []  # Historial de movimientos en SAN

        # try to start engine, but continue if not available
        self.ai_available = False
        try:
            self.ai.start()
            self.ai_available = True
            dbg("Stockfish iniciado correctamente.")
        except Exception as e:
            dbg("Stockfish no disponible:", e)
            self.ai_available = False

        self._load_piece_images()
        self._create_layout()
        self._draw_board()
        dbg("GUI iniciada. FEN inicial:", self.game.board.fen())
        dbg("Turno inicial:", "WHITE" if self.game.board.turn == chess.WHITE else "BLACK")

    # UI
    def _create_layout(self):
        self.canvas = tk.Canvas(self, width=8 * SQUARE_SIZE, height=8 * SQUARE_SIZE)
        self.canvas.place(x=30, y=30)
        self.canvas.bind("<Button-1>", self._on_click)

        side = ttk.Frame(self)
        side.place(x=700, y=30)

        ttk.Label(side, text="📜 Movimientos", font=("Arial", 12, "bold")).pack(anchor="w")
        self.move_text = tk.Text(side, width=38, height=18, state="disabled", relief="solid", borderwidth=1)
        self.move_text.pack(pady=10)

        # Botones de control
        buttons_frame = ttk.Frame(side)
        buttons_frame.pack(pady=5)
        
        ttk.Button(buttons_frame, text="Nuevo Juego", command=self._new_game).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(buttons_frame, text="Reiniciar", command=self._restart_game).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(buttons_frame, text="Deshacer", command=self._undo).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(buttons_frame, text="Guardar", command=self._save_game).grid(row=1, column=1, padx=3, pady=3)
        ttk.Button(buttons_frame, text="Cargar", command=self._load_game).grid(row=2, column=0, columnspan=2, padx=3, pady=3, sticky="ew")

    # draw
    def _load_piece_images(self):
        """Carga las imágenes de piezas con redimensionamiento.
        Las referencias se mantienen en self.piece_images_cache PERMANENTEMENTE
        para evitar garbage collection.
        """
        try:
            for symbol, filename in PIECE_IMAGES.items():
                img_path = self.pieces_path / filename
                if img_path.exists():
                    img = Image.open(img_path)
                    img = img.resize((SQUARE_SIZE - 10, SQUARE_SIZE - 10), Image.Resampling.LANCZOS)
                    # Crear PhotoImage y almacenarla PERMANENTEMENTE en la instancia
                    photo_img = ImageTk.PhotoImage(img)
                    # IMPORTANTE: guardar ambas referencias (PIL Image y PhotoImage) para evitar GC
                    self.piece_images_cache[symbol] = (img, photo_img)
                    dbg(f"✓ Imagen cargada: {filename}")
                else:
                    dbg(f"✗ Imagen no encontrada: {img_path}")
                    self.piece_images_cache[symbol] = None
        except Exception as e:
            dbg(f"✗ Error cargando imágenes: {e}")
            # Inicializar como None para evitar accesos a clave no existente
            for symbol in PIECE_IMAGES.keys():
                self.piece_images_cache[symbol] = None

    def _draw_board(self):
        self.canvas.delete("all")
        self.canvas_images = []  # Limpiar referencias antiguas
        
        # Dibujar cuadrados del tablero
        for r in range(8):
            for c in range(8):
                x1, y1 = c * SQUARE_SIZE, (7 - r) * SQUARE_SIZE
                x2, y2 = x1 + SQUARE_SIZE, y1 + SQUARE_SIZE
                color = BOARD_COLOR_LIGHT if (r + c) % 2 == 0 else BOARD_COLOR_DARK
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Dibujar anotaciones del último movimiento (resaltado)
        if len(self.game.board.move_stack) > 0:
            last_move = self.game.board.move_stack[-1]
            # Resaltar casilla origen (amarillo suave)
            from_file = chess.square_file(last_move.from_square)
            from_rank = chess.square_rank(last_move.from_square)
            from_x1 = from_file * SQUARE_SIZE
            from_y1 = (7 - from_rank) * SQUARE_SIZE
            from_x2 = from_x1 + SQUARE_SIZE
            from_y2 = from_y1 + SQUARE_SIZE
            self.canvas.create_rectangle(from_x1, from_y1, from_x2, from_y2, fill="#F0D800", outline="")
            
            # Resaltar casilla destino (amarillo más claro)
            to_file = chess.square_file(last_move.to_square)
            to_rank = chess.square_rank(last_move.to_square)
            to_x1 = to_file * SQUARE_SIZE
            to_y1 = (7 - to_rank) * SQUARE_SIZE
            to_x2 = to_x1 + SQUARE_SIZE
            to_y2 = to_y1 + SQUARE_SIZE
            self.canvas.create_rectangle(to_x1, to_y1, to_x2, to_y2, fill="#FFEB99", outline="")
            
            # Guardar SAN para mostrar más tarde (después de dibujar las piezas)
            # El SAN fue calculado y guardado en _apply_move_force() ANTES del push
            if hasattr(self, '_last_move_san_text'):
                self._last_move_san = (to_x1 + 8, to_y1 + 8, self._last_move_san_text)
            else:
                self._last_move_san = None

        # Dibujar indicadores de movimientos (debajo de las piezas)
        self._draw_move_indicators()

        # Dibujar piezas usando imágenes (con referencias mantenidas vivas)
        for sq in chess.SQUARES:
            p = self.game.piece_at(sq)
            if not p:
                continue
            symbol = p.symbol()
            f, r = chess.square_file(sq), chess.square_rank(sq)
            x = f * SQUARE_SIZE + SQUARE_SIZE / 2
            y = (7 - r) * SQUARE_SIZE + SQUARE_SIZE / 2
            
            # Usar imagen si está disponible
            if symbol in self.piece_images_cache and self.piece_images_cache[symbol] is not None:
                try:
                    # El cache contiene tupla (PIL_Image, PhotoImage)
                    # Solo necesitamos el PhotoImage para el canvas
                    img_data = self.piece_images_cache[symbol]
                    if isinstance(img_data, tuple):
                        pil_img, photo_img = img_data
                    else:
                        photo_img = img_data
                    
                    # Mantener referencia en canvas_images para evitar garbage collection
                    self.canvas_images.append(photo_img)
                    self.canvas.create_image(x, y, image=photo_img)
                    dbg(f"✓ [DRAW] pieza {symbol} dibujada en ({f},{r})")
                except Exception as e:
                    dbg(f"✗ [DRAW] error drawing image for {symbol}: {e}")
                    # Fallback a símbolo Unicode
                    txt = PIECE_SYMBOLS.get(symbol, '?')
                    self.canvas.create_text(x, y, text=txt, font=("DejaVu Sans", 48, "bold"), fill="#000000")
            else:
                # Sin imagen disponible - usar símbolo Unicode
                dbg(f"⚠ [DRAW] imagen no disponible para {symbol}, usando fallback Unicode")
                txt = PIECE_SYMBOLS.get(symbol, '?')
                self.canvas.create_text(x, y, text=txt, font=("DejaVu Sans", 48, "bold"), fill="#000000")

        # Dibujar anotación SAN encima de la pieza destino si existe
        try:
            if hasattr(self, '_last_move_san') and self._last_move_san:
                x_txt, y_txt, txt = self._last_move_san
                self.canvas.create_text(x_txt, y_txt, text=txt, font=("Arial", 9, "bold"), fill="#333333", anchor="nw")
        except Exception:
            pass

        # Dibujar selección (borde) encima de las piezas
        self._draw_selection_and_moves()
        
        # Actualizar lista de movimientos
        self._update_move_list()
        dbg("[DRAW] board fen:", self.game.board.fen(), " turn:", "WHITE" if self.game.board.turn==chess.WHITE else "BLACK")

    def _draw_selection_and_moves(self):
        """Dibuja resaltado y movimientos posibles cuando se selecciona una pieza."""
        # Solo dibuja el borde de selección (no indicadores que cubran las piezas)
        if self.selected_square is None:
            return

        file = chess.square_file(self.selected_square)
        rank = chess.square_rank(self.selected_square)
        x1, y1 = file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE
        x2, y2 = x1 + SQUARE_SIZE, y1 + SQUARE_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00AA00", width=5)


    def _material_score(self, board: chess.Board) -> int:
        """Simple material evaluation: positive means advantage for White."""
        vals = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }
        score = 0
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p:
                continue
            v = vals.get(p.piece_type, 0)
            score += v if p.color == chess.WHITE else -v
        return score

    def _compute_suggestions(self):
        """Compute suggested move(s) for the currently selected white piece.
        Simple heuristic: prefer moves that increase material (captures/promotions), fallback to mobility.
        """
        self.suggested_moves = set()
        if self.selected_square is None:
            return
        if self.game.board.turn != chess.WHITE:
            return

        # collect legal moves from selected square
        cand = [m for m in self.game.board.legal_moves if m.from_square == self.selected_square]
        if not cand:
            return

        base_score = self._material_score(self.game.board)
        best_score = None
        best_moves = []
        for m in cand:
            b = self.game.board.copy()
            try:
                b.push(m)
            except Exception:
                continue
            score = self._material_score(b) - base_score
            # add small tie-breaker: number of legal moves after the move (mobility)
            mobility = len(list(b.legal_moves))
            score = score * 100 + mobility
            if best_score is None or score > best_score:
                best_score = score
                best_moves = [m]
            elif score == best_score:
                best_moves.append(m)

        # Keep 1 or 2 best moves as suggestions
        for m in best_moves[:2]:
            self.suggested_moves.add(m)


    def _draw_move_indicators(self):
        """Dibuja indicadores de movimientos por debajo de las piezas para no ocultarlas.
        Este método dibuja puntos pequeños para movimientos normales y anillos (solo contorno)
        para capturas, y se ejecuta antes de dibujar las piezas.
        """
        try:
            if self.selected_square is None:
                return
            # Compute suggestions for the selected piece if necessary
            self._compute_suggestions()

            for move in self.game.board.legal_moves:
                if move.from_square == self.selected_square:
                    to_file = chess.square_file(move.to_square)
                    to_rank = chess.square_rank(move.to_square)
                    cx = to_file * SQUARE_SIZE + SQUARE_SIZE / 2
                    cy = (7 - to_rank) * SQUARE_SIZE + SQUARE_SIZE / 2
                    target_piece = self.game.board.piece_at(move.to_square)
                    # If this move is a suggested move, draw a blue marker
                    if move in self.suggested_moves:
                        self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10,
                                               fill="#3399FF", outline="")
                    elif target_piece:
                        # Captura: dibujar anillo (solo contorno) para no ocultar la pieza
                        self.canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14,
                                               outline="#CC0000", width=3)
                    else:
                        # Movimiento normal: punto verde pequeño
                        self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                               fill="#00DD00", outline="")
        except Exception:
            dbg("[INDICATORS] error drawing move indicators")

    # clicks
    def _on_click(self, event):
        dbg("[CLICK] received at", event.x, event.y)
        if self.game_over:
            dbg("[CLICK] ignored: game is over")
            return
        if self.ai_thinking:
            dbg("[CLICK] ignored: AI thinking")
            return
        if self.game.board.turn != chess.WHITE:
            dbg("[CLICK] ignored: not WHITE's turn (turn is {})".format("WHITE" if self.game.board.turn==chess.WHITE else "BLACK"))
            return

        file = event.x // SQUARE_SIZE
        rank = 7 - (event.y // SQUARE_SIZE)
        if not (0 <= file < 8 and 0 <= rank < 8):
            dbg("[CLICK] out of board")
            return
        sq = chess.square(file, rank)
        piece = self.game.piece_at(sq)
        dbg("[CLICK] square", chess.square_name(sq), "piece:", piece)

        if self.selected_square is None:
            if piece and piece.color == chess.WHITE:
                self.selected_square = sq
                dbg("[SELECT] selected", chess.square_name(sq))
                # show indicators/suggestions immediately
                self._draw_board()
            else:
                dbg("[SELECT] no white piece on clicked square")
        else:
            # build move, try apply
            mv = chess.Move(self.selected_square, sq)
            dbg("[MOVE] attempting move", mv.uci() if mv else mv)
            applied = self._apply_move_force(mv)
            if not applied:
                # try promotion to queen if pawn and last rank
                if chess.square_rank(sq) in (0,7) and self.game.board.piece_type_at(self.selected_square) == chess.PAWN:
                    mv2 = chess.Move(self.selected_square, sq, promotion=chess.QUEEN)
                    dbg("[MOVE] trying promotion move", mv2.uci())
                    applied = self._apply_move_force(mv2)
                    if applied:
                        dbg("[APPLY] promotion applied", mv2.uci())
            if applied:
                self.selected_square = None
                self._draw_board()
                dbg("[MOVE] applied. fen after:", self.game.board.fen(), "turn:", ("WHITE" if self.game.board.turn==chess.WHITE else "BLACK"))
                # if now AI's turn AND game not over, trigger AI
                if self.game.board.turn == chess.BLACK and not self.game_over:
                    self.after(120, self._ai_move)
            else:
                dbg("[MOVE] not applied")
                self.selected_square = None
            self._draw_board()

    def _apply_move_force(self, move):
        """
        Force-apply a move to self.game.board:
        - Try direct push if move in legal moves
        - Else try to match UCI with one of legal moves
        - Calculates and stores SAN notation BEFORE pushing
        - Returns True if applied
        """
        try:
            legal = list(self.game.board.legal_moves)
            dbg("[APPLY] legal moves count:", len(legal))
            
            # direct membership
            if move in legal:
                # Calcular SAN ANTES de hacer push
                move_san = self.game.board.san(move)
                self._last_move_san_text = move_san
                self.move_history.append(move_san)  # Guardar en historial
                self.game.board.push(move)
                dbg("[APPLY] direct push used:", move.uci(), "SAN:", move_san)
                # Check end of game conditions
                if self.game.board.is_checkmate():
                    self.game_over = True
                    dbg("[CHECKMATE] Game over! Result:", self.game.board.result())
                    messagebox.showinfo("Jaque mate", f"Jaque mate. Resultado: {self.game.board.result()}")
                    dbg("[CHECKMATE] Dialog closed, scheduling restart...")
                    self.after(500, self._new_game)  # Auto-restart after 500ms
                elif self.game.board.is_stalemate() or self.game.board.is_insufficient_material():
                    self.game_over = True
                    dbg("[STALEMATE] Game over!")
                    messagebox.showinfo("Tablas", "La partida ha terminado en tablas.")
                    dbg("[STALEMATE] Dialog closed, scheduling restart...")
                    self.after(500, self._new_game)  # Auto-restart after 500ms
                # NOTE: No check notification here - only notify after AI moves (when it's player's turn)
                return True
            
            # match by UCI
            u = move.uci()
            for m in legal:
                if m.uci() == u:
                    # Calcular SAN ANTES de hacer push
                    move_san = self.game.board.san(m)
                    self._last_move_san_text = move_san
                    self.move_history.append(move_san)  # Guardar en historial
                    self.game.board.push(m)
                    dbg("[APPLY] push by matching uci:", m.uci(), "SAN:", move_san)
                    # Check end of game conditions
                    if self.game.board.is_checkmate():
                        self.game_over = True
                        messagebox.showinfo("Jaque mate", f"Jaque mate. Resultado: {self.game.board.result()}")
                        self.after(500, self._new_game)  # Auto-restart after 500ms
                    elif self.game.board.is_stalemate() or self.game.board.is_insufficient_material():
                        self.game_over = True
                        messagebox.showinfo("Tablas", "La partida ha terminado en tablas.")
                        self.after(500, self._new_game)  # Auto-restart after 500ms
                    # NOTE: No check notification here - only notify after AI moves (when it's player's turn)
                    return True
            
            # try SAN matching: convert all legal to SAN and compare? skip - risky
            dbg("[APPLY] move not matched among legal moves")
            return False
        except Exception as e:
            dbg("[ERROR] exception in _apply_move_force:", e)
            return False
            traceback.print_exc()
            return False

    # AI
    def _ai_move(self):
        if self.game_over or self.game.board.is_game_over():
            dbg("[AI] game over, not moving")
            return
        self.ai_thinking = True
        dbg("[AI] starting worker - current fen:", self.game.board.fen())

        def worker():
            mv = None
            try:
                # Usar smart_move que combina Stockfish + táctica inteligente
                mv = self.ai.get_smart_move(self.game.board)
                dbg("[AI] smart move selected:", mv)
                    
            except Exception as e:
                dbg("[AI] error computing smart move:", e)
                traceback.print_exc()
                mv = None

            if mv is None:
                # Fallback: intenta mejor movimiento disponible (aleatorio)
                try:
                    leg = list(self.game.board.legal_moves)
                    if leg:
                        mv = leg[0]
                        dbg("[AI] fallback to first legal move:", mv)
                except:
                    pass
            
            if mv is None:
                # Último recurso: movimiento aleatorio
                leg = list(self.game.board.legal_moves)
                if len(leg) == 0:
                    dbg("[AI] no legal moves for AI")
                else:
                    mv = random.choice(leg)
                    dbg("[AI] fallback random chosen mv:", mv.uci())

            def apply_finish():
                try:
                    if mv is not None:
                        # match mv to current legal moves (safety)
                        if mv in self.game.board.legal_moves:
                            # Guardar SAN ANTES de push
                            move_san = self.game.board.san(mv)
                            self.move_history.append(move_san)
                            self._last_move_san_text = move_san
                            self.game.board.push(mv)
                            dbg("[AI] pushed mv:", mv.uci(), "SAN:", move_san)
                            # Check end of game
                            if self.game.board.is_checkmate():
                                self.game_over = True
                                dbg("[AI CHECKMATE] Game over! Result:", self.game.board.result())
                                messagebox.showinfo("Jaque mate", f"Jaque mate. Resultado: {self.game.board.result()}")
                                dbg("[AI CHECKMATE] Dialog closed, scheduling restart...")
                                self.after(500, self._new_game)  # Auto-restart after 500ms
                            elif self.game.board.is_stalemate() or self.game.board.is_insufficient_material():
                                self.game_over = True
                                dbg("[AI STALEMATE] Game over!")
                                messagebox.showinfo("Tablas", "La partida ha terminado en tablas.")
                                dbg("[AI STALEMATE] Dialog closed, scheduling restart...")
                                self.after(500, self._new_game)  # Auto-restart after 500ms
                            elif self.game.board.is_check() and self.game.board.turn == chess.WHITE:
                                # Only notify check if it's the player's turn (WHITE) and they are in check
                                messagebox.showinfo("Jaque", "¡Jaque al rey!")
                        else:
                            # try to match by uci string
                            u = mv.uci()
                            pushed = False
                            for m in list(self.game.board.legal_moves):
                                if m.uci() == u:
                                    # Guardar SAN ANTES de push
                                    move_san = self.game.board.san(m)
                                    self._last_move_san_text = move_san
                                    self.move_history.append(move_san)
                                    self.game.board.push(m)
                                    dbg("[AI] pushed matched mv by uci:", m.uci(), "SAN:", move_san)
                                    # Check end of game
                                    if self.game.board.is_checkmate():
                                        self.game_over = True
                                        dbg("[AI CHECKMATE] Game over! Result:", self.game.board.result())
                                        messagebox.showinfo("Jaque mate", f"Jaque mate. Resultado: {self.game.board.result()}")
                                        dbg("[AI CHECKMATE] Dialog closed, scheduling restart...")
                                        self.after(500, self._new_game)  # Auto-restart after 500ms
                                    elif self.game.board.is_stalemate() or self.game.board.is_insufficient_material():
                                        self.game_over = True
                                        dbg("[AI STALEMATE] Game over!")
                                        messagebox.showinfo("Tablas", "La partida ha terminado en tablas.")
                                        dbg("[AI STALEMATE] Dialog closed, scheduling restart...")
                                        self.after(500, self._new_game)  # Auto-restart after 500ms
                                    elif self.game.board.is_check() and self.game.board.turn == chess.WHITE:
                                        # Only notify check if it's the player's turn (WHITE) and they are in check
                                        messagebox.showinfo("Jaque", "¡Jaque al rey!")
                                    pushed = True
                                    break
                            if not pushed:
                                dbg("[AI] could not apply mv (not legal now):", mv)
                    else:
                        dbg("[AI] no mv computed")
                except Exception as e:
                    dbg("[AI ERROR] applying mv:", e)
                    traceback.print_exc()
                finally:
                    self.ai_thinking = False
                    self._draw_board()
                    dbg("[AI] after apply fen:", self.game.board.fen(), "turn:", ("WHITE" if self.game.board.turn==chess.WHITE else "BLACK"))
                    if self.game.board.is_game_over():
                        messagebox.showinfo("Fin del juego", "La partida ha terminado.")
            self.after(0, apply_finish)

        threading.Thread(target=worker, daemon=True).start()

    # helper
    def _update_move_list(self):
        """Actualiza la lista de movimientos con numeración algebraica.
        Lee directamente del historial que se construye mientras se hacen los moves.
        """
        try:
            moves = []
            for i, san in enumerate(self.move_history):
                # Agrupar por pares (movimiento blanco y negro)
                if i % 2 == 0:
                    move_num = (i // 2) + 1
                    moves.append(f"{move_num}. {san}")
                else:
                    moves[-1] += f" {san}"
        except Exception as e:
            dbg("[ERROR] en _update_move_list:", e)
            moves = []
        
        text = "\n".join(moves)
        self.move_text.config(state="normal")
        self.move_text.delete("1.0", "end")
        self.move_text.insert("1.0", text)
        self.move_text.config(state="disabled")

    def _new_game(self):
        self.game.reset()
        self.selected_square = None
        self.suggested_moves = set()
        self.game_over = False
        self.ai_thinking = False
        self.move_history = []
        self._draw_board()
        dbg("[GAME] new game started. fen:", self.game.board.fen())

    def _restart_game(self):
        """Reinicia la partida actual (alias para _new_game)"""
        self._new_game()
        messagebox.showinfo("Reiniciar", "Partida reiniciada.")

    def _undo(self):
        """Deshacer los últimos 2 movimientos (jugador + IA)"""
        try:
            if len(self.game.board.move_stack) == 0:
                messagebox.showinfo("Deshacer", "No hay movimientos para deshacer.")
                return
            
            # Deshacer el movimiento de la IA (negro)
            if len(self.game.board.move_stack) > 0 and self.game.board.turn == chess.WHITE:
                self.game.board.pop()
                dbg("[UNDO] Deshecho movimiento de IA")
            
            # Deshacer el movimiento del jugador (blanco)
            if len(self.game.board.move_stack) > 0:
                self.game.board.pop()
                dbg("[UNDO] Deshecho movimiento del jugador")
            
            self.selected_square = None
            self.ai_thinking = False
            self._draw_board()
            dbg("[UNDO] FEN después deshacer:", self.game.board.fen())
        except Exception as e:
            dbg("[UNDO ERROR]", e)
            traceback.print_exc()

    def _save_game(self):
        """Guardar la partida actual en la base de datos"""
        try:
            # Generar PGN
            pgn_text = self.game.export_pgn(white="Jugador", black="IA Stockfish")
            
            # Guardar en base de datos
            game_id = self.db.save_game(pgn_text, white="Jugador", black="IA Stockfish")
            messagebox.showinfo("Guardar Partida", f"Partida guardada correctamente con ID: {game_id}")
            dbg(f"[SAVE] Partida guardada con ID: {game_id}")
        except Exception as e:
            dbg("[SAVE ERROR]", e)
            messagebox.showerror("Error", f"No se pudo guardar la partida: {e}")

    def _load_game(self):
        """Cargar una partida guardada de la base de datos"""
        try:
            # Obtener lista de partidas
            games = self.db.search_games(limit=50)
            
            if not games:
                messagebox.showinfo("Cargar Partida", "No hay partidas guardadas.")
                return
            
            # Crear ventana de selección
            load_window = tk.Toplevel(self)
            load_window.title("Cargar Partida")
            load_window.geometry("400x400")
            
            ttk.Label(load_window, text="Selecciona una partida:", font=("Arial", 10, "bold")).pack(pady=10)
            
            # Crear listbox con las partidas
            listbox = tk.Listbox(load_window, height=15, width=50)
            listbox.pack(pady=10, padx=10)
            
            for game_id, date, white, black, result in games:
                listbox.insert(tk.END, f"ID:{game_id} - {date} - {white} vs {black} ({result})")
            
            def load_selected():
                selection = listbox.curselection()
                if not selection:
                    messagebox.showwarning("Selección", "Por favor, selecciona una partida.")
                    return
                
                game_id = games[selection[0]][0]
                pgn_text = self.db.load_pgn_by_id(game_id)
                
                if pgn_text:
                    # Parsear PGN y cargar
                    try:
                        import io
                        pgn_io = io.StringIO(pgn_text)
                        game_pgn = chess.pgn.read_game(pgn_io)
                        
                        if game_pgn is None:
                            raise ValueError("PGN no válido")
                        
                        self.game.board.reset()
                        
                        # Reproducir movimientos
                        node = game_pgn
                        while node.variations:
                            move = node.variations[0].move
                            self.game.board.push(move)
                            node = node.variations[0]
                        
                        self.selected_square = None
                        self.ai_thinking = False
                        self._draw_board()
                        messagebox.showinfo("Cargar", "Partida cargada correctamente.")
                        load_window.destroy()
                        dbg(f"[LOAD] Partida {game_id} cargada")
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo parsear la partida: {e}")
                        dbg("[LOAD ERROR]", e)
            
            ttk.Button(load_window, text="Cargar", command=load_selected).pack(pady=10)
            
        except Exception as e:
            dbg("[LOAD ERROR]", e)
            messagebox.showerror("Error", f"No se pudo cargar la partida: {e}")
