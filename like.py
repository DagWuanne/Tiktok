from flask import Flask, request, jsonify
import requests
import re
import time

app = Flask(__name__)

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

INFO = {
    "developer": "Đăng Quân",
    "telegram": "@vuammo",
    "group": "t.me/tienichchanel"
}


def extract_video_id(url):
    try:
        response = requests.head(
            url,
            headers=COMMON_HEADERS,
            allow_redirects=True,
            timeout=10
        )

        long_url = response.url

        match = re.search(r"/video/(\d+)", long_url)

        if match:
            return match.group(1)

        return None

    except Exception:
        return None


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "api": "/api/like?link=TIKTOK_URL",
        "developer": INFO["developer"],
        "telegram": INFO["telegram"],
        "group": INFO["group"]
    })


@app.route("/api/like", methods=["GET"])
def process_buff_like():

    input_url = request.args.get("link")

    if not input_url:
        return jsonify({
            "success": False,
            "message": "Thiếu tham số ?link=",
            **INFO
        }), 400

    video_id = extract_video_id(input_url)

    if not video_id:
        return jsonify({
            "success": False,
            "message": "Không thể lấy ID video từ link",
            **INFO
        }), 400

    try:

        search_payload = {
            "input": str(video_id),
            "type": "videoDetails"
        }

        search_res = requests.post(
            "https://tikfollowers.com/api/search",
            json=search_payload,
            headers=COMMON_HEADERS,
            timeout=15
        )

        search_data = search_res.json()

        if search_data.get("status") != "success":
            return jsonify({
                "success": False,
                "stage": "search",
                "message": "Không lấy được thông tin video",
                "response": search_data,
                **INFO
            })

        process_payload = search_data.copy()

        process_payload["type"] = "like"

        process_payload.pop("status", None)

        time.sleep(1)

        process_res = requests.post(
            "https://tikfollowers.com/api/process",
            json=process_payload,
            headers=COMMON_HEADERS,
            timeout=15
        )

        process_data = process_res.json()

        if process_data.get("status") != "success":
            return jsonify({
                "success": False,
                "stage": "process",
                "message": "Không thể xử lý buff like",
                "response": process_data,
                **INFO
            })

        data = process_data.get("data", {})
        stats = data.get("stats", {})

        return jsonify({
            "success": True,
            "video_id": video_id,
            "username": data.get("username"),
            "current_views": stats.get("play_count", 0),
            "current_likes": stats.get("digg_count", 0),
            "comments": stats.get("comment_count", 0),
            "shares": stats.get("share_count", 0),
            "likes_sent": data.get("amount_processed", 0),
            "message": process_data.get("message"),
            **INFO
        })

    except requests.Timeout:
        return jsonify({
            "success": False,
            "message": "Timeout server nguồn",
            **INFO
        }), 504

    except requests.RequestException as e:
        return jsonify({
            "success": False,
            "message": str(e),
            **INFO
        }), 502

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            **INFO
        }), 500

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
