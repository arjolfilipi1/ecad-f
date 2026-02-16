from PyQt5.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem
from PyQt5.QtGui import QPainterPath, QPen, QBrush, QColor, QFont
from PyQt5.QtCore import QRectF, QPointF, Qt
import ezdxf
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class DXFCavityRenderer(QGraphicsItem):
    """Renders connector back view from DXF with wire colors"""
    
    def __init__(self, dxf_path: Path, cavities_data: Dict[str, dict] = None):
        super().__init__()
        self.dxf_path = dxf_path
        self.cavities_data = cavities_data or {}  # Maps cavity number -> {wire_color, signal, etc.}
        self.cavity_items = {}
        self.text_items = {}
        self.bounding_rect = QRectF()
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        
        self._load_dxf()
    
    def _load_dxf(self):
        """Load and parse DXF file"""
        if not self.dxf_path.exists():
            return
        
        doc = ezdxf.readfile(str(self.dxf_path))
        msp = doc.modelspace()
        
        # Calculate bounding box
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        # Process entities
        for entity in msp:
            if entity.dxftype() == 'CIRCLE':
                x, y = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                min_x = min(min_x, x - r)
                min_y = min(min_y, y - r)
                max_x = max(max_x, x + r)
                max_y = max(max_y, y + r)
                
                # Store cavity position
                cavity_num = self._find_cavity_number(msp, x, y)
                if cavity_num:
                    self.cavity_items[cavity_num] = (x, y, r)
            
            elif entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                min_x = min(min_x, start.x, end.x)
                min_y = min(min_y, start.y, end.y)
                max_x = max(max_x, start.x, end.x)
                max_y = max(max_y, start.y, end.y)
            
            elif entity.dxftype() == 'LWPOLYLINE':
                for point in entity.get_points():
                    x, y = point[0], point[1]
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        
        # Add padding
        padding = 10
        self.bounding_rect = QRectF(
            min_x - padding, min_y - padding,
            max_x - min_x + padding * 2,
            max_y - min_y + padding * 2
        )
    
    def _find_cavity_number(self, msp, x: float, y: float) -> Optional[str]:
        """Find cavity number text near given coordinates"""
        for text in msp.query('TEXT MTEXT'):
            if text.dxf.layer == 'CAVITY_TEXT':
                tx, ty = text.dxf.insert.x, text.dxf.insert.y
                if abs(tx - x) < 5 and abs(ty - y) < 5:
                    return text.plain_text() if hasattr(text, 'plain_text') else text.dxf.text
        return None
    
    def boundingRect(self):
        """Required for QGraphicsItem"""
        return self.bounding_rect
    
    def paint(self, painter, option, widget=None):
        """Render the connector back view"""
        if not self.dxf_path.exists():
            painter.drawText(10, 20, "DXF not found")
            return
        
        painter.setRenderHint(painter.Antialiasing)
        
        # Draw DXF content
        doc = ezdxf.readfile(str(self.dxf_path))
        msp = doc.modelspace()
        
        for entity in msp:
            if entity.dxftype() == 'CIRCLE':
                self._draw_circle(painter, entity)
            elif entity.dxftype() == 'LINE':
                self._draw_line(painter, entity)
            elif entity.dxftype() == 'LWPOLYLINE':
                self._draw_polyline(painter, entity)
            elif entity.dxftype() == 'TEXT':
                self._draw_text(painter, entity)
            elif entity.dxftype() == 'MTEXT':
                self._draw_mtext(painter, entity)
    
    def _draw_circle(self, painter, entity):
        """Draw a circle with wire color if cavity has data"""
        x, y = entity.dxf.center.x, entity.dxf.center.y
        r = entity.dxf.radius
        
        # Check if this cavity has wire data
        cavity_num = self._find_cavity_number_from_position(x, y)
        
        if cavity_num and cavity_num in self.cavities_data:
            # Color the cavity based on wire color
            wire_color = self.cavities_data[cavity_num].get('wire_color', '')
            color_map = {
                'RT': QColor(255, 0, 0),
                'SW': QColor(0, 0, 0),
                'GN': QColor(0, 255, 0),
                'BL': QColor(0, 0, 255),
                'GE': QColor(255, 255, 0),
                'BR': QColor(165, 42, 42),
                'WS': QColor(255, 255, 255),
                'GR': QColor(128, 128, 128),
            }
            fill_color = color_map.get(wire_color, QColor(200, 200, 200))
            painter.setBrush(QBrush(fill_color))
        else:
            painter.setBrush(QBrush(QColor(240, 240, 240)))
        
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(QPointF(x, y), r, r)
        
        # Draw cavity number
        if cavity_num:
            painter.setPen(QPen(Qt.black, 0.5))
            painter.setFont(QFont("Arial", r * 0.8))
            painter.drawText(QPointF(x - r * 0.3, y + r * 0.3), cavity_num)
    
    def _draw_line(self, painter, entity):
        """Draw a line entity"""
        start = entity.dxf.start
        end = entity.dxf.end
        painter.setPen(QPen(Qt.black, 0.5))
        painter.drawLine(QPointF(start.x, start.y), QPointF(end.x, end.y))
    
    def _draw_polyline(self, painter, entity):
        """Draw a polyline entity"""
        points = entity.get_points()
        if len(points) < 2:
            return
        
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for i in range(1, len(points)):
            path.lineTo(points[i][0], points[i][1])
        
        if entity.closed:
            path.closeSubpath()
        
        painter.setPen(QPen(Qt.black, 0.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    
    def _draw_text(self, painter, entity):
        """Draw text entity"""
        if entity.dxf.layer == 'CAVITY_TEXT':
            return  # Skip cavity numbers - we draw them on cavities
        
        pos = entity.dxf.insert
        text = entity.dxf.text
        height = int(entity.dxf.height)
        
        painter.setPen(QPen(Qt.black, 0.5))
        painter.setFont(QFont("Arial", height))
        painter.drawText(QPointF(pos.x, pos.y), text)
    
    def _draw_mtext(self, painter, entity):
        """Draw mtext entity"""
        if entity.dxf.layer == 'CAVITY_TEXT':
            return
        
        pos = entity.dxf.insert
        text = entity.plain_text()
        height = entity.dxf.char_height
        
        painter.setPen(QPen(Qt.black, 0.5))
        painter.setFont(QFont("Arial", height))
        painter.drawText(QPointF(pos.x, pos.y), text)
    
    def _find_cavity_number_from_position(self, x: float, y: float) -> Optional[str]:
        """Find cavity number for a given position"""
        for cavity_num, (cx, cy, r) in self.cavity_items.items():
            if abs(cx - x) < 1 and abs(cy - y) < 1:
                return cavity_num
        return None
    
    def set_cavity_data(self, cavity_num: str, data: dict):
        """Update wire data for a specific cavity"""
        self.cavities_data[cavity_num] = data
        self.update()
    
    def set_all_cavity_data(self, data: Dict[str, dict]):
        """Update all cavity data at once"""
        self.cavities_data = data
        self.update()
