FROM python:3.13-slim

RUN useradd -m user

COPY requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /var/lib/itrust
WORKDIR /var/lib/itrust/

COPY hestia/ ./hestia/

RUN mkdir -p ./app/data/corpus_dir

RUN chown -R user:user /var/lib/itrust

USER user

RUN ls -la
EXPOSE 5555
CMD ["python", "-m", "hestia.main"]