# Models

## Category

| Field | Type | Description |
|-------|------|-------------|
| name | CharField | Category name (max 100 chars) |
| slug | SlugField | URL-friendly identifier (max 100 chars, unique) |
| description | TextField | Detailed description |
| parent | ForeignKey | Parent category (null for top-level) |
| is_active | BooleanField | Whether category is active |
| created_at | DateTimeField | Auto-generated timestamp |
| updated_at | DateTimeField | Auto-updated timestamp |

## Product

| Field | Type | Description |
|-------|------|-------------|
| SKU | CharField | Stock Keeping Unit (max 50 chars, unique) |
| name | CharField | Product name (max 200 chars) |
| slug | SlugField | URL-friendly identifier (max 200 chars, unique) |
| category | ForeignKey | Category this product belongs to |
| description | TextField | Detailed product description |
| short_description | CharField | Brief summary (max 500 chars) |
| price | DecimalField | Selling price (10 digits, 2 decimal places) |
| cost | DecimalField | Cost price (nullable) |
| stock_quantity | PositiveIntegerField | Items in stock |
| is_active | BooleanField | Whether product is active |
| is_featured | BooleanField | Whether product should be featured |
| weight | DecimalField | Weight in kg (nullable) |

## ProductImage

| Field | Type | Description |
|-------|------|-------------|
| product | ForeignKey | Parent product |
| image | ImageField | Image file (uploaded to product_images/) |
| alt_text | CharField | Alternative text (max 200 chars) |
| is_primary | BooleanField | Primary image flag |
| order | PositiveIntegerField | Display order |
