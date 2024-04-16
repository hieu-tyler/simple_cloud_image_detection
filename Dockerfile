FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN apt-get update
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000

CMD ["python", "object_detection.py"]