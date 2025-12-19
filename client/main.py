import asyncio
import pickle
import sys
import os

# Fix for WASM/Pygbag import issues
# If running in Emscripten, ensure we can import local modules
if sys.platform == "emscripten":
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        print(f"DEBUG: sys.path updated: {sys.path}")
    except Exception as e:
        print(f"DEBUG: Error updating sys.path: {e}")

import pygame
import platform

# Robust import for the logic module
try:
    import logic as game
except ImportError:
    import client.logic as game

# --- WebSocket Client Wrapper ---
# Standard 'websockets' library triggers 'Lock' attribute errors in Pygbag/Python 3.12.
# We use a wrapper to choose between standard websockets and native JS WebSockets.

class WSClient:
    def __init__(self):
        self.ws = None
        self.is_wasm = platform.system() == "Emscripten"
        self.messages = asyncio.Queue()
        self.closed = False

    async def connect(self, uri):
        if self.is_wasm:
            import js
            from pyodide.ffi import create_proxy
            
            print(f"DEBUG: JS WebSocket connecting to {uri}")
            self.ws = js.WebSocket.new(uri)
            self.ws.binaryType = "arraybuffer"
            
            connected_future = asyncio.get_running_loop().create_future()
            
            def on_open(event):
                print("DEBUG: JS WebSocket Open")
                if not connected_future.done():
                    connected_future.set_result(True)
            
            def on_message(event):
                # event.data is an ArrayBuffer when binaryType is arraybuffer
                # We need to convert it to bytes
                try:
                    data = event.data.to_py().tobytes()
                    self.messages.put_nowait(data)
                except Exception as e:
                    print(f"DEBUG: Error processing message: {e}")
                
            def on_error(event):
                print("DEBUG: JS WebSocket Error")
                if not connected_future.done():
                    connected_future.set_exception(Exception("WebSocket connection failed"))

            def on_close(event):
                print("DEBUG: JS WebSocket Closed")
                self.closed = True
                # Wake up the queue if waiting
                self.messages.put_nowait(None) 
                
            self.ws.onopen = create_proxy(on_open)
            self.ws.onmessage = create_proxy(on_message)
            self.ws.onerror = create_proxy(on_error)
            self.ws.onclose = create_proxy(on_close)
            
            await connected_future
            return self
        else:
            import websockets
            self.ws = await websockets.connect(uri)
            return self

    async def send(self, data):
        if self.is_wasm:
            # data is bytes (from pickle)
            self.ws.send(data)
        else:
            await self.ws.send(data)

    async def receive(self):
        if self.is_wasm:
            msg = await self.messages.get()
            if msg is None:
                raise Exception("WebSocket closed")
            return msg
        else:
            return await self.ws.recv()

    async def close(self):
        if self.ws:
            if self.is_wasm:
                self.ws.close()
            else:
                await self.ws.close()
            self.ws = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.receive()
        except:
            raise StopAsyncIteration

# --- CONSTANTS ---
WIDTH, HEIGHT = 900, 900
HEIGHT_SLICE = HEIGHT // 18
BOARD_OFFSET = 100
CELL_SIZE = 230
MINI_CELL_SIZE = 75
HIGHLIGHT_BORDER_WIDTH = 5
HIGHLIGHT_PADDING = 35

# Colors
BG_COLOR = (238, 238, 238)
TEXT_COLOR = (20, 20, 20)
FILL_COLOR = (50, 50, 50)
HIGHLIGHT_COLOR = (215, 205, 100)

# Network
HOST = "127.0.0.1"
PORT = 5555
PROTOCOL = "ws"

if platform.system() == "Emscripten":
    import js
    browser_host = js.window.location.hostname
    if browser_host and browser_host != "localhost" and browser_host != "127.0.0.1":
        HOST = browser_host
        if js.window.location.protocol == "https:":
            PROTOCOL = "wss"
        print(f"Detected browser environment, connecting to {HOST}")

# Initialize Pygame
pygame.init()
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ultimate Tic Tac Toe")
clock = pygame.time.Clock()

# Load Assets
try:
    BOARD_IMG = pygame.image.load("assets/board.png")
    x_img = pygame.image.load("assets/x.png")
    X_IMG = pygame.transform.scale(
        x_img, ((x_img.get_width() * 0.25), (x_img.get_height() * 0.25))
    )
    o_img = pygame.image.load("assets/o.png")
    O_IMG = pygame.transform.scale(
        o_img, ((o_img.get_width() * 0.245), (o_img.get_height() * 0.245))
    )
    WINNING_X_IMG = pygame.image.load("assets/light_x.png")
    WINNING_O_IMG = pygame.image.load("assets/light_o.png")
    DRAW_IMG = pygame.image.load("assets/draw.png")
    MINI_DRAW_IMG = pygame.transform.scale(
        DRAW_IMG, ((DRAW_IMG.get_width() * 0.245), (DRAW_IMG.get_height() * 0.245))
    )

    title_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 32)
    game_state_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 24)
    input_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 28)
except Exception as e:
    print(f"Warning: Could not load assets: {e}")
    # Create fallback surfaces if assets missing
    BOARD_IMG = pygame.Surface((772, 772))
    BOARD_IMG.fill((200, 200, 200))
    X_IMG = pygame.Surface((50, 50)); X_IMG.fill((255, 0, 0))
    O_IMG = pygame.Surface((50, 50)); O_IMG.fill((0, 0, 255))
    MINI_DRAW_IMG = pygame.Surface((20, 20)); MINI_DRAW_IMG.fill((100, 100, 100))
    WINNING_X_IMG = X_IMG
    WINNING_O_IMG = O_IMG
    DRAW_IMG = MINI_DRAW_IMG
    title_font = pygame.font.SysFont("Arial", 32)
    game_state_font = pygame.font.SysFont("Arial", 24)
    input_font = pygame.font.SysFont("Arial", 28)


# Global State
board = game.generate_board()
graphical_board = [
    [[[[None, None] for _ in range(3)] for _ in range(3)] for _ in range(3)]
    for _ in range(3)
]
to_move = ["X", None]
my_player = None
game_finished = False
game_status = "MENU"  # MENU, WAITING, GAME, FINISHED
winner = None
game_id = ""
input_text = ""
ws_client = None
error = ""


def get_player_image(player):
    if player == "X":
        return X_IMG
    if player == "O":
        return O_IMG
    if player == "D":
        return MINI_DRAW_IMG
    return None


def get_winner_image(winner_player):
    if winner_player == "X":
        return WINNING_X_IMG
    if winner_player == "O":
        return WINNING_O_IMG
    if winner_player == "D":
        return DRAW_IMG
    return None


async def connect_and_listen():
    global game_status, my_player, board, to_move, winner, error, ws_client
    
    if not ws_client:
        return

    try:
        async for message in ws_client:
            msg = pickle.loads(message)
            command = msg[0]
            
            if command == "START":
                board = msg[1]
                game_status = "GAME"
                
            elif command == "UPDATE":
                board = msg[1]
                to_move = msg[2]
                render_board_state()

            elif command == "GAME_OVER":
                winner = msg[1]
                game_status = "FINISHED"

            elif command == "OPPONENT_LEFT":
                error = "Opponent Disconnected"
                winner = None
                game_status = "FINISHED"
                
    except Exception as e:
        print(f"DEBUG: Connection listener error: {e}")
        error = "Disconnected"
        game_status = "MENU"
        ws_client = None


def render_board_state():
    global graphical_board
    mini_spacing = 55
    offset = 220

    for i in range(3):
        for j in range(3):
            center_x = j * CELL_SIZE + offset
            center_y = i * CELL_SIZE + offset

            # Check mini cells
            for mi in range(3):
                for mj in range(3):
                    mark = board[i][j][mi][mj]
                    if (
                        isinstance(mark, str)
                        and graphical_board[i][j][mi][mj][0] is None
                    ):
                        img = get_player_image(mark)
                        px = center_x + (mj - 1) * mini_spacing
                        py = center_y + (mi - 1) * mini_spacing
                        graphical_board[i][j][mi][mj] = [
                            img,
                            img.get_rect(center=(px, py)),
                        ]

            # Check for large cell winner
            if len(board[i][j]) > 3:
                winning_player = board[i][j][3]
                winning_img = get_winner_image(winning_player)
                if winning_img:
                    if len(graphical_board[i][j]) <= 3:
                        winning_rect = winning_img.get_rect(center=(center_x, center_y))
                        graphical_board[i][j] += [(winning_img, winning_rect)]


def draw_menu():
    global error
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Ultimate Tic Tac Toe v2", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 3)))
    
    create_btn = pygame.Rect(0, 0, 200, 50)
    create_btn.center = (WIDTH // 2, HEIGHT_SLICE * 7)
    pygame.draw.rect(SCREEN, FILL_COLOR, create_btn, border_radius=5)
    create_text = game_state_font.render("Create Game", True, BG_COLOR)
    SCREEN.blit(create_text, create_text.get_rect(center=create_btn.center))
    
    input_box = pygame.Rect(0, 0, 300, 50)
    input_box.center = (WIDTH // 2, HEIGHT_SLICE * 9)
    pygame.draw.rect(SCREEN, BG_COLOR, input_box, border_radius=5)
    pygame.draw.rect(SCREEN, TEXT_COLOR, input_box, 2, border_radius=5)
    txt_surface = input_font.render(input_text, True, TEXT_COLOR)
    SCREEN.blit(txt_surface, txt_surface.get_rect(center=input_box.center))
    if not input_text:
        placeholder = input_font.render("Enter Game ID", True, (150, 150, 150))
        SCREEN.blit(placeholder, placeholder.get_rect(center=input_box.center))
    
    join_btn = pygame.Rect(0, 0, 200, 50)
    join_btn.center = (WIDTH // 2, HEIGHT_SLICE * 11)
    pygame.draw.rect(SCREEN, FILL_COLOR, join_btn, border_radius=5)
    join_text = game_state_font.render("Join Game", True, BG_COLOR)
    SCREEN.blit(join_text, join_text.get_rect(center=join_btn.center))
    
    if error:
        error_text = game_state_font.render(error, True, TEXT_COLOR)
        SCREEN.blit(error_text, error_text.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 13)))
    
    quit_btn = pygame.Rect(0, 0, 200, 50)
    quit_btn.center = (WIDTH // 2, HEIGHT_SLICE * 15)
    pygame.draw.rect(SCREEN, FILL_COLOR, quit_btn, border_radius=5)
    quit_text = game_state_font.render("Quit", True, BG_COLOR)
    SCREEN.blit(quit_text, quit_text.get_rect(center=quit_btn.center))
    return create_btn, input_box, join_btn, quit_btn


def draw_waiting():
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Ultimate Tic Tac Toe v2", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 3)))
    screen_title = title_font.render("Waiting for Opponent...", True, TEXT_COLOR)
    SCREEN.blit(screen_title, screen_title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 6)))
    id_text = title_font.render(f"Game ID: {game_id}", True, TEXT_COLOR)
    SCREEN.blit(id_text, id_text.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 9)))
    cancel_btn = pygame.Rect(0, 0, 200, 50)
    cancel_btn.center = (WIDTH // 2, HEIGHT_SLICE * 11)
    pygame.draw.rect(SCREEN, FILL_COLOR, cancel_btn, border_radius=5)
    cancel_text = game_state_font.render("Cancel", True, BG_COLOR)
    SCREEN.blit(cancel_text, cancel_text.get_rect(center=cancel_btn.center))
    return cancel_btn


def draw_game_window():
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD_IMG, (64, 64))
    if to_move[1] is not None and game_status == "GAME" and my_player != "SPECTATOR":
        row, col = to_move[1]
        offset = 220
        center_x = col * CELL_SIZE + offset
        center_y = row * CELL_SIZE + offset
        highlight_size = CELL_SIZE - (HIGHLIGHT_PADDING * 2)
        pygame.draw.rect(SCREEN, HIGHLIGHT_COLOR, (int(center_x - highlight_size/2), int(center_y - highlight_size/2), highlight_size, highlight_size), HIGHLIGHT_BORDER_WIDTH)

    for i in range(3):
        for j in range(3):
            for mi in range(3):
                for mj in range(3):
                    cell = graphical_board[i][j][mi][mj]
                    if cell and cell[0]:
                        SCREEN.blit(cell[0], cell[1])
            if len(graphical_board[i][j]) > 3:
                item = graphical_board[i][j][3]
                SCREEN.blit(item[0], item[1])

    title = title_font.render("Ultimate Tic Tac Toe", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 1)))
    id_text = game_state_font.render(f"ID: {game_id}", True, TEXT_COLOR)
    id_rect = id_text.get_rect(topleft=(20, HEIGHT_SLICE * 1))
    id_rect.centery = HEIGHT_SLICE * 1
    SCREEN.blit(id_text, id_rect)

    if my_player in ["X", "O"]:
        you_text_str = "You: "
        you_img = X_IMG if my_player == "X" else O_IMG
        txt_surf = game_state_font.render(you_text_str, True, TEXT_COLOR)
        txt_rect = txt_surf.get_rect()
        end_x = WIDTH - 20
        y_pos = HEIGHT_SLICE * 1
        img_rect = you_img.get_rect()
        img_rect.midright = (end_x, y_pos)
        txt_rect.midright = (img_rect.left - 10, y_pos)
        SCREEN.blit(txt_surf, txt_rect)
        SCREEN.blit(you_img, img_rect)
    elif my_player == "SPECTATOR":
        spec_text = game_state_font.render("SPECTATING", True, TEXT_COLOR)
        spec_rect = spec_text.get_rect(midright=(WIDTH - 20, HEIGHT_SLICE * 1))
        SCREEN.blit(spec_text, spec_rect)

    status_text_str = ""
    status_img = None
    if game_status == "FINISHED":
        if error == "Opponent Disconnected":
            status_text_str = "Opponent Disconnected"
        elif winner == "D":
            status_text_str = "Game Over: DRAW"
        else:
            status_text_str = "Winner: "
            status_img = X_IMG if winner == "X" else O_IMG
    elif game_status == "GAME":
        status_text_str = ("Your Turn: " if to_move[0] == my_player else "Opponent Turn: ") if my_player != "SPECTATOR" else "Turn: "
        status_img = X_IMG if to_move[0] == "X" else O_IMG

    bottom_center = (WIDTH // 2, HEIGHT_SLICE * 17)
    if status_img:
        txt_surf = game_state_font.render(status_text_str, True, TEXT_COLOR)
        txt_rect = txt_surf.get_rect()
        total_width = txt_rect.width + status_img.get_width() + 10
        start_x = bottom_center[0] - (total_width // 2)
        txt_rect.topleft = (start_x, bottom_center[1] - txt_rect.height // 2)
        SCREEN.blit(txt_surf, txt_rect)
        img_rect = status_img.get_rect(); img_rect.midleft = (txt_rect.right + 10, txt_rect.centery)
        SCREEN.blit(status_img, img_rect)
    else:
        status = game_state_font.render(status_text_str, True, TEXT_COLOR)
        SCREEN.blit(status, status.get_rect(center=bottom_center))

    exit_btn = pygame.Rect(0, 0, 120, 40)
    exit_btn.center = (WIDTH - 80, HEIGHT_SLICE * 17)
    pygame.draw.rect(SCREEN, FILL_COLOR, exit_btn, border_radius=5)
    exit_text = game_state_font.render("Exit", True, BG_COLOR)
    SCREEN.blit(exit_text, exit_text.get_rect(center=exit_btn.center))
    return exit_btn


async def perform_handshake(command, payload=None):
    global game_id, my_player, game_status, error, ws_client, board, to_move
    try:
        uri = f"{PROTOCOL}://{HOST}:{PORT}"
        ws_client = WSClient()
        await ws_client.connect(uri)
    except Exception as e:
        print(f"DEBUG: Handshake connection error: {e}")
        error = f"Conn failed: {e}"
        return False

    if command == "CREATE":
        await ws_client.send(pickle.dumps(("CREATE",)))
        try:
            message = await ws_client.receive()
            resp = pickle.loads(message)
            game_id = resp[1]
            my_player = resp[2]
            game_status = "WAITING"
            return True
        except Exception as e:
            error = f"Handshake err: {e}"
    elif command == "JOIN":
        await ws_client.send(pickle.dumps(("JOIN", payload)))
        try:
            message = await ws_client.receive()
            resp = pickle.loads(message)
            if resp[0] == "ERROR":
                error = resp[1]
                return False
            elif resp[0] == "JOINED":
                my_player = resp[1]
                game_id = payload
                game_status = "GAME"
                return True
        except Exception as e:
            error = f"Handshake err: {e}"
    if ws_client:
        await ws_client.close()
        ws_client = None
    return False


def reset_game():
    global board, graphical_board, to_move, my_player, game_finished, game_status, winner, game_id, input_text, error, ws_client
    board = game.generate_board()
    graphical_board = [[[[None, None] for _ in range(3)] for _ in range(3)] for _ in range(3)] for _ in range(3)]
    to_move = ["X", None]
    my_player = None
    game_finished = False
    game_status = "MENU"
    winner = None
    game_id = ""
    error = ""
    input_text = ""
    if ws_client:
        asyncio.create_task(ws_client.close())
        ws_client = None


async def main():
    global game_status, input_text, my_player, game_id, board, to_move
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        if game_status == "MENU":
            create_btn, input_box, join_btn, quit_btn = draw_menu()
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if create_btn.collidepoint(event.pos):
                        if await perform_handshake("CREATE"):
                            asyncio.create_task(connect_and_listen())
                    elif join_btn.collidepoint(event.pos):
                        if input_text:
                            if await perform_handshake("JOIN", input_text):
                                asyncio.create_task(connect_and_listen())
                    elif quit_btn.collidepoint(event.pos):
                        running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif len(input_text) < 10:
                        input_text += event.unicode
        elif game_status == "WAITING":
            cancel_btn = draw_waiting()
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and cancel_btn.collidepoint(event.pos):
                    reset_game()
        else:
            exit_btn = draw_game_window()
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if exit_btn.collidepoint(event.pos):
                        reset_game()
                        continue
                    if game_status == "GAME" and my_player == to_move[0] and my_player != "SPECTATOR":
                        x, y = pygame.mouse.get_pos()
                        large_col, large_row = (x - BOARD_OFFSET) // CELL_SIZE, (y - BOARD_OFFSET) // CELL_SIZE
                        if 0 <= large_col <= 2 and 0 <= large_row <= 2:
                            rel_x, rel_y = (x - BOARD_OFFSET) % 230, (y - BOARD_OFFSET) % 230
                            mini_col, mini_row = rel_x // MINI_CELL_SIZE, rel_y // MINI_CELL_SIZE
                            if mini_col <= 2 and mini_row <= 2:
                                move = (large_row, large_col, mini_row, mini_col)
                                try:
                                    if ws_client:
                                        await ws_client.send(pickle.dumps(move))
                                except Exception as e:
                                    print(f"Error sending move: {e}")
        pygame.display.update()
        await asyncio.sleep(0)
        clock.tick(30)
    if ws_client:
        await ws_client.close()
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
