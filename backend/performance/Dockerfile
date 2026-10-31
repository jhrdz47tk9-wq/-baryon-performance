FROM python:3.12-slim
WORKDIR /app
COPY requirements-pilot.txt .
RUN pip install --no-cache-dir -r requirements-pilot.txt
COPY pilot_web.py persist.py run.py engine.py economics.py hazop.py example.json ./
USER 65532:65532
ENV PORT=8080
CMD ["sh","-c","exec gunicorn --workers 1 --threads 4 --bind 0.0.0.0:${PORT} 'pilot_web:configured_app()'"]
