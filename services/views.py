from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .data import SERVICES_DATA, ORDERS_DATA, get_minio_url


def services_list(request):
    """MVT: View для списка услуг с фильтрацией по наименованию"""
    query = request.GET.get('q', '').strip()
    order_id = int(request.GET.get('order_id', 1))

    services = SERVICES_DATA.copy()
    order = ORDERS_DATA.get(order_id, {'id': order_id, 'items': []})

    if query:
        services = [s for s in services if query.lower() in s['name'].lower()]

    for service in services:
        service['image_url'] = get_minio_url(service['image_key'])

    cart_count = sum(item['quantity'] for item in order['items'])
    
    context = {
        'title': 'Кометы — услуги расчёта',
        'services': services,
        'query': query,
        'order_id': order_id,
        'cart_count': cart_count,
    }
    return render(request, 'services/comets_list.html', context)


def service_detail(request, service_id):
    """MVT: View для детальной информации об услуге"""
    order_id = int(request.GET.get('order_id', 1))

    service = None
    for s in SERVICES_DATA:
        if s['id'] == service_id:
            service = s.copy()
            break
    
    if not service:
        raise Http404("Услуга не найдена")

    service['image_url'] = get_minio_url(service['image_key'])
    
    context = {
        'title': f"{service['name']} — подробности",
        'service': service,
        'order_id': order_id,
    }
    return render(request, 'services/comet_detail.html', context)


def order_detail(request, order_id):
    """MVT: View для просмотра состава заявки"""
    order = ORDERS_DATA.get(order_id)
    if not order:
        raise Http404("Заявка не найдена")

    items = []
    for item in order['items']:
        service = None
        for s in SERVICES_DATA:
            if s['id'] == item['service_id']:
                service = s.copy()
                break
        
        if service:
            service['image_url'] = get_minio_url(service['image_key'])
            items.append({
                'service': service,
                'quantity': item['quantity'],
                'sort_order': item['sort_order'],
                'is_main': item['is_main'],
            })
    
    cart_count = sum(item['quantity'] for item in order['items'])
    
    context = {
        'title': f"Заявка #{order_id}",
        'order_id': order_id,
        'items': items,
        'cart_count': cart_count,
    }
    return render(request, 'orders/software_request.html', context)
