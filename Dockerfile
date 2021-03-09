# This will build the currently checked out version
#
# we use an intermediate image to build this image. it will make the resulting
# image a bit smaller.
#
# you can build the image with:
#
#   docker build . -t relay

FROM ubuntu:18.04 as builder
# python needs LANG
ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y apt-utils libssl-dev curl libsecp256k1-dev pkg-config \
    python3.8 python3.8-distutils python3.8-dev python3-venv python3.8-venv git build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3.8 -m venv /opt/relay
RUN /opt/relay/bin/pip install -U pip wheel setuptools

WORKDIR /relay
COPY ./dev-requirements.txt /relay/dev-requirements.txt
COPY ./requirements.txt /relay/requirements.txt
RUN /opt/relay/bin/pip install --disable-pip-version-check -r requirements.txt

COPY . /relay

RUN /opt/relay/bin/pip install --disable-pip-version-check .

FROM ubuntu:18.04 as runner
ENV LANG C.UTF-8
RUN apt-get -y update
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get -y update && \
    apt-get install -y apt-utils libssl-dev curl libpq5 libsecp256k1-0 \
    python3.8 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/relay/bin/tl-relay /usr/local/bin/


FROM runner
COPY --from=builder /opt/relay /opt/relay
WORKDIR /opt/relay
EXPOSE 5000
ENTRYPOINT ["tl-relay"]
