from gtts import gTTS
import pyttsx3
import os

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
        'rate': 125,
        'volume': 1,
        'voice': 'anna', #This will be replaced with the actual ID during __init__
        }

    config_options = {
        }

    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')

        def_voice = self.default_configs['voice']
        try:
            voice_id = self.get_voice(def_voice)
        except KeyError as e:
            voice_id = self.engine.getProperty('voice')
            print(f'{e} - defaulting to {voice_id}')

        self.default_configs['voice'] = voice_id
        print([x.name for x in self.voices])
        print(self.engine.getProperty('voice'))

    def get_voices(self):
        return [x.name for x in self.voices]

    def get_voice(self, name):
        """
        Find the voice best matching the given name and return its id
        """
        matches = list(filter(lambda x: name.lower() in x.name.lower(), self.voices))
        if len(matches) == 0:
            raise KeyError(f'No voice matching {name}')
            
        result = matches[0]
        if len(matches) > 1:
            print(f'Name ambiguous, selecting {result.name}')
        return result.id

    def set_configs(self, config):
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
        return AudioSegment.from_wav(self.temp_file_path)

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

    def __init__(self, data, config = {}):
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

        max_length = self.config.pop('max_length', None)
        clip = self.tts_engine.render(self.data['text'], self.config)
        if max_length != None:
            clip = clip[:int(max_length*1000)]
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

########################
# Twitch Chat Messages #
########################

#TODO: Classes for managing twitch chat messages and their metadata

#############
# User Info #
#############

#TODO: User-specific configuration info
#e.g. voice customization, single-user muting
#subscriber-only features

######################
# Message Processors #
######################

#TODO: Converting chat messages into snippets
#E.g. converting emotes into EmoteSnippets
#Performing search and replace behaviors
#Appending/prepending additional text such as speaker name
#Handling truncations and censoring


