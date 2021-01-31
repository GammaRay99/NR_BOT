from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/', methods=["GET", "POST"])
def main():
  return "Bot connected !"

def run():
    app.run(host="0.0.0.0", port=8080)

def web_interface():
    server = Thread(target=run)
    server.start()
