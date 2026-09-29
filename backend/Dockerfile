FROM python:3.12-slim
RUN pip install --no-cache-dir "pyjwt[crypto]==2.10.1"
COPY app.py /app/app.py
CMD ["python", "-u", "/app/app.py"]
