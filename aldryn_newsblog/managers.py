try:
    from collections import Counter
except ImportError:
    from backport_collections import Counter
import datetime
from operator import attrgetter

from django.db import models

from aldryn_people.models import Person
from parler.managers import TranslatableManager
from taggit.models import Tag, TaggedItem


class RelatedManager(TranslatableManager):

    def get_query_set(self):
        qs = super(RelatedManager, self).get_query_set().filter(
            is_published=True)
        return qs.select_related('featured_image')

    def get_months(self, namespace):
        """
        Get months and years with posts count for given namespace string.

        This means how much posts there are in each month.
        Returns list of dictionaries of the following format:
        [{'date': date(YEAR, MONTH, ARBITRARY_DAY), 'num_entries': NUM_ENTRIES}, ...]
        ordered by date.
        """

        # TODO: check if this limitation still exists in Django 1.6+
        # This is done in a naive way as Django is having tough time while
        # aggregating on date fields
        entries = self.filter(app_config__namespace=namespace)
        dates = entries.values_list('publishing_date', flat=True)
        dates = [(x.year, x.month) for x in dates]
        date_counter = Counter(dates)
        dates = set(dates)
        dates = sorted(dates, reverse=True)
        months = [
            # Use day=3 to make sure timezone won't affect this hacks'
            # month value. There are UTC+14 and UTC-12 timezones.
            {'date': datetime.date(year=year, month=month, day=3),
             'num_entries': date_counter[(year, month)]}
            for year, month in dates]
        return months

    def get_authors(self, namespace):
        """
        Get authors with articles count for given namespace string.

        Returns Person queryset annotated with and ordered by 'num_entries'.
        """

        # This methods relies on the fact that Article.app_config.namespace
        # is effectively unique for Article models
        return Person.objects.filter(
            article__app_config__namespace=namespace).annotate(
                num_entries=models.Count('article')).order_by('-num_entries')

    def get_tags(self, namespace):
        """
        Get tags with articles count for given namespace string.

        Returns list of Tag objects with ordered by custom 'num_entries' attribute.
        """

        entries = self.filter(app_config__namespace=namespace)
        if not entries:
            return []
        kwargs = TaggedItem.bulk_lookup_kwargs(entries)

        # aggregate and sort
        counted_tags = dict(TaggedItem.objects
                                      .filter(**kwargs)
                                      .values('tag')
                                      .annotate(tag_count=models.Count('tag'))
                                      .values_list('tag', 'tag_count'))

        # and finally get the results
        tags = Tag.objects.filter(pk__in=counted_tags.keys())
        for tag in tags:
            tag.num_entries = counted_tags[tag.pk]
        return sorted(tags, key=attrgetter('num_entries'), reverse=True)
