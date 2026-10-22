"""Sample product details for the demo catalog (shown as sample data in the app)."""

from __future__ import annotations

from ..models import ProductDetails, Review, SpecSection

SOURCE = "Demo catalog (sample details)"


def _specs(*sections: tuple[str, list[tuple[str, str]]]) -> tuple[SpecSection, ...]:
    return tuple(SpecSection(title, tuple(rows)) for title, rows in sections)


def _reviews(*items: tuple[float, str, str]) -> tuple[Review, ...]:
    return tuple(
        Review(text=text, rating=rating, title=title, author="Sample review") for rating, title, text in items
    )


# Share of ratings per star (5..1), in percent; turned into counts using the review total.
STAR_SHARE: dict[str, tuple[int, int, int, int, int]] = {
    "iPhone 15 128GB": (74, 16, 4, 2, 4),
    "Samsung Galaxy S24 256GB": (66, 18, 6, 3, 7),
    "Sony WH-1000XM5": (68, 17, 6, 3, 6),
    "boAt Airdopes 141": (52, 20, 10, 6, 12),
    "Nike Revolution 7": (62, 20, 8, 4, 6),
    "Prestige Iris 750W mixer grinder": (55, 22, 9, 5, 9),
}

DETAILS: dict[str, ProductDetails] = {
    "iPhone 15 128GB": ProductDetails(
        title="Apple iPhone 15 (128 GB)",
        brand="Apple",
        description=(
            "iPhone 15 has a 6.1-inch Super Retina XDR display with the Dynamic Island, a 48MP main "
            "camera with a 2x telephoto option, the A16 Bionic chip and USB-C charging, in an "
            "aluminium and colour-infused glass design."
        ),
        highlights=(
            "6.1-inch Super Retina XDR OLED display with Dynamic Island",
            "48MP main camera with 2x optical-quality zoom",
            "A16 Bionic chip",
            "USB-C charging and data",
            "Up to 20 hours video playback",
            "IP68 water and dust resistance",
        ),
        specs=_specs(
            (
                "Display",
                [
                    ("Size", "6.1 inches"),
                    ("Type", "Super Retina XDR OLED"),
                    ("Resolution", "2556 x 1179 pixels (460 ppi)"),
                ],
            ),
            ("Performance", [("Chip", "A16 Bionic"), ("Storage", "128 GB"), ("Operating system", "iOS")]),
            (
                "Camera",
                [
                    ("Rear", "48MP Main + 12MP Ultra Wide"),
                    ("Front", "12MP TrueDepth"),
                    ("Video", "4K at up to 60 fps"),
                ],
            ),
            (
                "Battery and charging",
                [
                    ("Video playback", "Up to 20 hours"),
                    ("Port", "USB-C"),
                    ("Wireless charging", "MagSafe and Qi"),
                ],
            ),
            (
                "Build",
                [
                    ("Weight", "171 g"),
                    ("Dimensions", "147.6 x 71.6 x 7.8 mm"),
                    ("Water resistance", "IP68"),
                    ("Network", "5G"),
                    ("SIM", "Nano-SIM + eSIM"),
                ],
            ),
        ),
        reviews=_reviews(
            (5, "Great camera", "Photos in daylight are excellent and the 2x zoom is genuinely useful."),
            (4, "Smooth, but 60Hz", "Very smooth for daily use; I only miss a 120Hz screen at this price."),
            (5, "USB-C finally", "Same cable as my laptop now. Battery easily lasts a full day."),
        ),
        source=SOURCE,
    ),
    "Samsung Galaxy S24 256GB": ProductDetails(
        title="Samsung Galaxy S24 5G (8 GB RAM, 256 GB)",
        brand="Samsung",
        description=(
            "Galaxy S24 brings Galaxy AI features such as Live Translate and Circle to Search to a "
            "compact 6.2-inch phone, with a 120Hz Dynamic AMOLED 2X display, a triple camera with a "
            "3x telephoto lens and the Exynos 2400 processor in India."
        ),
        highlights=(
            "6.2-inch FHD+ Dynamic AMOLED 2X, 120Hz",
            "Galaxy AI: Live Translate, Circle to Search, Note Assist",
            "50MP + 12MP ultra wide + 10MP 3x telephoto",
            "4000 mAh battery with 25W wired and wireless charging",
            "7 years of OS and security updates",
            "IP68 water and dust resistance",
        ),
        specs=_specs(
            (
                "Display",
                [
                    ("Size", "6.2 inches"),
                    ("Type", "Dynamic AMOLED 2X"),
                    ("Refresh rate", "Up to 120Hz"),
                    ("Resolution", "2340 x 1080 pixels"),
                ],
            ),
            (
                "Performance",
                [
                    ("Processor", "Exynos 2400"),
                    ("RAM", "8 GB"),
                    ("Storage", "256 GB"),
                    ("Operating system", "Android with One UI"),
                ],
            ),
            (
                "Camera",
                [
                    ("Rear", "50MP main (OIS) + 12MP ultra wide + 10MP 3x telephoto"),
                    ("Front", "12MP"),
                    ("Video", "Up to 8K at 30 fps"),
                ],
            ),
            (
                "Battery and charging",
                [
                    ("Battery", "4000 mAh"),
                    ("Wired charging", "25W"),
                    ("Wireless charging", "Yes, plus reverse wireless sharing"),
                ],
            ),
            (
                "Build",
                [
                    ("Weight", "167 g"),
                    ("Water resistance", "IP68"),
                    ("Glass", "Corning Gorilla Glass Victus 2"),
                    ("Network", "5G"),
                ],
            ),
        ),
        reviews=_reviews(
            (5, "Compact flagship", "Fits in one hand, the screen is bright and the zoom camera is great."),
            (4, "Good AI features", "Circle to Search is handy. Phone gets a little warm while gaming."),
            (3, "Battery is average", "Lasts a day with normal use, but heavy users will need a top-up."),
        ),
        source=SOURCE,
    ),
    "Sony WH-1000XM5": ProductDetails(
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        brand="Sony",
        description=(
            "Sony's flagship over-ear wireless headphones, with noise cancelling driven by two "
            "processors and eight microphones, up to 30 hours of battery with noise cancelling on, "
            "and clear hands-free calls."
        ),
        highlights=(
            "Industry-leading noise cancelling with 8 microphones",
            "Up to 30 hours battery (noise cancelling on)",
            "3-minute charge for about 3 hours of playback",
            "LDAC for high-resolution wireless audio",
            "Connect to two devices at once (multipoint)",
            "Lightweight, about 250 g",
        ),
        specs=_specs(
            (
                "Audio",
                [
                    ("Type", "Over-ear, closed back"),
                    ("Driver", "30 mm"),
                    ("Noise cancelling", "Yes, Integrated Processor V1 + QN1"),
                    ("Codecs", "SBC, AAC, LDAC"),
                ],
            ),
            (
                "Battery",
                [
                    ("With noise cancelling", "Up to 30 hours"),
                    ("Without noise cancelling", "Up to 40 hours"),
                    ("Quick charge", "3 min for about 3 hours"),
                    ("Charging port", "USB-C"),
                ],
            ),
            (
                "Connectivity",
                [("Wireless", "Bluetooth"), ("Multipoint", "Yes"), ("Wired", "3.5 mm cable included")],
            ),
            ("Build", [("Weight", "About 250 g"), ("Microphones", "8")]),
        ),
        reviews=_reviews(
            (5, "Silence on flights", "Noise cancelling is superb on flights and metro rides."),
            (5, "Very comfortable", "Light and comfortable for long work calls; mic quality is clear."),
            (3, "Does not fold", "Sounds great, but the case is bulky because the cups don't fold."),
        ),
        source=SOURCE,
    ),
    "boAt Airdopes 141": ProductDetails(
        title="boAt Airdopes 141 True Wireless Earbuds",
        brand="boAt",
        description=(
            "Budget truly wireless earbuds with up to 42 hours of total playback, ENx noise reduction "
            "for calls, BEAST mode for low-latency gaming and ASAP fast charging."
        ),
        highlights=(
            "Up to 42 hours total playback with the case",
            "ASAP Charge: 5 minutes for 75 minutes of playback",
            "ENx technology for clearer calls",
            "BEAST mode low-latency gaming",
            "IPX4 sweat and splash resistance",
            "Insta Wake N' Pair for quick connection",
        ),
        specs=_specs(
            ("Audio", [("Type", "In-ear, true wireless"), ("Driver", "8 mm"), ("Mic", "Yes, with ENx")]),
            (
                "Battery",
                [
                    ("Total playback", "Up to 42 hours"),
                    ("Fast charge", "5 min for 75 min"),
                    ("Charging port", "USB Type-C"),
                ],
            ),
            ("Build", [("Water resistance", "IPX4"), ("Controls", "Touch")]),
        ),
        reviews=_reviews(
            (5, "Value for money", "Battery life is excellent for the price and pairing is instant."),
            (4, "Good bass", "Punchy bass, decent for calls indoors. Outdoors calls are average."),
            (2, "Fit issue", "One earbud keeps slipping out during runs."),
        ),
        source=SOURCE,
    ),
    "Nike Revolution 7": ProductDetails(
        title="Nike Revolution 7 Men's Road Running Shoes",
        brand="Nike",
        description=(
            "An everyday road running shoe with soft foam cushioning, a breathable mesh upper and a "
            "durable rubber outsole, for easy runs, walks and gym sessions."
        ),
        highlights=(
            "Soft foam midsole for everyday cushioning",
            "Breathable mesh upper",
            "Durable rubber outsole",
            "Lace-up closure",
        ),
        specs=_specs(
            ("Product", [("Type", "Road running shoe"), ("Gender", "Men"), ("Closure", "Lace-up")]),
            ("Materials", [("Upper", "Mesh"), ("Midsole", "Foam"), ("Outsole", "Rubber")]),
        ),
        reviews=_reviews(
            (5, "Comfortable", "Very comfortable for daily 5 km walks. Size runs true."),
            (4, "Good starter shoe", "Light and cushioned enough for beginner running."),
            (3, "Average grip", "Grip is fine on roads but slippery on wet tiles."),
        ),
        source=SOURCE,
    ),
    "Prestige Iris 750W mixer grinder": ProductDetails(
        title="Prestige Iris 750 Watt Mixer Grinder with 4 Jars",
        brand="Prestige",
        description=(
            "A 750 W mixer grinder with three stainless steel jars for wet grinding, dry grinding and "
            "chutneys, plus a juicer jar with a fruit filter, 3-speed control with a pulse (incher) "
            "and anti-skid feet."
        ),
        highlights=(
            "750 W motor",
            "3 stainless steel jars + 1 juicer jar",
            "3-speed control with incher (pulse)",
            "Juicer jar with fruit filter",
            "Anti-skid feet",
        ),
        specs=_specs(
            ("Performance", [("Power", "750 W"), ("Speed settings", "3 + incher")]),
            (
                "Jars",
                [
                    ("Jars included", "4"),
                    ("Grinding jars", "3, stainless steel"),
                    ("Juicer", "1, with filter"),
                ],
            ),
            ("Electrical", [("Voltage", "230 V AC")]),
        ),
        reviews=_reviews(
            (5, "Powerful motor", "Grinds idli batter smoothly; chutney jar is very handy."),
            (4, "Good for daily use", "Works well, a bit loud at top speed."),
            (3, "Juicer is average", "Mixer is good but the juicer jar is messy to clean."),
        ),
        source=SOURCE,
    ),
}
