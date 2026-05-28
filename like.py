from flask import Flask, request, jsonify
import requests
import re
import time

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def safe_post(url, payload, timeout=15):
    try:
        r = requests.post(
            url,
            json=payload,
            headers=HEADERS,
            timeout=timeout
        )

        if r.status_code != 200:
            return {
                "status": "error",
                "message": f"HTTP {r.status_code}"
            }

        try:
            return r.json()
        except:
            return {
                "status": "error",
                "message": "Response không phải JSON"
            }

    except requests.Timeout:
        return {
            "status": "error",
            "message": "Timeout"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def extract_video_id(url):
    try:

        r = requests.get(
            url,
            allow_redirects=True,
            timeout=15,
            headers={
                "User-Agent":"Mozilla/5.0"
            }
        )

        final_url = r.url

        patterns = [
            r'/video/(\d+)',
            r'/photo/(\d+)',
            r'aweme_id=(\d+)'
        ]

        for p in patterns:
            m = re.search(p, final_url)

            if m:
                return m.group(1)

        html = r.text

        m = re.search(
            r'"aweme_id":"(\d+)"',
            html
        )

        if m:
            return m.group(1)

        return None

    except:
        return None


def extract_cooldown(text):

    try:

        text = str(text)

        m = re.findall(
            r'(\d+)',
            text
        )

        if not m:
            return 0

        return int(m[0])

    except:
        return 0


@app.route("/api/like")
def api_like():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400

    video_id = extract_video_id(link)
    if not video_id:
        return jsonify({"success": False, "message": "Không lấy được video ID"}), 400

    try:
        # Headers mạnh hơn
        search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://tikfollowers.com",
            "Referer": "https://tikfollowers.com/"
        }

        # === SEARCH ===
        search_resp = requests.post(
            "https://tikfollowers.com/api/search",
            json={"input": video_id, "type": "videoDetails"},
            headers=search_headers,
            timeout=15
        )

        # Debug nếu vẫn lỗi 400
        if search_resp.status_code == 400:
            return jsonify({
                "success": False,
                "stage": "search",
                "message": f"HTTP 400 - Server từ chối request. Có thể video không tồn tại hoặc bị chặn.",
                "status_code": search_resp.status_code,
                "response": search_resp.text[:500]  # Trả về nội dung lỗi
            })

        search_data = search_resp.json()

        if search_data.get("status") != "success":
            return jsonify({
                "success": False,
                "stage": "search",
                "message": search_data.get("message", "Search thất bại"),
                "response": search_data
            })

        token = search_data.get("token")
        username = search_data.get("username")
        aweme_id = search_data.get("aweme_id")

        if not aweme_id:
            return jsonify({"success": False, "message": "Không lấy được aweme_id"})

        # === PROCESS ===
        process_headers = search_headers.copy()
        payload = {
            "username": username,
            "aweme_id": aweme_id,
            "type": "like",
            "service_type": "like",
            "token": token
        }

        process_resp = requests.post(
            "https://tikfollowers.com/api/process",
            json=payload,
            headers=process_headers,
            timeout=20
        ).json()

        if process_resp.get("status") == "error":
            msg = process_resp.get("message", "")
            if "token" in msg.lower() or "InvalidOrExpiredToken" in msg:
                return jsonify({
                    "success": False,
                    "message": "Token lỗi. Thử lại sau 5-10 giây."
                })
            
            cooldown = extract_cooldown(msg)
            return jsonify({
                "success": False,
                "cooldown": True,
                "wait_time": cooldown,
                "message": msg
            })

        # Thành công
        data = process_resp.get("response", {}).get("data") or process_resp.get("data", {})
        stats = data.get("stats", {}) or process_resp.get("stats", {})

        return jsonify({
            "success": True,
            "cooldown": False,
            "username": data.get("username") or username,
            "video_id": data.get("aweme_id") or aweme_id,
            "amount_processed": data.get("amount_processed", 15),
            "current_views": stats.get("play_count"),
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
            "message": "Lỗi kết nối",
            "error": str(e)
        }), 500

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False
    )
