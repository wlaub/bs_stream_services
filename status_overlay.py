import time, datetime
import math
import json
import textwrap
import traceback
import obspython as obs

import ipc

class Handler():
    divider = '-'*37 + '\n'
    maxwidth = 37

    def __init__(self):
        base = time.localtime()
        ts = (*base[:3], 21,0,0,0,0,base[-1])
        self.nine = time.mktime(ts)
        
        self.make_intro_script()
        self.infolines =''
        
        #-30s: warning
        #-2s: error
        #10s: garage door starts
        #22.5s garage door ends
        err_start = 3600-60
        
        self.events = [
            [3300, '[INFO] Source occlusion projected in 300 seconds'],
#            [err_start-5, '[INFO] Uncorrectably packet errors in video stream'],
#            [err_start-2, '[INFO] Video stream corrupted PER = 1.0'],
#            [err_start+26, '[INFO] Video stream recovered'],
            ]
        self.events = sorted(self.events, key = lambda x: x[0])
        
        self.outfile_base = time.strftime('%Y%d%m_%H%M%S')
        self.outfile = f'{self.outfile_base}.txt'
        
        print('Handler instantiated')

    def add_div(self):
        self.infolines += self.divider
    
    def add_line(self, line):
        self.infolines += '\n'.join(textwrap.wrap(line, width=self.maxwidth, subsequent_indent='  ')) + '\n'

    def make_intro_script(self):
        lines = [
        ['Carrier Detected', 5000],
        ['Carrier Lock', 200],
        ['Detecting Modulation...', 420],
        ['    Excessive Redshift Detected', 200],
        ['    Training Redshift Compensation...', 3000],
        ['    Complete', 200],
        ['Complete', 200],
        ['Training Content Decoder...', 5000],
        ['    Content Type: video, audio', 200],
        ['Identifying content...', 3000],

        ['    Sapient Subject Detected', 200],
        ['    Training Personality Model...', 200],
        ['        Gathering Training Set... ({300} s)', 300000],
        ['        Gathering Training Set... ', 100],
        ['        Complete', 200],
        ['        Training...', 5000],
        ['    Definite Article Model Failed to Converge', 100],
        ['    Complete, Estimated Fitness 0.7852', 200],
#        ['No subject detected. Checking other features...', 200],
        
        ['    Non-causal entrypoint detected. Connecting...', 1000],
        ['       Notice: limited-bandwidth', 500],
        ['    Complete', 200],
        ['Complete', 200],
        ['Displaying Transmission in {5} s', 5000],
        ['Displaying Transmission', 100],
        ]
        
        #-23.9
        duration = sum([x[1] for x in lines])
        data = []
        offset = -duration
        accum = ''
        for line, dur in lines:
            if '{' in line:
                before, after = line.split('{')
                number, after = after.split('}')
                number = int(number)
                for idx in range(number+1)[::-1]:
                    tline = before + str(idx) + after
                    data.append([offset/1000, accum+tline])
                    offset+=1000
                #accum += tline+'\n'
            else:
                accum += line+'\n'
                data.append([offset/1000, accum])
                offset += dur
            
        print(f'Intro duration: {duration/1000:.2f} s')
        self.intro_duration = duration
        self.intro = data

    def get_intro(self, offset):
        if offset > 0:
            return self.intro[-1][1]
            
        for off, value in self.intro[::-1]:
            if offset >= off:
                return value
        return 'No Carrier'

    def get_offset(self):
        return time.time()-self.nine

    def handle_events(self, offset):
        cutidx = 0
        for idx, event in enumerate(self.events):
            if offset < event[0]:
                break
            else:
                self.add_line(event[1])
                cutidx = idx + 1
        if cutidx > 0:
            self.events = self.events[cutidx:]

    def get_text(self):
        stamp = self.get_offset()
        if stamp >= 3600 or stamp < -self.intro_duration:
            return 'No Carrier'
        self.handle_events(stamp)
        
        result = self.get_intro(stamp)
        if stamp > 0:
            #result += self.divider
            result += self.infolines
        return result
        
handler = Handler()

ipc_server = ipc.Server(7852)

def script_unload():
    print('Unloading')
    ipc_server.close()
    obs.timer_remove(do_tick)

def script_load(settings):

    source = obs.obs_get_source_by_name('Beat Saber Recursion')
    filters = obs.obs_source_backup_filters(source)
    filter = obs.obs_data_array_item(filters, 0)
    
    settings = obs.obs_data_get_obj(filter, 'settings')
    
    try:
        pass
        print(obs.obs_data_get_json(settings))
        #obs.obs_data_set_int(settings, 'delay_ms', 10)
        #obs.obs_data_set_double(settings, 'offset_x', 0*192+4*math.sin(time.time()))
    except Exception as e:
        #print(e)
        pass
        
    obs.obs_data_release(settings)
    
    obs.obs_data_release(filter)
    obs.obs_data_array_release(filters)
    obs.obs_source_release(source)

    obs.timer_add(do_tick, 50)

def script_description():
    return 'A script.'

def set_color(settings, r,g,b,a):
    try:
        obs.obs_data_set_int(settings, 'color', (int(a)<<24)+(int(b)<<16)+(int(g)<<8)+int(r))
    except Exception as e:
        print(e)
    

def do_tick():
    offset = handler.get_offset()
    messages = ipc_server.recv()
    for msg in messages:
        try:
            kind = msg.get('kind', None)
            if kind == 'new_map': 
                #TODO: determine when the map started relative to the start of the stream
                #And write out timestamps to a file
                
                #TODO: receive map bpm and update the recursion filter delay length accordioningly
                handler.add_div()
                for line in msg['data']:
                    handler.add_line(line)
            elif kind == 'log':
                if offset >= 0 and offset < 3600:
                    handler.add_line(f"[{msg['level'].upper()}] {msg['data']}")
        except Exception as e:
            print(f'Excepton in ipc: {e}')

    source = obs.obs_get_source_by_name('Status Text')
    settings = obs.obs_source_get_settings(source)
    try:
        obs.obs_data_set_string(settings, 'text', handler.get_text())
    except Exception as e:
        print(e)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)



    source = obs.obs_get_source_by_name('RecursionFilter')
    settings = obs.obs_source_get_settings(source)
    r = 0
    b = 0
    g = 0
    a = 140
    if offset < 3300:
        a = 150 + 40*math.sin(offset*2*math.pi/60)
        r = 0
#        r = (1+math.sin(offset*6.28/3))*120
#        g = (1+math.sin((offset+1)*6.28/3))*120
#        b = (1+math.sin((offset+2)*6.28/3))*120
    else:
        x = (offset-3300)/300
        a = 150 + 95*x
        r = 20*x
    set_color(settings, r,g,b,a)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)

    
    if False: #filter doesn't update on param change this way.
        source = obs.obs_get_source_by_name('Beat Saber Recursion')
        filters = obs.obs_source_backup_filters(source)
        filter = obs.obs_data_array_item(filters, 0)
        
        settings = obs.obs_data_get_obj(filter, 'settings')
        
        try:
            pass
            #print(obs.obs_data_get_double(settings, 'offset_x'))
            #TODO: Figure out how to get this to actually update for real right now
            obs.obs_data_set_int(settings, 'delay_ms', 420)
        except Exception as e:
            #print(e)
            pass
            
        obs.obs_data_release(settings)
        
        obs.obs_data_release(filter)
        obs.obs_data_array_release(filters)
        obs.obs_source_release(source)
        
        