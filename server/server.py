import asyncio
import pickle
import uuid
import sys
from pathlib import Path
import websockets

# Add the parent directory to sys.path to allow importing from 'client'
sys.path.append(str(Path(__file__).parent.parent))

from client import logic as game

HOST = "0.0.0.0"
PORT = 5555

games = {}  # game_id -> GameSession

class GameSession:
    def __init__(self, game_id):
        self.game_id = game_id
        self.board = game.generate_board()
        self.to_move = ["X", None]
        self.players = {}  # "X": ws, "O": ws
        self.spectators = set()
        self.winner = None

    async def broadcast(self, data):
        # Pickle the data once
        message = pickle.dumps(data)
        
        # Send to players
        to_remove = []
        for role, ws in self.players.items():
            try:
                await ws.send(message)
            except Exception as e:
                print(f"Error broadcasting to {role} in game {self.game_id}: {e}")
                to_remove.append(role)
        
        for role in to_remove:
            self.remove_player(role)

        # Send to spectators
        to_remove_specs = []
        for ws in self.spectators:
            try:
                await ws.send(message)
            except Exception as e:
                print(f"Error broadcasting to spectator in game {self.game_id}: {e}")
                to_remove_specs.append(ws)
        
        for ws in to_remove_specs:
            self.spectators.discard(ws)

    def remove_player(self, role):
        if role in self.players:
            del self.players[role]

    def add_spectator(self, ws):
        self.spectators.add(ws)

    def get_role(self, ws):
        for role, socket in self.players.items():
            if socket == ws:
                return role
        if ws in self.spectators:
            return "SPECTATOR"
        return None


async def handle_client(websocket):
    print(f"New connection from {websocket.remote_address}")
    current_game = None
    role = None
    
    try:
        # Handshake
        # Expecting a message immediately upon connection
        data = await websocket.recv()
        request = pickle.loads(data)
        command = request[0]

        if command == "CREATE":
            game_id = str(uuid.uuid4())[:5]
            current_game = GameSession(game_id)
            games[game_id] = current_game
            
            # No lock needed for simple dict operations in asyncio single-thread loop
            current_game.players["X"] = websocket
            role = "X"
            
            await websocket.send(pickle.dumps(("CREATED", game_id, "X")))
            print(f"Game {game_id} created")

        elif command == "JOIN":
            game_id = request[1]
            if game_id not in games:
                await websocket.send(pickle.dumps(("ERROR", "Game not found")))
                return
            
            current_game = games[game_id]
            
            if "O" not in current_game.players:
                current_game.players["O"] = websocket
                role = "O"
                await websocket.send(pickle.dumps(("JOINED", "O")))
                await current_game.broadcast(("START", current_game.board))
                print(f"Player O joined game {game_id}")
            else:
                current_game.add_spectator(websocket)
                role = "SPECTATOR"
                await websocket.send(pickle.dumps(("JOINED", "SPECTATOR")))
                await websocket.send(pickle.dumps(("UPDATE", current_game.board, current_game.to_move)))
                print(f"Spectator joined game {game_id}")
        else:
            return

        # Game Loop
        async for message in websocket:
            if role == "SPECTATOR":
                continue

            try:
                move = pickle.loads(message)
                # Apply move checking
                if current_game.to_move[0] == role:
                    new_board, new_to_move, valid = game.apply_move(
                        current_game.board, current_game.to_move, move
                    )

                    if valid:
                        current_game.board = new_board
                        current_game.to_move = new_to_move
                        
                        board_state = game.get_board_state(current_game.board)
                        winner = game.check_board_winner(board_state)

                        await current_game.broadcast(("UPDATE", current_game.board, current_game.to_move))

                        if winner:
                            await current_game.broadcast(("GAME_OVER", winner))
                            current_game.winner = winner

            except Exception as e:
                print(f"Error processing move: {e}")

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed")
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        if current_game:
            if role in ["X", "O"]:
                print(f"Player {role} disconnected from game {current_game.game_id}")
                current_game.remove_player(role)
                await current_game.broadcast(("OPPONENT_LEFT",))
            elif role == "SPECTATOR":
                current_game.spectators.discard(websocket)
            
            # Clean up empty games (optional but good for long running)
            if not current_game.players and not current_game.spectators:
                if current_game.game_id in games:
                    del games[current_game.game_id]


async def main():
    print(f"Starting WebSocket server on {HOST}:{PORT}")
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.get_running_loop().create_future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
