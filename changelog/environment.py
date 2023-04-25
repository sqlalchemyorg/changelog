import logging
import sys

LOG = logging.getLogger(__name__)


class Environment(object):
    __slots__ = ()

    env_classes = ()

    @classmethod
    def register(cls, env_class):
        cls.env_classes = (env_class,) + cls.env_classes

    @classmethod
    def from_document_settings(cls, settings):
        for cls in cls.env_classes:
            e = cls.from_document_settings(settings)
            if e is not None:
                return e

        raise NotImplementedError("TODO")

    @property
    def temp_data(self):
        raise NotImplementedError()

    @property
    def changelog_sections(self):
        raise NotImplementedError()

    @property
    def changelog_caption_class(self):
        raise NotImplementedError()

    @property
    def changelog_inner_tag_sort(self):
        raise NotImplementedError()

    @property
    def changelog_hide_sections_from_tags(self):
        raise NotImplementedError()

    @property
    def changelog_render_ticket(self):
        raise NotImplementedError()

    @property
    def changelog_render_pullreq(self):
        raise NotImplementedError()

    @property
    def changelog_render_changeset(self):
        raise NotImplementedError()

    def status_iterator(self, elements, message):
        raise NotImplementedError()


class DefaultEnvironment(Environment):
    @classmethod
    def from_document_settings(cls, settings):
        return settings.changelog_env

    def __init__(self, config_filename=None):
        self._temp_data = {}
        self.config = {}
        if config_filename is not None:
            exec(open(config_filename).read(), self.config)

    def log_debug(self, msg, *args):
        LOG.debug(msg, *args)

    @property
    def temp_data(self):
        return self._temp_data

    @property
    def changelog_sections(self):
        return self.config.get("changelog_sections", [])

    @property
    def changelog_caption_class(self):
        return self.config.get("changelog_caption_class", "caption")

    @property
    def changelog_inner_tag_sort(self):
        return self.config.get("changelog_inner_tag_sort", [])

    @property
    def changelog_hide_sections_from_tags(self):
        return self.config.get("changelog_hide_sections_from_tags", [])

    @property
    def changelog_hide_tags_in_entry(self):
        return self.config.get("changelog_hide_tags_in_entry", [])

    @property
    def changelog_render_ticket(self):
        return self.config.get("changelog_render_ticket", "ticket:%s")

    @property
    def changelog_render_pullreq(self):
        return self.config.get("changelog_render_pullreq", "pullreq:%s")

    @property
    def changelog_render_changeset(self):
        return self.config.get("changelog_render_changeset", "changeset:%s")

    def status_iterator(self, elements, message):
        for i, element in enumerate(elements, 1):
            percent = (i / len(elements)) * 100
            sys.stderr.write(message + "...[%d%%] %s\n" % (percent, element))
            yield element
