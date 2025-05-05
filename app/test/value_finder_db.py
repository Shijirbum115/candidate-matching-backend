import pymysql

# === CONFIGURE YOUR DB CONNECTION ===
db_config = {
    "host": "128.199.218.52",
    "user": "for_data_sync",
    "password": "It@gmUDhU_Lq[teXdGk1x0*bX0Z0MTH4",
    "database": "mcs",
    "charset": "utf8mb4"
}

# === SEARCH TERM ===
search_text = "Шалгалтад ирээгүй"

# === CONNECT AND RUN ===
connection = pymysql.connect(**db_config)
cursor = connection.cursor()

try:
    # Step 1: Get all varchar/text columns
    cursor.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND data_type IN ('varchar', 'text', 'mediumtext', 'longtext')
    """, (db_config['database'],))

    columns = cursor.fetchall()
    print(f"🔍 Scanning {len(columns)} text-like columns for exact match...")

    # Step 2: Loop over each column and search for exact match
    for table, column in columns:
        query = f"""
            SELECT `{column}` 
            FROM `{table}` 
            WHERE `{column}` = %s
            LIMIT 10
        """
        try:
            cursor.execute(query, (search_text,))
            results = cursor.fetchall()
            for row in results:
                print(f"{table}.{column} -> {row[0]}")
        except Exception as e:
            print(f"⚠️ Error querying {table}.{column}: {e}")

finally:
    cursor.close()
    connection.close()
