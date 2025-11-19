from fastapi import FastAPI
import requests
import time

app = FastAPI()

APPID = "your_appid"
SECRET = "your_secret"

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    return requests.get(url).json()["access_token"]


@app.get("/push")
def push(openid: str, text: str):
    token = get_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"

    data = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": text}
    }

    res = requests.post(url, json=data).json()
    return res


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wechat_push:app", host="0.0.0.0", port=8000)