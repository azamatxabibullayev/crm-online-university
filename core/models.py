from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from university_crm import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    teachers = models.ManyToManyField(User, limit_choices_to={'role': 'teacher'}, related_name='courses')

    def __str__(self):
        return self.name


class Attendance(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    date = models.DateField()
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ('course', 'student', 'date')

    def __str__(self):
        return f"{self.student.username} - {self.course.name} on {self.date}: {'Present' if self.present else 'Absent'}"


class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notices')
    target_role = models.CharField(max_length=10,
                                   choices=[('student', 'Student'), ('teacher', 'Teacher'), ('all', 'All')],
                                   default='all')

    def __str__(self):
        return self.title


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})

    def __str__(self):
        return f"{self.title} - {self.course.name}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    grade = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student.username} submission for {self.assignment.title}"


class LeaveRequest(models.Model):
    LEAVE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=LEAVE_STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='reviewed_leaves')

    def __str__(self):
        return f"{self.user.username} leave from {self.start_date} to {self.end_date} ({self.status})"

    class Meta:
        ordering = ['-submitted_at']


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    target_roles = models.CharField(
        max_length=50,
        choices=[
            ('all', 'All Users'),
            ('students', 'Students Only'),
            ('teachers', 'Teachers Only'),
            ('admins', 'Admins Only'),
        ],
        default='all',
    )

    def __str__(self):
        return self.title


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)  # for moderation
    is_tagged = models.BooleanField(default=False)  # flagged by admin

    def __str__(self):
        return f"Message {self.id} by {self.sender.username}"


class Timetable(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.course.name} - {self.day_of_week} ({self.start_time} to {self.end_time})"


class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    score = models.FloatField()
    max_score = models.FloatField(default=100)
    graded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='graded_items')
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course', 'title')

    def __str__(self):
        return f"{self.student.username} - {self.course.name} - {self.title}: {self.score}/{self.max_score}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    document = models.FileField(upload_to='user_documents/', blank=True, null=True)
    bio = models.TextField(blank=True)



    def __str__(self):
        return f"Profile of {self.user.username}"
