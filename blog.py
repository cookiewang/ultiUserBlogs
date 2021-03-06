import os
import re
import random
import hashlib
import hmac
from string import letters
import webapp2
import jinja2
import model

from google.appengine.ext import db


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'fart'

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)


##### user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


##### blog stuff

# This class is a handler of adding likes
class LikePost(BlogHandler):
  
    def get(self, post_id):
        # if not login, redirect to login page
        if not self.user:
            self.redirect("/login")
            return
        # retrieve the post by its post Id
        post = model.GetPostById(post_id)
        # only different user and only first time to select like 
        if post and post.author != self.user.name and not model.isExisted(post, self.user.name):
            model.AddLike(post_id)
            message = "One like was added successfully."
            self.render("result.html", message=message)
        else:
            if model.isExisted(post, self.user.name): # if selected like before, error out
                error = "You're only allowed to like others' blog once."
            else:               
                error = "You're only allowed to like others' blog."
            self.render("error.html", error=error)

# This class is to retrieve all the posts
class QueryHandler(BlogHandler):
   
     def get(self):
        # if not login, redirect to login page
        if not self.user:
            self.redirect("/login")
            return
        # retrieve all the posts
        posts = model.Post.query_posts()
        self.render('front.html', posts = posts)

# This class is to retrieve one post baesd on its post Id
class PostBlog(BlogHandler):
   
     def get(self, post_id):
        # if not login, redirect to login page
        if not self.user:
            self.redirect("/login")
            return

        if post_id != '0':
            post = model.GetPostById(post_id)
            if not post:
                self.error(404)
                return
             
            self.render("permalink.html", post = post)
            return

# This class creates a new post
class CreateNewPost(BlogHandler):
     def get(self):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         self.render("newpost.html", title='New Post')

     def post(self):
         # if not login, redirect to login page
         if not self.user:
             self.redirect('/login')
             return
         subject = self.request.get('subject')
         content = self.request.get('content')
         title = "New Post"
         if subject and content:
             post = model.InsertPost(self.user.name, subject, content)
             message = "A new post with Id %d was created successfully. " % post.key.integer_id()
             self.render("result.html", message=message)
         else:
             error = "subject and content, please!"
             self.render("newpost.html", title=title, subject=subject, content=content, error=error)

# This class is to update an existing post
class EditPost(BlogHandler):
     def get(self, post_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return

         post = model.GetPostById(post_id)
         if post.author == self.user.name: # only same user can edit the post
             subject = post.subject
             content = post.content
             self.render("newpost.html", title='Edit Post', subject=subject, content=content, error="")
         else:
             self.error(403)
             error = "You're not allowed to edit others' blog."
             self.render("error.html", error=error)
             return

     def post(self, post_id):
         # if not login, redirect to login page
         if not self.user:
             self.redirect('/login')
             return
         subject = self.request.get('subject')
         content = self.request.get('content')
         post = model.GetPostById(post_id)
         if not post or post.author != self.user.name: # only same user can edit the post
             self.error(403)
             error = "You're not allowed to edit others' blog."
             self.render("error.html", error=error)
             return

         title = "Edit Post"
         if subject and content:
             post = model.UpdatePost(post_id, subject, content)
             message = "A post with Id %d was edited successfully. " % post.key.integer_id()
             self.render("result.html", message=message)
         else:
             error = "subject and content, please!"
             self.render("newpost.html", title=title, subject=subject, content=content, error=error)

# This class is to delete an existing post
class DeletePost(BlogHandler):
     def get(self, post_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return

         post = model.GetPostById(post_id)
         if post.author == self.user.name: # only same user can delete the post
             self.render("deleteConfirm.html", title='Delete Post', id=post_id)
         else:
             self.error(403)
             error = "You're not allowed to delete others' blog."
             self.render("error.html", error=error)
         return

     def post(self, post_id):
         # if not login, redirect to login page
         if not self.user:
             self.redirect('/login')
             return
         post = model.GetPostById(post_id)
         if not post or post.author != self.user.name: # only same user can delete the post
             self.error(403)
             error = "You're not allowed to delete others' blog."
             self.render("error.html", error=error)
             return

         model.DeletePost(post_id)
         message = "One blog was deleted successfully."
         self.render("result.html", message=message)

# This class is to create a new comment
class CreateNewComment(BlogHandler):
     
     def get(self, post_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         post = model.GetPostById(post_id)
         if post.author == self.user.name: # only different user can add a comment
             error = "You're not allowed to write a comment for your blog."
             self.render("error.html", error=error)
         else:
             self.render("newcomment.html", title='New Comment')
         return

     def post(self, post_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         post = model.GetPostById(post_id)
         if post.author == self.user.name: # only different user can add a comment
             error = "You're not allowed to write a comment for your blog."
             self.render("error.html", error=error)
             return
         content = self.request.get('content')
         comment = model.InsertComment(self.user.name, content)
         model.addCommentToPost(post_id, comment.key.integer_id())
         message = "A new comment with Id %d was created successfully. " % comment.key.integer_id()
         self.render("result.html", message=message)

# This class is to update an existing comment
class UpdateComment(BlogHandler):
     def get(self, comment_id='0'):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         comment = model.GetCommentById(comment_id)
         if comment.author == self.user.name:   # only same user can update the comment
             content = comment.content
             self.render("newcomment.html", title='Edit Comment', content=content, error="")
         else:
             error = "You're not allowed to edit others' comment."
             self.render("error.html", error=error)

         return

     def post(self, comment_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         comment = model.GetCommentById(comment_id)
         if not comment or comment.author != self.user.name:  # must be the same user to update the comment
             error = "You're not allowed to edit others' comment."
             self.render("error.html", error=error)
             return
         content = self.request.get('content')
         if content:
             comment = model.UpdateComment(comment_id, content)
             message = "A comment with Id %d was edited successfully. " % comment.key.integer_id()
             self.render("result.html", message=message)
         else:
             error = "Content, please!"
             self.render("newcomment.html", title='Edit Comment', content=content, error=error)
         
         return

# This class deletes an existing comment
class DeleteComment(BlogHandler):
     def get(self, post_id, comment_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         comment = model.GetCommentById(comment_id)
         if comment.author == self.user.name: # only same user can delete the comment
             self.render("deleteCommentConfirm.html", title='Delete Comment', id=comment_id)
         else:
             error = "You're not allowed to delete others' comment."
             self.render("error.html", error=error)
 
         return            

     def post(self, post_id, comment_id):
         # if not login, redirect to login page
         if not self.user:
            self.redirect("/login")
            return
         comment = model.GetCommentById(comment_id)
         if not comment or comment.author != self.user.name: # must be the same user to delete the comment
             error = "You're not allowed to delete others' comment."
             self.render("error.html", error=error)
             return
         comment = model.DeleteComment(comment_id)
         model.RemoveCommentToPost(post_id, comment_id)
         message = "A comment with Id %s was deleted successfully. " % comment_id
         self.render("result.html", message=message)
         return

###### Unit 2 Hr's

class Rot13(BlogHandler):
    def get(self):
        self.render('rot13-form.html')

    def post(self):
        rot13 = ''
        text = self.request.get('text')
        if text:
            rot13 = text.encode('rot13')

        self.render('rot13-form.html', text = rot13)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Unit2Signup(Signup):
    def done(self):
        self.redirect('/unit2/welcome?username=' + self.username)

class Register(Signup):
    def done(self):
        # make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/blog')

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/blog')

class Unit3Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            self.redirect('/signup')

class Welcome(BlogHandler):
    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username = username)
        else:
            self.redirect('/unit2/signup')

app = webapp2.WSGIApplication([('/', QueryHandler),
                               ('/unit2/rot13', Rot13),
                               ('/unit2/signup', Unit2Signup),
                               ('/unit2/welcome', Welcome),
                               ('/blog/?', QueryHandler),
                               ('/blog/newpost',CreateNewPost),
                               ('/blog/EditPost/([0-9]+)', EditPost),
                               ('/blog/DeletePost/([0-9]+)', DeletePost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/unit3/welcome', Unit3Welcome),
                               ('/blog/like/([0-9]+)',LikePost),
                               ('/blog/([0-9]+)',PostBlog),
                               ('/blog/new-comment/([0-9]+)',CreateNewComment),
                               ('/blog/comment-edit/([0-9]+)',UpdateComment),
                               ('/blog/comment-delete/([0-9]+)/([0-9]+)', DeleteComment),
                               ],
                              debug=True)
