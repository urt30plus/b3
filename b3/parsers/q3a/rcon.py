# -*- coding: utf-8 -*-

# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #
#

__author__ = 'ThorN'
__version__ = '1.11'

import queue
import re
import select
import socket
import threading
import time

import b3.functions


class Rcon(object):
    socket_timeout = 0.80
    rconsendstring = '\377\377\377\377rcon "{password}" {data}\n'
    rconreplystring = '\377\377\377\377print\n'
    rcon_encoding = "latin-1"

    def __init__(self, console, host, password):
        """
        :param console: The console implementation
        :param host: The host where to send RCON commands
        :param password: The RCON password
        """
        self.console = console
        self.host = host
        self.password = password
        self.queue = queue.Queue()
        self.socket = socket.socket(type=socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.connect(self.host)
        self.lock = threading.Lock()
        self._stopEvent = threading.Event()
        b3.functions.start_daemon_thread(self._writelines)
        self.console.bot('Game name is: %s', self.console.gameName)

    def send_rcon(self, data, maxRetries=None, socketTimeout=None):
        """
        Send an RCON command.
        :param data: The string to be sent
        :param maxRetries: How many times we have to retry the sending upon failure
        :param socketTimeout: The socket timeout value
        """
        if socketTimeout is None:
            socketTimeout = self.socket_timeout
        if maxRetries is None:
            maxRetries = 2

        data = data.strip()

        self.console.verbose('RCON sending (%s:%s) %r', self.host[0], self.host[1], data)
        start_time = time.time()

        retries = 0
        while time.time() - start_time < 5:
            readables, writeables, errors = select.select([], [self.socket], [self.socket], socketTimeout)

            if errors:
                self.console.warning('RCON: %s', str(errors))
            elif writeables:
                try:
                    payload = self.rconsendstring.format(password=self.password, data=data)
                    payload = payload.encode(encoding=self.rcon_encoding)
                    writeables[0].send(payload)
                except Exception as msg:
                    self.console.warning('RCON: error sending: %r', msg)
                else:
                    try:
                        data = self.read_socket(self.socket, socketTimeout=socketTimeout)
                        self.console.verbose2('RCON: received %r', data)
                        return data
                    except Exception as msg:
                        self.console.warning('RCON: error reading: %r', msg)

                if re.match(r'^quit|map(_rotate)?.*', data):
                    # do not retry quits and map changes since they prevent the server from responding
                    self.console.verbose2('RCON: no retry for %r', data)
                    return ''

            else:
                self.console.verbose('RCON: no writeable socket')

            time.sleep(0.05)

            retries += 1

            if retries >= maxRetries:
                self.console.error('RCON: too many tries: aborting (%r)', data.strip())
                break

            self.console.verbose('RCON: retry sending %r (%s/%s)...', data.strip(), retries, maxRetries)

        self.console.debug('RCON: did not send any data')
        return ''

    def _writelines(self):
        """
        Write multiple RCON commands on the socket.
        """
        while not self._stopEvent.isSet():
            lines = self.queue.get(True)
            for cmd in lines:
                if not cmd:
                    continue
                with self.lock:
                    self.send_rcon(cmd, maxRetries=1)

    def writelines(self, lines):
        """
        Enqueue multiple RCON commands for later processing.
        :param lines: A list of RCON commands.
        """
        self.queue.put(lines)

    def write(self, cmd, maxRetries=None, socketTimeout=None):
        """
        Write a RCON command.
        :param cmd: The string to be sent
        :param maxRetries: How many times we have to retry the sending upon failure
        :param socketTimeout: The socket timeout value
        """
        with self.lock:
            data = self.send_rcon(cmd, maxRetries=maxRetries, socketTimeout=socketTimeout)
        return data or ''

    def read_socket(self, sock, size=4096, socketTimeout=None):
        """
        Read data from the socket.
        :param sock: The socket from where to read data
        :param size: The read size
        :param socketTimeout: The socket timeout value
        """
        if socketTimeout is None:
            socketTimeout = self.socket_timeout

        data = ''
        readables, writeables, errors = select.select([sock], [], [sock], socketTimeout)

        if not readables:
            self.console.verbose('No readable socket')
            return ''

        while readables:
            payload = sock.recv(size)
            d = payload.decode(encoding=self.rcon_encoding)
            if d:
                # remove rcon header
                data += d.replace(self.rconreplystring, '')
            readables, writeables, errors = select.select([sock], [], [sock], socketTimeout)

        return data

    def stop(self):
        """
        Stop the rcon writelines queue.
        """
        self._stopEvent.set()

    def flush(self):
        pass

    def close(self):
        pass
