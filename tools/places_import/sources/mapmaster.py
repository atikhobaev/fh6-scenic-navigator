from ._snapshot import load_rows


def load_snapshot():
    return load_rows("mapmaster_hidden_cars.json")
