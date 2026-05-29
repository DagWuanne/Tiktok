from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# =============================================
# DEV INFORMATION
# =============================================
DEV_INFO = {
    "dev": "Đăng Quân",
    "facebook": "https://www.facebook.com/bdquan185",
    "telegram": "t.me/@vuammo",
    "group": "https://t.me/tienichchanel/"
}
# =============================================

def add_dev_info(response_data):
    """Thêm thông tin dev vào mọi response"""
    if isinstance(response_data, dict):
        # Tránh ghi đè nếu đã có key "dev"
        if "dev" not in response_data:
            response_data["dev"] = DEV_INFO
    return response_data


def ExtractVideoId(inputStr):
    if inputStr.isdigit() and len(inputStr) == 19:
        return inputStr
    if 'vt.tiktok.com' in inputStr:
        try:
            resp = requests.get(inputStr, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True, timeout=10)
            inputStr = resp.url
        except Exception as e:
            print(e)
            return None
    patterns = [r'/(?:video|photo)/(\d{19})', r'/(\d{19})\?']
    for pattern in patterns:
        match = re.search(pattern, inputStr)
        if match:
            return match.group(1)
    return None


def BuffFollow(username):
    cleanUser = username.lstrip('@')
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    session.get('https://tikfollowers.com/free-tiktok-followers', headers=headers)
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
    searchRes = session.post('https://tikfollowers.com/api/search', json={"input": cleanUser, "type": "getUserDetails"}, headers=headers)
    
    if searchRes.status_code != 200:
        return add_dev_info({"x": f"Search lỗi: {searchRes.status_code}"})
        
    data = searchRes.json()
    token = data.get('token')
    user_id = data.get("user_id")
    sec_uid = data.get("sec_uid")

    if not user_id or not sec_uid:
        result = {
            "success": False,
            "status": "error",
            "message": "Missing user_id or sec_uid for follow service.",
            "response": data
        }
        return add_dev_info(result)

    processRes = session.post(
        'https://tikfollowers.com/api/process',
        json={
            "user_id": user_id,
            "sec_uid": sec_uid,
            "type": "followers",
            "token": token
        },
        headers=headers
    )
    
    result = processRes.json()
    return add_dev_info(result)


def BuffLike(videoInput):
    videoId = ExtractVideoId(videoInput)
    if not videoId:
        return add_dev_info({"message": "Không thể lấy video ID"})
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    session.get('https://tikfollowers.com/free-tiktok-like', headers=headers)
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
    searchRes = session.post('https://tikfollowers.com/api/search', json={"input": videoId, "type": "videoDetails"}, headers=headers)
    
    if searchRes.status_code != 200:
        return add_dev_info({"x": f"Search lỗi: {searchRes.status_code}"})
        
    data = searchRes.json()
    token = data.get('token')
    
    processRes = session.post(
        'https://tikfollowers.com/api/process',
        json={"aweme_id": data.get("aweme_id"), "type": "like", "token": token}, 
        headers=headers
    )
    
    result = processRes.json()
    return add_dev_info(result)


def BuffView(videoInput):
    videoId = ExtractVideoId(videoInput)
    if not videoId:
        return add_dev_info({"x": "Không thể lấy video ID"})
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    session.get('https://tikfollowers.com/free-tiktok-video-views', headers=headers)
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
    searchRes = session.post('https://tikfollowers.com/api/search', json={"input": videoId, "type": "videoDetails"}, headers=headers)
    
    if searchRes.status_code != 200:
        return add_dev_info({"x": f"Search failse: {searchRes.status_code}"})
        
    data = searchRes.json()
    token = data.get('token')
    
    processRes = session.post(
        'https://tikfollowers.com/api/process', 
        json={"aweme_id": data.get("aweme_id"), "type": "video_views", "token": token}, 
        headers=headers
    )
    
    result = processRes.json()
    return add_dev_info(result)


@app.route('/api/buff/follow', methods=['GET'])
def ApiFollow():
    username = request.args.get('username')
    if not username:
        return jsonify(add_dev_info({"message": "Thiếu username?username=xxx"})), 400
    return jsonify(BuffFollow(username))


@app.route('/api/buff/like', methods=['GET'])
def ApiLike():
    video = request.args.get('video')
    if not video:
        return jsonify(add_dev_info({"message": "Thiếu video?video=xxx"})), 400
    return jsonify(BuffLike(video))


@app.route('/api/buff/view', methods=['GET'])
def ApiView():
    video = request.args.get('video')
    if not video:
        return jsonify(add_dev_info({"message": "Thiếu video?video=xxx"})), 400
    return jsonify(BuffView(video))


@app.route('/api/buff/all', methods=['GET'])
def ApiAll():
    username = request.args.get('username')
    video = request.args.get('video')
    if not username or not video:
        return jsonify(add_dev_info({"message": "username hoặc video không có?username=xxx&video=xxx"})), 400
    
    result = {
        "follow": BuffFollow(username),
        "like": BuffLike(video),
        "view": BuffView(video)
    }
    return jsonify(add_dev_info(result))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2036, debug=False)
