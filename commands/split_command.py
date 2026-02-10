def split_segment(segment, split_pos):
    p1 = segment.line().p1()
    p2 = segment.line().p2()

    # Remove old segment
    scene.removeItem(segment)

    # Create junction
    junction = JunctionItem(split_pos)
    scene.addItem(junction)

    # Create two new segments
    s1 = WireSegmentItem(p1, split_pos, segment.net)
    s2 = WireSegmentItem(split_pos, p2, segment.net)

    scene.addItem(s1)
    scene.addItem(s2)

