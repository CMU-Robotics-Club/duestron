import os
import time
from flask import Flask, render_template, request, redirect
import threading

from requests_html import (
    HTMLSession,
)  # pip install git+https://github.com/psf/requests-html.git
from bs4 import BeautifulSoup
import re
import urllib.parse

import yaml

dues_payers = []

def tartanlunkheads():
    global dues_payers
    while True:
        with open("cred.yaml") as file:
            creds = yaml.safe_load(file)

        BASEURL = "https://tartanconnect.cmu.edu"

        session_requests = HTMLSession()

        ## Login to TartanConnect
        # Get csrf token
        result = session_requests.get(BASEURL + "/login_only")
        soup = BeautifulSoup(result.text, "html.parser")
        csrf_token = soup.find("input", {"name": "_csrf"})["value"]

        # Create form payload
        payload = {
            "email": creds["EMAIL"],
            "password": creds["PASSWORD"],
            "update": "1",
            "ssl": "1",
            "redirect": "student_index",
            "page": "login",
            "user": "",
            "_csrf": csrf_token,
        }

        # Send login request
        result = session_requests.post(
            BASEURL + "/student_login",
            data=payload,
            headers=dict(referer=BASEURL + "/login_only"),
        )

        # We have to visit the roboclub homepage first because of how TartanConnect works
        result = session_requests.get(
            "https://tartanconnect.cmu.edu/officer_login_redirect?club_id=68235"
        )

        # Validate that we have logged in successfully
        result = session_requests.get(
            "https://tartanconnect.cmu.edu/officer_login_redirect?club_id=68235"
        )
        if not (
            "Logout" in result.html.html
            and "Robotics Club" in result.html.html
            and "Dashboard | Robotics Club" in result.html.html
        ):
            raise TaskRevokedError("Failed to log in to TartanConnect")

        for i in range(20):
            members_raw_response = (
                session_requests.get(
                    "https://tartanconnect.cmu.edu/mobile_ws/v17/mobile_manage_members?range=0&limit=9999&filter4=11421891&filter1=members&filter4_contains=OR&filter4_notcontains=OR&filter6_contains=OR&filter6_notcontains=OR"
                )
            ).html.html

            andrewids = list(re.findall(r'"p7":"([^"]*)","p8":', members_raw_response))
            dues_payers = andrewids
            print("found {} dues paying members".format(len(andrewids)))
            time.sleep(600)

threading.Thread(target=tartanlunkheads, daemon=True).start()

app = Flask(__name__)

with open("index.html") as f:
    html = f.read()

@app.route("/")
def index():
    aid = request.args.get("andrewid")
    if aid:
        succ = ((aid+"@andrew.cmu.edu" in dues_payers) or (aid in dues_payers))
        out = '<h2 style="color: {};">{} has {}paid dues</h2>'.format(
            "green" if succ else "darkred", aid, "" if succ else "not ")
    else:
        out = ""


    return html.replace("!!!", out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
