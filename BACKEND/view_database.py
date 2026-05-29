#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('mfwa_mti.db')
cursor = conn.cursor()

print("\n=== OUTLETS ===")
cursor.execute("SELECT outlets.id, outlet_name, mti_score FROM outlets LEFT JOIN mti_indices ON outlets.id = mti_indices.outlet_id;")
for row in cursor.fetchall():
    print(row)

print("\n=== TOTAL ===")
cursor.execute("SELECT COUNT(*) FROM outlets;")
print(f"Total outlets: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM responses;")
print(f"Total responses: {cursor.fetchone()[0]}")

conn.close()
print("\nDone!")