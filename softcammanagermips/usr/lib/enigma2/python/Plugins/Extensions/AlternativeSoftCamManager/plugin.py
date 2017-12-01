#by Taapat taapat@gmail.com
#code and desing examples from 2boom plugins:
#		Easy Pnel for Pli http://gisclub.tv/index.php?topic=5075.0
#		newcamd.list switcher http://gisclub.tv/index.php?topic=4772.0
#openpli SoftcamSetup 

from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigText, \
	getConfigListEntry
from Components.Console import Console
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.List import List
from Components.ScrollLabel import ScrollLabel
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap

from enigma import eTimer
from os import path, remove 

config.plugins.AltSoftcam = ConfigSubsection()
config.plugins.AltSoftcam.actcam = ConfigText(default = "none")
config.plugins.AltSoftcam.camconfig = ConfigText(default = "/var/keys",
	visible_width = 100, fixed_size = False)
config.plugins.AltSoftcam.camdir = ConfigText(default = "/usr/bin/cam",
	visible_width = 100, fixed_size = False)
AltSoftcamConfigError = False
if not path.isdir(config.plugins.AltSoftcam.camconfig.value):
	config.plugins.AltSoftcam.camconfig.value = "none"
	AltSoftcamConfigError = True
if not path.isdir(config.plugins.AltSoftcam.camdir.value):
	config.plugins.AltSoftcam.camdir.value = "none"
	AltSoftcamConfigError = True

def getcamcmd(cam):
	cam = cam.lower()
	if "oscam" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -bc " + \
			config.plugins.AltSoftcam.camconfig.value + "/"
	elif "wicard" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -d -c " + \
			config.plugins.AltSoftcam.camconfig.value + "/wicardd.conf"
	elif "camd3" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " " + \
			config.plugins.AltSoftcam.camconfig.value + "/camd3.config"
	elif "mbox" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " " + \
			config.plugins.AltSoftcam.camconfig.value + "/mbox.cfg"
	elif "mpcs" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -c " + \
			config.plugins.AltSoftcam.camconfig.value
	elif "newcs" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -C " + \
			config.plugins.AltSoftcam.camconfig.value + "/newcs.conf"
	elif "vizcam" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -b -c " + \
			config.plugins.AltSoftcam.camconfig.value + "/"
	elif "rucam" in cam:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam + " -b"
	else:
		return config.plugins.AltSoftcam.camdir.value + "/" + cam

class AltCamManager(Screen):
	skin = """
<screen position="center,center" size="630,370" title="SoftCam manager">
	<eLabel position="5,0" size="620,2" backgroundColor="#aaaaaa" />
<widget source="list" render="Listbox" position="10,15" size="340,300" \
	scrollbarMode="showOnDemand">
	<convert type="TemplatedMultiContent">
		{"template": [
			MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (51, 40), png = 1), 
			MultiContentEntryText(pos = (65, 10), size = (275, 40), font=0, \
				flags = RT_HALIGN_LEFT, text = 0), 
			MultiContentEntryText(pos = (5, 25), size = (51, 16), font=1, \
				flags = RT_HALIGN_CENTER, text = 2), 
				],
	"fonts": [gFont("Regular", 26),gFont("Regular", 12)],
	"itemHeight": 50
	}
	</convert>
	</widget>
	<eLabel halign="center" position="390,10" size="210,35" font="Regular;20" \
		text="Ecm info" transparent="1" />
	<widget name="status" position="360,50" size="320,300" font="Regular;16" \
		halign="left" noWrap="1" />
	<eLabel position="12,358" size="148,2" backgroundColor="#00ff2525" />
	<eLabel position="165,358" size="148,2" backgroundColor="#00389416" />
	<eLabel position="318,358" size="148,2" backgroundColor="#00baa329" />
	<eLabel position="471,358" size="148,2" backgroundColor="#006565ff" />
	<widget name="key_red" position="12,328" zPosition="2" size="148,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
	<widget name="key_green" position="165,328" zPosition="2" size="148,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
	<widget name="key_yellow" position="318,328" zPosition="2" size="148,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
	<widget name="key_blue" position="471,328" zPosition="2" size="148,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.Console = Console()
		self["key_red"] = Label(_("Stop"))
		self["key_green"] = Label(_("Start"))
		self["key_yellow"] = Label(_("Restart"))
		self["key_blue"] = Label(_("Setup"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"green": self.start,
				"red": self.stop,
				"yellow": self.restart,
				"blue": self.setup
			}, -1)
		self["status"] = ScrollLabel()
		self["list"] = List([])
		self.actcam = config.plugins.AltSoftcam.actcam.value
		self.camstartcmd = ""
		self.CreateInfo()
		self.Timer = eTimer()
		self.Timer.callback.append(self.listecminfo)
		self.Timer.start(1000*4, False)

	def CreateInfo(self):
		global AltSoftcamConfigError
		if not AltSoftcamConfigError:
			self.StartCreateCamlist()
			self.listecminfo()

	def listecminfo(self):
		listecm = ""
		try:
			ecmfiles = open("/tmp/ecm.info", "r")
			for line in ecmfiles:
				if line[32:]:
					linebreak = line[23:].find(' ') + 23
					listecm += line[0:linebreak]
					listecm += "\n" + line[linebreak + 1:]
				else:
					listecm += line
			self["status"].setText(listecm)
			ecmfiles.close()
		except:
			self["status"].setText("")

	def StartCreateCamlist(self):
		self.Console.ePopen("ls %s" % config.plugins.AltSoftcam.camdir.value,
			self.CamListStart)

	def CamListStart(self, result, retval, extra_args):
		if not result.startswith('ls: '):
			self.softcamlist = result
			self.Console.ePopen("chmod 755 %s/*" %
				config.plugins.AltSoftcam.camdir.value)
			self.Console.ePopen("pidof %s" % self.actcam, self.CamActive)

	def CamActive(self, result, retval, extra_args):
		if result.strip():
			self.CreateCamList()
		else:
			for line in self.softcamlist.splitlines():
				if line != self.actcam:
					self.Console.ePopen("pidof %s" % line, self.CamActiveFromList, line)
			self.Console.ePopen("echo 1", self.CamActiveFromList, "none")

	def CamActiveFromList(self, result, retval, extra_args):
		if result.strip():
			self.actcam = extra_args
			self.CreateCamList()

	def CreateCamList(self):
		self.list = []
		try:
			test = self.actcam
		except:
			self.actcam = "none"
		if self.actcam != "none":
			try:
				softpng = LoadPixmap(cached=True,
					path=resolveFilename(SCOPE_PLUGINS,
					"Extensions/AlternativeSoftCamManager/images/actcam.png"))
				self.list.append((self.actcam, softpng, self.checkcam(self.actcam)))
			except:
				pass
		try:
			softpng = LoadPixmap(cached=True,
				path=resolveFilename(SCOPE_PLUGINS,
				"Extensions/AlternativeSoftCamManager/images/defcam.png"))
			for line in self.softcamlist.splitlines():
				if line != self.actcam:
					self.list.append((line, softpng, self.checkcam(line)))
		except:
			pass
		self["list"].setList(self.list)

	def checkcam (self, cam):
		cam = cam.lower()
		if "oscam" in cam:
			return "Oscam"
		elif "mgcamd" in cam:
			return "Mgcamd"
		elif "wicard" in cam:
			return "Wicard"
		elif "camd3" in cam:
			return "Camd3"
		elif "mcas" in cam:
			return "Mcas"
		elif "cccam" in cam:
			return "CCcam"
		elif "gbox" in cam:
			return "Gbox"
		elif "ufs910camd" in cam:
			return "Ufs910"
		elif "incubuscamd" in cam:
			return "Incubus"
		elif "mpcs" in cam:
			return "Mpcs"
		elif "mbox" in cam:
			return "Mbox"
		elif "newcs" in cam:
			return "Newcs"
		elif "vizcam" in cam:
			return "Vizcam"
		elif "sh4cam" in cam:
			return "Sh4CAM"
		elif "rucam" in cam:
			return "Rucam"
		else:
			return cam[0:6]

	def start(self):
		global AltSoftcamConfigError
		if not AltSoftcamConfigError:
			self.camstart = self["list"].getCurrent()[0]
			if self.camstart != self.actcam:
				print "[Alternative SoftCam Manager] Start SoftCam"
				self.camstartcmd = getcamcmd(self.camstart)
				msg = _("Starting %s") % self.camstart
				self.mbox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
				self.activityTimer = eTimer()
				self.activityTimer.timeout.get().append(self.Stopping)
				self.activityTimer.start(100, False)

	def stop(self):
		if self.actcam != "none":
			self.Console.ePopen("killall -9 %s" % self.actcam)
			print "[Alternative SoftCam Manager] stop ", self.actcam
			try:
				remove("/tmp/ecm.info")
			except:
				pass
			msg  = _("Stopping %s") % self.actcam
			self.actcam = "none"
			self.mbox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
			self.activityTimer = eTimer()
			self.activityTimer.timeout.get().append(self.closestop)
			self.activityTimer.start(1000, False)

	def closestop(self):
		self.activityTimer.stop()
		self.mbox.close()
		self.CreateInfo()

	def restart(self):
		global AltSoftcamConfigError
		if not AltSoftcamConfigError:
			print "[Alternative SoftCam Manager] restart SoftCam"
			self.camstart = self.actcam
			if self.camstartcmd == "":
				self.camstartcmd = getcamcmd(self.camstart)
			msg  = _("Restarting %s") % self.actcam
			self.mbox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
			self.activityTimer = eTimer()
			self.activityTimer.timeout.get().append(self.Stopping)
			self.activityTimer.start(100, False)

	def Stopping(self):
		self.activityTimer.stop()
		self.Console.ePopen("killall -9 %s" % self.actcam)
		print "[Alternative SoftCam Manager] stopping ", self.actcam
		try:
			remove("/tmp/ecm.info")
		except:
			pass
		self.actcam = self.camstart
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		if service:
			self.session.nav.stopService()
		self.Console.ePopen(self.camstartcmd)
		print "[Alternative SoftCam Manager] ", self.camstartcmd
		if self.mbox:
			self.mbox.close()
		if service:
			self.session.nav.playService(service)
		self.CreateInfo()

	def ok(self):
		if self["list"].getCurrent()[0] != self.actcam:
			self.start()
		else:
			self.restart()

	def cancel(self):
		if config.plugins.AltSoftcam.actcam.value != self.actcam:
			config.plugins.AltSoftcam.actcam.value = self.actcam
			config.plugins.AltSoftcam.actcam.save()
		self.close()

	def setup(self):
		self.session.openWithCallback(self.CreateInfo, ConfigEdit)

class ConfigEdit(Screen, ConfigListScreen):
	skin = """
<screen name="ConfigEdit" position="center,center" size="500,200" \
	title="SoftCam path configuration">
	<eLabel position="5,0" size="490,2" backgroundColor="#aaaaaa" />
<widget name="config" position="30,20" size="460,50" zPosition="1" \
	scrollbarMode="showOnDemand" />
	<eLabel position="85,180" size="166,2" backgroundColor="#00ff2525" />
	<eLabel position="255,180" size="166,2" backgroundColor="#00389416" />
	<widget name="key_red" position="85,150" zPosition="2" size="170,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
	<widget name="key_green" position="255,150" zPosition="2" size="170,30" \
		valign="center" halign="center" font="Regular;22" transparent="1" />
</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("Ok"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.ok,
				"green": self.ok,
				"red": self.close,
			}, -2)
		ConfigListScreen.__init__(self, [], session)
		self.camconfigold = config.plugins.AltSoftcam.camconfig.value
		self.camdirold = config.plugins.AltSoftcam.camdir.value
		self.list = []
		self.list.append(getConfigListEntry(_("SoftCam config directory"),
			config.plugins.AltSoftcam.camconfig))
		self.list.append(getConfigListEntry(_("SoftCam directory"),
			config.plugins.AltSoftcam.camdir))
		self["config"].list = self.list

	def ok(self):
		if self.camconfigold != config.plugins.AltSoftcam.camconfig.value \
			or self.camdirold != config.plugins.AltSoftcam.camdir.value:
			self.session.openWithCallback(self.updateConfig, MessageBox,
				(_("Are you sure you want to save this configuration?\n\n")))
		elif not path.isdir(self.camconfigold) or not path.isdir(self.camdirold):
			self.updateConfig(True)
		else:
			self.close()

	def updateConfig(self, ret = False):
		if ret == True:
			global AltSoftcamConfigError
			msg = [ ]
			if not path.isdir(config.plugins.AltSoftcam.camconfig.value):
				msg.append("%s " % config.plugins.AltSoftcam.camconfig.value)
			if not path.isdir(config.plugins.AltSoftcam.camdir.value):
				msg.append("%s " % config.plugins.AltSoftcam.camdir.value)
			if msg == [ ]:
				if config.plugins.AltSoftcam.camconfig.value[-1] == "/":
					config.plugins.AltSoftcam.camconfig.value = \
						config.plugins.AltSoftcam.camconfig.value[:-1]
				if config.plugins.AltSoftcam.camdir.value[-1] == "/":
					config.plugins.AltSoftcam.camdir.value = \
						config.plugins.AltSoftcam.camdir.value[:-1]
				config.plugins.AltSoftcam.camconfig.save()
				config.plugins.AltSoftcam.camdir.save()
				AltSoftcamConfigError = False
				self.close()
			else:
				AltSoftcamConfigError = True
				self.mbox = self.session.open(MessageBox,
					_("Directory %s does not exist!\nPlease set the correct directorypath!")
					% msg, MessageBox.TYPE_INFO, timeout = 5 )

def main(session, **kwargs):
	session.open(AltCamManager)

def StartCam(reason, **kwargs):
	global AltSoftcamConfigError
	if not AltSoftcamConfigError \
		and config.plugins.AltSoftcam.actcam.value != "none":
		if reason == 0: # Enigma start
			try:
				cmd = getcamcmd(config.plugins.AltSoftcam.actcam.value)
				Console().ePopen(cmd)
				print "[Alternative SoftCam Manager] ", cmd
			except:
				pass
		elif reason == 1: # Enigma stop
			try:
				Console().ePopen("killall -9 %s" %
					config.plugins.AltSoftcam.actcam.value)
				print "[Alternative SoftCam Manager] stopping ", \
					config.plugins.AltSoftcam.actcam.value
			except:
				pass

def Plugins(**kwargs):
	return [
	PluginDescriptor(name = _("Alternative SoftCam Manager"),
		description = _("Start, stop, restart SoftCams, change settings."),
		where = [ PluginDescriptor.WHERE_PLUGINMENU,
		PluginDescriptor.WHERE_EXTENSIONSMENU ],
		icon = "images/softcam.png", fnc = main),
	PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART,
		needsRestart = True, fnc = StartCam)]
