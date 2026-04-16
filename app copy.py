from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import RPi.GPIO as GPIO
import time
import random
import threading

app = Flask(__name__)
CORS(app)

# ------------------------------
# GPIO Setup
# ------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ------------------------------
# Zones (UPDATED)
# ------------------------------
ZONE_PINS = {
    "sb02": 26,
    "sb03": 5,
    "sb04": 6,
    "al_ansar": 12,
    "sb07": 13,
    "sb08": 16,
    "d01": 17,
    "d09": 18,
    "d10": 19,
    
}

# Initialize pins (OFF)
for pin in ZONE_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

# ------------------------------
# Virtual Groups
# ------------------------------
VIRTUAL_ZONE_GROUPS = {
    "super_blocks": [
        "sb02",
        "sb03",
        "sb04",
        "al_ansar",
        "sb07",
        "sb08"
    ],
    "districts": [
        "d01",
        "d09",
        "d10"
    ],
    
}

# ------------------------------
# Idle / Random Mode Config
# ------------------------------
last_activity_time = time.time()
IDLE_TIMEOUT = 120  # 2 minutes
RANDOM_MODE = False

# ------------------------------
# Helpers
# ------------------------------
def resolve_zones(zones):
    resolved = set()
    for zone in zones:
        if zone in VIRTUAL_ZONE_GROUPS:
            resolved.update(VIRTUAL_ZONE_GROUPS[zone])
        else:
            resolved.add(zone)
    return list(resolved)

def set_zone(zone, state):
    zones = resolve_zones([zone])
    for z in zones:
        pin = ZONE_PINS.get(z)
        if pin is not None:
            GPIO.output(pin, GPIO.LOW if state else GPIO.HIGH)

def turn_off_all():
    for z in ZONE_PINS:
        set_zone(z, False)

# ------------------------------
# Random Mode Worker
# ------------------------------
def random_mode_worker():
    global RANDOM_MODE

    while True:
        time.sleep(2)

        idle_time = time.time() - last_activity_time

        if idle_time > IDLE_TIMEOUT:
            RANDOM_MODE = True

        if RANDOM_MODE:
            zone = random.choice(list(ZONE_PINS.keys()))

            print(f"[RANDOM MODE] Switching to: {zone}")

            turn_off_all()
            set_zone(zone, True)

            time.sleep(random.randint(3, 8))

# Start background thread
threading.Thread(target=random_mode_worker, daemon=True).start()

# ------------------------------
# Activity Tracker
# ------------------------------
def update_activity():
    global last_activity_time, RANDOM_MODE
    last_activity_time = time.time()
    RANDOM_MODE = False

# ------------------------------
# API Endpoints
# ------------------------------
@app.route('/status', methods=['GET'])
def get_status():
    update_activity()
    status = {
        zone: "ON" if GPIO.input(pin) == GPIO.LOW else "OFF"
        for zone, pin in ZONE_PINS.items()
    }
    return jsonify(status)

@app.route("/on_zone/<zone>", methods=["POST"])
def on_zone(zone):
    update_activity()
    zone = zone.lower()
    turn_off_all()
    set_zone(zone, True)
    return jsonify({"status": "on", "zone": zone})

@app.route("/off_zone/<zone>", methods=["POST"])
def off_zone(zone):
    update_activity()
    zone = zone.lower()
    turn_off_all()
    return jsonify({"status": "off", "zone": zone})

@app.route("/on_all", methods=["POST"])
def on_all():
    update_activity()
    for zone in ZONE_PINS:
        set_zone(zone, True)
    return jsonify({"status": "all on"})

@app.route("/off_all", methods=["POST"])
def off_all():
    update_activity()
    turn_off_all()
    return jsonify({"status": "all off"})

# ------------------------------
# UI Routes
# ------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# ------------------------------
# Run App
# ------------------------------
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        GPIO.cleanup()
    finally:
        GPIO.cleanup()
