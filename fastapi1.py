from fastapi import FastAPI, Request
import hashlib
import xmltodict
import pandas as pd
import os
import time

app = FastAPI()

# -------- 微信公众号配置（你自己填写） --------
TOKEN = "your_token"

# -------- Excel 文件 --------
EXCEL_FILE = "wechat_messages.xlsx"


# 签名验证（微信绑定服务器时用）
@app.get("/wechat")
def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    check = ''.join(sorted([TOKEN, timestamp, nonce]))
    hashcode = hashlib.sha1(check.encode()).hexdigest()

    if hashcode == signature:
        return echostr
    return "verification failed"


# 接收用户发来的微信消息
@app.post("/wechat")
async def wechat_message(request: Request):
    xml = await request.body()
    msg = xmltodict.parse(xml)["xml"]

    data = {
        "sender": msg["FromUserName"],
        "content": msg.get("Content", ""),
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }

    # 写入 excel
    df = pd.DataFrame([data])
    if os.path.exists(EXCEL_FILE):
        old = pd.read_excel(EXCEL_FILE)
        df = pd.concat([old, df], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)

    # 回复消息
    reply = f"""
    <xml>
        <ToUserName><![CDATA[{msg['FromUserName']}]]></ToUserName>
        <FromUserName><![CDATA[{msg['ToUserName']}]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[消息已收到，已保存到Excel]]></Content>
    </xml>
    """
    return reply


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wechat_receive:app", host="0.0.0.0", port=8000)