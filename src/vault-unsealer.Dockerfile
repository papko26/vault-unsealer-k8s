FROM python:3.8-alpine as builder

WORKDIR /install
COPY vault-unsealer/requirements.txt .
RUN pip3 install --install-option="--prefix=/install" --ignore-installed -r requirements.txt && rm requirements.txt

FROM python:3.8-slim
COPY --from=builder /install /usr/local
WORKDIR /app 
COPY vault-unsealer/unsealer.py .
CMD ["python3", "unsealer.py"]
