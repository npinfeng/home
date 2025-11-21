from fastapi import FastAPI, Request, responses
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
import pandas as pd
from datetime import datetime
import os
import traceback

# ---------------- 微信配置 ----------------
TOKEN = os.getenv("TOKEN")
APPID = os.getenv("APPID")
APPSECRET = os.getenv("APPSECRET")

if not (TOKEN and APPID and APPSECRET):
    print("⚠️ 环境变量未配置完整：TOKEN, APPID, APPSECRET")
    TOKEN = TOKEN or "YOUR_TOKEN"
    APPID = APPID or "YOUR_APPID"
    APPSECRET = APPSECRET or "YOUR_APPSECRET"

# Excel 文件路径（容器临时目录）
EXCEL_FILENAME = "wechat_messages.xlsx"
LOCAL_TEMP_PATH = f"/tmp/{EXCEL_FILENAME}"

app = FastAPI()

# ---------------- 工具函数 ----------------
def get_excel_df() -> pd.DataFrame:
    """获取 Excel 数据（不存在则返回空 DataFrame）"""
    try:
        if os.path.exists(LOCAL_TEMP_PATH):
            df = pd.read_excel(LOCAL_TEMP_PATH, engine="openpyxl")
            return df
        else:
            return pd.DataFrame(columns=["接收时间", "用户OpenID", "消息类型", "消息内容", "消息ID"])
    except Exception:
        print(f"加载 Excel 失败：{traceback.format_exc()}")
        return pd.DataFrame(columns=["接收时间", "用户OpenID", "消息类型", "消息内容", "消息ID"])

def save_excel_df(df: pd.DataFrame):
    """保存 DataFrame 到本地 Excel（去重后保存）"""
    df = df.drop_duplicates(subset=["消息ID"], keep="last")
    df.to_excel(LOCAL_TEMP_PATH, index=False, engine="openpyxl")
    print(f"Excel 已保存，当前共 {len(df)} 条消息")

# ---------------- 微信接口 ----------------
@app.get("/wechat")
async def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    """微信服务器验证接口"""
    try:
        check_signature(TOKEN, signature, timestamp, nonce)
        return responses.PlainTextResponse(echostr)
    except InvalidSignatureException:
        return responses.PlainTextResponse("Invalid signature", status_code=403)

@app.post("/wechat")
async def receive_message(request: Request, signature: str, timestamp: str, nonce: str):
    """接收公众号消息"""
    try:
        check_signature(TOKEN, signature, timestamp, nonce)
    except InvalidSignatureException:
        return responses.PlainTextResponse("Invalid signature", status_code=403)

    try:
        xml_data = await request.body()
        msg = parse_message(xml_data)
        print(f"收到消息: 类型={msg.type}, 用户={msg.source}, 内容={getattr(msg, 'content', '无')}")
    except Exception:
        return responses.PlainTextResponse("Parse message failed", status_code=500)

    # 处理消息内容
    if msg.type == "text":
        content = msg.content.strip()
    elif msg.type in ["image", "voice", "video", "shortvideo"]:
        content = getattr(msg, "media_id", "无")
    elif msg.type in ["location", "link"]:
        content = getattr(msg, "title", "无")
    else:
        content = "未处理消息"

    message_data = {
        "接收时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "用户OpenID": msg.source,
        "消息类型": msg.type,
        "消息内容": content,
        "消息ID": msg.id
    }

    # 保存 Excel
    df = get_excel_df()
    df = pd.concat([df, pd.DataFrame([message_data])], ignore_index=True)
    save_excel_df(df)

    # 回复微信消息
    reply_text = "✅ 消息已收到" if msg.type == "text" else f"✅ 已收到 {msg.type} 消息"
    reply = create_reply(reply_text, msg)
    return responses.PlainTextResponse(reply.render(), media_type="application/xml")

# ---------------- 健康检查接口 ----------------
@app.get("/health")
async def health_check():
    return {"status": "healthy", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ---------------- 启动 ----------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 80))  # 微信云托管默认使用 PORT
    uvicorn.run(app, host="0.0.0.0", port=port)