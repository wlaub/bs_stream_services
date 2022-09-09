import time

import tts
import message

import ipc

server = ipc.Server(ipc.ports['tts'])


while True:
    tts_queue = []
    for msg in server.recv():
        try:
            kind = msg.get('kind', None)
            if kind == 'stt':
                tts_message = message.AIMessage(msg['data'])
                tts_queue.append(tts_message)
            elif kind == 'chat':
                tts_message = message.Message(**msg['data'])
                tts_queue.append(tts_message)
        except Exception as e:
            print(f'Unexpected exception processing {message}: {e}')
    
    if len(tts_queue) > 0:
        tts_message = tts_queue.pop(0)
        tts_message.play()
    time.sleep(0.2)

server.close()