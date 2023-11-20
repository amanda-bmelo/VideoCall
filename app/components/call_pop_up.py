from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel


class CallPopUp(QDialog):
    def __init__(self, user_name="An unamed user", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Solicitação de chamada de vídeo")

        QBtn = QDialogButtonBox.Yes | QDialogButtonBox.No

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.buttonBox.button(QDialogButtonBox.Yes).setObjectName('yes')
        self.buttonBox.button(QDialogButtonBox.No).setObjectName('no')

        self.setStyleSheet('''
            QDialogButtonBox QAbstractButton#yes {
                color: rgb(0, 90, 0);
                background-color: rgb(120, 200, 120);
                border-color: rgb(0, 90, 0);
                font: 14px;
            }
            QDialogButtonBox QAbstractButton#no {
                color: rgb(90, 0, 0);
                background-color: rgb(220, 120, 120);
                border-color: rgb(90, 0, 0);
                font: 14px;
            }
        ''')

        self.layout = QVBoxLayout()
        message = QLabel(
            f"{user_name} está te ligando!\nDeseja iniciar chamada de vídeo?"
        )
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
