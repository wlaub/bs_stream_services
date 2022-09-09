import typing
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
        
    def recv(self) -> typing.Dict:
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
        
    def send(self, data: typing.Dict):
        try:
            self.socket.send_json(data)
            return True
        except zmq.ZMQError as e:
            print(e)
            return False
        
    def close(self):
        self.socket.close()
        
class OverlayClient(Client):
    def __init__(self):
        super().__init__(ports['overlay'])

    def send_map(self, lines: typing.List):
        self.send({'kind': 'new_map', 'data': lines})

    def send_log(self, message: str, level: str = 'info'):
        self.send({'kind': 'log', 'level': level, 'data': message})

class TTSClient(Client):
    def __init__(self):
        super().__init__(ports['tts'])
        
    def send_chat(self, text, tags, hist, play_kwargs):
        self.send({
            'kind': 'chat',
            'data': {'msg': text, 'tags': tags, 'history': hist, 'play_kwargs':play_kwargs}
            })
            
    def send_stt(self, text):
        self.send({'kind': 'stt', 'data': text})