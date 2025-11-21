from fastapi import FastAPI, Request, responses
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
import pandas as pd
from datetime import datetime
import os
from wxcloudrun-sdk import init, cos  # 云托管SDK
import traceback

# 初始化微信云托管SDK（必须在所有操作前执行）
init()

# 从云托管环境变量读取配置（敏感信息不硬编码）
TOKEN = os.getenv("TOKEN")
APPID = os.getenv("APPID")
APPSECRET = os.getenv("APPSECRET")
COS_BUCKET = os.getenv("COS_BUCKET")  # 云存储桶名称（环境变量配置）
EXCEL_FILENAME = "wechat_messages.xlsx"
LOCAL_TEMP_PATH = f"/tmp/{EXCEL_FILENAME}"  # 云托管临时目录（容器内唯一可写目录）

# 验证配置是否齐全
assert TOKEN, "环境变量TOKEN未配置"
assert APPID, "环境变量APPID未配置"
assert APPSECRET, "环境变量APPSECRET未配置"
assert COS_BUCKET, "环境变量COS_BUCKET未配置"

app = FastAPI()

# -------------------------- 工具函数（适配云存储） --------------------------
def get_excel_df() -> pd.DataFrame:
    """获取Excel数据（优先从云存储加载，无则返回空DataFrame）"""
    try:
        # 1. 尝试从云存储下载文件到本地临时目录
        cos.download_file(
            Bucket=COS_BUCKET,
            Key=EXCEL_FILENAME,
            DestFilePath=LOCAL_TEMP_PATH
        )
        # 2. 读取Excel文件
        return pd.read_excel(LOCAL_TEMP_PATH, engine="openpyxl")
    except Exception as e:
        # 异常场景：文件不存在（首次运行）、下载失败等
        print(f"加载Excel失败（首次运行正常）：{traceback.format_exc()}")
        # 返回空DataFrame（带表头）
        return pd.DataFrame(columns=["接收时间", "用户OpenID", "消息类型", "消息内容", "消息ID"])

def save_excel_df(df: pd.DataFrame):
    """保存DataFrame到云存储（先存本地临时文件，再上传）"""
    try:
        # 1. 去重（避免微信重试导致的重复数据）
        df = df.drop_duplicates(subset=["消息ID"], keep="last")
        # 2. 保存到本地临时文件
        df.to_excel(LOCAL_TEMP_PATH, index=False, engine="openpyxl")
        # 3. 上传到微信云存储（覆盖原有文件）
        cos.upload_file(
            Bucket=COS_BUCKET,
            Key=EXCEL_FILENAME,
            LocalFilePath=LOCAL_TEMP_PATH
        )
        print(f"Excel已保存到云存储，当前共{len(df)}条消息")
    except Exception as e:
        print(f"保存Excel失败：{traceback.format_exc()}")
        raise  # 抛出异常，避免消息丢失（云托管会重试）

# -------------------------- 公众号接口 --------------------------
@app.get("/wechat")
async def wechat_verify(
    signature: str,
    timestamp: str,
    nonce: str,
    echostr: str
):
    """微信服务器验证接口（GET请求，仅首次配置需要）"""
    try:
        # 验证签名（Token必须与公众号配置一致）
        check_signature(TOKEN, signature, timestamp, nonce)
        return responses.PlainTextResponse(echostr)  # 验证成功，返回echostr
    except InvalidSignatureException:
        print("签名验证失败：可能是TOKEN不一致或参数错误")
        return responses.PlainTextResponse("Invalid signature", status_code=403)

@app.post("/wechat")
async def receive_message(
    request: Request,
    signature: str,
    timestamp: str,
    nonce: str
):
    """接收公众号消息接口（POST请求）"""
    # 1. 验证签名
    try:
        check_signature(TOKEN, signature, timestamp, nonce)
    except InvalidSignatureException:
        print("签名验证失败：POST请求签名错误")
        return responses.PlainTextResponse("Invalid signature", status_code=403)

    # 2. 解析微信消息（XML格式）
    try:
        xml_data = await request.body()
        msg = parse_message(xml_data)
        print(f"收到消息：类型={msg.type}，用户={msg.source}，内容={getattr(msg, 'content', '无')}")
    except Exception as e:
        print(f"解析消息失败：{traceback.format_exc()}")
        return responses.PlainTextResponse("Parse message failed", status_code=500)

    # 3. 处理文本消息（核心逻辑）
    if msg.type == "text":
        # 构造消息数据（包含消息ID用于去重）
        message_data = {
            "接收时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],  # 精确到毫秒
            "用户OpenID": msg.source,  # 用户唯一标识
            "消息类型": msg.type,
            "消息内容": msg.content.strip(),
            "消息ID": msg.id  # 微信消息唯一ID，用于去重
        }

        # 4. 加载现有数据并追加新消息
        df = get_excel_df()
        new_row = pd.DataFrame([message_data])
        df = pd.concat([df, new_row], ignore_index=True)

        # 5. 保存到云存储
        save_excel_df(df)

        # 6. 回复用户（微信要求5秒内返回，必须是XML格式）
        reply = create_reply("✅ 消息已收到，感谢你的反馈！", msg)
        return responses.PlainTextResponse(reply.render(), media_type="application/xml")

    # 4. 处理其他消息类型（图片、事件等）
    elif msg.type in ["image", "voice", "video", "shortvideo", "location", "link"]:
        message_data = {
            "接收时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "用户OpenID": msg.source,
            "消息类型": msg.type,
            "消息内容": getattr(msg, "media_id", "无") if msg.type in ["image", "voice", "video", "shortvideo"] else getattr(msg, "title", "无"),
            "消息ID": msg.id
        }
        df = get_excel_df()
        new_row = pd.DataFrame([message_data])
        df = pd.concat([df, new_row], ignore_index=True)
        save_excel_df(df)
        reply = create_reply(f"✅ 已收到{msg.type}类型消息！", msg)
        return responses.PlainTextResponse(reply.render(), media_type="application/xml")

    # 5. 未处理的消息类型（如事件消息）
    else:
        print(f"未处理的消息类型：{msg.type}")
        return responses.PlainTextResponse("success")  # 必须返回200，否则微信会重试

# -------------------------- 健康检查接口（云托管必需） --------------------------
@app.get("/health")
async def health_check():
    """云托管健康检查接口（每30秒调用一次，必须返回200）"""
    return {"status": "healthy", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# -------------------------- 启动入口（云托管自动调用） --------------------------
if __name__ == "__main__":
    # 本地测试用（云托管部署时会被Dockerfile的CMD覆盖）
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)