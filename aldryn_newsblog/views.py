from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.utils import translation
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from parler.views import TranslatableSlugMixin, ViewUrlMixin
from taggit.models import Tag

from aldryn_apphooks_config.mixins import AppConfigMixin
from aldryn_categories.models import Category
from aldryn_people.models import Person

from .models import Article


class ArticleDetail(TranslatableSlugMixin, AppConfigMixin, DetailView):
    model = Article
    slug_field = 'slug'

    def get_queryset(self):
        return Article.objects.active_translations(
            translation.get_language()
        ).filter(
            app_config__namespace=self.namespace
        )


class ArticleList(ViewUrlMixin, AppConfigMixin, ListView):
    """A complete list of articles."""
    model = Article
    paginate_by = getattr(settings, 'ALDRYN_NEWSBLOG_PAGINATE_BY', 10)

    @property
    def queryset(self):
        return Article.objects.active_translations(
            translation.get_language()
        ).filter(
            app_config__namespace=self.namespace
        )


class AuthorArticleList(ArticleList):
    """A list of articles written by a specific author."""
    @property
    def queryset(self):
        # Note: each Article.author is Person instance with guaranteed
        # presence of unique slug field, which allows to use it in URLs
        return super(AuthorArticleList, self).queryset.filter(
            author=self.author)

    def get(self, request, author):
        self.author = Person.objects.get(slug=author)
        return super(AuthorArticleList, self).get(request)

    def get_context_data(self, **kwargs):
        kwargs['newsblog_author'] = self.author
        return super(AuthorArticleList, self).get_context_data(**kwargs)


class CategoryArticleList(ArticleList):
    """A list of articles filtered by categories."""
    @property
    def queryset(self):
        return super(CategoryArticleList, self).queryset.filter(
            categories=self.category)

    def get(self, request, category):
        self.category = Category.objects.get(translations__slug=category)
        return super(CategoryArticleList, self).get(request)

    def get_context_data(self, **kwargs):
        kwargs['newsblog_category'] = self.category
        return super(CategoryArticleList, self).get_context_data(**kwargs)


class TagArticleList(ArticleList):
    """A list of articles filtered by tags."""
    @property
    def queryset(self):
        return super(TagArticleList, self).queryset.filter(
            tags=self.tag)

    def get(self, request, tag):
        self.tag = Tag.objects.get(slug=tag)
        return super(TagArticleList, self).get(request)

    def get_context_data(self, **kwargs):
        kwargs['newsblog_tag'] = self.tag
        return super(TagArticleList, self).get_context_data(**kwargs)


class DateRangeArticleList(ArticleList):
    """A list of articles for a specific date range"""
    @property
    def queryset(self):
        return super(DateRangeArticleList, self).queryset.filter(
            publishing_date__gte=self.date_from,
            publishing_date__lt=self.date_to)

    def _daterange_from_kwargs(self, kwargs):
        raise NotImplemented('Subclasses of DateRangeArticleList need to'
                             'implement `_daterange_from_kwargs`.')

    def get(self, request, **kwargs):
        self.date_from, self.date_to = self._daterange_from_kwargs(kwargs)
        return super(DateRangeArticleList, self).get(request)

    def get_context_data(self, **kwargs):
        kwargs['newsblog_day'] = (
            int(self.kwargs.get('day')) if 'day' in self.kwargs else None)
        kwargs['newsblog_month'] = (
            int(self.kwargs.get('month')) if 'month' in self.kwargs else None)
        kwargs['newsblog_year'] = (
            int(self.kwargs.get('year')) if 'year' in self.kwargs else None)
        if kwargs['newsblog_year']:
            kwargs['newsblog_archive_date'] = date(
                kwargs['newsblog_year'],
                kwargs['newsblog_month'] or 1,
                kwargs['newsblog_day'] or 1)
        return super(DateRangeArticleList, self).get_context_data(**kwargs)


class YearArticleList(DateRangeArticleList):
    def _daterange_from_kwargs(self, kwargs):
        date_from = datetime(int(kwargs['year']), 1, 1)
        date_to = date_from + relativedelta(years=1)
        return date_from, date_to


class MonthArticleList(DateRangeArticleList):
    def _daterange_from_kwargs(self, kwargs):
        date_from = datetime(int(kwargs['year']), int(kwargs['month']), 1)
        date_to = date_from + relativedelta(months=1)
        return date_from, date_to


class DayArticleList(DateRangeArticleList):
    def _daterange_from_kwargs(self, kwargs):
        date_from = datetime(
            int(kwargs['year']), int(kwargs['month']), int(kwargs['day']))
        date_to = date_from + relativedelta(days=1)
        return date_from, date_to
