import pickle
import socket
import threading

import game

HOST = "0.0.0.0"
PORT = 5555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(2)


clients = []
board = game.generate_board()
to_move = ["X", None]  # Player, Restriction

lock = threading.Lock()


def broadcast(data):
    for client in clients:
        try:
            client.send(pickle.dumps(data))
        except:
            clients.remove(client)


def handle_client(conn, player):
    global board, to_move

    # Send initial state
    # Protocol: ("WELCOME", player_symbol) then ("UPDATE", board, to_move)
    try:
        conn.send(pickle.dumps(("WELCOME", player)))
        conn.send(pickle.dumps(("UPDATE", board, to_move)))
    except:
        return

    while True:
        try:
            data = conn.recv(4096 * 4)  # Buffer size
            if not data:
                break

            try:
                move = pickle.loads(data)
                # Expected move format: (large_row, large_col, mini_row, mini_col)

                with lock:
                    if to_move[0] == player:
                        new_board, new_to_move, valid = game.apply_move(
                            board, to_move, move
                        )

                        if valid:
                            board = new_board
                            to_move = new_to_move

                            # check for global winner
                            board_state = game.get_board_state(board)
                            winner = game.check_board_winner(board_state)

                            broadcast(("UPDATE", board, to_move))

                            if winner:
                                broadcast(("GAME_OVER", winner))
            except Exception as e:
                print(f"Error processing move: {e}")

        except:
            break

    print(f"Player {player} disconnected")
    if conn in clients:
        clients.remove(conn)
    conn.close()


def start():
    print(f"Server started on {HOST}:{PORT}")
    print("Waiting for players...")

    player_symbols = ["X", "O"]

    while len(clients) < 2:
        conn, addr = server.accept()
        print(f"Connected by {addr}")
        clients.append(conn)

        player = player_symbols[len(clients) - 1]
        thread = threading.Thread(target=handle_client, args=(conn, player))
        thread.start()

    print("Game starting!")


if __name__ == "__main__":
    start()
