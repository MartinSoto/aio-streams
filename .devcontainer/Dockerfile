FROM martinsoto/devshell-python

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

RUN echo 'if [ -f ~/hosthome/.devshell/init.sh ]; then source ~/hosthome/.devshell/init.sh; fi' >> /root/.bashrc
