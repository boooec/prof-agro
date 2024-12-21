FROM python:3.11

WORKDIR /pyapp

COPY pyapp/. .

RUN apt-get update
# RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]
