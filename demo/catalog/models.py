"""
Catalog models for AAD-docs demo.

These models demonstrate the code map generation from model metadata.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """
    Product category.
    
    Represents a category of products in the catalog.
    Each category can have multiple products.
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("Category Name"),
        help_text=_("The name of the category (e.g., Electronics, Books)"),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("URL Slug"),
        help_text=_("URL-friendly identifier for the category"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the category"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Category"),
        help_text=_("Parent category, if this is a subcategory"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this category is active and visible"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("When this category was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("When this category was last updated"),
    )
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]
    
    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """
    Product in the catalog.
    
    Represents a product that can be sold.
    Each product belongs to a category.
    """
    
    SKU = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("SKU"),
        help_text=_("Stock Keeping Unit - unique identifier for the product"),
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Product Name"),
        help_text=_("The name of the product"),
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name=_("URL Slug"),
        help_text=_("URL-friendly identifier for the product"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Category"),
        help_text=_("The category this product belongs to"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the product"),
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Short Description"),
        help_text=_("Brief summary for listings"),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price"),
        help_text=_("Selling price of the product"),
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Cost"),
        help_text=_("Cost price of the product"),
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Stock Quantity"),
        help_text=_("Number of items in stock"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this product is active and visible"),
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured"),
        help_text=_("Whether this product should be featured"),
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("Weight (kg)"),
        help_text=_("Product weight in kilograms"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )
    
    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-is_featured", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["SKU"]),
            models.Index(fields=["category"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.SKU})"
    
    @property
    def profit_margin(self) -> float:
        """Calculate profit margin percentage."""
        if self.cost and self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0.0



