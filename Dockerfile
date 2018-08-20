FROM python:3.5 as builder

RUN apt-get update \
    && apt-get install -y apt-utils libssl-dev curl graphviz \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/relay
RUN /opt/relay/bin/pip install pip==18.0.0 setuptools==40.0.0

COPY ./constraints.txt /relay/constraints.txt
COPY ./requirements.txt /relay/requirements.txt

WORKDIR /relay

# remove development dependencies from the end of the file
RUN sed -i -e '/development dependencies/q' requirements.txt

RUN /opt/relay/bin/pip install -c constraints.txt -r requirements.txt

ENV THREADING_BACKEND gevent

COPY . /relay

RUN /opt/relay/bin/pip install -c constraints.txt .
RUN /opt/relay/bin/python -c 'import pkg_resources; print(pkg_resources.get_distribution("trustlines-relay").version)' >/opt/relay/VERSION

FROM python:3.5
COPY --from=builder /opt/relay /opt/relay

RUN apt-get update \
    && apt-get install -y apt-utils libssl-dev curl graphviz \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/relay/bin/tl-relay /usr/local/bin/

ENV THREADING_BACKEND gevent
WORKDIR /opt/relay
ENTRYPOINT ["tl-relay"]
