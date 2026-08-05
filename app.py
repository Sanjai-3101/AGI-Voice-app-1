import os
import re
import urllib.parse
import urllib.request
from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Agent</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f4f4f9;
        }
        .container {
            background: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            width: 320px;
        }
        h2 {
            margin-bottom: 20px;
            color: #333;
        }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s ease;
        }
        button:hover {
            background-color: #0056b3;
        }
        #status {
            margin-top: 15px;
            font-size: 14px;
            color: #666;
            min-height: 20px;
        }
    </style>
</head>
<body>

<div class="container">
    <h2>🎤 Voice Agent</h2>
    <button onclick="start()">Speak</button>
    <p id="status"></p>
</div>

<script>
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const s = document.getElementById("status");

async function send(cmd) {
    s.innerText = "Processing command: " + cmd;
    try {
        let r = await fetch("/agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text_command: cmd })
        });
        let d = await r.json();
        if (d.error) {
            return s.innerText = d.error;
        }
        s.innerText = "Opening link...";
        window.open(d.url, "_blank");
    } catch (err) {
        s.innerText = "Error connecting to server.";
    }
}

function start() {
    if (!SR) return alert("Web Speech API not supported. Please use Chrome or Edge.");
    let rec = new SR();
    rec.lang = "en-US";
    rec.onresult = e => send(e.results[0][0].transcript);
    rec.onerror = e => s.innerText = "Error: " + e.error;
    s.innerText = "Listening...";
    rec.start();
}
</script>

</body>
</html>
"""

def find_first_video_id(query):
    try:
        req = urllib.request.Request(
            "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query),
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US", "Cookie": "SOCS=CAI"}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode()
        m = re.search(r'(?:"videoId":|/watch\?v=)"([A-Za-z0-9_-]{11})"', html)
        return m.group(1) if m else None
    except Exception as e:
        print("Scraper error:", e)
        return None

def build_youtube_target(cmd):
    play = "play" in cmd
    q = re.sub(r"(open youtube( and (play|search))?|play|search( for)?|on youtube)", "", cmd).strip()
    if not q:
        return "https://www.youtube.com"
    if play:
        vid = find_first_video_id(q)
        if vid:
            return f"https://www.youtube.com/watch?v={vid}&autoplay=1"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)

def build_gmail_target(cmd):
    to = ""
    body = ""
    if m := re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))", cmd):
        to = m.group(1).replace(" ", "")
        if "@" not in to:
            to += "@gmail.com"
    if m := re.search(r"(type|saying)\s+(.*)", cmd):
        body = m.group(2).capitalize()
    if not (to or body):
        return "https://mail.google.com"
    return "https://mail.google.com/mail/u/0/?" + urllib.parse.urlencode(
        {"view": "cm", "fs": "1", "to": to, "body": body}
    )

@app.route("/")
def home():
    return render_template_string(HTML)

@app.post("/agent")
def agent():
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing command")
    cmd = data["text_command"].lower().strip()
    
    if "youtube" in cmd or "play" in cmd:
        return jsonify(action="open_tab", url=build_youtube_target(cmd))
    if any(k in cmd for k in ["gmail", "email", "mail"]):
        return jsonify(action="open_tab", url=build_gmail_target(cmd))
        
    return jsonify(error="Only YouTube and Gmail commands supported.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
