import os
import sys
from .database import init_database, reset_database, SQLITE_DATABASE_URL
from .models import Conversation, Message

def setup_database():
    try:
        print("Setting up CatBot database...")
        print(f"Database location: {SQLITE_DATABASE_URL}")
        
        # Initialize database tables
        init_database()
        
        print("✅ Database setup completed successfully!")
        print("\nDatabase schema created:")
        print("  - conversations table")
        print("  - messages table")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def reset_all_data():
    """Reset database"""
    try:
        print("⚠️  WARNING: This will delete ALL chat history!")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() == 'yes':
            reset_database()
            print("✅ Database reset completed!")
            return True
        else:
            print("❌ Reset cancelled")
            return False
            
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

def check_database():
    """Check if database exists and is properly set up"""
    try:
        # Extract file path from sqlite URL
        db_file = SQLITE_DATABASE_URL.replace("sqlite:///", "")
        
        if not os.path.exists(db_file):
            print(f"❌ Database file not found: {db_file}")
            return False
        
        from .database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['conversations', 'messages']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print("✅ Database is properly set up")
        print(f"📁 Database file: {db_file}")
        print(f"📊 Tables: {tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    """Run migration script directly"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_database()
        elif command == "reset":
            reset_all_data()
        elif command == "check":
            check_database()
        else:
            print("Unknown command. Use: setup, reset, or check")
    else:
        print("CatBot Database Migration Tool")
        print("Commands:")
        print("  python -m backend.database.migrations setup  - Set up database")
        print("  python -m backend.database.migrations check  - Check database")
        print("  python -m backend.database.migrations reset  - Reset database (deletes all data)") 