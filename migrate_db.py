import sqlite3

def upgrade():
    try:
        conn = sqlite3.connect('c:/KindKart/KindKart_/kindkart.db')
        conn.execute('ALTER TABLE message ADD COLUMN attachment_url VARCHAR(255)')
        conn.commit()
        print("Column added successfully!")
    except Exception as e:
        if 'duplicate column name' in str(e).lower():
            print("Column already exists. All good!")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade()
