'''
Based on https://github.com/twitchdev/chatbot-python-sample

Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/apache2.0/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
'''

import sys, os
import irc.bot
import requests

import time
import json
import re

import threading

import secrets

from gtts import gTTS

import tts
import message

import ipc

from pydub import AudioSegment
from pydub.playback import play
import pydub.effects as fx
import pydub.playback as playback

class TwitchBot(irc.bot.SingleServerIRCBot):
    tts_subs = {
        'url': '. It was at this point that the user sent a URL to TTS.',
        'long': ". I'm not reading this."
        }

    max_word_length = 30 #in characters
    max_message_duration = 30 # in seconds
    say_names = True

    def __init__(self, username, client_id, token, channel, user_configs):
        self.client_id = client_id
        self.token = token
        self.channel = '#' + channel

        # Get the channel id, we will need this for v5 API calls
        #url = 'https://api.twitch.tv/helix/users?login=' + channel
        #headers = {'Client-ID': client_id, 'Accept': 'application/vnd.twitchtv.v5+json', 'Authorization': f'Bearer {token}'}
        #r = requests.get(url, headers=headers).json()
        #print(r)
        #self.channel_id = r['users'][0]['_id']

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        botname = 'iambotatvideogamesdotcom'
        print('Connecting to ' + server + ' on port ' + str(port) + '...', flush=True)
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:'+token)], username, username)
        print('Connected', flush=True)
        self.user_configs_file = user_configs
        self.user_configs = json.load(open(self.user_configs_file, 'r'))
        self.configs_changed = False

        self.last_speaker = 0

        self.tts_server = ipc.Client(ipc.ports['tts'])

        self.history = []

    def save_configs(self):
        print('* Saved configs')
        json.dump(self.user_configs, open(self.user_configs_file, 'w'))
        self.configs_changed = False

    def get_user_config(self, tags, key, default = None):
        user_id = tags.get('user-id')
        user = self.user_configs.get(user_id, {key:default})
        return user.get(key, None)

    def set_user_config(self, tags, key, value):
         user_id = tags.get('user-id')   
         user = self.user_configs.get(user_id, {})       
         self.user_configs[user_id] = user
         user[key] = value
         self.configs_changed = True

    def check_mod(self, tags):
        """
        Return true if the user is a moderator
        """
        badges = tags['badges']
        if badges == None: return False
        for badge in badges:
            b = badge.split('/')[0]
            if b in ['broadcaster', 'admin', 'moderator']:
                return True

    def check_highlighted(self, tags):
        return tags.get('msg-id', None) == 'highlighted-message'

    def check_lang(self, lang):
        gTTS('t', lang=lang)

    def on_welcome(self, c, e):
        print('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

    def filter_text(self, msg, tags):
        speaker = tags.get('display-name')
        user = tags.get('user-id')
            #display-name: the username
            #subscriber: subscriber status
            #user-id

        msg = f'{msg}'

#        if user != self.last_speaker:
#            msg = f'{speaker}: {msg}'

        url_re = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        msg = re.sub(url_re, self.tts_subs['url'], msg)

        def replace_long(x):
            if len(x) > self.max_word_length:
                return self.tts_subs['long']
            return x

        subs = msg.split(' ')
        subs = map(replace_long, subs)
        msg = ' '.join(subs)

        snippets = self.split_emotes(msg, tags)

        if user != self.last_speaker and self.say_names:
            snippets.insert(0, tts.SpeechSnippet({'text': speaker}, {'max_length: 1'}))
#            snippets.insert(0, SpeechSnippet('ctext', {'text': speaker, 'max_length':1}))

        print(snippets)
        abort = False

        if 'http' in msg: abort = True

        

        if not abort:
            return snippets
        return []

    def on_privmsg(self, c, e):
        try:
            tags = {}
            for d in e.tags:
                tags[d['key']] = d['value']
      
            import pprint
            print('private message')
            print(e.arguments)
            pprint.pprint(tags)

        except Exception as exc:
            raise exc

    def speak_message(self, text, tags, play_kwargs = {}):
        
        hist = None
        if len(self.history) > 0:
            hist = self.history[-1]
        self.tts_server.send({
            'kind': 'chat',
            'data': {'msg': text, 'tags': tags, 'history': hist, 'play_kwargs':play_kwargs}
            })
        
        self.history.append({'msg': text, 'tags': tags})

    def on_pubmsg(self, c, e):
        try:
            # If a chat message starts with an exclamation point, try to run it as a command
            tags = {}
            for d in e.tags:
                tags[d['key']] = d['value']
      
            import pprint
            print(e.arguments)
            pprint.pprint(tags)

            if e.arguments[0][:1] == '!':
                cmd, *args= e.arguments[0][1:].split(' ')
                print('Received command: ' + cmd)
                self.do_command(e, tags, cmd, args)
            else:
                self.speak_message(e.arguments[0], tags)

            self.last_speaker = tags['user-id']
        except Exception as exc:
            print(f'Failed to process message {e}\n\n{exc}')
        print(flush=True)
        return

    def get_user_id(self, display_name):
        url = f'https://api.twitch.tv/kraken/users?login={display_name}'
        headers = {'Client-ID': self.client_id, 'Accept': 'application/vnd.twitchtv.v5+json'}
        r = requests.get(url, headers=headers).json()
        print(r)
        return r['id']


    def say_in_chat(self, text):
        c = self.connection
        c.privmsg(self.channel, text)

    def do_command(self, e, tags, cmd, args):
        c = self.connection

        if cmd == 'tts':
            subcmd = ''
            if len(args) > 0:
                subcmd = args[0]
                args = args[1:]
            is_mod = self.check_mod(tags)
            if subcmd == 'lang':
                if len(args) == 0:
                    c.privmsg(self.channel, f'Current language: {self.get_user_config(tags, "lang")}')
                else:
                    try:
                        newlang = args[0]
                        self.check_lang(newlang)
                        self.set_user_config(tags, 'lang', newlang)
                        c.privmsg(self.channel, f'Language set to {newlang}')
                    except ValueError as exc:
                        c.privmsg(self.channel, str(exc))
                    except IndexError as exc:
                        c.privmsg(self.channel, 'usage: lang [language]')
            elif subcmd == 'rev':
                text = ' '.join(args)
                self.speak_message(text, tags, {'reverse':True})
            elif subcmd == 'fade':
                text = ' '.join(args)
                self.speak_message(text, tags, {'fade':True})
            elif subcmd == 'config':
                helptext = tts.Snippet.tts_engine.get_config_options({})
                c.privmsg(self.channel, str(helptext))
            else:
                helptext = []
                helptext.append('TTS Commands:')
                helptext.append('* lang [language code]')
                helptext.append('* rev [text]')
                helptext.append('* fade [text]')
                c.privmsg(self.channel, ' '.join(helptext))
            


        # The command was not recognized
        else:
            pass
#            c.privmsg(self.channel, "Did not understand command: " + cmd)

        if self.configs_changed:
            self.save_configs()


def main():

    if len(sys.argv) < 2:
        print(f'Usage: python chatbot.py [channel]')
        exit(1)


    username = secrets.username
    client_id = secrets.client_id #Obtained by creating a twitch API app and getting its key. Does not include the 'oauth' part
    token = secrets.token #http://twitchapps.com/tmi/

    channel = sys.argv[1]

    bot = TwitchBot(username, client_id, token, channel, 'user_configs.json')
    
    try:
        bot.start()
    except (KeyboardInterrupt, Exception):
        pass
    

if __name__ == "__main__":
    main()
