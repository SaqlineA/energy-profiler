import random
import time
from datetime import datetime
import csv
from pathlib import Path
# Day 1: Simulates power readings for three household appliances.


class Appliance:
    def __init__(self,name, typical_watts):
        self.name = name
        self.typical_watts = typical_watts
        self.is_on= False

    def turn_on(self):
        self.is_on= True


    def turn_off(self):
        self.is_on = False



    def read_power(self):
        if not self.is_on:
         return 0


        variation = random.uniform(-2, 2)
        return self.typical_watts + variation

# Save beside this script, even when running it from another folder.
CSV_PATH = Path(__file__).resolve().parent / "power_readings.csv"


def run_simulation(output_path=CSV_PATH):
    lamp = Appliance("Lamp", 10)
    refrigerator = Appliance("Refrigerator", 150)
    microwave = Appliance("Microwave", 1200)

    lamp.turn_on()
    refrigerator.turn_on()

    # "w" replaces the previous run. "with" closes the file automatically.
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([
            "Timestamp", "Second", "Total Power (Watts)",
            "Lamp Power (Watts)", "Microwave Power (Watts)",
            "Refrigerator Power (Watts)",
        ])

        for second in range(30):
            if second == 10:
                microwave.turn_on()
            if second == 15:
                microwave.turn_off()

            # Take each reading once, then use it for both printing and saving.
            lamp_watts = round(lamp.read_power(), 2)
            microwave_watts = round(microwave.read_power(), 2)
            refrigerator_watts = round(refrigerator.read_power(), 2)
            total_watts = round(lamp_watts + microwave_watts + refrigerator_watts, 2)
            timestamp = datetime.now().isoformat(timespec="seconds")

            print(
                f"{timestamp} | Second {second}: "
                f"Lamp = {lamp_watts:.2f} W | "
                f"Refrigerator = {refrigerator_watts:.2f} W | "
                f"Microwave = {microwave_watts:.2f} W | "
                f"Total = {total_watts:.2f} W"
            )

            writer.writerow([
                timestamp, second, total_watts,
                lamp_watts, microwave_watts, refrigerator_watts,
            ])
            # Make each new row available to readers immediately.
            csv_file.flush()
            time.sleep(1)

    print(f"Saved 30 readings to {output_path}")


# Run when launched directly; importing this file only defines the code.
if __name__ == "__main__":
    run_simulation()
