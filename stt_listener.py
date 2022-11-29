import speech_recognition as sr
        
import ipc
import re

def filter_language(text):

    text = re.sub(r'\bthe\b', '[ERROR]', text)

    text = text.replace('  ', ' ')
    text = text.replace(' .', '.')
    
    return text

class STT():
    def __init__(self):
        
        self.overlay = ipc.OverlayClient()
        self.tts = ipc.TTSClient()

        for index, name in enumerate(sr.Microphone.list_microphone_names()[:4]):
             print(f'{index}: {name}')

        mic_index = int(input('Select mic '))

        self.r = r = sr.Recognizer()
        self.mic = mic = sr.Microphone(device_index = mic_index)

        with mic:
            r.adjust_for_ambient_noise(mic)

        print(f'{r.energy_threshold=}')
        r.energy_threshold += 50

        self.done = False
        
    def run(self):
        mic = self.mic
        r = self.r
        last_line = None
        while not self.done:
            try:
                print(f'Listening')
                with mic:
                    audio = r.listen(mic, phrase_time_limit=10, timeout = 2)

                try:
                    result = r.recognize_google(audio, show_all=True)
                except Exception as e:
                    print(f'Failed to parse: {e}')
                    continue

                if result == [] or result == {}:
                    print(f'Failed to parse: empty response')
                    continue

                entries = result['alternative']
                entries = filter(lambda x: 'confidence' in x.keys(), entries)
                entries = sorted(entries, key=lambda x: x['confidence'], reverse=True)
                
                if len(entries) == 0:
                    print('Failed to parse: no confidence')
                    continue
                    
                result = entries[0]['transcript']
                conf = entries[0]['confidence']
                    
                print(f'Heard {result}')

                if last_line == result:
                    print('Repeated sound')
                    continue
                
                result = filter_language(result)
                
                self.overlay.send_log(message = f'{conf*100:.0f} "{result}"', level= 'model')
                
                self.tts.send_stt(result)
                
                last_line = result
            except Exception as e:
                print(f'Unexpected exception in listener: {e}')
        print(f'STT closing')

if __name__ == '__main__':
    stt = STT()
    stt.run()