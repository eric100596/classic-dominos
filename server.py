# server.py
import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Use eventlet on Heroku; allow CORS for testing
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Minimal shared state (demo)
game_state = {"players": [], "board": []}

@app.route("/")
def home():
    return render_template("index.html")

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
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)

