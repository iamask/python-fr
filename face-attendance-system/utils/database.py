"""
Attendance Database Module
Handles CSV-based attendance tracking with duplicate prevention.

CSV Format:
Name,Date,Time,Status
John Doe,2024-01-15,09:30:45,Present
Jane Smith,2024-01-15,09:32:10,Present

Anti-Spam Logic:
- Check if (Name, Date) combination exists before writing
- If exists: Skip (person already marked today)
- If new: Append record with current timestamp
"""

import os
import csv
from datetime import datetime


class AttendanceDB:
    """
    Manages attendance records in CSV format.
    
    Provides:
    - Daily duplicate detection (anti-spam)
    - Attendance statistics
    - CSV persistence
    - Human-readable format for easy verification
    
    Attributes:
        filepath: Path to CSV file
        today: Current date string (YYYY-MM-DD)
        fieldnames: CSV column headers
    """
    
    def __init__(self, filepath='data/attendance.csv'):
        """
        Initialize database connection.
        
        Args:
            filepath: Path to attendance CSV file
        """
        self.filepath = filepath
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.fieldnames = ['Name', 'Date', 'Time', 'Status']
        
        # Ensure file exists with headers
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """
        Create CSV file with headers if it doesn't exist.
        Idempotent - safe to call multiple times.
        """
        if not os.path.exists(self.filepath):
            # Create directory if needed
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            
            # Create file with headers
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
    
    def is_already_marked(self, name, date=None):
        """
        Check if person already marked attendance for given date.
        
        This is the ANTI-SPAM mechanism that prevents duplicate entries.
        A person can only be marked once per day.
        
        Args:
            name: Person's name
            date: Date to check (default: today)
            
        Returns:
            bool: True if already marked, False if new entry
        """
        check_date = date or self.today
        
        if not os.path.exists(self.filepath):
            return False
        
        with open(self.filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if row['Name'] == name and row['Date'] == check_date:
                    return True
        
        return False
    
    def mark_attendance(self, name):
        """
        Mark attendance for a person.
        
        Flow:
        1. Check if already marked today (anti-spam)
        2. If new: Append to CSV with timestamp
        3. If duplicate: Return already-marked message
        
        Args:
            name: Person's name
            
        Returns:
            tuple: (success: bool, message: str)
                   success=True if new entry added
                   success=False if duplicate or error
        """
        # Update today's date
        self.today = datetime.now().strftime("%Y-%m-%d")
        
        # Check for duplicate
        if self.is_already_marked(name):
            return False, f"{name} already marked present today"
        
        # Get current time
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Append to CSV
        try:
            with open(self.filepath, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow({
                    'Name': name,
                    'Date': self.today,
                    'Time': current_time,
                    'Status': 'Present'
                })
            
            return True, f"✅ Attendance marked for {name} at {current_time}"
            
        except Exception as e:
            return False, f"❌ Error saving attendance: {e}"
    
    def get_today_stats(self):
        """
        Get attendance statistics for today.
        
        Returns:
            dict: {
                'date': today's date,
                'count': number of entries today,
                'names': list of names marked today
            }
        """
        self.today = datetime.now().strftime("%Y-%m-%d")
        count = 0
        names = []
        
        if not os.path.exists(self.filepath):
            return {'date': self.today, 'count': 0, 'names': []}
        
        with open(self.filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if row['Date'] == self.today:
                    count += 1
                    names.append(row['Name'])
        
        return {
            'date': self.today,
            'count': count,
            'names': names
        }
    
    def get_all_records(self, date=None):
        """
        Get all attendance records, optionally filtered by date.
        
        Args:
            date: Filter by date (YYYY-MM-DD), None for all
            
        Returns:
            list: List of attendance record dictionaries
        """
        records = []
        
        if not os.path.exists(self.filepath):
            return records
        
        with open(self.filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if date is None or row['Date'] == date:
                    records.append(dict(row))
        
        return records
    
    def get_registered_today_count(self):
        """Get count of today's attendance (convenience method)."""
        return self.get_today_stats()['count']
    
    def export_to_csv(self, output_path):
        """
        Export attendance to another CSV file.
        Useful for backing up or sharing data.
        
        Args:
            output_path: Destination file path
        """
        records = self.get_all_records()
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(records)
