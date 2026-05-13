from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, json, os, traceback

app = Flask(__name__)

# — Config desde variables de entorno —
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "SKYCONET2024")

BYBIT_BASE = "https://api.bybit.com"
SYMBOL     = "XRPUSDT"
CATEGORY   = "spot"
QTY        = "50"   # USDT por orden — ajustá según balance

def bybit_sign_v5(ts: str, api_key: str, recv_window: str, body: str, secret: str) -> str:
    sign_str = ts + api_key + recv_window + body
    return hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

def place_order(side: str, qty: str):
    ts          = str(int(time.time() * 1000))
    recv_window = "5000"

    body = {
        "category":  CATEGORY,
        "symbol":    SYMBOL,
        "side":      side,
        "orderType": "Market",
        "qty":       qty,
    }
    body_str = json.dumps(body, separators=(",", ":"))

    signature = bybit_sign_v5(ts, BYBIT_API_KEY, recv_window, body_str, BYBIT_API_SECRET)

    headers = {
        "Content-Type":       "application/json",
        "X-BAPI-API-KEY":     BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP":   ts,
        "X-BAPI-SIGN":        signature,
        "X-BAPI-RECV-WINDOW": recv_window,
    }

    r = requests.post(f"{BYBIT_BASE}/v5/order/create", data=body_str, headers=headers)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}

        # Verificar env vars
        if not BYBIT_API_KEY or not BYBIT_API_SECRET:
            return jsonify({
                "error": "Missing env vars",
                "BYBIT_API_KEY_set": bool(BYBIT_API_KEY),
                "BYBIT_API_SECRET_set": bool(BYBIT_API_SECRET),
            }), 500

        # Verificar secret
        if data.get("secret") != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

        action = data.get("action", "").upper()

        if action == "BUY":
            result = place_order("Buy", QTY)
        elif action == "SELL":
            result = place_order("Sell", QTY)
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {action} → {result}")
        return jsonify(result), 200

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[WEBHOOK ERROR] {tb}")
        return jsonify({
            "error": "Exception in webhook handler",
            "type": type(e).__name__,
            "message": str(e),
            "traceback": tb.splitlines()[-6:],
        }), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "SKYCONET XRP"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
