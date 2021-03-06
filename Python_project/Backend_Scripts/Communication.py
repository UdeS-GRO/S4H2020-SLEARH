import sys
import glob
import serial
import serial.tools.list_ports
import time
import json
import threading


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = list(serial.tools.list_ports.comports())
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = list(serial.tools.list_ports.comports())
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
        

    result = []
    for port in ports:
        if sys.platform.startswith('win'):
            if "Arduino" in port[1]:
                result.append(port[0])
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            if "ACM0" in port[1]:
                result.append(port[0])
        elif sys.platform.startswith('darwin'):
            # TODO: Make darwin platform working with serial ports verification
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

    return result


class Communication:

    def __init__(self):
        self.__stream__ = {}

        ## @public Communication attribute, Boolean that define if the private thread should run
        #
        self.should_run = True
        self.__port_name__ = None
        self.__port__ = None
        self._ui_adress = None
        self.__private_thread__ = threading.Thread(target=self.__communication_thread__)
        self.__private_thread__.setDaemon(True)

    ##Method that stores the UI adress in a pointer
    #@param adress Actual UI adress
    #
    def set_ui_adress(self, adress):
        self._ui_adress = adress

    ##Method that starts the Communication's private thread
    #
    def start_thread(self):
        self.__private_thread__.start()

    ##Method that ends the Communitaion's private thread
    #
    def end_thread(self):
        self.should_run = False
        self.__private_thread__.join()
        print("Communication thread joined")

    ##Method that update the communication stream to the Arduino
    #@param command_value String Letter to be exectued in ASCII
    #@param purpose Current purpose of the application
    #@param time_on_letter Time to wait on this letter before executing another one
    #
    def update_stream(self, command_value, purpose, time_on_letter):
        self.__stream__ = {
            "command": command_value,
            "purpose": purpose,
            "time": time_on_letter
        }

    ##Method that read the communication stream sent by the Arduino
    #
    def read_stream(self):
        try:
            if self.__port__ is not None:
                encoded_message = self.__port__.readline().decode("utf-8")
                try:
                    encoded_message = encoded_message.split(":")
                    first_part_encoded_message = encoded_message[0].split('"')
                    second_part_encoded_message = encoded_message[1].split('}')
                    dict_encoded_message = {first_part_encoded_message[1]: second_part_encoded_message[0]}
                    message = json.dumps(dict_encoded_message)
                    incoming_message = json.loads(message)
                    return incoming_message["com_state"]
                except IndexError as e:
                    print("")
                    return "none"
            else:
                return "none"
        except serial.SerialException or FileNotFoundError:
            self.connect_port()
            return self.read_stream()

    ##Method that send the uptaded communication stream to the Arduino
    #
    def send_stream(self):
        encoded_message = json.dumps(self.__stream__)

        try:
            print(str(encoded_message) + " on port " + str(self.__port__.name))
        except:
            print(str(encoded_message) + " on port None")

        try:
            if self.__port__ is not None:
                self.__port__.write(bytes(str(encoded_message), "utf-8"))
                print("Write success")
            else:
                print("Write failed, no connection")
        except serial.SerialException or FileNotFoundError or AttributeError as e:
            print("Could not send, because: " + e + ".")

    ##Method that tries to find an active Arduino communication port
    #
    def find_port(self):
        all_port = serial_ports()
        if len(all_port) < 1:
            if self.__port__ is not None:
                print("No Arduino found !")
                self.__port_name__ = None
                self.__port__ = None
            return False

        elif len(all_port) > 1:
            if self.__port__ is None or str(self.__port__.name) != str(all_port[0]):
                print("More than one Arduino found, using first at: " + all_port[0])
                self.__port_name__ = all_port[0]
        else:
            if self.__port__ is None or not str(self.__port__.name) == str(all_port[0]):
                print("Arduino found at: " + all_port[0])
                self.__port_name__ = all_port[0]

        if self.__port__ is None and self.__port_name__ is not None:
            self.connect_port()
        return True

    ##Method that  tries to connect to the Arduino Communication port
    #
    def connect_port(self):
        try:
            self.__port__ = serial.Serial(self.__port_name__, baudrate=9600)
        except serial.SerialException or FileNotFoundError:
            self.find_port()
            self.connect_port()
        print("Connected to " + str(self.__port__.name))

    #Communication private thread to keep the connection status up to date
    #
    def __communication_thread__(self):
        was_connected = None
        while self.should_run:

            if self.find_port():
                if self.__port__.isOpen():
                    if not was_connected:
                        self._ui_adress.change_connected_state(True)
                        self._ui_adress.change_hand_ready_state(True)
                    else:
                        pass
                    was_connected = True
                else:
                    self._ui_adress.change_connected_state(False)
                    was_connected = False

            else:
                self._ui_adress.change_connected_state(False)
                self._ui_adress.change_hand_ready_state(False)
                was_connected = False
                print("Exist: False")

            time.sleep(0.5)


Instance = Communication()
