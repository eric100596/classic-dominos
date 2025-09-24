import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Heroku provides PORT
    # Debug off in production
    # Flask-SocketIO will use eventlet/gevent if installed; otherwise HTTP/WebSocket fallback
    socketio.run(app, host="0.0.0.0", port=port)
# server.py
from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Minimal in-memory game state for testing
game_state = {"players": [], "board": []}

@app.route('/')
def index():
    return "Domino server is running."

@socketio.on('connect')
def on_connect():
    print("A player connected")

@socketio.on('join')
def on_join(data):
    username = data.get('username', 'Player')
    if username not in game_state["players"]:
        game_state["players"].append(username)
    emit('player_joined', {"players": game_state["players"]}, broadcast=True)

@socketio.on('play_tile')
def on_play_tile(data):
    tile = data.get("tile")
    username = data.get("username", "Player")
    if tile:
        game_state["board"].append(tile)
        emit('tile_played', {"board": game_state["board"], "move": {"username": username, "tile": tile}}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    print("A player disconnected")

if __name__ == '__main__':
    print("Starting Domino server on http://0.0.0.0:5000 ...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

# server.py
import os
from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Use eventlet on Heroku if available; allow all CORS for testing
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Very simple in-memory state to prove it works
game_state = {"players": [], "board": []}

@app.route("/")
def index():
    return "Domino server is running."

@socketio.on("connect")
def on_connect():
    print("A client connected")

@socketio.on("join")
def on_join(data):
    username = data.get("username", "Player")
    if username not in game_state["players"]:
        game_state["players"].append(username)
    emit("player_joined", {"players": game_state["players"]}, broadcast=True)

@socketio.on("play_tile")
def on_play_tile(data):
    tile = data.get("tile")
    username = data.get("username", "Player")
    if tile is not None:
        game_state["board"].append(tile)
        emit("tile_played",
             {"board": game_state["board"], "move": {"username": username, "tile": tile}},
             broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    print("A client disconnected")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Heroku provides PORT
    socketio.run(app, host="0.0.0.0", port=port)

