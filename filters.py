import re

import requests
import tts

from pydub import AudioSegment
from pydub.playback import play
import pydub.effects as fx
import pydub.playback as playback

###################
# Message Filters #
###################

class RegexReplace():
    def __init__(self, re, replacement):
        self.re = re
        self.replacement = replacement
    
    def process(self, snippet):
        if not isinstance(snippet, tts.SpeechSnippet): return False

        pieces = re.split(self.re, snippet.data['text'])
        if len(pieces) == 1: return False

        result = []
        for idx, piece in enumerate(pieces):
            result.append(tts.SpeechSnippet({'text': piece}, snippet.config))
            if idx < len(pieces) - 1:
                result.append(self.replacement)

        return result

class TooLongTruncate():
    def __init__(self, max_length):
        self.max_length = max_length

    def process(self, snippet):
        if not isinstance(snippet, tts.SpeechSnippet): return False

        otext = snippet.data['text']
        pieces = otext.split(' ')
        pieces = list(map(lambda x: x[:self.max_length], pieces))
        text = ' '.join(pieces)
        if text == otext: return False
        result = [tts.SpeechSnippet({'text': text}, snippet.config)]

        return result



