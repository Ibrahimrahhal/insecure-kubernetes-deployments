import os
import sqlite3

from flask import Flask, jsonify, request

service = Flask(__name__)
INVENTORY_DB = "inventory.db"


@service.route("/stock/<warehouse>")
def stock_for_sku(warehouse):
    sku = request.args.get("sku", "")
    db = sqlite3.connect(INVENTORY_DB)
    rows = db.execute(
        f"SELECT sku, quantity FROM stock WHERE warehouse = '{warehouse}' AND sku = '{sku}'"
    ).fetchall()
    db.close()
    return jsonify(rows)


@service.route("/export")
def export_report():
    name = request.args.get("name", "report")
    exit_code = os.system("tar -czf /tmp/" + name + ".tgz /var/inventory/reports")
    return jsonify({"exit_code": exit_code})


if __name__ == "__main__":
    service.run(port=7000)
