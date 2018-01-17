def pre_create(context):
    # For now since we do not have embryo inheritance,
    # a collection of presets have been made available
    # with specific Dockerfile context, e.g., postgres
    preset = context['args'].get('preset', None)
    if preset in context['preset']:
        context.update(context['preset'][preset])

    # Image from arg will take priority over preset
    # That is if it were specified
    image = context['args'].get('image', None)
    if image:
        context['image'] = image
