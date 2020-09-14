FROM python:3.7-slim
MAINTAINER zerthmonk

ENV PYTHONUBUFFERED=1
ENV PATH="/venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python-gi python-gi-cairo python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0 \
    build-essential libcairo2 libcairo2-dev libgirepository1.0-dev zlib1g-dev zlib1g bzip2

COPY requirements.txt /requirements.txt

ENV VENV="/venv"
RUN python -m venv $VENV
ENV PATH="$VENV/bin:$PATH"

RUN python -m pip install --upgrade pip && \
    python -m pip install -r /requirements.txt

RUN mkdir /app
WORKDIR /app
COPY app.py .
COPY static/ . 

RUN ["sh", "-c", "python app.py"]

