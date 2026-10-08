import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_syllabus_data():
    filepath = os.path.join(DATA_DIR, 'syllabus.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'VII': [], 'VIII': []}

def get_syllabus_view_data(semester='VII', search_query='', category_filter='all'):
    raw_data = load_syllabus_data()
    
    # Normalize semester
    sem_key = 'VIII' if str(semester).upper() in ['VIII', '8', 'SEM 8', 'SEM VIII'] else 'VII'
    subjects_list = raw_data.get(sem_key, [])
    
    # Process categories
    # Categories: Core, Elective, Lab, Project, Audit
    processed_subjects = []
    
    total_credits = 0
    core_count = 0
    elective_count = 0
    lab_count = 0
    project_count = 0
    audit_count = 0

    for sub in subjects_list:
        stype = sub.get('type', 'Core')
        credits = sub.get('credits', 0)
        
        # Determine normalized category
        cat = 'Core'
        if 'elective' in stype.lower():
            cat = 'Elective'
            elective_count += 1
        elif 'lab' in stype.lower():
            cat = 'Laboratory'
            lab_count += 1
        elif 'project' in stype.lower():
            cat = 'Project'
            project_count += 1
        elif 'audit' in stype.lower():
            cat = 'Audit Course'
            audit_count += 1
        else:
            cat = 'Core'
            core_count += 1
            
        total_credits += credits

        # Skip generic placeholder rows if there are specific elective options
        if sub.get('name') in ['Elective III', 'Elective IV', 'Elective V', 'Elective VI'] and len(sub.get('units', [])) <= 1:
            continue

        item = {
            'course_code': sub.get('course_code'),
            'name': sub.get('name'),
            'type': stype,
            'category': cat,
            'credits': credits,
            'units': sub.get('units', [])
        }
        processed_subjects.append(item)

    # Filter by category
    if category_filter and category_filter != 'all':
        cf = category_filter.lower()
        if cf == 'core':
            processed_subjects = [s for s in processed_subjects if s['category'] == 'Core']
        elif cf == 'elective':
            processed_subjects = [s for s in processed_subjects if s['category'] == 'Elective']
        elif cf in ['lab', 'laboratory']:
            processed_subjects = [s for s in processed_subjects if s['category'] == 'Laboratory']
        elif cf == 'project':
            processed_subjects = [s for s in processed_subjects if s['category'] == 'Project']
        elif cf == 'audit':
            processed_subjects = [s for s in processed_subjects if s['category'] == 'Audit Course']

    # Filter by search
    if search_query:
        sq = search_query.lower()
        filtered = []
        for s in processed_subjects:
            match = False
            if sq in s['name'].lower() or sq in s['course_code'].lower() or sq in s['type'].lower():
                match = True
            else:
                for u in s['units']:
                    if sq in u.get('title', '').lower() or any(sq in t.lower() for t in u.get('topics', [])):
                        match = True
                        break
            if match:
                filtered.append(s)
        processed_subjects = filtered

    return {
        'semester': sem_key,
        'semester_title': 'Semester VII (Fourth Year - Term I)' if sem_key == 'VII' else 'Semester VIII (Fourth Year - Term II)',
        'pattern': 'SPPU 2019 Course (Computer Engineering)',
        'subjects': processed_subjects,
        'stats': {
            'total_subjects': len(processed_subjects),
            'total_credits': 22 if sem_key == 'VII' else 22,
            'core_count': core_count,
            'elective_count': elective_count,
            'lab_count': lab_count,
            'project_count': project_count,
            'audit_count': audit_count
        },
        'filters': {
            'semester': sem_key,
            'search': search_query,
            'category': category_filter
        }
    }
