import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# اقرأ من أسماء المتغيرات البيئية (الـ Values تنحط في Azure Portal)
AZURE_ENDPOINT = os.getenv("https://test-tow.cognitiveservices.azure.com/")  # مثال القيمة: https://test-tow.cognitiveservices.azure.com/vision/v3.2/analyze
AZURE_KEY = os.getenv("4KJp3PoA5yecqFkJTewSkr5OysHfdODVpjMog3Me5Wp1Dp3A0uYYJQQJ99BJACPV0roXJ3w3AAAFACOGLbtF")            # مثال القيمة: مفتاح Key1/Key2

if not AZURE_ENDPOINT or not AZURE_KEY:
    print("⚠️ Missing AZURE_ENDPOINT or AZURE_KEY env vars in App Service → Environment variables")

app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # 6MB
ALLOWED_EXT = {"jpg", "jpeg", "png", "bmp", "gif", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

@app.route("/analyze", methods=["POST"])
def analyze_image():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image uploaded"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415
    if not AZURE_ENDPOINT or not AZURE_KEY:
        return jsonify({"error": "Server misconfigured: missing AZURE_ENDPOINT or AZURE_KEY"}), 500

    image_bytes = file.read()
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/octet-stream",
    }
    params = {"visualFeatures": "Description,Tags,Objects", "language": "en"}

    try:
        resp = requests.post(AZURE_ENDPOINT, headers=headers, params=params, data=image_bytes, timeout=30)
        if not resp.ok:
            return jsonify({"error": "Azure API error", "status": resp.status_code, "details": resp.text}), resp.status_code
        return jsonify(resp.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request to Azure failed", "details": str(e)}), 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
