FROM python:3.5

RUN apt-get update && \
    apt-get install -y apt-utils graphviz

COPY ./requirements.txt /relay/requirements.txt

WORKDIR /relay

RUN pip install -r requirements.txt

ENV THREADING_BACKEND gevent
ENV PYTHONPATH /relay

COPY . /relay

WORKDIR /relay/relay

ENTRYPOINT ["python", "trustlines.py"]
