"""
Console Output Service
Provides console-like output that can be displayed in chat/web interface
"""
from datetime import datetime
from typing import List, Dict, Any
import json

class ConsoleOutput:
    def __init__(self):
        self.messages = []
        self.max_messages = 100  # Keep last 100 messages
    
    def log(self, message: str, level: str = "INFO", data: Dict = None):
        """Add a log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'data': data
        }
        self.messages.append(entry)
        
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Also print to console for debugging
        print(f"[{timestamp}] {level}: {message}")
        if data:
            print(f"    Data: {json.dumps(data, indent=2, default=str)}")
    
    def info(self, message: str, data: Dict = None):
        """Log info message"""
        self.log(message, "INFO", data)
    
    def success(self, message: str, data: Dict = None):
        """Log success message"""
        self.log(message, "SUCCESS", data)
    
    def warning(self, message: str, data: Dict = None):
        """Log warning message"""
        self.log(message, "WARNING", data)
    
    def error(self, message: str, data: Dict = None):
        """Log error message"""
        self.log(message, "ERROR", data)
    
    def get_recent_messages(self, count: int = 20) -> List[Dict]:
        """Get recent messages"""
        return self.messages[-count:] if self.messages else []
    
    def get_all_messages(self) -> List[Dict]:
        """Get all messages"""
        return self.messages
    
    def clear(self):
        """Clear all messages"""
        self.messages = []
    
    def format_for_display(self, count: int = 20) -> str:
        """Format recent messages for display"""
        recent = self.get_recent_messages(count)
        if not recent:
            return "No console output yet."
        
        output = []
        for msg in recent:
            line = f"[{msg['timestamp']}] {msg['level']}: {msg['message']}"
            if msg.get('data'):
                line += f"\n    → {json.dumps(msg['data'], indent=4, default=str)}"
            output.append(line)
        
        return "\n".join(output)

# Global console instance
console = ConsoleOutput()

def get_console_output(count: int = 20) -> str:
    """Get formatted console output"""
    return console.format_for_display(count)

def clear_console():
    """Clear console output"""
    console.clear()