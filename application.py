from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import time
from datetime import date, datetime, timedelta
import pytz
import os
import uuid

from helpers import apology, login_required

# Configure application

app = Flask(__name__)

# Ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///y-event.db")

# Route to home page
@app.route("/")
def index():
    """Show list of events"""

    # Delete events that have already passed
    events = db.execute("SELECT * FROM eventsfinal ORDER BY starttime") # Arrange events in order of start time
    deleteid = [] # Id numbers of events to delete
    for i in range(len(events)):
        endtime = events[i]["endtime"]
        year = int(endtime[:4])
        month = int(endtime[5:7])
        day = int(endtime[8:10])
        hour = int(endtime[11:13])
        minute = int(endtime[14:])
        dt = datetime(year, month, day, hour, minute)
        # Calculate seconds since epoch of event
        eventtimestamp = (dt - datetime(1970, 1, 1)) / timedelta(seconds=1)
        # Calculate current number of seconds since epoch
        currenttimestamp = (datetime.now() - datetime(1970, 1, 1)) / timedelta(seconds=1)
        if (eventtimestamp < currenttimestamp):
            deleteid.append(events[i]["id"]) # If event has passed, add id to list

    # Delete from database where id is in deleteid
    for i in deleteid:
        db.execute("DELETE FROM eventsfinal WHERE id=:index", index=i)

    # Subject categories
    subjects = db.execute("SELECT * FROM subject")

    # Event type categories
    eventtypes = db.execute("SELECT * FROM eventtype")

    startdatelist = []
    enddatelist = []
    starttimelist = []
    endtimelist = []

    for i in range(len(events)):
        # Parse start time to show up as "day of week, month day, year"
        datestring = events[i]["starttime"]
        finaldate = date(day=int(datestring[8:10]), month=int(datestring[5:7]), year=int(datestring[:4])).strftime('%A' + ', ' + '%B %d' + ", " + '%Y')
        startdatelist.append(finaldate)
        timestring = datestring[11:]
        if int(timestring[:2]) > 12:
            firsttwo = str(int(timestring[:2]) - 12)
            timestring = firsttwo + timestring[2:] + " PM"
        elif int(timestring[:2]) == 12:
            timestring = "12" + timestring[2:] + " PM"
        elif int(timestring[:2]) == 0:
            timestring = "12" + timestring[2:] + " AM"
        else:
            timestring = timestring + " AM"
        starttimelist.append(timestring)

        # Parse end time in the same way
        datestring = events[i]["endtime"]
        finaldate = date(day=int(datestring[8:10]), month=int(datestring[5:7]), year=int(datestring[:4])).strftime('%A' + ', ' + '%B %d' + ", " + '%Y')
        enddatelist.append(finaldate)
        timestring = datestring[11:]
        if int(timestring[:2]) > 12:
            firsttwo = str(int(timestring[:2]) - 12)
            timestring = firsttwo + timestring[2:] + " PM"
        elif int(timestring[:2]) == 12:
            timestring = "12" + timestring[2:] + " PM"
        elif int(timestring[:2]) == 0:
            timestring = "12" + timestring[2:] + " AM"
        else:
            timestring = timestring + " AM"
        endtimelist.append(timestring)

    # Render template
    return render_template("index.html", events=events, entries=len(events), subjects=subjects, eventtypes=eventtypes, startdatelist=startdatelist, enddatelist=enddatelist, starttimelist=starttimelist, endtimelist=endtimelist)


# Admin approval page (in admin account only)
@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    """Show list of events with accept, decline and edit buttons"""

    # Check if logged into admin account
    if session["user_id"] != 11:
        return apology("Not admin", 403)

    # When user reaches page via post
    if request.method == "POST":

        # Listen to responses
        response=request.form['response'].split("_")
        if response[0] == "accept":

            row = db.execute("SELECT * FROM events WHERE id = :tmp", tmp=response[1])
            # Move event to eventsfinal, delete event from event
            db.execute("INSERT INTO eventsfinal (user_id, name, organizer, starttime, endtime, locationname, address, subject_id, eventtype_id, attendee, description, link) VALUES (:user_id, :name, :organizer, :starttime, :endtime, :locationname, :address, :subject_id, :eventtype_id, :attendee, :description, :link)", user_id = row[0]["user_id"], name = row[0]["name"], organizer= row[0]["organizer"], starttime =row[0]["starttime"], endtime = row[0]["endtime"], locationname = row[0]["locationname"], address = row[0]["address"], subject_id = row[0]["subject_id"], eventtype_id = row[0]["eventtype_id"], attendee = row[0]["attendee"], description = row[0]["description"], link=row[0]["link"])
            db.execute("DELETE FROM events WHERE id = :tmp", tmp=response[1])
            flash("Event accepted")
            return redirect("/admin")


        #delete event from events
        elif response[0] == "decline":
            row = db.execute("SELECT * FROM events WHERE id = :tmp", tmp=response[1])
            db.execute("DELETE FROM events WHERE id = :tmp", tmp=response[1])
            flash("Event declined")
            return redirect("/admin")

        #print event in addevent form except it goes right to eventsfinal
        elif response[0] == "edit":
            eventtypes = db.execute("SELECT * FROM eventtype")
            subjects = db.execute("SELECT * FROM subject")
            row = db.execute("SELECT * FROM events WHERE id = :tmp", tmp=response[1])
            event = row[0]
            defaultSubject = next((filter(lambda item: item['id'] == event['subject_id'], subjects)))['subject']
            defaultType = next((filter(lambda item: item['id'] == event['eventtype_id'], eventtypes)))['type']
            return render_template("editevent.html", event=event, eventtypes=eventtypes, subjects=subjects, defaultSubject=defaultSubject, defaultType=defaultType)


    #when events are loaded
    else:
        #sort events by time (for display purposes)
        events = db.execute("SELECT * FROM events ORDER BY starttime")
        subjects = db.execute("SELECT * FROM subject")
        eventtypes = db.execute("SELECT * FROM eventtype")
        startdatelist = []
        enddatelist = []
        starttimelist = []
        endtimelist = []

        #format start and end times such that it's more readable for users, and store them in separate lists
        for i in range(len(events)):
            datestring = events[i]["starttime"]
            finaldate = date(day=int(datestring[8:10]), month=int(datestring[5:7]), year=int(datestring[:4])).strftime('%A' + ', ' + '%B %d' + ", " + '%Y')
            startdatelist.append(finaldate)
            timestring = datestring[11:]
            if int(timestring[:2]) > 12:
                firsttwo = str(int(timestring[:2]) - 12)
                timestring = firsttwo + timestring[2:] + " PM"
            elif int(timestring[:2]) == 12:
                timestring = "12" + timestring[2:] + " PM"
            elif int(timestring[:2]) == 0:
                timestring = "12" + timestring[2:] + " AM"
            else:
                timestring = timestring + " AM"
            starttimelist.append(timestring)

            datestring = events[i]["endtime"]
            finaldate = date(day=int(datestring[8:10]), month=int(datestring[5:7]), year=int(datestring[:4])).strftime('%A' + ', ' + '%B %d' + ", " + '%Y')
            enddatelist.append(finaldate)
            timestring = datestring[11:]
            if int(timestring[:2]) > 12:
                firsttwo = str(int(timestring[:2]) - 12)
                timestring = firsttwo + timestring[2:] + " PM"
            elif int(timestring[:2]) == 12:
                timestring = "12" + timestring[2:] + " PM"
            elif int(timestring[:2]) == 0:
                timestring = "12" + timestring[2:] + " AM"
            else:
                timestring = timestring + " AM"
            endtimelist.append(timestring)


        return render_template("admin.html", events=events, entries=len(events), subjects=subjects, eventtypes=eventtypes, startdatelist=startdatelist, enddatelist=enddatelist, starttimelist=starttimelist, endtimelist=endtimelist)


@app.route("/editevent", methods=["GET", "POST"])
@login_required
def editevent():
    """Allow admin to edit an event."""

    #when admin submitted a form
    if request.method == "POST":

        #initialize variables
        eventid = request.form["submit"]
        name = request.form.get("eventname")
        description = request.form.get("description")
        organizer = request.form.get("organizer")
        starttime = request.form.get("starttime")
        endtime = request.form.get("endtime")
        locationname = request.form.get("locationname")
        address = request.form.get("address")
        eventtype = request.form.get("eventtype")
        subject = request.form.get("subject")
        subject_id = (db.execute("SELECT * FROM subject WHERE subject = :subject", subject=subject))[0]["id"]
        eventtype_id = (db.execute("SELECT * FROM eventtype WHERE type = :eventtype", eventtype=eventtype))[0]["id"]
        link = request.form.get("link")

        #insert the input of the form to the production database (eventsfinal)
        db.execute("""INSERT INTO eventsfinal (user_id, name, description, organizer, starttime, endtime, locationname, address, subject_id, eventtype_id, link)
            VALUES(:user_id, :name, :description, :organizer, :starttime, :endtime, :locationname, :address, :subject_id, :eventtype_id, :link)""",
                   user_id=session["user_id"], name=name, description=description, organizer=organizer, starttime=starttime, endtime=endtime,
                   locationname=locationname, address=address, subject_id=subject_id, eventtype_id=eventtype_id, link=link)

        subject_id = (db.execute("SELECT * FROM subject WHERE subject = :subject", subject=subject))[0]["id"]
        eventtype_id = (db.execute("SELECT * FROM eventtype WHERE type = :eventtype", eventtype=eventtype))[0]["id"]

        db.execute("""INSERT INTO eventsfinal (subject_id, eventtype_id)
            VALUES(:subject_id, :eventtype_id)""",
                   subject_id=subject_id, eventtype_id=eventtype_id)

        #delete the entries from the beta database (events)
        db.execute("DELETE FROM events WHERE id = :tmp", tmp=eventid)

        #flash message to indicate success
        flash("Event edited")

        #redirect admin to admin page for further approval of events
        return redirect("/admin")

    #when admin first load the page
    else:
        #initialize a list of all events pending approval
        rows = db.execute("SELECT * FROM events")
        eventtypes = db.execute("SELECT * FROM eventtype")
        subjects = db.execute("SELECT * FROM subject")

        #load editevent page with above variables
        return render_template("editevent.html", event=rows[0], eventtypes=eventtypes, subjects=subjects)


@app.route("/addevent", methods=["GET", "POST"])
@login_required
def addevent():
    """Allow user to add an event."""

    # If user reaches page via post
    if request.method == "POST":

        # Get data from user-submitted form
        name = request.form.get("eventname")
        description = request.form.get("description")
        organizer = request.form.get("organizer")
        starttime = request.form.get("starttime")
        endtime = request.form.get("endtime")
        locationname = request.form.get("locationname")
        address = request.form.get("address")
        eventtype = request.form.get("eventtype")
        subject = request.form.get("subject")
        link = request.form.get("link")

        # Get subject and eventtype ids
        subject_id = (db.execute("SELECT * FROM subject WHERE subject = :subject", subject=subject))[0]["id"]
        eventtype_id = (db.execute("SELECT * FROM eventtype WHERE type = :eventtype", eventtype=eventtype))[0]["id"]

        # Put data into events database, which is sent to admin
        db.execute("""INSERT INTO events (user_id, name, description, organizer, starttime, endtime, locationname, address, subject_id, eventtype_id, link)
            VALUES(:user_id, :name, :description, :organizer, :starttime, :endtime, :locationname, :address, :subject_id, :eventtype_id, :link)""",
                   user_id=session["user_id"], name=name, description=description, organizer=organizer, starttime=starttime, endtime=endtime,
                   locationname=locationname, address=address, subject_id=subject_id, eventtype_id=eventtype_id, link=link)

        # Put subject and eventtype ids into database, which is sent to admin
        db.execute("""INSERT INTO events (subject_id, eventtype_id)
            VALUES(:subject_id, :eventtype_id)""",
                   subject_id=subject_id, eventtype_id=eventtype_id)

        # Flash message to user
        flash("Event sent to admin!")

        # Redirects to home page
        return  redirect("/")

    # User reaches page via GET
    else:

        eventtypes = db.execute("SELECT * FROM eventtype")
        subjects = db.execute("SELECT * FROM subject")

        # Render template
        return render_template("addevent.html", eventtypes=eventtypes, subjects=subjects)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        if session["user_id"] == 11:
            return redirect("/admin")
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user for an account."""

    # POST
    if request.method == "POST":

        # Validate form submission
        if not request.form.get("email"):
            return apology("missing email")
        elif not request.form.get("username"):
            return apology("missing username")
        elif not request.form.get("password"):
            return apology("missing password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords don't match")

        # Add user to database

        username = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        #check if username is available
        if  username:
           return apology("username already registered")

        #check if email is taken
        email = db.execute("SELECT * FROM users WHERE email = :email",
                          email=request.form.get("email"))
        if email:
            return apology("email already registered")

        id = db.execute("INSERT INTO users (username, email, hash) VALUES(:username, :email, :tmp) ",
                        username=request.form.get("username"),
                        email=request.form.get("email"),
                        tmp=generate_password_hash(request.form.get("password")))

        # Log user in
        session["user_id"] = id

        # Let user know they're registered
        flash("Registered!")
        return redirect("/")

    # GET
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
