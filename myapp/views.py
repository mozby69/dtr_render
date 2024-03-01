from django.shortcuts import render,redirect
import os
import cv2
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
import qrcode
from pyzbar.pyzbar import decode
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import numpy as np
import base64
from io import BytesIO
from myapp.models import DailyRecord
from myapp.models import temporay
from myapp.models import Employee
from django.utils import timezone
from datetime import timedelta,datetime,date,time
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def is_admin(user):
    return user.groups.filter(name='admingroup').exists()


@login_required(login_url='login')
def home(request):
    user_in_admingroup = is_admin(request.user)
    return render(request, 'myapp/home.html', {'user_in_admingroup': user_in_admingroup})




def index(request):
    return render(request,'myapp/index.html')


def fetch_messages(request):
    # Retrieve messages based on tags (e.g., 'timein', 'breakout')
    messages = get_messages(request)
    filtered_messages = [
        {'text': message.message, 'tags': message.tags} for message in messages if 'timein' in message.tags
                                                                                   or 'breakout' in message.tags or 'breakin' in message.tags or 'timeout' in message.tags
                                                                                   or 'no_bibo' in message.tags or 'breakin_aft' in message.tags or 'timeout_aft' in message.tags
                                                                                   or 'timein_already' in message.tags or 'breakin_already' in message.tags or 'timeout_already' in message.tags
    ]

    return JsonResponse({'messages': filtered_messages})


@csrf_exempt
def webcam_qr_code_scanner(request):
    if request.method == 'POST':
        image_data = request.FILES['webcam_image'].read()
        decoded_objects = scan_qr_code_from_image_data(image_data)
        current_time = datetime.now()

        if decoded_objects:
            name = decoded_objects[0].data.decode('utf-8')
            prac_time = current_time.strftime("%H:%M")
            qr_existing = Employee.objects.filter(EmpCode=name).first()
            formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}" if qr_existing else name

            # FOR TIMEIN
            if "03:00" <= prac_time <= "09:59":
                existing_entry = DailyRecord.objects.filter(Empname=formatted_name,
                                                                    date=current_time.date()).first()
                if existing_entry is None:
                    insertData(name, current_time, request)
                    messages.success(request, f'Timein Successfully! - {formatted_name}', extra_tags='timein')
                    return HttpResponseRedirect(request.path)

                timein_already = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()
                existing_entry_timein_timestamps = timein_already.timein_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time - existing_entry_timein_timestamps >= timedelta(seconds=4):
                    messages.success(request, f'Timein Already! - {formatted_name}', extra_tags='timein_already')
                    return HttpResponseRedirect(request.path)

            # FOR BREAKOUT
            if "11:30" <= prac_time <= "12:30" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakout_names__isnull=True,
                                                                          date=current_time.date()).exists():
                existing_entry = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                existing_entry_timein_timestamps = existing_entry.timein_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                time_difference = current_time - existing_entry_timein_timestamps
                remaining_seconds = max(15 - time_difference.total_seconds(), 0)

                if current_time - existing_entry_timein_timestamps >= timedelta(seconds=15):
                    breakout(name, current_time)
                    temporay.objects.filter(Empname=formatted_name, date=current_time.date()).update(
                        breakout_names=formatted_name, breakout_timestamps=current_time)
                    messages.success(request, f'Breakout Successfully! - {formatted_name}', extra_tags='breakout')
                    return HttpResponseRedirect(request.path)

            # FOR BREAKIN
            if "11:30" <= prac_time <= "13:00" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakout_names__isnull=False,
                                                                          breakin_names__isnull=True,
                                                                          date=current_time.date()).exists():
                existing_entry2 = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                existing_entry_breakout_timestamps = existing_entry2.breakout_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time - existing_entry_breakout_timestamps >= timedelta(seconds=6):
                    breakin(name, current_time)
                    temporay.objects.filter(Empname=formatted_name, date=current_time.date()).update(
                        breakin_names=formatted_name, breakin_timestamps=current_time)
                    messages.success(request, f'Breakin Successfully! - {formatted_name}', extra_tags='breakin')
                    return HttpResponseRedirect(request.path)

            # IF BREAKIN IS ALREADY INSERTED
            if "11:30" <= prac_time <= "13:00" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakout_names__isnull=False,
                                                                          breakin_names__isnull=False,
                                                                          timeout_names__isnull=True,
                                                                          date=current_time.date()).exists():
                existing_entry3 = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                existing_entry_breakin_timestamps = existing_entry3.breakin_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time - existing_entry_breakin_timestamps >= timedelta(seconds=6):
                    messages.success(request, f'BREAKIN ALREADY! - {formatted_name}', extra_tags='breakin_already')
                    return HttpResponseRedirect(request.path)

            # FOR TIMEOUT
            if "15:30" <= prac_time <= "23:59" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakout_names__isnull=False,
                                                                          breakin_names__isnull=False,
                                                                          timeout_names__isnull=True,
                                                                          date=current_time.date()).exists():
                existing_entry3 = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                existing_entry_breakin_timestamps = existing_entry3.breakin_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                time_difference = current_time - existing_entry_breakin_timestamps
                remaining_seconds = max(30 - time_difference.total_seconds(), 0)

                if current_time - existing_entry_breakin_timestamps >= timedelta(seconds=30):
                    timeout(name, current_time)
                    temporay.objects.filter(Empname=formatted_name, date=current_time.date()).update(
                        timeout_names=formatted_name, timeout_timestamps=current_time)
                    messages.success(request, f'Timeout Successfully! - {formatted_name}', extra_tags='timeout')
                    return HttpResponseRedirect(request.path)

            # IF NO BREAKOUT OR BREAKIN
            if "15:00" <= prac_time <= "23:59" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakin_names__isnull=True,
                                                                          breakout_names__isnull=True,
                                                                          date=current_time.date()).exists():
                messages.success(request, f'NO BREAKOUT OR BREAKIN! - {formatted_name}', extra_tags='no_bibo')
                return HttpResponseRedirect(request.path)

            # IF TIMEOUT IS ALREADY INSERTED
            if "15:00" <= prac_time <= "23:59" and temporay.objects.filter(Empname=formatted_name,
                                                                          timein_names__isnull=False,
                                                                          breakout_names__isnull=False,
                                                                          breakin_names__isnull=False,
                                                                          timeout_names__isnull=False,
                                                                          date=current_time.date()).exists():
                existing_entry7 = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                existing_entry_breakin_timestamps = existing_entry7.timeout_timestamps.replace(tzinfo=timezone.utc)
                current_time = current_time.replace(tzinfo=timezone.utc)

                if current_time - existing_entry_breakin_timestamps >= timedelta(seconds=6):
                    messages.success(request, f'TIMEOUT ALREADY! - {formatted_name}', extra_tags='timeout_already')
                    return HttpResponseRedirect(request.path)

            # IF HALF DAY IN THE AFTERNOON - BREAKIN
            qr_existing = Employee.objects.filter(EmpCode=name).first()
            formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}" if qr_existing else name
            if "10:00" <= prac_time <= "13:00":
                existing_entry = DailyRecord.objects.filter(Empname=formatted_name,
                                                                    date=current_time.date()).first()
                if existing_entry is None:
                    afternoonBreakout(name, current_time, request)
                    messages.success(request, f'Breakin Successfully! - {formatted_name}', extra_tags='breakin_aft')
                    return HttpResponseRedirect(request.path)

                # HALF DAY TIMEOUT
                if "15:00" <= prac_time <= "23:59" and temporay.objects.filter(Empname=formatted_name,
                                                                              breakin_names__isnull=False,
                                                                              timeout_names__isnull=True,
                                                                              date=current_time.date()).exists():
                    existing_entry = temporay.objects.filter(Empname=formatted_name, date=current_time.date()).first()

                    existing_entry_breakin_timestamps = existing_entry.breakin_timestamps.replace(tzinfo=timezone.utc)
                    current_time = current_time.replace(tzinfo=timezone.utc)

                    time_difference = current_time - existing_entry_breakin_timestamps
                    remaining_seconds = max(15 - time_difference.total_seconds(), 0)

                    if current_time - existing_entry_breakin_timestamps >= timedelta(seconds=15):
                        afternoonTimeout(name, current_time)
                        temporay.objects.filter(Empname=formatted_name, date=current_time.date()).update(
                            timeout_names=formatted_name, timeout_timestamps=current_time)
                        messages.success(request, f'Timeout Successfully! - {formatted_name}', extra_tags='timeout_aft')
                        return HttpResponseRedirect(request.path)

            return JsonResponse({"success": True, "name": name})

    return JsonResponse({"success": False, "error": "QR code not detected"})


def scan_qr_code_from_image_data(image_data):
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    decoded_objects = decode(gray)
    return decoded_objects


def afternoonBreakout(name, current_time, request):
    formatted_time = current_time.strftime("%I:%M:%S")
    branch_names = request.user.username

    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing is None:
        DailyRecord.objects.filter(breakin__isnull=True, Empname=name, date=current_time.date()).create(Empname=name,
                                                                                                             breakin=formatted_time,
                                                                                                             branch_name=branch_names)
        temporay.objects.filter(Empname=name, date=current_time.date()).create(Empname=name, breakin_names=name,
                                                                           breakin_timestamps=current_time)

    else:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry is None:
            DailyRecord.objects.filter(Empname=formatted_name, breakin__isnull=True,
                                               date=current_time.date()).create(Empname=formatted_name,
                                                                                breakin=formatted_time,
                                                                                branch_name=branch_names)
            temporay.objects.filter(Empname=name, date=current_time.date()).create(Empname=formatted_name,
                                                                               breakin_names=formatted_name,
                                                                               breakin_timestamps=current_time)


def afternoonTimeout(name, current_time):
    formatted_time = current_time.strftime("%I:%M:%S")
    DailyRecord.objects.filter(Empname=name, breakin__isnull=False, date=current_time.date()).update(timeout=formatted_time)
    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry:
            DailyRecord.objects.filter(Empname=formatted_name, breakin__isnull=False, timeout__isnull=True,
                                               date=current_time.date()).update(timeout=formatted_time)


def breakout(name, current_time):
    formatted_time = current_time.strftime("%I:%M:%S")
    DailyRecord.objects.filter(timein__isnull=False, breakout__isnull=True, Empname=name,
                                       date=current_time.date()).update(breakout=formatted_time)
    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry:
            DailyRecord.objects.filter(timein__isnull=False, breakout__isnull=True, Empname=formatted_name,
                                               date=current_time.date()).update(breakout=formatted_time)


def insertData(name, current_time, request):
    formatted_time = current_time.strftime("%I:%M:%S")
    branch_names = request.user.username

    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing is None:

        DailyRecord.objects.filter(Empname=name, date=current_time.date()).create(
            Empname=name,
            timein=formatted_time,
            branch_name=branch_names,
        )
        temporay.objects.filter(Empname=name, date=current_time.date()).create(Empname=name, timein_names=name,
                                                                           timein_timestamps=current_time)
    else:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry is None:
            DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).create(
                Empname=formatted_name,
                timein=formatted_time,
                branch_name=branch_names,
            )
            temporay.objects.filter(Empname=name, date=current_time.date()).create(Empname=formatted_name,
                                                                               timein_names=formatted_name,
                                                                               timein_timestamps=current_time)


def breakin(name, current_time):
    formatted_time = current_time.strftime("%I:%M:%S")
    DailyRecord.objects.filter(timein__isnull=False, breakout__isnull=False, breakin__isnull=True, Empname=name,
                                       date=current_time.date()).update(breakin=formatted_time)
    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry:
            DailyRecord.objects.filter(Empname=formatted_name, timein__isnull=False, breakout__isnull=False,
                                               breakin__isnull=True, date=current_time.date()).update(
                breakin=formatted_time)


def timeout(name, current_time):
    formatted_time = current_time.strftime("%I:%M:%S")
    DailyRecord.objects.filter(timein__isnull=False, breakin__isnull=False, breakout__isnull=False,
                                       timeout__isnull=True, Empname=name, date=current_time.date()).update(
        timeout=formatted_time)
    qr_existing = Employee.objects.filter(EmpCode=name).first()

    if qr_existing:
        formatted_name = f"{qr_existing.Firstname} {qr_existing.Lastname}"
        existing_entry = DailyRecord.objects.filter(Empname=formatted_name, date=current_time.date()).first()

        if existing_entry:
            DailyRecord.objects.filter(timein__isnull=False, breakin__isnull=False, breakout__isnull=False,
                                               timeout__isnull=True, Empname=formatted_name,
                                               date=current_time.date()).update(timeout=formatted_time)




def display_qr_list(request):
    current_date = date.today()
    attendances = DailyRecord.objects.filter(date=current_date).order_by('-breakout', '-breakin', '-timeout','-timein')

    def custom_sort(attendance):
        times = [attendance.breakout, attendance.breakin, attendance.timeout]
        latest_time = max(filter(None, times), default=None)

        if latest_time is not None and isinstance(latest_time, str):
            latest_time = datetime.strptime(latest_time, '%H:%M:%S').time()

        return latest_time or datetime.min.time()

    sorted_attendances = sorted(attendances, key=custom_sort, reverse=True)

    data = [
        {
            'name': attendance.Empname,
            'timein': str(attendance.timein),
            'breakout': str(attendance.breakout),
            'breakin': str(attendance.breakin),
            'timeout': str(attendance.timeout)
        } for attendance in sorted_attendances
    ]

    return JsonResponse({'attendances': data})







def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                if request.user.username == 'emb_payroll':
                    return redirect('index_payroll')
                else:
                    return redirect('home')
            
    else:
        form = AuthenticationForm()
    return render(request, 'myapp/login.html', {'form': form})






