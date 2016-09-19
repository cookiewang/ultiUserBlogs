import os
from google.appengine.ext import ndb
import jinja2


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


def comment_key(name = 'default'):
    return ndb.Key('comments', name)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


class Comment(ndb.Model):
    author = ndb.TextProperty()
    user_names = ndb.StringProperty(repeated=True)
    subject = ndb.StringProperty(required = True)
    content = ndb.TextProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)
    last_modified = ndb.DateTimeProperty(auto_now = True)
    like_num = ndb.IntegerProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

    @classmethod
    def query_comments(cls):
        return cls.query(ancestor=comment_key()).order(-cls.created)

def isExisted(comment, name):
    if name in comment.user_names:
        return True
    else:
        comment.user_names.append(name)
        comment.put()
        return False


def GetCommentById(id):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    return key.get()    

def AddLike(id):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    comment = key.get()
    comment.like_num = comment.like_num + 1
    comment.put()
    return comment

def UpdateComment(id, subject, content):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    comment = key.get()
    comment.subject = subject
    comment.content = content
    comment.put()
    return comment


def InsertComment(author,subject,content):
    comment = Comment(parent=comment_key(), author=author, subject=subject, content=content, like_num=0)
    comment.put()
    return comment


def DeleteComment(id):
    key = ndb.Key('Comment', int(id), parent=comment_key())
    key.delete()
