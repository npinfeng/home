FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制代码和依赖文件
COPY main.py requirements.txt /app/

# 安装依赖  
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 暴露端口（云托管使用 PORT 环境变量）
EXPOSE 8080

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]