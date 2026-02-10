from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem
from PyQt5.QtCore import QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush


# -------------------------------------------------
# Wire Segment (drawable)
# -------------------------------------------------

class WireSegmentItem(QGraphicsLineItem):
    def __init__(self, p1: QPointF, p2: QPointF, net):
        super().__init__(QLineF(p1, p2))
        self.net = net
    
        self.setPen(QPen(net.color, 2))
        self.setFlag(self.ItemIsSelectable)
        self.setZValue(-1)

    def start(self):
        return self.line().p1()

    def end(self):
        return self.line().p2()

    def set_start(self, p):
        l = self.line()
        l.setP1(p)
        self.setLine(l)

    def set_end(self, p):
        l = self.line()
        l.setP2(p)
        self.setLine(l)


# -------------------------------------------------
# Junction
# -------------------------------------------------

class JunctionItem(QGraphicsEllipseItem):
    def __init__(self, pos: QPointF, net):
        super().__init__(-3, -3, 6, 6)
        self.net = net
        self.segments = []

        self.setPos(pos)
        self.setBrush(QBrush(net.color))
        self.setZValue(1)


# -------------------------------------------------
# Wire Item (logical)
# -------------------------------------------------

class WireItem:
    """
    Logical wire (not drawable).
    Owns segments and junctions.
    """

    def __init__(self,wid, net, scene):
        self.net = net
        self.wid = wid
        self.scene = scene

        self.segments = []
        self.junctions = []

        self._start_point = None

        net.wires.append(self)

    # ---------------------------------------------
    # Creation API (used by SchematicView)
    # ---------------------------------------------

    def start_at(self, point: QPointF):
        self._start_point = point

    def finish_at(self, point: QPointF):
        if self._start_point is None:
            return

        segment = WireSegmentItem(self._start_point, point, self.net)
        self._register_segment(segment)

        self._auto_junctions(segment)
        self._start_point = None

    # ---------------------------------------------
    # Segment & Junction management
    # ---------------------------------------------

    def _register_segment(self, segment):
        self.segments.append(segment)
        self.net.segments.append(segment)
        self.scene.addItem(segment)

    def _auto_junctions(self, new_seg):
        for item in list(self.scene.items()):
            if not isinstance(item, WireSegmentItem):
                continue
            if item is new_seg:
                continue
            if item.net != self.net:
                continue

            ip = self._intersection_point(new_seg, item)
            if not ip:
                continue

            if not self._is_endpoint(item, ip):
                self._split_segment(item, ip)

            if not self._is_endpoint(new_seg, ip):
                self._split_segment(new_seg, ip)

            junction = self._find_or_create_junction(ip)
            self._attach_segments(junction, ip)

    def _split_segment(self, seg, point):
        p1 = seg.start()
        p2 = seg.end()

        self.scene.removeItem(seg)
        self.segments.remove(seg)
        self.net.segments.remove(seg)

        s1 = WireSegmentItem(p1, point, self.net)
        s2 = WireSegmentItem(point, p2, self.net)

        self._register_segment(s1)
        self._register_segment(s2)

    def _find_or_create_junction(self, point):
        for j in self.junctions:
            if j.pos() == point:
                return j

        j = JunctionItem(point, self.net)
        self.junctions.append(j)
        self.net.junctions.append(j)
        self.scene.addItem(j)
        return j

    def _attach_segments(self, junction, point):
        for seg in self.segments:
            if seg.start() == point or seg.end() == point:
                if seg not in junction.segments:
                    junction.segments.append(seg)

    # ---------------------------------------------
    # Geometry helpers
    # ---------------------------------------------

    def _intersection_point(self, s1, s2):
        l1 = s1.line()
        l2 = s2.line()
        itype, point = l1.intersect(l2)
        if itype == QLineF.BoundedIntersection:
            return point
        return None

    def _is_endpoint(self, seg, point):
        return seg.start() == point or seg.end() == point