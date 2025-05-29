from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import TeacherSignupForm, StudentSignupForm, LeaveRequestForm, AnnouncementForm, LeaveRequest, TimetableForm, MessageForm, GradeForm, ProfileForm
from .models import User, Attendance, Course, Notice, Assignment, Submission, Announcement, Message, Conversation, Timetable, Grade, Profile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.core.files.storage import FileSystemStorage
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json


def home(request):
    return render(request, 'core/home.html')


def signup_teacher(request):
    if request.method == 'POST':
        form = TeacherSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('home')
    else:
        form = TeacherSignupForm()
    return render(request, 'core/signup.html', {'form': form, 'user_type': 'Teacher'})


def signup_student(request):
    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('home')
    else:
        form = StudentSignupForm()
    return render(request, 'core/signup.html', {'form': form, 'user_type': 'Student'})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def admin_dashboard(request):
    pending_teachers = User.objects.filter(role='teacher', is_approved=False)
    pending_students = User.objects.filter(role='student', is_approved=False)
    return render(request, 'core/admin_dashboard.html', {
        'teachers': pending_teachers,
        'students': pending_students
    })


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def approve_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_approved = True
    user.save()
    return redirect('admin_dashboard')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_approved:
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'teacher':
                    return redirect('teacher_dashboard')
                elif user.role == 'student':
                    return redirect('student_dashboard')
            else:
                messages.error(request, 'Your account is not yet approved.')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def teacher_dashboard(request):
    return render(request, 'core/teacher_dashboard.html')


@login_required
@user_passes_test(lambda u: u.role == 'student')
def student_dashboard(request):
    return render(request, 'core/student_dashboard.html')


@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def mark_attendance(request):
    courses = request.user.courses.all()
    if request.method == 'POST':
        course_id = request.POST.get('course')
        date_str = request.POST.get('date')
        date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        student_ids = request.POST.getlist('students')

        course = Course.objects.get(id=course_id)
        for student in course.students_set.all():
            present = str(student.id) in student_ids
            Attendance.objects.update_or_create(course=course, student=student, date=date,
                                                defaults={'present': present})

        return redirect('teacher_dashboard')

    else:
        return render(request, 'core/mark_attendance.html', {'courses': courses})


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'teacher'])
def post_notice(request):
    if request.method == 'POST':
        title = request.POST['title']
        content = request.POST['content']
        target_role = request.POST['target_role']
        Notice.objects.create(title=title, content=content, author=request.user, target_role=target_role)
        return redirect('dashboard')  # redirect based on role or home
    return render(request, 'core/post_notice.html')


@login_required
@user_passes_test(lambda u: u.role == 'student')
def student_dashboard(request):
    notices = Notice.objects.filter(target_role__in=['student', 'all']).order_by('-created_at')
    attendance = Attendance.objects.filter(student=request.user)
    return render(request, 'core/student_dashboard.html', {'notices': notices, 'attendance': attendance})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'core/course_list.html', {'courses': courses})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def course_create(request):
    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']
        course = Course.objects.create(name=name, description=description)
        return redirect('course_list')
    return render(request, 'core/course_form.html')


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def course_edit(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        course.name = request.POST['name']
        course.description = request.POST['description']
        course.save()
        return redirect('course_list')
    return render(request, 'core/course_form.html', {'course': course})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    return redirect('course_list')


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def course_edit(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    teachers = User.objects.filter(role='teacher')
    if request.method == 'POST':
        course.name = request.POST['name']
        course.description = request.POST['description']
        course.teachers.set(request.POST.getlist('teachers'))
        course.save()
        return redirect('course_list')
    return render(request, 'core/course_form.html', {'course': course, 'teachers': teachers})


@login_required
@user_passes_test(lambda u: u.role == 'student')
def course_list_student(request):
    courses = Course.objects.all()
    enrolled_courses = request.user.enrolled_courses.all()
    return render(request, 'core/course_list_student.html', {'courses': courses, 'enrolled_courses': enrolled_courses})


@login_required
@user_passes_test(lambda u: u.role == 'student')
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.students.add(request.user)
    return redirect('course_list_student')


@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def assignment_create(request):
    courses = request.user.courses.all()
    if request.method == 'POST':
        course_id = request.POST['course']
        title = request.POST['title']
        description = request.POST['description']
        deadline = request.POST['deadline']

        course = Course.objects.get(id=course_id)
        Assignment.objects.create(course=course, title=title, description=description, deadline=deadline,
                                  teacher=request.user)
        return redirect('teacher_dashboard')

    return render(request, 'core/assignment_form.html', {'courses': courses})


@login_required
@user_passes_test(lambda u: u.role == 'student')
def assignment_list_student(request):
    assignments = Assignment.objects.filter(course__students=request.user)
    submissions = Submission.objects.filter(student=request.user)
    submitted_assignments = {sub.assignment.id for sub in submissions}
    return render(request, 'core/assignment_list_student.html',
                  {'assignments': assignments, 'submitted_assignments': submitted_assignments})


@login_required
@user_passes_test(lambda u: u.role == 'student')
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        Submission.objects.update_or_create(assignment=assignment, student=request.user, defaults={'file': file})
        return redirect('assignment_list_student')

    return render(request, 'core/submit_assignment.html', {'assignment': assignment})


@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def submission_list(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
    submissions = Submission.objects.filter(assignment=assignment)
    return render(request, 'core/submission_list.html', {'assignment': assignment, 'submissions': submissions})


@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, assignment__teacher=request.user)
    if request.method == 'POST':
        grade = request.POST.get('grade')
        if grade:
            submission.grade = float(grade)
            submission.graded = True
            submission.save()
            return redirect('submission_list', assignment_id=submission.assignment.id)
    return render(request, 'core/grade_submission.html', {'submission': submission})


@login_required
@user_passes_test(lambda u: u.role == 'student')
def student_grades(request):
    submissions = Submission.objects.filter(student=request.user, graded=True).select_related('assignment',
                                                                                              'assignment__course')
    return render(request, 'core/student_grades.html', {'submissions': submissions})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def all_grades(request):
    submissions = Submission.objects.filter(graded=True).select_related('student', 'assignment', 'assignment__course')
    return render(request, 'core/all_grades.html', {'submissions': submissions})


@login_required
def leave_request_create(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_req = form.save(commit=False)
            leave_req.user = request.user
            leave_req.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('leave_requests')
    else:
        form = LeaveRequestForm()
    return render(request, 'core/leave_request_form.html', {'form': form})


@login_required
def leave_requests(request):
    # Show user their own leave requests
    leaves = LeaveRequest.objects.filter(user=request.user)
    return render(request, 'core/leave_requests_list.html', {'leaves': leaves})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def admin_leave_requests(request):
    leaves = LeaveRequest.objects.filter(status='pending')
    return render(request, 'core/admin_leave_requests.html', {'leaves': leaves})


@login_required
@user_passes_test(lambda u: u.role == 'admin')
def leave_request_review(request, leave_id, action):
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    if action not in ['approve', 'reject']:
        messages.error(request, "Invalid action.")
        return redirect('admin_leave_requests')
    if leave.status != 'pending':
        messages.warning(request, "This leave request has already been reviewed.")
        return redirect('admin_leave_requests')

    leave.status = 'approved' if action == 'approve' else 'rejected'
    leave.reviewed_at = timezone.now()
    leave.reviewed_by = request.user
    leave.save()
    messages.success(request, f"Leave request {leave.status}.")
    return redirect('admin_leave_requests')


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'teacher'])
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()

            # Send notification via channels
            channel_layer = get_channel_layer()

            # Prepare notification data
            notification = {
                'type': 'new_announcement',
                'title': announcement.title,
                'content': announcement.content,
                'target_roles': announcement.target_roles,
                'created_at': announcement.created_at.isoformat(),
            }

            # Send message to group 'notifications'
            async_to_sync(channel_layer.group_send)(
                'notifications',  # group name
                {
                    'type': 'send_notification',
                    'message': json.dumps(notification),
                }
            )

            messages.success(request, "Announcement created and notification sent.")
            return redirect('announcements_list')
    else:
        form = AnnouncementForm()
    return render(request, 'core/announcement_form.html', {'form': form})


@login_required
def announcements_list(request):
    # Show announcements visible to this user based on role or all
    announcements = Announcement.objects.filter(
        target_roles__in=['all', request.user.role]
    ).order_by('-created_at')
    return render(request, 'core/announcements_list.html', {'announcements': announcements})


@login_required
def conversation_list(request):
    # Show all conversations user is part of
    conversations = request.user.conversations.all().order_by('-created_at')
    return render(request, 'core/conversation_list.html', {'conversations': conversations})


@login_required
def conversation_detail(request, conv_id):
    conversation = get_object_or_404(Conversation, id=conv_id)
    if request.user not in conversation.participants.all():
        return HttpResponseForbidden("You are not a participant in this conversation.")

    messages = conversation.messages.filter(is_deleted=False).order_by('timestamp')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            return redirect('conversation_detail', conv_id=conv_id)
    else:
        form = MessageForm()

    return render(request, 'core/conversation_detail.html',
                  {'conversation': conversation, 'messages': messages, 'form': form})


@login_required
def start_conversation(request, user_id):
    # Start or get conversation between request.user and user_id
    other_user = get_object_or_404(User, id=user_id)
    if request.user == other_user:
        messages.error(request, "Cannot start conversation with yourself.")
        return redirect('conversation_list')

    # Check if conversation exists with these two participants
    conversations = Conversation.objects.filter(participants=request.user).filter(participants=other_user)
    if conversations.exists():
        conversation = conversations.first()
    else:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        conversation.save()

    return redirect('conversation_detail', conv_id=conversation.id)


# Admin moderation views

from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def moderate_messages(request):
    messages = Message.objects.filter(is_deleted=False).order_by('-timestamp')[:100]
    return render(request, 'core/moderate_messages.html', {'messages': messages})


@staff_member_required
def delete_message(request, msg_id):
    message = get_object_or_404(Message, id=msg_id)
    message.is_deleted = True
    message.save()
    return redirect('moderate_messages')


@staff_member_required
def tag_message(request, msg_id):
    message = get_object_or_404(Message, id=msg_id)
    message.is_tagged = not message.is_tagged
    message.save()
    return redirect('moderate_messages')


@login_required
def upload_timetable(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    if request.method == 'POST':
        form = TimetableForm(request.POST)
        if form.is_valid():
            timetable = form.save(commit=False)
            timetable.teacher = request.user
            timetable.save()
            return redirect('view_timetable')
    else:
        form = TimetableForm()

    return render(request, 'timetable/upload_timetable.html', {'form': form})


@login_required
def view_timetable(request):
    if request.user.role == 'teacher':
        timetables = Timetable.objects.filter(teacher=request.user)
    elif request.user.role == 'student':
        student_courses = request.user.courses.all()
        timetables = Timetable.objects.filter(course__in=student_courses)
    else:
        timetables = Timetable.objects.all()

    return render(request, 'timetable/view_timetable.html', {'timetables': timetables})

@login_required
def grade_list(request):
    user = request.user
    if user.role == 'teacher':
        grades = Grade.objects.filter(graded_by=user).order_by('-graded_at')
    elif user.role == 'student':
        grades = Grade.objects.filter(student=user).order_by('-graded_at')
    else:
        # admins see all grades
        grades = Grade.objects.all().order_by('-graded_at')
    return render(request, 'grades/grade_list.html', {'grades': grades})


@login_required
def grade_create(request):
    if request.user.role != 'teacher':
        messages.error(request, "Only teachers can add grades.")
        return redirect('grade_list')

    if request.method == 'POST':
        form = GradeForm(request.POST, teacher=request.user)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.graded_by = request.user
            grade.save()
            messages.success(request, "Grade created successfully.")
            return redirect('grade_list')
    else:
        form = GradeForm(teacher=request.user)

    return render(request, 'grades/grade_form.html', {'form': form, 'action': 'Create'})


@login_required
def grade_update(request, pk):
    grade = get_object_or_404(Grade, pk=pk)

    if request.user.role != 'teacher' or grade.graded_by != request.user:
        messages.error(request, "You are not authorized to edit this grade.")
        return redirect('grade_list')

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Grade updated successfully.")
            return redirect('grade_list')
    else:
        form = GradeForm(instance=grade, teacher=request.user)

    return render(request, 'grades/grade_form.html', {'form': form, 'action': 'Update'})

@login_required
def profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile.html', {'form': form})