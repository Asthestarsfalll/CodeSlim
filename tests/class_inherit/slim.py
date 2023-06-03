from codeslim import AutoSlim

AutoSlim("./module3/c.py", "./target/").mode(AutoSlim.SegmentLevel).merge_class(
    AutoSlim.Eliminate
).generate()
