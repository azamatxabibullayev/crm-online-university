from django.db import models
from django.contrib.auth.models import User
import os

def path_and_rename(instance, filename):
    upload_to = 'Images/'
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = 'User_Profile_Pictures/{}.{}'.format(instance.pk, ext)
    return os.path.join(upload_to, filename)

# Create your models here.
class user_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    bio = models.CharField(max_length=150, blank=True)
    profile_Pic = models.ImageField(upload_to=path_and_rename, verbose_name="Profile Picture", blank=True)

    teacher = 'teacher'
    student = 'student'
    parent = 'parent'
    user_types = [
        (teacher, 'teacher'),
        (student, 'student'),
        (parent, 'parent'),
    ]
    user_type = models.CharField(max_length=10, choices=user_types, default=student)

    def __str__(self):
        return self.user.username
