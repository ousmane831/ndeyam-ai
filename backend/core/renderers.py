"""Rendu JSON de l'API : messages du serveur en anglais si la requête le demande (Accept-Language)."""

from rest_framework.renderers import JSONRenderer

from .i18n_messages import translate_tree, wants_english


class LocalizedJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is not None and wants_english():
            data = translate_tree(data)
        return super().render(data, accepted_media_type, renderer_context)
