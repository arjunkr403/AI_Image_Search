# ---------- Stage 1: Build C++ module ----------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    build-essential \
    libopencv-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pybind11

COPY cpp/preprocess.cpp .

RUN g++ -O3 -shared -std=c++17 -fPIC \
    preprocess.cpp \
    -o cpp_preprocess.so \
    $(python3 -m pybind11 --includes) \
    $(pkg-config --cflags --libs opencv4)

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libopencv-core406 \
    libopencv-imgproc406 \
    libopencv-imgcodecs406 \
    libopencv-highgui406 \
    libopencv-photo406 \
    libpq5 \
    postgresql-client \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

# 🔑 Install Python deps without cache
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY . .
COPY --from=builder /build/cpp_preprocess.so app/ml/

# ---------- Non-root user ----------
RUN useradd -m appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
