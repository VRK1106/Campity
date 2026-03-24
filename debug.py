print("1. Start Debug", flush=True)
import sys
print(f"Python {sys.version}", flush=True)

try:
    print("2. Import Flask", flush=True)
    from flask import Flask
    print("3. Flask OK", flush=True)

    print("4. Import SQLAlchemy", flush=True)
    from flask_sqlalchemy import SQLAlchemy
    print("5. SQLAlchemy OK", flush=True)

    print("6. Import Redis", flush=True)
    import redis
    print("7. Redis OK", flush=True)

    print("8. Import SocketIO", flush=True)
    from flask_socketio import SocketIO
    print("9. SocketIO OK", flush=True)

except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("10. End Debug", flush=True)
