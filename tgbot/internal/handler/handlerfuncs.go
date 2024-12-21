package handler

import (
	"context"

	"tgbot/internal/proto"

	"github.com/pkg/errors"
)

var (
	errEmptyQuestion = errors.New("Question is empty")
	errEmptyAnswer   = errors.New("Answer is empty")
)

func (h *Handler) processQuestion(text string, questionType proto.QuestionType) (string, error) {
	if text == "" {
		return "", errEmptyQuestion
	}

	req := &proto.Request{Question: text, QuestionType: questionType}
	h.logger.Infof("Sending question to gRPC server '%#v'", req)
	resp, err := h.grpcClient.ProcessQuestion(context.Background(), req)
	if err != nil {
		return "", errors.Errorf("gRPC server returned error: %s", err.Error())
	}
	if resp.GetAnswer() == "" {
		return "", errEmptyAnswer
	}

	return resp.GetAnswer(), nil
}
