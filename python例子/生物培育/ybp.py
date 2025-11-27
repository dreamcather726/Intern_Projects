import sys
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QConicalGradient, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF

class GaugeWidget(QWidget):
    """
    一个自定义的Qt控件，用于显示圆形的进度条（仪表盘）。
    用于展示温度、湿度等百分比数据。
    """
    def __init__(self, parent=None, min_value=0.0, max_value=0.0, colors=None, gauge_width=20):
        """
        初始化仪表盘控件。
        
        Args:
            parent (QWidget): 父控件。
            min_value (float): 仪表盘的最小值。
            max_value (float): 仪表盘的最大值。
            colors (list): 用于渐变色的QColor列表。
            gauge_width (int): 仪表盘的宽度，单位为像素。
        """
        super().__init__(parent)
        
        self.min_value = min_value
        self.max_value = max_value
        self._value = self.min_value  # 内部存储的当前值
        self.colors = colors if colors else [QColor(1, 253, 209)] # 默认颜色

        # --- 仪表盘几何形状定义 ---
        self.start_angle = 225   # 起始角度 (3点钟方向为0度，顺时针增加)
        self.total_angle = 270   # 总共跨越的角度 (从225度到-45度)
        self.gauge_width = gauge_width     # 进度条的宽度
       

    def setValue(self, value):
        """设置当前值并触发重绘。"""
        self._value = max(self.min_value, min(value, self.max_value))
        self.update() # 请求Qt重绘此控件
        
    def setTotalAngle(self, angle):
        """设置仪表盘的总角度并触发重绘。"""
        self.total_angle = angle
        
        self.update() # 请求Qt重绘此控件
        
    def setStartAngle(self, angle):
        """设置仪表盘的起始角度并触发重绘。"""
        self.start_angle = angle
        self.update() # 请求Qt重绘此控件

    def paintEvent(self, event):
        """
        Qt的绘图事件处理函数。当调用update()时，此函数会被执行。
        负责绘制仪表盘的背景和前景进度条。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 开启抗锯齿，使圆形更平滑

        center_point = self.rect().center()
        radius = min(self.width(), self.height()) / 2
        
        # 动态计算绘制半径，以适应不同的gauge_width
        if hasattr(self, 'custom_margin'):
            margin = self.custom_margin
        elif self.gauge_width > 45:
            margin = self.gauge_width / 2 + 2
        elif self.gauge_width > 35:
            progress = (self.gauge_width - 35) / (45 - 35)
            margin_thin = self.gauge_width / 2 + 24
            margin_thick = self.gauge_width / 2 + 2
            margin = margin_thin + (margin_thick - margin_thin) * progress
        else:
            margin = self.gauge_width / 2 + 24
        draw_radius = radius - margin

        # 定义绘制圆弧的外切矩形
        rect = QRectF(center_point.x() - draw_radius,
                      center_point.y() - draw_radius,
                      draw_radius * 2, draw_radius * 2)

        # --- 绘制前景进度条 (带渐变色) ---
        gradient = QConicalGradient(center_point, self.start_angle)
        
        arc_ratio = self.total_angle / 360.0
        num_colors = len(self.colors)
        if num_colors > 1:
            for i, color in enumerate(self.colors):
                position = (i / (num_colors - 1)) * arc_ratio
                gradient.setColorAt(position, color)
        elif num_colors == 1:
            gradient.setColorAt(0.0, self.colors[0])
            gradient.setColorAt(arc_ratio, self.colors[0])
        
        gradient.setColorAt(1.0, self.colors[0] if self.colors else QColor(Qt.black))
        
        pen = QPen()
        pen.setBrush(QBrush(gradient))
        pen.setWidth(self.gauge_width)
        pen.setCapStyle(Qt.RoundCap) # 设置端点为圆形
        
        painter.setPen(pen)

        # 根据当前值计算需要绘制的角度
        value_angle = (self._value - self.min_value) / (self.max_value - self.min_value) * self.total_angle
        
        # QPainter.drawArc 使用1/16度为单位
        start_draw_angle = int(self.start_angle * 16)
        span_angle = -int(value_angle * 16) # 负值表示顺时针绘制

        painter.drawArc(rect, start_draw_angle, span_angle)