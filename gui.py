import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                            QCheckBox, QLineEdit, QGroupBox, QMessageBox,
                            QFileDialog, QListWidget, QDateTimeEdit, QTabWidget,
                            QDialog, QScrollArea)
from PyQt6.QtCore import Qt, QDateTime
from poster import PostWorker

class SocialPoster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.credentials = self.load_credentials()
        self.platform_prefs = self.load_platform_prefs()
        self.media_files = []
        self.platform_checks = {}
        self.discord_nitro_check = None
        self.discord_separate_check = None
        self.discord_embed_check = None
        self.init_ui()
        self.apply_dark_theme()
    
    def init_ui(self):
        self.setWindowTitle("Multi-Social Poster")
        self.setGeometry(100, 100, 700, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Post tab
        post_tab = QWidget()
        post_layout = QVBoxLayout(post_tab)
        
        # Post content
        post_layout.addWidget(QLabel("Post Content:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter your post content...")
        self.text_edit.setMaximumHeight(150)
        post_layout.addWidget(self.text_edit)
        
        # Character count
        self.char_count = QLabel("0 characters")
        self.text_edit.textChanged.connect(self.update_char_count)
        post_layout.addWidget(self.char_count)
        
        # Media section
        media_layout = QHBoxLayout()
        media_button = QPushButton("Add Media")
        media_button.clicked.connect(self.add_media)
        media_layout.addWidget(media_button)
        
        clear_media_button = QPushButton("Clear Media")
        clear_media_button.clicked.connect(self.clear_media)
        media_layout.addWidget(clear_media_button)
        media_layout.addStretch()
        post_layout.addLayout(media_layout)
        
        # Media list
        self.media_list = QListWidget()
        self.media_list.setMaximumHeight(100)
        post_layout.addWidget(self.media_list)
        
        # Schedule section
        schedule_layout = QHBoxLayout()
        self.schedule_check = QCheckBox("Schedule Post")
        schedule_layout.addWidget(self.schedule_check)
        
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setEnabled(False)
        self.schedule_check.toggled.connect(self.datetime_edit.setEnabled)
        schedule_layout.addWidget(self.datetime_edit)
        schedule_layout.addStretch()
        post_layout.addLayout(schedule_layout)
        
        # Post button
        self.post_button = QPushButton("Post to Selected Platforms")
        self.post_button.clicked.connect(self.post_to_platforms)
        post_layout.addWidget(self.post_button)
        
        post_layout.addStretch()
        self.tabs.addTab(post_tab, "Post")
        
        # Platforms tab
        platforms_tab = QWidget()
        platforms_layout = QVBoxLayout(platforms_tab)
        
        # Platform selection
        platform_group = QGroupBox("Select Platforms to Post To")
        platform_layout = QVBoxLayout()
        
        self.platform_checks = {}
        platforms = ["Twitter", "Bluesky", "Discord", "Reddit"]  # Removed Instagram
        for platform in platforms:
            checkbox = QCheckBox(platform)
            checkbox.setChecked(self.platform_prefs.get(platform, True))
            checkbox.toggled.connect(self.save_platform_prefs)
            self.platform_checks[platform] = checkbox
            platform_layout.addWidget(checkbox)
        
        platform_group.setLayout(platform_layout)
        platforms_layout.addWidget(platform_group)
        
        # Discord options
        discord_group = QGroupBox("Discord Options")
        discord_layout = QVBoxLayout()
        
        self.discord_nitro_check = QCheckBox("Discord Nitro / Vencord (Larger file sizes)")
        self.discord_nitro_check.setChecked(self.platform_prefs.get('discord_nitro', False))
        self.discord_nitro_check.toggled.connect(self.save_platform_prefs)
        discord_layout.addWidget(self.discord_nitro_check)
        
        nitro_info = QLabel("• Standard: 8MB max\n• Nitro/Vencord: 50MB images, 500MB videos")
        nitro_info.setStyleSheet("color: #888888; margin-left: 20px;")
        discord_layout.addWidget(nitro_info)
        
        # Multiple images options
        multi_label = QLabel("Multiple Images Options:")
        multi_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        discord_layout.addWidget(multi_label)
        
        self.discord_embed_check = QCheckBox("Use Discord embeds (via imgBB)")
        self.discord_embed_check.setChecked(self.platform_prefs.get('discord_embed', False))
        self.discord_embed_check.toggled.connect(self.on_discord_mode_changed)
        discord_layout.addWidget(self.discord_embed_check)
        
        embed_info = QLabel("• Uploads images to imgBB first\n• Shows up to 10 images in one message\n• Requires imgBB API key")
        embed_info.setStyleSheet("color: #888888; margin-left: 20px;")
        discord_layout.addWidget(embed_info)
        
        self.discord_separate_check = QCheckBox("Send files as separate messages")
        self.discord_separate_check.setChecked(self.platform_prefs.get('discord_separate', False))
        self.discord_separate_check.toggled.connect(self.on_discord_mode_changed)
        discord_layout.addWidget(self.discord_separate_check)
        
        separate_info = QLabel("• Each file sent as individual message\n• Good for large files or if embeds fail")
        separate_info.setStyleSheet("color: #888888; margin-left: 20px;")
        discord_layout.addWidget(separate_info)
        
        discord_group.setLayout(discord_layout)
        platforms_layout.addWidget(discord_group)
        
        # Platform limitations info
        info_group = QGroupBox("Platform Information")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            "• Twitter: 280 chars, 4 media max\n"
            "• Bluesky: 300 chars, 4 images max (no videos)\n"
            "• Discord: 2000 chars, 10 embeds or 1 attachment (see options)\n"
            "• Reddit: Title from first line (300 chars max), 1 media per post"
        )
        info_text.setStyleSheet("color: #888888;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        platforms_layout.addWidget(info_group)
        
        platforms_layout.addStretch()
        self.tabs.addTab(platforms_tab, "Platforms")
        
        # Status tab
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        status_layout.addWidget(QLabel("Status:"))
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        self.tabs.addTab(status_tab, "Status")
        
        main_layout.addWidget(self.tabs)
        
        # Settings button
        settings_button = QPushButton("Configure Credentials")
        settings_button.clicked.connect(self.open_settings)
        main_layout.addWidget(settings_button)
    
    def add_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Media Files",
            "",
            "Media Files (*.jpg *.jpeg *.png *.gif *.mp4 *.mov *.webm)"
        )
        
        for filepath in files:
            if filepath not in self.media_files:
                self.media_files.append(filepath)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                self.media_list.addItem(f"{os.path.basename(filepath)} ({size_mb:.1f} MB)")
    
    def clear_media(self):
        self.media_files.clear()
        self.media_list.clear()
    
    def on_discord_mode_changed(self):
        """Ensure only one Discord multiple image mode is selected"""
        sender = self.sender()
        if sender == self.discord_embed_check and self.discord_embed_check.isChecked():
            self.discord_separate_check.setChecked(False)
        elif sender == self.discord_separate_check and self.discord_separate_check.isChecked():
            self.discord_embed_check.setChecked(False)
        self.save_platform_prefs()
    
    def update_char_count(self):
        count = len(self.text_edit.toPlainText())
        self.char_count.setText(f"{count} characters")
        if count > 280:
            self.char_count.setStyleSheet("color: #ff6b6b;")
        else:
            self.char_count.setStyleSheet("color: #ffffff;")
    
    def post_to_platforms(self):
        content = self.text_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Warning", "Please enter some content to post.")
            return
        
        selected_platforms = [name for name, checkbox in self.platform_checks.items() 
                            if checkbox.isChecked()]
        
        if not selected_platforms:
            QMessageBox.warning(self, "Warning", "Please select at least one platform.")
            return
        
        scheduled_time = None
        if self.schedule_check.isChecked():
            scheduled_time = self.datetime_edit.dateTime().toPyDateTime()
        
        self.post_button.setEnabled(False)
        self.status_text.clear()
        self.tabs.setCurrentIndex(2)  # Switch to status tab
        
        discord_nitro = self.discord_nitro_check.isChecked()
        discord_separate = self.discord_separate_check.isChecked()
        discord_embed = self.discord_embed_check.isChecked()
        
        self.worker = PostWorker(content, self.media_files, selected_platforms, 
                               self.credentials, scheduled_time, discord_nitro, 
                               discord_separate, discord_embed)
        self.worker.status_update.connect(self.update_status)
        self.worker.finished.connect(self.on_posting_finished)
        self.worker.start()
    
    def update_status(self, message):
        self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def on_posting_finished(self):
        self.post_button.setEnabled(True)
        self.update_status("\n✓ Posting completed!")
    
    def open_settings(self):
        dialog = CredentialsDialog(self.credentials, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.credentials = dialog.get_credentials()
            self.save_credentials()
    
    def load_credentials(self):
        try:
            with open('social_credentials.json', 'r') as f:
                creds = json.load(f)
                # Ensure all platforms exist
                if 'instagram' not in creds:
                    creds['instagram'] = {'access_token': '', 'account_id': ''}
                if 'reddit' not in creds:
                    creds['reddit'] = {
                        'client_id': '',
                        'client_secret': '',
                        'username': '',
                        'password': '',
                        'user_agent': 'SocialPoster/1.0',
                        'subreddits': ''
                    }
                if 'imgbb' not in creds:
                    creds['imgbb'] = {'api_key': ''}
                # Handle old imgur config
                if 'imgur' in creds and 'imgbb' not in creds:
                    creds['imgbb'] = {'api_key': creds['imgur'].get('client_id', '')}
                return creds
        except:
            return {
                'twitter': {'api_key': '', 'api_secret': '', 'bearer_token': '', 
                        'access_token': '', 'access_secret': ''},
                'bluesky': {'handle': '', 'password': ''},
                'discord': {'webhook_url': ''},
                'instagram': {'access_token': '', 'account_id': ''},
                'reddit': {
                    'client_id': '',
                    'client_secret': '',
                    'username': '',
                    'password': '',
                    'user_agent': 'SocialPoster/1.0',
                    'subreddits': ''
                },
                'imgbb': {'api_key': ''}
            }
    
    def save_credentials(self):
        with open('social_credentials.json', 'w') as f:
            json.dump(self.credentials, f, indent=2)
    
    def load_platform_prefs(self):
        try:
            with open('platform_preferences.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'Twitter': True,
                'Bluesky': True,
                'Discord': True,
                'Instagram': False,  # Default to unchecked
                'Reddit': True,
                'discord_nitro': False,
                'discord_separate': False,
                'discord_embed': False
            }
    
    def save_platform_prefs(self):
        if not hasattr(self, 'platform_checks') or not self.platform_checks:
            return
            
        prefs = {}
        for platform, checkbox in self.platform_checks.items():
            prefs[platform] = checkbox.isChecked()
        
        if self.discord_nitro_check:
            prefs['discord_nitro'] = self.discord_nitro_check.isChecked()
        
        if hasattr(self, 'discord_separate_check'):
            prefs['discord_separate'] = self.discord_separate_check.isChecked()
            
        if hasattr(self, 'discord_embed_check'):
            prefs['discord_embed'] = self.discord_embed_check.isChecked()
        
        with open('platform_preferences.json', 'w') as f:
            json.dump(prefs, f, indent=2)
    
    def apply_dark_theme(self):
        dark_style = """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QTextEdit, QLineEdit, QListWidget {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            color: #ffffff;
            padding: 5px;
        }
        QPushButton {
            background-color: #0d7377;
            color: #ffffff;
            border: none;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #14a085;
        }
        QPushButton:pressed {
            background-color: #0a5d61;
        }
        QPushButton:disabled {
            background-color: #3d3d3d;
            color: #777777;
        }
        QGroupBox {
            border: 1px solid #3d3d3d;
            margin-top: 10px;
            padding-top: 10px;
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QCheckBox {
            color: #ffffff;
        }
        QCheckBox::indicator {
            width: 15px;
            height: 15px;
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
        }
        QCheckBox::indicator:checked {
            background-color: #0d7377;
        }
        QLabel {
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            background-color: #1e1e1e;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0d7377;
        }
        QDateTimeEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            color: #ffffff;
            padding: 5px;
        }
        """
        self.setStyleSheet(dark_style)

class CredentialsDialog(QDialog):
    def __init__(self, credentials, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Credentials")
        self.setModal(True)
        self.resize(550, 600)  # Reduced height since Instagram is removed
        self.credentials = credentials.copy()
        # Ensure imgbb exists
        if 'imgbb' not in self.credentials:
            self.credentials['imgbb'] = {'api_key': ''}
        self.apply_dark_theme()
        
        main_layout = QVBoxLayout(self)
        
        # Scroll area for credentials
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Twitter
        twitter_group = QGroupBox("Twitter")
        twitter_layout = QVBoxLayout()
        self.twitter_fields = {}
        for field in ['api_key', 'api_secret', 'bearer_token', 'access_token', 'access_secret']:
            twitter_layout.addWidget(QLabel(field.replace('_', ' ').title() + ':'))
            line_edit = QLineEdit(self.credentials['twitter'].get(field, ''))
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.twitter_fields[field] = line_edit
            twitter_layout.addWidget(line_edit)
        twitter_group.setLayout(twitter_layout)
        scroll_layout.addWidget(twitter_group)
        
        # Bluesky
        bluesky_group = QGroupBox("Bluesky")
        bluesky_layout = QVBoxLayout()
        bluesky_layout.addWidget(QLabel("Handle:"))
        self.bluesky_handle = QLineEdit(self.credentials['bluesky'].get('handle', ''))
        bluesky_layout.addWidget(self.bluesky_handle)
        bluesky_layout.addWidget(QLabel("Password:"))
        self.bluesky_password = QLineEdit(self.credentials['bluesky'].get('password', ''))
        self.bluesky_password.setEchoMode(QLineEdit.EchoMode.Password)
        bluesky_layout.addWidget(self.bluesky_password)
        bluesky_group.setLayout(bluesky_layout)
        scroll_layout.addWidget(bluesky_group)
        
        # Discord
        discord_group = QGroupBox("Discord")
        discord_layout = QVBoxLayout()
        discord_layout.addWidget(QLabel("Webhook URL:"))
        self.discord_webhook = QLineEdit(self.credentials['discord'].get('webhook_url', ''))
        discord_layout.addWidget(self.discord_webhook)
        discord_group.setLayout(discord_layout)
        scroll_layout.addWidget(discord_group)
        
        # Reddit
        reddit_group = QGroupBox("Reddit")
        reddit_layout = QVBoxLayout()
        
        reddit_layout.addWidget(QLabel("Client ID:"))
        self.reddit_client_id = QLineEdit(self.credentials['reddit'].get('client_id', ''))
        reddit_layout.addWidget(self.reddit_client_id)
        
        reddit_layout.addWidget(QLabel("Client Secret:"))
        self.reddit_client_secret = QLineEdit(self.credentials['reddit'].get('client_secret', ''))
        self.reddit_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        reddit_layout.addWidget(self.reddit_client_secret)
        
        reddit_layout.addWidget(QLabel("Username:"))
        self.reddit_username = QLineEdit(self.credentials['reddit'].get('username', ''))
        reddit_layout.addWidget(self.reddit_username)
        
        reddit_layout.addWidget(QLabel("Password:"))
        self.reddit_password = QLineEdit(self.credentials['reddit'].get('password', ''))
        self.reddit_password.setEchoMode(QLineEdit.EchoMode.Password)
        reddit_layout.addWidget(self.reddit_password)
        
        reddit_layout.addWidget(QLabel("User Agent:"))
        self.reddit_user_agent = QLineEdit(self.credentials['reddit'].get('user_agent', 'SocialPoster/1.0'))
        reddit_layout.addWidget(self.reddit_user_agent)
        
        reddit_layout.addWidget(QLabel("Subreddits (comma-separated):"))
        self.reddit_subreddits = QLineEdit(self.credentials['reddit'].get('subreddits', ''))
        self.reddit_subreddits.setPlaceholderText("e.g., python, programming, webdev")
        reddit_layout.addWidget(self.reddit_subreddits)
        
        # Add info label
        reddit_info = QLabel("Note: Create app at reddit.com/prefs/apps")
        reddit_info.setStyleSheet("color: #888888; font-size: 11px;")
        reddit_layout.addWidget(reddit_info)
        
        reddit_group.setLayout(reddit_layout)
        scroll_layout.addWidget(reddit_group)
        
        # imgBB
        imgbb_group = QGroupBox("imgBB (for Discord embed image hosting)")
        imgbb_layout = QVBoxLayout()
        
        imgbb_layout.addWidget(QLabel("API Key:"))
        self.imgbb_api_key = QLineEdit(self.credentials['imgbb'].get('api_key', ''))
        self.imgbb_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        imgbb_layout.addWidget(self.imgbb_api_key)
        
        # Add info label
        imgbb_info = QLabel("Note: Get your free API key at api.imgbb.com\nSupports images up to 32MB")
        imgbb_info.setStyleSheet("color: #888888; font-size: 11px;")
        imgbb_layout.addWidget(imgbb_info)
        
        imgbb_group.setLayout(imgbb_layout)
        scroll_layout.addWidget(imgbb_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
    
    def save_and_close(self):
        for field, widget in self.twitter_fields.items():
            self.credentials['twitter'][field] = widget.text()
        self.credentials['bluesky']['handle'] = self.bluesky_handle.text()
        self.credentials['bluesky']['password'] = self.bluesky_password.text()
        self.credentials['discord']['webhook_url'] = self.discord_webhook.text()
        # Instagram credentials are kept but not modified through UI
        self.credentials['reddit']['client_id'] = self.reddit_client_id.text()
        self.credentials['reddit']['client_secret'] = self.reddit_client_secret.text()
        self.credentials['reddit']['username'] = self.reddit_username.text()
        self.credentials['reddit']['password'] = self.reddit_password.text()
        self.credentials['reddit']['user_agent'] = self.reddit_user_agent.text()
        self.credentials['reddit']['subreddits'] = self.reddit_subreddits.text()
        self.credentials['imgbb']['api_key'] = self.imgbb_api_key.text()
        self.accept()
    
    def get_credentials(self):
        return self.credentials
    
    def apply_dark_theme(self):
        dark_style = """
        QDialog {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            color: #ffffff;
            padding: 5px;
        }
        QPushButton {
            background-color: #0d7377;
            color: #ffffff;
            border: none;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #14a085;
        }
        QPushButton:pressed {
            background-color: #0a5d61;
        }
        QGroupBox {
            border: 1px solid #3d3d3d;
            margin-top: 10px;
            padding-top: 10px;
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLabel {
            color: #ffffff;
        }
        QScrollArea {
            border: none;
            background-color: #1e1e1e;
        }
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #3d3d3d;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4d4d4d;
        }
        """
        self.setStyleSheet(dark_style)