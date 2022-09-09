import zmq
import json

ports = {
'overlay': 7852,
'tts': 7854,
}

class Server():
    def __init__(self, port):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(f'tcp://127.0.0.1:{port}')
        
    def recv(self):
        result = []
        while True:
            try:
                msg = self.socket.recv_multipart(flags= zmq.NOBLOCK)
                port, data = msg
                result.append(json.loads(data.decode()))
            except zmq.ZMQError as e:
                return result

    def close(self):
        self.socket.close()
            
class Client():
    def __init__(self, port):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.connect(f'tcp://127.0.0.1:{port}')
        
    def send(self, data):
        try:
            self.socket.send_json(data)
            return True
        except zmq.ZMQError as e:
            print(e)
            return False
        
    def close(self):
        self.socket.close()