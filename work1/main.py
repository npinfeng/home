import os
import logging
import json
from datetime import datetime
import pandas as pd
import xmltodict
from fastapi import FastAPI, Request, BackgroundTasks, Response

## \file main.py
## \brief 微信公众号消息收集服务主程序
## \author 作业提交者
## \date 2025-11-23

# ---------------- 日志 ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Excel 文件（容器临时目录）
EXCEL_FILE = os.path.join("/tmp", "messages.xlsx")

## \brief 初始化 Excel 文件，若不存在则创建
## \return None

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=["MsgId", "FromUserName", "CreateTime", "MsgType", "Content", "ReceiveTime"])
        df.to_excel(EXCEL_FILE, index=False)
        logger.info("Initialized new Excel file.")

init_excel()

## \brief 保存消息数据到 Excel 文件
## \param data 消息字典
## \return None

def save_to_excel(data: dict):
    try:
        msg_data = {
            "MsgId": data.get("MsgId", str(datetime.now().timestamp())),
            "FromUserName": data.get("FromUserName", "Unknown"),
            "CreateTime": data.get("CreateTime", ""),
            "MsgType": data.get("MsgType", "text"),
            "Content": data.get("Content") or f"[Event: {data.get('Event')}]" if "Event" in data else "[Non-Text Message]",
            "ReceiveTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        df = pd.read_excel(EXCEL_FILE)
        new_row = pd.DataFrame([msg_data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        logger.info(f"Message saved: {msg_data['Content']}")
    except Exception as e:
        logger.error(f"Error saving to Excel: {e}")

# ---------------- 根路径 ----------------
## \brief 服务根路径，返回运行状态
## \return 状态字典
@app.get("/")
async def root():
    return {"status": "running", "service": "WeChat Message Collector"}

# ---------------- 消息接收接口 ----------------
## \brief 微信消息接收接口，支持 JSON/XML 格式
## \param request 请求体
## \param background_tasks 后台任务
## \return 文本响应
@app.post("/wechat")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.body()
        logger.info(f"Received Raw Body 1: {type(body)}<->{body}")
        content = body.decode("utf-8")
        # logger.info(f"Received Raw Body: {content}")
        # print(f"Received Raw Body: {content}")
        msg_data = {}

        # 尝试解析 JSON
        if content.strip().startswith("{"):
            try:
                payload = json.loads(content)
                if "FromUserName" in payload:
                    msg_data = payload
                elif "data" in payload and isinstance(payload["data"], dict):
                    msg_data = payload["data"]
                elif "action" in payload:  # CloudEvent
                    msg_data = payload.get("data", {})
                else:
                    msg_data = payload
                logger.info("Parsed as JSON.")
            except Exception as e:
                logger.error(f"JSON parsing failed: {e}")

        # JSON 失败尝试 XML
        if not msg_data:
            try:
                xml_dict = xmltodict.parse(content)
                msg_data = xml_dict.get("xml", {})
                logger.info("Parsed as XML.")
            except Exception as e:
                logger.error(f"XML parsing failed: {e}")

        if not msg_data or "FromUserName" not in msg_data:
            logger.warning("Invalid message data.")
            return Response(content="success", media_type="text/plain")

        # 异步保存 Excel
        background_tasks.add_task(save_to_excel, msg_data)
        return Response(content="success", media_type="text/plain")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return Response(content="success", media_type="text/plain")

# ---------------- 下载 Excel ----------------
## \brief 下载收集到的微信消息 Excel 文件
## \return 文件响应或错误信息
@app.get("/download")
async def download_excel():
    if os.path.exists(EXCEL_FILE):
        from fastapi.responses import FileResponse
        return FileResponse(
            path=EXCEL_FILE,
            filename="wechat_messages.xlsx",
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    return {"error": "No file found"}

# ---------------- 启动 ----------------
## \brief 主程序入口，启动 FastAPI 服务
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))  # 微信云托管默认 PORT
    uvicorn.run(app, host="0.0.0.0", port=port)