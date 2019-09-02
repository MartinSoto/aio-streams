FROM ubuntu:disco as base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get -y install --no-install-recommends apt-utils dialog 2>&1 && \
    apt-get -y install \
        libbz2-1.0 \
        liblz4-1 \
        librocksdb5.17 \
        libsnappy1v5 \
        libzip5 \
        python3


FROM base as builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y install \
        libbz2-dev \
        liblz4-dev \
        librocksdb-dev \
        libsnappy-dev \
        libzip-dev \
        python3-dev \
        python3-pip

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt && \
        rm /tmp/requirements.txt


FROM base

COPY --from=builder /usr/local/lib/python3.7/dist-packages /usr/local/lib/python3.7/dist-packages
