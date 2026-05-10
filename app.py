import os
import re
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from scheduler import init_scheduler, schedule_campaign

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
scheduler = init_scheduler()


def extract_sheet_id(url: str):
    for pat in [r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
                r"spreadsheets/d/([a-zA-Z0-9-_]+)"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def extract_branding(data: dict) -> dict:
    return {
        "brand_name":   data.get("brand_name", "Newsletter").strip(),
        "logo_url":     data.get("logo_url", "").strip(),
        "accent_color": data.get("accent_color", "#1a1a2e").strip(),
        "website_url":  data.get("website_url", "").strip(),
        "twitter":      data.get("twitter", "").strip(),
        "instagram":    data.get("instagram", "").strip(),
        "linkedin":     data.get("linkedin", "").strip(),
        "facebook":     data.get("facebook", "").strip(),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schedule", methods=["POST"])
def schedule():
    try:
        data = request.get_json(force=True)

        required = ["gmail_address", "app_password", "sheet_url",
                    "subject", "message", "scheduled_time"]
        missing = [f for f in required if not data.get(f, "").strip()]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        if not is_valid_email(data["gmail_address"]):
            return jsonify({"error": "Invalid Gmail address."}), 400

        sheet_id = extract_sheet_id(data["sheet_url"])
        if not sheet_id:
            return jsonify({"error": "Could not extract Sheet ID from URL."}), 400

        try:
            run_at = datetime.fromisoformat(data["scheduled_time"])
        except ValueError:
            return jsonify({"error": "Invalid date/time format."}), 400

        if run_at <= datetime.now():
            return jsonify({"error": "Scheduled time must be in the future."}), 400

        branding = extract_branding(data)
        job_id = schedule_campaign(
            scheduler=scheduler,
            run_at=run_at,
            gmail_address=data["gmail_address"],
            app_password=data["app_password"],
            sheet_id=sheet_id,
            subject=data["subject"],
            message=data["message"],
            branding=branding,
        )

        return jsonify({
            "success": True,
            "message": f"Campaign scheduled for {run_at.strftime('%B %d, %Y at %I:%M %p')}",
            "job_id": job_id,
        })

    except Exception as exc:
        logger.exception("Error in /api/schedule")
        return jsonify({"error": f"Server error: {str(exc)}"}), 500


@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    jobs = [{"id": j.id, "next_run": str(j.next_run_time)}
            for j in scheduler.get_jobs()]
    return jsonify({"jobs": jobs})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting MailForge on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=False)