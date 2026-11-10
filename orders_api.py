import sqlite3
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "orders.db"


@app.route("/orders")
def find_orders():
    customer = request.args.get("customer", "")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT id, item, total FROM orders WHERE customer = '" + customer + "'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)


@app.route("/ping")
def ping_host():
    host = request.args.get("host", "127.0.0.1")
    output = subprocess.check_output("ping -c 1 " + host, shell=True)
    return output


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
