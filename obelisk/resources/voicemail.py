from twisted.web.resource import Resource
from twisted.web.util import redirectTo
from datetime import datetime
import time
import os

from obelisk import session

from obelisk.model import Model
from obelisk.asterisk.model import SipPeer, VoiceMailMessage
from obelisk.tools import html

from obelisk.templates import print_template

class VoiceMailResource(Resource):
    def __init__(self):
	Resource.__init__(self)

    def render_POST(self, request):
	logged = session.get_user(request)
	if not logged:
		return redirectTo("/", request)

	ext = logged.voip_id

	parts = request.path.split("/")
	if len(parts) > 3:
		action = parts[2]
		msg_id = parts[3]
		if action == 'delete':
			ext = self.delete_voicemail(request, logged, msg_id)
	
	return redirectTo("/voicemail/"+ext, request)

    def delete_voicemail(self, request, logged, msg_id):
	model = Model()
	msg = model.query(VoiceMailMessage).filter_by(msg_id=msg_id).first()
	mb_user = msg.mailboxuser
	if msg and msg.recording and (mb_user == logged.voip_id or logged.admin):
		number = msg.msgnum
		msgdir = msg.dir
		model.session.delete(msg)
		model.session.commit()
		# reorder other messages in the folder
		msgs = model.query(VoiceMailMessage).filter_by(mailboxuser=mb_user)
		for amsg in msgs:
			if amsg.msgnum > number and amsg.dir == msgdir:
				amsg.msgnum -= 1
		model.session.commit()
		return mb_user
	return logged.voip_id

    def render_GET(self, request):
	logged = session.get_user(request)
	if not logged:
		return redirectTo("/", request)

	parts = request.path.split("/")
	if len(parts) > 3 and parts[2] == 'message':
		msg_id = parts[3]
		return self.render_voice_message(request, logged, msg_id)
	if len(parts) > 2 and logged.admin:
		user_ext = parts[2]
	else:
		user_ext = logged.voip_id

	request.setHeader('Cache-Control', 'no-cache, must-revalidate') # http1.1
	request.setHeader('Pragma', 'no-cache') # http1.0
	res = self.render_mailbox(user_ext)
	return print_template('content-pbx-lorea', {'content': res})

    def render_voice_message(self, request, logged, msg_id):
	model = Model()
	msg = model.query(VoiceMailMessage).filter_by(msg_id=msg_id).first()
	if msg and msg.recording and (msg.mailboxuser == logged.voip_id): # no admin here:
		request.setHeader('Content-Description', 'File Transfer')
		request.setHeader('Content-Type', 'application/octet-stream')
		request.setHeader('Content-Disposition', 'attachment; filename=recording-'+msg_id+'-.ogg')
		request.setHeader('Content-Transfer-Encoding', 'binary')
		#request.setHeader('Expires', '0')
		request.setHeader('Content-Length', len(msg.recording))
		return msg.recording
	return "no access"

    def render_mailbox(self, user_ext):
	output = "<h1>Correo de voz</h1>\n"
	model = Model()
	model.session.commit() # refresh session
	all_messages = model.query(VoiceMailMessage).filter_by(mailboxuser=user_ext)
	folders = set()
	for message in all_messages:
		folders.add(message.dir)
	folders = list(folders)
	folders.sort()
	for folder in folders:
		result = []
		messages = model.query(VoiceMailMessage).filter_by(mailboxuser=user_ext, dir=folder)
		output += "<h2>"+os.path.basename(folder)+"</h2>\n"
		for message in messages:
			if message.msg_id:
				audio = html.format_audio('/voicemail/message/' + message.msg_id)
				actions = '<form method="POST" action="/voicemail/delete/%s"><input type="hidden" name="msg_id" value="%s" /><input type="submit" name="submit" value="Borrar" /></form>' % (message.msg_id, message.msg_id)
			else:
				audio = ""
				actions = ""
			result.append([message.callerid, time.ctime(message.origtime), str(message.duration), audio, actions])
		output += html.format_table([['origen', 'fecha', 'duracion', 'audio', 'actions']] + result)
	return output

    def getChild(self, name, request):
        return self
