package handler

import (
	"fmt"
	"sync"

	"tgbot/internal/proto"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	"go.uber.org/zap"
)

const (
	changeModeToQuestions = "Перейти в режим вопросов"
	changeModeToCheckList = "Перейти в режим чек-листов"
)

var numericKeyboard = tgbotapi.NewReplyKeyboard(
	tgbotapi.NewKeyboardButtonRow(
		tgbotapi.NewKeyboardButton(changeModeToQuestions),
		tgbotapi.NewKeyboardButton(changeModeToCheckList),
	),
)

type Handler struct {
	logger     *zap.SugaredLogger
	bot        *tgbotapi.BotAPI
	grpcClient proto.QuestionProcessorClient

	userModes   map[int64]proto.QuestionType
	userModesMu sync.RWMutex
}

func (h *Handler) HandleUpdates(updates tgbotapi.UpdatesChannel) {
	for update := range updates {
		h.handleUpdate(&update)
	}
}

func (h *Handler) setMode(chatID int64, mode proto.QuestionType) {
	h.userModesMu.Lock()
	defer h.userModesMu.Unlock()
	h.userModes[chatID] = mode
}

func (h *Handler) mode(chatID int64) proto.QuestionType {
	h.userModesMu.RLock()
	defer h.userModesMu.RUnlock()
	mode, ok := h.userModes[chatID]
	if !ok {
		mode = proto.QuestionType_QUESTION_TYPE_QUESTION
	}
	return mode
}

func (h *Handler) handleUpdate(update *tgbotapi.Update) {
	msg := update.Message
	if msg == nil {
		return
	}

	go func() {
		h.logger.Infof("%#v", msg)
		text := msg.Text
		if text == "" {
			h.reply(msg, "Question cannot be empty")
			return
		}

		mode := proto.QuestionType_QUESTION_TYPE_UNSPECIFIED
		switch text {
		case changeModeToQuestions:
			mode = proto.QuestionType_QUESTION_TYPE_QUESTION
			h.reply(msg, "Выбран режим вопросов")
			h.setMode(msg.Chat.ID, mode)
			return
		case changeModeToCheckList:
			mode = proto.QuestionType_QUESTION_TYPE_CHECKLIST
			h.reply(msg, "Выбран режим чек-листов")
			h.setMode(msg.Chat.ID, mode)
			return
		default:
			mode = h.mode(msg.Chat.ID)
		}

		answer, err := h.processQuestion(text, mode)
		if err != nil {
			errMsg := fmt.Sprintf("Unable to process question: %s", err.Error())
			h.logger.Errorf(errMsg)
			h.reply(msg, errMsg)
			return
		}

		h.reply(msg, answer)
	}()
}

func (h *Handler) reply(msg *tgbotapi.Message, text string) {
	reply := tgbotapi.NewMessage(msg.Chat.ID, text)
	reply.ReplyMarkup = numericKeyboard
	reply.ReplyToMessageID = msg.MessageID
	if _, err := h.bot.Send(reply); err != nil {
		h.logger.Errorf("Unable to send tg message: %s", err.Error())
	}
}

func NewBotHandler(lgr *zap.SugaredLogger, bot *tgbotapi.BotAPI, client proto.QuestionProcessorClient) *Handler {
	return &Handler{
		logger:      lgr,
		bot:         bot,
		grpcClient:  client,
		userModes:   make(map[int64]proto.QuestionType),
		userModesMu: sync.RWMutex{},
	}
}
