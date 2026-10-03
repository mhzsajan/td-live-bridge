from TDStoreTools import StorageManager
import TDFunctions as TDF
import json
import select
import socket
import time


class LiveBridgeExt:
	"""Persistent, non-blocking client for AbleBridgePlus TCP 9877.

	Runs on the main thread from the frame callback and never blocks: every
	socket call is guarded by select() with a zero timeout. The socket is
	created once and reused, so Live's status bar does not flash
	"Client connected" on each poll.

	Wire contract (MCP_Server/connections/ableton.py), verified against a
	live session:
	  out:  {"type": "<command>", "params": {...}} + "\n"
	  back: one JSON object terminated by "\n"  ->
	        {"status": "success", "result": {...}}
	"""

	HOST = '127.0.0.1'
	PORT = 9877
	COMMAND = 'get_song_transport'

	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		TDF.createProperty(self, 'LiveTempo', value=120.0,
						   dependable=True, readOnly=False)
		TDF.createProperty(self, 'LiveStatus', value='idle',
						   dependable=True, readOnly=False)
		self.sock = None
		self.inbox = b''
		self.outbox = b''
		self.lastSend = 0.0
		self.lastError = ''

	# ---- lifecycle ------------------------------------------------

	def onDestroyTD(self):
		self.DropConnection()

	def DropConnection(self):
		if self.sock is not None:
			try:
				self.sock.close()
			except OSError:
				pass
		self.sock = None
		self.inbox = b''
		self.outbox = b''

	# ---- per-frame pump -------------------------------------------

	def Pump(self):
		"""Called every frame by pump_exec. Returns without blocking."""
		pars = self.ownerComp.par
		if not pars.Connect:
			if self.sock is not None:
				self.DropConnection()
				self.LiveStatus = 'off'
			return

		if self.sock is None:
			self.TryConnect()
			return

		# Schedule the request before flushing so a reply can land same frame.
		now = time.time()
		interval = 1.0 / max(1.0, float(pars.Rate))
		if not self.outbox and now - self.lastSend >= interval:
			self.outbox = (json.dumps(
				{'type': self.COMMAND, 'params': {}}) + '\n').encode('utf-8')
			self.lastSend = now

		self.Flush()
		self.Drain()

	def TryConnect(self):
		# create_connection is the one blocking call here. On loopback a
		# refused connection returns immediately, so this is cheap while
		# Live is closed; it is only attempted when not already connected.
		try:
			sock = socket.create_connection((self.HOST, self.PORT), timeout=0.5)
			sock.setblocking(False)
		except OSError as e:
			self.lastError = str(e)
			self.LiveStatus = 'disconnected'
			return
		self.sock = sock
		self.inbox = b''
		self.outbox = b''
		self.lastSend = 0.0
		self.lastError = ''
		self.LiveStatus = 'connected'

	def Flush(self):
		"""Write pending request bytes, non-blocking."""
		if not self.outbox:
			return
		try:
			_, writable, _ = select.select([], [self.sock], [], 0)
			if not writable:
				return
			sent = self.sock.send(self.outbox)
			self.outbox = self.outbox[sent:]
		except OSError as e:
			self.HandleError(e)

	def Drain(self):
		"""Read whatever arrived and parse every complete line."""
		try:
			readable, _, _ = select.select([self.sock], [], [], 0)
			if not readable:
				return
			chunk = self.sock.recv(65536)
			if not chunk:
				raise ConnectionError('Live closed the connection')
			self.inbox += chunk
		except OSError as e:
			self.HandleError(e)
			return

		# bytes are immutable, so rebind rather than slice-delete.
		while True:
			nl = self.inbox.find(b'\n')
			if nl == -1:
				break
			line = self.inbox[:nl].strip()
			self.inbox = self.inbox[nl + 1:]
			if line:
				self.HandleLine(line)

	# ---- payload --------------------------------------------------

	def HandleLine(self, line):
		try:
			msg = json.loads(line.decode('utf-8', 'replace'))
		except ValueError as e:
			self.lastError = 'malformed JSON: {0}'.format(e)
			return
		if msg.get('status') != 'success':
			self.lastError = str(msg.get('error')
								or msg.get('message') or msg)
			return
		result = msg.get('result')
		if not isinstance(result, dict) or 'tempo' not in result:
			return
		self.LiveTempo = float(result.get('tempo') or 120.0)
		self.LiveStatus = 'connected'
		self.lastError = ''

	def HandleError(self, e):
		self.lastError = str(e)
		self.DropConnection()
		self.LiveStatus = 'disconnected'
