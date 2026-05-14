from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, json, os

app = Flask(__name__)

BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "SKYCONET2024")

BYBIT_BASE  = "https://api.bybit.com"
SYMBOL      = "XRPUSDT"
CATEGORY    = "spot"
QTY         = "50"
RECV_WINDOW = "5000"

def bybit_sign_v5(ts, api_key, recv_window, body, secret):
    payload = f"{ts}{api_key}{recv_window}{body}"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def place_order(side, qty):
    ts = str(int(time.time() * 1000))
    body = {
        "category": CATEGORY,
        "symbol": SYMBOL,
        "side": side,
        "orderType": "Market",
        "qty": qty,
    }
    body_str = json.dumps(body, separators=(",", ":"))
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "X-BAPI-SIGN": bybit_sign_v5(ts, BYBIT_API_KEY, RECV_WINDOW, body_str, BYBIT_API_SECRET),
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(f"{BYBIT_BASE}/v5/order/create", data=body_str, headers=headers, timeout=10)
    except requests.RequestException as e:
        return {"ok": False, "error": "request_failed", "message": str(e)}
    try:
        return r.json()
    except ValueError:
        return {"ok": False, "error": "invalid_json_from_bybit", "status_code": r.status_code, "body_snippet": r.text[:500]}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}
        if data.get("secret") != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        if not BYBIT_API_KEY or not BYBIT_API_SECRET:
            return jsonify({"error": "Missing env vars"}), 500
        action = data.get("action", "").upper()
        if action == "BUY":
            result = place_order("Buy", QTY)
        elif action == "SELL":
            result = place_order("Sell", QTY)
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {action} -> {result}")
        return jsonify(result), 200
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return jsonify({"error": "Exception in webhook handler", "message": str(e), "traceback": tb.splitlines()[-6:]}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "SKYCONET XRP"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
