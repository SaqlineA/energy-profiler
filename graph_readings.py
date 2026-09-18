import csv
from pathlib import Path
import matplotlib.pyplot as plt

times = []
total_watts = []

csv_path = Path(__file__).resolve().parent / "power_readings.csv"

with open(csv_path, "r", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:
        times.append(int(row["Second"]))
        total_watts.append(float(row["Total Power (Watts)"]))

#print(times)
#print(total_watts)

threshold = 50

for index in range(1, len(total_watts)):
    previous = total_watts[index - 1]
    current = total_watts[index]
    change = current - previous

    if abs(change) > threshold:
        event_size = abs(change)

        if 1100 <= event_size <= 1300:
            appliance = "Microwave"
        else:
            appliance = "Unknown appliance"

        if change > 0:
            state = "ON"
        else:
            state = "OFF"

        print(
            f"{appliance} turned {state} at second {times[index]} "
            f"({event_size:.2f} watt change)"
        )

plt.plot(times, total_watts, marker="o")

plt.xlabel("Time (seconds)")
plt.ylabel("Power (watts)")
plt.title("Household Power Usage")
plt.grid(True)


plt.tight_layout()
plt.show()
