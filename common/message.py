import json

class Message:
    def __init__(self, type, data):
        self.type = type
        self.data = data

    def to_json(self):
        return json.dumps({"type": self.type, "data": self.data})

    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)
        return Message(data["type"], data["data"])