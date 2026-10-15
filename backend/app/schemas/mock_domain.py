"""
Pydantic Schemas and Deterministic Mock Data for Controlled Research Experiments (Experiment B).

These schemas define lightweight, deterministic demo e-commerce endpoints to enable
real HTTP application traffic capture for behavioral integrity verification tasks
(TASK_01, TASK_02, TASK_03).

PRIVACY & RESEARCH CONSTRAINTS:
- No personal identifiable information (PII) stored.
- Demonstrator endpoints only; does not mutate persistent database tables or session caches.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Deterministic Mock Product Catalog
# ------------------------------------------------------------------------------

MOCK_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "prod_01": {
        "id": "prod_01",
        "name": "Quantum Pro Laptop 15",
        "category": "laptops",
        "price": 1299.99,
        "rating": 4.8,
        "description": "High-performance simulated developer workstation laptop with 16-core CPU.",
        "in_stock": True,
        "specifications": {
            "processor": "16-core OctaThread 3.8GHz",
            "memory": "32GB LPDDR5",
            "storage": "1TB NVMe Gen4",
            "display": "15.6-inch OLED 2880x1800 120Hz"
        }
    },
    "prod_02": {
        "id": "prod_02",
        "name": "Quantum Air Laptop 13",
        "category": "laptops",
        "price": 949.99,
        "rating": 4.6,
        "description": "Ultra-lightweight portable laptop for field telemetry and remote research.",
        "in_stock": True,
        "specifications": {
            "processor": "8-core OctaThread 2.6GHz",
            "memory": "16GB LPDDR5",
            "storage": "512GB NVMe Gen4",
            "display": "13.3-inch IPS 2560x1600"
        }
    },
    "prod_03": {
        "id": "prod_03",
        "name": "ErgoMech Tactile Keyboard",
        "category": "peripherals",
        "price": 159.99,
        "rating": 4.9,
        "description": "Custom mechanical keyboard with lubricated tactile switches and low-latency polling.",
        "in_stock": True,
        "specifications": {
            "switch_type": "Tactile Quiet 55g",
            "layout": "ANSI 75%",
            "connectivity": "USB-C wired / 2.4GHz RF",
            "polling_rate_hz": 1000
        }
    },
    "prod_04": {
        "id": "prod_04",
        "name": "Precision Optics Mouse",
        "category": "peripherals",
        "price": 79.99,
        "rating": 4.7,
        "description": "Ergonomic high-DPI optical mouse designed for micro-movement tracking experiments.",
        "in_stock": True,
        "specifications": {
            "sensor": "Optical 26000 DPI",
            "weight_g": 63,
            "buttons": 6,
            "polling_rate_hz": 1000
        }
    },
    "prod_05": {
        "id": "prod_05",
        "name": "UltraView 4K Monitor 27",
        "category": "monitors",
        "price": 449.99,
        "rating": 4.5,
        "description": "Color-accurate 27-inch 4K IPS display for telemetry analysis and visual verification.",
        "in_stock": True,
        "specifications": {
            "panel": "IPS 3840x2160",
            "refresh_rate_hz": 144,
            "color_gamut": "99% DCI-P3",
            "ports": "2x HDMI 2.1, 1x DP 1.4, 1x USB-C 90W"
        }
    },
    "prod_06": {
        "id": "prod_06",
        "name": "UltraWide Curved Monitor 34",
        "category": "monitors",
        "price": 699.99,
        "rating": 4.7,
        "description": "Immersive 34-inch 21:9 ultrawide monitor for multi-window research dashboards.",
        "in_stock": True,
        "specifications": {
            "panel": "Curved VA 3440x1440 1500R",
            "refresh_rate_hz": 165,
            "hdr": "HDR400",
            "ports": "2x HDMI 2.0, 2x DP 1.4"
        }
    },
    "prod_07": {
        "id": "prod_07",
        "name": "Studio ANC Headset Pro",
        "category": "audio",
        "price": 229.99,
        "rating": 4.4,
        "description": "Active noise-cancelling wireless headphones with high-fidelity acoustic drivers.",
        "in_stock": True,
        "specifications": {
            "driver_mm": 40,
            "battery_life_hours": 36,
            "anc_modes": 3,
            "bluetooth": "5.3 with LDAC"
        }
    },
    "prod_08": {
        "id": "prod_08",
        "name": "ThunderDock 12-in-1 Hub",
        "category": "accessories",
        "price": 119.99,
        "rating": 4.6,
        "description": "Multi-port aluminum desktop docking station with dual 4K display output and GbE.",
        "in_stock": True,
        "specifications": {
            "upstream": "Thunderbolt 4 85W PD",
            "downstream_ports": "3x USB-A 3.2, 2x USB-C 10Gbps, 2x DP, 1x GbE, SD/TF",
            "material": "Anodized Aluminum"
        }
    }
}


# ------------------------------------------------------------------------------
# 2. Schemas
# ------------------------------------------------------------------------------

class ProductItem(BaseModel):
    id: str = Field(..., description="Unique product ID")
    name: str = Field(..., description="Product display name")
    category: str = Field(..., description="Product category")
    price: float = Field(..., ge=0.0, description="Product price in base currency")
    rating: float = Field(default=5.0, ge=0.0, le=5.0, description="Average review rating")
    description: str = Field(..., description="Product summary description")
    in_stock: bool = Field(default=True, description="Stock availability flag")


class ProductListResponse(BaseModel):
    products: List[ProductItem] = Field(default_factory=list, description="Paginated products list")
    total: int = Field(..., ge=0, description="Total matching products count")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Page size limit")
    category: Optional[str] = Field(default=None, description="Applied category filter")


class ProductDetailResponse(BaseModel):
    id: str = Field(..., description="Product identifier")
    name: str = Field(..., description="Product display name")
    category: str = Field(..., description="Product category")
    price: float = Field(..., ge=0.0, description="Product price")
    rating: float = Field(..., ge=0.0, le=5.0, description="Review score")
    description: str = Field(..., description="Detailed product description")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Hardware technical specifications")
    in_stock: bool = Field(default=True, description="Stock status")


class SearchResponse(BaseModel):
    query: str = Field(..., description="Search query executed")
    results: List[ProductItem] = Field(default_factory=list, description="Matching product items")
    total_results: int = Field(..., ge=0, description="Total number of matching items")
    limit: int = Field(..., ge=1, description="Maximum returned results limit")


class SearchFilterResponse(BaseModel):
    filter: str = Field(..., description="Applied filter criterion")
    sort: str = Field(..., description="Applied sort ordering")
    results: List[ProductItem] = Field(default_factory=list, description="Filtered and sorted product items")
    total_results: int = Field(..., ge=0, description="Total number of matching items")


class CatalogResponse(BaseModel):
    category: Optional[str] = Field(default=None, description="Category filter if specified")
    categories: List[str] = Field(..., description="Available catalog product categories")
    featured_products: List[ProductItem] = Field(default_factory=list, description="Featured catalog products")
    total_catalog_items: int = Field(..., ge=0, description="Total active items in catalog")


class CartItemRequest(BaseModel):
    item_id: str = Field(..., min_length=1, max_length=64, description="Product identifier to add to cart")
    quantity: int = Field(..., gt=0, le=999, description="Positive quantity of items")


class CartItemResponse(BaseModel):
    status: str = Field(default="ADDED", description="Cart mutation status")
    item_id: str = Field(..., description="Product added")
    quantity: int = Field(..., gt=0, description="Quantity added")
    message: str = Field(default="Item added to mock cart successfully")


class CheckoutVerifyRequest(BaseModel):
    shipping_method: str = Field(..., min_length=1, max_length=64, description="Selected shipping method (standard, express, overnight, pickup)")
    currency: str = Field(..., min_length=3, max_length=3, description="3-letter currency code (e.g., USD, EUR)")


class CheckoutVerifyResponse(BaseModel):
    status: str = Field(default="VERIFIED", description="Checkout verification status")
    shipping_method: str = Field(..., description="Validated shipping method")
    currency: str = Field(..., description="Validated currency code")
    is_valid: bool = Field(default=True, description="Validation result boolean")
    message: str = Field(default="Mock checkout parameters verified for research demonstration")
