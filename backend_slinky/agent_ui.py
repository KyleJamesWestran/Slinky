import sys
import uuid
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QFileDialog, QHBoxLayout, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QProcess
from agent_config_manager import load_config, save_config

class SlinkyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slinky Service Manager")
        self.setGeometry(200, 200, 600, 500)

        self.config = load_config()
        self.process = QProcess(self)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Unique ID Display
        self.uuid_label = QLabel(f"Unique ID: {self.config['unique_id']}")
        layout.addWidget(self.uuid_label)

        # Connections List
        layout.addWidget(QLabel("Connections:"))
        self.conn_list = QListWidget()
        self.refresh_connection_list()
        layout.addWidget(self.conn_list)

        # Add/Edit Form
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Connection Name")
        form_layout.addWidget(self.name_input)

        self.type_select = QComboBox()
        self.type_select.addItems(["filemanager", "mssql", "sqlite"])
        self.type_select.currentIndexChanged.connect(self.on_type_change)
        form_layout.addWidget(self.type_select)

        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText("Path / Conn String / DB Name")
        form_layout.addWidget(self.param_input)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        form_layout.addWidget(browse_btn)

        add_btn = QPushButton("Add / Update")
        add_btn.clicked.connect(self.add_or_update_connection)
        form_layout.addWidget(add_btn)

        layout.addLayout(form_layout)

        # Start/Stop Buttons
        self.start_btn = QPushButton("Start Service")
        self.start_btn.clicked.connect(self.start_service)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop Service")
        self.stop_btn.clicked.connect(self.stop_service)
        layout.addWidget(self.stop_btn)

        # Output box
        layout.addWidget(QLabel("Service Output:"))
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    def refresh_connection_list(self):
        self.conn_list.clear()
        for conn in self.config['connections']:
            display = f"{conn['connection_name']} ({conn['connection_type']})"
            self.conn_list.addItem(display)

    def on_type_change(self):
        self.param_input.setPlaceholderText({
            "filemanager": "Path",
            "mssql": "Connection String",
            "sqlite": "Database Name"
        }[self.type_select.currentText()])

    def browse_file(self):
        if self.type_select.currentText() == "filemanager":
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
            if path:
                self.param_input.setText(path)

    def add_or_update_connection(self):
        name = self.name_input.text().strip()
        conn_type = self.type_select.currentText()
        param = self.param_input.text().strip()

        if not name or not param:
            return

        # Check if connection already exists to preserve gui
        existing_conn = next((c for c in self.config['connections'] if c['connection_name'] == name), None)
        gui_id = existing_conn.get("connection_gui") if existing_conn else str(uuid.uuid4())

        # Remove old entry if editing
        self.config['connections'] = [c for c in self.config['connections'] if c['connection_name'] != name]

        conn = {
            "connection_name": name,
            "connection_type": conn_type,
            "connection_gui": gui_id
        }

        if conn_type == "filemanager":
            conn["connection_path"] = param
        elif conn_type == "mssql":
            conn["connection_string"] = param
        elif conn_type == "sqlite":
            conn["connection_database_name"] = param

        self.config['connections'].append(conn)
        save_config(self.config)
        self.refresh_connection_list()

    def start_service(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.output_box.append("Service already running.")
            return

        self.output_box.append("Starting service...")
        self.process.start(sys.executable, ["-u", "agent_service.py"])

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf-8")
        self.output_box.append(stdout)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf-8")
        self.output_box.append(stderr)

    def process_finished(self):
        self.output_box.append("Service stopped.")

    def stop_service(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.output_box.append("Stopping service...")
            self.process.terminate()

            if not self.process.waitForFinished(3000):  # Wait up to 3 seconds
                self.output_box.append("Force killing service...")
                self.process.kill()
        else:
            self.output_box.append("Service is not running.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = SlinkyUI()
    ui.show()
    sys.exit(app.exec())
