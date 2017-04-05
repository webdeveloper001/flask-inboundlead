from flask import Blueprint, session, render_template
from flask_login import current_user, login_user
from assistantAIfunctions import *
from models import *
from googleAppFunctions import *
from datetime import datetime, timedelta
import json

branchCode = Blueprint('branchCode', __name__,template_folder='templates',static_folder='static')

@branchCode.route("/modalTest", methods=["GET","POST"])
def modalTest():
  return render_template('web2lead/modalTest.html')