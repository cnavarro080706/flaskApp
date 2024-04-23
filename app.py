from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, request,logging                                                        # Importing the Flask module
# from data import Articles                                      # Importing the articles data
from flask_mysqldb import MySQL                                # Importing MySQL flask module
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt                          # Import module to encrypt passwords

app = Flask(__name__)                                          # Flask Object

# Config MySQL
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "devpasswd"
app.config["MYSQL_DB"] = "myflaskapp"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"                 # Coverting received data to Dict

# initialize MySQL
mysql = MySQL(app)

app.debug=True                                                 # enable this for page refresh

# Articles = Articles()

# Index
@app.route("/")                                                # route for index page
def index():
    return render_template("index.html")                       # create a sample view function
# About
@app.route("/about")
def about():
    return render_template("about.html")

# Articles
@app.route("/articles")
def articles():
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template("articles.html", articles=articles)
    else:
        msg = "No articles found."
        return render_template("articles.html", msg=msg)

    # Close connection
    cur.close()

# Single Article
@app.route("/article/<string:id>/")
def article(id):
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    return render_template("article.html", article=article)

# Register Form Class
class RegistrationForm(Form):
    lastname = StringField("Lastname", [validators.Length(min=1, max=50)])
    firstname = StringField("Firstname", [validators.Length(min=1, max=50)])
    username = StringField("Username", [validators.Length(min=4, max=25)])
    email = StringField("Email", [validators.Length(min=6, max=50)])
    password = PasswordField("Password", [
        validators.DataRequired(),
        validators.EqualTo("confirm", message="Passwords do not match!")
        ])
    confirm = PasswordField("Confirm Password")

# User Registeration
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        lastname = form.lastname.data
        firstname = form.firstname.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))        # encrypt the plain text pw

        # create cursor
        cur = mysql.connection.cursor()

        # execute query
        cur.execute("INSERT INTO users (lastname, firstname, username, email, password) VALUES (%s, %s, %s, %s, %s)", (lastname, firstname, username, email, password))

        # commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash("Your are Registered Successfully!", "success")

        return redirect(url_for("index")) 
    return render_template("register.html", form=form)   

# User login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get form fields
        username = request.form["username"]
        password_candidate =  request.form["password"]

        # Create cursor
        cur = mysql.connection.cursor()
       
        # Execute Get Query by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get MySQL PW hash
            data = cur.fetchone()
            password = data["password"]

            # Compare user login password to MySQL user password
            if sha256_crypt.verify(password_candidate, password):
                # app.logger.info("PASSWORD MATCHED.") - This is for debugging purposes
                # Cature session variables
                session["logged_in"] = True
                session["username"] = username

                flash('You have logged in successfuly!', "success")
                return redirect(url_for("dashboard"))
            else:
                # app.logger.info("PASSWORD NOT MATCHED!") - This is for debugging purposes
                error = "Invalid Username or Password!"
                return render_template("login.html", error=error)
            # Close connection
            cur.close()
        else:
            # app.logger.info("NO USER!") - This is for debugging purposes
            error = "Username not found."
            return render_template("login.html", error=error)
    
    return render_template("login.html")

# Check if the user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, ** kwargs)
        else:
            flash("Unauthorized, Please login.", "danger")
            return redirect(url_for("login"))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You're Session was logged out sucessfully!", "success")
    return redirect(url_for("login"))

# Dashboard
@app.route("/dashboard")
@is_logged_in
def dashboard():
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template("dashboard.html", articles=articles)
    else:
        msg = "No articles found."
        return render_template("dashboard.html", msg=msg)

    # Close connection
    cur.close()
    
# Article Form Class
class ArticleForm(Form):
    title = StringField("Title", [validators.Length(min=1, max=200)])
    body = TextAreaField("Body", [validators.Length(min=1)])
   
# Add Article
@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor

        cur = mysql.connection.cursor()

        # Execute CRUD
        cur.execute("INSERT INTO articles(title, body, author) VALUES (%s, %s, %s)", (title, body, session["username"]))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()
        flash(" Article created succesfully!", "success")
        return redirect(url_for("dashboard"))
   
    return render_template("add_article.html", form=form)

# Edit Article
@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):

    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article["title"]
    form.body.data = article["body"]

    if request.method == "POST" and form.validate():
        title = request.form["title"]
        body = request.form["body"]

        # Create Cursor

        cur = mysql.connection.cursor()

        # Execute CRUD
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()
        flash(" Article updated succesfully!", "success")
        return redirect(url_for("dashboard"))
   
    return render_template("edit_article.html", form=form)

# Delete Article
@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id=%s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash(" Article deleted succesfully!", "success")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":                                     # Run the application in  main
    app.secret_key="secret_1234"
    app.run()


