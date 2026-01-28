FROM python:3.13-slim
WORKDIR /hestia

RUN useradd -m user
RUN chown -R user:user /hestia
USER user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hestia/ ./




EXPOSE 7860
CMD ["python", "hestia.py"]