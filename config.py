import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
  DEBUG = False
  TESTING = False
  CSRF_ENABLED = True
  SECRET_KEY = os.environ['SECRET_KEY']
  SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
  SECURITY_PASSWORD_SALT = os.environ['SECURITY_PASSWORD_SALT']
  SQLALCHEMY_TRACK_MODIFICATIONS=False
  # mail settings
  MAIL_SERVER = 'smtp.gmail.com'
  MAIL_PORT = 465
  MAIL_USERNAME = 'hi@tryscribe.com'
  MAIL_PASSWORD = os.environ['MAIL_PASSWORD']
  MAIL_USE_TLS = False
  MAIL_USE_SSL = True
  MAIL_DEFAULT_SENDER = 'sachin@tryscribe.com'
  # Stripe test configs
  STRIPE_CLIENT_ID = 'ca_9KNKL89g9NkEqU0sunL2HuVZGSLdiBPD'
  STRIPE_SECRET_KEY = 'sk_test_J1C47kLMolxuraaz86eB3iYX'
  STRIPE_PUBLISHABLE_KEY = 'pk_test_dzO4Vz93tvnyjdYOxHEvBsQp'
  SENTRY_DSN = 'https://621875d3701c4f678c7c2e0fa9f24bf3:b6e4731bb8f74cfabe747da7195637a2@sentry.io/132589'
  CLEARBIT_KEY='sk_c26c251e8cdfd7f81d7f8fd3a8236595#'
  #celery
  #CELERY_BROKER_URL = 'redis://'
  #CELERY_RESULT_BACKEND = 'redis://'
  #CELERY_TASK_SERIALIZER = 'json'
  ERROR_HANDLER_LEVEL=Exception
  BASE_URL = 'https:///www.tryscribe.com'
  UPLOAD_FOLDER = 'static/files'
  DEFAULT_REP = 'emma@tryscribe.com'
  DEFAULT_SALESREP_ID = 49
  TEMPLATE_JS_FILE = "template.js"
  frontToken = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzY29wZXMiOlsiKiJdLCJpc3MiOiJmcm9udCIsInN1YiI6InNjcmliZTIifQ.8IlB_g56KCVtYgDZe1_YlpWdqFIl3RjNsBtTlu9KVsY"
  frontHeaders = {'Authorization': frontToken, 'Content-Type': 'application/json', 'Accept': 'application/json'}
  frontFwdUrl = "https://api2.frontapp.com/channels/cha_1gqn/incoming_messages"
  frontReceiveUrl = "http://be595715.ngrok.io/frontReply"

class ProductionConfig(Config):
  DEBUG = False
  ERROR_HANDLER_LEVEL=Exception
  BASE_URL = 'https://www.tryscribe.com'
  CLEARBIT_KEY = 'sk_c26c251e8cdfd7f81d7f8fd3a8236595'

class StagingConfig(Config):
  DEVELOPMENT = True
  DEBUG = False
  ERROR_HANDLER_LEVEL=Exception
  BASE_URL = 'https://lit-hollows-94218.herokuapp.com'
  DEFAULT_REP = 'arorapsr@gmail.com'
  DEFAULT_SALESREP_ID = 2
  TEMPLATE_JS_FILE = "templateStaging.js"
  CLEARBIT_KEY = 'sk_c26c251e8cdfd7f81d7f8fd3a8236595'


class DevelopmentConfig(Config):
  DEVELOPMENT = True
  DEBUG = True
  ERROR_HANDLER_LEVEL = 500
  BASE_URL = 'http://localhost:5000'
  DEFAULT_REP = 'sachinbhat.as@gmail.com'
  DEFAULT_SALESREP_ID = 38
  TEMPLATE_JS_FILE = "templateDevelopment.js"


class TestingConfig(Config):
  TESTING = True
  SQLALCHEMY_DATABASE_URI = 'postgres:///sachin_test_db'
  CSRF_ENABLED = False



