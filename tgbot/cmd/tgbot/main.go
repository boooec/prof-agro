package main

import (
	"log"
	"os"

	"tgbot/internal/handler"
	"tgbot/internal/proto"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	PythonServerURI = "pyapp:8080"
)

func main() {
	logger, cancelLogger := initLogger()
	defer cancelLogger()
	logger.Info("Logger initialized")

	conn, err := grpc.NewClient(PythonServerURI, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		logger.Fatal(err)
	}
	defer conn.Close()
	grpcClient := proto.NewQuestionProcessorClient(conn)

	bot, err := tgbotapi.NewBotAPI(os.Getenv("TGBOT_TOKEN"))
	if err != nil {
		logger.Fatal(err)
	}

	if _, err = bot.RemoveWebhook(); err != nil {
		logger.Fatal(err)
	}

	updates, err := bot.GetUpdatesChan(tgbotapi.NewUpdate(0))
	if err != nil {
		logger.Fatal(err)
	}
	logger.Infof(`Got UpdatesChannel from bot "%s"`, bot.Self.UserName)

	handler.NewBotHandler(logger, bot, grpcClient).HandleUpdates(updates)
}

func initLogger() (*zap.SugaredLogger, func()) {
	zapConfig := zap.NewDevelopmentConfig() // zap.NewProductionConfig()
	zapConfig.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	zapLogger, err := zapConfig.Build()
	if err != nil {
		log.Fatal(err)
	}
	logger := zapLogger.Sugar()
	cancel := func() {
		if err := logger.Sync(); err != nil {
			log.Fatal(err)
		}
	}
	return logger, cancel
}
