# 🎯 Guía de Uso - Chess Project Mejorado

## ✨ Nuevas Funcionalidades

### 1. Visualización Clara de Piezas
- **Piezas Blancas**: Imágenes claras en color blanco
- **Piezas Negras**: Imágenes oscuras para fácil distinción
- Ahora es muy fácil ver qué piezas son blancas y cuáles negras

### 2. Botones de Control (Panel Derecho)

| Botón | Función | Atajo |
|-------|---------|-------|
| **Nuevo Juego** | Inicia una partida nueva | - |
| **Deshacer** | Deshace últimos 2 movimientos | - |
| **Guardar** | Guarda la partida actual | Ctrl+S |
| **Cargar** | Carga una partida guardada | Ctrl+O |

### 3. Panel de Movimientos
- Muestra todos los movimientos en **notación algebraica**
- Agrupados por turno: `1. e4 c5 2. Nf3 d6...`
- Se actualiza automáticamente con cada movimiento

## 🎮 Flujo de Juego

```
Juego Normal
├── Haces clic en una pieza blanca
├── Se resalta en verde
├── Aparecen círculos verdes con movimientos posibles
├── Haces clic en el destino
└── Turno de la IA (automático)

Guardar Progreso
├── Haces clic en "Guardar"
├── Se guarda en la base de datos
└── Mensaje de confirmación con ID

Cargar Partida
├── Haces clic en "Cargar"
├── Se abre ventana con lista de partidas
├── Seleccionas una
├── Se carga y reproduce automáticamente
└── Puedes continuar jugando

Deshacer Movimiento
├── Haces clic en "Deshacer"
├── Se borran últimos 2 movimientos
└── Vuelve a ser tu turno
```

## 📊 Información Técnica

### Archivos Imagen Disponibles
- `wP.png` - Peón blanco
- `wR.png` - Torre blanca
- `wN.png` - Caballo blanco
- `wB.png` - Alfil blanco
- `wQ.png` - Reina blanca
- `wK.png` - Rey blanco
- `bP.png` - Peón negro
- `bR.png` - Torre negra
- `bN.png` - Caballo negro
- `bB.png` - Alfil negro
- `bQ.png` - Reina negra
- `bK.png` - Rey negro

### Base de Datos
- Archivo: `chess_games.db`
- Tabla: `games`
- Campos: id, date, white, black, result, pgn
- Formato: SQLite

## 💡 Ejemplos de Uso

### Ejemplo 1: Juego Rápido
```
1. Abre la aplicación
2. Juega algunos movimientos
3. Haz clic en "Guardar"
4. Cierra la aplicación
```

### Ejemplo 2: Reanudar Partida
```
1. Abre la aplicación
2. Haz clic en "Cargar"
3. Selecciona tu partida anterior
4. Continúa jugando desde donde dejaste
```

### Ejemplo 3: Explorar Variantes
```
1. Juega una partida
2. Haz clic en "Deshacer" varias veces
3. Prueba otros movimientos
4. Cada movimiento diferente crea una nueva variante
```

## 🐛 Solución de Problemas

### Las imágenes no se ven
- Verifica que exista la carpeta `/pieces`
- Comprueba que todos los archivos `.png` están presentes
- Reinicia la aplicación

### No se puede guardar
- Verifica permisos de escritura en la carpeta del proyecto
- Comprueba que SQLite está disponible

### La IA no juega
- Stockfish debe estar instalado: `apt-get install stockfish`
- O ajusta la ruta en `main.py`

## 🎨 Interfaz

```
┌─────────────────────┬──────────────────────┐
│                     │ 📜 Movimientos       │
│   TABLERO DE        │ ──────────────────── │
│   AJEDREZ           │ 1. e4 c5             │
│   (8x8)             │ 2. Nf3 d6            │
│                     │ 3. d4 cxd4           │
│                     │ 4. Nxd4 Nf6          │
│                     │                      │
│                     │ [Nuevo Juego]        │
│                     │ [Deshacer]           │
│                     │ [Guardar] [Cargar]   │
└─────────────────────┴──────────────────────┘
```

## 📚 Notación Algebraica

- `e4` - Movimiento a casilla e4
- `Nf3` - Caballo a f3
- `Bxc5` - Alfil captura en c5
- `O-O` - Enroque corto
- `O-O-O` - Enroque largo
- `e8=Q` - Peón promocionado a reina
- `+` - Jaque
- `#` - Jaque mate

## 🚀 Instalación de Dependencias

```bash
# Desde el directorio del proyecto:
pip install Pillow python-chess

# O si usas venv:
.venv/bin/pip install Pillow python-chess
```

## 📝 Contacto y Soporte

Si tienes problemas, revisa que:
1. Python 3.10+ esté instalado
2. Todas las dependencias estén instaladas
3. La carpeta `pieces` tenga todas las imágenes
4. La base de datos `chess_games.db` sea escribible
