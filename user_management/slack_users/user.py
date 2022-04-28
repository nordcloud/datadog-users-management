# Copyright 2021 Nordcloud Oy or its affiliates. All Rights Reserved.
class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

    def __str__(self):
        return "{0} {1} {2}".format(self.id, self.name, self.email)
