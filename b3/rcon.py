import queue
import re
import select
import socket
import threading

import b3.functions

__author__ = 'ThorN'
__version__ = '1.11'


class Rcon:
    socket_timeout = 0.8
    socket_timeout2 = 0.225
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
        self.socket.settimeout(2.0)
        self.socket.connect(self.host)
        self.lock = threading.Lock()
        self.queue = None
        self._stopEvent = object()
        self._writelines_thread = None

    def send_rcon(self, sock, data, maxRetries=None, socketTimeout=None):
        """
        Send an RCON command.
        :param sock: The socket used to send the payload
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
        while retries < maxRetries:
            sock.settimeout(socketTimeout)
            try:
                sock.sendall(payload)
            except Exception as msg:
                self.console.warning('RCON: send(%s) error: %r', data, msg)
            else:
                try:
                    return self.read_socket(sock, socketTimeout=socketTimeout)
                except Exception as msg:
                    self.console.warning('RCON: read(%s) error: %r', data, msg)

            if re.match(r'^quit|map(_rotate)?.*', data):
                # do not retry quits and map changes since they prevent the
                # server from responding
                return ''

            retries += 1
            self.console.warning('RCON: send(%s) retry %s', data, retries)

        self.console.error('RCON: send(%s) too many tries, aborting', data)
        return ''

    def read_socket(self, sock, size=4096, socketTimeout=0.5):
        """
        Read data from the socket.
        :param sock: The socket from where to read data
        :param size: The read size
        :param socketTimeout: The socket timeout value
        """
        data = b''
        while True:
            readables, _, errors = select.select([sock], [], [sock], socketTimeout)
            if errors:
                raise socket.error
            if not readables:
                break
            payload = sock.recv(size)
            data += payload.replace(self.rconreplystring, b'')
            # lower timeout for subsequent calls
            socketTimeout = self.socket_timeout2

        if data == b'':
            return ''
        return data.decode(encoding=self.console.encoding)

    def write(self, cmd, maxRetries=None, socketTimeout=None):
        """
        Write a RCON command.
        :param cmd: The string to be sent
        :param maxRetries: How many times we have to retry the sending upon failure
        :param socketTimeout: The socket timeout value
        """
        with self.lock:
            data = self.send_rcon(self.socket, cmd, maxRetries=maxRetries, socketTimeout=socketTimeout)
        return data or ''

    def writelines(self, lines):
        """
        Enqueue multiple RCON commands for later processing.
        :param lines: A list of RCON commands.
        """
        q = self.queue
        if not q:
            q = self.queue = queue.Queue(maxsize=100)
            self._writelines_thread = b3.functions.start_daemon_thread(
                target=self._writelines, name='rcon'
            )

        q.put(lines)

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
                        self.send_rcon(self.socket, cmd, maxRetries=1)

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

    def __str__(self):
        return (
            f'Rcon({self.host}, '
            f'timeout={self.socket_timeout}, timeout2={self.socket_timeout2})'
        )

