import os
import re
import time
import logging
from flask import Flask, request, jsonify
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cấu hình qua biến môi trường
TIMEOUT = int(os.getenv("TIMEOUT", 15))
PORT = int(os.getenv("PORT", 3000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Headers mặc định giả lập trình duyệt
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://tikfollowers.com",
    "Referer": "https://tikfollowers.com/"
}

class TikFollowersAPI:
    """Quản lý tương tác với API tikfollowers.com"""
    
    def __init__(self):
        self.session = requests.Session()
        # Cấu hình retry tự động khi gặp lỗi mạng
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(BASE_HEADERS)
        # Khởi tạo session (gọi trang chủ để lấy cookie)
        try:
            self.session.get("https://tikfollowers.com", timeout=TIMEOUT)
            logger.info("Session initialized")
        except Exception as e:
            logger.warning(f"Could not initialize session: {e}")

    def extract_video_id(self, url: str) -> str | None:
        """Trích xuất video ID từ URL TikTok (cả video/photo)"""
        try:
            resp = requests.get(
                url,
                allow_redirects=True,
                timeout=TIMEOUT,
                headers={"User-Agent": BASE_HEADERS["User-Agent"]}
            )
            final_url = resp.url
            html = resp.text

            # Các pattern ưu tiên
            patterns = [
                r'/video/(\d+)',
                r'/photo/(\d+)',
                r'aweme_id=(\d+)',
                r'"aweme_id":"(\d+)"',
            ]
            for p in patterns:
                m = re.search(p, final_url or html)
                if m:
                    return m.group(1)
            # Thử tìm trong HTML
            m = re.search(r'"aweme_id":"(\d+)"', html)
            if m:
                return m.group(1)
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
            return None

    def extract_cooldown(self, message: str) -> int:
        """Trích xuất số giây cooldown từ thông báo lỗi"""
        nums = re.findall(r'(\d+)', str(message))
        return int(nums[0]) if nums else 0

    def search(self, video_id: str) -> dict:
        """Bước 1: Gửi search để lấy token và aweme_id"""
        try:
            resp = self.session.post(
                "https://tikfollowers.com/api/search",
                json={"input": video_id, "type": "videoDetails"},
                timeout=TIMEOUT
            )
            resp.raise_for_status()  # Raise HTTPError for bad status
            data = resp.json()
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"Search HTTP error: {e}, Response: {resp.text[:200] if resp else ''}")
            return {"status": "error", "message": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"status": "error", "message": str(e)}

    def process(self, service_type: str, token: str, username: str, aweme_id: str, amount: int = None) -> dict:
        """Bước 2: Gửi yêu cầu buff (like/view/follow/comment)"""
        payload = {
            "username": username,
            "aweme_id": aweme_id,
            "type": service_type,
            "service_type": service_type,
            "token": token
        }
        if amount and service_type in ["view", "like"]:  # Một số dịch vụ cho phép tùy chỉnh số lượng
            payload["amount"] = amount

        try:
            resp = self.session.post(
                "https://tikfollowers.com/api/process",
                json=payload,
                timeout=TIMEOUT + 10
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Process HTTP error: {e}, Response: {resp.text[:200] if resp else ''}")
            return {"status": "error", "message": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Process error: {e}")
            return {"status": "error", "message": str(e)}

    def execute_service(self, service_type: str, video_url: str, amount: int = None) -> dict:
        """Chuỗi hoàn chỉnh: extract ID -> search -> process -> response"""
        # Xác thực link
        video_id = self.extract_video_id(video_url)
        if not video_id:
            return {"success": False, "message": "Không thể trích xuất video ID từ link"}

        logger.info(f"Processing {service_type} for video_id={video_id}")

        # Bước search
        search_result = self.search(video_id)
        if search_result.get("status") != "success":
            return {
                "success": False,
                "stage": "search",
                "message": search_result.get("message", "Search thất bại"),
                "response": search_result
            }

        token = search_result.get("token")
        username = search_result.get("username")
        aweme_id = search_result.get("aweme_id")
        if not aweme_id:
            return {"success": False, "message": "Không lấy được aweme_id từ search"}

        # Bước process
        process_result = self.process(service_type, token, username, aweme_id, amount)
        
        # Xử lý lỗi token
        if process_result.get("status") == "error":
            msg = process_result.get("message", "")
            if "token" in msg.lower() or "InvalidOrExpiredToken" in msg:
                return {
                    "success": False,
                    "message": "Token hết hạn hoặc không hợp lệ. Hãy thử lại sau 5-10 giây."
                }
            cooldown = self.extract_cooldown(msg)
            if cooldown > 0:
                return {
                    "success": False,
                    "cooldown": True,
                    "wait_time": cooldown,
                    "message": f"Vui lòng chờ {cooldown}s rồi thử lại."
                }
            return {"success": False, "message": msg}

        # Thành công: trích xuất dữ liệu thống kê nếu có
        data = process_result.get("response", {}).get("data") or process_result.get("data", {})
        stats = data.get("stats", {}) or process_result.get("stats", {})
        
        result = {
            "success": True,
            "service": service_type,
            "username": data.get("username") or username,
            "video_id": data.get("aweme_id") or aweme_id,
            "amount_processed": data.get("amount_processed", amount or "default"),
            "stats": {
                "likes": stats.get("digg_count"),
                "comments": stats.get("comment_count"),
                "shares": stats.get("share_count"),
                "favorites": stats.get("collect_count"),
                "views": stats.get("play_count")
            },
            "message": "Buff thành công"
        }
        return result

# Khởi tạo instance API toàn cục
tiktok_api = TikFollowersAPI()

# ---------------- API Endpoints ----------------

@app.route("/api/like")
def api_like():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400
    amount = request.args.get("amount", type=int)  # cho phép ?amount=100 (nếu API hỗ trợ)
    result = tiktok_api.execute_service("like", link, amount)
    return jsonify(result)

@app.route("/api/view")
def api_view():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400
    amount = request.args.get("amount", type=int)
    result = tiktok_api.execute_service("view", link, amount)
    return jsonify(result)

@app.route("/api/follow")
def api_follow():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400
    result = tiktok_api.execute_service("follow", link)
    return jsonify(result)

@app.route("/api/comment")
def api_comment():
    link = request.args.get("link", "").strip()
    if not link:
        return jsonify({"success": False, "message": "Thiếu ?link="}), 400
    result = tiktok_api.execute_service("comment", link)
    return jsonify(result)

@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "service": "TikTok Buff API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
