"""The SmartKharid app screen (Flet: one UI for Android, iOS, Windows, macOS, Linux and web)."""

from __future__ import annotations

import os

import flet as ft

from .formatting import format_count, format_money
from .models import PRESETS, Comparison, ProductDetails, Review, ScoredOffer, Weights
from .scoring import (
    BADGE_CHEAPEST,
    BADGE_FASTEST,
    BADGE_OUT_OF_STOCK,
    BADGE_RECOMMENDED,
    BADGE_TOP_RATED,
)
from .service import compare, fetch_details, fetch_offers
from .sources import DemoSource, SerpApiShoppingSource, Source
from .sources.demo import SUGGESTIONS

APP_NAME = "SmartKharid"
PREF = "smartkharid."
SOURCE_DEMO = "demo"
SOURCE_SERPAPI = "serpapi"
COUNTRIES = {"in": "India (₹)", "us": "United States ($)", "gb": "United Kingdom (£)", "ae": "UAE (AED)"}

BADGE_COLORS = {
    BADGE_RECOMMENDED: ft.Colors.GREEN_700,
    BADGE_CHEAPEST: ft.Colors.BLUE_700,
    BADGE_TOP_RATED: ft.Colors.AMBER_800,
    BADGE_FASTEST: ft.Colors.PURPLE_600,
    BADGE_OUT_OF_STOCK: ft.Colors.ERROR,  # theme-aware, stays readable in dark mode
}
CRITERIA = [
    ("price", "Price", ft.Icons.CURRENCY_RUPEE),
    ("reviews", "Customer reviews", ft.Icons.STAR_OUTLINE),
    ("delivery", "Fast delivery", ft.Icons.LOCAL_SHIPPING_OUTLINED),
    ("trust", "Store trust", ft.Icons.VERIFIED_USER_OUTLINED),
]


def _badge(label: str) -> ft.Control:
    color = BADGE_COLORS.get(label, ft.Colors.GREY_700)
    return ft.Container(
        content=ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=color),
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
    )


def _rating(s: ScoredOffer) -> ft.Control:
    o = s.offer
    if o.rating is None or o.review_count <= 0:
        return ft.Text("No reviews yet", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
    return ft.Row(
        [
            ft.Icon(ft.Icons.STAR_ROUNDED, color=ft.Colors.AMBER_700, size=18),
            ft.Text(f"{o.rating:.1f}", size=13, weight=ft.FontWeight.BOLD),
            ft.Text(f"({format_count(o.review_count)} reviews)", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=3,
        wrap=True,
    )


def _delivery(s: ScoredOffer) -> ft.Control:
    days = s.offer.delivery_days
    text = "Delivery time n/a" if days is None else "Tomorrow" if days <= 1 else f"{days} days"
    return ft.Row(
        [
            ft.Icon(ft.Icons.LOCAL_SHIPPING_OUTLINED, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text(text, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=4,
        tight=True,
    )


def _price_block(s: ScoredOffer, size: int) -> ft.Control:
    o = s.offer
    lines: list[ft.Control] = [
        ft.Text(format_money(o.total_price, o.currency), size=size, weight=ft.FontWeight.BOLD)
    ]
    if o.shipping > 0:
        lines.append(
            ft.Text(
                f"incl. {format_money(o.shipping, o.currency)} shipping",
                size=11,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
    return ft.Column(lines, spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.END)


def _breakdown(s: ScoredOffer) -> ft.Control:
    parts = [
        ("Price", s.price_score),
        ("Reviews", s.review_score),
        ("Delivery", s.delivery_score),
        ("Trust", s.trust_score),
    ]
    return ft.Text(
        "  ·  ".join(f"{name} {round(v * 100)}" for name, v in parts),
        size=11,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )


def _stars(rating: float | None, size: int = 14) -> ft.Control:
    rating = rating or 0
    icons = []
    for i in range(1, 6):
        if rating >= i - 0.25:
            icon = ft.Icons.STAR_ROUNDED
        elif rating >= i - 0.75:
            icon = ft.Icons.STAR_HALF_ROUNDED
        else:
            icon = ft.Icons.STAR_BORDER_ROUNDED
        icons.append(ft.Icon(icon, size=size, color=ft.Colors.AMBER_700))
    return ft.Row(icons, spacing=0, tight=True)


def _muted(text: str, size: int = 12, **kwargs) -> ft.Text:
    return ft.Text(text, size=size, color=ft.Colors.ON_SURFACE_VARIANT, **kwargs)


def _image(url: str | None, size: int) -> ft.Control:
    placeholder = ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=size // 2, color=ft.Colors.ON_SURFACE_VARIANT)
    content = (
        ft.Image(src=url, fit=ft.BoxFit.CONTAIN, width=size, height=size, error_content=placeholder)
        if url
        else placeholder
    )
    return ft.Container(
        content,
        width=size,
        height=size,
        bgcolor=ft.Colors.WHITE if url else ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def _section(title: str, icon, controls: list[ft.Control]) -> ft.Control:
    return ft.ExpansionTile(
        title=ft.Text(title, weight=ft.FontWeight.W_600, size=15),
        leading=ft.Icon(icon, size=20),
        tile_padding=ft.Padding.symmetric(horizontal=4),
        controls_padding=ft.Padding.only(left=4, right=4, bottom=8),
        expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
        controls=controls,
    )


def _review(r: Review) -> ft.Control:
    meta = " · ".join(x for x in (r.author, r.source, r.date) if x)
    lines: list[ft.Control] = []
    if r.rating is not None:
        lines.append(_stars(r.rating, 13))
    if r.title:
        lines.append(ft.Text(r.title, weight=ft.FontWeight.W_600, size=13))
    lines.append(ft.Text(r.text, size=13))
    if meta:
        lines.append(_muted(meta, 11))
    return ft.Container(
        ft.Column(lines, spacing=4),
        padding=10,
        border_radius=10,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )


class SmartKharidApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.prefs = ft.SharedPreferences()

        self.source_mode = SOURCE_DEMO
        self.serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self.country = "in"
        self.weights = PRESETS["Balanced"]

        self.full_details = True  # live mode: one extra SerpApi search for specs, reviews, photos

        self.query = ""
        self.offers = []
        self.errors: dict[str, str] = {}
        self.loading = False
        self.search_seq = 0  # ignores product details that arrive after a newer search started
        self.details: ProductDetails | None = None
        self.details_loading = False

        self.search_field = ft.TextField(
            hint_text="e.g. iPhone 15 128GB",
            label="Search a product",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=12,
            expand=True,
            # On phones an autofocused field pops the keyboard over the screen at launch.
            autofocus=page.platform not in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS),
            on_submit=self.on_search,
        )
        self.search_button = ft.FilledButton(
            "Compare", icon=ft.Icons.COMPARE_ARROWS, on_click=self.on_search, height=48
        )
        self.source_label = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.sliders = {
            key: ft.Slider(
                min=0,
                max=10,
                divisions=10,
                label="{value}",
                on_change_end=self.on_weights_change,
            )
            for key, _, _ in CRITERIA
        }
        self.priority_summary = ft.Text(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.results = ft.Column(spacing=12)

    # ---------- setup ----------

    async def start(self):
        page = self.page
        page.title = APP_NAME
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
        page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 0
        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.SHOPPING_BAG_OUTLINED),
            title=ft.Text(APP_NAME, weight=ft.FontWeight.BOLD),
            actions=[
                ft.IconButton(ft.Icons.SETTINGS_OUTLINED, tooltip="Settings", on_click=self.open_settings)
            ],
        )

        await self.load_settings()
        self.sync_sliders()
        self.update_source_label()
        self.render()

        body = ft.Column(
            [
                ft.Row([self.search_field, self.search_button], spacing=8),
                self.source_label,
                self.priorities_panel(),
                self.results,
            ],
            spacing=14,
        )
        page.add(
            ft.SafeArea(
                ft.ResponsiveRow(
                    [ft.Container(body, padding=16, col={"xs": 12, "md": 10, "lg": 8, "xl": 7})],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
        )

    def priorities_panel(self) -> ft.Control:
        presets = ft.Row(
            [ft.OutlinedButton(name, on_click=self.on_preset, data=name) for name in PRESETS],
            wrap=True,
            spacing=8,
            run_spacing=8,
        )
        # Label above a full-width slider, so the slider is wide enough to drag on a phone.
        rows = [
            ft.Column(
                [ft.Row([ft.Icon(icon, size=20), ft.Text(label)], spacing=8), self.sliders[key]],
                spacing=0,
            )
            for key, label, icon in CRITERIA
        ]
        return ft.ExpansionTile(
            title=ft.Text("Your priorities", weight=ft.FontWeight.W_600),
            subtitle=self.priority_summary,
            leading=ft.Icon(ft.Icons.TUNE),
            controls=[
                ft.Container(
                    ft.Column([presets, *rows], spacing=4),
                    padding=ft.Padding.only(left=16, right=16, bottom=12),
                )
            ],
        )

    # ---------- settings ----------

    async def load_settings(self):
        p = self.prefs
        self.source_mode = await p.get(PREF + "source") or self.source_mode
        self.serpapi_key = await p.get(PREF + "serpapi_key") or self.serpapi_key
        self.country = await p.get(PREF + "country") or self.country
        full = await p.get(PREF + "full_details")
        if isinstance(full, bool):
            self.full_details = full
        saved = await p.get(PREF + "weights")
        if isinstance(saved, str):
            try:
                self.weights = Weights(*(float(x) for x in saved.split(",")))
            except (TypeError, ValueError):
                pass

    async def save_settings(self):
        p = self.prefs
        await p.set(PREF + "source", self.source_mode)
        await p.set(PREF + "serpapi_key", self.serpapi_key)
        await p.set(PREF + "country", self.country)
        await p.set(PREF + "full_details", self.full_details)
        await self.save_weights()

    async def save_weights(self):
        w = self.weights
        await self.prefs.set(PREF + "weights", f"{w.price},{w.reviews},{w.delivery},{w.trust}")

    def update_source_label(self):
        if self.source_mode == SOURCE_SERPAPI:
            self.source_label.value = (
                f"Live prices: Google Shopping ({COUNTRIES.get(self.country, self.country)})"
            )
        else:
            self.source_label.value = (
                "Demo mode: sample prices for a few products. Add a SerpApi key in Settings for live prices."
            )

    def build_sources(self) -> list[Source]:
        if self.source_mode == SOURCE_SERPAPI:
            return [
                SerpApiShoppingSource(self.serpapi_key, country=self.country, full_details=self.full_details)
            ]
        return [DemoSource()]

    def open_settings(self, e):
        source = ft.Dropdown(
            label="Price data",
            value=self.source_mode,
            expand=True,
            options=[
                ft.DropdownOption(key=SOURCE_DEMO, text="Demo (sample prices)"),
                ft.DropdownOption(key=SOURCE_SERPAPI, text="Live (Google Shopping)"),
            ],
        )
        key = ft.TextField(
            label="SerpApi API key",
            value=self.serpapi_key,
            password=True,
            can_reveal_password=True,
        )
        country = ft.Dropdown(
            label="Country",
            value=self.country,
            expand=True,
            options=[ft.DropdownOption(key=k, text=v) for k, v in COUNTRIES.items()],
        )
        full_details = ft.Switch(label="Full product details (live mode)", value=self.full_details)

        async def save(_):
            self.source_mode = source.value or SOURCE_DEMO
            self.serpapi_key = (key.value or "").strip()
            self.country = country.value or "in"
            self.full_details = bool(full_details.value)
            await self.save_settings()
            self.page.pop_dialog()
            self.update_source_label()
            if self.query:
                await self.run_search()
            else:
                self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                scrollable=True,  # the keyboard leaves little room on phones
                inset_padding=ft.Padding.symmetric(horizontal=16, vertical=24),
                title=ft.Text("Settings"),
                content=ft.Column(
                    [
                        ft.Row([source]),
                        key,
                        ft.Row([country]),
                        full_details,
                        ft.Text(
                            "Live mode compares prices, ratings and reviews from Amazon, Flipkart, "
                            "Croma and hundreds of other stores listed on Google Shopping. "
                            "Full product details (photos, description, specifications, reviews) "
                            "use one more SerpApi search per product. "
                            "Get a free API key at serpapi.com. The key is stored only on this device.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    tight=True,
                    spacing=12,
                    width=420,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: self.page.pop_dialog()),
                    ft.FilledButton("Save", on_click=save),
                ],
            )
        )

    # ---------- priorities ----------

    def sync_sliders(self):
        for key, _, _ in CRITERIA:
            self.sliders[key].value = getattr(self.weights, key)
        n = self.weights.normalized()
        self.priority_summary.value = " · ".join(
            f"{label.split()[-1].capitalize()} {round(getattr(n, key) * 100)}%" for key, label, _ in CRITERIA
        )

    async def on_weights_change(self, e):
        self.weights = Weights(**{key: float(self.sliders[key].value) for key, _, _ in CRITERIA})
        self.sync_sliders()
        if not self.loading:  # a running search renders with the new weights when it finishes
            self.render()
        await self.save_weights()

    async def on_preset(self, e):
        self.weights = PRESETS[e.control.data]
        self.sync_sliders()
        if not self.loading:
            self.render()
        await self.save_weights()

    # ---------- search ----------

    async def on_search(self, e=None):
        query = (self.search_field.value or "").strip()
        if not query or self.loading:
            return
        self.query = query
        await self.run_search()

    async def on_suggestion(self, e):
        self.search_field.value = e.control.data
        await self.on_search()

    async def run_search(self):
        self.search_seq += 1
        seq = self.search_seq
        self.details, self.details_loading = None, False
        self.loading = True
        self.search_field.disabled = True  # drops focus, which hides the phone keyboard
        self.search_button.disabled = True
        self.results.controls = [
            ft.Container(
                ft.Column(
                    [ft.ProgressRing(), ft.Text(f"Checking stores for “{self.query}”…")],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
                alignment=ft.Alignment.CENTER,
            )
        ]
        self.page.update()
        sources = self.build_sources()
        try:
            fetched = await fetch_offers(self.query, sources)
            self.offers, self.errors = fetched.offers, fetched.errors
        finally:
            self.loading = False
            self.search_field.disabled = False
            self.search_button.disabled = False
        comparison = compare(self.query, self.offers, self.weights, self.errors)
        self.details_loading = bool(comparison.ranked)
        self.render()  # prices first; the product details follow when they arrive
        self.page.update()
        if not comparison.ranked:
            return
        details, error = await fetch_details(self.query, comparison, sources)
        if seq != self.search_seq:
            return
        self.details_loading = False
        self.details = details
        if error and details is None:
            self.errors = {**self.errors, "Product details": error}
        self.render()
        self.page.update()

    # ---------- results ----------

    def render(self):
        if not self.query:
            self.results.controls = [self.welcome()]
            return
        comparison = compare(self.query, self.offers, self.weights, self.errors)
        controls: list[ft.Control] = [self.error_banner(name, msg) for name, msg in comparison.errors.items()]
        if not comparison.ranked:
            if not comparison.errors:  # with errors, the banner already says what went wrong
                controls.append(self.empty_state())
        else:
            if self.details_loading or self.details:
                controls.append(self.product_card())
            if comparison.recommended:
                controls.append(self.recommendation_card(comparison))
            controls.append(self.summary_line(comparison))
            controls += [self.offer_card(i, s) for i, s in enumerate(comparison.ranked, 1)]
            controls.append(
                ft.Text(
                    "Prices and stock change often. Confirm the final price on the store before paying.",
                    size=11,
                    italic=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
        self.results.controls = controls

    def suggestion_chips(self) -> ft.Control:
        return ft.Row(
            [
                ft.Chip(
                    label=s, leading=ft.Icon(ft.Icons.SEARCH, size=16), data=s, on_click=self.on_suggestion
                )
                for s in SUGGESTIONS
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
        )

    def welcome(self) -> ft.Control:
        steps = [
            (ft.Icons.SEARCH, "Type the product you want to buy."),
            (
                ft.Icons.STOREFRONT_OUTLINED,
                "SmartKharid checks its price, reviews and delivery on every store.",
            ),
            (ft.Icons.LIST_ALT, "You also see the product's photos, specifications, highlights and reviews."),
            (ft.Icons.THUMB_UP_OUTLINED, "You get the best store for you, with the reasons."),
        ]
        return ft.Column(
            [
                ft.Text("Find the best store to buy from", size=22, weight=ft.FontWeight.BOLD),
                *[
                    ft.Row([ft.Icon(icon, color=ft.Colors.PRIMARY), ft.Text(text, expand=True)])
                    for icon, text in steps
                ],
                ft.Container(height=4),
                ft.Text(
                    "Try one of these:" if self.source_mode == SOURCE_DEMO else "Popular searches:",
                    weight=ft.FontWeight.W_600,
                ),
                self.suggestion_chips(),
            ],
            spacing=10,
        )

    def empty_state(self) -> ft.Control:
        hint = (
            "The demo catalog only has a few products. "
            "Try one of these, or switch to live prices in Settings:"
            if self.source_mode == SOURCE_DEMO
            else "Try a shorter or more general name (brand + model), e.g. “iPhone 15 128GB”."
        )
        items: list[ft.Control] = [
            ft.Icon(ft.Icons.SEARCH_OFF, size=40, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text(f"No store listings found for “{self.query}”.", weight=ft.FontWeight.W_600),
            ft.Text(hint, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
        ]
        if self.source_mode == SOURCE_DEMO:
            items.append(self.suggestion_chips())
        return ft.Container(ft.Column(items, spacing=8), padding=ft.Padding.symmetric(vertical=24))

    def error_banner(self, source: str, message: str) -> ft.Control:
        return ft.Container(
            ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_800),
                    ft.Text(f"{source}: {message}", expand=True, size=13),
                ]
            ),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.ORANGE),
            border_radius=10,
            padding=12,
        )

    def summary_line(self, c: Comparison) -> ft.Control:
        stores = len(c.ranked)
        text = f"Compared {stores} store{'s' if stores != 1 else ''}"
        if c.filtered_out:
            plural = "s" if c.filtered_out != 1 else ""
            text += f" · ignored {c.filtered_out} unrelated listing{plural} (accessories, other variants)"
        return ft.Text(text, size=12, color=ft.Colors.ON_SURFACE_VARIANT)

    def product_card(self) -> ft.Control:
        d = self.details
        if d is None:
            loading = ft.Row(
                [
                    ft.ProgressRing(width=18, height=18, stroke_width=2),
                    _muted("Loading product details…", 13),
                ],
                spacing=10,
            )
            return ft.Card(ft.Container(loading, padding=16))

        info: list[ft.Control] = [
            ft.Text(
                d.title, size=17, weight=ft.FontWeight.BOLD, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS
            )
        ]
        if d.brand:
            info.append(_muted(f"Brand: {d.brand}", 13))
        if d.rating is not None:
            rating: list[ft.Control] = [
                ft.Text(f"{d.rating:.1f}", size=14, weight=ft.FontWeight.BOLD),
                _stars(d.rating),
            ]
            if d.review_count:
                rating.append(_muted(f"({format_count(d.review_count)})", 13))
            info.append(ft.Row(rating, spacing=4, wrap=True))
        if d.price_range:
            info.append(ft.Text(d.price_range, size=14, weight=ft.FontWeight.W_600))

        controls: list[ft.Control] = [
            ft.Row(
                [_image(d.images[0] if d.images else None, 104), ft.Column(info, spacing=4, expand=True)],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=14,
            )
        ]
        if d.highlights:
            controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.CHECK, size=16, color=ft.Colors.PRIMARY),
                                ft.Text(h, size=13, expand=True),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            spacing=6,
                        )
                        for h in d.highlights[:5]
                    ],
                    spacing=4,
                )
            )

        sections: list[ft.Control] = []
        if len(d.images) > 1:
            photos = ft.Row([_image(url, 140) for url in d.images], scroll=ft.ScrollMode.AUTO, spacing=8)
            sections.append(_section(f"Photos ({len(d.images)})", ft.Icons.PHOTO_LIBRARY_OUTLINED, [photos]))
        if d.description:
            text = ft.Text(d.description, size=13, selectable=True)
            sections.append(_section("Description", ft.Icons.DESCRIPTION_OUTLINED, [text]))
        if len(d.highlights) > 5:
            bullets = [ft.Text("• " + h, size=13) for h in d.highlights]
            sections.append(_section("All highlights", ft.Icons.CHECKLIST, bullets))
        if d.specs:
            rows: list[ft.Control] = []
            for spec in d.specs:
                if spec.title:
                    heading = ft.Text(spec.title, weight=ft.FontWeight.BOLD, size=13)
                    rows.append(ft.Container(heading, padding=ft.Padding.only(top=6)))
                rows += [
                    ft.Row(
                        [_muted(name, 13, expand=2), ft.Text(value, size=13, expand=3, selectable=True)],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                    for name, value in spec.rows
                ]
            sections.append(_section("Specifications", ft.Icons.LIST_ALT, [ft.Column(rows, spacing=6)]))
        if d.rating_breakdown or d.reviews:
            parts: list[ft.Control] = []
            total = sum(n for _, n in d.rating_breakdown)
            for stars, n in d.rating_breakdown:
                bar = ft.ProgressBar(
                    value=n / total if total else 0, expand=True, bar_height=8, border_radius=4
                )
                count = _muted(format_count(n), 12, width=64, text_align=ft.TextAlign.RIGHT)
                parts.append(
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Text(str(stars), size=12),
                                    ft.Icon(ft.Icons.STAR_ROUNDED, size=12, color=ft.Colors.AMBER_700),
                                ],
                                spacing=1,
                                width=30,
                            ),
                            bar,
                            count,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
            parts += [_review(r) for r in d.reviews]
            title = "Ratings & reviews" if d.reviews else "Ratings"
            sections.append(_section(title, ft.Icons.RATE_REVIEW_OUTLINED, [ft.Column(parts, spacing=8)]))
        if sections:
            controls.append(ft.Column(sections, spacing=0))

        footer = " ".join(x for x in (f"Details: {d.source}." if d.source else "", d.note) if x)
        if footer:
            controls.append(_muted(footer, 11, italic=True))
        return ft.Card(ft.Container(ft.Column(controls, spacing=10), padding=16))

    def recommendation_card(self, c: Comparison) -> ft.Control:
        s = c.recommended
        o = s.offer
        green = ft.Colors.GREEN_700
        reasons = [
            ft.Row(
                [ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=green), ft.Text(r, expand=True, size=14)],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=8,
            )
            for r in c.reasons
        ]
        return ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.EMOJI_EVENTS, color=green),
                            ft.Text("Best place to buy", weight=ft.FontWeight.BOLD, color=green),
                            ft.Container(expand=True),
                            ft.Text(f"Score {s.score:.0f}/100", weight=ft.FontWeight.W_600, color=green),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.Text(o.store, size=28, weight=ft.FontWeight.BOLD, expand=True),
                            _price_block(s, 26),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Text(
                        o.title,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row([_rating(s), _delivery(s)], spacing=16, wrap=True),
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    *reasons,
                    ft.Container(height=4),
                    ft.FilledButton(
                        f"Buy on {o.store}",
                        icon=ft.Icons.OPEN_IN_NEW,
                        url=o.url,
                        disabled=not o.url,
                        style=ft.ButtonStyle(bgcolor=green, color=ft.Colors.WHITE),
                    ),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.GREEN),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.5, ft.Colors.GREEN)),
            border_radius=16,
            padding=18,
        )

    def offer_card(self, rank: int, s: ScoredOffer) -> ft.Control:
        o = s.offer
        left = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(f"#{rank}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(
                            o.store,
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Text(o.title, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row([_rating(s), _delivery(s)], spacing=14, wrap=True),
                ft.Row([_badge(b) for b in s.badges], wrap=True, spacing=6, run_spacing=6),
            ],
            spacing=5,
            expand=True,
        )
        right = ft.Column(
            [
                _price_block(s, 18),
                ft.Text(f"Score {s.score:.0f}", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )
        return ft.Card(
            ft.Container(
                ft.Column(
                    [
                        ft.Row([left, right], vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.ProgressBar(value=s.score / 100, bar_height=6, border_radius=3),
                        ft.Row(
                            [
                                ft.Container(_breakdown(s), expand=True),
                                ft.OutlinedButton(
                                    "Open store", icon=ft.Icons.OPEN_IN_NEW, url=o.url, disabled=not o.url
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=8,
                ),
                padding=14,
            ),
            opacity=1.0 if o.in_stock else 0.7,
        )


async def main(page: ft.Page):
    await SmartKharidApp(page).start()
