from smartkharid.matching import filter_matching, is_same_product, normalize, relevance
from smartkharid.models import Offer


def offer(title: str, price: float = 1000, store: str = "Amazon") -> Offer:
    return Offer(store=store, title=title, price=price, url="https://example.com")


def test_normalize_joins_numbers_and_units():
    assert normalize("Apple iPhone 15 (128 GB)") == "apple iphone 15 128gb"
    assert normalize("Prestige Iris 750 Watt") == "prestige iris 750w"
    assert normalize("Sony WH-1000XM5") == "sony wh1000xm5"


def test_same_product_across_store_title_styles():
    q = "iPhone 15 128GB"
    assert is_same_product(q, "Apple iPhone 15 (128 GB) - Black")
    assert is_same_product(q, "Apple iPhone 15 (Black, 128 GB)")
    assert is_same_product(q, "Apple iPhone 15 128GB Black")


def test_rejects_other_storage_and_model_variants():
    q = "iPhone 15 128GB"
    assert not is_same_product(q, "Apple iPhone 15 (256GB, Black)")
    assert not is_same_product(q, "Apple iPhone 15 Plus (Black, 128 GB)")
    assert not is_same_product(q, "Apple iPhone 15 Pro (128 GB)")
    assert not is_same_product(q, "Apple iPhone 14 (128 GB)")


def test_variant_word_allowed_when_user_asked_for_it():
    assert is_same_product("iPhone 15 Pro 128GB", "Apple iPhone 15 Pro (128 GB)")


def test_rejects_accessories_but_not_products_mentioning_them():
    assert not is_same_product("iPhone 15", "Spigen Liquid Air Case for iPhone 15")
    assert not is_same_product("iPhone 15", "Tempered Glass Screen Protector Compatible with iPhone 15")
    assert is_same_product("Sony WH-1000XM5", "Sony WH-1000XM5 Headphones for Travel with Carry Case")
    assert is_same_product("iPhone 15 case", "Spigen Liquid Air Case for iPhone 15")


def test_numbers_must_match_exactly():
    assert not is_same_product("Nike Revolution 7", "Nike Revolution 6 Running Shoes")
    assert relevance("boat airdopes 141", "boAt Airdopes141 Earbuds") == 1.0


def test_filter_drops_suspiciously_cheap_matches():
    offers = [
        offer("Apple iPhone 15 128GB", 60000),
        offer("Apple iPhone 15 128GB", 61000, "Flipkart"),
        offer("Apple iPhone 15 128GB", 62000, "Croma"),
        offer("Apple iPhone 15 128GB Back Skin Sticker", 299, "Meesho"),
    ]
    kept, dropped = filter_matching("iPhone 15 128GB", offers)
    assert [o.store for o in kept] == ["Amazon", "Flipkart", "Croma"]
    assert dropped == 1
