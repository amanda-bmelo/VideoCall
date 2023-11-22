import base64
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget
from util.message import Message
from util.thread import thread
from util.wsocket import WSocket
from vidstream import CameraClient, StreamingServer, AudioReceiver, AudioSender
import socket
from socket import socket as Socket


class Client(QWidget):
    update_users = pyqtSignal(list, name="update_users")

    def __init__(
        self,
        on_tcp_state_change=lambda: None,
        on_udp_state_change=lambda: None,
        self_ip=socket.gethostbyname(socket.gethostname()),
        *args,
        **kwargs
    ):
        super(Client, self).__init__(*args, **kwargs)
        self.name: str | None = None
        self.tcp: WSocket | None = None
        self.last_registry: bool | dict | None = None
        self.data: str | None = None

        self.udp = WSocket(
            Socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        )
        self.connected_to_udp = None
        self.connected_to_udp_username: str = "?"
        self.ip: str = self_ip
        self.udp.bind((self_ip, 0))

        self._tcp_state: str = "offline"
        self.on_tcp_state_change = on_tcp_state_change

        self._udp_state: str = "idle"
        self.on_udp_state_change = on_udp_state_change

        self.call_connections: list = []
        self.on_voice_receive = lambda x: None

        thread(self.udp_listen, ())

    def connect_to_server(self, ip: str, port: int =5000):
        try:
            self.tcp = WSocket(
                Socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            )
            self.tcp.connect((ip, port))
            thread(self.tcp_listen, ())

        except Exception as e:
            print("Failed to connect to server with error:\n", e)

    # Make pyqt5 easier to handle
    @property
    def tcp_state(self):
        return self._tcp_state

    @tcp_state.setter
    def tcp_state(self, _v: str):
        self._tcp_state: str = _v
        self.on_tcp_state_change()

    @property
    def udp_state(self):
        return self._udp_state

    @udp_state.setter
    def udp_state(self, _v: str):
        self._udp_state = _v
        self.on_udp_state_change()

    ################################

    # Is a function since you can get it off of the socket
    @property
    def udp_address(self):
        return self.udp.getsockname()

    ###################

    def send(self, message: Message):
        if self.tcp_state == "unregistered" and message.type == Message.kind(
            "register"
        ):
            self.name = message.user_name
            self.tcp_state = "waiting_register"

        elif self.tcp_state == "idle":
            if message.type == Message.kind("registry"):
                self.tcp_state = "waiting_registry"

            elif message.type == Message.kind("unregister"):
                self.tcp_state = "disconnecting"

        self.tcp.send(message)

    def udp_send(self, msg: Message, address):
        if (
            self.udp_state == "idle" and
            msg.type == Message.kind("call_request")
        ):
            self.udp_state = "waiting_response"

        elif self.udp_state == "received_request":
            if msg.type == Message.kind("accept_call"):
                self.udp_state = "on_call"
                self.start_called_stream()

            elif msg.type == Message.kind("reject_call"):
                self.udp_state = "idle"

        elif self.udp_state in [
            "on_call",
            "waiting_response",
        ] and msg.type == Message.kind("end_call"):
            self.udp_state = "idle"
            self.connected_to_udp = None
            self.connected_to_udp_username = "?"

        if address is None:
            return
        self.udp.sendto(msg.encode(), address)

    def tcp_listen(self):
        try:
            self.tcp_state = "unregistered"
            message = None
            while True:
                message = self.tcp.recv(1024)

                if self.tcp_state == "waiting_register":
                    if message.type == Message.kind("accepted_register"):
                        print(
                            "Succesfully registered!"
                        )
                        self.tcp_state = "idle"

                    elif message.type == Message.kind("declined_register"):
                        print(
                            "Some user with that name already exists!" +
                            "Choose another one."
                        )
                        self.name = None
                        self.tcp_state = "unregistered"

                elif self.tcp_state == "waiting_registry":
                    if message.type == Message.kind("registry"):
                        self.last_registry = message.user
                        self.tcp_state = "idle"

                    elif message.type == Message.kind("not_found"):
                        self.last_registry = False
                        self.tcp_state = "idle"

                elif self.tcp_state == "idle" and message.type == Message.kind(
                    "users_list"
                ):
                    self.data = message.data
                    self.update_users.emit(self.data["users"])
                    self.on_udp_state_change()

                elif (
                    self.tcp_state == "disconnecting" and
                    message.type == Message.kind("accepted_unregister")
                ):
                    self.tcp.close()
                    self.tcp_state = "offline"
                    return

        except Exception as e:
            print(e)
            self.tcp_state = "offline"

    def udp_listen(self):
        msg = None
        while 1:
            data, address = self.udp.recvfrom(4096)
            msg = Message.decode(data)
            if (
                self.udp_state == "idle" and
                msg.type == Message.kind("call_request")
            ):
                self.connected_to_udp = address
                self.connected_to_udp_username = msg.user_name
                self.caller_name = msg.user_name
                self.udp_state = "received_request"

            elif (
                self.udp_state != "idle" and
                msg.type == Message.kind("call_request")
            ):
                self.udp_send(Message("occupied"), address)

            elif self.udp_state == "waiting_response":
                if msg.type == Message.kind("accept_call"):
                    self.connected_to_udp = address
                    self.connected_to_udp_username = msg.name
                    self.start_caller_stream()
                    self.udp_state = "on_call"

                elif msg.type in [
                    Message.kind("reject_call"),
                    Message.kind("occupied"),
                ]:
                    self.udp_state = "idle"

            elif self.udp_state == "on_call":
                if (
                    msg.type == Message.kind("voice")
                    and address == self.connected_to_udp
                ):
                    self.received_voice(base64.b64decode(msg.voice))

                elif msg.type == Message.kind("end_call"):
                    self.connected_to_udp = None
                    self.connected_to_udp_username = None
                    self.udp_state = "idle"

    def login(self, username):
        self.send(
            Message(
                "register",
                user_name=username,
                ip=self.udp_address[0],
                porta=self.udp_address[1],
            )
        )

    def logoff(self):
        self.send(Message("unregister"))

    def call_user(self, user_name):
        self.last_registry = None
        self.send(Message("registry", user_name=user_name))

        # Will be false if user doesnt exist
        while self.last_registry is None:
            pass
        if self.last_registry is False:
            return

        user_to_call = self.last_registry
        self.call(user_to_call["ip"], user_to_call["porta"])

    def respond_call_request(self, accept=True):
        if accept:
            self.udp_send(
                Message("accept_call", user_name=self.name),
                self.connected_to_udp,
            )
        else:
            self.udp_send(
                Message("reject_call", user_name=self.name),
                self.connected_to_udp,
            )

    def call(self, ip, porta):
        self.udp_send(
            Message("call_request", user_name=self.name), (ip, porta)
        )

    def end_call(self):
        self.udp_send(Message("end_call"), self.connected_to_udp)
        self.call_connections[0].stop_server()
        self.call_connections[1].stop_server()
        self.call_connections[2].stop_stream()
        self.call_connections[3].stop_stream()

    def start_call(
        self,
        send_video_port,
        recv_video_port,
        send_audio_port,
        recv_audio_port,
    ):
        ip = self.connected_to_udp[0]
        screen = StreamingServer(self.ip, recv_video_port)
        phone = AudioReceiver(self.ip, recv_audio_port)
        camera = CameraClient(ip, send_video_port)
        mic = AudioSender(ip, send_audio_port)
        self.call_connections = [screen, phone, camera, mic]
        thread(screen.start_server, ())
        thread(phone.start_server, ())
        thread(camera.start_stream, ())
        thread(mic.start_stream, ())

    def start_called_stream(self):
        self.start_call(9999, 8888, 7777, 6666)

    def start_caller_stream(self):
        self.start_call(8888, 9999, 6666, 7777)

