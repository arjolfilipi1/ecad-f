#model/models
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Tuple, NamedTuple, Any
import json
from datetime import datetime
import math
import uuid
from itertools import count

class GermanWireColor(NamedTuple):
    """Standard German automotive wire colors with RGB values"""
    code: str  # Standard abbreviation
    name_de: str  # German name
    name_en: str  # English name
    rgb: Tuple[int, int, int]  # RGB values (0-255)
    hex_code: str  # Hex color code

class GermanWireColors:
    """Standard German automotive wire colors according to DIN 72551"""
    
    # Base colors
    SW = GermanWireColor("SW", "Schwarz", "Black", (0, 0, 0), "#000000")
    BR = GermanWireColor("BR", "Braun", "Brown", (102, 51, 0), "#663300")
    RT = GermanWireColor("RT", "Rot", "Red", (255, 0, 0), "#FF0000")
    GN = GermanWireColor("GN", "Grün", "Green", (0, 128, 0), "#008000")
    BL = GermanWireColor("BL", "Blau", "Blue", (0, 0, 255), "#0000FF")
    VI = GermanWireColor("VI", "Violett", "Violet", (128, 0, 128), "#800080")
    GR = GermanWireColor("GR", "Grau", "Gray", (128, 128, 128), "#808080")
    WS = GermanWireColor("WS", "Weiß", "White", (255, 255, 255), "#FFFFFF")
    GE = GermanWireColor("GE", "Gelb", "Yellow", (255, 255, 0), "#FFFF00")
    OR = GermanWireColor("OR", "Orange", "Orange", (255, 165, 0), "#FFA500")
    RS = GermanWireColor("RS", "Rosa", "Pink", (255, 192, 203), "#FFC0CB")
    TK = GermanWireColor("TK", "Türkis", "Turquoise", (64, 224, 208), "#40E0D0")
    
    # Metallic colors
    SI = GermanWireColor("SI", "Silber", "Silver", (192, 192, 192), "#C0C0C0")
    
    @classmethod
    def get_all_colors(cls) -> Dict[str, GermanWireColor]:
        """Return all available colors as a dictionary"""
        return {
            'SW': cls.SW, 'BR': cls.BR, 'RT': cls.RT, 'GN': cls.GN,
            'BL': cls.BL, 'VI': cls.VI, 'GR': cls.GR, 'WS': cls.WS,
            'GE': cls.GE, 'OR': cls.OR, 'RS': cls.RS, 'TK': cls.TK,
            'SI': cls.SI
        }
    
    @classmethod
    def get_color(cls, color_code: str) -> GermanWireColor:
        """Get a specific color by its code"""
        colors = cls.get_all_colors()
        return colors.get(color_code.upper(), cls.SW)  # Default to black if not found
    
    @classmethod
    def is_valid_color(cls, color_code: str) -> bool:
        """Check if a color code is valid"""
        return color_code.upper() in cls.get_all_colors()
    
    @classmethod
    def get_color_display_name(cls, color_code: str, language: str = 'en') -> str:
        """Get the display name for a color code"""
        color = cls.get_color(color_code)
        return color.name_en if language == 'en' else color.name_de
    
    @classmethod
    def get_rgb(cls, color_code: str) -> Tuple[int, int, int]:
        """Get RGB values for a color code"""
        return cls.get_color(color_code).rgb
    
    @classmethod
    def get_hex_code(cls, color_code: str) -> str:
        """Get hex color code for a color code"""
        return cls.get_color(color_code).hex_code

# Example of combined colors (base + stripe)
class CombinedWireColor:
    """Represents a wire with base color and stripe"""
    def __init__(self, base_color: Optional[str] = None, stripe_color: Optional[str] = None,color: Optional[str] = None):
        if color is None:
            base_color = 'SW' if not base_color else base_color
            self.base_color = base_color.upper()
            self.stripe_color = stripe_color.upper() if stripe_color else None
        else:
            if "/" not in color:
                self.base_color = color
                self.stripe_color = None
            else:
                self.base_color,self.stripe_color = color.split("/")
        if not GermanWireColors.is_valid_color(self.base_color):
            raise ValueError(f"Invalid base color code: {base_color}")
        
        if self.stripe_color and not GermanWireColors.is_valid_color(self.stripe_color):
            raise ValueError(f"Invalid stripe color code: {stripe_color}")
    
    def to_dict(self):
        return { 'color': (self.base_color + "/" +self.stripe_color) if self.stripe_color else self.base_color }
    def upper(self):
        return self.code.upper()
    @property
    def code(self) -> str:
        """Get the combined color code (e.g., 'SW/GE' for black with yellow stripe)"""
        if self.stripe_color:
            return f"{self.base_color}/{self.stripe_color}"
        return self.base_color
    
    @property
    def display_name(self, language: str = 'en') -> str:
        """Get display name"""
        base_name = GermanWireColors.get_color_display_name(self.base_color, language)
        if self.stripe_color:
            stripe_name = GermanWireColors.get_color_display_name(self.stripe_color, language)
            return f"{base_name}/{stripe_name}" if language == 'en' else f"{base_name}/{stripe_name}"
        return base_name
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Get RGB values (returns base color RGB)"""
        return GermanWireColors.get_rgb(self.base_color)
    
    @property
    def hex_code(self) -> str:
        """Get hex color code (returns base color hex)"""
        return GermanWireColors.get_hex_code(self.base_color)
    
    def get_stripe_rgb(self) -> Optional[Tuple[int, int, int]]:
        """Get RGB values for the stripe"""
        if self.stripe_color:
            return GermanWireColors.get_rgb(self.stripe_color)
        return None
    
    def __str__(self) -> str:
        return self.code
        
class ConnectorType(Enum):
    JT = "Junior Timer"
    GT = "General Timer"
    MT = "Micro Timer"
    DTM = "Deutsch DTM"
    DTP = "Deutsch DTP"
    SQUARE = "Square Connector"
    OTHER = "Other"

class SealType(Enum):
    UNSEALED = "Unsealed"
    CONNECTOR_SEALED = "Connector Sealed"
    FULLY_SEALED = "Fully Sealed"

class Gender(Enum):
    MALE = "Male"
    FEMALE = "Female"

class WireType(Enum):
    FLRY_B_0_35 = "FLRY-B 0.35 mm²"
    FLRY_B_0_5 = "FLRY-B 0.5 mm²"
    FLRY_B_0_75 = "FLRY-B 0.75 mm²"
    FLRY_B_1_0 = "FLRY-B 1.0 mm²"
    FLRY_B_1_5 = "FLRY-B 1.5 mm²"
    FLRY_B_2_5 = "FLRY-B 2.5 mm²"

class ProtectionType(Enum):
    BRAIDED_SLEEVE = "Braided Sleeve (PET)"
    SHRINK_TUBING = "Heat Shrink Tubing"
    SPIRAL_WRAP = "Spiral Wrap"
    FLEX_CONDUIT = "Flexible Conduit"
    TAPE = "Friction Tape"
    FABRIC_TAPE = "Fabric Tape"

class NodeType(Enum):
    CONNECTOR = "CONNECTOR"
    SPLICE = "SPLICE"
    GROUND = "GROUND"
    TERMINAL = "TERMINAL"
    BREAKOUT = "BREAKOUT"

class FastenerCategory(Enum):
    CLIP = "Clip"
    BRACKET = "Bracket"
    BOLT = "Bolt"
    NUT = "Nut"
    WASHER = "Washer"
    TIE = "Cable Tie"
    GROMMET = "Grommet"
    OTHER = "Other"

class FastenerMaterial(Enum):
    NYLON = "Nylon"
    STEEL = "Steel"
    STAINLESS_STEEL = "Stainless Steel"
    ALUMINUM = "Aluminum"
    PLASTIC = "Plastic"
    RUBBER = "Rubber"

@dataclass
class FastenerType:
    id: str
    name: str
    description: Optional[str] = None
    category: FastenerCategory = FastenerCategory.CLIP
    material: FastenerMaterial = FastenerMaterial.NYLON
    default_size: Optional[str] = None

@dataclass
class Fastener:
    id: str
    harness_id: str
    type: FastenerType
    part_number: str
    quantity: int = 1
    position: Tuple[float, float] = (0.0, 0.0)
    orientation: float = 0.0  # Rotation in degrees
    size: Optional[str] = None
    torque_nm: Optional[float] = None  # Torque specification
    notes: Optional[str] = None
    branch_id: Optional[str] = None  # If attached to a branch
    distance_from_start_mm: Optional[float] = None  # Position along branch
    node_id: Optional[str] = None  # If attached to a node
    
@dataclass
class TopologySegment:
    """Represents a segment in the topology graph"""
    id: str
    start_node_id: str
    end_node_id: str
    wire_ids: List[str] = field(default_factory=list)
    bundle_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'start_node_id': self.start_node_id,
            'end_node_id': self.end_node_id,
            'wire_ids': self.wire_ids,
            'bundle_id': self.bundle_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TopologySegment':
        return cls(
            id=data['id'],
            start_node_id=data['start_node_id'],
            end_node_id=data['end_node_id'],
            wire_ids=data.get('wire_ids', []),
            bundle_id=data.get('bundle_id')
        )

@dataclass
class Pin:
    """Represents a single cavity/pin within a connector."""
    pid: str
    number: str
    gender: Gender
    seal: SealType
    wire_ids: List[str] = None
    description: Optional[str] = None
    current_rating: Optional[float] = None  # Amps
    graphics_item: Optional[any] = None
    
    @property
    def id(self):
        return self.pid
        
    def is_used(self) -> bool:
        return len(self.wire_ids) > 0
        
    def add_wire_model(self,wire):
        
        if isinstance(wire,Wire):
            if not self.wire_ids:
                self.wire_ids = []
            if wire.id not in self.wire_ids:
                self.wire_ids.append(wire.id)
        else:
            print("wire model given to pin model is wrong type",type(wire))
        print("added wire",self.wire_ids)
    def remove_wire_model(self,wire):
        if isinstance(wire,Wire) and self.wire_ids is not None:
            if wire.id in self.wire_ids:
                self.wire_ids.remove(wire.id)
                if self.graphics_item and self.graphics_item.parent:
                    self.graphics_item.parent.update_info_display()
        else:
            print("wire model given to pin model is wrong type",type(wire))
        print("removed wire",self.wire_ids,wire.id)
    def to_dict(self) -> dict:
        return {
            'pid': self.pid,
            'number': self.number,
            'gender': self.gender.value,
            'seal': self.seal.value,
            'wire_ids': self.wire_ids,
            'description': self.description,
            'current_rating': self.current_rating
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Pin':
        return cls(
            pid=data['pid'],
            number=data['number'],
            gender=Gender(data['gender']),
            seal=SealType(data['seal']),
            wire_ids=data.get('wire_ids'),
            description=data.get('description'),
            current_rating=data.get('current_rating')
        )

@dataclass
class Wire:
    """Represents a single wire run between two nodes."""
    id: str
    harness_id: str
    type: WireType
    color: CombinedWireColor
    from_node_id: str
    to_node_id: str
    from_pin: Optional[str] = None
    to_pin: Optional[str] = None
    calculated_length_mm: Optional[float] = None
    signal_name: Optional[str] = None
    part_number: Optional[str] = None
    notes: Optional[str] = None
    cross_section:Optional[float] = None
    graphics_item: Optional[any] = None
    length: float = 0.0  # length
    # NEW: List of node IDs that this wire passes through (in order)
    route: List[str] = field(default_factory=list)
    
    # NEW: List of routed graphics items representing this wire
    routed_graphics: List[any] = field(default_factory=list)
    
    def add_route_node(self, node_id: str):
        """Add a node to the wire's route"""
        if node_id not in self.route:
            self.route.append(node_id)
    
    def set_route(self, node_ids: List[str]):
        """Set the complete route for this wire"""
        self.route = node_ids.copy()
    
    def clear_route(self):
        """Clear the wire's route"""
        self.route.clear()
    
    def add_routed_graphics(self, graphics_item):
        """Add a routed graphics item for this wire"""
        if graphics_item not in self.routed_graphics:
            self.routed_graphics.append(graphics_item)
    
    def remove_routed_graphics(self, graphics_item):
        """Remove a routed graphics item"""
        if graphics_item in self.routed_graphics:
            self.routed_graphics.remove(graphics_item)
    
    def clear_routed_graphics(self):
        """Clear all routed graphics items"""
        self.routed_graphics.clear()

    def __str__(self):
        return self.id
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'harness_id': self.harness_id,
            'type': self.type.value,
            'color': self.color.to_dict(),
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'from_pin': self.from_pin,
            'to_pin': self.to_pin,
            'calculated_length_mm': self.calculated_length_mm,
            'signal_name': self.signal_name,
            'part_number': self.part_number,
            'notes': self.notes,
            'cross_section': self.cross_section,
            'route': self.route  # NEW: Save route
        }

    
    @classmethod
    def from_dict(cls, data: dict) -> 'Wire':
        return cls(
            id=data['id'],
            harness_id=data['harness_id'],
            type=WireType(data['type']),
            color=CombinedWireColor(**data['color']),
            from_node_id=data['from_node_id'],
            to_node_id=data['to_node_id'],
            from_pin=data.get('from_pin'),
            to_pin=data.get('to_pin'),
            calculated_length_mm=data.get('calculated_length_mm'),
            signal_name=data.get('signal_name'),
            part_number=data.get('part_number'),
            notes=data.get('notes'),
            cross_section=data.get('cross_section'),
            length=data.get('length'),
            route=data.get('route', [])
        )

@dataclass
class Connector:
    """The primary object, representing a connector housing."""
    id: str
    name: str
    type: ConnectorType
    gender: Gender
    seal: SealType
    series: str = None
    part_number: Optional[str] = None
    manufacturer: Optional[str] = None
    pins: Dict[str, Pin] = field(default_factory=dict)
    position: Tuple[float, float] = (0.0, 0.0)
    description: Optional[str] = None
    rotation: int = 0
    graphics_item: Optional[any] = None
    table_pos: Tuple[float, float] = (25.0, -15.0)  # NEW: Store table position offset
    
    # ... rest of the class ...
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'gender': self.gender.value,
            'seal': self.seal.value,
            'series': self.series,
            'part_number': self.part_number,
            'manufacturer': self.manufacturer,
            'pins': {num: pin.to_dict() for num, pin in self.pins.items()},
            'position': self.position,
            'description': self.description,
            'rotation': self.rotation,
            'table_pos': self.table_pos  # NEW: Save table position
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Connector':
        connector = cls(
            id=data['id'],
            name=data['name'],
            type=ConnectorType(data['type']),
            gender=Gender(data['gender']),
            seal=SealType(data['seal']),
            series=data.get('series'),
            part_number=data.get('part_number'),
            manufacturer=data.get('manufacturer'),
            position=tuple(data.get('position', (0, 0))),
            description=data.get('description'),
            rotation=data.get('rotation', 0),
            table_pos=tuple(data.get('table_pos', (25.0, -15.0)))  # NEW: Load table position
        )
        for pin_num, pin_data in data.get('pins', {}).items():
            connector.pins[pin_num] = Pin.from_dict(pin_data)
        return connector


@dataclass
class Node:
    """A point in the harness where connections happen."""
    id: str
    harness_id: str
    name: str
    type: NodeType
    connector_id: Optional[str] = None
    position: Tuple[float, float] = (0.0, 0.0)
    graphics_item: Optional[any] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'harness_id': self.harness_id,
            'name': self.name,
            'type': self.type.value,
            'connector_id': self.connector_id,
            'position': self.position
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Node':
        return cls(
            id=data['id'],
            harness_id=data['harness_id'],
            name=data['name'],
            type=NodeType(data['type']),
            connector_id=data.get('connector_id'),
            position=tuple(data.get('position', (0, 0)))
        )

@dataclass
class BranchProtection:
    """Defines the protective material applied over a segment."""
    id: str
    type: ProtectionType
    part_number: Optional[str] = None
    diameter_mm: Optional[float] = None
    color: Optional[str] = None
    material: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type.value,
            'part_number': self.part_number,
            'diameter_mm': self.diameter_mm,
            'color': self.color,
            'material': self.material
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BranchProtection':
        return cls(
            id=data['id'],
            type=ProtectionType(data['type']),
            part_number=data.get('part_number'),
            diameter_mm=data.get('diameter_mm'),
            color=data.get('color'),
            material=data.get('material')
        )

@dataclass
class HarnessBranch:
    """A logical grouping of wires that run together."""
    id: str
    harness_id: str
    name: str
    protection_id: Optional[str] = None
    path_points: List[Tuple[float, float]] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)  # List of node IDs on this branch
    wire_ids: List[str] = field(default_factory=list)  # Wires in this branch
    graphics_item: Optional[any] = None
    
    def calculate_length(self) -> float:
        """Calculate total length of the branch."""
        if len(self.path_points) < 2:
            return 0.0
        import math
        total = 0.0
        for i in range(len(self.path_points) - 1):
            dx = self.path_points[i+1][0] - self.path_points[i][0]
            dy = self.path_points[i+1][1] - self.path_points[i][1]
            total += math.sqrt(dx*dx + dy*dy)
        return total
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'harness_id': self.harness_id,
            'name': self.name,
            'protection_id': self.protection_id,
            'path_points': self.path_points,
            'node_ids': self.node_ids,
            'wire_ids': self.wire_ids
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HarnessBranch':
        return cls(
            id=data['id'],
            harness_id=data['harness_id'],
            name=data['name'],
            protection_id=data.get('protection_id'),
            path_points=[tuple(p) for p in data.get('path_points', [])],
            node_ids=data.get('node_ids', []),
            wire_ids=data.get('wire_ids', [])
        )
@dataclass
class Bundle:
    """Represents a bundle in the harness"""
    id: str
    name: str = ""
    start_point: Tuple[float, float] = (0.0, 0.0)
    end_point: Tuple[float, float] = (0.0, 0.0)
    start_node_id: Optional[str] = None
    end_node_id: Optional[str] = None
    specified_length: Optional[float] = None
    length: float = 0.0
    wire_count: int = 0
    wire_ids: List[str] = field(default_factory=list)
    auto_created: bool = False
    graphics_item: Optional[any] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'start_point': self.start_point,
            'end_point': self.end_point,
            'start_node_id': self.start_node_id,
            'end_node_id': self.end_node_id,
            'specified_length': self.specified_length,
            'length': self.length,
            'wire_count': self.wire_count,
            'wire_ids': self.wire_ids,
            'auto_created': self.auto_created
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bundle':
        return cls(
            id=data['id'],
            name=data.get('name', data['id']),
            start_point=tuple(data.get('start_point', (0, 0))),
            end_point=tuple(data.get('end_point', (0, 0))),
            start_node_id=data.get('start_node_id'),
            end_node_id=data.get('end_node_id'),
            specified_length=data.get('specified_length'),
            length=data.get('length', 0.0),
            wire_count=data.get('wire_count', 0),
            wire_ids=data.get('wire_ids', []),
            auto_created=data.get('auto_created', False))

@dataclass
class BranchPoint:
    """Represents a branch point in the harness topology"""
    id: str
    name: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    branch_type: str = "split"  # "split", "merge", "splice"
    node_id: Optional[str] = None  # Reference to topology node
    connected_segments: List[str] = field(default_factory=list)  # IDs of connected segments
    graphics_item: Optional[any] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'branch_type': self.branch_type,
            'node_id': self.node_id,
            'connected_segments': self.connected_segments
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BranchPoint':
        return cls(
            id=data['id'],
            name=data.get('name', data['id']),
            position=tuple(data.get('position', (0, 0))),
            branch_type=data.get('branch_type', 'split'),
            node_id=data.get('node_id'),
            connected_segments=data.get('connected_segments', [])
        )

@dataclass
class WiringHarness:
    _ids = count(0)
    """The top-level object representing the entire harness."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Harness"
    part_number: str = ""
    revision: str = "1.0"
    description: str = ""  # ADD THIS
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    branch_points: Dict[str, BranchPoint] = field(default_factory=dict)  # ADD THIS
    connectors: Dict[str, Connector] = field(default_factory=dict)
    wires: Dict[str, Wire] = field(default_factory=dict)
    bundles: Dict[str, Bundle] = field(default_factory=dict)  # ADD THIS
    branches: Dict[str, HarnessBranch] = field(default_factory=dict)
    protections: Dict[str, BranchProtection] = field(default_factory=dict)
    nodes: Dict[str, Node] = field(default_factory=dict)
    segments: Dict[str, TopologySegment] = field(default_factory=dict)
     
    def add_connector(self, connector: Connector) -> None:
        self.connectors[connector.id] = connector
        self.modified_date = datetime.now()
    
    def remove_connector(self, connector: Connector) -> None:
        del self.connectors[connector.id]
        self.modified_date = datetime.now()
    
    def add_wire(self, wire: Wire) -> None:
        self.wires[wire.id] = wire
        self.modified_date = datetime.now()
    
    def add_bundle(self, bundle: Bundle) -> None:
        """Add a bundle to the harness"""
        self.bundles[bundle.id] = bundle
        self.modified_date = datetime.now()
        
    def add_branch_point(self, branch_point: BranchPoint) -> None:
        """Add a branch point to the harness"""
        self.branch_points[branch_point.id] = branch_point
        self.modified_date = datetime.now()
    
    def remove_branch_point(self, branch_point: BranchPoint) -> None:
        """Remove a branch point from the harness"""
        if branch_point.id in self.branch_points:
            del self.branch_points[branch_point.id]
            self.modified_date = datetime.now()

    def remove_bundle(self, bundle: Bundle) -> None:
        """Remove a bundle from the harness"""
        if bundle.id in self.bundles:
            del self.bundles[bundle.id]
            self.modified_date = datetime.now()
    
    def add_branch(self, branch: HarnessBranch) -> None:
        self.branches[branch.id] = branch
        self.modified_date = datetime.now()
    
    def next_cid(self) -> str:
        return "C" + str(next(self._ids))
    
    def next_bpid(self) -> str:
        """Generate next branch point ID"""
        return "BP" + str(next(self._ids))

    def next_bid(self) -> str:
        """Generate next bundle ID"""
        return "B" + str(next(self._ids))
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'part_number': self.part_number,
            'revision': self.revision,
            'description': self.description,  
            'created_date': self.created_date.isoformat(),
            'modified_date': self.modified_date.isoformat(),
            'branch_points': {k: v.to_dict() for k, v in self.branch_points.items()},  
            'connectors': {k: v.to_dict() for k, v in self.connectors.items()},
            'wires': {k: v.to_dict() for k, v in self.wires.items()},
            'bundles': {k: v.to_dict() for k, v in self.bundles.items()}, 
            'segments': {k: v.to_dict() for k, v in self.segments.items()},
            'branches': {k: v.to_dict() for k, v in self.branches.items()},
            'protections': {k: v.to_dict() for k, v in self.protections.items()},
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WiringHarness':
        harness = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'New Harness'),
            part_number=data.get('part_number', ''),
            revision=data.get('revision', '1.0'),
            description=data.get('description', ''),
            created_date=datetime.fromisoformat(data['created_date']) if 'created_date' in data else datetime.now(),
            modified_date=datetime.fromisoformat(data['modified_date']) if 'modified_date' in data else datetime.now()
        )
        
        for k, v in data.get('connectors', {}).items():
            harness.connectors[k] = Connector.from_dict(v)
 
        for k, v in data.get('segments', {}).items():
            harness.segments[k] = TopologySegment.from_dict(v)

        for k, v in data.get('wires', {}).items():
            harness.wires[k] = Wire.from_dict(v)
        
        for k, v in data.get('bundles', {}).items():  
            harness.bundles[k] = Bundle.from_dict(v)
        
        for k, v in data.get('branches', {}).items():
            harness.branches[k] = HarnessBranch.from_dict(v)
        
        for k, v in data.get('branch_points', {}).items():  
            harness.branch_points[k] = BranchPoint.from_dict(v)

        for k, v in data.get('protections', {}).items():
            harness.protections[k] = BranchProtection.from_dict(v)
        
        for k, v in data.get('nodes', {}).items():
            harness.nodes[k] = Node.from_dict(v)
        harness._update_ids_counter()

        return harness

    def _update_ids_counter(self):
        """Update the _ids counter to be greater than any existing ID numbers"""
        max_num = 0
        
        # Check connector IDs
        for conn_id in self.connectors.keys():
            if conn_id.startswith('C'):
                try:
                    num = int(conn_id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        # Check wire IDs
        for wire_id in self.wires.keys():
            if wire_id.startswith('W'):
                try:
                    num = int(wire_id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        # Check bundle IDs
        for bundle_id in self.bundles.keys():
            if bundle_id.startswith('B'):
                try:
                    num = int(bundle_id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        # Check branch point IDs
        for bp_id in self.branch_points.keys():
            if bp_id.startswith('BP'):
                try:
                    num = int(bp_id[2:])  # Skip 'BP' prefix
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        # Update the counter to max_num + 1
        # Reset the counter and advance it
        self.__class__._ids = count(max_num + 1)
        
        print(f"ID counter updated to start from {max_num + 1}")

