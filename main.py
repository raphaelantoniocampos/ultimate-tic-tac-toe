import copy
import sys

import pygame

# --- CONSTANTS ---
WIDTH, HEIGHT = 900, 900

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))

BG_COLOR = (214, 201, 227)

INIT_GRAPHICAL_BOARD = [
    [[[[None, None] for _ in range(3)] for _ in range(3)] for _ in range(3)]
    for _ in range(3)
]

# Load assets
BOARD = pygame.image.load("assets/board.png")

x_img = pygame.image.load("assets/X.png")
X_IMG = pygame.transform.scale(
    x_img,
    ((x_img.get_width() * 0.25), (x_img.get_height() * 0.25)),
)
o_img = pygame.image.load("assets/O.png")
O_IMG = pygame.transform.scale(
    o_img,
    ((o_img.get_width() * 0.245), (o_img.get_height() * 0.245)),
)

WINNING_X_IMG = pygame.image.load("assets/light_x.png")
WINNING_O_IMG = pygame.image.load("assets/light_o.png")
DRAW_IMG = pygame.image.load("assets/draw.png")

BOARD_OFFSET = 100
CELL_SIZE = 230

MINI_CELL_SIZE = 75

# global board
graphical_board = copy.deepcopy(INIT_GRAPHICAL_BOARD)


def main():
    pygame.init()

    pygame.display.set_caption("Ultimate Tic Tac Toe!")

    # Start game variables
    to_move = ["X", None]  # Who starts and playable area limits
    game_finished = False

    # board = copy.deepcopy(INIT_BOARD)
    board = generate_board()

    # Draw board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD, (64, 64))

    pygame.display.update()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            # Player action
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not game_finished:
                    # Adds X/O
                    board, to_move = add_XO(board, to_move)

                    render_board(board, X_IMG, O_IMG)

                    if not to_move[0]:
                        break

                    # winner = check_board_winner(board)
                    # print(winner)
                    # if winner is not None:
                    #     game_finished = True

                else:
                    # Restarts game next click
                    # board = copy.deepcopy(INIT_BOARD)
                    board = generate_board()
                    global graphical_board
                    graphical_board = copy.deepcopy(INIT_GRAPHICAL_BOARD)
                    to_move = ["X", None]
                    game_finished = False

        # Draws the game
        draw_game(board)

        # Refreshes the screen
        pygame.display.update()


def add_XO(board, to_move):
    x, y = pygame.mouse.get_pos()

    # Identify the large cell (0, 1 or 2)
    # Subtract the offset to align the click with the grid
    # Divide by cell size
    large_col = (x - BOARD_OFFSET) // CELL_SIZE
    large_row = (y - BOARD_OFFSET) // CELL_SIZE

    if not (0 <= large_col <= 2 and 0 <= large_row <= 2):
        return board, to_move

    # Identify the mini-cell within the large cell (0, 1 or 2)
    # Calculate the relative position of the mouse within the large cell
    rel_x = (x - BOARD_OFFSET) % 230
    rel_y = (y - BOARD_OFFSET) % 230

    # Divide relative position by mini-cell size
    mini_col = rel_x // MINI_CELL_SIZE
    mini_row = rel_y // MINI_CELL_SIZE

    if mini_col > 2:
        mini_col = 2
    if mini_row > 2:
        mini_row = 2

    # DEBUG
    print(
        f"MINI BOARD: [{large_row}][{large_col}] | MINI-CELL [{mini_row}][{mini_col}]"
    )

    # Determine valid move
    if to_move[1]:
        if to_move[1] != (large_row, large_col):
            return board, to_move

    mini_board = board[large_row][large_col]
    if isinstance(mini_board, str):
        to_move[1] = None
        return board, to_move

    # Update the board
    if isinstance(mini_board, list):
        if isinstance(mini_board[mini_row][mini_col], int):
            mini_board[mini_row][mini_col] = to_move[0]

            # Switch player
            to_move[0] = "O" if to_move[0] == "X" else "X"
            to_move[1] = (mini_row, mini_col)
            if isinstance(board[mini_row][mini_col], str):
                to_move[1] = None

    # Check for mini board winner
    winner = check_board_winner(mini_board)
    if winner:
        to_move[1] = None
        board[large_row][large_col] = winner

    return board, to_move


def render_board(board, x_mini_img, o_mini_img):
    global graphical_board
    mini_spacing = 55
    offset = 220

    for i in range(3):
        for j in range(3):
            center_x = j * CELL_SIZE + offset
            center_y = i * CELL_SIZE + offset

            # If board contains mini board
            if isinstance(board[i][j], list):
                for mi in range(3):
                    for mj in range(3):
                        mark = board[i][j][mi][mj]

                        if (
                            isinstance(mark, str)
                            and graphical_board[i][j][mi][mj][0] is None
                        ):
                            img = x_mini_img if mark == "X" else o_mini_img
                            px = center_x + (mj - 1) * mini_spacing
                            py = center_y + (mi - 1) * mini_spacing

                            graphical_board[i][j][mi][mj] = [
                                img,
                                img.get_rect(center=(px, py)),
                            ]

            # if board is won or draw
            else:
                winning_img = get_winning_img(board[i][j])
                if winning_img:
                    winning_rect = winning_img.get_rect(center=(center_x, center_y))
                    graphical_board[i][j] = (winning_img, winning_rect)


def get_winning_img(winner):
    global WINNING_X_IMG, WINNING_O_IMG

    if winner == "X":
        return WINNING_X_IMG
    elif winner == "O":
        return WINNING_O_IMG
    elif winner == "D":
        return DRAW_IMG
    else:
        return None


def check_board_winner(board):
    # Check rows and columns
    for mi in range(3):
        # Lines
        if board[mi][0] == board[mi][1] == board[mi][2] and board[mi][0] not in [
            0,
            1,
            2,
        ]:
            winner = board[mi][0]
            return winner

        # Columns
        if board[0][mi] == board[1][mi] == board[2][mi] and board[0][mi] not in [
            0,
            3,
            6,
        ]:
            winner = board[0][mi]
            return winner

    # Check diagonals

    # Diagonal (0,0), (1,1), (2,2)
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] not in [0]:
        winner = board[0][0]
        return winner

    # Diagonal (0,2), (1,1), (2,0)
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] not in [2]:
        winner = board[0][2]
        return winner

    # Check draw
    for row in board:
        for cell in row:
            if cell not in ["X", "O"]:
                return None

    return "D"


def draw_game(board):
    global graphical_board
    # Clear the screen and draw the main board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD, (64, 64))

    # Scroll through large cells
    for i in range(3):
        for j in range(3):
            # If the large cell contains a list, we draw the mini cells
            if isinstance(graphical_board[i][j], list):
                # Case where graphical_board[i][j] is a 3x3 matrix of mini-cells
                for mi in range(3):
                    for mj in range(3):
                        # Checks if there is an image and a rect defined
                        if (
                            graphical_board[i][j][mi][mj] is not None
                            and graphical_board[i][j][mi][mj][0] is not None
                        ):
                            SCREEN.blit(
                                graphical_board[i][j][mi][mj][0],
                                graphical_board[i][j][mi][mj][1],
                            )

            # If the large block was won by someone
            elif graphical_board[i][j][0] is not None:
                SCREEN.blit(graphical_board[i][j][0], graphical_board[i][j][1])


def generate_board():
    board = []
    for i in range(3):
        line = []
        for j in range(3):
            mini_board = []
            counter = 0
            for mi in range(3):
                mini_line = []
                for mj in range(3):
                    mini_line.append(counter)
                    counter += 1
                mini_board.append(mini_line)

            line.append(mini_board)

        board.append(line)
    return board


if __name__ == "__main__":
    main()
