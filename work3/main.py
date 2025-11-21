import os
import requests
from fastapi import FastAPI, Query, Response

app = FastAPI()

# ---------------- 微信配置 ----------------
APPID = os.getenv("APPID", "YOUR_APPID")
APPSECRET = os.getenv("APPSECRET", "YOUR_APPSECRET")

# access_token 缓存
ACCESS_TOKEN_CACHE = {"token": None, "expires_at": 0}

def get_access_token():
    """获取微信公众号 access_token（自动缓存）"""
    import time
    if ACCESS_TOKEN_CACHE["token"] and ACCESS_TOKEN_CACHE["expires_at"] > time.time():
        return ACCESS_TOKEN_CACHE["token"]
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    resp = requests.get(url)
    data = resp.json()
    if "access_token" in data:
        ACCESS_TOKEN_CACHE["token"] = data["access_token"]
        ACCESS_TOKEN_CACHE["expires_at"] = time.time() + data["expires_in"] - 60
        return data["access_token"]
    else:
        raise Exception(f"获取 access_token 失败: {data}")

def push_text_message(to_user_openid: str, content: str):
    """向单个用户发送文本消息"""
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    payload = {
        "touser": to_user_openid,
        "msgtype": "text",
        "text": {"content": content}
    }
    resp = requests.post(url, json=payload)
    return resp.json()

# ---------------- 根接口 ----------------
@app.get("/")
async def root():
    return {"status": "running", "service": "WeChat Push Only"}

# ---------------- 主动推送接口 ----------------
@app.post("/push")
async def push_message(
    content: str = Query(..., description="要发送的文本消息"),
    openids: str = Query(..., description="粉丝 OpenID 列表，用逗号分隔")
):
    """
    主动向指定用户推送消息
    openids 示例: "openid1,openid2,openid3"
    """
    user_list = [o.strip() for o in openids.split(",") if o.strip()]
    if not user_list:
        return {"error": "没有有效 OpenID"}

    results = []
    for openid in user_list:
        try:
            resp = push_text_message(openid, content)
            results.append({"openid": openid, "status": resp})
        except Exception as e:
            results.append({"openid": openid, "status": str(e)})

    return {"pushed_count": len(results), "results": results}

# ---------------- 启动 ----------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)