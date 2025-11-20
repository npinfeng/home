from fastapi import FastAPI, Request, responses
from wechatpy import parse_message, create_reply
import pandas as pd
from datetime import datetime
import os

app = FastAPI()
EXCEL_PATH = "wechat_messages.xlsx"

@app.post("/wechat")
async def receive_message(request: Request):
    xml_data = await request.body()
    msg = parse_message(xml_data)

    if msg.type == "text":
        message_data = {
            "接收时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "用户OpenID": msg.source,
            "消息类型": msg.type,
            "消息内容": msg.content.strip()
        }
        save_to_excel(message_data)
        reply = create_reply("消息已收到，感谢反馈！", msg)
        return responses.PlainTextResponse(reply.render())
    
    return responses.PlainTextResponse("success")

def save_to_excel(data: dict):
    if not os.path.exists(EXCEL_PATH):
        df = pd.DataFrame(columns=["接收时间", "用户OpenID", "消息类型", "消息内容"])
        df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")

    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")