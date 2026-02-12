#model/models
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, NamedTuple
import math
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
    def __init__(self, base_color: str, stripe_color: Optional[str] = None):
        base_color = 'SW' if not base_color else base_color
        self.base_color = base_color.upper()
        self.stripe_color = stripe_color.upper() if stripe_color else None
        
        if not GermanWireColors.is_valid_color(self.base_color):
            raise ValueError(f"Invalid base color code: {base_color}")
        
        if self.stripe_color and not GermanWireColors.is_valid_color(self.stripe_color):
            raise ValueError(f"Invalid stripe color code: {stripe_color}")
    
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
    """Types of connectors used in the automotive industry."""
    JT = "Junior Timer"         # Metri-Pack 150/280
    GT = "General Timer"        # Metri-Pack 480/630
    MT = "Micro Timer"          # Metri-Pack 56/110
    DTM = "Deutsch DTM"
    DTP = "Deutsch DTP"
    SQUARE = "Square Connector" # e.g., Sumitomo MT
    OTHER = "Other"

class SealType(Enum):
    """Common seal types for connectors and pins."""
    UNSEALED = "Unsealed"
    CONNECTOR_SEALED = "Connector Sealed"
    FULLY_SEALED = "Fully Sealed"

class Gender(Enum):
    """Gender of a connector or pin."""
    MALE = "Male"
    FEMALE = "Female"

class WireType(Enum):
    """Standard automotive wire types (by cross-sectional area)."""
    FLRY_B_0_35 = "FLRY-B 0.35 mm²"
    FLRY_B_0_5 = "FLRY-B 0.5 mm²"
    FLRY_B_0_75 = "FLRY-B 0.75 mm²"
    FLRY_B_1_0 = "FLRY-B 1.0 mm²"
    FLRY_B_1_5 = "FLRY-B 1.5 mm²"
    FLRY_B_2_5 = "FLRY-B 2.5 mm²"

class ProtectionType(Enum):
    """Types of protective sleeving and conduit."""
    BRAIDED_SLEEVE = "Braided Sleeve (PET)"
    SHRINK_TUBING = "Heat Shrink Tubing"
    SPIRAL_WRAP = "Spiral Wrap"
    FLEX_CONDUIT = "Flexible Conduit"
    TAPE = "Friction Tape"
    FABRIC_TAPE = "Fabric Tape"

class NodeType(Enum):
    """Types of nodes in the harness."""
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
class Pin:
    """Represents a single cavity/pin within a connector."""
    number: str
    gender: Gender
    seal: SealType
    wire_id: Optional[str] = None  # The ID of the wire connected to this pin
@dataclass
class Wire:
    """Represents a single wire run between two nodes."""
    id: str
    harness_id: str
    type: WireType
    color: CombinedWireColor  # Changed from str to CombinedWireColor
    from_node_id: str
    to_node_id: str
    from_pin: Optional[str] = None
    to_pin: Optional[str] = None
    calculated_length_mm: Optional[float] = None

    @property
    def color_code(self) -> str:
        """Get the color code string (e.g., 'SW' or 'SW/GE')"""
        return self.color.code

    @property
    def color_display_name(self) -> str:
        """Get the display name for the color"""
        return self.color.display_name

    @property
    def rgb_color(self) -> Tuple[int, int, int]:
        """Get RGB values for the wire color"""
        return self.color.rgb

    @property
    def stripe_rgb(self) -> Optional[Tuple[int, int, int]]:
        """Get RGB values for the stripe color if exists"""
        return self.color.get_stripe_rgb()

    @property
    def hex_color(self) -> str:
        """Get hex color code"""
        return self.color.hex_code
@dataclass
class Connector:
    """The primary object, representing a connector housing."""
    id: str
    name: str
    type: ConnectorType
    gender: Gender
    seal: SealType
    wires: List[Wire] = None
    part_number: Optional[str] = None
    pins: Dict[str, Pin] = field(default_factory=dict)
    position: Tuple[float, float] = (0.0, 0.0)

@dataclass
class BranchProtection:
    """Defines the protective material applied over a segment of the harness."""
    id: str
    type: ProtectionType
    part_number: Optional[str] = None
    diameter: Optional[float] = None  # in mm

@dataclass
class Node:
    """A point in the harness where connections happen. Can be a Connector, Splice, Ground, etc."""
    id: str
    harness_id: str
    name: str
    type: NodeType
    connector_id: Optional[str] = None  # Only if type is CONNECTOR
    position: Tuple[float, float] = (0.0, 0.0)



@dataclass
class BranchSegment:
    """
    A logical grouping of wires that run together and share the same protection.
    A branch runs between two or more nodes (connectors, splices).
    """
    id: str
    harness_id: str
    name: str
    protection_id: Optional[str] = None
    path_points: List[Tuple[float, float]] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)  # List of node IDs on this branch

@dataclass
class HarnessBranch:
    """
    A logical grouping of wires that run together and share the same protection.
    A branch runs between two or more nodes (connectors, splices).
    """
    id: str
    harness_id: str
    name: str
    protection_id: Optional[str] = None
    path_points: List[Tuple[float, float]] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)  # List of node IDs on this branch
    
    def calculate_length(self) -> float:
        """Calculates the total length of the branch by summing the distance between path points."""
        if len(self.path_points) < 2:
            return 0.0

        total_length = 0.0
        prev_point = self.path_points[0]
        
        for current_point in self.path_points[1:]:
            dx = current_point[0] - prev_point[0]
            dy = current_point[1] - prev_point[1]
            total_length += math.sqrt(dx * dx + dy * dy)
            prev_point = current_point

        return total_length

    def find_distance_to_node(self, node_id: str, nodes_dict: Dict[str, Node]) -> Optional[float]:
        """
        Finds the distance along the branch path to a specific node.
        This is a simplified version that finds the closest path point.
        """
        node = nodes_dict.get(node_id)
        
        if node is None:
            return None

        # Find the closest path point to the node's position
        min_distance = float('inf')
        closest_point_index = 0

        for i, point in enumerate(self.path_points):
            dx = point[0] - node.position[0]
            dy = point[1] - node.position[1]
            distance = math.sqrt(dx * dx + dy * dy)
            if distance < min_distance:
                min_distance = distance
                closest_point_index = i

        # Calculate length from start to the closest point
        if closest_point_index == 0:
            return 0.0

        length_to_node = 0.0
        for i in range(closest_point_index):
            p1 = self.path_points[i]
            p2 = self.path_points[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length_to_node += math.sqrt(dx * dx + dy * dy)

        return length_to_node

    def calculate_wire_length(self, wire: Wire, nodes_dict: Dict[str, Node]) -> Optional[float]:
        """
        Calculates the approximate length of a wire within this branch.
        This assumes the wire runs the entire length of the branch.
        For more accuracy, you'd need to know where it enters/exits.
        """
        if wire.from_node_id not in self.nodes or wire.to_node_id not in self.nodes:
            return None  # Wire doesn't run through this branch

        # Simple approximation: use total branch length
        # For better accuracy, calculate distance between entry and exit points
        return self.calculate_length()

@dataclass
class WiringHarness:
    """The top-level object representing the entire harness."""
    name: str
    part_number: str
    connectors: Dict[str, Connector] = field(default_factory=dict)
    wires: Dict[str, Wire] = field(default_factory=dict)
    branches: Dict[str, HarnessBranch] = field(default_factory=dict)
    protections: Dict[str, BranchProtection] = field(default_factory=dict)
    nodes: Dict[str, Node] = field(default_factory=dict)
    fasteners: Dict[str, Fastener] = field(default_factory=dict)
    fastener_types: Dict[str, FastenerType] = field(default_factory=dict)
    def get_connector_pins(self, connector_id: str) -> Dict[str, Pin]:
        """Get all pins for a specific connector."""
        connector = self.connectors.get(connector_id)
        return connector.pins if connector else {}

    def get_wires_for_connector(self, connector_id: str) -> List[Wire]:
        """Get all wires connected to a specific connector."""
        wires = []
        for wire in self.wires.values():
            # Check if wire is connected to this connector via its nodes
            from_node = self.nodes.get(wire.from_node_id)
            to_node = self.nodes.get(wire.to_node_id)
            
            if (from_node and from_node.connector_id == connector_id) or \
               (to_node and to_node.connector_id == connector_id):
                wires.append(wire)
        return wires

    def calculate_branch_wire_lengths(self) -> Dict[str, float]:
        """Calculate and update wire lengths based on branch paths."""
        wire_lengths = {}
        
        for wire_id, wire in self.wires.items():
            total_length = 0.0
            
            # Find all branches this wire passes through
            for branch in self.branches.values():
                branch_length = branch.calculate_wire_length(wire, self.nodes)
                if branch_length is not None:
                    total_length += branch_length
            
            # Add service loop allowance (e.g., 10%)
            total_length *= 1.1
            wire.calculated_length_mm = total_length
            wire_lengths[wire_id] = total_length
        
        return wire_lengths

    def generate_pinout_report(self, connector_id: str) -> List[Dict]:
        """Generate a pinout report for a specific connector."""
        report = []
        connector = self.connectors.get(connector_id)
        
        if not connector:
            return report

        for pin_number, pin in connector.pins.items():
            connected_wire = None
            if pin.wire_id:
                connected_wire = self.wires.get(pin.wire_id)
            
            report.append({
                'pin_number': pin_number,
                'gender': pin.gender.value,
                'seal': pin.seal.value,
                'wire_id': pin.wire_id,
                'wire_type': connected_wire.type.value if connected_wire else 'N/A',
                'wire_color': connected_wire.color if connected_wire else 'N/A',
                'connected_to': self._get_connection_point(connected_wire, connector_id) if connected_wire else 'N/A'
            })
        
        return report

    def _get_connection_point(self, wire: Wire, current_connector_id: str) -> str:
        """Helper method to determine where a wire connects to."""
        from_node = self.nodes.get(wire.from_node_id)
        to_node = self.nodes.get(wire.to_node_id)
        
        if from_node and from_node.connector_id == current_connector_id:
            # This wire goes from current connector to another node
            if to_node:
                if to_node.connector_id:
                    return f"Connector {to_node.connector_id}, Pin {wire.to_pin}"
                else:
                    return f"{to_node.type.value} {to_node.name}"
        
        elif to_node and to_node.connector_id == current_connector_id:
            # This wire comes from another node to current connector
            if from_node:
                if from_node.connector_id:
                    return f"Connector {from_node.connector_id}, Pin {wire.from_pin}"
                else:
                    return f"{from_node.type.value} {from_node.name}"
        
        return "Unknown"

    def generate_bom(self) -> Dict[str, Dict]:
        """Generate a Bill of Materials for the harness."""
        bom = {
            'connectors': {},
            'wires': {},
            'protections': {},
            'total_wire_length': 0.0
        }
        
        # Count connectors
        for connector in self.connectors.values():
            bom['connectors'][connector.id] = {
                'type': connector.type.value,
                'part_number': connector.part_number,
                'quantity': 1
            }
        
        # Calculate wire quantities and total length
        wire_types = {}
        for wire in self.wires.values():
            wire_type_key = f"{wire.type.value}_{wire.color}"
            if wire_type_key not in wire_types:
                wire_types[wire_type_key] = {
                    'type': wire.type.value,
                    'color': wire.color,
                    'length_mm': 0.0,
                    'count': 0
                }
            
            wire_types[wire_type_key]['length_mm'] += wire.calculated_length_mm or 0
            wire_types[wire_type_key]['count'] += 1
            bom['total_wire_length'] += wire.calculated_length_mm or 0
        
        bom['wires'] = wire_types
        
        # Count protections
        for protection in self.protections.values():
            bom['protections'][protection.id] = {
                'type': protection.type.value,
                'part_number': protection.part_number,
                'diameter_mm': protection.diameter_mm,
                'quantity': 0  # Will be calculated based on branch usage
            }
        
        # Calculate protection lengths based on branches
        for branch in self.branches.values():
            if branch.protection_id and branch.protection_id in bom['protections']:
                branch_length = branch.calculate_length()
                bom['protections'][branch.protection_id]['quantity'] += branch_length
        
        return bom
    def get_fasteners_for_branch(self, branch_id: str) -> List[Fastener]:
        """Get all fasteners attached to a specific branch."""
        return [f for f in self.fasteners.values() if f.branch_id == branch_id]
    
    def get_fasteners_for_node(self, node_id: str) -> List[Fastener]:
        """Get all fasteners attached to a specific node."""
        return [f for f in self.fasteners.values() if f.node_id == node_id]
    
    def generate_fastener_bom(self) -> Dict[str, Dict]:
        """Generate Bill of Materials for fasteners."""
        fastener_bom = {}
        
        for fastener in self.fasteners.values():
            key = f"{fastener.part_number}_{fastener.size or ''}"
            if key not in fastener_bom:
                fastener_bom[key] = {
                    'part_number': fastener.part_number,
                    'type': fastener.type.name,
                    'size': fastener.size,
                    'quantity': 0,
                    'torque': fastener.torque_nm,
                    'locations': []
                }
            
            fastener_bom[key]['quantity'] += fastener.quantity
            if fastener.branch_id:
                fastener_bom[key]['locations'].append(f"Branch {fastener.branch_id}")
            elif fastener.node_id:
                fastener_bom[key]['locations'].append(f"Node {fastener.node_id}")
        
        return fastener_bom
# Example usage and testing
if __name__ == "__main__":
    # Create a simple test harness
    test_harness = WiringHarness(
        name="Test Harness",
        part_number="TEST-001",
        connectors={},
        wires={},
        branches={},
        protections={},
        nodes={}
    )
    
    print(f"Created test harness: {test_harness.name}")