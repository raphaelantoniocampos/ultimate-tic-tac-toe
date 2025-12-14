import copy
import sys

import pygame

# --- CONSTANTS ---
WIDTH, HEIGHT = 900, 900

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))

BG_COLOR = (214, 201, 227)

BOARD_OFFSET = 100
CELL_SIZE = 230
MINI_CELL_SIZE = 75

HIGHLIGHT_COLOR = (255, 255, 100)
HIGHLIGHT_BORDER_WIDTH = 5
HIGHLIGHT_PADDING = 35

INIT_GRAPHICAL_BOARD = [
    [[[[None, None] for _ in range(3)] for _ in range(3)] for _ in range(3)]
    for _ in range(3)
]

# Load assets
BOARD = pygame.image.load("assets/board.png")
x_img = pygame.image.load("assets/x.png")
X_IMG = pygame.transform.scale(
    x_img,
    ((x_img.get_width() * 0.25), (x_img.get_height() * 0.25)),
)
o_img = pygame.image.load("assets/o.png")
O_IMG = pygame.transform.scale(
    o_img,
    ((o_img.get_width() * 0.245), (o_img.get_height() * 0.245)),
)
WINNING_X_IMG = pygame.image.load("assets/light_x.png")
WINNING_O_IMG = pygame.image.load("assets/light_o.png")
DRAW_IMG = pygame.image.load("assets/draw.png")
MINI_DRAW_IMG = pygame.transform.scale(
    DRAW_IMG,
    ((DRAW_IMG.get_width() * 0.245), (DRAW_IMG.get_height() * 0.245)),
)


# global board
graphical_board = copy.deepcopy(INIT_GRAPHICAL_BOARD)


def main():
    pygame.init()

    title_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 32)
    game_state_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 24)
    button_font = pygame.font.Font("assets/0xProtoNerdFont-Regular.ttf", 20)

    pygame.display.set_caption("Ultimate Tic Tac Toe!")

    title = title_font.render("Ultimate Tic Tac Toe", True, (20, 20, 20))
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 18))

    # Start game variables
    # Who starts and playable area limits
    to_move, player_img = ["X", None], X_IMG
    game_finished = False

    # board = copy.deepcopy(INIT_BOARD)
    board = generate_board()

    # Draw board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD, (64, 64))

    pygame.display.update()

    game_state_text = "PLAYER:"
    game_state = game_state_font.render(game_state_text, True, (20, 20, 20))

    button_rect = None

    starting_game = True
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            # Player action
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                if (
                    (game_finished or starting_game)
                    and button_rect
                    and button_rect.collidepoint(x, y)
                ):
                    starting_game = False
                    global graphical_board
                    board = generate_board()
                    graphical_board = copy.deepcopy(INIT_GRAPHICAL_BOARD)
                    to_move = ["X", None]
                    game_finished = False
                    game_state_text = "PLAYER:"
                    player_img = X_IMG
                    break

                if not game_finished and not starting_game:
                    # Adds X/O
                    board, to_move = add_XO(board, to_move)

                    render_board(board)

                    if not to_move[0]:
                        break

                    board_state = get_board_state(board)
                    winner = check_board_winner(board_state)
                    player_img = get_player_image(to_move[0])

                    if isinstance(winner, str):
                        player_img = get_player_image(winner)
                        game_state_text = "WINNER"
                        to_move[1] = None
                        if winner == "D":
                            game_state_text = "DRAW"
                        game_finished = True

        # Draws the game
        draw_game(board, to_move)

        if starting_game:
            button_rect = draw_button(
                SCREEN,
                "START",
                button_font,
                WIDTH // 2,
                HEIGHT // 2,
            )

        elif game_finished:
            button_rect = draw_button(
                SCREEN,
                "RESTART",
                button_font,
                WIDTH // 2,
                HEIGHT // 2,
            )
        else:
            button_rect = None

        game_state = game_state_font.render(
            game_state_text,
            True,
            (20, 20, 20),
        )
        SCREEN.blit(title, title_rect)
        SCREEN.blit(
            game_state,
            game_state.get_rect(
                center=((WIDTH // 2) - WIDTH // 21, (HEIGHT // 18) * 17)
            ),
        )
        SCREEN.blit(
            player_img,
            player_img.get_rect(
                center=((WIDTH // 2) + WIDTH // 21, (HEIGHT // 18) * 17)
            ),
        )

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
    if len(mini_board) > 3:
        to_move[1] = None
        return board, to_move

    # Update the board
    if isinstance(mini_board, list):
        if isinstance(mini_board[mini_row][mini_col], int):
            mini_board[mini_row][mini_col] = to_move[0]

            # Switch player
            to_move[0] = "O" if to_move[0] == "X" else "X"
            to_move[1] = (mini_row, mini_col)
            if len(board[mini_row][mini_col]) > 3:
                to_move[1] = None

    # Check for mini board winner
    winner = check_board_winner(mini_board)
    if winner:
        mini_board += [winner]
        if to_move[1] == (large_row, large_col):
            to_move[1] = None

    return board, to_move


def render_board(board):
    global graphical_board
    mini_spacing = 55
    offset = 220

    for i in range(3):
        for j in range(3):
            center_x = j * CELL_SIZE + offset
            center_y = i * CELL_SIZE + offset

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

            if len(board[i][j]) > 3:
                winning_img = get_winner_image(board[i][j][3])
                if winning_img:
                    winning_rect = winning_img.get_rect(
                        center=(center_x, center_y),
                    )
                    graphical_board[i][j] += [(winning_img, winning_rect)]


def get_player_image(player):
    if player == "X":
        return X_IMG
    if player == "O":
        return O_IMG
    if player == "D":
        return MINI_DRAW_IMG
    return None


def get_winner_image(winner):
    global WINNING_X_IMG, WINNING_O_IMG

    if winner == "X":
        return WINNING_X_IMG
    if winner == "O":
        return WINNING_O_IMG
    if winner == "D":
        return DRAW_IMG
    return None


def check_board_winner(board):
    winner = ""
    lines = []

    # Rows and Columns
    for i in range(3):
        # Rows
        lines.append([board[i][0], board[i][1], board[i][2]])
        # Columns
        lines.append([board[0][i], board[1][i], board[2][i]])

    # Diagonals
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])

    # Win Condition
    for line in lines:
        # Count X's, O's and D's in the line
        count_x = line.count("X")
        count_o = line.count("O")
        count_d = line.count("D")

        if (
            (count_x == 3)
            or (count_x == 2 and count_d == 1)
            or (count_x == 1 and count_d == 2)
        ):
            winner = "X"

        if (
            (count_o == 3)
            or (count_o == 2 and count_d == 1)
            or (count_o == 1 and count_d == 2)
        ):
            if winner == "X":
                winner = "D"
            else:
                winner = "O"

    has_unresolved_mini_board = False
    for row in board:
        if has_unresolved_mini_board := any(isinstance(n, int) for n in row):
            break

    if not winner and not has_unresolved_mini_board:
        winner = "D"

    if not winner:
        winner = None

    return winner


def draw_game(board, to_move):
    global graphical_board
    # Clear the screen and draw the main board
    SCREEN.fill(BG_COLOR)
    SCREEN.blit(BOARD, (64, 64))

    if to_move[1] is not None:
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
    for i in range(3):
        for j in range(3):
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
            if len(graphical_board[i][j]) > 3:
                SCREEN.blit(
                    graphical_board[i][j][3][0],
                    graphical_board[i][j][3][1],
                )


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


def get_board_state(board):
    board_state = []
    counter = 0
    for i in range(3):
        row = []
        for j in range(3):
            mini_board = board[i][j]
            if len(mini_board) > 3:
                winner = mini_board[3]
            else:
                winner = counter
            counter += 1

            row.append(winner)
        board_state.append(row)

    return board_state


def draw_button(screen, text, font, center_x, center_y):
    button_width = 180
    button_height = 50
    text_surface = font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(center_x, center_y))

    button_rect = pygame.Rect(
        center_x - (button_width / 2),
        center_y - (button_height / 2),
        button_width,
        button_height,
    )
    pygame.draw.rect(screen, (50, 50, 50), button_rect, border_radius=5)

    screen.blit(text_surface, text_rect)

    return button_rect


if __name__ == "__main__":
    main()
