from gtts import gTTS
import pyttsx3
import os
import time

from pydub import AudioSegment
from pydub.playback import play
import pydub.effects as fx
import pydub.playback as playback

###############
# TTS Engines #
###############

class TTS():
    """
    TTS wrapper class for abstracting different TTS libraries
    """
    temp_file_path = 'temp.mp3'

    default_configs = { 
        }
    #User configuration options info
    config_options = {
        #name: {'description': 'text', permissions: [user types]}
        }

    def __init__(self):
        pass

    def get_instance_config(self, config):
        """
        Update default configs with permitted configs
        """
        instance_config = dict(self.default_configs)
        for key, val in config.items():
            if key in self.config_options.keys():
                instance_config[key] = config[key]
        return instance_config

    def get_config_options(self, config):
        lines = []
        lines.append('TTS Configuration Options:')
        instance_config = self.get_instance_config(config)
        for key, val in self.config_options.items():
            lines.append(f'{key}: {instance_config[key]} / {self.default_configs[key]}')
        return ' | '.join(lines)


    def render(self, text, config):
        """
        Return an AudioSegment of the given text rendered to speech subject to
        optional configurations in kwargs
        """
        raise NotImplemented()

class GTTS(TTS):
    default_configs = {
        'lang': 'en',
        }
    config_options = {
        'lang': {
            'description': 'The TTS language code',
            'permissions': [], #not yet implemented
            }
    }


    def render(self, text, config = {}):
        instance_config = self.get_instance_config(config)

        gTTS(text, **instance_config).save(self.temp_file_path)
        clip = AudioSegment.from_mp3(self.temp_file_path)
        return clip 

        

class PyTTSX3(TTS):
    default_configs = {
        'rate': 200,
        'volume': 1,
        'voice': None, #This will be replaced with the actual ID during __init__
        'voice_name': 'zira'
        }

    config_options = {
        'rate': {'description': 'TTS reading rate', 'permissions': ['mod', 'sub']},
        'voice_name': {'description': 'Name of the voice to read in', 'permissions': ['mod', 'sub']}
        }

    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')

        voice_id = self.get_voice(
            self.default_configs['voice_name'], 
            self.engine.getProperty('voice')
            )

        self.default_configs['voice'] = voice_id
        print([x.name for x in self.voices])
        print(self.engine.getProperty('voice'))

    def get_voices(self):
        return [x.name for x in self.voices]

    def get_voice(self, name, default=None):
        """
        Find the voice best matching the given name and return its id
        """
        matches = list(filter(lambda x: name.lower() in x.name.lower(), self.voices))
        if len(matches) == 0:
            if default == None:
                raise KeyError(f'No voice matching {name}')
            else:
                print(f'No voice matching {name}')
                return default
            
        result = matches[0]
        if len(matches) > 1:
            print(f'Name ambiguous, selecting {result.name}')
        return result.id

    def set_configs(self, config):
        if config['voice_name'] != self.default_configs['voice_name']:
            config['voice'] = self.get_voice(config['voice_name'], self.default_configs['voice'])
        for prop, val in config.items():
            try:
#                old = self.engine.getProperty(prop)
                self.engine.setProperty(prop, val)
            except Exception as e:
                print(f'Failed to set pyttsx engine property {prop} to {val}:\n{e}')

    def render(self, text, config = {}):
        instance_config = self.get_instance_config(config)   
        self.set_configs(instance_config)
        self.engine.save_to_file(text, self.temp_file_path)
        self.engine.runAndWait()
        time.sleep(0.05) #sometimes the file doesn't get updated before trying to read it?
        clip = AudioSegment.from_wav(self.temp_file_path)
        return clip

####################
# Message Snippets #
####################

class Snippet():
    """
    A class for representing the mapping of a message segment into audio. Also
    contains global configurations such as the tts engine to use for all tts
    rendering.
    """
    muted = False           #per-class mute setting. When mute is true, render should return None
    tts_engine = PyTTSX3()  #The default tts engine to use

    def __init__(self, data, config = {'voice_name':'zira'}):
        """
        Data is the message snippet content and relevant metadata
        Config is a dictionary with parameters to be used for rendering the 
        audio output.
        """
        self.data = data
        self.config = config

    def render(self):
        """
        Return an AudioSegment representing this snippet or None if there is no
        audio
        """
        return None

class SpeechSnippet(Snippet):
    muted = False
    
    def render(self):
        if self.muted: return None

        config = dict(self.config)

        max_length = config.pop('max_length', None)
        clip = self.tts_engine.render(self.data['text'], self.config)
        if max_length != None:
            clip = clip[:int(max_length*1000)]
        
            
        return clip

    def __repr__(self):
        return f'SpeechSnippet : {self.data["text"]}'

class AISpeechSnippet(SpeechSnippet):
    def render(self):
        if self.muted: return None

        config = dict(self.config)

        clips = []
        for voice in ['david', 'zira']:
            config['voice_name'] = voice
            clips.append(self.tts_engine.render(self.data['text'], config))
            
        clip = None
        for tclip in clips:
            if clip is None:
                clip = tclip
            else:
                longer = max(clip, tclip, key=lambda x: len(x))
                shorter = min(clip, tclip, key=lambda x: len(x))
                clip = longer.overlay(shorter)
        return clip

    def __repr__(self):
        return f'SpeechSnippet : {self.data["text"]}'
        
class EmoteSnippet(Snippet):
    muted = False
    emote_map = {
        'LUL':'kefka.mp3'
    }
    emote_dir = 'emote_sounds'

    def render(self, **kwargs):
        if self.muted: return None
        if self.data['emote_name'] in self.emote_map.keys():
            filename = self.emote_map[self.data['emote_name']]
            filename = os.path.join(self.emote_dir, filename)
            return AudioSegment.from_mp3(filename)
        else:
            return self.tts_engine.render(self.data['emote_name'])

    def __repr__(self):
        return f'EmoteSnippet : {self.data["emote_name"]}'

class Mp3Snippet(Snippet):
    muted = False

    def render(self):
        return AudioSegment.from_mp3(self.data['filename'])

class ModemSnippet(Snippet):
    """
    Converts text into a bitstream via ascii and then into a sound
    """
    muted = False

    def render(self, **kwargs):
        if self.muted: return None
        duration = kwargs.get('duration', 0.75)
        count = len(self.data['text'])
        fs = 44100
        sps =16
        base_dur = sps*8*count/fs
        repeats = max(1,int(duration/base_dur))
        bits = []
        for char in self.data['text']:
            for _ in range(repeats):
                bits.extend(list(bin(ord(char)))[2:])
        data = []
        for bit in bits:
            if bit == '0': value = 0x00
            else: value = 0x40
            data.extend([value]*sps)
        result = AudioSegment(data= bytes(data), sample_width=1, frame_rate = fs, channels  =1)
        return result



######################
# Message Processors #
######################

#TODO: Converting chat messages into snippets
#E.g. converting emotes into EmoteSnippets
#Performing search and replace behaviors
#Appending/prepending additional text such as speaker name
#Handling truncations and censoring


