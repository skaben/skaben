FROM rabbitmq:3.8.9-management-alpine

ENV RABBITMQ_VERSION=3.8.3

COPY ./rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
COPY ./definitions.json /etc/rabbitmq/definitions.json
RUN chown rabbitmq:rabbitmq /etc/rabbitmq/rabbitmq.conf /etc/rabbitmq/definitions.json

RUN rabbitmq-plugins enable --offline rabbitmq_management
RUN rabbitmq-plugins enable --offline rabbitmq_mqtt
RUN rabbitmq-plugins enable --offline rabbitmq_web_stomp
RUN rabbitmq-plugins enable --offline  rabbitmq_prometheus

RUN echo 'NODENAME=rabbit@localhost' > /etc/rabbitmq/rabbitmq-env.conf

EXPOSE 15672
EXPOSE 15674
EXPOSE 15675
EXPOSE 15692
EXPOSE 1883
EXPOSE 8883

