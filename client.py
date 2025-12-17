import pickle
import socket
import sys
import threading

import pygame
import subprocess

import game

# --- CONSTANTS ---
WIDTH, HEIGHT = 900, 900
BG_COLOR = (214, 201, 227)
BOARD_OFFSET = 100
CELL_SIZE = 230
MINI_CELL_SIZE = 75
HIGHLIGHT_COLOR = (255, 255, 100)
HIGHLIGHT_BORDER_WIDTH = 5
HIGHLIGHT_PADDING = 35

HOST = "127.0.0.1"
PORT = 5555

# Initialize Pygame
pygame.init()
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ultimate Tic Tac Toe")

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
client_socket = None

# client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


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


def copy_to_clipboard(text):
    try:
        subprocess.run(['clip'], input=text.strip().encode(
            'utf-16'), check=True)
        print("Copied to clipboard!")
    except Exception as e:
        print(f"Clipboard failed: {e}")


def connect_and_listen():
    global game_status, my_player, board, to_move, winner
    while True:
        try:
            data = client_socket.recv(4096 * 4)
            if not data:
                break
            msg = pickle.loads(data)
            command = msg[0]
            if command == "CREATED":
                # ("CREATED", game_id, role)
                # Actually main thread handles the socket for create/join first
                # But if we move logic here, we need to be careful.
                # Let's keep handshake in main thread for simplicity before starting this listener.
                pass

            elif command == "JOINED":
                # Same as above, handshake handled in main
                pass
            elif command == "START":
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
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Ultimate Tic Tac Toe", True, (20, 20, 20))
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 4)))
    # Create Button
    create_btn = pygame.Rect(0, 0, 200, 50)
    create_btn.center = (WIDTH // 2, HEIGHT // 2 - 60)
    pygame.draw.rect(SCREEN, (50, 50, 50), create_btn, border_radius=5)
    create_text = game_state_font.render("Create Game", True, (255, 255, 255))
    SCREEN.blit(create_text, create_text.get_rect(center=create_btn.center))
    # Join Input
    input_box = pygame.Rect(0, 0, 300, 50)
    input_box.center = (WIDTH // 2, HEIGHT // 2 + 20)
    pygame.draw.rect(SCREEN, (255, 255, 255), input_box, border_radius=5)
    pygame.draw.rect(SCREEN, (0, 0, 0), input_box, 2, border_radius=5)

    txt_surface = input_font.render(input_text, True, (0, 0, 0))
    # Clip text if too long? For now just let it overflow or be centered
    SCREEN.blit(txt_surface, txt_surface.get_rect(center=input_box.center))

    # Placeholder text if empty
    if not input_text:
        placeholder = input_font.render("Enter Game ID", True, (150, 150, 150))
        SCREEN.blit(placeholder, placeholder.get_rect(center=input_box.center))
    # Join Button
    join_btn = pygame.Rect(0, 0, 200, 50)
    join_btn.center = (WIDTH // 2, HEIGHT // 2 + 100)
    pygame.draw.rect(SCREEN, (50, 50, 50), join_btn, border_radius=5)
    join_text = game_state_font.render("Join Game", True, (255, 255, 255))
    SCREEN.blit(join_text, join_text.get_rect(center=join_btn.center))
    return create_btn, input_box, join_btn


def draw_waiting():
    SCREEN.fill(BG_COLOR)
    title = title_font.render("Waiting for Opponent...", True, (20, 20, 20))
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3)))
    id_text = title_font.render(f"Game ID: {game_id}", True, (20, 20, 20))
    SCREEN.blit(id_text, id_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    copy_btn = pygame.Rect(0, 0, 200, 50)
    copy_btn.center = (WIDTH // 2, HEIGHT // 2 + 80)
    pygame.draw.rect(SCREEN, (50, 50, 50), copy_btn, border_radius=5)
    copy_text = game_state_font.render("Copy ID", True, (255, 255, 255))
    SCREEN.blit(copy_text, copy_text.get_rect(center=copy_btn.center))
    return copy_btn


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
    title = title_font.render("Ultimate Tic Tac Toe", True, (20, 20, 20))
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 18)))

    status_text = f"You are: {my_player}"

    if my_player == "SPECTATOR":
        status_text = "Spectating Mode"
        if game_status == "FINISHED":
            if winner == "D":
                status_text += " - DRAW"
            else:
                status_text += f" - {winner} WINS!"

    elif game_status == "FINISHED":
        if winner == "D":
            status_text = "Game Over: DRAW"
        else:
            status_text = f"Game Over: {winner} WINS!"
    elif to_move[0] == my_player:
        status_text += " (YOUR TURN)"
    else:
        status_text += " (OPPONENT'S TURN)"

    status = game_state_font.render(status_text, True, (20, 20, 20))
    SCREEN.blit(status, status.get_rect(center=(WIDTH // 2, HEIGHT - 50)))


def main():
    global game_status, input_text, client_socket, my_player, game_id, board, to_move

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
    except:
        print("Could not connect to server.")
        return

    # thread = threading.Thread(target=receive_data)
    # thread.daemon = True
    # thread.start()
    clock = pygame.time.Clock()

    running = True
    while running:
        # for event in pygame.event.get():
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            # if (
            #     event.type == pygame.MOUSEBUTTONDOWN
            #     and not game_finished
            #     and my_player == to_move[0]
            # ):
            #     x, y = pygame.mouse.get_pos()
        if game_status == "MENU":
            create_btn, input_box, join_btn = draw_menu()

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if create_btn.collidepoint(event.pos):
                        # Send CREATE
                        client_socket.send(pickle.dumps(("CREATE",)))
                        resp = pickle.loads(client_socket.recv(4096))
                        # ("CREATED", game_id, role)
                        game_id = resp[1]
                        my_player = resp[2]
                        game_status = "WAITING"

                        # Start listener thread
                        thread = threading.Thread(
                            target=connect_and_listen, daemon=True)
                        thread.start()

                # # Input mapping logic from main.py
                # large_col = (x - BOARD_OFFSET) // CELL_SIZE
                # large_row = (y - BOARD_OFFSET) // CELL_SIZE
                    elif join_btn.collidepoint(event.pos):
                        if input_text:
                            # Send JOIN
                            client_socket.send(
                                pickle.dumps(("JOIN", input_text)))
                            resp = pickle.loads(client_socket.recv(4096))

                            if resp[0] == "ERROR":
                                print(f"Error: {resp[1]}")
                                # Optional: Show error on UI
                            else:
                                if resp[0] == "JOINED":
                                    my_player = resp[1]  # "O" or "SPECTATOR"
                                    game_id = input_text

                                    if my_player == "SPECTATOR":
                                        # Expecting UPDATE next or handle it in thread?
                                        # Let's start thread, but thread loop handles messages.
                                        # Handshake is done.
                                        game_status = "GAME"
                                    else:
                                        # Player O joined, waiting for START
                                        # Wait, if I am O, game starts immediately usually?
                                        # Server broadcasts START after O joins.
                                        game_status = "GAME"  # Or waiting for START?
                                        # Actually role O receives START in thread.

                                    thread = threading.Thread(
                                        target=connect_and_listen, daemon=True)
                                    thread.start()
                # if 0 <= large_col <= 2 and 0 <= large_row <= 2:
                #     rel_x = (x - BOARD_OFFSET) % 230
                #     rel_y = (y - BOARD_OFFSET) % 230
                #     mini_col = rel_x // MINI_CELL_SIZE
                #     mini_row = rel_y // MINI_CELL_SIZE
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        if len(input_text) < 10:
                            input_text += event.unicode

        elif game_status == "WAITING":
            copy_btn = draw_waiting()
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if copy_btn.collidepoint(event.pos):
                        copy_to_clipboard(game_id)
                    # if mini_col <= 2 and mini_row <= 2:
                    #     # Send move
                    #     move = (large_row, large_col, mini_row, mini_col)
                    #     try:
                    #         client_socket.send(pickle.dumps(move))
                    #     except Exception as e:
                    #         print(f"Error sending move: {e}")
        else:  # GAME or FINISHED
            for event in events:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and game_status == "GAME"
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
                            move = (large_row, large_col, mini_row, mini_col)
                            try:
                                client_socket.send(pickle.dumps(move))
                            except:
                                pass

            draw_game_window()

    # client_socket.close()
        pygame.display.update()
        clock.tick(30)
    try:
        client_socket.close()
    except:
        pass
    sys.exit()


if __name__ == "__main__":
    main()
