def pre_create(context):
    args = context['args']
    name = args.get('name', context.get('name'))
    context['name'] = name
