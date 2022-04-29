# Copyright 2021 Nordcloud Oy or its affiliates. All Rights Reserved.
from typing import NamedTuple


class User(NamedTuple):
    id: str
    name: str
    email: str
