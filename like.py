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

    link = request.args.get(
        "link",
        ""
    ).strip()

    if not link:

        return jsonify({
            "success":False,
            "message":"Thiếu ?link="
        }),400


    video_id = extract_video_id(
        link
    )


    if not video_id:

        return jsonify({
            "success":False,
            "message":"Không lấy được video ID"
        }),400


    try:

        process_resp = None

        for attempt in range(3):

            search_resp = safe_post(
                "https://tikfollowers.com/api/search",
                {
                    "input":video_id,
                    "type":"videoDetails"
                }
            )


            if search_resp.get(
                "status"
            ) != "success":

                return jsonify({
                    "success":False,
                    "stage":"search",
                    "message":
                    search_resp.get(
                        "message",
                        "Search thất bại"
                    )
                })


            payload = {

                "username":
                search_resp.get(
                    "username"
                ),

                "aweme_id":
                search_resp.get(
                    "aweme_id"
                ),

                "type":
                "like",

                "service_type":
                "like",

                "token":
                search_resp.get(
                    "token"
                )
            }


            process_resp = safe_post(
                "https://tikfollowers.com/api/process",
                payload,
                20
            )


            msg = str(
                process_resp.get(
                    "message",
                    ""
                )
            )


            if (
                process_resp.get(
                    "status"
                ) != "error"
            ):

                break


            if (
                "InvalidOrExpiredToken"
                in msg
            ):

                time.sleep(1)

                continue

            break


        if process_resp.get(
            "status"
        ) == "error":

            msg = process_resp.get(
                "message",
                "Lỗi không xác định"
            )


            cooldown = extract_cooldown(
                msg
            )


            return jsonify({

                "success":False,

                "cooldown":
                cooldown > 0,

                "wait_time":{

                    "minutes":
                    cooldown//60,

                    "seconds":
                    cooldown%60,

                    "total_seconds":
                    cooldown
                },

                "message":
                msg

            })


        data = (

            process_resp.get(
                "response",
                {}
            ).get(
                "data",
                {}
            )

            or

            process_resp.get(
                "data",
                {}
            )

        )


        stats = (

            data.get(
                "stats",
                {}
            )

            or

            process_resp.get(
                "stats",
                {}
            )

        )


        return jsonify({

            "success":True,

            "cooldown":False,

            "username":
            data.get(
                "username"
            )
            or
            payload["username"],


            "video_id":
            data.get(
                "aweme_id"
            )
            or
            payload["aweme_id"],


            "amount_processed":
            data.get(
                "amount_processed",
                15
            ),


            "current_views":
            stats.get(
                "play_count",
                0
            ),


            "stats":{

                "likes":
                stats.get(
                    "digg_count",
                    0
                ),

                "comments":
                stats.get(
                    "comment_count",
                    0
                ),

                "shares":
                stats.get(
                    "share_count",
                    0
                ),

                "favorites":
                stats.get(
                    "collect_count",
                    0
                ),

                "views":
                stats.get(
                    "play_count",
                    0
                )
            },

            "message":
            "Buff thành công"

        })


    except Exception as e:

        return jsonify({

            "success":False,

            "message":
            "Lỗi server",

            "error":
            str(e)

        }),500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False
    )
