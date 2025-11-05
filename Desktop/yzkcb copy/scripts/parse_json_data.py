import os
import json
from typing import List, Dict, Any

JSON_DATA_DIR = os.path.join('data', 'json_data')
OUTPUT_FILE = os.path.join('data', 'processed', 'parsed_json_data.jsonl')

def parse_json_files(directory: str) -> List[Dict[str, Any]]:
    parsed_records = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # Flatten or extract relevant fields as needed
                    if isinstance(data, dict):
                        data['__source_file__'] = filename
                        # Extract display name from nested metadata if available
                        if 'metadata' in data and isinstance(data['metadata'], dict):
                            if 'filename' in data['metadata']:
                                data['__display_name__'] = data['metadata']['filename']
                        parsed_records.append(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                item['__source_file__'] = filename
                                # Extract display name from nested metadata if available
                                if 'metadata' in item and isinstance(item['metadata'], dict):
                                    if 'filename' in item['metadata']:
                                        item['__display_name__'] = item['metadata']['filename']
                                parsed_records.append(item)
                except Exception as e:
                    print(f"Error parsing {filename}: {e}")
    return parsed_records

def save_as_jsonl(records: List[Dict[str, Any]], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

def main():
    records = parse_json_files(JSON_DATA_DIR)
    print(f"Parsed {len(records)} records from JSON files.")
    save_as_jsonl(records, OUTPUT_FILE)
    print(f"Saved parsed records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
