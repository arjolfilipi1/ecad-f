import pandas as pd

def load_from_excel(path, scene, netlist):
    connectors_df = pd.read_excel(path, sheet_name="connectors")
    wires_df = pd.read_excel(path, sheet_name="wires")

    connectors = {}

    for _, row in connectors_df.iterrows():
        c = ConnectorItem(row.id, row.x, row.y, row.pins)
        scene.addItem(c)
        connectors[row.id] = c

    for _, row in wires_df.iterrows():
        c1 = connectors[row.from_connector]
        c2 = connectors[row.to_connector]

        p1 = c1.pins[row.from_pin - 1]
        p2 = c2.pins[row.to_pin - 1]

        w = WireItem(row.id, p1, p2)
        scene.addItem(w)

        netlist.connect(p1, p2)