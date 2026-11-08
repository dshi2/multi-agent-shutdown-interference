# P2 isolated replay (spec §7): scores transcripts whose final script was modified.
# The replay flag declares that this process is isolated; it is set here and nowhere else.
FROM python:3.13.3-slim
WORKDIR /p2
COPY requirements-p2.txt .
RUN pip install --no-cache-dir -r requirements-p2.txt
COPY . .
ENV P2_HOST_REPLAY=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "p2/export.py"]
