import subprocess
import sys
import time

services = [
    "inventory_service.py",
    "payment_service.py",
    "order_service.py"
]

processes = []

try:
    for service in services:
        p = subprocess.Popen([sys.executable, service])
        processes.append(p)
        print(f"Started {service}")
        time.sleep(1)

    print("\nAll services are running:")
    print("Inventory: http://127.0.0.1:5001")
    print("Payment:   http://127.0.0.1:5002")
    print("Orders:    http://127.0.0.1:5000")
    print("\nPress CTRL + C to stop all services.\n")

    for p in processes:
        p.wait()

except KeyboardInterrupt:
    print("\nStopping services...")

    for p in processes:
        p.terminate()

    print("All services stopped.")