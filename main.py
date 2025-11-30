"""
Punto de entrada del proyecto 'segundo chess'
"""
from engine.game_manager import GameManager
from engine.stockfish_ai import StockfishAI
ai = StockfishAI(path="/chess_proyect/engine/stockfish") 
from database.db_manager import DBManager
from gui.board_gui import BoardGUI

def main():
    # Inicializar módulos principales
    game = GameManager()
    db = DBManager()

    # Inicializar la IA Stockfish (ajustar ruta si es necesario)
    ai = StockfishAI(path="stockfish")

    # Iniciar GUI principal
    app = BoardGUI(game=game, ai=ai, db=db)

    app.mainloop()

if __name__ == "__main__":
    main()
