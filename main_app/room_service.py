import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_rooms_json():
    filepath = os.path.join(DATA_DIR, 'rooms.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_rooms_json(data):
    filepath = os.path.join(DATA_DIR, 'rooms.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_room_bookings():
    filepath = os.path.join(DATA_DIR, 'room_bookings.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_room_bookings(data):
    filepath = os.path.join(DATA_DIR, 'room_bookings.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def parse_time_to_minutes(t_str):
    if not t_str:
        return 0
    t_str = t_str.strip().upper()
    try:
        dt = datetime.strptime(t_str, '%I:%M %p')
        return dt.hour * 60 + dt.minute
    except Exception:
        try:
            dt = datetime.strptime(t_str, '%H:%M')
            return dt.hour * 60 + dt.minute
        except Exception:
            return 0

def times_overlap(s1, e1, s2, e2):
    return max(s1, s2) < min(e1, e2)

def check_booking_conflict(room_id, date_str, start_time_str, end_time_str, exclude_booking_id=None):
    """
    Checks if a booking conflicts with:
    1. Timetable schedule for the day of week.
    2. Any existing Approved booking for that room on that date.
    3. Maintenance status override.
    Returns: (has_conflict: bool, conflict_message: str or None)
    """
    rooms = load_rooms_json()
    room = next((r for r in rooms if str(r.get('id')) == str(room_id)), None)
    if not room:
        return True, "Selected room does not exist."

    if room.get('status_override') == 'Maintenance':
        return True, f"This room is currently under maintenance ({room.get('maintenance_reason', 'Maintenance')})."

    req_start = parse_time_to_minutes(start_time_str)
    req_end = parse_time_to_minutes(end_time_str)
    if req_start >= req_end:
        return True, "End time must be after start time."

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        target_date = datetime.now()
    
    day_of_week = target_date.strftime('%A')
    if day_of_week == 'Sunday':
        day_of_week = 'Monday'

    # 1. Check weekly timetable schedule
    schedule = room.get('weekly_schedule', {}).get(day_of_week, room.get('weekly_schedule', {}).get('Monday', []))
    for slot in schedule:
        title = slot.get('title', '').strip()
        if title and title.lower() != 'free':
            time_range = slot.get('time', '')
            try:
                s_str, e_str = [t.strip() for t in time_range.split('-')]
                slot_s = parse_time_to_minutes(s_str)
                slot_e = parse_time_to_minutes(e_str)
                if times_overlap(req_start, req_end, slot_s, slot_e):
                    faculty = slot.get('faculty', '')
                    c_name = slot.get('class', '')
                    fac_info = f" ({faculty} | {c_name})" if faculty else ""
                    return True, f"This room is already occupied during the selected time by '{title}'{fac_info} ({time_range})."
            except Exception:
                pass

    # 2. Check other approved bookings
    bookings = load_room_bookings()
    for b in bookings:
        if exclude_booking_id and str(b.get('id')) == str(exclude_booking_id):
            continue
        if str(b.get('room_id')) == str(room_id) and b.get('date') == date_str and b.get('status') == 'Approved':
            b_s = parse_time_to_minutes(b.get('start_time'))
            b_e = parse_time_to_minutes(b.get('end_time'))
            if times_overlap(req_start, req_end, b_s, b_e):
                return True, f"This room is already booked by {b.get('teacher_name', 'Faculty')} for '{b.get('event_type')}' ({b.get('start_time')} - {b.get('end_time')})."

    return False, None

def create_booking_request(room_id, teacher_name, teacher_email, date_str, start_time, end_time, event_type, purpose=""):
    """Creates a new pending room booking request and notifies the HOD."""
    has_conflict, error_msg = check_booking_conflict(room_id, date_str, start_time, end_time)
    if has_conflict:
        return False, error_msg

    rooms = load_rooms_json()
    room = next((r for r in rooms if str(r.get('id')) == str(room_id)), None)
    if not room:
        return False, "Room not found."

    bookings = load_room_bookings()
    booking_id = f"BK-{len(bookings) + 1001}"

    now_str = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    new_booking = {
        "id": booking_id,
        "room_id": int(room_id),
        "room_number": room.get('room_number'),
        "room_type": room.get('type'),
        "building": room.get('building'),
        "teacher_name": teacher_name,
        "teacher_email": teacher_email,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "event_type": event_type,
        "purpose": purpose,
        "status": "Pending",
        "requested_at": now_str,
        "hod_remarks": ""
    }
    bookings.insert(0, new_booking)
    save_room_bookings(bookings)

    # Send Notification to HOD
    try:
        notif_path = os.path.join(DATA_DIR, 'notifications.json')
        if os.path.exists(notif_path):
            with open(notif_path, 'r', encoding='utf-8') as f:
                notifs = json.load(f)
            notifs.insert(0, {
                "id": len(notifs) + 1,
                "title": f"New Slot Booking Request: {room.get('room_number')}",
                "message": f"{teacher_name} has requested {room.get('room_number')} on {date_str} ({start_time} - {end_time}) for '{event_type}'.",
                "category": "Booking Request",
                "created_at": "Just now",
                "badge_class": "badge-warning"
            })
            with open(notif_path, 'w', encoding='utf-8') as f:
                json.dump(notifs, f, indent=2)
    except Exception:
        pass

    return True, new_booking

def approve_booking_request(booking_id, hod_user=None, remarks="Approved by HOD"):
    bookings = load_room_bookings()
    booking = next((b for b in bookings if str(b.get('id')) == str(booking_id)), None)
    if not booking:
        return False, "Booking request not found."

    # Validate conflicts prior to approval
    has_conflict, error_msg = check_booking_conflict(
        room_id=booking.get('room_id'),
        date_str=booking.get('date'),
        start_time_str=booking.get('start_time'),
        end_time_str=booking.get('end_time'),
        exclude_booking_id=booking.get('id')
    )
    if has_conflict:
        return False, f"Cannot approve: {error_msg}"

    booking['status'] = 'Approved'
    booking['approved_at'] = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    booking['hod_remarks'] = remarks
    save_room_bookings(bookings)
    return True, booking

def reject_booking_request(booking_id, hod_user=None, remarks="Rejected by HOD"):
    bookings = load_room_bookings()
    booking = next((b for b in bookings if str(b.get('id')) == str(booking_id)), None)
    if not booking:
        return False, "Booking request not found."

    booking['status'] = 'Rejected'
    booking['rejected_at'] = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    booking['hod_remarks'] = remarks
    save_room_bookings(bookings)
    return True, booking

def get_room_availability_data(date_str=None, search_query='', building_filter='all', status_filter='all', sort_by='name', category_tab='all', selected_room_id=None, user_email=None):
    rooms = load_rooms_json()
    all_bookings = load_room_bookings()

    # Selected date calculation (default to current local time or provided date)
    if not date_str:
        selected_date = datetime.now()
        date_str = selected_date.strftime('%Y-%m-%d')
    else:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            selected_date = datetime.now()
            date_str = selected_date.strftime('%Y-%m-%d')

    # Determine Day of Week
    day_of_week = selected_date.strftime('%A')
    if day_of_week in ['Sunday']:
        day_of_week = 'Monday'

    # Current time reference
    now_hour = datetime.now().hour
    now_minute = datetime.now().minute
    current_time_minutes = now_hour * 60 + now_minute
    
    if current_time_minutes < 9 * 60 or current_time_minutes > 17 * 60:
        simulated_minutes = 9 * 60 + 30 # 09:30 AM default display
    else:
        simulated_minutes = current_time_minutes

    # Filter approved bookings for the selected date
    date_approved_bookings = [b for b in all_bookings if b.get('date') == date_str and b.get('status') == 'Approved']

    processed_rooms = []
    
    available_count = 0
    occupied_count = 0
    upcoming_count = 0
    maintenance_count = 0

    all_buildings = set()

    for r in rooms:
        all_buildings.add(r.get('building', 'Block A'))
        
        override = r.get('status_override')
        
        # Base schedule for day
        schedule_for_day = list(r.get('weekly_schedule', {}).get(day_of_week, r.get('weekly_schedule', {}).get('Monday', [])))
        
        # Overlay approved bookings into schedule for this room
        room_approved = [b for b in date_approved_bookings if str(b.get('room_id')) == str(r.get('id'))]
        for ab in room_approved:
            schedule_for_day.append({
                'time': f"{ab.get('start_time')} - {ab.get('end_time')}",
                'title': f"{ab.get('event_type')}: {ab.get('purpose')}" if ab.get('purpose') else ab.get('event_type'),
                'faculty': ab.get('teacher_name', 'Faculty'),
                'class': 'Booked Slot',
                'is_booking': True
            })

        current_status = "Available"
        current_event = None
        next_event = None
        timing_display = "Free now"
        
        if override == "Maintenance":
            current_status = "Maintenance"
            timing_display = "All day"
            current_event = {
                "title": r.get('maintenance_reason', 'Under Maintenance'),
                "faculty": r.get('staff_in_charge', 'IT Dept.'),
                "class": "Maintenance",
                "time": "All day"
            }
        else:
            active_slot = None
            upcoming_slot = None
            
            for idx, slot in enumerate(schedule_for_day):
                title = slot.get('title', '').strip()
                if not title or title.lower() == 'free':
                    continue
                
                time_range = slot.get('time', '')
                try:
                    start_str, end_str = [t.strip() for t in time_range.split('-')]
                    start_min = parse_time_to_minutes(start_str)
                    end_min = parse_time_to_minutes(end_str)
                except Exception:
                    start_min, end_min = 9 * 60, 10 * 60

                if start_min <= simulated_minutes <= end_min:
                    active_slot = slot
                elif start_min > simulated_minutes and (upcoming_slot is None or start_min < upcoming_slot['start_min']):
                    upcoming_slot = dict(slot, start_min=start_min)

            if active_slot:
                current_status = "Occupied"
                current_event = active_slot
                timing_display = active_slot.get('time')
                if upcoming_slot:
                    next_event = upcoming_slot
            elif upcoming_slot and (upcoming_slot['start_min'] - simulated_minutes) <= 120:
                current_status = "Upcoming"
                current_event = upcoming_slot
                timing_display = upcoming_slot.get('time')
                next_event = upcoming_slot
            else:
                current_status = "Available"
                if upcoming_slot:
                    timing_display = f"Free now (Next: {upcoming_slot.get('time', '').split('-')[0].strip()})"
                    next_event = upcoming_slot
                else:
                    timing_display = "Free now"

        if current_status == "Available":
            available_count += 1
        elif current_status == "Occupied":
            occupied_count += 1
        elif current_status == "Upcoming":
            upcoming_count += 1
        elif current_status == "Maintenance":
            maintenance_count += 1

        # Build daily chronological timeline
        timeline = []
        for slot in schedule_for_day:
            is_free = not slot.get('title') or slot.get('title').lower() == 'free'
            timeline.append({
                "time": slot.get('time'),
                "title": slot.get('title'),
                "faculty": slot.get('faculty', ''),
                "class": slot.get('class', ''),
                "is_free": is_free,
                "is_booking": slot.get('is_booking', False)
            })

        # Sort timeline by start time
        timeline.sort(key=lambda x: parse_time_to_minutes(x.get('time', '').split('-')[0].strip()))

        room_obj = {
            "id": r.get('id'),
            "room_number": r.get('room_number'),
            "type": r.get('type'),
            "building": r.get('building'),
            "capacity": r.get('capacity'),
            "status": current_status,
            "image": r.get('image'),
            "department": r.get('department'),
            "staff_in_charge": r.get('staff_in_charge'),
            "current_event": current_event,
            "next_event": next_event,
            "timing_display": timing_display,
            "timeline": timeline,
            "maintenance_reason": r.get('maintenance_reason', '')
        }
        processed_rooms.append(room_obj)

    # 1. Filter by Category Tab
    if category_tab and category_tab != 'all':
        if category_tab.lower() == 'classrooms':
            processed_rooms = [r for r in processed_rooms if r['type'].lower() == 'classroom']
        elif category_tab.lower() in ['laboratories', 'labs']:
            processed_rooms = [r for r in processed_rooms if r['type'].lower() in ['laboratory', 'lab']]
        elif category_tab.lower() == 'halls':
            processed_rooms = [r for r in processed_rooms if r['type'].lower() == 'hall']

    # 2. Filter by Search Query
    if search_query:
        sq = search_query.lower()
        processed_rooms = [
            r for r in processed_rooms
            if sq in r['room_number'].lower() or sq in r['building'].lower() or sq in r['type'].lower() or (r['current_event'] and sq in r['current_event'].get('title', '').lower())
        ]

    # 3. Filter by Building
    if building_filter and building_filter != 'all':
        processed_rooms = [r for r in processed_rooms if r['building'].lower() == building_filter.lower()]

    # 4. Filter by Status
    if status_filter and status_filter != 'all':
        processed_rooms = [r for r in processed_rooms if r['status'].lower() == status_filter.lower()]

    # 5. Sorting
    if sort_by == 'capacity':
        processed_rooms.sort(key=lambda x: x['capacity'], reverse=True)
    elif sort_by == 'building':
        processed_rooms.sort(key=lambda x: (x['building'], x['room_number']))
    elif sort_by == 'status':
        processed_rooms.sort(key=lambda x: x['status'])
    else:
        processed_rooms.sort(key=lambda x: x['room_number'])

    selected_room = None
    if selected_room_id:
        selected_room = next((r for r in processed_rooms if str(r['id']) == str(selected_room_id)), None)
    if not selected_room and processed_rooms:
        selected_room = processed_rooms[0]

    # Load staff list for booking dropdown
    teachers_path = os.path.join(DATA_DIR, 'teachers.json')
    teachers_list = []
    if os.path.exists(teachers_path):
        with open(teachers_path, 'r', encoding='utf-8') as f:
            teachers_list = json.load(f)

    # Get user's bookings if logged in
    user_bookings = all_bookings
    if user_email:
        user_bookings = [b for b in all_bookings if b.get('teacher_email') == user_email]

    pending_bookings = [b for b in all_bookings if b.get('status') == 'Pending']

    return {
        "summary": {
            "available": available_count,
            "occupied": occupied_count,
            "upcoming": upcoming_count,
            "maintenance": maintenance_count,
            "total": len(rooms)
        },
        "rooms": processed_rooms,
        "buildings": sorted(list(all_buildings)),
        "selected_room": selected_room,
        "selected_date": date_str,
        "day_of_week": day_of_week,
        "teachers": teachers_list,
        "all_bookings": all_bookings,
        "user_bookings": user_bookings,
        "pending_bookings": pending_bookings,
        "filters": {
            "search": search_query,
            "building": building_filter,
            "status": status_filter,
            "sort_by": sort_by,
            "category_tab": category_tab
        }
    }

def update_room_status(room_id, status_override=None, maintenance_reason=None, capacity=None, building=None):
    rooms = load_rooms_json()
    updated = False
    for r in rooms:
        if str(r.get('id')) == str(room_id):
            if status_override is not None:
                r['status_override'] = None if status_override == 'Auto' else status_override
            if maintenance_reason is not None:
                r['maintenance_reason'] = maintenance_reason
            if capacity is not None:
                r['capacity'] = int(capacity)
            if building is not None:
                r['building'] = building
            updated = True
            break
    if updated:
        save_rooms_json(rooms)
    return updated
