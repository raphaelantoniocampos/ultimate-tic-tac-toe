import pickle
import socket
import sys
import threading

import pygame

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

# Global State
board = game.generate_board()
graphical_board = [
    [[[[None, None] for _ in range(3)] for _ in range(3)] for _ in range(3)]
    for _ in range(3)
]
to_move = ["X", None]
my_player = None
game_finished = False
winner = None

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


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


def draw_game_window():
    # Clear the screen and draw the main board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD_IMG, (64, 64))

    # Highlight valid move area
    if to_move[1] is not None and not game_finished:
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
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 18))
    SCREEN.blit(title, title_rect)

    status_text = f"You are: {my_player}"
    if game_finished:
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

    pygame.display.update()


def receive_data():
    global board, to_move, my_player, game_finished, winner
    while True:
        try:
            data = client_socket.recv(4096 * 4)
            if not data:
                break
            msg = pickle.loads(data)

            if msg[0] == "WELCOME":
                my_player = msg[1]
                print(f"Connected as Player {my_player}")
                pygame.display.set_caption(f"Ultimate Tic Tac Toe - Player {my_player}")

            elif msg[0] == "UPDATE":
                board = msg[1]
                to_move = msg[2]
                render_board_state()

            elif msg[0] == "GAME_OVER":
                winner = msg[1]
                game_finished = True
                print(f"Game Over. Winner: {winner}")

        except Exception as e:
            print(f"Connection error: {e}")
            break


def main():
    try:
        client_socket.connect((HOST, PORT))
    except:
        print("Could not connect to server.")
        return

    thread = threading.Thread(target=receive_data)
    thread.daemon = True
    thread.start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and not game_finished
                and my_player == to_move[0]
            ):
                x, y = pygame.mouse.get_pos()

                # Input mapping logic from main.py
                large_col = (x - BOARD_OFFSET) // CELL_SIZE
                large_row = (y - BOARD_OFFSET) // CELL_SIZE

                if 0 <= large_col <= 2 and 0 <= large_row <= 2:
                    rel_x = (x - BOARD_OFFSET) % 230
                    rel_y = (y - BOARD_OFFSET) % 230
                    mini_col = rel_x // MINI_CELL_SIZE
                    mini_row = rel_y // MINI_CELL_SIZE

                    if mini_col <= 2 and mini_row <= 2:
                        # Send move
                        move = (large_row, large_col, mini_row, mini_col)
                        try:
                            client_socket.send(pickle.dumps(move))
                        except Exception as e:
                            print(f"Error sending move: {e}")

        draw_game_window()

    client_socket.close()
    sys.exit()


if __name__ == "__main__":
    main()
