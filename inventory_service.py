import re
import sqlite3
import subprocess

from flask import Flask, jsonify, request

service = Flask(__name__)
INVENTORY_DB = "inventory.db"


@service.route("/stock/<warehouse>")
def stock_for_sku(warehouse):
    sku = request.args.get("sku", "")
    db = sqlite3.connect(INVENTORY_DB)
    rows = db.execute(
        "SELECT sku, quantity FROM stock WHERE warehouse = ? AND sku = ?",
        (warehouse, sku),
    ).fetchall()
    db.close()
    return jsonify(rows)


@service.route("/export")
def export_report():
    name = request.args.get("name", "report")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        return jsonify({"error": "invalid name"}), 400
    result = subprocess.run(
        ["tar", "-czf", f"/tmp/{name}.tgz", "/var/inventory/reports"], check=False
    )
    return jsonify({"exit_code": result.returncode})


if __name__ == "__main__":
    service.run(port=7000)
