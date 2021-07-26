FROM prom/prometheus

USER root
COPY ./prometheus.yml /etc/prometheus/prometheus.yml
RUN chown 65534:65534 /etc/prometheus/prometheus.yml && \
    chmod 440 /etc/prometheus/prometheus.yml
USER 65534
