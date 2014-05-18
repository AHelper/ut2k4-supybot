###
# Copyright (c) 2014, Collin Eggert
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import socket

class UnrealTournament(callbacks.Plugin):
  """Add the help for "@plugin help UnrealTournament" here
  This should describe *how* to use this plugin."""
  def __init__(self, irc):
    self.__parent = super(UnrealTournament, self)
    self.__parent.__init__(irc)
    self.checkTime = 10
    self.addr = "204.11.33.157"
    self.channel = "#cemetech-ut"
    
  def Query(self, k, v=""):
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.sendto("\\{}\\{}".format(k, v), (self.addr, 7787))
    recv, addr = conn.recvfrom(1024)
    return dict((recv[1::2][i],recv[2::2][i]) for i in range(0,len(recv[1::2])))
  
  def start(self, irc, msg, args):
    def poll():
      result = self.Query("players")
      players = {}
      for k, v in result.items():
        k, p = k.split('_')
        if p not in players:
          players[p]={}
        players[p][k]=v
      playerNames = []
      irc.queueMsg(ircmsgs.privmsg("#evocatus", 'UT: {} players are now on the server ({})'.format(len(self.players), ",".join(playerNames))))
      for n, p in players.items():
        playerNames.append(p["player"])
      if len(self.players) == 0 and len(players) > 0:
        self.players = players
        #irc.queueMsg(ircmsgs.privmsg(self.channel, 'UT: {} players are now on the server ({})'.format(len(self.players), ",".join(playerNames))))
    try:
      schedule.addPeriodicEvent(poll, self.checkTime, 'utPoll', False)
    except AssertionError:
      irc.reply('Already polling UT server')
    else:
      irc.reply("Polling '{}' every {} seconds.".format(self.addr, self.checkTime))
  start = wrap(start)
  
  def stop(self, irc, msg, args):
    try:
      schedule.removePeriodicEvent('utPoll')
    except KeyError:
      irc.reply('UT poll was already stopped')
    else:
      irc.reply('Polling stopped.')
  stop = wrap(stop)
  
  def ut(self, irc, msg, args):
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.sendto("\\echo\\UT!", ("204.11.33.157", 7787))
    recv, addr = conn.recvfrom(1024)
    irc.reply("UDP ({}): {}".format(addr,recv))
  ut = wrap(ut)

Class = UnrealTournament


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
