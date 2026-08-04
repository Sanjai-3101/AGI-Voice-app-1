import os, re, urllib.parse, urllib.request
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

def get_vid(q):
    try:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        ids = re.findall(r"\"videoId\":\"([^\"]+)\"", res)
        return ids[0] if ids else None
    except Exception:
        return None

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/agent", methods=["POST"])
def ai_agent_router():
    d = request.get_json(silent=True)
    if not d or "text_command" not in d:
        abort(400, description="Missing 'text_command' in request body")
    
    cmd = d["text_command"].strip().lower()

    if "youtube" in cmd:
        q = cmd
        pats = [
            "open youtube and search", "open youtube and play",
            "open youtube", "search for", "search",
            "and play", "play", "on youtube"
        ]
        for p in pats:
            q = q.replace(p, "")
        q = q.strip()
        if not q:
            target = "https://www.youtube.com"
        elif vid := get_vid(q):
            target = f"https://www.youtube.com/watch?v={vid}&autoplay=1"
        else:
            target = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"

    elif any(k in cmd for k in ["gmail", "email", "mail", "message"]):
        to, body = "", ""
        reg_to = (
            r"(?:update|send|mail|message)?\s*to\s+"
            r"([a-zA-Z0-9._%+\s]+?)"
            r"(?=\s+(?:and|type|write|saying|with|content|that|message|$))"
        )
        if tm := re.search(reg_to, cmd):
            c = tm.group(1).strip().replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
            to = c if "@" in c else f"{c}@gmail.com"

        reg_body = r"(?:type|write|saying|content|message|that)\s+(.*)"
        if bm := re.search(reg_body, cmd):
            if b := bm.group(1).strip():
                body = b[0].upper() + b[1:]

        if to or body:
            target = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={urllib.parse.quote(to)}&body={urllib.parse.quote(body)}"
        else:
            target = "https://mail.google.com"

    else:
        target = f"https://www.google.com/search?q={urllib.parse.quote_plus(cmd)}"

    return jsonify({"action": "open_tab", "url": target})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
