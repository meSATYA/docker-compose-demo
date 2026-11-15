import os
import socket

import redis
from flask import Flask, jsonify

app = Flask(__name__)
# "redis" is the compose service name -> resolved by Docker's built-in DNS
cache = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)


@app.route("/")
def index():
    visits = cache.incr("visits")
    return jsonify(
        message="Hello from Docker Compose!",
        visits=visits,
        served_by=socket.gethostname(),  # container ID -> shows load balancing
    )


@app.route("/health")
def health():
    cache.ping()
    return jsonify(status="ok")
