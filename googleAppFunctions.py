import os
import httplib2
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from apiclient import errors
import base64
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import os

# ----------------------------------------------------------------------------#
# gmail specific functions
# ----------------------------------------------------------------------------#
def ModifyMessage(service, user_id, msg_id, msg_labels):
  try:
    message = service.users().messages().modify(userId=user_id, id=msg_id,
                                                body=msg_labels).execute()

    label_ids = message['labelIds']

    print 'Message ID: %s - With Label IDs %s' % (msg_id, label_ids)
    return message
  except errors.HttpError, error:
    print 'An error occurred: %s' % error


def CreateMsgLabels(removeLabels,addLabels):#labels=[scribeProcessing]
  return {'removeLabelIds': removeLabels, 'addLabelIds': addLabels}

def CreateLabel(service, user_id, label_object):
  try:
    label = service.users().labels().create(userId=user_id,
                                            body=label_object).execute()
    print label['id']
    return label
  except errors.HttpError, error:
    print 'An error occurred: %s' % error


def MakeLabel(label_name, mlv='show', llv='labelShow'):
  label = {'messageListVisibility': mlv,
           'name': label_name,
           'labelListVisibility': llv}
  return label

def SendMessage(service, user_id, message):
  try:
    message = (service.users().messages().send(userId=user_id, body=message)
               .execute())
    print 'Message Id: %s' % message['id']
    return message
  except errors.HttpError, error:
    print 'An error occurred: %s' % error

def CreateDraft(service, user_id, message_body):
  try:
    message = {'message': message_body}
    draft = service.users().drafts().create(userId=user_id, body=message).execute()

    print 'Draft id: %s\nDraft message: %s' % (draft['id'], draft['message'])

    return draft
  except errors.HttpError, error:
    print 'An error occurred: %s' % error
    return None

def CreateMessage(sender, to, subject, message_text, cc=None, thread_id=None):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    if cc is not None:
      message['cc']=cc
    if thread_id is not None:
        return {'raw': base64.urlsafe_b64encode(message.as_string()),'threadId':thread_id}
    else:
        return {'raw': base64.urlsafe_b64encode(message.as_string())}

def CreateMessageWithAttachment(sender, to, subject, message_text, file_dir,filename,thread_id):
  message = MIMEMultipart()
  message['to'] = to
  message['from'] = sender
  message['subject'] = subject

  msg = MIMEText(message_text)
  message.attach(msg)

  path = os.path.join(file_dir, filename)
  content_type, encoding = mimetypes.guess_type(path)

  if content_type is None or encoding is not None:
    content_type = 'application/octet-stream'
  main_type, sub_type = content_type.split('/', 1)
  if main_type == 'text':
    fp = open(path, 'rb')
    msg = MIMEText(fp.read(), _subtype=sub_type)
    fp.close()
  elif main_type == 'image':
    fp = open(path, 'rb')
    msg = MIMEImage(fp.read(), _subtype=sub_type)
    fp.close()
  elif main_type == 'audio':
    fp = open(path, 'rb')
    msg = MIMEAudio(fp.read(), _subtype=sub_type)
    fp.close()
  else:
    fp = open(path, 'rb')
    msg = MIMEBase(main_type, sub_type)
    msg.set_payload(fp.read())
    fp.close()

  msg.add_header('Content-Disposition', 'attachment', filename=filename)
  message.attach(msg)

  if thread_id != "":
      return {'raw': base64.urlsafe_b64encode(message.as_string()), 'threadId': thread_id}
  else:
      return {'raw': base64.urlsafe_b64encode(message.as_string())}

def givePermissions(user,drive):
  domain_permission = {
    'type': 'user',
    'role': 'writer',
    'emailAddress': user.email,
  }
  req = drive.permissions().create(
    fileId=user.spreadSheetId,
    body=domain_permission,
    fields="id"
  )
  req.execute()
  return user.spreadSheetId