"""The app logo, drawn in code: a cassette's two reels and tape turning into lines of text.

Used for the window icon, the header, and (via write_ico) the .exe icon, so no
image files are needed.
"""

import struct

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap

RED = "#C8102E"
WHITE = "#FFFFFF"


def paint_logo(painter, size):
    """Draws the logo into a size x size square at the painter's origin (designed on a 64 grid)."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 64, size / 64)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(RED))
    painter.drawRoundedRect(QRectF(0, 0, 64, 64), 15, 15)

    pen = QPen(QColor(WHITE), 4.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    # Two tape reels...
    painter.drawEllipse(QPointF(21, 23), 8, 8)
    painter.drawEllipse(QPointF(43, 23), 8, 8)
    # ...joined by the tape running along their bottoms...
    painter.drawLine(QPointF(21, 31), QPointF(43, 31))
    # ...which becomes lines of transcript text.
    painter.drawLine(QPointF(15, 42), QPointF(49, 42))
    painter.drawLine(QPointF(15, 51), QPointF(37, 51))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(WHITE))
    painter.drawEllipse(QPointF(21, 23), 2.5, 2.5)
    painter.drawEllipse(QPointF(43, 23), 2.5, 2.5)
    painter.restore()


def logo_image(size):
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    paint_logo(painter, size)
    painter.end()
    return image


def logo_pixmap(size, device_pixel_ratio=1.0):
    pixmap = QPixmap.fromImage(logo_image(round(size * device_pixel_ratio)))
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    return pixmap


def logo_icon():
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(logo_image(size)))
    return icon


def write_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Writes a multi-size Windows .ico file (PNG-compressed entries) for the .exe."""
    images = []
    for size in sizes:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        logo_image(size).save(buffer, "PNG")
        buffer.close()
        images.append((size, bytes(data)))

    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, png in images:
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO format
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    with open(path, "wb") as f:
        f.write(header + entries + b"".join(png for _, png in images))
