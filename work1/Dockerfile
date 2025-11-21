# 基础镜像：微信云托管Python3.11官方镜像（内置依赖环境）
FROM wxcloudrun/python:3.9-slim

# 避免中文乱码
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# 设置工作目录（云托管默认工作目录为/app，不可修改）
WORKDIR /app

# 复制依赖文件并安装（优先安装依赖，利用Docker缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有应用代码到工作目录
COPY . .

# 暴露端口（云托管强制80端口，必须声明）
EXPOSE 80

# 启动命令（必须与代码中uvicorn端口一致，前台运行）
CMD ["uvicorn", "main.py:app", "--host", "0.0.0.0", "--port", "80"]