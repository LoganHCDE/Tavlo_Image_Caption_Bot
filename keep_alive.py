import os
from threading import Thread
from flask import Flask, jsonify
from waitress import serve


def create_app(bot, model):
    app = Flask(__name__)

    @app.get('/')
    def home():
        return '<h1>Tavlo</h1><p>Discord image captions powered by Gemma 4 26B.</p><p><a href="https://www.tavlo.app/">Tavlo website</a></p>'

    @app.get('/healthz')
    def health():
        ready = bot.is_ready()
        return jsonify(status='ready' if ready else 'connecting', model=model), 200 if ready else 503

    return app


def keep_alive(bot, model):
    Thread(target=serve, kwargs={
        'app': create_app(bot, model),
        'host': os.getenv('WEB_HOST', '127.0.0.1'),
        'port': int(os.getenv('PORT', '8080')),
        'threads': 2,
    }, daemon=True).start()
