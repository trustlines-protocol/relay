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

RUN apt-get update \
    && apt-get install -y apt-utils libssl-dev curl libsecp256k1-dev \
    python3 python3-distutils python3-dev python3-venv git build-essential libpq-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/relay

WORKDIR /relay
COPY ./dev-requirements.txt /relay/dev-requirements.txt
RUN /opt/relay/bin/pip install --disable-pip-version-check -c dev-requirements.txt pip wheel setuptools
COPY ./requirements.txt /relay/requirements.txt

RUN /opt/relay/bin/pip install --disable-pip-version-check -r requirements.txt

COPY . /relay

RUN /opt/relay/bin/pip install --disable-pip-version-check .

FROM ubuntu:18.04 as runner
ENV LANG C.UTF-8
RUN apt-get update \
    && apt-get install -y apt-utils libssl-dev curl \
                          python3 libpq5 libsecp256k1-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/relay/bin/tl-relay /usr/local/bin/


FROM runner
COPY --from=builder /opt/relay /opt/relay
WORKDIR /opt/relay
EXPOSE 5000
ENTRYPOINT ["tl-relay"]
