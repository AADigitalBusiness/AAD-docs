"""Catalog models for the AAD-docs demo app."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Grouping of products in the store catalog."""

    name = models.CharField(
        max_length=100,
        verbose_name=_("Category name"),
        help_text=_("Human-readable name shown in the store navigation."),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL segment that identifies this category."),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent category"),
        help_text=_("Optional parent category in the hierarchy."),
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Item offered for sale in the catalog."""

    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("SKU"),
        help_text=_("Unique stock keeping unit code for inventory tracking."),
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Product name"),
        help_text=_("Display title of the product shown to buyers."),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("Category"),
        help_text=_("Category under which this product is listed."),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price"),
        help_text=_("Unit sale price in the store currency."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether the product is available for purchase."),
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"
