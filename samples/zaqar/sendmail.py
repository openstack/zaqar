# Copyright (c) 2018 Ustack, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from email.mime.text import MIMEText
from email.parser import Parser
import json
import smtplib
import sys

from keystoneauth1 import loading
from keystoneauth1 import session as ks_session
from oslo_config import cfg
import requests
import retrying

KUNKA_SERVICE_TYPE = 'portal'

"""KUNKA_CORP_INFO_PATH is an API for obtaining information from the database
(such as /api/email/corporation-info), and the returned information
is the value of the field in the mail template. It is connected after
the ip:port which is the database connection information. ip:port
like 127.0.0.1:3306, or other"""
KUNKA_CORP_INFO_PATH = 'Your API address'

# The information is relatively sensitive, suggesting encrypted transmission,
# or stored in the database to return.When "use_ssl" is False, the "port" is
# 25, otherwise, the "port" is 465 in using SSL type.
mail_info = {
    "from": "youremail@youremail.com",
    "hostname": "yourSMTP_serverAddr",
    "username": "yourSMTP_server-username",
    "password": "Authorization_code",
    "port": 25,
    "use_ssl": False
}

# It's a HTML mail template,and can be changed as needed
mail_body = u"""
<div style="font-family: 'Microsoft YaHei', Arial, Helvetica,sans-serif;
position: relative;margin: 0 auto; width: 702px; font-size: 0;">
  <div style="display: inline-block; width: 0; height: 0;
  border-width: 10px; border-style: solid; border-color:
  transparent #343E41 #343E41 transparent;margin-left: 227px;"></div>
  <div style="display: inline-block; width: 0; height: 0;
  border-width: 10px; border-style: solid; border-color:
  transparent transparent #343E41 #343E41;margin-left: 206px;"></div>
  <div style="width: 206px; height: 60px; position:absolute;
  top: 0px; left: 247px; background-color: #343E41;
  background-position: center center; background-size:
  contain; background-repeat: no-repeat; z-index: 10;">
  <img src="{logo_url}" style=" width: 206px; height: 60px;"></div>
  <div style="width: 662px; margin-top: 0; margin-left:
  auto; margin-right: auto; background-color: #343E41;
  padding: 20px;">
    <div style="width: 662px; background-color:
    transparent; border: 1.2px solid #01AFC9;
    position: relative; padding: 0; text-align: center;">
    <div style="width: 20px; height: 20px; position:
    absolute; left:0; top: 0; background-color: #01AFC9;
     margin: 0;"></div>
    <div style="width: 20px; height: 20px; position:
     absolute; right:0; top: 0; background-color:
     #01AFC9; margin: 0;"></div>
    <div style="width: 20px; height: 20px; position:
    absolute; left:0; bottom: 0; background-color:
    #01AFC9; margin: 0;"></div>
    <div style="width: 20px; height: 20px; position:
    absolute; right:0; bottom: 0; background-color:
     #01AFC9; margin: 0;"></div>
    <p style="text-align: center; margin-top:36px;">
      <span style="font-size: 6px; color: #ffffff;
       vertical-align: middle;">///////////////////</span>
      <span style="display: inline-block; margin-left:
      40px; margin-right: 40px; color: #ffffff; font-size:
       20px; vertical-align: middle;">Respected
        {corp_name}user</span>
      <span style="font-size: 6px; color: #ffffff;
       vertical-align: middle;">///////////////////</span>
    </p >
    <div>
      <div style="margin-top: 12px; color: #ffffff;
       font-size: 14px; text-align: left; display:
       inline-block; max-width: 60%;">
            <div>
                <div>
                    <p>{confirm_or_alarm}</p>
                </div>
            </div>
      </div>
    </div>
    <p style="margin-top: 16px; margin-bottom: 14px;
     font-size: 12px; letter-spacing: 0.67px; text-align:
     center; height: 16px; color: #ffffff;">{corp_name}—
     <a style="text-decoration: none; color:
      #ffffff;" href=" >">{home_link} </a></p >
    </div>
  </div>
</div>
"""

mail_confirm_link = u"""
Your mailbox will be used for receiving system notifications.
If you confirm, click the following link:
<a href="{confirm_link}" target="_blank">Activation link</a>
"""

mail_alarm_info = u"""
 Your alarm information is as follows:{reason}<br>
 Alarm level:{severity}<br>
 Alarm name:{alarm_name}<br>
 Alarm ID ：{alarm_id}
"""


def prepare_conf():
    cfg.CONF(project='zaqar')
    loading.register_auth_conf_options(cfg.CONF, 'keystone_authtoken')


def get_admin_session():
    auth_plugin = \
        loading.load_auth_from_conf_options(cfg.CONF, 'keystone_authtoken')
    return ks_session.Session(auth=auth_plugin)


def get_endpoint(session, service_type, interface='internal'):
    return session.get_endpoint(service_type=service_type,
                                interface=interface)


@retrying.retry(stop_max_attempt_number=3)
def get_corp_info(session):
    kunka_endpoint = get_endpoint(session, KUNKA_SERVICE_TYPE)
    kunka_url = kunka_endpoint + KUNKA_CORP_INFO_PATH

    res = None
    res = requests.get(kunka_url)

    corp_info = res.json()
    return {"corp_name": corp_info['corporationName'],
            "logo_url": corp_info['emailLogoUrl'],
            "home_link": corp_info['homeUrl'],
            "from": corp_info['from']}


def generate_msg(subbody, to, from_, subject, **kwargs):
    payload = mail_body.format(confirm_or_alarm=subbody, **kwargs)
    msg = MIMEText(payload.encode('utf-8'), 'html', 'utf-8')
    msg['subject'] = subject
    msg['from'] = from_
    msg['to'] = to

    return msg


def generate_subbody(subbody, **kwargs):
    return subbody.format(**kwargs)


def get_confirm_link(str_):
    return str_.split('below: ')[-1]


def prepare_msg(msg_str):
    headers = Parser().parsestr(msg_str)
    payload = headers.get_payload()

    msg_subject = headers['subject']
    if not headers['subject']:
        alarm_info = json.loads(payload)['body']
        subject = msg_subject + alarm_info['alarm_name']
        template = generate_subbody(mail_alarm_info,
                                    reason=alarm_info['reason'],
                                    severity=alarm_info['severity'],
                                    alarm_name=alarm_info['alarm_name'],
                                    alarm_id=alarm_info['alarm_id'])
    else:
        subject = msg_subject
        template = generate_subbody(mail_confirm_link,
                                    confirm_link=get_confirm_link(payload))

    session = get_admin_session()
    corp_info = get_corp_info(session)

    msg = generate_msg(
        template, headers['to'],
        corp_info['from'], subject, logo_url=corp_info['logo_url'],
        corp_name=corp_info['corp_name'], home_link=corp_info['home_link'])

    return msg


@retrying.retry(stop_max_attempt_number=3)
def send_it(msg):
    # if "use_ssl" is True, the "port" is 465 in using SSL type,
    # or other SSL port.
    if mail_info['use_ssl']:
        sender = smtplib.SMTP_SSL(mail_info["hostname"], mail_info['port'])
    else:
        sender = smtplib.SMTP(mail_info["hostname"], mail_info['port'])
    sender.set_debuglevel(1)

    sender.ehlo(mail_info["hostname"])
    try:
        sender.login(mail_info["username"], mail_info["password"])
    except smtplib.SMTPException:
        print("Error: Failed to connect to the SMTP service")
    sender.sendmail(msg['from'], msg['to'], msg.as_string())


def send_email(msg_str):
    prepare_conf()
    send_it(prepare_msg(msg_str))


if __name__ == '__main__':
    send_email(''.join(sys.stdin.readlines()))
