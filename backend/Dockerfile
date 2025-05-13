FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app/

# 全面配置APT镜像源
RUN echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    && echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.ustc.edu.cn/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && apt-get update && apt-get install -y supervisor gcc

# 配置Python包管理器镜像
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

COPY supervisord.conf /usr/etc/supervisord.conf

# Install dependencies.
COPY uv.lock /app/uv.lock
COPY pyproject.toml /app/pyproject.toml

RUN PYTHONDONTWRITEBYTECODE=1 uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

# 使用国内镜像下载Playwright
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# Pre-download playwright dependencies.
RUN playwright install --with-deps chromium

# Pre-download nltk data with mirrors
ENV NLTK_DATA="/usr/local/lib/python3.11/site-packages/llama_index/core/_static/nltk_cache"
RUN mkdir -p $NLTK_DATA \
    && python -c 'import nltk; \
    download_dir = "/usr/local/lib/python3.11/site-packages/llama_index/core/_static/nltk_cache";\
    nltk.download("stopwords", download_dir=download_dir);\
    nltk.download("punkt", download_dir=download_dir);'

ENV PYTHONPATH=/app

COPY . /app/

# Default number of workers
ENV WEB_CONCURRENCY=4

CMD ["sh", "-c", "fastapi run app/api_server.py --host 0.0.0.0 --port 80 --workers ${WEB_CONCURRENCY}"]