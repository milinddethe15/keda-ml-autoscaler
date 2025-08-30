FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY externalscaler.proto .
COPY generate_proto.sh .
RUN chmod +x generate_proto.sh && ./generate_proto.sh

COPY scaler.py .

EXPOSE 6000

CMD ["python", "scaler.py"]
