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

import inspect

def lineno():
  """Returns the current line number in our program."""
  return str(inspect.currentframe().f_back.f_lineno)
  
IRCLE_COLORS = [
  {'color':[0xFF, 0xFF, 0xFF],'code':'\x030'},
  {'color':[0x00, 0x00, 0x00],'code':'\x031'},
  {'color':[0xFF, 0x00, 0x00],'code':'\x032'},
  {'color':[0xFF, 0x80, 0x00],'code':'\x033'},
  {'color':[0xFF, 0xFF, 0x00],'code':'\x034'},
  {'color':[0x80, 0xFF, 0x00],'code':'\x035'},
  {'color':[0x00, 0xFF, 0x00],'code':'\x036'},
  {'color':[0x00, 0xFF, 0x80],'code':'\x037'},
  {'color':[0x00, 0xFF, 0xFF],'code':'\x038'},
  {'color':[0x00, 0x80, 0xFF],'code':'\x039'},
  {'color':[0x00, 0x00, 0xFF],'code':'\x03:'},
  {'color':[0x80, 0x00, 0xFF],'code':'\x03;'},
  {'color':[0xFF, 0x00, 0xFF],'code':'\x03<'},
  {'color':[0xFF, 0x00, 0x80],'code':'\x03='},
  {'color':[0xC0, 0xC0, 0xC0],'code':'\x03>'},
  {'color':[0x40, 0x40, 0x40],'code':'\x03?'},
  {'color':[0x80, 0x00, 0x00],'code':'\x03@'},
  {'color':[0x80, 0x40, 0x00],'code':'\x03A'},
  {'color':[0x80, 0x80, 0x00],'code':'\x03B'},
  {'color':[0x40, 0x80, 0x00],'code':'\x03C'},
  {'color':[0x00, 0x80, 0x00],'code':'\x03D'},
  {'color':[0x00, 0x80, 0x40],'code':'\x03E'},
  {'color':[0x00, 0x80, 0x80],'code':'\x03F'},
  {'color':[0x00, 0x40, 0x80],'code':'\x03G'},
  {'color':[0x00, 0x00, 0x80],'code':'\x03H'},
  {'color':[0x40, 0x00, 0x80],'code':'\x03I'},
  {'color':[0x80, 0x00, 0x80],'code':'\x03J'},
  {'color':[0x80, 0x00, 0x40],'code':'\x03K'}]

class Server:
  DEFAULT_PORT = 7778
  ServerInfo1 = struct.Struct("<IBII")
  ServerInfo2 = struct.Struct("<IIII")
  ServerInfo3 = struct.Struct("<I")
  ServerInfo4 = struct.Struct("<IiI")
  
  def __init__(self, parent, irc, hostname):
    self.parent = parent
    self.irc = irc
    parts = hostname.split(':')
    if len(parts) == 2:
      self.addr = parts[0]
      self.port = int(parts[1])
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
    self.polling = False
    self.channels = []
  def __del__(self):
    self.stopPoll()
  def __str__(self):
    return self.addr + ":" + str(self.port)
  def colorDistance(self, rgb1, rgb2):
    # From https://stackoverflow.com/a/14097641
    rm = 0.5*(rgb1[0]+rgb2[0])
    d = sum((2+rm,4,3-rm)*(rgb1-rgb2)**2)**0.5
    return d
  def rgbToIRCColorCode(self, color, channel = None):
    if self.parent.registryValue('color', channel) == 0:
      return ''
    elif self.parent.registryValue('color', channel) == 1: # ircle
      rank = {}
      for c in IRCLE_COLORS:
        rank[self.colorDistance(color, c['color'])] = c
      closest = sorted(rank.items(), lambda x:x[1])
      return closest['code']
    else:
      return ''
  def getPlayerText(self, player, channel = None):
    ret = ''
    try:
      itr = iter(player)
      while True:
        c = itr.next()
        if c == '\x1b':
          # RGB value follows
          rgb = [itr.next(), itr.next(), itr.next()]
          ret += self.rgbToIRCColorCode(rgb, channel)
        else:
          ret += c
    except StopIteration:
      return ret
  def printJoins(self, joins, channel = None):
    if self.parent.registryValue('sayJoins', channel):
      if len(joins) > 0:
        return ", ".join([self.getPlayerText(x, channel) for x in joins]) + " joined"
    return ''
  def printParts(self, joins, channel = None):
    if self.parent.registryValue('sayParts', channel):
      if len(joins) > 0:
        return ", ".join([self.getPlayerText(x, channel) for x in joins]) + " left"
    return ''
  def poll(self):
    log.info("Polling for " + str(self) + " on channels " + str(self.channels))
    response, players, scores, joined, parted = self.Poll()
    log.info(str(response))
    for channel in self.channels:
      log.info("Checking for " + channel)
      if len(self.players) == 0 and len(players) > 0 and len(str(self.parent.registryValue('onFirstJoinSay', channel)).strip()) > 0:
        if self.utdelay == 0:
          self.irc.queueMsg(ircmsgs.privmsg(channel, self.parent.registryValue('onFirstJoinSay')))
      msgJoins = self.printJoins(joined, channel)
      msgParts = self.printParts(parted, channel)
      
      msg = msgJoins
      if len(msgParts) > 0:
        if len(msg) > 0:
          msg += ' and '
        msg += msgParts
      log.info("Send to " + channel + " with msg: " + msg)
      
      self.players = players
      if len(players) > 0:
        self.utdelay = 6*30
      elif self.utdelay > 0:
        self.utdelay = self.utdelay - 1
  def startPoll(self):
    self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    schedule.addPeriodicEvent(lambda: self.poll(), self.checkTime, 'utPoll:' + str(self), False)
    self.polling = True
  def stopPoll(self):
    log.info('stopping poll')
    schedule.removePeriodicEvent('utPoll:' + str(self))
    self.polling = False
    self.conn.close()
  def addChannel(self, channelName):
    if not self.polling:
      self.startPoll()
    self.channels.append(channelName)
  # Returns True if it is unused
  def delChannel(self, channelName):
    if channelName in self.channels:
      self.channels.remove(channelName)
    if len(self.channels) == 0:
      self.stopPoll()
  def Query(self, queryId):
    log.info("TEST")
    log.info(lineno())
    if not self.valid:
      log.error("Querying on an invalid server instance!")
    else:
      log.info(lineno())
      log.info(str((self.addr, self.port)))
      self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.conn.sendto(struct.pack("<IB",0x80, queryId), (self.addr, self.port))
      log.info(lineno())
      recv, addr = self.conn.recvfrom(500000)
      log.info(lineno())
      if recv[0:5] == struct.pack("<IB",0x80, queryId):
        log.info("Query response")
        return recv[5:]
      else:
        log.info("Invalid response header")
    return ""

  def ParseString(self, data):
    length = struct.unpack("<B", data[0])
    ret = data[1:length[0]]
    del data[:1+length[0]]
    return ret

  def Flush(self):
    t = self.conn.gettimeout()
    self.conn.settimeout(0.5)
    while 1:
      try:
        recv, addr = self.conn.recvfrom(500000)
      except:
        break
    self.conn.settimeout(t)
  def Poll(self):
    self.Flush()
    log.info("Poll")
    result = self.Query(0)
    response = {}
    log.info(lineno())
    response['serverId'], x, response['gamePort'], response['queryPort'] = self.ServerInfo1.unpack_from(result)
    response['serverIp'] = ''
    log.info(lineno())
    log.info(len(result))
    log.info(self.ServerInfo1.size)
    del result[:self.ServerInfo1.size]
    log.info(lineno())
    response['serverName'] = self.ParseString(result)
    response['mapName'] = self.ParseString(result)
    response['gameType'] = self.ParseString(result)
    log.info(lineno())
    response['currentPlayers'], response['maxPlayers'], response['ping'], response['serverFlags'] = self.ServerInfo2.unpack_from(result)
    del result[:self.ServerInfo2.size]
    log.info(lineno())
    response['skillLevel'] = self.ParseString(result)
    log.info(lineno())
    log.info(str(response))
    log.info(lineno())
    players = []
    scores = {}
    joined = []
    parted = []
    if response['currentPlayers'] > 0:
      result = self.Query(2)
      while len(result) != 0:
        t = self.ServerInfo3.unpack_from(result)
        del result[:self.ServerInfo3.size]
        
        name = self.ParseString(result)
        if name != "Red Team" and name != "Blue Team":
          players.append(name)
        
        (x, scores[name], x) = self.ServerInfo4.unpack_from(result)
        scores[name] = t[1]
        del result[:self.ServerInfo4.size]
    for p in self.players:
      if p not in players:
        parted.append(p)
    for p in players:
      if p not in self.players:
        joined.append(p)
    log.info(str(scores))
    
    if len(parted) > 0 and self.info.has_key('mapName') and self.info.has_key('gameType') and (self.info['mapName'] != response['mapName'] or self.info['gameType'] != response['gameType']):
      self.partdelay = 3
    if self.partdelay > 0:
      players.extend(parted)
      parted = []
      self.partdelay = self.partdelay-1
      
    if self.info == {} and self.players == []:
      self.info = response
      self.players = players
      joined = []
    return response, players, scores, joined, parted

class UnrealTournament(callbacks.Plugin):
  """Add the help for "@plugin help UnrealTournament" here
  This should describe *how* to use this plugin."""
  def __init__(self, irc):
    self.__parent = super(UnrealTournament, self)
    self.__parent.__init__(irc)
    self.servers = {}
    #for server in self.registryValue('servers'):
      #srv = Server(server)
      #if srv.valid:
        #self.servers.append(srv)
  def __del__(self):
      log.info("Dieing")
  def doJoin(self, irc, msg):
    channel = msg.args[0]
    log.info(channel + " has servers " + ', '.join(self.registryValue('servers', channel)))
    for server in self.registryValue('servers', channel):
      if not self.servers.has_key(server):
        self.servers[server] = Server(self, irc, server)
      srv = self.servers[server]
      srv.addChannel(channel)
  def doPart(self, irc, msg):
    channel = msg.args[0]
    # Shut down polling
    for server in self.registryValue('servers', channel):
      if self.servers.has_key(server):
        if self.servers[server].delChannel(channel):
          self.servers[server] = None
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
