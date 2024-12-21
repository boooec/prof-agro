all:
	sudo -E docker compose up -d --build

stop:
	sudo docker container stop prof-agro-tgbot-1
	sudo docker container stop prof-agro-pyapp-1

gen:
	protoc -I=./proto --go_out=. --go-grpc_out=. ./proto/api.proto
	python -m grpc_tools.protoc -I=. --python_out=./pyapp --pyi_out=./pyapp --grpc_python_out=./pyapp proto/api.proto

ls:
	sudo docker container ls -a

docker_start:
	sudo systemctl start docker

logs:
	sudo docker container logs prof-agro-tgbot-1 -f

logs-py:
	sudo docker container logs prof-agro-pyapp-1 -f

golint:
	cd tgbot && golangci-lint run -c ./.golangci.yml
