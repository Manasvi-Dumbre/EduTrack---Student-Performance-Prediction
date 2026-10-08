import json
import os
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


from . import data_service

def student_home(request):
    # Only load data for the currently logged-in student
    user_email = request.user.email if hasattr(request.user, 'email') and request.user.email else None
    identifier = user_email

    # Look up the database profile before resolving the JSON dashboard record.
    db_student = None
    try:
        db_student = Student.objects.filter(admin=request.user).first()
    except Exception:
        pass

    if db_student and not data_service.get_student_by_email_or_id(identifier):
        full_name = db_student.admin.get_full_name().strip().casefold()
        matching_student = next(
            (student for student in data_service.get_all_students()
             if student.get('name', '').strip().casefold() == full_name),
            None
        )
        if matching_student:
            identifier = matching_student.get('student_id')

    filters = {
        'academic_year': request.GET.get('academic_year', '2025-2026'),
        'quarter': request.GET.get('quarter', 'all'),
        'month': request.GET.get('month', 'all'),
        'subject': request.GET.get('subject', 'all'),
        'date_range': request.GET.get('date_range', '')
    }

    dashboard_data = data_service.get_student_dashboard_data(identifier, filters)
    
    context = {
        'page_title': 'Student Academic Performance Dashboard',
        'data': dashboard_data,
        'student': dashboard_data.get('student', {}),
        'all_students': dashboard_data.get('all_students', []),
        'assessments': dashboard_data.get('assessments', []),
        'subjects': dashboard_data.get('subjects', []),
        'attendance_records': dashboard_data.get('attendance_records', {}),
        'assignments': dashboard_data.get('assignments', []),
        'feedback': dashboard_data.get('feedback', []),
        'performance_history': dashboard_data.get('performance_history', {}),
        'notifications': dashboard_data.get('notifications', []),
        'academic_calendar': dashboard_data.get('academic_calendar', []),
        'strengths': dashboard_data.get('strengths', []),
        'weaknesses': dashboard_data.get('weaknesses', []),
        'insights': dashboard_data.get('insights', []),
        'next_steps': dashboard_data.get('next_steps', []),
        'timeline_events': dashboard_data.get('timeline_events', []),
        'active_filters': filters,
        'db_student': db_student
    }
    return render(request, 'student_template/erpnext_student_home.html', context)


@csrf_exempt
def filter_student_dashboard(request):
    if request.method in ['GET', 'POST']:
        data_source = request.POST if request.method == 'POST' else request.GET
        student_id = data_source.get('student_id') or (request.user.email if hasattr(request.user, 'email') and request.user.email else 'studentone@student.com')
        filters = {
            'academic_year': data_source.get('academic_year', '2025-2026'),
            'quarter': data_source.get('quarter', 'all'),
            'month': data_source.get('month', 'all'),
            'subject': data_source.get('subject', 'all'),
            'date_range': data_source.get('date_range', '')
        }
        dashboard_data = data_service.get_student_dashboard_data(student_id, filters)
        return JsonResponse({'status': 'success', 'data': dashboard_data})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student)
    context = {
        'results': results,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)


#library

def view_books(request):
    books = Book.objects.all()
    context = {
        'books': books,
        'page_title': "Library"
    }
    return render(request, "student_template/view_books.html", context)


def seed_default_assignments_if_needed():
    if Assignment.objects.count() == 0:
        sample_assignments = [
            {
                "title": "Data Structures & Algorithms Assignment",
                "description": "Implement Singly Linked List with insert and delete operations.",
                "subject_code": "DAA",
                "subject_name": "Design & Analysis of Algorithms",
                "due_date": "2026-10-25"
            },
            {
                "title": "Software Testing & Quality Assurance Test Suite",
                "description": "Design comprehensive Selenium test scripts and generate execution report.",
                "subject_code": "STQA",
                "subject_name": "Software Testing & Quality Assurance",
                "due_date": "2026-10-28"
            },
            {
                "title": "Blockchain Technology Smart Contract Development",
                "description": "Develop Solidity smart contract for decentralized student credential verification.",
                "subject_code": "BT",
                "subject_name": "Blockchain Technology",
                "due_date": "2026-11-05"
            },
            {
                "title": "Object Oriented Modeling & Design UML Diagrams",
                "description": "Construct UML Class, Sequence, and State Machine diagrams for ERP System.",
                "subject_code": "OOMD",
                "subject_name": "Object Oriented Modeling & Design",
                "due_date": "2026-11-10"
            },
            {
                "title": "Machine Learning Model Training & Evaluation",
                "description": "Train and evaluate Random Forest model on student performance dataset.",
                "subject_code": "ML",
                "subject_name": "Machine Learning",
                "due_date": "2026-11-15"
            }
        ]
        for item in sample_assignments:
            Assignment.objects.create(**item)


def student_assignments(request):
    try:
        student = get_object_or_404(Student, admin=request.user)
    except Exception:
        student = None

    seed_default_assignments_if_needed()
    assignments_list = Assignment.objects.all().order_by('due_date')

    today = datetime.now().date()
    assignment_items = []

    # Subject badge styles
    subject_badges = {
        'DAA': {'bg': '#eff6ff', 'color': '#2563eb', 'border': '#bfdbfe'},
        'STQA': {'bg': '#f0fdf4', 'color': '#16a34a', 'border': '#bbf7d0'},
        'BT': {'bg': '#fef3c7', 'color': '#d97706', 'border': '#fde68a'},
        'OOMD': {'bg': '#faf5ff', 'color': '#9333ea', 'border': '#e9d5ff'},
        'ML': {'bg': '#fff1f2', 'color': '#e11d48', 'border': '#fecdd3'},
    }

    pdf_files = {
        'DAA': 'image/ASSIGNMENTS_DAA.pdf',
        'STQA': 'image/ASSIGNMENTS_STQA.pdf',
        'BT': 'image/ASSIGNMENTS_BT.pdf',
        'OOMD': 'image/ASSIGNMENTS_OOMD.pdf',
        'ML': 'image/ASSIGNMENTS_ML.pdf',
    }

    for ass in assignments_list:
        sub = None
        if student:
            sub = AssignmentSubmission.objects.filter(assignment=ass, student=student).first()

        if sub:
            status = 'Submitted'
            status_badge_class = 'bg-success-light text-success'
        elif ass.due_date < today:
            status = 'Overdue'
            status_badge_class = 'bg-danger-light text-danger'
        else:
            status = 'Pending'
            status_badge_class = 'bg-warning-light text-warning'

        badge_info = subject_badges.get(ass.subject_code, {'bg': '#f1f5f9', 'color': '#475569', 'border': '#cbd5e1'})
        pdf_rel = pdf_files.get(ass.subject_code, 'image/ASSIGNMENTS_1 BT.pdf')

        assignment_items.append({
            'assignment': ass,
            'submission': sub,
            'status': status,
            'status_badge_class': status_badge_class,
            'badge_info': badge_info,
            'pdf_rel': pdf_rel,
            'is_overdue': ass.due_date < today and not sub,
        })

    context = {
        'page_title': 'Assignments',
        'assignment_items': assignment_items,
        'today': today
    }
    return render(request, 'student_template/student_assignments.html', context)


def upload_assignment_submission(request, assignment_id):
    if request.method == 'POST':
        assignment = get_object_or_404(Assignment, id=assignment_id)
        try:
            student = Student.objects.get(admin=request.user)
        except Student.DoesNotExist:
            messages.error(request, "Student record not found!")
            return redirect('student_assignments')

        uploaded_file = request.FILES.get('submission_file')
        if not uploaded_file:
            messages.error(request, "Please select a file to upload.")
            return redirect('student_assignments')

        # Allowed file formats: PDF, DOC, DOCX, PPT, PPTX, ZIP
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.zip']
        if ext not in allowed_exts:
            messages.error(request, "Invalid file format! Allowed formats: PDF, DOC, DOCX, PPT, PPTX, ZIP.")
            return redirect('student_assignments')

        fs = FileSystemStorage()
        saved_name = fs.save(f"assignments/{uploaded_file.name}", uploaded_file)

        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=student
        )
        submission.file = saved_name
        submission.filename = uploaded_file.name
        submission.status = 'Submitted'
        submission.save()

        messages.success(request, f"Successfully uploaded '{uploaded_file.name}' for {assignment.title}!")
        return redirect('student_assignments')

    return redirect('student_assignments')


def student_timetable(request):
    """Render the class timetable page for students, loading teacher data from JSON."""
    teachers = []
    try:
        teachers_json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'teachers.json'
        )
        with open(teachers_json_path, 'r', encoding='utf-8') as f:
            teachers = json.load(f)
    except Exception:
        pass

    context = {
        'page_title': 'Class Timetable',
        'teachers': teachers,
    }
    return render(request, 'student_template/student_timetable.html', context)
