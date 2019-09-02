FROM martinsoto/aio-streams as runtime


FROM martinsoto/devshell-python

RUN apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get -y install \
        kafkacat \
        libbz2-1.0 \
        liblz4-1 \
        librocksdb5.17 \
        libsnappy1v5 \
        libzip5
COPY --from=runtime /usr/local/lib/python3.7/dist-packages /usr/local/lib/python3.7/dist-packages/

COPY dev-requirements.txt /tmp/dev-requirements.txt
RUN pip3 install -r /tmp/dev-requirements.txt && \
        rm /tmp/dev-requirements.txt

RUN echo 'if [ -f ~/hosthome/.devshell/init.sh ]; then source ~/hosthome/.devshell/init.sh; fi' >> /root/.bashrc
