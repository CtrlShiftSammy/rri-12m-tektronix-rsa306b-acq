import pyvisa

rm = pyvisa.ResourceManager('@py')
resources = rm.list_resources()

# Print all found resources
print("Found resources:")
for res in resources:
    print(res)

# Find USB-TMC device
tek_device = [res for res in resources if 'INSTR' in res][0]
inst = rm.open_resource(tek_device)

print(inst.query('*IDN?'))  # Should return Tektronix identification
