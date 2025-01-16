
# crc_utils.py

def crc16(data, offset, length):
    """
    Calculate CRC-16 ARC for the given data.

    Parameters:
        data (bytes): The data to calculate CRC for.
        offset (int): The starting point in the data for CRC calculation.
        length (int): The number of bytes to include in the CRC calculation.

    Returns:
        int: The CRC-16 ARC checksum value.
    """
    if data is None or offset < 0 or offset > len(data) - 1 or offset + length > len(data):
        return 0
    crc = 0x0000
    for i in range(offset, offset + length):
        crc ^= data[i]
        for j in range(8):
            if (crc & 0x0001) > 0:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return crc

def reverse_bytes(crc_value):
    """
    Reverse the byte order of a CRC value.

    Parameters:
        crc_value (int): The CRC value to reverse.

    Returns:
        str: The reversed CRC value as a string.
    """
    hex_str = f"{crc_value:04X}"
    reversed_hex_str = hex_str[2:] + hex_str[:2]
    return reversed_hex_str

def verify_crc(data, received_crc):
    """
    Verify the CRC-16 ARC checksum of the given data.

    Parameters:
        data (bytes): The data to verify (excluding CRC bytes).
        received_crc (str): The received CRC in hexadecimal format.

    Returns:
        bool: True if the CRC matches, False otherwise.
    """
    calculated_crc = crc16(data, 0, len(data))
    calculated_crc_reversed = reverse_bytes(calculated_crc)
    return calculated_crc_reversed.upper() == received_crc.upper()

