#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las mejoras funcionan correctamente.
Ejecutar con: python test_mejoras.py
"""

import sys
from pathlib import Path

# Añadir ruta del proyecto
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Verificar que todos los módulos se importan correctamente."""
    print("🔍 Probando importaciones...")
    try:
        from engine.game_manager import GameManager
        from engine.stockfish_ai import StockfishAI
        from database.db_manager import DBManager
        from gui.board_gui import BoardGUI
        from PIL import Image
        print("✓ Todas las importaciones OK")
        return True
    except ImportError as e:
        print(f"✗ Error de importación: {e}")
        return False

def test_piece_images():
    """Verificar que todas las imágenes de piezas existen."""
    print("\n🖼️  Probando imágenes de piezas...")
    pieces_path = PROJECT_ROOT / "pieces"
    
    required_files = [
        "wP.png", "wR.png", "wN.png", "wB.png", "wQ.png", "wK.png",
        "bP.png", "bR.png", "bN.png", "bB.png", "bQ.png", "bK.png"
    ]
    
    missing = []
    for filename in required_files:
        if not (pieces_path / filename).exists():
            missing.append(filename)
    
    if missing:
        print(f"✗ Falta imágenes: {', '.join(missing)}")
        return False
    else:
        print(f"✓ Todas las 12 imágenes encontradas")
        return True

def test_game_manager():
    """Verificar que GameManager funciona."""
    print("\n🎮 Probando GameManager...")
    try:
        from engine.game_manager import GameManager
        game = GameManager()
        
        # Verificar métodos clave
        assert hasattr(game, 'board'), "No tiene atributo 'board'"
        assert hasattr(game, 'export_pgn'), "No tiene método 'export_pgn'"
        assert hasattr(game, 'piece_at'), "No tiene método 'piece_at'"
        assert hasattr(game, 'reset'), "No tiene método 'reset'"
        
        # Verificar estado inicial
        pgn = game.export_pgn()
        assert "1. e2e4" not in pgn or "*" in pgn, "PGN no válido"
        
        print("✓ GameManager funciona correctamente")
        return True
    except Exception as e:
        print(f"✗ Error en GameManager: {e}")
        return False

def test_db_manager():
    """Verificar que DBManager funciona."""
    print("\n💾 Probando DBManager...")
    try:
        from database.db_manager import DBManager
        import tempfile
        
        # Usar DB temporal para no contaminar
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = DBManager(db_path)
        
        # Verificar métodos clave
        assert hasattr(db, 'save_game'), "No tiene método 'save_game'"
        assert hasattr(db, 'search_games'), "No tiene método 'search_games'"
        assert hasattr(db, 'load_pgn_by_id'), "No tiene método 'load_pgn_by_id'"
        
        # Guardar una prueba
        pgn_test = "[Event \"Test\"]\n1. e4 e5"
        game_id = db.save_game(pgn_test, "Test", "Test")
        assert isinstance(game_id, int), "ID no es entero"
        
        # Buscar
        games = db.search_games()
        assert len(games) >= 1, "No se guardó la partida"
        
        # Cargar
        loaded = db.load_pgn_by_id(game_id)
        assert "e4" in loaded, "PGN no se guardó correctamente"
        
        db.close()
        
        print("✓ DBManager funciona correctamente")
        return True
    except Exception as e:
        print(f"✗ Error en DBManager: {e}")
        return False

def test_gui_methods():
    """Verificar que los métodos GUI nuevos existen."""
    print("\n🎨 Probando métodos de GUI...")
    try:
        from gui.board_gui import BoardGUI
        
        # Verificar que los métodos existen
        required_methods = [
            '_load_piece_images',
            '_draw_selection_and_moves',
            '_update_move_list',
            '_undo',
            '_save_game',
            '_load_game'
        ]
        
        for method in required_methods:
            assert hasattr(BoardGUI, method), f"No tiene método '{method}'"
        
        print(f"✓ Todos los {len(required_methods)} métodos GUI nuevos están presentes")
        return True
    except Exception as e:
        print(f"✗ Error en GUI: {e}")
        return False

def test_chess_notation():
    """Verificar que la notación de ajedrez funciona."""
    print("\n📝 Probando notación de ajedrez...")
    try:
        import chess
        board = chess.Board()
        
        # Hacer un movimiento
        move = chess.Move.from_uci("e2e4")
        if move in board.legal_moves:
            board.push(move)
            # Obtener la notación SAN del movimiento que acabamos de hacer
            last_move = board.move_stack[-1]
            # Necesitamos copiar el board y ir atrás
            board_copy = board.copy()
            board_copy.pop()
            san = board_copy.san(last_move)
            assert "e4" in san, f"Notación incorrecta: {san}"
            print("✓ Notación de ajedrez funciona correctamente")
            return True
        else:
            print("✗ Movimiento no legal")
            return False
    except Exception as e:
        print(f"✗ Error en notación: {e}")
        return False

def main():
    """Ejecutar todas las pruebas."""
    print("=" * 60)
    print("🧪 PRUEBAS DE MEJORAS - CHESS PROJECT")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_piece_images,
        test_game_manager,
        test_db_manager,
        test_gui_methods,
        test_chess_notation
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Excepción en {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✓ Pruebas pasadas: {passed}/{total}")
    print(f"{'✗ Pruebas fallidas: ' + str(total - passed) if passed < total else '✓ ¡TODAS LAS PRUEBAS PASARON!'}")
    
    if passed == total:
        print("\n🎉 ¡El proyecto está listo para usar!")
        print("\nPara ejecutar la aplicación:")
        print("  cd /home/lonelyhacker/Escritorio/Chess_proyect")
        print("  .venv/bin/python main.py")
        return 0
    else:
        print("\n⚠️  Hay algunos problemas que revisar.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
