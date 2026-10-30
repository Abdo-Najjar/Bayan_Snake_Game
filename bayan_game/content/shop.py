"""Outfits sold in the shop. Item names are "items.<id>" in the language files."""

SHOP_ITEMS = [
    dict(id="pink", kind="dress", price=0, color=(255, 105, 180)),
    dict(id="sky", kind="dress", price=30, color=(90, 180, 255)),
    dict(id="mint", kind="dress", price=40, color=(70, 205, 150)),
    dict(id="purple", kind="dress", price=40, color=(160, 95, 225)),
    dict(id="red", kind="dress", price=50, color=(230, 60, 70)),
    dict(id="gold", kind="dress", price=120, color=(245, 195, 40)),
    dict(id="bow", kind="hat", price=0),
    dict(id="flower", kind="hat", price=25),
    dict(id="cap", kind="hat", price=30),
    dict(id="hijab", kind="hat", price=30),
    dict(id="crown", kind="hat", price=100),
]

FREE_ITEMS = [it["id"] for it in SHOP_ITEMS if it["price"] == 0]


def item_by_id(item_id):
    for it in SHOP_ITEMS:
        if it["id"] == item_id:
            return it
    return SHOP_ITEMS[0]


def dress_color(item_id):
    return item_by_id(item_id).get("color", SHOP_ITEMS[0]["color"])
