import time
import json
import traceback
import websocket

import ipc

class BaseMonitor():
    def __init__(self):
        self.wscallbacks = {
            'on_message': lambda x,y: self.on_message(x,y),
            'on_open': lambda x: self.on_open(x),
            'on_error': lambda x,y: self.on_error(x,y),
            'on_close': lambda x,y,z: self.on_close(x,y,z),
        }
        self.closed = False
        self.history = []
        self.ws = None
        self.running = True
        self.overlay = ipc.OverlayClient()
        self.last_error = None
        self.norepeat_errors = set([10061])
    
    def on_message(self, ws, message):
        try:
            message=json.loads(message)
            #print(message.keys(), flush=True)
            self.process_message(message)
        except Exception as e:
            print(f'Error processing message {str(message):420}:\n')
            traceback.print_exc()
            print('', flush=True)
            raise e

    def on_open(self, ws):
        self.closed=False
        self.history = []
        print('Socket opened', flush=True)
    
    def on_error(self, ws, error):
        if self.last_error != error.winerror or error.winerror not in self.norepeat_errors:
            print(f'Error: {error}', flush=True)   
        self.last_error = error.winerror
    
    def on_close(self, ws, status_code, msg):
        self.closed = True
        print(f'Connection closed {status_code} {msg}', flush=True)

    def get_ws_app(self, host = '127.0.0.1', port = 2947):
        """
        Creates the websocket app instance and wires up the relevant callbacks
        """
       
        ws = websocket.WebSocketApp(f"ws://{self.host}:{self.port}/{self.endpoint}",
            **self.wscallbacks,
            )

        return ws

    def close_now(self):
        self.running = False
        self.ws.close()
    
    def do_monitor(self):
        while self.running:
            self.ws = ws = self.get_ws_app()
            print('Connecting...', flush=True)
            ws.run_forever()
            time.sleep(1)

class Monitor(BaseMonitor):
    host = '127.0.0.1'
    port = 2947
    endpoint = 'socket'
    
    def format_log(self, message):
        name = message['name']
        subname = message['sub_name']
        author = message['artist']
        mapper = message['mapper']
        bsr = message['BSRKey']

        lines = []
        lines.append(f'{author} - {name}')
        if subname.strip() != '':
            lines.append(f'  {subname}')
            
        tline = f'Mapper: {mapper}'
        if bsr is not None and bsr != '':
            tline += f' BSR: {bsr}'
        lines.append(tline)
        return lines

    def process_message(self, message):
        if message['_type'] == 'event':
            event = message['_event']
            if event == 'mapInfo':
                info = message['mapInfoChanged']
                if len(self.history) == 0 or info['level_id'] != self.history[-1]['level_id']:                    
                    lines = self.format_log(info)
                    self.overlay.send_map(lines)
#                    self.overlay.send({'kind': 'new_map', 'data': lines})
                    self.history.append(info)    


mon = Monitor()

mon.do_monitor()
