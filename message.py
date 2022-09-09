import re

import requests
import tts
import filters

from pydub import AudioSegment
from pydub.playback import play
import pydub.effects as fx
import pydub.playback as playback

########################
# Twitch Chat Messages #
########################

#TODO: Classes for managing twitch chat messages and their metadata

class CustomFilter():
    filemap = {
        'BibleThump': 'emote_sounds/kefka.mp3'
    }
    def process(self, snippet):
        if not isinstance(snippet, tts.EmoteSnippet): return False

        filename = self.filemap.get(snippet.data['emote_name'], None)
        if filename == None: return False

        return [tts.Mp3Snippet({'filename': filename})]

class AIMessage():
    def __init__(self, text):
        self.snippet = tts.AISpeechSnippet({'text':text})
        
    def play(self, **kwargs):
        clip = self.snippet.render()
        play(clip)

class Message():
    """
    A message
    """

    extract_emotes = True        #Turn emotes into EmoteSnippets
    announce_new_speakers = True #Announce the speaker when the speaker changes

    max_message_duration = 30 # in seconds

    filters = [
        filters.ModemReplace( # replaces urls
            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            tts.SpeechSnippet({'text': 'URL Removed'})),
        filters.TooLongTruncate(30),
        CustomFilter(),
    ]

    def __init__(self, msg, tags, history, play_kwargs = {}):
        """
        msg and tags come from the chatbot
        history the previous {msg: msg, tags:tags}
        """
        self.msg = msg
        self.tags = tags
        self.play_kwargs = play_kwargs

        self.user = User(msg, tags)
        self.past_user = None
        if history is not None:
            self.past_user = User(**history)

        self.emote_data = self.parse_emotes()
        #TODO: Extract emote data

        #TODO: Extract flags data

        self.snippets = self.preprocess()
        self.snippets = self.process(self.snippets)
        self.snippets = self.postprocess(self.snippets)

    def play(self, reverse=False, fade=False):
        """
        Play the message
        """
        reverse = self.play_kwargs.pop('reverse', reverse)
        fade = self.play_kwargs.pop('fade', fade)
        
        clip = AudioSegment.empty()
        for snippet in self.snippets:
            tclip = snippet.render()
            if tclip != None:
                clip += tclip
        if clip.duration_seconds > self.max_message_duration:
            return False

        if reverse:
            clip = clip.reverse()
        if fade:
            clip = clip.fade_out(int(clip.duration_seconds*1000))

#        if self.check_highlighted(tags):
#            clip = fx.speedup(clip)
#            clip = fx.low_pass_filter(clip, 500)

        play(clip)
        return True



    def parse_emotes(self):
        emotes = self.tags['emotes']
        if emotes == None: return []
        result = []
        kinds = emotes.split('/')
        for kind in kinds:
            kind, ranges = kind.split(':')
            king = int(kind)
            ranges = ranges.split(',')
            for left, right in map(lambda x: x.split('-'), ranges):
                result.append({'kind': kind, 'left': int(left), 'right': int(right)})
        result = sorted(result, key=lambda x: x['left'])
        return result

    def preprocess(self):
        """
        Generate the starting set of snippets. It is here that emotes get split out
        """
        emotes = self.tags['emotes']
        text = self.msg

        #handle emotes
        if emotes == None or not self.extract_emotes: 
            result = [tts.SpeechSnippet({'text': text.strip()})]
        else:
            result = []
            emotes = self.parse_emotes()
            diff = 0
            for emote in emotes:
                textl = text[:emote['left']-diff]
                textr = text[emote['right']+1-diff:]

                emote['text'] = text[emote['left']-diff:emote['right']-diff+1]
                diff += len(text)-len(textr)
                text = textr
                result.append(tts.SpeechSnippet({'text': textl.strip()}))
                result.append(tts.EmoteSnippet({'emote_name': emote['text']}))
            if len(textr.strip()) > 0:
                result.append(tts.SpeechSnippet({'text': textr.strip()}))

        return result

    def process(self, result):
        """
        Keep applying filters until there's nothing left to apply.
        """
        max_depth = 10
        depth = 0
        done = False
        while not done and depth < max_depth:
            done = True
            depth += 1
            for idx, snippet in enumerate(result):
                for filt in self.filters:
                    tsnips = filt.process(snippet)
                    if tsnips != False:
                        result[idx:idx+1] = tsnips
                        done = False
                        break
        return result
            

    def postprocess(self, result):
        """
        Executed after all filters are done
        """
        if self.announce_new_speakers:
            if self.past_user is None or self.past_user.id != self.user.id:
                result.insert(0, tts.SpeechSnippet({'text': self.user.display_name}, {'max_length': 1}))
       
        return result


#############
# User Info #
#############

#TODO: User-specific configuration info
#e.g. voice customization, single-user muting
#subscriber-only features

class User():
    """
    A user as identified by twitch message tag info
    """

    #Maps lists of badge names to user broader classes.
    #For example anyone with a broadcaster, admin, or moderator badge is a mod
    user_classes = {
    'mod': ['broadcaster', 'admin', 'moderator'],
    'sub': ['subscriber'],
    }

    def __init__(self, msg, tags):
        self.msg = msg
        self.tags = tags

        self.id = tags.get('user-id') 
        self.display_name = tags.get('display-name')
    
        self.badges = []
        if tags['badges'] != None:
            for b in tags.get('badges', []):
                self.badges.append(b.split('/'))

        self.configs = {}
    
    def get_class(self, classname):
        """
        Return True if a user is in the desired class
        """
        classes = self.user_classes[classname]
        for b in self.badges:
            if b[0] in classes: return True
        return False


    def is_mod(self):
        """
        The user is a moderator, admin, or the broadcaster
        """
        for b in self.badges:
             if b[0] in ['broadcaster', 'admin', 'moderator']:
                return True
        return False
           
    def is_sub(self):
        """
        The user is a subscriber
        """
        for b in self.badges:
             if b[0] in ['subscriber']:
                return True
        return False
       

    

