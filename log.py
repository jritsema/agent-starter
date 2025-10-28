import logging
import json


class JSONFormatter(logging.Formatter):
    def format(self, record):
        if 'request=' in record.getMessage():
            msg = record.getMessage()
            if 'request=<' in msg and '}>' in msg:
                start = msg.find('request=<') + 9
                end = msg.rfind('}>')
                try:
                    request_dict = eval(msg[start:end+1])
                    formatted_json = json.dumps(request_dict, indent=2)
                    record.msg = msg[:start-9] + f"request=\n{formatted_json}"
                except:
                    pass
        return super().format(record)
