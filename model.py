import os
from google.appengine.ext import ndb
import jinja2


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def comment_key(name = 'default'):
    return ndb.Key('comments', name)

def post_key(name = 'default'):
    return ndb.Key('posts', name)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class Post(ndb.Model):
    author = ndb.TextProperty()
    user_names = ndb.StringProperty(repeated=True)
    comment_ids = ndb.IntegerProperty(repeated=True)
    subject = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)
    last_modified = ndb.DateTimeProperty(auto_now = True)
    like_num = ndb.IntegerProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

    @classmethod
    def getCommentById(self, comment_id, post_id):
        comment = GetCommentById(comment_id)
        if comment is not None:
            return comment.render(post_id)
        else:
            return "" 
    @classmethod
    def query_posts(cls):
        return cls.query(ancestor=post_key()).order(-cls.created)


class Comment(ndb.Model):
    author = ndb.TextProperty()
    content = ndb.TextProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)
    last_modified = ndb.DateTimeProperty(auto_now = True)

    def render(self, post_id):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("comment.html", c=self, postId=post_id)

    @classmethod
    def query_comments(cls):
        return cls.query(ancestor=comment_key()).order(-cls.created)

def InsertComment(author, content):
    comment = Comment(parent=comment_key(), author=author, content=content)
    comment.put()
    return comment

def GetCommentById(id):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    return key.get()

def UpdateComment(id, content):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    comment = key.get()
    comment.content = content
    comment.put()
    return comment

def addCommentToPost(post_id, comment_id):
    post = GetPostById(post_id)
    post.comment_ids.append(comment_id)
    post.put()

def RemoveCommentToPost(post_id, comment_id):
    post = GetPostById(post_id)
    post.comment_ids.remove(int(comment_id))
    post.put()

def DeleteComment(id):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    key.delete()

def isExisted(post, name):
    if name in post.user_names:
        return True
    else:
        post.user_names.append(name)
        post.put()
        return False


def GetPostById(id):
    key = ndb.Key('Post', int(id), parent=post_key())
    return key.get()    

def AddLike(id):
    key = ndb.Key('Post', int(id), parent=post_key())
    post = key.get()
    post.like_num = post.like_num + 1
    post.put()
    return post

def UpdatePost(id, subject, content):
    key = ndb.Key('Post', int(id), parent=post_key())
    post = key.get()
    post.subject = subject
    post.content = content
    post.put()
    return post


def InsertPost(author,subject,content):
    post = Post(parent=post_key(), author=author, subject=subject, content=content, like_num=0)
    post.put()
    return post


def DeletePost(id):
    key = ndb.Key('Post', int(id), parent=post_key())
    key.delete()
