from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse
from django.contrib.auth.models import User
from django.db import connection
from django.contrib import messages
from .models import Comet, Distance, RequestComet
from .data import calculate_heliocentric_distance_au
from datetime import date
import math


def services_list(request):
    query = request.GET.get('q', '').strip()
    request_id = int(request.GET.get('request_id', 1))


    comets = Comet.objects.filter(is_deleted=False)
    
    if query:
        comets = comets.filter(name__icontains=query)


    current_request = None
    cart_count = 0
    if request.user.is_authenticated:
        try:
            current_request = Distance.objects.get(
                astronomer=request.user, 
                status='draft'
            )
            cart_count = RequestComet.objects.filter(request=current_request).count()
        except Distance.DoesNotExist:
            pass
    
    context = {
        'title': 'Кометы — услуги расчёта',
        'comets': comets,
        'query': query,
        'request_id': request_id,
        'cart_count': cart_count,
        'current_request': current_request,
    }
    return render(request, 'services/comets_list.html', context)


def comet_detail(request, comet_id):
    request_id = int(request.GET.get('request_id', 1))
    

    comet = get_object_or_404(Comet, id=comet_id, is_deleted=False)
    
    context = {
        'title': f"{comet.name} — подробности",
        'comet': comet,
        'request_id': request_id,
    }
    return render(request, 'services/comet_detail.html', context)


def trajectory_calculation_detail(request, request_id):

    distance = get_object_or_404(Distance, id=request_id)
    

    if distance.status == 'deleted':
        raise Http404("Заявка удалена")
    

    request_comets = RequestComet.objects.filter(request=distance).select_related('comet')
    
    items = []
    for req_comet in request_comets:

        distance = math.sqrt(
            (float(req_comet.coords_x) - float(req_comet.comet.k_x))**2 + 
            (float(req_comet.coords_y) - float(req_comet.comet.k_y))**2 + 
            (float(req_comet.coords_z) - float(req_comet.comet.k_z))**2
        )
        
        items.append({
            'comet': req_comet.comet,
            'quantity': req_comet.quantity,
            'sort_order': req_comet.sort_order,
            'is_main': req_comet.is_main,
            'coords': {
                'x': req_comet.coords_x,
                'y': req_comet.coords_y, 
                'z': req_comet.coords_z
            },
            'distance_au': distance,
        })
    
    cart_count = request_comets.count()
    

    astronomers_list = distance.astronomers_list or ['Судьи В. Г.', 'Коваленко А. И.', 'Петров С. М.']
    telescopes_list = distance.telescopes_list or ['Хаббл', 'Кеплер', 'Джеймс Уэбб']
    
    context = {
        'title': f"Заявка #{request_id}",
        'request_id': request_id,
        'items': items,
        'cart_count': cart_count,
        'astronomer': '—',  # Будет выбираться из списка
        'telescope': '—',   # Будет выбираться из списка
        'calc_request': distance,
        'astronomers_list': astronomers_list,
        'telescopes_list': telescopes_list,
    }
    return render(request, 'orders/trajectory_calculation.html', context)


def add_comet_to_request(request, comet_id):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    if not request.user.is_authenticated:
        messages.error(request, "Необходима авторизация")
        return redirect('comets:comets_list')
    
    comet = get_object_or_404(Comet, id=comet_id, is_deleted=False)
    

    distance, created = Distance.objects.get_or_create(
        astronomer=request.user,
        status='draft',
        defaults={}
    )
    

    request_comet, created = RequestComet.objects.get_or_create(
        request=distance,
        comet=comet,
        defaults={
            'quantity': 1,
            'sort_order': RequestComet.objects.filter(request=distance).count() + 1,
            'is_main': False,
            'coords_x': 0.0,
            'coords_y': 0.0,
            'coords_z': 0.0,
        }
    )
    
    if not created:

        request_comet.quantity += 1
        request_comet.save()
        messages.info(request, f"Количество кометы {comet.name} увеличено")
    else:
        messages.success(request, f"Комета {comet.name} добавлена в заявку")
    
    return redirect('comets:comets_list')


def delete_trajectory_calculation(request, request_id):
    """POST: Логическое удаление заявки через SQL UPDATE"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    if not request.user.is_authenticated:
        messages.error(request, "Необходима авторизация")
        return redirect('comets:comets_list')
    

    distance = get_object_or_404(Distance, id=request_id)
    if distance.astronomer != request.user:
        messages.error(request, "Нет прав для удаления этой заявки")
        return redirect('comets:comets_list')
    

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE services_distance SET status = %s WHERE id = %s",
            ['deleted', request_id]
        )
    
    messages.success(request, f"Заявка #{request_id} удалена")
    return redirect('comets:comets_list')