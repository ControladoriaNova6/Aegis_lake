import time
from flask import Flask
app = Flask(__name__)

@app.route("/lento")
def lento():
    time.sleep(3)  # simula um processamento de arquivo grande
    return "concluido"
