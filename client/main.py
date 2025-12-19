import asyncio
import pickle
import socket
import threading

import pygame
import platform
import game

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
# Default to localhost for local development
HOST = "127.0.0.1"
PORT = 5555

# Detect if we are running in a browser
if platform.system() == "Emscripten":
    import js
    # Get the hostname from the browser's location
    browser_host = js.window.location.hostname
    if browser_host and browser_host != "localhost" and browser_host != "127.0.0.1":
        HOST = browser_host
        # Note: In browser environment, you might need to connect via WebSockets 
        # or use a proxy. Pygbag handles some of this, but HOST must point to the server.
        print(f"Detected browser environment, connecting to {HOST}")

# Initialize Pygame
pygame.init()
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ultimate Tic Tac Toe")
clock = pygame.time.Clock()

# Load Assets
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
client_reader = None
client_writer = None
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
    global game_status, my_player, board, to_move, winner, error
    while True:
        try:
            # Data length is not provided, but we can read until EOF or use a large buffer
            # pickle usually needs the full data.
            # For simplicity, we assume the server sends encapsulated packets if needed, 
            # but here we follow the existing pickle logic.
            data = await client_reader.read(4096 * 4)
            if not data:
                break
            msg = pickle.loads(data)
            command = msg[0]
            if command == "START":
                # ("START", board)
                board = msg[1]
                game_status = "GAME"

            elif command == "UPDATE":
                # ("UPDATE", board, to_move)
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
            print(f"Connection error: {e}")
            break


def render_board_state():
    global graphical_board
    mini_spacing = 55
    offset = 220

    for i in range(3):
        for j in range(3):
            # Coordinates for center of large cell
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
                    winning_rect = winning_img.get_rect(
                        center=(
                            center_x,
                            center_y,
                        )
                    )
                    graphical_board[i][j] += [(winning_img, winning_rect)]


def draw_menu():
    global error
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Ultimate Tic Tac Toe", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 3)))
    # Create Button
    create_btn = pygame.Rect(0, 0, 200, 50)
    create_btn.center = (WIDTH // 2, HEIGHT_SLICE * 7)
    pygame.draw.rect(SCREEN, FILL_COLOR, create_btn, border_radius=5)
    create_text = game_state_font.render("Create Game", True, BG_COLOR)
    SCREEN.blit(create_text, create_text.get_rect(center=create_btn.center))
    # Join Input
    input_box = pygame.Rect(0, 0, 300, 50)
    input_box.center = (WIDTH // 2, HEIGHT_SLICE * 9)
    pygame.draw.rect(SCREEN, BG_COLOR, input_box, border_radius=5)
    pygame.draw.rect(SCREEN, TEXT_COLOR, input_box, 2, border_radius=5)

    txt_surface = input_font.render(input_text, True, TEXT_COLOR)
    SCREEN.blit(txt_surface, txt_surface.get_rect(center=input_box.center))

    # Placeholder text if empty
    if not input_text:
        placeholder = input_font.render("Enter Game ID", True, (150, 150, 150))
        SCREEN.blit(placeholder, placeholder.get_rect(center=input_box.center))
    # Join Button
    join_btn = pygame.Rect(0, 0, 200, 50)
    join_btn.center = (WIDTH // 2, HEIGHT_SLICE * 11)
    pygame.draw.rect(SCREEN, FILL_COLOR, join_btn, border_radius=5)
    join_text = game_state_font.render("Join Game", True, BG_COLOR)
    SCREEN.blit(join_text, join_text.get_rect(center=join_btn.center))
    # Error response
    if error:
        error_text = game_state_font.render(error, True, TEXT_COLOR)
        SCREEN.blit(error_text, error_text.get_rect(
            center=(WIDTH // 2, HEIGHT_SLICE * 13)))
    # Quit Button
    quit_btn = pygame.Rect(0, 0, 200, 50)
    quit_btn.center = (WIDTH // 2, HEIGHT_SLICE * 15)
    pygame.draw.rect(SCREEN, FILL_COLOR, quit_btn, border_radius=5)
    quit_text = game_state_font.render("Quit", True, BG_COLOR)
    SCREEN.blit(quit_text, quit_text.get_rect(center=quit_btn.center))
    return create_btn, input_box, join_btn, quit_btn


def draw_waiting():
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Ultimate Tic Tac Toe", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 3)))
    screen_title = title_font.render(
        "Waiting for Opponent...", True, TEXT_COLOR)
    SCREEN.blit(screen_title, screen_title.get_rect(
        center=(WIDTH // 2, HEIGHT_SLICE * 6)),)
    id_text = title_font.render(f"Game ID: {game_id}", True, TEXT_COLOR)
    SCREEN.blit(id_text, id_text.get_rect(
        center=(WIDTH // 2, HEIGHT_SLICE * 9)))

    # Cancel Button
    cancel_btn = pygame.Rect(0, 0, 200, 50)
    cancel_btn.center = (WIDTH // 2, HEIGHT_SLICE * 11)
    pygame.draw.rect(SCREEN, FILL_COLOR, cancel_btn, border_radius=5)
    cancel_text = game_state_font.render("Cancel", True, BG_COLOR)
    SCREEN.blit(cancel_text, cancel_text.get_rect(center=cancel_btn.center))
    return cancel_btn


def draw_game_window():
    # Clear the screen and draw the main board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD_IMG, (64, 64))

    # Highlight valid move area
    if to_move[1] is not None and game_status == "GAME" and my_player != "SPECTATOR":
        row, col = to_move[1]
        offset = 220
        center_x = col * CELL_SIZE + offset
        center_y = row * CELL_SIZE + offset
        highlight_size = CELL_SIZE - (HIGHLIGHT_PADDING * 2)
        pygame.draw.rect(
            surface=SCREEN,
            color=HIGHLIGHT_COLOR,
            rect=(
                int(center_x - (highlight_size / 2)),
                int(center_y - (highlight_size / 2)),
                highlight_size,
                highlight_size,
            ),
            width=HIGHLIGHT_BORDER_WIDTH,
        )

    # Draw marks
    for i in range(3):
        for j in range(3):
            for mi in range(3):
                for mj in range(3):
                    cell = graphical_board[i][j][mi][mj]
                    if cell is not None and cell[0] is not None:
                        SCREEN.blit(cell[0], cell[1])

            # Draw large winner if exists
            if len(graphical_board[i][j]) > 3:
                # The stored item is (img, rect)
                item = graphical_board[i][j][3]
                SCREEN.blit(item[0], item[1])

    # UI Text
    # Title roughly consistent
    title = title_font.render("Ultimate Tic Tac Toe", True, TEXT_COLOR)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT_SLICE * 1)))
    
    # Game ID - Top Left
    id_text = game_state_font.render(f"ID: {game_id}", True, TEXT_COLOR)
    id_rect = id_text.get_rect(topleft=(20, HEIGHT_SLICE * 1))
    # Align visually with title center Y or just place securely
    id_rect.centery = HEIGHT_SLICE * 1
    SCREEN.blit(id_text, id_rect)

    # "You are" - Top Right
    if my_player in ["X", "O"]:
        you_text_str = "You: "
        you_img = X_IMG if my_player == "X" else O_IMG
        
        txt_surf = game_state_font.render(you_text_str, True, TEXT_COLOR)
        txt_rect = txt_surf.get_rect()
        
        # Position top right
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


    # Bottom Status Construction
    status_text_str = ""
    status_img = None
    
    if game_status == "FINISHED":
        if error == "Opponent Disconnected":
            status_text_str = "Opponent Disconnected"
        elif winner == "D":
            status_text_str = "Game Over: DRAW"
        else:
            status_text_str = "Winner: "
            if winner == "X":
                status_img = X_IMG
            elif winner == "O":
                status_img = O_IMG
    elif game_status == "GAME":
        if my_player == "SPECTATOR":
             status_text_str = f"Turn: "
        else:
            if to_move[0] == my_player:
                status_text_str = "Your Turn (" 
            else:
                status_text_str = "Opponent Turn ("
        
        # The image for whose turn it is
        if to_move[0] == "X":
            status_img = X_IMG
        else:
            status_img = O_IMG
            
        if my_player != "SPECTATOR":
            # Add closing parenthesis via a separate text or just imply it by proximity?
            # Let's simplify: "Turn: [Image]" is cleanest, but user wants "Your Turn"
            # Let's do: "Your Turn" [Image] or "Opponent Turn" [Image]
            if to_move[0] == my_player:
                 status_text_str = "Your Turn: "
            else:
                 status_text_str = "Opponent Turn: "
    

    # Render Bottom Status
    bottom_center = (WIDTH // 2, HEIGHT_SLICE * 17)
    
    if status_img:
        # Text left of image
        txt_surf = game_state_font.render(status_text_str, True, TEXT_COLOR)
        txt_rect = txt_surf.get_rect()
        
        # Calculate total width to center
        total_width = txt_rect.width + status_img.get_width() + 10
        start_x = bottom_center[0] - (total_width // 2)
        
        # Blit Text
        txt_rect.topleft = (start_x, bottom_center[1] - txt_rect.height // 2)
        SCREEN.blit(txt_surf, txt_rect)
        
        # Blit Image
        img_rect = status_img.get_rect()
        img_rect.midleft = (txt_rect.right + 10, txt_rect.centery)
        SCREEN.blit(status_img, img_rect)
            
    else:
        # Just text
        status = game_state_font.render(status_text_str, True, TEXT_COLOR)
        SCREEN.blit(status, status.get_rect(center=bottom_center))

    # Exit Button 
    # Use HEIGHT_SLICE logic
    exit_btn = pygame.Rect(0, 0, 120, 40)
    # Bottom Right? or Center Bottom below status?
    # User asked for consistent positioning.
    # Previous it was (WIDTH - 80, HEIGHT - 40).
    # Let's keep it bottom right or move to bottom center below status (might be too crowded).
    # Let's put it on slice 17 but far right? or Slice 16?
    # Actually, let's stick to bottom right but use slices for Y margin reference slightly.
    # HEIGHT = 18 slices. Slice 17 is center of bottom status.
    # Slice 17 y is 850.
    exit_btn.center = (WIDTH - 80, HEIGHT_SLICE * 17)
    
    pygame.draw.rect(SCREEN, FILL_COLOR, exit_btn, border_radius=5)
    exit_text = game_state_font.render("Exit", True, BG_COLOR)
    SCREEN.blit(exit_text, exit_text.get_rect(center=exit_btn.center))
    
    return exit_btn


async def perform_handshake(command, payload=None):
    global game_id, my_player, game_status, error, client_reader, client_writer, board, to_move
    
    try:
        client_reader, client_writer = await asyncio.open_connection(HOST, PORT)
    except Exception as e:
        print(f"Could not connect to server: {e}")
        return False

    if command == "CREATE":
        client_writer.write(pickle.dumps(("CREATE",)))
        await client_writer.drain()
        
        data = await client_reader.read(4096)
        resp = pickle.loads(data)
        # ("CREATED", game_id, role)
        game_id = resp[1]
        my_player = resp[2]
        game_status = "WAITING"
        return True

    elif command == "JOIN":
        client_writer.write(pickle.dumps(("JOIN", payload)))
        await client_writer.drain()
        
        data = await client_reader.read(4096)
        resp = pickle.loads(data)

        if resp[0] == "ERROR":
            error = resp[1]
            return False
        else:
            if resp[0] == "JOINED":
                my_player = resp[1]  # "O" or "SPECTATOR"
                game_id = payload
                game_status = "GAME"
                return True
    return False


def reset_game():
    global board, graphical_board, to_move, my_player, game_finished, game_status, winner, game_id, input_text, error, client_writer
    
    board = game.generate_board()
    graphical_board = [
        [[[[None, None] for _ in range(3)]
          for _ in range(3)] for _ in range(3)]
        for _ in range(3)
    ]
    to_move = ["X", None]
    my_player = None
    game_finished = False
    game_status = "MENU"
    winner = None
    game_id = ""
    error = ""
    input_text = ""
    
    if client_writer:
        try:
            client_writer.close()
        except:
            pass


async def main():
    global game_status, input_text, client_socket, my_player, game_id, board, to_move

    clock = pygame.time.Clock()

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
                            # Start listener task
                            asyncio.create_task(connect_and_listen())

                    elif join_btn.collidepoint(event.pos):
                        if input_text:
                            if await perform_handshake("JOIN", input_text):
                                asyncio.create_task(connect_and_listen())

                    elif quit_btn.collidepoint(event.pos):
                        # Quit game
                        running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        if len(input_text) < 10:
                            input_text += event.unicode

        elif game_status == "WAITING":
            cancel_btn = draw_waiting()
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if cancel_btn.collidepoint(event.pos):
                        reset_game()
                        
        else:  # GAME or FINISHED
            exit_btn = draw_game_window()
            
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if exit_btn.collidepoint(event.pos):
                        reset_game()
                        continue  # Skip move logic

                    if (
                        game_status == "GAME"
                        and my_player == to_move[0]
                        and my_player != "SPECTATOR"
                    ):
                        x, y = pygame.mouse.get_pos()
                        # Input logic
                        large_col = (x - BOARD_OFFSET) // CELL_SIZE
                        large_row = (y - BOARD_OFFSET) // CELL_SIZE

                        if 0 <= large_col <= 2 and 0 <= large_row <= 2:
                            rel_x = (x - BOARD_OFFSET) % 230
                            rel_y = (y - BOARD_OFFSET) % 230
                            mini_col = rel_x // MINI_CELL_SIZE
                            mini_row = rel_y // MINI_CELL_SIZE

                            if mini_col <= 2 and mini_row <= 2:
                                move = (large_row, large_col,
                                        mini_row, mini_col)
                                try:
                                    client_writer.write(pickle.dumps(move))
                                    await client_writer.drain()
                                except Exception as e:
                                    print(f"Error sending move ({move}): {e}")
                                    pass

        pygame.display.update()
        await asyncio.sleep(0)
        clock.tick(30)
    try:
        if client_writer:
            client_writer.close()
            await client_writer.wait_closed()
    except Exception as e:
        print(f"Error closing socket: {e}")
        pass
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
