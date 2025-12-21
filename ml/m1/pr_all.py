import subprocess
import sys
import time

def main():
    for week in range(1, 16):
        subprocess.run(["python", "predict_upcoming.py", "2025", str(week)])
        time.sleep(1)

if __name__ == "__main__":
    main()
