import csv
from typing import Type, List, Any, Optional, Callable, Dict, Iterable
from pydantic import BaseModel
from pathlib import Path


class CSVDatabase:
    def __init__(self, model: Type[BaseModel], file_path: str):
        self.model = model
        self.file_path = Path(file_path)

        # Ensure the file exists and has the correct headers
        if not self.file_path.exists() or self._is_empty():
            self._create_file()

    def _is_empty(self) -> bool:
        return self.file_path.stat().st_size == 0

    def _create_file(self):
        with self.file_path.open(mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.model.model_fields.keys())
            writer.writeheader()

    def _check_and_create_header(self):
        if self._is_empty():
            self._create_file()

    def insert_row(self, data: dict):
        # Ensure the header exists before inserting
        self._check_and_create_header()

        # Ensure the data matches the model's fields
        validated_data = self.model(**data)
        with self.file_path.open(mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.model.model_fields.keys())
            writer.writerow(validated_data.model_dump())

    def update_row(self, key_field: str, key_value: Any, updated_data: dict):
        rows = self.get_all_rows()
        updated = False

        for row in rows:
            if row[key_field] == key_value:
                for key, value in updated_data.items():
                    if key in row:
                        row[key] = value
                updated = True
                break

        if updated:
            self._write_all_rows(rows)

    def delete_row(self, key_field: str, key_value: Any):
        rows = self.get_all_rows()
        rows = [row for row in rows if row[key_field] != key_value]
        self._write_all_rows(rows)

    def get_all_rows(self) -> List[dict]:
        with self.file_path.open(mode='r', newline='') as file:
            reader = csv.DictReader(file)
            return list(reader)

    def _write_all_rows(self, rows: List[Dict[str, str]]):
        """Writes all rows to the CSV file with the specified fieldnames."""
        # Access fieldnames correctly, depending on whether __fields__ is a dict or property
        fieldnames = list(self.model.model_fields.keys()) if isinstance(self.model.model_fields, dict) else list(
            self.model.model_fields.keys())

        with self.file_path.open(mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def get_first_row_by_key(self, key_field: str, key_value: Any) -> Optional[Dict[str, str]]:
        """Retrieve the first row that matches the specified key."""
        with self.file_path.open(mode='r', newline='') as file:
            reader: Iterable[Dict[str, str]] = csv.DictReader(file)  # Explicit type hint for reader
            for row in reader:
                if row.get(key_field) == str(key_value):  # Convert key_value to string to match CSV string data
                    return row
        return None

    def get_rows_by_condition(self, condition: Callable[[Dict[str, str]], bool]) -> List[Dict[str, str]]:
        """
        Retrieve rows that satisfy the provided condition.

        Args:
            condition (Callable[[Dict[str, str]], bool]): A function that takes a row (dict)
                                                          and returns True if the row meets the condition,
                                                          False otherwise.

        Returns:
            List[Dict[str, str]]: A list of rows that meet the condition.
        """
        matched_rows: List[Dict[str, str]] = []

        with self.file_path.open(mode='r', newline='') as file:
            reader: Iterable[Dict[str, str]] = csv.DictReader(file)  # Explicit type hint for reader
            for row in reader:
                if condition(row):
                    matched_rows.append(row)

        return matched_rows

    def get_unprocessed_rows(self) -> List[Dict[str, str]]:
        """Retrieve all rows where 'processed' is False."""
        unprocessed_rows: List[Dict[str, str]] = []

        with self.file_path.open(mode='r', newline='') as file:
            reader: Iterable[Dict[str, str]] = csv.DictReader(file)  # Explicitly hint the type for clarity
            for row in reader:
                if row.get('processed', '').strip().lower() == 'false':
                    unprocessed_rows.append(row)

        return unprocessed_rows

    def get_last_row(self) -> Optional[dict]:
        """Retrieve the last row in the CSV file."""
        with self.file_path.open(mode='r', newline='') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            return rows[-1] if rows else None

    def get_last_row_by_condition(self, condition: Callable[[Dict[str, str]], bool]) -> Optional[dict]:
        """
        Retrieve the last row that matches the specified condition.

        Args:
            condition (Callable[[Dict[str, str]], bool]): A function that takes a row (dict) as input
                                                          and returns True if the row matches the condition,
                                                          otherwise False.

        Returns:
            Optional[dict]: The last row that matches the condition, or None if no match is found.
        """
        with self.file_path.open(mode='r', newline='') as file:
            reader = csv.DictReader(file)
            rows = list(reader)  # Load all rows into memory

            # Iterate in reverse to find the last matching row based on the physical order
        for row in reversed(rows):
            if condition(row):
                return row
        return None

    def get_last_n_rows(self, n: int) -> List[Dict[str, str]]:
        """
        Retrieve the last n rows in the CSV file.

        Args:
            n (int): The number of rows to retrieve from the end of the file.

        Returns:
            List[Dict[str, str]]: A list of the last n rows.
        """
        with self.file_path.open(mode='r', newline='') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            return rows[-n:] if rows else []
