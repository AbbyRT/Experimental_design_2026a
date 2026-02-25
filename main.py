# ============================================
# MAX6675 TEMPERATURE ACQUISITION SYSTEM
# ============================================
# : Sampling frequency: 1 Hz
# : Total samples: 180 (3 minutos)
# : Allows pause (p), resume (r), quit (q)
# : Output format: CSV -> time_seconds, temperature_C
# : Data stored in memory, written at end
# : Unique filename based on ticks_ms
# ============================================

# ===============================
# IMPORT MODULES
# ===============================
from machine import Pin
import time
import sys
import select

# ===============================
# SPI PIN CONFIGURATION
# ===============================
sck = Pin(18, Pin.OUT) #clock
cs = Pin(5, Pin.OUT) # chip select
so = Pin(19, Pin.IN) #data from the sensor

# ==================================
# MAX6675 DRIVER CLASS
# ==================================
"""
Temperature reading by applying a bit banging process:
the SCK pin indicates when it's the time to send the data, it syncronizes the data transmission
CS (chip select): as the name states, it indicates when the communication must be enabled.
SO: it sends the data corresponding to the temperature reading

"""
class MAX6675:
    def __init__(self, sck, cs, so):
        self.sck = sck
        self.cs = cs
        self.so = so
        self.cs.value(1)

    def read(self):
        self.cs.value(0) #chip activation
        time.sleep_us(10)
        value = 0
        for _ in range(16): #a bit is read by pulse, there are 16 pulses, 12 belongs to the temp reading
            self.sck.value(1)
            value <<= 1
            if self.so.value():
                value |= 1
            self.sck.value(0)
        self.cs.value(1)
        if value & 0x4:
            return None
        value >>= 3
        return value * 0.25 #data transformation, each unit represents 0.25 C (conversor resolution)

# ===============================
# SENSOR INITIALIZATION
# ===============================
sensor = MAX6675(sck, cs, so)

# ===============================
# EXPERIMENT CONFIGURATION
# ===============================
SAMPLING_INTERVAL = 1       # : segundos entre muestras
TOTAL_SAMPLES     = 180     # : 1 Hz x 180 s = 3 minutos

# ===============================
# HELPER FUNCTION: NON-BLOCKING KEY CHECK
# ===============================
def read_keyboard():
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.readline().strip()
    return None

# ===============================
# HELPER FUNCTION: WRITE CSV
# ===============================
def write_csv(filename, data):
    with open(filename, 'w') as f:
        f.write("time_seconds,temperature_C\n")
        for elapsed, temp in data:
            f.write("{:.3f},{:.2f}\n".format(elapsed, temp))
    print("CSV guardado como:", filename)

# ===============================
# DATA ACQUISITION LOOP
# ===============================

# : Nombre unico basado en tiempo de arranque
csv_filename = "temp_{}.csv".format(time.ticks_ms())

# : Lista en memoria para acumular muestras
data = []

print("START")
print("Duracion: 3 minutos ({} muestras a 1 Hz)".format(TOTAL_SAMPLES))
print("Archivo de salida: {}".format(csv_filename))
print("Presiona 'p' para pausar, 'r' para reanudar, 'q' para salir")

t0          = time.ticks_ms()
paused_time = 0
pause_start = None
paused      = False
sample_count = 0

try:
    while sample_count < TOTAL_SAMPLES:

        # : Verificar teclado
        key = read_keyboard()
        if key == 'p' and not paused:
            paused = True
            pause_start = time.ticks_ms()
            print("PAUSED")
        elif key == 'r' and paused:
            paused = False
            pause_end = time.ticks_ms()
            paused_time += time.ticks_diff(pause_end, pause_start)
            print("RESUMED")
        elif key == 'q':
            print("STOP")
            break

        # : Adquisicion solo si no esta pausado
        if not paused:
            t_now = time.ticks_ms()
            elapsed_time = (
                time.ticks_diff(t_now, t0) - paused_time
            ) / 1000.0

            temp = sensor.read()
            if temp is not None:
                print("{:.3f},{:.2f}".format(elapsed_time, temp))
                data.append((elapsed_time, temp))   # : Guarda en memoria
                sample_count += 1
            else:
                print("ERROR: Thermocouple disconnected")

            time.sleep(SAMPLING_INTERVAL)
        else:
            time.sleep(0.1)

    print("STOP")

except KeyboardInterrupt:
    print("STOP")

# ===============================
# ESCRITURA DEL CSV AL FINALIZAR
# ===============================
if data:
    write_csv(csv_filename, data)
else:

    print("Sin datos para guardar.")
