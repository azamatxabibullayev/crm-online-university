from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Announcement, LeaveRequest, Message, Timetable, Grade, Profile


class TeacherSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        user.is_active = True
        user.is_approved = False
        if commit:
            user.save()
        return user


class StudentSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        user.is_active = True
        user.is_approved = False
        if commit:
            user.save()
        return user


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'target_roles']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'target_roles': forms.Select(attrs={'class': 'form-select'}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Type your message...'}),
        }


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['course', 'day_of_week', 'start_time', 'end_time']


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'course', 'title', 'score', 'max_score']

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

        # Filter courses to only those taught by this teacher
        if teacher:
            self.fields['course'].queryset = Course.objects.filter(teachers=teacher)

        # Filter students to those enrolled in the selected courses (or all students as fallback)
        self.fields['student'].queryset = User.objects.filter(role='student')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'document', 'bio']
