FROM python:3.13-slim
WORKDIR /root

RUN useradd -m user
RUN chown -R user:user /root
USER user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hestia/ ./hestia/

EXPOSE 5555
CMD ["python", "-m", "hestia.main"]