import os, json
class ReceiveSequenceManager:
    def __init__(self): self.rules = []; self.current_file_path = None
    def load_from_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f); self.rules = data if isinstance(data, list) else []
                self.current_file_path = path; return True
        except (json.JSONDecodeError, IOError, FileNotFoundError): self.rules = []; self.current_file_path = None; return False
    def save_to_file(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.rules, f, indent=4, ensure_ascii=False)
            self.current_file_path = path; return True
        except IOError: return False
    def save_current_file(self):
        if self.current_file_path: return self.save_to_file(self.current_file_path)
        return False
    def new_set(self): self.rules = []; self.current_file_path = None
    def get_rules(self): return self.rules
    def add_rule(self, rule): self.rules.append(rule); self.save_current_file()
    def edit_rule(self, index, rule):
        if 0 <= index < len(self.rules): self.rules[index] = rule; self.save_current_file()
    def delete_rule(self, index):
        if 0 <= index < len(self.rules): del self.rules[index]; self.save_current_file()
    def check_and_get_response(self, data: bytes):
        for rule in self.rules:
            if not rule.get('enabled', True): continue
            trigger = rule.get('trigger', ''); mode = rule.get('mode', 'ASCII')
            if self._match(data, trigger, mode): return {'sequence': rule.get('response', ''), 'mode': rule.get('response_mode', 'ASCII')}
        return None
    def _match(self, received_data: bytes, trigger: str, mode: str) -> bool:
        if not trigger: return False
        try:
            if mode == 'ASCII': return trigger == received_data.decode('utf-8', errors='replace').strip()
            elif mode == 'HEX': hex_str = trigger.replace('0x', '').replace('0X', '').replace(',', ' '); return bytes([int(b, 16) for b in hex_str.split() if b]) in received_data
        except ValueError: return False
        return False