from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, json, os

app = Flask(__name__)

# — Config desde variables de entorno —
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "SKYCONET2024")

BYBIT_BASE = "https://api.bybit.com"
SYMBOL     = "XRPUSDT"
CATEGORY   = "spot"   # spot trading 
QTY        = "50"       # USDT por orden — ajustá según balance

def bybit_sign(params: dict, secret: str) -> str:
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(secret.encode(), param_str.encode(), hashlib.sha256).hexdigest()

def place_order(side: str, qty: str):
    ts = str(int(time.time() * 1000))
    params = {
        "api_key":    BYBIT_API_KEY,
        "category":   CATEGORY,
        "symbol":     SYMBOL,
        "side":       side,          # "Buy" o "Sell"
        "orderType":  "Market",
        "qty":        qty,
        "timestamp":  ts,
        "recv_window": "5000",
    }
    params["sign"] = bybit_sign(params, BYBIT_API_SECRET)
    r = requests.post(f"{BYBIT_BASE}/v5/order/create", json=params)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    # Verificar secret
    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    action = data.get("action", "").upper()   # "BUY" o "SELL"

    if action == "BUY":
        result = place_order("Buy", QTY)
    elif action == "SELL":
        result = place_order("Sell", QTY)
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {action} → {result}")
    return jsonify(result), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "SKYCONET XRP"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
