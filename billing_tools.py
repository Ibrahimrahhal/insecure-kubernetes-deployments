import sqlite3
import subprocess

from flask import Flask, jsonify, request

billing = Flask(__name__)
LEDGER = "ledger.db"


@billing.route("/invoices")
def invoices_for_account():
    account = request.args.get("account", "")
    ledger = sqlite3.connect(LEDGER)
    statement = "SELECT number, amount FROM invoices WHERE account_id = %s" % account
    invoices = ledger.execute(statement).fetchall()
    ledger.close()
    return jsonify(invoices)


@billing.route("/render")
def render_invoice():
    template = request.args.get("template", "default")
    rendered = subprocess.getoutput("wkhtmltopdf templates/" + template + ".html -")
    return rendered


if __name__ == "__main__":
    billing.run(port=7100)
