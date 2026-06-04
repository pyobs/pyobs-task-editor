import re
from PySide6 import QtWidgets, QtCore, QtGui


class _YamlHighlighter(QtGui.QSyntaxHighlighter):
    _RULES: list[tuple[re.Pattern, QtGui.QTextCharFormat]] = []

    def __init__(self, document: QtGui.QTextDocument):
        super().__init__(document)

        def fmt(color: str, bold: bool = False, italic: bool = False) -> QtGui.QTextCharFormat:
            f = QtGui.QTextCharFormat()
            f.setForeground(QtGui.QColor(color))
            if bold:
                f.setFontWeight(QtGui.QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        self._rules = [
            (re.compile(r"#[^\n]*"), fmt("#6a9955", italic=True)),  # comment
            (re.compile(r"^[ \t]*[\w\-]+(?=\s*:)", re.M), fmt("#9cdcfe", bold=True)),  # key
            (re.compile(r'"[^"]*"|\'[^\']*\''), fmt("#ce9178")),  # string
            (re.compile(r"\b(true|false|yes|no|null)\b"), fmt("#569cd6", bold=True)),  # bool/null
            (re.compile(r"\b-?[0-9]+(\.[0-9]+)?\b"), fmt("#b5cea8")),  # number
            (re.compile(r"[&*][^\s]+"), fmt("#c586c0")),  # anchor/alias
            (re.compile(r"!![^\s]+"), fmt("#4ec9b0")),  # tag
            (re.compile(r"^\s*-(?= )", re.M), fmt("#569cd6", bold=True)),  # list marker
        ]

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class YamlEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        font = QtGui.QFont("Courier New", 10)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)

        self._indent = 2  # spaces per indent level
        self._guide_color = QtGui.QColor("#555555")

        self._highlighter = _YamlHighlighter(self.document())
        self._line_number_area = _LineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_width()

    # ── Line numbers ──────────────────────────────────────────────────────────

    def _line_number_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 6 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self):
        self.setViewportMargins(self._line_number_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QtCore.QRect, dy: int):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(cr.left(), cr.top(), self._line_number_width(), cr.height())

    def _paint_line_numbers(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QtGui.QColor("#1e1e1e"))
        painter.setFont(self.font())

        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QtGui.QColor("#858585"))
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 3,
                    self.fontMetrics().height(),
                    QtCore.Qt.AlignmentFlag.AlignRight,
                    str(block.blockNumber() + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    # ── Indent guides ─────────────────────────────────────────────────────────

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)

        painter = QtGui.QPainter(self.viewport())
        painter.setPen(QtGui.QPen(self._guide_color, 1))

        char_w = self.fontMetrics().horizontalAdvance(" ")
        offset = self.contentOffset().x() + self.document().documentMargin()

        block = self.firstVisibleBlock()
        while block.isValid():
            text = block.text()
            indent = len(text) - len(text.lstrip(" "))
            if indent >= self._indent:
                top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
                bottom = top + int(self.blockBoundingRect(block).height())
                if top > self.viewport().height():
                    break
                for level in range(self._indent, indent + 1, self._indent):
                    x = int(offset + level * char_w)
                    painter.drawLine(x, top, x, bottom)
            block = block.next()

    # ── Smart indent on Enter / Tab / Shift+Tab ───────────────────────────────

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key.Key_Return:
            self._handle_return()
        elif event.key() == QtCore.Qt.Key.Key_Tab:
            self._indent_selection(dedent=False)
        elif event.key() == QtCore.Qt.Key.Key_Backtab:
            self._indent_selection(dedent=True)
        else:
            super().keyPressEvent(event)

    def _current_indent(self) -> int:
        cursor = self.textCursor()
        line = cursor.block().text()
        return len(line) - len(line.lstrip(" "))

    def _handle_return(self):
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.rstrip()
        # Extra indent after a mapping key or list marker
        if stripped.endswith(":") or re.match(r"^\s*-\s*$", stripped):
            indent += self._indent
        cursor.insertText("\n" + " " * indent)
        self.setTextCursor(cursor)

    def _indent_selection(self, dedent: bool):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            if dedent:
                # Remove up to _indent spaces before cursor
                pos = cursor.positionInBlock()
                remove = min(self._indent, pos - (pos % self._indent or self._indent))
                if remove > 0:
                    cursor.movePosition(
                        QtGui.QTextCursor.MoveOperation.Left, QtGui.QTextCursor.MoveMode.KeepAnchor, remove
                    )
                    cursor.removeSelectedText()
            else:
                cursor.insertText(" " * self._indent)
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
            if dedent:
                line = cursor.block().text()
                spaces = min(self._indent, len(line) - len(line.lstrip(" ")))
                if spaces:
                    cursor.movePosition(
                        QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, spaces
                    )
                    cursor.removeSelectedText()
            else:
                cursor.insertText(" " * self._indent)
            if not cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock):
                break
            end += self._indent if not dedent else 0
        cursor.endEditBlock()


class _LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor: YamlEditor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, event: QtGui.QPaintEvent):
        self._editor._paint_line_numbers(event)
