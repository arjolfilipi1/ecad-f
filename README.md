

# **ECAD – Electrical Harness Design & Forming Board Platform**

A modular **Python / PyQt5-based ECAD system** for electrical wiring harness design, connector database management, and topology-driven routing.

This project is architected to evolve toward **1:1 scale harness visualization and forming board generation** for manufacturing applications.

## Overview

ECAD consists of two primary subsystems:

- Connector Database Manager

- Harness & Topology Editor

The application separates:

* Logical electrical connections (nets & wires)

* Physical harness topology (nodes, segments, branches)

* Connector geometry & cavity definitions

* Visualization layer (graphics scene)

This layered architecture enables scalable growth toward full manufacturing output.

# Core Modules

## **Database Layer**

* `connector_db.py` – Connector library management (SQLite backend)

* `project_db.py` – Project save/load handling

##  **Model Layer**

* `models.py` – Core data models

* `netlist.py` – Electrical connection logic

* `topology_manager.py` – Graph-based harness topology engine

## **Graphics Layer**

* `schematic_view.py` – Main interactive view

* `connector_item.py` – Connector graphics representation

* `wire_item.py` – Wire rendering logic

* `segment_item.py` – Harness segment visualization

* `topology_item.py` – Topology node/branch visualization

## **Utilities**

* `auto_route.py` – Routing logic

* `excel_import.py` – Wire list import (Excel/CSV)

* `settings_manager.py` – Application settings

## **Applications**

* `connector_manager.py` – Connector database GUI

* `p2.py` – Main harness editor application

## Key Capabilities

**Connector Database Management**

- [x] SQLite-backed connector library

- [ ]  Manufacturer / series filtering

- [ ] Cavity coordinate definition (X/Y geometry)

- [ ]   DXF file attachment support

- [ ] Metadata management (gender, seal, housing color, datasheet, notes)

## Harness Editor

* Interactive connector placement

* Pin-level wiring

* Graph-based topology routing

* Branch creation

* Segment-based harness modeling

* Object tree structure

* Undo / Redo

* Selection management

* Visualization modes

## Topology Engine

The harness is modeled as a **graph structure**:

* Nodes → Connectors or branch points

* Segments → Physical harness paths

* Wires → Logical electrical connections routed across segments

This abstraction enables:

* Shared trunk routing

* Multi-branch harness modeling

* Physical separation from electrical logic

* Future length calculation and bundle grouping

## Excel / CSV Wire Import

* Import .xlsx, .xls, .csv

* Wire-only import

* Optional automatic routing

* Topology-assisted branch creation

## Architecture Philosophy

The system is designed around **separation of concerns**:
<table>
<thead>
<tr>
<th>Layer</th>
<th>Responsibility</th>
</tr>
</thead>
<tbody>
<tr>
<td>Database</td>
<td>Persistent connector & project storage</td>
</tr>
<tr>
<td>Model</td>
<td>Electrical and topology logic</td>
</tr>
<tr>
<td>Graphics</td>
<td>Scene rendering & user interaction</td>
</tr>
<tr>
<td>Routing</td>
<td>Wire path calculation</td>
</tr>
<tr>
<td>Import</td>
<td>External data ingestion</td>
</tr>
</tbody>
</table>

This structure allows controlled expansion toward manufacturing-grade features.

## Installation

**Requirements**

* Python 3.9+

* PyQt5
```
pip install PyQt5
```
Optional (Excel support):
```
pip install pandas openpyxl
```

## Running the Applications

***Connector Database Manager***
```
python connector_manager.py
```
**Harness Editor**
```
python p2.py
```
## Development Status

**Implemented**

* Connector library system

* Graph-based topology manager

* Segment visualization

* Wire rendering

* Excel import

* Basic auto-routing

* Project file framework

**Planned**

* DXF geometry parsing

* True 1:1 scale rendering

* Forming board layout engine

* Wire length calculation

* Bundle grouping

* Manufacturing documentation export


## Strategic Direction

The long-term objective of ECAD is to transition from schematic-level harness modeling to:

* ✅ 1:1 scale harness visualization

* ✅ Forming board generation

* ✅ Manufacturing-ready output

* ✅ Production workflow integration

The current topology and geometric architecture are built to support this evolution.

## Vision

ECAD aims to provide a streamlined path from:

* **Electrical Data → Harness Topology → Physical Layout → Forming Board**

Bridging the gap between schematic design and manufacturing execution.

