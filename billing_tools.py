import sqlite3
import subprocess

from flask import Flask, jsonify, request

billing = Flask(__name__)
LEDGER = "ledger.db"
ALLOWED_TEMPLATES = {"default", "compact", "detailed"}


@billing.route("/invoices")
def invoices_for_account():
    account = request.args.get("account", "")
    ledger = sqlite3.connect(LEDGER)
    invoices = ledger.execute(
        "SELECT number, amount FROM invoices WHERE account_id = ?", (account,)
    ).fetchall()
    ledger.close()
    return jsonify(invoices)


@billing.route("/render")
def render_invoice():
    template = request.args.get("template", "default")
    if template not in ALLOWED_TEMPLATES:
        return jsonify({"error": "unknown template"}), 400
    result = subprocess.run(
        ["wkhtmltopdf", f"templates/{template}.html", "-"],
        capture_output=True,
        check=False,
    )
    return result.stdout


if __name__ == "__main__":
    billing.run(port=7100)
