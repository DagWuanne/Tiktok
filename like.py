from flask import Flask, request, jsonify
from urllib.parse import unquote
import requests
import re
import os
import time

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}

def extract_video_id(url):
    try:
        url = unquote(url.strip())
        try:
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
            full_url = r.url
        except:
            full_url = url

        patterns = [
            r"/video/(\d{18,20})",
            r"(\d{18,20})"
        ]

        for pattern in patterns:
            match = re.search(pattern, full_url)
            if match:
                return match.group(1)
        return None
    except:
        return None


def extract_cooldown(msg):
    try:
        m = re.search(r"(\d+)\s*minute\(s\).*?(\d+)\s*second\(s\)", msg)
        if m:
            return {
                "minutes": int(m.group(1)),
                "seconds": int(m.group(2)),
                "total_seconds": int(m.group(1))*60 + int(m.group(2))
            }
        s = re.search(r"(\d+)\s*second\(s\)", msg)
        if s:
            sec = int(s.group(1))
            return {"minutes": 0, "seconds": sec, "total_seconds": sec}
    except:
        pass
    return {"minutes": 0, "seconds": 0, "total_seconds": 0}


@app.route("/")
def home():
    return jsonify({
        "developer": "Đăng Quân",
        "status": "running",
        "api": "/api/like?link=..."
    })


@app.route("/api/like")
def api_like():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400

    video_id = extract_video_id(link)
    if not video_id:
        return jsonify({"success": False, "message": "Không lấy được video ID"}), 400

    try:
        # Search
        search_resp = requests.post(
            "https://tikfollowers.com/api/search",
            json={"input": video_id, "type": "videoDetails"},
            headers=HEADERS,
            timeout=15
        ).json()

        if search_resp.get("status") != "success":
            return jsonify({
                "success": False,
                "stage": "search",
                "message": search_resp.get("message", "Search thất bại")
            })

        # Process
        payload = {
            "username": search_resp.get("username"),
            "aweme_id": search_resp.get("aweme_id"),
            "type": "like",
            "service_type": "like"
        }

        time.sleep(1)

        process_resp = requests.post(
            "https://tikfollowers.com/api/process",
            json=payload,
            headers=HEADERS,
            timeout=20
        ).json()

        if process_resp.get("status") == "error":
            cooldown = extract_cooldown(process_resp.get("message", ""))
            return jsonify({
                "success": False,
                "cooldown": True,
                "wait_time": cooldown,
                "message": process_resp.get("message")
            })

        # Response thành công
        data = process_resp.get("response", {}).get("data") or process_resp.get("data", {})
        stats = data.get("stats", {}) or process_resp.get("stats", {})

        return jsonify({
            "success": True,
            "cooldown": False,
            "username": data.get("username") or search_resp.get("username"),
            "video_id": data.get("aweme_id") or video_id,
            "amount_processed": data.get("amount_processed", 15),
            "current_views": stats.get("play_count") or process_resp.get("current_views"),
            "stats": {
                "likes": stats.get("digg_count"),
                "comments": stats.get("comment_count"),
                "shares": stats.get("share_count"),
                "favorites": stats.get("collect_count"),
                "views": stats.get("play_count")
            },
            "message": "Buff thành công"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Lỗi khi buff",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
