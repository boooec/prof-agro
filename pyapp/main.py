from concurrent import futures
import grpc
import proto.api_pb2_grpc as api_grpc
import proto.api_pb2 as api
import ml
import time
import datetime
import threading


def print_log(*args, **kwargs):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{current_time} -", *args, **kwargs, flush=True)


class ProcessingServicer(api_grpc.QuestionProcessorServicer):
    def ProcessQuestion(self, req: api.Request, _) -> api.Response:
        answer = ml.giga_invoke(req)
        print_log("Got answer from giga_invoke: '", answer, "'", sep='')
        return api.Response(answer=answer)


def serve() -> None:
    print_log("Starting server")
    server = grpc.server(futures.ThreadPoolExecutor())
    api_grpc.add_QuestionProcessorServicer_to_server(ProcessingServicer(), server)
    print_log("Adding insecure port")
    server.add_insecure_port('[::]:8080')
    print_log("Starting server")
    server.start()

    def token_updater():
        print_log("will firstly get token")
        ml.update_token()
        while True:
            time.sleep(25 * 60)
            print_log("will get token")
            ml.update_token()

    token_thread = threading.Thread(target=token_updater, daemon=True)
    token_thread.start()

    print_log("Server started")
    server.wait_for_termination()


print_log("main.py started, __name__ = ", __name__)
if __name__ == '__main__':
    serve()
