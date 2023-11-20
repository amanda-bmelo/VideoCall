import PyQt5
from PyQt5.QtWidgets import (
    QMainWindow,
    QTableWidgetItem,
    QWidget,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QVBoxLayout,
)
from PyQt5.QtCore import pyqtSlot
from app.client import Client
from app.components.call_pop_up import CallPopUp
from .server import ip_address


class Window(QMainWindow):
    state_change = PyQt5.QtCore.pyqtSignal()

    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(150, 150, 600, 550)

        self.setStyleSheet(
            """
            QWidget { background-color: white;
            font: 14px; }
            QPushButton {
            color: rgb(0, 90, 90);
            background-color: rgb(190, 225, 225);
            border-style: outset;
            border-width: 1px;
            border-radius: 10px;
            border-color: rgb(0, 90, 90);
            font: 12px;
            min-width: 8em;
            padding: 6px;
            margin: 10px 0px 20px 0px;
            }
            QPushButton:pressed {
            color: rgb(60, 128, 124);
            background-color: rgb(180, 228, 227);
            border-color: rgb(110, 205, 200);
            }
            QLineEdit {
            color: black;
            background-color: rgb(255, 255, 253);
            border-style: outset;
            border-width: 1px;
            border-radius: 5px;
            border-color: lightblue;
            font: 12px;
            min-width: 8em;
            padding: 10px;
            }
            QTableWidget {
            color: rgb(0, 70, 70);
            border-width: 0px;
            border-style: solid;
            }
            QHeaderView::section {
            background-color: rgb(200, 235, 235);
            border-width: 0px 0px 1px 0px;
            border-color: rgb(120, 155, 155);
            border-style: outset;
            padding: 5px;
            }"""
        )
        self.setWindowTitle("Video Call - conecte com seus amigos")
        self.console_history = []
        self.tcp_state = "offline"
        self.udp_state = "idle"

        self.state_change.connect(self.updated_state)
        self.client = Client(
            self.state_change.emit, self.state_change.emit, ip_address
        )
        self.client.update_users.connect(self.update_connection_table)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        formLayout = QFormLayout()

        # Connection
        self.ip = QLineEdit()
        self.ip.setText(ip_address)
        self.connect_btn = QPushButton("Conectar com servidor", self)
        self.connect_btn.clicked.connect(self.connect)
        formLayout.addRow("IP do Servidor: [0.0.0.0]", self.ip)
        formLayout.addRow(self.connect_btn)
        #######

        # Login
        self.user_name = QLineEdit()
        self.user_name.setText("Fulano")
        self.login_btn = QPushButton("Logar", self)
        self.login_btn.clicked.connect(self.login)
        formLayout.addRow("Seu nome:", self.user_name)
        formLayout.addRow(self.login_btn)
        #######

        # TCP server stuff
        self.server_status = QLabel(self)
        self.server_status.setGeometry(20, 20, 100, 100)
        self.server_status.setText("[offline]")
        formLayout.addRow("Status do servidor: ", self.server_status)

        self.user_to_call = QLineEdit()
        self.server_status.setGeometry(50, 50, 100, 100)
        formLayout.addRow("Para quem deseja ligar?", self.user_to_call)
        #######

        # Action bar
        h_box_layout = QHBoxLayout()
        self.dc = QPushButton("Desconectar (do servidor)")
        self.dc.setStyleSheet(
            "color: rgb(90, 0, 0);"
            + "background-color: rgb(220, 120, 120);"
            + "border-color: rgb(90, 0, 0);"
        )
        self.dc.clicked.connect(self.disconnect)
        h_box_layout.addWidget(self.dc)

        self.call_btn = QPushButton("Iniciar chamada")
        self.call_btn.setStyleSheet(
            "color: rgb(0, 90, 0);"
            + "background-color: rgb(120, 200, 120);"
            + "border-color: rgb(0, 90, 0);"
            + "font: 14px;"
        )
        self.call_btn.clicked.connect(self.call)
        h_box_layout.addWidget(self.call_btn, 1)

        self.ec = QPushButton("Desligar chamada")
        self.ec.setStyleSheet(
            "color: rgb(90, 0, 0);"
            + "background-color: rgb(220, 120, 120);"
            + "border-color: rgb(90, 0, 0);"
            + "font: 14px;"
        )
        self.ec.clicked.connect(self.end_call)
        h_box_layout.addWidget(self.ec, 2)

        formLayout.addRow(h_box_layout)
        #######

        # Connection Table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setRowCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["Nome", "IP", "Porta"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.tableWidget)
        formLayout.addRow(v_box_layout)
        #######

        self.centralWidget.setLayout(formLayout)

        self.updated_state()

    def updated_state(self):
        self.tcp_state = self.client.tcp_state
        self.udp_state = self.client.udp_state
        self.server_status.setText(f"[tcp:{self.tcp_state}, udp:{self.udp_state}]")

        # UDP #
        if self.udp_state == "idle":
            self.ec.setDisabled(True)
            self.call_btn.setDisabled(False)

        elif self.udp_state == "waiting_response":
            self.ec.setDisabled(False)
            self.call_btn.setDisabled(True)

        elif self.udp_state == "received_request":
            self.client.respond_call_request(self.call_request_pop_up())
            self.ec.setDisabled(True)
            self.call_btn.setDisabled(True)

        elif self.udp_state == "on_call":
            self.ec.setDisabled(False)
            self.call_btn.setDisabled(True)

        # TCP #
        if self.tcp_state == "offline":
            # Connect to server enabled
            self.ip.setDisabled(False)
            self.connect_btn.setDisabled(False)

            # Set name disbled
            self.user_name.setDisabled(True)
            self.login_btn.setDisabled(True)

            # Call disabled
            self.dc.setDisabled(True)
            self.call_btn.setDisabled(True)
            self.user_to_call.setDisabled(True)

            self.clear_table()

        elif self.tcp_state == "unregistered":
            # Connect to server enabled
            self.ip.setDisabled(True)
            self.connect_btn.setDisabled(True)

            # Set name disbled
            self.user_name.setDisabled(False)
            self.login_btn.setDisabled(False)

            # Call disabled
            self.dc.setDisabled(True)
            self.call_btn.setDisabled(True)
            self.user_to_call.setDisabled(True)

        elif self.tcp_state == "waiting_register":
            # Connect to server enabled
            self.ip.setDisabled(True)
            self.connect_btn.setDisabled(True)

            # Set name disbled
            self.user_name.setDisabled(True)
            self.login_btn.setDisabled(True)

            # Call disabled
            self.dc.setDisabled(True)
            self.call_btn.setDisabled(True)
            self.user_to_call.setDisabled(True)

        elif self.tcp_state == "idle":
            # Connect to server enabled
            self.ip.setDisabled(True)
            self.connect_btn.setDisabled(True)

            # Set name disbled
            self.user_name.setDisabled(True)
            self.login_btn.setDisabled(True)

            # Call disabled
            self.dc.setDisabled(False)
            self.call_btn.setDisabled(False)
            self.user_to_call.setDisabled(False)

    def connect(self):
        self.client.connect_to_server(self.ip.text())

    def disconnect(self):
        self.client.logoff()

    def login(self):
        self.client.login(self.user_name.text())

    def call(self):
        self.client.call_user(self.user_to_call.text())

    def end_call(self):
        self.client.end_call()

    def call_request_pop_up(self):
        p = CallPopUp(self.client.caller_name, self)
        return p.exec_()

    @pyqtSlot(list, name="users_list")
    def update_connection_table(self, data):
        self.clear_table()
        index = 0
        for user in data:
            self.tableWidget.setItem(index, 0, QTableWidgetItem(user["name"]))
            self.tableWidget.setItem(index, 1, QTableWidgetItem(user["ip"]))
            self.tableWidget.setItem(
                index, 2, QTableWidgetItem(str(user["porta"]))
            )
            index += 1

    def clear_table(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(3)
