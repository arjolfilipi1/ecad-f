class Net:
    def __init__(self, name):
        self.name = name
        self.pins = set()

class Netlist:
    def __init__(self):
        self.nets = {}

    def connect(self, pin_a, pin_b):
        net_a = self.find_net(pin_a)
        net_b = self.find_net(pin_b)

        if net_a and net_b and net_a != net_b:
            net_a.pins |= net_b.pins
            del self.nets[net_b.name]

        elif net_a:
            net_a.pins.add(pin_b)

        elif net_b:
            net_b.pins.add(pin_a)

        else:
            name = f"NET_{len(self.nets)+1}"
            net = Net(name)
            net.pins.update([pin_a, pin_b])
            self.nets[name] = net

    def find_net(self, pin):
        for net in self.nets.values():
            if pin in net.pins:
                return net
        return None