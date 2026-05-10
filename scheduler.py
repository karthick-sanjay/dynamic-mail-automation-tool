import logging
import time
import uuid
import re
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formatdate, make_msgid
import base64

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)

SEND_DELAY_SECONDS  = 1
MAX_RETRIES         = 2
RETRY_DELAY_SECONDS = 5


# ── Scheduler ─────────────────────────────────────────────────────────────────
def init_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        job_defaults={"coalesce": False, "max_instances": 1},
    )
    scheduler.start()
    logger.info("APScheduler started.")
    return scheduler


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


# ── HTML email template ───────────────────────────────────────────────────────
def _build_html(message: str, branding: dict) -> str:
    brand_name  = branding.get("brand_name", "Newsletter")
    logo_url    = branding.get("logo_url", "")
    if logo_url:
        logo_url = logo_url.strip()
    accent      = branding.get("accent_color", "#b8976a").strip() or "#b8976a"
    website_url = branding.get("website_url", "").strip()
    twitter     = branding.get("twitter", "").strip()
    instagram   = branding.get("instagram", "").strip()
    linkedin    = branding.get("linkedin", "").strip()
    facebook    = branding.get("facebook", "").strip()

    # Fixed premium header — deep charcoal works with every logo palette
    HEADER_BG   = "#1c1c1e"
    HEADER_LINE = "#2e2e32"
    STRIP_BG    = "#f5f3ef"
    STRIP_TEXT  = "#8c7355"

    serif = "Georgia,&quot;Times New Roman&quot;,serif"

    # Header block
    if logo_url:
        img_src = "cid:logo_image" if logo_url.startswith("data:image") else logo_url
        logo_block = (
            '<img src="' + img_src + '" alt="' + brand_name + '"'
            ' style="max-height:110px;max-width:300px;object-fit:contain;'
            'display:block;margin:0 auto 22px auto;" />'
            '<span style="display:block;text-align:center;'
            'font-family:Georgia,serif;font-size:11px;font-weight:400;'
            'letter-spacing:7px;text-transform:uppercase;'
            'color:rgba(255,255,255,0.5);">' + brand_name + '</span>'
        )
    else:
        logo_block = (
            '<span style="display:block;text-align:center;'
            'font-family:Georgia,serif;font-size:36px;font-weight:400;'
            'letter-spacing:8px;text-transform:uppercase;'
            'color:#ffffff;line-height:1.15;">' + brand_name + '</span>'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0"'
            ' style="margin-top:20px;"><tr>'
            '<td style="border-top:1px solid rgba(255,255,255,0.15);font-size:0;">&nbsp;</td>'
            '<td align="center" style="padding:0 14px;white-space:nowrap;'
            'color:rgba(255,255,255,0.28);font-size:9px;letter-spacing:4px;">&#10022;</td>'
            '<td style="border-top:1px solid rgba(255,255,255,0.15);font-size:0;">&nbsp;</td>'
            '</tr></table>'
        )

    if website_url:
        logo_block = '<a href="' + website_url + '" style="text-decoration:none;">' + logo_block + '</a>'

    # Social links
    social_links = []
    platforms = [
        (twitter,   "twitter",   "Twitter"),
        (instagram, "instagram", "Instagram"),
        (linkedin,  "linkedin",  "LinkedIn"),
        (facebook,  "facebook",  "Facebook"),
    ]
    for handle, key, label in platforms:
        if handle:
            if handle.startswith("http"):
                url = handle
            elif key == "twitter":
                url = "https://twitter.com/" + handle.lstrip("@")
            elif key == "instagram":
                url = "https://instagram.com/" + handle.lstrip("@")
            elif key == "linkedin":
                url = "https://linkedin.com/company/" + handle.lstrip("@")
            else:
                url = "https://facebook.com/" + handle.lstrip("@")
            social_links.append(
                '<a href="' + url + '" style="color:#aaaaaa;text-decoration:none;'
                'font-size:10px;letter-spacing:0.15em;text-transform:uppercase;'
                'font-family:Arial,sans-serif;margin:0 10px;">' + label + '</a>'
            )

    social_row = ""
    if social_links:
        sep = '<span style="color:#dddddd;">&#183;</span>'
        social_row = (
            '<tr><td align="center" style="padding:0 0 16px;">'
            + sep.join(social_links)
            + '</td></tr>'
        )

    website_row = ""
    if website_url:
        clean = website_url.replace("https://","").replace("http://","").rstrip("/")
        website_row = (
            '<tr><td align="center" style="padding:0 0 14px;">'
            '<a href="' + website_url + '" style="color:' + accent + ';font-size:11px;'
            'text-decoration:none;letter-spacing:0.08em;font-family:Arial,sans-serif;">'
            + clean + '</a></td></tr>'
        )

    # Message paragraphs
    paragraphs = ""
    for para in message.split("\n\n"):
        line_text = para.replace("\n", "<br>").strip()
        if line_text:
            paragraphs += (
                '<p style="margin:0 0 22px 0;color:#2a2a2a;font-size:16px;'
                'line-height:1.9;font-family:Georgia,serif;font-weight:400;">'
                + line_text + '</p>'
            )

    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        "<title>" + brand_name + "</title>"
        "</head>"
        '<body style="margin:0;padding:0;background:#eceae6;font-family:Georgia,serif;">'

        '<table width="100%" cellpadding="0" cellspacing="0" border="0"'
        ' style="background:#eceae6;padding:52px 0 72px;">'
        '<tr><td align="center" valign="top">'

        '<table width="600" cellpadding="0" cellspacing="0" border="0"'
        ' style="max-width:600px;width:100%;background:#ffffff;'
        'box-shadow:0 12px 60px rgba(0,0,0,0.14),0 2px 6px rgba(0,0,0,0.07);">'

        # gold accent top bar
        '<tr><td style="background:' + accent + ';height:4px;font-size:0;">&nbsp;</td></tr>'

        # fixed charcoal header
        '<tr><td align="center" style="background:' + HEADER_BG + ';padding:56px 48px 52px;">'
        + logo_block +
        '</td></tr>'

        '<tr><td style="background:' + HEADER_LINE + ';height:1px;font-size:0;">&nbsp;</td></tr>'

        # warm ivory strip
        '<tr><td align="center" style="background:' + STRIP_BG + ';padding:13px 48px;'
        'font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.22em;'
        'text-transform:uppercase;color:' + STRIP_TEXT + ';">'
        + brand_name + '&nbsp;&nbsp;&#183;&nbsp;&nbsp;Newsletter'
        '</td></tr>'

        # body
        '<tr><td style="padding:56px 60px 48px;background:#ffffff;">'
        + paragraphs +
        '</td></tr>'

        # ornamental divider
        '<tr><td align="center" style="padding:0 60px 40px;background:#ffffff;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="border-top:1px solid #e4e3df;font-size:0;">&nbsp;</td>'
        '<td align="center" style="padding:0 18px;color:#c8c5bc;font-size:13px;'
        'white-space:nowrap;letter-spacing:6px;">&#10022; &#10022; &#10022;</td>'
        '<td style="border-top:1px solid #e4e3df;font-size:0;">&nbsp;</td>'
        '</tr></table></td></tr>'

        # footer
        '<tr><td style="background:#f7f6f3;padding:36px 48px 40px;border-top:1px solid #edecea;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'

        '<tr><td align="center" style="padding:0 0 18px;">'
        '<span style="font-family:Georgia,serif;font-size:13px;letter-spacing:4px;'
        'color:#aaaaaa;text-transform:uppercase;">' + brand_name + '</span></td></tr>'

        + website_row + social_row +

        '<tr><td style="border-top:1px solid #e8e7e3;font-size:0;">&nbsp;</td></tr>'
        '<tr><td align="center" style="padding:18px 0 0;color:#c0c0c0;font-size:11px;'
        'line-height:1.8;font-family:Arial,sans-serif;">'
        'You received this because you subscribed to '
        '<span style="color:#999;font-weight:600;">' + brand_name + '</span>.<br>'
        'Reply with <span style="color:#999;">&#8220;unsubscribe&#8221;</span> to opt out.'
        '</td></tr>'

        '</table></td></tr>'
        '</table>'

        '<table width="600" cellpadding="0" cellspacing="0" border="0"'
        ' style="max-width:600px;width:100%;margin-top:24px;">'
        '<tr><td align="center" style="color:#b8b5ae;font-size:10px;'
        'letter-spacing:0.14em;text-transform:uppercase;font-family:Arial,sans-serif;">'
        'Sent with MailForge</td></tr></table>'

        '</td></tr></table>'
        '</body></html>'
    )



# ── Google Sheets ─────────────────────────────────────────────────────────────
def fetch_emails_from_sheet(sheet_id: str) -> list:
    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid=0"
    )
    logger.info("Fetching sheet CSV: %s", csv_url)
    req = urllib.request.Request(
        csv_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; MailForge/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"HTTP {e.code} fetching sheet. "
            "Ensure it is shared as 'Anyone with the link → Viewer'."
        )
    except Exception as exc:
        raise RuntimeError(f"Could not fetch sheet: {exc}")

    lines = content.splitlines()
    logger.info("Sheet: %d lines downloaded", len(lines))

    if not lines:
        raise RuntimeError("Sheet is empty.")
    if lines[0].strip().startswith("<!DOCTYPE") or "<html" in lines[0].lower():
        raise RuntimeError(
            "Google returned a login page. "
            "Share the sheet as 'Anyone with the link → Viewer'."
        )

    emails = []
    for line in lines:
        cells = [c.strip().strip('"').strip() for c in line.split(",")]
        for cell in cells:
            if not cell:
                continue
            if cell.lower() in ("email", "emails", "e-mail", "email address"):
                continue
            if _is_valid_email(cell):
                emails.append(cell)

    logger.info("Valid emails found: %d → %s", len(emails), emails)
    return emails


# ── Email builder ─────────────────────────────────────────────────────────────
def _build_message(from_addr: str, to_addr: str,
                   subject: str, message: str, branding: dict) -> MIMEMultipart:
    logo_url = branding.get("logo_url", "").strip()
    has_inline_logo = logo_url.startswith("data:image")

    # Use "related" when we have an inline image so CID attachment works
    # Use "alternative" otherwise (plain + html only)
    if has_inline_logo:
        outer = MIMEMultipart("related")
        alt   = MIMEMultipart("alternative")
        alt.attach(MIMEText(message, "plain", "utf-8"))
        alt.attach(MIMEText(_build_html(message, branding), "html", "utf-8"))
        outer.attach(alt)

        # Decode base64 data URL and attach as inline image with Content-ID
        try:
            header, b64data = logo_url.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]   # e.g. image/png
            img_data  = base64.b64decode(b64data)
            img_part  = MIMEImage(img_data, _subtype=mime_type.split("/")[1])
            img_part.add_header("Content-ID", "<logo_image>")
            img_part.add_header("Content-Disposition", "inline", filename="logo")
            outer.attach(img_part)
        except Exception as e:
            logger.warning("Could not attach logo image: %s", e)
        msg = outer
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(message, "plain", "utf-8"))
        msg.attach(MIMEText(_build_html(message, branding), "html", "utf-8"))

    msg["From"]             = from_addr
    msg["To"]               = to_addr
    msg["Subject"]          = subject
    msg["Date"]             = formatdate(localtime=True)
    msg["Message-ID"]       = make_msgid(domain=from_addr.split("@")[-1])
    msg["MIME-Version"]     = "1.0"
    msg["Precedence"]       = "bulk"
    msg["X-Mailer"]         = "MailForge/1.0"
    msg["List-Unsubscribe"] = f"<mailto:{from_addr}?subject=unsubscribe>"
    return msg


# ── Gmail SMTP sender ─────────────────────────────────────────────────────────
def _connect_gmail(gmail_address: str, app_password: str):
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
    server.login(gmail_address.strip(), app_password.strip())
    return server


def send_emails_gmail(gmail_address: str, app_password: str,
                      recipients: list, subject: str,
                      message: str, branding: dict) -> dict:
    sent, failed, errors = 0, 0, []

    try:
        server = _connect_gmail(gmail_address, app_password)
        logger.info("Gmail SMTP connected as %s", gmail_address)
    except smtplib.SMTPAuthenticationError:
        msg = (
            "Gmail authentication failed. "
            "Use an App Password from myaccount.google.com/apppasswords."
        )
        logger.error(msg)
        return {"sent": 0, "failed": len(recipients),
                "total": len(recipients), "errors": [msg]}
    except Exception as exc:
        logger.error("Gmail SMTP connection failed: %s", exc)
        return {"sent": 0, "failed": len(recipients),
                "total": len(recipients), "errors": [str(exc)]}

    for idx, email in enumerate(recipients):
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                mime_msg = _build_message(
                    gmail_address.strip(), email.strip(),
                    subject, message, branding
                )
                server.sendmail(
                    gmail_address.strip(),
                    email.strip(),
                    mime_msg.as_string()
                )
                logger.info("  [%d/%d] SENT → %s  (attempt %d)",
                            idx + 1, len(recipients), email, attempt)
                sent += 1
                success = True
                break

            except smtplib.SMTPServerDisconnected:
                logger.warning("  Connection lost, reconnecting…")
                try:
                    server = _connect_gmail(gmail_address, app_password)
                    logger.info("  Reconnected.")
                except Exception as reconnect_err:
                    logger.error("  Reconnect failed: %s", reconnect_err)
                    break

            except smtplib.SMTPException as exc:
                err_str = str(exc)
                if "421" in err_str or "rate limit" in err_str.lower():
                    wait = RETRY_DELAY_SECONDS * attempt
                    logger.warning("  Rate limit — waiting %ds…", wait)
                    time.sleep(wait)
                else:
                    logger.error("  SMTP error for %s: %s", email, exc)
                    errors.append(f"{email}: {err_str}")
                    break

            except Exception as exc:
                logger.error("  Error for %s: %s", email, exc)
                errors.append(f"{email}: {str(exc)}")
                break

        if not success and not any(email in e for e in errors):
            errors.append(f"{email}: failed after {MAX_RETRIES} attempts")
            failed += 1

        if idx < len(recipients) - 1:
            logger.info("  Waiting %ds before next send…", SEND_DELAY_SECONDS)
            time.sleep(SEND_DELAY_SECONDS)

    try:
        server.quit()
    except Exception:
        pass

    return {"sent": sent, "failed": failed,
            "total": len(recipients), "errors": errors}


# ── Campaign runner ───────────────────────────────────────────────────────────
def _run_campaign(gmail_address, app_password, sheet_id,
                  subject, message, branding):
    logger.info("=" * 60)
    logger.info("CAMPAIGN START  brand=%s  sheet=%s",
                branding.get("brand_name", "?"), sheet_id)
    logger.info("=" * 60)

    try:
        emails = fetch_emails_from_sheet(sheet_id)
    except Exception as exc:
        logger.error("Sheet fetch failed: %s", exc)
        return

    if not emails:
        logger.error("No valid emails found in sheet.")
        return

    logger.info("Sending to %d recipient(s)…", len(emails))
    results = send_emails_gmail(
        gmail_address, app_password, emails, subject, message, branding
    )

    logger.info("=" * 60)
    logger.info("CAMPAIGN DONE  sent=%d  failed=%d  total=%d",
                results["sent"], results["failed"], results["total"])
    for err in results.get("errors", []):
        logger.error("  ERROR: %s", err)
    logger.info("=" * 60)


# ── Public API ────────────────────────────────────────────────────────────────
def schedule_campaign(scheduler, run_at, gmail_address, app_password,
                      sheet_id, subject, message, branding) -> str:
    job_id = f"campaign_{uuid.uuid4().hex[:8]}"
    scheduler.add_job(
        func=_run_campaign,
        trigger="date",
        run_date=run_at,
        id=job_id,
        kwargs=dict(
            gmail_address=gmail_address,
            app_password=app_password,
            sheet_id=sheet_id,
            subject=subject,
            message=message,
            branding=branding,
        ),
        misfire_grace_time=300,
    )
    logger.info("Job %s scheduled for %s", job_id, run_at.isoformat())
    return job_id