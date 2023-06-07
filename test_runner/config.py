# TODO use config file
from os import makedirs
import pathlib

BASE_DIR = pathlib.Path(__file__).parent.resolve().joinpath("data")
makedirs(BASE_DIR,exist_ok=True)
print(BASE_DIR)

RUN_DIR= BASE_DIR.joinpath("runs")
makedirs(RUN_DIR, exist_ok=True)

