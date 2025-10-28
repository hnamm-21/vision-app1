import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

# Flask setup
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # لو التطبيق والواجهة على نفس الدومين، ممكن الاستغناء عنه

# ===== Azure config (من متغيرات البيئة) =====
AZURE_ENDPOINT = os.getenv("https://test-tow.cognitiveservices.azure.com/")  # مثال: https://<name>.cognitiveservices.azure.com/vision/v3.2/analyze
AZURE_KEY = os.getenv("4KJp3PoA5yecqFkJTewSkr5OysHfdODVpjMog3Me5Wp1Dp3A0uYYJQQJ99BJACPV0roXJ3w3AAAFACOGLbtF")            # Key1 أو Key2 من Manage Keys

# تحقق مبكر من الإعدادات
if not AZURE_ENDPOINT or not AZURE_KEY:
    print("⚠️  AZURE_ENDPOINT / AZURE_KEY غير مضبوطين في متغيرات البيئة. "
          "اضبطهم من Azure → Web App → Configuration → Application settings.")

# ===== قيود رفع الملفات =====
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # 6MB
ALLOWED_EXT = {"jpg", "jpeg", "png", "bmp", "gif", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ===== Routes =====
@app.route("/")
def home():
    # صفحة الواجهة (templates/index.html)
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    # مسار فحص صحي بسيط لأغراض Azure / المراقبة
    return jsonify({"status": "ok"}), 200


@app.route("/analyze", methods=["POST"])
def analyze_image():
    # 1) التحقق من الملف
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image uploaded"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415

    if not AZURE_ENDPOINT or not AZURE_KEY:
        return jsonify({"error": "Server misconfigured: missing AZURE_ENDPOINT or AZURE_KEY"}), 500

    image_bytes = file.read()

    # 2) طلب Azure
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/octet-stream",
    }
    params = {
        # v3.2 features: Categories, Tags, Description, Faces, ImageType, Color, Adult, Objects, Brands
        "visualFeatures": "Description,Tags,Objects",
        "language": "en",
    }

    try:
        resp = requests.post(
            AZURE_ENDPOINT,
            headers=headers,
            params=params,
            data=image_bytes,
            timeout=30
        )

        # 3) معالجة الاستجابة
        if not resp.ok:
            # نعيد النص الخام لمساعدة الديبَغ (مثلاً 401/404/415/429)
            return jsonify({
                "error": "Azure API error",
                "status": resp.status_code,
                "details": resp.text
            }), resp.status_code

        return jsonify(resp.json())

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Request to Azure failed", "details": str(e)}), 502


# ===== تشغيل محلي/على Azure =====
if __name__ == "__main__":
    # Azure App Service يمرر المنفذ عبر PORT
    port = int(os.environ.get("PORT", 5000))
    # host=0.0.0.0 مهم على Azure/حاويات
    app.run(host="0.0.0.0", port=port, debug=False)
