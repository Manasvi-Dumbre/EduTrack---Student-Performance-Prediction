import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt

from .EmailBackend import EmailBackend
from .models import Attendance, Session, Subject 

# Create your views here.


def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        #Google recaptcha
        captcha_token = request.POST.get('g-recaptcha-response')
        captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        captcha_key = "6LfTGD4qAAAAALtlli02bIM2MGi_V0cUYrmzGEGd"
        # captcha_key = "6LfHPwojAAAAAAtIjbi-7_N4fNf7Wp0LUiYlCDw_"  #server
        data = {
            'secret': captcha_key,
            'response': captcha_token
        }
        # Make request
        try:
            captcha_server = requests.post(url=captcha_url, data=data)
            response = json.loads(captcha_server.text)
            if response['success'] == False:
                messages.error(request, 'Invalid Captcha. Try Again')
                return redirect('/')
        except:
            messages.error(request, 'Captcha could not be verified. Try Again')
            return redirect('/')
        
        #Authenticate
        user = EmailBackend.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user != None:
            login(request, user)
            
            # Handle "Remember Me" functionality
            remember_me = request.POST.get('remember')
            if remember_me:
                # Set session to expire when browser closes = False
                # Session will last for 30 days
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days in seconds
            else:
                # Set session to expire when browser closes
                request.session.set_expiry(0)
            
            if user.user_type == '1':
                return redirect(reverse("admin_home"))
            elif user.user_type == '2':
                return redirect(reverse("staff_home"))
            else:
                return redirect(reverse("student_home"))
        else:
            messages.error(request, "Invalid details")
            return redirect("/")



def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
"""
    return HttpResponse(data, content_type='application/javascript')


def room_availability(request):
    """Render the Classrooms & Labs/Halls Availability page with staff booking and HOD approval."""
    if not request.user.is_authenticated:
        return redirect('login_page')

    from main_app.room_service import (
        get_room_availability_data,
        update_room_status,
        create_booking_request,
        approve_booking_request,
        reject_booking_request,
        check_booking_conflict
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Staff Slot Booking Request
        if action == 'book_slot' and str(request.user.user_type) == '2':
            room_id = request.POST.get('room_id')
            teacher_name = request.POST.get('teacher_name')
            date_val = request.POST.get('date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            event_type = request.POST.get('event_type')
            purpose = request.POST.get('purpose', '')

            success, res = create_booking_request(
                room_id=room_id,
                teacher_name=teacher_name,
                teacher_email=request.user.email,
                date_str=date_val,
                start_time=start_time,
                end_time=end_time,
                event_type=event_type,
                purpose=purpose
            )
            if success:
                messages.success(request, "Slot booking request submitted successfully! A notification has been sent to the HOD for approval.")
            else:
                messages.error(request, f"Booking Conflict / Error: {res}")
            
            return redirect(f"/room_availability/?date={date_val}")

        # 2. HOD / Admin Approval
        elif action == 'approve_booking' and str(request.user.user_type) == '1':
            booking_id = request.POST.get('booking_id')
            remarks = request.POST.get('hod_remarks', 'Approved by HOD')
            success, res = approve_booking_request(booking_id, hod_user=request.user, remarks=remarks)
            if success:
                messages.success(request, f"Booking request {booking_id} approved successfully! Room is now reserved and marked on the timetable.")
            else:
                messages.error(request, f"Approval Error: {res}")
            return redirect('room_availability')

        # 3. HOD / Admin Rejection
        elif action == 'reject_booking' and str(request.user.user_type) == '1':
            booking_id = request.POST.get('booking_id')
            remarks = request.POST.get('hod_remarks', 'Rejected by HOD')
            success, res = reject_booking_request(booking_id, hod_user=request.user, remarks=remarks)
            if success:
                messages.info(request, f"Booking request {booking_id} has been rejected.")
            else:
                messages.error(request, f"Rejection Error: {res}")
            return redirect('room_availability')

        # 4. Admin room status update
        elif str(request.user.user_type) == '1':
            room_id = request.POST.get('room_id')
            status_override = request.POST.get('status_override')
            maintenance_reason = request.POST.get('maintenance_reason', '')
            capacity = request.POST.get('capacity')
            building = request.POST.get('building')

            updated = update_room_status(
                room_id=room_id,
                status_override=status_override,
                maintenance_reason=maintenance_reason,
                capacity=capacity,
                building=building
            )
            if updated:
                messages.success(request, "Room status updated successfully!")
            else:
                messages.error(request, "Failed to update room status.")
            return redirect('room_availability')

    date_str = request.GET.get('date', '')
    search_query = request.GET.get('search', '').strip()
    building_filter = request.GET.get('building', 'all')
    status_filter = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'name')
    category_tab = request.GET.get('category', 'all')
    selected_room_id = request.GET.get('room_id')

    availability_data = get_room_availability_data(
        date_str=date_str,
        search_query=search_query,
        building_filter=building_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        category_tab=category_tab,
        selected_room_id=selected_room_id,
        user_email=request.user.email
    )

    context = {
        'page_title': 'Room & Resource Availability',
        'page_subtitle': 'Check the availability of classrooms, halls and laboratories based on the college timetable.',
        'availability': availability_data,
        'user_is_admin': str(request.user.user_type) == '1',
        'user_is_staff': str(request.user.user_type) == '2',
        'user_is_student': str(request.user.user_type) == '3',
    }
    return render(request, 'main_app/room_availability.html', context)


def syllabus_view(request):
    """Render the SPPU 2019 Course Fourth Year Syllabus page for Semester VII & VIII."""
    if not request.user.is_authenticated:
        return redirect('login_page')

    semester = request.GET.get('semester', 'VII')
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', 'all')

    from main_app.syllabus_service import get_syllabus_view_data
    syllabus_data = get_syllabus_view_data(
        semester=semester,
        search_query=search_query,
        category_filter=category_filter
    )

    context = {
        'page_title': 'Course Syllabus',
        'page_subtitle': 'Fourth Year Computer Engineering (SPPU 2019 Course) - Semester VII & VIII',
        'syllabus': syllabus_data,
        'user_is_admin': str(request.user.user_type) == '1',
        'user_is_staff': str(request.user.user_type) == '2',
    }
    return render(request, 'main_app/syllabus.html', context)



