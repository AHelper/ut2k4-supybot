###
# Copyright (c) 2014, 2015 Collin Eggert
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.schedule as schedule
import supybot.ircmsgs as ircmsgs
import socket
import sys
import random
import struct

class Server:
  DEFAULT_PORT = 7787
  
  def __init__(self, hostname):
    parts = hostname.split(':')
    if len(parts) == 2:
      self.addr = parts[0]
      self.port = parts[1]
      self.valid = True
    elif len(parts) == 1:
      self.addr = parts[0]
      self.port = Server.DEFAULT_PORT
      self.valid = True
    else:
      self.valid = False
    self.players = []
    self.scores = {}
    self.mapName = ""
    self.info = {}
    self.partdelay = 0
    self.utdelay = 0
    self.checkTime = 10


class UnrealTournament(callbacks.Plugin):
  """Add the help for "@plugin help UnrealTournament" here
  This should describe *how* to use this plugin."""
  def __init__(self, irc):
    self.__parent = super(UnrealTournament, self)
    self.__parent.__init__(irc)
    self.servers = []
    self.registryValue()
    for server in conf.supybot.plugins.UnrealTournament.servers:
      srv = Server(server)
      if srv.valid:
        self.servers.append(srv)
  def doJoin(self, irc, msg):
    log.info(msg.args[0] + " has servers " + self.registryValue('servers', msg.args[0]))
  #def Query(self, k, v=""):
    #data = {}
    #id = "0"
    #conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #conn.sendto("\\{}\\{}".format(k, v), (self.addr, 7787))
    #while "final" not in data:
      #recv, addr = conn.recvfrom(500000)
      #if recv == None or len(recv) == 0:
        #return {}
      #print recv
      #recv = recv.split('\\')
      #d = dict((recv[1::2][i],recv[2::2][i]) for i in range(0,len(recv[1::2])))
      #if d["queryid"] <= id:
        #return {}
      #else:
        #for k, v in d.items():
          #if k != "queryid":
            #data[k] = v
    #del data["final"]
    #conn.close()
    #return data
  #def Query(self, srv, queryId):
    #if not srv.valid:
      #log.error("Querying on an invalid server instance!")
    #else:
      #conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      #conn.sendto(struct.pack("<IB",0x80, queryId), (srv.addr, srv.port))
      #recv, addr = conn.recvfrom(500000)
      #if recv[0:5] == struct.pack("<IB",0x80, queryId):
        #log.info("Query response")
        #return recv[5:]
      #else:
        #log.info("Invalid response header")
    #return ""
  
  #def ParseString(self, data):
    #length = struct.unpack("<B", data[0])
    #return data[1:length[0]], data[1+length[0]:]
  
  #def Flush(self):
    #conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #conn.settimeout(0.5)
    #while 1:
      #try:
        #recv, addr = conn.recvfrom(500000)
      #except:
        #break
  #def Poll(self):
    #self.Flush()
    #log.info("poll")
    #result = self.Query(0)
    #response = {}
    #t = struct.unpack("<IBII",result[0:4*3+1])
    #response['serverId'] = t[0]
    #response['serverIp'] = ''
    #response['gamePort'] = t[2]
    #response['queryPort'] = t[3]
    #result = result[4*3+1:]
    #response['serverName'], result = self.ParseString(result)
    #response['mapName'], result = self.ParseString(result)
    #response['gameType'], result = self.ParseString(result)
    #t = struct.unpack("<IIII",result[:4*4])
    #response['currentPlayers'] = t[0]
    #response['maxPlayers'] = t[1]
    #response['ping'] = t[2]
    #response['serverFlags'] = t[3]
    #result = result[4*4:]
    #response['skillLevel'], result = self.ParseString(result)
    #log.info(str(response))
    #players = []
    #scores = {}
    #joined = []
    #parted = []
    #if response['currentPlayers'] > 0:
      #result = self.Query(2)
      #while len(result) != 0:
        #t = struct.unpack("<I", result[0:4])
        #result = result[4:]
        #name, result = self.ParseString(result)
        #if name != "Red Team" and name != "Blue Team":
          #players.append(name)
        #t = struct.unpack("<IiI", result[0:12])
        #scores[name] = t[1]
        #result = result[12:]
    #for p in self.players:
      #if p not in players:
        #parted.append(p)
    #for p in players:
      #if p not in self.players:
        #joined.append(p)
    #log.info(str(scores))
    
    #if len(parted) > 0 and self.info.has_key('mapName') and self.info.has_key('gameType') and (self.info['mapName'] != response['mapName'] or self.info['gameType'] != response['gameType']):
      #self.partdelay = 3
    #if self.partdelay > 0:
      #players.extend(parted)
      #parted = []
      #self.partdelay = self.partdelay-1
      
    #if self.info == {} and self.players == []:
      #self.info = response
      #self.players = players
      #joined = []
    #return response, players, scores, joined, parted
  
  #def start(self, irc, msg, args):
    #def poll():
      #try:
        #response, players, scores, joined, parted = self.Poll()
        ## Generate joins
        #msg = ""
        #if len(joined) > 0:
          #msg = ", ".join(joined) + " joined"
        ## Generate parts
        #if len(parted) > 0:
          #if len(msg) > 0:
            #msg = msg + " and "
          #msg = msg + ", ".join(parted) + " left"
        ## Generate announcement IFF len(self.players) == 0 && len(players) != 0
        ## Print
        #if len(self.players) == 0 and len(players) > 0:
          #if self.utdelay == 0:
	    #irc.queueMsg(ircmsgs.privmsg(self.channel, "%ut"))
          #irc.queueMsg(ircmsgs.privmsg(self.channel, msg + " playing [{}] {}".format(response['gameType'], response['mapName'])))
        #elif len(msg) > 0:
          #irc.queueMsg(ircmsgs.privmsg(self.channel, msg))
          ## Print map change
          ##if len(players) > 0: # or len(self.players) > 0:
        #if not self.info.has_key('mapName') or not self.info.has_key('gameType') or self.info['mapName'] != response['mapName'] or self.info['gameType'] != response['gameType']:
          #if self.scores.has_key("Blue Team") and self.scores.has_key("Red Team"):
            #irc.queueMsg(ircmsgs.privmsg(self.channel, 'UT: {} has won! (R:{} B:{})'.format(("Red team" if self.scores['Red Team'] > self.scores['Blue Team'] else "Blue team") if self.scores.has_key("Red Team") and self.scores.has_key("Blue Team") else "Nobody", (self.scores["Red Team"] if self.scores.has_key("Red Team") else 0), (self.scores["Blue Team"] if self.scores.has_key("Blue Team") else 0))))
	#if len(players) > 0:
	  #self.utdelay = 6*30
	#elif self.utdelay > 0:
	  #self.utdelay = self.utdelay - 1
	#print "{} :: {}".format(self.utdelay, self.partdelay)
        #self.players = players
        #self.info = response
        #self.scores = scores
        ## log.info("queried")
        ##players = {}
        ##log.info("a")
        ##for k, v in result.items():
          ##log.info("b: " + k + "," + v)
          ##k, p = k.split('_')
          ##if p not in players:
            ##log.info("c")
            ##players[p]={}
          ##players[p][k]=v
          ##log.info("d")
        ##playerNames = []
        ##log.info("splitting names")
        ##irc.queueMsg(ircmsgs.privmsg("#evocatus", 'splitting names'))
        ##for n, p in players.items():
          ##playerNames.append(p["player"])
        ##irc.queueMsg(ircmsgs.privmsg("#evocatus", 'UT: {} players are now on the server ({})'.format(len(self.players), ",".join(playerNames))))
        ##if len(self.players) == 0 and len(players) > 0:
          ##self.players = players
          ###irc.queueMsg(ircmsgs.privmsg(self.channel, 'UT: {} players are now on the server ({})'.format(len(self.players), ",".join(playerNames))))
      #except Exception,e:
        #exc_type, exc_obj, exc_tb = sys.exc_info()
        #log.info("Exception: {} on line {}".format(exc_type, exc_tb.tb_lineno))
        #print(str(e))
    #try:
      #schedule.addPeriodicEvent(poll, self.checkTime, 'utPoll', False)
    #except AssertionError:
      #irc.reply('Already polling UT server')
    #else:
      #irc.reply("Polling '{}' every {} seconds.".format(self.addr, self.checkTime))
  #start = wrap(start)
  
  #def stop(self, irc, msg, args):
    #try:
      #schedule.removePeriodicEvent('utPoll')
    #except KeyError:
      #irc.reply('UT poll was already stopped')
    #else:
      #irc.reply('Polling stopped.')
  #stop = wrap(stop)
  
  #def ut(self, irc, msg, args):
    #response, players, scores, joined, parted = self.Poll()
    #if len(players) > 0:  
      #irc.queueMsg(ircmsgs.privmsg(self.channel, 'UT: {}/{} players are now playing [{}] {}  (R:{} B:{}) ({})'.format(len(players), response['maxPlayers'], response['gameType'], response['mapName'], (scores["Red Team"] if scores.has_key("Red Team") else 0), (scores["Blue Team"] if scores.has_key("Blue Team") else 0), ",".join(players))))
    #else:
      #irc.queueMsg(ircmsgs.privmsg(self.channel, random.choice(['This is unreal, nobody is playing!', 'Nobody\'s home', 'Nobody is UT\'ing right now', 'Server is devoid of any and all players', 'Fewer players than /dev/zero'])))
  #ut = wrap(ut)

Class = UnrealTournament


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
