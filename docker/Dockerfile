# LOTT Strategy Container Dockerfile
# 用于构建策略运行环境的镜像

FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY src/ ./src/
COPY config/ ./config/

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/.cache

# 非root用户运行
RUN useradd -m -u 1000 lott && \
    chown -R lott:lott /app
USER lott

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 默认入口
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]