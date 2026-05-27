from flask import Flask, request, jsonify
from urllib.parse import unquote
import requests
import re
import time
import os

app = Flask(__name__)

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}

def extract_video_id(url):
    try:
        url = unquote(url)

        try:
            r = requests.head(
                url,
                headers=COMMON_HEADERS,
                allow_redirects=True,
                timeout=10
            )
        except:
            r = requests.get(
                url,
                headers=COMMON_HEADERS,
                allow_redirects=True,
                timeout=10
            )

        long_url = r.url

        match = re.search(
            r"/video/(\d+)",
            long_url
        )

        if match:
            return match.group(1)

        match = re.search(
            r"video/(\d+)",
            url
        )

        return match.group(1) if match else None

    except:
        return None


def extract_cooldown(message):
    try:

        result = re.search(
            r"(\d+)\s*minute\(s\).*?(\d+)\s*second\(s\)",
            message
        )

        if result:

            minute = int(result.group(1))
            second = int(result.group(2))

            return {
                "minutes": minute,
                "seconds": second,
                "total_seconds": minute * 60 + second
            }

        result = re.search(
            r"(\d+)\s*second\(s\)",
            message
        )

        if result:

            second = int(result.group(1))

            return {
                "minutes": 0,
                "seconds": second,
                "total_seconds": second
            }

    except:
        pass

    return {
        "minutes": 0,
        "seconds": 0,
        "total_seconds": 0
    }


@app.route("/api/like", methods=["GET"])
def process_buff_like():

    link = unquote(
        request.args.get(
            "link",
            ""
        )
    )

    if not link:

        return jsonify({
            "success": False,
            "message": "Thiếu ?link="
        }),400


    video_id = extract_video_id(link)

    if not video_id:

        return jsonify({
            "success": False,
            "message": "Không lấy được ID video"
        })


    try:

        search = requests.post(
            "https://tikfollowers.com/api/search",
            json={
                "input": video_id,
                "type": "videoDetails"
            },
            headers=COMMON_HEADERS,
            timeout=15
        ).json()


        if search.get("status") != "success":

            return jsonify({
                "success": False,
                "stage": "search",
                "response": search
            })


        payload = search.copy()

        payload["type"] = "like"

        payload.pop(
            "status",
            None
        )

        time.sleep(1)

        process = requests.post(
            "https://tikfollowers.com/api/process",
            json=payload,
            headers=COMMON_HEADERS,
            timeout=15
        ).json()


        if process.get("status") == "error":

            cooldown = extract_cooldown(
                process.get(
                    "message",
                    ""
                )
            )

            return jsonify({

                "success": False,
                "cooldown": True,

                "username":
                process.get(
                    "data",
                    {}
                ).get(
                    "username"
                ),

                "video_id":
                process.get(
                    "data",
                    {}
                ).get(
                    "target_identifier"
                ),

                "wait_time":
                cooldown,

                "message":
                process.get(
                    "message"
                )
            })


        stats = process.get(
            "stats",
            {}
        )


        return jsonify({

            "success": True,
            "cooldown": False,

            "username":
            process.get(
                "username"
            ),

            "video_id":
            process.get(
                "aweme_id"
            ),

            "amount_processed":
            process.get(
                "amount_processed",
                15
            ),

            "current_views":
            stats.get(
                "play_count"
            ),

            "stats":{

                "likes":
                stats.get(
                    "digg_count"
                ),

                "comments":
                stats.get(
                    "comment_count"
                ),

                "shares":
                stats.get(
                    "share_count"
                ),

                "favorites":
                stats.get(
                    "collect_count"
                ),

                "views":
                stats.get(
                    "play_count"
                )
            },

            "message":"Buff thành công"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "error": str(e)

        })


@app.route("/")
def home():

    return jsonify({
        "developer":"Đăng Quân",
        "status":"running",
        "api":"/api/like?link=tiktok_url"
    })


if __name__ == "__main__":

    PORT = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
