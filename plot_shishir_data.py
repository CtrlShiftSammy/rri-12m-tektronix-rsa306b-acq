import argparse
import csv
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser(
        description="Plot first 3*4096 values of the last CSV column against index."
    )
    parser.add_argument("csv_file", help="Path to input CSV file")
    args = parser.parse_args()

    values = []
    with open(args.csv_file, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                values.append(float(row[-1]))
            except ValueError:
                # skip rows where last column isn't numeric
                continue
            if len(values) >= 3*4096:
                break

    plt.plot(range(len(values)), values)
    plt.xlabel("Index")
    plt.ylabel("Last column value")
    plt.title("First 3*4096 samples vs Index")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
