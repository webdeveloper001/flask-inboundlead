from flask_wtf import Form
from wtforms import TextField, PasswordField, IntegerField, DateField, SelectField, TextAreaField, DateTimeField
from wtforms_components import TimeField
from wtforms.validators import DataRequired, EqualTo, Length, Email, ValidationError
from wtforms import validators
from wtforms.fields.html5 import EmailField

class Register(Form):
    name = TextField('Name', validators=[DataRequired(message="Please enter your name"), Length(min=1, max=25)])
    email = EmailField('Email', validators=[DataRequired(message="Please enter your email address"),
                                            validators.Email("Please enter correct email address.")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=2, max=40)])
    confirm = PasswordField('Repeat Password',[DataRequired(),EqualTo('password', message='Passwords must match')])

class LoginForm(Form):
    email = TextField('Email', [DataRequired(), validators.Email("Please enter correct email address.")])
    password = PasswordField('Password', [DataRequired()])

class ForgotForm(Form):
    email = TextField('Email', validators=[DataRequired(), Length(min=6, max=40), validators.Email("Please enter correct email address.")])

class ResetPasswordSubmit(Form):
    password = PasswordField('Password', validators=[validators.Required(), validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password')

class RequestDemo(Form):
    name = TextField('Name', validators=[DataRequired(message="Please enter your name")])
    email = EmailField('Email', validators=[DataRequired(message="Please enter your email address"),
                                validators.Email("Please enter correct email address.")])
    phone = IntegerField('Phone', validators=[DataRequired(message="Please enter your phone number")])
    message = SelectField('entityType',choices=[('Publisher','Publisher'), ('App developer','App developer'), ('publisher network', 'publisher network'), ('ad tech', 'ad tech')])


class ContactForm(Form):
    email = EmailField('Email', validators=[DataRequired(message="Please enter your email address"),
                             validators.Email("Please enter correct email address.")])
    name = TextField('Name', validators=[DataRequired(message="Please enter your name")])
    phone = IntegerField('Phone', validators=[DataRequired(message="Please enter your phone number")])
    message = TextAreaField('Message', validators=[DataRequired(message="Please enter message")])

#----------------------------------------------------------------------------#
# Web2Lead
# ----------------------------------------------------------------------------#

class ScribeForm(Form):
    name = TextField('Name', validators=[DataRequired("Please enter your name")])
    email = EmailField('Email', validators=[DataRequired(message="Please enter your email address"),
                                            validators.Email("Please enter correct email address.")])
    company = TextField('Company', validators=[DataRequired("Please enter your company")])

#----------------------------------------------------------------------------#
# inboundLead forms
# ----------------------------------------------------------------------------#
class CreateAssistant(Form):
    hostName = TextField('Your Name', validators=[])
    hostCompany = TextField('Your Company', validators=[])
    assistantName = TextField("New Assistant's Name", validators=[])
    assistantSignature = TextAreaField("Assistant's Signature", validators=[])

class AddTemplates(Form):
    template1q = TextAreaField('Email when lead is high quality:', validators=[])
    template2q = TextAreaField('Email when lead is low quality:', validators=[])
    template3q = TextAreaField('Email to qualify low quality leads:', validators=[])
    template4q = TextAreaField('Email when lead asks about pricing:', validators=[])
    template5q = TextAreaField('Email when lead asks for more info:', validators=[])
    template6q = TextAreaField('Introductory Email:', validators=[])
    template7q = TextAreaField('First Follow Up Email:', validators=[])
    onboardingSubject = TextField("OnboardingSubject",validators=[])
    template1a = TextAreaField('', validators=[])
    template2a = TextAreaField('', validators=[])
    template3a = TextAreaField('', validators=[])
    template4a = TextAreaField('', validators=[])
    template5a = TextAreaField('', validators=[])
    template6a = TextAreaField('', validators=[])
    template7a = TextAreaField('', validators=[])

class AddCalendar(Form):
    callDuration = IntegerField('Call Duration (mins)', validators=[])
    dayStartTime = TimeField('Start of working day',validators=[])
    dayEndTime = TimeField('End of working day', validators=[])

class SuggestReply(Form):
    replyEmail=TextAreaField('replyEmail',validators=[])

