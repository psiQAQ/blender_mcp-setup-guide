def get_extension_settings(context):
    scene = getattr(context, "scene", None)
    return getattr(scene, "example_extension_settings", None) if scene else None
