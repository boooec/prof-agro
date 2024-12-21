FROM golang:1.22

WORKDIR /tgbot

COPY tgbot/. .

RUN go mod download
RUN go build -o main ./cmd/tgbot

CMD ["./main"]
