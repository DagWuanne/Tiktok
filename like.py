from flask import Flask, request, jsonify
from urllib.parse import unquote
import requests
import re
import os
import time

app = Flask(__name__)

HEADERS = {
    "User-Agent":"Mozilla/5.0"
}

def extract_video_id(url):
    try:

        url = unquote(url)

        try:
            r = requests.get(
                url,
                headers=HEADERS,
                allow_redirects=True,
                timeout=15
            )

            full_url = r.url

        except:
            full_url = url

        patterns = [
            r"/video/(\d+)",
            r"video/(\d+)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                full_url
            )

            if match:
                return match.group(1)

        return None

    except:
        return None


def extract_cooldown(msg):

    try:

        m = re.search(
            r"(\d+)\s*minute\(s\).*?(\d+)\s*second\(s\)",
            msg
        )

        if m:

            minute = int(m.group(1))
            second = int(m.group(2))

            return {
                "minutes":minute,
                "seconds":second,
                "total_seconds":minute*60+second
            }

        s = re.search(
            r"(\d+)\s*second\(s\)",
            msg
        )

        if s:

            second=int(
                s.group(1)
            )

            return {
                "minutes":0,
                "seconds":second,
                "total_seconds":second
            }

    except:
        pass

    return {
        "minutes":0,
        "seconds":0,
        "total_seconds":0
    }


@app.route("/")
def home():

    return jsonify({

        "developer":"Đăng Quân",

        "status":"running",

        "api":
        "/api/like?link=https://vt.tiktok.com/xxxxx/"
    })


@app.route("/api/like")
def api_like():

    link = unquote(
        request.args.get(
            "link",
            ""
        )
    )

    if not link:

        return jsonify({

            "success":False,

            "message":
            "Thiếu ?link="

        }),400


    video_id = extract_video_id(
        link
    )

    if not video_id:

        return jsonify({

            "success":False,

            "message":
            "Không lấy được ID video"

        })


    try:

        search = requests.post(

            "https://tikfollowers.com/api/search",

            json={

                "input":video_id,

                "type":"videoDetails"

            },

            headers=HEADERS,

            timeout=20

        ).json()


        if search.get(
            "status"
        ) != "success":

            return jsonify({

                "success":False,

                "stage":"search",

                "response":
                search

            })


        payload = search.copy()

        payload["type"]="like"

        payload.pop(
            "status",
            None
        )

        time.sleep(1)

        process = requests.post(

            "https://tikfollowers.com/api/process",

            json=payload,

            headers=HEADERS,

            timeout=20

        ).json()


        if process.get(
            "status"
        ) == "error":

            cooldown = extract_cooldown(

                process.get(
                    "message",
                    ""
                )

            )

            return jsonify({

                "success":False,

                "cooldown":True,

                "wait_time":
                cooldown,

                "message":
                process.get(
                    "message"
                )

            })


        data = process.get(
            "response",
            {}
        ).get(
            "data",
            {}
        )

        stats = data.get(
            "stats",
            {}
        )

        return jsonify({

            "success":True,

            "cooldown":False,

            "username":
            data.get(
                "username"
            ),

            "video_id":
            data.get(
                "aweme_id"
            ),

            "amount_processed":
            data.get(
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

            "message":
            "Buff thành công"

        })

    except Exception as e:

        return jsonify({

            "success":False,

            "error":
            str(e)

        })


if __name__=="__main__":

    port=int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
