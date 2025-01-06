import sys

try:
    from django.db import models
except Exception:
    print('Exception: Django Not Found, please install it with "pip install django".')
    sys.exit()


# Sample User model
class User(models.Model):
    # name = models.CharField(max_length=50, default="Dan")
    email = models.EmailField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=50)
    content = models.TextField(null=True)

    def __str__(self):
        return f"<{self.user.email}|{self.role}|{self.timestamp}>"
