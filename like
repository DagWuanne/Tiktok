from flask import Flask, request, jsonify
import requests
import re
import time

app = Flask(__name__)

COMMON_HEADERS = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0'
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
        match = re.search(r'/video/(\d+)', long_url)
        if match:
            return match.group(1)
        return None
    except:
        return None

@app.route('/')
def process_buff_like():
    input_url = request.args.get("link")

    if not input_url:
        return jsonify({
            "success": False,
            "message": "Thiếu ?link="
        }), 400

    video_id = extract_video_id(input_url)

    if not video_id:
        return jsonify({
            "success": False,
            "message": "Không lấy được ID video"
        }), 400

    try:
        # Bước 1: Tìm kiếm thông tin video để lấy stats (likes hiện tại)
        search_res = requests.post(
            "https://tikfollowers.com/api/search",
            json={
                "input": str(video_id),
                "type": "videoDetails"
            },
            headers=COMMON_HEADERS,
            timeout=15
        )
        search_data = search_res.json()

        if search_data.get("status") != "success":
            return jsonify({
                "success": False,
                "stage": "search",
                "data": search_data
            })

        # Lấy số likes trước khi buff
        likes_before = search_data.get("stats", {}).get("digg_count", 0)

        # Bước 2: Gửi yêu cầu buff like
        payload = search_data.copy()
        payload["type"] = "like"
        payload.pop("status", None)  # bỏ status cũ

        time.sleep(1)

        process_res = requests.post(
            "https://tikfollowers.com/api/process",
            json=payload,
            headers=COMMON_HEADERS,
            timeout=15
        )
        process_data = process_res.json()

        # Lấy số like đã xử lý
        amount_processed = process_data.get("data", {}).get("amount_processed", 0)

        # Tính likes sau buff (ước lượng)
        likes_after = likes_before + amount_processed

        # Đóng gói kết quả trả về chỉ những thứ cần thiết
        result = {
            "success": process_data.get("status") == "success",
            "video_id": video_id,
            "username": search_data.get("username"),
            "likes_before": likes_before,
            "likes_after": likes_after,
            "amount_processed": amount_processed,
            "message": process_data.get("message", ""),
            "status": process_data.get("status", "error")
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
