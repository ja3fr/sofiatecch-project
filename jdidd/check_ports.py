import serial.tools.list_ports

# On récupère la liste de tous les ports COM connectés
available_ports = serial.tools.list_ports.comports()

if not available_ports:
    print("Aucun port COM n'a été trouvé.")
    print("Assurez-vous que votre appareil (carte Arduino, adaptateur USB-Série, etc.) est bien branché.")
else:
    print("Voici la liste des ports COM disponibles :")
    print("-" * 40)
    for port in available_ports:
        # port.device est le nom du port (ex: "COM3")
        # port.description est une description plus complète
        # port.hwid contient des informations sur l'identifiant matériel
        print(f"Port: {port.device}")
        print(f"  Description: {port.description}")
        print(f"  ID Matériel: {port.hwid}")
        print("-" * 40)