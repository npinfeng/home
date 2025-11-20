from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from openpyxl import Workbook, load_workbook
import os
import traceback

app = FastAPI()

EXCEL_FILE = "papers.xlsx"


# 初始化 Excel（自动创建）
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.append(["标题", "作者", "章节"])
        wb.save(EXCEL_FILE)

init_excel()


@app.get("/", response_class=HTMLResponse)
def read_form():
    # 表单页面
    return """
    <html>
        <body>
            <h2>论文信息提交</h2>
            <form method="post" action="/submit">
                标题：<input type="text" name="title"><br><br>
                作者：<input type="text" name="author"><br><br>
                章节：<input type="text" name="chapter"><br><br>
                <button type="submit">提交</button>
            </form>
        </body>
    </html>
    """


@app.post("/submit")
def submit_form(
    title: str = Form(...),
    author: str = Form(...),
    chapter: str = Form(...)
):
    try:
        # 写入 Excel
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        ws.append([title, author, chapter])
        wb.save(EXCEL_FILE)

        # 使用 JSONResponse，防止 FastAPI 内部终止
        return JSONResponse({
            "status": "success",
            "msg": "提交成功",
            "data": {
                "title": title,
                "author": author,
                "chapter": chapter
            }
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "msg": "发生异常",
            "detail": str(e),
            "trace": traceback.format_exc()
        })
# 运行命令：

#uvicorn work1.main2:app --reload --host 0.0.0.0 --port 8000