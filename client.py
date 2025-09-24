# client.py
import socketio

sio = socketio.Client()

USERNAME = None  # we'll set this at runtime

@sio.on('connect')
def on_connect():
    print("Connected to server")
    sio.emit('join', {"username": USERNAME})

@sio.on('player_joined')
def on_player_joined(data):
    print("Players in game:", data["players"])

@sio.on('tile_played')
def on_tile_played(data):
    print("Board:", data["board"], "Last move:", data["move"])

def connect(url="http://localhost:5000", username="Player"):
    global USERNAME
    USERNAME = username
    sio.connect(url)

def play_tile(tile):
    sio.emit("play_tile", {"username": USERNAME, "tile": tile})

if __name__ == "__main__":
    name = input("Enter your player name: ").strip() or "Player"
    connect(username=name)
    while True:
        move = input("Enter a tile like 6,3 or 'quit': ").strip().lower()
        if move == "quit":
            break
        try:
            tile = [int(x) for x in move.split(",")]
            play_tile(tile)
        except Exception:
            print("Format should be 6,3")

