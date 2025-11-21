# 使用官方 Python 3.11 slim 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制代码和依赖文件
COPY . /app

# 升级 pip 并安装依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 容器暴露端口（微信云托管通常使用 8080）
EXPOSE 80

# 启动 FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]