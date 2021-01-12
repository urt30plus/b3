import queue
import re
import select
import socket
import threading
import time

import b3.functions

__author__ = 'ThorN'
__version__ = '1.11'


class Rcon:
    socket_timeout = 0.80
    rconreplystring = b'\377\377\377\377print\n'

    def __init__(self, console, host, password):
        """
        :param console: The console implementation
        :param host: The host where to send RCON commands
        :param password: The RCON password
        """
        self.console = console
        self.host = host
        self.rconsendstring = f'\377\377\377\377rcon "{password}" '.encode(
            self.console.encoding
        )
        self.socket = socket.socket(type=socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.connect(self.host)
        self.lock = threading.Lock()
        self.queue = None
        self._stopEvent = object()
        self.console.bot('Game name is: %s', self.console.gameName)
        self._writelines_thread = None

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
        payload = self.rconsendstring + data.encode(self.console.encoding) + b'\n'

        retries = 0
        start_time = time.time()
        while time.time() - start_time < 5:
            readables, writeables, errors = select.select([], [self.socket], [self.socket], socketTimeout)

            if errors:
                self.console.warning('RCON send_rcon: %s', str(errors))
            elif writeables:
                try:
                    writeables[0].send(payload)
                except Exception as msg:
                    self.console.warning('RCON: error sending: %r', msg)
                else:
                    try:
                        return self.read_socket(self.socket, socketTimeout=socketTimeout)
                    except Exception as msg:
                        self.console.warning('RCON: error reading: %r', msg)

                if re.match(r'^quit|map(_rotate)?.*', data):
                    # do not retry quits and map changes since they prevent the server from responding
                    return ''

            time.sleep(0.05)
            retries += 1
            if retries >= maxRetries:
                self.console.error('RCON: too many tries: aborting (%r)', data)
                break
        return ''

    def read_socket(self, sock, size=4096, socketTimeout=None):
        """
        Read data from the socket.
        :param sock: The socket from where to read data
        :param size: The read size
        :param socketTimeout: The socket timeout value
        """
        if socketTimeout is None:
            socketTimeout = self.socket_timeout

        readables, writeables, errors = select.select([sock], [], [sock], socketTimeout)

        if errors:
            self.console.warning('RCON read_socket: %s', str(errors))

        if not readables:
            return ''

        data = b''
        while readables:
            if payload := sock.recv(size):
                # remove rcon header
                data += payload.replace(self.rconreplystring, b'')
            readables, writeables, errors = select.select([sock], [], [sock], socketTimeout)

        return data.decode(encoding=self.console.encoding)

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

    def writelines(self, lines):
        """
        Enqueue multiple RCON commands for later processing.
        :param lines: A list of RCON commands.
        """
        if not self.queue:
            self.queue = queue.Queue()
            self._writelines_thread = b3.functions.start_daemon_thread(
                target=self._writelines, name='rcon'
            )

        self.queue.put(lines)

    def _writelines(self):
        """
        Write multiple RCON commands on the socket.
        """
        while True:
            lines = self.queue.get()
            if lines is self._stopEvent:
                break
            for cmd in lines:
                if cmd:
                    with self.lock:
                        self.send_rcon(cmd, maxRetries=1)

    def stop(self):
        """
        Stop the rcon writelines queue.
        """
        if self.queue:
            self.queue.put(self._stopEvent)
            self._writelines_thread.join(timeout=5.0)

    def close(self):
        self.stop()
        with self.lock:
            self.socket.close()
