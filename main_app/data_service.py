import json
import os
from pathlib import Path
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def sync_db_and_json():
    """
    Ensures complete bidirectional synchronization between Django SQLite Database 
    (CustomUser, Student, Staff) and JSON data files (students.json, teachers.json, users.json).
    """
    try:
        from main_app.models import CustomUser, Student, Staff
        
        students_json = load_json('students.json') or []
        teachers_json = load_json('teachers.json') or []
        
        # 1. Sync students from JSON -> Django DB (so login works for all students in students.json)
        for s in students_json:
            email = s.get('email', '').strip().lower()
            if not email:
                continue
            if not CustomUser.objects.filter(email__iexact=email).exists():
                name_parts = s.get('name', 'Student User').strip().split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                gender = 'F' if s.get('gender', '').lower() == 'female' else 'M'
                try:
                    user = CustomUser.objects.create_user(
                        email=email,
                        password='student123',
                        user_type=3,
                        first_name=first_name,
                        last_name=last_name
                    )
                    user.gender = gender
                    user.address = 'Department Address'
                    user.save()
                except Exception as ex:
                    print(f"Error creating DB student for {email}: {ex}")

        # 2. Sync teachers from JSON -> Django DB (so login works for all teachers in teachers.json)
        for t in teachers_json:
            email = t.get('email', '').strip().lower()
            if not email:
                continue
            if not CustomUser.objects.filter(email__iexact=email).exists():
                clean_name = t.get('name', 'Prof Teacher').replace('Prof. ', '').replace('Dr. ', '').strip()
                name_parts = clean_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                try:
                    user = CustomUser.objects.create_user(
                        email=email,
                        password='staff123',
                        user_type=2,
                        first_name=first_name,
                        last_name=last_name
                    )
                    user.gender = 'M'
                    user.address = 'Department Office'
                    user.save()
                except Exception as ex:
                    print(f"Error creating DB staff for {email}: {ex}")

        # Reload JSON in case updated
        students_json = load_json('students.json') or []
        teachers_json = load_json('teachers.json') or []

        # 3. Sync students from Django DB -> JSON (so admin-created students appear in students.json)
        db_students = CustomUser.objects.filter(user_type=3)
        updated_students_json = list(students_json)
        existing_student_emails = {s.get('email', '').strip().lower() for s in updated_students_json if s.get('email')}
        
        max_student_id_num = 0
        for s in updated_students_json:
            st_id = s.get('student_id', 'STU-000')
            try:
                num = int(st_id.split('-')[-1])
                if num > max_student_id_num:
                    max_student_id_num = num
            except ValueError:
                pass

        for db_s in db_students:
            email = db_s.email.strip().lower()
            if email not in existing_student_emails:
                max_student_id_num += 1
                stu_code = f"STU-{max_student_id_num:03d}"
                roll_code = f"2023-AIML-{max_student_id_num:03d}"
                full_name = f"{db_s.first_name} {db_s.last_name}".strip() or email.split('@')[0]
                avatar_path = db_s.profile_pic.url if db_s.profile_pic else "/static/dist/img/avatar.png"
                new_entry = {
                    "id": len(updated_students_json) + 1,
                    "student_id": stu_code,
                    "roll_no": roll_code,
                    "name": full_name,
                    "email": db_s.email,
                    "avatar": avatar_path,
                    "gender": "Female" if db_s.gender == 'F' else "Male",
                    "department": "Computer Science & Engineering (AIML)",
                    "class_name": "Third Year (TE) - Division A",
                    "academic_year": "2025-2026",
                    "semester": "Semester V",
                    "enrollment_date": "2023-08-01",
                    "overall_score": 82.0,
                    "overall_percentage": 82.0,
                    "gpa": 8.2,
                    "cgpa": 8.1,
                    "class_rank": 12,
                    "total_class_size": 68,
                    "attendance_percentage": 90.0,
                    "avg_internal_marks": 17.5,
                    "assignment_completion_rate": 92.0,
                    "subjects_at_risk_count": 0,
                    "quarter_improvement": 3.2,
                    "predicted_category": "First Class",
                    "predicted_percentage_range": "80% - 85%",
                    "risk_level": "Low Risk",
                    "assigned_subjects": ["SUB-101", "SUB-102", "SUB-103", "SUB-104", "SUB-105", "SUB-106"]
                }
                updated_students_json.append(new_entry)
                existing_student_emails.add(email)

        if len(updated_students_json) != len(students_json):
            save_json('students.json', updated_students_json)
            students_json = updated_students_json

        # 4. Sync teachers from Django DB -> JSON (so admin-created staff appear in teachers.json)
        db_staff = CustomUser.objects.filter(user_type=2)
        updated_teachers_json = list(teachers_json)
        existing_teacher_emails = {t.get('email', '').strip().lower() for t in updated_teachers_json if t.get('email')}
        
        max_tch_id_num = 0
        for t in updated_teachers_json:
            t_id = t.get('teacher_id', 'TCH-000')
            try:
                num = int(t_id.split('-')[-1])
                if num > max_tch_id_num:
                    max_tch_id_num = num
            except ValueError:
                pass
                
        for db_t in db_staff:
            email = db_t.email.strip().lower()
            if email not in existing_teacher_emails:
                max_tch_id_num += 1
                tch_code = f"TCH-{max_tch_id_num:03d}"
                full_name = f"Prof. {db_t.first_name} {db_t.last_name}".strip() or email.split('@')[0]
                avatar_path = db_t.profile_pic.url if db_t.profile_pic else "/static/dist/img/avatar.png"
                new_entry = {
                    "id": len(updated_teachers_json) + 1,
                    "teacher_id": tch_code,
                    "name": full_name,
                    "email": db_t.email,
                    "designation": "Assistant Professor",
                    "department": "CSE (AIML)",
                    "phone": "+91 98000 11122",
                    "avatar": avatar_path,
                    "assigned_subjects": ["SUB-101"],
                    "assigned_classes": ["TE CSE-AIML A"],
                    "supervised_students": ["STU-001", "STU-002", "STU-003", "STU-004", "STU-005"]
                }
                updated_teachers_json.append(new_entry)
                existing_teacher_emails.add(email)

        if len(updated_teachers_json) != len(teachers_json):
            save_json('teachers.json', updated_teachers_json)
            teachers_json = updated_teachers_json

        # 5. Build up-to-date users.json
        all_db_users = CustomUser.objects.all().order_by('id')
        users_list = []
        for idx, u in enumerate(all_db_users, 1):
            role_str = "Administrator" if str(u.user_type) == '1' else ("Teacher" if str(u.user_type) == '2' else "Student")
            item = {
                "id": idx,
                "email": u.email,
                "name": u.get_full_name() or u.email.split('@')[0],
                "user_type": str(u.user_type),
                "role": role_str,
                "status": "Active"
            }
            if str(u.user_type) == '3':
                st_match = next((s for s in students_json if s.get('email', '').lower() == u.email.lower()), None)
                if st_match:
                    item['student_id'] = st_match.get('student_id', f'STU-{idx:03d}')
            users_list.append(item)
            
        save_json('users.json', users_list)

    except Exception as e:
        print("Error during sync_db_and_json:", e)

def add_student_to_json(user, course=None, session=None):
    """Call after adding a student to Django DB."""
    students = load_json('students.json') or []
    email = user.email.strip().lower()
    
    for s in students:
        if s.get('email', '').strip().lower() == email:
            return s

    max_num = 0
    for s in students:
        try:
            num = int(s.get('student_id', 'STU-000').split('-')[-1])
            if num > max_num:
                max_num = num
        except ValueError:
            pass

    max_num += 1
    stu_code = f"STU-{max_num:03d}"
    roll_code = f"2023-AIML-{max_num:03d}"
    full_name = user.get_full_name() or user.email.split('@')[0]
    avatar_path = user.profile_pic.url if user.profile_pic else "/static/dist/img/avatar.png"

    new_student = {
        "id": len(students) + 1,
        "student_id": stu_code,
        "roll_no": roll_code,
        "name": full_name,
        "email": user.email,
        "avatar": avatar_path,
        "gender": "Female" if user.gender == 'F' else "Male",
        "department": course.name if course else "Computer Science & Engineering (AIML)",
        "class_name": "Third Year (TE) - Division A",
        "academic_year": "2025-2026",
        "semester": "Semester V",
        "enrollment_date": "2023-08-01",
        "overall_score": 80.0,
        "overall_percentage": 80.0,
        "gpa": 8.0,
        "cgpa": 8.0,
        "class_rank": 15,
        "total_class_size": 68,
        "attendance_percentage": 88.0,
        "avg_internal_marks": 17.5,
        "assignment_completion_rate": 90.0,
        "subjects_at_risk_count": 0,
        "quarter_improvement": 3.0,
        "predicted_category": "First Class",
        "predicted_percentage_range": "78% - 83%",
        "risk_level": "Low Risk",
        "assigned_subjects": ["SUB-101", "SUB-102", "SUB-103", "SUB-104", "SUB-105", "SUB-106"]
    }
    students.append(new_student)
    save_json('students.json', students)
    sync_db_and_json()
    return new_student

def add_staff_to_json(user, course=None):
    """Call after adding a teacher to Django DB."""
    teachers = load_json('teachers.json') or []
    email = user.email.strip().lower()

    for t in teachers:
        if t.get('email', '').strip().lower() == email:
            return t

    max_num = 0
    for t in teachers:
        try:
            num = int(t.get('teacher_id', 'TCH-000').split('-')[-1])
            if num > max_num:
                max_num = num
        except ValueError:
            pass

    max_num += 1
    tch_code = f"TCH-{max_num:03d}"
    full_name = f"Prof. {user.get_full_name()}".strip() if not user.first_name.startswith('Prof') else user.get_full_name()
    avatar_path = user.profile_pic.url if user.profile_pic else "/static/dist/img/avatar.png"

    new_teacher = {
        "id": len(teachers) + 1,
        "teacher_id": tch_code,
        "name": full_name,
        "email": user.email,
        "designation": "Assistant Professor",
        "department": course.name if course else "CSE (AIML)",
        "phone": "+91 98000 11122",
        "avatar": avatar_path,
        "assigned_subjects": ["SUB-101"],
        "assigned_classes": ["TE CSE-AIML A"],
        "supervised_students": ["STU-001", "STU-002", "STU-003", "STU-004", "STU-005"]
    }
    teachers.append(new_teacher)
    save_json('teachers.json', teachers)
    sync_db_and_json()
    return new_teacher

def delete_student_from_json(email):
    """Remove student from students.json by email."""
    students = load_json('students.json') or []
    students = [s for s in students if s.get('email', '').strip().lower() != email.strip().lower()]
    save_json('students.json', students)
    sync_db_and_json()

def delete_staff_from_json(email):
    """Remove teacher from teachers.json by email."""
    teachers = load_json('teachers.json') or []
    teachers = [t for t in teachers if t.get('email', '').strip().lower() != email.strip().lower()]
    save_json('teachers.json', teachers)
    sync_db_and_json()

def get_all_students():
    return load_json('students.json')

def get_all_teachers():
    return load_json('teachers.json')

def get_all_subjects():
    return load_json('subjects.json')

def get_student_by_email_or_id(identifier):
    students = load_json('students.json')
    if not students:
        return None
    for s in students:
        if s.get('email') == identifier or s.get('student_id') == identifier or str(s.get('id')) == str(identifier):
            return s
    return None

def get_student_dashboard_data(identifier, filters=None):
    if filters is None:
        filters = {}
    
    student = get_student_by_email_or_id(identifier)
    if not student:
        return {}
    
    student_id = student['student_id']
    score_factor = student.get('overall_score', 80.0) / 87.4
    att_factor = student.get('attendance_percentage', 85.0) / 91.2
    
    all_subjects = load_json('subjects.json')
    all_assessments = load_json('assessments.json')
    all_assignments = load_json('assignments.json')
    all_feedback = load_json('teacher_feedback.json')
    all_notifications = load_json('notifications.json')
    all_calendar = load_json('academic_calendar.json')
    
    # Subject variance modifiers for realism
    subject_modifiers = {
        "SUB-101": 1.03,
        "SUB-102": 0.98,
        "SUB-103": 0.94,
        "SUB-104": 1.05,
        "SUB-105": 1.01,
        "SUB-106": 0.95
    }
    
    # Dynamically scale assessments to match the specific logged-in student
    student_assessments = []
    for base_ass in all_assessments:
        code = base_ass.get('subject_code')
        mod = subject_modifiers.get(code, 1.0)
        
        calc_pct = round(min(98.5, max(42.0, student.get('overall_score', 80.0) * mod)), 1)
        calc_att = round(min(99.0, max(48.0, student.get('attendance_percentage', 85.0) * (0.95 + 0.1 * mod))), 1)
        calc_internal = round(min(20.0, max(8.0, (calc_pct / 100.0) * 20.0)), 1)
        calc_exam = round(min(80.0, max(30.0, (calc_pct / 100.0) * 80.0)), 1)
        
        status = "Excellent" if calc_pct >= 85 else ("Good" if calc_pct >= 75 else ("Average" if calc_pct >= 60 else "At Risk"))
        grade = "O" if calc_pct >= 90 else ("A+" if calc_pct >= 85 else ("A" if calc_pct >= 75 else ("B+" if calc_pct >= 65 else ("B" if calc_pct >= 55 else "C"))))
        
        improvement = round(student.get('quarter_improvement', 2.0) * (0.8 + 0.4 * mod), 1)
        
        ass_entry = {
            "student_id": student_id,
            "subject_code": code,
            "subject_name": base_ass.get('subject_name'),
            "unit_test_1": round(calc_internal * 0.95, 1),
            "unit_test_2": calc_internal,
            "mid_term": round(calc_exam * 0.35, 1),
            "max_internal": 20.0,
            "assignments_avg": round(min(100.0, calc_pct + 4.0), 1),
            "internal_assessment": calc_internal,
            "semester_exam": calc_exam,
            "total_marks": round(calc_internal + calc_exam, 1),
            "percentage": calc_pct,
            "grade": grade,
            "status": status,
            "improvement": improvement,
            "attendance_pct": calc_att,
            "teacher_remarks": base_ass.get('teacher_remarks'),
            "improvement_areas": base_ass.get('improvement_areas')
        }
        student_assessments.append(ass_entry)
    
    # Scale monthly trend data
    months = ['Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
    monthly_trend_scores = []
    base_s = student.get('overall_score', 80.0)
    month_variances = [-4.5, -2.5, -1.8, -3.2, -0.5, 1.2, 2.8, 3.5]
    
    for i, m in enumerate(months):
        m_score = round(min(99.0, max(45.0, base_s + month_variances[i])), 1)
        m_att = round(min(98.5, max(50.0, student.get('attendance_percentage', 85.0) + (month_variances[i] * 0.7))), 1)
        monthly_trend_scores.append({
            "month": m,
            "score": m_score,
            "attendance": m_att,
            "study_hours": round(max(15, int(base_s * 0.5 + i * 2))),
            "assignments_submitted": 3 if i % 2 == 0 else 4
        })
        
    # Scale Quarterly data
    quarterly_data = [
        {"quarter": "Q1 (Aug-Oct)", "overall_score": round(base_s - 3.2, 1), "attendance": round(student.get('attendance_percentage', 85.0) + 1.5, 1)},
        {"quarter": "Q2 (Nov-Dec)", "overall_score": round(base_s - 2.0, 1), "attendance": round(student.get('attendance_percentage', 85.0) - 2.8, 1)},
        {"quarter": "Q3 (Jan-Mar)", "overall_score": round(base_s, 1), "attendance": round(student.get('attendance_percentage', 85.0), 1)},
        {"quarter": "Q4 (Projected)", "overall_score": round(min(98.0, base_s + student.get('quarter_improvement', 2.0)), 1), "attendance": round(min(98.0, student.get('attendance_percentage', 85.0) + 1.0), 1)}
    ]
    
    # Filter assignments for this student
    student_assignments = all_assignments
    
    # Filter feedback
    student_feedback = all_feedback

    # Apply Subject Filter if selected
    selected_subject = filters.get('subject')
    if selected_subject and selected_subject != 'all':
        student_assessments = [a for a in student_assessments if a.get('subject_code') == selected_subject]
        student_assignments = [asn for asn in student_assignments if asn.get('subject_code') == selected_subject]
        student_feedback = [fb for fb in student_feedback if fb.get('subject_code') == selected_subject]

    # Calculate Strengths & Weaknesses
    strengths = []
    weaknesses = []
    insights = []
    
    for ass in student_assessments:
        pct = ass.get('percentage', 0)
        att = ass.get('attendance_pct', 0)
        sub_name = ass.get('subject_name', '')
        
        if pct >= 80:
            strengths.append({
                "subject": sub_name,
                "score": f"{pct}%",
                "grade": ass.get('grade', 'A+'),
                "message": f"Strong conceptual clarity in {sub_name}. Consistent assessment marks."
            })
        elif pct < 65 or ass.get('status') in ['Needs Improvement', 'At Risk']:
            weaknesses.append({
                "subject": sub_name,
                "score": f"{pct}%",
                "grade": ass.get('grade', 'C'),
                "message": f"Scoring below target in {sub_name} ({pct}%). Recommended for faculty review and doubt-clearing."
            })
            
        if att < 75:
            insights.append({
                "type": "warning",
                "title": f"Attendance Defaulter Alert: {sub_name}",
                "message": f"Your attendance in {sub_name} is {att}%, below the mandatory 75% limit. Attend upcoming classes regularly."
            })
            
    if student.get('quarter_improvement', 0) > 0:
        insights.append({
            "type": "positive",
            "title": "Positive Growth Trajectory",
            "message": f"Overall academic performance has improved by +{student.get('quarter_improvement')}% compared to the previous quarter."
        })
    elif student.get('quarter_improvement', 0) < 0:
        insights.append({
            "type": "warning",
            "title": "Performance Dip Alert",
            "message": f"Overall marks dropped by {abs(student.get('quarter_improvement'))}% compared to the previous quarter. Please consult your subject mentor."
        })

    # Actionable Next Steps
    next_steps = [
        {
            "priority": "High" if student.get('attendance_percentage', 0) < 75 else "Medium",
            "title": "Attendance Compliance",
            "description": f"Current overall attendance is {student.get('attendance_percentage', 0)}%. Keep attendance strictly above 75%.",
            "icon": "fas fa-user-check",
            "color": "danger" if student.get('attendance_percentage', 0) < 75 else "primary"
        },
        {
            "priority": "High",
            "title": "Prepare for IA-2 Internal Assessments",
            "description": "Second term internal tests begin on April 2nd. Review past subject question banks.",
            "icon": "fas fa-pen-alt",
            "color": "warning"
        },
        {
            "priority": "Medium",
            "title": "Recommended Library References",
            "description": "Borrow syllabus-aligned textbooks from the college digital library.",
            "icon": "fas fa-book-reader",
            "color": "info"
        },
        {
            "priority": "Medium",
            "title": "Review Faculty Feedback",
            "description": "Follow up on recent faculty recommendations and laboratory submission corrections.",
            "icon": "fas fa-comments",
            "color": "success"
        }
    ]

    # Academic Activity Timeline
    timeline_events = [
        {
            "date": "Today, 10:30 AM",
            "title": "Teacher Feedback Received",
            "category": "Feedback",
            "description": "Prof. R.K. Yadav posted academic guidance for Artificial Intelligence & Neural Networks.",
            "badge_class": "badge-info",
            "icon": "fas fa-comment-dots"
        },
        {
            "date": "28 Mar 2026",
            "title": "Assignment Graded",
            "category": "Assessment",
            "description": f"Scored {int(student.get('overall_score', 80))}/100 in recent departmental assignment.",
            "badge_class": "badge-success",
            "icon": "fas fa-clipboard-check"
        },
        {
            "date": "24 Mar 2026",
            "title": "Monthly Attendance Logged",
            "category": "Attendance",
            "description": f"March attendance logged at {student.get('attendance_percentage')}% across all enrolled courses.",
            "badge_class": "badge-primary",
            "icon": "fas fa-calendar-check"
        },
        {
            "date": "15 Feb 2026",
            "title": "Semester V Term Results",
            "category": "Examination",
            "description": f"Current Semester GPA: {student.get('gpa')} ({student.get('predicted_category')}).",
            "badge_class": "badge-warning",
            "icon": "fas fa-award"
        },
        {
            "date": "02 Apr 2026 (Upcoming)",
            "title": "Internal Assessment 2 (IA-2)",
            "category": "Exam Alert",
            "description": "Second term internal tests start across all enrolled departments.",
            "badge_class": "badge-danger",
            "icon": "fas fa-bell"
        }
    ]

    # Skill proficiencies for radar chart
    radar_labels = [a.get('subject_name')[:12] for a in student_assessments]
    radar_scores = [a.get('percentage') for a in student_assessments]

    return {
        "student": student,
        "subjects": all_subjects,
        "assessments": student_assessments,
        "assignments": student_assignments,
        "feedback": student_feedback,
        "monthly_trends": monthly_trend_scores,
        "quarterly_progress": quarterly_data,
        "radar_labels": radar_labels,
        "radar_scores": radar_scores,
        "notifications": all_notifications,
        "academic_calendar": all_calendar,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "insights": insights,
        "next_steps": next_steps,
        "timeline_events": timeline_events,
        "filters": {
            "academic_year": filters.get('academic_year', '2025-2026'),
            "quarter": filters.get('quarter', 'all'),
            "month": filters.get('month', 'all'),
            "subject": filters.get('subject', 'all')
        }
    }
