FROM apache/nifi:1.28.0
ARG UID
ARG GID
USER root

RUN apt-get update && \
	apt-get install -y python3.10 python3-pip

# Change UID
RUN usermod -u $UID nifi && groupmod -g $GID nifi \
 && chown -R nifi:nifi ${NIFI_BASE_DIR}

USER nifi

WORKDIR /opt/nifi/nifi-current

USER root

COPY ./requirements.txt /opt
RUN pip install --no-cache-dir -r /opt/requirements.txt



