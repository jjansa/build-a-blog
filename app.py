from flask import Flask, request, redirect, render_template, session, escape, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, DDL
from sqlalchemy.event import listen
from datetime import datetime
import pymysql
from hashutils import make_pw_hash, check_pw_hash
from slugify import slugify
import os
from mimetypes import MimeTypes
# from urllib import request

app = Flask(__name__)
app.secret_key = b'1\x19\xca0\\\xe7\x84X\xb3\x03d/tR\x14\x88'
app.config["CACHE_TYPE"] = "null"
app.config['DEBUG'] =True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/lc1012019'
app.config['SQLALCHEMY_ECHO'] = True 
db = SQLAlchemy(app)

#Create function to get default values from other columns when needed
def same_as(column_name):
    def default_function(context):
        return context.get_current_parameters()[column_name]
    return default_function

def create_username(username):
    if username != '':
        return username
    else:
        return slugify(session.get('user').first_name +' ' + session.get('user').last_name)

def get_author_id(self):
    return session.get('user').id

def get_author(self):
    return session.get('user').first_name + ' ' + session.get('user').last_name

def get_publisher(self):
    return session.get('user').first_name + ' ' + session.get('user').last_name

def get_mime_type(media):
#get media file from the form input
    url = urllib.pathname2url('media[0]')
    return MimeTypes.guess_type(url)
      

class Blog_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(140), nullable=False)
    posts = db.relationship('Post', backref='blog_user', lazy=True)
    role = db.relationship('UserRoles', backref='user_roles')
  
    def __init__(self, email, password, first_name, last_name, username=''):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = make_pw_hash(password)
        self.username = create_username(username)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __init__(self, name):
        self.name = name


class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('blog__user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

    def __init__(self, user_id, role_id):
        self.user_id = user_id
        self.role_id = role_id

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('blog__user.id', ondelete='CASCADE'))
    login = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    def __init__(self, user_id):
        self.user_id = self.user_id


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('blog__user.id',  ondelete='CASCADE'), nullable=False,)
    content = db.Column(db.Text, nullable=False)
    post_status = db.Column(db.String(10), nullable=False, default='draft')
    post_type = db.Column(db.String(100))
    post_mime_type = db.Column(db.String(100))
    slug = db.Column(db.String(255), nullable=False)
    post_parent = db.Column(db.Integer, default=0, nullable=False)
    published_post = db.relationship('Published_Post', backref='published_posts', lazy=True)
    term_relationships = db.relationship('Term_Relationship', backref="post_terms", lazy=True)
    post_meta = db.relationship('Post_Meta', backref='postmeta', lazy=True)


    def __init__(self, title, content):
        self.title = title 
        self.author_id = get_author_id()
        self.content = content
        self.post_type = post_type
        self.post_mime_type = get_mime_type()
        self.slug = slugify(title)

    
class Published_Post(db.Model):
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'),  primary_key=True, nullable=False)
    published_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    published_by = db.Column(db.String(255), nullable=False)

    def __init__(self):
        self.published_by = get_publisher()

class Post_Meta(db.Model):
    __tablename__ = 'postmeta'
    meta_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    meta_key = db.Column(db.String(255),  nullable=False)
    meta_value = db.Column(db.Text, nullable=False)

    def __init__(self, post_id, meta_key, meta_value):
        self.post_id = post_id
        self.meta_key = meta_key
        self.meta_value = meta_value
        

class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    taxonomy_of_term = db.relationship('Term_Taxonomy', backref='term_taxonomy', lazy=True)

    def __init__(self, name):
        self.name = name
        self.slug = slugify(name)        

class Term_Taxonomy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    taxonomy = db.Column(db.String(255), nullable=False)       
    term_id = db.Column(db.Integer, db.ForeignKey('term.id',  ondelete='CASCADE'), nullable=False)
    terms_relationships = db.relationship('Term_Relationship', backref='terms_taxonomy_relationship', lazy=True)

    def __init__(self, taxonomy, term_id):
        self.taxonomy = taxonomy
        self.term_id = term_id

class Term_Relationship(db.Model):
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), primary_key=True, nullable=False)
    term_taxonomy_id = db.Column(db.Integer, db.ForeignKey('term__taxonomy.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    
    def __init__(self, post_id, term_taxonomy_id):
        self.post_id = post_id
        self.term_taxonomy_id = term_taxonomy_id

event.listen(Term.__table__, 'after_create', DDL(""" INSERT INTO term (id, name, slug) VALUE (1, 'Blog', 'blog'), (2, 'Event', 'event'), (3, 'Page', 'page'), (4, 'Post Tag', 'post-tag'), (5, 'Attachment', 'attachment'), (6, 'Slide', 'slide') """))
event.listen(Term_Taxonomy.__table__, 'after_create', DDL(""" INSERT INTO term__taxonomy (id, taxonomy, term_id)  VALUE (1, 'category', 1), (2, 'category', 2), (3, 'category', 3), (4, 'tag', 4), (5, 'category', 5), (6, 'category', 6) """))
event.listen(Role.__table__, 'after_create', DDL(""" INSERT INTO roles (id, name)  VALUE (1, 'admin'), (2, 'editior'), (3, 'author') """))




# @app.before_first_request
# def setup():
#     post = Term('Blog Post')
#     tag = Term('Post Tag')
#     page = Term('Page')
#     event = Term('Event Post')
#     db.session.add(post)
#     db.session.add(tag)
#     db.session.add(page)
#     db.session.add(event)
#     db.session.flush()
#     postTax = Term_Taxonomy('category', post.id)
#     tagTax = Term_Taxonomy('tag', tag.id)
#     pagTax = Term_Taxonomy('category', page.id)
#     eventTax = Term_Taxonomy('category', event.id)
#     db.session.add(postTax)
#     db.session.add(tagTax)
#     db.session.add(pagTax)
#     db.session.add(eventTax)
#     db.session.flush()
#     db.session.commit()

@app.route('/')
def home():
    return render_template('site/pages/index.html', title='Home')

@app.route('/blog.html')
def blog():
    return render_template('site/pages/blog.html', title="Blog")

@app.route('/post/<int:post_id>')
def show_post(post_id):
    return

@app.route('/admin')
def admin():
    if 'user' in session:
        return render_template('/admin/dash/dash.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'authenticated' in session:
        return jsonify({'success': 1})
    else:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            if email != "" and password !="":
                user = Blog_User.query.filter_by(email=email).first()
                if user:
                    if check_pw_hash(password, user.password):
                        session['authenticated'] = True
                        session['user'] = user
                        return jsonify({'success': 2, 'message': '', 'alertType': 'success'})
                    else: 
                        return jsonify({'error': 1, 'message': 'Invalid email or password', 'alertType': 'error' })
                else:
                    return jsonify({'error': 2, 'message': 'That user does not exist. Please, register.', 'alertType': 'error' })
            else:
                return jsonify({'error': 3, 'message': 'Email and password are required.', 'alertType': 'error'})
        filterColor = 'purple' 
        return render_template('admin/auth/pages/login.html', reg_link="/register", log_link="/login", lock_link="/lock", filter_color = filterColor)


@app.route('/register')
def register():
    return render_template('admin/auth/pages/register.html')

@app.route("/lock")
def lock():
    return render_template("admin/auth/pages/lock.html")

@app.route('/logout')
def logout():
    return

@app.route('/admin/dash/add_post')
def make_posts():
    if 'user' in session:
        #new_post=Post(title, author, content, date, categorey, tags, post_type)
        return



if (__name__) == '__main__':
    #db.create_all()
    app.run()
