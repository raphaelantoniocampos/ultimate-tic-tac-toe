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


def apply_move(board, to_move, move_indices):
    large_row, large_col, mini_row, mini_col = move_indices
    player = to_move[0]
    required_next_move = to_move[1]

    # Determine valid move
    if required_next_move:
        if required_next_move != (large_row, large_col):
            return board, to_move, False  # Invalid move: Wrong large cell

    mini_board = board[large_row][large_col]

    # Check for mini board winner
    if len(mini_board) > 3:
        to_move[1] = None
        return board, to_move, False

    if not isinstance(mini_board[mini_row][mini_col], int):
        return board, to_move, False

    # Apply move
    mini_board[mini_row][mini_col] = player

    # Check for mini board winner
    winner = check_board_winner(mini_board)
    if winner:
        mini_board += [winner]

    # Switch player
    next_player = "O" if player == "X" else "X"
    next_restriction = (mini_row, mini_col)

    # Check if the target large cell is already won
    target_mini_board = board[mini_row][mini_col]
    if len(target_mini_board) > 3:
        next_restriction = None

    return board, [next_player, next_restriction], True
