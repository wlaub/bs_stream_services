import ipc

overlay = ipc.OverlayClient()
tts = ipc.TTSClient()

while True:
    try:
        command = input('> ').strip()
        cmd, *data = command.split(' ')
        if cmd == 'log':
            if len(data) < 2:
                raise ValueError("log command requires level and message")
            level = data[0]
            msg = ' '.join(data[1:])
            overlay.send_log(msg, level)
        elif cmd == 'tts':
            msg = ' '.join(data)
            tts.send_chat(msg, {'user-id': -1, 'display-name': 'terminal client'}, None, {})
            #tts.send_stt(msg)
        elif cmd == 'stt':
            msg = ' '.join(data)
            tts.send_stt(msg)
        elif cmd == 'help':
            print("""
Commands:
  log <level> <message>
  tts <message>
  stt <message>
  exit/quit
""")
        elif cmd in {'exit', 'quit'}:
            break
        else:
            print(f'Unknown command: {cmd}')
    except Exception as e:
        print(f'Exception: {e}', flush = True)