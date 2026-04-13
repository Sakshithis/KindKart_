import sqlite3

def upgrade():
    try:
        conn = sqlite3.connect('c:/KindKart/KindKart_/kindkart.db')
        conn.execute('ALTER TABLE message ADD COLUMN attachment_url VARCHAR(255)')
    except Exception as e:
        print(f"attachment_url error: {e}")
    try:
        conn.execute('ALTER TABLE message ADD COLUMN is_read BOOLEAN DEFAULT 0')
    except Exception as e:
        print(f"is_read error: {e}")
    try:
        conn.commit()
        print("Columns updated successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade()
