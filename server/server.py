import pickle
import socket
import sys
import threading
import uuid
from pathlib import Path

# Add the parent directory to sys.path to allow importing from 'client'
sys.path.append(str(Path(__file__).parent.parent))

from client import logic as game

HOST = "0.0.0.0"
PORT = 5555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()


clients = []
games = {}  # game_id -> GameSession


class GameSession:
    def __init__(self, game_id):
        self.game_id = game_id
        self.board = game.generate_board()
        self.to_move = ["X", None]
        self.players = {}  # "X": conn, "O": conn
        self.spectators = []
        self.lock = threading.Lock()
        self.winner = None

    def broadcast(self, data):
        # Send to players
        for role, conn in list(self.players.items()):
            try:
                conn.send(pickle.dumps(data))
            except Exception as e:
                print(f"Error broadcasting to {role}: {e}")
                self.remove_player(role)
        # Send to spectators
        for conn in list(self.spectators):
            try:
                conn.send(pickle.dumps(data))
            except Exception as e:
                print(f"Error broadcasting to spectator: {e}")
                self.spectators.remove(conn)

    def remove_player(self, role):
        if role in self.players:
            del self.players[role]

    def add_spectator(self, conn):
        self.spectators.append(conn)

    def get_role(self, conn):
        for role, c in self.players.items():
            if c == conn:
                return role
        if conn in self.spectators:
            return "SPECTATOR"
        return None


def handle_client(conn, addr):
    print(f"New connection from {addr}")
    current_game = None
    role = None
    try:
        # Handshake Loop
        data = conn.recv(4096)
        if not data:
            return

        request = pickle.loads(data)
        command = request[0]
        if command == "CREATE":
            game_id = str(uuid.uuid4())[:5]
            current_game = GameSession(game_id)
            games[game_id] = current_game

            with current_game.lock:
                current_game.players["X"] = conn
                role = "X"

            conn.send(pickle.dumps(("CREATED", game_id, "X")))
            print(f"Game {game_id} created by {addr}")
        elif command == "JOIN":
            game_id = request[1]
            if game_id not in games:
                conn.send(pickle.dumps(("ERROR", "Game not found")))
                return
            current_game = games[game_id]

            with current_game.lock:
                if "O" not in current_game.players:
                    current_game.players["O"] = conn
                    role = "O"
                    conn.send(pickle.dumps(("JOINED", "O")))
                    current_game.broadcast(("START", current_game.board))
                    print(f"Player O joined game {game_id}")
                else:
                    current_game.add_spectator(conn)
                    role = "SPECTATOR"
                    conn.send(pickle.dumps(("JOINED", "SPECTATOR")))
                    conn.send(
                        pickle.dumps(
                            ("UPDATE", current_game.board, current_game.to_move)
                        )
                    )
                    print(f"Spectator joined game {game_id}")
        else:
            return

        # Game Loop
        while True:
            data = conn.recv(4096 * 4)
            if not data:
                break

            if role == "SPECTATOR":
                continue  # Spectators only listen

            try:
                move = pickle.loads(data)
                with current_game.lock:
                    if current_game.to_move[0] == role:
                        new_board, new_to_move, valid = game.apply_move(
                            current_game.board, current_game.to_move, move
                        )

                        if valid:
                            current_game.board = new_board
                            current_game.to_move = new_to_move

                            board_state = game.get_board_state(
                                current_game.board)
                            winner = game.check_board_winner(board_state)

                            # broadcast(("UPDATE", board, to_move))
                            current_game.broadcast(
                                (
                                    "UPDATE",
                                    current_game.board,
                                    current_game.to_move,
                                )
                            )

                            if winner:
                                # broadcast(("GAME_OVER", winner))
                                current_game.broadcast(("GAME_OVER", winner))
                                current_game.winner = winner
            except Exception as e:
                print(f"Error processing move in game {current_game.game_id}: {e}")

    except Exception as e:
        print(f"Connection error with {addr}: {e}")
    finally:
        if current_game:
            with current_game.lock:
                if role in ["X", "O"]:
                    print(
                        f"Player {role} disconnected from game {current_game.game_id}")
                    current_game.remove_player(role)
                    # Notify others of disconnect
                    current_game.broadcast(("OPPONENT_LEFT",))
                elif role == "SPECTATOR":
                    if conn in current_game.spectators:
                        current_game.spectators.remove(conn)
        conn.close()


def start():
    print(f"Server started on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start()
