# validate_serial.py
import serial

COM_PORT = "COM5"  # Instrument port location
TIMEOUT = 1
CHECK_COMMAND = "*IDN?\n"  # Terminate with newline

# Open connection
serial_connection = serial.Serial(
    port=COM_PORT,
    timeout=TIMEOUT,
    write_timeout=TIMEOUT,
)
serial_connection.write(CHECK_COMMAND.encode())  # Send command
response = serial_connection.readline().decode()  # read response
serial_connection.close()  # Close connection
print(response)