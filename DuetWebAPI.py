# Python Script containing a class to send commands to, and query specific information from,
#   Duet based printers running either Duet RepRap V2 or V3 firmware.
#
# Does NOT hold open the connection.  Use for low-volume requests.
# Does NOT, at this time, support Duet passwords.
#
# Not intended to be a gerneral purpose interface; instead, it contains methods
# to issue commands or return specific information. Feel free to extend with new
# methods for other information; please keep the abstraction for V2 V3 
#
# Copyright (C) 2020 Danal Estes all rights reserved.
# Copyright (C) 2021 Haytham Bennani
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires Python3

# create logger
import logging
logger = logging.getLogger('TAMV.DuetWebAPI')

class DuetWebAPI:
    import requests
    import json
    import sys
    import time
    import datetime

    pt = 0
    _base_url = ''
    _rrf2 = False

    def __init__(self,base_url):
        logger.debug('Starting DuetWebAPI..')
        self._base_url = base_url
        try:
            logger.info('Connecting to ' + base_url + '..')
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=(2,60))
            replyURL = (f'{self._base_url}'+'/rr_reply')
            reply = self.requests.get(replyURL,timeout=2)
            j = self.json.loads(r.text)
            _=j['coords']
            firmwareName = j['firmwareName']

            try:
                firmwareName = j['firmwareName']
                # fetch hardware board type from firmware name, character 24
                boardVersion = firmwareName[24]
                firmwareVersion = j['firmwareVersion']
                if firmwareVersion[0] == "2":
                    self._rrf2 = True
                else: 
                    self._rrf2 = False
                    self.pt = 2
                    return
            except Exception as e:
                self._rrf2 = True
                logger.warning('unknown board+RRF combo - defaulting to RRF2')
            self.pt = 2
            logger.info('Connected to '+ firmwareName + '- V'+firmwareVersion)
            return
        except:
            try:
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=(2,60))
                j = self.json.loads(r.text)
                _=j
                firmwareName = j['boards'][0]['firmwareName']
                firmwareVersion = j['boards'][0]['firmwareVersion']
                self.pt = 3
                logger.info('Connected to: '+ firmwareName + '- V'+firmwareVersion)
                return
            except:
                logger.error( self._base_url + " does not appear to be an RRF2 or RRF3 printer")
                return 
####
# The following methods are a more atomic, reading/writing basic data structures in the printer. 
####

    def printerType(self):
        return(self.pt)

    def baseURL(self):
        return(self._base_url)

    def getCoords(self):
        import time
        try:
            if (self.pt == 2):
                if not self._rrf2:
                    logger.debug('XX - Duet RRF 3 using rr_status endpoint')
                    #RRF 3 using rr_status API
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error parsing getStatus session: ' + r)
                    buffer_size = 0
                    while buffer_size < 150:
                        logger.debug('XX - Buffering..')
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                while self.getStatus() not in "idle":
                    logger.debug('XX - printer not idle _SLEEPING_')
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                logger.debug('XX - calling API endpoint')
                r = self.requests.get(URL,timeout=2)
                logger.debug('XX - endpoint reply received')
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                logger.debug('XX - calling endpoint again')
                reply = self.requests.get(replyURL,timeout=2)
                logger.debug('XX - coordinate response received')
                jc=j['coords']['xyz']
                an=j['axisNames']
                ret=self.json.loads('{}')
                for i in range(0,len(jc)):
                    ret[ an[i] ] = jc[i]
                logger.debug('XX - returning coordinates')
                return(ret)
            if (self.pt == 3):
                logger.debug('XX - Duet RRF 3 using machine/status endpoint')
                while self.getStatus() not in "idle":
                    logger.debug('XX - printer not idle _SLEEPING_')
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/machine/status')
                logger.debug('XX - requesting machine status')
                r = self.requests.get(URL,timeout=2)
                logger.debug('XX - machine reponse received')
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ja=j['move']['axes']
                ret=self.json.loads('{}')
                for i in range(0,len(ja)):
                    ret[ ja[i]['letter'] ] = ja[i]['userPosition']
                logger.debug('XX - returning from machine/status call')
                return(ret)
        except Exception as e1:
            logger.error('Exception occurred in getCoords: ' + e1 )
        
    def getCoordsAbs(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            jc=j['coords']['machine']
            an=j['axisNames']
            ret=self.json.loads('{}')
            for i in range(0,len(jc)):
                ret[ an[i] ] = jc[i]
            return(ret)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            ja=j['move']['axes']
            ret=self.json.loads('{}')
            for i in range(0,len(ja)):
                ret[ ja[i]['letter'] ] = ja[i]['machinePosition']
            return(ret)

    def getLayer(self):
        if (self.pt == 2):
           URL=(f'{self._base_url}'+'/rr_status?type=3')
           r = self.requests.get(URL,timeout=2)
           j = self.json.loads(r.text)
           s = j['currentLayer']
           return (s)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            s = j['job']['layer']
            if (s == None): s=0
            return(s)


    def getModelQuery(self, key):
        if (self.pt == 2):
            if not self._rrf2:
                #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=2)
                if not r.ok:
                    logger.warning('Error in isIdle: ' + str(r))
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=2)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    replyURL = (f'{self._base_url}'+'/rr_reply')
                    reply = self.requests.get(replyURL,timeout=2)
                    if buffer_size < 150:
                        logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                        time.sleep(0.6)
            argString = ''
            for x in range(len(key)):
                argString = argString + '.' + key[x]
            argString = argString[1:]
            URL=(f'{self._base_url}'+'/rr_model?key=' + argString)
            try: 
                j = ''
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
            except Exception as c1:
                logger.info('Query failed: ' + str(c1))
                return ('')
            if not self._rrf2:
                #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=2)
            return (j)
        if (self.pt == 3):
            try:
                while self.getStatus() not in "idle":
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                try:
                    for x in range(len(key)): 
                        j=j[key[x]]
                except Exception as c1:
                    try:
                        logger.warning( 'Failed adding ' +  key[x])
                    except: None
                    logger.warning( 'Error returned: '  + str(c1) )
                return(j)
            except Exception as c2:
                logger.warning( 'Error: ' + str(c2) )
                return('')
            return (j)


    def getG10ToolOffset(self,tool):
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            ja=j['move']['axes']
            jt=j['tools']
            ret=self.json.loads('{}')
            to = jt[tool]['offsets']
            for i in range(0,len(to)):
                ret[ ja[i]['letter'] ] = to[i]
            logger.debug('Tool offset for T' + str(tool) +': ' + str(ret))
            return(ret)
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            ja=j['axisNames']
            jt=j['tools']
            ret=self.json.loads('{}')
            to = jt[tool]['offsets']
            for i in range(0,len(to)):
                ret[ ja[i] ] = to[i]
            logger.debug('Tool offset for T' + str(tool) +': ' + str(ret))
            return(ret)
        logger.warning('getG10ToolOffset entered unhandled exception state.')
        return({'X':0,'Y':0,'Z':0})      # Dummy for now              

    def getNumExtruders(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            jc=j['coords']['extr']
            logger.debug('Number of extruders: ' + str(len(jc)))
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            logger.debug('Number of extruders: ' + str(len(j['move']['extruders'])))
            return(len(j['move']['extruders']))

    def getNumTools(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            jc=j['tools']
            logger.debug('Number of tools: ' + str(len(jc)))
            return(len(jc))
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            logger.debug('Number of tools: ' + str(len(j['tools'])))
            return(len(j['tools']))

    def getStatus(self):
        import time
        try:
            if (self.pt == 2):
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error in getStatus session: ' + str(r))
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                s=j['status']
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
                if not self._rrf2:
                    endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                    r2 = self.requests.get(endsessionURL,timeout=2)
                    if not r2.ok:
                        logger.error('getStatus ended session: ' + str(r2))
                if ('I' in s): return('idle')
                if ('P' in s): return('processing')
                if ('S' in s): return('paused')
                if ('B' in s): return('canceling')
                return(s)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: 
                    j = j['result']
                _status = str(j['state']['status'])
                return( _status.lower() )
        except Exception as e1:
            logger.error('Unhandled exception in getStatus: ' + str(e1))
            return 'Error'

    def gCode(self,command):
        if (self.pt == 2):
            if not self._rrf2:
                #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                import time
                sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                r = self.requests.get(sessionURL,timeout=2)
                buffer_size = 0
                while buffer_size < 150:
                    bufferURL = (f'{self._base_url}'+'/rr_gcode')
                    buffer_request = self.requests.get(bufferURL,timeout=2)
                    try:
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                    except:
                        buffer_size = 149
                    if buffer_size < 150:
                        logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                        time.sleep(0.6)
            URL=(f'{self._base_url}'+'/rr_gcode?gcode='+command)
            r = self.requests.get(URL,timeout=2)
            replyURL = (f'{self._base_url}'+'/rr_reply')
            reply = self.requests.get(replyURL,timeout=2)
            if not self._rrf2:
                #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=2)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/code/')
            r = self.requests.post(URL, data=command)
        if (r.ok):
           return(0)
        else:
            logger.warning("Error running gCode command: return code " + str(r.status_code) + ' - ' + str(r.reason))
            return(r.status_code)
    
    def gCodeBatch(self,commands):
        for command in commands:
            if (self.pt == 2):
                if not self._rrf2:
                #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    import time
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        buffer_response = buffer_request.json()
                        buffer_size = int(buffer_response['buff'])
                        time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_gcode?gcode='+command)
                r = self.requests.get(URL,timeout=2)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
                json_response = r.json()
                buffer_size = int(json_response['buff'])
                #print( "Buffer: ", buffer_size )
                #print( command, ' -> ', reply )
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/code/')
                r = self.requests.post(URL, data=command)
            if not (r.ok):
                logger.warning("Error in gCodeBatch command: " + str(r.status_code) + str(r.reason) )
                endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                r2 = self.requests.get(endsessionURL,timeout=2)
                return(r.status_code)
        if not self._rrf2:
            #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
            endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
            r2 = self.requests.get(endsessionURL,timeout=2)

    def getFilenamed(self,filename):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_download?name='+filename)
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/file/'+filename)
        r = self.requests.get(URL,timeout=2)
        return(r.text.splitlines()) # replace('\n',str(chr(0x0a))).replace('\t','    '))

    def getTemperatures(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            logger.error('getTemperatures no yet implemented for RRF V2 printers.')
            return('Error Dx05: getTemperatures not implemented (yet) for RRF V2 printers.')
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/status')
            r  = self.requests.get(URL,timeout=2)
            j  = self.json.loads(r.text)
            if 'result' in j: j = j['result']
            jsa=j['sensors']['analog']
            return(jsa)
        
    def checkDuet2RRF3(self):
        if (self.pt == 2):
            URL=(f'{self._base_url}'+'/rr_status?type=2')
            r = self.requests.get(URL,timeout=2)
            j = self.json.loads(r.text)
            s=j['firmwareVersion']
            if s == "3.2":
                return True
            else:
                return False

    def getCurrentTool(self):
        import time
        logger.debug('Starting getCurrentTool')
        try:
            if (self.pt == 2):
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error in getCurrentTool: '  + str(r))
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                while self.getStatus() not in "idle":
                    logger.debug('Machine not idle, sleeping 0.5 seconds.')
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
                ret=j['currentTool']
                logger.debug('Found current tool - exiting.')
                return(ret)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ret=j['state']['currentTool']
                logger.debug('Found current tool - exiting.')
                return(ret)
        except Exception as e1:
            logger.error('Unhandled exception in getCurrentTool: ' + str(e1))

    def getHeaters(self):
        import time
        try:
            if (self.pt == 2):
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error in getHeaters session: ' + str(r))
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                while self.getStatus() not in "idle":
                    time.sleep(0.5)
                URL=(f'{self._base_url}'+'/rr_status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
                ret=j['heaters']
                return(ret)
            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: j = j['result']
                ret=j['heat']['heaters']
                return(ret)
        except Exception as e1:
            logger.error('Unhandled exception in getHeaters: ' + str(e1))

    def isIdle(self):
        try:
            if (self.pt == 2):
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error in isIdle: ' + str(r))
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                URL=(f'{self._base_url}'+'/rr_status?type=2')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                s=j['status']
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                    r2 = self.requests.get(endsessionURL,timeout=2)
                    if not r2.ok:
                        logger.error('Unhandled exception in isIdle: ' + str(r2))
                        return False
                if ('I' in s):
                    return True
                else: 
                    return False

            if (self.pt == 3):
                URL=(f'{self._base_url}'+'/machine/status')
                r = self.requests.get(URL,timeout=2)
                j = self.json.loads(r.text)
                if 'result' in j: 
                    j = j['result']
                status = str(j['state']['status'])
                if status.upper() == 'IDLE':
                    return True
                else:
                    return False
        except Exception as e1:
            logger.error('Unhandled exception in isIdle: ' + str(e1))
            return False
####
# The following methods provide services built on the atomics above. 
####


    # Given a line from config g that defines an endstop (N574) or Z probe (M558),
    # Return a line that will define the same thing to a "nil" pin, i.e. undefine it
    def _nilEndstop(self,configLine):
        ret = ''
        for each in [word for word in configLine.split()]: ret = ret + (each if (not (('P' in each[0]) or ('p' in each[0]))) else 'P"nil"') + ' '
        return(ret)

    def clearEndstops(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                   )]:
            commandBuffer.append(self._nilEndstop(each))
        self.gCodeBatch(commandBuffer)
    

    def resetEndstops(self):
        import time
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line)                    )]:
            commandBuffer.append(self._nilEndstop(each))
        for each in [line for line in c if (('M574 ' in line) or ('M558 ' in line) or ('G31 ' in line))]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetAxisLimits(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if 'M208 ' in line]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetG10(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if 'G10 ' in line]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def resetAdvancedMovement(self):
        c = self.getFilenamed('/sys/config.g')
        commandBuffer = []
        for each in [line for line in c if (('M566 ' in line) or ('M201 ' in line) or ('M204 ' in line) or ('M203 ' in line))]:
            commandBuffer.append(each)
        self.gCodeBatch(commandBuffer)

    def getTriggerHeight(self):
        _errCode = 0
        _errMsg = ''
        triggerHeight = 0
        #if (command.lower[:1]) in ['k']:
        logger.info('here')
        if (self.pt == 2):
            if not self._rrf2:
                try:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    sessionURL = (f'{self._base_url}'+'/rr_connect?password=reprap')
                    r = self.requests.get(sessionURL,timeout=2)
                    if not r.ok:
                        logger.warning('Error in isIdle: ' + str(r))
                    buffer_size = 0
                    while buffer_size < 150:
                        bufferURL = (f'{self._base_url}'+'/rr_gcode')
                        buffer_request = self.requests.get(bufferURL,timeout=2)
                        try:
                            buffer_response = buffer_request.json()
                            buffer_size = int(buffer_response['buff'])
                        except:
                            buffer_size = 149
                        replyURL = (f'{self._base_url}'+'/rr_reply')
                        reply = self.requests.get(replyURL,timeout=2)
                        logger.info(reply)
                        if buffer_size < 150:
                            logger.debug('Buffer low - adding 0.6s delay before next call: ' + str(buffer_size))
                            time.sleep(0.6)
                except Exception as c1:
                    logger.info('huh')
                    logger.warning( 'Tool coordinates cannot be determined:' + str(c1) )
                    return (0, 'none', '0' )
                URL=(f'{self._base_url}'+'/rr_gcode?gcode=G31')
                r = self.requests.get(URL,timeout=2)
                replyURL = (f'{self._base_url}'+'/rr_reply')
                reply = self.requests.get(replyURL,timeout=2)
               # Reply is of the format:
                # "Z probe 0: current reading 0, threshold 500, trigger height 0.000, offsets X0.0 Y0.0 U0.0"
            try:
                #start = reply.find('trigger height')
                triggerHeight = reply
                #triggerHeight = reply[start+15:]
                #triggerHeight = float(triggerHeight[:triggerHeight.find(',')])
                if not self._rrf2:
                    #RRF 3 on a Duet Ethernet/Wifi board, apply buffer checking
                    endsessionURL = (f'{self._base_url}'+'/rr_disconnect')
                    r2 = self.requests.get(endsessionURL,timeout=2)
            except Exception as c1:
                logger.info(triggerHeight)
                logger.warning( 'Tool coordinates cannot be determined:' + str(c1) )
        if (self.pt == 3):
            URL=(f'{self._base_url}'+'/machine/code/')
            r = self.requests.post(URL, data='G31')
            # Reply is of the format:
            # "Z probe 0: current reading 0, threshold 500, trigger height 0.000, offsets X0.0 Y0.0"
            reply = r.text
            start = reply.find('trigger height')
            triggerHeight = reply[start+15:]
            triggerHeight = float(triggerHeight[:triggerHeight.find(',')])
        if (r.ok):
           return (_errCode, _errMsg, triggerHeight )
        else:
            _errCode = float(r.status_code)
            _errMsg = r.reason
            logger.error("Bad resposne in getTriggerHeight: " + str(r.status_code) + ' - ' + str(r.reason))
            return (_errCode, _errMsg, None )
    