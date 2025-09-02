import os, json
class SendSequenceManager:
    def __init__(self): self.sequences = []; self.current_file_path = None
    def load_from_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f); self.sequences = data if isinstance(data, list) else []
                self.current_file_path = path; return True
        except (json.JSONDecodeError, IOError, FileNotFoundError): self.sequences = []; self.current_file_path = None; return False
    def save_to_file(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.sequences, f, indent=4, ensure_ascii=False)
            self.current_file_path = path; return True
        except IOError: return False
    def save_current_file(self):
        if self.current_file_path: return self.save_to_file(self.current_file_path)
        return False
    def new_set(self): self.sequences = []; self.current_file_path = None
    def get_sequences(self): return self.sequences
    def add_sequence(self, data): self.sequences.append(data); self.save_current_file()
    def edit_sequence(self, index, data):
        if 0 <= index < len(self.sequences): self.sequences[index] = data; self.save_current_file()
    def delete_sequence(self, index):
        if 0 <= index < len(self.sequences): del self.sequences[index]; self.save_current_file()