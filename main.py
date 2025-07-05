import sys
from PyQt6.QtWidgets import QApplication
from gui import SocialPoster

if __name__ == '__main__':
    app = QApplication(sys.argv)
    poster = SocialPoster()
    poster.show()
    sys.exit(app.exec())