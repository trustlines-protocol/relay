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
    && apt-get install -y apt-utils libssl-dev curl graphviz \
    python3 python3-distutils python3-dev python3-venv git build-essential libpq-dev libgraphviz-dev libsecp256k1-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/relay
RUN /opt/relay/bin/pip install pip==18.0.0 setuptools==40.0.0

COPY ./constraints.txt /relay/constraints.txt
COPY ./requirements.txt /relay/requirements.txt

WORKDIR /relay

# remove development dependencies from the end of the file
RUN sed -i -e '/development dependencies/q' requirements.txt

RUN /opt/relay/bin/pip install -c constraints.txt -r requirements.txt

COPY . /relay

RUN /opt/relay/bin/pip install -c constraints.txt .
RUN /opt/relay/bin/python -c 'import pkg_resources; print(pkg_resources.get_distribution("trustlines-relay").version)' >/opt/relay/VERSION

FROM ubuntu:18.04 as runner
ENV LANG C.UTF-8
RUN apt-get update \
    && apt-get install -y apt-utils libssl-dev curl graphviz \
                          python3 libpq5 libsecp256k1-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/relay/bin/tl-relay /usr/local/bin/


FROM runner
COPY --from=builder /opt/relay /opt/relay
WORKDIR /opt/relay
ENTRYPOINT ["tl-relay"]
